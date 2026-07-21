"""子智能体 G: 终审 (任务六).

职责 (见 docs/DESIGN_AGENT.md 第 4.7 节与第 7.6 节):
1. 子图内单报告终审 (finalize_single_report):
   - 读取 merged_cache (任务五产物)
   - SMART LLM 输出最终交叉评审建议 + JSON 结构化结果 (title/summary/content_md)
   - 写入 final_cache
2. 顶层图多报告交叉评审 (review_and_finalize):
   - 读取所有 B 子图的 final_cache_key
   - 检查文档间一致性 (术语统一 / 避免重复内容)
   - 简化版: 直接返回子图产物, 多报告间一致性检查可作为后续优化

import 路径约定: 用绝对导入.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from src.llm.client import LLMClient, LLMTier, get_llm_client
from src.observability.tracing import trace_chain
from src.skills.docbot.cache import read_cache

logger = logging.getLogger(__name__)


class FinalReviewerG:
    """子智能体 G: 终审.

    节点函数 g_final_in_subgraph_node 调用本类 finalize_single_report() 方法
    (子图内单报告终审); 顶层图节点函数 final_reviewer_g_node 调用
    review_and_finalize() 方法 (多报告交叉评审).
    使用 SMART LLM 输出最终 JSON 结构化文档.
    """

    def __init__(self, settings: Any | None = None) -> None:
        self.settings = settings
        try:
            self.llm: LLMClient = LLMClient(settings) if settings is not None else get_llm_client()
        except Exception:  # noqa: BLE001
            self.llm = get_llm_client()

    async def run(self, state: dict, *, settings: Any | None = None) -> dict:
        """执行单报告终审 (节点函数调用入口).

        本方法签名遵循任务约束. 实际终审逻辑委托给 finalize_single_report().
        """
        s = settings or self.settings
        merged = state.get("_merged_data", {})
        code_learning = state.get("_code_learning_data", {})
        result = await self.finalize_single_report(
            report_type=state.get("report_type", ""),
            language=state.get("language", "zh"),
            merged=merged,
            code_learning=code_learning,
            llm_session_id=state.get("llm_session_id", ""),
            settings=s,
        )
        return {"_final_result": result}

    async def finalize_single_report(
        self,
        report_type: str,
        language: str,
        merged: dict,
        code_learning: dict,
        llm_session_id: str,
        settings: Any | None = None,
    ) -> dict:
        """单报告终审 (子图内调用).

        Args:
            report_type: 报告类型 (8 种之一)
            language: 输出语言 (zh|en)
            merged: 任务五合并产物 {content_md, image_svgs, toc}
            code_learning: 任务一代码学习摘要
            llm_session_id: LLM 会话 ID
            settings: Settings 实例 (可选)

        Returns:
            {title, summary, content_md, image_svgs, toc}
        """
        # settings 透传给 LLM 调用 (LLMClient 内部解析)
        merged_content = ""
        if isinstance(merged, dict):
            merged_content = str(merged.get("content_md", ""))

        async with trace_chain(
            name=f"docbot.final_review.{report_type}",
            input={"merged_length": len(merged_content)},
        ) as span:
            # 1. 加载 persona + prompt 模板
            persona = self._load_persona(report_type)
            prompt_template = self._load_prompt_template()

            code_summary = ""
            if isinstance(code_learning, dict):
                code_summary = str(code_learning.get("summary", ""))

            # 2. 构造 prompt
            prompt = prompt_template.format(
                role_name=persona.get("role_name", "技术文档专家"),
                description=persona.get("description", ""),
                report_type=report_type,
                language=language,
                merged_content=merged_content,
                code_summary=code_summary[:30_000],  # 截断防止超长
            )

            # 3. SMART LLM 终审 (输出 JSON: title/summary/content_md)
            messages = [{"role": "user", "content": prompt}]
            response = await self.llm.achat(
                messages,
                tier=LLMTier.SMART,
                session_id=llm_session_id,
                span_name=f"docbot.final_review.{report_type}",
                step="final_review",
            )

            # 4. 解析 JSON 输出 (失败降级使用 merged 原文)
            final = self._parse_final(response.content, merged, persona)

            span.update(
                output={
                    "final_length": len(final.get("content_md", "")),
                    "title": final.get("title", ""),
                    "fallback": final.get("_fallback", False),
                }
            )
            return final

    async def review_and_finalize(
        self,
        report_type: str,
        final_cache_key: str,
        all_report_types: list[str],
        user_id: str,
        session_id: str,
        settings: Any | None = None,
    ) -> dict:
        """多报告交叉评审 (顶层图调用).

        简化版: 直接读取 final_cache 返回子图产物,
        多报告间一致性检查可作为后续优化.

        Args:
            report_type: 报告类型
            final_cache_key: 子图 final_cache 键
            all_report_types: 本次请求所有报告类型 (供交叉评审参考)
            user_id: 用户 ID
            session_id: 会话 ID
            settings: Settings 实例 (可选)

        Returns:
            {report_type, title, summary, content_md, image_svg, final_cache_key}
        """
        s = settings or self.settings
        async with trace_chain(
            name=f"docbot.cross_review.{report_type}",
            input={
                "report_type": report_type,
                "all_report_types": all_report_types,
                "final_cache_key": final_cache_key,
            },
        ) as span:
            # 从 Redis 读取子图 final 产物
            final_data: dict = {}
            raw = await read_cache(final_cache_key, settings=s)
            if raw:
                try:
                    parsed = json.loads(raw)
                    if isinstance(parsed, dict):
                        final_data = parsed
                except (json.JSONDecodeError, TypeError) as e:
                    logger.warning("final_cache JSON 解析失败 (降级空字典): %s", e)

            image_svgs = final_data.get("image_svgs", [])
            image_svg = image_svgs[0] if isinstance(image_svgs, list) and image_svgs else ""

            span.update(
                output={
                    "has_title": bool(final_data.get("title")),
                    "content_length": len(final_data.get("content_md", "")),
                }
            )
            return {
                "report_type": report_type,
                "title": final_data.get("title", ""),
                "summary": final_data.get("summary", ""),
                "content_md": final_data.get("content_md", ""),
                "image_svg": image_svg,
                "final_cache_key": final_cache_key,
            }

    def _load_persona(self, report_type: str) -> dict[str, str]:
        """加载 persona (失败降级空字典)."""
        try:
            from src.config.docbot.personas import DOCBOT_REPORT_PERSONAS

            return DOCBOT_REPORT_PERSONAS.get(report_type, {})
        except Exception as e:  # noqa: BLE001
            logger.warning("加载 persona 失败 (降级空 persona): %s", e)
            return {}

    def _load_prompt_template(self) -> str:
        """加载 FINAL_REVIEW_PROMPT 模板 (失败降级内置极简版)."""
        try:
            from src.config.docbot.prompts import FINAL_REVIEW_PROMPT

            return FINAL_REVIEW_PROMPT
        except Exception as e:  # noqa: BLE001
            logger.warning("加载 FINAL_REVIEW_PROMPT 失败 (降级内置): %s", e)
            return self._default_prompt()

    @staticmethod
    def _default_prompt() -> str:
        """提示词模板缺失时的兜底."""
        return (
            "你是 {role_name}, {description}\n\n"
            "请对以下 {report_type} 类型合并后的文档做最终评审与定稿:\n\n"
            "合并后内容:\n{merged_content}\n\n"
            "代码仓库学习摘要 (节选):\n{code_summary}\n\n"
            "目标语言: {language}\n\n"
            "输出 JSON: "
            '{{"title": "文档标题", "summary": "200 字以内摘要", '
            '"content_md": "最终定稿 Markdown 内容"}}'
        )

    @staticmethod
    def _parse_final(content: str, merged: dict, persona: dict) -> dict:
        """解析 LLM 输出的 JSON 终审结果, 失败降级使用 merged 原文."""
        merged_content = merged.get("content_md", "") if isinstance(merged, dict) else ""
        merged_images = merged.get("image_svgs", []) if isinstance(merged, dict) else []
        merged_toc = merged.get("toc", []) if isinstance(merged, dict) else []
        fallback_title = persona.get("role_name", "") if isinstance(persona, dict) else ""

        try:
            final = json.loads(content)
            if isinstance(final, dict):
                return {
                    "title": str(final.get("title", fallback_title)),
                    "summary": str(final.get("summary", "")),
                    "content_md": str(final.get("content_md", merged_content)),
                    "image_svgs": merged_images,
                    "toc": merged_toc,
                }
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning("LLM 终审 JSON 解析失败 (降级使用 merged 原文): %s", e)

        return {
            "title": fallback_title,
            "summary": "终审 JSON 解析失败, 使用合并原文",
            "content_md": merged_content,
            "image_svgs": merged_images,
            "toc": merged_toc,
            "_fallback": True,
        }


__all__ = ["FinalReviewerG"]

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

        P1 优化 (2026-07-24): 恢复 LLM 智能评审能力, 采用 sections_summary 策略.
        - LLM 接收每章节前 500 字符摘要 (非全文), 避免 max_tokens 截断
        - LLM 输出 JSON: {title, summary, terminology_suggestions, duplicate_chapters}
        - content_md 从 merged 透传 + 术语替换 (不经 LLM 生成, 避免截断/篡改)
        - duplicate_chapters 仅记录日志, 不实际删除 (避免章节丢失)

        历史决策 (2026-07-23): 曾降级为仅生成 title+summary.
        原因: 原 prompt 要求 LLM 将整个 content_md 作为 JSON 输出, 导致截断.
        现通过 sections_summary 策略恢复智能评审, 同时保持 content_md 零丢失.

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
        merged_images: list = []
        merged_toc: list = []
        if isinstance(merged, dict):
            merged_content = str(merged.get("content_md", ""))
            merged_images = merged.get("image_svgs", []) if isinstance(merged.get("image_svgs"), list) else []
            merged_toc = merged.get("toc", []) if isinstance(merged.get("toc"), list) else []

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

            # 2. 构造 sections_summary (每章节前 500 字符, 非全文)
            #    替代旧的 merged_preview (前 8000 字符), 避免 max_tokens 截断
            sections_summary = self._build_sections_summary(merged_content)

            prompt = prompt_template.format(
                role_name=persona.get("role_name", "技术文档专家"),
                description=persona.get("description", ""),
                report_type=report_type,
                language=language,
                sections_summary=sections_summary,
                code_summary=code_summary[:5_000],
            )

            # 3. SMART LLM 终审 (输出 JSON: title/summary/terminology/duplicate, 不含 content_md)
            messages = [{"role": "user", "content": prompt}]
            response = await self.llm.achat(
                messages,
                tier=LLMTier.SMART,
                session_id=llm_session_id,
                span_name=f"docbot.final_review.{report_type}",
                step="final_review",
            )

            # 4. 解析 LLM 输出, 提取 title/summary/terminology_suggestions/duplicate_chapters
            title, summary, terminology, duplicates = self._parse_review_response(
                response.content, persona
            )

            # 5. 应用术语统一建议 (字符串替换, 不删除章节, 保持零丢失)
            final_content_md = self._apply_terminology_suggestions(
                merged_content, terminology
            )

            # 6. 重复章节仅记录日志, 不实际删除 (避免章节丢失, 与大纲一一对应)
            if duplicates:
                logger.warning(
                    "终审检测到疑似重复章节 (不删除, 仅标记): %s, report_type=%s",
                    duplicates, report_type,
                )

            span.update(
                output={
                    "final_length": len(final_content_md),
                    "title": title,
                    "summary_length": len(summary),
                    "terminology_count": len(terminology),
                    "duplicate_chapters": duplicates,
                    "terminology_applied": final_content_md != merged_content,
                }
            )
            return {
                "title": title,
                "summary": summary,
                "content_md": final_content_md,  # 透传 + 术语替换, 零章节丢失
                "image_svgs": merged_images,
                "toc": merged_toc,
            }

    @staticmethod
    def _build_sections_summary(content_md: str, max_per_section: int = 500) -> str:
        """构造章节摘要 (每章节前 N 字符, 用于 LLM 评审).

        按 \\n\\n---\\n\\n 分割章节 (与 merger._concat_chapters 的分隔符一致),
        每章节提取标题行 + 前 max_per_section 字符作为摘要.
        替代旧的 merged_preview (前 8000 字符连续截取), 让 LLM 能看到所有章节
        的开头内容, 更准确地识别术语不一致和重复章节.

        Args:
            content_md: 合并后的完整文档内容
            max_per_section: 每章节摘要最大字符数 (默认 500)

        Returns:
            章节摘要文本 (各章节用空行分隔)
        """
        if not content_md:
            return "(空文档)"
        sections = content_md.split("\n\n---\n\n")
        summaries: list[str] = []
        for i, section in enumerate(sections, 1):
            section = section.strip() if isinstance(section, str) else ""
            if not section:
                continue
            # 提取第一行作为章节标题 (通常是 ## 标题)
            first_line = section.split("\n", 1)[0] if section else ""
            # 截取前 max_per_section 字符
            preview = section[:max_per_section]
            if len(section) > max_per_section:
                preview = preview + "..."
            summaries.append(f"### 章节{i}: {first_line}\n{preview}")
        return "\n\n".join(summaries) if summaries else "(无章节内容)"

    @staticmethod
    def _apply_terminology_suggestions(
        content_md: str, suggestions: list[dict]
    ) -> str:
        """应用术语统一建议 (字符串替换).

        仅做简单的字符串替换, 将不一致的术语统一为建议术语.
        不删除任何章节内容, 保持与大纲一一对应.

        Args:
            content_md: 原始合并内容
            suggestions: 术语建议列表 [{from, to, reason}, ...]

        Returns:
            术语统一后的内容 (若 suggestions 为空或替换失败, 返回原文)
        """
        if not content_md or not suggestions:
            return content_md
        result = content_md
        for sug in suggestions:
            if not isinstance(sug, dict):
                continue
            from_term = str(sug.get("from", "")).strip()
            to_term = str(sug.get("to", "")).strip()
            # 安全约束: 仅替换非空且长度合理的术语 (避免误替换单字符)
            if from_term and to_term and len(from_term) >= 2 and from_term != to_term:
                result = result.replace(from_term, to_term)
        return result

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
        """提示词模板缺失时的兜底 (P1: 智能评审版, 输出 title/summary/terminology/duplicate)."""
        return (
            "你是 {role_name}, {description}\n\n"
            "请对以下 {report_type} 类型合并后的文档进行终审:\n\n"
            "章节摘要:\n{sections_summary}\n\n"
            "代码仓库学习摘要 (节选):\n{code_summary}\n\n"
            "目标语言: {language}\n\n"
            "输出 JSON (严格 JSON, 不要 markdown 代码块): "
            '{{"title": "文档标题", "summary": "200 字以内摘要", '
            '"terminology_suggestions": [{{"from": "原始术语", "to": "统一术语"}}], '
            '"duplicate_chapters": []}}'
        )

    @staticmethod
    def _parse_review_response(
        content: str, persona: dict
    ) -> tuple[str, str, list[dict], list[int]]:
        """解析 LLM 终审输出 (P1: 智能评审版).

        解析 JSON: {title, summary, terminology_suggestions, duplicate_chapters}
        失败降级: title 使用 persona 角色名, terminology/duplicates 为空列表.

        Args:
            content: LLM 输出文本 (期望 JSON)
            persona: persona 字典 (用于降级 title)

        Returns:
            (title, summary, terminology_suggestions, duplicate_chapters) 元组
            - terminology_suggestions: [{from, to, reason}, ...]
            - duplicate_chapters: [int, ...] 疑似重复的章节编号
        """
        import re

        fallback_title = persona.get("role_name", "") if isinstance(persona, dict) else ""
        empty_terminology: list[dict] = []
        empty_duplicates: list[int] = []

        def _extract_fields(parsed: dict) -> tuple[str, str, list[dict], list[int]]:
            title = str(parsed.get("title", fallback_title))
            summary = str(parsed.get("summary", ""))
            terminology = parsed.get("terminology_suggestions", [])
            if not isinstance(terminology, list):
                terminology = []
            duplicates = parsed.get("duplicate_chapters", [])
            if not isinstance(duplicates, list):
                duplicates = []
            # duplicates 元素转 int (容错)
            duplicates_int: list[int] = []
            for d in duplicates:
                try:
                    duplicates_int.append(int(d))
                except (TypeError, ValueError):
                    continue
            return title, summary, terminology, duplicates_int

        # 尝试直接解析 JSON
        try:
            parsed = json.loads(content)
            if isinstance(parsed, dict):
                title, summary, terminology, duplicates = _extract_fields(parsed)
                if title or summary:
                    return title, summary, terminology, duplicates
        except (json.JSONDecodeError, TypeError):
            pass

        # 尝试从 markdown 代码块中提取 JSON
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
        if json_match:
            try:
                parsed = json.loads(json_match.group(1))
                if isinstance(parsed, dict):
                    title, summary, terminology, duplicates = _extract_fields(parsed)
                    if title or summary:
                        return title, summary, terminology, duplicates
            except (json.JSONDecodeError, TypeError):
                pass

        # 尝试从文本中提取 title 和 summary 字段 (容错: LLM 输出非标准 JSON)
        title_match = re.search(r'"title"\s*:\s*"([^"]*)"', content)
        summary_match = re.search(r'"summary"\s*:\s*"([^"]*)"', content)
        if title_match or summary_match:
            title = title_match.group(1) if title_match else fallback_title
            summary = summary_match.group(1) if summary_match else ""
            return title, summary, empty_terminology, empty_duplicates

        # 全部失败, 降级
        logger.warning("LLM 终审 JSON 解析失败 (降级使用 persona 角色名): content[:200]=%s", content[:200])
        return fallback_title, "", empty_terminology, empty_duplicates


__all__ = ["FinalReviewerG"]

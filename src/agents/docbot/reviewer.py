"""子智能体 E: 评审 (任务四).

职责 (见 docs/DESIGN_AGENT.md 第 4.5 节与第 7.4 节):
1. 读取 content_cache_keys[current_chapter_idx - 1] (D 填充的内容)
2. FAST LLM 评审 (覆盖度 / 准确性 / 代码路径引用 / 完整性)
3. 输出评审建议 + 修订后的内容
4. 写入 reviewed_cache_keys
5. 与 D 形成修订循环 (max_revisions_per_chapter=3)

import 路径约定: 用绝对导入.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from src.llm.client import LLMClient, LLMTier, get_llm_client
from src.observability.tracing import trace_chain

logger = logging.getLogger(__name__)


class ReviewerE:
    """子智能体 E: 评审.

    节点函数 e_review_node 调用本类 review_chapter() 方法.
    使用 FAST LLM 评审 D 填充的章节内容 (单次修订, route_after_e 不返回 'revise').
    与 D 形成修订循环, 通过 revision_count + max_revisions_per_chapter 控制硬上限.
    """

    def __init__(self, settings: Any | None = None) -> None:
        self.settings = settings
        try:
            self.llm: LLMClient = LLMClient(settings) if settings is not None else get_llm_client()
        except Exception:  # noqa: BLE001
            self.llm = get_llm_client()

    async def run(self, state: dict, *, settings: Any | None = None) -> dict:
        """执行章节评审 (节点函数调用入口).

        本方法签名遵循任务约束. 实际评审逻辑委托给 review_chapter().
        节点函数负责构造 cache_key + 写缓存, 本方法返回评审结果 dict.
        """
        s = settings or self.settings
        idx = state.get("current_chapter_idx", 0) - 1  # D 已 +1, E 处理上一个章节
        chapters = state.get("chapters", [])
        if idx < 0 or idx >= len(chapters):
            return {}

        chapter = chapters[idx]
        content_data = state.get("_content_data", {})

        result = await self.review_chapter(
            chapter=chapter,
            content=content_data,
            code_learning=state.get("_code_learning_data", {}),
            report_type=state.get("report_type", ""),
            language=state.get("language", "zh"),
            llm_session_id=state.get("llm_session_id", ""),
            settings=s,
        )
        return {
            "_reviewed_result": result,
            "revision_count": 1,  # operator.add 累积修订次数
        }

    async def review_chapter(
        self,
        chapter: dict,
        content: dict,
        code_learning: dict,
        report_type: str,
        language: str,
        llm_session_id: str,
        settings: Any | None = None,
        *,
        revision_round: int = 1,
        max_revisions: int = 3,
    ) -> dict:
        """评审单个章节.

        Args:
            chapter: 章节定义 {idx, title, sections, key_points}
            content: D 填充的内容 {chapter_idx, content_md, image_svgs}
            code_learning: 任务一代码学习摘要
            report_type: 报告类型
            language: 输出语言 (zh|en)
            llm_session_id: LLM 会话 ID
            settings: Settings 实例 (可选)
            revision_round: 当前修订轮次 (1-based)
            max_revisions: 最大修订次数 (默认 3)

        Returns:
            {chapter_idx, content_md, review_notes, needs_revision, image_svgs}
        """
        chapter_idx = chapter.get("idx", 0)
        chapter_title = chapter.get("title", "")
        async with trace_chain(
            name=f"docbot.review.{report_type}.{chapter_idx}",
            input={"chapter": chapter_title, "revision_round": revision_round},
        ) as span:
            # 1. 加载提示词模板
            prompt_template = self._load_prompt_template()
            code_summary = (
                code_learning.get("summary", "") if isinstance(code_learning, dict) else ""
            )
            content_md = (
                content.get("content_md", "") if isinstance(content, dict) else str(content)
            )

            # 2. 构造 prompt
            prompt = prompt_template.format(
                chapter_title=chapter_title,
                chapter_sections=chapter.get("sections", []),
                key_points=chapter.get("key_points", []),
                content=content_md,
                code_summary=code_summary[:30_000],  # 截断防止超长
                language=language,
            )

            # 3. SMART LLM 评审 (单次修订, route_after_e 不返回 'revise', 无 D-E 循环)
            # 用 SMART tier (deepseek-v4-flash) 取代 FAST tier (glm-4-flash):
            # - ZHIPU_API_KEY 无效时 FAST tier 认证失败, 降级链耗尽抛异常导致子图失败
            # - graph_total_timeout 已增至 1800s, SMART tier 12 章节评审时间充足
            # - 评审输出 JSON (needs_revision/review_notes/revised_content), SMART 质量更优
            messages = [{"role": "user", "content": prompt}]
            # 捕获 LLM 调用异常 (认证失败/降级链耗尽等), 失败时降级不修订,
            # 避免 e_review 节点抛异常导致整个子图失败 (success_reports 为空).
            try:
                response = await self.llm.achat(
                    messages,
                    tier=LLMTier.SMART,
                    session_id=llm_session_id,
                    span_name=f"docbot.review.{report_type}.{chapter_idx}",
                    step="review",
                )
            except Exception as llm_err:  # noqa: BLE001
                logger.warning(
                    "章节 %s LLM 评审调用失败 (降级不修订, 不阻断子图): %s",
                    chapter_idx,
                    llm_err,
                )
                span.update(
                    metadata={
                        "step": "review",
                        "llm_error": str(llm_err)[:200],
                        "degraded": True,
                    }
                )
                return {
                    "chapter_idx": chapter_idx,
                    "content_md": content_md,  # 原内容不修订
                    "review_notes": f"LLM 评审调用失败, 跳过修订: {llm_err}",
                    "needs_revision": False,
                    "image_svgs": content.get("image_svgs", []) if isinstance(content, dict) else [],
                }

            # 4. 解析 JSON 输出 (失败降级不修订)
            review = self._parse_review(response.content, content_md)
            # 修订轮次达上限时强制通过 (避免无限循环)
            if revision_round >= max_revisions and review.get("needs_revision", False):
                logger.info(
                    "章节 %s 修订达上限 (%d/%d), 强制通过",
                    chapter_idx,
                    revision_round,
                    max_revisions,
                )
                review["needs_revision"] = False

            span.update(
                output={
                    "needs_revision": review.get("needs_revision", False),
                    "review_notes_length": len(review.get("review_notes", "")),
                    "revision_round": revision_round,
                    "forced_pass": revision_round >= max_revisions,
                }
            )
            return {
                "chapter_idx": chapter_idx,
                "content_md": review.get("revised_content", content_md),
                "review_notes": review.get("review_notes", ""),
                "needs_revision": review.get("needs_revision", False),
                "image_svgs": content.get("image_svgs", []) if isinstance(content, dict) else [],
            }

    def _load_prompt_template(self) -> str:
        """加载 REVIEW_PROMPT 模板 (失败降级内置极简版)."""
        try:
            from src.config.docbot.prompts import REVIEW_PROMPT

            return REVIEW_PROMPT
        except Exception as e:  # noqa: BLE001
            logger.warning("加载 REVIEW_PROMPT 失败 (降级内置): %s", e)
            return self._default_prompt()

    @staticmethod
    def _default_prompt() -> str:
        """提示词模板缺失时的兜底."""
        return (
            "你是技术文档评审专家, 正在评审以下章节内容:\n\n"
            "章节标题: {chapter_title}\n"
            "章节小节: {chapter_sections}\n"
            "关键点: {key_points}\n\n"
            "待评审内容:\n{content}\n\n"
            "代码仓库学习摘要 (节选):\n{code_summary}\n\n"
            "目标语言: {language}\n\n"
            '输出 JSON: {{"needs_revision": false, "review_notes": "", "revised_content": ""}}'
        )

    @staticmethod
    def _parse_review(content: str, fallback_content: str) -> dict:
        """解析 LLM 输出的 JSON 评审结果, 失败降级不修订."""
        try:
            review = json.loads(content)
            if isinstance(review, dict):
                return {
                    "needs_revision": bool(review.get("needs_revision", False)),
                    "review_notes": str(review.get("review_notes", "")),
                    "revised_content": str(review.get("revised_content", fallback_content)),
                }
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning("LLM 评审 JSON 解析失败 (降级不修订): %s", e)
        return {
            "needs_revision": False,
            "review_notes": "JSON 解析失败, 跳过修订",
            "revised_content": fallback_content,
        }


__all__ = ["ReviewerE"]

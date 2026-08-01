"""子智能体 E: 评审 (任务四).

职责 (见 docs/DESIGN_AGENT.md 第 4.5 节与 AGENTS.md 第 7.4 节):
1. 读取 content_cache (D 填充的内容)
2. TOK-E1: 两阶段评审 — 先短 JSON 判定, needs_revision=false 时透传
3. 需要修订时再调用改写 LLM
4. PERF-E1: review_all_chapters_parallel 并行评审

import 路径约定: 用绝对导入.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from src.llm.client import LLMClient, LLMTier, get_llm_client
from src.observability.tracing import trace_chain

logger = logging.getLogger(__name__)

# TOK-E1: 阶段一仅判定 (禁止输出全文 revised_content)
_REVIEW_JUDGE_PROMPT = """你是技术文档评审专家, 正在评审以下章节内容的质量.

# 章节标题
{chapter_title}

# 章节小节
{chapter_sections}

# 关键点
{key_points}

# 待评审内容 (节选)
{content}

# 代码仓库学习摘要 (节选)
{code_summary}

# 目标语言
{language}

# 评审标准 (TOK-E2: 收紧, 实证上一轮 rewrite 率≈100%)
1. 事实错误: 端点/路径/方法/错误码/类名与代码摘要明显冲突 → 必须修订
2. 关键缺失: 章节要点完全未覆盖且影响可用性 → 可修订
3. 文风/深度/结构不够好、引用偏少、措辞可优化 → **不修订** (needs_revision=false)
4. 默认倾向 false: 存疑时选择不修订

# 任务要求
仅判定是否需要修订, **禁止**输出 revised_content 全文.
除非存在明确事实错误或关键要点完全缺失, 否则 needs_revision 必须为 false.

# 输出格式 (严格 JSON, 不要 markdown 代码块)
{{
  "needs_revision": false,
  "review_notes": "若不需要修订可为空; 若需要, 列出具体修改建议 (简短)"
}}
"""

# TOK-E1: 阶段二仅在 needs_revision=true 时调用
_REVIEW_REWRITE_PROMPT = """你是技术文档修订专家. 请按评审建议修订章节内容.

# 章节标题
{chapter_title}

# 原内容
{content}

# 修订建议
{review_notes}

# 代码摘要 (节选)
{code_summary}

# 目标语言
{language}

# 修订约束
1. 不得添加或修改标题序号前缀
2. 保留原 ## / ### 标题层级
3. 禁止输出 PlantUML / Mermaid / SVG 代码块
4. 直接输出修订后的完整 Markdown, 不要前后说明
"""


class ReviewerE:
    """子智能体 E: 评审."""

    def __init__(self, settings: Any | None = None) -> None:
        self.settings = settings
        try:
            self.llm: LLMClient = LLMClient(settings) if settings is not None else get_llm_client()
        except Exception:  # noqa: BLE001
            self.llm = get_llm_client()

    async def run(self, state: dict, *, settings: Any | None = None) -> dict:
        """执行章节评审 (节点函数调用入口)."""
        s = settings or self.settings
        idx = state.get("current_chapter_idx", 0) - 1
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
            "revision_count": 1,
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
        """TOK-E1 两阶段评审单个章节."""
        chapter_idx = chapter.get("idx", 0)
        chapter_title = chapter.get("title", "")
        async with trace_chain(
            name=f"docbot.review.{report_type}.{chapter_idx}",
            input={"chapter": chapter_title, "revision_round": revision_round},
        ) as span:
            code_summary = (
                code_learning.get("summary", "") if isinstance(code_learning, dict) else ""
            )[:8000]
            content_md = (
                content.get("content_md", "") if isinstance(content, dict) else str(content)
            )
            image_svgs = content.get("image_svgs", []) if isinstance(content, dict) else []

            judge_prompt = _REVIEW_JUDGE_PROMPT.format(
                chapter_title=chapter_title,
                chapter_sections=chapter.get("sections", []),
                key_points=chapter.get("key_points", []),
                content=content_md[:12_000],
                code_summary=code_summary,
                language=language,
            )

            try:
                judge_resp = await self.llm.achat(
                    [{"role": "user", "content": judge_prompt}],
                    tier=LLMTier.SMART,
                    session_id=llm_session_id,
                    span_name=f"docbot.review.{report_type}.{chapter_idx}",
                    step="review_judge",
                    max_tokens=1024,
                    reasoning_effort="none",
                    temperature=0.0,
                )
            except Exception as llm_err:  # noqa: BLE001
                logger.warning(
                    "章节 %s 评审判定失败 (降级不修订): %s", chapter_idx, llm_err
                )
                span.update(metadata={"degraded": True, "llm_error": str(llm_err)[:200]})
                return {
                    "chapter_idx": chapter_idx,
                    "content_md": content_md,
                    "review_notes": f"LLM 评审判定失败, 跳过修订: {llm_err}",
                    "needs_revision": False,
                    "image_svgs": image_svgs,
                }

            review = self._parse_judge(judge_resp.content)
            if revision_round >= max_revisions and review.get("needs_revision", False):
                review["needs_revision"] = False
                logger.info(
                    "章节 %s 修订达上限 (%d/%d), 强制通过",
                    chapter_idx,
                    revision_round,
                    max_revisions,
                )

            # TOK-E2b: api_doc 确定性卡片禁止 rewrite (LLM 改写会冲淡 AST 真源且拉长墙钟)
            # requirements: 仅当评审意见含事实/路径类关键词才允许 rewrite
            if review.get("needs_revision"):
                notes = str(review.get("review_notes") or "")
                if report_type == "api_doc":
                    logger.info(
                        "TOK-E2b: api_doc 章节 %s 跳过 rewrite (notes=%s)",
                        chapter_idx,
                        notes[:80],
                    )
                    review["needs_revision"] = False
                else:
                    critical_keys = (
                        "事实错误",
                        "路径错误",
                        "端点错误",
                        "编造",
                        "幻觉",
                        "完全缺失",
                        "错误码错误",
                        "与代码不符",
                    )
                    if not any(k in notes for k in critical_keys):
                        logger.info(
                            "TOK-E2b: 章节 %s 非事实类意见, 跳过 rewrite (notes=%s)",
                            chapter_idx,
                            notes[:80],
                        )
                        review["needs_revision"] = False

            final_content = content_md
            if review.get("needs_revision"):
                try:
                    rewrite_prompt = _REVIEW_REWRITE_PROMPT.format(
                        chapter_title=chapter_title,
                        content=content_md[:20_000],
                        review_notes=review.get("review_notes", "")[:2000],
                        code_summary=code_summary[:4000],
                        language=language,
                    )
                    rewrite_resp = await self.llm.achat(
                        [{"role": "user", "content": rewrite_prompt}],
                        tier=LLMTier.SMART,
                        session_id=llm_session_id,
                        span_name=f"docbot.review.rewrite.{report_type}.{chapter_idx}",
                        step="review_rewrite",
                        max_tokens=8192,
                        reasoning_effort="none",
                    )
                    if rewrite_resp.content and len(rewrite_resp.content) > 50:
                        final_content = rewrite_resp.content
                except Exception as e:  # noqa: BLE001
                    logger.warning("章节 %s 评审改写失败 (透传原文): %s", chapter_idx, e)
                    review["needs_revision"] = False

            span.update(
                output={
                    "needs_revision": review.get("needs_revision", False),
                    "review_notes_length": len(review.get("review_notes", "")),
                    "revision_round": revision_round,
                    "two_phase": True,
                    "rewrote": final_content is not content_md
                    and final_content != content_md,
                }
            )
            return {
                "chapter_idx": chapter_idx,
                "content_md": final_content,
                "review_notes": review.get("review_notes", ""),
                "needs_revision": bool(review.get("needs_revision", False)),
                "image_svgs": image_svgs,
            }

    async def review_all_chapters_parallel(
        self,
        chapters: list[dict],
        contents: list[dict],
        code_learning: dict,
        report_type: str,
        language: str,
        llm_session_id: str,
        settings: Any | None = None,
        *,
        max_revisions: int = 3,
        max_concurrent: int = 3,
    ) -> list[dict]:
        """PERF-E1: 并行评审全部章节."""
        if not chapters:
            return []
        semaphore = asyncio.Semaphore(max(1, max_concurrent))

        async def _one(i: int, chapter: dict) -> dict:
            async with semaphore:
                content = contents[i] if i < len(contents) else {}
                try:
                    return await self.review_chapter(
                        chapter=chapter if isinstance(chapter, dict) else {"idx": i},
                        content=content if isinstance(content, dict) else {},
                        code_learning=code_learning,
                        report_type=report_type,
                        language=language,
                        llm_session_id=llm_session_id,
                        settings=settings,
                        revision_round=1,
                        max_revisions=max_revisions,
                    )
                except Exception as e:  # noqa: BLE001
                    logger.warning("并行评审章节 %d 失败: %s", i, e)
                    md = ""
                    if isinstance(content, dict):
                        md = str(content.get("content_md") or "")
                    return {
                        "chapter_idx": i,
                        "content_md": md,
                        "review_notes": f"评审失败: {e}",
                        "needs_revision": False,
                        "image_svgs": [],
                    }

        tasks = [_one(i, ch) for i, ch in enumerate(chapters)]
        results = await asyncio.gather(*tasks)
        return list(results)

    def _load_prompt_template(self) -> str:
        """兼容旧调用."""
        try:
            from src.config.docbot.prompts import REVIEW_PROMPT

            return REVIEW_PROMPT
        except Exception as e:  # noqa: BLE001
            logger.warning("加载 REVIEW_PROMPT 失败: %s", e)
            return _REVIEW_JUDGE_PROMPT

    @staticmethod
    def _parse_judge(content: str) -> dict:
        """解析阶段一判定 JSON."""
        if not content:
            return {"needs_revision": False, "review_notes": ""}
        try:
            data = json.loads(content)
            if isinstance(data, dict):
                return {
                    "needs_revision": bool(data.get("needs_revision", False)),
                    "review_notes": str(data.get("review_notes", "")),
                }
        except (json.JSONDecodeError, TypeError):
            pass
        # 尝试提取 JSON 块
        first = content.find("{")
        last = content.rfind("}")
        if first >= 0 and last > first:
            try:
                data = json.loads(content[first : last + 1])
                if isinstance(data, dict):
                    return {
                        "needs_revision": bool(data.get("needs_revision", False)),
                        "review_notes": str(data.get("review_notes", "")),
                    }
            except (json.JSONDecodeError, TypeError):
                pass
        logger.warning("评审判定 JSON 解析失败, 降级不修订")
        return {"needs_revision": False, "review_notes": "JSON 解析失败, 跳过修订"}

    @staticmethod
    def _parse_review(content: str, fallback_content: str) -> dict:
        """兼容旧解析接口."""
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

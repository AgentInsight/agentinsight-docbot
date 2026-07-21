"""任务四技能: SMART LLM 评审章节内容.

职责 (见 docs/DESIGN_AGENT.md 第 4.5 节与第 7.4 节):
1. SMART LLM 评审 D 填充的章节 (覆盖度 / 准确性 / 代码路径引用 / 完整性)
2. 输出 JSON: {needs_revision, review_notes, revised_content}
3. 与 D 形成修订循环 (max_revisions_per_chapter=3 控制硬上限)

本技能是 ReviewerE 类的轻量函数式封装.

import 路径约定: 用绝对导入.
"""

from __future__ import annotations

from typing import Any

from src.agents.docbot.reviewer import ReviewerE


async def review_chapter(
    *,
    chapter: dict,
    content: dict,
    code_learning: dict,
    report_type: str,
    language: str,
    llm_session_id: str,
    settings: Any | None = None,
    revision_round: int = 1,
    max_revisions: int = 3,
) -> dict:
    """任务四: SMART LLM 评审单个章节.

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
    reviewer = ReviewerE(settings)
    return await reviewer.review_chapter(
        chapter=chapter,
        content=content,
        code_learning=code_learning,
        report_type=report_type,
        language=language,
        llm_session_id=llm_session_id,
        settings=settings,
        revision_round=revision_round,
        max_revisions=max_revisions,
    )


__all__ = ["review_chapter"]

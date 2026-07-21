"""任务六技能: SMART LLM 终审 + 修改建议.

职责 (见 docs/DESIGN_AGENT.md 第 4.7 节与第 7.6 节):
1. 读取 merged_cache (任务五产物)
2. SMART LLM 输出 JSON 终审结果 (title/summary/content_md)
3. 失败降级使用 merged 原文

本技能是 FinalReviewerG 类的轻量函数式封装.

import 路径约定: 用绝对导入.
"""

from __future__ import annotations

from typing import Any

from src.agents.docbot.final_reviewer import FinalReviewerG


async def final_review(
    *,
    report_type: str,
    language: str,
    merged: dict,
    code_learning: dict,
    llm_session_id: str,
    settings: Any | None = None,
) -> dict:
    """任务六: SMART LLM 单报告终审.

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
    reviewer = FinalReviewerG(settings)
    return await reviewer.finalize_single_report(
        report_type=report_type,
        language=language,
        merged=merged,
        code_learning=code_learning,
        llm_session_id=llm_session_id,
        settings=settings,
    )


__all__ = ["final_review"]

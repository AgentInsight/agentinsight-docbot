"""任务二技能: STRATEGIC LLM 细化报告纲要.

职责 (见 docs/DESIGN_AGENT.md 第 4.3 节与第 7.2 节):
- 基于 8 种文档默认大纲 (从 docs/*_OUTLINE.md 加载) + 代码上下文
- STRATEGIC LLM 细化纲要 (增删改章节)
- 输出 chapters: [{idx, title, sections, key_points}]

本技能是 OutlineRefinerC 类的轻量函数式封装, 供节点函数直接调用或 CodeLearner 模式复用.

import 路径约定: 用绝对导入.
"""

from __future__ import annotations

from typing import Any

from src.agents.docbot.outline_refiner import OutlineRefinerC


async def refine_outline(
    *,
    code_learning: dict,
    report_type: str,
    language: str,
    llm_session_id: str,
    settings: Any | None = None,
) -> dict:
    """任务二: STRATEGIC LLM 细化报告纲要.

    Args:
        code_learning: 任务一代码学习摘要 (dict 或 cache_key 字符串)
        report_type: 报告类型 (8 种之一)
        language: 输出语言 (zh|en)
        llm_session_id: LLM 会话 ID
        settings: Settings 实例 (可选)

    Returns:
        {"chapters": [{idx, title, sections, key_points}]}
    """
    refiner = OutlineRefinerC(settings)
    return await refiner.refine_outline(
        code_learning=code_learning,
        report_type=report_type,
        language=language,
        llm_session_id=llm_session_id,
        settings=settings,
    )


__all__ = ["refine_outline"]

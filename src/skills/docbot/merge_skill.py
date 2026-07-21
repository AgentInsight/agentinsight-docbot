"""任务五技能: SMART LLM 合并所有章节 + 去重.

职责 (见 docs/DESIGN_AGENT.md 第 4.6 节与第 7.5 节):
1. 读取所有 reviewed_cache_keys 内容 (任务四产物)
2. SMART LLM 合并所有章节 + 去除重复内容 (术语定义 / 代码示例等)
3. 统一术语和格式
4. 生成目录 (TOC)
5. 输出 {content_md, image_svgs, toc}

本技能是 MergerF 类的轻量函数式封装.

import 路径约定: 用绝对导入.
"""

from __future__ import annotations

from typing import Any

from src.agents.docbot.merger import MergerF


async def merge_chapters(
    *,
    reviewed_chapters: list[dict],
    chapters: list[dict],
    report_type: str,
    language: str,
    llm_session_id: str,
    settings: Any | None = None,
) -> dict:
    """任务五: SMART LLM 合并所有章节 + 去重.

    Args:
        reviewed_chapters: 任务四产物列表 [{chapter_idx, content_md, image_svgs, ...}]
        chapters: 章节定义列表 [{idx, title, ...}]
        report_type: 报告类型
        language: 输出语言 (zh|en)
        llm_session_id: LLM 会话 ID
        settings: Settings 实例 (可选)

    Returns:
        {content_md, image_svgs, toc}
    """
    merger = MergerF(settings)
    return await merger.merge_chapters(
        reviewed_chapters=reviewed_chapters,
        chapters=chapters,
        report_type=report_type,
        language=language,
        llm_session_id=llm_session_id,
        settings=settings,
    )


__all__ = ["merge_chapters"]

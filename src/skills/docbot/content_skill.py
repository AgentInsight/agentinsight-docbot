"""任务三技能: SMART LLM 填充章节内容 + SVG 配图.

职责 (见 docs/DESIGN_AGENT.md 第 4.4 节与第 7.3 节):
1. RAG 检索 (BM25 + Vector + RRF + 可选 Rerank), namespace 按 user_id + repo_id 隔离
2. SMART LLM 填充章节内容 (markdown 格式)
3. 按需生成 SVG 配图 (使用从 AIR 拷贝的 ImageGenerator)
4. 输出 {chapter_idx, content_md, image_svgs}

本技能是 ContentFillerD 类的轻量函数式封装.

import 路径约定: 用绝对导入.
"""

from __future__ import annotations

from typing import Any

from src.agents.docbot.content_filler import ContentFillerD


async def fill_chapter(
    *,
    chapter: dict,
    code_learning: dict,
    report_type: str,
    language: str,
    repo_id: str,
    user_id: str,
    llm_session_id: str,
    settings: Any | None = None,
) -> dict:
    """任务三: SMART LLM 填充单个章节内容.

    Args:
        chapter: 章节定义 {idx, title, sections, key_points}
        code_learning: 任务一代码学习摘要
        report_type: 报告类型
        language: 输出语言 (zh|en)
        repo_id: 仓库 ID (用于 RAG namespace 隔离)
        user_id: 用户 ID
        llm_session_id: LLM 会话 ID
        settings: Settings 实例 (可选)

    Returns:
        {chapter_idx, content_md, image_svgs}
    """
    filler = ContentFillerD(settings)
    return await filler.fill_chapter(
        chapter=chapter,
        code_learning=code_learning,
        report_type=report_type,
        language=language,
        repo_id=repo_id,
        user_id=user_id,
        llm_session_id=llm_session_id,
        settings=settings,
    )


async def generate_image_for_chapter(
    *,
    chapter_title: str,
    report_type: str,
    language: str,
    user_id: str,
    settings: Any | None = None,
) -> str:
    """为章节生成 SVG 配图 (失败时返回空字符串, 不阻断主流程).

    Args:
        chapter_title: 章节标题 (作为图像 prompt 主题)
        report_type: 报告类型 (用于 trace)
        language: 输出语言 (zh|en)
        user_id: 用户 ID (用于 trace 隔离)
        settings: Settings 实例 (可选)

    Returns:
        SVG 字符串 (失败时返回空字符串)
    """
    filler = ContentFillerD(settings)
    return await filler._generate_image_for_chapter(  # noqa: SLF001 (技能封装允许访问内部方法)
        chapter_title=chapter_title,
        report_type=report_type,
        language=language,
        user_id=user_id,
    )


__all__ = ["fill_chapter", "generate_image_for_chapter"]

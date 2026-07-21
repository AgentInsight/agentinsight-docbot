"""docbot 图守卫与路由函数.

约定 (见 docs/DESIGN_AGENT.md 第 5 章与 AGENTS.md 第 5 章):
- 路由函数为纯函数, 接受 state, 返回字符串 (路由 key)
- max_revisions_per_chapter=3 为硬上限, 由 revision_count + 条件边强制
- D 循环: 填充下一章节 或 进入评审
- E 循环: 修订当前章节 或 评审下一章节 或 完成

路由键约定:
- route_after_d 返回 'next_chapter' (回到 d_content_fill) 或 'review' (流转到 e_review)
- route_after_e 返回 'revise' (回到 d_content_fill) / 'next_chapter' (回到 e_review)
  或 'done' (流转到 f_merge)

import 路径约定: 用绝对导入 (不是 from src.graph...).
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def route_after_d(state: dict) -> str:
    """D 填充内容后路由.

    - 还有未处理章节 (current_chapter_idx < len(chapters)) → 'next_chapter'
      (回到 d_content_fill 继续填充下一章节)
    - 所有章节填充完毕 → 'review' (流转到 e_review)

    Args:
        state: ReportTaskState

    Returns:
        'next_chapter' | 'review'
    """
    current_idx = state.get("current_chapter_idx", 0)
    chapters = state.get("chapters", [])
    if current_idx < len(chapters):
        return "next_chapter"
    return "review"


def route_after_e(state: dict) -> str:
    """E 评审后路由.

    修订循环控制 (见 docs/DESIGN_AGENT.md 第 5.2 节):
    - 简化版: 通过 revision_count + max_revisions_per_chapter 控制
    - 实际修订建议由 LLM 输出的 needs_revision 标志决定 (写入 reviewed_cache, 节点读取)
    - 达 max_revisions_per_chapter 时强制通过 (ReviewerE 内已实现, 此处仅路由)

    路由规则:
    - 还有未评审章节 (current_chapter_idx < len(chapters)) → 'next_chapter'
      (D 已推进到下一章节, E 继续评审)
    - 所有章节评审完毕 → 'done' (流转到 f_merge)

    注: 简化版未实现基于 needs_revision 的 revise 循环 (需把 needs_revision
        写入 state, 当前 reviewed_cache 仅存 Redis). 实际实现可扩展 state
        增加 current_chapter_needs_revision 字段, 或在此读取 Redis (异步,
        LangGraph 路由函数不支持 async, 故简化).

    Args:
        state: ReportTaskState

    Returns:
        'next_chapter' | 'done'
    """
    current_idx = state.get("current_chapter_idx", 0)
    chapters = state.get("chapters", [])
    revision_count = state.get("revision_count", 0)
    max_revisions = state.get("max_revisions_per_chapter", 3)

    # 所有章节评审完毕 → done
    if current_idx >= len(chapters):
        # revision_count 达上限时强制完成 (避免无限循环)
        if revision_count >= max_revisions:
            return "done"
        return "done"

    # 还有未评审章节 → next_chapter (D 已推进到下一章节, E 继续评审)
    return "next_chapter"


__all__ = ["route_after_d", "route_after_e"]

"""docbot 报告子图构建器.

约定 (见 docs/DESIGN_AGENT.md 第 6.2 节与 AGENTS.md 第 5 章):
- StateGraph(ReportTaskState) 报告子图, 不挂独立 checkpointer (与顶层图共享)
- 节点通过 functools.partial 注入 settings, 保持节点函数纯函数语义
- D-E 修订循环通过 add_conditional_edges 实现, max_revisions_per_chapter=3 硬上限
- 纲要细化步骤已移除 (用户要求: 原始大纲够用), 直接加载 outlines/*.yaml
- 节点顺序 (带循环):
  b_init_session → c_code_learning → c_load_outline → d_content_fill
      ↕ (D 循环)
  e_review → f_merge → g_final_in_subgraph → END

D 循环路由键:
- 'next_chapter' → d_content_fill (继续填充下一章节)
- 'review' → e_review (所有章节填充完毕, 进入评审)

E 循环路由键 (基于独立 review_idx):
- 'next_chapter' → e_review (E 继续评审下一章节)
- 'done' → f_merge (所有章节评审完毕)

import 路径约定: 用绝对导入.
"""

from __future__ import annotations

import logging
from functools import partial
from typing import Any

from langgraph.graph import END, StateGraph

from src.graph.edges import route_after_d, route_after_e
from src.graph.report_nodes import (
    b_init_session_node,
    c_code_learning_node,
    c_load_outline_node,
    d_content_fill_node,
    e_review_node,
    f_merge_node,
    g_final_in_subgraph_node,
)
from src.graph.state import ReportTaskState

logger = logging.getLogger(__name__)


def build_report_subgraph(settings: Any | None = None):
    """构建单个报告任务的子图 (同步, 不挂 checkpointer).

    节点顺序 (带 D-E 循环):
    b_init_session → c_code_learning → c_load_outline → d_content_fill
        ↕ (D 循环: next_chapter → d_content_fill, review → e_review)
    e_review → f_merge → g_final_in_subgraph → END

    说明:
    - 纲要细化步骤已移除, c_load_outline 直接加载 outlines/*.yaml 默认大纲
    - D 循环: 每次填充一个章节, current_chapter_idx += 1, 直到所有章节填充完毕
    - E 循环: 使用独立 review_idx 索引, 确保所有章节都被评审 (修复原索引错位 bug)
    - 简化版: route_after_e 不实现 'revise' 路径, 修订由 ReviewerE 内 revision_round 控制

    Args:
        settings: Settings 实例 (可选)

    Returns:
        已 compile 的 LangGraph 子图 (不挂 checkpointer, 由顶层图 spawn_b_tasks
        调用时通过 config 注入 thread_id 做会话隔离)
    """
    graph = StateGraph(ReportTaskState)

    # partial 注入 settings, 保持节点函数纯函数语义
    graph.add_node("b_init_session", partial(b_init_session_node, settings=settings))
    graph.add_node("c_code_learning", partial(c_code_learning_node, settings=settings))
    graph.add_node("c_load_outline", partial(c_load_outline_node, settings=settings))
    graph.add_node("d_content_fill", partial(d_content_fill_node, settings=settings))
    graph.add_node("e_review", partial(e_review_node, settings=settings))
    graph.add_node("f_merge", partial(f_merge_node, settings=settings))
    graph.add_node("g_final_in_subgraph", partial(g_final_in_subgraph_node, settings=settings))

    graph.set_entry_point("b_init_session")
    graph.add_edge("b_init_session", "c_code_learning")
    graph.add_edge("c_code_learning", "c_load_outline")
    graph.add_edge("c_load_outline", "d_content_fill")

    # D 循环: 填充下一章节 或 进入评审
    graph.add_conditional_edges(
        "d_content_fill",
        route_after_d,
        {
            "next_chapter": "d_content_fill",
            "review": "e_review",
        },
    )

    # E 循环: 评审下一章节 或 完成 (基于独立 review_idx)
    # 简化版 route_after_e 仅返回 'next_chapter' | 'done', 'revise' 路径未启用
    # (修订由 ReviewerE 内 revision_round 控制, 达上限强制通过)
    graph.add_conditional_edges(
        "e_review",
        route_after_e,
        {
            "revise": "d_content_fill",
            "next_chapter": "e_review",
            "done": "f_merge",
        },
    )

    graph.add_edge("f_merge", "g_final_in_subgraph")
    graph.add_edge("g_final_in_subgraph", END)

    return graph.compile()


__all__ = ["build_report_subgraph"]

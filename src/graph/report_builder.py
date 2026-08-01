"""docbot 报告子图构建器.

约定 (见 docs/DESIGN_AGENT.md 第 6.2 节与 AGENTS.md 第 5 章):
- StateGraph(ReportTaskState) 报告子图, 不挂独立 checkpointer (与顶层图共享)
- 节点通过 functools.partial 注入 settings, 保持节点函数纯函数语义
- P0 (perf v2): 纲要后改为章级并行填章/评审 (d_content_fill_all → e_review_all)
- 节点顺序:
  b_init_session → c_code_learning → c_outline_refine
    → d_content_fill_all → e_review_all → f_merge → g_final_in_subgraph → END

import 路径约定: 用绝对导入.
"""

from __future__ import annotations

import logging
from functools import partial
from typing import Any

from langgraph.graph import END, StateGraph

from src.graph.report_nodes import (
    b_init_session_node,
    c_code_learning_node,
    c_outline_refine_node,
    d_content_fill_all_node,
    e_review_all_node,
    f_merge_node,
    g_final_in_subgraph_node,
)
from src.graph.state import ReportTaskState

logger = logging.getLogger(__name__)


def build_report_subgraph(settings: Any | None = None):
    """构建单个报告任务的子图 (同步, 不挂 checkpointer).

    P0 章级并行: outline 后单节点并行填章 → 单节点并行评审 → merge.
    旧版 D/E 自环节点保留在 report_nodes 供兼容测试, 子图不再挂载.

    Args:
        settings: Settings 实例 (可选)

    Returns:
        已 compile 的 LangGraph 子图
    """
    graph = StateGraph(ReportTaskState)

    graph.add_node("b_init_session", partial(b_init_session_node, settings=settings))
    graph.add_node("c_code_learning", partial(c_code_learning_node, settings=settings))
    graph.add_node("c_outline_refine", partial(c_outline_refine_node, settings=settings))
    graph.add_node("d_content_fill_all", partial(d_content_fill_all_node, settings=settings))
    graph.add_node("e_review_all", partial(e_review_all_node, settings=settings))
    graph.add_node("f_merge", partial(f_merge_node, settings=settings))
    graph.add_node("g_final_in_subgraph", partial(g_final_in_subgraph_node, settings=settings))

    graph.set_entry_point("b_init_session")
    graph.add_edge("b_init_session", "c_code_learning")
    graph.add_edge("c_code_learning", "c_outline_refine")
    graph.add_edge("c_outline_refine", "d_content_fill_all")
    graph.add_edge("d_content_fill_all", "e_review_all")
    graph.add_edge("e_review_all", "f_merge")
    graph.add_edge("f_merge", "g_final_in_subgraph")
    graph.add_edge("g_final_in_subgraph", END)

    return graph.compile()


__all__ = ["build_report_subgraph"]

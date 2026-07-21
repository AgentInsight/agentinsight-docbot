"""docbot 顶层图构建器.

约定 (见 docs/DESIGN_AGENT.md 第 6.1 节与 AGENTS.md 第 5 章):
- StateGraph(DocbotState) 顶层图, 挂 PostgresSaver checkpointer
- 节点通过 functools.partial 注入 settings, 保持节点函数纯函数语义
- 节点顺序: coordinator_a → spawn_b_tasks → final_reviewer_g → save_reports → END

import 路径约定: 用绝对导入.
"""

from __future__ import annotations

import logging
from functools import partial
from typing import Any

from langgraph.graph import END, StateGraph

from src.graph.nodes import (
    coordinator_a_node,
    final_reviewer_g_node,
    save_reports_node,
    spawn_b_tasks_node,
)
from src.graph.state import DocbotState

logger = logging.getLogger(__name__)


async def build_docbot_graph(settings: Any | None = None):
    """构建 docbot 顶层图 (异步, 因 checkpointer 创建为 async).

    节点顺序:
    coordinator_a → spawn_b_tasks → final_reviewer_g → save_reports → END

    Args:
        settings: Settings 实例 (可选; None 时由 get_checkpointer 内部 get_settings())

    Returns:
        已 compile 的 LangGraph 可执行图 (挂 PostgresSaver checkpointer)
    """
    from src.memory.checkpointer import get_checkpointer

    graph = StateGraph(DocbotState)

    # partial 注入 settings, 保持节点函数纯函数语义
    graph.add_node("coordinator_a", partial(coordinator_a_node, settings=settings))
    graph.add_node("spawn_b_tasks", partial(spawn_b_tasks_node, settings=settings))
    graph.add_node("final_reviewer_g", partial(final_reviewer_g_node, settings=settings))
    graph.add_node("save_reports", partial(save_reports_node, settings=settings))

    graph.set_entry_point("coordinator_a")
    graph.add_edge("coordinator_a", "spawn_b_tasks")
    graph.add_edge("spawn_b_tasks", "final_reviewer_g")
    graph.add_edge("final_reviewer_g", "save_reports")
    graph.add_edge("save_reports", END)

    # PostgresSaver 创建为 async (get_checkpointer 返回 coroutine)
    checkpointer = await get_checkpointer(settings)
    return graph.compile(checkpointer=checkpointer)


__all__ = ["build_docbot_graph"]

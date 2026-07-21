"""docbot LangGraph 图编排模块.

模块清单 (见 docs/DESIGN_AGENT.md 第 1 章与 AGENTS.md 第 3 章):
- state.py           DocbotState (顶层图) + ReportTaskState (报告子图) 双 schema
- nodes.py            顶层图 4 个节点 (coordinator_a / spawn_b_tasks / final_reviewer_g / save_reports)
- report_nodes.py    报告子图 7 个节点 (b_init_session / c_code_learning / c_outline_refine /
                      d_content_fill / e_review / f_merge / g_final_in_subgraph)
- edges.py            守卫与路由 (route_after_d / route_after_e)
- builder.py          build_docbot_graph() 顶层图构建器 (async, 挂 PostgresSaver)
- report_builder.py   build_report_subgraph() 报告子图构建器 (sync, 不挂 checkpointer)

导出接口:
- build_docbot_graph: 异步构建顶层图, await 调用
- build_report_subgraph: 同步构建报告子图
- DocbotState: 顶层图 state TypedDict
- ReportTaskState: 报告子图 state TypedDict

import 路径约定: 用绝对导入 (不是 from src.graph...).
"""

from __future__ import annotations

from src.graph.builder import build_docbot_graph
from src.graph.report_builder import build_report_subgraph
from src.graph.state import DocbotState, ReportTaskState

__all__ = [
    "DocbotState",
    "ReportTaskState",
    "build_docbot_graph",
    "build_report_subgraph",
]

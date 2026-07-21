"""docbot 7 个子智能体业务逻辑.

子智能体清单 (见 docs/DESIGN_AGENT.md 第 7 章与 AGENTS.md 第 5 章):
- CoordinatorA     (coordinator.py)      顶层协调入口, 解析 JSON 指令 + 校验参数
- ReportRunnerB    (report_runner.py)    单报告任务协调, 创建 llm_session_id + report_id
- OutlineRefinerC  (outline_refiner.py)  纲要细化, STRATEGIC LLM 在默认大纲基础上 + 代码上下文
- ContentFillerD    (content_filler.py)   章节内容填充, SMART LLM + RAG + SVG 配图
- ReviewerE        (reviewer.py)         章节评审, SMART LLM 输出 JSON 评审建议 + 修订内容
- MergerF          (merger.py)           合并去重, SMART LLM 合并所有章节 + 统一术语
- FinalReviewerG   (final_reviewer.py)   终审, SMART LLM 输出 JSON 终审结果 (title/summary/content_md)

调用方式: 节点函数 (graph/nodes.py + graph/report_nodes.py) 通过 partial 注入 settings,
实例化对应类后调用其 run() 或专项方法 (refine_outline / fill_chapter / ...).

import 路径约定: 用绝对导入 (不是 from src.agents...).
"""

from __future__ import annotations

from src.agents.docbot.content_filler import ContentFillerD
from src.agents.docbot.coordinator import CoordinatorA
from src.agents.docbot.final_reviewer import FinalReviewerG
from src.agents.docbot.merger import MergerF
from src.agents.docbot.outline_refiner import OutlineRefinerC
from src.agents.docbot.report_runner import ReportRunnerB
from src.agents.docbot.reviewer import ReviewerE

__all__ = [
    "ContentFillerD",
    "CoordinatorA",
    "FinalReviewerG",
    "MergerF",
    "OutlineRefinerC",
    "ReportRunnerB",
    "ReviewerE",
]

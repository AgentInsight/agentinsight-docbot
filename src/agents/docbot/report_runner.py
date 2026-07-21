"""子智能体 B: 单报告任务协调.

职责 (见 docs/DESIGN_AGENT.md 第 4.1 节):
1. 为该报告任务创建独立 LLM 会话 ID (b_init_session 节点调用)
2. 协调 6 步流水线执行 (实际编排由报告子图 build_report_subgraph 完成)
3. 收集子图最终产物 (final_cache_key + report_id + title + summary)

本类不直接执行 LLM 调用, 仅负责会话初始化与最终产物收集;
6 步流水线的具体业务逻辑在 agents/docbot/outline_refiner.py / content_filler.py /
reviewer.py / merger.py / final_reviewer.py 中实现, 由 report_nodes.py 节点函数调用.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from src.observability.tracing import trace_chain

logger = logging.getLogger(__name__)


class ReportRunnerB:
    """子智能体 B: 单报告任务协调.

    节点函数 b_init_session_node 调用本类 init_session() 创建 LLM 会话;
    节点函数 g_final_in_subgraph_node 调用本类 collect_result() 收集最终产物.
    """

    def __init__(self, settings: Any | None = None) -> None:
        self.settings = settings

    async def run(self, state: dict, *, settings: Any | None = None) -> dict:
        """执行单报告任务协调 (在 b_init_session 节点中调用).

        职责:
        1. 为该报告任务创建独立 LLM 会话 ID
        2. 创建 report_id (供 save_reports 节点引用)
        3. 设置 max_revisions_per_chapter (从 settings 读取, 默认 3)

        Args:
            state: ReportTaskState (dict 形式)
            settings: Settings 实例 (可选)

        Returns:
            delta dict: {llm_session_id, report_id, max_revisions_per_chapter}
        """
        s = settings or self.settings
        report_type = state.get("report_type", "unknown")
        async with trace_chain(
            name=f"docbot.report.{report_type}.b_init",
            input={"report_type": report_type},
        ) as span:
            llm_session_id = f"docbot-{report_type}-{uuid.uuid4().hex[:8]}"
            report_id = f"rpt-{uuid.uuid4().hex}"

            # max_revisions_per_chapter 默认 3 (D-E 修订循环硬上限)
            max_revisions = 3
            if s is not None:
                max_revisions = int(getattr(s, "max_revisions_per_chapter", 3))

            span.update(
                output={
                    "llm_session_id": llm_session_id,
                    "report_id": report_id,
                    "max_revisions_per_chapter": max_revisions,
                }
            )
            return {
                "llm_session_id": llm_session_id,
                "report_id": report_id,
                "max_revisions_per_chapter": max_revisions,
            }

    async def collect_result(self, state: dict, *, settings: Any | None = None) -> dict:
        """收集报告子图最终产物 (供顶层图 spawn_b_tasks 提取 final_cache_key).

        Args:
            state: ReportTaskState (子图执行完毕后的完整 state)

        Returns:
            {report_type, report_id, final_cache_key, title, summary, image_svg, download_urls}
        """
        return {
            "report_type": state.get("report_type", ""),
            "report_id": state.get("report_id", ""),
            "final_cache_key": state.get("final_cache_key", ""),
            "title": state.get("report_title", ""),
            "summary": state.get("report_summary", ""),
            "image_svg": state.get("report_image_svg", ""),
            "download_urls": state.get("download_urls", {}),
        }


__all__ = ["ReportRunnerB"]

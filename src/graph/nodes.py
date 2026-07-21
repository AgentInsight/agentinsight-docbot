"""docbot 顶层图节点函数 (4 个).

约定 (见 docs/DESIGN_AGENT.md 第 3 章与 AGENTS.md 第 5 章):
- 节点为纯函数: async def node(state, settings) -> dict
- 节点不原地修改 state, 返回 delta dict 由 LangGraph reducer 合并
- 节点不直连厂商 LLM SDK, 统一走 llm/ 网关 (LiteLLM)
- 节点内通过异步上下文管理器包裹 trace (trace_agent / trace_chain)
- settings 通过 functools.partial 在 builder 中注入, 保持节点函数纯函数语义

顶层图节点顺序:
coordinator_a → spawn_b_tasks → final_reviewer_g → save_reports → END

import 路径约定: 用绝对导入 (不是 from src.graph...).
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from src.observability.tracing import trace_chain

logger = logging.getLogger(__name__)


async def coordinator_a_node(state: dict, settings: Any | None = None) -> dict:
    """子智能体 A: 协调入口.

    职责:
    1. 解析用户消息中的 JSON 指令 (action=generate_docs)
    2. 校验 repo_id / report_types / report_format / language
    3. 生成 trace_agent 根 span
    4. 返回派发参数 (不在此节点派发 B 子图, 由 spawn_b_tasks 负责)

    Args:
        state: 顶层 DocbotState (dict 形式)
        settings: Settings 实例 (由 partial 注入)

    Returns:
        delta dict: {repo_id, report_types, report_format, language, iteration_count}
        或 {errors} (校验失败时)
    """
    # 延迟导入避免模块加载时循环依赖 (agents.docbot.coordinator 可能 import graph.state)
    from src.agents.docbot.coordinator import CoordinatorA

    coordinator = CoordinatorA(settings)
    return await coordinator.run(state, settings=settings)


async def spawn_b_tasks_node(state: dict, settings: Any | None = None) -> dict:
    """子智能体 A 的派发逻辑: asyncio.gather 并发派发 N 个 B 子图.

    并发上限由 settings.max_concurrent_reports (默认 3) 控制 (见 AGENTS.md 第 5 章).
    不使用 LangGraph Send API (AGENTS.md 第 4 章不推荐清单第 16 项),
    用 asyncio.gather + Semaphore 保持状态机语义清晰.

    Args:
        state: 顶层 DocbotState, 已含 repo_id / report_types / report_format / language
        settings: Settings 实例

    Returns:
        delta dict: {report_tasks: list[dict], errors: list[str]}
        report_tasks 每项: {report_type, report_id, final_cache_key, title, summary, image_svg, download_urls}
    """
    from src.graph.report_builder import build_report_subgraph
    from src.graph.state import ReportTaskState

    async with trace_chain(
        name="docbot.spawn_b_tasks",
        input={
            "report_types": state.get("report_types", []),
            "repo_id": state.get("repo_id", ""),
        },
    ) as span:
        # 并发上限 (默认 3, 与 settings.max_concurrent_reports 一致)
        max_concurrent = 3
        if settings is not None:
            max_concurrent = int(getattr(settings, "max_concurrent_reports", 3))
        semaphore = asyncio.Semaphore(max_concurrent)

        report_types = state.get("report_types", [])
        agent_id = state.get("agent_id", "agentinsight-docbot")
        user_id = state.get("user_id", "")
        session_id = state.get("session_id", "")
        repo_id = state.get("repo_id", "")
        report_format = state.get("report_format", "markdown")
        language = state.get("language", "zh")
        max_revisions_per_chapter = 3
        if settings is not None:
            max_revisions_per_chapter = int(getattr(settings, "max_revisions_per_chapter", 3))

        async def run_one(report_type: str) -> dict:
            async with semaphore:
                # 构造子图初始 state (ReportTaskState 全字段)
                sub_state: ReportTaskState = {
                    "report_type": report_type,
                    "report_format": report_format,
                    "language": language,
                    "repo_id": repo_id,
                    "user_id": user_id,
                    "session_id": session_id,
                    "agent_id": agent_id,
                    "llm_session_id": "",
                    "code_learning_cache_key": "",
                    "outline_cache_key": "",
                    "content_cache_keys": [],
                    "reviewed_cache_keys": [],
                    "merged_cache_key": "",
                    "final_cache_key": "",
                    "current_chapter_idx": 0,
                    "chapters": [],
                    "max_revisions_per_chapter": max_revisions_per_chapter,
                    "revision_count": 0,
                    "report_id": "",
                    "report_title": "",
                    "report_summary": "",
                    "report_image_svg": "",
                    "download_urls": {},
                }
                # 子图独立 thread_id (与顶层图区分, 见 AGENTS.md 第 6 章)
                thread_id = f"{agent_id}:{session_id}:{report_type}"
                config = {"configurable": {"thread_id": thread_id}}
                subgraph = build_report_subgraph(settings)
                result = await subgraph.ainvoke(sub_state, config=config)
                return result if isinstance(result, dict) else {}

        # 并发派发, return_exceptions=True 防止单个失败拖垮全部
        tasks = [run_one(rt) for rt in report_types]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        success_reports: list[dict] = []
        errors: list[str] = []
        for rt, r in zip(report_types, results, strict=True):
            if isinstance(r, Exception):
                errors.append(f"report_type={rt} failed: {r}")
            elif isinstance(r, dict) and r.get("final_cache_key"):
                success_reports.append(
                    {
                        "report_type": rt,
                        "report_id": r.get("report_id", ""),
                        "final_cache_key": r["final_cache_key"],
                        "title": r.get("report_title", ""),
                        "summary": r.get("report_summary", ""),
                        "image_svg": r.get("report_image_svg", ""),
                        "download_urls": r.get("download_urls", {}),
                    }
                )
            else:
                errors.append(f"report_type={rt} no_final_cache_key")

        span.update(
            output={
                "success_count": len(success_reports),
                "error_count": len(errors),
            }
        )
        return {
            "report_tasks": success_reports,
            "errors": errors,
        }


async def final_reviewer_g_node(state: dict, settings: Any | None = None) -> dict:
    """子智能体 G (顶层图位置): 对子图产物做最终交叉评审.

    职责:
    1. 读取所有 B 子图的 final_cache_key
    2. 检查文档间一致性 (术语统一 / 避免重复内容)
    3. SMART LLM 输出最终交叉评审建议
    4. 写入 final_reports

    简化版 (见 docs/DESIGN_AGENT.md 第 7.6 节 review_and_finalize 注释):
    直接读取 final_cache 返回子图产物, 多报告间一致性检查可作为后续优化.

    Args:
        state: 顶层 DocbotState, 已含 report_tasks
        settings: Settings 实例

    Returns:
        delta dict: {final_reports: list[dict]}
    """
    from src.agents.docbot.final_reviewer import FinalReviewerG

    reviewer = FinalReviewerG(settings)
    report_tasks = state.get("report_tasks", [])
    async with trace_chain(
        name="docbot.final_reviewer_g",
        input={"report_count": len(report_tasks)},
    ) as span:
        final_reports: list[dict] = []
        for task in report_tasks:
            if not isinstance(task, dict):
                continue
            try:
                report = await reviewer.review_and_finalize(
                    report_type=task.get("report_type", ""),
                    final_cache_key=task.get("final_cache_key", ""),
                    all_report_types=state.get("report_types", []),
                    user_id=state.get("user_id", ""),
                    session_id=state.get("session_id", ""),
                    settings=settings,
                )
                # 补充 report_id / download_urls (来自子图 collect_result)
                report["report_id"] = task.get("report_id", "")
                report["download_urls"] = task.get("download_urls", {})
                final_reports.append(report)
            except Exception as e:  # noqa: BLE001
                span.update(metadata={"error": str(e)})
                logger.warning("final_reviewer_g 处理失败 (降级使用子图产物): %s", e)
                # 失败时使用子图原始产物
                final_reports.append(
                    {
                        "report_id": task.get("report_id", ""),
                        "report_type": task.get("report_type", ""),
                        "title": task.get("title", ""),
                        "summary": task.get("summary", ""),
                        "download_urls": task.get("download_urls", {}),
                        "image_svg": task.get("image_svg", ""),
                        "content_md": "",  # 由 save_reports 从缓存读取
                        "final_cache_key": task.get("final_cache_key", ""),
                    }
                )
        span.update(output={"final_count": len(final_reports)})
        return {"final_reports": final_reports}


async def save_reports_node(state: dict, settings: Any | None = None) -> dict:
    """保存最终报告到 Postgres research_reports 表 + 生成多格式下载链接.

    复用从 AIR 拷贝的 ReportStore.save_report() + Publisher.publish() (见 AGENTS.md 第 3 章).
    为 5 种格式 (markdown/html/pdf/docx/json) 各生成一份并保存.

    Args:
        state: 顶层 DocbotState, 已含 final_reports
        settings: Settings 实例

    Returns:
        delta dict: {final_reports: list[dict]} (覆盖, 含 download_urls)
    """
    from src.memory.report_store import ReportStore
    from src.skills.docbot.cache import read_cache
    from src.skills.researcher.publisher import Publisher

    report_store = ReportStore(settings) if settings is not None else ReportStore()
    publisher = Publisher(settings) if settings is not None else Publisher()

    saved: list[dict] = []
    agent_id = state.get("agent_id", "agentinsight-docbot")
    user_id = state.get("user_id", "")
    session_id = state.get("session_id", "")

    async with trace_chain(
        name="docbot.save_reports",
        input={"report_count": len(state.get("final_reports", []))},
    ) as span:
        for report in state.get("final_reports", []):
            if not isinstance(report, dict):
                continue
            report_type = report.get("report_type") or report.get("report_type_label")
            if not report_type:
                continue

            # 从缓存读取最终 markdown 内容 (final_reviewer_g 不在 state 内放全文)
            content_md = report.get("content_md", "")
            if not content_md:
                final_cache_key = report.get("final_cache_key", "")
                if final_cache_key:
                    raw = await read_cache(final_cache_key, settings=settings)
                    if raw:
                        try:
                            parsed = json.loads(raw)
                            if isinstance(parsed, dict):
                                content_md = str(parsed.get("content_md", ""))
                        except (json.JSONDecodeError, TypeError) as e:
                            logger.warning("final_cache JSON 解析失败: %s", e)

            image_svg = report.get("image_svg", "")

            # 生成 5 种格式 (markdown/html/pdf/docx/json)
            download_urls: dict[str, str] = {}
            for fmt in ["markdown", "html", "pdf", "docx", "json"]:
                try:
                    converted = await publisher.publish(
                        content_md,
                        output_format=fmt,
                        title=report.get("title", ""),
                        user_id=user_id,
                        session_id=session_id,
                    )
                    converted_content = converted.get("content", content_md)
                    report_id = await report_store.save_report(
                        session_id=session_id,
                        user_id=user_id,
                        agent_id=agent_id,
                        query=report.get("title", report_type),
                        report_md=str(converted_content) if converted_content else content_md,
                        report_format=fmt,
                        sources=[],
                        agent_role=report_type,
                        report_type_label=report_type,
                        report_summary=report.get("summary", ""),
                        report_image_svg=image_svg,
                    )
                    if report_id:
                        download_urls[fmt] = f"/v1/reports/{report_id}/download?format={fmt}"
                except Exception as e:  # noqa: BLE001
                    logger.warning("格式转换失败 (跳过): fmt=%s, error=%s", fmt, e)

            saved.append(
                {
                    "report_id": report.get("report_id", ""),
                    "report_type": report_type,
                    "title": report.get("title", ""),
                    "summary": report.get("summary", ""),
                    "image_svg": image_svg,
                    "download_urls": download_urls,
                }
            )

        span.update(output={"saved_count": len(saved)})
        return {"final_reports": saved}


__all__ = [
    "coordinator_a_node",
    "final_reviewer_g_node",
    "save_reports_node",
    "spawn_b_tasks_node",
]

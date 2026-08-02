"""docbot 顶层图节点函数 (5 个).

约定 (见 docs/DESIGN_AGENT.md 第 3 章与 AGENTS.md 第 5 章):
- 节点为纯函数: async def node(state, settings) -> dict
- 节点不原地修改 state, 返回 delta dict 由 LangGraph reducer 合并
- 节点不直连厂商 LLM SDK, 统一走 llm/ 网关 (LiteLLM)
- 节点内通过异步上下文管理器包裹 trace (trace_agent / trace_chain)
- settings 通过 functools.partial 在 builder 中注入, 保持节点函数纯函数语义

顶层图节点顺序:
coordinator_a → spawn_b_tasks → final_reviewer_g → save_reports → cleanup_repo → END

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

        # 诊断日志: 派发前置状态
        repo_config = state.get("_repo_config", {})
        repo_url = repo_config.get("repo_url", "") if isinstance(repo_config, dict) else ""
        logger.info(
            "spawn_b_tasks 开始: report_types=%s, repo_id=%s, repo_url=%s, "
            "user_id=%s, session_id=%s, max_concurrent=%d",
            report_types, repo_id, repo_url, user_id, session_id, max_concurrent,
        )
        if not repo_url:
            logger.error(
                "spawn_b_tasks 严重: _repo_config 缺失或 repo_url 为空, "
                "子图 c_code_learning_node 必将失败. repo_config 类型=%s",
                type(repo_config).__name__,
            )

        async def run_one(report_type: str) -> dict:
            async with semaphore:
                logger.info("子图开始执行: report_type=%s, repo_id=%s", report_type, repo_id)
                # 构造子图初始 state (ReportTaskState 全字段)
                sub_state: ReportTaskState = {
                    "report_type": report_type,
                    "report_format": report_format,
                    "language": language,
                    "repo_id": repo_id,
                    "user_id": user_id,
                    "session_id": session_id,
                    "agent_id": agent_id,
                    "_repo_config": state.get("_repo_config", {}),
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
                try:
                    result = await subgraph.ainvoke(sub_state, config=config)
                    result_dict = result if isinstance(result, dict) else {}
                    logger.info(
                        "子图执行完成: report_type=%s, final_cache_key=%s, report_id=%s, "
                        "title=%s, chapters=%d, content_keys=%d, reviewed_keys=%d",
                        report_type,
                        result_dict.get("final_cache_key", ""),
                        result_dict.get("report_id", ""),
                        (result_dict.get("report_title", "") or "")[:50],
                        len(result_dict.get("chapters", [])),
                        len(result_dict.get("content_cache_keys", [])),
                        len(result_dict.get("reviewed_cache_keys", [])),
                    )
                    return result_dict
                except Exception as e:
                    logger.exception(
                        "子图执行抛出异常: report_type=%s, error=%s: %s",
                        report_type, type(e).__name__, e,
                    )
                    raise

        # 并发派发, return_exceptions=True 防止单个失败拖垮全部
        tasks = [run_one(rt) for rt in report_types]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        success_reports: list[dict] = []
        errors: list[str] = []
        for rt, r in zip(report_types, results, strict=True):
            if isinstance(r, Exception):
                # 详细记录异常类型与消息, 便于定位
                err_msg = (
                    f"report_type={rt} failed: {type(r).__name__}: {r}"
                )
                errors.append(err_msg)
                logger.error(
                    "子图失败收集: report_type=%s, exception_type=%s, "
                    "exception_msg=%s",
                    rt, type(r).__name__, str(r)[:500],
                )
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
                logger.info(
                    "子图成功收集: report_type=%s, final_cache_key=%s",
                    rt, r["final_cache_key"],
                )
            else:
                # 缺失 final_cache_key, 记录子图返回的完整 keys 便于诊断
                err_msg = f"report_type={rt} no_final_cache_key"
                errors.append(err_msg)
                logger.error(
                    "子图无 final_cache_key: report_type=%s, "
                    "result_type=%s, result_keys=%s, merged_cache_key=%s, "
                    "code_learning_cache_key=%s",
                    rt,
                    type(r).__name__ if r else "None",
                    list(r.keys()) if isinstance(r, dict) else [],
                    r.get("merged_cache_key", "") if isinstance(r, dict) else "",
                    r.get("code_learning_cache_key", "") if isinstance(r, dict) else "",
                )

        span.update(
            output={
                "success_count": len(success_reports),
                "error_count": len(errors),
            }
        )
        logger.info(
            "spawn_b_tasks 完成: success_count=%d, error_count=%d, errors=%s",
            len(success_reports), len(errors), errors,
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

    对齐 AIR (researcher) 的单行存储策略:
    - 仅保存 1 行 Markdown 原文 (report_format='markdown')
    - 下载端点 /v1/reports/{report_id}/download?format=xxx 按需实时转换
    - download_urls 为 5 种格式生成链接, 均指向同一 report_id

    优势 (相比原 5 行预转换方案):
    - 消除 JSON 双层包装 (原 json 格式入库时包装一次, 下载时再包装一次)
    - 消除 DOCX str(bytes) 乱码 (原 docx 入库存 bytes 字符串表示)
    - 消除 HTML 二次转换破损 (原 html 入库已转 HTML, 下载又当 Markdown 转)
    - 节省 80% 存储空间 (5 行 → 1 行)

    Args:
        state: 顶层 DocbotState, 已含 final_reports
        settings: Settings 实例

    Returns:
        delta dict: {final_reports: list[dict]} (覆盖, 含 download_urls)
    """
    from src.memory.report_store import ReportStore
    from src.skills.docbot.cache import read_cache

    report_store = ReportStore(settings) if settings is not None else ReportStore()

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

            # 单行 Markdown 入库 (对齐 AIR 策略, 下载端点按需转换)
            report_id = await report_store.save_report(
                session_id=session_id,
                user_id=user_id,
                agent_id=agent_id,
                query=report.get("title", report_type),
                report_md=content_md,  # 纯 Markdown, 不做格式转换
                report_format="markdown",
                sources=[],
                agent_role=report_type,
                report_type_label=report_type,
                report_summary=report.get("summary", ""),
                report_image_svg=image_svg,
            )

            # 5 种格式下载链接均指向同一 report_id (下载端点按需转换)
            download_urls: dict[str, str] = {}
            if report_id:
                for fmt in ["markdown", "html", "pdf", "docx", "json"]:
                    download_urls[fmt] = f"/v1/reports/{report_id}/download?format={fmt}"

            saved.append(
                {
                    "report_id": report_id or "",
                    "report_type": report_type,
                    "title": report.get("title", ""),
                    "summary": report.get("summary", ""),
                    "image_svg": image_svg,
                    "download_urls": download_urls,
                    "content_md": content_md,  # 保留供 API 响应直接返回
                }
            )

        span.update(output={"saved_count": len(saved)})

        # 成功入库后立即扣减每日限额 (与持久化同节点, 避免 SSE 断连导致 routes 层漏计)
        # daily_usage_charged=True 时 routes 层跳过二次扣减
        daily_usage_charged = False
        if saved and user_id and agent_id:
            try:
                from src.api.ip_user_resolver import increment_daily_report_count

                await increment_daily_report_count(
                    user_id, agent_id, delta=len(saved)
                )
                daily_usage_charged = True
            except Exception as usage_err:  # noqa: BLE001
                logger.warning(
                    "save_reports 每日文档计数递增失败 (user=%s, agent=%s, delta=%d): %s",
                    user_id,
                    agent_id,
                    len(saved),
                    usage_err,
                    exc_info=True,
                )

        # P1-5.3.2: 文档生成成功后, 更新 last_doc_commit_hash 供下次漂移检测
        # 不阻断主流程, 失败仅记录日志
        if saved:
            try:
                await _update_repo_doc_commit_hash(state=state, settings=settings, span=span)
            except Exception as commit_err:  # noqa: BLE001
                logger.warning(
                    "更新 last_doc_commit_hash 失败 (不阻断主流程): %s",
                    commit_err,
                )

        return {
            "final_reports": saved,
            "daily_usage_charged": daily_usage_charged,
        }


async def _update_repo_doc_commit_hash(
    *,
    state: dict,
    settings: Any | None,
    span: Any,
) -> None:
    """P1-5.3.2: 文档生成成功后更新 user_git_repos.last_doc_commit_hash.

    获取当前仓库 HEAD commit hash, 写入 user_git_repos,
    供下次同步时的 detect_doc_drift 对比检测文档漂移.
    """
    from src.memory.db_initializer import get_pool
    from src.skills.docbot.drift_detector import update_last_doc_commit
    from src.tools.git_mcp import get_git_mcp_adapter

    repo_id = state.get("repo_id", "")
    user_id = state.get("user_id", "")
    agent_id = state.get("agent_id", "agentinsight-docbot")
    if not repo_id or not user_id:
        return

    adapter = get_git_mcp_adapter()
    repo_path = adapter._repo_path(user_id, repo_id)
    if not repo_path.exists():
        logger.warning(
            "更新 last_doc_commit_hash 跳过: 仓库目录不存在 (repo_id=%s)",
            repo_id,
        )
        return

    try:
        commit_hash = await adapter.get_head_commit_hash(str(repo_path))
    except Exception as e:  # noqa: BLE001
        logger.warning("获取 HEAD commit hash 失败 (跳过更新 last_doc_commit_hash): %s", e)
        return

    pool = await get_pool()
    await update_last_doc_commit(
        pool=pool,
        repo_id=repo_id,
        user_id=user_id,
        agent_id=agent_id,
        commit_hash=commit_hash,
    )
    span.update(metadata={"last_doc_commit_hash": commit_hash[:12]})


async def cleanup_repo_node(state: dict, settings: Any | None = None) -> dict:
    """文档生成完成后删除克隆目录 (任务3要求: 按需下载, 完成后删除).

    在 save_reports 之后执行, 清理 temp/repos/{user_id}/{repo_id}/ 目录,
    避免克隆仓库在磁盘上长期堆积. 失败不阻断主流程.

    Args:
        state: 顶层 DocbotState, 含 user_id / repo_id
        settings: Settings 实例 (未使用, 保留以保持节点函数签名一致)

    Returns:
        空 dict (不修改 state)
    """
    import asyncio
    import shutil

    from src.tools.git_mcp import get_git_mcp_adapter

    user_id = state.get("user_id", "")
    repo_id = state.get("repo_id", "")
    if not user_id or not repo_id:
        return {}

    async with trace_chain(
        name="docbot.cleanup_repo",
        input={"repo_id": repo_id, "user_id": user_id},
    ) as span:
        try:
            adapter = get_git_mcp_adapter()
            repo_path = adapter._repo_path(user_id, repo_id)
            if repo_path.exists():
                await asyncio.to_thread(shutil.rmtree, repo_path, ignore_errors=True)
                logger.info("已清理仓库克隆目录: %s", repo_path)
                span.update(output={"cleaned": True, "repo_path": str(repo_path)})
            else:
                span.update(output={"cleaned": False, "reason": "not_exist"})
        except Exception as e:  # noqa: BLE001
            logger.warning("清理仓库克隆目录失败 (不阻断主流程): %s", e)
            span.update(output={"cleaned": False, "error": str(e)})

    return {}


__all__ = [
    "cleanup_repo_node",
    "coordinator_a_node",
    "final_reviewer_g_node",
    "save_reports_node",
    "spawn_b_tasks_node",
]

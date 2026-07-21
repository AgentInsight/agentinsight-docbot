"""docbot 报告子图节点函数 (7 个).

约定 (见 docs/DESIGN_AGENT.md 第 4 章与 AGENTS.md 第 5 章):
- 节点为纯函数: async def node(state, settings) -> dict
- 节点不原地修改 state, 返回 delta dict 由 LangGraph reducer 合并
- 6 步流水线中间产物体积可能达数百 KB, 不直接放入 state;
  state 仅存 cache_key, 实际内容存 Redis (TTL 24 小时)
- 节点通过 read_cache / write_cache 与 Redis 交互 (函数式 API, 见 skills.docbot.cache)
- settings 通过 functools.partial 在 builder 中注入

报告子图节点顺序 (带 D-E 循环):
b_init_session → c_code_learning → c_outline_refine → d_content_fill
    ↕ (D-E 循环, max_revisions_per_chapter=3)
e_review → f_merge → g_final_in_subgraph → END

import 路径约定: 用绝对导入 (不是 from src.graph...).
"""

from __future__ import annotations

import json
import logging
from typing import Any

from src.observability.tracing import trace_chain
from src.skills.docbot.cache import build_cache_key, read_cache, write_cache

logger = logging.getLogger(__name__)


async def b_init_session_node(state: dict, settings: Any | None = None) -> dict:
    """任务一前置: 为该报告任务创建独立 LLM 会话 ID + report_id.

    后续所有 LLM 调用都基于这个 llm_session_id (用于 LLM 服务端会话保持 + 上下文复用).
    report_id 供顶层图 save_reports 节点引用.

    Args:
        state: ReportTaskState (dict 形式)
        settings: Settings 实例

    Returns:
        delta dict: {llm_session_id, report_id, max_revisions_per_chapter}
    """
    from src.agents.docbot.report_runner import ReportRunnerB

    report_type = state.get("report_type", "unknown")
    runner = ReportRunnerB(settings)
    async with trace_chain(
        name=f"docbot.report.{report_type}.b_init",
        input={"report_type": report_type},
    ):
        return await runner.run(state, settings=settings)


async def c_code_learning_node(state: dict, settings: Any | None = None) -> dict:
    """任务一: STRATEGIC LLM 深度学习用户代码仓库.

    职责:
    1. 通过 GitMCPAdapter 克隆 / 拉取仓库
    2. 枚举所有文件, 构建文件索引
    3. 对关键文件 (README/入口文件/配置文件/核心模块) 逐文件学习
    4. 输出结构化学习摘要: {summary, file_index, key_modules, dependencies, architecture_notes}
    5. 写入 Redis 缓存 (TTL 24h, 由 settings.docbot_cache_ttl 控制)
    6. 缓存命中检测 (同 session 同 repo 复用)

    Args:
        state: ReportTaskState
        settings: Settings 实例

    Returns:
        delta dict: {code_learning_cache_key}
    """
    from src.skills.docbot.code_learner import learn_code

    agent_id = state.get("agent_id", "agentinsight-docbot")
    user_id = state.get("user_id", "")
    session_id = state.get("session_id", "")
    repo_id = state.get("repo_id", "")
    report_type = state.get("report_type", "")
    llm_session_id = state.get("llm_session_id", "")

    cache_key = build_cache_key(
        agent_id=agent_id,
        user_id=user_id,
        session_id=session_id,
        type_="code_learning",
        report_type=report_type,
    )

    # 缓存命中检测 (同 session 同 repo 复用)
    cached = await read_cache(cache_key, settings=settings)
    if cached:
        logger.info("code_learning 缓存命中, 复用: %s", cache_key)
        return {"code_learning_cache_key": cache_key}

    # 仓库配置从 user_git_repos 表查询 (这里通过 repo_id 反查)
    # 节点函数不直接查 DB (避免循环依赖), 由 skills.docbot.code_learner 内部处理
    # 实际部署时, 调用方应在 state 内注入 repo_config 或由 code_learner 内部 fetch
    repo_config = state.get("_repo_config") or {"repo_url": "", "auth_type": "none"}

    learning_result = await learn_code(
        repo_config=repo_config,
        repo_id=repo_id,
        user_id=user_id,
        report_type=report_type,
        llm_session_id=llm_session_id,
        settings=settings,
    )

    # 写入 Redis 缓存 (JSON 序列化)
    await write_cache(
        cache_key,
        json.dumps(learning_result, ensure_ascii=False),
        settings=settings,
    )
    return {"code_learning_cache_key": cache_key}


async def c_outline_refine_node(state: dict, settings: Any | None = None) -> dict:
    """任务二: 基于默认大纲 + 代码上下文, STRATEGIC LLM 细化报告纲要.

    职责:
    1. 读取 code_learning_cache
    2. 通过 config.docbot.outlines.load_outline(report_type) 加载默认大纲
    3. STRATEGIC LLM 根据代码上下文细化大纲 (增删改章节)
    4. 输出 chapters: [{idx, title, sections, key_points}]
    5. 写入 outline_cache

    Args:
        state: ReportTaskState
        settings: Settings 实例

    Returns:
        delta dict: {outline_cache_key, chapters, current_chapter_idx}
    """
    from src.agents.docbot.outline_refiner import OutlineRefinerC

    agent_id = state.get("agent_id", "agentinsight-docbot")
    user_id = state.get("user_id", "")
    session_id = state.get("session_id", "")
    report_type = state.get("report_type", "")
    language = state.get("language", "zh")
    llm_session_id = state.get("llm_session_id", "")
    code_learning_cache_key = state.get("code_learning_cache_key", "")

    # 读取任务一产物 (从 Redis)
    code_learning: dict = {}
    if code_learning_cache_key:
        raw = await read_cache(code_learning_cache_key, settings=settings)
        if raw:
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, dict):
                    code_learning = parsed
            except (json.JSONDecodeError, TypeError) as e:
                logger.warning("code_learning_cache JSON 解析失败: %s", e)

    # 调用 OutlineRefinerC 细化纲要
    refiner = OutlineRefinerC(settings)
    outline = await refiner.refine_outline(
        code_learning=code_learning,
        report_type=report_type,
        language=language,
        llm_session_id=llm_session_id,
        settings=settings,
    )

    # 写入 outline_cache
    outline_cache_key = build_cache_key(
        agent_id=agent_id,
        user_id=user_id,
        session_id=session_id,
        type_="outline",
        report_type=report_type,
    )
    await write_cache(
        outline_cache_key,
        json.dumps(outline, ensure_ascii=False),
        settings=settings,
    )
    return {
        "outline_cache_key": outline_cache_key,
        "chapters": outline.get("chapters", []),
        "current_chapter_idx": 0,
    }


async def d_content_fill_node(state: dict, settings: Any | None = None) -> dict:
    """任务三: D 按章节顺序填充内容 (每次调用处理 current_chapter_idx 对应章节).

    职责:
    1. 读取 outline_cache + code_learning_cache
    2. 取当前章节 chapters[current_chapter_idx]
    3. RAG 检索 (BM25 + Vector + RRF + 可选 Rerank), namespace 按 user_id + repo_id 隔离
    4. SMART LLM 填充章节内容 (markdown 格式)
    5. 按需生成 SVG 配图 (使用从 AIR 拷贝的 ImageGenerator)
    6. 写入 content_cache_keys[current_chapter_idx]
    7. current_chapter_idx += 1

    Args:
        state: ReportTaskState
        settings: Settings 实例

    Returns:
        delta dict: {content_cache_keys: [key], current_chapter_idx: idx+1}
        所有章节已填充完毕时返回 {} (由 route_after_d 路由到 e_review)
    """
    from src.agents.docbot.content_filler import ContentFillerD

    agent_id = state.get("agent_id", "agentinsight-docbot")
    user_id = state.get("user_id", "")
    session_id = state.get("session_id", "")
    report_type = state.get("report_type", "")
    language = state.get("language", "zh")
    repo_id = state.get("repo_id", "")
    llm_session_id = state.get("llm_session_id", "")

    chapters = state.get("chapters", [])
    idx = state.get("current_chapter_idx", 0)
    if idx >= len(chapters):
        # 所有章节已填充完毕, 流转到 f_merge (由 route_after_d 控制)
        return {}

    chapter = chapters[idx]
    if not isinstance(chapter, dict):
        logger.warning("章节 %d 不是 dict, 跳过", idx)
        return {"current_chapter_idx": idx + 1}

    # 读取 code_learning_cache
    code_learning: dict = {}
    code_learning_cache_key = state.get("code_learning_cache_key", "")
    if code_learning_cache_key:
        raw = await read_cache(code_learning_cache_key, settings=settings)
        if raw:
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, dict):
                    code_learning = parsed
            except (json.JSONDecodeError, TypeError) as e:
                logger.warning("code_learning_cache JSON 解析失败: %s", e)

    # 调用 ContentFillerD 填充章节
    filler = ContentFillerD(settings)
    chapter_result = await filler.fill_chapter(
        chapter=chapter,
        code_learning=code_learning,
        report_type=report_type,
        language=language,
        repo_id=repo_id,
        user_id=user_id,
        llm_session_id=llm_session_id,
        settings=settings,
    )

    # 写入 content_cache
    content_cache_key = build_cache_key(
        agent_id=agent_id,
        user_id=user_id,
        session_id=session_id,
        type_="content",
        report_type=report_type,
        chapter_idx=idx,
    )
    await write_cache(
        content_cache_key,
        json.dumps(chapter_result, ensure_ascii=False),
        settings=settings,
    )
    return {
        "content_cache_keys": [content_cache_key],
        "current_chapter_idx": idx + 1,
    }


async def e_review_node(state: dict, settings: Any | None = None) -> dict:
    """任务四: E 评审 D 填充的章节内容.

    职责:
    1. 读取 content_cache_keys[current_chapter_idx - 1] (D 已 +1)
    2. SMART LLM 评审 (覆盖度 / 准确性 / 代码路径引用 / 完整性)
    3. 输出评审建议 + 修订后的内容
    4. 写入 reviewed_cache_keys
    5. 与 D 形成修订循环 (max_revisions_per_chapter=3 控制硬上限)

    Args:
        state: ReportTaskState
        settings: Settings 实例

    Returns:
        delta dict: {reviewed_cache_keys: [key], revision_count: 1}
    """
    from src.agents.docbot.reviewer import ReviewerE

    agent_id = state.get("agent_id", "agentinsight-docbot")
    user_id = state.get("user_id", "")
    session_id = state.get("session_id", "")
    report_type = state.get("report_type", "")
    language = state.get("language", "zh")
    llm_session_id = state.get("llm_session_id", "")

    chapters = state.get("chapters", [])
    content_cache_keys = state.get("content_cache_keys", [])
    # D 已 +1, E 处理上一个章节
    idx = state.get("current_chapter_idx", 0) - 1
    if idx < 0 or idx >= len(content_cache_keys) or idx >= len(chapters):
        return {}

    content_key = content_cache_keys[idx]
    content_raw = await read_cache(content_key, settings=settings)
    content_data: dict = {}
    if content_raw:
        try:
            parsed = json.loads(content_raw)
            if isinstance(parsed, dict):
                content_data = parsed
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning("content_cache JSON 解析失败: %s", e)

    # 读取 code_learning_cache
    code_learning: dict = {}
    code_learning_cache_key = state.get("code_learning_cache_key", "")
    if code_learning_cache_key:
        raw = await read_cache(code_learning_cache_key, settings=settings)
        if raw:
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, dict):
                    code_learning = parsed
            except (json.JSONDecodeError, TypeError) as e:
                logger.warning("code_learning_cache JSON 解析失败: %s", e)

    # 计算当前修订轮次 (用于强制通过避免无限循环)
    max_revisions = state.get("max_revisions_per_chapter", 3)
    revision_count = state.get("revision_count", 0)
    revision_round = (revision_count % max_revisions) + 1

    chapter = chapters[idx]
    reviewer = ReviewerE(settings)
    reviewed = await reviewer.review_chapter(
        chapter=chapter,
        content=content_data,
        code_learning=code_learning,
        report_type=report_type,
        language=language,
        llm_session_id=llm_session_id,
        settings=settings,
        revision_round=revision_round,
        max_revisions=max_revisions,
    )

    reviewed_key = build_cache_key(
        agent_id=agent_id,
        user_id=user_id,
        session_id=session_id,
        type_="reviewed",
        report_type=report_type,
        chapter_idx=idx,
    )
    await write_cache(
        reviewed_key,
        json.dumps(reviewed, ensure_ascii=False),
        settings=settings,
    )
    return {
        "reviewed_cache_keys": [reviewed_key],
        "revision_count": 1,  # operator.add 累积修订次数
    }


async def f_merge_node(state: dict, settings: Any | None = None) -> dict:
    """任务五: F 合并所有 reviewed_cache_keys 内容, SMART LLM 去重.

    Args:
        state: ReportTaskState
        settings: Settings 实例

    Returns:
        delta dict: {merged_cache_key}
    """
    from src.agents.docbot.merger import MergerF

    agent_id = state.get("agent_id", "agentinsight-docbot")
    user_id = state.get("user_id", "")
    session_id = state.get("session_id", "")
    report_type = state.get("report_type", "")
    language = state.get("language", "zh")
    llm_session_id = state.get("llm_session_id", "")
    chapters = state.get("chapters", [])
    reviewed_cache_keys = state.get("reviewed_cache_keys", [])

    # 读取所有 reviewed_cache
    reviewed_data: list[dict] = []
    for key in reviewed_cache_keys:
        raw = await read_cache(key, settings=settings)
        if raw:
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, dict):
                    reviewed_data.append(parsed)
            except (json.JSONDecodeError, TypeError) as e:
                logger.warning("reviewed_cache JSON 解析失败 (跳过): %s", e)

    # 调用 MergerF 合并
    merger = MergerF(settings)
    merged = await merger.merge_chapters(
        reviewed_chapters=reviewed_data,
        chapters=chapters,
        report_type=report_type,
        language=language,
        llm_session_id=llm_session_id,
        settings=settings,
    )

    merged_key = build_cache_key(
        agent_id=agent_id,
        user_id=user_id,
        session_id=session_id,
        type_="merged",
        report_type=report_type,
    )
    await write_cache(
        merged_key,
        json.dumps(merged, ensure_ascii=False),
        settings=settings,
    )
    return {"merged_cache_key": merged_key}


async def g_final_in_subgraph_node(state: dict, settings: Any | None = None) -> dict:
    """任务六: G 子图内终审 merged_cache, 输出 final_cache.

    与顶层图 final_reviewer_g 区别 (见 docs/DESIGN_AGENT.md 第 4.7 节):
    - 此节点处理单个报告的终审 (SMART LLM 输出 JSON: title/summary/content_md)
    - 顶层图 final_reviewer_g 处理多报告间的交叉一致性

    Args:
        state: ReportTaskState
        settings: Settings 实例

    Returns:
        delta dict: {final_cache_key, report_title, report_summary, report_image_svg}
    """
    from src.agents.docbot.final_reviewer import FinalReviewerG

    agent_id = state.get("agent_id", "agentinsight-docbot")
    user_id = state.get("user_id", "")
    session_id = state.get("session_id", "")
    report_type = state.get("report_type", "")
    language = state.get("language", "zh")
    llm_session_id = state.get("llm_session_id", "")
    merged_cache_key = state.get("merged_cache_key", "")
    code_learning_cache_key = state.get("code_learning_cache_key", "")

    # 读取 merged_cache
    merged: dict = {}
    if merged_cache_key:
        raw = await read_cache(merged_cache_key, settings=settings)
        if raw:
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, dict):
                    merged = parsed
            except (json.JSONDecodeError, TypeError) as e:
                logger.warning("merged_cache JSON 解析失败: %s", e)

    # 读取 code_learning_cache
    code_learning: dict = {}
    if code_learning_cache_key:
        raw = await read_cache(code_learning_cache_key, settings=settings)
        if raw:
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, dict):
                    code_learning = parsed
            except (json.JSONDecodeError, TypeError) as e:
                logger.warning("code_learning_cache JSON 解析失败: %s", e)

    # 调用 FinalReviewerG 终审
    reviewer = FinalReviewerG(settings)
    final_doc = await reviewer.finalize_single_report(
        report_type=report_type,
        language=language,
        merged=merged,
        code_learning=code_learning,
        llm_session_id=llm_session_id,
        settings=settings,
    )

    # 写入 final_cache
    final_key = build_cache_key(
        agent_id=agent_id,
        user_id=user_id,
        session_id=session_id,
        type_="final",
        report_type=report_type,
    )
    await write_cache(
        final_key,
        json.dumps(final_doc, ensure_ascii=False),
        settings=settings,
    )

    # 提取首张 SVG (report_image_svg 字段, 供顶层图 spawn_b_tasks 收集)
    image_svgs = final_doc.get("image_svgs", [])
    report_image_svg = image_svgs[0] if isinstance(image_svgs, list) and image_svgs else ""

    return {
        "final_cache_key": final_key,
        "report_title": final_doc.get("title", ""),
        "report_summary": final_doc.get("summary", ""),
        "report_image_svg": report_image_svg,
    }


__all__ = [
    "b_init_session_node",
    "c_code_learning_node",
    "c_outline_refine_node",
    "d_content_fill_node",
    "e_review_node",
    "f_merge_node",
    "g_final_in_subgraph_node",
]

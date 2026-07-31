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

# ContentFillerD 实例缓存 (key = "{agent_id}:{session_id}:{report_type}")
# 跨 d_content_fill_node 调用复用同一实例, 使 _dedup_compressor 的
# _written_embeddings 跨章节累积, 实现章节级语义去重 (P0 优化).
# 子图所有章节处理完毕后清理缓存, 避免内存泄漏.
_filler_cache: dict[str, Any] = {}


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

    logger.info(
        "c_code_learning 开始: report_type=%s, repo_id=%s, user_id=%s, "
        "session_id=%s, llm_session_id=%s",
        report_type,
        repo_id,
        user_id,
        session_id,
        llm_session_id,
    )

    cache_key = build_cache_key(
        agent_id=agent_id,
        user_id=user_id,
        session_id=session_id,
        type_="code_learning",
        report_type=report_type,
        repo_id=repo_id,
    )

    # 缓存命中检测 (同 session 同 repo 复用)
    cached = await read_cache(cache_key, settings=settings)
    if cached:
        logger.info("code_learning 缓存命中, 复用: %s", cache_key)
        return {"code_learning_cache_key": cache_key}

    # 仓库配置由 coordinator_a 从 DB 加载并解密后注入 state (按需下载机制, 任务3)
    repo_config = state.get("_repo_config")
    if not repo_config or not repo_config.get("repo_url"):
        # 诊断: 详细记录缺失原因
        config_type = type(repo_config).__name__ if repo_config else "None"
        repo_url_val = repo_config.get("repo_url", "") if isinstance(repo_config, dict) else ""
        config_keys = list(repo_config.keys()) if isinstance(repo_config, dict) else []
        logger.error(
            "c_code_learning 失败: missing_repo_config. report_type=%s, "
            "repo_id=%s, config_type=%s, repo_url=%r, config_keys=%s. "
            "请检查 coordinator_a_node 是否成功加载仓库配置.",
            report_type,
            repo_id,
            config_type,
            repo_url_val,
            config_keys,
        )
        return {"errors": ["missing_repo_config"]}

    # 诊断: 记录 repo_config 关键字段 (脱敏, 不记录 token/password/ssh_key)
    safe_config = {
        "repo_url": repo_config.get("repo_url", ""),
        "auth_type": repo_config.get("auth_type", "none"),
        "default_branch": repo_config.get("default_branch", ""),
        "clone_depth": repo_config.get("clone_depth", 0),
        "has_token": bool(repo_config.get("token")),
        "has_password": bool(repo_config.get("password")),
        "has_ssh_key": bool(repo_config.get("ssh_key")),
    }
    logger.info("c_code_learning repo_config: %s", safe_config)

    try:
        learning_result = await learn_code(
            repo_config=repo_config,
            repo_id=repo_id,
            user_id=user_id,
            report_type=report_type,
            llm_session_id=llm_session_id,
            settings=settings,
        )
    except Exception as e:
        logger.exception(
            "c_code_learning learn_code 抛出异常: report_type=%s, repo_id=%s, error=%s: %s",
            report_type,
            repo_id,
            type(e).__name__,
            e,
        )
        return {"errors": [f"code_learning_failed: {type(e).__name__}: {e}"]}

    # 诊断: 记录学习结果关键字段
    logger.info(
        "c_code_learning learn_code 完成: report_type=%s, summary_length=%d, "
        "key_modules=%d, dependencies=%d, file_count=%d, repo_path=%s",
        report_type,
        len(learning_result.get("summary", "")),
        len(learning_result.get("key_modules", [])),
        len(learning_result.get("dependencies", [])),
        learning_result.get("file_index", {}).get("file_count", 0),
        learning_result.get("repo_path", ""),
    )

    # 写入 Redis 缓存 (JSON 序列化)
    try:
        await write_cache(
            cache_key,
            json.dumps(learning_result, ensure_ascii=False),
            settings=settings,
        )
    except Exception as e:
        logger.exception(
            "c_code_learning write_cache 失败: cache_key=%s, error=%s: %s",
            cache_key,
            type(e).__name__,
            e,
        )
        return {"errors": [f"write_cache_failed: {type(e).__name__}: {e}"]}

    # P0-3: 自动触发 Qdrant 索引 (若该仓库未索引, 报告流水线后续 d_content_fill 会无 RAG 数据)
    # 失败不阻断主流程, 仅 warning; d_content_fill 降级从 file_index 直接检索
    repo_path = learning_result.get("repo_path", "")
    if repo_path:
        try:
            await _ensure_qdrant_indexed(
                repo_path=repo_path,
                repo_id=repo_id,
                user_id=user_id,
                agent_id=agent_id,
                settings=settings,
            )
        except Exception as e:
            logger.warning(
                "c_code_learning 自动索引 Qdrant 失败 (不阻断, repo_id=%s): %s: %s",
                repo_id,
                type(e).__name__,
                e,
            )

    logger.info("c_code_learning 完成: cache_key=%s", cache_key)
    return {"code_learning_cache_key": cache_key}


async def _ensure_qdrant_indexed(
    repo_path: str,
    repo_id: str,
    user_id: str,
    agent_id: str,
    settings: Any | None,
) -> None:
    """P0-3: 检查 Qdrant 是否已索引该仓库, 未索引则自动触发.

    失败仅 warning, 不阻断主流程 (d_content_fill 降级从 file_index 检索).
    """
    from src.rag.qdrant_manager import QdrantManager
    from src.skills.docbot.repo_loader import index_repo_to_qdrant

    try:
        qdrant_mgr = QdrantManager(settings)
        has_repo_data = await qdrant_mgr.has_repo_data(user_id, repo_id)
    except Exception as e:
        logger.warning(
            "Qdrant has_repo_data 检查失败 (跳过自动索引, repo_id=%s): %s: %s",
            repo_id,
            type(e).__name__,
            e,
        )
        return

    if has_repo_data:
        logger.info("Qdrant 已索引仓库 %s, 跳过自动索引", repo_id)
        return

    logger.info("Qdrant 未索引仓库 %s, 自动触发索引 (P0-3)", repo_id)
    try:
        result = await index_repo_to_qdrant(
            repo_path=repo_path,
            user_id=user_id,
            repo_id=repo_id,
            agent_id=agent_id,
            settings=settings,
        )
        indexed_count = result.get("indexed_count", 0)
        errors = result.get("errors", [])
        logger.info(
            "Qdrant 自动索引完成: repo_id=%s, indexed_count=%d, errors=%d",
            repo_id,
            indexed_count,
            len(errors),
        )
        if errors:
            logger.warning(
                "Qdrant 自动索引部分失败 (不阻断): 前3个错误=%s",
                errors[:3],
            )
    except Exception as e:
        logger.warning(
            "Qdrant 自动索引失败 (不阻断, repo_id=%s): %s: %s",
            repo_id,
            type(e).__name__,
            e,
        )


async def c_outline_refine_node(state: dict, settings: Any | None = None) -> dict:
    """任务二: STRATEGIC LLM 基于 code_learning + AGENTS.md/README.md 优化纲要.

    职责 (P0-1 恢复纲要细化, 修复幻觉引用根源):
    1. 读取 code_learning_cache (任务一产物, 含 summary/key_modules/dependencies/architecture_notes)
    2. 加载默认大纲 outlines/{report_type}.yaml (作为参考基础)
    3. 读取目标仓库 AGENTS.md (优先) + README.md (次选) 作为产品定位 ground truth
    4. 调用 OutlineRefinerC.refine_outline() 由 STRATEGIC LLM 优化纲要
       - 删除不适用章节 (无证据的 conditional 章必须 removed)
       - 增加必要章节 (endpoints/key_modules 揭示但默认纲要缺失的模块)
       - 替换硬编码通用示例为代码中的真实路径/实体/认证/错误码
    5. 校验优化后纲要 (章节数 ≤ max_chapters, 保留引言和附录)
    6. 写入 outline_cache + state.chapters
    7. 初始化 current_chapter_idx=0 和 review_idx=0

    Args:
        state: ReportTaskState
        settings: Settings 实例

    Returns:
        delta dict: {chapters, current_chapter_idx, review_idx, outline_cache_key?}
    """
    from src.agents.docbot.outline_refiner import OutlineRefinerC
    from src.config.docbot.outlines import load_outline

    agent_id = state.get("agent_id", "agentinsight-docbot")
    user_id = state.get("user_id", "")
    session_id = state.get("session_id", "")
    report_type = state.get("report_type", "")
    language = state.get("language", "zh")
    llm_session_id = state.get("llm_session_id", "")
    repo_id = state.get("repo_id", "")

    logger.info("c_outline_refine 开始: report_type=%s", report_type)

    # 1. 读取 code_learning_cache
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

    if not code_learning:
        # 硬约束: 无代码学习结果时禁止原样输出默认 YAML
        logger.error(
            "c_outline_refine: code_learning 为空, 拒绝使用默认 YAML 原样输出 "
            "(report_type=%s). 请先修复 code_learning 失败原因.",
            report_type,
        )
        return {
            "chapters": [],
            "current_chapter_idx": 0,
            "review_idx": 0,
            "errors": ["code_learning_empty_outline_blocked"],
        }

    # 2. 读取目标仓库 AGENTS.md / README.md (作为 ground truth)
    repo_path = code_learning.get("repo_path", "")
    agents_md = _read_repo_doc(repo_path, "AGENTS.md")
    readme_md = _read_repo_doc(repo_path, "README.md") if not agents_md else ""

    # 3. 加载默认大纲 (作为参考基础, 传给 refine_outline)
    default_outline = load_outline(report_type)

    # 4. 调用 OutlineRefinerC 优化纲要
    refiner = OutlineRefinerC(settings)
    try:
        refined = await refiner.refine_outline(
            code_learning=code_learning,
            report_type=report_type,
            language=language,
            llm_session_id=llm_session_id,
            settings=settings,
            default_outline=default_outline,
            agents_md=agents_md,
            readme_md=readme_md,
        )
    except Exception as e:
        logger.exception(
            "c_outline_refine 失败, 降级使用默认大纲 (report_type=%s): %s: %s",
            report_type,
            type(e).__name__,
            e,
        )
        return {
            "chapters": default_outline,
            "current_chapter_idx": 0,
            "review_idx": 0,
        }

    chapters = refined.get("chapters", [])
    if not chapters:
        logger.warning(
            "c_outline_refine: 优化后大纲为空, 降级使用默认大纲 (report_type=%s)",
            report_type,
        )
        chapters = default_outline

    # 5. 写入 outline_cache (供后续节点复用)
    outline_cache_key = build_cache_key(
        agent_id=agent_id,
        user_id=user_id,
        session_id=session_id,
        type_="outline",
        report_type=report_type,
        repo_id=repo_id,
    )
    try:
        await write_cache(
            outline_cache_key,
            json.dumps(refined, ensure_ascii=False),
            settings=settings,
        )
    except Exception as e:
        logger.warning("outline_cache 写入失败 (不阻断): %s: %s", type(e).__name__, e)

    logger.info(
        "c_outline_refine 完成: report_type=%s, chapters=%d, refine_summary=%s",
        report_type,
        len(chapters),
        refined.get("refine_summary", "")[:200],
    )

    return {
        "chapters": chapters,
        "current_chapter_idx": 0,
        "review_idx": 0,
        "outline_cache_key": outline_cache_key,
    }


def _read_repo_doc(repo_path: str, filename: str) -> str:
    """读取目标仓库根目录的文档文件 (AGENTS.md / README.md), 失败返回空字符串.

    P0-1: 作为产品定位 ground truth, 优先级 AGENTS.md > README.md.
    截断到 20_000 字符防止 token 溢出.
    """
    if not repo_path:
        return ""
    import os

    # 尝试多个候选路径 (根目录 / docs/ 子目录)
    candidates = [
        os.path.join(repo_path, filename),
        os.path.join(repo_path, "docs", filename),
        os.path.join(repo_path, filename.upper()),
        os.path.join(repo_path, filename.lower()),
    ]
    for path in candidates:
        try:
            if os.path.isfile(path):
                with open(path, encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    if content:
                        return content[:20_000]
        except OSError as e:
            logger.debug("读取 %s 失败: %s", path, e)
            continue
    return ""


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
        # 所有章节已填充完毕, 清理 ContentFillerD 缓存 (释放 _dedup_compressor 内存)
        # 并流转到 f_merge (由 route_after_d 控制)
        filler_cache_key = f"{agent_id}:{session_id}:{report_type}"
        _filler_cache.pop(filler_cache_key, None)
        return {}

    chapter = chapters[idx]
    if not isinstance(chapter, dict):
        # 章节无效时写入空内容占位, 保持 content_cache_keys 与 chapters 索引一致
        logger.warning("章节 %d 不是 dict, 写入空内容占位", idx)
        placeholder_key = build_cache_key(
            agent_id=agent_id,
            user_id=user_id,
            session_id=session_id,
            type_="content",
            report_type=report_type,
            chapter_idx=idx,
            repo_id=repo_id,
        )
        placeholder_result = {
            "chapter_idx": idx,
            "content_md": "## 章节内容缺失\n\n本章节定义无效, 无法填充内容.",
            "image_svgs": [],
        }
        await write_cache(
            placeholder_key,
            json.dumps(placeholder_result, ensure_ascii=False),
            settings=settings,
        )
        return {
            "content_cache_keys": [placeholder_key],
            "current_chapter_idx": idx + 1,
        }

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

    # 调用 ContentFillerD 填充章节 (P0: 复用同一实例, 使 _dedup_compressor
    # 跨 fill_chapter 调用累积 _written_embeddings, 实现章节级语义去重)
    filler_cache_key = f"{agent_id}:{session_id}:{report_type}"
    filler = _filler_cache.get(filler_cache_key)
    if filler is None:
        filler = ContentFillerD(settings)
        _filler_cache[filler_cache_key] = filler
    # P0-5: 传入 file_index 供生成期引用校验 (含 files[].path 集合)
    file_index = code_learning.get("file_index") if isinstance(code_learning, dict) else None
    chapter_result = await filler.fill_chapter(
        chapter=chapter,
        code_learning=code_learning,
        report_type=report_type,
        language=language,
        repo_id=repo_id,
        user_id=user_id,
        llm_session_id=llm_session_id,
        settings=settings,
        file_index=file_index,
    )

    # 写入 content_cache
    content_cache_key = build_cache_key(
        agent_id=agent_id,
        user_id=user_id,
        session_id=session_id,
        type_="content",
        report_type=report_type,
        chapter_idx=idx,
        repo_id=repo_id,
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
    1. 使用独立 review_idx 索引 (不依赖 current_chapter_idx, 避免索引错位)
    2. 读取 content_cache_keys[review_idx]
    3. SMART LLM 评审 (覆盖度 / 准确性 / 代码路径引用 / 完整性)
    4. 输出评审建议 + 修订后的内容
    5. 写入 reviewed_cache_keys[review_idx]
    6. review_idx += 1

    修复说明: 原实现使用 current_chapter_idx - 1 作为索引, 但 D 完成所有章节后
    current_chapter_idx 已等于 len(chapters), 导致 E 只评审最后一个章节.
    现改用独立 review_idx 字段, 从 0 开始递增, 确保所有章节都被评审.

    Args:
        state: ReportTaskState
        settings: Settings 实例

    Returns:
        delta dict: {reviewed_cache_keys: [key], review_idx: idx+1}
    """
    from src.agents.docbot.reviewer import ReviewerE

    agent_id = state.get("agent_id", "agentinsight-docbot")
    user_id = state.get("user_id", "")
    session_id = state.get("session_id", "")
    report_type = state.get("report_type", "")
    language = state.get("language", "zh")
    llm_session_id = state.get("llm_session_id", "")
    repo_id = state.get("repo_id", "")

    chapters = state.get("chapters", [])
    content_cache_keys = state.get("content_cache_keys", [])
    # 使用独立 review_idx, 不依赖 current_chapter_idx
    idx = state.get("review_idx", 0)
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
        repo_id=repo_id,
    )
    await write_cache(
        reviewed_key,
        json.dumps(reviewed, ensure_ascii=False),
        settings=settings,
    )
    return {
        "reviewed_cache_keys": [reviewed_key],
        "review_idx": idx + 1,  # 推进评审索引
        "revision_count": 1,  # operator.add 累积修订次数
    }


async def f_merge_node(state: dict, settings: Any | None = None) -> dict:
    """任务五: F 合并所有章节内容, SMART LLM 去重.

    修复说明: 原实现只读取 reviewed_cache_keys, 若 E 评审时某些章节被跳过,
    则 reviewed_data 长度 < len(chapters), 导致合并文档缺失章节.
    现增加兜底机制: 按 chapter_idx 顺序遍历所有章节, 优先读 reviewed_cache,
    若缺失则降级读 content_cache, 确保所有章节内容都被合并.

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
    content_cache_keys = state.get("content_cache_keys", [])
    repo_id = state.get("repo_id", "")

    # 先读取所有 reviewed_cache 到 dict (按数组位置 0-based 索引, 与 chapters 数组对齐)
    reviewed_map: dict[int, dict] = {}
    for arr_idx, key in enumerate(reviewed_cache_keys):
        raw = await read_cache(key, settings=settings)
        if raw:
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, dict):
                    reviewed_map[arr_idx] = parsed  # 用数组位置作键, 与 chapters 对齐
            except (json.JSONDecodeError, TypeError) as e:
                logger.warning("reviewed_cache JSON 解析失败 (跳过): %s", e)

    # 再读取所有 content_cache 到 dict (按数组位置 0-based 索引, 兜底用)
    content_map: dict[int, dict] = {}
    for arr_idx, key in enumerate(content_cache_keys):
        raw = await read_cache(key, settings=settings)
        if raw:
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, dict):
                    content_map[arr_idx] = parsed  # 用数组位置作键, 与 chapters 对齐
            except (json.JSONDecodeError, TypeError) as e:
                logger.warning("content_cache JSON 解析失败 (跳过): %s", e)

    # 按章节顺序组装 reviewed_data: 优先 reviewed, 缺失则降级 content
    # 使用数组位置 i (0-based) 作为查找键, 与 reviewed_map/content_map 一致
    reviewed_data: list[dict] = []
    missing_count = 0
    for i, ch in enumerate(chapters):
        if not isinstance(ch, dict):
            continue
        # 优先用 reviewed (按数组位置查找)
        if i in reviewed_map:
            reviewed_data.append(reviewed_map[i])
        # 降级用 content (按数组位置查找)
        elif i in content_map:
            logger.warning("章节 %d 缺少评审结果, 降级使用填充内容", i)
            reviewed_data.append(content_map[i])
        else:
            # 完全缺失, 写入占位
            missing_count += 1
            logger.error("章节 %d 内容完全缺失!", i)
            reviewed_data.append(
                {
                    "chapter_idx": ch.get("idx", i + 1),
                    "content_md": f"## {ch.get('title', f'章节{i + 1}')}\n\n本章节内容生成失败, 请重新生成.",
                    "image_svgs": [],
                }
            )

    if missing_count > 0:
        logger.error("合并阶段发现 %d 个章节内容完全缺失", missing_count)

    logger.info(
        "合并阶段: chapters=%d, reviewed=%d, content_fallback=%d, missing=%d",
        len(chapters),
        len(reviewed_map),
        len(reviewed_data) - len(reviewed_map) - missing_count,
        missing_count,
    )

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
        repo_id=repo_id,
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
    repo_id = state.get("repo_id", "")

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

    # 调用 FinalReviewerG 终审 (P1-5.3.3: 传入 refined chapters 供结构校验)
    reviewer = FinalReviewerG(settings)
    final_doc = await reviewer.finalize_single_report(
        report_type=report_type,
        language=language,
        merged=merged,
        code_learning=code_learning,
        llm_session_id=llm_session_id,
        settings=settings,
        chapters=state.get("chapters") or None,
    )

    # 写入 final_cache
    final_key = build_cache_key(
        agent_id=agent_id,
        user_id=user_id,
        session_id=session_id,
        type_="final",
        report_type=report_type,
        repo_id=repo_id,
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

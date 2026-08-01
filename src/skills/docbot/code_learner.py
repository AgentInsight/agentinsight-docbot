"""任务一技能: STRATEGIC LLM 深度学习用户代码仓库.

职责 (见 docs/DESIGN_AGENT.md 第 4.2 节与第 7.1 节):
1. 通过 GitMCPAdapter 克隆 / 拉取仓库 (复用 skills.docbot.repo_loader.clone_repo)
2. 构建文件索引 (复用 skills.docbot.repo_loader.build_file_index)
3. 选取关键文件并读取内容 (复用 select_key_files + read_files)
4. STRATEGIC LLM 学习, 输出结构化 JSON: {summary, key_modules, dependencies, architecture_notes}
5. 写入 Redis 缓存 (由节点函数 c_code_learning_node 负责, 本技能返回 dict)

优化 (参考业界开源智能体):
- 注入 persona (role_name / description) 让 LLM 从对应角色视角学习代码
- report_type 差异化学习侧重 (架构/设计/需求/测试/优化/性能/缺陷/API)
- 结构化 JSON 输出, 与下游 outline_refiner / content_filler 期望字段对齐
- 要求 LLM 标注文件路径:行号引用, 供下游精确引用代码

import 路径约定: 用绝对导入.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any

from src.llm.client import LLMClient, LLMTier, get_llm_client
from src.observability.tracing import trace_chain
from src.skills.docbot.code_graph import build_code_graph, format_code_graph_for_prompt
from src.skills.docbot.repo_loader import (
    build_file_index,
    clone_repo,
    read_files,
    select_key_files,
)
from src.skills.docbot.repo_map import generate_repo_map

logger = logging.getLogger(__name__)

# PERF-T0 / TOK-S0: 同 session×repo 学习单飞 (确定性事实 + 共享 STRATEGIC 基线)
_learning_locks: dict[str, asyncio.Lock] = {}
_learning_locks_guard = asyncio.Lock()


async def _get_learning_lock(user_id: str, repo_id: str, session_id: str) -> asyncio.Lock:
    key = f"{user_id}:{repo_id}:{session_id}"
    async with _learning_locks_guard:
        lock = _learning_locks.get(key)
        if lock is None:
            lock = asyncio.Lock()
            _learning_locks[key] = lock
        return lock


# 代码学习 prompt 模板缺失时的兜底
_DEFAULT_PROMPT = """你是 {report_type} 类型技术文档的代码学习专家. 请深度学习以下代码仓库并输出结构化摘要.

## 文件索引

{file_index}

## 关键文件内容

{file_contents}

## 输出要求 (严格 JSON, 不要 markdown 代码块)
{{
  "summary": "Markdown 格式的整体摘要",
  "key_modules": [{{"name": "模块名", "path": "路径", "responsibility": "职责"}}],
  "dependencies": [{{"from": "模块A", "to": "模块B", "type": "import"}}],
  "architecture_notes": "架构笔记 Markdown"
}}
"""

_TYPE_ADAPT_PROMPT = """你是 {role_name}. {description}

已有一份仓库公共学习摘要与确定性事实. 请按当前报告类型侧重做**增量合成**, 输出结构化 JSON.
禁止重复复述无关维度; 公共事实已给定, 只需补齐类型专属字段.

# 学习侧重
{learning_focus}

# 公共摘要 (已压缩)
{shared_summary}

# 确定性事实层 (已压缩)
{facts_text}

# 输出 schema 附加字段
{output_schema_extra}

# 输出要求 (严格 JSON)
{{
  "summary": "围绕当前报告类型的 Markdown 摘要 (带 path:line)",
  "key_modules": [],
  "dependencies": [],
  "architecture_notes": ""
  {output_schema_extra}
}}
"""


async def learn_code(
    *,
    repo_config: dict,
    repo_id: str,
    user_id: str,
    report_type: str,
    llm_session_id: str,
    settings: Any | None = None,
    session_id: str = "",
    agent_id: str = "agentinsight-docbot",
) -> dict:
    """任务一: STRATEGIC LLM 深度学习用户代码仓库.

    Args:
        repo_config: 仓库配置 (含 repo_url / auth_type / token / ...)
        repo_id: 仓库 ID
        user_id: 用户 ID
        report_type: 报告类型 (8 种之一, 决定学习侧重)
        llm_session_id: LLM 会话 ID (用于会话保持)
        settings: Settings 实例 (可选)
        session_id: 会话 ID (PERF-T0 共享学习缓存键)
        agent_id: Agent 标识

    Returns:
        {
            "summary": str (LLM 输出的整体摘要, Markdown 格式),
            "file_index": dict,
            "key_modules": list[dict] (LLM 提取的模块列表, 含 name/path/responsibility),
            "dependencies": list[dict] (LLM 提取的依赖列表, 含 from/to/type),
            "architecture_notes": str (LLM 输出的架构笔记, Markdown 格式),
            "repo_path": str,
        }
    """
    async with trace_chain(
        name=f"docbot.code_learning.{report_type}",
        input={"repo_id": repo_id, "user_id": user_id, "report_type": report_type},
    ) as span:
        logger.info(
            "learn_code 开始: report_type=%s, repo_id=%s, user_id=%s, "
            "llm_session_id=%s, repo_url=%s",
            report_type,
            repo_id,
            user_id,
            llm_session_id,
            repo_config.get("repo_url", ""),
        )

        # PERF-T0 / TOK-S0: 尝试复用同 session×repo 的共享学习基线
        if session_id:
            try:
                from src.skills.docbot.cache import build_cache_key, read_cache

                shared_key = build_cache_key(
                    agent_id=agent_id,
                    user_id=user_id,
                    session_id=session_id,
                    type_="code_learning_shared",
                    report_type="_shared",
                    repo_id=repo_id,
                )
                shared_raw = await read_cache(shared_key, settings=settings)
                if shared_raw:
                    shared_base = json.loads(shared_raw)
                    if isinstance(shared_base, dict) and shared_base.get("summary"):
                        logger.info(
                            "TOK-S0: 命中共享学习基线, 做类型增量合成 report_type=%s",
                            report_type,
                        )
                        adapted = await _adapt_learning_for_type(
                            shared_base=shared_base,
                            report_type=report_type,
                            llm_session_id=llm_session_id,
                            settings=settings,
                        )
                        span.update(
                            metadata={
                                "shared_learning_hit": True,
                                "summary_length": len(adapted.get("summary", "")),
                            }
                        )
                        return adapted
            except Exception as e:  # noqa: BLE001
                logger.warning("共享学习基线读取失败 (继续全量学习): %s", e)

        # 同 session×repo 单飞: 避免双报告并发重复 STRATEGIC
        learn_lock = await _get_learning_lock(user_id, repo_id, session_id or llm_session_id)
        async with learn_lock:
            # 双重检查共享缓存 (另一协程可能刚写完)
            if session_id:
                try:
                    from src.skills.docbot.cache import build_cache_key, read_cache

                    shared_key = build_cache_key(
                        agent_id=agent_id,
                        user_id=user_id,
                        session_id=session_id,
                        type_="code_learning_shared",
                        report_type="_shared",
                        repo_id=repo_id,
                    )
                    shared_raw = await read_cache(shared_key, settings=settings)
                    if shared_raw:
                        shared_base = json.loads(shared_raw)
                        if isinstance(shared_base, dict) and shared_base.get("summary"):
                            logger.info(
                                "TOK-S0: 单飞后命中共享基线, 类型增量合成 report_type=%s",
                                report_type,
                            )
                            return await _adapt_learning_for_type(
                                shared_base=shared_base,
                                report_type=report_type,
                                llm_session_id=llm_session_id,
                                settings=settings,
                            )
                except Exception as e:  # noqa: BLE001
                    logger.warning("共享学习双重检查失败: %s", e)

            return await _learn_code_full(
                repo_config=repo_config,
                repo_id=repo_id,
                user_id=user_id,
                report_type=report_type,
                llm_session_id=llm_session_id,
                settings=settings,
                session_id=session_id,
                agent_id=agent_id,
                span=span,
            )


async def _adapt_learning_for_type(
    *,
    shared_base: dict,
    report_type: str,
    llm_session_id: str,
    settings: Any | None,
) -> dict:
    """TOK-S0: 基于共享基线做短 prompt 类型增量合成 (SMART, 非二次 STRATEGIC)."""
    from src.config.docbot.learning_focus import (
        LEARNING_SCHEMA_VERSION,
        extract_type_specific_fields,
        format_extra_schema,
        format_learning_focus,
    )

    role_name, description = _load_persona(report_type)
    learning_focus = format_learning_focus(report_type)
    output_schema_extra = format_extra_schema(report_type)
    facts_parts = [
        str(shared_base.get("project_metadata_text") or "")[:2000],
        str(shared_base.get("glossary_text") or "")[:3000],
        str(shared_base.get("endpoints_text") or "")[:4000],
        str(shared_base.get("enums_text") or "")[:2000],
        str(shared_base.get("scopes_text") or "")[:1500],
        str(shared_base.get("config_specs_text") or "")[:1500],
    ]
    prompt = _TYPE_ADAPT_PROMPT.format(
        role_name=role_name,
        description=description,
        learning_focus=learning_focus,
        shared_summary=str(shared_base.get("summary") or "")[:8000],
        facts_text="\n\n".join(p for p in facts_parts if p),
        output_schema_extra=output_schema_extra,
    )
    llm = _get_llm(settings)
    try:
        response = await llm.achat(
            [{"role": "user", "content": prompt}],
            tier=LLMTier.SMART,
            session_id=llm_session_id,
            span_name=f"docbot.code_learning.adapt.{report_type}",
            step="code_learning_adapt",
            max_tokens=4096,
            reasoning_effort="none",
            temperature=0.0,
        )
        parsed = _parse_learning_response(response.content or "")
    except Exception as e:  # noqa: BLE001
        logger.warning("类型增量合成失败, 复用共享基线: %s", e)
        parsed = {}

    result = dict(shared_base)
    if parsed.get("summary"):
        result["summary"] = parsed["summary"]
    if parsed.get("architecture_notes"):
        result["architecture_notes"] = parsed["architecture_notes"]
    if parsed.get("key_modules"):
        result["key_modules"] = parsed["key_modules"]
    if parsed.get("dependencies"):
        result["dependencies"] = parsed["dependencies"]
    type_specific = extract_type_specific_fields(report_type, parsed)
    result["type_specific"] = type_specific
    result["learning_schema_version"] = LEARNING_SCHEMA_VERSION
    result["shared_learning_adapted"] = True
    result.update(type_specific)
    return result


async def _learn_code_full(
    *,
    repo_config: dict,
    repo_id: str,
    user_id: str,
    report_type: str,
    llm_session_id: str,
    settings: Any | None,
    session_id: str,
    agent_id: str,
    span: Any,
) -> dict:
    """全量学习路径 (首个报告类型执行; 结果写入共享基线)."""
    # 1. 克隆 / 拉取仓库
    logger.info("learn_code 步骤1: 克隆/拉取仓库 (report_type=%s)", report_type)
    try:
        repo_path = await clone_repo(repo_config, user_id, repo_id, settings=settings)
    except Exception as e:
        logger.exception(
            "learn_code 步骤1 失败: 克隆仓库异常. report_type=%s, repo_id=%s, "
            "repo_url=%s, error=%s: %s",
            report_type,
            repo_id,
            repo_config.get("repo_url", ""),
            type(e).__name__,
            e,
        )
        raise
    logger.info(
        "learn_code 步骤1 完成: repo_path=%s (report_type=%s)",
        repo_path,
        report_type,
    )
    span.update(metadata={"repo_path": repo_path})

    # 2. 构建文件索引
    logger.info("learn_code 步骤2: 构建文件索引 (report_type=%s)", report_type)
    file_index = await build_file_index(repo_path, settings=settings)
    file_count = file_index.get("file_count", 0)
    logger.info(
        "learn_code 步骤2 完成: file_count=%d, total_size_bytes=%d (report_type=%s)",
        file_count,
        file_index.get("total_size_bytes", 0),
        report_type,
    )
    if file_count == 0:
        logger.error(
            "learn_code 严重: 仓库文件数为 0, 可能仓库为空或克隆未完成. "
            "report_type=%s, repo_path=%s, repo_url=%s",
            report_type,
            repo_path,
            repo_config.get("repo_url", ""),
        )
    span.update(metadata={"file_count": file_count})

    # 3. 选取关键文件 + 读取内容 (P0: 按 report_type 调整优先级)
    key_files = select_key_files(file_index, max_files=30, report_type=report_type)
    logger.info(
        "learn_code 步骤3: 选取关键文件 %d 个 (report_type=%s)",
        len(key_files),
        report_type,
    )
    file_contents = await read_files(repo_path, key_files, settings=settings)
    logger.info(
        "learn_code 步骤3 完成: file_contents_length=%d (report_type=%s)",
        len(file_contents),
        report_type,
    )
    if not file_contents:
        logger.warning(
            "learn_code 警告: 关键文件内容为空. report_type=%s, key_files=%s",
            report_type,
            key_files[:5],
        )
    span.update(
        metadata={
            "key_files_count": len(key_files),
            "file_contents_length": len(file_contents),
        }
    )

    # 4. 加载提示词模板 + persona
    prompt_template = _load_prompt_template()
    role_name, description = _load_persona(report_type)
    logger.info(
        "learn_code 步骤4: prompt_template 长度=%d, role_name=%s (report_type=%s)",
        len(prompt_template),
        role_name,
        report_type,
    )

    # 4.6 P1-5.2.2: 构建代码知识图谱
    code_graph_obj = build_code_graph(repo_path, file_index)
    code_graph_text = format_code_graph_for_prompt(code_graph_obj)
    logger.info(
        "learn_code 步骤4.6: code_graph nodes=%d, edges=%d, text_length=%d (report_type=%s)",
        len(code_graph_obj.nodes),
        len(code_graph_obj.edges),
        len(code_graph_text),
        report_type,
    )

    # 4.5 P1-5.2.1: 生成 tree-sitter 仓库地图
    repo_map = generate_repo_map(repo_path, file_index, code_graph=code_graph_obj)
    logger.info(
        "learn_code 步骤4.5: repo_map 长度=%d (report_type=%s, PageRank排序)",
        len(repo_map),
        report_type,
    )
    span.update(metadata={"repo_map_length": len(repo_map)})
    span.update(
        metadata={
            "code_graph_nodes": len(code_graph_obj.nodes),
            "code_graph_edges": len(code_graph_obj.edges),
        }
    )

    # v8-P0-A: 提取项目元数据
    project_metadata: dict[str, Any] = {}
    project_metadata_text: str = ""
    try:
        from src.skills.docbot.project_metadata import (
            extract_project_metadata,
            format_metadata_for_prompt,
        )
        project_metadata = extract_project_metadata(repo_path, file_index)
        project_metadata_text = format_metadata_for_prompt(project_metadata)
        logger.info(
            "v8-P0-A: project_name=%s brand_count=%d",
            project_metadata.get("project_name", ""),
            len(project_metadata.get("brand_names", [])),
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("v8-P0-A: 项目元数据提取失败 (降级空): %s", e)

    # v8-P0-B: 提取术语词典
    terminology_glossary: dict[str, list[str]] = {}
    glossary_text: str = ""
    try:
        from src.skills.docbot.terminology_glossary import (
            extract_terminology_glossary,
            format_glossary_for_prompt,
        )
        code_graph_dict: dict[str, Any] = {"nodes": [], "edges": []}
        if code_graph_obj is not None:
            try:
                code_graph_dict = {
                    "nodes": [
                        {"name": n.name, "kind": n.kind, "file_path": n.file_path}
                        for n in code_graph_obj.nodes.values()
                    ],
                    "edges": [],
                }
            except Exception:  # noqa: BLE001
                pass
        terminology_glossary = extract_terminology_glossary(
            code_graph=code_graph_dict,
            repo_map=repo_map,
            file_index=file_index,
            project_metadata=project_metadata,
        )
        glossary_text = format_glossary_for_prompt(terminology_glossary)
        logger.info(
            "v8-P0-B: glossary_terms=%d",
            len(terminology_glossary.get("all_terms", [])),
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("v8-P0-B: 术语词典提取失败 (降级空): %s", e)

    # v8-P0-C: AST 结构感知搜索
    http_endpoints: list[dict[str, Any]] = []
    enum_definitions: list[dict[str, Any]] = []
    endpoints_text: str = ""
    enums_text: str = ""
    domain_symbols: dict[str, list[str]] = {"class_names": [], "table_names": []}
    literal_api_routes: list[str] = []
    try:
        from src.skills.docbot.ast_search import (
            search_http_endpoints,
            search_enum_definitions,
            format_endpoints_for_prompt,
            format_enums_for_prompt,
            search_domain_symbols,
            search_literal_api_routes,
        )
        http_endpoints = search_http_endpoints(repo_path, file_index)
        enum_definitions = search_enum_definitions(repo_path, file_index)
        endpoints_text = format_endpoints_for_prompt(http_endpoints)
        enums_text = format_enums_for_prompt(enum_definitions)
        domain_symbols = search_domain_symbols(repo_path)
        literal_api_routes = search_literal_api_routes(repo_path)
        existing = {
            str(ep.get("route") or "").lower().rstrip("/")
            for ep in http_endpoints
            if isinstance(ep, dict)
        }
        for r in literal_api_routes:
            key = str(r).lower().rstrip("/")
            if key and key not in existing:
                http_endpoints.append(
                    {
                        "http_method": "ANY",
                        "route": r,
                        "method_name": "literal_route",
                        "class_name": "LiteralRoute",
                        "summary": "源码字面量路由",
                    }
                )
                existing.add(key)
        logger.info(
            "v8-P0-C: endpoints=%d enums=%d domain_classes=%d literal_routes=%d",
            len(http_endpoints),
            len(enum_definitions),
            len(domain_symbols.get("class_names", [])),
            len(literal_api_routes),
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("v8-P0-C: AST 搜索失败 (降级空): %s", e)

    # v8-P0-E: Scope 识别
    scopes: dict[str, Any] = {}
    scopes_text: str = ""
    try:
        from src.skills.docbot.scope_detector import (
            detect_scopes,
            format_scopes_for_prompt,
        )
        scopes = detect_scopes(repo_path)
        scopes_text = format_scopes_for_prompt(scopes)
        logger.info(
            "v8-P0-E: is_monorepo=%s scope_count=%d",
            scopes.get("is_monorepo", False),
            len(scopes.get("scopes", [])),
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("v8-P0-E: Scope 识别失败 (降级空): %s", e)

    # v8-P0-H: 配置文件技术规格提取
    config_specs: dict[str, Any] = {}
    config_specs_text: str = ""
    try:
        from src.skills.docbot.project_metadata import (
            extract_config_specs,
            format_config_specs_for_prompt,
        )
        config_specs = extract_config_specs(repo_path)
        config_specs_text = format_config_specs_for_prompt(config_specs)
        logger.info("v8-P0-H: config_specs_count=%d", len(config_specs))
    except Exception as e:  # noqa: BLE001
        logger.warning("v8-P0-H: 配置规格提取失败 (降级空): %s", e)

    # 4.7 多视角 (若开启)
    if _is_multi_perspective_enabled(settings):
        logger.info(
            "learn_code 步骤4.7: 多视角代码审问已启用 (report_type=%s)",
            report_type,
        )
        try:
            from src.skills.docbot.multi_perspective_learner import (
                learn_code_multi_perspective,
            )

            return await learn_code_multi_perspective(
                repo_config=repo_config,
                repo_id=repo_id,
                user_id=user_id,
                report_type=report_type,
                llm_session_id=llm_session_id,
                repo_path=repo_path,
                file_index=file_index,
                file_contents=file_contents,
                code_graph_obj=code_graph_obj,
                settings=settings,
                project_metadata=project_metadata,
                project_metadata_text=project_metadata_text,
                terminology_glossary=terminology_glossary,
                glossary_text=glossary_text,
                http_endpoints=http_endpoints,
                enum_definitions=enum_definitions,
                endpoints_text=endpoints_text,
                enums_text=enums_text,
                scopes=scopes,
                scopes_text=scopes_text,
                config_specs=config_specs,
                config_specs_text=config_specs_text,
            )
        except Exception as e:
            logger.warning(
                "learn_code 步骤4.7 失败: 降级到单视角. report_type=%s, error=%s: %s",
                report_type,
                type(e).__name__,
                e,
            )
            span.update(
                metadata={"multi_perspective_fallback_reason": f"{type(e).__name__}: {e}"}
            )

    # 5. 构造 prompt
    from src.config.docbot.learning_focus import (
        LEARNING_SCHEMA_VERSION,
        extract_type_specific_fields,
        format_extra_schema,
        format_learning_focus,
    )

    learning_focus = format_learning_focus(report_type)
    output_schema_extra = format_extra_schema(report_type)
    (
        repo_map_budgeted,
        code_graph_budgeted,
        file_contents_budgeted,
        meta_budgeted,
        gloss_budgeted,
        ep_budgeted,
        en_budgeted,
        cfg_budgeted,
        scopes_budgeted,
    ) = _apply_token_budgets(
        settings=settings,
        repo_map=repo_map,
        code_graph=code_graph_text,
        file_contents=file_contents,
        project_metadata_text=project_metadata_text,
        glossary_text=glossary_text,
        endpoints_text=endpoints_text,
        enums_text=enums_text,
        config_specs_text=config_specs_text,
        scopes_text=scopes_text,
        report_type=report_type,
    )
    prompt = prompt_template.format(
        report_type=report_type,
        role_name=role_name,
        description=description,
        learning_focus=learning_focus,
        output_schema_extra=output_schema_extra,
        file_index=file_index.get("summary", ""),
        file_contents=file_contents_budgeted,
        repo_map=repo_map_budgeted,
        code_graph=code_graph_budgeted,
        project_metadata_text=meta_budgeted,
        glossary_text=gloss_budgeted,
        endpoints_text=ep_budgeted,
        enums_text=en_budgeted,
        config_specs_text=cfg_budgeted,
        scopes_text=scopes_budgeted,
    )
    logger.info(
        "learn_code 步骤5: prompt 构造完成, 长度=%d (report_type=%s, schema=%s)",
        len(prompt),
        report_type,
        LEARNING_SCHEMA_VERSION,
    )

    # 6. STRATEGIC LLM 学习
    llm = _get_llm(settings)
    messages = [{"role": "user", "content": prompt}]
    logger.info(
        "learn_code 步骤6: 调用 STRATEGIC LLM (report_type=%s, session_id=%s)",
        report_type,
        llm_session_id,
    )
    try:
        response = await llm.achat(
            messages,
            tier=LLMTier.STRATEGIC,
            session_id=llm_session_id,
            span_name=f"docbot.code_learning.{report_type}",
            step="code_learning",
            max_tokens=getattr(settings, "strategic_token_limit", 8192) or 8192,
            reasoning_effort="none",
        )
    except Exception as e:
        logger.exception(
            "learn_code 步骤6 失败: LLM 调用异常. report_type=%s, tier=STRATEGIC, error=%s: %s",
            report_type,
            type(e).__name__,
            e,
        )
        raise
    logger.info(
        "learn_code 步骤6 完成: LLM 响应 content_length=%d, model=%s, "
        "input_tokens=%d, output_tokens=%d (report_type=%s)",
        len(response.content or ""),
        response.model,
        response.input_tokens,
        response.output_tokens,
        report_type,
    )
    if not response.content:
        logger.error(
            "learn_code 严重: LLM 返回空 content. report_type=%s, model=%s",
            report_type,
            response.model,
        )

    # 7. 解析 LLM JSON 输出
    parsed = _parse_learning_response(response.content)
    logger.info(
        "learn_code 步骤7: JSON 解析完成, parsed_keys=%s (report_type=%s)",
        list(parsed.keys()) if isinstance(parsed, dict) else "not_dict",
        report_type,
    )
    key_modules = parsed.get("key_modules", [])
    if not key_modules:
        key_modules = _extract_modules_fallback(file_index)
        logger.info(
            "learn_code 降级: key_modules 从文件索引启发式提取, count=%d (report_type=%s)",
            len(key_modules),
            report_type,
        )
    dependencies = parsed.get("dependencies", [])
    if not dependencies:
        dependencies = _extract_dependencies_fallback(file_index)
        logger.info(
            "learn_code 降级: dependencies 从文件索引提取, count=%d (report_type=%s)",
            len(dependencies),
            report_type,
        )

    type_specific = extract_type_specific_fields(report_type, parsed)
    citation_issues = _validate_learning_citations(
        parsed=parsed,
        type_specific=type_specific,
        file_index=file_index,
    )
    learning_result = {
        "summary": parsed.get("summary", response.content),
        "file_index": file_index,
        "key_modules": key_modules,
        "dependencies": dependencies,
        "architecture_notes": parsed.get("architecture_notes", response.content),
        "repo_path": repo_path,
        "learning_schema_version": LEARNING_SCHEMA_VERSION,
        "repo_map": repo_map,
        "code_graph": {
            "nodes": [
                {
                    "name": n.name,
                    "file_path": n.file_path,
                    "kind": n.kind,
                    "signature": n.signature,
                }
                for n in code_graph_obj.nodes.values()
            ],
            "edges": [
                {
                    "source": e.source,
                    "target": e.target,
                    "edge_type": e.edge_type,
                    "evidence": e.evidence,
                }
                for e in code_graph_obj.edges
            ],
            "module_deps": {
                k: sorted(v) for k, v in code_graph_obj.module_deps.items()
            },
        },
        "project_metadata": project_metadata,
        "project_metadata_text": project_metadata_text,
        "terminology_glossary": terminology_glossary,
        "glossary_text": glossary_text,
        "http_endpoints": http_endpoints,
        "enum_definitions": enum_definitions,
        "endpoints_text": endpoints_text,
        "enums_text": enums_text,
        "scopes": scopes,
        "scopes_text": scopes_text,
        "config_specs": config_specs,
        "config_specs_text": config_specs_text,
        "domain_symbols": domain_symbols,
        "literal_api_routes": literal_api_routes,
        "type_specific": type_specific,
        "citation_issues": citation_issues,
        **type_specific,
    }
    span.update(output={"summary_length": len(learning_result["summary"])})

    # 写入共享基线供同 session 其他报告类型复用
    if session_id:
        try:
            from src.skills.docbot.cache import build_cache_key, write_cache

            shared_key = build_cache_key(
                agent_id=agent_id,
                user_id=user_id,
                session_id=session_id,
                type_="code_learning_shared",
                report_type="_shared",
                repo_id=repo_id,
            )
            await write_cache(
                shared_key,
                json.dumps(learning_result, ensure_ascii=False),
                settings=settings,
            )
            logger.info("TOK-S0: 已写入共享学习基线: %s", shared_key)
        except Exception as e:  # noqa: BLE001
            logger.warning("写入共享学习基线失败 (不阻断): %s", e)

    logger.info(
        "learn_code 全部完成: report_type=%s, summary_length=%d, "
        "key_modules=%d, dependencies=%d, repo_map_length=%d, code_graph_nodes=%d",
        report_type,
        len(learning_result["summary"]),
        len(key_modules),
        len(dependencies),
        len(repo_map),
        len(code_graph_obj.nodes),
    )
    return learning_result



def _get_llm(settings: Any | None) -> LLMClient:
    """获取 LLMClient (settings 为 None 时用全局单例, 失败降级)."""
    try:
        if settings is not None:
            return LLMClient(settings)
        return get_llm_client()
    except Exception:  # noqa: BLE001
        return get_llm_client()


def _is_multi_perspective_enabled(settings: Any | None) -> bool:
    """检查 P2-5.4.1 多视角代码审问开关是否开启.

    默认关闭 (settings 为 None 或字段缺失时返回 False, 保持向后兼容).
    """
    if settings is None:
        return False
    try:
        return bool(getattr(settings, "docbot_multi_perspective_enabled", False))
    except Exception:  # noqa: BLE001
        return False


def _load_prompt_template() -> str:
    """加载 CODE_LEARNING_PROMPT 模板 (失败降级内置极简版)."""
    try:
        from src.config.docbot.prompts import CODE_LEARNING_PROMPT

        return CODE_LEARNING_PROMPT
    except Exception as e:  # noqa: BLE001
        logger.warning("加载 CODE_LEARNING_PROMPT 失败 (降级内置): %s", e)
        return _DEFAULT_PROMPT


def _load_persona(report_type: str) -> tuple[str, str]:
    """加载报告类型对应的 persona (role_name, description).

    失败时降级到通用 persona.
    """
    try:
        from src.config.docbot.personas import DOCBOT_REPORT_PERSONAS

        persona = DOCBOT_REPORT_PERSONAS.get(report_type, {})
        role_name = persona.get("role_name", "技术文档专家")
        description = persona.get("description", "生成结构完整的技术文档")
        return role_name, description
    except Exception as e:  # noqa: BLE001
        logger.warning("加载 persona 失败 (降级通用): %s", e)
        return "技术文档专家", "生成结构完整的技术文档"


def _parse_learning_response(content: str) -> dict:
    """解析 LLM 输出的 JSON 结构化摘要.

    期望格式:
    {
        "summary": "Markdown 文本",
        "key_modules": [{"name", "path", "responsibility", "key_symbols", "confidence"}],
        "dependencies": [{"from", "to", "type", "evidence"}],
        "architecture_notes": "Markdown 文本"
    }

    解析失败时降级: 把整个 content 作为 summary, 其他字段为空.
    """
    if not content:
        return {}

    # 尝试直接解析
    try:
        parsed = json.loads(content)
        if isinstance(parsed, dict):
            return parsed
    except (json.JSONDecodeError, TypeError):
        pass

    # 尝试从 markdown 代码块中提取 JSON
    json_block_pattern = re.compile(r"```(?:json)?\s*\n?(.*?)\n?```", re.DOTALL)
    match = json_block_pattern.search(content)
    if match:
        try:
            parsed = json.loads(match.group(1))
            if isinstance(parsed, dict):
                return parsed
        except (json.JSONDecodeError, TypeError):
            pass

    # 尝试提取第一个 { 到最后一个 } 之间的内容
    first_brace = content.find("{")
    last_brace = content.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        try:
            parsed = json.loads(content[first_brace : last_brace + 1])
            if isinstance(parsed, dict):
                return parsed
        except (json.JSONDecodeError, TypeError):
            pass

    logger.warning("LLM 输出 JSON 解析失败, 降级为纯文本 summary")
    return {
        "summary": content,
        "key_modules": [],
        "dependencies": [],
        "architecture_notes": content,
    }


def _extract_modules_fallback(file_index: dict) -> list[dict]:
    """从文件索引启发式提取模块列表 (LLM 解析失败时降级用)."""
    files = file_index.get("files", []) if isinstance(file_index, dict) else []
    modules: dict[str, dict] = {}
    for f in files:
        if not isinstance(f, dict):
            continue
        path = f.get("path", "")
        parts = path.split("/")
        if len(parts) > 1:
            top = parts[0]
            # 排除明显非模块的目录 (src/ tests/ docs/ examples/)
            if top not in {"src", "tests", "test", "docs", "examples", "example"}:
                if top not in modules:
                    modules[top] = {
                        "name": top,
                        "path": top,
                        "responsibility": "",
                        "key_symbols": [],
                        "confidence": "low",
                    }
    return sorted(modules.values(), key=lambda m: m["name"])


def _extract_dependencies_fallback(file_index: dict) -> list[dict]:
    """从文件索引提取依赖文件列表 (LLM 解析失败时降级用)."""
    files = file_index.get("files", []) if isinstance(file_index, dict) else []
    deps: list[dict] = []
    dep_names = {
        "requirements.txt",
        "package.json",
        "go.mod",
        "pom.xml",
        "Cargo.toml",
        "build.gradle",
        "pyproject.toml",
    }
    for f in files:
        if not isinstance(f, dict):
            continue
        name = f.get("name", "")
        if name in dep_names:
            deps.append(
                {
                    "from": name,
                    "to": f.get("path", name),
                    "type": "dependency_file",
                    "evidence": f.get("path", name),
                }
            )
    return deps


def _clip_chars(text: str, max_chars: int) -> str:
    """按字符上限裁剪文本."""
    if not text or max_chars <= 0:
        return ""
    if len(text) <= max_chars:
        return text
    return text[: max(0, max_chars - 20)] + "\n... (truncated)"


def _apply_token_budgets(
    *,
    settings: Any | None,
    repo_map: str,
    code_graph: str,
    file_contents: str,
    project_metadata_text: str,
    glossary_text: str,
    endpoints_text: str,
    enums_text: str,
    config_specs_text: str,
    scopes_text: str,
    report_type: str = "",
) -> tuple[str, str, str, str, str, str, str, str, str]:
    """P1-A / TOK-C1/C2: 按 STRATEGIC 窗口分配上下文预算并按类型裁剪.

    budget ≈ strategic_context_tokens * 0.6:
    - repo_map ≤ 15%
    - code_graph ≤ 10%
    - 确定性层 *_text ≤ 25%
    - file_contents ≤ 50%
    TOK-C2: 非 api 类型大幅压缩 endpoints; 非 architecture 压缩 scopes 等.
    """
    ctx_tokens = 128_000
    if settings is not None:
        ctx_tokens = int(
            getattr(settings, "strategic_context_tokens", None)
            or getattr(settings, "context_max_tokens", None)
            or 128_000
        )
    budget = max(8_000, int(ctx_tokens * 0.6))
    repo_map_chars = (budget * 15 // 100) * 4
    code_graph_chars = (budget * 10 // 100) * 4
    facts_chars = (budget * 25 // 100) * 4
    files_chars = (budget * 50 // 100) * 4

    # 确定性层 6 段均分 facts 预算
    per_fact = max(2_000, facts_chars // 6)

    # TOK-C2: 按类型裁剪注入字段
    rt = (report_type or "").lower()
    ep_limit = per_fact
    en_limit = per_fact
    scopes_limit = per_fact
    cfg_limit = per_fact
    if rt and rt != "api_doc":
        ep_limit = min(per_fact, 4_000)
        en_limit = min(per_fact, 3_000)
    if rt and rt not in ("architecture", "design", "optimization"):
        scopes_limit = min(per_fact, 2_000)
    if rt and rt not in ("architecture", "optimization", "performance"):
        cfg_limit = min(per_fact, 2_000)

    return (
        _clip_chars(repo_map, repo_map_chars),
        _clip_chars(code_graph, code_graph_chars),
        _clip_chars(file_contents, min(files_chars, 500_000)),
        _clip_chars(project_metadata_text, per_fact),
        _clip_chars(glossary_text, per_fact),
        _clip_chars(endpoints_text, ep_limit),
        _clip_chars(enums_text, en_limit),
        _clip_chars(config_specs_text, cfg_limit),
        _clip_chars(scopes_text, scopes_limit),
    )


# path:line 引用模式 (兼容 path:L42)
_PATH_LINE_RE = re.compile(
    r"(?P<path>[A-Za-z0-9_./\\-]+\.[A-Za-z0-9]+):L?(?P<line>\d+)"
)


def _validate_learning_citations(
    *,
    parsed: dict,
    type_specific: dict,
    file_index: dict | None,
) -> list[dict]:
    """P1-B: 对 summary / architecture_notes / 类型字段中的 path:line 做存在性校验.

    无效引用记入 citation_issues (不阻断主流程); 失败降级为空列表.
    """
    if not isinstance(parsed, dict):
        return []
    try:
        from src.skills.docbot.citation_extractor import validate_citations
    except Exception as e:  # noqa: BLE001
        logger.warning("citation_extractor 不可用, 跳过学习结果引用校验: %s", e)
        return []

    texts: list[str] = []
    for key in ("summary", "architecture_notes"):
        val = parsed.get(key)
        if isinstance(val, str) and val:
            texts.append(val)
    texts.append(json.dumps(type_specific, ensure_ascii=False) if type_specific else "")

    blob = "\n".join(texts)
    citations: list[dict] = []
    seen: set[tuple[str, int | None, int | None]] = set()
    for m in _PATH_LINE_RE.finditer(blob):
        path = m.group("path").replace("\\", "/")
        # 去掉可能的前导 ./
        path = path.lstrip("./")
        line = int(m.group("line"))
        key = (path, line, line)
        if key in seen:
            continue
        seen.add(key)
        citations.append(
            {
                "file_path": path,
                "line_start": line,
                "line_end": line,
                "raw_reference": m.group(0),
                "chapter_idx": None,
            }
        )
    if not citations:
        return []
    try:
        result = validate_citations(citations, file_index=file_index)
    except Exception as e:  # noqa: BLE001
        logger.warning("学习结果引用校验失败 (降级空): %s", e)
        return []
    issues = result.get("issues") or []
    if issues:
        logger.info(
            "learn_code P1-B: citation_issues=%d (missing_files=%d)",
            len(issues),
            len(result.get("missing_files") or []),
        )
    return list(issues) if isinstance(issues, list) else []


__all__ = ["learn_code"]

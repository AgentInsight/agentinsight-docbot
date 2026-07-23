"""API 路由: OpenAI 兼容端点 + 报告下载.

docbot OpenAI 兼容端点与 API 测试设计约束:
- 统一调用 OpenAI 兼容端点 POST /v1/chat/completions, 请求体带 stream: true
- 用户消息内容为 JSON 指令:
  {"action":"generate_docs","repo_id":...,"report_types":[...],"report_format":...,"language":...}
- 所有请求都视为 generate_docs 指令, 调用顶层 docbot graph
- 不区分 SHORT_QUERY/OFF_TOPIC/CHAT/RESEARCH (docbot 单一意图)
- 测试页面只能走对外 OpenAI 兼容接口, 禁止调用后端私有端点

不暴露端点 (与从 AIR 拷贝的代码差异):
- POST /v1/feedback (docbot 不启用人审)
- WS /v1/ws/{session_id} (docbot 仅用 SSE 推送进度)
- GET/POST/PUT/DELETE /v1/mcp/configs (MCP 系统自带, 不暴露配置)
- POST /v1/files (docbot 不接受文件上传, 仅分析用户代码仓库)
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Any

import orjson
from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from pydantic import BaseModel, Field, StrictBool

from src.api.middleware import (
    get_request_agent_id,
    get_request_session_id,
    get_request_user_id,
)
from src.config.settings import get_settings
from src.observability.tracing import trace_agent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["openai-compatible"])

# 后台任务引用保留 (防止 GC 静默取消 asyncio.create_task)
_background_tasks: set[asyncio.Task[Any]] = set()


def _create_background_task(coro: Any) -> asyncio.Task[Any]:
    """创建后台任务并保留引用 (防止 GC 静默取消).

    标准模式: set + done_callback(discard), 任务完成后自动从集合移除.
    """
    task = asyncio.create_task(coro)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return task


# ========== LangGraph 图单例 (延迟构建, 复用) ==========
_compiled_graph: Any | None = None


async def _get_graph() -> Any:
    """获取/构建已编译的 docbot 顶层 LangGraph 单例.

    生产 StateGraph 必须挂 PostgresSaver.
    首次调用时构建, 后续复用 (单例).

    docbot 顶层图编排:
    - coordinator_a: 解析 JSON 指令 / 校验参数 / 建立根 span
    - spawn_b_tasks: asyncio.gather 并发派发 N 个 B 子图 (Semaphore 限流)
    - final_reviewer_g: 多报告交叉一致性评审
    - save_reports: 复用 ReportStore 保存 5 种格式
    """
    global _compiled_graph
    if _compiled_graph is None:
        from src.graph.builder import build_docbot_graph

        _compiled_graph = await build_docbot_graph()
    return _compiled_graph


# ========== 请求/响应模型 (OpenAI 兼容) ==========


class ChatMessage(BaseModel):
    """OpenAI 兼容消息格式."""

    role: str = "user"
    content: str = ""


class ChatCompletionRequest(BaseModel):
    """OpenAI 兼容 /v1/chat/completions 请求 (docbot 专属).

    用户消息内容为 JSON 指令字符串:
      {"action":"generate_docs","repo_id":...,"report_types":[...],"report_format":...,"language":...}

    扩展字段 (非 OpenAI 标准) 优先级: 显式请求字段 > 消息内容 JSON 指令 > Settings 默认值.
    """

    model: str = "agentinsight-docbot"
    messages: list[ChatMessage]
    stream: StrictBool = False
    temperature: float | None = None
    max_tokens: int | None = None
    session_id: str | None = Field(None, description="会话 ID (thread_id), 不传则自动生成")
    # docbot 专属扩展字段 (可从 messages 内容 JSON 指令解析, 也可显式传入)
    repo_id: str | None = Field(
        None, description="代码仓库 ID (来自 /v1/repos 创建, 必填)"
    )
    report_types: list[str] | None = Field(
        None,
        description=(
            "报告类型列表, 可选值: architecture|design|requirements|testcase|"
            "optimization|performance|defect|api_doc"
        ),
    )
    report_format: str | None = Field(
        None, description="输出格式: markdown | html | pdf | docx | json"
    )
    language: str | None = Field(
        None, description="文档语言: zh (简体中文, 默认) | en (English)"
    )


class ChatCompletionResponse(BaseModel):
    """OpenAI 兼容非流式响应."""

    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: list[dict[str, Any]]
    usage: dict[str, Any]
    # 报告输出格式 (markdown/html/pdf/docx/json)
    report_format: str | None = None
    # PDF 等二进制格式生成的文件路径
    file_path: str | None = None
    # 报告主键 UUID (一个 session 可生成多个报告, 下载基于 report_id)
    report_id: str | None = None
    # 多报告生成时的报告 ID 列表 (docbot 一次可生成多份文档)
    report_ids: list[str] | None = None


# ========== 会话持久化辅助 (以 UserId 为单位的对话保存) ==========


async def _persist_user_message(
    session_id: str,
    agent_id: str,
    user_id: str,
    query: str,
) -> None:
    """保存用户消息到 chat_messages, 并确保 research_sessions 记录存在.

    失败仅告警, 不阻断主流程 (消息持久化为辅助功能).
    """
    try:
        from src.api.middleware import get_request_client_ip
        from src.memory.session_store import get_session_store

        store = get_session_store()
        client_ip = get_request_client_ip()
        title = query[:100] if query else ""
        await store.ensure_session(session_id, agent_id, user_id, query=query, client_ip=client_ip)
        if title:
            existing_title = await store.get_session_title(session_id, agent_id, user_id)
            if not existing_title:
                await store.update_session_title(session_id, agent_id, user_id, title)
        await store.save_message(
            session_id=session_id,
            agent_id=agent_id,
            user_id=user_id,
            role="user",
            content=query,
        )
    except Exception:
        logger.warning(
            "保存用户消息失败 (不阻断主流程, session=%s): ",
            session_id,
            exc_info=True,
        )


async def _persist_assistant_message(
    session_id: str,
    agent_id: str,
    user_id: str,
    content: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    """保存 assistant 消息到 chat_messages.

    在流式/非流式响应完成后调用 (后台任务, 不阻塞用户响应).
    失败仅告警, 不阻断主流程.
    """
    try:
        from src.memory.session_store import get_session_store

        store = get_session_store()
        await store.save_message(
            session_id=session_id,
            agent_id=agent_id,
            user_id=user_id,
            role="assistant",
            content=content,
            metadata=metadata,
        )
    except Exception:
        logger.warning(
            "保存 assistant 消息失败 (不阻断主流程, session=%s): ",
            session_id,
            exc_info=True,
        )


def _parse_docbot_instruction(content: str) -> dict[str, Any]:
    """解析用户消息中的 JSON 指令.

    指令格式: {"action":"generate_docs","repo_id":...,"report_types":[...],"report_format":...,"language":...}

    解析失败时返回空 dict (调用方走 Settings 默认值).
    """
    if not content:
        return {}
    try:
        # 容忍前后空白和代码块包裹
        text = content.strip()
        if text.startswith("```"):
            # 剥离代码块围栏
            lines = text.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            text = "\n".join(lines).strip()
        parsed = orjson.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except Exception:  # noqa: BLE001
        logger.debug("用户消息非 JSON 指令, 走默认配置: %s", content[:200])
    return {}


# ========== 端点实现 ==========


@router.post("/chat/completions")
async def chat_completions(
    request: ChatCompletionRequest,
    req: Request,
    authorization: str | None = Header(None),
) -> Any:
    """OpenAI 兼容 docbot 端点.

    所有请求都视为 generate_docs 指令, 调用 docbot 顶层 graph.
    用户消息内容应为 JSON 指令 (或显式通过扩展字段传入配置).
    """
    settings = get_settings()

    # 提取最后一条 user 消息作为指令
    user_messages = [m for m in request.messages if m.role == "user"]
    if not user_messages:
        raise HTTPException(status_code=400, detail="messages 必须包含至少一条 user 消息")

    query = user_messages[-1].content
    if not query.strip():
        raise HTTPException(status_code=400, detail="查询内容不能为空")

    # 解析 JSON 指令 (扩展字段优先级高于消息内容)
    instruction = _parse_docbot_instruction(query)
    repo_id = request.repo_id or instruction.get("repo_id")
    report_types = request.report_types or instruction.get("report_types")
    report_format = request.report_format or instruction.get("report_format") or settings.default_report_format
    language = (request.language or instruction.get("language") or settings.report_language or "zh").lower()

    # 校验必填字段
    if not repo_id:
        raise HTTPException(
            status_code=400,
            detail="repo_id 必填 (通过请求体扩展字段或 messages 内容 JSON 指令提供)",
        )
    if not report_types:
        # 默认生成 architecture 报告
        report_types = ["architecture"]
    # 校验 language 仅接受 zh / en
    if language not in ("zh", "en"):
        raise HTTPException(
            status_code=400,
            detail=f"language 仅支持 zh / en, 实际: {language}",
        )
    # 校验 report_types 取值
    allowed_types = {
        "architecture", "design", "requirements", "testcase",
        "optimization", "performance", "defect", "api_doc",
    }
    invalid = [t for t in report_types if t not in allowed_types]
    if invalid:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的 report_types: {invalid}, 允许: {sorted(allowed_types)}",
        )
    # 校验 report_format
    if report_format not in ("markdown", "html", "pdf", "docx", "json"):
        raise HTTPException(
            status_code=400,
            detail=f"不支持的 report_format: {report_format}",
        )

    # 会话 ID (thread_id): 优先请求体, 其次中间件, 最后生成
    session_id = request.session_id or get_request_session_id() or str(uuid.uuid4())

    # user_id / agent_id 由中间件注入
    user_id = get_request_user_id()
    agent_id = get_request_agent_id()

    # 会话持久化: 保存 user 消息到 chat_messages + 确保 research_sessions 存在
    if user_id and agent_id:
        await _persist_user_message(session_id, agent_id, user_id, query)

    # 初始 State (TypedDict, 节点返回 delta)
    initial_state: dict[str, Any] = {
        "query": query,
        "session_id": session_id,
        "user_id": user_id,
        "agent_id": agent_id,
        # docbot 专属字段
        "repo_id": repo_id,
        "report_types": list(report_types),
        "report_format": report_format,
        "language": language,
        # 通用字段 (兼容 LangGraph state)
        "messages": [],
        "report_md": "",
        "report_formats": {},
        "status": "pending",
    }

    # 持久化报告配置到数据库 (per-session)
    if user_id and agent_id:
        try:
            from src.memory.session_store import get_session_store

            store = get_session_store()
            await store.update_report_config(
                session_id,
                agent_id,
                user_id,
                report_type=",".join(report_types),
                report_format=report_format,
                language=language,
            )
        except Exception:
            logger.warning(
                "保存报告配置失败 (不阻断主流程, session=%s): ",
                session_id,
                exc_info=True,
            )

    # LangGraph 配置: thread_id 做会话隔离
    thread_id = f"{agent_id}:{session_id}"
    graph_config = {"configurable": {"thread_id": thread_id}}

    if request.stream:
        return StreamingResponse(
            _stream_docbot(
                initial_state,
                graph_config,
                request,
                session_id,
                save_user_id=user_id,
                save_agent_id=agent_id,
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Session-Id": session_id,
            },
        )
    else:
        # 非流式: 完整执行后返回
        docbot_response = await _run_docbot(
            initial_state,
            graph_config,
            request,
            session_id,
        )
        # 会话持久化: 保存 assistant 消息到 chat_messages
        if user_id and agent_id:
            content = docbot_response.choices[0]["message"]["content"]
            if content:
                await _persist_assistant_message(
                    session_id,
                    agent_id,
                    user_id,
                    content,
                    metadata={
                        "intent": "generate_docs",
                        "report_ids": docbot_response.report_ids,
                    },
                )
        return _with_session_id(docbot_response, session_id)


def _with_session_id(response: ChatCompletionResponse, session_id: str) -> JSONResponse:
    """将非流式 ChatCompletionResponse 包装为 JSONResponse 并注入 X-Session-Id 响应头."""
    return JSONResponse(
        content=response.model_dump(),
        headers={"X-Session-Id": session_id},
    )


async def _stream_docbot(
    initial_state: dict[str, Any],
    graph_config: dict[str, Any],
    request: ChatCompletionRequest,
    session_id: str,
    *,
    save_user_id: str | None = None,
    save_agent_id: str | None = None,
) -> Any:
    """流式 SSE 响应生成器 (docbot 顶层图).

    接入 LangGraph astream, 逐节点 yield 进度 + 最终报告.
    用 trace_agent 包裹 graph.ainvoke 作为根 span.
    """
    completion_id = f"chatcmpl-{uuid.uuid4().hex[:24]}"
    created = int(time.time())

    def _sse_chunk(delta: dict[str, Any], finish_reason: str | None = None) -> str:
        """构造 SSE 数据帧."""
        chunk = {
            "id": completion_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": request.model,
            "choices": [
                {
                    "index": 0,
                    "delta": delta,
                    "finish_reason": finish_reason,
                }
            ],
        }
        return f"data: {orjson.dumps(chunk).decode('utf-8')}\n\n"

    # SSE 首块 (role)
    yield _sse_chunk({"role": "assistant"})

    collected_content: list[str] = []

    # 根 span 包裹整次文档生成
    async with trace_agent(
        name="agentinsight-docbot",
        input={
            "query": initial_state["query"][:200],
            "session_id": session_id,
            "repo_id": initial_state.get("repo_id"),
            "report_types": initial_state.get("report_types"),
        },
        metadata={
            "session_id": session_id,
            "intent": "generate_docs",
            "user_id": initial_state.get("user_id"),
            "repo_id": initial_state.get("repo_id"),
            "report_types": initial_state.get("report_types"),
        },
        session_id=session_id,
        user_id=initial_state.get("user_id"),
    ):
        try:
            graph = await _get_graph()

            # 节点名称中文映射 (用于流式进度提示)
            node_label = {
                "coordinator_a": "协调入口",
                "spawn_b_tasks": "并发派发报告任务",
                "final_reviewer_g": "多报告交叉评审",
                "save_reports": "保存报告",
                # 报告子图节点
                "b_init": "报告初始化",
                "c_code_learning": "代码学习",
                "c_outline_refine": "纲要细化",
                "d_content_fill": "内容填充",
                "e_review": "评审",
                "f_merge": "合并去重",
                "g_final_in_subgraph": "终审",
            }

            final_state: dict[str, Any] = {}

            async for event in graph.astream(
                initial_state, config=graph_config, stream_mode="updates"
            ):
                for node_name, delta in event.items():
                    if not isinstance(delta, dict):
                        continue
                    final_state.update(delta)

                    label = node_label.get(node_name, node_name)
                    progress = f"\n\n> **[{label}]** "
                    if node_name == "spawn_b_tasks":
                        report_count = len(delta.get("report_tasks", []))
                        progress += f"已派发 {report_count} 个报告任务\n"
                    elif node_name == "save_reports":
                        progress += "报告保存完成\n"
                        # 推送 report_ids (前端用于构造下载链接)
                        report_ids = delta.get("report_ids") or []
                        if report_ids:
                            yield _sse_chunk({"report_ids": report_ids})
                    elif node_name == "final_reviewer_g":
                        progress += "终审完成\n"
                    else:
                        progress += "\n"

                    yield _sse_chunk({"content": progress})
                    if progress:
                        collected_content.append(progress)
                    # 背压: 让出控制权
                    await asyncio.sleep(0.001)

            # 输出最终报告内容 (从 final_reports 列表提取, save_reports_node 已持久化到 DB)
            final_reports = final_state.get("final_reports") or []

            if not final_reports:
                hint = "\n\n*未生成报告内容 (可能代码仓库为空或同步未完成)*"
                collected_content.append(hint)
                yield _sse_chunk({"content": hint})
            else:
                # 推送每份报告的元信息 (含 download_urls, 前端用于构造下载链接)
                report_ids: list[str] = []
                summaries: list[str] = []
                for rpt in final_reports:
                    if not isinstance(rpt, dict):
                        continue
                    rid = rpt.get("report_id", "")
                    if rid:
                        report_ids.append(rid)
                    title = rpt.get("title") or rpt.get("report_type", "")
                    summary = rpt.get("summary", "")
                    download_urls = rpt.get("download_urls", {})
                    if summary:
                        summaries.append(f"### {title}\n\n{summary}")
                    # 推送单份报告元信息 (前端用于展示报告卡片 + 下载链接)
                    yield _sse_chunk(
                        {
                            "delta": {
                                "report": {
                                    "report_id": rid,
                                    "title": title,
                                    "summary": summary,
                                    "download_urls": download_urls,
                                }
                            }
                        }
                    )

                # 汇总文本作为最终 content (供会话持久化)
                final_content = (
                    "\n\n".join(summaries)
                    if summaries
                    else "文档已生成, 请通过下载链接获取"
                )
                collected_content.append(final_content)
                # 分块推送最终报告内容
                paragraphs = final_content.split("\n\n")
                for para in paragraphs:
                    yield _sse_chunk({"content": para + "\n\n"})
                    await asyncio.sleep(0.001)

                # 推送 report_ids (前端用于构造下载链接)
                if report_ids:
                    yield _sse_chunk({"report_ids": report_ids})

        except Exception as e:
            logger.exception("docbot 流水线执行失败")
            _err_msg = f"\n\n**文档生成失败**: {str(e)[:200]}"
            collected_content.append(_err_msg)
            yield _sse_chunk({"content": _err_msg})
            if save_user_id and save_agent_id and collected_content:
                full_response = "".join(collected_content)
                if full_response:
                    await _persist_assistant_message(
                        session_id,
                        save_agent_id,
                        save_user_id,
                        full_response,
                        metadata={"intent": "generate_docs", "status": "error"},
                    )
            yield _sse_chunk({}, finish_reason="error")
            yield "data: [DONE]\n\n"
            return

    # 会话持久化: 保存 assistant 消息
    if save_user_id and save_agent_id and collected_content:
        full_response = "".join(collected_content)
        if full_response:
            await _persist_assistant_message(
                session_id,
                save_agent_id,
                save_user_id,
                full_response,
                metadata={"intent": "generate_docs"},
            )

    yield _sse_chunk({}, finish_reason="stop")
    yield "data: [DONE]\n\n"


async def _run_docbot(
    initial_state: dict[str, Any],
    graph_config: dict[str, Any],
    request: ChatCompletionRequest,
    session_id: str,
) -> ChatCompletionResponse:
    """非流式文档生成执行.

    接入 LangGraph ainvoke.
    trace_agent 根 span.
    """
    completion_id = f"chatcmpl-{uuid.uuid4().hex[:24]}"
    created = int(time.time())

    async with trace_agent(
        name="agentinsight-docbot",
        input={
            "query": initial_state["query"][:200],
            "session_id": session_id,
            "repo_id": initial_state.get("repo_id"),
            "report_types": initial_state.get("report_types"),
        },
        metadata={
            "session_id": session_id,
            "intent": "generate_docs",
            "user_id": initial_state.get("user_id"),
            "repo_id": initial_state.get("repo_id"),
            "report_types": initial_state.get("report_types"),
        },
        session_id=session_id,
        user_id=initial_state.get("user_id"),
    ):
        settings = get_settings()
        file_path: str | None = None
        report_ids: list[str] = []
        try:
            graph = await _get_graph()
            final_state = await asyncio.wait_for(
                graph.ainvoke(initial_state, config=graph_config),
                timeout=settings.graph_total_timeout,
            )
            # 从 final_reports 列表提取内容 (save_reports_node 已持久化到 DB)
            final_reports = final_state.get("final_reports") or []

            if not final_reports:
                content = "未生成报告内容 (可能代码仓库为空或同步未完成)"
            else:
                summaries: list[str] = []
                for rpt in final_reports:
                    if not isinstance(rpt, dict):
                        continue
                    rid = rpt.get("report_id", "")
                    if rid:
                        report_ids.append(rid)
                    title = rpt.get("title") or rpt.get("report_type", "")
                    summary = rpt.get("summary", "")
                    if summary:
                        summaries.append(f"### {title}\n\n{summary}")
                content = (
                    "\n\n".join(summaries)
                    if summaries
                    else "文档已生成, 请通过下载链接获取"
                )

            # usage 估算
            total_tokens = final_state.get("total_tokens", 0) or 0
            if total_tokens > 0:
                usage = {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": total_tokens,
                    "cost_usd": round(final_state.get("total_cost_usd", 0.0) or 0.0, 6),
                }
            else:
                prompt_tokens = len(initial_state["query"]) // 4
                completion_tokens = len(content) // 4
                usage = {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": prompt_tokens + completion_tokens,
                }

        except Exception as e:
            logger.exception("docbot 流水线执行失败")
            content = f"文档生成失败: {str(e)[:500]}"
            usage = {
                "prompt_tokens": len(initial_state["query"]) // 4,
                "completion_tokens": len(content) // 4,
                "total_tokens": (len(initial_state["query"]) + len(content)) // 4,
            }
            report_ids = []

    return ChatCompletionResponse(
        id=completion_id,
        created=created,
        model=request.model,
        choices=[
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        usage=usage,
        report_format=request.report_format or "markdown",
        file_path=file_path,
        report_ids=report_ids if report_ids else None,
    )


@router.get("/models")
async def list_models() -> Any:
    """OpenAI 兼容 /v1/models 端点."""
    return {
        "object": "list",
        "data": [
            {
                "id": "agentinsight-docbot",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "agentinsight",
            }
        ],
    }


# ========== 报告下载端点 (多格式输出支持) ==========


@router.get("/reports/session/{session_id}")
async def list_session_reports(
    session_id: str,
    authorization: str | None = Header(None),
) -> list[dict[str, Any]]:
    """列出指定 session 的所有报告.

    一个 session 可以生成多个报告, 返回按 created_at DESC 排序的列表.
    """
    from src.memory.report_store import get_report_store

    user_id = get_request_user_id() or "anonymous"
    store = get_report_store()
    reports = await store.list_reports(
        agent_id=get_settings().agent_name,
        session_id=session_id,
        user_id=user_id,
        limit=50,
    )
    return [
        {
            "report_id": r.get("report_id"),
            "session_id": r.get("session_id"),
            "query": (r.get("query", "") or "")[:200],
            "report_format": r.get("report_format", "markdown"),
            "agent_role": r.get("agent_role"),
            "created_at": r.get("created_at"),
            "updated_at": r.get("updated_at"),
        }
        for r in reports
    ]


@router.get("/reports/{report_id}/download")
async def download_report(
    report_id: str,
    format: str = "markdown",
    authorization: str | None = Header(None),
) -> Response:
    """下载技术文档报告 (按 report_id, 支持多格式实时转换).

    支持 format: markdown / html / pdf / docx / json
    数据按 agent_id + user_id 隔离.
    """
    import aiofiles
    import aiofiles.os

    from src.memory.report_store import get_report_store
    from src.skills.researcher.publisher import Publisher

    user_id = get_request_user_id() or "anonymous"
    store = get_report_store()

    # report_id 应为 UUID
    report: dict[str, Any] | None = None
    try:
        uuid.UUID(report_id)
    except ValueError:
        report = None
    else:
        report = await store.get_report(
            report_id=report_id,
            agent_id=get_settings().agent_name,
            user_id=user_id,
        )

    deprecated_fallback = False
    if not report:
        # 向后兼容: 调用方仍传 session_id, 取该 session 最新报告
        reports = await store.list_reports(
            agent_id=get_settings().agent_name,
            session_id=report_id,
            user_id=user_id,
            limit=1,
        )
        if reports:
            report = reports[0]
            deprecated_fallback = True
            logger.warning(
                "下载端点收到 session_id=%s (兼容字段), 建议使用 report_id=%s",
                report_id,
                report.get("report_id"),
            )

    if not report:
        raise HTTPException(status_code=404, detail="报告不存在")

    # 数据隔离校验
    report_user_id = report.get("user_id")
    if report_user_id and report_user_id != user_id:
        raise HTTPException(status_code=403, detail="无权访问该报告")

    actual_report_id = report.get("report_id") or report_id
    content = report.get("report_md", "")
    title = (report.get("query", "") or "技术文档")[:100]
    sources = report.get("sources", []) if isinstance(report.get("sources"), list) else []
    agent_role = report.get("agent_role", "") or ""

    publisher = Publisher()
    extra_headers: dict[str, str] = {}
    if deprecated_fallback:
        extra_headers["X-Deprecated"] = (
            "true - 使用 session_id 调用已弃用, 请改用 report_id"
        )
        extra_headers["Link"] = (
            f'</v1/reports/{actual_report_id}/download>; rel="successor-version"'
        )

    if format == "markdown":
        return Response(
            content=content.encode("utf-8"),
            media_type="text/markdown",
            headers={
                "Content-Disposition": f"attachment; filename=report_{actual_report_id}.md",
                **extra_headers,
            },
        )
    elif format == "html":
        html = publisher._md_to_html(content)
        return Response(
            content=html.encode("utf-8"),
            media_type="text/html",
            headers={
                "Content-Disposition": f"attachment; filename=report_{actual_report_id}.html",
                **extra_headers,
            },
        )
    elif format == "pdf":
        pdf_path = await publisher._md_to_pdf(content, actual_report_id)
        if await aiofiles.os.path.exists(pdf_path):
            async with aiofiles.open(pdf_path, "rb") as f:
                pdf_content = await f.read()
            return Response(
                content=pdf_content,
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f"attachment; filename=report_{actual_report_id}.pdf",
                    **extra_headers,
                },
            )
        raise HTTPException(status_code=404, detail="PDF 生成失败")
    elif format == "docx":
        docx_bytes = publisher._to_docx(content, title=title)
        return Response(
            content=docx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={
                "Content-Disposition": f"attachment; filename=report_{actual_report_id}.docx",
                **extra_headers,
            },
        )
    elif format == "json":
        json_str = publisher._to_json(
            content,
            title=title,
            sources=sources,
            agent_role_server=agent_role,
        )
        return Response(
            content=json_str.encode("utf-8"),
            media_type="application/json",
            headers={
                "Content-Disposition": f"attachment; filename=report_{actual_report_id}.json",
                **extra_headers,
            },
        )
    else:
        raise HTTPException(status_code=400, detail=f"不支持的格式: {format}")

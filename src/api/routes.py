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
    # 报告详情列表 (含 download_urls, 前端用于展示下载链接)
    # 每项: {report_id, report_type, title, summary, download_urls: {markdown/html/pdf/docx/json: url}}
    reports: list[dict[str, Any]] | None = None


# ========== 会话持久化辅助 (以 UserId 为单位的对话保存) ==========


def _session_title_from_query(query: str | None) -> str:
    """从首条用户消息推导会话标题.

    generate_docs JSON 指令（含截断前缀）不得作为会话名, 回退为「当前会话」.
    """
    if not query:
        return ""
    q = query.strip()
    if q.startswith("{") and '"action"' in q and "generate_docs" in q:
        return "当前会话"
    return q[:100]


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
        title = _session_title_from_query(query)
        await store.ensure_session(session_id, agent_id, user_id, query=query, client_ip=client_ip)
        if title:
            existing_title = await store.get_session_title(session_id, agent_id, user_id)
            # 空标题或历史误写入的 generate_docs JSON → 用合理默认名覆盖
            if not existing_title or (
                existing_title.strip().startswith("{")
                and "generate_docs" in existing_title
            ):
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

    metadata 约定 (generate_docs 成功时):
    - intent: "generate_docs"
    - report_ids: list[str]
    - reports: list[{report_id, report_type, title, summary, download_urls}]
      前端加载历史会话时据此恢复「生成的文档」下载链接
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


def _build_download_urls(report_id: str) -> dict[str, str]:
    """按 report_id 构造 5 种格式的下载相对路径."""
    if not report_id:
        return {}
    return {
        fmt: f"/v1/reports/{report_id}/download?format={fmt}"
        for fmt in ("markdown", "html", "pdf", "docx", "json")
    }


async def _charge_daily_usage_if_needed(
    *,
    user_id: str,
    agent_id: str,
    report_ids: list[str],
    already_charged: bool,
    session_id: str = "",
) -> bool:
    """按成功报告份数扣减每日限额; 已扣减则跳过.

    Returns:
        True 表示本次或此前已完成扣减.
    """
    if already_charged:
        return True
    success_docs = len([rid for rid in report_ids if rid])
    if success_docs <= 0 or not user_id or not agent_id:
        return False
    try:
        from src.api.ip_user_resolver import increment_daily_report_count

        await increment_daily_report_count(user_id, agent_id, delta=success_docs)
        return True
    except Exception:
        logger.warning(
            "每日文档计数递增失败 (user=%s, session=%s, delta=%d, 不阻断主流程)",
            user_id,
            session_id,
            success_docs,
            exc_info=True,
        )
        return False


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

    # 每日文档生成限额检查 (与 researcher 对齐: 覆盖全部已解析 user_id, 含 JWT / IP)
    # 计数语义: 单次请求一个仓库, 每个报告类型计 1 份; 请求前预检, 成功保存后按实际成功份数扣减
    # 限额从数据库 report_limits 表读取 (用户级 → Agent 级默认 3 → 全局 → settings)
    if user_id and agent_id:
        from src.api.ip_user_resolver import (
            check_daily_report_limit,
            count_requested_docs,
        )

        requested_docs = count_requested_docs(list(report_types))
        allowed, current_count, effective_limit = await check_daily_report_limit(
            user_id, agent_id, requested_count=requested_docs
        )
        if not allowed:
            # 当日剩余额度 (0=已用完; >0 但 < requested_docs=不足以覆盖所选文档类型)
            remaining = max(0, effective_limit - current_count)
            if remaining <= 0:
                limit_msg = (
                    f"您今日的文档生成次数已达上限 ({current_count}/{effective_limit})。"
                    f"每日限额将在北京时间次日 0 点重置, 届时可继续使用。"
                )
            else:
                limit_msg = (
                    f"您今日文档生成剩余次数为 {remaining}，"
                    f"不足以生成本次请求的 {requested_docs} 份文档"
                    f"（每个报告类型计为 1 份）。"
                    f"每日限额为 {effective_limit} 份，已用 {current_count} 份。"
                    f"每日限额将在北京时间次日 0 点重置, 届时可继续使用。"
                )
            if request.stream:
                # 流式: 发送友好提示后关闭 SSE (delta.remaining 与 researcher 字段对齐)
                async def _limit_exceeded_stream() -> Any:
                    completion_id = f"chatcmpl-{uuid.uuid4().hex[:24]}"
                    chunk = {
                        "id": completion_id,
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": request.model,
                        "choices": [
                            {
                                "index": 0,
                                "delta": {
                                    "content": limit_msg,
                                    "remaining": remaining,
                                },
                                "finish_reason": None,
                            }
                        ],
                    }
                    yield f"data: {orjson.dumps(chunk).decode('utf-8')}\n\n"
                    done_chunk = {
                        "id": completion_id,
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": request.model,
                        "choices": [
                            {
                                "index": 0,
                                "delta": {},
                                "finish_reason": "stop",
                            }
                        ],
                    }
                    yield f"data: {orjson.dumps(done_chunk).decode('utf-8')}\n\n"
                    yield "data: [DONE]\n\n"

                return StreamingResponse(
                    _limit_exceeded_stream(),
                    media_type="text/event-stream",
                    headers={
                        "Cache-Control": "no-cache, no-transform",
                        "Connection": "keep-alive",
                        "X-Accel-Buffering": "no",
                        "X-Session-Id": session_id,
                    },
                )
            # 非流式: 返回 JSON 错误 (error.remaining 供前端结构化读取)
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "message": limit_msg,
                        "type": "rate_limit_exceeded",
                        "code": "daily_report_limit",
                        "remaining": remaining,
                    }
                },
                headers={"X-Session-Id": session_id},
            )

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
                # no-transform: 禁止中间代理改写/缓冲 SSE 体
                "Cache-Control": "no-cache, no-transform",
                "Connection": "keep-alive",
                # 禁用 Nginx 等反向代理对 SSE 的缓冲, 保证进度帧实时到达浏览器
                "X-Accel-Buffering": "no",
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
        # 会话持久化: 保存 assistant 消息到 chat_messages (含报告元数据供历史恢复)
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
                        "report_ids": docbot_response.report_ids or [],
                        "reports": docbot_response.reports or [],
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
    # 报告元数据提升到外层, 供流结束后写入 chat_messages.message_metadata
    persisted_report_ids: list[str] = []
    persisted_reports_meta: list[dict[str, Any]] = []

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
            # save_reports 节点入库后即扣减; 若节点已扣减则跳过, 避免 SSE 后半段断连漏计
            usage_charged = False

            # 立即推送启动帧, 避免首节点耗时导致前端长时间空白
            start_msg = "\n\n> **[开始生成]** 文档生成流水线已启动，请稍候…\n"
            yield _sse_chunk({"content": start_msg})
            collected_content.append(start_msg)

            # 用队列合并 graph 事件与心跳: 长节点执行期间每 8s 推送一次,
            # 防止浏览器/代理侧看起来像「对话框无消息」
            event_queue: asyncio.Queue[tuple[str, Any]] = asyncio.Queue()

            async def _produce_graph_events() -> None:
                try:
                    async for event in graph.astream(
                        initial_state, config=graph_config, stream_mode="updates"
                    ):
                        await event_queue.put(("event", event))
                except Exception as exc:  # noqa: BLE001 — 交由消费侧统一处理
                    await event_queue.put(("error", exc))
                finally:
                    await event_queue.put(("done", None))

            producer = asyncio.create_task(_produce_graph_events())
            heartbeat_count = 0
            try:
                while True:
                    try:
                        kind, payload = await asyncio.wait_for(event_queue.get(), timeout=8.0)
                    except asyncio.TimeoutError:
                        heartbeat_count += 1
                        # 心跳不写入 collected_content, 避免污染落库的会话正文
                        yield _sse_chunk(
                            {
                                "content": (
                                    f"\n\n> **[进行中]** 仍在生成文档"
                                    f"（已等待约 {heartbeat_count * 8} 秒）…\n"
                                )
                            }
                        )
                        continue

                    if kind == "done":
                        break
                    if kind == "error":
                        raise payload

                    event = payload
                    for node_name, delta in event.items():
                        if not isinstance(delta, dict):
                            continue
                        final_state.update(delta)

                        # 入库完成即扣减 (先于后续 SSE 推送, 降低客户端断连漏计风险)
                        if node_name == "save_reports":
                            if delta.get("daily_usage_charged"):
                                usage_charged = True
                            else:
                                early_ids = [
                                    str(r.get("report_id", ""))
                                    for r in (delta.get("final_reports") or [])
                                    if isinstance(r, dict) and r.get("report_id")
                                ]
                                usage_charged = await _charge_daily_usage_if_needed(
                                    user_id=str(initial_state.get("user_id") or ""),
                                    agent_id=str(initial_state.get("agent_id") or ""),
                                    report_ids=early_ids,
                                    already_charged=usage_charged,
                                    session_id=session_id,
                                )

                        label = node_label.get(node_name, node_name)
                        progress = f"\n\n> **[{label}]** "
                        if node_name == "spawn_b_tasks":
                            report_count = len(delta.get("report_tasks", []))
                            progress += f"已派发 {report_count} 个报告任务\n"
                        elif node_name == "save_reports":
                            progress += "报告保存完成\n"
                        elif node_name == "final_reviewer_g":
                            progress += "终审完成\n"
                        else:
                            progress += "\n"

                        yield _sse_chunk({"content": progress})
                        if progress:
                            collected_content.append(progress)
                        # 背压: 让出控制权
                        await asyncio.sleep(0.001)
            finally:
                if not producer.done():
                    producer.cancel()
                    try:
                        await producer
                    except (asyncio.CancelledError, Exception):
                        pass

            # 输出最终报告内容 (从 final_reports 列表提取, save_reports_node 已持久化到 DB)
            final_reports = final_state.get("final_reports") or []
            if final_state.get("daily_usage_charged"):
                usage_charged = True
            # spawn_b_tasks_node 收集的子图错误 (用于诊断)
            pipeline_errors = final_state.get("errors") or []

            if not final_reports:
                # 诊断: 输出具体错误信息, 便于定位失败原因
                if pipeline_errors:
                    err_detail = "; ".join(str(e)[:200] for e in pipeline_errors[:5])
                    hint = (
                        f"\n\n*未生成报告内容 (流水线错误)*\n\n"
                        f"**错误详情 ({len(pipeline_errors)} 项)**:\n"
                        f"```\n{err_detail}\n```"
                    )
                else:
                    hint = "\n\n*未生成报告内容 (可能代码仓库为空或同步未完成)*"
                collected_content.append(hint)
                yield _sse_chunk({"content": hint})
            else:
                # 推送每份报告的元信息 (含 download_urls, 前端用于构造下载链接)
                summaries: list[str] = []
                for rpt in final_reports:
                    if not isinstance(rpt, dict):
                        continue
                    rid = rpt.get("report_id", "")
                    if rid:
                        persisted_report_ids.append(rid)
                    title = rpt.get("title") or rpt.get("report_type", "")
                    summary = rpt.get("summary", "")
                    download_urls = rpt.get("download_urls") or _build_download_urls(str(rid))
                    if summary:
                        summaries.append(f"### {title}\n\n{summary}")
                    report_meta = {
                        "report_id": rid,
                        "report_type": rpt.get("report_type", ""),
                        "title": title,
                        "summary": summary,
                        "download_urls": download_urls,
                    }
                    persisted_reports_meta.append(report_meta)
                    # 推送单份报告元信息 (前端用于展示报告卡片 + 下载链接)
                    yield _sse_chunk({"report": report_meta})

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

                # 推送 report_ids + reports 元信息 (前端用于构造下载链接)
                if persisted_report_ids:
                    yield _sse_chunk({"report_ids": persisted_report_ids})
                if persisted_reports_meta:
                    yield _sse_chunk({"reports": persisted_reports_meta})

                # 兜底: 节点未扣减时再补扣一次 (mock 图 / 旧节点无 daily_usage_charged)
                await _charge_daily_usage_if_needed(
                    user_id=str(initial_state.get("user_id") or ""),
                    agent_id=str(initial_state.get("agent_id") or ""),
                    report_ids=persisted_report_ids,
                    already_charged=usage_charged,
                    session_id=session_id,
                )

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

    # 会话持久化: 保存 assistant 消息 (含 reports 元数据, 刷新会话后可恢复下载链接)
    if save_user_id and save_agent_id and collected_content:
        full_response = "".join(collected_content)
        if full_response:
            await _persist_assistant_message(
                session_id,
                save_agent_id,
                save_user_id,
                full_response,
                metadata={
                    "intent": "generate_docs",
                    "report_ids": persisted_report_ids,
                    "reports": persisted_reports_meta,
                },
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
    content = ""
    usage: dict[str, Any] = {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
    }
    report_ids: list[str] = []
    reports_meta: list[dict[str, Any]] = []
    usage_charged = False

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
        try:
            graph = await _get_graph()
            final_state = await asyncio.wait_for(
                graph.ainvoke(initial_state, config=graph_config),
                timeout=settings.graph_total_timeout,
            )
            # 从 final_reports 列表提取内容 (save_reports_node 已持久化到 DB)
            final_reports = final_state.get("final_reports") or []
            usage_charged = bool(final_state.get("daily_usage_charged"))
            # spawn_b_tasks_node 收集的子图错误 (用于诊断)
            pipeline_errors = final_state.get("errors") or []

            if not final_reports:
                # 诊断: 输出具体错误信息, 便于定位失败原因
                if pipeline_errors:
                    err_detail = "; ".join(str(e)[:200] for e in pipeline_errors[:5])
                    content = (
                        f"未生成报告内容 (流水线错误)\n\n"
                        f"错误详情 ({len(pipeline_errors)} 项):\n{err_detail}"
                    )
                else:
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
                    download_urls = rpt.get("download_urls", {})
                    if summary:
                        summaries.append(f"### {title}\n\n{summary}")
                    reports_meta.append(
                        {
                            "report_id": rid,
                            "report_type": rpt.get("report_type", ""),
                            "title": title,
                            "summary": summary,
                            "download_urls": download_urls,
                        }
                    )
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
            reports_meta = []

    # 文档生成成功后按实际成功份数递增每日计数
    # save_reports 已扣减时跳过; 失败/空结果不计数
    _uid_final = str(initial_state.get("user_id") or "")
    _aid_final = str(initial_state.get("agent_id") or "")
    if (
        content
        and "文档生成失败" not in content
        and "未生成报告内容" not in content
    ):
        await _charge_daily_usage_if_needed(
            user_id=_uid_final,
            agent_id=_aid_final,
            report_ids=report_ids,
            already_charged=usage_charged,
            session_id=session_id,
        )

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
        reports=reports_meta if reports_meta else None,
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
    # 附带 title/summary/download_urls, 供前端刷新会话后恢复「生成的文档」下载区
    # (save_reports_node 将 title 写入 query 字段, summary 写入 report_summary)
    result: list[dict[str, Any]] = []
    for r in reports:
        rid = str(r.get("report_id") or "")
        title = (r.get("query", "") or r.get("report_type_label", "") or "技术文档")[:200]
        result.append(
            {
                "report_id": rid,
                "session_id": r.get("session_id"),
                "query": title,
                "report_format": r.get("report_format", "markdown"),
                "agent_role": r.get("agent_role"),
                "report_type": r.get("report_type_label") or r.get("agent_role") or "",
                "title": title,
                "summary": r.get("report_summary") or "",
                "download_urls": _build_download_urls(rid),
                "created_at": r.get("created_at"),
                "updated_at": r.get("updated_at"),
            }
        )
    return result


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

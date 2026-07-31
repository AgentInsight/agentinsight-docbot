"""agentinsight-docbot server.py

FastAPI 启动入口, 含:
- 系统 MCP 子进程启动 (mcp-server-git + mcp-server-filesystem)
- 路由注册 (chat completions + sessions + repos + reports)
- 健康检查端点 /health
- CORS / 安全响应头中间件

前端演示由独立的 agentinsight-demo 项目负责.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.requests import Request

from src.api.middleware import (
    JWTAuthMiddleware,
    RequestIDMiddleware,
    SecurityHeadersMiddleware,
    close_jwt_middleware,
)
from src.api.repo_routes import router as repo_router
from src.api.routes import router as chat_router
from src.api.session_routes import router as session_router
from src.common.exceptions import AgentError
from src.config.settings import get_settings

logger = logging.getLogger(__name__)

# 后台任务引用保留 (防止 GC 静默取消 asyncio.create_task)
_background_tasks: set[asyncio.Task[None]] = set()

# MCP 子进程句柄 (lifespan 启动, 关闭时终止)
_mcp_subprocesses: list[asyncio.subprocess.Process] = []


def _create_background_task(coro: object) -> asyncio.Task[None]:
    """创建后台任务并保留引用 (防止 GC 静默取消).

    标准模式: set + done_callback(discard), 任务完成后自动从集合移除.
    """
    task: asyncio.Task[None] = asyncio.create_task(coro)  # type: ignore[arg-type]
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return task


def _parse_mcp_args(args_str: str) -> list[str]:
    """解析 MCP 命令参数 (JSON 数组字符串).

    示例:
        '["mcp-server-git"]'
        '["-y", "@modelcontextprotocol/server-filesystem", "/tmp/repos"]'
    """
    if not args_str:
        return []
    try:
        args = json.loads(args_str)
        if isinstance(args, list):
            return [str(a) for a in args]
    except Exception as e:  # noqa: BLE001
        logger.warning("解析 MCP 参数失败 (%s), 使用空列表: %s", args_str, e)
    return []


async def _start_mcp_subprocesses() -> None:
    """启动系统自带 MCP 子进程 (mcp-server-git + mcp-server-filesystem).

    - mcp-server-git: `uvx mcp-server-git` (Python MCP 服务)
    - mcp-server-filesystem: `npx -y @modelcontextprotocol/server-filesystem /tmp/repos`
      (Node.js MCP 服务)

    子进程以 stdio 模式启动, 所有用户共享. GitMCPAdapter 仅提供高级 API,
    不直接管理这些子进程生命周期 (由本函数 + _stop_mcp_subprocesses 统一管理).

    失败不阻断启动 (仅告警), 后续调用方走降级路径.
    """
    settings = get_settings()

    # mcp-server-git (Python uvx)
    git_cmd = settings.mcp_git_command
    git_args = _parse_mcp_args(settings.mcp_git_args)
    if git_cmd:
        logger.info("启动 mcp-server-git 子进程: %s %s", git_cmd, " ".join(git_args))
        try:
            proc = await asyncio.create_subprocess_exec(
                git_cmd,
                *git_args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _mcp_subprocesses.append(proc)
            logger.info("mcp-server-git 子进程已启动 (pid=%s)", proc.pid)
        except FileNotFoundError:
            logger.warning("mcp-server-git 启动失败: 命令 %s 不存在 (跳过)", git_cmd)
        except Exception as e:  # noqa: BLE001
            logger.warning("mcp-server-git 启动异常 (不阻断启动): %s", e)

    # mcp-server-filesystem (Node.js npx)
    fs_cmd = settings.mcp_filesystem_command
    fs_args = _parse_mcp_args(settings.mcp_filesystem_args)
    if fs_cmd:
        logger.info("启动 mcp-server-filesystem 子进程: %s %s", fs_cmd, " ".join(fs_args))
        try:
            proc = await asyncio.create_subprocess_exec(
                fs_cmd,
                *fs_args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _mcp_subprocesses.append(proc)
            logger.info("mcp-server-filesystem 子进程已启动 (pid=%s)", proc.pid)
        except FileNotFoundError:
            logger.warning("mcp-server-filesystem 启动失败: 命令 %s 不存在 (跳过)", fs_cmd)
        except Exception as e:  # noqa: BLE001
            logger.warning("mcp-server-filesystem 启动异常 (不阻断启动): %s", e)


async def _stop_mcp_subprocesses() -> None:
    """停止所有 MCP 子进程 (优雅 terminate + 强制 kill 兜底)."""
    for proc in _mcp_subprocesses:
        if proc.returncode is not None:
            continue
        try:
            proc.terminate()
            try:
                await asyncio.wait_for(proc.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
            logger.info("MCP 子进程 (pid=%s) 已停止", proc.pid)
        except ProcessLookupError:
            pass
        except Exception as e:  # noqa: BLE001
            logger.warning("停止 MCP 子进程异常: %s", e)
    _mcp_subprocesses.clear()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """应用生命周期: 启动时初始化, 关闭时清理."""
    settings = get_settings()
    logging.basicConfig(level=settings.log_level)
    logger.info("agentinsight-docbot 启动中 (env=%s)", settings.env)

    # 1. 启动系统自带 MCP 子进程 (mcp-server-git + mcp-server-filesystem)
    # 失败不阻断启动 (仅告警), 后续调用方走降级路径
    await _start_mcp_subprocesses()

    # 2. PostgreSQL 业务表初始化 (AGENTS.md 第 6 章核心约定)
    # 执行 scripts/init.sql, 所有 DDL 幂等 (IF NOT EXISTS / CREATE OR REPLACE)
    # 失败不阻断启动 (仅告警), depends_on service_healthy 已保证 Postgres 就绪
    # 不推荐依赖 postgres 容器 /docker-entrypoint-initdb.d/ (仅首次启动执行, 后续不执行)
    try:
        from src.memory.db_initializer import init_database

        await init_database(settings)
    except Exception as e:  # noqa: BLE001
        logger.warning("PostgreSQL 业务表初始化失败 (不阻断启动): %s", e)

    # 3. 显式同步 ensure Qdrant 集合
    # 必须同步等待完成, 避免新环境首请求竞态 (后台任务可能在集合未就绪时被查询)
    # 失败不阻断启动 (仅告警), 后续业务方法自保 _ensure_collection_once 兜底
    async def _ensure_qdrant_collection() -> None:
        try:
            from src.rag.qdrant_manager import get_qdrant_manager

            mgr = get_qdrant_manager()
            await mgr.ensure_collection()  # 幂等, 不存在则创建
            logger.info("Qdrant 集合 %s 已就绪", mgr.settings.qdrant_collection)
        except Exception as e:  # noqa: BLE001
            logger.warning("Qdrant ensure_collection 失败 (不阻断启动): %s", e)

    await _ensure_qdrant_collection()

    # 4. Embeddings 批量预热 (后台执行, 不阻塞启动)
    # 触发 TEI 模型加载, 避免首次真实调用冷启动; 失败不阻断启动
    async def _warmup_embeddings() -> None:
        try:
            from src.rag.embeddings import warmup_embeddings

            await warmup_embeddings()
        except Exception as e:  # noqa: BLE001
            logger.warning("Embeddings 预热失败 (不阻断): %s", e)

    _create_background_task(_warmup_embeddings())

    # 5. LangGraph docbot 图预热 (后台任务触发首次构建, 首次请求直接复用单例)
    # 复用 routes._get_graph() 全局单例 (懒加载), 后台触发首次构建; 失败不阻断启动
    async def _warmup_graph() -> None:
        try:
            from src.api.routes import _get_graph

            await _get_graph()  # 触发首次构建并存入全局单例
            logger.info("LangGraph docbot 图已预热 (全局单例)")
        except Exception as e:  # noqa: BLE001
            logger.warning("图预热失败 (不阻断启动, 首次请求时重试): %s", e)

    _create_background_task(_warmup_graph())

    # 6. v6-P0-A: 容器启动时清理 RAG 检索结果缓存, 避免跨容器持久化污染
    # Redis 缓存跨容器持久化会导致过时空结果长期遮蔽新索引数据
    async def _invalidate_rag_cache_on_startup() -> None:
        try:
            from src.common.redis_client import get_redis_client

            redis = await get_redis_client(settings)
            if redis is None:
                return
            # 使用 SCAN 避免阻塞 Redis (禁用 KEYS)
            # 缓存键格式: {agent_id}:{user_id}:rag:* (见 _cache_key 方法)
            cursor = b"0"
            total_deleted = 0
            while True:
                cursor, keys = await redis.scan(
                    cursor=cursor,
                    match=f"{settings.agent_id}:*:rag:*",
                    count=200,
                )
                if keys:
                    await redis.delete(*keys)
                    total_deleted += len(keys)
                # cursor 类型可能是 bytes 或 int
                if cursor == b"0" or cursor == 0:
                    break
            if total_deleted > 0:
                logger.info("v6-P0-A: 容器启动清理 RAG 缓存 %d 条", total_deleted)
        except Exception as e:  # noqa: BLE001
            logger.warning("v6-P0-A: 清理 RAG 缓存失败 (不阻断启动): %s", e)

    _create_background_task(_invalidate_rag_cache_on_startup())

    yield

    # ===== 关闭阶段 (按启动逆序释放) =====

    # 停止系统自带 MCP 子进程
    await _stop_mcp_subprocesses()

    # 关闭 GitMCPAdapter 单例 (释放临时资源, 不终止 MCP 子进程)
    try:
        from src.tools.git_mcp import get_git_mcp_adapter

        await get_git_mcp_adapter().close()
    except Exception as e:  # noqa: BLE001
        logger.warning("GitMCPAdapter 关闭异常: %s", e)

    # 关闭全局 Redis 单例 (由 common.redis_client 统一工厂创建, lifespan 统一关闭)
    from src.common.redis_client import close_redis_client

    await close_redis_client()

    # 关闭 JWTAuthMiddleware 的 httpx.AsyncClient (纯 ASGI middleware 无法从 app 获取实例)
    await close_jwt_middleware()

    # 关闭 asyncpg 业务表连接池 (优雅 shutdown, 避免连接泄漏)
    from src.memory.db_initializer import close_pool

    await close_pool()

    # 关闭 Checkpointer 的 psycopg 连接池 (优雅 shutdown)
    from src.memory.checkpointer import close_checkpointer_pool

    await close_checkpointer_pool()

    logger.info("agentinsight-docbot 已关闭")


def create_app() -> FastAPI:
    """创建 FastAPI 应用."""
    settings = get_settings()

    app = FastAPI(
        title="agentinsight-docbot",
        description="根据代码仓库一键生成技术文档的智能体",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.env == "dev" else None,
        redoc_url=None,
        openapi_url="/openapi.json" if settings.env == "dev" else None,
    )

    # 中间件注册 (Starlette 反向执行, 最后添加的最先执行)
    # 1. RequestIDMiddleware: 最外层, 注入 X-Request-ID (纯 ASGI)
    app.add_middleware(RequestIDMiddleware)

    # 2. SecurityHeadersMiddleware: 安全响应头 (不可绕过)
    app.add_middleware(SecurityHeadersMiddleware)

    # 3. JWTAuthMiddleware: JWT 身份解析, 注入 contextvars
    app.add_middleware(JWTAuthMiddleware, settings=settings)

    # 4. CORSMiddleware: 跨域 (最内层, 业务请求处理前)
    allow_credentials = "*" not in settings.cors_allow_origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=allow_credentials,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    # 健康检查端点 (容器健康检查)
    @app.get("/health")
    async def health() -> JSONResponse:
        return JSONResponse(
            status_code=200,
            content={
                "status": "ok",
                "service": "agentinsight-docbot",
                "version": "1.0.0",
            },
        )

    # 路由注册:
    # - /v1/chat/completions (OpenAI 兼容端点 + 报告生成 + SSE 流)
    # - /v1/models / /v1/reports (报告查询/下载)
    app.include_router(chat_router)

    # - /v1/sessions (会话管理: 列表/创建/删除/消息分页)
    app.include_router(session_router)

    # - /v1/repos (用户代码仓库 CRUD + test + sync)
    app.include_router(repo_router)

    # 全局异常处理器 (结构化 JSON 错误响应, 符合 OpenAI 兼容 API 规范)
    @app.exception_handler(AgentError)
    async def agent_error_handler(request: Request, exc: AgentError) -> JSONResponse:
        """捕获 Agent 系统自定义异常, 返回结构化错误响应."""
        logger.warning(
            "AgentError: %s (code=%s, http_status=%s)",
            exc.message,
            exc.code,
            exc.http_status,
        )
        return JSONResponse(
            status_code=exc.http_status,
            content={
                "error": {
                    "message": exc.message,
                    "type": exc.__class__.__name__,
                    "code": exc.code,
                }
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        """捕获所有未处理异常, 返回 500 JSON (避免 Starlette 默认格式泄露堆栈)."""
        logger.exception("Unhandled exception: %s", exc)
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "message": "Internal Server Error",
                    "type": "internal_error",
                    "code": "internal_error",
                }
            },
        )

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8068,
        reload=False,
        log_level=get_settings().log_level.lower(),
    )

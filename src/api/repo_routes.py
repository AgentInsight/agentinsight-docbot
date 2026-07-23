"""用户代码仓库 CRUD + 测试 + 同步端点.

端点列表:
- GET    /v1/repos                          列出当前用户所有仓库
- GET    /v1/repos/{repo_id}                获取单个仓库 (不返回敏感字段原文)
- POST   /v1/repos                          创建仓库配置 (敏感字段 AES-GCM 加密后存入)
- PUT    /v1/repos/{repo_id}                更新仓库配置
- DELETE /v1/repos/{repo_id}                删除仓库配置
- POST   /v1/repos/{repo_id}/test           测试连接 (调用 GitMCPAdapter.test_connection)
- POST   /v1/repos/{repo_id}/sync           触发克隆/拉取 + 索引到 Qdrant
- GET    /v1/repos/{repo_id}/sync-status    查询同步状态

数据隔离:
- 所有查询带 agent_id + user_id (复合索引)
- user_id 由 JWT 中间件注入 (contextvars)
- agent_id = agent_name = 'agentinsight-docbot'

安全约束 (属第 11 章安全硬约束):
- API 响应禁止返回敏感字段原文, 仅返回 has_token/has_username 等标志位
- 敏感字段加密用 AES-GCM (密钥 settings.git_credential_key 环境变量注入)
- 密钥仅创建/更新时接受明文, 立即加密后丢弃明文
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any, Literal

import asyncpg
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from src.api.middleware import get_request_agent_id, get_request_user_id
from src.config.settings import get_settings
from src.memory.db_initializer import get_pool
from src.tools.git_mcp import (
    decrypt_credential,
    encrypt_credential,
    get_git_mcp_adapter,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/repos", tags=["repo-management"])

# 后台任务引用保留 (防止 GC 静默取消 asyncio.create_task)
_background_sync_tasks: set[asyncio.Task[Any]] = set()


def _create_background_task(coro: Any) -> asyncio.Task[Any]:
    """创建后台任务并保留引用 (防止 GC 静默取消)."""
    task = asyncio.create_task(coro)
    _background_sync_tasks.add(task)
    task.add_done_callback(_background_sync_tasks.discard)
    return task


# ========== Pydantic 请求/响应模型 ==========


class RepoCreateRequest(BaseModel):
    """创建仓库配置请求.

    敏感字段 (token/password/ssh_key/ssh_passphrase) 接受明文,
    立即加密后丢弃明文 (属第 11 章安全硬约束).
    """

    repo_name: str = Field(..., min_length=1, max_length=256, description="仓库名称 (1-256 字符)")
    platform: Literal[
        "github", "gitlab", "gitee", "bitbucket", "coding", "gitea", "custom"
    ] = Field(..., description="代码托管平台")
    repo_url: str = Field(..., min_length=1, max_length=1024, description="HTTP(S) 或 SSH URL")
    default_branch: str = Field("main", description="默认分支")
    auth_type: Literal["none", "token", "password", "ssh_key"] = Field("none", description="认证方式")
    token: str | None = Field(None, description="GitHub/GitLab PAT (明文, 立即加密后丢弃)")
    username: str | None = Field(None, description="用户名 (password 模式)")
    password: str | None = Field(None, description="密码 (password 模式, 明文, 立即加密后丢弃)")
    ssh_key: str | None = Field(None, description="SSH 私钥 (ssh_key 模式, 明文, 立即加密后丢弃)")
    ssh_passphrase: str | None = Field(None, description="SSH key passphrase (明文, 立即加密后丢弃)")
    clone_depth: int = Field(0, ge=0, description="克隆深度 (0=完整克隆, >0=浅克隆深度)")
    enabled: bool = Field(True, description="是否启用")


class RepoUpdateRequest(BaseModel):
    """更新仓库配置请求.

    所有字段可选, 未传字段不更新.
    敏感字段传值则加密覆盖, 不传则保留原值.
    """

    repo_name: str | None = Field(None, min_length=1, max_length=256)
    default_branch: str | None = None
    auth_type: Literal["none", "token", "password", "ssh_key"] | None = None
    token: str | None = None
    username: str | None = None
    password: str | None = None
    ssh_key: str | None = None
    ssh_passphrase: str | None = None
    clone_depth: int | None = Field(None, ge=0)
    enabled: bool | None = None


class RepoResponse(BaseModel):
    """仓库配置响应 (不含敏感字段原文).

    has_token/has_username/has_password/has_ssh_key 为布尔标志位,
    表示数据库是否存储对应加密字段 (属第 11 章安全硬约束).
    """

    id: str
    repo_name: str
    platform: str
    repo_url: str
    default_branch: str
    auth_type: str
    has_token: bool
    has_username: bool
    has_password: bool
    has_ssh_key: bool
    clone_depth: int
    enabled: bool
    last_synced_at: str | None
    last_sync_status: str | None
    last_sync_error: str | None
    created_at: str
    updated_at: str


# ========== 辅助函数 ==========


def _get_user_agent() -> tuple[str, str]:
    """从请求上下文获取 user_id 和 agent_id.

    Returns:
        (user_id, agent_id)

    Raises:
        HTTPException: 401 user_id 未解析 / 500 agent_id 未解析
    """
    user_id = get_request_user_id()
    agent_id = get_request_agent_id()
    if not user_id:
        raise HTTPException(status_code=401, detail="无法解析用户身份 (缺少 user_id)")
    if not agent_id:
        raise HTTPException(status_code=500, detail="无法解析 Agent 身份 (缺少 agent_id)")
    return user_id, agent_id


def _row_to_response(row: asyncpg.Record | dict[str, Any]) -> RepoResponse:
    """将数据库行转换为 RepoResponse (不含敏感字段).

    安全约束: 仅返回 has_xxx 标志位, 不返回 encrypted_xxx 原文.
    """
    if isinstance(row, asyncpg.Record):
        data = dict(row)
    else:
        data = row

    last_synced_at = data.get("last_synced_at")
    created_at = data.get("created_at")
    updated_at = data.get("updated_at")

    return RepoResponse(
        id=str(data.get("id")),
        repo_name=data.get("repo_name", ""),
        platform=data.get("platform", ""),
        repo_url=data.get("repo_url", ""),
        default_branch=data.get("default_branch", "main"),
        auth_type=data.get("auth_type", "none"),
        has_token=bool(data.get("encrypted_token")),
        has_username=bool(data.get("encrypted_username")),
        has_password=bool(data.get("encrypted_password")),
        has_ssh_key=bool(data.get("encrypted_ssh_key")),
        clone_depth=int(data.get("clone_depth", 0)),
        enabled=bool(data.get("enabled", True)),
        last_synced_at=last_synced_at.isoformat() if last_synced_at else None,
        last_sync_status=data.get("last_sync_status"),
        last_sync_error=data.get("last_sync_error"),
        created_at=created_at.isoformat() if created_at else "",
        updated_at=updated_at.isoformat() if updated_at else "",
    )


def _load_repo_config(row: dict[str, Any]) -> dict[str, Any]:
    """从数据库行加载完整 repo_config (含解密后的敏感字段).

    供 test_connection / sync 端点使用 (不在 API 响应中返回).
    """
    settings = get_settings()
    key = settings.git_credential_key
    return {
        "repo_url": row.get("repo_url", ""),
        "default_branch": row.get("default_branch", "main"),
        "clone_depth": int(row.get("clone_depth", 0)),
        "auth_type": row.get("auth_type", "none"),
        "token": decrypt_credential(row.get("encrypted_token"), key),
        "username": decrypt_credential(row.get("encrypted_username"), key),
        "password": decrypt_credential(row.get("encrypted_password"), key),
        "ssh_key": decrypt_credential(row.get("encrypted_ssh_key"), key),
        "ssh_passphrase": decrypt_credential(row.get("ssh_passphrase"), key),
    }


async def _fetch_repo_row(pool: Any, repo_id: str, user_id: str, agent_id: str) -> dict[str, Any] | None:
    """查询仓库行 (含加密字段), 返回 dict 或 None."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT id, agent_id, user_id, repo_name, platform, repo_url,
                   default_branch, auth_type, encrypted_token, encrypted_username,
                   encrypted_password, encrypted_ssh_key, ssh_passphrase,
                   clone_depth, enabled, last_synced_at, last_sync_status,
                   last_sync_error, created_at, updated_at
              FROM user_git_repos
             WHERE id = $1 AND agent_id = $2 AND user_id = $3
            """,
            repo_id,
            agent_id,
            user_id,
        )
    return dict(row) if row else None


# ========== 端点实现 ==========


@router.get("")
async def list_repos() -> list[dict[str, Any]]:
    """列出当前用户所有仓库 (按 updated_at DESC 排序).

    返回: [RepoResponse.model_dump()] (不含敏感字段)
    """
    user_id, agent_id = _get_user_agent()
    pool = await get_pool()

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, agent_id, user_id, repo_name, platform, repo_url,
                   default_branch, auth_type, encrypted_token, encrypted_username,
                   encrypted_password, encrypted_ssh_key, ssh_passphrase,
                   clone_depth, enabled, last_synced_at, last_sync_status,
                   last_sync_error, created_at, updated_at
              FROM user_git_repos
             WHERE agent_id = $1 AND user_id = $2
             ORDER BY updated_at DESC
            """,
            agent_id,
            user_id,
        )

    return [_row_to_response(r).model_dump() for r in rows]


@router.get("/{repo_id}")
async def get_repo(repo_id: str) -> dict[str, Any]:
    """获取单个仓库 (不返回敏感字段原文)."""
    user_id, agent_id = _get_user_agent()
    pool = await get_pool()

    row = await _fetch_repo_row(pool, repo_id, user_id, agent_id)
    if not row:
        raise HTTPException(status_code=404, detail="仓库不存在")

    return _row_to_response(row).model_dump()


@router.post("", status_code=201)
async def create_repo(request: RepoCreateRequest) -> dict[str, Any]:
    """创建仓库配置.

    敏感字段 (token/password/ssh_key/ssh_passphrase) 接受明文,
    立即 AES-GCM 加密后丢弃明文 (属第 11 章安全硬约束).
    """
    user_id, agent_id = _get_user_agent()
    settings = get_settings()
    key = settings.git_credential_key

    # 校验: 启用敏感认证时必须提供对应凭据
    if request.auth_type == "token" and not request.token:
        raise HTTPException(status_code=400, detail="auth_type=token 时必须提供 token")
    if request.auth_type == "password" and not (request.username and request.password):
        raise HTTPException(
            status_code=400, detail="auth_type=password 时必须提供 username 和 password"
        )
    if request.auth_type == "ssh_key" and not request.ssh_key:
        raise HTTPException(status_code=400, detail="auth_type=ssh_key 时必须提供 ssh_key")

    # 加密敏感字段 (明文立即丢弃)
    encrypted_token = encrypt_credential(request.token, key)
    encrypted_username = encrypt_credential(request.username, key)
    encrypted_password = encrypt_credential(request.password, key)
    encrypted_ssh_key = encrypt_credential(request.ssh_key, key)
    encrypted_ssh_passphrase_col = encrypt_credential(request.ssh_passphrase, key)

    repo_id = uuid.uuid4().hex

    pool = await get_pool()
    async with pool.acquire() as conn:
        try:
            await conn.execute(
                """
                INSERT INTO user_git_repos
                    (id, agent_id, user_id, repo_name, platform, repo_url,
                     default_branch, auth_type, encrypted_token, encrypted_username,
                     encrypted_password, encrypted_ssh_key, ssh_passphrase,
                     clone_depth, enabled, last_sync_status)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
                """,
                repo_id,
                agent_id,
                user_id,
                request.repo_name,
                request.platform,
                request.repo_url,
                request.default_branch,
                request.auth_type,
                encrypted_token,
                encrypted_username,
                encrypted_password,
                encrypted_ssh_key,
                encrypted_ssh_passphrase_col,
                request.clone_depth,
                request.enabled,
                "never",
            )
        except asyncpg.UniqueViolationError as e:
            raise HTTPException(status_code=409, detail="仓库已存在") from e

    # 重新查询以获取 created_at / updated_at
    row = await _fetch_repo_row(pool, repo_id, user_id, agent_id)
    return _row_to_response(row).model_dump() if row else {"id": repo_id}


@router.put("/{repo_id}")
async def update_repo(repo_id: str, request: RepoUpdateRequest) -> dict[str, Any]:
    """更新仓库配置.

    敏感字段传值则加密覆盖, 不传则保留原值.
    auth_type 切换为 none 时, 清空所有加密字段.
    """
    user_id, agent_id = _get_user_agent()
    settings = get_settings()
    key = settings.git_credential_key
    pool = await get_pool()

    existing = await _fetch_repo_row(pool, repo_id, user_id, agent_id)
    if not existing:
        raise HTTPException(status_code=404, detail="仓库不存在")

    # 动态构造 SET 子句 (仅更新非 None 字段)
    updates: list[str] = []
    params: list[Any] = []
    param_idx = 1

    if request.repo_name is not None:
        updates.append(f"repo_name = ${param_idx}")
        params.append(request.repo_name)
        param_idx += 1
    if request.default_branch is not None:
        updates.append(f"default_branch = ${param_idx}")
        params.append(request.default_branch)
        param_idx += 1
    if request.auth_type is not None:
        updates.append(f"auth_type = ${param_idx}")
        params.append(request.auth_type)
        param_idx += 1
        # auth_type 切换为 none 时, 清空所有加密字段
        if request.auth_type == "none":
            updates.append("encrypted_token = NULL")
            updates.append("encrypted_username = NULL")
            updates.append("encrypted_password = NULL")
            updates.append("encrypted_ssh_key = NULL")
            updates.append("ssh_passphrase = NULL")

    # 敏感字段: 传值则加密覆盖 (传空字符串则清空)
    if request.token is not None:
        updates.append(f"encrypted_token = ${param_idx}")
        params.append(encrypt_credential(request.token or None, key))
        param_idx += 1
    if request.username is not None:
        updates.append(f"encrypted_username = ${param_idx}")
        params.append(encrypt_credential(request.username or None, key))
        param_idx += 1
    if request.password is not None:
        updates.append(f"encrypted_password = ${param_idx}")
        params.append(encrypt_credential(request.password or None, key))
        param_idx += 1
    if request.ssh_key is not None:
        updates.append(f"encrypted_ssh_key = ${param_idx}")
        params.append(encrypt_credential(request.ssh_key or None, key))
        param_idx += 1
    if request.ssh_passphrase is not None:
        updates.append(f"ssh_passphrase = ${param_idx}")
        params.append(encrypt_credential(request.ssh_passphrase or None, key))
        param_idx += 1
    if request.clone_depth is not None:
        updates.append(f"clone_depth = ${param_idx}")
        params.append(request.clone_depth)
        param_idx += 1
    if request.enabled is not None:
        updates.append(f"enabled = ${param_idx}")
        params.append(request.enabled)
        param_idx += 1

    if not updates:
        # 无字段更新, 直接返回当前状态
        return _row_to_response(existing).model_dump()

    # updated_at 由触发器自动维护
    where_idx = param_idx
    params.extend([repo_id, agent_id, user_id])

    async with pool.acquire() as conn:
        await conn.execute(
            f"""
            UPDATE user_git_repos
               SET {", ".join(updates)}
             WHERE id = ${where_idx} AND agent_id = ${where_idx + 1} AND user_id = ${where_idx + 2}
            """,
            *params,
        )

    row = await _fetch_repo_row(pool, repo_id, user_id, agent_id)
    return _row_to_response(row).model_dump() if row else _row_to_response(existing).model_dump()


@router.delete("/{repo_id}")
async def delete_repo(repo_id: str) -> dict[str, Any]:
    """删除仓库配置.

    同时清理本地克隆目录 (temp/repos/{user_id}/{repo_id}/).
    Qdrant 索引数据保留 (可手动清理 namespace={agent_id}:{user_id}:{repo_id}).
    """
    user_id, agent_id = _get_user_agent()
    pool = await get_pool()

    existing = await _fetch_repo_row(pool, repo_id, user_id, agent_id)
    if not existing:
        raise HTTPException(status_code=404, detail="仓库不存在")

    async with pool.acquire() as conn:
        await conn.execute(
            """
            DELETE FROM user_git_repos
             WHERE id = $1 AND agent_id = $2 AND user_id = $3
            """,
            repo_id,
            agent_id,
            user_id,
        )

    # 清理本地克隆目录
    try:
        adapter = get_git_mcp_adapter()
        repo_path = adapter._repo_path(user_id, repo_id)
        if repo_path.exists():
            await asyncio.to_thread(
                __import__("shutil").rmtree, repo_path, ignore_errors=True
            )
    except Exception as e:  # noqa: BLE001
        logger.warning("清理仓库本地目录失败 (不阻断删除): %s", e)

    return {"id": repo_id, "deleted": True}


@router.post("/{repo_id}/test")
async def test_repo_connection(repo_id: str) -> dict[str, Any]:
    """测试连接 (调用 GitMCPAdapter.test_connection, 不实际克隆).

    通过 git ls-remote 探活, 校验认证凭据是否有效.
    """
    user_id, agent_id = _get_user_agent()
    pool = await get_pool()

    row = await _fetch_repo_row(pool, repo_id, user_id, agent_id)
    if not row:
        raise HTTPException(status_code=404, detail="仓库不存在")

    repo_config = _load_repo_config(row)
    adapter = get_git_mcp_adapter()
    result = await adapter.test_connection(repo_config)

    return {
        "repo_id": repo_id,
        "success": result["success"],
        "message": "连接成功" if result["success"] else (result.get("error") or "连接失败 (检查 URL/认证/网络)"),
    }


@router.post("/{repo_id}/sync", status_code=202)
async def sync_repo(repo_id: str) -> dict[str, Any]:
    """触发克隆/拉取 + 索引到 Qdrant.

    流程 (后台执行):
    1. 克隆仓库到 temp/repos/{user_id}/{repo_id}/ (已存在则 git pull)
    2. 枚举文件 (跳过 .git/node_modules/__pycache__/dist/build/.venv/.next/target/)
    3. 按文件类型分块 (代码 AST / 配置整体 / 文档按章节)
    4. 嵌入 (bge-base-zh-v1.5, 768 维) 写入 Qdrant
       namespace = {agent_id}:{user_id}:{repo_id}
    5. 更新 last_synced_at / last_sync_status / last_sync_error

    返回 202 Accepted, 后台异步执行.
    """
    user_id, agent_id = _get_user_agent()
    pool = await get_pool()

    row = await _fetch_repo_row(pool, repo_id, user_id, agent_id)
    if not row:
        raise HTTPException(status_code=404, detail="仓库不存在")

    # 标记为 syncing
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE user_git_repos
               SET last_sync_status = 'syncing',
                   last_sync_error = NULL
             WHERE id = $1 AND agent_id = $2 AND user_id = $3
            """,
            repo_id,
            agent_id,
            user_id,
        )

    # 后台执行同步任务
    repo_config = _load_repo_config(row)
    _create_background_task(
        _run_sync(repo_id, user_id, agent_id, repo_config)
    )

    return {
        "repo_id": repo_id,
        "status": "syncing",
        "message": "同步任务已启动, 请通过 GET /v1/repos/{repo_id}/sync-status 查询状态",
    }


@router.get("/{repo_id}/sync-status")
async def get_sync_status(repo_id: str) -> dict[str, Any]:
    """查询同步状态.

    返回: {repo_id, last_synced_at, last_sync_status, last_sync_error}
    last_sync_status: never / syncing / success / failed
    """
    user_id, agent_id = _get_user_agent()
    pool = await get_pool()

    row = await _fetch_repo_row(pool, repo_id, user_id, agent_id)
    if not row:
        raise HTTPException(status_code=404, detail="仓库不存在")

    last_synced_at = row.get("last_synced_at")
    return {
        "repo_id": repo_id,
        "last_synced_at": last_synced_at.isoformat() if last_synced_at else None,
        "last_sync_status": row.get("last_sync_status", "never"),
        "last_sync_error": row.get("last_sync_error"),
    }


# ========== 后台同步任务实现 ==========


async def _run_sync(
    repo_id: str,
    user_id: str,
    agent_id: str,
    repo_config: dict[str, Any],
) -> None:
    """后台同步任务: 克隆 → 枚举 → 分块 → 嵌入 → 索引 → 更新状态.

    失败不阻断主流程, 仅更新 last_sync_status / last_sync_error.
    """
    pool = await get_pool()
    adapter = get_git_mcp_adapter()
    settings = get_settings()

    try:
        # 1. 克隆 / 拉取仓库
        repo_path = await adapter.clone_repo(repo_config, user_id, repo_id)

        # 2. 枚举文件
        files = await adapter.list_files(repo_path, pattern="**/*")
        if not files:
            raise RuntimeError("仓库无文件 (可能为空仓库或被 .gitignore 过滤)")

        # 3. 分块 + 嵌入 + 索引到 Qdrant
        namespace = f"{agent_id}:{user_id}:{repo_id}"
        await _index_repo_to_qdrant(
            repo_path=repo_path,
            files=files,
            namespace=namespace,
            user_id=user_id,
            repo_id=repo_id,
            adapter=adapter,
        )

        # 4. 更新同步状态
        async with pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE user_git_repos
                   SET last_synced_at = NOW(),
                       last_sync_status = 'success',
                       last_sync_error = NULL
                 WHERE id = $1 AND agent_id = $2 AND user_id = $3
                """,
                repo_id,
                agent_id,
                user_id,
            )

        logger.info(
            "仓库同步成功: repo_id=%s, user=%s, files=%d, namespace=%s",
            repo_id,
            user_id,
            len(files),
            namespace,
        )

    except Exception as e:  # noqa: BLE001
        logger.warning("仓库同步失败 (不阻断主流程): repo_id=%s, error=%s", repo_id, e)
        try:
            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE user_git_repos
                       SET last_synced_at = NOW(),
                           last_sync_status = 'failed',
                           last_sync_error = $4
                     WHERE id = $1 AND agent_id = $2 AND user_id = $3
                    """,
                    repo_id,
                    agent_id,
                    user_id,
                    str(e)[:500],
                )
        except Exception as update_err:  # noqa: BLE001
            logger.warning("更新同步失败状态异常: %s", update_err)


async def _index_repo_to_qdrant(
    repo_path: str,
    files: list[str],
    namespace: str,
    user_id: str,
    repo_id: str,
    adapter: Any,
) -> None:
    """将仓库文件分块索引到 Qdrant (namespace={agent_id}:{user_id}:{repo_id}).

    分块策略:
    - 代码文件 (.py/.js/.ts/.go/.java/...): 按函数/类 AST 分块 (简化版: 按行数分块)
    - 配置文件 (.yml/.json/.toml/...): 整体作为一个 chunk
    - 文档文件 (.md/.rst/.txt): 按章节分块 (标题层级)

    每个点 payload 含: content, metadata {file_path, language, chunk_type, chunk_index}, namespace, user_id, repo_id.
    """
    from src.rag.embeddings import get_embeddings_client

    # 文件类型识别
    code_exts = {".py", ".js", ".ts", ".go", ".java", ".c", ".cpp", ".h", ".rs", ".rb", ".php", ".swift", ".kt"}
    config_exts = {".yml", ".yaml", ".json", ".toml", ".ini", ".cfg", ".conf", ".env", ".xml"}
    doc_exts = {".md", ".rst", ".txt"}

    # 限制单次索引文件数 (避免超长同步时间, 上限 1000 文件)
    max_files = 1000
    files_to_index = files[:max_files]

    embeddings_client = get_embeddings_client()
    all_points: list[dict[str, Any]] = []
    for file_rel in files_to_index:
        try:
            content = await adapter.read_file(repo_path, file_rel, max_size_mb=2)
        except Exception as e:  # noqa: BLE001
            logger.debug("跳过文件 %s (读取失败): %s", file_rel, e)
            continue

        ext = "." + file_rel.rsplit(".", 1)[-1] if "." in file_rel else ""
        if ext in code_exts:
            chunk_type = "code"
            chunks = _chunk_code(content, file_rel)
        elif ext in config_exts:
            chunk_type = "config"
            chunks = [(content, 0)]
        elif ext in doc_exts:
            chunk_type = "doc"
            chunks = _chunk_doc(content)
        else:
            chunk_type = "text"
            chunks = _chunk_text(content)

        # 语言识别
        language = _detect_language(ext)

        for chunk_text, chunk_idx in chunks:
            if not chunk_text.strip():
                continue
            all_points.append({
                "content": chunk_text,
                "metadata": {
                    "file_path": file_rel,
                    "language": language,
                    "chunk_type": chunk_type,
                    "chunk_index": chunk_idx,
                    "repo_id": repo_id,
                },
            })

        # 每 200 个点批量写入一次 (避免单批过大)
        if len(all_points) >= 200:
            await embeddings_client.embed_and_index(
                texts=[p["content"] for p in all_points],
                namespace=namespace,
                metadata_list=[p["metadata"] for p in all_points],
                user_id=user_id,
            )
            all_points.clear()

    # 写入剩余点
    if all_points:
        await embeddings_client.embed_and_index(
            texts=[p["content"] for p in all_points],
            namespace=namespace,
            metadata_list=[p["metadata"] for p in all_points],
            user_id=user_id,
        )


def _chunk_code(content: str, file_path: str) -> list[tuple[str, int]]:
    """代码分块 (简化版: 按行数分块, 100 行/块, 20 行 overlap).

    生产环境推荐 AST 解析 (按函数/类分块), 此处简化实现保证可用.
    """
    lines = content.split("\n")
    chunk_size = 100
    overlap = 20
    chunks: list[tuple[str, int]] = []
    idx = 0
    i = 0
    while i < len(lines):
        chunk_lines = lines[i : i + chunk_size]
        if not chunk_lines:
            break
        chunks.append(("\n".join(chunk_lines), idx))
        idx += 1
        i += chunk_size - overlap
    return chunks


def _chunk_doc(content: str) -> list[tuple[str, int]]:
    """文档分块 (按章节标题分块).

    Markdown: 按 # / ## / ### 标题分块.
    """
    # 空内容直接返回空列表 (避免产生仅含空字符串的单块)
    if not content:
        return []
    lines = content.split("\n")
    chunks: list[tuple[str, int]] = []
    current: list[str] = []
    idx = 0

    for line in lines:
        # 检测标题行 (# 开头, 不超过 6 级)
        if line.startswith("#") and len(line) > 1 and line[1] in "# ":
            if current:
                chunks.append(("\n".join(current), idx))
                idx += 1
                current = []
        current.append(line)

    if current:
        chunks.append(("\n".join(current), idx))

    return chunks


def _chunk_text(content: str, chunk_size: int = 2000) -> list[tuple[str, int]]:
    """纯文本分块 (按字符数分块)."""
    chunks: list[tuple[str, int]] = []
    for i in range(0, len(content), chunk_size):
        chunks.append((content[i : i + chunk_size], len(chunks)))
    return chunks


def _detect_language(ext: str) -> str:
    """根据扩展名识别编程语言."""
    lang_map = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".go": "go",
        ".java": "java",
        ".c": "c",
        ".cpp": "cpp",
        ".h": "c",
        ".rs": "rust",
        ".rb": "ruby",
        ".php": "php",
        ".swift": "swift",
        ".kt": "kotlin",
        ".md": "markdown",
        ".rst": "rst",
        ".yml": "yaml",
        ".yaml": "yaml",
        ".json": "json",
        ".toml": "toml",
        ".xml": "xml",
    }
    return lang_map.get(ext, "text")


__all__ = ["router"]

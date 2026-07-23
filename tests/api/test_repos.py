"""API 测试: /v1/repos CRUD + test + sync 端点.

不依赖外部服务, 用 mock asyncpg pool + mock GitMCPAdapter 验证:
- GET    /v1/repos              列出仓库
- GET    /v1/repos/{repo_id}    获取仓库 (404 不存在)
- POST   /v1/repos              创建仓库 (敏感字段加密)
- PUT    /v1/repos/{repo_id}    更新仓库 (动态 SET 子句)
- DELETE /v1/repos/{repo_id}    删除仓库 (404 / 200)
- POST   /v1/repos/{repo_id}/test        测试连接
- POST   /v1/repos/{repo_id}/sync        触发同步 (202)
- GET    /v1/repos/{repo_id}/sync-status 查询同步状态

安全约束 (AGENTS.md 第 11 章):
- API 响应禁止返回敏感字段原文, 仅返回 has_xxx 标志位
- 敏感字段 AES-GCM 加密后存入数据库
- 数据隔离: 所有查询带 agent_id + user_id (复合索引)
"""
from __future__ import annotations

from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.api import repo_routes as _rr
from src.api.repo_routes import (
    RepoCreateRequest,
    RepoUpdateRequest,
    _row_to_response,
    create_repo,
    delete_repo,
    get_repo,
    get_sync_status,
    list_repos,
    sync_repo,
    update_repo,
)
# test_repo_connection 以 _rr.test_repo_connection 引用 (避免 pytest 误识别为测试函数)


# ========== 辅助函数: 构造 mock 数据库行 ==========


def _make_repo_row(
    repo_id: str = "test_docbot_repo_uuid_1",
    agent_id: str = "agentinsight-docbot",
    user_id: str = "test_docbot_user_1",
    repo_name: str = "test-repo",
    platform: str = "github",
    repo_url: str = "https://github.com/test/repo.git",
    default_branch: str = "main",
    auth_type: str = "none",
    encrypted_token: str | None = None,
    encrypted_username: str | None = None,
    encrypted_password: str | None = None,
    encrypted_ssh_key: str | None = None,
    ssh_passphrase: str | None = None,
    clone_depth: int = 0,
    enabled: bool = True,
    last_synced_at: datetime | None = None,
    last_sync_status: str | None = "never",
    last_sync_error: str | None = None,
) -> dict[str, Any]:
    """构造数据库行 dict (模拟 asyncpg.Record)."""
    return {
        "id": repo_id,
        "agent_id": agent_id,
        "user_id": user_id,
        "repo_name": repo_name,
        "platform": platform,
        "repo_url": repo_url,
        "default_branch": default_branch,
        "auth_type": auth_type,
        "encrypted_token": encrypted_token,
        "encrypted_username": encrypted_username,
        "encrypted_password": encrypted_password,
        "encrypted_ssh_key": encrypted_ssh_key,
        "ssh_passphrase": ssh_passphrase,
        "clone_depth": clone_depth,
        "enabled": enabled,
        "last_synced_at": last_synced_at,
        "last_sync_status": last_sync_status,
        "last_sync_error": last_sync_error,
        "created_at": datetime(2026, 1, 1, 0, 0, 0),
        "updated_at": datetime(2026, 1, 2, 0, 0, 0),
    }


def _make_mock_pool(fetch_rows: list[dict] | None = None,
                    fetch_row: dict | None = None,
                    execute_result: str = "INSERT 0 1") -> MagicMock:
    """构造 mock asyncpg 连接池.

    Args:
        fetch_rows: fetch 返回的多行 (list)
        fetch_row: fetchrow 返回的单行
        execute_result: execute 返回值 (如 "INSERT 0 1" / "DELETE 1")
    """
    mock_conn = MagicMock()
    mock_conn.fetch = AsyncMock(return_value=fetch_rows or [])
    mock_conn.fetchrow = AsyncMock(return_value=fetch_row)
    mock_conn.execute = AsyncMock(return_value=execute_result)

    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock()
    mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
    return mock_pool


# ========== 测试用例 ==========


@pytest.mark.api
class TestRowToResponse:
    """_row_to_response 辅助函数测试 (敏感字段不外泄)."""

    def test_row_to_response_no_sensitive_fields(self) -> None:
        """响应不应包含加密字段原文."""
        row = _make_repo_row(encrypted_token="enc_token", encrypted_password="enc_pass")
        resp = _row_to_response(row)
        # 禁止出现敏感字段原文
        assert "encrypted_token" not in resp.model_dump()
        assert "encrypted_password" not in resp.model_dump()
        assert "encrypted_ssh_key" not in resp.model_dump()
        assert "ssh_passphrase" not in resp.model_dump()

    def test_row_to_response_has_flags(self) -> None:
        """has_xxx 标志位应正确反映加密字段是否存在."""
        row = _make_repo_row(
            encrypted_token="enc_token",
            encrypted_username="enc_user",
            encrypted_password=None,
            encrypted_ssh_key=None,
        )
        resp = _row_to_response(row)
        assert resp.has_token is True
        assert resp.has_username is True
        assert resp.has_password is False
        assert resp.has_ssh_key is False

    def test_row_to_response_id_to_string(self) -> None:
        """id 应转为字符串."""
        row = _make_repo_row(repo_id=12345)
        resp = _row_to_response(row)
        assert resp.id == "12345"
        assert isinstance(resp.id, str)

    def test_row_to_response_timestamps_iso_format(self) -> None:
        """时间戳应转 ISO 字符串."""
        row = _make_repo_row(last_synced_at=datetime(2026, 1, 1, 12, 0, 0))
        resp = _row_to_response(row)
        assert resp.last_synced_at is not None
        assert "2026-01-01T12:00:00" in resp.last_synced_at
        assert resp.created_at == "2026-01-01T00:00:00"


@pytest.mark.api
class TestListRepos:
    """GET /v1/repos 列出仓库."""

    async def test_list_repos_returns_user_repos_only(self) -> None:
        """仅返回当前用户的仓库 (agent_id + user_id 过滤)."""
        rows = [
            _make_repo_row(repo_id="r1", repo_name="repo1"),
            _make_repo_row(repo_id="r2", repo_name="repo2"),
        ]
        mock_pool = _make_mock_pool(fetch_rows=rows)

        with patch("src.api.repo_routes.get_request_user_id", return_value="test_docbot_user_1"), \
             patch("src.api.repo_routes.get_request_agent_id", return_value="agentinsight-docbot"), \
             patch("src.api.repo_routes.get_pool", AsyncMock(return_value=mock_pool)):
            result = await list_repos()

        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["repo_name"] in ("repo1", "repo2")

    async def test_list_repos_empty(self) -> None:
        """无仓库时返回空列表."""
        mock_pool = _make_mock_pool(fetch_rows=[])

        with patch("src.api.repo_routes.get_request_user_id", return_value="test_docbot_user_1"), \
             patch("src.api.repo_routes.get_request_agent_id", return_value="agentinsight-docbot"), \
             patch("src.api.repo_routes.get_pool", AsyncMock(return_value=mock_pool)):
            result = await list_repos()

        assert result == []

    async def test_list_repos_401_when_no_user(self) -> None:
        """无 user_id 应抛 401."""
        from fastapi import HTTPException

        with patch("src.api.repo_routes.get_request_user_id", return_value=""), \
             patch("src.api.repo_routes.get_request_agent_id", return_value="agentinsight-docbot"), \
             pytest.raises(HTTPException) as exc_info:
            await list_repos()

        assert exc_info.value.status_code == 401


@pytest.mark.api
class TestGetRepo:
    """GET /v1/repos/{repo_id} 获取仓库."""

    async def test_get_repo_returns_repo(self) -> None:
        """存在的仓库应返回详情."""
        row = _make_repo_row(repo_id="test_docbot_repo_1", repo_name="my-repo")
        mock_pool = _make_mock_pool(fetch_row=row)

        with patch("src.api.repo_routes.get_request_user_id", return_value="test_docbot_user_1"), \
             patch("src.api.repo_routes.get_request_agent_id", return_value="agentinsight-docbot"), \
             patch("src.api.repo_routes.get_pool", AsyncMock(return_value=mock_pool)):
            result = await get_repo("test_docbot_repo_1")

        assert result["id"] == "test_docbot_repo_1"
        assert result["repo_name"] == "my-repo"

    async def test_get_repo_404_when_not_found(self) -> None:
        """不存在的仓库应抛 404."""
        from fastapi import HTTPException

        mock_pool = _make_mock_pool(fetch_row=None)

        with patch("src.api.repo_routes.get_request_user_id", return_value="test_docbot_user_1"), \
             patch("src.api.repo_routes.get_request_agent_id", return_value="agentinsight-docbot"), \
             patch("src.api.repo_routes.get_pool", AsyncMock(return_value=mock_pool)), \
             pytest.raises(HTTPException) as exc_info:
            await get_repo("nonexistent_repo")

        assert exc_info.value.status_code == 404


@pytest.mark.api
class TestCreateRepo:
    """POST /v1/repos 创建仓库 (敏感字段加密)."""

    async def test_create_repo_encrypts_sensitive_fields(self) -> None:
        """敏感字段应经过 encrypt_credential."""
        row = _make_repo_row(
            repo_id="new_repo_uuid",
            repo_name="new-repo",
            auth_type="token",
            encrypted_token="encrypted_value",
        )
        mock_pool = _make_mock_pool(fetch_row=row, execute_result="INSERT 0 1")

        # 捕获 encrypt_credential 调用
        encrypt_calls: list[str] = []

        def _fake_encrypt(value: str | None, key: str) -> str | None:
            encrypt_calls.append(value or "")
            return f"encrypted_{value}" if value else None

        request = RepoCreateRequest(
            repo_name="new-repo",
            platform="github",
            repo_url="https://github.com/test/new.git",
            auth_type="token",
            token="ghp_test_token",
        )

        with patch("src.api.repo_routes.get_request_user_id", return_value="test_docbot_user_1"), \
             patch("src.api.repo_routes.get_request_agent_id", return_value="agentinsight-docbot"), \
             patch("src.api.repo_routes.get_pool", AsyncMock(return_value=mock_pool)), \
             patch("src.api.repo_routes.get_settings") as mock_get_settings, \
             patch("src.api.repo_routes.encrypt_credential", side_effect=_fake_encrypt):
            mock_get_settings.return_value.git_credential_key = "test" * 32
            result = await create_repo(request)

        # 敏感字段被加密
        assert any("ghp_test_token" in c for c in encrypt_calls)
        assert result["id"] == "new_repo_uuid"

    async def test_create_repo_400_when_token_missing(self) -> None:
        """auth_type=token 时缺 token 应抛 400."""
        from fastapi import HTTPException

        mock_pool = _make_mock_pool()

        request = RepoCreateRequest(
            repo_name="new-repo",
            platform="github",
            repo_url="https://github.com/test/new.git",
            auth_type="token",
            # token 缺失
        )

        with patch("src.api.repo_routes.get_request_user_id", return_value="test_docbot_user_1"), \
             patch("src.api.repo_routes.get_request_agent_id", return_value="agentinsight-docbot"), \
             patch("src.api.repo_routes.get_pool", AsyncMock(return_value=mock_pool)), \
             patch("src.api.repo_routes.get_settings") as mock_get_settings, \
             pytest.raises(HTTPException) as exc_info:
            mock_get_settings.return_value.git_credential_key = "test" * 32
            await create_repo(request)

        assert exc_info.value.status_code == 400
        assert "token" in exc_info.value.detail

    async def test_create_repo_400_when_password_auth_missing_username(self) -> None:
        """auth_type=password 时缺 username 应抛 400."""
        from fastapi import HTTPException

        mock_pool = _make_mock_pool()
        request = RepoCreateRequest(
            repo_name="new-repo",
            platform="github",
            repo_url="https://github.com/test/new.git",
            auth_type="password",
            password="pass",
            # username 缺失
        )

        with patch("src.api.repo_routes.get_request_user_id", return_value="test_docbot_user_1"), \
             patch("src.api.repo_routes.get_request_agent_id", return_value="agentinsight-docbot"), \
             patch("src.api.repo_routes.get_pool", AsyncMock(return_value=mock_pool)), \
             patch("src.api.repo_routes.get_settings") as mock_get_settings, \
             pytest.raises(HTTPException) as exc_info:
            mock_get_settings.return_value.git_credential_key = "test" * 32
            await create_repo(request)

        assert exc_info.value.status_code == 400

    async def test_create_repo_400_when_ssh_key_missing(self) -> None:
        """auth_type=ssh_key 时缺 ssh_key 应抛 400."""
        from fastapi import HTTPException

        mock_pool = _make_mock_pool()
        request = RepoCreateRequest(
            repo_name="new-repo",
            platform="github",
            repo_url="https://github.com/test/new.git",
            auth_type="ssh_key",
        )

        with patch("src.api.repo_routes.get_request_user_id", return_value="test_docbot_user_1"), \
             patch("src.api.repo_routes.get_request_agent_id", return_value="agentinsight-docbot"), \
             patch("src.api.repo_routes.get_pool", AsyncMock(return_value=mock_pool)), \
             patch("src.api.repo_routes.get_settings") as mock_get_settings, \
             pytest.raises(HTTPException) as exc_info:
            mock_get_settings.return_value.git_credential_key = "test" * 32
            await create_repo(request)

        assert exc_info.value.status_code == 400

    async def test_create_repo_default_auth_type_none(self) -> None:
        """auth_type=none (默认) 时无需敏感字段."""
        row = _make_repo_row(repo_name="pub-repo", auth_type="none")
        mock_pool = _make_mock_pool(fetch_row=row)

        request = RepoCreateRequest(
            repo_name="pub-repo",
            platform="github",
            repo_url="https://github.com/test/pub.git",
        )

        with patch("src.api.repo_routes.get_request_user_id", return_value="test_docbot_user_1"), \
             patch("src.api.repo_routes.get_request_agent_id", return_value="agentinsight-docbot"), \
             patch("src.api.repo_routes.get_pool", AsyncMock(return_value=mock_pool)), \
             patch("src.api.repo_routes.get_settings") as mock_get_settings, \
             patch("src.api.repo_routes.encrypt_credential", return_value=None):
            mock_get_settings.return_value.git_credential_key = "test" * 32
            result = await create_repo(request)

        assert result["auth_type"] == "none"


@pytest.mark.api
class TestUpdateRepo:
    """PUT /v1/repos/{repo_id} 更新仓库."""

    async def test_update_repo_404_when_not_found(self) -> None:
        """更新不存在的仓库应抛 404."""
        from fastapi import HTTPException

        mock_pool = _make_mock_pool(fetch_row=None)
        request = RepoUpdateRequest(repo_name="new-name")

        with patch("src.api.repo_routes.get_request_user_id", return_value="test_docbot_user_1"), \
             patch("src.api.repo_routes.get_request_agent_id", return_value="agentinsight-docbot"), \
             patch("src.api.repo_routes.get_pool", AsyncMock(return_value=mock_pool)), \
             patch("src.api.repo_routes.get_settings") as mock_get_settings, \
             pytest.raises(HTTPException) as exc_info:
            mock_get_settings.return_value.git_credential_key = "test" * 32
            await update_repo("nonexistent", request)

        assert exc_info.value.status_code == 404

    async def test_update_repo_no_changes_returns_existing(self) -> None:
        """无字段更新时返回当前状态 (不执行 UPDATE)."""
        existing = _make_repo_row(repo_id="r1", repo_name="old-name")
        mock_pool = _make_mock_pool(fetch_row=existing)
        request = RepoUpdateRequest()  # 所有字段 None

        with patch("src.api.repo_routes.get_request_user_id", return_value="test_docbot_user_1"), \
             patch("src.api.repo_routes.get_request_agent_id", return_value="agentinsight-docbot"), \
             patch("src.api.repo_routes.get_pool", AsyncMock(return_value=mock_pool)), \
             patch("src.api.repo_routes.get_settings") as mock_get_settings:
            mock_get_settings.return_value.git_credential_key = "test" * 32
            result = await update_repo("r1", request)

        # 应返回已有行
        assert result["repo_name"] == "old-name"

    async def test_update_repo_clears_credentials_when_auth_none(self) -> None:
        """auth_type 切换为 none 时清空所有加密字段."""
        existing = _make_repo_row(
            repo_id="r1",
            auth_type="token",
            encrypted_token="enc_token",
            encrypted_username="enc_user",
            encrypted_password="enc_pass",
        )
        # 更新后返回的行
        updated = _make_repo_row(
            repo_id="r1",
            auth_type="none",
            encrypted_token=None,
            encrypted_username=None,
            encrypted_password=None,
        )
        mock_pool = _make_mock_pool(fetch_row=updated)
        # 第一次 fetch (existing), 第二次 fetch (updated)
        mock_conn = mock_pool.acquire.return_value.__aenter__.return_value
        # _fetch_repo_row 内部使用 pool.acquire, 第二次调用应返回 updated
        mock_conn.fetchrow = AsyncMock(side_effect=[existing, updated])

        request = RepoUpdateRequest(auth_type="none")

        with patch("src.api.repo_routes.get_request_user_id", return_value="test_docbot_user_1"), \
             patch("src.api.repo_routes.get_request_agent_id", return_value="agentinsight-docbot"), \
             patch("src.api.repo_routes.get_pool", AsyncMock(return_value=mock_pool)), \
             patch("src.api.repo_routes.get_settings") as mock_get_settings, \
             patch("src.api.repo_routes.encrypt_credential", return_value=None):
            mock_get_settings.return_value.git_credential_key = "test" * 32
            result = await update_repo("r1", request)

        # 验证 SQL SET 含清空 NULL 子句
        execute_call = mock_conn.execute.call_args
        sql_arg = execute_call.args[0] if execute_call.args else execute_call[0][0]
        assert "encrypted_token = NULL" in sql_arg
        assert "encrypted_password = NULL" in sql_arg


@pytest.mark.api
class TestDeleteRepo:
    """DELETE /v1/repos/{repo_id} 删除仓库."""

    async def test_delete_repo_returns_id_and_deleted_flag(self) -> None:
        """成功删除应返回 {id, deleted: True}."""
        existing = _make_repo_row(repo_id="r1")
        mock_pool = _make_mock_pool(fetch_row=existing, execute_result="DELETE 1")

        with patch("src.api.repo_routes.get_request_user_id", return_value="test_docbot_user_1"), \
             patch("src.api.repo_routes.get_request_agent_id", return_value="agentinsight-docbot"), \
             patch("src.api.repo_routes.get_pool", AsyncMock(return_value=mock_pool)), \
             patch("src.api.repo_routes.get_git_mcp_adapter") as mock_adapter:
            # mock adapter 避免真实文件操作
            mock_adapter.return_value._repo_path.return_value = MagicMock(exists=lambda: False)
            result = await delete_repo("r1")

        assert result["id"] == "r1"
        assert result["deleted"] is True

    async def test_delete_repo_404_when_not_found(self) -> None:
        """删除不存在的仓库应抛 404."""
        from fastapi import HTTPException

        mock_pool = _make_mock_pool(fetch_row=None)

        with patch("src.api.repo_routes.get_request_user_id", return_value="test_docbot_user_1"), \
             patch("src.api.repo_routes.get_request_agent_id", return_value="agentinsight-docbot"), \
             patch("src.api.repo_routes.get_pool", AsyncMock(return_value=mock_pool)), \
             pytest.raises(HTTPException) as exc_info:
            await delete_repo("nonexistent")

        assert exc_info.value.status_code == 404


@pytest.mark.api
class TestRepoConnectionTest:
    """POST /v1/repos/{repo_id}/test 测试连接."""

    async def test_test_connection_success(self) -> None:
        """连接成功应返回 success=True."""
        existing = _make_repo_row(repo_id="r1")
        mock_pool = _make_mock_pool(fetch_row=existing)

        with patch("src.api.repo_routes.get_request_user_id", return_value="test_docbot_user_1"), \
             patch("src.api.repo_routes.get_request_agent_id", return_value="agentinsight-docbot"), \
             patch("src.api.repo_routes.get_pool", AsyncMock(return_value=mock_pool)), \
             patch("src.api.repo_routes.get_settings") as mock_get_settings, \
             patch("src.api.repo_routes.decrypt_credential", return_value=None), \
             patch("src.api.repo_routes.get_git_mcp_adapter") as mock_adapter:
            mock_get_settings.return_value.git_credential_key = "test" * 32
            mock_adapter.return_value.test_connection = AsyncMock(return_value={"success": True, "error": None})
            result = await _rr.test_repo_connection("r1")

        assert result["success"] is True
        assert "成功" in result["message"]

    async def test_test_connection_failure(self) -> None:
        """连接失败应返回 success=False."""
        existing = _make_repo_row(repo_id="r1")
        mock_pool = _make_mock_pool(fetch_row=existing)

        with patch("src.api.repo_routes.get_request_user_id", return_value="test_docbot_user_1"), \
             patch("src.api.repo_routes.get_request_agent_id", return_value="agentinsight-docbot"), \
             patch("src.api.repo_routes.get_pool", AsyncMock(return_value=mock_pool)), \
             patch("src.api.repo_routes.get_settings") as mock_get_settings, \
             patch("src.api.repo_routes.decrypt_credential", return_value=None), \
             patch("src.api.repo_routes.get_git_mcp_adapter") as mock_adapter:
            mock_get_settings.return_value.git_credential_key = "test" * 32
            mock_adapter.return_value.test_connection = AsyncMock(return_value={"success": False, "error": "连接失败"})
            result = await _rr.test_repo_connection("r1")

        assert result["success"] is False

    async def test_test_connection_404_when_not_found(self) -> None:
        """仓库不存在应抛 404."""
        from fastapi import HTTPException

        mock_pool = _make_mock_pool(fetch_row=None)

        with patch("src.api.repo_routes.get_request_user_id", return_value="test_docbot_user_1"), \
             patch("src.api.repo_routes.get_request_agent_id", return_value="agentinsight-docbot"), \
             patch("src.api.repo_routes.get_pool", AsyncMock(return_value=mock_pool)), \
             pytest.raises(HTTPException) as exc_info:
            await _rr.test_repo_connection("nonexistent")

        assert exc_info.value.status_code == 404


@pytest.mark.api
class TestRepoSync:
    """POST /v1/repos/{repo_id}/sync 触发同步 + GET sync-status."""

    async def test_sync_repo_returns_202_with_syncing_status(self) -> None:
        """触发同步应立即返回 202 (syncing)."""
        existing = _make_repo_row(repo_id="r1")
        mock_pool = _make_mock_pool(fetch_row=existing)

        with patch("src.api.repo_routes.get_request_user_id", return_value="test_docbot_user_1"), \
             patch("src.api.repo_routes.get_request_agent_id", return_value="agentinsight-docbot"), \
             patch("src.api.repo_routes.get_pool", AsyncMock(return_value=mock_pool)), \
             patch("src.api.repo_routes.get_settings") as mock_get_settings, \
             patch("src.api.repo_routes.decrypt_credential", return_value=None), \
             patch("src.api.repo_routes._create_background_task", side_effect=lambda coro: coro.close()) as mock_create_task:
            mock_get_settings.return_value.git_credential_key = "test" * 32
            result = await sync_repo("r1")

        assert result["status"] == "syncing"
        # 后台任务应被创建 (但不实际执行)
        assert mock_create_task.called

    async def test_sync_repo_404_when_not_found(self) -> None:
        """仓库不存在应抛 404."""
        from fastapi import HTTPException

        mock_pool = _make_mock_pool(fetch_row=None)

        with patch("src.api.repo_routes.get_request_user_id", return_value="test_docbot_user_1"), \
             patch("src.api.repo_routes.get_request_agent_id", return_value="agentinsight-docbot"), \
             patch("src.api.repo_routes.get_pool", AsyncMock(return_value=mock_pool)), \
             pytest.raises(HTTPException) as exc_info:
            await sync_repo("nonexistent")

        assert exc_info.value.status_code == 404

    async def test_get_sync_status_returns_status(self) -> None:
        """查询同步状态应返回 last_sync_status."""
        existing = _make_repo_row(
            repo_id="r1",
            last_synced_at=datetime(2026, 1, 1, 12, 0, 0),
            last_sync_status="success",
            last_sync_error=None,
        )
        mock_pool = _make_mock_pool(fetch_row=existing)

        with patch("src.api.repo_routes.get_request_user_id", return_value="test_docbot_user_1"), \
             patch("src.api.repo_routes.get_request_agent_id", return_value="agentinsight-docbot"), \
             patch("src.api.repo_routes.get_pool", AsyncMock(return_value=mock_pool)):
            result = await get_sync_status("r1")

        assert result["repo_id"] == "r1"
        assert result["last_sync_status"] == "success"
        assert result["last_synced_at"] is not None
        assert "2026-01-01T12:00:00" in result["last_synced_at"]

    async def test_get_sync_status_404_when_not_found(self) -> None:
        """仓库不存在应抛 404."""
        from fastapi import HTTPException

        mock_pool = _make_mock_pool(fetch_row=None)

        with patch("src.api.repo_routes.get_request_user_id", return_value="test_docbot_user_1"), \
             patch("src.api.repo_routes.get_request_agent_id", return_value="agentinsight-docbot"), \
             patch("src.api.repo_routes.get_pool", AsyncMock(return_value=mock_pool)), \
             pytest.raises(HTTPException) as exc_info:
            await get_sync_status("nonexistent")

        assert exc_info.value.status_code == 404

    async def test_get_sync_status_never_state(self) -> None:
        """从未同步的仓库应返回 last_sync_status=never."""
        existing = _make_repo_row(
            repo_id="r1",
            last_synced_at=None,
            last_sync_status="never",
            last_sync_error=None,
        )
        mock_pool = _make_mock_pool(fetch_row=existing)

        with patch("src.api.repo_routes.get_request_user_id", return_value="test_docbot_user_1"), \
             patch("src.api.repo_routes.get_request_agent_id", return_value="agentinsight-docbot"), \
             patch("src.api.repo_routes.get_pool", AsyncMock(return_value=mock_pool)):
            result = await get_sync_status("r1")

        assert result["last_sync_status"] == "never"
        assert result["last_synced_at"] is None


@pytest.mark.api
class TestRepoDataIsolation:
    """数据隔离: 所有查询带 agent_id + user_id 复合过滤."""

    async def test_list_repos_filters_by_agent_and_user(self) -> None:
        """list_repos SQL WHERE 含 agent_id + user_id."""
        mock_pool = _make_mock_pool(fetch_rows=[])

        with patch("src.api.repo_routes.get_request_user_id", return_value="test_docbot_user_1"), \
             patch("src.api.repo_routes.get_request_agent_id", return_value="agentinsight-docbot"), \
             patch("src.api.repo_routes.get_pool", AsyncMock(return_value=mock_pool)):
            await list_repos()

        # 验证 SQL WHERE 子句含 agent_id 和 user_id 过滤
        mock_conn = mock_pool.acquire.return_value.__aenter__.return_value
        fetch_call = mock_conn.fetch.call_args
        sql_arg = fetch_call.args[0] if fetch_call.args else fetch_call[0][0]
        assert "agent_id" in sql_arg
        assert "user_id" in sql_arg
        assert "WHERE" in sql_arg

    async def test_fetch_repo_row_uses_user_id_isolation(self) -> None:
        """_fetch_repo_row 内部 SQL 含 user_id 隔离."""
        from src.api.repo_routes import _fetch_repo_row

        mock_pool = _make_mock_pool(fetch_row=None)

        await _fetch_repo_row(mock_pool, "r1", "test_docbot_user_1", "agentinsight-docbot")

        mock_conn = mock_pool.acquire.return_value.__aenter__.return_value
        fetchrow_call = mock_conn.fetchrow.call_args
        sql_arg = fetchrow_call.args[0] if fetchrow_call.args else fetchrow_call[0][0]
        assert "user_id = $" in sql_arg
        assert "agent_id = $" in sql_arg

"""安全测试: API 响应不含敏感字段原文.

测试目标 (见 AGENTS.md 第 11 章安全硬约束):
- RepoResponse 模型不含 token/password/ssh_key 原文字段
- 仅含 has_token/has_username/has_password/has_ssh_key 标志位
"""
from __future__ import annotations

from pathlib import Path

import pytest


class TestRepoResponseNoSensitiveFields:
    """RepoResponse 模型不含敏感字段测试."""

    @pytest.fixture
    def repo_response_fields(self) -> set[str]:
        """从源码扫描 RepoResponse 模型字段."""
        source_path = Path(__file__).parent.parent.parent / "src" / "api" / "repo_routes.py"
        content = source_path.read_text(encoding="utf-8")
        # 简单解析 class RepoResponse 内的字段
        fields: set[str] = set()
        in_class = False
        for line in content.splitlines():
            if "class RepoResponse" in line:
                in_class = True
                continue
            if in_class:
                # 字段定义格式: <name>: <type> = ...
                if line.startswith("    ") and ":" in line and not line.startswith("    #"):
                    field = line.split(":")[0].strip()
                    if field and not field.startswith("_"):
                        fields.add(field)
                # 类结束 (新顶层定义或空行 + 新代码)
                elif in_class and not line.startswith(" ") and line.strip():
                    break
        return fields

    def test_repo_response_does_not_contain_token_field(self, repo_response_fields: set) -> None:
        """RepoResponse 不含 token 原文字段 (仅 has_token 标志位)."""
        assert "token" not in repo_response_fields, (
            f"RepoResponse 含 token 原文字段 (违反第 11 章硬约束): {repo_response_fields}"
        )
        assert "encrypted_token" not in repo_response_fields

    def test_repo_response_does_not_contain_password_field(self, repo_response_fields: set) -> None:
        """RepoResponse 不含 password 原文字段 (仅 has_password 标志位)."""
        assert "password" not in repo_response_fields
        assert "encrypted_password" not in repo_response_fields

    def test_repo_response_does_not_contain_ssh_key_field(self, repo_response_fields: set) -> None:
        """RepoResponse 不含 ssh_key 原文字段 (仅 has_ssh_key 标志位)."""
        assert "ssh_key" not in repo_response_fields
        assert "encrypted_ssh_key" not in repo_response_fields

    def test_repo_response_does_not_contain_username_field(self, repo_response_fields: set) -> None:
        """RepoResponse 不含 username 原文字段 (仅 has_username 标志位)."""
        assert "username" not in repo_response_fields
        assert "encrypted_username" not in repo_response_fields

    def test_repo_response_contains_has_token_flag(self, repo_response_fields: set) -> None:
        """RepoResponse 含 has_token 标志位."""
        assert "has_token" in repo_response_fields

    def test_repo_response_contains_has_username_flag(self, repo_response_fields: set) -> None:
        """RepoResponse 含 has_username 标志位."""
        assert "has_username" in repo_response_fields

    def test_repo_response_contains_has_password_flag(self, repo_response_fields: set) -> None:
        """RepoResponse 含 has_password 标志位."""
        assert "has_password" in repo_response_fields

    def test_repo_response_contains_has_ssh_key_flag(self, repo_response_fields: set) -> None:
        """RepoResponse 含 has_ssh_key 标志位."""
        assert "has_ssh_key" in repo_response_fields

    def test_repo_response_contains_basic_fields(self, repo_response_fields: set) -> None:
        """RepoResponse 含基本字段 (id/repo_name/platform/repo_url/auth_type)."""
        for field in ("id", "repo_name", "platform", "repo_url", "auth_type"):
            assert field in repo_response_fields, f"RepoResponse 缺基本字段 {field}"


class TestRepoResponseModel:
    """RepoResponse Pydantic 模型测试."""

    def test_repo_response_can_be_constructed_with_flags(self) -> None:
        """RepoResponse 可用 has_xxx 标志位构造 (不含敏感字段)."""
        try:
            from src.api.repo_routes import RepoResponse
        except ImportError as e:
            pytest.skip(f"repo_routes 模块导入失败: {e}")

        # 构造时不传敏感字段
        response = RepoResponse(
            id="repo-1",
            repo_name="test-repo",
            platform="github",
            repo_url="https://github.com/test/repo.git",
            default_branch="main",
            auth_type="token",
            has_token=True,
            has_username=False,
            has_password=False,
            has_ssh_key=False,
            clone_depth=1,
            enabled=True,
            last_synced_at=None,
            last_sync_status="never",
            last_sync_error=None,
            created_at="2026-01-01T00:00:00+00:00",
            updated_at="2026-01-01T00:00:00+00:00",
        )
        assert response.id == "repo-1"
        assert response.has_token is True
        assert response.has_password is False

    def test_repo_response_model_dump_excludes_sensitive(self) -> None:
        """RepoResponse.model_dump() 不含敏感字段原文."""
        try:
            from src.api.repo_routes import RepoResponse
        except ImportError as e:
            pytest.skip(f"repo_routes 模块导入失败: {e}")

        response = RepoResponse(
            id="repo-1",
            repo_name="test-repo",
            platform="github",
            repo_url="https://github.com/test/repo.git",
            default_branch="main",
            auth_type="token",
            has_token=True,
            has_username=False,
            has_password=False,
            has_ssh_key=False,
            clone_depth=1,
            enabled=True,
            last_synced_at=None,
            last_sync_status="never",
            last_sync_error=None,
            created_at="2026-01-01T00:00:00+00:00",
            updated_at="2026-01-01T00:00:00+00:00",
        )
        dumped = response.model_dump()
        # 验证不含敏感字段
        for sensitive_field in (
            "token",
            "password",
            "ssh_key",
            "username",
            "encrypted_token",
            "encrypted_password",
            "encrypted_ssh_key",
            "encrypted_username",
        ):
            assert sensitive_field not in dumped, (
                f"model_dump() 含敏感字段 {sensitive_field}"
            )
        # 验证含标志位
        assert "has_token" in dumped
        assert "has_password" in dumped

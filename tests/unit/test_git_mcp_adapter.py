"""单元测试: GitMCPAdapter URL 解析 + 平台支持.

测试目标:
- GitMCPAdapter 初始化不抛异常
- _repo_path 返回正确路径
- _build_auth_url 支持 none/token/password/ssh_key 四种认证方式
- _check_git_domain 域名白名单校验
- _check_repo_size 仓库大小限制
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.tools.git_mcp import GitMCPAdapter


class TestGitMCPAdapterInit:
    """GitMCPAdapter 初始化测试."""

    def test_init_with_mock_settings(self, mock_settings: MagicMock) -> None:
        """初始化不抛异常."""
        adapter = GitMCPAdapter(settings=mock_settings)
        assert adapter is not None
        assert adapter.settings is mock_settings

    def test_repo_path_format(self, mock_settings: MagicMock) -> None:
        """_repo_path 返回 {clone_root}/{user_id}/{repo_id}/."""
        adapter = GitMCPAdapter(settings=mock_settings)
        path = adapter._repo_path("user1", "repo1")
        # 路径应含 user_id 和 repo_id
        assert "user1" in str(path)
        assert "repo1" in str(path)
        # 应以 repo_clone_root 开头
        assert str(path).startswith(mock_settings.repo_clone_root)


class TestBuildAuthUrl:
    """_build_auth_url 认证 URL 构造测试."""

    def test_auth_none(self, mock_settings: MagicMock) -> None:
        """auth_type=none 时, URL 不变."""
        adapter = GitMCPAdapter(settings=mock_settings)
        repo_url = "https://github.com/test/repo.git"
        repo_config = {"auth_type": "none"}
        auth_url, ssh_key_path = adapter._build_auth_url(repo_url, repo_config)
        assert auth_url == repo_url
        assert ssh_key_path is None

    def test_auth_token(self, mock_settings: MagicMock) -> None:
        """auth_type=token 时, URL 嵌入 oauth2:{token}@."""
        adapter = GitMCPAdapter(settings=mock_settings)
        repo_url = "https://github.com/test/repo.git"
        repo_config = {"auth_type": "token", "token": "ghp_abc123"}
        auth_url, ssh_key_path = adapter._build_auth_url(repo_url, repo_config)
        assert "oauth2:ghp_abc123" in auth_url
        assert "github.com" in auth_url
        assert ssh_key_path is None

    def test_auth_password(self, mock_settings: MagicMock) -> None:
        """auth_type=password 时, URL 嵌入 {user}:{pass}@."""
        adapter = GitMCPAdapter(settings=mock_settings)
        repo_url = "https://gitlab.com/test/repo.git"
        repo_config = {
            "auth_type": "password",
            "username": "user1",
            "password": "pass1",
        }
        auth_url, _ = adapter._build_auth_url(repo_url, repo_config)
        assert "user1:pass1" in auth_url
        assert "gitlab.com" in auth_url

    def test_auth_ssh_key_url_unchanged(self, mock_settings: MagicMock) -> None:
        """auth_type=ssh_key 时, URL 保持原样 (SSH key 通过 GIT_SSH_COMMAND 注入)."""
        adapter = GitMCPAdapter(settings=mock_settings)
        repo_url = "git@github.com:test/repo.git"
        repo_config = {"auth_type": "ssh_key", "ssh_key": "-----BEGIN..."}
        auth_url, ssh_key_path = adapter._build_auth_url(repo_url, repo_config)
        assert auth_url == repo_url
        assert ssh_key_path is None

    def test_auth_token_no_token(self, mock_settings: MagicMock) -> None:
        """auth_type=token 但 token 为空时, URL 不变."""
        adapter = GitMCPAdapter(settings=mock_settings)
        repo_url = "https://github.com/test/repo.git"
        repo_config = {"auth_type": "token", "token": ""}
        auth_url, _ = adapter._build_auth_url(repo_url, repo_config)
        assert auth_url == repo_url

    def test_auth_password_no_credentials(self, mock_settings: MagicMock) -> None:
        """auth_type=password 但无 username/password 时, URL 不变."""
        adapter = GitMCPAdapter(settings=mock_settings)
        repo_url = "https://github.com/test/repo.git"
        repo_config = {"auth_type": "password", "username": "", "password": ""}
        auth_url, _ = adapter._build_auth_url(repo_url, repo_config)
        assert auth_url == repo_url

    def test_auth_non_http_url_unchanged(self, mock_settings: MagicMock) -> None:
        """非 HTTP(S) URL (如 git://) 时, 不嵌入凭据."""
        adapter = GitMCPAdapter(settings=mock_settings)
        repo_url = "git://github.com/test/repo.git"
        repo_config = {"auth_type": "token", "token": "abc"}
        auth_url, _ = adapter._build_auth_url(repo_url, repo_config)
        assert auth_url == repo_url


class TestCheckGitDomain:
    """_check_git_domain 域名白名单校验测试."""

    def test_no_whitelist_allows_all(self, mock_settings: MagicMock) -> None:
        """白名单为空时, 允许所有域名."""
        adapter = GitMCPAdapter(settings=mock_settings)
        # allowed_git_domains_list 默认空
        adapter._check_git_domain("https://any.example.com/repo.git")

    def test_whitelist_allowed_exact_match(self, mock_settings: MagicMock) -> None:
        """白名单精确匹配允许."""
        mock_settings.allowed_git_domains_list = ["github.com"]
        adapter = GitMCPAdapter(settings=mock_settings)
        adapter._check_git_domain("https://github.com/test/repo.git")

    def test_whitelist_allowed_subdomain(self, mock_settings: MagicMock) -> None:
        """白名单子域名允许 (host endswith .domain)."""
        mock_settings.allowed_git_domains_list = ["github.com"]
        adapter = GitMCPAdapter(settings=mock_settings)
        adapter._check_git_domain("https://sub.github.com/repo.git")

    def test_whitelist_blocked_raises(self, mock_settings: MagicMock) -> None:
        """白名单不匹配时抛 ValueError."""
        mock_settings.allowed_git_domains_list = ["github.com"]
        adapter = GitMCPAdapter(settings=mock_settings)
        with pytest.raises(ValueError, match="不在白名单"):
            adapter._check_git_domain("https://gitlab.com/test/repo.git")

    def test_whitelist_multiple_domains(self, mock_settings: MagicMock) -> None:
        """白名单支持多个域名."""
        mock_settings.allowed_git_domains_list = ["github.com", "gitlab.com"]
        adapter = GitMCPAdapter(settings=mock_settings)
        adapter._check_git_domain("https://github.com/test/repo.git")
        adapter._check_git_domain("https://gitlab.com/test/repo.git")


class TestCheckRepoSize:
    """_check_repo_size 仓库大小校验测试."""

    def test_small_repo_no_raise(
        self, mock_settings: MagicMock, tmp_path: Path
    ) -> None:
        """小仓库不抛异常."""
        mock_settings.max_repo_size_mb = 1024
        adapter = GitMCPAdapter(settings=mock_settings)
        # 在 tmp_path 下创建小文件
        (tmp_path / "file.txt").write_text("x" * 100)
        adapter._check_repo_size(tmp_path)  # 不抛异常

    def test_oversized_repo_raises(
        self, mock_settings: MagicMock, tmp_path: Path
    ) -> None:
        """超限仓库抛 ValueError."""
        mock_settings.max_repo_size_mb = 1  # 1 MB
        adapter = GitMCPAdapter(settings=mock_settings)
        # 创建超过 1MB 的文件
        (tmp_path / "large.txt").write_text("x" * (2 * 1024 * 1024))
        with pytest.raises(ValueError, match="仓库大小.*超出限制"):
            adapter._check_repo_size(tmp_path)

    def test_git_dir_excluded_from_size(
        self, mock_settings: MagicMock, tmp_path: Path
    ) -> None:
        """.git 目录不计入业务大小."""
        mock_settings.max_repo_size_mb = 1
        adapter = GitMCPAdapter(settings=mock_settings)
        # 创建 .git 目录 (历史对象, 应被跳过)
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        (git_dir / "large_obj").write_text("x" * (2 * 1024 * 1024))
        # 创建业务文件 (不超过限制)
        (tmp_path / "small.txt").write_text("x" * 100)
        # 不应抛异常
        adapter._check_repo_size(tmp_path)


class TestSupportedPlatforms:
    """GitMCPAdapter 支持的平台测试 (见 AGENTS.md 第 9 章)."""

    @pytest.mark.parametrize(
        "platform,repo_url",
        [
            ("github", "https://github.com/test/repo.git"),
            ("gitlab", "https://gitlab.com/test/repo.git"),
            ("gitee", "https://gitee.com/test/repo.git"),
            ("bitbucket", "https://bitbucket.org/test/repo.git"),
            ("coding", "https://e.coding.net/test/repo.git"),
            ("gitea", "https://gitea.example.com/test/repo.git"),
            ("custom", "https://custom.example.com/test/repo.git"),
        ],
    )
    def test_all_platforms_supported(
        self, mock_settings: MagicMock, platform: str, repo_url: str
    ) -> None:
        """7 种平台 URL 都能被 _build_auth_url 处理 (none 模式)."""
        adapter = GitMCPAdapter(settings=mock_settings)
        auth_url, _ = adapter._build_auth_url(repo_url, {"auth_type": "none"})
        assert auth_url == repo_url

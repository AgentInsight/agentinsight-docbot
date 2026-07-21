"""安全测试: 仓库 URL 白名单 (ALLOWED_GIT_DOMAINS).

测试目标 (见 AGENTS.md 第 11 章 Prompt Injection 硬约束):
- 仓库 URL 白名单校验 (防 LLM 注入内网渗透)
- GitMCPAdapter._check_git_domain 行为
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.tools.git_mcp import GitMCPAdapter


class TestAllowedGitDomains:
    """Git 域名白名单测试."""

    def test_no_whitelist_allows_all(self, mock_settings: MagicMock) -> None:
        """白名单为空时, 允许所有域名."""
        mock_settings.allowed_git_domains_list = []
        adapter = GitMCPAdapter(settings=mock_settings)
        adapter._check_git_domain("https://any.example.com/repo.git")
        adapter._check_git_domain("https://192.168.1.1/repo.git")  # 内网 IP

    def test_whitelist_exact_match_allowed(self, mock_settings: MagicMock) -> None:
        """白名单精确匹配允许."""
        mock_settings.allowed_git_domains_list = ["github.com"]
        adapter = GitMCPAdapter(settings=mock_settings)
        adapter._check_git_domain("https://github.com/test/repo.git")

    def test_whitelist_subdomain_allowed(self, mock_settings: MagicMock) -> None:
        """白名单子域名允许 (host endswith .domain)."""
        mock_settings.allowed_git_domains_list = ["github.com"]
        adapter = GitMCPAdapter(settings=mock_settings)
        adapter._check_git_domain("https://api.github.com/repo.git")
        adapter._check_git_domain("https://sub.api.github.com/repo.git")

    def test_whitelist_blocked_domain_raises(self, mock_settings: MagicMock) -> None:
        """白名单不匹配抛 ValueError (防内网渗透)."""
        mock_settings.allowed_git_domains_list = ["github.com"]
        adapter = GitMCPAdapter(settings=mock_settings)
        with pytest.raises(ValueError, match="不在白名单"):
            adapter._check_git_domain("https://gitlab.com/test/repo.git")

    def test_whitelist_blocks_internal_ips(self, mock_settings: MagicMock) -> None:
        """白名单模式阻止内网 IP 访问."""
        mock_settings.allowed_git_domains_list = ["github.com"]
        adapter = GitMCPAdapter(settings=mock_settings)
        with pytest.raises(ValueError, match="不在白名单"):
            adapter._check_git_domain("https://192.168.1.1/repo.git")

    def test_whitelist_blocks_localhost(self, mock_settings: MagicMock) -> None:
        """白名单模式阻止 localhost 访问."""
        mock_settings.allowed_git_domains_list = ["github.com"]
        adapter = GitMCPAdapter(settings=mock_settings)
        with pytest.raises(ValueError, match="不在白名单"):
            adapter._check_git_domain("https://localhost/repo.git")
        with pytest.raises(ValueError, match="不在白名单"):
            adapter._check_git_domain("https://127.0.0.1/repo.git")

    def test_whitelist_multiple_domains(self, mock_settings: MagicMock) -> None:
        """白名单支持多个域名."""
        mock_settings.allowed_git_domains_list = ["github.com", "gitlab.com", "gitee.com"]
        adapter = GitMCPAdapter(settings=mock_settings)
        adapter._check_git_domain("https://github.com/test/repo.git")
        adapter._check_git_domain("https://gitlab.com/test/repo.git")
        adapter._check_git_domain("https://gitee.com/test/repo.git")

    def test_whitelist_case_insensitive(self, mock_settings: MagicMock) -> None:
        """白名单匹配不区分大小写 (host 与 allowed 列表均转小写后比较)."""
        mock_settings.allowed_git_domains_list = ["GitHub.com"]
        adapter = GitMCPAdapter(settings=mock_settings)
        # host 大小写混合, allowed 列表也大小写混合, 应允许
        adapter._check_git_domain("https://GITHUB.COM/test/repo.git")
        adapter._check_git_domain("https://github.com/test/repo.git")
        adapter._check_git_domain("https://API.GitHub.com/test/repo.git")

    def test_invalid_url_no_host_no_raise(self, mock_settings: MagicMock) -> None:
        """URL 不含 host (如 file:///) 时, 不抛异常 (无 host 无法校验)."""
        mock_settings.allowed_git_domains_list = ["github.com"]
        adapter = GitMCPAdapter(settings=mock_settings)
        # file:// 路径, parts.hostname 返回 None
        adapter._check_git_domain("file:///local/path")


class TestAllowedGitDomainsSettings:
    """Settings.allowed_git_domains_list 属性测试."""

    def test_allowed_git_domains_list_default_empty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """默认 allowed_git_domains_list 为空列表 (允许全部)."""
        from src.config.settings import Settings

        monkeypatch.setenv("ENV", "dev")
        monkeypatch.delenv("ALLOWED_GIT_DOMAINS", raising=False)
        s = Settings(_env_file=None)
        assert s.allowed_git_domains_list == []

    def test_allowed_git_domains_list_single(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """单域名配置."""
        from src.config.settings import Settings

        monkeypatch.setenv("ENV", "dev")
        monkeypatch.setenv("ALLOWED_GIT_DOMAINS", "github.com")
        s = Settings(_env_file=None)
        assert s.allowed_git_domains_list == ["github.com"]

    def test_allowed_git_domains_list_multiple(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """多域名配置 (逗号分隔)."""
        from src.config.settings import Settings

        monkeypatch.setenv("ENV", "dev")
        monkeypatch.setenv("ALLOWED_GIT_DOMAINS", "github.com,gitlab.com,gitee.com")
        s = Settings(_env_file=None)
        assert s.allowed_git_domains_list == ["github.com", "gitlab.com", "gitee.com"]

    def test_allowed_git_domains_list_strips_whitespace(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """配置含空格时自动 strip."""
        from src.config.settings import Settings

        monkeypatch.setenv("ENV", "dev")
        monkeypatch.setenv("ALLOWED_GIT_DOMAINS", " github.com , gitlab.com , ")
        s = Settings(_env_file=None)
        assert s.allowed_git_domains_list == ["github.com", "gitlab.com"]

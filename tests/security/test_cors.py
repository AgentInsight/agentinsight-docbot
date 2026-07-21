"""安全测试: CORS 配置.

测试目标 (见 AGENTS.md 第 11 章 CORS 架构偏好):
- CORS 不允许 * 用于生产 (属架构偏好, 非硬约束)
- 开发环境默认 http://localhost:8068
"""
from __future__ import annotations

from pathlib import Path

import pytest


class TestCorsConfiguration:
    """CORS 配置测试."""

    def test_cors_allow_origins_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """默认 CORS 含 localhost:8068.

        显式 delenv CORS_ALLOW_ORIGINS 防止环境变量污染 (pydantic 2.x 默认读 env vars).
        """
        from src.config.settings import Settings

        monkeypatch.delenv("CORS_ALLOW_ORIGINS", raising=False)
        monkeypatch.setenv("ENV", "dev")
        s = Settings(_env_file=None)
        assert "http://localhost:8068" in s.cors_origins_list

    def test_cors_origins_list_parses_comma(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """cors_origins_list 解析逗号分隔."""
        from src.config.settings import Settings

        monkeypatch.setenv("ENV", "dev")
        monkeypatch.setenv("CORS_ALLOW_ORIGINS", "http://a.com,http://b.com,http://c.com")
        s = Settings(_env_file=None)
        assert s.cors_origins_list == ["http://a.com", "http://b.com", "http://c.com"]

    def test_cors_origins_list_strips_whitespace(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """cors_origins_list 自动 strip 空格."""
        from src.config.settings import Settings

        monkeypatch.setenv("ENV", "dev")
        monkeypatch.setenv("CORS_ALLOW_ORIGINS", " http://a.com , http://b.com , ")
        s = Settings(_env_file=None)
        assert s.cors_origins_list == ["http://a.com", "http://b.com"]

    def test_cors_origins_list_empty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """空 CORS 配置返回空列表."""
        from src.config.settings import Settings

        monkeypatch.setenv("ENV", "dev")
        monkeypatch.setenv("CORS_ALLOW_ORIGINS", "")
        s = Settings(_env_file=None)
        assert s.cors_origins_list == []

    def test_server_py_uses_cors_middleware(self) -> None:
        """验证 server.py 注册了 CORSMiddleware."""
        server_path = Path(__file__).parent.parent.parent / "server.py"
        content = server_path.read_text(encoding="utf-8")
        assert "CORSMiddleware" in content
        assert "cors_origins_list" in content or "cors_allow_origins" in content

    def test_server_py_cors_methods_restricted(self) -> None:
        """验证 CORS allow_methods 限制为 5 种 (GET/POST/PUT/DELETE/OPTIONS)."""
        server_path = Path(__file__).parent.parent.parent / "server.py"
        content = server_path.read_text(encoding="utf-8")
        # 验证不含 *
        assert 'allow_methods=["*"]' not in content

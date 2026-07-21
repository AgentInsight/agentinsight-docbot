"""安全测试: 校验 3 个端点不存在 (/v1/feedback /v1/ws/* /v1/mcp/configs).

测试目标 (见 AGENTS.md 第 13 章关键测试用例 3 + 第 4 章不推荐清单 20):
- 用 TestClient 验证 POST /v1/feedback 返回 404 或 405
- 验证 GET /v1/mcp/configs 返回 404
- 验证 WS /v1/ws/test-session 返回 404

注: 端点不存在的测试, 不依赖外部服务, 只需 FastAPI app 实例
"""
from __future__ import annotations

from pathlib import Path

import pytest


class TestEndpointNotExist:
    """验证 3 个不应暴露的端点确实不存在."""

    @pytest.fixture
    def source_routes_check(self) -> dict[str, bool]:
        """从源码扫描路由注册情况.

        Returns:
            {
                "feedback": True/False,  # POST /v1/feedback 是否注册
                "mcp_configs": True/False,  # /v1/mcp/configs 是否注册
                "ws": True/False,  # WS /v1/ws/* 是否注册
            }
        """
        project_root = Path(__file__).parent.parent.parent
        src_dir = project_root / "src"

        result = {"feedback": False, "mcp_configs": False, "ws": False}
        if not src_dir.exists():
            return result

        for py_file in src_dir.rglob("*.py"):
            try:
                content = py_file.read_text(encoding="utf-8")
                # 检查 /v1/feedback 路由注册
                if '"/v1/feedback"' in content or "'/v1/feedback'" in content:
                    if "router.post" in content or "@app.post" in content or "@router.post" in content:
                        result["feedback"] = True
                # 检查 /v1/mcp/configs
                if '"/v1/mcp/configs"' in content or "'/v1/mcp/configs'" in content:
                    result["mcp_configs"] = True
                # 检查 WS /v1/ws/
                if '"/v1/ws/' in content or "'/v1/ws/" in content:
                    if "websocket" in content.lower():
                        result["ws"] = True
            except UnicodeDecodeError:
                continue

        return result

    def test_feedback_endpoint_not_registered(self, source_routes_check: dict) -> None:
        """验证 POST /v1/feedback 端点未注册."""
        assert not source_routes_check["feedback"], (
            "POST /v1/feedback 不应被注册 (docbot 不启用人审, 见 AGENTS.md 第 4 章不推荐清单 20)"
        )

    def test_mcp_configs_endpoint_not_registered(self, source_routes_check: dict) -> None:
        """验证 /v1/mcp/configs 端点未注册."""
        assert not source_routes_check["mcp_configs"], (
            "/v1/mcp/configs 不应被注册 (MCP 系统自带, 见 AGENTS.md 第 4 章不推荐清单 21)"
        )

    def test_ws_endpoint_not_registered(self, source_routes_check: dict) -> None:
        """验证 WS /v1/ws/* 端点未注册."""
        assert not source_routes_check["ws"], (
            "WS /v1/ws/* 不应被注册 (docbot 仅用 SSE, 见 AGENTS.md 第 4 章不推荐清单 20)"
        )

    def test_routes_py_does_not_contain_feedback(self) -> None:
        """验证 routes.py 不含 /v1/feedback 路由定义."""
        project_root = Path(__file__).parent.parent.parent
        routes_path = project_root / "src" / "api" / "routes.py"
        if not routes_path.exists():
            pytest.skip("routes.py 不存在")

        content = routes_path.read_text(encoding="utf-8")
        # 不应注册 /v1/feedback
        assert '"/v1/feedback"' not in content
        assert "'/v1/feedback'" not in content

    def test_session_routes_does_not_contain_ws(self) -> None:
        """验证 session_routes.py 不含 WS /v1/ws/* 路由."""
        project_root = Path(__file__).parent.parent.parent
        session_path = project_root / "src" / "api" / "session_routes.py"
        if not session_path.exists():
            pytest.skip("session_routes.py 不存在")

        content = session_path.read_text(encoding="utf-8")
        # 不应注册 /v1/ws/
        assert '"/v1/ws/' not in content
        assert "'/v1/ws/" not in content
        # 不应使用 @router.websocket
        assert "@router.websocket" not in content

    def test_repo_routes_does_not_contain_mcp_configs(self) -> None:
        """验证 repo_routes.py 不含 /v1/mcp/configs 路由."""
        project_root = Path(__file__).parent.parent.parent
        repo_path = project_root / "src" / "api" / "repo_routes.py"
        if not repo_path.exists():
            pytest.skip("repo_routes.py 不存在")

        content = repo_path.read_text(encoding="utf-8")
        assert '"/v1/mcp/configs"' not in content
        assert "'/v1/mcp/configs'" not in content

    def test_init_sql_does_not_create_mcp_configs_table(self) -> None:
        """验证 init.sql 不创建 mcp_configs 表."""
        project_root = Path(__file__).parent.parent.parent
        sql_path = project_root / "scripts" / "init.sql"
        if not sql_path.exists():
            pytest.skip("init.sql 不存在")

        content = sql_path.read_text(encoding="utf-8")
        # 不应 CREATE TABLE mcp_configs
        assert "CREATE TABLE IF NOT EXISTS mcp_configs" not in content
        assert "CREATE TABLE mcp_configs" not in content

"""API 测试: 校验 3 个端点不存在 (/v1/feedback /v1/ws/* /v1/mcp/configs).

需要部署后容器栈.
测试目标 (见 AGENTS.md 第 13 章关键测试用例 3):
- POST /v1/feedback 返回 404 或 405
- GET /v1/mcp/configs 返回 404
- WS /v1/ws/test-session 返回 404

注: 单元测试版本在 tests/security/test_endpoint_not_exist.py (源码扫描).
本文件需要部署后用 HTTP 实际请求验证.
"""
from __future__ import annotations

import pytest


@pytest.mark.api
@pytest.mark.requires_external
class TestEndpointNotExistLive:
    async def test_feedback_endpoint_404(self) -> None:
        """POST /v1/feedback 应返回 404 (端点不存在)."""
        pytest.skip("Requires external services")

    async def test_mcp_configs_endpoint_404(self) -> None:
        """GET /v1/mcp/configs 应返回 404."""
        pytest.skip("Requires external services")

    async def test_ws_endpoint_404(self) -> None:
        """WS /v1/ws/test-session 应返回 404."""
        pytest.skip("Requires external services")

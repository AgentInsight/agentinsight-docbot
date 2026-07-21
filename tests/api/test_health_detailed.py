"""API 测试: /health 端点详细字段验证.

验证:
- /health 返回 200 + status=ok
- 响应含 service=agentinsight-docbot
- 响应含 version 字段 (非空字符串)
- 响应 Content-Type 为 application/json

需要部署后容器栈 (agent-docbot 容器).
测试目标地址从环境变量 AGENT_URL 注入 (默认 http://127.0.0.1:8068).
"""
from __future__ import annotations

import os

import pytest

_AGENT_URL = os.getenv("AGENT_URL", "http://127.0.0.1:8068")


def _get_async_client():
    """延迟 import httpx, 测试环境可能未安装."""
    try:
        import httpx
    except ImportError as e:
        pytest.skip(f"httpx 未安装: {e}")
    return httpx


@pytest.mark.api
@pytest.mark.requires_external
class TestHealthDetailed:
    """/health 端点详细字段测试."""

    async def test_health_returns_200_ok(self) -> None:
        """测试 /health 返回 200 + status=ok."""
        httpx = _get_async_client()
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(f"{_AGENT_URL}/health")
            except Exception as e:  # noqa: BLE001
                pytest.skip(f"无法连接到 {_AGENT_URL}/health: {e}")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "ok"

    async def test_health_service_field_is_docbot(self) -> None:
        """测试 /health 响应含 service=agentinsight-docbot."""
        httpx = _get_async_client()
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(f"{_AGENT_URL}/health")
            except Exception as e:  # noqa: BLE001
                pytest.skip(f"无法连接到 {_AGENT_URL}/health: {e}")
        assert response.status_code == 200
        data = response.json()
        assert "service" in data, "/health 响应缺 service 字段"
        assert data["service"] == "agentinsight-docbot", (
            f"service 字段值异常: {data['service']} (应为 agentinsight-docbot)"
        )

    async def test_health_version_field_present(self) -> None:
        """测试 /health 响应含 version 字段 (非空字符串)."""
        httpx = _get_async_client()
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(f"{_AGENT_URL}/health")
            except Exception as e:  # noqa: BLE001
                pytest.skip(f"无法连接到 {_AGENT_URL}/health: {e}")
        assert response.status_code == 200
        data = response.json()
        assert "version" in data, "/health 响应缺 version 字段"
        version = data["version"]
        assert isinstance(version, str), f"version 字段类型异常: {type(version)} (应为 str)"
        assert version.strip(), "version 字段为空字符串"

    async def test_health_content_type_is_json(self) -> None:
        """测试 /health 响应 Content-Type 含 application/json."""
        httpx = _get_async_client()
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(f"{_AGENT_URL}/health")
            except Exception as e:  # noqa: BLE001
                pytest.skip(f"无法连接到 {_AGENT_URL}/health: {e}")
        assert response.status_code == 200
        content_type = response.headers.get("content-type", "")
        assert "application/json" in content_type, (
            f"Content-Type 异常: {content_type} (应含 application/json)"
        )

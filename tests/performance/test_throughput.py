"""性能测试: 吞吐量测试.

测量各端点的 RPS (Requests Per Second), 与基线对比.
需要部署后容器栈.
"""
from __future__ import annotations

from typing import Any

import pytest


@pytest.mark.performance
@pytest.mark.requires_external
class TestEndpointThroughput:
    """端点吞吐量测试."""

    async def test_health_endpoint_rps(self) -> None:
        """测试 /health 端点吞吐量 >= 1000 RPS."""
        pytest.skip("Requires external services")

    async def test_repos_create_rps(self) -> None:
        """测试 POST /v1/repos 吞吐量 >= 50 RPS."""
        pytest.skip("Requires external services")

    async def test_repos_list_rps(self) -> None:
        """测试 GET /v1/repos 吞吐量 >= 100 RPS."""
        pytest.skip("Requires external services")

    async def test_chat_completions_rps(self) -> None:
        """测试 POST /v1/chat/completions 吞吐量 >= 0.5 RPS."""
        pytest.skip("Requires external services")

    async def test_report_download_rps(self) -> None:
        """测试 GET /v1/reports/{id}/download 吞吐量 >= 10 RPS."""
        pytest.skip("Requires external services")


async def _measure_rps(
    url: str,
    payload: dict[str, Any],
    duration_sec: float = 10.0,
) -> float:
    """测量端点吞吐量 (辅助函数, 待实现).

    Returns:
        RPS (requests per second)
    """
    raise NotImplementedError("待实现 (依赖外部服务)")

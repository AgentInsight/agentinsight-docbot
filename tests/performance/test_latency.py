"""性能测试: 延迟基线测试.

测量各端点的 P50/P95/P99 延迟, 与基线对比.
需要部署后容器栈.
"""
from __future__ import annotations

from typing import Any

import pytest


@pytest.mark.performance
@pytest.mark.requires_external
class TestEndpointLatency:
    """端点延迟测试."""

    async def test_health_endpoint_p95(self) -> None:
        """测试 /health 端点 P95 延迟 < 50ms."""
        pytest.skip("Requires external services")

    async def test_repos_create_p95(self) -> None:
        """测试 POST /v1/repos P95 延迟 < 200ms."""
        pytest.skip("Requires external services")

    async def test_repos_list_p95(self) -> None:
        """测试 GET /v1/repos P95 延迟 < 150ms."""
        pytest.skip("Requires external services")

    async def test_chat_completions_p95(self) -> None:
        """测试 POST /v1/chat/completions P95 延迟 < 30s."""
        pytest.skip("Requires external services")

    async def test_report_download_p95(self) -> None:
        """测试 GET /v1/reports/{report_id}/download P95 延迟 < 1s."""
        pytest.skip("Requires external services")


def _percentile(values: list[float], p: float) -> float:
    """计算百分位数 (辅助函数)."""
    if not values:
        return 0.0
    sorted_values = sorted(values)
    k = (len(sorted_values) - 1) * p
    f = int(k)
    c = min(f + 1, len(sorted_values) - 1)
    return sorted_values[f] + (sorted_values[c] - sorted_values[f]) * (k - f)


async def _measure_latency_ms(
    url: str,
    payload: dict[str, Any],
    n: int = 50,
) -> dict[str, float]:
    """测量端点延迟 (辅助函数, 待实现).

    Returns:
        dict 含 p50, p95, p99, avg, min, max
    """
    raise NotImplementedError("待实现 (依赖外部服务)")

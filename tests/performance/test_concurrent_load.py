"""性能测试: 并发负载测试.

模拟 N 个并发用户同时请求 /v1/chat/completions, 测量:
- 成功率
- 平均/P95 延迟
- 错误率
- 资源使用 (CPU/Memory)

需要部署后容器栈 + 外部 LLM.
"""
from __future__ import annotations

from typing import Any

import pytest


@pytest.mark.performance
@pytest.mark.requires_external
class TestConcurrentLoad:
    """并发负载测试."""

    async def test_concurrent_chat_completions(
        self,
        perf_target_url: str,
        perf_concurrent_users: int,
    ) -> None:
        """测试 N 个并发用户的 chat/completions 请求."""
        pytest.skip("Requires external services")

    async def test_concurrent_repo_creation(
        self,
        perf_target_url: str,
        perf_concurrent_users: int,
    ) -> None:
        """测试 N 个并发用户的 POST /v1/repos 请求."""
        pytest.skip("Requires external services")

    async def test_max_concurrent_reports_respected(
        self,
        perf_target_url: str,
    ) -> None:
        """测试 max_concurrent_reports 上限生效 (3 个并发报告)."""
        pytest.skip("Requires external services")

    async def test_semaphore_limits_llm_concurrency(
        self,
        perf_target_url: str,
    ) -> None:
        """测试 max_llm_concurrency 信号量生效."""
        pytest.skip("Requires external services")


async def _measure_concurrent_requests(
    url: str,
    payload: dict[str, Any],
    concurrent: int,
) -> dict[str, Any]:
    """测量并发请求性能 (辅助函数, 待实现).

    Returns:
        dict 含 success_rate, avg_latency_ms, p95_latency_ms, error_rate
    """
    raise NotImplementedError("待实现 (依赖外部服务)")

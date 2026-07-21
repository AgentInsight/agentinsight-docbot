"""性能测试专用 fixture.

提供:
- perf_settings: 性能测试 Settings (放宽 max_concurrent_reports)
- perf_target_url: 性能测试目标 URL (默认 http://localhost:8068)
- perf_concurrent_users: 并发用户数 (默认 10)
- perf_ramp_up: 升压时间秒 (默认 5)
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest


@pytest.fixture
def perf_settings() -> MagicMock:
    """性能测试 Settings (放宽并发限制)."""
    settings = MagicMock()
    settings.agent_name = "agentinsight-docbot"
    settings.max_concurrent_reports = 5
    settings.max_llm_concurrency = 20
    settings.max_rag_concurrency = 30
    return settings


@pytest.fixture
def perf_target_url() -> str:
    """性能测试目标 URL."""
    return "http://localhost:8068"


@pytest.fixture
def perf_concurrent_users() -> int:
    """并发用户数."""
    return 10


@pytest.fixture
def perf_ramp_up() -> int:
    """升压时间 (秒)."""
    return 5


@pytest.fixture
def perf_baseline_latency_ms() -> dict[str, float]:
    """延迟基线 (ms).

    每个端点的预期 P95 延迟基线.
    """
    return {
        "GET /health": 50.0,
        "POST /v1/repos": 200.0,
        "GET /v1/repos": 150.0,
        "POST /v1/chat/completions": 30_000.0,  # 30 秒 (单次报告生成)
    }


@pytest.fixture
def perf_baseline_throughput_rps() -> dict[str, float]:
    """吞吐量基线 (RPS).

    每个端点的预期吞吐量基线.
    """
    return {
        "GET /health": 1000.0,
        "POST /v1/repos": 50.0,
        "GET /v1/repos": 100.0,
        "POST /v1/chat/completions": 0.5,  # 0.5 RPS (低吞吐任务)
    }


__all__ = [
    "perf_baseline_latency_ms",
    "perf_baseline_throughput_rps",
    "perf_concurrent_users",
    "perf_ramp_up",
    "perf_settings",
    "perf_target_url",
]

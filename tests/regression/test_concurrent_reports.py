"""回归测试: 多报告并发派发 (Semaphore=3).

需要部署后容器栈.
测试目标 (见 AGENTS.md 第 5 章并发控制):
- 单次请求最多并发派发 3 个 B 子图
- max_concurrent_reports=3 限流
"""
from __future__ import annotations

import pytest


@pytest.mark.regression
@pytest.mark.requires_external
class TestConcurrentReports:
    async def test_max_three_concurrent_reports(self) -> None:
        """测试 3 个 B 子图并发派发."""
        pytest.skip("Requires external services")

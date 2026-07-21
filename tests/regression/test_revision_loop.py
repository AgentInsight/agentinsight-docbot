"""回归测试: D-E 修订循环 (max_revisions_per_chapter=3).

需要部署后容器栈.
测试目标 (见 AGENTS.md 第 13 章关键测试用例 2):
- D-E 修订循环每章节最多 3 轮 (达上限强制通过)
- max_revisions_per_chapter 硬上限
"""
from __future__ import annotations

import pytest


@pytest.mark.regression
@pytest.mark.requires_external
class TestRevisionLoop:
    async def test_revision_loop_max_three(self) -> None:
        """测试 D-E 修订循环最多 3 轮."""
        pytest.skip("Requires external services")

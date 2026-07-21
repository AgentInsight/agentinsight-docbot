"""探索性测试: 边界场景 (空仓库 / 超大仓库 / 无效 report_type / 无效 language).

需要部署后容器栈.
"""
from __future__ import annotations

import pytest


@pytest.mark.exploratory
@pytest.mark.requires_external
class TestEdgeCases:
    async def test_empty_repo(self) -> None:
        """测试空仓库 (sync 失败, 文件数为 0)."""
        pytest.skip("Requires external services")

    async def test_oversized_repo_rejected(self) -> None:
        """测试超大仓库 (>1024MB) 被拒绝克隆."""
        pytest.skip("Requires external services")

    async def test_invalid_report_type_rejected(self) -> None:
        """测试无效 report_type 被校验拒绝."""
        pytest.skip("Requires external services")

    async def test_invalid_language_rejected(self) -> None:
        """测试无效 language (非 zh/en) 被校验拒绝."""
        pytest.skip("Requires external services")

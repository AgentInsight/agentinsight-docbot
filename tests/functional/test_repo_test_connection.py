"""功能测试: /v1/repos/{id}/test 测试连接.

需要部署后容器栈.
测试目标: POST /v1/repos/{repo_id}/test 调用 git ls-remote 探活.
"""
from __future__ import annotations

import pytest


@pytest.mark.functional
@pytest.mark.requires_external
class TestRepoTestConnection:
    """需要部署后容器栈."""

    async def test_test_connection_success(self) -> None:
        """测试连接成功 (公开仓库)."""
        pytest.skip("Requires external services")

    async def test_test_connection_failure(self) -> None:
        """测试连接失败 (无效 URL)."""
        pytest.skip("Requires external services")

    async def test_test_connection_with_token(self) -> None:
        """测试连接 (token 模式, 需要有效 PAT)."""
        pytest.skip("Requires external services")

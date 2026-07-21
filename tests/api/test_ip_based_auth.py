"""API 测试: IP-based user_id 解析.

需要部署后容器栈.
"""
from __future__ import annotations

import pytest


@pytest.mark.api
@pytest.mark.requires_external
class TestIpBasedAuth:
    async def test_ip_based_user_id_resolved(self) -> None:
        """测试无 JWT Token 时基于 IP 生成 user_id (self_host=True)."""
        pytest.skip("Requires external services")

"""API 测试: Bearer JWT Token 鉴权.

需要部署后容器栈.
测试目标 (见 AGENTS.md 第 8 章):
- 携带 Bearer JWT Token 时, 解析 user_id 注入请求上下文
- 不携带 Token 时 (self_host=True) 走 IP-based 解析
- self_host=False 时不携带 Token 返回 401
"""
from __future__ import annotations

import pytest


@pytest.mark.api
@pytest.mark.requires_external
class TestJwtAuth:
    async def test_valid_jwt_token_accepted(self) -> None:
        """测试携带有效 JWT Token 通过鉴权."""
        pytest.skip("Requires external services")

    async def test_invalid_jwt_token_falls_back_to_ip(self) -> None:
        """测试携带无效 JWT Token 走 IP-based 降级 (self_host=True)."""
        pytest.skip("Requires external services")

    async def test_missing_jwt_token_returns_401_in_cloud_mode(self) -> None:
        """测试 self_host=False 模式下缺少 JWT Token 返回 401."""
        pytest.skip("Requires external services")

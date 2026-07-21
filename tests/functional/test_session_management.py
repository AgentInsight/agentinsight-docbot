"""功能测试: /v1/sessions 会话管理 CRUD.

需要部署后容器栈.
测试目标: 会话列表 / 创建 / 删除 / 消息分页.
"""
from __future__ import annotations

import pytest


@pytest.mark.functional
@pytest.mark.requires_external
class TestSessionManagement:
    async def test_list_sessions(self) -> None:
        """测试列出当前用户所有会话."""
        pytest.skip("Requires external services")

    async def test_create_session(self) -> None:
        """测试创建新会话 (生成 session_id)."""
        pytest.skip("Requires external services")

    async def test_delete_session(self) -> None:
        """测试删除会话 (含级联清理: Checkpoint + Redis 缓存 + 业务元数据)."""
        pytest.skip("Requires external services")

    async def test_get_session_messages_pagination(self) -> None:
        """测试会话消息分页加载 (limit/offset)."""
        pytest.skip("Requires external services")

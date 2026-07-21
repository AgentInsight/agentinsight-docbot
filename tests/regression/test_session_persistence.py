"""回归测试: 会话持久化 + 级联删除.

需要部署后容器栈.
"""
from __future__ import annotations

import pytest


@pytest.mark.regression
@pytest.mark.requires_external
class TestSessionPersistence:
    async def test_session_persisted_in_postgres(self) -> None:
        """测试会话持久化到 Postgres Checkpointer."""
        pytest.skip("Requires external services")

    async def test_delete_session_cascades_cleanup(self) -> None:
        """测试删除会话级联清理 (Checkpoint + Redis 缓存 + 业务元数据 + 临时克隆目录)."""
        pytest.skip("Requires external services")

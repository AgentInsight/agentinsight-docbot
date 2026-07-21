"""功能测试: /v1/repos/{id}/sync 同步触发索引.

需要部署后容器栈 (PostgreSQL + Redis + Qdrant + Embeddings + agent-docbot).
测试目标: POST /v1/repos/{repo_id}/sync 触发克隆 + 索引到 Qdrant.
"""
from __future__ import annotations

import pytest


@pytest.mark.functional
@pytest.mark.requires_external
class TestRepoSync:
    async def test_sync_triggers_clone(self) -> None:
        """测试 sync 触发 git clone 到 temp/repos/{user_id}/{repo_id}/."""
        pytest.skip("Requires external services")

    async def test_sync_indexes_to_qdrant(self) -> None:
        """测试 sync 索引到 Qdrant (namespace={agent_id}:{user_id}:{repo_id})."""
        pytest.skip("Requires external services")

    async def test_sync_status_polling(self) -> None:
        """测试 sync-status 轮询 (syncing → success/failed)."""
        pytest.skip("Requires external services")

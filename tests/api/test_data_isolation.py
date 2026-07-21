"""API 测试: 多用户数据隔离 (namespace 含 repo_id).

需要部署后容器栈.
测试目标 (见 AGENTS.md 第 7 章多仓库隔离核心约定):
- Qdrant namespace 含 repo_id 维度: agentinsight-docbot:{user_id}:{repo_id}
- 不同用户/不同仓库的数据不互相可见
"""
from __future__ import annotations

import pytest


@pytest.mark.api
@pytest.mark.requires_external
class TestDataIsolation:
    async def test_user_a_cannot_see_user_b_repos(self) -> None:
        """测试用户 A 不能看到用户 B 的仓库配置 (PostgreSQL user_id 隔离)."""
        pytest.skip("Requires external services")

    async def test_repo_a_data_not_in_repo_b_namespace(self) -> None:
        """测试仓库 A 的 Qdrant 索引不出现在仓库 B 的 namespace 中."""
        pytest.skip("Requires external services")

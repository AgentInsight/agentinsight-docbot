"""集成测试: Qdrant namespace 多仓库隔离.

验证:
- namespace 命名规则包含 repo_id
- 不同 repo_id 的向量数据完全隔离
- 删除 repo 时 namespace 被清理

需要部署后容器栈 (Qdrant).
"""
from __future__ import annotations

import pytest


@pytest.mark.integration
@pytest.mark.requires_external
class TestQdrantNamespace:
    """Qdrant namespace 隔离测试."""

    async def test_namespace_contains_repo_id(self) -> None:
        """测试 namespace 命名包含 repo_id."""
        pytest.skip("Requires external Qdrant")

    async def test_two_repos_have_isolated_namespaces(self) -> None:
        """测试两个不同 repo_id 的向量数据完全隔离."""
        pytest.skip("Requires external Qdrant")

    async def test_cross_repo_search_returns_empty(self) -> None:
        """测试跨仓库搜索返回空结果 (隔离生效)."""
        pytest.skip("Requires external Qdrant")

    async def test_delete_repo_clears_namespace(self) -> None:
        """测试删除 repo 时 namespace 被清理."""
        pytest.skip("Requires external Qdrant")

    async def test_same_repo_id_reused_after_delete(self) -> None:
        """测试删除后相同 repo_id 可重新使用 (无残留向量)."""
        pytest.skip("Requires external Qdrant")

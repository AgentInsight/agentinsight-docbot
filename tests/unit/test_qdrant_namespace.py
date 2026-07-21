"""单元测试: Qdrant namespace 字符串构造 (P0 修复).

测试目标 (P0-1 架构修复):
- build_repo_namespace 返回 "{agent_id}:{user_id}:{repo_id}" 格式
- build_repo_namespace 不同 user_id / repo_id 组合返回不同 namespace
- build_repo_namespace 与 AIR 的 build_data_user_namespace 隔离 (不冲突)

注意: conftest.py 已将 qdrant_client mock 为 MagicMock (测试环境缺依赖时),
QdrantManager 构造时不会实际连接 Qdrant, 仅创建 MagicMock 客户端.
"""
from __future__ import annotations

import pytest

from src.config.settings import get_settings
from src.rag.qdrant_manager import QdrantManager


@pytest.fixture
def qdrant_manager() -> QdrantManager:
    """构造 QdrantManager 实例 (不连接 Qdrant, 仅测试 namespace 字符串构造)."""
    settings = get_settings()
    return QdrantManager(settings)


class TestBuildRepoNamespace:
    """build_repo_namespace namespace 字符串构造测试."""

    def test_namespace_format_contains_agent_user_repo(self, qdrant_manager: QdrantManager) -> None:
        """namespace 格式应为 "{agent_id}:{user_id}:{repo_id}"."""
        ns = qdrant_manager.build_repo_namespace("user123", "repo456")
        # agent_id 来自 settings.agent_name
        agent_id = qdrant_manager.settings.agent_name
        assert ns == f"{agent_id}:user123:repo456"

    def test_namespace_different_users_isolated(self, qdrant_manager: QdrantManager) -> None:
        """不同 user_id 的 namespace 应隔离."""
        ns1 = qdrant_manager.build_repo_namespace("user1", "repo1")
        ns2 = qdrant_manager.build_repo_namespace("user2", "repo1")
        assert ns1 != ns2
        assert "user1" in ns1
        assert "user2" in ns2

    def test_namespace_different_repos_isolated(self, qdrant_manager: QdrantManager) -> None:
        """不同 repo_id 的 namespace 应隔离."""
        ns1 = qdrant_manager.build_repo_namespace("user1", "repo1")
        ns2 = qdrant_manager.build_repo_namespace("user1", "repo2")
        assert ns1 != ns2
        assert "repo1" in ns1
        assert "repo2" in ns2

    def test_namespace_does_not_collide_with_air_data_namespace(
        self, qdrant_manager: QdrantManager,
    ) -> None:
        """docbot repo namespace 不应与 AIR 的 data namespace 冲突.

        AIR: {agent_id}-data:{user_id}
        docbot: {agent_id}:{user_id}:{repo_id}
        """
        air_ns = qdrant_manager.build_data_user_namespace("user1")
        docbot_ns = qdrant_manager.build_repo_namespace("user1", "repo1")
        assert air_ns != docbot_ns
        # AIR namespace 含 "-data:" 中缀
        assert "-data:" in air_ns
        # docbot namespace 不含 "-data:" 中缀
        assert "-data:" not in docbot_ns


class TestHasRepoDataInputValidation:
    """has_repo_data 输入校验测试 (不实际调用 Qdrant)."""

    @pytest.mark.asyncio
    async def test_has_repo_data_empty_user_returns_false(self, qdrant_manager: QdrantManager) -> None:
        """user_id 为空时直接返回 False, 不调 Qdrant."""
        result = await qdrant_manager.has_repo_data("", "repo1")
        assert result is False

    @pytest.mark.asyncio
    async def test_has_repo_data_empty_repo_returns_false(self, qdrant_manager: QdrantManager) -> None:
        """repo_id 为空时直接返回 False, 不调 Qdrant."""
        result = await qdrant_manager.has_repo_data("user1", "")
        assert result is False

    @pytest.mark.asyncio
    async def test_has_repo_data_none_user_returns_false(self, qdrant_manager: QdrantManager) -> None:
        """user_id 为 None 时直接返回 False."""
        result = await qdrant_manager.has_repo_data(None, "repo1")  # type: ignore[arg-type]
        assert result is False

    @pytest.mark.asyncio
    async def test_has_repo_data_none_repo_returns_false(self, qdrant_manager: QdrantManager) -> None:
        """repo_id 为 None 时直接返回 False."""
        result = await qdrant_manager.has_repo_data("user1", None)  # type: ignore[arg-type]
        assert result is False

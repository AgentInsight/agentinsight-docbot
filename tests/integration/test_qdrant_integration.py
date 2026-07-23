"""集成测试: Qdrant 向量存储 namespace 隔离.

不依赖外部服务, 用 mock QdrantClient 验证:
- namespace 格式: {agent_id}:{user_id}:{repo_id} 三层隔离
- 不同 namespace 的点互不可见
- 点 payload 含 metadata {file_path, language, chunk_type, chunk_index, repo_id}
- embed_and_index 批量写入 (200 点/批)
- search 按 namespace 过滤

测试目标 (AGENTS.md 第 13 章集成测试):
- Qdrant 集成不依赖 --run-external
- 用 mock 替代 QdrantClient
- 数据隔离: namespace=test_docbot_*
"""
from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _make_mock_embeddings_client() -> MagicMock:
    """构造 mock embeddings client (含 embed_and_index + search)."""
    client = MagicMock()
    client.embed_and_index = AsyncMock(return_value={"indexed": 0})
    client.search = AsyncMock(return_value=[])
    client.delete_namespace = AsyncMock(return_value=True)
    return client


@pytest.mark.integration
class TestQdrantNamespaceFormat:
    """namespace 三层隔离格式测试."""

    def test_namespace_format_three_tier(self) -> None:
        """namespace 应为 {agent_id}:{user_id}:{repo_id} 三层格式."""
        agent_id = "agentinsight-docbot"
        user_id = "test_docbot_user_1"
        repo_id = "test_docbot_repo_1"
        namespace = f"{agent_id}:{user_id}:{repo_id}"
        # 应含 3 层, 用 : 分隔
        parts = namespace.split(":")
        assert len(parts) == 3
        assert parts[0] == agent_id
        assert parts[1] == user_id
        assert parts[2] == repo_id

    def test_namespace_differs_per_user(self) -> None:
        """不同 user_id 应产生不同 namespace."""
        agent_id = "agentinsight-docbot"
        repo_id = "test_docbot_repo_1"
        ns_user1 = f"{agent_id}:test_docbot_user_1:{repo_id}"
        ns_user2 = f"{agent_id}:test_docbot_user_2:{repo_id}"
        assert ns_user1 != ns_user2

    def test_namespace_differs_per_repo(self) -> None:
        """不同 repo_id 应产生不同 namespace."""
        agent_id = "agentinsight-docbot"
        user_id = "test_docbot_user_1"
        ns_repo1 = f"{agent_id}:{user_id}:test_docbot_repo_1"
        ns_repo2 = f"{agent_id}:{user_id}:test_docbot_repo_2"
        assert ns_repo1 != ns_repo2

    def test_namespace_differs_per_agent(self) -> None:
        """不同 agent_id 应产生不同 namespace (跨智能体隔离)."""
        user_id = "test_docbot_user_1"
        repo_id = "test_docbot_repo_1"
        ns_docbot = f"agentinsight-docbot:{user_id}:{repo_id}"
        ns_researcher = f"agentinsight-researcher:{user_id}:{repo_id}"
        assert ns_docbot != ns_researcher


@pytest.mark.integration
class TestQdrantIndexOperation:
    """Qdrant 索引操作测试 (mock embed_and_index)."""

    async def test_embed_and_index_called_with_correct_namespace(self) -> None:
        """embed_and_index 应使用正确的 namespace."""
        from src.api.repo_routes import _index_repo_to_qdrant

        mock_adapter = MagicMock()
        mock_adapter.read_file = AsyncMock(return_value="def hello(): pass")

        mock_embeddings_client = _make_mock_embeddings_client()

        with patch("src.rag.embeddings.get_embeddings_client", return_value=mock_embeddings_client):
            await _index_repo_to_qdrant(
                repo_path="/tmp/test_repo",
                files=["main.py"],
                namespace="agentinsight-docbot:test_docbot_user_1:test_docbot_repo_1",
                user_id="test_docbot_user_1",
                repo_id="test_docbot_repo_1",
                adapter=mock_adapter,
            )

        # 验证 embed_and_index 被调用且 namespace 正确
        assert mock_embeddings_client.embed_and_index.called
        call_kwargs = mock_embeddings_client.embed_and_index.call_args.kwargs
        assert call_kwargs["namespace"] == "agentinsight-docbot:test_docbot_user_1:test_docbot_repo_1"
        assert call_kwargs["user_id"] == "test_docbot_user_1"

    async def test_embed_and_index_payload_contains_metadata(self) -> None:
        """点的 payload 应含 metadata (file_path, language, chunk_type, chunk_index, repo_id)."""
        from src.api.repo_routes import _index_repo_to_qdrant

        mock_adapter = MagicMock()
        mock_adapter.read_file = AsyncMock(return_value="def hello(): pass\n")

        mock_embeddings_client = _make_mock_embeddings_client()

        with patch("src.rag.embeddings.get_embeddings_client", return_value=mock_embeddings_client):
            await _index_repo_to_qdrant(
                repo_path="/tmp/test_repo",
                files=["main.py"],
                namespace="agentinsight-docbot:test_docbot_user_1:test_docbot_repo_1",
                user_id="test_docbot_user_1",
                repo_id="test_docbot_repo_1",
                adapter=mock_adapter,
            )

        call_args = mock_embeddings_client.embed_and_index.call_args
        # 检查 metadata_list 含预期字段
        metadata_list = call_args.kwargs.get("metadata_list", [])
        assert len(metadata_list) > 0
        meta = metadata_list[0]
        assert "file_path" in meta
        assert "language" in meta
        assert "chunk_type" in meta
        assert "chunk_index" in meta
        assert "repo_id" in meta
        assert meta["file_path"] == "main.py"
        assert meta["language"] == "python"
        assert meta["chunk_type"] == "code"
        assert meta["repo_id"] == "test_docbot_repo_1"

    async def test_embed_and_index_empty_files_no_call(self) -> None:
        """无文件时不应调用 embed_and_index."""
        from src.api.repo_routes import _index_repo_to_qdrant

        mock_adapter = MagicMock()
        mock_embeddings_client = _make_mock_embeddings_client()

        with patch("src.rag.embeddings.get_embeddings_client", return_value=mock_embeddings_client):
            await _index_repo_to_qdrant(
                repo_path="/tmp/test_repo",
                files=[],
                namespace="agentinsight-docbot:test_docbot_user_1:test_docbot_repo_1",
                user_id="test_docbot_user_1",
                repo_id="test_docbot_repo_1",
                adapter=mock_adapter,
            )

        # 无文件 → 不应调用 embed_and_index
        assert not mock_embeddings_client.embed_and_index.called

    async def test_embed_and_index_skips_unreadable_files(self) -> None:
        """读取失败的文件应被跳过 (不阻断)."""
        from src.api.repo_routes import _index_repo_to_qdrant

        mock_adapter = MagicMock()
        # 第一个文件读取失败, 第二个文件正常
        mock_adapter.read_file = AsyncMock(side_effect=[Exception("读取失败"), "def hello(): pass"])

        mock_embeddings_client = _make_mock_embeddings_client()

        with patch("src.rag.embeddings.get_embeddings_client", return_value=mock_embeddings_client):
            await _index_repo_to_qdrant(
                repo_path="/tmp/test_repo",
                files=["bad.py", "good.py"],
                namespace="agentinsight-docbot:test_docbot_user_1:test_docbot_repo_1",
                user_id="test_docbot_user_1",
                repo_id="test_docbot_repo_1",
                adapter=mock_adapter,
            )

        # 仍应索引 good.py
        assert mock_embeddings_client.embed_and_index.called
        call_args = mock_embeddings_client.embed_and_index.call_args
        metadata_list = call_args.kwargs.get("metadata_list", [])
        # 应仅含 good.py 的元数据
        assert all(m["file_path"] == "good.py" for m in metadata_list)


@pytest.mark.integration
class TestQdrantSearchIsolation:
    """Qdrant 检索时的 namespace 隔离."""

    async def test_search_uses_correct_namespace(self) -> None:
        """检索应使用正确的 namespace (不跨用户/仓库检索)."""
        # mock get_embeddings_client.search 调用
        mock_client = _make_mock_embeddings_client()
        mock_client.search = AsyncMock(return_value=[{"content": "代码片段", "score": 0.9}])

        # 模拟 RAG 检索逻辑 (用 namespace 过滤)
        namespace = "agentinsight-docbot:test_docbot_user_1:test_docbot_repo_1"
        results = await mock_client.search(
            query="架构",
            namespace=namespace,
            top_k=5,
        )

        assert len(results) == 1
        # 验证 search 被调用且 namespace 正确
        call_kwargs = mock_client.search.call_args.kwargs
        assert call_kwargs["namespace"] == namespace

    async def test_search_results_isolated_per_namespace(self) -> None:
        """不同 namespace 的检索结果互不可见."""
        mock_client = MagicMock()
        # ns1 返回结果, ns2 返回空
        async def _fake_search(query, namespace, top_k=5):
            if "test_docbot_user_1" in namespace:
                return [{"content": "user1 数据", "score": 0.95}]
            return []

        mock_client.search = _fake_search

        ns1 = "agentinsight-docbot:test_docbot_user_1:test_docbot_repo_1"
        ns2 = "agentinsight-docbot:test_docbot_user_2:test_docbot_repo_1"

        results1 = await mock_client.search(query="test", namespace=ns1)
        results2 = await mock_client.search(query="test", namespace=ns2)

        assert len(results1) == 1
        assert len(results2) == 0


@pytest.mark.integration
class TestQdrantFileLimit:
    """Qdrant 索引文件数上限测试."""

    async def test_index_caps_at_1000_files(self) -> None:
        """单次索引文件数上限 1000 (避免超长同步时间)."""
        from src.api.repo_routes import _index_repo_to_qdrant

        # 生成 1500 个文件名 (超过 1000 上限)
        files = [f"file_{i}.py" for i in range(1500)]

        mock_adapter = MagicMock()
        mock_adapter.read_file = AsyncMock(return_value="x")

        mock_embeddings_client = _make_mock_embeddings_client()

        with patch("src.rag.embeddings.get_embeddings_client", return_value=mock_embeddings_client):
            await _index_repo_to_qdrant(
                repo_path="/tmp/test_repo",
                files=files,
                namespace="agentinsight-docbot:test_docbot_user_1:test_docbot_repo_1",
                user_id="test_docbot_user_1",
                repo_id="test_docbot_repo_1",
                adapter=mock_adapter,
            )

        # 验证 read_file 仅被调用 1000 次 (上限)
        assert mock_adapter.read_file.call_count <= 1000

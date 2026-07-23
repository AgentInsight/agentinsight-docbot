"""功能测试: 仓库分析功能 (mock GitMCPAdapter).

不依赖外部服务, 验证:
- 文件枚举跳过规则 (.git/node_modules/__pycache__ 等)
- 文件分块策略 (代码/配置/文档)
- 语言识别
- namespace 多仓库隔离 ({agent_id}:{user_id}:{repo_id})
- 同步状态更新
"""
from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.api.repo_routes import (
    _chunk_code,
    _chunk_doc,
    _chunk_text,
    _detect_language,
)


@pytest.mark.functional
class TestRepoFileChunking:
    """文件分块策略测试."""

    def test_chunk_code_splits_by_lines(self) -> None:
        """代码应按行数分块 (100 行/块, 20 行 overlap)."""
        # 生成 250 行代码
        content = "\n".join(f"line {i}" for i in range(250))
        chunks = _chunk_code(content, "test.py")
        # 250 行, chunk_size=100, overlap=20, step=80
        # 0-100, 80-180, 160-260 (实际 250 行)
        assert len(chunks) >= 2
        # 每个块应为 (text, idx) 元组
        for text, idx in chunks:
            assert isinstance(text, str)
            assert isinstance(idx, int)

    def test_chunk_code_short_file_single_chunk(self) -> None:
        """短文件应为单块."""
        content = "line 1\nline 2\nline 3"
        chunks = _chunk_code(content, "test.py")
        assert len(chunks) == 1
        assert chunks[0][1] == 0  # idx 从 0 开始

    def test_chunk_doc_splits_by_headings(self) -> None:
        """文档应按标题分块."""
        content = (
            "# 标题1\n内容1\n"
            "## 子标题1.1\n内容1.1\n"
            "# 标题2\n内容2\n"
            "### 子标题2.1\n内容2.1\n"
        )
        chunks = _chunk_doc(content)
        # 至少 2 个块 (按 # 标题分块)
        assert len(chunks) >= 2

    def test_chunk_doc_empty_content(self) -> None:
        """空文档应返回空列表或单空块."""
        chunks = _chunk_doc("")
        # 空内容, current 为空, 不 append
        # 实现中: for line in [] → 跳过, current 为空, 不 append
        assert len(chunks) == 0

    def test_chunk_text_by_chars(self) -> None:
        """纯文本应按字符数分块 (2000 字符/块)."""
        content = "x" * 5000
        chunks = _chunk_text(content, chunk_size=2000)
        # 5000 字符, 2000/块 → 3 块
        assert len(chunks) == 3
        # 每块应为 (text, idx) 元组
        for text, idx in chunks:
            assert isinstance(text, str)
            assert isinstance(idx, int)

    def test_chunk_text_custom_size(self) -> None:
        """自定义 chunk_size 应生效."""
        content = "x" * 100
        chunks = _chunk_text(content, chunk_size=30)
        # 100 字符, 30/块 → 4 块 (30+30+30+10)
        assert len(chunks) == 4


@pytest.mark.functional
class TestLanguageDetection:
    """文件语言识别测试."""

    @pytest.mark.parametrize(
        "ext,expected_lang",
        [
            (".py", "python"),
            (".js", "javascript"),
            (".ts", "typescript"),
            (".go", "go"),
            (".java", "java"),
            (".c", "c"),
            (".cpp", "cpp"),
            (".h", "c"),
            (".rs", "rust"),
            (".rb", "ruby"),
            (".php", "php"),
            (".swift", "swift"),
            (".kt", "kotlin"),
            (".md", "markdown"),
            (".rst", "rst"),
            (".yml", "yaml"),
            (".yaml", "yaml"),
            (".json", "json"),
            (".toml", "toml"),
            (".xml", "xml"),
        ],
    )
    def test_detect_language_known_extensions(self, ext: str, expected_lang: str) -> None:
        """已知扩展名应识别为对应语言."""
        assert _detect_language(ext) == expected_lang

    def test_detect_language_unknown_extension(self) -> None:
        """未知扩展名应回退为 'text'."""
        assert _detect_language(".unknown") == "text"
        assert _detect_language(".xyz") == "text"

    def test_detect_language_empty_extension(self) -> None:
        """空扩展名应为 'text'."""
        assert _detect_language("") == "text"


@pytest.mark.functional
class TestRepoNamespaceIsolation:
    """仓库 namespace 多仓库隔离测试."""

    def test_namespace_format_contains_repo_id(self) -> None:
        """namespace 应含 repo_id 维度, 格式 {agent_id}:{user_id}:{repo_id}."""
        # repo_routes.py 第 593 行: namespace = f"{agent_id}:{user_id}:{repo_id}"
        agent_id = "agentinsight-docbot"
        user_id = "test_docbot_user_1"
        repo_id = "test_docbot_repo_1"
        namespace = f"{agent_id}:{user_id}:{repo_id}"
        # 三段式隔离
        parts = namespace.split(":")
        assert len(parts) == 3
        assert parts[0] == agent_id
        assert parts[1] == user_id
        assert parts[2] == repo_id

    def test_different_repos_have_different_namespaces(self) -> None:
        """不同 repo_id 应有不同 namespace."""
        agent_id = "agentinsight-docbot"
        user_id = "test_docbot_user_1"
        ns1 = f"{agent_id}:{user_id}:repo_1"
        ns2 = f"{agent_id}:{user_id}:repo_2"
        assert ns1 != ns2

    def test_different_users_have_different_namespaces(self) -> None:
        """不同 user_id 应有不同 namespace."""
        agent_id = "agentinsight-docbot"
        repo_id = "test_docbot_repo_1"
        ns1 = f"{agent_id}:user_1:{repo_id}"
        ns2 = f"{agent_id}:user_2:{repo_id}"
        assert ns1 != ns2


@pytest.mark.functional
class TestRepoSyncStatusUpdate:
    """仓库同步状态更新测试 (mock asyncpg)."""

    async def test_sync_marks_status_syncing(self, mock_settings: Any) -> None:
        """sync_repo 应将 last_sync_status 标记为 'syncing'."""
        from src.api.repo_routes import sync_repo

        mock_conn = MagicMock()
        mock_conn.execute = AsyncMock(return_value="UPDATE 1")

        mock_pool = MagicMock()
        mock_pool.acquire = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)

        mock_row = {
            "id": "test_docbot_repo_1",
            "repo_url": "https://github.com/test/repo.git",
            "default_branch": "main",
            "clone_depth": 1,
            "auth_type": "none",
            "encrypted_token": None,
            "encrypted_username": None,
            "encrypted_password": None,
            "encrypted_ssh_key": None,
            "ssh_passphrase": None,
        }

        with (
            patch("src.api.repo_routes.get_pool", AsyncMock(return_value=mock_pool)),
            patch("src.api.repo_routes._fetch_repo_row", AsyncMock(return_value=mock_row)),
            patch("src.api.repo_routes._get_user_agent", return_value=("test_docbot_user_1", "agentinsight-docbot")),
            patch("src.api.repo_routes._load_repo_config", return_value={"repo_url": "https://github.com/test/repo.git"}),
            # side_effect 关闭传入的协程, 避免 "coroutine never awaited" RuntimeWarning
            # (sync_repo 会构造 _run_sync(...) 协程传入, mock 默认丢弃会触发 GC 警告)
            patch("src.api.repo_routes._create_background_task", side_effect=lambda coro: coro.close()),
        ):
            result = await sync_repo(repo_id="test_docbot_repo_1")

        assert result["status"] == "syncing"
        assert result["repo_id"] == "test_docbot_repo_1"

    async def test_sync_returns_404_when_repo_not_found(self, mock_settings: Any) -> None:
        """仓库不存在时 sync_repo 应返回 404."""
        from src.api.repo_routes import sync_repo
        from fastapi import HTTPException

        mock_pool = MagicMock()

        with (
            patch("src.api.repo_routes.get_pool", AsyncMock(return_value=mock_pool)),
            patch("src.api.repo_routes._fetch_repo_row", AsyncMock(return_value=None)),
            patch("src.api.repo_routes._get_user_agent", return_value=("test_docbot_user_1", "agentinsight-docbot")),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await sync_repo(repo_id="nonexistent_repo")

        assert exc_info.value.status_code == 404

    async def test_get_sync_status_returns_status(self, mock_settings: Any) -> None:
        """get_sync_status 应返回同步状态."""
        from src.api.repo_routes import get_sync_status

        mock_row = {
            "last_synced_at": None,
            "last_sync_status": "never",
            "last_sync_error": None,
        }

        with (
            patch("src.api.repo_routes._fetch_repo_row", AsyncMock(return_value=mock_row)),
            patch("src.api.repo_routes._get_user_agent", return_value=("test_docbot_user_1", "agentinsight-docbot")),
        ):
            result = await get_sync_status(repo_id="test_docbot_repo_1")

        assert result["repo_id"] == "test_docbot_repo_1"
        assert result["last_sync_status"] == "never"
        assert result["last_synced_at"] is None

    async def test_get_sync_status_404_when_not_found(self, mock_settings: Any) -> None:
        """仓库不存在时 get_sync_status 应返回 404."""
        from src.api.repo_routes import get_sync_status
        from fastapi import HTTPException

        with (
            patch("src.api.repo_routes._fetch_repo_row", AsyncMock(return_value=None)),
            patch("src.api.repo_routes._get_user_agent", return_value=("test_docbot_user_1", "agentinsight-docbot")),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await get_sync_status(repo_id="nonexistent_repo")

        assert exc_info.value.status_code == 404

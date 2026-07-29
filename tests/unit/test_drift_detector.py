"""单元测试: P1-5.3.2 代码变更触发文档漂移检测.

测试目标:
- detect_doc_drift 在无 last_doc_commit_hash 时跳过 (首次同步)
- detect_doc_drift 在 commit 相同时无漂移
- detect_doc_drift 在 commit 不同时检测变更文件
- detect_doc_drift 通过 report_citations 标记 stale 报告
- detect_doc_drift 在 git diff 失败时保守标记全部报告为 stale
- detect_doc_drift 异常时不阻断流程
- update_last_doc_commit 更新成功 / 失败不阻断
"""
from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.skills.docbot.drift_detector import (
    detect_doc_drift,
    update_last_doc_commit,
)


# ========== Mock 工具 ==========


class MockPool:
    """模拟 asyncpg 连接池."""

    def __init__(
        self,
        fetchrow_result: dict | None = None,
        fetch_results: list[dict] | None = None,
        execute_should_fail: bool = False,
    ) -> None:
        self._fetchrow_result = fetchrow_result or {}
        self._fetch_results = fetch_results or []
        self._execute_should_fail = execute_should_fail
        self.execute_calls: list[tuple] = []

    def acquire(self) -> Any:
        conn = MagicMock()
        conn.fetchrow = AsyncMock(return_value=self._fetchrow_result)
        conn.fetch = AsyncMock(return_value=self._fetch_results)
        conn.execute = AsyncMock(side_effect=self._mock_execute)
        cm = MagicMock()
        cm.__aenter__ = AsyncMock(return_value=conn)
        cm.__aexit__ = AsyncMock(return_value=None)
        return cm

    async def _mock_execute(self, *args: Any) -> str:
        if self._execute_should_fail:
            raise RuntimeError("mock execute failure")
        self.execute_calls.append(args)
        return "OK"


class MockAdapter:
    """模拟 GitMCPAdapter."""

    def __init__(
        self,
        head_commit: str = "abc123def456789012345678901234567890abcd",
        changed_files: list[str] | None = None,
        head_should_fail: bool = False,
        diff_should_fail: bool = False,
    ) -> None:
        self._head_commit = head_commit
        self._changed_files = changed_files if changed_files is not None else []
        self._head_should_fail = head_should_fail
        self._diff_should_fail = diff_should_fail

    async def get_head_commit_hash(self, repo_path: str) -> str:
        if self._head_should_fail:
            raise RuntimeError("mock get_head_commit_hash failure")
        return self._head_commit

    async def list_changed_files(
        self, repo_path: str, from_commit: str, to_commit: str = "HEAD"
    ) -> list[str]:
        if self._diff_should_fail:
            raise RuntimeError("mock list_changed_files failure")
        return self._changed_files


# ========== detect_doc_drift 测试 ==========


class TestDetectDocDrift:
    """校验漂移检测逻辑."""

    @pytest.mark.asyncio
    async def test_skip_when_no_last_doc_commit(self) -> None:
        """无 last_doc_commit_hash 时应跳过 (首次同步)."""
        pool = MockPool(fetchrow_result={"last_doc_commit_hash": None})
        adapter = MockAdapter()

        result = await detect_doc_drift(
            repo_id="repo-1",
            user_id="user-1",
            agent_id="agentinsight-docbot",
            repo_path="/tmp/repos/user-1/repo-1",
            adapter=adapter,
            pool=pool,
        )

        assert result["skipped"] is True
        assert result["detected"] is False
        assert result["current_commit"] is None
        assert result["stale_reports"] == []

    @pytest.mark.asyncio
    async def test_no_drift_when_commits_equal(self) -> None:
        """commit 相同时应无漂移."""
        commit = "abc123def456789012345678901234567890abcd"
        pool = MockPool(fetchrow_result={"last_doc_commit_hash": commit})
        adapter = MockAdapter(head_commit=commit)

        result = await detect_doc_drift(
            repo_id="repo-1",
            user_id="user-1",
            agent_id="agentinsight-docbot",
            repo_path="/tmp/repos/user-1/repo-1",
            adapter=adapter,
            pool=pool,
        )

        assert result["detected"] is False
        assert result["current_commit"] == commit
        assert result["last_doc_commit"] == commit
        assert result["changed_files"] == []

    @pytest.mark.asyncio
    async def test_drift_detected_with_changed_files(self) -> None:
        """commit 不同且有变更文件时, 应检测到漂移."""
        pool = MockPool(
            fetchrow_result={"last_doc_commit_hash": "old_commit_hash_1234567890abcd1234"},
            fetch_results=[{"report_id": "report-1"}, {"report_id": "report-2"}],
        )
        adapter = MockAdapter(
            head_commit="new_commit_hash_1234567890abcd1234",
            changed_files=["src/server.py", "src/api/routes.py"],
        )

        result = await detect_doc_drift(
            repo_id="repo-1",
            user_id="user-1",
            agent_id="agentinsight-docbot",
            repo_path="/tmp/repos/user-1/repo-1",
            adapter=adapter,
            pool=pool,
        )

        assert result["detected"] is True
        assert result["current_commit"] == "new_commit_hash_1234567890abcd1234"
        assert result["last_doc_commit"] == "old_commit_hash_1234567890abcd1234"
        assert len(result["changed_files"]) == 2
        assert len(result["stale_reports"]) == 2
        assert "report-1" in result["stale_reports"]
        assert "report-2" in result["stale_reports"]

    @pytest.mark.asyncio
    async def test_drift_no_stale_reports_when_no_citations_match(self) -> None:
        """commit 不同但无报告引用变更文件时, detected 应为 False."""
        pool = MockPool(
            fetchrow_result={"last_doc_commit_hash": "old_commit_hash_1234567890abcd1234"},
            fetch_results=[],  # 无匹配的 stale 报告
        )
        adapter = MockAdapter(
            head_commit="new_commit_hash_1234567890abcd1234",
            changed_files=["src/unrelated.py"],
        )

        result = await detect_doc_drift(
            repo_id="repo-1",
            user_id="user-1",
            agent_id="agentinsight-docbot",
            repo_path="/tmp/repos/user-1/repo-1",
            adapter=adapter,
            pool=pool,
        )

        assert result["detected"] is False  # 有变更但无 stale 报告
        assert len(result["changed_files"]) == 1
        assert result["stale_reports"] == []

    @pytest.mark.asyncio
    async def test_drift_no_changed_files(self) -> None:
        """commit 不同但无变更文件时 (仅 metadata 变更), 应无漂移."""
        pool = MockPool(
            fetchrow_result={"last_doc_commit_hash": "old_commit_hash_1234567890abcd1234"},
        )
        adapter = MockAdapter(
            head_commit="new_commit_hash_1234567890abcd1234",
            changed_files=[],  # 无变更文件
        )

        result = await detect_doc_drift(
            repo_id="repo-1",
            user_id="user-1",
            agent_id="agentinsight-docbot",
            repo_path="/tmp/repos/user-1/repo-1",
            adapter=adapter,
            pool=pool,
        )

        assert result["detected"] is False
        assert result["changed_files"] == []

    @pytest.mark.asyncio
    async def test_drift_git_diff_fails_conservative_mark(self) -> None:
        """git diff 失败时, 应保守标记全部报告为 stale."""
        pool = MockPool(
            fetchrow_result={"last_doc_commit_hash": "old_commit_hash_1234567890abcd1234"},
            fetch_results=[{"report_id": "report-1"}, {"report_id": "report-2"}],
        )
        adapter = MockAdapter(
            head_commit="new_commit_hash_1234567890abcd1234",
            diff_should_fail=True,  # git diff 失败
        )

        result = await detect_doc_drift(
            repo_id="repo-1",
            user_id="user-1",
            agent_id="agentinsight-docbot",
            repo_path="/tmp/repos/user-1/repo-1",
            adapter=adapter,
            pool=pool,
        )

        # git diff 失败时 changed_files = ["*"], 标记全部报告为 stale
        assert result["detected"] is True
        assert "*" in result["changed_files"]
        assert len(result["stale_reports"]) == 2

    @pytest.mark.asyncio
    async def test_drift_head_commit_fails(self) -> None:
        """get_head_commit_hash 失败时, 应返回 error 但不阻断."""
        pool = MockPool(
            fetchrow_result={"last_doc_commit_hash": "old_commit_hash_1234567890abcd1234"},
        )
        adapter = MockAdapter(head_should_fail=True)

        result = await detect_doc_drift(
            repo_id="repo-1",
            user_id="user-1",
            agent_id="agentinsight-docbot",
            repo_path="/tmp/repos/user-1/repo-1",
            adapter=adapter,
            pool=pool,
        )

        assert result["detected"] is False
        assert result["error"] is not None
        assert "get_head_commit_hash" in result["error"]

    @pytest.mark.asyncio
    async def test_drift_repo_not_found(self) -> None:
        """user_git_repos 记录不存在时, 应跳过."""
        pool = MockPool(fetchrow_result=None)
        adapter = MockAdapter()

        result = await detect_doc_drift(
            repo_id="nonexistent-repo",
            user_id="user-1",
            agent_id="agentinsight-docbot",
            repo_path="/tmp/repos/user-1/nonexistent-repo",
            adapter=adapter,
            pool=pool,
        )

        assert result["skipped"] is True
        assert result["error"] is not None


# ========== update_last_doc_commit 测试 ==========


class TestUpdateLastDocCommit:
    """校验 update_last_doc_commit."""

    @pytest.mark.asyncio
    async def test_update_success(self) -> None:
        """成功更新 last_doc_commit_hash."""
        pool = MockPool()
        commit = "abc123def456789012345678901234567890abcd"

        await update_last_doc_commit(
            pool=pool,
            repo_id="repo-1",
            user_id="user-1",
            agent_id="agentinsight-docbot",
            commit_hash=commit,
        )

        assert len(pool.execute_calls) == 1

    @pytest.mark.asyncio
    async def test_update_failure_no_raise(self) -> None:
        """更新失败时不抛异常 (仅记录日志)."""
        pool = MockPool(execute_should_fail=True)
        commit = "abc123def456789012345678901234567890abcd"

        # 不应抛异常
        await update_last_doc_commit(
            pool=pool,
            repo_id="repo-1",
            user_id="user-1",
            agent_id="agentinsight-docbot",
            commit_hash=commit,
        )

"""探索性测试: 并发请求场景.

不依赖外部服务, 探索性验证:
- 多个用户并发请求 (user_id 隔离)
- 同一用户多个会话并发 (session_id 隔离)
- MAX_CONCURRENT_REPORTS=3 信号量限制
- spawn_b_tasks 内部并发 (asyncio.gather + Semaphore)
- 后台同步任务 _background_sync_tasks 集合管理 (防 GC)
- 并发请求下 Redis cache_key 不串扰

探索性目标 (AGENTS.md 第 13 章探索性测试):
- 发现并发场景下的竞态条件
- 不依赖 --run-external
- 用 mock 替代外部服务
"""
from __future__ import annotations

import asyncio
from contextlib import contextmanager
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.graph.nodes import spawn_b_tasks_node


# mock DB 层 (coordinator_a 校验通过后查 user_git_repos 加载 repo_config)
_MOCK_REPO_ROW = {
    "id": "test_docbot_repo_1", "agent_id": "agentinsight-docbot",
    "user_id": "test_docbot_user_1", "repo_name": "test-repo",
    "platform": "github", "repo_url": "https://github.com/test/repo.git",
    "default_branch": "main", "auth_type": "none",
    "encrypted_token": None, "encrypted_username": None,
    "encrypted_password": None, "encrypted_ssh_key": None,
    "ssh_passphrase": None, "clone_depth": 0, "enabled": True,
}
_MOCK_REPO_CONFIG = {
    "repo_url": "https://github.com/test/repo.git",
    "default_branch": "main", "clone_depth": 0, "auth_type": "none",
    "token": None, "username": None, "password": None,
    "ssh_key": None, "ssh_passphrase": None,
}


@contextmanager
def _mock_repo_db():
    """mock coordinator_a 的 DB 检查 (不依赖真实 Postgres)."""
    with (
        patch("src.memory.db_initializer.get_pool", AsyncMock(return_value=MagicMock())),
        patch("src.api.repo_routes._fetch_repo_row", AsyncMock(return_value=_MOCK_REPO_ROW)),
        patch("src.api.repo_routes._load_repo_config", return_value=_MOCK_REPO_CONFIG),
    ):
        yield


def _make_mock_settings() -> MagicMock:
    """构造 mock Settings."""
    settings = MagicMock()
    settings.agent_name = "agentinsight-docbot"
    settings.agent_id = "agentinsight-docbot"
    settings.git_credential_key = "test" * 32
    settings.max_concurrent_reports = 3
    settings.max_chapters_per_report = 20
    settings.max_revisions_per_chapter = 3
    settings.max_llm_concurrency = 5
    settings.max_rag_concurrency = 10
    settings.docbot_cache_ttl = 86400
    settings.redis_url = None
    return settings


def _make_initial_state(
    user_id: str = "test_docbot_user_1",
    session_id: str = "test_docbot_session_1",
    repo_id: str = "test_docbot_repo_1",
    report_types: list[str] | None = None,
) -> dict[str, Any]:
    """构造初始 DocbotState."""
    return {
        "messages": [],
        "user_id": user_id,
        "session_id": session_id,
        "agent_id": "agentinsight-docbot",
        "repo_id": repo_id,
        "report_types": report_types or ["architecture"],
        "report_format": "markdown",
        "language": "zh",
        "report_tasks": [],
        "final_reports": [],
        "errors": [],
        "iteration_count": 1,
    }


@pytest.mark.exploratory
class TestConcurrentMultiUserRequests:
    """多用户并发请求隔离."""

    async def test_concurrent_users_have_isolated_state(self) -> None:
        """并发用户的 state 应相互隔离."""
        # 构造 3 个用户的并发请求
        users = ["test_docbot_user_1", "test_docbot_user_2", "test_docbot_user_3"]
        states = [
            _make_initial_state(
                user_id=u,
                session_id=f"test_docbot_session_{u}",
                repo_id=f"test_docbot_repo_{u}",
            )
            for u in users
        ]

        # 并发执行 coordinator.run (用 mock trace_agent)
        coordinator_calls = []

        async def _run_coordinator(state):
            from src.agents.docbot.coordinator import CoordinatorA
            coordinator = CoordinatorA()
            with patch("src.agents.docbot.coordinator.trace_agent") as mock_trace, \
                 _mock_repo_db():
                mock_cm = MagicMock()
                mock_cm.__aenter__ = AsyncMock(return_value=mock_cm)
                mock_cm.__aexit__ = AsyncMock(return_value=None)
                mock_trace.return_value = mock_cm
                state["messages"] = [
                    {"role": "user", "content": f'{{"action":"generate_docs","repo_id":"{state["repo_id"]}","report_types":["architecture"]}}'}
                ]
                return await coordinator.run(state, settings=_make_mock_settings())

        results = await asyncio.gather(*[_run_coordinator(s) for s in states])

        # 验证每个用户的 delta 含各自的 repo_id (无串扰)
        for i, user_id in enumerate(users):
            assert results[i].get("repo_id") == f"test_docbot_repo_{user_id}"

    async def test_concurrent_sessions_same_user_isolated(self) -> None:
        """同一用户多个会话并发应相互隔离."""
        user_id = "test_docbot_user_1"
        sessions = ["test_docbot_session_a", "test_docbot_session_b", "test_docbot_session_c"]
        states = [
            _make_initial_state(
                user_id=user_id,
                session_id=s,
                repo_id=f"test_docbot_repo_{s}",
            )
            for s in sessions
        ]

        async def _run_coordinator(state):
            from src.agents.docbot.coordinator import CoordinatorA
            coordinator = CoordinatorA()
            with patch("src.agents.docbot.coordinator.trace_agent") as mock_trace, \
                 _mock_repo_db():
                mock_cm = MagicMock()
                mock_cm.__aenter__ = AsyncMock(return_value=mock_cm)
                mock_cm.__aexit__ = AsyncMock(return_value=None)
                mock_trace.return_value = mock_cm
                state["messages"] = [
                    {"role": "user", "content": f'{{"action":"generate_docs","repo_id":"{state["repo_id"]}","report_types":["architecture"]}}'}
                ]
                return await coordinator.run(state, settings=_make_mock_settings())

        results = await asyncio.gather(*[_run_coordinator(s) for s in states])

        # 每个 session 应有独立的 repo_id
        for i, session_id in enumerate(sessions):
            assert results[i].get("repo_id") == f"test_docbot_repo_{session_id}"


@pytest.mark.exploratory
class TestConcurrentReportDispatch:
    """spawn_b_tasks 并发派发."""

    async def test_concurrent_dispatch_uses_semaphore(self) -> None:
        """spawn_b_tasks 应使用 Semaphore 限制并发数."""
        settings = _make_mock_settings()
        # 5 种报告类型, 但 max_concurrent_reports=3
        state = _make_initial_state(
            report_types=["architecture", "design", "requirements", "testcase", "optimization"]
        )

        # 跟踪并发数
        max_concurrent = 0
        current_concurrent = 0
        lock = asyncio.Lock()

        async def _fake_ainvoke(_state, config=None):
            nonlocal max_concurrent, current_concurrent
            async with lock:
                current_concurrent += 1
                if current_concurrent > max_concurrent:
                    max_concurrent = current_concurrent
            await asyncio.sleep(0.05)  # 模拟 IO
            async with lock:
                current_concurrent -= 1
            rt = _state.get("report_type", "unknown")
            return {
                "final_cache_key": f"docbot:test:cache:{rt}",
                "report_id": f"test_docbot_report_uuid_{rt}",
                "report_title": f"{rt} 文档",
                "report_summary": "",
                "report_image_svg": "",
                "download_urls": {},
            }

        mock_subgraph = MagicMock()
        mock_subgraph.ainvoke = _fake_ainvoke

        # spawn_b_tasks 不直接访问 Redis, 仅需 mock build_report_subgraph
        with patch("src.graph.report_builder.build_report_subgraph", return_value=mock_subgraph):
            spawn_delta = await spawn_b_tasks_node(state, settings=settings)

        # 应生成 5 个 report_tasks
        assert len(spawn_delta["report_tasks"]) == 5
        # 并发数不应超过 max_concurrent_reports=3
        # (注意: Semaphore 限制并发, 但 max_concurrent 观测可能因时序略低)
        assert max_concurrent <= 3

    async def test_concurrent_dispatch_all_succeed(self) -> None:
        """并发派发的所有报告应全部成功."""
        settings = _make_mock_settings()
        state = _make_initial_state(
            report_types=["architecture", "design", "requirements", "testcase"]
        )

        async def _fake_ainvoke(state_, config=None):
            rt = state_.get("report_type")
            await asyncio.sleep(0.01)  # 模拟短暂 IO
            return {
                "final_cache_key": f"docbot:test:cache:{rt}",
                "report_id": f"test_docbot_report_uuid_{rt}",
                "report_title": f"{rt} 文档",
                "report_summary": f"{rt} 摘要",
                "report_image_svg": "",
                "download_urls": {},
            }

        mock_subgraph = MagicMock()
        mock_subgraph.ainvoke = _fake_ainvoke

        # spawn_b_tasks 不直接访问 Redis, 仅需 mock build_report_subgraph
        with patch("src.graph.report_builder.build_report_subgraph", return_value=mock_subgraph):
            spawn_delta = await spawn_b_tasks_node(state, settings=settings)

        # 所有 4 种报告应成功
        assert len(spawn_delta["report_tasks"]) == 4
        assert "errors" not in spawn_delta or not spawn_delta["errors"]

    async def test_concurrent_dispatch_with_one_failure(self) -> None:
        """并发派发中一个失败, 其他应不受影响."""
        settings = _make_mock_settings()
        state = _make_initial_state(
            report_types=["architecture", "design", "requirements"]
        )

        async def _fake_ainvoke(state_, config=None):
            rt = state_.get("report_type")
            if rt == "design":
                raise RuntimeError("design 子图失败")
            await asyncio.sleep(0.01)
            return {
                "final_cache_key": f"docbot:test:cache:{rt}",
                "report_id": f"test_docbot_report_uuid_{rt}",
                "report_title": f"{rt} 文档",
                "report_summary": "",
                "report_image_svg": "",
                "download_urls": {},
            }

        mock_subgraph = MagicMock()
        mock_subgraph.ainvoke = _fake_ainvoke

        # spawn_b_tasks 不直接访问 Redis, 仅需 mock build_report_subgraph
        with patch("src.graph.report_builder.build_report_subgraph", return_value=mock_subgraph):
            spawn_delta = await spawn_b_tasks_node(state, settings=settings)

        # 失败的 design 应记入 errors
        assert "errors" in spawn_delta
        assert any("design" in e for e in spawn_delta["errors"])
        # 成功的 architecture 和 requirements 应入 report_tasks
        successful_types = [t["report_type"] for t in spawn_delta["report_tasks"]]
        assert "architecture" in successful_types
        assert "requirements" in successful_types
        assert "design" not in successful_types


@pytest.mark.exploratory
class TestBackgroundSyncTaskManagement:
    """后台同步任务集合管理 (防 GC 静默取消)."""

    def test_background_sync_tasks_set_exists(self) -> None:
        """_background_sync_tasks 集合应存在 (防止 GC 静默取消)."""
        from src.api.repo_routes import _background_sync_tasks
        assert isinstance(_background_sync_tasks, set)

    async def test_create_background_task_adds_to_set(self) -> None:
        """_create_background_task 应将任务加入集合."""
        from src.api.repo_routes import _background_sync_tasks, _create_background_task

        async def _dummy_coro():
            await asyncio.sleep(0.01)

        initial_count = len(_background_sync_tasks)
        task = _create_background_task(_dummy_coro())
        # 任务应被加入集合
        assert len(_background_sync_tasks) >= initial_count + 1

        # 等待任务完成
        await task
        # 完成后应从集合中移除 (add_done_callback 回调)
        await asyncio.sleep(0.01)  # 等 callback 执行
        assert task not in _background_sync_tasks

    async def test_multiple_background_tasks_managed(self) -> None:
        """多个后台任务应都被管理."""
        from src.api.repo_routes import _background_sync_tasks, _create_background_task

        async def _dummy_coro(idx: int):
            await asyncio.sleep(0.01 * idx)

        tasks = [_create_background_task(_dummy_coro(i)) for i in range(3)]
        # 所有任务应都在集合中
        for t in tasks:
            assert t in _background_sync_tasks

        # 等待全部完成
        await asyncio.gather(*tasks)
        await asyncio.sleep(0.05)  # 等 callback 执行
        # 全部应从集合中移除
        for t in tasks:
            assert t not in _background_sync_tasks

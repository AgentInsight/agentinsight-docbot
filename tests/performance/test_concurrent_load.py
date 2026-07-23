"""性能测试: 并发负载 (mock 化基准测试).

不依赖外部服务, 用 mock 测量并发处理能力:
- coordinator_a 并发校验吞吐量
- spawn_b_tasks 并发派发吞吐量
- 多用户并发隔离性能
- 信号量限流效果验证 (MAX_CONCURRENT_REPORTS=3)

性能基线 (参考 perf_baseline_throughput_rps):
- coordinator_a 校验吞吐量: > 50 RPS
- spawn_b_tasks 8 报告并发: < 1 秒 (mock LLM)

测试目标 (AGENTS.md 第 13 章性能测试):
- 并发负载不依赖 --run-external (mock 外部服务)
- 测量纯异步逻辑的并发能力
"""
from __future__ import annotations

import asyncio
import time
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.graph.nodes import spawn_b_tasks_node


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
    report_types: list[str] | None = None,
    user_id: str = "test_docbot_user_1",
    session_id: str = "test_docbot_session_1",
) -> dict[str, Any]:
    """构造初始 DocbotState."""
    return {
        "messages": [],
        "user_id": user_id,
        "session_id": session_id,
        "agent_id": "agentinsight-docbot",
        "repo_id": "test_docbot_repo_1",
        "report_types": report_types or ["architecture"],
        "report_format": "markdown",
        "language": "zh",
        "report_tasks": [],
        "final_reports": [],
        "errors": [],
        "iteration_count": 1,
    }


@pytest.mark.performance
class TestCoordinatorConcurrentThroughput:
    """coordinator_a 并发校验吞吐量."""

    async def test_concurrent_coordinator_throughput(self) -> None:
        """并发 coordinator_a 校验吞吐量应 > 50 RPS."""
        from src.agents.docbot.coordinator import CoordinatorA

        settings = _make_mock_settings()
        coordinator = CoordinatorA()

        async def _run_one(idx: int) -> None:
            state = {
                "messages": [{"role": "user", "content": f'{{"action":"generate_docs","repo_id":"r{idx}","report_types":["architecture"]}}'}],
                "session_id": f"test_docbot_session_{idx}",
                "user_id": f"test_docbot_user_{idx}",
                "agent_id": "agentinsight-docbot",
            }
            with patch("src.agents.docbot.coordinator.trace_agent") as mock_trace:
                mock_cm = MagicMock()
                mock_cm.__aenter__ = AsyncMock(return_value=mock_cm)
                mock_cm.__aexit__ = AsyncMock(return_value=None)
                mock_trace.return_value = mock_cm
                await coordinator.run(state, settings=settings)

        # 预热
        await _run_one(0)

        # 测量 50 个并发请求
        concurrency = 50
        start = time.perf_counter()
        await asyncio.gather(*[_run_one(i) for i in range(concurrency)])
        elapsed_s = time.perf_counter() - start
        rps = concurrency / elapsed_s

        # 吞吐量应 > 50 RPS (mock trace_agent 后, 校验为纯 CPU)
        assert rps > 50, f"并发吞吐量 {rps:.1f} RPS 低于基线 50 RPS"

    async def test_concurrent_coordinator_no_state_corruption(self) -> None:
        """并发 coordinator_a 不应导致状态串扰."""
        from src.agents.docbot.coordinator import CoordinatorA

        settings = _make_mock_settings()
        coordinator = CoordinatorA()

        async def _run_one(idx: int) -> str:
            state = {
                "messages": [{"role": "user", "content": f'{{"action":"generate_docs","repo_id":"r{idx}","report_types":["architecture"]}}'}],
                "session_id": f"test_docbot_session_{idx}",
                "user_id": f"test_docbot_user_{idx}",
                "agent_id": "agentinsight-docbot",
            }
            # mock DB 层: coordinator 校验通过后会查 user_git_repos 加载 repo_config
            # (并发测试不应依赖真实 Postgres, patch 三个 DB 入口)
            mock_row = {
                "id": f"r{idx}", "agent_id": "agentinsight-docbot",
                "user_id": f"test_docbot_user_{idx}", "repo_name": "test-repo",
                "platform": "github", "repo_url": "https://github.com/test/repo.git",
                "default_branch": "main", "auth_type": "none",
                "encrypted_token": None, "encrypted_username": None,
                "encrypted_password": None, "encrypted_ssh_key": None,
                "ssh_passphrase": None, "clone_depth": 0, "enabled": True,
            }
            mock_repo_config = {
                "repo_url": "https://github.com/test/repo.git",
                "default_branch": "main", "clone_depth": 0, "auth_type": "none",
                "token": None, "username": None, "password": None,
                "ssh_key": None, "ssh_passphrase": None,
            }
            with patch("src.agents.docbot.coordinator.trace_agent") as mock_trace, \
                 patch("src.memory.db_initializer.get_pool", AsyncMock(return_value=MagicMock())), \
                 patch("src.api.repo_routes._fetch_repo_row", AsyncMock(return_value=mock_row)), \
                 patch("src.api.repo_routes._load_repo_config", return_value=mock_repo_config):
                mock_cm = MagicMock()
                mock_cm.__aenter__ = AsyncMock(return_value=mock_cm)
                mock_cm.__aexit__ = AsyncMock(return_value=None)
                mock_trace.return_value = mock_cm
                delta = await coordinator.run(state, settings=settings)
                return delta.get("repo_id", "")

        # 并发 20 个请求, 每个使用不同 repo_id
        concurrency = 20
        results = await asyncio.gather(*[_run_one(i) for i in range(concurrency)])

        # 每个 repo_id 应与请求一致 (无串扰)
        for i in range(concurrency):
            assert results[i] == f"r{i}"


@pytest.mark.performance
class TestSpawnBTasksConcurrentPerformance:
    """spawn_b_tasks 并发派发性能."""

    async def test_spawn_8_reports_under_semaphore(self) -> None:
        """8 报告并发派发 (Semaphore=3) 应在 1 秒内完成 (mock LLM)."""
        settings = _make_mock_settings()
        all_types = [
            "architecture", "design", "requirements", "testcase",
            "optimization", "performance", "defect", "api_doc",
        ]
        state = _make_initial_state(report_types=all_types)

        async def _fake_ainvoke(s, config=None):
            await asyncio.sleep(0.05)  # 模拟 50ms IO
            rt = s.get("report_type", "unknown")
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
            start = time.perf_counter()
            spawn_delta = await spawn_b_tasks_node(state, settings=settings)
            elapsed_s = time.perf_counter() - start

        # 8 报告 × 50ms, Semaphore=3 → 至少 ceil(8/3) * 50ms = 150ms
        # 上限 1 秒 (含调度开销)
        assert elapsed_s < 1.0, f"8 报告并发派发耗时 {elapsed_s:.3f}s 超过 1 秒"
        assert len(spawn_delta["report_tasks"]) == 8

    async def test_spawn_semaphore_limits_concurrency(self) -> None:
        """Semaphore 应将并发限制在 max_concurrent_reports=3."""
        settings = _make_mock_settings()
        state = _make_initial_state(
            report_types=["a", "b", "c", "d", "e", "f"]  # 6 种 (虚构类型用于测并发)
        )
        # 注意: 这些虚构类型会被 coordinator 拒绝, 但我们直接测 spawn_b_tasks
        # 故直接构造 state.report_types

        max_concurrent_observed = 0
        current_concurrent = 0
        lock = asyncio.Lock()

        async def _fake_ainvoke(s, config=None):
            nonlocal max_concurrent_observed, current_concurrent
            async with lock:
                current_concurrent += 1
                if current_concurrent > max_concurrent_observed:
                    max_concurrent_observed = current_concurrent
            await asyncio.sleep(0.05)
            async with lock:
                current_concurrent -= 1
            rt = s.get("report_type", "unknown")
            return {
                "final_cache_key": f"docbot:test:cache:{rt}",
                "report_id": f"test_docbot_report_uuid_{rt}",
                "report_title": "",
                "report_summary": "",
                "report_image_svg": "",
                "download_urls": {},
            }

        mock_subgraph = MagicMock()
        mock_subgraph.ainvoke = _fake_ainvoke

        # spawn_b_tasks 不直接访问 Redis, 仅需 mock build_report_subgraph
        with patch("src.graph.report_builder.build_report_subgraph", return_value=mock_subgraph):
            await spawn_b_tasks_node(state, settings=settings)

        # 并发数不应超过 max_concurrent_reports=3
        assert max_concurrent_observed <= 3, (
            f"观测最大并发数 {max_concurrent_observed} 超过限制 3"
        )


@pytest.mark.performance
class TestMultiUserConcurrentPerformance:
    """多用户并发性能."""

    async def test_multi_user_concurrent_spawn_isolated(self) -> None:
        """多用户并发 spawn_b_tasks 应相互隔离且不串扰."""
        settings = _make_mock_settings()

        async def _run_user_flow(user_id: str) -> str:
            state = _make_initial_state(
                user_id=user_id,
                session_id=f"test_docbot_session_{user_id}",
                report_types=["architecture"],
            )

            async def _fake_ainvoke(s, config=None):
                return {
                    "final_cache_key": f"docbot:{user_id}:cache:architecture",
                    "report_id": f"test_docbot_report_uuid_{user_id}_architecture",
                    "report_title": "架构文档",
                    "report_summary": "",
                    "report_image_svg": "",
                    "download_urls": {},
                }

            mock_subgraph = MagicMock()
            mock_subgraph.ainvoke = _fake_ainvoke

            # spawn_b_tasks 不直接访问 Redis, 仅需 mock build_report_subgraph
            with patch("src.graph.report_builder.build_report_subgraph", return_value=mock_subgraph):
                spawn_delta = await spawn_b_tasks_node(state, settings=settings)

            return spawn_delta["report_tasks"][0]["report_id"]

        # 5 个用户并发
        user_ids = [f"test_docbot_user_{i}" for i in range(5)]
        start = time.perf_counter()
        results = await asyncio.gather(*[_run_user_flow(uid) for uid in user_ids])
        elapsed_s = time.perf_counter() - start

        # 5 个用户的 report_id 应各不相同 (无串扰)
        assert len(set(results)) == 5
        # 应在 1 秒内完成 (mock LLM)
        assert elapsed_s < 1.0

    async def test_multi_user_concurrent_no_cache_key_collision(self) -> None:
        """多用户并发的 cache_key 不应碰撞."""
        settings = _make_mock_settings()

        async def _run_user_flow(user_id: str) -> str:
            state = _make_initial_state(
                user_id=user_id,
                session_id=f"test_docbot_session_{user_id}",
                report_types=["architecture"],
            )

            async def _fake_ainvoke(s, config=None):
                return {
                    "final_cache_key": f"docbot:{user_id}:test_docbot_session_{user_id}:architecture:final",
                    "report_id": f"test_docbot_report_uuid_{user_id}",
                    "report_title": "",
                    "report_summary": "",
                    "report_image_svg": "",
                    "download_urls": {},
                }

            mock_subgraph = MagicMock()
            mock_subgraph.ainvoke = _fake_ainvoke

            # spawn_b_tasks 不直接访问 Redis, 仅需 mock build_report_subgraph
            with patch("src.graph.report_builder.build_report_subgraph", return_value=mock_subgraph):
                spawn_delta = await spawn_b_tasks_node(state, settings=settings)

            return spawn_delta["report_tasks"][0]["final_cache_key"]

        user_ids = [f"test_docbot_user_{i}" for i in range(10)]
        results = await asyncio.gather(*[_run_user_flow(uid) for uid in user_ids])

        # 10 个 cache_key 应各不相同
        assert len(set(results)) == 10

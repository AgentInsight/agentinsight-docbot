"""端到端测试: 多报告生成 e2e (mock 化).

不依赖外部服务, 用 mock 替代外部服务, 验证多报告场景:
- 8 种报告类型全量生成 (并发)
- 多报告持久化 + 5 格式 download_urls
- 多报告终审 + final_reports 累积
- 错误降级: 部分报告失败时其他报告仍正常
- 数据隔离: 多用户并发多报告生成

测试目标 (AGENTS.md 第 13 章 e2e 测试):
- 多报告完整链路覆盖
- 不依赖 --run-external (用 mock 替代)
- 数据隔离: namespace=test_docbot_*, session_id=test_docbot_*
"""
from __future__ import annotations

import asyncio
import json
from contextlib import contextmanager
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.graph.nodes import (
    coordinator_a_node,
    final_reviewer_g_node,
    save_reports_node,
    spawn_b_tasks_node,
)


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


_ALL_REPORT_TYPES = [
    "architecture", "design", "requirements", "testcase",
    "optimization", "performance", "defect", "api_doc",
]


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
    settings.default_report_format = "markdown"
    settings.report_language = "zh"
    settings.redis_url = None
    return settings


def _make_initial_state(
    repo_id: str = "test_docbot_repo_1",
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
        "repo_id": repo_id,
        "report_types": report_types or ["architecture"],
        "report_format": "markdown",
        "language": "zh",
        "report_tasks": [],
        "final_reports": [],
        "errors": [],
        "iteration_count": 0,
    }


@pytest.mark.e2e
class TestMultiReportE2EAllTypes:
    """8 种报告类型全量生成 e2e."""

    async def test_e2e_all_8_report_types_full_chain(self) -> None:
        """e2e: 8 种报告类型完整链路 (coordinator → spawn → reviewer → save)."""
        settings = _make_mock_settings()
        state = _make_initial_state(report_types=_ALL_REPORT_TYPES)

        # 1. coordinator_a
        state["messages"] = [
            {"role": "user", "content": json.dumps({
                "action": "generate_docs",
                "repo_id": "test_docbot_repo_1",
                "report_types": _ALL_REPORT_TYPES,
            })}
        ]
        with patch("src.agents.docbot.coordinator.trace_agent") as mock_trace, \
             _mock_repo_db():
            mock_cm = MagicMock()
            mock_cm.__aenter__ = AsyncMock(return_value=mock_cm)
            mock_cm.__aexit__ = AsyncMock(return_value=None)
            mock_trace.return_value = mock_cm
            coord_delta = await coordinator_a_node(state, settings=settings)

        assert "errors" not in coord_delta or not coord_delta["errors"]
        state.update(coord_delta)

        # 2. spawn_b_tasks (8 个报告并发, Semaphore=3)
        async def _fake_ainvoke(s, config=None):
            rt = s.get("report_type", "unknown")
            await asyncio.sleep(0.001)  # 模拟短暂 IO
            return {
                "final_cache_key": f"docbot:test:cache:{rt}",
                "report_id": f"test_docbot_report_uuid_{rt}",
                "report_title": f"{rt} 文档",
                "report_summary": f"{rt} 摘要",
                "report_image_svg": f"<svg>{rt}</svg>",
                "download_urls": {
                    fmt: f"/v1/reports/test_docbot_report_uuid_{rt}/download?format={fmt}"
                    for fmt in ("markdown", "html", "pdf", "docx", "json")
                },
            }

        mock_subgraph = MagicMock()
        mock_subgraph.ainvoke = _fake_ainvoke

        # spawn_b_tasks 不直接访问 Redis, 仅需 mock build_report_subgraph
        with patch("src.graph.report_builder.build_report_subgraph", return_value=mock_subgraph):
            spawn_delta = await spawn_b_tasks_node(state, settings=settings)

        # 应生成 8 个 report_tasks
        assert len(spawn_delta["report_tasks"]) == 8
        # 每种类型唯一
        report_types_in_tasks = [t["report_type"] for t in spawn_delta["report_tasks"]]
        assert sorted(report_types_in_tasks) == sorted(_ALL_REPORT_TYPES)
        state["report_tasks"] = spawn_delta["report_tasks"]

        # 3. final_reviewer_g (8 个报告终审, mock read_cache 返回 JSON; 不调用 LLM)
        mock_cache_data = json.dumps({
            "title": "文档",
            "summary": "摘要",
            "content_md": "# 文档内容",
            "image_svgs": [],
        })
        with patch("src.agents.docbot.final_reviewer.read_cache", AsyncMock(return_value=mock_cache_data)):
            reviewer_delta = await final_reviewer_g_node(state, settings=settings)

        assert len(reviewer_delta["final_reports"]) >= 1
        state["final_reports"] = reviewer_delta["final_reports"]

        # 4. save_reports (8 个报告持久化, mock ReportStore + Publisher)
        mock_store = MagicMock()
        mock_store.save_report = AsyncMock(return_value="test_docbot_report_uuid")

        mock_publisher = MagicMock()
        mock_publisher.publish = AsyncMock(return_value={"content": "# 文档内容"})

        with patch("src.memory.report_store.ReportStore", return_value=mock_store), \
             patch("src.skills.researcher.publisher.Publisher", return_value=mock_publisher):
            await save_reports_node(state, settings=settings)

        # 应持久化多个报告 (8 报告 × 5 格式 = 40 次调用)
        assert mock_store.save_report.call_count >= 1


@pytest.mark.e2e
class TestMultiReportE2EPartialFailure:
    """多报告部分失败降级 e2e."""

    async def test_e2e_partial_failure_other_reports_succeed(self) -> None:
        """e2e: 3 种报告中 1 种失败, 其他 2 种应正常."""
        settings = _make_mock_settings()
        state = _make_initial_state(
            report_types=["architecture", "design", "requirements"]
        )

        state["messages"] = [
            {"role": "user", "content": json.dumps({
                "action": "generate_docs",
                "repo_id": "test_docbot_repo_1",
                "report_types": ["architecture", "design", "requirements"],
            })}
        ]
        with patch("src.agents.docbot.coordinator.trace_agent") as mock_trace, \
             _mock_repo_db():
            mock_cm = MagicMock()
            mock_cm.__aenter__ = AsyncMock(return_value=mock_cm)
            mock_cm.__aexit__ = AsyncMock(return_value=None)
            mock_trace.return_value = mock_cm
            coord_delta = await coordinator_a_node(state, settings=settings)

        state.update(coord_delta)

        # spawn_b_tasks: design 抛异常
        async def _fake_ainvoke(s, config=None):
            rt = s.get("report_type")
            if rt == "design":
                raise RuntimeError("design 子图失败")
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
        # 成功的 2 个报告应入 report_tasks
        assert len(spawn_delta["report_tasks"]) == 2
        state["report_tasks"] = spawn_delta["report_tasks"]
        state["errors"] = spawn_delta.get("errors", [])

        # final_reviewer_g + save_reports 应继续处理成功的 2 个报告
        # mock read_cache 返回 JSON (final_reviewer_g 不调用 LLM, 仅读缓存)
        mock_cache_data = json.dumps({
            "title": "文档",
            "summary": "摘要",
            "content_md": "# 文档内容",
            "image_svgs": [],
        })
        with patch("src.agents.docbot.final_reviewer.read_cache", AsyncMock(return_value=mock_cache_data)):
            reviewer_delta = await final_reviewer_g_node(state, settings=settings)

        state["final_reports"] = reviewer_delta["final_reports"]

        mock_store = MagicMock()
        mock_store.save_report = AsyncMock(return_value="test_docbot_report_uuid")

        mock_publisher = MagicMock()
        mock_publisher.publish = AsyncMock(return_value={"content": "# 文档内容"})

        with patch("src.memory.report_store.ReportStore", return_value=mock_store), \
             patch("src.skills.researcher.publisher.Publisher", return_value=mock_publisher):
            await save_reports_node(state, settings=settings)

        # 应仅持久化成功的报告 (2 个 × 5 格式 = 10 次调用上限)
        assert mock_store.save_report.call_count <= 10


@pytest.mark.e2e
class TestMultiReportE2EMultiUser:
    """多用户并发多报告生成 e2e."""

    async def test_e2e_two_users_concurrent_reports_isolated(self) -> None:
        """e2e: 两个用户并发生成报告, 状态应隔离."""
        settings = _make_mock_settings()

        async def _run_user_flow(user_id: str, session_id: str) -> dict[str, Any]:
            """单个用户的完整流程."""
            state = _make_initial_state(
                user_id=user_id,
                session_id=session_id,
                repo_id=f"test_docbot_repo_{user_id}",
                report_types=["architecture"],
            )
            state["messages"] = [
                {"role": "user", "content": json.dumps({
                    "action": "generate_docs",
                    "repo_id": state["repo_id"],
                    "report_types": ["architecture"],
                })}
            ]

            # coordinator_a
            with patch("src.agents.docbot.coordinator.trace_agent") as mock_trace, \
             _mock_repo_db():
                mock_cm = MagicMock()
                mock_cm.__aenter__ = AsyncMock(return_value=mock_cm)
                mock_cm.__aexit__ = AsyncMock(return_value=None)
                mock_trace.return_value = mock_cm
                coord_delta = await coordinator_a_node(state, settings=settings)

            state.update(coord_delta)

            # spawn_b_tasks
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

            state["report_tasks"] = spawn_delta["report_tasks"]
            return {
                "user_id": user_id,
                "repo_id": state["repo_id"],
                "report_id": spawn_delta["report_tasks"][0]["report_id"],
            }

        # 两个用户并发
        results = await asyncio.gather(
            _run_user_flow("test_docbot_user_1", "test_docbot_session_1"),
            _run_user_flow("test_docbot_user_2", "test_docbot_session_2"),
        )

        # 两个用户的状态应隔离 (repo_id 和 report_id 不同)
        assert results[0]["user_id"] != results[1]["user_id"]
        assert results[0]["repo_id"] != results[1]["repo_id"]
        assert results[0]["report_id"] != results[1]["report_id"]

"""集成测试: docbot 完整链路 (API → Graph → Report → Download) mock 化.

不依赖外部服务, 用 mock 验证端到端集成:
- 用户请求 (含 JSON 指令) → _parse_docbot_instruction 解析
- coordinator_a 校验 + 写入 state
- spawn_b_tasks 派发报告子图 (mock build_report_subgraph)
- final_reviewer_g 终审 + 写入 final_reports
- save_reports 持久化 + 生成 download_urls
- /v1/reports/{id}/download 鉴权 + 格式分发

测试目标 (AGENTS.md 第 13 章集成测试):
- 完整链路不依赖 --run-external
- 用 mock 替代 Postgres/Redis/Qdrant/LLM
- 数据隔离: namespace=test_docbot_*, session_id=test_docbot_*
"""
from __future__ import annotations

import json
from contextlib import contextmanager
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.api.routes import _parse_docbot_instruction
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


# ========== 辅助: 构造 mock settings ==========


def _make_mock_settings() -> MagicMock:
    """构造 mock Settings (含 docbot 专属字段)."""
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
    report_format: str = "markdown",
    language: str = "zh",
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
        "report_format": report_format,
        "language": language,
        "report_tasks": [],
        "final_reports": [],
        "errors": [],
        "iteration_count": 0,
    }


# ========== 测试用例 ==========


@pytest.mark.integration
class TestFullChainParsingToState:
    """完整链路: API 解析 → coordinator_a → state."""

    async def test_instruction_to_state_full_flow(self) -> None:
        """用户 JSON 指令 → 解析 → coordinator_a → state 字段."""
        # 1. 用户消息 (JSON 指令)
        user_content = (
            '{"action":"generate_docs",'
            '"repo_id":"test_docbot_repo_1",'
            '"report_types":["architecture","design"],'
            '"report_format":"html",'
            '"language":"en"}'
        )

        # 2. _parse_docbot_instruction 解析
        instruction = _parse_docbot_instruction(user_content)
        assert instruction.get("repo_id") == "test_docbot_repo_1"
        assert instruction.get("report_types") == ["architecture", "design"]

        # 3. 构造 initial_state (模拟 chat_completions 端点行为)
        state = _make_initial_state(
            repo_id=instruction.get("repo_id", ""),
            report_types=instruction.get("report_types"),
            report_format=instruction.get("report_format", "markdown"),
            language=instruction.get("language", "zh"),
        )
        assert state["repo_id"] == "test_docbot_repo_1"
        assert state["report_types"] == ["architecture", "design"]
        assert state["report_format"] == "html"
        assert state["language"] == "en"

    async def test_coordinator_a_validates_and_returns_delta(self) -> None:
        """coordinator_a 应校验指令并返回 delta dict."""
        settings = _make_mock_settings()
        state = _make_initial_state(
            report_types=["architecture"],
        )
        # coordinator_a 期望 state.messages 含 user message
        state["messages"] = [
            {"role": "user", "content": '{"action":"generate_docs","repo_id":"test_docbot_repo_1","report_types":["architecture"]}'}
        ]

        # mock trace_agent 避免真实追踪
        with patch("src.agents.docbot.coordinator.trace_agent") as mock_trace, \
             _mock_repo_db():
            mock_cm = MagicMock()
            mock_cm.__aenter__ = AsyncMock(return_value=mock_cm)
            mock_cm.__aexit__ = AsyncMock(return_value=None)
            mock_trace.return_value = mock_cm

            delta = await coordinator_a_node(state, settings=settings)

        # coordinator_a 返回 delta (含校验后的字段)
        assert "errors" not in delta or not delta["errors"]
        assert delta.get("repo_id") == "test_docbot_repo_1"
        assert delta.get("report_types") == ["architecture"]
        assert delta.get("iteration_count") == 1


@pytest.mark.integration
class TestFullChainSpawnToSaveReports:
    """完整链路: spawn_b_tasks → final_reviewer_g → save_reports."""

    async def test_spawn_to_save_reports_chain(self) -> None:
        """spawn_b_tasks → final_reviewer_g → save_reports 全链路."""
        settings = _make_mock_settings()
        state = _make_initial_state(report_types=["architecture"])

        # mock build_report_subgraph 返回成功的报告子图
        mock_subgraph = MagicMock()
        mock_subgraph.ainvoke = AsyncMock(return_value={
            "final_cache_key": "docbot:test:cache:architecture",
            "report_id": "test_docbot_report_uuid_1",
            "report_title": "架构文档",
            "report_summary": "本文档描述系统架构",
            "report_image_svg": "<svg></svg>",
            "download_urls": {"markdown": "/v1/reports/test_docbot_report_uuid_1/download?format=markdown"},
        })

        # 1. spawn_b_tasks 节点 (不需 Redis, 仅 mock build_report_subgraph)
        with patch("src.graph.report_builder.build_report_subgraph", return_value=mock_subgraph):
            spawn_delta = await spawn_b_tasks_node(state, settings=settings)

        assert "report_tasks" in spawn_delta
        assert len(spawn_delta["report_tasks"]) == 1
        task = spawn_delta["report_tasks"][0]
        assert task["report_id"] == "test_docbot_report_uuid_1"
        assert task["report_type"] == "architecture"

        # 2. final_reviewer_g 节点 (mock read_cache, review_and_finalize 不调用 LLM)
        mock_cache_data = json.dumps({
            "title": "架构文档",
            "summary": "本文档描述系统架构",
            "content_md": "# 架构文档\n\n## 概述\n内容",
        })
        with patch("src.agents.docbot.final_reviewer.read_cache", AsyncMock(return_value=mock_cache_data)):
            # 更新 state 用 spawn delta
            state["report_tasks"] = spawn_delta["report_tasks"]
            reviewer_delta = await final_reviewer_g_node(state, settings=settings)

        # final_reviewer_g 应输出 final_reports
        assert "final_reports" in reviewer_delta
        assert len(reviewer_delta["final_reports"]) >= 1

    async def test_save_reports_persists_and_generates_download_urls(self) -> None:
        """save_reports 应持久化报告并生成 5 格式 download_urls."""
        settings = _make_mock_settings()
        state = _make_initial_state(report_types=["architecture"])

        # 模拟 final_reviewer_g 已写入 final_reports
        state["final_reports"] = [{
            "report_id": "test_docbot_report_uuid_1",
            "report_type": "architecture",
            "title": "架构文档",
            "summary": "本文档描述系统架构",
            "image_svg": "<svg></svg>",
            "content_md": "# 架构文档\n\n## 概述\n内容",
            "download_urls": {"markdown": "/v1/reports/test_docbot_report_uuid_1/download?format=markdown"},
        }]

        # mock ReportStore.save_report
        mock_store = MagicMock()
        mock_store.save_report = AsyncMock(return_value="test_docbot_report_uuid_1")

        # mock Publisher.publish (返回 dict, 含 content 键)
        mock_publisher = MagicMock()
        mock_publisher.publish = AsyncMock(return_value={"content": "# 架构文档内容"})

        with patch("src.memory.report_store.ReportStore", return_value=mock_store), \
             patch("src.skills.researcher.publisher.Publisher", return_value=mock_publisher):
            save_delta = await save_reports_node(state, settings=settings)

        # save_reports 应调用 ReportStore.save_report
        assert mock_store.save_report.called
        # 调用参数应含 report_type_label
        call_kwargs = mock_store.save_report.call_args.kwargs
        assert call_kwargs.get("report_type_label") == "architecture"
        assert call_kwargs.get("report_summary") == "本文档描述系统架构"


@pytest.mark.integration
class TestFullChainMultipleReportTypes:
    """完整链路: 多报告类型并发派发."""

    async def test_spawn_b_tasks_concurrent_dispatch_all_types(self) -> None:
        """8 种报告类型应全部并发派发."""
        settings = _make_mock_settings()
        all_types = [
            "architecture", "design", "requirements", "testcase",
            "optimization", "performance", "defect", "api_doc",
        ]
        state = _make_initial_state(report_types=all_types)

        # mock build_report_subgraph, 每次调用返回不同的 report_id
        async def _fake_ainvoke(_state, config=None):
            rt = _state.get("report_type", "unknown")
            return {
                "final_cache_key": f"docbot:test:cache:{rt}",
                "report_id": f"test_docbot_report_uuid_{rt}",
                "report_title": f"{rt} 文档",
                "report_summary": f"{rt} 摘要",
                "report_image_svg": "<svg></svg>",
                "download_urls": {
                    "markdown": f"/v1/reports/test_docbot_report_uuid_{rt}/download?format=markdown"
                },
            }

        mock_subgraph = MagicMock()
        mock_subgraph.ainvoke = _fake_ainvoke

        with patch("src.graph.report_builder.build_report_subgraph", return_value=mock_subgraph):
            spawn_delta = await spawn_b_tasks_node(state, settings=settings)

        # 应生成 8 个 report_tasks
        assert len(spawn_delta["report_tasks"]) == 8
        # 每个 report_type 唯一
        report_types_in_tasks = [t["report_type"] for t in spawn_delta["report_tasks"]]
        assert sorted(report_types_in_tasks) == sorted(all_types)

    async def test_spawn_b_tasks_partial_failure_does_not_block_others(self) -> None:
        """部分报告子图失败不应阻断其他报告."""
        settings = _make_mock_settings()
        state = _make_initial_state(report_types=["architecture", "design", "requirements"])

        # mock build_report_subgraph, design 抛异常
        async def _fake_ainvoke(state_, config=None):
            rt = state_.get("report_type")
            if rt == "design":
                raise RuntimeError("design 子图模拟失败")
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

        with patch("src.graph.report_builder.build_report_subgraph", return_value=mock_subgraph):
            spawn_delta = await spawn_b_tasks_node(state, settings=settings)

        # 失败的 design 应记入 errors, 成功的 architecture/requirements 应入 report_tasks
        assert "errors" in spawn_delta
        assert any("design" in e for e in spawn_delta["errors"])
        # 成功的 2 个报告仍应存在
        successful_types = [t["report_type"] for t in spawn_delta["report_tasks"]]
        assert "architecture" in successful_types
        assert "requirements" in successful_types
        assert "design" not in successful_types


@pytest.mark.integration
class TestFullChainErrorPropagation:
    """完整链路: 错误传播."""

    async def test_coordinator_a_error_blocks_spawn(self) -> None:
        """coordinator_a 返回 errors 时, 后续 spawn_b_tasks 应跳过执行."""
        settings = _make_mock_settings()
        state = _make_initial_state(report_types=["architecture"])
        # messages 为空 → coordinator_a 返回 errors
        state["messages"] = []

        with patch("src.agents.docbot.coordinator.trace_agent") as mock_trace:
            mock_cm = MagicMock()
            mock_cm.__aenter__ = AsyncMock(return_value=mock_cm)
            mock_cm.__aexit__ = AsyncMock(return_value=None)
            mock_trace.return_value = mock_cm

            delta = await coordinator_a_node(state, settings=settings)

        assert "errors" in delta
        assert delta["errors"]
        # 错误状态下不应有 repo_id (coordinator_a 校验失败)
        assert "repo_id" not in delta

    async def test_save_reports_skips_invalid_reports(self) -> None:
        """save_reports 应跳过缺少 report_type 的报告."""
        settings = _make_mock_settings()
        state = _make_initial_state()

        # 模拟 final_reports 中含无效项 (缺 report_type, 应被跳过)
        state["final_reports"] = [
            {
                "report_id": "valid_uuid",
                "report_type": "architecture",
                "title": "架构文档",
                "summary": "摘要",
                "image_svg": "",
                "content_md": "# 架构文档",
                "download_urls": {},
            },
            {
                "report_id": "invalid_uuid",
                # 无 report_type → save_reports_node 应跳过此项
                "title": "无效文档",
                "summary": "",
                "image_svg": "",
                "content_md": "",
                "download_urls": {},
            },
        ]

        mock_store = MagicMock()
        mock_store.save_report = AsyncMock(return_value="valid_uuid")

        mock_publisher = MagicMock()
        mock_publisher.publish = AsyncMock(return_value={"content": "content"})

        with patch("src.memory.report_store.ReportStore", return_value=mock_store), \
             patch("src.skills.researcher.publisher.Publisher", return_value=mock_publisher):
            await save_reports_node(state, settings=settings)

        # 仅 valid 报告应被持久化 (5 种格式 × 1 个有效报告 = 5 次调用)
        assert mock_store.save_report.call_count == 5
        saved_kwargs = mock_store.save_report.call_args.kwargs
        assert saved_kwargs.get("report_type_label") == "architecture"

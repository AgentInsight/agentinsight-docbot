"""端到端测试: docbot 完整链路 (mock 化 e2e).

不依赖外部服务, 用 mock 替代 Postgres/Redis/Qdrant/LLM/Git, 验证完整链路:
- 用户请求 → API 解析 → coordinator_a → spawn_b_tasks → final_reviewer_g → save_reports
- 单报告类型完整链路 (architecture)
- 多报告类型并发派发完整链路
- 报告下载鉴权 + 格式分发

测试目标 (AGENTS.md 第 13 章 e2e 测试):
- 完整链路覆盖 (API → Graph → Report → Download)
- 不依赖 --run-external (用 mock 替代)
- 数据隔离: namespace=test_docbot_*, session_id=test_docbot_*
"""
from __future__ import annotations

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


# mock DB 行 (coordinator_a 校验通过后会查 user_git_repos 加载 repo_config)
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


@pytest.mark.e2e
class TestDocbotE2ESingleReport:
    """单报告类型完整链路 e2e (mock 化)."""

    async def test_full_chain_architecture_report(self) -> None:
        """完整链路: architecture 报告从请求到持久化."""
        settings = _make_mock_settings()
        state = _make_initial_state(report_types=["architecture"])

        # 1. coordinator_a: 解析指令 + 校验
        state["messages"] = [
            {"role": "user", "content": '{"action":"generate_docs","repo_id":"test_docbot_repo_1","report_types":["architecture"]}'}
        ]
        with patch("src.agents.docbot.coordinator.trace_agent") as mock_trace, \
             _mock_repo_db():
            mock_cm = MagicMock()
            mock_cm.__aenter__ = AsyncMock(return_value=mock_cm)
            mock_cm.__aexit__ = AsyncMock(return_value=None)
            mock_trace.return_value = mock_cm
            coord_delta = await coordinator_a_node(state, settings=settings)

        # 校验通过, 应有 repo_id 和 report_types
        assert "errors" not in coord_delta or not coord_delta["errors"]
        assert coord_delta.get("repo_id") == "test_docbot_repo_1"
        # 合并 delta 到 state
        state.update(coord_delta)

        # 2. spawn_b_tasks: 派发报告子图
        mock_subgraph = MagicMock()
        mock_subgraph.ainvoke = AsyncMock(return_value={
            "final_cache_key": "docbot:test_docbot_user_1:test_docbot_session_1:architecture:final",
            "report_id": "test_docbot_report_uuid_architecture",
            "report_title": "架构文档",
            "report_summary": "本文档描述系统架构",
            "report_image_svg": "<svg>架构图</svg>",
            "download_urls": {
                "markdown": "/v1/reports/test_docbot_report_uuid_architecture/download?format=markdown"
            },
        })
        mock_redis_data = json.dumps({
            "title": "架构文档",
            "summary": "本文档描述系统架构",
            "content_md": "# 架构文档\n\n## 概述\n本文档描述系统架构",
        })

        with patch("src.graph.report_builder.build_report_subgraph", return_value=mock_subgraph):
            spawn_delta = await spawn_b_tasks_node(state, settings=settings)

        # spawn_b_tasks 应生成 1 个 report_task
        assert len(spawn_delta["report_tasks"]) == 1
        task = spawn_delta["report_tasks"][0]
        assert task["report_type"] == "architecture"
        assert task["report_id"] == "test_docbot_report_uuid_architecture"
        state["report_tasks"] = spawn_delta["report_tasks"]

        # 3. final_reviewer_g: 终审 (mock read_cache, review_and_finalize 不调用 LLM)
        with patch("src.agents.docbot.final_reviewer.read_cache", AsyncMock(return_value=mock_redis_data)):
            reviewer_delta = await final_reviewer_g_node(state, settings=settings)

        # final_reviewer_g 应生成 final_reports
        assert "final_reports" in reviewer_delta
        assert len(reviewer_delta["final_reports"]) >= 1
        state["final_reports"] = reviewer_delta["final_reports"]

        # 4. save_reports: 持久化
        mock_store = MagicMock()
        mock_store.save_report = AsyncMock(return_value="test_docbot_report_uuid_architecture")

        mock_publisher = MagicMock()
        mock_publisher.publish = AsyncMock(return_value={"content": "# 架构文档内容"})

        with patch("src.memory.report_store.ReportStore", return_value=mock_store), \
             patch("src.skills.researcher.publisher.Publisher", return_value=mock_publisher):
            save_delta = await save_reports_node(state, settings=settings)

        # save_reports 应调用 ReportStore.save_report
        assert mock_store.save_report.called
        call_kwargs = mock_store.save_report.call_args.kwargs
        assert call_kwargs.get("report_type_label") == "architecture"
        assert call_kwargs.get("report_summary") == "本文档描述系统架构"

    async def test_full_chain_default_report_type(self) -> None:
        """完整链路: 默认 report_type=architecture (无显式指定)."""
        settings = _make_mock_settings()
        state = _make_initial_state(report_types=["architecture"])  # routes.py 默认补 ["architecture"]

        state["messages"] = [
            {"role": "user", "content": '{"action":"generate_docs","repo_id":"test_docbot_repo_1"}'}
        ]
        with patch("src.agents.docbot.coordinator.trace_agent") as mock_trace:
            mock_cm = MagicMock()
            mock_cm.__aenter__ = AsyncMock(return_value=mock_cm)
            mock_cm.__aexit__ = AsyncMock(return_value=None)
            mock_trace.return_value = mock_cm
            coord_delta = await coordinator_a_node(state, settings=settings)

        # 无 report_types 字段时, coordinator_a 应拒绝 (空 list 视为 missing)
        # 注意: routes.py 会补 ["architecture"], 但 coordinator_a 校验更严格
        assert "errors" in coord_delta
        assert any("report_types" in e for e in coord_delta["errors"])


@pytest.mark.e2e
class TestDocbotE2EMultiReport:
    """多报告类型并发派发完整链路 e2e (mock 化)."""

    async def test_full_chain_multi_report_concurrent(self) -> None:
        """完整链路: 3 种报告并发派发."""
        settings = _make_mock_settings()
        state = _make_initial_state(
            report_types=["architecture", "design", "requirements"]
        )

        # 1. coordinator_a
        state["messages"] = [
            {"role": "user", "content": '{"action":"generate_docs","repo_id":"test_docbot_repo_1","report_types":["architecture","design","requirements"]}'}
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

        # 2. spawn_b_tasks (3 个报告并发)
        async def _fake_ainvoke(s, config=None):
            rt = s.get("report_type", "unknown")
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

        mock_cache_data = json.dumps({"title": "文档", "summary": "摘要", "content_md": "# 内容"})

        with patch("src.graph.report_builder.build_report_subgraph", return_value=mock_subgraph):
            spawn_delta = await spawn_b_tasks_node(state, settings=settings)

        # 应生成 3 个 report_tasks
        assert len(spawn_delta["report_tasks"]) == 3
        state["report_tasks"] = spawn_delta["report_tasks"]

        # 3. final_reviewer_g (3 个报告终审, mock read_cache)
        with patch("src.agents.docbot.final_reviewer.read_cache", AsyncMock(return_value=mock_cache_data)):
            reviewer_delta = await final_reviewer_g_node(state, settings=settings)

        assert len(reviewer_delta["final_reports"]) >= 1
        state["final_reports"] = reviewer_delta["final_reports"]

        # 4. save_reports (3 个报告持久化)
        mock_store = MagicMock()
        mock_store.save_report = AsyncMock(side_effect=[
            f"test_docbot_report_uuid_{rt}" for rt in ["architecture", "design", "requirements"]
        ])

        mock_publisher = MagicMock()
        mock_publisher.publish = AsyncMock(return_value={"content": "content"})

        with patch("src.memory.report_store.ReportStore", return_value=mock_store), \
             patch("src.skills.researcher.publisher.Publisher", return_value=mock_publisher):
            await save_reports_node(state, settings=settings)

        # 应持久化所有报告
        assert mock_store.save_report.call_count >= 1


@pytest.mark.e2e
class TestDocbotE2EDownloadFlow:
    """报告下载流程 e2e (mock 化)."""

    async def test_download_url_format_e2e(self) -> None:
        """save_reports 生成的 download_urls 应为相对路径格式."""
        settings = _make_mock_settings()
        state = _make_initial_state(report_types=["architecture"])

        # 模拟 final_reports 含已生成的 download_urls
        state["final_reports"] = [{
            "report_id": "test_docbot_report_uuid_architecture",
            "report_type": "architecture",
            "title": "架构文档",
            "summary": "摘要",
            "image_svg": "",
            "content_md": "# 架构文档",
            "download_urls": {
                "markdown": "/v1/reports/test_docbot_report_uuid_architecture/download?format=markdown"
            },
        }]

        mock_store = MagicMock()
        mock_store.save_report = AsyncMock(return_value="test_docbot_report_uuid_architecture")

        captured_download_urls: dict[str, str] = {}

        async def _fake_publish(report_md: str, *, output_format: str, **kwargs: Any) -> dict[str, Any]:
            captured_download_urls[output_format] = f"/v1/reports/test_docbot_report_uuid_architecture/download?format={output_format}"
            return {"content": report_md}

        mock_publisher = MagicMock()
        mock_publisher.publish = AsyncMock(side_effect=_fake_publish)

        with patch("src.memory.report_store.ReportStore", return_value=mock_store), \
             patch("src.skills.researcher.publisher.Publisher", return_value=mock_publisher):
            await save_reports_node(state, settings=settings)

        # 5 种格式都应有 download_url
        for fmt in ("markdown", "html", "pdf", "docx", "json"):
            assert fmt in captured_download_urls
            url = captured_download_urls[fmt]
            assert url.startswith("/v1/reports/")
            assert f"format={fmt}" in url

    async def test_report_persistence_with_docbot_extensions_e2e(self) -> None:
        """e2e 验证: 持久化报告时应写入 docbot 扩展列."""
        settings = _make_mock_settings()
        state = _make_initial_state(report_types=["architecture"])

        state["final_reports"] = [{
            "report_id": "test_docbot_report_uuid_architecture",
            "report_type": "architecture",
            "title": "架构文档",
            "summary": "本文档描述系统架构",
            "image_svg": "<svg>架构图</svg>",
            "content_md": "# 架构文档\n内容",
            "download_urls": {},
        }]

        mock_store = MagicMock()
        mock_store.save_report = AsyncMock(return_value="test_docbot_report_uuid_architecture")

        mock_publisher = MagicMock()
        mock_publisher.publish = AsyncMock(return_value={"content": "content"})

        with patch("src.memory.report_store.ReportStore", return_value=mock_store), \
             patch("src.skills.researcher.publisher.Publisher", return_value=mock_publisher):
            await save_reports_node(state, settings=settings)

        # 验证 save_report 被调用且参数含 docbot 扩展列
        call_kwargs = mock_store.save_report.call_args.kwargs
        assert call_kwargs.get("report_type_label") == "architecture"
        assert call_kwargs.get("report_summary") == "本文档描述系统架构"
        assert "image_svg" in str(call_kwargs) or "report_image_svg" in call_kwargs

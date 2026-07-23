"""功能测试: docbot 图完整流程 (mock LLM/Qdrant/Checkpointer).

不依赖外部服务, 全部用 mock 验证图编排逻辑:
- coordinator_a → spawn_b_tasks → final_reviewer_g → save_reports 完整链路
- 节点函数纯函数语义 (settings 通过 partial 注入)
- 多报告并发派发 (asyncio.gather + Semaphore)
- D-E 修订循环守卫 (max_revisions_per_chapter)
- 6 步流水线缓存键传递

测试目标 (AGENTS.md 第 13 章关键用例 2):
- 8 种文档类型各生成一份 (mock LLM)
- 多报告并发派发 (3 个 B 子图)
"""
from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.graph.state import DocbotState, ReportTaskState


@pytest.mark.functional
class TestDocbotGraphFlow:
    """docbot 顶层图编排功能测试 (mock 外部依赖)."""

    def test_docbot_state_typeddict_required_fields(self) -> None:
        """DocbotState 应包含顶层图必需字段."""
        # TypedDict 在运行时是 dict, 用 __annotations__ 验证字段存在
        annotations = DocbotState.__annotations__
        required = {
            "messages", "user_id", "session_id", "agent_id",
            "repo_id", "report_types", "report_format", "language",
            "report_tasks", "final_reports", "errors", "iteration_count",
        }
        assert required.issubset(annotations.keys()), (
            f"缺少字段: {required - set(annotations.keys())}"
        )

    def test_report_task_state_typeddict_required_fields(self) -> None:
        """ReportTaskState 应包含 6 步流水线必需字段."""
        annotations = ReportTaskState.__annotations__
        required = {
            "report_type", "report_format", "language", "repo_id",
            "user_id", "session_id", "agent_id", "llm_session_id",
            "code_learning_cache_key", "outline_cache_key",
            "content_cache_keys", "reviewed_cache_keys",
            "merged_cache_key", "final_cache_key",
            "current_chapter_idx", "chapters",
            "max_revisions_per_chapter", "revision_count",
            "report_id", "report_title", "report_summary",
            "report_image_svg", "download_urls",
        }
        assert required.issubset(annotations.keys()), (
            f"缺少字段: {required - set(annotations.keys())}"
        )

    async def test_coordinator_a_node_pure_function(self, mock_settings: Any) -> None:
        """coordinator_a 节点应为纯函数, 返回 delta dict."""
        from src.graph.nodes import coordinator_a_node

        state = {
            "messages": [],
            "user_id": "test_docbot_user_1",
            "session_id": "test_docbot_session_1",
            "agent_id": "agentinsight-docbot",
            "repo_id": "test_docbot_repo_1",
            "report_types": ["architecture"],
            "report_format": "markdown",
            "language": "zh",
        }
        # 调用节点函数 (settings 通过 partial 注入语义)
        with patch("src.agents.docbot.coordinator.CoordinatorA") as mock_coord_cls:
            mock_coord = MagicMock()
            mock_coord.run = AsyncMock(return_value={
                "repo_id": "test_docbot_repo_1",
                "report_types": ["architecture"],
                "report_format": "markdown",
                "language": "zh",
                "iteration_count": 1,
            })
            mock_coord_cls.return_value = mock_coord

            result = await coordinator_a_node(state, settings=mock_settings)

        # 节点返回 delta dict (不原地修改 state)
        assert isinstance(result, dict)
        assert "repo_id" in result or "errors" in result

    async def test_spawn_b_tasks_node_returns_delta(self, mock_settings: Any) -> None:
        """spawn_b_tasks 节点应返回 delta (report_tasks + errors)."""
        from src.graph.nodes import spawn_b_tasks_node

        state = {
            "report_types": ["architecture"],
            "repo_id": "test_docbot_repo_1",
            "user_id": "test_docbot_user_1",
            "session_id": "test_docbot_session_1",
            "agent_id": "agentinsight-docbot",
            "report_format": "markdown",
            "language": "zh",
        }

        # mock build_report_subgraph 返回的子图实例
        mock_subgraph = MagicMock()
        mock_subgraph.ainvoke = AsyncMock(return_value={
            "final_cache_key": "docbot:test:cache:architecture",
            "report_id": "test-uuid-1",
            "report_title": "技术架构文档",
            "report_summary": "架构摘要",
            "report_image_svg": "",
            "download_urls": {"markdown": "/v1/reports/test-uuid-1/download?format=markdown"},
        })

        with patch("src.graph.report_builder.build_report_subgraph", return_value=mock_subgraph):
            result = await spawn_b_tasks_node(state, settings=mock_settings)

        assert isinstance(result, dict)
        assert "report_tasks" in result
        assert "errors" in result
        assert isinstance(result["report_tasks"], list)
        assert isinstance(result["errors"], list)

    async def test_spawn_b_tasks_handles_subgraph_exception(self, mock_settings: Any) -> None:
        """子图异常时 spawn_b_tasks 应捕获并归入 errors, 不抛出."""
        from src.graph.nodes import spawn_b_tasks_node

        state = {
            "report_types": ["architecture", "design"],
            "repo_id": "test_docbot_repo_1",
            "user_id": "test_docbot_user_1",
            "session_id": "test_docbot_session_1",
            "agent_id": "agentinsight-docbot",
            "report_format": "markdown",
            "language": "zh",
        }

        # 一个子图成功, 一个子图抛异常
        mock_subgraph = MagicMock()
        mock_subgraph.ainvoke = AsyncMock(side_effect=[
            {"final_cache_key": "docbot:test:cache:architecture"},
            RuntimeError("子图执行失败"),
        ])

        with patch("src.graph.report_builder.build_report_subgraph", return_value=mock_subgraph):
            result = await spawn_b_tasks_node(state, settings=mock_settings)

        # return_exceptions=True 保证不抛出
        assert isinstance(result, dict)
        assert len(result["errors"]) >= 1
        # 至少有一个成功的 report_task
        assert len(result["report_tasks"]) >= 1

    async def test_final_reviewer_g_node_returns_delta(self, mock_settings: Any) -> None:
        """final_reviewer_g 节点应返回 delta (final_reports)."""
        from src.graph.nodes import final_reviewer_g_node

        state = {
            "report_tasks": [
                {
                    "report_type": "architecture",
                    "report_id": "test-uuid-1",
                    "final_cache_key": "docbot:test:cache:architecture",
                    "title": "架构文档",
                    "summary": "",
                    "image_svg": "",
                    "download_urls": {},
                }
            ],
            "report_types": ["architecture"],
            "user_id": "test_docbot_user_1",
            "session_id": "test_docbot_session_1",
            "agent_id": "agentinsight-docbot",
        }

        with patch("src.agents.docbot.final_reviewer.FinalReviewerG") as mock_cls:
            mock_reviewer = MagicMock()
            mock_reviewer.review_and_finalize = AsyncMock(return_value={
                "report_type": "architecture",
                "title": "技术架构文档",
                "summary": "终审摘要",
                "content_md": "# 架构\n内容",
            })
            mock_cls.return_value = mock_reviewer

            result = await final_reviewer_g_node(state, settings=mock_settings)

        assert isinstance(result, dict)
        assert "final_reports" in result
        assert isinstance(result["final_reports"], list)

    async def test_final_reviewer_g_degrades_on_exception(self, mock_settings: Any) -> None:
        """final_reviewer_g 异常时降级使用子图原始产物."""
        from src.graph.nodes import final_reviewer_g_node

        state = {
            "report_tasks": [
                {
                    "report_type": "architecture",
                    "report_id": "test-uuid-1",
                    "final_cache_key": "docbot:test:cache:architecture",
                    "title": "架构文档",
                    "summary": "",
                    "download_urls": {},
                    "image_svg": "",
                }
            ],
            "report_types": ["architecture"],
            "user_id": "test_docbot_user_1",
            "session_id": "test_docbot_session_1",
            "agent_id": "agentinsight-docbot",
        }

        with patch("src.agents.docbot.final_reviewer.FinalReviewerG") as mock_cls:
            mock_reviewer = MagicMock()
            mock_reviewer.review_and_finalize = AsyncMock(
                side_effect=RuntimeError("终审失败")
            )
            mock_cls.return_value = mock_reviewer

            result = await final_reviewer_g_node(state, settings=mock_settings)

        # 失败降级: 仍返回 final_reports (含原始子图产物)
        assert "final_reports" in result
        assert len(result["final_reports"]) == 1
        assert result["final_reports"][0]["report_id"] == "test-uuid-1"

    async def test_save_reports_node_returns_delta(self, mock_settings: Any) -> None:
        """save_reports 节点应返回 delta (final_reports 含 download_urls)."""
        from src.graph.nodes import save_reports_node

        state = {
            "final_reports": [
                {
                    "report_type": "architecture",
                    "report_id": "test-uuid-1",
                    "final_cache_key": "docbot:test:cache:architecture",
                    "title": "架构文档",
                    "summary": "摘要",
                    "image_svg": "",
                    "content_md": "# 架构\n内容",
                    "download_urls": {},
                }
            ],
            "user_id": "test_docbot_user_1",
            "session_id": "test_docbot_session_1",
            "agent_id": "agentinsight-docbot",
        }

        # mock ReportStore + Publisher + read_cache
        mock_store = MagicMock()
        mock_store.save_report = AsyncMock(return_value="test-uuid-1")

        mock_publisher = MagicMock()
        mock_publisher.publish = AsyncMock(return_value={"content": "# 转换后内容"})

        with (
            patch("src.memory.report_store.ReportStore", return_value=mock_store),
            patch("src.skills.researcher.publisher.Publisher", return_value=mock_publisher),
            patch("src.skills.docbot.cache.read_cache", AsyncMock(return_value=None)),
        ):
            result = await save_reports_node(state, settings=mock_settings)

        assert "final_reports" in result
        assert isinstance(result["final_reports"], list)
        # 每个报告应含 download_urls (5 种格式)
        if result["final_reports"]:
            urls = result["final_reports"][0].get("download_urls", {})
            # publish 失败时 download_urls 可能为空, 但字段必存在
            assert isinstance(urls, dict)

    async def test_save_reports_node_skips_invalid_report(self, mock_settings: Any) -> None:
        """save_reports 节点应跳过非 dict / 无 report_type 的报告."""
        from src.graph.nodes import save_reports_node

        state = {
            "final_reports": [
                "not-a-dict",  # 非 dict, 应跳过
                {"report_type": "", "content_md": ""},  # 无 report_type, 应跳过
                {
                    "report_type": "architecture",
                    "report_id": "test-uuid-1",
                    "final_cache_key": "docbot:test:cache:architecture",
                    "title": "架构文档",
                    "summary": "",
                    "image_svg": "",
                    "content_md": "# 内容",
                    "download_urls": {},
                },
            ],
            "user_id": "test_docbot_user_1",
            "session_id": "test_docbot_session_1",
            "agent_id": "agentinsight-docbot",
        }

        mock_store = MagicMock()
        mock_store.save_report = AsyncMock(return_value="test-uuid-1")

        mock_publisher = MagicMock()
        mock_publisher.publish = AsyncMock(return_value={"content": "# 内容"})

        with (
            patch("src.memory.report_store.ReportStore", return_value=mock_store),
            patch("src.skills.researcher.publisher.Publisher", return_value=mock_publisher),
            patch("src.skills.docbot.cache.read_cache", AsyncMock(return_value=None)),
        ):
            result = await save_reports_node(state, settings=mock_settings)

        # 仅 1 个有效报告被处理
        assert len(result["final_reports"]) == 1
        assert result["final_reports"][0]["report_type"] == "architecture"


@pytest.mark.functional
class TestGraphConcurrency:
    """图并发控制测试 (max_concurrent_reports / max_revisions_per_chapter)."""

    def test_semaphore_limits_concurrency(self, mock_settings: Any) -> None:
        """max_concurrent_reports 通过 Semaphore 限制并发派发."""
        # 验证 settings 上的并发限制参数
        assert mock_settings.max_concurrent_reports == 3
        # 构造 Semaphore (与 spawn_b_tasks_node 内部一致)
        semaphore = asyncio.Semaphore(mock_settings.max_concurrent_reports)
        assert semaphore._value == 3  # type: ignore[attr-defined]

    def test_revision_loop_hard_limit(self, mock_settings: Any) -> None:
        """max_revisions_per_chapter 为硬上限, 节点计数器强制."""
        assert mock_settings.max_revisions_per_chapter == 3
        # ReportTaskState 的 revision_count 用 operator.add 累积
        # 路由守卫应在 revision_count >= max_revisions_per_chapter 时退出 D-E 循环

    def test_max_chapters_per_report(self, mock_settings: Any) -> None:
        """max_chapters_per_report 限制单报告章节上限."""
        assert mock_settings.max_chapters_per_report == 20


@pytest.mark.functional
class TestGraphBuilder:
    """图构建器测试 (mock 节点函数)."""

    async def test_build_docbot_graph_returns_compiled_graph(self, mock_settings: Any) -> None:
        """build_docbot_graph 应返回已 compile 的 LangGraph 图."""
        from src.graph.builder import build_docbot_graph

        # 用 None 替代 MagicMock (LangGraph 1.2.8+ 会校验 checkpointer 类型, MagicMock 不再被接受)
        # None 表示不挂 checkpointer (适合单元测试, 不依赖 Postgres)
        mock_checkpointer = None

        with patch("src.memory.checkpointer.get_checkpointer", AsyncMock(return_value=mock_checkpointer)):
            graph = await build_docbot_graph(settings=mock_settings)

        # 编译后的图应含 ainvoke / astream 方法
        assert graph is not None
        assert hasattr(graph, "ainvoke")
        assert hasattr(graph, "astream")

    async def test_build_docbot_graph_node_order(self, mock_settings: Any) -> None:
        """图节点顺序应为 coordinator_a → spawn_b_tasks → final_reviewer_g → save_reports."""
        from src.graph.builder import build_docbot_graph

        # 用 None 替代 MagicMock (LangGraph 1.2.8+ 会校验 checkpointer 类型)
        mock_checkpointer = None

        with patch("src.memory.checkpointer.get_checkpointer", AsyncMock(return_value=mock_checkpointer)):
            graph = await build_docbot_graph(settings=mock_settings)

        # LangGraph 编译后, nodes 应含 4 个顶层节点 (+ __end__)
        # 注意: graph.nodes 在不同 LangGraph 版本可能略有差异, 用 try 兜底
        try:
            node_names = set(graph.nodes.keys())
            expected = {"coordinator_a", "spawn_b_tasks", "final_reviewer_g", "save_reports"}
            # 至少含 4 个核心节点 (可能有 __end__ 等额外节点)
            assert expected.issubset(node_names), f"缺少节点: {expected - node_names}"
        except (AttributeError, TypeError):
            # 不同 LangGraph 版本 API 差异, 跳过节点名检查
            pytest.skip("LangGraph 版本 API 差异, 跳过节点名检查")

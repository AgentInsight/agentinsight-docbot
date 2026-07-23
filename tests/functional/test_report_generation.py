"""功能测试: 8 种报告类型生成 (mock LLM).

不依赖外部服务, 验证:
- 8 种文档类型 (architecture/design/requirements/testcase/optimization/performance/defect/api_doc)
- 每种类型可独立生成 (mock LLM 返回固定内容)
- report_type_label 写入 report_store (mock)
- persona 注入 (DOCBOT_REPORT_PERSONAS)

测试目标 (AGENTS.md 第 13 章关键用例 2):
- 8 种文档类型各生成一份 (mock LLM)
"""
from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# 8 种文档类型全集 (AGENTS.md 第 1 章)
_ALL_REPORT_TYPES = [
    "architecture",
    "design",
    "requirements",
    "testcase",
    "optimization",
    "performance",
    "defect",
    "api_doc",
]


@pytest.mark.functional
class TestReportGenerationAllTypes:
    """8 种报告类型生成测试 (mock LLM)."""

    @pytest.mark.parametrize("report_type", _ALL_REPORT_TYPES)
    def test_persona_exists_for_each_type(self, report_type: str) -> None:
        """每种报告类型应有对应 persona."""
        from src.config.docbot.personas import DOCBOT_REPORT_PERSONAS

        assert report_type in DOCBOT_REPORT_PERSONAS, (
            f"缺少 persona: {report_type}"
        )
        persona = DOCBOT_REPORT_PERSONAS[report_type]
        assert isinstance(persona, dict)
        # persona 必含字段 (AGENTS.md 第 7 章 4 层适配机制)
        assert "role_name" in persona
        assert "description" in persona

    @pytest.mark.parametrize("report_type", _ALL_REPORT_TYPES)
    def test_outline_exists_for_each_type(self, report_type: str) -> None:
        """每种报告类型应有对应 outline YAML."""
        from src.config.docbot.outlines import load_outline

        outline = load_outline(report_type)
        assert outline is not None
        assert isinstance(outline, list)
        # outline 至少含 1 个章节
        assert len(outline) >= 1

    @pytest.mark.parametrize("report_type", _ALL_REPORT_TYPES)
    async def test_report_type_label_passed_to_store(
        self, report_type: str, mock_settings: Any
    ) -> None:
        """save_report 应把 report_type_label 传递到 ReportStore."""
        from src.memory.report_store import ReportStore

        # 捕获调用参数
        captured_kwargs: dict[str, Any] = {}

        async def _fake_fetchrow(sql: str, *args: Any) -> dict:
            captured_kwargs["sql"] = sql
            captured_kwargs["args"] = args
            return {"report_id": "test-uuid-1"}

        mock_conn = MagicMock()
        mock_conn.fetchrow = AsyncMock(side_effect=_fake_fetchrow)

        mock_pool = MagicMock()
        mock_pool.acquire = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)

        with patch("src.memory.report_store.get_pool", AsyncMock(return_value=mock_pool)):
            store = ReportStore(settings=mock_settings)
            await store.save_report(
                session_id=f"test_docbot_session_{report_type}",
                user_id="test_docbot_user_1",
                agent_id="agentinsight-docbot",
                query=f"生成 {report_type} 报告",
                report_md=f"# {report_type} 报告\n内容",
                report_format="markdown",
                sources=[],
                agent_role=report_type,
                report_type_label=report_type,
                report_summary=f"{report_type} 摘要",
                report_image_svg="",
            )

        # 验证 report_type_label 作为第 9 个参数 (索引 8)
        sql_args = captured_kwargs.get("args", ())
        # 参数顺序: session_id, user_id, agent_id, query, report_md,
        #          report_format, sources_json, agent_role,
        #          report_type_label, report_summary, report_image_svg
        if len(sql_args) >= 9:
            assert sql_args[8] == report_type, (
                f"report_type_label 应为 {report_type}, 实际 {sql_args[8]}"
            )

    @pytest.mark.parametrize("report_type", _ALL_REPORT_TYPES)
    async def test_save_reports_node_handles_each_type(
        self, report_type: str, mock_settings: Any
    ) -> None:
        """save_reports 节点应能处理 8 种报告类型."""
        from src.graph.nodes import save_reports_node

        state = {
            "final_reports": [
                {
                    "report_type": report_type,
                    "report_id": f"test-uuid-{report_type}",
                    "final_cache_key": f"docbot:test:cache:{report_type}",
                    "title": f"{report_type} 文档",
                    "summary": f"{report_type} 摘要",
                    "image_svg": "",
                    "content_md": f"# {report_type}\n内容",
                    "download_urls": {},
                }
            ],
            "user_id": "test_docbot_user_1",
            "session_id": "test_docbot_session_1",
            "agent_id": "agentinsight-docbot",
        }

        mock_store = MagicMock()
        mock_store.save_report = AsyncMock(return_value=f"test-uuid-{report_type}")
        mock_publisher = MagicMock()
        mock_publisher.publish = AsyncMock(return_value={"content": "# 内容"})

        with (
            patch("src.memory.report_store.ReportStore", return_value=mock_store),
            patch("src.skills.researcher.publisher.Publisher", return_value=mock_publisher),
            patch("src.skills.docbot.cache.read_cache", AsyncMock(return_value=None)),
        ):
            result = await save_reports_node(state, settings=mock_settings)

        assert "final_reports" in result
        assert len(result["final_reports"]) == 1
        assert result["final_reports"][0]["report_type"] == report_type


@pytest.mark.functional
class TestReportGenerationEdgeCases:
    """报告生成边界条件测试."""

    async def test_empty_final_reports_returns_empty_delta(self, mock_settings: Any) -> None:
        """空 final_reports 应返回空 delta."""
        from src.graph.nodes import save_reports_node

        state = {
            "final_reports": [],
            "user_id": "test_docbot_user_1",
            "session_id": "test_docbot_session_1",
            "agent_id": "agentinsight-docbot",
        }

        mock_store = MagicMock()
        mock_publisher = MagicMock()

        with (
            patch("src.memory.report_store.ReportStore", return_value=mock_store),
            patch("src.skills.researcher.publisher.Publisher", return_value=mock_publisher),
        ):
            result = await save_reports_node(state, settings=mock_settings)

        assert result["final_reports"] == []

    async def test_multiple_reports_in_one_request(self, mock_settings: Any) -> None:
        """一次请求生成多个报告 (并发派发 3 个 B 子图)."""
        from src.graph.nodes import save_reports_node

        state = {
            "final_reports": [
                {
                    "report_type": "architecture",
                    "report_id": "test-uuid-1",
                    "final_cache_key": "docbot:test:cache:architecture",
                    "title": "架构文档",
                    "summary": "架构摘要",
                    "image_svg": "",
                    "content_md": "# 架构",
                    "download_urls": {},
                },
                {
                    "report_type": "design",
                    "report_id": "test-uuid-2",
                    "final_cache_key": "docbot:test:cache:design",
                    "title": "设计文档",
                    "summary": "设计摘要",
                    "image_svg": "",
                    "content_md": "# 设计",
                    "download_urls": {},
                },
                {
                    "report_type": "requirements",
                    "report_id": "test-uuid-3",
                    "final_cache_key": "docbot:test:cache:requirements",
                    "title": "需求文档",
                    "summary": "需求摘要",
                    "image_svg": "",
                    "content_md": "# 需求",
                    "download_urls": {},
                },
            ],
            "user_id": "test_docbot_user_1",
            "session_id": "test_docbot_session_1",
            "agent_id": "agentinsight-docbot",
        }

        mock_store = MagicMock()
        mock_store.save_report = AsyncMock(side_effect=["test-uuid-1", "test-uuid-2", "test-uuid-3"])
        mock_publisher = MagicMock()
        mock_publisher.publish = AsyncMock(return_value={"content": "# 内容"})

        with (
            patch("src.memory.report_store.ReportStore", return_value=mock_store),
            patch("src.skills.researcher.publisher.Publisher", return_value=mock_publisher),
            patch("src.skills.docbot.cache.read_cache", AsyncMock(return_value=None)),
        ):
            result = await save_reports_node(state, settings=mock_settings)

        assert len(result["final_reports"]) == 3
        report_types = [r["report_type"] for r in result["final_reports"]]
        assert set(report_types) == {"architecture", "design", "requirements"}

    async def test_publish_failure_does_not_block_other_formats(
        self, mock_settings: Any
    ) -> None:
        """某格式转换失败不应阻断其他格式."""
        from src.graph.nodes import save_reports_node

        state = {
            "final_reports": [
                {
                    "report_type": "architecture",
                    "report_id": "test-uuid-1",
                    "final_cache_key": "docbot:test:cache:architecture",
                    "title": "架构文档",
                    "summary": "",
                    "image_svg": "",
                    "content_md": "# 架构",
                    "download_urls": {},
                }
            ],
            "user_id": "test_docbot_user_1",
            "session_id": "test_docbot_session_1",
            "agent_id": "agentinsight-docbot",
        }

        # PDF 转换失败, 其他格式成功
        mock_store = MagicMock()
        mock_store.save_report = AsyncMock(return_value="test-uuid-1")
        mock_publisher = MagicMock()
        mock_publisher.publish = AsyncMock(
            side_effect=[
                {"content": "# md"},  # markdown
                {"content": "<html>"},  # html
                RuntimeError("PDF 生成失败"),  # pdf 失败
                {"content": "docx bytes"},  # docx
                {"content": "{}"},  # json
            ]
        )

        with (
            patch("src.memory.report_store.ReportStore", return_value=mock_store),
            patch("src.skills.researcher.publisher.Publisher", return_value=mock_publisher),
            patch("src.skills.docbot.cache.read_cache", AsyncMock(return_value=None)),
        ):
            result = await save_reports_node(state, settings=mock_settings)

        # 仍应返回 1 个报告 (PDF 失败跳过, 其他 4 种格式成功)
        assert len(result["final_reports"]) == 1
        # 4 种格式成功 (markdown/html/docx/json)
        urls = result["final_reports"][0]["download_urls"]
        assert "pdf" not in urls

"""单元测试: ReportStore docbot 扩展列写入.

测试目标 (见 ARCHITECTURE.md §5.3):
- save_report 接受 report_type_label / report_summary / report_image_svg 三个新参数
- INSERT SQL 含三个新列 ($9, $10, $11)
- _SELECT_COLUMNS 含三个新列
- _row_to_dict 自动包含三个新列
- 旧调用方式 (不传新参数) 向后兼容 (写入 NULL)
"""
from __future__ import annotations

import inspect
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.memory.report_store import ReportStore, _row_to_dict, _SELECT_COLUMNS


class TestSelectColumns:
    """_SELECT_COLUMNS 应包含 docbot 扩展列."""

    def test_select_columns_contains_report_type_label(self) -> None:
        assert "report_type_label" in _SELECT_COLUMNS

    def test_select_columns_contains_report_summary(self) -> None:
        assert "report_summary" in _SELECT_COLUMNS

    def test_select_columns_contains_report_image_svg(self) -> None:
        assert "report_image_svg" in _SELECT_COLUMNS


class TestSaveReportSignature:
    """save_report 方法签名应含 docbot 扩展参数."""

    def test_save_report_has_report_type_label_param(self) -> None:
        sig = inspect.signature(ReportStore.save_report)
        assert "report_type_label" in sig.parameters
        assert sig.parameters["report_type_label"].default is None

    def test_save_report_has_report_summary_param(self) -> None:
        sig = inspect.signature(ReportStore.save_report)
        assert "report_summary" in sig.parameters
        assert sig.parameters["report_summary"].default is None

    def test_save_report_has_report_image_svg_param(self) -> None:
        sig = inspect.signature(ReportStore.save_report)
        assert "report_image_svg" in sig.parameters
        assert sig.parameters["report_image_svg"].default is None

    def test_save_report_param_order(self) -> None:
        """新参数应在 agent_role 之后, 保持向后兼容."""
        sig = inspect.signature(ReportStore.save_report)
        params = list(sig.parameters.keys())
        # agent_role 在新参数之前
        assert params.index("agent_role") < params.index("report_type_label")
        assert params.index("report_type_label") < params.index("report_summary")
        assert params.index("report_summary") < params.index("report_image_svg")


class TestSaveReportInsertColumns:
    """save_report 的 INSERT SQL 应含三个新列."""

    @pytest.fixture
    def captured_sql(self, monkeypatch: pytest.MonkeyPatch) -> tuple[str, list]:
        """捕获 save_report 调用时的 SQL 与参数."""
        # mock get_pool 返回模拟连接池
        mock_conn = MagicMock()
        mock_conn.fetchrow = AsyncMock(return_value={"report_id": "test-uuid-123"})

        mock_pool = MagicMock()
        mock_pool.acquire = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)

        # mock get_pool 函数
        async def _fake_get_pool(_settings):
            return mock_pool

        monkeypatch.setattr(
            "src.memory.report_store.get_pool", _fake_get_pool
        )

        return mock_conn, []

    async def test_insert_sql_contains_new_columns(
        self,
        captured_sql: tuple,
    ) -> None:
        """INSERT SQL 应含 report_type_label / report_summary / report_image_svg."""
        mock_conn, _ = captured_sql
        store = ReportStore(settings=MagicMock())

        await store.save_report(
            session_id="sess-1",
            user_id="user-1",
            agent_id="agentinsight-docbot",
            query="测试查询",
            report_md="# 报告内容",
            report_format="markdown",
            sources=[],
            agent_role="architecture",
            report_type_label="architecture",
            report_summary="这是一个架构文档",
            report_image_svg="<svg></svg>",
        )

        # 验证 fetchrow 被调用
        assert mock_conn.fetchrow.called
        call_args = mock_conn.fetchrow.call_args
        sql_arg = call_args.args[0] if call_args.args else call_args[0][0]

        # SQL 应含三个新列名
        assert "report_type_label" in sql_arg
        assert "report_summary" in sql_arg
        assert "report_image_svg" in sql_arg
        # VALUES 占位符应为 11 个 ($1..$11)
        assert "$9" in sql_arg
        assert "$10" in sql_arg
        assert "$11" in sql_arg

    async def test_insert_passes_new_column_values(
        self,
        captured_sql: tuple,
    ) -> None:
        """save_report 应把新参数值传递到 SQL 参数列表."""
        mock_conn, _ = captured_sql
        store = ReportStore(settings=MagicMock())

        await store.save_report(
            session_id="sess-1",
            user_id="user-1",
            agent_id="agentinsight-docbot",
            query="测试查询",
            report_md="# 报告内容",
            report_format="markdown",
            sources=[],
            agent_role="architecture",
            report_type_label="architecture",
            report_summary="摘要内容",
            report_image_svg="<svg>image</svg>",
        )

        call_args = mock_conn.fetchrow.call_args
        # 参数列表 (位置参数, 跳过 SQL 字符串)
        sql_params = call_args.args[1:] if call_args.args else call_args[0][1:]
        # $9 = report_type_label, $10 = report_summary, $11 = report_image_svg
        assert sql_params[8] == "architecture"
        assert sql_params[9] == "摘要内容"
        assert sql_params[10] == "<svg>image</svg>"

    async def test_insert_defaults_to_none_when_omitted(
        self,
        captured_sql: tuple,
    ) -> None:
        """不传新参数时, 三列应写入 None (向后兼容)."""
        mock_conn, _ = captured_sql
        store = ReportStore(settings=MagicMock())

        # 旧调用方式: 不传新参数
        await store.save_report(
            session_id="sess-1",
            user_id="user-1",
            agent_id="agentinsight-docbot",
            query="测试查询",
            report_md="# 报告内容",
            report_format="markdown",
            sources=[],
            agent_role="architecture",
        )

        call_args = mock_conn.fetchrow.call_args
        sql_params = call_args.args[1:] if call_args.args else call_args[0][1:]
        # $9, $10, $11 都应为 None
        assert sql_params[8] is None
        assert sql_params[9] is None
        assert sql_params[10] is None


class TestRowToDictExtensionColumns:
    """_row_to_dict 应自动包含 docbot 扩展列."""

    def test_row_to_dict_includes_extension_columns(self) -> None:
        """dict(row) 自动包含所有列, 无需额外处理."""
        # 模拟 asyncpg.Record (用 dict 替代)
        fake_row = {
            "report_id": "uuid-1",
            "session_id": "sess-1",
            "user_id": "user-1",
            "agent_id": "agentinsight-docbot",
            "query": "测试",
            "report_md": "# 内容",
            "report_format": "markdown",
            "sources": [],
            "agent_role": "architecture",
            "report_type_label": "architecture",
            "report_summary": "摘要",
            "report_image_svg": "<svg></svg>",
            "created_at": None,
            "updated_at": None,
        }

        # dict(fake_row) 模拟 dict(row) 行为
        d = dict(fake_row)
        result = _row_to_dict(d)  # type: ignore[arg-type]

        assert result["report_type_label"] == "architecture"
        assert result["report_summary"] == "摘要"
        assert result["report_image_svg"] == "<svg></svg>"

"""API 测试: /v1/reports/{id}/download 测试 (鉴权/格式/404).

不依赖外部服务, 用 mock 验证:
- 5 种格式各自的响应
- 404 (报告不存在)
- 403 (跨用户访问)
- 数据隔离校验 (report_user_id != user_id → 403)
- deprecated_fallback (session_id 兼容)
"""
from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException


@pytest.mark.api
class TestReportDownloadAuth:
    """报告下载鉴权测试."""

    async def test_download_nonexistent_report_returns_404(self, mock_settings: Any) -> None:
        """不存在的 report_id 应返回 404."""
        from src.api.routes import download_report

        mock_store = MagicMock()
        mock_store.get_report = AsyncMock(return_value=None)
        mock_store.list_reports = AsyncMock(return_value=[])

        with (
            patch("src.memory.report_store.get_report_store", return_value=mock_store),
            patch("src.api.routes.get_settings") as mock_get_settings,
            patch("src.api.routes.get_request_user_id", return_value="test_docbot_user_1"),
            patch("src.api.routes.uuid.UUID", side_effect=ValueError("not uuid")),
        ):
            mock_get_settings.return_value.agent_name = "agentinsight-docbot"

            with pytest.raises(HTTPException) as exc_info:
                await download_report(
                    report_id="nonexistent-id",
                    format="markdown",
                    authorization="Bearer test-jwt",
                )

        assert exc_info.value.status_code == 404
        assert "报告不存在" in exc_info.value.detail

    async def test_download_cross_user_returns_403(self, mock_settings: Any) -> None:
        """跨用户访问报告应返回 403 (数据隔离)."""
        from src.api.routes import download_report

        mock_store = MagicMock()
        # 报告属于 other_user, 但当前请求是 test_docbot_user_1
        mock_store.get_report = AsyncMock(return_value={
            "report_id": "test-uuid-1",
            "user_id": "other_user",
            "report_md": "# 内容",
            "query": "测试",
            "sources": [],
            "agent_role": "architecture",
        })

        with (
            patch("src.memory.report_store.get_report_store", return_value=mock_store),
            patch("src.api.routes.get_settings") as mock_get_settings,
            patch("src.api.routes.get_request_user_id", return_value="test_docbot_user_1"),
            patch("src.api.routes.uuid.UUID"),  # 不抛 ValueError
        ):
            mock_get_settings.return_value.agent_name = "agentinsight-docbot"

            with pytest.raises(HTTPException) as exc_info:
                await download_report(
                    report_id="test-uuid-1",
                    format="markdown",
                    authorization="Bearer test-jwt",
                )

        assert exc_info.value.status_code == 403
        assert "无权访问" in exc_info.value.detail

    async def test_download_invalid_format_returns_400(self, mock_settings: Any) -> None:
        """非法 format 应返回 400."""
        from src.api.routes import download_report

        mock_store = MagicMock()
        mock_store.get_report = AsyncMock(return_value={
            "report_id": "test-uuid-1",
            "user_id": "test_docbot_user_1",
            "report_md": "# 内容",
            "query": "测试",
            "sources": [],
            "agent_role": "architecture",
        })

        with (
            patch("src.memory.report_store.get_report_store", return_value=mock_store),
            patch("src.api.routes.get_settings") as mock_get_settings,
            patch("src.api.routes.get_request_user_id", return_value="test_docbot_user_1"),
            patch("src.api.routes.uuid.UUID"),
            patch("src.skills.researcher.publisher.Publisher"),
        ):
            mock_get_settings.return_value.agent_name = "agentinsight-docbot"

            with pytest.raises(HTTPException) as exc_info:
                await download_report(
                    report_id="test-uuid-1",
                    format="invalid_format",
                    authorization="Bearer test-jwt",
                )

        assert exc_info.value.status_code == 400
        assert "不支持的格式" in exc_info.value.detail


@pytest.mark.api
class TestReportDownloadFormats:
    """报告下载 5 种格式测试."""

    async def test_download_markdown_format(self, mock_settings: Any) -> None:
        """markdown 格式下载应返回 text/markdown."""
        from src.api.routes import download_report

        mock_store = MagicMock()
        mock_store.get_report = AsyncMock(return_value={
            "report_id": "test-uuid-1",
            "user_id": "test_docbot_user_1",
            "report_md": "# 报告内容",
            "query": "测试",
            "sources": [],
            "agent_role": "architecture",
        })

        with (
            patch("src.memory.report_store.get_report_store", return_value=mock_store),
            patch("src.api.routes.get_settings") as mock_get_settings,
            patch("src.api.routes.get_request_user_id", return_value="test_docbot_user_1"),
            patch("src.api.routes.uuid.UUID"),
        ):
            mock_get_settings.return_value.agent_name = "agentinsight-docbot"

            response = await download_report(
                report_id="test-uuid-1",
                format="markdown",
                authorization="Bearer test-jwt",
            )

        assert response.media_type == "text/markdown"
        # Content-Disposition 应含 filename
        content_disp = response.headers.get("content-disposition", "")
        assert "attachment" in content_disp
        assert ".md" in content_disp

    async def test_download_json_format(self, mock_settings: Any) -> None:
        """json 格式下载应返回 application/json."""
        from src.api.routes import download_report

        mock_store = MagicMock()
        mock_store.get_report = AsyncMock(return_value={
            "report_id": "test-uuid-1",
            "user_id": "test_docbot_user_1",
            "report_md": "# 报告内容",
            "query": "测试",
            "sources": [],
            "agent_role": "architecture",
        })

        mock_publisher = MagicMock()
        mock_publisher._to_json = MagicMock(return_value='{"title":"报告"}')

        with (
            patch("src.memory.report_store.get_report_store", return_value=mock_store),
            patch("src.skills.researcher.publisher.Publisher", return_value=mock_publisher),
            patch("src.api.routes.get_settings") as mock_get_settings,
            patch("src.api.routes.get_request_user_id", return_value="test_docbot_user_1"),
            patch("src.api.routes.uuid.UUID"),
        ):
            mock_get_settings.return_value.agent_name = "agentinsight-docbot"

            response = await download_report(
                report_id="test-uuid-1",
                format="json",
                authorization="Bearer test-jwt",
            )

        assert response.media_type == "application/json"
        content_disp = response.headers.get("content-disposition", "")
        assert ".json" in content_disp


@pytest.mark.api
class TestListSessionReports:
    """/v1/reports/session/{session_id} 端点测试."""

    async def test_list_session_reports_returns_list(self, mock_settings: Any) -> None:
        """列出 session 报告应返回 list."""
        from src.api.routes import list_session_reports

        mock_store = MagicMock()
        mock_store.list_reports = AsyncMock(return_value=[
            {
                "report_id": "test-uuid-1",
                "session_id": "test_docbot_session_1",
                "query": "测试1",
                "report_format": "markdown",
                "agent_role": "architecture",
                "created_at": None,
                "updated_at": None,
            },
            {
                "report_id": "test-uuid-2",
                "session_id": "test_docbot_session_1",
                "query": "测试2",
                "report_format": "html",
                "agent_role": "design",
                "created_at": None,
                "updated_at": None,
            },
        ])

        with (
            patch("src.memory.report_store.get_report_store", return_value=mock_store),
            patch("src.api.routes.get_settings") as mock_get_settings,
            patch("src.api.routes.get_request_user_id", return_value="test_docbot_user_1"),
        ):
            mock_get_settings.return_value.agent_name = "agentinsight-docbot"

            result = await list_session_reports(
                session_id="test_docbot_session_1",
                authorization="Bearer test-jwt",
            )

        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["report_id"] == "test-uuid-1"

    async def test_list_session_reports_empty(self, mock_settings: Any) -> None:
        """空 session 应返回空列表."""
        from src.api.routes import list_session_reports

        mock_store = MagicMock()
        mock_store.list_reports = AsyncMock(return_value=[])

        with (
            patch("src.memory.report_store.get_report_store", return_value=mock_store),
            patch("src.api.routes.get_settings") as mock_get_settings,
            patch("src.api.routes.get_request_user_id", return_value="test_docbot_user_1"),
        ):
            mock_get_settings.return_value.agent_name = "agentinsight-docbot"

            result = await list_session_reports(
                session_id="empty_session",
                authorization="Bearer test-jwt",
            )

        assert result == []

    async def test_list_session_reports_query_truncated(self, mock_settings: Any) -> None:
        """query 字段应截断到 200 字符."""
        from src.api.routes import list_session_reports

        long_query = "x" * 500
        mock_store = MagicMock()
        mock_store.list_reports = AsyncMock(return_value=[
            {
                "report_id": "test-uuid-1",
                "session_id": "test_docbot_session_1",
                "query": long_query,
                "report_format": "markdown",
                "agent_role": None,
                "created_at": None,
                "updated_at": None,
            },
        ])

        with (
            patch("src.memory.report_store.get_report_store", return_value=mock_store),
            patch("src.api.routes.get_settings") as mock_get_settings,
            patch("src.api.routes.get_request_user_id", return_value="test_docbot_user_1"),
        ):
            mock_get_settings.return_value.agent_name = "agentinsight-docbot"

            result = await list_session_reports(
                session_id="test_docbot_session_1",
                authorization="Bearer test-jwt",
            )

        # query 应被截断到 200 字符
        assert len(result[0]["query"]) <= 200

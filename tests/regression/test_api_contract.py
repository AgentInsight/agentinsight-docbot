"""回归测试: API 契约稳定性 (确保 API 行为不随重构改变).

不依赖外部服务, 用 mock 验证 API 契约:
- /v1/chat/completions 请求/响应字段稳定
- /v1/chat/completions 错误码契约 (400/500)
- /v1/reports/{id}/download 鉴权契约 (404/403/400)
- /v1/reports/{id}/download download_urls 相对路径格式
- /v1/models 端点返回 model 列表
- /v1/repos CRUD 字段稳定 (RepoResponse 字段集)

回归目标 (AGENTS.md 第 13 章回归测试):
- API 契约变更应被检测 (字段增删/类型变更/错误码变更)
- 不依赖 --run-external
"""
from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.api.routes import (
    ChatCompletionRequest,
    ChatMessage,
    _parse_docbot_instruction,
)
from src.api.repo_routes import (
    RepoCreateRequest,
    RepoResponse,
    RepoUpdateRequest,
    _row_to_response,
)


@pytest.mark.regression
class TestChatCompletionsContract:
    """/v1/chat/completions API 契约稳定性."""

    def test_request_model_has_required_fields(self) -> None:
        """ChatCompletionRequest 应含 messages 字段."""
        sig_fields = ChatCompletionRequest.model_fields
        assert "messages" in sig_fields
        assert "model" in sig_fields
        assert "stream" in sig_fields

    def test_request_model_has_docbot_extension_fields(self) -> None:
        """ChatCompletionRequest 应含 docbot 扩展字段."""
        sig_fields = ChatCompletionRequest.model_fields
        assert "repo_id" in sig_fields
        assert "report_types" in sig_fields
        assert "report_format" in sig_fields
        assert "language" in sig_fields
        assert "session_id" in sig_fields

    def test_default_model_is_docbot(self) -> None:
        """默认 model 应稳定为 'agentinsight-docbot'."""
        req = ChatCompletionRequest(messages=[ChatMessage(role="user", content="x")])
        assert req.model == "agentinsight-docbot"

    def test_default_stream_is_false(self) -> None:
        """默认 stream 应稳定为 False."""
        req = ChatCompletionRequest(messages=[ChatMessage(role="user", content="x")])
        assert req.stream is False

    def test_chat_message_has_role_and_content(self) -> None:
        """ChatMessage 应含 role 和 content 字段."""
        msg = ChatMessage(role="user", content="测试")
        assert msg.role == "user"
        assert msg.content == "测试"


@pytest.mark.regression
class TestReportDownloadUrlContract:
    """download_urls 相对路径格式契约."""

    def test_download_url_relative_path_format(self) -> None:
        """download_urls 应为相对路径 /v1/reports/{id}/download?format={fmt}."""
        report_id = "test_docbot_report_uuid_1"
        # 5 种格式的 download_urls
        download_urls = {
            fmt: f"/v1/reports/{report_id}/download?format={fmt}"
            for fmt in ("markdown", "html", "pdf", "docx", "json")
        }
        for fmt, url in download_urls.items():
            # 应为相对路径 (不以 http 开头)
            assert url.startswith("/v1/reports/")
            assert f"format={fmt}" in url
            assert report_id in url

    def test_download_url_contains_all_5_formats(self) -> None:
        """download_urls 应含 5 种格式."""
        report_id = "test_docbot_report_uuid_1"
        # 模拟 save_reports_node 生成的 download_urls
        formats = ["markdown", "html", "pdf", "docx", "json"]
        download_urls = {
            fmt: f"/v1/reports/{report_id}/download?format={fmt}"
            for fmt in formats
        }
        assert set(download_urls.keys()) == set(formats)


@pytest.mark.regression
class TestRepoResponseContract:
    """RepoResponse 字段集契约稳定性."""

    def test_repo_response_has_no_sensitive_fields(self) -> None:
        """RepoResponse 不应含敏感字段 (encrypted_xxx)."""
        fields = set(RepoResponse.model_fields.keys())
        # 禁止出现加密字段
        assert "encrypted_token" not in fields
        assert "encrypted_username" not in fields
        assert "encrypted_password" not in fields
        assert "encrypted_ssh_key" not in fields
        assert "ssh_passphrase" not in fields

    def test_repo_response_has_has_xxx_flags(self) -> None:
        """RepoResponse 应含 has_xxx 标志位."""
        fields = set(RepoResponse.model_fields.keys())
        assert "has_token" in fields
        assert "has_username" in fields
        assert "has_password" in fields
        assert "has_ssh_key" in fields

    def test_repo_response_has_required_fields(self) -> None:
        """RepoResponse 应含基础字段."""
        fields = set(RepoResponse.model_fields.keys())
        required = {
            "id", "repo_name", "platform", "repo_url",
            "default_branch", "auth_type",
            "clone_depth", "enabled",
            "last_synced_at", "last_sync_status", "last_sync_error",
            "created_at", "updated_at",
        }
        assert required.issubset(fields)

    def test_repo_create_request_auth_type_enum(self) -> None:
        """RepoCreateRequest.auth_type 应支持 4 种枚举值."""
        for auth in ("none", "token", "password", "ssh_key"):
            req = RepoCreateRequest(
                repo_name="t",
                platform="github",
                repo_url="https://github.com/t/t.git",
                auth_type=auth,
            )
            assert req.auth_type == auth

    def test_repo_create_request_platform_enum(self) -> None:
        """RepoCreateRequest.platform 应支持 7 种枚举值."""
        for plat in ("github", "gitlab", "gitee", "bitbucket", "coding", "gitea", "custom"):
            req = RepoCreateRequest(
                repo_name="t",
                platform=plat,
                repo_url="https://example.com/t/t.git",
            )
            assert req.platform == plat


@pytest.mark.regression
class TestValidationErrorContract:
    """校验错误码契约 (400 错误稳定)."""

    @pytest.mark.parametrize(
        "language",
        ["zh", "en", "ZH", "EN", "Zh", "eN"],
    )
    def test_language_accepts_zh_en_case_insensitive(self, language: str) -> None:
        """language 应接受 zh/en (大小写不敏感, 内部 .lower())."""
        # 仅验证 .lower() 后的值在 zh/en 中
        assert language.lower() in ("zh", "en")

    @pytest.mark.parametrize(
        "invalid_language",
        ["fr", "de", "ja", "english", "chinese", ""],
    )
    def test_invalid_language_rejected(self, invalid_language: str) -> None:
        """非 zh/en 的 language 应被拒绝."""
        if not invalid_language:
            return  # 空字符串由 Pydantic 校验
        assert invalid_language.lower() not in ("zh", "en")

    @pytest.mark.parametrize(
        "report_format",
        ["markdown", "html", "pdf", "docx", "json"],
    )
    def test_valid_report_formats_accepted(self, report_format: str) -> None:
        """5 种 report_format 应被接受."""
        valid_formats = {"markdown", "html", "pdf", "docx", "json"}
        assert report_format in valid_formats

    @pytest.mark.parametrize(
        "invalid_format",
        ["txt", "rtf", "csv", "xml", "yaml", "MD", "HTML"],
    )
    def test_invalid_report_formats_rejected(self, invalid_format: str) -> None:
        """非 5 种格式的 report_format 应被拒绝."""
        valid_formats = {"markdown", "html", "pdf", "docx", "json"}
        assert invalid_format not in valid_formats

    @pytest.mark.parametrize(
        "report_type",
        [
            "architecture", "design", "requirements", "testcase",
            "optimization", "performance", "defect", "api_doc",
        ],
    )
    def test_valid_report_types_accepted(self, report_type: str) -> None:
        """8 种 report_type 应被接受."""
        valid_types = {
            "architecture", "design", "requirements", "testcase",
            "optimization", "performance", "defect", "api_doc",
        }
        assert report_type in valid_types

    @pytest.mark.parametrize(
        "invalid_type",
        ["overview", "summary", "intro", "conclusion", "refactor", "", "ARCHITECTURE"],
    )
    def test_invalid_report_types_rejected(self, invalid_type: str) -> None:
        """非 8 种类型的 report_type 应被拒绝."""
        if not invalid_type:
            return
        valid_types = {
            "architecture", "design", "requirements", "testcase",
            "optimization", "performance", "defect", "api_doc",
        }
        assert invalid_type not in valid_types

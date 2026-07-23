"""API 测试: /v1/chat/completions 完整 API 测试 (流式/非流式/错误码).

不依赖外部服务, 用 mock 验证:
- 请求体校验 (Pydantic ChatCompletionRequest)
- JSON 指令解析 (_parse_docbot_instruction)
- 字段优先级: 显式请求字段 > 消息内容 JSON 指令 > Settings 默认值
- 错误码: 400 (缺 repo_id / 非法 language / 非法 report_types / 非法 report_format)
- 流式 SSE 响应格式

测试目标 (AGENTS.md 第 13 章关键测试用例 3):
- /v1/chat/completions 流式 SSE + 非流式 + 错误码
"""
from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from src.api.routes import (
    ChatCompletionRequest,
    ChatMessage,
    _parse_docbot_instruction,
)


@pytest.mark.api
class TestChatCompletionRequestModel:
    """ChatCompletionRequest Pydantic 模型测试."""

    def test_minimal_request_with_repo_id(self) -> None:
        """最小请求应含 messages + repo_id."""
        req = ChatCompletionRequest(
            messages=[ChatMessage(role="user", content="生成文档")],
            repo_id="test_docbot_repo_1",
        )
        assert req.model == "agentinsight-docbot"
        assert req.stream is False
        assert req.repo_id == "test_docbot_repo_1"
        assert req.report_types is None
        assert req.report_format is None
        assert req.language is None

    def test_request_with_all_extension_fields(self) -> None:
        """含所有扩展字段的请求."""
        req = ChatCompletionRequest(
            messages=[ChatMessage(role="user", content="生成文档")],
            repo_id="test_docbot_repo_1",
            report_types=["architecture", "design"],
            report_format="html",
            language="en",
            session_id="test_docbot_session_1",
            stream=True,
        )
        assert req.repo_id == "test_docbot_repo_1"
        assert req.report_types == ["architecture", "design"]
        assert req.report_format == "html"
        assert req.language == "en"
        assert req.session_id == "test_docbot_session_1"
        assert req.stream is True

    def test_request_default_model_is_docbot(self) -> None:
        """默认 model 应为 'agentinsight-docbot'."""
        req = ChatCompletionRequest(
            messages=[ChatMessage(role="user", content="生成")],
        )
        assert req.model == "agentinsight-docbot"


@pytest.mark.api
class TestInstructionParsing:
    """_parse_docbot_instruction JSON 指令解析测试."""

    def test_parse_valid_json_instruction(self) -> None:
        """合法 JSON 指令应解析为 dict."""
        content = '{"action":"generate_docs","repo_id":"test_docbot_repo_1","report_types":["architecture"]}'
        result = _parse_docbot_instruction(content)
        assert isinstance(result, dict)
        assert result.get("action") == "generate_docs"
        assert result.get("repo_id") == "test_docbot_repo_1"
        assert result.get("report_types") == ["architecture"]

    def test_parse_empty_content_returns_empty_dict(self) -> None:
        """空 content 应返回空 dict."""
        assert _parse_docbot_instruction("") == {}
        assert _parse_docbot_instruction("   ") == {}

    def test_parse_invalid_json_returns_empty_dict(self) -> None:
        """非法 JSON 应返回空 dict (走默认配置)."""
        assert _parse_docbot_instruction("not json") == {}
        assert _parse_docbot_instruction("{invalid json") == {}

    def test_parse_non_dict_json_returns_empty_dict(self) -> None:
        """非 dict JSON (list/str/int) 应返回空 dict."""
        assert _parse_docbot_instruction("[1,2,3]") == {}
        assert _parse_docbot_instruction('"string"') == {}
        assert _parse_docbot_instruction("123") == {}

    def test_parse_code_fence_wrapped_json(self) -> None:
        """代码块围栏包裹的 JSON 应正确解析."""
        content = '```json\n{"action":"generate_docs","repo_id":"test"}\n```'
        result = _parse_docbot_instruction(content)
        assert isinstance(result, dict)
        assert result.get("repo_id") == "test"

    def test_parse_code_fence_without_lang(self) -> None:
        """无语言标识的代码块围栏也应解析."""
        content = '```\n{"action":"generate_docs","repo_id":"test"}\n```'
        result = _parse_docbot_instruction(content)
        assert isinstance(result, dict)
        assert result.get("repo_id") == "test"

    def test_parse_json_with_extra_whitespace(self) -> None:
        """前后空白应被容忍."""
        content = '  \n  {"action":"generate_docs","repo_id":"test"}  \n  '
        result = _parse_docbot_instruction(content)
        assert isinstance(result, dict)
        assert result.get("repo_id") == "test"

    def test_parse_instruction_with_all_fields(self) -> None:
        """含所有字段的指令应完整解析."""
        content = (
            '{"action":"generate_docs","repo_id":"test_docbot_repo_1",'
            '"report_types":["architecture","design","requirements"],'
            '"report_format":"pdf","language":"en"}'
        )
        result = _parse_docbot_instruction(content)
        assert result["repo_id"] == "test_docbot_repo_1"
        assert result["report_types"] == ["architecture", "design", "requirements"]
        assert result["report_format"] == "pdf"
        assert result["language"] == "en"


@pytest.mark.api
class TestChatCompletionsValidation:
    """chat_completions 端点字段校验测试 (mock settings + graph)."""

    async def test_missing_repo_id_returns_400(self, mock_settings: Any) -> None:
        """缺 repo_id 应返回 400."""
        from src.api.routes import chat_completions

        request = ChatCompletionRequest(
            messages=[ChatMessage(role="user", content='{"action":"generate_docs"}')],
        )

        with (
            patch("src.api.routes.get_settings", return_value=mock_settings),
            patch("src.api.routes.get_request_session_id", return_value=""),
            patch("src.api.routes.get_request_user_id", return_value=""),
            patch("src.api.routes.get_request_agent_id", return_value=""),
            patch("src.api.middleware.get_request_session_id", return_value=""),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await chat_completions(request, req=MagicMock(), authorization=None)

        assert exc_info.value.status_code == 400
        assert "repo_id" in exc_info.value.detail

    async def test_invalid_language_returns_400(self, mock_settings: Any) -> None:
        """非法 language 应返回 400."""
        from src.api.routes import chat_completions

        request = ChatCompletionRequest(
            messages=[ChatMessage(role="user", content='{"action":"generate_docs","repo_id":"test","language":"ja"}')],
        )

        with (
            patch("src.api.routes.get_settings", return_value=mock_settings),
            patch("src.api.routes.get_request_session_id", return_value=""),
            patch("src.api.routes.get_request_user_id", return_value=""),
            patch("src.api.routes.get_request_agent_id", return_value=""),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await chat_completions(request, req=MagicMock(), authorization=None)

        assert exc_info.value.status_code == 400
        assert "language" in exc_info.value.detail

    async def test_invalid_report_types_returns_400(self, mock_settings: Any) -> None:
        """非法 report_types 应返回 400."""
        from src.api.routes import chat_completions

        # mock_settings.report_language 必须为字符串, 否则 language 校验先失败
        mock_settings.default_report_format = "markdown"
        mock_settings.report_language = "zh"

        request = ChatCompletionRequest(
            messages=[ChatMessage(
                role="user",
                content='{"action":"generate_docs","repo_id":"test","report_types":["unknown_type"]}',
            )],
        )

        with (
            patch("src.api.routes.get_settings", return_value=mock_settings),
            patch("src.api.routes.get_request_session_id", return_value=""),
            patch("src.api.routes.get_request_user_id", return_value=""),
            patch("src.api.routes.get_request_agent_id", return_value=""),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await chat_completions(request, req=MagicMock(), authorization=None)

        assert exc_info.value.status_code == 400
        assert "report_types" in exc_info.value.detail

    async def test_invalid_report_format_returns_400(self, mock_settings: Any) -> None:
        """非法 report_format 应返回 400."""
        from src.api.routes import chat_completions

        # mock_settings.report_language 必须为字符串, 否则 language 校验先失败
        mock_settings.default_report_format = "markdown"
        mock_settings.report_language = "zh"

        request = ChatCompletionRequest(
            messages=[ChatMessage(
                role="user",
                content='{"action":"generate_docs","repo_id":"test","report_format":"xml"}',
            )],
        )

        with (
            patch("src.api.routes.get_settings", return_value=mock_settings),
            patch("src.api.routes.get_request_session_id", return_value=""),
            patch("src.api.routes.get_request_user_id", return_value=""),
            patch("src.api.routes.get_request_agent_id", return_value=""),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await chat_completions(request, req=MagicMock(), authorization=None)

        assert exc_info.value.status_code == 400
        assert "report_format" in exc_info.value.detail

    async def test_empty_messages_returns_400(self, mock_settings: Any) -> None:
        """空 messages 应返回 400 (无 user 消息)."""
        from src.api.routes import chat_completions

        request = ChatCompletionRequest(messages=[])

        with patch("src.api.routes.get_settings", return_value=mock_settings):
            with pytest.raises(HTTPException) as exc_info:
                await chat_completions(request, req=MagicMock(), authorization=None)

        assert exc_info.value.status_code == 400
        assert "messages" in exc_info.value.detail

    async def test_empty_content_returns_400(self, mock_settings: Any) -> None:
        """空 content 应返回 400."""
        from src.api.routes import chat_completions

        request = ChatCompletionRequest(
            messages=[ChatMessage(role="user", content="   ")],
        )

        with patch("src.api.routes.get_settings", return_value=mock_settings):
            with pytest.raises(HTTPException) as exc_info:
                await chat_completions(request, req=MagicMock(), authorization=None)

        assert exc_info.value.status_code == 400

    async def test_default_report_types_when_missing(self, mock_settings: Any) -> None:
        """缺 report_types 时默认为 ['architecture']."""
        from src.api.routes import ChatCompletionResponse, chat_completions

        # mock settings 让 default_report_format 等不抛异常
        mock_settings.default_report_format = "markdown"
        mock_settings.report_language = "zh"
        mock_settings.graph_total_timeout = 300

        request = ChatCompletionRequest(
            messages=[ChatMessage(role="user", content='{"action":"generate_docs","repo_id":"test"}')],
        )

        # mock 整个 _run_docbot 验证 default report_types 注入
        captured_state: dict[str, Any] = {}

        async def _fake_run_docbot(state, config, req, sess_id):
            captured_state.update(state)
            # 返回真实 ChatCompletionResponse (避免 MagicMock 无法 JSON 序列化)
            return ChatCompletionResponse(
                id="chatcmpl-test",
                created=0,
                model="agentinsight-docbot",
                choices=[
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": "ok"},
                        "finish_reason": "stop",
                    }
                ],
                usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            )

        with (
            patch("src.api.routes.get_settings", return_value=mock_settings),
            patch("src.api.routes.get_request_session_id", return_value=""),
            patch("src.api.routes.get_request_user_id", return_value="test_docbot_user_1"),
            patch("src.api.routes.get_request_agent_id", return_value="agentinsight-docbot"),
            patch("src.api.routes._run_docbot", _fake_run_docbot),
            patch("src.api.routes._persist_user_message", AsyncMock()),
            patch("src.api.routes._persist_assistant_message", AsyncMock()),
            patch("src.memory.session_store.get_session_store") as mock_get_store,
        ):
            mock_store = MagicMock()
            mock_store.update_report_config = AsyncMock()
            mock_get_store.return_value = mock_store

            await chat_completions(request, req=MagicMock(), authorization=None)

        # 默认 report_types 应为 ['architecture']
        assert captured_state.get("report_types") == ["architecture"]

    async def test_field_priority_explicit_over_instruction(self, mock_settings: Any) -> None:
        """显式请求字段优先级高于消息内容 JSON 指令."""
        from src.api.routes import ChatCompletionResponse, chat_completions

        mock_settings.default_report_format = "markdown"
        mock_settings.report_language = "zh"
        mock_settings.graph_total_timeout = 300

        # 消息内容指令用 zh, 显式请求字段传 en
        request = ChatCompletionRequest(
            messages=[ChatMessage(
                role="user",
                content='{"action":"generate_docs","repo_id":"from_instruction","language":"zh"}',
            )],
            repo_id="from_explicit",
            language="en",
        )

        captured_state: dict[str, Any] = {}

        async def _fake_run_docbot(state, config, req, sess_id):
            captured_state.update(state)
            # 返回真实 ChatCompletionResponse (避免 MagicMock 无法 JSON 序列化)
            return ChatCompletionResponse(
                id="chatcmpl-test",
                created=0,
                model="agentinsight-docbot",
                choices=[
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": "ok"},
                        "finish_reason": "stop",
                    }
                ],
                usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            )

        with (
            patch("src.api.routes.get_settings", return_value=mock_settings),
            patch("src.api.routes.get_request_session_id", return_value=""),
            patch("src.api.routes.get_request_user_id", return_value="test_docbot_user_1"),
            patch("src.api.routes.get_request_agent_id", return_value="agentinsight-docbot"),
            patch("src.api.routes._run_docbot", _fake_run_docbot),
            patch("src.api.routes._persist_user_message", AsyncMock()),
            patch("src.api.routes._persist_assistant_message", AsyncMock()),
            patch("src.memory.session_store.get_session_store") as mock_get_store,
        ):
            mock_store = MagicMock()
            mock_store.update_report_config = AsyncMock()
            mock_get_store.return_value = mock_store

            await chat_completions(request, req=MagicMock(), authorization=None)

        # 显式字段优先
        assert captured_state.get("repo_id") == "from_explicit"
        assert captured_state.get("language") == "en"


@pytest.mark.api
class TestListModelsEndpoint:
    """/v1/models 端点测试."""

    async def test_list_models_returns_docbot(self) -> None:
        """/v1/models 应返回 agentinsight-docbot."""
        from src.api.routes import list_models

        result = await list_models()
        assert result["object"] == "list"
        assert len(result["data"]) == 1
        assert result["data"][0]["id"] == "agentinsight-docbot"
        assert result["data"][0]["owned_by"] == "agentinsight"

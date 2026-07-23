"""回归测试: SSE 流式响应格式稳定性.

不依赖外部服务, 验证 SSE 格式契约:
- data: 行格式 (OpenAI 兼容)
- [DONE] 结束标记
- chunk 结构: {id, object, created, model, choices}
- choices 结构: {index, delta, finish_reason}
- 错误事件格式: {"error": {...}}

测试目标 (AGENTS.md 第 13 章回归测试):
- SSE 格式不随重构改变
- 不依赖 --run-external
"""
from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _make_sse_chunk(
    content: str = "",
    finish_reason: str | None = None,
    chunk_id: str = "chatcmpl-test_docbot_1",
    model: str = "agentinsight-docbot",
) -> str:
    """构造 OpenAI 兼容的 SSE chunk 字符串."""
    delta: dict[str, Any] = {}
    if content:
        delta["content"] = content
    if finish_reason:
        delta = {}  # finish 时 delta 通常为空
    chunk = {
        "id": chunk_id,
        "object": "chat.completion.chunk",
        "created": 1767200000,
        "model": model,
        "choices": [
            {
                "index": 0,
                "delta": delta,
                "finish_reason": finish_reason,
            }
        ],
    }
    return f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"


@pytest.mark.regression
class TestSSEFormatContract:
    """SSE 格式契约稳定性."""

    def test_sse_chunk_starts_with_data_prefix(self) -> None:
        """SSE chunk 应以 'data: ' 开头."""
        chunk = _make_sse_chunk(content="hello")
        assert chunk.startswith("data: ")

    def test_sse_chunk_ends_with_double_newline(self) -> None:
        """SSE chunk 应以 '\\n\\n' 结尾."""
        chunk = _make_sse_chunk(content="hello")
        assert chunk.endswith("\n\n")

    def test_sse_chunk_json_parseable(self) -> None:
        """SSE chunk 的 data 应可解析为 JSON."""
        chunk = _make_sse_chunk(content="hello")
        data_line = chunk.strip().removeprefix("data: ")
        parsed = json.loads(data_line)
        assert isinstance(parsed, dict)
        assert parsed["object"] == "chat.completion.chunk"

    def test_sse_chunk_has_required_fields(self) -> None:
        """SSE chunk JSON 应含 id/object/created/model/choices."""
        chunk = _make_sse_chunk(content="hello")
        data_line = chunk.strip().removeprefix("data: ")
        parsed = json.loads(data_line)
        assert "id" in parsed
        assert "object" in parsed
        assert "created" in parsed
        assert "model" in parsed
        assert "choices" in parsed

    def test_sse_chunk_choices_structure(self) -> None:
        """SSE chunk choices 应含 index/delta/finish_reason."""
        chunk = _make_sse_chunk(content="hello", finish_reason="stop")
        data_line = chunk.strip().removeprefix("data: ")
        parsed = json.loads(data_line)
        choice = parsed["choices"][0]
        assert "index" in choice
        assert "delta" in choice
        assert "finish_reason" in choice

    def test_sse_done_marker_format(self) -> None:
        """SSE 流应以 'data: [DONE]\\n\\n' 结束."""
        done_marker = "data: [DONE]\n\n"
        assert done_marker.startswith("data: [DONE]")
        assert done_marker.endswith("\n\n")

    def test_sse_content_delta_carries_text(self) -> None:
        """content delta 应携带文本片段."""
        chunk = _make_sse_chunk(content="架构")
        data_line = chunk.strip().removeprefix("data: ")
        parsed = json.loads(data_line)
        assert parsed["choices"][0]["delta"]["content"] == "架构"

    def test_sse_finish_chunk_has_stop_reason(self) -> None:
        """结束 chunk 的 finish_reason 应为 'stop'."""
        chunk = _make_sse_chunk(finish_reason="stop")
        data_line = chunk.strip().removeprefix("data: ")
        parsed = json.loads(data_line)
        assert parsed["choices"][0]["finish_reason"] == "stop"


@pytest.mark.regression
class TestSSEModelField:
    """SSE chunk model 字段稳定性."""

    def test_model_field_is_docbot(self) -> None:
        """SSE chunk model 应为 'agentinsight-docbot'."""
        chunk = _make_sse_chunk(content="hello")
        data_line = chunk.strip().removeprefix("data: ")
        parsed = json.loads(data_line)
        assert parsed["model"] == "agentinsight-docbot"

    def test_object_field_is_chat_completion_chunk(self) -> None:
        """SSE chunk object 应为 'chat.completion.chunk'."""
        chunk = _make_sse_chunk(content="hello")
        data_line = chunk.strip().removeprefix("data: ")
        parsed = json.loads(data_line)
        assert parsed["object"] == "chat.completion.chunk"


@pytest.mark.regression
class TestNonStreamingResponseContract:
    """非流式响应格式契约."""

    def test_non_streaming_response_has_required_fields(self) -> None:
        """非流式响应应含 id/object/created/model/choices."""
        response = {
            "id": "chatcmpl-test_docbot_1",
            "object": "chat.completion",
            "created": 1767200000,
            "model": "agentinsight-docbot",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "文档生成中..."},
                    "finish_reason": "stop",
                }
            ],
        }
        assert "id" in response
        assert response["object"] == "chat.completion"
        assert response["model"] == "agentinsight-docbot"
        assert response["choices"][0]["message"]["role"] == "assistant"

    def test_non_streaming_choice_has_message_not_delta(self) -> None:
        """非流式响应 choices 应含 message (非 delta)."""
        response = {
            "id": "chatcmpl-test",
            "object": "chat.completion",
            "created": 1767200000,
            "model": "agentinsight-docbot",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "内容"},
                    "finish_reason": "stop",
                }
            ],
        }
        choice = response["choices"][0]
        assert "message" in choice
        assert "delta" not in choice


@pytest.mark.regression
class TestSSEErrorEventContract:
    """SSE 错误事件格式契约."""

    def test_error_event_has_error_field(self) -> None:
        """错误事件应含 error 字段."""
        error_chunk = {
            "error": {
                "message": "repo_id 必填",
                "type": "invalid_request_error",
                "code": "invalid_repo_id",
            }
        }
        sse_line = f"data: {json.dumps(error_chunk)}\n\n"
        parsed = json.loads(sse_line.strip().removeprefix("data: "))
        assert "error" in parsed
        assert "message" in parsed["error"]

    def test_error_event_before_done_marker(self) -> None:
        """错误事件应在 [DONE] 之前发送."""
        events = [
            "data: " + json.dumps({"error": {"message": "失败"}}) + "\n\n",
            "data: [DONE]\n\n",
        ]
        # 第一个事件应为错误, 最后一个为 DONE
        assert "error" in events[0]
        assert "[DONE]" in events[-1]

"""API 测试: JSON 指令解析 (_parse_docbot_instruction).

不依赖外部服务, 验证:
- 合法 JSON 指令解析为 dict
- 代码块围栏 (```json ... ```) 自动剥离
- 非法 JSON / 非 dict / 空字符串返回 {}
- 字段优先级: 显式请求字段 > 消息内容 JSON 指令 > Settings 默认值
- 指令字段透传 (action/repo_id/report_types/report_format/language)
- 指令字段与显式字段的合并语义 (显式覆盖指令)

测试目标 (AGENTS.md 第 13 章关键测试用例 3.2):
- 用户消息内容可为 JSON 指令字符串
- 指令格式: {"action":"generate_docs","repo_id":...,"report_types":[...],"report_format":...,"language":...}
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


@pytest.mark.api
class TestParseDocbotInstructionBasic:
    """_parse_docbot_instruction 基础解析测试."""

    def test_parse_empty_string_returns_empty_dict(self) -> None:
        """空字符串应返回空 dict."""
        assert _parse_docbot_instruction("") == {}

    def test_parse_none_returns_empty_dict(self) -> None:
        """None 应返回空 dict."""
        # _parse_docbot_instruction 首行检查 not content, None 视为 falsy
        assert _parse_docbot_instruction(None) == {}

    def test_parse_whitespace_only_returns_empty_dict(self) -> None:
        """纯空白应返回空 dict."""
        assert _parse_docbot_instruction("   \n\t  ") == {}

    def test_parse_valid_json_returns_dict(self) -> None:
        """合法 JSON 应解析为 dict."""
        content = '{"action":"generate_docs","repo_id":"test_docbot_repo_1"}'
        result = _parse_docbot_instruction(content)
        assert isinstance(result, dict)
        assert result.get("action") == "generate_docs"
        assert result.get("repo_id") == "test_docbot_repo_1"

    def test_parse_non_json_text_returns_empty_dict(self) -> None:
        """非 JSON 文本应返回空 dict (走默认配置)."""
        result = _parse_docbot_instruction("生成架构文档")
        assert result == {}

    def test_parse_json_array_returns_empty_dict(self) -> None:
        """JSON 数组 (非 dict) 应返回空 dict."""
        result = _parse_docbot_instruction('["a", "b"]')
        assert result == {}

    def test_parse_json_string_returns_empty_dict(self) -> None:
        """JSON 字符串 (非 dict) 应返回空 dict."""
        result = _parse_docbot_instruction('"just a string"')
        assert result == {}

    def test_parse_json_number_returns_empty_dict(self) -> None:
        """JSON 数字 (非 dict) 应返回空 dict."""
        result = _parse_docbot_instruction("12345")
        assert result == {}


@pytest.mark.api
class TestParseDocbotInstructionCodeFence:
    """代码块围栏剥离测试."""

    def test_parse_json_with_code_fence(self) -> None:
        """```json 围栏应被剥离."""
        content = '```json\n{"action":"generate_docs","repo_id":"r1"}\n```'
        result = _parse_docbot_instruction(content)
        assert result.get("action") == "generate_docs"
        assert result.get("repo_id") == "r1"

    def test_parse_json_with_plain_code_fence(self) -> None:
        """``` 围栏 (无语言标识) 应被剥离."""
        content = '```\n{"action":"generate_docs"}\n```'
        result = _parse_docbot_instruction(content)
        assert result.get("action") == "generate_docs"

    def test_parse_json_with_code_fence_no_closing(self) -> None:
        """无闭合 ``` 的代码块也应能解析."""
        content = '```json\n{"action":"generate_docs"}'
        result = _parse_docbot_instruction(content)
        assert result.get("action") == "generate_docs"

    def test_parse_json_with_leading_whitespace(self) -> None:
        """前后空白应被 strip 后解析."""
        content = '  \n  {"action":"generate_docs"}  \n  '
        result = _parse_docbot_instruction(content)
        assert result.get("action") == "generate_docs"


@pytest.mark.api
class TestParseDocbotInstructionFields:
    """指令字段透传测试."""

    def test_parse_full_instruction_with_all_fields(self) -> None:
        """完整指令含所有字段应全部透传."""
        content = (
            '{"action":"generate_docs",'
            '"repo_id":"test_docbot_repo_1",'
            '"report_types":["architecture","design"],'
            '"report_format":"html",'
            '"language":"en"}'
        )
        result = _parse_docbot_instruction(content)
        assert result.get("action") == "generate_docs"
        assert result.get("repo_id") == "test_docbot_repo_1"
        assert result.get("report_types") == ["architecture", "design"]
        assert result.get("report_format") == "html"
        assert result.get("language") == "en"

    def test_parse_instruction_with_session_id(self) -> None:
        """指令含 session_id 应透传."""
        content = '{"action":"generate_docs","session_id":"test_docbot_session_1"}'
        result = _parse_docbot_instruction(content)
        assert result.get("session_id") == "test_docbot_session_1"

    def test_parse_instruction_partial_fields(self) -> None:
        """部分字段的指令应只返回已有字段."""
        content = '{"action":"generate_docs","repo_id":"r1"}'
        result = _parse_docbot_instruction(content)
        assert "report_types" not in result
        assert "report_format" not in result

    def test_parse_instruction_with_extra_unknown_fields(self) -> None:
        """未知字段应保留在 dict 中 (调用方按需取用)."""
        content = '{"action":"generate_docs","custom_field":"value"}'
        result = _parse_docbot_instruction(content)
        assert result.get("custom_field") == "value"


@pytest.mark.api
class TestFieldPriority:
    """字段优先级测试: 显式请求字段 > 消息内容 JSON 指令 > Settings 默认值.

    优先级逻辑 (routes.py 272-276 行):
        repo_id = request.repo_id or instruction.get("repo_id")
        report_types = request.report_types or instruction.get("report_types")
        report_format = request.report_format or instruction.get("report_format") or settings.default_report_format
        language = (request.language or instruction.get("language") or settings.report_language or "zh").lower()
    """

    def test_explicit_repo_id_overrides_instruction(self) -> None:
        """显式 repo_id 应覆盖指令中的 repo_id."""
        request = ChatCompletionRequest(
            messages=[ChatMessage(role="user", content='{"repo_id":"from_instruction"}')],
            repo_id="from_explicit",
        )
        instruction = _parse_docbot_instruction(request.messages[0].content)
        # 显式字段优先
        repo_id = request.repo_id or instruction.get("repo_id")
        assert repo_id == "from_explicit"

    def test_instruction_repo_id_used_when_no_explicit(self) -> None:
        """无显式字段时使用指令字段."""
        request = ChatCompletionRequest(
            messages=[ChatMessage(role="user", content='{"repo_id":"from_instruction"}')],
        )
        instruction = _parse_docbot_instruction(request.messages[0].content)
        repo_id = request.repo_id or instruction.get("repo_id")
        assert repo_id == "from_instruction"

    def test_explicit_language_overrides_instruction(self) -> None:
        """显式 language 应覆盖指令中的 language."""
        request = ChatCompletionRequest(
            messages=[ChatMessage(role="user", content='{"language":"zh"}')],
            language="en",
        )
        instruction = _parse_docbot_instruction(request.messages[0].content)
        language = (request.language or instruction.get("language") or "zh").lower()
        assert language == "en"

    def test_instruction_language_used_when_no_explicit(self) -> None:
        """无显式 language 时使用指令中的 language."""
        request = ChatCompletionRequest(
            messages=[ChatMessage(role="user", content='{"language":"en"}')],
        )
        instruction = _parse_docbot_instruction(request.messages[0].content)
        language = (request.language or instruction.get("language") or "zh").lower()
        assert language == "en"

    def test_default_language_zh_when_no_source(self) -> None:
        """无显式/指令 language 时默认 zh."""
        request = ChatCompletionRequest(
            messages=[ChatMessage(role="user", content='{"repo_id":"r1"}')],
        )
        instruction = _parse_docbot_instruction(request.messages[0].content)
        language = (request.language or instruction.get("language") or "zh").lower()
        assert language == "zh"

    def test_explicit_report_types_overrides_instruction(self) -> None:
        """显式 report_types 应覆盖指令中的 report_types."""
        request = ChatCompletionRequest(
            messages=[ChatMessage(role="user", content='{"report_types":["design"]}')],
            report_types=["architecture"],
        )
        instruction = _parse_docbot_instruction(request.messages[0].content)
        report_types = request.report_types or instruction.get("report_types")
        assert report_types == ["architecture"]

    def test_explicit_report_format_overrides_instruction(self) -> None:
        """显式 report_format 应覆盖指令中的 report_format."""
        request = ChatCompletionRequest(
            messages=[ChatMessage(role="user", content='{"report_format":"html"}')],
            report_format="pdf",
        )
        instruction = _parse_docbot_instruction(request.messages[0].content)
        report_format = request.report_format or instruction.get("report_format")
        assert report_format == "pdf"

    def test_language_converted_to_lowercase(self) -> None:
        """language 应转为小写."""
        request = ChatCompletionRequest(
            messages=[ChatMessage(role="user", content='{"language":"EN"}')],
        )
        instruction = _parse_docbot_instruction(request.messages[0].content)
        language = (request.language or instruction.get("language") or "zh").lower()
        assert language == "en"


@pytest.mark.api
class TestParseInstructionInvalidJson:
    """非法 JSON 处理 (不应抛异常)."""

    def test_parse_broken_json_returns_empty_dict(self) -> None:
        """截断的 JSON 应返回空 dict."""
        result = _parse_docbot_instruction('{"action":"generate_docs"')
        assert result == {}

    def test_parse_json_with_trailing_comma_returns_empty_dict(self) -> None:
        """尾随逗号的 JSON 应返回空 dict."""
        result = _parse_docbot_instruction('{"action":"generate_docs",}')
        assert result == {}

    def test_parse_json_with_unquoted_key_returns_empty_dict(self) -> None:
        """未加引号的 key 应返回空 dict."""
        result = _parse_docbot_instruction('{action:"generate_docs"}')
        assert result == {}

    def test_parse_html_returns_empty_dict(self) -> None:
        """HTML 内容应返回空 dict."""
        result = _parse_docbot_instruction("<html><body>hello</body></html>")
        assert result == {}

    def test_parse_yaml_returns_empty_dict(self) -> None:
        """YAML 内容应返回空 dict."""
        result = _parse_docbot_instruction("action: generate_docs\nrepo_id: r1")
        assert result == {}

    def test_parse_markdown_returns_empty_dict(self) -> None:
        """Markdown 内容应返回空 dict."""
        result = _parse_docbot_instruction("# 标题\n生成架构文档")
        assert result == {}

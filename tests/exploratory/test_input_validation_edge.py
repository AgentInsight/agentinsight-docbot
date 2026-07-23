"""探索性测试: 输入校验边界场景.

不依赖外部服务, 探索性验证:
- 超长 repo_id / report_types / language 输入
- 特殊字符 (Unicode/emoji/SQL 注入尝试)
- 空列表 / 嵌套结构 / None 值
- Pydantic 校验边界 (min_length/max_length)
- JSON 指令含嵌套对象 / 数组
- 用户消息含代码块 / 多语言混合

探索性目标 (AGENTS.md 第 13 章探索性测试):
- 发现未预见的输入组合
- 不依赖 --run-external
- 用 mock 替代外部服务
"""
from __future__ import annotations

import json
from contextlib import contextmanager
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from src.agents.docbot.coordinator import CoordinatorA
from src.api.routes import (
    ChatCompletionRequest,
    ChatMessage,
    _parse_docbot_instruction,
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


def _make_mock_settings() -> MagicMock:
    """构造 mock Settings."""
    settings = MagicMock()
    settings.agent_name = "agentinsight-docbot"
    settings.agent_id = "agentinsight-docbot"
    settings.git_credential_key = "test" * 32
    settings.max_concurrent_reports = 3
    settings.max_chapters_per_report = 20
    settings.max_revisions_per_chapter = 3
    settings.default_report_format = "markdown"
    settings.report_language = "zh"
    return settings


@pytest.mark.exploratory
class TestRepoIdEdgeCases:
    """repo_id 边界场景."""

    async def test_repo_id_with_special_characters(self) -> None:
        """repo_id 含特殊字符应能解析 (coordinator 不限制字符集)."""
        coordinator = CoordinatorA()
        state = {
            "messages": [{"role": "user", "content": '{"action":"generate_docs","repo_id":"repo-with-dash_under.dot","report_types":["architecture"]}'}],
            "session_id": "test_docbot_session_1",
            "user_id": "test_docbot_user_1",
            "agent_id": "agentinsight-docbot",
        }

        with patch("src.agents.docbot.coordinator.trace_agent") as mock_trace, \
             _mock_repo_db():
            mock_cm = MagicMock()
            mock_cm.__aenter__ = AsyncMock(return_value=mock_cm)
            mock_cm.__aexit__ = AsyncMock(return_value=None)
            mock_trace.return_value = mock_cm

            delta = await coordinator.run(state, settings=_make_mock_settings())

        assert "errors" not in delta or not delta["errors"]
        assert delta.get("repo_id") == "repo-with-dash_under.dot"

    async def test_repo_id_with_unicode(self) -> None:
        """repo_id 含 Unicode 字符应能解析."""
        coordinator = CoordinatorA()
        state = {
            "messages": [{"role": "user", "content": '{"action":"generate_docs","repo_id":"测试仓库","report_types":["architecture"]}'}],
            "session_id": "test_docbot_session_1",
            "user_id": "test_docbot_user_1",
            "agent_id": "agentinsight-docbot",
        }

        with patch("src.agents.docbot.coordinator.trace_agent") as mock_trace, \
             _mock_repo_db():
            mock_cm = MagicMock()
            mock_cm.__aenter__ = AsyncMock(return_value=mock_cm)
            mock_cm.__aexit__ = AsyncMock(return_value=None)
            mock_trace.return_value = mock_cm

            delta = await coordinator.run(state, settings=_make_mock_settings())

        assert delta.get("repo_id") == "测试仓库"

    async def test_empty_repo_id_rejected(self) -> None:
        """空 repo_id 应被校验拒绝."""
        coordinator = CoordinatorA()
        state = {
            "messages": [{"role": "user", "content": '{"action":"generate_docs","repo_id":"","report_types":["architecture"]}'}],
            "session_id": "test_docbot_session_1",
            "user_id": "test_docbot_user_1",
            "agent_id": "agentinsight-docbot",
        }

        with patch("src.agents.docbot.coordinator.trace_agent") as mock_trace, \
             _mock_repo_db():
            mock_cm = MagicMock()
            mock_cm.__aenter__ = AsyncMock(return_value=mock_cm)
            mock_cm.__aexit__ = AsyncMock(return_value=None)
            mock_trace.return_value = mock_cm

            delta = await coordinator.run(state, settings=_make_mock_settings())

        assert "errors" in delta
        assert any("repo_id" in e for e in delta["errors"])

    async def test_missing_repo_id_rejected(self) -> None:
        """缺 repo_id 字段应被校验拒绝."""
        coordinator = CoordinatorA()
        state = {
            "messages": [{"role": "user", "content": '{"action":"generate_docs","report_types":["architecture"]}'}],
            "session_id": "test_docbot_session_1",
            "user_id": "test_docbot_user_1",
            "agent_id": "agentinsight-docbot",
        }

        with patch("src.agents.docbot.coordinator.trace_agent") as mock_trace, \
             _mock_repo_db():
            mock_cm = MagicMock()
            mock_cm.__aenter__ = AsyncMock(return_value=mock_cm)
            mock_cm.__aexit__ = AsyncMock(return_value=None)
            mock_trace.return_value = mock_cm

            delta = await coordinator.run(state, settings=_make_mock_settings())

        assert "errors" in delta
        assert any("repo_id" in e for e in delta["errors"])

    async def test_repo_id_non_string_rejected(self) -> None:
        """repo_id 为非字符串 (数字) 应被校验拒绝."""
        coordinator = CoordinatorA()
        state = {
            "messages": [{"role": "user", "content": '{"action":"generate_docs","repo_id":12345,"report_types":["architecture"]}'}],
            "session_id": "test_docbot_session_1",
            "user_id": "test_docbot_user_1",
            "agent_id": "agentinsight-docbot",
        }

        with patch("src.agents.docbot.coordinator.trace_agent") as mock_trace, \
             _mock_repo_db():
            mock_cm = MagicMock()
            mock_cm.__aenter__ = AsyncMock(return_value=mock_cm)
            mock_cm.__aexit__ = AsyncMock(return_value=None)
            mock_trace.return_value = mock_cm

            delta = await coordinator.run(state, settings=_make_mock_settings())

        assert "errors" in delta


@pytest.mark.exploratory
class TestReportTypesEdgeCases:
    """report_types 边界场景."""

    async def test_empty_report_types_rejected(self) -> None:
        """空 report_types 列表应被校验拒绝."""
        coordinator = CoordinatorA()
        state = {
            "messages": [{"role": "user", "content": '{"action":"generate_docs","repo_id":"r1","report_types":[]}'}],
            "session_id": "test_docbot_session_1",
            "user_id": "test_docbot_user_1",
            "agent_id": "agentinsight-docbot",
        }

        with patch("src.agents.docbot.coordinator.trace_agent") as mock_trace, \
             _mock_repo_db():
            mock_cm = MagicMock()
            mock_cm.__aenter__ = AsyncMock(return_value=mock_cm)
            mock_cm.__aexit__ = AsyncMock(return_value=None)
            mock_trace.return_value = mock_cm

            delta = await coordinator.run(state, settings=_make_mock_settings())

        assert "errors" in delta
        assert any("report_types" in e for e in delta["errors"])

    async def test_too_many_report_types_rejected(self) -> None:
        """超过 8 种 report_type 应被校验拒绝."""
        coordinator = CoordinatorA()
        # 9 种类型 (含 1 个无效, 但数量先超限)
        nine_types = [
            "architecture", "design", "requirements", "testcase",
            "optimization", "performance", "defect", "api_doc", "extra",
        ]
        state = {
            "messages": [{"role": "user", "content": '{"action":"generate_docs","repo_id":"r1","report_types":' + json.dumps(nine_types) + '}'}],
            "session_id": "test_docbot_session_1",
            "user_id": "test_docbot_user_1",
            "agent_id": "agentinsight-docbot",
        }

        with patch("src.agents.docbot.coordinator.trace_agent") as mock_trace, \
             _mock_repo_db():
            mock_cm = MagicMock()
            mock_cm.__aenter__ = AsyncMock(return_value=mock_cm)
            mock_cm.__aexit__ = AsyncMock(return_value=None)
            mock_trace.return_value = mock_cm

            delta = await coordinator.run(state, settings=_make_mock_settings())

        assert "errors" in delta
        # 应含数量超限错误
        assert any("too_many" in e for e in delta["errors"])

    async def test_invalid_report_type_in_list_rejected(self) -> None:
        """report_types 含无效类型应被校验拒绝."""
        coordinator = CoordinatorA()
        state = {
            "messages": [{"role": "user", "content": '{"action":"generate_docs","repo_id":"r1","report_types":["architecture","invalid_type"]}'}],
            "session_id": "test_docbot_session_1",
            "user_id": "test_docbot_user_1",
            "agent_id": "agentinsight-docbot",
        }

        with patch("src.agents.docbot.coordinator.trace_agent") as mock_trace, \
             _mock_repo_db():
            mock_cm = MagicMock()
            mock_cm.__aenter__ = AsyncMock(return_value=mock_cm)
            mock_cm.__aexit__ = AsyncMock(return_value=None)
            mock_trace.return_value = mock_cm

            delta = await coordinator.run(state, settings=_make_mock_settings())

        assert "errors" in delta
        assert any("invalid_report_types" in e for e in delta["errors"])

    async def test_all_8_valid_report_types_accepted(self) -> None:
        """8 种全部 report_type 应被接受 (边界值)."""
        coordinator = CoordinatorA()
        all_types = [
            "architecture", "design", "requirements", "testcase",
            "optimization", "performance", "defect", "api_doc",
        ]
        state = {
            "messages": [{"role": "user", "content": json.dumps({"action": "generate_docs", "repo_id": "r1", "report_types": all_types})}],
            "session_id": "test_docbot_session_1",
            "user_id": "test_docbot_user_1",
            "agent_id": "agentinsight-docbot",
        }

        with patch("src.agents.docbot.coordinator.trace_agent") as mock_trace, \
             _mock_repo_db():
            mock_cm = MagicMock()
            mock_cm.__aenter__ = AsyncMock(return_value=mock_cm)
            mock_cm.__aexit__ = AsyncMock(return_value=None)
            mock_trace.return_value = mock_cm

            delta = await coordinator.run(state, settings=_make_mock_settings())

        assert "errors" not in delta or not delta["errors"]
        assert delta.get("report_types") == all_types


@pytest.mark.exploratory
class TestInstructionEdgeCases:
    """JSON 指令边界场景."""

    def test_instruction_with_nested_object(self) -> None:
        """指令含嵌套对象应能解析."""
        content = '{"action":"generate_docs","repo_id":"r1","metadata":{"key":"value"}}'
        result = _parse_docbot_instruction(content)
        assert result.get("metadata") == {"key": "value"}

    def test_instruction_with_array_field(self) -> None:
        """指令含数组字段应能解析."""
        content = '{"action":"generate_docs","repo_id":"r1","tags":["a","b","c"]}'
        result = _parse_docbot_instruction(content)
        assert result.get("tags") == ["a", "b", "c"]

    def test_instruction_with_emoji(self) -> None:
        """指令含 emoji 应能解析."""
        content = '{"action":"generate_docs","repo_id":"r1","note":"📄 文档"}'
        result = _parse_docbot_instruction(content)
        assert result.get("note") == "📄 文档"

    def test_instruction_with_sql_injection_attempt(self) -> None:
        """SQL 注入尝试应被当作普通字符串处理 (不执行)."""
        content = '{"action":"generate_docs","repo_id":"r1 OR 1=1; DROP TABLE users; --"}'
        result = _parse_docbot_instruction(content)
        # 仅解析为字符串, 不执行 SQL
        assert "DROP TABLE" in result.get("repo_id", "")

    def test_instruction_with_xss_attempt(self) -> None:
        """XSS 尝试应被当作普通字符串处理."""
        content = '{"action":"generate_docs","repo_id":"<script>alert(1)</script>"}'
        result = _parse_docbot_instruction(content)
        assert "<script>" in result.get("repo_id", "")

    def test_instruction_with_long_string(self) -> None:
        """超长字符串应能解析 (无长度限制)."""
        long_value = "x" * 10000
        content = f'{{"action":"generate_docs","repo_id":"{long_value}"}}'
        result = _parse_docbot_instruction(content)
        assert len(result.get("repo_id", "")) == 10000


@pytest.mark.exploratory
class TestMessageEdgeCases:
    """用户消息边界场景."""

    def test_message_with_only_whitespace_content(self) -> None:
        """纯空白消息内容应被解析为空 dict."""
        result = _parse_docbot_instruction("   \n\t  ")
        assert result == {}

    def test_message_with_multiline_json(self) -> None:
        """多行 JSON 应能解析."""
        content = '''{
            "action": "generate_docs",
            "repo_id": "r1",
            "report_types": ["architecture"]
        }'''
        result = _parse_docbot_instruction(content)
        assert result.get("action") == "generate_docs"
        assert result.get("repo_id") == "r1"

    def test_message_with_code_block_json(self) -> None:
        """代码块包裹的 JSON 应能解析."""
        content = '```json\n{"action":"generate_docs","repo_id":"r1"}\n```'
        result = _parse_docbot_instruction(content)
        assert result.get("action") == "generate_docs"

    def test_message_with_mixed_languages(self) -> None:
        """含中英日混合的 JSON 值应能解析."""
        content = '{"action":"generate_docs","repo_id":"r1","note":"中文 English 日本語"}'
        result = _parse_docbot_instruction(content)
        assert result.get("note") == "中文 English 日本語"

    async def test_empty_messages_rejected_by_coordinator(self) -> None:
        """空 messages 列表应被 coordinator 拒绝."""
        coordinator = CoordinatorA()
        state = {
            "messages": [],
            "session_id": "test_docbot_session_1",
            "user_id": "test_docbot_user_1",
            "agent_id": "agentinsight-docbot",
        }

        with patch("src.agents.docbot.coordinator.trace_agent") as mock_trace, \
             _mock_repo_db():
            mock_cm = MagicMock()
            mock_cm.__aenter__ = AsyncMock(return_value=mock_cm)
            mock_cm.__aexit__ = AsyncMock(return_value=None)
            mock_trace.return_value = mock_cm

            delta = await coordinator.run(state, settings=_make_mock_settings())

        assert "errors" in delta
        assert delta["errors"] == ["empty_messages"]

    async def test_non_dict_instruction_rejected(self) -> None:
        """非 dict 的 JSON 指令 (数组/字符串/数字) 应被拒绝."""
        coordinator = CoordinatorA()
        state = {
            "messages": [{"role": "user", "content": '["not", "a", "dict"]'}],
            "session_id": "test_docbot_session_1",
            "user_id": "test_docbot_user_1",
            "agent_id": "agentinsight-docbot",
        }

        with patch("src.agents.docbot.coordinator.trace_agent") as mock_trace, \
             _mock_repo_db():
            mock_cm = MagicMock()
            mock_cm.__aenter__ = AsyncMock(return_value=mock_cm)
            mock_cm.__aexit__ = AsyncMock(return_value=None)
            mock_trace.return_value = mock_cm

            delta = await coordinator.run(state, settings=_make_mock_settings())

        assert "errors" in delta
        assert any("not_dict" in e for e in delta["errors"])

    async def test_unsupported_action_rejected(self) -> None:
        """非 generate_docs 的 action 应被拒绝."""
        coordinator = CoordinatorA()
        state = {
            "messages": [{"role": "user", "content": '{"action":"search","repo_id":"r1","report_types":["architecture"]}'}],
            "session_id": "test_docbot_session_1",
            "user_id": "test_docbot_user_1",
            "agent_id": "agentinsight-docbot",
        }

        with patch("src.agents.docbot.coordinator.trace_agent") as mock_trace, \
             _mock_repo_db():
            mock_cm = MagicMock()
            mock_cm.__aenter__ = AsyncMock(return_value=mock_cm)
            mock_cm.__aexit__ = AsyncMock(return_value=None)
            mock_trace.return_value = mock_cm

            delta = await coordinator.run(state, settings=_make_mock_settings())

        assert "errors" in delta
        assert any("unsupported_action" in e for e in delta["errors"])

    async def test_invalid_json_rejected(self) -> None:
        """非法 JSON 应被拒绝."""
        coordinator = CoordinatorA()
        state = {
            "messages": [{"role": "user", "content": 'not a json string'}],
            "session_id": "test_docbot_session_1",
            "user_id": "test_docbot_user_1",
            "agent_id": "agentinsight-docbot",
        }

        with patch("src.agents.docbot.coordinator.trace_agent") as mock_trace, \
             _mock_repo_db():
            mock_cm = MagicMock()
            mock_cm.__aenter__ = AsyncMock(return_value=mock_cm)
            mock_cm.__aexit__ = AsyncMock(return_value=None)
            mock_trace.return_value = mock_cm

            delta = await coordinator.run(state, settings=_make_mock_settings())

        assert "errors" in delta
        assert any("invalid_instruction" in e for e in delta["errors"])

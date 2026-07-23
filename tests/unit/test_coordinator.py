"""单元测试: coordinator_a 派发逻辑 + language 校验.

测试目标 (见 AGENTS.md 第 13 章关键测试用例 1):
- coordinator_a 派发逻辑 (mock 子图) + language 校验 (仅 zh/en)
- 解析 JSON 指令 (action=generate_docs)
- 校验 repo_id / report_types / report_format / language
"""
from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.docbot.coordinator import (
    _VALID_LANGUAGES,
    _VALID_REPORT_FORMATS,
    _VALID_REPORT_TYPES,
    CoordinatorA,
)


def _mock_repo_db():
    """构造 mock 上下文: 让 coordinator_a 的 repo_not_found 检查通过.

    coordinator 校验通过后会查 user_git_repos 表加载 repo_config,
    单元测试不应依赖真实 Postgres, 这里 patch 三个 DB 入口.
    """
    mock_row = {
        "id": "repo-123",
        "agent_id": "agentinsight-docbot",
        "user_id": "user1",
        "repo_name": "test-repo",
        "platform": "github",
        "repo_url": "https://github.com/test/repo.git",
        "default_branch": "main",
        "auth_type": "none",
        "encrypted_token": None,
        "encrypted_username": None,
        "encrypted_password": None,
        "encrypted_ssh_key": None,
        "ssh_passphrase": None,
        "clone_depth": 0,
        "enabled": True,
    }
    mock_repo_config = {
        "repo_url": "https://github.com/test/repo.git",
        "default_branch": "main",
        "clone_depth": 0,
        "auth_type": "none",
        "token": None,
        "username": None,
        "password": None,
        "ssh_key": None,
        "ssh_passphrase": None,
    }
    return (
        patch("src.memory.db_initializer.get_pool", AsyncMock(return_value=MagicMock())),
        patch("src.api.repo_routes._fetch_repo_row", AsyncMock(return_value=mock_row)),
        patch("src.api.repo_routes._load_repo_config", return_value=mock_repo_config),
    )


class TestCoordinatorAValidation:
    """CoordinatorA 参数校验测试."""

    @pytest.fixture
    def coordinator(self) -> CoordinatorA:
        """提供 CoordinatorA 实例 (无 settings 注入)."""
        return CoordinatorA()

    @pytest.fixture
    def valid_instruction(self) -> dict[str, Any]:
        """提供合法 generate_docs 指令."""
        return {
            "action": "generate_docs",
            "repo_id": "repo-123",
            "report_types": ["architecture"],
            "report_format": "markdown",
            "language": "zh",
        }

    @pytest.mark.asyncio
    async def test_valid_instruction_returns_delta(
        self, coordinator: CoordinatorA, valid_instruction: dict
    ) -> None:
        """合法指令返回正确 delta."""
        state = {
            "messages": [{"role": "user", "content": json.dumps(valid_instruction)}],
            "session_id": "session1",
            "user_id": "user1",
            "agent_id": "agentinsight-docbot",
        }
        # mock DB: coordinator 校验通过后会查 user_git_repos 表加载 repo_config
        p_pool, p_fetch, p_load = _mock_repo_db()
        with p_pool, p_fetch, p_load:
            result = await coordinator.run(state)
        assert "errors" not in result
        assert result["repo_id"] == "repo-123"
        assert result["report_types"] == ["architecture"]
        assert result["report_format"] == "markdown"
        assert result["language"] == "zh"
        assert result["iteration_count"] == 1

    @pytest.mark.asyncio
    async def test_empty_messages_returns_error(self, coordinator: CoordinatorA) -> None:
        """空 messages 返回 empty_messages 错误."""
        state: dict[str, Any] = {"messages": []}
        result = await coordinator.run(state)
        assert "errors" in result
        assert "empty_messages" in result["errors"]

    @pytest.mark.asyncio
    async def test_invalid_json_returns_error(self, coordinator: CoordinatorA) -> None:
        """非 JSON 内容返回 invalid_instruction 错误."""
        state = {"messages": [{"role": "user", "content": "not json"}]}
        result = await coordinator.run(state)
        assert "errors" in result
        assert any("invalid_instruction" in e for e in result["errors"])

    @pytest.mark.asyncio
    async def test_unsupported_action_returns_error(
        self, coordinator: CoordinatorA
    ) -> None:
        """非 generate_docs action 返回 unsupported_action 错误."""
        state = {
            "messages": [
                {"role": "user", "content": json.dumps({"action": "unknown_action"})}
            ]
        }
        result = await coordinator.run(state)
        assert "errors" in result
        assert any("unsupported_action" in e for e in result["errors"])

    @pytest.mark.asyncio
    async def test_missing_repo_id_returns_error(
        self, coordinator: CoordinatorA, valid_instruction: dict
    ) -> None:
        """缺少 repo_id 返回 missing_or_invalid_repo_id 错误."""
        valid_instruction.pop("repo_id")
        state = {
            "messages": [
                {"role": "user", "content": json.dumps(valid_instruction)}
            ]
        }
        result = await coordinator.run(state)
        assert "errors" in result
        assert any("missing_or_invalid_repo_id" in e for e in result["errors"])

    @pytest.mark.asyncio
    async def test_missing_report_types_returns_error(
        self, coordinator: CoordinatorA, valid_instruction: dict
    ) -> None:
        """缺少 report_types 返回 missing_or_invalid_report_types 错误."""
        valid_instruction.pop("report_types")
        state = {
            "messages": [
                {"role": "user", "content": json.dumps(valid_instruction)}
            ]
        }
        result = await coordinator.run(state)
        assert "errors" in result
        assert any("missing_or_invalid_report_types" in e for e in result["errors"])

    @pytest.mark.asyncio
    async def test_invalid_report_type_returns_error(
        self, coordinator: CoordinatorA, valid_instruction: dict
    ) -> None:
        """非法 report_type 返回 invalid_report_types 错误."""
        valid_instruction["report_types"] = ["invalid_type"]
        state = {
            "messages": [
                {"role": "user", "content": json.dumps(valid_instruction)}
            ]
        }
        result = await coordinator.run(state)
        assert "errors" in result
        assert any("invalid_report_types" in e for e in result["errors"])

    @pytest.mark.asyncio
    async def test_invalid_report_format_returns_error(
        self, coordinator: CoordinatorA, valid_instruction: dict
    ) -> None:
        """非法 report_format 返回 invalid_report_format 错误."""
        valid_instruction["report_format"] = "invalid_format"
        state = {
            "messages": [
                {"role": "user", "content": json.dumps(valid_instruction)}
            ]
        }
        result = await coordinator.run(state)
        assert "errors" in result
        assert any("invalid_report_format" in e for e in result["errors"])


class TestLanguageValidation:
    """language 字段校验测试 (仅 zh/en)."""

    @pytest.mark.asyncio
    async def test_language_zh_accepted(self) -> None:
        """language='zh' 通过校验."""
        coordinator = CoordinatorA()
        instruction = {
            "action": "generate_docs",
            "repo_id": "r1",
            "report_types": ["architecture"],
            "report_format": "markdown",
            "language": "zh",
        }
        state = {
            "messages": [{"role": "user", "content": json.dumps(instruction)}],
            "user_id": "user1",
            "agent_id": "agentinsight-docbot",
        }
        # mock DB: coordinator 校验通过后会查 user_git_repos 表加载 repo_config
        p_pool, p_fetch, p_load = _mock_repo_db()
        with p_pool, p_fetch, p_load:
            result = await coordinator.run(state)
        assert "errors" not in result
        assert result["language"] == "zh"

    @pytest.mark.asyncio
    async def test_language_en_accepted(self) -> None:
        """language='en' 通过校验."""
        coordinator = CoordinatorA()
        instruction = {
            "action": "generate_docs",
            "repo_id": "r1",
            "report_types": ["architecture"],
            "report_format": "markdown",
            "language": "en",
        }
        state = {
            "messages": [{"role": "user", "content": json.dumps(instruction)}],
            "user_id": "user1",
            "agent_id": "agentinsight-docbot",
        }
        # mock DB: coordinator 校验通过后会查 user_git_repos 表加载 repo_config
        p_pool, p_fetch, p_load = _mock_repo_db()
        with p_pool, p_fetch, p_load:
            result = await coordinator.run(state)
        assert "errors" not in result
        assert result["language"] == "en"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("invalid_lang", ["ja", "fr", "de", "ZH", "En", "", "chinese"])
    async def test_invalid_language_returns_error(self, invalid_lang: str) -> None:
        """非 zh/en 语言返回 invalid_language 错误."""
        coordinator = CoordinatorA()
        instruction = {
            "action": "generate_docs",
            "repo_id": "r1",
            "report_types": ["architecture"],
            "report_format": "markdown",
            "language": invalid_lang,
        }
        state = {"messages": [{"role": "user", "content": json.dumps(instruction)}]}
        result = await coordinator.run(state)
        assert "errors" in result
        assert any("invalid_language" in e for e in result["errors"])

    def test_valid_languages_set(self) -> None:
        """_VALID_LANGUAGES 含 zh/en 两种."""
        assert _VALID_LANGUAGES == frozenset({"zh", "en"})
        assert len(_VALID_LANGUAGES) == 2

    def test_valid_report_types_contains_eight(self) -> None:
        """_VALID_REPORT_TYPES 含 8 种类型."""
        expected = {
            "architecture",
            "design",
            "requirements",
            "testcase",
            "optimization",
            "performance",
            "defect",
            "api_doc",
        }
        assert _VALID_REPORT_TYPES == expected
        assert len(_VALID_REPORT_TYPES) == 8

    def test_valid_report_formats_contains_five(self) -> None:
        """_VALID_REPORT_FORMATS 含 5 种格式."""
        expected = {"markdown", "html", "pdf", "docx", "json"}
        assert _VALID_REPORT_FORMATS == expected
        assert len(_VALID_REPORT_FORMATS) == 5


class TestCoordinatorExtractContent:
    """_extract_content 静态方法测试."""

    def test_extract_from_dict(self) -> None:
        """从 dict 提取 content."""
        msg = {"role": "user", "content": "hello"}
        assert CoordinatorA._extract_content(msg) == "hello"

    def test_extract_from_dict_no_content(self) -> None:
        """dict 缺 content 字段返回空字符串."""
        msg = {"role": "user"}
        assert CoordinatorA._extract_content(msg) == ""

    def test_extract_from_object(self) -> None:
        """从对象提取 content (兼容 langchain BaseMessage)."""
        obj = MagicMock()
        obj.content = "hello from object"
        assert CoordinatorA._extract_content(obj) == "hello from object"

    def test_extract_from_object_no_content(self) -> None:
        """对象无 content 属性返回空字符串."""
        obj = MagicMock()
        del obj.content
        # MagicMock 删除属性后访问会自动创建 MagicMock, 这里测试 None 情况
        # 实际 _extract_content 用 getattr(message, "content", None)
        # 验证: 如果 content is None, 返回 ""
        # 但 MagicMock 自动创建新 MagicMock 而不是 None
        # 这里我们用一个简单的对象测试
        class Empty:
            pass

        result = CoordinatorA._extract_content(Empty())
        assert result == ""

"""性能测试: API 响应时间 (mock 化基准测试).

不依赖外部服务, 用 mock 测量纯函数耗时:
- _parse_docbot_instruction 解析延迟 (单次/批量)
- coordinator_a 校验延迟 (单次/批量)
- RepoResponse 模型序列化延迟
- _row_to_response 转换延迟
- Pydantic 模型校验延迟

性能基线 (参考 perf_baseline_latency_ms):
- /v1/chat/completions 校验逻辑: < 50ms (不含 LLM 调用)
- 模型序列化: < 10ms
- JSON 指令解析: < 5ms

测试目标 (AGENTS.md 第 13 章性能测试):
- 性能基准不依赖 --run-external (mock 外部服务)
- 测量纯函数/纯逻辑耗时
"""
from __future__ import annotations

import asyncio
import time
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.docbot.coordinator import CoordinatorA
from src.api.repo_routes import RepoCreateRequest, _row_to_response
from src.api.routes import ChatCompletionRequest, ChatMessage, _parse_docbot_instruction


# ========== 基线阈值 ==========

_PARSE_INSTRUCTION_BASELINE_MS = 5.0  # JSON 指令解析基线 5ms
_COORDINATOR_VALIDATE_BASELINE_MS = 50.0  # coordinator_a 校验基线 50ms
_REPO_RESPONSE_SERIALIZE_BASELINE_MS = 10.0  # RepoResponse 序列化基线 10ms
_PYDANTIC_VALIDATE_BASELINE_MS = 5.0  # Pydantic 校验基线 5ms


def _make_mock_settings() -> MagicMock:
    """构造 mock Settings."""
    settings = MagicMock()
    settings.agent_name = "agentinsight-docbot"
    settings.agent_id = "agentinsight-docbot"
    settings.git_credential_key = "test" * 32
    return settings


@pytest.mark.performance
class TestParseInstructionPerformance:
    """_parse_docbot_instruction 解析性能."""

    def test_parse_single_instruction_latency(self) -> None:
        """单次 JSON 指令解析延迟应 < 5ms."""
        content = '{"action":"generate_docs","repo_id":"test_docbot_repo_1","report_types":["architecture"]}'
        # 预热
        _parse_docbot_instruction(content)

        # 测量
        iterations = 100
        start = time.perf_counter()
        for _ in range(iterations):
            _parse_docbot_instruction(content)
        elapsed_ms = (time.perf_counter() - start) * 1000
        avg_ms = elapsed_ms / iterations

        assert avg_ms < _PARSE_INSTRUCTION_BASELINE_MS, (
            f"平均解析延迟 {avg_ms:.3f}ms 超过基线 {_PARSE_INSTRUCTION_BASELINE_MS}ms"
        )

    def test_parse_large_instruction_latency(self) -> None:
        """含大量字段的 JSON 解析延迟应 < 10ms."""
        large_types = [
            "architecture", "design", "requirements", "testcase",
            "optimization", "performance", "defect", "api_doc",
        ]
        content = (
            '{"action":"generate_docs","repo_id":"test_docbot_repo_1",'
            '"report_types":' + str(large_types) + ','
            '"report_format":"html","language":"en",'
            '"metadata":{"key1":"value1","key2":"value2"}}'
        )
        # 预热
        _parse_docbot_instruction(content)

        iterations = 50
        start = time.perf_counter()
        for _ in range(iterations):
            _parse_docbot_instruction(content)
        elapsed_ms = (time.perf_counter() - start) * 1000
        avg_ms = elapsed_ms / iterations

        assert avg_ms < 10.0, f"大指令平均解析延迟 {avg_ms:.3f}ms 超过 10ms"

    def test_parse_invalid_json_fast_failure(self) -> None:
        """非法 JSON 解析失败应快速返回 (不抛异常)."""
        invalid_inputs = [
            "not a json",
            "<html>invalid</html>",
            "{broken json",
            "",
        ]
        for content in invalid_inputs:
            start = time.perf_counter()
            result = _parse_docbot_instruction(content)
            elapsed_ms = (time.perf_counter() - start) * 1000
            # 失败应 < 2ms 且返回空 dict
            assert result == {}
            assert elapsed_ms < 2.0


@pytest.mark.performance
class TestCoordinatorPerformance:
    """CoordinatorA 校验性能."""

    async def test_coordinator_validate_single_request_latency(self) -> None:
        """coordinator_a 单次校验延迟应 < 50ms."""
        settings = _make_mock_settings()
        coordinator = CoordinatorA()
        state = {
            "messages": [{"role": "user", "content": '{"action":"generate_docs","repo_id":"test_docbot_repo_1","report_types":["architecture"]}'}],
            "session_id": "test_docbot_session_1",
            "user_id": "test_docbot_user_1",
            "agent_id": "agentinsight-docbot",
        }

        with patch("src.agents.docbot.coordinator.trace_agent") as mock_trace:
            mock_cm = MagicMock()
            mock_cm.__aenter__ = AsyncMock(return_value=mock_cm)
            mock_cm.__aexit__ = AsyncMock(return_value=None)
            mock_trace.return_value = mock_cm

            # 预热
            await coordinator.run(state, settings=settings)

            # 测量
            iterations = 20
            start = time.perf_counter()
            for _ in range(iterations):
                await coordinator.run(state, settings=settings)
            elapsed_ms = (time.perf_counter() - start) * 1000
            avg_ms = elapsed_ms / iterations

        assert avg_ms < _COORDINATOR_VALIDATE_BASELINE_MS, (
            f"coordinator_a 平均校验延迟 {avg_ms:.3f}ms 超过基线 {_COORDINATOR_VALIDATE_BASELINE_MS}ms"
        )

    async def test_coordinator_validate_8_types_not_significantly_slower(self) -> None:
        """8 种 report_type 校验不应比 1 种显著慢 (5x 内)."""
        settings = _make_mock_settings()
        coordinator = CoordinatorA()
        import json

        state_1 = {
            "messages": [{"role": "user", "content": json.dumps({
                "action": "generate_docs", "repo_id": "r1", "report_types": ["architecture"],
            })}],
            "session_id": "test_docbot_session_1",
            "user_id": "test_docbot_user_1",
            "agent_id": "agentinsight-docbot",
        }
        state_8 = {
            "messages": [{"role": "user", "content": json.dumps({
                "action": "generate_docs", "repo_id": "r1",
                "report_types": ["architecture", "design", "requirements", "testcase",
                                 "optimization", "performance", "defect", "api_doc"],
            })}],
            "session_id": "test_docbot_session_1",
            "user_id": "test_docbot_user_1",
            "agent_id": "agentinsight-docbot",
        }

        with patch("src.agents.docbot.coordinator.trace_agent") as mock_trace:
            mock_cm = MagicMock()
            mock_cm.__aenter__ = AsyncMock(return_value=mock_cm)
            mock_cm.__aexit__ = AsyncMock(return_value=None)
            mock_trace.return_value = mock_cm

            # 预热
            await coordinator.run(state_1, settings=settings)
            await coordinator.run(state_8, settings=settings)

            # 测量 1 种类型
            iterations = 20
            start = time.perf_counter()
            for _ in range(iterations):
                await coordinator.run(state_1, settings=settings)
            avg_1 = (time.perf_counter() - start) * 1000 / iterations

            # 测量 8 种类型
            start = time.perf_counter()
            for _ in range(iterations):
                await coordinator.run(state_8, settings=settings)
            avg_8 = (time.perf_counter() - start) * 1000 / iterations

        # 8 种不应比 1 种慢 5x 以上 (校验复杂度应线性)
        assert avg_8 < avg_1 * 5, f"8 种类型 {avg_8:.3f}ms 比 1 种 {avg_1:.3f}ms 慢超过 5x"


@pytest.mark.performance
class TestRepoResponseSerializePerformance:
    """RepoResponse 序列化性能."""

    def test_row_to_response_single_latency(self) -> None:
        """单次 _row_to_response 转换延迟应 < 2ms."""
        from datetime import datetime
        row = {
            "id": "test_docbot_repo_uuid_1",
            "agent_id": "agentinsight-docbot",
            "user_id": "test_docbot_user_1",
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
            "last_synced_at": datetime(2026, 1, 1),
            "last_sync_status": "success",
            "last_sync_error": None,
            "created_at": datetime(2026, 1, 1),
            "updated_at": datetime(2026, 1, 2),
        }

        # 预热
        _row_to_response(row)

        iterations = 100
        start = time.perf_counter()
        for _ in range(iterations):
            _row_to_response(row)
        elapsed_ms = (time.perf_counter() - start) * 1000
        avg_ms = elapsed_ms / iterations

        assert avg_ms < 2.0, f"单次转换延迟 {avg_ms:.3f}ms 超过 2ms"

    def test_row_to_response_model_dump_latency(self) -> None:
        """RepoResponse.model_dump() 序列化延迟应 < 5ms."""
        from datetime import datetime
        row = {
            "id": "test_docbot_repo_uuid_1",
            "agent_id": "agentinsight-docbot",
            "user_id": "test_docbot_user_1",
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
            "last_synced_at": datetime(2026, 1, 1),
            "last_sync_status": "success",
            "last_sync_error": None,
            "created_at": datetime(2026, 1, 1),
            "updated_at": datetime(2026, 1, 2),
        }
        resp = _row_to_response(row)

        iterations = 100
        start = time.perf_counter()
        for _ in range(iterations):
            resp.model_dump()
        elapsed_ms = (time.perf_counter() - start) * 1000
        avg_ms = elapsed_ms / iterations

        assert avg_ms < _REPO_RESPONSE_SERIALIZE_BASELINE_MS


@pytest.mark.performance
class TestPydanticValidationPerformance:
    """Pydantic 模型校验性能."""

    def test_chat_completion_request_validation_latency(self) -> None:
        """ChatCompletionRequest 校验延迟应 < 5ms."""
        # 预热
        ChatCompletionRequest(
            messages=[ChatMessage(role="user", content="x")],
            repo_id="test_docbot_repo_1",
            report_types=["architecture"],
            report_format="markdown",
            language="zh",
        )

        iterations = 100
        start = time.perf_counter()
        for _ in range(iterations):
            ChatCompletionRequest(
                messages=[ChatMessage(role="user", content="x")],
                repo_id="test_docbot_repo_1",
                report_types=["architecture"],
                report_format="markdown",
                language="zh",
            )
        elapsed_ms = (time.perf_counter() - start) * 1000
        avg_ms = elapsed_ms / iterations

        assert avg_ms < _PYDANTIC_VALIDATE_BASELINE_MS

    def test_repo_create_request_validation_latency(self) -> None:
        """RepoCreateRequest 校验延迟应 < 5ms."""
        # 预热
        RepoCreateRequest(
            repo_name="test",
            platform="github",
            repo_url="https://github.com/t/t.git",
        )

        iterations = 100
        start = time.perf_counter()
        for _ in range(iterations):
            RepoCreateRequest(
                repo_name="test",
                platform="github",
                repo_url="https://github.com/t/t.git",
            )
        elapsed_ms = (time.perf_counter() - start) * 1000
        avg_ms = elapsed_ms / iterations

        assert avg_ms < _PYDANTIC_VALIDATE_BASELINE_MS

"""API 测试: /v1/chat/completions 非流式 + 错误码.

需要部署后容器栈.
测试目标 (见 AGENTS.md 第 13 章关键测试用例 3):
- OpenAI 兼容端点非流式响应
- 错误码 (401/400/500)
"""
from __future__ import annotations

import pytest


@pytest.mark.api
@pytest.mark.requires_external
class TestOpenAiCompatible:
    async def test_chat_completions_non_stream(self) -> None:
        """测试非流式响应 (stream=false)."""
        pytest.skip("Requires external services")

    async def test_invalid_instruction_returns_400(self) -> None:
        """测试非法 JSON 指令返回 400."""
        pytest.skip("Requires external services")

    async def test_missing_auth_returns_401(self) -> None:
        """测试缺少 Authorization 头返回 401 (self_host=False 模式)."""
        pytest.skip("Requires external services")

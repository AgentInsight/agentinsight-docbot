"""API 测试: /v1/models 返回模型列表.

需要部署后容器栈.
"""
from __future__ import annotations

import pytest


@pytest.mark.api
@pytest.mark.requires_external
class TestModelsEndpoint:
    async def test_models_returns_list(self) -> None:
        """测试 /v1/models 返回模型列表.

        验证: 200 + 响应含 'agentinsight-docbot' 模型.
        """
        pytest.skip("Requires external services")

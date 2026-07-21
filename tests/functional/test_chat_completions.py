"""功能测试: /v1/chat/completions SSE 流式.

需要部署后容器栈.
测试目标: POST /v1/chat/completions stream=true 接收 SSE 事件流.
"""
from __future__ import annotations

import pytest


@pytest.mark.functional
@pytest.mark.requires_external
class TestChatCompletions:
    async def test_chat_completions_sse_stream(self) -> None:
        """测试 SSE 流式响应.

        请求体:
            POST /v1/chat/completions
            {
                "model": "agentinsight-docbot",
                "stream": true,
                "messages": [{
                    "role": "user",
                    "content": "{\\"action\\":\\"generate_docs\\",\\"repo_id\\":\\"xxx\\",\\"report_types\\":[\\"architecture\\"],\\"report_format\\":\\"markdown\\",\\"language\\":\\"zh\\"}"
                }]
            }
        验证: 200 + Content-Type: text/event-stream + SSE 事件流
        """
        pytest.skip("Requires external services")

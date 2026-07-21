"""端到端测试: 完整链路.

需要部署后容器栈.
测试目标 (见 AGENTS.md 第 13 章关键测试用例 4 + 第 14 章):
- 配置仓库 → 新建会话 → 选择报告类型 → 一键生成 → 验证 SSE 进度 → 验证下载 → 切换会话验证隔离
"""
from __future__ import annotations

import pytest


@pytest.mark.e2e
@pytest.mark.requires_external
class TestGenerateDocsFlow:
    async def test_full_generate_docs_flow(self) -> None:
        """测试完整文档生成流程.

        步骤:
        1. POST /v1/repos 创建代码仓库配置
        2. POST /v1/repos/{id}/sync 同步触发克隆 + 索引
        3. POST /v1/chat/completions (stream=true) 一键生成
        4. 验证 SSE 事件流 (进度/工具调用/检索来源)
        5. GET /v1/reports/{id}/download 验证下载
        6. 切换会话验证数据隔离
        """
        pytest.skip("Requires external services")

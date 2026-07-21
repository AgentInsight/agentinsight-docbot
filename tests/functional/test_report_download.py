"""功能测试: /v1/reports/{id}/download 5 种格式.

需要部署后容器栈.
测试目标: 验证 5 种文档格式 (markdown/html/pdf/docx/json) 下载.
"""
from __future__ import annotations

import pytest


@pytest.mark.functional
@pytest.mark.requires_external
class TestReportDownload:
    @pytest.mark.parametrize("fmt", ["markdown", "html", "pdf", "docx", "json"])
    async def test_download_report(self, fmt: str) -> None:
        """测试下载指定格式的报告.

        前置条件: 已生成 1 份报告 (report_id 存在)
        验证: 200 + Content-Type 对应格式
        """
        pytest.skip("Requires external services")

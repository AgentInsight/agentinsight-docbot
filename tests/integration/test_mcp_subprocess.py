"""集成测试: 系统 MCP 子进程管理.

验证 GitMCPAdapter (系统自带 MCP 子进程封装):
- 子进程启动成功
- 子进程关闭正常
- 异常退出后自动重启
- 资源清理 (无僵尸进程)

需要部署后容器栈.
"""
from __future__ import annotations

import pytest


@pytest.mark.integration
@pytest.mark.requires_external
class TestMCPSubprocess:
    """MCP 子进程管理测试."""

    async def test_mcp_subprocess_starts(self) -> None:
        """测试 MCP 子进程启动成功."""
        pytest.skip("Requires external services")

    async def test_mcp_subprocess_stops_cleanly(self) -> None:
        """测试 MCP 子进程正常关闭."""
        pytest.skip("Requires external services")

    async def test_mcp_subprocess_restart_on_crash(self) -> None:
        """测试 MCP 子进程异常退出后自动重启."""
        pytest.skip("Requires external services")

    async def test_mcp_subprocess_no_zombie(self) -> None:
        """测试 MCP 子进程关闭后无僵尸进程."""
        pytest.skip("Requires external services")

    async def test_mcp_subprocess_credentials_injected(self) -> None:
        """测试 MCP 子进程注入解密后的凭据 (AES-GCM 解密)."""
        pytest.skip("Requires external services")

    async def test_mcp_subprocess_stdin_handshake(self) -> None:
        """测试 MCP 子进程 stdin 握手协议."""
        pytest.skip("Requires external services")

    async def test_mcp_subprocess_not_user_configurable(self) -> None:
        """测试 MCP 配置不通过 /v1/mcp/configs 暴露 (系统自带)."""
        pytest.skip("Requires external services")

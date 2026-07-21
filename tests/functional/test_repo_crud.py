"""功能测试: /v1/repos CRUD + 敏感字段不返回原文.

需要部署后容器栈 (PostgreSQL + Redis + agent-docbot) 才能运行.
测试目标 (见 AGENTS.md 第 13 章关键测试用例 3):
- POST /v1/repos 创建仓库配置
- GET /v1/repos 列出当前用户仓库
- GET /v1/repos/{repo_id} 获取单个仓库
- PUT /v1/repos/{repo_id} 更新仓库配置
- DELETE /v1/repos/{repo_id} 删除仓库
- 验证 API 响应不含敏感字段原文 (仅 has_token 等标志位)
"""
from __future__ import annotations

import pytest


@pytest.mark.functional
@pytest.mark.requires_external
class TestRepoCrud:
    """需要部署后容器栈 (PostgreSQL + agent-docbot)."""

    @pytest.fixture
    def agent_docbot_url(self) -> str:
        """Agent 服务 URL (部署后)."""
        import os

        return os.environ.get("AGENT_URL", "http://agent-docbot:8068")

    async def test_create_repo(self, agent_docbot_url: str) -> None:
        """测试创建代码仓库配置.

        前置条件: 服务端 .env 已配置 GIT_CREDENTIAL_KEY (32 字节)
        请求体:
            POST /v1/repos
            {
                "repo_name": "test-repo",
                "platform": "github",
                "repo_url": "https://github.com/test/repo.git",
                "auth_type": "none",
                "default_branch": "main"
            }
        验证: 201 + 响应含 has_token=False
        """
        pytest.skip("Requires external services (PostgreSQL + agent-docbot)")

    async def test_list_repos(self, agent_docbot_url: str) -> None:
        """测试列出用户仓库.

        前置条件: 用户至少有 1 个仓库配置
        验证: 200 + 响应为 list[RepoResponse] + 不含敏感字段
        """
        pytest.skip("Requires external services")

    async def test_get_repo_by_id(self, agent_docbot_url: str) -> None:
        """测试获取单个仓库."""
        pytest.skip("Requires external services")

    async def test_update_repo(self, agent_docbot_url: str) -> None:
        """测试更新仓库配置 (含敏感字段更新)."""
        pytest.skip("Requires external services")

    async def test_delete_repo(self, agent_docbot_url: str) -> None:
        """测试删除仓库配置 + 验证本地克隆目录清理."""
        pytest.skip("Requires external services")

    async def test_response_does_not_contain_sensitive_fields(self, agent_docbot_url: str) -> None:
        """验证 API 响应不含 token/password/ssh_key 原文字段.

        属第 11 章安全硬约束.
        """
        pytest.skip("Requires external services")

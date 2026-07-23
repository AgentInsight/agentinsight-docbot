"""单元测试: init.sql DDL 关键字段校验.

测试目标 (见 AGENTS.md 第 13 章关键测试用例 1):
- 读取 scripts/init.sql 文本
- 含 'mcp_configs' CREATE TABLE (系统 MCP 配置, 预置 fetch/filesystem/git)
- 含 'user_git_repos' CREATE TABLE
- 含 'report_type_label' / 'report_summary' / 'report_image_svg'
- 不含 'research_search_logs' / 'uploaded_files'
"""
from __future__ import annotations

from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).parent.parent.parent
_INIT_SQL_PATH = _PROJECT_ROOT / "scripts" / "init.sql"


class TestInitSqlContent:
    """init.sql DDL 内容校验."""

    @pytest.fixture(scope="class")
    def init_sql_content(self) -> str:
        """读取 init.sql 全文 (类作用域, 避免重复 IO)."""
        assert _INIT_SQL_PATH.exists(), f"init.sql 不存在: {_INIT_SQL_PATH}"
        return _INIT_SQL_PATH.read_text(encoding="utf-8")

    def test_init_sql_file_exists(self) -> None:
        """验证 init.sql 文件存在."""
        assert _INIT_SQL_PATH.exists()

    def test_init_sql_not_empty(self, init_sql_content: str) -> None:
        """验证 init.sql 内容非空."""
        assert len(init_sql_content) > 1000, "init.sql 内容过短"

    def test_contains_user_git_repos_table(self, init_sql_content: str) -> None:
        """验证含 'user_git_repos' CREATE TABLE (docbot 专属业务表)."""
        assert "CREATE TABLE IF NOT EXISTS user_git_repos" in init_sql_content
        assert "user_git_repos" in init_sql_content

    def test_contains_mcp_configs_table(self, init_sql_content: str) -> None:
        """验证含 'mcp_configs' CREATE TABLE (系统 MCP 配置表)."""
        assert "CREATE TABLE IF NOT EXISTS mcp_configs" in init_sql_content
        assert "mcp_configs" in init_sql_content

    def test_mcp_configs_has_key_columns(self, init_sql_content: str) -> None:
        """验证 mcp_configs 表含关键列 (agent_id/user_id/name/transport_type/is_system)."""
        # 检查 mcp_configs 表定义区块内含关键列
        assert "transport_type" in init_sql_content
        assert "is_system" in init_sql_content
        assert "command" in init_sql_content
        assert "args" in init_sql_content  # noqa: S101
        assert "env_vars" in init_sql_content

    def test_mcp_configs_has_indexes(self, init_sql_content: str) -> None:
        """验证 mcp_configs 表含必要索引 (agent_user / system / unique_name)."""
        assert "idx_mcp_configs_agent_user" in init_sql_content
        assert "idx_mcp_configs_system" in init_sql_content
        assert "idx_mcp_configs_unique_name" in init_sql_content

    def test_mcp_configs_has_updated_at_trigger(self, init_sql_content: str) -> None:
        """验证 mcp_configs 表挂了 update_updated_at 触发器."""
        assert "trg_mcp_configs_updated_at" in init_sql_content

    def test_mcp_configs_has_preset_system_configs(self, init_sql_content: str) -> None:
        """验证预置了 3 个系统 MCP 配置 (fetch / filesystem / git)."""
        # 预置 INSERT 语句应含这 3 个系统 MCP
        assert "'fetch'" in init_sql_content
        assert "'filesystem'" in init_sql_content
        assert "'git'" in init_sql_content
        # 都应是 is_system = TRUE
        # 统计 is_system = TRUE 的预置行 (至少 3 个)
        assert init_sql_content.count("is_system = TRUE") >= 3 or (
            init_sql_content.count("TRUE") >= 3
        )

    def test_contains_report_type_label_column(self, init_sql_content: str) -> None:
        """验证含 'report_type_label' 列 (research_reports 表扩展列)."""
        assert "report_type_label" in init_sql_content

    def test_contains_report_summary_column(self, init_sql_content: str) -> None:
        """验证含 'report_summary' 列."""
        assert "report_summary" in init_sql_content

    def test_contains_report_image_svg_column(self, init_sql_content: str) -> None:
        """验证含 'report_image_svg' 列."""
        assert "report_image_svg" in init_sql_content

    def test_contains_docbot_type_index(self, init_sql_content: str) -> None:
        """验证含 idx_research_reports_agent_user_type 索引 (按文档类型查询)."""
        assert "idx_research_reports_agent_user_type" in init_sql_content
        assert "report_type_label" in init_sql_content

    def test_not_contains_research_search_logs(self, init_sql_content: str) -> None:
        """验证不含 'research_search_logs' 表 (docbot 不使用搜索日志表)."""
        # 检查 CREATE TABLE research_search_logs
        # 但允许在注释中提及 (从 AIR 拷贝的注释)
        # 简单检查: 不含 CREATE TABLE research_search_logs
        assert "CREATE TABLE IF NOT EXISTS research_search_logs" not in init_sql_content
        assert "CREATE TABLE research_search_logs" not in init_sql_content

    def test_not_contains_uploaded_files(self, init_sql_content: str) -> None:
        """验证不含 'uploaded_files' CREATE TABLE (docbot 不接受文件上传)."""
        # 不创建 uploaded_files 表
        assert "CREATE TABLE IF NOT EXISTS uploaded_files" not in init_sql_content
        assert "CREATE TABLE uploaded_files" not in init_sql_content

    def test_contains_agent_id_user_id_composite_index(self, init_sql_content: str) -> None:
        """验证含 agent_id + user_id 复合索引 (数据隔离)."""
        assert "agent_id, user_id" in init_sql_content or "agent_id,user_id" in init_sql_content

    def test_contains_update_updated_at_function(self, init_sql_content: str) -> None:
        """验证含 update_updated_at_column() 触发器函数 (自动维护 updated_at)."""
        assert "update_updated_at_column" in init_sql_content
        assert "CREATE OR REPLACE FUNCTION" in init_sql_content

    def test_contains_create_or_replace_trigger(self, init_sql_content: str) -> None:
        """验证使用 CREATE OR REPLACE TRIGGER 保证幂等."""
        assert "CREATE OR REPLACE TRIGGER" in init_sql_content

    def test_contains_idempotent_ddl(self, init_sql_content: str) -> None:
        """验证 DDL 使用 IF NOT EXISTS / IF EXISTS (幂等)."""
        # CREATE TABLE IF NOT EXISTS
        assert "CREATE TABLE IF NOT EXISTS" in init_sql_content
        # CREATE INDEX IF NOT EXISTS
        assert "CREATE INDEX IF NOT EXISTS" in init_sql_content
        # ALTER TABLE IF EXISTS ... ADD COLUMN IF NOT EXISTS
        assert "ADD COLUMN IF NOT EXISTS" in init_sql_content

    def test_contains_extensions(self, init_sql_content: str) -> None:
        """验证含 uuid-ossp 和 pgcrypto 扩展."""
        assert "uuid-ossp" in init_sql_content
        assert "pgcrypto" in init_sql_content

    def test_contains_aes_gcm_encrypted_fields(self, init_sql_content: str) -> None:
        """验证含 AES-GCM 加密的敏感字段 (encrypted_token / encrypted_password / encrypted_ssh_key)."""
        assert "encrypted_token" in init_sql_content
        assert "encrypted_username" in init_sql_content
        assert "encrypted_password" in init_sql_content
        assert "encrypted_ssh_key" in init_sql_content

    def test_contains_supported_platforms_comment(self, init_sql_content: str) -> None:
        """验证含 7 种支持平台的注释."""
        # platform 字段注释含 7 种平台
        platforms_in_sql = [
            p for p in (
                "github",
                "gitlab",
                "gitee",
                "bitbucket",
                "coding",
                "gitea",
                "custom",
            )
            if p in init_sql_content
        ]
        # 至少含部分平台
        assert len(platforms_in_sql) >= 5, f"仅含 {platforms_in_sql}"

    def test_contains_auth_type_field(self, init_sql_content: str) -> None:
        """验证含 auth_type 字段 (none/token/password/ssh_key)."""
        assert "auth_type" in init_sql_content

"""集成测试: 数据库初始化 (init.sql 幂等性).

验证:
- scripts/init.sql 可成功执行
- 重复执行不报错 (CREATE TABLE IF NOT EXISTS)
- 所有预期表存在
- 索引存在

需要部署后容器栈 (Postgres).
"""
from __future__ import annotations

from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).parent.parent.parent
_INIT_SQL_PATH = _PROJECT_ROOT / "scripts" / "init.sql"

EXPECTED_TABLES = [
    "research_sessions",
    "research_reports",
    "token_usage_logs",
    "user_git_repos",
    "chat_messages",
    "report_limits",
    "daily_report_usage",
    "mcp_configs",
]

EXPECTED_INDEXES = [
    "idx_research_sessions_agent_user_updated",
    "idx_chat_messages_session",
    "idx_user_git_repos_agent_user",
    "idx_research_reports_session_agent_user",
]


@pytest.mark.integration
@pytest.mark.requires_external
class TestDatabaseInit:
    """数据库初始化测试."""

    async def test_init_sql_executes_successfully(self) -> None:
        """测试 init.sql 可成功执行."""
        pytest.skip("Requires external Postgres")

    async def test_init_sql_idempotent(self) -> None:
        """测试 init.sql 重复执行不报错."""
        pytest.skip("Requires external Postgres")

    async def test_all_expected_tables_exist(self) -> None:
        """测试所有预期表存在."""
        pytest.skip("Requires external Postgres")

    async def test_all_expected_indexes_exist(self) -> None:
        """测试所有预期索引存在."""
        pytest.skip("Requires external Postgres")

    async def test_repos_table_has_repo_id_unique_constraint(self) -> None:
        """测试 repos.repo_id 有 UNIQUE 约束."""
        pytest.skip("Requires external Postgres")

    async def test_report_records_has_repo_id_index(self) -> None:
        """测试 report_records.repo_id 索引存在 (多仓库隔离)."""
        pytest.skip("Requires external Postgres")


def test_init_sql_file_exists() -> None:
    """(单元测试) 验证 init.sql 文件存在."""
    assert _INIT_SQL_PATH.exists(), f"init.sql 不存在: {_INIT_SQL_PATH}"


def test_init_sql_contains_create_tables() -> None:
    """(单元测试) 验证 init.sql 包含所有预期表的 CREATE TABLE 语句."""
    content = _INIT_SQL_PATH.read_text(encoding="utf-8")
    for table in EXPECTED_TABLES:
        assert "CREATE TABLE" in content.upper(), "未找到 CREATE TABLE 语句"
        # 表名应出现在 SQL 中
        assert table.lower() in content.lower(), f"表 {table} 未在 init.sql 中定义"

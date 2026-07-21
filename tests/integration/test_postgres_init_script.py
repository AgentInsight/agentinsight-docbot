"""集成测试: postgres 容器 init.sql 执行完整性.

验证:
- init.sql 在 postgres 容器启动时已执行 (业务表存在)
- 表结构正确 (关键列存在)
- 触发器存在 (update_updated_at_column 触发器函数 + 各表触发器)
- 默认限额行存在 (report_limits 全局默认 daily_limit=5)

需要部署后容器栈 (Postgres).
不直接连数据库, 用 docker exec 探测.
"""
from __future__ import annotations

import os
import subprocess

import pytest

# 容器名默认: agentinsight-docbot-postgres-1 (compose -p agentinsight-docbot 命名约定)
_POSTGRES_CONTAINER = os.getenv("POSTGRES_CONTAINER", "agentinsight-docbot-postgres-1")
_POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
_POSTGRES_DB = os.getenv("POSTGRES_DB", "agents")


def _psql_query(query: str) -> subprocess.CompletedProcess:
    """通过 docker exec 在 postgres 容器内执行 psql 查询.

    返回 CompletedProcess, 调用方负责检查 returncode.
    """
    cmd = [
        "docker",
        "exec",
        _POSTGRES_CONTAINER,
        "psql",
        "-U",
        _POSTGRES_USER,
        "-d",
        _POSTGRES_DB,
        "-t",
        "-A",
        "-c",
        query,
    ]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=30)


def _skip_if_unavailable(result: subprocess.CompletedProcess) -> None:
    """若 psql 查询失败则跳过测试 (容器可能未就绪)."""
    if result.returncode != 0:
        pytest.skip(f"psql 查询失败 (容器可能未就绪): {result.stderr}")


@pytest.mark.integration
@pytest.mark.requires_external
class TestPostgresInitScript:
    """postgres 容器 init.sql 执行完整性测试."""

    def test_init_sql_executed_all_tables_exist(self) -> None:
        """验证 init.sql 已执行, 所有预期业务表存在."""
        expected_tables = [
            "research_sessions",
            "research_reports",
            "user_git_repos",
            "report_limits",
            "daily_report_usage",
            "token_usage_logs",
            "chat_messages",
        ]
        result = _psql_query(
            "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename;"
        )
        _skip_if_unavailable(result)
        tables = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        missing = [t for t in expected_tables if t not in tables]
        assert not missing, f"缺失业务表 (init.sql 可能未执行): {missing}"

    def test_user_git_repos_table_structure_correct(self) -> None:
        """验证 user_git_repos 表结构正确 (含 agent_id/user_id/encrypted_token 等关键列)."""
        result = _psql_query(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='user_git_repos' ORDER BY column_name;"
        )
        _skip_if_unavailable(result)
        columns = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        expected_columns = [
            "agent_id",
            "user_id",
            "repo_name",
            "repo_url",
            "auth_type",
            "encrypted_token",
            "encrypted_username",
            "encrypted_password",
            "encrypted_ssh_key",
            "enabled",
        ]
        missing = [c for c in expected_columns if c not in columns]
        assert not missing, f"user_git_repos 缺失关键列: {missing}"

    def test_research_sessions_has_agent_id_user_id(self) -> None:
        """验证 research_sessions 表含 agent_id + user_id 隔离列."""
        result = _psql_query(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='research_sessions' AND column_name IN "
            "('agent_id','user_id','session_id','status','expires_at');"
        )
        _skip_if_unavailable(result)
        columns = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        assert "agent_id" in columns, "research_sessions 缺 agent_id 列"
        assert "user_id" in columns, "research_sessions 缺 user_id 列"
        assert "session_id" in columns, "research_sessions 缺 session_id 列"

    def test_triggers_exist_on_tables(self) -> None:
        """验证 update_updated_at_column 触发器函数与各表触发器存在."""
        # 触发器函数
        result_fn = _psql_query(
            "SELECT proname FROM pg_proc WHERE proname='update_updated_at_column';"
        )
        _skip_if_unavailable(result_fn)
        fns = [line.strip() for line in result_fn.stdout.splitlines() if line.strip()]
        assert "update_updated_at_column" in fns, "触发器函数 update_updated_at_column 不存在"

        # 各表触发器
        result_trg = _psql_query(
            "SELECT tgname FROM pg_trigger WHERE tgname LIKE 'trg_%updated_at' "
            "AND NOT tgisinternal ORDER BY tgname;"
        )
        _skip_if_unavailable(result_trg)
        triggers = [line.strip() for line in result_trg.stdout.splitlines() if line.strip()]
        expected_triggers = [
            "trg_research_sessions_updated_at",
            "trg_research_reports_updated_at",
            "trg_user_git_repos_updated_at",
            "trg_report_limits_updated_at",
            "trg_daily_report_usage_updated_at",
        ]
        missing = [t for t in expected_triggers if t not in triggers]
        assert not missing, f"缺失触发器: {missing}"

    def test_default_limit_row_exists(self) -> None:
        """验证 report_limits 表存在全局默认限额行 (agent_id IS NULL, user_id IS NULL, daily_limit=5)."""
        result = _psql_query(
            "SELECT daily_limit FROM report_limits "
            "WHERE agent_id IS NULL AND user_id IS NULL;"
        )
        _skip_if_unavailable(result)
        rows = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        assert rows, "report_limits 无全局默认限额行"
        assert rows[0] == "5", f"全局默认限额 daily_limit 应为 5, 实际为 {rows[0]}"

    def test_extensions_installed(self) -> None:
        """验证 uuid-ossp 和 pgcrypto 扩展已安装."""
        result = _psql_query(
            "SELECT extname FROM pg_extension WHERE extname IN ('uuid-ossp','pgcrypto') "
            "ORDER BY extname;"
        )
        _skip_if_unavailable(result)
        exts = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        assert "uuid-ossp" in exts, "uuid-ossp 扩展未安装"
        assert "pgcrypto" in exts, "pgcrypto 扩展未安装"

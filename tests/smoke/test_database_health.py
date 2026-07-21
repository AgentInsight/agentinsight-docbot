"""冒烟测试: Postgres 容器 init.sql 已执行, 业务表存在.

验证:
- postgres 容器运行中
- init.sql 已执行 (业务表存在)
- 关键表 (research_sessions / user_git_repos / report_limits) 可查询

需要部署后容器栈 (Postgres).
不直接连数据库, 用 docker exec 探测.
测试目标地址从环境变量 AGENT_URL 注入 (默认 http://127.0.0.1:8068).
"""
from __future__ import annotations

import os
import subprocess

import pytest

# 容器名默认: agentinsight-docbot-postgres-1 (compose -p agentinsight-docbot 命名约定)
_POSTGRES_CONTAINER = os.getenv("POSTGRES_CONTAINER", "agentinsight-docbot-postgres-1")
_POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
_POSTGRES_DB = os.getenv("POSTGRES_DB", "agents")

EXPECTED_TABLES = [
    "research_sessions",
    "research_reports",
    "user_git_repos",
    "report_limits",
    "daily_report_usage",
    "token_usage_logs",
    "chat_messages",
]


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


@pytest.mark.smoke
@pytest.mark.requires_external
class TestDatabaseHealth:
    """Postgres 容器业务表存在冒烟测试."""

    def test_postgres_container_running(self) -> None:
        """验证 postgres 容器运行中 (docker exec 可执行)."""
        result = subprocess.run(
            [
                "docker",
                "inspect",
                "--format",
                "{{.State.Running}}",
                _POSTGRES_CONTAINER,
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            pytest.skip(f"postgres 容器不可用: {_POSTGRES_CONTAINER}")
        assert result.stdout.strip() == "true", (
            f"postgres 容器未运行: {_POSTGRES_CONTAINER}"
        )

    def test_init_sql_executed_tables_exist(self) -> None:
        """验证 init.sql 已执行, 关键业务表存在 (research_sessions / user_git_repos / report_limits)."""
        result = _psql_query(
            "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename;"
        )
        if result.returncode != 0:
            pytest.skip(f"psql 查询失败 (容器可能未就绪): {result.stderr}")
        tables = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        for table in ("research_sessions", "user_git_repos", "report_limits"):
            assert table in tables, f"业务表 {table} 不存在 (init.sql 可能未执行)"

    def test_all_expected_tables_present(self) -> None:
        """验证所有预期业务表均存在 (7 张表)."""
        result = _psql_query(
            "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename;"
        )
        if result.returncode != 0:
            pytest.skip(f"psql 查询失败: {result.stderr}")
        tables = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        missing = [t for t in EXPECTED_TABLES if t not in tables]
        assert not missing, f"缺失业务表: {missing}"

    def test_report_limits_queryable(self) -> None:
        """验证 report_limits 表可查询 (含全局默认限额行)."""
        result = _psql_query(
            "SELECT count(*) FROM report_limits WHERE agent_id IS NULL AND user_id IS NULL;"
        )
        if result.returncode != 0:
            pytest.skip(f"psql 查询失败: {result.stderr}")
        count = int(result.stdout.strip() or "0")
        assert count >= 1, "report_limits 表无全局默认限额行 (init.sql 可能未执行)"

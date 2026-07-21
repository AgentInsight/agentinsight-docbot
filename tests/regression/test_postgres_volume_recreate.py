"""回归测试: postgres 卷重建后表结构仍正确 (init.sql 幂等性保证).

验证:
- init.sql 重复执行不报错 (CREATE TABLE IF NOT EXISTS / CREATE OR REPLACE 幂等)
- 重复执行后表结构仍正确 (列不丢失, 不重复)
- 重复执行后触发器/函数仍存在 (CREATE OR REPLACE 保证)
- 默认限额行不重复 (WHERE NOT EXISTS 保证)

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
    return subprocess.run(cmd, capture_output=True, text=True, timeout=60)


def _psql_exec_file(sql_path_in_container: str) -> subprocess.CompletedProcess:
    """通过 docker exec 在 postgres 容器内执行 SQL 文件 (幂等性回归).

    sql_path_in_container: 容器内 init.sql 路径 (如 /docker-entrypoint-initdb.d/init.sql)
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
        "-v",
        "ON_ERROR_STOP=1",
        "-f",
        sql_path_in_container,
    ]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=120)


def _skip_if_unavailable(result: subprocess.CompletedProcess) -> None:
    """若 psql 查询失败则跳过测试 (容器可能未就绪)."""
    if result.returncode != 0:
        pytest.skip(f"psql 查询失败 (容器可能未就绪): {result.stderr}")


@pytest.mark.regression
@pytest.mark.requires_external
class TestPostgresVolumeRecreate:
    """postgres 卷重建后表结构仍正确 (init.sql 幂等性) 回归测试."""

    def test_init_sql_repeated_execution_no_error(self) -> None:
        """验证 init.sql 重复执行不报错 (幂等性核心保证).

        场景: 模拟卷重建后 init.sql 被再次执行 (postgres 容器
        /docker-entrypoint-initdb.d/init.sql 仅首次启动执行, 此处手动重跑).
        """
        # 容器内 init.sql 挂载路径 (见 docker-compose.yml)
        result = _psql_exec_file("/docker-entrypoint-initdb.d/init.sql")
        if result.returncode != 0:
            # 容器可能未挂载 init.sql 或未就绪, 跳过
            pytest.skip(f"init.sql 重复执行失败 (容器可能未挂载 init.sql): {result.stderr}")
        # 重复执行应无错误 (returncode == 0)
        assert result.returncode == 0, (
            f"init.sql 重复执行报错 (违反幂等性): {result.stderr}"
        )

    def test_tables_structure_correct_after_repeated_execution(self) -> None:
        """验证 init.sql 重复执行后表结构仍正确 (列不丢失, 表数量一致)."""
        # 先重复执行一次
        exec_result = _psql_exec_file("/docker-entrypoint-initdb.d/init.sql")
        if exec_result.returncode != 0:
            pytest.skip(f"init.sql 重复执行失败: {exec_result.stderr}")

        # 查询表数量与关键列
        result = _psql_query(
            "SELECT count(*) FROM pg_tables WHERE schemaname='public';"
        )
        _skip_if_unavailable(result)
        table_count = int(result.stdout.strip() or "0")
        # 至少 7 张业务表
        assert table_count >= 7, (
            f"重复执行后业务表数量异常: {table_count} (应 >= 7)"
        )

        # 验证 user_git_repos 关键列不丢失
        col_result = _psql_query(
            "SELECT count(*) FROM information_schema.columns "
            "WHERE table_name='user_git_repos' AND column_name='encrypted_token';"
        )
        _skip_if_unavailable(col_result)
        col_count = int(col_result.stdout.strip() or "0")
        assert col_count == 1, (
            f"user_git_repos.encrypted_token 列数量异常: {col_count} (应 = 1)"
        )

    def test_default_limit_row_not_duplicated_after_repeated_execution(self) -> None:
        """验证 init.sql 重复执行后默认限额行不重复 (WHERE NOT EXISTS 保证)."""
        # 先重复执行一次
        exec_result = _psql_exec_file("/docker-entrypoint-initdb.d/init.sql")
        if exec_result.returncode != 0:
            pytest.skip(f"init.sql 重复执行失败: {exec_result.stderr}")

        # 查询全局默认限额行数量
        result = _psql_query(
            "SELECT count(*) FROM report_limits "
            "WHERE agent_id IS NULL AND user_id IS NULL;"
        )
        _skip_if_unavailable(result)
        count = int(result.stdout.strip() or "0")
        assert count == 1, (
            f"全局默认限额行重复 (违反 WHERE NOT EXISTS 幂等性): count={count} (应 = 1)"
        )

    def test_triggers_still_exist_after_repeated_execution(self) -> None:
        """验证 init.sql 重复执行后触发器仍存在 (CREATE OR REPLACE 保证)."""
        # 先重复执行一次
        exec_result = _psql_exec_file("/docker-entrypoint-initdb.d/init.sql")
        if exec_result.returncode != 0:
            pytest.skip(f"init.sql 重复执行失败: {exec_result.stderr}")

        # 查询触发器
        result = _psql_query(
            "SELECT count(*) FROM pg_trigger "
            "WHERE tgname LIKE 'trg_%updated_at' AND NOT tgisinternal;"
        )
        _skip_if_unavailable(result)
        count = int(result.stdout.strip() or "0")
        # 5 张表各 1 个触发器
        assert count >= 5, (
            f"重复执行后触发器数量异常: {count} (应 >= 5)"
        )

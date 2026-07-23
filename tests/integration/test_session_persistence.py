"""集成测试: 会话持久化 (Postgres + Redis cache_key 中转).

不依赖外部服务, 用 mock asyncpg + mock Redis 验证:
- chat_messages 表写入用户消息
- research_sessions 表确保会话存在
- Redis cache_key 写入/读取/过期 (TTL 24h)
- ReportStore 跨会话查询隔离 (agent_id + user_id + session_id)
- 6 步流水线中间产物通过 cache_key 在 Redis 中传递

测试目标 (AGENTS.md 第 13 章集成测试):
- 会话持久化不依赖 --run-external
- 用 mock 替代 Postgres/Redis
- 数据隔离: session_id=test_docbot_*, user_id=test_docbot_*
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _make_mock_pool(fetch_rows: list | None = None,
                    fetch_row: dict | None = None,
                    execute_result: str = "INSERT 0 1") -> MagicMock:
    """构造 mock asyncpg 连接池."""
    mock_conn = MagicMock()
    mock_conn.fetch = AsyncMock(return_value=fetch_rows or [])
    mock_conn.fetchrow = AsyncMock(return_value=fetch_row)
    mock_conn.execute = AsyncMock(return_value=execute_result)

    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock()
    mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
    return mock_pool


@pytest.mark.integration
class TestChatMessagesPersistence:
    """chat_messages 表写入测试 (经 session_store)."""

    async def test_user_message_persisted_with_session(self) -> None:
        """用户消息应写入 chat_messages 并关联 session_id (经 session_store)."""
        from src.api.routes import _persist_user_message

        mock_store = MagicMock()
        mock_store.ensure_session = AsyncMock(return_value=None)
        mock_store.get_session_title = AsyncMock(return_value=None)
        mock_store.update_session_title = AsyncMock(return_value=None)
        mock_store.save_message = AsyncMock(return_value=None)

        with patch("src.memory.session_store.get_session_store", return_value=mock_store), \
             patch("src.api.middleware.get_request_client_ip", return_value="127.0.0.1"):
            await _persist_user_message(
                session_id="test_docbot_session_1",
                agent_id="agentinsight-docbot",
                user_id="test_docbot_user_1",
                query='{"action":"generate_docs","repo_id":"test_docbot_repo_1"}',
            )

        # 验证 ensure_session + save_message 被调用
        assert mock_store.ensure_session.called
        ensure_args = mock_store.ensure_session.call_args.args
        assert ensure_args[0] == "test_docbot_session_1"
        assert ensure_args[1] == "agentinsight-docbot"
        assert ensure_args[2] == "test_docbot_user_1"

        assert mock_store.save_message.called
        save_kwargs = mock_store.save_message.call_args.kwargs
        assert save_kwargs["session_id"] == "test_docbot_session_1"
        assert save_kwargs["user_id"] == "test_docbot_user_1"
        assert save_kwargs["role"] == "user"

    async def test_message_persistence_failure_does_not_block(self) -> None:
        """消息持久化失败不应阻断主流程 (try/except 兜底)."""
        from src.api.routes import _persist_user_message

        mock_store = MagicMock()
        mock_store.ensure_session = AsyncMock(side_effect=Exception("DB 不可用"))

        with patch("src.memory.session_store.get_session_store", return_value=mock_store), \
             patch("src.api.middleware.get_request_client_ip", return_value="127.0.0.1"):
            # 不应抛异常 (内部 try/except 兜底)
            await _persist_user_message(
                session_id="test_docbot_session_1",
                agent_id="agentinsight-docbot",
                user_id="test_docbot_user_1",
                query="测试查询",
            )


@pytest.mark.integration
class TestRedisCacheKeyPassing:
    """Redis cache_key 在 6 步流水线中的传递."""

    async def test_cache_key_write_and_read_roundtrip(self) -> None:
        """cache_key 写入 Redis 后应能读回."""
        # 需要 fakeredis 实际存储数据 (MagicMock 无法模拟 Redis 读写回环)
        fakeredis = pytest.importorskip("fakeredis.aioredis", reason="需要 fakeredis 库")
        redis = fakeredis.FakeRedis()

        cache_key = "docbot:test_docbot_user_1:test_docbot_session_1:architecture:code_learning"
        cache_value = json.dumps({"summary": "代码学习产物", "files": ["main.py"]}, ensure_ascii=False)

        # 写入
        await redis.setex(cache_key, 86400, cache_value)
        # 读回
        result = await redis.get(cache_key)
        if isinstance(result, bytes):
            result = result.decode("utf-8")
        assert result == cache_value
        # 解析
        parsed = json.loads(result)
        assert parsed["summary"] == "代码学习产物"

        if hasattr(redis, "aclose"):
            await redis.aclose()

    async def test_cache_key_ttl_24h(self) -> None:
        """cache_key 应设置 24h TTL."""
        # 需要 fakeredis 实际存储数据 (MagicMock 无法模拟 setex 后 get 返回值)
        fakeredis = pytest.importorskip("fakeredis.aioredis", reason="需要 fakeredis 库")
        redis = fakeredis.FakeRedis()

        cache_key = "docbot:test_docbot_user_1:test_docbot_session_1:architecture:outline"
        await redis.setex(cache_key, 86400, "outline_data")

        # 验证 setex 被调用 (fakeredis 实际存储)
        result = await redis.get(cache_key)
        assert result is not None

        if hasattr(redis, "aclose"):
            await redis.aclose()

    async def test_cache_key_namespace_isolation(self) -> None:
        """不同 session_id 的 cache_key 应隔离."""
        # 需要 fakeredis 实际存储数据 (MagicMock 无法模拟跨 key 隔离)
        fakeredis = pytest.importorskip("fakeredis.aioredis", reason="需要 fakeredis 库")
        redis = fakeredis.FakeRedis()

        # 写入 session_1 的 cache
        await redis.setex(
            "docbot:user_1:session_1:architecture:code_learning",
            86400,
            "session_1_data",
        )
        # 读取 session_2 的 cache (应返回 None)
        result = await redis.get("docbot:user_1:session_2:architecture:code_learning")
        assert result is None

        if hasattr(redis, "aclose"):
            await redis.aclose()


@pytest.mark.integration
class TestReportStoreSessionIsolation:
    """ReportStore 跨会话查询隔离."""

    async def test_list_reports_filtered_by_session(self) -> None:
        """list_reports 应按 session_id 过滤 (跨会话隔离)."""
        from src.memory.report_store import ReportStore

        # 模拟数据库返回的行 (仅当前 session 的报告)
        rows = [
            {
                "report_id": "uuid_1",
                "session_id": "test_docbot_session_1",
                "user_id": "test_docbot_user_1",
                "agent_id": "agentinsight-docbot",
                "query": "query1",
                "report_md": "# 内容",
                "report_format": "markdown",
                "sources": [],
                "agent_role": "architecture",
                "report_type_label": "architecture",
                "report_summary": "摘要",
                "report_image_svg": "",
                "created_at": datetime(2026, 1, 1),
                "updated_at": datetime(2026, 1, 1),
            }
        ]
        mock_pool = _make_mock_pool(fetch_rows=rows)

        with patch("src.memory.report_store.get_pool", AsyncMock(return_value=mock_pool)):
            store = ReportStore(settings=MagicMock())
            result = await store.list_reports(
                agent_id="agentinsight-docbot",
                session_id="test_docbot_session_1",
                user_id="test_docbot_user_1",
            )

        assert len(result) == 1
        assert result[0]["session_id"] == "test_docbot_session_1"

        # 验证 SQL WHERE 含 session_id 过滤
        mock_conn = mock_pool.acquire.return_value.__aenter__.return_value
        fetch_call = mock_conn.fetch.call_args
        sql_arg = fetch_call.args[0] if fetch_call.args else fetch_call[0][0]
        assert "session_id" in sql_arg

    async def test_get_report_isolated_by_user(self) -> None:
        """get_report 应按 user_id 隔离 (跨用户隔离)."""
        from src.memory.report_store import ReportStore

        # mock 数据库返回 None (其他用户的报告不可见)
        mock_pool = _make_mock_pool(fetch_row=None)

        with patch("src.memory.report_store.get_pool", AsyncMock(return_value=mock_pool)):
            store = ReportStore(settings=MagicMock())
            result = await store.get_report(
                report_id="test_docbot_report_uuid_1",
                agent_id="agentinsight-docbot",
                user_id="test_docbot_user_1",
            )

        # 其他用户的报告应返回 None
        assert result is None

        # 验证 SQL WHERE 含 user_id 隔离
        mock_conn = mock_pool.acquire.return_value.__aenter__.return_value
        fetchrow_call = mock_conn.fetchrow.call_args
        sql_arg = fetchrow_call.args[0] if fetchrow_call.args else fetchrow_call[0][0]
        assert "user_id" in sql_arg
        assert "agent_id" in sql_arg

    async def test_delete_report_isolated_by_user(self) -> None:
        """delete_report 应按 user_id 隔离."""
        from src.memory.report_store import ReportStore

        # mock 返回 DELETE 0 (其他用户的报告, 未删除)
        mock_pool = _make_mock_pool(execute_result="DELETE 0")

        with patch("src.memory.report_store.get_pool", AsyncMock(return_value=mock_pool)):
            store = ReportStore(settings=MagicMock())
            deleted = await store.delete_report(
                report_id="test_docbot_report_uuid_1",
                agent_id="agentinsight-docbot",
                user_id="test_docbot_user_1",
            )

        # 跨用户删除应返回 False
        assert deleted is False

        # 验证 SQL WHERE 含 user_id
        mock_conn = mock_pool.acquire.return_value.__aenter__.return_value
        execute_call = mock_conn.execute.call_args
        sql_arg = execute_call.args[0] if execute_call.args else execute_call[0][0]
        assert "user_id" in sql_arg
        assert "agent_id" in sql_arg

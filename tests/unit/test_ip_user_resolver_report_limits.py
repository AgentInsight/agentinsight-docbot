"""单元测试: docbot 每日文档限额解析与扣减 (ip_user_resolver).

覆盖:
1. 有用户限额 → 取用户级
2. 无用户限额 → 取 Agent/系统级
3. 剩余不足申请份数 → 拒绝
4. 成功扣减 delta (多报告类型)
5. count_requested_docs 去重语义
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.api.ip_user_resolver import (
    check_daily_report_limit,
    count_requested_docs,
    increment_daily_report_count,
)

pytestmark = pytest.mark.unit


def test_count_requested_docs_dedup() -> None:
    """每个报告类型计 1 份, 重复类型去重."""
    assert count_requested_docs(["requirements", "api_doc"]) == 2
    assert count_requested_docs(["architecture", "architecture"]) == 1
    assert count_requested_docs([]) == 0
    assert count_requested_docs(None) == 0


@pytest.mark.asyncio
async def test_user_limit_takes_precedence(monkeypatch: pytest.MonkeyPatch) -> None:
    """有用户限额时取用户级 (10), 不取 Agent 默认."""
    monkeypatch.setattr(
        "src.api.ip_user_resolver._get_daily_limit_from_db",
        AsyncMock(return_value=10),
    )
    monkeypatch.setattr(
        "src.api.ip_user_resolver._get_daily_usage_from_db",
        AsyncMock(return_value=2),
    )
    allowed, count, limit = await check_daily_report_limit(
        "user-1", "agentinsight-docbot", requested_count=1
    )
    assert allowed is True
    assert count == 2
    assert limit == 10


@pytest.mark.asyncio
async def test_no_user_uses_agent_or_system_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """无用户专属时走库返回的 Agent/系统默认 (3)."""
    monkeypatch.setattr(
        "src.api.ip_user_resolver._get_daily_limit_from_db",
        AsyncMock(return_value=3),
    )
    monkeypatch.setattr(
        "src.api.ip_user_resolver._get_daily_usage_from_db",
        AsyncMock(return_value=1),
    )
    allowed, count, limit = await check_daily_report_limit(
        "user-1", "agentinsight-docbot", requested_count=1
    )
    assert allowed is True
    assert count == 1
    assert limit == 3


@pytest.mark.asyncio
async def test_remaining_insufficient_rejects(monkeypatch: pytest.MonkeyPatch) -> None:
    """剩余 1 < 申请 2 → 拒绝."""
    monkeypatch.setattr(
        "src.api.ip_user_resolver._get_daily_limit_from_db",
        AsyncMock(return_value=3),
    )
    monkeypatch.setattr(
        "src.api.ip_user_resolver._get_daily_usage_from_db",
        AsyncMock(return_value=2),
    )
    allowed, count, limit = await check_daily_report_limit(
        "user-1", "agentinsight-docbot", requested_count=2
    )
    assert allowed is False
    assert count == 2
    assert limit == 3


@pytest.mark.asyncio
async def test_remaining_exact_allows(monkeypatch: pytest.MonkeyPatch) -> None:
    """剩余 2 >= 申请 2 → 允许."""
    monkeypatch.setattr(
        "src.api.ip_user_resolver._get_daily_limit_from_db",
        AsyncMock(return_value=3),
    )
    monkeypatch.setattr(
        "src.api.ip_user_resolver._get_daily_usage_from_db",
        AsyncMock(return_value=1),
    )
    allowed, count, limit = await check_daily_report_limit(
        "user-1", "agentinsight-docbot", requested_count=2
    )
    assert allowed is True
    assert count == 1
    assert limit == 3


@pytest.mark.asyncio
async def test_db_zero_falls_back_to_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """库无有效配置 (0) → 回退 settings.ip_daily_report_limit."""
    monkeypatch.setattr(
        "src.api.ip_user_resolver._get_daily_limit_from_db",
        AsyncMock(return_value=0),
    )
    monkeypatch.setattr(
        "src.api.ip_user_resolver._get_daily_usage_from_db",
        AsyncMock(return_value=0),
    )
    fake_settings = MagicMock()
    fake_settings.ip_daily_report_limit = 3
    monkeypatch.setattr(
        "src.config.settings.get_settings",
        lambda: fake_settings,
    )
    allowed, count, limit = await check_daily_report_limit(
        "user-1", "agentinsight-docbot", requested_count=1
    )
    assert allowed is True
    assert count == 0
    assert limit == 3


@pytest.mark.asyncio
async def test_increment_with_delta(monkeypatch: pytest.MonkeyPatch) -> None:
    """成功扣减支持 delta>1 (多报告类型)."""
    fake_conn = AsyncMock()
    fake_conn.fetchrow = AsyncMock(return_value={"daily_count": 5})
    fake_pool = MagicMock()
    fake_pool.acquire = MagicMock(
        return_value=MagicMock(
            __aenter__=AsyncMock(return_value=fake_conn),
            __aexit__=AsyncMock(return_value=None),
        )
    )
    monkeypatch.setattr(
        "src.memory.db_initializer.get_pool",
        AsyncMock(return_value=fake_pool),
    )

    new_count = await increment_daily_report_count(
        "user-1", "agentinsight-docbot", delta=2
    )
    assert new_count == 5
    # INSERT ... VALUES ($1,$2,$3,$4) 中 $4 为 delta
    args = fake_conn.fetchrow.await_args.args
    assert args[-1] == 2

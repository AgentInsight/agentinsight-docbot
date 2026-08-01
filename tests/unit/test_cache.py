"""单元测试: Redis 缓存键管理 (6 步流水线中间产物传递).

测试目标:
- build_cache_key 格式正确: docbot:agentinsight-docbot:user1:session1:code_learning:architecture
- write_cache + read_cache 往返 (用 fakeredis mock)
- clear_session_cache 按前缀删除
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.skills.docbot.cache import (
    CACHE_TYPES,
    build_cache_key,
    clear_session_cache,
    delete_cache,
    read_cache,
    write_cache,
)


class TestBuildCacheKey:
    """build_cache_key 格式测试."""

    def test_basic_format(self) -> None:
        """键格式: docbot:{agent_id}:{user_id}:{session_id}:{type}:{report_type}."""
        key = build_cache_key(
            agent_id="agentinsight-docbot",
            user_id="user1",
            session_id="session1",
            type_="code_learning",
            report_type="architecture",
        )
        assert key == "docbot:agentinsight-docbot:user1:session1:code_learning:architecture"

    def test_with_chapter_idx(self) -> None:
        """含 chapter_idx 时附加: :content:architecture:0."""
        key = build_cache_key(
            agent_id="agentinsight-docbot",
            user_id="user1",
            session_id="session1",
            type_="content",
            report_type="architecture",
            chapter_idx=0,
        )
        assert key == "docbot:agentinsight-docbot:user1:session1:content:architecture:0"

    def test_chapter_idx_str(self) -> None:
        """chapter_idx 支持字符串."""
        key = build_cache_key(
            agent_id="agentinsight-docbot",
            user_id="user1",
            session_id="session1",
            type_="reviewed",
            report_type="api_doc",
            chapter_idx="2",
        )
        assert key == "docbot:agentinsight-docbot:user1:session1:reviewed:api_doc:2"

    def test_invalid_cache_type_raises(self) -> None:
        """非法 type_ 抛 ValueError."""
        with pytest.raises(ValueError, match="invalid_cache_type"):
            build_cache_key(
                agent_id="agentinsight-docbot",
                user_id="user1",
                session_id="session1",
                type_="invalid_type",
                report_type="architecture",
            )

    def test_cache_types_contains_six_types(self) -> None:
        """CACHE_TYPES 含流水线类型 + 共享学习类型."""
        expected = {
            "code_learning",
            "outline",
            "content",
            "reviewed",
            "merged",
            "final",
            "repo_facts",
            "code_learning_shared",
        }
        assert set(CACHE_TYPES) == expected
        assert len(CACHE_TYPES) == 8

    def test_chapter_idx_none_omitted(self) -> None:
        """chapter_idx=None 时, 键不附加 chapter_idx 部分."""
        key_no_chapter = build_cache_key(
            agent_id="agentinsight-docbot",
            user_id="user1",
            session_id="session1",
            type_="outline",
            report_type="architecture",
            chapter_idx=None,
        )
        key_omitted = build_cache_key(
            agent_id="agentinsight-docbot",
            user_id="user1",
            session_id="session1",
            type_="outline",
            report_type="architecture",
        )
        assert key_no_chapter == key_omitted
        assert key_no_chapter.endswith(":architecture")
        assert ":architecture:" not in key_no_chapter


class TestWriteReadCache:
    """write_cache + read_cache 往返测试 (mock Redis)."""

    @pytest.mark.asyncio
    async def test_write_then_read_round_trip(self, mock_settings: MagicMock) -> None:
        """write_cache + read_cache 往返 (fakeredis)."""
        try:
            import fakeredis.aioredis

            fake_redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
        except ImportError:
            pytest.skip("fakeredis 未安装")

        # mock get_redis_client 返回 fakeredis
        with patch("src.skills.docbot.cache.get_redis_client", AsyncMock(return_value=fake_redis)):
            key = "docbot:agentinsight-docbot:user1:session1:code_learning:architecture"
            value = '{"summary": "test code learning"}'

            await write_cache(key, value, settings=mock_settings)
            result = await read_cache(key, settings=mock_settings)

            assert result == value

        await fake_redis.aclose()

    @pytest.mark.asyncio
    async def test_read_cache_miss_returns_none(self, mock_settings: MagicMock) -> None:
        """缓存未命中返回 None."""
        try:
            import fakeredis.aioredis

            fake_redis = fakeredis.aioredis.FakeRedis()
        except ImportError:
            pytest.skip("fakeredis 未安装")

        with patch("src.skills.docbot.cache.get_redis_client", AsyncMock(return_value=fake_redis)):
            result = await read_cache("nonexistent:key", settings=mock_settings)
            assert result is None

        await fake_redis.aclose()

    @pytest.mark.asyncio
    async def test_write_cache_redis_unavailable_no_raise(self, mock_settings: MagicMock) -> None:
        """Redis 不可用时 write_cache 不抛异常 (降级)."""
        with patch("src.skills.docbot.cache.get_redis_client", AsyncMock(return_value=None)):
            # 不应抛异常
            await write_cache("any:key", "value", settings=mock_settings)

    @pytest.mark.asyncio
    async def test_read_cache_redis_unavailable_returns_none(self, mock_settings: MagicMock) -> None:
        """Redis 不可用时 read_cache 返回 None."""
        with patch("src.skills.docbot.cache.get_redis_client", AsyncMock(return_value=None)):
            result = await read_cache("any:key", settings=mock_settings)
            assert result is None


class TestClearSessionCache:
    """clear_session_cache 按前缀删除测试."""

    @pytest.mark.asyncio
    async def test_clear_session_cache_deletes_matching_keys(self, mock_settings: MagicMock) -> None:
        """clear_session_cache 删除指定会话的所有缓存键."""
        try:
            import fakeredis.aioredis

            fake_redis = fakeredis.aioredis.FakeRedis()
        except ImportError:
            pytest.skip("fakeredis 未安装")

        with patch("src.skills.docbot.cache.get_redis_client", AsyncMock(return_value=fake_redis)):
            # 准备多个键: 属于该会话 + 不属于
            session_keys = [
                "docbot:agentinsight-docbot:user1:session1:code_learning:architecture",
                "docbot:agentinsight-docbot:user1:session1:outline:architecture",
                "docbot:agentinsight-docbot:user1:session1:content:architecture:0",
                "docbot:agentinsight-docbot:user1:session1:final:architecture",
            ]
            other_keys = [
                "docbot:agentinsight-docbot:user1:session2:code_learning:architecture",
                "docbot:agentinsight-docbot:user2:session1:code_learning:architecture",
            ]
            for k in session_keys + other_keys:
                await fake_redis.setex(k, 3600, "value")

            # 执行清理
            await clear_session_cache(
                agent_id="agentinsight-docbot",
                user_id="user1",
                session_id="session1",
                settings=mock_settings,
            )

            # 验证 session1 的所有键已被删除
            for k in session_keys:
                result = await fake_redis.get(k)
                assert result is None, f"键 {k} 应被删除"

            # 验证其他会话的键仍存在
            for k in other_keys:
                result = await fake_redis.get(k)
                assert result is not None, f"其他会话的键 {k} 不应被删除"

        await fake_redis.aclose()

    @pytest.mark.asyncio
    async def test_clear_session_cache_redis_unavailable_no_raise(self, mock_settings: MagicMock) -> None:
        """Redis 不可用时 clear_session_cache 不抛异常."""
        with patch("src.skills.docbot.cache.get_redis_client", AsyncMock(return_value=None)):
            await clear_session_cache(
                agent_id="agentinsight-docbot",
                user_id="user1",
                session_id="session1",
                settings=mock_settings,
            )


class TestDeleteCache:
    """delete_cache 单键删除测试."""

    @pytest.mark.asyncio
    async def test_delete_cache_existing_key(self, mock_settings: MagicMock) -> None:
        """delete_cache 删除已存在的键."""
        try:
            import fakeredis.aioredis

            fake_redis = fakeredis.aioredis.FakeRedis()
        except ImportError:
            pytest.skip("fakeredis 未安装")

        with patch("src.skills.docbot.cache.get_redis_client", AsyncMock(return_value=fake_redis)):
            key = "docbot:agentinsight-docbot:user1:session1:outline:architecture"
            await fake_redis.setex(key, 3600, "value")
            await delete_cache(key, settings=mock_settings)
            result = await fake_redis.get(key)
            assert result is None

        await fake_redis.aclose()

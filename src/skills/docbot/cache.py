"""docbot Redis 缓存键管理 (6 步流水线中间产物传递).

设计约束 (见 docs/DESIGN_AGENT.md 第 8 章与 AGENTS.md 第 7 章):
- 6 步流水线中间产物体积可能达数百 KB, 不直接放入 LangGraph state (避免 state 膨胀)
- 统一存 Redis (TTL 24 小时, 由 settings.docbot_cache_ttl 控制), state 仅存 cache_key
- 键格式: docbot:{agent_id}:{user_id}:{session_id}:{type}:{report_type}[:{chapter_idx}]
- type 取值: code_learning | outline | content | reviewed | merged | final

import 路径约定: 用绝对导入 (不是 from src.skills...)
"""

from __future__ import annotations

import logging

from src.common.redis_client import get_redis_client
from src.config.settings import Settings, get_settings
from src.observability.tracing import trace_chain

logger = logging.getLogger(__name__)

# 6 步流水线缓存类型全集 (type 字段允许值)
CACHE_TYPES: frozenset[str] = frozenset(
    {"code_learning", "outline", "content", "reviewed", "merged", "final"}
)

# 默认 TTL (24 小时), settings.docbot_cache_ttl 缺失时的兜底
_DEFAULT_TTL: int = 86400

# 缓存键前缀 (与 AGENTS.md 第 7 章 Redis 约定一致)
_KEY_PREFIX: str = "docbot"


def build_cache_key(
    agent_id: str,
    user_id: str,
    session_id: str,
    type_: str,
    report_type: str,
    chapter_idx: int | str | None = None,
) -> str:
    """构造缓存键.

    键格式: docbot:{agent_id}:{user_id}:{session_id}:{type}:{report_type}[:{chapter_idx}]

    Args:
        agent_id: Agent 标识 (固定 'agentinsight-docbot')
        user_id: 用户 ID
        session_id: 会话 ID (thread_id)
        type_: 缓存类型, 取值见 CACHE_TYPES
        report_type: 报告类型 (architecture/design/.../api_doc 共 8 种)
        chapter_idx: 章节索引 (仅 content/reviewed 类型需要, 0-based)

    Returns:
        缓存键字符串
    """
    if type_ not in CACHE_TYPES:
        raise ValueError(f"invalid_cache_type: {type_}, allowed: {sorted(CACHE_TYPES)}")
    parts = [_KEY_PREFIX, agent_id, user_id, session_id, type_, report_type]
    if chapter_idx is not None:
        parts.append(str(chapter_idx))
    return ":".join(parts)


def _resolve_ttl(settings: Settings | None, ttl: int | None) -> int:
    """解析 TTL: 显式传入优先, 否则取 settings.docbot_cache_ttl, 兜底 86400."""
    if ttl is not None:
        return int(ttl)
    if settings is not None:
        return int(getattr(settings, "docbot_cache_ttl", _DEFAULT_TTL))
    return _DEFAULT_TTL


async def write_cache(
    key: str,
    value: str,
    ttl: int | None = None,
    *,
    settings: Settings | None = None,
) -> None:
    """写入缓存 (字符串值).

    Args:
        key: 缓存键 (由 build_cache_key 构造)
        value: 缓存值 (字符串; 调用方负责 JSON 序列化)
        ttl: TTL 秒数; None 时取 settings.docbot_cache_ttl (默认 86400)
        settings: Settings 实例 (可选)
    """
    settings = settings or get_settings()
    resolved_ttl = _resolve_ttl(settings, ttl)
    async with trace_chain(
        name="docbot.cache.write",
        input={"key": key, "ttl": resolved_ttl, "value_len": len(value)},
    ) as span:
        redis = await get_redis_client(settings)
        if redis is None:
            span.update(metadata={"success": False, "reason": "redis_unavailable"})
            logger.warning("Redis 不可用, 跳过缓存写入: %s", key)
            return
        try:
            await redis.setex(key, resolved_ttl, value)
            span.update(output={"success": True})
        except Exception as e:  # noqa: BLE001
            span.update(metadata={"success": False, "error": str(e)})
            logger.warning("缓存写入失败 (不阻断): key=%s, error=%s", key, e)


async def read_cache(
    key: str,
    *,
    settings: Settings | None = None,
) -> str | None:
    """读取缓存 (字符串值).

    Args:
        key: 缓存键 (由 build_cache_key 构造)
        settings: Settings 实例 (可选)

    Returns:
        缓存值字符串; 未命中或 Redis 不可用时返回 None
    """
    settings = settings or get_settings()
    async with trace_chain(
        name="docbot.cache.read",
        input={"key": key},
    ) as span:
        redis = await get_redis_client(settings)
        if redis is None:
            span.update(output={"hit": False, "reason": "redis_unavailable"})
            return None
        try:
            raw = await redis.get(key)
        except Exception as e:  # noqa: BLE001
            span.update(output={"hit": False, "error": str(e)})
            logger.warning("缓存读取失败 (不阻断): key=%s, error=%s", key, e)
            return None
        if raw is None:
            span.update(output={"hit": False})
            return None
        span.update(output={"hit": True, "value_len": len(raw)})
        return raw


async def delete_cache(
    key: str,
    *,
    settings: Settings | None = None,
) -> None:
    """删除单个缓存键.

    Args:
        key: 缓存键 (由 build_cache_key 构造)
        settings: Settings 实例 (可选)
    """
    settings = settings or get_settings()
    async with trace_chain(
        name="docbot.cache.delete",
        input={"key": key},
    ):
        redis = await get_redis_client(settings)
        if redis is None:
            return
        try:
            await redis.delete(key)
        except Exception as e:  # noqa: BLE001
            logger.warning("缓存删除失败 (不阻断): key=%s, error=%s", key, e)


async def clear_session_cache(
    agent_id: str,
    user_id: str,
    session_id: str,
    *,
    settings: Settings | None = None,
) -> None:
    """删除会话所有 docbot 缓存 (按前缀扫描删除).

    会话清理时调用, 级联清理 6 步流水线所有中间产物.
    扫描模式: docbot:{agent_id}:{user_id}:{session_id}:*

    Args:
        agent_id: Agent 标识
        user_id: 用户 ID
        session_id: 会话 ID
        settings: Settings 实例 (可选)
    """
    settings = settings or get_settings()
    pattern = f"{_KEY_PREFIX}:{agent_id}:{user_id}:{session_id}:*"
    async with trace_chain(
        name="docbot.cache.clear_session",
        input={"pattern": pattern},
    ) as span:
        redis = await get_redis_client(settings)
        if redis is None:
            span.update(metadata={"success": False, "reason": "redis_unavailable"})
            return
        deleted_count = 0
        try:
            async for key in redis.scan_iter(match=pattern, count=100):
                await redis.delete(key)
                deleted_count += 1
            span.update(output={"deleted_count": deleted_count, "success": True})
            logger.info(
                "会话缓存已清理: agent_id=%s, user_id=%s, session_id=%s, deleted=%d",
                agent_id,
                user_id,
                session_id,
                deleted_count,
            )
        except Exception as e:  # noqa: BLE001
            span.update(metadata={"success": False, "error": str(e)})
            logger.warning("会话缓存清理失败 (不阻断): pattern=%s, error=%s", pattern, e)


__all__ = [
    "CACHE_TYPES",
    "build_cache_key",
    "write_cache",
    "read_cache",
    "delete_cache",
    "clear_session_cache",
]

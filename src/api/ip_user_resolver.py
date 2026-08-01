"""IP-based 用户身份解析 + 每日文档生成限额控制.

无 JWT Token 时, 按 IP 生成唯一且不变的 UserId.
- 1 个 IP 对应 1 个 UserId (确定性: SHA256 哈希, 不存储原始 IP)
- 每日文档生成限额从数据库 report_limits 表读取 (已从环境变量迁移)
  - 回退顺序: 用户专属 → Agent 级 → 全局系统默认 → settings → 硬编码默认 3
  - daily_limit=0 或缺失视为无效配置, 继续回退; 最终默认 3 (0 不表示「不限制」)
  - docbot Agent 级默认 daily_limit=3 (agent_id='agentinsight-docbot', user_id IS NULL)
- 每日使用次数从数据库 daily_report_usage 表读取 (已从 Redis 迁移)
  - 按 agent_id + user_id + 日期 记录当日文档生成份数
- 计数语义: 每个仓库 × 每个报告类型 = 1 份; 请求前按申请份数预检, 成功保存后按实际成功份数扣减
- 所有已解析 user_id (含 JWT) 均受限额约束
- 超限时友好提示用户

数据库降级策略: 数据库不可用时降级放行 (fail-open, 不阻断用户)
"""

from __future__ import annotations

import hashlib
import logging
from datetime import UTC, date, datetime, timedelta

logger = logging.getLogger(__name__)

# 硬编码默认日限额: 库内 0/缺失且 settings 亦无效时的最终兜底 (docbot Agent 默认 3)
_DEFAULT_DAILY_LIMIT = 3


def generate_user_id_from_ip(ip: str) -> str:
    """根据 IP 生成确定性 UserId (唯一且不变).

    SHA256 哈希, 优先取前 24 位 (96 bit, 碰撞概率远低于 16 位);
    若前 24 位无法保证唯一性 (理论上极小概率), 则使用完整 64 位哈希.
    加 "ip_" 前缀标识匿名用户.
    不存储原始 IP, 仅存储哈希 (PII 保护).

    Args:
        ip: 客户端 IP 地址
    Returns:
        形如 "ip_a1b2c3d4e5f6789012345678" 的 UserId
    """
    if not ip:
        ip = "0.0.0.0"
    hash_hex = hashlib.sha256(ip.encode("utf-8")).hexdigest()
    # 优先采用前 24 位 hex (96 bit, IPv4 全空间 ~4.3e9, 生日碰撞概率 < 1e-12)
    return f"ip_{hash_hex[:24]}"


def get_client_ip(request) -> str:
    """从请求中提取真实客户端 IP.

    优先级: X-Forwarded-For (第一个) > X-Real-IP > request.client.host

    Args:
        request: Starlette/FastAPI Request 对象
    Returns:
        客户端 IP 字符串
    """
    # X-Forwarded-For: client, proxy1, proxy2 (取第一个)
    xff = request.headers.get("X-Forwarded-For", "")
    if xff:
        return xff.split(",")[0].strip()
    # X-Real-IP
    xri = request.headers.get("X-Real-IP", "")
    if xri:
        return xri.strip()
    # 直连
    if request.client:
        return request.client.host
    return "0.0.0.0"


def _get_beijing_date() -> date:
    """获取北京时间 (UTC+8) 当日日期对象.

    与用户感知的"自然日"对齐.
    返回 datetime.date 对象 (非字符串), 因为 asyncpg 的 DATE 列
    需要 date 对象, 字符串会抛 AttributeError: 'str' object has no attribute 'toordinal'.
    """
    now_bj = datetime.now(UTC) + timedelta(hours=8)
    return now_bj.date()


def count_requested_docs(report_types: list[str] | None) -> int:
    """计算本次请求申请的文档份数.

    语义: 单次请求绑定一个仓库, 每个报告类型计 1 份; 去重后计数.
    """
    if not report_types:
        return 0
    # 保序去重, 避免重复类型重复计费
    return len(dict.fromkeys(str(t) for t in report_types if t))


def _fallback_limit_from_settings() -> int:
    """从 settings.ip_daily_report_limit 取兜底限额; <=0 时回退硬编码默认 3."""
    try:
        from src.config.settings import get_settings

        settings_limit = int(get_settings().ip_daily_report_limit)
    except Exception as e:  # noqa: BLE001
        logger.warning(
            "读取 settings.ip_daily_report_limit 失败, 使用默认 %d: %s",
            _DEFAULT_DAILY_LIMIT,
            e,
        )
        return _DEFAULT_DAILY_LIMIT
    if settings_limit > 0:
        return settings_limit
    return _DEFAULT_DAILY_LIMIT


async def _get_daily_limit_from_db(agent_id: str, user_id: str) -> int:
    """从数据库 report_limits 表读取每日报告限额.

    优先级回退 (任一级 daily_limit=0 视为无效并跳过):
    1. (agent_id, user_id) 精确匹配 (Agent + 用户专属限额)
    2. (agent_id, user_id IS NULL) (Agent 默认限额)
    3. (agent_id IS NULL, user_id IS NULL) (全局系统默认限额)

    若三者均不存在或均为 0, 返回 0 (表示无有效库配置, 由调用方继续回退到 settings/默认 3).
    """
    from src.memory.db_initializer import get_pool

    pool = await get_pool()
    async with pool.acquire() as conn:
        return await _fetch_daily_limit_from_conn(conn, agent_id, user_id)


async def _fetch_daily_limit_from_conn(conn, agent_id: str, user_id: str) -> int:
    """在已有连接上读取有效库限额 (NULL/0 跳过各级)."""
    # NULLIF(..., 0): 库内显式 0 与缺失同等视为无效, 继续下一级回退
    # LIMIT 1 防御: 历史脏数据可能含重复行
    row = await conn.fetchrow(
        """
        SELECT COALESCE(
            NULLIF((SELECT daily_limit FROM report_limits WHERE agent_id = $1 AND user_id = $2 LIMIT 1), 0),
            NULLIF((SELECT daily_limit FROM report_limits WHERE agent_id = $1 AND user_id IS NULL LIMIT 1), 0),
            NULLIF((SELECT daily_limit FROM report_limits WHERE agent_id IS NULL AND user_id IS NULL LIMIT 1), 0)
        ) AS effective_limit
        """,
        agent_id,
        user_id,
    )
    if row and row["effective_limit"] is not None:
        return int(row["effective_limit"])
    return 0


async def _resolve_effective_daily_limit(agent_id: str, user_id: str, conn=None) -> int:
    """解析最终有效日限额.

    回退顺序:
    1. 库: agent_id+user_id → agent_id+NULL → NULL+NULL (0 跳过)
    2. settings.ip_daily_report_limit (>0 时)
    3. 硬编码默认 3
    """
    if conn is not None:
        db_limit = await _fetch_daily_limit_from_conn(conn, agent_id, user_id)
    else:
        db_limit = await _get_daily_limit_from_db(agent_id, user_id)
    if db_limit > 0:
        return db_limit
    return _fallback_limit_from_settings()


async def check_daily_report_limit(
    user_id: str,
    agent_id: str,
    limit: int | None = None,  # noqa: ARG001 保留兼容旧调用签名, 数据库模式忽略
    *,
    requested_count: int = 1,
) -> tuple[bool, int, int]:
    """只读检查用户当日文档生成是否足以覆盖申请份数 (不扣减).

    生产路径: 请求入口预检 remaining >= requested_count;
    成功保存后再调用 increment_daily_report_count(delta=成功份数) 扣减.

    Args:
        user_id: 用户 ID (IP 生成的或 JWT 解析的)
        agent_id: Agent ID (即 agent_name, 多 Agent 数据隔离键)
        limit: 保留兼容旧调用, 数据库模式忽略此参数
        requested_count: 本次申请份数 (每个报告类型计 1 份, 默认 1)
    Returns:
        (allowed, current_count, daily_limit):
        - allowed=True 表示剩余次数足够完成本次申请
        - current_count 为当日已用次数
        - daily_limit 为有效限额 (始终 >0, 默认至少为 3)
    """
    try:
        req = max(1, int(requested_count or 1))
        effective_limit = await _resolve_effective_daily_limit(agent_id, user_id)
        current_count = await _get_daily_usage_from_db(agent_id, user_id)
        remaining = max(0, effective_limit - current_count)

        if remaining < req:
            logger.info(
                "用户 %s (agent=%s) 当日文档限额不足: 剩余 %d < 申请 %d (已用 %d/%d)",
                user_id,
                agent_id,
                remaining,
                req,
                current_count,
                effective_limit,
            )
            return False, current_count, effective_limit
        return True, current_count, effective_limit
    except Exception as e:  # noqa: BLE001
        # 数据库不可用时降级放行 (fail-open, 不阻断用户)
        logger.warning("每日限额检查失败 (降级放行): %s", e)
        return True, 0, _DEFAULT_DAILY_LIMIT


async def _get_daily_usage_from_db(agent_id: str, user_id: str) -> int:
    """从数据库 daily_report_usage 表读取当日使用次数.

    按 agent_id + user_id + 日期 三级隔离 (多 Agent 共享表, 各 Agent 各用户独立计数).
    """
    from src.memory.db_initializer import get_pool

    usage_date = _get_beijing_date()
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT daily_count FROM daily_report_usage "
            "WHERE agent_id = $1 AND user_id = $2 AND usage_date = $3",
            agent_id,
            user_id,
            usage_date,
        )
        if row:
            return int(row["daily_count"])
        return 0


async def increment_daily_report_count(
    user_id: str,
    agent_id: str,
    delta: int = 1,
) -> int:
    """文档生成成功后递增当日计数 (按成功保存的报告份数扣减).

    从数据库 daily_report_usage 表 upsert (agent_id + user_id + 日期).
    首次计数时 INSERT (daily_count=delta), 后续 UPDATE (daily_count + delta).

    异常向上抛出, 由调用方决定是否吞掉 (便于 routes.py 层记录可见日志).

    Args:
        user_id: 用户 ID
        agent_id: Agent ID (即 agent_name, 多 Agent 数据隔离键)
        delta: 本次成功保存的文档份数 (每个成功 report_type 计 1, 默认 1)
    Returns:
        递增后的计数值
    Raises:
        Exception: 数据库操作失败时向上抛出
    """
    from src.memory.db_initializer import get_pool

    add = max(0, int(delta or 0))
    if add <= 0:
        return await _get_daily_usage_from_db(agent_id, user_id)

    usage_date = _get_beijing_date()
    pool = await get_pool()
    async with pool.acquire() as conn:
        # INSERT ... ON CONFLICT 幂等 upsert
        # ON CONFLICT (agent_id, user_id, usage_date): 三级隔离键联合唯一约束
        row = await conn.fetchrow(
            """
            INSERT INTO daily_report_usage (agent_id, user_id, usage_date, daily_count)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (agent_id, user_id, usage_date)
            DO UPDATE SET daily_count = daily_report_usage.daily_count + $4
            RETURNING daily_count
            """,
            agent_id,
            user_id,
            usage_date,
            add,
        )
        new_count = int(row["daily_count"]) if row else 0
        logger.info(
            "用户 %s (agent=%s) 当日文档计数 +%d (当前 %d)",
            user_id,
            agent_id,
            add,
            new_count,
        )
        return new_count

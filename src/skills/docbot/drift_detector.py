"""P1-5.3.2 代码变更触发文档漂移检测.

职责:
1. 在仓库同步时, 获取当前 HEAD commit hash
2. 对比上次生成文档时的 commit hash (last_doc_commit_hash)
3. 若 commit 不同, 用 git diff --name-only 列出变更文件
4. 查询 report_citations 表中引用了变更文件的所有报告
5. 将这些报告标记为 is_stale=true, 记录 stale_reason

设计原则:
- 漂移检测不阻断同步流程, 失败时仅记录日志
- 仅当 last_doc_commit_hash 存在时才检测 (首次同步无文档生成记录时跳过)
- 检测结果写入 research_reports.is_stale / stale_reason / stale_detected_at

import 路径约定: 用绝对导入.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


async def detect_doc_drift(
    *,
    repo_id: str,
    user_id: str,
    agent_id: str,
    repo_path: str,
    adapter: Any,
    pool: Any,
    settings: Any | None = None,
) -> dict:
    """检测代码变更是否导致已生成文档过期.

    流程:
    1. 从 user_git_repos 读取 last_doc_commit_hash
    2. 获取当前 HEAD commit hash
    3. 若两者不同, 用 git diff 列出变更文件
    4. 查询 report_citations 中引用了变更文件的报告
    5. 将这些报告标记为 is_stale=true

    Args:
        repo_id: 仓库 ID
        user_id: 用户 ID
        agent_id: Agent ID
        repo_path: 仓库本地路径
        adapter: GitMCPAdapter 实例 (含 get_head_commit_hash / list_changed_files)
        pool: asyncpg 连接池
        settings: Settings 实例 (可选)

    Returns:
        {
            "detected": bool,  # 是否检测到漂移 (False 表示无漂移或跳过)
            "skipped": bool,   # 是否跳过 (无 last_doc_commit_hash 时)
            "current_commit": str | None,
            "last_doc_commit": str | None,
            "changed_files": list[str],
            "stale_reports": list[str],  # 被标记为 stale 的 report_id 列表
            "error": str | None,  # 异常信息 (不阻断流程)
        }
    """
    result: dict = {
        "detected": False,
        "skipped": False,
        "current_commit": None,
        "last_doc_commit": None,
        "changed_files": [],
        "stale_reports": [],
        "error": None,
    }

    try:
        # 1. 读取 last_doc_commit_hash
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT last_doc_commit_hash
                  FROM user_git_repos
                 WHERE id = $1 AND agent_id = $2 AND user_id = $3
                """,
                repo_id,
                agent_id,
                user_id,
            )
        if not row:
            result["skipped"] = True
            result["error"] = "user_git_repos 记录不存在"
            return result

        last_doc_commit = row.get("last_doc_commit_hash")
        result["last_doc_commit"] = last_doc_commit

        if not last_doc_commit:
            # 首次同步或未生成过文档, 跳过漂移检测
            result["skipped"] = True
            logger.info(
                "漂移检测跳过: 无 last_doc_commit_hash (repo_id=%s, 可能首次同步或未生成文档)",
                repo_id,
            )
            return result

        # 2. 获取当前 HEAD commit hash
        try:
            current_commit = await adapter.get_head_commit_hash(repo_path)
        except Exception as e:  # noqa: BLE001
            result["error"] = f"get_head_commit_hash 失败: {e}"
            logger.warning("漂移检测: 获取 HEAD commit 失败 (跳过): %s", e)
            return result

        result["current_commit"] = current_commit

        # 3. 对比 commit hash
        if current_commit == last_doc_commit:
            logger.info(
                "漂移检测: 代码无变更 (repo_id=%s, commit=%s)",
                repo_id,
                current_commit[:12],
            )
            return result

        # commit 不同, 检测变更文件
        logger.info(
            "漂移检测: 代码有变更 (repo_id=%s, last_doc=%s -> current=%s)",
            repo_id,
            last_doc_commit[:12],
            current_commit[:12],
        )

        # 4. 获取变更文件列表
        try:
            changed_files = await adapter.list_changed_files(
                repo_path=repo_path,
                from_commit=last_doc_commit,
                to_commit=current_commit,
            )
        except Exception as e:  # noqa: BLE001
            result["error"] = f"list_changed_files 失败: {e}"
            logger.warning("漂移检测: 获取变更文件失败 (标记全部文档为 stale): %s", e)
            # git diff 失败时, 保守标记该仓库所有文档为 stale
            changed_files = ["*"]  # 通配符, 表示全部文件

        result["changed_files"] = changed_files

        if not changed_files:
            logger.info(
                "漂移检测: commit 不同但无变更文件 (repo_id=%s, 可能仅 metadata 变更)",
                repo_id,
            )
            return result

        # 5. 查询引用了变更文件的报告并标记为 stale
        stale_reports = await _mark_stale_reports(
            pool=pool,
            agent_id=agent_id,
            user_id=user_id,
            changed_files=changed_files,
        )
        result["stale_reports"] = stale_reports
        result["detected"] = bool(stale_reports)

        if stale_reports:
            logger.warning(
                "漂移检测: 检测到 %d 个报告因代码变更而过期 (repo_id=%s, 变更文件 %d 个)",
                len(stale_reports),
                repo_id,
                len(changed_files),
            )
        else:
            logger.info(
                "漂移检测: 代码有变更但无报告引用变更文件 (repo_id=%s, 变更文件 %d 个)",
                repo_id,
                len(changed_files),
            )

    except Exception as e:  # noqa: BLE001
        result["error"] = f"漂移检测异常: {e}"
        logger.warning("漂移检测异常 (不阻断同步, repo_id=%s): %s", repo_id, e)

    return result


async def _mark_stale_reports(
    *,
    pool: Any,
    agent_id: str,
    user_id: str,
    changed_files: list[str],
) -> list[str]:
    """查询引用了变更文件的报告, 标记为 is_stale=true.

    Args:
        pool: asyncpg 连接池
        agent_id: Agent ID
        user_id: 用户 ID
        changed_files: 变更文件路径列表 (含 "*" 时标记全部)

    Returns:
        被标记为 stale 的 report_id 列表
    """
    # 通配符场景: 标记该用户+agent 的所有报告为 stale
    if "*" in changed_files:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                UPDATE research_reports
                   SET is_stale = TRUE,
                       stale_reason = 'code changed since last doc generation (git diff failed, conservative mark)',
                       stale_detected_at = NOW()
                 WHERE agent_id = $1 AND user_id = $2 AND is_stale = FALSE
                 RETURNING report_id::text
                """,
                agent_id,
                user_id,
            )
        return [r["report_id"] for r in rows]

    # 精确匹配场景: 通过 report_citations 反查引用了变更文件的报告
    # 使用 ANY 数组匹配, 避免 IN 子句过长
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            UPDATE research_reports
               SET is_stale = TRUE,
                   stale_reason = 'code changed since last doc generation (cited file modified)',
                   stale_detected_at = NOW()
             WHERE agent_id = $1 AND user_id = $2 AND is_stale = FALSE
               AND report_id IN (
                   SELECT DISTINCT rc.report_id
                     FROM report_citations rc
                    WHERE rc.agent_id = $1
                      AND rc.user_id = $2
                      AND rc.file_path = ANY($3::text[])
               )
             RETURNING report_id::text
            """,
            agent_id,
            user_id,
            changed_files,
        )
    return [r["report_id"] for r in rows]


async def update_last_doc_commit(
    *,
    pool: Any,
    repo_id: str,
    user_id: str,
    agent_id: str,
    commit_hash: str,
) -> None:
    """更新 last_doc_commit_hash (在文档生成成功后调用).

    Args:
        pool: asyncpg 连接池
        repo_id: 仓库 ID
        user_id: 用户 ID
        agent_id: Agent ID
        commit_hash: 当前 HEAD commit hash
    """
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE user_git_repos
                   SET last_doc_commit_hash = $4,
                       last_doc_synced_at = NOW()
                 WHERE id = $1 AND agent_id = $2 AND user_id = $3
                """,
                repo_id,
                agent_id,
                user_id,
                commit_hash,
            )
        logger.info(
            "已更新 last_doc_commit_hash (repo_id=%s, commit=%s)",
            repo_id,
            commit_hash[:12],
        )
    except Exception as e:  # noqa: BLE001
        logger.warning(
            "更新 last_doc_commit_hash 失败 (不阻断流程, repo_id=%s): %s",
            repo_id,
            e,
        )


__all__ = ["detect_doc_drift", "update_last_doc_commit"]

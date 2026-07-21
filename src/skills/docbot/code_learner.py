"""任务一技能: STRATEGIC LLM 深度学习用户代码仓库.

职责 (见 docs/DESIGN_AGENT.md 第 4.2 节与第 7.1 节):
1. 通过 GitMCPAdapter 克隆 / 拉取仓库 (复用 skills.docbot.repo_loader.clone_repo)
2. 构建文件索引 (复用 skills.docbot.repo_loader.build_file_index)
3. 选取关键文件并读取内容 (复用 select_key_files + read_files)
4. STRATEGIC LLM 学习, 输出结构化摘要: {summary, file_index, key_modules, dependencies, architecture_notes}
5. 写入 Redis 缓存 (由节点函数 c_code_learning_node 负责, 本技能返回 dict)

import 路径约定: 用绝对导入.
"""

from __future__ import annotations

import logging
from typing import Any

from src.llm.client import LLMClient, LLMTier, get_llm_client
from src.observability.tracing import trace_chain
from src.skills.docbot.repo_loader import (
    build_file_index,
    clone_repo,
    read_files,
    select_key_files,
)

logger = logging.getLogger(__name__)

# 代码学习 prompt 模板缺失时的兜底
_DEFAULT_PROMPT = """你是 {report_type} 类型技术文档的代码学习专家, 请深度学习以下代码仓库并输出结构化摘要.

## 文件索引

{file_index}

## 关键文件内容

{file_contents}

## 输出要求

输出结构化摘要, 包含:
1. 项目概览 (技术栈 / 架构模式 / 主要模块)
2. 关键模块说明 (模块职责 / 入口点)
3. 依赖关系 (内部模块间 + 外部依赖)
4. 架构笔记 (设计模式 / 数据流 / 关键约定)
"""


async def learn_code(
    *,
    repo_config: dict,
    repo_id: str,
    user_id: str,
    report_type: str,
    llm_session_id: str,
    settings: Any | None = None,
) -> dict:
    """任务一: STRATEGIC LLM 深度学习用户代码仓库.

    Args:
        repo_config: 仓库配置 (含 repo_url / auth_type / token / ...)
        repo_id: 仓库 ID
        user_id: 用户 ID
        report_type: 报告类型 (8 种之一, 决定学习侧重)
        llm_session_id: LLM 会话 ID (用于会话保持)
        settings: Settings 实例 (可选)

    Returns:
        {
            "summary": str (LLM 输出的结构化摘要, 供后续任务引用),
            "file_index": dict,
            "key_modules": list[str],
            "dependencies": list[str],
            "architecture_notes": str,
            "repo_path": str,
        }
    """
    async with trace_chain(
        name=f"docbot.code_learning.{report_type}",
        input={"repo_id": repo_id, "user_id": user_id, "report_type": report_type},
    ) as span:
        # 1. 克隆 / 拉取仓库
        repo_path = await clone_repo(repo_config, user_id, repo_id, settings=settings)
        span.update(metadata={"repo_path": repo_path})

        # 2. 构建文件索引
        file_index = await build_file_index(repo_path, settings=settings)
        span.update(metadata={"file_count": file_index.get("file_count", 0)})

        # 3. 选取关键文件 + 读取内容
        key_files = select_key_files(file_index, max_files=30)
        file_contents = await read_files(repo_path, key_files, settings=settings)
        span.update(
            metadata={
                "key_files_count": len(key_files),
                "file_contents_length": len(file_contents),
            }
        )

        # 4. 加载提示词模板
        prompt_template = _load_prompt_template()

        # 5. 构造 prompt
        prompt = prompt_template.format(
            report_type=report_type,
            file_index=file_index.get("summary", ""),
            file_contents=file_contents[:500_000],  # 截断防止超长
        )

        # 6. STRATEGIC LLM 学习
        llm = _get_llm(settings)
        messages = [{"role": "user", "content": prompt}]
        response = await llm.achat(
            messages,
            tier=LLMTier.STRATEGIC,
            session_id=llm_session_id,
            span_name=f"docbot.code_learning.{report_type}",
            step="code_learning",
        )

        # 7. 提取模块 + 依赖
        key_modules = _extract_modules(file_index)
        dependencies = _extract_dependencies(file_index)

        learning_result = {
            "summary": response.content,
            "file_index": file_index,
            "key_modules": key_modules,
            "dependencies": dependencies,
            "architecture_notes": response.content,
            "repo_path": repo_path,
        }
        span.update(output={"summary_length": len(response.content)})
        return learning_result


def _get_llm(settings: Any | None) -> LLMClient:
    """获取 LLMClient (settings 为 None 时用全局单例, 失败降级)."""
    try:
        if settings is not None:
            return LLMClient(settings)
        return get_llm_client()
    except Exception:  # noqa: BLE001
        return get_llm_client()


def _load_prompt_template() -> str:
    """加载 CODE_LEARNING_PROMPT 模板 (失败降级内置极简版)."""
    try:
        from src.config.docbot.prompts import CODE_LEARNING_PROMPT

        return CODE_LEARNING_PROMPT
    except Exception as e:  # noqa: BLE001
        logger.warning("加载 CODE_LEARNING_PROMPT 失败 (降级内置): %s", e)
        return _DEFAULT_PROMPT


def _extract_modules(file_index: dict) -> list[str]:
    """从文件索引提取顶级模块列表."""
    files = file_index.get("files", []) if isinstance(file_index, dict) else []
    modules: set[str] = set()
    for f in files:
        if not isinstance(f, dict):
            continue
        path = f.get("path", "")
        parts = path.split("/")
        if len(parts) > 1:
            top = parts[0]
            # 排除明显非模块的目录 (src/ tests/ docs/ examples/)
            if top not in {"src", "tests", "test", "docs", "examples", "example"}:
                modules.add(top)
    return sorted(modules)


def _extract_dependencies(file_index: dict) -> list[str]:
    """从文件索引提取依赖文件路径列表 (requirements.txt / package.json / go.mod 等)."""
    files = file_index.get("files", []) if isinstance(file_index, dict) else []
    deps: list[str] = []
    dep_names = {
        "requirements.txt",
        "package.json",
        "go.mod",
        "pom.xml",
        "Cargo.toml",
        "build.gradle",
        "pyproject.toml",
    }
    for f in files:
        if not isinstance(f, dict):
            continue
        name = f.get("name", "")
        if name in dep_names:
            deps.append(f.get("path", name))
    return deps


__all__ = ["learn_code"]

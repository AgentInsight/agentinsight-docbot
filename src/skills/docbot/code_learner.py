"""任务一技能: STRATEGIC LLM 深度学习用户代码仓库.

职责 (见 docs/DESIGN_AGENT.md 第 4.2 节与第 7.1 节):
1. 通过 GitMCPAdapter 克隆 / 拉取仓库 (复用 skills.docbot.repo_loader.clone_repo)
2. 构建文件索引 (复用 skills.docbot.repo_loader.build_file_index)
3. 选取关键文件并读取内容 (复用 select_key_files + read_files)
4. STRATEGIC LLM 学习, 输出结构化 JSON: {summary, key_modules, dependencies, architecture_notes}
5. 写入 Redis 缓存 (由节点函数 c_code_learning_node 负责, 本技能返回 dict)

优化 (参考业界开源智能体):
- 注入 persona (role_name / description) 让 LLM 从对应角色视角学习代码
- report_type 差异化学习侧重 (架构/设计/需求/测试/优化/性能/缺陷/API)
- 结构化 JSON 输出, 与下游 outline_refiner / content_filler 期望字段对齐
- 要求 LLM 标注文件路径:行号引用, 供下游精确引用代码

import 路径约定: 用绝对导入.
"""

from __future__ import annotations

import json
import logging
import re
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
_DEFAULT_PROMPT = """你是 {report_type} 类型技术文档的代码学习专家. 请深度学习以下代码仓库并输出结构化摘要.

## 文件索引

{file_index}

## 关键文件内容

{file_contents}

## 输出要求 (严格 JSON, 不要 markdown 代码块)
{{
  "summary": "Markdown 格式的整体摘要",
  "key_modules": [{{"name": "模块名", "path": "路径", "responsibility": "职责"}}],
  "dependencies": [{{"from": "模块A", "to": "模块B", "type": "import"}}],
  "architecture_notes": "架构笔记 Markdown"
}}
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
            "summary": str (LLM 输出的整体摘要, Markdown 格式),
            "file_index": dict,
            "key_modules": list[dict] (LLM 提取的模块列表, 含 name/path/responsibility),
            "dependencies": list[dict] (LLM 提取的依赖列表, 含 from/to/type),
            "architecture_notes": str (LLM 输出的架构笔记, Markdown 格式),
            "repo_path": str,
        }
    """
    async with trace_chain(
        name=f"docbot.code_learning.{report_type}",
        input={"repo_id": repo_id, "user_id": user_id, "report_type": report_type},
    ) as span:
        logger.info(
            "learn_code 开始: report_type=%s, repo_id=%s, user_id=%s, "
            "llm_session_id=%s, repo_url=%s",
            report_type, repo_id, user_id, llm_session_id,
            repo_config.get("repo_url", ""),
        )

        # 1. 克隆 / 拉取仓库
        logger.info("learn_code 步骤1: 克隆/拉取仓库 (report_type=%s)", report_type)
        try:
            repo_path = await clone_repo(repo_config, user_id, repo_id, settings=settings)
        except Exception as e:
            logger.exception(
                "learn_code 步骤1 失败: 克隆仓库异常. report_type=%s, repo_id=%s, "
                "repo_url=%s, error=%s: %s",
                report_type, repo_id, repo_config.get("repo_url", ""),
                type(e).__name__, e,
            )
            raise
        logger.info(
            "learn_code 步骤1 完成: repo_path=%s (report_type=%s)",
            repo_path, report_type,
        )
        span.update(metadata={"repo_path": repo_path})

        # 2. 构建文件索引
        logger.info("learn_code 步骤2: 构建文件索引 (report_type=%s)", report_type)
        file_index = await build_file_index(repo_path, settings=settings)
        file_count = file_index.get("file_count", 0)
        logger.info(
            "learn_code 步骤2 完成: file_count=%d, total_size_bytes=%d (report_type=%s)",
            file_count, file_index.get("total_size_bytes", 0), report_type,
        )
        if file_count == 0:
            logger.error(
                "learn_code 严重: 仓库文件数为 0, 可能仓库为空或克隆未完成. "
                "report_type=%s, repo_path=%s, repo_url=%s",
                report_type, repo_path, repo_config.get("repo_url", ""),
            )
        span.update(metadata={"file_count": file_count})

        # 3. 选取关键文件 + 读取内容
        key_files = select_key_files(file_index, max_files=30)
        logger.info(
            "learn_code 步骤3: 选取关键文件 %d 个 (report_type=%s)",
            len(key_files), report_type,
        )
        file_contents = await read_files(repo_path, key_files, settings=settings)
        logger.info(
            "learn_code 步骤3 完成: file_contents_length=%d (report_type=%s)",
            len(file_contents), report_type,
        )
        if not file_contents:
            logger.warning(
                "learn_code 警告: 关键文件内容为空. report_type=%s, key_files=%s",
                report_type, key_files[:5],
            )
        span.update(
            metadata={
                "key_files_count": len(key_files),
                "file_contents_length": len(file_contents),
            }
        )

        # 4. 加载提示词模板 + persona
        prompt_template = _load_prompt_template()
        role_name, description = _load_persona(report_type)
        logger.info(
            "learn_code 步骤4: prompt_template 长度=%d, role_name=%s (report_type=%s)",
            len(prompt_template), role_name, report_type,
        )

        # 5. 构造 prompt (注入 persona + report_type + 文件索引 + 文件内容)
        prompt = prompt_template.format(
            report_type=report_type,
            role_name=role_name,
            description=description,
            file_index=file_index.get("summary", ""),
            file_contents=file_contents[:500_000],  # 截断防止超长
        )
        logger.info(
            "learn_code 步骤5: prompt 构造完成, 长度=%d (report_type=%s)",
            len(prompt), report_type,
        )

        # 6. STRATEGIC LLM 学习
        llm = _get_llm(settings)
        messages = [{"role": "user", "content": prompt}]
        logger.info(
            "learn_code 步骤6: 调用 STRATEGIC LLM (report_type=%s, session_id=%s)",
            report_type, llm_session_id,
        )
        try:
            response = await llm.achat(
                messages,
                tier=LLMTier.STRATEGIC,
                session_id=llm_session_id,
                span_name=f"docbot.code_learning.{report_type}",
                step="code_learning",
            )
        except Exception as e:
            logger.exception(
                "learn_code 步骤6 失败: LLM 调用异常. report_type=%s, "
                "tier=STRATEGIC, error=%s: %s",
                report_type, type(e).__name__, e,
            )
            raise
        logger.info(
            "learn_code 步骤6 完成: LLM 响应 content_length=%d, model=%s, "
            "input_tokens=%d, output_tokens=%d (report_type=%s)",
            len(response.content or ""), response.model,
            response.input_tokens, response.output_tokens, report_type,
        )
        if not response.content:
            logger.error(
                "learn_code 严重: LLM 返回空 content. report_type=%s, model=%s",
                report_type, response.model,
            )

        # 7. 解析 LLM JSON 输出, 提取结构化字段
        parsed = _parse_learning_response(response.content)
        logger.info(
            "learn_code 步骤7: JSON 解析完成, parsed_keys=%s (report_type=%s)",
            list(parsed.keys()) if isinstance(parsed, dict) else "not_dict",
            report_type,
        )
        key_modules = parsed.get("key_modules", [])
        if not key_modules:
            # 降级: 从文件索引启发式提取
            key_modules = _extract_modules_fallback(file_index)
            logger.info(
                "learn_code 降级: key_modules 从文件索引启发式提取, count=%d (report_type=%s)",
                len(key_modules), report_type,
            )
        dependencies = parsed.get("dependencies", [])
        if not dependencies:
            # 降级: 从文件索引提取依赖文件路径
            dependencies = _extract_dependencies_fallback(file_index)
            logger.info(
                "learn_code 降级: dependencies 从文件索引提取, count=%d (report_type=%s)",
                len(dependencies), report_type,
            )

        learning_result = {
            "summary": parsed.get("summary", response.content),
            "file_index": file_index,
            "key_modules": key_modules,
            "dependencies": dependencies,
            "architecture_notes": parsed.get("architecture_notes", response.content),
            "repo_path": repo_path,
        }
        span.update(output={"summary_length": len(learning_result["summary"])})
        logger.info(
            "learn_code 全部完成: report_type=%s, summary_length=%d, "
            "key_modules=%d, dependencies=%d",
            report_type, len(learning_result["summary"]),
            len(key_modules), len(dependencies),
        )
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


def _load_persona(report_type: str) -> tuple[str, str]:
    """加载报告类型对应的 persona (role_name, description).

    失败时降级到通用 persona.
    """
    try:
        from src.config.docbot.personas import DOCBOT_REPORT_PERSONAS

        persona = DOCBOT_REPORT_PERSONAS.get(report_type, {})
        role_name = persona.get("role_name", "技术文档专家")
        description = persona.get("description", "生成结构完整的技术文档")
        return role_name, description
    except Exception as e:  # noqa: BLE001
        logger.warning("加载 persona 失败 (降级通用): %s", e)
        return "技术文档专家", "生成结构完整的技术文档"


def _parse_learning_response(content: str) -> dict:
    """解析 LLM 输出的 JSON 结构化摘要.

    期望格式:
    {
        "summary": "Markdown 文本",
        "key_modules": [{"name", "path", "responsibility", "key_symbols", "confidence"}],
        "dependencies": [{"from", "to", "type", "evidence"}],
        "architecture_notes": "Markdown 文本"
    }

    解析失败时降级: 把整个 content 作为 summary, 其他字段为空.
    """
    if not content:
        return {}

    # 尝试直接解析
    try:
        parsed = json.loads(content)
        if isinstance(parsed, dict):
            return parsed
    except (json.JSONDecodeError, TypeError):
        pass

    # 尝试从 markdown 代码块中提取 JSON
    json_block_pattern = re.compile(r"```(?:json)?\s*\n?(.*?)\n?```", re.DOTALL)
    match = json_block_pattern.search(content)
    if match:
        try:
            parsed = json.loads(match.group(1))
            if isinstance(parsed, dict):
                return parsed
        except (json.JSONDecodeError, TypeError):
            pass

    # 尝试提取第一个 { 到最后一个 } 之间的内容
    first_brace = content.find("{")
    last_brace = content.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        try:
            parsed = json.loads(content[first_brace : last_brace + 1])
            if isinstance(parsed, dict):
                return parsed
        except (json.JSONDecodeError, TypeError):
            pass

    logger.warning("LLM 输出 JSON 解析失败, 降级为纯文本 summary")
    return {"summary": content, "key_modules": [], "dependencies": [], "architecture_notes": content}


def _extract_modules_fallback(file_index: dict) -> list[dict]:
    """从文件索引启发式提取模块列表 (LLM 解析失败时降级用)."""
    files = file_index.get("files", []) if isinstance(file_index, dict) else []
    modules: dict[str, dict] = {}
    for f in files:
        if not isinstance(f, dict):
            continue
        path = f.get("path", "")
        parts = path.split("/")
        if len(parts) > 1:
            top = parts[0]
            # 排除明显非模块的目录 (src/ tests/ docs/ examples/)
            if top not in {"src", "tests", "test", "docs", "examples", "example"}:
                if top not in modules:
                    modules[top] = {
                        "name": top,
                        "path": top,
                        "responsibility": "",
                        "key_symbols": [],
                        "confidence": "low",
                    }
    return sorted(modules.values(), key=lambda m: m["name"])


def _extract_dependencies_fallback(file_index: dict) -> list[dict]:
    """从文件索引提取依赖文件列表 (LLM 解析失败时降级用)."""
    files = file_index.get("files", []) if isinstance(file_index, dict) else []
    deps: list[dict] = []
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
            deps.append({
                "from": name,
                "to": f.get("path", name),
                "type": "dependency_file",
                "evidence": f.get("path", name),
            })
    return deps


__all__ = ["learn_code"]

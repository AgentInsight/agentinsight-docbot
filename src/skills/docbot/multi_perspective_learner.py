"""P2-5.4.1 多视角代码审问 (借鉴 STORM).

职责:
1. 按 report_type 派生 3 个视角提问者 (perspectives.py)
2. 三阶段流程:
   - 阶段1 (FAST LLM): 每个视角生成 5-8 个针对性问题
   - 阶段2 (SMART LLM): 每个视角回答自己的问题
   - 阶段3 (STRATEGIC LLM): 汇总 3 个视角问答 → 统一结构化摘要
3. 并发执行 3 个视角的提问与回答 (asyncio.gather)
4. 失败降级: 任意视角失败返回部分结果; 全部失败抛异常由调用方回退到 learn_code

设计约束:
- 返回结构与 code_learner.learn_code 完全一致 (向后兼容)
- 复用 code_learner 的辅助函数 (_get_llm / _load_persona / _parse_learning_response 等)
- 复用 repo_map / code_graph 上下文 (P1-5.2.1 / P1-5.2.2 成果)
- 成本控制: 提问阶段仅用 repo_map+code_graph (无 file_contents), 回答阶段截断 file_contents 到 100K
- 遵循 AGENTS.md: skills 不依赖 graph, 纯函数 + 关键字参数

import 路径约定: 用绝对导入.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any

from src.llm.client import LLMTier
from src.observability.tracing import trace_chain
from src.skills.docbot.code_graph import CodeGraph, format_code_graph_for_prompt
from src.skills.docbot.code_learner import (
    _extract_dependencies_fallback,
    _extract_modules_fallback,
    _get_llm,
    _load_persona,
    _parse_learning_response,
)
from src.skills.docbot.repo_map import generate_repo_map

logger = logging.getLogger(__name__)

# 回答阶段 file_contents 截断阈值 (100K, 控制成本)
_MAX_FILE_CONTENTS_FOR_ANSWER = 100_000

# 视角问答结果最大字符数 (汇总阶段输入截断)
_MAX_PERSPECTIVE_QA_CHARS = 50_000

# 汇总阶段 perspective_qa 单视角截断
_MAX_QA_PER_PERSPECTIVE = 15_000


async def learn_code_multi_perspective(
    *,
    repo_config: dict,
    repo_id: str,
    user_id: str,
    report_type: str,
    llm_session_id: str,
    repo_path: str,
    file_index: dict,
    file_contents: str,
    code_graph_obj: CodeGraph,
    settings: Any | None = None,
    project_metadata: dict | None = None,
    project_metadata_text: str = "",
    terminology_glossary: dict | None = None,
    glossary_text: str = "",
    http_endpoints: list | None = None,
    enum_definitions: list | None = None,
    endpoints_text: str = "",
    enums_text: str = "",
    scopes: dict | None = None,
    scopes_text: str = "",
    config_specs: dict | None = None,
    config_specs_text: str = "",
) -> dict:
    """多视角代码审问主入口.

    本函数假设上游已完成: 仓库克隆 / 文件索引构建 / 关键文件读取 / repo_map 生成 / code_graph 构建.
    这些步骤与 code_learner.learn_code 共享, 由调用方决定是否复用.

    Args:
        repo_config: 仓库配置 (含 repo_url 等)
        repo_id: 仓库 ID
        user_id: 用户 ID
        report_type: 报告类型 (8 种之一)
        llm_session_id: LLM 会话 ID
        repo_path: 仓库本地路径
        file_index: build_file_index 返回的索引
        file_contents: read_files 返回的关键文件内容
        code_graph_obj: build_code_graph 返回的 CodeGraph 实例
        settings: Settings 实例 (可选)

    Returns:
        与 code_learner.learn_code 完全一致的结构:
        {
            "summary": str,
            "file_index": dict,
            "key_modules": list[dict],
            "dependencies": list[dict],
            "architecture_notes": str,
            "repo_path": str,
        }
    """
    async with trace_chain(
        name=f"docbot.multi_perspective_learning.{report_type}",
        input={"repo_id": repo_id, "user_id": user_id, "report_type": report_type},
    ) as span:
        logger.info(
            "multi_perspective_learning 开始: report_type=%s, repo_id=%s",
            report_type,
            repo_id,
        )

        # 准备共享上下文
        # v6-P0-C: 传 code_graph_obj 启用 PageRank 排序 (核心模块优先)
        repo_map = generate_repo_map(repo_path, file_index, code_graph=code_graph_obj)
        code_graph_text = format_code_graph_for_prompt(code_graph_obj)
        file_index_summary = file_index.get("summary", "")

        span.update(
            metadata={
                "repo_map_length": len(repo_map),
                "code_graph_text_length": len(code_graph_text),
            }
        )

        # 加载视角配置
        perspectives = _load_perspectives(report_type)
        perspective_count = len(perspectives)
        logger.info(
            "multi_perspective_learning 视角数=%d, perspectives=%s (report_type=%s)",
            perspective_count,
            [p.get("role") for p in perspectives],
            report_type,
        )

        # 阶段 1+2 并发: 每个视角先生成问题再回答
        llm = _get_llm(settings)
        perspective_tasks = [
            _generate_and_answer(
                perspective=p,
                report_type=report_type,
                llm_session_id=llm_session_id,
                repo_map=repo_map,
                code_graph_text=code_graph_text,
                file_index_summary=file_index_summary,
                file_contents=file_contents[:_MAX_FILE_CONTENTS_FOR_ANSWER],
                llm=llm,
            )
            for p in perspectives
        ]
        perspective_qa_list = await asyncio.gather(*perspective_tasks, return_exceptions=True)

        # 过滤失败的视角 (异常视角降级为空 qa)
        valid_qa_list: list[dict] = []
        failed_count = 0
        for i, qa in enumerate(perspective_qa_list):
            if isinstance(qa, Exception):
                failed_count += 1
                logger.warning(
                    "multi_perspective_learning 视角 %s 失败: %s: %s (report_type=%s)",
                    perspectives[i].get("role"),
                    type(qa).__name__,
                    qa,
                    report_type,
                )
            elif isinstance(qa, dict) and qa.get("answers"):
                valid_qa_list.append(qa)

        logger.info(
            "multi_perspective_learning 阶段1+2 完成: valid=%d, failed=%d (report_type=%s)",
            len(valid_qa_list),
            failed_count,
            report_type,
        )
        span.update(
            metadata={
                "valid_perspectives": len(valid_qa_list),
                "failed_perspectives": failed_count,
            }
        )

        # 所有视角都失败时抛异常, 由调用方降级到 learn_code
        if not valid_qa_list:
            raise RuntimeError(f"所有视角均失败 (report_type={report_type}), 无法汇总")

        # 阶段 3: STRATEGIC LLM 汇总
        perspective_qa_text = _format_perspective_qa(valid_qa_list)
        role_name, description = _load_persona(report_type)

        synthesis_result = await _synthesize(
            role_name=role_name,
            description=description,
            report_type=report_type,
            llm_session_id=llm_session_id,
            perspective_qa=perspective_qa_text,
            perspective_count=len(valid_qa_list),
            repo_map=repo_map,
            code_graph_text=code_graph_text,
            file_index_summary=file_index_summary,
            llm=llm,
        )

        # 解析汇总结果
        parsed = _parse_learning_response(synthesis_result)
        key_modules = parsed.get("key_modules", [])
        if not key_modules:
            key_modules = _extract_modules_fallback(file_index)
            logger.info(
                "multi_perspective_learning 降级: key_modules 从文件索引提取, count=%d",
                len(key_modules),
            )
        dependencies = parsed.get("dependencies", [])
        if not dependencies:
            dependencies = _extract_dependencies_fallback(file_index)
            logger.info(
                "multi_perspective_learning 降级: dependencies 从文件索引提取, count=%d",
                len(dependencies),
            )

        learning_result = {
            "summary": parsed.get("summary", synthesis_result),
            "file_index": file_index,
            "key_modules": key_modules,
            "dependencies": dependencies,
            "architecture_notes": parsed.get("architecture_notes", synthesis_result),
            "repo_path": repo_path,
            # v5-P0-A: 补充 repo_map 和 code_graph
            "repo_map": repo_map,
            "code_graph": {
                "nodes": [
                    {
                        "name": n.name,
                        "file_path": n.file_path,
                        "kind": n.kind,
                        "signature": n.signature,
                    }
                    for n in code_graph_obj.nodes.values()
                ],
                "edges": [
                    {
                        "source": e.source,
                        "target": e.target,
                        "edge_type": e.edge_type,
                        "evidence": e.evidence,
                    }
                    for e in code_graph_obj.edges
                ],
                "module_deps": {
                    k: sorted(v) for k, v in code_graph_obj.module_deps.items()
                },
            },
            # v12: 与单视角 learn_code 对齐
            "project_metadata": project_metadata or {},
            "project_metadata_text": project_metadata_text,
            "terminology_glossary": terminology_glossary or {},
            "glossary_text": glossary_text,
            "http_endpoints": http_endpoints or [],
            "enum_definitions": enum_definitions or [],
            "endpoints_text": endpoints_text,
            "enums_text": enums_text,
            "scopes": scopes or {},
            "scopes_text": scopes_text,
            "config_specs": config_specs or {},
            "config_specs_text": config_specs_text,
        }
        # v2-P0-C: 透传类型专属字段
        try:
            from src.config.docbot.learning_focus import (
                LEARNING_SCHEMA_VERSION,
                extract_type_specific_fields,
            )

            type_specific = extract_type_specific_fields(report_type, parsed)
            learning_result["learning_schema_version"] = LEARNING_SCHEMA_VERSION
            learning_result["type_specific"] = type_specific
            learning_result.update(type_specific)
        except Exception as e:  # noqa: BLE001
            logger.warning("multi_perspective 类型字段提取失败 (降级跳过): %s", e)

        span.update(output={"summary_length": len(learning_result["summary"])})        logger.info(
            "multi_perspective_learning 全部完成: report_type=%s, "
            "valid_perspectives=%d, summary_length=%d, repo_map_length=%d, code_graph_nodes=%d",
            report_type,
            len(valid_qa_list),
            len(learning_result["summary"]),
            len(repo_map),
            len(code_graph_obj.nodes),
        )
        return learning_result


# ========== 阶段 1+2: 单视角生成问题 + 回答 ==========


async def _generate_and_answer(
    *,
    perspective: dict[str, object],
    report_type: str,
    llm_session_id: str,
    repo_map: str,
    code_graph_text: str,
    file_index_summary: str,
    file_contents: str,
    llm: Any,
) -> dict:
    """单视角的提问 + 回答流程.

    Returns:
        {
            "role": str,
            "focus": str,
            "questions": list[str],
            "answers": list[dict],  # [{question, answer, citations, confidence}]
        }
    """
    role = str(perspective.get("role", "未知视角"))
    focus = str(perspective.get("focus", ""))
    question_topics_list = perspective.get("question_topics", [])
    if isinstance(question_topics_list, list):
        question_topics = "\n".join(f"- {t}" for t in question_topics_list)
    else:
        question_topics = str(question_topics_list)

    # 阶段 1: FAST LLM 生成问题
    questions = await _generate_questions(
        role=role,
        focus=focus,
        question_topics=question_topics,
        report_type=report_type,
        llm_session_id=llm_session_id,
        repo_map=repo_map,
        code_graph_text=code_graph_text,
        file_index_summary=file_index_summary,
        llm=llm,
    )
    logger.info(
        "multi_perspective_learning 视角 %s 生成问题 %d 个 (report_type=%s)",
        role,
        len(questions),
        report_type,
    )

    if not questions:
        logger.warning(
            "multi_perspective_learning 视角 %s 未生成问题, 跳过回答阶段",
            role,
        )
        return {"role": role, "focus": focus, "questions": [], "answers": []}

    # 阶段 2: SMART LLM 回答问题
    answers = await _answer_questions(
        role=role,
        perspective_role=role,
        questions=questions,
        report_type=report_type,
        llm_session_id=llm_session_id,
        repo_map=repo_map,
        code_graph_text=code_graph_text,
        file_contents=file_contents,
        llm=llm,
    )
    logger.info(
        "multi_perspective_learning 视角 %s 回答问题 %d 个 (report_type=%s)",
        role,
        len(answers),
        report_type,
    )

    return {
        "role": role,
        "focus": focus,
        "questions": questions,
        "answers": answers,
    }


async def _generate_questions(
    *,
    role: str,
    focus: str,
    question_topics: str,
    report_type: str,
    llm_session_id: str,
    repo_map: str,
    code_graph_text: str,
    file_index_summary: str,
    llm: Any,
) -> list[str]:
    """阶段 1: FAST LLM 生成针对性问题."""
    from src.config.docbot.prompts import MULTI_PERSPECTIVE_QUESTION_PROMPT

    prompt = MULTI_PERSPECTIVE_QUESTION_PROMPT.format(
        role=role,
        focus=focus,
        question_topics=question_topics,
        report_type=report_type,
        repo_map=repo_map,
        code_graph=code_graph_text,
        file_index=file_index_summary,
    )

    messages = [{"role": "user", "content": prompt}]
    response = await llm.achat(
        messages,
        tier=LLMTier.FAST,
        session_id=llm_session_id,
        span_name=f"docbot.multi_perspective.question.{role}",
        step="multi_perspective_question",
    )

    parsed = _parse_json_response(response.content)
    questions = parsed.get("questions", [])
    if not isinstance(questions, list):
        return []
    return [str(q) for q in questions if q]


async def _answer_questions(
    *,
    role: str,
    perspective_role: str,
    questions: list[str],
    report_type: str,
    llm_session_id: str,
    repo_map: str,
    code_graph_text: str,
    file_contents: str,
    llm: Any,
) -> list[dict]:
    """阶段 2: SMART LLM 回答问题."""
    from src.config.docbot.prompts import MULTI_PERSPECTIVE_ANSWER_PROMPT

    questions_text = "\n".join(f"{i + 1}. {q}" for i, q in enumerate(questions))
    prompt = MULTI_PERSPECTIVE_ANSWER_PROMPT.format(
        role=role,
        perspective_role=perspective_role,
        questions=questions_text,
        repo_map=repo_map,
        code_graph=code_graph_text,
        file_contents=file_contents,
    )

    messages = [{"role": "user", "content": prompt}]
    response = await llm.achat(
        messages,
        tier=LLMTier.SMART,
        session_id=llm_session_id,
        span_name=f"docbot.multi_perspective.answer.{role}",
        step="multi_perspective_answer",
    )

    parsed = _parse_json_response(response.content)
    answers = parsed.get("answers", [])
    if not isinstance(answers, list):
        return []
    return [a for a in answers if isinstance(a, dict)]


async def _synthesize(
    *,
    role_name: str,
    description: str,
    report_type: str,
    llm_session_id: str,
    perspective_qa: str,
    perspective_count: int,
    repo_map: str,
    code_graph_text: str,
    file_index_summary: str,
    llm: Any,
) -> str:
    """阶段 3: STRATEGIC LLM 汇总多视角问答."""
    from src.config.docbot.learning_focus import (
        format_extra_schema,
        format_learning_focus,
    )
    from src.config.docbot.prompts import MULTI_PERSPECTIVE_SYNTHESIS_PROMPT

    prompt = MULTI_PERSPECTIVE_SYNTHESIS_PROMPT.format(
        role_name=role_name,
        description=description,
        report_type=report_type,
        learning_focus=format_learning_focus(report_type),
        output_schema_extra=format_extra_schema(report_type),
        perspective_count=perspective_count,
        perspective_qa=perspective_qa,
        repo_map=repo_map,
        code_graph=code_graph_text,
        file_index=file_index_summary,
    )

    messages = [{"role": "user", "content": prompt}]
    response = await llm.achat(
        messages,
        tier=LLMTier.STRATEGIC,
        session_id=llm_session_id,
        span_name=f"docbot.multi_perspective.synthesis.{report_type}",
        step="multi_perspective_synthesis",
    )
    return response.content or ""


# ========== 辅助函数 ==========


def _load_perspectives(report_type: str) -> list[dict[str, object]]:
    """加载视角配置 (失败降级到空列表)."""
    try:
        from src.config.docbot.perspectives import get_perspectives

        return get_perspectives(report_type)
    except Exception as e:  # noqa: BLE001
        logger.warning("加载 perspectives 失败 (降级空列表): %s", e)
        return []


def _parse_json_response(content: str) -> dict:
    """解析 LLM JSON 响应 (三层降级, 复用 code_learner 的解析逻辑).

    与 _parse_learning_response 不同: 本函数用于解析 questions/answers 结构,
    失败时返回空 dict (而非把 content 作为 summary).
    """
    if not content:
        return {}

    # 直接解析
    try:
        parsed = json.loads(content)
        if isinstance(parsed, dict):
            return parsed
    except (json.JSONDecodeError, TypeError):
        pass

    # 从 markdown 代码块提取
    json_block_pattern = re.compile(r"```(?:json)?\s*\n?(.*?)\n?```", re.DOTALL)
    match = json_block_pattern.search(content)
    if match:
        try:
            parsed = json.loads(match.group(1))
            if isinstance(parsed, dict):
                return parsed
        except (json.JSONDecodeError, TypeError):
            pass

    # 提取首尾大括号间内容
    first_brace = content.find("{")
    last_brace = content.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        try:
            parsed = json.loads(content[first_brace : last_brace + 1])
            if isinstance(parsed, dict):
                return parsed
        except (json.JSONDecodeError, TypeError):
            pass

    logger.warning("LLM JSON 解析失败, 返回空 dict")
    return {}


def _format_perspective_qa(qa_list: list[dict]) -> str:
    """格式化多视角问答结果为汇总 prompt 输入文本.

    每个视角截断到 _MAX_QA_PER_PERSPECTIVE 字符, 总长度截断到 _MAX_PERSPECTIVE_QA_CHARS.
    """
    sections: list[str] = []
    total_chars = 0

    for qa in qa_list:
        role = qa.get("role", "未知视角")
        focus = qa.get("focus", "")
        questions = qa.get("questions", [])
        answers = qa.get("answers", [])

        section_lines = [f"## 视角: {role} (关注: {focus})"]

        # 问答对
        for i, ans in enumerate(answers):
            if not isinstance(ans, dict):
                continue
            q = ans.get("question", questions[i] if i < len(questions) else "")
            a = ans.get("answer", "")
            citations = ans.get("citations", [])
            confidence = ans.get("confidence", "medium")

            citation_text = ", ".join(citations) if isinstance(citations, list) else str(citations)
            section_lines.append(f"### Q{i + 1}: {q}")
            section_lines.append(f"答: {a}")
            if citation_text:
                section_lines.append(f"引用: {citation_text}")
            section_lines.append(f"置信度: {confidence}")

        section = "\n".join(section_lines)
        # 单视角截断
        if len(section) > _MAX_QA_PER_PERSPECTIVE:
            section = section[:_MAX_QA_PER_PERSPECTIVE] + "\n... (truncated)"

        if total_chars + len(section) > _MAX_PERSPECTIVE_QA_CHARS:
            sections.append("... (后续视角已截断)")
            break

        sections.append(section)
        total_chars += len(section)

    return "\n\n".join(sections)


__all__ = ["learn_code_multi_perspective"]

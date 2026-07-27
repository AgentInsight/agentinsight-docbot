"""子智能体 A: 协调入口.

职责 (见 docs/DESIGN_AGENT.md 第 3.1 节):
1. 解析用户消息中的 JSON 指令 (action=generate_docs)
2. 校验 repo_id / report_types / report_format / language
3. 生成 trace_agent 根 span
4. 返回派发参数 (不在此节点派发 B 子图, 由 spawn_b_tasks 负责)

import 路径约定: 用绝对导入 (不是 from src.agents...)
"""

from __future__ import annotations

import json
import logging
from typing import Any

from src.observability.tracing import trace_agent

logger = logging.getLogger(__name__)

# 支持的报告类型全集 (8 种, 见 AGENTS.md 第 7 章)
_VALID_REPORT_TYPES: frozenset[str] = frozenset(
    {
        "architecture",
        "design",
        "requirements",
        "testcase",
        "optimization",
        "performance",
        "defect",
        "api_doc",
    }
)

# 支持的输出格式全集 (5 种, 见 AGENTS.md 第 1 章)
_VALID_REPORT_FORMATS: frozenset[str] = frozenset({"markdown", "html", "pdf", "docx", "json"})

# 支持的语言全集 (2 种, 见 AGENTS.md 第 7 章)
_VALID_LANGUAGES: frozenset[str] = frozenset({"zh", "en"})

# 单次请求最大报告类型数 (与 settings.max_chapters_per_report 配合控制成本)
_MAX_REPORT_TYPES_PER_REQUEST: int = 8


class CoordinatorA:
    """子智能体 A: 协调入口.

    节点函数 coordinator_a_node 调用本类 run() 方法,
    解析 JSON 指令 + 校验参数 + 建立根 trace span.
    """

    def __init__(self, settings: Any | None = None) -> None:
        # settings 延迟到 run() 时由节点函数注入, 此处仅保存引用
        self.settings = settings

    async def run(self, state: dict, *, settings: Any | None = None) -> dict:
        """执行协调入口逻辑.

        支持两种入口:
        1. routes.py 预解析入口: state 已含 repo_id/report_types/report_format/language
           (routes.py _parse_docbot_instruction 已校验), messages 可能为空
        2. 原始 messages 入口: state.messages 非空, 含 JSON 指令字符串

        优先使用 state 中已注入的字段 (入口1), 避免重复解析;
        state 中无 repo_id 时降级从 messages 解析 (入口2).

        Args:
            state: 顶层 DocbotState (dict 形式)
            settings: Settings 实例 (可选, 优先于构造时注入)

        Returns:
            delta dict, 含 repo_id / report_types / report_format / language / iteration_count
            或 errors (校验失败时)
        """
        async with trace_agent(
            name="docbot.coordinator_a",
            input={"messages": state.get("messages", [])},
            metadata={
                "session_id": state.get("session_id", ""),
                "intent": "generate_docs",
                "agent_id": state.get("agent_id", ""),
            },
            session_id=state.get("session_id"),
            user_id=state.get("user_id"),
        ) as span:
            # 入口1: routes.py 预解析, state 已含 repo_id/report_types
            repo_id = state.get("repo_id", "")
            report_types = state.get("report_types", [])
            report_format = state.get("report_format", "markdown")
            language = state.get("language", "zh")

            # 入口2: state 无 repo_id 时从 messages 解析 JSON 指令
            if not repo_id:
                messages = state.get("messages") or []
                if not messages:
                    error = "empty_messages"
                    span.update(output={"error": error})
                    return {"errors": [error]}

                last_message = messages[-1]
                content = self._extract_content(last_message)

                try:
                    instruction = json.loads(content)
                except (json.JSONDecodeError, TypeError) as e:
                    error = f"invalid_instruction: {e}"
                    span.update(output={"error": error})
                    return {"errors": [error]}

                if not isinstance(instruction, dict):
                    error = "instruction_not_dict"
                    span.update(output={"error": error})
                    return {"errors": [error]}

                if instruction.get("action") != "generate_docs":
                    error = f"unsupported_action: {instruction.get('action')}"
                    span.update(output={"error": error})
                    return {"errors": [error]}

                repo_id = instruction.get("repo_id", "")
                report_types = instruction.get("report_types", [])
                report_format = instruction.get("report_format", "markdown")
                language = instruction.get("language", "zh")

            errors: list[str] = []
            if not repo_id or not isinstance(repo_id, str):
                errors.append("missing_or_invalid_repo_id")
            if not report_types or not isinstance(report_types, list):
                errors.append("missing_or_invalid_report_types")
            else:
                invalid_types = set(report_types) - _VALID_REPORT_TYPES
                if invalid_types:
                    errors.append(f"invalid_report_types: {sorted(invalid_types)}")
                if len(report_types) > _MAX_REPORT_TYPES_PER_REQUEST:
                    errors.append(
                        f"too_many_report_types: {len(report_types)} > {_MAX_REPORT_TYPES_PER_REQUEST}"
                    )

            if not isinstance(report_format, str) or report_format not in _VALID_REPORT_FORMATS:
                errors.append(f"invalid_report_format: {report_format}")

            if not isinstance(language, str) or language not in _VALID_LANGUAGES:
                errors.append(f"invalid_language: {language}")

            if errors:
                span.update(output={"errors": errors})
                return {"errors": errors}

            # 校验通过后, 从 DB 加载并解密仓库配置 (供 c_code_learning_node 按需克隆)
            # 延迟导入避免 agents/ 反向依赖 api/
            from src.api.repo_routes import _fetch_repo_row, _load_repo_config
            from src.memory.db_initializer import get_pool

            user_id = state.get("user_id", "")
            agent_id = state.get("agent_id", "agentinsight-docbot")
            repo_config: dict[str, Any] = {}
            if user_id and agent_id:
                try:
                    pool = await get_pool()
                    row = await _fetch_repo_row(pool, repo_id, user_id, agent_id)
                    if row:
                        repo_config = _load_repo_config(row)
                except Exception as e:  # noqa: BLE001
                    logger.warning("coordinator_a 加载 repo_config 失败: %s", e)

            if not repo_config or not repo_config.get("repo_url"):
                error = f"repo_not_found: {repo_id}"
                span.update(output={"error": error})
                return {"errors": [error]}

            span.update(
                output={
                    "repo_id": repo_id,
                    "report_types": report_types,
                    "report_format": report_format,
                    "language": language,
                }
            )
            return {
                "repo_id": repo_id,
                "report_types": report_types,
                "report_format": report_format,
                "language": language,
                "iteration_count": 1,
                "_repo_config": repo_config,
            }

    @staticmethod
    def _extract_content(message: Any) -> str:
        """从消息对象提取 content 字符串.

        兼容 dict / BaseMessage / 其他对象.
        """
        if isinstance(message, dict):
            return str(message.get("content", ""))
        # 兼容 langchain-core BaseMessage 等对象
        content = getattr(message, "content", None)
        if content is None:
            return ""
        return str(content)


__all__ = ["CoordinatorA"]

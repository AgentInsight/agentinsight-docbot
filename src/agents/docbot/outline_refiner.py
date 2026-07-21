"""子智能体 C: 纲要细化 (任务二).

职责 (见 docs/DESIGN_AGENT.md 第 4.3 节与第 7.2 节):
1. 读取 code_learning_cache (任务一产物)
2. 通过 config.docbot.outlines.load_outline(report_type) 加载默认大纲
3. STRATEGIC LLM 根据代码上下文细化大纲 (增删改章节)
4. 输出 chapters: [{idx, title, sections, key_points}]
5. 写入 outline_cache

import 路径约定: 用绝对导入.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from src.llm.client import LLMClient, LLMTier, get_llm_client
from src.observability.tracing import trace_chain

logger = logging.getLogger(__name__)


class OutlineRefinerC:
    """子智能体 C: 纲要细化.

    节点函数 c_outline_refine_node 调用本类 refine_outline() 方法.
    使用 STRATEGIC LLM 在默认大纲基础上根据代码上下文细化.
    """

    def __init__(self, settings: Any | None = None) -> None:
        self.settings = settings
        # LLMClient 构造支持 settings 参数 (dataclass field default_factory)
        # 但为兼容 settings 为 None 的场景, 显式延迟到首次调用时获取
        try:
            self.llm: LLMClient = LLMClient(settings) if settings is not None else get_llm_client()
        except Exception:  # noqa: BLE001
            self.llm = get_llm_client()

    async def run(self, state: dict, *, settings: Any | None = None) -> dict:
        """执行纲要细化 (节点函数调用入口).

        本方法签名遵循任务约束 "每个类需有 async def run(self, state, *, settings=None) -> dict".
        实际细化逻辑委托给 refine_outline().

        Args:
            state: ReportTaskState
            settings: Settings 实例 (可选)

        Returns:
            delta dict: {outline_cache_key, chapters, current_chapter_idx}
            (本方法返回 chapters 供节点函数写入 state; outline_cache_key 由节点函数构造)
        """
        s = settings or self.settings
        report_type = state.get("report_type", "unknown")
        language = state.get("language", "zh")

        # 从缓存读取任务一产物 (节点函数已写好 cache_key, 此处简化为直接传 code_learning)
        # 实际节点函数会先 read_cache 再传入; 此处接收 dict 或 cache_key 字符串
        code_learning = state.get("_code_learning_data", {})
        if not code_learning:
            logger.warning("OutlineRefinerC 收到空 code_learning, 使用空字典降级")

        outline = await self.refine_outline(
            code_learning=code_learning,
            report_type=report_type,
            language=language,
            llm_session_id=state.get("llm_session_id", ""),
            settings=s,
        )
        return {"chapters": outline.get("chapters", []), "current_chapter_idx": 0}

    async def refine_outline(
        self,
        code_learning: dict | str,
        report_type: str,
        language: str,
        llm_session_id: str,
        settings: Any | None = None,
    ) -> dict:
        """细化纲要 (供节点函数直接调用).

        Args:
            code_learning: 任务一代码学习摘要 (dict 或 cache_key 字符串)
            report_type: 报告类型 (8 种之一)
            language: 输出语言 (zh|en)
            llm_session_id: LLM 会话 ID
            settings: Settings 实例 (可选)

        Returns:
            {"chapters": [{idx, title, sections, key_points}]}
        """
        async with trace_chain(
            name=f"docbot.outline_refine.{report_type}",
            input={"report_type": report_type, "language": language},
        ) as span:
            # 1. 加载默认大纲 (从 docs/{PREFIX}_OUTLINE.md, 由 config.docbot.outlines 提供)
            default_outline: list[dict] = []
            try:
                from src.config.docbot.outlines import load_outline

                default_outline = load_outline(report_type)
            except Exception as e:  # noqa: BLE001
                logger.warning("加载默认大纲失败 (降级空大纲): %s", e)
                default_outline = []

            # 2. 加载 persona (从 config.docbot.personas)
            persona: dict[str, str] = {}
            try:
                from src.config.docbot.personas import DOCBOT_REPORT_PERSONAS

                persona = DOCBOT_REPORT_PERSONAS.get(report_type, {})
            except Exception as e:  # noqa: BLE001
                logger.warning("加载 persona 失败 (降级空 persona): %s", e)

            # 3. 加载提示词模板 (从 config.docbot.prompts)
            prompt_template: str = ""
            try:
                from src.config.docbot.prompts import OUTLINE_REFINE_PROMPT

                prompt_template = OUTLINE_REFINE_PROMPT
            except Exception as e:  # noqa: BLE001
                logger.warning("加载 OUTLINE_REFINE_PROMPT 失败: %s", e)
                prompt_template = self._default_prompt()

            # 4. 提取代码学习摘要文本 (兼容 dict / str)
            code_summary = self._extract_summary(code_learning)

            # 5. 构造 prompt
            prompt = prompt_template.format(
                role_name=persona.get("role_name", "技术文档专家"),
                description=persona.get("description", ""),
                report_type=report_type,
                language=language,
                default_outline=default_outline,
                code_summary=code_summary[:50_000],
                key_modules=code_learning.get("key_modules", [])
                if isinstance(code_learning, dict)
                else [],
                dependencies=code_learning.get("dependencies", [])
                if isinstance(code_learning, dict)
                else [],
            )

            # 6. STRATEGIC LLM 细化纲要
            messages = [{"role": "user", "content": prompt}]
            response = await self.llm.achat(
                messages,
                tier=LLMTier.STRATEGIC,
                session_id=llm_session_id,
                span_name=f"docbot.outline_refine.{report_type}",
                step="outline_refine",
            )

            # 7. 解析 JSON 输出 (失败降级使用默认大纲)
            outline = self._parse_outline(response.content, default_outline)
            span.update(
                output={
                    "chapter_count": len(outline.get("chapters", [])),
                    "fallback": outline.get("_fallback", False),
                }
            )
            return outline

    @staticmethod
    def _extract_summary(code_learning: dict | str) -> str:
        """从 code_learning 提取 summary 文本 (兼容 dict / str)."""
        if isinstance(code_learning, dict):
            return str(code_learning.get("summary", ""))
        return str(code_learning)

    @staticmethod
    def _default_prompt() -> str:
        """提示词模板缺失时的兜底 (极简版)."""
        return (
            "你是 {role_name}，{description}\n\n"
            "请基于以下信息细化 {report_type} 类型技术文档的纲要:\n\n"
            "默认大纲: {default_outline}\n\n"
            "代码仓库学习摘要: {code_summary}\n\n"
            "目标语言: {language}\n\n"
            '输出 JSON: {{"chapters": [{{"idx": 0, "title": "", "sections": [], "key_points": []}}]}}'
        )

    @staticmethod
    def _parse_outline(content: str, default_outline: list[dict]) -> dict:
        """解析 LLM 输出的 JSON 纲要, 失败降级使用默认大纲."""
        try:
            outline = json.loads(content)
            if isinstance(outline, dict) and "chapters" in outline:
                chapters = outline["chapters"]
                if isinstance(chapters, list) and chapters:
                    return {"chapters": chapters}
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning("LLM 纲要 JSON 解析失败 (降级默认大纲): %s", e)
        return {"chapters": default_outline, "_fallback": True}


__all__ = ["OutlineRefinerC"]

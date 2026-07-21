"""子智能体 F: 合并去重 (任务五).

职责 (见 docs/DESIGN_AGENT.md 第 4.6 节与第 7.5 节):
1. 读取所有 reviewed_cache_keys 内容 (任务四产物)
2. SMART LLM 合并所有章节 + 去除重复内容 (术语定义 / 代码示例等)
3. 统一术语和格式
4. 生成目录 (TOC)
5. 保持逻辑连贯
6. 写入 merged_cache

import 路径约定: 用绝对导入.
"""

from __future__ import annotations

import logging
from typing import Any

from src.llm.client import LLMClient, LLMTier, get_llm_client
from src.observability.tracing import trace_chain

logger = logging.getLogger(__name__)


class MergerF:
    """子智能体 F: 合并去重.

    节点函数 f_merge_node 调用本类 merge_chapters() 方法.
    使用 SMART LLM 合并所有 reviewed 章节 + 去重 + 统一术语.
    """

    def __init__(self, settings: Any | None = None) -> None:
        self.settings = settings
        try:
            self.llm: LLMClient = LLMClient(settings) if settings is not None else get_llm_client()
        except Exception:  # noqa: BLE001
            self.llm = get_llm_client()

    async def run(self, state: dict, *, settings: Any | None = None) -> dict:
        """执行合并去重 (节点函数调用入口).

        本方法签名遵循任务约束. 实际合并逻辑委托给 merge_chapters().
        节点函数负责构造 cache_key + 写缓存, 本方法返回合并结果 dict.
        """
        s = settings or self.settings
        reviewed_data = state.get("_reviewed_data_list", [])
        chapters = state.get("chapters", [])

        result = await self.merge_chapters(
            reviewed_chapters=reviewed_data,
            chapters=chapters,
            report_type=state.get("report_type", ""),
            language=state.get("language", "zh"),
            llm_session_id=state.get("llm_session_id", ""),
            settings=s,
        )
        return {"_merged_result": result}

    async def merge_chapters(
        self,
        reviewed_chapters: list[dict],
        chapters: list[dict],
        report_type: str,
        language: str,
        llm_session_id: str,
        settings: Any | None = None,
    ) -> dict:
        """合并所有章节.

        Args:
            reviewed_chapters: 任务四产物列表 [{chapter_idx, content_md, image_svgs, ...}]
            chapters: 章节定义列表 [{idx, title, ...}]
            report_type: 报告类型
            language: 输出语言 (zh|en)
            llm_session_id: LLM 会话 ID
            settings: Settings 实例 (可选)

        Returns:
            {content_md, image_svgs, toc}
        """
        async with trace_chain(
            name=f"docbot.merge.{report_type}",
            input={"chapter_count": len(reviewed_chapters)},
        ) as span:
            # 1. 拼接所有章节内容 (按 chapter_idx 排序确保顺序)
            sorted_chapters = sorted(
                reviewed_chapters,
                key=lambda c: c.get("chapter_idx", 0) if isinstance(c, dict) else 0,
            )
            all_content = self._concat_chapters(sorted_chapters)

            # 2. 加载提示词模板
            prompt_template = self._load_prompt_template()

            # 3. 构造 prompt
            prompt = prompt_template.format(
                report_type=report_type,
                language=language,
                chapter_count=len(sorted_chapters),
                all_content=all_content,
            )

            # 4. SMART LLM 合并 + 去重
            messages = [{"role": "user", "content": prompt}]
            response = await self.llm.achat(
                messages,
                tier=LLMTier.SMART,
                session_id=llm_session_id,
                span_name=f"docbot.merge.{report_type}",
                step="merge",
            )

            # 5. 收集所有图片 (保留章节级图片)
            all_images: list[str] = []
            for ch in sorted_chapters:
                if isinstance(ch, dict):
                    imgs = ch.get("image_svgs", [])
                    if isinstance(imgs, list):
                        all_images.extend(imgs)

            # 6. 生成目录 (基于章节定义)
            toc = self._build_toc(chapters)

            span.update(
                output={
                    "merged_length": len(response.content),
                    "image_count": len(all_images),
                    "input_length": len(all_content),
                }
            )
            return {
                "content_md": response.content,
                "image_svgs": all_images,
                "toc": toc,
            }

    @staticmethod
    def _concat_chapters(sorted_chapters: list[dict]) -> str:
        """拼接所有章节内容为单一文本."""
        parts: list[str] = []
        for ch in sorted_chapters:
            if not isinstance(ch, dict):
                continue
            content_md = ch.get("content_md", "")
            if not content_md:
                continue
            # 提取首行作为标题分隔
            first_line = content_md.split("\n", 1)[0] if content_md else ""
            parts.append(f"{first_line}\n\n{content_md}")
        return "\n\n---\n\n".join(parts)

    def _load_prompt_template(self) -> str:
        """加载 MERGE_PROMPT 模板 (失败降级内置极简版)."""
        try:
            from src.config.docbot.prompts import MERGE_PROMPT

            return MERGE_PROMPT
        except Exception as e:  # noqa: BLE001
            logger.warning("加载 MERGE_PROMPT 失败 (降级内置): %s", e)
            return self._default_prompt()

    @staticmethod
    def _default_prompt() -> str:
        """提示词模板缺失时的兜底."""
        return (
            "你是技术文档合并专家, 正在合并 {report_type} 类型文档的所有章节:\n\n"
            "章节数量: {chapter_count}\n\n"
            "待合并内容:\n{all_content}\n\n"
            "目标语言: {language}\n\n"
            "要求: 按章节顺序合并, 去除重复内容, 统一术语, 生成目录, 保持逻辑连贯.\n"
            "输出 Markdown 格式的完整文档."
        )

    @staticmethod
    def _build_toc(chapters: list[dict]) -> list[int | str]:
        """生成目录 (章节 idx 列表)."""
        toc: list[int | str] = []
        for ch in chapters:
            if isinstance(ch, dict):
                toc.append(ch.get("idx", ""))
        return toc


__all__ = ["MergerF"]

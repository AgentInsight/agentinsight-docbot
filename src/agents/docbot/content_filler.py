"""子智能体 D: 内容填充 (任务三).

职责 (见 docs/DESIGN_AGENT.md 第 4.4 节与第 7.3 节):
1. 读取 outline_cache + code_learning_cache
2. 取当前章节 chapters[current_chapter_idx]
3. RAG 检索 (BM25 + Vector + RRF + 可选 Rerank), namespace 按 user_id + repo_id 隔离
4. SMART LLM 填充章节内容 (markdown 格式)
5. 按需生成 SVG 配图 (使用从 AIR 拷贝的 ImageGenerator)
6. 写入 content_cache_keys[current_chapter_idx]
7. current_chapter_idx += 1

import 路径约定: 用绝对导入.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from src.llm.client import LLMClient, LLMTier, get_llm_client
from src.observability.tracing import trace_chain, trace_retriever

logger = logging.getLogger(__name__)

# 触发配图的章节标题关键词 (架构图 / 流程图 / 部署图等)
_IMAGE_TRIGGER_KEYWORDS: tuple[str, ...] = (
    "架构",
    "流程",
    "拓扑",
    "结构",
    "部署",
    "数据流",
    "模块",
    "architecture",
    "flow",
    "topology",
    "structure",
    "deployment",
    "dataflow",
)


class ContentFillerD:
    """子智能体 D: 内容填充.

    节点函数 d_content_fill_node 调用本类 fill_chapter() 方法.
    使用 SMART LLM + RAG 检索 + 可选 SVG 配图.
    RAG 检索 namespace 按 user_id + repo_id 隔离, 确保多仓库场景下不串数据.
    """

    def __init__(self, settings: Any | None = None) -> None:
        self.settings = settings
        try:
            self.llm: LLMClient = LLMClient(settings) if settings is not None else get_llm_client()
        except Exception:  # noqa: BLE001
            self.llm = get_llm_client()
        # 延迟初始化 retriever / image_generator, 避免模块加载时强依赖外部服务
        self._retriever: Any = None
        self._image_generator: Any = None
        # 章节级语义去重 (P0: 跨章节去重, 同一 ContentFillerD 实例共享)
        self._dedup_compressor: Any = None
        self._dedup_lock: asyncio.Lock = asyncio.Lock()

    def _get_retriever(self) -> Any:
        """延迟初始化 HybridRetriever (从 AIR 拷贝)."""
        if self._retriever is None:
            try:
                from src.rag.retriever import HybridRetriever

                self._retriever = HybridRetriever(self.settings)
            except Exception as e:  # noqa: BLE001
                logger.warning("HybridRetriever 初始化失败 (降级无 RAG): %s", e)
                self._retriever = None
        return self._retriever

    def _get_image_generator(self) -> Any:
        """延迟初始化 ImageGenerator (从 AIR 拷贝)."""
        if self._image_generator is None:
            try:
                from src.skills.researcher.image_generator import ImageGenerator

                self._image_generator = ImageGenerator(self.settings)
            except Exception as e:  # noqa: BLE001
                logger.warning("ImageGenerator 初始化失败 (降级无配图): %s", e)
                self._image_generator = None
        return self._image_generator

    def _get_dedup_compressor(self) -> Any:
        """延迟初始化 WrittenContentCompressor (P0: 章节级语义去重).

        同一 ContentFillerD 实例共享 compressor, 跨 fill_chapter 调用累积
        _written_embeddings, 实现章节间去重. 初始化失败降级为 None, 调用方
        据此跳过去重逻辑.
        """
        if self._dedup_compressor is None:
            try:
                from src.skills.docbot.dedup import WrittenContentCompressor

                self._dedup_compressor = WrittenContentCompressor(self.settings)
            except Exception as e:  # noqa: BLE001
                logger.warning("WrittenContentCompressor 初始化失败 (降级无去重): %s", e)
                self._dedup_compressor = None
        return self._dedup_compressor

    @staticmethod
    def _split_chunks(text: str, max_chunk_len: int = 500) -> list[str]:
        """将文本按段落分割为 chunk (用于章节级语义去重).

        不同于 WrittenContentCompressor.compute_embedding 内部的 recursive_split
        (chunk_size=1000, 用于 embedding), 此处 max_chunk_len=500 用于在
        check_and_update_partial 返回 filtered_content 后的二次拼接校验.
        当前实现保留以兼容优化方案文档的步骤 3, 实际去重走 compute_embedding
        的 recursive_split.
        """
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        chunks: list[str] = []
        current = ""
        for para in paragraphs:
            if len(current) + len(para) > max_chunk_len and current:
                chunks.append(current)
                current = para
            else:
                current = f"{current}\n\n{para}" if current else para
        if current:
            chunks.append(current)
        return chunks

    async def run(self, state: dict, *, settings: Any | None = None) -> dict:
        """执行章节内容填充 (节点函数调用入口).

        本方法签名遵循任务约束. 实际填充逻辑委托给 fill_chapter().
        节点函数负责构造 cache_key + 写缓存, 本方法返回章节内容 dict.
        """
        s = settings or self.settings
        idx = state.get("current_chapter_idx", 0)
        chapters = state.get("chapters", [])
        if idx >= len(chapters):
            return {}

        chapter = chapters[idx]
        result = await self.fill_chapter(
            chapter=chapter,
            code_learning=state.get("_code_learning_data", {}),
            report_type=state.get("report_type", ""),
            language=state.get("language", "zh"),
            repo_id=state.get("repo_id", ""),
            user_id=state.get("user_id", ""),
            llm_session_id=state.get("llm_session_id", ""),
            settings=s,
        )
        return {"_chapter_result": result, "current_chapter_idx": idx + 1}

    async def fill_chapter(
        self,
        chapter: dict,
        code_learning: dict,
        report_type: str,
        language: str,
        repo_id: str,
        user_id: str,
        llm_session_id: str,
        settings: Any | None = None,
    ) -> dict:
        """填充单个章节内容.

        Args:
            chapter: 章节定义 {idx, title, sections, key_points}
            code_learning: 任务一代码学习摘要
            report_type: 报告类型
            language: 输出语言 (zh|en)
            repo_id: 仓库 ID (用于 RAG namespace 隔离)
            user_id: 用户 ID
            llm_session_id: LLM 会话 ID
            settings: Settings 实例 (可选)

        Returns:
            {chapter_idx, content_md, image_svgs}
        """
        chapter_idx = chapter.get("idx", 0)
        chapter_title = chapter.get("title", "")
        async with trace_chain(
            name=f"docbot.content_fill.{report_type}.{chapter_idx}",
            input={"chapter": chapter_title},
        ) as span:
            # 1. RAG 检索 (用户私有代码索引, namespace 含 user_id + repo_id 隔离)
            rag_context = await self._retrieve_rag_context(
                chapter=chapter,
                report_type=report_type,
                user_id=user_id,
                repo_id=repo_id,
                chapter_idx=chapter_idx,
            )

            # 2. 加载提示词模板
            prompt_template = self._load_prompt_template()
            code_summary = (
                code_learning.get("summary", "") if isinstance(code_learning, dict) else ""
            )

            # 3. 构造 prompt
            prompt = prompt_template.format(
                chapter_title=chapter_title,
                chapter_purpose=chapter.get("purpose", ""),
                chapter_sections=chapter.get("sections", []),
                key_points=chapter.get("key_points", []),
                chapter_example=chapter.get("example", ""),
                language=language,
                code_summary=code_summary[:50_000],  # 截断防止超长
                rag_context=rag_context,
            )

            # 4. SMART LLM 填充内容
            messages = [{"role": "user", "content": prompt}]
            response = await self.llm.achat(
                messages,
                tier=LLMTier.SMART,
                session_id=llm_session_id,
                span_name=f"docbot.content_fill.{report_type}.{chapter_idx}",
                step="content_fill",
            )
            content_md = response.content

            # 4.5 P0: 章节级语义去重 (跨章节消除重复内容, 术语定义 / 代码示例等)
            # 同一 ContentFillerD 实例共享 _dedup_compressor, 累积已写入 chunks embedding
            # 降级策略: compressor 初始化失败或 embedding 失败时保留原文, 不阻断主流程
            content_md = await self._dedup_chapter_content(content_md, chapter_title)

            # 5. 按需生成 SVG 配图
            image_svgs: list[str] = []
            if self._should_generate_image(chapter):
                svg = await self._generate_image_for_chapter(
                    chapter_title=chapter_title,
                    report_type=report_type,
                    language=language,
                    user_id=user_id,
                )
                if svg:
                    image_svgs.append(svg)

            span.update(
                output={
                    "content_length": len(content_md),
                    "image_count": len(image_svgs),
                    "rag_context_length": len(rag_context),
                }
            )
            return {
                "chapter_idx": chapter_idx,
                "content_md": content_md,
                "image_svgs": image_svgs,
            }

    async def _dedup_chapter_content(self, content_md: str, chapter_title: str) -> str:
        """对章节内容做跨章节语义去重 (P0: WrittenContentCompressor 集成).

        使用 check_and_update_partial 做 chunk 级去重:
        - 所有 chunk 都相似: 返回占位文本 (章节保留, 内容标记为去重跳过)
        - 部分 chunk 相似: 只保留不相似的 chunk (filtered_content)
        - 无相似 chunk: 全部保留 (original_content)
        - 任何异常降级: 保留原文, 不阻断主流程

        Args:
            content_md: LLM 生成的章节内容
            chapter_title: 章节标题 (用于日志)

        Returns:
            去重后的内容 (可能为占位文本 / 部分保留 / 全部保留)
        """
        if not content_md or not content_md.strip():
            return content_md

        compressor = self._get_dedup_compressor()
        if compressor is None:
            return content_md

        try:
            # 锁外 I/O: 计算 chunk embeddings (FastEmbed 本地模型)
            chunks, content_embs = await compressor.compute_embedding(content_md)
            if not chunks or not content_embs:
                # embedding 失败 (降级), 保留原文
                return content_md

            # 锁内 numpy 比对: 跨章节语义去重
            async with self._dedup_lock:
                keep, filtered_content = compressor.check_and_update_partial(
                    chunks, content_embs
                )

            if not keep:
                logger.info("章节 '%s' 内容与已写章节高度相似, 已去重跳过", chapter_title)
                return f"## {chapter_title}\n\n*此章节内容与已写章节高度相似, 已去重跳过。*"
            if filtered_content != content_md:
                logger.info("章节 '%s' 部分内容去重, 保留差异部分", chapter_title)
                return filtered_content
            return content_md
        except Exception as e:  # noqa: BLE001
            logger.warning("章节 '%s' 去重失败 (降级保留原文): %s", chapter_title, e)
            return content_md

    async def _retrieve_rag_context(
        self,
        chapter: dict,
        report_type: str,
        user_id: str,
        repo_id: str,
        chapter_idx: int,
    ) -> str:
        """RAG 检索相关代码片段 (namespace 按 user_id + repo_id 隔离)."""
        retriever = self._get_retriever()
        if retriever is None:
            return ""

        # 检索查询: 章节标题 + key_points
        query_parts = [chapter.get("title", "")]
        query_parts.extend(chapter.get("key_points", []))
        query = " ".join(str(p) for p in query_parts if p)

        async with trace_retriever(
            name=f"docbot.rag.{report_type}.{chapter_idx}",
            input={"query": query[:200], "user_id": user_id, "repo_id": repo_id},
            metadata={"retriever_type": "hybrid", "namespace_strategy": "user_repo_isolated"},
            user_id=user_id,
        ) as rag_span:
            try:
                # docbot 多仓库隔离: 传 repo_id 让 retriever 走 build_repo_namespaces 路径
                # namespace = {agent_id}:{user_id}:{repo_id}, 跨仓库不可见
                results = await retriever.retrieve(
                    query=query,
                    user_id=user_id,
                    repo_id=repo_id,
                    top_k=20,
                )
            except Exception as e:  # noqa: BLE001
                logger.warning("RAG 检索失败 (降级空上下文): %s", e)
                rag_span.update(output={"matched": 0, "error": str(e)})
                return ""

            matched = len(results) if isinstance(results, list) else 0
            top_score = (
                results[0].get("score", 0.0) if matched and isinstance(results[0], dict) else 0.0
            )
            rag_span.update(
                output={"matched": matched},
                metadata={
                    "candidate_count": matched,
                    "retriever_type": "hybrid",
                    "top_score": top_score,
                },
            )
            # 取 Top-5 拼接为上下文
            top_results = results[:5] if isinstance(results, list) else []
            return "\n\n".join(
                r.get("content", "")
                for r in top_results
                if isinstance(r, dict) and r.get("content")
            )

    def _load_prompt_template(self) -> str:
        """加载 CONTENT_FILL_PROMPT 模板 (失败降级内置极简版)."""
        try:
            from src.config.docbot.prompts import CONTENT_FILL_PROMPT

            return CONTENT_FILL_PROMPT
        except Exception as e:  # noqa: BLE001
            logger.warning("加载 CONTENT_FILL_PROMPT 失败 (降级内置): %s", e)
            return self._default_prompt()

    @staticmethod
    def _default_prompt() -> str:
        """提示词模板缺失时的兜底."""
        return (
            "你是技术文档撰写专家, 正在填充以下章节的详细内容:\n\n"
            "章节标题: {chapter_title}\n"
            "章节小节: {chapter_sections}\n"
            "关键点: {key_points}\n\n"
            "代码仓库学习摘要 (节选):\n{code_summary}\n\n"
            "相关代码片段 (RAG 检索结果):\n{rag_context}\n\n"
            "目标语言: {language}\n\n"
            "请使用 Markdown 格式输出 (含 ## 章节标题)."
        )

    @staticmethod
    def _should_generate_image(chapter: dict) -> bool:
        """判断章节是否适合配图 (架构图 / 流程图 / 部署图等)."""
        title = str(chapter.get("title", "")).lower()
        return any(kw in title for kw in _IMAGE_TRIGGER_KEYWORDS)

    async def _generate_image_for_chapter(
        self,
        chapter_title: str,
        report_type: str,
        language: str,
        user_id: str,
    ) -> str:
        """为章节生成 SVG 配图 (失败时返回空字符串, 不阻断主流程)."""
        image_gen = self._get_image_generator()
        if image_gen is None:
            return ""
        try:
            result = await image_gen.generate_image(
                prompt=chapter_title,
                topic=chapter_title,
                language=language,
                user_id=user_id,
            )
            # ImageGenerator 返回 dict, SVG 模式含 svg 字段
            if isinstance(result, dict):
                svg = result.get("svg")
                if isinstance(svg, str) and svg:
                    return svg
            return ""
        except Exception as e:  # noqa: BLE001
            logger.warning("SVG 配图生成失败 (降级无图): %s", e)
            return ""


__all__ = ["ContentFillerD"]

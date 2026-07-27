"""已写入内容去重器 (从 AIR 拷贝, 用于 docbot 章节级语义去重).

来源: agentinsight-researcher/src/skills/researcher/context_manager.py:557-1090
迁移改动:
1. _cosine_similarity_batch 原为 ContextManager 静态方法, 改为 WrittenContentCompressor 自身静态方法
2. check_and_update / check_and_update_partial 内部调用从 ContextManager._cosine_similarity_batch
   改为 WrittenContentCompressor._cosine_similarity_batch
3. 依赖 docbot 项目已有的 rag/fastembed_client.py / rag/embeddings_filter.py / observability/tracing.py

设计原则:
1. chunk 级去重 (切成 chunks 后逐 chunk 比对), 非整篇判断
2. FastEmbed (bge-small-zh-v1.5, 512维) 本地模型, 无远程 API 调用
3. numpy 矩阵批量余弦相似度, 替代 O(N*M) 双重 for 循环
4. LRU 缓存 (8192 项), 用 sha256(chunk) 作 key 避免重复嵌入
5. 锁粒度优化: compute_embedding (锁外 I/O) + check_and_update (锁内 numpy 比对)
"""

from __future__ import annotations

import hashlib
import logging
from collections import OrderedDict

import numpy as np

from src.config.settings import Settings, get_settings
from src.observability.tracing import trace_embedding
from src.rag.fastembed_client import FastEmbedClient, get_fastembed_client

logger = logging.getLogger(__name__)


class WrittenContentCompressor:
    """已写入内容去重器.

    优化:
    - 阈值走 settings.written_content_similarity_threshold
    - chunk 级去重 (切成 chunks 后逐 chunk 比对)
    - 多查询并集去重 (current_subtopic + draft_section_titles 并集)

    用 FastEmbed (本地 bge-small-zh-v1.5, 512维) 对已写入内容做相似度去重,
    避免重复内容进入上下文. 不依赖远程 TEI 服务 (TEI 仅用于私有数据 Qdrant 索引).

    docbot 集成场景: ContentFillerD.fill_chapter() 在 LLM 生成 content_md 后调用,
    跨章节去重 (同一 ContentFillerD 实例的 _dedup_compressor 跨 fill_chapter 调用共享).
    """

    settings: Settings
    _fastembed: FastEmbedClient
    threshold: float
    # chunk 级去重
    _written_embeddings: list[list[float]]
    _written_chunks: list[str]
    # 单条 chunk embedding 缓存 (key=chunk sha256), 避免同一 chunk
    # 在不同 content 中重复嵌入; reset() 时一并清空. 使用 OrderedDict 实现
    # LRU 淘汰, 防止多会话并发下无限增长导致内存泄漏.
    _chunk_cache: OrderedDict[str, list[float]]

    # LRU 上限: 单会话 deep_research L9-L10 最大 ~1050 项, 5 并发会话共享场景
    # 约 5250 项. 提升至 8192 覆盖极端并发场景, 内存 ≈17MB (8192 × 2.1KB),
    # 相对容器峰值内存可忽略, 确保 LRU 不淘汰活跃 chunk.
    CHUNK_CACHE_MAX_SIZE: int = 8192

    def __init__(
        self,
        settings: Settings | None = None,
        similarity_threshold: float | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._fastembed = get_fastembed_client()
        # 阈值走 settings (优先级: 参数 > settings > 默认 0.5)
        self.threshold = (
            similarity_threshold
            if similarity_threshold is not None
            else getattr(self.settings, "written_content_similarity_threshold", 0.5)
        )
        self._written_embeddings = []
        self._written_chunks = []
        self._chunk_cache = OrderedDict()

    def _cache_get(self, key: str) -> list[float] | None:
        """LRU 读取: 命中时 move_to_end 标记为最近使用."""
        value = self._chunk_cache.get(key)
        if value is not None:
            self._chunk_cache.move_to_end(key)
        return value

    def _cache_set(self, key: str, value: list[float]) -> None:
        """LRU 写入: 超过上限时淘汰最久未使用项, 写入后标记为最近使用."""
        if key in self._chunk_cache:
            self._chunk_cache.move_to_end(key)
        self._chunk_cache[key] = value
        self._chunk_cache.move_to_end(key)
        while len(self._chunk_cache) > self.CHUNK_CACHE_MAX_SIZE:
            self._chunk_cache.popitem(last=False)

    @staticmethod
    def _cosine_similarity_batch(
        new_vecs: list[list[float]],
        written_vecs: list[list[float]],
    ) -> np.ndarray:
        """批量余弦相似度 (numpy 矩阵加速, 修复 context-compress 性能瓶颈).

        一次性计算 M 条新向量与 N 条已写入向量之间的两两余弦相似度,
        替代 O(N*M) 双重 for 循环.

        迁移自 AIR ContextManager._cosine_similarity_batch (原为 ContextManager 静态方法).

        Args:
            new_vecs: 新向量列表 (M 条, 每条 D 维)
            written_vecs: 已写入向量列表 (N 条, 每条 D 维)

        Returns:
            shape=(M, N) 的 numpy 数组, 每元素为对应位置的余弦相似度.
            若任一输入为空或维度不匹配, 返回 shape=(0, 0) 的空数组.
        """
        if not new_vecs or not written_vecs:
            return np.zeros((0, 0), dtype=np.float32)
        new_matrix = np.asarray(new_vecs, dtype=np.float32)
        written_matrix = np.asarray(written_vecs, dtype=np.float32)
        if new_matrix.ndim != 2 or written_matrix.ndim != 2:
            return np.zeros((0, 0), dtype=np.float32)
        # L2 归一化 (避免除零, 零向量范数置 1, 结果为 0)
        new_norms = np.linalg.norm(new_matrix, axis=1, keepdims=True)
        written_norms = np.linalg.norm(written_matrix, axis=1, keepdims=True)
        new_norms = np.where(new_norms == 0, 1.0, new_norms)
        written_norms = np.where(written_norms == 0, 1.0, written_norms)
        new_normalized = new_matrix / new_norms
        written_normalized = written_matrix / written_norms
        # 矩阵乘法: (M, D) @ (D, N) = (M, N)
        return new_normalized @ written_normalized.T

    async def compute_embedding(
        self,
        content: str,
    ) -> tuple[list[str], list[list[float]]]:
        """锁外计算 content 的 chunk embeddings (缩小锁粒度).

        在锁外完成本地 FastEmbed I/O, 利用 _chunk_cache 缓存单条 chunk 的
        embedding, 避免同一 chunk 在不同 content 中重复嵌入. 返回 (chunks,
        content_embs) 供 check_and_update 在锁内做 numpy 相似度比对.

        拆分动机: should_keep 在 dedup_lock 内部调用 embed_texts 会使并行
        退化为串行. 现将 embed_texts 移到锁外, 锁仅保护
        _written_embeddings / _written_chunks 的并发修改.

        Embeddings 与追踪约束:
        - 上下文压缩统一用 FastEmbed (bge-small-zh-v1.5, 512维), 禁用远程 TEI
        - 高频 embedding 调用必带 trace_embedding span (含 model/usage_details)

        Args:
            content: 待判断的内容字符串

        Returns:
            (chunks, content_embs): chunks 为分块后的文本列表, content_embs 为
            对应 embedding 列表. content 为空或 embedding 失败时返回 ([], []),
            调用方应据此降级保留内容.
        """
        if not content.strip():
            return [], []

        # chunk 级切分 (复用 embeddings_filter.recursive_split, chunk_size=1000)
        from src.rag.embeddings_filter import DEFAULT_SEPARATORS, recursive_split

        chunks = recursive_split(
            content,
            separators=DEFAULT_SEPARATORS,
            chunk_size=self.settings.embeddings_filter_chunk_size,
            chunk_overlap=self.settings.embeddings_filter_chunk_overlap,
        )
        if not chunks:
            chunks = [content]

        # 单条 chunk embedding 缓存, 避免同一 chunk 在不同 content 中重复嵌入
        content_embs: list[list[float]] = [[] for _ in chunks]
        miss_indices: list[int] = []
        miss_chunks: list[str] = []
        for i, chunk in enumerate(chunks):
            cache_key = hashlib.sha256(chunk.encode("utf-8")).hexdigest()
            cached = self._cache_get(cache_key)
            if cached is not None:
                content_embs[i] = cached
            else:
                miss_indices.append(i)
                miss_chunks.append(chunk)

        if miss_chunks:
            # 方案 B: 包裹 trace_embedding span, 便于在可观测后端独立查看去重 embedding 指标
            # (FastEmbed 内部 embed_texts 已有自己的 fastembed-embed span; 此处外层
            #  span 提供"去重场景"语义, 与精排场景区分, 便于 profiling)
            async with trace_embedding(
                name="written-content-dedup-embed",
                input={
                    "text_count": len(miss_chunks),
                    "total_chars": sum(len(t) for t in miss_chunks),
                },
                model=self.settings.fastembed_model_name,
            ) as span:
                try:
                    miss_embs = await self._fastembed.embed_texts(miss_chunks)
                except Exception as e:  # noqa: BLE001
                    logger.warning("WrittenContentCompressor embedding 失败, 保留内容: %s", e)
                    span.update(metadata={"error": str(e), "degraded": True})
                    return [], []
                for idx, chunk, emb in zip(miss_indices, miss_chunks, miss_embs, strict=True):
                    content_embs[idx] = emb
                    cache_key = hashlib.sha256(chunk.encode("utf-8")).hexdigest()
                    self._cache_set(cache_key, emb)
                # 估算 token 数 (粗略: 字符数 / 3, 与 FastEmbedClient 内部一致)
                token_count = sum(len(t) for t in miss_chunks) // 3
                span.update(
                    output={"vector_count": len(miss_embs)},
                    usage_details={"total_tokens": token_count},
                )

        return chunks, content_embs

    def check_and_update(
        self,
        chunks: list[str],
        content_embs: list[list[float]],
    ) -> bool:
        """锁内同步: numpy 矩阵比对相似度 + 更新内部状态.

        在锁内执行 (保护 _written_embeddings 和 _written_chunks 的并发修改),
        用 numpy 矩阵乘法一次性计算所有相似度, 替代 O(N*M) 双重 for 循环.
        任意 chunk 与已写入 chunks 的最高相似度 >= threshold 即丢弃整篇 content,
        保留原语义.

        Args:
            chunks: 分块后的文本列表 (来自 compute_embedding)
            content_embs: 对应的 embedding 列表 (来自 compute_embedding)

        Returns:
            True 表示应保留 (无高度相似的已写入内容), False 表示应丢弃.
            chunks/content_embs 为空 (compute_embedding 失败) 时降级保留.
        """
        # compute_embedding 失败时返回 ([], []), 此处降级保留
        if not chunks or not content_embs:
            return True

        # 首次写入: 直接记录所有 chunks 的 embedding, 无需比对
        if not self._written_embeddings:
            self._written_embeddings.extend(content_embs)
            self._written_chunks.extend(chunks)
            return True

        # numpy 矩阵运算替代双重 for 循环
        # sim_matrix shape = (len(content_embs), len(self._written_embeddings))
        sim_matrix = WrittenContentCompressor._cosine_similarity_batch(
            content_embs,
            self._written_embeddings,
        )
        if sim_matrix.size == 0:
            # 矩阵为空 (维度不匹配等), 降级保留并记录
            self._written_embeddings.extend(content_embs)
            self._written_chunks.extend(chunks)
            return True

        # 每个 chunk 与所有已写入 chunks 的最高相似度
        max_sims = np.max(sim_matrix, axis=1)
        # 任意 chunk 的最高相似度 >= threshold 即丢弃整篇 content (保留原语义)
        if float(np.max(max_sims)) >= self.threshold:
            return False

        # 无高度相似: 记录新 chunks 的 embedding
        self._written_embeddings.extend(content_embs)
        self._written_chunks.extend(chunks)
        return True

    def check_and_update_partial(
        self,
        chunks: list[str],
        content_embs: list[list[float]],
    ) -> tuple[bool, str]:
        """跨章节语义去重 (只丢弃相似 chunk, 保留差异部分).

        串行去重: 串行处理子主题, 每个参考已写章节避免重复;
        本项目并行处理, "任意 chunk 相似即整篇丢弃"过于激进,
        导致子主题间有部分相似内容时整篇被丢弃 (TOC 有标题但正文无内容).

        新策略:
        - 所有 chunk 都相似: 整篇丢弃 (返回 (False, ""))
        - 部分 chunk 相似: 只保留不相似的 chunk (返回 (True, filtered_content))
        - 无相似 chunk: 全部保留 (返回 (True, original_content))

        docbot 集成: ContentFillerD 调用此方法做章节级去重,
        避免章节间重复内容 (术语定义 / 代码示例等) 进入最终文档.
        """
        # compute_embedding 失败时返回 ([], []), 此处降级保留
        if not chunks or not content_embs:
            return True, "\n\n".join(chunks) if chunks else ""

        original_content = "\n\n".join(chunks)

        # 首次写入: 直接记录所有 chunks 的 embedding, 无需比对
        if not self._written_embeddings:
            self._written_embeddings.extend(content_embs)
            self._written_chunks.extend(chunks)
            return True, original_content

        # numpy 矩阵运算替代双重 for 循环
        try:
            sim_matrix = WrittenContentCompressor._cosine_similarity_batch(
                content_embs,
                self._written_embeddings,
            )
        except ValueError:
            # 维度不匹配 (如不同 embedding 模型), 降级保留并记录
            self._written_embeddings.extend(content_embs)
            self._written_chunks.extend(chunks)
            return True, original_content
        if sim_matrix.size == 0:
            # 矩阵为空 (维度不匹配等), 降级保留并记录
            self._written_embeddings.extend(content_embs)
            self._written_chunks.extend(chunks)
            return True, original_content

        # 每个 chunk 与所有已写入 chunks 的最高相似度
        max_sims = np.max(sim_matrix, axis=1)
        similar_mask = max_sims >= self.threshold

        # 所有 chunk 都相似: 整篇丢弃
        if bool(np.all(similar_mask)):
            return False, ""

        # 部分 chunk 相似: 只保留不相似的 chunk
        keep_indices = [i for i, is_sim in enumerate(similar_mask) if not is_sim]
        if len(keep_indices) < len(chunks):
            # 有部分相似 chunk 被过滤
            keep_chunks = [chunks[i] for i in keep_indices]
            keep_embs = [content_embs[i] for i in keep_indices]
            # 只记录不相似 chunk 的 embedding
            self._written_embeddings.extend(keep_embs)
            self._written_chunks.extend(keep_chunks)
            filtered_content = "\n\n".join(keep_chunks)
            return True, filtered_content

        # 无相似 chunk: 全部保留
        self._written_embeddings.extend(content_embs)
        self._written_chunks.extend(chunks)
        return True, original_content

    async def should_keep(self, content: str) -> bool:
        """判断内容是否应保留 (兼容入口, 内部调用 compute_embedding + check_and_update).

        chunk 级去重. 切成 chunks 后取最高相似度判断,
        与 WrittenContentCompressor 对齐.

        内部拆分为 compute_embedding (锁外 I/O) + check_and_update
        (锁内 numpy 比对). 单调用方可直接用此方法; 并行场景应分别调用两步
        以缩小锁粒度.

        Args:
            content: 待判断的内容字符串

        Returns:
            True 表示应保留 (无高度相似的已写入内容), False 表示应丢弃.
            空 content 返回 False (保留原语义); embedding 失败降级返回 True.
        """
        # 保留原语义: 空 content 直接丢弃 (不进入 compute_embedding)
        if not content.strip():
            return False
        chunks, content_embs = await self.compute_embedding(content)
        return self.check_and_update(chunks, content_embs)

    def reset(self) -> None:
        """重置已写入内容记录 (每次新研究调用)."""
        self._written_embeddings.clear()
        self._written_chunks.clear()
        self._chunk_cache.clear()


__all__ = ["WrittenContentCompressor"]

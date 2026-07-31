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
import re
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


# v10-P0-5: docbot 自身路径泄露模式 (与目标仓库无关, 出现即视为幻觉)
_DOCBOT_LEAK_PATTERNS: tuple[str, ...] = (
    r'agentinsight-docbot/[^\s\)\]]*',
    r'/memory/projects/[^\s\)\]]*',
    r'\.trae-cn/[^\s\)\]]*',
    r'src/config/docbot/outlines/[^\s\)\]]*',
    r'[A-Za-z]:\\Projects\\[^\s\)\]]*',
    r'/Projects/Entrepreneurship/[^\s\)\]]*',
    # v11-P0-5: 完整路径模式 (跨平台, 含正反斜杠)
    r'[a-zA-Z]:[\\/]Projects[\\/]Entrepreneurship[\\/]AIProjects[\\/]agentinsight-agents[\\/]agentinsight-docbot[^\s\)\]]*',
    r'/Projects/Entrepreneurship/AIProjects/agentinsight-agents/agentinsight-docbot[^\s\)\]]*',
    r'-d-Projects-Entrepreneurship-AIProjects[^\s\)\]]*',
)

# v12: 品牌名翻译修正 — 禁止硬编码任何具体产品名.
# 仅保留「中文误译前缀 + PascalCase 后缀」的通用模式; 具体品牌由 brand_names 驱动.
_BRAND_TRANSLATION_PATTERNS: list[tuple[re.Pattern, str]] = []


def _enforce_brand_names(
    content: str,
    brand_names: list[str] | None = None,
) -> str:
    """强制修正品牌名翻译 (后置校验, 不依赖 LLM).

    借鉴 Aider 签名直填: 品牌名是不可修改的「锁定符号」.
    **禁止硬编码任何具体仓库/产品名** — 仅根据 project_metadata.brand_names 动态修正.

    策略:
    1. 对每个 brand (如从 .sln/.csproj 提取的名称), 将其常见中文误译还原
    2. 若 brand 含 PascalCase 多段 (如 XxxYyy), 修正「中文首段 + 英文余段」拼写

    Args:
        content: LLM 生成的 Markdown 内容
        brand_names: 从 project_metadata 提取的品牌名列表

    Returns:
        修正后的内容
    """
    if not content:
        return content

    fixed = content
    if not brand_names:
        return fixed

    # 常见英文段 → 中文误译表 (通用, 非项目特有)
    _CN_MISTRANSLATIONS: dict[str, list[str]] = {
        "Agent": ["智能体", "代理体"],
        "Trace": ["追踪"],
        "Observation": ["观测"],
        "Score": ["评分"],
        "Alert": ["告警"],
        "Session": ["会话"],
        "Insight": ["洞察"],
    }

    for brand in brand_names:
        if not brand or len(brand) < 3:
            continue
        # 1. 完整品牌被拆成「中文 + 英文余段」: 智能体Xxx → Brand
        # 提取首段 PascalCase
        first_m = re.match(r"^([A-Z][a-z]+)", brand)
        if not first_m:
            continue
        first_seg = first_m.group(1)
        rest = brand[len(first_seg):]
        cn_list = _CN_MISTRANSLATIONS.get(first_seg, [])
        for cn in cn_list:
            if rest:
                # 中文首段 + 英文余段 → 完整品牌
                fixed = re.sub(rf"{re.escape(cn)}\s*{re.escape(rest)}", brand, fixed)
                fixed = re.sub(rf"{re.escape(cn)}{re.escape(rest)}", brand, fixed)
            # 中文 + 紧跟大写英文 (类名上下文): 智能体Config → AgentConfig (用 first_seg)
            fixed = re.sub(
                rf"{re.escape(cn)}([A-Z][a-zA-Z]+)",
                rf"{first_seg}\1",
                fixed,
            )
            # 路径段: 智能体Management/ → AgentManagement/
            fixed = re.sub(
                rf"{re.escape(cn)}([A-Z][a-zA-Z]+)/",
                rf"{first_seg}\1/",
                fixed,
            )
            # 短语: 「智能体 配置」仅当 brand 以该段开头
            if first_seg == "Agent":
                fixed = re.sub(rf"{re.escape(cn)}\s+配置", f"{first_seg} 配置", fixed)
                fixed = re.sub(rf"{re.escape(cn)}\s+会话", f"{first_seg} 会话", fixed)
                fixed = re.sub(rf"{re.escape(cn)}\s+报表", f"{first_seg} 报表", fixed)

    return fixed


# 占位已删除


# v10-P0-5: 代码文件路径前导斜杠修正模式
# 仅对 .cs/.py/.ts/.java/.go/.js 等代码文件路径生效, 避免 /api/ 等 URL 路径被误改
_LEADING_SLASH_CODE_PATTERN = re.compile(
    r'(?<!\w)/((?:API|Models|Admin|Agents|SDK|src|app|lib|tests|test|docs|examples)/'
    r'[^\s:)\]]+\.(?:cs|py|ts|tsx|js|jsx|java|go|rs|rb|php))'
)


def validate_and_fix_paths(content: str) -> str:
    """v10-P0-5: 校验并修正文档中的路径格式.

    借鉴 STORM 输出格式硬约束 + Aider rel_fname 统一.

    1. 移除 docbot 自身路径泄露 (agentinsight-docbot/, /memory/projects/, .trae-cn/ 等)
    2. 将开头的 /API/xxx 路径改为 API/xxx (去掉多余前导斜杠)
    3. 将反斜杠改为正斜杠 (统一 POSIX 风格)

    Args:
        content: 原始 Markdown 内容

    Returns:
        修正后的 Markdown 内容
    """
    if not content:
        return content

    fixed = content

    # 1. 移除 docbot 自身路径泄露 (替换为占位符, 让 LLM/审阅者注意到)
    for pattern in _DOCBOT_LEAK_PATTERNS:
        fixed = re.sub(pattern, '(已移除无关路径)', fixed)

    # 2. 修正前导斜杠 (仅对代码文件路径生效, URL /api/xxx 不动)
    fixed = _LEADING_SLASH_CODE_PATTERN.sub(r'\1', fixed)

    # 3. 反斜杠改正斜杠 (仅出现在路径上下文中, 避免影响 LaTeX/正则)
    # 匹配 (盘符:\路径\) 或 (路径\路径.cs) 形式
    fixed = re.sub(r'([A-Za-z]):\\', r'\1:/', fixed)  # D:\ → D:/
    fixed = re.sub(r'(?<=[A-Za-z0-9_])\\(?=[A-Za-z0-9_])', '/', fixed)  # 中间的 \ → /

    return fixed


def _adapt_ast_endpoints_to_signatures(endpoints: list[dict]) -> list[dict]:
    """v11-P0-1: 将 ast_search 返回的端点适配为 signature_extractor 兼容的签名字典.

    ast_search 返回: {class_name, method_name, http_method, route, file_path, line, summary}
    signature_extractor 返回: {controller, action, http_method, route, signature, file_path, line, parameters, return_type, framework}

    适配字段名映射 + 补充默认值, 保持 render_api_table 兼容.

    Args:
        endpoints: ast_search.search_http_endpoints 返回的端点列表

    Returns:
        签名字典列表 (与 SignatureExtractor.extract_api_signatures 兼容)
    """
    signatures: list[dict] = []
    for ep in endpoints:
        if not isinstance(ep, dict):
            continue
        signatures.append({
            "controller": ep.get("class_name", "") or ep.get("controller", ""),
            "action": ep.get("method_name", "") or ep.get("action", ""),
            "http_method": ep.get("http_method", ""),
            "route": ep.get("route", "") or ep.get("full_route", ""),
            "signature": ep.get("summary", "") or "",
            "file_path": ep.get("file_path", ""),
            "line": ep.get("line", 0),
            "parameters": [],  # ast_search 不解析参数, 留空
            "return_type": "",  # ast_search 不解析返回类型, 留空
            "framework": "dotnet" if str(ep.get("file_path", "")).endswith(".cs") else "fastapi",
        })
    return signatures


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
        file_index: dict | None = None,
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
            file_index: 仓库文件索引 (P0-5 引用校验用, 含 files[].path)

        Returns:
            {chapter_idx, content_md, image_svgs, has_invalid_citations?}
        """
        chapter_idx = chapter.get("idx", 0)
        chapter_title = chapter.get("title", "")
        async with trace_chain(
            name=f"docbot.content_fill.{report_type}.{chapter_idx}",
            input={"chapter": chapter_title},
        ) as span:
            # v10-P0-6: code_learning 完整性校验 (诊断 SymbolValidator 0 符号根因)
            # 缺失字段不阻断主流程, 但记录 warning 便于排查
            if isinstance(code_learning, dict):
                _required_keys = (
                    "repo_map", "code_graph", "file_index",
                    "http_endpoints", "endpoints_text",
                    "glossary_text", "project_metadata_text",
                )
                _missing_keys = [
                    k for k in _required_keys
                    if k not in code_learning or not code_learning.get(k)
                ]
                if _missing_keys:
                    logger.warning(
                        "v10-P0-6: 章节 %s code_learning 缺失字段: %s (现有 keys=%s), "
                        "SymbolValidator / 引用校验可能失效",
                        chapter_idx, _missing_keys,
                        list(code_learning.keys())[:20],
                    )
                    span.update(
                        metadata={
                            "v10_code_learning_missing": _missing_keys,
                            "v10_code_learning_keys": list(code_learning.keys())[:20],
                        }
                    )
                else:
                    logger.debug(
                        "v10-P0-6: 章节 %s code_learning 完整 (keys=%d)",
                        chapter_idx, len(code_learning),
                    )

            # v8-P0-G: API 文档接口级生成 (按端点逐个生成, 解决接口遗漏)
            # 触发条件: api_doc 类型 + API 详情章节 + code_learning 含 http_endpoints
            # 失败降级: 任何异常或空结果都回退到下方整章节生成流程, 不阻断主流程
            # 注意: 若接口级生成成功, 直接返回, 不进入后续 RAG / LLM / refine 流程
            if (
                report_type == "api_doc"
                and self._is_api_detail_chapter(chapter)
                and isinstance(code_learning, dict)
                and code_learning.get("http_endpoints")
            ):
                try:
                    content_md = await self._generate_api_doc_by_endpoint(
                        chapter=chapter,
                        code_learning=code_learning,
                        language=language,
                        repo_id=repo_id,
                        user_id=user_id,
                        llm_session_id=llm_session_id,
                        settings=settings,
                    )
                    if content_md:
                        # v10-P0-5/P0-7: 接口级生成内容也走路径修正 + 幻觉校验
                        # 避免直接 return 跳过后置校验导致幻觉/路径泄露
                        try:
                            content_md = validate_and_fix_paths(content_md)
                        except Exception as e:  # noqa: BLE001
                            logger.warning(
                                "v10-P0-5: 接口级生成章节 %s 路径修正异常: %s",
                                chapter_idx, e,
                            )
                        try:
                            from src.agents.docbot.symbol_validator import SymbolValidator

                            sv = SymbolValidator()
                            sv.build_from_code_learning(code_learning)
                            if sv._built:
                                sv_result = sv.validate_document(content_md)
                                if not sv_result["valid"]:
                                    hall_syms = sv_result["hallucinated_symbols"]
                                    logger.warning(
                                        "v10-P0-7: 接口级生成章节 %s 检测到 %d 个幻觉符号, 触发重写",
                                        chapter_idx, len(hall_syms),
                                    )
                                    rewrite_prompt = self._build_hallucination_rewrite_prompt(
                                        original_content=content_md,
                                        hallucinated_symbols=hall_syms,
                                        chapter=chapter,
                                        code_learning=code_learning,
                                    )
                                    rewrite_resp = await self.llm.achat(
                                        [{"role": "user", "content": rewrite_prompt}],
                                        tier=LLMTier.SMART,
                                        session_id=llm_session_id,
                                        span_name=f"docbot.content_fill.endpoint_hallucination_rewrite.{chapter_idx}",
                                        max_tokens=8192,
                                        reasoning_effort="none",
                                    )
                                    if rewrite_resp.content and len(rewrite_resp.content) > 100:
                                        content_md = rewrite_resp.content
                                        logger.info(
                                            "v10-P0-7: 接口级生成章节 %s 幻觉重写成功",
                                            chapter_idx,
                                        )
                        except Exception as e:  # noqa: BLE001
                            logger.warning(
                                "v10-P0-7: 接口级生成章节 %s 幻觉校验异常: %s",
                                chapter_idx, e,
                            )
                        span.update(
                            output={
                                "content_length": len(content_md),
                                "image_count": 0,
                                "v8_p0_g_triggered": True,
                            }
                        )
                        return {
                            "chapter_idx": chapter_idx,
                            "content_md": content_md,
                            "image_svgs": [],
                        }
                    # 生成失败, 降级到整章节生成 (继续执行后续逻辑)
                    logger.warning("v8-P0-G: 接口级生成返回空, 降级整章节生成")
                except Exception as e:  # noqa: BLE001
                    logger.warning("v8-P0-G: 接口级生成失败 (降级整章节): %s", e)

            # 1. RAG 检索 (用户私有代码索引, namespace 含 user_id + repo_id 隔离)
            # v6-P0-B: 传 code_learning 给 _retrieve_rag_context, 用于 query 语义增强
            # v6-P0-D: 替换为迭代检索, 第 2 轮基于第 1 轮符号补充跨文件依赖
            rag_context = await self._iterative_retrieve(
                chapter=chapter,
                report_type=report_type,
                user_id=user_id,
                repo_id=repo_id,
                chapter_idx=chapter_idx,
                code_learning=code_learning,
            )

            # 2. 加载提示词模板
            prompt_template = self._load_prompt_template()
            code_summary = (
                code_learning.get("summary", "") if isinstance(code_learning, dict) else ""
            )
            # P0-4: 注入 key_modules (含 path) + dependencies (含 evidence), 让 LLM 拿到真实路径
            key_modules_text = self._format_key_modules(
                code_learning.get("key_modules", []) if isinstance(code_learning, dict) else []
            )
            dependencies_text = self._format_dependencies(
                code_learning.get("dependencies", []) if isinstance(code_learning, dict) else []
            )

            # v5-P0-C: RAG 空结果降级 — 注入 code_learning 结构化上下文, 避免 LLM 无上下文编造
            if "[GROUNDING_EMPTY]" in rag_context:
                logger.warning(
                    "v5-P0-C: RAG 空结果, 降级注入 code_learning 上下文 (chapter=%s, idx=%s)",
                    chapter_title[:50],
                    chapter_idx,
                )
                repo_map_text = (
                    code_learning.get("repo_map", "")
                    if isinstance(code_learning, dict)
                    else ""
                )
                rag_context = (
                    "[RAG_EMPTY_FALLBACK] RAG 检索无结果, 以下为 code_learning 结构化摘要, "
                    "请基于此生成内容, 禁止编造未在下文出现的类名/函数名/路径.\n\n"
                    f"## 代码摘要\n{code_summary[:8000]}\n\n"
                    f"## 关键模块\n{key_modules_text}\n\n"
                    f"## 依赖关系\n{dependencies_text}\n\n"
                    f"## 仓库符号地图 (tree-sitter)\n{repo_map_text[:5000]}"
                )

            # 3. 构造 prompt
            # v9-P0-B: 注入 v8 上下文 (project_metadata/glossary/endpoints/enums/config_specs)
            prompt = prompt_template.format(
                chapter_title=chapter_title,
                chapter_purpose=chapter.get("purpose", ""),
                chapter_sections=chapter.get("sections", []),
                key_points=chapter.get("key_points", []),
                chapter_example=chapter.get("example", ""),
                language=language,
                code_summary=code_summary[:50_000],  # 截断防止超长
                key_modules=key_modules_text,
                dependencies=dependencies_text,
                rag_context=rag_context,
                # v9 新增 kwargs (从 code_learning 提取 v8 上下文)
                endpoints_text=self._safe_get_str(code_learning, "endpoints_text")[:12_000],
                enums_text=self._safe_get_str(code_learning, "enums_text")[:8_000],
                config_specs_text=self._safe_get_str(code_learning, "config_specs_text")[:4_000],
                project_metadata_text=self._safe_get_str(code_learning, "project_metadata_text")[:4_000],
                glossary_text=self._safe_get_str(code_learning, "glossary_text")[:8_000],
            )

            # 4. P0-6: SMART LLM 填充内容 (含重试 + FAST 降级)
            # v12: 显式 max_tokens=8192, 避免推理模型 thinking 耗尽默认 6000 导致 content 为空
            content_md = await self._generate_with_retry(
                prompt=prompt,
                chapter=chapter,
                report_type=report_type,
                chapter_idx=chapter_idx,
                llm_session_id=llm_session_id,
                span=span,
                max_tokens=8192,
            )

            # v8-P1-J: 两阶段 draft→refine (借鉴 RepoCoder)
            # 第 1 阶段: 已通过 _generate_with_retry 生成 content_md (草稿)
            # 第 2 阶段: 用草稿中的符号做二次检索, 修正草稿中的幻觉 errorCode/字段名
            # 触发条件: code_learning 含 http_endpoints 或 enum_definitions (幻觉高发场景)
            # 失败降级: 任何异常返回原草稿, 不阻断主流程
            # 注意: 仅在整章节生成场景触发 (v8-P0-G 接口级生成已直接返回, 不会走到这里)
            try:
                if (
                    isinstance(code_learning, dict)
                    and (
                        code_learning.get("http_endpoints")
                        or code_learning.get("enum_definitions")
                    )
                    and content_md
                    and len(content_md) > 500
                ):
                    content_md = await self._refine_with_second_retrieval(
                        draft_content=content_md,
                        chapter=chapter,
                        code_learning=code_learning,
                        report_type=report_type,
                        repo_id=repo_id,
                        user_id=user_id,
                        llm_session_id=llm_session_id,
                        settings=settings,
                    )
            except Exception as e:  # noqa: BLE001
                logger.warning("v8-P1-J: refine 异常 (降级使用原草稿): %s", e)

            # 4.5 P0-5: 生成期引用校验 + 重写循环 (仅当 file_index 可用时)
            content_md, has_invalid = await self._validate_and_rewrite_citations(
                content_md=content_md,
                chapter=chapter,
                chapter_idx=chapter_idx,
                file_index=file_index,
                prompt_template=prompt_template,
                base_prompt_kwargs={
                    "chapter_title": chapter_title,
                    "chapter_purpose": chapter.get("purpose", ""),
                    "chapter_sections": chapter.get("sections", []),
                    "key_points": chapter.get("key_points", []),
                    "chapter_example": chapter.get("example", ""),
                    "language": language,
                    "code_summary": code_summary[:50_000],
                    "key_modules": key_modules_text,
                    "dependencies": dependencies_text,
                    "rag_context": rag_context,
                },
                report_type=report_type,
                llm_session_id=llm_session_id,
                span=span,
            )

            # 4.5.1 O4-P0-B: AST 符号白名单校验 (在引用校验之后)
            # 校验文档中提到的类名/函数名是否在 code_learning 符号集合中
            # 失败降级: SymbolValidator 构建失败时跳过, 不阻断主流程
            # v10-P0-7: 检测到幻觉符号后触发 LLM 重写 (替换原"仅记录"逻辑)
            # 借鉴 Sweep.dev checkpoint + AutoCodeRover 签名优先
            try:
                from src.agents.docbot.symbol_validator import SymbolValidator

                symbol_validator = SymbolValidator()
                symbol_validator.build_from_code_learning(code_learning)
                if symbol_validator._built:
                    symbol_result = symbol_validator.validate_document(content_md)
                    if not symbol_result["valid"]:
                        hallucinated_syms = symbol_result["hallucinated_symbols"]
                        logger.warning(
                            "v10-P0-7: 章节 %s 检测到 %d 个幻觉符号, 触发重写: %s",
                            chapter_idx,
                            len(hallucinated_syms),
                            hallucinated_syms[:10],
                        )
                        span.update(
                            metadata={
                                "symbol_hallucinations": len(hallucinated_syms),
                                "sample_hallucinated": hallucinated_syms[:10],
                                "v10_hallucination_rewrite_triggered": True,
                            }
                        )
                        # v10-P0-7: 触发 LLM 重写, 而非仅记录
                        try:
                            rewrite_prompt = self._build_hallucination_rewrite_prompt(
                                original_content=content_md,
                                hallucinated_symbols=hallucinated_syms,
                                chapter=chapter,
                                code_learning=code_learning,
                            )
                            rewrite_response = await self.llm.achat(
                                [{"role": "user", "content": rewrite_prompt}],
                                tier=LLMTier.SMART,
                                session_id=llm_session_id,
                                span_name=f"docbot.content_fill.hallucination_rewrite.{chapter_idx}",
                                max_tokens=8192,
                                reasoning_effort="none",
                            )
                            if rewrite_response.content and len(rewrite_response.content) > 100:
                                content_md = rewrite_response.content
                                logger.info(
                                    "v10-P0-7: 章节 %s 幻觉重写成功, 新长度=%d",
                                    chapter_idx, len(content_md),
                                )
                                span.update(
                                    metadata={
                                        "v10_hallucination_rewrite_success": True,
                                        "v10_new_content_length": len(content_md),
                                    }
                                )
                            else:
                                logger.warning(
                                    "v10-P0-7: 章节 %s 幻觉重写返回空, 保留原文",
                                    chapter_idx,
                                )
                        except Exception as e:  # noqa: BLE001
                            logger.warning(
                                "v10-P0-7: 章节 %s 幻觉重写失败 (保留原文): %s",
                                chapter_idx, e,
                            )
                    else:
                        logger.info(
                            "O4-P0-B: 章节 %s 符号白名单校验通过 (matched=%d)",
                            chapter_idx,
                            symbol_result["matched_count"],
                        )
            except Exception as e:  # noqa: BLE001
                logger.warning("O4-P0-B: 符号白名单校验异常 (降级跳过): %s", e)

            # 4.5.2 O4-P0-C: API 签名直填 (仅 api_doc 类型, 在 API 清单章节)
            # 直接将 AST 提取的真实签名表注入章节, LLM 不可修改
            if (
                report_type == "api_doc"
                and self._is_api_list_chapter(chapter)
                and isinstance(code_learning, dict)
            ):
                try:
                    signatures: list[dict] = []

                    # v12-P0-3: 优先使用 code_learning.http_endpoints (任务一已扫描完整)
                    # 不再依赖 settings.repo_root (几乎总为空导致注入失败)
                    raw_eps = code_learning.get("http_endpoints") or []
                    if isinstance(raw_eps, list) and raw_eps:
                        # v14: 按章节过滤后再注入, 禁止每个接口章塞入全部端点
                        filtered = self._filter_endpoints_for_chapter(raw_eps, chapter)
                        # 概览/清单章: 过滤为空时用全量 (仅当 _is_api_list_chapter 且非 Controller 章)
                        if not filtered and not chapter.get("controller_name"):
                            title_l = str(chapter.get("title") or "").lower()
                            if any(
                                kw in title_l
                                for kw in ("概览", "清单", "overview", "list", "引言")
                            ):
                                filtered = list(raw_eps)
                        signatures = _adapt_ast_endpoints_to_signatures(filtered)
                        logger.info(
                            "v12-P0-3: 章节 %s 从 code_learning 取 %d 个端点 (过滤后)",
                            chapter_idx, len(signatures),
                        )

                    # 降级: 若 code_learning 无端点, 尝试用 repo_path 重新扫描
                    if not signatures:
                        repo_path = (
                            str(code_learning.get("repo_path") or "")
                            or self._get_repo_path(settings)
                        )
                        if repo_path:
                            try:
                                from src.skills.docbot.ast_search import search_http_endpoints

                                ast_endpoints = search_http_endpoints(repo_path=repo_path)
                                if ast_endpoints:
                                    signatures = _adapt_ast_endpoints_to_signatures(
                                        ast_endpoints
                                    )
                                    logger.info(
                                        "v12-P0-3: 章节 %s ast_search 提取 %d 个端点",
                                        chapter_idx, len(signatures),
                                    )
                            except Exception as e_ast:  # noqa: BLE001
                                logger.warning(
                                    "v12-P0-3: ast_search 提取失败: %s", e_ast,
                                )

                    # 再降级: signature_extractor
                    if not signatures:
                        repo_path = (
                            str(code_learning.get("repo_path") or "")
                            or self._get_repo_path(settings)
                        )
                        if repo_path:
                            try:
                                from src.agents.docbot.signature_extractor import (
                                    SignatureExtractor,
                                )

                                extractor = SignatureExtractor()
                                signatures = extractor.extract_api_signatures(
                                    code_learning, repo_path
                                )
                                if signatures:
                                    logger.info(
                                        "v12-P0-3 降级: signature_extractor %d 个签名",
                                        len(signatures),
                                    )
                            except Exception as e_sig:  # noqa: BLE001
                                logger.warning(
                                    "v12-P0-3: signature_extractor 失败: %s", e_sig,
                                )

                    if signatures:
                        try:
                            from src.skills.docbot.ast_search import (
                                render_api_inventory_markdown,
                            )

                            # 优先用规范化 inventory 表 (对齐 Trae 格式)
                            api_table = render_api_inventory_markdown(
                                [
                                    {
                                        "http_method": s.get("http_method", ""),
                                        "route": s.get("route", ""),
                                        "method_name": s.get("action", ""),
                                        "class_name": s.get("controller", ""),
                                    }
                                    for s in signatures
                                ]
                            )
                            content_md = self._inject_signature_table(
                                content_md, chapter_title, api_table
                            )
                            # 若 LLM 表格与注入表重复, 用确定性表整体替换清单区
                            content_md = self._replace_api_inventory_section(
                                content_md, api_table
                            )
                            logger.info(
                                "O4-P0-C: 章节 %s 注入 %d 个 API 签名 (api_doc)",
                                chapter_idx,
                                len(signatures),
                            )
                            span.update(
                                metadata={
                                    "injected_api_signatures": len(signatures),
                                    "signature_framework": signatures[0].get(
                                        "framework", "unknown"
                                    ),
                                }
                            )
                        except Exception as e_render:  # noqa: BLE001
                            logger.warning(
                                "O4-P0-C: render_api_table 渲染失败 (保留 LLM 生成内容): %s",
                                e_render,
                            )
                except Exception as e:  # noqa: BLE001
                    logger.warning("O4-P0-C: 签名直填异常 (降级跳过): %s", e)

            # 4.6 P0: 章节级语义去重 (跨章节消除重复内容, 术语定义 / 代码示例等)
            # 同一 ContentFillerD 实例共享 _dedup_compressor, 累积已写入 chunks embedding
            # 降级策略: compressor 初始化失败或 embedding 失败时保留原文, 不阻断主流程
            content_md = await self._dedup_chapter_content(content_md, chapter_title)

            # 4.7 v10-P0-5: 路径格式后置校验 (脚本化修正, 不依赖 LLM)
            # 修正 docbot 自身路径泄露 + 前导斜杠 + 反斜杠, 提升路径相似度
            try:
                original_len = len(content_md)
                content_md = validate_and_fix_paths(content_md)
                if len(content_md) != original_len:
                    logger.info(
                        "v10-P0-5: 章节 %s 路径修正 (len %d → %d)",
                        chapter_idx, original_len, len(content_md),
                    )
            except Exception as e:  # noqa: BLE001
                logger.warning("v10-P0-5: 路径修正异常 (保留原文): %s", e)

            # 4.8 v11-P0-4: 品牌名翻译强制修正 (后置校验, 不依赖 LLM)
            # 修正 LLM 把 "Agent" 翻译成 "智能体" 的幻觉, 借鉴 Aider {{LOCKED}} 不可修改标记
            try:
                original_len = len(content_md)
                # 从 code_learning.project_metadata 提取品牌名
                brand_names: list[str] = []
                if isinstance(code_learning, dict):
                    pm = code_learning.get("project_metadata") or {}
                    if isinstance(pm, dict):
                        bn = pm.get("brand_names") or []
                        if isinstance(bn, list):
                            brand_names = [str(b) for b in bn if b]
                content_md = _enforce_brand_names(content_md, brand_names)
                if len(content_md) != original_len:
                    logger.info(
                        "v11-P0-4: 章节 %s 品牌名修正 (len %d → %d, brands=%s)",
                        chapter_idx, original_len, len(content_md), brand_names[:3],
                    )
            except Exception as e:  # noqa: BLE001
                logger.warning("v11-P0-4: 品牌名修正异常 (保留原文): %s", e)

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
                    "has_invalid_citations": has_invalid,
                }
            )
            result: dict[str, Any] = {
                "chapter_idx": chapter_idx,
                "content_md": content_md,
                "image_svgs": image_svgs,
            }
            if has_invalid:
                result["has_invalid_citations"] = True
            return result

    async def _generate_with_retry(
        self,
        prompt: str,
        chapter: dict,
        report_type: str,
        chapter_idx: int,
        llm_session_id: str,
        span: Any,
        max_tokens: int = 8192,
    ) -> str:
        """P0-6: SMART LLM 调用层重试 + FAST LLM 降级.

        重试条件: LLM 调用异常 / 返回空内容 / 返回内容过短 (<100 字符)
        重试次数: 最多 3 次 SMART, 全部失败降级 1 次 FAST
        最终失败: 输出兜底占位符 (不阻断整篇报告生成)
        """
        max_generation_retries = 3
        min_content_length = 100
        messages = [{"role": "user", "content": prompt}]
        content_md = ""
        for attempt in range(max_generation_retries):
            try:
                response = await self.llm.achat(
                    messages,
                    tier=LLMTier.SMART,
                    session_id=llm_session_id,
                    span_name=f"docbot.content_fill.{report_type}.{chapter_idx}",
                    step="content_fill",
                    max_tokens=max_tokens,
                    # deepseek-v4 默认 thinking 会把 max_tokens 耗尽在 reasoning 上,
                    # 导致 content 为空; 内容填充关闭 thinking
                    reasoning_effort="none",
                )
                content_md = response.content or ""
                if content_md.strip() and len(content_md.strip()) >= min_content_length:
                    if attempt > 0:
                        logger.info(
                            "章节 %s 第 %d 次重试成功 (report_type=%s)",
                            chapter_idx,
                            attempt + 1,
                            report_type,
                        )
                    return content_md
                logger.warning(
                    "章节 %s 生成内容过短 (attempt %d/%d, length=%d, report_type=%s, "
                    "out_tokens=%s)",
                    chapter_idx,
                    attempt + 1,
                    max_generation_retries,
                    len(content_md.strip()),
                    report_type,
                    getattr(response, "output_tokens", "?"),
                )
            except Exception as e:  # noqa: BLE001
                logger.warning(
                    "章节 %s 生成异常 (attempt %d/%d, report_type=%s): %s: %s",
                    chapter_idx,
                    attempt + 1,
                    max_generation_retries,
                    report_type,
                    type(e).__name__,
                    e,
                )
                content_md = ""

        # 3 次 SMART 均失败: 降级 FAST LLM
        logger.error(
            "章节 %s 3 次 SMART 重试均失败, 降级 FAST LLM (report_type=%s)",
            chapter_idx,
            report_type,
        )
        try:
            response = await self.llm.achat(
                messages,
                tier=LLMTier.FAST,
                session_id=llm_session_id,
                span_name=f"docbot.content_fill.{report_type}.{chapter_idx}.fallback",
                step="content_fill_fallback",
                max_tokens=max_tokens,
                reasoning_effort="none",
            )
            content_md = response.content or ""
            if content_md.strip():
                span.update(metadata={"fallback_from": "smart", "fallback_to": "fast"})
                return content_md
        except Exception as e:  # noqa: BLE001
            logger.error(
                "章节 %s FAST LLM 降级也失败 (report_type=%s): %s: %s",
                chapter_idx,
                report_type,
                type(e).__name__,
                e,
            )

        # 最终兜底: 占位符 (不抛出异常, 不阻断整篇报告)
        span.update(metadata={"fallback_from": "smart", "fallback_to": "placeholder"})
        return f"## {chapter.get('title', f'章节{chapter_idx}')}\n\n*此章节内容生成失败，请重新生成报告。*"

    async def _validate_and_rewrite_citations(
        self,
        content_md: str,
        chapter: dict,
        chapter_idx: int,
        file_index: dict | None,
        prompt_template: str,
        base_prompt_kwargs: dict,
        report_type: str,
        llm_session_id: str,
        span: Any,
    ) -> tuple[str, bool]:
        """P0-5: 生成期引用校验 + 重写循环.

        校验 content_md 中的引用路径是否在 file_index 中存在
        - 通过: 返回原文
        - 失败: 追加"禁止引用路径"约束重写, 最多重写 2 次
        - 最终仍失败: 移除幻觉引用后返回, 标记 has_invalid=True

        Returns:
            (清洁后的 content_md, has_invalid)
        """
        if not content_md or not file_index:
            return content_md, False

        try:
            from src.skills.docbot.citation_extractor import (
                extract_and_validate_citations,
            )
        except Exception as e:  # noqa: BLE001
            logger.warning(
                "章节 %s citation_extractor 导入失败, 跳过引用校验: %s",
                chapter_idx,
                e,
            )
            return content_md, False

        max_citation_rewrites = 2
        max_attempts = max_citation_rewrites + 1  # 总尝试 3 次
        invalid_paths: list[str] = []
        current_content = content_md
        current_prompt_extra = ""

        for attempt in range(max_attempts):
            citations, validation = extract_and_validate_citations(
                current_content, file_index=file_index, chapter_idx=chapter_idx
            )

            if validation.get("passed", True):
                if attempt > 0:
                    logger.info(
                        "章节 %s 引用校验第 %d 次重写通过 (report_type=%s)",
                        chapter_idx,
                        attempt,
                        report_type,
                    )
                span.update(
                    metadata={
                        "citation_attempt": attempt,
                        "citation_count": len(citations),
                        "citation_passed": True,
                    }
                )
                return current_content, False

            invalid_paths = validation.get("missing_files", [])
            if not invalid_paths:
                # 仅行号问题 (无 missing_files), 不重写, 直接通过
                return current_content, False

            if attempt < max_citation_rewrites:
                logger.warning(
                    "章节 %s 引用校验失败 (attempt %d/%d), 幻觉路径数=%d, 将重写 (report_type=%s): %s",
                    chapter_idx,
                    attempt + 1,
                    max_attempts,
                    len(invalid_paths),
                    report_type,
                    invalid_paths[:5],
                )
                # 在 prompt 末尾追加"禁止引用路径"约束, 重新生成
                forbidden_list = "\n".join(f"- {p}" for p in invalid_paths)
                current_prompt_extra = (
                    f"\n\n# 禁止引用的路径 (前次生成幻觉, 必须避免)\n"
                    f"以下路径在目标仓库中不存在, 禁止在生成内容中引用:\n{forbidden_list}\n"
                    f"请基于 {base_prompt_kwargs.get('rag_context', '')} 中真实存在的路径重新引用。"
                )
                # 重新构造 prompt (在原 prompt 基础上追加禁止列表)
                try:
                    new_prompt = prompt_template.format(**base_prompt_kwargs) + current_prompt_extra
                except (KeyError, IndexError) as e:
                    logger.warning("章节 %s 重写 prompt 构造失败, 跳过重写: %s", chapter_idx, e)
                    return current_content, True

                messages = [{"role": "user", "content": new_prompt}]
                try:
                    response = await self.llm.achat(
                        messages,
                        tier=LLMTier.SMART,
                        session_id=llm_session_id,
                        span_name=f"docbot.content_fill.{report_type}.{chapter_idx}.rewrite.{attempt}",
                        step="content_fill_citation_rewrite",
                    )
                    new_content = response.content or ""
                    if new_content.strip() and len(new_content.strip()) >= 100:
                        current_content = new_content
                        continue
                except Exception as e:  # noqa: BLE001
                    logger.warning(
                        "章节 %s 引用重写 LLM 调用失败 (attempt %d): %s",
                        chapter_idx,
                        attempt,
                        e,
                    )
            else:
                # 最后一次仍失败: 移除幻觉引用后输出
                logger.error(
                    "章节 %s 引用校验最终失败, 已移除 %d 个幻觉引用 (report_type=%s)",
                    chapter_idx,
                    len(invalid_paths),
                    report_type,
                )
                cleaned = self._strip_invalid_citations(current_content, invalid_paths)
                span.update(
                    metadata={
                        "citation_attempt": attempt,
                        "citation_count": len(citations) if "citations" in locals() else 0,
                        "citation_passed": False,
                        "invalid_paths_stripped": len(invalid_paths),
                    }
                )
                return cleaned, True

        # 理论不可达 (for-else 已覆盖), 兜底返回
        return current_content, False

    @staticmethod
    def _strip_invalid_citations(content: str, invalid_paths: list[str]) -> str:
        """从 content 中移除幻觉引用 (替换为 [已移除幻觉引用] 标记)."""
        if not content or not invalid_paths:
            return content
        result = content
        for path in invalid_paths:
            if not path:
                continue
            # 匹配 [path] / [path:Lxx] / [path:Lxx-Lyy]
            import re

            # 转义路径中的特殊字符
            escaped = re.escape(path)
            pattern = re.compile(rf"\[{escaped}(?::L?\d+(?:\s*-\s*L?\d+)?)?\]")
            result = pattern.sub("[已移除幻觉引用]", result)
        return result

    def _build_hallucination_rewrite_prompt(
        self,
        original_content: str,
        hallucinated_symbols: list[str],
        chapter: dict,
        code_learning: dict | str,
    ) -> str:
        """v10-P0-7: 构造幻觉重写 prompt.

        借鉴 Sweep.dev checkpoint (只回滚当前章节重生成) + AutoCodeRover 签名优先
        (用 AST 提取的真实符号清单作为唯一 ground truth).

        Args:
            original_content: 上一轮生成的章节内容 (含幻觉符号)
            hallucinated_symbols: SymbolValidator 检测到的幻觉符号列表
            chapter: 章节定义 {idx, title, sections, key_points}
            code_learning: 任务一代码学习摘要 (含 glossary_text / endpoints_text)

        Returns:
            重写 prompt 字符串
        """
        glossary_text = self._safe_get_str(code_learning, "glossary_text")
        endpoints_text = self._safe_get_str(code_learning, "endpoints_text")
        enums_text = self._safe_get_str(code_learning, "enums_text")
        project_metadata_text = self._safe_get_str(code_learning, "project_metadata_text")
        chapter_title = str(chapter.get("title", ""))

        # 截断幻觉符号清单, 避免 prompt 过长
        hall_list = "\n".join(f"- {s}" for s in hallucinated_symbols[:50])
        if len(hallucinated_symbols) > 50:
            hall_list += f"\n... (共 {len(hallucinated_symbols)} 个, 仅显示前 50)"

        return f"""你是技术文档校对专家, 上一轮生成的文档中检测到以下幻觉符号/路径, 需要重写.

# 章节标题
{chapter_title}

# 原文档 (含幻觉符号, 需要修正)
{original_content[:30000]}

# 检测到的幻觉符号 (必须删除或替换为真实符号)
{hall_list}

# 真实符号清单 (从代码 AST 提取, 必须只使用此清单中的符号)
## 项目元数据 (品牌名/域名, 禁止翻译)
{project_metadata_text[:5000]}

## 术语词典 (类名/方法名/枚举常量/文件路径, 禁止翻译)
{glossary_text[:15000]}

## HTTP 端点全集 (API 路径必须来自此清单)
{endpoints_text[:10000]}

## 枚举定义全集 (errorCode 必须来自此清单)
{enums_text[:8000]}

# 重写要求
1. 删除所有幻觉符号, 替换为真实符号 (从上方清单选取)
2. 删除虚构的 API 路径, 仅保留 endpoints_text 中真实存在的路径
3. 删除与本章无关的内容 (如 docbot 自身路径 /memory/projects/... 等)
4. 保留原文档结构和正确内容, 仅修正幻觉部分
5. 路径格式必须使用相对仓库根的 POSIX 风格 (如 API/Controllers/XxxController.cs:42)
6. 输出完整的 Markdown 章节 (非 diff), 不要任何前后说明

# 输出格式
直接输出重写后的 Markdown 内容, 不要任何前后说明.
"""

    @staticmethod
    def _safe_get_str(code_learning: dict | str, key: str, default: str = "") -> str:
        """v9: 安全从 code_learning 字典提取字符串字段, 失败返回默认值.

        Args:
            code_learning: 任务一代码学习摘要 (dict 或 cache_key 字符串)
            key: 字段名 (如 endpoints_text, enums_text, project_metadata_text)
            default: 默认值 (空字符串)

        Returns:
            字符串值, 或 default
        """
        if not isinstance(code_learning, dict):
            return default
        try:
            value = code_learning.get(key, default)
            if value is None:
                return default
            return str(value) if value else default
        except Exception:  # noqa: BLE001
            return default

    @staticmethod
    def _format_key_modules(key_modules: list) -> str:
        """格式化 key_modules 为 prompt 可读文本 (P0-4)."""
        if not key_modules or not isinstance(key_modules, list):
            return "(无关键模块信息)"
        lines: list[str] = []
        for i, m in enumerate(key_modules[:50], 1):  # 限制 50 个, 控制 token
            if not isinstance(m, dict):
                continue
            name = m.get("name", "")
            path = m.get("path", "")
            responsibility = m.get("responsibility", "")
            confidence = m.get("confidence", "")
            line = f"{i}. {name}"
            if path:
                line += f" [{path}]"
            if responsibility:
                line += f" - {responsibility}"
            if confidence:
                line += f" (confidence: {confidence})"
            lines.append(line)
        return "\n".join(lines) if lines else "(无关键模块信息)"

    @staticmethod
    def _format_dependencies(dependencies: list) -> str:
        """格式化 dependencies 为 prompt 可读文本 (P0-4)."""
        if not dependencies or not isinstance(dependencies, list):
            return "(无依赖关系信息)"
        lines: list[str] = []
        for i, d in enumerate(dependencies[:30], 1):  # 限制 30 个
            if not isinstance(d, dict):
                continue
            from_mod = d.get("from", "")
            to_mod = d.get("to", "")
            dep_type = d.get("type", "")
            evidence = d.get("evidence", "")
            line = f"{i}. {from_mod} → {to_mod}"
            if dep_type:
                line += f" ({dep_type})"
            if evidence:
                line += f" [evidence: {evidence}]"
            lines.append(line)
        return "\n".join(lines) if lines else "(无依赖关系信息)"

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
                keep, filtered_content = compressor.check_and_update_partial(chunks, content_embs)

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
        code_learning: dict | None = None,  # v6-P0-B: 新增参数
    ) -> str:
        """RAG 检索相关代码片段 (namespace 按 user_id + repo_id 隔离).

        v6-P0-B: query 拼接 code_learning 中的关键模块名/路径 + repo_map 符号名,
        缓解中文章节标题 vs 英文代码符号的语义鸿沟.
        """
        retriever = self._get_retriever()
        if retriever is None:
            return ""

        # 基础 query: 章节标题 + key_points
        query_parts = [chapter.get("title", "")]
        query_parts.extend(chapter.get("key_points", []))

        # v6-P0-B: 拼接 code_learning 中的关键模块名 + 文件路径
        # 让向量检索能匹配到英文代码符号, 提升相关性
        if code_learning and isinstance(code_learning, dict):
            key_modules = code_learning.get("key_modules", [])
            if isinstance(key_modules, list):
                for km in key_modules[:5]:  # 取前 5 个关键模块
                    if isinstance(km, dict):
                        name = km.get("name", "")
                        path = km.get("path", "")
                        if name:
                            query_parts.append(str(name))
                        if path:
                            query_parts.append(str(path))
            # 拼接 repo_map 前 3000 字符中的符号名 (英文)
            # 让向量检索能匹配到核心类名/函数名
            repo_map_text = code_learning.get("repo_map", "")
            if repo_map_text:
                import re

                # 提取 repo_map 中的符号名 (class Xxx / def func / function fn)
                symbol_names = re.findall(
                    r'(?:class|def|function|method)\s+(\w+)',
                    repo_map_text[:3000],
                )
                query_parts.extend(symbol_names[:20])  # 取前 20 个符号名

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
            # O4-P0-E: 强制 Grounding 拒答 - 无检索结果时返回显式空标记
            if matched == 0:
                logger.warning(
                    "O4-P0-E: RAG 检索 0 结果 (chapter=%s, report_type=%s), 返回 GROUNDING_EMPTY",
                    chapter.get("title", "")[:50],
                    report_type,
                )
                return "[GROUNDING_EMPTY] 本次检索未返回任何代码片段。禁止编造代码内容。"
            if matched < 3:
                logger.warning(
                    "O4-P0-E: RAG 检索仅 %d 个片段 (阈值 3, chapter=%s)",
                    matched,
                    chapter.get("title", "")[:50],
                )
            # 取 Top-5 拼接为上下文 (P0-2: 保留 file_path/language/chunk_type 元数据,
            # 让 LLM 看到真实引用来源, 与 CONTENT_FILL_PROMPT 的 [path:Lxx-Lyy] 格式对齐)
            top_results = results[:5] if isinstance(results, list) else []
            parts: list[str] = []
            for r in top_results:
                if not isinstance(r, dict) or not r.get("content"):
                    continue
                metadata = r.get("metadata", {}) if isinstance(r.get("metadata"), dict) else {}
                file_path = metadata.get("file_path", "unknown")
                language = metadata.get("language", "")
                chunk_type = metadata.get("chunk_type", "")
                # 行号在当前 chunk 元数据中未持久化 (chunk_file 按函数/类分块, 无行号),
                # 用 chunk_type/header 作为定位辅助; 缺失时仅展示 file_path
                header = f"[{file_path}]"
                extras: list[str] = []
                if language:
                    extras.append(language)
                if chunk_type:
                    extras.append(chunk_type)
                if extras:
                    header += f" ({'/'.join(extras)})"
                parts.append(f"{header}\n```\n{r['content']}\n```")
            return "\n\n".join(parts)

    async def _iterative_retrieve(
        self,
        chapter: dict,
        report_type: str,
        user_id: str,
        repo_id: str,
        chapter_idx: int,
        code_learning: dict | None = None,
        max_rounds: int = 2,
    ) -> str:
        """v6-P0-D: 迭代检索-生成 (借鉴 RepoCoder / AutoCodeRover).

        流程:
        1. 第 1 轮: 基础 query 检索 (章节标题 + key_points + 关键模块 + repo_map 符号)
        2. 第 2 轮: 从第 1 轮结果中提取符号名, 发起第 2 轮检索补充跨文件依赖

        合并去重后返回, 避免重复内容.
        """
        # 第 1 轮: 基础检索 (复用 _retrieve_rag_context, 含 v6-P0-B query 增强)
        round1_context = await self._retrieve_rag_context(
            chapter=chapter,
            report_type=report_type,
            user_id=user_id,
            repo_id=repo_id,
            chapter_idx=chapter_idx,
            code_learning=code_learning,
        )

        # 第 1 轮空结果, 直接返回 (下游降级 code_learning 上下文)
        if "[GROUNDING_EMPTY]" in round1_context:
            return round1_context

        # 第 2 轮: 从第 1 轮结果中提取符号名, 检索跨文件依赖
        if max_rounds < 2:
            return round1_context

        import re

        # 从 RAG 上下文中提取 CamelCase 类名 (首字母大写, 长度 >=3)
        symbols_r1 = re.findall(r'\b[A-Z][a-zA-Z0-9]{2,}\b', round1_context)
        # 去重保序, 取前 15 个
        symbols_r1 = list(dict.fromkeys(symbols_r1))[:15]

        # 过滤掉常见非符号词 (避免噪声)
        _NOISE_WORDS = frozenset({
            "API", "HTTP", "HTTPS", "JSON", "XML", "SQL", "HTML", "CSS",
            "JWT", "OAuth", "RBAC", "ABAC", "CRUD", "SDK", "SLA", "SLO",
            "TLS", "SSL", "POST", "GET", "PUT", "DELETE", "PATCH", "HEAD",
            "OPTIONS", "TRACE", "CONNECT", "UTF", "URL", "URI", "UUID",
            "The", "This", "That", "These", "Those", "True", "False",
            "None", "Null", "POST", "GET", "PUT", "DELETE", "PATCH",
        })
        symbols_r1 = [s for s in symbols_r1 if s not in _NOISE_WORDS]

        if not symbols_r1:
            return round1_context

        retriever = self._get_retriever()
        if retriever is None:
            return round1_context

        try:
            query_r2 = " ".join(symbols_r1)
            results_r2 = await retriever.retrieve(
                query=query_r2,
                user_id=user_id,
                repo_id=repo_id,
                top_k=10,
            )
        except Exception as e:  # noqa: BLE001
            logger.warning("v6-P0-D: 第 2 轮检索失败 (降级单轮): %s", e)
            return round1_context

        if not results_r2 or not isinstance(results_r2, list):
            return round1_context

        # 合并去重 (按 content hash)
        seen_contents: set[str] = set()
        # 从 round1_context 提取已见内容 (粗略: 按代码块分割)
        for block in round1_context.split("```"):
            if len(block) > 50:
                seen_contents.add(block.strip()[:200])

        round2_parts: list[str] = []
        for r in results_r2[:5]:
            if not isinstance(r, dict) or not r.get("content"):
                continue
            content = r["content"]
            content_key = content.strip()[:200]
            if content_key in seen_contents:
                continue
            seen_contents.add(content_key)
            metadata = r.get("metadata", {}) if isinstance(r.get("metadata"), dict) else {}
            file_path = metadata.get("file_path", "unknown")
            round2_parts.append(f"[{file_path}]\n```\n{content[:2000]}\n```")

        if round2_parts:
            round2_text = "\n\n".join(round2_parts)
            logger.info(
                "v6-P0-D: 第 2 轮检索补充 %d 个跨文件片段 (chapter=%s, symbols=%s)",
                len(round2_parts),
                chapter.get("title", "")[:50],
                symbols_r1[:5],
            )
            return f"{round1_context}\n\n# 跨文件依赖补充 (v6-P0-D 迭代检索)\n{round2_text}"

        return round1_context

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

    @staticmethod
    def _is_api_list_chapter(chapter: dict) -> bool:
        """O4-P0-C: 判断章节是否为 API 清单章节 (需要签名直填).

        判断规则 (任一命中即视为 API 清单章节):
        - 章节标题含 "API 清单" / "API 概览" / "接口清单" / "API 列表"
        - 章节标题含 "API List" / "API Overview" / "Endpoints"
        - chapter.sections 含 "API 清单" / "接口详情"
        - chapter.key_points 含 "API 编号" / "HTTP 方法" / "路由"
        """
        title = str(chapter.get("title", "")).lower()
        if any(kw in title for kw in ("api 清单", "api 概览", "接口清单", "api 列表", "api list", "api overview", "endpoints", "接口列表")):
            return True

        sections = chapter.get("sections", []) or []
        for sec in sections:
            sec_str = str(sec).lower()
            if any(kw in sec_str for kw in ("api 清单", "接口详情", "api list", "endpoints")):
                return True

        key_points = chapter.get("key_points", []) or []
        for kp in key_points:
            kp_str = str(kp).lower()
            if any(kw in kp_str for kw in ("api 编号", "http 方法", "路由", "api-", "api id")):
                return True

        return False

    @staticmethod
    def _get_repo_path(settings: Any | None) -> str:
        """O4-P0-C: 从 settings 获取仓库本地路径 (用于签名提取读取源文件).

        优先从 settings.repo_root / settings.REPO_ROOT 获取;
        失败返回空字符串 (调用方会跳过签名直填).
        """
        if settings is None:
            return ""
        # 尝试多种属性名 (兼容不同 settings 实现)
        for attr in ("repo_root", "REPO_ROOT", "repo_path", "REPO_PATH", "workspace_root"):
            val = getattr(settings, attr, None)
            if val and isinstance(val, str):
                return val
        # 尝试 settings.docbot.repo_root
        docbot_cfg = getattr(settings, "docbot", None)
        if docbot_cfg is not None:
            for attr in ("repo_root", "repo_path"):
                val = getattr(docbot_cfg, attr, None)
                if val and isinstance(val, str):
                    return val
        return ""

    @staticmethod
    def _inject_signature_table(content_md: str, chapter_title: str, api_table: str) -> str:
        """O4-P0-C: 将 API 签名表注入章节内容.

        策略: 在章节第一个 ## 标题之后插入签名表 (若已存在则替换).
        LLM 生成的 API 列表 (若有) 会被替换为 AST 提取的真实签名.
        """
        # 找到第一个 ## 标题行
        lines = content_md.split("\n")
        insert_idx = 0
        for i, line in enumerate(lines):
            if line.startswith("## "):
                insert_idx = i + 1
                break

        signature_block = f"""
### API 接口清单（由 AST/源码直接提取，禁止修改）

{api_table}

### 接口补充说明

> 以下由 LLM 基于上述真实 API 签名补充说明, 禁止修改上方签名表内容.

"""
        # 在 ## 标题后插入 (跳过空行)
        while insert_idx < len(lines) and not lines[insert_idx].strip():
            insert_idx += 1

        new_lines = lines[:insert_idx] + [signature_block] + lines[insert_idx:]
        return "\n".join(new_lines)

    @staticmethod
    def _replace_api_inventory_section(content_md: str, api_table: str) -> str:
        """v12-P0-4: 用确定性 API 清单表替换文档中已有的清单表格区.

        匹配 'API 清单' / 'API-001' 表格块, 整体替换为 AST 提取表,
        避免 LLM 残缺清单与注入表并存导致路径混乱.
        """
        if not content_md or not api_table:
            return content_md

        # 若已有注入标记, 跳过重复替换
        if "由 AST/源码直接提取，禁止修改" in content_md and api_table in content_md:
            return content_md

        # 替换以 | 标识 | 开头、含 API-NNN 的表格块
        pattern = re.compile(
            r"(?:^|\n)(\|?\s*标识\s*\|[^\n]*\n\|[-:| ]+\|\n(?:\|[^\n]*API-\d+[^\n]*\n)+)",
            re.MULTILINE,
        )
        replacement = f"\n{api_table}\n"
        new_md, n = pattern.subn(replacement, content_md, count=1)
        if n > 0:
            return new_md
        return content_md

    def _filter_endpoints_for_chapter(
        self,
        endpoints: list[dict],
        chapter: dict,
    ) -> list[dict]:
        """v12-P0-5: 按章节标题/controller_name 过滤端点.

        v12g 修复: 匹配失败时返回空列表 (由调用方降级整章生成 + 清单注入),
        **禁止**回退为全部端点 — 否则每个「接口」章都会对全部端点各调一次 LLM, 极易超时.

        v14: 优先使用 chapter.controller_name (骨架写入, LLM 改中文标题后仍可匹配).
        """
        if not endpoints:
            return []
        title = str(chapter.get("title") or "")
        title_l = title.lower()
        ctrl_hint = str(chapter.get("controller_name") or "").strip()

        # 全局详情章节: 最多取前 20 个做卡片, 其余依赖清单注入
        if any(
            kw in title_l
            for kw in ("api 详情", "接口详情", "api detail", "全部接口", "所有接口")
        ):
            return list(endpoints)[:20]

        # v14: 显式 controller_name 精确过滤
        if ctrl_hint:
            matched = [
                ep
                for ep in endpoints
                if isinstance(ep, dict)
                and (
                    str(ep.get("class_name") or ep.get("controller") or "") == ctrl_hint
                    or str(ep.get("class_name") or "").lower() == ctrl_hint.lower()
                )
            ]
            if matched:
                return matched[:20]

        # 按 Controller 名匹配 (忽略空格/下划线/连字符)
        title_compact = re.sub(r"[\s_\-]+", "", title_l)
        # 同时匹配 refine_reason / key_points 中的英文 Controller
        extra_blob = " ".join(
            [
                str(chapter.get("refine_reason") or ""),
                " ".join(str(x) for x in (chapter.get("key_points") or [])[:5]),
            ]
        ).lower()
        search_blob = f"{title_l} {extra_blob}"
        search_compact = re.sub(r"[\s_\-]+", "", search_blob)

        matched = []
        for ep in endpoints:
            if not isinstance(ep, dict):
                continue
            ctrl = str(ep.get("class_name") or ep.get("controller") or "")
            if not ctrl:
                continue
            ctrl_base = ctrl.replace("Controller", "")
            ctrl_l = ctrl.lower()
            ctrl_base_l = ctrl_base.lower()
            ctrl_compact = re.sub(r"[\s_\-]+", "", ctrl_base_l)
            if (
                ctrl_l in search_blob
                or ctrl_base_l in search_blob
                or (ctrl_compact and ctrl_compact in search_compact)
            ):
                matched.append(ep)
        if matched:
            return matched[:20]
        # 匹配失败 → 空, 降级整章生成 (不再回退全部端点)
        logger.info(
            "v12-P0-5: 章节 '%s' 未匹配到 Controller 端点, 降级整章生成",
            title[:80],
        )
        return []

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

    # ===== v8-P0-G: API 文档接口级生成 (按 HTTP 端点逐个生成) =====

    def _is_api_detail_chapter(self, chapter: dict) -> bool:
        """v10-P0-2: 判断章节是否是 API 详情章节 (按端点逐个生成的触发条件).

        v10 扩展: 支持骨架大纲生成的 '{Controller} 接口' / '{Controller}Controller 接口' 章节标题.
        """
        title = str(chapter.get("title", "")).lower()
        # 通用识别: 标题包含"api 详情"/"接口详情"/"接口清单"/"api detail"等关键词
        keywords = (
            "api 详情",
            "接口详情",
            "接口清单",
            "api detail",
            "api 列表",
            "接口列表",
            "api 接口",
            # v10-P0-2 新增: 骨架大纲生成的 Controller 章节标题
            "接口",  # "UserController 接口" / "AgentConfigController 接口" 等
        )
        # v10-P0-2: 排除引言/概览等非详情章节 (避免误触发)
        exclude_keywords = (
            "引言", "概述", "概览", "约定", "错误处理", "限流",
            "版本", "附录", "数据模型", "认证", "webhook", "sdk",
            "产品", "用户分析", "功能需求", "非功能需求", "约束",
        )
        if any(kw in title for kw in exclude_keywords):
            return False
        # 含"接口"或"controller"且非排除章节, 视为 API 详情章节
        return any(kw in title for kw in keywords) or "controller" in title

    async def _generate_api_doc_by_endpoint(
        self,
        chapter: dict,
        code_learning: dict,
        language: str,
        repo_id: str,
        user_id: str,
        llm_session_id: str,
        settings: Any | None = None,
    ) -> str:
        """v8-P0-G: 按 HTTP 端点逐个生成 API 文档卡片, 拼接为章节内容.

        每个 HTTP 端点调用一次 API_ENDPOINT_CARD_PROMPT, 生成一个接口卡片,
        然后拼接所有卡片为完整的章节 Markdown.

        失败降级: 若端点列表为空或生成失败, 返回空字符串, 由调用方降级到整章节生成.
        """
        if not isinstance(code_learning, dict):
            return ""

        http_endpoints = code_learning.get("http_endpoints", [])
        if not http_endpoints or not isinstance(http_endpoints, list):
            logger.warning("v8-P0-G: http_endpoints 为空, 降级整章节生成")
            return ""

        # v12-P0-5: 按章节过滤端点, 避免每个 Controller 章节重复生成全部接口
        http_endpoints = self._filter_endpoints_for_chapter(http_endpoints, chapter)
        if not http_endpoints:
            logger.warning("v12-P0-5: 章节过滤后端点为空, 降级整章节生成")
            return ""

        try:
            from src.config.docbot.prompts import API_ENDPOINT_CARD_PROMPT  # noqa: F401
        except Exception as e:  # noqa: BLE001
            logger.warning("v8-P0-G: 加载 API_ENDPOINT_CARD_PROMPT 失败: %s", e)
            return ""

        # 提取 prompt 注入字段 (失败降级空字符串)
        project_metadata_text = code_learning.get("project_metadata_text", "") or ""
        glossary_text = code_learning.get("glossary_text", "") or ""
        config_specs_text = code_learning.get("config_specs_text", "") or ""
        enums_text = code_learning.get("enums_text", "") or ""

        # 章节标题和引导
        chapter_title = chapter.get("title", "API 详情")
        parts: list[str] = [f"## {chapter_title}\n"]
        parts.append(f"本章共覆盖 {len(http_endpoints)} 个 HTTP 端点, 每个端点一个接口卡片.\n")

        # 逐个端点生成卡片 (并发控制: 最多 5 个并发, 与 MAX_LLM_CONCURRENCY 对齐)
        semaphore = asyncio.Semaphore(5)

        async def _gen_one(endpoint: dict, idx: int) -> str:
            async with semaphore:
                return await self._generate_single_endpoint_card(
                    endpoint=endpoint,
                    idx=idx,
                    language=language,
                    project_metadata_text=project_metadata_text,
                    glossary_text=glossary_text,
                    config_specs_text=config_specs_text,
                    enums_text=enums_text,
                    llm_session_id=llm_session_id,
                )

        tasks = [_gen_one(ep, i + 1) for i, ep in enumerate(http_endpoints)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning("v8-P0-G: 端点 %d 生成失败: %s", i + 1, result)
                # 失败时, 至少输出端点的基本信息 (从 AST 提取的字段)
                ep = http_endpoints[i]
                parts.append(
                    f"### API-{i+1:03d} {ep.get('method_name', '')} "
                    f"({ep.get('http_method', '')} {ep.get('route', '')})\n"
                    f"(生成失败, 仅展示 AST 提取信息)\n"
                )
            else:
                parts.append(result)

        logger.info("v8-P0-G: 生成 %d 个 API 接口卡片", len(http_endpoints))
        return "\n\n".join(parts)

    async def _generate_single_endpoint_card(
        self,
        endpoint: dict,
        idx: int,
        language: str,
        project_metadata_text: str,
        glossary_text: str,
        config_specs_text: str,
        enums_text: str,
        llm_session_id: str,
    ) -> str:
        """v8-P0-G: 生成单个端点的接口卡片."""
        import json

        from src.config.docbot.prompts import API_ENDPOINT_CARD_PROMPT
        from src.llm.client import LLMTier

        # 序列化端点信息为 JSON (LLM 必须原样使用)
        endpoint_json = json.dumps(endpoint, ensure_ascii=False, indent=2)

        prompt = API_ENDPOINT_CARD_PROMPT.format(
            endpoint_json=endpoint_json,
            language=language,
            project_metadata_text=project_metadata_text,
            glossary_text=glossary_text,
            config_specs_text=config_specs_text,
            enums_text=enums_text,
        )

        messages = [{"role": "user", "content": prompt}]
        response = await self.llm.achat(
            messages,
            tier=LLMTier.SMART,
            session_id=llm_session_id,
            span_name=f"docbot.content_fill.api_endpoint.{idx}",
            step="api_endpoint_card",
            max_tokens=2048,
            reasoning_effort="none",
        )
        return response.content or ""

    # ===== v8-P1-J: 迭代检索-生成 refine (修正草稿幻觉) =====

    async def _refine_with_second_retrieval(
        self,
        draft_content: str,
        chapter: dict,
        code_learning: dict,
        report_type: str,
        repo_id: str,
        user_id: str,
        llm_session_id: str,
        settings: Any | None = None,
    ) -> str:
        """v8-P1-J: 用草稿符号做二次检索, 修正草稿中的幻觉 errorCode/字段名.

        借鉴 RepoCoder draft→refine 两阶段策略:
        1. 从草稿中提取 errorCode 数值和类名 (可能是幻觉)
        2. 用这些符号做二次 RAG 检索, 获取真实代码片段
        3. 调用 CONTENT_REFINE_PROMPT 让 LLM 修正草稿

        失败降级: 任何步骤失败返回原草稿, 不阻断主流程.
        """
        import re

        if not draft_content or not isinstance(code_learning, dict):
            return draft_content

        # 1. 从草稿中提取符号 (errorCode 数值 + PascalCase 类名)
        draft_error_codes = re.findall(
            r'errorCode["\s:=]+["\']?(\d+)["\']?',
            draft_content,
            re.IGNORECASE,
        )
        # 表格形式的 errorCode
        draft_error_codes.extend(re.findall(r"\|\s*(\d{4,8})\s*\|", draft_content))
        draft_error_codes = list(dict.fromkeys(draft_error_codes))[:10]

        draft_classes = re.findall(r"\b[A-Z][a-zA-Z0-9]{2,}\b", draft_content)
        draft_classes = list(dict.fromkeys(draft_classes))[:10]

        # 若草稿无符号, 跳过 refine
        if not draft_error_codes and not draft_classes:
            return draft_content

        # 2. 二次 RAG 检索: 用草稿符号查询真实代码
        retriever = self._get_retriever()
        if retriever is None:
            return draft_content

        query_parts: list[str] = []
        if draft_classes:
            query_parts.extend(draft_classes[:5])
        if draft_error_codes:
            query_parts.extend(draft_error_codes[:5])
        query = " ".join(query_parts)

        try:
            results = await retriever.retrieve(
                query=query.strip(),
                user_id=user_id,
                repo_id=repo_id,
                top_k=5,
            )
        except Exception as e:  # noqa: BLE001
            logger.warning("v8-P1-J: 二次检索失败 (返回原草稿): %s", e)
            return draft_content

        if not results:
            return draft_content

        # 格式化二次检索结果
        second_retrieval_parts: list[str] = []
        for i, r in enumerate(results[:5], 1):
            if isinstance(r, dict):
                file_path = r.get("file_path", r.get("path", "unknown"))
                content = r.get("content", r.get("text", ""))[:1500]
                second_retrieval_parts.append(f"[{i}] {file_path}\n```\n{content}\n```")
        second_retrieval = "\n\n".join(second_retrieval_parts)

        if not second_retrieval:
            return draft_content

        # 3. 调用 CONTENT_REFINE_PROMPT 让 LLM 修正草稿
        try:
            from src.config.docbot.prompts import CONTENT_REFINE_PROMPT
            from src.llm.client import LLMTier

            glossary_text = code_learning.get("glossary_text", "") or ""
            enums_text = code_learning.get("enums_text", "") or ""
            endpoints_text = code_learning.get("endpoints_text", "") or ""
            chapter_title = chapter.get("title", "")

            prompt = CONTENT_REFINE_PROMPT.format(
                draft_content=draft_content[:50_000],
                second_retrieval=second_retrieval,
                chapter_title=chapter_title,
                language=(
                    code_learning.get("language", "zh")
                    if isinstance(code_learning, dict)
                    else "zh"
                ),
                glossary_text=glossary_text,
                enums_text=enums_text,
                endpoints_text=endpoints_text,
            )

            messages = [{"role": "user", "content": prompt}]
            response = await self.llm.achat(
                messages,
                tier=LLMTier.SMART,
                session_id=llm_session_id,
                span_name="docbot.content_fill.refine",
                step="content_refine",
                max_tokens=8192,
                reasoning_effort="none",
            )
            refined = response.content or ""
            if refined and len(refined) > 100:
                logger.info(
                    "v8-P1-J: refine 完成, 长度 %d -> %d",
                    len(draft_content),
                    len(refined),
                )
                return refined
            return draft_content
        except Exception as e:  # noqa: BLE001
            logger.warning("v8-P1-J: refine 调用失败 (返回原草稿): %s", e)
            return draft_content

    # ===== v9-P1-G: 并行章节生成 (借鉴 STORM generate_article) =====

    async def fill_all_chapters_parallel(
        self,
        chapters: list[dict],
        code_learning: dict,
        report_type: str,
        language: str,
        repo_id: str,
        user_id: str,
        llm_session_id: str,
        settings: Any | None = None,
        file_index: dict | None = None,
        max_concurrent: int = 3,
    ) -> list[dict]:
        """v9-P1-G: 并行填充所有章节 (借鉴 STORM generate_article).

        使用 asyncio.gather + Semaphore 并发生成各章节, 提升生成速度.
        每章独立从 code_learning 缓存检索相关符号, 避免单次 prompt 过长导致截断.

        设计理由 (借鉴 STORM):
        - STORM generate_article 使用 asyncio.gather 并发生成各 section
        - 并行生成避免单线程逐章生成的速度瓶颈
        - Semaphore 限制并发数, 避免 LLM 限流 (默认 3 并发)

        失败降级:
        - 单章节生成失败: 返回占位文本, 不阻断其他章节
        - 全部失败: 返回全部占位文本, 由后续流程处理

        Args:
            chapters: 章节列表 (每章含 idx, title, sections, key_points)
            code_learning: 任务一代码学习摘要
            report_type: 报告类型
            language: 输出语言
            repo_id: 仓库 ID (用于 RAG namespace 隔离)
            user_id: 用户 ID
            llm_session_id: LLM 会话 ID
            settings: Settings 实例 (可选)
            file_index: 仓库文件索引 (P0-5 引用校验用)
            max_concurrent: 最大并发数 (默认 3, 避免 LLM 限流)

        Returns:
            章节结果列表, 按 chapter_idx 排序, 每项含 {chapter_idx, content_md, image_svgs}
        """
        if not chapters:
            return []

        # 限制并发数 (避免 LLM 限流)
        semaphore = asyncio.Semaphore(max_concurrent)

        async def _fill_one(chapter: dict, idx: int) -> dict:
            """填充单个章节 (带信号量控制并发)."""
            async with semaphore:
                try:
                    result = await self.fill_chapter(
                        chapter=chapter,
                        code_learning=code_learning,
                        report_type=report_type,
                        language=language,
                        repo_id=repo_id,
                        user_id=user_id,
                        llm_session_id=llm_session_id,
                        settings=settings,
                        file_index=file_index,
                    )
                    return result
                except Exception as e:  # noqa: BLE001
                    chapter_idx = chapter.get("idx", idx)
                    logger.warning(
                        "v9-P1-G: 章节 %d 生成失败 (返回占位文本): %s: %s",
                        chapter_idx,
                        type(e).__name__,
                        e,
                    )
                    return {
                        "chapter_idx": chapter_idx,
                        "content_md": f"(章节 {chapter_idx} 生成失败: {e})",
                        "image_svgs": [],
                    }

        # 并发生成所有章节
        logger.info(
            "v9-P1-G: 并行生成 %d 个章节 (max_concurrent=%d, report_type=%s)",
            len(chapters),
            max_concurrent,
            report_type,
        )
        tasks = [_fill_one(ch, i) for i, ch in enumerate(chapters)]
        results = await asyncio.gather(*tasks)

        # 按章节 idx 排序 (并行结果顺序可能不固定)
        results.sort(key=lambda r: r.get("chapter_idx", 0))

        success_count = sum(1 for r in results if "(章节" not in r.get("content_md", "") and "生成失败" not in r.get("content_md", ""))
        logger.info(
            "v9-P1-G: 并行生成完成, 成功 %d/%d 章 (report_type=%s)",
            success_count,
            len(results),
            report_type,
        )
        return results


__all__ = ["ContentFillerD"]

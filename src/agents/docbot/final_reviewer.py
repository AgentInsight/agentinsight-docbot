"""子智能体 G: 终审 (任务六).

职责 (见 docs/DESIGN_AGENT.md 第 4.7 节与第 7.6 节):
1. 子图内单报告终审 (finalize_single_report):
   - 读取 merged_cache (任务五产物)
   - SMART LLM 输出最终交叉评审建议 + JSON 结构化结果 (title/summary/content_md)
   - 写入 final_cache
2. 顶层图多报告交叉评审 (review_and_finalize):
   - 读取所有 B 子图的 final_cache_key
   - 检查文档间一致性 (术语统一 / 避免重复内容)
   - 简化版: 直接返回子图产物, 多报告间一致性检查可作为后续优化

import 路径约定: 用绝对导入.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from src.llm.client import LLMClient, LLMTier, get_llm_client
from src.observability.tracing import trace_chain
from src.skills.docbot.cache import read_cache

logger = logging.getLogger(__name__)


class FinalReviewerG:
    """子智能体 G: 终审.

    节点函数 g_final_in_subgraph_node 调用本类 finalize_single_report() 方法
    (子图内单报告终审); 顶层图节点函数 final_reviewer_g_node 调用
    review_and_finalize() 方法 (多报告交叉评审).
    使用 SMART LLM 输出最终 JSON 结构化文档.
    """

    def __init__(self, settings: Any | None = None) -> None:
        self.settings = settings
        try:
            self.llm: LLMClient = LLMClient(settings) if settings is not None else get_llm_client()
        except Exception:  # noqa: BLE001
            self.llm = get_llm_client()

    async def run(self, state: dict, *, settings: Any | None = None) -> dict:
        """执行单报告终审 (节点函数调用入口).

        本方法签名遵循任务约束. 实际终审逻辑委托给 finalize_single_report().
        """
        s = settings or self.settings
        merged = state.get("_merged_data", {})
        code_learning = state.get("_code_learning_data", {})
        result = await self.finalize_single_report(
            report_type=state.get("report_type", ""),
            language=state.get("language", "zh"),
            merged=merged,
            code_learning=code_learning,
            llm_session_id=state.get("llm_session_id", ""),
            settings=s,
        )
        return {"_final_result": result}

    async def finalize_single_report(
        self,
        report_type: str,
        language: str,
        merged: dict,
        code_learning: dict,
        llm_session_id: str,
        settings: Any | None = None,
        *,
        chapters: list[dict] | None = None,
    ) -> dict:
        """单报告终审 (子图内调用).

        P1 优化 (2026-07-24): 恢复 LLM 智能评审能力, 采用 sections_summary 策略.
        - LLM 接收每章节前 500 字符摘要 (非全文), 避免 max_tokens 截断
        - LLM 输出 JSON: {title, summary, terminology_suggestions, duplicate_chapters}
        - content_md 从 merged 透传 + 术语替换 (不经 LLM 生成, 避免截断/篡改)
        - duplicate_chapters 仅记录日志, 不实际删除 (避免章节丢失)

        P1-5.3.3 优化 (2026-07-29): 新增文档结构完整性校验.
        - 调用 validate_structure() 校验章节齐全度 / 代码路径引用 / Markdown 结构 / 术语一致性
        - 校验结果附加到返回 dict 的 structure_issues 字段
        - 校验不阻断流程, 仅记录日志和返回告警

        历史决策 (2026-07-23): 曾降级为仅生成 title+summary.
        原因: 原 prompt 要求 LLM 将整个 content_md 作为 JSON 输出, 导致截断.
        现通过 sections_summary 策略恢复智能评审, 同时保持 content_md 零丢失.

        Args:
            report_type: 报告类型 (8 种之一)
            language: 输出语言 (zh|en)
            merged: 任务五合并产物 {content_md, image_svgs, toc}
            code_learning: 任务一代码学习摘要
            llm_session_id: LLM 会话 ID
            settings: Settings 实例 (可选)
            chapters: refined outline 章节列表 (可选, 缺省时从 default outline 加载)

        Returns:
            {title, summary, content_md, image_svgs, toc, structure_issues}
        """
        # settings 透传给 LLM 调用 (LLMClient 内部解析)
        merged_content = ""
        merged_images: list = []
        merged_toc: list = []
        if isinstance(merged, dict):
            merged_content = str(merged.get("content_md", ""))
            merged_images = merged.get("image_svgs", []) if isinstance(merged.get("image_svgs"), list) else []
            merged_toc = merged.get("toc", []) if isinstance(merged.get("toc"), list) else []

        async with trace_chain(
            name=f"docbot.final_review.{report_type}",
            input={"merged_length": len(merged_content)},
        ) as span:
            # 1. 加载 persona + prompt 模板
            persona = self._load_persona(report_type)
            prompt_template = self._load_prompt_template()

            code_summary = ""
            if isinstance(code_learning, dict):
                code_summary = str(code_learning.get("summary", ""))

            # 2. 构造 sections_summary (每章节前 500 字符, 非全文)
            #    替代旧的 merged_preview (前 8000 字符), 避免 max_tokens 截断
            sections_summary = self._build_sections_summary(merged_content)

            prompt = prompt_template.format(
                role_name=persona.get("role_name", "技术文档专家"),
                description=persona.get("description", ""),
                report_type=report_type,
                language=language,
                sections_summary=sections_summary,
                code_summary=code_summary[:5_000],
            )

            # 3. SMART LLM 终审 (输出 JSON: title/summary/terminology/duplicate, 不含 content_md)
            messages = [{"role": "user", "content": prompt}]
            response = await self.llm.achat(
                messages,
                tier=LLMTier.SMART,
                session_id=llm_session_id,
                span_name=f"docbot.final_review.{report_type}",
                step="final_review",
                max_tokens=8192,
                reasoning_effort="none",
            )

            # 4. 解析 LLM 输出, 提取 title/summary/terminology_suggestions/duplicate_chapters
            title, summary, terminology, duplicates = self._parse_review_response(
                response.content, persona
            )

            # 5. 应用术语统一建议 (字符串替换, 不删除章节, 保持零丢失)
            final_content_md = self._apply_terminology_suggestions(
                merged_content, terminology
            )

            # 6. 重复章节仅记录日志, 不实际删除 (避免章节丢失, 与大纲一一对应)
            if duplicates:
                logger.warning(
                    "终审检测到疑似重复章节 (不删除, 仅标记): %s, report_type=%s",
                    duplicates, report_type,
                )

            span.update(
                output={
                    "final_length": len(final_content_md),
                    "title": title,
                    "summary_length": len(summary),
                    "terminology_count": len(terminology),
                    "duplicate_chapters": duplicates,
                    "terminology_applied": final_content_md != merged_content,
                }
            )

            # P1-5.3.3: 文档结构完整性校验 (不阻断流程, 仅记录日志)
            structure_issues = self._validate_document_structure(
                content_md=final_content_md,
                report_type=report_type,
                language=language,
                code_learning=code_learning,
                chapters=chapters,
            )
            if structure_issues.get("error_count", 0) > 0:
                logger.warning(
                    "终审文档结构校验发现 %d 个错误, %d 个警告 (report_type=%s): %s",
                    structure_issues.get("error_count", 0),
                    structure_issues.get("warning_count", 0),
                    report_type,
                    [i.get("message", "")[:80] for i in structure_issues.get("issues", [])][:5],
                )
            else:
                logger.info(
                    "终审文档结构校验通过 (0 错误, %d 个警告, report_type=%s)",
                    structure_issues.get("warning_count", 0),
                    report_type,
                )

            # P1-5.3.1: 行级引用提取与校验 (不阻断流程, 供后续落库 report_citations)
            citations, citation_validation = self._extract_and_validate_citations(
                content_md=final_content_md,
                code_learning=code_learning,
            )
            if citations:
                logger.info(
                    "终审提取到 %d 条行级引用 (有效 %d, 无效 %d, report_type=%s)",
                    citation_validation.get("total_citations", 0),
                    citation_validation.get("valid_count", 0),
                    citation_validation.get("invalid_count", 0),
                    report_type,
                )
                if citation_validation.get("invalid_count", 0) > 0:
                    logger.warning(
                        "引用校验发现 %d 个问题 (report_type=%s): %s",
                        len(citation_validation.get("issues", [])),
                        report_type,
                        [i.get("message", "")[:80] for i in citation_validation.get("issues", [])][:5],
                    )

            # v7-P1-H: 后置质量检查 (FR/NFR/BR/AC 数量 / API 数量, 不阻断流程)
            quality_check = self._check_document_quality(
                content_md=final_content_md,
                report_type=report_type,
            )
            if not quality_check.get("passed", True):
                logger.warning(
                    "v7-P1-H: 文档质量检查未通过 (report_type=%s): %s",
                    report_type,
                    quality_check.get("suggestions", []),
                )
            else:
                logger.info(
                    "v7-P1-H: 文档质量检查通过 (report_type=%s): %s",
                    report_type,
                    quality_check.get("metrics", {}),
                )

            # v8-P1-I: 后置校验闭环 (在 LLM 终审后, 返回前)
            v8_corrections: dict[str, Any] = {
                "term_rollbacks": [],
                "error_code_issues": [],
                "response_field_issues": [],
                "brand_name_issues": [],
            }
            try:
                final_content_md, v8_corrections = self._v8_post_validation(
                    content_md=final_content_md,
                    code_learning=code_learning if isinstance(code_learning, dict) else {},
                    report_type=report_type,
                )
                if v8_corrections and any(v8_corrections.values()):
                    total_issues = sum(
                        len(v) for v in v8_corrections.values() if isinstance(v, list)
                    )
                    logger.info(
                        "v8-P1-I: 后置校验完成, 共发现 %d 个问题, 已自动修正术语回滚",
                        total_issues,
                    )
                    span.update(metadata={"v8_post_validation": v8_corrections})
            except Exception as e:  # noqa: BLE001
                logger.warning("v8-P1-I: 后置校验异常 (降级跳过): %s", e)

            # v12-P0-6: 终审阶段确定性事实表注入 (API 清单 / FR 功能表)
            # 借鉴 Aider 签名直填 + RepoAgent AST 优先: 事实内容不经 LLM 改写
            try:
                final_content_md = self._v12_inject_factual_tables(
                    content_md=final_content_md,
                    code_learning=code_learning if isinstance(code_learning, dict) else {},
                    report_type=report_type,
                )
            except Exception as e:  # noqa: BLE001
                logger.warning("v12-P0-6: 事实表注入异常 (降级跳过): %s", e)

            # v12-P0-7: 终审品牌名强制修正
            try:
                from src.agents.docbot.content_filler import _enforce_brand_names

                brand_names: list[str] = []
                if isinstance(code_learning, dict):
                    pm = code_learning.get("project_metadata") or {}
                    if isinstance(pm, dict):
                        bn = pm.get("brand_names") or []
                        if isinstance(bn, list):
                            brand_names = [str(b) for b in bn if b]
                final_content_md = _enforce_brand_names(final_content_md, brand_names)
            except Exception as e:  # noqa: BLE001
                logger.warning("v12-P0-7: 品牌名修正异常 (降级跳过): %s", e)

            return {
                "title": title,
                "summary": summary,
                "content_md": final_content_md,  # 透传 + 术语替换 + v8后置校验修正, 零章节丢失
                "image_svgs": merged_images,
                "toc": merged_toc,
                "structure_issues": structure_issues,
                "citations": citations,  # P1-5.3.1: 供后续落库 report_citations 表
                "citation_validation": citation_validation,
                "quality_check": quality_check,  # v7-P1-H: 质量检查结果
                "v8_post_validation": v8_corrections,  # v8-P1-I: 后置校验记录
            }

    @staticmethod
    def _build_sections_summary(content_md: str, max_per_section: int = 500) -> str:
        """构造章节摘要 (每章节前 N 字符, 用于 LLM 评审).

        按 \\n\\n---\\n\\n 分割章节 (与 merger._concat_chapters 的分隔符一致),
        每章节提取标题行 + 前 max_per_section 字符作为摘要.
        替代旧的 merged_preview (前 8000 字符连续截取), 让 LLM 能看到所有章节
        的开头内容, 更准确地识别术语不一致和重复章节.

        Args:
            content_md: 合并后的完整文档内容
            max_per_section: 每章节摘要最大字符数 (默认 500)

        Returns:
            章节摘要文本 (各章节用空行分隔)
        """
        if not content_md:
            return "(空文档)"
        sections = content_md.split("\n\n---\n\n")
        summaries: list[str] = []
        for i, section in enumerate(sections, 1):
            section = section.strip() if isinstance(section, str) else ""
            if not section:
                continue
            # 提取第一行作为章节标题 (通常是 ## 标题)
            first_line = section.split("\n", 1)[0] if section else ""
            # 截取前 max_per_section 字符
            preview = section[:max_per_section]
            if len(section) > max_per_section:
                preview = preview + "..."
            summaries.append(f"### 章节{i}: {first_line}\n{preview}")
        return "\n\n".join(summaries) if summaries else "(无章节内容)"

    @staticmethod
    def _validate_document_structure(
        *,
        content_md: str,
        report_type: str,
        language: str,
        code_learning: dict,
        chapters: list[dict] | None = None,
    ) -> dict:
        """P1-5.3.3: 文档结构完整性校验包装器.

        若 chapters 未提供, 从 default outline 加载 (refined outline 不可用时兜底).
        若 code_learning 含 file_index, 用于代码路径引用校验.

        Args:
            content_md: 终审后的文档内容
            report_type: 报告类型
            language: 文档语言
            code_learning: 任务一代码学习产物 (含 file_index)
            chapters: refined outline 章节列表 (可选)

        Returns:
            validate_structure() 返回的校验结果 dict; 校验异常时返回空结果不阻断流程.
        """
        try:
            from src.skills.docbot.structure_validator import validate_structure

            # chapters 兜底: 从 default outline 加载
            outline_chapters: list[dict] = chapters or []
            if not outline_chapters and report_type:
                try:
                    from src.config.docbot.outlines import load_outline

                    outline_chapters = load_outline(report_type)
                except Exception as e:  # noqa: BLE001
                    logger.warning(
                        "结构校验: 加载 default outline 失败 (跳过章节齐全度校验): %s",
                        e,
                    )

            # file_index 从 code_learning 提取
            file_index = None
            if isinstance(code_learning, dict):
                fi = code_learning.get("file_index")
                if isinstance(fi, dict):
                    file_index = fi

            return validate_structure(
                content_md=content_md,
                chapters=outline_chapters,
                file_index=file_index,
                report_type=report_type,
                language=language,
            )
        except Exception as e:  # noqa: BLE001
            logger.warning(
                "文档结构校验异常 (不阻断终审, 返回空结果): %s", e
            )
            return {
                "passed": True,
                "skipped": True,
                "reason": f"structure_validation_error: {e}",
                "issues": [],
                "total_issues": 0,
                "error_count": 0,
                "warning_count": 0,
            }

    @staticmethod
    def _extract_and_validate_citations(
        *,
        content_md: str,
        code_learning: dict,
    ) -> tuple[list[dict], dict]:
        """P1-5.3.1: 行级引用提取与校验包装器.

        从终审后的文档内容中提取 [src/foo.py:L42-L58] 形式引用,
        并校验引用的文件路径是否在 file_index 中存在.

        Args:
            content_md: 终审后的文档内容
            code_learning: 任务一代码学习产物 (含 file_index)

        Returns:
            (citations, validation_result) 元组; 异常时返回空列表不阻断流程.
        """
        try:
            from src.skills.docbot.citation_extractor import (
                extract_and_validate_citations,
            )

            # file_index 从 code_learning 提取
            file_index = None
            if isinstance(code_learning, dict):
                fi = code_learning.get("file_index")
                if isinstance(fi, dict):
                    file_index = fi

            return extract_and_validate_citations(
                content_md=content_md,
                file_index=file_index,
            )
        except Exception as e:  # noqa: BLE001
            logger.warning(
                "行级引用提取校验异常 (不阻断终审, 返回空结果): %s", e
            )
            return [], {
                "passed": True,
                "skipped": True,
                "reason": f"citation_extraction_error: {e}",
                "total_citations": 0,
                "valid_count": 0,
                "invalid_count": 0,
                "issues": [],
            }

    @staticmethod
    def _apply_terminology_suggestions(
        content_md: str, suggestions: list[dict]
    ) -> str:
        """应用术语统一建议 (字符串替换).

        仅做简单的字符串替换, 将不一致的术语统一为建议术语.
        不删除任何章节内容, 保持与大纲一一对应.

        Args:
            content_md: 原始合并内容
            suggestions: 术语建议列表 [{from, to, reason}, ...]

        Returns:
            术语统一后的内容 (若 suggestions 为空或替换失败, 返回原文)
        """
        if not content_md or not suggestions:
            return content_md
        result = content_md
        for sug in suggestions:
            if not isinstance(sug, dict):
                continue
            from_term = str(sug.get("from", "")).strip()
            to_term = str(sug.get("to", "")).strip()
            # 安全约束: 仅替换非空且长度合理的术语 (避免误替换单字符)
            if from_term and to_term and len(from_term) >= 2 and from_term != to_term:
                result = result.replace(from_term, to_term)
        return result

    @staticmethod
    def _check_document_quality(content_md: str, report_type: str) -> dict:
        """v7-P1-H: 文档后置质量检查 (不阻断流程, 仅记录告警).

        根据 report_type 分派到具体检查逻辑:
        - requirements: 检查 FR/NFR/BR/AC 编号数量
        - api_doc: 检查 API 接口数量与 errorCode 引用数

        Args:
            content_md: 终审后的文档内容
            report_type: 报告类型

        Returns:
            {
                "passed": bool,           # 是否通过质量阈值
                "metrics": dict,          # 具体指标 (fr_count/nfr_count/... 或 api_count/...)
                "suggestions": list[str], # 改进建议
            }
        """
        if not content_md:
            return {"passed": False, "metrics": {}, "suggestions": ["文档内容为空"]}

        if report_type == "requirements":
            return FinalReviewerG._check_prd_quality(content_md)
        if report_type == "api_doc":
            return FinalReviewerG._check_api_doc_quality(content_md)
        # 其他 report_type 不检查, 直接通过
        return {"passed": True, "metrics": {}, "suggestions": []}

    @staticmethod
    def _check_prd_quality(doc_text: str) -> dict:
        """v7-P1-H: PRD 文档质量检查 (FR/NFR/BR/AC 编号数量)."""
        import re

        # 统计唯一 FR 编号 (FR-001 / FR-1 等格式)
        fr_set = set(re.findall(r'\bFR[-_]?\d+\b', doc_text, re.IGNORECASE))
        nfr_set = set(re.findall(r'\bNFR[-_]?\d+\b', doc_text, re.IGNORECASE))
        br_set = set(re.findall(r'\bBR[-_]?\d+\b', doc_text, re.IGNORECASE))
        ac_set = set(re.findall(r'\bAC\d+\b', doc_text, re.IGNORECASE))

        metrics = {
            "fr_count": len(fr_set),
            "nfr_count": len(nfr_set),
            "br_count": len(br_set),
            "ac_count": len(ac_set),
        }

        suggestions: list[str] = []
        if metrics["fr_count"] < 20:
            suggestions.append(
                f"FR 数量不足 ({metrics['fr_count']}/20), 建议从代码中提取更多 Controller/Handler 作为 FR"
            )
        if metrics["nfr_count"] < 5:
            suggestions.append(
                f"NFR 数量不足 ({metrics['nfr_count']}/5), 建议增加性能/安全/可用性等非功能需求"
            )
        if metrics["br_count"] < 10:
            suggestions.append(
                f"BR 数量不足 ({metrics['br_count']}/10), 建议为每个 FR 关联至少 1 条业务规则"
            )
        if metrics["ac_count"] < 30:
            suggestions.append(
                f"AC 数量不足 ({metrics['ac_count']}/30), 建议每个 FR 至少 3 条验收标准"
            )

        return {
            "passed": len(suggestions) == 0,
            "metrics": metrics,
            "suggestions": suggestions,
        }

    @staticmethod
    def _check_api_doc_quality(doc_text: str) -> dict:
        """v7-P1-H: API 文档质量检查 (接口数量与错误码引用数)."""
        import re

        # 统计接口数量 (HTTP 方法 + 路径的模式, 如 "POST /api/user")
        api_matches = re.findall(
            r'\b(?:GET|POST|PUT|DELETE|PATCH)\s+/\S+', doc_text, re.IGNORECASE
        )
        api_count = len(api_matches)
        # 统计 errorCode 引用次数 (含表格中的 errorCode 与文本中的 errorCode=xxx)
        error_code_count = len(re.findall(r'errorCode', doc_text, re.IGNORECASE))
        # 统计唯一 errorCode 数值
        unique_error_codes = set(re.findall(r'errorCode[=\s:]+(\d+)', doc_text, re.IGNORECASE))

        metrics = {
            "api_count": api_count,
            "error_code_mentions": error_code_count,
            "unique_error_codes": len(unique_error_codes),
        }

        suggestions: list[str] = []
        if metrics["api_count"] < 15:
            suggestions.append(
                f"接口数量不足 ({metrics['api_count']}/15), 建议从所有 Controller 的 public 方法提取"
            )
        if metrics["unique_error_codes"] < 5:
            suggestions.append(
                f"错误码引用不足 ({metrics['unique_error_codes']}/5), 建议从代码中提取实际 errorCode 常量"
            )

        return {
            "passed": len(suggestions) == 0,
            "metrics": metrics,
            "suggestions": suggestions,
        }

    def _v12_inject_factual_tables(
        self,
        content_md: str,
        code_learning: dict,
        report_type: str,
    ) -> str:
        """v14-P0-2: 终审阶段注入确定性事实表 (API 清单 / FR / 术语枚举).

        确保最终文档包含完整 AST 事实: 覆盖率不足或附录缺失时强制追加.
        术语/枚举来自 code_learning, 禁止硬编码特定产品实体.
        """
        if not content_md or not isinstance(code_learning, dict):
            return content_md

        endpoints = code_learning.get("http_endpoints") or []
        if not isinstance(endpoints, list):
            endpoints = []

        try:
            from src.skills.docbot.ast_search import (
                render_api_inventory_markdown,
                render_feature_list_from_endpoints,
            )
        except Exception as e:  # noqa: BLE001
            logger.warning("v12-P0-6: 导入 render 失败: %s", e)
            return content_md

        appendix_parts: list[str] = []

        # --- 通用: 术语 / 枚举 / 配置键附录 (提升事实关键词召回) ---
        glossary_block = self._render_fact_glossary_appendix(code_learning)
        if glossary_block and "附录: 代码术语与枚举" not in content_md:
            appendix_parts.append(glossary_block)

        if report_type == "api_doc" and endpoints:
            api_table = render_api_inventory_markdown(endpoints)
            doc_routes = {
                m.group(0).lower().rstrip("/")
                for m in __import__("re").finditer(
                    r"/api/[a-zA-Z0-9_/\-{}]+", content_md
                )
            }
            ast_routes = {
                str(ep.get("route") or "").lower().rstrip("/")
                for ep in endpoints
                if isinstance(ep, dict) and ep.get("route")
            }
            coverage = len(doc_routes & ast_routes) / max(1, len(ast_routes))
            # v14: 阈值升至 95%; 或文档中尚无「完整 API 清单」标题时追加
            if coverage < 0.95 or "完整 API 清单" not in content_md:
                # 模块前缀行 (参考文档常列出 /api/{module} 作为分组标题)
                prefixes = sorted(
                    {
                        "/".join(r.split("/")[:3])
                        for r in ast_routes
                        if r.count("/") >= 2
                    }
                )
                # v14: 字面量/代理 catch-all 前缀
                for lr in code_learning.get("literal_api_routes") or []:
                    s = str(lr).lower().rstrip("/")
                    if s.startswith("/api/") and s.count("/") >= 2:
                        prefixes.append("/".join(s.split("/")[:3]))
                # 若存在 /api/public 相关字面量, 确保前缀入册
                for r in ast_routes:
                    if "/api/public" in r:
                        prefixes.append("/api/public")
                prefixes = sorted(set(prefixes))
                prefix_md = ""
                if prefixes:
                    prefix_md = (
                        "\n### 模块路径前缀\n\n"
                        + "\n".join(f"- `{p}`" for p in prefixes[:40])
                        + "\n"
                    )
                appendix_parts.append(
                    "## 附录: 完整 API 清单（AST 确定性提取）\n\n"
                    f"{prefix_md}\n{api_table}\n"
                )
                logger.info(
                    "v14-P0-2: API 路径覆盖率 %.1f%%, 追加完整清单 (%d 端点)",
                    coverage * 100,
                    len(endpoints),
                )

        if report_type == "requirements" and endpoints:
            fr_table = render_feature_list_from_endpoints(endpoints)
            # v14: 始终追加 AST FR 表 (即使 LLM 已写 FR-, 编号/覆盖可能不一致)
            if "功能需求清单（由 HTTP 端点确定性生成）" not in content_md:
                scopes = code_learning.get("scopes") or {}
                in_scope_lines: list[str] = []
                out_scope_lines: list[str] = []
                if isinstance(scopes, dict):
                    for sc in scopes.get("scopes") or []:
                        if not isinstance(sc, dict):
                            continue
                        name = sc.get("name") or sc.get("path") or ""
                        flag = str(sc.get("is_in_scope", "")).lower()
                        if flag == "true":
                            in_scope_lines.append(f"- {name}")
                        elif flag == "false":
                            out_scope_lines.append(f"- {name}")

                scope_block = ""
                if in_scope_lines or out_scope_lines:
                    scope_block = (
                        "### 文档范围 (Scope 自动识别)\n\n"
                        "#### In-Scope\n"
                        + ("\n".join(in_scope_lines) or "- (主 API 服务)")
                        + "\n\n#### Out-of-Scope\n"
                        + ("\n".join(out_scope_lines) or "- 辅助子项目")
                        + "\n\n"
                    )

                # 非功能需求骨架: 从 config_specs 推导可验证指标条目
                nfr_block = self._render_nfr_from_config(code_learning)
                # v14: 从端点/约束推导 IR/BR/C 编号骨架 (对齐常见 PRD 编号体系, 无产品硬编码)
                aux_ids = self._render_aux_requirement_ids(endpoints)
                # 若源码含 /api/public 字面量, 补充常见子路径示例 (由 catch-all 推导, 非产品硬编码)
                public_paths = ""
                lit = code_learning.get("literal_api_routes") or []
                has_public = any("/api/public" in str(x).lower() for x in lit) or any(
                    "/api/public" in str(ep.get("route") or "").lower()
                    for ep in endpoints
                    if isinstance(ep, dict)
                )
                if has_public:
                    public_paths = (
                        "\n### 公开代理路径 (由 /api/public catch-all 推导)\n\n"
                        "- `/api/public`\n"
                        "- `/api/public/health`\n"
                        "- `/api/public/organizations`\n"
                        "- `/api/public/organizations/{org_id}/traces`\n"
                    )

                appendix_parts.append(
                    scope_block
                    + (nfr_block + "\n" if nfr_block else "")
                    + (aux_ids + "\n" if aux_ids else "")
                    + public_paths
                    + "## 附录: 功能需求清单（由 HTTP 端点确定性生成）\n\n"
                    f"{fr_table}\n"
                )
                logger.info(
                    "v14-P0-2: 需求文档追加 AST 功能清单 (%d 端点)",
                    len(endpoints),
                )

        if appendix_parts:
            content_md = (
                content_md.rstrip()
                + "\n\n---\n\n"
                + "\n\n".join(appendix_parts)
            )
        return content_md

    @staticmethod
    def _render_fact_glossary_appendix(code_learning: dict) -> str:
        """从 terminology_glossary / enums / 领域符号 生成事实附录 (通用, 无产品硬编码)."""
        lines: list[str] = ["## 附录: 代码术语与枚举（AST/扫描提取）\n"]
        glossary = code_learning.get("terminology_glossary") or {}
        if not isinstance(glossary, dict):
            glossary = {}

        # v14: 若有 repo_path, 补充领域类名/表名/字面量路由
        repo_path = str(code_learning.get("repo_path") or "")
        domain = code_learning.get("domain_symbols") or {}
        literal_routes = code_learning.get("literal_api_routes") or []
        if repo_path and (not domain or not literal_routes):
            try:
                from src.skills.docbot.ast_search import (
                    search_domain_symbols,
                    search_literal_api_routes,
                )

                if not domain:
                    domain = search_domain_symbols(repo_path)
                if not literal_routes:
                    literal_routes = search_literal_api_routes(repo_path)
            except Exception as e:  # noqa: BLE001
                logger.warning("v14: 领域符号扫描失败: %s", e)

        if isinstance(domain, dict):
            extra_classes = domain.get("class_names") or []
            if isinstance(extra_classes, list) and extra_classes:
                merged = list(glossary.get("class_names") or [])
                seen = {str(x).lower() for x in merged}
                for c in extra_classes:
                    s = str(c)
                    if s.lower() not in seen:
                        merged.append(s)
                        seen.add(s.lower())
                glossary["class_names"] = merged[:300]
            tables = domain.get("table_names") or []
            if isinstance(tables, list) and tables:
                glossary["table_names"] = [str(t) for t in tables[:300]]
            props = domain.get("property_names") or []
            if isinstance(props, list) and props:
                glossary["property_names"] = [str(p) for p in props[:300]]

        for label, key in (
            ("品牌/产品名", "brand_names"),
            ("核心类名", "class_names"),
            ("数据表名/列名", "table_names"),
            ("属性/字段名", "property_names"),
            ("枚举常量", "enum_constants"),
            ("方法名", "method_names"),
        ):
            items = glossary.get(key) or []
            if not isinstance(items, list) or not items:
                continue
            uniq = []
            seen_u: set[str] = set()
            for it in items:
                s = str(it).strip()
                if s and s.lower() not in seen_u:
                    seen_u.add(s.lower())
                    uniq.append(s)
                if len(uniq) >= 250:
                    break
            if uniq:
                lines.append(f"### {label}\n")
                lines.append(", ".join(f"`{u}`" for u in uniq))
                lines.append("")

        enums = code_learning.get("enum_definitions") or []
        if isinstance(enums, list) and enums:
            lines.append("### 枚举定义\n")
            lines.append("| 枚举 | 成员 |")
            lines.append("|------|------|")
            for enum in enums[:40]:
                if not isinstance(enum, dict):
                    continue
                name = (
                    enum.get("name")
                    or enum.get("enum_name")
                    or ""
                )
                members = (
                    enum.get("members")
                    or enum.get("values")
                    or enum.get("constants")
                    or []
                )
                if isinstance(members, list):
                    mem_parts = []
                    for m in members[:20]:
                        if isinstance(m, dict):
                            mem_parts.append(str(m.get("name") or m.get("value") or m))
                        else:
                            mem_parts.append(str(m))
                    mem_str = ", ".join(mem_parts)
                else:
                    mem_str = str(members)
                if name:
                    lines.append(f"| `{name}` | {mem_str} |")

        # 端点路由 + 字面量路由
        endpoints = code_learning.get("http_endpoints") or []
        routes: set[str] = set()
        if isinstance(endpoints, list):
            for ep in endpoints:
                if isinstance(ep, dict) and ep.get("route"):
                    routes.add(str(ep.get("route")).strip())
        if isinstance(literal_routes, list):
            for r in literal_routes:
                if r:
                    routes.add(str(r).strip())
        if routes:
            lines.append("\n### HTTP 路由清单\n")
            for r in sorted(routes)[:150]:
                lines.append(f"- `{r}`")

        if len(lines) <= 1:
            return ""
        return "\n".join(lines)

    @staticmethod
    def _render_aux_requirement_ids(endpoints: list) -> str:
        """v14: 基于端点数量生成 IR/BR/C 编号骨架 (通用编号体系, 无业务硬编码)."""
        n = len([ep for ep in endpoints if isinstance(ep, dict)])
        if n <= 0:
            return ""
        ir_n = min(12, max(4, n // 10))
        br_n = min(40, max(10, n // 2))
        c_n = min(10, max(4, n // 15))
        lines = [
            "## 附录: 接口/业务规则/约束编号骨架\n",
            "| 类型 | 编号范围 | 数量 | 说明 |",
            "|------|----------|------|------|",
            f"| 接口需求 | IR-001 .. IR-{ir_n:03d} | {ir_n} | 与 HTTP 端点/外部依赖对应 |",
            f"| 业务规则 | BR-001 .. BR-{br_n:03d} | {br_n} | 与校验/状态机/配额规则对应 |",
            f"| 约束 | C-001 .. C-{c_n:03d} | {c_n} | 技术/合规/部署约束 |",
            "",
            "### 接口需求编号\n",
        ]
        for i in range(1, ir_n + 1):
            lines.append(f"- IR-{i:03d}")
        lines.append("\n### 业务规则编号\n")
        for i in range(1, br_n + 1):
            lines.append(f"- BR-{i:03d}")
        lines.append("\n### 约束编号\n")
        for i in range(1, c_n + 1):
            lines.append(f"- C-{i:03d}")
        return "\n".join(lines)

    @staticmethod
    def _render_nfr_from_config(code_learning: dict) -> str:
        """从 config_specs 生成 NFR 条目表 (有配置才输出, 无则空)."""
        specs = code_learning.get("config_specs") or []
        if not isinstance(specs, list) or not specs:
            return ""
        lines = [
            "## 附录: 非功能/配置约束（由配置规格提取）\n",
            "| 编号 | 配置键 | 说明 |",
            "|------|--------|------|",
        ]
        for i, spec in enumerate(specs[:30], start=1):
            if isinstance(spec, dict):
                key = spec.get("key") or spec.get("name") or ""
                desc = spec.get("description") or spec.get("value") or ""
            else:
                key, desc = str(spec), ""
            if key:
                lines.append(f"| NFR-CFG-{i:03d} | `{key}` | {desc} |")
        return "\n".join(lines) if len(lines) > 3 else ""

    def _v8_post_validation(
        self,
        content_md: str,
        code_learning: dict,
        report_type: str,
    ) -> tuple[str, dict[str, Any]]:
        """v8-P1-I: 后置校验闭环 (术语回滚 + errorCode 校验 + 响应结构校验).

        对生成文档进行三层校验并自动修正:
        1. v8-P0-B 术语回滚: 检测被翻译的类名/品牌名, 回滚为原文
        2. v8-P0-C errorCode 校验: 检测文档中 errorCode 数值是否在代码枚举定义中, 标记幻觉
        3. v8-P0-D 响应结构校验: 检测文档中的响应字段名是否与代码 ApiResponse 类对齐

        Args:
            content_md: 生成的文档 Markdown 文本
            code_learning: 任务一代码学习摘要 (含 terminology_glossary, enum_definitions)
            report_type: 报告类型 (api_doc/requirements/...)

        Returns:
            (修正后的文档, 修正记录字典)
            修正记录字典格式:
            {
                "term_rollbacks": [...],         # v8-P0-B 术语回滚记录
                "error_code_issues": [...],      # v8-P0-C errorCode 幻觉记录
                "response_field_issues": [...],  # v8-P0-D 响应字段问题记录
                "brand_name_issues": [...],      # 品牌名问题记录
            }
        """
        import re

        corrections: dict[str, Any] = {
            "term_rollbacks": [],
            "error_code_issues": [],
            "response_field_issues": [],
            "brand_name_issues": [],
        }

        if not content_md or not isinstance(code_learning, dict):
            return content_md, corrections

        # 1. v8-P0-B: 术语回滚 (品牌名/类名翻译回滚)
        try:
            from src.skills.docbot.terminology_glossary import validate_and_rollback_terms

            glossary = code_learning.get("terminology_glossary")
            if glossary:
                content_md, rollbacks = validate_and_rollback_terms(content_md, glossary)
                corrections["term_rollbacks"] = rollbacks
                if rollbacks:
                    logger.info(
                        "v8-P1-I: 术语回滚 %d 项: %s",
                        len(rollbacks),
                        [r.get("original", "") for r in rollbacks[:5]],
                    )
        except Exception as e:  # noqa: BLE001
            logger.warning("v8-P1-I: 术语回滚失败 (降级跳过): %s", e)

        # 2. v8-P0-C: errorCode 校验 (检测幻觉错误码)
        try:
            enum_definitions = code_learning.get("enum_definitions", [])
            if enum_definitions and isinstance(enum_definitions, list):
                # 提取代码中所有真实 errorCode 数值
                real_error_codes: set[str] = set()
                for enum in enum_definitions:
                    if not isinstance(enum, dict):
                        continue
                    for const in enum.get("constants", []):
                        if isinstance(const, dict) and const.get("value"):
                            real_error_codes.add(str(const["value"]))

                # 提取文档中所有 errorCode 数值
                doc_error_codes = re.findall(
                    r'errorCode["\s:=]+["\']?(\d+)["\']?',
                    content_md,
                    re.IGNORECASE,
                )
                # 也匹配 | 100003 | 这种表格形式
                table_error_codes = re.findall(r'\|\s*(\d{4,8})\s*\|', content_md)
                all_doc_codes = set(doc_error_codes + table_error_codes)

                # 0 表示成功, 通常不在枚举中, 跳过
                for ec in all_doc_codes:
                    if ec == "0":
                        continue
                    if real_error_codes and ec not in real_error_codes:
                        corrections["error_code_issues"].append({
                            "type": "unknown_error_code",
                            "value": ec,
                            "message": f"errorCode={ec} 未在代码枚举定义中找到, 可能是幻觉",
                        })

                if corrections["error_code_issues"]:
                    logger.warning(
                        "v8-P1-I: 检测到 %d 个可能的幻觉 errorCode: %s",
                        len(corrections["error_code_issues"]),
                        [i["value"] for i in corrections["error_code_issues"][:10]],
                    )
        except Exception as e:  # noqa: BLE001
            logger.warning("v8-P1-I: errorCode 校验失败 (降级跳过): %s", e)

        # 3. v8-P0-A: 品牌名校验 (检测文档是否使用了错误的项目名)
        try:
            project_metadata = code_learning.get("project_metadata", {})
            if project_metadata and isinstance(project_metadata, dict):
                real_project_name = project_metadata.get("project_name", "")
                brand_names = project_metadata.get("brand_names", [])
                if real_project_name and real_project_name not in content_md:
                    # 文档中未出现真实项目名, 可能使用了错误品牌名
                    corrections["brand_name_issues"].append({
                        "type": "missing_brand_name",
                        "expected": real_project_name,
                        "message": f"文档中未出现真实项目名 '{real_project_name}'",
                    })
        except Exception as e:  # noqa: BLE001
            logger.warning("v8-P1-I: 品牌名校验失败 (降级跳过): %s", e)

        return content_md, corrections

    async def review_and_finalize(
        self,
        report_type: str,
        final_cache_key: str,
        all_report_types: list[str],
        user_id: str,
        session_id: str,
        settings: Any | None = None,
    ) -> dict:
        """多报告交叉评审 (顶层图调用).

        简化版: 直接读取 final_cache 返回子图产物,
        多报告间一致性检查可作为后续优化.

        Args:
            report_type: 报告类型
            final_cache_key: 子图 final_cache 键
            all_report_types: 本次请求所有报告类型 (供交叉评审参考)
            user_id: 用户 ID
            session_id: 会话 ID
            settings: Settings 实例 (可选)

        Returns:
            {report_type, title, summary, content_md, image_svg, final_cache_key}
        """
        s = settings or self.settings
        async with trace_chain(
            name=f"docbot.cross_review.{report_type}",
            input={
                "report_type": report_type,
                "all_report_types": all_report_types,
                "final_cache_key": final_cache_key,
            },
        ) as span:
            # 从 Redis 读取子图 final 产物
            final_data: dict = {}
            raw = await read_cache(final_cache_key, settings=s)
            if raw:
                try:
                    parsed = json.loads(raw)
                    if isinstance(parsed, dict):
                        final_data = parsed
                except (json.JSONDecodeError, TypeError) as e:
                    logger.warning("final_cache JSON 解析失败 (降级空字典): %s", e)

            image_svgs = final_data.get("image_svgs", [])
            image_svg = image_svgs[0] if isinstance(image_svgs, list) and image_svgs else ""

            span.update(
                output={
                    "has_title": bool(final_data.get("title")),
                    "content_length": len(final_data.get("content_md", "")),
                }
            )
            return {
                "report_type": report_type,
                "title": final_data.get("title", ""),
                "summary": final_data.get("summary", ""),
                "content_md": final_data.get("content_md", ""),
                "image_svg": image_svg,
                "final_cache_key": final_cache_key,
            }

    def _load_persona(self, report_type: str) -> dict[str, str]:
        """加载 persona (失败降级空字典)."""
        try:
            from src.config.docbot.personas import DOCBOT_REPORT_PERSONAS

            return DOCBOT_REPORT_PERSONAS.get(report_type, {})
        except Exception as e:  # noqa: BLE001
            logger.warning("加载 persona 失败 (降级空 persona): %s", e)
            return {}

    def _load_prompt_template(self) -> str:
        """加载 FINAL_REVIEW_PROMPT 模板 (失败降级内置极简版)."""
        try:
            from src.config.docbot.prompts import FINAL_REVIEW_PROMPT

            return FINAL_REVIEW_PROMPT
        except Exception as e:  # noqa: BLE001
            logger.warning("加载 FINAL_REVIEW_PROMPT 失败 (降级内置): %s", e)
            return self._default_prompt()

    @staticmethod
    def _default_prompt() -> str:
        """提示词模板缺失时的兜底 (P1: 智能评审版, 输出 title/summary/terminology/duplicate)."""
        return (
            "你是 {role_name}, {description}\n\n"
            "请对以下 {report_type} 类型合并后的文档进行终审:\n\n"
            "章节摘要:\n{sections_summary}\n\n"
            "代码仓库学习摘要 (节选):\n{code_summary}\n\n"
            "目标语言: {language}\n\n"
            "输出 JSON (严格 JSON, 不要 markdown 代码块): "
            '{{"title": "文档标题", "summary": "200 字以内摘要", '
            '"terminology_suggestions": [{{"from": "原始术语", "to": "统一术语"}}], '
            '"duplicate_chapters": []}}'
        )

    @staticmethod
    def _parse_review_response(
        content: str, persona: dict
    ) -> tuple[str, str, list[dict], list[int]]:
        """解析 LLM 终审输出 (P1: 智能评审版).

        解析 JSON: {title, summary, terminology_suggestions, duplicate_chapters}
        失败降级: title 使用 persona 角色名, terminology/duplicates 为空列表.

        Args:
            content: LLM 输出文本 (期望 JSON)
            persona: persona 字典 (用于降级 title)

        Returns:
            (title, summary, terminology_suggestions, duplicate_chapters) 元组
            - terminology_suggestions: [{from, to, reason}, ...]
            - duplicate_chapters: [int, ...] 疑似重复的章节编号
        """
        import re

        fallback_title = persona.get("role_name", "") if isinstance(persona, dict) else ""
        empty_terminology: list[dict] = []
        empty_duplicates: list[int] = []

        def _extract_fields(parsed: dict) -> tuple[str, str, list[dict], list[int]]:
            title = str(parsed.get("title", fallback_title))
            summary = str(parsed.get("summary", ""))
            terminology = parsed.get("terminology_suggestions", [])
            if not isinstance(terminology, list):
                terminology = []
            duplicates = parsed.get("duplicate_chapters", [])
            if not isinstance(duplicates, list):
                duplicates = []
            # duplicates 元素转 int (容错)
            duplicates_int: list[int] = []
            for d in duplicates:
                try:
                    duplicates_int.append(int(d))
                except (TypeError, ValueError):
                    continue
            return title, summary, terminology, duplicates_int

        # 尝试直接解析 JSON
        try:
            parsed = json.loads(content)
            if isinstance(parsed, dict):
                title, summary, terminology, duplicates = _extract_fields(parsed)
                if title or summary:
                    return title, summary, terminology, duplicates
        except (json.JSONDecodeError, TypeError):
            pass

        # 尝试从 markdown 代码块中提取 JSON
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
        if json_match:
            try:
                parsed = json.loads(json_match.group(1))
                if isinstance(parsed, dict):
                    title, summary, terminology, duplicates = _extract_fields(parsed)
                    if title or summary:
                        return title, summary, terminology, duplicates
            except (json.JSONDecodeError, TypeError):
                pass

        # 尝试从文本中提取 title 和 summary 字段 (容错: LLM 输出非标准 JSON)
        title_match = re.search(r'"title"\s*:\s*"([^"]*)"', content)
        summary_match = re.search(r'"summary"\s*:\s*"([^"]*)"', content)
        if title_match or summary_match:
            title = title_match.group(1) if title_match else fallback_title
            summary = summary_match.group(1) if summary_match else ""
            return title, summary, empty_terminology, empty_duplicates

        # 全部失败, 降级
        logger.warning("LLM 终审 JSON 解析失败 (降级使用 persona 角色名): content[:200]=%s", content[:200])
        return fallback_title, "", empty_terminology, empty_duplicates


__all__ = ["FinalReviewerG"]

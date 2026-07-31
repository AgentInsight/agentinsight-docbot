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
import re
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
        *,
        default_outline: list[dict] | None = None,
        agents_md: str = "",
        readme_md: str = "",
    ) -> dict:
        """细化纲要 (供节点函数直接调用).

        P0-1 增强: 接受外部传入的 default_outline / agents_md / readme_md,
        作为 STRATEGIC LLM 优化纲要的 ground truth (产品定位 / 项目规范).

        Args:
            code_learning: 任务一代码学习摘要 (dict 或 cache_key 字符串)
            report_type: 报告类型 (8 种之一)
            language: 输出语言 (zh|en)
            llm_session_id: LLM 会话 ID
            settings: Settings 实例 (可选)
            default_outline: 外部传入的默认大纲 (节点函数已加载, 避免重复加载);
                             为 None 时内部加载
            agents_md: 目标仓库 AGENTS.md 内容 (项目规范 ground truth)
            readme_md: 目标仓库 README.md 内容 (产品定位 ground truth)

        Returns:
            {"chapters": [{idx, title, sections, key_points, source, refine_reason}],
             "refine_summary": str}
        """
        async with trace_chain(
            name=f"docbot.outline_refine.{report_type}",
            input={"report_type": report_type, "language": language},
        ) as span:
            # 1. 默认大纲: 优先用外部传入, 否则内部加载
            if default_outline is None:
                try:
                    from src.config.docbot.outlines import load_outline

                    default_outline = load_outline(report_type)
                except Exception as e:  # noqa: BLE001
                    logger.warning("加载默认大纲失败 (降级空大纲): %s", e)
                    default_outline = []
            if not isinstance(default_outline, list):
                default_outline = []

            # 2. 加载 max_chapters (从 outline meta)
            max_chapters = 30  # 兜底默认值
            try:
                from src.config.docbot.outlines import load_outline_meta

                meta = load_outline_meta(report_type)
                max_chapters = int(meta.get("max_chapters", 30))
            except Exception as e:  # noqa: BLE001
                logger.warning("加载 max_chapters 失败 (降级 30): %s", e)

            # 3. 加载 persona (从 config.docbot.personas)
            persona: dict[str, str] = {}
            try:
                from src.config.docbot.personas import DOCBOT_REPORT_PERSONAS

                persona = DOCBOT_REPORT_PERSONAS.get(report_type, {})
            except Exception as e:  # noqa: BLE001
                logger.warning("加载 persona 失败 (降级空 persona): %s", e)

            # 4. 加载提示词模板 (从 config.docbot.prompts)
            prompt_template: str = ""
            try:
                from src.config.docbot.prompts import OUTLINE_REFINE_PROMPT

                prompt_template = OUTLINE_REFINE_PROMPT
            except Exception as e:  # noqa: BLE001
                logger.warning("加载 OUTLINE_REFINE_PROMPT 失败: %s", e)
                prompt_template = self._default_prompt()

            # 5. 提取代码学习摘要文本 (兼容 dict / str)
            code_summary = self._extract_summary(code_learning)

            # v9-P1-F: 两阶段大纲生成 (借鉴 STORM 两阶段 outline)
            # 阶段 1: 从代码学习结果构造骨架大纲 (非 LLM, 避免通用示例污染)
            # 阶段 2: STRATEGIC LLM 在骨架大纲基础上精炼 (删除不必要章节, 增加必要章节)
            # 用户补充要求 #1: 使用 STRATEGIC_LLM 对纲要进行优化, 删除不必要的章节以及增加必要的章节
            skeleton_outline = self._build_skeleton_outline(
                code_learning=code_learning if isinstance(code_learning, dict) else {},
                report_type=report_type,
                default_outline=default_outline,
            )
            if skeleton_outline:
                # 用骨架大纲替代默认大纲作为 LLM 精炼的起点
                # 这样 LLM 看到的是基于代码的骨架, 而非通用模板, 减少通用示例污染
                default_outline = skeleton_outline
                logger.info(
                    "v9-P1-F: 使用骨架大纲 (基于代码学习结果) 作为 LLM 精炼起点, "
                    "骨架章节=%d (report_type=%s)",
                    len(skeleton_outline),
                    report_type,
                )
                span.update(metadata={"v9_p1_f_skeleton_chapters": len(skeleton_outline)})

            # 6. 构造 prompt (P0-1: 注入 agents_md / readme_md / max_chapters 作为 ground truth)
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
                agents_md=agents_md[:50_000] if agents_md else "(未提供 AGENTS.md)",
                readme_md=readme_md[:30_000] if readme_md else "(未提供 README.md)",
                max_chapters=max_chapters,
                # v8 新增 kwargs (从 code_learning 字典提取, 失败降级为空字符串)
                endpoints_text=self._safe_get_str(code_learning, "endpoints_text"),
                enums_text=self._safe_get_str(code_learning, "enums_text"),
                project_metadata_text=self._safe_get_str(
                    code_learning, "project_metadata_text"
                ),
                glossary_text=self._safe_get_str(code_learning, "glossary_text"),
                scopes_text=self._safe_get_str(code_learning, "scopes_text"),
                config_specs_text=self._safe_get_str(code_learning, "config_specs_text"),
            )

            # v6-P0-E: 注入文档结构通用引导, 让 LLM 基于代码学习结果优化纲要结构
            # 使用标准编号体系 (FR/NFR/IR/DR/C/BR) + 表格化呈现, 但不硬编码特定项目内容
            try:
                from src.config.docbot.prompts import (
                    API_DOC_STRUCTURE_GUIDE,
                    PRD_STRUCTURE_GUIDE,
                )

                if report_type == "requirements":
                    structure_guide = PRD_STRUCTURE_GUIDE
                elif report_type == "api_doc":
                    structure_guide = API_DOC_STRUCTURE_GUIDE
                else:
                    structure_guide = ""

                if structure_guide:
                    prompt += (
                        "\n\n# v6-P0-E 文档结构优化引导\n"
                        "在优化大纲时, 请遵循以下通用原则, "
                        "但章节内容和分组必须基于代码学习结果 (code_summary / key_modules / AGENTS.md) 动态推导, "
                        "禁止套用任何预设的业务域分组:\n\n"
                        f"{structure_guide}"
                    )
            except Exception as e:  # noqa: BLE001
                logger.warning("v6-P0-E: 注入结构引导失败 (降级默认): %s", e)

            # 7. STRATEGIC LLM 细化纲要 (v7-P0-A: 增大 max_tokens 防截断)
            messages = [{"role": "user", "content": prompt}]
            response = await self.llm.achat(
                messages,
                tier=LLMTier.STRATEGIC,
                session_id=llm_session_id,
                span_name=f"docbot.outline_refine.{report_type}",
                step="outline_refine",
                max_tokens=8192,  # v7-P0-A: 增大 max_tokens 防止 JSON 截断
            )

            # 8. 解析 JSON 输出 (失败降级使用默认大纲)
            outline = self._parse_outline(response.content, default_outline)

            # v7-P1-G: 解析失败时, 用更大 max_tokens 重试一次
            if outline.get("_fallback"):
                logger.warning(
                    "v7-P1-G: 大纲解析失败 (fallback=True), 用 max_tokens=12288 重试一次"
                )
                try:
                    retry_response = await self.llm.achat(
                        messages,
                        tier=LLMTier.STRATEGIC,
                        session_id=llm_session_id,
                        span_name=f"docbot.outline_refine.{report_type}.retry",
                        step="outline_refine_retry",
                        max_tokens=12288,  # 进一步增大, 确保完整输出
                    )
                    outline = self._parse_outline(retry_response.content, default_outline)
                    if not outline.get("_fallback"):
                        logger.info(
                            "v7-P1-G: 重试成功, 使用 %d 个章节",
                            len(outline.get("chapters", [])),
                        )
                except Exception as e:  # noqa: BLE001
                    logger.warning("v7-P1-G: 重试调用 LLM 失败 (降级默认大纲): %s", e)

            # v12: 校验纲要确有增删改 (禁止原样输出默认 YAML)
            outline = self._validate_outline_mutations(
                outline=outline,
                baseline_outline=default_outline,
                code_learning=code_learning if isinstance(code_learning, dict) else {},
                report_type=report_type,
            )

            span.update(
                output={
                    "chapter_count": len(outline.get("chapters", [])),
                    "fallback": outline.get("_fallback", False),
                    "has_agents_md": bool(agents_md),
                    "has_readme_md": bool(readme_md),
                    "outline_sources": outline.get("_source_counts"),
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
    def _build_skeleton_outline(
        code_learning: dict,
        report_type: str,
        default_outline: list[dict],
    ) -> list[dict]:
        """v9-P1-F: 从代码学习结果构造骨架大纲 (非 LLM, 避免通用示例污染).

        借鉴 STORM 两阶段 outline: 先构造骨架, 再由 LLM 精炼.
        骨架大纲基于 code_learning 的 endpoints / enums / key_modules 直接构造章节,
        避免默认大纲中的通用示例 (如 /users, /orders, OAuth2 等) 污染 LLM 输出.

        设计原则 (禁止硬编码特定仓库/产品名):
        - 章节标题和 key_points 不含任何项目特定硬编码
        - 章节内容完全从 code_learning 动态推导
        - 仅构造骨架结构, 具体内容由 LLM 精炼

        Args:
            code_learning: 任务一代码学习摘要 (含 http_endpoints / enum_definitions / key_modules)
            report_type: 报告类型 (api_doc / requirements / 等)
            default_outline: 默认大纲 (兜底, 当 code_learning 无可用数据时使用)

        Returns:
            骨架大纲章节列表, 每章含 {idx, title, sections, key_points, source, refine_reason}.
            若 code_learning 无可用数据, 返回空列表 (由调用方降级到 default_outline).
        """
        if not isinstance(code_learning, dict) or not code_learning:
            return []

        # 从 code_learning 提取关键数据
        endpoints = code_learning.get("http_endpoints", [])
        if not isinstance(endpoints, list):
            endpoints = []
        key_modules = code_learning.get("key_modules", [])
        if not isinstance(key_modules, list):
            key_modules = []
        dependencies = code_learning.get("dependencies", [])
        if not isinstance(dependencies, list):
            dependencies = []

        # 若无 endpoints 且无 key_modules, 无法构造骨架, 降级到默认大纲
        if not endpoints and not key_modules:
            return []

        skeleton: list[dict] = []

        if report_type == "api_doc" and endpoints:
            # API 文档骨架大纲 (基于 HTTP 端点构造)
            # 1. 引言 (保留通用结构)
            skeleton.append({
                "idx": 1,
                "title": "引言",
                "sections": ["编写目的", "适用范围", "术语与缩略语", "参考文档", "版本历史"],
                "key_points": ["基于代码学习结果生成, 产品定位从 project_metadata 推导"],
                "source": "skeleton",
                "refine_reason": "v9 骨架大纲: 基于 code_learning 构造",
            })

            # 2. API 概览 (从 endpoints 提取分类)
            # v10-P0-1: 按 class_name 字段分组 (修复字段名错误, ast_search 返回 class_name 而非 controller)
            controllers: set[str] = set()
            for ep in endpoints:
                if isinstance(ep, dict):
                    ctrl = ep.get("class_name", "") or ep.get("controller", "") or ep.get("controller_class", "") or "Unknown"
                    controllers.add(str(ctrl))

            skeleton.append({
                "idx": 2,
                "title": "API 概览",
                "sections": ["基础信息", "API 分类", "API 清单"],
                "key_points": [
                    f"基础信息 (Base URL / 数据格式 / 时间格式, 从 code_learning 推导)",
                    f"API 分类 (按 Controller 模块分组, 共 {len(controllers)} 个分组)",
                    f"API 清单 (覆盖全部 {len(endpoints)} 个 HTTP 端点, 必须与 endpoints_text 完全对齐)",
                ],
                "source": "skeleton",
                "refine_reason": f"v9 骨架大纲: 基于 {len(endpoints)} 个 HTTP 端点",
            })

            # 3. 认证授权 (从代码学习结果推导, 不预设具体方式)
            skeleton.append({
                "idx": 3,
                "title": "认证授权",
                "sections": ["认证机制", "授权流程", "Token 管理"],
                "key_points": ["认证方式从 code_learning 推导, 禁止照搬默认 OAuth2/mTLS"],
                "source": "skeleton",
                "refine_reason": "v9 骨架大纲: 认证方式从代码提取",
            })

            # 4-N. 接口详情 (按 Controller 分组, 每组一章)
            sorted_controllers = sorted(controllers)
            for i, controller in enumerate(sorted_controllers, start=4):
                # v10-P0-1: 使用 class_name 字段过滤端点 (修复字段名错误)
                controller_endpoints = [
                    ep for ep in endpoints
                    if isinstance(ep, dict)
                    and (ep.get("class_name", "") or ep.get("controller", "") or ep.get("controller_class", "") or "Unknown") == controller
                ]
                # 构造每个端点的 section 标题
                sections: list[str] = []
                for ep in controller_endpoints:
                    # v10-P0-1: 字段名对齐 ast_search 返回 (http_method / route / summary)
                    method = ep.get("http_method", "") or ep.get("method", "") or ""
                    route = ep.get("route", "") or ep.get("path", "") or ""
                    summary_text = ep.get("summary", "") or ep.get("description", "") or ""
                    if method and route:
                        sections.append(f"{method} {route}" + (f" - {summary_text}" if summary_text else ""))
                    elif route:
                        sections.append(route)

                skeleton.append({
                    "idx": i,
                    "title": f"{controller} 接口",
                    # v14: 保留 Controller 类名供内容填充过滤 (LLM 改中文标题后仍可匹配)
                    "controller_name": controller,
                    "sections": sections or [f"{controller} 端点详情"],
                    "key_points": [
                        f"覆盖 {len(controller_endpoints)} 个端点, 每端点一个接口卡片",
                        "每个接口含: 接口名 + HTTP 方法 + 路径 + 描述 + 鉴权方式 + 请求参数 + 响应格式 + 错误码 + 请求示例 + 响应示例",
                        f"本章仅描述 {controller} 的端点, 标题须保留 Controller 英文类名",
                    ],
                    "source": "skeleton",
                    "refine_reason": f"v9 骨架大纲: {controller} 共 {len(controller_endpoints)} 个端点",
                })

            # 末章: 错误码与通用约定
            last_idx = len(skeleton) + 1
            skeleton.append({
                "idx": last_idx,
                "title": "错误码与通用约定",
                "sections": ["错误码清单", "通用响应结构", "版本治理", "附录"],
                "key_points": [
                    "错误码必须从 enums_text 提取, 禁止编造",
                    "通用响应结构从代码 ApiResponse<T> 类提取真实字段",
                ],
                "source": "skeleton",
                "refine_reason": "v9 骨架大纲: 错误码与通用约定",
            })

        elif report_type == "requirements" and endpoints:
            # PRD 需求文档骨架大纲 (基于 HTTP 端点推导 FR 目标数量)
            fr_count = min(50, len(endpoints))  # FR 目标数量 30-50, 上限 50

            skeleton.append({
                "idx": 1,
                "title": "引言",
                "sections": ["编写目的与目标读者", "产品背景与业务痛点", "文档范围", "术语与缩略语", "参考文档", "版本历史"],
                "key_points": ["基于代码学习结果生成, 产品定位从 project_metadata 推导"],
                "source": "skeleton",
                "refine_reason": "v9 骨架大纲: 基于 code_learning 构造",
            })

            skeleton.append({
                "idx": 2,
                "title": "产品概述与用户分析",
                "sections": ["产品定位", "价值主张", "北极星指标", "Persona 矩阵", "用户旅程"],
                "key_points": ["产品定位必须来自 project_metadata_text + code_summary"],
                "source": "skeleton",
                "refine_reason": "v9 骨架大纲: 产品定位从代码推导",
            })

            # 功能需求章节: 每个端点对应一个 FR
            fr_sections: list[str] = []
            for i, ep in enumerate(endpoints[:fr_count]):
                if isinstance(ep, dict):
                    summary_text = ep.get("summary", "") or ep.get("description", "") or ""
                    route = ep.get("route", "") or ep.get("path", "") or ""
                    title_text = summary_text or route or f"FR-{i+1:03d}"
                    fr_sections.append(f"FR-{i+1:03d} {title_text}")

            skeleton.append({
                "idx": 3,
                "title": "功能需求",
                "sections": fr_sections or [f"FR-{i+1:03d}" for i in range(fr_count)],
                "key_points": [
                    f"FR 目标数量 {fr_count} 个, 每个端点对应一个独立 FR",
                    "FR 编号使用 FR-001/FR-002 连续 3 位数字格式",
                    "每个 FR 含用户故事 + 主流程 + 验收标准 + 业务规则",
                    "验收标准含具体 errorCode (从 enums_text 提取), 禁止编造",
                ],
                "source": "skeleton",
                "refine_reason": f"v9 骨架大纲: 基于 {len(endpoints)} 个 HTTP 端点推导 {fr_count} 个 FR",
            })

            skeleton.append({
                "idx": 4,
                "title": "非功能需求",
                "sections": ["性能", "可用性", "安全", "可扩展性", "可维护性", "兼容性", "本地化"],
                "key_points": [
                    "NFR 编号 NFR-{CATEGORY}-NNN 格式 (P/A/S/SC/M/AC/C/L 8 个子类)",
                    "目标 15-30 条 NFR, 每个含编号+指标+目标值(含具体数值)+验证方式",
                    "NFR 必须用表格呈现, 禁止散文描述",
                ],
                "source": "skeleton",
                "refine_reason": "v9 骨架大纲: NFR 标准 8 子类",
            })

            skeleton.append({
                "idx": 5,
                "title": "接口需求",
                "sections": ["内部接口", "外部接口"],
                "key_points": ["从 code_learning 的 dependencies 提取接口依赖"],
                "source": "skeleton",
                "refine_reason": "v9 骨架大纲: 接口需求从 dependencies 推导",
            })

            skeleton.append({
                "idx": 6,
                "title": "数据需求",
                "sections": ["数据模型", "数据存储", "数据流"],
                "key_points": ["从 code_learning 的 key_modules 提取数据模型"],
                "source": "skeleton",
                "refine_reason": "v9 骨架大纲: 数据需求从 key_modules 推导",
            })

            skeleton.append({
                "idx": 7,
                "title": "约束条件",
                "sections": ["技术约束", "业务约束", "合规约束"],
                "key_points": ["从 AGENTS.md + code_summary 提取约束"],
                "source": "skeleton",
                "refine_reason": "v9 骨架大纲: 约束条件从 AGENTS.md 推导",
            })

            skeleton.append({
                "idx": 8,
                "title": "需求追踪矩阵",
                "sections": ["FR 追踪", "NFR 追踪"],
                "key_points": ["FR/NFR 与代码 Controller/Handler 对应关系"],
                "source": "skeleton",
                "refine_reason": "v9 骨架大纲: 需求追踪矩阵",
            })

        else:
            # 其他类型报告: 无法构造骨架, 返回空列表 (由调用方降级到 default_outline)
            return []

        return skeleton

    @staticmethod
    def _validate_outline_mutations(
        outline: dict,
        baseline_outline: list[dict],
        code_learning: dict,
        report_type: str,
    ) -> dict:
        """v12: 校验 STRATEGIC 纲要确有增删改, 禁止原样输出默认 YAML.

        - 统计 source=added/removed/refined/default
        - 若几乎无变更且 baseline 非骨架 (无 source=skeleton), 用骨架强制替换
        - api_doc: 若有 http_endpoints 但章节未覆盖 Controller, 合并骨架 Controller 章
        """
        if not isinstance(outline, dict):
            return outline
        chapters = outline.get("chapters") or []
        if not isinstance(chapters, list):
            chapters = []

        source_counts: dict[str, int] = {
            "added": 0,
            "removed": 0,
            "refined": 0,
            "default": 0,
            "skeleton": 0,
            "other": 0,
        }
        for ch in chapters:
            if not isinstance(ch, dict):
                continue
            src = str(ch.get("source") or "other").lower()
            if src in source_counts:
                source_counts[src] += 1
            else:
                source_counts["other"] += 1

        mutations = (
            source_counts["added"]
            + source_counts["removed"]
            + source_counts["refined"]
            + source_counts["skeleton"]
        )
        outline["_source_counts"] = source_counts

        # 标题集合对比: 与 baseline 完全一致 → 视为未优化
        baseline_titles = {
            str(c.get("title", "")).strip().lower()
            for c in (baseline_outline or [])
            if isinstance(c, dict)
        }
        result_titles = {
            str(c.get("title", "")).strip().lower()
            for c in chapters
            if isinstance(c, dict)
        }
        identical_titles = bool(baseline_titles) and baseline_titles == result_titles

        endpoints = code_learning.get("http_endpoints") or []
        if not isinstance(endpoints, list):
            endpoints = []

        if mutations == 0 and identical_titles and endpoints:
            logger.warning(
                "v12: 纲要未发生增删改且标题与基线完全一致 (report_type=%s), "
                "强制用代码骨架重建章节",
                report_type,
            )
            skeleton = OutlineRefinerC._build_skeleton_outline(
                code_learning=code_learning,
                report_type=report_type,
                default_outline=baseline_outline or [],
            )
            if skeleton:
                outline = {
                    "chapters": skeleton,
                    "refine_summary": (
                        "v12 强制骨架: LLM 未对默认纲要做实质性增删改, "
                        "改用 AST/代码学习骨架"
                    ),
                    "_source_counts": {"skeleton": len(skeleton)},
                }
                return outline

        # api_doc: 确保每个 Controller 至少有一章
        if report_type == "api_doc" and endpoints:
            controllers = {
                str(ep.get("class_name") or ep.get("controller") or "")
                for ep in endpoints
                if isinstance(ep, dict)
            }
            controllers.discard("")
            covered = set()
            for ch in chapters:
                if not isinstance(ch, dict):
                    continue
                title = str(ch.get("title") or "").lower()
                for ctrl in controllers:
                    base = ctrl.replace("Controller", "").lower()
                    if ctrl.lower() in title or (base and base in title):
                        covered.add(ctrl)
            missing = controllers - covered
            if missing and len(missing) >= max(1, len(controllers) // 3):
                logger.warning(
                    "v12: api_doc 纲要缺失 %d/%d 个 Controller 章节, 追加骨架章",
                    len(missing),
                    len(controllers),
                )
                skeleton = OutlineRefinerC._build_skeleton_outline(
                    code_learning=code_learning,
                    report_type=report_type,
                    default_outline=baseline_outline or [],
                )
                # 仅追加缺失 Controller 对应的骨架章
                existing_titles = {
                    str(c.get("title") or "").lower()
                    for c in chapters
                    if isinstance(c, dict)
                }
                next_idx = max(
                    (int(c.get("idx") or 0) for c in chapters if isinstance(c, dict)),
                    default=0,
                ) + 1
                for sk in skeleton:
                    if not isinstance(sk, dict):
                        continue
                    t = str(sk.get("title") or "").lower()
                    if t in existing_titles:
                        continue
                    if any(
                        ctrl.lower() in t
                        or ctrl.replace("Controller", "").lower() in t
                        for ctrl in missing
                    ):
                        sk = dict(sk)
                        sk["idx"] = next_idx
                        sk["source"] = "added"
                        sk["refine_reason"] = "v12 补全缺失 Controller 章节"
                        chapters.append(sk)
                        next_idx += 1
                outline["chapters"] = chapters
                source_counts["added"] = source_counts.get("added", 0) + len(missing)
                outline["_source_counts"] = source_counts

        # v14: 回填 controller_name + 按 Controller 去重 (避免中英重复章挤掉真实 Controller)
        if report_type == "api_doc" and endpoints:
            chapters = OutlineRefinerC._dedupe_controller_chapters(
                list(outline.get("chapters") or chapters),
                endpoints,
            )
            outline["chapters"] = chapters

        logger.info(
            "v12: 纲要变更统计 report_type=%s added=%d removed=%d refined=%d "
            "default=%d skeleton=%d identical_titles=%s",
            report_type,
            source_counts["added"],
            source_counts["removed"],
            source_counts["refined"],
            source_counts["default"],
            source_counts["skeleton"],
            identical_titles,
        )

        # 硬上限: 与 Settings.max_chapters_per_report / outline meta 对齐 (默认 20)
        max_ch = 20
        try:
            from src.config.docbot.outlines import load_outline_meta

            meta = load_outline_meta(report_type)
            max_ch = int(meta.get("max_chapters", 20))
        except Exception:  # noqa: BLE001
            max_ch = 20
        chapters = outline.get("chapters") or []
        if isinstance(chapters, list) and len(chapters) > max_ch:
            # v14: 截断时优先保留带 controller_name 的接口章 + 前言/认证/错误码
            chapters = OutlineRefinerC._prioritize_chapters_for_truncation(
                chapters, max_ch
            )
            logger.warning(
                "v12: 纲要章节数超过上限 %d, 截断后 %d (report_type=%s)",
                max_ch,
                len(chapters),
                report_type,
            )
            outline["chapters"] = chapters

        return outline

    @staticmethod
    def _dedupe_controller_chapters(
        chapters: list,
        endpoints: list,
    ) -> list:
        """v14: 为章节回填 controller_name, 并去掉同一 Controller 的重复章."""
        controllers = sorted(
            {
                str(ep.get("class_name") or ep.get("controller") or "")
                for ep in endpoints
                if isinstance(ep, dict)
            }
        )
        controllers = [c for c in controllers if c]

        def _match_ctrl(title: str, reason: str) -> str:
            blob = f"{title} {reason}".lower()
            blob_compact = re.sub(r"[\s_\-]+", "", blob)
            best = ""
            for ctrl in controllers:
                base = ctrl.replace("Controller", "")
                if ctrl.lower() in blob or base.lower() in blob:
                    if len(ctrl) > len(best):
                        best = ctrl
                    continue
                if re.sub(r"[\s_\-]+", "", base.lower()) in blob_compact:
                    if len(ctrl) > len(best):
                        best = ctrl
            return best

        result: list = []
        seen_ctrl: set[str] = set()
        for ch in chapters:
            if not isinstance(ch, dict):
                continue
            ch = dict(ch)
            title = str(ch.get("title") or "")
            reason = str(ch.get("refine_reason") or "")
            ctrl = str(ch.get("controller_name") or "") or _match_ctrl(title, reason)
            if ctrl:
                ch["controller_name"] = ctrl
                # 若标题已无英文 Controller 名, 恢复为「{Controller} 接口」便于过滤匹配
                if ctrl.lower() not in title.lower():
                    ch["title"] = f"{ctrl} 接口"
                if ctrl in seen_ctrl:
                    # 重复 Controller 章丢弃 (保留先出现的)
                    continue
                seen_ctrl.add(ctrl)
            result.append(ch)

        # 补全仍缺失的 Controller
        next_idx = max((int(c.get("idx") or 0) for c in result if isinstance(c, dict)), default=0) + 1
        for ctrl in controllers:
            if ctrl in seen_ctrl:
                continue
            result.append({
                "idx": next_idx,
                "title": f"{ctrl} 接口",
                "controller_name": ctrl,
                "sections": [f"{ctrl} 端点详情"],
                "key_points": [f"覆盖 {ctrl} 全部端点"],
                "source": "added",
                "refine_reason": f"v14 补全缺失 Controller: {ctrl}",
            })
            next_idx += 1
            seen_ctrl.add(ctrl)
        # 重编号
        for i, ch in enumerate(result, start=1):
            if isinstance(ch, dict):
                ch["idx"] = i
        return result

    @staticmethod
    def _prioritize_chapters_for_truncation(chapters: list, max_ch: int) -> list:
        """截断时优先保留前言类 + 带 controller_name 的接口章."""
        if len(chapters) <= max_ch:
            return chapters
        keep_kw = ("引言", "概览", "概述", "认证", "授权", "错误", "约定", "附录")
        head: list = []
        ctrl_chs: list = []
        other: list = []
        for ch in chapters:
            if not isinstance(ch, dict):
                continue
            title = str(ch.get("title") or "")
            if any(k in title for k in keep_kw) and not ch.get("controller_name"):
                head.append(ch)
            elif ch.get("controller_name"):
                ctrl_chs.append(ch)
            else:
                other.append(ch)
        # 预留 head, 剩余名额给 Controller
        head = head[: max(3, max_ch // 5)]
        remain = max_ch - len(head)
        selected = head + ctrl_chs[:remain]
        if len(selected) < max_ch:
            selected.extend(other[: max_ch - len(selected)])
        for i, ch in enumerate(selected, start=1):
            ch["idx"] = i
        return selected

    @staticmethod
    def _safe_get_str(code_learning: dict | str, key: str, default: str = "") -> str:
        """v8: 安全从 code_learning 字典提取字符串字段, 失败返回默认值.

        Args:
            code_learning: 任务一代码学习摘要 (dict 或 cache_key 字符串)
            key: 字段名 (如 endpoints_text, enums_text)
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
        """解析 LLM 输出的 JSON 纲要, 失败降级使用默认大纲.

        O4-P0-D: 三层降级解析策略, 应对 STRATEGIC LLM 输出不稳定的 JSON:
        1. 直接 json.loads
        2. 提取 ```json ... ``` 代码块
        3. 修复常见 JSON 错误 (markdown 前缀/截断/中文标点) 后重试

        v7-P0-A: 扩展为 5 层降级策略:
        4. 流式截断修复 (处理 Unterminated string, 保留最后一个完整 chapter)
        5. 单引号转双引号 + 控制字符清理 + 尾随逗号修复
        失败时记录完整响应到 /tmp, 便于调试.
        """
        import re
        import time

        if not content or not content.strip():
            logger.warning("LLM 纲要响应为空 (降级默认大纲)")
            return {"chapters": default_outline, "_fallback": True}

        # 策略 1: 直接解析
        try:
            outline = json.loads(content)
            if isinstance(outline, dict) and "chapters" in outline:
                chapters = outline["chapters"]
                if isinstance(chapters, list) and chapters:
                    return {"chapters": chapters}
        except (json.JSONDecodeError, TypeError):
            pass

        # 策略 2: 提取 ```json ... ``` 代码块
        json_block_match = re.search(r'```(?:json)?\s*(.*?)\s*```', content, re.DOTALL)
        if json_block_match:
            try:
                outline = json.loads(json_block_match.group(1))
                if isinstance(outline, dict) and "chapters" in outline:
                    chapters = outline["chapters"]
                    if isinstance(chapters, list) and chapters:
                        logger.info("O4-P0-D: 策略 2 (代码块提取) 解析成功")
                        return {"chapters": chapters}
            except (json.JSONDecodeError, TypeError):
                pass

        # 策略 3: 修复常见 JSON 错误后重试
        fixed = content.strip()
        # 3a: 移除 markdown 前后缀 (```json 或 ```)
        fixed = re.sub(r'^```(?:json)?\s*', '', fixed)
        fixed = re.sub(r'\s*```$', '', fixed)
        # 3b: 修复中文标点 (全角引号/冒号)
        fixed = fixed.replace('\u201c', '"').replace('\u201d', '"')
        fixed = fixed.replace('\u2018', "'").replace('\u2019', "'")
        fixed = fixed.replace('\uff1a', ':').replace('\uff0c', ',')
        # 3c: 修复截断 (补全未闭合的括号)
        open_braces = fixed.count("{") - fixed.count("}")
        open_brackets = fixed.count("[") - fixed.count("]")
        if open_braces > 0 or open_brackets > 0:
            fixed = fixed + ("]" * max(open_brackets, 0)) + ("}" * max(open_braces, 0))
        # 3d: 提取首个 { 到最后一个 } 之间的内容 (去除前后说明文字)
        first_brace = fixed.find("{")
        last_brace = fixed.rfind("}")
        if first_brace >= 0 and last_brace > first_brace:
            fixed = fixed[first_brace : last_brace + 1]

        try:
            outline = json.loads(fixed)
            if isinstance(outline, dict) and "chapters" in outline:
                chapters = outline["chapters"]
                if isinstance(chapters, list) and chapters:
                    logger.info("O4-P0-D: 策略 3 (修复后) 解析成功")
                    return {"chapters": chapters}
        except (json.JSONDecodeError, TypeError):
            pass

        # v7-P0-A 策略 4: 流式截断修复 (处理 "Unterminated string" 错误)
        # 当 LLM 输出被 max_tokens 截断时, 字符串可能未闭合
        # 检测最后一个完整的 chapter 对象, 丢弃截断的部分对象
        def _repair_truncated_json(text: str) -> str | None:
            """v7-P0-A: 修复截断的 JSON (保留最后一个完整对象)."""
            # 找到最后一个 chapter 对象的关键字段
            last_chapter_end = text.rfind('"refine_reason":')
            if last_chapter_end < 0:
                last_chapter_end = text.rfind('"source":')
            if last_chapter_end < 0:
                last_chapter_end = text.rfind('"key_points":')
            if last_chapter_end < 0:
                return None
            # 从该位置向后找第一个 } (chapter 对象闭合)
            end_brace = text.find('}', last_chapter_end)
            if end_brace < 0:
                return None
            # 截断到该 } 之后, 补全 ] 和 }
            truncated = text[:end_brace + 1]
            # 移除可能的尾部逗号
            truncated = truncated.rstrip().rstrip(',')
            # 补全外层结构和可选的 refine_summary
            result = truncated + '\n  ]\n}'
            return result

        repaired = _repair_truncated_json(fixed)
        if repaired:
            try:
                outline = json.loads(repaired)
                if isinstance(outline, dict) and "chapters" in outline:
                    chapters = outline["chapters"]
                    if isinstance(chapters, list) and chapters:
                        logger.info(
                            "v7-P0-A: 策略 4 (截断修复) 解析成功, 保留 %d 个章节",
                            len(chapters),
                        )
                        return {"chapters": chapters}
            except (json.JSONDecodeError, TypeError) as e:
                logger.debug("v7-P0-A: 策略 4 失败: %s", e)

        # v7-P0-A 策略 5: 单引号转双引号 + 控制字符清理 + 尾随逗号修复
        cleaned = fixed.replace("'", '"')  # 单引号转双引号
        cleaned = re.sub(r'[\x00-\x1f\x7f]', '', cleaned)  # 移除控制字符
        cleaned = re.sub(r',\s*([}\]])', r'\1', cleaned)  # 尾随逗号修复
        # 再次尝试截断修复
        repaired_cleaned = _repair_truncated_json(cleaned) or cleaned
        try:
            outline = json.loads(repaired_cleaned)
            if isinstance(outline, dict) and "chapters" in outline:
                chapters = outline["chapters"]
                if isinstance(chapters, list) and chapters:
                    logger.info("v7-P0-A: 策略 5 (单引号+控制字符) 解析成功")
                    return {"chapters": chapters}
        except (json.JSONDecodeError, TypeError):
            pass

        # v7-P0-A: 全部失败, 记录完整响应到文件, 便于调试
        debug_path = f"/tmp/outline_parse_failed_{int(time.time())}.txt"
        try:
            with open(debug_path, "w", encoding="utf-8") as f:
                f.write(f"content_length: {len(content)}\n")
                f.write(f"content:\n{content}\n")
            logger.warning("v7-P0-A: 完整响应已保存到 %s", debug_path)
        except Exception:  # noqa: BLE001
            pass

        logger.warning(
            "O4-P0-D: JSON 解析五层降级均失败 (降级默认大纲), 原始响应前 200 字: %s",
            content[:200],
        )
        return {"chapters": default_outline, "_fallback": True}


__all__ = ["OutlineRefinerC"]

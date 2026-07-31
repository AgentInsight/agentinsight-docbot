"""按 report_type 的代码学习侧重配置 (数据驱动, 无业务 if-else).

P0 (optimization-plan-code-learning-v1):
- Prompt 只注入当前类型侧重, 禁止 8 种全量清单平均用力
- 扩展 JSON schema 附加字段 (向后兼容公共四字段)
- 禁止硬编码任何特定产品/仓库业务事实
"""

from __future__ import annotations

from typing import Any

# 学习侧重字典: dimensions / must_cover / forbid / extra_json_fields
LEARNING_FOCUS_BY_TYPE: dict[str, dict[str, Any]] = {
    "architecture": {
        "dimensions": ["依赖图", "调用链", "分层模式", "设计模式", "部署拓扑", "数据流"],
        "must_cover": [
            "入口点与分层边界（带 path:line）",
            "模块依赖方向与循环依赖风险",
            "部署/运行时组件（仅来自仓库内 compose/Dockerfile/helm 等证据；无证据写 insufficient_evidence）",
        ],
        "forbid": "禁止输出完整 API 手册、测试用例清单、空泛业务需求叙述。",
        "extra_json_fields": {
            "deployment_topology": "Markdown，无证据则写 insufficient_evidence",
            "data_flows": [
                {"from": "", "to": "", "via": "", "evidence": "path:line"}
            ],
        },
    },
    "design": {
        "dimensions": ["模块划分", "接口契约", "核心流程", "异常处理", "数据模型"],
        "must_cover": [
            "模块边界与职责（带 path:line）",
            "公开接口契约（方法签名/输入输出，须有代码证据）",
            "核心流程与异常路径（指向真实处理代码）",
        ],
        "forbid": "禁止输出部署拓扑长文、完整 API 错误码手册、测试覆盖盲区清单。",
        "extra_json_fields": {
            "interface_contracts": [
                {
                    "name": "",
                    "path": "",
                    "inputs": "",
                    "outputs": "",
                    "evidence": "path:line",
                }
            ],
            "exception_paths": [
                {"trigger": "", "handler": "", "evidence": "path:line"}
            ],
        },
    },
    "requirements": {
        "dimensions": ["功能边界", "用户故事", "验收标准", "业务流程"],
        "must_cover": [
            "从公开入口/API/CLI 反推功能边界（须标 confidence）",
            "可验收候选条件须绑定代码证据；禁止臆造业务动机",
            "Out-of-Scope 须对照 scopes_text / 文件索引",
        ],
        "forbid": "禁止输出部署拓扑长文、性能热点分析、完整 API 字段级手册。",
        "extra_json_fields": {
            "feature_boundaries": [
                {
                    "feature": "",
                    "in_scope": True,
                    "evidence": "path:line",
                    "confidence": "low|medium|high",
                }
            ],
            "acceptance_candidates": [
                {
                    "criterion": "",
                    "evidence": "path:line",
                    "confidence": "low|medium|high",
                }
            ],
        },
    },
    "testcase": {
        "dimensions": ["可测试点", "边界条件", "异常路径", "测试覆盖盲区"],
        "must_cover": [
            "从公开函数/API 列出可测试点（带 path:line）",
            "基于文件索引对比 tests/ 与实现，列出覆盖盲区；不得虚构测试文件",
            "异常路径须指向真实 except/Result/error 处理代码",
        ],
        "forbid": "禁止输出部署拓扑长文、完整 API 手册、空泛架构综述。",
        "extra_json_fields": {
            "test_points": [
                {
                    "target": "",
                    "scenario": "",
                    "boundary": "",
                    "evidence": "path:line",
                }
            ],
            "coverage_gaps": [
                {
                    "area": "",
                    "evidence": "path:line 或 file_index",
                    "confidence": "low|medium|high",
                }
            ],
        },
    },
    "optimization": {
        "dimensions": ["性能瓶颈", "资源消耗", "扩展性限制", "优化机会"],
        "must_cover": [
            "优化机会须绑定代码/配置证据（连接池、缓存、批处理、异步等）",
            "扩展性限制须来自配置规格或架构边界证据",
            "无 profiling 数据时标注 confidence: low，禁止空泛建议",
        ],
        "forbid": "禁止输出用户故事清单、完整 API 手册、测试用例表。",
        "extra_json_fields": {
            "optimization_opportunities": [
                {
                    "area": "",
                    "suggestion": "",
                    "evidence": "path:line",
                    "confidence": "low|medium|high",
                }
            ],
            "scalability_limits": [
                {"limit": "", "evidence": "path:line", "confidence": "low|medium|high"}
            ],
        },
    },
    "performance": {
        "dimensions": ["热点函数", "时间复杂度", "内存分配", "IO 模式"],
        "must_cover": [
            "热点候选须指向真实函数/方法（带 path:line）",
            "复杂度与 IO 模式基于代码结构推断并标注 confidence",
            "无 runtime profiling 时禁止编造耗时数字",
        ],
        "forbid": "禁止输出完整需求文档、API 错误码手册、部署拓扑长文。",
        "extra_json_fields": {
            "hotspots": [
                {
                    "symbol": "",
                    "reason": "",
                    "evidence": "path:line",
                    "confidence": "low|medium|high",
                }
            ],
            "complexity_notes": [{"symbol": "", "note": "", "evidence": "path:line"}],
            "io_patterns": [{"pattern": "", "evidence": "path:line"}],
        },
    },
    "defect": {
        "dimensions": ["异常处理", "错误传播", "资源泄漏", "并发隐患"],
        "must_cover": [
            "缺陷风险须指向真实代码模式（裸 except、未关闭资源、锁/全局可变等）",
            "错误传播路径须有 evidence",
            "无证据的风险标注 confidence: low，禁止臆造漏洞编号",
        ],
        "forbid": "禁止输出产品路线图、完整 API 手册、空泛架构综述。",
        "extra_json_fields": {
            "defect_risks": [
                {
                    "category": "exception|leak|concurrency|other",
                    "description": "",
                    "evidence": "path:line",
                    "confidence": "low|medium|high",
                }
            ],
        },
    },
    "api_doc": {
        "dimensions": ["公开接口", "请求响应模型", "认证授权", "错误码", "版本治理"],
        "must_cover": [
            "公开接口须与 endpoints_text 对齐（方法/路由）",
            "认证授权与错误码须引用 enums_text / 真实中间件代码；无证据写 insufficient_evidence",
            "版本治理仅记录仓库内可见约定，禁止猜测未出现的版本策略",
        ],
        "forbid": "禁止输出部署拓扑长文、测试覆盖盲区、空泛业务需求叙述。",
        "extra_json_fields": {
            "auth_model": "Markdown，无证据则写 insufficient_evidence",
            "error_code_index": [
                {"code": "", "meaning": "", "evidence": "path:line 或 enum"}
            ],
            "versioning_notes": "Markdown，无证据则写 insufficient_evidence",
        },
    },
}

# 公共 JSON 四字段 (下游已依赖, 不可移除)
_COMMON_SCHEMA_HINT = """  "summary": "Markdown 格式摘要: 必须围绕当前报告类型学习侧重组织章节, 每个事实带文件路径:行号引用",
  "key_modules": [
    {"name": "模块名", "path": "src/xxx/yyy.py", "responsibility": "职责描述", "key_symbols": ["函数/类名"], "confidence": "high"}
  ],
  "dependencies": [
    {"from": "模块A", "to": "模块B", "type": "import|call|inherit", "evidence": "src/a.py:10"}
  ],
  "architecture_notes": "与当前报告类型相关的补充笔记 (Markdown), 带文件路径:行号引用; 非 architecture 类型时勿写成万能架构综述"
"""

# 各类型专属字段名 (用于透传到 learning_result)
TYPE_SPECIFIC_FIELD_NAMES: dict[str, tuple[str, ...]] = {
    "architecture": ("deployment_topology", "data_flows"),
    "design": ("interface_contracts", "exception_paths"),
    "requirements": ("feature_boundaries", "acceptance_candidates"),
    "testcase": ("test_points", "coverage_gaps"),
    "optimization": ("optimization_opportunities", "scalability_limits"),
    "performance": ("hotspots", "complexity_notes", "io_patterns"),
    "defect": ("defect_risks",),
    "api_doc": ("auth_model", "error_code_index", "versioning_notes"),
}

LEARNING_SCHEMA_VERSION = "v2"


def get_learning_focus(report_type: str) -> dict[str, Any]:
    """获取指定 report_type 的学习侧重配置; 未知类型回退 architecture."""
    return LEARNING_FOCUS_BY_TYPE.get(
        report_type, LEARNING_FOCUS_BY_TYPE["architecture"]
    )


def format_learning_focus(report_type: str) -> str:
    """格式化为 CODE_LEARNING_PROMPT 的 {learning_focus} 块 (仅当前类型)."""
    spec = get_learning_focus(report_type)
    dims = [f"- {d}" for d in spec.get("dimensions", [])]
    checks = [
        f"{i}. {c}" for i, c in enumerate(spec.get("must_cover", []), 1)
    ]
    forbid = spec.get("forbid", "")
    lines = [
        f"当前报告类型: {report_type}",
        "学习侧重维度:",
        *dims,
        "",
        "必覆盖检查清单:",
        *checks,
    ]
    if forbid:
        lines.extend(["", f"禁止: {forbid}"])
    lines.extend(
        [
            "",
            "输出硬约束:",
            f"你必须只针对当前报告类型 {report_type} 的学习侧重输出结论；",
            "其他报告类型的维度一律省略，禁止写成「万能架构摘要」。",
        ]
    )
    return "\n".join(lines)


def format_extra_schema(report_type: str) -> str:
    """格式化为 CODE_LEARNING_PROMPT 的 {output_schema_extra} (类型专属 JSON 字段示意)."""
    import json

    spec = get_learning_focus(report_type)
    extra = spec.get("extra_json_fields") or {}
    if not extra:
        return ""
    # 缩进与公共 schema 对齐 (2 空格)
    body = json.dumps(extra, ensure_ascii=False, indent=2)
    # 去掉最外层 {}, 改为逗号引导的字段行
    inner = body.strip()
    if inner.startswith("{") and inner.endswith("}"):
        inner = inner[1:-1].strip()
    return ",\n  " + inner if inner else ""


def format_output_schema_block(report_type: str) -> str:
    """完整输出格式块: 公共四字段 + 类型专属字段."""
    extra = format_extra_schema(report_type)
    return (
        "{\n"
        + _COMMON_SCHEMA_HINT.rstrip()
        + (extra if extra else "")
        + "\n}"
    )


def extract_type_specific_fields(report_type: str, parsed: dict[str, Any]) -> dict[str, Any]:
    """从 LLM 解析结果中提取类型专属字段 (缺失则跳过, 失败降级为空)."""
    if not isinstance(parsed, dict):
        return {}
    names = TYPE_SPECIFIC_FIELD_NAMES.get(report_type, ())
    out: dict[str, Any] = {}
    for name in names:
        if name in parsed:
            out[name] = parsed[name]
    return out


__all__ = [
    "LEARNING_FOCUS_BY_TYPE",
    "LEARNING_SCHEMA_VERSION",
    "TYPE_SPECIFIC_FIELD_NAMES",
    "extract_type_specific_fields",
    "format_extra_schema",
    "format_learning_focus",
    "format_output_schema_block",
    "get_learning_focus",
]

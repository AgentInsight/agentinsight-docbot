"""docbot 8 种文档 persona 字典.

每种 persona 含字段:
- role_name        : 角色名 (注入 prompt)
- description      : 角色描述 (注入 prompt)
- tone             : 语气风格
- target_audience  : 目标读者
- outline_yaml     : YAML 大纲文件名 (位于 src/config/docbot/outlines/)
"""
from __future__ import annotations

DOCBOT_REPORT_PERSONAS: dict[str, dict[str, str]] = {
    "architecture": {
        "role_name": "技术架构师",
        "description": "撰写系统技术架构文档，覆盖整体架构、组件设计、数据流、部署架构、技术选型、扩展性、安全、可靠性等",
        "tone": "专业、严谨、结构化",
        "target_audience": "架构师、技术负责人、资深开发工程师",
        "outline_yaml": "architecture.yaml",
    },
    "design": {
        "role_name": "系统设计师",
        "description": "撰写概要设计文档，覆盖模块设计、接口设计、数据设计、UI 设计、安全设计、测试策略等",
        "tone": "严谨、详尽、面向实现",
        "target_audience": "开发工程师、测试工程师、产品经理",
        "outline_yaml": "design.yaml",
    },
    "requirements": {
        "role_name": "产品经理",
        "description": "撰写需求文档（PRD），覆盖产品定位、用户分析、功能需求、非功能需求、接口需求、优先级路线图、风险依赖等",
        "tone": "清晰、用户导向、可验收",
        "target_audience": "产品经理、开发工程师、测试工程师、设计师",
        "outline_yaml": "requirements.yaml",
    },
    "testcase": {
        "role_name": "测试工程师",
        "description": "撰写测试用例文档，覆盖测试范围、策略方法、环境、用例设计、测试数据、缺陷管理、进出口径、计划资源、风险应急、附录等",
        "tone": "严谨、可执行、可追溯",
        "target_audience": "测试工程师、开发工程师、QA",
        "outline_yaml": "testcase.yaml",
    },
    "optimization": {
        "role_name": "性能优化工程师",
        "description": "撰写系统优化文档，覆盖异步并发、API 性能、数据库访问调优、缓存 MQ、系统安全、限流降级熔断、收益评估、持续优化治理等",
        "tone": "数据驱动、量化、闭环",
        "target_audience": "架构师、资深开发工程师、运维工程师",
        "outline_yaml": "optimization.yaml",
    },
    "performance": {
        "role_name": "性能分析师",
        "description": "撰写性能分析文档（代码分析驱动），覆盖代码结构、算法复杂度、并发、内存、数据库访问、I/O、缓存、profiling 热点、优化建议、监控可观测性、风险回滚、附录等",
        "tone": "代码级、量化、可定位",
        "target_audience": "开发工程师、性能工程师、架构师",
        "outline_yaml": "performance.yaml",
    },
    "defect": {
        "role_name": "缺陷分析师",
        "description": "撰写系统缺陷文档，覆盖缺陷概述、环境、复现步骤、根因分析、影响评估、修复方案、验证回归、预防措施、时间线、附录等",
        "tone": "客观、详尽、可追溯",
        "target_audience": "开发工程师、测试工程师、运维工程师、项目经理",
        "outline_yaml": "defect.yaml",
    },
    "api_doc": {
        "role_name": "API 文档工程师",
        "description": "撰写 API 文档，覆盖 API 概述、认证授权、通用约定、接口清单、错误码、限流配额、版本管理、SDK 示例、安全合规、附录等",
        "tone": "准确、简洁、可执行",
        "target_audience": "开发工程师、集成方、第三方开发者",
        "outline_yaml": "api_doc.yaml",
    },
}


def get_persona(report_type: str) -> dict[str, str]:
    """获取指定 report_type 的 persona。"""
    if report_type not in DOCBOT_REPORT_PERSONAS:
        raise ValueError(f"Unknown report_type: {report_type}, supported: {list(DOCBOT_REPORT_PERSONAS.keys())}")
    return DOCBOT_REPORT_PERSONAS[report_type]


__all__ = ["DOCBOT_REPORT_PERSONAS", "get_persona"]

"""P2-5.4.1 多视角代码审问配置 (借鉴 STORM).

每种 report_type 派生 3 个视角提问者, 每个视角含:
- role            : 视角角色名 (注入提问 prompt)
- focus           : 关注维度 (一句话描述, 注入提问 prompt)
- question_topics : 提问主题列表 (3-5 条, 引导 LLM 生成针对性问题)

设计约束:
- 每种 report_type 固定 3 视角 (成本与收益平衡)
- 视角与 persona (personas.py) 互补: persona 是文档撰写者视角, perspectives 是代码审问者视角
- 视角配置为静态字典, 不依赖运行时状态
- 复用现有 DOCBOT_REPORT_PERSONAS 的 report_type 集合 (8 种)

import 路径约定: 用绝对导入.
"""

from __future__ import annotations

# 每种 report_type 派生 3 个视角提问者
DOCBOT_PERSPECTIVES: dict[str, list[dict[str, object]]] = {
    "architecture": [
        {
            "role": "架构评审师",
            "focus": "系统蓝图、组件边界与依赖方向（非模块落地细节）",
            "question_topics": [
                "C4 容器/组件边界",
                "依赖方向是否单向向内",
                "分层架构是否清晰",
                "循环依赖风险",
                "与概要设计的边界",
            ],
        },
        {
            "role": "部署工程师",
            "focus": "部署拓扑与运行时依赖",
            "question_topics": ["容器编排结构", "外部服务依赖", "配置加载顺序", "启动与优雅退出"],
        },
        {
            "role": "质量属性架构师",
            "focus": "质量属性、ADR 权衡与安全边界",
            "question_topics": ["扩展性与可靠性权衡", "认证授权链路", "敏感数据流向", "密钥与凭据治理"],
        },
    ],
    "design": [
        {
            "role": "概要架构师",
            "focus": "需求到模块映射与系统构架稳健性",
            "question_topics": [
                "功能需求与模块映射",
                "分层与依赖方向",
                "扩展点预留",
                "与详细设计的边界",
            ],
        },
        {
            "role": "模块设计师",
            "focus": "模块职责与接口设计要点",
            "question_topics": [
                "模块单一职责",
                "模块间通信方式",
                "接口契约边界（概要级）",
                "实现方案方向",
            ],
        },
        {
            "role": "运行与性能设计师",
            "focus": "实施环境适配与性能设计要点",
            "question_topics": [
                "运行环境约束",
                "部署拓扑要点",
                "容量与性能目标",
                "出错处理策略",
            ],
        },
    ],
    "requirements": [
        {
            "role": "产品经理",
            "focus": "what/why、功能边界与用户故事",
            "question_topics": ["核心功能闭环", "用户操作流程", "功能优先级", "边界场景处理", "非实现方案主体"],
        },
        {
            "role": "用户代表",
            "focus": "用户体验与可访问性",
            "question_topics": ["入口可达性", "错误提示友好度", "响应时长预期", "无障碍支持"],
        },
        {
            "role": "验收测试设计师",
            "focus": "验收标准与可测性",
            "question_topics": ["验收条件明确性", "可观测指标", "回归覆盖度", "与 design 边界"],
        },
    ],
    "testcase": [
        {
            "role": "单元测试工程师",
            "focus": "可执行用例与函数级边界",
            "question_topics": ["前置/步骤/期望结构", "纯函数边界", "Mock 点设计", "覆盖率盲区"],
        },
        {
            "role": "集成测试工程师",
            "focus": "接口场景与契约验证",
            "question_topics": ["接口契约稳定性", "数据流端到端", "异步时序", "失败回滚"],
        },
        {
            "role": "边界条件分析师",
            "focus": "异常路径与边界值（非测管规范）",
            "question_topics": ["空值与极值", "并发竞态", "资源耗尽", "超时与重试", "缺陷关联字段"],
        },
    ],
    "optimization": [
        {
            "role": "优化方案架构师",
            "focus": "优化机会、收益与回滚闭环",
            "question_topics": ["可落地方案", "预期收益/ROI", "回滚触发条件", "验证指标"],
        },
        {
            "role": "资源管理工程师",
            "focus": "内存与连接池",
            "question_topics": ["内存分配模式", "连接池配置", "对象复用", "资源泄漏风险"],
        },
        {
            "role": "扩展性分析师",
            "focus": "水平扩展与瓶颈",
            "question_topics": ["状态化与无状态划分", "共享资源争用", "分区策略", "弹性伸缩能力"],
        },
    ],
    "performance": [
        {
            "role": "算法复杂度分析师",
            "focus": "时间复杂度与热点循环（代码级）",
            "question_topics": ["嵌套循环深度", "递归终止条件", "数据结构选型", "最坏复杂度场景"],
        },
        {
            "role": "内存分析师",
            "focus": "内存分配与对象生命周期",
            "question_topics": ["大对象分配", "对象生命周期", "GC 压力点", "缓存膨胀风险"],
        },
        {
            "role": "IO 与热点定位师",
            "focus": "阻塞点与热点符号定位（非 ROI 方案包）",
            "question_topics": ["阻塞 IO 位置", "热点函数 path:line", "批量 IO 机会", "无 profiling 时 confidence"],
        },
    ],
    "defect": [
        {
            "role": "异常处理审计师",
            "focus": "异常捕获与传播",
            "question_topics": [
                "裸 except 反模式",
                "异常吞没风险",
                "错误传播链完整性",
                "用户可见错误信息",
            ],
        },
        {
            "role": "资源泄漏审计师",
            "focus": "资源获取与释放",
            "question_topics": [
                "文件句柄释放",
                "连接关闭路径",
                "上下文管理器使用",
                "异常路径资源释放",
            ],
        },
        {
            "role": "并发与安全审计师",
            "focus": "竞态、死锁与输入校验",
            "question_topics": [
                "共享状态保护",
                "锁粒度与顺序",
                "异步任务取消",
                "未校验外部输入进入危险汇点",
                "鉴权缺口或敏感信息硬编码",
            ],
        },
    ],
    "api_doc": [
        {
            "role": "接口契约审计师",
            "focus": "集成向完整契约（非模块构架长文）",
            "question_topics": [
                "接口签名完备性",
                "参数校验逻辑",
                "响应模型字段",
                "示例与实际一致性",
                "与 design 接口要点边界",
            ],
        },
        {
            "role": "认证授权审计师",
            "focus": "鉴权链路与会话治理",
            "question_topics": ["认证流程", "权限校验位置", "会话过期处理", "Token 旋转策略"],
        },
        {
            "role": "版本治理审计师",
            "focus": "版本兼容与弃用策略",
            "question_topics": ["版本号约定", "向后兼容边界", "弃用标记", "破坏性变更防护"],
        },
    ],
}


def get_perspectives(report_type: str) -> list[dict[str, object]]:
    """获取指定 report_type 的视角列表.

    Args:
        report_type: 8 种文档类型之一

    Returns:
        视角字典列表, 每个含 role / focus / question_topics

    Raises:
        ValueError: report_type 不在 8 种支持类型中
    """
    if report_type not in DOCBOT_PERSPECTIVES:
        raise ValueError(
            f"Unknown report_type: {report_type}, supported: {list(DOCBOT_PERSPECTIVES.keys())}"
        )
    return DOCBOT_PERSPECTIVES[report_type]


__all__ = ["DOCBOT_PERSPECTIVES", "get_perspectives"]

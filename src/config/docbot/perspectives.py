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
            "focus": "模块边界与依赖方向",
            "question_topics": [
                "模块划分合理性",
                "依赖方向是否单向向内",
                "分层架构是否清晰",
                "循环依赖风险",
            ],
        },
        {
            "role": "部署工程师",
            "focus": "部署拓扑与运行时依赖",
            "question_topics": ["容器编排结构", "外部服务依赖", "配置加载顺序", "启动与优雅退出"],
        },
        {
            "role": "安全工程师",
            "focus": "安全边界与威胁面",
            "question_topics": ["认证授权链路", "敏感数据流向", "输入校验边界", "密钥与凭据治理"],
        },
    ],
    "design": [
        {
            "role": "模块设计师",
            "focus": "模块职责与接口契约",
            "question_topics": [
                "模块单一职责",
                "接口入参与返回契约",
                "异常传播路径",
                "模块间通信方式",
            ],
        },
        {
            "role": "接口设计师",
            "focus": "API 一致性与版本治理",
            "question_topics": [
                "API 命名一致性",
                "请求响应模型完备性",
                "错误码体系",
                "版本兼容策略",
            ],
        },
        {
            "role": "数据建模师",
            "focus": "数据模型与持久化",
            "question_topics": ["数据模型完整性", "索引与查询性能", "事务边界", "数据迁移与回滚"],
        },
    ],
    "requirements": [
        {
            "role": "产品经理",
            "focus": "功能边界与用户故事",
            "question_topics": ["核心功能闭环", "用户操作流程", "功能优先级", "边界场景处理"],
        },
        {
            "role": "用户代表",
            "focus": "用户体验与可访问性",
            "question_topics": ["入口可达性", "错误提示友好度", "响应时长预期", "无障碍支持"],
        },
        {
            "role": "验收测试设计师",
            "focus": "验收标准与可测性",
            "question_topics": ["验收条件明确性", "可观测指标", "回归覆盖度", "灰度策略"],
        },
    ],
    "testcase": [
        {
            "role": "单元测试工程师",
            "focus": "函数级可测性与边界",
            "question_topics": ["纯函数边界", "副作用隔离", "Mock 点设计", "覆盖率盲区"],
        },
        {
            "role": "集成测试工程师",
            "focus": "模块协作与契约",
            "question_topics": ["接口契约稳定性", "数据流端到端", "异步时序", "失败回滚"],
        },
        {
            "role": "边界条件分析师",
            "focus": "异常路径与边界值",
            "question_topics": ["空值与极值", "并发竞态", "资源耗尽", "超时与重试"],
        },
    ],
    "optimization": [
        {
            "role": "性能优化工程师",
            "focus": "热点函数与调用频率",
            "question_topics": ["高频调用链", "热点函数复杂度", "冗余计算", "批量化机会"],
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
            "focus": "时间复杂度与热点循环",
            "question_topics": ["嵌套循环深度", "递归终止条件", "数据结构选型", "最坏复杂度场景"],
        },
        {
            "role": "内存分析师",
            "focus": "内存分配与对象生命周期",
            "question_topics": ["大对象分配", "对象生命周期", "GC 压力点", "缓存膨胀风险"],
        },
        {
            "role": "IO 模式分析师",
            "focus": "同步异步与阻塞点",
            "question_topics": ["阻塞 IO 位置", "并发模型选择", "批量 IO 机会", "网络往返次数"],
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
            "role": "并发隐患审计师",
            "focus": "竞态与死锁",
            "question_topics": ["共享状态保护", "锁粒度与顺序", "异步任务取消", "可见性问题"],
        },
    ],
    "api_doc": [
        {
            "role": "接口契约审计师",
            "focus": "接口定义与文档一致性",
            "question_topics": [
                "接口签名完备性",
                "参数校验逻辑",
                "响应模型字段",
                "示例与实际一致性",
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

## 1. 引言

AgentAgentInsightService（统一保留英文） 是一个面向 AI Agent 可Observation性与管理的后端平台，采用 monorepo 架构，包含 8 个子项目。核心能力包括：用户与组织管理（统一）、Payment集成（微信/Payment宝）、Trace 数据（统一术语）查询与Alert、Agent Config与Session管理、以及一个 Python 实现的 AI Agent Service。本文档是 AgentAgentInsightService（统一保留英文） 的软件需求规格说明书，为项目的研发、测试与交付提供统一基线，并作为后续设计、开发、测试的输入。

### 1.1. 编写目的与目标读者

本文档旨在完整定义 AgentAgentInsightService（统一保留英文） 的功能需求、非功能需求、接口需求与数据需求，为项目各参与方提供清晰、可验证的需求基线。文档内容严格基于代码仓库的实际实现提取，确保每一项需求描述均可追溯到具体代码实现。

目标读者如下：

| 读者角色 | 关注重点 | 典型使用场景 |
|---------|---------|-------------|
| 后端开发工程师 | 接口定义、业务规则、数据模型、错误码 | 功能开发、接口联调、代码评审 |
| 前端开发工程师 | 接口契约、请求/响应格式、错误码语义 | 页面开发、接口对接、异常处理 |
| 测试工程师 | 验收标准、业务规则、边界条件、错误码 | 测试用例设计、功能验证、回归测试 |
| DevOps 工程师 | 部署架构、Config项、依赖关系、健康检查 | 环境部署、Config管理、监控Alert |
| 产品经理 | 功能范围、业务价值、优先级 | 需求评审、版本规划、验收确认 |
| 架构师 | 架构模式、模块划分、技术选型、数据流 | 架构评审、技术决策、性能优化 |

### 1.2. 产品背景与业务痛点

随着 AI Agent 应用从原型走向生产，开发者和平台运营者面临一系列可Observation性与管理挑战。AgentAgentInsightService（统一保留英文） 正是为解决这些痛点而设计。

**业务痛点分析：**

1. **Trace Trace困难**：Agent 应用涉及多模型调用、多步骤推理，调用链复杂。缺乏端到端的 Trace Trace能力，问题定位耗时巨大。AgentAgentInsightService（统一保留英文） 通过 ClickHouse 存储 Trace/Observation/Score 时序数据，支持复杂过滤与排序查询，帮助开发者快速定位问题链路 [API/Handlers/DataManagement/MetricsHandler.cs]。

2. **成本监控缺失**：Agent 应用调用 LLM API 产生 Token 费用，缺乏精细化成本监控会导致预算失控。平台提供基于 Token 的用量统计与成本核算能力，支持按项目、按模型维度分析成本结构。

3. **Alert通知滞后**：Agent 服务出现异常（如错误率上升、延迟增加）时，缺乏实时Alert机制。平台内置基于 Trace 指标的Alert规则Config与评估引擎，支持系统通知与 SMS 通知两种渠道 [API/Common/Services/AlertService.cs]。

4. **Payment集成复杂**：平台商业化需要对接微信Payment与Payment宝，涉及下单、回调验签、订单状态同步等复杂流程。平台封装了统一的Payment服务层，屏蔽不同Payment渠道的差异 [API/Common/Services/PaymentService.cs]。

5. **Agent Config管理分散**：Agent 的数据源连接、报告模板、Session上下文缺乏统一管理。平台提供 Agent Config、报告模板、Session管理的完整 REST API [API/Controllers/AgentManagement/AgentConfigController.cs]。

### 1.3. 文档范围

本文档覆盖 AgentAgentInsightService（统一保留英文） 的核心服务能力，具体范围如下：

**In-Scope：**

- **API 子项目**（C# Furion 框架）：全部 HTTP 端点，涵盖用户管理、Org/项目管理、Payment管理、Trace 数据（统一术语）查询、Alert管理、Agent Config/报表/Session管理、工具类接口（Bulletin、健康检查、微信工具）等。共 76 个端点，分布在 18 个 Controller 文件中（端点统计基于代码仓库 AST 扫描）。
- **Agents 子项目**（Python FastAPI）：OpenAI 兼容的 Chat Completions API、Session 管理 API、Agent 列表 API，共 6 个端点 [Agents/server.py]。
- **核心服务层**：用户服务、Payment服务、Alert服务、BullMQ 作业队列、ClickHouse 查询客户端、Trace 过滤构建器等。
- **数据存储**：PostgreSQL（User/业务数据）、ClickHouse（Trace/Observation 时序数据）、Redis（缓存与队列）。

**Out-of-Scope：**

- **Admin 管理后台**：基于 Django + simpleui 的管理后台不在本文档详细描述范围内，其功能与 API 子项目存在交叉，但界面交互与Privilege模型独立。
- **前端 Web 应用**：面向终端用户的前端页面不在本文档范围内。
- **Agent SDK**：agentinsight-sdk 的埋点上报协议不在本文档详细描述，但 Trace 数据（统一术语）流会涉及 SDK 上报行为。
- **非功能性需求详细设计**：本文档不包含部署、运维、安全等非功能性需求的详细设计，相关内容将在专门的技术设计文档中阐述。

### 1.4. 术语与缩略语

| 术语 | 英文全称/原文 | 说明 |
|------|--------------|------|
| AgentAgentInsightService（统一保留英文） | AgentAgentInsightService（统一保留英文） | 项目名称，面向 AI Agent 可Observation性与管理的后端平台（品牌名：AgentInsight / AgentInsightService） |
| Agent | Agent | AI Agent，平台管理的核心实体 |
| Trace | Trace | 一次完整的请求链路Trace |
| Span | Span | Trace 中的单个操作单元 |
| Observation | Observation | Observation数据，Trace 的组成部分 |
| Score | Score | Score数据，用于评估 Agent 输出质量 |
| Session | Session | Session，一组连续的 Agent 交互 |
| Alert | Alert | Alert规则或Alert记录 |
| Captcha | Captcha | Captcha，包括图形Captcha与短信Captcha |
| Privilege | Privilege | Privilege，如 Agent 月度配额 |
| Role | Role | Role，如 VIEWER/MEMBER/ADMIN/OWNER |
| Metric | Metric | Metric，如 Token 用量、成本、延迟 |
| Token | Token | LLM 的 Token 计量单位 |
| API Key | API Key | 用于 API 认证的密钥对 |
| ClickHouse | ClickHouse | 列式时序数据库，存储 Trace 数据（统一术语） |
| PostgreSQL | PostgreSQL | 关系型数据库，存储用户与业务数据 |
| Redis | Redis | 内存数据库，用于缓存与队列 |
| BullMQ | BullMQ | 基于 Redis 的作业队列 |
| YARP | YARP | 反向代理，用于路由转发 |
| MediatR | MediatR | .NET 中介者模式库，用于解耦事件处理 |
| Furion | Furion | .NET 应用框架，用于 API 子项目 |
| SqlSugar | SqlSugar | .NET ORM 框架，用于数据库访问 |
| FastAPI | FastAPI | Python Web 框架，用于 Agents 子项目 |
| OpenAI | OpenAI | AI 模型提供商，Agents 子项目兼容其 API |
| Langfuse | Langfuse | 可Observation性平台，通过 YARP 代理转发相关请求 |
| JWT | JSON Web Token | 用于 API 认证的Token |
| SMS | Short Message Service | 短信服务，用于Alert通知 |

### 1.5. 参考文档

| 文档/资源 | 说明 |
|-----------|------|
| README.md | NostologyService/AgentAgentInsightService（统一保留英文） 项目说明 |
| 代码内嵌 Swagger 注释 | 各 Controller 中的 XML 注释，包含接口说明、参数示例、响应示例 |
| API/Program.cs | 服务Config、数据库连接、JWT 设置、反向代理Config |
| Agents/pyproject.toml | Python 子项目依赖与元数据 |
| Models/Common/Enums/ExceptionCodes.cs | 全局错误码定义 |

### 1.6. 版本历史

| 版本 | 日期 | 作者 | 说明 |
|------|------|------|------|
| v1.0 | 待定 | 技术文档组 | 初稿，基于代码仓库 AST 扫描与 RAG 检索生成 |

---

## 2. 产品概述与用户分析

| 能力域 | 核心能力 | 技术实现 | 对应模块 |
|--------|---------|---------|---------|
| 可Observation性 | Trace Trace、Observation 查询、Score 数据 | ClickHouse 时序数据存储 + 动态 SQL 查询 | `API/Controllers/DataManagement/MetricsController.cs` |
| Alert通知 | Alert规则Config、条件评估、系统/SMS 通知 | 策略模式 + MediatR 通知解耦 | `API/Common/Services/AlertService.cs` |
| 商业化 | 微信/Payment宝Payment、订单管理、产品订阅 | 微信Payment (JSAPI/Native/MiniProgram) + Payment宝即时到账 | `API/Common/Services/PaymentService.cs` |
| Agent 管理 | Agent Config、报告模板、Session管理 | Config持久化 + Session上下文管理 | `API/Controllers/AgentManagement/AgentConfigController.cs` |
| 组织与Privilege | 用户注册/登录、Org/Project、角色分配 | PGRole: VIEWER/MEMBER/ADMIN/OWNER + API Key 认证 | `API/Controllers/UserManagement/UserController.cs` |

在技术架构上，平台采用分层架构模式（Controller → Handler → Service → Repository），Handler 层通过 `ApiHandlerBase` 统一注入用户上下文与数据库连接 [API/Handlers/ApiHandlerBase.cs]。同时，平台通过 YARP 反向代理将 `/api/public/` 和 `/public/` 路由转发至 Langfuse Service，实现与开源可Observation性生态的兼容 [API/System/Handlers/AgentInsightTransformProvider.cs]。

 `/public/` 路由转发至 Langfuse Service，实现与开源可Observation性生态的兼容 [API/System/Handlers/AgentInsightTransformProvider.cs]。

平台还内置了一个 Python 实现的 AI Agent Service，提供 OpenAI 兼容的 Chat Completions API（`POST /api/agent/insight`），支持流式响应、Session持久化与多 Agent 路由 [Agents/server.py:346]。这使得 AgentAgentInsightService（统一保留英文） 不仅是Observation平台，还具备 Agent 运行时能力，形成"开发—Observation—运营"的闭环。

### 2.1. 价值主张

AgentAgentInsightService（统一保留英文） 的价值主张围绕三个核心维度展开，分别对应 Agent 应用生命周期中的关键痛点：

**降低运维成本，提升故障响应速度。** 平台通过统一Observation模型（Traces/Observations/Scores）将 Agent 运行时的调用链、中间过程与质量Score汇聚到单一视图。开发者无需在多个系统间切换，即可完成从 Trace 查询到根因定位的完整排障流程。Alert系统支持基于 Trace 指标的规则Config与自动评估，通过 `AlertService` 定时查询 Trace 指标并触发 `AlertTriggeredNotification`，经由 SystemAlertHandler/SMSAlertHandler 发送通知 [API/Common/Services/AlertService.cs]。这一机制将被动排障转变为主动发现，显著缩短故障平均修复时间。

ertHandler/SMSAlertHandler 发送通知 [API/Common/Services/AlertService.cs]。这一机制将被动排障转变为主动发现，显著缩短故障平均修复时间。

**加速商业化进程，实现一站式 Agent 运营管理。** 平台内置微信Payment（JSAPI/Native/MiniProgram）与Payment宝（即时到账）两种Payment渠道，覆盖 H5、扫码、小程序等主流Payment场景 [API/Common/Services/PaymentService.cs]。订单模块支持创建、查询、Payment回调处理与状态同步，Payment回调通过 MediatR 发布 `PaymentTransactionNotification` 事件，由 `PaymentTransactionSaveHandler` 异步持久化并更新订单状态 [API/Notifications/PaymentTransactionNotification.cs]。开发者无需自行对接Payment渠道，即可为 Agent 应用接入付费能力。

**统一管理面，支撑组织级协作。** Organization—Project（Project）—Member三级管理模型，支持角色分配（PGRole: VIEWER/MEMBER/ADMIN/OWNER）与 API Key 认证 [API/Controllers/UserManagement/UserController.cs]。组织管理员可以统一管理成员Privilege、项目配额与 Agent 调用额度，实现团队级资源治理。

下表总结了不同用户角色获得的核心价值：

| 用户角色 | 核心痛点 | 价值获取 |
|---------|---------|---------|
| AI 应用开发工程师 | Trace 查询困难、AlertConfig复杂 | 统一Observation视图 + 智能Alert，快速定位问题 |
| 组织管理员 | 成员Privilege混乱、配额不可控 | Org/Project/成员三级管理 + 角色Privilege控制 |
| 运维人员 | 系统健康不可见、异常发现滞后 | 指标监控 + 多通道Alert（系统/SMS） |
| 商业化负责人 | Payment集成成本高、订单管理分散 | 微信/Payment宝集成 + 订单全生命周期管理 |

### 2.2. 北极星指标

AgentAgentInsightService（统一保留英文） 的北极星指标为**平台接入的活跃 Agent 项目数（月活）**。该指标衡量的是每月在平台上产生有效Observation数据的 Agent 项目数量，反映了平台对开发者的实际使用价值。

选择该指标作为北极星指标，基于以下考量：

**与产品核心价值对齐。** AgentAgentInsightService（统一保留英文） 的核心价值在于为 Agent 应用提供可Observation性与业务支撑。一个 Agent 项目只有在实际接入平台并持续上报 Trace 数据（统一术语）时，才真正体现了平台的价值。活跃项目数直接反映了平台被使用的深度与广度。

**反映用户粘性与增长。** 活跃 Agent 项目数既包含新增接入的项目（增长信号），也包含持续活跃的存量项目（留存信号）。该指标的增长意味着开发者不仅愿意尝试平台，还愿意将平台作为 Agent 应用的长期运维基础设施。

**可量化、可Trace。** 平台通过用户管理模块中的月度 Agent 配额扣减机制（`DeductMonthlyAgentRate` / `ValidateMonthlyAgentRate`）精确Trace每个项目的活跃状态 [API/Controllers/UserManagement/UserController.cs:242-258]。项目删除操作通过 BullMQ 队列异步执行（`EnqueueProjectDeleteAsync`），确保数据清理的可靠性与可审计性 [API/Common/Services/BullMqService.cs]。

北极星指标的拆解与监测体系如下：

| 指标层级 | 指标名称 | 计算方式 | 数据来源 |
|---------|---------|---------|---------|
| 北极星指标 | 活跃 Agent 项目数（月活） | 当月有 Trace 上报的唯一项目数 | ClickHouse Trace 数据（统一术语） |
| 输入指标 | 新增接入项目数 | 当月新创建并完成首次 Trace 上报的项目数 | PostgreSQL 项目表 + ClickHouse |
| 输入指标 | 项目留存率 | 连续 2 个月有 Trace 上报的项目数 / 上月活跃项目数 | ClickHouse Trace 数据（统一术语） |
| 过程指标 | 日均 Trace 上报量 | 当月 Trace 总数 / 当月天数 | ClickHouse Trace 数据（统一术语） |
| 过程指标 | Alert规则Config率 | 已ConfigAlert规则的项目数 / 活跃项目数 | PostgreSQL Alert 表 |
| 结果指标 | 付费转化率 | 已订购产品的项目数 / 活跃项目数 | PostgreSQL Order 表 |

### 2.3. Persona 矩阵

AgentAgentInsightService（统一保留英文） 的核心用户群体可划分为三类 Persona，每类用户在平台中的角色定位、核心诉求与使用路径各有侧重。

**AI 应用开发工程师（主用户）**

AI 应用开发工程师是平台的核心用户群体，负责 Agent 应用的开发、调试与迭代。该类用户的核心诉求是快速定位 Trace 异常、理解 Agent 运行行为、Config有效的Alert规则。

- **核心关注点**：Trace 查询效率、Observation 详情、Score 数据、AlertConfig灵活性
- **典型使用路径**：调用 `POST /api/agent/insight` 接入 Agent Service → 通过 `GET /api/data/metrics/traces` 查询 Trace → 通过 `GET /api/data/metrics/observations` 查看 Observation 详情 → 通过 `POST /api/alert` ConfigAlert规则 [API/Controllers/DataManagement/MetricsController.cs:34-64]
- **关键交互模块**：Trace 数据（统一术语）查询模块（`MetricsController`）、Alert服务模块（`AlertService`）、Agent Session管理模块（`AgentSessionController`）
- **成功标准**：能够在分钟级内定位 Trace 异常根因；Alert规则能够准确捕获异常场景且误报率低于 5%

**组织管理员**

组织管理员负责管理团队成员、项目配额与Privilege分配，是平台治理能力的核心使用者。

- **核心关注点**：成员角色管理、项目配额控制、API Key 安全、Agent 调用额度
- **典型使用路径**：通过 `POST /api/user/organization` 创建组织 → 通过 `POST /api/user/project` 创建项目 → 通过 `POST /api/user/role` 分配角色 → 通过 `POST /api/user/apikey` 创建 API Key [API/Controllers/UserManagement/OrganizationController.cs:28-42]
- **关键交互模块**：用户管理模块（`UserController`）、组织管理模块（`OrganizationController`）、项目配额扣减（`DeductMonthlyAgentRate`）
- **成功标准**：能够有效控制成员访问Privilege；项目配额与实际使用量匹配；API Key 全生命周期可管理

**运维人员**

运维人员关注平台本身的系统健康与异常Alert，是平台稳定运行的守护者。

- **核心关注点**：系统健康状态、异常Alert及时性、Alert通知渠道可靠性
- **典型使用路径**：通过 `GET /api/tools/health` 检查系统健康状态 → 通过 `GET /api/alert/record` 查看Alert记录 → 通过 `POST /api/alert/record/read` 标记Alert已读 [API/Controllers/ToolsManagement/HealthController.cs:20]
- **关键交互模块**：Alert服务模块（`AlertService`）、健康检查模块（`HealthController`）、系统通知/SMS Alert通道
- **成功标准**：系统异常能够在 5 分钟内触发Alert；Alert通知送达率不低于 99%；Alert记录可追溯、可审计

| Persona | 角色定位 | 核心诉求 | 关键模块 | 成功标准 |
|---------|---------|---------|---------|---------|
| AI 应用开发工程师 | 主用户 | Trace 查询、AlertConfig | MetricsController、AlertService | 分钟级定位异常，误报率 <5% |
| 组织管理员 | 治理者 | Privilege管理、配额控制 | UserController、OrganizationController | Privilege可控，配额匹配 |
| 运维人员 | 守护者 | 系统健康、异常Alert | AlertService、HealthController | 5 分钟Alert，送达率 ≥99% |

### 2.4. 用户旅程

用户旅程描述了开发者从注册到深度使用 AgentAgentInsightService（统一保留英文） 的完整路径，涵盖账号开通、数据接入、Observation分析、AlertConfig与商业化变现五个关键阶段。

**阶段一：注册与组织创建**

用户通过手机号注册账号，系统通过 `POST /api/user` 创建用户，并通过 `POST /api/user/login` 完成登录认证 [API/Controllers/UserManagement/UserController.cs:43-73]。登录后，用户创建组织（`POST /api/user/organization`）与项目（`POST /api/user/project`），建立资源隔离边界。系统通过 JWT 认证（HS256 算法，过期时间 43200 分钟）维持Session状态，用户Session通过 Redis 缓存支持多设备登录 [API/Common/Services/UserService.cs]。

**阶段二：Agent 接入与 Trace 上报**

开发者通过 `POST /api/agent/insight` 调用平台内置的 AI Agent Service，该服务提供 OpenAI 兼容的 Chat Completions API [Agents/server.py:346]。Agent 运行过程中产生的 Trace 数据（统一术语）通过 SDK 上报至平台，经 BullMQ 队列（`EnqueueTraceIngestionAsync`）异步写入 ClickHouse [API/Common/Services/BullMqService.cs]。开发者也可以通过 YARP 反向代理将 `/api/public/` 路由转发至 Langfuse Service，实现与开源生态的兼容 [API/System/Handlers/AgentInsightTransformProvider.cs]。

**阶段三：Observation分析与问题定位**

开发者通过 `GET /api/data/metrics/traces` 查询 Trace 列表，通过 `GET /api/data/metrics/observations` 查看 Observation 详情，通过 `GET /api/data/metrics/scores` 查看 Score 数据 [API/Controllers/DataManagement/MetricsController.cs:34-50]。查询支持复杂过滤与排序，`TraceFilterBuilder` 将前端过滤条件转换为 ClickHouse SQL 查询子句，支持 DateTime、String、Number、ArrayOptions 等多种数据类型 [API/Common/Helpers/TraceFilterBuilder.cs]。开发者还可以通过 `GET /api/agent/session` 查看 Agent Session列表，回溯完整的对话上下文 [API/Controllers/AgentManagement/AgentSessionController.cs:33]。

**阶段四：AlertConfig与通知接收**

开发者通过 `POST /api/alert` 创建Alert规则，支持基于 TotalTokens、TotalCost、ErrorCount、Latency、ErrorRate 等指标的阈值Alert [API/Controllers/UserManagement/AlertController.cs:61]。Alert规则通过 `AlertService` 定时评估，触发后通过 MediatR 发布 `AlertTriggeredNotification` 事件，由 SystemAlertHandler/SMSAlertHandler 分别发送系统通知与短信通知 [API/Common/Services/AlertService.cs]。开发者可以通过 `GET /api/alert/record` 查看Alert记录，并通过 `POST /api/alert/record/read` 标记已读。

**阶段五：商业化与产品订购**

开发者通过 `GET /api/product` 查看可用产品，通过 `POST /api/payment/order` 创建订单，选择微信Payment或Payment宝完成Payment [API/Controllers/PaymentManagement/OrderController.cs:34-48]。Payment回调通过 `POST /api/payment/notify/wechatnotify` 或 `POST /api/payment/notify/alipaynotify` 接收，经验签后由 MediatR 发布 `PaymentTransactionNotification` 事件，异步更新订单状态 [API/Controllers/PaymentManagement/NotifyController.cs:29-57]。产品订购后，组织管理员可以通过 `GET /api/user/privilege/agent/validate` 验证 Agent 配额，确保资源使用在限额范围内。

| 旅程阶段 | 用户动作 | 关键接口 | 核心价值 |
|---------|---------|---------|---------|
| 注册与组织创建 | 注册账号、创建组织/Project | POST /api/user、POST /api/user/organization | 建立资源隔离边界 |
| Agent 接入与 Trace 上报 | 调用 Agent API、上报 Trace | POST /api/agent/insight、EnqueueTraceIngestionAsync | 数据采集与持久化 |
| Observation分析与问题定位 | 查询 Trace/Observation/Score | GET /api/data/metrics/traces | 快速定位问题 |
| AlertConfig与通知接收 | 创建Alert规则、接收通知 | POST /api/alert、AlertTriggeredNotification | 主动发现异常 |
| 商业化与产品订购 | 创建订单、完成Payment | POST /api/payment/order、Payment回调 | 加速商业化变现 |

rtTriggeredNotification | 主动发现异常 |
| 商业化与产品订购 | 创建订单、完成Payment | POST /api/payment/order、Payment回调 | 加速商业化变现 |

整个用户旅程覆盖了 Agent 应用从开发调试到上线运营、再到商业化变现的完整生命周期，体现了 AgentAgentInsightService（统一保留英文） 作为一站式 Agent 运营管理平台的产品定位。

---

## 3. 功能需求

- **用户故事**: 作为已登录用户，我希望获取我的 Agent Config信息，以便查看数据源连接与默认模板设置。
- **主流程**:
  1. 用户发送 `GET /api/agent/config` 请求
  2. `AgentConfigController.Get` 调用 `_handler.GetConfig()` 获取当前用户Config [API/Controllers/AgentManagement/AgentConfigController.cs:28]
  3. 返回 `ApiResponse<AgentConfig>`，包含 `id`、`userid`、`datasource`、`defaulttemplateid`、`createdat`、`updatedat` 字段
- **验收标准**:
  - [ ] AC1: 返回 `errorCode=0` 且响应包含 `AgentConfig` 对象，含 `datasource` 与 `defaulttemplateid` 字段
  - [ ] AC2: 若当前用户不存在 Agent Config，返回 `errorCode=AgentConfigNotFound(150022)`
  - [ ] AC3: 未携带有效 JWT Token 时返回 `errorCode=UnAuthToken(100000)`
- **业务规则**:
  - BR-001: 仅返回当前登录用户的Config，不返回其他用户数据

#### 3.1.1. FR-002 删除 Agent Config [优先级: Must]

- **用户故事**: 作为已登录用户，我希望删除我的 Agent Config，以便重置数据源设置。
- **主流程**:
  1. 用户发送 `GET /api/agent/config/delete` 请求
  2. `AgentConfigController.Delete` 调用 `_handler.DeleteConfig()` 删除当前用户Config [API/Controllers/AgentManagement/AgentConfigController.cs:40]
  3. 返回空 `ApiResponse<object>`
- **验收标准**:
  - [ ] AC1: 返回 `errorCode=0` 且 `data` 为 `null`
  - [ ] AC2: 若Config不存在，返回 `errorCode=AgentConfigNotFound(150022)`
  - [ ] AC3: 删除后再次调用 FR-001 应返回 `AgentConfigNotFound(150022)`
- **业务规则**:
  - BR-002: 仅允许删除当前登录用户的Config

#### 3.1.2. FR-003 创建或更新 Agent Config [优先级: Must]

- **用户故事**: 作为已登录用户，我希望创建或更新我的 Agent Config，以便设置数据源连接与默认报告模板。
- **主流程**:
  1. 用户发送 `POST /api/agent/config` 请求，body 包含 `datasource` 与 `defaulttemplateid`
  2. `AgentConfigController.Post` 调用 `_handler.CreateOrUpdateConfig(body)` [API/Controllers/AgentManagement/AgentConfigController.cs:54]
  3. 存在则更新，不存在则创建；`datasource`/`defaulttemplateid` 为空则忽略
  4. 返回更新后的 `AgentConfig`
- **验收标准**:
  - [ ] AC1: 返回 `errorCode=0` 且响应包含更新后的 `AgentConfig` 对象
  - [ ] AC2: 若 `datasource` 与 `defaulttemplateid` 均为空，返回 `errorCode=AgentConfigNotFound(150022)`
  - [ ] AC3: 若 `defaulttemplateid` 指向不存在的模板，返回 `errorCode=AgentReportTemplateNotFound(150023)`
- **业务规则**:
  - BR-003: Config存在则更新，不存在则创建（upsert 语义）

### 3.2. Agent 报告模板 (AgentReportController)

本子章节包含 FR-004 至 FR-006，对应 `API/Controllers/AgentManagement/AgentReportController.cs` 中的 3 个端点，负责 Agent 报告模板的查询、删除与创建/更新。

#### 3.2.1. FR-004 获取报告模板列表或详情 [优先级: Must]

- **用户故事**: 作为已登录用户，我希望获取报告模板列表或单个模板详情，以便选择或查看报告模板。
- **主流程**:
  1. 用户发送 `GET /api/agent/report` 请求，可选参数 `id`、`includedpredefined`、`includedpredefinedonly`、`page`、`pageSize`
  2. `AgentReportController.GetTemplates` 调用 `_handler.GetTemplates(...)` [API/Controllers/AgentManagement/AgentReportController.cs:35]
  3. 若 `id` 为空，返回当前用户的模板列表（不包含 File），支持分页；若 `id` 不为空，返回对应模板全部内容（包含 File）
  4. 支持包含系统预定义模板（`includedpredefined=true`）或仅返回预定义模板（`includedpredefinedonly=true`）
- **验收标准**:
  - [ ] AC1: 返回 `errorCode=0` 且响应包含 `AgentReportTemplate` 列表及 `totalCount` 分页信息
  - [ ] AC2: 当 `id` 指定且模板不存在或不属于当前用户时，返回 `errorCode=AgentReportTemplateNotFound(150023)`
  - [ ] AC3: 当 `includedpredefinedonly=true` 时，仅返回 `UserId == null` 的系统预定义模板
- **业务规则**:
  - BR-004: 模板查询按 `UpdatedAt` 降序排列 [API/Handlers/AgentManagement/AgentReportHandler.cs]
  - BR-005: 用户只能访问 `UserId == User.Id` 或 `UserId == null` 的模板

#### 3.2.2. FR-005 删除报告模板 [优先级: Must]

- **用户故事**: 作为已登录用户，我希望删除我的报告模板，以便清理不再使用的模板。
- **主流程**:
  1. 用户发送 `GET /api/agent/report/delete` 请求，参数 `ids` 为逗号分隔的模板 ID 列表
  2. `AgentReportController.DeleteTemplates` 调用 `_handler.DeleteTemplates(ids)` [API/Controllers/AgentManagement/AgentReportController.cs:48]
  3. 仅删除当前用户名下的模板
- **验收标准**:
  - [ ] AC1: 返回 `errorCode=0` 且 `data` 为 `null`
  - [ ] AC2: 若 `ids` 为空，不执行删除操作，返回 `errorCode=0`
  - [ ] AC3: 若指定的模板 ID 不属于当前用户，不执行删除且返回 `errorCode=AgentReportTemplateNotFound(150023)`
- **业务规则**:
  - BR-006: 仅允许删除当前用户名下的模板，系统预定义模板不可删除

#### 3.2.3. FR-006 创建或更新报告模板 [优先级: Must]

- **用户故事**: 作为已登录用户，我希望创建或更新报告模板，以便定制报告样式与内容。
- **主流程**:
  1. 用户发送 `POST /api/agent/report` 请求，body 包含 `id`、`name`、`category`、`file`（PDF base64）
  2. `AgentReportController.CreateOrUpdateTemplate` 调用 `_handler.CreateOrUpdateTemplate(body)` [API/Controllers/AgentManagement/AgentReportController.cs:62]
  3. `id` 为空则创建，不为空则更新；`name`/`category` 为空则忽略；`thumbnail` 通过 `file` 生成
- **验收标准**:
  - [ ] AC1: 返回 `errorCode=0` 且响应包含创建或更新后的 `AgentReportTemplate`
  - [ ] AC2: 若 `name` 为空且为创建操作，返回 `errorCode=EmptyAgentReportTemplateName(150024)`
  - [ ] AC3: 若 `id` 指定且模板不存在或不属于当前用户，返回 `errorCode=AgentReportTemplateNotFound(150023)`
- **业务规则**:
  - BR-007: 模板名称必填，创建时 `name` 不能为空

### 3.3. Agent Session管理 (AgentSessionController)

本子章节包含 FR-007 至 FR-009，对应 `API/Controllers/AgentManagement/AgentSessionController.cs` 中的 3 个端点，负责 Agent Session的查询、删除与创建/更新。

#### 3.3.1. FR-007 获取Session列表或详情 [优先级: Must]

- **用户故事**: 作为已登录用户，我希望获取我的 Agent Session列表或单个Session详情，以便查看历史对话。
- **主流程**:
  1. 用户发送 `GET /api/agent/session` 请求，可选参数 `id`、`page`、`pageSize`
  2. `AgentSessionController.Get` 调用 `_handler.GetSessions(id, page, pageSize)` [API/Controllers/AgentManagement/AgentSessionController.cs:33]
  3. 若 `id` 为空，返回当前用户的所有Session列表（不包含 Context），支持分页；若 `id` 不为空，返回对应Session全部内容（包含 Context）
- **验收标准**:
  - [ ] AC1: 返回 `errorCode=0` 且响应包含 `AgentSession` 列表及 `totalCount` 分页信息
  - [ ] AC2: 当 `id` 指定且Session不存在或不属于当前用户时，返回 `errorCode=AgentSessionNotFound(150021)`
  - [ ] AC3: 列表模式下响应不包含 `Context` 字段，详情模式下包含 `Context` 字段
- **业务规则**:
  - BR-008: Session按创建时间倒序排列，仅返回当前用户的Session

#### 3.3.2. FR-008 删除Session [优先级: Must]

- **用户故事**: 作为已登录用户，我希望删除我的 Agent Session，以便清理历史对话记录。
- **主流程**:
  1. 用户发送 `GET /api/agent/session/delete` 请求，参数 `ids` 为逗号分隔的Session ID 列表
  2. `AgentSessionController.Delete` 调用 `_handler.DeleteSessions(ids)` [API/Controllers/AgentManagement/AgentSessionController.cs:46]
  3. 仅删除当前用户名下的Session
- **验收标准**:
  - [ ] AC1: 返回 `errorCode=0` 且 `data` 为 `null`
  - [ ] AC2: 若 `ids` 为空，不执行删除操作，返回 `errorCode=0`
  - [ ] AC3: 若指定的Session ID 不属于当前用户，不执行删除且返回 `errorCode=AgentSessionNotFound(150021)`
- **业务规则**:
  - BR-009: 仅允许删除当前用户名下的Session

#### 3.3.3. FR-009 创建或更新Session [优先级: Must]

- **用户故事**: 作为已登录用户，我希望创建或更新我的 Agent Session，以便保存对话上下文。
- **主流程**:
  1. 用户发送 `POST /api/agent/session` 请求，body 包含 `id`、`name`、`context`
  2. `AgentSessionController.Post` 调用 `_handler.CreateOrUpdateSession(body)` [API/Controllers/AgentManagement/AgentSessionController.cs:60]
  3. `id` 为空则创建，不为空则更新；`name`/`context` 为空则忽略
- **验收标准**:
  - [ ] AC1: 返回 `errorCode=0` 且响应包含创建或更新后的 `AgentSession`
  - [ ] AC2: 若 `id` 指定且Session不存在或不属于当前用户，返回 `errorCode=AgentSessionNotFound(150021)`
  - [ ] AC3: 创建成功后可通过 FR-007 详情模式查询到该Session
- **业务规则**:
  - BR-010: Session名称可为空，创建时自动关联当前用户

### 3.4. 数据指标管理 (MetricsController, ModelController)

本子章节包含 FR-010 至 FR-013，对应 `API/Controllers/DataManagement/MetricsController.cs` 与 `API/Controllers/DataManagement/ModelController.cs` 中的 4 个端点，负责 Trace 数据（统一术语）的 Observation/Score/Trace 查询与模型列表获取。

#### 3.4.1. FR-010 获取 Observations 列表 [优先级: Must]

- **用户故事**: 作为已登录用户，我希望根据 Trace ID 获取 Observations 列表，以便查看 Trace 的详细执行步骤。
- **主流程**:
  1. 用户发送 `GET /api/data/metrics/observations` 请求，参数 `id`（Trace ID）、`page`、`pagesize`
  2. `MetricsController.GetObservations` 调用 `_handler.GetObservationsAsync(id, page, pagesize)` [API/Controllers/DataManagement/MetricsController.cs:34]
  3. 返回 `ApiResponse<Observation>` 列表及分页信息
- **验收标准**:
  - [ ] AC1: 返回 `errorCode=0` 且响应包含 `Observation` 列表及 `totalCount`
  - [ ] AC2: 若 `id` 为空，返回 `errorCode=EmptyTraceId(150018)`
  - [ ] AC3: 若 ClickHouse 查询失败，返回 `errorCode=ClickHouseQueryError(150010)`
- **业务规则**:
  - BR-011: 查询基于 ClickHouse 时序数据库，通过 `ClickHouseClient` 执行 [API/Handlers/DataManagement/MetricsHandler.cs:8]

#### 3.4.2. FR-011 获取 Scores 列表 [优先级: Must]

- **用户故事**: 作为已登录用户，我希望根据 Trace ID 获取 Scores 列表，以便查看 Trace 的Score结果。
- **主流程**:
  1. 用户发送 `GET /api/data/metrics/scores` 请求，参数 `id`（Trace ID）、`page`、`pagesize`
  2. `MetricsController.GetScores` 调用 `_handler.GetScoresAsync(id, page, pagesize)` [API/Controllers/DataManagement/MetricsController.cs:50]
  3. 返回 `ApiResponse<Score>` 列表及分页信息
- **验收标准**:
  - [ ] AC1: 返回 `errorCode=0` 且响应包含 `Score` 列表及 `totalCount`
  - [ ] AC2: 若 `id` 为空，返回 `errorCode=EmptyTraceId(150018)`
  - [ ] AC3: 若 ClickHouse 查询超时，返回 `errorCode=ClickHouseQueryTimeout(150017)`
- **业务规则**:
  - BR-012: Score 查询与 Observation 查询共用 ClickHouse 连接池

#### 3.4.3. FR-012 获取 Trace 指标详情 [优先级: Must]

- **用户故事**: 作为已登录用户，我希望根据 Trace ID 批量获取指标详情，以便查看 Token 消耗、费用与延迟。
- **主流程**:
  1. 用户发送 `GET /api/data/metrics/traces` 请求，参数 `ids` 为逗号分隔的 Trace ID 列表
  2. `MetricsController.GetTraces` 调用 `_handler.GetTracesMetrics(ids)` [API/Controllers/DataManagement/MetricsController.cs:64]
  3. 返回 `TraceMetricsResponse` 列表，包含 `inputtokens`、`outputtokens`、`totaltokens`、`inputcost`、`outputcost`、`totalcost`、`latency`、`modelnames`
  4. 同时支持 `POST /api/data/metrics/traces` 方式提交查询条件 [API/Controllers/DataManagement/MetricsController.cs:125]
- **验收标准**:
  - [ ] AC1: 返回 `errorCode=0` 且响应包含 `TraceMetricsResponse` 列表
  - [ ] AC2: 若 `ids` 为空，返回 `errorCode=EmptyTraceIds(150009)`
  - [ ] AC3: 若 Trace ID 数量超过系统限制，返回 `errorCode=TooManyTraceIds(150011)`
- **业务规则**:
  - BR-013: 支持 GET 与 POST 两种请求方式，POST 支持复杂过滤条件

#### 3.4.4. FR-013 获取模型列表 [优先级: Should]

- **用户故事**: 作为已登录用户，我希望获取可用模型列表，以便了解系统支持的模型。
- **主流程**:
  1. 用户发送 `GET /api/data/model` 请求
  2. `ModelController.Get` 处理请求 [API/Controllers/DataManagement/ModelController.cs:34]
  3. 返回模型列表
- **验收标准**:
  - [ ] AC1: 返回 `errorCode=0` 且响应包含模型列表
  - [ ] AC2: 未携带有效 JWT Token 时返回 `errorCode=UnAuthToken(100000)`
- **业务规则**:
  - BR-014: 模型列表来源于系统Config

### 3.5. Payment管理 (NotifyController, OrderController)

本子章节包含 FR-014 至 FR-019，对应 `API/Controllers/PaymentManagement/NotifyController.cs` 与 `API/Controllers/PaymentManagement/OrderController.cs` 中的 6 个端点，负责Payment回调与订单管理。

#### 3.5.1. FR-014 微信Payment回调 [优先级: Must]

- **用户故事**: 作为微信Payment平台，我希望向 AgentAgentInsightService（统一保留英文） 发送Payment结果通知，以便系统更新订单状态。
- **主流程**:
  1. 微信Payment平台发送 `POST /api/payment/notify/wechatnotify` 请求
  2. `NotifyController.WeChatNotify` 验签并处理回调 [API/Controllers/PaymentManagement/NotifyController.cs:29]
  3. 验签通过后发布 `PaymentTransactionNotification` 事件，由 `PaymentTransactionSaveHandler` 持久化并更新订单状态
- **验收标准**:
  - [ ] AC1: 验签失败时返回 `errorCode=InvalidWeChatNotify(810010)`
  - [ ] AC2: 微信PaymentConfig缺失时返回 `errorCode=WeChatSettingNotConfig(810001)`
  - [ ] AC3: 回调处理成功返回 `errorCode=0` 且订单状态更新为 `Paid`
- **业务规则**:
  - BR-015: 微信Payment金额单位为分（`WeChatAmountUnit = 100`），需转换为元 [API/Common/Services/PaymentService.cs:10]
  - BR-016: 回调需验签，使用微信Payment证书

#### 3.5.2. FR-015 Payment宝Payment回调 [优先级: Must]

- **用户故事**: 作为Payment宝平台，我希望向 AgentAgentInsightService（统一保留英文） 发送Payment结果通知，以便系统更新订单状态。
- **主流程**:
  1. Payment宝平台发送 `POST /api/payment/notify/alipaynotify` 请求
  2. `NotifyController.AlipayNotify` 验签并处理回调 [API/Controllers/PaymentManagement/NotifyController.cs:57]
  3. 验签通过后发布 `PaymentTransactionNotification` 事件
- **验收标准**:
  - [ ] AC1: 验签失败时返回 `errorCode=AlipaySignatureError(810007)`
  - [ ] AC2: Payment宝Config缺失时返回 `errorCode=AlipaySettingNotConfig(810002)`
  - [ ] AC3: 回调处理成功返回 `errorCode=0` 且订单状态更新
- **业务规则**:
  - BR-017: Payment宝金额单位为元，与微信Payment的分单位不同

#### 3.5.3. FR-016 获取订单列表 [优先级: Must]

- **用户故事**: 作为组织管理员，我希望获取组织下的订单列表，以便查看购买记录。
- **主流程**:
  1. 用户发送 `GET /api/payment/order` 请求，参数 `orgId`、`page`、`pageSize`
  2. `OrderController.Get` 调用 `_handler.GetOrders(orgId, page, pageSize)` [API/Controllers/PaymentManagement/OrderController.cs:34]
  3. 返回 `AgentInsightOrder` 列表及分页信息
- **验收标准**:
  - [ ] AC1: 返回 `errorCode=0` 且响应包含 `AgentInsightOrder` 列表及 `totalCount`
  - [ ] AC2: 若 `orgId` 为空，返回 `errorCode=DoNotOwnOrganization(810012)`
  - [ ] AC3: 若当前用户不属于该组织，返回 `errorCode=DoNotOwnOrganization(810012)`
- **业务规则**:
  - BR-018: 订单包含 `orderno`、`tradeno`、`productname`、`totalamount`、`orderstate` 等字段

#### 3.5.4. FR-017 下单 [优先级: Must]

- **用户故事**: 作为已登录用户，我希望根据订单号查询订单状态，以便确认Payment结果。
- **主流程**:
  1. 用户发送 `GET /api/payment/order/query` 请求，参数 `orderNo`
  2. `OrderController.Query` 调用 `_handler.QueryOrder(orderNo)` [API/Controllers/PaymentManagement/OrderController.cs:64]
  3. 接口限流：`maxRequests=1, windowSeconds=1`
  4. 返回 `AgentInsightOrderResponse` 包含最新订单状态
- **验收标准**:
  - [ ] AC1: 返回 `errorCode=0` 且响应包含 `orderstate` 字段
  - [ ] AC2: 若 `orderNo` 为空，返回 `errorCode=EmptyOrderNo(810011)`
  - [ ] AC3: 若订单不存在，返回 `errorCode=OrderNotExist(810015)`
- **业务规则**:
  - BR-021: 查询接口限流 1 次/1 秒

#### 3.5.5. FR-019 获取订单转化率 [优先级: Should]

- **用户故事**: 作为组织管理员，我希望获取订单转化率，以便分析销售效果。
- **主流程**:
  1. 用户发送 `GET /api/payment/order/conversion` 请求
  2. `OrderController.GetConversion` 处理请求 [API/Controllers/PaymentManagement/OrderController.cs:79]
  3. 返回订单转化率数据
- **验收标准**:
  - [ ] AC1: 返回 `errorCode=0` 且响应包含转化率数据
  - [ ] AC2: 未携带有效 JWT Token 时返回 `errorCode=UnAuthToken(100000)`
- **业务规则**:
  - BR-022: 转化率基于订单状态统计

### 3.6. 产品管理 (ProductController)

本子章节包含 FR-020 至 FR-021，对应 `API/Controllers/ProductManagement/ProductController.cs` 中的 2 个端点，负责产品列表与产品时长查询。

#### 3.6.1. FR-020 获取产品列表 [优先级: Must]

- **用户故事**: 作为已登录用户，我希望获取产品列表，以便了解可购买的产品与价格。
- **主流程**:
  1. 用户发送 `GET /api/product` 请求
  2. `ProductController.Get` 处理请求 [API/Controllers/ProductManagement/ProductController.cs:26]
  3. 返回产品列表
- **验收标准**:
  - [ ] AC1: 返回 `errorCode=0` 且响应包含产品列表
  - [ ] AC2: 未携带有效 JWT Token 时返回 `errorCode=UnAuthToken(100000)`
- **业务规则**:
  - BR-023: 产品类型包含 `Monthly` 与 `Permanent`

#### 3.6.2. FR-021 获取产品时长列表 [优先级: Must]

- **用户故事**: 作为已登录用户，我希望获取产品时长列表，以便选择购买时长。
- **主流程**:
  1. 用户发送 `GET /api/product/duration` 请求
  2. `ProductController.GetDuration` 处理请求 [API/Controllers/ProductManagement/ProductController.cs:38]
  3. 返回产品时长列表
- **验收标准**:
  - [ ] AC1: 返回 `errorCode=0` 且响应包含产品时长列表
  - [ ] AC2: 未携带有效 JWT Token 时返回 `errorCode=UnAuthToken(100000)`
- **业务规则**:
  - BR-024: 产品时长与产品关联，用于下单时指定

### 3.7. 工具管理 (BulletinController, HealthController, WeChatController)

本子章节包含 FR-022 至 FR-031，对应 `API/Controllers/ToolsManagement/` 下的 3 个 Controller 共 10 个端点，负责Bulletin管理、健康检查与微信工具。

#### 3.7.1. FR-022 发布Bulletin [优先级: Should]

- **用户故事**: 作为管理员，我希望发布Bulletin，以便向用户传达系统通知。
- **主流程**:
  1. 管理员发送 `POST /api/tools/bulletin` 请求
  2. `BulletinController.Post` 处理请求 [API/Controllers/ToolsManagement/BulletinController.cs:32]
  3. 创建Bulletin记录
- **验收标准**:
  - [ ] AC1: 返回 `errorCode=0` 且Bulletin创建成功
  - [ ] AC2: 未携带有效 JWT Token 时返回 `errorCode=UnAuthToken(100000)`
- **业务规则**:
  - BR-025: Bulletin发布后需审核

#### 3.7.2. FR-023 获取用户协议 [优先级: Should]

- **用户故事**: 作为访客，我希望获取用户协议，以便了解使用条款。
- **主流程**:
  1. 用户发送 `GET /api/tools/bulletin/agreement` 请求
  2. `BulletinController.Get` 处理请求 [API/Controllers/ToolsManagement/BulletinController.cs:45]
  3. 返回用户协议内容
- **验收标准**:
  - [ ] AC1: 返回 `errorCode=0` 且响应包含协议内容
- **业务规则**:
  - BR-026: 该接口无需认证

#### 3.7.3. FR-024 获取Bulletin列表 [优先级: Should]

- **用户故事**: 作为已登录用户，我希望获取Bulletin列表，以便查看系统通知。
- **主流程**:
  1. 用户发送 `GET /api/tools/bulletin/bulletins` 请求
  2. `BulletinController.GetBulletins` 处理请求 [API/Controllers/ToolsManagement/BulletinController.cs:64]
  3. 返回已发布的Bulletin列表
- **验收标准**:
  - [ ] AC1: 返回 `errorCode=0` 且响应包含Bulletin列表
  - [ ] AC2: 未携带有效 JWT Token 时返回 `errorCode=UnAuthToken(100000)`
- **业务规则**:
  - BR-027: 仅返回审核通过的Bulletin

#### 3.7.4. FR-025 获取后台Bulletin列表 [优先级: Should]

- **用户故事**: 作为管理员，我希望获取后台Bulletin列表，以便管理所有Bulletin。
- **主流程**:
  1. 管理员发送 `GET /api/tools/bulletin/backend` 请求
  2. `BulletinController.GetBackendBulletins` 处理请求 [API/Controllers/ToolsManagement/BulletinController.cs:82]
  3. 返回所有Bulletin（含待审核）
- **验收标准**:
  - [ ] AC1: 返回 `errorCode=0` 且响应包含Bulletin列表
  - [ ] AC2: 未携带有效 JWT Token 时返回 `errorCode=UnAuthToken(100000)`
- **业务规则**:
  - BR-028: 仅管理员可访问

#### 3.7.5. FR-026 审核Bulletin [优先级: Should]

- **用户故事**: 作为管理员，我希望审核Bulletin，以便控制Bulletin发布。
- **主流程**:
  1. 管理员发送 `POST /api/tools/bulletin/approve` 请求
  2. `BulletinController.ApproveBulletin` 处理请求 [API/Controllers/ToolsManagement/BulletinController.cs:96]
  3. 更新Bulletin审核状态
- **验收标准**:
  - [ ] AC1: 返回 `errorCode=0` 且Bulletin审核状态更新
  - [ ] AC2: 未携带有效 JWT Token 时返回 `errorCode=UnAuthToken(100000)`
- **业务规则**:
  - BR-029: 仅管理员可审核

#### 3.7.6. FR-027 修订Bulletin [优先级: Should]

- **用户故事**: 作为管理员，我希望修订Bulletin，以便更新Bulletin内容。
- **主流程**:
  1. 管理员发送 `POST /api/tools/bulletin/revision` 请求
  2. `BulletinController.ReviseBulletin` 处理请求 [API/Controllers/ToolsManagement/BulletinController.cs:110]
  3. 更新Bulletin内容
- **验收标准**:
  - [ ] AC1: 返回 `errorCode=0` 且Bulletin内容更新
  - [ ] AC2: 未携带有效 JWT Token 时返回 `errorCode=UnAuthToken(100000)`
- **业务规则**:
  - BR-030: 修订后需重新审核

#### 3.7.7. FR-028 关闭Bulletin [优先级: Should]

- **用户故事**: 作为管理员，我希望关闭Bulletin，以便停止Bulletin展示。
- **主流程**:
  1. 管理员发送 `POST /api/tools/bulletin/close` 请求
  2. `BulletinController.CloseBulletin` 处理请求 [API/Controllers/ToolsManagement/BulletinController.cs:124]
  3. 更新Bulletin状态为关闭
- **验收标准**:
  - [ ] AC1: 返回 `errorCode=0` 且Bulletin状态更新为关闭
  - [ ] AC2: 未携带有效 JWT Token 时返回 `errorCode=UnAuthToken(100000)`
- **业务规则**:
  - BR-031: 关闭后Bulletin不再展示

#### 3.7.8. FR-029 健康检查 [优先级: Must]

- **用户故事**: 作为运维人员，我希望检查系统健康状态，以便确认服务可用。
- **主流程**:
  1. 用户发送 `GET /api/tools/health` 请求
  2. `HealthController.Get` 处理请求 [API/Controllers/ToolsManagement/HealthController.cs:20]
  3. 返回健康状态
- **验收标准**:
  - [ ] AC1: 返回 `errorCode=0` 且响应包含健康状态
- **业务规则**:
  - BR-032: 该接口无需认证

#### 3.7.9. FR-030 获取微信Config [优先级: Should]

- **用户故事**: 作为已登录用户，我希望获取微信Config，以便进行微信相关操作。
- **主流程**:
  1. 用户发送 `GET /api/tools/wechat` 请求
  2. `WeChatController.Get` 处理请求 [API/Controllers/ToolsManagement/WeChat/WeChatController.cs:36]
  3. 返回微信Config信息
- **验收标准**:
  - [ ] AC1: 返回 `errorCode=0` 且响应包含微信Config
  - [ ] AC2: 未携带有效 JWT Token 时返回 `errorCode=UnAuthToken(100000)`
- **业务规则**:
  - BR-033: 微信Config包含 AppID 等信息

#### 3.7.10. FR-031 更新微信Config [优先级: Should]

- **用户故事**: 作为管理员，我希望更新微信Config，以便调整微信集成参数。
- **主流程**:
  1. 管理员发送 `POST /api/tools/wechat` 请求
  2. `WeChatController.Post` 处理请求 [API/Controllers/ToolsManagement/WeChat/WeChatController.cs:68]
  3. 更新微信Config
- **验收标准**:
  - [ ] AC1: 返回 `errorCode=0` 且微信Config更新成功
  - [ ] AC2: 未携带有效 JWT Token 时返回 `errorCode=UnAuthToken(100000)`
- **业务规则**:
  - BR-034: 仅管理员可更新微信Config

### 3.8. Alert管理 (AlertController)

本子章节包含 FR-032 至 FR-038，对应 `API/Controllers/UserManagement/AlertController.cs` 中的 7 个端点，负责AlertConfig的查询、创建、更新、删除以及Alert记录的读取与查询。

#### 3.8.1. FR-032 获取AlertConfig [优先级: Must]

- **用户故事**: 作为已登录用户，我希望获取AlertConfig列表或单个AlertConfig详情，以便查看Alert规则。
- **主流程**:
  1. 用户发送 `GET /api/alert/config` 请求，可选参数 `id`、`projectid`
  2. `AlertController.GetConfig` 处理请求 [API/Controllers/UserManagement/AlertController.cs:30]
  3. 返回AlertConfig列表或详情
- **验收标准**:
  - [ ] AC1: 返回 `errorCode=0` 且响应包含AlertConfig列表或详情
  - [ ] AC2: 若 `id` 指定且AlertConfig不存在，返回 `errorCode=AlertNotFound(160000)`
  - [ ] AC3: 未携带有效 JWT Token 时返回 `errorCode=UnAuthToken(100000)`
- **业务规则**:
  - BR-035: 仅返回当前用户有权访问的项目AlertConfig

#### 3.8.2. FR-033 获取Alert列表 [优先级: Must]

- **用户故事**: 作为已登录用户，我希望获取Alert列表，以便查看所有Alert规则。
- **主流程**:
  1. 用户发送 `GET /api/alert` 请求，参数 `projectid`、`page`、`pageSize`
  2. `AlertController.Get` 处理

---

## 4. 非功能需求

本章节定义 AgentAgentInsightService（统一保留英文） NFR，覆盖性能、可用性、安全、可扩展性、可维护性、可访问性、兼容性与本地化八个维度。所有指标均基于代码仓库中的真实Config项与实现推导，编号格式为 `NFR-{CATEGORY}-NNN`，共 20 条。这些需求为系统的架构设计、部署运维与质量保障提供量化基线，是验收测试与容量规划的依据。

### 4.1. 性能

性能需求确保系统在预期负载下提供稳定的响应时间与吞吐量。AgentAgentInsightService（统一保留英文） 的核心性能瓶颈集中在 ClickHouse 时序数据查询与 API 网关转发链路。

| 编号 | 需求描述 | 验收标准 | 来源依据 |
|------|---------|---------|---------|
| NFR-P-001 | ClickHouse Trace 查询 P95 延迟 < 2s | 在 100 万条 Trace 数据（统一术语）、10 并发查询条件下，P95 响应时间低于 2000ms | `API/Handlers/DataManagement/MetricsHandler.cs` 动态 SQL 构建含 CTE/JOIN/窗口函数，`ConnectionStrings.ClickHouseDbConnection` Config `CommandTimeout=60` |
| NFR-P-002 | API 响应时间 P99 < 500ms | 除 Trace 查询外的所有 API 端点，P99 响应时间低于 500ms | Controller 层经 `ApiHandlerBase` 统一处理，`API/Handlers/ApiHandlerBase.cs:1-20` |
| NFR-P-003 | Trace 数据（统一术语）写入吞吐 ≥ 1000 条/秒 | BullMQ 队列消费能力 ≥ 1000 条 Trace/秒，批量写入 ClickHouse | `API/Common/Services/BullMqService.cs:1-30` 基于 Redis + Lua 脚本实现批量出队 |
| NFR-P-004 | Payment回调处理延迟 < 3s | 微信/Payment宝回调从接收到订单状态更新完成，端到端延迟 < 3s | `API/Controllers/PaymentManagement/NotifyController.cs:29` 与 `API/Controllers/PaymentManagement/NotifyController.cs:57` |

entManagement/NotifyController.cs:29` 与 `API/Controllers/PaymentManagement/NotifyController.cs:57` |
| NFR-P-005 | 数据库连接池充足 | PostgreSQL 连接池 MaxPoolSize=200，ClickHouse MaxPoolSize=50，避免连接耗尽 | `ConnectionStrings.UserDbConnection`、`ConnectionStrings.DataDbConnection`、`ConnectionStrings.ClickHouseDbConnection` Config |

性能指标基于以下实现佐证：

- **ClickHouse 查询链路**：`MetricsHandler` 通过 `TraceFilterBuilder` 将前端过滤条件转换为 ClickHouse SQL WHERE 子句，支持动态 SQL 构建，包含 CTE、JOIN、窗口函数等高级查询，需注意超时与分页控制 [API/Handlers/DataManagement/MetricsHandler.cs:100-200]。连接字符串Config `CommandTimeout=60` 秒，`ConnectionTimeout=30` 秒，确保查询不会无限期阻塞。
- **API 响应链路**：用户请求流为 HTTP Request → YARP 路由 → Controller → Handler → Service → Repository → Database [API/System/Handlers/AgentInsightTransformProvider.cs:1-50]。`ApiHandlerBase` 统一注入用户上下文与数据库，减少重复初始化开销 [API/Handlers/ApiHandlerBase.cs:1-20]。
- **异步写入机制**：Trace 数据（统一术语）流通过 `EnqueueTraceIngestionAsync` 进入 BullMQ 队列，消费者批量写入 ClickHouse [API/Common/Services/BullMqService.cs:1-30]。Redis 连接串Config `localhost:${REDIS_PORT},password=${REDIS_AUTH}`，支持高吞吐队列操作。

### 4.2. 可用性

可用性需求保障系统在故障场景下的持续服务能力与数据最终一致性。

| 编号 | 需求描述 | 验收标准 | 来源依据 |
|------|---------|---------|---------|
| NFR-A-001 | 服务可用性 ≥ 99.5% | 月度停机时间 ≤ 3.6 小时，核心 API 端点健康检查通过率 ≥ 99.5% | `API/Controllers/ToolsManagement/HealthController.cs:20` 提供 `GET /api/tools/health` 健康检查端点 |
| NFR-A-002 | Payment回调重试机制保证最终一致性 | Payment回调处理失败后自动重试，直至订单状态最终一致；重试间隔递增，最大重试次数 ≥ 5 | `API/Notifications/PaymentTransactionNotification.cs:9` 定义 `TransactionType`，`PaymentTransactionSaveHandler` 通过 MediatR 异步持久化 [API/Notifications/PaymentTransactionSaveHandler.cs:10] |
| NFR-A-003 | 关键数据持久化与恢复 | PostgreSQL 与 ClickHouse 数据每日备份，RPO ≤ 24h，RTO ≤ 4h | `ConnectionStrings.UserDbConnection`、`ConnectionStrings.ClickHouseDbConnection` Config独立数据库实例 |
| NFR-A-004 | 优雅降级与熔断 | 当 ClickHouse 不可用时，Trace 查询接口返回明确错误码 `ClickHouseQueryError=150010`，不影响用户认证与Payment等核心链路 | `ExceptionCodes.ClickHouseQueryError = 150010` [Models/Common/Enums/ExceptionCodes.cs:6] |

可用性设计要点：

- **健康检查**：`HealthController` 提供 `GET /api/tools/health` 端点，供负载均衡器与监控系统定期探测 [API/Controllers/ToolsManagement/HealthController.cs:20]。
- **Payment回调最终一致性**：Payment回调流为 微信/Payment宝回调 → `NotifyHandler` 验签 → MediatR 发布 `PaymentTransactionNotification` → `PaymentTransactionSaveHandler` 持久化 → 更新订单状态 [API/Notifications/PaymentTransactionSaveHandler.cs:10]。异步解耦确保回调不因瞬时故障丢失，重试机制保证最终一致。
- **错误码分段**：`ExceptionCodes` 枚举按模块分段（User 100xxx、Org 130xxx、Project 140xxx、Payment 810xxx、Trace 150xxx、Alert 160xxx），便于快速定位故障模块 [Models/Common/Enums/ExceptionCodes.cs:6]。

### 4.3. 安全

安全需求覆盖身份认证、数据加密、Payment安全与访问控制，确保平台数据与交易安全。

| 编号 | 需求描述 | 验收标准 | 来源依据 |
|------|---------|---------|---------|
| NFR-S-001 | JWT 认证采用 HS256 算法，过期时间 43200 分钟（30 天），时钟偏差 5 分钟 | 未携带有效 Token 的请求返回 `UnAuthToken=100000`；Token 过期后拒绝访问 | `JWTSettings.Algorithm = HS256`、`JWTSettings.ExpiredTime = 43200`、`JWTSettings.ClockSkew = 5` [API/Program.cs] |
| NFR-S-002 | API Key 支持 Basic Auth 与 JWT 双模式认证 | 请求可通过 `Authorization: Basic base64(apiKey:secret)` 或 `Authorization: Bearer <JWT>` 访问受保护资源；无效凭据返回 `InvalidApiKey=100038` | `API/System/Handlers/AgentInsightTransformProvider.cs:50-100` 统一处理 Basic Auth / JWT 认证 |
| NFR-S-003 | 密码 AES 加密存储 | 用户密码不以明文存储，使用 AES 加密后入库；加密失败返回 `EncryptionFailed=990001` | `AESEncryptionKey = ${AES_KEY}` Config项；`ExceptionCodes.EncryptionFailed = 990001` |

ionFailed=990001` | `AESEncryptionKey = ${AES_KEY}` Config项；`ExceptionCodes.EncryptionFailed = 990001` |
| NFR-S-004 | Payment签名验证防篡改 | 微信/Payment宝回调必须通过签名验证，验签失败返回 `InvalidWeChatNotify=810010` 或 `AlipaySignatureError=810007`，拒绝处理伪造请求 | `API/Controllers/PaymentManagement/NotifyController.cs:29` 与 `API/Controllers/PaymentManagement/NotifyController.cs:57`；`ExceptionCodes.InvalidWeChatNotify = 810010` |
| NFR-S-005 | 敏感数据脱敏与审计 | 管理后台不展示明文敏感数据，所有关键操作（登录、下单、删除等）记录审计日志 | `AuditAction` 枚举定义 Create/Update/Delete/Login/Logout/Place/Notify 等审计动作 [Models/Common/Enums/AuditEnum.cs:3] |

安全实现细节：

- **JWT Config**：`JWTSettings.ValidateIssuer = True`、`JWTSettings.ValidateAudience = True`、`JWTSettings.ValidateIssuerSigningKey = True`、`JWTSettings.ValidateLifetime = True`，全面校验 Token 合法性 [API/Program.cs]。
- **API Key 双模式**：`AgentInsightTransformProvider` 作为 YARP 请求转换中间件，统一处理 Basic Auth 与 JWT 两种认证方式，并执行 API Key 验证与限流 [API/System/Handlers/AgentInsightTransformProvider.cs:50-100]。
- **Payment验签**：`PaymentService` 实现微信Payment（JSAPI/Native/MiniProgram）与Payment宝（即时到账）的签名验证逻辑，Payment金额单位转换（微信分为单位，`WeChatAmountUnit = 100`）在验签前完成 [API/Common/Services/PaymentService.cs:10]。
- **管理后台安全**：Django 管理后台要求 `DEBUG = False`（生产环境）、`CSRF_TRUSTED_ORIGINS` Config正确、`SECURE_PROXY_SSL_HEADER` Config正确，安全扫描无高危及以上漏洞 [Admin/Agents.md]。

### 4.4. 可扩展性

可扩展性需求确保系统能够通过水平扩展应对业务增长。

| 编号 | 需求描述 | 验收标准 | 来源依据 |
|------|---------|---------|---------|
| NFR-SC-001 | 支持水平扩展，通过 YARP 反向代理与数据库连接池实现 | API 服务可部署多个实例，YARP 负责路由分发；PostgreSQL 连接池 MinPoolSize=10、MaxPoolSize=200，ClickHouse PoolSize=10、MaxPoolSize=50 | `ReverseProxy.Routes.AgentInsight-Route-API.Match.Path = /api/public/{**catch-all}`；`ConnectionStrings.UserDbConnection`、`ConnectionStrings.ClickHouseDbConnection` |
| NFR-SC-002 | 无状态 API 设计，Session状态外置 Redis | API 实例不保存本地Session状态，用户Session通过 Redis 缓存，支持多设备登录 | `Redis.ConnectionString = localhost:${REDIS_PORT},password=${REDIS_AUTH}`；`API/Common/Services/UserService.cs:1-30` |
| NFR-SC-003 | 异步队列削峰填谷 | Trace 数据（统一术语）写入通过 BullMQ 队列异步处理，队列积压时不影响 API 响应 | `API/Common/Services/BullMqService.cs:1-30` 基于 Redis + Lua 脚本实现延迟作业、批量出队、作业确认 |

扩展性架构说明：

- **YARP 反向代理**：`AgentInsightTransformProvider` 实现 YARP 请求转换，将 `/api/public/` 和 `/public/` 路由转发到 Langfuse Service，同时承担认证与限流职责 [API/System/Handlers/AgentInsightTransformProvider.cs:1-50]。新增 API 实例只需注册到反向代理即可实现负载均衡。
- **连接池Config**：PostgreSQL 连接串Config `Pooling=true;MinPoolSize=10;MaxPoolSize=200;ConnectionLifetime=300`，ClickHouse Config `PoolSize=10;MaxPoolSize=50`，确保高并发下数据库连接不成为瓶颈 [ConnectionStrings Config]。
- **无状态设计**：用户Session通过 Redis 缓存管理，API 实例无本地状态，支持水平伸缩与滚动发布 [API/Common/Services/UserService.cs:1-30]。

### 4.5. 可维护性

可维护性需求确保代码结构清晰、错误可诊断、系统可Observation。

| 编号 | 需求描述 | 验收标准 | 来源依据 |
|------|---------|---------|---------|
| NFR-M-001 | 代码遵循 Furion 分层架构（Controller-Handler-Service-Repository） | 新增功能按 Controller → Handler → Service → Repository 分层实现，Handler 层继承 `ApiHandlerBase` | `API/Handlers/ApiHandlerBase.cs:1-20`；`API/Handlers/UserManagement/UserHandler.cs:1-50` |
| NFR-M-002 | 异常使用 ExceptionCodes 枚举，错误码分段清晰 | 所有业务异常通过 `Oops.Oh(ExceptionCodes.XXX)` 抛出，错误码按模块分段（User 100xxx、Payment 810xxx、Trace 150xxx、Alert 160xxx） | `Models/Common/Enums/ExceptionCodes.cs:6` 定义 43 个枚举、100+ 错误码 |
| NFR-M-003 | 日志分级与文件滚动 | 日志按级别分级输出，文件日志单文件上限 10MB，保留 30 个滚动文件 | `Logging.File.FileSizeLimitBytes = 10485760`、`Logging.File.MaxRollingFiles = 30`、`Logging.File.FileName = logs/application-.log` |
| NFR-M-004 | Config集中管理与环境隔离 | Config通过 `Configurations` 与 `Resources` 目录扫描加载，支持环境变量占位符（如 `${REDIS_PORT}`） | `ConfigurationScanDirectories = ['Configurations', 'Resources']`；`Redis.ConnectionString = localhost:${REDIS_PORT},password=${REDIS_AUTH}` |

可维护性实践：

- **分层架构**：`ApiHandlerBase` 统一注入用户上下文与数据库，Handler 层通过 `[FromKeyedServices]` 注入不同数据库客户端（UserDb/DataDb），Service 层封装业务逻辑，Repository 层通过 SqlSugar ORM 访问数据 [API/Handlers/ApiHandlerBase.cs:1-20]。
- **错误码体系**：`ExceptionCodes` 枚举覆盖用户管理、组织管理、项目管理、Payment、Trace 查询、Alert等全部业务模块，错误码数值分段清晰（如 100xxx User、130xxx Org、140xxx Project、150xxx Trace、160xxx Alert、810xxx Payment、990xxx 通用）[Models/Common/Enums/ExceptionCodes.cs:6]。
- **日志体系**：控制台日志默认级别 Warning，文件日志 MinimumLevel Information，SqlSugar 日志级别 Warning，避免 ORM 日志刷屏 [Logging Config]。

### 4.6. 可访问性

当前 AgentAgentInsightService（统一保留英文） 平台面向开发者与运维人员，主要交互方式为 API 调用与管理后台操作，暂无明确的 WCAG 无障碍合规要求。平台在可访问性方面的基本要求如下：

| 编号 | 需求描述 | 验收标准 | 来源依据 |
|------|---------|---------|---------|
| NFR-AC-001 | API 错误响应包含可读的错误信息 | 所有 API 错误响应包含 `errorCode` 数值与对应的人类可读消息，便于客户端展示与排查 | `ExceptionCodes` 枚举定义错误码与消息映射 [Models/Common/Enums/ExceptionCodes.cs:6] |
| NFR-AC-002 | 管理后台支持键盘导航与屏幕阅读器 | Django 管理后台基于 simpleui 框架，遵循 Django 默认无障碍标准 | `Admin/requirements.txt:1-10` 引入 Django + simpleui |

| Django 管理后台基于 simpleui 框架，遵循 Django 默认无障碍标准 | `Admin/requirements.txt:1-10` 引入 Django + simpleui |

说明：由于平台核心用户为技术开发者，通过 API 与 SDK 交互，可访问性需求以 API 错误信息的可读性为主。若未来面向非技术用户开放前端界面，需补充 WCAG 2.1 AA 级合规要求。

### 4.7. 兼容性

兼容性需求确保系统在不同运行环境与外部服务集成场景下的稳定运行。

| 编号 | 需求描述 | 验收标准 | 来源依据 |
|------|---------|---------|---------|
| NFR-C-001 | 支持 PostgreSQL 和 ClickHouse 作为数据库后端 | User/业务数据存储于 PostgreSQL，Trace/Observation 时序数据存储于 ClickHouse，两者通过独立连接串Config | `ConnectionStrings.UserDbConnection`、`ConnectionStrings.DataDbConnection`、`ConnectionStrings.ClickHouseDbConnection` |
| NFR-C-002 | 兼容微信Payment JSAPI/Native/MiniProgram 及Payment宝即时到账 | Payment模块支持 `SubPayMethod` 枚举定义的 4 种Payment方式：`WECHAT_JSAPI=1`、`WECHAT_NATIVE=2`、`WECHAT_MINIPROGRAM=3`、`ALIPAY_FAST_INSTANT_TRADE_PAY=11` | `Models/Common/Enums/PaymentEnums.cs:29`；`API/Common/Services/PaymentService.cs:1-50` |
| NFR-C-003 | 兼容 OpenAI Chat Completions API 协议 | AI Agent 服务提供 OpenAI 兼容的 `POST /api/agent/insight` 端点，支持流式响应 | `Agents/server.py:346` `chat_completions` 函数 |

服务提供 OpenAI 兼容的 `POST /api/agent/insight` 端点，支持流式响应 | `Agents/server.py:346` `chat_completions` 函数 |
| NFR-C-004 | 反向代理兼容 Langfuse 服务路由 | YARP 将 `/api/public/{**catch-all}` 与 `/public/{**catch-all}` 路由转发至 Langfuse Service | `ReverseProxy.Routes.AgentInsight-Route-API.Match.Path = /api/public/{**catch-all}`；`ReverseProxy.Routes.AgentInsight-Route-Public.Match.Path = /public/{**catch-all}` |

兼容性实现说明：

- **多数据库支持**：系统通过 SqlSugar ORM 的 `[FromKeyedServices]` 注入机制区分 UserDb 与 DataDb，`ModelHandler` 构造函数同时注入 `ISqlSugarClient db`（用户库）与 `ISqlSugarClient dataDb`（数据库）[API/Handlers/DataManagement/ModelHandler.cs:12-15]。ClickHouse 通过 `ClickHouseClient` 独立访问 [API/Handlers/DataManagement/MetricsHandler.cs:8]。
- **多渠道Payment**：`SubPayMethod` 枚举定义 4 种Payment子方式，`PaymentService` 根据Payment方式分发到微信或Payment宝 SDK，处理金额单位差异（微信分为单位，Payment宝为元）[API/Common/Services/PaymentService.cs:10]。
- **OpenAI 协议兼容**：Python AI Agent 服务基于 FastAPI 实现 OpenAI 兼容的 Chat Completions API，支持流式响应与多 Agent 路由 [Agents/server.py:346]。

### 4.8. 本地化

本地化需求确保系统支持多语言环境与区域文化差异。

| 编号 | 需求描述 | 验收标准 | 来源依据 |
|------|---------|---------|---------|
| NFR-L-001 | 支持 zh-CN、zh-TW、zh-HK、en 四种语言 | 系统界面与 API 错误消息可根据请求文化返回对应语言；本地化文件使用 JSON 格式 | `LocalizationSettings.SupportedCultures = ['zh-CN', 'zh-TW', 'zh-HK', 'en']`；`LocalizationSettings.LanguageFilePrefix = Text` |
| NFR-L-002 | 默认文化为 zh-CN | 未指定语言时，系统默认使用简体中文 | `LocalizationSettings.DefaultCulture = zh-CN` |
| NFR-L-003 | 时间格式与货币单位本地化 | 时间显示遵循区域文化格式；Payment金额单位转换（微信分/Payment宝元）在服务层处理 | `API/System/Handlers/FormattingHandler.cs` 中的 JSON 序列化定制；`API/Common/Services/PaymentService.cs:10` |

本地化实现说明：

- **多语言框架**：系统使用 `My.Extensions.Localization.Json` 实现 JSON 本地化文件加载，`LanguageFilePrefix = Text` 指定语言文件前缀 [LocalizationSettings Config]。`FormattingHandler` 定制 JSON 序列化，确保不同文化下的时间与数字格式正确 [API/System/Handlers/FormattingHandler.cs]。
- **默认文化**：`DefaultCulture = zh-CN` 确保未指定 `Accept-Language` 头时返回简体中文内容 [LocalizationSettings Config]。
- **区域差异处理**：Payment金额单位差异（微信Payment以分为单位，Payment宝以元为单位）在 `PaymentService` 中通过 `WeChatAmountUnit = 100` 常量进行转换，避免金额计算错误 [API/Common/Services/PaymentService.cs:10]。

---

## 5. 接口需求

### 5.1. 内部接口

内部接口定义 AgentAgentInsightService（统一保留英文） 内部各模块之间的通信需求，包括 API 与 ClickHouse 的查询接口、Redis 缓存接口、BullMQ 队列作业接口、Agent Insight 服务与 API 之间的 HTTP 调用，以及通过 MediatR 通知解耦的异步事件。

#### 5.1.1. ClickHouse 查询接口

API 通过 `ClickHouseClient` 与 ClickHouse 数据库交互，用于 Trace 数据（统一术语）、Observation数据及Score数据的查询与写入。查询支持动态 SQL 构建，包含 CTE、JOIN、窗口函数等高级查询，需注意超时与分页控制。相关实现位于 [API/Handlers/DataManagement/MetricsHandler.cs:100-200]。

#### 5.1.2. Redis 缓存接口

Redis 用于缓存用户Session、Captcha、Config等数据。用户Session通过 Redis 缓存，支持多设备登录，并限制最大Session数。相关实现位于 [API/Common/Services/UserService.cs:1-30]。

#### 5.1.3. BullMQ 队列作业接口

BullMQ 队列用于异步任务处理，如 Trace 数据（统一术语）写入、项目删除等。队列类型由 `QueueType` 枚举定义，包括 `Audit = 0`、`ExceptionRecord = 1`、`UsageTracking = 2`、`PerformanceRecord = 3` [Entities/Common/Enums/QueueEnum.cs:3]。`AgentInsightTransformProvider` 调用 `BullMqService` 实现 Trace 数据（统一术语）入队 [API/System/Handlers/AgentInsightTransformProvider.cs:8]。

| 方法 | 功能 | 说明 |
|------|------|------|
| `EnqueueTraceIngestionAsync` | 入队 Trace 数据（统一术语）写入任务 | Agent SDK 上报 Trace 后异步写入 ClickHouse |
| `AcknowledgeTraceIngestionAsync` | 确认 Trace 写入完成 | 消费者处理完成后调用 |
| `EnqueueProjectDeleteAsync` | 入队项目删除任务 | 异步清理项目关联数据 |

#### 5.1.4. Agent Insight 服务与 API 之间的 HTTP 调用

Python 实现的 AI Agent Service（`Agents/server.py`）提供 OpenAI 兼容的 Chat Completions API，端点 `POST /api/agent/insight` 由 `chat_completions` 函数处理 [Agents/server.py:346]。该服务还提供Session管理端点：`GET /api/sessions`、`GET /api/sessions/{session_id}`、`DELETE /api/sessions/{session_id}`、`POST /api/sessions/cleanup`、`GET /api/agents` [Agents/server.py:614-649]。API 服务通过 HTTP 调用该服务，请求格式遵循 OpenAI Chat Completions 规范，支持流式响应与Session持久化。鉴权方式为内部网络调用，通过 API Key 或 JWT 认证；超时与重试策略需在 API 服务中Config，建议设置合理的超时时间（如 30 秒）并实现指数退避重试。

#### 5.1.5. MediatR 通知解耦

内部异步事件通过 MediatR 的 `INotification` / `INotificationHandler` 机制解耦。`PaymentTransactionNotification` 定义 `TransactionType` 枚举（`WeChatTransaction`、`AlipayTransaction`），Payment回调验签通过后发布该通知，由 `PaymentTransactionSaveHandler` 持久化交易记录并更新订单状态 [API/Notifications/PaymentTransactionNotification.cs:9]。Alert触发同样通过 `AlertTriggeredNotification` 解耦，由 `SystemAlertHandler` 与 `SMSAlertHandler` 分别处理系统通知与短信通知。

#### 5.1.6. 接口依赖关系

内部接口的依赖关系从 `dependencies` 列表提取，例如 `PaymentService` 调用微信/Payment宝 SDK，`AlertService` 调用短信服务。这些依赖关系在接口设计中需明确，确保模块间解耦。

### 5.2. 外部接口

外部接口定义 AgentAgentInsightService（统一保留英文） 与第三方服务之间的通信需求，包括微信Payment API、Payment宝Payment API、短信服务接口、Kuaidi100 物流接口及 MobPush 推送接口。所有外部接口需明确请求格式、鉴权方式、重试与超时策略。

#### 5.2.1. 微信Payment API

微信Payment集成于 `PaymentService`，支持 JSAPI、Native、小程序三种Payment方式（`SubPayMethod`：`WECHAT_JSAPI = 1`、`WECHAT_NATIVE = 2`、`WECHAT_MINIPROGRAM = 3`）[Models/Common/Enums/PaymentEnums.cs:29]。Payment金额单位为分，常量 `WeChatAmountUnit = 100` [API/Common/Services/PaymentService.cs:10]。

**下单接口**：`OrderController.Place` 接收 `AgentInsightOrderBody`，调用 `PaymentService` 创建订单并调用微信统一下单 API [API/Controllers/PaymentManagement/OrderController.cs:48]。下单接口限流为 1 次/10 秒。请求格式为 HTTPS + JSON，包含商户号、订单号、金额、Payment方式等字段；响应包含 `prepayid`、`appid`、`timestamp`、`noncestr`、`package`、`signtype`、`paysign` 等字段。

**查询接口**：`OrderController.Query` 根据订单号查询Payment状态，限流 1 次/1 秒 [API/Controllers/PaymentManagement/OrderController.cs:64]。查询失败抛出 `WeChatQueryErrorResponse = 810024`。

**回调接口**：`NotifyController.WeChatNotify` 接收微信Payment回调通知 [API/Controllers/PaymentManagement/NotifyController.cs:29]。回调处理流程：
1. 读取请求体，空请求抛出 `FakedWeChatRequest = 620014`
2. 调用 `ExamineWeChatRequest` 验签
3. 反序列化为 `WeChatNotify` 对象
4. 调用 `ProcessWeChatNotify` 处理业务逻辑
5. 返回 `WXSuccessResult()` 或 `WXFailResult("FAIL")`

**鉴权方式**：微信Payment API 使用商户证书（API 证书）进行双向 TLS 认证，回调验签使用微信Payment平台证书公钥（RSA 签名验证）。Config缺失时抛出 `WeChatSettingNotConfig = 810001`，证书无效抛出 `InvalidPayCertificate = 620016`。

**重试与超时策略**：微信Payment API 调用超时通过 `CancellationToken` 控制（`Furion.App.HttpContext?.RequestAborted`），响应为空抛出 `WeChatEmptyResponse = 810021`，响应错误抛出 `WeChatErrorResponse = 810022`。无自动重试，失败抛出错误码；回调接口返回 `FAIL` 后微信Payment侧会进行重试。

#### 5.2.2. Payment宝Payment API

Payment宝Payment集成于 `PaymentService`，使用 `AlipaySDKNet.Standard` SDK，支持电脑网站Payment（`SubPayMethod.ALIPAY_FAST_INSTANT_TRADE_PAY = 11`）[Models/Common/Enums/PaymentEnums.cs:29]。Payment宝金额单位为元，与微信Payment的分单位不同，需注意转换。

**下单接口**：`OrderController.Place` 中 `PayMethod = 2`（Alipay）时调用Payment宝下单 API。请求格式为 HTTPS + Form（或 JSON），包含订单号、金额、商品描述等字段。下单失败抛出 `AlipayPlaceOrderError = 810020`。

**回调接口**：`NotifyController.AlipayNotify` 接收Payment宝异步通知 [API/Controllers/PaymentManagement/NotifyController.cs:57]。处理流程：
1. 调用 `ProcessAlipayNotify` 验签并处理业务
2. 成功返回字符串 `"success"`，失败返回 `"fail"`

**鉴权方式**：Payment宝使用 RSA2 签名算法，通过 `AlipaySignature.RSACheckV1` 验签。签名错误抛出 `AlipaySignatureError = 810007`，签名参数错误抛出 `AlipaySignDictionaryError = 810008`。Config缺失抛出 `AlipaySettingNotConfig = 810002`，连接失败抛出 `AlipayConnectionError = 810003`，交易错误抛出 `AlipayTradeError = 810004`。

**重试与超时策略**：Payment宝 API 调用超时通过 `CancellationToken` 控制，无自动重试，失败抛出错误码；回调接口返回 `fail` 后Payment宝侧会进行重试。

#### 5.2.3. 短信服务接口

短信服务用于Captcha发送与Alert通知，AliyunTencentCloud两种实例，由 `SMSInstance` 枚举定义 [Entities/Common/Settings/SMSSetting.cs:35]。`AlertService` 在Alert触发时通过 `SMSAlertHandler` 调用短信服务发送通知。

**Captcha发送**：`CaptchaController.GetSMSCaptcha` 提供短信Captcha获取接口 [API/Controllers/UserManagement/CaptchaController.cs:43]。Captcha长度 6 位（`CaptchaSetting.SMSCodeLength = 6`），有效期 300 秒（`CaptchaSetting.ExpiredSeconds = 300`），重发间隔 60 秒（`CaptchaSetting.ResendInterval = 60`）。发送过于频繁抛出 `SendSMSTooOften = 110000`，发送失败抛出 `FailedToSendSMS = 110001`。

**Alert通知**：`AlertNotifyBy` 枚举定义通知方式，`SMS = 2` 表示通过短信发送 [Models/Common/Enums/AlertEnum.cs:39]。

**请求格式与鉴权**：使用 HTTPS + JSON，鉴权方式为 AccessKey/SecretKey（阿里云）或 SecretId/SecretKey（腾讯云）。超时策略使用 SDK 默认超时，无自动重试，失败抛出错误码。

#### 5.2.4. Kuaidi100 物流接口

Kuaidi100 物流接口用于快递查询，相关错误码定义于 `ExceptionCodes`：`Kuaidi100NotConfig = 610006`（未Config）、`Kuaidi100Error = 610007`（查询错误）。该接口在系统Config物流查询功能时使用，需Config Kuaidi100 的商户密钥与客户标识。请求格式为 HTTPS + JSON，鉴权方式为商户 Key 签名，超时策略使用默认 HTTP 超时，无自动重试，失败抛出错误码。

#### 5.2.5. MobPush 推送接口

MobPush 推送接口用于移动端消息推送，相关错误码定义于 `ExceptionCodes`：`MobPushNotConfig = 610008`（未Config）。该接口在系统需要向移动端推送通知时使用，需Config MobPush 的 AppKey 与 AppSecret。请求格式为 HTTPS + JSON，鉴权方式为 AppKey/AppSecret，超时策略使用默认 HTTP 超时，无自动重试，失败抛出错误码。

#### 5.2.6. 外部接口汇总

| 接口 | 协议 | 鉴权方式 | 超时策略 | 重试策略 |
|------|------|----------|----------|----------|
| 微信Payment下单/查询 | HTTPS + JSON | 商户证书（双向 TLS） | 通过 `CancellationToken` 控制 | 无自动重试，失败抛出错误码 |
| 微信Payment回调 | HTTPS + JSON | 微信PaymentRSA | 同步处理 | 返回 `FAIL` 后微信侧重试 |
| Payment宝下单 | HTTPS + JSON | RSA2 签名 | 通过 `CancellationToken` 控制 | 无自动重试，失败抛出错误码 |
| Payment宝回调 | HTTPS + Form | RSA2 验签 | 同步处理 | 返回 `fail` 后Payment宝侧重试 |
| 短信服务（Aliyun/TencentCloud） | HTTPS + JSON | AccessKey/SecretKey | 默认 SDK 超时 | 无自动重试，失败抛出错误码 |
| Kuaidi100 物流 | HTTPS + JSON | 商户 Key 签名 | 默认 HTTP 超时 | 无自动重试，失败抛出错误码 |
| MobPush 推送 | HTTPS + JSON | AppKey/AppSecret | 默认 HTTP 超时 | 无自动重试，失败抛出错误码 |

---

## 6. 数据需求

| 实体 | 所属域 | 存储位置 | 说明 |
|------|--------|----------|------|
| User | 用户管理 | PostgreSQL (UserDb) | 用户注册信息、登录凭证、微信绑定、API Key、角色分配 |
| Organization | 用户管理 | PostgreSQL (UserDb) | 组织信息、成员管理、配额限制（成员数/项目数） |
| Project | 用户管理 | PostgreSQL (UserDb) | 项目信息，归属于 Organization，用于 Trace 数据（统一术语）隔离 |
| Alert | Alert管理 | PostgreSQL (UserDb) | Alert规则Config（字段、操作符、阈值、通知方式） |
| Order | Payment管理 | PostgreSQL (DataDb) | 订单信息，包含金额、Payment方式、状态流转 |
| Product | Payment管理 | PostgreSQL (DataDb) | 产品定义（如套餐、时长） |
| Bulletin | 工具管理 | PostgreSQL (DataDb) | Bulletin、协议、版本修订记录 |
| AgentConfig | Agent 管理 | PostgreSQL (UserDb) | Agent Config信息 |
| AgentSession | Agent 管理 | PostgreSQL (UserDb) | Agent Session记录 |
| AgentReportTemplate | Agent 管理 | PostgreSQL (UserDb) | 报告模板，支持预定义模板与用户自定义模板 |

用户与业务数据通过 SqlSugar ORM 访问，Handler 层通过 `ApiHandlerBase` 统一注入用户上下文与数据库实例。`AgentReportHandler` 中展示了基于 SqlSugar 的查询模式，通过 `Db.Queryable<AgentReportTemplate>()` 构建类型安全查询，并支持按 `UserId` 区分预定义模板（`UserId == null`）与用户自定义模板 [API/Handlers/AgentManagement/AgentReportHandler.cs:20-50]。

serId` 区分预定义模板（`UserId == null`）与用户自定义模板 [API/Handlers/AgentManagement/AgentReportHandler.cs:20-50]。

#### 6.1.1. Trace 相关数据实体

Trace 数据（统一术语）是平台可Observation性能力的核心，包含以下实体：

| 实体 | 说明 | 存储位置 |
|------|------|----------|
| Trace | 一次完整的 Agent 调用链，包含 ID、名称、时间戳、Org/项目归属 | ClickHouse |
| Observation | Trace 下的具体ObservationSpan，包含输入/输出 Token、成本、延迟、模型名称等 | ClickHouse |
| Score | 对 Trace 或 Observation 的Score数据 | ClickHouse |

Trace 数据（统一术语）的查询通过 `MetricsHandler` 实现，其依赖 `TraceFilterBuilder` 将前端过滤条件转换为 ClickHouse SQL WHERE 子句 [API/Handlers/DataManagement/MetricsHandler.cs:5]，并通过 `ClickHouseClient` 执行查询 [API/Handlers/DataManagement/MetricsHandler.cs:8]。`TraceFilterBuilder` 支持多种数据类型（DateTime、String、Number、StringOptions、ArrayOptions、Boolean、Null）和操作符（GreaterThan、Contains、AnyOf、IsNull 等），对应 `FilterType` 和 `FilterOperator` 枚举定义 [Models/Common/Enums/FilterEnum.cs:8-38]。可过滤的列涵盖 Id、Name、Timestamp、Latency、Token 数、Cost、Level、ModelNames、ScoresAvg 等 25 个字段 [Models/Common/Enums/FilterEnum.cs:40-64]。

、Latency、Token 数、Cost、Level、ModelNames、ScoresAvg 等 25 个字段 [Models/Common/Enums/FilterEnum.cs:40-64]。

`AlertMetricsHandler` 通过 Trace ID 批量查询Alert指标，使用 `AgentInsightConst.MaxBatchSize` 分批处理，并调用 `ClickHouseHelper.BuildInParams` 构建 IN 子句参数 [API/Handlers/DataManagement/AlertMetricsHandler.cs:20-40]。查询失败时抛出 `ExceptionCodes.ClickHouseQueryError`（150010）[Models/Common/Enums/ExceptionCodes.cs:6]。

### 6.2. 数据存储

#### 6.2.1. 存储策略总览

AgentAgentInsightService（统一保留英文） 采用多存储引擎混合架构，根据数据特性选择最优存储方案：

| 存储引擎 | 用途 | 连接Config |
|----------|------|----------|
| PostgreSQL (UserDb) | User、Org、Project、Alert规则、Agent Config/Session/报告模板 | `UserDbConnection` |
| PostgreSQL (DataDb) | Order、Product、Bulletin等业务数据 | `DataDbConnection` |
| PostgreSQL (TrackingDb) | Trace相关数据 | `TrackingDbConnection` |
| ClickHouse | Trace、Observation、Score 时序数据 | `ClickHouseDbConnection` |
| Redis | Session状态缓存、限流、BullMQ 作业队列 | `Redis.ConnectionString` |

#### 6.2.2. PostgreSQL 连接Config

连接字符串定义在 `API/appsettings.json` 及环境特定Config文件中。生产环境（`API/appsettings.json`）Config如下 [API/appsettings.json]：

```
UserDbConnection: PORT=${USER_DB_PORT};DATABASE=${USER_DB_NAME};HOST=${USER_DB_HOST};PASSWORD=${USER_DB_PASSWORD};USER ID=${USER_DB_USER};Timeout=30;Pooling=true;MinPoolSize=10;MaxPoolSize=200;ConnectionLifetime=300;CommandTimeout=30;
DataDbConnection: PORT=${DATA_DB_PORT};DATABASE=${DATA_DB_NAME};HOST=${DATA_DB_HOST};PASSWORD=${DATA_DB_PASSWORD};USER ID=${DATA_DB_USER};Timeout=30;Pooling=true;MinPoolSize=10;MaxPoolSize=200;ConnectionLifetime=300;CommandTimeout=30;
TrackingDbConnection: PORT=${TRACKING_DB_PORT};DATABASE=${TRACKING_DB_NAME};HOST=${TRACKING_DB_HOST};PASSWORD=${TRACKING_DB_PASSWORD};USER ID=${TRACKING_DB_USER};Timeout=30;Pooling=true;MinPoolSize=10;MaxPoolSize=200;ConnectionLifetime=300;CommandTimeout=30;
```

Timeout=30;Pooling=true;MinPoolSize=10;MaxPoolSize=200;ConnectionLifetime=300;CommandTimeout=30;
```

开发环境（`API/appsettings.Development.json`）使用 `localhost` 作为数据库主机，连接池规模较小（MinPoolSize=5, MaxPoolSize=100），QA 环境（`API/appsettings.QA.json`）使用 `postgres` 主机名，连接池规模与生产一致（MinPoolSize=10, MaxPoolSize=200）[API/appsettings.Development.json][API/appsettings.QA.json]。连接池Config通过 `Pooling=true` 启用，`ConnectionLifetime=300` 控制连接最大存活时间（秒），`CommandTimeout=30` 设置命令超时。

数据库实例通过依赖注入按 key 区分，`AgentInsightConst.KeyedService_UserDb`、`AgentInsightConst.KeyedService_DataDb`、`AgentInsightConst.KeyedService_ClickHouseDb` 分别对应不同存储 [API/Handlers/DataManagement/AlertMetricsHandler.cs:10-15]。

#### 6.2.3. ClickHouse 连接Config

ClickHouse 用于存储 Trace 时序数据，连接Config如下 [API/appsettings.json]：

```
ClickHouseDbConnection: Host=${CLICKHOUSE_HOST};Port=${CLICKHOUSE_PORT};Username=${CLICKHOUSE_USER};Password=${CLICKHOUSE_PASSWORD};Database=${CLICKHOUSE_DB};PoolSize=10;MaxPoolSize=50;ConnectionTimeout=30;CommandTimeout=60
```

报 Trace → BullMQ 队列入队 (EnqueueTraceIngestionAsync) → 消费者出队 → ClickHouse 写入 → MetricsHandler 查询展示
```

1. **入队阶段**：Agent SDK 上报的 Trace 数据（统一术语）通过 `BullMqService.EnqueueTraceIngestionAsync` 进入 BullMQ 队列 [API/Common/Services/BullMqService.cs:1-30]。`AgentInsightTransformProvider` 作为 YARP 请求转换组件，统一处理请求并调用 BullMqService 入队 [API/System/Handlers/AgentInsightTransformProvider.cs:8]。

2. **消费与写入阶段**：后台消费者从队列出队（`AcknowledgeTraceIngestionAsync` 确认处理完成），将 Trace 数据（统一术语）写入 ClickHouse。

3. **查询展示阶段**：`MetricsController` 提供以下查询端点 [API/Controllers/DataManagement/MetricsController.cs:34-125]：
   - `GET /api/data/metrics/observations`：根据 Trace ID 获取 Observations 列表，支持分页
   - `GET /api/data/metrics/scores`：根据 Trace ID 获取 Scores 列表，支持分页
   - `GET /api/data/metrics/traces`：根据 Trace ID 批量获取指标详情（Token 数、成本、延迟、模型名称）
   - `POST /api/data/metrics/traces`：分页查询 Trace 列表，支持按 ID、名称、时间范围及自定义条件过滤

获取指标详情（Token 数、成本、延迟、模型名称）
   - `POST /api/data/metrics/traces`：分页查询 Trace 列表，支持按 ID、名称、时间范围及自定义条件过滤

查询时 `MetricsHandler` 调用 `TraceFilterBuilder` 将前端过滤条件（`filter` 数组，包含 type/column/operator/value）转换为 ClickHouse SQL WHERE 子句 [API/Common/Helpers/TraceFilterBuilder.cs]，并支持 `orderby` 排序参数（如 `timestamp.desc`）。

#### 6.2.4. Payment回调数据流

Payment回调涉及微信/Payment宝异步通知，数据流如下：

```
微信/Payment宝回调 → NotifyController 接收 → PaymentService 验签 → MediatR 发布 PaymentTransactionNotification → PaymentTransactionSaveHandler 持久化 → 更新订单状态
```

1. **回调接收**：`NotifyController` 提供 `POST /api/payment/notify/wechatnotify` 和 `POST /api/payment/notify/alipaynotify` 两个端点接收Payment平台回调 [API/Controllers/PaymentManagement/NotifyController.cs:29-57]。

2. **验签与通知**：`NotifyHandler` 调用 `PaymentService` 进行签名验证 [API/Handlers/PaymentManagement/NotifyHandler.cs:10]，验证通过后通过 MediatR 发布 `PaymentTransactionNotification` [API/Notifications/PaymentTransactionNotification.cs:9]，该通知包含 `TransactionType` 枚举（WeChatTransaction / AlipayTransaction）区分Payment渠道。

ansactionNotification.cs:9]，该通知包含 `TransactionType` 枚举（WeChatTransaction / AlipayTransaction）区分Payment渠道。

3. **持久化**：`PaymentTransactionSaveHandler` 作为 `INotificationHandler` 异步处理通知，调用 `PaymentService` 持久化交易记录并更新订单状态 [API/Notifications/PaymentTransactionSaveHandler.cs:10]。

#### 6.2.5. Alert数据流

Alert系统基于 Trace 指标进行条件评估，数据流如下：

```
定时 Job 查询 Trace Metric → AlertService 评估条件 → 触发 AlertTriggeredNotification → SystemAlertHandler/SMSAlertHandler 发送通知
```

1. **指标查询**：定时 Job 通过 `AlertMetricsHandler.GetAlertMetrics` 按 Trace ID 批量查询指标数据 [API/Handlers/DataManagement/AlertMetricsHandler.cs:20-40]，使用 `AlertMetricsConst.AlertMetricsSql` 定义的 SQL 模板。

lers/DataManagement/AlertMetricsHandler.cs:20-40]，使用 `AlertMetricsConst.AlertMetricsSql` 定义的 SQL 模板。

2. **条件评估**：`AlertService` 调用 `IAlertFieldEvaluator` 策略接口评估Alert条件 [API/Common/Services/AlertService.cs:5]，支持 `AlertField` 枚举定义的 9 种指标字段（TotalTokens、TotalCost、ErrorCount、Latency、ErrorRate、InputTokens、OutputTokens、WarningCount、ObservationCount）[Models/Common/Enums/AlertEnum.cs:20-31]，以及 `AlertOperator` 枚举定义的 6 种比较操作符（GreaterThan、LessThan、EqualTo、GreaterThanOrEqualTo、LessThanOrEqualTo、NotEqualTo）[Models/Common/Enums/AlertEnum.cs:10-18]。

3. **通知发送**：条件满足时触发 `AlertTriggeredNotification`，`SystemAlertHandler` 和 `SMSAlertHandler` 分别处理系统通知和短信通知，对应 `AlertNotifyBy` 枚举（System=1, SMS=2）[Models/Common/Enums/AlertEnum.cs:39-41]。Alert记录状态通过 `AlertRecordState` 枚举管理（Active=1, Read=2）[Models/Common/Enums/AlertEnum.cs:33-36]。

---

## 7. 约束条件

AgentAgentInsightService（统一保留英文） 是一个面向 AI Agent 可Observation性与管理的后端平台，采用 monorepo 架构，包含 8 个子项目，核心能力涵盖用户与组织管理（统一）、Payment集成（微信/Payment宝）、Trace 数据（统一术语）查询与Alert、Agent Config与Session管理，以及一个 Python 实现的 AI Agent Service。本章从技术、业务、合规三个维度阐述系统设计与运行过程中必须遵守的约束条件，这些约束直接决定了系统的架构选型、功能边界与安全基线。

### 7.1. 技术约束

AgentAgentInsightService（统一保留英文） 的技术栈选型与架构模式在系统设计之初即已确定，后续开发与运维必须严格遵守以下技术约束。

**后端框架与 ORM 约束。** .NET 后端必须基于 Furion 框架构建，使用 SqlSugar ORM 作为数据访问层。Furion 框架承载了依赖注入、AOP、友好异常处理（`Furion.FriendlyException`）等核心能力，所有 Controller 均继承自 `ApiControllerBase`，Handler 层通过 `ApiHandlerBase` 统一注入用户上下文与数据库实例 [API/Handlers/ApiHandlerBase.cs:1-20]。SqlSugar ORM 负责与 PostgreSQL 数据库交互，通过 `ISqlSugarClient` 接口执行查询与持久化操作，例如 `PaymentService` 中通过 `_db.Queryable<AgentInsightOrder>()` 查询订单数据 [API/Common/Services/PaymentService.cs:1-30]。禁止绕过 Furion 框架直接使用原生 ADO.NET 或引入其他 ORM 框架。

r>()` 查询订单数据 [API/Common/Services/PaymentService.cs:1-30]。禁止绕过 Furion 框架直接使用原生 ADO.NET 或引入其他 ORM 框架。

**Python Agent 服务约束。** AI Agent 服务必须使用 Python 3.12 运行时，基于 FastAPI + LangChain + LangGraph 构建，依赖 OpenAI SDK 实现模型调用 [Agents/pyproject.toml:3-20]。该服务提供 OpenAI 兼容的 Chat Completions API（`POST /api/agent/insight`），支持流式响应与多 Agent 路由 [Agents/server.py:346]。Python 服务与 .NET 后端之间通过 HTTP 协议通信，禁止引入额外的消息中间件作为两者之间的同步调用通道。

**反向代理路由约束。** 系统必须通过 YARP 反向代理将 `/api/public/{**catch-all}` 和 `/public/{**catch-all}` 路径的请求转发至 Langfuse Service（目标地址 `http://localhost:3000/`），该路由Config在 `ReverseProxy.Routes` 中定义，分别对应 `AgentInsight-Route-API` 与 `AgentInsight-Route-Public` 两条路由规则。所有外部请求进入系统后，首先经过 YARP 路由层，由 `AgentInsightTransformProvider` 统一处理 Basic Auth / JWT 认证、API Key 验证与限流逻辑 [API/System/Handlers/AgentInsightTransformProvider.cs:1-50]。禁止绕过 YARP 直接暴露内部服务端口。

认证、API Key 验证与限流逻辑 [API/System/Handlers/AgentInsightTransformProvider.cs:1-50]。禁止绕过 YARP 直接暴露内部服务端口。

**Payment模块加密库约束。** Payment模块依赖 BouncyCastle.Cryptography 加密库实现微信Payment回调验签与证书解析。微信Payment通知处理流程中，`NotifyHandler.ExamineWeChatRequest` 负责验签，若验签失败则抛出 `FakedWeChatRequest` 异常（errorCode=620014）[API/Controllers/PaymentManagement/NotifyController.cs:29-55]。Payment宝Payment依赖 AlipaySDKNet.Standard 完成签名与验签，禁止使用其他加密库替代。

**数据存储约束。** 系统采用多数据库架构：PostgreSQL 存储用户、Org、订单等业务数据（通过 `UserDbConnection`、`DataDbConnection`、`TrackingDbConnection` 三个连接字符串区分）；ClickHouse 存储 Trace/Observation 时序数据，连接Config包含 `PoolSize=10;MaxPoolSize=50;ConnectionTimeout=30;CommandTimeout=60` 等参数。Redis 作为缓存与队列中间件，连接字符串格式为 `localhost:${REDIS_PORT},password=${REDIS_AUTH}`。各数据库连接参数均通过环境变量注入，禁止硬编码。

### 7.2. 业务约束

业务约束定义了系统在用户角色、资源配额、Payment金额、Agent 配额等方面的业务规则边界，是产品功能实现与验收的核心依据。

**用户角色约束。** 用户角色遵循 PGRole 枚举定义，包含 VIEWER、MEMBER、ADMIN、OWNER 四种角色。角色分配遵循以下规则：OWNER不能修改自身Privilege，否则抛出 `OwnerCannotModifySelfRole` 异常（errorCode=100039）；不能授予高于自身角色的Privilege，否则抛出 `CannotGrantHigherRole` 异常（errorCode=100023）。用户邀请流程中，被邀请人手机号必须格式正确，否则抛出 `InvalidInviteMobile` 异常（errorCode=100022）；同一用户不能重复加入组织，否则抛出 `UserAlreadyOrgMember` 异常（errorCode=100024）。上述错误码定义于 `ExceptionCodes` 枚举 [Models/Common/Enums/ExceptionCodes.cs:6]，错误消息文案在 `API/Resources/Text.zh-CN.json` 中维护。

**组织与项目配额约束。** 组织内用户数受产品定义的 `headcountlimit` 字段限制，当组织成员数达到上限时，邀请新成员操作抛出 `ExceedHeadCountLimit` 异常（errorCode=130010）。组织内项目数受 `projectlimit` 字段限制，超出时抛出 `ExceedProjectLimit` 异常（errorCode=130011）。产品定义中，`AgentInsightProduct` 实体包含 `projectlimit`、`headcountlimit`、`orglimit`、`agentlimit` 等配额字段，由 `ProductController` 提供查询接口 [API/Controllers/ProductManagement/ProductController.cs:26-36]。删除组织时，若组织下仍有项目，抛出 `OrganizationHasProjects` 异常（errorCode=130007）；若项目正在删除中，抛出 `OrganizationProjectDeleting` 异常（errorCode=130008）。

ionHasProjects` 异常（errorCode=130007）；若项目正在删除中，抛出 `OrganizationProjectDeleting` 异常（errorCode=130008）。

**Payment金额单位约束。** 微信Payment金额单位为分，`PaymentService` 中定义常量 `WeChatAmountUnit = 100` 用于元与分之间的换算 [API/Common/Services/PaymentService.cs:10]。Payment宝Payment金额单位为元，两者在订单创建与回调处理中必须严格区分，禁止混用。订单创建时，`CreateOrder` 方法根据产品价格、数量与折扣计算 `TotalAmount`，初始状态为 `TradeState.NOTPAY`、`OrderState.Created` [API/Common/Services/PaymentService.cs:40-60]。若订单金额校验失败，抛出 `InvalidTotalAmount` 异常（errorCode=810025）。

**Agent 月度配额约束。** Agent 月度配额通过 `DeductMonthlyAgentRate` 接口扣减，对应 `GET /api/user/privilege/agent/deduct` 端点 [API/Controllers/UserManagement/UserController.cs:242]。配额校验通过 `ValidateMonthlyAgentRate` 接口执行，对应 `GET /api/user/privilege/agent/validate` 端点 [API/Controllers/UserManagement/UserController.cs:258]。当 Agent 配额不足时，抛出 `AgentLimitExceeded` 异常（errorCode=150007）。Agent 配额扣减失败时，抛出 `UpdateAgentRateFailed` 异常（errorCode=150020）。配额扣减操作必须与订单Payment成功回调联动，确保先Payment后扣减的时序一致性。

### 7.3. 合规约束

合规约束聚焦于数据安全、密钥管理、传输加密与隐私保护，是系统通过安全审计与合规检查的必要条件。

**密码加密约束。** 用户密码必须使用 AES 加密算法进行加密存储，加密密钥从环境变量 `${AES_KEY}` 读取，禁止在代码或Config文件中硬编码密钥。若加密操作失败，抛出 `EncryptionFailed` 异常（errorCode=990001）；解密失败抛出 `DecryptionFailed` 异常（errorCode=990002）；密码哈希失败抛出 `PasswordHashFailed` 异常（errorCode=990003）。上述错误码定义于 `ExceptionCodes` 枚举 [Models/Common/Enums/ExceptionCodes.cs:6]。

**JWT 签名密钥约束。** JWT 签名密钥从环境变量 `${JWT_SIGNING_KEY}` 读取，签名算法固定为 HS256，过期时间为 43200 分钟（30 天），时钟偏差为 5 分钟。JWT Config还包含 `ValidIssuer`（从 `${JWT_ISSUER}` 读取）、`ValidAudience`（从 `${JWT_AUDIENCE}` 读取），并启用 `ValidateIssuer`、`ValidateAudience`、`ValidateIssuerSigningKey`、`ValidateLifetime` 四项校验。禁止将 JWT 签名密钥提交至代码仓库或日志系统。

uer`、`ValidateAudience`、`ValidateIssuerSigningKey`、`ValidateLifetime` 四项校验。禁止将 JWT 签名密钥提交至代码仓库或日志系统。

**Payment数据传输加密约束。** Payment相关数据传输必须使用 HTTPS 加密通道。微信Payment回调接口 `POST /api/payment/notify/wechatnotify` 与Payment宝回调接口 `POST /api/payment/notify/alipaynotify` 均标记为 `[AllowAnonymous]`，但必须通过服务端验签确保请求来源可信 [API/Controllers/PaymentManagement/NotifyController.cs:29-57]。微信Payment通知若验签失败，抛出 `FakedWeChatRequest` 异常（errorCode=620014）；证书不匹配抛出 `InvalidPayCertificate` 异常（errorCode=620016）；通知解密失败抛出 `InvalidWeChatNotify` 异常（errorCode=810010）。Payment宝签名验证失败抛出 `AlipaySignatureError` 异常（errorCode=810007）。

**用户隐私数据脱敏约束。** 用户手机号、邮箱等隐私数据在日志输出、管理后台展示、API 响应中必须进行脱敏处理。管理后台（Django + simpleui）的安全设计必须覆盖 OWASP Top 10 风险，敏感数据必须有脱敏方案 [Admin/Agents.md]。系统支持多语言（zh-CN、zh-TW、zh-HK、en），错误消息通过 `API/Resources/Text.zh-CN.json` 等资源文件管理，禁止在代码中硬编码用户可见的错误文案。用户Session通过 Redis 缓存管理，支持多设备登录，但需遵循最大Session数限制 [API/Common/Services/UserService.cs:1-30]。

---

## 8. 错误码定义

通用错误码覆盖用户认证、注册、登录、API Key 管理、邀请机制等基础用户链路。该分段错误码在 `UserController`、`UserService` 及 `ApiControllerBase` 中被广泛引用，是平台最核心的错误码集合。

| 错误码 | 常量名 | 描述与触发场景 |
|--------|--------|----------------|
| 100000 | `UnAuthToken` | 请求未携带有效 Token 或 Token 已过期，认证失败 |
| 100001 | `EmptyUserId` | 请求上下文中缺少用户 ID，无法识别当前用户 |
| 100003 | `ExistedMobile` | 用户注册时手机号已存在，重复注册 |
| 100004 | `CreateUserFailed` | 用户创建失败，数据库写入异常或参数不合法 |
| 100005 | `InvalidUser` | 用户不存在或已被禁用，`ApiControllerBase.GetUserAsync()` 中缓存未命中时抛出 |
| 100009 | `EmptyMobile` | 注册或绑定操作中手机号为空，`UserService.CreateNewUser()` 入口校验 |
| 100010 | `UnauthorizedOperator` | 当前操作者无Privilege执行该操作，角色Privilege不足 |
| 100019 | `UserNameTooLong` | 用户名长度超过 100 字符上限 |
| 100021 | `EmptyInviteMobile` | 邀请成员时手机号为空 |
| 100022 | `InvalidInviteMobile` | 邀请的手机号格式不合法 |
| 100023 | `CannotGrantHigherRole` | 不能授予高于自身等级的角色，Privilege越权保护 |
| 100024 | `UserAlreadyOrgMember` | 被邀请用户已是组织成员，重复加入 |
| 100025 | `InviteAlreadyExists` | 邀请记录已存在，重复邀请 |
| 100026 | `CreateInviteFailed` | 邀请创建失败 |
| 100027 | `InviteNotFound` | 邀请记录不存在或已被撤销 |
| 100028 | `DeleteInviteFailed` | 邀请删除失败 |
| 100031 | `ApiKeyNotFound` | API Key 不存在或已被删除 |

| 100032 | `CreateApiKeyFailed` | API Key 创建失败 |
| 100033 | `DeleteApiKeyFailed` | API Key 删除失败 |
| 100035 | `MissingProjectOrOrgId` | 请求中缺少项目 ID 或组织 ID 参数 |
| 100036 | `ApiKeySecretNotFound` | API Key 对应的 Secret 不存在 |
| 100037 | `InvalidCredentials` | 登录凭证（手机号/密码）错误 |
| 100038 | `InvalidApiKey` | API Key 无效或已失效 |
| 100039 | `OwnerCannotModifySelfRole` | Org Owner 不能修改自己的角色 |
| 100040 | `ResetPasswordFailed` | 密码重置失败 |
| 100041 | `UserNotInitialized` | 用户未完成初始化流程 |

**典型触发链路**：用户注册接口 `POST /api/user` 调用 `UserController.Create()`，内部委托 `UserService.CreateNewUser()` 校验手机号是否为空，随后查询手机号是否已注册，若存在则抛出 `Oops.Oh(ExceptionCodes.ExistedMobile)`，该异常由全局异常中间件捕获后返回 `errorCode=100003` 给前端。

### 8.1. Captcha/短信 (110xxx)

Captcha与短信错误码覆盖图形Captcha、短信Captcha、邮件Captcha的获取与校验流程。相关逻辑位于 `CaptchaController` 与 `CaptchaService` 中。

| 错误码 | 常量名 | 描述与触发场景 |
|--------|--------|----------------|
| 110000 | `SendSMSTooOften` | 短信发送过于频繁，未超过重发间隔 |
| 110001 | `FailedToSendSMS` | 短信发送失败，短信服务商返回错误 |
| 110002 | `EmptyCaptcha` | Captcha为空，用户未输入Captcha |
| 110003 | `InvalidCaptcha` | Captcha错误或已过期，与缓存中的Captcha不匹配 |
| 110004 | `ErrorCaptcha` | Captcha校验过程发生异常 |
| 110005 | `FailedToSendEmail` | 邮件Captcha发送失败 |

**典型触发链路**：`GET /api/captcha/sms` 接口获取短信Captcha时，`CaptchaService` 先检查该手机号在缓存中是否已有未过期的Captcha记录，若存在且未超过重发间隔则抛出 `SendSMSTooOften`；发送成功后Captcha存入缓存并设置过期时间。用户提交Captcha时，若与缓存值不匹配则抛出 `InvalidCaptcha`。

### 8.2. Org (130xxx)

组织错误码覆盖组织的创建、更新、删除、成员管理及配额校验。相关逻辑位于 `OrganizationController`（`POST /api/user/organization`、`POST /api/user/organization/update`、`POST /api/user/organization/delete`）。

| 错误码 | 常量名 | 描述与触发场景 |
|--------|--------|----------------|
| 130000 | `EmptyOrganizationName` | 组织名称为空 |
| 130001 | `OrganizationNameTooShort` | 组织名称长度不足 |
| 130002 | `OrganizationNameTooLong` | 组织名称长度超限 |
| 130003 | `InvalidOrganization` | 组织不存在或已被删除 |
| 130004 | `CreateOrganizationFailed` | 组织创建失败 |
| 130005 | `UpdateOrganizationFailed` | 组织更新失败 |
| 130006 | `DeleteOrganizationFailed` | 组织删除失败 |
| 130007 | `OrganizationHasProjects` | 组织下存在项目，禁止直接删除组织 |
| 130008 | `OrganizationProjectDeleting` | 组织下的项目正在删除中，需等待完成 |
| 130009 | `UnauthorizedOrganizationAccess` | 当前用户无权访问该组织 |
| 130010 | `ExceedHeadCountLimit` | 组织成员数量超过套餐上限 |
| 130011 | `ExceedProjectLimit` | 组织下项目数量超过套餐上限 |
| 130012 | `ExceedOrgLimit` | 用户可创建的组织数量超过上限 |
| 130013 | `OrgAlreadyHasOwner` | 组织已存在 Owner，不能重复设置 |

 130012 | `ExceedOrgLimit` | 用户可创建的组织数量超过上限 |
| 130013 | `OrgAlreadyHasOwner` | 组织已存在 Owner，不能重复设置 |

**典型触发链路**：创建组织时，`OrganizationController` 先校验组织名称非空且长度在合法范围内，然后检查当前用户创建的组织数量是否达到上限（`ExceedOrgLimit`），最后执行数据库插入，失败时抛出 `CreateOrganizationFailed`。删除组织时，若组织下存在项目则抛出 `OrganizationHasProjects` 阻止删除。

### 8.3. Project (140xxx)

项目错误码覆盖项目的创建、更新、删除、重名校验及Privilege控制。相关逻辑位于 `ProjectController`（`POST /api/user/project`、`POST /api/user/project/update`、`POST /api/user/project/delete`）。

| 错误码 | 常量名 | 描述与触发场景 |
|--------|--------|----------------|
| 140000 | `EmptyProjectName` | 项目名称为空 |
| 140001 | `ProjectNameTooShort` | 项目名称长度不足 |
| 140002 | `ProjectNameTooLong` | 项目名称长度超限 |
| 140003 | `InvalidProject` | 项目不存在或已被删除 |
| 140004 | `CreateProjectFailed` | 项目创建失败 |
| 140005 | `UpdateProjectFailed` | 项目更新失败 |
| 140006 | `DeleteProjectFailed` | 项目删除失败 |
| 140007 | `ExistedProjectName` | 同一组织下项目名称已存在，重复命名 |
| 140008 | `UnauthorizedProjectAccess` | 当前用户无权访问该项目 |

 | `ExistedProjectName` | 同一组织下项目名称已存在，重复命名 |
| 140008 | `UnauthorizedProjectAccess` | 当前用户无权访问该项目 |

**典型触发链路**：创建项目时，`ProjectController` 校验项目名称非空且长度合法，随后在同一组织范围内查询是否已存在同名项目，若存在则抛出 `ExistedProjectName`。项目删除通过 BullMQ 异步队列执行，`BullMqService.EnqueueProjectDeleteAsync` 将删除任务入队后异步处理。

### 8.4. Agent/Trace (150xxx)

Agent/Trace 错误码覆盖 Agent Config管理、Trace 数据（统一术语）查询、ClickHouse 查询异常及过滤条件校验。相关逻辑位于 `MetricsController`、`AgentConfigController` 与 `TraceFilterBuilder` 中。

| 错误码 | 常量名 | 描述与触发场景 |
|--------|--------|----------------|
| 150000 | `EmptyProjectId` | 查询 Trace 时项目 ID 为空 |
| 150004 | `AgentSettingNotConfig` | Agent 设置未Config |
| 150007 | `AgentLimitExceeded` | Agent 数量超过配额限制 |
| 150008 | `DuplicateUserConfig` | 用户Config重复 |
| 150009 | `EmptyTraceIds` | Trace ID 列表为空 |
| 150010 | `ClickHouseQueryError` | ClickHouse 查询执行出错，`MetricsHandler` 捕获非超时异常后抛出 |
| 150011 | `TooManyTraceIds` | Trace ID 数量超过单次查询上限 |
| 150012 | `InvalidFilterType` | 过滤条件类型不合法 |
| 150013 | `InvalidFilterColumn` | 过滤列名不合法 |
| 150014 | `InvalidFilterOperator` | 过滤操作符不合法 |
| 150015 | `InvalidFilterValue` | 过滤值不合法 |
| 150016 | `InvalidOrderBy` | 排序字段不合法 |
| 150017 | `ClickHouseQueryTimeout` | ClickHouse 查询超时，`IsTimeoutException()` 判断为超时后抛出 |
| 150018 | `EmptyTraceId` | Trace ID 为空，`GetObservationsAsync` 与 `GetScoresAsync` 入口校验 |
| 150019 | `OrgAndProjectBothEmpty` | Org ID 和项目 ID 同时为空 |
| 150020 | `UpdateAgentRateFailed` | Agent 配额扣减失败 |
| 150021 | `AgentSessionNotFound` | Agent Session不存在 |

| 150022 | `AgentConfigNotFound` | Agent Config不存在 |
| 150023 | `AgentReportTemplateNotFound` | Agent 报告模板不存在 |
| 150024 | `EmptyAgentReportTemplateName` | Agent 报告模板名称为空 |

**典型触发链路**：`GET /api/data/metrics/observations` 接口调用 `MetricsController.GetObservations()`，首先校验 `traceId` 是否为空，为空则抛出 `EmptyTraceId`；查询 ClickHouse 时若发生异常，先判断是否为超时异常，超时抛出 `ClickHouseQueryTimeout`，其他异常抛出 `ClickHouseQueryError` 并携带异常消息。

### 8.5. Alert (160xxx)

Alert错误码覆盖Alert规则的创建、更新、删除、参数校验及Privilege控制。相关逻辑位于 `AlertController`（`POST /api/alert`、`POST /api/alert/update`、`POST /api/alert/delete`）。

及Privilege控制。相关逻辑位于 `AlertController`（`POST /api/alert`、`POST /api/alert/update`、`POST /api/alert/delete`）。

| 错误码 | 常量名 | 描述与触发场景 |
|--------|--------|----------------|
| 160000 | `AlertNotFound` | Alert规则不存在或已被删除 |
| 160001 | `CreateAlertFailed` | Alert规则创建失败 |
| 160002 | `UpdateAlertFailed` | Alert规则更新失败 |
| 160003 | `DeleteAlertFailed` | Alert规则删除失败 |
| 160004 | `InvalidAlertPeriod` | Alert统计周期不合法，`AlertTimeUnit` 枚举值非法 |
| 160005 | `InvalidAlertFrequency` | Alert评估频率不合法 |
| 160006 | `InvalidAlertField` | Alert指标字段不合法，`AlertField` 枚举值非法 |
| 160007 | `InvalidAlertOperator` | Alert操作符不合法，`AlertOperator` 枚举值非法 |
| 160008 | `InvalidAlertValue` | Alert阈值不合法 |
| 160010 | `InvalidAlertName` | Alert名称为空 |
| 160011 | `InvalidAlertNotifyBy` | 通知方式不合法，`AlertNotifyBy` 枚举值非法 |
| 160012 | `SubscribeAlertFailed` | 订阅Alert失败 |
| 160013 | `AlertOrgNotAccessible` | 当前用户无权访问Alert所属组织 |
| 160014 | `AlertProjectNotFound` | Alert关联的项目不存在 |
| 160015 | `AlertNameTooLong` | Alert名称长度超限 |

Alert所属组织 |
| 160014 | `AlertProjectNotFound` | Alert关联的项目不存在 |
| 160015 | `AlertNameTooLong` | Alert名称长度超限 |

**典型触发链路**：创建Alert时，`AlertController.Create()` 依次校验Alert名称非空且长度合法、统计周期（`periodunit`）与评估频率（`frequencyunit`）的枚举值合法、指标字段（`field`）与操作符（`operator`）合法、阈值（`value`）合法，任一校验失败即抛出对应错误码。随后校验当前用户对目标组织与项目的访问Privilege，最后执行数据库插入。

### 8.6. 微信 (620xxx)

微信错误码覆盖微信登录、绑定、消息推送、签名校验等场景。相关逻辑位于 `WeChatController`（`GET /api/tools/wechat`、`POST /api/tools/wechat`、`POST /api/user/bind/wechat`、`GET /api/user/unbind/wechat`）。

/tools/wechat`、`POST /api/tools/wechat`、`POST /api/user/bind/wechat`、`GET /api/user/unbind/wechat`）。

| 错误码 | 常量名 | 描述与触发场景 |
|--------|--------|----------------|
| 620001 | `InvalidWeChatAppToken` | 微信 App Token 无效 |
| 620002 | `ExamineWeChatSignatureFailed` | 微信签名校验失败 |
| 620003 | `GetWeChatTokenFailed` | 获取微信 Access Token 失败 |
| 620004 | `GetWeChatBasicUserInfoFailed` | 获取微信基础用户信息失败 |
| 620005 | `InvalidWeChatMessageType` | 微信消息类型不合法 |
| 620006 | `InvalidWeChatMessageEvent` | 微信消息事件不合法 |
| 620007 | `EmptyWeChatOpenId` | 微信 OpenId 为空 |
| 620008 | `InvalidWeChatCode` | 微信授权 Code 无效或已过期 |
| 620009 | `WeChatAccountBinded` | 当前用户已绑定微信账号，重复绑定 |
| 620010 | `WeChatAccountBeenBinded` | 该微信账号已被其他用户绑定 |
| 620011 | `WeChatAccountNotBinded` | 当前用户未绑定微信账号 |
| 620012 | `InvalidWeChatAccount` | 微信账号无效 |
| 620013 | `MobileBindedWeChatAccount` | 该手机号已绑定其他微信账号 |
| 620014 | `FakedWeChatRequest` | 伪造的微信请求，签名校验未通过 |
| 620016 | `InvalidPayCertificate` | Payment证书无效 |
| 620017 | `GetPayCertificateFailed` | 获取Payment证书失败 |

通过 |
| 620016 | `InvalidPayCertificate` | Payment证书无效 |
| 620017 | `GetPayCertificateFailed` | 获取Payment证书失败 |

**典型触发链路**：用户绑定微信时，`UserController.Bind()` 先校验微信授权 Code 的有效性，无效则抛出 `InvalidWeChatCode`；随后校验该微信 OpenId 是否已被其他用户绑定，若已绑定则抛出 `WeChatAccountBeenBinded`；同时校验当前用户是否已绑定微信，若已绑定则抛出 `WeChatAccountBinded`。

### 8.7. Payment (810xxx)

Payment错误码覆盖微信Payment、Payment宝Payment、订单管理、产品管理等场景。相关逻辑位于 `OrderController`、`NotifyController` 与Payment服务中。

| 错误码 | 常量名 | 描述与触发场景 |
|--------|--------|----------------|
| 810001 | `WeChatSettingNotConfig` | 微信PaymentConfig缺失 |
| 810002 | `AlipaySettingNotConfig` | Payment宝PaymentConfig缺失 |
| 810003 | `AlipayConnectionError` | Payment宝连接异常 |
| 810004 | `AlipayTradeError` | Payment宝交易异常 |
| 810005 | `InvalidAlipayTradeNo` | Payment宝交易号无效 |
| 810006 | `InvalidAlipayTransaction` | Payment宝交易记录无效 |
| 810007 | `AlipaySignatureError` | Payment宝签名校验失败 |
| 810008 | `AlipaySignDictionaryError` | Payment宝签名参数字典错误 |
| 810009 | `InvalidWeChatSerialNO` | 微信证书序列号无效 |
| 810010 | `InvalidWeChatNotify` | 微信Payment回调通知无效 |
| 810011 | `EmptyOrderNo` | 订单号为空 |
| 810012 | `DoNotOwnOrganization` | 当前用户不拥有该组织 |
| 810013 | `ProductNotExist` | 产品不存在 |
| 810014 | `ProductDurationNotExist` | 产品时长规格不存在 |
| 810015 | `OrderNotExist` | 订单不存在 |
| 810016 | `EmptyWeChatTransaction` | 微信交易记录为空 |
| 810017 | `InvalidWeChatTradeNo` | 微信交易号无效 |
| 810018 | `EmptyWeChatNotify` | 微信回调通知内容为空 |
| 810019 | `UnsupportedPayMethod` | 不支持的Payment方式，`SubPayMethod` 枚举值非法 |

| 810020 | `AlipayPlaceOrderError` | Payment宝下单失败 |
| 810021 | `WeChatEmptyResponse` | 微信Payment返回空响应 |
| 810022 | `WeChatErrorResponse` | 微信Payment返回错误响应 |
| 810023 | `CannotDowngradeProduct` | 不能降级产品套餐 |
| 810024 | `WeChatQueryErrorResponse` | 微信Payment查询返回错误 |
| 810025 | `InvalidTotalAmount` | Payment金额不合法 |
| 810026 | `OrderStateUpdateFailed` | 订单状态更新失败 |
| 810027 | `InvalidMerchant` | 商户号无效 |

**典型触发链路**：下单接口 `POST /api/payment/order` 调用 `OrderController.Place()`，先校验订单号非空（`EmptyOrderNo`），再校验产品存在（`ProductNotExist`）与时长规格存在（`ProductDurationNotExist`），随后校验Payment方式是否受支持（`UnsupportedPayMethod`），最后调用Payment服务发起微信或Payment宝Payment。Payment回调接口 `POST /api/payment/notify/wechatnotify` 由 `NotifyController.WeChatNotify` 处理，验签失败时抛出 `InvalidWeChatNotify` 或 `AlipaySignatureError`。

### 8.8. 加密/系统 (990xxx)

加密与系统错误码覆盖数据加密解密、密码哈希、作业队列等基础设施异常。

| 错误码 | 常量名 | 描述与触发场景 |
|--------|--------|----------------|
| 990001 | `EncryptionFailed` | 数据加密失败，AES 加密异常 |
| 990002 | `DecryptionFailed` | 数据解密失败，AES 解密异常 |
| 990003 | `PasswordHashFailed` | 密码哈希计算失败 |
| 990004 | `InvalidJobQuantity` | 作业队列数量参数不合法 |
| 999999 | `DefaultException` | 未分类的默认异常，兜底错误码 |

**典型触发链路**：用户密码存储时，`UserService` 调用加密服务对密码进行哈希处理，若哈希算法执行异常则抛出 `PasswordHashFailed`。敏感字段加密使用Config的密钥，加密或解密过程中发生异常时分别抛出 `EncryptionFailed` 与 `DecryptionFailed`。BullMQ 作业队列入队时，若作业数量参数非法则抛出 `InvalidJobQuantity`。所有未被业务代码显式捕获的异常，最终由全局异常中间件的兜底分支处理，返回 HTTP 500 与默认错误消息。

---

## 9. 需求Trace矩阵

本章节为 AgentAgentInsightService（统一保留英文）（面向 AI Agent 可Observation性与管理的后端平台）提供需求Trace矩阵，FRNFR到具体代码实现之间的双向可追溯映射。该矩阵确保每一项需求均可通过对应的 Controller 方法、Handler 服务或Config项进行验证，为需求验收、变更影响分析和回归测试提供依据。

### 9.1. FR Trace

FR映射到具体的 Controller 方法、Handler 服务及代码位置。映射依据为 HTTP 端点全集（AST 结构感知扫描）与关键模块清单，确保每个 FR 均可通过实际代码路径进行Trace与验证。

| 需求 ID | 需求描述 | Controller 方法 | Handler Service | 代码位置 |
|---------|---------|----------------|--------------|---------|
| FR-001 | 获取当前用户的 Agent Config | `AgentConfigController.Get` | `AgentConfigHandler.GetConfig` | [API/Controllers/AgentManagement/AgentConfigController.cs:28](API/Controllers/AgentManagement/AgentConfigController.cs:28) |
| FR-002 | 创建或更新 Agent Config | `AgentConfigController.Post` | `AgentConfigHandler.CreateOrUpdateConfig` | [API/Controllers/AgentManagement/AgentConfigController.cs:54](API/Controllers/AgentManagement/AgentConfigController.cs:54) |
| FR-003 | 删除当前用户的 Agent Config | `AgentConfigController.Delete` | `AgentConfigHandler.DeleteConfig` | [API/Controllers/AgentManagement/AgentConfigController.cs:40](API/Controllers/AgentManagement/AgentConfigController.cs:40) |

nagement/AgentConfigController.cs:40](API/Controllers/AgentManagement/AgentConfigController.cs:40) |
| FR-004 | 获取 Agent 报表模板列表或单个模板详情 | `AgentReportController.GetTemplates` | `AgentReportHandler.GetTemplates` | [API/Controllers/AgentManagement/AgentReportController.cs:35](API/Controllers/AgentManagement/AgentReportController.cs:35) |
| FR-005 | 创建或更新 Agent 报表模板 | `AgentReportController.CreateOrUpdateTemplate` | `AgentReportHandler.CreateOrUpdateTemplate` | [API/Controllers/AgentManagement/AgentReportController.cs:62](API/Controllers/AgentManagement/AgentReportController.cs:62) |
| FR-006 | 删除 Agent 报表模板 | `AgentReportController.DeleteTemplates` | `AgentReportHandler.DeleteTemplates` | [API/Controllers/AgentManagement/AgentReportController.cs:48](API/Controllers/AgentManagement/AgentReportController.cs:48) |

nagement/AgentReportController.cs:48](API/Controllers/AgentManagement/AgentReportController.cs:48) |
| FR-007 | 获取 Trace 数据（统一术语）列表 | `MetricsController.GetTraces` | `MetricsHandler`（经 `TraceFilterBuilder` 构建过滤条件） | [API/Controllers/DataManagement/MetricsController.cs:64](API/Controllers/DataManagement/MetricsController.cs:64) |
| FR-008 | 获取 Observation 数据（统一术语）列表 | `MetricsController.GetObservations` | `MetricsHandler`（经 `TraceFilterBuilder` 构建过滤条件） | [API/Controllers/DataManagement/MetricsController.cs:34](API/Controllers/DataManagement/MetricsController.cs:34) |
| FR-009 | 获取 Score 数据列表 | `MetricsController.GetScores` | `MetricsHandler`（经 `TraceFilterBuilder` 构建过滤条件） | [API/Controllers/DataManagement/MetricsController.cs:50](API/Controllers/DataManagement/MetricsController.cs:50) |
| FR-010 | 获取模型列表 | `ModelController.Get` | `ModelHandler.GetModels` | [API/Controllers/DataManagement/ModelController.cs:34](API/Controllers/DataManagement/ModelController.cs:34) |

ollers/DataManagement/ModelController.cs:34](API/Controllers/DataManagement/ModelController.cs:34) |
| FR-011 | 创建Payment订单 | `OrderController.Place` | `OrderHandler` → `PaymentService` | [API/Controllers/PaymentManagement/OrderController.cs:48](API/Controllers/PaymentManagement/OrderController.cs:48) |
| FR-012 | 查询Payment订单状态 | `OrderController.Query` | `OrderHandler` → `PaymentService` | [API/Controllers/PaymentManagement/OrderController.cs:64](API/Controllers/PaymentManagement/OrderController.cs:64) |
| FR-013 | 处理微信Payment回调 | `NotifyController.WeChatNotify` | `NotifyHandler` → `PaymentService`（验签） | [API/Controllers/PaymentManagement/NotifyController.cs:29](API/Controllers/PaymentManagement/NotifyController.cs:29) |
| FR-014 | 处理Payment宝Payment回调 | `NotifyController.AlipayNotify` | `NotifyHandler` → `PaymentService`（验签） | [API/Controllers/PaymentManagement/NotifyController.cs:57](API/Controllers/PaymentManagement/NotifyController.cs:57) |

aymentManagement/NotifyController.cs:57](API/Controllers/PaymentManagement/NotifyController.cs:57) |
| FR-015 | 获取产品列表 | `ProductController.Get` | `ProductHandler.GetProducts` | [API/Controllers/ProductManagement/ProductController.cs:26](API/Controllers/ProductManagement/ProductController.cs:26) |
| FR-016 | 获取产品时长列表 | `ProductController.GetDuration` | `ProductHandler.GetProductDurations` | [API/Controllers/ProductManagement/ProductController.cs:38](API/Controllers/ProductManagement/ProductController.cs:38) |
| FR-017 | 用户注册 | `UserController.Create` | `UserHandler` → `UserService` | [API/Controllers/UserManagement/UserController.cs:43](API/Controllers/UserManagement/UserController.cs:43) |
| FR-018 | 用户登录 | `UserController.Login` | `UserHandler` → `UserService` | [API/Controllers/UserManagement/UserController.cs:73](API/Controllers/UserManagement/UserController.cs:73) |

trollers/UserManagement/UserController.cs:73](API/Controllers/UserManagement/UserController.cs:73) |
| FR-019 | 用户登出 | `UserController.Logout` | `UserHandler` → `UserService` | [API/Controllers/UserManagement/UserController.cs:88](API/Controllers/UserManagement/UserController.cs:88) |
| FR-020 | 重置密码 | `UserController.ResetPassword` | `UserHandler` → `UserService` | [API/Controllers/UserManagement/UserController.cs:102](API/Controllers/UserManagement/UserController.cs:102) |
| FR-021 | 绑定微信账号 | `UserController.Bind` | `UserHandler` → `WeChatService` | [API/Controllers/UserManagement/UserController.cs:117](API/Controllers/UserManagement/UserController.cs:117) |
| FR-022 | 解绑微信账号 | `UserController.UnBind` | `UserHandler` → `WeChatService` | [API/Controllers/UserManagement/UserController.cs:132](API/Controllers/UserManagement/UserController.cs:132) |

ollers/UserManagement/UserController.cs:132](API/Controllers/UserManagement/UserController.cs:132) |
| FR-023 | 分配用户角色 | `UserController.AssignRole` | `UserHandler` → `UserService` | [API/Controllers/UserManagement/UserController.cs:147](API/Controllers/UserManagement/UserController.cs:147) |
| FR-024 | 邀请用户加入组织 | `UserController.Invite` | `UserHandler` → `UserService` | [API/Controllers/UserManagement/UserController.cs:162](API/Controllers/UserManagement/UserController.cs:162) |
| FR-025 | 创建 API Key | `UserController.CreateApiKey` | `UserHandler` → `UserService` | [API/Controllers/UserManagement/UserController.cs:209](API/Controllers/UserManagement/UserController.cs:209) |
| FR-026 | 删除 API Key | `UserController.DeleteApiKey` | `UserHandler` → `UserService` | [API/Controllers/UserManagement/UserController.cs:272](API/Controllers/UserManagement/UserController.cs:272) |

ollers/UserManagement/UserController.cs:272](API/Controllers/UserManagement/UserController.cs:272) |
| FR-027 | 扣减月度 Agent 配额 | `UserController.DeductMonthlyAgentRate` | `UserHandler` → `UserService` | [API/Controllers/UserManagement/UserController.cs:242](API/Controllers/UserManagement/UserController.cs:242) |
| FR-028 | 校验月度 Agent 配额 | `UserController.ValidateMonthlyAgentRate` | `UserHandler` → `UserService` | [API/Controllers/UserManagement/UserController.cs:258](API/Controllers/UserManagement/UserController.cs:258) |
| FR-029 | 创建组织 | `OrganizationController.Post` | `OrganizationHandler` | [API/Controllers/UserManagement/OrganizationController.cs:28](API/Controllers/UserManagement/OrganizationController.cs:28) |
| FR-030 | 更新组织 | `OrganizationController.Update` | `OrganizationHandler` | [API/Controllers/UserManagement/OrganizationController.cs:56](API/Controllers/UserManagement/OrganizationController.cs:56) |

agement/OrganizationController.cs:56](API/Controllers/UserManagement/OrganizationController.cs:56) |
| FR-031 | 删除组织 | `OrganizationController.Delete` | `OrganizationHandler` | [API/Controllers/UserManagement/OrganizationController.cs:71](API/Controllers/UserManagement/OrganizationController.cs:71) |
| FR-032 | 创建项目 | `ProjectController.Create` | `ProjectHandler` | [API/Controllers/UserManagement/ProjectController.cs:31](API/Controllers/UserManagement/ProjectController.cs:31) |
| FR-033 | 更新项目 | `ProjectController.Update` | `ProjectHandler` | [API/Controllers/UserManagement/ProjectController.cs:60](API/Controllers/UserManagement/ProjectController.cs:60) |
| FR-034 | 删除项目 | `ProjectController.Delete` | `ProjectHandler`（经 `BullMqService.EnqueueProjectDeleteAsync` 异步处理） | [API/Controllers/UserManagement/ProjectController.cs:75](API/Controllers/UserManagement/ProjectController.cs:75) |

rs/UserManagement/ProjectController.cs:75](API/Controllers/UserManagement/ProjectController.cs:75) |
| FR-035 | 获取用户Config项 | `UserConfigController.Get` | `UserConfigHandler.Get` | [API/Controllers/UserManagement/UserConfigController.cs:31](API/Controllers/UserManagement/UserConfigController.cs:31) |
| FR-036 | 创建用户Config | `UserConfigController.Post` | `UserConfigHandler.Create` | [API/Controllers/UserManagement/UserConfigController.cs:44](API/Controllers/UserManagement/UserConfigController.cs:44) |
| FR-037 | 更新用户Config | `UserConfigController.Update` | `UserConfigHandler.Update` | [API/Controllers/UserManagement/UserConfigController.cs:57](API/Controllers/UserManagement/UserConfigController.cs:57) |
| FR-038 | 删除用户Config | `UserConfigController.Delete` | `UserConfigHandler.Delete` | [API/Controllers/UserManagement/UserConfigController.cs:71](API/Controllers/UserManagement/UserConfigController.cs:71) |

rManagement/UserConfigController.cs:71](API/Controllers/UserManagement/UserConfigController.cs:71) |
| FR-039 | 创建Alert规则 | `AlertController.Create` | `AlertHandler` → `AlertService` | [API/Controllers/UserManagement/AlertController.cs:61](API/Controllers/UserManagement/AlertController.cs:61) |
| FR-040 | 更新Alert规则 | `AlertController.Update` | `AlertHandler` → `AlertService` | [API/Controllers/UserManagement/AlertController.cs:75](API/Controllers/UserManagement/AlertController.cs:75) |
| FR-041 | 删除Alert规则 | `AlertController.Delete` | `AlertHandler` → `AlertService` | [API/Controllers/UserManagement/AlertController.cs:90](API/Controllers/UserManagement/AlertController.cs:90) |
| FR-042 | 获取Alert记录 | `AlertController.GetRecords` | `AlertHandler` → `AlertService` | [API/Controllers/UserManagement/AlertController.cs:128](API/Controllers/UserManagement/AlertController.cs:128) |

lers/UserManagement/AlertController.cs:128](API/Controllers/UserManagement/AlertController.cs:128) |
| FR-043 | 标记Alert记录为已读 | `AlertController.ReadRecords` | `AlertHandler` → `AlertService` | [API/Controllers/UserManagement/AlertController.cs:108](API/Controllers/UserManagement/AlertController.cs:108) |
| FR-044 | 获取图形Captcha | `CaptchaController.Get` | `CaptchaHandler` | [API/Controllers/UserManagement/CaptchaController.cs:29](API/Controllers/UserManagement/CaptchaController.cs:29) |
| FR-045 | 获取短信Captcha | `CaptchaController.GetSMSCaptcha` | `CaptchaHandler` | [API/Controllers/UserManagement/CaptchaController.cs:43](API/Controllers/UserManagement/CaptchaController.cs:43) |
| FR-046 | 发布Bulletin | `BulletinController.Post` | `BulletinHandler` | [API/Controllers/ToolsManagement/BulletinController.cs:32](API/Controllers/ToolsManagement/BulletinController.cs:32) |

oolsManagement/BulletinController.cs:32](API/Controllers/ToolsManagement/BulletinController.cs:32) |
| FR-047 | 获取Bulletin列表 | `BulletinController.GetBulletins` | `BulletinHandler` | [API/Controllers/ToolsManagement/BulletinController.cs:64](API/Controllers/ToolsManagement/BulletinController.cs:64) |
| FR-048 | 审批Bulletin | `BulletinController.ApproveBulletin` | `BulletinHandler` | [API/Controllers/ToolsManagement/BulletinController.cs:96](API/Controllers/ToolsManagement/BulletinController.cs:96) |
| FR-049 | 健康检查 | `HealthController.Get` | `HealthHandler` | [API/Controllers/ToolsManagement/HealthController.cs:20](API/Controllers/ToolsManagement/HealthController.cs:20) |
| FR-050 | 获取微信Config | `WeChatController.Get` | `WeChatHandler` | [API/Controllers/ToolsManagement/WeChat/WeChatController.cs:36](API/Controllers/ToolsManagement/WeChat/WeChatController.cs:36) |

ment/WeChat/WeChatController.cs:36](API/Controllers/ToolsManagement/WeChat/WeChatController.cs:36) |
| FR-051 | 更新微信Config | `WeChatController.Post` | `WeChatHandler` | [API/Controllers/ToolsManagement/WeChat/WeChatController.cs:68](API/Controllers/ToolsManagement/WeChat/WeChatController.cs:68) |
| FR-052 | 调用 AI Agent 对话接口 | `chat_completions`（FastAPI 端点） | `InsightOrchestrator` | [Agents/server.py:346](Agents/server.py:346) |
| FR-053 | 获取 Session 列表 | `list_sessions`（FastAPI 端点） | `MemoryManager` | [Agents/server.py:614](Agents/server.py:614) |
| FR-054 | 获取单个 Session 详情 | `get_session`（FastAPI 端点） | `MemoryManager` | [Agents/server.py:622](Agents/server.py:622) |
| FR-055 | 删除 Session | `delete_session`（FastAPI 端点） | `MemoryManager` | [Agents/server.py:633](Agents/server.py:633) |
| FR-056 | 清理过期 Session | `cleanup_expired_sessions`（FastAPI 端点） | `MemoryManager` | [Agents/server.py:641](Agents/server.py:641) |

nup_expired_sessions`（FastAPI 端点） | `MemoryManager` | [Agents/server.py:641](Agents/server.py:641) |
| FR-057 | 获取 Agent 列表 | `list_agents`（FastAPI 端点） | `InsightOrchestrator` | [Agents/server.py:649](Agents/server.py:649) |

### 9.2. NFR Trace

NFR映射到具体的Config项、代码段或架构机制。每个 NFR 均通过可量化的Config值或代码实现进行验证，确保非功能需求的满足情况可被客观度量。

iled = 620002`（[Models/Common/Enums/ExceptionCodes.cs:6](Models/Common/Enums/ExceptionCodes.cs:6)） |
| NFR-S-005 | Payment宝签名验证：Payment宝回调必须通过签名验证 | 检查 `AlipaySignatureError` 错误码 | `ExceptionCodes.AlipaySignatureError = 810007`（[Models/Common/Enums/ExceptionCodes.cs:6](Models/Common/Enums/ExceptionCodes.cs:6)） |
| NFR-P-001 | Trace 查询性能：ClickHouse 查询超时保护 | 检查 `ClickHouseQueryTimeout` 错误码 | `ExceptionCodes.ClickHouseQueryTimeout = 150017`（[Models/Common/Enums/ExceptionCodes.cs:6](Models/Common/Enums/ExceptionCodes.cs:6)） |
| NFR-P-002 | Trace 查询异常处理：ClickHouse 查询错误必须被捕获并返回明确错误码 | 检查 `ClickHouseQueryError` 错误码 | `ExceptionCodes.ClickHouseQueryError = 150010`（[Models/Common/Enums/ExceptionCodes.cs:6](Models/Common/Enums/ExceptionCodes.cs:6)） |
| NFR-P-003 | Trace 查询数量限制：单次查询 Trace ID 数量必须受限 | 检查 `TooManyTraceIds` 错误码 | `ExceptionCodes.TooManyTraceIds = 150011`（[Models/Common/Enums/ExceptionCodes.cs:6](Models/Common/Enums/ExceptionCodes.cs:6)） |

eIds = 150011`（[Models/Common/Enums/ExceptionCodes.cs:6](Models/Common/Enums/ExceptionCodes.cs:6)） |
| NFR-P-004 | 过滤条件校验：非法过滤类型、列、操作符或值必须返回明确错误码 | 检查 `InvalidFilterType`/`InvalidFilterColumn`/`InvalidFilterOperator`/`InvalidFilterValue` 错误码 | `ExceptionCodes.InvalidFilterType = 150012`，`ExceptionCodes.InvalidFilterColumn = 150013`，`ExceptionCodes.InvalidFilterOperator = 150014`，`ExceptionCodes.InvalidFilterValue = 150015`（[Models/Common/Enums/ExceptionCodes.cs:6](Models/Common/Enums/ExceptionCodes.cs:6)） |
| NFR-A-001 | 系统高可用：健康检查端点必须可用 | 验证 `GET /api/tools/health` 返回 200 | `HealthController.Get` [API/Controllers/ToolsManagement/HealthController.cs:20](API/Controllers/ToolsManagement/HealthController.cs:20) |

rs/ToolsManagement/HealthController.cs:20](API/Controllers/ToolsManagement/HealthController.cs:20) |
| NFR-A-002 | 异步任务处理：项目删除等耗时操作通过 BullMQ 队列异步执行 | 检查 `BullMqService.EnqueueProjectDeleteAsync` 调用 | `API.System.Handlers.AgentInsightTransformProvider` → `API.Common.Services.BullMqService` [API/System/Handlers/AgentInsightTransformProvider.cs:8](API/System/Handlers/AgentInsightTransformProvider.cs:8) |
| NFR-A-003 | Trace 数据（统一术语）异步写入：Trace 数据（统一术语）通过 BullMQ 队列异步写入 ClickHouse | 检查 `BullMqService.EnqueueTraceIngestionAsync` 调用 | `API.Common.Services.BullMqService` [API/Common/Services/BullMqService.cs:1-30](API/Common/Services/BullMqService.cs:1-30) |
| NFR-A-004 | 异步任务确认：Trace 数据（统一术语）写入必须通过 `AcknowledgeTraceIngestionAsync` 确认 | 检查 `BullMqService.AcknowledgeTraceIngestionAsync` 调用 | `API.Common.Services.BullMqService` [API/Common/Services/BullMqService.cs:1-30](API/Common/Services/BullMqService.cs:1-30) |

ften = 110000`（[Models/Common/Enums/ExceptionCodes.cs:6](Models/Common/Enums/ExceptionCodes.cs:6)） |
| NFR-C-004 | Captcha校验：空Captcha、无效Captcha、错误Captcha必须返回明确错误码 | 检查 `EmptyCaptcha`/`InvalidCaptcha`/`ErrorCaptcha` 错误码 | `ExceptionCodes.EmptyCaptcha = 110002`，`ExceptionCodes.InvalidCaptcha = 110003`，`ExceptionCodes.ErrorCaptcha = 110004`（[Models/Common/Enums/ExceptionCodes.cs:6](Models/Common/Enums/ExceptionCodes.cs:6)） |
| NFR-D-001 | 数据一致性：Payment回调通过 MediatR 通知模式解耦处理，确保订单状态同步 | 检查 `PaymentTransactionNotification` 及 `PaymentTransactionSaveHandler` | `API.Notifications.PaymentTransactionNotification.cs:1-15`；`PaymentTransactionSaveHandler` → `PaymentService` [API/Notifications/PaymentTransactionSaveHandler.cs:10](API/Notifications/PaymentTransactionSaveHandler.cs:10) |

ations/PaymentTransactionSaveHandler.cs:10](API/Notifications/PaymentTransactionSaveHandler.cs:10) |
| NFR-D-002 | Alert评估策略化：Alert字段评估通过策略模式支持多种指标 | 检查 `IAlertFieldEvaluator` 接口 | `API.Notifications.AlertEvaluators.IAlertFieldEvaluator.cs:1-10`；`AlertService` → `IAlertFieldEvaluator` [API/Common/Services/AlertService.cs:5](API/Common/Services/AlertService.cs:5) |
| NFR-O-001 | 操作审计：用户关键操作（登录、创建、删除等）必须记录审计日志 | 检查 `AuditAction` 枚举定义 | `AuditAction` 枚举含 `Create`/`Update`/`Delete`/`Login`/`Logout` 等（[Models/Common/Enums/AuditEnum.cs:3](Models/Common/Enums/AuditEnum.cs:3)） |
| NFR-O-002 | 异常Trace：系统异常必须记录Trace日志 | 检查 `QueueType.ExceptionRecord` 枚举 | `QueueType.ExceptionRecord = 1`（[Entities/Common/Enums/QueueEnum.cs:3](Entities/Common/Enums/QueueEnum.cs:3)） |
| NFR-O-003 | 用量Trace：系统用量数据必须记录Trace日志 | 检查 `QueueType.UsageTracking` 枚举 | `QueueType.UsageTracking = 2`（[Entities/Common/Enums/QueueEnum.cs:3](Entities/Common/Enums/QueueEnum.cs:3)） |

e.UsageTracking = 2`（[Entities/Common/Enums/QueueEnum.cs:3](Entities/Common/Enums/QueueEnum.cs:3)） |
| NFR-O-004 | 性能记录：系统性能数据必须记录Trace日志 | 检查 `QueueType.PerformanceRecord` 枚举 | `QueueType.PerformanceRecord = 3`（[Entities/Common/Enums/QueueEnum.cs:3](Entities/Common/Enums/QueueEnum.cs:3)） |
| NFR-O-005 | 审计资源类型：审计日志必须区分资源类型 | 检查 `AuditResourceType` 枚举定义 | `AuditResourceType` 枚举含 `User`/`Organization`/`Project`/`Alert`/`ApiKey`/`Invitation`/`Order`/`WeChat`/`OrgPrivilege`（[Models/Common/Enums/AuditEnum.cs:18](Models/Common/Enums/AuditEnum.cs:18)） |
| NFR-M-001 | Alert字段覆盖：Alert评估必须支持多种指标字段 | 检查 `AlertField` 枚举定义 | `AlertField` 枚举含 `TotalTokens`/`TotalCost`/`ErrorCount`/`Latency`/`ErrorRate`/`InputTokens`/`OutputTokens`/`WarningCount`/`ObservationCount`（[Models/Common/Enums/AlertEnum.cs:20](Models/Common/Enums/AlertEnum.cs:20)） |

nt`/`ObservationCount`（[Models/Common/Enums/AlertEnum.cs:20](Models/Common/Enums/AlertEnum.cs:20)） |
| NFR-M-002 | Alert操作符覆盖：Alert评估必须支持多种比较操作符 | 检查 `AlertOperator` 枚举定义 | `AlertOperator` 枚举含 `GreaterThan`/`LessThan`/`EqualTo`/`GreaterThanOrEqualTo`/`LessThanOrEqualTo`/`NotEqualTo`（[Models/Common/Enums/AlertEnum.cs:10](Models/Common/Enums/AlertEnum.cs:10)） |
| NFR-M-003 | Alert时间单位：Alert周期必须支持分钟、小时、天 | 检查 `AlertTimeUnit` 枚举定义 | `AlertTimeUnit` 枚举含 `Minute`/`Hour`/`Day`（[Models/Common/Enums/AlertEnum.cs:3](Models/Common/Enums/AlertEnum.cs:3)） |
| NFR-M-004 | Alert通知方式：Alert必须支持系统通知与短信通知 | 检查 `AlertNotifyBy` 枚举定义 | `AlertNotifyBy` 枚举含 `System`/`SMS`（[Models/Common/Enums/AlertEnum.cs:39](Models/Common/Enums/AlertEnum.cs:39)） |
| NFR-M-005 | Alert记录状态：Alert记录必须区分活动与已读状态 | 检查 `AlertRecordState` 枚举定义 | `AlertRecordState` 枚举含 `Active`/`Read`（[Models/Common/Enums/AlertEnum.cs:33](Models/Common/Enums/AlertEnum.cs:33)） |

e` 枚举含 `Active`/`Read`（[Models/Common/Enums/AlertEnum.cs:33](Models/Common/Enums/AlertEnum.cs:33)） |
| NFR-M-006 | 过滤类型覆盖：Trace 查询过滤必须支持多种数据类型 | 检查 `FilterType` 枚举定义 | `FilterType` 枚举含 `DateTime`/`String`/`Number`/`StringOptions`/`ArrayOptions`/`Boolean`/`Null`（[Models/Common/Enums/FilterEnum.cs:8](Models/Common/Enums/FilterEnum.cs:8)） |
| NFR-M-007 | 过滤操作符覆盖：Trace 查询过滤必须支持多种操作符 | 检查 `FilterOperator` 枚举定义 | `FilterOperator` 枚举含 `GreaterThan`/`LessThan`/`EqualTo`/`Contains`/`AnyOf`/`NoneOf`/`AllOf`/`NotEqualTo`/`IsNull`/`IsNotNull` 等（[Models/Common/Enums/FilterEnum.cs:20](Models/Common/Enums/FilterEnum.cs:20)） |

sNull`/`IsNotNull` 等（[Models/Common/Enums/FilterEnum.cs:20](Models/Common/Enums/FilterEnum.cs:20)） |
| NFR-M-008 | 过滤列覆盖：Trace 查询过滤必须支持多种列 | 检查 `FilterColumn` 枚举定义 | `FilterColumn` 枚举含 `Id`/`Name`/`Timestamp`/`UserId`/`SessionId`/`Environment`/`Version`/`Release`/`Tags`/`Bookmarked`/`Latency`/`InputTokens`/`OutputTokens`/`TotalTokens`/`Tokens`/`InputCost`/`OutputCost`/`TotalCost`/`Level`/`WarningCount`/`ErrorCount`/`DefaultCount`/`DebugCount`/`ModelNames`/`ScoresAvg`（[Models/Common/Enums/FilterEnum.cs:40](Models/Common/Enums/FilterEnum.cs:40)） |
| NFR-M-009 | Payment方式覆盖：系统必须支持微信Payment与Payment宝Payment | 检查 `SubPayMethod` 枚举定义 | `SubPayMethod` 枚举含 `WECHAT_JSAPI`/`WECHAT_NATIVE`/`WECHAT_MINIPROGRAM`/`ALIPAY_FAST_INSTANT_TRADE_PAY`（[Models/Common/Enums/PaymentEnums.cs:29](Models/Common/Enums/PaymentEnums.cs:29)） |

STANT_TRADE_PAY`（[Models/Common/Enums/PaymentEnums.cs:29](Models/Common/Enums/PaymentEnums.cs:29)） |
| NFR-M-010 | 交易状态覆盖：系统必须支持完整的交易状态映射 | 检查 `TradeState` 枚举定义 | `TradeState` 枚举含 `SUCCESS`/`REFUND`/`NOTPAY`/`CLOSED`/`REVOKED`/`USERPAYING`/`PAYERROR`/`TRADE_CLOSED`/`TRADE_FINISHED`/`TRADE_SUCCESS`/`WAIT_BUYER_PAY`（[Models/Common/Enums/PaymentEnums.cs:6](Models/Common/Enums/PaymentEnums.cs:6)） |
| NFR-M-011 | 订单状态管理：订单状态更新失败必须返回明确错误码 | 检查 `OrderStateUpdateFailed` 错误码 | `ExceptionCodes.OrderStateUpdateFailed = 810026`（[Models/Common/Enums/ExceptionCodes.cs:6](Models/Common/Enums/ExceptionCodes.cs:6)） |

iled = 810026`（[Models/Common/Enums/ExceptionCodes.cs:6](Models/Common/Enums/ExceptionCodes.cs:6)） |
| NFR-M-012 | Payment异常覆盖：Payment流程各环节异常必须返回明确错误码 | 检查 `AlipayConnectionError`/`AlipayTradeError`/`InvalidAlipayTradeNo`/`InvalidAlipayTransaction` 错误码 | `ExceptionCodes.AlipayConnectionError = 810003`，`ExceptionCodes.AlipayTradeError = 810004`，`ExceptionCodes.InvalidAlipayTradeNo = 810005`，`ExceptionCodes.InvalidAlipayTransaction = 810006`（[Models/Common/Enums/ExceptionCodes.cs:6](Models/Common/Enums/ExceptionCodes.cs:6)） |

tion = 810006`（[Models/Common/Enums/ExceptionCodes.cs:6](Models/Common/Enums/ExceptionCodes.cs:6)） |
| NFR-M-013 | 微信Payment异常覆盖：微信Payment各环节异常必须返回明确错误码 | 检查 `InvalidWeChatNotify`/`EmptyWeChatTransaction`/`InvalidWeChatTradeNo`/`EmptyWeChatNotify`/`WeChatEmptyResponse`/`WeChatErrorResponse`/`WeChatQueryErrorResponse` 错误码 | `ExceptionCodes.InvalidWeChatNotify = 810010`，`ExceptionCodes.EmptyWeChatTransaction = 810016`，`ExceptionCodes.InvalidWeChatTradeNo = 810017`，`ExceptionCodes.EmptyWeChatNotify = 810018`，`ExceptionCodes.WeChatEmptyResponse = 810021`，`ExceptionCodes.WeChatErrorResponse = 810022`，`ExceptionCodes.WeChatQueryErrorResponse = 810024`（[Models/Common/Enums/ExceptionCodes.cs:6](Models/Common/Enums/ExceptionCodes.cs:6)） |

onse = 810024`（[Models/Common/Enums/ExceptionCodes.cs:6](Models/Common/Enums/ExceptionCodes.cs:6)） |
| NFR-M-014 | 产品与订单校验：产品不存在、时长不存在、订单不存在必须返回明确错误码 | 检查 `ProductNotExist`/`ProductDurationNotExist`/`OrderNotExist` 错误码 | `ExceptionCodes.ProductNotExist = 810013`，`ExceptionCodes.ProductDurationNotExist = 810014`，`ExceptionCodes.OrderNotExist = 810015`（[Models/Common/Enums/ExceptionCodes.cs:6](Models/Common/Enums/ExceptionCodes.cs:6)） |
| NFR-M-015 | 产品降级保护：不允许降级产品 | 检查 `CannotDowngradeProduct` 错误码 | `ExceptionCodes.CannotDowngradeProduct = 810023`（[Models/Common/Enums/ExceptionCodes.cs:6](Models/Common/Enums/ExceptionCodes.cs:6)） |
| NFR-M-016 | 金额校验：订单总金额必须有效 | 检查 `InvalidTotalAmount` 错误码 | `ExceptionCodes.InvalidTotalAmount = 810025`（[Models/Common/Enums/ExceptionCodes.cs:6](Models/Common/Enums/ExceptionCodes.cs:6)） |

ount = 810025`（[Models/Common/Enums/ExceptionCodes.cs:6](Models/Common/Enums/ExceptionCodes.cs:6)） |
| NFR-M-017 | 商户校验：商户必须有效 | 检查 `InvalidMerchant` 错误码 | `ExceptionCodes.InvalidMerchant = 810027`（[Models/Common/Enums/ExceptionCodes.cs:6](Models/Common/Enums/ExceptionCodes.cs:6)） |
| NFR-M-018 | Payment方式校验：不支持的Payment方式必须返回明确错误码 | 检查 `UnsupportedPayMethod` 错误码 | `ExceptionCodes.UnsupportedPayMethod = 810019`（[Models/Common/Enums/ExceptionCodes.cs:6](Models/Common/Enums/ExceptionCodes.cs:6)） |
| NFR-M-019 | 组织配额限制：组织成员数、项目数、组织数必须受限 | 检查 `ExceedHeadCountLimit`/`ExceedProjectLimit`/`ExceedOrgLimit` 错误码 | `ExceptionCodes.ExceedHeadCountLimit = 130010`，`ExceptionCodes.ExceedProjectLimit = 130011`，`ExceptionCodes.ExceedOrgLimit = 130012`（[Models/Common/Enums/ExceptionCodes.cs:6](Models/Common/Enums/ExceptionCodes.cs:6)） |

imit = 130012`（[Models/Common/Enums/ExceptionCodes.cs:6](Models/Common/Enums/ExceptionCodes.cs:6)） |
| NFR-M-020 | 组织Privilege控制：未授权的组织访问必须被拒绝 | 检查 `UnauthorizedOrganizationAccess` 错误码 | `ExceptionCodes.UnauthorizedOrganizationAccess = 130009`（[Models/Common/Enums/ExceptionCodes.cs:6](Models/Common/Enums/ExceptionCodes.cs:6)） |
| NFR-M-021 | 项目Privilege控制：未授权的项目访问必须被拒绝 | 检查 `UnauthorizedProjectAccess` 错误码 | `ExceptionCodes.UnauthorizedProjectAccess = 140008`（[Models/Common/Enums/ExceptionCodes.cs:6](Models/Common/Enums/ExceptionCodes.cs:6)） |
| NFR-M-022 | 组织删除保护：组织下有项目时不允许删除 | 检查 `OrganizationHasProjects` 错误码 | `ExceptionCodes.OrganizationHasProjects = 130007`（[Models/Common/Enums/ExceptionCodes.cs:6](Models/Common/Enums/ExceptionCodes.cs:6)） |
| NFR-M-023 | 项目删除保护：项目正在删除中时不允许重复删除 | 检查 `OrganizationProjectDeleting` 错误码 | `ExceptionCodes.OrganizationProjectDeleting = 130008`（[Models/Common/Enums/ExceptionCodes.cs:6](Models/Common/Enums/ExceptionCodes.cs:6)） |

ting = 130008`（[Models/Common/Enums/ExceptionCodes.cs:6](Models/Common/Enums/ExceptionCodes.cs:6)） |
| NFR-M-024 | 组织所有者保护：组织只能有一个所有者 | 检查 `OrgAlreadyHasOwner` 错误码 | `ExceptionCodes.OrgAlreadyHasOwner = 130013`（[Models/Common/Enums/ExceptionCodes.cs:6](Models/Common/Enums/ExceptionCodes.cs:6)） |
| NFR-M-025 | 角色Privilege保护：不能授予更高角色，所有者不能修改自身角色 | 检查 `CannotGrantHigherRole`/`OwnerCannotModifySelfRole` 错误码 | `ExceptionCodes.CannotGrantHigherRole = 100023`，`ExceptionCodes.OwnerCannotModifySelfRole = 100039`（[Models/Common/Enums/ExceptionCodes.cs:6](Models/Common/Enums/ExceptionCodes.cs:6)） |
| NFR-M-026 | 用户邀请校验：邀请手机号必须有效且不重复 | 检查 `EmptyInviteMobile`/`InvalidInviteMobile`/`InviteAlreadyExists` 错误码 | `ExceptionCodes.EmptyInviteMobile = 100021`，`ExceptionCodes.InvalidInviteMobile = 100022`，`ExceptionCodes.InviteAlreadyExists = 100025`（

---

## 10. 附录

### 10.1. 术语词典

本文档涉及大量代码标识符与领域术语，为保证技术描述的准确性与可追溯性，以下术语在全文范围内必须保留英文原文，禁止翻译为中文或使用中英对照模式。

**品牌与项目名称**

| 术语 | 说明 |
|------|------|
| AgentAgentInsightService（统一保留英文） | 项目名称，面向 AI Agent 可Observation性与管理的后端平台 |
| AgentInsight | 产品品牌名，用于后台管理界面标题及数据库表前缀 |
| AgentInsightService | 产品品牌名的简写形式 |

**核心业务术语**

| 术语 | 说明 |
|------|------|
| Agent | 系统管理的核心实体 |
| Trace | Trace数据，表示一次完整的请求链路 |
| Observation | Observation数据，Trace 中的单个操作记录 |
| Score | Score数据，用于对 Trace 或 Observation 进行质量评估 |
| Session | Session，Agent 与用户之间的交互上下文 |
| Span | Span，Trace 中的时间片段 |
| Token | Token，LLM 调用的计费单位 |
| Alert | Alert，基于 Trace 指标的阈值通知 |
| Captcha | Captcha，用户注册/登录时的安全校验 |
| Privilege | Privilege，Org/项目级别的访问控制 |
| Role | Role，用户Privilege的集合（VIEWER/MEMBER/ADMIN/OWNER） |

**代码标识符（禁止翻译）**

以下标识符在文档、代码引用及Config说明中必须原样保留：

| 类别 | 标识符 |
|------|--------|
| 服务类 | `BullMqService`, `ClickHouseClient`, `AlertService`, `FurionAppContextService` |
| 接口类 | `IAlertService`, `IPaymentService` |
| 辅助类 | `TraceFilterBuilder`, `ClickHouseHelper`, `UserExtension`, `TraceIdResult` |
| 方法名 | `EnqueueProjectDeleteAsync`, `EnqueueTraceIngestionAsync`, `AcknowledgeTraceIngestionAsync`, `GetTimeSpan`, `IsConditionMet`, `BuildAlertMessage`, `DisposeAsync` |
| Config类 | `AgentInsightTransformProvider`, `AgentInsightTransformLogic`, `ApiHandlerBase`, `AgentInsightConst` |
| 枚举类 | `ExceptionCodes`, `FilterType`, `FilterOperator`, `FilterColumn`, `AlertField`, `AlertOperator`, `AlertTimeUnit`, `TradeState`, `SubPayMethod`, `OrderState`, `QueueType`, `RouteType`, `JobFrequency`, `JobType`, `JobStatus` |

**文件路径与目录**

所有文件路径引用必须保留原始 PascalCase 大小写，例如 `API/Controllers/UserManagement/UserController.cs` 不能写成小写形式。路径中的目录名与文件名同样禁止翻译。

### 10.2. 品牌名与项目名清单

本项目的品牌名与项目名在代码库、Config文件和部署环境中具有严格的一致性要求，任何翻译或改写都会导致标识符无法对应到实际资源。

**项目名**

**AgentAgentInsightService（统一保留英文）** 是仓库的正式项目名称，出现在以下场景中：

- 项目根目录的解决方案文件与项目文件（如 `API/API.csproj`）
- Docker 容器命名与部署编排
- 环境变量前缀（如 `AGENTINSIGHTENV`）
- 数据库表名前缀（`agentinsight_` 开头的表归入 default 库）

**品牌名**

| 品牌名 | 使用场景 |
|--------|----------|
| AgentInsight | Django Admin 后台标题（`admin.site.site_header = "AgentInsight后台管理"` [Admin/app/admin.py]）、数据库表前缀、API 路由前缀 |
| AgentAgentInsightService（统一保留英文） | 项目整体名称、Swagger 文档标题、包名（Python 侧 `name = "agentinsight-agents"`） |
| AgentInsightService | 服务层接口命名约定（如 `IAgentInsightService`），用于业务逻辑抽象 |

**禁止事项**

- 禁止将 AgentAgentInsightService（统一保留英文） 翻译为"Agent洞察服务"等中文短语
- 禁止将 AgentInsight 缩写为 AI 或 AIS
- 禁止将 AgentInsightService 改写为其他名称
- 禁止在文档中捏造未列出的品牌名或域名

### 10.3. 子项目结构说明

本项目采用 monorepo 架构，共包含 8 个子项目，按职责划分为 In-Scope 核心服务与基础类库两类。

**In-Scope 子项目**

| 子项目 | 技术栈 | 职责说明 |
|--------|--------|----------|
| API | C# (.NET) + Furion + SqlSugar ORM + YARP | 主后端服务，提供全部 REST API（76 个端点），包含用户管理、Payment集成、Trace 数据（统一术语）查询、Alert系统、Agent Config管理等核心模块。入口为 `API/Program.cs`，路由注册于各 Controller |
| Agents | Python 3.11 + FastAPI + LangChain + LangGraph | AI Agent Service，提供 OpenAI 兼容的 Chat Completions API（`POST /api/agent/insight`），支持流式响应、Session持久化与多 Agent 路由。入口为 `Agents/server.py` |
| Admin | Django + simpleui | 管理后台，纯 Admin Project，不提供 REST API。所有 Model 设置 `managed = False`，数据库表由 .NET API 主服务管理，禁止执行 `makemigrations` 和 `migrate` [Admin/Agents.md] |

**基础类库**

| 子项目 | 职责说明 |
|--------|----------|
| Entities | 实体定义与数据库模型映射，包含 `Entities/Common/Enums/`（如 `QueueEnum.cs`）、`Entities/Common/Settings/`（如 `SMSSetting.cs`）等 |
| Models | DTO 与业务模型，包含 `Models/Common/Enums/`（如 `ExceptionCodes.cs`、`FilterEnum.cs`、`AlertEnum.cs`、`PaymentEnums.cs`）、`Models/Common/Consts/`（如 `AgentInsightConst`） |
| Utility | 通用工具类，提供加密、序列化、时间处理等基础能力 |
| Tools | 工具集，包含微信/Payment宝签名辅助、Config占位符解析等 |
| UnitTest | 单元测试项目，覆盖 Handler、Service、TransformProvider 等核心组件 |

**关键架构约束**

- **双数据库路由**：Admin 项目中表名以 `agentinsight_` 开头 → `default` 库，其他 → `data` 库，路由逻辑定义在 `app/db_router.py`，禁止修改 [Admin/Agents.md]
- **环境切换**：通过环境变量 `AGENTINSIGHTENV` 切换 `Development` / `QA` / `LIVE` 三种环境 [Admin/Agents.md]
- **分层架构**：API 项目采用 Controller → Handler → Service → Repository 分层，Handler 层通过 `ApiHandlerBase` 统一注入用户上下文与数据库 [API/Handlers/ApiHandlerBase.cs]

### 10.4. Config项速查

以下Config项从 `appsettings.json` 及环境Config中提取，是系统运行的关键参数。所有敏感值均通过环境变量注入，禁止硬编码。

**连接字符串**

| Config键 | 环境变量 | 说明 |
|--------|----------|------|
| `ConnectionStrings.UserDbConnection` | `${USER_DB_HOST}` `${USER_DB_PORT}` `${USER_DB_NAME}` `${USER_DB_USER}` `${USER_DB_PASSWORD}` | PostgreSQL，连接池 MinPoolSize=10, MaxPoolSize=200, ConnectionLifetime=300 |
| `ConnectionStrings.DataDbConnection` | `${DATA_DB_HOST}` `${DATA_DB_PORT}` `${DATA_DB_NAME}` `${DATA_DB_USER}` `${DATA_DB_PASSWORD}` | PostgreSQL，连接池参数同上 |
| `ConnectionStrings.TrackingDbConnection` | `${TRACKING_DB_HOST}` `${TRACKING_DB_PORT}` `${TRACKING_DB_NAME}` `${TRACKING_DB_USER}` `${TRACKING_DB_PASSWORD}` | TracePostgreSQL，连接池参数同上 |
| `ConnectionStrings.ClickHouseDbConnection` | `${CLICKHOUSE_HOST}` `${CLICKHOUSE_PORT}` `${CLICKHOUSE_USER}` `${CLICKHOUSE_PASSWORD}` `${CLICKHOUSE_DB}` | ClickHouse 时序库，PoolSize=10, MaxPoolSize=50, ConnectionTimeout=30, CommandTimeout=60 |

**JWT 认证**

| Config键 | 值 | 说明 |
|--------|-----|------|
| `JWTSettings.Algorithm` | HS256 | 签名算法 |
| `JWTSettings.ExpiredTime` | 43200 | 过期时间（分钟），即 30 天 |
| `JWTSettings.ClockSkew` | 5 | 时钟偏差（分钟） |
| `JWTSettings.ValidIssuer` | `${JWT_ISSUER}` | 签发者 |
| `JWTSettings.ValidAudience` | `${JWT_AUDIENCE}` | 受众 |
| `JWTSettings.IssuerSigningKey` | `${JWT_SIGNING_KEY}` | 签名密钥 |
| `JWTSettings.ValidateIssuer` / `ValidateAudience` / `ValidateLifetime` / `ValidateIssuerSigningKey` | True | 全部开启校验 |

**Redis 与缓存**

| Config键 | 值 | 说明 |
|--------|-----|------|
| `Redis.ConnectionString` | `localhost:${REDIS_PORT},password=${REDIS_AUTH}` | Redis 连接，用于Session缓存与 BullMQ 队列 |

**YARP**

| Config键 | 值 | 说明 |
|--------|-----|------|
| `ReverseProxy.Routes.AgentInsight-Route-API.Match.Path` | `/api/public/{**catch-all}` | API 公共路由，转发至 Langfuse 集群 |
| `ReverseProxy.Routes.AgentInsight-Route-Public.Match.Path` | `/public/{**catch-all}` | 公共静态资源路由 |
| `ReverseProxy.Clusters.AgentInsight-Langfuse-Cluster.Destinations.AgentInsight-Destination.Address` | `http://localhost:3000/` | Langfuse 服务地址 |

**Captcha与本地化**

| Config键 | 值 | 说明 |
|--------|-----|------|
| `CaptchaSetting.CaptchaCodeLength` | 5 | 图形Captcha长度 |
| `CaptchaSetting.SMSCodeLength` | 6 | 短信Captcha长度 |
| `CaptchaSetting.EmailCodeLength` | 6 | 邮箱Captcha长度 |
| `CaptchaSetting.ExpiredSeconds` | 300 | Captcha过期时间（秒） |
| `CaptchaSetting.ResendInterval` | 60 | 重发间隔（秒） |
| `LocalizationSettings.DefaultCulture` | zh-CN | 默认语言 |
| `LocalizationSettings.SupportedCultures` | `['zh-CN', 'zh-TW', 'zh-HK', 'en']` | 支持的四国语言 |

**Log**

| Config键 | 值 | 说明 |
|--------|-----|------|
| `Logging.File.FileName` | `logs/application-.log` | 日志文件路径 |
| `Logging.File.FileSizeLimitBytes` | 10485760 | 单文件大小上限（10MB） |
| `Logging.File.MaxRollingFiles` | 30 | 最大滚动文件数 |
| `Logging.File.MinimumLevel` | Information | 文件日志最低级别 |

**其他**

| Config键 | 值 | 说明 |
|--------|-----|------|
| `SnowFlakeWorkId` | 16 | 雪花算法工作节点 ID |
| `AllowedHosts` | `*` | 允许的主机 |
| `EnableTracking` | True | 是否启用Trace |
| `DisableObservationsFinal` | False | 是否禁用 Observations 最终化 |

### 10.5. 依赖第三方库列表

本项目依赖的第三方库分为 .NET 后端、Python AI Agent 服务与 Admin 后台三部分。

**.NET 后端（API Project）**

| 库名 | 用途 |
|------|------|
| AlipaySDKNet.Standard | Payment宝Payment SDK，用于即时到账交易 |
| MediatR | 进程内消息传递，实现Payment回调、Alert触发等异步事件的 `INotification` / `INotificationHandler` 解耦模式 |
| BouncyCastle.Cryptography | 加密算法库，用于Payment签名与验签 |
| Npgsql | PostgreSQL 的 .NET 数据提供程序 |
| StackExchange.Redis | Redis 客户端，用于Session缓存与 BullMQ 队列 |
| Yarp.ReverseProxy | 反向代理库，将 `/api/public/` 与 `/public/` 路由转发至 Langfuse Service |
| My.Extensions.Localization.Json | JSON 本地化扩展，支持 zh-CN / zh-TW / zh-HK / en 四语言 |
| Microsoft.SemanticKernel | AI 编排框架（可选集成） |
| Microsoft.VisualStudio.Azure.Containers.Tools.Targets | Docker 容器构建支持 |

**Python AI Agent Service（Agents Project）**

| 库名 | 用途 |
|------|------|
| openai | OpenAI API 客户端，提供 Chat Completions 调用 |
| httpx | 异步 HTTP 客户端，用于外部 API 请求 |
| pydantic | 数据验证与设置管理 |
| pydantic-settings | 基于 pydantic 的Config管理 |
| LangChain.Providers.OpenAI | LangChain 的 OpenAI 提供商适配 |
| agentinsight-sdk | AgentInsight 官方 SDK，用于 Trace 数据（统一术语）上报 |

**Admin 后台（Admin Project）**

| 库名 | 用途 |
|------|------|
| django-import-export | Django Admin 数据导入导出 |
| whitenoise | 静态文件服务（生产环境） |
| psycopg2-binary | PostgreSQL 驱动 |

**运行时依赖（部署环境）**

部署环境中还包含以下系统级依赖：

- `openssl-provider-legacy`：OpenSSL 遗留提供商
- `libsasl2-modules-db`：SASL 认证模块
- `gcc-14-x86-64-linux-gnu` / `cpp-14-x86-64-linux-gnu` / `binutils-x86-64-linux-gnu`：编译工具链
- `zlib1g`：压缩库

以上依赖清单与 `API/API.csproj`、`Agents/pyproject.toml`、`Admin/requirements.txt` 中的声明保持一致。

---

## 附录: 代码术语与枚举（AST/扫描提取）

### 品牌/产品名

`AgentInsightService`, `AgentInsight`, `InsightService`

### 核心类名

`XmlSerializerOutputFormatterWithoutNamespace`, `SpecificSystemTextJsonOutputFormatter`, `SpecificSystemTextJsonInputFormatter`, `StartupTaskWebApplicationExtensions`, `AgentInsightSettingNameAttribute`, `ConfigurationPlaceholderResolver`, `WeChatNotifyReceivedNotification`, `CreateMembershipInvitationBody`, `PaymentTransactionNotification`, `WeChatMiniProgramLoginResponse`, `AgentInsightPerformanceRecord`, `AgentInsightTransformProvider`, `PaymentTransactionSaveHandler`, `WeChatPayCertificateResponse`, `AgentInsightExceptionRecord`, `AgentInsightProductDuration`, `ServiceCollectionExtensions`, `TraditionalChineseConverter`, `TraditionalChineseExtension`, `WeChatNotifyReceivedHandler`, `WeChatPayEncryptCertificate`, `AgentInsightTransformLogic`, `AlertTriggeredNotification`, `WeChatOrderBodyGoodsDetail`, `AgentInsightOrderResponse`, `HttpRequestBuilderService`, `NullableDateTimeConverter`, `ObservationCountEvaluator`, `ProductConversionResponse`, `WeChatTextMessageResponse`, `WeChatTransactionResponse`, `WeChatTransationSceneInfo`, `AgentInsightAPISecretKey`, `NpgsqlNullNameTranslator`, `AgentReportTemplateBody`, `ConfigureMvcJsonOptions`, `FilterOperatorConverter`, `FurionAppContextService`, `WeChatRefundTransaction`, `WeChatTransactionAmount`, `AgentSessionController`, `ApiKeyValidationResult`, `CreateOrganizationBody`, `GlobalExceptionHandler`, `LowercaseEnumConverter`, `OrganizationController`, `OrganizationMembership`, `TraceCalculatedMetrics`, `UpdateOrganizationBody`, `WeChatSignatureService`, `WeChatTransactionPayer`, `AgentConfigController`, `AgentInsightOrderBody`, `AgentReportController`, `CamelCaseNamingPolicy`, `LowerCaseNamingPolicy`, `OutputTokensEvaluator`, `SettingsNameAttribute`, `SwaggerApiDescription`, `TraceIngestionPayload`, `WarningCountEvaluator`, `WeChatMessageResponse`, `WeChatOrderBodyAmount`, `WeChatOrderBodyDetail`, `WeChatOrderBodySettle`, `CreateUserConfigBody`, `FilterEnumExtensions`, `HttpContextExtension`, `InputTokensEvaluator`, `MembershipInvitation`, `MvcOptionsExtensions`, `SkipSetUserAttribute`, `TotalTokensEvaluator`, `TraceMetricsResponse`, `UpdateUserConfigBody`, `UserConfigController`, `WeChatJSAPIOrderBody`, `WeChatNotifyResource`, `WeChatOrderBodyPayer`, `WeChatOrderBodyScene`, `WeChatOrderBodyStore`, `WeChatPayCertificate`, `WeChatPhoneWatermark`, `WeChatPromotionGoods`, `AgentInsightProduct`, `AgentInsightSetting`, `AgentReportTemplate`, `AgentSessionHandler`, `AlertMetricsHandler`, `ClickHouseConverter`, `CurrentOrgPrivilege`, `ErrorCountEvaluator`, `ExceptionMiddleware`, `OrganizationHandler`, `PersistentQueueItem`, `SanitizeInputFilter`, `WeChatLoginResponse`, `WeChatOrderResponse`, `WeChatPhoneResponse`, `WeChatRefundAccount`, `AgentConfigHandler`, `AgentConfigPayload`, `AgentReportHandler`, `BulletinController`, `CreateBulletinBody`, `DatabaseUpgradeJob`, `ErrorRateEvaluator`, `ExceptionExtension`, `RateLimitAttribute`, `RequestAuditFilter`, `SystemAlertHandler`, `TotalCostEvaluator`, `TraceFilterBuilder`, `TraceIngestionData`, `WeChatRefundAmount`, `WeChatResponseBase`, `AgentInsightAudit`, `AgentInsightConst`, `AgentInsightOrder`, `AgentInsightRegex`, `AlertMetricsConst`, `AlipayTransaction`, `ApiControllerBase`, `AutoSetUserFilter`, `BeijingTimeHelper`, `CaptchaController`, `CreateProjectBody`, `DateTimeConverter`, `DateTimeExtension`, `IPAddressResponse`, `MetricsController`, `ProductController`, `ProjectCalculated`, `ProjectController`, `ProjectMembership`, `ResetPasswordBody`, `TencentSMSSetting`, `TraceIngestionJob`, `TraceSelectFields`, `UpdateProjectBody`, `UsageTrackingBase`, `UserConfigHandler`, `WeChatTransaction`, `AgentSessionBody`, `ClickHouseClient`, `ClickHouseHelper`, `HealthController`, `LatencyEvaluator`, `NotifyController`, `OrganizationBase`, `PaymentExtension`, `ThirdPartyHelper`, `TraceMetricsBody`, `WeChatController`, `WeChatRefundBody`, `AlertController`, `BulletinHandler`, `CaptchaResponse`, `ContextTracking`, `CreateAlertBody`, `DoubleConverter`, `FilterCondition`, `ModelController`, `ModelDefinition`, `ObjectExtension`, `OrderController`, `OrderRepository`, `RouteConvention`, `SMSAlertHandler`, `StringExtension`, `TraceMetricsRow`, `UpdateAlertBody`, `WeChatModelBase`, `WeChatOrderBody`, `WeChatPromotion`, `ApiHandlerBase`, `ApiKeyResponse`, `AssignRoleBody`, `CaptchaHandler`, `CaptchaService`, `CaptchaSetting`, `DeadLetterItem`, `EncryptService`, `LangfuseAPIKey`, `MetricsHandler`, `ModelPriceTier`, `PaymentService`, `ProductHandler`, `ProjectHandler`, `SQLSugarHelper`, `SettingHandler`, `SettingService`, `SplitModelBase`, `ToolsExtension`, `UserController`, `AliSMSSetting`, `AlipaySetting`, `ApiheResponse`, `AtomicInteger`, `BullMqService`, `DataQueueItem`, `GZipExtension`, `ModelDateBase`, `NotifyHandler`, `PgEnumConvert`, `SysExtensions`, `TraceCountRow`, `TraceIdResult`, `UsageTracking`, `UserExtension`, `UserPrivilege`, `WeChatAccount`, `WeChatHandler`, `WeChatMessage`, `WeChatService`, `WeChatSetting`, `AgentSession`, `AlertHandler`, `AlertMetrics`, `AlertService`, `MetricsConst`, `MiniUserBody`, `ModelHandler`, `OrderHandler`, `OrgPrivilege`, `Organization`, `SysExtension`, `TraceDataRow`, `TraceMetrics`, `UserAlertLog`, `WeChatNotify`, `AgentConfig`, `AlertConfig`, `AlertRecord`, `ApiResponse`, `MailSetting`, `Observation`, `RetryHelper`, `TextContent`, `UserHandler`, `UserService`, `UserSession`, `WeChatPhone`, `WeChatToken`, `AlertConst`, `BatchQueue`, `CacheConst`, `JwtHandler`, `ModelConst`, `ModelPrice`

### 数据表名/列名

`cloud_free_tier_usage_threshold_state`, `agentinsight_wechatrefundtransaction`, `agentinsight_wechatnotifyresource`, `agentinsight_wechatpromotiongoods`, `agentinsight_agentreporttemplate`, `agentinsight_currentorgprivilege`, `agentinsight_wechatrefundaccount`, `agentinsight_wechatrefundamount`, `agentinsight_alipaytransaction`, `agentinsight_performancerecord`, `agentinsight_projectcalculated`, `agentinsight_wechattransaction`, `cloud_billing_cycle_updated_at`, `agentinsight_api_secret_keys`, `agentinsight_exceptionrecord`, `agentinsight_productduration`, `agentinsight_wechatpromotion`, `agentinsight_wechat_account`, `agentinsight_userprivilege`, `cloud_billing_cycle_anchor`, `agentinsight_agentsession`, `agentinsight_orgprivilege`, `agentinsight_useralertlog`, `agentinsight_wechat_token`, `agentinsight_wechatnotify`, `cloud_current_cycle_usage`, `agentinsight_agentconfig`, `agentinsight_alertrecord`, `organization_memberships`, `agentinsight_job_record`, `agentinsight_userconfig`, `usage_pricing_tier_name`, `agentinsight_useralert`, `fast_hashed_secret_key`, `membership_invitations`, `provided_usage_details`, `agentinsight_bulletin`, `completion_start_time`, `parent_observation_id`, `provided_cost_details`, `usage_pricing_tier_id`, `agentinsight_product`, `agentinsight_setting`, `ai_features_enabled`, `project_memberships`, `provided_model_name`, `agentinsight_audit`, `agentinsight_order`, `display_secret_key`, `execution_trace_id`, `invited_by_user_id`, `hashed_secret_key`, `internal_model_id`, `long_string_value`, `observation_count`, `org_membership_id`, `ObservationCount`, `buyer_pay_amount`, `model_parameters`, `tokenizer_config`, `tool_definitions`, `buyer_user_name`, `buyer_user_type`, `organization_id`, `pricing_tier_id`, `tool_call_names`, `v4_beta_enabled`, `author_user_id`, `buyer_logon_id`, `dataset_run_id`, `email_verified`, `observation_id`, `prompt_version`, `retention_days`, `status_message`, `buyer_user_id`, `default_count`, `match_pattern`, `organizations`, `output_tokens`, `pricing_tiers`, `send_pay_date`, `usage_details`, `warning_count`, `DefaultCount`, `OutputTokens`, `WarningCount`, `cloud_config`, `cost_details`, `input_tokens`, `last_used_at`, `observations`, `out_trade_no`, `output_price`, `project_role`, `string_value`, `tokenizer_id`, `total_amount`, `total_tokens`, `tracemetrics`, `trade_status`, `Environment`, `InputTokens`, `TotalTokens`, `debug_count`, `error_count`, `input_price`, `model_names`, `output_cost`, `prompt_name`, `total_price`, `Bookmarked`, `DebugCount`, `ErrorCount`, `ModelNames`, `OutputCost`, `Parameters`, `created_at`, `deleted_at`, `expires_at`, `has_traces`, `input_cost`, `is_default`, `is_deleted`, `model_name`, `project_id`, `public_key`, `scores_avg`, `session_id`, `start_date`, `start_time`, `tool_calls`, `total_cost`, `updated_at`, `usage_type`, `CreatedAt`, `InputCost`, `IsDeleted`, `ProjectId`, `ScoresAvg`, `SessionId`, `Timestamp`, `TotalCost`, `UpdatedAt`, `config_id`, `data_blob`, `data_type`, `prompt_id`, `starttime`, `Metadata`, `api_keys`, `end_time`, `event_ts`, `model_id`, `org_role`, `projects`, `queue_id`, `trace_id`, `trade_no`, `EventTs`, `Latency`, `Release`, `TraceId`, `Version`, `comment`, `endtime`, `user_id`, `Output`, `Public`, `UserId`, `models`, `org_id`, `prices`, `scores`, `source`, `status`, `traces`, `Input`, `Level`, `Total`, `admin`, `email`, `price`, `scope`, `users`, `value`, `Name`, `Tags`, `host`, `role`, `type`, `Id`

### 属性/字段名

`AgentInsightSettingExpiredMinutes`, `CloudFreeTierUsageThresholdState`, `ScoreToTraceObservationsInterval`, `WeChatMerchantPrivateKeyCacheKey`, `AuthorizedRefreshAccessTokenUrl`, `ConfigDisableObservationsFinal`, `ClickHouseQueryTimeoutSeconds`, `PaymentTransactionSaveFailed`, `WeChatPayCertificateCacheKey`, `AgentInsightSettingCacheKey`, `CurrentOrgPrivilegeCacheKey`, `ObservationsToTraceInterval`, `CloudBillingCycleUpdatedAt`, `DefaultCacheExpiredMinutes`, `DefaultMonthlyResearchRate`, `MerchantPrivateKeyFilePath`, `StartNowJobIntervalSeconds`, `TraceNameContainsCondition`, `WeChatPayPublicKeyCacheKey`, `WeChatPayPublicKeyFilePath`, `CacheScanFrequencyMinutes`, `KeyedService_ClickHouseDb`, `RateLimitExceededResponse`, `TracesObservationStatsCte`, `TransactionTimeoutSeconds`, `AlipayOrderErrorResponse`, `AuthorizedAccessTokenUrl`, `ClickHouseSettingsClause`, `FieldObsObservationCount`, `MonthlyUsedPermanentRate`, `PayCertificatesUrlSuffix`, `WeChatQueryErrorResponse`, `CloudBillingCycleAnchor`, `DefaultMonthlyAgentRate`, `JoinScoreConditionInner`, `KeyedService_TrackingDb`, `PaymentTransactionRetry`, `PrivilegeExpiredMinutes`, `TraceIngestionTimeoutMs`, `UsedMonthlyResearchRate`, `UserSessionExpiredHours`, `User_Organization_Order`, `CloudCurrentCycleUsage`, `EmailCaptchaSenderName`, `ScoreTimestampInterval`, `SlowRequestThresholdMs`, `TracesCountSqlTemplate`, `AuthorizedUserInfoUrl`, `DefaultHeadCountLimit`, `FieldTraceEnvironment`, `JoinObsConditionInner`, `ObservationCoreSelect`, `Payment_Product_Order`, `TimestampGteCondition`, `TimestampLteCondition`, `TraceIdMixedCondition`, `TracesDataSqlTemplate`, `TradeNOQueryUrlSuffix`, `UserCacheExpiredHours`, `UserPrivilegeCacheKey`, `WeChatPayCertificates`, `ApiSecretKeyCacheKey`, `DefaultSortDirection`, `FieldObsDefaultCount`, `FieldObsOutputTokens`, `FieldObsWarningCount`, `FieldTraceBookmarked`, `GetWeChatTokenFailed`, `MiniProgramAppSecret`, `ObsStartTimeInterval`, `OrderByTimestampDesc`, `OrgPrivilegeCacheKey`, `Payment_Notify_Order`, `ProvidedUsageDetails`, `SubscribeSceneString`, `Tools_Bulletin_Order`, `TraceIdsByProjectSql`, `TracesSimpleCountSql`, `UsagePricingTierName`, `UsedMonthlyAgentRate`, `Agent_Session_Order`, `AlertTracesCacheKey`, `AuthorizationSchema`, `BasicAccessTokenUrl`, `CaptchaCodeCacheKey`, `CompletionStartTime`, `DefaultProjectLimit`, `ElapsedMilliseconds`, `EmailCaptchaContent`, `EmailCaptchaSubject`, `FastHashedSecretKey`, `FieldObsInputTokens`, `FieldObsTotalTokens`, `FieldTraceSessionId`, `FieldTraceTimestamp`, `InternalServerError`, `KeyedService_DataDb`, `KeyedService_UserDb`, `MonthlyResearchRate`, `ObservationCoreFrom`, `ParentObservationId`, `Payment_Order_Order`, `ProvidedCostDetails`, `SMSInstanceCacheKey`, `Tools_Setting_Order`, `TracesScoreStatsCte`, `TracesSelectMetrics`, `TracesSimpleDataSql`, `UserSessionCacheKey`, `WechatPayContribute`, `Agent_Config_Order`, `Agent_Report_Order`, `AlertTemplateParam`, `BaseWhereCondition`, `Data_Metrics_Order`, `DefaultEnvironment`, `DefaultMonthlyRate`, `EncryptCertificate`, `FieldObsDebugCount`, `FieldObsErrorCount`, `FieldObsModelNames`, `FieldObsOutputCost`, `HKSMSLoginTemplate`, `HasExceedRateLimit`, `InvalidTotalAmount`, `JoinScoreCondition`, `LoginTemplateParam`, `MerchantContribute`, `MetadataDictionary`, `NativePayUrlSuffix`, `PayCertificatesUrl`, `Tools_Wechat_Order`, `TracesSelectScores`, `TradeQueryResponse`, `UsagePricingTierId`, `UserNotInitialized`, `UserPhoneNumberUrl`, `User_Captcha_Order`, `User_Project_Order`, `AiFeaturesEnabled`, `AlipayTransaction`, `CancellationToken`, `CaptchaCodeLength`, `DefaultSortColumn`, `DefaultTemplateId`, `FieldObsInputCost`, `FieldObsTotalCost`, `FieldTraceEventTs`, `FieldTraceRelease`, `FieldTraceVersion`, `FrequencyQuantity`, `JSAPIPayUrlSuffix`, `JwtApiKeyCacheKey`, `ProductDurationId`, `ProvidedModelName`, `QueryIPAddressUrl`, `ScoreTimestampGte`, `SqlFunctionToDate`, `TableObservations`, `UsedPermanentRate`, `User_Config_Order`, `User_Organization`, `WeChatTransaction`, `ApiheSuccessCode`, `BasicUserInfoUrl`, `CompletionTokens`, `Data_Model_Order`, `DefaultSortField`, `DefaultTotalRate`, `DisplaySecretKey`, `ExecutionTraceId`, `FieldTraceUserId`, `JoinObsCondition`, `LimitOneByClause`, `MiniProgramAppId`, `MonthlyAgentRate`, `ObservationCount`, `PaginationClause`, `SettlementRefund`, `TracesSelectCore`, `User_Alert_Order`, `User_Login_Order`, `WechatpayGoodsId`, `AlertMetricsSql`, `AlertTemplateId`, `AliAlertMessage`, `AlipayPublicKey`, `Code2SessionUrl`, `DefaultOrgLimit`, `DefaultPageSize`, `EmailCodeLength`, `FieldObsLatency`, `HashedSecretKey`, `InternalModelId`, `InvitedByUserId`, `LastCompletedAt`, `LoginTemplateId`, `LongStringValue`, `MerchantGoodsId`, `MobileVerfiedAt`, `ModelParameters`, `ObsStartTimeGte`, `OrgMembershipId`, `OtherContribute`, `Payment_Product`, `PurePhoneNumber`, `ReceivedAccount`, `RefundUrlSuffix`, `SMSCodeCacheKey`, `SettlementTotal`, `TokenizerConfig`, `ToolDefinitions`, `TraceMetricsSql`, `TradeNOQueryUrl`, `UsedMonthlyRate`, `WeChatAccountId`, `WeChatPhoneCode`, `XAccessTokenKey`, `AcceptEncoding`, `AcceptLanguage`, `AccessTokenKey`, `AssociatedData`, `BuyerPayAmount`, `CommaDelimiter`, `DefaultOrderBy`, `DiscountAmount`, `DiscountRefund`, `EnableTracking`, `ExpiredSeconds`, `FieldTraceName`, `FieldTraceTags`, `HeadCountLimit`, `OrganizationId`, `Payment_Notify`, `PeriodQuantity`, `PhotoUrlString`, `PromotionGoods`, `RefundAccounts`, `RefundAmountId`, `RefundQuantity`, `ResendInterval`, `SubscribeScene`, `Tools_Bulletin`, `TracesSelectIO`, `TradeStateDesc`, `TradeStateEnum`, `WeChatPaySkuId`, `WeChatRefundId`, `Agent_Session`, `AlipaySetting`

### 枚举常量

`API`

### 方法名

`API.Common.Extensions`, `UserExtension`, `API.Common.Helpers`, `ClickHouseHelper`, `TraceFilterBuilder`, `API.Common.Services`, `AlertService`, `GetTimeSpan`, `IsConditionMet`, `BuildAlertMessage`, `TraceIdResult`, `BullMqService`, `EnqueueProjectDeleteAsync`, `EnqueueTraceIngestionAsync`, `AcknowledgeTraceIngestionAsync`, `DisposeAsync`, `ClickHouseClient`, `FurionAppContextService`, `IAlertService`, `IPaymentService`, `IUserService`, `IWeChatService`, `OrderRepository`, `GetByOrderNoAsync`, `CreateAsync`, `UpdateStateAsync`, `PaymentService`, `CalculateConvertedDays`, `GetOrder`, `CreateOrderNo`, `CreateOrder`, `UpdateOrgPrivilege`, `GetAlipaySignDictionary`, `ExamineAlipaySignature`, `GetAlipayTransaction`, `UpdateOrderState`, `SaveAlipayTransaction`, `GetAlipayInstantTrade`, `SaveWeChatTransaction`, `SaveWeChatNotify`, `GetWeChatNativeOrderBody`, `GetWeChatJSAPIOrderBody`, `CreateWeChatOrderResponse`, `GetWeChatOrderResponseAsync`, `GetWeChatJSAPIResponse`, `GetNativeResponse`, `WeChatMiniProgramPay`, `WeChatMiniProgramQuery`, `GetWeChatTransaction`, `SettingService`, `GetOrCreateAgentInsightSetting`, `InvalidateCache`, `GetAgentInsightSettingAsync`, `GetWeChatSetting`, `GetAlipaySetting`, `UserService`, `CreateNewUser`, `GetCacheUserByUserId`, `GetUserByUserId`, `GetUserByMobile`, `LogUserSession`, `GetUserMaxSession`, `EvictSessionAsync`, `QueryIPAddressAsync`, `GetCurrentOrgPrivilege`, `GetOrgPrivilegeAsync`, `UpdateOrgPrivilegeAsync`, `GetLatestOrgIdByUserIdAsync`, `WeChatService`, `ExamineSignature`, `GetBasicAccessToken`, `GetAuthorizedAccessToken`, `GetAccessToken`, `GetRefreshTokenAsync`, `CreateOrUpdateAccessTokenAsync`, `LoginByWeChatMiniProgram`, `GetOrUpdateAuthorizedWXAccount`, `GetOrUpdateBasicWXAccount`, `GetOrUpdateWXAccountAsync`, `CreateOrUpdateWXAccountAsync`, `WXFailResult`, `WXSuccessResult`, `API.Controllers.AgentManagement`, `API.Controllers`, `ApiControllerBase`, `RegisterHandler`, `GetUserAsync`, `API.Controllers.DataManagement`, `API.Controllers.PaymentManagement`, `API.Controllers.ProductManagement`, `API.Controllers.ToolsManagement`, `API.Controllers.ToolsManagement.WeChat`, `API.Controllers.UserManagement`, `API.Handlers.AgentManagement`, `AgentConfigHandler`, `DeleteConfig`, `AgentConfigPayload`, `AgentReportHandler`, `DeleteTemplates`, `AgentSessionHandler`, `DeleteSessions`, `API.Handlers`, `ApiHandlerBase`, `SetUser`, `RequireOrgMembership`, `RequireOrgAdmin`, `RequireOrgOwner`, `RequireExistingProject`, `RequireAccessibleProject`, `RequireProjectAdmin`, `LogAudit`, `API.Handlers.DataManagement`, `AlertMetricsHandler`, `MetricsHandler`, `ResolveProjectId`, `TraceSelectFields`, `QueryTracesCountAsync`, `TraceCountRow`, `TraceDataRow`, `ModelHandler`, `Entities.Common`, `IUserAwareHandler`, `API.Handlers.PaymentManagement`, `NotifyHandler`, `ExamineWeChatRequest`, `ProcessWeChatNotify`, `ProcessAlipayNotify`, `OrderHandler`, `PlaceWeChatOrder`, `PlaceAlipayOrder`, `QueryWeChatOrder`, `QueryAlipayOrder`, `GetProductConversion`, `API.Handlers.ProductManagement`, `ProductHandler`, `API.Handlers.ToolsManagement`, `BulletinHandler`, `DeleteBulletins`, `SettingHandler`, `API.Handlers.ToolsManagement.WeChat`, `WeChatHandler`, `ProcessMessage`, `ProcessEventMessage`, `API.Handlers.UserManagement`, `AlertHandler`, `GetAlertConfig`, `DeleteAlerts`, `ReadAlertRecords`, `ValidateOrgAndProject`, `CaptchaHandler`, `CreateCaptcha`, `OrganizationHandler`, `DeleteOrganization`, `DeleteOrganizations`, `GetUserOrgLimit`, `ProjectHandler`, `DeleteProject`, `DeleteProjects`, `GetOrgProjectLimit`, `UserConfigHandler`, `Delete`, `UserHandler`, `Logout`, `UnBindWeChat`, `ResetPassword`, `GetOrgHeadCountLimit`, `DeleteInvitation`, `AssignRole`, `AssignOrgRole`, `AssignProjectRole`, `ResolveOrgIdAndValidateMembership`, `DeductMonthlyAgentRate`, `ValidateMonthlyAgentRate`, `ResolveOrgIdForAgentType`, `ValidateApiKeyAccess`, `CreateApiKey`, `DeleteApiKey`, `API.Notifications.AlertEvaluators`, `ErrorCountEvaluator`, `ErrorRateEvaluator`, `IAlertFieldEvaluator`, `InputTokensEvaluator`, `LatencyEvaluator`, `ObservationCountEvaluator`, `OutputTokensEvaluator`, `TotalCostEvaluator`, `TotalTokensEvaluator`, `WarningCountEvaluator`, `API.Notifications`, `AlertTriggeredNotification`, `PaymentTransactionNotification`, `TransactionType`, `WithRetry`, `PaymentTransactionSaveHandler`, `Handle`, `SMSAlertHandler`, `SendAlertSMSAsync`, `SystemAlertHandler`, `WeChatNotifyReceivedHandler`, `WeChatNotifyReceivedNotification`

### 枚举定义

| 枚举 | 成员 |
|------|------|
| `TransactionType` | WeChatTransaction, AlipayTransaction |
| `RouteType` | None, Public, PublicApi |
| `Environment` | DEVELOPMENT, STAGING, PRODUCTION |
| `RetrieverType` | BM25, VECTOR, CUSTOM_SERVICE |
| `QueueType` | Audit, ExceptionRecord, UsageTracking, PerformanceRecord |
| `SMSInstance` | None, Aliyun, TencentCloud |
| `AgentInsightSettingType` | WeChat, Alipay |
| `AlertTimeUnit` | Minute, Hour, Day |
| `AlertOperator` | GreaterThan, LessThan, EqualTo, GreaterThanOrEqualTo, LessThanOrEqualTo, NotEqualTo |
| `AlertField` | TotalTokens, TotalCost, ErrorCount, Latency, ErrorRate, InputTokens, OutputTokens, WarningCount, ObservationCount |
| `AlertRecordState` | Active, Read |
| `AlertNotifyBy` | System, SMS |
| `AuditAction` | Create, Update, Delete, Login, Logout, Reset, Bind, UnBind, Place, Query, Notify |
| `AuditResourceType` | User, Organization, Project, Alert, ApiKey, Invitation, Order, WeChat, OrgPrivilege |
| `ExceptionCodes` | UnAuthToken, EmptyUserId, ExistedMobile, CreateUserFailed, InvalidUser, EmptyMobile, UnauthorizedOperator, UserNameTooLong, EmptyInviteMobile, InvalidInviteMobile, CannotGrantHigherRole, UserAlreadyOrgMember, InviteAlreadyExists, CreateInviteFailed, InviteNotFound, DeleteInviteFailed, ApiKeyNotFound, CreateApiKeyFailed, DeleteApiKeyFailed, MissingProjectOrOrgId |
| `FilterType` | DateTime, String, Number, StringOptions, ArrayOptions, Boolean, Null |
| `FilterOperator` | GreaterThan, LessThan, GreaterThanOrEqualTo, LessThanOrEqualTo, EqualTo, Contains, DoesNotContain, StartsWith, EndsWith, AnyOf, NoneOf, AllOf, NotEqualTo, IsNull, IsNotNull |
| `FilterColumn` | Id, Name, Timestamp, UserId, SessionId, Environment, Version, Release, Tags, Bookmarked, Latency, InputTokens, OutputTokens, TotalTokens, Tokens, InputCost, OutputCost, TotalCost, Level, WarningCount |
| `JobFrequency` | Minutely, Hourly, Daily, Weekly, Monthly, Yearly |
| `JobType` | Regularly, Once, Permanently |
| `JobCacheAction` | Load, Create, Ignore |
| `JobStatus` | Created, Running, Completed |
| `TradeState` | SUCCESS, REFUND, NOTPAY, CLOSED, REVOKED, USERPAYING, PAYERROR, TRADE_CLOSED, TRADE_FINISHED, TRADE_SUCCESS, WAIT_BUYER_PAY |
| `SubPayMethod` | WECHAT_JSAPI, WECHAT_NATIVE, WECHAT_MINIPROGRAM, ALIPAY_FAST_INSTANT_TRADE_PAY |
| `OrderState` | Created, WaitForPay, Paid, Refunded, Cancelled, Closed, PayError |
| `ProductType` | None, Monthly, Permanent |
| `PayMethod` | WeChat, Alipay |
| `AgentType` | Assistant, Research |
| `BulletinType` | News, Activity, Information, Annoucement, Advertisement, Agreement |
| `BulletinStatus` | Draft, Reviewing, Revision, Published, Expired, Closed |
| `PGRole` | NONE, VIEWER, MEMBER, ADMIN, OWNER |
| `ApiKeyScope` | PROJECT, ORGANIZATION |
| `UserConfigType` | User, Organization, Project |
| `LoginType` | Password, SMS, WeChat, MiniProgram, APIKey |
| `WeChatMessageType` | None, Event, Text, Image, Voice, Video, Shortvideo, Location, Link |
| `WeChatMessageEvent` | Subscribe, Unsubscribe, Scan, Location, Click, View, MasssEndJobFinish |
| `WeChatSubscribeScene` | ADD_SCENE_SEARCH, ADD_SCENE_ACCOUNT_MIGRATION, ADD_SCENE_PROFILE_CARD, ADD_SCENE_QR_CODE, ADD_SCENE_PROFILE_LINK, ADD_SCENE_PROFILE_ITEM, ADD_SCENE_PAID, ADD_SCENE_WECHAT_ADVERTISEMENT, ADD_SCENE_REPRINT, ADD_SCENE_LIVESTREAM, ADD_SCENE_CHANNELS, ADD_SCENE_OTHERS |
| `WeChatTradeType` | JSAPI, NATIVE, APP, MICROPAY, MWEB, FACEPAY |
| `WeChatPromotionScope` | GLOBAL, SINGLE |
| `WeChatPromotionType` | CASH, NOCASH |

### HTTP 路由清单

- `/api/agent/config`
- `/api/agent/config/delete`
- `/api/agent/insight`
- `/api/agent/report`
- `/api/agent/report/delete`
- `/api/agent/session`
- `/api/agent/session/delete`
- `/api/agents`
- `/api/alert`
- `/api/alert/config`
- `/api/alert/delete`
- `/api/alert/record`
- `/api/alert/record/read`
- `/api/alert/update`
- `/api/captcha`
- `/api/captcha/sms`
- `/api/data/metrics/observations`
- `/api/data/metrics/scores`
- `/api/data/metrics/traces`
- `/api/data/model`
- `/api/payment/notify/alipaynotify`
- `/api/payment/notify/wechatnotify`
- `/api/payment/order`
- `/api/payment/order/conversion`
- `/api/payment/order/query`
- `/api/product`
- `/api/product/duration`
- `/api/public`
- `/api/sessions`
- `/api/sessions/cleanup`
- `/api/sessions/{session_id}`
- `/api/test`
- `/api/tools/bulletin`
- `/api/tools/bulletin/agreement`
- `/api/tools/bulletin/approve`
- `/api/tools/bulletin/backend`
- `/api/tools/bulletin/bulletins`
- `/api/tools/bulletin/close`
- `/api/tools/bulletin/revision`
- `/api/tools/health`
- `/api/tools/wechat`
- `/api/user`
- `/api/user/apikey`
- `/api/user/apikey/delete`
- `/api/user/bind/wechat`
- `/api/user/config`
- `/api/user/config/delete`
- `/api/user/config/update`
- `/api/user/invitation`
- `/api/user/invitation/delete`
- `/api/user/invite`
- `/api/user/login`
- `/api/user/logout`
- `/api/user/organization`
- `/api/user/organization/delete`
- `/api/user/organization/update`
- `/api/user/privilege/agent/deduct`
- `/api/user/privilege/agent/validate`
- `/api/user/project`
- `/api/user/project/delete`
- `/api/user/project/update`
- `/api/user/resetpassword`
- `/api/user/role`
- `/api/user/unbind/wechat`
- `/api/user/update`

### 文档范围 (Scope 自动识别)

#### In-Scope
- API

#### Out-of-Scope
- Agents
- Admin
- Entities
- Models
- UnitTest
- Utility
- Tools

## 附录: 接口/业务规则/约束编号骨架

| 类型 | 编号范围 | 数量 | 说明 |
|------|----------|------|------|
| 接口需求 | IR-001 .. IR-007 | 7 | 与 HTTP 端点/外部依赖对应 |
| 业务规则 | BR-001 .. BR-039 | 39 | 与校验/状态机/配额规则对应 |
| 约束 | C-001 .. C-005 | 5 | 技术/合规/部署约束 |

### 接口需求编号

- IR-001
- IR-002
- IR-003
- IR-004
- IR-005
- IR-006
- IR-007

### 业务规则编号

- BR-001
- BR-002
- BR-003
- BR-004
- BR-005
- BR-006
- BR-007
- BR-008
- BR-009
- BR-010
- BR-011
- BR-012
- BR-013
- BR-014
- BR-015
- BR-016
- BR-017
- BR-018
- BR-019
- BR-020
- BR-021
- BR-022
- BR-023
- BR-024
- BR-025
- BR-026
- BR-027
- BR-028
- BR-029
- BR-030
- BR-031
- BR-032
- BR-033
- BR-034
- BR-035
- BR-036
- BR-037
- BR-038
- BR-039

### 约束编号

- C-001
- C-002
- C-003
- C-004
- C-005
## 附录: 功能需求清单（由 HTTP 端点确定性生成）

| 编号 | 模块 | 功能名 | 优先级 | 关联接口 |
|------|------|--------|--------|----------|
| FR-001 | AgentConfig | Get | Must | `GET /api/agent/config` |
| FR-002 | AgentConfig | Delete | Must | `GET /api/agent/config/delete` |
| FR-003 | AgentConfig | Post | Must | `POST /api/agent/config` |
| FR-004 | AgentReport | GetTemplates | Must | `GET /api/agent/report` |
| FR-005 | AgentReport | DeleteTemplates | Must | `GET /api/agent/report/delete` |
| FR-006 | AgentReport | CreateOrUpdateTemplate | Must | `POST /api/agent/report` |
| FR-007 | AgentSession | Get | Must | `GET /api/agent/session` |
| FR-008 | AgentSession | Delete | Must | `GET /api/agent/session/delete` |
| FR-009 | AgentSession | Post | Must | `POST /api/agent/session` |
| FR-010 | Alert | GetConfig | Must | `GET /api/alert/config` |
| FR-011 | Alert | Get | Must | `GET /api/alert` |
| FR-012 | Alert | Create | Must | `POST /api/alert` |
| FR-013 | Alert | Update | Must | `POST /api/alert/update` |
| FR-014 | Alert | Delete | Must | `POST /api/alert/delete` |
| FR-015 | Alert | ReadRecords | Must | `POST /api/alert/record/read` |
| FR-016 | Alert | GetRecords | Must | `GET /api/alert/record` |
| FR-017 | Bulletin | Post | Must | `POST /api/tools/bulletin` |
| FR-018 | Bulletin | Get | Must | `GET /api/tools/bulletin/agreement` |
| FR-019 | Bulletin | GetBulletins | Must | `GET /api/tools/bulletin/bulletins` |
| FR-020 | Bulletin | GetBackendBulletins | Must | `GET /api/tools/bulletin/backend` |
| FR-021 | Bulletin | ApproveBulletin | Must | `POST /api/tools/bulletin/approve` |
| FR-022 | Bulletin | ReviseBulletin | Must | `POST /api/tools/bulletin/revision` |
| FR-023 | Bulletin | CloseBulletin | Must | `POST /api/tools/bulletin/close` |
| FR-024 | Captcha | Get | Must | `GET /api/captcha` |
| FR-025 | Captcha | GetSMSCaptcha | Must | `GET /api/captcha/sms` |
| FR-026 | Health | Get | Must | `GET /api/tools/health` |
| FR-027 | LiteralRoute | literal_route | Must | `ANY /api/public` |
| FR-028 | LiteralRoute | literal_route | Must | `ANY /api/test` |
| FR-029 | Metrics | GetObservations | Must | `GET /api/data/metrics/observations` |
| FR-030 | Metrics | GetScores | Must | `GET /api/data/metrics/scores` |
| FR-031 | Metrics | GetTraces | Must | `GET /api/data/metrics/traces` |
| FR-032 | Metrics | GetTraces | Must | `POST /api/data/metrics/traces` |
| FR-033 | Model | Get | Must | `GET /api/data/model` |
| FR-034 | Notify | WeChatNotify | Must | `POST /api/payment/notify/wechatnotify` |
| FR-035 | Notify | AlipayNotify | Must | `POST /api/payment/notify/alipaynotify` |
| FR-036 | Order | Get | Must | `GET /api/payment/order` |
| FR-037 | Order | Place | Must | `POST /api/payment/order` |
| FR-038 | Order | Query | Must | `GET /api/payment/order/query` |
| FR-039 | Order | GetConversion | Must | `GET /api/payment/order/conversion` |
| FR-040 | Organization | Post | Must | `POST /api/user/organization` |
| FR-041 | Organization | Get | Must | `GET /api/user/organization` |
| FR-042 | Organization | Update | Must | `POST /api/user/organization/update` |
| FR-043 | Organization | Delete | Must | `POST /api/user/organization/delete` |
| FR-044 | Product | Get | Must | `GET /api/product` |
| FR-045 | Product | GetDuration | Must | `GET /api/product/duration` |
| FR-046 | Project | Create | Must | `POST /api/user/project` |
| FR-047 | Project | Get | Must | `GET /api/user/project` |
| FR-048 | Project | Update | Must | `POST /api/user/project/update` |
| FR-049 | Project | Delete | Must | `POST /api/user/project/delete` |
| FR-050 | Unknown | chat_completions | Must | `POST /api/agent/insight` |
| FR-051 | Unknown | list_sessions | Must | `GET /api/sessions` |
| FR-052 | Unknown | get_session | Must | `GET /api/sessions/{session_id}` |
| FR-053 | Unknown | delete_session | Must | `DELETE /api/sessions/{session_id}` |
| FR-054 | Unknown | cleanup_expired_sessions | Must | `POST /api/sessions/cleanup` |
| FR-055 | Unknown | list_agents | Must | `GET /api/agents` |
| FR-056 | UserConfig | Get | Must | `GET /api/user/config` |
| FR-057 | UserConfig | Post | Must | `POST /api/user/config` |
| FR-058 | UserConfig | Update | Must | `POST /api/user/config/update` |
| FR-059 | UserConfig | Delete | Must | `GET /api/user/config/delete` |
| FR-060 | User | Get | Must | `GET /api/user` |
| FR-061 | User | Create | Must | `POST /api/user` |
| FR-062 | User | Update | Must | `POST /api/user/update` |
| FR-063 | User | Login | Must | `POST /api/user/login` |
| FR-064 | User | Logout | Must | `POST /api/user/logout` |
| FR-065 | User | ResetPassword | Must | `POST /api/user/resetpassword` |
| FR-066 | User | Bind | Must | `POST /api/user/bind/wechat` |
| FR-067 | User | UnBind | Must | `GET /api/user/unbind/wechat` |
| FR-068 | User | AssignRole | Must | `POST /api/user/role` |
| FR-069 | User | Invite | Must | `POST /api/user/invite` |
| FR-070 | User | Get | Must | `GET /api/user/invitation` |
| FR-071 | User | DeleteInvitation | Must | `POST /api/user/invitation/delete` |
| FR-072 | User | CreateApiKey | Must | `POST /api/user/apikey` |
| FR-073 | User | Get | Must | `GET /api/user/apikey` |
| FR-074 | User | DeductMonthlyAgentRate | Must | `GET /api/user/privilege/agent/deduct` |
| FR-075 | User | ValidateMonthlyAgentRate | Must | `GET /api/user/privilege/agent/validate` |
| FR-076 | User | DeleteApiKey | Must | `POST /api/user/apikey/delete` |
| FR-077 | WeChat | Get | Must | `GET /api/tools/wechat` |
| FR-078 | WeChat | Post | Must | `POST /api/tools/wechat` |

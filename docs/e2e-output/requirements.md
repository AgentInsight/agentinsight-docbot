## 1. 引言

AgentInsightService（保持英文） 是一个面向 AI Agent 应用的可Observation性与管理平台，核心定位是为企业提供 Agent 对话Trace、性能分析、成本监控、用户Privilege管理以及订阅Payment功能，并内置可扩展的多 Agent 运行时服务。产品覆盖两大主要子项目：API 子项目（C# / Furion） 提供 RESTful Web API，负责用户管理、Org/项目管理、Agent Config、Trace数据查询、Alert、Payment集成等业务逻辑；Agents 子项目（Python / FastAPI） 提供 OpenAI 兼容的 Chat Completions 端点（保持英文）、意图路由、RAG 与多 Agent 协同，并持久化Session。此外，Admin (Django) 子项目提供后台管理界面，用于菜单导航、通知Bulletin等。

### 1.1. 编写目的与目标读者

本文档定义 AgentInsightService（保持英文） 的全部功能与非功能需求，作为产品研发、测试验收与项目管理的统一依据。文档以代码仓库为唯一事实来源，所有功能描述、接口定义、错误码与Config规格均从实际代码中提取，确保需求与实现的一致性。

目标读者包括：

| 读者角色 | 关注内容 | 典型使用场景 |
|---------|---------|-------------|
| 架构师 | 系统架构、技术选型、模块划分 | 评估系统设计合理性，规划技术演进路线 |
| 开发工程师 | 接口定义、业务规则、数据结构 | 功能开发、缺陷修复、代码评审 |
| 测试工程师 | 验收标准、错误码、边界条件 | 编写测试用例、执行功能验证与回归测试 |
| 产品经理 | 功能范围、用户角色、业务价值 | 确认产品需求覆盖度，规划迭代优先级 |
| 运维人员 | Config规格、部署依赖、健康检查 | 环境部署、Config管理、故障排查 |

### 1.2. 产品背景与业务痛点

#### 1.2.1. 业务背景

随着 AI Agent 应用在企业场景中的规模化落地，Agent 的运行质量直接关系到业务效果与成本控制。AgentInsightService（保持英文） 应运而生，定位为面向 AI Agent 应用的可Observation性与管理平台，覆盖 Agent 对话Trace、性能分析、成本监控、用户Privilege管理以及订阅Payment功能 [代码仓库学习摘要]。

产品包含三大子项目：

- **API 子项目（C# / Furion）**：提供 RESTful Web API，负责用户管理、Org/项目管理、Agent Config、Trace数据查询、Alert、Payment集成等业务逻辑 [API/Controllers/UserManagement/UserController.cs:29]。
- **Agents 子项目（Python / FastAPI）**：提供 OpenAI 兼容的 Chat Completions 端点（保持英文） [Agents/server.py:346]、意图路由、RAG 与多 Agent 协同，并持久化Session [Agents/server.py:614]。
- **Admin (Django)**：提供后台管理界面，用于菜单导航、通知Bulletin等。

#### 1.2.2. 业务痛点

企业在使用 AI Agent 过程中面临以下核心痛点：

1. **可Observation性缺失**：Agent 调用链路复杂，涉及多模型、多工具、多轮对话，缺乏统一的 Trace Trace机制，问题定位困难。
2. **成本不可控**：Token 消耗、模型调用费用缺乏精细化监控，难以按项目、按用户维度进行成本核算与配额管理。
3. **Privilege管理薄弱**：Org、Project、成员之间的数据隔离与角色Privilege控制不足，存在数据越权访问风险。
4. **Alert能力不足**：缺乏基于指标阈值的主动Alert机制，无法在异常发生时及时通知相关人员。
5. **商业化能力缺失**：缺少订阅、Payment、订单管理等商业化基础设施，难以将平台能力转化为可持续的业务收入。

AgentInsightService（保持英文） 通过提供端到端的可Observation性、成本监控、Privilege管理与订阅Payment能力，系统性解决上述痛点。

### 1.3. 文档范围

本文档覆盖 AgentInsightService（保持英文） 的功能需求与非功能需求，范围限定如下：

#### 1.3.1. In-Scope

| 子项目 | 技术栈 | 范围说明 |
|--------|--------|---------|
| API | C# / Furion | 全部 RESTful Web API 端点（共 76 个，来源：HTTP 端点清单），涵盖用户管理、Org/项目管理、Agent Config、Trace数据查询、Alert、Payment集成等业务逻辑 |
| Agents | Python / FastAPI | OpenAI 兼容的 Chat Completions 端点（保持英文）、Session 管理、Agent 列表查询等 6 个端点（来源：HTTP 端点清单） |

#### 1.3.2. Out-of-Scope

| 子项目 | 技术栈 | 范围说明 |
|--------|--------|---------|
| Admin | Django | 仅作为后台管理界面简述，不展开其内部实现细节 |

#### 1.3.3. 需求分类

本文档按以下类别组织需求：

- **功能需求 (FR)**：系统必须具备的业务功能，按模块划分。
- **非功能需求 (NFR)**：性能、安全、可用性、可维护性等质量属性。
- **接口需求 (IR)**：RESTful API 的请求/响应定义、错误码规范。
- **数据需求 (DR)**：核心数据实体、存储方案与数据流转。
- **约束条件**：技术栈、部署环境、合规性等限制。

### 1.4. 术语与缩略语

本文档遵循术语词典及强制英文原文规则：文档中出现的专业术语和代码标识符一律使用英文原文，不做中文翻译。以下为本文档使用的术语和代码标识符：

| 术语 | 说明 |
|------|------|
| Agent | AI Agent，指代可独立执行任务的 AI 程序实体 |
| Trace | 一次完整的请求调用链Trace记录 |
| Span | Trace 中的单个操作单元 |
| Session | Agent 与用户之间的一次持续交互过程 |
| Alert | 基于指标阈值触发的Alert规则或Alert记录 |
| Observation | 可Observation性数据点，用于性能分析与行为Trace |
| Metric | 指标数据，如 Token 消耗、延迟、错误率等 |
| Score | Score数据，用于评估 Agent 输出质量 |
| Token | 模型输入/输出的最小文本单元 |
| Privilege | 用户或组织拥有的功能Privilege |
| Role | 用户在组织/项目中的角色（OWNER / ADMIN / MEMBER / VIEWER） |
| Captcha | Captcha，用于注册、登录等场景的身份验证 |
| InsightService | AgentInsightService（保持英文） 的短名称，指代同一产品 |

以下为本文档中出现的代码标识符，保留原文：

| 标识符 | 说明 |
|--------|------|
| AgentInsightService（保持英文） | 项目名称 |
| AgentInsight | 品牌名称 |
| API | C# 后端子项目 |
| Agents | Python AI 服务子项目 |
| Admin | Django 后台管理子项目 |
| ExceptionCodes | 错误码枚举定义 [Models/Common/Enums/ExceptionCodes.cs:6] |
| FilterType | 过滤器类型枚举 [Models/Common/Enums/FilterEnum.cs:8] |
| FilterOperator | 过滤器操作符枚举 [Models/Common/Enums/FilterEnum.cs:20] |
| FilterColumn | 过滤器列枚举 [Models/Common/Enums/FilterEnum.cs:40] |
| AlertField | Alert字段枚举 [Models/Common/Enums/AlertEnum.cs:20] |
| AlertOperator | Alert操作符枚举 [Models/Common/Enums/AlertEnum.cs:10] |
| AlertTimeUnit | Alert时间单位枚举 [Models/Common/Enums/AlertEnum.cs:3] |
| AlertRecordState | Alert记录状态枚举 [Models/Common/Enums/AlertEnum.cs:33] |
| AlertNotifyBy | Alert通知方式枚举 [Models/Common/Enums/AlertEnum.cs:39] |
| OrderState | 订单状态枚举 [Models/Common/Enums/PaymentEnums.cs:40] |
| TradeState | 交易状态枚举 [Models/Common/Enums/PaymentEnums.cs:6] |
| SubPayMethod | Payment方式枚举 [Models/Common/Enums/PaymentEnums.cs:29] |
| QueueType | 消息队列类型枚举 [Entities/Common/Enums/QueueEnum.cs:3] |
| SMSInstance | 短信服务商枚举 [Entities/Common/Settings/SMSSetting.cs:35] |
| RouteType | 路由类型枚举 [API/System/Handlers/AgentInsightTransformLogic.cs:72] |
| Environment | 环境枚举 [Agents/common/config.py:15] |
| RetrieverType | 检索器类型枚举 [Agents/common/retriever.py:54] |

### 1.5. 参考文档

本文档的编写参考了以下代码仓库资料：

| 资料名称 | 说明 |
|---------|------|
| 产品概述与学习摘要 | 产品概述、技术栈、用户角色与场景的权威描述 |
| HTTP 端点清单 | 从 AST 提取的 76 个端点全集，分布在 18 个文件中 |
| 枚举定义清单 | 从 AST 提取的 43 个枚举定义，含错误码常量名与数值 |
| Config文件技术规格 | 从Config文件提取的技术规格，含 JWT、Redis、ClickHouse、本地化等Config项 |
| 关键代码片段 | 各 Controller 的接口实现代码，作为功能描述的佐证 |
| 依赖关系清单 | 各子项目的依赖文件映射（requirements.txt / pyproject.toml） |
| 关键模块清单 | 仓库一级子目录结构（API、Agents、Admin、Models、Entities 等） |

### 1.6. 版本历史

| 版本 | 日期 | 修订说明 | 作者 |
|------|------|---------|------|
| v1.0 | 待定 | 初始版本：基于代码仓库学习摘要与 AST 扫描结果，完成引言章节编写 | [作者姓名] |

---

## 2. 产品概述与用户分析

### 2.1. 产品定位

AgentInsightService（保持英文） 是一个面向 AI Agent 应用的可Observation性与管理平台，核心定位是为企业提供 Agent 对话Trace、性能分析、成本监控、用户Privilege管理以及订阅Payment功能，并内置可扩展的多 Agent 运行时服务。产品覆盖两大主要子项目：

- **API 子项目（C# / Furion）**: 提供 RESTful Web API，负责用户管理、Org/项目管理、Agent Config、Trace数据查询、Alert、Payment集成等业务逻辑（`API/Program.cs:1`）。
- **Agents 子项目（Python / FastAPI）**: 提供 OpenAI 兼容的 Chat Completions 端点（保持英文）（`Agents/server.py:346`）、意图路由、RAG 与多 Agent 协同，并持久化Session（`Agents/server.py:614`）。

此外，**Admin 子项目（Django + SimpleUI）** 子项目提供后台管理界面（`Admin/staticfiles/admin/simpleui-x/js/index.js`），用于菜单导航、通知Bulletin等。

### 2.2. 价值主张

**1. 快速故障定位**

通过实时 Trace 与 Alert 机制，将 AI 应用故障定位时间从小时级缩短至分钟级。产品提供完整的 Trace 数据采集、存储与查询能力，支持按时间、User、Session、模型名称等多维度过滤（FilterColumn 枚举定义了 25 种可过滤字段，包括 Latency、InputTokens、OutputTokens、TotalCost 等 [Models/Common/Enums/FilterEnum.cs:40]）。Alert 系统支持基于 TotalTokens、TotalCost、ErrorCount、Latency、ErrorRate 等指标的阈值Alert [Models/Common/Enums/AlertEnum.cs:20]，并通过 System 或 SMS 方式通知用户 [Models/Common/Enums/AlertEnum.cs:39]。

**2. 精细化成本监控**

产品提供模型级别的成本Trace能力。ModelController 支持按项目维度管理模型定义，包括输入价格、输出价格、总价、计费单位、分词器Config等 [API/Controllers/DataManagement/ModelController.cs:34]。结合 Trace 数据中的 Token 消耗记录，企业可以精确核算每个 Agent、每个 Session、每次调用的实际成本，为预算管控与成本优化提供数据支撑。

**3. 简化商业化闭环**

产品内置订阅Payment功能，支持微信Payment与Payment宝两种Payment渠道 [Models/Common/Enums/AgentInsightEnum.cs:3]。ProductController 提供产品列表与产品时长列表查询接口 [API/Controllers/ProductManagement/ProductController.cs:26]，OrderController 提供下单、查询、转化率统计接口 [API/Controllers/PaymentManagement/OrderController.cs:34]。企业用户可以直接在平台上完成订阅购买、配额升级等操作，无需额外对接Payment系统。

**4. 多 Agent 协同管理**

Agents 子项目提供多 Agent 运行时服务，支持意图路由与 RAG 检索增强 [Agents/server.py:346]。企业可以在统一平台上管理多个 Agent 的Config、Session与Trace数据，实现 Agent 间的协同调度与统一Observation。

### 2.3. 北极星指标

AgentInsightService（保持英文） 的北极星指标为**月活跃Trace Session 数量**与 **Alert 触发准确率**，两者共同衡量产品的核心价值交付。

**月活跃Trace Session 数量**（Monthly Active Traced Sessions, MATS）反映产品对用户的可Observation性价值。该指标统计每月通过 SDK 上报并成功写入 ClickHouse 的 Session 数量，覆盖所有项目与 Agent。Session 是 Trace 数据的基本组织单元，AgentSessionController 提供 Session 的创建、查询、删除接口 [API/Controllers/AgentManagement/AgentSessionController.cs:33]。MATS 的增长意味着用户正在将更多 Agent 运行纳入可Observation性覆盖范围，产品价值随之放大。

**Alert 触发准确率**（Alert Precision）衡量Alert系统的有效性。该指标定义为：真实触发Alert的事件数 ÷ 系统触发Alert的事件总数。Alert 系统基于 AlertField、AlertOperator、AlertTimeUnit 等枚举定义Alert规则 [Models/Common/Enums/AlertEnum.cs:3]，AlertController 提供AlertConfig的创建、更新、删除与记录查询接口 [API/Controllers/UserManagement/AlertController.cs:30]。高准确率意味着用户信任Alert系统，愿意将Alert纳入日常运维流程，减少误报与漏报带来的运维噪音。

两个指标构成"量"与"质"的双轮驱动：MATS 衡量可Observation性覆盖广度，Alert 准确率衡量Alert系统的可靠性。产品团队通过提升 Trace 采集的易用性与稳定性来驱动 MATS 增长，通过优化Alert规则引擎与阈值推荐算法来提升 Alert 准确率。

### 2.4. 用户角色与画像 (Persona 矩阵)

AgentInsightService（保持英文） 面向五类核心用户角色，每类角色在Privilege、使用场景与核心诉求上存在显著差异。角色定义基于 PGRole 枚举，包含 OWNER、ADMIN、MEMBER、VIEWER 四种角色 [Models/Common/Enums/UserEnum.cs:3]，此外还有匿名用户与 API Key User。

| Role | Privilege级别 | 核心场景 | 核心诉求 | 对应代码模块 |
|------|---------|---------|---------|-------------|
| OWNER（企业所有者） | 最高Privilege | 创建组织、管理订阅、分配管理员 | 掌控全局、成本可控、数据安全 | OrganizationController、ProductController |
| ADMIN（企业管理员） | 管理Privilege | 创建项目、邀请成员、Config Agent、管理Alert | 高效运维、快速定位、团队协作 | ProjectController、UserController、AlertController |
| MEMBER（成员）/ VIEWER（浏览者） | 协作/只读Privilege | 查看 Trace 数据、参与 Agent Session、查看Alert记录 | 数据可见、协作顺畅 | MetricsController、AgentSessionController |
| API Key User | 程序化访问 | CI/CD 集成、数据上报、自动化运维 | 接口稳定、鉴权安全 | UserController.CreateApiKey |
| 匿名用户 | 未注册/未登录 | 注册、登录、获取Captcha | 快速上手、低门槛体验 | CaptchaController、UserController.Login |

**OWNER（企业所有者）**

企业所有者是组织的创建者与最高管理者，拥有组织内的全部Privilege。其核心职责包括：创建组织（OrganizationController.Post [API/Controllers/UserManagement/OrganizationController.cs:28]）、管理订阅与配额（ProductController.Get [API/Controllers/ProductManagement/ProductController.cs:26]）、查看订单与Payment记录（OrderController.Get [API/Controllers/PaymentManagement/OrderController.cs:34]）。OWNER 关注的核心指标是 ROI（投入产出比），希望通过 AgentInsightService（保持英文） 降低 AI 应用的运维成本与故障时间，同时确保数据安全与合规。

**ADMIN（企业管理员）**

企业管理员是组织内的日常运营管理者，由 OWNER 分配角色。其核心职责包括：创建与管理项目（ProjectController.Create [API/Controllers/UserManagement/ProjectController.cs:31]）、邀请成员并分配角色（UserController.Invite [API/Controllers/UserManagement/UserController.cs:162]）、Config Agent 与数据源（AgentConfigController.Post [API/Controllers/AgentManagement/AgentConfigController.cs:54]）、创建与管理Alert规则（AlertController.Create [API/Controllers/UserManagement/AlertController.cs:61]）。ADMIN MTTR与Alert准确率，希望通过实时 Trace 与精准 Alert 快速定位并解决问题。

**MEMBER（成员）/ VIEWER（浏览者）**

成员与浏览者是组织内的协作角色。MEMBER 可以查看项目Trace数据、Alert记录，参与 Agent Session；VIEWER 仅具备只读Privilege。其核心操作包括：查看 Trace 数据（MetricsController.GetTraces [API/Controllers/DataManagement/MetricsController.cs:64]）、查看 Observation 与 Score 数据（MetricsController.GetObservations [API/Controllers/DataManagement/MetricsController.cs:34]）、管理个人 Agent Session（AgentSessionController.Get [API/Controllers/AgentManagement/AgentSessionController.cs:33]）。该角色关注的核心指标是数据可获取性与界面易用性。

**API Key User**

API Key 用户通过程序化方式访问平台能力，适用于 CI/CD 集成、自动化数据上报等场景。用户可以通过 UserController.CreateApiKey 创建 API Key [API/Controllers/UserManagement/UserController.cs:209]，并通过 API Key 调用公共Trace API 上报 Trace 数据。该角色关注的核心指标是接口稳定性、鉴权安全性与文档完善度。

**匿名用户**

匿名用户指尚未注册或未登录的访问者。他们可以通过 CaptchaController 获取Captcha完成注册 [API/Controllers/UserManagement/CaptchaController.cs:29]，或直接登录系统（UserController.Login [API/Controllers/UserManagement/UserController.cs:73]）。匿名用户的核心诉求是快速上手、低门槛体验产品功能。

### 2.5. 用户旅程

用户旅程覆盖从注册到持续使用的完整生命周期，分为五个关键阶段。每个阶段对应平台的具体功能模块与操作路径。

**阶段一：注册与组织创建**

匿名用户通过 CaptchaController 获取Captcha完成注册 [API/Controllers/UserManagement/CaptchaController.cs:29]，随后登录系统（UserController.Login [API/Controllers/UserManagement/UserController.cs:73]）。首次登录后，用户创建组织（OrganizationController.Post [API/Controllers/UserManagement/OrganizationController.cs:28]），系统自动将创建者设为 OWNER Role。组织创建成功后，OWNER 可以创建项目（ProjectController.Create [API/Controllers/UserManagement/ProjectController.cs:31]），项目是 Trace 数据隔离与配额管理的基本单元。

**阶段二：Agent Config与 SDK 集成**

管理员在项目中Config Agent 信息，包括数据源连接信息与默认模板（AgentConfigController.Post [API/Controllers/AgentManagement/AgentConfigController.cs:54]）。同时，管理员通过 UserController.CreateApiKey 创建 API Key [API/Controllers/UserManagement/UserController.cs:209]，用于 SDK 上报 Trace 数据时的身份认证。开发者将 agentinsight-sdk 集成到 AI 应用中，Config API Key 与上报端点，开始上报 Trace 数据。

**阶段三：Trace 数据上报与存储**

Agent 运行时通过 SDK 将 Trace 数据上报至平台。API 网关通过 YARP 反向代理将 `/api/public/{**catch-all}` 路径的请求转发至 AgentInsight-Langfuse-Cluster 集群。Trace 数据经处理后写入 ClickHouse 时序数据库，Session 元数据写入 PostgreSQL。Agents 子项目同时提供 OpenAI 兼容的 Chat Completions 端点（保持英文） [Agents/server.py:346]，支持 Agent Session的持久化存储 [Agents/server.py:614]。

**阶段四：监控、分析与Alert**

用户通过 MetricsController 查询 Trace、Observation、Score 数据 [API/Controllers/DataManagement/MetricsController.cs:34]，通过 AgentSessionController 查看Session详情 [API/Controllers/AgentManagement/AgentSessionController.cs:33]。管理员ConfigAlert规则（AlertController.Create [API/Controllers/UserManagement/AlertController.cs:61]），系统根据 AlertField、AlertOperator、AlertTimeUnit 等条件实时评估 Trace 数据，触发Alert后通过 System 或 SMS 通知用户 [Models/Common/Enums/AlertEnum.cs:39]。用户可以在 AlertController.GetRecords 查看Alert记录 [API/Controllers/UserManagement/AlertController.cs:128]。

**阶段五：订阅管理与配额升级**

当组织的 Agent 数量或 Trace 数据量接近配额上限时，OWNER 通过 ProductController 查看可用产品与时长选项 [API/Controllers/ProductManagement/ProductController.cs:26]，通过 OrderController.Place 下单购买 [API/Controllers/PaymentManagement/OrderController.cs:48]，Payment完成后系统自动更新组织配额。用户还可以通过 UserController.DeductMonthlyAgentRate 与 ValidateMonthlyAgentRate 管理 Agent 月度配额 [API/Controllers/UserManagement/UserController.cs:242][API/Controllers/UserManagement/UserController.cs:258]。

整个用户旅程形成闭环：从注册创建组织，到Config Agent 并集成 SDK，再到数据上报与监控Alert，最终通过订阅管理实现商业化闭环。每个阶段都有明确的用户角色参与、功能模块支撑与数据流转路径，确保用户能够快速上手并持续获得价值。

---

## 3. 功能需求

- **用户故事**: 作为已登录用户，我希望获取我当前的 Agent Config，以便查看数据源连接信息和默认模板设置。
- **主流程**:
  1. 用户发送 `GET /api/agent/config` 请求。
  2. `AgentConfigController.Get` 接收请求并调用 `_handler.GetConfig()` 方法 [API/Controllers/AgentManagement/AgentConfigController.cs:28]。
  3. `AgentConfigHandler.GetConfig` 从数据库查询当前用户的 AgentConfig 记录。
  4. 返回 `ApiResponse<AgentConfig>`，包含 `id`、`userid`、`datasource`、`defaulttemplateid`、`createdat`、`updatedat` 字段。
- **验收标准**:
  - [ ] AC1: 返回 HTTP 200，响应体为 `ApiResponse<AgentConfig>` 格式，`errorCode=0`。
  - [ ] AC2: 响应包含 `datasource` 字段（JSON 字符串）与 `defaulttemplateid` 字段。
  - [ ] AC3: 若当前用户不存在 Agent Config，返回 `errorCode=150022` (AgentConfigNotFound)。
- **业务规则**:
  - BR-001: 仅允许已认证用户访问，未携带有效 Token 时返回 `errorCode=100000` (UnAuthToken)。

#### 3.1.1. FR-002 删除当前用户的 Agent Config [优先级: Should]

- **用户故事**: 作为已登录用户，我希望删除我的 Agent Config，以便重置数据源设置。
- **主流程**:
  1. 用户发送 `GET /api/agent/config/delete` 请求。
  2. `AgentConfigController.Delete` 接收请求并调用 `_handler.DeleteConfig()` 方法 [API/Controllers/AgentManagement/AgentConfigController.cs:40]。
  3. `AgentConfigHandler.DeleteConfig` 删除当前用户的 AgentConfig 记录。
  4. 返回空数据 `ApiResponse<object>`。
- **验收标准**:
  - [ ] AC1: 返回 HTTP 200，响应体为 `ApiResponse<object>`，`errorCode=0`。
  - [ ] AC2: 删除后再次调用 FR-001 返回 `errorCode=150022` (AgentConfigNotFound)。
- **业务规则**:
  - BR-002: 仅允许删除当前用户自己的Config，不涉及其他用户数据。

#### 3.1.2. FR-003 创建或更新 Agent Config [优先级: Must]

- **用户故事**: 作为已登录用户，我希望创建或更新我的 Agent Config，以便设置数据源连接和默认模板。
- **主流程**:
  1. 用户发送 `POST /api/agent/config` 请求，请求体为 JSON 字符串，包含 `datasource` 与 `defaulttemplateid` 字段。
  2. `AgentConfigController.Post` 接收请求并调用 `_handler.CreateOrUpdateConfig(body)` 方法 [API/Controllers/AgentManagement/AgentConfigController.cs:54]。
  3. `AgentConfigHandler.CreateOrUpdateConfig` 判断Config是否存在：存在则更新，不存在则创建。
  4. 返回创建或更新后的 `AgentConfig` 对象。
- **验收标准**:
  - [ ] AC1: 返回 HTTP 200，响应体为 `ApiResponse<AgentConfig>`，`errorCode=0`。
  - [ ] AC2: 请求体 `datasource` 或 `defaulttemplateid` 为空时，对应字段保持不变（更新场景）。
  - [ ] AC3: 新建Config时，`userid` 自动取当前登录用户 ID。
- **业务规则**:
  - BR-003: Config内容为 JSON 字符串，服务端负责解析与校验。
  - BR-004: 每个用户仅存在一条 Agent Config记录。

#### 3.1.3. FR-004 获取 Agent Session列表或单个Session详情 [优先级: Must]

- **用户故事**: 作为已登录用户，我希望获取我的 Agent Session列表或查看某个Session的完整内容，以便回顾历史对话。
- **主流程**:
  1. 用户发送 `GET /api/agent/session` 请求，可选参数 `id`、`page`、`pageSize`。
  2. `AgentSessionController.Get` 接收请求并调用 `_handler.GetSessions(id, page.ToRealPage(), pageSize.ToRealPageSize())` 方法 [API/Controllers/AgentManagement/AgentSessionController.cs:33]。
  3. `AgentSessionHandler.GetSessions` 判断 `id` 是否为空：为空则返回当前用户所有Session列表（不包含 Context），不为空则返回对应Session全部内容（包含 Context）[API/Handlers/AgentManagement/AgentSessionHandler.cs:14]。
  4. 返回 `ApiResponse<AgentSession>`，包含分页信息。
- **验收标准**:
  - [ ] AC1: 返回 HTTP 200，响应体为 `ApiResponse<AgentSession>`，`errorCode=0`。
  - [ ] AC2: 列表模式按 `UpdatedAt` 倒序排列，且不包含 `Context` 字段。
  - [ ] AC3: 详情模式包含 `Context` 字段；若指定 `id` 不存在或不属于当前用户，返回 `errorCode=150021` (AgentSessionNotFound)。
- **业务规则**:
  - BR-005: 分页参数 `page` 默认值为 `AgentInsightConst.DefaultPage` (1)，`pageSize` 默认值为 `AgentInsightConst.DefaultPageSize` (10)。
  - BR-006: Session数据按用户隔离，仅返回当前用户名下的Session。

#### 3.1.4. FR-005 删除 Agent Session [优先级: Should]

- **用户故事**: 作为已登录用户，我希望批量删除我的 Agent Session，以便清理历史记录。
- **主流程**:
  1. 用户发送 `GET /api/agent/session/delete` 请求，参数 `ids` 为逗号分隔的Session ID 列表。
  2. `AgentSessionController.Delete` 接收请求并调用 `_handler.DeleteSessions(ids)` 方法 [API/Controllers/AgentManagement/AgentSessionController.cs:46]。
  3. `AgentSessionHandler.DeleteSessions` 将 `ids` 按逗号分割并去重，仅删除当前用户名下的Session [API/Handlers/AgentManagement/AgentSessionHandler.cs:36]。
  4. 返回空数据 `ApiResponse<object>`。
- **验收标准**:
  - [ ] AC1: 返回 HTTP 200，响应体为 `ApiResponse<object>`，`errorCode=0`。
  - [ ] AC2: `ids` 为空时直接返回，不执行删除操作。
  - [ ] AC3: 仅删除当前用户名下的Session，其他用户的Session不受影响。
- **业务规则**:
  - BR-007: 删除操作使用 `SqlFunc.ContainsArray` 进行批量匹配，确保 SQL 安全。

#### 3.1.5. FR-006 创建或更新 Agent Session [优先级: Must]

- **用户故事**: 作为已登录用户，我希望创建新Session或更新现有Session，以便保存对话上下文。
- **主流程**:
  1. 用户发送 `POST /api/agent/session` 请求，请求体为 `AgentSessionBody`，包含 `id`、`name`、`context` 字段。
  2. `AgentSessionController.Post` 接收请求并调用 `_handler.CreateOrUpdateSession(body)` 方法 [API/Controllers/AgentManagement/AgentSessionController.cs:60]。
  3. `AgentSessionHandler.CreateOrUpdateSession` 判断 `id` 是否为空：为空则创建新Session，不为空则更新现有Session [API/Handlers/AgentManagement/AgentSessionHandler.cs:53]。
  4. 返回创建或更新后的 `AgentSession` 对象。
- **验收标准**:
  - [ ] AC1: 返回 HTTP 200，响应体为 `ApiResponse<AgentSession>`，`errorCode=0`。
  - [ ] AC2: 创建时 `UserId` 自动取当前登录用户 ID。
  - [ ] AC3: 更新时若 `name` 或 `context` 为空，对应字段保持不变；若 `id` 不存在或不属于当前用户，返回 `errorCode=150021` (AgentSessionNotFound)。
- **业务规则**:
  - BR-008: 更新操作仅更新 `Name`、`Context`、`UpdatedAt` 三个字段。

#### 3.1.6. FR-007 获取 Agent 报表模板列表或单个模板详情 [优先级: Must]

- **用户故事**: 作为已登录用户，我希望获取报表模板列表或查看某个模板的完整内容，以便生成 Agent 报表。
- **主流程**:
  1. 用户发送 `GET /api/agent/report` 请求，可选参数 `id`、`includedpredefined`、`includedpredefinedonly`、`page`、`pageSize`。
  2. `AgentReportController.GetTemplates` 接收请求并调用 `_handler.GetTemplates(id, includedpredefined, includedpredefinedonly, page.ToRealPage(), pageSize.ToRealPageSize())` 方法 [API/Controllers/AgentManagement/AgentReportController.cs:35]。
  3. `AgentReportHandler.GetTemplates` 判断 `id` 是否为空：为空则返回模板列表（不包含 File），不为空则返回对应模板全部内容（包含 File）。
  4. 返回 `ApiResponse<AgentReportTemplate>`，包含分页信息。
- **验收标准**:
  - [ ] AC1: 返回 HTTP 200，响应体为 `ApiResponse<AgentReportTemplate>`，`errorCode=0`。
  - [ ] AC2: `includedpredefined=true` 时包含系统预定义模板；`includedpredefinedonly=true` 时仅返回系统预定义模板。
  - [ ] AC3: 指定 `id` 不存在或不属于当前用户时返回 `errorCode=150023` (AgentReportTemplateNotFound)。
- **业务规则**:
  - BR-009: 列表模式不包含 `File` 字段以减小响应体积；详情模式包含 `File` 字段。

#### 3.1.7. FR-008 删除 Agent 报表模板 [优先级: Should]

- **用户故事**: 作为已登录用户，我希望批量删除我的报表模板，以便清理不再使用的模板。
- **主流程**:
  1. 用户发送 `GET /api/agent/report/delete` 请求，参数 `ids` 为逗号分隔的模板 ID 列表。
  2. `AgentReportController.DeleteTemplates` 接收请求并调用 `_handler.DeleteTemplates(ids)` 方法 [API/Controllers/AgentManagement/AgentReportController.cs:48]。
  3. `AgentReportHandler.DeleteTemplates` 将 `ids` 按逗号分割并去重，仅删除当前用户名下的模板。
  4. 返回空数据 `ApiResponse<object>`。
- **验收标准**:
  - [ ] AC1: 返回 HTTP 200，响应体为 `ApiResponse<object>`，`errorCode=0`。
  - [ ] AC2: `ids` 为空时直接返回，不执行删除操作。
  - [ ] AC3: 仅删除当前用户名下的模板，其他用户的模板不受影响。
- **业务规则**:
  - BR-010: 系统预定义模板不可被删除。

#### 3.1.8. FR-009 创建或更新 Agent 报表模板 [优先级: Must]

- **用户故事**: 作为已登录用户，我希望创建新报表模板或更新现有模板，以便定制报表格式。
- **主流程**:
  1. 用户发送 `POST /api/agent/report` 请求，请求体为 `AgentReportTemplateBody`，包含 `id`、`name`、`category`、`file` 字段。
  2. `AgentReportController.CreateOrUpdateTemplate` 接收请求并调用 `_handler.CreateOrUpdateTemplate(body)` 方法 [API/Controllers/AgentManagement/AgentReportController.cs:62]。
  3. `AgentReportHandler.CreateOrUpdateTemplate` 判断 `id` 是否为空：为空则创建新模板，不为空则更新现有模板。
  4. 返回创建或更新后的 `AgentReportTemplate` 对象。
- **验收标准**:
  - [ ] AC1: 返回 HTTP 200，响应体为 `ApiResponse<AgentReportTemplate>`，`errorCode=0`。
  - [ ] AC2: `file` 为 PDF 文件内容的 base64 编码，`thumbnail` 由 `file` 自动生成。
  - [ ] AC3: 更新时若 `name` 或 `category` 为空，对应字段保持不变；若 `id` 不存在或不属于当前用户，返回 `errorCode=150023` (AgentReportTemplateNotFound)。
  - [ ] AC4: 模板名称为空时返回 `errorCode=150024` (EmptyAgentReportTemplateName)。
- **业务规则**:
  - BR-011: 模板名称必填，创建时若名称为空则抛出 `EmptyAgentReportTemplateName` 异常。

### 3.2. Data Management (数据管理)

Data Management 分组涵盖 Metrics/Model 相关端点，共 5 个 FR。

#### 3.2.1. FR-010 获取 Observations 列表 [优先级: Must]

- **用户故事**: 作为项目成员，我希望获取指定项目的 Observation 数据，以便分析 Agent 运行时的Observation信息。
- **主流程**:
  1. 用户发送 `GET /api/data/metrics/observations` 请求，携带项目 ID 与过滤条件。
  2. `MetricsController.GetObservations` 接收请求并调用 `_handler.GetObservations()` 方法 [API/Controllers/DataManagement/MetricsController.cs:34]。
  3. `MetricsHandler.GetObservations` 从 ClickHouse 查询 Observation 数据。
  4. 返回 `ApiResponse<Observation>`，包含分页信息。
- **验收标准**:
  - [ ] AC1: 返回 HTTP 200，响应体为 `ApiResponse<Observation>`，`errorCode=0`。
  - [ ] AC2: 支持按时间范围、Project ID 等条件过滤。
  - [ ] AC3: 未提供项目 ID 时返回 `errorCode=150000` (EmptyProjectId)。
- **业务规则**:
  - BR-012: 查询使用 ClickHouse 时序数据库，连接串Config为 `ConnectionStrings.ClickHouseDbConnection`。

#### 3.2.2. FR-011 获取 Scores 列表 [优先级: Must]

- **用户故事**: 作为项目成员，我希望获取指定项目的 Score 数据，以便评估 Agent 输出质量。
- **主流程**:
  1. 用户发送 `GET /api/data/metrics/scores` 请求，携带项目 ID 与过滤条件。
  2. `MetricsController.GetScores` 接收请求并调用 `_handler.GetScores()` 方法 [API/Controllers/DataManagement/MetricsController.cs:50]。
  3. `MetricsHandler.GetScores` 从 ClickHouse 查询 Score 数据。
  4. 返回 `ApiResponse<Score>`，包含分页信息。
- **验收标准**:
  - [ ] AC1: 返回 HTTP 200，响应体为 `ApiResponse<Score>`，`errorCode=0`。
  - [ ] AC2: 支持按时间范围、Project ID 等条件过滤。
  - [ ] AC3: 未提供项目 ID 时返回 `errorCode=150000` (EmptyProjectId)。
- **业务规则**:
  - BR-013: Score 数据与 Trace 关联，通过 `TraceId` 建立关联关系。

#### 3.2.3. FR-012 获取 Traces 列表 [优先级: Must]

- **用户故事**: 作为项目成员，我希望获取指定项目的 Trace 列表，以便Trace Agent 调用链路。
- **主流程**:
  1. 用户发送 `GET /api/data/metrics/traces` 请求，携带项目 ID 与过滤条件。
  2. `MetricsController.GetTraces` 接收请求并调用 `_handler.GetTraces()` 方法 [API/Controllers/DataManagement/MetricsController.cs:64]。
  3. `MetricsHandler.GetTraces` 从 ClickHouse 查询 Trace 数据，支持复杂过滤条件。
  4. 返回 `ApiResponse<Trace>`，包含分页信息。
- **验收标准**:
  - [ ] AC1: 返回 HTTP 200，响应体为 `ApiResponse<Trace>`，`errorCode=0`。
  - [ ] AC2: 支持按 `FilterColumn`、`FilterOperator`、`FilterType` 组合过滤。
  - [ ] AC3: 未提供项目 ID 时返回 `errorCode=150000` (EmptyProjectId)。
  - [ ] AC4: 过滤条件无效时返回对应错误码，如 `InvalidFilterType=150012`、`InvalidFilterColumn=150013`、`InvalidFilterOperator=150014`、`InvalidFilterValue=150015`。
- **业务规则**:
  - BR-014: 过滤条件基于 `FilterType`、`FilterOperator`、`FilterColumn` 枚举定义 [Models/Common/Enums/FilterEnum.cs:8]。
  - BR-015: 排序方式支持 `orderby` 参数，默认为 `-updatedat`。

#### 3.2.4. FR-013 查询 Traces (POST) [优先级: Must]

- **用户故事**: 作为项目成员，我希望通过 POST 请求查询 Traces，以便使用更复杂的查询条件。
- **主流程**:
  1. 用户发送 `POST /api/data/metrics/traces` 请求，请求体包含查询条件。
  2. `MetricsController.GetTraces` 接收请求并调用 `_handler.GetTraces()` 方法 [API/Controllers/DataManagement/MetricsController.cs:125]。
  3. `MetricsHandler.GetTraces` 从 ClickHouse 查询 Trace 数据。
  4. 返回 `ApiResponse<Trace>`，包含分页信息。
- **验收标准**:
  - [ ] AC1: 返回 HTTP 200，响应体为 `ApiResponse<Trace>`，`errorCode=0`。
  - [ ] AC2: 请求体支持 `traceIds` 数组，一次最多查询 100 个 Trace。
  - [ ] AC3: `traceIds` 为空时返回 `errorCode=150009` (EmptyTraceIds)；超过 100 个时返回 `errorCode=150011` (TooManyTraceIds)。
- **业务规则**:
  - BR-016: 单次查询 Trace 数量上限为 100，超过时抛出 `TooManyTraceIds` 异常。

#### 3.2.5. FR-014 获取模型列表 [优先级: Must]

- **用户故事**: 作为项目成员，我希望获取模型列表，以便查看模型定价与Config信息。
- **主流程**:
  1. 用户发送 `GET /api/data/model` 请求，可选参数 `keyword`、`projectid`、`includedpredefined`、`orderby`、`page`、`pageSize`。
  2. `ModelController.Get` 接收请求并调用 `_handler.Get()` 方法 [API/Controllers/DataManagement/ModelController.cs:34]。
  3. `ModelHandler.Get` 从数据库查询 `ModelDefinition` 列表。
  4. 返回 `ApiResponse<ModelDefinition>`，包含分页信息。
- **验收标准**:
  - [ ] AC1: 返回 HTTP 200，响应体为 `ApiResponse<ModelDefinition>`，`errorCode=0`。
  - [ ] AC2: `projectid` 为空且 `includedpredefined=false` 时返回错误，要求提供项目 ID。
  - [ ] AC3: `includedpredefined=true` 时同时返回预定义模型（`projectid=null` 的模型）与项目专属模型。
  - [ ] AC4: 响应包含 `modelname`、`inputprice`、`outputprice`、`totalprice`、`unit`、`pricingtiers` 等字段。
- **业务规则**:
  - BR-017: `orderby` 支持 `createdat`、`-createdat`、`-updatedat` 等排序方式，默认为 `-updatedat`。

### 3.3. Payment Management (Payment管理)

Payment Management 分组涵盖 Notify/Order 相关端点，共 6 个 FR。

#### 3.3.1. FR-015 微信Payment回调通知 [优先级: Must]

- **用户故事**: 作为Payment系统，我希望接收微信Payment回调通知，以便更新订单状态。
- **主流程**:
  1. 微信Payment平台发送 `POST /api/payment/notify/wechatnotify` 请求，携带Payment结果通知。
  2. `NotifyController.WeChatNotify` 接收请求并调用 `_handler.WeChatNotify()` 方法 [API/Controllers/PaymentManagement/NotifyController.cs:29]。
  3. `NotifyHandler.WeChatNotify` 验证通知签名，解析Payment结果，更新订单状态。
  4. 返回处理结果给微信Payment平台。
- **验收标准**:
  - [ ] AC1: 返回 HTTP 200，响应体包含处理结果。
  - [ ] AC2: 签名验证失败时返回 `errorCode=620002` (ExamineWeChatSignatureFailed)。
  - [ ] AC3: 通知内容为空时返回 `errorCode=810018` (EmptyWeChatNotify)。
  - [ ] AC4: 订单状态更新失败时返回 `errorCode=810026` (OrderStateUpdateFailed)。
- **业务规则**:
  - BR-018: 回调通知使用微信Payment证书进行签名验证，证书Config缺失时返回 `errorCode=620016` (InvalidPayCertificate)。

#### 3.3.2. FR-016 Payment宝Payment回调通知 [优先级: Must]

- **用户故事**: 作为Payment系统，我希望接收Payment宝Payment回调通知，以便更新订单状态。
- **主流程**:
  1. Payment宝平台发送 `POST /api/payment/notify/alipaynotify` 请求，携带Payment结果通知。
  2. `NotifyController.AlipayNotify` 接收请求并调用 `_handler.AlipayNotify()` 方法 [API/Controllers/PaymentManagement/NotifyController.cs:57]。
  3. `NotifyHandler.AlipayNotify` 验证通知签名，解析Payment结果，更新订单状态。
  4. 返回处理结果给Payment宝平台。
- **验收标准**:
  - [ ] AC1: 返回 HTTP 200，响应体包含处理结果。
  - [ ] AC2: 签名验证失败时返回 `errorCode=810007` (AlipaySignatureError)。
  - [ ] AC3: Payment宝Config缺失时返回 `errorCode=810002` (AlipaySettingNotConfig)。
  - [ ] AC4: 交易号无效时返回 `errorCode=810005` (InvalidAlipayTradeNo)。
- **业务规则**:
  - BR-019: 回调通知使用Payment宝 SDK 进行签名验证，SDK 为 AlipaySDKNet.Standard。

#### 3.3.3. FR-017 获取订单列表 [优先级: Must]

- **用户故事**: 作为企业管理员，我希望获取订单列表，以便查看订阅购买记录。
- **主流程**:
  1. 用户发送 `GET /api/payment/order` 请求。
  2. `OrderController.Get` 接收请求并调用 `_handler.Get()` 方法 [API/Controllers/PaymentManagement/OrderController.cs:34]。
  3. `OrderHandler.Get` 从数据库查询订单列表。
  4. 返回 `ApiResponse<Order>`，包含分页信息。
- **验收标准**:
  - [ ] AC1: 返回 HTTP 200，响应体为 `ApiResponse<Order>`，`errorCode=0`。
  - [ ] AC2: 响应包含 `orderno`、`productid`、`amount`、`state` 等字段。
  - [ ] AC3: 仅返回当前用户所属组织的订单。
- **业务规则**:
  - BR-020: 订单状态使用 `OrderState` 枚举定义 [Models/Common/Enums/PaymentEnums.cs:40]。

#### 3.3.4. FR-018 下单 [优先级: Must]

- **用户故事**: 作为企业管理员，我希望下单购买产品，以便开通订阅服务。
- **主流程**:
  1. 用户发送 `POST /api/payment/order` 请求，请求体包含产品 ID、时长 ID 等信息。
  2. `OrderController.Place` 接收请求并调用 `_handler.Place()` 方法 [API/Controllers/PaymentManagement/OrderController.cs:48]。
  3. `OrderHandler.Place` 校验产品与时长信息，创建订单，调用Payment接口。
  4. 返回订单信息与Payment参数。
- **验收标准**:
  - [ ] AC1: 返回 HTTP 200，响应体为 `ApiResponse<Order>`，`errorCode=0`。
  - [ ] AC2: 产品不存在时返回 `errorCode=810013` (ProductNotExist)。
  - [ ] AC3: 产品时长不存在时返回 `errorCode=810014` (ProductDurationNotExist)。
  - [ ] AC4: 不支持的Payment方式时返回 `errorCode=810019` (UnsupportedPayMethod)。
  - [ ] AC5: 降级产品时返回 `errorCode=810023` (CannotDowngradeProduct)。
- **业务规则**:
  - BR-021: Payment方式支持 `SubPayMethod` 枚举定义，包括 WECHAT_JSAPI、WECHAT_NATIVE、WECHAT_MINIPROGRAM、ALIPAY_FAST_INSTANT_TRADE_PAY [Models/Common/Enums/PaymentEnums.cs:29]。

#### 3.3.5. FR-019 查询订单状态 [优先级: Must]

- **用户故事**: 作为企业管理员，我希望查询订单状态，以便确认Payment是否成功。
- **主流程**:
  1. 用户发送 `GET /api/payment/order/query` 请求，携带订单号。
  2. `OrderController.Query` 接收请求并调用 `_handler.Query()` 方法 [API/Controllers/PaymentManagement/OrderController.cs:64]。
  3. `OrderHandler.Query` 查询订单状态，必要时调用Payment平台查询接口。
  4. 返回订单最新状态。
- **验收标准**:
  - [ ] AC1: 返回 HTTP 200，响应体为 `ApiResponse<Order>`，`errorCode=0`。
  - [ ] AC2: 订单号为空时返回 `errorCode=810011` (EmptyOrderNo)。
  - [ ] AC3: 订单不存在时返回 `errorCode=810015` (OrderNotExist)。
- **业务规则**:
  - BR-022: 查询操作记录审计日志，`AuditAction.Query` [Models/Common/Enums/AuditEnum.cs:3]。

#### 3.3.6. FR-020 获取订单转化率 [优先级: Should]

- **用户故事**: 作为企业管理员，我希望获取订单转化率，以便评估营销效果。
- **主流程**:
  1. 用户发送 `GET /api/payment/order/conversion` 请求。
  2. `OrderController.GetConversion` 接收请求并调用 `_handler.GetConversion()` 方法 [API/Controllers/PaymentManagement/OrderController.cs:79]。
  3. `OrderHandler.GetConversion` 统计订单转化率数据。
  4. 返回转化率统计结果。
- **验收标准**:
  - [ ] AC1: 返回 HTTP 200，响应体为 `ApiResponse<ConversionRate>`，`errorCode=0`。
  - [ ] AC2: 响应包含总订单数、成功订单数、转化率等字段。
- **业务规则**:
  - BR-023: 转化率 = 成功订单数 / 总订单数 × 100%。

### 3.4. Product Management (产品管理)

Product Management 分组涵盖 Product 相关端点，共 2 个 FR。

#### 3.4.1. FR-021 获取产品列表 [优先级: Must]

- **用户故事**: 作为企业管理员，我希望获取产品列表，以便了解可购买的订阅套餐。
- **主流程**:
  1. 用户发送 `GET /api/product` 请求。
  2. `ProductController.Get` 接收请求并调用 `_handler.GetProducts()` 方法 [API/Controllers/ProductManagement/ProductController.cs:26]。
  3. `ProductHandler.GetProducts` 从数据库查询 `AgentInsightProduct` 列表。
  4. 返回产品列表。
- **验收标准**:
  - [ ] AC1: 返回 HTTP 200，响应体为 `ApiResponse<AgentInsightProduct>`，`errorCode=0`。
  - [ ] AC2: 响应包含 `name`、`type`、`price`、`monthlyrate`、`permanentrate`、`projectlimit`、`headcountlimit`、`orglimit`、`agentlimit`、`level` 字段。
  - [ ] AC3: `type` 字段取值：0=None、1=Monthly、2=Permanent。
- **业务规则**:
  - BR-024: 产品列表对所有已认证用户开放，无需特定角色。

#### 3.4.2. FR-022 获取产品时长列表 [优先级: Must]

- **用户故事**: 作为企业管理员，我希望获取产品时长列表，以便选择订阅时长。
- **主流程**:
  1. 用户发送 `GET /api/product/duration` 请求。
  2. `ProductController.GetDuration` 接收请求并调用 `_handler.GetProductDurations()` 方法 [API/Controllers/ProductManagement/ProductController.cs:38]。
  3. `ProductHandler.GetProductDurations` 从数据库查询 `AgentInsightProductDuration` 列表。
  4. 返回产品时长列表。
- **验收标准**:
  - [ ] AC1: 返回 HTTP 200，响应体为 `ApiResponse<AgentInsightProductDuration>`，`errorCode=0`。
  - [ ] AC2: 响应包含 `name`、`quantity`、`discount` 字段。
- **业务规则**:
  - BR-025: 产品时长与产品关联，下单时需同时指定产品与时长。

### 3.5. Tools Management (工具管理)

Tools Management 分组涵盖 Bulletin/Health/WeChat 相关端点，共 10 个 FR。

#### 3.5.1. FR-023 发布Bulletin [优先级: Should]

- **用户故事**: 作为企业管理员，我希望发布Bulletin，以便通知用户重要信息。
- **主流程**:
  1. 用户发送 `POST /api/tools/bulletin` 请求，请求体包含Bulletin内容。
  2. `BulletinController.Post` 接收请求并调用 `_handler.Post()` 方法 [API/Controllers/ToolsManagement/BulletinController.cs:32]。
  3. `BulletinHandler.Post` 创建Bulletin记录。
  4. 返回创建后的Bulletin信息。
- **验收标准**:
  - [ ] AC1: 返回 HTTP 200，响应体为 `ApiResponse<Bulletin>`，`errorCode=0`。
  - [ ] AC2: Bulletin创建后状态为待审核。
- **业务规则**:
  - BR-026: Bulletin发布后需经过审核方可对外可见。

#### 3.5.2. FR-024 获取用户协议 [优先级: Must]

- **用户故事**: 作为匿名用户，我希望获取用户协议，以便了解服务条款。
- **主流程**:
  1. 用户发送 `GET /api/tools/bulletin/agreement` 请求。
  2. `BulletinController.Get` 接收请求并调用 `_handler.Get()` 方法 [API/Controllers/ToolsManagement/BulletinController.cs:45]。
  3. `BulletinHandler.Get` 查询最新的用户协议。
  4. 返回协议内容。
- **验收标准**:
  - [ ] AC1: 返回 HTTP 200，响应体为 `ApiResponse<Bulletin>`，`errorCode=0`。
  - [ ] AC2: 无需认证即可访问。
- **业务规则**:
  - BR-027: 用户协议为系统预定义Bulletin，不可被用户删除。

#### 3.5.3. FR-025 获取Bulletin列表 [优先级: Must]

- **用户故事**: 作为已登录用户，我希望获取Bulletin列表，以便了解平台动态。
- **主流程**:
  1. 用户发送 `GET /api/tools/bulletin/bulletins` 请求。
  2. `BulletinController.GetBulletins` 接收请求并调用 `_handler.GetBulletins()` 方法 [API/Controllers/ToolsManagement/BulletinController.cs:64]。
  3. `BulletinHandler.GetBulletins` 查询已审核通过的Bulletin列表。
  4. 返回Bulletin列表。
- **验收标准**:
  - [ ] AC1: 返回 HTTP 200，响应体为 `ApiResponse<Bulletin>`，`errorCode=0`。
  - [ ] AC2: 仅返回状态为已审核的Bulletin。
- **业务规则**:
  - BR-028: Bulletin列表按发布时间倒序排列。

#### 3.5.4. FR-026 获取后台Bulletin列表 [优先级: Should]

- **用户故事**: 作为企业管理员，我希望获取后台Bulletin列表，以便管理所有Bulletin。
- **主流程**:
  1. 用户发送 `GET /api/tools/bulletin/backend` 请求。
  2. `BulletinController.GetBackendBulletins` 接收请求并调用 `_handler.GetBackendBulletins()` 方法 [API/Controllers/ToolsManagement/BulletinController.cs:82]。
  3. `BulletinHandler.GetBackendBulletins` 查询所有Bulletin（含待审核与已关闭）。
  4. 返回Bulletin列表。
- **验收标准**:
  - [ ] AC1: 返回 HTTP 200，响应体为 `ApiResponse<Bulletin>`，`errorCode=0`。
  - [ ] AC2: 包含所有状态的Bulletin。
- **业务规则**:
  - BR-029: 仅 OWNER / ADMIN 角色可访问后台Bulletin列表。

#### 3.5.5. FR-027 审核Bulletin [优先级: Should]

- **用户故事**: 作为企业管理员，我希望审核Bulletin，以便控制Bulletin发布质量。
- **主流程**:
  1. 用户发送 `POST /api/tools/bulletin/approve` 请求，携带Bulletin ID。
  2. `BulletinController.ApproveBulletin` 接收请求并调用 `_handler.ApproveBulletin()` 方法 [API/Controllers/ToolsManagement/BulletinController.cs:96]。
  3. `BulletinHandler.ApproveBulletin` 更新Bulletin状态为已审核。
  4. 返回更新后的Bulletin信息。
- **验收标准**:
  - [ ] AC1: 返回 HTTP 200，响应体为 `ApiResponse<Bulletin>`，`errorCode=0`。
  - [ ] AC2: Bulletin审核后状态变为已审核。
- **业务规则**:
  - BR-030: 仅 OWNER / ADMIN 角色可执行审核操作。

#### 3.5.6. FR-028 修订Bulletin [优先级: Should]

- **用户故事**: 作为企业管理员，我希望修订Bulletin，以便更正Bulletin内容。
- **主流程**:
  1. 用户发送 `POST /api/tools/bulletin/revision` 请求，携带Bulletin ID 与修订内容。
  2. `BulletinController.ReviseBulletin` 接收请求并调用 `_handler.ReviseBulletin()` 方法 [API/Controllers/ToolsManagement/BulletinController.cs:110]。
  3. `BulletinHandler.ReviseBulletin` 更新Bulletin内容并重置状态为待审核。
  4. 返回更新后的Bulletin信息。
- **验收标准**:
  - [ ] AC1: 返回 HTTP 200，响应体为 `ApiResponse<Bulletin>`，`errorCode=

---

## 4. 非功能需求

### 4.1. 性能 (Performance)

性能需求聚焦 Trace 查询、指标聚合与 Agent 推理服务的端到端延迟与吞吐量。ClickHouse 作为时序数据存储，承载 Trace、Observation、Score 等核心可Observation性数据的写入与查询，其连接池Config为 `PoolSize=10;MaxPoolSize=50;ConnectionTimeout=30;CommandTimeout=60`（`ConnectionStrings.ClickHouseDbConnection`），为查询延迟提供了基础保障。MetricsController 提供 Trace 查询与指标聚合接口，其中 `GetObservations` 与 `GetScores` 均通过 `MetricsHandler` 调用 ClickHouse 进行分页查询（`API/Controllers/DataManagement/MetricsController.cs:34`），查询路径包含 TraceId 过滤与 `IsDeleted` 条件，确保数据精确性。`GetTraces` 支持按 ID、名称、时间范围及自定义条件过滤（`API/Controllers/DataManagement/MetricsController.cs:64`），当查询超时或条件非法时，系统抛出 `ClickHouseQueryTimeout = 150017` 或 `InvalidFilterType = 150012` 等异常（`Models/Common/Enums/ExceptionCodes.cs:6`），为性能监控提供了明确的错误信号。

| 编号 | Metric | 目标值 | 验证方式 |
|------|------|--------|----------|
| NFR-P-001 | Trace P95 | ≤ 2s，在 `ClickHouseQueryTimeout=150017` 阈值内 | 使用 JMeter 或 k6 对 `GET /api/data/metrics/traces` 进行压测，模拟 100 并发用户，统计 P95 延迟 |
| NFR-P-002 | Observation P95 | ≤ 1s | 对 `GET /api/data/metrics/observations` 进行压测，单 Trace 下 10,000 条 Observation 数据 |
| NFR-P-003 | Score P95 | ≤ 1s | 对 `GET /api/data/metrics/scores` 进行压测，单 Trace 下 5,000 条 Score 数据 |
| NFR-P-004 | Agent Chat Completions 首 Token P95 | ≤ 3s | 对 `POST /api/agent/insight`（`Agents/server.py:346`）进行压测，模拟 50 并发请求 |
| NFR-P-005 | Trace 数据写入吞吐量 | ≥ 1,000 条/秒 | 使用数据上报脚本（如 `agentinsight-sdk` 批量发送）向公共Trace API 持续写入 Trace，统计 ClickHouse 写入吞吐量 |
| NFR-P-006 | 分页查询默认页大小 | 默认 10 条/页，最大 100 条/页 | 代码审查确认 `AgentInsightConst.DefaultPageSize` 常量值 |

### 4.2. 可用性 (Availability)

可用性需求确保系统在单点故障或依赖服务异常时仍能提供核心功能。系统依赖 Redis 作为缓存与消息队列（`Redis.ConnectionString = localhost:${REDIS_PORT},password=${REDIS_AUTH}`），ClickHouse 存储 Trace 时序数据，PostgreSQL 存储用户/Config/订单数据。`HealthController` 提供 `GET /api/tools/health` 健康检查端点（`API/Controllers/ToolsManagement/HealthController.cs:20`），用于负载均衡器或容器编排系统的存活探针。日志系统采用文件滚动策略，`Logging.File.FileName = logs/application-.log`，单文件大小限制 10MB，最大滚动文件数 30（`Logging.File.FileSizeLimitBytes = 10485760; MaxRollingFiles = 30`），避免日志文件无限增长导致磁盘耗尽。

| 编号 | Metric | 目标值 | 验证方式 |
|------|------|--------|----------|
| NFR-A-001 | 系统可用性 | ≥ 99.9%（月度） | 监控 `GET /api/tools/health` 端点，统计月度不可用时长 |
| NFR-A-002 | 健康检查响应时间 | ≤ 500ms | 对 `GET /api/tools/health` 进行监控，P95 延迟不超过 500ms |
| NFR-A-003 | 日志文件滚动 | 单文件 ≤ 10MB，保留最近 30 个文件 | 检查 `logs/` 目录，确认文件大小与数量符合Config |
| NFR-A-004 | 数据库连接池可用性 | PostgreSQL 连接池 MinPoolSize=10, MaxPoolSize=200 | 监控连接池使用率，确认无连接耗尽导致的 5xx 错误 |
| NFR-A-005 | Redis 故障降级 | 缓存不可用时，核心 API 仍可返回数据（降级为直查数据库） | 模拟 Redis 宕机，验证 `GET /api/user` 等接口仍可用 |

### 4.3. 安全 (Security)

安全需求覆盖认证、授权、数据加密与Payment安全。系统采用 JWT 认证，Token有效期 43200 秒（12 小时），算法 HS256（`JWTSettings.ExpiredTime = 43200; JWTSettings.Algorithm = HS256`），并启用 Audience、Issuer、SigningKey 与 Lifetime 校验（`JWTSettings.ValidateAudience = True; ValidateIssuer = True; ValidateIssuerSigningKey = True; ValidateLifetime = True`）。用户登录接口 `POST /api/user/login` 支持密码、短信、微信、小程序与 API Key 五种登录方式（`API/Controllers/UserManagement/UserController.cs:73`），其中 API Key 登录需在 Authorization 头携带 Basic publickey:secretkey。Payment回调接口 `POST /api/payment/notify/wechatnotify` 与 `POST /api/payment/notify/alipaynotify`（`API/Controllers/PaymentManagement/NotifyController.cs:29`）需验证签名，防止伪造回调。CaptchaConfig为图形Captcha长度 5 位、邮箱Captcha 6 位、短信Captcha 6 位，有效期 300 秒，重发间隔 60 秒（`CaptchaSetting.CaptchaCodeLength = 5; EmailCodeLength = 6; SMSCodeLength = 6; ExpiredSeconds = 300; ResendInterval = 60`）。

| 编号 | Metric | 目标值 | 验证方式 |
|------|------|--------|----------|
| NFR-S-001 | JWT 认证 | Token有效期 43200 秒，算法 HS256 | 代码审查确认 `JWTSettings` Config；使用过期Token调用 API 验证返回 `UnAuthToken = 100000` |
| NFR-S-002 | 密码存储 | 密码必须哈希存储，禁止明文 | 代码审查确认 `PasswordHashFailed = 990003` 异常路径；检查数据库用户表密码字段 |
| NFR-S-003 | API Key 认证 | API Key 登录需 Basic 认证（publickey:secretkey） | 调用 `POST /api/user/login`（logintype=5），验证无 Authorization 头时返回 `InvalidApiKey = 100038` |
| NFR-S-004 | Payment回调签名验证 | 微信/Payment宝回调必须验证签名，失败返回 `InvalidWeChatNotify = 810010` / `AlipaySignatureError = 810007` | 构造伪造签名回调，验证返回对应错误码 |
| NFR-S-005 | Captcha安全 | 图形Captcha 5 位，有效期 300 秒，重发间隔 60 秒 | 调用 `GET /api/captcha` 与 `GET /api/captcha/sms`，验证Captcha长度与重发限制 |
| NFR-S-006 | SQL 注入防护 | 所有数据库查询必须使用 ORM 参数化查询 | 代码审查确认 SqlSugar ORM 使用参数化查询；使用 SQLMap 进行渗透测试 |
| NFR-S-007 | 敏感数据脱敏 | Admin 后台列表不展示敏感数据明文 | 代码审查确认 Admin Config（`Admin/Agents.md` 安全工程师检查项） |

### 4.4. 可扩展性 (Scalability)

可扩展性需求确保系统在数据量增长与用户规模扩大时保持稳定。ClickHouse 连接池支持 10-50 的动态扩展（`ConnectionStrings.ClickHouseDbConnection` 中 `PoolSize=10;MaxPoolSize=50`），PostgreSQL 连接池支持 10-200 的扩展（`ConnectionStrings.UserDbConnection` 中 `MinPoolSize=10;MaxPoolSize=200`）。Redis BullMq支撑异步任务处理，`BullMqService` 提供 `EnqueueProjectDeleteAsync` 与 `EnqueueTraceIngestionAsync` 等队列操作，实现 Trace 数据异步写入，避免同步阻塞。YARP 反向代理Config了 `/api/public/{**catch-all}` 与 `/public/{**catch-all}` 路由（`ReverseProxy.Routes.AgentInsight-Route-API.Match.Path`），支持将公共 API 请求转发至 Langfuse 集群，实现水平扩展。

| 编号 | Metric | 目标值 | 验证方式 |
|------|------|--------|----------|
| NFR-SC-001 | ClickHouse 连接池扩展 | 连接池范围 10-50，支持动态扩展 | 监控连接池使用率，确认达到上限时自动扩展 |
| NFR-SC-002 | PostgreSQL 连接池扩展 | 连接池范围 10-200，支持动态扩展 | 监控连接池使用率，确认达到上限时自动扩展 |
| NFR-SC-003 | Trace 数据异步写入 | Trace 数据通过 BullMq 异步写入，不阻塞主流程 | 代码审查确认 `EnqueueTraceIngestionAsync` 调用路径；压测确认写入延迟不随请求量线性增长 |
| NFR-SC-004 | 反向代理水平扩展 | YARP 支持将公共 API 请求转发至独立集群 | 验证 `/api/public/{**catch-all}` 路由转发至 `AgentInsight-Langfuse-Cluster` |
| NFR-SC-005 | Agent 服务水平扩展 | Agents 子项目支持多实例部署，Session数据持久化 | 部署多个 Agents 实例，验证 `GET /api/sessions`（`Agents/server.py:614`）返回一致数据 |

### 4.5. 可维护性 (Maintainability)

可维护性需求确保系统易于诊断、监控与升级。系统采用结构化日志，日志级别可Config（`Logging.LogLevel.Default = Warning`），文件日志最低级别为 Information（`Logging.File.MinimumLevel = Information`），支持按天滚动。API 文档通过 Swagger 分组管理，`SpecificationDocumentSettings.GroupOpenApiInfos` Config了 User、Data、Agent 等分组（`SpecificationDocumentSettings.RoutePrefix = api`），便于开发者查阅。Config管理支持环境变量占位符（如 `${JWT_SIGNING_KEY}`、`${CLICKHOUSE_HOST}`），敏感信息不硬编码在代码中。代码仓库包含 `UnitTest` 目录，Admin 子项目要求单元测试通过率 100%、行覆盖率 ≥ 80%（`Admin/Agents.md` 代码评审通过标准）。

| 编号 | Metric | 目标值 | 验证方式 |
|------|------|--------|----------|
| NFR-M-001 | 日志可Config性 | 日志级别与输出目标可通过Config调整 | 修改 `Logging.LogLevel.Default` Config，验证日志输出变化 |
| NFR-M-002 | API 文档完整性 | 所有 Controller 必须包含 Swagger 分组与描述 | 访问 Swagger UI，确认 User/Data/Agent/Payment 等分组完整 |
| NFR-M-003 | Config外部化 | 敏感Config（密钥、连接串）必须使用环境变量占位符 | 代码审查确认 `${JWT_SIGNING_KEY}`、`${CLICKHOUSE_HOST}` 等占位符 |
| NFR-M-004 | 单元测试覆盖率 | Admin 子项目行覆盖率 ≥ 80%，通过率 100% | 运行 `python -m pytest app/tests.py -v --cov=app --cov-report=term-missing` |
| NFR-M-005 | 代码风格规范 | Admin 子项目通过 flake8 与 black 检查 | 运行 `flake8 app/ --max-line-length=120` 与 `black app/ --check --line-length=120` |

### 4.6. 兼容性 (Compatibility)

兼容性需求确保系统在不同客户端、浏览器与 API 版本下正常工作。Agents 子项目提供 OpenAI 兼容的 Chat Completions 端点（保持英文）（`Agents/server.py:346`），支持标准 OpenAI SDK 接入。系统支持微信小程序、微信公众号、Payment宝等多种Payment渠道，`SubPayMethod` 枚举定义了 `WECHAT_JSAPI = 1`、`WECHAT_NATIVE = 2`、`WECHAT_MINIPROGRAM = 3`、`ALIPAY_FAST_INSTANT_TRADE_PAY = 11`（`Models/Common/Enums/PaymentEnums.cs:29`），覆盖主流Payment场景。API 响应格式统一为 `ApiResponse<T>` 包装结构，包含 `errorCode` 字段，客户端可根据错误码进行差异化处理。反向代理Config支持将 `/api/public/` 与 `/public/` 路径转发至 Langfuse 集群，兼容 Langfuse 生态的Trace数据上报。

| 编号 | Metric | 目标值 | 验证方式 |
|------|------|--------|----------|
| NFR-C-001 | OpenAI API 兼容性 | `POST /api/agent/insight` 兼容 OpenAI Chat Completions 协议 | 使用 OpenAI SDK 调用该端点，验证请求/响应格式兼容 |
| NFR-C-002 | Payment渠道兼容 | 支持微信 JSAPI/Native/小程序与Payment宝即时到账 | 分别发起四种Payment方式，验证下单与回调流程 |
| NFR-C-003 | API 响应格式统一 | 所有 API 返回 `ApiResponse<T>` 结构，包含 `errorCode` | 代码审查确认所有 Controller 返回 `ApiResponse<T>` |
| NFR-C-004 | Langfuse 兼容 | `/api/public/{**catch-all}` 路由转发至 Langfuse 集群 | 发送 Trace 数据至 `/api/public/` 路径，验证 Langfuse 集群收到数据 |
| NFR-C-005 | 浏览器兼容 | Admin 后台兼容 Chrome/Firefox/Safari 最新两个主版本 | 使用三大浏览器访问 Admin 后台，验证功能正常 |

### 4.7. 本地化 (Localization)

本地化需求确保系统支持多语言与多区域文化。系统Config了本地化支持，`LocalizationSettings.SupportedCultures = ['zh-CN', 'zh-TW', 'zh-HK', 'en']`，默认文化为 `zh-CN`（`LocalizationSettings.DefaultCulture = zh-CN`），语言文件前缀为 `Text`（`LocalizationSettings.LanguageFilePrefix = Text`）。本地化资源文件存放在 `Resources` 目录（`ConfigurationScanDirectories = ['Configurations', 'Resources']`），支持 JSON 格式的语言文件。Captcha短信与邮件内容需根据当前文化输出对应语言。

| 编号 | Metric | 目标值 | 验证方式 |
|------|------|--------|----------|
| NFR-L-001 | 支持文化 | 支持 zh-CN, zh-TW, zh-HK, en 四种文化 | 代码审查确认 `LocalizationSettings.SupportedCultures` Config；切换 `Accept-Language` 头验证响应语言 |
| NFR-L-002 | 默认文化 | 默认文化为 zh-CN | 无 `Accept-Language` 头时，验证响应使用简体中文 |
| NFR-L-003 | 语言文件管理 | 语言文件使用 JSON 格式，前缀为 `Text` | 检查 `Resources` 目录，确认语言文件命名与格式 |
| NFR-L-004 | Captcha本地化 | 短信/邮箱Captcha内容根据当前文化输出对应语言 | 分别设置 zh-CN 与 en 文化，触发短信Captcha，验证内容语言 |

---

## 5. 接口需求

用 `IPaymentService.SaveWeChatNotify` 持久化微信Payment通知数据 [API/Notifications/WeChatNotifyReceivedHandler.cs]。

该事件处理机制内置重试策略，`MaxRetries` 常量设为 3，重试延迟分别为 1 秒、3 秒、5 秒。当 `SaveWeChatNotify` 抛出异常时，Handler捕获异常并记录日志，若 `RetryCount` 未超过上限则递归调用自身进行重试 [API/Notifications/WeChatNotifyReceivedHandler.cs]。此设计确保Payment通知在瞬时故障场景下不丢失，满足Payment场景的数据一致性要求。

事件通知机制同样用于Payment事务处理。`PaymentService` 在订单状态变更时发布 `PaymentTransactionNotification`，该通知包含 `TransactionType` 枚举（`WeChatTransaction` / `AlipayTransaction`），用于区分不同Payment渠道的事务类型 [API/Notifications/PaymentTransactionNotification.cs:9]。

#### 5.1.1. BullMqService 队列

`BullMqService` 是基于 Redis 的消息队列服务，封装项目删除与 Trace 数据摄入等异步任务。该服务通过 `EnqueueProjectDeleteAsync` 方法将项目删除任务投递到队列，由后台消费者异步执行删除逻辑，避免同步删除造成接口长时间阻塞。`EnqueueTraceIngestionAsync` 方法用于将 Trace 数据摄入任务入队，实现Trace数据的异步写入。`AcknowledgeTraceIngestionAsync` 方法用于确认消息已被成功消费，确保消息不重复处理。`DisposeAsync` 方法在服务关闭时释放队列连接资源 [API/System/Handlers/AgentInsightTransformProvider.cs]。

消费，确保消息不重复处理。`DisposeAsync` 方法在服务关闭时释放队列连接资源 [API/System/Handlers/AgentInsightTransformProvider.cs]。

`AgentInsightTransformProvider` 构造函数注入 `IBullMqService` 实例，在 YARP 反向代理的请求转换过程中，若检测到项目删除或 Trace 数据上报请求，则通过 `BullMqService` 将任务异步入队 [API/System/Handlers/AgentInsightTransformProvider.cs]。队列消费端与生产端通过 Redis 连接字符串建立连接，该Config项在 `Redis.ConnectionString` 中定义。

#### 5.1.2. ClickHouseClient 查询接口

ClickHouse 作为 Trace 时序数据的存储引擎，`ClickHouseClient` 封装对 ClickHouse 的查询操作。查询接口支持按 Trace ID、时间范围、过滤条件等维度检索Trace数据，并支持分页与排序。`ClickHouseHelper` 提供连接池管理，连接池大小Config为 10-50（`PoolSize=10;MaxPoolSize=50`），连接超时 30 秒，命令超时 60 秒（`ConnectionStrings.ClickHouseDbConnection`）。

10-50（`PoolSize=10;MaxPoolSize=50`），连接超时 30 秒，命令超时 60 秒（`ConnectionStrings.ClickHouseDbConnection`）。

查询接口的过滤条件由 `TraceFilterBuilder` 构建，支持 `FilterType`（`DateTime`、`String`、`Number`、`StringOptions`、`ArrayOptions`、`Boolean`、`Null`）与 `FilterOperator`（`GreaterThan`、`LessThan`、`EqualTo`、`Contains`、`StartsWith`、`AnyOf`、`IsNull` 等）组合 [Models/Common/Enums/FilterEnum.cs:8][Models/Common/Enums/FilterEnum.cs:20]。当查询条件不合法时，接口抛出对应错误码：`InvalidFilterType`（150012）、`InvalidFilterColumn`（150013）、`InvalidFilterOperator`（150014）、`InvalidFilterValue`（150015）[Models/Common/Enums/ExceptionCodes.cs]。

#### 5.1.3. FurionAppContextService 上下文传递

`FurionAppContextService` 实现 `IAppContextService` 接口，负责在请求处理链路中传递用户身份、Org、项目等上下文信息。该服务在 API 请求进入时从 JWT Token 或 API Key 解析当前用户与组织信息，并将其存储在异步上下文中，供后续业务逻辑访问。

负责在请求处理链路中传递用户身份、Org、项目等上下文信息。该服务在 API 请求进入时从 JWT Token 或 API Key 解析当前用户与组织信息，并将其存储在异步上下文中，供后续业务逻辑访问。

在 YARP 反向代理场景中，`AgentInsightTransformProvider` 通过 `IAppContextService` 获取当前请求的上下文信息，用于 API Key 鉴权、速率限制检查及用户Privilege验证 [API/System/Handlers/AgentInsightTransformProvider.cs]。上下文传递确保请求在跨模块调用时（如 API → Agents Service）能够保留用户身份信息，实现端到端的Privilege控制。

#### 5.1.4. 内部接口汇总

| 接口组件 | 职责 | 关键方法/类型 | 依赖 |
|---------|------|--------------|------|
| MediatR 事件通知 | 进程内事件发布与订阅 | `INotificationHandler<T>`、`WeChatNotifyReceivedNotification` | MediatR |
| BullMqService | 异步任务队列 | `EnqueueProjectDeleteAsync`、`EnqueueTraceIngestionAsync`、`AcknowledgeTraceIngestionAsync`、`DisposeAsync` | StackExchange.Redis |
| ClickHouseClient | Trace 时序数据查询 | `ClickHouseHelper`、`TraceFilterBuilder` | ClickHouse |
| FurionAppContextService | 请求上下文传递 | `IAppContextService` | Furion |

### 5.2. 外部接口

外部接口定义 AgentInsightService（保持英文） 与外部系统（第三方Payment平台、微信服务器、AI 客户端、Langfuse 集群）之间的通信契约。

#### 5.2.1. YARP 反向代理至 AgentInsight-Langfuse-Cluster

API 子项目通过 YARP 反向代理将特定路径的请求转发至 `AgentInsight-Langfuse-Cluster` 集群。反向代理Config定义了两个路由规则：

- `AgentInsight-Route-API`：匹配路径 `/api/public/{**catch-all}`，集群 ID 为 `AgentInsight-Langfuse-Cluster` [ReverseProxy.Routes.AgentInsight-Route-API.Match.Path]
- `AgentInsight-Route-Public`：匹配路径 `/public/{**catch-all}`，集群 ID 为 `AgentInsight-Langfuse-Cluster` [ReverseProxy.Routes.AgentInsight-Route-Public.Match.Path]

集群 `AgentInsight-Langfuse-Cluster` 的目标地址为 `http://localhost:3000/` [ReverseProxy.Clusters.AgentInsight-Langfuse-Cluster.Destinations.AgentInsight-Destination.Address]。

`AgentInsightTransformProvider` 实现 `ITransformProvider` 接口，在请求转发前执行自定义转换逻辑 [API/System/Handlers/AgentInsightTransformProvider.cs]。转换逻辑根据路由路径调用 `AgentInsightTransformLogic.DetermineRouteType` 判断路由类型（`RouteType.None` / `RouteType.Public` / `RouteType.PublicApi`）[API/System/Handlers/AgentInsightTransformLogic.cs:72]。对于 `RouteType.Public` 类型的路由，转换器自动添加 `/api` 路径前缀。

I/System/Handlers/AgentInsightTransformLogic.cs:72]。对于 `RouteType.Public` 类型的路由，转换器自动添加 `/api` 路径前缀。

请求转换过程中，`AgentInsightTransformProvider` 检查 `Authorization` 请求头：若以 `Basic ` 开头，则调用 `HandleBasicAuthRequest` 处理 API Key 鉴权；否则调用 `HandleJwtAuthRequest` 处理 JWT 鉴权 [API/System/Handlers/AgentInsightTransformProvider.cs]。Basic Auth 鉴权流程如下：

1. 调用 `AgentInsightTransformLogic.ParseBasicAuth` 解析公钥与私钥
2. 若公钥或私钥为空，返回 `InvalidCredentials`（100037）错误
3. 调用 `ResolveApiKeyWithCache` 校验 API Key，若无效返回 `InvalidApiKey`（100038）错误
4. 若 API Key 关联用户，检查当前组织 Privilege 是否超出速率限制，超出则返回限流响应 [API/System/Handlers/AgentInsightTransformProvider.cs]

#### 5.2.2. Payment通知 Webhook

Payment通知 Webhook 由 `NotifyController` 提供，接收微信Payment与Payment宝的异步通知回调。Controller路由前缀为 `api/payment/notify`，标记为 `[AllowAnonymous]` 且不在 Swagger 文档中展示 [API/Controllers/PaymentManagement/NotifyController.cs]。

**微信Payment通知**（`POST /api/payment/notify/wechatnotify`）：

`WeChatNotify` 方法接收微信服务器推送的Payment结果通知。处理流程如下：

1. 读取请求体内容，若为空则抛出 `FakedWeChatRequest`（620014）异常 [API/Controllers/PaymentManagement/NotifyController.cs]
2. 调用 `NotifyHandler.ExamineWeChatRequest` 验证请求签名，该验证通过 `Wechatpay-Serial` 请求头获取证书序列号，并使用 `IWeChatSignatureService.GetOrCreatePayCertificatesAsync` 获取平台证书进行验签 [API/Handlers/PaymentManagement/NotifyHandler.cs]
3. 将请求体反序列化为 `WeChatNotify` 对象
4. 调用 `NotifyHandler.ProcessWeChatNotify` 处理通知，更新订单状态
5. 返回 `WXSuccessResult()` 表示处理成功，或 `WXFailResult("FAIL")` 表示处理失败 [API/Controllers/PaymentManagement/NotifyController.cs]

**Payment宝通知**（`POST /api/payment/notify/alipaynotify`）：

`AlipayNotify` 方法接收Payment宝服务器推送的异步通知。处理流程如下：

1. 调用 `NotifyHandler.ProcessAlipayNotify` 处理通知，内部通过 `IPaymentService.GetAlipaySignDictionary` 提取签名参数，并调用 `ExamineAlipaySignature` 验证签名 [API/Common/Services/IPaymentService.cs]
2. 处理成功返回字符串 `"success"`，失败返回 `"fail"` [API/Controllers/PaymentManagement/NotifyController.cs]

#### 5.2.3. 微信消息回调

微信消息回调由 `WeChatController` 提供，路由前缀为 `api/tools/wechat`，标记为 `[AllowAnonymous]`，供微信服务器调用 [API/Controllers/ToolsManagement/WeChat/WeChatController.cs]。

**签名验证**（`GET /api/tools/wechat`）：

微信服务器在Config回调 URL 时调用该接口验证签名。`Get` 方法接收 `signature`、`timestamp`、`nonce`、`echostr` 四个参数，调用 `IWeChatService.ExamineSignature` 验证签名：将 `OfficalToken`、`timestamp`、`nonce` 按字典序排序后拼接，计算 SHA1 哈希并与 `signature` 比对 [API/Common/Services/WeChatService.cs]。验证通过返回 `echostr` 原文，失败抛出 `ExamineWeChatSignatureFailed`（620002）异常 [API/Controllers/ToolsManagement/WeChat/WeChatController.cs]。

**消息接收**（`POST /api/tools/wechat`）：

`Post` 方法接收微信推送的消息与事件，请求体为 XML 格式的 `WeChatMessage`。处理流程如下：

1. 验证签名，失败抛出 `ExamineWeChatSignatureFailed`（620002）异常
2. 将 `openid` 参数或 `FromUserName` 字段赋值给 `body.OpenId`
3. 调用 `WeChatHandler.ProcessMessage` 处理消息，返回回复消息
4. 若回复消息的 `MsgType` 为 `WeChatMessageType.None`，返回空响应；否则返回 XML 格式的回复消息 [API/Controllers/ToolsManagement/WeChat/WeChatController.cs]

#### 5.2.4. OpenAI 兼容 Chat Completions

Agents 子项目提供 OpenAI 兼容的 Chat Completions 端点（保持英文） `POST /api/agent/insight`，由 `Agents/server.py` 中的 `chat_completions` 函数处理 [Agents/server.py:346]。该端点接受 OpenAI Chat Completions 格式的请求，支持多 Agent 路由、RAG 检索增强生成与 Session 持久化。

请求经过 YARP 反向代理转发至 Agents Service，代理层完成 API Key 鉴权与速率限制检查。Agents 服务内部通过 `LangChain.Providers.OpenAI` 与 `Microsoft.SemanticKernel` 实现 LLM 调用与 Agent 编排，使用 `agentinsight-sdk` 与 API 子项目交互。

#### 5.2.5. 外部接口汇总

| 接口 | 方法 | 路径 | 鉴权 | 调用方 |
|------|------|------|------|--------|
| Langfuse 集群代理 | 任意 | `/api/public/{**catch-all}`、`/public/{**catch-all}` | BasicAuth / JWT | 外部客户端 |
| 微信Payment通知 | POST | `/api/payment/notify/wechatnotify` | 微信签名验证 | 微信Payment服务器 |
| Payment宝通知 | POST | `/api/payment/notify/alipaynotify` | Payment宝签名验证 | Payment宝服务器 |
| 微信签名验证 | GET | `/api/tools/wechat` | 微信签名验证 | 微信服务器 |
| 微信消息接收 | POST | `/api/tools/wechat` | 微信签名验证 | 微信服务器 |
| Chat Completions | POST | `/api/agent/insight` | BasicAuth / JWT | AI 客户端 |

---

## 6. 数据需求

AgentInsightService（保持英文） 是一个面向 AI Agent 应用的可Observation性与管理平台，核心定位是为企业提供 Agent 对话Trace、性能分析、成本监控、用户Privilege管理以及订阅Payment功能，并内置可扩展的多 Agent 运行时服务。本章节从数据模型、数据存储与数据流三个维度阐述系统的数据需求，明确各实体的结构定义、存储介质选型以及数据在系统各组件间的流转路径，为后续功能实现与接口设计提供数据层面的约束与依据。

### 6.1. 数据模型

系统核心实体包括 User、Organization、Project、Alert、AgentConfig、AgentSession、Order、Bulletin 等，对应 Models 层定义。实体间关系如下：

体包括 User、Organization、Project、Alert、AgentConfig、AgentSession、Order、Bulletin 等，对应 Models 层定义。实体间关系如下：

| 实体 | 关键字段 | 关联关系 | 说明 |
|------|---------|---------|------|
| User | Id, Mobile, Role | 1:N Organization（通过成员关系） | 用户可属于多个组织，角色枚举定义于 `Models/Common/Enums/UserEnum.cs` |
| Organization | Id, Name, OwnerId | 1:N Project | 组织为项目归属单位，支持成员邀请与角色分配 |
| Project | Id, Name, OrgId | N:1 Organization | 项目隶属于组织，删除时触发异步清理任务 |
| Alert | Id, Name, Field, Operator, Value | N:1 Project | Alert规则绑定项目，字段枚举见 `Models/Common/Enums/AlertEnum.cs` |
| AgentConfig | Id, UserId, DataSource, DefaultTemplateId | 1:1 User | 用户级 Agent Config，存储数据源连接信息 |
| AgentSession | Id, UserId, ProjectId, Status | N:1 User/Project | Agent Session记录，支持持久化与过期清理 |
| Order | Id, OrderNo, ProductId, State | N:1 User | 订阅订单，状态枚举见 `Models/Common/Enums/PaymentEnums.cs` |
| Bulletin | Id, Title, Content, State | — | Bulletin/协议内容，支持审批流 |

`Models/Common/Enums/PaymentEnums.cs` |
| Bulletin | Id, Title, Content, State | — | Bulletin/协议内容，支持审批流 |

**User 与 Organization 关联**：用户通过成员表与组织建立多对多关系，角色分为 OWNER / ADMIN / MEMBER / VIEWER，角色定义位于 `Models/Common/Enums/UserEnum.cs`。组织创建者自动成为 OWNER，拥有成员管理与项目配额管理Privilege。用户通过 `API.Common.Services` 中的服务获取组织Privilege信息。

**Project 与 Trace 数据关联**：Project 是 Trace 数据隔离的边界。查询 Trace 时需先解析项目归属（`API/Handlers/DataManagement/MetricsHandler.cs`），确保数据访问Privilege受控。删除 Project 时通过 `BullMqService.EnqueueProjectDeleteAsync` 异步清理关联数据。

**Alert 规则模型**：Alert 实体包含 Field（如 TotalTokens、TotalCost、ErrorCount）、Operator（如 GreaterThan、LessThan）、Value 及时间周期Config，枚举定义于 `Models/Common/Enums/AlertEnum.cs`。Alert规则支持按项目维度订阅，触发后生成 AlertRecord。

**ModelDefinition 模型**：模型管理实体定义于 `Models/DataManagement`，包含 ModelName、MatchPattern、InputPrice、OutputPrice、PricingTiers 等字段，支持项目级自定义模型与系统预定义模型（`API/Controllers/DataManagement/ModelController.cs`）。

### 6.2. 数据存储

系统采用多存储介质混合架构，按数据类型选择最优存储引擎：

| 存储介质 | 连接Config | 数据内容 | 说明 |
|---------|---------|---------|------|
| PostgreSQL (UserDb) | `ConnectionStrings.UserDbConnection` | User、Org、Project、Role、API Key | 用户域核心数据，连接池 MinPoolSize=10, MaxPoolSize=200 |
| PostgreSQL (DataDb) | `ConnectionStrings.DataDbConnection` | Agent Config、报表模板、模型定义 | 业务Config数据，连接池Config同 UserDb |
| PostgreSQL (TrackingDb) | `ConnectionStrings.TrackingDbConnection` | 审计日志、异常记录、用量Trace | 行为Trace数据，`EnableTracking=True` 时启用 |
| ClickHouse | `ConnectionStrings.ClickHouseDbConnection` | Trace、Observation、Score 时序数据 | 列式存储，PoolSize=10, MaxPoolSize=50, CommandTimeout=60 |
| Redis | `Redis.ConnectionString` | 缓存、BullMq 队列、Session 临时数据 | 连接串 `localhost:${REDIS_PORT},password=${REDIS_AUTH}` |

**PostgreSQL 多库隔离**：系统通过 `[FromKeyedServices]` 注入不同的 `ISqlSugarClient` 实例（`API/Handlers/DataManagement/MetricsHandler.cs`），实现 UserDb、DataDb、ClickHouseDb 的物理隔离。Admin 后台约定 `agentinsight_` 前缀表路由至 default 库，其他表路由至 data 库（`Admin/Agents.md`）。

aDb、ClickHouseDb 的物理隔离。Admin 后台约定 `agentinsight_` 前缀表路由至 default 库，其他表路由至 data 库（`Admin/Agents.md`）。

**ClickHouse 时序存储**：Trace、Observation、Score 数据写入 ClickHouse，查询通过 `_chdb.Queryable<Observation>()` 执行（`API/Handlers/DataManagement/MetricsHandler.cs`）。查询超时Config为 60 秒，超时抛出 `ClickHouseQueryTimeout`（errorCode=150017），查询失败抛出 `ClickHouseQueryError`（errorCode=150010）。

**Redis 缓存与队列**：Redis 承担缓存与消息队列双重职责。BullMq 队列用于 Trace 数据摄入与 Project 删除等异步任务；StackExchange.Redis 客户端负责连接管理。Session 数据在 Agents 侧通过 Redis 持久化，支持过期清理（`Agents/server.py`）。

### 6.3. 数据流

数据流涵盖 Trace 上报、查询过滤、Alert触发与异步任务处理四条主链路：

**Trace 上报链路**：Agent 侧通过 agentinsight-sdk 采集 Trace 数据 → 调用 API 公共端点（`/api/public/{**catch-all}` 经 YARP 反向代理）→ API 层经 `BullMqService.EnqueueTraceIngestionAsync` 将数据入队 → Ingestion 消费者从队列拉取数据 → 写入 ClickHouse。该链路为异步解耦设计，上报请求快速返回，数据落库由后台任务完成。

ueTraceIngestionAsync` 将数据入队 → Ingestion 消费者从队列拉取数据 → 写入 ClickHouse。该链路为异步解耦设计，上报请求快速返回，数据落库由后台任务完成。

**Trace 查询链路**：前端发起查询请求 → `MetricsController.GetTraces` 接收过滤条件（`API/Controllers/DataManagement/MetricsController.cs`）→ `MetricsHandler.GetTraces` 调用 `TraceFilterBuilder.BuildFilters` 构建 SQL 过滤条件 → 查询 ClickHouse 返回分页结果。过滤条件支持 FilterType（DateTime、String、Number 等）与 FilterOperator（GreaterThan、Contains、AnyOf 等），枚举定义于 `Models/Common/Enums/FilterEnum.cs`。

**Alert触发链路**：Alert规则Config后，定时任务按周期（Minute/Hour/Day）拉取指标数据 → `AlertService.IsConditionMet` 判断是否满足触发条件 → 满足则生成 AlertRecord 并通过 `BuildAlertMessage` 构建通知内容 → 按 `AlertNotifyBy`（System/SMS）发送通知。Alert字段与操作符枚举见 `Models/Common/Enums/AlertEnum.cs`。

**异步任务链路**：Project 删除时调用 `EnqueueProjectDeleteAsync` 入队，后台消费者执行级联清理（Trace、Observation、Score 等关联数据）；Trace 数据摄入失败时通过 `AcknowledgeTraceIngestionAsync` 确认处理状态，支持重试机制。队列类型枚举见 `Entities/Common/Enums/QueueEnum.cs`（Audit、ExceptionRecord、UsageTracking、PerformanceRecord）。

队列类型枚举见 `Entities/Common/Enums/QueueEnum.cs`（Audit、ExceptionRecord、UsageTracking、PerformanceRecord）。

**数据生命周期管理**：Session 数据支持过期清理（`Agents/server.py` 的 `cleanup_expired_sessions` 端点）；Trace 数据在 ClickHouse 中按时间分区存储，查询时通过 `from`/`to` 参数限定时间范围，避免全表扫描。

---

## 7. 约束条件

AgentInsightService（保持英文） 是一个面向 AI Agent 应用的可Observation性与管理平台，核心定位是为企业提供 Agent 对话Trace、性能分析、成本监控、用户Privilege管理以及订阅Payment功能，并内置可扩展的多 Agent 运行时服务。产品由 API（C# / Furion）与 Agents（Python / FastAPI）两大子项目构成，前者负责 RESTful Web API 与业务逻辑，后者提供 OpenAI 兼容的 Chat Completions 端点（保持英文）与多 Agent 协同能力。此外，Admin（Django + SimpleUI）子项目提供后台管理界面。本章从技术约束、业务约束与合规约束三个维度，明确平台在架构选型、资源配额与数据安全方面的硬性边界，作为系统设计、开发与运维的基线依据。

### 7.1. 技术约束

AgentInsightService（保持英文） 的技术选型由代码仓库的实际依赖与Config文件锁定，任何偏离以下约束的改动均需经过架构评审。

**后端框架与运行时**

API 子项目基于 ASP.NET Core 8 构建，采用 Furion 应用框架作为核心开发框架，ORM 使用 SqlSugar，事件通知通过 MediatR 实现，反向代理由 YARP 提供。API 子项目的Controller均继承自 `ApiControllerBase`，并通过 `[ApiDescriptionSettings]` 特性进行 Swagger 分组描述，例如 `AgentConfigController` 标注为 `SwaggerApiDescription.Agent` 分组（`API/Controllers/AgentManagement/AgentConfigController.cs:13-L16`）。

**AI 服务运行时**

Agents 子项目要求 Python 3.11 及以上版本，项目元数据中声明 `requires-python = ">=3.11"` 与 `python_version = "3.11"`（`Agents/pyproject.toml`）。AI 服务基于 FastAPI 框架，依赖 LangChain/LangGraph 生态，向量存储使用 Qdrant/ChromaDB，并通过 `agentinsight-sdk` 与 OpenAI 库实现模型调用与链路Trace。`Agents/server.py` 中注册了 OpenAI 兼容的 Chat Completions 端点（保持英文）（`Agents/server.py:346`）、Session管理端点（`Agents/server.py:614-L649`）与 Agent 列表端点（`Agents/server.py:649`）。

**数据存储与中间件**

| 组件 | 版本要求 | 用途 | Config来源 |
|------|---------|------|---------|
| Redis | 5.0+ | 缓存、BullMq 队列 | `Redis.ConnectionString` |
| ClickHouse | 22+ | Trace 时序数据存储 | `ConnectionStrings.ClickHouseDbConnection`（PoolSize=10, MaxPoolSize=50） |
| PostgreSQL | 14+ | User、Config、订单等关系数据 | `ConnectionStrings.UserDbConnection` / `DataDbConnection` / `TrackingDbConnection`（MinPoolSize=10, MaxPoolSize=200） |

ClickHouse 连接串Config了连接池大小 10-50、连接超时 30 秒、命令超时 60 秒。PostgreSQL 连接串Config了 60 秒超时、连接池最小 10 与最大 200、连接生命周期 300 秒。Redis 同时承担缓存与 BullMq 队列职责，队列类型包括 `Audit`、`ExceptionRecord`、`UsageTracking`、`PerformanceRecord`（`Entities/Common/Enums/QueueEnum.cs:3`）。

**Config与本地化**

Config扫描目录限定为 `Configurations` 与 `Resources`。本地化支持 `zh-CN`、`zh-TW`、`zh-HK`、`en` 四种文化，默认文化为 `zh-CN`，语言文件前缀为 `Text`。日志Config中文件日志最小级别为 Information，滚动文件大小上限 10485760 字节，最多保留 30 个滚动文件。

### 7.2. 业务约束

业务约束围绕订阅Privilege与资源配额展开，确保多租户场景下资源使用可控、可预期。

**Org、项目与成员配额**

单用户可创建的组织数、项目数与成员数受订阅产品等级约束。产品定义中明确包含 `projectlimit`（项目数上限）、`headcountlimit`（成员数上限）、`orglimit`（组织数上限）与 `agentlimit`（Agent 数上限）字段（`API/Controllers/ProductManagement/ProductController.cs:26-L34`）。当用户超出配额时，系统返回对应的错误码：

| 错误码 | 常量名 | 触发场景 |
|--------|--------|---------|
| 130012 | `ExceedOrgLimit` | 组织数超出订阅上限 |
| 130011 | `ExceedProjectLimit` | 项目数超出订阅上限 |
| 130010 | `ExceedHeadCountLimit` | 成员数超出订阅上限 |

上述错误码定义于 `Models/Common/Enums/ExceptionCodes.cs:6`。配额校验在组织创建、项目创建与成员邀请等操作的服务端逻辑中强制执行，防止客户端绕过限制。产品类型分为 `Monthly`（按月订阅）与 `Permanent`（永久订阅），产品时长支持自定义数量与折扣（`API/Controllers/ProductManagement/ProductController.cs:38-L44`）。

**Agent 使用配额**

Agent 的调用频次与总量受订阅Privilege控制。当 Agent 使用量超出订阅允许的配额时，系统返回 `AgentLimitExceeded`（错误码 150007，`Models/Common/Enums/ExceptionCodes.cs:6`）。API 子项目提供月度 Agent 配额的扣减与校验端点：`GET /api/user/privilege/agent/deduct` 对应 `UserController.DeductMonthlyAgentRate`，`GET /api/user/privilege/agent/validate` 对应 `UserController.ValidateMonthlyAgentRate`（`API/Controllers/UserManagement/UserController.cs:242-L258`）。配额扣减失败时返回 `UpdateAgentRateFailed`（错误码 150020）。

**角色Privilege边界**

用户角色分为 `OWNER`、`ADMIN`、`MEMBER`、`VIEWER`。角色分配遵循以下规则：
- `OWNER` 不可修改自身角色（`OwnerCannotModifySelfRole`，错误码 100039）
- 不可授予高于操作者自身等级的角色（`CannotGrantHigherRole`，错误码 100023）
- 组织内已存在 `OWNER` 时不可重复设置（`OrgAlreadyHasOwner`，错误码 130013）

**Session与Config归属**

Agent Session（`AgentSession`）与 Agent Config（`AgentConfig`）均以用户维度隔离。Session查询、更新与删除操作仅允许操作当前用户名下的数据，例如 `AgentSessionHandler.GetSessions` 中强制 `s.UserId == User.Id` 条件，删除操作同样限定 `s.UserId == User.Id`。Session不存在时返回 `AgentSessionNotFound`（错误码 150021），Config不存在时返回 `AgentConfigNotFound`（错误码 150022）。

### 7.3. 合规约束

合规约束覆盖数据传输加密、身份认证与数据本地化存储三个方面，PIPL及相关安全标准。

**数据传输加密**

敏感数据在传输与存储环节使用 AES 加密，加密密钥通过环境变量注入。加密与解密失败时分别返回 `EncryptionFailed`（错误码 990001）与 `DecryptionFailed`（错误码 990002）。密码哈希失败返回 `PasswordHashFailed`（错误码 990003）。上述错误码定义于 `Models/Common/Enums/ExceptionCodes.cs:6`。

**API Key 强制认证**

平台未在Config文件中显式体现双向 TLS Config项，但强制要求 API Key 认证。API Key 的创建、查询与删除端点分别对应 `UserController.CreateApiKey`、`UserController.Get`（apikey 重载）与 `UserController.DeleteApiKey`（`API/Controllers/UserManagement/UserController.cs:209-L272`）。API Key 不存在时返回 `ApiKeyNotFound`（错误码 100031），创建失败返回 `CreateApiKeyFailed`（错误码 100032），删除失败返回 `DeleteApiKeyFailed`（错误码 100033），无效 Key 返回 `InvalidApiKey`（错误码 100038）。API Key 用于程序化访问公共Trace API，适用于 CI/CD 集成或数据上报场景。

**数据本地化存储**

PIPL要求，用户数据本地化存储。所有数据库连接均指向内部基础设施：PostgreSQL 承载用户、Config与订单数据，ClickHouse 承载 Trace 时序数据，Redis 承载缓存与队列。三个数据库连接串均使用内部主机名，未Config任何跨域数据同步或外部存储目标，确保个人信息与业务数据不出境。

**审计与Trace**

平台内置审计日志机制，审计动作枚举包括 `Create`、`Update`、`Delete`、`Login`、`Logout`、`Reset`、`Bind`、`UnBind`、`Place`、`Query`、`Notify`（`Models/Common/Enums/AuditEnum.cs:3`），审计资源类型包括 `User`、`Organization`、`Project`、`Alert`、`ApiKey`、`Invitation`、`Order`、`WeChat`、`OrgPrivilege`（`Models/Common/Enums/AuditEnum.cs:18`）。审计队列类型为 `Audit`（`Entities/Common/Enums/QueueEnum.cs:3`），通过 BullMq 异步处理，确保关键操作可追溯。

---

## 8. 需求Trace矩阵

AgentInsightService（保持英文） 是一个面向 AI Agent 应用的可Observation性与管理平台，核心定位是为企业提供 Agent 对话Trace、性能分析、成本监控、用户Privilege管理以及订阅Payment功能，并内置可扩展的多 Agent 运行时服务。本章节通过需求Trace矩阵，FRNFR映射到具体的代码实现位置与测试用例，确保每一项需求均可追溯至可验证的交付物。矩阵覆盖 API（C# / Furion）与 Agents（Python / FastAPI）两大子项目，为需求评审、变更影响分析与验收提供依据。

### 8.1. FR Trace

FR TraceFR关联至具体 Controller 或服务端点的处理方法，并标注主实现文件与测试用例参考。矩阵中的“来源”列标识需求对应的 HTTP 端点或分析结论，“主实现文件”列给出精确到方法级别的代码位置，“测试用例参考”列指向 `UnitTest` 目录下的对应测试类。

| 需求 ID | 需求描述 | 来源（端点/分析） | 主实现文件 | 测试用例参考 |
|---------|---------|-------------------|------------|--------------|
| FR-001 | 获取当前用户的 Agent Config | GET /api/agent/config | `API/Controllers/AgentManagement/AgentConfigController.cs:28` → `AgentConfigController.Get` | `UnitTest/` 下 AgentConfig 相关测试 |
| FR-002 | 删除当前用户的 Agent Config | GET /api/agent/config/delete | `API/Controllers/AgentManagement/AgentConfigController.cs:40` → `AgentConfigController.Delete` | `UnitTest/` 下 AgentConfig 相关测试 |
| FR-003 | 创建或更新 Agent Config | POST /api/agent/config | `API/Controllers/AgentManagement/AgentConfigController.cs:54` → `AgentConfigController.Post` | `UnitTest/` 下 AgentConfig 相关测试 |
| FR-004 | 获取 Agent 报表模板列表或单个模板详情 | GET /api/agent/report | `API/Controllers/AgentManagement/AgentReportController.cs:35` → `AgentReportController.GetTemplates` | `UnitTest/` 下 AgentReport 相关测试 |

entReportController.cs:35` → `AgentReportController.GetTemplates` | `UnitTest/` 下 AgentReport 相关测试 |
| FR-005 | 删除 Agent 报表模板 | GET /api/agent/report/delete | `API/Controllers/AgentManagement/AgentReportController.cs:48` → `AgentReportController.DeleteTemplates` | `UnitTest/` 下 AgentReport 相关测试 |
| FR-006 | 创建或更新 Agent 报表模板 | POST /api/agent/report | `API/Controllers/AgentManagement/AgentReportController.cs:62` → `AgentReportController.CreateOrUpdateTemplate` | `UnitTest/` 下 AgentReport 相关测试 |
| FR-007 | 获取 Agent Session列表或单个Session详情 | GET /api/agent/session | `API/Controllers/AgentManagement/AgentSessionController.cs:33` → `AgentSessionController.Get` | `UnitTest/` 下 AgentSession 相关测试 |
| FR-008 | 删除 Agent Session | GET /api/agent/session/delete | `API/Controllers/AgentManagement/AgentSessionController.cs:46` → `AgentSessionController.Delete` | `UnitTest/` 下 AgentSession 相关测试 |

/AgentSessionController.cs:46` → `AgentSessionController.Delete` | `UnitTest/` 下 AgentSession 相关测试 |
| FR-009 | 创建或更新 Agent Session | POST /api/agent/session | `API/Controllers/AgentManagement/AgentSessionController.cs:60` → `AgentSessionController.Post` | `UnitTest/` 下 AgentSession 相关测试 |
| FR-010 | 根据 Trace ID 获取 Observations 列表 | GET /api/data/metrics/observations | `API/Controllers/DataManagement/MetricsController.cs:34` → `MetricsController.GetObservations` | `UnitTest/` 下 MetricsControllerFurionIntegrationTests |
| FR-011 | 根据 Trace ID 获取 Scores 列表 | GET /api/data/metrics/scores | `API/Controllers/DataManagement/MetricsController.cs:50` → `MetricsController.GetScores` | `UnitTest/` 下 MetricsControllerFurionIntegrationTests |
| FR-012 | 根据 Trace ID 批量获取指标详情 | GET /api/data/metrics/traces | `API/Controllers/DataManagement/MetricsController.cs:64` → `MetricsController.GetTraces` | `UnitTest/` 下 MetricsControllerFurionIntegrationTests |

ler.cs:64` → `MetricsController.GetTraces` | `UnitTest/` 下 MetricsControllerFurionIntegrationTests |
| FR-013 | 分页查询 Trace 列表，支持自定义条件过滤 | POST /api/data/metrics/traces | `API/Controllers/DataManagement/MetricsController.cs:125` → `MetricsController.GetTraces` | `UnitTest/` 下 MetricsControllerFurionIntegrationTests |
| FR-014 | 获取模型列表 | GET /api/data/model | `API/Controllers/DataManagement/ModelController.cs:34` → `ModelController.Get` | `UnitTest/` 下 ModelController 相关测试 |
| FR-015 | 获取产品列表 | GET /api/product | `API/Controllers/ProductManagement/ProductController.cs:26` → `ProductController.Get` | `UnitTest/` 下 ProductController 相关测试 |
| FR-016 | 获取产品时长列表 | GET /api/product/duration | `API/Controllers/ProductManagement/ProductController.cs:38` → `ProductController.GetDuration` | `UnitTest/` 下 ProductController 相关测试 |
| FR-017 | 获取用户信息 | GET /api/user | `API/Controllers/UserManagement/UserController.cs:29` → `UserController.Get` | `UnitTest/` 下 UserControllerCoverageEnhancementTests |

serController.cs:29` → `UserController.Get` | `UnitTest/` 下 UserControllerCoverageEnhancementTests |
| FR-018 | 创建用户 | POST /api/user | `API/Controllers/UserManagement/UserController.cs:43` → `UserController.Create` | `UnitTest/` 下 UserControllerCoverageEnhancementTests |
| FR-019 | 用户登录 | POST /api/user/login | `API/Controllers/UserManagement/UserController.cs:73` → `UserController.Login` | `UnitTest/` 下 UserControllerCoverageEnhancementTests |
| FR-020 | 用户登出 | POST /api/user/logout | `API/Controllers/UserManagement/UserController.cs:88` → `UserController.Logout` | `UnitTest/` 下 UserControllerCoverageEnhancementTests |
| FR-021 | 重置密码 | POST /api/user/resetpassword | `API/Controllers/UserManagement/UserController.cs:102` → `UserController.ResetPassword` | `UnitTest/` 下 UserControllerCoverageEnhancementTests |

er.cs:102` → `UserController.ResetPassword` | `UnitTest/` 下 UserControllerCoverageEnhancementTests |
| FR-022 | 创建 API Key | POST /api/user/apikey | `API/Controllers/UserManagement/UserController.cs:209` → `UserController.CreateApiKey` | `UnitTest/` 下 UserControllerCoverageEnhancementTests |
| FR-023 | 获取 API Key 列表 | GET /api/user/apikey | `API/Controllers/UserManagement/UserController.cs:225` → `UserController.Get` | `UnitTest/` 下 UserControllerCoverageEnhancementTests |
| FR-024 | 删除 API Key | POST /api/user/apikey/delete | `API/Controllers/UserManagement/UserController.cs:272` → `UserController.DeleteApiKey` | `UnitTest/` 下 UserControllerCoverageEnhancementTests |
| FR-025 | 创建组织 | POST /api/user/organization | `API/Controllers/UserManagement/OrganizationController.cs:28` → `OrganizationController.Post` | `UnitTest/` 下 OrganizationControllerComprehensiveTests |

er.cs:28` → `OrganizationController.Post` | `UnitTest/` 下 OrganizationControllerComprehensiveTests |
| FR-026 | 获取组织信息 | GET /api/user/organization | `API/Controllers/UserManagement/OrganizationController.cs:42` → `OrganizationController.Get` | `UnitTest/` 下 OrganizationControllerComprehensiveTests |
| FR-027 | 创建项目 | POST /api/user/project | `API/Controllers/UserManagement/ProjectController.cs:31` → `ProjectController.Create` | `UnitTest/` 下 ProjectController 相关测试 |
| FR-028 | 获取项目列表 | GET /api/user/project | `API/Controllers/UserManagement/ProjectController.cs:46` → `ProjectController.Get` | `UnitTest/` 下 ProjectController 相关测试 |
| FR-029 | 获取Captcha | GET /api/captcha | `API/Controllers/UserManagement/CaptchaController.cs:29` → `CaptchaController.Get` | `UnitTest/` 下 CaptchaControllerFurionIntegrationTests |

ontroller.cs:29` → `CaptchaController.Get` | `UnitTest/` 下 CaptchaControllerFurionIntegrationTests |
| FR-030 | 获取短信Captcha | GET /api/captcha/sms | `API/Controllers/UserManagement/CaptchaController.cs:43` → `CaptchaController.GetSMSCaptcha` | `UnitTest/` 下 CaptchaControllerFurionIntegrationTests |
| FR-031 | 获取 Alert Config | GET /api/alert/config | `API/Controllers/UserManagement/AlertController.cs:30` → `AlertController.GetConfig` | `UnitTest/` 下 AlertMetricsHandlerComprehensiveTests |
| FR-032 | 获取 Alert 列表 | GET /api/alert | `API/Controllers/UserManagement/AlertController.cs:47` → `AlertController.Get` | `UnitTest/` 下 AlertMetricsHandlerComprehensiveTests |
| FR-033 | 创建 Alert | POST /api/alert | `API/Controllers/UserManagement/AlertController.cs:61` → `AlertController.Create` | `UnitTest/` 下 AlertMetricsHandlerComprehensiveTests |

Controller.cs:61` → `AlertController.Create` | `UnitTest/` 下 AlertMetricsHandlerComprehensiveTests |
| FR-034 | 更新 Alert | POST /api/alert/update | `API/Controllers/UserManagement/AlertController.cs:75` → `AlertController.Update` | `UnitTest/` 下 AlertMetricsHandlerComprehensiveTests |
| FR-035 | 删除 Alert | POST /api/alert/delete | `API/Controllers/UserManagement/AlertController.cs:90` → `AlertController.Delete` | `UnitTest/` 下 AlertMetricsHandlerComprehensiveTests |
| FR-036 | 标记 Alert 记录为已读 | POST /api/alert/record/read | `API/Controllers/UserManagement/AlertController.cs:108` → `AlertController.ReadRecords` | `UnitTest/` 下 AlertMetricsHandlerComprehensiveTests |
| FR-037 | 获取 Alert 记录 | GET /api/alert/record | `API/Controllers/UserManagement/AlertController.cs:128` → `AlertController.GetRecords` | `UnitTest/` 下 AlertMetricsHandlerComprehensiveTests |

oller.cs:128` → `AlertController.GetRecords` | `UnitTest/` 下 AlertMetricsHandlerComprehensiveTests |
| FR-038 | 处理微信Payment通知 | POST /api/payment/notify/wechatnotify | `API/Controllers/PaymentManagement/NotifyController.cs:29` → `NotifyController.WeChatNotify` | `UnitTest/` 下 NotifyControllerFurionIntegrationTests |
| FR-039 | 处理Payment宝Payment通知 | POST /api/payment/notify/alipaynotify | `API/Controllers/PaymentManagement/NotifyController.cs:57` → `NotifyController.AlipayNotify` | `UnitTest/` 下 NotifyControllerFurionIntegrationTests |
| FR-040 | 获取订单列表 | GET /api/payment/order | `API/Controllers/PaymentManagement/OrderController.cs:34` → `OrderController.Get` | `UnitTest/` 下 PaymentServiceCoverageEnhancementTests |
| FR-041 | 创建订单 | POST /api/payment/order | `API/Controllers/PaymentManagement/OrderController.cs:48` → `OrderController.Place` | `UnitTest/` 下 PaymentServiceCoverageEnhancementTests |

Controller.cs:48` → `OrderController.Place` | `UnitTest/` 下 PaymentServiceCoverageEnhancementTests |
| FR-042 | 获取订单转换率 | GET /api/payment/order/conversion | `API/Controllers/PaymentManagement/OrderController.cs:79` → `OrderController.GetConversion` | `UnitTest/` 下 PaymentServiceCoverageEnhancementTests |
| FR-043 | 发布Bulletin | POST /api/tools/bulletin | `API/Controllers/ToolsManagement/BulletinController.cs:32` → `BulletinController.Post` | `UnitTest/` 下 BulletinController 相关测试 |
| FR-044 | 获取Bulletin列表 | GET /api/tools/bulletin/bulletins | `API/Controllers/ToolsManagement/BulletinController.cs:64` → `BulletinController.GetBulletins` | `UnitTest/` 下 BulletinController 相关测试 |
| FR-045 | 健康检查 | GET /api/tools/health | `API/Controllers/ToolsManagement/HealthController.cs:20` → `HealthController.Get` | `UnitTest/` 下 HealthController 相关测试 |

sManagement/HealthController.cs:20` → `HealthController.Get` | `UnitTest/` 下 HealthController 相关测试 |
| FR-046 | 处理微信消息 | POST /api/tools/wechat | `API/Controllers/ToolsManagement/WeChat/WeChatController.cs:68` → `WeChatController.Post` | `UnitTest/` 下 WeChatSignatureHelperFurionIntegrationTests |
| FR-047 | 提供 OpenAI 兼容的 Chat Completions 端点（保持英文） | POST /api/agent/insight | `Agents/server.py:346` → `chat_completions` | `UnitTest/` 下 Agents 相关测试 |
| FR-048 | 获取 Session 列表 | GET /api/sessions | `Agents/server.py:614` → `list_sessions` | `UnitTest/` 下 Agents 相关测试 |
| FR-049 | 获取单个 Session 详情 | GET /api/sessions/{session_id} | `Agents/server.py:622` → `get_session` | `UnitTest/` 下 Agents 相关测试 |
| FR-050 | 删除 Session | DELETE /api/sessions/{session_id} | `Agents/server.py:633` → `delete_session` | `UnitTest/` 下 Agents 相关测试 |
| FR-051 | 清理过期 Session | POST /api/sessions/cleanup | `Agents/server.py:641` → `cleanup_expired_sessions` | `UnitTest/` 下 Agents 相关测试 |

sessions/cleanup | `Agents/server.py:641` → `cleanup_expired_sessions` | `UnitTest/` 下 Agents 相关测试 |
| FR-052 | 获取 Agent 列表 | GET /api/agents | `Agents/server.py:649` → `list_agents` | `UnitTest/` 下 Agents 相关测试 |

#### 8.1.1. 交叉引用表

以下交叉引用表用于快速定位同一功能在不同层次（Controller → Handler → 测试）的实现映射，便于追溯需求实现链路：

| 需求 ID | Controller 方法 | Handler 方法 | 测试类参考 |
|---------|----------------|--------------|------------|
| FR-001 | `AgentConfigController.Get` | `AgentConfigHandler.GetConfig` | `UnitTest/` 下 AgentConfig 相关测试 |
| FR-003 | `AgentConfigController.Post` | `AgentConfigHandler.CreateOrUpdateConfig` | `UnitTest/` 下 AgentConfig 相关测试 |
| FR-004 | `AgentReportController.GetTemplates` | `AgentReportHandler.GetTemplates` | `UnitTest/` 下 AgentReport 相关测试 |
| FR-006 | `AgentReportController.CreateOrUpdateTemplate` | `AgentReportHandler.CreateOrUpdateTemplate` | `UnitTest/` 下 AgentReport 相关测试 |
| FR-007 | `AgentSessionController.Get` | `AgentSessionHandler.GetSessions` | `UnitTest/` 下 AgentSession 相关测试 |
| FR-009 | `AgentSessionController.Post` | `AgentSessionHandler.CreateOrUpdateSession` | `UnitTest/` 下 AgentSession 相关测试 |
| FR-010 | `MetricsController.GetObservations` | `MetricsHandler.GetObservationsAsync` | `UnitTest/` 下 MetricsControllerFurionIntegrationTests |

s` | `MetricsHandler.GetObservationsAsync` | `UnitTest/` 下 MetricsControllerFurionIntegrationTests |
| FR-011 | `MetricsController.GetScores` | `MetricsHandler.GetScoresAsync` | `UnitTest/` 下 MetricsControllerFurionIntegrationTests |
| FR-012 | `MetricsController.GetTraces` | `MetricsHandler.GetTracesMetrics` | `UnitTest/` 下 MetricsControllerFurionIntegrationTests |
| FR-014 | `ModelController.Get` | `ModelHandler.GetModels` | `UnitTest/` 下 ModelController 相关测试 |
| FR-015 | `ProductController.Get` | `ProductHandler.GetProducts` | `UnitTest/` 下 ProductController 相关测试 |
| FR-016 | `ProductController.GetDuration` | `ProductHandler.GetProductDurations` | `UnitTest/` 下 ProductController 相关测试 |

### 8.2. NFR Trace

NFR TraceNFR关联至相关模块、架构决策或Config项。矩阵中的“关联模块/架构决策”列指明该 NFR 在代码仓库中的落地位置，“验证方式”列说明如何通过Config、测试或架构设计来验证该需求的满足情况。

| 需求 ID | 需求描述 | 关联模块/架构决策 | 验证方式 |
|---------|---------|-------------------|----------|
| NFR-S-001 | 用户认证与授权安全 | `API/Handlers/UserManagement/UserHandler.cs:216` 中 API Key 认证逻辑；`ExceptionCodes.UnAuthToken = 100000`、`ExceptionCodes.InvalidApiKey = 100038`、`ExceptionCodes.InvalidCredentials = 100037` 错误码 | 验证 JWT 过期时间、签名算法与 API Key 校验逻辑；`UnitTest/` 下 UserControllerCoverageEnhancementTests 覆盖登录与 API Key 场景 |
| NFR-S-002 | Payment签名与回调安全 | `API/Controllers/PaymentManagement/NotifyController.cs:29`（`WeChatNotify`）与 `:57`（`AlipayNotify`）；`ExceptionCodes.InvalidWeChatNotify = 810010`、`ExceptionCodes.AlipaySignatureError = 810007`、`ExceptionCodes.FakedWeChatRequest = 620014` 错误码 | 验证微信/Payment宝回调签名校验逻辑；`UnitTest/` 下 NotifyControllerFurionIntegrationTests 与 WeChatSignatureHelperFurionIntegrationTests 覆盖签名验证场景 |

/` 下 NotifyControllerFurionIntegrationTests 与 WeChatSignatureHelperFurionIntegrationTests 覆盖签名验证场景 |
| NFR-S-003 | 敏感数据加密存储 | `ExceptionCodes.EncryptionFailed = 990001`、`ExceptionCodes.DecryptionFailed = 990002`、`ExceptionCodes.PasswordHashFailed = 990003` 错误码 | 验证加密/解密失败时返回对应错误码；`UnitTest/` 下相关测试覆盖加密异常场景 |
| NFR-P-001 | 高并发数据写入与查询性能 | ClickHouse 查询相关错误码：`ExceptionCodes.ClickHouseQueryError = 150010`、`ExceptionCodes.ClickHouseQueryTimeout = 150017`、`ExceptionCodes.TooManyTraceIds = 150011`；`API.Common.Helpers.ClickHouseHelper` 与 `TraceFilterBuilder` | 验证 ClickHouse 查询超时与错误处理逻辑；`UnitTest/` 下 MetricsControllerFurionIntegrationTests 与 TraceFilterBuilderCoverageEnhancementTests 覆盖 Trace 查询场景 |

MetricsControllerFurionIntegrationTests 与 TraceFilterBuilderCoverageEnhancementTests 覆盖 Trace 查询场景 |
| NFR-P-002 | 异步任务处理性能 | Redis BullMq与 `QueueType` 枚举（`QueueType.Audit = 0`，`QueueType.ExceptionRecord = 1`，`QueueType.UsageTracking = 2`，`QueueType.PerformanceRecord = 3`）；`API.Common.Services.BullMqService` 中的 `EnqueueTraceIngestionAsync`、`AcknowledgeTraceIngestionAsync`、`EnqueueProjectDeleteAsync` | 验证异步队列的入队与消费逻辑；`UnitTest/` 下 BullMqDeleteProjectComprehensiveTests 覆盖队列场景 |
| NFR-A-001 | 系统高可用与健康检查 | `API/Controllers/ToolsManagement/HealthController.cs:20` → `HealthController.Get` | 验证健康检查端点返回状态；`UnitTest/` 下 HealthController 相关测试 |
| NFR-A-002 | 反向代理与路由可用性 | YARP 反向代理Config（`RouteType.Public = 1`，`RouteType.PublicApi = 2`）；`API/System/Handlers/AgentInsightTransformLogic.cs:72` 中的路由转换逻辑 | 验证公共 API 路由转发规则；`UnitTest/` 下 AgentInsightTransformProviderCoverageTests 与 AgentInsightTransformProviderBehavioralTests 覆盖路由匹配场景 |

AgentInsightTransformProviderCoverageTests 与 AgentInsightTransformProviderBehavioralTests 覆盖路由匹配场景 |
| NFR-O-001 | 操作审计与Trace | `QueueType.Audit = 0` 与 `AuditAction` 枚举（`AuditAction.Create`，`AuditAction.Update`，`AuditAction.Delete`，`AuditAction.Login`，`AuditAction.Logout`，`AuditAction.Reset`，`AuditAction.Bind`，`AuditAction.UnBind`，`AuditAction.Place`，`AuditAction.Query`，`AuditAction.Notify`）；`AuditResourceType` 枚举（`AuditResourceType.User`，`AuditResourceType.Organization`，`AuditResourceType.Project`，`AuditResourceType.Alert`，`AuditResourceType.ApiKey`，`AuditResourceType.Invitation`，`AuditResourceType.Order`，`AuditResourceType.WeChat`，`AuditResourceType.OrgPrivilege`） | 验证审计日志的入队与记录逻辑；`UnitTest/` 下 AuditExceptionTrackingComprehensiveTests 与 RequestAuditFilterFurionIntegrationTests 覆盖审计场景 |
| NFR-O-002 | 异常记录与Trace | `QueueType.ExceptionRecord = 1`；`ExceptionCodes.DefaultException = 999999` | 验证异常记录队列的消费逻辑；`UnitTest/` 下 AuditExceptionTrackingComprehensiveTests 覆盖异常场景 |

tException = 999999` | 验证异常记录队列的消费逻辑；`UnitTest/` 下 AuditExceptionTrackingComprehensiveTests 覆盖异常场景 |
| NFR-L-001 | 多语言本地化支持 | `My.Extensions.Localization.Json` 本地化框架；`TraditionalChineseExtensionFurionIntegrationTests`、`TraditionalChineseExtensionExtendedCoverageTests`、`TraditionalChineseExtensionFunctionalTests`、`TraditionalChineseExtensionCoverageTests`、`TraditionalChineseExtensionExtendedTests`、`TraditionalChineseExtensionDirectTests` 测试类 | 验证本地化资源文件加载与语言切换；`UnitTest/` 下 TraditionalChineseExtension 相关测试覆盖本地化场景 |
| NFR-C-001 | Config集中管理与占位符解析 | `ConfigurationPlaceholderResolverDirectTests` 测试类 | 验证Config占位符的解析逻辑；`UnitTest/` 下 ConfigurationPlaceholderResolverDirectTests 覆盖Config解析场景 |
| NFR-C-002 | 日志记录与滚动策略 | `concurrent_log_handler-0.9.25-py3-none-any` 日志处理依赖 | 验证日志文件滚动与级别过滤Config；`UnitTest/` 下 Logging 相关测试覆盖日志场景 |

current_log_handler-0.9.25-py3-none-any` 日志处理依赖 | 验证日志文件滚动与级别过滤Config；`UnitTest/` 下 Logging 相关测试覆盖日志场景 |
| NFR-M-001 | 可Observation性指标采集 | `QueueType.UsageTracking = 2` 与 `QueueType.PerformanceRecord = 3`；`MetricsController` 中的 Trace 与 Observation 数据采集逻辑 | 验证 Trace 与 Observation 数据采集开关；`UnitTest/` 下 MetricsControllerFurionIntegrationTests 与 MetricsHandlerCoverageEnhancementTests 覆盖指标查询场景 |

| NFR-M-002 | 指标查询过滤能力 | `FilterType` 枚举（`FilterType.DateTime = 1`，`FilterType.String = 2`，`FilterType.Number = 3`，`FilterType.StringOptions = 4`，`FilterType.ArrayOptions = 5`，`FilterType.Boolean = 6`，`FilterType.Null = 7`）；`FilterOperator` 枚举（`FilterOperator.GreaterThan = 1`，`FilterOperator.LessThan = 2`，`FilterOperator.GreaterThanOrEqualTo = 3`，`FilterOperator.LessThanOrEqualTo = 4`，`FilterOperator.EqualTo = 5`，`FilterOperator.Contains = 6`，`FilterOperator.DoesNotContain = 7`，`FilterOperator.StartsWith = 8`，`FilterOperator.EndsWith = 9`，`FilterOperator.AnyOf = 10`，`FilterOperator.NoneOf = 11`，`FilterOperator.AllOf = 12`，`FilterOperator.NotEqualTo = 13`，`FilterOperator.IsNull = 14`，`FilterOperator.IsNotNull = 15`）；`FilterColumn` 枚举（`FilterColumn.Id = 1`，`FilterColumn.Name = 2`，`FilterColumn.Timestamp = 3`，`FilterColumn.UserId = 4`，`FilterColumn.SessionId = 5`，`FilterColumn.Environment = 6`，`FilterColumn.Version = 7`，`FilterColumn.Release = 8`，`FilterColumn.Tags =

9`，`FilterColumn.Bookmarked = 10`，`FilterColumn.Latency = 11`，`FilterColumn.InputTokens = 12`，`FilterColumn.OutputTokens = 13`，`FilterColumn.TotalTokens = 14`，`FilterColumn.Tokens = 15`，`FilterColumn.InputCost = 16`，`FilterColumn.OutputCost = 17`，`FilterColumn.TotalCost = 18`，`FilterColumn.Level = 19`，`FilterColumn.WarningCount = 20`，`FilterColumn.ErrorCount = 21`，`FilterColumn.DefaultCount = 22`，`FilterColumn.DebugCount = 23`，`FilterColumn.ModelNames = 24`，`FilterColumn.ScoresAvg = 25`）；`ExceptionCodes.InvalidFilterType = 150012`、`ExceptionCodes.InvalidFilterColumn = 150013`、`ExceptionCodes.InvalidFilterOperator = 150014`、`ExceptionCodes.InvalidFilterValue = 150015`、`ExceptionCodes.InvalidOrderBy = 150016` | 验证 Trace 查询的过滤条件组合与非法过滤参数错误处理；`UnitTest/` 下 MetricsControllerFurionIntegrationTests 与 TraceFilterBuilderCoverageEnhancementTests 覆盖过滤场景 |

| NFR-T-001 | 数据存储可靠性 | PostgreSQL 连接Config（`ConnectionStrings.UserDbConnection`，`ConnectionStrings.TrackingDbConnection`，`ConnectionStrings.DataDbConnection`）；`Npgsql` 数据库驱动；`psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64` Python 端 PostgreSQL 驱动 | 验证数据库连接超时与池化Config；`UnitTest/` 下相关测试覆盖数据库连接场景 |

---

## 9. 错误码参考

### 9.1. 错误码参考

AgentInsightService（保持英文） 是一个面向 AI Agent 应用的可Observation性与管理平台，核心定位是为企业提供 Agent 对话Trace、性能分析、成本监控、用户Privilege管理以及订阅Payment功能，并内置可扩展的多 Agent 运行时服务。本文档汇总了 AgentInsightService（保持英文） 全系统错误码定义，所有错误码常量集中定义于 `Models/Common/Enums/ExceptionCodes.cs`，由 `API/System/Handlers/ExceptionMiddleware.cs` 统一捕获并序列化为 `ApiResponse<object>` 返回给客户端。错误码按业务域划分为多个区间，每个区间对应一组功能模块，便于开发与测试人员快速定位问题。

#### 9.1.1. 错误码使用说明

- **抛出方式**：业务代码中通过 `throw new AppFriendlyException((int)ErrorCode.XXX, "错误消息")` 抛出，其中 `ErrorCode` 为 `ExceptionCodes.cs` 中定义的枚举。
- **捕获与响应**：`ExceptionMiddleware` 捕获 `AppFriendlyException`，将错误码与错误消息写入响应体，HTTP 状态码通常为 200（业务错误）或 500（系统错误）。
- **排查建议**：开发与测试人员可根据错误码区间定位模块，结合响应中的 `ErrorMessage` 与日志进一步分析。

### 9.2. 通用错误码 (10xxxx)

通用错误码覆盖用户认证、授权、API Key 管理等基础通用场景，数值范围为 100000-100041。

| 常量名 | 数值 | 触发场景 |
|--------|------|----------|
| UnAuthToken | 100000 | 请求未携带有效 Token 或 Token 已过期 |
| EmptyUserId | 100001 | User ID 为空 |
| ExistedMobile | 100003 | 注册时手机号已存在 |
| CreateUserFailed | 100004 | 创建用户失败 |
| InvalidUser | 100005 | 用户不存在或已被禁用 |
| EmptyMobile | 100009 | 手机号为空 |
| UnauthorizedOperator | 100010 | 当前操作者无Privilege执行该操作 |
| UserNameTooLong | 100019 | 用户名超过长度限制 |
| EmptyInviteMobile | 100021 | 邀请成员时手机号为空 |
| InvalidInviteMobile | 100022 | 邀请的手机号格式非法 |
| CannotGrantHigherRole | 100023 | 不能授予高于自身等级的角色 |
| UserAlreadyOrgMember | 100024 | 用户已是组织成员 |
| InviteAlreadyExists | 100025 | 邀请记录已存在 |
| CreateInviteFailed | 100026 | 创建邀请失败 |
| InviteNotFound | 100027 | 邀请记录不存在 |
| DeleteInviteFailed | 100028 | 删除邀请失败 |
| ApiKeyNotFound | 100031 | API Key 不存在 |
| CreateApiKeyFailed | 100032 | 创建 API Key 失败 |
| DeleteApiKeyFailed | 100033 | 删除 API Key 失败 |
| MissingProjectOrOrgId | 100035 | 缺少项目 ID 或组织 ID |
| ApiKeySecretNotFound | 100036 | API Key 密钥不存在 |
| InvalidCredentials | 100037 | 登录凭证无效 |
| InvalidApiKey | 100038 | API Key 无效 |
| OwnerCannotModifySelfRole | 100039 | OWNER 不能修改自身角色 |
| ResetPasswordFailed | 100040 | 重置密码失败 |
| UserNotInitialized | 100041 | 用户未初始化 |

上述错误码在用户注册、登录、邀请成员、API Key 管理等接口中广泛使用。例如 `API/Controllers/UserManagement/UserController.cs` 中创建 API Key 时若 Key 已存在则抛出 `ApiKeyNotFound` 或 `CreateApiKeyFailed`。`ExceptionMiddleware` 捕获 `AppFriendlyException` 后将错误码与错误消息写入响应体 [API/System/Handlers/ExceptionMiddleware.cs:L24-L34]。

### 9.3. 短信/Captcha错误码 (11xxxx)

短信与Captcha错误码覆盖图形Captcha、短信Captcha、邮件Captcha的生成与校验场景，数值范围为 110000-110005。

| 常量名 | 数值 | 触发场景 |
|--------|------|----------|
| SendSMSTooOften | 110000 | 短信发送过于频繁，超出 `CaptchaSetting.ResendInterval`（60 秒）限制 |
| FailedToSendSMS | 110001 | 短信发送失败（如 SMS 服务商返回错误） |
| EmptyCaptcha | 110002 | Captcha为空 |
| InvalidCaptcha | 110003 | Captcha无效或已过期 |
| ErrorCaptcha | 110004 | Captcha校验出错 |
| FailedToSendEmail | 110005 | 邮件发送失败 |

Captcha相关Config定义于 `CaptchaSetting`：`CaptchaCodeLength = 5`、`SMSCodeLength = 6`、`EmailCodeLength = 6`、`ExpiredSeconds = 300`、`ResendInterval = 60`。`API/Controllers/UserManagement/CaptchaController.cs` 提供 `GET /api/captcha`（图形Captcha）与 `GET /api/captcha/sms`（短信Captcha）两个端点 [API/Controllers/UserManagement/CaptchaController.cs:L29-L43]。当用户提交的Captcha与缓存中的值不匹配时，抛出 `InvalidCaptcha`（110003）。

### 9.4. 组织相关错误码 (13xxxx)

组织相关错误码覆盖组织创建、更新、删除、成员管理及配额限制等场景，数值范围为 130000-130013。

| 常量名 | 数值 | 触发场景 |
|--------|------|----------|
| EmptyOrganizationName | 130000 | 组织名称为空 |
| OrganizationNameTooShort | 130001 | 组织名称过短 |
| OrganizationNameTooLong | 130002 | 组织名称过长 |
| InvalidOrganization | 130003 | 组织不存在或无效 |
| CreateOrganizationFailed | 130004 | 创建组织失败 |
| UpdateOrganizationFailed | 130005 | 更新组织失败 |
| DeleteOrganizationFailed | 130006 | 删除组织失败 |
| OrganizationHasProjects | 130007 | 组织下存在项目，无法删除 |
| OrganizationProjectDeleting | 130008 | 组织下项目正在删除中 |
| UnauthorizedOrganizationAccess | 130009 | 无权访问该组织 |
| ExceedHeadCountLimit | 130010 | 超出组织成员人数上限 |
| ExceedProjectLimit | 130011 | 超出组织项目数上限 |
| ExceedOrgLimit | 130012 | 超出组织数上限 |
| OrgAlreadyHasOwner | 130013 | 组织已存在 OWNER |

组织相关接口由 `API/Controllers/UserManagement/OrganizationController.cs` 提供，包括 `POST /api/user/organization`（创建）、`GET /api/user/organization`（查询）、`POST /api/user/organization/update`（更新）、`POST /api/user/organization/delete`（删除）[API/Controllers/UserManagement/OrganizationController.cs:L28-L71]。

### 9.5. 项目相关错误码 (14xxxx)

项目相关错误码覆盖项目创建、更新、删除、命名校验及访问Privilege等场景，数值范围为 140000-140008。

| 常量名 | 数值 | 触发场景 |
|--------|------|----------|
| EmptyProjectName | 140000 | 项目名称为空 |
| ProjectNameTooShort | 140001 | 项目名称过短 |
| ProjectNameTooLong | 140002 | 项目名称过长 |
| InvalidProject | 140003 | 项目不存在或无效 |
| CreateProjectFailed | 140004 | 创建项目失败 |
| UpdateProjectFailed | 140005 | 更新项目失败 |
| DeleteProjectFailed | 140006 | 删除项目失败 |
| ExistedProjectName | 140007 | 项目名称已存在 |
| UnauthorizedProjectAccess | 140008 | 无权访问该项目 |

项目相关接口由 `API/Controllers/UserManagement/ProjectController.cs` 提供，包括 `POST /api/user/project`（创建）、`GET /api/user/project`（查询）、`POST /api/user/project/update`（更新）、`POST /api/user/project/delete`（删除）[API/Controllers/UserManagement/ProjectController.cs:L31-L75]。项目删除采用异步队列机制，通过 `BullMqService.EnqueueProjectDeleteAsync` 将删除任务入队，删除过程中若再次访问项目将返回 `InvalidProject`（140003）。

### 9.6. Agent/查询相关错误码 (15xxxx)

Agent 与查询相关错误码覆盖 Agent Config、Trace 查询、ClickHouse 查询、过滤器校验等场景，数值范围为 150000-150024。

| 常量名 | 数值 | 触发场景 |
|--------|------|----------|
| EmptyProjectId | 150000 | Project ID 为空 |
| AgentSettingNotConfig | 150004 | Agent Config未设置 |
| AgentLimitExceeded | 150007 | 超出 Agent 数量限制 |
| DuplicateUserConfig | 150008 | 用户Config重复 |
| EmptyTraceIds | 150009 | Trace ID 列表为空 |
| ClickHouseQueryError | 150010 | ClickHouse 查询执行出错 |
| TooManyTraceIds | 150011 | Trace ID 数量超出上限 |
| InvalidFilterType | 150012 | 过滤器类型非法 |
| InvalidFilterColumn | 150013 | 过滤器列名非法 |
| InvalidFilterOperator | 150014 | 过滤器操作符非法 |
| InvalidFilterValue | 150015 | 过滤器值非法 |
| InvalidOrderBy | 150016 | 排序字段非法 |
| ClickHouseQueryTimeout | 150017 | ClickHouse 查询超时 |
| EmptyTraceId | 150018 | Trace ID 为空 |
| OrgAndProjectBothEmpty | 150019 | Org ID 与项目 ID 均为空 |
| UpdateAgentRateFailed | 150020 | 更新 Agent 费率失败 |
| AgentSessionNotFound | 150021 | Agent Session 不存在 |
| AgentConfigNotFound | 150022 | Agent Config不存在 |
| AgentReportTemplateNotFound | 150023 | Agent 报告模板不存在 |
| EmptyAgentReportTemplateName | 150024 | Agent 报告模板名称为空 |

Trace 查询接口由 `API/Controllers/DataManagement/MetricsController.cs` 提供，包括 `GET /api/data/metrics/observations`、`GET /api/data/metrics/scores`、`GET /api/data/metrics/traces` 与 `POST /api/data/metrics/traces` [API/Controllers/DataManagement/MetricsController.cs:L34-L125]。查询 Trace 时若 Trace ID 列表为空则抛出 `EmptyTraceIds`（150009），若 ClickHouse 查询执行失败则抛出 `ClickHouseQueryError`（150010），若查询超时则抛出 `ClickHouseQueryTimeout`（150017）。过滤器相关错误码（`InvalidFilterType`、`InvalidFilterColumn`、`InvalidFilterOperator`、`InvalidFilterValue`、`InvalidOrderBy`）在 `TraceFilterBuilder` 构建查询条件时触发。

### 9.7. Alert相关错误码 (16xxxx)

Alert相关错误码覆盖 Alert 的创建、更新、删除、订阅及参数校验等场景，数值范围为 160000-160015。

| 常量名 | 数值 | 触发场景 |
|--------|------|----------|
| AlertNotFound | 160000 | Alert 不存在 |
| CreateAlertFailed | 160001 | 创建 Alert 失败 |
| UpdateAlertFailed | 160002 | 更新 Alert 失败 |
| DeleteAlertFailed | 160003 | 删除 Alert 失败 |
| InvalidAlertPeriod | 160004 | Alert 统计周期非法 |
| InvalidAlertFrequency | 160005 | Alert 检查频率非法 |
| InvalidAlertField | 160006 | Alert 监控字段非法 |
| InvalidAlertOperator | 160007 | Alert 比较操作符非法 |
| InvalidAlertValue | 160008 | Alert 阈值非法 |
| InvalidAlertName | 160010 | Alert 名称为空 |
| InvalidAlertNotifyBy | 160011 | Alert 通知方式非法 |
| SubscribeAlertFailed | 160012 | 订阅 Alert 失败 |
| AlertOrgNotAccessible | 160013 | 无权访问该组织的 Alert |
| AlertProjectNotFound | 160014 | Alert 关联的项目不存在 |
| AlertNameTooLong | 160015 | Alert 名称过长 |

Alert相关接口由 `API/Controllers/UserManagement/AlertController.cs` 提供，包括 `GET /api/alert/config`（获取AlertConfig）、`GET /api/alert`（查询Alert）、`POST /api/alert`（创建Alert）、`POST /api/alert/update`（更新Alert）、`POST /api/alert/delete`（删除Alert）、`POST /api/alert/record/read`（标记Alert记录已读）、`GET /api/alert/record`（查询Alert记录）[API/Controllers/UserManagement/AlertController.cs:L30-L128]。Alert 的监控字段定义于 `AlertField` 枚举（如 `TotalTokens`、`TotalCost`、`ErrorCount`、`Latency`、`ErrorRate` 等），比较操作符定义于 `AlertOperator` 枚举（如 `GreaterThan`、`LessThan`、`EqualTo` 等）。

### 9.8. 微信相关错误码 (62xxxx)

微信相关错误码覆盖微信登录、消息校验、账号绑定等场景，数值范围为 620001-620017。

| 常量名 | 数值 | 触发场景 |
|--------|------|----------|
| InvalidWeChatAppToken | 620001 | 微信 App Token 无效 |
| ExamineWeChatSignatureFailed | 620002 | 微信签名校验失败 |
| GetWeChatTokenFailed | 620003 | 获取微信 Token 失败 |
| GetWeChatBasicUserInfoFailed | 620004 | 获取微信基础用户信息失败 |
| InvalidWeChatMessageType | 620005 | 微信消息类型非法 |
| InvalidWeChatMessageEvent | 620006 | 微信消息事件非法 |
| EmptyWeChatOpenId | 620007 | 微信 OpenId 为空 |
| InvalidWeChatCode | 620008 | 微信授权码无效 |
| WeChatAccountBinded | 620009 | 当前账号已绑定微信 |
| WeChatAccountBeenBinded | 620010 | 微信已被其他账号绑定 |
| WeChatAccountNotBinded | 620011 | 微信账号未绑定 |
| InvalidWeChatAccount | 620012 | 微信账号无效 |
| MobileBindedWeChatAccount | 620013 | 手机号已绑定微信账号 |
| FakedWeChatRequest | 620014 | 伪造的微信请求 |
| InvalidPayCertificate | 620016 | Payment证书无效 |
| GetPayCertificateFailed | 620017 | 获取Payment证书失败 |

微信相关接口由 `API/Controllers/ToolsManagement/WeChat/WeChatController.cs` 提供，包括 `GET /api/tools/wechat` 与 `POST /api/tools/wechat` [API/Controllers/ToolsManagement/WeChat/WeChatController.cs:L36-L68]。在 `NotifyController.WeChatNotify` 中，若请求体为空则抛出 `FakedWeChatRequest`（620014），随后调用 `ExamineWeChatRequest` 校验签名，签名校验失败时抛出 `ExamineWeChatSignatureFailed`（620002）[API/Controllers/PaymentManagement/NotifyController.cs:L29-L55]。

### 9.9. Payment相关错误码 (81xxxx)

Payment相关错误码覆盖微信Payment、Payment宝Payment、订单管理、产品管理等场景，数值范围为 810001-810027。

| 常量名 | 数值 | 触发场景 |
|--------|------|----------|
| WeChatSettingNotConfig | 810001 | 微信PaymentConfig未设置 |
| AlipaySettingNotConfig | 810002 | Payment宝PaymentConfig未设置 |
| AlipayConnectionError | 810003 | Payment宝连接错误 |
| AlipayTradeError | 810004 | Payment宝交易错误 |
| InvalidAlipayTradeNo | 810005 | Payment宝交易号无效 |
| InvalidAlipayTransaction | 810006 | Payment宝交易无效 |
| AlipaySignatureError | 810007 | Payment宝签名错误 |
| AlipaySignDictionaryError | 810008 | Payment宝签名参数错误 |
| InvalidWeChatSerialNO | 810009 | 微信证书序列号无效 |
| InvalidWeChatNotify | 810010 | 微信通知无效 |
| EmptyOrderNo | 810011 | 订单号为空 |
| DoNotOwnOrganization | 810012 | 当前用户不拥有任何组织 |
| ProductNotExist | 810013 | 产品不存在 |
| ProductDurationNotExist | 810014 | 产品时长不存在 |
| OrderNotExist | 810015 | 订单不存在 |
| EmptyWeChatTransaction | 810016 | 微信交易为空 |
| InvalidWeChatTradeNo | 810017 | 微信交易号无效 |
| EmptyWeChatNotify | 810018 | 微信通知为空 |
| UnsupportedPayMethod | 810019 | 不支持的Payment方式 |
| AlipayPlaceOrderError | 810020 | Payment宝下单错误 |
| WeChatEmptyResponse | 810021 | 微信返回空响应 |
| WeChatErrorResponse | 810022 | 微信返回错误响应 |
| CannotDowngradeProduct | 810023 | 不能降级产品 |
| WeChatQueryErrorResponse | 810024 | 微信查询返回错误响应 |
| InvalidTotalAmount | 810025 | 订单总金额无效 |
| OrderStateUpdateFailed | 810026 | 订单状态更新失败 |
| InvalidMerchant | 810027 | 商户无效 |

Payment相关接口由 `API/Controllers/PaymentManagement/OrderController.cs` 与 `API/Controllers/PaymentManagement/NotifyController.cs` 提供。`OrderController` 提供 `GET /api/payment/order`（查询订单）、`POST /api/payment/order`（下单）、`GET /api/payment/order/query`（查询交易状态）、`GET /api/payment/order/conversion`（查询转化率）[API/Controllers/PaymentManagement/OrderController.cs:L34-L79]。`NotifyController` 提供 `POST /api/payment/notify/wechatnotify` 与 `POST /api/payment/notify/alipaynotify` 两个回调端点 [API/Controllers/PaymentManagement/NotifyController.cs:L29-L57]。

### 9.10. 系统错误码 (99xxxx)

系统错误码覆盖加密解密、密码哈希、任务调度等系统级异常场景，数值范围为 990001-999999。

| 常量名 | 数值 | 触发场景 |
|--------|------|----------|
| EncryptionFailed | 990001 | 加密失败 |
| DecryptionFailed | 990002 | 解密失败 |
| PasswordHashFailed | 990003 | 密码哈希计算失败 |
| InvalidJobQuantity | 990004 | 任务数量非法 |
| DefaultException | 999999 | 默认异常（未分类错误） |

当系统抛出未捕获的异常时，`ExceptionMiddleware` 将 HTTP 状态码设置为 500，并返回 `ErrorCode = 500`、`ErrorMessage = TextContent.InternalServerError` 的响应体 [API/System/Handlers/ExceptionMiddleware.cs:L35-L43]。`DefaultException`（999999）作为兜底错误码，用于未明确分类的异常场景。

---

## 10. 附录

### 10.1. 术语表

以下术语在本文档中具有特定含义，且在代码中均有对应标识符，建议在翻译和开发中保留英文原文。

| 术语 | 说明 |
|------|------|
| Agent | Agent，指代 AI 应用中的执行单元，可独立完成特定任务 |
| Trace | Trace，指一次请求在系统中的完整调用链记录 |
| Span | Span，Trace 中的最小执行单元，代表一次操作或调用 |
| Token | Token，既指 LLM 的输入/输出计费单位，也指 API 访问凭证 |
| Alert | Alert，指根据监控指标触发的通知记录 |
| InsightService | 洞察服务，指 AgentInsightService（保持英文） 平台的核心服务 |

上述术语在代码中均有对应标识符，例如 `Models/Common/Enums/AlertEnum.cs` 中定义了 `AlertField` 枚举，`API/Controllers/AgentManagement/AgentSessionController.cs` 中定义了 `AgentSession` 实体，`Agents/server.py` 中实现了Session持久化逻辑。

### 10.2. 枚举定义汇总

AgentInsightService（保持英文） 在代码中共定义了 43 个枚举类型，覆盖Alert、审计、过滤、Payment、任务调度等核心领域。以下按模块分组列出全部枚举及其常量值。

#### 10.2.1. Alert相关枚举

定义于 `Models/Common/Enums/AlertEnum.cs`：

| 枚举 | 常量 | 值 | 说明 |
|------|------|-----|------|
| AlertTimeUnit | Minute / Hour / Day | 1 / 2 / 3 | Alert时间单位 |
| AlertOperator | GreaterThan / LessThan / EqualTo / GreaterThanOrEqualTo / LessThanOrEqualTo / NotEqualTo | 1~6 | Alert比较操作符 |
| AlertField | TotalTokens / TotalCost / ErrorCount / Latency / ErrorRate / InputTokens / OutputTokens / WarningCount / ObservationCount | 1~9 | Alert监控字段 |
| AlertRecordState | Active / Read | 1 / 2 | Alert记录状态 |
| AlertNotifyBy | System / SMS | 1 / 2 | Alert通知方式 |

#### 10.2.2. 审计相关枚举

定义于 `Models/Common/Enums/AuditEnum.cs`：

| 枚举 | 常量 |
|------|------|
| AuditAction | Create, Update, Delete, Login, Logout, Reset, Bind, UnBind, Place, Query, Notify |
| AuditResourceType | User, Organization, Project, Alert, ApiKey, Invitation, Order, WeChat, OrgPrivilege |

#### 10.2.3. 过滤相关枚举

定义于 `Models/Common/Enums/FilterEnum.cs`：

| 枚举 | 常量 | 值 |
|------|------|-----|
| FilterType | DateTime / String / Number / StringOptions / ArrayOptions / Boolean / Null | 1~7 |
| FilterOperator | GreaterThan / LessThan / GreaterThanOrEqualTo / LessThanOrEqualTo / EqualTo / Contains / DoesNotContain / StartsWith / EndsWith / AnyOf / NoneOf / AllOf / NotEqualTo / IsNull / IsNotNull | 1~15 |
| FilterColumn | Id / Name / Timestamp / UserId / SessionId / Environment / Version / Release / Tags / Bookmarked / Latency / InputTokens / OutputTokens / TotalTokens / Tokens / InputCost / OutputCost / TotalCost / Level / WarningCount / ErrorCount / DefaultCount / DebugCount / ModelNames / ScoresAvg | 1~25 |

#### 10.2.4. Payment相关枚举

定义于 `Models/Common/Enums/PaymentEnums.cs`：

| 枚举 | 常量 | 值 |
|------|------|-----|
| TradeState | SUCCESS / REFUND / NOTPAY / CLOSED / REVOKED / USERPAYING / PAYERROR / TRADE_CLOSED / TRADE_FINISHED / TRADE_SUCCESS / WAIT_BUYER_PAY | 1~7, 10~13 |
| SubPayMethod | WECHAT_JSAPI / WECHAT_NATIVE / WECHAT_MINIPROGRAM / ALIPAY_FAST_INSTANT_TRADE_PAY | 1, 2, 3, 11 |
| OrderState | Created / WaitForPay / Paid / Refunded / Cancelled / Closed / PayError | 1~7 |
| ProductType | None / Monthly / Permanent | 0~2 |
| PayMethod | WeChat / Alipay | 1 / 2 |
| AgentType | Assistant / Research | 1 / 2 |

#### 10.2.5. 任务调度相关枚举

定义于 `Models/Common/Enums/JobEnums.cs`：

| 枚举 | 常量 | 值 |
|------|------|-----|
| JobFrequency | Minutely / Hourly / Daily / Weekly / Monthly / Yearly | 1~6 |
| JobType | Regularly / Once / Permanently | 1~3 |
| JobCacheAction | Load / Create / Ignore | 1~3 |
| JobStatus | Created / Running / Completed | 1~3 |

#### 10.2.6. 用户与Privilege相关枚举

定义于 `Models/Common/Enums/UserEnum.cs`：

| 枚举 | 常量 | 值 |
|------|------|-----|
| PGRole | NONE / VIEWER / MEMBER / ADMIN / OWNER | 0~4 |
| ApiKeyScope | PROJECT / ORGANIZATION | 0 / 1 |
| UserConfigType | User / Organization / Project | 0~2 |
| LoginType | Password / SMS / WeChat / MiniProgram / APIKey | 1~5 |

#### 10.2.7. 微信相关枚举

定义于 `Models/Common/Enums/WeChatEnum.cs`：

| 枚举 | 常量 | 值 |
|------|------|-----|
| WeChatMessageType | None / Event / Text / Image / Voice / Video / Shortvideo / Location / Link | 0~8 |
| WeChatMessageEvent | Subscribe / Unsubscribe / Scan / Location / Click / View / MasssEndJobFinish | 1~7 |
| WeChatSubscribeScene | ADD_SCENE_SEARCH / ADD_SCENE_ACCOUNT_MIGRATION / ADD_SCENE_PROFILE_CARD / ADD_SCENE_QR_CODE / ADD_SCENE_PROFILE_LINK / ADD_SCENE_PROFILE_ITEM / ADD_SCENE_PAID / ADD_SCENE_WECHAT_ADVERTISEMENT / ADD_SCENE_REPRINT / ADD_SCENE_LIVESTREAM / ADD_SCENE_CHANNELS / ADD_SCENE_OTHERS | 1~12 |
| WeChatTradeType | JSAPI / NATIVE / APP / MICROPAY / MWEB / FACEPAY | 1~6 |
| WeChatPromotionScope | GLOBAL / SINGLE | 1 / 2 |
| WeChatPromotionType | CASH / NOCASH | 1 / 2 |

| WeChatBankType | ICBC_DEBIT / ICBC_CREDIT / ICBC_ECNY / ABC_DEBIT / ABC_CREDIT / ABC_ECNY / PSBC_CREDIT / PSBC_DEBIT / PSBC_ECNY / CCB_DEBIT / CCB_CREDIT / CCB_ECNY / CMB_DEBIT / CMB_CREDIT / CMB_ECNY / BOC_DEBIT / BOC_CREDIT / BOC_ECNY / COMM_DEBIT / COMM_CREDIT / COMM_ECNY / SPDB_DEBIT / SPDB_CREDIT / GDB_DEBIT / GDB_CREDIT / CMBC_DEBIT / CMBC_CREDIT / PAB_DEBIT / PAB_CREDIT / CEB_DEBIT / CEB_CREDIT / CIB_DEBIT / CIB_CREDIT / CIB_ECNY / CITIC_DEBIT / CITIC_CREDIT / BOSH_DEBIT / BOSH_CREDIT / AHRCUB_CREDIT / AHRCUB_DEBIT / AIB_DEBIT / ASCB_DEBIT / ATRB_DEBIT / BCZ_CREDIT / BCZ_DEBIT / BDB_DEBIT / BEEB_CREDIT / BEEB_DEBIT / BGZB_DEBIT / BHB_CREDIT / BHB_DEBIT / BJRCB_CREDIT / BJRCB_DEBIT / BNC_CREDIT / BNC_DEBIT / BOB_CREDIT / BOB_DEBIT / BOBBG_CREDIT / BOBBG_DEBIT / BOCD_DEBIT / BOCDB_DEBIT / BOCFB_DEBIT / BOCTS_DEBIT / BOD_CREDIT / BOD_DEBIT / BOFS_DEBIT / BOHN_DEBIT / BOIMCB_CREDIT / BOIMCB_DEBIT / BOJN_DEBIT / BOJX_DEBIT / BOLB_DEBIT / BOLFB_DEBIT / BONX_CREDIT / BONX_DEBIT / BOPDS_DEBIT / BOPJ_DEBIT / BOQHB_CREDIT / BOQHB_DEBIT / BOSXB_DEBIT / BOSZS_DEBIT / BOTSB_DEBIT / BOZ_CREDIT / BOZ_DEBIT / BSB_CREDIT / BSB_DEBIT / BYK_DEBIT / CBHB_DEBIT / CCAB_CREDIT / CCAB_DEBIT / CDRCB_DEBIT / CITIB_CREDIT / CITIB_DEBIT / CJCCB_DEBIT / CQB_CREDIT / CQB_DEBIT / CQRCB_CREDIT / CQRCB_DEBIT / CQTGB_DEBIT / CRB_CREDIT / CRB_DEBIT / CSCB_CREDIT / CSCB_DEBIT / CSRCB_CREDIT / CSRCB_DEBIT / CSXB_DEBIT / CYCB_CREDIT / CYCB_DEBIT / CZB_CREDIT / CZB_DEBIT / CZCB_CREDIT / CZCB_DEBIT / CZCCB_DEBIT / DANDONGB_CREDIT / DANDONGB_DEBIT / DBSB_DEBIT / DCSFRB_DEBIT / DHDYB_DEBIT / DHRB_DEBIT / DLB_CREDIT / DLB_DEBIT / DLRCB_DEBIT / DRCB_CREDIT / DRCB_DEBIT / DSB_DEBIT / DTCCB_DEBIT / DYB_CREDIT / DYB_DEBIT / DYCCB_DEBIT / DYLSB_DEBIT / DZB_DEBIT / DZCCB_DEBIT / EDRB_DEBIT / ESUNB_DEBIT / FBB_DEBIT / FDB_CREDIT / FDB_DEBIT / FJHXB_CREDIT / FJHXB_DEBIT / FJNX_CREDIT / FJNX_DEBIT / FUXINB_CREDIT / FUXINB_DEBIT / FXLZB_DEBIT / GADRB_DEBIT / GDHX_DEBIT / GDNYB_CREDIT / GDNYB_DEBIT / GDRCU_DEBIT / GLB_CREDIT / GLB_DEBIT / GLGMCB_DEBIT / GRCB_CREDIT / GRCB_DEBIT / GSB_DEBIT / GSNX_DEBIT / GSRB_DEBIT / GXNX_CREDIT / GXNX_DEBIT / GYCB_CREDIT / GYCB_DEBIT / GZCB_CREDIT / GZCB_DEBIT / GZCCB_CREDIT / GZCCB_DEBIT / GZNX_DEBIT / HAINNX_CREDIT / HAINNX_DEBIT / HANAB_DEBIT / HBCB_CREDIT / HBCB_DEBIT / HBNX_CREDIT / HBNX_DEBIT / HDCB_DEBIT / HEBNX_DEBIT / HFB_CREDIT / HFB_DEBIT / HKB_CREDIT / HKB_DEBIT / HKBEA_CREDIT / HKBEA_DEBIT / HKUB_DEBIT / HLDCCB_DEBIT / HLDYB_DEBIT / HLJRCUB_DEBIT / HMCCB_DEBIT / HNNX_DEBIT / HRBB_CREDIT / HRBB_DEBIT / HRCB_DEBIT / HRXJB_CREDIT / HRXJB_DEBIT / HSB_CREDIT / HSB_DEBIT / HSBC_DEBIT / HSBCC_CREDIT / HSBCC_DEBIT / HSCB_DEBIT / HUIHEB_DEBIT / HUNNX_DEBIT / HUSRB_DEBIT / HXB_CREDIT / HXB_DEBIT / HZB_CREDIT / HZB_DEBIT / HZCCB_DEBIT / IBKB_DEBIT / JCB_DEBIT / JCBK_CREDIT / JDHDB_DEBIT / JDZCCB_DEBIT / JHCCB_CREDIT / JHCCB_DEBIT / MYB_ECNY / JJCCB_CREDIT / JJCCB_DEBIT / UPQUICKPASS_DEBIT / JLB_CREDIT / JLB_DEBIT / JLNX_DEBIT / JNRCB_CREDIT / JNRCB_DEBIT / JRCB_CREDIT / JRCB_DEBIT / JSB_CREDIT / JSB_DEBIT / JSHB_CREDIT / JSHB_DEBIT / JSNX_CREDIT / JSNX_DEBIT / JUFENGB_DEBIT / JXB_DEBIT / JXNXB_DEBIT / JZB_CREDIT / JZB_DEBIT / JZCB_CREDIT / JZCB_DEBIT / KCBEB_DEBIT / KLB_CREDIT / KLB_DEBIT / KRCB_DEBIT / KSHB_DEBIT / KUERLECB_DEBIT / LCYRB_DEBIT / LICYRB_DEBIT / LJB_DEBIT / LLB_DEBIT / LLHZCB_DEBIT / LNNX_DEBIT / LPCB_DEBIT / LPSBLVB_DEBIT / LSB_CREDIT / LSB_DEBIT / LSCCB_DEBIT / LUZB_DEBIT / LWB_DEBIT / LYYHB_DEBIT / LZB_CREDIT / LZB_DEBIT / LZCCB_DEBIT / MHBRB_DEBIT / MINTAIB_CREDIT / MINTAIB_DEBIT / MPJDRB_DEBIT / MYCCB_DEBIT / NBCB_CREDIT / NBCB_DEBIT / NCB_DEBIT / NCBCB_DEBIT / NCCB_DEBIT / NJCB_CREDIT / NJCB_DEBIT / NJJDRB_DEBIT / NJXLRB_DEBIT / NMGNX_DEBIT / NNGMB_DEBIT / NUB_DEBIT / NYCCB_DEBIT / OCBCWHCB_DEBIT / OHVB_DEBIT / ORDOSB_CREDIT / ORDOSB_DEBIT / PBDLRB_DEBIT / PJDWHFB_DEBIT / PJJYRB_DEBIT / PZHCCB_DEBIT / QDCCB_CREDIT / QDCCB_DEBIT / QHDB_DEBIT / QHJDRB_DEBIT / QHNX_DEBIT / QJSYB_DEBIT / QLB_CREDIT / QLB_DEBIT / QLVB_DEBIT / QSB_CREDIT / QSB_DEBIT / QZCCB_CREDIT / QZCCB_DEBIT / RHCB_DEBIT / RQCZB_DEBIT / RXYHB_DEBIT / RZB_DEBIT / SCB_CREDIT / SCB_DEBIT / SCNX_DEBIT / SDEB_CREDIT / SDEB_DEBIT / SDRCU_DEBIT / SHHJB_DEBIT / SHINHAN_DEBIT / SHRB_DEBIT / SJB_CREDIT / SJB_DEBIT / SNB_DEBIT / SNCCB_DEBIT / SPDYB_DEBIT / SRB_DEBIT / SRCB_CREDIT / SRCB_DEBIT / SUZB_CREDIT / SUZB_DEBIT / SXNX_DEBIT / SXXH_DEBIT / SZRCB_CREDIT / SZRCB_DEBIT / TACCB_CREDIT / TACCB_DEBIT / TCRCB_DEBIT / TJB_CREDIT / TJB_DEBIT / TJBHB_CREDIT / TJBHB_DEBIT / TJHMB_DEBIT / TJNHVB_DEBIT / TLB_DEBIT / TLVB_DEBIT / TMDYB_DEBIT / TRCB_CREDIT / TRCB_DEBIT / TZB_CREDIT / TZB_DEBIT / UOB_DEBIT / URB_DEBIT / VBCB_DEBIT / WACZB_DEBIT / WB_DEBIT / WEB_DEBIT / TENPAY_ECNY / WEGOB_DEBIT / WFB_CREDIT / WFB_DEBIT / WHB_CREDIT / WHB_DEBIT / WHRC_CREDIT / WHRC_DEBIT / WHRYVB_DEBIT / WJRCB_CREDIT / WJRCB_DEBIT / WLMQB_CREDIT / WLMQB_DEBIT / WRCB_CREDIT / WRCB_DEBIT / WUHAICB_DEBIT / WZB_CREDIT / WZB_DEBIT / WZMSB_DEBIT / XAB_CREDIT / XAB_DEBIT / XCXPB_DEBIT / XHB_DEBIT / XHNMB_DEBIT / XIB_DEBIT / XINANB_DEBIT / XJB_DEBIT / XJJDRB_DEBIT / XJRCCB_DEBIT / XMCCB_CREDIT / XMCCB_DEBIT / XRTB_DEBIT / XTB_CREDIT / XTB_DEBIT / XWB_DEBIT / XXCB_DEBIT / XXHZCB_DEBIT / XXRB_DEBIT / XYPQZYCB_DEBIT / XZB_DEBIT / YACCB_DEBIT / YBCCB_DEBIT / YKCB_DEBIT / YLB_DEBIT / YNHTB_CREDIT / YNHTB_DEBIT / YNRCCB_CREDIT / YNRCCB_DEBIT / YQCCB_DEBIT / YQMYRB_DEBIT / YRRCB_CREDIT / YRRCB_DEBIT / YTB_DEBIT / YYBSCB_DEBIT / ZCRB_DEBIT / ZGB_DEBIT / ZGCB_DEBIT / ZHCB_DEBIT / ZHQYTB_DEBIT / ZJB_DEBIT / ZJLXRB_DEBIT / ZJRCUB_CREDIT / ZJRCUB_DEBIT / ZJTLCB_CREDIT / ZJTLCB_DEBIT / ZRCB_CREDIT / ZRCB_DEBIT / ZSXKCCB_DEBIT / ZYB_CREDIT / ZYB_DEBIT / ZZB_CREDIT / ZZB_DEBIT / ZZCCB_DEBIT / DINERSCLUD / MASTERCARD / VISA / AMERICANEXPRESS_CREDIT / DISCOVER / UPQUICKPASS_CREDIT / OTHERS | 1~428 |

#### 10.2.8. 工具相关枚举

定义于 `Models/Common/Enums/ToolsEnum.cs`：

| 枚举 | 常量 | 值 |
|------|------|-----|
| BulletinType | News / Activity / Information / Annoucement / Advertisement / Agreement | 1~5, 9 |
| BulletinStatus | Draft / Reviewing / Revision / Published / Expired / Closed | 1~6 |

#### 10.2.9. 其他业务枚举

| 枚举 | 定义位置 | 常量 |
|------|----------|------|
| TransactionType | `API/Notifications/PaymentTransactionNotification.cs` | WeChatTransaction, AlipayTransaction |
| RouteType | `API/System/Handlers/AgentInsightTransformLogic.cs` | None=0, Public=1, PublicApi=2 |
| Environment | `Agents/common/config.py` | DEVELOPMENT, STAGING, PRODUCTION |
| RetrieverType | `Agents/common/retriever.py` | BM25, VECTOR, CUSTOM_SERVICE |
| QueueType | `Entities/Common/Enums/QueueEnum.cs` | Audit=0, ExceptionRecord=1, UsageTracking=2, PerformanceRecord=3 |
| SMSInstance | `Entities/Common/Settings/SMSSetting.cs` | None=0, Aliyun=1, TencentCloud=2 |
| AgentInsightSettingType | `Models/Common/Enums/AgentInsightEnum.cs` | WeChat=1, Alipay=2 |

#### 10.2.10. 错误码枚举

`ExceptionCodes` 定义于 `Models/Common/Enums/ExceptionCodes.cs`，包含全部错误码常量。以下列出关键分组的代表性错误码：

| 分组 | 范围 | 示例 |
|------|------|------|
| 用户管理 | 100000~100041 | UnAuthToken=100000, InvalidCredentials=100037, InvalidApiKey=100038 |
| Captcha/SMS | 110000~110005 | SendSMSTooOften=110000, InvalidCaptcha=110003 |
| 组织管理 | 130000~130013 | EmptyOrganizationName=130000, ExceedHeadCountLimit=130010 |
| 项目管理 | 140000~140008 | EmptyProjectName=140000, UnauthorizedProjectAccess=140008 |
| Agent/Trace | 150000~150024 | EmptyTraceIds=150009, AgentSessionNotFound=150021 |
| Alert | 160000~160015 | AlertNotFound=160000, InvalidAlertOperator=160007 |
| Payment | 810001~810027 | WeChatSettingNotConfig=810001, ProductNotExist=810013 |
| 通用 | 990001~999999 | EncryptionFailed=990001, DefaultException=999999 |

### 10.3. Config规格速查

以下列出 AgentInsightService（保持英文） 的核心Config项及其默认值。所有 `${KEY}` 形式的值均需通过环境变量注入。

#### 10.3.1. 认证与安全

| Config键 | 默认值 | 说明 |
|--------|--------|------|
| JWTSettings.Algorithm | HS256 | JWT 签名算法 |
| JWTSettings.ExpiredTime | 43200 | Token 过期时间（秒），即 12 小时 |
| JWTSettings.ClockSkew | 5 | 时钟偏移容忍（秒） |
| JWTSettings.ValidateIssuer / ValidateAudience / ValidateLifetime / ValidateIssuerSigningKey | True | 校验开关 |
| JWTSettings.IssuerSigningKey | ${JWT_SIGNING_KEY} | 签名密钥 |
| JWTSettings.ValidIssuer | ${JWT_ISSUER} | 签发者 |
| JWTSettings.ValidAudience | ${JWT_AUDIENCE} | 受众 |
| AESEncryptionKey | ${AES_KEY} | AES 加密密钥 |

#### 10.3.2. 数据库连接

| Config键 | 默认值 |
|--------|--------|
| ConnectionStrings.UserDbConnection | PORT=${USER_DB_PORT};DATABASE=${USER_DB_NAME};HOST=postgres;PASSWORD=${USER_DB_PASSWORD};USER ID=${USER_DB_USER};Timeout=60;Pooling=true;MinPoolSize=10;MaxPoolSize=200;ConnectionLifetime=300 |
| ConnectionStrings.DataDbConnection | PORT=${DATA_DB_PORT};DATABASE=${DATA_DB_NAME};HOST=postgres;PASSWORD=${DATA_DB_PASSWORD};USER ID=${DATA_DB_USER};Timeout=60;Pooling=true;MinPoolSize=10;MaxPoolSize=200;ConnectionLifetime=300 |
| ConnectionStrings.TrackingDbConnection | PORT=${TRACKING_DB_PORT};DATABASE=${TRACKING_DB_NAME};HOST=postgres;PASSWORD=${TRACKING_DB_PASSWORD};USER ID=${TRACKING_DB_USER};Timeout=60;Pooling=true;MinPoolSize=10;MaxPoolSize=200;ConnectionLifetime=300 |
| ConnectionStrings.ClickHouseDbConnection | Host=${CLICKHOUSE_HOST};Port=${CLICKHOUSE_PORT};Username=${CLICKHOUSE_USER};Password=${CLICKHOUSE_PASSWORD};Database=${CLICKHOUSE_DB};PoolSize=10;MaxPoolSize=50;ConnectionTimeout=30;CommandTimeout=60 |

#### 10.3.3. 缓存与消息队列

| Config键 | 默认值 |
|--------|--------|
| Redis.ConnectionString | localhost:${REDIS_PORT},password=${REDIS_AUTH} |

#### 10.3.4. 反向代理

| Config键 | 默认值 |
|--------|--------|
| ReverseProxy.Routes.AgentInsight-Route-API.Match.Path | /api/public/{**catch-all} |
| ReverseProxy.Routes.AgentInsight-Route-Public.Match.Path | /public/{**catch-all} |
| ReverseProxy.Clusters.AgentInsight-Langfuse-Cluster.Destinations.AgentInsight-Destination.Address | http://localhost:3000/ |

#### 10.3.5. Captcha与本地化

| Config键 | 默认值 |
|--------|--------|
| CaptchaSetting.CaptchaCodeLength | 5 |
| CaptchaSetting.SMSCodeLength / EmailCodeLength | 6 |
| CaptchaSetting.ExpiredSeconds | 300 |
| CaptchaSetting.ResendInterval | 60 |
| LocalizationSettings.DefaultCulture | zh-CN |
| LocalizationSettings.SupportedCultures | ['zh-CN', 'zh-TW', 'zh-HK', 'en'] |

#### 10.3.6. Log

| Config键 | 默认值 |
|--------|--------|
| Logging.LogLevel.Default | Warning |
| Logging.File.FileName | logs/application-.log |
| Logging.File.FileSizeLimitBytes | 10485760 |
| Logging.File.MaxRollingFiles | 30 |

#### 10.3.7. Python 服务Config

| Config键 | 默认值 |
|--------|--------|
| name | agentinsight-agents |
| version | 1.0.0 |
| description | AgentInsight Multi-Agent AI Service |
| requires-python | >=3.11 |
| python_version | 3.11 |
| line-length | 100 |
| fail_under | 70 |

### 10.4. 依赖项清单

AgentInsightService（保持英文） 由多个子项目组成，各子项目的依赖项分别声明于对应的依赖清单文件中。

#### 10.4.1. API 子项目（C# / .NET）

API 子项目基于 ASP.NET Core 8 与 Furion 框架构建，核心 NuGet 依赖包括：

| 依赖包 | 用途 |
|--------|------|
| AlipaySDKNet.Standard | Payment宝Payment SDK 集成 |
| MediatR | 事件通知与命令查询分离 |
| BouncyCastle.Cryptography | 加密算法库 |
| Npgsql | PostgreSQL 数据库驱动 |
| StackExchange.Redis | Redis 客户端 |
| Yarp.ReverseProxy | 反向代理路由 |
| My.Extensions.Localization.Json | JSON 本地化资源 |
| Microsoft.VisualStudio.Azure.Containers.Tools.Targets | Docker 容器化支持 |

#### 10.4.2. Agents Python

Agents 子项目基于 Python 3.11 与 FastAPI 构建，核心依赖包括：

| 依赖包 | 用途 |
|--------|------|
| fastapi | Web 框架 |
| langchain | 语言链框架 |
| langgraph | 多 Agent 协同 |
| qdrant-client | 向量数据库客户端 |
| chromadb | 向量数据库 |
| openai | OpenAI API 客户端 |
| agentinsight-sdk | AgentInsight 平台 SDK |
| uvicorn | ASGI 服务器 |
| pydantic | 数据验证 |

#### 10.4.3. Admin Django

Admin 子项目基于 Django 4.2 构建，核心依赖包括：

| 依赖包 | 用途 |
|--------|------|
| Django | Web 框架 |
| django-simpleui | 后台管理界面 |
| element-ui | 前端组件库（Vue 2） |

---

## 附录: 代码术语与枚举（AST/扫描提取）

### 核心类名

`XmlSerializerOutputFormatterWithoutNamespace`, `SpecificSystemTextJsonOutputFormatter`, `SpecificSystemTextJsonInputFormatter`, `StartupTaskWebApplicationExtensions`, `AgentInsightSettingNameAttribute`, `ConfigurationPlaceholderResolver`, `WeChatNotifyReceivedNotification`, `CreateMembershipInvitationBody`, `PaymentTransactionNotification`, `WeChatMiniProgramLoginResponse`, `AgentInsightPerformanceRecord`, `AgentInsightTransformProvider`, `PaymentTransactionSaveHandler`, `WeChatPayCertificateResponse`, `AgentInsightExceptionRecord`, `AgentInsightProductDuration`, `ServiceCollectionExtensions`, `TraditionalChineseConverter`, `TraditionalChineseExtension`, `WeChatNotifyReceivedHandler`, `WeChatPayEncryptCertificate`, `AgentInsightTransformLogic`, `AlertTriggeredNotification`, `WeChatOrderBodyGoodsDetail`, `AgentInsightOrderResponse`, `HttpRequestBuilderService`, `NullableDateTimeConverter`, `ObservationCountEvaluator`, `ProductConversionResponse`, `WeChatTextMessageResponse`, `WeChatTransactionResponse`, `WeChatTransationSceneInfo`, `AgentInsightAPISecretKey`, `NpgsqlNullNameTranslator`, `AgentReportTemplateBody`, `ConfigureMvcJsonOptions`, `FilterOperatorConverter`, `FurionAppContextService`, `WeChatRefundTransaction`, `WeChatTransactionAmount`, `AgentSessionController`, `ApiKeyValidationResult`, `CreateOrganizationBody`, `GlobalExceptionHandler`, `LowercaseEnumConverter`, `OrganizationController`, `OrganizationMembership`, `TraceCalculatedMetrics`, `UpdateOrganizationBody`, `WeChatSignatureService`, `WeChatTransactionPayer`, `AgentConfigController`, `AgentInsightOrderBody`, `AgentReportController`, `CamelCaseNamingPolicy`, `LowerCaseNamingPolicy`, `OutputTokensEvaluator`, `SettingsNameAttribute`, `SwaggerApiDescription`, `TraceIngestionPayload`, `WarningCountEvaluator`, `WeChatMessageResponse`, `WeChatOrderBodyAmount`, `WeChatOrderBodyDetail`, `WeChatOrderBodySettle`, `CreateUserConfigBody`, `FilterEnumExtensions`, `HttpContextExtension`, `InputTokensEvaluator`, `MembershipInvitation`, `MvcOptionsExtensions`, `SkipSetUserAttribute`, `TotalTokensEvaluator`, `TraceMetricsResponse`, `UpdateUserConfigBody`, `UserConfigController`, `WeChatJSAPIOrderBody`, `WeChatNotifyResource`, `WeChatOrderBodyPayer`, `WeChatOrderBodyScene`, `WeChatOrderBodyStore`, `WeChatPayCertificate`, `WeChatPhoneWatermark`, `WeChatPromotionGoods`, `AgentInsightProduct`, `AgentInsightSetting`, `AgentReportTemplate`, `AgentSessionHandler`, `AlertMetricsHandler`, `ClickHouseConverter`, `CurrentOrgPrivilege`, `ErrorCountEvaluator`, `ExceptionMiddleware`, `OrganizationHandler`, `PersistentQueueItem`, `SanitizeInputFilter`, `WeChatLoginResponse`, `WeChatOrderResponse`, `WeChatPhoneResponse`, `WeChatRefundAccount`, `AgentConfigHandler`, `AgentConfigPayload`, `AgentReportHandler`, `BulletinController`, `CreateBulletinBody`, `DatabaseUpgradeJob`, `ErrorRateEvaluator`, `ExceptionExtension`, `RateLimitAttribute`, `RequestAuditFilter`, `SystemAlertHandler`, `TotalCostEvaluator`, `TraceFilterBuilder`, `TraceIngestionData`, `WeChatRefundAmount`, `WeChatResponseBase`, `AgentInsightAudit`, `AgentInsightConst`, `AgentInsightOrder`, `AgentInsightRegex`, `AlertMetricsConst`, `AlipayTransaction`, `ApiControllerBase`, `AutoSetUserFilter`, `BeijingTimeHelper`, `CaptchaController`, `CreateProjectBody`, `DateTimeConverter`, `DateTimeExtension`, `IPAddressResponse`, `MetricsController`, `ProductController`, `ProjectCalculated`, `ProjectController`, `ProjectMembership`, `ResetPasswordBody`, `TencentSMSSetting`, `TraceIngestionJob`, `TraceSelectFields`, `UpdateProjectBody`, `UsageTrackingBase`, `UserConfigHandler`, `WeChatTransaction`, `AgentSessionBody`, `ClickHouseClient`, `ClickHouseHelper`, `HealthController`, `LatencyEvaluator`, `NotifyController`, `OrganizationBase`, `PaymentExtension`, `ThirdPartyHelper`, `TraceMetricsBody`, `WeChatController`, `WeChatRefundBody`, `AlertController`, `BulletinHandler`, `CaptchaResponse`, `ContextTracking`, `CreateAlertBody`, `DoubleConverter`, `FilterCondition`, `ModelController`, `ModelDefinition`, `ObjectExtension`, `OrderController`, `OrderRepository`, `RouteConvention`, `SMSAlertHandler`, `StringExtension`, `TraceMetricsRow`, `UpdateAlertBody`, `WeChatModelBase`, `WeChatOrderBody`, `WeChatPromotion`, `ApiHandlerBase`, `ApiKeyResponse`, `AssignRoleBody`, `CaptchaHandler`, `CaptchaService`, `CaptchaSetting`, `DeadLetterItem`, `EncryptService`, `LangfuseAPIKey`, `MetricsHandler`, `ModelPriceTier`, `PaymentService`, `ProductHandler`, `ProjectHandler`, `SQLSugarHelper`, `SettingHandler`, `SettingService`, `SplitModelBase`, `ToolsExtension`, `UserController`, `AliSMSSetting`, `AlipaySetting`, `ApiheResponse`, `AtomicInteger`, `BullMqService`, `DataQueueItem`, `GZipExtension`, `ModelDateBase`, `NotifyHandler`, `PgEnumConvert`, `SysExtensions`, `TraceCountRow`, `TraceIdResult`, `UsageTracking`, `UserExtension`, `UserPrivilege`, `WeChatAccount`, `WeChatHandler`, `WeChatMessage`, `WeChatService`, `WeChatSetting`, `AgentSession`, `AlertHandler`, `AlertMetrics`, `AlertService`, `MetricsConst`, `MiniUserBody`, `ModelHandler`, `OrderHandler`, `OrgPrivilege`, `Organization`, `SysExtension`, `TraceDataRow`, `TraceMetrics`, `UserAlertLog`, `WeChatNotify`, `AgentConfig`, `AlertConfig`, `AlertRecord`, `ApiResponse`, `MailSetting`, `Observation`, `RetryHelper`, `TextContent`, `UserHandler`, `UserService`, `UserSession`, `WeChatPhone`, `WeChatToken`, `AlertConst`, `BatchQueue`, `CacheConst`, `JwtHandler`, `ModelConst`, `ModelPrice`

### 数据表名/列名

`cloud_free_tier_usage_threshold_state`, `agentinsight_wechatrefundtransaction`, `agentinsight_wechatnotifyresource`, `agentinsight_wechatpromotiongoods`, `agentinsight_agentreporttemplate`, `agentinsight_currentorgprivilege`, `agentinsight_wechatrefundaccount`, `agentinsight_wechatrefundamount`, `agentinsight_alipaytransaction`, `agentinsight_performancerecord`, `agentinsight_projectcalculated`, `agentinsight_wechattransaction`, `cloud_billing_cycle_updated_at`, `agentinsight_api_secret_keys`, `agentinsight_exceptionrecord`, `agentinsight_productduration`, `agentinsight_wechatpromotion`, `agentinsight_wechat_account`, `agentinsight_userprivilege`, `cloud_billing_cycle_anchor`, `agentinsight_agentsession`, `agentinsight_orgprivilege`, `agentinsight_useralertlog`, `agentinsight_wechat_token`, `agentinsight_wechatnotify`, `cloud_current_cycle_usage`, `agentinsight_agentconfig`, `agentinsight_alertrecord`, `organization_memberships`, `agentinsight_job_record`, `agentinsight_userconfig`, `usage_pricing_tier_name`, `agentinsight_useralert`, `fast_hashed_secret_key`, `membership_invitations`, `provided_usage_details`, `agentinsight_bulletin`, `completion_start_time`, `parent_observation_id`, `provided_cost_details`, `usage_pricing_tier_id`, `agentinsight_product`, `agentinsight_setting`, `ai_features_enabled`, `project_memberships`, `provided_model_name`, `agentinsight_audit`, `agentinsight_order`, `display_secret_key`, `execution_trace_id`, `invited_by_user_id`, `hashed_secret_key`, `internal_model_id`, `long_string_value`, `observation_count`, `org_membership_id`, `ObservationCount`, `buyer_pay_amount`, `model_parameters`, `tokenizer_config`, `tool_definitions`, `buyer_user_name`, `buyer_user_type`, `organization_id`, `pricing_tier_id`, `tool_call_names`, `v4_beta_enabled`, `author_user_id`, `buyer_logon_id`, `dataset_run_id`, `email_verified`, `observation_id`, `prompt_version`, `retention_days`, `status_message`, `buyer_user_id`, `default_count`, `match_pattern`, `organizations`, `output_tokens`, `pricing_tiers`, `send_pay_date`, `usage_details`, `warning_count`, `DefaultCount`, `OutputTokens`, `WarningCount`, `cloud_config`, `cost_details`, `input_tokens`, `last_used_at`, `observations`, `out_trade_no`, `output_price`, `project_role`, `string_value`, `tokenizer_id`, `total_amount`, `total_tokens`, `tracemetrics`, `trade_status`, `Environment`, `InputTokens`, `TotalTokens`, `debug_count`, `error_count`, `input_price`, `model_names`, `output_cost`, `prompt_name`, `total_price`, `Bookmarked`, `DebugCount`, `ErrorCount`, `ModelNames`, `OutputCost`, `Parameters`, `created_at`, `deleted_at`, `expires_at`, `has_traces`, `input_cost`, `is_default`, `is_deleted`, `model_name`, `project_id`, `public_key`, `scores_avg`, `session_id`, `start_date`, `start_time`, `tool_calls`, `total_cost`, `updated_at`, `usage_type`, `CreatedAt`, `InputCost`, `IsDeleted`, `ProjectId`, `ScoresAvg`, `SessionId`, `Timestamp`, `TotalCost`, `UpdatedAt`, `config_id`, `data_blob`, `data_type`, `prompt_id`, `starttime`, `Metadata`, `api_keys`, `end_time`, `event_ts`, `model_id`, `org_role`, `projects`, `queue_id`, `trace_id`, `trade_no`, `EventTs`, `Latency`, `Release`, `TraceId`, `Version`, `comment`, `endtime`, `user_id`, `Output`, `Public`, `UserId`, `models`, `org_id`, `prices`, `scores`, `source`, `status`, `traces`, `Input`, `Level`, `Total`, `admin`, `email`, `price`, `scope`, `users`, `value`, `Name`, `Tags`, `host`, `role`, `type`, `Id`

### 属性/字段名

`AgentInsightSettingExpiredMinutes`, `CloudFreeTierUsageThresholdState`, `ScoreToTraceObservationsInterval`, `WeChatMerchantPrivateKeyCacheKey`, `AuthorizedRefreshAccessTokenUrl`, `ConfigDisableObservationsFinal`, `ClickHouseQueryTimeoutSeconds`, `PaymentTransactionSaveFailed`, `WeChatPayCertificateCacheKey`, `AgentInsightSettingCacheKey`, `CurrentOrgPrivilegeCacheKey`, `ObservationsToTraceInterval`, `CloudBillingCycleUpdatedAt`, `DefaultCacheExpiredMinutes`, `DefaultMonthlyResearchRate`, `MerchantPrivateKeyFilePath`, `StartNowJobIntervalSeconds`, `TraceNameContainsCondition`, `WeChatPayPublicKeyCacheKey`, `WeChatPayPublicKeyFilePath`, `CacheScanFrequencyMinutes`, `KeyedService_ClickHouseDb`, `RateLimitExceededResponse`, `TracesObservationStatsCte`, `TransactionTimeoutSeconds`, `AlipayOrderErrorResponse`, `AuthorizedAccessTokenUrl`, `ClickHouseSettingsClause`, `FieldObsObservationCount`, `MonthlyUsedPermanentRate`, `PayCertificatesUrlSuffix`, `WeChatQueryErrorResponse`, `CloudBillingCycleAnchor`, `DefaultMonthlyAgentRate`, `JoinScoreConditionInner`, `KeyedService_TrackingDb`, `PaymentTransactionRetry`, `PrivilegeExpiredMinutes`, `TraceIngestionTimeoutMs`, `UsedMonthlyResearchRate`, `UserSessionExpiredHours`, `User_Organization_Order`, `CloudCurrentCycleUsage`, `EmailCaptchaSenderName`, `ScoreTimestampInterval`, `SlowRequestThresholdMs`, `TracesCountSqlTemplate`, `AuthorizedUserInfoUrl`, `DefaultHeadCountLimit`, `FieldTraceEnvironment`, `JoinObsConditionInner`, `ObservationCoreSelect`, `Payment_Product_Order`, `TimestampGteCondition`, `TimestampLteCondition`, `TraceIdMixedCondition`, `TracesDataSqlTemplate`, `TradeNOQueryUrlSuffix`, `UserCacheExpiredHours`, `UserPrivilegeCacheKey`, `WeChatPayCertificates`, `ApiSecretKeyCacheKey`, `DefaultSortDirection`, `FieldObsDefaultCount`, `FieldObsOutputTokens`, `FieldObsWarningCount`, `FieldTraceBookmarked`, `GetWeChatTokenFailed`, `MiniProgramAppSecret`, `ObsStartTimeInterval`, `OrderByTimestampDesc`, `OrgPrivilegeCacheKey`, `Payment_Notify_Order`, `ProvidedUsageDetails`, `SubscribeSceneString`, `Tools_Bulletin_Order`, `TraceIdsByProjectSql`, `TracesSimpleCountSql`, `UsagePricingTierName`, `UsedMonthlyAgentRate`, `Agent_Session_Order`, `AlertTracesCacheKey`, `AuthorizationSchema`, `BasicAccessTokenUrl`, `CaptchaCodeCacheKey`, `CompletionStartTime`, `DefaultProjectLimit`, `ElapsedMilliseconds`, `EmailCaptchaContent`, `EmailCaptchaSubject`, `FastHashedSecretKey`, `FieldObsInputTokens`, `FieldObsTotalTokens`, `FieldTraceSessionId`, `FieldTraceTimestamp`, `InternalServerError`, `KeyedService_DataDb`, `KeyedService_UserDb`, `MonthlyResearchRate`, `ObservationCoreFrom`, `ParentObservationId`, `Payment_Order_Order`, `ProvidedCostDetails`, `SMSInstanceCacheKey`, `Tools_Setting_Order`, `TracesScoreStatsCte`, `TracesSelectMetrics`, `TracesSimpleDataSql`, `UserSessionCacheKey`, `WechatPayContribute`, `Agent_Config_Order`, `Agent_Report_Order`, `AlertTemplateParam`, `BaseWhereCondition`, `Data_Metrics_Order`, `DefaultEnvironment`, `DefaultMonthlyRate`, `EncryptCertificate`, `FieldObsDebugCount`, `FieldObsErrorCount`, `FieldObsModelNames`, `FieldObsOutputCost`, `HKSMSLoginTemplate`, `HasExceedRateLimit`, `InvalidTotalAmount`, `JoinScoreCondition`, `LoginTemplateParam`, `MerchantContribute`, `MetadataDictionary`, `NativePayUrlSuffix`, `PayCertificatesUrl`, `Tools_Wechat_Order`, `TracesSelectScores`, `TradeQueryResponse`, `UsagePricingTierId`, `UserNotInitialized`, `UserPhoneNumberUrl`, `User_Captcha_Order`, `User_Project_Order`, `AiFeaturesEnabled`, `AlipayTransaction`, `CancellationToken`, `CaptchaCodeLength`, `DefaultSortColumn`, `DefaultTemplateId`, `FieldObsInputCost`, `FieldObsTotalCost`, `FieldTraceEventTs`, `FieldTraceRelease`, `FieldTraceVersion`, `FrequencyQuantity`, `JSAPIPayUrlSuffix`, `JwtApiKeyCacheKey`, `ProductDurationId`, `ProvidedModelName`, `QueryIPAddressUrl`, `ScoreTimestampGte`, `SqlFunctionToDate`, `TableObservations`, `UsedPermanentRate`, `User_Config_Order`, `User_Organization`, `WeChatTransaction`, `ApiheSuccessCode`, `BasicUserInfoUrl`, `CompletionTokens`, `Data_Model_Order`, `DefaultSortField`, `DefaultTotalRate`, `DisplaySecretKey`, `ExecutionTraceId`, `FieldTraceUserId`, `JoinObsCondition`, `LimitOneByClause`, `MiniProgramAppId`, `MonthlyAgentRate`, `ObservationCount`, `PaginationClause`, `SettlementRefund`, `TracesSelectCore`, `User_Alert_Order`, `User_Login_Order`, `WechatpayGoodsId`, `AlertMetricsSql`, `AlertTemplateId`, `AliAlertMessage`, `AlipayPublicKey`, `Code2SessionUrl`, `DefaultOrgLimit`, `DefaultPageSize`, `EmailCodeLength`, `FieldObsLatency`, `HashedSecretKey`, `InternalModelId`, `InvitedByUserId`, `LastCompletedAt`, `LoginTemplateId`, `LongStringValue`, `MerchantGoodsId`, `MobileVerfiedAt`, `ModelParameters`, `ObsStartTimeGte`, `OrgMembershipId`, `OtherContribute`, `Payment_Product`, `PurePhoneNumber`, `ReceivedAccount`, `RefundUrlSuffix`, `SMSCodeCacheKey`, `SettlementTotal`, `TokenizerConfig`, `ToolDefinitions`, `TraceMetricsSql`, `TradeNOQueryUrl`, `UsedMonthlyRate`, `WeChatAccountId`, `WeChatPhoneCode`, `XAccessTokenKey`, `AcceptEncoding`, `AcceptLanguage`, `AccessTokenKey`, `AssociatedData`, `BuyerPayAmount`, `CommaDelimiter`, `DefaultOrderBy`, `DiscountAmount`, `DiscountRefund`, `EnableTracking`, `ExpiredSeconds`, `FieldTraceName`, `FieldTraceTags`, `HeadCountLimit`, `OrganizationId`, `Payment_Notify`, `PeriodQuantity`, `PhotoUrlString`, `PromotionGoods`, `RefundAccounts`, `RefundAmountId`, `RefundQuantity`, `ResendInterval`, `SubscribeScene`, `Tools_Bulletin`, `TracesSelectIO`, `TradeStateDesc`, `TradeStateEnum`, `WeChatPaySkuId`, `WeChatRefundId`, `Agent_Session`, `AlipaySetting`

### 枚举常量

`BulletinType`, `News`, `Activity`, `Information`, `Annoucement`, `Advertisement`, `Agreement`, `BulletinStatus`, `Draft`, `Reviewing`, `Revision`, `Published`, `Expired`, `Closed`, `AlertTimeUnit`, `Minute`, `Hour`, `Day`, `AlertOperator`, `GreaterThan`, `LessThan`, `EqualTo`, `GreaterThanOrEqualTo`, `LessThanOrEqualTo`, `NotEqualTo`, `AlertField`, `TotalTokens`, `TotalCost`, `ErrorCount`, `Latency`, `ErrorRate`, `InputTokens`, `OutputTokens`, `WarningCount`, `ObservationCount`, `AlertRecordState`, `Active`, `Read`, `AlertNotifyBy`, `System`, `SMS`, `AuditAction`, `Create`, `Update`, `Delete`, `Login`, `Logout`, `Reset`, `Bind`, `UnBind`, `Place`, `Query`, `Notify`, `AuditResourceType`, `User`, `Organization`, `Project`, `Alert`, `ApiKey`, `Invitation`, `Order`, `WeChat`, `OrgPrivilege`, `WeChatMessageType`, `None`, `Event`, `Text`, `Image`, `Voice`, `Video`, `Shortvideo`, `Location`, `Link`, `WeChatMessageEvent`, `Subscribe`, `Unsubscribe`, `Scan`, `Click`, `View`, `MasssEndJobFinish`, `WeChatSubscribeScene`, `ADD_SCENE_SEARCH`, `ADD_SCENE_ACCOUNT_MIGRATION`, `ADD_SCENE_PROFILE_CARD`, `ADD_SCENE_QR_CODE`, `ADD_SCENE_PROFILE_LINK`, `ADD_SCENE_PROFILE_ITEM`, `ADD_SCENE_PAID`, `ADD_SCENE_WECHAT_ADVERTISEMENT`, `ADD_SCENE_REPRINT`, `ADD_SCENE_LIVESTREAM`, `ADD_SCENE_CHANNELS`, `ADD_SCENE_OTHERS`, `WeChatTradeType`, `JSAPI`, `NATIVE`, `APP`, `MICROPAY`, `MWEB`, `FACEPAY`, `WeChatPromotionScope`, `GLOBAL`, `SINGLE`, `WeChatPromotionType`, `CASH`, `NOCASH`, `WeChatBankType`, `ICBC_DEBIT`, `ICBC_CREDIT`, `ICBC_ECNY`, `ABC_DEBIT`, `ABC_CREDIT`, `ABC_ECNY`, `PSBC_CREDIT`, `PSBC_DEBIT`, `PSBC_ECNY`, `CCB_DEBIT`, `CCB_CREDIT`, `CCB_ECNY`, `CMB_DEBIT`, `CMB_CREDIT`, `CMB_ECNY`, `BOC_DEBIT`, `BOC_CREDIT`, `BOC_ECNY`, `COMM_DEBIT`, `COMM_CREDIT`, `COMM_ECNY`, `SPDB_DEBIT`, `SPDB_CREDIT`, `GDB_DEBIT`, `GDB_CREDIT`, `CMBC_DEBIT`, `CMBC_CREDIT`, `PAB_DEBIT`, `PAB_CREDIT`, `CEB_DEBIT`, `CEB_CREDIT`, `CIB_DEBIT`, `CIB_CREDIT`, `CIB_ECNY`, `CITIC_DEBIT`, `CITIC_CREDIT`, `BOSH_DEBIT`, `BOSH_CREDIT`, `AHRCUB_CREDIT`, `AHRCUB_DEBIT`, `AIB_DEBIT`, `ASCB_DEBIT`, `ATRB_DEBIT`, `BCZ_CREDIT`, `BCZ_DEBIT`, `BDB_DEBIT`, `BEEB_CREDIT`, `BEEB_DEBIT`, `BGZB_DEBIT`, `BHB_CREDIT`, `BHB_DEBIT`, `BJRCB_CREDIT`, `BJRCB_DEBIT`, `BNC_CREDIT`, `BNC_DEBIT`, `BOB_CREDIT`, `BOB_DEBIT`, `BOBBG_CREDIT`, `BOBBG_DEBIT`, `BOCD_DEBIT`, `BOCDB_DEBIT`, `BOCFB_DEBIT`, `BOCTS_DEBIT`, `BOD_CREDIT`, `BOD_DEBIT`, `BOFS_DEBIT`, `BOHN_DEBIT`, `BOIMCB_CREDIT`, `BOIMCB_DEBIT`, `BOJN_DEBIT`, `BOJX_DEBIT`, `BOLB_DEBIT`, `BOLFB_DEBIT`, `BONX_CREDIT`, `BONX_DEBIT`, `BOPDS_DEBIT`, `BOPJ_DEBIT`, `BOQHB_CREDIT`, `BOQHB_DEBIT`, `BOSXB_DEBIT`, `BOSZS_DEBIT`, `BOTSB_DEBIT`, `BOZ_CREDIT`, `BOZ_DEBIT`, `BSB_CREDIT`, `BSB_DEBIT`, `BYK_DEBIT`, `CBHB_DEBIT`, `CCAB_CREDIT`, `CCAB_DEBIT`, `CDRCB_DEBIT`, `CITIB_CREDIT`, `CITIB_DEBIT`, `CJCCB_DEBIT`, `CQB_CREDIT`, `CQB_DEBIT`, `CQRCB_CREDIT`, `CQRCB_DEBIT`, `CQTGB_DEBIT`, `CRB_CREDIT`, `CRB_DEBIT`, `CSCB_CREDIT`, `CSCB_DEBIT`, `CSRCB_CREDIT`, `CSRCB_DEBIT`, `CSXB_DEBIT`, `CYCB_CREDIT`, `CYCB_DEBIT`, `CZB_CREDIT`, `CZB_DEBIT`, `CZCB_CREDIT`, `CZCB_DEBIT`, `CZCCB_DEBIT`, `DANDONGB_CREDIT`, `DANDONGB_DEBIT`, `DBSB_DEBIT`, `DCSFRB_DEBIT`, `DHDYB_DEBIT`, `DHRB_DEBIT`, `DLB_CREDIT`, `DLB_DEBIT`, `DLRCB_DEBIT`, `DRCB_CREDIT`, `DRCB_DEBIT`, `DSB_DEBIT`, `DTCCB_DEBIT`, `DYB_CREDIT`, `DYB_DEBIT`, `DYCCB_DEBIT`, `DYLSB_DEBIT`, `DZB_DEBIT`, `DZCCB_DEBIT`, `EDRB_DEBIT`, `ESUNB_DEBIT`, `FBB_DEBIT`, `FDB_CREDIT`, `FDB_DEBIT`, `FJHXB_CREDIT`, `FJHXB_DEBIT`, `FJNX_CREDIT`, `FJNX_DEBIT`, `FUXINB_CREDIT`, `FUXINB_DEBIT`

### 枚举定义

| 枚举 | 成员 |
|------|------|
| `BulletinType` | News, Activity, Information, Annoucement, Advertisement, Agreement |
| `BulletinStatus` | Draft, Reviewing, Revision, Published, Expired, Closed |
| `AlertTimeUnit` | Minute, Hour, Day |
| `AlertOperator` | GreaterThan, LessThan, EqualTo, GreaterThanOrEqualTo, LessThanOrEqualTo, NotEqualTo |
| `AlertField` | TotalTokens, TotalCost, ErrorCount, Latency, ErrorRate, InputTokens, OutputTokens, WarningCount, ObservationCount |
| `AlertRecordState` | Active, Read |
| `AlertNotifyBy` | System, SMS |
| `AuditAction` | Create, Update, Delete, Login, Logout, Reset, Bind, UnBind, Place, Query, Notify |
| `AuditResourceType` | User, Organization, Project, Alert, ApiKey, Invitation, Order, WeChat, OrgPrivilege |
| `WeChatMessageType` | None, Event, Text, Image, Voice, Video, Shortvideo, Location, Link |
| `WeChatMessageEvent` | Subscribe, Unsubscribe, Scan, Location, Click, View, MasssEndJobFinish |
| `WeChatSubscribeScene` | ADD_SCENE_SEARCH, ADD_SCENE_ACCOUNT_MIGRATION, ADD_SCENE_PROFILE_CARD, ADD_SCENE_QR_CODE, ADD_SCENE_PROFILE_LINK, ADD_SCENE_PROFILE_ITEM, ADD_SCENE_PAID, ADD_SCENE_WECHAT_ADVERTISEMENT, ADD_SCENE_REPRINT, ADD_SCENE_LIVESTREAM, ADD_SCENE_CHANNELS, ADD_SCENE_OTHERS |
| `WeChatTradeType` | JSAPI, NATIVE, APP, MICROPAY, MWEB, FACEPAY |
| `WeChatPromotionScope` | GLOBAL, SINGLE |
| `WeChatPromotionType` | CASH, NOCASH |
| `WeChatBankType` | ICBC_DEBIT, ICBC_CREDIT, ICBC_ECNY, ABC_DEBIT, ABC_CREDIT, ABC_ECNY, PSBC_CREDIT, PSBC_DEBIT, PSBC_ECNY, CCB_DEBIT, CCB_CREDIT, CCB_ECNY, CMB_DEBIT, CMB_CREDIT, CMB_ECNY, BOC_DEBIT, BOC_CREDIT, BOC_ECNY, COMM_DEBIT, COMM_CREDIT |
| `JobFrequency` | Minutely, Hourly, Daily, Weekly, Monthly, Yearly |
| `JobType` | Regularly, Once, Permanently |
| `JobCacheAction` | Load, Create, Ignore |
| `JobStatus` | Created, Running, Completed |
| `FilterType` | DateTime, String, Number, StringOptions, ArrayOptions, Boolean, Null |
| `FilterOperator` | GreaterThan, LessThan, GreaterThanOrEqualTo, LessThanOrEqualTo, EqualTo, Contains, DoesNotContain, StartsWith, EndsWith, AnyOf, NoneOf, AllOf, NotEqualTo, IsNull, IsNotNull |
| `FilterColumn` | Id, Name, Timestamp, UserId, SessionId, Environment, Version, Release, Tags, Bookmarked, Latency, InputTokens, OutputTokens, TotalTokens, Tokens, InputCost, OutputCost, TotalCost, Level, WarningCount |
| `TradeState` | SUCCESS, REFUND, NOTPAY, CLOSED, REVOKED, USERPAYING, PAYERROR, TRADE_CLOSED, TRADE_FINISHED, TRADE_SUCCESS, WAIT_BUYER_PAY |
| `SubPayMethod` | WECHAT_JSAPI, WECHAT_NATIVE, WECHAT_MINIPROGRAM, ALIPAY_FAST_INSTANT_TRADE_PAY |
| `OrderState` | Created, WaitForPay, Paid, Refunded, Cancelled, Closed, PayError |
| `ProductType` | None, Monthly, Permanent |
| `PayMethod` | WeChat, Alipay |
| `AgentType` | Assistant, Research |
| `AgentInsightSettingType` | WeChat, Alipay |
| `PGRole` | NONE, VIEWER, MEMBER, ADMIN, OWNER |
| `ApiKeyScope` | PROJECT, ORGANIZATION |
| `UserConfigType` | User, Organization, Project |
| `LoginType` | Password, SMS, WeChat, MiniProgram, APIKey |
| `ExceptionCodes` | UnAuthToken, EmptyUserId, ExistedMobile, CreateUserFailed, InvalidUser, EmptyMobile, UnauthorizedOperator, UserNameTooLong, EmptyInviteMobile, InvalidInviteMobile, CannotGrantHigherRole, UserAlreadyOrgMember, InviteAlreadyExists, CreateInviteFailed, InviteNotFound, DeleteInviteFailed, ApiKeyNotFound, CreateApiKeyFailed, DeleteApiKeyFailed, MissingProjectOrOrgId |
| `ExceptionCodes` | UnAuthToken, DefaultException |
| `TransactionType` | WeChatTransaction, AlipayTransaction |
| `RouteType` | None, Public, PublicApi |
| `SMSInstance` | None, Aliyun, TencentCloud |
| `QueueType` | Audit, ExceptionRecord, UsageTracking, PerformanceRecord |

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
- Admin

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

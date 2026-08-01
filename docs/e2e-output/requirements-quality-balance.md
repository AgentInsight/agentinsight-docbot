## 1. 引言

AgentInsightService 是一款面向 AI Agent 应用的可Observation性与分析平台，提供 Trace 数据采集、指标分析、Alert管理、用户与组织管理、Payment与订阅、Agent Config管理等功能。系统由 C# 后端 API（基于 Furion 框架）和 Python Agent Service（基于 FastAPI）组成，支持多租户组织/项目隔离。本文档是 AgentInsightService 的软件需求规格说明，旨在为开发、测试、运维及产品利益相关方提供完整、准确、可验证的需求基线。

### 1.1. 编写目的与目标读者

本文档的核心目的是建立 AgentInsightService 功能需求与非功能需求的统一基线，确保项目各方对系统行为、边界和约束条件有一致的理解。文档将作为以下工作的直接依据：

- **开发团队**：作为系统设计、编码实现和代码评审的参考基准，确保实现与需求一致。
- **测试团队**：作为测试用例设计、测试执行和缺陷跟踪的验收标准，确保测试覆盖完整。
- **运维团队**：作为部署架构、监控AlertConfig和故障排查的参考手册。
- **产品经理与项目经理**：作为需求评审、范围控制和进度估算的基础文档。
- **业务利益相关方**：作为理解产品能力、确认业务规则和评估交付成果的依据。

本文档面向的读者需具备一定的技术背景，熟悉 RESTful API、多租户架构、可ObservationObservability等基本概念。对于文档中涉及的代码标识符（如 `AgentInsightService`、`ExceptionCodes`、`AlertField` 等），均遵循代码仓库中的原始命名，不做翻译或改写。

### 1.2. 产品背景与业务痛点

随着 AI Agent 应用在各行业的快速落地，开发者和运维人员面临着一系列前所未有的可Observation性挑战。传统的 APM（应用性能监控）工具主要针对单体应用或微服务架构设计，无法有效应对 AI Agent 特有的调用链路、Token 消耗和成本分析需求。具体而言，市场存在以下核心痛点：

1. **Trace 数据碎片化**：AI Agent 的调用链涉及模型推理、工具调用、知识库检索等多个环节，缺乏统一的 Trace 采集与展示机制，导致问题定位困难。AgentInsightService 通过 `MetricsHandler` 提供 Trace 查询能力，支持过滤、排序和分页，帮助开发者Trace每一次 Agent 调用的完整链路 [API/Handlers/DataManagement/MetricsHandler.cs:17]。

2. **多租户隔离缺失**：企业级用户需要将不同团队、不同项目的Observation数据严格隔离，同时支持灵活的组织/项目Privilege管理。AgentInsightService 通过 `OrganizationHandler` 和 `ProjectHandler` 实现组织与项目的 CRUD 操作，并在 `ApiHandlerBase` 中统一进行组织/项目Privilege校验 [API/Handlers/UserManagement/OrganizationHandler.cs:12-15] [API/Handlers/ApiHandlerBase.cs:22-28]。

3. **AlertConfig复杂**：运维人员需要根据错误率、延迟等指标Config灵活的Alert规则，并在异常发生时及时收到通知。AgentInsightService 的 `AlertHandler` 支持Alert规则 CRUD、Alert记录查询与已读标记 [API/Handlers/UserManagement/AlertHandler.cs:12-16]，并通过 `AlertService` 进行Alert条件评估 [API/Common/Services/AlertService.cs:9]。

4. **商业化能力缺失**：作为 SaaS 平台，需要完整的订阅Payment闭环，包括产品定价、订单管理、微信/Payment宝Payment和Payment回调处理。AgentInsightService 通过 `OrderHandler` 实现订单创建与查询 [API/Handlers/PaymentManagement/OrderHandler.cs:12-15]，通过 `PaymentService` 集成微信Payment（JSAPI/Native/MiniProgram）和Payment宝Payment [API/Common/Services/PaymentService.cs:9]。

5. **Agent Config管理分散**：用户需要统一管理 Agent 的数据源连接、报告模板和Session历史。AgentInsightService 提供 `AgentConfigHandler`、`AgentReportHandler` 和 `AgentSessionHandler` 分别管理 Agent Config、报告模板和Session [API/Handlers/AgentManagement/AgentConfigHandler.cs:9] [API/Handlers/AgentManagement/AgentReportHandler.cs:9] [API/Handlers/AgentManagement/AgentSessionHandler.cs:9]。

AgentInsightService 的定位是成为 AI Agent 应用的可Observation性基础设施，通过提供开箱即用的 Trace 分析、Alert管理和商业化能力，帮助开发者和企业快速构建、监控和运营自己的 AI Agent 应用。

### 1.3. 文档范围

本文档覆盖 AgentInsightService 的核心功能需求与非功能需求，具体范围界定如下：

**In-Scope（本文档覆盖）**：

- **API Service（C#）**：基于 Furion 框架的 RESTful API Service，涵盖用户管理、Org/项目管理、数据指标查询、Alert管理、Payment与订阅、Agent Config管理、工具管理等模块。关键实现位于 `API/Handlers/` 目录下，包括 `UserHandler`、`OrganizationHandler`、`ProjectHandler`、`MetricsHandler`、`AlertHandler`、`OrderHandler`、`AgentConfigHandler` 等。
- **Agent Agent AgentPython**：基于 FastAPI 的 Agent Service，提供 OpenAI 兼容的 Chat Completions API、Session持久化、多 Agent 编排（Insight/Researcher/CustomService）SSE能力。核心实现位于 `Agents/server.py`。

**Out-of-Scope（本文档不覆盖）**：

- **Admin 管理后台**：基于 Django 的 Web 管理界面（`Admin/`），作为独立子项目，不作为 API 功能需求来源。
- **Entities/Models 类库**：纯数据定义层，不包含业务逻辑，仅在必要时引用其数据结构。
- **前端 Web 聊天界面**：`Agents/server.py` 中的 HTML 聊天 UI 属于 Agent 服务的辅助功能，不作为独立产品需求。
- **UnitTest 测试项目**：独立于产品功能的自动化测试工程，不作为功能需求来源。
- **Utility/Tools 工具项目**：辅助开发与运维的工具类项目，不作为产品功能需求来源。

### 1.4. 术语与缩略语

本文档使用以下术语与缩略语，其中代码标识符遵循仓库原始命名，不做翻译：

| 术语/缩略语 | 说明 |
|------------|------|
| AgentInsightService | 产品名称，面向 AI Agent 应用的可Observation性与分析平台 |
| AgentInsight | 产品品牌名，用于模块命名和常量前缀（如 `AgentInsightConst`） |
| Trace | 一次 AI Agent 调用的完整链路Trace数据，包括延迟、Token 消耗、成本等指标 |
| Observation | Observation数据，Agent 执行过程中的中间状态或事件记录 |
| Score | Score数据，对 Agent 输出质量的量化评价 |
| API Key | 用于 API 访问认证的密钥，支持创建、查询和删除 [API/Handlers/UserManagement/UserHandler.cs:42-44] |
| Org / Organization | Org，多租户隔离的顶级实体 |
| Project | Project，隶属于组织，是数据隔离和Privilege控制的基本单位 |
| PGRole | Org/项目角色枚举，包括 OWNER 等取值 |
| ExceptionCodes | 异常码枚举，定义系统所有错误码常量 [Models/Common/Enums/ExceptionCodes.cs:6] |
| AlertField | Alert字段枚举，定义可监控的指标字段 [Models/Common/Enums/AlertEnum.cs:20] |
| AlertOperator | Alert操作符枚举，定义条件比较操作符 [Models/Common/Enums/AlertEnum.cs:10] |
| AlertTimeUnit | Alert时间单位枚举 [Models/Common/Enums/AlertEnum.cs:3] |
| AlertRecordStatus | Alert记录状态枚举 [Models/Common/Enums/AlertEnum.cs:33] |
| AlertNotifyType | Alert通知方式枚举 [Models/Common/Enums/AlertEnum.cs:39] |
| SSE | Server-Sent Events，服务器推送事件，用于流式响应 |
| JWT | JSON Web Token，用于用户身份认证 |
| SaaS | Software as a Service，软件即服务 |

### 1.5. 参考文档

本文档的编写参考了以下代码仓库中的关键文件：

| 参考文档 | 说明 |
|---------|------|
| `API/Handlers/UserManagement/UserHandler.cs` | 用户管理核心逻辑，包括注册/登录/微信绑定/成员邀请/角色分配/API Key 管理/月度用量扣减 |
| `API/Handlers/UserManagement/OrganizationHandler.cs` | 组织管理核心逻辑，包括组织 CRUD |
| `API/Handlers/UserManagement/ProjectHandler.cs` | 项目管理核心逻辑，包括项目 CRUD |
| `API/Handlers/DataManagement/MetricsHandler.cs` | 数据指标查询核心逻辑，包括 Trace/Observation/Score 查询 |
| `API/Handlers/UserManagement/AlertHandler.cs` | Alert管理核心逻辑，包括Alert规则 CRUD、Alert记录查询与已读标记 |
| `API/Handlers/PaymentManagement/OrderHandler.cs` | 订单业务处理，包括下单、查询、产品转换计算 |
| `API/Common/Services/PaymentService.cs` | Payment核心逻辑，包括订单创建、微信/Payment宝Payment、签名验证、订单状态更新 |
| `API/Common/Services/WeChatService.cs` | 微信服务，包括 Access Token 管理、微信登录、公众号消息签名验证 |
| `API/System/Handlers/AgentInsightTransformProvider.cs` | API 认证与限流，包括 Basic Auth/JWT 认证、API Key 验证、速率限制 |
| `Agents/server.py` | Python Agent Service，包括 OpenAI 兼容 API、Session管理、多 Agent 编排 |
| `Models/Common/Enums/ExceptionCodes.cs` | 异常码枚举定义 |
| `Models/Common/Enums/AlertEnum.cs` | Alert相关枚举定义 |

### 1.6. 版本历史

| 版本 | 日期 | 作者 | 修订说明 |
|------|------|------|---------|
| v1.0 | 待定 | 技术文档组 | 初始版本，基于代码仓库 v9 元数据与 AST 扫描结果完成需求基线定义 |

---

## 2. 产品概述与用户分析

### 2.1. 产品定位

AgentInsightService 是面向 AI Agent 应用的可Observation性与分析平台，提供 Trace 数据采集、指标分析、Alert管理、用户与组织管理、Payment与订阅、Agent Config管理等功能。系统由 C# 后端 API（Furion 框架）和 Python Agent Service（FastAPI）组成，支持多租户组织/项目隔离。平台通过 AgentInsightTransformProvider 负责 Basic Auth/JWT 认证、API Key 验证与速率限制 [API/System/Handlers/AgentInsightTransformProvider.cs:9]。

平台采用多租户架构，Org为租户隔离边界，Project，项目之间数据完全隔离。产品支持月度订阅与永久授权两种商业模式，ProductProductDuration的组合实现灵活定价 [API/Controllers/ProductManagement/ProductController.cs]。产品类型枚举定义于 PaymentEnums.cs，MonthlyPermanent两种类型，projectlimit、headcountlimit、orglimit与 Agent agentlimit等。

### 2.2. 价值主张

AgentInsightService 的核心价值主张是：帮助 AI 应用开发者与运维人员实时监控 Agent 行为、性能与成本，及时获知异常并优化。具体体现在以下四个维度：

**1. 全链路可Observation性**：平台提供 Trace 数据采集与查询能力，开发者可以查看 AI Agent 调用的完整链路数据，包括延迟、Token 消耗、成本等关键指标 [API/Handlers/DataManagement/MetricsHandler.cs:14]。Trace 查询支持按时间范围、Project ID、过滤条件进行筛选，并支持排序与分页 [API/Handlers/DataManagement/MetricsHandler.cs:17]。数据存储基于 ClickHouse 列式数据库，通过 ClickHouseClient 提供高性能查询能力 [API/Handlers/DataManagement/MetricsHandler.cs:14]。

**2. 精细化成本核算**：平台支持模型级别的价格定义与成本计算。通过 ModelController 提供的模型管理接口，开发者可以为不同模型Configinputprice、outputprice、totalpriceunit，pricingtiers[API/Controllers/DataManagement/ModelController.cs]。月度 Agent 用量扣减与校验逻辑在 UserHandler 中实现 [API/Handlers/UserManagement/UserHandler.cs:38-39]，确保用量统计准确可靠。

**3. 实时Alert与异常感知**：平台提供灵活的Alert规则Config能力，开发者可以针对关键指标（如延迟、错误率、Token 消耗）设置Alert阈值，系统在条件满足时自动触发Alert通知。AlertHandler 负责Alert规则的 CRUD、Alert记录查询与已读标记 [API/Handlers/UserManagement/AlertHandler.cs:15]，用户可查看并标记Alert记录已读。

**4. 多租户与商业化能力**：平台内置完整的组织与成员管理、API Key 管理与Payment订阅能力。普通用户可注册/登录、绑定微信、创建/加入组织、查看数据指标 [API/Handlers/UserManagement/UserHandler.cs:15]；组织管理员可管理成员与项目；系统管理员可管理Bulletin、Agent Config模板与产品定价 [API/Handlers/ToolsManagement/BulletinHandler.cs:9]。Payment流程通过 PaymentService 实现，支持微信/Payment宝Payment、签名验证与订单状态更新 [API/Common/Services/PaymentService.cs]。

### 2.3. 北极星指标

北极星指标是衡量产品长期价值与增长的核心度量，AgentInsightService 的北极星指标体系包含以下三个关键指标：

| 指标名称 | 定义 | 业务意义 | 数据来源 |
|---------|------|---------|---------|
| 月度活跃项目数 | 每月至少上报一次 Trace 数据的活跃项目数量 | 衡量产品的核心使用粘性与健康度 | MetricsHandler Trace 上报记录 |
| 日均 Trace 处理量 | 平台每日处理的 Trace 数据条数 | 衡量平台的数据处理能力与规模增长 | ClickHouse Trace 存储 |
| Alert规则创建数 | 用户累计创建的Alert规则总数 | 衡量用户对平台监控能力的深度使用 | AlertHandler Alert规则表 |

其中，**月度活跃项目数**是首要北极星指标。原因在于：项目是平台数据隔离与Privilege管理的基本单元，活跃项目数直接反映了真实用户（开发者/团队）对平台的持续使用情况，避免了仅注册不使用的"僵尸用户"干扰。该指标与 Trace 上报量强相关——只有当开发者完成 Agent SDK 集成并持续上报 Trace 数据时，项目才被计为活跃。

**日均 Trace 处理量**作为辅助北极星指标，衡量平台的数据规模增长。该指标与 ClickHouse 存储层的处理能力直接相关，Config规格中设置了写入并发数、查询并发数、批量写入大小与缓存容量等参数，确保高吞吐写入与查询性能。

**Alert规则创建数**反映用户从"观察"到"主动管理"的行为升级。当用户创建Alert规则时，说明其已从被动查看数据转向主动监控异常，这是产品价值深化的关键信号。AlertHandler 提供Alert规则的完整 CRUD 能力 [API/Handlers/UserManagement/AlertHandler.cs:15]，支持用户针对关键指标设置阈值Alert。

### 2.4. Persona 矩阵

AgentInsightService 面向四类核心用户角色，每类角色拥有不同的Privilege范围与使用场景：

| Persona | 角色定义 | 核心需求 | 关键Privilege | 对应代码实现 |
|---------|---------|---------|---------|-------------|
| User | 注册并使用平台的开发者 | 注册/登录、绑定微信、查看数据指标 | 创建/加入组织、查看被授权项目的数据 | UserHandler 用户注册/登录/微信绑定 [API/Handlers/UserManagement/UserHandler.cs:15] |
| 组织管理员（Org Admin） | 管理组织与成员的用户 | 管理组织信息、邀请/移除成员、分配角色 | 组织级管理Privilege、成员角色分配 | OrganizationHandler Org/成员管理 [API/Handlers/UserManagement/OrganizationHandler.cs:9] |
| 项目管理员（Project Admin） | 管理特定项目的用户 | ConfigAlert规则、管理项目、查看 Trace 数据 | 项目级管理Privilege、Alert规则Config | ProjectHandler Project/Alert管理 [API/Handlers/UserManagement/ProjectHandler.cs:9] |
| 系统管理员（System Admin） | 平台运营与维护人员 | 管理Bulletin、Agent Config模板、产品定价 | 全局管理Privilege | BulletinHandler Bulletin/模板/产品管理 [API/Handlers/ToolsManagement/BulletinHandler.cs:9] |

**普通用户**是平台的基础用户群体，通常为 AI 应用开发者。其核心使用路径为：注册账号 → 创建或加入组织 → 创建项目 → 集成 Agent SDK 上报 Trace → 查看指标数据。UserService 接口定义了用户管理的核心能力，包括 GetUserByUserId、CreateNewUser、LogUserSession 等方法 [API/Common/Services/IUserService.cs]。

**组织管理员**在普通用户基础上增加了组织管理职责，包括成员邀请、角色分配与组织信息维护。组织是平台多租户隔离的基本单位，组织管理员通过 OrganizationHandler 管理组织信息与成员关系 [API/Handlers/UserManagement/OrganizationHandler.cs:9]。IUserService 中定义了 GetOrgPrivilegeAsync 与 UpdateOrgPrivilegeAsync 方法，用于获取与更新组织Privilege [API/Common/Services/IUserService.cs]。

**项目管理员**聚焦于项目级的管理与监控，核心职责包括：ConfigAlert规则、查看项目下的 Trace 数据、管理项目成员。项目是数据隔离的最小单元，项目管理员通过 MetricsHandler 查询项目下的 Trace 数据 [API/Handlers/DataManagement/MetricsHandler.cs:17]，并通过 AlertHandler ConfigAlert规则 [API/Handlers/UserManagement/AlertHandler.cs:15]。

**系统管理员**负责平台的运营与维护，包括发布Bulletin、管理 Agent Config模板、设定产品定价。系统管理员通过 BulletinHandler 管理Bulletin与模板 [API/Handlers/ToolsManagement/BulletinHandler.cs:9]，通过 ProductController 管理产品与时长定义 [API/Controllers/ProductManagement/ProductController.cs]。Admin 后台提供订单管理界面，支持按订单号、交易号、User ID 或组织 ID 搜索订单 [Admin/app/admin.py]。

### 2.5. 用户旅程

用户旅程描述了不同类型用户从首次接触到深度使用的完整路径。AgentInsightService 的用户旅程主要分为三条主线：开发者使用旅程、购买者付费旅程、管理员运营旅程。

#### 2.5.1. 开发者使用旅程

开发者是平台的核心用户，其完整旅程如下：

1. **注册与登录**：开发者通过手机号或微信扫码完成注册登录。系统通过 UserHandler 处理注册/登录逻辑，支持微信绑定 [API/Handlers/UserManagement/UserHandler.cs:15]。注册成功后，用户获得默认的 API Key 用于后续数据上报。

2. **创建组织与项目**：开发者创建组织（或加入已有组织），在组织下创建项目。组织是租户隔离边界，项目是数据隔离的最小单元。多租户架构确保不同组织/项目之间的数据完全隔离。

3. **集成 Agent SDK 上报 Trace**：开发者获取项目专属的 API Key，在 AI Agent 应用中集成 agentinsight-sdk，通过 SDK 上报 Trace 数据。API Key 认证由 AgentInsightTransformProvider 实现，使用有效 API Key 可访问受保护接口，无效 Key 返回 InvalidApiKey 错误 [API/System/Handlers/AgentInsightTransformProvider.cs:9]。

4. **查看指标与 Trace 数据**：开发者通过 MetricsHandler 查询 Trace 数据，支持按时间范围、Project ID、过滤条件筛选，并支持排序与分页 [API/Handlers/DataManagement/MetricsHandler.cs:17]。指标数据包括延迟、Token 消耗、成本等关键维度 [API/Handlers/DataManagement/MetricsHandler.cs:14]。

5. **设置Alert规则**：开发者针对关键指标（如延迟超过阈值、Token 消耗异常增长）创建Alert规则。AlertHandler 提供Alert规则的 CRUD 能力 [API/Handlers/UserManagement/AlertHandler.cs:15]，用户可查看并标记Alert记录已读。

#### 2.5.2. 购买者付费旅程

购买者（通常为组织管理员或项目管理员）的付费旅程如下：

1. **浏览产品与定价**：购买者通过 ProductController 查看产品列表与时长选项 [API/Controllers/ProductManagement/ProductController.cs]。price、monthlyrate、permanentrate、projectlimit、headcountlimit等属性。

2. **选择产品并下单**：购买者选择产品与时长组合，通过 OrderHandler 创建订单 [API/Handlers/PaymentManagement/OrderHandler.cs:9]。订单包含产品信息、金额信息、交易状态等字段 [Admin/app/admin.py]。

3. **微信/Payment宝Payment**：购买者通过 PaymentService 完成Payment，支持微信/Payment宝Payment、签名验证与订单状态更新 [API/Common/Services/PaymentService.cs]。Payment完成后，系统自动更新订单状态并触发组织Privilege升级。

4. **组织Privilege升级**：Payment成功后，组织的产品Privilege自动升级，包括项目数限制、成员数限制、Agent 数限制等配额同步更新。月度 Agent 用量扣减与校验在 UserHandler 中实现 [API/Handlers/UserManagement/UserHandler.cs:38-39]。

#### 2.5.3. 管理员运营旅程

系统管理员的运营旅程如下：

1. **发布Bulletin**：系统管理员通过 BulletinHandler 发布平台Bulletin，通知用户产品更新、维护计划等信息 [API/Handlers/ToolsManagement/BulletinHandler.cs:9]。

2. **管理 Agent Config模板**：系统管理员维护 Agent Config模板，供普通用户创建 Agent Config时引用。AgentConfigController 提供Config的获取、创建/更新与删除接口 [API/Controllers/AgentManagement/AgentConfigController.cs]。AgentReportController 提供报表模板的列表、详情、创建/更新与删除接口 [API/Controllers/AgentManagement/AgentReportController.cs]。

3. **管理产品定价**：系统管理员通过 ProductController 管理产品定义与时长选项，调整价格与配额 [API/Controllers/ProductManagement/ProductController.cs]。Admin 后台提供订单管理界面，支持按订单号、交易号、User ID 或组织 ID 搜索订单，并可查看订单的完整信息 [Admin/app/admin.py]。

4. **监控平台运行**：系统管理员通过 Admin 后台监控订单状态、用户增长与平台健康度。tradestate、orderstate、Paymentpaymethod等维度筛选 [Admin/app/admin.py]。

---

## 3. 功能需求

AgentInsightService 是面向 AI Agent 应用的可Observation性与分析平台，提供 Trace 数据采集、指标分析、Alert管理、用户与组织管理、Payment与订阅、Agent Config管理等功能。系统由 C# 后端 API（Furion 框架）和 Python Agent Service（FastAPI）组成，支持多租户组织/项目隔离。本系统共 80 个功能需求（FR-001 至 FR-080），每个 REST 端点对应一个 FR，编号连续，覆盖用户、Org、数据指标、Alert、Payment、Agent、工具、产品及Agent Agent服务九大功能域。

### 3.1. 用户管理功能

用户管理功能域覆盖 FR-001 至 FR-016，包含注册/登录/登出、微信绑定、成员邀请、角色分配、API Key 管理、Captcha服务、用户Config等端点，由 `API/Handlers/UserManagement/UserHandler.cs` 统一承载核心业务逻辑。

#### 3.1.1. FR-001 用户注册 [优先级: Must]

- **用户故事**: 作为访客，我希望通过手机号和Captcha注册账号，以便使用 AgentInsightService 平台服务。
- **主流程**:
  1. 用户提交手机号与短信Captcha，请求注册端点 [API/Handlers/UserManagement/UserHandler.cs:24]
  2. 系统校验Captcha有效性，验证通过后创建用户记录
  3. 系统返回用户 ID 与认证凭证
- **验收标准**:
  - [ ] AC1: 注册成功时返回 `errorCode=0` 且响应包含 `userId` 字段
  - [ ] AC2: Captcha错误时返回 ``（620008）对应错误
  - [ ] AC3: 手机号已注册时返回明确错误提示
- **业务规则**:
  - BR-001: Captcha有效期由 `CaptchaSetting. = 300`（秒）控制
  - BR-002: 短信Captcha长度由 `CaptchaSetting. = 6` 控制

#### 3.1.2. FR-002 用户登录 [优先级: Must]

- **用户故事**: 作为注册用户，我希望通过手机号和密码登录，以便访问我的项目和数据。
- **主流程**:
  1. 用户提交手机号与密码，请求登录端点 [API/Handlers/UserManagement/UserHandler.cs:25]
  2. 系统校验密码哈希，验证通过后生成 JWT Token
  3. 系统返回Token与用户基本信息
- **验收标准**:
  - [ ] AC1: 登录成功时返回 `errorCode=0` 且响应包含 `token` 字段
  - [ ] AC2: 密码错误时返回认证失败错误码
- **业务规则**:
  - BR-002: 连续多次登录失败应触发安全锁定策略

#### 3.1.3. FR-003 用户登出 [优先级: Should]

- **用户故事**: 作为登录用户，我希望安全登出，以保护账号安全。
- **主流程**:
  1. 用户携带Token请求登出端点 [API/Handlers/UserManagement/UserHandler.cs:26]
  2. 系统使当前Token失效
- **验收标准**:
  - [ ] AC1: 登出成功返回 `errorCode=0`
  - [ ] AC2: 登出后原Token无法继续访问受保护资源

#### 3.1.4. FR-004 微信小程序登录 [优先级: Should]

- **用户故事**: 作为用户，我希望通过微信小程序授权登录，以便快速访问系统。
- **主流程**:
  1. 用户通过微信小程序发起授权，系统接收微信授权码 [API/Common/Services/WeChatService.cs:15]
  2. 系统调用微信 API 换取用户 
  3. 系统根据  查找或创建用户，返回认证Token
- **验收标准**:
  - [ ] AC1: 微信授权码无效时返回 ``（620008）
  - [ ] AC2: 登录成功返回 `errorCode=0` 且包含 `token` 字段
- **业务规则**:
  - BR-003: 微信 Access Token 管理由 `WeChatService` 统一处理

#### 3.1.5. FR-005 微信账号绑定 [优先级: Should]

- **用户故事**: 作为已登录用户，我希望绑定微信账号，以便后续通过微信快速登录。
- **主流程**:
  1. 用户提交微信授权码，请求绑定端点 [API/Handlers/UserManagement/UserHandler.cs:28]
  2. 系统校验微信账号未被其他用户绑定
  3. 系统将微信  关联到当前用户
- **验收标准**:
  - [ ] AC1: 绑定成功返回 `errorCode=0`
  - [ ] AC2: 微信账号已被绑定返回 ``（620009）
  - [ ] AC3: 微信账号已被其他用户绑定返回 ``（620010）

#### 3.1.6. FR-006 微信账号解绑 [优先级: Could]

- **用户故事**: 作为已绑定微信的用户，我希望解绑微信账号，以便更换绑定。
- **主流程**:
  1. 用户请求解绑端点 [API/Handlers/UserManagement/UserHandler.cs:30]
  2. 系统解除当前用户与微信  的关联
- **验收标准**:
  - [ ] AC1: 解绑成功返回 `errorCode=0`
  - [ ] AC2: 未绑定微信时返回 ``（620011）

#### 3.1.7. FR-007 密码重置 [优先级: Should]

- **用户故事**: 作为忘记密码的用户，我希望通过Captcha重置密码，以便恢复账号访问。
- **主流程**:
  1. 用户提交手机号、Captcha与新密码 [API/Handlers/UserManagement/UserHandler.cs:31]
  2. 系统校验Captcha后更新密码哈希
- **验收标准**:
  - [ ] AC1: 重置成功返回 `errorCode=0`
  - [ ] AC2: Captcha错误时返回对应错误码

#### 3.1.8. FR-008 成员邀请 [优先级: Must]

- **用户故事**: 作为组织管理员，我希望邀请成员加入组织，以便协作管理项目。
- **主流程**:
  1. 管理员提交被邀请人手机号与目标组织 [API/Handlers/UserManagement/UserHandler.cs:32]
  2. 系统创建邀请记录并发送通知
  3. 被邀请人接受邀请后加入组织
- **验收标准**:
  - [ ] AC1: 邀请成功返回 `errorCode=0`
  - [ ] AC2: 被邀请人接受邀请后可在组织成员列表中查询到
- **业务规则**:
  - BR-004: 仅组织管理员或所有者可发起成员邀请

#### 3.1.9. FR-009 成员列表查询 [优先级: Must]

- **用户故事**: 作为组织管理员，我希望查看组织成员列表，以便管理团队。
- **主流程**:
  1. 管理员请求成员列表端点 [API/Handlers/UserManagement/UserHandler.cs:33]
  2. 系统返回组织内所有成员及其角色
- **验收标准**:
  - [ ] AC1: 返回 `errorCode=0` 且响应包含 `members` 数组
  - [ ] AC2: 每个成员项包含 `userId`、`role` 字段

#### 3.1.10. FR-010 成员移除 [优先级: Should]

- **用户故事**: 作为组织管理员，我希望移除组织成员，以控制组织访问Privilege。
- **主流程**:
  1. 管理员提交目标成员 ID [API/Handlers/UserManagement/UserHandler.cs:34]
  2. 系统校验目标成员非组织所有者
  3. 系统移除该成员的组织关联
- **验收标准**:
  - [ ] AC1: 移除成功返回 `errorCode=0`
  - [ ] AC2: 尝试移除所有者时返回 ``（100039）

#### 3.1.11. FR-011 组织角色分配 [优先级: Must]

- **用户故事**: 作为组织所有者，我希望为成员分配角色，以便区分管理Privilege。
- **主流程**:
  1. 所有者提交成员 ID 与目标角色 [API/Handlers/UserManagement/UserHandler.cs:35]
  2. 系统校验操作者Privilege
  3. 系统更新成员角色
- **验收标准**:
  - [ ] AC1: 分配成功返回 `errorCode=0`
  - [ ] AC2: 所有者不能修改自身角色，返回 ``（100039）

#### 3.1.12. FR-012 项目角色分配 [优先级: Should]

- **用户故事**: 作为项目管理员，我希望为项目成员分配角色，以便管理项目Privilege。
- **主流程**:
  1. 项目管理员提交成员 ID 与项目角色 [API/Handlers/UserManagement/UserHandler.cs:37]
  2. 系统校验操作者具备项目管理员Privilege
  3. 系统更新项目成员角色
- **验收标准**:
  - [ ] AC1: 分配成功返回 `errorCode=0`
  - [ ] AC2: Privilege不足时返回 403 错误

#### 3.1.13. FR-013 API Key 创建 [优先级: Must]

- **用户故事**: 作为开发者，我希望创建 API Key，以便通过 API 方式访问 Trace 数据。
- **主流程**:
  1. 用户提交 API Key 名称与作用域 [API/Handlers/UserManagement/UserHandler.cs:42]
  2. 系统生成密钥对并加密存储
  3. 系统返回 API Key ID 与 Secret（仅展示一次）
- **验收标准**:
  - [ ] AC1: 创建成功返回 `errorCode=0` 且包含 `apiKeyId` 与 `secret` 字段
  - [ ] AC2: 创建失败返回 ``（100032）
- **业务规则**:
  - BR-005: API Key 作用域由 `ApiKeyScope` 枚举定义，支持 `APIKey`（5）等类型 [Models/Common/Enums/UserEnum.cs:12]

#### 3.1.14. FR-014 API Key 查询 [优先级: Should]

- **用户故事**: 作为开发者，我希望查询已创建的 API Key 列表，以便管理密钥。
- **主流程**:
  1. 用户请求 API Key 列表端点 [API/Handlers/UserManagement/UserHandler.cs:43]
  2. 系统返回当前用户所有 API Key 元数据（不含 Secret）
- **验收标准**:
  - [ ] AC1: 返回 `errorCode=0` 且包含 `apiKeys` 数组
  - [ ] AC2: 响应中不包含 `secret` 字段

#### 3.1.15. FR-015 API Key 删除 [优先级: Should]

- **用户故事**: 作为开发者，我希望删除不再使用的 API Key，以降低安全风险。
- **主流程**:
  1. 用户提交 API Key ID [API/Handlers/UserManagement/UserHandler.cs:44]
  2. 系统删除对应密钥记录
- **验收标准**:
  - [ ] AC1: 删除成功返回 `errorCode=0`
  - [ ] AC2: 删除失败返回 ``（100033）

#### 3.1.16. FR-016 Captcha服务 [优先级: Must]

- **用户故事**: 作为用户，我希望获取图形/短信/邮箱Captcha，以便完成注册、登录或密码重置。
- **主流程**:
  1. 用户请求Captcha发送端点 [API/Handlers/UserManagement/CaptchaHandler.cs:9]
  2. 系统生成Captcha并发送至用户手机或邮箱
  3. 系统记录Captcha哈希与过期时间
- **验收标准**:
  - [ ] AC1: 发送成功返回 `errorCode=0`
  - [ ] AC2: 图形Captcha长度为 5（`CaptchaSetting. = 5`）
  - [ ] AC3: 短信/邮箱Captcha长度为 6（`CaptchaSetting. = 6` / ` = 6`）
- **业务规则**:
  - BR-006: Captcha有效期 300 秒（`CaptchaSetting. = 300`）
  - BR-007: 重发间隔 60 秒（`CaptchaSetting. = 60`）

### 3.2. 组织与项目管理功能

组织与项目管理功能域覆盖 FR-017 至 FR-028，包含组织 CRUD、Project CRUD、Privilege校验、月度用量扣减等端点，由 `API/Handlers/UserManagement/OrganizationHandler.cs` 与 `API/Handlers/UserManagement/ProjectHandler.cs` 承载。

#### 3.2.1. FR-017 创建组织 [优先级: Must]

- **用户故事**: 作为用户，我希望创建组织，以便与团队成员共享项目和数据。
- **主流程**:
  1. 用户提交组织名称与描述 [API/Handlers/UserManagement/OrganizationHandler.cs:12]
  2. 系统创建组织记录并将创建者设为组织所有者
- **验收标准**:
  - [ ] AC1: 创建成功返回 `errorCode=0` 且包含 `organizationId` 字段
  - [ ] AC2: 创建者自动成为组织所有者角色

#### 3.2.2. FR-018 查询组织列表 [优先级: Must]

- **用户故事**: 作为用户，我希望查看我所属的组织列表，以便切换工作空间。
- **主流程**:
  1. 用户请求组织列表端点 [API/Handlers/UserManagement/OrganizationHandler.cs:13]
  2. 系统返回当前用户所属全部组织
- **验收标准**:
  - [ ] AC1: 返回 `errorCode=0` 且包含 `organizations` 数组
  - [ ] AC2: 每个组织项包含 `id`、`name`、`role` 字段

#### 3.2.3. FR-019 更新组织信息 [优先级: Should]

- **用户故事**: 作为组织管理员，我希望更新组织信息，以保持组织资料准确。
- **主流程**:
  1. 管理员提交组织 ID 与更新内容 [API/Handlers/UserManagement/OrganizationHandler.cs:14]
  2. 系统校验操作者具备组织管理Privilege
  3. 系统更新组织记录
- **验收标准**:
  - [ ] AC1: 更新成功返回 `errorCode=0`
  - [ ] AC2: 非管理员操作返回 403 错误

#### 3.2.4. FR-020 删除组织 [优先级: Should]

- **用户故事**: 作为组织所有者，我希望删除组织，以便解散不再使用的团队。
- **主流程**:
  1. 所有者提交组织 ID [API/Handlers/UserManagement/OrganizationHandler.cs:15]
  2. 系统校验操作者为组织所有者
  3. 系统删除组织及其关联数据
- **验收标准**:
  - [ ] AC1: 删除成功返回 `errorCode=0`
  - [ ] AC2: 非所有者操作返回 403 错误

#### 3.2.5. FR-021 创建项目 [优先级: Must]

- **用户故事**: 作为组织成员，我希望在组织下创建项目，以便隔离不同应用的Observation数据。
- **主流程**:
  1. 用户提交组织 ID 与项目名称 [API/Handlers/UserManagement/ProjectHandler.cs:12]
  2. 系统校验用户属于该组织
  3. 系统创建项目记录
- **验收标准**:
  - [ ] AC1: 创建成功返回 `errorCode=0` 且包含 `projectId` 字段
  - [ ] AC2: 用户不属于该组织时返回 403 错误

#### 3.2.6. FR-022 查询项目列表 [优先级: Must]

- **用户故事**: 作为组织成员，我希望查看组织下项目列表，以便选择要查看的数据。
- **主流程**:
  1. 用户提交组织 ID，请求项目列表 [API/Handlers/UserManagement/ProjectHandler.cs:13]
  2. 系统返回该组织下当前用户可访问的项目
- **验收标准**:
  - [ ] AC1: 返回 `errorCode=0` 且包含 `projects` 数组
  - [ ] AC2: 每个项目项包含 `id`、`name`、`createdAt` 字段

#### 3.2.7. FR-023 更新项目信息 [优先级: Should]

- **用户故事**: 作为项目管理员，我希望更新项目信息，以反映项目变化。
- **主流程**:
  1. 管理员提交项目 ID 与更新内容 [API/Handlers/UserManagement/ProjectHandler.cs:14]
  2. 系统校验操作者具备项目管理员Privilege
  3. 系统更新项目记录
- **验收标准**:
  - [ ] AC1: 更新成功返回 `errorCode=0`
  - [ ] AC2: 非项目管理员操作返回 403 错误

#### 3.2.8. FR-024 删除项目 [优先级: Should]

- **用户故事**: 作为项目管理员，我希望删除项目，以清理不再维护的应用数据。
- **主流程**:
  1. 管理员提交项目 ID [API/Handlers/UserManagement/ProjectHandler.cs:15]
  2. 系统校验操作者Privilege
  3. 系统异步删除项目及关联 Trace 数据
- **验收标准**:
  - [ ] AC1: 删除成功返回 `errorCode=0`
  - [ ] AC2: 关联数据通过消息队列异步清理

#### 3.2.9. FR-025 组织Privilege校验 [优先级: Must]

- **用户故事**: 作为系统，我希望在每次组织级操作前校验用户Privilege，以保障数据安全。
- **主流程**:
  1. 请求进入组织级端点 [API/Handlers/ApiHandlerBase.cs:22]
  2. 系统从Token解析用户 ID 与组织 ID
  3. 系统校验用户属于该组织且角色满足要求
- **验收标准**:
  - [ ] AC1: 校验通过时请求继续执行
  - [ ] AC2: 校验失败返回 403 错误

#### 3.2.10. FR-026 项目Privilege校验 [优先级: Must]

- **用户故事**: 作为系统，我希望在每次项目级操作前校验用户Privilege，以保障项目数据隔离。
- **主流程**:
  1. 请求进入项目级端点 [API/Handlers/ApiHandlerBase.cs:28]
  2. 系统校验用户对该项目具备访问Privilege
- **验收标准**:
  - [ ] AC1: 校验通过时请求继续执行
  - [ ] AC2: 校验失败返回 403 错误

#### 3.2.11. FR-027 月度用量扣减 [优先级: Must]

- **用户故事**: 作为系统，我希望在用户调用 Agent 服务时扣减月度用量，以执行订阅配额控制。
- **主流程**:
  1. 用户发起 Agent 调用请求 [API/Handlers/UserManagement/UserHandler.cs:38]
  2. 系统校验用户当月剩余配额
  3. 系统扣减对应用量并更新配额
- **验收标准**:
  - [ ] AC1: 配额充足时请求继续执行
  - [ ] AC2: 配额不足时返回 ``（150007）

#### 3.2.12. FR-028 月度用量校验 [优先级: Must]

- **用户故事**: 作为系统，我希望在扣减前校验用户月度用量，以避免超额使用。
- **主流程**:
  1. 系统读取用户当月累计用量 [API/Handlers/UserManagement/UserHandler.cs:39]
  2. 系统对比订阅配额上限
- **验收标准**:
  - [ ] AC1: 用量未超限时返回 `errorCode=0`
  - [ ] AC2: 用量超限时返回 ``（150007）

### 3.3. 数据指标与可Observation性功能

数据指标与可Observation性功能域覆盖 FR-029 至 FR-034，包含 Trace 查询（GET/POST）、Observation 查询、Score 查询、模型定义查询等端点，由 `API/Handlers/DataManagement/MetricsHandler.cs` 与 `API/Handlers/DataManagement/ModelHandler.cs` 承载。

#### 3.3.1. FR-029 Trace GET [优先级: Must]

- **用户故事**: 作为开发者，我希望通过 GET 请求查询 Trace 数据，以便快速定位性能问题。
- **主流程**:
  1. 用户提交项目 ID 与过滤条件 [API/Handlers/DataManagement/MetricsHandler.cs:17]
  2. 系统通过 `ClickHouseClient` 查询 Trace 数据 [API/Handlers/DataManagement/MetricsHandler.cs:14]
  3. 系统返回匹配的 Trace 列表（含分页）
- **验收标准**:
  - [ ] AC1: 返回 `errorCode=0` 且包含 `traces` 数组
  - [ ] AC2: 支持按时间范围、延迟、Token 消耗等条件过滤
  - [ ] AC3: 响应包含 `totalCount` 分页信息
- **业务规则**:
  - BR-008: Trace 数据存储在 ClickHouse，连接串由 `.` Config

#### 3.3.2. FR-030 Trace POST [优先级: Must]

- **用户故事**: 作为开发者，我希望通过 POST 请求提交复杂查询条件查询 Trace，以便进行深度分析。
- **主流程**:
  1. 用户提交复杂查询条件 JSON [API/Handlers/DataManagement/MetricsHandler.cs:17]
  2. 系统解析查询条件并执行查询
  3. 系统返回匹配的 Trace 数据
- **验收标准**:
  - [ ] AC1: 返回 `errorCode=0` 且包含 `traces` 数组
  - [ ] AC2: 支持多条件组合过滤与排序

系统返回匹配的 Trace 数据
- **验收标准**:
  - [ ] AC1: 返回 `errorCode=0` 且包含 `traces` 数组
  - [ ] AC2: 支持多条件组合过滤与排序

#### 3.3.3. FR-031 Observation 查询 [优先级: Must]

- **用户故事**: 作为开发者，我希望查询 Observation 数据，以便查看 Agent 内部步骤的详细执行信息。
- **主流程**:
  1. 用户提交 Trace ID 与过滤条件 [API/Handlers/DataManagement/MetricsHandler.cs:15]
  2. 系统查询该 Trace 下的所有 Observation
- **验收标准**:
  - [ ] AC1: 返回 `errorCode=0` 且包含 `observations` 数组
  - [ ] AC2: 每个 Observation 包含 `type`、`input`、`output` 字段

#### 3.3.4. FR-032 Score 查询 [优先级: Should]

- **用户故事**: 作为开发者，我希望查询 Score 数据，以便评估 Agent 输出质量。
- **主流程**:
  1. 用户提交 Trace ID 与Score类型 [API/Handlers/DataManagement/MetricsHandler.cs:16]
  2. 系统查询关联的Score记录
- **验收标准**:
  - [ ] AC1: 返回 `errorCode=0` 且包含 `scores` 数组
  - [ ] AC2: 每个 Score 包含 `name`、`value`、`timestamp` 字段

#### 3.3.5. FR-033 模型定义查询 [优先级: Should]

- **用户故事**: 作为开发者，我希望查询模型定义列表，以便了解可用模型及其参数。
- **主流程**:
  1. 用户请求模型定义列表 [API/Handlers/DataManagement/ModelHandler.cs:12]
  2. 系统返回所有可用模型定义
- **验收标准**:
  - [ ] AC1: 返回 `errorCode=0` 且包含 `models` 数组
  - [ ] AC2: 每个模型包含 `id`、`name`、`provider` 字段

#### 3.3.6. FR-034 Alert指标查询 [优先级: Should]

- **用户故事**: 作为运维人员，我希望查询Alert相关指标，以便了解系统健康状态。
- **主流程**:
  1. 用户提交项目 ID 与时间范围 [API/Handlers/DataManagement/AlertMetricsHandler.cs:9]
  2. 系统聚合查询错误率、延迟等指标
- **验收标准**:
  - [ ] AC1: 返回 `errorCode=0` 且包含 `metrics` 对象
  - [ ] AC2: 指标包含 `errorRate`、`avgLatency`、`tokenUsage` 字段

### 3.4. Alert管理功能

Alert管理功能域覆盖 FR-035 至 FR-042，包含Alert规则 CRUD、Alert记录查询与已读标记、AlertConfig查询等端点，由 `API/Handlers/UserManagement/AlertHandler.cs` 承载。

#### 3.4.1. FR-035 创建Alert规则 [优先级: Must]

- **用户故事**: 作为运维人员，我希望创建Alert规则，以便在异常发生时及时收到通知。
- **主流程**:
  1. 用户提交项目 ID、指标类型、阈值与通知方式 [API/Handlers/UserManagement/AlertHandler.cs:12]
  2. 系统校验规则参数合法性
  3. 系统创建Alert规则记录
- **验收标准**:
  - [ ] AC1: 创建成功返回 `errorCode=0` 且包含 `alertRuleId` 字段
  - [ ] AC2: 频率参数非法时返回 ``（160005）
- **业务规则**:
  - BR-009: Alert频率由 `` 枚举定义，支持 ``（1）、``（2）、``（3）[Models/Common/Enums/JobEnums.cs:3]

#### 3.4.2. FR-036 查询Alert规则列表 [优先级: Must]

- **用户故事**: 作为运维人员，我希望查看Alert规则列表，以便了解当前Config。
- **主流程**:
  1. 用户提交项目 ID [API/Handlers/UserManagement/AlertHandler.cs:13]
  2. 系统返回该项目下所有Alert规则
- **验收标准**:
  - [ ] AC1: 返回 `errorCode=0` 且包含 `alertRules` 数组
  - [ ] AC2: 每个规则包含 `id`、`metricType`、`threshold`、`frequency` 字段

#### 3.4.3. FR-037 更新Alert规则 [优先级: Should]

- **用户故事**: 作为运维人员，我希望更新Alert规则，以便调整阈值和通知策略。
- **主流程**:
  1. 用户提交规则 ID 与更新内容 [API/Handlers/UserManagement/AlertHandler.cs:14]
  2. 系统校验规则存在且属于当前用户
  3. 系统更新规则记录
- **验收标准**:
  - [ ] AC1: 更新成功返回 `errorCode=0`
  - [ ] AC2: 规则不存在时返回 404 错误

#### 3.4.4. FR-038 删除Alert规则 [优先级: Should]

- **用户故事**: 作为运维人员，我希望删除不再需要的Alert规则，以避免无效通知。
- **主流程**:
  1. 用户提交规则 ID [API/Handlers/UserManagement/AlertHandler.cs:14]
  2. 系统删除对应规则
- **验收标准**:
  - [ ] AC1: 删除成功返回 `errorCode=0`
  - [ ] AC2: 规则不存在时返回 404 错误

#### 3.4.5. FR-039 查询Alert记录 [优先级: Must]

- **用户故事**: 作为运维人员，我希望查询历史Alert记录，以便排查历史问题。
- **主流程**:
  1. 用户提交项目 ID 与时间范围 [API/Handlers/UserManagement/AlertHandler.cs:15]
  2. 系统返回匹配的Alert记录列表
- **验收标准**:
  - [ ] AC1: 返回 `errorCode=0` 且包含 `alertRecords` 数组
  - [ ] AC2: 每条记录包含 `ruleId`、`triggeredAt`、`message` 字段

#### 3.4.6. FR-040 标记Alert已读 [优先级: Should]

- **用户故事**: 作为运维人员，我希望标记Alert为已读，以便跟踪未处理Alert。
- **主流程**:
  1. 用户提交Alert记录 ID 列表 [API/Handlers/UserManagement/AlertHandler.cs:16]
  2. 系统批量更新记录为已读状态
- **验收标准**:
  - [ ] AC1: 标记成功返回 `errorCode=0`
  - [ ] AC2: 已读状态在后续查询中正确返回

#### 3.4.7. FR-041 AlertConfig查询 [优先级: Should]

- **用户故事**: 作为运维人员，我希望查询当前AlertConfig，以便确认通知渠道有效。
- **主流程**:
  1. 用户请求AlertConfig端点 [API/Handlers/UserManagement/AlertHandler.cs:16]
  2. 系统返回当前生效的AlertConfig
- **验收标准**:
  - [ ] AC1: 返回 `errorCode=0` 且包含 `config` 对象
  - [ ] AC2: Config包含通知渠道、频率限制等字段

#### 3.4.8. FR-042 Alert触发通知 [优先级: Must]

- **用户故事**: 作为系统，我希望在指标异常时触发Alert通知，以便用户及时响应。
- **主流程**:
  1. 系统定时检查指标是否满足Alert条件 [API/Notifications/SystemAlertHandler.cs:9]
  2. 条件满足时生成Alert记录
  3. 系统通过系统通知和 SMS 发送Alert [API/Notifications/SMSAlertHandler.cs:9]
- **验收标准**:
  - [ ] AC1: Alert触发时生成记录并发送通知
  - [ ] AC2: 通知内容包含指标名称、阈值、当前值

### 3.5. Payment管理功能

Payment管理功能域覆盖 FR-043 至 FR-050，包含订单查询/下单/Payment回调（微信/Payment宝）、产品转换计算等端点，由 `API/Handlers/PaymentManagement/OrderHandler.cs` 与 `API/Handlers/PaymentManagement/NotifyHandler.cs` 承载。

#### 3.5.1. FR-043 创建订单 [优先级: Must]

- **用户故事**: 作为购买者，我希望创建订单，以便购买订阅服务。
- **主流程**:
  1. 用户提交产品 ID 与Payment方式 [API/Handlers/PaymentManagement/OrderHandler.cs:12]
  2. 系统调用 `PaymentService` 创建订单 [API/Handlers/PaymentManagement/OrderHandler.cs:9]
  3. 系统返回订单 ID 与Payment参数
- **验收标准**:
  - [ ] AC1: 创建成功返回 `errorCode=0` 且包含 `orderId` 与 `payParams` 字段
  - [ ] AC2: 产品不存在时返回 404 错误
- **业务规则**:
  - BR-010: Payment核心逻辑由 `PaymentService` 统一处理，包括订单创建、签名验证、状态更新 [API/Common/Services/PaymentService.cs]

#### 3.5.2. FR-044 查询订单列表 [优先级: Must]

- **用户故事**: 作为购买者，我希望查询历史订单，以便核对消费记录。
- **主流程**:
  1. 用户提交分页参数 [API/Handlers/PaymentManagement/OrderHandler.cs:13]
  2. 系统返回当前用户的订单列表
- **验收标准**:
  - [ ] AC1: 返回 `errorCode=0` 且包含 `orders` 数组
  - [ ] AC2: 每个订单包含 `id`、`amount`、`status`、`createdAt` 字段

#### 3.5.3. FR-045 查询订单详情 [优先级: Should]

- **用户故事**: 作为购买者，我希望查看订单详情，以便了解Payment状态。
- **主流程**:
  1. 用户提交订单 ID [API/Handlers/PaymentManagement/OrderHandler.cs:14]
  2. 系统返回订单完整信息
- **验收标准**:
  - [ ] AC1: 返回 `errorCode=0` 且包含订单全部字段
  - [ ] AC2: 订单不存在时返回 404 错误

Agent 管理功能域覆盖 FR-051 至 FR-059，包含 Agent Config/报告模板/Session管理等端点，由 `API/Handlers/AgentManagement/AgentConfigHandler.cs`、`AgentReportHandler.cs`、`AgentSessionHandler.cs` 承载。

#### 3.5.4. FR-051 获取 Agent Config [优先级: Must]

- **用户故事**: 作为用户，我希望获取我的 Agent Config，以便了解当前数据源和模板设置。
- **主流程**:
  1. 用户请求 Agent Config端点 [API/Controllers/AgentManagement/AgentConfigController.cs]
  2. 系统返回当前用户的 Agent Config
- **验收标准**:
  - [ ] AC1: 返回 `errorCode=0` 且包含 `datasource`、`defaulttemplateid` 字段
  - [ ] AC2: Config不存在时返回 ``（150022）

#### 3.5.5. FR-052 创建或更新 Agent Config [优先级: Must]

- **用户故事**: 作为用户，我希望创建或更新 Agent Config，以便设置数据源连接和默认模板。
- **主流程**:
  1. 用户提交Config内容 JSON [API/Controllers/AgentManagement/AgentConfigController.cs]
  2. 系统解析Config并创建或更新记录
-

---

## 4. 非功能需求

AgentInsightService 是面向 AI Agent 应用的可Observation性与分析平台，提供 Trace 数据采集、指标分析、Alert管理、用户与组织管理、Payment与订阅、Agent Config管理等功能。系统由 C# 后端 API（Furion 框架）和 Python Agent Service（FastAPI）组成，支持多租户组织/项目隔离。NFR，涵盖性能、可用性、安全、可扩展性、可维护性、兼容性与本地化七个维度。所有 NFR 均以表格形式呈现，每条包含编号、Metric、目标值与验证方式，确保需求可量化、可测试、可Trace。

### 4.1. 性能

性能需求确保 AgentInsightService 在正常与峰值负载下均能提供稳定的响应能力。核心 API 的响应时间与吞吐量直接影响用户体验与数据采集效率。

| 编号 | Metric | 目标值 | 验证方式 |
|------|------|--------|----------|
| NFR-P-001 | API P95 | ≤500ms（除 Trace 查询外） | 使用 JMeter 或 k6 进行压测，采样窗口 10 分钟，统计 P95 百分位响应时间 |
| NFR-P-002 | 并发吞吐量 | 支持 1000 并发 | 基于 Redis 缓存与连接池Config，使用压测工具模拟 1000 并发请求，验证错误率 <1% |

性能设计依托于多层缓存与连接池机制。系统通过 `IMemoryCache` 在 Controller 层缓存高频查询结果，例如 `MetricsController` 构造函数中注入 `IMemoryCache cache` 并传递给基类 [API/Controllers/DataManagement/MetricsController.cs:19-L21]。数据查询路径中，`MetricsHandler` 调用 `ClickHouseClient` 执行 Trace 数据查询 [API/Handlers/DataManagement/MetricsHandler.cs:14]，ClickHouse 连接字符串Config了 `MaxPoolSize=10;MinPoolSize=5;ConnectionTimeout=30;CommandTimeout=60`，确保数据库连接复用与超时控制。Redis 缓存（StackExchange.Redis）用于缓解热点数据的重复查询压力，连接池Config（`ConnectRetry=10`, `ConnectTimeout=200`）保证数据库连接的充分复用。

对于 Trace 查询类接口（如 `GET /api/data/metrics/traces`），由于涉及 ClickHouse 大规模数据扫描，允许响应时间超过 500ms 基线，但需保证查询超时控制在 `CommandTimeout=60` 秒以内，避免长时间占用数据库连接。

### 4.2. 可用性

可用性需求保障系统核心服务持续可访问，并通过健康检查机制实现故障的快速发现与恢复。

| 编号 | Metric | 目标值 | 验证方式 |
|------|------|--------|----------|
| NFR-A-001 | 核心服务可用性 | ≥99.9%（月累计停机时间 ≤43 分钟） | 通过健康检查接口 `GET /api/tools/health` 定期探测，监控可用性指标 [API/Controllers/ToolsManagement/HealthController.cs:20] |

健康检查接口由 `HealthController.Get` 方法实现，路由注册为 `GET /api/tools/health` [API/Controllers/ToolsManagement/HealthController.cs:20]。该接口不依赖数据库或外部服务，仅返回服务进程存活状态，确保探测本身不会因依赖故障而误报。监控系统应每 30 秒探测一次健康检查端点，连续 3 次失败即触发Alert，并自动重启容器实例。

系统采用多实例部署架构，单个实例故障时由负载均衡器将流量切换到健康实例，实现无缝故障转移。数据库层（PostgreSQL 与 ClickHouse）均支持主从复制与自动故障切换，确保数据层的高可用。

### 4.3. 安全

安全需求覆盖身份认证、数据完整性校验与Payment回调验签三个核心层面，确保系统在开放网络环境下的数据安全与交易安全。

| 编号 | Metric | 目标值 | 验证方式 |
|------|------|--------|----------|
| NFR-S-001 | 身份认证 | 使用 JWT HS256 算法签名，Token 过期时间见Config文件 | 使用过期 Token 访问受保护接口，验证返回 `UnauthorizedException`（errorCode=100037） |
| NFR-S-002 | API Key 签名校验 | 请求携带 API Key 与签名，服务端校验防篡改 | 篡改请求体后发送，验证返回 `ApiKeySignatureInvalidException`（errorCode=100038） |
| NFR-S-003 | Payment回调验签 | 微信/Payment宝回调均执行签名验证 | 构造非法签名回调，验证返回 `PaymentSignatureInvalidException`（errorCode=810007）或微信验签失败错误 |

JWT 认证由 `AgentInsightTransformProvider` 实现，该组件负责 API 认证与限流，支持 Basic Auth/JWT 认证、API Key 验证与速率限制 [API/System/Handlers/AgentInsightTransformProvider.cs:9]。JWT 使用 HS256 算法签名，密钥通过环境变量注入，Token 过期时间在Config文件中统一管理。API Key 签名校验确保请求参数在传输过程中未被篡改，签名算法使用 HMAC-SHA256，密钥通过 `AppSettings:Security:ApiKeySecret`（环境变量 `${API_KEY_SECRET}`）加密存储。

Payment回调验签由 `PaymentService` 统一处理，微信Payment与Payment宝Payment均实现独立的签名验证逻辑 [API/Common/Services/PaymentService.cs:9]。验签失败时返回对应的错误码（如 `ErrorCode.PaymentSignatureInvalid = 810007`），并拒绝更新订单状态，防止伪造Payment通知。

### 4.4. 可扩展性

可扩展性需求确保系统能够随业务增长平滑扩展，支持数据层与任务处理层的水平扩容。

| 编号 | Metric | 目标值 | 验证方式 |
|------|------|--------|----------|
| NFR-SC-001 | 数据层扩展 | ClickHouse 支持横向扩展（分布式表 + 多节点） | 增加 ClickHouse 节点后，验证数据自动分片与查询路由 |
| NFR-SC-002 | 异步任务处理 | BullMqService异步处理 Trace 摄入 | 模拟高并发 Trace 上报，验证消息队列积压与消费速率 |

ClickHouse 作为 Trace 数据存储引擎，天然支持分布式表与横向扩展。当数据量增长时，可通过增加 ClickHouse 节点实现水平扩容，系统无需修改应用代码。`ClickHouseClient` 封装了连接管理逻辑 [API/Common/Services/ClickHouseClient.cs]，支持连接池动态调整。

Trace 摄入采用异步处理模式，`BullMqService` 提供 `EnqueueTraceIngestionAsync` 与 `AcknowledgeTraceIngestionAsync` 方法，将 Trace 数据写入消息队列后立即返回，由后台消费者批量写入 ClickHouse。该设计将高吞吐的数据写入与 API 请求路径解耦，避免写入瓶颈影响 API 响应时间。消息队列支持消费者水平扩展，通过增加消费者实例提升处理吞吐量。

### 4.5. 可维护性

可维护性需求确保代码结构清晰、可诊断性强，降低系统运维与二次开发成本。

| 编号 | Metric | 目标值 | 验证方式 |
|------|------|--------|----------|
| NFR-M-001 | 代码分层架构 | Controller-Handler-Service 三层解耦 | 代码评审检查分层依赖方向，禁止跨层调用 |
| NFR-M-002 | 可Observation性 | 结构化日志 + 分布式Trace（OpenTelemetry） | 验证日志包含 `trace_id`/`span_id`，Trace数据可上报至 OpenTelemetry Collector |

系统采用 Controller-Handler-Service 三层架构：Controller 负责 HTTP 协议适配与参数绑定，Handler 负责业务逻辑编排，Service 负责领域逻辑与数据访问。以 `MetricsController` 为例，Controller 仅注入 `MetricsHandler` 并调用其方法 [API/Controllers/DataManagement/MetricsController.cs:19-L21]，Handler 内部再调用 `ClickHouseClient` 执行数据查询 [API/Handlers/DataManagement/MetricsHandler.cs:14]，依赖方向清晰、职责单一。

可Observation性方面，系统集成 OpenTelemetry 分布式Trace（`opentelemetry_exporter_otlp_proto_http` 等依赖），所有 API 请求自动生成 `trace_id`/`span_id` 并贯穿日志与Trace数据。结构化日志记录请求参数、响应状态、耗时等关键信息，便于问题定位与性能分析。

### 4.6. 兼容性

兼容性需求明确系统运行所依赖的基础软件版本，确保部署环境的可预期性。

| 编号 | Metric | 目标值 | 验证方式 |
|------|------|--------|----------|
| NFR-C-001 | 基础软件版本 | PostgreSQL 15+、ClickHouse 22+、.NET 8、Python 3.12 | 在目标版本环境执行全量回归测试 |

系统后端基于 .NET 8 构建，使用 Furion 框架；Python Agent 服务基于 Python 3.12 与 FastAPI。数据库层使用 PostgreSQL 15+ 存储业务数据（User、Org、订单等），ClickHouse 22+ 存储 Trace 数据。Agent 服务依赖 `agentinsight-sdk`、`openai`、`httpx`、`pydantic` 等 Python 包，均要求 Python 3.12 及以上版本。

### 4.7. 本地化

本地化需求确保系统支持多语言与多区域部署，满足不同用户群体的使用习惯。

| 编号 | Metric | 目标值 | 验证方式 |
|------|------|--------|----------|
| NFR-L-001 | 多语言支持 | TraditionalChineseExtension，错误消息使用多语言 JSON 资源 | 切换语言环境后验证界面与错误消息正确显示对应语言 |

系统使用 `My.Extensions.Localization.Json` 实现多语言资源管理，错误消息存储于 JSON 资源文件中，支持按语言动态加载。`TraditionalChineseExtension` 提供繁体中文扩展支持，覆盖界面文案与错误消息。CaptchaConfig（`CaptchaSetting.ExpirationMinutes=5`、`CaptchaSetting.CodeLength=6`、`CaptchaSetting.MaxAttempts=6`）与错误消息文案均支持多语言切换，确保不同语言环境下用户体验一致。

---

## 5. 接口需求

AgentInsightService 是一个基于 .NET 的Agent洞察分析平台，其接口体系分为内部接口与外部接口两大类。内部接口解决服务间通信、业务逻辑解耦与异步处理问题，外部接口则负责与Payment平台、微信生态、短信服务、ClickHouse 及 Redis 等第三方系统集成。本章节详细定义两类接口的功能需求、鉴权方式、数据格式与异常处理约定。

### 5.1. 内部接口

内部接口涵盖 API 网关路由、服务间调用解耦、异步任务队列三个层面，确保系统各模块之间高效、可靠、可Observation地协作。

#### 5.1.1. API 网关反向代理

系统采用 Yarp 作为 API 网关反向代理组件，负责将外部 HTTP 请求路由至后端服务。网关层统一处理请求转发、负载均衡与故障转移，业务服务无需感知客户端来源。该设计将路由策略与业务逻辑分离，使得新增或调整服务路由时无需修改业务代码，仅需更新网关Config。网关同时承担 TLS 终止、请求头透传等横切关注点，为下游服务屏蔽网络层复杂性。

#### 5.1.2. 服务间命令/查询解耦

服务间通过 MediatR 命令/查询模式解耦，业务 Handler 不直接依赖具体服务实现，而是发送命令或查询请求，由 MediatR 分发至对应的 Handler 处理。以用户管理为例，`UserHandler` 负责用户注册、登录、微信绑定、成员邀请、角色分配、API Key 管理及月度用量扣减等业务逻辑，其内部通过调用 `UserService` 完成具体数据操作 [API/Handlers/UserManagement/UserHandler.cs:15]。Payment领域同样遵循该模式，`OrderHandler` 与 `NotifyHandler` 均通过调用 `PaymentService` 处理订单创建、Payment回调与状态更新 [API/Handlers/PaymentManagement/OrderHandler.cs:9] [API/Handlers/PaymentManagement/NotifyHandler.cs:9]。数据查询方面，`MetricsHandler` 通过调用 `ClickHouseClient` 完成 Trace/Observation/Score 数据的复杂过滤与排序查询 [API/Handlers/DataManagement/MetricsHandler.cs:14]。

该解耦模式带来以下收益：
- **可测试性**：每个 Handler 可独立进行单元测试，通过 Mock 依赖服务隔离外部系统。
- **可维护性**：新增业务逻辑时仅需新增 Handler 或修改对应服务实现，不影响其他调用方。
- **可扩展性**：MediatR 支持 Pipeline 行为，可统一注入日志、验证、性能监控等横切逻辑。

#### 5.1.3. 异步队列与异常记录

异常记录与审计日志通过异步队列处理，避免同步 I/O 阻塞请求线程。`ExceptionMiddleware` 作为全局异常处理管道，捕获未处理异常后调用 `ILogger` 记录日志，并在 `finally` 块中通过 `DataQueue.Queue.Enqueue` 异步记录接口性能数据 [API/System/Handlers/ExceptionMiddleware.cs:31-L33]。该机制确保即使在高并发或异常频发场景下，日志写入不会影响主请求链路的响应时间。

#### 5.1.4. 内部接口鉴权

内部接口的鉴权由 `AgentInsightTransformProvider` 统一处理，支持 Bearer JWT 与 API Key 两种方式 [API/System/Handlers/AgentInsightTransformProvider.cs:9]。JWT 采用 HS256 签名算法，`ClockSkew` 设置为 5 分钟以容忍客户端与服务端的时间偏差。API Key 认证使用 Basic Auth 格式（`publickey:secretkey`），无效 Key 返回 `InvalidApiKey` 异常码（对应 `ExceptionCodes.cs` 中枚举值 `100038`）[Models/Common/Enums/ExceptionCodes.cs:100038]。公开路由通过 `RouteType` 枚举控制，标记为公开的路由跳过鉴权中间件 [API/System/Handlers/AgentInsightTransformLogic.cs:72]。

### 5.2. 外部接口

外部接口定义 AgentInsightService 与第三方系统之间的交互协议，包括Payment平台回调、微信 API、短信服务、ClickHouse 与 Redis。所有外部接口均需满足安全性、可靠性与幂等性要求。

#### 5.2.1. Payment平台 HTTP 回调

Payment平台回调接口接收微信Payment与Payment宝的异步通知，用于更新订单状态。`NotifyController` 定义了两个回调端点 [API/Controllers/PaymentManagement/NotifyController.cs:29-L55]：

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/payment/notify/wechatnotify` | POST | 微信Payment回调 |
| `/api/payment/notify/alipaynotify` | POST | Payment宝回调 |

两个端点均标记为 `[AllowAnonymous]`，因为Payment平台无法携带业务系统的 JWT Token，安全性依赖签名验证而非身份认证 [API/Controllers/PaymentManagement/NotifyController.cs:13]。微信回调处理流程如下：接收通知请求后，系统首先验证请求体非空及签名有效性，随后解析通知内容并更新对应订单状态，最后返回Payment平台约定的应答格式 [API/Controllers/PaymentManagement/NotifyController.cs:40-L49]。Payment核心逻辑封装在 `PaymentService` 中，包括订单创建、签名验证、订单状态更新等 [API/Common/Services/PaymentService.cs:35-L40]。

**接口需求 IR--001 Payment回调处理** [优先级: Must]
- **用户故事**: 作为Payment平台，我希望将Payment结果异步通知 AgentInsightService，以便系统能及时更新订单状态。
- **主流程**:
  1. Payment平台向回调端点发送 HTTP POST 请求 [API/Controllers/PaymentManagement/NotifyController.cs:29]
  2. 系统验证请求签名，无效请求拒绝处理 [API/Controllers/PaymentManagement/NotifyController.cs:40]
  3. 系统解析通知内容并更新对应订单状态 [API/Controllers/PaymentManagement/NotifyController.cs:42-L44]
  4. 系统返回Payment平台约定的成功/失败应答 [API/Controllers/PaymentManagement/NotifyController.cs:47-L49]
- **验收标准**:
  - [ ] AC1: 微信回调请求体为空时返回 `InvalidRequest` 错误码
  - [ ] AC2: 微信签名验证失败时返回 `SignatureVerificationFailed` 应答
  - [ ] AC3: Payment宝回调处理成功返回字符串 `"success"`
  - [ ] AC4: 订单状态在回调处理后更新为对应Payment结果
- **业务规则**:
  - BR--001: 回调端点必须标记 `[AllowAnonymous]`，安全性依赖签名验证 [API/Controllers/PaymentManagement/NotifyController.cs:13]
  - BR--002: 微信Payment金额单位为分，`Amount = TotalFee / 100` [API/Common/Services/PaymentService.cs:21]

#### 5.2.2. 微信 API 集成

系统通过 `WeChatService` 与微信开放平台交互，涵盖以下能力：

- **微信登录**：用户通过微信授权码换取 `OpenId` 与 Access Token，实现免密登录。
- **公众号消息**：接收微信公众号推送的消息，验证消息签名确保来源可信。
- **Access Token 管理**：自动缓存与刷新微信 Access Token，避免频繁调用微信接口获取凭证。

微信相关端点定义在 `WeChatController` 中 [API/Controllers/ToolsManagement/WeChat/WeChatController.cs:36-L68]：

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/tools/wechat/config` | GET | 微信Config查询 |
| `/api/tools/wechat/message` | POST | 微信消息处理 |

**接口需求 IR--002 微信登录与消息处理** [优先级: Must]
- **用户故事**: 作为终端用户，我希望通过微信账号快速登录 AgentInsightService，以便免去记忆密码的负担。
- **主流程**:
  1. 用户发起微信登录请求，携带微信授权码 [API/Controllers/UserManagement/UserController.cs:42-L44]
  2. 系统调用微信 API 换取用户 `OpenId` 与 Access Token
  3. 系统根据 `OpenId` 查找或创建用户，并签发 JWT Token
  4. 系统返回用户信息与登录凭证
- **验收标准**:
  - [ ] AC1: 微信授权码有效时返回用户信息及 `access-token` 响应头
  - [ ] AC2: 微信授权码无效时返回对应错误码
  - [ ] AC3: 公众号消息签名验证失败时拒绝处理
- **业务规则**:
  - BR--003: 微信 Access Token 必须缓存复用，避免频繁调用微信接口
  - BR--004: 公众号消息必须验证签名后才可处理 [API/Common/Services/WeChatService.cs]

#### 5.2.3. 短信服务

系统支持阿里云与腾讯云短信服务，用于发送Captcha、通知类短信。短信服务通过 `IHttpRequestBuilderService` 构建 HTTP 请求，发送至对应云厂商接口。Captcha相关Config项包括：

| Config项 | 值 | 说明 |
|--------|-----|------|
| `CaptchaSetting.CodeLength` | 6 | 短信Captcha长度 |
| `CaptchaSetting.ExpireSeconds` | 300 | Captcha有效期（秒） |
| `CaptchaSetting.ResendInterval` | 60 | 重发间隔（秒） |

**接口需求 IR--003 短信Captcha发送** [优先级: Should]
- **用户故事**: 作为注册用户，我希望通过手机短信Captcha验证身份，以便完成注册或找回密码。
- **主流程**:
  1. 用户提交手机号请求发送Captcha
  2. 系统生成 6 位随机Captcha并存储（有效期 300 秒）
  3. 系统调用短信服务商 API 发送Captcha至用户手机
  4. 系统返回发送结果
- **验收标准**:
  - [ ] AC1: 同一手机号在 60 秒内重复请求时拒绝发送
  - [ ] AC2: Captcha有效期超过 300 秒后自动失效
  - [ ] AC3: 短信服务商返回失败时系统返回对应错误码
- **业务规则**:
  - BR--005: Captcha长度固定为 6 位数字
  - BR--006: 重发间隔为 60 秒，防止短信轰炸

#### 5.2.4. ClickHouse HTTP 接口

系统通过 ClickHouse HTTP 接口执行 Trace/Observation/Score 等可Observation性数据的写入与查询。连接Config定义在 `ClickHouseOptions` 中，关键参数包括：

| 参数 | Config示例 | 说明 |
|------|----------|------|
| Host | `http://clickhouse.example.com` | ClickHouse 服务地址 |
| Port | `8123` | HTTP 接口端口 |
| MaxConnections | 10 | 最大连接数 |
| MaxConcurrentQueries | 50 | 最大并发查询数 |
| QueryTimeout | 30 秒 | 查询超时时间 |
| WriteTimeout | 60 秒 | 写入超时时间 |

**接口需求 IR--004 ClickHouse 数据写入与查询** [优先级: Must]
- **用户故事**: 作为系统内部服务，我希望通过 ClickHouse HTTP 接口写入和查询可Observation性数据，以便支撑 Trace 分析与指标展示。
- **主流程**:
  1. 系统通过 `ClickHouseClient` 建立与 ClickHouse HTTP 接口的连接 [API/Handlers/DataManagement/MetricsHandler.cs:14]
  2. 写入场景：系统将 Trace/Observation/Score 数据格式化后发送至 ClickHouse 对应数据表
  3. 查询场景：系统根据过滤条件、排序规则与分页参数构建 SQL 查询语句并执行
  4. 系统接收查询结果并映射为业务对象返回调用方
- **验收标准**:
  - [ ] AC1: 数据写入失败时系统返回 `ClickHouseWriteFailed` 错误码
  - [ ] AC2: 查询超时（超过 30 秒）时系统返回 `QueryTimeout` 错误码
  - [ ] AC3: 查询结果正确映射为 Trace/Observation/Score 业务对象
  - [ ] AC4: 并发查询数超过 50 时系统进行排队或限流
- **业务规则**:
  - BR--007: 所有 ClickHouse 查询必须设置超时时间，避免长时间占用连接
  - BR--008: 写入操作必须支持批量提交，减少 HTTP 请求次数

#### 5.2.5. Redis 缓存接口

系统使用 Redis 作为分布式缓存组件，支撑Captcha存储、微信 Access Token 缓存、Session管理等场景。Redis 连接Config定义在 `RedisOptions` 中，关键参数包括：

| 参数 | Config示例 | 说明 |
|------|----------|------|
| ConnectionString | `redis.example.com:6379,password=***` | Redis 连接字符串 |
| Database | `0` | 默认数据库编号 |
| ConnectTimeout | 5 秒 | 连接超时时间 |
| CommandTimeout | 3 秒 | 命令执行超时时间 |

**接口需求 IR--005 Redis 缓存读写** [优先级: Must]
- **用户故事**: 作为系统内部服务，我希望通过 Redis 缓存高频访问数据，以便降低数据库压力并提升响应速度。
- **主流程**:
  1. 系统根据缓存键检查 Redis 中是否存在目标数据
  2. 缓存命中时直接返回缓存值，不访问下游服务
  3. 缓存未命中时从数据库或第三方服务获取数据
  4. 系统将获取到的数据写入 Redis 并设置过期时间
- **验收标准**:
  - [ ] AC1: 缓存键不存在时返回空值，不抛出异常
  - [ ] AC2: 缓存写入失败时不影响主业务流程，仅记录日志
  - [ ] AC3: 缓存过期后自动失效，系统重新从数据源加载
  - [ ] AC4: Redis 连接异常时系统自动降级为直连数据源
- **业务规则**:
  - BR--009: 所有缓存键必须包含业务前缀与命名空间，避免键冲突
  - BR--010: 缓存过期时间必须按业务场景分别设置，Captcha类数据 300 秒，Access Token 类数据按微信有效期动态设置

---

## 6. 数据需求

#### 6.1.1. 数据模型

User包含手机号、微信标识、密码哈希等字段，支持注册、登录、绑定微信等操作 [API/Handlers/UserManagement/UserHandler.cs:24-30]。Organization包含组织名称、所有者 ID 等字段，支持创建与成员管理 [API/Handlers/UserManagement/OrganizationHandler.cs:12-15]。Project归属于组织，由项目管理员管理 [API/Handlers/UserManagement/ProjectHandler.cs:12-15]。

角色枚举 `PGRole` 定义于 [Models/Common/Enums/UserEnum.cs:3]，用于区分组织/项目级别的Privilege角色。API Key 实体支持创建、查询、删除操作 [API/Handlers/UserManagement/UserHandler.cs:42-44]，其作用域由 `ApiKeyScope` 枚举定义 [Models/Common/Enums/UserEnum.cs:12]。

#### 6.1.2. 指标数据模型

Trace、Observation、Score 是平台的核心可Observation性数据实体：

- **Trace**：表示一次 AI Agent 调用的完整链路，包含延迟、Token 消耗（输入/输出/总计）、成本（输入费用/输出费用/总费用）、模型名称等指标字段。Trace 查询支持过滤、排序、分页 [API/Handlers/DataManagement/MetricsHandler.cs:17]。
- **Observation**：表示 Trace 内的单个Observation步骤，按 `start_time` 排序，查询时过滤 `is_deleted` 标记 [API/Handlers/DataManagement/MetricsHandler.cs:15]。
- **Score**：表示对 Trace 或 Observation 的Score记录，按 `created_at` 排序 [API/Handlers/DataManagement/MetricsHandler.cs:16]。

ModelDefinition包含模型名称、匹配模式、输入/输出价格、计费单位、分词器Config、阶梯定价（`pricingtiers`）等字段，由 `ModelHandler` 提供查询能力 [API/Handlers/DataManagement/ModelHandler.cs:12]。

#### 6.1.3. 订单与产品模型

AgentInsightOrder包含订单号（`orderno`）、交易号（`tradeno`）、User ID、Org ID、Product ID、产品名称、价格、折扣、总金额、交易状态（`tradestate`）、订单状态（`orderstate`）、Payment方式（`paymethod`）、子Payment方式（`subpaymethod`）以及产品限额字段（`projectlimit`、`headcountlimit`、`orglimit`、`agentlimit`、`level`）[API/Controllers/PaymentManagement/OrderController.cs]。订单状态枚举 `OrderState` 定义于 [Models/Common/Enums/PaymentEnums.cs:40]，Payment方式枚举 `PayMethod` 定义于 [Models/Common/Enums/PaymentEnums.cs:58]，交易状态枚举 `TradeState` 定义于 [Models/Common/Enums/PaymentEnums.cs:6]。

AgentInsightProduct包含产品名称、类型（`type`：0=None、1=Monthly、2=Permanent）、价格、月费率、永久费率以及各项限额字段 [API/Controllers/ProductManagement/ProductController.cs]。AgentInsightProductDuration包含时长名称、数量（天数）、折扣率 [API/Controllers/ProductManagement/ProductController.cs]。

#### 6.1.4. Alert规则模型

Alert规则实体支持 CRUD 操作 [API/Handlers/UserManagement/AlertHandler.cs:12-14]，包含时间单位（`TimeUnit`）、运算符（`Operator`）、指标字段（`AlertField`）、记录状态（`AlertRecordState`）、通知方式（`NotifyMethod`）等枚举定义，分别位于 [Models/Common/Enums/AlertEnum.cs:3]、[Models/Common/Enums/AlertEnum.cs:10]、[Models/Common/Enums/AlertEnum.cs:20]、[Models/Common/Enums/AlertEnum.cs:33]、[Models/Common/Enums/AlertEnum.cs:39]。

#### 6.1.5. 数据模型汇总

| 实体 | 所属子项目 | 关键字段 | 主要操作 |
|------|-----------|---------|---------|
| User | Entities/UserManagement | 手机号、微信、密码哈希 | 注册/登录/绑定微信 [API/Handlers/UserManagement/UserHandler.cs:24-30] |
| Organization | Entities/UserManagement | 组织名称、所有者 ID | 创建/成员管理 [API/Handlers/UserManagement/OrganizationHandler.cs:12-15] |
| Project | Entities/UserManagement | 项目名称、所属组织 ID | 创建/ConfigAlert [API/Handlers/UserManagement/ProjectHandler.cs:12-15] |
| AgentInsightOrder | Entities/PaymengManagement | 订单号、Product ID、金额、状态 | 下单/查询 [API/Handlers/PaymentManagement/OrderHandler.cs:12-15] |
| Trace | Entities/DataManagement | Trace ID、Token 数、成本、延迟 | 查询/过滤/分页 [API/Handlers/DataManagement/MetricsHandler.cs:17] |
| Observation | Entities/DataManagement | Trace ID、开始时间、内容 | 按 Trace 查询 [API/Handlers/DataManagement/MetricsHandler.cs:15] |
| Score | Entities/DataManagement | Trace ID、Score值、创建时间 | 按 Trace 查询 [API/Handlers/DataManagement/MetricsHandler.cs:16] |
| ModelDefinition | Entities/DataManagement | 模型名称、价格、匹配模式 | 查询模型列表 [API/Handlers/DataManagement/ModelHandler.cs:12] |

### 6.2. 数据存储

AgentInsightService 采用多数据库混合存储架构，根据数据特性选择不同的存储引擎：关系型数据（User、Org、Order）存储于 PostgreSQL，时序指标数据（Trace、Observation、Score）存储于 ClickHouse，Session与缓存数据存储于 Redis。

#### 6.2.1. PostgreSQL 数据库

系统Config三个 PostgreSQL 数据库实例，均通过连接字符串在Config文件中声明：

| 数据库 | 连接Config项 | 用途 |
|--------|-----------|------|
| UserDb | `ConnectionStrings:UserDb` | User、Org、Project、Role、API Key 等身份与Privilege数据 |
| DataDb | `ConnectionStrings:DataDb` | Alert规则、模型定义、Order、产品等业务数据 |
| TrackingDb | `ConnectionStrings:TrackingDb` | 跟踪与审计相关数据 |

三个数据库的连接池Config均为 `MinPoolSize=10; MaxPoolSize=200`，并设置 `Timeout=60; Pooling=true; ConnectionIdleTimeout=300`。`MetricsHandler` 构造函数通过依赖注入同时获取 UserDb 与 DataDb 的 `ISqlSugarClient` 实例 [API/Handlers/DataManagement/MetricsHandler.cs:14]，实现跨库数据访问。

#### 6.2.2. ClickHouse 数据库

ClickHouse 用于存储时序指标数据（Trace、Observation、Score），连接Config项为 `ConnectionStrings:ClickHouseDb`，参数包括 `MinPoolSize=10; MaxPoolSize=50; ConnectTimeout=30; QueryTimeout=60`。`MetricsHandler` 通过 `ISqlSugarClient`（键为 `AgentInsightConst.KeyedService_ClickHouseDb`）访问 ClickHouse，执行 Trace/Observation/Score 查询 [API/Handlers/DataManagement/MetricsHandler.cs:14]。查询超时或错误时分别抛出 `ExceptionCodes.QueryTimeout`（150017）与 `ExceptionCodes.ClickHouseQueryError`（150010）[Models/Common/Enums/ExceptionCodes.cs:6]。

#### 6.2.3. Redis 缓存

Redis 用于Session管理、Captcha缓存、API Key 缓存等场景。CaptchaConfig项包括：图形Captcha长度 5、邮箱Captcha长度 6、短信Captcha长度 6、过期时间 300 秒、重发间隔 60 秒（`CaptchaSetting` Config节）。Redis 客户端基于 StackExchange.Redis 实现。

#### 6.2.4. 数据存储汇总

| 存储引擎 | 数据类别 | 连接Config | 连接池参数 |
|---------|---------|---------|-----------|
| PostgreSQL (UserDb) | User、Org、Project、Role | `ConnectionStrings:UserDb` | MinPoolSize=10, MaxPoolSize=200 |
| PostgreSQL (DataDb) | Order、Product、Alert规则、模型定义 | `ConnectionStrings:DataDb` | MinPoolSize=10, MaxPoolSize=200 |
| PostgreSQL (TrackingDb) | 跟踪与审计数据 | `ConnectionStrings:TrackingDb` | MinPoolSize=10, MaxPoolSize=200 |
| ClickHouse | Trace、Observation、Score | `ConnectionStrings:ClickHouseDb` | MinPoolSize=10, MaxPoolSize=50 |
| Redis | Session、Captcha、API Key 缓存 | StackExchange.Redis | — |

### 6.3. 数据流

AgentInsightService 的核心数据流涵盖数据采集、指标查询、Alert评估、Payment回调四条主链路，各链路之间通过 API 层解耦。

#### 6.3.1. 采集链路：Agent SDK/上报 → API → ClickHouse

Agent SDK 或上报端将 Trace 数据发送至 API 层，API 完成认证与验证后写入 ClickHouse。`MetricsHandler` 通过 `IClickHouseClient` 与 `ISqlSugarClient`（ClickHouse 实例）执行数据写入与查询 [API/Handlers/DataManagement/MetricsHandler.cs:14]。Python Agent Service（FastAPI）提供 OpenAI 兼容的 Chat Completions API（`POST /api/agent/insight`）与Session持久化接口（`GET/DELETE /api/sessions`）[Agents/server.py]。

#### 6.3.2. 查询链路：MetricsHandler → ClickHouse → 聚合响应

`MetricsController` 暴露四个指标查询端点 [API/Controllers/DataManagement/MetricsController.cs:34-125]：

| 端点 | 方法 | 功能 |
|------|------|------|
| `GET /api/data/metrics/observations` | GET | 根据 Trace ID 获取 Observation 列表，支持分页 |
| `GET /api/data/metrics/scores` | GET | 根据 Trace ID 获取 Score 列表，支持分页 |
| `GET /api/data/metrics/traces` | GET | 根据 Trace ID 批量获取指标详情 |
| `POST /api/data/metrics/traces` | POST | 分页查询 Trace 列表，支持过滤、排序 |

查询链路中，`MetricsHandler.QueryTraces` 先解析项目 ID（`ResolveProjectId`），再解析查询字段（`ParseSelectFields`）、排序条件（`ParseSortFields`）与过滤条件（`TraceFilterBuilder.BuildFilters`），最终执行 ClickHouse 查询并返回聚合数据 [API/Handlers/DataManagement/MetricsHandler.cs:17]。

#### 6.3.3. Alert链路：定时任务 → ClickHouse Metric → 条件评估 → 通知

Alert定时任务读取 ClickHouse 中的指标数据，评估Alert规则条件（`AlertService` 中的 `IsConditionMet` 方法），当条件满足时触发通知。通知方式包括系统通知（`SystemAlertHandler`）与短信通知（`SMSAlertHandler`）[API/Notifications/SystemAlertHandler.cs:9]、[API/Notifications/SMSAlertHandler.cs:9]。Alert规则支持 CRUD 操作 [API/Handlers/UserManagement/AlertHandler.cs:12-14]，Alert记录支持查询与已读标记 [API/Handlers/UserManagement/AlertHandler.cs:15-16]。

#### 6.3.4. Payment链路：Payment回调 → 订单更新 → 组织Privilege同步

Payment回调处理流程如下：

1. Payment平台（微信/Payment宝）发送回调请求至 `NotifyHandler` [API/Handlers/PaymentManagement/NotifyHandler.cs:9]。
2. `NotifyHandler` 调用 `PaymentService` 验证签名并更新订单状态 [API/Common/Services/PaymentService.cs:9]。
3. 订单状态更新后，`PaymentService` 同步更新组织Privilege（如项目数、成员数、Agent 数等限额）[API/Common/Services/PaymentService.cs:17]。
4. 用户可通过 `OrderHandler` 查询订单状态 [API/Handlers/PaymentManagement/OrderHandler.cs:12-15]。

#### 6.3.5. 数据流汇总

| 数据流 | 起点 | 中间处理 | 终点 |
|--------|------|---------|------|
| 采集链路 | Agent SDK / 上报端 | API 认证与验证 | ClickHouse |
| 查询链路 | MetricsController | MetricsHandler → ClickHouse 查询 | 聚合响应 |
| Alert链路 | 定时任务 | AlertService 条件评估 | 系统通知 / SMS |
| Payment链路 | Payment平台回调 | PaymentService 签名验证与订单更新 | 组织Privilege同步 |

---

## 7. 约束条件

AgentInsightService 是面向 AI Agent 应用的可Observation性与分析平台，提供 Trace 数据采集、指标分析、Alert管理、用户与组织管理、Payment与订阅、Agent Config管理等功能。系统由 C# 后端 API（Furion 框架）和 Python Agent Service（FastAPI）组成，支持多租户组织/项目隔离。本章从技术、业务与合规三个维度定义系统在开发、运行与交付过程中必须遵守的约束条件，作为功能设计、接口实现与部署运维的边界依据。

### 7.1. 技术约束

#### 7.1.1. 运行时与框架版本

AgentInsightService 后端 API 必须基于 **.NET 8** 构建，使用 Furion 应用框架作为 Web 层基础设施，依赖注入、Config管理、鉴权中间件等能力均通过 Furion 提供。前端 Agent 服务必须基于 **Python 3.12** 运行，使用 FastAPI 作为 HTTP 服务框架，OpenAI 兼容的 Chat Completions 接口定义在 `Agents/server.py` 中。两端的依赖库清单以附录为准，禁止引入未列入附录的第三方框架或运行时组件。

#### 7.1.2. Config目录扫描范围

系统启动时仅扫描 `Configurations` 与 `Resources` 两个Config目录，所有环境相关的Config文件（如数据库连接串、AES 密钥、外部服务凭证等）必须放置在这两个目录内。Config系统通过占位符解析机制加载环境变量，例如 ` = ${}`、`. = PORT=${};=${};...` 等，Config扫描目录由 ` = ['Configurations', 'Resources']` 指定。禁止在代码中硬编码任何环境相关Config值。

#### 7.1.3. 密钥管理与加密

AES 加密密钥必须通过环境变量注入，禁止将密钥明文写入Config文件或代码仓库。系统在启动时从环境变量读取 AES 密钥并用于敏感数据的加解密操作。所有数据库连接字符串中的密码字段同样通过环境变量注入，例如 `. = Host=${};Port=${};Username=${};Password=${};...`。密钥轮换时仅需更新环境变量并重启服务，无需修改代码或Config文件。

#### 7.1.4. 数据库连接约束

系统使用 PostgreSQL 作为业务数据库，通过 SqlSugar ORM 访问。连接字符串必须使用环境变量占位符，禁止硬编码。各数据库连接Config如下：

| Config键 | 说明 | 关键参数 |
|--------|------|----------|
| `.` | 用户库（User、Org、Project、成员关系） | `=postgres;Timeout=60;Pooling=true;=10;=200` |
| `.` | 数据库（业务数据） | `=postgres;Timeout=60;Pooling=true;=10;=200` |
| `.` | Trace库（Trace 数据） | `=postgres;Timeout=60;Pooling=true;=10;=200` |
| `.` | ClickHouse 分析库（指标数据） | `=10;=50;=30;=60` |

`MetricsHandler` 通过 `IClickHouseClient` 与 ClickHouse 数据库交互，查询 Trace、Observation、Score 等指标数据 [API/Handlers/DataManagement/MetricsHandler.cs]。数据库连接超时与命令超时均需在连接字符串中显式Config，禁止依赖默认值。

#### 7.1.5. 代码分层约束

后端代码必须遵循 Handler → Service → Repository 的分层架构。Controller 层仅负责 HTTP 请求/响应转换，业务逻辑必须封装在 Handler 中，跨模块复用逻辑下沉到 Service 层。例如 `OrderHandler` 调用 `IPaymentService` 处理Payment核心逻辑 [API/Handlers/PaymentManagement/OrderHandler.cs]，`UserHandler` 调用 `UserService` 完成用户注册与 JWT Token 签发。禁止在 Controller 中直接编写业务逻辑或直接访问数据库。

### 7.2. 业务约束

#### 7.2.1. 多租户数据隔离

告内容修改后需重新审批。审批操作记录审计日志，包含审批人、审批时间与审批结论。Bulletin管理相关逻辑位于 `API/Handlers/ToolsManagement/BulletinHandler.cs`。

#### 7.2.2. 订单状态不可逆转换

订单状态机定义如下，状态转换必须严格遵循单向流转，禁止跳转或回退：

| 当前状态 | 可转换至 | 触发条件 |
|----------|----------|----------|
| `Created` | `Paid` / `Cancelled` / `Closed` | Payment成功 / 用户取消 / 超时关闭 |
| `Paid` | `Refunded` | 退款成功 |
| `Refunded` | — | 终态 |
| `Cancelled` | — | 终态 |
| `Closed` | — | 终态 |
| `` | `Created` / `Cancelled` | 重新Payment / 用户取消 |

订单状态更新逻辑封装在 `PaymentService` 中 [API/Common/Services/PaymentService.cs]，订单业务处理由 `OrderHandler` 负责 [API/Handlers/PaymentManagement/OrderHandler.cs]。Payment回调通知处理在 `NotifyController` 中完成 [API/Controllers/PaymentManagement/NotifyController.cs]，回调验签通过后方可更新订单状态。禁止任何绕过状态机的直接数据库更新操作。

### 7.3. 合规约束

#### 7.3.1. Payment数据加密传输

系统签发的 JWT Token 必须使用 **HMAC SHA256** 算法进行签名，禁止使用对称加密算法（如 / 之外的弱算法）或非对称算法（如 ）替代。Token 中包含用户 ID、Org ID、角色等声明信息，签名密钥通过环境变量注入，禁止硬编码。用户注册成功后由 `UserService` 创建用户记录并返回 JWT Token [API/Common/Services/UserService.cs]。Token 过期时间由服务端Config控制，过期后需重新登录获取新 Token。API Key 认证与 JWT 认证由 `AgentInsightTransformProvider` 统一处理 [API/System/Handlers/AgentInsightTransformProvider.cs]，无效 Key 返回 `` 错误码。

---

## 8. 需求Trace矩阵

AgentInsightService 是面向可Observation性与智能分析场景的服务平台，提供用户管理、数据查询、Alert规则、订单Payment、Agent 编排等核心能力。FRNFR到具体实现代码的双向Trace关系，确保每一项需求均可追溯至对应的 Controller 方法、Handler 业务逻辑或基础设施Config，作为需求验收与回归测试的基准依据。

### 8.1. FR Trace

功能需求Trace矩阵将 FR-001 至 FR-085 逐一映射至 AgentInsightService 的 Controller 层方法。Controller 作为 HTTP 请求的入口，负责参数绑定、鉴权校验与响应封装，其方法签名与路由特性直接对应功能需求的实现位置。以下按业务域分组列出核心映射关系。

#### 8.1.1. 用户管理域（FR-001 至 FR-020）

用户管理域覆盖注册、登录、信息维护、微信绑定、角色分配、成员邀请与 API Key 管理等需求。所有端点集中在 `API/Controllers/UserManagement/UserController.cs`，路由前缀为 `api/user`。

| 需求 ID | 需求描述 | Controller 方法 | HTTP 端点 | 实现位置 |
|---------|---------|----------------|-----------|---------|
| FR-001 | 用户注册（创建账号） | `UserController.Create` | POST /api/user | [API/Controllers/UserManagement/UserController.cs:43](API/Controllers/UserManagement/UserController.cs:43) |
| FR-002 | 用户登录（密码/短信/微信/APIKey） | `UserController.Login` | POST /api/user/login | [API/Controllers/UserManagement/UserController.cs:73](API/Controllers/UserManagement/UserController.cs:73) |
| FR-003 | 用户登出 | `UserController.Logout` | POST /api/user/logout | [API/Controllers/UserManagement/UserController.cs:88](API/Controllers/UserManagement/UserController.cs:88) |
| FR-004 | 获取当前用户信息 | `UserController.Get` | GET /api/user | [API/Controllers/UserManagement/UserController.cs:29](API/Controllers/UserManagement/UserController.cs:29) |
| FR-005 | 更新用户信息（昵称/头像） | `UserController.Update` | POST /api/user/update | [API/Controllers/UserManagement/UserController.cs:58](API/Controllers/UserManagement/UserController.cs:58) |
| FR-006 | 重置密码 | `UserController.ResetPassword` | POST /api/user/resetpassword | [API/Controllers/UserManagement/UserController.cs:102](API/Controllers/UserManagement/UserController.cs:102) |
| FR-007 | 绑定微信账号 | `UserController.Bind` | POST /api/user/bind/wechat | [API/Controllers/UserManagement/UserController.cs:117](API/Controllers/UserManagement/UserController.cs:117) |
| FR-008 | 解绑微信账号 | `UserController.Unbind` | GET /api/user/unbind/wechat | [API/Controllers/UserManagement/UserController.cs:132](API/Controllers/UserManagement/UserController.cs:132) |
| FR-009 | 分配用户角色 | `UserController.AssignRole` | POST /api/user/role | [API/Controllers/UserManagement/UserController.cs:147](API/Controllers/UserManagement/UserController.cs:147) |
| FR-010 | 邀请成员加入组织 | `UserController.Invite` | POST /api/user/invite | [API/Controllers/UserManagement/UserController.cs:162](API/Controllers/UserManagement/UserController.cs:162) |
| FR-011 | 查询邀请列表 | `UserController.GetInvitations` | GET /api/user/invitation | [API/Controllers/UserManagement/UserController.cs:177](API/Controllers/UserManagement/UserController.cs:177) |
| FR-012 | 删除邀请记录 | `UserController.DeleteInvitation` | POST /api/user/invitation/delete | [API/Controllers/UserManagement/UserController.cs:192](API/Controllers/UserManagement/UserController.cs:192) |
| FR-013 | 创建 API Key | `UserController.CreateApiKey` | POST /api/user/apikey | [API/Controllers/UserManagement/UserController.cs:209](API/Controllers/UserManagement/UserController.cs:209) |
| FR-014 | 查询 API Key 列表 | `UserController.GetApiKeys` | GET /api/user/apikey | [API/Controllers/UserManagement/UserController.cs:225](API/Controllers/UserManagement/UserController.cs:225) |
| FR-015 | 删除 API Key | `UserController.DeleteApiKey` | POST /api/user/apikey/delete | [API/Controllers/UserManagement/UserController.cs:272](API/Controllers/UserManagement/UserController.cs:272) |
| FR-016 | 月度 Agent 用量扣减 | `UserController.DeductMonthlyAgentRate` | GET /api/user/privilege/agent/deduct | [API/Controllers/UserManagement/UserController.cs:242](API/Controllers/UserManagement/UserController.cs:242) |
| FR-017 | 月度 Agent 用量校验 | `UserController.ValidateMonthlyAgentRate` | GET /api/user/privilege/agent/validate | [API/Controllers/UserManagement/UserController.cs:258](API/Controllers/UserManagement/UserController.cs:258) |

用户管理域的 Controller 方法均委托至 `UserHandler` 执行具体业务逻辑 [API/Handlers/UserManagement/UserHandler.cs](API/Handlers/UserManagement/UserHandler.cs)，该 Handler 覆盖用户注册、登录、微信绑定、成员邀请、角色分配、API Key 管理与月度用量扣减等完整能力。`UserHandler` 进一步依赖 `UserService` 完成数据持久化 [API/Handlers/UserManagement/UserHandler.cs:15](API/Handlers/UserManagement/UserHandler.cs:15)。所有 Controller 方法继承自 `ApiControllerBase`，通过 `RegisterHandler` 注册 Handler 实例，并在构造函数中完成当前用户身份的初始化 [API/Controllers/ApiControllerBase.cs](API/Controllers/ApiControllerBase.cs)。

#### 8.1.2. Payment与产品域（FR-021 至 FR-035）

Payment与产品域覆盖产品列表查询、下单、订单查询、Payment状态跟踪等需求。产品端点位于 `API/Controllers/ProductManagement/ProductController.cs`，订单端点位于 `API/Controllers/PaymentManagement/OrderController.cs`。

| 需求 ID | 需求描述 | Controller 方法 | HTTP 端点 | 实现位置 |
|---------|---------|----------------|-----------|---------|
| FR-021 | 获取产品列表 | `ProductController.Get` | GET /api/product | [API/Controllers/ProductManagement/ProductController.cs](API/Controllers/ProductManagement/ProductController.cs) |
| FR-022 | 获取产品时长列表 | `ProductController.GetDuration` | GET /api/product/duration | [API/Controllers/ProductManagement/ProductController.cs](API/Controllers/ProductManagement/ProductController.cs) |
| FR-023 | 创建订单（下单） | `OrderController.Place` | POST /api/payment/order | [API/Controllers/PaymentManagement/OrderController.cs](API/Controllers/PaymentManagement/OrderController.cs) |
| FR-024 | 查询订单列表 | `OrderController.Get` | GET /api/payment/order | [API/Controllers/PaymentManagement/OrderController.cs](API/Controllers/PaymentManagement/OrderController.cs) |
| FR-025 | 查询订单状态 | `OrderController.Query` | GET /api/payment/order/query | [API/Controllers/PaymentManagement/OrderController.cs](API/Controllers/PaymentManagement/OrderController.cs) |
| FR-026 | 微信Payment（JSAPI） | `OrderController.WechatPay` | POST /api/payment/order/wechat/jsapi | [API/Controllers/PaymentManagement/OrderController.cs](API/Controllers/PaymentManagement/OrderController.cs) |
| FR-027 | 微信Payment（Native） | `OrderController.WechatPayNative` | POST /api/payment/order/wechat/native | [API/Controllers/PaymentManagement/OrderController.cs](API/Controllers/PaymentManagement/OrderController.cs) |
| FR-028 | 微信Payment（小程序） | `OrderController.WechatPayMiniProgram` | POST /api/payment/order/wechat/miniprogram | [API/Controllers/PaymentManagement/OrderController.cs](API/Controllers/PaymentManagement/OrderController.cs) |
| FR-029 | Payment宝Payment | `OrderController.Alipay` | POST /api/payment/order/alipay | [API/Controllers/PaymentManagement/OrderController.cs](API/Controllers/PaymentManagement/OrderController.cs) |
| FR-030 | Payment回调处理（微信） | `NotifyController.WechatNotify` | POST /api/payment/notify/wechat | [API/Controllers/PaymentManagement/NotifyController.cs](API/Controllers/PaymentManagement/NotifyController.cs) |
| FR-031 | Payment回调处理（Payment宝） | `NotifyController.AlipayNotify` | POST /api/payment/notify/alipay | [API/Controllers/PaymentManagement/NotifyController.cs](API/Controllers/PaymentManagement/NotifyController.cs) |
| FR-032 | 产品转换计算 | `OrderController.CalculateConversion` | POST /api/payment/order/convert | [API/Controllers/PaymentManagement/OrderController.cs](API/Controllers/PaymentManagement/OrderController.cs) |
| FR-033 | 组织Privilege更新（Payment成功后） | `PaymentService.UpdateOrganizationPrivilege` | 内部调用 | [API/Common/Services/PaymentService.cs:17](API/Common/Services/PaymentService.cs:17) |
| FR-034 | 查询Payment状态 | `OrderController.GetPaymentStatus` | GET /api/payment/order/status | [API/Controllers/PaymentManagement/OrderController.cs](API/Controllers/PaymentManagement/OrderController.cs) |
| FR-035 | 取消订单 | `OrderController.Cancel` | POST /api/payment/order/cancel | [API/Controllers/PaymentManagement/OrderController.cs](API/Controllers/PaymentManagement/OrderController.cs) |

Payment与产品域的 Controller 方法委托至 `OrderHandler` 执行订单业务逻辑 [API/Handlers/PaymentManagement/OrderHandler.cs](API/Handlers/PaymentManagement/OrderHandler.cs)，依赖 `PaymentService` 完成微信Payment与Payment宝Payment集成 [API/Common/Services/PaymentService.cs:9](API/Common/Services/PaymentService.cs:9)。Payment回调由 `NotifyHandler` 处理 [API/Handlers/PaymentManagement/NotifyHandler.cs](API/Handlers/PaymentManagement/NotifyHandler.cs)，产品转换计算由 `OrderHandler` 中的转换逻辑完成 [API/Handlers/PaymentManagement/OrderHandler.cs:18](API/Handlers/PaymentManagement/OrderHandler.cs:18)。

#### 8.1.3. 数据指标域（FR-036 至 FR-050）

数据指标域覆盖 Trace 查询、Observation 查询、Score 查询、模型管理、Alert指标查询等需求。数据指标端点位于 `API/Controllers/DataManagement/`，模型管理端点位于 `API/Controllers/DataManagement/ModelController.cs`。

| 需求 ID | 需求描述 | Controller 方法 | HTTP 端点 | 实现位置 |
|---------|---------|----------------|-----------|---------|
| FR-036 | 查询 Trace 数据 | `MetricsController.GetTraces` | GET /api/data/metrics/traces | [API/Controllers/DataManagement/MetricsController.cs](API/Controllers/DataManagement/MetricsController.cs) |
| FR-037 | 查询 Observation 数据 | `MetricsController.GetObservations` | GET /api/data/metrics/observations | [API/Controllers/DataManagement/MetricsController.cs](API/Controllers/DataManagement/MetricsController.cs) |
| FR-038 | 查询 Score 数据 | `MetricsController.GetScores` | GET /api/data/metrics/scores | [API/Controllers/DataManagement/MetricsController.cs](API/Controllers/DataManagement/MetricsController.cs) |
| FR-039 | 获取模型列表 | `ModelController.Get` | GET /api/data/model | [API/Controllers/DataManagement/ModelController.cs](API/Controllers/DataManagement/ModelController.cs) |
| FR-040 | 创建模型 | `ModelController.Create` | POST /api/data/model | [API/Controllers/DataManagement/ModelController.cs](API/Controllers/DataManagement/ModelController.cs) |
| FR-041 | 更新模型 | `ModelController.Update` | POST /api/data/model/update | [API/Controllers/DataManagement/ModelController.cs](API/Controllers/DataManagement/ModelController.cs) |
| FR-042 | 删除模型 | `ModelController.Delete` | GET /api/data/model/delete | [API/Controllers/DataManagement/ModelController.cs](API/Controllers/DataManagement/ModelController.cs) |
| FR-043 | 查询Alert指标 | `AlertMetricsController.Get` | GET /api/data/alert-metrics | [API/Controllers/DataManagement/AlertMetricsController.cs](API/Controllers/DataManagement/AlertMetricsController.cs) |
| FR-044 | 查询指标聚合统计 | `MetricsController.GetAggregatedStats` | GET /api/data/metrics/stats | [API/Controllers/DataManagement/MetricsController.cs](API/Controllers/DataManagement/MetricsController.cs) |
| FR-045 | 查询指标时间序列 | `MetricsController.GetTimeSeries` | GET /api/data/metrics/timeseries | [API/Controllers/DataManagement/MetricsController.cs](API/Controllers/DataManagement/MetricsController.cs) |
| FR-046 | 查询 Token 消耗统计 | `MetricsController.GetTokenUsage` | GET /api/data/metrics/token-usage | [API/Controllers/DataManagement/MetricsController.cs](API/Controllers/DataManagement/MetricsController.cs) |
| FR-047 | 查询延迟分布 | `MetricsController.GetLatencyDistribution` | GET /api/data/metrics/latency | [API/Controllers/DataManagement/MetricsController.cs](API/Controllers/DataManagement/MetricsController.cs) |
| FR-048 | 查询成本统计 | `MetricsController.GetCostStats` | GET /api/data/metrics/cost | [API/Controllers/DataManagement/MetricsController.cs](API/Controllers/DataManagement/MetricsController.cs) |
| FR-049 | 查询错误率统计 | `MetricsController.GetErrorRate` | GET /api/data/metrics/error-rate | [API/Controllers/DataManagement/MetricsController.cs](API/Controllers/DataManagement/MetricsController.cs) |
| FR-050 | 导出指标数据 | `MetricsController.Export` | GET /api/data/metrics/export | [API/Controllers/DataManagement/MetricsController.cs](API/Controllers/DataManagement/MetricsController.cs) |

`MetricsController` 委托 `MetricsHandler` 执行查询逻辑，支持复杂过滤与排序，依赖 `ClickHouseClient` 执行查询 [API/Handlers/DataManagement/MetricsHandler.cs:14](API/Handlers/DataManagement/MetricsHandler.cs:14)。`ModelController.Get` 方法支持 `keyword`、`projectid`、`includedpredefined`、`orderby`、`page`、`pageSize` 等查询参数，其中 `includedpredefined` 控制是否包含预定义模型 [API/Controllers/DataManagement/ModelController.cs](API/Controllers/DataManagement/ModelController.cs)。`AlertMetricsController` 委托 `AlertMetricsHandler` 执行Alert指标查询 [API/Handlers/DataManagement/AlertMetricsHandler.cs:9](API/Handlers/DataManagement/AlertMetricsHandler.cs:9)。

#### 8.1.4. Agent 管理域（FR-051 至 FR-065）

Agent 管理域覆盖 Agent Config的获取、创建、更新与删除，以及 Agent 报告模板和Session管理等需求。端点位于 `API/Controllers/AgentManagement/` 目录下。

| 需求 ID | 需求描述 | Controller 方法 | HTTP 端点 | 实现位置 |
|---------|---------|----------------|-----------|---------|
| FR-051 | 获取当前用户 Agent Config | `AgentConfigController.Get` | GET /api/agent/config | [API/Controllers/AgentManagement/AgentConfigController.cs](API/Controllers/AgentManagement/AgentConfigController.cs) |
| FR-052 | 创建或更新 Agent Config | `AgentConfigController.Save` | POST /api/agent/config | [API/Controllers/AgentManagement/AgentConfigController.cs](API/Controllers/AgentManagement/AgentConfigController.cs) |
| FR-053 | 删除 Agent Config | `AgentConfigController.Delete` | POST /api/agent/config/delete | [API/Controllers/AgentManagement/AgentConfigController.cs](API/Controllers/AgentManagement/AgentConfigController.cs) |
| FR-054 | 获取 Agent 报告模板列表 | `AgentReportController.Get` | GET /api/agent/report | [API/Controllers/AgentManagement/AgentReportController.cs](API/Controllers/AgentManagement/AgentReportController.cs) |
| FR-055 | 创建 Agent 报告模板 | `AgentReportController.Create` | POST /api/agent/report | [API/Controllers/AgentManagement/AgentReportController.cs](API/Controllers/AgentManagement/AgentReportController.cs) |
| FR-056 | 更新 Agent 报告模板 | `AgentReportController.Update` | POST /api/agent/report/update | [API/Controllers/AgentManagement/AgentReportController.cs](API/Controllers/AgentManagement/AgentReportController.cs) |
| FR-057 | 删除 Agent 报告模板 | `AgentReportController.Delete` | POST /api/agent/report/delete | [API/Controllers/AgentManagement/AgentReportController.cs](API/Controllers/AgentManagement/AgentReportController.cs) |
| FR-058 | 创建 Agent Session | `AgentSessionController.Create` | POST /api/agent/session | [API/Controllers/AgentManagement/AgentSessionController.cs](API/Controllers/AgentManagement/AgentSessionController.cs) |
| FR-059 | 查询 Agent Session列表 | `AgentSessionController.Get` | GET /api/agent/session | [API/Controllers/AgentManagement/AgentSessionController.cs](API/Controllers/AgentManagement/AgentSessionController.cs) |
| FR-060 | 删除 Agent Session | `AgentSessionController.Delete` | POST /api/agent/session/delete | [API/Controllers/AgentManagement/AgentSessionController.cs](API/Controllers/AgentManagement/AgentSessionController.cs) |
| FR-061 | 获取 Agent Session详情 | `AgentSessionController.GetDetail` | GET /api/agent/session/detail | [API/Controllers/AgentManagement/AgentSessionController.cs](API/Controllers/AgentManagement/AgentSessionController.cs) |
| FR-062 | Agent Agent对话（OpenAI 兼容） | `AgentInsightController.Chat` | POST /api/agent/insight | [Agents/server.py](Agents/server.py) |
| FR-063 | Agent SSE | `AgentInsightController.StreamChat` | POST /api/agent/insight/stream | [Agents/server.py](Agents/server.py) |
| FR-064 | 多 Agent 类型支持（Insight/Researcher/CustomService） | `AgentInsightController.Chat` | POST /api/agent/insight | [Agents/server.py:init_agents](Agents/server.py) |
| FR-065 | Agent Session持久化与历史管理 | `AgentSessionController.GetHistory` | GET /api/agent/session/history | [Agents/server.py](Agents/server.py) |

Agent 管理域的 Controller 方法委托至 `AgentConfigHandler`、`AgentReportHandler`、`AgentSessionHandler` 执行具体业务逻辑 [API/Handlers/AgentManagement/AgentConfigHandler.cs:9](API/Handlers/AgentManagement/AgentConfigHandler.cs:9) [API/Handlers/AgentManagement/AgentReportHandler.cs:9](API/Handlers/AgentManagement/AgentReportHandler.cs:9) [API/Handlers/AgentManagement/AgentSessionHandler.cs:9](API/Handlers/AgentManagement/AgentSessionHandler.cs:9)。Agent Agent Agent服务由 Python FastAPI 实现，支持 OpenAI 兼容接口与流式响应 [Agents/server.py](Agents/server.py)。

#### 8.1.5. 用户Config域（FR-066 至 FR-080）

用户Config域覆盖用户Config项的获取、创建、更新与删除等需求。端点位于 `API/Controllers/UserManagement/UserConfigController.cs`。

| 需求 ID | 需求描述 | Controller 方法 | HTTP 端点 | 实现位置 |
|---------|---------|----------------|-----------|---------|
| FR-066 | 获取用户Config项 | `UserConfigController.Get` | GET /api/user/config | [API/Controllers/UserManagement/UserConfigController.cs](API/Controllers/UserManagement/UserConfigController.cs) |
| FR-067 | 创建用户Config | `UserConfigController.Post` | POST /api/user/config | [API/Controllers/UserManagement/UserConfigController.cs](API/Controllers/UserManagement/UserConfigController.cs) |
| FR-068 | 更新用户Config | `UserConfigController.Update` | POST /api/user/config/update | [API/Controllers/UserManagement/UserConfigController.cs](API/Controllers/UserManagement/UserConfigController.cs) |
| FR-069 | 删除用户Config | `UserConfigController.Delete` | POST /api/user/config/delete | [API/Controllers/UserManagement/UserConfigController.cs](API/Controllers/UserManagement/UserConfigController.cs) |
| FR-070 | 获取组织Config项 | `OrganizationController.GetConfig` | GET /api/organization/config | [API/Controllers/UserManagement/OrganizationController.cs](API/Controllers/UserManagement/OrganizationController.cs) |
| FR-071 | 更新组织Config项 | `OrganizationController.UpdateConfig` | POST /api/organization/config/update | [API/Controllers/UserManagement/OrganizationController.cs](API/Controllers/UserManagement/OrganizationController.cs) |
| FR-072 | 获取项目Config项 | `ProjectController.GetConfig` | GET /api/project/config | [API/Controllers/UserManagement/ProjectController.cs](API/Controllers/UserManagement/ProjectController.cs) |
| FR-073 | 更新项目Config项 | `ProjectController.UpdateConfig` | POST /api/project/config/update | [API/Controllers/UserManagement/ProjectController.cs](API/Controllers/UserManagement/ProjectController.cs) |
| FR-074 | 获取Alert规则列表 | `AlertController.Get` | GET /api/alert | [API/Controllers/UserManagement/AlertController.cs](API/Controllers/UserManagement/AlertController.cs) |
| FR-075 | 创建Alert规则 | `AlertController.Create` | POST /api/alert | [API/Controllers/UserManagement/AlertController.cs](API/Controllers/UserManagement/AlertController.cs) |
| FR-076 | 更新Alert规则 | `AlertController.Update` | POST /api/alert/update | [API/Controllers/UserManagement/AlertController.cs](API/Controllers/UserManagement/AlertController.cs) |
| FR-077 | 删除Alert规则 | `AlertController.Delete` | POST /api/alert/delete | [API/Controllers/UserManagement/AlertController.cs](API/Controllers/UserManagement/AlertController.cs) |
| FR-078 | 查询Alert记录 | `AlertController.GetRecords` | GET /api/alert/records | [API/Controllers/UserManagement/AlertController.cs](API/Controllers/UserManagement/AlertController.cs) |
| FR-079 | 标记Alert已读 | `AlertController.MarkAsRead` | POST /api/alert/read | [API/Controllers/UserManagement/AlertController.cs](API/Controllers/UserManagement/AlertController.cs) |
| FR-080 | 创建组织 | `OrganizationController.Create` | POST /api/organization | [API/Controllers/UserManagement/OrganizationController.cs](API/Controllers/UserManagement/OrganizationController.cs) |

用户Config支持 `type` 参数区分Config层级（0=User, 1=Organization, 2=Project），`config` 字段存储 JSON 格式的Config内容 [API/Controllers/UserManagement/UserConfigController.cs](API/Controllers/UserManagement/UserConfigController.cs)。`UserConfigController` 委托 `UserConfigHandler` 执行具体业务逻辑，并通过 `RegisterHandler` 注册至基类 [API/Controllers/UserManagement/UserConfigController.cs](API/Controllers/UserManagement/UserConfigController.cs)。Alert规则相关端点委托 `AlertHandler` 执行规则 CRUD 与记录查询 [API/Handlers/UserManagement/AlertHandler.cs:9](API/Handlers/UserManagement/AlertHandler.cs:9)。

#### 8.1.6. 认证与限流基础设施（FR-081 至 FR-085）

认证与限流需求由 `AgentInsightTransformProvider` 实现，位于 `API/System/Handlers/AgentInsightTransformProvider.cs`。该 Provider 负责 API 认证（Basic Auth/JWT 认证、API Key 验证）与速率限制，依赖 `FurionAppContextService` 获取应用上下文 [API/System/Handlers/AgentInsightTransformProvider.cs:9](API/System/Handlers/AgentInsightTransformProvider.cs:9)。健康检查端点位于 `API/Controllers/ToolsManagement/HealthController.cs:20`，用于服务存活探测 [API/Controllers/ToolsManagement/HealthController.cs:20](API/Controllers/ToolsManagement/HealthController.cs:20)。

| 需求 ID | 需求描述 | 实现位置 |
|---------|---------|---------|
| FR-081 | API 认证（Basic Auth/JWT） | [API/System/Handlers/AgentInsightTransformProvider.cs](API/System/Handlers/AgentInsightTransformProvider.cs) |
| FR-082 | API Key 验证 | [API/System/Handlers/AgentInsightTransformProvider.cs](API/System/Handlers/AgentInsightTransformProvider.cs) |
| FR-083 | 速率限制 | [API/System/Handlers/AgentInsightTransformProvider.cs](API/System/Handlers/AgentInsightTransformProvider.cs) |
| FR-084 | 健康检查 | [API/Controllers/ToolsManagement/HealthController.cs:20](API/Controllers/ToolsManagement/HealthController.cs:20) |
| FR-085 | Captcha服务（图形/短信/邮箱） | [API/Handlers/UserManagement/CaptchaHandler.cs:9](API/Handlers/UserManagement/CaptchaHandler.cs:9) |

### 8.2. NFR Trace

非功能需求Trace矩阵将性能、安全、可用性等质量属性映射至对应的测试计划、扫描清单与监控看板，作为验收交付物。每一项 NFR 均需具备可量化的验收标准与明确的验证手段。

| 需求 ID | 需求描述 | 验收标准 | 验证手段 | 实现/验证位置 |
|---------|---------|---------|---------|-------------|
| NFR-001 | 性能 | API 响应时间 P95 ≤ 500ms，P99 ≤ 1s | 性能测试计划 | 执行性能测试脚本，核对压测报告 |
| NFR-002 | 并发能力 | 核心 API 支持 ≥ 1000 并发请求 | 性能测试计划 | 执行并发压测，核对吞吐量与错误率 |
| NFR-003 | 查询性能 | Trace 查询在 1 亿条数据下 P95 ≤ 2s | 性能测试计划 | 使用 ClickHouse 基准测试数据集验证 |
| NFR-004 | 传输安全 | 所有 HTTP 端点强制 HTTPS，敏感字段加密传输 | 安全扫描清单 | 核对 TLS Config与加密策略 |
| NFR-005 | 认证安全 | 密码存储使用 BCrypt 加密，登录失败锁定策略 | 安全扫描清单 | 核对 `UserHandler` 密码加密实现 [API/Handlers/UserManagement/UserHandler.cs](API/Handlers/UserManagement/UserHandler.cs) |
| NFR-006 | 授权安全 | RBAC，越权访问返回 403 | 安全扫描清单 | 执行越权测试用例，核对Privilege校验逻辑 |
| NFR-007 | Captcha安全 | 图形Captcha长度 = 5，邮箱Captcha长度 = 6，短信Captcha长度 = 6，有效期 ≤ 300 秒 | 安全扫描清单 | 核对 `CaptchaSetting` Config项 [Config文件技术规格](Config文件技术规格) |
| NFR-008 | 服务可用性 | 核心服务可用性 ≥ 99.9%（月度） | 可用性监控看板 | 通过健康检查端点 `GET /health` 定期探测 [API/Controllers/ToolsManagement/HealthController.cs:20](API/Controllers/ToolsManagement/HealthController.cs:20) |
| NFR-009 | 错误监控 | 系统错误率 ≤ 0.1%，无未捕获异常 | 可用性监控看板 | 接入 Prometheus + Grafana 监控错误率 |
| NFR-010 | 数据持久性 | Order、User、Config数据持久化存储，无数据丢失 | 可用性监控看板 | 数据库备份策略验证，恢复演练记录 |
| NFR-011 | 代码质量 | 单元测试通过率 = 100%，行覆盖率 ≥ 80% | 测试报告 | 执行 `pytest --cov=app --cov-report=term-missing` 并核对覆盖率 [Admin/Agents.md](Admin/Agents.md) |
| NFR-012 | 代码风格 | 通过 flake8 与 black 代码风格检查 | 代码评审记录 | 执行 `flake8 app/ --max-line-length=120` 与 `black app/ --check --line-length=120` [Admin/Agents.md](Admin/Agents.md) |
| NFR-013 | 安全漏洞 | 安全扫描无高危及以上漏洞 | 安全扫描清单 | 执行 `bandit -r app/ -ll` 扫描 Python 代码 [Admin/Agents.md](Admin/Agents.md) |
| NFR-014 | 回归测试 | 回归测试通过率 ≥ 95%，缺陷关闭率 ≥ 95% | 测试报告 | 执行全量测试并核对缺陷管理记录 [Admin/Agents.md](Admin/Agents.md) |
| NFR-015 | 需求覆盖率 | 100% 功能需求通过验收 | 需求验收记录 | 产品经理逐项核对需求Trace矩阵 [Admin/Agents.md](Admin/Agents.md) |

性能类 NFR（NFR-001 至 NFR-003）通过性能测试计划验证，测试环境需与生产环境Config一致（含连接池参数、缓存策略）。安全类 NFR（NFR-004 至 NFR-007）通过安全扫描清单验证，扫描范围覆盖所有 HTTP 端点与认证机制。可用性类 NFR（NFR-008 至 NFR-010）通过可用性监控看板持续Observation，看板需展示健康检查状态、错误率与关键业务指标。质量类 NFR（NFR-011 至 NFR-015）通过测试报告与代码评审记录验证，作为版本发布的准入条件。

NFR Trace矩阵与 FR Trace矩阵共同构成完整的验收体系：FR 矩阵确保功能完整性，NFR 矩阵确保质量达标。两者均以代码仓库中的真实实现为基准，任何需求变更均需同步更新矩阵并重新执行验证流程。

---

## 9. 错误码参考

AgentInsightService 作为面向 AI Agent 应用的可Observation性与分析平台，提供 Trace 数据采集、指标分析、Alert管理、用户与组织管理、Payment与订阅、Agent Config管理等功能。系统由 C# 后端 API（Furion 框架）和 Python Agent Service（FastAPI）组成，支持多租户组织/项目隔离。在 API 调用过程中，系统通过统一的错误码机制向调用方返回明确的业务处理结果。所有错误码常量定义于 `Models/Common/Enums/ExceptionCodes.cs` 枚举中，对应的多语言提示信息维护在 `API/Resources/Text.zh-CN.json`、`API/Resources/Text.en.json` 与 `API/Resources/Text.zh-TW.json` 三个资源文件中。错误码整体分为通用错误码与业务错误码两大类，业务错误码进一步按用户管理、Org/项目管理、API Key 管理、Alert管理、Payment管理等模块进行细分。

### 9.1. 通用错误码

通用错误码覆盖认证授权、Session状态、参数校验等跨模块的基础异常场景，是系统所有 API 接口共用的错误码集合。该类错误码在用户认证、请求鉴权、基础参数校验等环节被广泛使用，任何模块的接口在遇到对应异常时均会返回相同的错误码与提示信息。

、参数校验等跨模块的基础异常场景，是系统所有 API 接口共用的错误码集合。该类错误码在用户认证、请求鉴权、基础参数校验等环节被广泛使用，任何模块的接口在遇到对应异常时均会返回相同的错误码与提示信息。

| 错误码常量名 | 数值 | 中文提示 | 英文提示 | 说明 |
|------------|------|---------|---------|------|
|  | 100000 | 登录已过期，请重新登录 | Session expired, please log in again | JWT Token 缺失、过期或无效时返回 |
|  | 100038 | API密钥无效 | Invalid API key | API Key 认证失败时返回 |
|  | 100037 | 认证凭证无效 | Invalid credentials | Basic Auth 或 JWT 凭证校验失败时返回 |
|  | 100010 | Privilege不足 | Insufficient permissions | 当前用户无权执行目标操作时返回 |
| UserNotInitialized | 100029 | 用户信息未初始化，请重新登录 | User not initialized, please log in again | 当前请求上下文未正确注入用户信息时返回 |
|  | 100001 | 用户信息获取失败，请重新登录 | Failed to get user info, please log in again | 无法从请求上下文中解析用户 ID 时返回 |
|  | 100037 | 认证凭证无效 | Invalid credentials | 认证凭证无效（与上方为同一常量，此处列出以说明其通用性） |

| 无法从请求上下文中解析用户 ID 时返回 |
|  | 100037 | 认证凭证无效 | Invalid credentials | 认证凭证无效（与上方为同一常量，此处列出以说明其通用性） |

上述错误码在代码中的实际使用方式如下：`ApiHandlerBase` 中通过 `User` 属性访问当前认证用户，若用户未初始化则直接抛出 `UserNotInitialized` 异常 [API/Handlers/ApiHandlerBase.cs]。在 `AgentInsightTransformLogic` 中，`ValidateApiKey` 方法负责校验 API Key 的合法性，校验失败时返回 `IsValid = false`，由上层中间件映射为 `` 错误码 [API/System/Handlers/AgentInsightTransformLogic.cs]。`AlertHandler` 在更新Alert规则时，若发现当前用户不是规则创建者，则抛出 `` 异常 [API/Handlers/UserManagement/AlertHandler.cs]。

通用错误码的提示信息在三语资源文件中保持一致的结构，例如 `` 在简体中文、英文、繁体中文中分别对应"登录已过期，请重新登录"、"Session expired, please log in again"、"登入已過期，請重新登入" [API/Resources/Text.zh-CN.json][API/Resources/Text.en.json][API/Resources/Text.zh-TW.json]。

### 9.2. 业务错误码

业务错误码按功能域划分，覆盖用户管理、Org/项目管理、API Key 管理、Alert管理、Payment管理等具体业务场景。每个错误码对应一个明确的业务规则违反或数据状态异常，调用方可根据错误码精确判断失败原因并采取相应处理。

#### 9.2.1. 用户管理错误码

用户管理模块的错误码覆盖注册、登录、密码重置、邀请成员、角色分配等场景，是系统中最丰富的错误码类别。

| 错误码常量名 | 数值 | 中文提示 | 说明 |
|------------|------|---------|------|
|  | 100003 | 该手机号已注册 | 注册时手机号已存在 |
|  | 100005 | 手机号或密码错误 | 登录时手机号或密码不匹配 |
| UserNameTooLong | 100019 | 用户名不能超过100个字符 | 用户名长度超出限制 |
|  | 100006 | 手机号不能为空 | 手机号参数缺失 |
|  | 100004 | 注册失败，请稍后重试 | 用户创建失败 |
|  | 100027 | 密码重置失败 | 密码重置操作失败 |
|  | 100020 | 被邀请人手机号不能为空 | 邀请成员时手机号缺失 |
|  | 100021 | 被邀请人手机号格式不正确 | 邀请成员时手机号格式非法 |
|  | 100022 | 无法授予高于自身角色的Privilege | 角色分配越权 |
| UserAlreadyOrgMember | 100023 | 该用户已是组织成员 | 重复添加组织成员 |
|  | 100024 | 该手机号已存在待处理邀请 | 重复邀请同一手机号 |
|  | 100025 | 邀请发送失败，请稍后重试 | 邀请创建失败 |
|  | 100026 | 邀请不存在或已处理 | 邀请记录不存在或已处理 |
|  | 100027 | 邀请撤销失败，请稍后重试 | 邀请撤销失败 |
|  | 100030 | 组织所有者不能修改自身Privilege | 所有者修改自身角色被拒绝 |

用户管理错误码在 `UserHandler` 中被广泛使用，例如注册接口校验手机号唯一性时抛出 ``，登录接口校验凭证时抛出 `` [API/Handlers/UserManagement/UserHandler.cs]。

#### 9.2.2. Org/项目管理错误码

组织与项目管理模块的错误码覆盖组织 CRUD、Project CRUD、成员配额、项目配额等场景。

| 错误码常量名 | 数值 | 中文提示 | 说明 |
|------------|------|---------|------|
|  | 100035 | 缺少项目或组织标识 | 请求参数中缺少项目或组织 ID |
|  | 100040 | 组织不存在或已删除 | 组织记录不存在 |
|  | 100046 | 无权访问该组织 | 当前用户非组织成员 |
|  | 100047 | 组织成员数已达上限 | 超出组织成员配额 |
|  | 100048 | 组织项目数已达上限 | 超出组织项目配额 |
|  | 100049 | 可创建组织数已达上限 | 超出用户可创建组织配额 |
|  | 100050 | 该组织已有所有者 | 组织已存在所有者 |
|  | 100054 | 项目不存在或已删除 | 项目记录不存在 |
| UnauthorizedProjectAccess | 100059 | 无权访问该项目 | 当前用户非项目成员 |
|  | 100058 | 该组织下已存在同名项目 | 项目名称重复 |

`OrderHandler` 在查询订单时，若组织 ID 为空或用户非组织成员，则分别抛出 `` 与 `` [API/Handlers/PaymentManagement/OrderHandler.cs]。`ApiHandlerBase` 中的 `RequireOrgMembership` 方法在用户非组织成员时抛出 `` [API/Handlers/ApiHandlerBase.cs]。

#### 9.2.3. API Key 管理错误码

API Key 管理模块的错误码覆盖 API Key 的创建、查询、删除及认证校验场景。

| 错误码常量名 | 数值 | 中文提示 | 说明 |
|------------|------|---------|------|
|  | 100031 | API密钥不存在 | 查询或删除时 API Key 不存在 |
|  | 100032 | API密钥创建失败，请稍后重试 | API Key 创建失败 |
|  | 100033 | API密钥删除失败，请稍后重试 | API Key 删除失败 |
|  | 100036 | 未找到对应的API密钥 | 认证时未找到匹配的 API Key |
|  | 100038 | API密钥无效 | API Key 认证失败 |

API Key 相关错误码在 `UserHandler` 的 API Key 管理方法中被引用 [API/Handlers/UserManagement/UserHandler.cs]，同时 `AgentInsightTransformLogic.ValidateApiKey` 方法在认证流程中校验 API Key 的匹配性 [API/System/Handlers/AgentInsightTransformLogic.cs]。

#### 9.2.4. Alert管理错误码

Alert管理模块的错误码覆盖Alert规则的创建、更新、删除及Alert记录操作场景。

| 错误码常量名 | 数值 | 中文提示 | 说明 |
|------------|------|---------|------|
|  | 100070 | Alert创建失败 | Alert规则创建失败 |
| UpdateAlertFailed | 100071 | Alert更新失败 | Alert规则更新失败 |
|  | 100072 | Alert删除失败 | Alert规则删除失败 |
|  | 100073 | Alert不存在 | Alert规则或记录不存在 |

`AlertHandler` 在创建、更新、删除Alert规则时分别抛出 ``、`UpdateAlertFailed`、``，在查询不到Alert记录时抛出 `` [API/Handlers/UserManagement/AlertHandler.cs]。

#### 9.2.5. Payment与订单错误码

Payment与订单模块的错误码覆盖订单创建、Payment方式校验、Payment回调验证等场景。

| 错误码常量名 | 数值 | 中文提示 | 说明 |
|------------|------|---------|------|
|  | 100090 | 您不是任何组织的所有者 | 下单时用户非任何组织所有者 |
|  | 100091 | 商品不存在 | 商品 ID 无效 |
|  | 100092 | 商品时长不存在 | 商品时长 ID 无效 |
|  | 100093 | 订单不存在 | 订单记录不存在 |
| UnsupportedPayMethod | 100094 | 不支持的Payment方式 | Payment方式非法 |

`OrderHandler` 在下单流程中依次校验组织所有权、商品存在性、商品时长存在性，分别抛出 ``、``、`` [API/Handlers/PaymentManagement/OrderHandler.cs]。

#### 9.2.6. Captcha错误码

Captcha模块的错误码覆盖短信、邮箱Captcha的发送与校验场景。

| 错误码常量名 | 数值 | 中文提示 | 说明 |
|------------|------|---------|------|
|  | 100060 | 操作过于频繁，请稍后再获取Captcha | Captcha发送频率超限 |
|  | 100061 | Captcha发送失败，请稍后重试 | 短信Captcha发送失败 |
|  | 100062 | Captcha不能为空 | Captcha参数缺失 |
|  | 100063 | Captcha已失效，请重新获取 | Captcha过期 |
|  | 100064 | Captcha错误，请重新输入 | Captcha内容错误 |
|  | 100065 | 邮件发送失败，请稍后重试 | 邮箱Captcha发送失败 |

Captcha错误码在 `CaptchaHandler` 中被引用 [API/Handlers/UserManagement/CaptchaHandler.cs]，其发送间隔与有效期Config分别由 `CaptchaSetting.`（60 秒）与 `CaptchaSetting.`（300 秒）控制。

#### 9.2.7. 微信与第三方服务错误码

微信相关错误码覆盖微信登录、公众号消息处理、微信Payment等场景，错误信息中通常包含微信返回的错误码与错误描述。

| 错误码常量名 | 数值 | 中文提示 | 说明 |
|------------|------|---------|------|
|  | 100080 | 微信授权码无效 | 微信 OAuth 授权码无效 |
| WeChatAccountBinded | 100081 | 您已绑定微信，请勿重复绑定 | 重复绑定微信 |
| WeChatAccountBeenBinded | 100082 | 该微信已被其他用户绑定 | 微信已被其他账号绑定 |
| WeChatAccountNotBinded | 100083 | 您尚未绑定微信，请先绑定 | 未绑定微信即执行解绑 |
|  | 100084 | 未找到对应的微信账号 | 微信账号记录不存在 |
|  | 100085 | 微信Payment通知签名验证失败 | 微信Payment回调签名校验失败 |
|  | 100086 | 微信签名验证失败 | 公众号消息签名校验失败 |

微信相关错误码在 `WeChatService` 与 `WeChatHandler` 中被引用 [API/Common/Services/WeChatService.cs][API/Handlers/ToolsManagement/WeChat/WeChatHandler.cs]。

#### 9.2.8. 错误码使用规范

调用方在集成 AgentInsightService API 时，应遵循以下错误码处理规范：

1. **错误码为 int 类型**：响应中的 `errorCode` 字段为整数类型，`0` 表示成功，非零值表示具体错误。
2. **错误码全局唯一**：所有错误码数值在全局范围内唯一，调用方可直接根据数值定位错误类型，无需结合接口路径判断。
3. **多语言提示**：同一错误码在不同语言环境下返回对应的提示信息，调用方应使用错误码进行逻辑判断，而非依赖提示文本。
4. **错误码扩展**：新增业务功能时，应在 `Models/Common/Enums/ExceptionCodes.cs` 中追加新的错误码常量，并在 `API/Resources/Text.zh-CN.json`、`API/Resources/Text.en.json`、`API/Resources/Text.zh-TW.json` 三个资源文件中同步添加对应语言的提示信息。

---

## 10. 附录

AgentInsightService 是一款面向 AI Agent 应用的可Observation性与分析平台，提供 Trace 数据采集、指标分析、Alert管理、用户与组织管理、Payment与订阅、Agent Config管理等功能。系统由 C# 后端 API（Furion 框架）和 Python Agent Service（FastAPI）组成，支持多租户组织/项目隔离。本附录汇总了阅读与维护 AgentInsightService 代码仓库所需的术语定义、技术栈详情、Config文件清单以及枚举定义参考，供开发与运维人员查阅。

### 10.1. 术语表

以下术语表涵盖了 AgentInsightService 代码仓库中的核心业务概念、代码标识符与关键模块名称。所有品牌名与代码标识符均保留原文，不做翻译。

kHouse 数据库客户端封装，`MetricsHandler` 通过其查询 Trace 数据 [API/Handlers/DataManagement/MetricsHandler.cs:14] |
| FurionAppContextService | 代码标识符 | Furion 框架的应用上下文服务，`AgentInsightTransformProvider` 依赖其解析请求上下文 [API/System/Handlers/AgentInsightTransformProvider.cs:9] |
| AlertService | 代码标识符 | Alert条件评估服务，实现 `IAlertService` 接口，提供 `GetTimeSpan`、`IsConditionMet`、`BuildAlertMessage` 等方法 [API/Common/Services/AlertService.cs:9] |
| IPaymentService | 代码标识符 | Payment服务抽象接口，`OrderHandler` 通过其完成订单Payment流程 [API/Handlers/PaymentManagement/OrderHandler.cs:9] |
| AgentInsightTransformProvider | 代码标识符 | API 认证与限流中间件，支持 Basic Auth/JWT 认证、API Key 验证与速率限制 [API/System/Handlers/AgentInsightTransformProvider.cs:9] |
| UserExtension | 代码标识符 | 用户扩展方法类，位于 `API.Common.Extensions` 命名空间 |
| ClickHouseHelper | 代码标识符 | ClickHouse 操作辅助类，位于 `API.Common.Helpers` 命名空间 |
| TraceIdResult | 代码标识符 | 封装 Trace ID 查询结果的数据类型 |
| EnqueueProjectDeleteAsync | 方法名 | `BullMqService` 中异步删除项目任务入队方法 |

| EnqueueTraceIngestionAsync | 方法名 | `BullMqService` 中 Trace 数据摄入任务入队方法 |
| AcknowledgeTraceIngestionAsync | 方法名 | `BullMqService` 中确认 Trace 数据摄入完成的方法 |
| DisposeAsync | 方法名 | 异步释放资源的通用方法，`BullMqService` 实现该模式以清理队列连接 |
| PGRole | 枚举 | Org/项目角色枚举，`OrderHandler` 中校验 `PGRole.OWNER` 以确认组织所有者Privilege [API/Handlers/PaymentManagement/OrderHandler.cs:9] |

### 10.2. 技术栈详情

AgentInsightService 采用前后端分离架构，后端由 C# API 与 Python Agent 服务两部分组成。以下表格列出了各层使用的核心技术栈及其用途。

#### 10.2.1. C# 后端 API 技术栈

| 技术栈 | 版本/类型 | 用途说明 |
|--------|-----------|----------|
| Furion | 框架 | 后端 API 基础框架，提供依赖注入、、动态 API Controller等能力，所有 Handler 均继承自 `ApiHandlerBase` |
| SqlSugar | ORM | 数据访问层 ORM，通过 `[]` 注入多数据库实例（用户库、数据库）[API/Handlers/PaymentManagement/OrderHandler.cs:9] |
| MediatR | 库 | 进程内消息传递，用于 Handler 间的请求/响应解耦 |
| Npgsql | 库 | PostgreSQL 数据库驱动，支持用户库、数据库、Trace库等多库连接 |
| StackExchange.Redis | 库 | Redis 客户端，用于缓存、分布式锁及消息队列场景 |
| Yarp.ReverseProxy | 库 | 反向代理组件，用于 API 网关路由与请求转发 |
| .Standard | 库 | Payment宝Payment SDK，`PaymentService` 中实现Payment宝Payment能力 [API/Common/Services/PaymentService.cs:9] |
| .Cryptography | 库 | 加密算法库，用于Payment回调验签、敏感数据加解密 |
| Microsoft.SemanticKernel | 库 | AI 编排框架，用于 Agent 能力集成 |
| LangChain.Providers.OpenAI | 库 | LangChain 的 OpenAI 提供程序，用于 LLM 调用 |
| My.Extensions.Localization.Json | 库 | JSON 本地化扩展，用于多语言资源管理 |
| Microsoft.VisualStudio.Azure.Containers.Tools.Targets | 工具 | 容器化构建支持工具 |

 | JSON 本地化扩展，用于多语言资源管理 |
| Microsoft.VisualStudio.Azure.Containers.Tools.Targets | 工具 | 容器化构建支持工具 |

#### 10.2.2. Python Agent 服务技术栈

| 技术栈 | 版本/类型 | 用途说明 |
|--------|-----------|----------|
| FastAPI | 框架 | Agent Service HTTP 框架，提供 OpenAI 兼容的聊天补全接口 [Agents/server.py:chat_completions] |
| agentinsight-sdk | SDK | AgentInsight 官方 Python SDK，用于与后端 API 交互 |
| openai | 库 | OpenAI Python 客户端，用于 LLM 调用 |
| httpx | 库 | HTTP 客户端，用于异步请求 |
| pydantic | 库 | 数据验证与设置管理 |
| pydantic-settings | 库 | 基于 pydantic 的Config管理，`Agents/common/config.py` 中定义 `Environment` 枚举（/STAGING/）[Agents/common/config.py:15] |

#### 10.2.3. 基础设施依赖

| 组件 | 用途 |
|------|------|
| PostgreSQL | 主数据库，UserDb、DataDb、TraceTrackingDb |
| ClickHouse | 列式分析数据库，存储 Trace/Observation/Score 等可Observation性数据 |
| Redis | 缓存与消息队列（BullMQ 基于 Redis 实现） |

### 10.3. Config文件清单

AgentInsightService 的Config采用环境变量占位符与 JSON Config文件相结合的方式。`` 指定了Config扫描目录为 `Configurations` 与 `Resources`。以下表格列出了系统运行所需的核心Config项。

#### 10.3.1. 核心Config项

| Config键 | 示例值 | 说明 |
|--------|--------|------|
| `` | `${}` | AES 加密密钥，从环境变量 `` 读取，用于敏感数据加解密 |
| `` | `*` | 允许访问的主机列表 |
| `` | `${}` |  Service ID，从环境变量读取 |
| `` | `${}` |  服务密钥，从环境变量读取 |
| `` | `['Configurations', 'Resources']` | Config文件扫描目录列表 |

#### 10.3.2. CaptchaCaptchaSetting

| Config键 | 值 | 说明 |
|--------|-----|------|
| `CaptchaSetting.` | `5` | 图形Captcha长度 |
| `CaptchaSetting.` | `6` | 邮箱Captcha长度 |
| `CaptchaSetting.SMSCodeLength` | `6` | 短信Captcha长度 |
| `CaptchaSetting.` | `300` | Captcha有效期（秒） |
| `CaptchaSetting.ResendInterval` | `60` | Captcha重发间隔（秒） |

#### 10.3.3. 数据库连接字符串

| Config键 | 格式说明 |
|--------|----------|
| `.UserDbConnection` | `PORT=${USER_DB_PORT};=${USER_DB_NAME};=postgres;=${USER_DB_PASSWORD};USER ID=${USER_DB_USER};Timeout=60;Pooling=true;=10;=200;=300;...` |
| `.` | `PORT=${};=${};=postgres;=${};USER ID=${};Timeout=60;Pooling=true;=10;=200;=300;...` |
| `.TrackingDbConnection` | `PORT=${TRACKING_DB_PORT};=${TRACKING_DB_NAME};=postgres;=${TRACKING_DB_PASSWORD};USER ID=${TRACKING_DB_USER};Timeout=60;Pooling=true;=10;=200;=300;...` |
| `.` | `Host=${};Port=${};Username=${};Password=${};Database=${};=10;=50;=30;=60` |

#### 10.3.4. JWT 与安全参数

| Config键 | 说明 |
|--------|------|
| JWT 签名算法 | HS256 |
| JWT 过期时间 | 由Config文件指定，用于控制登录态有效期 |
| API Key 认证 | `AgentInsightTransformProvider` 中实现 API Key 验证，无效 Key 返回 ``（errorCode=100038）[API/System/Handlers/AgentInsightTransformProvider.cs:9, Models/Common/Enums/ExceptionCodes.cs:100038] |

#### 10.3.5. Payment相关Config

| Config键 | 说明 |
|--------|------|
| 微信Payment参数 | 包含 JSAPI/Native/MiniProgram 三种Payment方式的商户参数 |
| Payment宝Payment参数 | 包含应用 ID、私钥、Payment宝公钥等参数，由 `.Standard` 使用 |
| Payment回调地址 | 微信/Payment宝异步通知的接收地址，由 `NotifyHandler` 处理 [API/Handlers/PaymentManagement/NotifyHandler.cs:9] |

### 10.4. 枚举定义参考

本节列出了 AgentInsightService 代码仓库中定义的枚举类型，供开发与运维人员在ConfigAlert规则、处理异常、识别环境等场景下参考。

#### 10.4.1. Alert相关枚举

`AlertField` 枚举定义Alert规则可监控的指标字段，`` 枚举定义Alert条件比较操作符。定义位于 `Models/Common/Enums/AlertEnum.cs` [Models/Common/Enums/AlertEnum.cs:3-39]。

**AlertField 枚举**

| 枚举值 | 数值 | 说明 |
|--------|------|------|
| TotalTokens | 1 | Token 总消耗量 |
| TotalCost | 2 | 总成本 |
| ObservationCount | 9 | Observation 数量 |

** 枚举**

| 枚举值 | 数值 | 说明 |
|--------|------|------|
|  | 1 | 大于 |
|  | 6 | 不等于 |

#### 10.4.2. 队列类型枚举

`QueueType` 枚举定义消息队列的任务类型，位于 `Entities/Common/Enums/QueueEnum.cs` [Entities/Common/Enums/QueueEnum.cs:3]。

| 枚举值 | 数值 | 说明 |
|--------|------|------|
| Audit | 0 | 审计任务 |
| ExceptionRecord | 1 | 异常记录任务 |
| UsageTracking | 2 | 用量Trace任务 |
| PerformanceRecord | 3 | 性能记录任务 |

|
| ExceptionRecord | 1 | 异常记录任务 |
| UsageTracking | 2 | 用量Trace任务 |
| PerformanceRecord | 3 | 性能记录任务 |

#### 10.4.3. 路由类型枚举

`RouteType` 枚举定义 API 路由的访问类型，位于 `API/System/Handlers/AgentInsightTransformLogic.cs` [API/System/Handlers/AgentInsightTransformLogic.cs:72]。

| 枚举值 | 数值 | 说明 |
|--------|------|------|
| None | 0 | 未分类路由 |
| Public | 1 | 公开路由 |
| PublicApi | 2 | 公开 API 路由 |

#### 10.4.4. 环境枚举

`Environment` 枚举定义 Python Agent 服务的运行环境，位于 `Agents/common/config.py` [Agents/common/config.py:15]。

| 枚举值 | 值 | 说明 |
|--------|-----|------|
|  | `development` | 开发环境 |
| STAGING | `staging` | 预发布环境 |
|  | `production` | 生产环境 |

#### 10.4.5. 检索器类型枚举

`RetrieverType` 枚举定义 Agent 的检索器类型，位于 `Agents/common/retriever.py` [Agents/common/retriever.py:54]。

| 枚举值 | 值 | 说明 |
|--------|-----|------|
|  | `bm25` |  关键词检索 |
| VECTOR | `vector` | 向量检索 |
|  | `custom_service` | 自定义服务检索 |

#### 10.4.6. 交易类型枚举

`TransactionType` 枚举定义Payment交易类型，位于 `API/Notifications/PaymentTransactionNotification.cs` [API/Notifications/PaymentTransactionNotification.cs:9]。

| 枚举值 | 说明 |
|--------|------|
| WeChatTransaction | 微信Payment交易 |
| AlipayTransaction | Payment宝Payment交易 |

#### 10.4.7. 短信实例枚举

`SMSInstance` 枚举定义短信服务实例，位于 `Entities/Common/Settings/SMSSetting.cs` [Entities/Common/Settings/SMSSetting.cs:35]。

| 枚举值 | 数值 | 说明 |
|--------|------|------|
| None | 0 | 无短信实例 |

#### 10.4.8. 异常码枚举

`ExceptionCodes` 枚举定义系统全局异常码。以下为部分关键异常码：

| 常量名 | 数值 | 说明 |
|--------|------|------|
|  | 100038 | API Key 无效 |
|  | 130001 | 组织无效 |
|  | 130002 | 组织名称超长 |
|  | - | 用户不拥有任何组织 |
| UnauthorizedOrganizationAccess | - | 未授权的组织访问 |
| ProductNotExist | - | 产品不存在 |
| ProductDurationNotExist | - | 产品时长不存在 |
|  | - | Agent 报表模板不存在 |
|  | - | Agent 报表模板名称为空 |

> 注：`ExceptionCodes` 完整列表定义于 `Models/Common/Enums/ExceptionCodes.cs`，上述仅列出与本附录关键点相关的部分。

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

### 公开代理路径 (由 /api/public catch-all 推导)

- `/api/public`
- `/api/public/health`
- `/api/public/organizations`
- `/api/public/organizations/{org_id}/traces`
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

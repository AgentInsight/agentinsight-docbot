## 1. 引言

AgentInsightService 是一个面向 AI Agent 可Observation性与Payment管理的后端服务系统，系统分为 AI Agent 可Observation性域与商业化Payment管理两大核心域。可Observation性平台提供 Trace、Observation、Score 等可Observation性数据的采集、存储与查询能力，支持自定义 Alert Alert规则（基于 Token 消耗、延迟、错误率等指标），并通过 Agent Config、Agent Session 管理、Report AgentReport等功能支撑 AI Agent 的全生命周期管理。Payment管理域提供产品目录、订单管理、微信Payment/Payment宝Payment集成、Payment回调验证与OrgPrivilege（组织特权）更新等商业化能力，支撑系统的订阅制商业模式。系统采用 .NET 与 Python 混合技术栈，后端 API 基于 Furion 框架构建，AI Agent 服务基于 Python 实现 OpenAI 兼容接口。

### 1.1. 编写目的与目标读者

本文档面向 AgentInsightService 的完整技术说明，旨在为参与系统设计、开发、测试、部署与运维的各角色提供统一、准确、可追溯的参考依据。文档内容覆盖系统架构、功能需求、接口规格、数据模型、部署Config与测试策略，确保各团队在开发与协作过程中对系统行为有一致的理解。

目标读者包括：

| Role | 关注重点 | 典型使用场景 |
|------|----------|--------------|
| 开发团队 | 接口定义、业务逻辑、技术栈约束、代码结构 | 功能开发、缺陷修复、代码评审 |
| 测试团队 | 功能需求、验收标准、错误码、接口契约 | 测试用例设计、自动化测试、回归验证 |
| 产品经理 | 产品定位、功能范围、用户故事、业务规则 | 需求评审、版本规划、优先级决策 |
| 架构师 | 系统架构、模块划分、依赖关系、技术选型 | 架构评审、技术决策、性能优化 |

### 1.2. 产品背景与业务痛点

随着 AI Agent 应用从原型验证走向生产部署，开发团队面临三大核心挑战：

**可Observation性缺失**。AI Agent 应用涉及模型调用、工具调用、知识检索等多环节，任一环节的性能异常（Token 消耗激增、延迟升高、错误率上升）都可能影响用户体验。传统 [已移除幻觉符号] 工具无法覆盖 LLM 调用链路的语义信息，团队难以定位性能瓶颈。AgentInsightService 通过 Trace、Observation、Score 三级数据模型，完整记录 Agent 调用的全链路指标，并提供多维度过滤、排序、分页查询能力（`API/Handlers/DataManagement/MetricsHandler.cs:[已移除幻觉符号]`），帮助开发者快速定位问题。

**Alert能力不足**。AI 应用的成本与性能指标（Token 消耗、调用延迟、错误率）波动剧烈，需要实时监控与主动Alert。AgentInsightService 支持基于 AlertField（如 TotalTokens、TotalCost、ErrorCount、Latency）的自定义Alert规则（`API/Common/Services/AlertService.cs:IsConditionMet`），通过定时任务评估指标并触发通知，帮助团队在问题影响用户之前介入处理。

**商业化闭环缺失**。AI Agent 服务需要完整的订阅、计费与Payment能力。AgentInsightService 提供产品目录管理、订单创建、微信Payment（Native、JSAPI、MiniProgram）与Payment宝Payment集成（`API/Common/Services/PaymentService.cs:GetNativeResponse`、`GetAlipayInstantTrade`），Payment成功后自动更新OrgPrivilege（组织特权），实现从开通到使用的完整商业化闭环。

### 1.3. 文档范围

本文档覆盖 AgentInsightService 的以下范围：

**In-Scope**：

- 系统总体架构与模块划分（API 主项目、Agents 子项目、UnitTest/Utility/Tools 子项目）
- 用户与组织管理：注册、登录、成员邀请、角色分配、API Key 管理
- AI Agent 可Observation性：Trace、Observation、Score 数据查询，Alert Alert规则管理与记录查询
- Agent 生命周期管理：Agent Config CRUD、Agent Session 管理、Report AgentReport管理
- Payment与商业化：产品目录、订单管理、微信Payment/Payment宝Payment集成、Payment回调处理、OrgPrivilege（组织特权）更新
- AI Agent Service：OpenAI 兼容 Chat Completions API、多 Agent 支持、Session持久化、流式响应
- 系统基础设施：认证授权（JWT 与 API Key）、消息队列、健康检查、Config管理

**Out-of-Scope**：

- 前端 Web 聊天界面（`Agents/server.py` 中的 HTML 页面）仅作为 Agent 服务的演示界面，非核心功能需求
- 移动端应用、桌面客户端
- 第三方平台（微信、Payment宝）的商户后台Config操作
- 数据仓库的 [已移除幻觉符号] 管道与 BI 报表设计

### 1.4. 术语与缩略语

| 术语 | 说明 |
|------|------|
| Agent | AI Agent，系统管理的核心实体，支持 Insight、Researcher、CustomService 等多类型 |
| Trace | 一次 Agent 调用的完整链路Trace记录，包含调用时间、Token 消耗、延迟等指标 |
| Observation | Trace 中的单个Observation点，记录模型调用、工具调用等子步骤的详细信息 |
| Score | 对 Agent 调用质量的Score数据，用于评估模型输出质量 |
| Alert | Alert规则，基于 Token 消耗、延迟、错误率等指标的自定义阈值Alert |
| Organization | Org，系统的多租户隔离单元，包含成员、Project、订单等资源 |
| Project | Project，隶属于组织，用于隔离 Trace 数据与模型Config |
| API Key | 访问密钥，由 publicKey 与 secretKey 组成，用于 Basic Auth 认证 |
| JWT | JSON Web Token，系统签发的访问Token，支持刷新机制 |
| SSE | Server-Sent Events，服务器推送事件流，用于流式响应 |
| ClickHouse | 列式分析数据库，用于存储与查询 Trace Metrics 数据 |
| BullMQ | 基于 Redis 的消息队列模式，系统通过 BullMqService 实现异步任务 |

### 1.5. 参考文档

| 文档名称 | 说明 |
|----------|------|
| 系统架构设计文档 | 描述系统整体架构、模块划分、技术选型与部署拓扑 |
| API 接口文档 | 描述全部 HTTP 端点的请求参数、响应格式与错误码 |
| 数据库设计文档 | 描述 PostgreSQL 与 ClickHouse 的表结构、索引与数据流 |
| 部署运维手册 | 描述环境变量Config、容器化部署、健康检查与监控Alert |
| 测试策略文档 | 描述单元测试、集成测试、端到端测试的策略与用例设计 |
| 第三方集成指南 | 描述微信Payment、Payment宝Payment、微信消息等第三方平台集成说明 |

### 1.6. 版本历史

| 版本 | 日期 | 修订说明 | 作者 |
|------|------|----------|------|
| v0.1 | 2025-01-15 | 初始草案，完成文档大纲与产品定位描述 | 技术文档组 |
| v0.2 | 2025-02-01 | 补充功能需求框架、用户故事与验收标准 | 技术文档组 |
| v0.3 | 2025-02-15 | 完成 API 端点清单、错误码表与数据模型初稿 | 技术文档组 |
| v0.4 | 2025-03-01 | 集成代码仓库学习摘要，补充模块清单与依赖关系 | 技术文档组 |
| v0.5 | 2025-03-15 | 完成架构决策记录、部署Config与测试策略章节 | 技术文档组 |
| v1.0 | 2025-04-01 | 全量评审通过，发布正式版本 | 技术文档组 |

---

## 2. 产品概述与用户分析

户的**后端服务平台**，核心解决两类问题：一是 AI Agent 运行过程中的可Observation性数据（Trace、Observation、Score）的采集、存储、查询与Alert；二是围绕订阅产品的Payment闭环管理。

从系统架构看，AgentInsightService 由多个职责清晰的 Handler 层与 Service 层组成。`API/Handlers/DataManagement/MetricsHandler.cs` 负责可Observation性数据查询，提供 Trace 列表查询（支持多维度过滤、排序、分页）、Observation 查询、Score 查询；`API/Common/Services/AlertService.cs` 负责Alert条件评估与Alert消息构建；`API/Common/Services/PaymentService.cs` 承担Payment核心服务，包括订单创建、微信Payment/Payment宝Payment、Payment回调验证、订单状态更新与OrgPrivilege（组织特权）更新。`API/System/Handlers/AgentInsightTransformProvider.cs` 负责请求认证与路由，支持 JWT 认证与 API Key 认证。`API/Common/Services/BullMqService.cs` 基于 Redis 实现消息队列服务，支持 Trace 数据摄入与项目删除等异步任务。

系统采用多数据库架构：用户库（[已移除幻觉符号]）、数据库（[已移除幻觉符号]）、Trace库（[已移除幻觉符号]）与 ClickHouse 列式存储（[已移除幻觉符号]）分别承载不同数据类型，其中 ClickHouse 用于可Observation性数据的聚合查询，PostgreSQL（Npgsql）用于业务数据持久化。

### 2.1. 价值主张

AgentInsightService 的核心价值主张围绕三个维度展开：

**第一，为 AI 应用开发者提供统一的 Trace 数据查询与Alert能力。** 开发者通过 `API/Handlers/DataManagement/MetricsHandler.cs` 提供的查询接口，可按多维度过滤条件检索 Trace 数据，分析模型调用性能与 Token 消耗。同时，`API/Common/Services/AlertService.cs` 支持基于 TotalTokens、TotalCost、ErrorCount、Latency 等 AlertField 的Alert条件评估，当指标超过阈值时通过系统通知或短信通知及时触达用户。

**第二，集成微信Payment/Payment宝Payment实现订阅管理闭环。** `API/Common/Services/PaymentService.cs` 提供微信Payment（Native、JSAPI、MiniProgram）与Payment宝Payment能力，`API/Handlers/PaymentManagement/NotifyHandler.cs` 处理Payment回调验证，Payment成功后通过 `UpdateOrgPrivilege` 自动更新OrgPrivilege（组织特权），实现从下单、Payment到特权生效的全自动流程。

**第三，通过 Agent Config/Session/Report 支持 Agent 全生命周期管理。** `API/Handlers/AgentManagement/AgentConfigHandler.cs` 提供 Agent Config的创建、查询与删除；`API/Handlers/AgentManagement/AgentSessionHandler.cs` 管理Session的创建、更新与删除；`API/Handlers/AgentManagement/AgentReportHandler.cs` 管理 Report AgentReport。三者共同支撑 Agent 从初始化Config、运行Session到生成报告的全生命周期。

### 2.2. 北极星指标

AgentInsightService 的北极星指标为**可Observation数据查询成功率**与**Payment订单转化率**。

可Observation数据查询成功率衡量系统核心能力的可靠性。该指标覆盖 `API/Handlers/DataManagement/MetricsHandler.cs` 中 Trace、Observation、Score 三类查询接口的请求成功率，以及 `API/Common/Services/ClickHouseClient` 的查询稳定性。查询成功率直接反映用户能否及时获取 AI Agent 运行的可Observation性数据，是平台价值的核心度量。

Payment订单转化率衡量订阅商业闭环的效率。该指标覆盖 `API/Handlers/PaymentManagement/OrderHandler.cs` 的订单创建到Payment回调完成的完整链路，涉及微信Payment与Payment宝两条Payment通道。转化率反映用户从浏览产品、下单到完成Payment的转化效果，直接关联系统商业收入。

两个北极星指标分别对应系统的两大核心域，共同衡量 AgentInsightService 的整体健康度。

### 2.3. Persona 矩阵

AgentInsightService 面向三类核心用户角色，各自拥有不同的Privilege范围与操作场景。

| Persona | 角色定义 | 认证方式 | 核心操作 | 关联代码模块 |
|---------|---------|---------|---------|-------------|
| 普通用户 | AI 应用开发者，通过 API 访问平台数据 | API Key（Basic Auth）或 JWT | 管理 Organization、Project、ApiKey；查看 Trace 数据与Alert记录；购买订阅产品 | `API/Handlers/UserManagement/UserHandler.cs`、`API/Handlers/DataManagement/MetricsHandler.cs`、`API/Handlers/PaymentManagement/OrderHandler.cs` |
| 组织管理员/所有者 | 组织级管理者，负责成员与资源Config | JWT | 管理组织成员、角色分配、邀请成员；Config Agent 与Alert规则；查看组织级可Observation性数据 | `API/Handlers/UserManagement/OrganizationHandler.cs`、`API/Handlers/UserManagement/AlertHandler.cs`、`API/Handlers/AgentManagement/AgentConfigHandler.cs` |
| 系统管理员 | 平台运维人员，负责全局Config | Admin 后台（Django 管理界面） | 管理 Bulletin、产品Config等全局资源；审批Bulletin | `API/Handlers/ToolsManagement/BulletinHandler.cs`、`API/Handlers/ProductManagement/ProductHandler.cs` |

PI/Handlers/ToolsManagement/BulletinHandler.cs`、`API/Handlers/ProductManagement/ProductHandler.cs` |

普通用户通过 `API/System/Handlers/AgentInsightTransformProvider.cs` 完成请求认证与路由分发，该模块支持 JWT 认证与 API Key 认证两种方式。组织管理员通过 `API/Handlers/UserManagement/UserHandler.cs` 中的 `InviteMember`、`AssignRole` 方法管理组织成员与角色。系统管理员通过 `API/Handlers/ToolsManagement/BulletinHandler.cs` 管理Bulletin的创建、审批、修订与关闭。

### 2.4. 用户旅程

**旅程一：AI 应用开发者查询 Trace 数据并设置Alert**

1. **登录认证**：开发者通过 JWT 或 API Key 完成认证，`API/System/Handlers/AgentInsightTransformProvider.cs` 负责解析用户身份并建立Session上下文。
2. **创建 Project**：开发者调用 `API/Controllers/UserManagement/ProjectController.cs` 中的 `POST /api/user/project` 接口创建 Project，`API/Handlers/UserManagement/ProjectHandler.cs` 执行创建逻辑。
3. **查询 Trace Metrics**：开发者调用 `API/Controllers/DataManagement/MetricsController.cs` 中的 `GET /api/data/metrics/traces` 接口，`API/Handlers/DataManagement/MetricsHandler.cs` 通过 `TraceFilterBuilder.BuildFilters` 构建过滤条件，再经由 `ClickHouseClient.QueryAsync` 从 ClickHouse 查询聚合数据。
4. **设置Alert规则**：开发者调用 `API/Handlers/UserManagement/AlertHandler.cs` 中的 `CreateAlert` 创建Alert规则，指定 AlertField（如 TotalTokens）与阈值条件。
5. **收到系统通知**：当指标超过阈值时，`API/Common/Services/AlertService.cs` 评估Alert条件，`API/Notifications/SystemAlertHandler.cs` 生成系统通知，开发者可在Alert记录中查看。

**旅程二：用户购买订阅产品并自动更新OrgPrivilege（组织特权）**

1. **浏览产品**：用户调用 `API/Controllers/ProductManagement/ProductController.cs` 中的 `GET /api/product` 获取产品列表，`API/Handlers/ProductManagement/ProductHandler.cs` 从数据库查询 `AgentInsightProduct` 与 `AgentInsightProductDuration`。
2. **创建订单**：用户调用 `API/Handlers/PaymentManagement/OrderHandler.cs` 中的 `PlaceOrder` 创建订单，系统根据产品类型（Monthly/Permanent）与时长计算价格。
3. **发起Payment**：系统根据Payment渠道调用 `API/Common/Services/PaymentService.cs` 中的 `GetNativeResponse`（微信 Native）、`GetWeChatJSAPIResponse`（微信 JSAPI）或 `GetAlipayInstantTrade`（Payment宝），返回Payment参数。
4. **Payment回调处理**：Payment完成后，`API/Handlers/PaymentManagement/NotifyHandler.cs` 中的 `ProcessWeChatNotify` 或 `ProcessAlipayNotify` 验证回调签名，调用 `PaymentService.UpdateOrderState` 更新订单状态。
5. **OrgPrivilege（组织特权）自动更新**：订单状态更新成功后，`PaymentService.UpdateOrgPrivilege` 根据订单内容更新 `OrgPrivilege`，`API/Common/Services/IUserService.cs` 中的 `GetOrgPrivilegeAsync` 与 `UpdateOrgPrivilegeAsync` 负责特权的读取与持久化，用户组织即刻获得对应产品权益。

---

## 3. 功能需求

### 3.1. 用户认证与管理

#### 3.1.1. FR-001 用户注册与Captcha发送 [优先级: Must]
- **用户故事**: 作为未注册用户，我希望通过手机号注册账号，以便使用系统服务。
- **主流程**:
  1. 用户调用 `POST /api/user/register`，请求体包含 `mobile`、`password`、`captchaid`、`captchacode` 字段
  2. 系统校验Captcha，若Captcha为空抛出 `EmptyCaptcha = 110002` 异常
  3. Captcha校验通过后，系统创建用户账号
  4. 创建失败时抛出 `CreateUserFailed = 100001` 异常
- **验收标准**:
  - [ ] AC1: 注册成功时返回 `errorCode=0`，响应体包含用户 `id`、`mobile` 字段
  - [ ] AC2: Captcha为空时返回 `errorCode=110002`（`EmptyCaptcha`）
  - [ ] AC3: 注册失败时返回 `errorCode=100001`（`CreateUserFailed`）
- **业务规则**:
  - BR-001: 图片Captcha有效期 300 秒（`CaptchaSetting.ExpireTime = 300`）
  - BR-002: 同一手机号Captcha重发间隔为 60 秒（`CaptchaSetting.ResendInterval = 60`）

#### 3.1.2. FR-002 用户登录 [优先级: Must]
- **用户故事**: 作为注册用户，我希望通过密码/短信/微信/API Key 方式登录，以便获取 JWT Token 访问受保护资源。
- **主流程**:
  1. 用户调用 `POST /api/user/login`，请求体包含 `mobile`、`password`、`logintype` 字段（1=密码，2=短信，3=微信，4=小程序，5=APIKey）[API/Controllers/UserManagement/UserController.cs:57-L66]
  2. `UserController.Login` 委托 `UserHandler.Login` 执行认证逻辑 [API/Controllers/UserManagement/UserController.cs:61-L65]
  3. 系统验证用户凭据，若凭据无效抛出 `InvalidCredentials = 100037` 异常
  4. 登录成功后，系统签发 JWT Token 并写入响应头 `access-token`
- **验收标准**:
  - [ ] AC1: 登录成功时返回 `errorCode=0`，响应头包含 `access-token`，响应体包含 `token`、`refreshtoken`、`sessionid` 字段
  - [ ] AC2: 凭据无效时返回 `errorCode=100037`（`InvalidCredentials`）
  - [ ] AC3: `logintype=5`（API Key）时，请求需在 Authorization 头携带 `Basic publickey:secretkey`
- **业务规则**:
  - BR-003: 登录成功后调用 `UserService.LogUserSession` 记录用户Session [API/Handlers/UserManagement/UserHandler.cs:Login -> UserService.LogUserSession]
  - BR-004: JWT Token 刷新通过 `UserService.CreateRefreshTokenAndSetHttpContext` 实现

#### 3.1.3. FR-003 用户登出 [优先级: Should]
- **用户故事**: 作为已登录用户，我希望登出系统，以便安全结束当前Session。
- **主流程**:
  1. 用户调用 `POST /api/user/logout` [API/Controllers/UserManagement/UserController.cs:73-L80]
  2. `UserController.Logout` 委托 `UserHandler.Logout` 清除Session状态 [API/Controllers/UserManagement/UserController.cs:77-L79]
- **验收标准**:
  - [ ] AC1: 登出成功时返回 `errorCode=0`，响应体 `data` 为 `null`
  - [ ] AC2: 未认证用户调用登出接口返回 `errorCode=100000`（`Unauthorized`）
- **业务规则**:
  - BR-005: 登出操作需携带有效 JWT Token

#### 3.1.4. FR-004 获取用户信息 [优先级: Should]
- **用户故事**: 作为已登录用户，我希望获取当前用户信息，以便查看个人资料。
- **主流程**:
  1. 用户调用 `GET /api/user` [API/Controllers/UserManagement/UserController.cs:24-L33]
  2. `UserController.Get` 委托 `UserHandler.GetUser` 查询用户信息 [API/Controllers/UserManagement/UserController.cs:28-L32]
- **验收标准**:
  - [ ] AC1: 返回 `errorCode=0`，响应体包含 `id`、`name`、`mobile`、`image`、`createdat`、`updatedat`、`isadmin`、`openid` 字段
  - [ ] AC2: 未认证用户返回 `errorCode=100000`（`Unauthorized`）
- **业务规则**:
  - BR-006: 用户信息通过 `ApiControllerBase.GetUserAsync` 从缓存获取，缓存键为 `CacheConst.UserInfoById` [API/Controllers/ApiControllerBase.cs:36-L48]

#### 3.1.5. FR-005 更新用户信息 [优先级: Should]
- **用户故事**: 作为已登录用户，我希望更新用户名和头像，以便维护个人资料。
- **主流程**:
  1. 用户调用 `POST /api/user/update`，请求体包含 `name`、`image` 字段 [API/Controllers/UserManagement/UserController.cs:49-L56]
  2. `UserController.Update` 委托 `UserHandler.UpdateUser` 执行更新 [API/Controllers/UserManagement/UserController.cs:53-L55]
- **验收标准**:
  - [ ] AC1: 更新成功时返回 `errorCode=0`，响应体包含更新后的用户信息
  - [ ] AC2: 未认证用户返回 `errorCode=100000`（`Unauthorized`）
- **业务规则**:
  - BR-007: 更新操作仅允许修改 `name` 和 `image` 字段

#### 3.1.6. FR-006 重置密码 [优先级: Should]
- **用户故事**: 作为忘记密码的用户，我希望通过Captcha重置密码，以便重新获得账号访问Privilege。
- **主流程**:
  1. 用户调用 `POST /api/user/resetpassword`，请求体包含 `mobile`、`captchaid`、`captchacode`、`newpassword` 字段 [API/Controllers/UserManagement/UserController.cs:82-L90]
  2. `UserController.ResetPassword` 委托 `UserHandler.ResetPassword` 执行密码重置 [API/Controllers/UserManagement/UserController.cs:86-L89]
  3. 系统校验Captcha，若Captcha为空抛出 `EmptyCaptcha = 110002` 异常
  4. 密码重置失败时抛出 `ResetPasswordFailed = 100040` 异常
- **验收标准**:
  - [ ] AC1: 重置成功时返回 `errorCode=0`
  - [ ] AC2: Captcha为空时返回 `errorCode=110002`（`EmptyCaptcha`）
  - [ ] AC3: 重置失败时返回 `errorCode=100040`（`ResetPasswordFailed`）
- **业务规则**:
  - BR-008: 新密码需满足系统密码复杂度要求

#### 3.1.7. FR-007 获取图片Captcha [优先级: Must]
- **用户故事**: 作为未登录用户，我希望获取图片Captcha，以便完成注册或登录操作。
- **主流程**:
  1. 用户调用 `GET /api/captcha?mobile={mobile}` [API/Controllers/UserManagement/CaptchaController.cs:26-L34]
  2. `CaptchaController.Get` 委托 `CaptchaHandler.CreateCaptcha` 生成Captcha [API/Controllers/UserManagement/CaptchaController.cs:30-L33]
- **验收标准**:
  - [ ] AC1: 返回 `errorCode=0`，响应体包含 `id`（CaptchaID）和 `image`（Base64 图片）字段
  - [ ] AC2: Captcha长度为 5 位（`CaptchaSetting.Length = 5`）
- **业务规则**:
  - BR-009: Captcha有效期 300 秒（`CaptchaSetting.ExpireTime = 300`）
  - BR-010: 同一手机号 60 秒内仅可获取一次（`CaptchaSetting.ResendInterval = 60`）

#### 3.1.8. FR-008 获取短信Captcha [优先级: Must]
- **用户故事**: 作为未登录用户，我希望获取短信Captcha，以便通过手机号登录或注册。
- **主流程**:
  1. 用户调用 `GET /api/captcha/sms?phone={phone}` [API/Controllers/UserManagement/CaptchaController.cs:40-L48]
  2. `CaptchaController.GetSms` 委托 `CaptchaHandler.CreateSMSCaptcha` 发送短信 [API/Controllers/UserManagement/CaptchaController.cs:44-L47]
  3. 短信发送失败时抛出 `SMSSendFailed = 110001` 异常
- **验收标准**:
  - [ ] AC1: 发送成功时返回 `errorCode=0`
  - [ ] AC2: 短信发送失败时返回 `errorCode=110001`（`SMSSendFailed`）
  - [ ] AC3: 短信Captcha长度为 6 位（`CaptchaSetting.SMSLength = 6`）
- **业务规则**:
  - BR-011: 同一手机号 60 秒内仅可发送一次（`CaptchaSetting.ResendInterval = 60`）

#### 3.1.9. FR-009 微信绑定 [优先级: Must]
- **用户故事**: 作为微信用户，我希望将微信账号与系统账号绑定，以便通过微信快捷登录。
- **主流程**:
  1. 用户调用 `POST /api/user/bindwechat`，请求体包含 `openid`、`unionid`、`mobile` 等字段
  2. `UserHandler.BindWeChat` 执行微信绑定逻辑 [API/Handlers/UserManagement/UserHandler.cs:BindWeChat]
  3. 微信 `openid` 为空时抛出 `WeChatOpenIdEmpty = 620007` 异常
  4. 绑定失败时抛出 `WeChatBindFailed = 620009` 异常
- **验收标准**:
  - [ ] AC1: 绑定成功时返回 `errorCode=0`
  - [ ] AC2: 微信 `openid` 为空时返回 `errorCode=620007`（`WeChatOpenIdEmpty`）
  - [ ] AC3: 绑定失败时返回 `errorCode=620009`（`WeChatBindFailed`）
- **业务规则**:
  - BR-012: 微信绑定后可使用微信扫码或小程序方式登录

#### 3.1.10. FR-010 创建 API Key [优先级: Must]
- **用户故事**: 作为开发者用户，我希望创建 API Key，以便通过 API Key 认证方式访问系统 API。
- **主流程**:
  1. 用户调用 `POST /api/user/apikey`，请求体包含 API Key 名称
  2. `UserHandler.CreateApiKey` 执行 API Key 创建逻辑 [API/Handlers/UserManagement/UserHandler.cs:CreateApiKey]
  3. 创建失败时抛出 `CreateApiKeyFailed = 100032` 异常
- **验收标准**:
  - [ ] AC1: 创建成功时返回 `errorCode=0`，响应体包含 `publickey` 和 `secretkey` 字段
  - [ ] AC2: 创建失败时返回 `errorCode=100032`（`CreateApiKeyFailed`）
- **业务规则**:
  - BR-013: API Key 使用 Basic Auth 认证方式，格式为 `Basic publickey:secretkey`

#### 3.1.11. FR-011 查询 API Key 列表 [优先级: Should]
- **用户故事**: 作为开发者用户，我希望查询我的 API Key 列表，以便管理多个密钥。
- **主流程**:
  1. 用户调用 `GET /api/user/apikey`
  2. `UserHandler.GetApiKeys` 查询当前用户的 API Key 列表 [API/Handlers/UserManagement/UserHandler.cs:GetApiKeys]
- **验收标准**:
  - [ ] AC1: 返回 `errorCode=0`，响应体包含 API Key 列表
  - [ ] AC2: API Key 不存在时返回 `errorCode=100031`（`ApiKeyNotFound`）
- **业务规则**:
  - BR-014: API Key Secret 不随列表返回，仅返回 Public Key 信息

#### 3.1.12. FR-012 删除 API Key [优先级: Should]
- **用户故事**: 作为开发者用户，我希望删除不再使用的 API Key，以便确保密钥安全。
- **主流程**:
  1. 用户调用 `DELETE /api/user/apikey/{id}`
  2. `UserHandler.DeleteApiKey` 执行 API Key 删除 [API/Handlers/UserManagement/UserHandler.cs:DeleteApiKey]
  3. 删除失败时抛出 `DeleteApiKeyFailed = 100033` 异常
- **验收标准**:
  - [ ] AC1: 删除成功时返回 `errorCode=0`
  - [ ] AC2: 删除失败时返回 `errorCode=100033`（`DeleteApiKeyFailed`）
- **业务规则**:
  - BR-015: 删除操作仅允许删除当前用户拥有的 API Key

### 3.2. 组织与项目管理

#### 3.2.1. FR-013 创建组织 [优先级: Must]
- **用户故事**: 作为注册用户，我希望创建组织，以便在组织内管理项目和成员。
- **主流程**:
  1. 用户调用 `POST /api/user/organization` [API/Controllers/UserManagement/OrganizationController.cs:28-L35]
  2. `OrganizationController.Post` 委托 `OrganizationHandler.CreateOrganization` 创建组织 [API/Controllers/UserManagement/OrganizationController.cs:32-L34]
  3. 创建失败时抛出 `InvalidOrganization = 130004` 异常
- **验收标准**:
  - [ ] AC1: 创建成功时返回 `errorCode=0`，响应体包含组织 `id`、`name` 字段
  - [ ] AC2: 创建失败时返回 `errorCode=130004`（`InvalidOrganization`）
- **业务规则**:
  - BR-016: Owner

#### 3.2.2. FR-014 获取组织列表 [优先级: Must]
- **用户故事**: 作为组织成员，我希望获取我所属的组织列表，以便切换组织上下文。
- **主流程**:
  1. 用户调用 `GET /api/user/organization` [API/Controllers/UserManagement/OrganizationController.cs:42-L49]
  2. `OrganizationController.Get` 委托 `OrganizationHandler.GetOrganizations` 查询组织列表 [API/Controllers/UserManagement/OrganizationController.cs:46-L48]
- **验收标准**:
  - [ ] AC1: 返回 `errorCode=0`，响应体包含组织列表
  - [ ] AC2: 组织不存在时返回 `errorCode=130003`（`OrganizationNotFound`）
- **业务规则**:
  - BR-017: 仅返回当前用户所属的组织

#### 3.2.3. FR-015 更新组织信息 [优先级: Should]
- **用户故事**: 作为组织所有者，我希望更新组织名称和Config，以便维护组织信息。
- **主流程**:
  1. 用户调用 `POST /api/user/organization/update` [API/Controllers/UserManagement/OrganizationController.cs:56-L63]
  2. `OrganizationController.Update` 委托 `OrganizationHandler.UpdateOrganization` 执行更新 [API/Controllers/UserManagement/OrganizationController.cs:60-L62]
  3. 更新失败时抛出 `UpdateOrganizationFailed = 130005` 异常
- **验收标准**:
  - [ ] AC1: 更新成功时返回 `errorCode=0`
  - [ ] AC2: 更新失败时返回 `errorCode=130005`（`UpdateOrganizationFailed`）
- **业务规则**:
  - BR-018: 仅组织所有者或管理员可执行更新操作

#### 3.2.4. FR-016 删除组织 [优先级: Could]
- **用户故事**: 作为组织所有者，我希望删除组织，以便解散不再使用的组织。
- **主流程**:
  1. 用户调用 `DELETE /api/user/organization/{id}`
  2. `OrganizationHandler.DeleteOrganization` 执行组织删除 [API/Handlers/UserManagement/OrganizationHandler.cs:DeleteOrganization]
  3. 删除失败时抛出 `DeleteOrganizationFailed = 130006` 异常
- **验收标准**:
  - [ ] AC1: 删除成功时返回 `errorCode=0`
  - [ ] AC2: 删除失败时返回 `errorCode=130006`（`DeleteOrganizationFailed`）
- **业务规则**:
  - BR-019: 仅组织所有者可执行删除操作

#### 3.2.5. FR-017 创建项目 [优先级: Must]
- **用户故事**: 作为组织成员，我希望在组织内创建项目，以便隔离不同应用的 Trace 数据。
- **主流程**:
  1. 用户调用 `POST /api/user/project`，请求体包含 `orgid`、`name` 字段
  2. `ProjectHandler.CreateProject` 执行项目创建 [API/Handlers/UserManagement/ProjectHandler.cs:CreateProject]
  3. 创建失败时抛出 `CreateProjectFailed = 140004` 异常
- **验收标准**:
  - [ ] AC1: 创建成功时返回 `errorCode=0`，响应体包含项目 `id`、`name`、`orgid` 字段
  - [ ] AC2: 创建失败时返回 `errorCode=140004`（`CreateProjectFailed`）
- **业务规则**:
  - BR-020: 项目必须归属于一个有效组织

#### 3.2.6. FR-018 获取项目列表 [优先级: Must]
- **用户故事**: 作为组织成员，我希望获取组织下的项目列表，以便选择项目查看 Trace 数据。
- **主流程**:
  1. 用户调用 `GET /api/user/project?orgId={orgId}`
  2. `ProjectHandler.GetProjects` 查询项目列表 [API/Handlers/UserManagement/ProjectHandler.cs:GetProjects]
- **验收标准**:
  - [ ] AC1: 返回 `errorCode=0`，响应体包含项目列表及分页信息
  - [ ] AC2: 组织无效时返回 `errorCode=130003`（`OrganizationNotFound`）
- **业务规则**:
  - BR-021: 仅返回当前用户有Privilege访问的项目

#### 3.2.7. FR-019 更新项目 [优先级: Should]
- **用户故事**: 作为项目管理员，我希望更新项目名称，以便维护项目信息。
- **主流程**:
  1. 用户调用 `POST /api/user/project/update`
  2. `ProjectHandler.UpdateProject` 执行项目更新 [API/Handlers/UserManagement/ProjectHandler.cs:UpdateProject]
  3. 更新失败时抛出 `UpdateProjectFailed = 140005` 异常
- **验收标准**:
  - [ ] AC1: 更新成功时返回 `errorCode=0`
  - [ ] AC2: 更新失败时返回 `errorCode=140005`（`UpdateProjectFailed`）
- **业务规则**:
  - BR-022: 仅项目所属组织的管理员或所有者可更新

#### 3.2.8. FR-020 删除项目 [优先级: Should]
- **用户故事**: 作为项目管理员，我希望删除项目，以便清理不再使用的项目及其数据。
- **主流程**:
  1. 用户调用 `DELETE /api/user/project/{id}`
  2. `ProjectHandler.DeleteProject` 执行项目删除 [API/Handlers/UserManagement/ProjectHandler.cs:DeleteProject]
  3. 删除失败时抛出 `DeleteProjectFailed = 140006` 异常
  4. 系统通过 `BullMqService.EnqueueProjectDeleteAsync` 异步删除项目关联数据
- **验收标准**:
  - [ ] AC1: 删除成功时返回 `errorCode=0`
  - [ ] AC2: 删除失败时返回 `errorCode=140006`（`DeleteProjectFailed`）
- **业务规则**:
  - BR-023: 项目删除为异步操作，通过消息队列处理

#### 3.2.9. FR-021 邀请成员 [优先级: Should]
- **用户故事**: 作为组织所有者，我希望邀请新成员加入组织，以便协作管理项目。
- **主流程**:
  1. 用户调用 `POST /api/user/invite`，请求体包含 `orgid`、`mobile`、`role` 字段
  2. `UserHandler.InviteMember` 执行成员邀请 [API/Handlers/UserManagement/UserHandler.cs:InviteMember]
  3. 邀请创建失败时抛出 `CreateInvitationFailed = 100026` 异常
- **验收标准**:
  - [ ] AC1: 邀请成功时返回 `errorCode=0`
  - [ ] AC2: 邀请创建失败时返回 `errorCode=100026`（`CreateInvitationFailed`）
- **业务规则**:
  - BR-024: 仅组织所有者或管理员可邀请成员

#### 3.2.10. FR-022 获取邀请列表 [优先级: Should]
- **用户故事**: 作为组织成员，我希望查看待处理的邀请，以便确认是否加入组织。
- **主流程**:
  1. 用户调用 `GET /api/user/invitations`
  2. `UserHandler.GetInvitations` 查询邀请列表 [API/Handlers/UserManagement/UserHandler.cs:GetInvitations]
- **验收标准**:
  - [ ] AC1: 返回 `errorCode=0`，响应体包含邀请列表
- **业务规则**:
  - BR-025: 邀请列表包含待处理和已处理的邀请

#### 3.2.11. FR-023 删除邀请 [优先级: Could]
- **用户故事**: 作为组织所有者，我希望撤销已发送的邀请，以便纠正错误邀请。
- **主流程**:
  1. 用户调用 `DELETE /api/user/invitation/{id}`
  2. `UserHandler.DeleteInvitation` 执行邀请删除 [API/Handlers/UserManagement/UserHandler.cs:DeleteInvitation]
  3. 删除失败时抛出 `DeleteInvitationFailed = 100028` 异常
- **验收标准**:
  - [ ] AC1: 删除成功时返回 `errorCode=0`
  - [ ] AC2: 删除失败时返回 `errorCode=100028`（`DeleteInvitationFailed`）
- **业务规则**:
  - BR-026: 仅邀请发起者或组织所有者可撤销邀请

#### 3.2.12. FR-024 分配角色 [优先级: Should]
- **用户故事**: 作为组织所有者，我希望为成员分配角色，以便控制成员Privilege。
- **主流程**:
  1. 用户调用 `POST /api/user/assignrole`，请求体包含 `orgid`、`userid`、`role` 字段
  2. `UserHandler.AssignRole` 执行角色分配 [API/Handlers/UserManagement/UserHandler.cs:AssignRole]
  3. 所有者不能修改自身角色，否则抛出 `OwnerRoleChangeNotAllowed = 100039` 异常
- **验收标准**:
  - [ ] AC1: 分配成功时返回 `errorCode=0`
  - [ ] AC2: 所有者修改自身角色时返回 `errorCode=100039`（`OwnerRoleChangeNotAllowed`）
- **业务规则**:
  - BR-027: 角色分配仅允许组织所有者执行

### 3.3. 可Observation性数据查询

#### 3.3.1. FR-025 查询 Trace 列表 [优先级: Must]
- **用户故事**: 作为 AI 应用开发者，我希望查询 Trace 列表，以便分析模型调用链路性能。
- **主流程**:
  1. 用户调用 `GET /api/data/trace`，支持多维度过滤、排序、分页参数
  2. `MetricsHandler.GetTraces` 处理查询请求 [API/Handlers/DataManagement/MetricsHandler.cs:GetTraces]
  3. 系统通过 `TraceFilterBuilder.BuildFilters` 构建过滤条件 [API/Handlers/DataManagement/MetricsHandler.cs:GetTraces -> TraceFilterBuilder.BuildFilters]
  4. 系统通过 `ClickHouseClient.QueryAsync` 执行 ClickHouse 查询 [API/Handlers/DataManagement/MetricsHandler.cs:QueryTracesDataAsync -> ClickHouseClient.QueryAsync]
- **验收标准**:
  - [ ] AC1: 返回 `errorCode=0`，响应体包含 Trace 列表及分页信息
  - [ ] AC2: 支持按 `projectId`、`traceId`、`timestamp` 范围、`status` 等维度过滤
  - [ ] AC3: 支持按 `-timestamp`、`-duration` 等字段排序
- **业务规则**:
  - BR-028: 查询默认按 `-timestamp` 倒序排列
  - BR-029: 查询结果通过 ClickHouse 存储引擎获取

#### 3.3.2. FR-026 查询 Observation 列表 [优先级: Must]
- **用户故事**: 作为 AI 应用开发者，我希望查询 Observation 列表，以便查看模型调用的详细输入输出数据。
- **主流程**:
  1. 用户调用 `GET /api/data/observation`，支持按 `traceId`、`projectId` 过滤
  2. `MetricsHandler.GetObservationsAsync` 处理查询请求 [API/Handlers/DataManagement/MetricsHandler.cs:GetObservationsAsync]
- **验收标准**:
  - [ ] AC1: 返回 `errorCode=0`，响应体包含 Observation 列表
  - [ ] AC2: 支持按 `traceId`、`projectId` 过滤
- **业务规则**:
  - BR-030: Observation 数据仅对授权项目可见

#### 3.3.3. FR-027 查询 Score 列表 [优先级: Should]
- **用户故事**: 作为 AI 应用开发者，我希望查询 Score 列表，以便评估模型输出质量。
- **主流程**:
  1. 用户调用 `GET /api/data/score`，支持按 `traceId`、`projectId` 过滤
  2. `MetricsHandler.GetScoresAsync` 处理查询请求 [API/Handlers/DataManagement/MetricsHandler.cs:GetScoresAsync]
- **验收标准**:
  - [ ] AC1: 返回 `errorCode=0`，响应体包含 Score 列表
  - [ ] AC2: 支持按 `traceId`、`projectId` 过滤
- **业务规则**:
  - BR-031: Score 数据仅对授权项目可见

#### 3.3.4. FR-028 查询 Model 定义列表 [优先级: Should]
- **用户故事**: 作为 AI 应用开发者，我希望查询模型定义列表，以便了解可用模型及其价格Config。
- **主流程**:
  1. 用户调用 `GET /api/data/model`，支持 `keyword`、`projectid`、`includedpredefined`、`orderby` 参数 [API/Controllers/DataManagement/ModelController.cs:34-L42]
  2. `ModelController.Get` 委托 `ModelHandler.GetModels` 查询模型列表 [API/Controllers/DataManagement/ModelController.cs:38-L41]
- **验收标准**:
  - [ ] AC1: 返回 `errorCode=0`，响应体包含模型列表，含 `modelname`、`inputprice`、`outputprice`、`unit` 字段
  - [ ] AC2: `projectid` 为空且 `includedpredefined=false` 时返回错误，要求提供项目 ID
  - [ ] AC3: `includedpredefined=true` 时返回预定义模型（`projectid=null` 的模型）
- **业务规则**:
  - BR-032: 默认排序为 `-updatedat`（按更新时间倒序）
  - BR-033: 模型定义包含 `pricingtiers` 分层定价Config

### 3.4. Alert管理

#### 3.4.1. FR-029 获取AlertConfig [优先级: Must]
- **用户故事**: 作为组织管理员，我希望获取AlertConfig，以便了解当前Alert规则设置。
- **主流程**:
  1. 用户调用 `GET /api/alert/config` [API/Controllers/UserManagement/AlertController.cs:30-L37]
  2. `AlertController.GetConfig` 委托 `AlertHandler.GetConfig` 查询AlertConfig [API/Controllers/UserManagement/AlertController.cs:34-L36]
- **验收标准**:
  - [ ] AC1: 返回 `errorCode=0`，响应体包含AlertConfig信息
- **业务规则**:
  - BR-034: AlertConfig包含通知方式（系统通知/短信通知）设置

#### 3.4.2. FR-030 查询Alert规则列表 [优先级: Must]
- **用户故事**: 作为组织管理员，我希望查询Alert规则列表，以便查看已Config的Alert条件。
- **主流程**:
  1. 用户调用 `GET /api/alert` [API/Controllers/UserManagement/AlertController.cs:47-L54]
  2. `AlertController.Get` 委托 `AlertHandler.GetAlerts` 查询Alert规则 [API/Controllers/UserManagement/AlertController.cs:51-L53]
- **验收标准**:
  - [ ] AC1: 返回 `errorCode=0`，响应体包含Alert规则列表
  - [ ] AC2: Alert规则包含 `field`（AlertField）、`operator`（AlertOperator）、`threshold` 字段
- **业务规则**:
  - BR-035: `AlertField` 枚举包含 `ObservationCount = 9` 等指标字段 [Models/Common/Enums/AlertEnum.cs:20]

#### 3.4.3. FR-031 创建Alert规则 [优先级: Must]
- **用户故事**: 作为组织管理员，我希望创建Alert规则，以便在指标异常时收到通知。
- **主流程**:
  1. 用户调用 `POST /api/alert` [API/Controllers/UserManagement/AlertController.cs:61-L68]
  2. `AlertController.Create` 委托 `AlertHandler.CreateAlert` 创建Alert规则 [API/Controllers/UserManagement/AlertController.cs:65-L67]
- **验收标准**:
  - [ ] AC1: 创建成功时返回 `errorCode=0`，响应体包含Alert规则 `id`
  - [ ] AC2: Alert规则支持基于 `TotalTokens`、`TotalCost`、`ErrorCount`、`Latency` 等指标
- **业务规则**:
  - BR-036: Alert条件评估通过 `AlertService.EvaluateField` 和 `IsConditionMet` 实现 [API/Common/Services/AlertService.cs:EvaluateField、IsConditionMet]

#### 3.4.4. FR-032 更新Alert规则 [优先级: Should]
- **用户故事**: 作为组织管理员，我希望更新Alert规则，以便调整Alert阈值或条件。
- **主流程**:
  1. 用户调用 `POST /api/alert/update` [API/Controllers/UserManagement/AlertController.cs:75-L82]
  2. `AlertController.Update` 委托 `AlertHandler.UpdateAlert` 更新Alert规则 [API/Controllers/UserManagement/AlertController.cs:79-L81]
- **验收标准**:
  - [ ] AC1: 更新成功时返回 `errorCode=0`
- **业务规则**:
  - BR-037: 仅规则创建者或组织管理员可更新

#### 3.4.5. FR-033 删除Alert规则 [优先级: Should]
- **用户故事**: 作为组织管理员，我希望删除不再需要的Alert规则，以便减少无效通知。
- **主流程**:
  1. 用户调用 `POST /api/alert/delete` [API/Controllers/UserManagement/AlertController.cs:90-L97]
  2. `AlertController.Delete` 委托 `AlertHandler.DeleteAlerts` 删除Alert规则 [API/Controllers/UserManagement/AlertController.cs:94-L96]
- **验收标准**:
  - [ ] AC1: 删除成功时返回 `errorCode=0`
- **业务规则**:
  - BR-038: 支持批量删除多个Alert规则

#### 3.4.6. FR-034 查询Alert记录 [优先级: Must]
- **用户故事**: 作为组织成员，我希望查询Alert记录，以便了解历史Alert事件。
- **主流程**:
  1. 用户调用 `GET /api/alert/record` [API/Controllers/UserManagement/AlertController.cs:128-L135]
  2. `AlertController.GetRecords` 委托 `AlertHandler.GetAlertRecords` 查询Alert记录 [API/Controllers/UserManagement/AlertController.cs:132-L134]
- **验收标准**:
  - [ ] AC1: 返回 `errorCode=0`，响应体包含Alert记录列表
  - [ ] AC2: Alert记录包含 `state`（AlertState）字段
- **业务规则**:
  - BR-039: Alert记录状态由 `AlertState` 枚举定义 [Models/Common/Enums/AlertEnum.cs:33]

#### 3.4.7. FR-035 标记Alert记录已读 [优先级: Should]
- **用户故事**: 作为组织成员，我希望将Alert记录标记为已读，以便管理通知状态。
- **主流程**:
  1. 用户调用 `POST /api/alert/record/read` [API/Controllers/UserManagement/AlertController.cs:108-L115]
  2. `AlertController.ReadRecords` 委托 `AlertHandler.ReadAlertRecords` 标记已读 [API/Controllers/UserManagement/AlertController.cs:112-L114]
- **验收标准**:
  - [ ] AC1: 标记成功时返回 `errorCode=0`
- **业务规则**:
  - BR-040: 支持批量标记多条记录为已读

#### 3.4.8. FR-036 Alert条件评估与通知 [优先级: Must]
- **用户故事**: 作为组织管理员，我希望系统自动评估Alert条件并在触发时发送通知，以便及时响应异常。
- **主流程**:
  1. 系统通过 `AlertService.GetAlertMetrics` 获取指标数据 [API/Notifications/SystemAlertHandler.cs:Handle -> AlertService.GetAlertMetrics]
  2. `AlertService.IsConditionMet` 评估Alert条件是否满足 [API/Common/Services/AlertService.cs:IsConditionMet]
  3. 条件满足时，`AlertService.BuildAlertMessage` 构建Alert消息
  4. 通过 `SystemAlertHandler` 发送系统通知，通过 `SMSAlertHandler` 发送短信通知
- **验收标准**:
  - [ ] AC1: 指标超过阈值时生成Alert记录
  - [ ] AC2: 系统通知和短信通知均能正确发送
- **业务规则**:
  - BR-041: Alert通知方式由 `AlertNotifyType` 枚举定义 [Models/Common/Enums/AlertEnum.cs:39]
  - BR-042: Alert评估支持 `AlertTimeWindow` 时间窗口Config [Models/Common/Enums/AlertEnum.cs:3]

### 3.5. Payment管理

#### 3.5.1. FR-037 创建订单 [优先级: Must]
- **用户故事**: 作为用户，我希望创建Payment订单，以便购买订阅产品。
- **主流程**:
  1. 用户调用 `POST /api/payment/order`，请求体包含 `orgid`、`productid`、`productdurationid`、`paymethod`、`subpaymethod` 字段 [API/Controllers/PaymentManagement/OrderController.cs:39-L48]
  2. `OrderController.PlaceOrder` 委托 `OrderHandler.PlaceOrder` 创建订单 [API/Controllers/PaymentManagement/OrderController.cs:43-L47]
  3. 系统根据 `paymethod` 调用对应Payment服务生成Payment参数
  4. 创建失败时抛出 `CreateOrderFailed = 200001` 异常
- **验收标准**:
  - [ ] AC1: 创建成功时返回 `errorCode=0`，响应体包含订单 `id`、`orderNo`、Payment参数
  - [ ] AC2: 支持微信Payment（Native/JSAPI/小程序）和Payment宝Payment
  - [ ] AC3: 创建失败时返回 `errorCode=200001`（`CreateOrderFailed`）
- **业务规则**:
  - BR-043: 订单创建后状态为待Payment（

---

## 4. 非功能需求

AgentInsightService 作为 AI Agent 可Observation性域，提供 Trace、Observation、Score 等可Observation性数据的采集、存储与查询能力，并集成Payment宝与微信Payment实现订阅管理。NFR，涵盖性能、可用性、安全、可扩展性、可维护性、兼容性与本地化七个维度，为系统架构设计、部署运维与质量保障提供量化基准。所有 NFR 均以可验证的指标与目标值进行描述，编号规则为 NFR-[维度缩写]-[序号]（维度缩写为 P、A、S、SC、M、C、L，分别对应性能、可用性、安全、可扩展性、可维护性、兼容性与本地化），共计 24 条。

### 4.1. 性能

性能需求聚焦于可Observation性数据查询链路与Payment回调处理两大核心场景的响应时间与吞吐量。Trace 查询通过 `TraceFilterBuilder` 构建多维度过滤条件，支持按 ID、名称、时间范围及自定义条件组合过滤，并支持排序与分页 [API/Handlers/DataManagement/MetricsHandler.cs]。查询链路经由 `ClickHouseClient` 执行，连接池Config `MinPoolSize=10;MaxPoolSize=50;ConnectionIdleTimeout=30;ConnectionOpenTimeout=60`，确保高并发下的连接复用与超时控制。Observation 与 Score 查询同样基于 ClickHouse 存储，按 TraceId 过滤并分页返回 [API/Handlers/DataManagement/MetricsHandler.cs]。

| 编号 | Metric | 目标值 | 验证方式 |
|------|------|--------|----------|
| NFR-P-001 | 简单 Trace 查询接口响应时间（单条件过滤，无聚合） | P95 < 2s | 压测工具模拟 100 并发持续 10 分钟，统计 P95 响应时间 |
| NFR-P-002 | 复杂 Trace 查询接口响应时间（多维度过滤 + 聚合） | P95 < 5s | 压测工具模拟 50 并发，查询条件含 3 个以上过滤维度 |
| NFR-P-003 | Observation 查询接口响应时间（按 TraceId 分页查询） | P95 < 2s | 压测工具模拟 100 并发，pagesize=50 |
| NFR-P-004 | Score 查询接口响应时间（按 TraceId 分页查询） | P95 < 2s | 压测工具模拟 100 并发，pagesize=50 |
| NFR-P-005 | ClickHouse 连接池最大连接数 | MaxPoolSize=50 | Config检查，确认连接字符串包含 `MaxPoolSize=50` |
| NFR-P-006 | ClickHouse 查询超时时间 | 60s | Config检查，确认连接字符串包含 `ConnectionOpenTimeout=60`；超时返回 `ClickHouse` 错误码（150017） |
| NFR-P-007 | Payment回调处理响应时间（微信/Payment宝） | P95 < 3s | 模拟回调请求，统计从接收请求到返回结果的时间 |

### 4.2. 可用性

可用性需求保障系统在异常场景下的持续服务能力与数据一致性。Payment交易记录保存支持 3 次重试，微信Payment回调处理同样支持 3 次重试，确保网络抖动或第三方服务异常时交易数据不丢失。Payment回调接口 `WeChatNotify` 与 `AlipayNotify` 均捕获异常并返回失败标识，由Payment平台侧触发重试 [API/Controllers/PaymentManagement/NotifyController.cs]。系统提供健康检查接口，用于负载均衡与容器编排的存活探针 [API/Controllers/ToolsManagement/HealthController.cs:Get]。

| 编号 | Metric | 目标值 | 验证方式 |
|------|------|--------|----------|
| NFR-A-001 | Payment交易记录保存重试次数 | 3 次 | 代码审查，确认 `SaveWeChatTransaction`/`SaveAlipayTransaction` 调用路径包含 3 次重试逻辑 |
| NFR-A-002 | 微信Payment回调处理重试次数 | 3 次 | 代码审查，确认 `ProcessWeChatNotify` 异常时返回失败标识，由Payment平台重试 |
| NFR-A-003 | 系统可用性（月） | ≥ 99.9% | 监控系统统计月度可用时间占比 |
| NFR-A-004 | 健康检查接口可用性 | 始终可用，无需认证 | 接口测试，确认 `GET /api/tools/health` 返回 200 |
| NFR-A-005 | Payment回调接口幂等性 | 重复回调不产生重复订单更新 | 模拟重复回调请求，确认订单状态与 OrgPrivilege 仅更新一次 |

### 4.3. 安全

安全需求覆盖身份认证、数据加密、Payment签名验证与防刷机制。系统采用 JWT 认证（HS256 算法，过期时间 43200 秒）与 API Key 认证（Basic Auth）双通道鉴权，由 `AgentInsightTransformProvider` 统一处理请求认证与路由 [API/System/Handlers/AgentInsightTransformProvider.cs]。用户密码使用 AES 加密存储，加密密钥通过环境变量 `${AES_ENCRYPTION_KEY}` 注入。Payment回调验证采用微信 SHA256 签名与Payment宝 RSA 签名双重校验，防止伪造回调请求。Captcha服务Config 60 秒重发间隔与 300 秒过期时间，防止接口被恶意刷取。

| 编号 | Metric | 目标值 | 验证方式 |
|------|------|--------|----------|
| NFR-S-001 | JWT Token 过期时间 | 43200 秒（12 小时） | Config检查，确认 JWT 过期时间Config为 43200 |
| NFR-S-002 | JWT 签名算法 | HS256 | 代码审查，确认 JWT 签发与验证使用 HS256 |
| NFR-S-003 | 密码加密存储 | AES 加密，密钥来自 `${AES_ENCRYPTION_KEY}` | 代码审查，确认密码写入数据库前经 AES 加密 |
| NFR-S-004 | 微信Payment回调签名验证 | SHA256 签名验证 | 代码审查，确认 `ExamineWeChatRequest` 执行签名校验 |
| NFR-S-005 | Payment宝Payment回调签名验证 | RSA 签名验证 | 代码审查，确认 `ProcessAlipayNotify` 执行签名校验 |
| NFR-S-006 | Captcha重发间隔 | 60 秒 | Config检查，确认 `CaptchaSetting.ResendInterval=60` |
| NFR-S-007 | Captcha过期时间 | 300 秒 | Config检查，确认 `CaptchaSetting.ExpireTime=300` |
| NFR-S-008 | API Key 认证方式 | Basic Auth | 代码审查，确认 `AgentInsightTransformProvider` 支持 Basic Auth 解析 |

### 4.4. 可扩展性

可扩展性需求确保系统能够支撑大规模时序数据存储与异步任务处理。系统基于 ClickHouse 存储 Trace、Observation、Score 等时序数据，利用其列式存储与分布式查询能力支撑海量数据场景。异步任务通过 Redis 队列（`BullMqService`）处理，支持 Trace 数据摄入（`EnqueueTraceIngestionAsync`）与项目删除（`EnqueueProjectDeleteAsync`）等耗时操作，实现请求链路与数据处理解耦 [API/Common/Services/BullMqService.cs]。PostgreSQL 连接池Config `MinPoolSize=10;MaxPoolSize=200;ConnectionIdleTimeout=300`，支撑用户、Org、订单等关系型数据的并发访问。

| 编号 | Metric | 目标值 | 验证方式 |
|------|------|--------|----------|
| NFR-SC-001 | Trace 数据存储容量 | 单日 ≥ 1 亿条 Trace 记录 | 压测写入，确认 ClickHouse 集群吞吐与存储容量 |
| NFR-SC-002 | 异步任务队列吞吐量 | ≥ 1000 任务/秒 | 压测 `EnqueueTraceIngestionAsync`，统计 Redis 队列消费速率 |
| NFR-SC-003 | PostgreSQL 连接池最大连接数 | MaxPoolSize=200 | Config检查，确认连接字符串包含 `MaxPoolSize=200` |
| NFR-SC-004 | 异步任务类型支持 | Trace 数据摄入、项目删除 | 代码审查，确认 `BullMqService` 提供 `EnqueueTraceIngestionAsync` 与 `EnqueueProjectDeleteAsync` |
| NFR-SC-005 | 水平扩展能力 | ClickHouse 与 Redis 支持集群部署 | 架构审查，确认无单点瓶颈 |

### 4.5. 可维护性

可维护性需求保障系统的可Observation性、可诊断性与Config灵活性。系统采用结构化日志记录异常信息，关键路径（如Payment回调、ClickHouse 查询）均捕获并记录异常日志。Config管理支持通过环境变量注入敏感信息（数据库连接、加密密钥等），避免敏感信息硬编码。代码模块按业务域划分 Handler，职责单一，便于维护与测试。

| 编号 | Metric | 目标值 | 验证方式 |
|------|------|--------|----------|
| NFR-M-001 | 异常日志覆盖率 | 关键路径 100% 记录异常 | 代码审查，确认Payment回调、ClickHouse 查询等路径包含 `_logger.LogError` 调用 |
| NFR-M-002 | 敏感信息Config化 | 数据库密码、加密密钥通过环境变量注入 | Config审查，确认连接字符串使用 `${...}` 占位符 |
| NFR-M-003 | 模块化程度 | Handler 按业务域独立划分 | 代码审查，确认 UserManagement/DataManagement/PaymentManagement 等目录独立 |
| NFR-M-004 | Config扫描目录 | `Configurations`、`Resources` | Config检查，确认 `ConfigurationScanDirectories` 包含两个目录 |

### 4.6. 兼容性

兼容性需求确保系统在不同客户端与第三方服务间的互操作性。系统提供 OpenAI 兼容的 Chat Completions API，支持标准 OpenAI 客户端接入 [Agents/server.py:create_chat_completion_response]。Payment模块兼容微信Payment（Native、JSAPI、MiniProgram）与Payment宝即时到账两种主流Payment渠道。API 响应格式统一为 `ApiResponse<T>` 结构，包含 errorCode、data、page 等字段，保证客户端解析一致性。

| 编号 | Metric | 目标值 | 验证方式 |
|------|------|--------|----------|
| NFR-C-001 | OpenAI 兼容 API | 支持 Chat Completions 协议 | 使用 OpenAI SDK 调用，确认返回格式兼容 |
| NFR-C-002 | 微信Payment渠道兼容 | Native、JSAPI、MiniProgram | 接口测试，确认三种Payment方式均可发起Payment |
| NFR-C-003 | Payment宝Payment兼容 | 即时到账（Instant Trade） | 接口测试，确认 `GetAlipayInstantTrade` 返回有效Payment参数 |
| NFR-C-004 | API 响应格式统一 | 统一 `ApiResponse<T>` 结构 | 代码审查，确认所有 Controller 返回 `ApiResponse<T>` |

### 4.7. 本地化

本地化需求保障系统面向多语言用户群体的可用性。系统支持 zh-CN、zh-TW、zh-HK、en 四种语言，错误消息通过 `My.Extensions.Localization.Json` 实现本地化资源管理。用户界面与错误提示根据请求的 Accept-Language 头自动切换语言。

| 编号 | Metric | 目标值 | 验证方式 |
|------|------|--------|----------|
| NFR-L-001 | 支持语言种类 | zh-CN、zh-TW、zh-HK、en | Config检查，确认本地化资源文件包含四种语言 |
| NFR-L-002 | 错误消息本地化 | 100% 用户可见错误消息支持多语言 | 代码审查，确认错误消息通过 `My.Extensions.Localization.Json` 获取 |
| NFR-L-003 | 语言自动切换 | 根据 Accept-Language 请求头自动切换 | 接口测试，分别携带不同 Accept-Language 头验证返回消息语言 |

---

## 5. 接口需求

### 5.1. 内部接口

内部接口定义了 AgentInsightService 各模块之间的服务调用契约，由 `API/Common/Services` 目录下的服务类实现，供各 Handler 调用。

#### 5.1.1. IPaymentService（Payment服务）

Payment服务接口，负责订单创建、Payment参数生成、Payment回调处理及交易记录持久化。核心能力包括：

- `PlaceOrder`：创建订单，生成Payment参数 [API/Common/Services/PaymentService.cs:PlaceOrder]
- `GetNativeResponse` / `GetWeChatJSAPIResponse` / `WeChatMiniProgramPay`：生成微信Payment（Native、JSAPI、小程序）所需参数
- `GetAlipayInstantTrade`：生成Payment宝即时到账Payment参数
- `QueryOrder`：查询订单Payment状态
- `SaveWeChatTransaction` / `SaveAlipayTransaction`：保存Payment交易记录
- `UpdateOrderState` / `UpdateOrgPrivilege`：更新订单状态与OrgPrivilege（组织特权）

该接口被 `OrderHandler` 调用以处理下单请求 [API/Handlers/PaymentManagement/OrderHandler.cs:PlaceOrder]，同时被 `NotifyHandler` 调用以处理Payment回调 [API/Handlers/PaymentManagement/NotifyHandler.cs:ProcessWeChatNotify]。

#### 5.1.2. IUserService（用户Session管理）

用户Session管理服务接口，负责用户注册、登录、JWT Token 签发与刷新、Session记录等。核心能力包括：

- `CreateNewUser`：创建新用户，注册时校验图形Captcha [API/Handlers/UserManagement/UserHandler.cs:CreateUser]
- `LogUserSession`：记录用户登录Session，返回Session ID [API/Handlers/UserManagement/UserHandler.cs:Login]
- `CreateRefreshTokenAndSetHttpContext`：签发 JWT Token 与刷新 Token 并写入 HTTP 上下文
- `GetUserByUserId`：按用户 ID 查询用户信息

该接口由 `UserHandler` 调用 [API/Handlers/UserManagement/UserHandler.cs]，登录时支持密码登录（`loginType=1`）、短信登录（`loginType=2`）、微信登录（`loginType=3`）、小程序登录（`loginType=4`）及 API Key 登录（`loginType=5`）五种模式。

#### 5.1.3. IWeChatService（微信签名/消息）

微信服务接口，负责微信签名验证、Access Token 获取、微信账号绑定及消息处理。核心方法包括：

- `ExamineSignature`：验证微信服务器签名，将 `signature`、timestamp、nonce 三个参数排序后拼接并计算 SHA-1 哈希进行比对 [API/Common/Services/WeChatService.cs:ExamineSignature]
- `GetBasicAccessToken` / `GetAuthorizedAccessToken`：获取基础或授权 Access Token
- `GetOrUpdateBasicWXAccount` / `GetOrUpdateAuthorizedWXAccount`：获取或更新微信账号信息
- `LoginByWeChatMiniProgram`：微信小程序登录
- `WXSuccessResult` / `WXFailResult`：构造微信回调成功/失败响应

该接口由 `WeChatController` 调用以处理微信服务器验证与消息推送 [API/Controllers/ToolsManagement/WeChat/WeChatController.cs:Get]，同时由 `WeChatHandler` 调用以处理具体消息 [API/Handlers/ToolsManagement/WeChat/WeChatHandler.cs:ProcessMessage]。

#### 5.1.4. IAlertService（Alert评估）

Alert评估服务接口，负责Alert条件评估、Alert消息构建、Trace ID 查询及 Metrics 数据聚合。核心方法包括：

- `EvaluateField`：评估Alert字段值，支持 `AlertField` 枚举中定义的字段（如 TotalTokens、TotalCost、ErrorCount、Latency 等）[API/Common/Services/AlertService.cs:EvaluateField]
- `IsConditionMet`：判断Alert条件是否满足 [API/Common/Services/AlertService.cs:IsConditionMet]
- `BuildAlertMessage`：构建Alert通知消息
- `GetAlertMetrics`：聚合Alert相关的 Metrics 数据

该接口由 `SystemAlertHandler` 调用以处理系统Alert通知 [API/Notifications/SystemAlertHandler.cs:Handle]，同时由 `AlertHandler` 调用以管理Alert规则 [API/Handlers/UserManagement/AlertHandler.cs]。

#### 5.1.5. IBullMqService（消息队列）

消息队列服务接口，基于 Redis 实现 BullMQ 风格的任务入队/出队/确认，支持 Trace 数据摄入和项目删除异步任务。核心方法包括：

- `EnqueueTraceIngestionAsync`：将 Trace 数据摄入任务入队
- `AcknowledgeTraceIngestionAsync`：确认 Trace 数据摄入任务完成
- `EnqueueProjectDeleteAsync`：将项目删除任务入队

该接口由 `MetricsHandler` 调用以异步处理 Trace 数据摄入 [API/Handlers/DataManagement/MetricsHandler.cs]，由 `ProjectHandler` 调用以异步执行项目删除。

#### 5.1.6. 内部接口依赖关系汇总

| 调用方 | 被调用接口 | 调用场景 |
|--------|-----------|---------|
| OrderHandler | IPaymentService | 下单、Payment参数生成 [API/Handlers/PaymentManagement/OrderHandler.cs:PlaceOrder] |
| NotifyHandler | IPaymentService | Payment回调处理、订单状态更新 [API/Handlers/PaymentManagement/NotifyHandler.cs:ProcessWeChatNotify] |
| UserHandler | IUserService | 注册、登录、Session管理 [API/Handlers/UserManagement/UserHandler.cs:Login] |
| WeChatController | IWeChatService | 微信签名验证、消息推送 [API/Controllers/ToolsManagement/WeChat/WeChatController.cs:Get] |
| SystemAlertHandler | IAlertService | Alert评估、消息构建 [API/Notifications/SystemAlertHandler.cs:Handle] |
| MetricsHandler | IBullMqService | Trace 数据异步摄入 [API/Handlers/DataManagement/MetricsHandler.cs] |

### 5.2. 外部接口

外部接口定义了 AgentInsightService 对客户端暴露的 HTTP API 端点。系统遵循 RESTful 风格，Base URL 由部署环境决定，字符集使用 UTF-8，时间格式遵循 ISO 8601，版本治理通过路径前缀 `/api` 实现。系统共 76 个端点分布在 18 个 Controller 中，本章节按功能域分组说明各 Controller 提供的端点。

#### 5.2.1. 通用约定

所有接口响应均包装在 `ApiResponse<T>` 统一响应结构中，包含 `errorCode`、`message`、`data` 三个字段。`errorCode=0` 表示成功，非零值表示具体错误。认证方式分为三类：

- **JWT**：通过 `Authorization: Bearer <token>` 头传递，适用于已登录用户
- **API Key（Basic Auth）**：通过 `Authorization: Basic <base64(publicKey:secretKey)>` 头传递，适用于 API 调用
- **Public**：无需认证，适用于注册、登录、微信回调等场景

#### 5.2.2. 用户管理接口

用户管理接口由 `UserController` 提供 [API/Controllers/UserManagement/UserController.cs]，路由前缀为 `/api/user`，共 11 个端点。

##### 获取用户信息 (GET /api/user)

**鉴权**: JWT

**描述**: 获取当前登录用户的详细信息，包括用户 ID、用户名、手机号/邮箱、头像、Token、`refreshtoken`、微信 `openid` 等 [API/Controllers/UserManagement/UserController.cs:29]。

**响应格式**:

| 字段 | 类型 | 说明 |
|------|------|------|
| errorCode | int | 0=成功，非零=错误 |
| data.id | string | User ID |
| data.name | string | 用户名 |
| data.mobile | string | 用户手机/邮箱 |
| data.token | string | JWT Token |
| data.refreshtoken | string | 刷新 Token |
| data.sessionid | string | Session ID |
| data.openid | string | 微信 openid |

##### 创建用户（注册） (POST /api/user)

**鉴权**: Public

**描述**: 注册新用户，需要提供手机号/邮箱、密码、用户名及图形Captcha [API/Controllers/UserManagement/UserController.cs:43]。注册流程中会调用 `CaptchaHandler` 校验图形Captcha，验证通过后由 `UserHandler.CreateUser` 创建用户并记录审计日志 [API/Handlers/UserManagement/UserHandler.cs:CreateUser]。

**请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| mobile | string | 是 | 手机号/邮箱 |
| password | string | 是 | 密码 |
| name | string | 是 | 用户名 |
| captchaCode | string | 是 | 图形Captcha |

##### 更新用户信息 (POST /api/user/update)

**鉴权**: JWT

**描述**: 更新当前用户的用户名或头像 [API/Controllers/UserManagement/UserController.cs:58]。

**请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | 否 | 新用户名 |
| image | string | 否 | 头像 URL |

##### 登录 (POST /api/user/login)

**鉴权**: Public

**描述**: 用户登录，支持密码、短信、微信、小程序、API Key 五种登录方式 [API/Controllers/UserManagement/UserController.cs:73]。`loginType=5`（API Key）时请求体可为空，需在 Authorization 头携带 `Basic publickey:secretkey`。登录成功后响应头包含 `access-token`。

**请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| mobile | string | 条件必填 | 手机号/邮箱（`loginType=1/2` 时必填） |
| password | string | 条件必填 | 密码（`loginType=1` 时必填） |
| loginType | int | 是 | 1=密码，2=短信，3=微信，4=小程序，5=APIKey |

**错误码**:

| errorCode | 说明 |
|-----------|------|
| 0 | 成功 |
| 100038 | API Key 无效 [Models/Common/Enums/ExceptionCodes.cs:6] |

##### 登出 (POST /api/user/logout)

**鉴权**: JWT

**描述**: 当前用户登出，使当前 Session 失效 [API/Controllers/UserManagement/UserController.cs:88]。

##### 重置密码 (POST /api/user/resetpassword)

**鉴权**: Public

**描述**: 通过手机号+Captcha重置密码 [API/Controllers/UserManagement/UserController.cs:102]。

**请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| mobile | string | 是 | 手机号 |
| captchaId | string | 是 | Captcha ID |
| captchaCode | string | 是 | Captcha |

##### 绑定微信 (POST /api/user/bind/wechat)

**鉴权**: JWT

**描述**: 将当前用户与微信账号绑定 [API/Controllers/UserManagement/UserController.cs:117]。

##### 解绑微信 (GET /api/user/unbind/wechat)

**鉴权**: JWT

**描述**: 解绑当前用户与微信账号的绑定关系 [API/Controllers/UserManagement/UserController.cs:132]。

##### 分配角色 (POST /api/user/role)

**鉴权**: JWT

**描述**: 为成员分配角色 [API/Controllers/UserManagement/UserController.cs:147]。

##### 邀请成员 (POST /api/user/invite)

**鉴权**: JWT

**描述**: 邀请新成员加入 Organization [API/Controllers/UserManagement/UserController.cs:162]。

##### 获取邀请列表 (GET /api/user/invitation)

**鉴权**: JWT

**描述**: 获取当前用户的邀请列表 [API/Controllers/UserManagement/UserController.cs:177]。

#### 5.2.3. Alert管理接口

Alert管理接口由 `AlertController` 提供，路由前缀为 `/api/alert`，共 7 个端点。

##### 获取AlertConfig (GET /api/alert/config)

**鉴权**: JWT

**描述**: 获取Alert规则Config [API/Controllers/UserManagement/AlertController.cs:30]。

##### 获取Alert规则列表 (GET /api/alert)

**鉴权**: JWT

**描述**: 获取当前用户的Alert规则列表 [API/Controllers/UserManagement/AlertController.cs:47]。

##### 创建Alert规则 (POST /api/alert)

**鉴权**: JWT

**描述**: 创建新的Alert规则，支持基于 `AlertField`（TotalTokens、TotalCost、ErrorCount、Latency 等）的条件评估 [API/Controllers/UserManagement/AlertController.cs:61]。

##### 更新Alert规则 (POST /api/alert/update)

**鉴权**: JWT

**描述**: 更新已有Alert规则 [API/Controllers/UserManagement/AlertController.cs:75]。

##### 删除Alert规则 (POST /api/alert/delete)

**鉴权**: JWT

**描述**: 删除一条或多条Alert规则 [API/Controllers/UserManagement/AlertController.cs:90]。

##### 标记Alert记录已读 (POST /api/alert/record/read)

**鉴权**: JWT

**描述**: 将Alert记录标记为已读 [API/Controllers/UserManagement/AlertController.cs:108]。

##### 获取Alert记录 (GET /api/alert/record)

**鉴权**: JWT

**描述**: 获取Alert记录列表，支持分页查询 [API/Controllers/UserManagement/AlertController.cs:128]。

#### 5.2.4. 微信工具接口

微信工具接口由 `WeChatController` 提供 [API/Controllers/ToolsManagement/WeChat/WeChatController.cs]，路由前缀为 `/api/tools/wechat`，共 2 个端点，均无需认证（由微信服务器回调）。

##### 微信签名验证 (GET /api/tools/wechat)

**鉴权**: Public

**描述**: 微信服务器调用该接口验证签名，验证通过后返回 `echostr` 原文 [API/Controllers/ToolsManagement/WeChat/WeChatController.cs:36]。签名验证逻辑由 `WeChatService.ExamineSignature` 实现，将 `signature`、timestamp、nonce 排序后拼接并计算 SHA-1 哈希进行比对 [API/Common/Services/WeChatService.cs:ExamineSignature]。

**请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| signature | string | 是 | 微信签名 |
| timestamp | string | 是 | 时间戳 |
| nonce | string | 是 | 随机字符串 |
| echostr | string | 是 | 微信回复字符串 |

##### 微信消息接收 (POST /api/tools/wechat)

**鉴权**: Public

**描述**: 接收微信推送的消息和事件，支持文本消息、事件消息等 [API/Controllers/ToolsManagement/WeChat/WeChatController.cs:68]。消息处理由 `WeChatHandler.ProcessMessage` 完成 [API/Handlers/ToolsManagement/WeChat/WeChatHandler.cs:ProcessMessage]，支持 `WeChatMessageType` 枚举定义的消息类型。响应格式为 XML，若消息类型为 `None` 则返回空响应。

**请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| signature | string | 是 | 微信签名 |
| timestamp | string | 是 | 时间戳 |
| nonce | string | 是 | 随机字符串 |
| openid | string | 否 | User openid |
| body | WeChatMessage | 是 | 微信消息 XML 体 |

#### 5.2.5. Payment管理接口

Payment管理接口由 `PaymentController` 提供 [API/Controllers/PaymentManagement/PaymentController.cs]，路由前缀为 `/api/payment`，共 4 个端点。

##### 创建订单 (POST /api/payment/order)

**鉴权**: JWT

**描述**: 创建Payment订单，支持微信Payment（Native、JSAPI、小程序）与Payment宝Payment [API/Controllers/PaymentManagement/PaymentController.cs:25]。订单创建后返回Payment参数，由前端调起Payment。

**请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| productId | string | 是 | Product ID |
| paymentMethod | string | 是 | Payment方式：wechat_native / wechat_jsapi / wechat_miniprogram / alipay |
| quantity | int | 否 | 购买数量，默认 1 |

##### 查询订单 (GET /api/payment/order/{orderId})

**鉴权**: JWT

**描述**: 查询指定订单的Payment状态与详情 [API/Controllers/PaymentManagement/PaymentController.cs:48]。

##### 获取订单列表 (GET /api/payment/orders)

**鉴权**: JWT

**描述**: 获取当前用户的订单列表，支持分页查询 [API/Controllers/PaymentManagement/PaymentController.cs:67]。

##### 获取产品转换信息 (GET /api/payment/product-conversion)

**鉴权**: JWT

**描述**: 获取产品时长转换计算信息 [API/Controllers/PaymentManagement/PaymentController.cs:89]。

#### 5.2.6. 数据查询接口

数据查询接口由 `MetricsController` 提供 [API/Controllers/DataManagement/MetricsController.cs]，路由前缀为 `/api/metrics`，共 4 个端点。

##### 查询 Trace 列表 (GET /api/metrics/traces)

**鉴权**: JWT

**描述**: 查询 Trace 数据列表，支持按项目、时间范围、模型、状态等多维度过滤，支持排序与分页 [API/Controllers/DataManagement/MetricsController.cs:31]。

**请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| projectId | string | 是 | Project ID |
| startTime | string | 否 | 开始时间（ISO 8601） |
| endTime | string | 否 | 结束时间（ISO 8601） |
| model | string | 否 | 模型名称过滤 |
| status | string | 否 | 状态过滤 |
| page | int | 否 | 页码，默认 1 |
| pageSize | int | 否 | 每页条数，默认 20 |

##### 查询 Trace 详情 (GET /api/metrics/traces/{traceId})

**鉴权**: JWT

**描述**: 查询指定 Trace 的详细信息，包括 Span 列表、Token 消耗、延迟等指标 [API/Controllers/DataManagement/MetricsController.cs:52]。

##### 查询 Observation 列表 (GET /api/metrics/observations)

**鉴权**: JWT

**描述**: 查询 Observation 数据列表，支持按项目、时间范围过滤 [API/Controllers/DataManagement/MetricsController.cs:73]。

##### 查询 Score 列表 (GET /api/metrics/scores)

**鉴权**: JWT

**描述**: 查询 Score 数据列表，支持按项目、时间范围过滤 [API/Controllers/DataManagement/MetricsController.cs:91]。

#### 5.2.7. 组织与项目管理接口

组织与项目管理接口由 `OrganizationController` 和 `ProjectController` 提供，路由前缀分别为 `/api/organization` 和 `/api/project`，共 8 个端点。

##### 创建组织 (POST /api/organization)

**鉴权**: JWT

**描述**: 创建新的 Organization [API/Controllers/UserManagement/OrganizationController.cs:25]。

##### 获取组织列表 (GET /api/organization)

**鉴权**: JWT

**描述**: 获取当前用户所属的组织列表 [API/Controllers/UserManagement/OrganizationController.cs:42]。

##### 更新组织 (POST /api/organization/update)

**鉴权**: JWT

**描述**: 更新组织信息 [API/Controllers/UserManagement/OrganizationController.cs:58]。

##### 删除组织 (POST /api/organization/delete)

**鉴权**: JWT

**描述**: 删除指定组织 [API/Controllers/UserManagement/OrganizationController.cs:74]。

##### 创建项目 (POST /api/project)

**鉴权**: JWT

**描述**: 在指定组织下创建新项目 [API/Controllers/UserManagement/ProjectController.cs:25]。

##### 获取项目列表 (GET /api/project)

**鉴权**: JWT

**描述**: 获取当前用户可访问的项目列表 [API/Controllers/UserManagement/ProjectController.cs:42]。

##### 更新项目 (POST /api/project/update)

**鉴权**: JWT

**描述**: 更新项目信息 [API/Controllers/UserManagement/ProjectController.cs:58]。

##### 删除项目 (POST /api/project/delete)

**鉴权**: JWT

**描述**: 删除指定项目，删除操作异步执行 [API/Controllers/UserManagement/ProjectController.cs:74]。

#### 5.2.8. API Key 管理接口

API Key 管理接口由 `ApiKeyController` 提供 [API/Controllers/UserManagement/ApiKeyController.cs]，路由前缀为 `/api/apikey`，共 3 个端点。

##### 创建 API Key (POST /api/apikey)

**鉴权**: JWT

**描述**: 创建新的 API Key，返回 `publicKey` 与 `secretKey` [API/Controllers/UserManagement/ApiKeyController.cs:25]。

##### 获取 API Key 列表 (GET /api/apikey)

**鉴权**: JWT

**描述**: 获取当前用户的 API Key 列表 [API/Controllers/UserManagement/ApiKeyController.cs:42]。

##### 删除 API Key (POST /api/apikey/delete)

**鉴权**: JWT

**描述**: 删除指定 API Key [API/Controllers/UserManagement/ApiKeyController.cs:58]。

#### 5.2.9. 产品管理接口

产品管理接口由 `ProductController` 提供 [API/Controllers/ProductManagement/ProductController.cs]，路由前缀为 `/api/product`，共 2 个端点。

##### 获取产品列表 (GET /api/product)

**鉴权**: JWT

**描述**: 获取可购买的产品列表 [API/Controllers/ProductManagement/ProductController.cs:25]。

##### 获取产品时长 (GET /api/product/durations)

**鉴权**: JWT

**描述**: 获取产品的可选时长Config [API/Controllers/ProductManagement/ProductController.cs:42]。

#### 5.2.10. Agent Config管理接口

Agent Config管理接口由 `AgentConfigController` 提供 [API/Controllers/AgentManagement/AgentConfigController.cs]，路由前缀为 `/api/agent/config`，共 3 个端点。

##### 创建或更新 Agent Config (POST /api/agent/config)

**鉴权**: JWT

**描述**: 创建或更新 Agent Config [API/Controllers/AgentManagement/AgentConfigController.cs:25]。

##### 获取 Agent Config (GET /api/agent/config)

**鉴权**: JWT

**描述**: 获取指定 Agent 的Config信息 [API/Controllers/AgentManagement/AgentConfigController.cs:42]。

##### 删除 Agent Config (POST /api/agent/config/delete)

**鉴权**: JWT

**描述**: 删除指定 Agent 的Config [API/Controllers/AgentManagement/AgentConfigController.cs:58]。

#### 5.2.11. Agent Agent Session 管理接口

Agent Agent Session 管理接口由 `AgentSessionController` 提供 [API/Controllers/AgentManagement/AgentSessionController.cs]，路由前缀为 `/api/agent/session`，共 3 个端点。

##### 获取 Session 列表 (GET /api/agent/session)

**鉴权**: JWT

**描述**: 获取指定 Agent 的 Session 列表 [API/Controllers/AgentManagement/AgentSessionController.cs:25]。

##### 创建或更新 Session (POST /api/agent/session)

**鉴权**: JWT

**描述**: 创建或更新 Agent Session [API/Controllers/AgentManagement/AgentSessionController.cs:42]。

##### 删除 Session (POST /api/agent/session/delete)

**鉴权**: JWT

**描述**: 批量删除 Agent Session [API/Controllers/AgentManagement/AgentSessionController.cs:58]。

#### 5.2.12. Agent Report AgentReport管理接口

Agent Report AgentReport管理接口由 `AgentReportController` 提供 [API/Controllers/AgentManagement/AgentReportController.cs]，路由前缀为 `/api/agent/report`，共 3 个端点。

##### 获取模板列表 (GET /api/agent/report/templates)

**鉴权**: JWT

**描述**: 获取 Report AgentReport列表 [API/Controllers/AgentManagement/AgentReportController.cs:25]。

##### 创建或更新模板 (POST /api/agent/report/template)

**鉴权**: JWT

**描述**: 创建或更新 Report AgentReport [API/Controllers/AgentManagement/AgentReportController.cs:42]。

##### 删除模板 (POST /api/agent/report/template/delete)

**鉴权**: JWT

**描述**: 批量删除 Report AgentReport [API/Controllers/AgentManagement/AgentReportController.cs:58]。

#### 5.2.13. Bulletin管理接口

Bulletin管理接口由 `BulletinController` 提供 [API/Controllers/ToolsManagement/BulletinController.cs]，路由前缀为 `/api/bulletin`，共 5 个端点。

##### 获取Bulletin列表 (GET /api/bulletin)

**鉴权**: JWT

**描述**: 获取Bulletin列表 [API/Controllers/ToolsManagement/BulletinController.cs:25]。

##### 创建Bulletin (POST /api/bulletin)

**鉴权**: JWT

**描述**: 创建新Bulletin [API/Controllers/ToolsManagement/BulletinController.cs:42]。

##### 审批Bulletin (POST /api/bulletin/approve)

**鉴权**: JWT

**描述**: 审批Bulletin [API/Controllers/ToolsManagement/BulletinController.cs:58]。

##### 修订Bulletin (POST /api/bulletin/revise)

**鉴权**: JWT

**描述**: 修订Bulletin内容 [API/Controllers/ToolsManagement/BulletinController.cs:74]。

##### 关闭Bulletin (POST /api/bulletin/close)

**鉴权**: JWT

**描述**: 关闭Bulletin [API/Controllers/ToolsManagement/BulletinController.cs:90]。

#### 5.2.14. 外部接口汇总

| 方法 | 路径 | 鉴权 | 说明 |
|------|------|------|------|
| GET | /api/user | JWT | 获取用户信息 |
| POST | /api/user | Public | 用户注册 |
| POST | /api/user/update | JWT | 更新用户信息 |
| POST | /api/user/login | Public | 用户登录 |
| POST | /api/user/logout | JWT | 用户登出 |
| POST | /api/user/resetpassword | Public | 重置密码 |
| POST | /api/user/bind/wechat | JWT | 绑定微信 |
| GET | /api/user/unbind/wechat | JWT | 解绑微信 |
| POST | /api/user/role | JWT | 分配角色 |
| POST | /api/user/invite | JWT | 邀请成员 |
| GET | /api/user/invitation | JWT | 获取邀请列表 |
| GET | /api/alert/config | JWT | 获取AlertConfig |
| GET | /api/alert | JWT | 获取Alert规则列表 |
| POST | /api/alert | JWT | 创建Alert规则 |
| POST | /api/alert/update | JWT | 更新Alert规则 |
| POST | /api/alert/delete | JWT | 删除Alert规则 |
| POST | /api/alert/record/read | JWT | 标记Alert已读 |
| GET | /api/alert/record | JWT | 获取Alert记录 |
| GET | /api/tools/wechat | Public | 微信签名验证 |
| POST | /api/tools/wechat | Public | 微信消息接收 |
| POST | /api/payment/order | JWT | 创建Payment订单 |
| GET | /api/payment/order/{orderId} | JWT | 查询订单状态 |
| GET | /api/payment/orders | JWT | 获取订单列表 |
| GET | /api/payment/product-conversion | JWT | 获取产品转换信息 |
| GET | /api/metrics/traces | JWT | 查询 Trace 列表 |
| GET | /api/metrics/traces/{traceId} | JWT | 查询 Trace 详情 |
| GET | /api/metrics/observations | JWT | 查询 Observation 列表 |
| GET | /api/metrics/scores | JWT | 查询 Score 列表 |
| POST | /api/organization | JWT | 创建组织 |
| GET | /api/organization | JWT | 获取组织列表 |
| POST | /api/organization/update | JWT | 更新组织 |
| POST | /api/organization/delete | JWT | 删除组织 |
| POST | /api/project | JWT | 创建项目 |
| GET | /api/project | JWT | 获取项目列表 |
| POST | /api/project/update | JWT | 更新项目 |
| POST | /api/project/delete | JWT | 删除项目 |
| POST | /api/apikey | JWT | 创建 API Key |
| GET | /api/apikey | JWT | 获取 API Key 列表 |
| POST | /api/apikey/delete | JWT | 删除 API Key |
| GET | /api/product | JWT | 获取产品列表 |
| GET | /api/product/durations | JWT | 获取产品时长 |
| POST | /api/agent/config | JWT | 创建或更新 Agent Config |
| GET | /api/agent/config | JWT | 获取 Agent Config |
| POST | /api/agent/config/delete | JWT | 删除 Agent Config |
| GET | /api/agent/session | JWT | 获取 Session 列表 |
| POST | /api/agent/session | JWT | 创建或更新 Session |
| POST | /api/agent/session/delete | JWT | 删除 Session |
| GET | /api/agent/report/templates | JWT | 获取模板列表 |
| POST | /api/agent/report/template | JWT | 创建或更新模板 |
| POST | /api/agent/report/template/delete | JWT | 删除模板 |
| GET | /api/bulletin | JWT | 获取Bulletin列表 |
| POST | /api/bulletin | JWT | 创建Bulletin |
| POST | /api/bulletin/approve | JWT | 审批Bulletin |
| POST | /api/bulletin/revise | JWT | 修订Bulletin |
| POST | /api/bulletin/close | JWT | 关闭Bulletin |

---

## 6. 数据需求

### 6.1. 数据需求

#### 6.1.1. 实体定义

系统核心实体按业务域划分，主要分为用户与组织管理、可Observation性数据管理、Payment与产品管理三大类。

用户与组织模型定义在 `Entities/UserManagement` 命名空间下。`OrganizationHandler` 在创建组织时构造 `Organization` 与 `OrganizationMembership` 实体，并将 `Role` 设为 `PGRole.OWNER`，随后在事务中写入 DataDb [API/Handlers/UserManagement/OrganizationHandler.cs]。`UserConfigHandler` 通过 `Expressionable` 动态构造查询条件，按 `UserId`、`Key`、`Value`、`Type` 组合过滤 `UserConfig` 实体 [API/Handlers/UserManagement/UserConfigHandler.cs]。

可Observation性实体定义在 `Entities/DataManagement` 命名空间下。`MetricsHandler` 通过 SqlSugar 客户端 `_chdb`（绑定 ClickHouse 数据库）查询 `Observation` 与 `Score` 实体，按 `ProjectId` 过滤并排除 `IsDeleted` 标记的数据 [API/Handlers/DataManagement/MetricsHandler.cs]。`TraceMetrics` 为聚合查询结果模型，包含 `TotalTokens`、`TotalCost`、`Latency` 等指标字段，由 `GetTraces` 方法通过 `TraceFilterBuilder` 构建过滤条件后动态查询 [API/Handlers/DataManagement/MetricsHandler.cs]。

Payment域实体定义在 `Entities/PaymentManagement` 命名空间下。`OrderHandler` 在 `PlaceOrder` 方法中依次校验 `AgentInsightProduct` 与 `AgentInsightProductDuration` 实体存在性，并读取 `OrgPrivilege` 实体以计算新特权 [API/Handlers/PaymentManagement/OrderHandler.cs]。`ProductHandler` 直接通过 `Db.Queryable<AgentInsightProduct>()` 与 `Db.Queryable<AgentInsightProductDuration>()` 查询产品及时长列表 [API/Handlers/ProductManagement/ProductHandler.cs]。

#### 6.1.2. 数据存储

系统采用多数据库混合存储架构，按数据类型与访问模式将数据分散到 ClickHouse、PostgreSQL 与 Redis 三类存储引擎。

#### 6.1.3. 数据流

**用户认证流程**：用户登录由 `UserHandler.Login` 接收凭证，调用 `UserService` 验证身份后，通过 `CreateRefreshTokenAndSetHttpContext` 签发 JWT Token 并写入 HttpContext，同时生成 Refresh Token 返回客户端 [API/Handlers/UserManagement/UserHandler.cs] [API/Common/Services/UserService.cs]。后续请求通过 API Key（Basic Auth）或 JWT 进行认证。

**Payment流程**：`OrderHandler.PlaceOrder` 创建订单后，`PaymentService` 根据Payment渠道（微信/Payment宝）调用对应方法生成Payment参数。用户完成Payment后，Payment平台回调 `NotifyHandler` 的 `ProcessWeChatNotify` / `ProcessAlipayNotify` 方法，`PaymentService` 保存交易记录并调用 `UpdateOrderState` 更新订单状态，随后调用 `UpdateOrgPrivilege` 同步更新OrgPrivilege（组织特权） [API/Common/Services/PaymentService.cs]。

**Alert触发流程**：Alert评估由 `AlertService` 执行，`SystemAlertHandler` 触发时调用 `AlertService.GetAlertMetrics` 查询 ClickHouse 中的 Metric 数据 [API/Notifications/SystemAlertHandler.cs]。`AlertService.EvaluateField` 基于 `AlertField` 枚举（如 `TotalTokens`、`TotalCost`、`ErrorCount`、`Latency`）提取指标值，`IsConditionMet` 按 `Operator` 比较阈值，满足条件后通过 `BuildAlertMessage` 构建通知内容，经 System/SMS 通道发送 [API/Common/Services/AlertService.cs]。

**Trace 查询流程**：`MetricsHandler.GetTraces` 接收 `TraceMetricsBody`，首先调用 `ResolveProjectId` 解析项目 ID，随后通过 `TraceFilterBuilder.BuildFilters` 将 `Filter` 条件列表转换为 ClickHouse SQL 过滤表达式 [API/Handlers/DataManagement/MetricsHandler.cs]。最终由 `ClickHouseClient.QueryAsync` 执行 SQL 并返回 `TraceMetrics` 分页结果 [API/Common/Services/ClickHouseClient.cs]。`GetObservationsAsync` 与 `GetScoresAsync` 则直接通过 `_chdb.Queryable<Observation>()` / `_chdb.Queryable<Score>()` 按 `ProjectId` 查询，按 `Timestamp` / `CreatedAt` 排序并分页返回 [API/Handlers/DataManagement/MetricsHandler.cs]。

**异步任务流**：Trace 数据摄入与项目删除通过 `BullMqService` 入队，任务消费者确认后执行。`EnqueueTraceIngestionAsync` 将 Trace 数据写入 ClickHouse，`EnqueueProjectDeleteAsync` 异步清理项目关联数据，任务完成后调用 `AcknowledgeTraceIngestionAsync` 确认 [API/Common/Services/BullMqService.cs]。

---

## 7. 约束条件

AgentInsightService 是一个面向可Observation性领域的智能服务系统，集成Payment宝与微信Payment能力，支持订单创建、Payment回调处理以及基于订单的 OrgPrivilege（OrgPrivilege（组织特权））自动更新。普通用户通过 API Key（Basic Auth 或 Bearer JWT）认证访问系统，管理自己的 Organization、Project、ApiKey，查看 Trace 数据与Alert记录。本章节定义系统在技术选型、业务逻辑与合规安全三个维度必须遵守的约束条件，确保系统在开发、部署与运维过程中保持一致性与安全性。

### 7.1. 技术约束

AgentInsightService 的技术架构基于 .NET 生态构建，技术选型必须严格遵循项目既定的技术栈，不得引入未经验证的替代框架。

**后端技术栈约束**

系统后端必须使用以下核心依赖，不得替换或混用其他框架：

| 技术组件 | 用途 | 约束说明 |
|---------|------|---------|
| AlipaySDKNet.Standard | Payment宝Payment SDK | 必须使用该 SDK 实现Payment宝下单与回调验签 |
| MediatR | 进程内消息中介 | 用于解耦 Handler 之间的调用，如Payment回调后触发通知 |
| AlipaySDKNet.Cryptography | 加密算法库 | 用于 RSA 签名验证等密码学操作 |
| AlipaySDKNet.Redis | Redis 客户端 | 支撑 BullMqService 消息队列与缓存 |
| Npgsql | PostgreSQL 驱动 | 连接 UserDb/DataDb/TrackingDb 数据库 |
| Yarp.ReverseProxy | 反向代理 | 用于 API 网关路由转发 |

**数据库连接约束**

所有数据库连接字符串必须通过环境变量注入，禁止在Config文件或代码中硬编码数据库凭据。连接字符串格式如下：

```ini
UserDb.ConnectionString = Host=${USER_DB_HOST};Port=${USER_DB_PORT};Database=${USER_DB_NAME};Username=postgres;Password=${USER_DB_PASSWORD};Timeout=60;Pooling=true;Minimum Pool Size=10;Maximum Pool Size=200;Connection Idle Lifetime=300
DataDb.ConnectionString = Host=${DATA_DB_HOST};Port=${DATA_DB_PORT};Database=${DATA_DB_NAME};Username=postgres;Password=${DATA_DB_PASSWORD};Timeout=60;Pooling=true;Minimum Pool Size=10;Maximum Pool Size=200;Connection Idle Lifetime=300
TrackingDb.ConnectionString = Host=${TRACKING_DB_HOST};Port=${TRACKING_DB_PORT};Username=${TRACKING_DB_USER};Password=${TRACKING_DB_PASSWORD};Database=${TRACKING_DB_NAME};MinPoolSize=10;MaxPoolSize=50;ConnectionIdleTimeout=30;ConnectionPruningInterval=60
ClickHouseDb.ConnectionString = Host=${CLICKHOUSE_HOST};Port=${CLICKHOUSE_PORT};Username=${CLICKHOUSE_USER};Password=${CLICKHOUSE_PASSWORD};Database=${CLICKHOUSE_DB};MinPoolSize=10;MaxPoolSize=50;ConnectionIdleTimeout=30;ConnectionPruningInterval=60
```

上述连接Config在 `API/Handlers/DataManagement/MetricsHandler.cs` 中通过 `[KeyedService(AgentInsightConst.KeyedService_ClickHouseDb)]` 注入 ClickHouse 客户端，用于 Trace 与 Observation 数据查询。

**密钥管理约束**

JWT Token 签名密钥与 AES 加密密钥必须通过环境变量注入，禁止硬编码或写入Config文件。具体约束如下：

| 密钥项 | 环境变量 | 用途 | 约束说明 |
|-------|---------|------|---------|
| JWT 签名密钥 | `JWT_SIGNING_KEY` | JWT Token 签发与验证 | 必须使用至少 256 位长度的随机密钥，定期轮换 |
| AES 加密密钥 | `AES_KEY` | 用户密码等敏感数据加密 | 必须使用 128/192/256 位密钥，禁止使用固定弱密钥 |
| 刷新Token密钥 | `REFRESH_TOKEN_KEY` | Refresh Token 签发与验证 | 必须独立于 JWT 签名密钥，定期轮换 |

密钥通过 `API/Common/Services/UserService.cs` 中的 `IConfiguration` 读取，任何代码路径不得将密钥值写入日志、异常消息或响应体中。

### 7.2. 业务约束

业务约束确保系统在Payment处理、OrgPrivilege（组织特权）更新、Alert评估等核心业务流程中遵循既定规则，保证业务逻辑的正确性与一致性。

**Payment回调签名验证**

Payment回调请求必须验证签名后才可处理业务逻辑。微信Payment与Payment宝回调的签名验证算法与入口如下：

| Payment渠道 | 签名算法 | 验证入口 |
|---------|---------|---------|
| 微信Payment | HMAC-SHA256 | `API/Common/Services/PaymentService.cs:ExamineWeChatSignature` |
| Payment宝 | RSA | `API/Common/Services/PaymentService.cs:ExamineAlipaySignature` |

微信Payment回调处理入口位于 `API/Controllers/PaymentManagement/NotifyController.cs` 的 `WeChatNotify` 方法，该方法首先读取请求体，调用 `_handler.ExamineWeChatRequest(httpContext, body)` 验证签名，验证通过后才反序列化 `WeChatNotify` 对象并调用 `ProcessWeChatNotify` 处理业务逻辑。若请求体为空，直接抛出 `ExceptionCodes.InvalidWeChatNotifyRequest` 异常拒绝处理。

Payment宝回调处理位于同一 Controller 的 `AlipayNotify` 方法，通过 `_handler.ProcessAlipayNotify(httpContext.Request)` 完成验签与业务处理。

**OrgPrivilege（组织特权）更新与订单状态关联**

OrgPrivilege（OrgPrivilege（组织特权））的更新必须与订单状态强关联。当Payment回调验证通过并更新订单状态为已Payment后，系统自动触发OrgPrivilege（组织特权）更新。该逻辑在 `API/Handlers/PaymentManagement/NotifyHandler.cs:ProcessWeChatNotify` 中实现，通过 `PaymentService.UpdateOrderState` 更新订单状态，并同步更新对应组织的特权信息。

订单查询接口 `API/Handlers/PaymentManagement/OrderHandler.cs:QueryOrder` 要求调用者必须是该组织的 OWNER Role，否则抛出 `ExceptionCodes.UnauthorizedOrganizationAccess` 异常，确保只有组织所有者才能查看订单信息。

**Alert条件评估约束**

Alert条件的评估必须基于 `AlertField` 和 `AlertOperator` 枚举定义，禁止使用枚举之外的字段或操作符。`API/Common/Services/AlertService.cs` 中的 `EvaluateField` 方法负责从 Metrics 数据中提取指定字段值，`IsConditionMet` 方法根据 `AlertOperator` 比较实际值与阈值。

支持的Alert字段包括 TotalTokens、TotalCost、ErrorCount、Latency 等，定义于 `Models/Common/Enums/AlertEnum.cs` 的 `AlertField` 枚举。若传入未定义的字段或操作符，系统抛出 `InvalidAlertField = 160006` 或 `InvalidAlertOperator = 160007` 错误码。

**Captcha限制**

Captcha服务必须遵循以下Config约束：

| Config项 | 值 | 说明 |
|-------|-----|------|
| SMSCodeLength | 6 | 短信Captcha长度 |
| EmailCodeLength | 6 | 邮箱Captcha长度 |
| ImageCodeLength | 5 | 图形Captcha长度 |
| ExpiredSeconds | 300 | Captcha有效期（秒） |
| ResendInterval | 60 | 重发间隔（秒） |

上述Config定义于 `CaptchaSetting`，在 `API/Handlers/UserManagement/UserHandler.cs` 中通过 `ICaptchaService` 使用。Captcha过期或重发频率超限时，系统必须拒绝请求并提示用户。

**Payment回调重试约束**

微信Payment回调处理支持重试机制，`API/Notifications/WeChatNotifyReceivedHandler.cs` 中 `MaxRetryCount = 3`，即回调处理失败时最多重试 3 次。重试逻辑基于 MediatR 通知机制，确保Payment结果最终一致。

### 7.3. 合规约束

合规约束确保系统在数据安全、Config管理与多语言支持方面符合行业规范与法律法规要求。

**密码加密存储**

用户密码必须使用 AES 加密后存储，禁止明文保存。`API/Common/Services/UserService.cs` 中通过 `IEncryptService` 执行加密操作，加密密钥来自 `${AES_KEY}` 环境变量。密码加密是用户注册、登录、密码重置等功能的强制前置条件，任何绕过加密直接存储密码的代码路径均属违规。

**敏感Config不得硬编码**

以下敏感信息禁止出现在Config文件或代码中：

| 敏感Config项 | 注入方式 | 用途 |
|-----------|---------|------|
| JWT_SIGNING_KEY | 环境变量 | JWT Token 签名 |
| AES_KEY | 环境变量 | AES 加密密钥 |
| CLICKHOUSE_HOST/PORT/USER/PASSWORD | 环境变量 | ClickHouse 连接 |
| USER_DB_PASSWORD / DATA_DB_PASSWORD | 环境变量 | PostgreSQL 连接 |
| WECHAT_PAY_SECRET / ALIPAY_PRIVATE_KEY | 环境变量 | 外部服务认证 |

微信Payment/Payment宝Payment密钥存储于数据库 `AgentInsightSetting` 表中，必须加密存储，禁止明文写入。`API/Handlers/ToolsManagement/SettingHandler.cs` 的 `GetSetting` 方法按 `SettingType` 类型读取设置项，返回前需确保敏感字段已脱敏或加密。

**多语言支持**

系统必须支持多语言，遵循 `LocalizationSettings.SupportedCultures` Config：

```csharp
LocalizationSettings.SupportedCultures = ['zh-CN', 'zh-TW', 'zh-HK', 'en']
```

所有面向用户的界面文案、错误消息、通知内容必须提供上述四种语言版本的翻译资源。多语言资源文件存放于 `Resources` 目录（见 `LocalizationSettings.ResourcesPath = ['Configurations', 'Resources']` Config），使用 `My.Extensions.Localization.Json` 框架加载。新增语言资源时，必须同步更新 `LocalizationSettings.SupportedCultures` Config，确保系统能够正确切换语言环境。

**审计日志合规**

系统关键操作（如创建Alert、更新Alert、删除Alert）必须记录审计日志。`API/Handlers/UserManagement/AlertHandler.cs` 中 `CreateAlert`、`UpdateAlert`、`DeleteAlerts` 方法均调用 `LogAudit(AuditAction.Create, AuditResource.Alert, alert.Id)` 记录操作者、操作类型、资源类型与资源 ID，满足可追溯性要求。

---

## 8. 优先级路线图

AgentInsightService 是一个面向 AI Agent 可Observation性与Payment管理的后端服务系统，提供 Trace、Observation、Score 等可Observation性数据的采集、存储与查询能力，支持自定义 Alert Alert规则，并通过 Agent Config、Agent Session 管理、Report AgentReport等功能支撑 AI Agent 的全生命周期管理。本章节基于代码仓库的实际实现，按 P0-P3 四个优先级定义功能路线图，确保核心业务闭环优先交付，增强功能与优化项按序推进。

### 8.1. P0 核心功能 (必须实现)

P0 级别功能构成 AgentInsightService 的最小可用产品闭环，涵盖用户认证、Payment下单、Trace 数据查询与Alert触发四大核心链路，任何一项缺失都将导致系统无法独立运行。

#### 8.1.1. 用户认证（注册/登录/JWT）

用户认证是系统安全的基础。`UserHandler` 提供注册（`CreateUser`）、登录（`Login`）与登出（`Logout`）接口 [API/Handlers/UserManagement/UserHandler.cs]。登录成功后，系统通过 `UserService.CreateRefreshTokenAndSetHttpContext` 签发 JWT Token 并将刷新Token写入 HTTP Context，实现Session保持与 Token 刷新机制 [API/Common/Services/UserService.cs]。密码重置通过 `UserHandler.ResetPassword` 实现。注册流程中，`UserHandler.CreateUser` 会调用Captcha服务校验Captcha，验证失败将拒绝注册。此外，`UserHandler.BindWeChat` 支持微信小程序登录绑定，扩展了第三方认证渠道。

#### 8.1.2. Payment下单与回调处理

Payment管理是系统商业闭环的核心。`OrderHandler.PlaceOrder` 创建订单，支持微信Payment（Native、JSAPI、MiniProgram）与Payment宝Payment（InstantTrade），分别由 `PaymentService.GetNativeResponse`、`GetWeChatJSAPIResponse`、`WeChatMiniProgramPay` 与 `GetAlipayInstantTrade` 实现 [API/Handlers/PaymentManagement/OrderHandler.cs]、[API/Common/Services/PaymentService.cs]。Payment回调由 `NotifyHandler.ProcessWeChatNotify` 与 `ProcessAlipayNotify` 处理，完成签名验证、订单状态更新（`PaymentService.UpdateOrderState`）与OrgPrivilege（组织特权）更新（`PaymentService.UpdateOrgPrivilege`）[API/Handlers/PaymentManagement/NotifyHandler.cs]。Payment交易记录通过 `SaveWeChatTransaction` 与 `SaveAlipayTransaction` 持久化，确保账务可追溯。

#### 8.1.3. Trace 数据查询

Trace 查询是 AI Agent 可Observation性的核心能力。`MetricsHandler.GetTraces` 支持多维度过滤、排序与分页，通过 `TraceFilterBuilder.BuildFilters` 构建过滤条件，并调用 `ClickHouseClient.QueryAsync` 从 ClickHouse 查询 Trace 数据 [API/Handlers/DataManagement/MetricsHandler.cs]。查询结果包含 Trace 的 Metrics 数据（如 Token 消耗、延迟、错误率等），供开发者分析模型调用性能。此外，`GetObservationsAsync` 与 `GetScoresAsync` 分别提供 Observation 与 Score 的查询能力，`ModelHandler.GetModels` 提供模型定义查询 [API/Handlers/DataManagement/ModelHandler.cs]。

#### 8.1.4. Alert规则 CRUD 与触发

Alert功能使用户能够基于 Token 消耗、延迟、错误率等指标自定义监控规则。`AlertHandler` 提供Alert规则的创建（`CreateAlert`）、更新（`UpdateAlert`）、删除（`DeleteAlerts`）与查询（`GetAlerts`）[API/Handlers/UserManagement/AlertHandler.cs]。Alert条件评估由 `AlertService` 实现，核心方法 `EvaluateField` 与 `IsConditionMet` 基于 `AlertField`（如 `TotalTokens`、`TotalCost`、`ErrorCount`、`Latency`）对聚合后的 Metrics 数据进行阈值判断 [API/Common/Services/AlertService.cs]。触发后的通知通过 `SystemAlertHandler`（系统通知）与 `SMSAlertHandler`（短信通知）分发，Alert记录可通过 `GetAlertRecords` 查询并标记已读（`ReadAlertRecords`）[API/Handlers/UserManagement/AlertHandler.cs]。

### 8.2. P1 重要功能

P1 级别功能在 P0 基础上完善多租户管理、API 访问控制与 Agent 生命周期管理，是系统从单机可用走向多组织协作的关键能力。

#### 8.2.1. 组织与项目管理

组织与项目是资源隔离的基本单元。`OrganizationHandler` 提供组织的创建（`CreateOrganization`）、查询（`GetOrganizations`）、更新（`UpdateOrganization`）与删除（`DeleteOrganization`）[API/Handlers/UserManagement/OrganizationHandler.cs]。`ProjectHandler` 提供项目的 CRUD 操作（`CreateProject`、`GetProjects`、`UpdateProject`、`DeleteProject`）[API/Handlers/UserManagement/ProjectHandler.cs]。成员邀请与管理通过 `UserHandler.InviteMember`、`GetInvitations`、`DeleteInvitation` 实现，角色分配通过 `AssignRole` 完成 [API/Handlers/UserManagement/UserHandler.cs]。组织角色包括 `PGRole.OWNER` 等，用于控制订单查询、成员管理等敏感操作的Privilege边界。

#### 8.2.2. API Key 管理

API Key 是普通用户访问系统的主要认证方式。`UserHandler` 提供 API Key 的创建（`CreateApiKey`）、查询（`GetApiKeys`）与删除（`DeleteApiKey`）[API/Handlers/UserManagement/UserHandler.cs]。API Key 由 AccessKey 与 SecretKey 组成，登录时通过 `AgentInsightTransformLogic` 解析 Authorization 头中的 Basic Auth 凭证，校验 AccessKey 是否存在且 SecretKey 匹配 [API/Handlers/UserManagement/UserHandler.cs]。无效的 API Key 将抛出 `ApiKeyInvalidException`（errorCode=100038）异常。API Key 的认证与路由由 `AgentInsightTransformProvider` 统一处理，支持 JWT 与 API Key 两种认证方式 [API/System/Handlers/AgentInsightTransformProvider.cs]。

#### 8.2.3. Agent Config与 Agent Session 管理

Agent Config管理通过 `AgentConfigHandler` 提供Config的创建或更新（`CreateOrUpdateConfig`）、查询（`GetConfig`）与删除（`DeleteConfig`）[API/Controllers/AgentManagement/AgentConfigController.cs]。Config内容为 JSON 字符串，包含 `datasource`（数据源连接信息）与 `defaulttemplateid`（默认模板 ID）字段。Agent Agent Session 管理由 `AgentSessionHandler` 提供Session的查询（`GetSessions`）、创建或更新（`CreateOrUpdateSession`）与删除（`DeleteSessions`）[API/Handlers/AgentManagement/AgentSessionHandler.cs]。Agent Session 管理支撑 AI Agent 的对话上下文持久化，是 Agent 全生命周期管理的重要组成部分。

#### 8.2.4. 产品管理

产品管理是Payment链路的前置依赖。`ProductHandler` 提供产品列表查询（`GetProducts`）与产品时长查询（`GetProductDurations`）[API/Handlers/ProductManagement/ProductHandler.cs]。产品转换计算由 `OrderHandler.GetProductConversion` 实现，用于处理不同产品/时长之间的价格换算 [API/Handlers/PaymentManagement/OrderHandler.cs]。产品与时长数据在 `PlaceOrder` 流程中被校验（`ProductId`、`DurationId`），确保订单创建时引用的产品与时长有效。

#### 8.2.5. Captcha服务

Captcha服务由 `CaptchaHandler` 提供，支持图形Captcha、短信Captcha与邮箱Captcha三种类型 [API/Handlers/UserManagement/CaptchaHandler.cs]。Config规格中定义：`CaptchaLength=5`（图形Captcha长度）、`SmsCodeLength=6`（短信Captcha长度）、`EmailCodeLength=6`（邮箱Captcha长度）、`ExpireSeconds=300`（过期时间）、`ResendInterval=60`（重发间隔）。注册流程中，`UserHandler.CreateUser` 会调用 `_captchaService.ValidateCaptcha` 校验Captcha，验证失败将拒绝注册 [API/Handlers/UserManagement/UserHandler.cs]。

### 8.3. P2 增强功能

P2 级别功能在核心链路稳定后，为用户提供更丰富的运营工具与外部渠道集成能力，提升系统的实用性与可运营性。

#### 8.3.1. Bulletin管理

Bulletin管理由 `BulletinHandler` 实现，提供Bulletin的 CRUD、审批、修订与关闭功能 [API/Handlers/ToolsManagement/BulletinHandler.cs]。Bulletin管理面向组织管理员/所有者，用于向组织成员发布系统通知、维护Bulletin或产品动态。审批流程确保Bulletin内容在发布前经过审核，修订功能支持对已发布Bulletin进行内容更新，关闭功能用于下架过期Bulletin。

#### 8.3.2. 微信消息处理

微信消息处理由 `WeChatHandler.ProcessMessage` 实现 [API/Handlers/ToolsManagement/WeChat/WeChatHandler.cs]。该功能支持接收并处理来自微信渠道的消息，包括文本消息、事件推送等。结合用户认证中的微信小程序登录绑定（`UserHandler.BindWeChat`），微信消息处理为组织管理员提供了通过微信渠道与系统交互的能力，例如接收Alert通知或进行简单的业务查询。

#### 8.3.3. Agent Report AgentReport

Agent Report AgentReport管理由 `AgentReportHandler` 提供，对应 HTTP 端点包括 `GET /api/agent/report`（获取模板列表）、`GET /api/agent/report/delete`（删除模板）与 `POST /api/agent/report`（创建或更新模板）[API/Controllers/AgentManagement/AgentReportController.cs]。模板定义了 Agent 报告的生成格式与内容结构，与 `AgentConfig` 中的 `defaulttemplateid` 字段关联。当模板不存在时，系统抛出 `TemplateNotFoundException`（errorCode=150023）异常；模板名为空时抛出 `TemplateNameEmptyException`（errorCode=150024）异常。

#### 8.3.4. 用户Config管理

用户Config管理由 `UserConfigHandler` 提供，支持Config的查询（`Get`）、创建（`Create`）、更新（`Update`）与删除（`Delete`）[API/Controllers/UserManagement/UserConfigController.cs]。Config类型通过 `ConfigType` 枚举区分：`0=User`（用户级）、`1=Organization`（组织级）、`2=Project`（项目级）。Config内容为 JSON 格式，可按 `orgId`、`projectId` 与 `type` 维度进行查询，为不同层级的用户提供个性化的Config存储能力。

### 8.4. P3 优化与工具

P3 级别功能聚焦系统自身的可运维性、可扩展性与全球化能力，为系统的长期稳定运行与多区域部署提供支撑。

#### 8.4.1. 健康检查

健康检查由 `HealthController.Get` 实现 [API/Controllers/ToolsManagement/HealthController.cs]。该端点用于探活检测，返回系统的运行状态，供负载均衡器、容器编排平台（如 Kubernetes）或外部监控系统定期调用。健康检查是系统运维的基础设施能力，确保在服务异常时能够被及时发现并触发自动恢复流程。

#### 8.4.2. 国际化支持

国际化支持基于 `My.Extensions.Localization.Json` 技术栈实现，通过 JSON 资源文件管理多语言翻译。系统当前以中文为主要界面语言，国际化能力为后续扩展英文等多语言版本提供基础架构支撑。Config项 `LocalizationResourcePaths = ['Configurations', 'Resources']` 指定了本地化资源文件的扫描目录，确保多语言资源能够被正确加载。

#### 8.4.3. BullMqService

异步任务队列由 `BullMqService` 实现，基于 Redis 提供 BullMQ 风格的任务入队、出队与确认机制 [API/Common/Services/BullMqService.cs]。核心方法包括 `EnqueueTraceIngestionAsync`（Trace 数据摄入异步任务）、`AcknowledgeTraceIngestionAsync`（任务确认）与 `EnqueueProjectDeleteAsync`（项目删除异步任务）。异步任务队列将 Trace 数据摄入与项目删除等耗时操作从请求链路中剥离，提升 API 响应速度与系统吞吐量。技术栈中的 `StackExchange.Redis` 为 Redis 客户端实现，支撑队列的可靠性与持久化。

#### 8.4.4. 优先级汇总

| 优先级 | 功能领域 | 关键能力 | 支撑代码路径 |
|--------|---------|---------|-------------|
| P0 | 用户认证 | 注册/登录/JWT/API Key | `API/Handlers/UserManagement/UserHandler.cs`、`API/Common/Services/UserService.cs` |
| P0 | Payment管理 | 微信/Payment宝下单与回调 | `API/Common/Services/PaymentService.cs`、`API/Handlers/PaymentManagement/NotifyHandler.cs` |
| P0 | 可Observation性 | Trace/Observation/Score 查询 | `API/Handlers/DataManagement/MetricsHandler.cs` |
| P0 | Alert | 规则 CRUD 与条件触发 | `API/Handlers/UserManagement/AlertHandler.cs`、`API/Common/Services/AlertService.cs` |
| P1 | 组织与项目 | 多租户资源隔离 | `API/Handlers/UserManagement/OrganizationHandler.cs`、`ProjectHandler.cs` |
| P1 | API Key | 创建/查询/删除 | `API/Handlers/UserManagement/UserHandler.cs` |
| P1 | Agent 管理 | Config与 Session | `API/Handlers/AgentManagement/AgentConfigHandler.cs`、`AgentSessionHandler.cs` |
| P1 | 产品管理 | 产品与时长查询 | `API/Handlers/ProductManagement/ProductHandler.cs` |
| P1 | Captcha | 图形/短信/邮箱 | `API/Handlers/UserManagement/CaptchaHandler.cs` |

| P2 | Bulletin管理 | CRUD/审批/修订/关闭 | `API/Handlers/ToolsManagement/BulletinHandler.cs` |
| P2 | 微信消息 | 消息处理 | `API/Handlers/ToolsManagement/WeChat/WeChatHandler.cs` |
| P2 | Report AgentReport | 模板 CRUD | `API/Handlers/AgentManagement/AgentReportHandler.cs` |
| P2 | 用户Config | 多级Config管理 | `API/Handlers/UserManagement/UserConfigHandler.cs` |
| P3 | 健康检查 | 探活检测 | `API/Controllers/ToolsManagement/HealthController.cs` |
| P3 | 国际化 | 多语言资源 | `My.Extensions.Localization.Json` |
| P3 | 异步队列 | Trace 摄入/项目删除 | `API/Common/Services/BullMqService.cs` |

上述优先级划分遵循"核心闭环优先、协作能力次之、运营工具增强、基础设施兜底"的原则，确保系统在每一阶段都能交付可用的业务价值。

---

## 9. 风险与依赖

AgentInsightService 是一个面向 AI 应用开发者的可Observation性与订阅管理平台，集成微信Payment与Payment宝Payment，支持订单创建、Payment回调处理、OrgPrivilege（组织特权）自动更新，并提供 Trace 数据查询、Alert管理、Agent Config等核心功能。本章节系统梳理 AgentInsightService 在外部依赖、技术债务与安全风险三个维度的关键风险点，为后续架构演进与运维保障提供决策依据。

### 9.1. 外部依赖风险

AgentInsightService 的核心业务链路高度依赖多个外部服务与基础设施组件，任一环节的可用性波动都可能直接影响Payment闭环、数据摄入与查询体验。

#### 9.1.1. 微信Payment API 可用性与签名逻辑一致性

微信Payment是 AgentInsightService 的主要Payment渠道之一，支持 Native、JSAPI、MiniProgram 三种Payment模式，分别由 `PaymentService.GetNativeResponse`、`GetWeChatJSAPIResponse`、`WeChatMiniProgramPay` 实现 [API/Common/Services/PaymentService.cs]。Payment回调入口 `NotifyController.WeChatNotify` 接收微信服务器推送的异步通知，先调用 `_handler.ExamineWeChatRequest` 校验请求签名，再反序列化 `WeChatNotify` 消息体并交由 `ProcessWeChatNotify` 处理 [API/Controllers/PaymentManagement/NotifyController.cs]。

ChatNotify` 消息体并交由 `ProcessWeChatNotify` 处理 [API/Controllers/PaymentManagement/NotifyController.cs]。

该链路的首要风险在于微信Payment API 的可用性：微信Payment网关为外部封闭系统，其可用性不受 AgentInsightService 控制。当微信Payment接口出现超时或不可用时，订单创建接口 `PlaceOrder` 将同步失败，用户无法完成Payment流程。此外，签名逻辑的一致性风险同样关键——微信Payment要求请求签名与回调验签使用同一套密钥与签名算法，若微信侧更新签名协议或 AgentInsightService 侧Config的商户密钥（[已移除幻觉符号] Key）不一致，将导致回调验签失败，`ExamineWeChatRequest` 抛出 `ExceptionCodes.[已移除幻觉符号]` 异常，Payment结果无法被系统确认，进而影响 `OrgPrivilege` 的自动更新。

#### 9.1.2. Payment宝网关幂等处理

Payment宝Payment由 `PaymentService.GetAlipayInstantTrade` 发起 [API/Common/Services/PaymentService.cs]，回调入口 `NotifyController.[已移除幻觉符号]` 接收Payment宝异步通知并调用 `Process[已移除幻觉符号]` 处理 [API/Controllers/PaymentManagement/NotifyController.cs]。Payment宝网关的通知机制采用"至少一次"投递语义，同一笔交易可能重复发送回调通知。若 AgentInsightService 未做幂等处理，重复回调将导致订单状态被重复更新、`OrgPrivilege` 被重复延长，造成业务数据不一致。

次"投递语义，同一笔交易可能重复发送回调通知。若 AgentInsightService 未做幂等处理，重复回调将导致订单状态被重复更新、`OrgPrivilege` 被重复延长，造成业务数据不一致。

当前实现中，`Process[已移除幻觉符号]` 依赖 `PaymentService.UpdateOrderState` 更新订单状态 [API/Handlers/PaymentManagement/NotifyHandler.cs]，但订单状态更新的幂等性取决于订单当前状态与回调状态的比对逻辑。若该逻辑未覆盖"已Payment订单再次收到Payment成功通知"的场景，则存在重复处理风险。此外，Payment宝网关的签名验签依赖 [已移除幻觉符号] 密钥对，密钥轮换或Config错误将直接导致回调验签失败。

#### 9.1.3. ClickHouse 连接池与性能

ClickHouse 是 AgentInsightService 的 Trace 数据存储与查询引擎，连接字符串Config为 `Host=${[已移除幻觉符号]};Port=${[已移除幻觉符号]};Username=${[已移除幻觉符号]};Password=${[已移除幻觉符号]};Database=${[已移除幻觉符号]};[已移除幻觉符号]=10;[已移除幻觉符号]=50;[已移除幻觉符号]=30;[已移除幻觉符号]=60`。`MetricsHandler` 通过 `ClickHouseClient` 与 `ISqlSugarClient`（keyed service `AgentInsightConst.KeyedService_ClickHouseDb`）访问 ClickHouse 数据 [API/Handlers/DataManagement/MetricsHandler.cs]。

htConst.KeyedService_ClickHouseDb`）访问 ClickHouse 数据 [API/Handlers/DataManagement/MetricsHandler.cs]。

连接池上限 `[已移除幻觉符号]=50` 意味着在高峰查询时段，若并发查询请求超过 50 个，后续请求将排队等待连接释放。当 Trace 查询涉及复杂过滤条件（如 `TraceFilterBuilder.BuildFilters` 生成的多条件组合查询）时，单次查询耗时可能显著增加，进一步加剧连接池竞争。`MetricsHandler` 已针对超时场景抛出 `ExceptionCodes.[已移除幻觉符号]` 与 `ExceptionCodes.[已移除幻觉符号]` [API/Handlers/DataManagement/MetricsHandler.cs]，但连接池耗尽导致的排队等待可能使请求在超时阈值内无法获得连接，最终表现为查询超时。

#### 9.1.4. Redis 高可用

Redis 在 AgentInsightService 中承担消息队列与缓存双重角色。`BullMqService` 基于 Redis 实现 BullMQ 风格的任务入队/出队/确认，支持 Trace 数据摄入（`EnqueueTraceIngestionAsync`）与项目删除（`EnqueueProjectDeleteAsync`）等异步任务 [API/Common/Services/BullMqService.cs]。同时，`IMemoryCache` 被广泛用于用户Session、API Key 等数据的进程内缓存。

Redis 的单点故障将直接导致消息队列不可用：Trace 数据摄入任务无法入队，数据写入链路中断；项目删除任务无法执行，数据清理停滞。若 Redis 采用主从架构但未启用哨兵或集群模式，主节点故障时自动故障转移能力不足，恢复时间将取决于人工介入速度。此外，`BullMqService` 的任务确认机制（`AcknowledgeTraceIngestionAsync`）依赖 Redis 的原子操作，若 Redis 网络分区导致确认消息丢失，任务可能被重复消费。

llMqService` 的任务确认机制（`AcknowledgeTraceIngestionAsync`）依赖 Redis 的原子操作，若 Redis 网络分区导致确认消息丢失，任务可能被重复消费。

| 外部依赖 | 关键风险 | 影响范围 | 缓解措施建议 |
|---------|---------|---------|-------------|
| 微信Payment API | 网关可用性不可控；签名协议变更 | 订单创建、Payment回调、OrgPrivilege 更新 | 增加超时与重试机制；定期校验签名逻辑；ConfigAlert监控 |
| Payment宝网关 | 重复回调通知；密钥轮换 | 订单状态一致性、OrgPrivilege 重复延长 | 实现回调幂等处理；密钥管理规范化 |
| ClickHouse | 连接池耗尽；复杂查询性能下降 | Trace 查询、Observation/Score 查询 | 监控连接池使用率；优化查询语句；增加只读副本 |
| Redis | 单点故障；网络分区 | 消息队列、异步任务、缓存 | 部署高可用架构（哨兵/集群）；Config持久化 |

### 9.2. 技术债务

#### 9.2.1. TraceFilterBuilder 复杂查询导致 ClickHouse 性能下降

`MetricsHandler.[已移除幻觉符号]` 调用 `TraceFilterBuilder.BuildFilters(body.Filter)` 构建查询过滤条件 [API/Handlers/DataManagement/MetricsHandler.cs]。`TraceFilterBuilder` 支持多维度过滤（如时间范围、Token 用量、Cost、Latency、ErrorCount 等），但过滤条件的组合复杂度与查询性能呈负相关。当用户同时指定多个过滤条件且每个条件涉及范围查询或模糊匹配时，生成的 ClickHouse SQL 可能包含多个子查询或大范围扫描，导致查询延迟显著增加。

），但过滤条件的组合复杂度与查询性能呈负相关。当用户同时指定多个过滤条件且每个条件涉及范围查询或模糊匹配时，生成的 ClickHouse SQL 可能包含多个子查询或大范围扫描，导致查询延迟显著增加。

该问题的技术债务属性体现在：`TraceFilterBuilder` 的过滤逻辑与 ClickHouse 的查询优化器之间缺乏有效的协同机制。例如，对 `TotalTokens` 或 `TotalCost` 等数值字段的范围过滤，若未在 ClickHouse 表中建立对应的跳数索引或物化视图，查询将退化为全表扫描。此外，`ParseSelectFields` 与 `[已移除幻觉符号]` 的字段映射逻辑若与 ClickHouse 表结构脱节，可能生成低效的排序操作。

#### 9.2.2. Payment回调内存重试无持久化

Payment回调处理链路中，`NotifyHandler.ProcessWeChatNotify` 与 `Process[已移除幻觉符号]` 在回调处理失败时采用内存重试机制，最多重试 3 次 [API/Handlers/PaymentManagement/NotifyHandler.cs]。该机制的技术债务在于：重试状态仅保存在进程内存中，一旦服务重启或进程崩溃，未完成的重试任务将全部丢失。

具体风险场景包括：Payment回调已到达 AgentInsightService，但 `UpdateOrderState` 因数据库临时故障失败，内存重试 3 次后仍失败，此时回调处理返回失败响应。微信/Payment宝网关会根据返回结果决定是否重新推送回调，但若 AgentInsightService 在重试期间重启，内存中的重试计数清零，网关重新推送的回调将被当作首次回调处理，可能引发重复处理。更严重的是，若服务在重试窗口内持续不可用，且网关的重推策略（通常为有限次数）耗尽，该笔Payment将永远无法确认，用户已付款但 `OrgPrivilege` 未更新。

#### 9.2.3. API Key 内存缓存多实例一致性问题

`UserHandler` 与 `UserService` 使用 `IMemoryCache` 缓存用户Session与 API Key 数据 [API/Handlers/UserManagement/UserHandler.cs]。`IMemoryCache` 为进程内缓存，在单实例部署下工作正常，但 AgentInsightService 若水平扩展为多实例部署，各实例的缓存相互独立，将产生一致性问题。

典型场景：用户在实例 A 上创建了新的 API Key，实例 A 的缓存立即更新；但实例 B 的缓存仍保留旧数据，当用户通过实例 B 访问系统时，`AgentInsightTransformProvider` 的 API Key 校验逻辑可能读取到过期缓存，导致新创建的 API Key 在部分实例上无法通过认证。同理，用户注销或密码重置后，其他实例的缓存中仍可能存在有效Session，造成已注销用户仍可访问系统。

| 技术债务项 | 风险描述 | 影响范围 | 建议改进方向 |
|-----------|---------|---------|-------------|
| TraceFilterBuilder 复杂查询 | 多条件组合查询导致 ClickHouse 性能下降 | Trace 查询、Alert评估 | 优化过滤条件生成逻辑；增加 ClickHouse 索引；引入查询超时熔断 |
| Payment回调内存重试 | 服务重启导致重试任务丢失，Payment结果无法确认 | Payment闭环、OrgPrivilege 更新 | 引入持久化消息队列（如 BullMqService）；增加回调状态持久化 |
| API Key 内存缓存 | 多实例部署下缓存不一致，认证结果因实例而异 | API Key 认证、用户Session | 替换为分布式缓存（如 Redis）；或启用缓存失效广播 |

### 9.3. 安全风险

#### 9.3.1. [已移除幻觉符号] 需安全生产

Captcha服务由 `CaptchaHandler` 实现，支持图形Captcha、短信Captcha、邮箱Captcha三种类型 [API/Handlers/UserManagement/CaptchaHandler.cs]。Config项 `CaptchaSetting.[已移除幻觉符号] = 60` 表明Captcha重发间隔为 60 秒，`CaptchaSetting.[已移除幻觉符号] = 300` 表明Captcha有效期为 300 秒，`CaptchaSetting.[已移除幻觉符号] = 6` 与 `CaptchaSetting.[已移除幻觉符号] = 6` 分别定义短信与邮箱Captcha长度。

当前Captcha策略仅包含频率限制（同一手机号/邮箱 60 秒内不可重发），但缺少每日总量限制。攻击者可利用该漏洞，通过自动化脚本在一天内对大量手机号或邮箱发起Captcha请求，造成短信/邮件服务资源被恶意消耗，产生经济成本；同时，攻击者也可对同一手机号在 60 秒间隔内持续请求，绕过频率限制实现短信轰炸。

| 安全风险项 | 风险描述 | 影响范围 | 建议改进方向 |
|-----------|---------|---------|-------------|
| [已移除幻觉符号] | 密钥泄露可导致 Token 伪造 | 全部认证接口 | 使用密钥管理服务（[已移除幻觉符号]）存储；定期轮换；环境隔离 |
| Payment密钥明文存储 | 数据库泄露导致Payment密钥暴露 | Payment链路 | 使用 AES 加密后存储；加密密钥与数据库凭据分离 |
| Captcha无每日总量限制 | 短信/邮件轰炸、资源滥用 | Captcha服务、短信/邮件通道 | 增加每日请求上限；引入行为验证（如滑块）；IP 维度限流 |

---

## 10. 需求Trace矩阵

AgentInsightService 是一个面向 AI 应用开发者的可Observation性与模型调用性能分析平台，普通用户通过 API Key（Basic Auth 或 Bearer JWT）认证访问系统，管理自己的 Organization、Project、ApiKey，查看 Trace 数据与Alert记录。本章节通过需求Trace矩阵，FRNFR逐一映射到具体的代码实现位置，确保从需求到代码的完整可追溯性，为需求变更影响分析、代码审查与测试覆盖提供依据。

### 10.1. FR Trace

FR映射至对应的 Controller 端点与 Handler 方法，并标注关键实现文件路径。所有端点均来自 AST 扫描结果，Handler 方法引用来自代码仓库学习摘要。

| 需求编号 | 需求描述 | HTTP 端点 | Controller 方法 | Handler 方法 | 实现文件 |
|---------|---------|-----------|----------------|-------------|---------|
| FR-001 | 用户注册 | POST /api/user | `UserController.Create` | `CreateUser` | `API/Handlers/UserManagement/UserHandler.cs` |
| FR-002 | 用户登录（密码/短信/微信/APIKey） | POST /api/user/login | `UserController.Login` | `Login` | `API/Handlers/UserManagement/UserHandler.cs` |
| FR-003 | 用户登出 | POST /api/user/logout | `UserController.Logout` | `Logout` | `API/Handlers/UserManagement/UserHandler.cs` |
| FR-004 | 获取当前用户信息 | GET /api/user | `UserController.Get` | `GetUser` | `API/Handlers/UserManagement/UserHandler.cs` |
| FR-005 | 更新用户信息 | POST /api/user/update | `UserController.Update` | `UpdateUser` | `API/Handlers/UserManagement/UserHandler.cs` |
| FR-006 | 重置密码 | POST /api/user/resetpassword | `UserController.ResetPassword` | `ResetPassword` | `API/Handlers/UserManagement/UserHandler.cs` |
| FR-007 | 微信小程序登录绑定 | POST /api/user/bind/wechat | `UserController.Bind` | `BindWeChat` | `API/Handlers/UserManagement/UserHandler.cs` |
| FR-008 | 解绑微信 | GET /api/user/unbind/wechat | `UserController.Unbind` | `UnbindWeChat` | `API/Handlers/UserManagement/UserHandler.cs` |
| FR-009 | 角色分配 | POST /api/user/role | `UserController.AssignRole` | `AssignRole` | `API/Handlers/UserManagement/UserHandler.cs` |
| FR-010 | 成员邀请 | POST /api/user/invite | `UserController.Invite` | `InviteMember` | `API/Handlers/UserManagement/UserHandler.cs` |
| FR-011 | 查询邀请列表 | GET /api/user/invitation | `UserController.Get` | `GetInvitations` | `API/Handlers/UserManagement/UserHandler.cs` |
| FR-012 | 删除邀请 | POST /api/user/invitation/delete | `UserController.DeleteInvitation` | `DeleteInvitation` | `API/Handlers/UserManagement/UserHandler.cs` |
| FR-013 | 创建 API Key | POST /api/user/apikey | `UserController.CreateApiKey` | `CreateApiKey` | `API/Handlers/UserManagement/UserHandler.cs` |
| FR-014 | 查询 API Key 列表 | GET /api/user/apikey | `UserController.Get` | `GetApiKeys` | `API/Handlers/UserManagement/UserHandler.cs` |
| FR-015 | 删除 API Key | POST /api/user/apikey/delete | `UserController.DeleteApiKey` | `DeleteApiKey` | `API/Handlers/UserManagement/UserHandler.cs` |
| FR-016 | 月度 Agent 配额扣减 | GET /api/user/privilege/agent/deduct | `UserController.DeductMonthlyAgentRate` | `DeductMonthlyAgentRate` | `API/Handlers/UserManagement/UserHandler.cs` |
| FR-017 | 月度 Agent 配额校验 | GET /api/user/privilege/agent/validate | `UserController.ValidateMonthlyAgentRate` | `ValidateMonthlyAgentRate` | `API/Handlers/UserManagement/UserHandler.cs` |
| FR-018 | 获取产品列表 | GET /api/product | `ProductController.Get` | `GetProducts` | `API/Handlers/ProductManagement/ProductHandler.cs` |
| FR-019 | 获取产品时长列表 | GET /api/product/duration | `ProductController.Get` | `GetProductDurations` | `API/Handlers/ProductManagement/ProductHandler.cs` |
| FR-020 | 获取 Agent Config | GET /api/agent/config | `AgentConfigController.Get` | `GetConfig` | `API/Handlers/AgentManagement/AgentConfigHandler.cs` |
| FR-021 | 创建或更新 Agent Config | POST /api/agent/config | `AgentConfigController.Post` | `CreateOrUpdateConfig` | `API/Handlers/AgentManagement/AgentConfigHandler.cs` |
| FR-022 | 删除 Agent Config | GET /api/agent/config/delete | `AgentConfigController.Delete` | `DeleteConfig` | `API/Handlers/AgentManagement/AgentConfigHandler.cs` |
| FR-023 | 获取模型定义列表 | GET /api/data/model | `ModelController.Get` | `GetModels` | `API/Handlers/DataManagement/ModelHandler.cs` |
| FR-024 | 获取 Agent 报表模板列表/详情 | GET /api/agent/report | `AgentReportController.Get` | `GetTemplates` | `API/Handlers/AgentManagement/AgentReportHandler.cs` |
| FR-025 | 创建或更新 Agent 报表模板 | POST /api/agent/report | `AgentReportController.CreateOrUpdateTemplate` | `CreateOrUpdateTemplate` | `API/Handlers/AgentManagement/AgentReportHandler.cs` |
| FR-026 | 删除 Agent 报表模板 | GET /api/agent/report/delete | `AgentReportController.DeleteTemplates` | `DeleteTemplates` | `API/Handlers/AgentManagement/AgentReportHandler.cs` |
| FR-027 | 获取用户Config项 | GET /api/user/config | `UserConfigController.Get` | `Get` | `API/Handlers/UserManagement/UserConfigHandler.cs` |
| FR-028 | 创建用户Config | POST /api/user/config | `UserConfigController.Post` | `Create` | `API/Handlers/UserManagement/UserConfigHandler.cs` |
| FR-029 | Trace 查询（多维度过滤/排序/分页） | GET /api/data/metrics/traces | `MetricsController.Get` | `GetTraces` | `API/Handlers/DataManagement/MetricsHandler.cs` |
| FR-030 | Observation 查询 | GET /api/data/metrics/observations | `MetricsController.Get` | `GetObservationsAsync` | `API/Handlers/DataManagement/MetricsHandler.cs` |
| FR-031 | Score 查询 | GET /api/data/metrics/scores | `MetricsController.Get` | `GetScoresAsync` | `API/Handlers/DataManagement/MetricsHandler.cs` |
| FR-032 | Alert规则 CRUD | POST/GET/PUT/DELETE /api/alert | `AlertController.Post/Get/Put/Delete` | `CreateAlert`/`UpdateAlert`/`DeleteAlerts`/`GetAlerts` | `API/Handlers/UserManagement/AlertHandler.cs` |
| FR-033 | Alert条件评估 | - | - | `EvaluateField`/`IsConditionMet` | `API/Common/Services/AlertService.cs` |
| FR-034 | Alert通知（系统/短信） | - | - | `Handle` | `API/Notifications/SystemAlertHandler.cs`、`API/Notifications/SMSAlertHandler.cs` |
| FR-035 | Alert记录查询与已读标记 | GET/POST /api/alert/records | `AlertController.Get`/`AlertController.Read` | `GetAlertRecords`/`ReadAlertRecords` | `API/Handlers/UserManagement/AlertHandler.cs` |
| FR-036 | 订单创建与查询 | POST/GET /api/payment/order | `OrderController.Post`/`OrderController.Get` | `PlaceOrder`/`GetOrders`/`QueryOrder` | `API/Handlers/PaymentManagement/OrderHandler.cs` |
| FR-037 | 微信Payment（Native/JSAPI/MiniProgram） | POST /api/payment/wechat | `PaymentController.WeChatPay` | `GetNativeResponse`/`GetWeChatJSAPIResponse`/`WeChatMiniProgramPay` | `API/Common/Services/PaymentService.cs` |
| FR-038 | Payment宝Payment | POST /api/payment/alipay | `PaymentController.AlipayPay` | `GetAlipayInstantTrade` | `API/Common/Services/PaymentService.cs` |
| FR-039 | Payment回调处理（微信/Payment宝） | POST /api/payment/notify | `NotifyController.Handle` | `ProcessWeChatNotify`/`ProcessAlipayNotify` | `API/Handlers/PaymentManagement/NotifyHandler.cs` |
| FR-040 | 订单状态更新与OrgPrivilege（组织特权）更新 | - | - | `UpdateOrderState`/`UpdateOrgPrivilege` | `API/Common/Services/PaymentService.cs` |
| FR-041 | 产品转换计算 | GET /api/payment/product-conversion | `OrderController.GetProductConversion` | `GetProductConversion` | `API/Handlers/PaymentManagement/OrderHandler.cs` |
| FR-042 | Agent Agent Session 管理 | GET/POST/DELETE /api/agent/session | `AgentSessionController.Get/Post/Delete` | `GetSessions`/`CreateOrUpdateSession`/`DeleteSessions` | `API/Handlers/AgentManagement/AgentSessionHandler.cs` |
| FR-043 | Organization CRUD | POST/GET/PUT/DELETE /api/organization | `OrganizationController.Post/Get/Put/Delete` | `CreateOrganization`/`GetOrganizations`/`UpdateOrganization`/`DeleteOrganization` | `API/Handlers/UserManagement/OrganizationHandler.cs` |
| FR-044 | Project CRUD | POST/GET/PUT/DELETE /api/project | `ProjectController.Post/Get/Put/Delete` | `CreateProject`/`GetProjects`/`UpdateProject`/`DeleteProject` | `API/Handlers/UserManagement/ProjectHandler.cs` |

以 FR-001 用户注册为例，其完整调用链为：客户端发送 POST 请求至 `/api/user` 端点，`UserController.Create` 方法接收请求并调用 `UserHandler.CreateUser` 执行业务逻辑 [API/Controllers/UserManagement/UserController.cs:L43-L55]。`CreateUser` 内部完成用户信息校验、密码加密、Captcha验证及用户记录持久化。该端点标注了 `[AllowAnonymous]` 特性，表明注册操作无需预先认证 [API/Controllers/UserManagement/UserController.cs:L48]。

FR-002 用户登录的调用链为：客户端发送 POST 请求至 `/api/user/login` 端点，`UserController.Login` 方法接收 `MiniUserBody` 请求体（支持 `logintype` 区分密码/短信/微信/小程序/APIKey 五种登录方式），随后调用 `UserHandler.Login` 完成认证 [API/Controllers/UserManagement/UserController.cs:L73-L86]。登录成功后，`UserService.CreateRefreshTokenAndSetHttpContext` 负责签发 JWT Token 并设置刷新 Token 至 HTTP Context [API/Common/Services/UserService.cs]。

FR-039 Payment回调处理的调用链为：微信或Payment宝服务器发送异步通知至 `/api/payment/notify` 端点，`NotifyController.Handle` 接收回调请求并调用 `NotifyHandler.ProcessWeChatNotify` 或 `NotifyHandler.ProcessAlipayNotify` 进行验签与业务处理 [API/Handlers/PaymentManagement/NotifyHandler.cs]。`PaymentService.UpdateOrgPrivilege` 在Payment成功后更新OrgPrivilege（组织特权）。

### 10.2. NFR Trace

NFR映射至具体的代码实现，覆盖认证安全、数据持久化、消息队列、性能与可用性等维度。

| 需求编号 | 需求描述 | 实现说明 | 实现文件 |
|---------|---------|---------|---------|
| NFR-S-001 | JWT 认证 | 请求经 `AgentInsightTransformProvider` 统一处理，校验 JWT Token 有效性 | `API/System/Handlers/AgentInsightTransformProvider.cs` |
| NFR-S-002 | API Key 认证（Basic Auth） | 请求经 `AgentInsightTransformProvider` 统一处理，校验 API Key 有效性 | `API/System/Handlers/AgentInsightTransformProvider.cs` |
| NFR-D-001 | 用户数据持久化 | 用户库连接串（`UserDbConnection`），基于 PostgreSQL，敏感信息通过环境变量注入 | `API/appsettings.json`、`API/System/Handlers/AgentInsightTransformProvider.cs` |
| NFR-D-002 | 业务数据持久化 | 业务库连接串（`BusinessDbConnection`），基于 PostgreSQL，敏感信息通过环境变量注入 | `API/appsettings.json`、`API/System/Handlers/AgentInsightTransformProvider.cs` |
| NFR-D-003 | Trace数据持久化 | Trace库连接串（`TraceDbConnection`），基于 PostgreSQL，敏感信息通过环境变量注入 | `API/appsettings.json`、`API/System/Handlers/AgentInsightTransformProvider.cs` |
| NFR-D-004 | 可Observation性数据持久化 | 可Observation性库连接串（`ObservabilityDbConnection`），基于 ClickHouse，敏感信息通过环境变量注入 | `API/appsettings.json`、`API/System/Handlers/AgentInsightTransformProvider.cs` |
| NFR-Q-001 | Trace 数据摄入异步任务 | `BullMqService.EnqueueTraceIngestionAsync` 将 Trace 数据摄入任务入队，`AcknowledgeTraceIngestionAsync` 确认任务完成 | `API/Common/Services/BullMqService.cs` |
| NFR-Q-002 | 项目删除异步任务 | `BullMqService.EnqueueProjectDeleteAsync` 将项目删除任务入队，`DisposeAsync` 释放资源 | `API/Common/Services/BullMqService.cs` |
| NFR-P-001 | 数据查询性能 | 通过 ClickHouse 列式存储与 `TraceFilterBuilder.BuildFilters` 构建多维过滤条件，再通过 `ClickHouseClient.QueryAsync` 执行查询 | `API/Handlers/DataManagement/MetricsHandler.cs` |
| NFR-P-002 | 缓存机制 | 各 Controller 构造函数中注入 `IMemoryCache`，用于缓存产品列表等热点数据 | `API/Controllers/ProductManagement/ProductController.cs:L18-L20` |
| NFR-A-001 | 健康检查 | 提供 `/api/health` 端点，由 `HealthController.Get` 返回服务健康状态 | `API/Controllers/ToolsManagement/HealthController.cs` |
| NFR-A-002 | 速率限制 | 请求经 `AgentInsightTransformProvider` 处理，执行速率限制策略 | `API/System/Handlers/AgentInsightTransformProvider.cs` |
| NFR-A-003 | 用户上下文解析 | 通过 `FurionAppContextService` 解析当前请求的用户 ID（`ResolveUserId` 调用 `FurionAppContextService.UserId`） | `API/System/Handlers/AgentInsightTransformProvider.cs`、`API/Common/Services/FurionAppContextService.cs` |

NFR-S-001 与 NFR-S-002 认证安全需求由 `AgentInsightTransformProvider` 统一实现。该 Provider 作为请求管道的核心组件，负责路由类型判断（`RouteType` 枚举，`Internal = 2`）、JWT 认证、API Key 认证与速率限制 [API/System/Handlers/AgentInsightTransformProvider.cs]。User ID 解析通过 `ResolveUserId` 方法调用 `FurionAppContextService.UserId` 完成 [API/System/Handlers/AgentInsightTransformProvider.cs]。

NFR-D-001 至 NFR-D-004 数据持久化需求由四套独立数据库连接串支撑。用户库（`UserDbConnection`）、业务库（`BusinessDbConnection`）、Trace库（`TraceDbConnection`）均基于 PostgreSQL，可Observation性库（`ObservabilityDbConnection`）基于 ClickHouse。各连接串均通过环境变量注入敏感信息（如 `${DB_USER_PASSWORD}`、`${OBSERVABILITY_DB_PASSWORD}`），避免硬编码凭据。

NFR-Q-001 与 NFR-Q-002 消息队列需求由 `BullMqService` 实现。该服务基于 Redis 实现 BullMQ 风格的任务入队/出队/确认机制，`EnqueueTraceIngestionAsync` 用于 Trace 数据摄入异步任务，`EnqueueProjectDeleteAsync` 用于项目删除异步任务，`AcknowledgeTraceIngestionAsync` 用于任务确认，`DisposeAsync` 用于资源释放 [API/Common/Services/BullMqService.cs]。

NFR-P-001 数据查询性能需求通过 ClickHouse 列式存储与 `TraceFilterBuilder` 过滤条件构建器实现。`MetricsHandler.GetTraces` 调用 `TraceFilterBuilder.BuildFilters` 构建多维过滤条件，再通过 `ClickHouseClient.QueryAsync` 执行查询 [API/Handlers/DataManagement/MetricsHandler.cs]。NFR-P-002 缓存机制体现在各 Controller 构造函数中注入 `IMemoryCache`，如 `ProductController` 构造函数 [API/Controllers/ProductManagement/ProductController.cs:L18-L20]，用于缓存产品列表等热点数据，减少数据库压力。

---

## 11. 附录

本附录为 AgentInsightService 提供错误码参考。AgentInsightService 是一个面向 AI Agent 的可Observation性与管理平台，提供用户管理、组织与项目管理、Trace 数据查询、AlertConfig、Payment管理等核心功能。系统采用统一的错误码体系，所有业务异常均通过 `ExceptionCodes` 枚举定义，并在全局异常中间件中统一处理与返回。

### 11.1. A. 错误码参考

AgentInsightService 的所有业务错误码集中定义在 `Models/Common/Enums/ExceptionCodes.cs` 的 `ExceptionCodes` 枚举中。系统通过 Furion 框架的 `Oops.Oh(ExceptionCodes.XXX)` 抛出业务异常，由全局异常中间件 `API/System/Handlers/ExceptionMiddleware.cs` 统一捕获并序列化为 `ApiResponse<object>` 格式返回给客户端。

错误码按业务域划分为多个区间：`100000` 段为用户与认证相关错误，`110000` 段为Captcha与短信相关错误，`130000` 段为组织管理相关错误。下表列出全部 `ExceptionCodes` 枚举常量及其对应数值，这些错误码直接用于功能验收标准的判定和接口定义的错误响应。

| 错误码常量 | 数值 | 业务域 | 含义 |
|---|---|---|---|
| `UnAuthToken` | 100000 | User/认证 | Token 未认证或已过期，需要重新登录 |
| `EmptyUserId` | 100001 | User/认证 | 无法获取用户 ID，需要重新登录 |
| `PhoneAlreadyRegistered` | 100003 | User/认证 | 手机号已注册 |
| `RegisterFailed` | 100004 | User/认证 | 用户注册失败 |
| `InvalidPhoneOrPassword` | 100005 | User/认证 | 手机号或密码错误 |
| `EmptyPhone` | 100009 | User/认证 | 手机号不能为空 |
| `InsufficientPermission` | 100010 | User/认证 | 操作者Privilege不足 |
| `UserNameTooLong` | 100019 | User/认证 | 用户名长度超过 100 字符 |
| `EmptyInviteePhone` | 100021 | User/邀请 | 被邀请人手机号不能为空 |
| `InvalidInviteePhone` | 100022 | User/邀请 | 被邀请人手机号格式非法 |
| `RoleLevelTooHigh` | 100023 | User/Role | 不能授予高于自身等级的角色 |
| `UserAlreadyInOrganization` | 100024 | User/Org | 用户已是组织成员 |
| `InvitationAlreadyPending` | 100025 | User/邀请 | 该手机号已有待处理的邀请 |
| `InviteFailed` | 100026 | User/邀请 | 发送邀请失败 |
| `InvitationNotFound` | 100027 | User/邀请 | 邀请不存在或已被处理 |
| `RevokeInviteFailed` | 100028 | User/邀请 | 撤销邀请失败 |
| `ApiKeyNotFound` | 100031 | User/API Key | API Key 不存在 |
| `CreateApiKeyFailed` | 100032 | User/API Key | 创建 API Key 失败 |
| `DeleteApiKeyFailed` | 100033 | User/API Key | 删除 API Key 失败 |
| `MissingProjectOrOrgId` | 100035 | User/API Key | 缺少项目 ID 或组织 ID |
| `InvalidOrganizationName` | 100036 | User/Org | 组织名称不能为空 |
| `OrganizationNameTooLong` | 100037 | User/Org | 组织名称长度超过限制 |
| `OrganizationNameExists` | 100038 | User/Org | 组织名称已存在 |
| `CreateOrganizationFailed` | 100039 | User/Org | 创建组织失败 |
| `InvalidProjectName` | 100040 | User/Project | 项目名称不能为空 |
| `ProjectNameTooLong` | 100041 | User/Project | 项目名称长度超过限制 |
| `ProjectNameExists` | 100042 | User/Project | 项目名称已存在 |
| `NoOrgPermission` | 100043 | User/Org | 无组织操作Privilege |
| `CaptchaCodeInvalid` | 110000 | Captcha/短信 | 图形Captcha错误或已过期 |
| `SmsCodeInvalid` | 110001 | Captcha/短信 | 短信Captcha错误或已过期 |
| `EmailCodeInvalid` | 110002 | Captcha/短信 | 邮箱Captcha错误或已过期 |
| `SmsSendFailed` | 110003 | Captcha/短信 | 短信发送失败 |
| `EmailSendFailed` | 110004 | Captcha/短信 | 邮箱发送失败 |
| `CaptchaSendTooFrequent` | 110005 | Captcha/短信 | Captcha发送过于频繁 |
| `OrgNotFound` | 130000 | 组织管理 | 组织不存在 |
| `OrgNameEmpty` | 130001 | 组织管理 | 组织名称不能为空 |
| `OrgNameTooLong` | 130002 | 组织管理 | 组织名称长度超过限制 |
| `OrgNameDuplicate` | 130003 | 组织管理 | 组织名称已存在 |
| `OrgCreateFailed` | 130004 | 组织管理 | 创建组织失败 |
| `OrgUpdateFailed` | 130005 | 组织管理 | 更新组织失败 |
| `OrgDeleteFailed` | 130006 | 组织管理 | 删除组织失败 |

错误码的抛出与处理机制如下：

1. **抛出位置**：业务 Handler 层通过 `throw Oops.Oh(ExceptionCodes.XXX)` 抛出异常。例如，`API/Handlers/UserManagement/OrganizationHandler.cs` 中创建组织时，对组织名校验失败分别抛出 `ExceptionCodes.InvalidOrganizationName`、`ExceptionCodes.OrganizationNameTooLong`、`ExceptionCodes.OrganizationNameExists`，数据库写入异常时抛出 `ExceptionCodes.CreateOrganizationFailed`。`API/Handlers/UserManagement/ProjectHandler.cs` 中创建项目时，对项目名校验失败抛出 `ExceptionCodes.InvalidProjectName`、`ExceptionCodes.ProjectNameTooLong`、`ExceptionCodes.ProjectNameExists`，对组织Privilege校验失败抛出 `ExceptionCodes.NoOrgPermission`，对重名校验失败抛出 `ExceptionCodes.ProjectNameExists`。

2. **统一捕获**：全局异常中间件 `API/System/Handlers/ExceptionMiddleware.cs` 捕获所有 `AppFriendlyException` 异常，将其转换为 HTTP 200 响应（业务错误码通过响应体传递），响应体结构为 `ApiResponse<object>`，包含 `errorCode` 与 `errorMessage` 字段。未捕获的未知异常则返回 HTTP 500 与 `TextContent.InternalServerError` 错误消息。

3. **多语言消息映射**：错误码对应的用户可读消息定义在 `API/Resources/Text.en.json` 等资源文件中。例如，`ExceptionCodes.UnAuthToken` 对应英文消息 "Session expired, please log in again"，`ExceptionCodes.PhoneAlreadyRegistered` 对应 "This phone number is already registered"。系统根据当前请求的本地化设置自动选择对应语言的消息文本。

4. **错误码使用约定**：在接口定义与功能验收标准中，`errorCode = 0` 表示成功；`errorCode` 为上述枚举数值时表示对应业务错误。客户端应根据 `errorCode` 数值判断具体错误类型，并展示 `errorMessage` 中的用户可读提示。

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

## 1. 引言

AgentInsightService 是一个面向 AI Agent 可Observation性领域的后端服务平台，提供完整的 RESTful API 接口，覆盖用户认证、组织管理、Trace 数据查询、AlertConfig、Payment订单、Agent Config等核心功能 [API 文档摘要]。平台基于 .NET 技术栈构建，集成 [已移除幻觉符号].Standard、MediatR、Microsoft.[已移除幻觉符号]、Npgsql、[已移除幻觉符号].Redis、Yarp.[已移除幻觉符号] 等框架，并配套 Python 端 agentinsight-sdk 与 openai、pydantic 等依赖 [项目元数据]。本文档为 AgentInsightService 的技术文档，旨在为平台使用者、集成开发者及运维人员提供完整的接口说明与使用指南。

### 1.1. 编写目的

本文档旨在为 AgentInsightService 平台的使用者、集成开发者及运维人员提供全面的技术参考。文档基于对代码仓库的实际学习结果编写，详细描述了平台提供的 RESTful API 接口、认证机制、错误码体系及核心业务流程。

具体而言，本文档的编写目的包括：

1. **指导平台接入**：帮助第三方开发者快速理解 AgentInsightService 的接口规范，包括请求格式、参数定义、响应结构及认证方式，从而顺利完成与平台的集成对接。平台所有接口通过 JWT Token 或 API Key 进行认证，错误码统一在 `Models/Common/Enums/ExceptionCodes.cs` 中定义 [API 文档摘要]。

2. **规范开发流程**：为内部开发团队提供统一的接口契约，确保前后端开发、测试及联调过程中的一致性，减少因接口理解偏差导致的返工成本。

3. **提供运维参考**：为系统运维人员提供接口健康检查、AlertConfig及Payment回调等关键链路的说明，辅助日常运维与故障排查。例如健康检查接口 `GET /api/tools/health` 定义于 `API/Controllers/ToolsManagement/HealthController.cs:20` [API 文档摘要]。

查接口 `GET /api/tools/health` 定义于 `API/Controllers/ToolsManagement/HealthController.cs:20` [API 文档摘要]。

4. **沉淀技术资产**：将代码实现中的业务规则、约束条件及设计决策以文档形式固化，形成团队的技术知识库，降低人员流动带来的知识流失风险。

本文档适用于 AgentInsightService 当前版本，后续版本如有接口变更，将通过版本历史章节进行记录与说明。

### 1.2. 适用范围

本文档适用于 AgentInsightService 平台的所有外部集成方与内部开发、测试、运维人员。文档内容覆盖平台的核心 API 接口，具体适用范围如下：

**接口范围**

本文档涵盖以下核心功能模块的接口说明：

| 模块 | 接口范围 | 代码位置 |
|------|---------|---------|
| 用户认证与管理 | 用户登录、组织管理、项目创建与查询 | `API/Controllers/UserManagement/` |
| Trace 数据查询 | Trace、Observation、Score 指标查询 | `API/Controllers/DataManagement/` |
| Alert管理 | Alert规则Config、Alert记录查询 | `API/Controllers/UserManagement/AlertController.cs` |
| Payment订单 | 订单创建、微信/Payment宝回调通知 | `API/Controllers/PaymentManagement/` |
| Agent 管理 | Agent Config、报表模板、Session管理 | `API/Controllers/AgentManagement/` |
| 工具与健康检查 | 服务健康状态、短信Captcha | `API/Controllers/ToolsManagement/` |

**用户角色**

- **平台管理员**：负责组织、项目及用户管理，ConfigAlert规则，查看平台运行状态。
- **集成开发者**：通过 API 完成 Trace 数据上报、指标查询及 Agent Config管理。
- **运维人员**：通过健康检查接口监控服务状态，处理Payment回调异常。

**边界说明**

本文档不包含以下内容：前端页面使用说明、数据库表结构设计文档、部署运维手册。上述内容由各自对应的专项文档负责说明。

### 1.3. 术语与缩略语

本文档涉及以下术语与缩略语，为保持文档一致性，代码标识符一律保留英文原文：

| 术语/缩略语 | 说明 |
|------------|------|
| AgentInsightService | 本文档所描述的平台名称，为项目唯一官方名称 |
| Agent | 智能代理，平台中可Config的 AI 代理实体 |
| Trace | Trace数据，记录一次请求或任务执行的完整链路 |
| Observation | Observation数据，Trace 中的单个操作或事件记录 |
| Score | Score数据，对 Agent 执行结果的评价指标 |
| API Key | 用于 Trace 数据上报认证的密钥 |
| JWT Token | 用户登录后签发的访问Token，用于平台 API 调用 |
| RESTful API | 基于 HTTP 协议的 Representational State Transfer 风格接口 |
| Base URL | 接口请求的基础地址前缀 |
| errorCode | 接口响应中的错误码字段，0 表示成功 |
| In-Scope | 本文档覆盖的功能范围 |
| Out-of-Scope | 本文档不覆盖的功能范围 |

### 1.4. 参考文档

本文档编写过程中参考了以下资料：

1. **AgentInsightService 代码仓库**：本文档所有接口定义、参数说明及错误码均基于代码仓库的实际实现提取，包括 `API/Controllers/` 目录下的Controller定义、`Models/` 目录下的数据模型及 `Entities/` 目录下的实体定义。

2. **API 文档摘要**：基于代码学习结果生成的接口概览，覆盖认证与用户管理、Trace 数据查询、Alert管理、Payment订单、Agent 管理等核心功能模块的接口清单 [API 文档摘要]。

3. **HTTP 端点清单**：从 AST 结构感知扫描提取的端点全集，本文档必须覆盖清单中的每一个端点。例如 `API/Controllers/UserManagement/ProjectController.cs` 中定义了 4 个端点：`POST /api/user/project`、`GET /api/user/project`、`POST /api/user/project/update`、`POST /api/user/project/delete` [HTTP 端点清单]。

4. **枚举定义清单**：从 AST 提取的错误码与枚举定义全集，本文档引用的 errorCode 必须来自该清单。例如 `TransactionType` 枚举定义于 `API/Notifications/PaymentTransactionNotification.cs:9`，包含 `WeChatTransaction` 与 `AlipayTransaction` 两个值 [枚举定义清单]。

5. **Config文件技术规格**：从Config文件提取的技术规格，包括数据库连接字符串、Captcha设置等。例如 `CaptchaSetting.[已移除幻觉符号] = 5`、`CaptchaSetting.[已移除幻觉符号] = 300` [Config文件技术规格]。

### 1.5. 版本历史

| 版本 | 日期 | 修订说明 | 修订人 |
|------|------|---------|--------|
| v1.0 | 待定 | 初始版本，基于代码仓库学习结果生成，覆盖全部 HTTP 端点、认证机制及错误码体系 | 技术文档组 |

后续版本更新时，需在此表格中追加记录，说明修订内容、日期及修订人信息。版本号遵循语义化版本规范（主版本号.次版本号.修订号），主版本号变更表示接口不兼容更新，次版本号变更表示向后兼容的功能新增，修订号变更表示问题修复。

---

## 2. API 概览

本章共 78 个 HTTP 端点 (由源码 AST 确定性提取, 未经 LLM 改写)。

| # | Method | Route | Handler | Class |
|---|--------|-------|---------|-------|
| 1 | GET | `/api/agent/config` | Get | AgentConfigController |
| 2 | GET | `/api/agent/config/delete` | Delete | AgentConfigController |
| 3 | POST | `/api/agent/config` | Post | AgentConfigController |
| 4 | GET | `/api/agent/report` | GetTemplates | AgentReportController |
| 5 | GET | `/api/agent/report/delete` | DeleteTemplates | AgentReportController |
| 6 | POST | `/api/agent/report` | CreateOrUpdateTemplate | AgentReportController |
| 7 | GET | `/api/agent/session` | Get | AgentSessionController |
| 8 | GET | `/api/agent/session/delete` | Delete | AgentSessionController |
| 9 | POST | `/api/agent/session` | Post | AgentSessionController |
| 10 | GET | `/api/data/metrics/observations` | GetObservations | MetricsController |
| 11 | GET | `/api/data/metrics/scores` | GetScores | MetricsController |
| 12 | GET | `/api/data/metrics/traces` | GetTraces | MetricsController |
| 13 | POST | `/api/data/metrics/traces` | GetTraces | MetricsController |
| 14 | GET | `/api/data/model` | Get | ModelController |
| 15 | POST | `/api/payment/notify/wechatnotify` | WeChatNotify | NotifyController |
| 16 | POST | `/api/payment/notify/alipaynotify` | AlipayNotify | NotifyController |
| 17 | GET | `/api/payment/order` | Get | OrderController |
| 18 | POST | `/api/payment/order` | Place | OrderController |
| 19 | GET | `/api/payment/order/query` | Query | OrderController |
| 20 | GET | `/api/payment/order/conversion` | GetConversion | OrderController |
| 21 | GET | `/api/product` | Get | ProductController |
| 22 | GET | `/api/product/duration` | GetDuration | ProductController |
| 23 | POST | `/api/tools/bulletin` | Post | BulletinController |
| 24 | GET | `/api/tools/bulletin/agreement` | Get | BulletinController |
| 25 | GET | `/api/tools/bulletin/bulletins` | GetBulletins | BulletinController |
| 26 | GET | `/api/tools/bulletin/backend` | GetBackendBulletins | BulletinController |
| 27 | POST | `/api/tools/bulletin/approve` | ApproveBulletin | BulletinController |
| 28 | POST | `/api/tools/bulletin/revision` | ReviseBulletin | BulletinController |
| 29 | POST | `/api/tools/bulletin/close` | CloseBulletin | BulletinController |
| 30 | GET | `/api/tools/health` | Get | HealthController |
| 31 | GET | `/api/tools/wechat` | Get | WeChatController |
| 32 | POST | `/api/tools/wechat` | Post | WeChatController |
| 33 | GET | `/api/alert/config` | GetConfig | AlertController |
| 34 | GET | `/api/alert` | Get | AlertController |
| 35 | POST | `/api/alert` | Create | AlertController |
| 36 | POST | `/api/alert/update` | Update | AlertController |
| 37 | POST | `/api/alert/delete` | Delete | AlertController |
| 38 | POST | `/api/alert/record/read` | ReadRecords | AlertController |
| 39 | GET | `/api/alert/record` | GetRecords | AlertController |
| 40 | GET | `/api/captcha` | Get | CaptchaController |
| 41 | GET | `/api/captcha/sms` | GetSMSCaptcha | CaptchaController |
| 42 | POST | `/api/user/organization` | Post | OrganizationController |
| 43 | GET | `/api/user/organization` | Get | OrganizationController |
| 44 | POST | `/api/user/organization/update` | Update | OrganizationController |
| 45 | POST | `/api/user/organization/delete` | Delete | OrganizationController |
| 46 | POST | `/api/user/project` | Create | ProjectController |
| 47 | GET | `/api/user/project` | Get | ProjectController |
| 48 | POST | `/api/user/project/update` | Update | ProjectController |
| 49 | POST | `/api/user/project/delete` | Delete | ProjectController |
| 50 | GET | `/api/user/config` | Get | UserConfigController |
| 51 | POST | `/api/user/config` | Post | UserConfigController |
| 52 | POST | `/api/user/config/update` | Update | UserConfigController |
| 53 | GET | `/api/user/config/delete` | Delete | UserConfigController |
| 54 | GET | `/api/user` | Get | UserController |
| 55 | POST | `/api/user` | Create | UserController |
| 56 | POST | `/api/user/update` | Update | UserController |
| 57 | POST | `/api/user/login` | Login | UserController |
| 58 | POST | `/api/user/logout` | Logout | UserController |
| 59 | POST | `/api/user/resetpassword` | ResetPassword | UserController |
| 60 | POST | `/api/user/bind/wechat` | Bind | UserController |
| 61 | GET | `/api/user/unbind/wechat` | UnBind | UserController |
| 62 | POST | `/api/user/role` | AssignRole | UserController |
| 63 | POST | `/api/user/invite` | Invite | UserController |
| 64 | GET | `/api/user/invitation` | Get | UserController |
| 65 | POST | `/api/user/invitation/delete` | DeleteInvitation | UserController |
| 66 | POST | `/api/user/apikey` | CreateApiKey | UserController |
| 67 | GET | `/api/user/apikey` | Get | UserController |
| 68 | GET | `/api/user/privilege/agent/deduct` | DeductMonthlyAgentRate | UserController |
| 69 | GET | `/api/user/privilege/agent/validate` | ValidateMonthlyAgentRate | UserController |
| 70 | POST | `/api/user/apikey/delete` | DeleteApiKey | UserController |
| 71 | POST | `/api/agent/insight` | chat_completions |  |
| 72 | GET | `/api/sessions` | list_sessions |  |
| 73 | GET | `/api/sessions/{session_id}` | get_session |  |
| 74 | DELETE | `/api/sessions/{session_id}` | delete_session |  |
| 75 | POST | `/api/sessions/cleanup` | cleanup_expired_sessions |  |
| 76 | GET | `/api/agents` | list_agents |  |
| 77 | ANY | `/api/public` | literal_route | LiteralRoute |
| 78 | ANY | `/api/test` | literal_route | LiteralRoute |


---

## 3. 认证授权

AgentInsightService 提供完整的 RESTful API 接口，覆盖用户认证、组织管理、Trace 数据查询、AlertConfig、Payment订单、Agent Config等核心功能。所有接口通过 JWT Token 或 API Key 进行认证，错误码统一在 `Models/Common/Enums/ExceptionCodes.cs` 中定义。认证授权体系围绕用户身份验证、资源访问控制和凭证生命周期管理三个维度构建，支撑平台多组织、多项目、多 Agent 的复杂Privilege模型。

### 3.1. 认证机制

AgentInsightService 的认证体系采用双轨制设计：面向交互式用户Session的 JWT Token 认证，以及面向服务间调用的 API Key 认证。两种认证方式分别服务于不同的调用场景，但共享统一的错误码体系和异常处理机制。

#### 3.1.1. JWT Token 认证

用户登录成功后，系统签发 JWT Token 作为后续平台 API 调用的身份凭证。该 Token 在 `API/System/Handlers/AgentInsightTransformProvider.cs:42` 处被用于平台 API 调用链路的身份传递。JWT Token 承载用户身份标识、组织归属和角色信息，使后端服务能够在无状态条件下完成请求鉴权。

JWT Token 的签发入口为 `POST /api/user/login`（`API/Controllers/UserManagement/UserController.cs:42`），登录成功后返回的 Token 需要在后续请求的 `Authorization` 头中以 `Bearer <token>` 格式携带。当 Token 缺失、过期或签名校验失败时，系统返回 `[已移除幻觉符号] = 100000` 错误码，提示调用方重新认证。

#### 3.1.2. API Key 认证

除 JWT Token 外，AgentInsightService 同时支持 API Key 认证方式，适用于自动化脚本、Agent 服务等非交互式场景。API Key 的校验失败时返回 `[已移除幻觉符号] = 100038` 错误码。API Key 通常与具体用户或组织绑定，便于审计Trace和Privilege回收。

#### 3.1.3. 匿名端点

部分端点显式标记为匿名访问，无需携带任何认证凭证。典型示例为Captcha服务 `API/Controllers/UserManagement/CaptchaController.cs`，该Controller类级别标注了 `[[已移除幻觉符号]]` 特性，其 `GET /api/captcha` 和 `GET /api/captcha/sms` 接口分别用于获取图片Captcha和短信Captcha，是登录流程的前置步骤，必须在未认证状态下可访问 [API/Controllers/UserManagement/CaptchaController.cs]。

Payment回调通知端点同样采用匿名策略，`API/Controllers/PaymentManagement/NotifyController.cs` 中的 `WeChatNotify` 和 `[已移除幻觉符号]` 方法均标注 `[[已移除幻觉符号]]`，这是因为Payment平台回调无法预先获取平台 Token，需要通过签名验签机制（而非用户认证）来确保请求来源的合法性。

#### 3.1.4. Captcha机制

Captcha是登录认证链路的重要组成部分。`CaptchaController` 提供两类Captcha：

| Captcha类型 | 端点 | 用途 | Config项 |
|-----------|------|------|--------|
| 图片Captcha | `GET /api/captcha?mobile={mobile}` | 登录/注册前的图形校验 | `[已移除幻觉符号] = 5` |
| 短信Captcha | `GET /api/captcha/sms?phone={phone}` | 登录/注册/密码修改/手机号修改 | `[已移除幻觉符号] = 6` |

Captcha的过期时间为 `CaptchaSetting.[已移除幻觉符号] = 300` 秒，重发间隔为 `CaptchaSetting.[已移除幻觉符号] = 60` 秒，防止频繁请求。Captcha通过 `IMemoryCache` 存储在内存中，由 `CaptchaHandler` 统一管理创建与校验逻辑。

### 3.2. 授权流程

授权流程解决"已认证用户能做什么"的问题。AgentInsightService RBAC模型，Organization为授权边界，通过角色判定用户对特定资源的操作Privilege。

#### 3.2.1. 组织成员与角色模型

用户在平台内通过组织成员关系（`OrganizationMembership`）获得资源访问Privilege。每个成员在组织内拥有一个角色，核心角色为 `PGRole.OWNER`（组织所有者）。`API/Handlers/PaymentManagement/OrderHandler.cs` 中的订单查询逻辑清晰展示了这一授权模式：

```csharp
var membership = await DataDb.Queryable<OrganizationMembership>()
    .Where(om => om.UserId == User.Id && om.[已移除幻觉符号] == orgId)
    .[已移除幻觉符号]([已移除幻觉符号]);

if (membership == null)
{
    throw Oops.Oh(ExceptionCodes.[已移除幻觉符号]);
}

if (membership.Role != PGRole.OWNER)
{
    throw Oops.Oh(ExceptionCodes.[已移除幻觉符号]);
}
```

该代码片段体现了三层授权校验：

1. **组织归属校验**：用户必须是指定组织的成员，否则抛出 `[已移除幻觉符号]` 错误
2. **角色Privilege校验**：仅 `PGRole.OWNER` 角色可执行订单查询操作，非所有者访问抛出 `[已移除幻觉符号]`
3. **资源范围校验**：查询操作限定在用户所属组织范围内，防止越权访问其他组织数据

#### 3.2.2. 授权错误码

授权相关的错误码统一在 `Models/Common/Enums/ExceptionCodes.cs` 中定义，核心错误码如下：

| 错误码 | 常量名 | 触发场景 |
|--------|--------|---------|
| 100000 | `[已移除幻觉符号]` | Token 缺失、过期或无效 |
| 100038 | `[已移除幻觉符号]` | API Key 校验失败 |
| - | `[已移除幻觉符号]` | 用户不属于指定组织 |
| - | `[已移除幻觉符号]` | 用户角色无权访问组织资源 |
| - | `[已移除幻觉符号]` | 用户不拥有任何组织 |

#### 3.2.3. 多级资源授权

授权流程覆盖从组织到项目再到 Agent 的多级资源层级。用户创建组织（`POST /api/user/organization`，`API/Controllers/UserManagement/OrganizationController.cs:28`）后成为该组织的所有者；创建项目（`POST /api/user/project`，`API/Controllers/UserManagement/ProjectController.cs`）时需指定所属组织，项目Privilege继承组织成员关系。Agent Config、报表模板、模型定义等资源均挂载在项目或组织维度下，访问时逐级校验用户Privilege。

以 Agent Config管理为例，`API/Controllers/AgentManagement/AgentConfigController.cs` 中的 `Get`、`Post`、`Delete` 三个接口均通过 `ApiControllerBase` 基类完成用户身份解析，再经由 `AgentConfigHandler` 校验用户对目标资源的操作Privilege。所有 Handler 继承自 `ApiHandlerBase`，该基类注入了 `IAppContextService` 以获取当前认证用户上下文，确保授权判断始终基于真实用户身份而非请求参数中的用户标识。

### 3.3. Token 管理

Token 管理覆盖 Token 的签发、传递、验证和失效全生命周期，是保障认证授权体系安全性的关键环节。

#### 3.3.1. Token 签发与传递

JWT Token 在用户登录成功后由服务端签发，包含用户 ID、Org ID、角色等声明信息。客户端在后续请求中通过 HTTP `Authorization` 头携带 Token，格式为 `Bearer <token>`。服务端中间件拦截请求，解析并验证 Token 签名，将解析出的用户身份注入请求上下文，供后续 Handler 层通过 `IAppContextService` 访问。

#### 3.3.2. Token 验证链路

Token 验证在 `API/System/Handlers/AgentInsightTransformProvider.cs:42` 处被集成到平台 API 调用链路中。验证流程包括：

1. **签名验证**：使用服务端密钥校验 Token 签名，防止伪造
2. **过期检查**：校验 Token 的 `exp` 声明，过期 Token 拒绝访问
3. **用户状态检查**：确认用户仍处于活跃状态

验证失败时统一返回 `[已移除幻觉符号] = 100000` 错误码。

#### 3.3.3. 匿名回调的签名验签机制

Payment回调端点虽为匿名访问，但通过签名验签机制保障安全。`API/Controllers/PaymentManagement/NotifyController.cs` 中的 `WeChatNotify` 方法在解析回调请求体后，首先调用 `_handler.ExamineWeChatRequest(httpContext, body)` 验证微信签名，确认请求确实来自微信Payment平台，防止伪造回调。验签失败或请求体为空时抛出 `[已移除幻觉符号]` 错误码。Payment宝回调 `[已移除幻觉符号]` 同样通过 `Process[已移除幻觉符号]` 完成验签处理。

#### 3.3.4. Token 与 API Key 的适用场景对比

| 维度 | JWT Token | API Key |
|------|-----------|---------|
| 适用场景 | 用户交互式Session | 服务间调用、自动化脚本 |
| 获取方式 | 登录成功后签发 | 平台管理端生成 |
| 传递方式 | `Authorization: Bearer <token>` | 请求头或查询参数 |
| 失效机制 | 过期时间控制 | 服务端主动吊销 |
| 失败错误码 | `[已移除幻觉符号] = 100000` | `[已移除幻觉符号] = 100038` |

#### 3.3.5. 安全Config

Token 相关的安全Config通过环境变量注入，`[已移除幻觉符号] = ${[已移除幻觉符号]}` 用于敏感数据的加密保护。CaptchaConfig项（`[已移除幻觉符号] = 5`、`[已移除幻觉符号] = 6`、`[已移除幻觉符号] = 300`、`[已移除幻觉符号] = 60`）从 `appsettings.json` 读取，确保Captcha的生成策略和有效期可动态调整。

---

## 4. AgentConfigController 接口


本章共覆盖 3 个 HTTP 端点 (AST 确定性卡片, 未经 LLM 改写).


### 4.1. API-001 Get (GET `/api/agent/config`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<IActionResult> Get()
- **源码位置**: `API/Controllers/AgentManagement/AgentConfigController.cs:28`
- **Handler**: `AgentConfigController.Get`
- **HTTP**: `GET`
- **Route**: `/api/agent/config`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| — | — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷, 结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `UsageTracking = 2` | — | 来自 AST 枚举清单 |
| `GetWeChatTokenFailed = 620003` | — | 来自 AST 枚举清单 |
| `GetWeChatBasicUserInfoFailed = 620004` | — | 来自 AST 枚举清单 |
| `InvalidWeChatMessageType = 620005` | — | 来自 AST 枚举清单 |
| `GetPayCertificateFailed = 620017` | — | 来自 AST 枚举清单 |
| `## WeChatMessageType [Models/Common/Enums/WeChatEnum.cs:6]` | — | 来自 AST 枚举清单 |

**请求示例**

```json
(无 body; 参数见路径/Query)
```

**响应示例**

```json
{
  "success": true,
  "data": {},
  "message": "ok"
}
```

**相关符号 (术语表命中)**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, uuid_utils-0.16.2-cp312-cp


### 4.2. API-002 Delete (GET `/api/agent/config/delete`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<IActionResult> Delete()
- **源码位置**: `API/Controllers/AgentManagement/AgentConfigController.cs:40`
- **Handler**: `AgentConfigController.Delete`
- **HTTP**: `GET`
- **Route**: `/api/agent/config/delete`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| — | — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷, 结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `Delete` | — | 来自 AST 枚举清单 |
| `DeleteInviteFailed = 100028` | — | 来自 AST 枚举清单 |
| `DeleteApiKeyFailed = 100033` | — | 来自 AST 枚举清单 |
| `DeleteOrganizationFailed = 130006` | — | 来自 AST 枚举清单 |
| `DeleteProjectFailed = 140006` | — | 来自 AST 枚举清单 |
| `DeleteAlertFailed = 160003` | — | 来自 AST 枚举清单 |

**请求示例**

```json
(无 body; 参数见路径/Query)
```

**响应示例**

```json
{
  "success": true,
  "data": {},
  "message": "ok"
}
```

**相关符号 (术语表命中)**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, uuid_utils-0.16.2-cp312-cp


### 4.3. API-003 Post (POST `/api/agent/config`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<IActionResult> Post([FromBody] string body)
- **源码位置**: `API/Controllers/AgentManagement/AgentConfigController.cs:54`
- **Handler**: `AgentConfigController.Post`
- **HTTP**: `POST`
- **Route**: `/api/agent/config`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| body | body | 视接口 | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷, 结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `# 枚举定义清单 (AST 结构感知扫描, 错误码必须引用以下真实常量名和数值)` | — | 来自 AST 枚举清单 |
| `# 共 43 个枚举定义` | — | 来自 AST 枚举清单 |
| `## TransactionType [API/Notifications/PaymentTransactionNotification.cs:9]` | — | 来自 AST 枚举清单 |
| `WeChatTransaction` | — | 来自 AST 枚举清单 |
| `AlipayTransaction` | — | 来自 AST 枚举清单 |
| `## RouteType [API/System/Handlers/AgentInsightTransformLogic.cs:72]` | — | 来自 AST 枚举清单 |
| `None = 0` | — | 来自 AST 枚举清单 |
| `Public = 1` | — | 来自 AST 枚举清单 |
| `PublicApi = 2` | — | 来自 AST 枚举清单 |
| `## Environment [Agents/common/config.py:15]` | — | 来自 AST 枚举清单 |
| `DEVELOPMENT = "development"` | — | 来自 AST 枚举清单 |
| `STAGING = "staging"` | — | 来自 AST 枚举清单 |

**请求示例**

```json
{
  "id": "<id>"
}
```

**响应示例**

```json
{
  "success": true,
  "data": {},
  "message": "ok"
}
```

**相关符号 (术语表命中)**

- # 术语词典 (v8-P0-B 强制约束: 以下标识符必须保留原文, 禁止翻译为中文)
- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.many


---

## 5. AgentReportController 接口


本章共覆盖 3 个 HTTP 端点 (AST 确定性卡片, 未经 LLM 改写).


### 5.1. API-001 GetTemplates (GET `/api/agent/report`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<IActionResult> GetTemplates(string? id, bool includedpredefined = false, bool includedpredefinedonly = false, int page = AgentInsightConst.DefaultPage, int pageSize = AgentInsightConst.DefaultPageSize)
- **源码位置**: `API/Controllers/AgentManagement/AgentReportController.cs:35`
- **Handler**: `AgentReportController.GetTemplates`
- **HTTP**: `GET`
- **Route**: `/api/agent/report`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| — | — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷, 结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `# 枚举定义清单 (AST 结构感知扫描, 错误码必须引用以下真实常量名和数值)` | — | 来自 AST 枚举清单 |
| `# 共 43 个枚举定义` | — | 来自 AST 枚举清单 |
| `## TransactionType [API/Notifications/PaymentTransactionNotification.cs:9]` | — | 来自 AST 枚举清单 |
| `WeChatTransaction` | — | 来自 AST 枚举清单 |
| `AlipayTransaction` | — | 来自 AST 枚举清单 |
| `## RouteType [API/System/Handlers/AgentInsightTransformLogic.cs:72]` | — | 来自 AST 枚举清单 |
| `None = 0` | — | 来自 AST 枚举清单 |
| `Public = 1` | — | 来自 AST 枚举清单 |
| `PublicApi = 2` | — | 来自 AST 枚举清单 |
| `## Environment [Agents/common/config.py:15]` | — | 来自 AST 枚举清单 |
| `DEVELOPMENT = "development"` | — | 来自 AST 枚举清单 |
| `STAGING = "staging"` | — | 来自 AST 枚举清单 |

**请求示例**

```json
(无 body; 参数见路径/Query)
```

**响应示例**

```json
{
  "success": true,
  "data": {},
  "message": "ok"
}
```

**相关符号 (术语表命中)**

- # 术语词典 (v8-P0-B 强制约束: 以下标识符必须保留原文, 禁止翻译为中文)
- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.many


### 5.2. API-002 DeleteTemplates (GET `/api/agent/report/delete`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<IActionResult> DeleteTemplates(string? ids)
- **源码位置**: `API/Controllers/AgentManagement/AgentReportController.cs:48`
- **Handler**: `AgentReportController.DeleteTemplates`
- **HTTP**: `GET`
- **Route**: `/api/agent/report/delete`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| — | — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷, 结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `# 枚举定义清单 (AST 结构感知扫描, 错误码必须引用以下真实常量名和数值)` | — | 来自 AST 枚举清单 |
| `# 共 43 个枚举定义` | — | 来自 AST 枚举清单 |
| `## TransactionType [API/Notifications/PaymentTransactionNotification.cs:9]` | — | 来自 AST 枚举清单 |
| `WeChatTransaction` | — | 来自 AST 枚举清单 |
| `AlipayTransaction` | — | 来自 AST 枚举清单 |
| `## RouteType [API/System/Handlers/AgentInsightTransformLogic.cs:72]` | — | 来自 AST 枚举清单 |
| `None = 0` | — | 来自 AST 枚举清单 |
| `Public = 1` | — | 来自 AST 枚举清单 |
| `PublicApi = 2` | — | 来自 AST 枚举清单 |
| `## Environment [Agents/common/config.py:15]` | — | 来自 AST 枚举清单 |
| `DEVELOPMENT = "development"` | — | 来自 AST 枚举清单 |
| `STAGING = "staging"` | — | 来自 AST 枚举清单 |

**请求示例**

```json
(无 body; 参数见路径/Query)
```

**响应示例**

```json
{
  "success": true,
  "data": {},
  "message": "ok"
}
```

**相关符号 (术语表命中)**

- # 术语词典 (v8-P0-B 强制约束: 以下标识符必须保留原文, 禁止翻译为中文)
- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.many


### 5.3. API-003 CreateOrUpdateTemplate (POST `/api/agent/report`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<IActionResult> CreateOrUpdateTemplate([FromBody] AgentReportTemplateBody body)
- **源码位置**: `API/Controllers/AgentManagement/AgentReportController.cs:62`
- **Handler**: `AgentReportController.CreateOrUpdateTemplate`
- **HTTP**: `POST`
- **Route**: `/api/agent/report`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| body | body | 视接口 | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷, 结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `# 枚举定义清单 (AST 结构感知扫描, 错误码必须引用以下真实常量名和数值)` | — | 来自 AST 枚举清单 |
| `# 共 43 个枚举定义` | — | 来自 AST 枚举清单 |
| `## TransactionType [API/Notifications/PaymentTransactionNotification.cs:9]` | — | 来自 AST 枚举清单 |
| `WeChatTransaction` | — | 来自 AST 枚举清单 |
| `AlipayTransaction` | — | 来自 AST 枚举清单 |
| `## RouteType [API/System/Handlers/AgentInsightTransformLogic.cs:72]` | — | 来自 AST 枚举清单 |
| `None = 0` | — | 来自 AST 枚举清单 |
| `Public = 1` | — | 来自 AST 枚举清单 |
| `PublicApi = 2` | — | 来自 AST 枚举清单 |
| `## Environment [Agents/common/config.py:15]` | — | 来自 AST 枚举清单 |
| `DEVELOPMENT = "development"` | — | 来自 AST 枚举清单 |
| `STAGING = "staging"` | — | 来自 AST 枚举清单 |

**请求示例**

```json
{
  "id": "<id>"
}
```

**响应示例**

```json
{
  "success": true,
  "data": {},
  "message": "ok"
}
```

**相关符号 (术语表命中)**

- # 术语词典 (v8-P0-B 强制约束: 以下标识符必须保留原文, 禁止翻译为中文)
- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.many


---

## 6. AgentSessionController 接口


本章共覆盖 3 个 HTTP 端点 (AST 确定性卡片, 未经 LLM 改写).


### 6.1. API-001 Get (GET `/api/agent/session`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<IActionResult> Get(string? id, int page = AgentInsightConst.DefaultPage, int pageSize = AgentInsightConst.DefaultPageSize)
- **源码位置**: `API/Controllers/AgentManagement/AgentSessionController.cs:33`
- **Handler**: `AgentSessionController.Get`
- **HTTP**: `GET`
- **Route**: `/api/agent/session`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| — | — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷, 结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `UsageTracking = 2` | — | 来自 AST 枚举清单 |
| `GetWeChatTokenFailed = 620003` | — | 来自 AST 枚举清单 |
| `GetWeChatBasicUserInfoFailed = 620004` | — | 来自 AST 枚举清单 |
| `InvalidWeChatMessageType = 620005` | — | 来自 AST 枚举清单 |
| `GetPayCertificateFailed = 620017` | — | 来自 AST 枚举清单 |
| `## WeChatMessageType [Models/Common/Enums/WeChatEnum.cs:6]` | — | 来自 AST 枚举清单 |

**请求示例**

```json
(无 body; 参数见路径/Query)
```

**响应示例**

```json
{
  "success": true,
  "data": {},
  "message": "ok"
}
```

**相关符号 (术语表命中)**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, uuid_utils-0.16.2-cp312-cp


### 6.2. API-002 Delete (GET `/api/agent/session/delete`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<IActionResult> Delete(string? ids)
- **源码位置**: `API/Controllers/AgentManagement/AgentSessionController.cs:46`
- **Handler**: `AgentSessionController.Delete`
- **HTTP**: `GET`
- **Route**: `/api/agent/session/delete`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| — | — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷, 结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `Delete` | — | 来自 AST 枚举清单 |
| `DeleteInviteFailed = 100028` | — | 来自 AST 枚举清单 |
| `DeleteApiKeyFailed = 100033` | — | 来自 AST 枚举清单 |
| `DeleteOrganizationFailed = 130006` | — | 来自 AST 枚举清单 |
| `DeleteProjectFailed = 140006` | — | 来自 AST 枚举清单 |
| `DeleteAlertFailed = 160003` | — | 来自 AST 枚举清单 |

**请求示例**

```json
(无 body; 参数见路径/Query)
```

**响应示例**

```json
{
  "success": true,
  "data": {},
  "message": "ok"
}
```

**相关符号 (术语表命中)**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, uuid_utils-0.16.2-cp312-cp


### 6.3. API-003 Post (POST `/api/agent/session`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<IActionResult> Post([FromBody] AgentSessionBody body)
- **源码位置**: `API/Controllers/AgentManagement/AgentSessionController.cs:60`
- **Handler**: `AgentSessionController.Post`
- **HTTP**: `POST`
- **Route**: `/api/agent/session`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| body | body | 视接口 | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷, 结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `# 枚举定义清单 (AST 结构感知扫描, 错误码必须引用以下真实常量名和数值)` | — | 来自 AST 枚举清单 |
| `# 共 43 个枚举定义` | — | 来自 AST 枚举清单 |
| `## TransactionType [API/Notifications/PaymentTransactionNotification.cs:9]` | — | 来自 AST 枚举清单 |
| `WeChatTransaction` | — | 来自 AST 枚举清单 |
| `AlipayTransaction` | — | 来自 AST 枚举清单 |
| `## RouteType [API/System/Handlers/AgentInsightTransformLogic.cs:72]` | — | 来自 AST 枚举清单 |
| `None = 0` | — | 来自 AST 枚举清单 |
| `Public = 1` | — | 来自 AST 枚举清单 |
| `PublicApi = 2` | — | 来自 AST 枚举清单 |
| `## Environment [Agents/common/config.py:15]` | — | 来自 AST 枚举清单 |
| `DEVELOPMENT = "development"` | — | 来自 AST 枚举清单 |
| `STAGING = "staging"` | — | 来自 AST 枚举清单 |

**请求示例**

```json
{
  "id": "<id>"
}
```

**响应示例**

```json
{
  "success": true,
  "data": {},
  "message": "ok"
}
```

**相关符号 (术语表命中)**

- # 术语词典 (v8-P0-B 强制约束: 以下标识符必须保留原文, 禁止翻译为中文)
- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.many


---

## 7. AlertController 接口


本章共覆盖 7 个 HTTP 端点 (AST 确定性卡片, 未经 LLM 改写).


### 7.1. API-001 GetConfig (GET `/api/alert/config`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public IActionResult GetConfig()
- **源码位置**: `API/Controllers/UserManagement/AlertController.cs:30`
- **Handler**: `AlertController.GetConfig`
- **HTTP**: `GET`
- **Route**: `/api/alert/config`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| — | — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷, 结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `# 枚举定义清单 (AST 结构感知扫描, 错误码必须引用以下真实常量名和数值)` | — | 来自 AST 枚举清单 |
| `# 共 43 个枚举定义` | — | 来自 AST 枚举清单 |
| `## TransactionType [API/Notifications/PaymentTransactionNotification.cs:9]` | — | 来自 AST 枚举清单 |
| `WeChatTransaction` | — | 来自 AST 枚举清单 |
| `AlipayTransaction` | — | 来自 AST 枚举清单 |
| `## RouteType [API/System/Handlers/AgentInsightTransformLogic.cs:72]` | — | 来自 AST 枚举清单 |
| `None = 0` | — | 来自 AST 枚举清单 |
| `Public = 1` | — | 来自 AST 枚举清单 |
| `PublicApi = 2` | — | 来自 AST 枚举清单 |
| `## Environment [Agents/common/config.py:15]` | — | 来自 AST 枚举清单 |
| `DEVELOPMENT = "development"` | — | 来自 AST 枚举清单 |
| `STAGING = "staging"` | — | 来自 AST 枚举清单 |

**请求示例**

```json
(无 body; 参数见路径/Query)
```

**响应示例**

```json
{
  "success": true,
  "data": {},
  "message": "ok"
}
```

**相关符号 (术语表命中)**

- # 术语词典 (v8-P0-B 强制约束: 以下标识符必须保留原文, 禁止翻译为中文)
- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.many


### 7.2. API-002 Get (GET `/api/alert`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<IActionResult> Get(string? orgId, string? projectId)
- **源码位置**: `API/Controllers/UserManagement/AlertController.cs:47`
- **Handler**: `AlertController.Get`
- **HTTP**: `GET`
- **Route**: `/api/alert`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| — | — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷, 结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `UsageTracking = 2` | — | 来自 AST 枚举清单 |
| `GetWeChatTokenFailed = 620003` | — | 来自 AST 枚举清单 |
| `GetWeChatBasicUserInfoFailed = 620004` | — | 来自 AST 枚举清单 |
| `InvalidWeChatMessageType = 620005` | — | 来自 AST 枚举清单 |
| `GetPayCertificateFailed = 620017` | — | 来自 AST 枚举清单 |
| `## WeChatMessageType [Models/Common/Enums/WeChatEnum.cs:6]` | — | 来自 AST 枚举清单 |

**请求示例**

```json
(无 body; 参数见路径/Query)
```

**响应示例**

```json
{
  "success": true,
  "data": {},
  "message": "ok"
}
```

**相关符号 (术语表命中)**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, uuid_utils-0.16.2-cp312-cp


### 7.3. API-003 Create (POST `/api/alert`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<IActionResult> Create([FromBody] CreateAlertBody body)
- **源码位置**: `API/Controllers/UserManagement/AlertController.cs:61`
- **Handler**: `AlertController.Create`
- **HTTP**: `POST`
- **Route**: `/api/alert`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| body | body | 视接口 | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷, 结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `Create` | — | 来自 AST 枚举清单 |
| `CreateUserFailed = 100004` | — | 来自 AST 枚举清单 |
| `CreateInviteFailed = 100026` | — | 来自 AST 枚举清单 |
| `CreateApiKeyFailed = 100032` | — | 来自 AST 枚举清单 |
| `CreateOrganizationFailed = 130004` | — | 来自 AST 枚举清单 |
| `CreateProjectFailed = 140004` | — | 来自 AST 枚举清单 |
| `CreateAlertFailed = 160001` | — | 来自 AST 枚举清单 |
| `Create = 2` | — | 来自 AST 枚举清单 |
| `Created = 1` | — | 来自 AST 枚举清单 |
| `Created = 1` | — | 来自 AST 枚举清单 |

**请求示例**

```json
{
  "id": "<id>"
}
```

**响应示例**

```json
{
  "success": true,
  "data": {},
  "message": "ok"
}
```

**相关符号 (术语表命中)**

- # 术语词典 (v8-P0-B 强制约束: 以下标识符必须保留原文, 禁止翻译为中文)
- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.many


### 7.4. API-004 Update (POST `/api/alert/update`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<IActionResult> Update([FromBody] UpdateAlertBody body)
- **源码位置**: `API/Controllers/UserManagement/AlertController.cs:75`
- **Handler**: `AlertController.Update`
- **HTTP**: `POST`
- **Route**: `/api/alert/update`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| body | body | 视接口 | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷, 结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `Update` | — | 来自 AST 枚举清单 |
| `UpdateOrganizationFailed = 130005` | — | 来自 AST 枚举清单 |
| `UpdateProjectFailed = 140005` | — | 来自 AST 枚举清单 |
| `OrderStateUpdateFailed = 810026` | — | 来自 AST 枚举清单 |
| `UpdateAgentRateFailed = 150020` | — | 来自 AST 枚举清单 |
| `UpdateAlertFailed = 160002` | — | 来自 AST 枚举清单 |

**请求示例**

```json
{
  "id": "<id>"
}
```

**响应示例**

```json
{
  "success": true,
  "data": {},
  "message": "ok"
}
```

**相关符号 (术语表命中)**

- # 术语词典 (v8-P0-B 强制约束: 以下标识符必须保留原文, 禁止翻译为中文)
- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.many


### 7.5. API-005 Delete (POST `/api/alert/delete`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<IActionResult> Delete(string alertIds)
- **源码位置**: `API/Controllers/UserManagement/AlertController.cs:90`
- **Handler**: `AlertController.Delete`
- **HTTP**: `POST`
- **Route**: `/api/alert/delete`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| body | body | 视接口 | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷, 结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `Delete` | — | 来自 AST 枚举清单 |
| `DeleteInviteFailed = 100028` | — | 来自 AST 枚举清单 |
| `DeleteApiKeyFailed = 100033` | — | 来自 AST 枚举清单 |
| `DeleteOrganizationFailed = 130006` | — | 来自 AST 枚举清单 |
| `DeleteProjectFailed = 140006` | — | 来自 AST 枚举清单 |
| `DeleteAlertFailed = 160003` | — | 来自 AST 枚举清单 |

**请求示例**

```json
{
  "id": "<id>"
}
```

**响应示例**

```json
{
  "success": true,
  "data": {},
  "message": "ok"
}
```

**相关符号 (术语表命中)**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, uuid_utils-0.16.2-cp312-cp


### 7.6. API-006 ReadRecords (POST `/api/alert/record/read`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<IActionResult> ReadRecords(string recordIds)
- **源码位置**: `API/Controllers/UserManagement/AlertController.cs:108`
- **Handler**: `AlertController.ReadRecords`
- **HTTP**: `POST`
- **Route**: `/api/alert/record/read`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| body | body | 视接口 | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷, 结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `# 枚举定义清单 (AST 结构感知扫描, 错误码必须引用以下真实常量名和数值)` | — | 来自 AST 枚举清单 |
| `# 共 43 个枚举定义` | — | 来自 AST 枚举清单 |
| `## TransactionType [API/Notifications/PaymentTransactionNotification.cs:9]` | — | 来自 AST 枚举清单 |
| `WeChatTransaction` | — | 来自 AST 枚举清单 |
| `AlipayTransaction` | — | 来自 AST 枚举清单 |
| `## RouteType [API/System/Handlers/AgentInsightTransformLogic.cs:72]` | — | 来自 AST 枚举清单 |
| `None = 0` | — | 来自 AST 枚举清单 |
| `Public = 1` | — | 来自 AST 枚举清单 |
| `PublicApi = 2` | — | 来自 AST 枚举清单 |
| `## Environment [Agents/common/config.py:15]` | — | 来自 AST 枚举清单 |
| `DEVELOPMENT = "development"` | — | 来自 AST 枚举清单 |
| `STAGING = "staging"` | — | 来自 AST 枚举清单 |

**请求示例**

```json
{
  "id": "<id>"
}
```

**响应示例**

```json
{
  "success": true,
  "data": {},
  "message": "ok"
}
```

**相关符号 (术语表命中)**

- # 术语词典 (v8-P0-B 强制约束: 以下标识符必须保留原文, 禁止翻译为中文)
- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.many


### 7.7. API-007 GetRecords (GET `/api/alert/record`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<IActionResult> GetRecords(string? orgId, string? projectId, string? alertId, AlertRecordState? state = AlertRecordState.Active)
- **源码位置**: `API/Controllers/UserManagement/AlertController.cs:128`
- **Handler**: `AlertController.GetRecords`
- **HTTP**: `GET`
- **Route**: `/api/alert/record`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| — | — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷, 结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `# 枚举定义清单 (AST 结构感知扫描, 错误码必须引用以下真实常量名和数值)` | — | 来自 AST 枚举清单 |
| `# 共 43 个枚举定义` | — | 来自 AST 枚举清单 |
| `## TransactionType [API/Notifications/PaymentTransactionNotification.cs:9]` | — | 来自 AST 枚举清单 |
| `WeChatTransaction` | — | 来自 AST 枚举清单 |
| `AlipayTransaction` | — | 来自 AST 枚举清单 |
| `## RouteType [API/System/Handlers/AgentInsightTransformLogic.cs:72]` | — | 来自 AST 枚举清单 |
| `None = 0` | — | 来自 AST 枚举清单 |
| `Public = 1` | — | 来自 AST 枚举清单 |
| `PublicApi = 2` | — | 来自 AST 枚举清单 |
| `## Environment [Agents/common/config.py:15]` | — | 来自 AST 枚举清单 |
| `DEVELOPMENT = "development"` | — | 来自 AST 枚举清单 |
| `STAGING = "staging"` | — | 来自 AST 枚举清单 |

**请求示例**

```json
(无 body; 参数见路径/Query)
```

**响应示例**

```json
{
  "success": true,
  "data": {},
  "message": "ok"
}
```

**相关符号 (术语表命中)**

- # 术语词典 (v8-P0-B 强制约束: 以下标识符必须保留原文, 禁止翻译为中文)
- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.many


---

## 8. BulletinController 接口


本章共覆盖 7 个 HTTP 端点 (AST 确定性卡片, 未经 LLM 改写).


### 8.1. API-001 Post (POST `/api/tools/bulletin`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<IActionResult> Post([FromBody] CreateBulletinBody body)
- **源码位置**: `API/Controllers/ToolsManagement/BulletinController.cs:32`
- **Handler**: `BulletinController.Post`
- **HTTP**: `POST`
- **Route**: `/api/tools/bulletin`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| body | body | 视接口 | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷, 结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `# 枚举定义清单 (AST 结构感知扫描, 错误码必须引用以下真实常量名和数值)` | — | 来自 AST 枚举清单 |
| `# 共 43 个枚举定义` | — | 来自 AST 枚举清单 |
| `## TransactionType [API/Notifications/PaymentTransactionNotification.cs:9]` | — | 来自 AST 枚举清单 |
| `WeChatTransaction` | — | 来自 AST 枚举清单 |
| `AlipayTransaction` | — | 来自 AST 枚举清单 |
| `## RouteType [API/System/Handlers/AgentInsightTransformLogic.cs:72]` | — | 来自 AST 枚举清单 |
| `None = 0` | — | 来自 AST 枚举清单 |
| `Public = 1` | — | 来自 AST 枚举清单 |
| `PublicApi = 2` | — | 来自 AST 枚举清单 |
| `## Environment [Agents/common/config.py:15]` | — | 来自 AST 枚举清单 |
| `DEVELOPMENT = "development"` | — | 来自 AST 枚举清单 |
| `STAGING = "staging"` | — | 来自 AST 枚举清单 |

**请求示例**

```json
{
  "id": "<id>"
}
```

**响应示例**

```json
{
  "success": true,
  "data": {},
  "message": "ok"
}
```

**相关符号 (术语表命中)**

- # 术语词典 (v8-P0-B 强制约束: 以下标识符必须保留原文, 禁止翻译为中文)
- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.many


### 8.2. API-002 Get (GET `/api/tools/bulletin/agreement`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<IActionResult> Get(string alias)
- **源码位置**: `API/Controllers/ToolsManagement/BulletinController.cs:45`
- **Handler**: `BulletinController.Get`
- **HTTP**: `GET`
- **Route**: `/api/tools/bulletin/agreement`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| — | — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷, 结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `UsageTracking = 2` | — | 来自 AST 枚举清单 |
| `GetWeChatTokenFailed = 620003` | — | 来自 AST 枚举清单 |
| `GetWeChatBasicUserInfoFailed = 620004` | — | 来自 AST 枚举清单 |
| `InvalidWeChatMessageType = 620005` | — | 来自 AST 枚举清单 |
| `GetPayCertificateFailed = 620017` | — | 来自 AST 枚举清单 |
| `## WeChatMessageType [Models/Common/Enums/WeChatEnum.cs:6]` | — | 来自 AST 枚举清单 |

**请求示例**

```json
(无 body; 参数见路径/Query)
```

**响应示例**

```json
{
  "success": true,
  "data": {},
  "message": "ok"
}
```

**相关符号 (术语表命中)**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, uuid_utils-0.16.2-cp312-cp


### 8.3. API-003 GetBulletins (GET `/api/tools/bulletin/bulletins`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<IActionResult> GetBulletins(BulletinType? type, bool isCarousel = false, int page = AgentInsightConst.DefaultPage, int pageSize = AgentInsightConst.DefaultPageSize)
- **源码位置**: `API/Controllers/ToolsManagement/BulletinController.cs:64`
- **Handler**: `BulletinController.GetBulletins`
- **HTTP**: `GET`
- **Route**: `/api/tools/bulletin/bulletins`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| — | — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷, 结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `# 枚举定义清单 (AST 结构感知扫描, 错误码必须引用以下真实常量名和数值)` | — | 来自 AST 枚举清单 |
| `# 共 43 个枚举定义` | — | 来自 AST 枚举清单 |
| `## TransactionType [API/Notifications/PaymentTransactionNotification.cs:9]` | — | 来自 AST 枚举清单 |
| `WeChatTransaction` | — | 来自 AST 枚举清单 |
| `AlipayTransaction` | — | 来自 AST 枚举清单 |
| `## RouteType [API/System/Handlers/AgentInsightTransformLogic.cs:72]` | — | 来自 AST 枚举清单 |
| `None = 0` | — | 来自 AST 枚举清单 |
| `Public = 1` | — | 来自 AST 枚举清单 |
| `PublicApi = 2` | — | 来自 AST 枚举清单 |
| `## Environment [Agents/common/config.py:15]` | — | 来自 AST 枚举清单 |
| `DEVELOPMENT = "development"` | — | 来自 AST 枚举清单 |
| `STAGING = "staging"` | — | 来自 AST 枚举清单 |

**请求示例**

```json
(无 body; 参数见路径/Query)
```

**响应示例**

```json
{
  "success": true,
  "data": {},
  "message": "ok"
}
```

**相关符号 (术语表命中)**

- # 术语词典 (v8-P0-B 强制约束: 以下标识符必须保留原文, 禁止翻译为中文)
- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.many


### 8.4. API-004 GetBackendBulletins (GET `/api/tools/bulletin/backend`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<IActionResult> GetBackendBulletins(BulletinType? type, BulletinStatus? status, int page = AgentInsightConst.DefaultPage, int pageSize = AgentInsightConst.DefaultPageSize)
- **源码位置**: `API/Controllers/ToolsManagement/BulletinController.cs:82`
- **Handler**: `BulletinController.GetBackendBulletins`
- **HTTP**: `GET`
- **Route**: `/api/tools/bulletin/backend`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| — | — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷, 结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `# 枚举定义清单 (AST 结构感知扫描, 错误码必须引用以下真实常量名和数值)` | — | 来自 AST 枚举清单 |
| `# 共 43 个枚举定义` | — | 来自 AST 枚举清单 |
| `## TransactionType [API/Notifications/PaymentTransactionNotification.cs:9]` | — | 来自 AST 枚举清单 |
| `WeChatTransaction` | — | 来自 AST 枚举清单 |
| `AlipayTransaction` | — | 来自 AST 枚举清单 |
| `## RouteType [API/System/Handlers/AgentInsightTransformLogic.cs:72]` | — | 来自 AST 枚举清单 |
| `None = 0` | — | 来自 AST 枚举清单 |
| `Public = 1` | — | 来自 AST 枚举清单 |
| `PublicApi = 2` | — | 来自 AST 枚举清单 |
| `## Environment [Agents/common/config.py:15]` | — | 来自 AST 枚举清单 |
| `DEVELOPMENT = "development"` | — | 来自 AST 枚举清单 |
| `STAGING = "staging"` | — | 来自 AST 枚举清单 |

**请求示例**

```json
(无 body; 参数见路径/Query)
```

**响应示例**

```json
{
  "success": true,
  "data": {},
  "message": "ok"
}
```

**相关符号 (术语表命中)**

- # 术语词典 (v8-P0-B 强制约束: 以下标识符必须保留原文, 禁止翻译为中文)
- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.many


### 8.5. API-005 ApproveBulletin (POST `/api/tools/bulletin/approve`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<IActionResult> ApproveBulletin(string ids)
- **源码位置**: `API/Controllers/ToolsManagement/BulletinController.cs:96`
- **Handler**: `BulletinController.ApproveBulletin`
- **HTTP**: `POST`
- **Route**: `/api/tools/bulletin/approve`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| body | body | 视接口 | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷, 结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `# 枚举定义清单 (AST 结构感知扫描, 错误码必须引用以下真实常量名和数值)` | — | 来自 AST 枚举清单 |
| `# 共 43 个枚举定义` | — | 来自 AST 枚举清单 |
| `## TransactionType [API/Notifications/PaymentTransactionNotification.cs:9]` | — | 来自 AST 枚举清单 |
| `WeChatTransaction` | — | 来自 AST 枚举清单 |
| `AlipayTransaction` | — | 来自 AST 枚举清单 |
| `## RouteType [API/System/Handlers/AgentInsightTransformLogic.cs:72]` | — | 来自 AST 枚举清单 |
| `None = 0` | — | 来自 AST 枚举清单 |
| `Public = 1` | — | 来自 AST 枚举清单 |
| `PublicApi = 2` | — | 来自 AST 枚举清单 |
| `## Environment [Agents/common/config.py:15]` | — | 来自 AST 枚举清单 |
| `DEVELOPMENT = "development"` | — | 来自 AST 枚举清单 |
| `STAGING = "staging"` | — | 来自 AST 枚举清单 |

**请求示例**

```json
{
  "id": "<id>"
}
```

**响应示例**

```json
{
  "success": true,
  "data": {},
  "message": "ok"
}
```

**相关符号 (术语表命中)**

- # 术语词典 (v8-P0-B 强制约束: 以下标识符必须保留原文, 禁止翻译为中文)
- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.many


### 8.6. API-006 ReviseBulletin (POST `/api/tools/bulletin/revision`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<IActionResult> ReviseBulletin(string ids)
- **源码位置**: `API/Controllers/ToolsManagement/BulletinController.cs:110`
- **Handler**: `BulletinController.ReviseBulletin`
- **HTTP**: `POST`
- **Route**: `/api/tools/bulletin/revision`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| body | body | 视接口 | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷, 结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `# 枚举定义清单 (AST 结构感知扫描, 错误码必须引用以下真实常量名和数值)` | — | 来自 AST 枚举清单 |
| `# 共 43 个枚举定义` | — | 来自 AST 枚举清单 |
| `## TransactionType [API/Notifications/PaymentTransactionNotification.cs:9]` | — | 来自 AST 枚举清单 |
| `WeChatTransaction` | — | 来自 AST 枚举清单 |
| `AlipayTransaction` | — | 来自 AST 枚举清单 |
| `## RouteType [API/System/Handlers/AgentInsightTransformLogic.cs:72]` | — | 来自 AST 枚举清单 |
| `None = 0` | — | 来自 AST 枚举清单 |
| `Public = 1` | — | 来自 AST 枚举清单 |
| `PublicApi = 2` | — | 来自 AST 枚举清单 |
| `## Environment [Agents/common/config.py:15]` | — | 来自 AST 枚举清单 |
| `DEVELOPMENT = "development"` | — | 来自 AST 枚举清单 |
| `STAGING = "staging"` | — | 来自 AST 枚举清单 |

**请求示例**

```json
{
  "id": "<id>"
}
```

**响应示例**

```json
{
  "success": true,
  "data": {},
  "message": "ok"
}
```

**相关符号 (术语表命中)**

- # 术语词典 (v8-P0-B 强制约束: 以下标识符必须保留原文, 禁止翻译为中文)
- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.many


### 8.7. API-007 CloseBulletin (POST `/api/tools/bulletin/close`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<IActionResult> CloseBulletin(string ids)
- **源码位置**: `API/Controllers/ToolsManagement/BulletinController.cs:124`
- **Handler**: `BulletinController.CloseBulletin`
- **HTTP**: `POST`
- **Route**: `/api/tools/bulletin/close`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| body | body | 视接口 | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷, 结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `# 枚举定义清单 (AST 结构感知扫描, 错误码必须引用以下真实常量名和数值)` | — | 来自 AST 枚举清单 |
| `# 共 43 个枚举定义` | — | 来自 AST 枚举清单 |
| `## TransactionType [API/Notifications/PaymentTransactionNotification.cs:9]` | — | 来自 AST 枚举清单 |
| `WeChatTransaction` | — | 来自 AST 枚举清单 |
| `AlipayTransaction` | — | 来自 AST 枚举清单 |
| `## RouteType [API/System/Handlers/AgentInsightTransformLogic.cs:72]` | — | 来自 AST 枚举清单 |
| `None = 0` | — | 来自 AST 枚举清单 |
| `Public = 1` | — | 来自 AST 枚举清单 |
| `PublicApi = 2` | — | 来自 AST 枚举清单 |
| `## Environment [Agents/common/config.py:15]` | — | 来自 AST 枚举清单 |
| `DEVELOPMENT = "development"` | — | 来自 AST 枚举清单 |
| `STAGING = "staging"` | — | 来自 AST 枚举清单 |

**请求示例**

```json
{
  "id": "<id>"
}
```

**响应示例**

```json
{
  "success": true,
  "data": {},
  "message": "ok"
}
```

**相关符号 (术语表命中)**

- # 术语词典 (v8-P0-B 强制约束: 以下标识符必须保留原文, 禁止翻译为中文)
- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.many


---

## 9. CaptchaController 接口


本章共覆盖 2 个 HTTP 端点 (AST 确定性卡片, 未经 LLM 改写).


### 9.1. API-001 Get (GET `/api/captcha`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public IActionResult Get(string mobile)
- **源码位置**: `API/Controllers/UserManagement/CaptchaController.cs:29`
- **Handler**: `CaptchaController.Get`
- **HTTP**: `GET`
- **Route**: `/api/captcha`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| — | — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷, 结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `UsageTracking = 2` | — | 来自 AST 枚举清单 |
| `GetWeChatTokenFailed = 620003` | — | 来自 AST 枚举清单 |
| `GetWeChatBasicUserInfoFailed = 620004` | — | 来自 AST 枚举清单 |
| `InvalidWeChatMessageType = 620005` | — | 来自 AST 枚举清单 |
| `GetPayCertificateFailed = 620017` | — | 来自 AST 枚举清单 |
| `## WeChatMessageType [Models/Common/Enums/WeChatEnum.cs:6]` | — | 来自 AST 枚举清单 |

**请求示例**

```json
(无 body; 参数见路径/Query)
```

**响应示例**

```json
{
  "success": true,
  "data": {},
  "message": "ok"
}
```

**相关符号 (术语表命中)**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, uuid_utils-0.16.2-cp312-cp


### 9.2. API-002 GetSMSCaptcha (GET `/api/captcha/sms`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<IActionResult> GetSMSCaptcha(string phone)
- **源码位置**: `API/Controllers/UserManagement/CaptchaController.cs:43`
- **Handler**: `CaptchaController.GetSMSCaptcha`
- **HTTP**: `GET`
- **Route**: `/api/captcha/sms`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| — | — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷, 结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `# 枚举定义清单 (AST 结构感知扫描, 错误码必须引用以下真实常量名和数值)` | — | 来自 AST 枚举清单 |
| `# 共 43 个枚举定义` | — | 来自 AST 枚举清单 |
| `## TransactionType [API/Notifications/PaymentTransactionNotification.cs:9]` | — | 来自 AST 枚举清单 |
| `WeChatTransaction` | — | 来自 AST 枚举清单 |
| `AlipayTransaction` | — | 来自 AST 枚举清单 |
| `## RouteType [API/System/Handlers/AgentInsightTransformLogic.cs:72]` | — | 来自 AST 枚举清单 |
| `None = 0` | — | 来自 AST 枚举清单 |
| `Public = 1` | — | 来自 AST 枚举清单 |
| `PublicApi = 2` | — | 来自 AST 枚举清单 |
| `## Environment [Agents/common/config.py:15]` | — | 来自 AST 枚举清单 |
| `DEVELOPMENT = "development"` | — | 来自 AST 枚举清单 |
| `STAGING = "staging"` | — | 来自 AST 枚举清单 |

**请求示例**

```json
(无 body; 参数见路径/Query)
```

**响应示例**

```json
{
  "success": true,
  "data": {},
  "message": "ok"
}
```

**相关符号 (术语表命中)**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, uuid_utils-0.16.2-cp312-cp


---

## 10. HealthController 接口


本章共覆盖 1 个 HTTP 端点 (AST 确定性卡片, 未经 LLM 改写).


### 10.1. API-001 Get (GET `/api/tools/health`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public IActionResult Get()
- **源码位置**: `API/Controllers/ToolsManagement/HealthController.cs:20`
- **Handler**: `HealthController.Get`
- **HTTP**: `GET`
- **Route**: `/api/tools/health`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| — | — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷, 结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `UsageTracking = 2` | — | 来自 AST 枚举清单 |
| `GetWeChatTokenFailed = 620003` | — | 来自 AST 枚举清单 |
| `GetWeChatBasicUserInfoFailed = 620004` | — | 来自 AST 枚举清单 |
| `InvalidWeChatMessageType = 620005` | — | 来自 AST 枚举清单 |
| `GetPayCertificateFailed = 620017` | — | 来自 AST 枚举清单 |
| `## WeChatMessageType [Models/Common/Enums/WeChatEnum.cs:6]` | — | 来自 AST 枚举清单 |

**请求示例**

```json
(无 body; 参数见路径/Query)
```

**响应示例**

```json
{
  "success": true,
  "data": {},
  "message": "ok"
}
```

**相关符号 (术语表命中)**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, uuid_utils-0.16.2-cp312-cp


---

## 11. LiteralRoute 接口


本章共覆盖 2 个 HTTP 端点 (AST 确定性卡片, 未经 LLM 改写).


### 11.1. API-001 literal_route (ANY `/api/public`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: 源码字面量路由
- **源码位置**: `-`
- **Handler**: `LiteralRoute.literal_route`
- **HTTP**: `ANY`
- **Route**: `/api/public`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| — | — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷, 结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `# 枚举定义清单 (AST 结构感知扫描, 错误码必须引用以下真实常量名和数值)` | — | 来自 AST 枚举清单 |
| `# 共 43 个枚举定义` | — | 来自 AST 枚举清单 |
| `## TransactionType [API/Notifications/PaymentTransactionNotification.cs:9]` | — | 来自 AST 枚举清单 |
| `WeChatTransaction` | — | 来自 AST 枚举清单 |
| `AlipayTransaction` | — | 来自 AST 枚举清单 |
| `## RouteType [API/System/Handlers/AgentInsightTransformLogic.cs:72]` | — | 来自 AST 枚举清单 |
| `None = 0` | — | 来自 AST 枚举清单 |
| `Public = 1` | — | 来自 AST 枚举清单 |
| `PublicApi = 2` | — | 来自 AST 枚举清单 |
| `## Environment [Agents/common/config.py:15]` | — | 来自 AST 枚举清单 |
| `DEVELOPMENT = "development"` | — | 来自 AST 枚举清单 |
| `STAGING = "staging"` | — | 来自 AST 枚举清单 |

**请求示例**

```json
{
  "id": "<id>"
}
```

**响应示例**

```json
{
  "success": true,
  "data": {},
  "message": "ok"
}
```

**相关符号 (术语表命中)**

- # 术语词典 (v8-P0-B 强制约束: 以下标识符必须保留原文, 禁止翻译为中文)
- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.many


### 11.2. API-002 literal_route (ANY `/api/test`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: 源码字面量路由
- **源码位置**: `-`
- **Handler**: `LiteralRoute.literal_route`
- **HTTP**: `ANY`
- **Route**: `/api/test`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| — | — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷, 结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `# 枚举定义清单 (AST 结构感知扫描, 错误码必须引用以下真实常量名和数值)` | — | 来自 AST 枚举清单 |
| `# 共 43 个枚举定义` | — | 来自 AST 枚举清单 |
| `## TransactionType [API/Notifications/PaymentTransactionNotification.cs:9]` | — | 来自 AST 枚举清单 |
| `WeChatTransaction` | — | 来自 AST 枚举清单 |
| `AlipayTransaction` | — | 来自 AST 枚举清单 |
| `## RouteType [API/System/Handlers/AgentInsightTransformLogic.cs:72]` | — | 来自 AST 枚举清单 |
| `None = 0` | — | 来自 AST 枚举清单 |
| `Public = 1` | — | 来自 AST 枚举清单 |
| `PublicApi = 2` | — | 来自 AST 枚举清单 |
| `## Environment [Agents/common/config.py:15]` | — | 来自 AST 枚举清单 |
| `DEVELOPMENT = "development"` | — | 来自 AST 枚举清单 |
| `STAGING = "staging"` | — | 来自 AST 枚举清单 |

**请求示例**

```json
{
  "id": "<id>"
}
```

**响应示例**

```json
{
  "success": true,
  "data": {},
  "message": "ok"
}
```

**相关符号 (术语表命中)**

- # 术语词典 (v8-P0-B 强制约束: 以下标识符必须保留原文, 禁止翻译为中文)
- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.many


---

## 12. MetricsController 接口


本章共覆盖 4 个 HTTP 端点 (AST 确定性卡片, 未经 LLM 改写).


### 12.1. API-001 GetObservations (GET `/api/data/metrics/observations`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<IActionResult> GetObservations(string id, int page = AgentInsightConst.DefaultPage, int pagesize = AgentInsightConst.DefaultPageSize)
- **源码位置**: `API/Controllers/DataManagement/MetricsController.cs:34`
- **Handler**: `MetricsController.GetObservations`
- **HTTP**: `GET`
- **Route**: `/api/data/metrics/observations`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| — | — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷, 结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `# 枚举定义清单 (AST 结构感知扫描, 错误码必须引用以下真实常量名和数值)` | — | 来自 AST 枚举清单 |
| `# 共 43 个枚举定义` | — | 来自 AST 枚举清单 |
| `## TransactionType [API/Notifications/PaymentTransactionNotification.cs:9]` | — | 来自 AST 枚举清单 |
| `WeChatTransaction` | — | 来自 AST 枚举清单 |
| `AlipayTransaction` | — | 来自 AST 枚举清单 |
| `## RouteType [API/System/Handlers/AgentInsightTransformLogic.cs:72]` | — | 来自 AST 枚举清单 |
| `None = 0` | — | 来自 AST 枚举清单 |
| `Public = 1` | — | 来自 AST 枚举清单 |
| `PublicApi = 2` | — | 来自 AST 枚举清单 |
| `## Environment [Agents/common/config.py:15]` | — | 来自 AST 枚举清单 |
| `DEVELOPMENT = "development"` | — | 来自 AST 枚举清单 |
| `STAGING = "staging"` | — | 来自 AST 枚举清单 |

**请求示例**

```json
(无 body; 参数见路径/Query)
```

**响应示例**

```json
{
  "success": true,
  "data": {},
  "message": "ok"
}
```

**相关符号 (术语表命中)**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, uuid_utils-0.16.2-cp312-cp


### 12.2. API-002 GetScores (GET `/api/data/metrics/scores`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<IActionResult> GetScores(string id, int page = AgentInsightConst.DefaultPage, int pagesize = AgentInsightConst.DefaultPageSize)
- **源码位置**: `API/Controllers/DataManagement/MetricsController.cs:50`
- **Handler**: `MetricsController.GetScores`
- **HTTP**: `GET`
- **Route**: `/api/data/metrics/scores`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| — | — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷, 结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `# 枚举定义清单 (AST 结构感知扫描, 错误码必须引用以下真实常量名和数值)` | — | 来自 AST 枚举清单 |
| `# 共 43 个枚举定义` | — | 来自 AST 枚举清单 |
| `## TransactionType [API/Notifications/PaymentTransactionNotification.cs:9]` | — | 来自 AST 枚举清单 |
| `WeChatTransaction` | — | 来自 AST 枚举清单 |
| `AlipayTransaction` | — | 来自 AST 枚举清单 |
| `## RouteType [API/System/Handlers/AgentInsightTransformLogic.cs:72]` | — | 来自 AST 枚举清单 |
| `None = 0` | — | 来自 AST 枚举清单 |
| `Public = 1` | — | 来自 AST 枚举清单 |
| `PublicApi = 2` | — | 来自 AST 枚举清单 |
| `## Environment [Agents/common/config.py:15]` | — | 来自 AST 枚举清单 |
| `DEVELOPMENT = "development"` | — | 来自 AST 枚举清单 |
| `STAGING = "staging"` | — | 来自 AST 枚举清单 |

**请求示例**

```json
(无 body; 参数见路径/Query)
```

**响应示例**

```json
{
  "success": true,
  "data": {},
  "message": "ok"
}
```

**相关符号 (术语表命中)**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, uuid_utils-0.16.2-cp312-cp


### 12.3. API-003 GetTraces (GET `/api/data/metrics/traces`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<IActionResult> GetTraces(string ids)
- **源码位置**: `API/Controllers/DataManagement/MetricsController.cs:64`
- **Handler**: `MetricsController.GetTraces`
- **HTTP**: `GET`
- **Route**: `/api/data/metrics/traces`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| — | — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷, 结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `# 枚举定义清单 (AST 结构感知扫描, 错误码必须引用以下真实常量名和数值)` | — | 来自 AST 枚举清单 |
| `# 共 43 个枚举定义` | — | 来自 AST 枚举清单 |
| `## TransactionType [API/Notifications/PaymentTransactionNotification.cs:9]` | — | 来自 AST 枚举清单 |
| `WeChatTransaction` | — | 来自 AST 枚举清单 |
| `AlipayTransaction` | — | 来自 AST 枚举清单 |
| `## RouteType [API/System/Handlers/AgentInsightTransformLogic.cs:72]` | — | 来自 AST 枚举清单 |
| `None = 0` | — | 来自 AST 枚举清单 |
| `Public = 1` | — | 来自 AST 枚举清单 |
| `PublicApi = 2` | — | 来自 AST 枚举清单 |
| `## Environment [Agents/common/config.py:15]` | — | 来自 AST 枚举清单 |
| `DEVELOPMENT = "development"` | — | 来自 AST 枚举清单 |
| `STAGING = "staging"` | — | 来自 AST 枚举清单 |

**请求示例**

```json
(无 body; 参数见路径/Query)
```

**响应示例**

```json
{
  "success": true,
  "data": {},
  "message": "ok"
}
```

**相关符号 (术语表命中)**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, uuid_utils-0.16.2-cp312-cp


### 12.4. API-004 GetTraces (POST `/api/data/metrics/traces`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<IActionResult> GetTraces([FromBody] TraceMetricsBody body)
- **源码位置**: `API/Controllers/DataManagement/MetricsController.cs:125`
- **Handler**: `MetricsController.GetTraces`
- **HTTP**: `POST`
- **Route**: `/api/data/metrics/traces`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| body | body | 视接口 | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷, 结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `# 枚举定义清单 (AST 结构感知扫描, 错误码必须引用以下真实常量名和数值)` | — | 来自 AST 枚举清单 |
| `# 共 43 个枚举定义` | — | 来自 AST 枚举清单 |
| `## TransactionType [API/Notifications/PaymentTransactionNotification.cs:9]` | — | 来自 AST 枚举清单 |
| `WeChatTransaction` | — | 来自 AST 枚举清单 |
| `AlipayTransaction` | — | 来自 AST 枚举清单 |
| `## RouteType [API/System/Handlers/AgentInsightTransformLogic.cs:72]` | — | 来自 AST 枚举清单 |
| `None = 0` | — | 来自 AST 枚举清单 |
| `Public = 1` | — | 来自 AST 枚举清单 |
| `PublicApi = 2` | — | 来自 AST 枚举清单 |
| `## Environment [Agents/common/config.py:15]` | — | 来自 AST 枚举清单 |
| `DEVELOPMENT = "development"` | — | 来自 AST 枚举清单 |
| `STAGING = "staging"` | — | 来自 AST 枚举清单 |

**请求示例**

```json
{
  "id": "<id>"
}
```

**响应示例**

```json
{
  "success": true,
  "data": {},
  "message": "ok"
}
```

**相关符号 (术语表命中)**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, uuid_utils-0.16.2-cp312-cp


---

## 13. ModelController 接口


本章共覆盖 1 个 HTTP 端点 (AST 确定性卡片, 未经 LLM 改写).


### 13.1. API-001 Get (GET `/api/data/model`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<IActionResult> Get(string? keyword, string? projectid, bool includedpredefined = false, string orderby = "-updatedat", int page = AgentInsightConst.DefaultPage, int pageSize = AgentInsightConst.DefaultPageSize)
- **源码位置**: `API/Controllers/DataManagement/ModelController.cs:34`
- **Handler**: `ModelController.Get`
- **HTTP**: `GET`
- **Route**: `/api/data/model`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| — | — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷, 结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `UsageTracking = 2` | — | 来自 AST 枚举清单 |
| `GetWeChatTokenFailed = 620003` | — | 来自 AST 枚举清单 |
| `GetWeChatBasicUserInfoFailed = 620004` | — | 来自 AST 枚举清单 |
| `InvalidWeChatMessageType = 620005` | — | 来自 AST 枚举清单 |
| `GetPayCertificateFailed = 620017` | — | 来自 AST 枚举清单 |
| `## WeChatMessageType [Models/Common/Enums/WeChatEnum.cs:6]` | — | 来自 AST 枚举清单 |

**请求示例**

```json
(无 body; 参数见路径/Query)
```

**响应示例**

```json
{
  "success": true,
  "data": {},
  "message": "ok"
}
```

**相关符号 (术语表命中)**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, uuid_utils-0.16.2-cp312-cp


---

## 14. NotifyController 接口


本章共覆盖 2 个 HTTP 端点 (AST 确定性卡片, 未经 LLM 改写).


### 14.1. API-001 WeChatNotify (POST `/api/payment/notify/wechatnotify`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<IActionResult> WeChatNotify()
- **源码位置**: `API/Controllers/PaymentManagement/NotifyController.cs:29`
- **Handler**: `NotifyController.WeChatNotify`
- **HTTP**: `POST`
- **Route**: `/api/payment/notify/wechatnotify`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| body | body | 视接口 | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷, 结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `InvalidWeChatNotify = 810010` | — | 来自 AST 枚举清单 |
| `EmptyWeChatNotify = 810018` | — | 来自 AST 枚举清单 |

**请求示例**

```json
{
  "id": "<id>"
}
```

**响应示例**

```json
{
  "success": true,
  "data": {},
  "message": "ok"
}
```

**相关符号 (术语表命中)**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, uuid_utils-0.16.2-cp312-cp


### 14.2. API-002 AlipayNotify (POST `/api/payment/notify/alipaynotify`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<IActionResult> AlipayNotify()
- **源码位置**: `API/Controllers/PaymentManagement/NotifyController.cs:57`
- **Handler**: `NotifyController.AlipayNotify`
- **HTTP**: `POST`
- **Route**: `/api/payment/notify/alipaynotify`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| body | body | 视接口 | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷, 结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `# 枚举定义清单 (AST 结构感知扫描, 错误码必须引用以下真实常量名和数值)` | — | 来自 AST 枚举清单 |
| `# 共 43 个枚举定义` | — | 来自 AST 枚举清单 |
| `## TransactionType [API/Notifications/PaymentTransactionNotification.cs:9]` | — | 来自 AST 枚举清单 |
| `WeChatTransaction` | — | 来自 AST 枚举清单 |
| `AlipayTransaction` | — | 来自 AST 枚举清单 |
| `## RouteType [API/System/Handlers/AgentInsightTransformLogic.cs:72]` | — | 来自 AST 枚举清单 |
| `None = 0` | — | 来自 AST 枚举清单 |
| `Public = 1` | — | 来自 AST 枚举清单 |
| `PublicApi = 2` | — | 来自 AST 枚举清单 |
| `## Environment [Agents/common/config.py:15]` | — | 来自 AST 枚举清单 |
| `DEVELOPMENT = "development"` | — | 来自 AST 枚举清单 |
| `STAGING = "staging"` | — | 来自 AST 枚举清单 |

**请求示例**

```json
{
  "id": "<id>"
}
```

**响应示例**

```json
{
  "success": true,
  "data": {},
  "message": "ok"
}
```

**相关符号 (术语表命中)**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, uuid_utils-0.16.2-cp312-cp


---

## 15. OrderController 接口


本章共覆盖 4 个 HTTP 端点 (AST 确定性卡片, 未经 LLM 改写).


### 15.1. API-001 Get (GET `/api/payment/order`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<IActionResult> Get(string orgId, int page = AgentInsightConst.DefaultPage, int pageSize = AgentInsightConst.DefaultPageSize)
- **源码位置**: `API/Controllers/PaymentManagement/OrderController.cs:34`
- **Handler**: `OrderController.Get`
- **HTTP**: `GET`
- **Route**: `/api/payment/order`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| — | — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷, 结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `UsageTracking = 2` | — | 来自 AST 枚举清单 |
| `GetWeChatTokenFailed = 620003` | — | 来自 AST 枚举清单 |
| `GetWeChatBasicUserInfoFailed = 620004` | — | 来自 AST 枚举清单 |
| `InvalidWeChatMessageType = 620005` | — | 来自 AST 枚举清单 |
| `GetPayCertificateFailed = 620017` | — | 来自 AST 枚举清单 |
| `## WeChatMessageType [Models/Common/Enums/WeChatEnum.cs:6]` | — | 来自 AST 枚举清单 |

**请求示例**

```json
(无 body; 参数见路径/Query)
```

**响应示例**

```json
{
  "success": true,
  "data": {},
  "message": "ok"
}
```

**相关符号 (术语表命中)**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, uuid_utils-0.16.2-cp312-cp


### 15.2. API-002 Place (POST `/api/payment/order`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<IActionResult> Place([FromBody] AgentInsightOrderBody body)
- **源码位置**: `API/Controllers/PaymentManagement/OrderController.cs:48`
- **Handler**: `OrderController.Place`
- **HTTP**: `POST`
- **Route**: `/api/payment/order`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| body | body | 视接口 | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷, 结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `Place` | — | 来自 AST 枚举清单 |
| `AlipayPlaceOrderError = 810020` | — | 来自 AST 枚举清单 |

**请求示例**

```json
{
  "id": "<id>"
}
```

**响应示例**

```json
{
  "success": true,
  "data": {},
  "message": "ok"
}
```

**相关符号 (术语表命中)**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, uuid_utils-0.16.2-cp312-cp


### 15.3. API-003 Query (GET `/api/payment/order/query`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<IActionResult> Query(string orderNo)
- **源码位置**: `API/Controllers/PaymentManagement/OrderController.cs:64`
- **Handler**: `OrderController.Query`
- **HTTP**: `GET`
- **Route**: `/api/payment/order/query`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| — | — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷, 结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `Query` | — | 来自 AST 枚举清单 |
| `WeChatQueryErrorResponse = 810024` | — | 来自 AST 枚举清单 |
| `ClickHouseQueryError = 150010` | — | 来自 AST 枚举清单 |
| `ClickHouseQueryTimeout = 150017` | — | 来自 AST 枚举清单 |

**请求示例**

```json
(无 body; 参数见路径/Query)
```

**响应示例**

```json
{
  "success": true,
  "data": {},
  "message": "ok"
}
```

**相关符号 (术语表命中)**

- # 术语词典 (v8-P0-B 强制约束: 以下标识符必须保留原文, 禁止翻译为中文)
- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.many


### 15.4. API-004 GetConversion (GET `/api/payment/order/conversion`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<IActionResult> GetConversion(string newProductId)
- **源码位置**: `API/Controllers/PaymentManagement/OrderController.cs:79`
- **Handler**: `OrderController.GetConversion`
- **HTTP**: `GET`
- **Route**: `/api/payment/order/conversion`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| — | — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷, 结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `# 枚举定义清单 (AST 结构感知扫描, 错误码必须引用以下真实常量名和数值)` | — | 来自 AST 枚举清单 |
| `# 共 43 个枚举定义` | — | 来自 AST 枚举清单 |
| `## TransactionType [API/Notifications/PaymentTransactionNotification.cs:9]` | — | 来自 AST 枚举清单 |
| `WeChatTransaction` | — | 来自 AST 枚举清单 |
| `AlipayTransaction` | — | 来自 AST 枚举清单 |
| `## RouteType [API/System/Handlers/AgentInsightTransformLogic.cs:72]` | — | 来自 AST 枚举清单 |
| `None = 0` | — | 来自 AST 枚举清单 |
| `Public = 1` | — | 来自 AST 枚举清单 |
| `PublicApi = 2` | — | 来自 AST 枚举清单 |
| `## Environment [Agents/common/config.py:15]` | — | 来自 AST 枚举清单 |
| `DEVELOPMENT = "development"` | — | 来自 AST 枚举清单 |
| `STAGING = "staging"` | — | 来自 AST 枚举清单 |

**请求示例**

```json
(无 body; 参数见路径/Query)
```

**响应示例**

```json
{
  "success": true,
  "data": {},
  "message": "ok"
}
```

**相关符号 (术语表命中)**

- # 术语词典 (v8-P0-B 强制约束: 以下标识符必须保留原文, 禁止翻译为中文)
- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.many


---

## 16. OrganizationController 接口


本章共覆盖 4 个 HTTP 端点 (AST 确定性卡片, 未经 LLM 改写).


### 16.1. API-001 Post (POST `/api/user/organization`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<IActionResult> Post([FromBody] CreateOrganizationBody body)
- **源码位置**: `API/Controllers/UserManagement/OrganizationController.cs:28`
- **Handler**: `OrganizationController.Post`
- **HTTP**: `POST`
- **Route**: `/api/user/organization`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| body | body | 视接口 | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷, 结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `# 枚举定义清单 (AST 结构感知扫描, 错误码必须引用以下真实常量名和数值)` | — | 来自 AST 枚举清单 |
| `# 共 43 个枚举定义` | — | 来自 AST 枚举清单 |
| `## TransactionType [API/Notifications/PaymentTransactionNotification.cs:9]` | — | 来自 AST 枚举清单 |
| `WeChatTransaction` | — | 来自 AST 枚举清单 |
| `AlipayTransaction` | — | 来自 AST 枚举清单 |
| `## RouteType [API/System/Handlers/AgentInsightTransformLogic.cs:72]` | — | 来自 AST 枚举清单 |
| `None = 0` | — | 来自 AST 枚举清单 |
| `Public = 1` | — | 来自 AST 枚举清单 |
| `PublicApi = 2` | — | 来自 AST 枚举清单 |
| `## Environment [Agents/common/config.py:15]` | — | 来自 AST 枚举清单 |
| `DEVELOPMENT = "development"` | — | 来自 AST 枚举清单 |
| `STAGING = "staging"` | — | 来自 AST 枚举清单 |

**请求示例**

```json
{
  "id": "<id>"
}
```

**响应示例**

```json
{
  "success": true,
  "data": {},
  "message": "ok"
}
```

**相关符号 (术语表命中)**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, uuid_utils-0.16.2-cp312-cp


### 16.2. API-002 Get (GET `/api/user/organization`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<IActionResult> Get(string? orgId)
- **源码位置**: `API/Controllers/UserManagement/OrganizationController.cs:42`
- **Handler**: `OrganizationController.Get`
- **HTTP**: `GET`
- **Route**: `/api/user/organization`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| — | — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷, 结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `UsageTracking = 2` | — | 来自 AST 枚举清单 |
| `GetWeChatTokenFailed = 620003` | — | 来自 AST 枚举清单 |
| `GetWeChatBasicUserInfoFailed = 620004` | — | 来自 AST 枚举清单 |
| `InvalidWeChatMessageType = 620005` | — | 来自 AST 枚举清单 |
| `GetPayCertificateFailed = 620017` | — | 来自 AST 枚举清单 |
| `## WeChatMessageType [Models/Common/Enums/WeChatEnum.cs:6]` | — | 来自 AST 枚举清单 |

**请求示例**

```json
(无 body; 参数见路径/Query)
```

**响应示例**

```json
{
  "success": true,
  "data": {},
  "message": "ok"
}
```

**相关符号 (术语表命中)**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, uuid_utils-0.16.2-cp312-cp


### 16.3. API-003 Update (POST `/api/user/organization/update`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<IActionResult> Update([FromBody] UpdateOrganizationBody body)
- **源码位置**: `API/Controllers/UserManagement/OrganizationController.cs:56`
- **Handler**: `OrganizationController.Update`
- **HTTP**: `POST`
- **Route**: `/api/user/organization/update`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| body | body | 视接口 | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷, 结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `Update` | — | 来自 AST 枚举清单 |
| `UpdateOrganizationFailed = 130005` | — | 来自 AST 枚举清单 |
| `UpdateProjectFailed = 140005` | — | 来自 AST 枚举清单 |
| `OrderStateUpdateFailed = 810026` | — | 来自 AST 枚举清单 |
| `UpdateAgentRateFailed = 150020` | — | 来自 AST 枚举清单 |
| `UpdateAlertFailed = 160002` | — | 来自 AST 枚举清单 |

**请求示例**

```json
{
  "id": "<id>"
}
```

**响应示例**

```json
{
  "success": true,
  "data": {},
  "message": "ok"
}
```

**相关符号 (术语表命中)**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, uuid_utils-0.16.2-cp312-cp


### 16.4. API-004 Delete (POST `/api/user/organization/delete`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<IActionResult> Delete(string orgIds)
- **源码位置**: `API/Controllers/UserManagement/OrganizationController.cs:71`
- **Handler**: `OrganizationController.Delete`
- **HTTP**: `POST`
- **Route**: `/api/user/organization/delete`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| body | body | 视接口 | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷, 结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `Delete` | — | 来自 AST 枚举清单 |
| `DeleteInviteFailed = 100028` | — | 来自 AST 枚举清单 |
| `DeleteApiKeyFailed = 100033` | — | 来自 AST 枚举清单 |
| `DeleteOrganizationFailed = 130006` | — | 来自 AST 枚举清单 |
| `DeleteProjectFailed = 140006` | — | 来自 AST 枚举清单 |
| `DeleteAlertFailed = 160003` | — | 来自 AST 枚举清单 |

**请求示例**

```json
{
  "id": "<id>"
}
```

**响应示例**

```json
{
  "success": true,
  "data": {},
  "message": "ok"
}
```

**相关符号 (术语表命中)**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, uuid_utils-0.16.2-cp312-cp


---

## 17. ProductController 接口


本章共覆盖 2 个 HTTP 端点 (AST 确定性卡片, 未经 LLM 改写).


### 17.1. API-001 Get (GET `/api/product`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<IActionResult> Get()
- **源码位置**: `API/Controllers/ProductManagement/ProductController.cs:26`
- **Handler**: `ProductController.Get`
- **HTTP**: `GET`
- **Route**: `/api/product`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| — | — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷, 结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `UsageTracking = 2` | — | 来自 AST 枚举清单 |
| `GetWeChatTokenFailed = 620003` | — | 来自 AST 枚举清单 |
| `GetWeChatBasicUserInfoFailed = 620004` | — | 来自 AST 枚举清单 |
| `InvalidWeChatMessageType = 620005` | — | 来自 AST 枚举清单 |
| `GetPayCertificateFailed = 620017` | — | 来自 AST 枚举清单 |
| `## WeChatMessageType [Models/Common/Enums/WeChatEnum.cs:6]` | — | 来自 AST 枚举清单 |

**请求示例**

```json
(无 body; 参数见路径/Query)
```

**响应示例**

```json
{
  "success": true,
  "data": {},
  "message": "ok"
}
```

**相关符号 (术语表命中)**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, uuid_utils-0.16.2-cp312-cp


### 17.2. API-002 GetDuration (GET `/api/product/duration`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<IActionResult> GetDuration()
- **源码位置**: `API/Controllers/ProductManagement/ProductController.cs:38`
- **Handler**: `ProductController.GetDuration`
- **HTTP**: `GET`
- **Route**: `/api/product/duration`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| — | — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷, 结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `# 枚举定义清单 (AST 结构感知扫描, 错误码必须引用以下真实常量名和数值)` | — | 来自 AST 枚举清单 |
| `# 共 43 个枚举定义` | — | 来自 AST 枚举清单 |
| `## TransactionType [API/Notifications/PaymentTransactionNotification.cs:9]` | — | 来自 AST 枚举清单 |
| `WeChatTransaction` | — | 来自 AST 枚举清单 |
| `AlipayTransaction` | — | 来自 AST 枚举清单 |
| `## RouteType [API/System/Handlers/AgentInsightTransformLogic.cs:72]` | — | 来自 AST 枚举清单 |
| `None = 0` | — | 来自 AST 枚举清单 |
| `Public = 1` | — | 来自 AST 枚举清单 |
| `PublicApi = 2` | — | 来自 AST 枚举清单 |
| `## Environment [Agents/common/config.py:15]` | — | 来自 AST 枚举清单 |
| `DEVELOPMENT = "development"` | — | 来自 AST 枚举清单 |
| `STAGING = "staging"` | — | 来自 AST 枚举清单 |

**请求示例**

```json
(无 body; 参数见路径/Query)
```

**响应示例**

```json
{
  "success": true,
  "data": {},
  "message": "ok"
}
```

**相关符号 (术语表命中)**

- # 术语词典 (v8-P0-B 强制约束: 以下标识符必须保留原文, 禁止翻译为中文)
- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.many


---

## 18. ProjectController 接口


本章共覆盖 4 个 HTTP 端点 (AST 确定性卡片, 未经 LLM 改写).


### 18.1. API-001 Create (POST `/api/user/project`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<IActionResult> Create([FromBody] CreateProjectBody body)
- **源码位置**: `API/Controllers/UserManagement/ProjectController.cs:31`
- **Handler**: `ProjectController.Create`
- **HTTP**: `POST`
- **Route**: `/api/user/project`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| body | body | 视接口 | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷, 结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `Create` | — | 来自 AST 枚举清单 |
| `CreateUserFailed = 100004` | — | 来自 AST 枚举清单 |
| `CreateInviteFailed = 100026` | — | 来自 AST 枚举清单 |
| `CreateApiKeyFailed = 100032` | — | 来自 AST 枚举清单 |
| `CreateOrganizationFailed = 130004` | — | 来自 AST 枚举清单 |
| `CreateProjectFailed = 140004` | — | 来自 AST 枚举清单 |
| `CreateAlertFailed = 160001` | — | 来自 AST 枚举清单 |
| `Create = 2` | — | 来自 AST 枚举清单 |
| `Created = 1` | — | 来自 AST 枚举清单 |
| `Created = 1` | — | 来自 AST 枚举清单 |

**请求示例**

```json
{
  "id": "<id>"
}
```

**响应示例**

```json
{
  "success": true,
  "data": {},
  "message": "ok"
}
```

**相关符号 (术语表命中)**

- # 术语词典 (v8-P0-B 强制约束: 以下标识符必须保留原文, 禁止翻译为中文)
- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.many


### 18.2. API-002 Get (GET `/api/user/project`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<IActionResult> Get(string orgId, string? projectId)
- **源码位置**: `API/Controllers/UserManagement/ProjectController.cs:46`
- **Handler**: `ProjectController.Get`
- **HTTP**: `GET`
- **Route**: `/api/user/project`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| — | — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷, 结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `UsageTracking = 2` | — | 来自 AST 枚举清单 |
| `GetWeChatTokenFailed = 620003` | — | 来自 AST 枚举清单 |
| `GetWeChatBasicUserInfoFailed = 620004` | — | 来自 AST 枚举清单 |
| `InvalidWeChatMessageType = 620005` | — | 来自 AST 枚举清单 |
| `GetPayCertificateFailed = 620017` | — | 来自 AST 枚举清单 |
| `## WeChatMessageType [Models/Common/Enums/WeChatEnum.cs:6]` | — | 来自 AST 枚举清单 |

**请求示例**

```json
(无 body; 参数见路径/Query)
```

**响应示例**

```json
{
  "success": true,
  "data": {},
  "message": "ok"
}
```

**相关符号 (术语表命中)**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, uuid_utils-0.16.2-cp312-cp


### 18.3. API-003 Update (POST `/api/user/project/update`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<IActionResult> Update([FromBody] UpdateProjectBody body)
- **源码位置**: `API/Controllers/UserManagement/ProjectController.cs:60`
- **Handler**: `ProjectController.Update`
- **HTTP**: `POST`
- **Route**: `/api/user/project/update`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| body | body | 视接口 | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷, 结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `Update` | — | 来自 AST 枚举清单 |
| `UpdateOrganizationFailed = 130005` | — | 来自 AST 枚举清单 |
| `UpdateProjectFailed = 140005` | — | 来自 AST 枚举清单 |
| `OrderStateUpdateFailed = 810026` | — | 来自 AST 枚举清单 |
| `UpdateAgentRateFailed = 150020` | — | 来自 AST 枚举清单 |
| `UpdateAlertFailed = 160002` | — | 来自 AST 枚举清单 |

**请求示例**

```json
{
  "id": "<id>"
}
```

**响应示例**

```json
{
  "success": true,
  "data": {},
  "message": "ok"
}
```

**相关符号 (术语表命中)**

- # 术语词典 (v8-P0-B 强制约束: 以下标识符必须保留原文, 禁止翻译为中文)
- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.many


### 18.4. API-004 Delete (POST `/api/user/project/delete`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<IActionResult> Delete(string projectIds)
- **源码位置**: `API/Controllers/UserManagement/ProjectController.cs:75`
- **Handler**: `ProjectController.Delete`
- **HTTP**: `POST`
- **Route**: `/api/user/project/delete`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| body | body | 视接口 | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷, 结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `Delete` | — | 来自 AST 枚举清单 |
| `DeleteInviteFailed = 100028` | — | 来自 AST 枚举清单 |
| `DeleteApiKeyFailed = 100033` | — | 来自 AST 枚举清单 |
| `DeleteOrganizationFailed = 130006` | — | 来自 AST 枚举清单 |
| `DeleteProjectFailed = 140006` | — | 来自 AST 枚举清单 |
| `DeleteAlertFailed = 160003` | — | 来自 AST 枚举清单 |

**请求示例**

```json
{
  "id": "<id>"
}
```

**响应示例**

```json
{
  "success": true,
  "data": {},
  "message": "ok"
}
```

**相关符号 (术语表命中)**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, uuid_utils-0.16.2-cp312-cp


---

## 19. Unknown 接口

### 19.1. API 接口清单（由 AST/源码直接提取，禁止修改）

| 标识 | 方法 | 路径 | 描述 | 鉴权 |
|------|------|------|------|------|
| API-001 | GET | `/api/user/config` | UserConfigController.Get | Bearer |
| API-002 | POST | `/api/user/config` | UserConfigController.Post | Bearer |
| API-003 | POST | `/api/user/config/update` | UserConfigController.Update | Bearer |
| API-004 | GET | `/api/user/config/delete` | UserConfigController.Delete | Bearer |
| API-005 | GET | `/api/captcha` | CaptchaController.Get | Bearer |
| API-006 | GET | `/api/captcha/sms` | CaptchaController.GetSMSCaptcha | Bearer |
| API-007 | GET | `/api/user` | UserController.Get | Bearer |
| API-008 | POST | `/api/user` | UserController.Create | Bearer |
| API-009 | POST | `/api/user/update` | UserController.Update | Bearer |
| API-010 | POST | `/api/user/login` | UserController.Login | Bearer |
| API-011 | POST | `/api/user/logout` | UserController.Logout | Bearer |
| API-012 | POST | `/api/user/resetpassword` | UserController.ResetPassword | Bearer |

| API-013 | POST | `/api/user/bind/wechat` | UserController.Bind | Bearer |
| API-014 | GET | `/api/user/unbind/wechat` | UserController.UnBind | Bearer |
| API-015 | POST | `/api/user/role` | UserController.AssignRole | Bearer |
| API-016 | POST | `/api/user/invite` | UserController.Invite | Bearer |
| API-017 | GET | `/api/user/invitation` | UserController.Get | Bearer |
| API-018 | POST | `/api/user/invitation/delete` | UserController.DeleteInvitation | Bearer |
| API-019 | POST | `/api/user/apikey` | UserController.CreateApiKey | Bearer |
| API-020 | GET | `/api/user/apikey` | UserController.Get | Bearer |
| API-021 | GET | `/api/user/privilege/agent/deduct` | UserController.DeductMonthlyAgentRate | Bearer |
| API-022 | GET | `/api/user/privilege/agent/validate` | UserController.ValidateMonthlyAgentRate | Bearer |
| API-023 | POST | `/api/user/apikey/delete` | UserController.DeleteApiKey | Bearer |
| API-024 | POST | `/api/user/project` | ProjectController.Create | Bearer |

| API-025 | GET | `/api/user/project` | ProjectController.Get | Bearer |
| API-026 | POST | `/api/user/project/update` | ProjectController.Update | Bearer |
| API-027 | POST | `/api/user/project/delete` | ProjectController.Delete | Bearer |
| API-028 | POST | `/api/user/organization` | OrganizationController.Post | Bearer |
| API-029 | GET | `/api/user/organization` | OrganizationController.Get | Bearer |
| API-030 | POST | `/api/user/organization/update` | OrganizationController.Update | Bearer |
| API-031 | POST | `/api/user/organization/delete` | OrganizationController.Delete | Bearer |
| API-032 | GET | `/api/alert/config` | AlertController.GetConfig | Bearer |
| API-033 | GET | `/api/alert` | AlertController.Get | Bearer |
| API-034 | POST | `/api/alert` | AlertController.Create | Bearer |
| API-035 | POST | `/api/alert/update` | AlertController.Update | Bearer |
| API-036 | POST | `/api/alert/delete` | AlertController.Delete | Bearer |

| API-037 | POST | `/api/alert/record/read` | AlertController.ReadRecords | Bearer |
| API-038 | GET | `/api/alert/record` | AlertController.GetRecords | Bearer |
| API-039 | GET | `/api/agent/session` | AgentSessionController.Get | Bearer |
| API-040 | GET | `/api/agent/session/delete` | AgentSessionController.Delete | Bearer |
| API-041 | POST | `/api/agent/session` | AgentSessionController.Post | Bearer |
| API-042 | GET | `/api/agent/config` | AgentConfigController.Get | Bearer |
| API-043 | GET | `/api/agent/config/delete` | AgentConfigController.Delete | Bearer |
| API-044 | POST | `/api/agent/config` | AgentConfigController.Post | Bearer |
| API-045 | GET | `/api/agent/report` | AgentReportController.GetTemplates | Bearer |
| API-046 | GET | `/api/agent/report/delete` | AgentReportController.DeleteTemplates | Bearer |
| API-047 | POST | `/api/agent/report` | AgentReportController.CreateOrUpdateTemplate | Bearer |

| API-048 | GET | `/api/data/model` | ModelController.Get | Bearer |
| API-049 | GET | `/api/data/metrics/observations` | MetricsController.GetObservations | Bearer |
| API-050 | GET | `/api/data/metrics/scores` | MetricsController.GetScores | Bearer |
| API-051 | GET | `/api/data/metrics/traces` | MetricsController.GetTraces | Bearer |
| API-052 | POST | `/api/data/metrics/traces` | MetricsController.GetTraces | Bearer |
| API-053 | GET | `/api/product` | ProductController.Get | Bearer |
| API-054 | GET | `/api/product/duration` | ProductController.GetDuration | Bearer |
| API-055 | GET | `/api/tools/health` | HealthController.Get | Bearer |
| API-056 | POST | `/api/tools/bulletin` | BulletinController.Post | Bearer |
| API-057 | GET | `/api/tools/bulletin/agreement` | BulletinController.Get | Bearer |
| API-058 | GET | `/api/tools/bulletin/bulletins` | BulletinController.GetBulletins | Bearer |

| API-059 | GET | `/api/tools/bulletin/backend` | BulletinController.GetBackendBulletins | Bearer |
| API-060 | POST | `/api/tools/bulletin/approve` | BulletinController.ApproveBulletin | Bearer |
| API-061 | POST | `/api/tools/bulletin/revision` | BulletinController.ReviseBulletin | Bearer |
| API-062 | POST | `/api/tools/bulletin/close` | BulletinController.CloseBulletin | Bearer |
| API-063 | GET | `/api/payment/order` | OrderController.Get | Bearer |
| API-064 | POST | `/api/payment/order` | OrderController.Place | Bearer |
| API-065 | GET | `/api/payment/order/query` | OrderController.Query | Bearer |
| API-066 | GET | `/api/payment/order/conversion` | OrderController.GetConversion | Bearer |
| API-067 | POST | `/api/payment/notify/wechatnotify` | NotifyController.WeChatNotify | Bearer |
| API-068 | POST | `/api/payment/notify/alipaynotify` | NotifyController.AlipayNotify | Bearer |
| API-069 | GET | `/api/tools/wechat` | WeChatController.Get | Bearer |

| API-070 | POST | `/api/tools/wechat` | WeChatController.Post | Bearer |
| API-071 | POST | `/api/agent/insight` | chat_completions | Bearer |
| API-072 | GET | `/api/sessions` | list_sessions | Bearer |
| API-073 | GET | `/api/sessions/{session_id}` | get_session | Bearer |
| API-074 | DELETE | `/api/sessions/{session_id}` | delete_session | Bearer |
| API-075 | POST | `/api/sessions/cleanup` | cleanup_expired_sessions | Bearer |
| API-076 | GET | `/api/agents` | list_agents | Bearer |

### 19.2. 接口补充说明

> 以下由 LLM 基于上述真实 API 签名补充说明, 禁止修改上方签名表内容.

本章节描述 AgentInsightService 平台中 `Unknown` Controller 暴露的 6 个 RESTful API 端点。AgentInsightService 提供完整的 RESTful API 接口，覆盖用户认证、组织管理、Trace 数据查询、AlertConfig、Payment订单、Agent Config等核心功能，所有接口通过 JWT Token 或 API Key 进行认证，错误码统一在 `Models/Common/Enums/ExceptionCodes.cs` 中定义。本章仅覆盖 `Unknown` 接口下的端点，包括 Agent Insight 对话补全、Session 生命周期管理以及 Agent 列表查询。

### 19.3. POST /api/agent/insight - async def [已移除幻觉符号](

**鉴权**: JWT Token（用户登录后签发，用于平台 API 调用）

**描述**: 该端点用于向 Agent 发送对话补全请求，是 AgentInsightService 的核心推理入口。客户端提交对话消息后，服务端通过内部 Agent 处理链完成推理并返回补全结果。该接口采用异步处理模式，适用于需要流式或非阻塞响应的对话场景。

#### 19.3.1. 请求参数

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| body | object | 是 | 对话补全请求体，包含消息列表、模型参数等Config |

请求体结构示例：

```json
{
  "messages": [
    { "role": "user", "content": "请分析当前项目的 Token 消耗趋势" }
  ],
  "model": "default",
  "stream": false
}
```

#### 19.3.2. 响应格式

| 字段 | 类型 | 说明 |
|------|------|------|
| errorCode | int | 0=成功，非 0=具体错误码 |
| data | object | 对话补全结果，包含生成的消息内容 |

#### 19.3.3. 错误码

| errorCode | message | 说明 |
|-----------|---------|------|
| 0 | success | 成功 |
| 100000 | [已移除幻觉符号] | Token 无效或已过期 |
| 150004 | [已移除幻觉符号] | Agent Config未设置 |
| 150007 | [已移除幻觉符号] | Agent 数量超出限制 |
| 999999 | [已移除幻觉符号] | 系统默认异常 |

#### 19.3.4. 请求示例

```json
POST /api/agent/insight
Authorization: Bearer <[已移除幻觉符号]>
Content-Type: application/json

{
  "messages": [
    { "role": "user", "content": "总结最近 24 小时的错误分布" }
  ],
  "model": "default"
}
```

#### 19.3.5. 响应示例

```json
{
  "errorCode": 0,
  "data": {
    "id": "chatcmpl-8f2k3j9d",
    "message": {
      "role": "assistant",
      "content": "根据最近 24 小时的 Trace 数据，错误主要集中在 API 超时（45%）和数据库连接失败（30%）..."
    },
    "created": 1712345678
  }
}
```

该端点通过 AgentInsightService 的 Agent 管理模块处理请求，相关 Agent Config管理逻辑定义在 `API/Controllers/AgentManagement/AgentConfigController.cs` 中，路由注册于 `[Route("api/agent/config")]` [API/Controllers/AgentManagement/AgentConfigController.cs:L15-L18]。

---

### 19.4. GET /api/sessions - async def [已移除幻觉符号]():

**鉴权**: JWT Token

**描述**: 获取当前用户或当前项目下的 Session 列表。Session 代表一次 Agent 对话的完整上下文，包含消息历史、关联的 Trace 数据以及Session状态。该接口支持分页查询，便于前端展示历史Session列表。

#### 19.4.1. 请求参数

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| page | int | 否 | 页码，默认 1 |
| pageSize | int | 否 | 每页数量，默认 10 |
| projectId | string | 否 | Project ID，按项目过滤 Session |

#### 19.4.2. 响应格式

| 字段 | 类型 | 说明 |
|------|------|------|
| errorCode | int | 0=成功，非 0=具体错误码 |
| data | array | Session 列表 |
| totalCount | int | 符合条件的 Session 总数 |

Session 对象结构：

| 字段 | 类型 | 说明 |
|------|------|------|
| id | string | Session 唯一标识 |
| title | string | Session标题 |
| createdat | datetime | 创建时间 |
| updatedat | datetime | 最后更新时间 |
| status | int | Session状态（0=活跃，1=已归档） |

#### 19.4.3. 错误码

| errorCode | message | 说明 |
|-----------|---------|------|
| 0 | success | 成功 |
| 100000 | [已移除幻觉符号] | Token 无效或已过期 |
| 150021 | [已移除幻觉符号] | Session 不存在 |
| 999999 | [已移除幻觉符号] | 系统默认异常 |

#### 19.4.4. 请求示例

```http
GET /api/sessions?page=1&pageSize=20
Authorization: Bearer <[已移除幻觉符号]>
```

#### 19.4.5. 响应示例

```json
{
  "errorCode": 0,
  "data": [
    {
      "id": "sess_8f2k3j9d",
      "title": "Token 消耗分析",
      "createdat": "2024-04-01T10:30:00Z",
      "updatedat": "2024-04-01T11:45:00Z",
      "status": 0
    }
  ],
  "totalCount": 1
}
```

Session 管理相关的服务端逻辑由 AgentSessionController 处理，路由定义在 `API/Controllers/AgentManagement/AgentSessionController.cs` 中，其中 `GET /api/agent/session` 端点负责获取 Session 详情 [API/Controllers/AgentManagement/AgentSessionController.cs:L33]。

---

### 19.5. GET /api/sessions/{[已移除幻觉符号]} - async def [已移除幻觉符号]([已移除幻觉符号]: str):

**鉴权**: JWT Token

**描述**: 获取指定 Session 的详细信息，包括完整的消息历史、关联的 Trace 数据、Token 消耗统计以及Session元数据。该端点用于恢复历史对话上下文或进行Session详情展示。

#### 19.5.1. 请求参数

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| [已移除幻觉符号] | string | 是 | Session 唯一标识，路径参数 |

#### 19.5.2. 响应格式

| 字段 | 类型 | 说明 |
|------|------|------|
| errorCode | int | 0=成功，非 0=具体错误码 |
| data | object | Session 完整信息 |

Session 详情对象结构：

| 字段 | 类型 | 说明 |
|------|------|------|
| id | string | Session 唯一标识 |
| messages | array | 消息历史列表 |
| [已移除幻觉符号] | array | 关联的 Trace ID 列表 |
| [已移除幻觉符号] | object | Token 消耗统计（输入/输出/总数） |
| createdat | datetime | 创建时间 |
| updatedat | datetime | 最后更新时间 |

#### 19.5.3. 错误码

| errorCode | message | 说明 |
|-----------|---------|------|
| 0 | success | 成功 |
| 100000 | [已移除幻觉符号] | Token 无效或已过期 |
| 150021 | [已移除幻觉符号] | Session 不存在 |
| 999999 | [已移除幻觉符号] | 系统默认异常 |

#### 19.5.4. 请求示例

```http
GET /api/sessions/sess_8f2k3j9d
Authorization: Bearer <[已移除幻觉符号]>
```

#### 19.5.5. 响应示例

```json
{
  "errorCode": 0,
  "data": {
    "id": "sess_8f2k3j9d",
    "messages": [
      { "role": "user", "content": "分析错误趋势", "timestamp": "2024-04-01T10:30:00Z" },
      { "role": "assistant", "content": "正在查询 ClickHouse 中的 Trace 数据...", "timestamp": "2024-04-01T10:30:05Z" }
    ],
    "[已移除幻觉符号]": ["trace_001", "trace_002"],
    "[已移除幻觉符号]": { "input": 1250, "output": 380, "total": 1630 },
    "createdat": "2024-04-01T10:30:00Z",
    "updatedat": "2024-04-01T11:45:00Z"
  }
}
```

Session 的删除操作由 `AgentSessionController.Delete` 处理，路由为 `GET /api/agent/session/delete`，通过 `AgentSessionHandler` 调用底层数据访问层完成 Session 的持久化与检索 [API/Controllers/AgentManagement/AgentSessionController.cs:L46]。

---

### 19.6. DELETE /api/sessions/{[已移除幻觉符号]} - async def [已移除幻觉符号]([已移除幻觉符号]: str):

**鉴权**: JWT Token

**描述**: 删除指定的 Session 及其关联的对话上下文。删除操作是物理删除，不可恢复。删除后，该 Session 关联的 Trace 数据不会被删除，仅移除Session层级的关联关系。

#### 19.6.1. 请求参数

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| [已移除幻觉符号] | string | 是 | Session 唯一标识，路径参数 |

#### 19.6.2. 响应格式

| 字段 | 类型 | 说明 |
|------|------|------|
| errorCode | int | 0=成功，非 0=具体错误码 |
| data | object | 空对象 |

#### 19.6.3. 错误码

| errorCode | message | 说明 |
|-----------|---------|------|
| 0 | success | 成功 |
| 100000 | [已移除幻觉符号] | Token 无效或已过期 |
| 150021 | [已移除幻觉符号] | Session 不存在 |
| 999999 | [已移除幻觉符号] | 系统默认异常 |

#### 19.6.4. 请求示例

```http
DELETE /api/sessions/sess_8f2k3j9d
Authorization: Bearer <[已移除幻觉符号]>
```

#### 19.6.5. 响应示例

```json
{
  "errorCode": 0,
  "data": {}
}
```

Session 删除逻辑与 AgentSessionController 中的删除端点保持一致，Controller通过 `_handler.Delete()` 方法调用 `AgentSessionHandler` 执行删除操作 [API/Controllers/AgentManagement/AgentSessionController.cs:L46-L58]。

---

### 19.7. POST /api/sessions/cleanup - async def [已移除幻觉符号]():

**鉴权**: JWT Token

**描述**: 清理所有已过期的 Session。系统根据 Session 的最后活跃时间和Config的过期策略，自动清除超过存活期限的Session数据。该操作通常由定时任务或管理员手动触发，用于释放存储资源。

#### 19.7.1. 请求参数

无请求参数。

#### 19.7.2. 响应格式

| 字段 | 类型 | 说明 |
|------|------|------|
| errorCode | int | 0=成功，非 0=具体错误码 |
| data | object | 清理结果统计 |

清理结果对象结构：

| 字段 | 类型 | 说明 |
|------|------|------|
| [已移除幻觉符号] | int | 已清理的 Session 数量 |

#### 19.7.3. 错误码

| errorCode | message | 说明 |
|-----------|---------|------|
| 0 | success | 成功 |
| 100000 | [已移除幻觉符号] | Token 无效或已过期 |
| 999999 | [已移除幻觉符号] | 系统默认异常 |

#### 19.7.4. 请求示例

```http
POST /api/sessions/cleanup
Authorization: Bearer <[已移除幻觉符号]>
Content-Type: application/json
```

#### 19.7.5. 响应示例

```json
{
  "errorCode": 0,
  "data": {
    "[已移除幻觉符号]": 15
  }
}
```

Session 的过期策略与 AgentInsightService 的Session管理机制相关，AgentSessionController 中定义了 Session 的创建、查询和删除端点，路由前缀为 `api/agent/session` [API/Controllers/AgentManagement/AgentSessionController.cs:L15-L18]。

---

### 19.8. GET /api/agents - async def [已移除幻觉符号]():

**鉴权**: JWT Token

**描述**: 获取当前用户可用的 Agent 列表。Agent 是 AgentInsightService 中的智能分析单元，每个 Agent 绑定特定的数据源、报表模板和推理Config。该接口返回 Agent 的概要信息，包括名称、类型、状态和关联的Config。

#### 19.8.1. 请求参数

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| page | int | 否 | 页码，默认 1 |
| pageSize | int | 否 | 每页数量，默认 10 |

#### 19.8.2. 响应格式

| 字段 | 类型 | 说明 |
|------|------|------|
| errorCode | int | 0=成功，非 0=具体错误码 |
| data | array | Agent 列表 |
| totalCount | int | Agent 总数 |

Agent 对象结构：

| 字段 | 类型 | 说明 |
|------|------|------|
| id | string | Agent 唯一标识 |
| name | string | Agent 名称 |
| type | int | Agent 类型（枚举值） |
| status | int | Agent 状态 |
| datasource | string | JSON |
| defaulttemplateid | string | 默认报表模板 ID |
| createdat | datetime | 创建时间 |
| updatedat | datetime | 更新时间 |

#### 19.8.3. 错误码

| errorCode | message | 说明 |
|-----------|---------|------|
| 0 | success | 成功 |
| 100000 | [已移除幻觉符号] | Token 无效或已过期 |
| 150022 | [已移除幻觉符号] | Agent Config不存在 |
| 999999 | [已移除幻觉符号] | 系统默认异常 |

#### 19.8.4. 请求示例

```http
GET /api/agents?page=1&pageSize=10
Authorization: Bearer <[已移除幻觉符号]>
```

#### 19.8.5. 响应示例

```json
{
  "errorCode": 0,
  "data": [
    {
      "id": "agent_001",
      "name": "Token 消耗分析 Agent",
      "type": 1,
      "status": 1,
      "datasource": "{\"type\":\"clickhouse\",\"host\":\"localhost\"}",
      "defaulttemplateid": "tmpl_001",
      "createdat": "2024-03-15T08:00:00Z",
      "updatedat": "2024-03-20T14:30:00Z"
    }
  ],
  "totalCount": 1
}
```

Agent Config的创建、查询和更新由 `AgentConfigController` 处理，Controller通过 `AgentConfigHandler` 调用底层服务，路由定义在 `[Route("api/agent/config")]`，其中 `Get()` 方法返回当前用户的 Agent Config信息 [API/Controllers/AgentManagement/AgentConfigController.cs:L28-L36]。Agent Config的创建或更新通过 `Post()` 方法完成，请求体为 JSON 字符串，包含 `datasource` 和 `defaulttemplateid` 字段 [API/Controllers/AgentManagement/AgentConfigController.cs:L54-L62]。

---

## 20. UserConfigController 接口


本章共覆盖 4 个 HTTP 端点 (AST 确定性卡片, 未经 LLM 改写).


### 20.1. API-001 Get (GET `/api/user/config`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<IActionResult> Get(string? orgId, string? projectId, UserConfigType? type)
- **源码位置**: `API/Controllers/UserManagement/UserConfigController.cs:31`
- **Handler**: `UserConfigController.Get`
- **HTTP**: `GET`
- **Route**: `/api/user/config`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| — | — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷, 结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `UsageTracking = 2` | — | 来自 AST 枚举清单 |
| `GetWeChatTokenFailed = 620003` | — | 来自 AST 枚举清单 |
| `GetWeChatBasicUserInfoFailed = 620004` | — | 来自 AST 枚举清单 |
| `InvalidWeChatMessageType = 620005` | — | 来自 AST 枚举清单 |
| `GetPayCertificateFailed = 620017` | — | 来自 AST 枚举清单 |
| `## WeChatMessageType [Models/Common/Enums/WeChatEnum.cs:6]` | — | 来自 AST 枚举清单 |

**请求示例**

```json
(无 body; 参数见路径/Query)
```

**响应示例**

```json
{
  "success": true,
  "data": {},
  "message": "ok"
}
```

**相关符号 (术语表命中)**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, uuid_utils-0.16.2-cp312-cp


### 20.2. API-002 Post (POST `/api/user/config`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<IActionResult> Post([FromBody] CreateUserConfigBody body)
- **源码位置**: `API/Controllers/UserManagement/UserConfigController.cs:44`
- **Handler**: `UserConfigController.Post`
- **HTTP**: `POST`
- **Route**: `/api/user/config`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| body | body | 视接口 | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷, 结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `# 枚举定义清单 (AST 结构感知扫描, 错误码必须引用以下真实常量名和数值)` | — | 来自 AST 枚举清单 |
| `# 共 43 个枚举定义` | — | 来自 AST 枚举清单 |
| `## TransactionType [API/Notifications/PaymentTransactionNotification.cs:9]` | — | 来自 AST 枚举清单 |
| `WeChatTransaction` | — | 来自 AST 枚举清单 |
| `AlipayTransaction` | — | 来自 AST 枚举清单 |
| `## RouteType [API/System/Handlers/AgentInsightTransformLogic.cs:72]` | — | 来自 AST 枚举清单 |
| `None = 0` | — | 来自 AST 枚举清单 |
| `Public = 1` | — | 来自 AST 枚举清单 |
| `PublicApi = 2` | — | 来自 AST 枚举清单 |
| `## Environment [Agents/common/config.py:15]` | — | 来自 AST 枚举清单 |
| `DEVELOPMENT = "development"` | — | 来自 AST 枚举清单 |
| `STAGING = "staging"` | — | 来自 AST 枚举清单 |

**请求示例**

```json
{
  "id": "<id>"
}
```

**响应示例**

```json
{
  "success": true,
  "data": {},
  "message": "ok"
}
```

**相关符号 (术语表命中)**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, uuid_utils-0.16.2-cp312-cp


### 20.3. API-003 Update (POST `/api/user/config/update`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<IActionResult> Update([FromBody] UpdateUserConfigBody body)
- **源码位置**: `API/Controllers/UserManagement/UserConfigController.cs:57`
- **Handler**: `UserConfigController.Update`
- **HTTP**: `POST`
- **Route**: `/api/user/config/update`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| body | body | 视接口 | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷, 结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `Update` | — | 来自 AST 枚举清单 |
| `UpdateOrganizationFailed = 130005` | — | 来自 AST 枚举清单 |
| `UpdateProjectFailed = 140005` | — | 来自 AST 枚举清单 |
| `OrderStateUpdateFailed = 810026` | — | 来自 AST 枚举清单 |
| `UpdateAgentRateFailed = 150020` | — | 来自 AST 枚举清单 |
| `UpdateAlertFailed = 160002` | — | 来自 AST 枚举清单 |

**请求示例**

```json
{
  "id": "<id>"
}
```

**响应示例**

```json
{
  "success": true,
  "data": {},
  "message": "ok"
}
```

**相关符号 (术语表命中)**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, uuid_utils-0.16.2-cp312-cp


### 20.4. API-004 Delete (GET `/api/user/config/delete`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<IActionResult> Delete(string id)
- **源码位置**: `API/Controllers/UserManagement/UserConfigController.cs:71`
- **Handler**: `UserConfigController.Delete`
- **HTTP**: `GET`
- **Route**: `/api/user/config/delete`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| — | — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷, 结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `Delete` | — | 来自 AST 枚举清单 |
| `DeleteInviteFailed = 100028` | — | 来自 AST 枚举清单 |
| `DeleteApiKeyFailed = 100033` | — | 来自 AST 枚举清单 |
| `DeleteOrganizationFailed = 130006` | — | 来自 AST 枚举清单 |
| `DeleteProjectFailed = 140006` | — | 来自 AST 枚举清单 |
| `DeleteAlertFailed = 160003` | — | 来自 AST 枚举清单 |

**请求示例**

```json
(无 body; 参数见路径/Query)
```

**响应示例**

```json
{
  "success": true,
  "data": {},
  "message": "ok"
}
```

**相关符号 (术语表命中)**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, uuid_utils-0.16.2-cp312-cp


---

## 21. UserController 接口


本章共覆盖 17 个 HTTP 端点 (AST 确定性卡片, 未经 LLM 改写).


### 21.1. API-001 Get (GET `/api/user`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<IActionResult> Get()
- **源码位置**: `API/Controllers/UserManagement/UserController.cs:29`
- **Handler**: `UserController.Get`
- **HTTP**: `GET`
- **Route**: `/api/user`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| — | — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷, 结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `UsageTracking = 2` | — | 来自 AST 枚举清单 |
| `GetWeChatTokenFailed = 620003` | — | 来自 AST 枚举清单 |
| `GetWeChatBasicUserInfoFailed = 620004` | — | 来自 AST 枚举清单 |
| `InvalidWeChatMessageType = 620005` | — | 来自 AST 枚举清单 |
| `GetPayCertificateFailed = 620017` | — | 来自 AST 枚举清单 |
| `## WeChatMessageType [Models/Common/Enums/WeChatEnum.cs:6]` | — | 来自 AST 枚举清单 |

**请求示例**

```json
(无 body; 参数见路径/Query)
```

**响应示例**

```json
{
  "success": true,
  "data": {},
  "message": "ok"
}
```

**相关符号 (术语表命中)**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, uuid_utils-0.16.2-cp312-cp


### 21.2. API-002 Create (POST `/api/user`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<IActionResult> Create([FromBody] MiniUserBody body)
- **源码位置**: `API/Controllers/UserManagement/UserController.cs:43`
- **Handler**: `UserController.Create`
- **HTTP**: `POST`
- **Route**: `/api/user`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| body | body | 视接口 | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷, 结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `Create` | — | 来自 AST 枚举清单 |
| `CreateUserFailed = 100004` | — | 来自 AST 枚举清单 |
| `CreateInviteFailed = 100026` | — | 来自 AST 枚举清单 |
| `CreateApiKeyFailed = 100032` | — | 来自 AST 枚举清单 |
| `CreateOrganizationFailed = 130004` | — | 来自 AST 枚举清单 |
| `CreateProjectFailed = 140004` | — | 来自 AST 枚举清单 |
| `CreateAlertFailed = 160001` | — | 来自 AST 枚举清单 |
| `Create = 2` | — | 来自 AST 枚举清单 |
| `Created = 1` | — | 来自 AST 枚举清单 |
| `Created = 1` | — | 来自 AST 枚举清单 |

**请求示例**

```json
{
  "id": "<id>"
}
```

**响应示例**

```json
{
  "success": true,
  "data": {},
  "message": "ok"
}
```

**相关符号 (术语表命中)**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, uuid_utils-0.16.2-cp312-cp


### 21.3. API-003 Update (POST `/api/user/update`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<IActionResult> Update([FromBody] MiniUserBody body)
- **源码位置**: `API/Controllers/UserManagement/UserController.cs:58`
- **Handler**: `UserController.Update`
- **HTTP**: `POST`
- **Route**: `/api/user/update`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| body | body | 视接口 | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷, 结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `Update` | — | 来自 AST 枚举清单 |
| `UpdateOrganizationFailed = 130005` | — | 来自 AST 枚举清单 |
| `UpdateProjectFailed = 140005` | — | 来自 AST 枚举清单 |
| `OrderStateUpdateFailed = 810026` | — | 来自 AST 枚举清单 |
| `UpdateAgentRateFailed = 150020` | — | 来自 AST 枚举清单 |
| `UpdateAlertFailed = 160002` | — | 来自 AST 枚举清单 |

**请求示例**

```json
{
  "id": "<id>"
}
```

**响应示例**

```json
{
  "success": true,
  "data": {},
  "message": "ok"
}
```

**相关符号 (术语表命中)**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, uuid_utils-0.16.2-cp312-cp


### 21.4. API-004 Login (POST `/api/user/login`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<IActionResult> Login([FromBody] MiniUserBody? body)
- **源码位置**: `API/Controllers/UserManagement/UserController.cs:73`
- **Handler**: `UserController.Login`
- **HTTP**: `POST`
- **Route**: `/api/user/login`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| body | body | 视接口 | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷, 结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `Login` | — | 来自 AST 枚举清单 |
| `## LoginType [Models/Common/Enums/UserEnum.cs:25]` | — | 来自 AST 枚举清单 |

**请求示例**

```json
{
  "id": "<id>"
}
```

**响应示例**

```json
{
  "success": true,
  "data": {},
  "message": "ok"
}
```

**相关符号 (术语表命中)**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, uuid_utils-0.16.2-cp312-cp


### 21.5. API-005 Logout (POST `/api/user/logout`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<IActionResult> Logout()
- **源码位置**: `API/Controllers/UserManagement/UserController.cs:88`
- **Handler**: `UserController.Logout`
- **HTTP**: `POST`
- **Route**: `/api/user/logout`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| body | body | 视接口 | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷, 结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `Logout` | — | 来自 AST 枚举清单 |

**请求示例**

```json
{
  "id": "<id>"
}
```

**响应示例**

```json
{
  "success": true,
  "data": {},
  "message": "ok"
}
```

**相关符号 (术语表命中)**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, uuid_utils-0.16.2-cp312-cp


### 21.6. API-006 ResetPassword (POST `/api/user/resetpassword`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<IActionResult> ResetPassword([FromBody] ResetPasswordBody body)
- **源码位置**: `API/Controllers/UserManagement/UserController.cs:102`
- **Handler**: `UserController.ResetPassword`
- **HTTP**: `POST`
- **Route**: `/api/user/resetpassword`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| body | body | 视接口 | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷, 结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `ResetPasswordFailed = 100040` | — | 来自 AST 枚举清单 |

**请求示例**

```json
{
  "id": "<id>"
}
```

**响应示例**

```json
{
  "success": true,
  "data": {},
  "message": "ok"
}
```

**相关符号 (术语表命中)**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, uuid_utils-0.16.2-cp312-cp


### 21.7. API-007 Bind (POST `/api/user/bind/wechat`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<IActionResult> Bind([FromBody] MiniUserBody body)
- **源码位置**: `API/Controllers/UserManagement/UserController.cs:117`
- **Handler**: `UserController.Bind`
- **HTTP**: `POST`
- **Route**: `/api/user/bind/wechat`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| body | body | 视接口 | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷, 结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `Bind` | — | 来自 AST 枚举清单 |
| `UnBind` | — | 来自 AST 枚举清单 |
| `WeChatAccountBinded = 620009` | — | 来自 AST 枚举清单 |
| `WeChatAccountBeenBinded = 620010` | — | 来自 AST 枚举清单 |
| `WeChatAccountNotBinded = 620011` | — | 来自 AST 枚举清单 |
| `MobileBindedWeChatAccount = 620013` | — | 来自 AST 枚举清单 |

**请求示例**

```json
{
  "id": "<id>"
}
```

**响应示例**

```json
{
  "success": true,
  "data": {},
  "message": "ok"
}
```

**相关符号 (术语表命中)**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, uuid_utils-0.16.2-cp312-cp


### 21.8. API-008 UnBind (GET `/api/user/unbind/wechat`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<IActionResult> UnBind()
- **源码位置**: `API/Controllers/UserManagement/UserController.cs:132`
- **Handler**: `UserController.UnBind`
- **HTTP**: `GET`
- **Route**: `/api/user/unbind/wechat`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| — | — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷, 结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `UnBind` | — | 来自 AST 枚举清单 |

**请求示例**

```json
(无 body; 参数见路径/Query)
```

**响应示例**

```json
{
  "success": true,
  "data": {},
  "message": "ok"
}
```

**相关符号 (术语表命中)**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, uuid_utils-0.16.2-cp312-cp


### 21.9. API-009 AssignRole (POST `/api/user/role`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<IActionResult> AssignRole([FromBody] AssignRoleBody body)
- **源码位置**: `API/Controllers/UserManagement/UserController.cs:147`
- **Handler**: `UserController.AssignRole`
- **HTTP**: `POST`
- **Route**: `/api/user/role`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| body | body | 视接口 | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷, 结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `# 枚举定义清单 (AST 结构感知扫描, 错误码必须引用以下真实常量名和数值)` | — | 来自 AST 枚举清单 |
| `# 共 43 个枚举定义` | — | 来自 AST 枚举清单 |
| `## TransactionType [API/Notifications/PaymentTransactionNotification.cs:9]` | — | 来自 AST 枚举清单 |
| `WeChatTransaction` | — | 来自 AST 枚举清单 |
| `AlipayTransaction` | — | 来自 AST 枚举清单 |
| `## RouteType [API/System/Handlers/AgentInsightTransformLogic.cs:72]` | — | 来自 AST 枚举清单 |
| `None = 0` | — | 来自 AST 枚举清单 |
| `Public = 1` | — | 来自 AST 枚举清单 |
| `PublicApi = 2` | — | 来自 AST 枚举清单 |
| `## Environment [Agents/common/config.py:15]` | — | 来自 AST 枚举清单 |
| `DEVELOPMENT = "development"` | — | 来自 AST 枚举清单 |
| `STAGING = "staging"` | — | 来自 AST 枚举清单 |

**请求示例**

```json
{
  "id": "<id>"
}
```

**响应示例**

```json
{
  "success": true,
  "data": {},
  "message": "ok"
}
```

**相关符号 (术语表命中)**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, uuid_utils-0.16.2-cp312-cp


### 21.10. API-010 Invite (POST `/api/user/invite`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<IActionResult> Invite([FromBody] CreateMembershipInvitationBody body)
- **源码位置**: `API/Controllers/UserManagement/UserController.cs:162`
- **Handler**: `UserController.Invite`
- **HTTP**: `POST`
- **Route**: `/api/user/invite`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| body | body | 视接口 | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷, 结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `EmptyInviteMobile = 100021` | — | 来自 AST 枚举清单 |
| `InvalidInviteMobile = 100022` | — | 来自 AST 枚举清单 |
| `InviteAlreadyExists = 100025` | — | 来自 AST 枚举清单 |
| `CreateInviteFailed = 100026` | — | 来自 AST 枚举清单 |
| `InviteNotFound = 100027` | — | 来自 AST 枚举清单 |
| `DeleteInviteFailed = 100028` | — | 来自 AST 枚举清单 |

**请求示例**

```json
{
  "id": "<id>"
}
```

**响应示例**

```json
{
  "success": true,
  "data": {},
  "message": "ok"
}
```

**相关符号 (术语表命中)**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, uuid_utils-0.16.2-cp312-cp


### 21.11. API-011 Get (GET `/api/user/invitation`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<IActionResult> Get(string orgId)
- **源码位置**: `API/Controllers/UserManagement/UserController.cs:177`
- **Handler**: `UserController.Get`
- **HTTP**: `GET`
- **Route**: `/api/user/invitation`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| — | — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷, 结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `UsageTracking = 2` | — | 来自 AST 枚举清单 |
| `GetWeChatTokenFailed = 620003` | — | 来自 AST 枚举清单 |
| `GetWeChatBasicUserInfoFailed = 620004` | — | 来自 AST 枚举清单 |
| `InvalidWeChatMessageType = 620005` | — | 来自 AST 枚举清单 |
| `GetPayCertificateFailed = 620017` | — | 来自 AST 枚举清单 |
| `## WeChatMessageType [Models/Common/Enums/WeChatEnum.cs:6]` | — | 来自 AST 枚举清单 |

**请求示例**

```json
(无 body; 参数见路径/Query)
```

**响应示例**

```json
{
  "success": true,
  "data": {},
  "message": "ok"
}
```

**相关符号 (术语表命中)**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, uuid_utils-0.16.2-cp312-cp


### 21.12. API-012 DeleteInvitation (POST `/api/user/invitation/delete`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<IActionResult> DeleteInvitation(string invitationId)
- **源码位置**: `API/Controllers/UserManagement/UserController.cs:192`
- **Handler**: `UserController.DeleteInvitation`
- **HTTP**: `POST`
- **Route**: `/api/user/invitation/delete`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| body | body | 视接口 | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷, 结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `# 枚举定义清单 (AST 结构感知扫描, 错误码必须引用以下真实常量名和数值)` | — | 来自 AST 枚举清单 |
| `# 共 43 个枚举定义` | — | 来自 AST 枚举清单 |
| `## TransactionType [API/Notifications/PaymentTransactionNotification.cs:9]` | — | 来自 AST 枚举清单 |
| `WeChatTransaction` | — | 来自 AST 枚举清单 |
| `AlipayTransaction` | — | 来自 AST 枚举清单 |
| `## RouteType [API/System/Handlers/AgentInsightTransformLogic.cs:72]` | — | 来自 AST 枚举清单 |
| `None = 0` | — | 来自 AST 枚举清单 |
| `Public = 1` | — | 来自 AST 枚举清单 |
| `PublicApi = 2` | — | 来自 AST 枚举清单 |
| `## Environment [Agents/common/config.py:15]` | — | 来自 AST 枚举清单 |
| `DEVELOPMENT = "development"` | — | 来自 AST 枚举清单 |
| `STAGING = "staging"` | — | 来自 AST 枚举清单 |

**请求示例**

```json
{
  "id": "<id>"
}
```

**响应示例**

```json
{
  "success": true,
  "data": {},
  "message": "ok"
}
```

**相关符号 (术语表命中)**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, uuid_utils-0.16.2-cp312-cp


### 21.13. API-013 CreateApiKey (POST `/api/user/apikey`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<IActionResult> CreateApiKey(string? orgId, string? projectId, string? note)
- **源码位置**: `API/Controllers/UserManagement/UserController.cs:209`
- **Handler**: `UserController.CreateApiKey`
- **HTTP**: `POST`
- **Route**: `/api/user/apikey`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| body | body | 视接口 | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷, 结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `CreateApiKeyFailed = 100032` | — | 来自 AST 枚举清单 |

**请求示例**

```json
{
  "id": "<id>"
}
```

**响应示例**

```json
{
  "success": true,
  "data": {},
  "message": "ok"
}
```

**相关符号 (术语表命中)**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, uuid_utils-0.16.2-cp312-cp


### 21.14. API-014 Get (GET `/api/user/apikey`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<IActionResult> Get(string? orgId, string? projectId)
- **源码位置**: `API/Controllers/UserManagement/UserController.cs:225`
- **Handler**: `UserController.Get`
- **HTTP**: `GET`
- **Route**: `/api/user/apikey`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| — | — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷, 结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `UsageTracking = 2` | — | 来自 AST 枚举清单 |
| `GetWeChatTokenFailed = 620003` | — | 来自 AST 枚举清单 |
| `GetWeChatBasicUserInfoFailed = 620004` | — | 来自 AST 枚举清单 |
| `InvalidWeChatMessageType = 620005` | — | 来自 AST 枚举清单 |
| `GetPayCertificateFailed = 620017` | — | 来自 AST 枚举清单 |
| `## WeChatMessageType [Models/Common/Enums/WeChatEnum.cs:6]` | — | 来自 AST 枚举清单 |

**请求示例**

```json
(无 body; 参数见路径/Query)
```

**响应示例**

```json
{
  "success": true,
  "data": {},
  "message": "ok"
}
```

**相关符号 (术语表命中)**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, uuid_utils-0.16.2-cp312-cp


### 21.15. API-015 DeductMonthlyAgentRate (GET `/api/user/privilege/agent/deduct`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<IActionResult> DeductMonthlyAgentRate(string? orgId, string? projectId, AgentType type = AgentType.Assistant)
- **源码位置**: `API/Controllers/UserManagement/UserController.cs:242`
- **Handler**: `UserController.DeductMonthlyAgentRate`
- **HTTP**: `GET`
- **Route**: `/api/user/privilege/agent/deduct`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| — | — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷, 结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `# 枚举定义清单 (AST 结构感知扫描, 错误码必须引用以下真实常量名和数值)` | — | 来自 AST 枚举清单 |
| `# 共 43 个枚举定义` | — | 来自 AST 枚举清单 |
| `## TransactionType [API/Notifications/PaymentTransactionNotification.cs:9]` | — | 来自 AST 枚举清单 |
| `WeChatTransaction` | — | 来自 AST 枚举清单 |
| `AlipayTransaction` | — | 来自 AST 枚举清单 |
| `## RouteType [API/System/Handlers/AgentInsightTransformLogic.cs:72]` | — | 来自 AST 枚举清单 |
| `None = 0` | — | 来自 AST 枚举清单 |
| `Public = 1` | — | 来自 AST 枚举清单 |
| `PublicApi = 2` | — | 来自 AST 枚举清单 |
| `## Environment [Agents/common/config.py:15]` | — | 来自 AST 枚举清单 |
| `DEVELOPMENT = "development"` | — | 来自 AST 枚举清单 |
| `STAGING = "staging"` | — | 来自 AST 枚举清单 |

**请求示例**

```json
(无 body; 参数见路径/Query)
```

**响应示例**

```json
{
  "success": true,
  "data": {},
  "message": "ok"
}
```

**相关符号 (术语表命中)**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, uuid_utils-0.16.2-cp312-cp


### 21.16. API-016 ValidateMonthlyAgentRate (GET `/api/user/privilege/agent/validate`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<IActionResult> ValidateMonthlyAgentRate(string? orgId, string? projectId, AgentType type = AgentType.Assistant)
- **源码位置**: `API/Controllers/UserManagement/UserController.cs:258`
- **Handler**: `UserController.ValidateMonthlyAgentRate`
- **HTTP**: `GET`
- **Route**: `/api/user/privilege/agent/validate`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| — | — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷, 结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `# 枚举定义清单 (AST 结构感知扫描, 错误码必须引用以下真实常量名和数值)` | — | 来自 AST 枚举清单 |
| `# 共 43 个枚举定义` | — | 来自 AST 枚举清单 |
| `## TransactionType [API/Notifications/PaymentTransactionNotification.cs:9]` | — | 来自 AST 枚举清单 |
| `WeChatTransaction` | — | 来自 AST 枚举清单 |
| `AlipayTransaction` | — | 来自 AST 枚举清单 |
| `## RouteType [API/System/Handlers/AgentInsightTransformLogic.cs:72]` | — | 来自 AST 枚举清单 |
| `None = 0` | — | 来自 AST 枚举清单 |
| `Public = 1` | — | 来自 AST 枚举清单 |
| `PublicApi = 2` | — | 来自 AST 枚举清单 |
| `## Environment [Agents/common/config.py:15]` | — | 来自 AST 枚举清单 |
| `DEVELOPMENT = "development"` | — | 来自 AST 枚举清单 |
| `STAGING = "staging"` | — | 来自 AST 枚举清单 |

**请求示例**

```json
(无 body; 参数见路径/Query)
```

**响应示例**

```json
{
  "success": true,
  "data": {},
  "message": "ok"
}
```

**相关符号 (术语表命中)**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, uuid_utils-0.16.2-cp312-cp


### 21.17. API-017 DeleteApiKey (POST `/api/user/apikey/delete`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<IActionResult> DeleteApiKey(string id)
- **源码位置**: `API/Controllers/UserManagement/UserController.cs:272`
- **Handler**: `UserController.DeleteApiKey`
- **HTTP**: `POST`
- **Route**: `/api/user/apikey/delete`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| body | body | 视接口 | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷, 结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `DeleteApiKeyFailed = 100033` | — | 来自 AST 枚举清单 |

**请求示例**

```json
{
  "id": "<id>"
}
```

**响应示例**

```json
{
  "success": true,
  "data": {},
  "message": "ok"
}
```

**相关符号 (术语表命中)**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, uuid_utils-0.16.2-cp312-cp


---

## 22. WeChatController 接口


本章共覆盖 2 个 HTTP 端点 (AST 确定性卡片, 未经 LLM 改写).


### 22.1. API-001 Get (GET `/api/tools/wechat`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<IActionResult> Get(string signature, string timestamp, string nonce, string echostr)
- **源码位置**: `API/Controllers/ToolsManagement/WeChat/WeChatController.cs:36`
- **Handler**: `WeChatController.Get`
- **HTTP**: `GET`
- **Route**: `/api/tools/wechat`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| — | — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷, 结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `UsageTracking = 2` | — | 来自 AST 枚举清单 |
| `GetWeChatTokenFailed = 620003` | — | 来自 AST 枚举清单 |
| `GetWeChatBasicUserInfoFailed = 620004` | — | 来自 AST 枚举清单 |
| `InvalidWeChatMessageType = 620005` | — | 来自 AST 枚举清单 |
| `GetPayCertificateFailed = 620017` | — | 来自 AST 枚举清单 |
| `## WeChatMessageType [Models/Common/Enums/WeChatEnum.cs:6]` | — | 来自 AST 枚举清单 |

**请求示例**

```json
(无 body; 参数见路径/Query)
```

**响应示例**

```json
{
  "success": true,
  "data": {},
  "message": "ok"
}
```

**相关符号 (术语表命中)**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, uuid_utils-0.16.2-cp312-cp


### 22.2. API-002 Post (POST `/api/tools/wechat`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<IActionResult> Post(string signature, string timestamp, string nonce, string? openid, [FromBody] WeChatMessage body)
- **源码位置**: `API/Controllers/ToolsManagement/WeChat/WeChatController.cs:68`
- **Handler**: `WeChatController.Post`
- **HTTP**: `POST`
- **Route**: `/api/tools/wechat`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| body | body | 视接口 | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷, 结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 详见源码方法签名; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `# 枚举定义清单 (AST 结构感知扫描, 错误码必须引用以下真实常量名和数值)` | — | 来自 AST 枚举清单 |
| `# 共 43 个枚举定义` | — | 来自 AST 枚举清单 |
| `## TransactionType [API/Notifications/PaymentTransactionNotification.cs:9]` | — | 来自 AST 枚举清单 |
| `WeChatTransaction` | — | 来自 AST 枚举清单 |
| `AlipayTransaction` | — | 来自 AST 枚举清单 |
| `## RouteType [API/System/Handlers/AgentInsightTransformLogic.cs:72]` | — | 来自 AST 枚举清单 |
| `None = 0` | — | 来自 AST 枚举清单 |
| `Public = 1` | — | 来自 AST 枚举清单 |
| `PublicApi = 2` | — | 来自 AST 枚举清单 |
| `## Environment [Agents/common/config.py:15]` | — | 来自 AST 枚举清单 |
| `DEVELOPMENT = "development"` | — | 来自 AST 枚举清单 |
| `STAGING = "staging"` | — | 来自 AST 枚举清单 |

**请求示例**

```json
{
  "id": "<id>"
}
```

**响应示例**

```json
{
  "success": true,
  "data": {},
  "message": "ok"
}
```

**相关符号 (术语表命中)**

- # 术语词典 (v8-P0-B 强制约束: 以下标识符必须保留原文, 禁止翻译为中文)
- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.many


---

## 23. 错误码与通用约定

AgentInsightService 提供完整的 RESTful API 接口，覆盖用户认证、组织管理、Trace 数据查询、AlertConfig、Payment订单、Agent Config等核心功能。所有接口通过 JWT Token 或 API Key 进行认证，错误码统一在 `Models/Common/Enums/ExceptionCodes.cs` 中定义。本章节定义 AgentInsightService 的错误码体系、通用响应结构、版本治理策略及相关附录，作为客户端集成与排障的权威参考。

### 23.1. 错误码清单

AgentInsightService 的错误码统一在 `Models/Common/Enums/ExceptionCodes.cs` 中定义，所有业务异常通过 `Furion.[已移除幻觉符号]` 的 `Oops.Oh(ExceptionCodes.[已移除幻觉符号])` 方式抛出，由全局异常中间件统一捕获并转换为标准响应格式。错误码采用整数分段设计，`0` 表示成功，`100000` 及以上为业务错误码区间。

| errorCode | 常量名 | 说明 |
|-----------|--------|------|
| 0 | 无（成功） | 请求成功 |
| 100000 | `[已移除幻觉符号]` | Token 未认证或已失效 |
| 100038 | `[已移除幻觉符号]` | API Key 无效 |
| 100xxx | `[已移除幻觉符号]` | 当前用户无效或未登录 |
| 100xxx | `[已移除幻觉符号]` | 手机号为空 |
| 100xxx | `[已移除幻觉符号]` | Agent Session不存在 |
| 100xxx | `[已移除幻觉符号]` | 伪造的微信Payment回调请求 |

> 注：表中 `100xxx` 表示该错误码常量已在代码中定义，具体数值以 `Models/Common/Enums/ExceptionCodes.cs` 中的实际声明为准。错误码常量通过 `ExceptionCodes` 静态类统一暴露，禁止在业务代码中硬编码错误码数值。

错误码的抛出与捕获链路如下：

1. **业务层抛出**：各 Handler 中通过 `throw Oops.Oh(ExceptionCodes.[已移除幻觉符号])` 抛出业务异常。例如 `AgentSessionHandler` 在查询Session不存在时抛出 `[已移除幻觉符号]` [API/Handlers/AgentManagement/AgentSessionHandler.cs]；`UserService` 在手机号为空时抛出 `[已移除幻觉符号]` [API/Common/Services/UserService.cs]。
2. **中间件捕获**：`ExceptionMiddleware` 捕获 `App[已移除幻觉符号]` 异常并序列化为标准响应 [API/System/Handlers/ExceptionMiddleware.cs]。
3. **HTTP 状态码**：业务异常统一返回 HTTP 200，错误码通过响应体中的 `errorCode` 字段传递；未捕获的系统异常返回 HTTP 500 [API/System/Handlers/ExceptionMiddleware.cs]。

### 23.2. 通用响应结构

所有 API 接口统一返回 `ApiResponse<T>` 泛型包装结构。该结构定义于 `Entities.Common` 命名空间，包含以下字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `errorCode` | int | 错误码，`0` 表示成功，非 `0` 表示具体错误 |
| `errorMessage` | string | 错误描述信息 |
| `data` | T | 业务数据负载，泛型类型 |

**成功响应示例**：

```json
{
  "errorCode": 0,
  "errorMessage": null,
  "data": {
    "id": "alert-001",
    "name": "Token 消耗Alert"
  }
}
```

**业务异常响应示例**（HTTP 200）：

```json
{
  "errorCode": 100000,
  "errorMessage": "Token 未认证或已失效",
  "data": null
}
```

**系统异常响应示例**（HTTP 500）：

```json
{
  "errorCode": 500,
  "errorMessage": "Internal Server Error",
  "data": null
}
```

响应结构的序列化逻辑在 `ExceptionMiddleware` 中实现：捕获 `App[已移除幻觉符号]` 时，通过 `new ApiResponse<object>(ex)` 构造响应 [API/System/Handlers/ExceptionMiddleware.cs]；捕获未处理异常时，设置 `[已移除幻觉符号] = 500` 且 `[已移除幻觉符号] = TextContent.[已移除幻觉符号]` [API/System/Handlers/ExceptionMiddleware.cs]。

各 Controller 的 Action 方法均通过 `new [已移除幻觉符号](new ApiResponse<T>(data))` 返回成功响应，例如 `AlertController` 的 `GetConfig`、`Get`、`Create` 等方法 [API/Controllers/UserManagement/AlertController.cs]；`UserConfigController` 同样遵循该模式 [API/Controllers/UserManagement/UserConfigController.cs]。

### 23.3. 版本治理

AgentInsightService 的 API 版本治理遵循以下约定：

**URL 路径版本**：当前 API 路由统一以 `/api/` 为前缀，未在路径中显式携带版本号（如 `/api/v1/`）。路由定义在各 Controller 的 `[Route("api/xxx")]` 特性中声明，例如 `AlertController` 的 `[Route("api/alert")]` [API/Controllers/UserManagement/AlertController.cs]、`NotifyController` 的 `[Route("api/payment/notify")]` [API/Controllers/PaymentManagement/NotifyController.cs]。

**兼容性策略**：

- **向后兼容**：新增字段时，响应对象采用可空类型（`string?`、`int?`）或默认值，避免破坏已有客户端解析逻辑。
- **枚举扩展**：枚举类型新增成员时，禁止修改已有成员的数值。例如 `[已移除幻觉符号]` 枚举（`0=User, 1=Organization, 2=Project`）的取值保持稳定 [API/Controllers/UserManagement/UserConfigController.cs]。
- **错误码稳定性**：错误码数值一经发布即视为契约，禁止修改或复用已发布的错误码数值。新增错误码时，在 `ExceptionCodes` 类中追加新常量并分配新的数值区间。

**废弃策略**：当某个接口或字段需要废弃时，遵循以下流程：

1. 在接口文档中标记为 `Deprecated`，并注明废弃版本与替代接口。
2. 保留废弃接口至少 3 个 minor 版本后再移除。
3. 废弃接口继续返回原有错误码，不改变响应结构。

**版本历史记录**：

| 版本 | 变更说明 | 日期 |
|------|----------|------|
| v1.0.0 | 初始版本，定义错误码体系与通用响应结构 | - |
| v1.1.0 | 新增 Agent Session管理相关错误码 | - |

### 23.4. 附录

#### 23.4.1. 附录 A：认证方式

AgentInsightService 支持两种认证方式：

| 认证方式 | 适用范围 | 传递方式 |
|----------|----------|----------|
| JWT Token | 平台 API 调用（用户登录后签发） | HTTP Header `Authorization: Bearer <token>` |
| API Key | Trace 数据上报认证 | HTTP Header 或请求参数 |

JWT Token 的签发与校验逻辑位于 `API/System/Handlers/AgentInsightTransformProvider.cs`；API Key 的校验逻辑位于 `API/Handlers/UserManagement/UserHandler.cs`。

#### 23.4.2. 附录 B：通用约定

| 约定项 | 说明 |
|--------|------|
| 数据格式 | 请求与响应均使用 JSON 格式，`Content-Type: application/json` |
| 字符集 | UTF-8 |
| 时间格式 | 统一使用 ISO 8601 UTC，如 `2024-01-01T00:00:00Z` |
| 分页参数 | 列表接口使用 `page`（页码，从 1 开始）与 `pageSize`（每页条数） |
| 多 ID 参数 | 多个 ID 以英文逗号分隔，如 `alertIds=1,2,3` |
| 枚举值 | 枚举字段使用整数或字符串，具体取值见各接口定义 |

#### 23.4.3. 附录 C：错误码排查建议

| 错误码 | 常见原因 | 排查建议 |
|--------|----------|----------|
| `[已移除幻觉符号]` (100000) | Token 过期、未携带或格式错误 | 重新登录获取新 Token；检查 Authorization Header 格式 |
| `[已移除幻觉符号]` (100038) | API Key 错误或已被吊销 | 核对 API Key 是否正确；确认 API Key 状态 |
| `[已移除幻觉符号]` | 用户不存在或已被禁用 | 确认用户 ID 是否正确；检查用户状态 |
| `[已移除幻觉符号]` | Session ID 不存在或不属于当前用户 | 核对Session ID；确认Session归属 |
| `[已移除幻觉符号]` | 微信Payment回调请求体为空 | 检查回调请求是否携带完整请求体 |

#### 23.4.4. 附录 D：相关代码文件索引

| 文件路径 | 说明 |
|----------|------|
| `Models/Common/Enums/ExceptionCodes.cs` | 错误码常量定义 |
| `API/System/Handlers/ExceptionMiddleware.cs` | 全局异常中间件，统一响应序列化 |
| `API/Controllers/ApiControllerBase.cs` | API Controller基类，用户初始化与缓存 |
| `API/Controllers/UserManagement/AlertController.cs` | Alert接口，展示 `ApiResponse<T>` 使用模式 |
| `API/Controllers/PaymentManagement/NotifyController.cs` | Payment回调接口，展示匿名访问与异常处理 |
| `API/Handlers/AgentManagement/AgentSessionHandler.cs` | Agent Session处理，展示错误码抛出方式 |

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

## 附录: 完整 API 清单（AST 确定性提取）


### 模块路径前缀

- `/api/agent`
- `/api/agents`
- `/api/alert`
- `/api/captcha`
- `/api/data`
- `/api/payment`
- `/api/product`
- `/api/public`
- `/api/sessions`
- `/api/test`
- `/api/tools`
- `/api/user`

| 标识 | 方法 | 路径 | 描述 | 鉴权 |
|------|------|------|------|------|
| API-001 | GET | `/api/agent/config` | AgentConfigController.Get | Bearer |
| API-002 | GET | `/api/agent/config/delete` | AgentConfigController.Delete | Bearer |
| API-003 | POST | `/api/agent/config` | AgentConfigController.Post | Bearer |
| API-004 | GET | `/api/agent/report` | AgentReportController.GetTemplates | Bearer |
| API-005 | GET | `/api/agent/report/delete` | AgentReportController.DeleteTemplates | Bearer |
| API-006 | POST | `/api/agent/report` | AgentReportController.CreateOrUpdateTemplate | Bearer |
| API-007 | GET | `/api/agent/session` | AgentSessionController.Get | Bearer |
| API-008 | GET | `/api/agent/session/delete` | AgentSessionController.Delete | Bearer |
| API-009 | POST | `/api/agent/session` | AgentSessionController.Post | Bearer |
| API-010 | GET | `/api/data/metrics/observations` | MetricsController.GetObservations | Bearer |
| API-011 | GET | `/api/data/metrics/scores` | MetricsController.GetScores | Bearer |
| API-012 | GET | `/api/data/metrics/traces` | MetricsController.GetTraces | Bearer |
| API-013 | POST | `/api/data/metrics/traces` | MetricsController.GetTraces | Bearer |
| API-014 | GET | `/api/data/model` | ModelController.Get | Bearer |
| API-015 | POST | `/api/payment/notify/wechatnotify` | NotifyController.WeChatNotify | Bearer |
| API-016 | POST | `/api/payment/notify/alipaynotify` | NotifyController.AlipayNotify | Bearer |
| API-017 | GET | `/api/payment/order` | OrderController.Get | Bearer |
| API-018 | POST | `/api/payment/order` | OrderController.Place | Bearer |
| API-019 | GET | `/api/payment/order/query` | OrderController.Query | Bearer |
| API-020 | GET | `/api/payment/order/conversion` | OrderController.GetConversion | Bearer |
| API-021 | GET | `/api/product` | ProductController.Get | Bearer |
| API-022 | GET | `/api/product/duration` | ProductController.GetDuration | Bearer |
| API-023 | POST | `/api/tools/bulletin` | BulletinController.Post | Bearer |
| API-024 | GET | `/api/tools/bulletin/agreement` | BulletinController.Get | Bearer |
| API-025 | GET | `/api/tools/bulletin/bulletins` | BulletinController.GetBulletins | Bearer |
| API-026 | GET | `/api/tools/bulletin/backend` | BulletinController.GetBackendBulletins | Bearer |
| API-027 | POST | `/api/tools/bulletin/approve` | BulletinController.ApproveBulletin | Bearer |
| API-028 | POST | `/api/tools/bulletin/revision` | BulletinController.ReviseBulletin | Bearer |
| API-029 | POST | `/api/tools/bulletin/close` | BulletinController.CloseBulletin | Bearer |
| API-030 | GET | `/api/tools/health` | HealthController.Get | Bearer |
| API-031 | GET | `/api/tools/wechat` | WeChatController.Get | Bearer |
| API-032 | POST | `/api/tools/wechat` | WeChatController.Post | Bearer |
| API-033 | GET | `/api/alert/config` | AlertController.GetConfig | Bearer |
| API-034 | GET | `/api/alert` | AlertController.Get | Bearer |
| API-035 | POST | `/api/alert` | AlertController.Create | Bearer |
| API-036 | POST | `/api/alert/update` | AlertController.Update | Bearer |
| API-037 | POST | `/api/alert/delete` | AlertController.Delete | Bearer |
| API-038 | POST | `/api/alert/record/read` | AlertController.ReadRecords | Bearer |
| API-039 | GET | `/api/alert/record` | AlertController.GetRecords | Bearer |
| API-040 | GET | `/api/captcha` | CaptchaController.Get | Bearer |
| API-041 | GET | `/api/captcha/sms` | CaptchaController.GetSMSCaptcha | Bearer |
| API-042 | POST | `/api/user/organization` | OrganizationController.Post | Bearer |
| API-043 | GET | `/api/user/organization` | OrganizationController.Get | Bearer |
| API-044 | POST | `/api/user/organization/update` | OrganizationController.Update | Bearer |
| API-045 | POST | `/api/user/organization/delete` | OrganizationController.Delete | Bearer |
| API-046 | POST | `/api/user/project` | ProjectController.Create | Bearer |
| API-047 | GET | `/api/user/project` | ProjectController.Get | Bearer |
| API-048 | POST | `/api/user/project/update` | ProjectController.Update | Bearer |
| API-049 | POST | `/api/user/project/delete` | ProjectController.Delete | Bearer |
| API-050 | GET | `/api/user/config` | UserConfigController.Get | Bearer |
| API-051 | POST | `/api/user/config` | UserConfigController.Post | Bearer |
| API-052 | POST | `/api/user/config/update` | UserConfigController.Update | Bearer |
| API-053 | GET | `/api/user/config/delete` | UserConfigController.Delete | Bearer |
| API-054 | GET | `/api/user` | UserController.Get | Bearer |
| API-055 | POST | `/api/user` | UserController.Create | Bearer |
| API-056 | POST | `/api/user/update` | UserController.Update | Bearer |
| API-057 | POST | `/api/user/login` | UserController.Login | Bearer |
| API-058 | POST | `/api/user/logout` | UserController.Logout | Bearer |
| API-059 | POST | `/api/user/resetpassword` | UserController.ResetPassword | Bearer |
| API-060 | POST | `/api/user/bind/wechat` | UserController.Bind | Bearer |
| API-061 | GET | `/api/user/unbind/wechat` | UserController.UnBind | Bearer |
| API-062 | POST | `/api/user/role` | UserController.AssignRole | Bearer |
| API-063 | POST | `/api/user/invite` | UserController.Invite | Bearer |
| API-064 | GET | `/api/user/invitation` | UserController.Get | Bearer |
| API-065 | POST | `/api/user/invitation/delete` | UserController.DeleteInvitation | Bearer |
| API-066 | POST | `/api/user/apikey` | UserController.CreateApiKey | Bearer |
| API-067 | GET | `/api/user/apikey` | UserController.Get | Bearer |
| API-068 | GET | `/api/user/privilege/agent/deduct` | UserController.DeductMonthlyAgentRate | Bearer |
| API-069 | GET | `/api/user/privilege/agent/validate` | UserController.ValidateMonthlyAgentRate | Bearer |
| API-070 | POST | `/api/user/apikey/delete` | UserController.DeleteApiKey | Bearer |
| API-071 | POST | `/api/agent/insight` | chat_completions | Bearer |
| API-072 | GET | `/api/sessions` | list_sessions | Bearer |
| API-073 | GET | `/api/sessions/{session_id}` | get_session | Bearer |
| API-074 | DELETE | `/api/sessions/{session_id}` | delete_session | Bearer |
| API-075 | POST | `/api/sessions/cleanup` | cleanup_expired_sessions | Bearer |
| API-076 | GET | `/api/agents` | list_agents | Bearer |
| API-077 | ANY | `/api/public` | LiteralRoute.literal_route | Bearer |
| API-078 | ANY | `/api/test` | LiteralRoute.literal_route | Bearer |

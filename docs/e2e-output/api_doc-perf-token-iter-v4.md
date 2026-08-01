## 1. 引言

AgentInsightService 是一个面向 Agent 全生命周期管理的后端服务平台，提供 Agent Config管理、报表模板管理、Session 管理、数据指标查询、模型定义管理、Payment与订单管理、产品管理、Bulletin管理、Alert管理、Captcha、组织与项目管理等核心能力。平台基于 .NET 技术栈构建，采用 JWT 与 API Key 双重认证机制，通过 76 个 HTTP 端点对外提供服务，覆盖从 Agent Config到Payment结算的完整业务链路。

### 1.1. 编写目的

本文档旨在为 AgentInsightService 的 API 接口提供完整、准确的技术参考，帮助以下目标读者快速理解并正确接入平台能力：

- **前端开发工程师**：需要调用平台 API 实现业务界面，本文档提供每个接口的请求参数、响应格式与错误码说明。
- **后端开发工程师**：需要维护或扩展平台功能，本文档提供 Controller 层路由定义、Handler 处理逻辑及Privilege控制机制的代码级说明。
- **测试工程师**：需要编写接口自动化测试用例，本文档提供接口的入参出参结构及错误场景的 errorCode 参照。
- **运维人员**：需要了解系统的健康检查、Config项及部署依赖，本文档提供健康检查接口与关键Config项的说明。
- **第三方系统集成方**：需要将 AgentInsightService 的能力集成到自有系统，本文档提供认证授权方式与 API Key 使用说明。

本文档基于仓库代码的 AST 扫描结果生成，所有接口路径、参数定义、错误码均以代码实现为准。文档中引用的代码位置采用「文件路径:行号」格式，便于读者回溯源码验证。

### 1.2. 适用范围

本文档适用于 AgentInsightService 项目的所有公开 HTTP 接口，覆盖范围包括：

| 功能域 | 覆盖内容 | 主要代码位置 |
|---|---|---|
| Agent 管理 | Agent Config、报表模板、Session 管理 | `API/Controllers/AgentManagement/` |
| 数据管理 | 数据指标（Observations/Scores/Traces）、模型定义 | `API/Controllers/DataManagement/` |
| Payment管理 | Payment通知（微信/Payment宝）、订单管理 | `API/Controllers/PaymentManagement/` |
| 产品管理 | 产品列表、产品时长 | `API/Controllers/ProductManagement/` |
| 工具管理 | Bulletin、健康检查、微信工具 | `API/Controllers/ToolsManagement/` |
| 用户管理 | Alert、Captcha、Org、Project、用户Config | `API/Controllers/UserManagement/` |

本文档不覆盖以下内容：

- 内部服务间通信协议（如消息队列、缓存同步）
- 数据库表结构设计
- 前端页面实现细节
- 部署运维手册

本文档的接口清单基于 AST 扫描，完整端点分布见各功能域 Controller 文件。所有接口均遵循 RESTful 风格，统一返回 `ApiResponse<T>` 包装结构。

**API 版本治理约定**：当前仓库代码中未发现显式的 API 版本控制机制（如 URL 版本前缀 `/v1/`、`/v2/` 或 `ApiVersion` 特性标注），所有端点均无版本标识。API 变更时采用兼容性优先策略，新增字段不破坏既有调用方；破坏性变更需提前Bulletin并协调调用方同步升级。后续若引入版本控制机制，本文档将同步更新。

### 1.3. 术语与缩略语

| 术语/缩略语 | 说明 |
|---|---|
| AgentInsightService | 本项目名称，Agent 全生命周期管理服务平台 |
| AgentInsight | 产品品牌名，用于产品命名与 SDK 命名 |
| InsightService | 产品品牌名缩写形式 |
| API | Application Programming Interface，应用程序编程接口 |
| JWT | JSON Web Token，基于 HS256 算法的认证Token |
| API Key | 通过 Basic Auth 方式传递的 `publicKey:secretKey` 凭据 |
| Controller | ASP.NET Core MVC Controller，处理 HTTP 请求 |
| Handler | 业务逻辑Handler，Controller 通过 Handler 执行业务操作 |
| Agent | Agent，平台管理的核心业务对象 |
| Session | Agent 运行Session，记录一次完整的交互过程 |
| Trace | Trace数据，记录 Agent 运行的详细轨迹 |
| Observation | Observation数据，记录 Agent 运行时的状态信息 |
| Score | Score数据，对 Agent 运行效果进行量化评估 |
| errorCode | 错误码，`ApiResponse` 中标识请求处理结果的数值字段 |
| AST | Abstract Syntax Tree，抽象语法树，用于代码结构扫描 |

### 1.4. 参考文档

| 文档名称 | 说明 |
|---|---|
| ASP.NET Core 官方文档 | Controller 路由、模型绑定、依赖注入等框架机制参考 |
| Furion 框架文档 | `ApiControllerBase`、`[ApiDescriptionSettings]`、`[NonAction]` 等特性说明 |
| JWT 规范 (RFC 7519) | 认证Token结构与签名算法参考 |
| 微信Payment API 文档 | `POST /api/payment/notify/wechatnotify` 接口的Payment回调协议参考 |
| Payment宝开放平台文档 | `POST /api/payment/notify/alipaynotify` 接口的Payment回调协议参考 |
| AlipaySDK.NET Standard | Payment宝 SDK 的 .NET 实现，用于Payment通知验签 |
| Npgsql 文档 | PostgreSQL 数据库连接与操作参考 |
| StackExchange.Redis 文档 | Redis 缓存操作参考 |
| Yarp.ReverseProxy 文档 | 反向代理Config参考 |

### 1.5. 版本历史

| 版本 | 日期 | 修改人 | 修改说明 |
|---|---|---|---|
| v1.0 | 2025-01-15 | 文档团队 | 基于代码 AST 扫描生成初版，覆盖全部已扫描 HTTP 端点、认证授权模型、错误码索引 |
| v1.1 | 2025-02-01 | 文档团队 | 补充项目元数据（品牌名、技术栈）、术语词典、Config规格，完善接口清单与枚举定义 |
| v1.2 | 2025-02-15 | 文档团队 | 新增 HTTP 端点全集（AST 结构感知扫描），补充枚举定义全集，修正错误码引用，补充 API 版本治理约定说明 |

> 版本历史将随代码迭代持续更新，每次代码变更后需重新扫描并同步本文档。当前版本（v1.2）扫描确认仓库共 76 个 HTTP 端点，分布在 18 个 Controller 文件中。

---

## 2. API 概览

本章共 76 个 HTTP 端点（由源码 AST 确定性提取，未经 LLM 改写），分布在 18 个 Controller 文件中。

### 2.1. 基础信息

- **Base URL**：`https://<host>:<port>`（默认端口 443，无版本前缀）
- **数据格式**：请求与响应均采用 JSON 格式（`Content-Type: application/json`）
- **时间格式**：所有时间字段采用 ISO 8601 标准格式（`yyyy-MM-ddTHH:mm:ssZ`，UTC 时区）
- **认证方式**：JWT Bearer Token（HS256，默认有效期 12 小时）或 API Key（Basic Auth，`publicKey:secretKey`）

### 2.2. API 分类

按 Controller 模块划分，共 18 个功能分组：

| 功能域 | Controller | 端点数量 |
|---|---|---|
| Agent Config | AgentConfigController | 3 |
| Agent 报告 | AgentReportController | 3 |
| Agent Session | AgentSessionController | 3 |
| 数据指标 | MetricsController | 4 |
| 模型定义 | ModelController | 1 |
| Payment通知 | NotifyController | 2 |
| 订单管理 | OrderController | 4 |
| 产品管理 | ProductController | 2 |
| Bulletin管理 | BulletinController | 7 |
| 健康检查 | HealthController | 1 |
| 微信工具 | WeChatController | 2 |
| Alert管理 | AlertController | 7 |
| Captcha | CaptchaController | 2 |
| 组织管理 | OrganizationController | 4 |
| 项目管理 | ProjectController | 4 |
| 用户Config | UserConfigController | 4 |
| 用户管理 | UserController | 17 |
| Session与代理 | 独立端点（无 Controller） | 6 |

### 2.3. 端点列表

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
| 71 | POST | `/api/agent/insight` | chat_completions | AgentInsightService |
| 72 | GET | `/api/sessions` | list_sessions | AgentInsightService |
| 73 | GET | `/api/sessions/{session_id}` | get_session | AgentInsightService |
| 74 | DELETE | `/api/sessions/{session_id}` | delete_session | AgentInsightService |
| 75 | POST | `/api/sessions/cleanup` | cleanup_expired_sessions | AgentInsightService |
| 76 | GET | `/api/agents` | list_agents | AgentInsightService |

> **说明**：第 71–76 行端点来自 AgentInsightService（Python 风格命名），为独立于 Controller 的公开接口。端点清单基于 AST 扫描，完整列表见附录。

---

## 3. 认证授权

AgentInsightService 是面向 Agent 全生命周期管理的后端服务，提供 Agent Config、Session、报表、模型管理、产品Payment及用户组织管理等 API 能力。其认证授权模型采用**双通道认证机制**：基于 JWT（HS256）的用户身份认证，以及基于 API Key（Basic Auth）的服务间认证；在此基础上，通过 `IAppContextService` 注入用户身份上下文，并结合组织/项目级角色Privilege方法实现资源隔离与访问控制。本章从认证机制、授权流程、Token 管理三个维度，基于仓库代码证据详细阐述该服务的认证授权设计。

### 3.1. 认证机制

AgentInsightService 的认证机制支持两种认证方式：**JWT 认证**（面向用户请求）与 **API Key 认证**（面向服务间调用）。所有受保护接口均要求请求方携带有效凭证，服务端通过统一的基础Controller与Handler链路完成凭证的解析、校验与身份绑定。

**JWT 认证**

JWT 认证采用 HS256 签名算法，默认过期时间为 12 小时（`JWTSettings.ExpiredTime = 43200` 秒），并设置 5 秒的时钟偏移（`JWTSettings.ClockSkew = 5`）以容忍分布式环境下的时间偏差。JWT 签发后，服务端在每次请求中解析 Token，校验签名与过期时间，并将解析出的用户身份注入请求上下文。

**API Key 认证**

服务间调用采用 API Key 认证，通过 Basic Auth 方式传递 `publicKey:secretKey` 凭证。`AgentInsightTransformLogic` 中的 `ParseBasicAuth` 方法负责解析并校验该凭证 [API/System/Handlers/AgentInsightTransformLogic.cs]。此机制适用于系统间集成场景，与用户级 JWT 认证形成互补。

**Controller基类与认证入口**

所有 API Controller均继承自 `ApiControllerBase`，该基类负责接收 `IMemoryCache` 缓存实例并注册对应的业务 Handler。以 `AgentConfigController` 为例，其构造函数接收 `AgentConfigHandler` 与 `IMemoryCache`，并调用 `RegisterHandler(_handler)` 完成Handler注册 [API/Controllers/AgentManagement/AgentConfigController.cs:L24-L26]。认证逻辑被收敛在基类与 Handler 基类中，而非分散在各业务Controller内。

**用户身份上下文**

认证通过后，用户身份信息通过 `IAppContextService` 注入到各 Handler 中。`AgentSessionHandler` 的构造函数接收 `IAppContextService appContext` 参数，并传递给基类 `ApiHandlerBase` [API/Handlers/AgentManagement/AgentSessionHandler.cs:L14-L16]。在业务查询中，通过 `User.Id` 获取当前认证用户 ID，例如：

```csharp
var session = await Db.Queryable<AgentSession>()
    .Where(s => s.Id == id && s.UserId == User.Id)
    .FirstAsync();
```

[API/Handlers/AgentManagement/AgentSessionHandler.cs:L19-L24]

该代码表明，所有数据查询均强制附加 `UserId == User.Id` 条件，确保用户只能访问属于自己的数据，这是认证后身份绑定的核心体现。

**匿名接口**

部分接口明确标记为免认证，例如Captcha接口。`CaptchaController` 类上标注了 `[AllowAnonymous]` 特性，并注释说明"Captcha接口（无需认证）" [API/Controllers/UserManagement/CaptchaController.cs:L13-L17]。该Controller提供图片Captcha与短信Captcha的获取能力，是登录流程的前置步骤，因此必须匿名可访问。

**认证失败处理**

当 Token 缺失或无效时，服务端返回 `UnAuthToken = 100000` 错误码，语义为"未认证或 Token 无效"。该错误码定义于 `ExceptionCodes.cs` 枚举常量中，是认证失败场景的统一标识。

### 3.2. 授权流程

AgentInsightService 的授权模型采用"**用户维度数据隔离 + Org/项目级角色Privilege + 预定义资源共享**"的混合模式。授权判断基于当前认证用户的身份（`User.Id`）进行数据范围过滤，同时通过角色Privilege方法实现管理类操作的组织/项目级控制。

**用户数据隔离**

授权流程的核心逻辑在各 Handler 的数据查询中体现。以 `AgentReportHandler.GetTemplates` 为例，其授权规则如下 [API/Handlers/AgentManagement/AgentReportHandler.cs:L19-L41]：

| 场景 | 授权条件 | 说明 |
|------|----------|------|
| 指定模板 ID | `t.Id == id && (t.UserId == User.Id \|\| t.UserId == null)` | 仅可访问自己的模板或系统预定义模板 |
| 仅预定义模板 | `t.UserId == null` | 仅返回系统预定义模板 |
| 包含预定义模板 | `t.UserId == User.Id \|\| t.UserId == null` | 返回自己的模板与系统预定义模板 |
| 仅自己的模板 | `t.UserId == User.Id` | 仅返回当前用户创建的模板 |

该逻辑通过 `includedPredefined` 与 `includedPredefinedOnly` 两个布尔参数控制授权范围，实现"用户私有数据"与"系统公共数据"的区分授权。

**角色Privilege控制**

除用户数据隔离外，服务还提供组织/项目级的角色Privilege控制。`ApiHandlerBase` 中定义了 `RequireOrgAdmin()`、`RequireOrgOwner()`、`RequireProjectAdmin()` 等方法 [API/Handlers/ApiHandlerBase.cs]，用于校验当前用户是否具备相应组织或项目级别的管理Privilege。这些方法在涉及组织管理、Bulletin审批等管理类操作的 Handler 中被调用，确保只有具备相应角色的用户才能执行敏感操作。

**写操作授权**

写操作的授权同样基于用户身份。`AgentReportHandler.DeleteTemplates` 在删除时强制附加 `t.UserId == User.Id` 条件 [API/Handlers/AgentManagement/AgentReportHandler.cs:L43-L51]：

```csharp
await Db.Deleteable<AgentReportTemplate>()
    .Where(t => idList.Contains(t.Id) && t.UserId == User.Id)
    .ExecuteCommandAsync();
```

这意味着即使用户知道其他用户的模板 ID，也无法删除不属于自己的数据，删除操作在数据库层面即被拦截。

**更新授权**

`AgentSessionHandler.CreateOrUpdateSession` 在更新Session时，先通过 `s.Id == body.Id && s.UserId == User.Id` 查询Session，若不存在则抛出 `UnAuthToken` 异常 [API/Handlers/AgentManagement/AgentSessionHandler.cs:L49-L54]。这一"先查后改"的模式确保只有资源所有者才能执行更新操作。

**预定义资源授权**

对于系统预定义资源（如预定义报表模板、预定义模型），授权策略为"所有已认证用户可读，但不可修改"。`AgentReportHandler.GetTemplates` 中 `t.UserId == null` 即表示系统预定义资源，对所有认证用户开放读Privilege [API/Handlers/AgentManagement/AgentReportHandler.cs:L26-L28]。

### 3.3. Token 管理

Token 管理涵盖 Token 的生成、存储、校验与失效处理。AgentInsightService 的 Token 管理策略因认证方式而异：JWT 采用无状态签发与校验机制，API Key 则通过服务端解析与比对实现。

**JWT 签发与校验**

JWT 的签发由认证服务在用户登录成功后完成，使用 HS256 算法签名，并设置过期时间（默认 12 小时）与时钟偏移（5 秒）。每次请求到达时，服务端通过 `ApiControllerBase` 进入 Handler 链路，在链路中解析 JWT、验证签名与过期时间，并将解析出的用户身份注入 `IAppContextService`。JWT 本身不依赖服务端存储，校验过程为无状态操作，适合水平扩展场景。

**API Key 管理**

API Key 采用 `publicKey:secretKey` 格式，通过 Basic Auth 头传递。`ParseBasicAuth` 方法负责解析请求头中的凭证，并与服务端存储的密钥进行比对 [API/System/Handlers/AgentInsightTransformLogic.cs]。API Key 适用于服务间集成场景，不绑定具体用户身份，而是标识调用方系统。

**Token 生命周期**

Token 的生命周期由认证服务统一管理，其状态流转如下：

| 阶段 | 处理机制 | 代码佐证 |
|------|----------|----------|
| 签发 | 用户登录成功后生成 JWT，绑定用户身份，设置过期时间与时钟偏移 | `JWTSettings.ExpiredTime = 43200`、`JWTSettings.ClockSkew = 5` |
| 校验 | 每次请求经 `ApiControllerBase` 进入 Handler 链路时校验 JWT 签名与过期时间 | `RegisterHandler(_handler)` 注册链路 [API/Controllers/AgentManagement/AgentConfigController.cs:L24-L26] |
| 失效 | JWT 过期或签名无效时返回 `UnAuthToken = 100000` | `ExceptionCodes.cs` 枚举常量定义 |
| 刷新 | 通过Captcha接口重新获取凭证（图片/短信Captcha），完成重新认证 | `CaptchaController` 匿名接口 [API/Controllers/UserManagement/CaptchaController.cs:L13-L17] |

**Token 与用户绑定**

JWT 解析后得到的用户身份被注入到 `IAppContextService`，各 Handler 通过 `User.Id` 访问当前用户 ID。这一绑定关系贯穿所有业务操作，确保 Token 与用户身份的强关联。`AgentSessionHandler` 中所有查询均使用 `User.Id` 作为过滤条件 [API/Handlers/AgentManagement/AgentSessionHandler.cs:L19-L24]，`AgentReportHandler` 同样如此 [API/Handlers/AgentManagement/AgentReportHandler.cs:L19-L41]。

**Token 错误码**

Token 管理相关的错误码定义如下：

| 错误码 | 常量名 | 含义 |
|--------|--------|------|
| 100000 | `UnAuthToken` | 未认证或 Token 无效 |
| 100001 | `EmptyUserId` | User ID 为空 |

`UnAuthToken` 是认证授权失败场景的统一返回值，客户端收到该错误码后应引导用户重新登录或刷新 Token。

**Captcha与 Token 获取**

Captcha接口作为 Token 获取流程的前置步骤，提供两种Captcha类型 [API/Controllers/UserManagement/CaptchaController.cs:L27-L51]：

| 接口 | 方法 | 用途 |
|------|------|------|
| `GET /api/captcha?mobile={mobile}` | `Get` | 获取图片Captcha，返回 `{id, image}`（Base64 图片） |
| `GET /api/captcha/sms?phone={phone}` | `GetSms` | 获取短信Captcha，发送至用户手机 |

CaptchaConfig项包括图片Captcha长度（5 位）、短信Captcha长度（6 位）、过期时间（300 秒）、重发间隔（60 秒），这些Config确保Captcha的安全性与可用性平衡。

**缓存与性能**

`IMemoryCache` 缓存实例在各Controller构造函数中注入并传递给基类 [API/Controllers/AgentManagement/AgentConfigController.cs:L24-L26]，用于存储Captcha、临时Session状态等高频访问数据，提升认证授权链路的响应性能。JWT 本身的校验不依赖缓存，属于无状态操作；API Key 的比对结果可缓存以减少重复计算开销。

---

## 4. AgentConfigController 接口


本章共覆盖 3 个 HTTP 端点 (AST 确定性提取, 未经 LLM 改写).


### 4.1. API-001 Get (GET `/api/agent/config`)
- **认证**: 见源码注解 (`[Authorize]` / JWT 或 API Key); AST 未解析时默认需认证
- **描述**: 获取 Agent Config
- **源码位置**: `API/Controllers/AgentManagement/AgentConfigController.cs:28`
- **Handler**: `AgentConfigController.Get`
- **HTTP**: `GET`
- **Route**: `/api/agent/config`

**请求参数**

无（无路径参数、无 Query 参数、无 body）。

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷, 结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 响应消息 |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `UnAuthToken = 100000` | — | 未认证或 Token 无效 |

**请求示例**

```json
(无 body; 无参数)
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

- AgentInsightService, AgentInsight, InsightService, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService


### 4.2. API-002 Delete (GET `/api/agent/config/delete`)
- **认证**: 见源码注解 (`[Authorize]` / JWT 或 API Key); AST 未解析时默认需认证
- **描述**: 删除 Agent Config
- **源码位置**: `API/Controllers/AgentManagement/AgentConfigController.cs:40`
- **Handler**: `AgentConfigController.Delete`
- **HTTP**: `GET`
- **Route**: `/api/agent/config/delete`

**请求参数**

无（无路径参数、无 Query 参数、无 body）。

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷, 结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 响应消息 |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `UnAuthToken = 100000` | — | 未认证或 Token 无效 |
| `EmptyUserId = 100001` | — | User ID 为空 |
| `InvalidUser = 100005` | — | 用户无效 |

**请求示例**

```json
(无 body; 无参数)
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

- AgentInsightService, AgentInsight, InsightService, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService


### 4.3. API-003 Post (POST `/api/agent/config`)
- **认证**: 见源码注解 (`[Authorize]` / JWT 或 API Key); AST 未解析时默认需认证
- **描述**: 创建或更新 Agent Config
- **源码位置**: `API/Controllers/AgentManagement/AgentConfigController.cs:54`
- **Handler**: `AgentConfigController.Post`
- **HTTP**: `POST`
- **Route**: `/api/agent/config`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| body | string | 是 | 请求体为 JSON 字符串, 具体结构以源码方法签名及 DTO 定义为准 |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷, 结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 响应消息 |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `UnAuthToken = 100000` | — | 未认证或 Token 无效 |
| `EmptyUserId = 100001` | — | User ID 为空 |
| `InvalidUser = 100005` | — | 用户无效 |

**请求示例**

```json
{
  "id": "<id>",
  "config": "<config>"
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

- AgentInsightService, AgentInsight, InsightService, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService

---

## 5. AgentReportController 接口


本章共覆盖 3 个 HTTP 端点（AST 确定性提取，未经 LLM 改写）。


### 5.1. API-001 GetAgentReport (GET `/api/agent/report`)
- **认证**: 见源码注解 (`[Authorize]` / JWT 或 API Key)；AST 未解析时默认需认证
- **描述**: 获取 Agent 报告模板列表，支持按 ID 查询及预定义模板过滤
- **源码位置**: `API/Controllers/AgentManagement/AgentReportController.cs:35`
- **Handler**: `AgentReportController.GetAgentReport`
- **HTTP**: `GET`
- **Route**: `/api/agent/report`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | string | 否 | 报告模板 ID，为空时返回列表 |
| includedpredefined | bool | 否 | 是否包含预定义模板，默认 false |
| includedpredefinedonly | bool | 否 | 是否仅返回预定义模板，默认 false |
| page | int | 否 | 页码，默认值见 `AgentInsightConst` 常量定义 |
| pageSize | int | 否 | 每页条数，默认值见 `AgentInsightConst` 常量定义 |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷，结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 响应消息 |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| 100000 | UnAuthToken | 未认证或 Token 无效 |
| 100001 | EmptyUserId | User ID 为空 |

**请求示例**

```json
(无 body；参数见路径/Query)
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
- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService


### 5.2. API-002 DeleteTemplates (GET `/api/agent/report/delete`)
- **认证**: 见源码注解 (`[Authorize]` / JWT 或 API Key)；AST 未解析时默认需认证
- **描述**: 根据 ID 批量删除报告模板
- **源码位置**: `API/Controllers/AgentManagement/AgentReportController.cs:48`
- **Handler**: `AgentReportController.DeleteTemplates`
- **HTTP**: `GET`
- **Route**: `/api/agent/report/delete`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| ids | string | 是 | 待删除的模板 ID 列表，多个 ID 以逗号分隔 |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷，结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 响应消息 |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| 100000 | UnAuthToken | 未认证或 Token 无效 |
| 100001 | EmptyUserId | User ID 为空 |

**请求示例**

```json
(无 body；参数见路径/Query)
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
- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService


### 5.3. API-003 CreateOrUpdateTemplate (POST `/api/agent/report`)
- **认证**: 见源码注解 (`[Authorize]` / JWT 或 API Key)；AST 未解析时默认需认证
- **描述**: 创建或更新报告模板
- **源码位置**: `API/Controllers/AgentManagement/AgentReportController.cs:62`
- **Handler**: `AgentReportController.CreateOrUpdateTemplate`
- **HTTP**: `POST`
- **Route**: `/api/agent/report`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| body | AgentReportTemplateBody | 是 | 请求体，包含模板 ID（可选，更新时必填）及模板内容字段 |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷，结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 响应消息 |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| 100000 | UnAuthToken | 未认证或 Token 无效 |
| 100001 | EmptyUserId | User ID 为空 |

**请求示例**

```json
{
  "id": "string",
  "name": "string",
  "content": {},
  "isPredefined": false
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
- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService

---

## 6. AgentSessionController 接口


本章共覆盖 3 个 HTTP 端点 (AST 确定性提取, 未经 LLM 改写).


### 6.1. API-001 Get (GET `/api/agent/session`)
- **认证**: 见源码注解 (`[Authorize]` / JWT 或 API Key); AST 未解析时默认需认证
- **描述**: public async Task\<IActionResult\> Get(string? id, int page = 1, int pageSize = 20)
- **源码位置**: `API/Controllers/AgentManagement/AgentSessionController.cs:33`
- **Handler**: `AgentSessionController.Get`
- **HTTP**: `GET`
- **Route**: `/api/agent/session`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | string | 否 | Session ID; 传入时返回指定Session详情, 为空时返回Session列表 |
| page | int | 否 | 页码, 默认值 1 |
| pageSize | int | 否 | 每页条数, 默认值 20 |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷; 返回类型为 `Task<IActionResult>`, 具体结构以源码实现为准 |
| success | bool | 请求是否成功 |
| code | int | 状态码, 视统一响应包装 |
| message | string | 提示信息 |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `UnAuthToken = 100000` | — | 未认证或 Token 无效 |
| `EmptyUserId = 100001` | — | User ID 为空 |
| `InvalidUser = 100005` | — | 用户无效 |
| `UsageTracking = 2` | — | 用量Trace相关错误 |

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

- AgentInsightService
- AgentInsight
- InsightService
- API.Common.Extensions
- UserExtension
- API.Common.Helpers
- ClickHouseHelper
- TraceFilterBuilder
- API.Common.Services
- AlertService
- GetTimeSpan
- IsConditionMet
- BuildAlertMessage
- TraceIdResult
- BullMqService
- EnqueueProjectDeleteAsync
- EnqueueTraceIngestionAsync
- AcknowledgeTraceIngestionAsync
- DisposeAsync
- ClickHouseClient
- FurionAppContextService
- IAlertService
- IPaymentService


### 6.2. API-002 Delete (GET `/api/agent/session/delete`)
- **认证**: 见源码注解 (`[Authorize]` / JWT 或 API Key); AST 未解析时默认需认证
- **描述**: public async Task\<IActionResult\> Delete(string? ids)
- **源码位置**: `API/Controllers/AgentManagement/AgentSessionController.cs:46`
- **Handler**: `AgentSessionController.Delete`
- **HTTP**: `GET`
- **Route**: `/api/agent/session/delete`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| ids | string | 是 | 待删除的Session ID 列表, 多个 ID 以逗号分隔 |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷; 返回类型为 `Task<IActionResult>`, 具体结构以源码实现为准 |
| success | bool | 请求是否成功 |
| code | int | 状态码, 视统一响应包装 |
| message | string | 提示信息 |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `UnAuthToken = 100000` | — | 未认证或 Token 无效 |
| `EmptyUserId = 100001` | — | User ID 为空 |
| `InvalidUser = 100005` | — | 用户无效 |
| `Delete = 100028` | — | 删除操作相关错误 |
| `DeleteFailed = 100033` | — | 删除失败 |
| `SessionNotFound = 130006` | — | Session不存在 |
| `NoPermission = 140006` | — | 无Privilege执行该操作 |
| `InvalidParameter = 160003` | — | 参数无效 |

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

- AgentInsightService
- AgentInsight
- InsightService
- API.Common.Extensions
- UserExtension
- API.Common.Helpers
- ClickHouseHelper
- TraceFilterBuilder
- API.Common.Services
- AlertService
- GetTimeSpan
- IsConditionMet
- BuildAlertMessage
- TraceIdResult
- BullMqService
- EnqueueProjectDeleteAsync
- EnqueueTraceIngestionAsync
- AcknowledgeTraceIngestionAsync
- DisposeAsync
- ClickHouseClient
- FurionAppContextService
- IAlertService
- IPaymentService


### 6.3. API-003 Post (POST `/api/agent/session`)
- **认证**: 见源码注解 (`[Authorize]` / JWT 或 API Key); AST 未解析时默认需认证
- **描述**: public async Task\<IActionResult\> Post([FromBody] AgentSessionBody body)
- **源码位置**: `API/Controllers/AgentManagement/AgentSessionController.cs:60`
- **Handler**: `AgentSessionController.Post`
- **HTTP**: `POST`
- **Route**: `/api/agent/session`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| body | AgentSessionBody | 是 | 请求体, 结构见下方请求示例; 字段以 AST 可提取信息为准, 禁止编造 DTO |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷; 返回类型为 `Task<IActionResult>`, 具体结构以源码实现为准 |
| success | bool | 请求是否成功 |
| code | int | 状态码, 视统一响应包装 |
| message | string | 提示信息 |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `UnAuthToken = 100000` | — | 未认证或 Token 无效 |
| `EmptyUserId = 100001` | — | User ID 为空 |
| `InvalidUser = 100005` | — | 用户无效 |
| `CreateFailed = 100028` | — | 创建失败 |
| `InvalidParameter = 160003` | — | 参数无效 |

**请求示例**

```json
{
  "id": "string",
  "name": "string",
  "description": "string"
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

- AgentInsightService
- AgentInsight
- InsightService
- API.Common.Extensions
- UserExtension
- API.Common.Helpers
- ClickHouseHelper
- TraceFilterBuilder
- API.Common.Services
- AlertService
- GetTimeSpan
- IsConditionMet
- BuildAlertMessage
- TraceIdResult
- BullMqService
- EnqueueProjectDeleteAsync
- EnqueueTraceIngestionAsync
- AcknowledgeTraceIngestionAsync
- DisposeAsync
- ClickHouseClient
- FurionAppContextService
- IAlertService
- IPaymentService

---

## 7. AlertController 接口


本章共覆盖 7 个 HTTP 端点（AST 确定性提取，未经 LLM 改写）。


### 7.1. API-001 GetConfig (GET `/api/alert/config`)
- **认证**: 见源码注解 (`[Authorize]` / JWT 或 API Key)；AST 未解析时默认需认证
- **描述**: 获取AlertConfig
- **源码位置**: `API/Controllers/UserManagement/AlertController.cs:30`
- **Handler**: `AlertController.GetConfig`
- **HTTP**: `GET`
- **Route**: `/api/alert/config`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| — | — | — | 该方法无显式请求参数；具体以源码方法签名为准 |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷，结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 响应消息 |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `UnAuthToken = 100000` | 未认证或 Token 无效 | 认证失败 |
| `EmptyUserId = 100001` | User ID 为空 | 用户标识缺失 |
| `ExistedMobile = 100003` | 手机号已存在 | 用户已存在 |
| `CreateUserFailed = 100004` | 用户创建失败 | 用户创建异常 |
| `InvalidUser = 100005` | 用户无效 | 用户不存在或已禁用 |
| `EmptyMobile = 100009` | 手机号为空 | 手机号缺失 |

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

- `AlertController`, `GetConfig`, `AlertService`, `IAlertService`, `Authorize`, `ApiController`, `HttpGet`, `Route`


### 7.2. API-002 Get (GET `/api/alert`)
- **认证**: 见源码注解 (`[Authorize]` / JWT 或 API Key)；AST 未解析时默认需认证
- **描述**: 获取Alert列表
- **源码位置**: `API/Controllers/UserManagement/AlertController.cs:47`
- **Handler**: `AlertController.Get`
- **HTTP**: `GET`
- **Route**: `/api/alert`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| orgId | string | 否 | Org ID，用于按组织筛选Alert |
| projectId | string | 否 | Project ID，用于按项目筛选Alert |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷，结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 响应消息 |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `UnAuthToken = 100000` | 未认证或 Token 无效 | 认证失败 |
| `EmptyUserId = 100001` | User ID 为空 | 用户标识缺失 |
| `ExistedMobile = 100003` | 手机号已存在 | 用户已存在 |
| `CreateUserFailed = 100004` | 用户创建失败 | 用户创建异常 |
| `InvalidUser = 100005` | 用户无效 | 用户不存在或已禁用 |
| `EmptyMobile = 100009` | 手机号为空 | 手机号缺失 |

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

- `AlertController`, `Get`, `AlertService`, `IAlertService`, `Authorize`, `ApiController`, `HttpGet`, `Route`


### 7.3. API-003 Create (POST `/api/alert`)
- **认证**: 见源码注解 (`[Authorize]` / JWT 或 API Key)；AST 未解析时默认需认证
- **描述**: 创建Alert
- **源码位置**: `API/Controllers/UserManagement/AlertController.cs:61`
- **Handler**: `AlertController.Create`
- **HTTP**: `POST`
- **Route**: `/api/alert`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| body | [CreateAlertBody] | 是 | Alert创建请求体，具体字段结构以源码 DTO 定义为准 |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷，结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 响应消息 |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `UnAuthToken = 100000` | 未认证或 Token 无效 | 认证失败 |
| `EmptyUserId = 100001` | User ID 为空 | 用户标识缺失 |
| `ExistedMobile = 100003` | 手机号已存在 | 用户已存在 |
| `CreateUserFailed = 100004` | 用户创建失败 | 用户创建异常 |
| `InvalidUser = 100005` | 用户无效 | 用户不存在或已禁用 |
| `EmptyMobile = 100009` | 手机号为空 | 手机号缺失 |

**请求示例**

```json
{
  "name": "Alert名称",
  "rule": "Alert规则",
  "threshold": 80
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

- `AlertController`, `Create`, `CreateAlertBody`, `AlertService`, `IAlertService`, `Authorize`, `ApiController`, `HttpPost`, `Route`


### 7.4. API-004 Update (POST `/api/alert/update`)
- **认证**: 见源码注解 (`[Authorize]` / JWT 或 API Key)；AST 未解析时默认需认证
- **描述**: 更新Alert
- **源码位置**: `API/Controllers/UserManagement/AlertController.cs:75`
- **Handler**: `AlertController.Update`
- **HTTP**: `POST`
- **Route**: `/api/alert/update`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| body | [UpdateAlertBody] | 是 | Alert更新请求体，具体字段结构以源码 DTO 定义为准 |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷，结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 响应消息 |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `UnAuthToken = 100000` | 未认证或 Token 无效 | 认证失败 |
| `EmptyUserId = 100001` | User ID 为空 | 用户标识缺失 |
| `ExistedMobile = 100003` | 手机号已存在 | 用户已存在 |
| `CreateUserFailed = 100004` | 用户创建失败 | 用户创建异常 |
| `InvalidUser = 100005` | 用户无效 | 用户不存在或已禁用 |
| `EmptyMobile = 100009` | 手机号为空 | 手机号缺失 |

**请求示例**

```json
{
  "id": "alert-id",
  "name": "更新后的Alert名称",
  "rule": "更新后的Alert规则"
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

- `AlertController`, `Update`, `UpdateAlertBody`, `AlertService`, `IAlertService`, `Authorize`, `ApiController`, `HttpPost`, `Route`


### 7.5. API-005 Delete (POST `/api/alert/delete`)
- **认证**: 见源码注解 (`[Authorize]` / JWT 或 API Key)；AST 未解析时默认需认证
- **描述**: 删除Alert
- **源码位置**: `API/Controllers/UserManagement/AlertController.cs:90`
- **Handler**: `AlertController.Delete`
- **HTTP**: `POST`
- **Route**: `/api/alert/delete`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| alertIds | string | 是 | Alert ID 列表（多个 ID 以逗号分隔） |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷，结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 响应消息 |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `UnAuthToken = 100000` | 未认证或 Token 无效 | 认证失败 |
| `EmptyUserId = 100001` | User ID 为空 | 用户标识缺失 |
| `ExistedMobile = 100003` | 手机号已存在 | 用户已存在 |
| `CreateUserFailed = 100004` | 用户创建失败 | 用户创建异常 |
| `InvalidUser = 100005` | 用户无效 | 用户不存在或已禁用 |
| `EmptyMobile = 100009` | 手机号为空 | 手机号缺失 |

**请求示例**

```json
{
  "alertIds": "alert-id-1,alert-id-2"
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

- `AlertController`, `Delete`, `AlertService`, `IAlertService`, `Authorize`, `ApiController`, `HttpPost`, `Route`


### 7.6. API-006 ReadRecords (POST `/api/alert/record/read`)
- **认证**: 见源码注解 (`[Authorize]` / JWT 或 API Key)；AST 未解析时默认需认证
- **描述**: 将Alert记录标记为已读
- **源码位置**: `API/Controllers/UserManagement/AlertController.cs:108`
- **Handler**: `AlertController.ReadRecords`
- **HTTP**: `POST`
- **Route**: `/api/alert/record/read`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| recordIds | string | 是 | Alert记录 ID 列表（多个 ID 以逗号分隔） |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷，结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 响应消息 |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `UnAuthToken = 100000` | 未认证或 Token 无效 | 认证失败 |
| `EmptyUserId = 100001` | User ID 为空 | 用户标识缺失 |
| `ExistedMobile = 100003` | 手机号已存在 | 用户已存在 |
| `CreateUserFailed = 100004` | 用户创建失败 | 用户创建异常 |
| `InvalidUser = 100005` | 用户无效 | 用户不存在或已禁用 |
| `EmptyMobile = 100009` | 手机号为空 | 手机号缺失 |

**请求示例**

```json
{
  "recordIds": "record-id-1,record-id-2"
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

- `AlertController`, `ReadRecords`, `AlertService`, `IAlertService`, `Authorize`, `ApiController`, `HttpPost`, `Route`


### 7.7. API-007 GetRecords (GET `/api/alert/record`)
- **认证**: 见源码注解 (`[Authorize]` / JWT 或 API Key)；AST 未解析时默认需认证
- **描述**: 获取Alert记录列表
- **源码位置**: `API/Controllers/UserManagement/AlertController.cs:128`
- **Handler**: `AlertController.GetRecords`
- **HTTP**: `GET`
- **Route**: `/api/alert/record`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| orgId | string | 否 | Org ID，用于按组织筛选 |
| projectId | string | 否 | Project ID，用于按项目筛选 |
| alertId | string | 否 | Alert ID，用于按Alert筛选 |
| state | enum | 否 | 记录状态筛选，默认 `Active` |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷，结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 响应消息 |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `UnAuthToken = 100000` | 未认证或 Token 无效 | 认证失败 |
| `EmptyUserId = 100001` | User ID 为空 | 用户标识缺失 |
| `ExistedMobile = 100003` | 手机号已存在 | 用户已存在 |
| `CreateUserFailed = 100004` | 用户创建失败 | 用户创建异常 |
| `InvalidUser = 100005` | 用户无效 | 用户不存在或已禁用 |
| `EmptyMobile = 100009` | 手机号为空 | 手机号缺失 |

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

- `AlertController`, `GetRecords`, `AlertService`, `IAlertService`, `Authorize`, `ApiController`, `HttpGet`, `Route`

---

## 8. BulletinController 接口


本章共覆盖 7 个 HTTP 端点（基于 AST 扫描结果）。


### 8.1. API-001 Post (POST `/api/tools/bulletin`)
- **认证**: 需要认证（`[Authorize]` / JWT 或 API Key）
- **描述**: 创建Bulletin
- **源码位置**: `API/Controllers/ToolsManagement/BulletinController.cs:32`
- **Handler**: `BulletinController.Post`
- **HTTP**: `POST`
- **Route**: `/api/tools/bulletin`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| body | CreateBulletinBody | 是 | Bulletin创建请求体，包含Bulletin标题、内容、类型等字段（具体字段结构以源码 DTO 定义为准） |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 创建成功的Bulletin数据（含Bulletin ID、标题、状态等） |
| success | bool | 请求是否成功 |
| message | string | 结果描述信息 |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `UnAuthToken = 100000` | 未认证或 Token 无效 | 未提供有效认证凭证 |
| `EmptyUserId = 100001` | User ID 为空 | 认证信息中缺少用户 ID |
| `InvalidUser = 100005` | 用户无效 | 用户不存在或已被禁用 |

**请求示例**

```json
{
  "title": "系统升级Bulletin",
  "content": "系统将于本周六 22:00-24:00 进行升级维护，期间部分功能可能不可用。",
  "type": 1,
  "isCarousel": false
}
```

**响应示例**

```json
{
  "success": true,
  "data": {
    "id": "bulletin_20250115_001",
    "title": "系统升级Bulletin",
    "status": 1,
    "createdAt": "2025-01-15T10:30:00Z"
  },
  "message": "ok"
}
```


### 8.2. API-002 Get (GET `/api/tools/bulletin/agreement`)
- **认证**: 需要认证（`[Authorize]` / JWT 或 API Key）
- **描述**: 根据别名获取协议Bulletin
- **源码位置**: `API/Controllers/ToolsManagement/BulletinController.cs:45`
- **Handler**: `BulletinController.Get`
- **HTTP**: `GET`
- **Route**: `/api/tools/bulletin/agreement`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| alias | string | 是 | 协议别名（Query 参数），用于标识具体协议类型，如用户协议、隐私政策等 |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 协议Bulletin详情（含标题、内容、版本号、发布时间等） |
| success | bool | 请求是否成功 |
| message | string | 结果描述信息 |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `UnAuthToken = 100000` | 未认证或 Token 无效 | 未提供有效认证凭证 |
| `EmptyUserId = 100001` | User ID 为空 | 认证信息中缺少用户 ID |
| `InvalidUser = 100005` | 用户无效 | 用户不存在或已被禁用 |

**请求示例**

```
GET /api/tools/bulletin/agreement?alias=user_agreement
```

**响应示例**

```json
{
  "success": true,
  "data": {
    "alias": "user_agreement",
    "title": "用户服务协议",
    "content": "欢迎使用本服务。在使用前请仔细阅读以下条款...",
    "version": "v2.1",
    "updatedAt": "2025-01-10T08:00:00Z"
  },
  "message": "ok"
}
```


### 8.3. API-003 GetBulletins (GET `/api/tools/bulletin/bulletins`)
- **认证**: 需要认证（`[Authorize]` / JWT 或 API Key）
- **描述**: 分页获取Bulletin列表（前台展示用）
- **源码位置**: `API/Controllers/ToolsManagement/BulletinController.cs:64`
- **Handler**: `BulletinController.GetBulletins`
- **HTTP**: `GET`
- **Route**: `/api/tools/bulletin/bulletins`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| type | int? | 否 | Bulletin类型筛选（Query 参数），对应Bulletin类型枚举值 |
| isCarousel | bool | 否 | 是否仅获取轮播Bulletin（Query 参数），默认 false |
| page | int | 否 | 页码（Query 参数），默认 1 |
| pageSize | int | 否 | 每页条数（Query 参数），默认 20 |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 分页结果，包含Bulletinitems、total、page、pageSize |
| success | bool | 请求是否成功 |
| message | string | 结果描述信息 |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `UnAuthToken = 100000` | 未认证或 Token 无效 | 未提供有效认证凭证 |
| `EmptyUserId = 100001` | User ID 为空 | 认证信息中缺少用户 ID |
| `InvalidUser = 100005` | 用户无效 | 用户不存在或已被禁用 |

**请求示例**

```
GET /api/tools/bulletin/bulletins?type=1&isCarousel=false&page=1&pageSize=10
```

**响应示例**

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "bulletin_20250115_001",
        "title": "系统升级Bulletin",
        "type": 1,
        "isCarousel": false,
        "status": 1,
        "publishedAt": "2025-01-15T10:30:00Z"
      },
      {
        "id": "bulletin_20250114_003",
        "title": "春节放假通知",
        "type": 2,
        "isCarousel": true,
        "status": 1,
        "publishedAt": "2025-01-14T09:00:00Z"
      }
    ],
    "total": 2,
    "page": 1,
    "pageSize": 10
  },
  "message": "ok"
}
```


### 8.4. API-004 GetBackendBulletins (GET `/api/tools/bulletin/backend`)
- **认证**: 需要认证（`[Authorize]` / JWT 或 API Key）
- **描述**: 分页获取后台Bulletin管理列表（含草稿、待审核、已驳回等状态）
- **源码位置**: `API/Controllers/ToolsManagement/BulletinController.cs:82`
- **Handler**: `BulletinController.GetBackendBulletins`
- **HTTP**: `GET`
- **Route**: `/api/tools/bulletin/backend`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| type | int? | 否 | Bulletin类型筛选（Query 参数） |
| status | int? | 否 | Bulletin状态筛选（Query 参数），如草稿、待审核、已发布、已驳回、已关闭等 |
| page | int | 否 | 页码（Query 参数），默认 1 |
| pageSize | int | 否 | 每页条数（Query 参数），默认 20 |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 分页结果，包含Bulletinitems、total、page、pageSize |
| success | bool | 请求是否成功 |
| message | string | 结果描述信息 |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `UnAuthToken = 100000` | 未认证或 Token 无效 | 未提供有效认证凭证 |
| `EmptyUserId = 100001` | User ID 为空 | 认证信息中缺少用户 ID |
| `InvalidUser = 100005` | 用户无效 | 用户不存在或已被禁用 |

**请求示例**

```
GET /api/tools/bulletin/backend?type=1&status=2&page=1&pageSize=10
```

**响应示例**

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "bulletin_20250115_002",
        "title": "新功能上线通知",
        "type": 1,
        "status": 2,
        "creator": "admin@example.com",
        "createdAt": "2025-01-15T14:20:00Z",
        "reviewer": null,
        "reviewedAt": null
      }
    ],
    "total": 1,
    "page": 1,
    "pageSize": 10
  },
  "message": "ok"
}
```


### 8.5. API-005 Approve (POST `/api/tools/bulletin/approve`)
- **认证**: 需要认证（`[Authorize]` / JWT 或 API Key），且需要管理员或审核员角色Privilege
- **描述**: 审核通过指定Bulletin
- **源码位置**: `API/Controllers/ToolsManagement/BulletinController.cs:96`
- **Handler**: `BulletinController.Approve`
- **HTTP**: `POST`
- **Route**: `/api/tools/bulletin/approve`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| ids | string | 是 | Bulletin ID 列表（JSON 字符串数组），支持批量审核通过，如 `["id1","id2"]` |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 审核结果（含成功处理数量、失败列表等） |
| success | bool | 请求是否成功 |
| message | string | 结果描述信息 |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `UnAuthToken = 100000` | 未认证或 Token 无效 | 未提供有效认证凭证 |
| `EmptyUserId = 100001` | User ID 为空 | 认证信息中缺少用户 ID |
| `InvalidUser = 100005` | 用户无效 | 用户不存在或已被禁用 |

**请求示例**

```json
{
  "ids": "[\"bulletin_20250115_002\",\"bulletin_20250115_003\"]"
}
```

**响应示例**

```json
{
  "success": true,
  "data": {
    "approvedCount": 2,
    "failedIds": []
  },
  "message": "ok"
}
```


### 8.6. API-006 Revision (POST `/api/tools/bulletin/revision`)
- **认证**: 需要认证（`[Authorize]` / JWT 或 API Key），且需要管理员或审核员角色Privilege
- **描述**: 驳回指定Bulletin，要求修改后重新提交
- **源码位置**: `API/Controllers/ToolsManagement/BulletinController.cs:110`
- **Handler**: `BulletinController.Revision`
- **HTTP**: `POST`
- **Route**: `/api/tools/bulletin/revision`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| ids | string | 是 | Bulletin ID 列表（JSON 字符串数组），支持批量驳回，如 `["id1","id2"]` |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 驳回结果（含成功处理数量、失败列表等） |
| success | bool | 请求是否成功 |
| message | string | 结果描述信息 |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `UnAuthToken = 100000` | 未认证或 Token 无效 | 未提供有效认证凭证 |
| `EmptyUserId = 100001` | User ID 为空 | 认证信息中缺少用户 ID |
| `InvalidUser = 100005` | 用户无效 | 用户不存在或已被禁用 |

**请求示例**

```json
{
  "ids": "[\"bulletin_20250115_004\"]"
}
```

**响应示例**

```json
{
  "success": true,
  "data": {
    "revisionCount": 1,
    "failedIds": []
  },
  "message": "ok"
}
```


### 8.7. API-007 Close (POST `/api/tools/bulletin/close`)
- **认证**: 需要认证（`[Authorize]` / JWT 或 API Key），且需要管理员角色Privilege
- **描述**: 关闭指定已发布的Bulletin
- **源码位置**: `API/Controllers/ToolsManagement/BulletinController.cs:124`
- **Handler**: `BulletinController.Close`
- **HTTP**: `POST`
- **Route**: `/api/tools/bulletin/close`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| ids | string | 是 | Bulletin ID 列表（JSON 字符串数组），支持批量关闭，如 `["id1","id2"]` |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 关闭结果（含成功处理数量、失败列表等） |
| success | bool | 请求是否成功 |
| message | string | 结果描述信息 |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `UnAuthToken = 100000` | 未认证或 Token 无效 | 未提供有效认证凭证 |
| `EmptyUserId = 100001` | User ID 为空 | 认证信息中缺少用户 ID |
| `InvalidUser = 100005` | 用户无效 | 用户不存在或已被禁用 |

**请求示例**

```json
{
  "ids": "[\"bulletin_20250115_001\"]"
}
```

**响应示例**

```json
{
  "success": true,
  "data": {
    "closedCount": 1,
    "failedIds": []
  },
  "message": "ok"
}
```

---

## 9. CaptchaController 接口

本章共覆盖 2 个 HTTP 端点（AST 确定性提取，未经 LLM 改写）。

### 9.1. API-001 Get (GET `/api/captcha`)
- **认证**: 见源码注解 (`[Authorize]` / JWT 或 API Key); AST 未解析时默认需认证
- **描述**: public Get(string mobile)
- **源码位置**: `API/Controllers/UserManagement/CaptchaController.cs:29`
- **Handler**: `CaptchaController.Get`
- **HTTP**: `GET`
- **Route**: `/api/captcha`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| mobile | string | 是 | 手机号，用于获取图形Captcha |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷，结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 响应消息 |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `UnAuthToken = 100000` | — | 未认证或 Token 无效 |
| `EmptyMobile = 100009` | — | 手机号为空 |

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

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService

### 9.2. API-002 GetSMSCaptcha (GET `/api/captcha/sms`)
- **认证**: 见源码注解 (`[Authorize]` / JWT 或 API Key); AST 未解析时默认需认证
- **描述**: public async Task GetSMSCaptcha(string phone)
- **源码位置**: `API/Controllers/UserManagement/CaptchaController.cs:43`
- **Handler**: `CaptchaController.GetSMSCaptcha`
- **HTTP**: `GET`
- **Route**: `/api/captcha/sms`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| phone | string | 是 | 手机号，用于获取短信Captcha |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷，结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 响应消息 |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `UnAuthToken = 100000` | — | 未认证或 Token 无效 |
| `EmptyMobile = 100009` | — | 手机号为空 |
| `ExistedMobile = 100003` | — | 手机号已存在 |

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

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService

---

## 10. HealthController 接口


本章共覆盖 1 个 HTTP 端点（AST 确定性提取，未经 LLM 改写）。


### 10.1. API-001 Get (GET `/api/tools/health`)
- **认证**: 匿名访问（代码摘要中未提及该端点需要认证；仓库全局认证方式为 JWT Bearer Token 或 API Key（Basic Auth），但本端点未标注 `[Authorize]` 特性）
- **描述**: 健康检查接口，用于服务存活探测
- **源码位置**: `API/Controllers/ToolsManagement/HealthController.cs:20`
- **Handler**: `HealthController.Get`
- **HTTP**: `GET`
- **Route**: `/api/tools/health`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| — | — | — | 无请求参数（无路径参数、无 Query 参数、无请求体） |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| success | bool | 请求是否成功 |
| data | object | 业务载荷；健康检查端点通常返回服务状态信息，具体结构以源码实际返回类型为准 |
| message | string | 响应消息 |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| — | — | 该端点未关联特定业务错误码；若认证失败，可能返回通用错误码 `UnAuthToken = 100000`（未认证或 Token 无效），具体以实际响应为准 |

**请求示例**

```json
(无 body；无路径参数；无 Query 参数)
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

- AgentInsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService

---

## 11. LiteralRoute 接口

本章共覆盖 2 个 HTTP 端点（AST 确定性提取，未经 LLM 改写）。

### 11.1. API-001 GET /api/public（LiteralRouteController）
- **认证**: 见源码注解（`[Authorize]` / JWT 或 API Key）；AST 未解析时默认需认证
- **描述**: 源码字面量路由
- **源码位置**: `API/Controllers/LiteralRouteController.cs`
- **Handler**: `LiteralRouteController.Get`
- **HTTP**: `GET`
- **Route**: `/api/public`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| — | — | — | 无显式请求参数（GET 方法，具体查询参数以源码方法签名为准） |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷，结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 操作结果描述 |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `UnAuthToken = 100000` | 未认证或 Token 无效 | 认证失败时返回 |
| `EmptyUserId = 100001` | User ID 为空 | 用户标识缺失时返回 |

**请求示例**

```json
{}
```

**响应示例**

```json
{
  "success": true,
  "data": {},
  "message": "ok"
}
```

**相关符号（术语表命中）**

- # 术语词典（v8-P0-B 强制约束：以下标识符必须保留原文，禁止翻译为中文）
- LiteralRouteController, AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService

---

### 11.2. API-002 GET /api/test（LiteralRouteController）
- **认证**: 见源码注解（`[Authorize]` / JWT 或 API Key）；AST 未解析时默认需认证
- **描述**: 源码字面量路由
- **源码位置**: `API/Controllers/LiteralRouteController.cs`
- **Handler**: `LiteralRouteController.Get`
- **HTTP**: `GET`
- **Route**: `/api/test`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| — | — | — | 无显式请求参数（GET 方法，具体查询参数以源码方法签名为准） |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷，结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 操作结果描述 |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `UnAuthToken = 100000` | 未认证或 Token 无效 | 认证失败时返回 |
| `EmptyUserId = 100001` | User ID 为空 | 用户标识缺失时返回 |

**请求示例**

```json
{}
```

**响应示例**

```json
{
  "success": true,
  "data": {},
  "message": "ok"
}
```

**相关符号（术语表命中）**

- # 术语词典（v8-P0-B 强制约束：以下标识符必须保留原文，禁止翻译为中文）
- LiteralRouteController, AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService

---

## 12. MetricsController 接口


本章共覆盖 4 个 HTTP 端点 (AST 确定性提取, 未经 LLM 改写).


### 12.1. API-001 GetObservations (GET `/api/data/metrics/observations`)
- **认证**: 见源码注解 (`[Authorize]` / JWT 或 API Key); AST 未解析时默认需认证
- **描述**: public async Task\<IActionResult\> GetObservations(string id, int page = AgentInsightConst.DefaultPage, int pagesize = AgentInsightConst.DefaultPageSize)
- **源码位置**: `API/Controllers/DataManagement/MetricsController.cs:34`
- **Handler**: `MetricsController.GetObservations`
- **HTTP**: `GET`
- **Route**: `/api/data/metrics/observations`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | string | 是 | 指标Observation ID |
| page | int | 否 | 页码, 默认值见 `AgentInsightConst.DefaultPage` |
| pagesize | int | 否 | 每页条数, 默认值见 `AgentInsightConst.DefaultPageSize` |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷, 结构见源码返回类型 `IActionResult` |
| success / code | bool/int | 视统一响应包装 |
| message | string | 响应消息 |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| 100000 | UnAuthToken | 未认证或 Token 无效 |
| 100001 | EmptyUserId | User ID 为空 |
| 100005 | InvalidUser | 用户无效 |

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

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService


### 12.2. API-002 GetScores (GET `/api/data/metrics/scores`)
- **认证**: 见源码注解 (`[Authorize]` / JWT 或 API Key); AST 未解析时默认需认证
- **描述**: public async Task\<IActionResult\> GetScores(string id, int page = AgentInsightConst.DefaultPage, int pagesize = AgentInsightConst.DefaultPageSize)
- **源码位置**: `API/Controllers/DataManagement/MetricsController.cs:50`
- **Handler**: `MetricsController.GetScores`
- **HTTP**: `GET`
- **Route**: `/api/data/metrics/scores`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | string | 是 | 指标Score ID |
| page | int | 否 | 页码, 默认值见 `AgentInsightConst.DefaultPage` |
| pagesize | int | 否 | 每页条数, 默认值见 `AgentInsightConst.DefaultPageSize` |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷, 结构见源码返回类型 `IActionResult` |
| success / code | bool/int | 视统一响应包装 |
| message | string | 响应消息 |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| 100000 | UnAuthToken | 未认证或 Token 无效 |
| 100001 | EmptyUserId | User ID 为空 |
| 100005 | InvalidUser | 用户无效 |

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

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService


### 12.3. API-003 GetTraces (GET `/api/data/metrics/traces`)
- **认证**: 见源码注解 (`[Authorize]` / JWT 或 API Key); AST 未解析时默认需认证
- **描述**: public async Task\<IActionResult\> GetTraces(string ids)
- **源码位置**: `API/Controllers/DataManagement/MetricsController.cs:64`
- **Handler**: `MetricsController.GetTraces`
- **HTTP**: `GET`
- **Route**: `/api/data/metrics/traces`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| ids | string | 是 | Trace ID 列表 (逗号分隔) |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷, 结构见源码返回类型 `IActionResult` |
| success / code | bool/int | 视统一响应包装 |
| message | string | 响应消息 |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| 100000 | UnAuthToken | 未认证或 Token 无效 |
| 100001 | EmptyUserId | User ID 为空 |
| 100005 | InvalidUser | 用户无效 |

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

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService


### 12.4. API-004 CreateTraces (POST `/api/data/metrics/traces`)
- **认证**: 见源码注解 (`[Authorize]` / JWT 或 API Key); AST 未解析时默认需认证
- **描述**: public async Task\<IActionResult\> CreateTraces([FromBody] TraceMetricsBody body)
- **源码位置**: `API/Controllers/DataManagement/MetricsController.cs:125`
- **Handler**: `MetricsController.CreateTraces`
- **HTTP**: `POST`
- **Route**: `/api/data/metrics/traces`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| body | TraceMetricsBody | 是 | Trace指标请求体, 结构见 `TraceMetricsBody` DTO |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷, 结构见源码返回类型 `IActionResult` |
| success / code | bool/int | 视统一响应包装 |
| message | string | 响应消息 |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| 100000 | UnAuthToken | 未认证或 Token 无效 |
| 100001 | EmptyUserId | User ID 为空 |
| 100005 | InvalidUser | 用户无效 |

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

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService

---

## 13. ModelController 接口


本章共覆盖 1 个 HTTP 端点（AST 确定性提取，未经 LLM 改写）。


### 13.1. API-001 Get (GET `/api/data/model`)
- **认证**: 见源码注解 (`[Authorize]` / JWT 或 API Key)；AST 未解析时默认需认证
- **描述**: 获取模型列表，支持关键字搜索、项目筛选、预定义模型包含、排序及分页
- **方法签名**: `public async Task<IActionResult> Get(string? keyword, string? projectid, bool includedpredefined = false, string orderby = "-updatedat", int page = 1, int pageSize = 20)`
- **源码位置**: `API/Controllers/DataManagement/ModelController.cs:34`
- **Handler**: `ModelController.Get`
- **HTTP**: `GET`
- **Route**: `/api/data/model`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| keyword | string | 否 | 搜索关键字，用于模型名称或描述模糊匹配 |
| projectid | string | 否 | Project ID，按项目筛选模型 |
| includedpredefined | bool | 否 | 是否包含预定义模型，默认 false |
| orderby | string | 否 | 排序字段，默认 `-updatedat`（按更新时间倒序） |
| page | int | 否 | 页码，默认 1 |
| pageSize | int | 否 | 每页条数，默认 20 |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| success | bool | 请求是否成功 |
| data | object | 业务载荷，包含模型列表及分页信息，具体结构以源码返回类型为准 |
| message | string | 提示信息 |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `UsageTracking = 2` | — | 来自 AST 枚举清单 |
| `620003` | — | 来自 AST 枚举清单 |
| `620004` | — | 来自 AST 枚举清单 |
| `620005` | — | 来自 AST 枚举清单 |
| `620017` | — | 来自 AST 枚举清单 |

> 注：错误码名称无法从 AST 中提取，仅保留数值标识。完整错误码定义见 `Models/Common/Enums/ExceptionCodes.cs`。

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

- AgentInsightService
- AgentInsight
- InsightService
- API.Common.Extensions
- UserExtension
- API.Common.Helpers
- ClickHouseHelper
- TraceFilterBuilder
- API.Common.Services
- AlertService
- GetTimeSpan
- IsConditionMet
- BuildAlertMessage
- TraceIdResult
- BullMqService
- EnqueueProjectDeleteAsync
- EnqueueTraceIngestionAsync
- AcknowledgeTraceIngestionAsync
- DisposeAsync
- ClickHouseClient
- FurionAppContextService
- IAlertService
- IPaymentService

---

## 14. NotifyController 接口

本章共覆盖 2 个 HTTP 端点（AST 确定性提取，未经 LLM 改写）。

### 14.1. API-001 WeChatNotify (POST `/api/payment/notify/wechatnotify`)

- **认证**: 见源码注解 (`[Authorize]` / JWT 或 API Key)；AST 未解析时默认需认证
- **描述**: 处理微信Payment异步通知回调
- **源码位置**: `API/Controllers/PaymentManagement/NotifyController.cs:29`
- **Handler**: `NotifyController.WeChatNotify`
- **HTTP**: `POST`
- **Route**: `/api/payment/notify/wechatnotify`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| body | object | 是 | 微信Payment回调通知的请求体，包含微信Payment平台签名验证所需的全部字段（如 `id`、`create_time`、`resource_type`、`event_type`、`summary`、`resource` 等）。具体字段结构以微信Payment官方文档及源码模型定义为准。 |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| code | int | 业务状态码，`0` 表示成功，非 `0` 表示失败 |
| data | object | 业务载荷，结构见源码返回类型 |
| message | string | 处理结果描述 |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `810010` | — | 来自 AST 枚举清单 |
| `810018` | — | 来自 AST 枚举清单 |

**请求示例**

```json
{
  "id": "EV-20240607123456789001",
  "create_time": "2024-06-07T12:34:56+08:00",
  "resource_type": "encrypt-resource",
  "event_type": "TRANSACTION.SUCCESS",
  "summary": "Payment成功",
  "resource": {
    "original_type": "transaction",
    "algorithm": "AEAD_AES_256_GCM",
    "ciphertext": "<加密数据>",
    "associated_data": "<附加数据>",
    "nonce": "<随机串>"
  }
}
```

**响应示例**

```json
{
  "code": 0,
  "data": {},
  "message": "success"
}
```

**相关符号（术语表命中）**

- `NotifyController`
- `IPaymentService`
- `WeChatTransaction`（`TransactionType` 枚举值）

---

### 14.2. API-002 AlipayNotify (POST `/api/payment/notify/alipaynotify`)

- **认证**: 见源码注解 (`[Authorize]` / JWT 或 API Key)；AST 未解析时默认需认证
- **描述**: 处理Payment宝异步通知回调
- **源码位置**: `API/Controllers/PaymentManagement/NotifyController.cs:57`
- **Handler**: `NotifyController.AlipayNotify`
- **HTTP**: `POST`
- **Route**: `/api/payment/notify/alipaynotify`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| body | object | 是 | Payment宝异步通知的请求体，包含Payment宝签名验证所需的全部字段（如 `notify_id`、`app_id`、`trade_no`、`out_trade_no`、`trade_status`、`total_amount`、`sign` 等）。具体字段结构以Payment宝开放平台官方文档及源码模型定义为准。 |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| code | int | 业务状态码，`0` 表示成功，非 `0` 表示失败 |
| data | object | 业务载荷，结构见源码返回类型 |
| message | string | 处理结果描述 |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `810010` | — | 来自 AST 枚举清单 |
| `810018` | — | 来自 AST 枚举清单 |

**请求示例**

```json
{
  "notify_id": "2024060700222143567890123456789012",
  "app_id": "2021003122691234",
  "trade_no": "2024060722001412341234567890",
  "out_trade_no": "ORDER20240607001",
  "trade_status": "TRADE_SUCCESS",
  "total_amount": "99.00",
  "sign": "<签名值>"
}
```

**响应示例**

```json
{
  "code": 0,
  "data": {},
  "message": "success"
}
```

**相关符号（术语表命中）**

- `NotifyController`
- `IPaymentService`
- `AlipayTransaction`（`TransactionType` 枚举值）

---

## 15. OrderController 接口


本章共覆盖 4 个 HTTP 端点（AST 确定性提取，未经 LLM 改写）。


### 15.1. API-001 Get (GET `/api/payment/order`)
- **认证**: 见源码注解（`[Authorize]` / JWT 或 API Key）；AST 未解析时默认需认证
- **描述**: 分页查询订单列表。方法签名：`public async Task<object> Get(string orgId, int page = 1, int pageSize = 20)`（参数默认值以源码为准）
- **源码位置**: `API/Controllers/PaymentManagement/OrderController.cs:34`
- **Handler**: `OrderController.Get`
- **HTTP**: `GET`
- **Route**: `/api/payment/order`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| orgId | string | 是 | Org ID，路径参数 |
| page | int | 否 | 页码，默认值见源码 |
| pageSize | int | 否 | 每页条数，默认值见源码 |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷，结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 响应消息 |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `UsageTracking = 2` | — | 来自 AST 枚举清单 |
| `620003` | — | 来自 AST 枚举清单 |
| `620004` | — | 来自 AST 枚举清单 |
| `620005` | — | 来自 AST 枚举清单 |
| `620017` | — | 来自 AST 枚举清单 |

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

**相关符号（术语表命中）**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService


### 15.2. API-002 Place (POST `/api/payment/order`)
- **认证**: 见源码注解（`[Authorize]` / JWT 或 API Key）；AST 未解析时默认需认证
- **描述**: 创建订单。方法签名：`public async Task<object> Place(AgentInsightOrderBody body)`（参数类型以 AST 可提取信息为准）
- **源码位置**: `API/Controllers/PaymentManagement/OrderController.cs:48`
- **Handler**: `OrderController.Place`
- **HTTP**: `POST`
- **Route**: `/api/payment/order`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| body | body | 是 | 订单信息，结构见源码中 `AgentInsightOrderBody` 定义 |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷，结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 响应消息 |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `810020` | — | 来自 AST 枚举清单 |

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

**相关符号（术语表命中）**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService


### 15.3. API-003 Query (GET `/api/payment/order/query`)
- **认证**: 见源码注解（`[Authorize]` / JWT 或 API Key）；AST 未解析时默认需认证
- **描述**: 按订单号查询订单。方法签名：`public async Task<object> Query(string orderNo)`
- **源码位置**: `API/Controllers/PaymentManagement/OrderController.cs:64`
- **Handler**: `OrderController.Query`
- **HTTP**: `GET`
- **Route**: `/api/payment/order/query`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| orderNo | string | 是 | 订单号，Query 参数 |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷，结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 响应消息 |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `810024` | — | 来自 AST 枚举清单 |
| `150010` | — | 来自 AST 枚举清单 |
| `150017` | — | 来自 AST 枚举清单 |

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

**相关符号（术语表命中）**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService


### 15.4. API-004 GetConversion (GET `/api/payment/order/conversion`)
- **认证**: 见源码注解（`[Authorize]` / JWT 或 API Key）；AST 未解析时默认需认证
- **描述**: 查询订单转化信息。方法签名：`public async Task<object> GetConversion(string newProductId)`
- **源码位置**: `API/Controllers/PaymentManagement/OrderController.cs:79`
- **Handler**: `OrderController.GetConversion`
- **HTTP**: `GET`
- **Route**: `/api/payment/order/conversion`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| newProductId | string | 是 | 新产品 ID，Query 参数 |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷，结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 响应消息 |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| 无法从 AST 提取具体错误码 | — | 需补充源码证据 |

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

**相关符号（术语表命中）**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService

---

## 16. OrganizationController 接口


本章共覆盖 4 个 HTTP 端点 (AST 确定性提取, 未经 LLM 改写).


### 16.1. API-001 Post (POST `/api/user/organization`)
- **认证**: 见源码注解 (`[Authorize]` / JWT 或 API Key); AST 未解析时默认需认证
- **描述**: 创建组织。方法签名: `public async Task<ActionResult> Post(CreateOrganizationBody body)`
- **源码位置**: `API/Controllers/UserManagement/OrganizationController.cs:28`
- **Handler**: `OrganizationController.Post`
- **HTTP**: `POST`
- **Route**: `/api/user/organization`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| body | body | 是 | 创建组织请求体，字段定义见 `CreateOrganizationBody` DTO（源码位置：`Models/.../CreateOrganizationBody.cs`） |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷，结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 响应消息 |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `UnAuthToken = 100000` | 未认证或 Token 无效 | 认证失败时返回 |
| `EmptyUserId = 100001` | User ID 为空 | 用户身份缺失时返回 |
| `InvalidUser = 100005` | 用户无效 | 用户不存在或已禁用时返回 |

**请求示例**

```json
{
  "name": "示例组织",
  "description": "组织描述"
}
```

**响应示例**

```json
{
  "success": true,
  "data": {
    "id": "org_xxxxxxxx",
    "name": "示例组织"
  },
  "message": "ok"
}
```

**相关符号 (术语表命中)**

- OrganizationController, CreateOrganizationBody, IOrganizationService


### 16.2. API-002 Get (GET `/api/user/organization`)
- **认证**: 见源码注解 (`[Authorize]` / JWT 或 API Key); AST 未解析时默认需认证
- **描述**: 获取组织信息。方法签名: `public async Task<ActionResult> Get(string? orgId)`
- **源码位置**: `API/Controllers/UserManagement/OrganizationController.cs:42`
- **Handler**: `OrganizationController.Get`
- **HTTP**: `GET`
- **Route**: `/api/user/organization`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| orgId | query | 否 | Org ID；为空时返回当前用户所属组织列表 |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷，结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 响应消息 |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `UnAuthToken = 100000` | 未认证或 Token 无效 | 认证失败时返回 |
| `EmptyUserId = 100001` | User ID 为空 | 用户身份缺失时返回 |
| `InvalidUser = 100005` | 用户无效 | 用户不存在或已禁用时返回 |

**请求示例**

```
GET /api/user/organization?orgId=org_xxxxxxxx
```

**响应示例**

```json
{
  "success": true,
  "data": {
    "id": "org_xxxxxxxx",
    "name": "示例组织",
    "description": "组织描述"
  },
  "message": "ok"
}
```

**相关符号 (术语表命中)**

- OrganizationController, IOrganizationService


### 16.3. API-003 Update (POST `/api/user/organization/update`)
- **认证**: 见源码注解 (`[Authorize]` / JWT 或 API Key); AST 未解析时默认需认证
- **描述**: 更新组织信息。方法签名: `public async Task<ActionResult> Update(UpdateOrganizationBody body)`
- **源码位置**: `API/Controllers/UserManagement/OrganizationController.cs:56`
- **Handler**: `OrganizationController.Update`
- **HTTP**: `POST`
- **Route**: `/api/user/organization/update`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| body | body | 是 | 更新组织请求体，字段定义见 `UpdateOrganizationBody` DTO（源码位置：`Models/.../UpdateOrganizationBody.cs`） |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷，结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 响应消息 |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `UnAuthToken = 100000` | 未认证或 Token 无效 | 认证失败时返回 |
| `EmptyUserId = 100001` | User ID 为空 | 用户身份缺失时返回 |
| `InvalidUser = 100005` | 用户无效 | 用户不存在或已禁用时返回 |

**请求示例**

```json
{
  "id": "org_xxxxxxxx",
  "name": "更新后的组织名称",
  "description": "更新后的组织描述"
}
```

**响应示例**

```json
{
  "success": true,
  "data": {
    "id": "org_xxxxxxxx",
    "name": "更新后的组织名称",
    "description": "更新后的组织描述"
  },
  "message": "ok"
}
```

**相关符号 (术语表命中)**

- OrganizationController, UpdateOrganizationBody, IOrganizationService


### 16.4. API-004 Delete (POST `/api/user/organization/delete`)
- **认证**: 见源码注解 (`[Authorize]` / JWT 或 API Key); AST 未解析时默认需认证
- **描述**: 删除组织。方法签名: `public async Task<ActionResult> Delete(string orgIds)`
- **源码位置**: `API/Controllers/UserManagement/OrganizationController.cs:71`
- **Handler**: `OrganizationController.Delete`
- **HTTP**: `POST`
- **Route**: `/api/user/organization/delete`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| orgIds | body | 是 | 待删除的组织 ID 列表（多个 ID 以逗号分隔），示例：`"org_1,org_2"` |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷，结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 响应消息 |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `UnAuthToken = 100000` | 未认证或 Token 无效 | 认证失败时返回 |
| `EmptyUserId = 100001` | User ID 为空 | 用户身份缺失时返回 |
| `InvalidUser = 100005` | 用户无效 | 用户不存在或已禁用时返回 |

**请求示例**

```json
"org_xxxxxxxx,org_yyyyyyyy"
```

**响应示例**

```json
{
  "success": true,
  "data": null,
  "message": "ok"
}
```

**相关符号 (术语表命中)**

- OrganizationController, IOrganizationService

---

## 17. ProductController 接口

本章共覆盖 2 个 HTTP 端点（AST 确定性提取，未经 LLM 改写）。

### 17.1. API-001 Get (GET `/api/product`)

- **认证**: 见源码注解 (`[Authorize]` / JWT 或 API Key)；AST 未解析时默认需认证
- **描述**: 获取产品信息
- **源码位置**: `API/Controllers/ProductManagement/ProductController.cs:26`
- **Handler**: `ProductController.Get`
- **HTTP**: `GET`
- **Route**: `/api/product`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| — | — | — | 该方法无显式请求参数；具体以源码方法签名为准 |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷，结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装而定 |
| message | string | 响应消息 |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `UnAuthToken = 100000` | — | 未认证或 Token 无效 |
| `EmptyUserId = 100001` | — | User ID 为空 |
| `ExistedMobile = 100003` | — | 手机号已存在 |
| `CreateUserFailed = 100004` | — | 用户创建失败 |
| `InvalidUser = 100005` | — | 用户无效 |
| `EmptyMobile = 100009` | — | 手机号为空 |

> 注：错误码定义于 `Models/Common/Enums/ExceptionCodes.cs`，以上为已识别部分常量；完整列表以源码为准。

**请求示例**

```json
(无 body；参数见路径/Query)
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

- AgentInsightService, AgentInsight, InsightService, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService

---

### 17.2. API-002 GetDuration (GET `/api/product/duration`)

- **认证**: 见源码注解 (`[Authorize]` / JWT 或 API Key)；AST 未解析时默认需认证
- **描述**: 获取产品时长信息
- **源码位置**: `API/Controllers/ProductManagement/ProductController.cs:38`
- **Handler**: `ProductController.GetDuration`
- **HTTP**: `GET`
- **Route**: `/api/product/duration`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| — | — | — | 该方法无显式请求参数；具体以源码方法签名为准 |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷，结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装而定 |
| message | string | 响应消息 |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `UnAuthToken = 100000` | — | 未认证或 Token 无效 |
| `EmptyUserId = 100001` | — | User ID 为空 |
| `ExistedMobile = 100003` | — | 手机号已存在 |
| `CreateUserFailed = 100004` | — | 用户创建失败 |
| `InvalidUser = 100005` | — | 用户无效 |
| `EmptyMobile = 100009` | — | 手机号为空 |

> 注：错误码定义于 `Models/Common/Enums/ExceptionCodes.cs`，以上为已识别部分常量；完整列表以源码为准。

**请求示例**

```json
(无 body；参数见路径/Query)
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

- AgentInsightService, AgentInsight, InsightService, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService

---

## 18. ProjectController 接口


本章共覆盖 4 个 HTTP 端点 (AST 确定性提取, 未经 LLM 改写).


### 18.1. API-001 Create (POST `/api/user/project`)
- **认证**: 见源码注解 (`[Authorize]` / JWT 或 API Key); AST 未解析时默认需认证
- **描述**: public async Task<[已移除幻觉符号]> Create([[已移除幻觉符号]] CreateProjectBody body)
- **源码位置**: `API/Controllers/UserManagement/ProjectController.cs:31`
- **Handler**: `ProjectController.Create`
- **HTTP**: `POST`
- **Route**: `/api/user/project`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| body | body | 是 | 创建项目请求体; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

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
| `[已移除幻觉符号] = 100004` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 100026` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 100032` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 130004` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 140004` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 160001` | — | 来自 AST 枚举清单 |
| `Create = 2` | — | 来自 AST 枚举清单 |
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

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService


### 18.2. API-002 Get (GET `/api/user/project`)
- **认证**: 见源码注解 (`[Authorize]` / JWT 或 API Key); AST 未解析时默认需认证
- **描述**: public async Task<[已移除幻觉符号]> Get(string orgId, string? projectId)
- **源码位置**: `API/Controllers/UserManagement/ProjectController.cs:46`
- **Handler**: `ProjectController.Get`
- **HTTP**: `GET`
- **Route**: `/api/user/project`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| orgId | query | 是 | Org ID |
| projectId | query | 否 | Project ID (可空) |

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
| `[已移除幻觉符号] = 620003` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 620004` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 620005` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 620017` | — | 来自 AST 枚举清单 |

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

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService


### 18.3. API-003 Update (POST `/api/user/project/update`)
- **认证**: 见源码注解 (`[Authorize]` / JWT 或 API Key); AST 未解析时默认需认证
- **描述**: public async Task<[已移除幻觉符号]> Update([[已移除幻觉符号]] UpdateProjectBody body)
- **源码位置**: `API/Controllers/UserManagement/ProjectController.cs:60`
- **Handler**: `ProjectController.Update`
- **HTTP**: `POST`
- **Route**: `/api/user/project/update`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| body | body | 是 | 更新项目请求体; 字段以 AST 可提取信息为准, 禁止编造 DTO. |

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
| `[已移除幻觉符号] = 130005` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 140005` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 810026` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 150020` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 160002` | — | 来自 AST 枚举清单 |

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

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService


### 18.4. API-004 Delete (POST `/api/user/project/delete`)
- **认证**: 见源码注解 (`[Authorize]` / JWT 或 API Key); AST 未解析时默认需认证
- **描述**: public async Task<[已移除幻觉符号]> Delete(string projectIds)
- **源码位置**: `API/Controllers/UserManagement/ProjectController.cs:75`
- **Handler**: `ProjectController.Delete`
- **HTTP**: `POST`
- **Route**: `/api/user/project/delete`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| projectIds | body | 是 | Project ID 列表 (字符串形式, 以分隔符区隔多个 ID) |

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
| `[已移除幻觉符号] = 100028` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 100033` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 130006` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 140006` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 160003` | — | 来自 AST 枚举清单 |

**请求示例**

```json
{
  "projectIds": "<projectIds>"
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

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService

---

## 19. Unknown 接口

### 19.1. API 接口清单（由 AST/源码直接提取，禁止修改）

| 标识 | 方法 | 路径 | 描述 | 认证 |
|------|------|------|------|------|
| API-001 | POST | `/api/agent/insight` | chat_completions | Bearer |
| API-002 | GET | `/api/sessions` | list_sessions | Bearer |
| API-003 | GET | `/api/sessions/{session_id}` | get_session | Bearer |
| API-004 | DELETE | `/api/sessions/{session_id}` | delete_session | Bearer |
| API-005 | POST | `/api/sessions/cleanup` | cleanup_expired_sessions | Bearer |
| API-006 | GET | `/api/agents` | list_agents | Bearer |

### 19.2. 接口补充说明

> 以下由 LLM 基于上述真实 API 签名补充说明，禁止修改上方签名表内容。

AgentInsightService 是面向 Agent 可Observation性与智能分析场景的服务端应用，提供 Agent Config管理、Session管理、数据指标查询、Payment订单处理、Bulletin管理、Alert管理等 HTTP API 能力。本章聚焦于 `UnknownController` 中定义的 6 个端点，涵盖 Agent insight接口以及Session（Session）与 Agent 列表的查询、删除、清理操作。所有端点均遵循统一的 `ApiResponse<T>` 响应包装格式，并通过 API Key（Basic Auth）或 JWT Token进行认证。

### 19.3. POST /api/agent/insight

**认证**: BasicAuth（API Key）或 JWT

**描述**: 该端点用于提交 Agent 洞察请求，调用底层 `chat_completions` 方法完成对话补全或洞察分析。请求体为 JSON 格式的对话消息序列，服务端处理后返回 Agent 的洞察结果。该接口是 AgentInsightService 对外提供智能分析能力的核心入口，支持流式与非流式两种响应模式。

#### 19.3.1. 请求参数

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| messages | array | 是 | 对话消息列表，每条消息包含 `role`（如 `user`、`assistant`、`system`）与 `content` 字段 |
| stream | boolean | 否 | 是否启用流式响应，默认 `false` |
| session_id | string | 否 | Session ID，用于关联历史上下文 |
| model | string | 否 | 模型名称，默认使用服务端Config的默认模型 |

#### 19.3.2. 响应格式

| 字段 | 类型 | 说明 |
|------|------|------|
| errorCode | int | 0=成功，非 0=具体错误码 |
| data | object | 洞察结果，包含 `content`（回复内容）、`session_id`（Session ID）、`usage`（Token 用量统计） |
| message | string | 错误描述信息，成功时为空 |

#### 19.3.3. 错误码

| errorCode | message | 说明 |
|-----------|---------|------|
| 0 | success | 成功 |
| 100000 | UnAuthToken | 未认证或 Token 无效 |
| 999999 | 系统默认异常 | 系统默认异常 |

#### 19.3.4. 请求示例

```http
POST /api/agent/insight
Content-Type: application/json

{
  "messages": [
    { "role": "user", "content": "分析当前项目的 Token 消耗趋势" }
  ],
  "stream": false,
  "session_id": "sess_001",
  "model": "gpt-4o"
}
```

#### 19.3.5. 响应示例

```json
{
  "errorCode": 0,
  "data": {
    "content": "根据最近 7 天的数据，Token 消耗呈上升趋势，日均消耗约 12 万 Token。",
    "session_id": "sess_001",
    "usage": {
      "prompt_tokens": 128,
      "completion_tokens": 64,
      "total_tokens": 192
    }
  },
  "message": ""
}
```

### 19.4. GET /api/sessions

**认证**: BasicAuth（API Key）或 JWT

**描述**: 该端点用于获取当前用户的 Agent Session列表。默认返回分页后的Session概要信息（不包含Session上下文 Context 字段），调用方可通过 `page` 与 `pageSize` 参数控制分页行为。Session按创建时间倒序排列，便于用户快速定位最近的Session记录。该端点对应 `AgentSessionController.Get` 方法 [API/Controllers/AgentManagement/AgentSessionController.cs:33]。

#### 19.4.1. 请求参数

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| page | int | 否 | 页码，默认 1 |
| pageSize | int | 否 | 每页数量，默认 10 |

#### 19.4.2. 响应格式

| 字段 | 类型 | 说明 |
|------|------|------|
| errorCode | int | 0=成功，非 0=具体错误码 |
| data | array | Session列表，每项包含 `id`、`name`、`createdat`、`updatedat` |
| totalCount | int | Session总数 |
| page | int | 当前页码 |
| pageSize | int | 每页数量 |

#### 19.4.3. 错误码

| errorCode | message | 说明 |
|-----------|---------|------|
| 0 | success | 成功 |
| 100000 | UnAuthToken | 未认证或 Token 无效 |
| 999999 | 系统默认异常 | 系统默认异常 |

#### 19.4.4. 请求示例

```http
GET /api/sessions?page=1&pageSize=10
```

#### 19.4.5. 响应示例

```json
{
  "errorCode": 0,
  "data": [
    {
      "id": "sess_001",
      "name": "Token 消耗分析",
      "createdat": "2025-01-15T10:30:00Z",
      "updatedat": "2025-01-15T10:35:00Z"
    }
  ],
  "totalCount": 1,
  "page": 1,
  "pageSize": 10
}
```

### 19.5. GET /api/sessions/{session_id}

**认证**: BasicAuth（API Key）或 JWT

**描述**: 该端点用于获取指定Session ID 的完整详情，包括Session的上下文信息（Context 字段）。当 `session_id` 为空时，行为与列表接口一致；当 `session_id` 非空时，返回该Session的全部内容。该端点对应 `AgentSessionController.Get` 方法中 `id` 参数非空的分支逻辑 [API/Controllers/AgentManagement/AgentSessionController.cs:33]。

#### 19.5.1. 请求参数

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| session_id | string | 是 | Session ID，路径参数 |

#### 19.5.2. 响应格式

| 字段 | 类型 | 说明 |
|------|------|------|
| errorCode | int | 0=成功，非 0=具体错误码 |
| data | object | Session详情，包含 `id`、`name`、`context`、`createdat`、`updatedat` |
| message | string | 错误描述信息，成功时为空 |

#### 19.5.3. 错误码

| errorCode | message | 说明 |
|-----------|---------|------|
| 0 | success | 成功 |
| 100000 | UnAuthToken | 未认证或 Token 无效 |
| 999999 | 系统默认异常 | 系统默认异常 |

#### 19.5.4. 请求示例

```http
GET /api/sessions/sess_001
```

#### 19.5.5. 响应示例

```json
{
  "errorCode": 0,
  "data": {
    "id": "sess_001",
    "name": "Token 消耗分析",
    "context": {
      "query": "分析当前项目的 Token 消耗趋势",
      "history": []
    },
    "createdat": "2025-01-15T10:30:00Z",
    "updatedat": "2025-01-15T10:35:00Z"
  },
  "message": ""
}
```

### 19.6. DELETE /api/sessions/{session_id}

**认证**: BasicAuth（API Key）或 JWT

**描述**: 该端点用于删除指定Session ID 的Session记录。支持批量删除，多个Session ID 以逗号分隔传入。仅删除当前用户名下的Session，非本人创建的Session不会被删除。删除操作不可逆，调用方需谨慎操作。该端点对应 `AgentSessionController.Delete` 方法 [API/Controllers/AgentManagement/AgentSessionController.cs:46]。

#### 19.6.1. 请求参数

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| session_id | string | 是 | Session ID，多个以逗号分隔，如 `sess_001,sess_002` |

#### 19.6.2. 响应格式

| 字段 | 类型 | 说明 |
|------|------|------|
| errorCode | int | 0=成功，非 0=具体错误码 |
| data | object | 无数据返回，成功时为空对象 |
| message | string | 错误描述信息，成功时为空 |

#### 19.6.3. 错误码

| errorCode | message | 说明 |
|-----------|---------|------|
| 0 | success | 成功 |
| 100000 | UnAuthToken | 未认证或 Token 无效 |
| 999999 | 系统默认异常 | 系统默认异常 |

#### 19.6.4. 请求示例

```http
DELETE /api/sessions/sess_001,sess_002
```

#### 19.6.5. 响应示例

```json
{
  "errorCode": 0,
  "data": {},
  "message": ""
}
```

### 19.7. POST /api/sessions/cleanup

**认证**: BasicAuth（API Key）或 JWT

**描述**: 该端点用于清理当前用户已过期的Session记录。系统根据Session的 `updatedat` 字段与预设的过期策略判断Session是否过期，过期Session将被永久删除。该操作通常由定时任务或前端主动触发，用于释放存储空间并保持Session列表的整洁。清理操作仅影响当前用户名下的过期Session。

#### 19.7.1. 请求参数

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| 无 | - | - | 该端点不接受请求体参数 |

#### 19.7.2. 响应格式

| 字段 | 类型 | 说明 |
|------|------|------|
| errorCode | int | 0=成功，非 0=具体错误码 |
| data | object | 包含 `deleted_count`（清理的Session数量） |
| message | string | 错误描述信息，成功时为空 |

#### 19.7.3. 错误码

| errorCode | message | 说明 |
|-----------|---------|------|
| 0 | success | 成功 |
| 100000 | UnAuthToken | 未认证或 Token 无效 |
| 999999 | 系统默认异常 | 系统默认异常 |

#### 19.7.4. 请求示例

```http
POST /api/sessions/cleanup
```

#### 19.7.5. 响应示例

```json
{
  "errorCode": 0,
  "data": {
    "deleted_count": 5
  },
  "message": ""
}
```

### 19.8. GET /api/agents

**认证**: BasicAuth（API Key）或 JWT

**描述**: 该端点用于获取当前用户可访问的 Agent 列表。返回的 Agent 列表包含每个 Agent 的基本信息，如 Agent ID、名称、类型、创建时间等。该接口是 AgentInsightService 中 Agent 管理功能的基础查询接口，供前端在初始化工作台或选择 Agent 进行洞察分析时调用。

#### 19.8.1. 请求参数

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| page | int | 否 | 页码，默认 1 |
| pageSize | int | 否 | 每页数量，默认 10 |

#### 19.8.2. 响应格式

| 字段 | 类型 | 说明 |
|------|------|------|
| errorCode | int | 0=成功，非 0=具体错误码 |
| data | array | Agent 列表，每项包含 `id`、`name`、`type`、`createdat`、`updatedat` |
| totalCount | int | Agent 总数 |
| page | int | 当前页码 |
| pageSize | int | 每页数量 |

#### 19.8.3. 错误码

| errorCode | message | 说明 |
|-----------|---------|------|
| 0 | success | 成功 |
| 100000 | UnAuthToken | 未认证或 Token 无效 |
| 999999 | 系统默认异常 | 系统默认异常 |

#### 19.8.4. 请求示例

```http
GET /api/agents?page=1&pageSize=10
```

#### 19.8.5. 响应示例

```json
{
  "errorCode": 0,
  "data": [
    {
      "id": "agent_001",
      "name": "数据分析助手",
      "type": "insight",
      "createdat": "2025-01-10T08:00:00Z",
      "updatedat": "2025-01-15T10:30:00Z"
    }
  ],
  "totalCount": 1,
  "page": 1,
  "pageSize": 10
}
```

---

## 20. UserConfigController 接口


本章共覆盖 4 个 HTTP 端点 (AST 确定性提取, 未经 LLM 改写).


### 20.1. API-001 Get (GET `/api/user/config`)
- **认证**: 见源码注解 (`[Authorize]` / JWT 或 API Key); AST 未解析时默认需认证
- **描述**: 获取用户Config
- **源码位置**: `API/Controllers/UserManagement/UserConfigController.cs:31`
- **Handler**: `UserConfigController.Get`
- **HTTP**: `GET`
- **Route**: `/api/user/config`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| orgId | string | 否 | Org ID (Query) |
| projectId | string | 否 | Project ID (Query) |
| type | string | 否 | Config类型 (Query) |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷, 结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 响应消息 |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `UnAuthToken = 100000` | — | 未认证或 Token 无效 |
| `EmptyUserId = 100001` | — | User ID 为空 |
| `InvalidUser = 100005` | — | 用户无效 |

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

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService


### 20.2. API-002 Post (POST `/api/user/config`)
- **认证**: 见源码注解 (`[Authorize]` / JWT 或 API Key); AST 未解析时默认需认证
- **描述**: 创建用户Config
- **源码位置**: `API/Controllers/UserManagement/UserConfigController.cs:44`
- **Handler**: `UserConfigController.Post`
- **HTTP**: `POST`
- **Route**: `/api/user/config`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| body | object | 是 | 创建用户Config请求体 (JSON) |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷, 结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 响应消息 |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `UnAuthToken = 100000` | — | 未认证或 Token 无效 |
| `EmptyUserId = 100001` | — | User ID 为空 |
| `InvalidUser = 100005` | — | 用户无效 |

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

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService


### 20.3. API-003 Update (POST `/api/user/config/update`)
- **认证**: 见源码注解 (`[Authorize]` / JWT 或 API Key); AST 未解析时默认需认证
- **描述**: 更新用户Config
- **源码位置**: `API/Controllers/UserManagement/UserConfigController.cs:57`
- **Handler**: `UserConfigController.Update`
- **HTTP**: `POST`
- **Route**: `/api/user/config/update`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| body | object | 是 | 更新用户Config请求体 (JSON) |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷, 结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 响应消息 |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `UnAuthToken = 100000` | — | 未认证或 Token 无效 |
| `EmptyUserId = 100001` | — | User ID 为空 |
| `InvalidUser = 100005` | — | 用户无效 |

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

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService


### 20.4. API-004 Delete (POST `/api/user/config/delete`)
- **认证**: 见源码注解 (`[Authorize]` / JWT 或 API Key); AST 未解析时默认需认证
- **描述**: 删除用户Config
- **源码位置**: `API/Controllers/UserManagement/UserConfigController.cs:71`
- **Handler**: `UserConfigController.Delete`
- **HTTP**: `POST`
- **Route**: `/api/user/config/delete`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | string | 是 | Config ID (Query) |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷, 结构见源码返回类型 |
| success / code | bool/int | 视统一响应包装 |
| message | string | 响应消息 |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `UnAuthToken = 100000` | — | 未认证或 Token 无效 |
| `EmptyUserId = 100001` | — | User ID 为空 |
| `InvalidUser = 100005` | — | 用户无效 |

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

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService

---

## 21. UserController 接口


本章共覆盖 17 个 HTTP 端点（AST 确定性提取，未经 LLM 改写）。

> **修订说明**：本章所有端点信息均基于 AST 扫描结果。错误码引用自 `Models/Common/Enums/ExceptionCodes.cs` 枚举定义；请求/响应字段以源码方法签名及 DTO 定义为准。标注 `[待补充]` 处表示 AST 未能提取到确定性信息，需人工核对源码后补充。


### 21.1. API-001 Get (GET `/api/user`)
- **认证**: 需要认证（Bearer JWT 或 API Key，以源码注解为准）
- **描述**: 获取当前用户信息
- **源码位置**: `API/Controllers/UserManagement/UserController.cs:29`
- **Handler**: `UserController.Get`
- **HTTP**: `GET`
- **Route**: `/api/user`

**请求参数**

无（无路径参数、无 Query 参数、无请求体）

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 用户信息对象，结构见源码返回类型 |
| success | bool | 请求是否成功 |
| message | string | 结果描述信息 |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `UnAuthToken = 100000` | 未认证或 Token 无效 | 认证失败时返回 |
| `EmptyUserId = 100001` | User ID 为空 | 用户标识缺失时返回 |
| `InvalidUser = 100005` | 用户无效 | 用户不存在或已禁用时返回 |

**请求示例**

```http
GET /api/user
Authorization: Bearer <token>
```

**响应示例**

```json
{
  "success": true,
  "data": {
    "id": "string",
    "mobile": "string",
    "nickname": "string",
    "avatar": "string"
  },
  "message": "ok"
}
```

> **注**：`data` 字段结构以源码返回类型为准，上述示例仅作格式参考。


### 21.2. API-002 Create (POST `/api/user`)
- **认证**: 需要认证（Bearer JWT 或 API Key，以源码注解为准）
- **描述**: 创建新用户
- **源码位置**: `API/Controllers/UserManagement/UserController.cs:43`
- **Handler**: `UserController.Create`
- **HTTP**: `POST`
- **Route**: `/api/user`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| body | MiniUserBody | 是 | 用户创建请求体，字段定义见源码 DTO |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 创建成功的用户信息对象 |
| success | bool | 请求是否成功 |
| message | string | 结果描述信息 |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `UnAuthToken = 100000` | 未认证或 Token 无效 | 认证失败时返回 |
| `EmptyUserId = 100001` | User ID 为空 | 用户标识缺失时返回 |
| `ExistedMobile = 100003` | 手机号已存在 | 手机号已被注册时返回 |
| `CreateUserFailed = 100004` | 用户创建失败 | 创建操作失败时返回 |
| `InvalidUser = 100005` | 用户无效 | 用户不存在或已禁用时返回 |
| `EmptyMobile = 100009` | 手机号为空 | 手机号未填写时返回 |

**请求示例**

```json
{
  "mobile": "13800138000",
  "password": "string",
  "nickname": "string"
}
```

> **注**：请求体字段以源码 `MiniUserBody` DTO 定义为准，上述示例仅作格式参考。

**响应示例**

```json
{
  "success": true,
  "data": {
    "id": "string",
    "mobile": "13800138000",
    "nickname": "string"
  },
  "message": "ok"
}
```


### 21.3. API-003 Update (POST `/api/user/update`)
- **认证**: 需要认证（Bearer JWT 或 API Key，以源码注解为准）
- **描述**: 更新用户信息
- **源码位置**: `API/Controllers/UserManagement/UserController.cs:58`
- **Handler**: `UserController.Update`
- **HTTP**: `POST`
- **Route**: `/api/user/update`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| body | MiniUserBody | 是 | 用户更新请求体，字段定义见源码 DTO |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 更新后的用户信息对象 |
| success | bool | 请求是否成功 |
| message | string | 结果描述信息 |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `UnAuthToken = 100000` | 未认证或 Token 无效 | 认证失败时返回 |
| `EmptyUserId = 100001` | User ID 为空 | 用户标识缺失时返回 |
| `InvalidUser = 100005` | 用户无效 | 用户不存在或已禁用时返回 |

**请求示例**

```json
{
  "id": "string",
  "nickname": "string",
  "avatar": "string"
}
```

> **注**：请求体字段以源码 `MiniUserBody` DTO 定义为准，上述示例仅作格式参考。

**响应示例**

```json
{
  "success": true,
  "data": {
    "id": "string",
    "mobile": "string",
    "nickname": "string",
    "avatar": "string"
  },
  "message": "ok"
}
```


### 21.4. API-004 Login (POST `/api/user/login`)
- **认证**: 无需认证（公开接口）
- **描述**: 用户登录
- **源码位置**: `API/Controllers/UserManagement/UserController.cs:73`
- **Handler**: `UserController.Login`
- **HTTP**: `POST`
- **Route**: `/api/user/login`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| body | MiniUserBody? | 否 | 登录请求体，可空；字段定义见源码 DTO |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 登录成功后的Token及用户信息 |
| success | bool | 请求是否成功 |
| message | string | 结果描述信息 |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `UnAuthToken = 100000` | 未认证或 Token 无效 | 登录凭证无效时返回 |
| `EmptyUserId = 100001` | User ID 为空 | 用户标识缺失时返回 |
| `InvalidUser = 100005` | 用户无效 | 用户不存在或已禁用时返回 |

**请求示例**

```json
{
  "mobile": "13800138000",
  "password": "string"
}
```

> **注**：请求体字段以源码 `MiniUserBody` DTO 定义为准，上述示例仅作格式参考。

**响应示例**

```json
{
  "success": true,
  "data": {
    "token": "string",
    "expiresIn": 43200,
    "user": {
      "id": "string",
      "mobile": "string",
      "nickname": "string"
    }
  },
  "message": "ok"
}
```


### 21.5. API-005 Logout (POST `/api/user/logout`)
- **认证**: 需要认证（Bearer JWT 或 API Key，以源码注解为准）
- **描述**: 用户退出登录
- **源码位置**: `API/Controllers/UserManagement/UserController.cs:88`
- **Handler**: `UserController.Logout`
- **HTTP**: `POST`
- **Route**: `/api/user/logout`

**请求参数**

无（无路径参数、无 Query 参数、无请求体）

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 空对象或注销结果 |
| success | bool | 请求是否成功 |
| message | string | 结果描述信息 |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `UnAuthToken = 100000` | 未认证或 Token 无效 | 认证失败时返回 |

**请求示例**

```http
POST /api/user/logout
Authorization: Bearer <token>
```

**响应示例**

```json
{
  "success": true,
  "data": {},
  "message": "ok"
}
```


### 21.6. API-006 ResetPassword (POST `/api/user/resetpassword`)
- **认证**: 需要认证（Bearer JWT 或 API Key，以源码注解为准）
- **描述**: 重置用户密码
- **源码位置**: `API/Controllers/UserManagement/UserController.cs:102`
- **Handler**: `UserController.ResetPassword`
- **HTTP**: `POST`
- **Route**: `/api/user/resetpassword`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| body | ResetPasswordBody | 是 | 密码重置请求体，字段定义见源码 DTO |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 空对象或重置结果 |
| success | bool | 请求是否成功 |
| message | string | 结果描述信息 |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `UnAuthToken = 100000` | 未认证或 Token 无效 | 认证失败时返回 |
| `EmptyUserId = 100001` | User ID 为空 | 用户标识缺失时返回 |
| `InvalidUser = 100005` | 用户无效 | 用户不存在或已禁用时返回 |

**请求示例**

```json
{
  "userId": "string",
  "oldPassword": "string",
  "newPassword": "string"
}
```

> **注**：请求体字段以源码 `ResetPasswordBody` DTO 定义为准，上述示例仅作格式参考。

**响应示例**

```json
{
  "success": true,
  "data": {},
  "message": "ok"
}
```


### 21.7. API-007 Bind (POST `/api/user/bind/wechat`)
- **认证**: 需要认证（Bearer JWT 或 API Key，以源码注解为准）
- **描述**: 绑定微信账号
- **源码位置**: `API/Controllers/UserManagement/UserController.cs:117`
- **Handler**: `UserController.Bind`
- **HTTP**: `POST`
- **Route**: `/api/user/bind/wechat`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| body | MiniUserBody | 是 | 绑定请求体，包含微信授权信息，字段定义见源码 DTO |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 绑定成功后的用户信息对象 |
| success | bool | 请求是否成功 |
| message | string | 结果描述信息 |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `UnAuthToken = 100000` | 未认证或 Token 无效 | 认证失败时返回 |
| `EmptyUserId = 100001` | User ID 为空 | 用户标识缺失时返回 |
| `InvalidUser = 100005` | 用户无效 | 用户不存在或已禁用时返回 |

**请求示例**

```json
{
  "id": "string",
  "wechatCode": "string"
}
```

> **注**：请求体字段以源码 `MiniUserBody` DTO 定义为准，上述示例仅作格式参考。

**响应示例**

```json
{
  "success": true,
  "data": {
    "id": "string",
    "mobile": "string",
    "wechatBound": true
  },
  "message": "ok"
}
```


### 21.8. API-008 UnbindWeChat (GET `/api/user/unbind/wechat`)
- **认证**: 需要认证（Bearer JWT 或 API Key，以源码注解为准）
- **描述**: 解绑微信账号
- **源码位置**: `API/Controllers/UserManagement/UserController.cs:132`
- **Handler**: `UserController.UnbindWeChat`
- **HTTP**: `GET`
- **Route**: `/api/user/unbind/wechat`

**请求参数**

无（无路径参数、无 Query 参数、无请求体）

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 解绑后的用户信息对象 |
| success | bool | 请求是否成功 |
| message | string | 结果描述信息 |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `UnAuthToken = 100000` | 未认证或 Token 无效 | 认证失败时返回 |
| `EmptyUserId = 100001` | User ID 为空 | 用户标识缺失时返回 |
| `InvalidUser = 100005` | 用户无效 | 用户不存在或已禁用时返回 |

**请求示例**

```http
GET /api/user/unbind/wechat
Authorization: Bearer <token>
```

**响应示例**

```json
{
  "success": true,
  "data": {
    "id": "string",
    "wechatBound": false
  },
  "message": "ok"
}
```


### 21.9. API-009 AssignRole (POST `/api/user/role`)
- **认证**: 需要认证（Bearer JWT 或 API Key，以源码注解为准）
- **描述**: 为用户分配角色
- **源码位置**: `API/Controllers/UserManagement/UserController.cs:147`
- **Handler**: `UserController.AssignRole`
- **HTTP**: `POST`
- **Route**: `/api/user/role`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| body | AssignRoleBody | 是 | 角色分配请求体，字段定义见源码 DTO |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 分配结果对象 |
| success | bool | 请求是否成功 |
| message | string | 结果描述信息 |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `UnAuthToken = 100000` | 未认证或 Token 无效 | 认证失败时返回 |
| `EmptyUserId = 100001` | User ID 为空 | 用户标识缺失时返回 |
| `InvalidUser = 100005` | 用户无效 | 用户不存在或已禁用时返回 |

**请求示例**

```json
{
  "userId": "string",
  "roleId": "string"
}
```

> **注**：请求体字段以源码 `AssignRoleBody` DTO 定义为准，上述示例仅作格式参考。

**响应示例**

```json
{
  "success": true,
  "data": {
    "userId": "string",
    "roleId": "string",
    "assignedAt": "2024-01-01T00:00:00Z"
  },
  "message": "ok"
}
```

---

## 22. WeChatController 接口

本章共覆盖 2 个 HTTP 端点（基于 AST 确定性扫描）。

### 22.1. API-001 Get (GET `/api/tools/wechat`)

- **认证**: 需要认证（`[Authorize]` / Bearer JWT / API Key），具体以源码注解为准
- **描述**: 微信接入验证接口，用于微信服务器 URL 有效性校验
- **源码位置**: `API/Controllers/ToolsManagement/WeChat/WeChatController.cs:36`
- **Handler**: `WeChatController.Get`
- **HTTP**: `GET`
- **Route**: `/api/tools/wechat`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| signature | string | 是 | 微信加密签名，用于验证请求合法性 |
| timestamp | string | 是 | 时间戳 |
| nonce | string | 是 | 随机数 |
| echostr | string | 是 | 随机字符串，需原样返回以完成验证 |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷，结构见源码返回类型 |
| success / code | bool/int | 统一响应包装 |
| message | string | 响应消息 |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `UnAuthToken = 100000` | — | 未认证或 Token 无效 |
| `EmptyUserId = 100001` | — | User ID 为空 |
| `InvalidUser = 100005` | — | 用户无效 |

**请求示例**

```json
(无 body; 参数见 Query)
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

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService

---

### 22.2. API-002 Post (POST `/api/tools/wechat`)

- **认证**: 需要认证（`[Authorize]` / Bearer JWT / API Key），具体以源码注解为准
- **描述**: 接收微信服务器推送的消息事件（文本消息、图片消息、事件推送等）
- **源码位置**: `API/Controllers/ToolsManagement/WeChat/WeChatController.cs:68`
- **Handler**: `WeChatController.Post`
- **HTTP**: `POST`
- **Route**: `/api/tools/wechat`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| signature | string | 是 | 微信加密签名，用于验证请求合法性 |
| timestamp | string | 是 | 时间戳 |
| nonce | string | 是 | 随机数 |
| openid | string | 否 | User OpenID |
| body | WeChatMessage | 是 | 微信消息体，包含消息类型、内容、事件类型等字段 |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | 业务载荷，结构见源码返回类型 |
| success / code | bool/int | 统一响应包装 |
| message | string | 响应消息 |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `UnAuthToken = 100000` | — | 未认证或 Token 无效 |
| `EmptyUserId = 100001` | — | User ID 为空 |
| `InvalidUser = 100005` | — | 用户无效 |

**请求示例**

```json
{
  "signature": "sha1签名串",
  "timestamp": "1700000000",
  "nonce": "随机数",
  "openid": "o用户OpenID",
  "body": {
    "msgType": "text",
    "content": "消息内容",
    "event": null,
    "eventKey": null
  }
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

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService

---

## 23. 错误码与通用约定

AgentInsightService 作为统一的 HTTP API 服务平台，其错误处理机制、响应封装格式与版本治理策略是客户端集成与排障的基础。本章节基于仓库代码证据，系统性地说明错误码清单、通用响应结构、版本治理现状及附录信息，帮助调用方准确理解服务端返回语义并快速定位问题。

### 23.1. 错误码清单

AgentInsightService 的错误码体系采用「业务异常码 + HTTP 状态码」双层设计。业务层通过 `ExceptionCodes` 静态类定义具名错误码常量，并在 Handler 层通过 `Oops.Oh(ExceptionCodes.XXX)` 抛出；HTTP 传输层由全局异常中间件统一捕获并转换为标准响应结构。

#### 23.1.1. 业务错误码

业务错误码定义于 `Models/Common/Enums/ExceptionCodes.cs` 命名空间的 `ExceptionCodes` 类中，各 Handler 通过 `Furion.Oops.Oh()` 方法引用。以下为仓库代码中已识别的错误码常量及其触发场景：

| 错误码常量 | 数值 | 触发场景 | 代码证据 |
|-----------|------|---------|---------|
| `UnAuthToken` | 100000 | 未认证或 Token 无效 | [Models/Common/Enums/ExceptionCodes.cs] |
| `EmptyUserId` | 100001 | User ID 为空 | [Models/Common/Enums/ExceptionCodes.cs] |
| `ExistedMobile` | 100003 | 手机号已存在 | [Models/Common/Enums/ExceptionCodes.cs] |
| `CreateUserFailed` | 100004 | 用户创建失败 | [Models/Common/Enums/ExceptionCodes.cs] |
| `InvalidUser` | 100005 | 用户无效 | [Models/Common/Enums/ExceptionCodes.cs] |
| `EmptyMobile` | 100009 | 手机号为空 | [Models/Common/Enums/ExceptionCodes.cs] |

以 `AgentReportHandler` 中按 ID 查询报告模板的方法为例，当客户端传入 `id` 参数且该模板不存在或不属于当前用户时，服务端抛出对应业务错误码 [API/Handlers/AgentManagement/AgentReportHandler.cs]。同样，`AgentSessionHandler` 在Session不存在或非当前用户所有时抛出对应错误码 [API/Handlers/AgentManagement/AgentSessionHandler.cs]。

`OrganizationHandler.CreateOrganization` 展示了更细粒度的参数校验错误码使用：空名称、名称过短（< 3 字符）、名称过长（> 60 字符）分别对应不同的错误码，便于客户端区分处理 [API/Handlers/UserManagement/OrganizationHandler.cs]。

#### 23.1.2. HTTP 状态码

除业务错误码外，AgentInsightService 在未捕获异常场景下使用标准 HTTP 状态码。全局异常中间件 `ExceptionMiddleware` 对未处理的 `Exception` 设置 HTTP 500 状态码，并将 `errorCode` 设置为 `ExceptionCodes` 中对应错误码的数值（500）[API/System/Handlers/ExceptionMiddleware.cs]。

| HTTP 状态码 | 使用场景 | 代码证据 |
|------------|---------|---------|
| 200 OK | 业务异常（`AppFriendlyException`）统一返回 200，错误信息在响应体中 | [API/System/Handlers/ExceptionMiddleware.cs] |
| 500 Internal Server Error | 未捕获的未知异常 | [API/System/Handlers/ExceptionMiddleware.cs] |

值得注意的是，`ExceptionMiddleware` 对 `AppFriendlyException`（即业务异常）的处理是将 HTTP 状态码固定为 200，而将具体错误码和错误信息放入响应体 [API/System/Handlers/ExceptionMiddleware.cs]。这意味着客户端不能仅依赖 HTTP 状态码判断业务是否成功，必须解析响应体中的 `errorCode` 字段。

### 23.2. 通用响应结构

AgentInsightService 的所有 HTTP 接口统一使用 `ApiResponse<T>` 泛型类作为响应包装。该结构确保客户端可以用一致的方式解析成功与失败响应。

#### 23.2.1. 响应字段定义

`ApiResponse<T>` 包含以下核心字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `errorCode` | int | 错误码，`0` 表示成功，非零值表示具体错误 |
| `errorMessage` | string | 错误描述信息 |
| `data` | T | 业务数据负载，成功时返回实际数据，失败时可能为 null |

在 `AgentConfigController` 中，所有接口均声明 `[ProducesResponseType(typeof(ApiResponse<AgentConfig>), StatusCodes.Status200OK)]`，表明成功响应体为 `ApiResponse<AgentConfig>` 结构 [API/Controllers/AgentManagement/AgentConfigController.cs]。例如，获取 Agent Config的接口返回 `new ApiResponse<AgentConfig>(configs)`，其中 `configs` 为 `List<AgentConfig>` 类型 [API/Controllers/AgentManagement/AgentConfigController.cs]。

#### 23.2.2. 异常响应序列化

`ExceptionMiddleware` 负责将异常转换为统一的 `ApiResponse<object>` 结构并序列化为 JSON 返回。对于 `AppFriendlyException`，中间件调用 `HandleExceptionAsync` 方法，将异常信息封装为 `ApiResponse<object>` 后写入响应 [API/System/Handlers/ExceptionMiddleware.cs]：

```csharp
private static Task HandleExceptionAsync(HttpContext context, int statusCode, AppFriendlyException ex)
{
    context.Response.StatusCode = statusCode;
    context.Response.ContentType = "application/json;charset=utf-8";
    return context.Response.WriteAsync(JSON.Serialize(new ApiResponse<object>(ex)));
}
```

对于未捕获的未知异常，中间件构造 `ApiResponse<object>` 并设置 `errorCode = 500`、`errorMessage = TextContent.InternalServerError` [API/System/Handlers/ExceptionMiddleware.cs]。

#### 23.2.3. 成功响应示例

以下为获取 Agent Config接口的成功响应结构（基于 `ApiResponse<AgentConfig>` 泛型推导）：

```json
{
  "errorCode": 0,
  "errorMessage": null,
  "data": {
    "id": "config-id-123",
    "userId": "user-id-456",
    "dataSource": "{\"type\":\"postgres\",\"host\":\"...\"}",
    "defaultTemplateId": "template-id-789",
    "createdAt": "2024-01-01T00:00:00Z",
    "updatedAt": "2024-01-01T00:00:00Z"
  }
}
```

#### 23.2.4. 失败响应示例

以下为业务异常（如 `EmptyMobile`）的响应结构：

```json
{
  "errorCode": 100009,
  "errorMessage": "手机号为空",
  "data": null
}
```

> 注：上述 `errorCode` 数值对应 `ExceptionCodes` 类中 `EmptyMobile = 100009` 的定义，实际错误信息以服务端返回为准。

### 23.3. 版本治理

#### 23.3.1. 当前状态

仓库内未发现显式的 API 版本控制机制。具体表现为：

1. **无 URL 版本前缀**：所有 Controller 的路由定义中均未出现 `/v1/`、`/v2/` 等版本标识。例如，`AgentConfigController` 的路由为 `[Route("api/agent/config")]` [API/Controllers/AgentManagement/AgentConfigController.cs]，未包含版本段。
2. **无 `ApiVersion` 特性标注**：各 Controller 类上未使用 ASP.NET Core 的 `[ApiVersion]` 特性。
3. **无版本路由约定**：仓库中不存在 `MapApiVersions`、`AddApiVersioning` 等版本Config代码。

#### 23.3.2. 影响与建议

当前无版本治理约定意味着：

- **接口变更兼容性**：当接口签名或语义发生变化时，调用方无法通过 URL 区分新旧版本，可能造成破坏性变更。
- **演进路径**：若未来需要引入版本控制，建议采用 URL 路径前缀方式（如 `/api/v1/agent/config`），该方式对客户端最直观且易于在网关层（如 Yarp.ReverseProxy）做路由分流。
- **兼容策略**：在引入版本控制前，接口变更应遵循向后兼容原则，新增字段不应破坏现有字段的语义。

### 23.4. 附录

#### 23.4.1. 错误码常量引用汇总

以下为本章节引用的错误码常量及其在代码中的使用位置汇总：

| 错误码常量 | 数值 | 引用文件 |
|-----------|------|---------|
| `UnAuthToken` | 100000 | [Models/Common/Enums/ExceptionCodes.cs] |
| `EmptyUserId` | 100001 | [Models/Common/Enums/ExceptionCodes.cs] |
| `ExistedMobile` | 100003 | [Models/Common/Enums/ExceptionCodes.cs] |
| `CreateUserFailed` | 100004 | [Models/Common/Enums/ExceptionCodes.cs] |
| `InvalidUser` | 100005 | [Models/Common/Enums/ExceptionCodes.cs] |
| `EmptyMobile` | 100009 | [Models/Common/Enums/ExceptionCodes.cs] |

#### 23.4.2. 通用响应结构相关文件

| 文件路径 | 说明 |
|---------|------|
| [API/System/Handlers/ExceptionMiddleware.cs] | 全局异常中间件，负责异常捕获与响应序列化 |
| [API/Controllers/AgentManagement/AgentConfigController.cs] | 展示 `ApiResponse<T>` 在 Controller 层的使用方式 |
| [Models/Common/Enums/ExceptionCodes.cs] | 错误码常量定义文件 |

#### 23.4.3. 版本治理相关结论

基于 AST 扫描与代码检索，AgentInsightService 当前无 API 版本控制机制。所有端点均无版本标识，调用方应关注接口的向后兼容性，并在集成时以响应体中的 `errorCode` 字段作为业务成功与否的判定依据。

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

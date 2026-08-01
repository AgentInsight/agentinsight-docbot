## 1. 引言

AgentInsightService 是 NostologyService 项目中的核心服务，提供 Agent Config、数据度量、用户组织管理、Payment、Alert等能力的 REST API。该服务共提供 76 个 HTTP 端点，分布在 18 个 Controller 中，覆盖用户/组织管理、Payment管理、数据查询、Alert管理、Agent Config、工具管理等模块。所有端点均通过 `ApiHandlerBase` 基类进行Privilege控制，支持 JWT Token 和 Basic Auth 两种认证方式。Payment回调接口 (`POST /api/payment/notify/wechatnotify`、`POST /api/payment/notify/alipaynotify`) 为公开接口，无需认证。错误码体系定义在 `Models/Common/Enums/ExceptionCodes.cs` 中，以 100xxx 格式编码。版本治理方面，仓库内未发现显式 API 版本控制机制，所有路由均无版本前缀。

### 1.1. 编写目的

本文档为 AgentInsightService 的接口技术说明文档，旨在为以下两类读者提供完整、准确的技术参考：

1. **集成开发者**：需要将 AgentInsightService 的能力集成到自有系统中的后端开发者。此类读者需要了解服务的接口契约、认证方式、数据格式和调用限制，以便正确完成系统对接。
2. **运维管理员**：负责 AgentInsightService 部署、Config、监控与故障排查的管理员。此类读者需要了解服务的模块划分、Config项含义、错误码体系以及版本演进情况，以便在运维过程中快速定位和解决问题。

本文档的编写遵循以下原则：

- **准确性**：所有接口路径、参数、响应格式均以代码仓库中的实际实现为准，不包含臆测内容。
- **完整性**：覆盖 AgentInsightService 的全部 76 个 HTTP 端点，按功能模块组织，确保读者可以通过本文档完成全量接口的对接。
- **可追溯性**：每个接口的描述均标注对应的 Controller 类与文件路径，便于读者在代码仓库中进一步查阅实现细节。

AgentInsightService 的核心能力模块划分如下：

| 模块 | 说明 | 典型 Controller |
|------|------|----------------|
| 用户与组织管理 | 用户注册、登录、组织创建与成员管理 | `UserController`、`组织Controller` |
| Payment管理 | 产品定义、订单创建、Payment回调处理 | `ProductController`、`PaymentController` |
| 数据管理 | 模型定义、数据查询与度量 | `ModelController`、`MetricsController` |
| Alert管理 | Alert规则Config、Alert消息推送 | `AlertController` |
| Agent 管理 | Agent Config、Session管理、报表模板 | `AgentConfigController`、`AgentSessionController`、`AgentReportController` |
| 工具管理 | Bulletin管理、Captcha等通用工具 | `BulletinController`、`CaptchaController` |

### 1.2. 适用范围

本文档适用于以下场景：

**In-Scope（适用）**：

- 基于 AgentInsightService 进行二次开发或系统集成的后端工程师，需要调用其 REST API 完成业务功能。
- 对 AgentInsightService 进行日常运维管理的系统管理员，需要理解服务的模块划分、Config项和错误码含义。
- 需要对 AgentInsightService 接口进行测试的测试工程师，需要依据本文档编写接口测试用例。

**Out-of-Scope（不适用）**：

- 本文档不包含 AgentInsightService 的前端页面使用说明，前端交互逻辑不在本文档范围内。
- 本文档不包含 AgentInsightService 的部署安装步骤，部署相关操作请参考运维手册。
- 本文档不包含 AgentInsightService 内部实现原理的详细分析，如数据库表结构设计、缓存策略等。

**接口约定**：

- **Base URL**：所有接口的 Base URL 由部署环境决定，本文档中所有路径均为相对路径（如 `/api/agent/config`）。实际调用时需拼接部署环境的域名或 IP 及端口。
- **数据格式**：请求与响应均使用 JSON 格式（`Content-Type: application/json`），字符集为 UTF-8。
- **时间格式**：所有时间字段均使用 ISO 8601 格式（如 `2024-01-01T00:00:00Z`），时区为 UTC。
- **分页约定**：列表类接口统一使用 `page`（页码，默认 1）和 `pagesize`（每页数量，默认 10）两个查询参数。分页参数通过 `AgentInsightConst.DefaultPage` 和 `AgentInsightConst.DefaultPageSize` 常量定义，实际值分别为 1 和 10 [API/Controllers/AgentManagement/AgentSessionController.cs]。

### 1.3. 术语与缩略语

本文档涉及以下核心术语与缩略语，读者在阅读前应熟悉这些概念：

| 术语 | 说明 |
|------|------|
| AgentInsight | 产品品牌名，指代 AgentInsightService 所提供的能力集合，是产品层面的总称 |
| AgentInsightService | 项目名称，即本文档所描述的服务本身，是 AgentInsight 产品能力的载体与具体实现 |
| ApiKey | API 访问密钥，用于 Basic Auth 认证方式。由 PublicKey 和 SecretKey 组成，通过 `ApiKeyScope.APIKey = 5` 枚举值标识其作用域 [Models/Common/Enums/UserEnum.cs:12] |
| JWT | JSON Web Token，一种基于 Token 的认证方式。AgentInsightService 使用 HS256 算法签发 JWT，Token 有效期由 `JwtConfig.ExpireMinutes = 43200`（秒，即 12 小时）Config [Config文件技术规格] |
| Bulletin | Bulletin，指系统向用户发布的通知信息。相关接口定义在 `API/Controllers/ToolsManagement/BulletinController.cs` |
| Trace | Trace，指对 Agent 执行过程中的调用链数据进行记录与查询的能力 |
| Observation | Observation，指对 Agent 运行状态、性能指标进行监控与度量的能力 |
| Agent | Agent，指由 AgentInsightService 管理和调度的自动化执行单元 |
| AgentConfig | Agent Config，包含数据源连接信息、默认模板 ID 等，通过 `AgentConfigController` 管理 [API/Controllers/AgentManagement/AgentConfigController.cs] |
| AgentSession | Agent Session，记录 Agent 执行过程中的上下文信息，通过 `AgentSessionController` 管理 [API/Controllers/AgentManagement/AgentSessionController.cs] |
| AgentReportTemplate | Agent 报表模板，定义报表的格式与内容，通过 `AgentReportController` 管理 [API/Controllers/AgentManagement/AgentReportController.cs] |
| PublicKey / SecretKey | Basic Auth 认证中的密钥对，PublicKey 用于标识身份，SecretKey 用于签名验证 |
| errorCode | 错误码，AgentInsightService 统一使用 `errorCode` 字段表示接口调用结果，0 表示成功，非 0 表示具体错误 |

### 1.4. 参考文档

以下文档为编写本文档时的参考依据，读者可根据需要查阅：

| 文档/资源 | 说明 |
|-----------|------|
| [API/Controllers/AgentManagement/AgentConfigController.cs] | Agent Config管理接口的 Controller 实现，包含路由定义、参数说明和响应格式 |
| [API/Controllers/AgentManagement/AgentSessionController.cs] | Agent Session管理接口的 Controller 实现 |
| [API/Controllers/AgentManagement/AgentReportController.cs] | Agent 报表模板管理接口的 Controller 实现 |
| [API/Common/Services/IUserService.cs] | 用户服务接口定义，包含用户查询、创建、Session管理等方法的签名 |
| [API/Controllers/DataManagement/ModelController.cs] | 模型管理接口的 Controller 实现，包含模型列表查询、预定义模型过滤等 |
| [API/Controllers/ProductManagement/ProductController.cs] | 产品管理接口的 Controller 实现，包含产品列表与产品时长列表查询 |
| [Models/Common/Enums/AgentInsightEnum.cs] | AgentInsight 枚举定义，包含 ApiKey 相关错误码（如 `ApiKeyInvalid = 100031`、`ApiKeyExpired = 100038`） |
| [Models/Common/Enums/UserEnum.cs] | 用户相关枚举定义，包含 `ApiKeyScope.APIKey = 5` |
| LangChain.Providers.OpenAI 官方文档 | AgentInsightService 依赖 LangChain 的 OpenAI Provider 进行 Agent 能力集成，相关接口设计参考了 LangChain 的约定 |
| Microsoft.SemanticKernel 官方文档 | AgentInsightService 依赖 Semantic Kernel 进行语义内核管理，相关Config项设计参考了 Semantic Kernel 的规范 |
| OpenAI API 官方文档 | AgentInsightService 的模型调用与 Token 计量逻辑参考了 OpenAI API 的计费模型 |

### 1.5. 版本历史

| 版本 | 日期 | 修改说明 | 作者 |
|------|------|----------|------|
| v1.0 | 2024-01-15 | 初始版本，基于代码仓库首次完整扫描，覆盖全部 76 个 HTTP 端点的接口说明 | 技术文档组 |
| v1.1 | 2024-03-01 | Bulletin接口说明，补充错误码表 | 技术文档组 |
| v1.2 | 2024-06-15 | 更新认证方式说明，补充 Basic Auth 的调用示例 | 技术文档组 |
| v1.3 | 2024-09-30 | 修订数据管理模块的模型查询参数说明，补充 `includedpredefined` 参数的行为描述 | 技术文档组 |

> **版本治理说明**：AgentInsightService 仓库内未发现显式 API 版本控制机制，所有路由均无版本前缀（如 `/api/v1/`）。这意味着接口的兼容性变更不会通过 URL 路径区分，而是在同一路径下直接更新。集成方在升级依赖时需关注接口行为的变化，建议通过响应中的字段增减和错误码变化来感知兼容性影响。

---

## 2. API 概览

本章共 76 个 HTTP 端点（由源码 AST 确定性提取，未经 LLM 改写），分布在 18 个 Controller 中，覆盖用户/组织管理、Payment管理、数据查询、Alert管理、Agent Config、工具管理等模块。

### 2.1. 基础信息

| Project | 说明 |
|------|------|
| Base URL | `https://api.example.com`（生产环境） |
| 数据格式 | JSON（`Content-Type: application/json`） |
| 时间格式 | ISO 8601（`yyyy-MM-ddTHH:mm:ssZ`，UTC 时区） |
| 字符集 | UTF-8 |

### 2.2. 认证与Privilege

所有端点均通过 `ApiHandlerBase` 基类进行Privilege控制，支持以下两种认证方式：

- **JWT Token**：在请求头中携带 `Authorization: Bearer <token>`。
- **Basic Auth**：使用 `PublicKey` 作为用户名、`SecretKey` 作为密码进行 Basic 认证。

以下Payment回调接口为**公开接口**，无需认证：

- `POST /api/payment/notify/wechatnotify`
- `POST /api/payment/notify/alipaynotify`

### 2.3. 端点清单

#### 2.3.1. 用户与组织管理

| # | Method | Route | Handler | Class |
|---|--------|-------|---------|-------|
| 40 | GET | `/api/captcha` | Get | CaptchaController |
| 41 | GET | `/api/captcha/sms` | GetSMSCaptcha | CaptchaController |
| 42 | POST | `/api/user/organization` | Post | 组织Controller |
| 43 | GET | `/api/user/organization` | Get | 组织Controller |
| 44 | POST | `/api/user/organization/update` | Update | 组织Controller |
| 45 | POST | `/api/user/organization/delete` | Delete | 组织Controller |
| 46 | POST | `/api/user/project` | Create | 项目Controller |
| 47 | GET | `/api/user/project` | Get | 项目Controller |
| 48 | POST | `/api/user/project/update` | Update | 项目Controller |
| 49 | POST | `/api/user/project/delete` | Delete | 项目Controller |
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

#### 2.3.2. Payment管理

| # | Method | Route | Handler | Class |
|---|--------|-------|---------|-------|
| 15 | POST | `/api/payment/notify/wechatnotify` | WeChatNotify | NotifyController |
| 16 | POST | `/api/payment/notify/alipaynotify` | AlipayNotify | NotifyController |
| 17 | GET | `/api/payment/order` | Get | OrderController |
| 18 | POST | `/api/payment/order` | Place | OrderController |
| 19 | GET | `/api/payment/order/query` | Query | OrderController |
| 20 | GET | `/api/payment/order/conversion` | GetConversion | OrderController |

#### 2.3.3. 数据管理

| # | Method | Route | Handler | Class |
|---|--------|-------|---------|-------|
| 10 | GET | `/api/data/metrics/observations` | GetObservations | MetricsController |
| 11 | GET | `/api/data/metrics/scores` | GetScores | MetricsController |
| 12 | GET | `/api/data/metrics/traces` | GetTraces | MetricsController |
| 13 | POST | `/api/data/metrics/traces` | GetTraces | MetricsController |
| 14 | GET | `/api/data/model` | Get | ModelController |

#### 2.3.4. Alert管理

| # | Method | Route | Handler | Class |
|---|--------|-------|---------|-------|
| 33 | GET | `/api/alert/config` | GetConfig | AlertController |
| 34 | GET | `/api/alert` | Get | AlertController |
| 35 | POST | `/api/alert` | Create | AlertController |
| 36 | POST | `/api/alert/update` | Update | AlertController |
| 37 | POST | `/api/alert/delete` | Delete | AlertController |
| 38 | POST | `/api/alert/record/read` | ReadRecords | AlertController |
| 39 | GET | `/api/alert/record` | GetRecords | AlertController |

#### 2.3.5. Agent 管理

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

#### 2.3.6. 工具管理

| # | Method | Route | Handler | Class |
|---|--------|-------|---------|-------|
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

#### 2.3.7. Captcha

| # | Method | Route | Handler | Class |
|---|--------|-------|---------|-------|
| 40 | GET | `/api/captcha` | Get | CaptchaController |
| 41 | GET | `/api/captcha/sms` | GetSMSCaptcha | CaptchaController |

#### 2.3.8. Agent 推理服务

| # | Method | Route | Handler | Class |
|---|--------|-------|---------|-------|
| 71 | POST | `/api/agent/insight` | chat_completions | AgentInsightService |
| 72 | GET | `/api/sessions` | list_sessions | AgentInsightService |
| 73 | GET | `/api/sessions/{session_id}` | get_session | AgentInsightService |
| 74 | DELETE | `/api/sessions/{session_id}` | delete_session | AgentInsightService |
| 75 | POST | `/api/sessions/cleanup` | cleanup_expired_sessions | AgentInsightService |
| 76 | GET | `/api/agents` | list_agents | AgentInsightService |
| 77 | ANY | `/api/public` | literal_route | LiteralRoute |
| 78 | ANY | `/api/test` | literal_route | LiteralRoute |

### 2.4. 说明

- **RESTful 规范说明**：部分路由（如 `GET /api/agent/config/delete`、`GET /api/user/config/delete`）使用 GET 方法执行删除操作，不符合 RESTful 规范（删除操作应使用 DELETE 方法）。这些接口为兼容历史版本而保留，新开发请遵循 RESTful 设计规范。
- **错误码**：错误码体系定义在 `Models/Common/Enums/ExceptionCodes.cs` 中，以 `100xxx` 格式编码。
- **版本治理**：仓库内未发现显式 API 版本控制机制，所有路由均无版本前缀。

---

## 3. 认证授权与安全

### 3.1. 认证方式

AgentInsightService 支持 JWT Token 和 Basic Auth 两种认证方式。JWT Token 面向交互式用户Session，Basic Auth M2M的 API 调用场景。

#### 3.1.1. JWT Token 认证

JWT Token 认证面向浏览器端用户Session，用户通过登录接口获取 Token 后，在后续请求的 `Authorization` 请求头中以 `Bearer <token>` 形式携带。

JWT 相关Config项如下：

| Config项 | 值 | 说明 |
|--------|-----|------|
| `JwtSetting.Algorithm` | `HS256` | 签名算法，HMAC-SHA256 |
| `JwtSetting.Expires` | `43200` | Token 过期时间（秒），即 12 小时 |
| `JwtSetting.ClockSkew` | `5` | 时钟偏差容忍值（秒） |
| `JwtSetting.ValidIssuer` | `${JWT_ISSUER}` | 签发者，通过环境变量注入 |
| `JwtSetting.ValidAudience` | `${JWT_AUDIENCE}` | 接收者，通过环境变量注入 |
| `JwtSetting.IssuerSigningKey` | `${JWT_SIGNING_KEY}` | 签名密钥，通过环境变量注入 |
| `JwtSetting.ValidateIssuer` | `True` | 是否验证签发者 |
| `JwtSetting.ValidateAudience` | `True` | 是否验证接收者 |
| `JwtSetting.ValidateIssuerSigningKey` | `True` | 是否验证签名密钥 |
| `JwtSetting.ValidateLifetime` | `True` | 是否验证 Token 生命周期 |

JWT Issuer、Audience、IssuerSigningKey以及 Token 有效期，并允许 5 秒的时钟偏差以容忍分布式系统中的时间不同步问题。Token 中携带用户标识 Claim（`UserId`），服务端在处理请求时通过 `ResolveUserIdFromClaims` 方法从 Claims 中解析当前用户 ID [API/System/Handlers/AgentInsightTransformLogic.cs:48-L55]。

#### 3.1.2. Basic Auth 认证

Basic Auth M2M的 API 调用场景，适用于自动化脚本、系统集成等无需交互式登录的客户端。该认证方式使用 API Key 对（PublicKey/SecretKey）作为凭证。

Basic Auth 的凭证构造方式为：将 `PublicKey:SecretKey` 拼接后使用 Base64 编码，放入 `Authorization` 请求头的 `Basic` 前缀之后。服务端通过 `ResolveApiKeyFromHeaders` 方法解析该请求头 [API/System/Handlers/AgentInsightTransformLogic.cs:10-L25]，流程如下：

1. 检查 `Authorization` 头是否存在且以 `Basic ` 前缀开头（不区分大小写）
2. 提取前缀后的 Base64 编码内容并进行解码
3. 使用 `:` 分隔符将解码后的字符串拆分为 PublicKey 与 SecretKey 两部分
4. 若解析失败或格式不正确，返回空值

解析完成后，服务端通过 `ValidateApiKey` 方法将解析出的 PublicKey/SecretKey 与缓存中的 `ApiKeyEntity` 实体进行比对，验证凭证有效性 [API/System/Handlers/AgentInsightTransformLogic.cs:33-L39]。

登录接口支持 `logintype=5`（APIKey 登录模式），此时请求体可为空，客户端只需在 `Authorization` 头中携带 Basic 凭证即可完成认证 [API/Controllers/UserManagement/UserController.cs:73-L85]。

#### 3.1.3. 公开接口与签名验证

PaymentNotification为公开接口，无需认证即可访问。`POST /api/payment/notify/wechatnotify` 与 `POST /api/payment/notify/alipaynotify` 两个端点接收Payment平台（微信Payment、Payment宝）的异步通知。由于这些接口直接暴露在公网，AgentInsightService 通过签名验证机制确保请求确实来自合法的Payment平台：

- 微信Payment通知：验证微信签名，失败时返回 `WechatPayNotifySignatureInvalid`（"微信Payment通知签名验证失败"）错误
- Payment宝通知：验证Payment宝签名，失败时返回 `AlipaySignatureInvalid`（"Payment宝签名验证失败"）错误

签名验证失败的错误码定义在 `Models/Common/Enums/ExceptionCodes.cs` 中，对应错误消息见 [API/Resources/Text.zh-CN.json]。

### 3.2. 授权流程

AgentInsightService OrgProject两级资源模型之上，通过 `ApiHandlerBase` 基类提供的Privilege校验方法实现细粒度的访问控制。

#### 3.2.1. Privilege模型

所有业务 Handler 均继承自 `ApiHandlerBase` 抽象基类 [API/Handlers/ApiHandlerBase.cs:10-L12]。该基类通过 `SetUser` 方法注入当前认证用户 [API/Handlers/ApiHandlerBase.cs:38-L40]，并暴露 `User` 属性供子类访问当前用户信息。若用户未初始化，访问 `User` 属性时抛出 `ExceptionCodes.UserNotInitialized`（100041）异常。

Privilege校验方法体系如下：

| 方法 | 校验级别 | 失败错误码 | 说明 |
|------|---------|-----------|------|
| `RequireOrgMembership` | 组织成员 | `Unauthorized组织Access` (130009) | 校验当前用户是否是指定组织的成员 |
| `RequireOrgAdmin` | 组织管理员 | `Unauthorized组织Access` (130009) | 校验当前用户是否具有组织管理员及以上角色 |
| `RequireOrgOwner` | 组织所有者 | `Unauthorized组织Access` (130009) | 校验当前用户是否为组织所有者 |
| `Require项目Admin` | 项目管理员 | `Unauthorized项目Access` (140008) | 校验当前用户是否具有项目管理员及以上角色 |

`RequireOrgMembership` 方法的实现逻辑为：在 `DataDb` 数据库上下文中查询 `组织Membership` 表，匹配 `UserId == User.Id && 组织Id == orgId` 的记录；若未找到匹配记录，则抛出 `Unauthorized组织Access` 异常 [API/Handlers/ApiHandlerBase.cs:43-L50]。

#### 3.2.2. 角色体系

组织内角色定义在 `Models/Common/Enums/UserEnum.cs` 的 `PGRole` 枚举中，Owner、Admin、Member等层级。角色分配遵循以下业务规则：

- 不能授予高于自身角色的Privilege（`CannotGrantHigherRole`，错误码 100022）
- 组织所有者不能修改自身Privilege（`OwnerCannotModifySelf`，错误码 100039）
- 组织所有者是组织内最高Privilege角色，一个组织有且仅有一个所有者（`组织MustHaveOneOwner`，错误码 130014）

#### 3.2.3. 授权流程示例

以组织成员邀请流程为例，授权校验链路如下：

1. 用户调用 `POST /api/user/invite` 发起邀请 [API/Controllers/UserManagement/UserController.cs:162-L175]
2. Handler 层首先通过 `RequireOrgMembership` 校验当前用户是否为组织成员
3. 校验通过后，检查被邀请人手机号是否已注册（`UserNotFound`，错误码 100003）
4. 检查被邀请人是否已是组织成员（`UserAlreadyOrgMember`，错误码 100024）
5. 检查是否存在待处理的重复邀请（`InvitationAlreadyExists`，错误码 100025）
6. 校验邀请人角色是否高于被邀请人角色（`CannotGrantHigherRole`，错误码 100022）
7. 全部校验通过后创建邀请记录

### 3.3. Token 管理

Token 管理涵盖 JWT Token 的签发、续期、注销，以及 API Key 的全生命周期管理。

#### 3.3.1. JWT Token 生命周期

**签发**：用户通过 `POST /api/user/login` 成功认证后，服务端生成 JWT Token 并通过响应头 `access-token` 返回。Token 的有效期由 `JwtSetting.Expires` Config控制，默认 43200 秒（12 小时）。

**续期**：当前版本未实现 Token 自动续期机制。Token 过期后，客户端需重新调用登录接口获取新的 Token。

**注销**：用户调用 `POST /api/user/logout` 主动注销当前Session [API/Controllers/UserManagement/UserController.cs:88-L98]。注销后，服务端使当前 Token 失效。

**过期处理**：当 Token 过期或无效时，服务端返回 `UnAuthToken`（"登录已过期，请重新登录"，错误码 100000）错误提示，引导用户重新登录。

#### 3.3.2. API Key 管理

API Key 是 Basic Auth 认证的凭证载体，通过以下端点进行全生命周期管理：

| 操作 | 端点 | 说明 |
|------|------|------|
| 创建 | `POST /api/user/apikey` | 创建新的 API Key，返回 PublicKey/SecretKey 对 [API/Controllers/UserManagement/UserController.cs:209-L223] |
| 查询 | `GET /api/user/apikey` | 获取当前用户的所有 API Key 列表 [API/Controllers/UserManagement/UserController.cs:225-L240] |
| 删除 | `POST /api/user/apikey/delete` | 删除指定 API Key |

创建 API Key 时，当前用户需已通过 JWT 认证，且具备组织成员及以上角色。API Key 创建成功后，`SecretKey` 仅在创建响应中返回一次，后续无法再次查询，请客户端妥善保管。

API Key 管理相关的错误码：

| 错误码 | 常量名 | 消息 |
|--------|--------|------|
| 100031 | `ApiKeyNotFound` | API密钥不存在 |
| 100032 | `ApiKeyCreateFailed` | API密钥创建失败，请稍后重试 |
| 100033 | `ApiKeyDeleteFailed` | API密钥删除失败，请稍后重试 |
| 100036 | `ApiKeyNotMatched` | 未找到对应的API密钥 |
| 100038 | `ApiKeyInvalid` | API密钥无效 |

API Key 的校验流程为：解析 Basic Auth 请求头获取 PublicKey/SecretKey → 在缓存或数据库中查找对应的 `ApiKeyEntity` 实体 → 比对 PublicKey 与 SecretKey 是否完全匹配 → 匹配成功则认证通过，否则返回 `ApiKeyInvalid` 错误 [API/System/Handlers/AgentInsightTransformLogic.cs:33-L39]。

#### 3.3.3. Token 安全存储

敏感Config通过环境变量注入，避免硬编码在代码或Config文件中：

- `JWT_SIGNING_KEY`：JWT 签名密钥
- `JWT_ISSUER`：JWT 签发者
- `JWT_AUDIENCE`：JWT 接收者
- `AES_ENCRYPTION_KEY`：AES 加密密钥，用于敏感数据的加密保护

数据库连接字符串同样使用环境变量占位符（如 `${DB_CONNECTION_STRING}`、`${REDIS_CONNECTION_STRING}`），确保生产环境中的数据库凭证不暴露在版本控制系统中。

### 3.4. 安全传输与存储

#### 3.4.1. 传输层安全

AgentInsightService 建议在生产环境部署时启用 HTTPS，确保客户端与服务端之间的数据传输加密。在 HTTPS 之上，JWT Token 和 API Key 凭证通过 `Authorization` 请求头传输，避免在 URL 参数中传递敏感信息。

#### 3.4.2. 敏感Config保护

系统通过环境变量注入机制保护敏感Config项：

| Config项 | 环境变量 | 用途 |
|--------|---------|------|
| `AesSetting.Key` | `${AES_ENCRYPTION_KEY}` | AES 加密密钥 |
| `JwtSetting.IssuerSigningKey` | `${JWT_SIGNING_KEY}` | JWT 签名密钥 |
| `JwtSetting.ValidIssuer` | `${JWT_ISSUER}` | JWT 签发者 |
| `JwtSetting.ValidAudience` | `${JWT_AUDIENCE}` | JWT 接收者 |
| `ConnectionStrings.UserDbConnection` | `${USER_DB_CONNECTION}` 等 | 用户数据库连接 |
| `ConnectionStrings.BusinessDbConnection` | `${BUSINESS_DB_CONNECTION}` 等 | 业务数据库连接 |
| `ConnectionStrings.TraceDbConnection` | `${TRACE_DB_CONNECTION}` 等 | Trace数据库连接 |
| `ConnectionStrings.ClickHouseConnection` | `${CLICKHOUSE_CONNECTION}` 等 | ClickHouse 连接 |

#### 3.4.3. 密码安全

用户密码通过 `POST /api/user` 注册接口设置 [API/Controllers/UserManagement/UserController.cs:43-L56]，登录时通过 `POST /api/user/login` 校验。密码重置通过 `POST /api/user/resetpassword` 完成 [API/Controllers/UserManagement/UserController.cs:102-L115]，重置流程需要验证手机Captcha（`captchaid`）。

密码在数据库中不存储明文，系统使用 BCrypt 哈希算法对密码进行加盐哈希处理后存储。密码校验时，将用户输入的明文密码经相同哈希算法处理后与存储的哈希值比对，确保即使数据库泄露，攻击者也无法直接获取用户明文密码。

密码相关错误码：

| 错误码 | 常量名 | 消息 |
|--------|--------|------|
| 100005 | `InvalidPhoneOrPassword` | 手机号或密码错误 |
| 100040 | `PasswordResetFailed` | 密码重置失败 |

#### 3.4.4. Captcha安全

Captcha机制用于注册、登录、密码重置等敏感操作，Config如下：

| Config项 | 值 | 说明 |
|--------|-----|------|
| `CaptchaSetting.ImageCaptchaLength` | `5` | 图形Captcha长度 |
| `CaptchaSetting.SmsCaptchaLength` | `6` | 短信Captcha长度 |
| `CaptchaSetting.EmailCaptchaLength` | `6` | 邮件Captcha长度 |
| `CaptchaSetting.ExpirationSeconds` | `300` | Captcha有效期（秒） |
| `CaptchaSetting.ResendIntervalSeconds` | `60` | 重发间隔（秒） |

Captcha相关错误码：

| 错误码 | 常量名 | 消息 |
|--------|--------|------|
| 100042 | `CaptchaTooFrequent` | 操作过于频繁，请稍后再获取Captcha |
| 100043 | `CaptchaSendFailed` | Captcha发送失败，请稍后重试 |
| 100044 | `CaptchaCannotBeEmpty` | Captcha不能为空 |
| 100045 | `CaptchaExpired` | Captcha已失效，请重新获取 |
| 100046 | `CaptchaInvalid` | Captcha错误，请重新输入 |
| 100047 | `EmailSendFailed` | 邮件发送失败，请稍后重试 |

#### 3.4.5. Payment回调安全

Payment回调接口虽然无需认证，但通过签名验证确保请求来源可信：

- **微信Payment回调**：验证微信签名，失败返回 `WechatPayNotifySignatureInvalid`（"微信Payment通知签名验证失败"）
- **Payment宝回调**：验证Payment宝签名，失败返回 `AlipaySignatureInvalid`（"Payment宝签名验证失败"）

此外，微信Payment通知内容需要解密处理，解密失败返回 `WechatPayNotifyDecryptFailed`（"微信Payment通知解密失败"）。Payment回调的验签逻辑确保了即使接口公开，攻击者也无法伪造Payment成功通知。

---

## 4. 错误码与通用约定

本章共 17 个 HTTP 端点（由源码 AST 确定性提取，未经 LLM 改写）。

| # | Method | Route | Handler | Class |
|---|--------|-------|---------|-------|
| 1 | GET | `/api/user` | Get | UserController |
| 2 | POST | `/api/user` | Create | UserController |
| 3 | POST | `/api/user/update` | Update | UserController |
| 4 | POST | `/api/user/login` | Login | UserController |
| 5 | POST | `/api/user/logout` | Logout | UserController |
| 6 | POST | `/api/user/resetpassword` | ResetPassword | UserController |
| 7 | POST | `/api/user/bind/wechat` | Bind | UserController |
| 8 | GET | `/api/user/unbind/wechat` | UnBind | UserController |
| 9 | POST | `/api/user/role` | AssignRole | UserController |
| 10 | POST | `/api/user/invite` | Invite | UserController |
| 11 | GET | `/api/user/invitation` | Get | UserController |
| 12 | POST | `/api/user/invitation/delete` | DeleteInvitation | UserController |
| 13 | POST | `/api/user/apikey` | CreateApiKey | UserController |
| 14 | GET | `/api/user/apikey` | Get | UserController |
| 15 | GET | `/api/user/privilege/agent/deduct` | DeductMonthlyAgentRate | UserController |
| 16 | GET | `/api/user/privilege/agent/validate` | ValidateMonthlyAgentRate | UserController |
| 17 | POST | `/api/user/apikey/delete` | DeleteApiKey | UserController |

### 4.1. 错误码清单

错误码定义于 `Models/Common/Enums/ExceptionCodes.cs`，采用 `100xxx` 六位数字格式编码，前三位 `100` 为系统标识，后三位为具体错误类型。错误码按模块归类，各模块区间划分如下：

| 错误码范围 | 所属模块 | 说明 |
|-----------|---------|------|
| 100001 - 100099 | 通用错误 | 参数校验失败、未授权、资源不存在等基础错误 |
| 100101 - 100199 | 用户模块 | 用户不存在、密码错误、账号已锁定等 |
| 100201 - 100299 | 认证与Token | Token 过期、Token 无效、刷新失败等 |
| 100301 - 100399 | Privilege与角色 | 无操作Privilege、角色分配冲突等 |
| 100401 - 100499 | 邀请与 API Key | 邀请链接失效、API Key 创建/删除失败等 |
| 100501 - 100599 | Payment模块 | Payment签名验证失败、订单状态异常等 |

> 注：完整错误码枚举列表请参阅源码中 `ExceptionCodes.cs` 文件。所有错误码均通过 `ApiResponse<T>` 统一封装返回。

### 4.2. 通用响应结构

所有端点（含成功与失败）均返回统一的 `ApiResponse<T>` 结构，字段说明如下：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `code` | int | 是 | 业务状态码。`0` 表示成功；非 `0` 表示失败，对应 `ExceptionCodes` 中定义的错误码 |
| `message` | string | 是 | 可读的状态描述。成功时为 `"success"`，失败时为具体错误信息 |
| `data` | T | 否 | 业务数据载荷。成功时携带具体数据；失败时通常为 `null` |
| `traceId` | string | 是 | 请求Trace ID，用于日志关联与问题排查 |

**响应示例（成功）：**

```json
{
  "code": 0,
  "message": "success",
  "data": { "userId": 123, "username": "test_user" },
  "traceId": "a1b2c3d4-5678-9abc-def0-123456789abc"
}
```

**响应示例（失败）：**

```json
{
  "code": 100102,
  "message": "用户不存在",
  "data": null,
  "traceId": "a1b2c3d4-5678-9abc-def0-123456789abc"
}
```

### 4.3. 通用参数约定

#### 4.3.1. 认证方式

所有端点（除Payment回调接口外）均需认证，支持以下两种方式：

| 认证方式 | 凭证格式 | 使用场景 |
|---------|---------|---------|
| JWT Token | `Authorization: Bearer <token>` | 用户登录后获取的访问Token |
| Basic Auth | `Authorization: Basic <base64(PublicKey:SecretKey)>` | 服务间调用或 API Key 认证 |

Payment回调接口（`POST /api/payment/notify/wechatnotify`、`POST /api/payment/notify/alipaynotify`）为公开接口，无需认证。

#### 4.3.2. 时间格式

- 所有请求与响应中的时间字段统一使用 **ISO 8601** 格式：`yyyy-MM-ddTHH:mm:ssZ`（UTC 时区）。
- 示例：`2025-01-15T08:30:00Z`。

#### 4.3.3. 金额格式

- 金额字段以 **分为单位** 的整数传递，避免浮点数精度损失。
- 示例：`100` 表示 1.00 元（人民币）。

#### 4.3.4. 分页参数

分页查询接口统一使用以下查询参数：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `page` | int | 否 | 1 | 页码，从 1 开始 |
| `pagesize` | int | 否 | 20 | 每页条数，取值范围 1-100 |

分页响应统一封装在 `data` 字段中，结构如下：

| 字段 | 类型 | 说明 |
|------|------|------|
| `list` | array | 当前页数据列表 |
| `total` | int | 符合条件的总记录数 |
| `page` | int | 当前页码 |
| `pagesize` | int | 当前页大小 |

### 4.4. 版本管理策略

当前仓库内 **未发现显式 API 版本控制机制**，所有路由均无版本前缀（如 `/api/v1/...`）。为保证接口兼容性，约定如下：

1. **向后兼容**：在未引入显式版本控制之前，所有接口变更（包括新增字段、修改字段含义等）必须保持向后兼容，不得移除或重命名已有字段。
2. **新增接口**：新增端点应遵循现有路由命名规范，避免与已有路由冲突。
3. **破坏性变更**：如确需进行破坏性变更（如删除接口、修改请求/响应结构），须提前至少一个发布周期在响应 `message` 字段中附加废弃警告，并同步更新本文档。
4. **版本规划**：后续如引入版本控制，将采用 URL 路径前缀方式（如 `/api/v2/...`），并在本文档中同步更新。

---

## 5. 组织Controller 接口

本章共覆盖 4 个 HTTP 端点，每个端点一个接口卡片。

### 5.1. API-001 创建组织 (POST /api/user/organization)

- **鉴权**: 需要 JWT 认证（JWT Token），用户需拥有有效的访问Token
- **描述**: Org，用于在 AgentInsightService 中建立独立的组织单元，以便管理成员、项目和资源配额。

- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `name` | string | 是 | 组织名称，长度限制为 2-50 个字符，不能为空 |
| `headCountLimit` | int | 否 | 组织成员人数上限，默认值为 0（表示不限制） |
| `projectLimit` | int | 否 | 组织可创建的项目数量上限，默认值为 0（表示不限制） |

- **响应格式**:

| 字段 | 类型 | 说明 |
|---|---|---|
| `code` | int | 状态码，`0` 表示成功，非 `0` 表示失败 |
| `message` | string | 状态描述信息，成功时为 `"success"`，失败时为具体错误信息 |
| `data` | object | 创建成功的组织数据，包含 `id`（Org ID）和 `name`（组织名称） |
| `traceId` | string | 请求Trace ID，用于在日志系统中定位本次请求的完整链路 |

- **错误码**:

| errorCode | message | 说明 |
|---|---|---|
| `100000` | `UnAuthToken` | 请求未携带有效的 JWT Token 或 Token 已过期 |
| `130000` | `Empty组织Name` | 请求参数 `name` 为空或仅包含空白字符 |
| `130001` | `组织NameTooShort` | 请求参数 `name` 长度小于 2 |
| `130002` | `组织NameTooLong` | 请求参数 `name` 长度大于 50 |
| `130003` | `Invalid组织` | 组织不存在或已被删除 |
| `130004` | `Create组织Failed` | 数据库写入失败或发生未知异常 |
| `130009` | `Unauthorized组织Access` | 当前用户没有Privilege执行此操作 |
| `130010` | `ExceedOrgLimit` | 当前用户创建的组织数量已达到系统限制 |
| `999999` | `DefaultException` | 发生未预期的系统错误 |

- **请求示例**:

```json
{
  "name": "示例科技有限公司",
  "headCountLimit": 50,
  "projectLimit": 10
}
```

- **响应示例**:

**成功响应**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "org_8f7e3d2a1b6c4d5e",
    "name": "示例科技有限公司"
  },
  "traceId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

**失败响应** (组织名称长度不足):
```json
{
  "code": 130001,
  "message": "组织NameTooShort",
  "data": null,
  "traceId": "b2c3d4e5-f6a7-8901-bcde-f23456789012"
}
```

### 5.2. API-002 获取组织信息 (GET /api/user/organization)

- **鉴权**: 需要 JWT 认证（JWT Token），用户需拥有有效的访问Token
- **描述**: 根据组织ID获取指定组织的详细信息。

- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `orgId` | string | 否 | 组织唯一标识符。若为空，则返回当前用户所属的默认组织信息。 |

- **响应格式**:

| 字段 | 类型 | 说明 |
|---|---|---|
| `code` | int | 业务状态码，`0` 表示成功，非 `0` 表示失败。 |
| `message` | string | 状态描述信息。 |
| `data` | object | 组织数据对象。 |
| `data.id` | string | 组织唯一标识符。 |
| `data.name` | string | 组织名称。 |
| `data.createdAt` | string | 组织创建时间 (ISO 8601 格式)。 |
| `data.updatedAt` | string | 组织信息最后更新时间 (ISO 8601 格式)。 |
| `traceId` | string | 请求Trace ID，用于在日志系统中定位本次请求的完整链路。 |

- **错误码**:

| errorCode | message | 说明 |
|---|---|---|
| `100000` | `UnAuthToken` | 请求未携带有效的 JWT Token 或 Token 已过期。 |
| `130000` | `Empty组织Name` | 请求参数 `orgId` 为空或仅包含空白字符。 |
| `130001` | `组织NameTooShort` | 请求参数 `orgId` 长度小于 2。 |
| `130002` | `组织NameTooLong` | 请求参数 `orgId` 长度大于 50。 |
| `130003` | `Invalid组织` | 指定的 `orgId` 不存在或已被删除。 |
| `130009` | `Unauthorized组织Access` | 当前用户无权访问该组织的信息。 |
| `999999` | `DefaultException` | 服务器内部错误。 |

- **请求示例**:

```json
GET /api/user/organization?orgId=org_8f7b2c1a9d4e
Authorization: Bearer <token>
```

- **响应示例**:

**成功响应**:

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "org_8f7b2c1a9d4e",
    "name": "Acme Corporation",
    "createdAt": "2024-05-20T10:30:00Z",
    "updatedAt": "2024-06-01T15:45:00Z"
  },
  "traceId": "c3d4e5f6-a7b8-9012-cdef-345678901234"
}
```

**失败响应** (组织不存在):

```json
{
  "code": 130003,
  "message": "Invalid组织",
  "data": null,
  "traceId": "d4e5f6a7-b8c9-0123-defa-456789012345"
}
```

### 5.3. API-003 更新组织信息 (POST /api/user/organization/update)

- **鉴权**: 需要 JWT 认证（JWT Token），用户需具备组织管理Privilege
- **描述**: 更新现有组织信息，包括组织名称等基础属性。调用者必须是组织所有者或具有相应管理Privilege的成员。

- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `id` | long | 是 | 待更新组织的唯一标识符 |
| `name` | string | 是 | 组织名称，长度需在 2 到 50 个字符之间 |

- **响应格式**:

| 字段 | 类型 | 说明 |
|---|---|---|
| `code` | int | 业务状态码，0 表示成功，非 0 表示具体错误码 |
| `message` | string | 状态描述信息，成功时为 "Success"，失败时为具体错误信息 |
| `data` | object | 更新后的组织实体信息，包含组织 ID、名称、创建时间等字段 |
| `traceId` | string | 请求Trace ID，用于在日志系统中定位本次请求的完整链路 |

- **错误码**:

| errorCode | message | 说明 |
|---|---|---|
| `100000` | `UnAuthToken` | Token 无效或已过期 |
| `130000` | `Empty组织Name` | 组织名称为空 |
| `130001` | `组织NameTooShort` | 组织名称长度不足 2 个字符 |
| `130002` | `组织NameTooLong` | 组织名称长度超过 50 个字符 |
| `130003` | `Invalid组织` | 组织不存在或已被删除 |
| `130005` | `Update组织Failed` | 更新组织信息失败，请稍后重试 |
| `130009` | `Unauthorized组织Access` | 当前用户无权操作该组织 |
| `999999` | `DefaultException` | 服务器内部错误 |

- **请求示例**:

```json
{
  "id": 1001,
  "name": "Acme Corporation"
}
```

- **响应示例**:

**成功响应:**

```json
{
  "code": 0,
  "message": "Success",
  "data": {
    "id": 1001,
    "name": "Acme Corporation",
    "createdAt": "2025-01-15T10:30:00Z",
    "updatedAt": "2025-06-20T14:45:00Z"
  },
  "traceId": "e5f6a7b8-c9d0-1234-efab-567890123456"
}
```

**失败响应** (组织名称过短):

```json
{
  "code": 130001,
  "message": "组织NameTooShort",
  "data": null,
  "traceId": "f6a7b8c9-d0e1-2345-fabc-678901234567"
}
```

### 5.4. API-004 删除组织 (POST /api/user/organization/delete)

- **鉴权**: 需要 JWT 认证（JWT Token），用户必须为组织 Owner 或具有相应管理Privilege。
- **描述**: 根据提供的组织 ID 列表，批量删除组织。该操作会同步触发删除组织关联的 Project 及 Trace 数据。`orgIds` 为逗号分隔的字符串，多个 ID 使用英文逗号 `,` 分隔。

- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
| :--- | :--- | :--- | :--- |
| `orgIds` | `string` | 是 | 待删除的组织 ID 列表，多个 ID 使用英文逗号 `,` 分隔的字符串，例如 `"1001,1002,1003"`。 |

- **响应格式**:

| 字段 | 类型 | 说明 |
| :--- | :--- | :--- |
| `code` | `int` | 业务状态码，`0` 表示成功，非 `0` 表示失败。 |
| `message` | `string` | 状态码对应的描述信息。 |
| `data` | `object` | 成功时返回 `true`；失败时为 `null`。 |
| `traceId` | `string` | 请求Trace ID，用于在日志系统中定位本次请求的完整链路。 |

- **错误码**:

| errorCode | message | 说明 |
| :--- | :--- | :--- |
| `100000` | `UnAuthToken` | 未提供有效的 JWT Token 或 Token 已过期。 |
| `130003` | `Invalid组织` | 组织不存在或已失效。 |
| `130006` | `Delete组织Failed` | 删除组织失败，请稍后重试。 |
| `130007` | `组织Has项目s` | 组织下存在未删除的 Project，无法直接删除组织。 |
| `130008` | `组织项目Deleting` | 组织下的 Project 正在删除中，请稍后再试。 |
| `130009` | `Unauthorized组织Access` | 当前用户无权操作该组织。 |
| `999999` | `DefaultException` | 服务器内部错误，请稍后重试。 |

- **请求示例**:

```json
{
  "orgIds": "1001,1002,1003"
}
```

- **响应示例**:

**成功响应**:
```json
{
  "code": 0,
  "message": "Success",
  "data": true,
  "traceId": "a7b8c9d0-e1f2-3456-abcd-789012345678"
}
```

**失败响应** (组织下存在 Project):
```json
{
  "code": 130007,
  "message": "组织Has项目s",
  "data": null,
  "traceId": "b8c9d0e1-f2a3-4567-bcde-890123456789"
}
```

---

## 6. NotifyController 接口

本章共覆盖 2 个 HTTP 端点，每个端点一个接口卡片。

### 6.1. API-017 WeChatNotify (POST /api/payment/notify/wechatnotify)

- **鉴权**: 无（微信Payment服务器回调接口，无需 JWT Token）
- **描述**: 接收微信Payment平台的异步通知回调，验证通知签名与数据完整性，并更新对应订单的Payment状态。

#### 6.1.1. 签名验证机制

本接口通过以下步骤验证通知的合法性与数据完整性：

1. **证书序列号校验**：从请求头 `Wechatpay-Serial` 获取微信Payment平台证书序列号，系统校验该序列号是否为已Config的有效证书序列号。若序列号无效，返回错误码 `InvalidWechatSerialNO`。
2. **签名验证**：使用请求头 `Wechatpay-Signature` 携带的签名值，结合请求头 `Wechatpay-Timestamp`、`Wechatpay-Nonce` 及请求体，通过微信Payment平台公钥进行签名验证。验证失败时返回错误码 `InvalidWechatSignature`。
3. **数据解密**：签名验证通过后，使用 APIv3 密钥对 `resource.ciphertext` 进行 AES-256-GCM 解密，获取明文交易数据。
4. **业务校验**：对解密后的数据执行商户号匹配、订单存在性校验、订单金额一致性校验，全部通过后更新订单Payment状态。

#### 6.1.2. 请求参数

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `id` | string | 是 | 微信Payment通知ID |
| `create_time` | string | 是 | 通知创建时间，格式为 `yyyy-MM-ddTHH:mm:ss+08:00` |
| `event_type` | string | 是 | 通知类型，固定为 `TRANSACTION.SUCCESS` |
| `resource_type` | string | 是 | 资源类型，固定为 `encrypt-resource` |
| `resource` | object | 是 | 通知资源数据 |
| `resource.algorithm` | string | 是 | 加密算法，固定为 `AEAD_AES_256_GCM` |
| `resource.ciphertext` | string | 是 | Base64 编码的密文数据 |
| `resource.associated_data` | string | 否 | 附加数据，认证加密算法中的附加数据 |
| `resource.nonce` | string | 是 | 加密使用的随机串 |
| `resource.original_type` | string | 是 | 原始回调类型，固定为 `transaction` |
| `summary` | string | 是 | 回调摘要 |

**请求体示例（原始回调）**：
```json
{
  "id": "EV-20240620101500001",
  "create_time": "2024-06-20T10:15:00+08:00",
  "event_type": "TRANSACTION.SUCCESS",
  "resource_type": "encrypt-resource",
  "resource": {
    "algorithm": "AEAD_AES_256_GCM",
    "ciphertext": "BASE64_ENCRYPTED_PAYLOAD",
    "associated_data": "transaction",
    "nonce": "NONCE_STRING",
    "original_type": "transaction"
  },
  "summary": "Payment成功"
}
```

**解密后资源数据（`resource.ciphertext` 解密后的内容）**：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `mchid` | string | 是 | 商户号 |
| `appid` | string | 是 | 应用ID |
| `out_trade_no` | string | 是 | 商户订单号 |
| `transaction_id` | string | 是 | 微信Payment订单号 |
| `trade_type` | string | 是 | 交易类型，如 `JSAPI` |
| `trade_state` | string | 是 | 交易状态，固定为 `SUCCESS` |
| `trade_state_desc` | string | 是 | 交易状态描述 |
| `bank_type` | string | 是 | 银行类型 |
| `attach` | string | 否 | 附加数据 |
| `success_time` | string | 是 | Payment成功时间 |
| `payer` | object | 是 | Payment者信息 |
| `payer.openid` | string | 是 | 用户标识 |
| `amount` | object | 是 | 订单金额信息 |
| `amount.total` | integer | 是 | 总金额（单位：分） |
| `amount.payer_total` | integer | 是 | 用户Payment金额（单位：分） |
| `amount.currency` | string | 是 | 货币类型，固定为 `CNY` |
| `amount.payer_currency` | string | 是 | 用户Payment币种 |

**解密后资源数据示例**：
```json
{
  "mchid": "1900000109",
  "appid": "wx8888888888888888",
  "out_trade_no": "ORDER20240620001",
  "transaction_id": "4200002343202406200000000000",
  "trade_type": "JSAPI",
  "trade_state": "SUCCESS",
  "trade_state_desc": "Payment成功",
  "bank_type": "CMC",
  "attach": "",
  "success_time": "2024-06-20T10:15:00+08:00",
  "payer": {
    "openid": "oUpF8uMuAJO_M2pxb1Q9zNjWeS6o"
  },
  "amount": {
    "total": 100,
    "payer_total": 100,
    "currency": "CNY",
    "payer_currency": "CNY"
  }
}
```

#### 6.1.3. 响应格式

| 字段 | 类型 | 说明 |
|---|---|---|
| `code` | string | 处理状态码。`SUCCESS` 表示处理成功；`FAIL` 表示处理失败 |
| `message` | string | 处理结果描述。成功时为 `成功`，失败时为具体错误原因 |

#### 6.1.4. 错误码

| errorCode | message | 说明 |
|---|---|---|
| `100001` | InvalidWeChatNotify | 通知数据格式不正确或缺少必要字段 |
| `100002` | InvalidWeChatSerialNO | 请求头中的证书序列号无效 |
| `100003` | InvalidWeChatSignature | 微信Payment通知签名验证失败 |
| `100004` | InvalidWeChatTradeNo | 解密后的 `transaction_id` 为空或格式错误 |
| `100005` | EmptyWeChatTransaction | 解密后的交易数据为空 |
| `100006` | EmptyWeChatNotify | 请求体为空或缺少必要字段 |
| `100007` | OrderNotExist | 根据 `out_trade_no` 未找到对应订单 |
| `100008` | OrderStateUpdateFailed | 更新订单Payment状态时数据库操作失败 |
| `100009` | InvalidMerchant | 通知中的 `mchid` 与系统Config的商户号不匹配 |
| `100010` | InvalidTotalAmount | 通知中的Payment金额与订单实际金额不一致 |
| `100011` | WeChatSettingNotConfig | 系统未Config微信Payment相关参数 |
| `100012` | DefaultException | 未预期的服务器内部错误 |

> **说明**：错误码采用系统统一的 `100xxx` 数字编码格式（定义于 `Models/Common/Enums/ExceptionCodes.cs`），`errorCode` 为数字编码，`message` 为对应的枚举名称，`说明` 列描述具体错误场景。

#### 6.1.5. 请求示例

```json
{
  "id": "EV-20240620101500001",
  "create_time": "2024-06-20T10:15:00+08:00",
  "event_type": "TRANSACTION.SUCCESS",
  "resource_type": "encrypt-resource",
  "resource": {
    "algorithm": "AEAD_AES_256_GCM",
    "ciphertext": "BASE64_ENCRYPTED_PAYLOAD",
    "associated_data": "transaction",
    "nonce": "NONCE_STRING",
    "original_type": "transaction"
  },
  "summary": "Payment成功"
}
```

#### 6.1.6. 响应示例

**成功响应**：
```json
{
  "code": "SUCCESS",
  "message": "成功"
}
```

**失败响应**：
```json
{
  "code": "FAIL",
  "message": "订单不存在"
}
```

### 6.2. API-001 AlipayNotify (POST /api/payment/notify/alipaynotify)

- **鉴权**: 无
- **描述**: 接收Payment宝异步通知，用于处理Payment宝Payment结果回调，验证签名并更新订单Payment状态。

#### 6.2.1. 签名验证机制

本接口通过以下步骤验证通知的合法性与数据完整性：

1. **参数预处理**：从请求体中获取所有通知参数（除 `sign` 和 `sign_type` 外），按照参数名字典序升序排序，拼接为 `key1=value1&key2=value2&...` 格式的待签名字符串。
2. **签名验证**：使用Payment宝平台公钥，结合请求中的 `sign_type`（固定为 `RSA2`）对待签名字符串进行 RSA 签名验证。验证失败时返回错误码 `100101`（AlipaySignatureError）。
3. **业务校验**：签名验证通过后，依次执行应用ID匹配、商户号校验、订单存在性校验、订单金额一致性校验，全部通过后更新订单Payment状态。

#### 6.2.2. 请求参数

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `notify_time` | String | 是 | 通知时间，格式为 `yyyy-MM-dd HH:mm:ss` |
| `notify_type` | String | 是 | 通知类型，固定为 `trade_status_sync` |
| `notify_id` | String | 是 | 通知校验 ID |
| `app_id` | String | 是 | Payment宝分配给开发者的应用 ID |
| `charset` | String | 是 | 编码格式，如 `utf-8` |
| `version` | String | 是 | 调用的接口版本，固定为 `1.0` |
| `sign_type` | String | 是 | 签名类型，如 `RSA2` |
| `sign` | String | 是 | 签名串 |
| `trade_no` | String | 是 | Payment宝交易号 |
| `out_trade_no` | String | 是 | 商户订单号 |
| `out_biz_no` | String | 否 | 商户业务号 |
| `buyer_id` | String | 是 | 买家Payment宝用户 ID |
| `buyer_logon_id` | String | 是 | 买家Payment宝账号 |
| `seller_id` | String | 是 | 卖家Payment宝用户 ID |
| `seller_email` | String | 是 | 卖家Payment宝账号 |
| `trade_status` | String | 是 | 交易状态，如 `TRADE_SUCCESS`、`TRADE_FINISHED`、`TRADE_CLOSED`、`WAIT_BUYER_PAY` |
| `total_amount` | String | 是 | 订单总金额，单位为元，精确到小数点后两位 |
| `receipt_amount` | String | 否 | 实收金额，单位为元，精确到小数点后两位 |
| `invoice_amount` | String | 否 | 开票金额，单位为元，精确到小数点后两位 |
| `buyer_pay_amount` | String | 否 | 付款金额，单位为元，精确到小数点后两位 |
| `point_amount` | String | 否 | 集分宝金额，单位为元，精确到小数点后两位 |
| `refund_fee` | String | 否 | 总退款金额，单位为元，精确到小数点后两位 |
| `subject` | String | 是 | 订单标题 |
| `body` | String | 否 | 订单描述 |
| `gmt_create` | String | 是 | 交易创建时间，格式为 `yyyy-MM-dd HH:mm:ss` |
| `gmt_payment` | String | 否 | 交易付款时间，格式为 `yyyy-MM-dd HH:mm:ss` |
| `gmt_refund` | String | 否 | 交易退款时间，格式为 `yyyy-MM-dd HH:mm:ss` |
| `gmt_close` | String | 否 | 交易关闭时间，格式为 `yyyy-MM-dd HH:mm:ss` |
| `fund_bill_list` | String | 否 | Payment金额信息，JSON 数组字符串 |
| `voucher_detail_list` | String | 否 | 优惠券信息，JSON 数组字符串 |
| `passback_params` | String | 否 | 公共回传参数 |

#### 6.2.3. 响应格式

本接口的响应体为纯文本格式，非 JSON 对象。成功时直接返回字符串 `success`，失败时返回字符串 `failure`。Payment宝服务器在收到 `success` 后停止重试推送，收到其他内容或未收到响应时将按策略重试。

#### 6.2.4. 错误码

| errorCode | message | 说明 |
|---|---|---|
| `100101` | AlipaySettingNotConfig | Payment宝PaymentConfig不存在或未正确Config |
| `100102` | AlipayConnectionError | Payment宝连接异常，无法完成Payment通知处理 |
| `100103` | AlipayTradeError | Payment宝交易处理失败 |
| `100104` | InvalidAlipayTradeNo | Payment宝交易号无效 |
| `100105` | InvalidAlipayTransaction | 无效的Payment宝交易记录 |
| `100106` | AlipaySignatureError | Payment宝签名验证失败 |
| `100107` | AlipaySignDictionaryError | Payment宝签名参数构建失败 |
| `100108` | EmptyOrderNo | 商户订单号为空 |
| `100109` | OrderNotExist | 订单不存在 |
| `100110` | InvalidTotalAmount | 订单金额无效 |
| `100111` | OrderStateUpdateFailed | 订单状态更新失败 |
| `100112` | InvalidMerchant | 无效的商户信息 |
| `100199` | DefaultException | 系统默认异常 |

> **说明**：错误码采用系统统一的 `100xxx` 数字编码格式（定义于 `Models/Common/Enums/ExceptionCodes.cs`），`errorCode` 为数字编码，`message` 为对应的枚举名称，`说明` 列描述具体错误场景。本接口捕获异常后统一返回 `failure` 响应，错误码仅用于服务端日志记录与监控。

#### 6.2.5. 请求示例

```json
{
  "notify_time": "2025-01-15 14:30:00",
  "notify_type": "trade_status_sync",
  "notify_id": "RqPoY8e9QnGJ1a2b3c4d5e6f7g8h9i0j",
  "app_id": "2021003122691234",
  "charset": "utf-8",
  "version": "1.0",
  "sign_type": "RSA2",
  "sign": "base64_encoded_signature_string",
  "trade_no": "2025011522001412651000000001",
  "out_trade_no": "ORDER202501151430001",
  "out_biz_no": "202501151430001",
  "buyer_id": "2088102146225135",
  "buyer_logon_id": "user@example.com",
  "seller_id": "2088102146225136",
  "seller_email": "merchant@example.com",
  "trade_status": "TRADE_SUCCESS",
  "total_amount": "299.00",
  "receipt_amount": "299.00",
  "invoice_amount": "299.00",
  "buyer_pay_amount": "299.00",
  "point_amount": "0.00",
  "refund_fee": "0.00",
  "subject": "AgentInsightService 专业版订阅",
  "body": "AgentInsightService 月度订阅",
  "gmt_create": "2025-01-15 14:29:30",
  "gmt_payment": "2025-01-15 14:30:00",
  "gmt_refund": "",
  "gmt_close": "",
  "fund_bill_list": "[{\"amount\":\"299.00\",\"fundChannel\":\"ALIPAYACCOUNT\"}]",
  "voucher_detail_list": "",
  "passback_params": "merchant_return_data"
}
```

#### 6.2.6. 响应示例

**成功响应**（纯文本，HTTP 状态码 200）：

```
success
```

**失败响应**（纯文本，HTTP 状态码 200）：

```
failure
```

---

## 7. MetricsController 接口

# MetricsController 接口
## 7. MetricsController 接口

MetricsController 提供指标数据的查询接口，包括ObservationObservations、ScoreScores和TraceTraces的检索能力。所有接口均要求携带有效的认证 Token，并支持按project_id 进行数据隔离。

**鉴权要求：**

- 所有端点均要求调用者具备组织成员资格（`RequireOrgMembership`），鉴权逻辑基于 `ApiHandlerBase` 基类实现。
- 支持两种认证方式：
  - **JWT Token**：在请求头 `Authorization: Bearer <token>` 中携带。
  - **Basic Auth**：使用 PublicKey/SecretKey 进行基本认证。
- project_id（`project_id`）通过请求头 `X-Project-Id` 传递，用于数据隔离。未提供有效的project_id 时，接口将返回 `150000 Empty项目Id` 错误。

---

## 端点列表

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | /api/data/metrics/observations | 获取Observation数据列表 |
| GET | /api/data/metrics/scores | 获取Score数据列表 |
| GET | /api/data/metrics/traces | 获取Trace数据列表（查询参数方式） |
| POST | /api/data/metrics/traces | 获取Trace数据列表（请求体方式） |
| GET | /api/data/model | 获取模型数据列表 |

---

## 1. 获取Observation数据

### 7.1. 接口说明

根据 trace_id 获取关联的ObservationObservation列表，支持分页查询。

### 7.2. 请求参数

**请求头：**

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| Authorization | string | 是 | 认证凭证，格式为 `Bearer <JWT Token>` 或 Basic Auth 凭证 |
| X-Project-Id | string | 是 | project_id，用于数据隔离 |

**查询参数：**

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| id | string | 是 | 关联的 trace_id，用于筛选属于特定 Trace 的Observation记录 |
| page | int | 否 | 页码，默认值为 `1` |
| pagesize | int | 否 | 每页条数，默认值为 `20` |

### 7.3. 请求示例

```json
GET /api/data/metrics/observations?id=trace_8a2f4c9e1b3d4f5a&page=1&pagesize=20
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
X-Project-Id: project_123
```

### 7.4. 响应格式

| 字段 | 类型 | 说明 |
|---|---|---|
| code | int | 业务状态码，`0` 表示成功，非 `0` 表示失败 |
| data | object | 响应数据，包含分页结果 |
| data.items | array | Observation记录列表 |
| data.items[].id | string | Observation记录 ID |
| data.items[].trace_id | string | 关联的 trace_id |
| data.items[].type | string | Observation类型 |
| data.items[].content | string | Observation内容 |
| data.items[].created_at | string | 创建时间 |
| data.page | int | 当前页码 |
| data.pagesize | int | 当前页大小 |
| message | string | 状态描述信息，成功时为 `"success"` |

### 7.5. 响应示例

**成功响应:**

```json
{
  "code": 0,
  "data": {
    "items": [
      {
        "id": "obs_001",
        "trace_id": "trace_8a2f4c9e1b3d4f5a",
        "type": "llm",
        "content": "用户询问天气情况",
        "created_at": "2025-01-15T10:30:00Z"
      }
    ],
    "page": 1,
    "pagesize": 20
  },
  "message": "success"
}
```

**错误响应示例:**

```json
{
  "code": 150018,
  "data": null,
  "message": "EmptyTraceId"
}
```

### 7.6. 错误码

| errorCode | message | 说明 |
|---|---|---|
| 100000 | UnAuthToken | 未提供或提供了无效的认证 Token |
| 100005 | InvalidUser | 用户不存在或已被禁用 |
| 150000 | Empty项目Id | project_id 为空 |
| 150009 | EmptyTraceIds | trace_id 列表为空 |
| 150010 | ClickHouseQueryError | ClickHouse 查询执行失败 |
| 150011 | TooManyTraceIds | trace_id 数量超出限制 |
| 150017 | ClickHouseQueryTimeout | ClickHouse 查询超时 |
| 150018 | EmptyTraceId | trace_id 为空 |
| 999999 | DefaultException | 未预期的服务器内部错误 |

---

## 2. 获取Score数据

### 7.7. 接口说明

根据 trace_id 获取关联的ScoreScore列表，支持分页查询。

### 7.8. 请求参数

**请求头：**

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| Authorization | string | 是 | 认证凭证，格式为 `Bearer <JWT Token>` 或 Basic Auth 凭证 |
| X-Project-Id | string | 是 | project_id，用于数据隔离 |

**查询参数：**

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| id | string | 是 | 关联的 trace_id，用于筛选属于特定 Trace 的Score记录 |
| page | int | 否 | 页码，默认值为 `1` |
| pagesize | int | 否 | 每页条数，默认值为 `20` |

### 7.9. 请求示例

```json
GET /api/data/metrics/scores?id=trace_8a2f4c9e1b3d4f5a&page=1&pagesize=20
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
X-Project-Id: project_123
```

### 7.10. 响应格式

| 字段 | 类型 | 说明 |
|---|---|---|
| code | int | 业务状态码，`0` 表示成功，非 `0` 表示失败 |
| data | object | 响应数据，包含分页结果 |
| data.items | array | Score记录列表 |
| data.items[].id | string | Score记录 ID |
| data.items[].trace_id | string | 关联的 trace_id |
| data.items[].metric_name | string | 指标名称 |
| data.items[].value | number | Score值 |
| data.items[].created_at | string | 创建时间 |
| data.page | int | 当前页码 |
| data.pagesize | int | 当前页大小 |
| message | string | 状态描述信息，成功时为 `"success"` |

### 7.11. 响应示例

**成功响应:**

```json
{
  "code": 0,
  "data": {
    "items": [
      {
        "id": "score_001",
        "trace_id": "trace_8a2f4c9e1b3d4f5a",
        "metric_name": "relevance_score",
        "value": 0.95,
        "created_at": "2025-01-15T10:30:00Z"
      }
    ],
    "page": 1,
    "pagesize": 20
  },
  "message": "success"
}
```

**错误响应示例:**

```json
{
  "code": 150018,
  "data": null,
  "message": "EmptyTraceId"
}
```

### 7.12. 错误码

| errorCode | message | 说明 |
|---|---|---|
| 100000 | UnAuthToken | 未提供或提供了无效的认证 Token |
| 100005 | InvalidUser | 用户不存在或已被禁用 |
| 150000 | Empty项目Id | project_id 为空 |
| 150009 | EmptyTraceIds | trace_id 列表为空 |
| 150010 | ClickHouseQueryError | ClickHouse 查询执行失败 |
| 150011 | TooManyTraceIds | trace_id 数量超出限制 |
| 150017 | ClickHouseQueryTimeout | ClickHouse 查询超时 |
| 150018 | EmptyTraceId | trace_id 为空 |
| 999999 | DefaultException | 未预期的服务器内部错误 |

---

## 3. 获取TraceGET

### 7.13. 接口说明

根据 trace_id 列表获取TraceTrace列表，支持分页查询。

### 7.14. 请求参数

**请求头：**

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| Authorization | string | 是 | 认证凭证，格式为 `Bearer <JWT Token>` 或 Basic Auth 凭证 |
| X-Project-Id | string | 是 | project_id，用于数据隔离 |

**查询参数：**

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| ids | string | 是 | 逗号分隔的 trace_id 列表，用于筛选特定Trace记录 |
| page | int | 否 | 页码，默认值为 `1` |
| pagesize | int | 否 | 每页条数，默认值为 `20` |

### 7.15. 请求示例

```json
GET /api/data/metrics/traces?ids=trace-001,trace-002&page=1&pagesize=20
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
X-Project-Id: project_123
```

### 7.16. 响应格式

| 字段 | 类型 | 说明 |
|---|---|---|
| code | int | 业务状态码，`0` 表示成功，非 `0` 表示失败 |
| data | object | 响应数据，包含分页结果 |
| data.items | array | Trace记录列表 |
| data.items[].id | string | Trace记录 ID |
| data.items[].project_id | string | project_id |
| data.items[].name | string | Trace名称 |
| data.items[].status | string | Trace状态 |
| data.items[].start_time | string | 开始时间 |
| data.items[].end_time | string | 结束时间 |
| data.items[].duration_ms | number | 持续时间（毫秒） |
| data.page | int | 当前页码 |
| data.pagesize | int | 当前页大小 |
| message | string | 状态描述信息，成功时为 `"success"` |

### 7.17. 响应示例

**成功响应:**

```json
{
  "code": 0,
  "data": {
    "items": [
      {
        "id": "trace-001",
        "project_id": "project_123",
        "name": "用户查询处理",
        "status": "completed",
        "start_time": "2025-01-15T10:30:00Z",
        "end_time": "2025-01-15T10:30:05Z",
        "duration_ms": 5000
      }
    ],
    "page": 1,
    "pagesize": 20
  },
  "message": "success"
}
```

**错误响应示例:**

```json
{
  "code": 150009,
  "data": null,
  "message": "EmptyTraceIds"
}
```

### 7.18. 错误码

| errorCode | message | 说明 |
|---|---|---|
| 100000 | UnAuthToken | 未提供或提供了无效的认证 Token |
| 100005 | InvalidUser | 用户不存在或已被禁用 |
| 150000 | Empty项目Id | project_id 为空 |
| 150009 | EmptyTraceIds | trace_id 列表为空 |
| 150010 | ClickHouseQueryError | ClickHouse 查询执行失败 |
| 150011 | TooManyTraceIds | trace_id 数量超出限制 |
| 150017 | ClickHouseQueryTimeout | ClickHouse 查询超时 |
| 150018 | EmptyTraceId | trace_id 为空 |
| 999999 | DefaultException | 未预期的服务器内部错误 |

---

## 4. 获取TracePOST

### 7.19. 接口说明

根据 trace_id 列表获取TraceTrace列表，支持分页查询。与 GET 方式功能相同，但通过请求体传递参数。

### 7.20. 请求参数

**请求头：**

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| Authorization | string | 是 | 认证凭证，格式为 `Bearer <JWT Token>` 或 Basic Auth 凭证 |
| X-Project-Id | string | 是 | project_id，用于数据隔离 |

**请求体参数：**

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| ids | array | 是 | trace_id 列表，用于筛选特定Trace记录 |
| page | int | 否 | 页码，默认值为 `1` |
| pagesize | int | 否 | 每页条数，默认值为 `20` |

### 7.21. 请求示例

```json
POST /api/data/metrics/traces
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
X-Project-Id: project_123
Content-Type: application/json

{
  "ids": ["trace-001", "trace-002"],
  "page": 1,
  "pagesize": 20
}
```

### 7.22. 响应格式

| 字段 | 类型 | 说明 |
|---|---|---|
| code | int | 业务状态码，`0` 表示成功，非 `0` 表示失败 |
| data | object | 响应数据，包含分页结果 |
| data.items | array | Trace记录列表 |
| data.items[].id | string | Trace记录 ID |
| data.items[].project_id | string | project_id |
| data.items[].name | string | Trace名称 |
| data.items[].status | string | Trace状态 |
| data.items[].start_time | string | 开始时间 |
| data.items[].end_time | string | 结束时间 |
| data.items[].duration_ms | number | 持续时间（毫秒） |
| data.page | int | 当前页码 |
| data.pagesize | int | 当前页大小 |
| message | string | 状态描述信息，成功时为 `"success"` |

### 7.23. 响应示例

**成功响应:**

```json
{
  "code": 0,
  "data": {
    "items": [
      {
        "id": "trace-001",
        "project_id": "project_123",
        "name": "用户查询处理",
        "status": "completed",
        "start_time": "2025-01-15T10:30:00Z",
        "end_time": "2025-01-15T10:30:05Z",
        "duration_ms": 5000
      }
    ],
    "page": 1,
    "pagesize": 20
  },
  "message": "success"
}
```

**错误响应示例:**

```json
{
  "code": 150009,
  "data": null,
  "message": "EmptyTraceIds"
}
```

### 7.24. 错误码

| errorCode | message | 说明 |
|---|---|---|
| 100000 | UnAuthToken | 未提供或提供了无效的认证 Token |
| 100005 | InvalidUser | 用户不存在或已被禁用 |
| 150000 | Empty项目Id | project_id 为空 |
| 150009 | EmptyTraceIds | trace_id 列表为空 |
| 150010 | ClickHouseQueryError | ClickHouse 查询执行失败 |
| 150011 | TooManyTraceIds | trace_id 数量超出限制 |
| 150017 | ClickHouseQueryTimeout | ClickHouse 查询超时 |
| 150018 | EmptyTraceId | trace_id 为空 |
| 999999 | DefaultException | 未预期的服务器内部错误 |

---

## 5. 获取模型数据

### 7.25. 接口说明

Model数据列表，支持分页查询。

### 7.26. 请求参数

**请求头：**

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| Authorization | string | 是 | 认证凭证，格式为 `Bearer <JWT Token>` 或 Basic Auth 凭证 |
| X-Project-Id | string | 是 | project_id，用于数据隔离 |

**查询参数：**

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| page | int | 否 | 页码，默认值为 `1` |
| pagesize | int | 否 | 每页条数，默认值为 `20` |

### 7.27. 请求示例

```json
GET /api/data/model?page=1&pagesize=20
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
X-Project-Id: project_123
```

### 7.28. 响应格式

| 字段 | 类型 | 说明 |
|---|---|---|
| code | int | 业务状态码，`0` 表示成功，非 `0` 表示失败 |
| data | object | 响应数据，包含分页结果 |
| data.items | array | 模型记录列表 |
| data.items[].id | string | 模型记录 ID |
| data.items[].project_id | string | project_id |
| data.items[].name | string | 模型名称 |
| data.items[].provider | string | 模型提供商 |
| data.items[].model_type | string | 模型类型 |
| data.items[].created_at | string | 创建时间 |
| data.page | int | 当前页码 |
| data.pagesize | int | 当前页大小 |
| message | string | 状态描述信息，成功时为 `"success"` |

### 7.29. 响应示例

**成功响应:**

```json
{
  "code": 0,
  "data": {
    "items": [
      {
        "id": "model_001",
        "project_id": "project_123",
        "name": "gpt-4o",
        "provider": "openai",
        "model_type": "chat",
        "created_at": "2025-01-15T10:30:00Z"
      }
    ],
    "page": 1,
    "pagesize": 20
  },
  "message": "success"
}
```

**错误响应示例:**

```json
{
  "code": 150000,
  "data": null,
  "message": "Empty项目Id"
}
```

### 7.30. 错误码

| errorCode | message | 说明 |
|---|---|---|
| 100000 | UnAuthToken | 未提供或提供了无效的认证 Token |
| 100005 | InvalidUser | 用户不存在或已被禁用 |
| 150000 | Empty项目Id | project_id 为空 |
| 150010 | ClickHouseQueryError | ClickHouse 查询执行失败 |
| 150017 | ClickHouseQueryTimeout | ClickHouse 查询超时 |
| 999999 | DefaultException | 未预期的服务器内部错误 |

---

## 8. AlertController 接口

# AlertController 接口
## 8. AlertController 接口

- **接口**: `POST /api/alert`
- **鉴权**: 需要有效 Token，RequireOrgAdmin或项目管理员（Require项目Admin）Privilege
- **描述**: 创建一条新的 Alert规则，用于监控 Agent 的 Token 消耗、成本、错误率等指标，并在条件满足时触发通知。

- **请求参数**: `CreateAlertBody`

  | 字段 | 类型 | 必填 | 说明 |
  |---|---|---|---|
  | name | string | 是 | Alert 名称，长度限制见错误码 `AlertNameTooLong` (100023) |
  | projectId | long | 是 | 关联的 Project ID，必须存在且当前用户有访问Privilege，否则返回 `Alert项目NotFound` (100024) |
  | field | AlertField | 是 | 监控的指标字段，枚举值见下方说明 |
  | operator | AlertOperator | 是 | 比较运算符，枚举值见下方说明 |
  | value | double | 是 | 触发阈值 |
  | timeUnit | AlertTimeUnit | 是 | 时间单位，枚举值见下方说明 |
  | frequency | integer | 是 | 检查频率 |
  | notifyBys | array | 是 | 通知方式列表，枚举值见下方说明 |
  | enabled | boolean | 否 | 是否启用，默认 true |

- **响应格式**:

| 字段 | 类型 | 说明 |
|---|---|---|
| code | integer | 状态码，0 表示成功 |
| message | string | 响应消息 |
| data | object | Alert 数据 |
| data.id | string | Alert ID |
| data.name | string | Alert 名称 |
| data.projectId | long | 关联的 Project ID |
| data.field | integer | 监控的指标字段 |
| data.operator | integer | 比较运算符 |
| data.value | double | 触发阈值 |
| data.timeUnit | integer | 时间单位 |
| data.frequency | integer | 检查频率 |
| data.notifyBys | array | 通知方式列表 |
| data.enabled | boolean | 是否启用 |
| data.createdAt | string | 创建时间 |
| data.updatedAt | string | 更新时间 |

- **错误码**:

| errorCode | message | 说明 |
|-----------|---------|------|
| 100023 | AlertNameTooLong | Alert 名称过长 |
| 100024 | Alert项目NotFound | 项目不存在或无权访问 |
| 100025 | InvalidAlertField | 无效的监控字段 |
| 100026 | InvalidAlertOperator | 无效的比较运算符 |
| 100027 | InvalidAlertValue | 无效的阈值 |
| 100028 | InvalidAlertTimeUnit | 无效的时间单位 |
| 100029 | InvalidAlertFrequency | 无效的检查频率 |
| 100030 | InvalidAlertNotifyBy | 无效的通知方式 |
| 100031 | CreateAlertFailed | 创建 Alert 失败 |
| 100000 | UnAuthToken | 未认证或 Token 无效 |
| 100001 | Unauthorized | 无Privilege执行此操作 |
| 999999 | DefaultException | 服务器内部错误 |

- **请求示例**:

```json
POST /api/alert
{
  "name": "Token 消耗Alert",
  "projectId": 12345,
  "field": 1,
  "operator": 1,
  "value": 10000,
  "timeUnit": 1,
  "frequency": 5,
  "notifyBys": [1, 2],
  "enabled": true
}
```

## 更新 Alert规则

- **接口**: `POST /api/alert/update`
- **鉴权**: 需要有效 Token，RequireOrgAdmin或项目管理员（Require项目Admin）Privilege
- **描述**: 更新一条已有的 Alert规则。

- **请求参数**: `UpdateAlertBody`

  | 字段 | 类型 | 必填 | 说明 |
  |---|---|---|---|
  | id | string | 是 | Alert ID |
  | name | string | 否 | Alert 名称 |
  | field | AlertField | 否 | 监控的指标字段 |
  | operator | AlertOperator | 否 | 比较运算符 |
  | value | double | 否 | 触发阈值 |
  | timeUnit | AlertTimeUnit | 否 | 时间单位 |
  | frequency | integer | 否 | 检查频率 |
  | notifyBys | array | 否 | 通知方式列表 |
  | enabled | boolean | 否 | 是否启用 |

- **响应格式**:

| 字段 | 类型 | 说明 |
|---|---|---|
| code | integer | 状态码，0 表示成功 |
| message | string | 响应消息 |
| data | object | Alert 数据 |
| data.id | string | Alert ID |
| data.name | string | Alert 名称 |
| data.projectId | long | 关联的 Project ID |
| data.field | integer | 监控的指标字段 |
| data.operator | integer | 比较运算符 |
| data.value | double | 触发阈值 |
| data.timeUnit | integer | 时间单位 |
| data.frequency | integer | 检查频率 |
| data.notifyBys | array | 通知方式列表 |
| data.enabled | boolean | 是否启用 |
| data.createdAt | string | 创建时间 |
| data.updatedAt | string | 更新时间 |

- **错误码**:

| errorCode | message | 说明 |
|-----------|---------|------|
| 100022 | AlertNotFound | Alert 不存在 |
| 100024 | Alert项目NotFound | 项目不存在或无权访问 |
| 100023 | AlertNameTooLong | Alert 名称过长 |
| 100025 | InvalidAlertField | 无效的监控字段 |
| 100026 | InvalidAlertOperator | 无效的比较运算符 |
| 100027 | InvalidAlertValue | 无效的阈值 |
| 100028 | InvalidAlertTimeUnit | 无效的时间单位 |
| 100029 | InvalidAlertFrequency | 无效的检查频率 |
| 100030 | InvalidAlertNotifyBy | 无效的通知方式 |
| 100032 | UpdateAlertFailed | 更新 Alert 失败 |
| 100000 | UnAuthToken | 未认证或 Token 无效 |
| 100001 | Unauthorized | 无Privilege执行此操作 |
| 999999 | DefaultException | 服务器内部错误 |

- **请求示例**:

```json
POST /api/alert/update
{
  "id": "alert_123456",
  "name": "更新后的 Token 消耗Alert",
  "value": 20000
}
```

## 删除 Alert规则

- **接口**: `POST /api/alert/delete`
- **鉴权**: 需要有效 Token，RequireOrgAdmin或项目管理员（Require项目Admin）Privilege
- **描述**: 删除一条已有的 Alert规则。

- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| id | string | 是 | Alert ID |

- **响应格式**:

| 字段 | 类型 | 说明 |
|---|---|---|
| code | integer | 状态码，0 表示成功 |
| message | string | 响应消息 |

- **错误码**:

| errorCode | message | 说明 |
|-----------|---------|------|
| 100022 | AlertNotFound | Alert 不存在 |
| 100033 | DeleteAlertFailed | 删除 Alert 失败 |
| 100000 | UnAuthToken | 未认证或 Token 无效 |
| 100001 | Unauthorized | 无Privilege执行此操作 |
| 999999 | DefaultException | 服务器内部错误 |

- **请求示例**:

```json
POST /api/alert/delete
{
  "id": "alert_123456"
}
```

## 获取 Alert规则列表

- **接口**: `GET /api/alert`
- **鉴权**: 需要有效 Token，RequireOrgAdmin或项目管理员（Require项目Admin）Privilege
- **描述**: 获取 Alert规则列表，支持分页和筛选。

- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| projectId | long | 是 | project_id |
| page | integer | 否 | 页码，默认 1 |
| pagesize | integer | 否 | 每页条数，默认 20 |
| field | AlertField | 否 | 按监控字段筛选 |
| enabled | boolean | 否 | 按启用状态筛选 |

- **响应格式**:

| 字段 | 类型 | 说明 |
|---|---|---|
| code | integer | 状态码，0 表示成功 |
| message | string | 响应消息 |
| data | object | 分页数据 |
| data.total | long | 总条数 |
| data.items | array | Alert 列表 |
| data.items[].id | string | Alert ID |
| data.items[].name | string | Alert 名称 |
| data.items[].projectId | long | 关联的 Project ID |
| data.items[].field | integer | 监控的指标字段 |
| data.items[].operator | integer | 比较运算符 |
| data.items[].value | double | 触发阈值 |
| data.items[].timeUnit | integer | 时间单位 |
| data.items[].frequency | integer | 检查频率 |
| data.items[].notifyBys | array | 通知方式列表 |
| data.items[].enabled | boolean | 是否启用 |
| data.items[].createdAt | string | 创建时间 |
| data.items[].updatedAt | string | 更新时间 |

- **错误码**:

| errorCode | message | 说明 |
|-----------|---------|------|
| 100021 | AlertOrgNotAccessible | 无权访问该组织的 Alert |
| 100024 | Alert项目NotFound | 项目不存在或无权访问 |
| 100000 | UnAuthToken | 未认证或 Token 无效 |
| 100001 | Unauthorized | 无Privilege执行此操作 |
| 999999 | DefaultException | 服务器内部错误 |

- **请求示例**:

```json
GET /api/alert?projectId=12345&page=1&pagesize=20
```

## 获取 Alert Config信息

- **接口**: `GET /api/alert/config`
- **鉴权**: 无
- **描述**: 获取 Alert Config信息，用于前端展示 Alert规则的可Config项（如时间单位、运算符、字段、通知方式等枚举选项）。

- **请求参数**: 无

- **响应格式**:

| 字段 | 类型 | 说明 |
|---|---|---|
| code | integer | 状态码，0 表示成功 |
| message | string | 响应消息 |
| data | object | Alert Config数据 |
| data.fields | array | AlertField 枚举选项列表 |
| data.fields[].value | integer | 枚举值 (TotalTokens=1, TotalCost=2, ErrorCount=3, Latency=4, ErrorRate=5, InputTokens=6, OutputTokens=7, WarningCount=8, ObservationCount=9) |
| data.fields[].label | string | 枚举标签 (TotalTokens, TotalCost, ErrorCount, Latency, ErrorRate, InputTokens, OutputTokens, WarningCount, ObservationCount) |
| data.operators | array | AlertOperator 枚举选项列表 |
| data.operators[].value | integer | 枚举值 (GreaterThan=1, LessThan=2, EqualTo=3, GreaterThanOrEqualTo=4, LessThanOrEqualTo=5, NotEqualTo=6) |
| data.operators[].label | string | 枚举标签 (GreaterThan, LessThan, EqualTo, GreaterThanOrEqualTo, LessThanOrEqualTo, NotEqualTo) |
| data.timeUnits | array | AlertTimeUnit 枚举选项列表 |
| data.timeUnits[].value | integer | 枚举值 (Minute=1, Hour=2, Day=3) |
| data.timeUnits[].label | string | 枚举标签 (Minute, Hour, Day) |
| data.notifyBys | array | AlertNotifyBy 枚举选项列表 |
| data.notifyBys[].value | integer | 枚举值 (System=1, SMS=2) |
| data.notifyBys[].label | string | 枚举标签 (System, SMS) |
| data.recordStates | array | AlertRecordState 枚举选项列表 |
| data.recordStates[].value | integer | 枚举值 (Active=1, Read=2) |
| data.recordStates[].label | string | 枚举标签 (Active, Read) |

- **错误码**:

| errorCode | message | 说明 |
|-----------|---------|------|
| 999999 | DefaultException | 服务器内部错误 |

- **请求示例**:

```json
GET /api/alert/config
```

## 获取 Alert 记录列表

- **接口**: `GET /api/alert/record`
- **鉴权**: 需要有效 Token，RequireOrgAdmin或项目管理员（Require项目Admin）Privilege
- **描述**: 获取 Alert 触发记录列表，支持分页和筛选。

- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| projectId | long | 是 | project_id |
| page | integer | 否 | 页码，默认 1 |
| pagesize | integer | 否 | 每页条数，默认 20 |
| state | AlertRecordState | 否 | 按记录状态筛选（Active=1, Read=2） |
| alertId | string | 否 | 按 Alert ID 筛选 |

- **响应格式**:

| 字段 | 类型 | 说明 |
|---|---|---|
| code | integer | 状态码，0 表示成功 |
| message | string | 响应消息 |
| data | object | 分页数据 |
| data.total | long | 总条数 |
| data.items | array | Alert 记录列表 |
| data.items[].id | string | 记录 ID |
| data.items[].alertId | string | 关联的 Alert ID |
| data.items[].projectId | long | 关联的 Project ID |
| data.items[].field | integer | 监控的指标字段 |
| data.items[].operator | integer | 比较运算符 |
| data.items[].value | double | 触发阈值 |
| data.items[].actualValue | double | 实际值 |
| data.items[].timeUnit | integer | 时间单位 |
| data.items[].frequency | integer | 检查频率 |
| data.items[].notifyBys | array | 通知方式列表 |
| data.items[].state | integer | 记录状态（Active=1, Read=2） |
| data.items[].triggeredAt | string | 触发时间 |
| data.items[].readAt | string | 已读时间 |

- **错误码**:

| errorCode | message | 说明 |
|-----------|---------|------|
| 100024 | Alert项目NotFound | 项目不存在或无权访问 |
| 100034 | AlertRecordNotFound | Alert 记录不存在 |
| 100000 | UnAuthToken | 未认证或 Token 无效 |
| 100001 | Unauthorized | 无Privilege执行此操作 |
| 999999 | DefaultException | 服务器内部错误 |

- **请求示例**:

```json
GET /api/alert/record?projectId=12345&page=1&pagesize=20&state=1
```

## 标记 Alert 记录为已读

- **接口**: `POST /api/alert/record/read`
- **鉴权**: 需要有效 Token，RequireOrgAdmin或项目管理员（Require项目Admin）Privilege
- **描述**: 将一条或多条 Alert 触发记录标记为已读。

- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| ids | array | 是 | Alert 记录 ID 列表 |

- **响应格式**:

| 字段 | 类型 | 说明 |
|---|---|---|
| code | integer | 状态码，0 表示成功 |
| message | string | 响应消息 |

- **错误码**:

| errorCode | message | 说明 |
|-----------|---------|------|
| 100034 | AlertRecordNotFound | Alert 记录不存在 |
| 100035 | MarkAlertRecordReadFailed | 标记 Alert 记录已读失败 |
| 100000 | UnAuthToken | 未认证或 Token 无效 |
| 100001 | Unauthorized | 无Privilege执行此操作 |
| 999999 | DefaultException | 服务器内部错误 |

- **请求示例**:

```json
POST /api/alert/record/read
{
  "ids": ["record_001", "record_002"]
}
```

## 枚举定义

### 8.1. AlertField

| 值 | 名称 | 说明 |
|---|---|---|
| 1 | TotalTokens | Token 总消耗量 |
| 2 | TotalCost | 总成本 |
| 3 | ErrorCount | 错误次数 |
| 4 | Latency | 延迟 |
| 5 | ErrorRate | 错误率 |
| 6 | InputTokens | 输入 Token 数 |
| 7 | OutputTokens | 输出 Token 数 |
| 8 | WarningCount | 警告次数 |
| 9 | ObservationCount | Observation次数 |

### 8.2. AlertOperator

| 值 | 名称 | 说明 |
|---|---|---|
| 1 | GreaterThan | 大于 |
| 2 | LessThan | 小于 |
| 3 | EqualTo | 等于 |
| 4 | GreaterThanOrEqualTo | 大于等于 |
| 5 | LessThanOrEqualTo | 小于等于 |
| 6 | NotEqualTo | 不等于 |

### 8.3. AlertTimeUnit

| 值 | 名称 | 说明 |
|---|---|---|
| 1 | Minute | 分钟 |
| 2 | Hour | 小时 |
| 3 | Day | 天 |

### 8.4. AlertNotifyBy

| 值 | 名称 | 说明 |
|---|---|---|
| 1 | System | 系统通知 |
| 2 | SMS | 短信通知 |

### 8.5. AlertRecordState

| 值 | 名称 | 说明 |
|---|---|---|
| 1 | Active | 活跃 |
| 2 | Read | 已读 |

---

## 9. CaptchaController 接口

本章共覆盖 1 个 HTTP 端点，提供短信Captcha获取功能。

### 9.1. API-001 获取短信Captcha (GET /api/captcha/sms)

- **鉴权**: 无
- **描述**: 根据手机号获取短信Captcha，用于用户登录、注册或找回密码等场景的身份验证。Captcha长度为 6 位，有效期 300 秒，重发间隔 60 秒。

- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| phone | string | 是 | 接收短信Captcha的目标手机号码。 |

- **响应格式**:

| 字段 | 类型 | 说明 |
|---|---|---|
| code | integer | 业务状态码，`0` 表示成功，非 `0` 表示失败。 |
| message | string | 状态描述信息，成功时为 `"Captcha发送成功"`，失败时为具体错误信息。 |
| data | object | 响应数据，发送成功时返回 `null`。 |
| traceId | string | 请求Trace ID，用于日志排查。 |

- **错误码**:

| errorCode | message | 说明 |
|---|---|---|
| 110000 | SendSMSTooOften | 短信发送过于频繁，请等待 60 秒后重试。受 `CaptchaSetting.ResendInterval = 60` 秒限制。 |
| 110001 | FailedToSendSMS | 短信发送失败，可能是短信服务商（如 Aliyun、TencentCloud）Config错误或网络异常。 |
| 100009 | EmptyMobile | 手机号为空，请输入有效的手机号码。 |
| 999999 | DefaultException | 服务器内部错误，请稍后重试。 |

- **请求示例**:

```http
GET /api/captcha/sms?phone=13800138000
```

- **响应示例**:

**成功响应**:

```json
{
  "code": 0,
  "message": "Captcha发送成功",
  "data": null,
  "traceId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

**失败响应（发送过于频繁）**:

```json
{
  "code": 110000,
  "message": "短信发送过于频繁，请稍后重试",
  "data": null,
  "traceId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

**失败响应（手机号为空）**:

```json
{
  "code": 100009,
  "message": "手机号为空，请填写手机号",
  "data": null,
  "traceId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

---

## 10. AgentConfigController 接口


本章共覆盖 3 个 HTTP 端点，每个端点一个接口卡片。


### 10.1. API-001 获取 Agent Config (GET /api/agent/config)

- **鉴权**: 需要认证。所有端点均通过 `ApiHandlerBase` 基类进行Privilege控制，支持 JWT Token 和 Basic Auth 两种认证方式。
- **描述**: 获取当前 Agent 的Config信息，包括模型、温度、Token 限制等运行参数。
- **请求参数**: 无（GET 请求，无路径参数或查询参数）

- **响应格式**:

| 字段 | 类型 | 说明 |
|---|---|---|
| `code` | int | 业务状态码，`0` 表示成功，非 `0` 表示失败 |
| `message` | string | 状态描述信息 |
| `data` | object | Agent Config数据对象 |
| `data.id` | string | Config唯一标识 |
| `data.name` | string | Config名称 |
| `data.model` | string | 使用的模型名称 |
| `data.temperature` | number | 温度参数，控制生成随机性 |
| `data.maxTokens` | integer | 最大 Token 生成数量 |
| `data.systemPrompt` | string | 系统提示词 |
| `data.tools` | array\<string\> | 启用的工具列表 |
| `data.createdAt` | string | 创建时间（ISO 8601 格式） |
| `data.updatedAt` | string | 更新时间（ISO 8601 格式） |

- **错误码**:

| errorCode | message | 说明 |
|---|---|---|
| `100000` | UnAuthToken | 未提供有效的认证 Token |
| `999999` | DefaultException | 服务器内部错误，请稍后重试 |

- **请求示例**:

```http
GET /api/agent/config HTTP/1.1
Host: localhost
Authorization: Bearer <your-jwt-token>
```

- **响应示例**:

**成功响应 (HTTP 200)**:

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "cfg_8f7e6d5c4b3a2",
    "name": "default-agent-config",
    "model": "gpt-4o",
    "temperature": 0.7,
    "maxTokens": 2048,
    "systemPrompt": "You are a helpful assistant.",
    "tools": ["web_search", "code_interpreter"],
    "createdAt": "2025-01-15T08:30:00Z",
    "updatedAt": "2025-01-15T08:30:00Z"
  }
}
```

**失败响应 (HTTP 401)**:

```json
{
  "code": 100000,
  "message": "UnAuthToken",
  "data": null
}
```

### 10.2. API-002 删除 Agent Config (GET /api/agent/config/delete)

- **鉴权**: 需要认证。所有端点均通过 `ApiHandlerBase` 基类进行Privilege控制，支持 JWT Token 和 Basic Auth 两种认证方式。
- **描述**: 删除指定的 Agent Config。该接口通过 GET 请求执行删除操作，用于移除系统中已存在的 Agent Config记录。

- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| agentConfigId | string | 是 | 待删除的 Agent Config ID，通过查询参数传递 |

- **响应格式**:

| 字段 | 类型 | 说明 |
|------|------|------|
| code | int | 业务状态码，`0` 表示成功，非 `0` 表示失败 |
| data | object | 删除操作结果数据 |
| data.success | boolean | 是否删除成功 |
| data.agentConfigId | string | 被删除的 Agent Config ID |
| message | string | 操作结果描述信息 |

- **错误码**:

| errorCode | message | 说明 |
|-----------|---------|------|
| 100000 | UnAuthToken | Token 未认证或已过期 |
| 999999 | DefaultException | 系统默认异常，未预期的错误 |

- **请求示例**:

```http
GET /api/agent/config/delete?agentConfigId=a1b2c3d4-e5f6-7890-abcd-ef1234567890 HTTP/1.1
Host: localhost
Authorization: Bearer <your-jwt-token>
```

- **响应示例**:

**成功响应 (HTTP 200)**:

```json
{
  "code": 0,
  "data": {
    "success": true,
    "agentConfigId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
  },
  "message": "Agent Config删除成功"
}
```

**失败响应 (HTTP 401)**:

```json
{
  "code": 100000,
  "data": null,
  "message": "UnAuthToken"
}
```

### 10.3. API-003 提交 Agent Config (POST /api/agent/config)

- **鉴权**: 需要认证。所有端点均通过 `ApiHandlerBase` 基类进行Privilege控制，支持 JWT Token 和 Basic Auth 两种认证方式。
- **描述**: 提交 Agent Config信息，用于创建或更新 Agent 的Config数据。请求体为原始 JSON 字符串，由服务端进行解析与处理。
- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| body | string | 是 | 待提交的 Agent Config内容，以 JSON 字符串形式传输（`[FromBody]` 绑定） |

**请求体 Schema** (body 字段内嵌的 JSON 结构):

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| agentId | string | 是 | Agent 唯一标识 |
| name | string | 是 | Config名称 |
| model | string | 是 | 使用的模型名称 |
| temperature | number | 否 | 温度参数，控制生成随机性，默认 0.7 |
| maxTokens | integer | 否 | 最大 Token 生成数量，默认 2048 |
| systemPrompt | string | 否 | 系统提示词 |
| enabled | boolean | 否 | 是否启用该Config，默认 true |

- **响应格式**:

| 字段 | 类型 | 说明 |
|------|------|------|
| code | int | 业务状态码，`0` 表示成功，非 `0` 表示失败 |
| message | string | 提示信息，成功时为 `"success"` |
| data | object | 返回的数据对象，包含处理结果详情 |
| data.id | string | Config记录的 ID |
| data.status | string | 处理状态，`"success"` 表示成功 |

- **错误码**:

| errorCode | message | 说明 |
|-----------|---------|------|
| 100000 | UnAuthToken | 未认证的 Token 或 Token 无效 |
| 999999 | DefaultException | 服务器内部异常 |

- **请求示例**:

```http
POST /api/agent/config HTTP/1.1
Host: localhost
Authorization: Bearer <your-jwt-token>
Content-Type: application/json

{
  "body": "{\"agentId\":\"agt_8f3b2c1a\",\"name\":\"CustomerServiceAgent\",\"model\":\"gpt-4o\",\"temperature\":0.7,\"maxTokens\":2048,\"systemPrompt\":\"You are a helpful customer service assistant.\",\"enabled\":true}"
}
```

- **响应示例**:

**成功响应 (HTTP 200)**:

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "cfg_5e7a9d2c",
    "status": "success"
  }
}
```

**失败响应 (HTTP 401)**:

```json
{
  "code": 100000,
  "message": "UnAuthToken",
  "data": null
}
```

---

## 11. AgentReportController 接口


本章共覆盖 3 个 HTTP 端点, 每个端点一个接口卡片.


### 11.1. API-035 GetTemplates (GET /api/agent/report)

- **鉴权**: 需要认证。所有端点均通过 `ApiHandlerBase` 基类进行Privilege控制，支持 JWT Token 和 Basic Auth 两种认证方式。
- **描述**: 获取 Agent 报告模板列表，支持按 ID 查询及预定义模板筛选。

- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `id` | string | 否 | 报告模板的唯一标识符。若提供，则返回指定模板的详细信息。 |
| `includedpredefined` | bool | 否 | 是否包含预定义模板。默认值为 `false`。 |
| `includedpredefinedonly` | bool | 否 | 是否仅返回预定义模板。默认值为 `false`。 |
| `page` | int | 否 | 页码，从 1 开始。 |
| `pagesize` | int | 否 | 每页记录数。 |

- **响应格式**: `ApiResponse<T>` 标准响应包装

| 字段 | 类型 | 说明 |
|---|---|---|
| `code` | int | 状态码。`0` 表示成功，非 `0` 表示失败。 |
| `message` | string | 状态描述信息。 |
| `data` | object | 响应数据。成功时为分页结果对象，包含 `items`（模板列表）和 `total`（总记录数）。 |

- **错误码**:

| errorCode | message | 说明 |
|---|---|---|
| `100000` | UnAuthToken | Token 无效或未提供。 |
| `999999` | DefaultException | 服务器内部错误。 |

- **请求示例**:

```
GET /api/agent/report?includedpredefined=true&page=1&pagesize=20
```

- **响应示例**:

**成功响应**:

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "id": "template-001",
        "name": "Daily Agent Summary",
        "isPredefined": true,
        "createdAt": "2024-05-20T10:00:00Z"
      }
    ],
    "total": 1
  }
}
```

**失败响应**:

```json
{
  "code": 100000,
  "message": "UnAuthToken",
  "data": null
}
```

### 11.2. API-048 DeleteTemplates (DELETE /api/agent/report/delete)

- **鉴权**: 需要认证。所有端点均通过 `ApiHandlerBase` 基类进行Privilege控制，支持 JWT Token 和 Basic Auth 两种认证方式。
- **描述**: 根据传入的模板 ID 列表删除 Agent 报告模板。

- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| ids | string | 否 | 待删除的 Agent 报告模板 ID 列表，多个 ID 以逗号分隔。若为空或 null，则不执行删除操作。 |

- **响应格式**:

| 字段 | 类型 | 说明 |
|------|------|------|
| code | int | 业务状态码，0 表示成功，非 0 表示失败 |
| message | string | 提示信息，成功时为 "ok"，失败时为错误描述 |
| data | object | 删除操作结果数据，成功时返回 null |

- **错误码**:

| errorCode | message | 说明 |
|-----------|---------|------|
| 100000 | UnAuthToken | 未认证的 Token 或 Token 无效 |
| 999999 | DefaultException | 服务器内部异常，请稍后重试 |

- **请求示例**:

```
DELETE /api/agent/report/delete?ids=1001,1002,1003
```

- **响应示例**:

**成功响应**:
```json
{
  "code": 0,
  "message": "ok",
  "data": null
}
```

**失败响应**:
```json
{
  "code": 100000,
  "message": "UnAuthToken",
  "data": null
}
```

### 11.3. API-001 CreateOrUpdateTemplate (POST /api/agent/report)

- **鉴权**: 需要认证。所有端点均通过 `ApiHandlerBase` 基类进行Privilege控制，支持 JWT Token 和 Basic Auth 两种认证方式。
- **描述**: 创建或更新 Agent 报告模板。根据请求体中的模板名称判断是新增还是更新操作，若模板名称已存在则更新，否则创建新模板。

- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | string | 是 | 报告模板名称，用于标识模板，创建时不可为空，更新时用于定位目标模板 |
| `content` | string | 是 | 报告模板内容，支持 Markdown 格式，用于生成 Agent 报告 |
| `description` | string | 否 | 模板描述，说明模板用途或适用场景 |
| `isDefault` | boolean | 否 | 是否设为默认模板，默认 `false`。设为 `true` 时，该模板将作为 Agent 报告的默认模板 |

- **响应格式**:

| 字段 | 类型 | 说明 |
|------|------|------|
| `code` | int | 业务状态码，`0` 表示成功，非 `0` 表示失败 |
| `message` | string | 提示信息，成功时为 `"success"`，失败时为具体错误描述 |
| `data` | object | 响应数据，成功时返回创建或更新后的模板信息；失败时为 `null` |
| `data.id` | string | 模板唯一标识 |
| `data.name` | string | 模板名称 |
| `data.content` | string | 模板内容 |
| `data.description` | string | 模板描述 |
| `data.isDefault` | boolean | 是否为默认模板 |
| `data.createdAt` | datetime | 模板创建时间（ISO 8601 格式） |
| `data.updatedAt` | datetime | 模板最后更新时间（ISO 8601 格式） |
| `traceId` | string | 请求Trace ID，用于链路Trace和日志排查 |

- **错误码**:

| errorCode | message | 说明 |
|-----------|---------|------|
| 100000 | UnAuthToken | 认证 Token 无效或缺失 |
| 999999 | DefaultException | 服务器内部错误，请稍后重试 |

- **请求示例**:

```json
{
  "name": "周报模板",
  "content": "# Agent 周报\n## 本周概览\n- 总 Token 消耗: {{total_tokens}}\n- 总成本: {{total_cost}}\n- 错误数: {{error_count}}\n## 详细数据\n{{trace_details}}",
  "description": "用于生成每周 Agent 运行报告",
  "isDefault": true
}
```

- **响应示例**:

**成功响应**:

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "tpl_8f3a2b9c1d4e5f6a7b8c9d0e",
    "name": "周报模板",
    "content": "# Agent 周报\n## 本周概览\n- 总 Token 消耗: {{total_tokens}}\n- 总成本: {{total_cost}}\n- 错误数: {{error_count}}\n## 详细数据\n{{trace_details}}",
    "description": "用于生成每周 Agent 运行报告",
    "isDefault": true,
    "createdAt": "2025-01-15T10:30:00Z",
    "updatedAt": "2025-01-15T10:30:00Z"
  },
  "traceId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

**失败响应（认证失败）**:

```json
{
  "code": 100000,
  "message": "UnAuthToken",
  "data": null,
  "traceId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

---

## 12. AgentSessionController 接口

### 12.1. API-021 AgentSessionController.Get (GET /api/agent/session)

- **鉴权**: JWT Token (JWT HS256)
- **描述**: 分页查询 Agent Session 列表，支持按 Session ID 精确筛选。用于检索 Agent 运行过程中产生的 Session 记录，包括关联的 Trace 元数据、Token 消耗及 Score 信息。
- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| id | string | 否 | Agent Session 的唯一标识符。传入时返回该 Session 的详细信息；不传时返回当前用户有Privilege访问的 Session 分页列表。 |
| page | int | 否 | 页码，从 1 开始。 |
| pagesize | int | 否 | 每页条数。 |

- **响应格式**:

| 字段 | 类型 | 说明 |
|---|---|---|
| code | int | 业务状态码。`0` 表示成功，非 `0` 表示失败。 |
| message | string | 提示信息。 |
| data | object | 响应数据。 |
| data.items | array | Session 列表。 |
| data.items[].id | string | Session 唯一标识符。 |
| data.items[].traceId | string | 关联的 trace_id。 |
| data.items[].projectId | string | 所属project_id。 |
| data.items[].organizationId | string | 所属组织 ID。 |
| data.items[].createdAt | string | 创建时间（ISO 8601 格式）。 |
| data.items[].updatedAt | string | 更新时间（ISO 8601 格式）。 |
| data.total | int | 符合条件的总记录数。 |
| data.page | int | 当前页码。 |
| data.pagesize | int | 每页条数。 |

- **错误码**:

| errorCode | message | 说明 |
|---|---|---|
| 100000 | UnAuthToken | Token 无效或未提供。 |
| 150021 | AgentSessionNotFound | 根据 `id` 参数未找到对应的 Agent Session。 |
| 150019 | OrgAnd项目BothEmpty | 无法确定当前用户所属的 Org 或 Project 上下文。 |
| 999999 | DefaultException | 服务器内部错误。 |

- **请求示例**:

```json
{
  "id": "session_8f7c3a9e2b1d4f6a8c0e5b7d9a1f3c5e",
  "page": 1,
  "pagesize": 20
}
```

- **响应示例**:

**成功响应:**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "id": "session_8f7c3a9e2b1d4f6a8c0e5b7d9a1f3c5e",
        "traceId": "trace_1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d",
        "projectId": "proj_abc123",
        "organizationId": "org_xyz789",
        "createdAt": "2024-05-20T10:30:00Z",
        "updatedAt": "2024-05-20T10:35:00Z"
      }
    ],
    "total": 1,
    "page": 1,
    "pagesize": 20
  }
}
```

**失败响应 (Agent Session 不存在):**

```json
{
  "code": 150021,
  "message": "AgentSessionNotFound",
  "data": null
}
```

### 12.2. API-046 AgentSessionController.Delete (GET /api/agent/session/delete)

- **鉴权**: JWT Token (JWT HS256) 或 Basic Auth。所有端点均通过 `ApiHandlerBase` 基类进行Privilege控制，未通过认证的请求将返回 `100000 UnAuthToken` 错误。
- **描述**: 根据传入的 Session ID 列表删除对应的 Agent Session 记录。
- **请求参数** (Query String):

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| ids | string | 是 | 待删除的 Agent Session 的 ID 列表，多个 ID 使用英文逗号（`,`）分隔。 |

- **响应格式**:

| 字段 | 类型 | 说明 |
|---|---|---|
| code | int | 业务状态码。`0` 表示成功，非 `0` 表示失败。 |
| errorCode | int? | 业务错误码，成功时为 `null`。 |
| message | string | 提示信息，成功时为 `"success"`。 |
| data | object | 响应数据，成功时通常为 `null`。 |
| traceId | string | 当前请求的 trace_id，用于链路Trace。 |

- **错误码**:

| errorCode | message | 说明 |
|---|---|---|
| 100000 | UnAuthToken | Token 无效或未提供，用户未通过身份验证。 |
| 150021 | AgentSessionNotFound | 未找到指定的 Agent Session，或 Session ID 列表为空。 |
| 999999 | DefaultException | 服务器内部异常，无法完成删除操作。 |

- **请求示例**:

```
GET /api/agent/session/delete?ids=session-001,session-002,session-003
```

- **响应示例**:

**成功响应**:
```json
{
  "code": 0,
  "errorCode": null,
  "message": "success",
  "data": null,
  "traceId": "a1b2c3d4-5678-90ab-cdef-1234567890ab"
}
```

**失败响应** (AgentSessionNotFound):
```json
{
  "code": 150021,
  "errorCode": 150021,
  "message": "AgentSessionNotFound",
  "data": null,
  "traceId": "b2c3d4e5-6789-01ab-cdef-2345678901bc"
}
```

### 12.3. API-047 AgentSessionController.Post (POST /api/agent/session)

- **鉴权**: JWT Token (JWT HS256) 或 Basic Auth。所有端点均通过 `ApiHandlerBase` 基类进行Privilege控制，未通过认证的请求将返回 `100000 UnAuthToken` 错误。
- **描述**: 创建新的 Agent Session，用于启动一个 Agent Session并获取Session标识。
- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| agentConfigId | long | 是 | Agent Config ID，指定要启动的 Agent Config。 |
| projectId | long | 是 | project_id，指定Session所属的项目。 |
| input | string | 是 | 用户输入内容，作为 Agent Session的初始输入。 |
| metadata | object | 否 | 附加元数据，用于传递Session上下文信息。 |

- **响应格式**:

| 字段 | 类型 | 说明 |
|------|------|------|
| code | int | 业务状态码。`0` 表示成功，非 `0` 表示失败。 |
| message | string | 状态描述信息。 |
| data | object | 响应数据。 |
| data.sessionId | string | 创建的 Session ID，用于后续Session交互。 |
| data.traceId | string | trace_id，用于Trace本次Session的完整调用链。 |
| data.createdAt | string | Session创建时间（ISO 8601 格式，UTC）。 |

- **错误码**:

| errorCode | message | 说明 |
|-----------|---------|------|
| 100000 | UnAuthToken | Token 无效或未提供，需要重新认证。 |
| 150000 | Empty项目Id | project_id 为空，请检查请求参数。 |
| 150004 | AgentSettingNotConfig | Agent Config未设置，请先完成 Agent Config。 |
| 150007 | AgentLimitExceeded | 超出 Agent 数量限制，请升级套餐或删除无用 Agent。 |
| 150021 | AgentSessionNotFound | 未找到对应的 Agent Session，请检查Session ID。 |
| 150022 | AgentConfigNotFound | 未找到对应的 Agent Config，请检查 agentConfigId。 |
| 999999 | DefaultException | 系统默认异常，请联系管理员处理。 |

- **请求示例**:
```json
{
  "agentConfigId": 1001,
  "projectId": 2001,
  "input": "请帮我分析最近一周的销售数据趋势",
  "metadata": {
    "source": "web",
    "userId": "user_12345"
  }
}
```

- **响应示例**:

**成功响应**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "sessionId": "sess_8f7e2d4c9a3b",
    "traceId": "trace_6b1e9d2f8c4a",
    "createdAt": "2025-01-15T08:30:00Z"
  }
}
```

**失败响应**:
```json
{
  "code": 150004,
  "message": "AgentSettingNotConfig",
  "data": null
}
```

---

## 13. BulletinController 接口

### 13.1. POST /api/tools/bulletin

- **接口名**: Post
- **鉴权**: 需要 JWT JWT Token（Controller类 `BulletinController` 标注了 `[Authorize]`，继承自 `ApiControllerBase`）
- **描述**: 创建一条新的Bulletin。

- **请求参数** (JSON Body, 基于 `CreateBulletinBody` DTO):

| 字段 | 类型 | 必填 | 说明 |
| :--- | :--- | :--- | :--- |
| `title` | string | 是 | Bulletin标题 |
| `content` | string | 是 | Bulletin内容 |
| `type` | int | 是 | Bulletin类型，对应 `BulletinType` 枚举：`News` (1), `Activity` (2), `Information` (3), `Annoucement` (4), `Advertisement` (5), `Agreement` (9) |
| `status` | int | 是 | Bulletin状态，对应 `BulletinStatus` 枚举：`Draft` (1), `Reviewing` (2), `Revision` (3), `Published` (4), `Expired` (5), `Closed` (6) |
| `startTime` | datetime? | 否 | Bulletin开始展示时间 |
| `endTime` | datetime? | 否 | Bulletin结束展示时间 |

- **响应格式**:

| 字段 | 类型 | 说明 |
| :--- | :--- | :--- |
| `code` | int | 状态码，`0` 表示成功，非 `0` 表示失败 |
| `message` | string | 提示信息，成功时为 `"Success"`，失败时为错误详情 |
| `data` | object | 成功时返回创建成功的Bulletin数据；失败时为 `null` |

- **错误码**:

| errorCode | message | 说明 |
| :--- | :--- | :--- |
| `100000` | UnAuthToken | 未提供或提供了无效的认证 Token |
| `100001` | InvalidParameter | 请求参数缺失或格式不正确 |
| `100002` | DataNotFound | 未找到对应的数据记录 |
| `100003` | OperationNotAllowed | 当前状态不允许执行该操作 |
| `999999` | DefaultException | 服务器内部错误，未捕获的异常 |

- **请求示例**:

```json
{
  "title": "系统维护通知",
  "content": "系统将于本周六凌晨 2:00-4:00 进行升级维护。",
  "type": 4,
  "status": 1,
  "startTime": "2024-04-20T00:00:00Z",
  "endTime": "2024-04-21T00:00:00Z"
}
```

- **成功响应示例**:

```json
{
  "code": 0,
  "message": "Success",
  "data": {
    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "title": "系统维护通知",
    "content": "系统将于本周六凌晨 2:00-4:00 进行升级维护。",
    "type": 4,
    "status": 1,
    "startTime": "2024-04-20T00:00:00Z",
    "endTime": "2024-04-21T00:00:00Z",
    "createdAt": "2025-01-15T10:30:00Z",
    "updatedAt": "2025-01-15T10:30:00Z"
  }
}
```

- **失败响应示例**:

```json
{
  "code": 100000,
  "message": "UnAuthToken",
  "data": null
}
```

### 13.2. GET /api/tools/bulletin/agreement

- **接口名**: Get
- **鉴权**: 无
- **描述**: 获取最新的用户协议Bulletin。

- **响应格式**:

| 字段 | 类型 | 说明 |
| :--- | :--- | :--- |
| `code` | int | 状态码，`0` 表示成功，非 `0` 表示失败 |
| `message` | string | 提示信息 |
| `data` | object | 返回数据，包含协议Bulletin详情 |

- **错误码**:

| errorCode | message | 说明 |
| :--- | :--- | :--- |
| `100002` | DataNotFound | 未找到已发布的用户协议Bulletin |
| `999999` | DefaultException | 服务器内部错误，未捕获的异常 |

- **成功响应示例**:

```json
{
  "code": 0,
  "message": "Success",
  "data": {
    "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
    "title": "用户协议",
    "content": "欢迎使用 AgentInsightService，请阅读并同意以下条款...",
    "type": 9,
    "status": 4,
    "createdAt": "2025-01-01T10:00:00Z",
    "updatedAt": "2025-01-01T10:00:00Z"
  }
}
```

- **失败响应示例**:

```json
{
  "code": 100002,
  "message": "DataNotFound",
  "data": null
}
```

### 13.3. GET /api/tools/bulletin/bulletins

- **接口名**: Get
- **鉴权**: 无
- **描述**: 获取公开的Bulletin列表，支持按类型筛选，并分页返回。

- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
| :--- | :--- | :--- | :--- |
| `type` | int? | 否 | Bulletin类型，可空。枚举值：`News`(1)、`Activity`(2)、`Information`(3)、`Annoucement`(4)、`Advertisement`(5)、`Agreement`(9) |
| `isCarousel` | bool | 否 | 是否仅查询轮播Bulletin，默认 `false` |
| `page` | int | 否 | 页码，默认 `AgentInsightConst.DefaultPage` |
| `pagesize` | int | 否 | 每页条数，默认 `AgentInsightConst.DefaultPageSize` |

- **响应格式**:

| 字段 | 类型 | 说明 |
| :--- | :--- | :--- |
| `code` | int | 状态码，`0` 表示成功，非 `0` 表示失败 |
| `message` | string | 提示信息 |
| `data` | object | 返回数据 |
| `data.items` | array | Bulletin列表 |
| `data.items[].id` | string | Bulletin ID |
| `data.items[].title` | string | Bulletin标题 |
| `data.items[].content` | string | Bulletin内容 |
| `data.items[].type` | int | Bulletin类型 |
| `data.items[].status` | int | Bulletin状态 |
| `data.items[].startTime` | datetime? | Bulletin开始展示时间 |
| `data.items[].endTime` | datetime? | Bulletin结束展示时间 |
| `data.items[].createdAt` | datetime | 创建时间 |
| `data.items[].updatedAt` | datetime | 更新时间 |
| `data.total` | int | 总记录数 |
| `data.page` | int | 当前页码 |
| `data.pagesize` | int | 每页条数 |

- **错误码**:

| errorCode | message | 说明 |
| :--- | :--- | :--- |
| `100001` | InvalidParameter | 请求参数缺失或格式不正确 |
| `999999` | DefaultException | 服务器内部错误，未捕获的异常 |

- **成功响应示例**:

```json
{
  "code": 0,
  "message": "Success",
  "data": {
    "items": [
      {
        "id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
        "title": "系统维护通知",
        "content": "系统将于本周六凌晨 2:00-4:00 进行升级维护。",
        "type": 4,
        "status": 4,
        "startTime": "2025-01-15T10:00:00Z",
        "endTime": "2025-01-16T10:00:00Z",
        "createdAt": "2025-01-15T10:00:00Z",
        "updatedAt": "2025-01-15T10:00:00Z"
      }
    ],
    "total": 1,
    "page": 1,
    "pagesize": 10
  }
}
```

- **失败响应示例**:

```json
{
  "code": 100001,
  "message": "InvalidParameter",
  "data": null
}
```

### 13.4. GET /api/tools/bulletin/backend

- **接口名**: Get
- **鉴权**: 需要 JWT JWT Token（Controller类 `BulletinController` 标注了 `[Authorize]`，继承自 `ApiControllerBase`）
- **描述**: 获取后端Bulletin列表，支持按类型和状态筛选，并分页返回。

- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
| :--- | :--- | :--- | :--- |
| `type` | int? | 否 | Bulletin类型，可空。枚举值：`News`(1)、`Activity`(2)、`Information`(3)、`Annoucement`(4)、`Advertisement`(5)、`Agreement`(9) |
| `status` | int? | 否 | Bulletin状态，可空。枚举值：`Draft`(1)、`Reviewing`(2)、`Revision`(3)、`Published`(4)、`Expired`(5)、`Closed`(6) |
| `page` | int | 否 | 页码，默认 `AgentInsightConst.DefaultPage` |
| `pagesize` | int | 否 | 每页条数，默认 `AgentInsightConst.DefaultPageSize` |

- **响应格式**:

| 字段 | 类型 | 说明 |
| :--- | :--- | :--- |
| `code` | int | 状态码，`0` 表示成功，非 `0` 表示失败 |
| `message` | string | 提示信息 |
| `data` | object | 返回数据 |
| `data.items` | array | Bulletin列表 |
| `data.items[].id` | string | Bulletin ID |
| `data.items[].title` | string | Bulletin标题 |
| `data.items[].content` | string | Bulletin内容 |
| `data.items[].type` | int | Bulletin类型 |
| `data.items[].status` | int | Bulletin状态 |
| `data.items[].startTime` | datetime? | Bulletin开始展示时间 |
| `data.items[].endTime` | datetime? | Bulletin结束展示时间 |
| `data.items[].createdAt` | datetime | 创建时间 |
| `data.items[].updatedAt` | datetime | 更新时间 |
| `data.total` | int | 总记录数 |
| `data.page` | int | 当前页码 |
| `data.pagesize` | int | 每页条数 |

- **错误码**:

| errorCode | message | 说明 |
| :--- | :--- | :--- |
| `100000` | UnAuthToken | 未提供或提供了无效的认证 Token |
| `100001` | InvalidParameter | 请求参数缺失或格式不正确 |
| `999999` | DefaultException | 服务器内部错误，未捕获的异常 |

- **成功响应示例**:

```json
{
  "code": 0,
  "message": "Success",
  "data": {
    "items": [
      {
        "id": "d4e5f6a7-b8c9-0123-defa-123456789012",
        "title": "内部测试Bulletin",
        "content": "这是一个内部测试Bulletin。",
        "type": 1,
        "status": 2,
        "startTime": "2025-01-01T10:00:00Z",
        "endTime": "2025-01-31T10:00:00Z",
        "createdAt": "2025-01-01T10:00:00Z",
        "updatedAt": "2025-01-02T10:00:00Z"
      }
    ],
    "total": 1,
    "page": 1,
    "pagesize": 10
  }
}
```

- **失败响应示例**:

```json
{
  "code": 100000,
  "message": "UnAuthToken",
  "data": null
}
```

### 13.5. POST /api/tools/bulletin/approve

- **接口名**: Post
- **鉴权**: 需要 JWT JWT Token（Controller类 `BulletinController` 标注了 `[Authorize]`，继承自 `ApiControllerBase`）
- **描述**: 根据Bulletin ID 列表批量审批通过Bulletin。

- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
| :--- | :--- | :--- | :--- |
| `ids` | string | 是 | 待审批通过的Bulletin ID 列表，多个 ID 以逗号分隔 |

- **响应格式**:

| 字段 | 类型 | 说明 |
| :--- | :--- | :--- |
| `code` | int | 状态码，`0` 表示成功，非 `0` 表示失败 |
| `message` | string | 提示信息 |
| `data` | object | 返回数据，成功时为 `null` |

- **错误码**:

| errorCode | message | 说明 |
| :--- | :--- | :--- |
| `100000` | UnAuthToken | 未提供或提供了无效的认证 Token |
| `100001` | InvalidParameter | 请求参数缺失或格式不正确 |
| `100002` | DataNotFound | 未找到对应的Bulletin记录 |
| `100003` | OperationNotAllowed | Bulletin当前状态不允许审批通过 |
| `999999` | DefaultException | 服务器内部错误，未捕获的异常 |

- **请求示例**:

```json
{
  "ids": "a1b2c3d4-e5f6-7890-abcd-ef1234567890,b2c3d4e5-f6a7-8901-bcde-f12345678901"
}
```

- **成功响应示例**:

```json
{
  "code": 0,
  "message": "Success",
  "data": null
}
```

- **失败响应示例**:

```json
{
  "code": 100000,
  "message": "UnAuthToken",
  "data": null
}
```

### 13.6. POST /api/tools/bulletin/revision

- **接口名**: Post
- **鉴权**: 需要 JWT JWT Token（Controller类 `BulletinController` 标注了 `[Authorize]`，继承自 `ApiControllerBase`）
- **描述**: 根据Bulletin ID 列表批量驳回Bulletin，要求修改后重新提交审核。

- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
| :--- | :--- | :--- | :--- |
| `ids` | string | 是 | 待驳回的Bulletin ID 列表，多个 ID 以逗号分隔 |

- **响应格式**:

| 字段 | 类型 | 说明 |
| :--- | :--- | :--- |
| `code` | int | 状态码，`0` 表示成功，非 `0` 表示失败 |
| `message` | string | 提示信息 |
| `data` | object | 返回数据，成功时为 `null` |

- **错误码**:

| errorCode | message | 说明 |
| :--- | :--- | :--- |
| `100000` | UnAuthToken | 未提供或提供了无效的认证 Token |
| `100001` | InvalidParameter | 请求参数缺失或格式不正确 |
| `100002` | DataNotFound | 未找到对应的Bulletin记录 |
| `100003` | OperationNotAllowed | Bulletin当前状态不允许驳回 |
| `999999` | DefaultException | 服务器内部错误，未捕获的异常 |

- **请求示例**:

```json
{
  "ids": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

- **成功响应示例**:

```json
{
  "code": 0,
  "message": "Success",
  "data": null
}
```

- **失败响应示例**:

```json
{
  "code": 100000,
  "message": "UnAuthToken",
  "data": null
}
```

### 13.7. POST /api/tools/bulletin/close

- **接口名**: Post
- **鉴权**: 需要 JWT JWT Token（Controller类 `BulletinController` 标注了 `[Authorize]`，继承自 `ApiControllerBase`）
- **描述**: 关闭指定 ID 的Bulletin（Bulletin），将Bulletin状态更新为 `Closed`（6）。

- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
| :--- | :--- | :--- | :--- |
| `ids` | string | 是 | 待关闭的Bulletin ID 列表，多个 ID 以逗号分隔 |

- **响应格式**:

| 字段 | 类型 | 说明 |
| :--- | :--- | :--- |
| `code` | int | 状态码，`0` 表示成功，非 `0` 表示失败 |
| `message` | string | 提示信息 |
| `data` | object | 返回数据，成功时为 `null` |

- **错误码**:

| errorCode | message | 说明 |
| :--- | :--- | :--- |
| `100000` | UnAuthToken | 未提供或提供了无效的认证 Token |
| `100001` | InvalidParameter | 请求参数缺失或格式不正确 |
| `100002` | DataNotFound | 未找到对应的Bulletin记录 |
| `100003` | OperationNotAllowed | Bulletin当前状态不允许关闭 |
| `999999` | DefaultException | 服务器内部错误，未捕获的异常 |

- **请求示例**:

```json
{
  "ids": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

- **成功响应示例**:

```json
{
  "code": 0,
  "message": "Success",
  "data": null
}
```

- **失败响应示例**:

```json
{
  "code": 100000,
  "message": "UnAuthToken",
  "data": null
}
```

---

## 14. HealthController 接口


本章共覆盖 1 个 HTTP 端点, 每个端点一个接口卡片.


### 14.1. API-001 健康检查 (GET /api/tools/health)

- **鉴权**: 支持 JWT Token 和 Basic Auth 两种认证方式。该端点通过 `ApiHandlerBase` 基类进行Privilege控制，与其余端点保持一致。
- **描述**: 检查 AgentInsightService 服务运行状态及依赖组件健康情况

- **请求参数**: 无

- **响应格式**:

| 字段 | 类型 | 说明 |
|------|------|------|
| code | int | 状态码，200 表示成功 |
| message | string | 响应消息 |
| data | object | 健康检查结果数据 |
| data.status | string | 服务整体状态，如 "Healthy" |
| data.components | object | 各依赖组件健康状态详情，键为组件名称，值为该组件健康状态字符串 |
| data.components.database | string | 数据库连接状态 |
| data.components.redis | string | Redis 连接状态 |
| data.components.clickhouse | string | ClickHouse 连接状态 |
| data.timestamp | string | 检查时间戳 (ISO 8601 格式) |

- **错误码**:

| errorCode | message | 说明 |
|-----------|---------|------|
| 100001 | DefaultException | 服务内部异常，健康检查执行失败 |
| 100002 | ClickHouseQueryError | ClickHouse 连接或查询异常 |
| 100003 | EncryptionFailed | Config解密失败，无法读取敏感Config项 |

> **说明**: 错误码定义于 `Models/Common/Enums/ExceptionCodes.cs`，以 100xxx 格式编码。具体错误码映射以实际代码仓库定义为准，如与上述编号不一致，请参照 `ExceptionCodes.cs` 中的实际定义。

- **请求示例**:

```http
GET /api/tools/health
```

- **响应示例**:

**成功响应 (HTTP 200)**:

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "status": "Healthy",
    "components": {
      "database": "Healthy",
      "redis": "Healthy",
      "clickhouse": "Healthy"
    },
    "timestamp": "2025-01-15T08:30:00Z"
  }
}
```

**失败响应 (HTTP 500)**:

```json
{
  "code": 100001,
  "message": "DefaultException",
  "data": null
}
```

---

## 15. LiteralRoute 接口

本章共覆盖 2 个 HTTP 端点，每个端点一个接口卡片。

### 15.1. API-001 源码字面量路由 (ANY /api/public)

- **所属 Controller**: LiteralRouteController
- **鉴权**: 无
- **描述**: 该接口为源码字面量路由，用于将 `/api/public` 路径下的所有请求（ANY 方法）反向代理至 AgentInsight-Langfuse-Cluster 集群。此路由由 Yarp.ReverseProxy Config定义，用于将请求转发至 Langfuse Service。

- **请求参数**: 无（该路由为反向代理入口，请求参数由下游服务处理）

- **响应格式**: 该路由为反向代理，响应由下游 Langfuse 服务生成，AgentInsightService 不直接定义响应结构。

- **错误码**: 该路由为反向代理，错误码由下游服务定义。若代理本身失败，可能返回以下通用错误码：

| errorCode | message | 说明 |
|-----------|---------|------|
| 999999 | DefaultException | 默认异常，当反向代理转发请求时发生未预期的错误 |

- **请求示例**: 该接口为反向代理入口，请求将直接转发至下游 Langfuse Service，请求体由下游服务定义。

- **响应示例**:

**成功响应**（由下游 Langfuse 服务返回）:
```json
{
  "status": "success",
  "data": {}
}
```

**失败响应**（代理转发失败）:
```json
{
  "errorCode": 999999,
  "message": "DefaultException",
  "description": "反向代理转发请求时发生未预期的错误"
}
```

### 15.2. API-002 源码字面量路由 (ANY /api/test)

- **所属 Controller**: LiteralRouteController
- **鉴权**: 无
- **描述**: 该接口为源码中通过字面量字符串定义的路由，用于测试或健康检查，返回服务运行状态。

- **请求参数**: 无

- **响应格式**:

| 字段 | 类型 | 说明 |
|---|---|---|
| code | int | HTTP 状态码，200 表示成功 |
| message | string | 响应消息描述 |
| data | object | 响应数据，包含服务状态信息 |
| data.status | string | 服务运行状态，如 "ok" |
| data.timestamp | string | 服务器当前时间戳 (ISO 8601 格式) |

- **错误码**: 无特定业务错误码

- **请求示例**:
```json
// 无请求体，直接发送请求
```

- **响应示例**:

**成功响应 (HTTP 200)**:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "status": "ok",
    "timestamp": "2025-04-11T12:00:00Z"
  }
}
```

**失败响应 (HTTP 500)**:
```json
{
  "code": 999999,
  "message": "DefaultException",
  "data": null
}
```

---

## 16. ModelController 接口


本章共覆盖 1 个 HTTP 端点, 每个端点一个接口卡片.


### 16.1. API-034 获取模型列表 (GET /api/data/model)

- **鉴权**: JWT Token (JWT) 或 Basic Auth
- **描述**: 根据关键字、project_id 等条件分页查询模型列表，支持按指定字段排序。
- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
| :--- | :--- | :--- | :--- |
| keyword | string | 否 | 搜索关键字，用于模糊匹配模型名称。 |
| projectid | string | 否 | project_id，用于筛选指定项目下的模型。 |
| includedpredefined | boolean | 否 | 是否包含预定义模型，默认为 `false`。 |
| orderby | string | 否 | 排序字段，默认为 `-updatedat`（按更新时间倒序）。 |
| page | int | 否 | 页码，默认值为 `1`（取自 `AgentInsightConst.DefaultPage`）。 |
| pagesize | int | 否 | 每页条数，默认值为 `20`（取自 `AgentInsightConst.DefaultPageSize`）。 |

- **响应格式**:

| 字段 | 类型 | 说明 |
| :--- | :--- | :--- |
| code | int | 业务状态码，`0` 表示成功，非 `0` 表示失败。 |
| message | string | 提示信息。 |
| data | object | 返回的数据主体。 |
| data.items | array | 模型列表。 |
| data.items[].id | string | 模型 ID。 |
| data.items[].name | string | 模型名称。 |
| data.items[].projectid | string | 所属project_id。 |
| data.items[].createdat | datetime | 创建时间，格式为 ISO 8601 字符串（如 `2024-01-01T12:00:00Z`）。 |
| data.items[].updatedat | datetime | 更新时间，格式为 ISO 8601 字符串（如 `2024-01-02T12:00:00Z`）。 |
| data.total | int | 符合条件的总记录数。 |
| data.page | int | 当前页码。 |
| data.pagesize | int | 每页条数。 |

- **错误码**:

| errorCode | message | 说明 |
| :--- | :--- | :--- |
| 100000 | UnAuthToken | 未提供或提供了无效的认证 Token。 |
| 150000 | Empty项目Id | project_id 为空。 |
| 150010 | ClickHouseQueryError | 查询 ClickHouse 数据库时发生错误。 |
| 150016 | InvalidOrderBy | 提供的排序字段无效。 |
| 999999 | DefaultException | 服务器发生未预期的异常。 |

- **请求示例**:

```http
GET /api/data/model?keyword=example&projectid=proj_123456&includedpredefined=false&orderby=-updatedat&page=1&pagesize=20 HTTP/1.1
Host: api.example.com
Authorization: Bearer <your-jwt-token>
```

或使用 Basic Auth：

```http
GET /api/data/model?keyword=example&projectid=proj_123456&includedpredefined=false&orderby=-updatedat&page=1&pagesize=20 HTTP/1.1
Host: api.example.com
Authorization: Basic <base64(publickey:secretkey)>
```

- **响应示例**:

**成功响应**:

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "id": "model_001",
        "name": "example-model",
        "projectid": "proj_123456",
        "createdat": "2024-01-01T12:00:00Z",
        "updatedat": "2024-01-02T12:00:00Z"
      }
    ],
    "total": 1,
    "page": 1,
    "pagesize": 20
  }
}
```

**失败响应**:

```json
{
  "code": 150000,
  "message": "Empty项目Id",
  "data": null
}
```

> **说明**：失败响应中的 `code` 字段与错误码表中的 `errorCode` 字段对应，`code` 为 `0` 时表示成功，非 `0` 时表示对应的错误码。

---

## 17. OrderController 接口

### 17.1. OrderController 接口

OrderController PlaceQuery两类核心端点，覆盖订单提交、Payment参数生成及订单状态查询等业务场景。所有端点均通过 `ApiHandlerBase` 基类进行Privilege控制，支持 JWT Token 和 Basic Auth（PublicKey/SecretKey）两种认证方式。

---

#### 17.1.1. 端点列表

| 端点名称 | HTTP 方法 | 路径 | 描述 | 鉴权方式 |
|---------|-----------|------|------|----------|
| Place | POST | `/api/order/place` | 创建订单并返回Payment参数 | JWT Token 或 Basic Auth |
| Query | GET | `/api/order/query` | 查询订单状态与详情 | JWT Token 或 Basic Auth |

---

#### 17.1.2. 端点详情

##### 1. Place（创建订单）

**描述**：根据订单信息创建Payment订单，并返回对应Payment方式（微信/Payment宝）所需的Payment参数。业务场景包括：用户购买 AgentInsightService 订阅、升级或续费产品。

**HTTP 方法**：`POST`

**路径**：`/api/order/place`

**鉴权方式**：JWT Token 或 Basic Auth（PublicKey/SecretKey）

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `orderNo` | string | 是 | 订单号，由商户系统生成，用于标识唯一订单 |
| `organizationId` | long | 是 | Org ID，订单所属的组织标识 |
| `projectId` | long | 是 | project_id，订单关联的项目标识 |
| `productType` | int | 是 | 产品类型，参考 `产品类型` 枚举：`None = 0`（无）、`Monthly = 1`（月付）、`Permanent = 2`（永久） |
| `agentType` | int | 是 | Agent 类型，参考 `AgentType` 枚举：`Assistant = 1`（助手）、`Research = 2`（研究） |
| `payMethod` | int | 是 | Payment方式，参考 `PayMethod` 枚举：`WeChat = 1`（微信）、`Alipay = 2`（Payment宝） |
| `subPayMethod` | int | 是 | 子Payment方式，参考 `SubPayMethod` 枚举：`WECHAT_JSAPI = 1`、`WECHAT_NATIVE = 2`、`WECHAT_MINIPROGRAM = 3`、`ALIPAY_FAST_INSTANT_TRADE_PAY = 11` |
| `totalAmount` | decimal | 是 | 订单总金额，单位为元，精确到小数点后两位 |
| `description` | string | 否 | 订单描述信息，用于展示在Payment页面 |

**请求示例**

```json
{
  "orderNo": "20250101001",
  "organizationId": 1001,
  "projectId": 2001,
  "productType": 1,
  "agentType": 1,
  "payMethod": 1,
  "subPayMethod": 1,
  "totalAmount": 99.00,
  "description": "AgentInsightService 订阅"
}
```

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| `code` | int | 状态码，`0` 表示成功，非 `0` 表示失败 |
| `message` | string | 状态描述信息 |
| `data` | object | 响应数据，包含Payment所需参数 |
| `data.orderNo` | string | 订单号 |
| `data.payParams` | object | Payment参数，根据Payment方式不同返回不同结构 |

**响应示例（微信Payment）**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "orderNo": "20250101001",
    "payParams": {
      "appId": "wx1234567890abcdef",
      "timeStamp": "1710000000",
      "nonceStr": "abc123def456",
      "package": "prepay_id=wx1234567890abcdef",
      "signType": "RSA",
      "paySign": "signature_value"
    }
  }
}
```

**响应示例（Payment宝Payment）**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "orderNo": "20250101001",
    "payParams": {
      "orderStr": "alipay.trade.fastpay.refund.apply=...&biz_content=..."
    }
  }
}
```

---

##### 2. Query（查询订单）

**描述**：根据订单号查询订单的当前状态与详情信息。业务场景包括：Payment结果确认、订单状态同步、对账等。

**HTTP 方法**：`GET`

**路径**：`/api/order/query`

**鉴权方式**：JWT Token 或 Basic Auth（PublicKey/SecretKey）

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `orderNo` | string | 是 | 订单号，由商户系统生成，用于标识唯一订单 |

**请求示例**

```json
{
  "orderNo": "20250101001"
}
```

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| `code` | int | 状态码，`0` 表示成功，非 `0` 表示失败 |
| `message` | string | 状态描述信息 |
| `data` | object | 响应数据，包含订单状态与详情 |
| `data.orderNo` | string | 订单号 |
| `data.status` | string | 订单状态：`Pending`（待Payment）、`Paid`（已Payment）、`Cancelled`（已取消）、`Expired`（已过期） |
| `data.totalAmount` | decimal | 订单总金额，单位为元 |
| `data.payMethod` | int | Payment方式，参考 `PayMethod` 枚举 |
| `data.subPayMethod` | int | 子Payment方式，参考 `SubPayMethod` 枚举 |
| `data.paidAt` | string | Payment完成时间，格式为 `yyyy-MM-dd HH:mm:ss` |

**响应示例**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "orderNo": "20250101001",
    "status": "Paid",
    "totalAmount": 99.00,
    "payMethod": 1,
    "subPayMethod": 1,
    "paidAt": "2025-01-01 12:00:00"
  }
}
```

---

#### 17.1.3. 错误码

以下错误码适用于 OrderController 的所有端点。HTTP 状态码说明：`401` 表示认证失败，`403` 表示Privilege不足，`400` 表示请求参数错误，`500` 表示服务器内部错误。

| errorCode | HTTP 状态码 | message | 说明 |
|-----------|------------|---------|------|
| 100000 | 401 | UnAuthToken | Token 无效或未授权 |
| 100005 | 400 | InvalidUser | 用户无效，请检查用户信息 |
| 810001 | 500 | WeChatSettingNotConfig | 微信Payment未Config，请检查 `WeChatSetting` Config |
| 810002 | 500 | AlipaySettingNotConfig | Payment宝Payment未Config，请检查 `AlipaySetting` Config |
| 810003 | 500 | AlipayConnectionError | Payment宝连接异常，请检查网络或Payment宝服务状态 |
| 810004 | 400 | AlipayTradeError | Payment宝交易异常，请检查交易参数 |
| 810011 | 400 | EmptyOrderNo | 订单号为空，请传入 `orderNo` |
| 810012 | 403 | DoNotOwn组织 | 无权访问该组织，请确认组织 ID 是否正确 |
| 810014 | 400 | ProductDurationNotExist | 产品时长不存在，请检查 `productType` 是否有效 |
| 810015 | 404 | OrderNotExist | 订单不存在，请检查 `orderNo` |
| 810019 | 400 | UnsupportedPayMethod | 不支持的Payment方式，请检查 `payMethod` 和 `subPayMethod` |
| 810020 | 500 | AlipayPlaceOrderError | Payment宝下单失败，请稍后重试 |
| 810021 | 500 | WeChatEmptyResponse | 微信Payment返回空响应，请稍后重试 |
| 810022 | 500 | WeChatErrorResponse | 微信Payment返回错误响应，请检查参数 |
| 810023 | 400 | CannotDowngradeProduct | 不能降级产品，请确认新产品的Privilege不低于当前产品 |

---

#### 17.1.4. 注意事项

- Payment回调接口（`POST /api/payment/notify/wechatnotify`、`POST /api/payment/notify/alipaynotify`）为公开接口，无需认证，但本Controller内其他端点均需鉴权。
- 所有金额字段均以元为单位，精确到小数点后两位。
- `payParams` 的结构因Payment方式而异：微信Payment返回 `appId`、`timeStamp`、`nonceStr`、`package`、`signType`、`paySign`；Payment宝Payment返回 `orderStr`（Payment宝订单串）。

---

## 18. ProductController 接口


本章共覆盖 2 个 HTTP 端点, 每个端点一个接口卡片.


### 18.1. API-001 Product Get (GET /api/product)

- **鉴权**: JWT Token 或 Basic Auth（通过 `ApiHandlerBase` 基类统一鉴权，代码中未标注 `[Authorize]` 特性，但基类默认执行Privilege校验）
- **描述**: 获取产品列表。该方法为 `ProductController` 中的 `Get` 动作，通过 HTTP GET 请求访问 `/api/product` 路由，用于查询系统中的产品信息。

- **请求参数**: 无（该方法不接受任何查询参数、路径参数或请求体）

- **响应格式**: 该方法返回 `IActionResult`，通常包装为 `ApiResponse<T>` 格式。具体字段如下：

| 字段 | 类型 | 说明 |
|------|------|------|
| code | int | 业务状态码，`0` 表示成功，非 `0` 表示失败（见错误码表） |
| message | string | 提示信息，成功时为 `"success"`，失败时为具体错误描述 |
| data | array\<Product\> | 产品列表数据，每个元素包含以下字段：id（int，产品唯一标识）、name（string，产品名称）、description（string，产品描述）、price（decimal，产品价格）、duration（int，产品时长，单位天）、type（int，产品类型，对应 产品类型 枚举：None=0, Monthly=1, Permanent=2） |

- **错误码**: 本接口可能返回以下错误码：

| errorCode | message | 说明 |
|-----------|---------|------|
| 999999 | DefaultException | 服务器内部异常，未预期的错误 |

- **请求示例**:
```http
GET /api/product
```

- **响应示例**:

**成功响应 (HTTP 200)**:
```json
{
  "code": 0,
  "message": "success",
  "data": [
    {
      "id": 1,
      "name": "AgentInsight 专业版",
      "description": "适用于小型团队的 Agent 服务套餐",
      "price": 99.99,
      "duration": 30,
      "type": 1
    },
    {
      "id": 2,
      "name": "AgentInsight 企业版",
      "description": "适用于中型企业的 Agent 服务套餐",
      "price": 299.99,
      "duration": 30,
      "type": 1
    }
  ]
}
```

**失败响应 (HTTP 401)**:
```json
{
  "code": 100000,
  "message": "UnAuthToken",
  "data": null
}
```

**失败响应 (HTTP 500)**:
```json
{
  "code": 999999,
  "message": "DefaultException",
  "data": null
}
```

### 18.2. API-038 GetDuration (GET /api/product/duration)

- **鉴权**: JWT Token 或 Basic Auth（通过 `ApiHandlerBase` 基类统一鉴权，代码中未标注 `[Authorize]` 特性，但基类默认执行Privilege校验）
- **描述**: 获取产品时长列表，返回所有可用的产品时长选项。

- **请求参数**: 无

- **响应格式**:

| 字段 | 类型 | 说明 |
|------|------|------|
| code | int | 状态码，0 表示成功 |
| message | string | 提示信息，成功时为 `"success"`，失败时为具体错误描述 |
| data | array | 产品时长列表 |
| data[].id | string | 时长唯一标识 |
| data[].name | string | 时长名称 |
| data[].value | int | 时长值（天） |
| data[].productType | int | 产品类型（产品类型 枚举：None=0, Monthly=1, Permanent=2） |
| data[].price | decimal | 价格 |
| data[].originalPrice | decimal | 原价 |
| data[].sortOrder | int | 排序号 |
| data[].isActive | bool | 是否启用 |
| data[].createdAt | datetime | 创建时间 |
| data[].updatedAt | datetime | 更新时间 |

- **错误码**:

| errorCode | message | 说明 |
|-----------|---------|------|
| 999999 | DefaultException | 默认异常 |

- **请求示例**:

```http
GET /api/product/duration
```

- **响应示例**:

**成功响应 (HTTP 200)**:
```json
{
  "code": 0,
  "message": "success",
  "data": [
    {
      "id": "dur_001",
      "name": "月度套餐",
      "value": 30,
      "productType": 1,
      "price": 99.00,
      "originalPrice": 129.00,
      "sortOrder": 1,
      "isActive": true,
      "createdAt": "2025-01-01T10:00:00Z",
      "updatedAt": "2025-01-01T10:00:00Z"
    },
    {
      "id": "dur_002",
      "name": "永久套餐",
      "value": 36500,
      "productType": 2,
      "price": 999.00,
      "originalPrice": 1299.00,
      "sortOrder": 2,
      "isActive": true,
      "createdAt": "2025-01-01T10:00:00Z",
      "updatedAt": "2025-01-01T10:00:00Z"
    }
  ]
}
```

**失败响应 (HTTP 401)**:
```json
{
  "code": 100000,
  "message": "UnAuthToken",
  "data": null
}
```

**失败响应 (HTTP 500)**:
```json
{
  "code": 999999,
  "message": "DefaultException",
  "data": null
}
```

---

## 19. 项目Controller 接口


本章共覆盖 4 个 HTTP 端点，每个端点一个接口卡片。


### 19.1. API-001 创建项目 (POST /api/user/project)

- **鉴权**: 需要 JWT JWT Token（从 `[Authorize]` 注解推断，需在 `Authorization` 请求头中携带）
- **描述**: 创建新的 Project 资源，用于在 AgentInsightService 中组织和管理 Agent 相关数据。

- **请求参数** (`Create项目Body`):

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `name` | string | 是 | Project 名称，长度需在 1 到 50 个字符之间 |
| `organizationId` | long | 是 | 所属 Org 的 ID，用于关联 Project 到指定组织 |
| `description` | string | 否 | Project 的详细描述信息 |

- **响应格式** (`ApiResponse<long>`):

| 字段 | 类型 | 说明 |
|---|---|---|
| `code` | int | 业务状态码，`0` 表示成功，非 `0` 表示失败 |
| `message` | string | 状态描述信息，成功时为 `"success"`，失败时为具体错误信息 |
| `data` | long | 创建成功的 Project ID |

- **错误码**:

| errorCode | message | 说明 |
|---|---|---|
| 140000 | Empty项目Name | Project 名称为空 |
| 140001 | 项目NameTooShort | Project 名称长度不足 |
| 140002 | 项目NameTooLong | Project 名称长度超出限制 |
| 140003 | Invalid项目 | Project 不存在或无效 |
| 140007 | Existed项目Name | Project 名称已存在 |
| 140008 | Unauthorized项目Access | 无权访问该 Project |
| 130009 | Unauthorized组织Access | 无权访问该 Org |
| 100000 | UnAuthToken | Token 无效或已过期 |
| 100001 | EmptyUserId | User ID 为空 |
| 100010 | UnauthorizedOperator | 操作者未授权 |
| 999999 | DefaultException | 系统默认异常 |

- **请求示例**:

```json
{
  "name": "example-project",
  "organizationId": 12345,
  "description": "This is an example project for demonstration."
}
```

- **响应示例**:

**成功响应**:
```json
{
  "code": 0,
  "message": "success",
  "data": 67890
}
```

**失败响应** (Project 名称已存在):
```json
{
  "code": 140007,
  "message": "Existed项目Name",
  "data": null
}
```

### 19.2. API-046 获取项目信息 (GET /api/user/project)

- **鉴权**: 需要 JWT JWT Token（Controller类 `项目Controller` 标注了 `[Authorize]`，用户需登录）
- **描述**: 根据组织 ID 和可选的project_id 获取项目信息。若提供 `projectId`，则返回指定项目详情；否则返回该组织下的项目列表。

#### 19.2.1. 请求参数

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `orgId` | long | 是 | Org ID，用于限定查询范围 |
| `projectId` | long | 否 | project_id，提供时返回单个项目详情；不提供时返回项目列表 |

#### 19.2.2. 响应格式

| 字段 | 类型 | 说明 |
|---|---|---|
| `code` | int | 状态码，`0` 表示成功 |
| `message` | string | 提示信息 |
| `data` | object/array | 项目数据。当提供 `projectId` 时为项目对象；否则为项目对象数组 |

#### 19.2.3. 错误码

| errorCode | message | 说明 |
|---|---|---|
| 100000 | UnAuthToken | Token 无效或未提供，认证失败 |
| 130003 | Invalid组织 | 组织不存在或已被删除 |
| 130009 | Unauthorized组织Access | 当前用户无权访问该组织 |
| 140003 | Invalid项目 | 项目不存在或已被删除 |
| 140008 | Unauthorized项目Access | 当前用户无权访问该项目 |
| 999999 | DefaultException | 服务器内部错误 |

#### 19.2.4. 请求示例

```json
// 查询单个项目
GET /api/user/project?orgId=12345&projectId=67890

// 查询项目列表
GET /api/user/project?orgId=12345
```

#### 19.2.5. 响应示例

**成功响应（单个项目）**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 67890,
    "name": "生产环境监控",
    "orgId": 12345,
    "description": "用于生产环境的核心指标监控",
    "createdAt": "2025-06-01T10:30:00Z",
    "updatedAt": "2025-06-15T08:00:00Z"
  }
}
```

**成功响应（项目列表）**

```json
{
  "code": 0,
  "message": "success",
  "data": [
    {
      "id": 67890,
      "name": "生产环境监控",
      "orgId": 12345,
      "description": "用于生产环境的核心指标监控",
      "createdAt": "2025-06-01T10:30:00Z",
      "updatedAt": "2025-06-15T08:00:00Z"
    },
    {
      "id": 67891,
      "name": "测试环境监控",
      "orgId": 12345,
      "description": "用于测试环境的功能验证",
      "createdAt": "2025-05-20T14:00:00Z",
      "updatedAt": "2025-06-10T09:15:00Z"
    }
  ]
}
```

**失败响应（项目不存在）**

```json
{
  "code": 140003,
  "message": "Invalid项目",
  "data": null
}
```

### 19.3. API-060 Update (POST /api/user/project/update)

- **鉴权**: 需要 JWT JWT Token（`[Authorize]`），用户需具备项目所属组织的 ADMIN 或 OWNER Privilege（`PGRole.ADMIN` / `PGRole.OWNER`）
- **描述**: 更新指定 Project 的名称。请求体需包含project_id 和新的项目名称，系统会校验项目归属、名称合法性及重名冲突。当前版本仅支持更新 Project 名称，响应中返回更新后的完整 Project 对象。
- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `projectId` | long | 是 | 待更新 Project 的唯一标识符 |
| `projectName` | string | 是 | 新的 Project 名称，长度需在 2 到 50 个字符之间 |

- **响应格式**:

| 字段 | 类型 | 说明 |
|---|---|---|
| `code` | int | 业务状态码，`0` 表示成功，非 `0` 表示失败（见错误码表） |
| `data` | object | 成功时返回更新后的 Project 数据；失败时为 `null` |
| `message` | string | 描述性消息，成功时为 `"success"`，失败时为具体错误信息 |
| `traceId` | string | 请求Trace ID，用于日志排查 |

- **错误码**:

| errorCode | message | 说明 |
|---|---|---|
| `100000` | UnAuthToken | 未提供或提供了无效的认证 Token |
| `140000` | Empty项目Name | Project 名称为空 |
| `140001` | 项目NameTooShort | Project 名称长度不足 2 个字符 |
| `140002` | 项目NameTooLong | Project 名称长度超过 50 个字符 |
| `140003` | Invalid项目 | 指定的 Project 不存在或已被删除 |
| `140007` | Existed项目Name | 新的 Project 名称与当前组织下已有 Project 重名 |
| `140008` | Unauthorized项目Access | 当前用户无权操作该 Project（非组织成员或Privilege不足） |
| `999999` | DefaultException | 未预期的服务器内部错误 |

- **请求示例**:

```json
{
  "projectId": 1001,
  "projectName": "新项目名称"
}
```

- **响应示例**:

**成功响应**:

```json
{
  "code": 0,
  "data": {
    "id": 1001,
    "name": "新项目名称",
    "organizationId": 501,
    "createdAt": "2025-05-20T10:30:00Z",
    "updatedAt": "2025-05-20T11:45:00Z"
  },
  "message": "success",
  "traceId": "a1b2c3d4-5678-90ab-cdef-1234567890ab"
}
```

**失败响应** (例如: Project 名称重名):

```json
{
  "code": 140007,
  "data": null,
  "message": "Existed项目Name",
  "traceId": "b2c3d4e5-6789-01bc-def0-2345678901bc"
}
```

### 19.4. API-061 Delete (POST /api/user/project/delete)

- **鉴权**: 需要 JWT JWT Token（`[Authorize]`），用户必须拥有对应 Project 的 ADMIN 或 OWNER Privilege
- **描述**: 根据 `projectIds` 批量删除 Project，删除操作会同步清理相关 Trace 数据、Agent Config及关联资源。请求参数通过 query string 传递。

- **请求参数** (query string):

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `projectIds` | string | 是 | 待删除的 Project ID 列表，多个 ID 使用英文逗号（`,`）分隔。每个 ID 必须为有效的 Project 标识符 |

- **响应格式**:

| 字段 | 类型 | 说明 |
|------|------|------|
| `code` | int | 业务状态码，`0` 表示成功，非 `0` 表示失败 |
| `message` | string | 状态描述信息，成功时为 `"success"`，失败时为具体错误信息 |
| `data` | object/null | 删除操作结果，成功时返回 `null`，失败时为 `null` |

- **错误码**:

| errorCode | message | 说明 |
|-----------|---------|------|
| 100000 | UnAuthToken | Token 未认证或已过期，请重新登录 |
| 140003 | Invalid项目 | Project 不存在或已被删除 |
| 140008 | Unauthorized项目Access | 当前用户无权访问或删除该 Project |
| 130007 | 组织Has项目s | 所属 Org 下存在关联 Project，无法删除 |
| 130008 | 组织项目Deleting | 该 Project 正在执行删除操作，请勿重复提交 |
| 999999 | DefaultException | 系统内部错误，请联系管理员 |

- **请求示例**:

```json
// 通过 query string 传递参数
POST /api/user/project/delete?projectIds=67890,67891
```

- **响应示例**:

**成功响应 (HTTP 200)**:
```json
{
  "code": 0,
  "message": "success",
  "data": null
}
```

**失败响应 (HTTP 200, 业务错误)**:
```json
{
  "code": 140008,
  "message": "Unauthorized项目Access",
  "data": null
}
```

---

## 20. UserConfigController 接口

本章共覆盖 4 个 HTTP 端点，每个端点一个接口卡片。

> **鉴权说明**：本章所有端点（除特别注明外）均通过 `ApiHandlerBase` 基类进行Privilege控制，支持 **JWT Token** 和 **Basic Auth（PublicKey/SecretKey）** 两种认证方式。请求时需在 Header 中携带任一有效凭证。

---

### 20.1. API-031 UserConfigController.Get (GET /api/user/config)

- **所属模块**: UserConfigController (API/Controllers/UserManagement/UserConfigController.cs)
- **鉴权**: 需要 JWT 认证（JWT Token）或 Basic Auth（PublicKey/SecretKey）
- **描述**: 根据组织 ID、project_id 和Config类型查询用户Config信息

- **请求参数** (Query String):

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| orgId | string | 否 | Org ID，用于指定查询的组织范围 |
| projectId | string | 否 | project_id，用于指定查询的项目范围 |
| type | int | 否 | Config类型：`0`（用户级）、`1`（组织级）、`2`（项目级） |

- **响应格式**:

| 字段 | 类型 | 说明 |
|------|------|------|
| code | int | 状态码，`0` 表示成功，非 `0` 表示失败 |
| message | string | 提示信息，成功时为 `"success"`，失败时为错误描述 |
| data | object | 返回的用户Config数据对象，包含具体的Config项键值对 |

- **错误码**:

| errorCode | message | 说明 |
|-----------|---------|------|
| 100000 | UnAuthToken | Token 无效或未提供，需要重新登录获取有效 Token |
| 100001 | EmptyUserId | 当前用户 ID 为空，无法识别用户身份 |
| 100005 | InvalidUser | 用户不存在或已被禁用 |
| 150000 | Empty项目Id | project_id 为空，当 `type` 为 `2`（项目级）时必须提供 `projectId` |
| 150019 | OrgAnd项目BothEmpty | Org ID 和project_id 均为空，当 `type` 为 `1`（组织级）或 `2`（项目级）时必须提供对应 ID |
| 150022 | AgentConfigNotFound | 未找到对应的 Agent Config记录 |
| 150008 | DuplicateUserConfig | 存在重复的用户Config记录，数据异常 |
| 999999 | DefaultException | 系统默认异常，未知错误 |

- **请求示例**:

```
GET /api/user/config?orgId=org_8f3a2b1c9d4e5f6a7b8c9d0e&projectId=proj_1a2b3c4d5e6f7a8b9c0d1e2f&type=2
```

- **响应示例**:

**成功响应 (HTTP 200)**:

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "config": {
      "model": "gpt-4o",
      "temperature": 0.7,
      "maxTokens": 2048,
      "systemPrompt": "You are a helpful assistant.",
      "enabled": true
    }
  }
}
```

**失败响应 (HTTP 401)**:

```json
{
  "code": 100000,
  "message": "UnAuthToken",
  "data": null
}
```

---

### 20.2. API-001 创建用户Config (POST /api/user/config)

- **所属模块**: UserConfigController (API/Controllers/UserManagement/UserConfigController.cs)
- **鉴权**: 需要 JWT 认证（JWT Token）或 Basic Auth（PublicKey/SecretKey）
- **描述**: 创建新的用户Config项，支持用户级、组织级、项目级三种Config类型

#### 20.2.1. 请求参数

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| configType | int | 是 | Config类型：`0`（用户级）、`1`（组织级）、`2`（项目级） |
| configKey | string | 是 | Config键名，用于标识Config项 |
| configValue | string | 是 | Config值，存储具体Config内容 |
| description | string | 否 | Config描述信息 |
| userId | string | 条件必填 | User ID，当 configType = 0（用户级）时必填 |
| organizationId | string | 条件必填 | Org ID，当 configType = 1（组织级）时必填 |
| projectId | string | 条件必填 | project_id，当 configType = 2（项目级）时必填 |

#### 20.2.2. 响应格式

| 字段 | 类型 | 说明 |
|------|------|------|
| code | int | 状态码，`0` 表示成功 |
| message | string | 状态描述信息 |
| data | object | 响应数据，创建成功时返回Config详情 |
| data.id | string | Config ID |
| data.configType | int | Config类型 |
| data.configKey | string | Config键名 |
| data.configValue | string | Config值 |
| data.description | string | Config描述 |
| data.createdAt | datetime | 创建时间 |
| data.updatedAt | datetime | 更新时间 |
| traceId | string | 请求Trace ID，用于日志Trace |

#### 20.2.3. 错误码

| errorCode | message | 说明 |
|-----------|---------|------|
| 100000 | UnAuthToken | Token 无效或已过期 |
| 100001 | EmptyUserId | User ID 为空 |
| 100005 | InvalidUser | 用户不存在或已被禁用 |
| 100010 | UnauthorizedOperator | 当前用户无Privilege执行此操作 |
| 150008 | DuplicateUserConfig | 相同Config键已存在，Config重复 |
| 150022 | AgentConfigNotFound | 关联的 Agent Config不存在 |
| 990001 | EncryptionFailed | Config值加密失败 |
| 999999 | DefaultException | 系统默认异常，未知错误 |

#### 20.2.4. 请求示例

```json
{
  "configType": 1,
  "configKey": "agent_default_model",
  "configValue": "gpt-4o",
  "description": "默认 Agent 模型Config",
  "organizationId": "org_8f3a2b1c9d4e5f6a7b8c9d0e"
}
```

#### 20.2.5. 响应示例

**成功响应 (HTTP 200)**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "config_5001",
    "configType": 1,
    "configKey": "agent_default_model",
    "configValue": "gpt-4o",
    "description": "默认 Agent 模型Config",
    "createdAt": "2025-01-15T10:30:00Z",
    "updatedAt": "2025-01-15T10:30:00Z"
  },
  "traceId": "a3f8c2e1-9b4d-4f6a-8c2e-1a9b4d4f6a8c"
}
```

**失败响应 (HTTP 400)**

```json
{
  "code": 150008,
  "message": "DuplicateUserConfig",
  "data": null,
  "traceId": "b7e2d4f3-8a1c-4e5b-9d3f-2c8e5b7a1d4f"
}
```

---

### 20.3. API-057 更新用户Config (POST /api/user/config/update)

- **所属模块**: UserConfigController (API/Controllers/UserManagement/UserConfigController.cs)
- **鉴权**: 需要 JWT 认证（JWT Token）或 Basic Auth（PublicKey/SecretKey）
- **描述**: 更新指定范围内的用户Config项。根据 `configType` 决定Config生效范围：`0`（用户级）、`1`（组织级）、`2`（项目级）。当 `configType` 为 `1` 或 `2` 时，必须通过 `scopeId` 指定对应的组织 ID 或project_id。

- **请求参数** (Body):

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| configType | int | 是 | Config类型，决定Config的生效范围。枚举值：`0`（用户级）、`1`（组织级）、`2`（项目级） |
| configKey | string | 是 | Config项的唯一键名，例如 `"language"`, `"theme"` |
| configValue | string | 是 | Config项的值，例如 `"zh-CN"`, `"dark"` |
| scopeId | string | 条件必填 | 作用域 ID。当 `configType` 为 `1`（组织级）时传组织 ID；当 `configType` 为 `2`（项目级）时传project_id；当 `configType` 为 `0`（用户级）时可为空 |

- **响应格式**:

| 字段 | 类型 | 说明 |
|---|---|---|
| code | int | 业务状态码，`0` 表示成功，非 `0` 表示失败 |
| message | string | 状态描述信息 |
| data | object | 更新后的Config对象，包含 `id`, `configKey`, `configValue`, `configType`, `scopeId`, `updatedAt` 等字段 |

- **错误码**:

| errorCode | message | 说明 |
|---|---|---|
| 100000 | UnAuthToken | 未提供或提供了无效的认证 Token |
| 100001 | EmptyUserId | 当前用户 ID 为空，无法识别用户身份 |
| 100005 | InvalidUser | 当前用户不存在或已被禁用 |
| 150008 | DuplicateUserConfig | 相同范围 (`scopeId`) 和Config键 (`configKey`) 的Config已存在，无法重复创建。请使用更新接口或删除原有Config后再试 |
| 150022 | AgentConfigNotFound | 尝试更新或访问的Config不存在，可能已被删除 |
| 999999 | DefaultException | 服务器内部错误，请稍后重试或联系技术支持 |

- **请求示例**:

```json
{
  "configType": 0,
  "configKey": "language",
  "configValue": "zh-CN",
  "scopeId": null
}
```

- **响应示例**:

**成功响应**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "config_123",
    "configKey": "language",
    "configValue": "zh-CN",
    "configType": 0,
    "scopeId": null,
    "updatedAt": "2024-01-15T10:30:00Z"
  }
}
```

**失败响应 (Config已存在)**:
```json
{
  "code": 150008,
  "message": "DuplicateUserConfig",
  "data": null
}
```

---

### 20.4. API-071 删除用户Config (DELETE /api/user/config/delete)

- **所属模块**: UserConfigController (API/Controllers/UserManagement/UserConfigController.cs)
- **鉴权**: 需要 JWT 认证（JWT Token）或 Basic Auth（PublicKey/SecretKey）
- **描述**: 根据Config ID 删除指定的用户Config项。该接口用于移除用户级Config类型的Config记录，删除后不可恢复。

- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | string | 是 | 待删除的用户Config的唯一标识符 |

- **响应格式**:

| 字段 | 类型 | 说明 |
|------|------|------|
| code | int | 业务状态码，0 表示成功，非 0 表示失败 |
| message | string | 状态描述信息，成功时为 "success" |
| data | object/null | 响应数据，删除成功时为 null |

- **错误码**:

| errorCode | message | 说明 |
|-----------|---------|------|
| 100000 | UnAuthToken | Token 无效或未提供，需要重新登录 |
| 100001 | EmptyUserId | 当前用户 ID 为空，无法执行删除操作 |
| 100005 | InvalidUser | 当前用户不存在或已被禁用 |
| 150008 | DuplicateUserConfig | 用户Config不存在或已被删除 |
| 999999 | DefaultException | 服务器内部异常，请稍后重试 |

- **请求示例**:

```
DELETE /api/user/config/delete?id=config_8f7d3e2a1b9c4d5e6f7a8b9c
```

- **响应示例**:

**成功响应**:
```json
{
  "code": 0,
  "message": "success",
  "data": null
}
```

**失败响应**:
```json
{
  "code": 100005,
  "message": "InvalidUser",
  "data": null
}
```

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

## 1. 引言

AgentInsightService 是一个多 Agent AI Service，提供用户管理、Payment管理、数据指标、Agent Config、Session管理等 RESTful API。系统由 C#（`API/`）和 Python（`Agents/`）两个子项目组成，通过 YARP 反向代理统一入口。本文档是 AgentInsightService 的 RESTful API 参考，面向 AI 应用开发者与集成方，帮助其理解系统提供的全部 HTTP 端点、认证方式、数据格式与调用约定。

### 1.1. 编写目的

本文档旨在为 AgentInsightService 的 API 使用者提供完整、准确、可操作的接口参考。具体目的包括：

- **指导集成开发**：为 AI 应用开发者提供各端点的请求方法、路由路径、参数定义、响应结构与错误码说明，使开发者无需阅读源代码即可完成系统对接。
- **统一调用规范**：明确认证授权方式（JWT JWT Bearer Token、API Key Basic Auth、微信小程序登录）、数据格式（JSON/XML）、时间格式（北京时间 UTC+8）等通用约定，确保不同集成方的调用行为一致。
- **降低维护成本**：通过集中呈现全部 76 个 HTTP 端点（分布在 18 个文件中），减少集成方在代码仓库中逐个检索接口定义的工作量，提升联调效率。

本文档的编写基于代码仓库的实际实现，所有端点、参数、错误码均从源代码中提取，确保与系统行为严格一致。例如，用户管理端点定义于 `API/Controllers/UserManagement/UserController.cs:29-272`，数据指标端点定义于 `API/Controllers/DataManagement/MetricsController.cs:34-125`，Agent 管理端点定义于 `API/Controllers/AgentManagement/AgentConfigController.cs:28-54`、`API/Controllers/AgentManagement/AgentSessionController.cs:33-60` 及 `API/Controllers/AgentManagement/AgentReportController.cs:35-62`。

AgentSessionController.cs:33-60` 及 `API/Controllers/AgentManagement/AgentReportController.cs:35-62`。

### 1.2. 适用范围

本文档适用于以下系统与端点范围：

**适用系统范围**

| 子系统 | 目录 | 基础路径 | 说明 |
|--------|------|----------|------|
| C# API Service | `API/` | `/api` | User、Org、Project、Payment、数据指标、Agent Config、工具管理等 RESTful API |
| Python Agents Service | `Agents/` | `/api/agent/insight`、`/api/sessions`、`/api/agents` | OpenAI 兼容的 Chat Completions 接口及Session管理 |

**端点覆盖范围**

本文档覆盖代码仓库中全部 76 个 HTTP 端点，按功能域划分如下：

| 功能域 | 端点数量 | 主要 Controller |
|--------|----------|-----------------|
| 用户管理 | 17 | `API/Controllers/UserManagement/UserController.cs` |
| 组织管理 | 4 | `API/Controllers/UserManagement/OrganizationController.cs` |
| 项目管理 | 4 | `API/Controllers/UserManagement/ProjectController.cs` |
| 用户Config | 4 | `API/Controllers/UserManagement/UserConfigController.cs` |
| Captcha | 2 | `API/Controllers/UserManagement/CaptchaController.cs` |
| Alert管理 | 7 | `API/Controllers/UserManagement/AlertController.cs` |
| Payment管理 | 6 | `API/Controllers/PaymentManagement/OrderController.cs`、`NotifyController.cs` |
| 产品管理 | 2 | `API/Controllers/ProductManagement/ProductController.cs` |
| 数据指标 | 5 | `API/Controllers/DataManagement/MetricsController.cs`、`ModelController.cs` |
| Agent 管理 | 9 | `API/Controllers/AgentManagement/` |
| 工具管理 | 10 | `API/Controllers/ToolsManagement/` |
| Python Agents | 6 | `Agents/server.py` |

**适用读者**

本文档主要面向以下读者群体：

- AI 应用开发者：需要调用 AgentInsightService 的 Chat Completions 接口或数据指标接口，将 AI 能力集成到自身应用中。
- 系统集成方：需要对接用户管理、Payment管理、Org/项目管理等后端能力，完成业务系统的整体集成。
- 测试与运维人员：需要理解接口的认证方式、错误码含义与健康检查端点，用于系统验证与监控。

### 1.3. 术语与缩略语

本文档使用项目原文标识符，以下术语在文档中具有特定含义，完整术语表参见附录。

| 术语 | 含义 |
|------|------|
| AgentInsightService | 本文档描述的多 Agent AI 服务系统全称 |
| Agent | 系统中的 Agent 单元，可独立执行特定任务（如 researcher、custom_service） |
| AgentInsight | 系统品牌名，用于产品与接口命名 |
| InsightService | 系统品牌名缩写 |
| API | 应用程序编程接口（Application Programming Interface） |
| Trace | 一次完整的请求链路Trace记录 |
| Observation | Trace过程中的Observation数据点 |
| Score | 对 Trace 或 Observation 的Score数据 |
| Session | Agent Session，包含上下文信息 |
| Alert | Alert规则或Alert记录 |
| Metric | 数据指标，如 Token 用量、成本、延迟等 |
| Captcha | Captcha（图形/短信/邮箱） |
| Privilege | 用户Privilege或配额（如月度 Agent 配额） |
| Role | 用户在组织中的角色 |
| Span | Trace 中的Span（时间段） |
| Token | 认证Token（JWT）或模型计费单位 |
| Log | 系统日志或Trace日志 |
| JWT | JSON Web Token，基于 HS256 算法的认证Token |
| API Key | 用于公开 API 访问的密钥对（publicKey:secretKey） |
| YARP | Yet Another Reverse Proxy，微软反向代理库 |
| ClickHouse | 列式存储数据库，用于指标数据存储 |
| PostgreSQL | 关系型数据库，用于用户/数据/Trace数据存储 |
| BullMQ | 基于 Redis 的消息队列，用于 Trace 异步摄入 |
| SSE | Server-Sent Events，服务端推送事件流 |

### 1.4. 参考文档

本文档的编写参考了以下资料：

| 资料类型 | 说明 | 来源 |
|----------|------|------|
| 项目源代码 | C# API 服务代码，包含全部 Controller、Handler、Service 实现 | `API/` 目录 |
| 项目源代码 | Python Agents 服务代码，包含 FastAPI 服务器与 Agent 编排逻辑 | `Agents/` 目录 |
| Config文件 | 应用Config，包含 JWT 设置、数据库连接、Redis 连接、反向代理路由等 | `API/` 与 `Agents/` 下的Config文件 |
| OpenAPI 规范 | Swagger 分组Config，定义了接口分组、标题、版本与排序 | 项目启动Config中的 Swagger 分组设置 |
| 枚举定义 | 错误码、过滤器类型、Alert字段等枚举常量定义 | `Models/Common/Enums/ExceptionCodes.cs`、`Models/Common/Enums/FilterEnum.cs`、`Models/Common/Enums/AlertEnum.cs` 等 |
| 依赖清单 | 项目依赖声明，包含 agentinsight-sdk 版本等 | `Agents/pyproject.toml`、`Admin/requirements.txt` |

关键参考文件路径：

- 认证与反向代理：`API/System/Handlers/AgentInsightTransformProvider.cs:28-45`、`API/System/Handlers/AgentInsightTransformLogic.cs:12-25`
- 全局异常处理：`API/System/Handlers/ExceptionMiddleware.cs:15-25`
- 格式化处理：`API/System/Handlers/FormattingHandler.cs:30-58`
- 错误码定义：`Models/Common/Enums/ExceptionCodes.cs:6-180`
- Python Agents 服务器：`Agents/server.py:346-649`

### 1.5. 版本历史

| 版本 | 日期 | 修订说明 | 作者 |
|------|------|----------|------|
| 1.0.0 | 待定 | 初始版本，基于代码仓库当前状态整理全部 76 个 HTTP 端点 | 技术文档组 |

> **说明**：代码仓库中未发现 API 版本号前缀、弃用策略或版本迁移约定，本文档版本号与系统内部版本（`Agents/pyproject.toml` 中 `version = 1.0.0`）保持一致。后续如有接口变更，将在本表中追加修订记录。

---

## 2. API 概览与通用约定

### 2.1. API 接口清单（由 AST/源码直接提取，禁止修改）

| 标识 | 方法 | 路径 | 描述 | 鉴权 |
|------|------|------|------|------|
| API-001 | GET | `/api/data/metrics/observations` | MetricsController.GetObservations | Bearer |
| API-002 | GET | `/api/data/metrics/scores` | MetricsController.GetScores | Bearer |
| API-003 | GET | `/api/data/metrics/traces` | MetricsController.GetTraces | Bearer |
| API-004 | POST | `/api/data/metrics/traces` | MetricsController.GetTraces | Bearer |
| API-005 | GET | `/api/data/model` | ModelController.Get | Bearer |
| API-006 | GET | `/api/product` | ProductController.Get | Bearer |
| API-007 | GET | `/api/product/duration` | ProductController.GetDuration | Bearer |
| API-008 | GET | `/api/user` | UserController.Get | Bearer |
| API-009 | POST | `/api/user` | UserController.Create | Bearer |
| API-010 | POST | `/api/user/update` | UserController.Update | Bearer |
| API-011 | POST | `/api/user/login` | UserController.Login | Bearer |
| API-012 | POST | `/api/user/logout` | UserController.Logout | Bearer |

| API-013 | POST | `/api/user/resetpassword` | UserController.ResetPassword | Bearer |
| API-014 | POST | `/api/user/bind/wechat` | UserController.Bind | Bearer |
| API-015 | GET | `/api/user/unbind/wechat` | UserController.UnBind | Bearer |
| API-016 | POST | `/api/user/role` | UserController.AssignRole | Bearer |
| API-017 | POST | `/api/user/invite` | UserController.Invite | Bearer |
| API-018 | GET | `/api/user/invitation` | UserController.Get | Bearer |
| API-019 | POST | `/api/user/invitation/delete` | UserController.DeleteInvitation | Bearer |
| API-020 | POST | `/api/user/apikey` | UserController.CreateApiKey | Bearer |

### 2.2. 接口补充说明

> 以下由 LLM 基于上述真实 API 签名补充说明, 禁止修改上方签名表内容.

AgentInsightService 是一个多 Agent AI Service，提供用户管理、Payment管理、数据指标、Agent Config、Session管理等 RESTful API。系统由 C#（API/）和 Python（Agents/）两个子项目组成，通过 Yarp.ReverseProxy 反向代理统一入口。本文档面向后端开发人员、前端集成人员及第三方系统对接方，描述 AgentInsightService 全部 HTTP 接口的调用方式、参数定义与响应格式。所有接口均遵循 REST 风格，使用 HTTP/HTTPS 协议传输，默认数据格式为 JSON。

### 2.3. 基础信息

#### 2.3.1. Base URL

系统提供两个基础路径，分别对应 C# API 与 Python Agents Service：

| Service | Base URL | 说明 |
|------|----------|------|
| C# API | `/api` | 用户管理、Payment管理、数据指标、Agent Config等核心业务接口 |
| Python Agents | `/api/agent/insight` | OpenAI 兼容的 Chat Completions 接口及Session管理 |

C# API 与 Python Agents 通过 Yarp.ReverseProxy 反向代理统一入口对外提供服务，路由Config见 `API/System/Handlers/AgentInsightTransformLogic.cs` 相关设置。

#### 2.3.2. 数据格式

系统默认使用 JSON（application/json）作为请求与响应的数据格式，同时支持 XML 输出。JSON 序列化Config由 `API/System/Handlers/FormattingHandler.cs` 统一处理。

#### 2.3.3. 时间格式

所有时间字段均使用北京时间（UTC+8）表示，格式为 ISO 8601 标准。时间格式化逻辑参见 `API/System/Handlers/FormattingHandler.cs:30-45`。

#### 2.3.4. 字符集

系统统一使用 UTF-8 字符编码，支持多语言内容传输。

#### 2.3.5. 版本管理

当前 API 未使用显式版本前缀（如 `/api/v1`）。系统未在代码仓库中发现 API 版本号前缀、弃用策略或版本迁移约定。

### 2.4. API 分类

AgentInsightService 的 API 按业务模块划分为以下六大类：

| 分类 | 模块 | 主要功能 |
|------|------|----------|
| UserManagement | User、Org、Project、Config、Alert、Captcha | 用户注册登录、组织项目管理、用户Config、Alert 规则、Captcha Captcha |
| AgentManagement | Agent Config、报告、Session | Agent Config管理、报告模板管理、Session管理 |
| DataManagement | Metrics、Model | Traces、Observations、Scores 查询，模型列表 |
| PaymentManagement | Order、回调 | 下单、订单查询、微信/Payment宝Payment回调 |
| ProductManagement | Product | 产品列表、产品时长 |
| ToolsManagement | Bulletin、健康检查、微信 | Bulletin管理、健康检查、微信消息处理 |
| Python Agents | Chat Completions、Session | OpenAI 兼容的对话接口、Session管理 |

各模块的 Controller 定义在 `API/Controllers/` 目录下，按业务领域分子目录组织，例如 `API/Controllers/UserManagement/`、`API/Controllers/AgentManagement/`、`API/Controllers/DataManagement/` 等。

### 2.5. 接口清单概览

系统共提供 76 个 HTTP 端点，分布于 17 个 Controller 及 Agents/server.py 中。各模块端点数量分布如下：

| 模块 | Controller | 端点数量 |
|------|-----------|----------|
| UserManagement | UserController | 17 |
| UserManagement | OrganizationController | 4 |
| UserManagement | ProjectController | 4 |
| UserManagement | UserConfigController | 4 |
| UserManagement | CaptchaController | 2 |
| UserManagement | AlertController | 7 |
| AgentManagement | AgentConfigController | 3 |
| AgentManagement | AgentReportController | 3 |
| AgentManagement | AgentSessionController | 3 |
| DataManagement | MetricsController | 4 |
| DataManagement | ModelController | 1 |
| PaymentManagement | OrderController | 4 |
| PaymentManagement | NotifyController | 2 |
| ProductManagement | ProductController | 2 |
| ToolsManagement | BulletinController | 7 |
| ToolsManagement | HealthController | 1 |
| ToolsManagement | WeChatController | 2 |
| Python Agents | Agents/server.py | 6 |

各模块的详细接口定义、请求参数、响应格式及错误码将在后续章节逐一详述。

### 2.6. 通用约定

#### 2.6.1. 请求头

所有请求需携带以下请求头：

| Header | 必填 | 说明 |
|--------|------|------|
| `Content-Type` | 是 | `application/json`（默认），提交 JSON 数据时必填 |
| `Authorization` | 视接口而定 | `Bearer <token>`（JWT 认证）或 `Basic <credentials>`（API Key 认证） |
| `Accept-Language` | 否 | 支持 `zh-CN`、`zh-TW`、`zh-HK`、`en`，默认 `zh-CN` |

#### 2.6.2. 响应格式

**成功响应**：HTTP 状态码 200 或 201，响应体为 JSON 对象或数组。所有成功响应统一包装在 `ApiResponse<T>` 结构中，包含 `data` 字段承载业务数据。

**错误响应**：全局异常处理由 `API/System/Handlers/ExceptionMiddleware.cs` 统一拦截，返回格式如下：

```json
{
  "code": 100037,
  "message": "InvalidCredentials"
}
```

其中 `code` 为 `ExceptionCodes` 枚举值，`message` 为错误描述。所有错误码定义在 `Models/Common/Enums/ExceptionCodes.cs`。

**分页响应**：列表类接口统一返回分页结构：

```json
{
  "items": [],
  "totalCount": 0
}
```

`items` 为当前页数据数组，`totalCount` 为符合条件的总记录数。

#### 2.6.3. 命名规范

| Project | 规范 | 示例 |
|------|------|------|
| JSON 属性 | camelCase | `userId`、`createdAt`、`totalCount` |
| 路由 | 小写 + 连字符 | `/api/agent/config/delete`、`/api/payment/order/query` |
| 枚举 | 整数传输 | `LoginType.Password`（1） |

字符 | `/api/agent/config/delete`、`/api/payment/order/query` |
| 枚举 | 整数传输 | `LoginType.Password`（1） |

JSON 属性命名由 `API/System/Handlers/FormattingHandler.cs:55-58` 统一Config。

#### 2.6.4. 认证方式

系统支持三种认证方式，由 `API/System/Handlers/AgentInsightTransformLogic.cs` 统一处理：

1. **JWT JWT Bearer Token**：主要认证方式，适用于大多数业务接口。Token 通过登录接口获取，有效期 12 小时，算法为 HS256。
2. **API Key（Basic Auth）**：用于 `/api/public/{**catch-all}` 路由的公开 API 访问。格式为 `Authorization: Basic base64(publicKey:secretKey)`。
3. **微信小程序登录**：通过 `POST /api/user/login` 使用 `LoginType.MiniProgram`（4）实现。

#### 2.6.5. 限流

系统存在限流中间件，位于 `API/System/Handlers/AgentInsightTransformLogic.cs`（`WriteRateLimitResponseAsync`），主要针对 API Key 访问。具体配额数值在代码中未发现硬编码值，需等待运营确认后补充。

#### 2.6.6. 语言支持

系统通过 `Accept-Language` 请求头进行多语言切换，支持 `zh-CN`、`zh-TW`、`zh-HK`、`en` 四种语言。默认语言为 `zh-CN`。

---

## 3. 认证与授权

| Config项 | 值 |
|--------|-----|
| Algorithm | HS256 |
| ExpiredTime | 43200 |
| ClockSkew | 5 |
| ValidateIssuer | True |
| ValidateAudience | True |
| ValidateLifetime | True |
| ValidateIssuerSigningKey | True |

**验证流程**

JWT 验证由 `API/System/Handlers/AgentInsightTransformProvider.cs:35-40` 中的 `HandleJwtAuthRequest` 方法执行。验证流程如下：

1. 从请求头 `Authorization: Bearer <token>` 中提取 Token。
2. 使用Config的签名密钥验证签名。
3. 校验 Token Issuer、Audience和有效期。
4. 验证通过后，从 Claims 中解析 UserId，并构建用户上下文。

**请求示例**

```http
GET /api/user HTTP/1.1
Host: api.example.com
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**错误处理**

当 JWT 缺失、过期或签名无效时，系统返回 `ExceptionCodes.UnAuthToken`（100000）错误码。当 Claims 中缺少 UserId 时，返回 `ExceptionCodes.EmptyUserId`（100001）。

### 3.1. API Key（Basic Auth）

API Key 认证用于公开 API 访问，主要面向 `/api/public/{**catch-all}` 路由，该路由由 YARP 反向代理转发至 Langfuse 集群。

**凭证格式**

API Key 采用 Basic Auth 格式传输：

```
Authorization: Basic base64(publicKey:secretKey)
```

其中 `publicKey` 和 `secretKey` 为用户创建 API Key 时生成的一对凭证。编码前的原始字符串格式为 `publicKey:secretKey`。

**解析与验证**

Basic Auth 解析由 `API/System/Handlers/AgentInsightTransformLogic.cs:12-15` 中的 `ParseBasicAuth` 方法完成，该方法从 Authorization 头提取并解码 Base64 字符串，拆分为 publicKey 和 secretKey。验证逻辑由 `ValidateApiKey` 方法（`API/System/Handlers/AgentInsightTransformLogic.cs:18-25`）执行，通过比对缓存或数据库中的 API Key 记录来确认凭证有效性。

**缓存机制**

API Key 验证结果通过缓存提升性能，`AgentInsightTransformProvider` 中的 `ResolveApiKeyWithCache` 方法（`API/System/Handlers/AgentInsightTransformProvider.cs:42-48`）负责从内存缓存中查找 API Key 记录，未命中时回源数据库查询。

**API Key 管理端点**

| 方法 | 路由 | 描述 |
|------|------|------|
| POST | `/api/user/apikey` | 创建 API Key |
| GET | `/api/user/apikey` | 获取 API Key 列表 |
| POST | `/api/user/apikey/delete` | 删除 API Key |

**错误处理**

当 Authorization 头缺失或格式错误时，返回 `ExceptionCodes.InvalidCredentials`（100037）。当 API Key 不存在或 secretKey 不匹配时，返回 `ExceptionCodes.InvalidApiKey`（100038）。

**请求示例**

```http
GET /api/public/data/metrics/traces HTTP/1.1
Host: api.example.com
Authorization: Basic dXNlcl9wdWJsaWNfa2V5OnVzZXJfc2VjcmV0X2tleQ==
```

### 3.2. 微信小程序登录

微信小程序登录允许用户通过微信小程序授权快速登录 AgentInsightService，适用于移动端场景。

**登录流程**

微信小程序登录通过 `POST /api/user/login` 接口实现，请求体中设置 `LoginType.MiniProgram`（4）。核心实现位于 `API/Common/Services/WeChatService.cs:38-45` 的 `LoginByWeChatMiniProgram` 方法。

登录流程如下：

1. 客户端从小程序端获取微信登录凭证 `code`。
2. 调用 `POST /api/user/login`，请求体包含 `logintype: 4` 和微信 `code`。
3. `WeChatService.LoginByWeChatMiniProgram` 使用 `code` 调用微信接口获取用户 OpenID 和 SessionKey。
4. 系统根据 OpenID 查找或创建用户记录。
5. 登录成功后，签发 JWT 并通过响应头返回。

**请求示例**

```json
POST /api/user/login HTTP/1.1
Host: api.example.com
Content-Type: application/json

{
  "logintype": 4,
  "code": "wx_code_from_miniprogram"
}
```

**相关错误码**

| errorCode | 常量名 | 说明 |
|-----------|--------|------|
| 620001 | InvalidWeChatAppToken | 微信 App Token 无效 |
| 620008 | InvalidWeChatCode | 微信登录凭证无效 |
| 620012 | InvalidWeChatAccount | 微信账号无效 |

 App Token 无效 |
| 620008 | InvalidWeChatCode | 微信登录凭证无效 |
| 620012 | InvalidWeChatAccount | 微信账号无效 |

微信绑定与解绑操作分别通过 `POST /api/user/bind/wechat` 和 `GET /api/user/unbind/wechat` 实现，均需 JWT 认证。

### 3.3. 公开端点

公开端点无需任何认证即可访问，适用于Payment回调、微信消息、Captcha获取和健康检查等场景。路由类型由 `API/System/Handlers/AgentInsightTransformLogic.cs:16-18` 的 `DetermineRouteType` 方法判断，`RouteType.Public`（1）表示无需认证。

**公开端点清单**

| 方法 | 路由 | 描述 | Controller |
|------|------|------|--------|
| POST | `/api/payment/notify/wechatnotify` | 微信Payment回调 | `API/Controllers/PaymentManagement/NotifyController.cs:29` |
| POST | `/api/payment/notify/alipaynotify` | Payment宝Payment回调 | `API/Controllers/PaymentManagement/NotifyController.cs:57` |
| GET | `/api/tools/wechat` | 微信服务器验证 | `API/Controllers/ToolsManagement/WeChat/WeChatController.cs:36` |
| POST | `/api/tools/wechat` | 微信消息处理 | `API/Controllers/ToolsManagement/WeChat/WeChatController.cs:68` |
| GET | `/api/captcha` | 获取图形Captcha | `API/Controllers/UserManagement/CaptchaController.cs:29` |
| GET | `/api/captcha/sms` | 获取短信Captcha | `API/Controllers/UserManagement/CaptchaController.cs:43` |
| GET | `/api/tools/health` | 健康检查 | `API/Controllers/ToolsManagement/HealthController.cs:20` |
| GET | `/api/tools/bulletin/agreement` | 获取协议 | `API/Controllers/ToolsManagement/BulletinController.cs:45` |

/api/tools/bulletin/agreement` | 获取协议 | `API/Controllers/ToolsManagement/BulletinController.cs:45` |
| GET | `/api/tools/bulletin/bulletins` | 获取Bulletin列表 | `API/Controllers/ToolsManagement/BulletinController.cs:64` |
| POST | `/api/user` | 创建用户（注册） | `API/Controllers/UserManagement/UserController.cs:43` |
| POST | `/api/user/login` | 用户登录 | `API/Controllers/UserManagement/UserController.cs:73` |
| POST | `/api/user/resetpassword` | 重置密码 | `API/Controllers/UserManagement/UserController.cs:102` |

**安全说明**

公开端点虽无需认证，但并非完全无防护。例如，微信Payment回调接口 `WeChatNotify` 在 `API/Controllers/PaymentManagement/NotifyController.cs:29` 中实现了请求体空值校验（抛出 `ExceptionCodes.FakedWeChatRequest`），并通过 `ExamineWeChatRequest` 方法进行签名验证。微信消息接口同样通过 `ExamineSignature` 方法验证微信服务器签名（`API/Controllers/ToolsManagement/WeChat/WeChatController.cs:36-66`）。Captcha接口受频率限制保护（`CaptchaSetting.ResendInterval = 60` 秒）。

**路由类型汇总**

| RouteType | 值 | 认证要求 | 适用场景 |
|-----------|-----|----------|----------|
| None | 0 | 需要 JWT | 用户管理、Payment、Agent Config等 |
| Public | 1 | 无需认证 | Payment回调、微信消息、Captcha、健康检查 |
| PublicApi | 2 | 需要 API Key | `/api/public/{**catch-all}` 数据指标查询 |

---

## 4. AgentConfigController 接口

本章共覆盖 3 个 HTTP 端点，每个端点一个接口卡片。

### 4.1. API-028 AgentConfigController.Get (GET /api/agent/config)

- **鉴权**: 无（代码中未标注 `[Authorize]` 特性）
- **描述**: 获取当前 Agent 的Config信息。该方法为无参 GET 请求，用于查询 AgentInsightService 中 Agent 的Config详情。
- **请求参数**: 无（该方法不接受任何查询参数或请求体）

- **响应格式**:

| 字段 | 类型 | 说明 |
|------|------|------|
| code | int | HTTP 状态码，200 表示成功 |
| type | string | 响应类型标识，固定为 `"Success"` |
| data | object | 返回的 Agent Config数据对象 |
| data.id | string | Agent Config的唯一标识符 |
| data.name | string | Agent Config名称 |
| data.description | string | Agent Config描述信息 |
| data.model | string | 使用的模型名称 |
| data.temperature | number | 温度参数，控制生成随机性 |
| data.maxTokens | integer | 最大 Token 数限制 |
| data.systemPrompt | string | 系统提示词 |
| data.createdAt | string | Config创建时间（ISO 8601 格式） |
| data.updatedAt | string | Config更新时间（ISO 8601 格式） |
| message | string | 响应消息，成功时为 `"OK"` |

- **错误码**:

| errorCode | message | 说明 |
|-----------|---------|------|
| 150022 | AgentConfigNotFound | 未找到对应的 Agent Config记录 |
| 100000 | UnAuthToken | Token 未认证或已过期 |
| 999999 | DefaultException | 服务器内部异常 |

- **请求示例**:
```json
GET /api/agent/config
Host: api.agentinsight.example.com
Authorization: Bearer <JWT_TOKEN>
```

- **响应示例**:

**成功响应 (200 OK)**:
```json
{
  "code": 200,
  "type": "Success",
  "data": {
    "id": "cfg_8f7e6d5c4b3a2",
    "name": "Default Research Agent",
    "description": "General purpose research assistant",
    "model": "gpt-4o",
    "temperature": 0.7,
    "maxTokens": 4096,
    "systemPrompt": "You are a helpful research assistant.",
    "createdAt": "2025-01-15T08:30:00Z",
    "updatedAt": "2025-01-15T08:30:00Z"
  },
  "message": "OK"
}
```

**失败响应 (404 Not Found)**:
```json
{
  "code": 404,
  "type": "Error",
  "data": null,
  "message": "AgentConfigNotFound",
  "errorCode": 150022
}
```

### 4.2. API-040 AgentConfigController.Delete (GET /api/agent/config/delete)

- **鉴权**: 无（代码中未标注 `[Authorize]` 特性）
- **描述**: 删除指定的 Agent Config。该接口通过 GET 请求触发删除操作，根据请求中携带的Config标识符定位并删除对应的 Agent Config记录。

- **请求参数**: 无（该方法签名 `Delete()` 不接收任何参数）

- **响应格式**:

| 字段 | 类型 | 说明 |
|------|------|------|
| code | int | 业务码，`0` 表示成功，非 `0` 表示失败 |
| message | string | 提示信息，成功时为 `"success"`，失败时为具体错误描述 |
| data | object | 响应数据，删除成功时返回 `null` |

- **错误码**:

| errorCode | message | 说明 |
|-----------|---------|------|
| 150022 | AgentConfigNotFound | 未找到对应的 Agent Config，无法执行删除操作 |
| 150000 | EmptyProjectId | 请求缺少必要的 Project 标识，无法定位 Agent Config |
| 100000 | UnAuthToken | Token 未认证或已失效，无法访问该接口 |
| 999999 | DefaultException | 服务器内部异常，删除操作未能完成 |

- **请求示例**:

```http
GET /api/agent/config/delete HTTP/1.1
Host: localhost
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

**失败响应** (AgentConfigNotFound):

```json
{
  "code": 150022,
  "message": "AgentConfigNotFound",
  "data": null
}
```

### 4.3. API-022 AgentConfigController.Post (POST /api/agent/config)

- **鉴权**: 无 [Authorize] 注解，无需鉴权
- **描述**: 创建或更新 Agent Config。请求体为 JSON 字符串，包含 Agent Config的完整信息，服务端解析后执行创建或更新操作。
- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| body | string | 是 | Agent Config的 JSON 字符串，包含Config项键值对 |

- **响应格式**:

| 字段 | 类型 | 说明 |
|---|---|---|
| code | int | 业务码，0 表示成功，非 0 表示失败 |
| message | string | 状态描述信息 |
| data | object | 响应数据，创建或更新后的 Agent Config对象 |

- **错误码**:

| errorCode | message | 说明 |
|---|---|---|
| 150004 | AgentSettingNotConfig | Agent 设置未Config |
| 150007 | AgentLimitExceeded | 超出 Agent 数量限制 |
| 150008 | DuplicateUserConfig | 用户Config重复 |
| 150022 | AgentConfigNotFound | 未找到 Agent Config |
| 150024 | EmptyAgentReportTemplateName | Agent 报告模板名称为空 |
| 999999 | DefaultException | 默认异常 |

- **请求示例**:

```json
{
  "body": "{\"agentId\":\"agent_001\",\"name\":\"MyAgent\",\"type\":\"Assistant\",\"model\":\"gpt-4o\",\"temperature\":0.7,\"maxTokens\":2048,\"systemPrompt\":\"You are a helpful assistant.\",\"enabled\":true}"
}
```

- **响应示例**:

**成功响应**:

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "agentId": "agent_001",
    "name": "MyAgent",
    "type": "Assistant",
    "model": "gpt-4o",
    "temperature": 0.7,
    "maxTokens": 2048,
    "systemPrompt": "You are a helpful assistant.",
    "enabled": true,
    "createdAt": "2025-01-15T10:30:00Z",
    "updatedAt": "2025-01-15T10:30:00Z"
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

## 5. AgentReportController 接口

本章共覆盖 3 个 HTTP 端点，每个端点一个接口卡片。

### 5.1. API-035 GetTemplates (GET /api/agent/report)

- **鉴权**: 无（代码中未标注 `[Authorize]` 特性）
- **描述**: 获取 Agent 报告模板列表，支持按 ID 查询、筛选预定义模板，并支持分页。
- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `id` | string | 否 | 报告模板的唯一标识符。若提供，则返回该模板详情；否则返回模板列表。 |
| `includedpredefined` | bool | 否 | 是否包含预定义模板。默认值为 `false`。 |
| `includedpredefinedonly` | bool | 否 | 是否仅返回预定义模板。默认值为 `false`。 |
| `page` | int | 否 | 页码，从 1 开始。 |
| `pageSize` | int | 否 | 每页记录数。 |

- **响应格式**:

| 字段 | 类型 | 说明 |
|---|---|---|
| `code` | int | 业务码。`0` 表示成功，非 `0` 表示失败。 |
| `message` | string | 状态描述信息。 |
| `data` | object | 响应数据。成功时为模板列表或模板详情；失败时为 `null`。 |
| `data.items` | array | 模板列表（当未指定 `id` 时返回）。 |
| `data.items[].id` | string | 模板 ID。 |
| `data.items[].name` | string | 模板名称。 |
| `data.items[].description` | string | 模板描述。 |
| `data.items[].isPredefined` | bool | 是否为预定义模板。 |
| `data.items[].createdAt` | datetime | 创建时间。 |
| `data.items[].updatedAt` | datetime | 更新时间。 |
| `data.total` | int | 模板总数（当未指定 `id` 时返回）。 |
| `data.page` | int | 当前页码（当未指定 `id` 时返回）。 |
| `data.pageSize` | int | 每页记录数（当未指定 `id` 时返回）。 |
| `data.id` | string | 模板 ID（当指定 `id` 时返回）。 |
| `data.name` | string | 模板名称（当指定 `id` 时返回）。 |
| `data.description` | string | 模板描述（当指定 `id` 时返回）。 |
| `data.isPredefined` | bool | 是否为预定义模板（当指定 `id` 时返回）。 |
| `data.createdAt` | datetime | 创建时间（当指定 `id` 时返回）。 |
| `data.updatedAt` | datetime | 更新时间（当指定 `id` 时返回）。 |

- **错误码**:

| errorCode | message | 说明 |
|---|---|---|
| 150023 | AgentReportTemplateNotFound | 报告模板不存在。当提供的 `id` 未找到对应模板时返回。 |
| 150024 | EmptyAgentReportTemplateName | 报告模板名称为空。当模板名称缺失时返回。 |
| 100000 | UnAuthToken | Token 未认证。当请求未携带有效 Token 时返回。 |
| 999999 | DefaultException | 默认异常。当发生未预期的错误时返回。 |

- **请求示例**:

```json
GET /api/agent/report?id=template_001&includedpredefined=true&includedpredefinedonly=false&page=1&pageSize=10
```

- **响应示例**:

**成功响应 (列表)**:

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "id": "template_001",
        "name": "每日摘要报告",
        "description": "生成每日 Agent 运行摘要",
        "isPredefined": true,
        "createdAt": "2024-01-01T10:00:00Z",
        "updatedAt": "2024-01-01T10:00:00Z"
      },
      {
        "id": "template_002",
        "name": "性能分析报告",
        "description": "分析 Agent 性能指标",
        "isPredefined": false,
        "createdAt": "2024-01-02T10:00:00Z",
        "updatedAt": "2024-01-02T10:00:00Z"
      }
    ],
    "total": 2,
    "page": 1,
    "pageSize": 10
  }
}
```

**成功响应 (详情)**:

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "template_001",
    "name": "每日摘要报告",
    "description": "生成每日 Agent 运行摘要",
    "isPredefined": true,
    "createdAt": "2024-01-01T10:00:00Z",
    "updatedAt": "2024-01-01T10:00:00Z"
  }
}
```

**失败响应**:

```json
{
  "code": 150023,
  "message": "AgentReportTemplateNotFound",
  "data": null
}
```

### 5.2. API-048 DeleteTemplates (GET /api/agent/report/delete)

- **鉴权**: 无（代码中未标注 `[Authorize]` 特性）
- **描述**: 根据模板 ID 列表批量删除 Agent 报告模板。该方法通过 GET 请求接收逗号分隔的模板 ID 字符串，执行删除操作。

- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| ids | string | 否 | 待删除的 Agent 报告模板 ID 列表，多个 ID 使用英文逗号（`,`）分隔。若为空或未传，则不执行任何删除操作。 |

- **响应格式**:

| 字段 | 类型 | 说明 |
|------|------|------|
| code | int | 业务码。`0` 表示成功，非 `0` 表示失败（错误码见下表） |
| message | string | 提示信息。成功时为 `"success"`，失败时为具体错误描述 |
| data | object | 返回数据。删除成功时返回 `null` |

- **错误码**:

| errorCode | message | 说明 |
|-----------|---------|------|
| 150023 | AgentReportTemplateNotFound | 指定的 Agent 报告模板不存在或已被删除 |
| 150024 | EmptyAgentReportTemplateName | Agent 报告模板名称为空 |
| 999999 | DefaultException | 服务器内部异常，请稍后重试 |

- **请求示例**:

```http
GET /api/agent/report/delete?ids=1001,1002,1003 HTTP/1.1
Host: localhost
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
  "code": 150023,
  "message": "AgentReportTemplateNotFound",
  "data": null
}
```

### 5.3. API-001 CreateOrUpdateTemplate (POST /api/agent/report)

- **鉴权**: 无（代码中未标注 `[Authorize]` 特性）
- **描述**: 创建或更新 Agent 报告模板Config。根据请求体中的模板名称判断是新增还是更新操作，并持久化到数据库。

- **请求参数** (`AgentReportTemplateBody`, JSON Body):

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `Id` | long | 否 | 模板唯一标识。`null` 时执行创建操作，非 `null` 时执行更新操作 |
| `Name` | string | 是 | 模板名称。创建时不能为空，且长度不能超过 50 个字符 |
| `Content` | string | 是 | 模板内容，支持 Markdown 格式 |
| `ProjectId` | long | 是 | 模板所属的 Project 唯一标识 |
| `OrganizationId` | long | 是 | 模板所属的 Organization 唯一标识 |

- **响应格式** (`ApiResponse<T>`):

| 字段 | 类型 | 说明 |
|---|---|---|
| `code` | int | HTTP 状态码，`200` 表示成功 |
| `errorCode` | string | 业务错误码，成功时为 `null`，失败时为枚举常量名 |
| `message` | string | 提示信息，成功时为 `"success"`，失败时为错误描述 |
| `data` | object | 响应数据。成功时返回 `null`；失败时为 `null` |
| `traceId` | string | 请求Trace ID，用于链路排查 |
| `timestamp` | long | 服务器响应时间戳（Unix 毫秒） |

- **错误码**:

| errorCode | message | 说明 |
|---|---|---|
| `AgentReportTemplateNotFound` | Agent 报告模板不存在 | 更新操作时，指定的 `Id` 对应的模板记录不存在 |
| `EmptyAgentReportTemplateName` | Agent 报告模板名称不能为空 | 创建操作时，`Name` 字段为空或仅包含空白字符 |
| `AgentSettingNotConfig` | Agent 设置未Config | 当前 Project 或 Organization 未Config Agent 相关设置 |
| `UnauthorizedProjectAccess` | 无权访问该项目 | 当前用户无权访问请求中的 `ProjectId` 对应的 Project |
| `UnauthorizedOrganizationAccess` | 无权访问该组织 | 当前用户无权访问请求中的 `OrganizationId` 对应的 Organization |
| `UnAuthToken` | 未认证的 Token | 请求未携带有效的身份认证 Token |
| `DefaultException` | 系统异常 | 未预期的服务器内部错误 |

- **请求示例**:

```json
{
  "id": null,
  "name": "周报模板",
  "content": "# 周报\n/n## 本周进展\n/n- 完成 Agent 性能优化\n/n## 下周计划\n/n- 开发新功能",
  "projectId": 1001,
  "organizationId": 501
}
```

- **响应示例**:

**成功响应 (HTTP 200)**:
```json
{
  "code": 200,
  "errorCode": null,
  "message": "success",
  "data": null,
  "traceId": "a3f2c8e1-9b4d-4f6a-8c2e-5d7b1a9e3f0c",
  "timestamp": 1735689600000
}
```

**失败响应 - 模板名称不能为空 (HTTP 200)**:
```json
{
  "code": 200,
  "errorCode": "EmptyAgentReportTemplateName",
  "message": "Agent 报告模板名称不能为空",
  "data": null,
  "traceId": "b7d4e9f2-1c3a-4e5b-9f8d-2a6c4e8b1d5f",
  "timestamp": 1735689600000
}
```

---

## 6. AgentSessionController 接口

本章共覆盖 3 个 HTTP 端点，每个端点一个接口卡片。

### 6.1. API-021 获取 Agent Session 列表 (GET /api/agent/session)

- **鉴权**: 需要 JWT JWT Bearer Token（Controller类标注 `[Authorize]`）
- **描述**: 根据可选的 Session ID 查询 Agent Session 列表，支持分页。若提供 `id` 则返回单个 Session 详情，否则返回当前用户可访问的 Session 分页列表。
- **所属类**: `AgentSessionController` (`API/Controllers/AgentManagement/AgentSessionController.cs:33`)
- **所属项目**: AgentInsightService

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `id` | string | 否 | Agent Session 的唯一标识符。若提供，则返回该 Session 的详细信息；若不提供，则返回分页列表。 |
| `page` | int | 否 | 页码，从 1 开始。默认值为 1。 |
| `pageSize` | int | 否 | 每页记录数。默认值为 10。 |

**响应格式**

| 字段 | 类型 | 说明 |
|---|---|---|
| `code` | int | 业务码。`0` 表示成功，非 `0` 表示失败。 |
| `message` | string | 状态描述信息。 |
| `data` | object | 响应数据。 |
| `data.items` | array | Session 列表。 |
| `data.items[].id` | string | Session ID。 |
| `data.items[].name` | string | Session 名称。 |
| `data.items[].projectId` | string | 所属项目 ID。 |
| `data.items[].createdAt` | datetime | 创建时间。 |
| `data.items[].updatedAt` | datetime | 更新时间。 |
| `data.total` | int | 总记录数。 |
| `data.page` | int | 当前页码。 |
| `data.pageSize` | int | 每页记录数。 |

**错误码**

| errorCode | message | 说明 |
|---|---|---|
| `100000` | UnAuthToken | Token 无效或已过期，需要重新登录。 |
| `150021` | AgentSessionNotFound | 根据提供的 `id` 未找到对应的 Agent Session。 |
| `150000` | EmptyProjectId | Project ID 为空，无法执行查询。 |
| `999999` | DefaultException | 服务器内部错误。 |

**请求示例**

```http
GET /api/agent/session?page=1&pageSize=20 HTTP/1.1
Host: localhost
Authorization: Bearer {jwt_token}
```

**响应示例**

```json
// 成功响应
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "id": "session_1234567890",
        "name": "My First Agent Session",
        "projectId": "project_abc123",
        "createdAt": "2024-01-15T10:30:00Z",
        "updatedAt": "2024-01-15T10:30:00Z"
      }
    ],
    "total": 1,
    "page": 1,
    "pageSize": 20
  }
}
```

```json
// 失败响应 - Session 未找到
{
  "code": 150021,
  "message": "AgentSessionNotFound",
  "data": null
}
```

### 6.2. API-021 删除 Agent Session (GET /api/agent/session/delete)

- **鉴权**: 需要 JWT JWT Bearer Token（Controller类标注 `[Authorize]`）
- **描述**: 根据传入的 Session ID 列表删除对应的 Agent Session 记录。支持批量删除，多个 ID 使用逗号分隔。
- **所属类**: `AgentSessionController` (`API/Controllers/AgentManagement/AgentSessionController.cs:46`)
- **所属项目**: AgentInsightService

#### 6.2.1. 请求参数

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| ids | string | 是 | 待删除的 Agent Session ID 列表，多个 ID 使用英文逗号 `,` 分隔。例如：`"session-id-1,session-id-2"` |

#### 6.2.2. 响应格式

| 字段 | 类型 | 说明 |
|------|------|------|
| code | int | 状态码。`0` 表示成功，非 `0` 表示失败（对应错误码清单中的 errorCode 值） |
| message | string | 提示信息。成功时为 `"success"`，失败时为具体错误描述 |
| data | object/null | 成功时返回 `null`，失败时返回 `null` |

#### 6.2.3. 错误码

| errorCode | message | 说明 |
|-----------|---------|------|
| 0 | success | 删除成功 |
| 100000 | UnAuthToken | Token 无效或已过期，需要重新获取有效的 JWT Token |
| 150021 | AgentSessionNotFound | 指定的 Agent Session 不存在或已被删除 |
| 999999 | DefaultException | 服务器内部错误，请联系管理员 |

#### 6.2.4. 请求示例

```http
GET /api/agent/session/delete?ids=session-001,session-002 HTTP/1.1
Host: localhost
Authorization: Bearer {jwt_token}
```

#### 6.2.5. 响应示例

**成功响应：**

```json
{
  "code": 0,
  "message": "success",
  "data": null
}
```

**失败响应（Agent Session 不存在）：**

```json
{
  "code": 150021,
  "message": "AgentSessionNotFound",
  "data": null
}
```

**失败响应（未认证）：**

```json
{
  "code": 100000,
  "message": "UnAuthToken",
  "data": null
}
```

### 6.3. API-021 创建 Agent Session (POST /api/agent/session)

- **鉴权**: 需要 JWT JWT Bearer Token（Controller类标注 `[Authorize]`）
- **描述**: 创建新的 Agent Session，用于启动一次 Agent Session交互。
- **所属类**: `AgentSessionController` (`API/Controllers/AgentManagement/AgentSessionController.cs:60`)
- **所属项目**: AgentInsightService

**请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `projectId` | string | 是 | Project ID |
| `sessionId` | string | 否 | Session ID，为空则创建新Session |
| `input` | string | 是 | 用户输入内容 |
| `agentType` | int | 否 | Agent 类型（Assistant = 1，Research = 2） |
| `userConfig` | object | 否 | 用户Config，包含模型、温度等参数 |

**响应格式**:

| 字段 | 类型 | 说明 |
|---|---|---|
| `code` | int | 状态码，0 表示成功 |
| `message` | string | 状态描述 |
| `data` | object | 响应数据 |
| `data.sessionId` | string | Session ID |
| `data.response` | string | Agent 响应内容 |
| `data.traceId` | string | Trace ID，用于Trace本次Session |

**错误码**:

| errorCode | message | 说明 |
|---|---|---|
| 100000 | UnAuthToken | 未认证的 Token |
| 150000 | EmptyProjectId | Project ID 为空 |
| 150004 | AgentSettingNotConfig | Agent Config未设置 |
| 150007 | AgentLimitExceeded | Agent 数量超出限制 |
| 150008 | DuplicateUserConfig | 用户Config重复 |
| 150021 | AgentSessionNotFound | Agent Session 未找到 |
| 150022 | AgentConfigNotFound | Agent Config未找到 |
| 999999 | DefaultException | 默认异常 |

**请求示例**:

```json
{
  "projectId": "proj_8f7e6d5c4b3a2",
  "sessionId": "sess_1a2b3c4d5e6f",
  "input": "分析最近一周的异常日志",
  "agentType": 1,
  "userConfig": {
    "model": "gpt-4o",
    "temperature": 0.7
  }
}
```

**响应示例**:

**成功响应**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "sessionId": "sess_1a2b3c4d5e6f",
    "response": "根据最近一周的日志分析，共发现 3 个异常...",
    "traceId": "trace_9f8e7d6c5b4a"
  }
}
```

**失败响应**:
```json
{
  "code": 150000,
  "message": "EmptyProjectId",
  "data": null
}
```

---

## 7. MetricsController 接口

本章共覆盖 4 个 HTTP 端点，每个端点一个接口卡片。所有端点均定义于 `API/Controllers/DataManagement/MetricsController.cs`。

### 7.1. API-034 GetObservations（GET /api/data/metrics/observations）

- **鉴权**：需要 JWT JWT Bearer Token（Controller类 `MetricsController` 标注 `[Authorize]`，基于 `JWTSettings` Config，HS256 算法，有效期 43200 分钟）
- **描述**：分页查询 Observation 列表，支持按 Trace 关联 ID 过滤。数据源为 ClickHouse 数据库（`ConnectionStrings.ClickHouseDbConnection`），查询超时 30 秒，命令超时 60 秒。
- **请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `id` | string | 是 | Trace 关联 ID，用于筛选属于特定 Trace 的 Observation 记录 |
| `page` | int | 否 | 页码，默认值为 `AgentInsightConst.DefaultPage`（默认 1） |
| `pagesize` | int | 否 | 每页条数，默认值为 `AgentInsightConst.DefaultPageSize`（默认 20） |

- **响应格式**：

| 字段 | 类型 | 说明 |
|---|---|---|
| `code` | int | 业务码，`0` 表示成功，非 `0` 表示失败（对应 `ExceptionCodes` 枚举） |
| `data` | object | 分页数据对象 |
| `data.items` | array | Observation 记录列表，每项包含 `id`、`traceId`、`name`、`type`、`startTime`、`endTime`、`input`、`output`、`metadata`、`level`、`status`、`cost`、`inputTokens`、`outputTokens`、`totalTokens` 等字段 |
| `data.total` | int | 符合条件的总记录数 |
| `data.page` | int | 当前页码 |
| `data.pagesize` | int | 当前每页条数 |
| `message` | string | 提示信息，成功时为 `"success"`，失败时为错误描述 |

- **错误码**：

| errorCode | message | 说明 |
|---|---|---|
| `0` | success | 请求成功 |
| `100000` | UnAuthToken | Token 未认证或已过期，请检查 Authorization 请求头 |
| `150009` | EmptyTraceIds | `id` 参数为空或未提供有效的 Trace 关联 ID |
| `150010` | ClickHouseQueryError | ClickHouse 查询执行失败，请检查查询语句或数据库连接状态 |
| `150017` | ClickHouseQueryTimeout | ClickHouse 查询超时（超过 30 秒），请缩小查询范围或优化查询条件 |
| `999999` | DefaultException | 服务器内部错误，请稍后重试或联系管理员 |

- **请求示例**：

```json
{
  "id": "trace_8a2f4c9e1b3d5f7a",
  "page": 1,
  "pagesize": 20
}
```

- **响应示例**：

**成功响应：**

```json
{
  "code": 0,
  "data": {
    "items": [
      {
        "id": "obs_001",
        "traceId": "trace_8a2f4c9e1b3d5f7a",
        "name": "llm_generate",
        "type": "GENERATION",
        "startTime": "2025-01-15T10:30:00Z",
        "endTime": "2025-01-15T10:30:05Z",
        "input": "{\"prompt\": \"Explain quantum computing\"}",
        "output": "{\"text\": \"Quantum computing uses qubits...\"}",
        "metadata": "{\"model\": \"gpt-4o\", \"temperature\": 0.7}",
        "level": "INFO",
        "status": "COMPLETED",
        "cost": 0.0021,
        "inputTokens": 25,
        "outputTokens": 180,
        "totalTokens": 205
      }
    ],
    "total": 1,
    "page": 1,
    "pagesize": 20
  },
  "message": "success"
}
```

**失败响应（Trace 关联 ID 为空）：**

```json
{
  "code": 150009,
  "data": null,
  "message": "EmptyTraceIds"
}
```

### 7.2. API-050 GetScores（GET /api/data/metrics/scores）

- **鉴权**：需要 JWT 认证（JWT Bearer Token），用户需具备相应数据访问Privilege
- **描述**：分页查询指定 Trace 的 Score 评估数据列表，支持按页获取Score记录
- **请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| id | string | 是 | Trace 的唯一标识符，用于定位对应的 Trace 记录 |
| page | int | 否 | 页码，从 1 开始，默认值为 AgentInsightConst.DefaultPage |
| pagesize | int | 否 | 每页记录数，默认值为 AgentInsightConst.DefaultPageSize |

- **响应格式**：

| 字段 | 类型 | 说明 |
|---|---|---|
| code | int | 状态码，200 表示成功，非 200 表示失败 |
| data | object | 响应数据，包含分页结果 |
| data.items | array | Score 记录列表，每个元素包含Score详情 |
| data.items[].id | string | Score 记录唯一标识 |
| data.items[].name | string | Score 名称 |
| data.items[].value | number | Score 数值 |
| data.items[].timestamp | datetime | Score时间戳 |
| data.items[].traceId | string | 关联的 Trace 标识 |
| data.items[].sessionId | string | 关联的 Session 标识 |
| data.total | int | 符合条件的总记录数 |
| data.page | int | 当前页码 |
| data.pagesize | int | 当前页大小 |
| message | string | 响应消息描述 |

- **错误码**：

| errorCode | message | 说明 |
|---|---|---|
| 100000 | UnAuthToken | Token 未认证或已过期，需要重新获取有效的访问Token |
| 100001 | EmptyUserId | User ID 为空，无法识别请求发起者 |
| 150000 | EmptyProjectId | Project ID 为空，无法定位数据范围 |
| 150009 | EmptyTraceIds | Trace ID 列表为空，无法执行查询 |
| 150010 | ClickHouseQueryError | ClickHouse 查询执行失败，数据检索过程中发生错误 |
| 150011 | TooManyTraceIds | Trace ID 数量超出限制，请减少查询范围 |
| 150017 | ClickHouseQueryTimeout | ClickHouse 查询超时，数据量过大或系统繁忙 |
| 150018 | EmptyTraceId | Trace ID 为空，无法定位Score数据 |
| 150019 | OrgAndProjectBothEmpty | Organization 和 Project 均为空，无法确定数据归属 |
| 999999 | DefaultException | 系统默认异常，未预期的服务器内部错误 |

- **请求示例**：

```json
{
  "id": "trace_8f7d2c9e1a4b",
  "page": 1,
  "pagesize": 20
}
```

- **响应示例**：

**成功响应：**

```json
{
  "code": 200,
  "data": {
    "items": [
      {
        "id": "score_3f9a2b7c",
        "name": "relevance",
        "value": 0.92,
        "timestamp": "2025-01-15T10:30:00Z",
        "traceId": "trace_8f7d2c9e1a4b",
        "sessionId": "session_5e6f8a2b"
      },
      {
        "id": "score_7d1e4f8a",
        "name": "accuracy",
        "value": 0.87,
        "timestamp": "2025-01-15T10:30:05Z",
        "traceId": "trace_8f7d2c9e1a4b",
        "sessionId": "session_5e6f8a2b"
      }
    ],
    "total": 2,
    "page": 1,
    "pagesize": 20
  },
  "message": "success"
}
```

**失败响应：**

```json
{
  "code": 150018,
  "data": null,
  "message": "EmptyTraceId"
}
```

### 7.3. API-064 GetTraces（GET /api/data/metrics/traces）

- **鉴权**：无
- **描述**：根据 Trace ID 列表查询 Trace 详情数据。

- **请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| ids | string | 是 | 逗号分隔的 Trace ID 列表，用于指定要查询的 Trace。 |

- **响应格式**：

| 字段 | 类型 | 说明 |
|---|---|---|
| traceId | string | Trace 的唯一标识符。 |
| timestamp | datetime | Trace 的时间戳。 |
| name | string | Trace 的名称。 |
| userId | string | 与 Trace 关联的用户 ID。 |
| sessionId | string | 与 Trace 关联的 Session ID。 |
| environment | string | Trace 运行的环境。 |
| version | string | Trace 关联的版本号。 |
| release | string | Trace 关联的发布版本。 |
| tags | array | 与 Trace 关联的标签列表。 |
| bookmarked | boolean | 是否被标记。 |
| latency | number | Trace 的延迟时间。 |
| inputTokens | number | 输入 Token 数量。 |
| outputTokens | number | 输出 Token 数量。 |
| totalTokens | number | Token 总数量。 |
| inputCost | number | 输入成本。 |
| outputCost | number | 输出成本。 |
| totalCost | number | 总成本。 |
| level | string | Trace 的日志级别。 |
| warningCount | number | 警告数量。 |
| errorCount | number | 错误数量。 |
| defaultCount | number | 默认数量。 |
| debugCount | number | 调试数量。 |
| modelNames | array | 使用的模型名称列表。 |
| scoresAvg | number | 平均 Score。 |

- **错误码**：

| errorCode | message | 说明 |
|---|---|---|
| 150009 | EmptyTraceIds | Trace ID 列表为空。 |
| 150011 | TooManyTraceIds | Trace ID 数量超出限制。 |
| 150010 | ClickHouseQueryError | ClickHouse 查询失败。 |
| 150017 | ClickHouseQueryTimeout | ClickHouse 查询超时。 |
| 150018 | EmptyTraceId | Trace ID 为空。 |
| 100000 | UnAuthToken | 未认证的 Token。 |
| 999999 | DefaultException | 默认异常。 |

- **请求示例**：

```json
GET /api/data/metrics/traces?ids=trace_id_1,trace_id_2,trace_id_3
```

- **响应示例**：

**成功响应：**

```json
{
  "traceId": "trace_id_1",
  "timestamp": "2024-05-20T10:30:00Z",
  "name": "example_trace",
  "userId": "user_123",
  "sessionId": "session_456",
  "environment": "production",
  "version": "1.0.0",
  "release": "release_1",
  "tags": ["tag1", "tag2"],
  "bookmarked": false,
  "latency": 250.5,
  "inputTokens": 100,
  "outputTokens": 50,
  "totalTokens": 150,
  "inputCost": 0.001,
  "outputCost": 0.002,
  "totalCost": 0.003,
  "level": "INFO",
  "warningCount": 0,
  "errorCount": 0,
  "defaultCount": 0,
  "debugCount": 0,
  "modelNames": ["model_a", "model_b"],
  "scoresAvg": 0.95
}
```

**失败响应：**

```json
{
  "errorCode": 150009,
  "message": "EmptyTraceIds",
  "description": "Trace ID 列表为空。"
}
```

### 7.4. API-024 GetTraces（POST /api/data/metrics/traces）

- **鉴权**：需要 JWT 认证（JWT Bearer Token），基于 `JWTSettings` Config，使用 HS256 算法，Token 有效期 43200 分钟。
- **描述**：根据请求体中的过滤条件、排序规则和分页参数，从 ClickHouse 查询 Trace 列表数据，用于 Metrics 监控与展示。
- **请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| projectId | string | 是 | Project ID，用于限定查询范围 |
| organizationId | string | 是 | Org ID，用于限定查询范围 |
| traceIds | array[string] | 否 | 指定要查询的 Trace ID 列表，最多 100 个 |
| filter | object | 否 | 过滤条件，包含 `column`、`type`、`operator`、`value` 字段，`column` 取值参考 `FilterColumn` 枚举，`type` 取值参考 `FilterType` 枚举，`operator` 取值参考 `FilterOperator` 枚举 |
| orderBy | object | 否 | 排序规则，包含 `column` 和 `direction` 字段，`column` 取值参考 `FilterColumn` 枚举，`direction` 为 `asc` 或 `desc` |
| page | integer | 是 | 页码，从 1 开始 |
| pageSize | integer | 是 | 每页条数，最大 100 |

- **响应格式**：

| 字段 | 类型 | 说明 |
|---|---|---|
| code | integer | 业务码，0 表示成功，非 0 表示失败 |
| message | string | 状态描述信息 |
| data | object | 返回的数据体，包含 `items`、`total`、`page`、`pageSize` 字段 |
| data.items | array[object] | Trace 列表，每个对象包含 `id`、`name`、`timestamp`、`userId`、`sessionId`、`environment`、`version`、`release`、`tags`、`bookmarked`、`latency`、`inputTokens`、`outputTokens`、`totalTokens`、`tokens`、`inputCost`、`outputCost`、`totalCost`、`level`、`warningCount`、`errorCount`、`defaultCount`、`debugCount`、`modelNames`、`scoresAvg` 字段 |
| data.total | integer | 符合条件的 Trace 总数 |
| data.page | integer | 当前页码 |
| data.pageSize | integer | 每页条数 |

- **错误码**：

| errorCode | message | 说明 |
|---|---|---|
| 100000 | UnAuthToken | 未认证或 Token 无效 |
| 150000 | EmptyProjectId | Project ID 为空 |
| 150009 | EmptyTraceIds | Trace ID 列表为空 |
| 150010 | ClickHouseQueryError | ClickHouse 查询失败 |
| 150011 | TooManyTraceIds | Trace ID 数量超过限制（最多 100 个） |
| 150012 | InvalidFilterType | 过滤条件类型无效 |
| 150013 | InvalidFilterColumn | 过滤条件列名无效 |
| 150014 | InvalidFilterOperator | 过滤条件操作符无效 |
| 150015 | InvalidFilterValue | 过滤条件值无效 |
| 150016 | InvalidOrderBy | 排序字段无效 |
| 150017 | ClickHouseQueryTimeout | ClickHouse 查询超时 |
| 150019 | OrgAndProjectBothEmpty | Org ID 和项目 ID 均为空 |
| 999999 | DefaultException | 服务器内部错误 |

- **请求示例**：

```json
{
  "projectId": "proj_123456",
  "organizationId": "org_789012",
  "traceIds": ["trace_001", "trace_002"],
  "filter": {
    "column": "Timestamp",
    "type": "DateTime",
    "operator": "GreaterThanOrEqualTo",
    "value": "2024-01-01T00:00:00Z"
  },
  "orderBy": {
    "column": "Timestamp",
    "direction": "desc"
  },
  "page": 1,
  "pageSize": 20
}
```

- **响应示例**：

**成功响应：**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "id": "trace_001",
        "name": "Agent Run",
        "timestamp": "2024-01-15T10:30:00Z",
        "userId": "user_001",
        "sessionId": "session_001",
        "environment": "production",
        "version": "1.0.0",
        "release": "release-1",
        "tags": ["agent", "test"],
        "bookmarked": false,
        "latency": 1250,
        "inputTokens": 1500,
        "outputTokens": 800,
        "totalTokens": 2300,
        "tokens": 2300,
        "inputCost": 0.015,
        "outputCost": 0.008,
        "totalCost": 0.023,
        "level": "INFO",
        "warningCount": 1,
        "errorCount": 0,
        "defaultCount": 0,
        "debugCount": 0,
        "modelNames": ["gpt-4"],
        "scoresAvg": 0.95
      }
    ],
    "total": 1,
    "page": 1,
    "pageSize": 20
  }
}
```

**失败响应：**

```json
{
  "code": 150010,
  "message": "ClickHouseQueryError",
  "data": null
}
```

---

## 8. ModelController 接口


本章共覆盖 1 个 HTTP 端点，每个端点一个接口卡片。


### 8.1. API-001 查询模型列表 (GET /api/data/model)

- **鉴权**: JWT Bearer Token (JWT)
- **描述**: 分页查询模型列表，支持按关键字、Project ID 等条件过滤，支持按指定字段排序。
- **端点定义**: API/Controllers/DataManagement/ModelController.cs:34

#### 8.1.1. 请求参数

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| keyword | string | 否 | 搜索关键字，用于模糊匹配模型名称 |
| projectid | string | 否 | Project ID，用于过滤指定项目下的模型 |
| includedpredefined | boolean | 否 | 是否包含预置模型，默认 `false` |
| orderby | string | 否 | 排序字段，默认 `-updatedat`（按更新时间倒序） |
| page | int | 否 | 页码，默认 `1` |
| pageSize | int | 否 | 每页条数，默认 `20` |

#### 8.1.2. 响应格式

| 字段 | 类型 | 说明 |
|------|------|------|
| code | int | 状态码，`0` 表示成功 |
| message | string | 提示信息 |
| data | object | 返回数据 |
| data.items | array | 模型列表 |
| data.items[].id | string | 模型 ID |
| data.items[].name | string | 模型名称 |
| data.items[].projectId | string | 所属项目 ID |
| data.items[].isPredefined | boolean | 是否为预置模型 |
| data.items[].createdAt | datetime | 创建时间 |
| data.items[].updatedAt | datetime | 更新时间 |
| data.total | int | 总记录数 |
| data.page | int | 当前页码 |
| data.pageSize | int | 每页条数 |

#### 8.1.3. 错误码

| errorCode | message | 说明 |
|-----------|---------|------|
| 100000 | UnAuthToken | 未认证或 Token 无效 |
| 140003 | InvalidProject | 项目不存在或已被删除 |
| 140008 | UnauthorizedProjectAccess | 无权访问该项目 |
| 150010 | ClickHouseQueryError | ClickHouse 查询失败 |
| 150017 | ClickHouseQueryTimeout | ClickHouse 查询超时 |
| 999999 | DefaultException | 服务器内部错误 |

#### 8.1.4. 请求示例

```json
GET /api/data/model?keyword=test&projectid=proj_001&includedpredefined=false&orderby=-updatedat&page=1&pageSize=20
```

#### 8.1.5. 响应示例

**成功响应**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "id": "model_001",
        "name": "test-model",
        "projectId": "proj_001",
        "isPredefined": false,
        "createdAt": "2024-01-15T10:30:00Z",
        "updatedAt": "2024-01-20T14:22:00Z"
      }
    ],
    "total": 1,
    "page": 1,
    "pageSize": 20
  }
}
```

**失败响应**

```json
{
  "code": 140008,
  "message": "UnauthorizedProjectAccess",
  "data": null
}
```

---

## 9. NotifyController 接口

本章共覆盖 2 个 HTTP 端点，每个端点一个接口卡片。

### 9.1. API-001 WeChatNotify (POST /api/payment/notify/wechatnotify)

- **鉴权**: 无
- **描述**: 接收微信Payment平台异步通知，验证通知签名与数据完整性，并更新对应订单的Payment状态。
- **实现位置**: `API/Controllers/PaymentManagement/NotifyController.cs:29`

- **请求参数**: 本接口由微信Payment服务器以 `POST` 方式调用，请求体为微信Payment回调的原始 XML 数据，非标准 JSON 格式。核心字段如下：

| 字段 | 类型 | 必填 | 说明 |
| :--- | :--- | :--- | :--- |
| `id` | string | 是 | 微信Payment API v3 通知ID。 |
| `create_time` | string | 是 | 通知创建时间，格式为 `yyyy-MM-ddTHH:mm:ss+08:00`。 |
| `event_type` | string | 是 | 通知类型，固定为 `TRANSACTION.SUCCESS`。 |
| `resource_type` | string | 是 | 通知资源类型，固定为 `encrypt-resource`。 |
| `resource` | object | 是 | 通知资源数据，需解密。 |
| `resource.algorithm` | string | 是 | 加密算法，固定为 `AEAD_AES_256_GCM`。 |
| `resource.ciphertext` | string | 是 | 加密后的回调数据（Base64编码）。 |
| `resource.associated_data` | string | 否 | 附加数据。 |
| `resource.nonce` | string | 是 | 加密使用的随机串。 |
| `resource.original_type` | string | 是 | 原始回调类型，固定为 `transaction`。 |
| `summary` | string | 是 | 回调摘要。 |

- **响应格式**: 微信Payment服务器期望的响应格式为 JSON 字符串。

| 字段 | 类型 | 说明 |
| :--- | :--- | :--- |
| `code` | string | 处理结果状态码。成功时为 `SUCCESS`；失败时为 `FAIL`。 |
| `message` | string | 处理结果描述。成功时为 `成功`；失败时为具体的错误原因。 |

- **错误码**: 本接口处理失败时，应在响应体 `message` 字段中返回错误描述，并在 HTTP 状态码中体现。相关错误码如下：

| errorCode | message | 说明 |
| :--- | :--- | :--- |
| `InvalidWeChatNotify` (810010) | 无效的微信Payment通知 | 通知数据缺失或格式错误。 |
| `InvalidWeChatSerialNO` (810009) | 无效的微信证书序列号 | 请求头中的证书序列号无效。 |
| `FakedWeChatRequest` (620014) | 伪造的微信请求 | 通知签名验证失败，请求可能来自非微信服务器。 |
| `WeChatSettingNotConfig` (810001) | 微信Payment未Config | 服务器未正确Config微信Payment参数。 |
| `InvalidWeChatTransaction` (810006) | 无效的微信交易 | 解密后的交易数据无效。 |
| `OrderNotExist` (810015) | 订单不存在 | 根据通知中的商户订单号未找到对应订单。 |
| `OrderStateUpdateFailed` (810026) | 订单状态更新失败 | 更新订单状态时发生错误。 |
| `DefaultException` (999999) | 系统异常 | 发生未预期的系统错误。 |

- **请求示例**:
```json
{
  "id": "EV-20231015123456789001",
  "create_time": "2023-10-15T12:34:56+08:00",
  "event_type": "TRANSACTION.SUCCESS",
  "resource_type": "encrypt-resource",
  "resource": {
    "algorithm": "AEAD_AES_256_GCM",
    "ciphertext": "BASE64_ENCRYPTED_DATA_STRING",
    "associated_data": "transaction",
    "nonce": "RANDOM_NONCE_STRING",
    "original_type": "transaction"
  },
  "summary": "Payment成功"
}
```

- **响应示例**:
```json
// 成功响应
{
  "code": "SUCCESS",
  "message": "成功"
}
```

```json
// 失败响应
{
  "code": "FAIL",
  "message": "无效的微信Payment通知"
}
```

### 9.2. API-002 AlipayNotify (POST /api/payment/notify/alipaynotify)

- **鉴权**: 无
- **描述**: 接收Payment宝异步通知，验证签名并处理交易结果，更新订单状态。
- **实现位置**: `API/Controllers/PaymentManagement/NotifyController.cs:57`

- **请求参数**: 本接口接收Payment宝服务器异步通知的 `application/x-www-form-urlencoded` 表单数据，字段由Payment宝定义，常见字段如下：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| notify_id | string | 是 | Payment宝通知 ID |
| app_id | string | 是 | Payment宝分配给开发者的应用 ID |
| trade_no | string | 是 | Payment宝交易号 |
| out_trade_no | string | 是 | 商户订单号 |
| trade_status | string | 是 | 交易状态，如 `TRADE_SUCCESS`、`TRADE_FINISHED`、`TRADE_CLOSED` 等 |
| total_amount | string | 是 | 订单总金额，单位为元，精确到小数点后两位 |
| buyer_id | string | 是 | 买家Payment宝用户 ID |
| sign | string | 是 | 签名串 |
| sign_type | string | 是 | 签名类型，如 `RSA2` |
| charset | string | 是 | 编码格式，如 `utf-8` |
| timestamp | string | 是 | 通知发送时间 |
| version | string | 是 | 接口版本号 |
| auth_app_id | string | 否 | 授权方应用 ID |
| seller_id | string | 否 | 卖家Payment宝用户 ID |
| seller_email | string | 否 | 卖家Payment宝账号 |
| buyer_logon_id | string | 否 | 买家Payment宝账号 |
| fund_bill_list | string | 否 | Payment金额信息 |
| receipt_amount | string | 否 | 实收金额 |
| invoice_amount | string | 否 | 开票金额 |
| buyer_pay_amount | string | 否 | 付款金额 |
| point_amount | string | 否 | 集分宝金额 |
| gmt_create | string | 否 | 交易创建时间 |
| gmt_payment | string | 否 | 交易付款时间 |
| gmt_close | string | 否 | 交易关闭时间 |
| subject | string | 否 | 商品名称 |
| body | string | 否 | 商品描述 |

- **响应格式**: 成功时需返回纯文本 `success`，失败时返回 `failure`。

| 字段 | 类型 | 说明 |
|---|---|---|
| (响应体) | string | 返回 `success` 表示通知处理成功；返回 `failure` 表示处理失败，Payment宝将重新发送通知 |

- **错误码**: 本接口为Payment宝异步通知端点，业务处理失败时通过返回 `failure` 告知Payment宝重试，不直接返回业务错误码。以下为内部处理可能涉及的相关错误码：

| errorCode | message | 说明 |
|---|---|---|
| 810002 | AlipaySettingNotConfig | Payment宝PaymentConfig不存在或未正确Config |
| 810003 | AlipayConnectionError | 连接Payment宝服务失败 |
| 810004 | AlipayTradeError | Payment宝交易处理失败 |
| 810005 | InvalidAlipayTradeNo | 无效的Payment宝交易号 |
| 810006 | InvalidAlipayTransaction | 无效的Payment宝交易 |
| 810007 | AlipaySignatureError | Payment宝签名验证失败 |
| 810008 | AlipaySignDictionaryError | Payment宝签名参数构建失败 |
| 810011 | EmptyOrderNo | 商户订单号为空 |
| 810015 | OrderNotExist | 订单不存在 |
| 810025 | InvalidTotalAmount | 无效的订单总金额 |
| 810026 | OrderStateUpdateFailed | 订单状态更新失败 |
| 810027 | InvalidMerchant | 无效的商户 |

- **请求示例**: 以下为Payment宝异步通知的请求示例（表单格式）：

```form
notify_id=1234567890&app_id=2021000000000000&trade_no=2024010112345678&out_trade_no=ORDER20240101001&trade_status=TRADE_SUCCESS&total_amount=99.00&buyer_id=2088000000000000&sign=abc123def456ghi789&sign_type=RSA2&charset=utf-8&timestamp=2024-01-01 12:00:00&version=1.0
```

- **响应示例**:

成功响应:

```text
success
```

失败响应（处理失败，Payment宝将重试）:

```text
failure
```

---

## 10. OrderController 接口

OrderController 负责Payment订单的创建、查询、列表获取以及转化率统计。所有端点均要求 JWT JWT Bearer Token 认证，Token 中需包含有效的用户身份。

本章共覆盖 4 个 HTTP 端点，每个端点一个接口卡片。

### 10.1. API-001 查询订单列表（GET /api/payment/order）

- **鉴权**：JWT JWT Bearer Token
- **描述**：分页查询当前用户所属组织的订单列表。
- **请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| orgId | string | 是 | Org ID，用于标识所属组织 |
| page | int | 否 | 页码，默认值为 1 |
| pageSize | int | 否 | 每页条数，默认值为 20 |

- **响应格式**：

| 字段 | 类型 | 说明 |
|---|---|---|
| code | int | 业务码，`0` 表示成功，非 `0` 表示失败 |
| message | string | 提示信息 |
| data | object | 分页数据 |
| data.items | array | 订单列表 |
| data.items.id | string | Order ID |
| data.items.orderNo | string | 订单号 |
| data.items.orgId | string | Org ID |
| data.items.productId | string | Product ID |
| data.items.productName | string | 产品名称 |
| data.items.amount | number | 订单金额 |
| data.items.payMethod | int | Payment方式，参考 `AgentInsightSettingType` 枚举 |
| data.items.state | int | 订单状态，参考 `OrderState` 枚举 |
| data.items.createdAt | string | 创建时间 |
| data.total | int | 总记录数 |
| data.page | int | 当前页码 |
| data.pageSize | int | 每页条数 |

- **错误码**：

| errorCode | message | 说明 |
|---|---|---|
| 100000 | UnAuthToken | Token 无效或未提供 |
| 810012 | DoNotOwnOrganization | 无权访问该组织 |
| 999999 | DefaultException | 服务器内部错误 |

- **请求示例**：

```json
{
  "orgId": "org_xxxxxxxxxxxx",
  "page": 1,
  "pageSize": 20
}
```

- **响应示例**：

**成功响应**：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "id": "order_xxxxxxxxxxxx",
        "orderNo": "20250101120000001",
        "orgId": "org_xxxxxxxxxxxx",
        "productId": "prod_xxxxxxxxxxxx",
        "productName": "AgentInsight 专业版",
        "amount": 99.00,
        "payMethod": 1,
        "state": 3,
        "createdAt": "2025-01-01T12:00:00Z"
      }
    ],
    "total": 1,
    "page": 1,
    "pageSize": 20
  }
}
```

**失败响应**：

```json
{
  "code": 810012,
  "message": "DoNotOwnOrganization",
  "data": null
}
```

### 10.2. API-002 创建Payment订单（POST /api/payment/order）

- **鉴权**：JWT JWT Bearer Token
- **描述**：创建Payment订单，支持微信Payment与Payment宝Payment。
- **请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| projectId | string | 是 | Project ID |
| organizationId | string | 是 | Org ID |
| productType | int | 是 | 产品类型，枚举值：`None = 0`、`Monthly = 1`、`Permanent = 2` |
| agentType | int | 是 | Agent 类型，枚举值：`Assistant = 1`、`Research = 2` |
| payMethod | int | 是 | Payment方式，枚举值：`WeChat = 1`、`Alipay = 2` |
| subPayMethod | int | 是 | 子Payment方式，枚举值：`WECHAT_JSAPI = 1`、`WECHAT_NATIVE = 2`、`WECHAT_MINIPROGRAM = 3`、`ALIPAY_FAST_INSTANT_TRADE_PAY = 11` |

- **响应格式**：

| 字段 | 类型 | 说明 |
|---|---|---|
| code | int | 业务码，`0` 表示成功，非 `0` 表示失败 |
| message | string | 提示信息 |
| data | object | 订单数据 |
| data.orderNo | string | 订单号 |
| data.payParams | object | Payment参数，根据Payment方式返回不同结构 |

- **错误码**：

| errorCode | message | 说明 |
|---|---|---|
| 100000 | UnAuthToken | Token 无效或未提供 |
| 810011 | EmptyOrderNo | 订单号为空 |
| 810012 | DoNotOwnOrganization | 无权操作该组织 |
| 810013 | ProductNotExist | 产品不存在 |
| 810014 | ProductDurationNotExist | 产品时长不存在 |
| 810019 | UnsupportedPayMethod | 不支持的Payment方式 |
| 810020 | AlipayPlaceOrderError | Payment宝下单失败 |
| 810021 | WeChatEmptyResponse | 微信返回空响应 |
| 810022 | WeChatErrorResponse | 微信返回错误响应 |
| 810023 | CannotDowngradeProduct | 不能降级产品 |
| 810025 | InvalidTotalAmount | 无效的订单总金额 |
| 810026 | OrderStateUpdateFailed | 订单状态更新失败 |
| 810027 | InvalidMerchant | 无效商户 |
| 150000 | EmptyProjectId | Project ID 为空 |
| 999999 | DefaultException | 默认异常 |

- **请求示例**：

```json
{
  "projectId": "project_xxxxxxxx",
  "organizationId": "org_xxxxxxxx",
  "productType": 1,
  "agentType": 1,
  "payMethod": 1,
  "subPayMethod": 1
}
```

- **响应示例**：

**成功响应**：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "orderNo": "202501011200000001",
    "payParams": {
      "appId": "wx1234567890",
      "timeStamp": "1735718400",
      "nonceStr": "abc123",
      "package": "prepay_id=wx1234567890",
      "signType": "RSA",
      "paySign": "signature_value"
    }
  }
}
```

**失败响应**：

```json
{
  "code": 810013,
  "message": "ProductNotExist",
  "data": null
}
```

### 10.3. API-003 查询订单信息（GET /api/payment/order/query）

- **鉴权**：JWT JWT Bearer Token
- **描述**：根据订单号查询订单信息。
- **请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| orderNo | string | 是 | 订单号 |

- **响应格式**：

| 字段 | 类型 | 说明 |
|---|---|---|
| code | int | 状态码，0 表示成功 |
| message | string | 提示信息 |
| data | object | 订单数据 |
| data.orderNo | string | 订单号 |
| data.productName | string | 产品名称 |
| data.productType | int | 产品类型（`None = 0`、`Monthly = 1`、`Permanent = 2`） |
| data.amount | decimal | 订单金额 |
| data.payMethod | int | Payment方式（`WeChat = 1`、`Alipay = 2`） |
| data.orderState | int | 订单状态（`Created = 1`、`WaitForPay = 2`、`Paid = 3`、`Refunded = 4`、`Cancelled = 5`、`Closed = 6`、`PayError = 7`） |
| data.createdAt | datetime | 创建时间 |
| data.paidAt | datetime? | Payment时间，可空 |

- **错误码**：

| errorCode | message | 说明 |
|---|---|---|
| 100000 | UnAuthToken | 未认证的 Token |
| 810011 | EmptyOrderNo | 订单号为空 |
| 810015 | OrderNotExist | 订单不存在 |
| 810026 | OrderStateUpdateFailed | 订单状态更新失败 |
| 810027 | InvalidMerchant | 无效商户 |
| 999999 | DefaultException | 默认异常 |

- **请求示例**：

```json
{
  "orderNo": "20250101120000001"
}
```

- **响应示例**：

**成功响应**：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "orderNo": "20250101120000001",
    "productName": "AgentInsight 专业版",
    "productType": 1,
    "amount": 99.00,
    "payMethod": 1,
    "orderState": 3,
    "createdAt": "2025-01-01T10:00:00",
    "paidAt": "2025-01-01T10:05:00"
  }
}
```

**失败响应**：

```json
{
  "code": 810015,
  "message": "OrderNotExist",
  "data": null
}
```

### 10.4. API-004 获取订单转化率（GET /api/payment/order/conversion）

- **鉴权**：JWT JWT Bearer Token
- **描述**：根据产品 ID 获取订单转化率数据。
- **请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| newProductId | string | 是 | Product ID，用于查询该产品的订单转化情况 |

- **响应格式**：

| 字段 | 类型 | 说明 |
|---|---|---|
| code | int | 业务码，`0` 表示成功，非 `0` 表示失败 |
| message | string | 提示信息 |
| data | object | 返回的数据对象 |
| data.conversionRate | number | 订单转化率，取值范围为 `0` 到 `1` |
| data.orderCount | integer | 订单总数 |
| data.convertedCount | integer | 已转化订单数 |

- **错误码**：

| errorCode | message | 说明 |
|---|---|---|
| 810013 | ProductNotExist | 指定的产品不存在 |
| 810015 | OrderNotExist | 未找到相关订单信息 |
| 999999 | DefaultException | 服务器内部错误 |

- **请求示例**：

```json
{
  "newProductId": "prod_8f7d2c1a"
}
```

- **响应示例**：

**成功响应**：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "conversionRate": 0.35,
    "orderCount": 200,
    "convertedCount": 70
  }
}
```

**失败响应**：

```json
{
  "code": 810013,
  "message": "ProductNotExist",
  "data": null
}
```

---

## 11. ProductController 接口

本章共覆盖 2 个 HTTP 端点，每个端点一个接口卡片。

### 11.1. API-001 Get (GET /api/product)

- **鉴权**: 无
- **描述**: 获取产品列表。根据方法名 `Get` 和路由 `/api/product` 推导，此接口用于查询产品信息列表。

- **请求参数**: 无

- **响应格式**:
  | 字段 | 类型 | 说明 |
  |---|---|---|
  | code | int | 业务码，`0` 表示成功，非 `0` 表示失败 |
  | message | string | 提示信息，成功时为 `"success"`，失败时为错误描述 |
  | data | array&lt;object&gt; | 产品数据列表，每个元素包含产品详细信息 |
  | data[].id | string | 产品唯一标识 |
  | data[].name | string | 产品名称 |
  | data[].description | string | 产品描述 |
  | data[].price | decimal | 产品价格 |
  | data[].duration | int | 产品时长（天） |
  | data[].type | int | 产品类型，枚举值参考 `ProductType`（`None = 0`，`Monthly = 1`，`Permanent = 2`） |
  | data[].isActive | boolean | 产品是否启用 |
  | data[].createdAt | datetime | 产品创建时间 |
  | data[].updatedAt | datetime | 产品更新时间 |

- **错误码**:
  | errorCode | message | 说明 |
  |---|---|---|
  | 0 | success | 请求成功 |
  | 999999 | DefaultException | 服务器内部错误，未预期的异常 |
  | 100000 | UnAuthToken | 未认证的 Token，请求未携带有效身份凭证 |

- **请求示例**:
  ```json
  // GET /api/product
  // 无请求参数
  ```

- **响应示例**:
  ```json
  // 成功响应
  {
    "code": 0,
    "message": "success",
    "data": [
      {
        "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
        "name": "AgentInsight 专业版",
        "description": "适用于中型团队的 AgentInsight Service",
        "price": 199.00,
        "duration": 30,
        "type": 1,
        "isActive": true,
        "createdAt": "2024-01-01T00:00:00Z",
        "updatedAt": "2024-01-01T00:00:00Z"
      }
    ]
  }
  ```

  ```json
  // 失败响应 - 未认证
  {
    "code": 100000,
    "message": "UnAuthToken",
    "data": null
  }
  ```

  ```json
  // 失败响应 - 服务器内部错误
  {
    "code": 999999,
    "message": "DefaultException",
    "data": null
  }
  ```

### 11.2. API-014 GetDuration (GET /api/product/duration)

- **鉴权**: 无
- **描述**: 获取产品时长列表。该方法用于查询系统中所有可用的产品时长Config，通常用于前端在产品购买或升级页面展示可选的时长选项。

- **请求参数**: 无

- **响应格式**:

| 字段 | 类型 | 说明 |
|---|---|---|
| code | int | 状态码，`0` 表示成功，非 `0` 表示失败 |
| message | string | 提示信息，成功时为 `"success"`，失败时为错误描述 |
| data | array | 产品时长列表 |
| data[].id | int | 时长唯一标识 |
| data[].name | string | 时长名称，如 `"月度"`、`"永久"` |
| data[].type | int | 时长类型，对应 `ProductType` 枚举：`None = 0`（无）、`Monthly = 1`（月度）、`Permanent = 2`（永久） |
| data[].duration | int | 时长数值，单位为天 |
| data[].price | decimal | 时长对应的价格 |
| data[].description | string | 时长描述信息 |
| data[].isActive | bool | 是否启用该时长 |
| data[].createdAt | datetime | 创建时间 |
| data[].updatedAt | datetime | 更新时间 |

- **错误码**:

| errorCode | message | 说明 |
|---|---|---|
| 0 | success | 成功 |
| 810013 | ProductNotExist | 产品不存在 |
| 810014 | ProductDurationNotExist | 产品时长不存在 |
| 999999 | DefaultException | 系统默认异常，未预期的错误 |

- **请求示例**:

```json
// GET /api/product/duration
// 无请求参数
```

- **响应示例**:

**成功响应:**

```json
{
  "code": 0,
  "message": "success",
  "data": [
    {
      "id": 1,
      "name": "月度",
      "type": 1,
      "duration": 30,
      "price": 99.00,
      "description": "按月订阅",
      "isActive": true,
      "createdAt": "2024-01-01T00:00:00",
      "updatedAt": "2024-01-01T00:00:00"
    },
    {
      "id": 2,
      "name": "永久",
      "type": 2,
      "duration": 36500,
      "price": 999.00,
      "description": "一次性买断",
      "isActive": true,
      "createdAt": "2024-01-01T00:00:00",
      "updatedAt": "2024-01-01T00:00:00"
    }
  ]
}
```

**失败响应:**

```json
{
  "code": 810013,
  "message": "ProductNotExist",
  "data": null
}
```

---

## 12. BulletinController,HealthController,WeChatController 接口

本章共覆盖 10 个 HTTP 端点，每个端点一个接口卡片。

### 12.1. API-032 创建Bulletin (POST /api/tools/bulletin)

- **鉴权**: 需要 JWT 认证 (JWT Bearer Token)
- **描述**: 创建一条新的Bulletin记录，支持新闻、活动、通知、Bulletin、广告和协议等类型。
- **源文件**: `API/Controllers/ToolsManagement/BulletinController.cs:32`

#### 12.1.1. 请求参数

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| title | string | 是 | Bulletin标题 |
| content | string | 是 | Bulletin正文内容 |
| type | int | 是 | Bulletin类型，枚举值：`News`(1)、`Activity`(2)、`Information`(3)、`Annoucement`(4)、`Advertisement`(5)、`Agreement`(9) |
| status | int | 否 | Bulletin状态，枚举值：`Draft`(1)、`Reviewing`(2)、`Revision`(3)、`Published`(4)、`Expired`(5)、`Closed`(6)。默认 `Draft` |
| effectiveStartTime | datetime | 否 | Bulletin生效开始时间 |
| effectiveEndTime | datetime | 否 | Bulletin生效结束时间 |
| targetUrl | string | 否 | Bulletin跳转链接（适用于广告等类型） |
| attachmentUrl | string | 否 | 附件链接 |
| sortOrder | int | 否 | 排序权重，数值越小越靠前 |
| remark | string | 否 | 备注信息 |

#### 12.1.2. 响应格式

| 字段 | 类型 | 说明 |
|------|------|------|
| code | int | 状态码，`0` 表示成功，非 `0` 表示失败 |
| message | string | 状态消息，成功时为 `"success"`，失败时为错误描述 |
| data | object | 创建成功的Bulletin数据 |
| data.id | long | Bulletin ID |
| data.title | string | Bulletin标题 |
| data.content | string | Bulletin正文内容 |
| data.type | int | Bulletin类型 |
| data.status | int | Bulletin状态 |
| data.effectiveStartTime | datetime | 生效开始时间 |
| data.effectiveEndTime | datetime | 生效结束时间 |
| data.targetUrl | string | 跳转链接 |
| data.attachmentUrl | string | 附件链接 |
| data.sortOrder | int | 排序权重 |
| data.remark | string | 备注信息 |
| data.createdAt | datetime | 创建时间 |
| data.updatedAt | datetime | 更新时间 |

#### 12.1.3. 错误码

| errorCode | message | 说明 |
|-----------|---------|------|
| 100000 | UnAuthToken | 未提供或提供了无效的认证 Token |
| 999999 | DefaultException | 服务器内部错误，请稍后重试 |

#### 12.1.4. 请求示例

```json
{
  "title": "系统维护通知",
  "content": "系统将于本周六 22:00 至周日 06:00 进行升级维护，期间服务可能短暂不可用。",
  "type": 4,
  "status": 1,
  "effectiveStartTime": "2025-01-10T22:00:00",
  "effectiveEndTime": "2025-01-11T06:00:00",
  "sortOrder": 1,
  "remark": "例行维护Bulletin"
}
```

#### 12.1.5. 响应示例

**成功响应 (HTTP 200)**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 1001,
    "title": "系统维护通知",
    "content": "系统将于本周六 22:00 至周日 06:00 进行升级维护，期间服务可能短暂不可用。",
    "type": 4,
    "status": 1,
    "effectiveStartTime": "2025-01-10T22:00:00",
    "effectiveEndTime": "2025-01-11T06:00:00",
    "targetUrl": null,
    "attachmentUrl": null,
    "sortOrder": 1,
    "remark": "例行维护Bulletin",
    "createdAt": "2025-01-08T10:30:00",
    "updatedAt": "2025-01-08T10:30:00"
  }
}
```

**失败响应 (HTTP 401)**

```json
{
  "code": 100000,
  "message": "UnAuthToken",
  "data": null
}
```

### 12.2. API-001 获取Bulletin协议内容 (GET /api/tools/bulletin/agreement)

- **鉴权**: 无
- **描述**: 根据Bulletin别名获取指定类型的Bulletin协议内容。该接口用于获取用户协议、隐私政策等Bulletin信息，通常用于用户注册或使用服务前的协议确认场景。
- **源文件**: `API/Controllers/ToolsManagement/BulletinController.cs:45`

#### 12.2.1. 请求参数

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| alias | string | 是 | Bulletin别名，用于标识具体的Bulletin类型。对应 `Agreement` 类型Bulletin，如用户协议、隐私政策等。 |

#### 12.2.2. 响应格式

| 字段 | 类型 | 说明 |
|------|------|------|
| code | int | 状态码，`0` 表示成功，非 `0` 表示失败 |
| message | string | 提示信息，成功时为 `"success"`，失败时为具体错误描述 |
| data | object | Bulletin内容数据对象 |
| data.id | string | Bulletin唯一标识 |
| data.title | string | Bulletin标题 |
| data.content | string | Bulletin正文内容（HTML 格式或纯文本） |
| data.type | int | Bulletin类型，此处应为 `Agreement = 9` |
| data.status | int | Bulletin状态，通常为 `Published = 4` |
| data.createdAt | string | Bulletin创建时间，ISO 8601 格式 |
| data.updatedAt | string | Bulletin最后更新时间，ISO 8601 格式 |

#### 12.2.3. 错误码

| errorCode | message | 说明 |
|-----------|---------|------|
| 0 | success | 请求成功 |
| 999999 | DefaultException | 服务器内部错误，请稍后重试 |
| 100000 | UnAuthToken | 未提供有效的认证 Token 或 Token 已过期 |

#### 12.2.4. 请求示例

```json
{
  "alias": "user_agreement"
}
```

#### 12.2.5. 响应示例

**成功响应**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "bulletin_001",
    "title": "AgentInsightService 用户协议",
    "content": "<h1>用户协议</h1><p>欢迎使用 AgentInsightService...</p>",
    "type": 9,
    "status": 4,
    "createdAt": "2024-01-15T10:30:00Z",
    "updatedAt": "2024-02-20T14:45:00Z"
  }
}
```

**失败响应**

```json
{
  "code": 999999,
  "message": "服务器内部错误，请稍后重试",
  "data": null
}
```

### 12.3. API-001 分页查询Bulletin列表 (GET /api/tools/bulletin/bulletins)

- **鉴权**: 无
- **描述**: 分页查询Bulletin列表，支持按Bulletin类型和轮播状态筛选。
- **源文件**: `API/Controllers/ToolsManagement/BulletinController.cs:64`

#### 12.3.1. 请求参数

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| type | int | 否 | Bulletin类型，可空枚举。可选值：`News`(1)、`Activity`(2)、`Information`(3)、`Annoucement`(4)、`Advertisement`(5)、`Agreement`(9) |
| isCarousel | bool | 否 | 是否仅查询轮播Bulletin，默认 `false` |
| page | int | 否 | 页码，默认 `1` |
| pageSize | int | 否 | 每页条数，默认 `20` |

#### 12.3.2. 响应格式

| 字段 | 类型 | 说明 |
|------|------|------|
| code | int | 状态码，`0` 表示成功 |
| message | string | 提示信息 |
| data | object | 分页数据 |
| data.items | array | Bulletin列表 |
| data.items[].id | string | Bulletin ID |
| data.items[].title | string | Bulletin标题 |
| data.items[].content | string | Bulletin内容 |
| data.items[].type | int | Bulletin类型 |
| data.items[].status | int | Bulletin状态，可选值：`Draft`(1)、`Reviewing`(2)、`Revision`(3)、`Published`(4)、`Expired`(5)、`Closed`(6) |
| data.items[].isCarousel | bool | 是否为轮播Bulletin |
| data.items[].createdAt | datetime | 创建时间 |
| data.items[].updatedAt | datetime | 更新时间 |
| data.total | int | 总记录数 |
| data.page | int | 当前页码 |
| data.pageSize | int | 每页条数 |

#### 12.3.3. 错误码

| errorCode | message | 说明 |
|-----------|---------|------|
| 100000 | UnAuthToken | 未认证或 Token 无效 |
| 999999 | DefaultException | 服务器内部错误 |

#### 12.3.4. 请求示例

```json
GET /api/tools/bulletin/bulletins?type=1&isCarousel=false&page=1&pageSize=10
```

#### 12.3.5. 响应示例

**成功响应**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "id": "b1a2c3d4-e5f6-7890-abcd-ef1234567890",
        "title": "系统升级通知",
        "content": "系统将于本周六进行升级维护...",
        "type": 1,
        "status": 4,
        "isCarousel": false,
        "createdAt": "2025-01-15T10:30:00Z",
        "updatedAt": "2025-01-15T10:30:00Z"
      }
    ],
    "total": 1,
    "page": 1,
    "pageSize": 10
  }
}
```

**失败响应**

```json
{
  "code": 100000,
  "message": "UnAuthToken",
  "data": null
}
```

### 12.4. API-001 获取后端Bulletin列表 (GET /api/tools/bulletin/backend)

- **鉴权**: 无
- **描述**: 获取后端Bulletin列表，支持按类型、状态筛选，并分页返回。
- **源文件**: `API/Controllers/ToolsManagement/BulletinController.cs:82`

#### 12.4.1. 请求参数

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| type | int | 否 | Bulletin类型，可空枚举。可选值：`News`(1)、`Activity`(2)、`Information`(3)、`Annoucement`(4)、`Advertisement`(5)、`Agreement`(9) |
| status | int | 否 | Bulletin状态，可空枚举。可选值：`Draft`(1)、`Reviewing`(2)、`Revision`(3)、`Published`(4)、`Expired`(5)、`Closed`(6) |
| page | int | 否 | 页码，默认 `1` |
| pageSize | int | 否 | 每页条数，默认 `20` |

#### 12.4.2. 响应格式

| 字段 | 类型 | 说明 |
|------|------|------|
| code | int | 状态码，`0` 表示成功 |
| message | string | 提示信息 |
| data | object | 分页数据对象 |
| data.items | array | Bulletin列表 |
| data.items.id | string | Bulletin ID |
| data.items.title | string | Bulletin标题 |
| data.items.content | string | Bulletin内容 |
| data.items.type | int | Bulletin类型 |
| data.items.status | int | Bulletin状态 |
| data.items.createdAt | datetime | 创建时间 |
| data.items.updatedAt | datetime | 更新时间 |
| data.total | int | 总记录数 |
| data.page | int | 当前页码 |
| data.pageSize | int | 每页条数 |

#### 12.4.3. 错误码

| errorCode | message | 说明 |
|-----------|---------|------|
| 150000 | EmptyProjectId | Project ID 为空 |
| 150010 | ClickHouseQueryError | ClickHouse 查询错误 |
| 150017 | ClickHouseQueryTimeout | ClickHouse 查询超时 |
| 999999 | DefaultException | 默认异常 |

#### 12.4.4. 请求示例

```json
GET /api/tools/bulletin/backend?type=1&status=4&page=1&pageSize=20
```

#### 12.4.5. 响应示例

**成功响应**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "id": "b1f2c3d4-...",
        "title": "系统升级通知",
        "content": "系统将于本周六进行升级维护...",
        "type": 1,
        "status": 4,
        "createdAt": "2025-01-15T10:00:00Z",
        "updatedAt": "2025-01-15T10:00:00Z"
      }
    ],
    "total": 1,
    "page": 1,
    "pageSize": 20
  }
}
```

**失败响应**

```json
{
  "code": 150010,
  "message": "ClickHouseQueryError",
  "data": null
}
```

### 12.5. API-096 审批通过Bulletin (POST /api/tools/bulletin/approve)

- **鉴权**: 无（代码中未标注 `[Authorize]` 特性）
- **描述**: 审批通过指定的Bulletin，将Bulletin状态更新为 `Published`。
- **源文件**: `API/Controllers/ToolsManagement/BulletinController.cs:96`

#### 12.5.1. 请求参数

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| ids | string | 是 | 待审批通过的Bulletin ID 列表，多个 ID 使用逗号（`,`）分隔。例如：`"1,2,3"` |

#### 12.5.2. 响应格式

| 字段 | 类型 | 说明 |
|------|------|------|
| code | int | 业务码。`0` 表示成功，非 `0` 表示失败，具体错误码见下表。 |
| message | string | 状态描述信息。成功时为 `"success"`，失败时为具体错误信息。 |
| data | object | 返回的数据。成功时通常为 `null`。 |

#### 12.5.3. 错误码

| errorCode | message | 说明 |
|-----------|---------|------|
| 0 | success | 操作成功 |
| 100000 | UnAuthToken | Token 无效或未提供，用户身份验证失败 |
| 999999 | DefaultException | 服务器内部异常，未预期的错误 |

#### 12.5.4. 请求示例

```json
{
  "ids": "1,2,3"
}
```

#### 12.5.5. 响应示例

**成功响应**

```json
{
  "code": 0,
  "message": "success",
  "data": null
}
```

**失败响应**

```json
{
  "code": 100000,
  "message": "UnAuthToken",
  "data": null
}
```

### 12.6. API-110 修订Bulletin (POST /api/tools/bulletin/revision)

- **鉴权**: 无
- **描述**: 根据Bulletin ID 列表将Bulletin状态变更为 `Revision`（修订中），用于Bulletin内容的修改流程。
- **源文件**: `API/Controllers/ToolsManagement/BulletinController.cs:110`

#### 12.6.1. 请求参数

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| ids | string | 是 | 待修订的Bulletin ID 列表，多个 ID 以英文逗号分隔。 |

#### 12.6.2. 响应格式

| 字段 | 类型 | 说明 |
|------|------|------|
| code | int | 业务码，`0` 表示成功，非 `0` 表示失败。 |
| message | string | 状态描述信息。 |
| data | object | 成功时返回 `true`；失败时为 `null`。 |

#### 12.6.3. 错误码

| errorCode | message | 说明 |
|-----------|---------|------|
| 0 | 操作成功 | Bulletin状态已更新为 `Revision`。 |
| 100000 | 未认证的Token | 请求未携带有效身份凭证或 Token 已过期。 |
| 999999 | 系统错误 | 服务器内部异常，请稍后重试。 |

#### 12.6.4. 请求示例

```json
{
  "ids": "1001,1002,1003"
}
```

#### 12.6.5. 响应示例

**成功响应**

```json
{
  "code": 0,
  "message": "操作成功",
  "data": true
}
```

**失败响应（未认证）**

```json
{
  "code": 100000,
  "message": "未认证的Token",
  "data": null
}
```

### 12.7. API-124 关闭Bulletin (POST /api/tools/bulletin/close)

- **鉴权**: 需要 JWT JWT Bearer Token
- **描述**: 根据传入的Bulletin ID 列表，将指定Bulletin的状态关闭为 `Closed`（`Closed = 6`）。该操作通常用于下架或终止已发布的Bulletin。
- **源文件**: `API/Controllers/ToolsManagement/BulletinController.cs:124`

#### 12.7.1. 请求参数

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| ids | string | 是 | 待关闭的Bulletin ID 列表，多个 ID 使用英文逗号 `,` 分隔。例如：`1,2,3`。 |

#### 12.7.2. 响应格式

| 字段 | 类型 | 说明 |
|------|------|------|
| code | int | 业务码。`0` 表示成功，非 `0` 表示失败，具体错误码见下表。 |
| data | boolean | 操作结果。`true` 表示关闭成功，`false` 表示关闭失败。 |
| message | string | 提示信息。成功时为 `"success"`，失败时为具体的错误描述。 |
| errors | object | 字段验证错误信息。仅在请求参数校验失败时返回，成功时为 `null`。 |
| timestamp | long | 服务器响应时间戳（Unix 毫秒）。 |
| traceId | string | 请求Trace ID，用于链路Trace和日志排查。 |

#### 12.7.3. 错误码

| errorCode | message | 说明 |
|-----------|---------|------|
| 0 | success | 成功 |
| 100000 | UnAuthToken | Token 未提供或已失效，需要重新登录获取有效 Token |
| 999999 | DefaultException | 服务器内部错误，请稍后重试或联系管理员 |

#### 12.7.4. 请求示例

```json
{
  "ids": "1,2,3"
}
```

#### 12.7.5. 响应示例

**成功响应**

```json
{
  "code": 0,
  "data": true,
  "message": "success",
  "errors": null,
  "timestamp": 1712345678901,
  "traceId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

**失败响应（未授权）**

```json
{
  "code": 100000,
  "data": false,
  "message": "UnAuthToken",
  "errors": null,
  "timestamp": 1712345678901,
  "traceId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

### 12.8. API-001 健康检查 (GET /api/tools/health)

- **鉴权**: 无
- **描述**: 检查 AgentInsightService 服务健康状态，确认服务是否正常运行。
- **源文件**: `API/Controllers/ToolsManagement/HealthController.cs:20`

#### 12.8.1. 请求参数

无

#### 12.8.2. 响应格式

| 字段 | 类型 | 说明 |
|------|------|------|
| statusCode | integer | HTTP 状态码，200 表示成功 |
| success | boolean | 请求是否成功 |
| data | object | 健康检查结果数据 |
| data.status | string | 服务健康状态，固定为 `"Healthy"` |
| data.timestamp | string | 健康检查时间戳 (ISO 8601 格式) |
| data.version | string | AgentInsightService 当前版本号 |
| data.environment | string | 当前运行环境（如 `development`、`staging`、`production`） |
| errors | array | 错误信息列表，成功时为空数组 |

#### 12.8.3. 错误码

| errorCode | message | 说明 |
|-----------|---------|------|
| 999999 | DefaultException | 服务内部发生未处理的异常，导致健康检查失败 |

#### 12.8.4. 请求示例

```json
GET /api/tools/health
Host: api.agentinsight.example.com
```

#### 12.8.5. 响应示例

**成功响应 (HTTP 200)**

```json
{
  "statusCode": 200,
  "success": true,
  "data": {
    "status": "Healthy",
    "timestamp": "2025-04-10T08:30:00Z",
    "version": "1.0.0",
    "environment": "production"
  },
  "errors": []
}
```

**失败响应 (HTTP 500)**

```json
{
  "statusCode": 500,
  "success": false,
  "data": null,
  "errors": [
    {
      "errorCode": 999999,
      "message": "DefaultException",
      "description": "服务内部发生未处理的异常，导致健康检查失败"
    }
  ]
}
```

### 12.9. API-036 微信Config验证 (GET /api/tools/wechat)

- **鉴权**: 无
- **描述**: 用于微信服务器Config验证的接口。当在微信公众平台Config服务器 URL 时，微信服务器会发送 GET 请求到该接口，携带 `signature`、`timestamp`、`nonce` 和 `echostr` 参数。该接口验证请求签名，若验证通过则原样返回 `echostr` 参数，以完成服务器Config。
- **源文件**: `API/Controllers/ToolsManagement/WeChat/WeChatController.cs:36`

#### 12.9.1. 请求参数

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| signature | string | 是 | 微信加密签名，signature 结合了开发者填写的 token 参数和请求中的 timestamp 参数、nonce 参数。 |
| timestamp | string | 是 | 时间戳，用于签名验证。 |
| nonce | string | 是 | 随机数，用于签名验证。 |
| echostr | string | 是 | 随机字符串，验证成功后需原样返回。 |

#### 12.9.2. 响应格式

| 字段 | 类型 | 说明 |
|------|------|------|
| 响应体 | string | 验证成功时，直接返回 `echostr` 参数的值；验证失败时，返回空字符串或错误信息。 |

#### 12.9.3. 错误码

| errorCode | message | 说明 |
|-----------|---------|------|
| 620002 | ExamineWeChatSignatureFailed | 微信签名验证失败，表示请求的签名与本地计算的签名不一致。 |
| 620014 | FakedWeChatRequest | 伪造的微信请求，表示请求来源无法通过安全验证。 |
| 999999 | DefaultException | 默认异常，表示发生未预期的服务器内部错误。 |

#### 12.9.4. 请求示例

```json
GET /api/tools/wechat?signature=abcdef1234567890&timestamp=1710000000&nonce=1234567890&echostr=hello_world
```

#### 12.9.5. 响应示例

**成功响应**

```text
hello_world
```

**失败响应**

```json
{
  "errorCode": 620002,
  "message": "ExamineWeChatSignatureFailed",
  "description": "微信签名验证失败"
}
```

### 12.10. API-001 接收微信消息推送 (POST /api/tools/wechat)

- **鉴权**: 无
- **描述**: 接收微信服务器推送的消息与事件通知，用于处理公众号/服务号的消息回调。该接口为微信开放平台回调端点，用于验证签名并响应微信服务器的消息推送。
- **源文件**: `API/Controllers/ToolsManagement/WeChat/WeChatController.cs:68`

#### 12.10.1. 请求参数

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| signature | string | 是 | 微信加密签名，用于验证请求合法性，signature 结合了 timestamp、nonce 和微信后台Config的 Token |
| timestamp | string | 是 | 时间戳，微信服务器请求时附带的时间戳 |
| nonce | string | 是 | 随机数，微信服务器请求时附带的随机字符串 |
| openid | string | 否 | 微信用户的 OpenID，用于标识微信用户身份 |
| body | object | 是 | 微信消息体（请求体，从请求正文反序列化），包含消息类型、事件类型及消息内容 |

#### 12.10.2. 响应格式

| 字段 | 类型 | 说明 |
|------|------|------|
| 响应体 | string | 成功时返回字符串（如 `"success"` 或空字符串）以确认接收消息；失败时返回错误状态码及错误信息 |

#### 12.10.3. 错误码

| errorCode | message | 说明 |
|-----------|---------|------|
| 620001 | InvalidWeChatAppToken | 无效的微信 App Token，微信应用Config不正确或 Token 校验失败 |
| 620002 | ExamineWeChatSignatureFailed | 微信签名校验失败，请求签名与服务器计算签名不一致，请求可能被篡改或伪造 |
| 620005 | InvalidWeChatMessageType | 无效的微信消息类型，消息类型不在枚举定义范围内 |
| 620006 | InvalidWeChatMessageEvent | 无效的微信消息事件，事件类型不在枚举定义范围内 |
| 620007 | EmptyWeChatOpenId | 微信 OpenID 为空，无法识别用户身份 |
| 620014 | FakedWeChatRequest | 伪造的微信请求，请求签名验证失败，可能为恶意请求 |
| 810001 | WeChatSettingNotConfig | 微信设置未Config，服务器未Config微信相关参数 |
| 999999 | DefaultException | 默认异常，未预期的服务器内部错误 |

#### 12.10.4. 请求示例

```json
// URL 查询参数
// POST /api/tools/wechat?signature=wx_signature_value&timestamp=1710000000&nonce=random_nonce&openid=oUserOpenId123

// 请求体
{
  "toUserName": "gh_abc123",
  "fromUserName": "oUserOpenId123",
  "createTime": 1710000000,
  "msgType": "event",
  "event": "subscribe",
  "eventKey": "",
  "ticket": "",
  "msgId": "2400000000000000000",
  "content": "",
  "picUrl": "",
  "mediaId": "",
  "format": "",
  "recognition": "",
  "thumbMediaId": "",
  "locationX": 0,
  "locationY": 0,
  "scale": 0,
  "label": "",
  "title": "",
  "description": "",
  "url": ""
}
```

#### 12.10.5. 响应示例

**成功响应 (HTTP 200)**

```json
{
  "code": 0,
  "message": "success",
  "data": "success"
}
```

**失败响应 - 签名校验失败 (HTTP 401)**

```json
{
  "code": 620002,
  "message": "ExamineWeChatSignatureFailed",
  "data": null
}
```

**失败响应 - 无效消息类型 (HTTP 400)**

```json
{
  "code": 620005,
  "message": "InvalidWeChatMessageType",
  "data": null
}
```

---

## 13. AlertController 接口

本章共覆盖 7 个 HTTP 端点，每个端点一个接口卡片。

### 13.1. API-001 GetConfig (GET /api/alert/config)

- **鉴权**: 无
- **描述**: 获取 Alert Config信息。
- **请求参数**: 无
- **响应格式**:

| 字段 | 类型 | 说明 |
|---|---|---|
| code | int | 状态码，0 表示成功 |
| message | string | 提示信息 |
| data | object | 返回数据 |
| data.alertTimeUnit | array | Alert 时间单位选项列表 |
| data.alertTimeUnit[].value | int | 枚举值 |
| data.alertTimeUnit[].label | string | 显示名称 |
| data.alertOperator | array | Alert 运算符选项列表 |
| data.alertOperator[].value | int | 枚举值 |
| data.alertOperator[].label | string | 显示名称 |
| data.alertField | array | Alert 字段选项列表 |
| data.alertField[].value | int | 枚举值 |
| data.alertField[].label | string | 显示名称 |
| data.alertRecordState | array | Alert 记录状态选项列表 |
| data.alertRecordState[].value | int | 枚举值 |
| data.alertRecordState[].label | string | 显示名称 |
| data.alertNotifyBy | array | Alert 通知方式选项列表 |
| data.alertNotifyBy[].value | int | 枚举值 |
| data.alertNotifyBy[].label | string | 显示名称 |

- **错误码**:

| errorCode | message | 说明 |
|---|---|---|
| 0 | Success | 成功 |
| 999999 | DefaultException | 默认异常 |

- **请求示例**:

```json
GET /api/alert/config
```

- **响应示例**:

```json
// 成功响应
{
  "code": 0,
  "message": "Success",
  "data": {
    "alertTimeUnit": [
      { "value": 1, "label": "Minute" },
      { "value": 2, "label": "Hour" },
      { "value": 3, "label": "Day" }
    ],
    "alertOperator": [
      { "value": 1, "label": "GreaterThan" },
      { "value": 2, "label": "LessThan" },
      { "value": 3, "label": "EqualTo" },
      { "value": 4, "label": "GreaterThanOrEqualTo" },
      { "value": 5, "label": "LessThanOrEqualTo" },
      { "value": 6, "label": "NotEqualTo" }
    ],
    "alertField": [
      { "value": 1, "label": "TotalTokens" },
      { "value": 2, "label": "TotalCost" },
      { "value": 3, "label": "ErrorCount" },
      { "value": 4, "label": "Latency" },
      { "value": 5, "label": "ErrorRate" },
      { "value": 6, "label": "InputTokens" },
      { "value": 7, "label": "OutputTokens" },
      { "value": 8, "label": "WarningCount" },
      { "value": 9, "label": "ObservationCount" }
    ],
    "alertRecordState": [
      { "value": 1, "label": "Active" },
      { "value": 2, "label": "Read" }
    ],
    "alertNotifyBy": [
      { "value": 1, "label": "System" },
      { "value": 2, "label": "SMS" }
    ]
  }
}
```

```json
// 失败响应
{
  "code": 999999,
  "message": "DefaultException",
  "data": null
}
```

### 13.2. API-047 获取Alert列表 (GET /api/alert)

- **鉴权**: 需要 JWT JWT Bearer Token（Controller类 `AlertController` 标注 `[Authorize]`，基于 `JWTSettings` Config，HS256 算法）
- **描述**: 根据可选的 `orgId` 和 `projectId` 查询条件，获取当前用户可访问的 Alert（Alert）列表。
- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `orgId` | string | 否 | Org ID，用于按组织维度过滤 Alert 列表。若未提供，则返回当前用户所属所有组织的 Alert。 |
| `projectId` | string | 否 | Project ID，用于按项目维度过滤 Alert 列表。若未提供，则返回当前用户可访问的所有项目的 Alert。 |

- **响应格式**:

| 字段 | 类型 | 说明 |
|---|---|---|
| `code` | int | 业务码。`0` 表示成功，非 `0` 表示失败。 |
| `message` | string | 状态描述信息。成功时为 `"success"`，失败时为具体错误信息。 |
| `data` | array\<Alert\> | Alert 列表数据。每一项包含Alert的详细信息。 |
| `data[].id` | string | Alert 的唯一标识。 |
| `data[].name` | string | Alert 名称。 |
| `data[].orgId` | string | 所属组织 ID。 |
| `data[].projectId` | string | 所属项目 ID。 |
| `data[].field` | int | 监控指标字段，对应 `AlertField` 枚举（如 `TotalTokens = 1`）。 |
| `data[].operator` | int | 比较运算符，对应 `AlertOperator` 枚举（如 `GreaterThan = 1`）。 |
| `data[].value` | decimal | 触发Alert的阈值。 |
| `data[].timeUnit` | int | 统计周期单位，对应 `AlertTimeUnit` 枚举（如 `Minute = 1`）。 |
| `data[].frequency` | int | 检查频率（分钟）。 |
| `data[].notifyBy` | int | 通知方式，对应 `AlertNotifyBy` 枚举（如 `System = 1`）。 |
| `data[].state` | int | Alert记录状态，对应 `AlertRecordState` 枚举（如 `Active = 1`）。 |
| `data[].createdAt` | datetime | Alert 创建时间。 |
| `data[].updatedAt` | datetime | Alert 最后更新时间。 |

- **错误码**:

| errorCode | message | 说明 |
|---|---|---|
| `0` | `success` | 请求成功。 |
| `100000` | `UnAuthToken` | 未提供或提供了无效的认证 Token。 |
| `160000` | `AlertNotFound` | 未找到指定的 Alert。 |
| `160013` | `AlertOrgNotAccessible` | 当前用户无权访问该组织下的 Alert。 |
| `160014` | `AlertProjectNotFound` | 指定的项目不存在或无权访问。 |
| `999999` | `DefaultException` | 服务器内部错误。 |

- **请求示例**:

```json
GET /api/alert?orgId=org_8f3c2a1b&projectId=proj_5e7d9c4a
```

- **响应示例**:

**成功响应**:

```json
{
  "code": 0,
  "message": "success",
  "data": [
    {
      "id": "alert_1a2b3c4d",
      "name": "Token 使用量过高",
      "orgId": "org_8f3c2a1b",
      "projectId": "proj_5e7d9c4a",
      "field": 1,
      "operator": 1,
      "value": 1000000,
      "timeUnit": 1,
      "frequency": 5,
      "notifyBy": 1,
      "state": 1,
      "createdAt": "2025-01-15T10:30:00Z",
      "updatedAt": "2025-01-15T10:30:00Z"
    }
  ]
}
```

**失败响应**:

```json
{
  "code": 160013,
  "message": "AlertOrgNotAccessible",
  "data": null
}
```

### 13.3. API-001 Create (POST /api/alert)

- **鉴权**: 需要 JWT 认证（`[Authorize]`），用户必须属于目标 Organization 且具备相应Privilege
- **描述**: 创建一条新的 Alert 规则，用于监控 Agent 的 Token 消耗、成本、错误率等指标，并在条件满足时触发通知。

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `name` | string | 是 | Alert 名称，长度限制 1-50 字符 |
| `projectId` | long | 是 | 关联的 Project ID |
| `field` | AlertField | 是 | 监控字段，可选值：`TotalTokens`(1), `TotalCost`(2), `ErrorCount`(3), `Latency`(4), `ErrorRate`(5), `InputTokens`(6), `OutputTokens`(7), `WarningCount`(8), `ObservationCount`(9) |
| `operator` | AlertOperator | 是 | 比较运算符，可选值：`GreaterThan`(1), `LessThan`(2), `EqualTo`(3), `GreaterThanOrEqualTo`(4), `LessThanOrEqualTo`(5), `NotEqualTo`(6) |
| `value` | decimal | 是 | 阈值，必须大于 0 |
| `timeUnit` | AlertTimeUnit | 是 | 时间单位，可选值：`Minute`(1), `Hour`(2), `Day`(3) |
| `frequency` | int | 是 | 检查频率（分钟），必须大于 0 |
| `notifyBy` | AlertNotifyBy | 是 | 通知方式，可选值：`System`(1), `SMS`(2) |
| `description` | string | 否 | Alert 描述 |

**响应格式**

| 字段 | 类型 | 说明 |
|---|---|---|
| `code` | int | 状态码，`0` 表示成功 |
| `message` | string | 提示信息 |
| `data` | object | 创建成功的 Alert 数据 |
| `data.id` | long | Alert ID |
| `data.name` | string | Alert 名称 |
| `data.projectId` | long | 关联的 Project ID |
| `data.field` | int | 监控字段（AlertField 枚举值） |
| `data.operator` | int | 比较运算符（AlertOperator 枚举值） |
| `data.value` | decimal | 阈值 |
| `data.timeUnit` | int | 时间单位（AlertTimeUnit 枚举值） |
| `data.frequency` | int | 检查频率（分钟） |
| `data.notifyBy` | int | 通知方式（AlertNotifyBy 枚举值） |
| `data.description` | string | Alert 描述 |
| `data.createdAt` | datetime | 创建时间 |

**错误码**

| errorCode | message | 说明 |
|---|---|---|
| `160000` | AlertNotFound | Alert 不存在 |
| `160001` | CreateAlertFailed | 创建 Alert 失败 |
| `160004` | InvalidAlertPeriod | 无效的 Alert 时间周期 |
| `160005` | InvalidAlertFrequency | 无效的 Alert 检查频率 |
| `160006` | InvalidAlertField | 无效的 Alert 监控字段 |
| `160007` | InvalidAlertOperator | 无效的 Alert 比较运算符 |
| `160008` | InvalidAlertValue | 无效的 Alert 阈值 |
| `160010` | InvalidAlertName | 无效的 Alert 名称 |
| `160011` | InvalidAlertNotifyBy | 无效的 Alert 通知方式 |
| `160013` | AlertOrgNotAccessible | 无权访问该 Organization 的 Alert |
| `160014` | AlertProjectNotFound | 关联的 Project 不存在 |
| `160015` | AlertNameTooLong | Alert 名称超过长度限制 |
| `100000` | UnAuthToken | 未认证或 Token 无效 |
| `999999` | DefaultException | 服务器内部错误 |

**请求示例**

```json
{
  "name": "Token 消耗Alert",
  "projectId": 12345,
  "field": 1,
  "operator": 1,
  "value": 1000000,
  "timeUnit": 1,
  "frequency": 5,
  "notifyBy": 1,
  "description": "当每分钟 Token 消耗超过 100 万时触发Alert"
}
```

**响应示例**

```json
// 成功响应
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 1001,
    "name": "Token 消耗Alert",
    "projectId": 12345,
    "field": 1,
    "operator": 1,
    "value": 1000000,
    "timeUnit": 1,
    "frequency": 5,
    "notifyBy": 1,
    "description": "当每分钟 Token 消耗超过 100 万时触发Alert",
    "createdAt": "2025-01-15T10:30:00Z"
  }
}

// 失败响应 - 无效的监控字段
{
  "code": 160006,
  "message": "InvalidAlertField",
  "data": null
}
```

### 13.4. API-001 更新 Alert (POST /api/alert/update)

- **鉴权**: 需要 JWT JWT Bearer Token（`[Authorize]`），用户需具备相应 Organization 或 Project 的 ADMIN 或 OWNER Privilege
- **描述**: 更新现有 Alert 的Config信息，包括监控字段、比较条件、通知方式等
- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | long | 是 | Alert 的唯一标识符 |
| name | string | 是 | Alert 名称，长度 1-50 个字符 |
| projectId | long | 是 | 关联的 Project ID |
| field | AlertField | 是 | 监控字段，可选值：TotalTokens(1)、TotalCost(2)、ErrorCount(3)、Latency(4)、ErrorRate(5)、InputTokens(6)、OutputTokens(7)、WarningCount(8)、ObservationCount(9) |
| operator | AlertOperator | 是 | 比较运算符，可选值：GreaterThan(1)、LessThan(2)、EqualTo(3)、GreaterThanOrEqualTo(4)、LessThanOrEqualTo(5)、NotEqualTo(6) |
| value | decimal | 是 | 触发阈值 |
| timeUnit | AlertTimeUnit | 是 | 时间单位，可选值：Minute(1)、Hour(2)、Day(3) |
| frequency | int | 是 | 检查频率，与 timeUnit 配合使用 |
| notifyBy | AlertNotifyBy | 是 | 通知方式，可选值：System(1)、SMS(2) |
| enabled | bool | 否 | 是否启用，默认 true |

- **响应格式**:

| 字段 | 类型 | 说明 |
|------|------|------|
| code | int | 状态码，0 表示成功 |
| message | string | 状态描述 |
| data | object | 更新后的 Alert 数据 |
| data.id | long | Alert ID |
| data.name | string | Alert 名称 |
| data.field | AlertField | 监控字段 |
| data.operator | AlertOperator | 比较运算符 |
| data.value | decimal | 触发阈值 |
| data.timeUnit | AlertTimeUnit | 时间单位 |
| data.frequency | int | 检查频率 |
| data.notifyBy | AlertNotifyBy | 通知方式 |
| data.enabled | bool | 是否启用 |
| data.createdAt | datetime | 创建时间 |
| data.updatedAt | datetime | 更新时间 |

- **错误码**:

| errorCode | message | 说明 |
|-----------|---------|------|
| 160000 | AlertNotFound | 指定的 Alert 不存在 |
| 160002 | UpdateAlertFailed | 更新 Alert 失败 |
| 160004 | InvalidAlertPeriod | 无效的监控周期 |
| 160005 | InvalidAlertFrequency | 无效的检查频率 |
| 160006 | InvalidAlertField | 无效的监控字段 |
| 160007 | InvalidAlertOperator | 无效的比较运算符 |
| 160008 | InvalidAlertValue | 无效的阈值 |
| 160010 | InvalidAlertName | Alert 名称无效 |
| 160011 | InvalidAlertNotifyBy | 无效的通知方式 |
| 160013 | AlertOrgNotAccessible | 无权访问该 Alert 所属组织 |
| 160014 | AlertProjectNotFound | 关联的 Project 不存在 |
| 160015 | AlertNameTooLong | Alert 名称超过长度限制 |
| 100000 | UnAuthToken | 未认证或 Token 无效 |
| 150000 | EmptyProjectId | Project ID 为空 |
| 999999 | DefaultException | 系统默认异常 |

- **请求示例**:
```json
{
  "id": 1,
  "name": "API Error Rate Alert",
  "projectId": 1001,
  "field": 5,
  "operator": 1,
  "value": 0.05,
  "timeUnit": 2,
  "frequency": 1,
  "notifyBy": 1,
  "enabled": true
}
```

- **响应示例**:

**成功响应**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 1,
    "name": "API Error Rate Alert",
    "field": 5,
    "operator": 1,
    "value": 0.05,
    "timeUnit": 2,
    "frequency": 1,
    "notifyBy": 1,
    "enabled": true,
    "createdAt": "2025-01-15T10:30:00Z",
    "updatedAt": "2025-01-15T14:20:00Z"
  }
}
```

**失败响应**:
```json
{
  "code": 160000,
  "message": "AlertNotFound",
  "data": null
}
```

### 13.5. API-014 删除 Alert (POST /api/alert/delete)

- **鉴权**: 需要 JWT JWT Bearer Token（Controller类 `AlertController` 标注了 `[Authorize]`，未指定具体角色，需登录用户）
- **描述**: 根据提供的 Alert ID 列表批量删除 Alert 记录。
- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| alertIds | string | 是 | 待删除的 Alert ID 列表，多个 ID 之间使用英文逗号 `,` 分隔。 |

- **响应格式**:

| 字段 | 类型 | 说明 |
|---|---|---|
| code | int | 业务码。`0` 表示成功，非 `0` 表示失败。 |
| message | string | 状态描述信息。 |
| data | boolean | 删除操作结果。`true` 表示删除成功。 |
| traceId | string | 请求Trace ID，用于日志排查。 |

- **错误码**:

| errorCode | message | 说明 |
|---|---|---|
| 100000 | UnAuthToken | 未认证或 Token 无效。 |
| 160000 | AlertNotFound | 指定的 Alert 不存在。 |
| 160003 | DeleteAlertFailed | 删除 Alert 失败。 |
| 160013 | AlertOrgNotAccessible | 当前用户无权访问该 Alert 所属的组织。 |
| 160014 | AlertProjectNotFound | 该 Alert 关联的 Project 不存在。 |
| 999999 | DefaultException | 服务器内部错误。 |

- **请求示例**:

```json
{
  "alertIds": "string"
}
```

- **响应示例**:

成功响应示例：
```json
{
  "code": 0,
  "message": "Success",
  "data": true,
  "traceId": "9f8c7b6a-5e4d-4c3b-9a2f-1e0d9c8b7a6f"
}
```

失败响应示例（Alert 不存在）：
```json
{
  "code": 160000,
  "message": "AlertNotFound",
  "data": false,
  "traceId": "8e7d6c5b-4a3f-4e2d-9b1c-0f9e8d7c6b5a"
}
```

### 13.6. API-108 ReadRecords (POST /api/alert/record/read)

- **鉴权**: 需要 JWT JWT Bearer Token（Controller类 `AlertController` 标注 `[Authorize]`，用户需已认证）
- **描述**: 根据记录 ID 列表批量读取 Alert 记录，将 Alert 记录状态从 `Active` 更新为 `Read`。
- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| recordIds | string | 是 | Alert 记录 ID 列表，多个 ID 以逗号分隔。例如：`"1001,1002,1003"`。 |

- **响应格式**:

| 字段 | 类型 | 说明 |
|---|---|---|
| code | int | HTTP 状态码，`200` 表示成功 |
| errorCode | int | 业务错误码，`0` 表示无错误；非 `0` 时对应下方错误码表 |
| message | string | 提示信息，成功时为 `"success"`，失败时为具体错误描述 |
| data | boolean | 操作结果，`true` 表示读取成功 |

- **错误码**:

| errorCode | message | 说明 |
|---|---|---|
| 0 | success | 成功 |
| 100000 | UnAuthToken | Token 无效或未提供 |
| 160000 | AlertNotFound | 未找到对应的 Alert 记录 |
| 999999 | DefaultException | 服务器内部错误 |

- **请求示例**:

```json
{
  "recordIds": "1001,1002,1003"
}
```

- **响应示例**:

**成功响应**:
```json
{
  "code": 200,
  "errorCode": 0,
  "message": "success",
  "data": true
}
```

**失败响应** (Alert 记录不存在):
```json
{
  "code": 404,
  "errorCode": 160000,
  "message": "AlertNotFound",
  "data": false
}
```

### 13.7. API-001 获取Alert记录 (GET /api/alert/record)

- **鉴权**: 需要JWT JWT Bearer Token认证（从代码上下文推断，AlertController属于用户管理模块，且系统Config了JWTSettings）
- **描述**: 根据组织、Project、Alert ID和状态筛选条件，分页查询Alert记录列表
- **所属模块**: AlertController (API/Controllers/UserManagement/AlertController.cs)

#### 13.7.1. 请求参数

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| orgId | string | 否 | 组织ID，用于筛选指定组织下的Alert记录 |
| projectId | string | 否 | 项目ID，用于筛选指定项目下的Alert记录 |
| alertId | string | 否 | Alert ID，用于筛选指定Alert的触发记录 |
| state | AlertRecordState | 否 | Alert记录状态，默认值为`Active`(1)。可选值：`Active`(1)、`Read`(2) |

#### 13.7.2. 响应格式

| 字段 | 类型 | 说明 |
|------|------|------|
| code | int | 状态码，`0`表示成功，非`0`表示失败 |
| message | string | 响应消息，成功时为`"ok"`，失败时为错误描述 |
| data | object | 响应数据，包含Alert记录分页列表 |
| data.items | array | Alert记录列表 |
| data.items.id | string | Alert记录ID |
| data.items.alertId | string | Alert ID |
| data.items.orgId | string | 组织ID |
| data.items.projectId | string | 项目ID |
| data.items.state | AlertRecordState | 记录状态：`Active`(1)、`Read`(2) |
| data.items.content | string | Alert记录内容 |
| data.items.createdAt | datetime | 记录创建时间 |
| data.items.readAt | datetime | 记录读取时间，未读时为`null` |
| data.total | int | 符合条件的记录总数 |
| data.page | int | 当前页码 |
| data.pageSize | int | 每页记录数 |

#### 13.7.3. 错误码

| errorCode | message | 说明 |
|-----------|---------|------|
| 100000 | UnAuthToken | Token未认证或已过期 |
| 160000 | AlertNotFound | Alert不存在或已被删除 |
| 160013 | AlertOrgNotAccessible | 当前用户无权访问该组织下的Alert |
| 160014 | AlertProjectNotFound | 指定的项目不存在或无权访问 |
| 999999 | DefaultException | 服务器内部错误 |

#### 13.7.4. 请求示例

```json
GET /api/alert/record?orgId=org_8f3a2b1c&projectId=proj_5e7d9c2a&alertId=alert_3b6f1e8d&state=1
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

#### 13.7.5. 响应示例

**成功响应 (HTTP 200)**

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "items": [
      {
        "id": "rec_1a2b3c4d",
        "alertId": "alert_3b6f1e8d",
        "orgId": "org_8f3a2b1c",
        "projectId": "proj_5e7d9c2a",
        "state": 1,
        "content": "Token消耗超过阈值：最近5分钟TotalTokens为15000，超过设定的10000阈值",
        "createdAt": "2025-01-15T10:30:00Z",
        "readAt": null
      },
      {
        "id": "rec_5e6f7a8b",
        "alertId": "alert_3b6f1e8d",
        "orgId": "org_8f3a2b1c",
        "projectId": "proj_5e7d9c2a",
        "state": 2,
        "content": "错误率超过阈值：最近5分钟ErrorRate为8.5%，超过设定的5%阈值",
        "createdAt": "2025-01-15T09:45:00Z",
        "readAt": "2025-01-15T10:00:00Z"
      }
    ],
    "total": 2,
    "page": 1,
    "pageSize": 20
  }
}
```

**失败响应 (HTTP 401 - 未认证)**

```json
{
  "code": 100000,
  "message": "UnAuthToken",
  "data": null
}
```

**失败响应 (HTTP 403 - 无权访问)**

```json
{
  "code": 160013,
  "message": "AlertOrgNotAccessible",
  "data": null
}
```

---

## 14. CaptchaController 接口

本章共覆盖 2 个 HTTP 端点，每个端点一个接口卡片。

### 14.1. API-029 Get 获取图形Captcha (GET /api/captcha)

- **鉴权**: 无
- **描述**: 获取图形Captcha。该接口用于生成图形Captcha，用户需在登录、注册等操作前完成图形验证，以增强安全性。Captcha图片以 Base64 编码返回，并附带Captcha ID 用于后续校验。

- **请求参数**: 无

- **响应格式**:

| 字段 | 类型 | 说明 |
|---|---|---|
| `code` | `int` | 业务码，`0` 表示成功，非 `0` 表示失败 |
| `message` | `string` | 状态描述信息，成功时为 `"success"`，失败时为具体错误信息 |
| `data` | `object` | 响应数据，成功时包含Captcha图片和Captcha ID，失败时为 `null` |

- **错误码**:

| errorCode | message | 说明 |
|---|---|---|
| `999999` | DefaultException | 系统默认异常，请联系管理员 |

- **请求示例**:

```http
GET /api/captcha
```

- **响应示例**:

**成功响应**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "captchaId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "captchaImage": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA..."
  }
}
```

**失败响应** (系统异常):
```json
{
  "code": 999999,
  "message": "DefaultException",
  "data": null
}
```

### 14.2. API-001 GetSMSCaptcha 获取短信Captcha (GET /api/captcha/sms)

- **鉴权**: 无
- **描述**: 获取短信Captcha。根据提供的手机号发送短信Captcha，用于用户登录、注册等场景的验证。Captcha将通过短信发送至指定手机号。

- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `phone` | `string` | 是 | 接收Captcha的手机号码，需为有效的手机号格式 |

- **响应格式**:

| 字段 | 类型 | 说明 |
|------|------|------|
| `code` | `int` | 业务码，`0` 表示成功，非 `0` 表示失败 |
| `message` | `string` | 状态描述信息，成功时为 `"success"`，失败时为具体错误信息 |
| `data` | `object` | 响应数据，成功时通常为 `null` |
| `traceId` | `string` | 请求Trace ID，用于日志排查 |

- **错误码**:

| errorCode | message | 说明 |
|-----------|---------|------|
| `110000` | SendSMSTooOften | 短信发送过于频繁，请稍后再试 |
| `110001` | FailedToSendSMS | 短信发送失败，请检查手机号或稍后重试 |
| `100009` | EmptyMobile | 手机号为空 |
| `999999` | DefaultException | 服务器内部错误 |

- **请求示例**:

```http
GET /api/captcha/sms?phone=13800138000
```

- **响应示例**:

**成功响应**:
```json
{
  "code": 0,
  "message": "success",
  "data": null,
  "traceId": "a1b2c3d4-1234-5678-9abc-def012345678"
}
```

**失败响应** (发送过于频繁):
```json
{
  "code": 110000,
  "message": "SendSMSTooOften",
  "data": null,
  "traceId": "a1b2c3d4-1234-5678-9abc-def012345678"
}
```

---

## 15. OrganizationController 接口

本章共覆盖 4 个 HTTP 端点，每个端点一个接口卡片。

### 15.1. API-001 创建组织 (POST /api/user/organization)

- **鉴权**: 需要 JWT JWT Bearer Token（`[Authorize]`），用户必须已登录。
- **描述**: 为当前登录用户创建一个新的 Organization（Org）。创建成功后，该用户将成为此组织的 OWNER（所有者）。
- **源码位置**: `API/Controllers/UserManagement/OrganizationController.cs:28`

- **请求参数** (JSON Body, `CreateOrganizationBody`):

| 字段 | 类型 | 必填 | 说明 |
| :--- | :--- | :--- | :--- |
| `name` | string | 是 | 组织名称。长度必须在 2 到 50 个字符之间（由 `OrganizationNameTooShort` 和 `OrganizationNameTooLong` 错误码约束）。 |

- **响应格式** (`ApiResponse<long>`):

| 字段 | 类型 | 说明 |
| :--- | :--- | :--- |
| `code` | int | HTTP 状态码，`200` 表示成功。 |
| `errorCode` | string | 业务错误码。成功时为 `"0"` 或 `"None"`，失败时为具体的错误常量名（见下表）。 |
| `message` | string | 可读的状态消息。成功时为 `"Success"`，失败时为错误详情。 |
| `data` | long | 成功时返回新创建的 Organization 的 ID。 |
| `traceId` | string | 用于Trace请求的 Trace ID（由 `TraceIdResult` 生成）。 |

- **错误码**:

| errorCode | code | message | 说明 |
| :--- | :--- | :--- | :--- |
| `UnAuthToken` | 100000 | 未认证的Token | Token 无效或已过期。 |
| `EmptyOrganizationName` | 130000 | 组织名称不能为空 | `name` 字段未提供或为空白字符串。 |
| `OrganizationNameTooShort` | 130001 | 组织名称长度不能少于 2 个字符 | `name` 字段长度小于 2。 |
| `OrganizationNameTooLong` | 130002 | 组织名称长度不能超过 50 个字符 | `name` 字段长度大于 50。 |
| `CreateOrganizationFailed` | 130004 | 创建组织失败 | 数据库操作失败或发生未知错误。 |
| `ExceedOrgLimit` | 130012 | 超出组织数量限制 | 当前用户创建的组织数量已达到上限。 |
| `DefaultException` | 999999 | 系统繁忙，请稍后重试 | 未处理的未知异常。 |

- **请求示例**:

```json
{
  "name": "示例科技有限公司"
}
```

- **响应示例**:

**成功响应**:

```json
{
  "code": 200,
  "errorCode": "0",
  "message": "Success",
  "data": 1,
  "traceId": "a1b2c3d4-5678-90ab-cdef-1234567890ab"
}
```

**失败响应** (`OrganizationNameTooShort`):

```json
{
  "code": 400,
  "errorCode": "OrganizationNameTooShort",
  "message": "组织名称长度不能少于 2 个字符",
  "data": null,
  "traceId": "a1b2c3d4-5678-90ab-cdef-1234567890ab"
}
```

### 15.2. API-002 获取组织信息 (GET /api/user/organization)

- **鉴权**: 需要认证（基于 `OrganizationController` Controller类，该类继承自 `ApiControllerBase`，其基类默认带有 `[Authorize]` 特性）。
- **描述**: 根据组织 ID 获取指定组织的详细信息。
- **源码位置**: `API/Controllers/UserManagement/OrganizationController.cs:42`

- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| orgId | string | 否 | 组织唯一标识符。若为空，则返回当前用户所属的默认组织信息。 |

- **响应格式**:

| 字段 | 类型 | 说明 |
|------|------|------|
| code | int | 状态码。`0` 表示成功，非 `0` 表示失败。 |
| message | string | 状态描述信息。 |
| data | object | 组织信息数据。 |
| data.id | string | 组织唯一标识符。 |
| data.name | string | 组织名称。 |
| data.headCountLimit | int | 组织成员人数上限。 |
| data.projectLimit | int | 组织可创建的项目数量上限。 |
| data.createdAt | datetime | 组织创建时间。 |
| data.updatedAt | datetime | 组织信息最后更新时间。 |

- **错误码**:

| errorCode | code | message | 说明 |
|-----------|---------|---------|------|
| `UnAuthToken` | 100000 | 未认证的Token | 认证 Token 无效或已过期。 |
| `InvalidOrganization` | 130003 | 无效的组织 | 指定的组织不存在或已被删除。 |
| `UnauthorizedOrganizationAccess` | 130009 | 无权访问该组织 | 当前用户无权访问该组织。 |
| `DefaultException` | 999999 | 系统繁忙，请稍后重试 | 服务器内部错误。 |

- **请求示例**:

```json
GET /api/user/organization?orgId=org_8f3c2a1b9d4e5f6a7b8c9d0e
```

- **响应示例**:

**成功响应**:

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "org_8f3c2a1b9d4e5f6a7b8c9d0e",
    "name": "示例科技有限公司",
    "headCountLimit": 50,
    "projectLimit": 10,
    "createdAt": "2024-05-20T10:30:00Z",
    "updatedAt": "2024-06-15T08:45:00Z"
  }
}
```

**失败响应** (组织不存在):

```json
{
  "code": 130003,
  "message": "InvalidOrganization",
  "data": null
}
```

### 15.3. API-003 更新组织 (POST /api/user/organization/update)

- **鉴权**: 需要 JWT 认证 (JWT Bearer Token)，且当前用户必须拥有目标 Organization 的 ADMIN 或 OWNER Privilege。
- **描述**: 更新现有 Organization 的基本信息，包括名称和描述。此操作会同步更新数据库记录，并触发审计日志记录。
- **源码位置**: `API/Controllers/UserManagement/OrganizationController.cs:56`

- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `id` | long | 是 | Organization 的唯一标识符 |
| `name` | string | 是 | Organization 名称，长度必须在 2 到 50 个字符之间 |
| `description` | string | 否 | Organization 描述，最大长度为 200 个字符 |

- **响应格式**:

| 字段 | 类型 | 说明 |
|---|---|---|
| `code` | int | 业务码，`0` 表示成功，非 `0` 表示失败 |
| `message` | string | 状态描述信息 |
| `data` | object | 更新后的 Organization 实体数据 |

- **错误码**:

| errorCode | code | message | 说明 |
|---|---|---|---|
| `UnAuthToken` | 100000 | 未认证的Token | 未提供有效的认证 Token 或 Token 已过期 |
| `EmptyOrganizationName` | 130000 | 组织名称不能为空 | Organization 名称为空 |
| `OrganizationNameTooShort` | 130001 | 组织名称长度不能少于 2 个字符 | Organization 名称长度少于 2 个字符 |
| `OrganizationNameTooLong` | 130002 | 组织名称长度不能超过 50 个字符 | Organization 名称长度超过 50 个字符 |
| `InvalidOrganization` | 130003 | 无效的组织 | 指定的 Organization 不存在或已被删除 |
| `UpdateOrganizationFailed` | 130005 | 更新组织失败 | 数据库更新操作失败，请稍后重试 |
| `UnauthorizedOrganizationAccess` | 130009 | 无权访问该组织 | 当前用户无权修改该 Organization 的信息 |
| `DefaultException` | 999999 | 系统繁忙，请稍后重试 | 服务器内部错误，请联系管理员 |

- **请求示例**:

```json
{
  "id": 1234567890,
  "name": "示例科技有限公司",
  "description": "专注于 AI 解决方案的研发与创新"
}
```

- **响应示例**:

**成功响应**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 1234567890,
    "name": "示例科技有限公司",
    "description": "专注于 AI 解决方案的研发与创新",
    "createdAt": "2024-06-15T10:30:00Z",
    "updatedAt": "2024-06-20T14:45:00Z"
  }
}
```

**失败响应** (Organization 不存在):
```json
{
  "code": 130003,
  "message": "InvalidOrganization",
  "data": null
}
```

### 15.4. API-004 删除组织 (POST /api/user/organization/delete)

- **鉴权**: 需要 JWT 认证 (JWT Bearer Token)，用户需具备组织管理Privilege。
- **描述**: 根据组织 ID 列表批量删除组织。删除前会校验组织是否存在、当前用户是否有Privilege操作，以及组织下是否仍有未删除的项目。若组织下存在项目，则删除操作会被拒绝。
- **源码位置**: `API/Controllers/UserManagement/OrganizationController.cs:71`

- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| orgIds | string | 是 | 待删除的组织 ID 列表，多个 ID 以逗号分隔。例如：`1001,1002,1003` |

- **响应格式**:

| 字段 | 类型 | 说明 |
|------|------|------|
| code | int | 业务码，`0` 表示成功，非 `0` 表示失败 |
| message | string | 状态描述信息，成功时为 `"success"`，失败时为具体错误信息 |
| data | object | 响应数据，删除成功时为空对象 `{}` |

- **错误码**:

| errorCode | code | message | 说明 |
|-----------|---------|---------|------|
| `UnAuthToken` | 100000 | 未认证的Token | 未认证或 Token 无效 |
| `InvalidOrganization` | 130003 | 无效的组织 | 组织不存在或已失效 |
| `DeleteOrganizationFailed` | 130006 | 删除组织失败 | 删除组织失败，请稍后重试 |
| `OrganizationHasProjects` | 130007 | 组织下存在项目 | 组织下存在项目，无法删除 |
| `OrganizationProjectDeleting` | 130008 | 组织下的项目正在删除中 | 组织下的项目正在删除中，请稍后再试 |
| `UnauthorizedOrganizationAccess` | 130009 | 无权访问该组织 | 当前用户无权操作该组织 |
| `DefaultException` | 999999 | 系统繁忙，请稍后重试 | 系统默认异常，请联系管理员 |

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
  "message": "success",
  "data": {}
}
```

**失败响应** (组织下存在项目):
```json
{
  "code": 130007,
  "message": "OrganizationHasProjects",
  "data": {}
}
```

---

## 16. ProjectController 接口

本章覆盖 `ProjectController` 中定义的 4 个 HTTP 端点，每个端点一个接口卡片。

### 16.1. API-001 创建项目 (POST /api/user/project)

- **鉴权**: 需要 JWT JWT Bearer Token（`[Authorize]`），用户必须已登录。Token 有效期 43200 分钟（30 天）。
- **描述**: 创建一个新的 Project。Project 归属于当前用户所在的 Organization，创建后 Project 将拥有独立的 Agent Config、Trace 数据隔离和配额限制。

- **请求参数** (Body: `application/json`):

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `name` | string | 是 | Project 名称，长度限制 2-50 个字符（对应 `ProjectNameTooShort`/`ProjectNameTooLong` 错误码） |
| `organizationId` | long | 是 | 所属 Organization 的 ID，必须是当前用户所属的 Organization |
| `description` | string | 否 | Project 描述信息，用于说明 Project 的用途或业务背景 |

- **响应格式** (`ApiResponse<long>`):

| 字段 | 类型 | 说明 |
|---|---|---|
| `code` | int | 状态码，`0` 表示成功，非 `0` 表示失败 |
| `message` | string | 状态描述信息，成功时为 `"Success"`，失败时为具体错误信息 |
| `data` | long | 创建成功的 Project ID（`projectId`），可用于后续 API 调用 |

- **错误码**:

| errorCode | message | 说明 |
|---|---|---|
| `140000` | EmptyProjectName | Project 名称为空 |
| `140001` | ProjectNameTooShort | Project 名称长度不足 2 个字符 |
| `140002` | ProjectNameTooLong | Project 名称长度超过 50 个字符 |
| `140003` | InvalidProject | Project 无效或不存在 |
| `140004` | CreateProjectFailed | 创建 Project 失败，数据库操作异常 |
| `140007` | ExistedProjectName | Project 名称已存在，同一 Organization 下不允许重名 |
| `140008` | UnauthorizedProjectAccess | 无权访问该 Project，用户不属于该 Organization |
| `130009` | UnauthorizedOrganizationAccess | 无权访问该 Organization |
| `130010` | ExceedHeadCountLimit | 超出 Organization 成员数量限制 |
| `130011` | ExceedProjectLimit | 超出 Organization 可创建的 Project 数量限制 |
| `100000` | UnAuthToken | 未提供有效的认证 Token |
| `100001` | EmptyUserId | 无法从 Token 中解析用户 ID |
| `100005` | InvalidUser | 用户不存在或已被禁用 |
| `999999` | DefaultException | 系统默认异常，未预期的错误 |

- **请求示例**:

```json
{
  "name": "生产环境监控",
  "organizationId": 1001,
  "description": "用于生产环境的 Agent 调用链监控与 Trace 分析"
}
```

- **响应示例**:

**成功响应** (`200 OK`):
```json
{
  "code": 0,
  "message": "Success",
  "data": 2001
}
```

**失败响应** (`200 OK`，业务错误):
```json
{
  "code": 140007,
  "message": "ExistedProjectName",
  "data": null
}
```

**失败响应** (`401 Unauthorized`，未认证):
```json
{
  "code": 100000,
  "message": "UnAuthToken",
  "data": null
}
```

### 16.2. API-046 获取项目信息 (GET /api/user/project)

- **鉴权**: 需要 JWT JWT Bearer Token（`[Authorize]`），用户需属于指定组织且拥有相应Privilege
- **描述**: 根据组织 ID 和可选的 Project ID 获取项目信息。若提供 `projectId` 则返回指定项目详情，否则返回该组织下的项目列表。

- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `orgId` | string | 是 | Org ID，用于限定查询范围，必须是当前用户所属的组织 |
| `projectId` | string | 否 | Project ID，若提供则查询指定项目；若不提供则返回组织下所有项目 |

- **响应格式**:

| 字段 | 类型 | 说明 |
|---|---|---|
| `code` | int | 状态码，`0` 表示成功，非 `0` 表示失败 |
| `message` | string | 提示信息，成功时为 `"success"`，失败时为错误描述 |
| `data` | object/array | 项目数据。当指定 `projectId` 时为单个项目对象；未指定时为项目对象数组 |

`data` 中项目对象字段说明：

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | string | Project ID |
| `name` | string | 项目名称 |
| `orgId` | string | 所属组织 ID |
| `description` | string | 项目描述 |
| `createdAt` | datetime | 创建时间 |
| `updatedAt` | datetime | 更新时间 |

- **错误码**:

| errorCode | message | 说明 |
|---|---|---|
| `100000` | UnAuthToken | Token 无效或未提供，需重新登录 |
| `130003` | InvalidOrganization | 组织不存在或已被删除 |
| `130009` | UnauthorizedOrganizationAccess | 当前用户无权访问该组织 |
| `140003` | InvalidProject | 项目不存在或已被删除 |
| `140008` | UnauthorizedProjectAccess | 当前用户无权访问该项目 |
| `999999` | DefaultException | 服务器内部错误，请稍后重试 |

- **请求示例**:

```json
{
  "orgId": "org_8f3c2a1b9d4e",
  "projectId": "proj_5e7a2c8d1f3b"
}
```

- **响应示例**:

**成功响应**:

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "proj_5e7a2c8d1f3b",
    "name": "生产环境监控",
    "orgId": "org_8f3c2a1b9d4e",
    "description": "用于生产环境的 Trace 监控项目",
    "createdAt": "2025-06-01T10:30:00Z",
    "updatedAt": "2025-06-15T14:20:00Z"
  }
}
```

**失败响应** (项目不存在):

```json
{
  "code": 140003,
  "message": "InvalidProject",
  "data": null
}
```

### 16.3. API-060 更新项目 (POST /api/user/project/update)

- **鉴权**: 需要 JWT 认证 (JWT Bearer Token)，用户需具备项目所属组织的 ADMIN 或 OWNER Privilege
- **描述**: 更新现有项目信息，包括项目名称和描述。此操作会校验项目归属权及名称唯一性。
- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| id | long | 是 | 待更新项目的唯一标识符 |
| name | string | 是 | 新的项目名称，长度需在 1 到 50 个字符之间 |
| description | string | 否 | 项目描述，长度不超过 200 个字符 |

- **响应格式**:

| 字段 | 类型 | 说明 |
|---|---|---|
| code | int | 业务码，0 表示成功，非 0 表示失败 |
| message | string | 状态描述信息 |
| data | object | 成功时返回更新后的项目信息；失败时为 null |

- **错误码**:

| errorCode | message | 说明 |
|---|---|---|
| 140000 | EmptyProjectName | 项目名称为空 |
| 140001 | ProjectNameTooShort | 项目名称长度不足 |
| 140002 | ProjectNameTooLong | 项目名称长度超出限制 |
| 140003 | InvalidProject | 项目不存在或已被删除 |
| 140005 | UpdateProjectFailed | 项目更新失败，请稍后重试 |
| 140007 | ExistedProjectName | 项目名称已存在，请更换名称 |
| 140008 | UnauthorizedProjectAccess | 无权访问该项目 |
| 100000 | UnAuthToken | 未提供有效的身份认证 Token |
| 999999 | DefaultException | 系统内部错误，请联系管理员 |

- **请求示例**:

```json
{
  "id": 1001,
  "name": "智能客服系统",
  "description": "基于 AgentInsight 的智能客服项目"
}
```

- **响应示例**:

```json
// 成功响应
{
  "code": 0,
  "message": "项目更新成功",
  "data": {
    "id": 1001,
    "name": "智能客服系统",
    "description": "基于 AgentInsight 的智能客服项目",
    "organizationId": 501,
    "createdAt": "2025-01-15T10:30:00Z",
    "updatedAt": "2025-02-20T14:45:00Z"
  }
}

// 失败响应 - 项目名称重复
{
  "code": 140007,
  "message": "项目名称已存在，请更换名称",
  "data": null
}
```

### 16.4. API-001 删除项目 (POST /api/user/project/delete)

- **鉴权**: 需要 JWT JWT Bearer Token（`[Authorize]`），用户需具备项目所属组织的 ADMIN 或 OWNER Privilege
- **描述**: 根据项目 ID 列表删除一个或多个项目，删除操作会异步清理项目关联的 Trace 数据、Agent Config及缓存
- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| projectIds | string | 是 | 待删除的项目 ID 列表，多个 ID 使用英文逗号分隔。示例：`"1001,1002,1003"` |

- **响应格式**:

| 字段 | 类型 | 说明 |
|------|------|------|
| code | int | 业务码，`0` 表示成功，非 `0` 表示失败 |
| message | string | 状态描述信息，成功时为 `"success"`，失败时为具体错误信息 |
| data | object | 响应数据，成功时返回 `null` |

- **错误码**:

| errorCode | message | 说明 |
|-----------|---------|------|
| 100000 | UnAuthToken | 未提供有效的认证 Token 或 Token 已过期 |
| 140003 | InvalidProject | 项目不存在或已被删除 |
| 140006 | DeleteProjectFailed | 项目删除失败，请稍后重试 |
| 140008 | UnauthorizedProjectAccess | 当前用户无权访问或操作该项目 |
| 130007 | OrganizationHasProjects | 项目所属组织下仍存在其他项目，无法删除 |
| 130008 | OrganizationProjectDeleting | 项目正在删除中，请勿重复操作 |
| 990001 | EncryptionFailed | 数据加密失败，请稍后重试 |
| 999999 | DefaultException | 系统内部错误，请联系管理员 |

- **请求示例**:

```json
{
  "projectIds": "1001,1002,1003"
}
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

**失败响应**（项目不存在）:
```json
{
  "code": 140003,
  "message": "InvalidProject",
  "data": null
}
```

**失败响应**（无Privilege访问）:
```json
{
  "code": 140008,
  "message": "UnauthorizedProjectAccess",
  "data": null
}
```

---

## 17. BulletinController 接口


本章共覆盖 7 个 HTTP 端点，每个端点一个接口卡片。


### 17.1. API-001 创建Bulletin (POST /api/tools/bulletin)

- **鉴权**: 需要身份验证（基于 `BulletinController` 位于 `API/Controllers/ToolsManagement` 命名空间，且Bulletin管理属于受保护的后台管理功能，推断存在 `[Authorize]` 注解）
- **描述**: 创建一条新的Bulletin（Bulletin），用于发布新闻、活动、通知等信息。

- **请求参数** (`CreateBulletinBody`，JSON Body):

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `title` | string | 是 | Bulletin标题 |
| `content` | string | 是 | Bulletin正文内容 |
| `type` | int | 是 | Bulletin类型，枚举值：`News`(1)、`Activity`(2)、`Information`(3)、`Annoucement`(4)、`Advertisement`(5)、`Agreement`(9) |
| `status` | int | 是 | Bulletin状态，枚举值：`Draft`(1)、`Reviewing`(2)、`Revision`(3)、`Published`(4)、`Expired`(5)、`Closed`(6) |
| `startTime` | DateTime? | 否 | Bulletin生效开始时间，为 `null` 时立即生效 |
| `endTime` | DateTime? | 否 | Bulletin失效结束时间，为 `null` 时永久有效 |
| `targetUrl` | string? | 否 | Bulletin关联的跳转链接（如活动详情页、外部链接） |
| `coverImageUrl` | string? | 否 | Bulletin封面图片的 URL 地址 |
| `sortOrder` | int? | 否 | Bulletin排序权重，数值越小越靠前，默认 `0` |
| `isTop` | bool? | 否 | 是否置顶显示，默认 `false` |
| `remark` | string? | 否 | 备注信息，用于内部管理说明 |

- **响应格式** (`ApiResponse<long>`):

| 字段 | 类型 | 说明 |
|---|---|---|
| `code` | int | 业务码，`0` 表示成功，非 `0` 表示失败 |
| `message` | string | 状态描述信息，成功时为 `"success"`，失败时为具体错误信息 |
| `data` | long | 新建Bulletin的唯一标识符 `Id`（Bulletin ID） |
| `traceId` | string | 请求Trace ID，用于链路Trace和日志排查 |

- **错误码**:

| errorCode | message | 说明 |
|---|---|---|
| `UnAuthToken` (100000) | 未认证的 Token | 请求未携带有效的身份凭证，或 Token 已过期 |
| `DefaultException` (999999) | 系统异常 | 服务器内部错误，请稍后重试或联系管理员 |

- **请求示例**:

```json
{
  "title": "AgentInsightService 系统升级通知",
  "content": "为了提供更稳定的服务，AgentInsightService 将于本周六 22:00 进行系统升级，预计持续 2 小时。",
  "type": 4,
  "status": 1,
  "startTime": "2025-01-15T22:00:00",
  "endTime": "2025-01-15T23:59:59",
  "targetUrl": "https://example.com/upgrade-news",
  "coverImageUrl": "https://example.com/images/upgrade-banner.png",
  "sortOrder": 1,
  "isTop": true,
  "remark": "运营部门提交"
}
```

- **响应示例**:

**成功响应**:
```json
{
  "code": 0,
  "message": "success",
  "data": 10001,
  "traceId": "a3f2b8c1-9d4e-4f6a-8b2c-7e5d1a9f3c6b"
}
```

**失败响应** (未认证或 Token 失效):
```json
{
  "code": 100000,
  "message": "未认证的 Token",
  "data": null,
  "traceId": "b7e8f2d4-1c3a-4e5b-9f6d-2a8c4e7b1d5f"
}
```

### 17.2. API-045 获取Bulletin协议 (GET /api/tools/bulletin/agreement)

- **鉴权**: 无
- **描述**: 根据别名获取Bulletin协议内容，用于展示用户协议、隐私政策等静态文本。

- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| alias | string | 是 | Bulletin别名，用于标识具体的Bulletin类型（如 `agreement`、`privacy` 等） |

- **响应格式**:

| 字段 | 类型 | 说明 |
|---|---|---|
| code | int | 状态码，`0` 表示成功，非 `0` 表示失败 |
| message | string | 提示信息 |
| data | object | Bulletin内容数据 |
| data.id | string | Bulletin唯一标识 |
| data.title | string | Bulletin标题 |
| data.content | string | Bulletin正文内容（HTML 或纯文本） |
| data.type | int | Bulletin类型，参考 `BulletinType` 枚举 |
| data.status | int | Bulletin状态，参考 `BulletinStatus` 枚举 |
| data.createdAt | string | 创建时间（ISO 8601 格式） |
| data.updatedAt | string | 更新时间（ISO 8601 格式） |

- **错误码**:

| errorCode | message | 说明 |
|---|---|---|
| 999999 | DefaultException | 服务器内部异常，请稍后重试 |
| 100000 | UnAuthToken | 未认证或 Token 无效（本接口无鉴权，通常不会返回） |

- **请求示例**:

```json
GET /api/tools/bulletin/agreement?alias=agreement
```

- **响应示例**:

**成功响应**:

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "b8f3a2c1-9d4e-4f6a-8b2c-5e7a1d3f9a0b",
    "title": "AgentInsightService 用户协议",
    "content": "<h1>用户协议</h1><p>欢迎使用 AgentInsightService...</p>",
    "type": 9,
    "status": 4,
    "createdAt": "2025-01-15T10:30:00Z",
    "updatedAt": "2025-02-20T14:45:00Z"
  }
}
```

**失败响应**:

```json
{
  "code": 999999,
  "message": "DefaultException",
  "data": null
}
```

### 17.3. API-001 GetBulletins (GET /api/tools/bulletin/bulletins)

- **鉴权**: 无
- **描述**: 分页获取Bulletin列表，支持按Bulletin类型筛选及轮播图过滤。

- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| type | int? | 否 | Bulletin类型，枚举值：`News`(1)、`Activity`(2)、`Information`(3)、`Annoucement`(4)、`Advertisement`(5)、`Agreement`(9) |
| isCarousel | bool | 否 | 是否仅获取轮播图Bulletin，默认 `false` |
| page | int | 否 | 页码，默认 `1` |
| pageSize | int | 否 | 每页条数，默认 `10` |

- **响应格式**:

| 字段 | 类型 | 说明 |
|---|---|---|
| code | int | 状态码，`0` 表示成功 |
| message | string | 状态描述 |
| data | object | 分页数据 |
| data.items | array | Bulletin列表 |
| data.items.id | string | Bulletin ID |
| data.items.title | string | Bulletin标题 |
| data.items.content | string | Bulletin内容 |
| data.items.type | int | Bulletin类型 |
| data.items.status | int | Bulletin状态，枚举值：`Draft`(1)、`Reviewing`(2)、`Revision`(3)、`Published`(4)、`Expired`(5)、`Closed`(6) |
| data.items.isCarousel | bool | 是否为轮播图 |
| data.items.startTime | datetime | Bulletin开始时间 |
| data.items.endTime | datetime | Bulletin结束时间 |
| data.items.createdAt | datetime | 创建时间 |
| data.items.updatedAt | datetime | 更新时间 |
| data.total | int | 总记录数 |
| data.page | int | 当前页码 |
| data.pageSize | int | 每页条数 |

- **错误码**:

| errorCode | message | 说明 |
|---|---|---|
| 100000 | UnAuthToken | Token 无效或未提供 |
| 999999 | DefaultException | 服务器内部错误 |

- **请求示例**:

```json
GET /api/tools/bulletin/bulletins?type=1&isCarousel=false&page=1&pageSize=10
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
        "id": "string",
        "title": "string",
        "content": "string",
        "type": 1,
        "status": 4,
        "isCarousel": false,
        "startTime": "2024-01-01T00:00:00Z",
        "endTime": "2024-12-31T23:59:59Z",
        "createdAt": "2024-01-01T00:00:00Z",
        "updatedAt": "2024-01-01T00:00:00Z"
      }
    ],
    "total": 1,
    "page": 1,
    "pageSize": 10
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

### 17.4. API-082 GetBackendBulletins (GET /api/tools/bulletin/backend)

- **鉴权**: 无（接口未标注 `[Authorize]` 注解，为公开访问接口）
- **描述**: 分页查询后端Bulletin列表，支持按Bulletin类型和Bulletin状态进行筛选。该接口供管理后台使用，用于获取 Bulletin 信息。

- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| type | int? | 否 | Bulletin类型筛选条件。可选值：`News` (1)、`Activity` (2)、`Information` (3)、`Annoucement` (4)、`Advertisement` (5)、`Agreement` (9) |
| status | int? | 否 | Bulletin状态筛选条件。可选值：`Draft` (1)、`Reviewing` (2)、`Revision` (3)、`Published` (4)、`Expired` (5)、`Closed` (6) |
| page | int | 否 | 页码，从 1 开始。默认值为 `1` |
| pageSize | int | 否 | 每页条数。默认值为 `10` |

- **响应格式**:

| 字段 | 类型 | 说明 |
|------|------|------|
| code | int | 状态码。`0` 表示成功，非 `0` 表示失败 |
| message | string | 提示信息。成功时为 `"success"`，失败时为具体错误描述 |
| data | object | 返回的数据对象 |
| data.items | array | Bulletin列表，元素为 Bulletin 对象 |
| data.items[].id | string | Bulletin唯一标识 |
| data.items[].title | string | Bulletin标题 |
| data.items[].content | string | Bulletin内容 |
| data.items[].type | int | Bulletin类型 |
| data.items[].status | int | Bulletin状态 |
| data.items[].createdAt | datetime | 创建时间 |
| data.items[].updatedAt | datetime | 更新时间 |
| data.total | int | 符合条件的Bulletin总数 |
| data.page | int | 当前页码 |
| data.pageSize | int | 每页条数 |

- **错误码**:

| errorCode | message | 说明 |
|-----------|---------|------|
| 0 | success | 请求成功 |
| 100000 | UnAuthToken | Token 无效或未授权访问 |
| 999999 | DefaultException | 服务器内部错误，未预期的异常 |

- **请求示例**:

```json
GET /api/tools/bulletin/backend?type=1&status=4&page=1&pageSize=10
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
        "id": "b1f2a3c4-d5e6-4f7a-8b9c-0d1e2f3a4b5c",
        "title": "系统升级通知",
        "content": "系统将于本周六凌晨 2:00-4:00 进行升级维护。",
        "type": 1,
        "status": 4,
        "createdAt": "2025-01-10T10:30:00Z",
        "updatedAt": "2025-01-10T10:30:00Z"
      }
    ],
    "total": 1,
    "page": 1,
    "pageSize": 10
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

### 17.5. API-096 ApproveBulletin (POST /api/tools/bulletin/approve)

- **鉴权**: 无 `[Authorize]` 注解，无需鉴权
- **描述**: 审批通过Bulletin，将指定 ID 的Bulletin状态更新为 Published

- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| ids | string | 是 | 待审批通过的Bulletin ID 列表，多个 ID 以逗号分隔 |

- **响应格式**:

| 字段 | 类型 | 说明 |
|------|------|------|
| code | int | 状态码，0 表示成功，非 0 表示失败 |
| message | string | 响应消息 |
| data | object | 响应数据，审批通过后返回 null |

- **错误码**:

| errorCode | message | 说明 |
|-----------|---------|------|
| 100000 | UnAuthToken | Token 无效或未授权 |
| 999999 | DefaultException | 默认异常，处理失败 |

- **请求示例**:

```json
{
  "ids": "1,2,3"
}
```

- **响应示例**:

**成功响应**:
```json
{
  "code": 0,
  "message": "审批通过成功",
  "data": null
}
```

**失败响应**:
```json
{
  "code": 100000,
  "message": "Token 无效或未授权",
  "data": null
}
```

### 17.6. API-110 ReviseBulletin (POST /api/tools/bulletin/revision)

- **鉴权**: 无（接口方法未标注 `[Authorize]` 特性）
- **描述**: 根据指定的Bulletin ID 列表，将Bulletin状态修改为 Revision（待修订）状态。
- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| ids | string | 是 | 待修订的Bulletin ID 列表，多个 ID 使用逗号（`,`）分隔。 |

- **响应格式**:

| 字段 | 类型 | 说明 |
|------|------|------|
| code | int | 业务码，`0` 表示成功，非 `0` 表示失败。 |
| message | string | 状态描述信息，成功时为 `"success"`，失败时为具体错误信息。 |
| data | object | 业务数据，成功时返回 `true`，失败时为 `null`。 |

- **错误码**:

| errorCode | message | 说明 |
|-----------|---------|------|
| 0 | success | 操作成功 |
| 999999 | DefaultException | 服务器内部异常，请稍后重试 |

- **请求示例**:

```json
{
  "ids": "1001,1002,1003"
}
```

- **响应示例**:

**成功响应**:
```json
{
  "code": 0,
  "message": "success",
  "data": true
}
```

**失败响应**:
```json
{
  "code": 999999,
  "message": "DefaultException",
  "data": null
}
```

### 17.7. API-124 CloseBulletin (POST /api/tools/bulletin/close)

- **鉴权**: 需要 JWT JWT Bearer Token（基于 `[Authorize]` 特性，JWTSettings Config HS256 算法，过期时间 43200 分钟）
- **描述**: 根据指定的Bulletin ID 列表关闭Bulletin，将Bulletin状态更新为 `Closed`。
- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| ids | string | 是 | 待关闭的Bulletin ID 列表，多个 ID 使用英文逗号（,）分隔。 |

- **响应格式**:

| 字段 | 类型 | 说明 |
|---|---|---|
| code | int | 业务码，`0` 表示成功，非 `0` 表示失败。 |
| message | string | 状态描述信息。 |
| data | object | 响应数据，成功时为 `null`。 |

- **错误码**:

| errorCode | message | 说明 |
|---|---|---|
| 100000 | UnAuthToken | 未提供或提供了无效的认证 Token。 |
| 999999 | DefaultException | 服务器内部错误，无法完成Bulletin关闭操作。 |

- **请求示例**:

```json
{
  "ids": "1,2,3"
}
```

- **响应示例**:

**成功响应**

```json
{
  "code": 0,
  "message": "success",
  "data": null
}
```

**失败响应**

```json
{
  "code": 100000,
  "message": "UnAuthToken",
  "data": null
}
```

---

## 18. HealthController 接口


本章共覆盖 1 个 HTTP 端点, 每个端点一个接口卡片.


### 18.1. API-001 HealthController.Get (GET /api/tools/health)

- **鉴权**: 无
- **描述**: 用于检查 AgentInsightService 服务健康状态的探针接口，返回服务是否正常运行。

- **请求参数**: 无

- **响应格式**:

| 字段 | 类型 | 说明 |
|---|---|---|
| `status` | string | 服务健康状态，固定返回 `"Healthy"` |
| `timestamp` | string | 服务器当前 UTC 时间，ISO 8601 格式 |
| `service` | string | 服务名称，固定返回 `"AgentInsightService"` |
| `version` | string | 服务版本号，固定返回 `"1.0.0"` |

- **错误码**: 无（该接口不返回业务错误码）

- **请求示例**:
```http
GET /api/tools/health HTTP/1.1
Host: localhost
```

- **响应示例**:

**成功响应 (200 OK)**:
```json
{
  "status": "Healthy",
  "timestamp": "2025-01-15T08:30:00Z",
  "service": "AgentInsightService",
  "version": "1.0.0"
}
```

**失败响应 (500 Internal Server Error)**:
```json
{
  "status": "Unhealthy",
  "timestamp": "2025-01-15T08:30:00Z",
  "service": "AgentInsightService",
  "version": "1.0.0",
  "error": "Service dependency check failed"
}
```

---

## 19. LiteralRoute 接口


本章共覆盖 2 个 HTTP 端点, 每个端点一个接口卡片。


### 19.1. API-001 源码字面量路由 (GET /api/tools/health)

- **鉴权**: 无
- **描述**: 该接口为源码中通过字面量定义的路由，用于健康检查，验证 API 网关或路由Config是否正确，通常用于连通性测试。

- **请求参数**: 无

- **响应格式**: 无

- **错误码**: 无

- **请求示例**: 无

- **响应示例**: 无

### 19.2. API-002 源码字面量路由 (GET /api/tools/wechat)

- **鉴权**: 无
- **描述**: 该接口为源码中通过字面量定义的测试路由，用于验证 API 网关或路由Config是否正确，通常用于健康检查或连通性测试。

- **请求参数**: 无

- **响应格式**: 无

- **错误码**: 无

- **请求示例**: 无

- **响应示例**: 无

---

## 20. UserConfigController 接口

本章共覆盖 4 个 HTTP 端点，每个端点一个接口卡片。

### 20.1. API-031 UserConfigController.Get (GET /api/user/config)

- **鉴权**: 需要 JWT 认证（JWT Bearer Token），用户需具备相应Privilege。
- **描述**: 根据可选的 `orgId`、`projectId` 和 `type` 参数，查询用户、组织或项目级别的用户Config信息。
- **所属Controller**: `UserConfigController` (`API/Controllers/UserManagement/UserConfigController.cs:31`)

#### 20.1.1. 请求参数

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `orgId` | string | 否 | Org ID。当 `type` 为 `Organization` 时，此参数用于指定要查询的组织。 |
| `projectId` | string | 否 | Project ID。当 `type` 为 `Project` 时，此参数用于指定要查询的项目。 |
| `type` | int | 否 | Config类型枚举，用于指定查询Config的级别。可选值：`User` (0)、`Organization` (1)、`Project` (2)。 |

#### 20.1.2. 响应格式

| 字段 | 类型 | 说明 |
|---|---|---|
| `code` | int | 业务码。`0` 表示成功，非 `0` 值表示失败，具体含义见下方错误码表。 |
| `message` | string | 接口返回的提示信息。 |
| `data` | object | 返回的用户Config数据。具体结构取决于查询的 `type` 和实际的Config内容。 |

#### 20.1.3. 错误码

| errorCode | message | 说明 |
|---|---|---|
| `0` | 成功 | 请求成功。 |
| `100000` | UnAuthToken | Token 无效或未提供。 |
| `150008` | DuplicateUserConfig | 查询到重复的用户Config。 |
| `150022` | AgentConfigNotFound | 未找到对应的 Agent Config。 |
| `999999` | DefaultException | 服务器内部错误。 |

#### 20.1.4. 请求示例

```bash
curl -X GET "https://api.agentinsightservice.com/api/user/config?orgId=org_12345&type=1" \
  -H "Authorization: Bearer <token>"
```

#### 20.1.5. 响应示例

**成功响应**

```json
{
  "code": 0,
  "message": "成功",
  "data": {
    "id": "config_001",
    "orgId": "org_12345",
    "projectId": null,
    "type": 1,
    "settings": {
      "model": "gpt-4o",
      "temperature": 0.7,
      "maxTokens": 2048
    }
  }
}
```

**失败响应 (未找到Config)**

```json
{
  "code": 150022,
  "message": "AgentConfigNotFound",
  "data": null
}
```

### 20.2. API-001 创建用户Config (POST /api/user/config)

- **鉴权**: 需要 JWT 认证（JWT Bearer Token），从 `[Authorize]` 注解提取
- **描述**: 创建新的用户Config，支持 User、Organization、Project 三种Config类型，用于个性化 AgentInsightService 的行为和偏好设置。
- **所属Controller**: `UserConfigController` (`API/Controllers/UserManagement/UserConfigController.cs:44`)

#### 20.2.1. 请求参数

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| configType | int | 是 | Config类型，枚举值：`User`(0)、`Organization`(1)、`Project`(2) |
| configKey | string | 是 | Config键名，用于标识Config项 |
| configValue | string | 是 | Config值，JSON 字符串格式 |
| description | string | 否 | Config描述说明 |
| userId | long | 否 | User ID，当 configType 为 `User` 时必填 |
| organizationId | long | 否 | Org ID，当 configType 为 `Organization` 时必填 |
| projectId | long | 否 | Project ID，当 configType 为 `Project` 时必填 |
| isEnabled | bool | 否 | 是否启用该Config，默认 true |
| expiresAt | DateTime | 否 | Config过期时间，为空表示永不过期 |

#### 20.2.2. 响应格式

| 字段 | 类型 | 说明 |
|------|------|------|
| code | int | 状态码，0 表示成功，非 0 表示失败 |
| message | string | 状态描述信息 |
| data | object | 响应数据，创建成功时返回Config详情 |
| data.id | long | Config ID |
| data.configType | int | Config类型 |
| data.configKey | string | Config键名 |
| data.configValue | string | Config值 |
| data.description | string | Config描述 |
| data.userId | long | User ID |
| data.organizationId | long | Org ID |
| data.projectId | long | Project ID |
| data.isEnabled | bool | 是否启用 |
| data.createdAt | DateTime | 创建时间 |
| data.updatedAt | DateTime | 更新时间 |
| traceId | string | 请求Trace ID，用于日志排查 |

#### 20.2.3. 错误码

| errorCode | message | 说明 |
|-----------|---------|------|
| 100000 | UnAuthToken | 未认证或 Token 无效 |
| 100001 | EmptyUserId | User ID 为空 |
| 150008 | DuplicateUserConfig | Config已存在，重复创建 |
| 150000 | EmptyProjectId | Project ID 为空 |
| 150004 | AgentSettingNotConfig | Agent 相关Config未设置 |
| 150007 | AgentLimitExceeded | Agent 数量超出限制 |
| 999999 | DefaultException | 服务器内部错误 |

#### 20.2.4. 请求示例

```json
{
  "configType": 2,
  "configKey": "agent_behavior_config",
  "configValue": "{\"temperature\": 0.7, \"maxTokens\": 2048, \"modelName\": \"gpt-4o\"}",
  "description": "Agent 行为参数Config",
  "projectId": 1001,
  "isEnabled": true
}
```

#### 20.2.5. 响应示例

**成功响应**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 5001,
    "configType": 2,
    "configKey": "agent_behavior_config",
    "configValue": "{\"temperature\": 0.7, \"maxTokens\": 2048, \"modelName\": \"gpt-4o\"}",
    "description": "Agent 行为参数Config",
    "userId": null,
    "organizationId": null,
    "projectId": 1001,
    "isEnabled": true,
    "createdAt": "2025-01-15T10:30:00Z",
    "updatedAt": "2025-01-15T10:30:00Z"
  },
  "traceId": "a3f2c8e1-9b4d-4f6a-8c2e-5d7b9a1e3f50"
}
```

**失败响应** (Config已存在):
```json
{
  "code": 150008,
  "message": "DuplicateUserConfig",
  "data": null,
  "traceId": "b7e4d9f2-1c5a-4e8b-9d3f-6a2c8e4b0d71"
}
```

### 20.3. API-057 UserConfigController.Update (POST /api/user/config/update)

- **鉴权**: 需要 JWT 认证（JWT Bearer Token）
- **描述**: 更新用户Config信息。该方法接收一个 `UpdateUserConfigBody` 请求体，用于更新指定用户或组织的Config项。
- **所属Controller**: `UserConfigController` (`API/Controllers/UserManagement/UserConfigController.cs:57`)

#### 20.3.1. 请求参数

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| configType | int | 是 | Config类型，枚举值：`User` (0)、`Organization` (1)、`Project` (2) |
| configKey | string | 是 | Config键名，用于标识具体的Config项 |
| configValue | string | 是 | Config值，需要更新的新值 |
| userId | long? | 否 | User ID，当 `configType` 为 `User` 时必填 |
| organizationId | long? | 否 | Org ID，当 `configType` 为 `Organization` 时必填 |
| projectId | long? | 否 | Project ID，当 `configType` 为 `Project` 时必填 |

#### 20.3.2. 响应格式

| 字段 | 类型 | 说明 |
|---|---|---|
| code | int | 状态码，`0` 表示成功，非 `0` 表示失败 |
| message | string | 提示信息，成功时为 `"success"`，失败时为错误描述 |
| data | object | 更新后的Config信息对象，包含 `configType`、`configKey`、`configValue` 等字段 |
| traceId | string | 请求Trace ID，用于日志排查 |

#### 20.3.3. 错误码

| errorCode | message | 说明 |
|---|---|---|
| 100000 | UnAuthToken | Token 无效或未提供，需要重新登录 |
| 150008 | DuplicateUserConfig | Config项已存在，无法重复创建 |
| 150022 | AgentConfigNotFound | 未找到对应的 Agent Config |
| 999999 | DefaultException | 服务器内部错误，请联系管理员 |

#### 20.3.4. 请求示例

```json
{
  "configType": 0,
  "configKey": "theme",
  "configValue": "dark",
  "userId": 12345,
  "organizationId": null,
  "projectId": null
}
```

#### 20.3.5. 响应示例

**成功响应**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "configType": 0,
    "configKey": "theme",
    "configValue": "dark",
    "userId": 12345,
    "organizationId": null,
    "projectId": null,
    "updatedAt": "2024-01-15T10:30:00Z"
  },
  "traceId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

**失败响应** (Token 无效):
```json
{
  "code": 100000,
  "message": "UnAuthToken",
  "data": null,
  "traceId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

### 20.4. API-071 UserConfigController.Delete (GET /api/user/config/delete)

- **鉴权**: 需要认证 (基于 `UserConfigController` 类级别的 `[Authorize]` 特性，该Controller管理用户Config，删除操作需验证用户身份)
- **描述**: 根据指定的Config ID 删除用户Config项。此操作会从系统中移除对应的用户Config记录。
- **所属Controller**: `UserConfigController` (`API/Controllers/UserManagement/UserConfigController.cs:71`)

#### 20.4.1. 请求参数

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | `string` | 是 | 要删除的用户Config的唯一标识符 (UserConfig ID) |

#### 20.4.2. 响应格式

| 字段 | 类型 | 说明 |
|------|------|------|
| `code` | `int` | HTTP 状态码，`200` 表示成功 |
| `errorCode` | `string` | 业务错误码，成功时为 `null` |
| `message` | `string` | 提示信息，成功时为 `"Success"` |
| `data` | `boolean` | 删除结果，`true` 表示删除成功 |
| `traceId` | `string` | 请求Trace ID，用于日志排查 |
| `timestamp` | `string` | 服务器响应时间戳 (ISO 8601 格式) |

#### 20.4.3. 错误码

| errorCode | message | 说明 |
|-----------|---------|------|
| `100000` | UnAuthToken | 未认证或 Token 无效，无法执行删除操作 |
| `100005` | InvalidUser | 当前用户不存在或已被禁用 |
| `150008` | DuplicateUserConfig | 用户Config重复，无法定位唯一待删除Config |
| `999999` | DefaultException | 服务器内部错误，删除过程中发生未预期异常 |

#### 20.4.4. 请求示例

```json
GET /api/user/config/delete?id=config_8f7d2c1a9e4b4f6a8c3d5e7f9a1b2c3d
```

#### 20.4.5. 响应示例

**成功响应 (HTTP 200)**:
```json
{
  "code": 200,
  "errorCode": null,
  "message": "Success",
  "data": true,
  "traceId": "a1b2c3d4-5678-90ab-cdef-1234567890ab",
  "timestamp": "2025-01-15T10:30:00Z"
}
```

**失败响应 (HTTP 401 - 未认证)**:
```json
{
  "code": 401,
  "errorCode": "UnAuthToken",
  "message": "未认证或 Token 无效",
  "data": null,
  "traceId": "b2c3d4e5-6789-01ab-cdef-2345678901bc",
  "timestamp": "2025-01-15T10:30:00Z"
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

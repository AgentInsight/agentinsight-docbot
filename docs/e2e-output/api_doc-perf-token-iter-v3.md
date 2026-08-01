## 1. 引言

AgentInsightService 公开 API 文档。系统提供 AI Agent 可Observation性数据查询、Alert管理、Payment订阅、Agent Config管理等核心能力。API 采用 RESTful 风格，路由前缀为 `/api`，共 76 个接口，分布在 18 个 Controller 中。认证支持 Bearer Token 与 API Key 认证 两种方式。错误码体系基于 `ExceptionCodes` 枚举（`Models/Common/Enums/ExceptionCodes.cs:6`），覆盖认证、参数校验、业务逻辑等场景。版本治理方面，仓库内未发现显式 API 版本控制机制，所有接口均无版本前缀。

### 1.1. 编写目的

本文档为 AgentInsightService 公开 API 参考手册，面向 AI 应用开发者、系统集成方及平台运维人员，提供完整的接口说明与集成指引。文档覆盖 AgentInsightService 主项目（API 和 Agents 子项目）的全部 HTTP 接口，共 76 个，分布在 18 个 Controller/模块中。

本文档旨在帮助目标读者完成以下任务：

- **接口对接**：了解每个 API 的请求参数、响应格式、错误码及调用限制，快速完成系统间集成。
- **能力评估**：通过 API 概览与模块清单，评估 AgentInsightService 的功能边界与适用范围。
- **故障排查**：借助错误码体系与通用约定，定位接口调用失败原因，提升联调效率。
- **安全接入**：掌握 Bearer Token 与 API Key 认证 两种认证方式的使用场景与Config方法。

文档内容基于代码仓库元数据与 AST 提取，所有接口定义、路由路径、参数结构均以仓库当前状态为准。

### 1.2. 适用范围

本文档适用于 AgentInsightService 主项目（API 和 Agents 子项目）的全部 HTTP 接口，共 76 个，分布在 18 个 Controller/模块中。具体覆盖范围如下：

| 模块分类 | Controller 名称 | 路由前缀 | 功能说明 |
|---------|----------------|---------|---------|
| Agent 管理 | AgentConfigController | `/api/agent/config` | Agent Config的查询、创建、更新与删除 [API/Controllers/AgentManagement/AgentConfigController.cs] |
| Agent 管理 | AgentSessionController | `/api/agent/session` | Agent Session的列表查询、详情获取、删除与创建更新 [API/Controllers/AgentManagement/AgentSessionController.cs] |
| Agent 管理 | AgentReportController | `/api/agent/report` | Agent 报表模板的列表查询、详情获取、删除与创建更新 [API/Controllers/AgentManagement/AgentReportController.cs] |
| 数据管理 | MetricsController | `/api/data/metrics` | Trace 指标查询、Observations 列表、Scores 列表及 Trace 详情 [API/Controllers/DataManagement/MetricsController.cs] |
| 数据管理 | ModelController | `/api/data/model` | 模型定义列表查询，支持关键词过滤与预定义模型筛选 [API/Controllers/DataManagement/ModelController.cs] |
| Payment管理 | ProductController | `/api/product` | 产品列表与产品时长列表查询 [API/Controllers/ProductManagement/ProductController.cs] |
| 其他模块 | NotifyController、OrderController、BulletinController、HealthController、WeChatController、AlertController、CaptchaController、OrganizationController 等 | — | 通知、Order、Bulletin、健康检查、微信集成、Alert、Captcha、组织管理等能力 |

本文档不覆盖以下内容：

- 前端页面使用说明与 UI 交互细节。
- 内部部署架构、数据库表结构设计。
- 非 HTTP 协议的系统间通信机制（如消息队列消费逻辑）。

### 1.3. 术语与缩略语

本文档使用 AgentInsightService 标识符体系，关键术语见下表。所有术语在文档中均保留英文原文，不进行翻译。

| 术语/缩略语 | 说明 |
|------------|------|
| AgentInsightService | 本项目名称，提供 AI Agent 可Observation性数据查询、Alert管理、Payment订阅、Agent Config管理等核心能力 |
| AgentInsight | 产品品牌名，与 AgentInsightService 同义 |
| InsightService | 产品品牌名缩写形式 |
| Agent | Agent，指由 AI 模型驱动的自动化任务执行单元 |
| Trace | 一次完整的 Agent 执行链路Trace记录 |
| Observation | Trace 执行过程中的Observation数据项 |
| Score | Trace 执行结果的Score数据 |
| API Key | 服务端集成时使用的密钥凭证 |
| JWT | JSON Web Token，用于 Web Session认证 |
| Base URL | 接口请求的基础路径前缀 |
| ISO 8601 | 国际标准日期时间格式 |

### 1.4. 参考文档

本文档基于以下代码仓库元数据与 AST 提取结果生成：

| 参考来源 | 说明 |
|---------|------|
| `API/Controllers/AgentManagement/AgentConfigController.cs` | Agent Config管理接口定义，路由前缀 `/api/agent/config` |
| `API/Controllers/AgentManagement/AgentSessionController.cs` | Agent Session管理接口定义，路由前缀 `/api/agent/session` |
| `API/Controllers/AgentManagement/AgentReportController.cs` | Agent 报表管理接口定义，路由前缀 `/api/agent/report` |
| `API/Controllers/DataManagement/MetricsController.cs` | 数据指标接口定义，路由前缀 `/api/data/metrics` |
| `API/Controllers/DataManagement/ModelController.cs` | 模型管理接口定义，路由前缀 `/api/data/model` |
| `API/Controllers/ProductManagement/ProductController.cs` | 产品接口定义，路由前缀 `/api/product` |
| `Models/Common/Enums/ExceptionCodes.cs:6` | 错误码枚举定义，覆盖认证、参数校验、业务逻辑等场景 |

### 1.5. 版本历史

| 版本 | 日期 | 说明 |
|------|------|------|
| v1.0 | 当前代码库状态 | 本文档初始版本，基于代码仓库元数据与 AST 提取生成 |

本文档为初始版本，基于当前代码库状态编写。后续版本更新将随代码变更同步修订。

### 1.6. API 概览

AgentInsightService API 采用 RESTful 风格设计，基础信息如下：

| Config项 | 值 | 说明 |
|--------|------|------|
| Base URL | `/api` | 所有接口的路由前缀 |
| 数据格式 | JSON | 请求与响应均使用 JSON 序列化 |
| 时间格式 | ISO 8601 | 所有时间字段遵循 ISO 8601 标准 |
| 字符集 | UTF-8 | 统一使用 UTF-8 编码 |
| 版本治理 | 未启用 | 仓库内未发现显式 API 版本控制机制，所有接口均无版本前缀 |

API 接口分布在 18 个 Controller/模块中，覆盖以下核心能力域：

- **Agent 可Observation性数据查询**：通过 MetricsController 提供 Trace、Observation、Score 等指标数据的查询能力 [API/Controllers/DataManagement/MetricsController.cs]。
- **Alert管理**：通过 AlertController 提供Alert规则的创建、更新、删除与订阅能力。
- **Payment订阅**：通过 ProductController、OrderController 提供产品查询、订单管理等Payment订阅相关能力 [API/Controllers/ProductManagement/ProductController.cs]。
- **Agent Config管理**：通过 AgentConfigController、AgentSessionController、AgentReportController 提供 Agent Config、Session、报表模板的管理能力 [API/Controllers/AgentManagement/AgentConfigController.cs]。

### 1.7. 认证授权

AgentInsightService 支持两种认证方式，分别面向不同的集成场景：

#### 1.7.1. Bearer Token

Bearer Token 用于 Web Session认证。调用方需在 HTTP 请求头中携带 `Authorization: Bearer <token>` 进行身份认证。该方式适用于浏览器端 Web 应用的用户Session管理。

#### 1.7.2. API Key 认证

API Key 认证 用于服务端集成场景，凭证由 `/api/user/apikey` 接口管理。调用方需在 HTTP 请求头中携带 API Key 作为 Basic Auth 凭证。该方式适用于服务端到服务端的系统间集成，便于自动化运维与程序化调用。

两种认证方式的选择建议：

| 场景 | 推荐认证方式 |
|------|------------|
| Web 浏览器用户Session | Bearer Token |
| 服务端系统集成 | API Key 认证 |
| 自动化脚本/定时任务 | API Key 认证 |

### 1.8. 通用约定

#### 1.8.1. 统一响应结构

所有接口的响应体遵循 `ApiResponse<T>` 统一结构，包含以下字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| code | int | 响应状态码，0 表示成功，非 0 表示具体错误 |
| message | string | 响应消息，成功时为空或 success，失败时为错误描述 |
| data | T | 业务数据负载，泛型类型，具体结构由各接口定义 |

#### 1.8.2. 分页参数

分页查询接口统一使用以下参数：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| page | int | 1 | 页码，从 1 开始 |
| pageSize | int | 10 | 每页数量 |

分页响应在 `ApiResponse<T>` 中额外包含 `totalCount`（总记录数）与当前页数据条数。例如 AgentSessionController 的 Get 方法返回 `ApiResponse<AgentSession>(sessions, totalCount, page, sessions.Count)`，其中 `totalCount` 为总记录数，`sessions.Count` 为当前页返回条数 [API/Controllers/AgentManagement/AgentSessionController.cs]。

#### 1.8.3. 时间格式

所有时间字段采用 ISO 8601 格式，例如 `2024-01-01T00:00:00Z`。在查询参数中传递时间范围时，可使用 `from` 和 `to` 字段指定起止时间，格式为 `yyyy-MM-dd HH:mm:ss`。

#### 1.8.4. 错误码体系

错误码体系基于 `ExceptionCodes` 枚举定义（`Models/Common/Enums/ExceptionCodes.cs:6`），覆盖认证、参数校验、业务逻辑等场景。各接口的错误码在具体章节中列出，通用错误码约定如下：

| errorCode | 说明 |
|-----------|------|
| 0 | 成功 |
| 100001 | User ID 为空 |
| 100005 | 用户无效 |
| 100031 | API Key 不存在 |
| 100038 | API Key 无效 |
| 150004 | Agent 设置未Config |
| 150007 | Agent 数量超限 |
| 150021 | Agent Session不存在 |
| 150022 | Agent Config不存在 |
| 150023 | Agent 报表模板不存在 |
| 160001 | 创建Alert失败 |
| 160002 | 更新Alert失败 |
| 160003 | 删除Alert失败 |
| 160012 | 订阅Alert失败 |
| 990001 | 加密失败 |
| 990002 | 解密失败 |
| 990003 | 密码哈希失败 |

> **注意**：上述错误码及其说明基于 `ExceptionCodes` 枚举定义整理。由于当前代码仓库中 `ExceptionCodes.cs` 的具体枚举值可能随版本迭代发生变化，本文档所列错误码值及对应说明应与代码实际定义保持一致。若实际使用中发现不一致，请以 `Models/Common/Enums/ExceptionCodes.cs` 中的定义为准。完整错误码列表请参见各接口详情章节。

---

## 2. 附录

### 2.1. 错误码清单

| 错误码常量 | 数值 | 含义 |
|-----------|------|------|
| `UnAuthToken` | 100000 | 登录已过期，请重新登录 |
| `GetUserInfoFailed` | 100001 | 用户信息获取失败，请重新登录 |
| `RegisterFailed` | 100004 | 注册失败，请稍后重试 |
| `InvalidCredentials` | 100005 | 手机号或密码错误 |
| `UserNameTooLong` | 100019 | 用户名不能超过100个字符 |
| `UserAlreadyOrgMember` | 100024 | 该用户已是组织成员 |
| `ApiKeyNotFound` | 100031 | API密钥不存在 |
| `ApiKeyCreateFailed` | 100032 | API密钥创建失败 |
| `ApiKeyDeleteFailed` | 100033 | API密钥删除失败 |
| `ApiKeyNotMatched` | 100036 | 未找到对应的API密钥 |
| `InvalidAuthCredential` | 100037 | 认证凭证无效 |
| `InvalidApiKey` | 100038 | API密钥无效 |
| `UserNotInitialized` | 100041 | 用户信息未初始化，请重新登录 |
| `WeChatUserInfoFailed` | 620004 | 获取微信用户信息失败 |
| `AgentSettingNotConfigured` | 150004 | Agent 设置未Config |
| `AgentQuotaExceeded` | 150007 | Agent 配额已超限 |
| `UserConfigDuplicate` | 150008 | 用户Config重复 |
| `UpdateAgentRateFailed` | 150020 | Agent 配额更新失败 |
| `AgentSessionNotFound` | 150021 | Agent Session不存在 |
| `AgentConfigNotFound` | 150022 | Agent Config不存在 |
| `AgentReportTemplateNotFound` | 150023 | Agent 报告模板不存在 |
| `AgentReportTemplateNameEmpty` | 150024 | Agent 报告模板名称为空 |
| `AlertNotFound` | 160000 | Alert不存在 |
| `AlertCreateFailed` | 160001 | Alert创建失败 |
| `UpdateAlertFailed` | 160002 | Alert更新失败 |
| `AlertDeleteFailed` | 160003 | Alert删除失败 |
| `AlertStatCycleInvalid` | 160004 | Alert统计周期无效 |
| `AlertFrequencyInvalid` | 160005 | Alert频率无效 |
| `AlertFieldInvalid` | 160006 | Alert字段无效 |
| `AlertOperatorInvalid` | 160007 | Alert操作符无效 |
| `AlertThresholdInvalid` | 160008 | Alert阈值无效 |
| `AlertNameInvalid` | 160010 | Alert名称无效 |
| `AlertNotifyChannelInvalid` | 160011 | Alert通知方式无效 |
| `SubscribeAlertFailed` | 160012 | Alert订阅失败 |
| `AlertOrgAccessDenied` | 160013 | 无权访问该组织的Alert |
| `AlertProjectNotFound` | 160014 | Alert关联项目不存在 |
| `AlertNameTooLong` | 160015 | Alert名称过长 |

错误码对应的用户提示文案在 `API/Resources/Text.zh-CN.json` 中定义，例如 `"UnAuthToken": "登录已过期，请重新登录"`、`"InvalidAuthCredential": "认证凭证无效"`、`"SendSMSTooOften": "操作过于频繁，请稍后再获取Captcha"`。服务端通过 `Oops.Oh(ExceptionCodes.XXX)` 抛出业务异常，由全局异常中间件捕获后转换为统一响应结构返回客户端。

### 2.2. 通用响应结构

AgentInsightService 所有 API 接口统一返回以下 JSON 结构：

```json
{
  "code": 0,
  "message": "success",
  "data": { }
}
```

各字段说明如下：

| 字段 | 类型 | 说明 |
|------|------|------|
| `code` | int | 业务状态码，`0` 表示成功，非零值对应 `ExceptionCodes` 枚举中定义的错误码 |
| `message` | string | 状态描述，成功时为 `"success"`，失败时为对应的错误提示文案（支持多语言） |
| `data` | object | 业务数据负载，成功时返回具体数据对象，失败时通常为 `null` 或空对象 |

响应结构在Controller层通过 `ApiResponse<T>` 泛型类型统一构造，例如 `AlertController.GetConfig` 返回 `new ApiResponse<AlertConfig>([config])`（`API/Controllers/UserManagement/AlertController.cs`），`AgentConfigController.Get` 返回 `new ApiResponse<AgentConfig>(configs)`（`API/Controllers/AgentManagement/AgentConfigController.cs`）。`ApiResponse<T>` 的构造函数接受数据列表或单个数据对象，自动填充 `code = 0` 与 `message = "success"`。

当业务处理抛出 `Furion` 异常时（通过 `Oops.Oh(ExceptionCodes.XXX)` 触发），全局异常中间件会捕获异常并将 `code` 设置为对应的错误码数值，`message` 设置为 `API/Resources/Text.zh-CN.json` 中映射的本地化文案。客户端应优先依据 `code` 字段判断业务结果，而非依赖 HTTP 状态码。

### 2.3. 版本治理

AgentInsightService 当前版本治理策略如下：

1. **无 URI 版本前缀**：仓库内所有 Controller 的路由均未包含版本号前缀，例如 `[Route("api/alert")]`（`API/Controllers/UserManagement/AlertController.cs`）、`[Route("api/agent/config")]`（`API/Controllers/AgentManagement/AgentConfigController.cs`）、`[Route("api/payment/notify")]`（`API/Controllers/PaymentManagement/NotifyController.cs`）。所有接口统一挂载在 `/api` 根路径下，共 76 个接口，分布在 18 个 Controller 中。

2. **后续版本规划**：考虑到 API 演进需求，后续引入版本治理时可参考以下两种方案：
   - **消息头版本化**：客户端在 HTTP 请求头中携带版本标识（如 `X-API-Version: v1`），服务端通过中间件解析版本号并路由到对应的Handler。该方案不改变现有 URI 结构，对客户端 URL 无侵入。
   - **路径版本化**：在路由前缀中增加版本段（如 `/api/v1/alert`），需要同步修改所有 Controller 的 `[Route]` 特性。该方案更直观，但会破坏现有客户端的 URL 兼容性。

3. **兼容性承诺**：在未正式引入版本机制前，服务端保证现有接口路径与响应结构的向后兼容。新增字段时遵循“增量添加”原则，不删除或重命名既有字段，避免破坏客户端解析。

### 2.4. 限流与配额

AgentInsightService 的限流与配额策略分为以下三个层面：

**1. 短信Captcha发送间隔**

短信Captcha接口受 `CaptchaSetting.ResendInterval` Config项约束，默认值为 `60` 秒（`API/Resources/Text.zh-CN.json` 中对应错误码 `SendSMSTooOften` 的提示为“操作过于频繁，请稍后再获取Captcha”）。同一手机号在 60 秒内重复请求发送Captcha时，服务端返回 `SendSMSTooOften` 错误。Captcha有效期由 `CaptchaSetting.ExpireIn` 控制，默认 `300` 秒；短信Captcha长度为 `CaptchaSetting.SMSCodeLength = 6`，图形Captcha长度为 `CaptchaSetting.ImageCodeLength = 5`，邮件Captcha长度为 `CaptchaSetting.EmailCodeLength = 6`。

**2. Agent 月度配额**

Agent 月度配额通过两个专用接口控制：

| 接口 | 方法 | 功能 |
|------|------|------|
| `/api/user/privilege/agent/validate` | GET | 校验当前用户是否仍有可用的 Agent 月度配额，返回配额使用情况 |
| `/api/user/privilege/agent/deduct` | GET | 扣减一次 Agent 月度配额，配额不足时返回 `AgentQuotaExceeded`（150007） |

配额扣减与校验逻辑在 `API/Controllers/UserManagement/UserController.cs` 中实现（`DeductMonthlyAgentRate` 位于第 242 行，`ValidateMonthlyAgentRate` 位于第 258 行）。配额超限时抛出 `AgentQuotaExceeded` 异常，客户端应提示用户升级套餐或等待下个计费周期。

**3. 一般 API 限流**

除短信Captcha与 Agent 配额外，一般 API 接口暂无硬性限流策略。生产环境部署时建议在网关层（如 Yarp.ReverseProxy）Config全局速率限制，防止异常流量冲击后端服务。

### 2.5. 安全合规说明

AgentInsightService 在安全合规方面遵循以下规范：

**1. 传输层安全**

所有 API 访问必须使用 HTTPS 协议，禁止明文 HTTP 传输。生产环境由反向代理或负载均衡器终止 TLS，后端服务间通信同样建议启用 TLS 加密。

**2. 敏感Config管理**

数据库连接字符串、AES 加密密钥、第三方服务凭证等敏感Config均通过环境变量注入，禁止硬编码在代码仓库或Config文件中。关键Config项包括：

| Config项 | 环境变量 | 说明 |
|--------|---------|------|
| `Encryption.AesKey` | `${AES_KEY}` | AES 加密密钥 |
| `ConnectionStrings.UserDbConnection` | `${USER_DB_*}` | 用户数据库连接 |
| `ConnectionStrings.BusinessDbConnection` | `${BUSINESS_DB_*}` | 业务数据库连接 |
| `ConnectionStrings.TrackingDbConnection` | `${TRACKING_DB_*}` | Trace数据库连接 |
| `ConnectionStrings.ClickHouseConnection` | `${CLICKHOUSE_DB_*}` | ClickHouse 分析数据库连接 |
| `WeChat.AppId` / `WeChat.AppSecret` | `${WECHAT_APP_ID}` / `${WECHAT_APP_SECRET}` | 微信第三方服务凭证 |

**3. API 密钥存储**

用户创建的 API Key 不以明文形式存储。服务端对 API Key 进行 SHA256 哈希后落库，客户端仅能在创建时获取一次明文 Secret。校验时对客户端提交的密钥执行相同哈希算法后比对，确保数据库泄露不会导致密钥直接暴露。API Key 删除接口为 `POST /api/user/apikey/delete`（`API/Controllers/UserManagement/UserController.cs:272`）。

**4. Payment回调验签**

Payment回调通知（微信Payment与Payment宝）必须执行严格的签名验证：

- **微信Payment**：`NotifyController.WeChatNotify`（`API/Controllers/PaymentManagement/NotifyController.cs`）在读取请求体后，首先调用 `ExamineWeChatRequest` 验证请求头中的签名信息，验签失败时抛出 `WeChatNotifySignatureInvalid` 异常（对应文案“微信Payment通知签名验证失败”）。验证通过后对通知内容进行解密与业务处理，最终返回微信要求的成功/失败响应格式。
- **Payment宝Payment**：`NotifyController.AlipayNotify` 调用 `ProcessAlipayNotify` 验证Payment宝异步通知的签名，验签失败时返回 `"fail"`，成功时返回 `"success"`。

验签逻辑遵循微信Payment与Payment宝开放平台的官方规范，包括证书序列号校验、签名算法验证、通知内容解密等步骤。Payment回调接口标记为 `[AllowAnonymous]` 且不在 Swagger 文档中展示（`[ApiExplorerSettings(IgnoreApi = true)]`），避免被误认为公开接口。

---

## 3. AgentConfigController 接口


本章共覆盖 3 个 HTTP 接口 (AST 确定性卡片, 未经 LLM 改写).


### 3.1. API-001 Get (GET `/api/agent/config`)
- **认证**: Bearer Token 或 API Key 认证（`[Authorize]` 装饰器）
- **描述**: 获取 Agent Config
- **源码位置**: `API/Controllers/AgentManagement/AgentConfigController.cs:28`
- **Handler**: `AgentConfigController.Get`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| — | — | — | 该方法无显式请求参数（方法签名为 `Get()`，未声明参数）。 |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| — | — | 返回 `Task`（HTTP 200 OK）。具体响应体结构以源码实现为准，AST 未提取到 DTO 定义。 |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `100000` | `UnAuthToken` | 认证失败（`ExceptionCodes.UnAuthToken`） |

**请求示例**

```http
GET /api/agent/config HTTP/1.1
Host: localhost
Authorization: Bearer <your-jwt-token>
```

**响应示例**

```http
HTTP/1.1 200 OK
Content-Type: application/json
```


### 3.2. API-002 Delete (GET `/api/agent/config/delete`)
- **认证**: Bearer Token 或 API Key 认证（`[Authorize]` 装饰器）
- **描述**: 删除 Agent Config
- **源码位置**: `API/Controllers/AgentManagement/AgentConfigController.cs:40`
- **Handler**: `AgentConfigController.Delete`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| — | — | — | 该方法无显式请求参数（方法签名为 `Delete()`，未声明参数）。 |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| — | — | 返回 `Task`（HTTP 200 OK）。具体响应体结构以源码实现为准，AST 未提取到 DTO 定义。 |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `100000` | `UnAuthToken` | 认证失败（`ExceptionCodes.UnAuthToken`） |

**请求示例**

```http
GET /api/agent/config/delete HTTP/1.1
Host: localhost
Authorization: Bearer <your-jwt-token>
```

**响应示例**

```http
HTTP/1.1 200 OK
Content-Type: application/json
```


### 3.3. API-003 Post (POST `/api/agent/config`)
- **认证**: Bearer Token 或 API Key 认证（`[Authorize]` 装饰器）
- **描述**: 更新 Agent Config
- **源码位置**: `API/Controllers/AgentManagement/AgentConfigController.cs:54`
- **Handler**: `AgentConfigController.Post`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| body | string | 是 | 请求体，类型为 `string`，包含待更新的 Agent Config内容。具体结构以源码实现为准，AST 未提取到 DTO 定义。 |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| — | — | 返回 `Task`（HTTP 200 OK）。具体响应体结构以源码实现为准，AST 未提取到 DTO 定义。 |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `100000` | `UnAuthToken` | 认证失败（`ExceptionCodes.UnAuthToken`） |
| `100001` | `InvalidParameter` | 参数校验失败（`ExceptionCodes.InvalidParameter`） |

**请求示例**

```http
POST /api/agent/config HTTP/1.1
Host: localhost
Authorization: Bearer <your-jwt-token>
Content-Type: application/json

"<agent-config-json-string>"
```

**响应示例**

```http
HTTP/1.1 200 OK
Content-Type: application/json
```

---

## 4. AgentReportController 接口


本章共覆盖 3 个 HTTP 接口 (AST 确定性卡片, 未经 LLM 改写).


### 4.1. API-001 GetTemplates (GET `/api/agent/report`)
- **认证**: 见源码注解 (`[Authorize]` / 等价装饰器); AST 未解析时标注「见代码」
- **描述**: 获取 Agent 报表模板列表。支持按模板 ID 精确查询，以及通过 `includedpredefined` / `includedpredefinedonly` 参数控制是否包含预定义模板。支持分页返回。
- **源码位置**: `API/Controllers/AgentManagement/AgentReportController.cs:35`
- **Handler**: `AgentReportController.GetTemplates`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | string | 否 | 模板 ID，传入时返回指定模板 |
| includedpredefined | bool | 否 | 是否包含预定义模板，默认 false |
| includedpredefinedonly | bool | 否 | 是否仅返回预定义模板，默认 false |
| page | int | 否 | 页码，默认 `AgentInsightConst.DefaultPage` |
| pageSize | int | 否 | 每页条数，默认 `AgentInsightConst.DefaultPageSize` |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| data | 集合 | 模板列表（分页结果） |
| total | int | 符合条件的模板总数 |
| page | int | 当前页码 |
| pageSize | int | 当前页大小 |

> 注：具体响应字段以源码实际返回 DTO 为准，此处为语义层面的通用描述。

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `ExceptionCodes` 枚举定义见 `Models/Common/Enums/ExceptionCodes.cs:6` | — | 错误码统一引用该枚举，覆盖认证、参数校验、业务逻辑等场景 |


### 4.2. API-002 DeleteTemplates (GET `/api/agent/report/delete`)
- **认证**: 见源码注解 (`[Authorize]` / 等价装饰器); AST 未解析时标注「见代码」
- **描述**: 根据模板 ID 批量删除报表模板。支持传入多个 ID（以逗号分隔）。
- **源码位置**: `API/Controllers/AgentManagement/AgentReportController.cs:48`
- **Handler**: `AgentReportController.DeleteTemplates`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| ids | string | 是 | 待删除的模板 ID 列表，多个 ID 以逗号分隔 |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| success | bool | 是否删除成功 |
| message | string | 操作结果描述 |

> 注：具体响应字段以源码实际返回 DTO 为准，此处为语义层面的通用描述。

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `ExceptionCodes` 枚举定义见 `Models/Common/Enums/ExceptionCodes.cs:6` | — | 错误码统一引用该枚举，覆盖认证、参数校验、业务逻辑等场景 |


### 4.3. API-003 CreateOrUpdateTemplate (POST `/api/agent/report`)
- **认证**: 见源码注解 (`[Authorize]` / 等价装饰器); AST 未解析时标注「见代码」
- **描述**: 创建或更新 Agent 报表模板。请求体为 `AgentReportTemplateBody`，包含模板的完整Config信息；若模板 ID 已存在则执行更新，否则执行创建。
- **源码位置**: `API/Controllers/AgentManagement/AgentReportController.cs:62`
- **Handler**: `AgentReportController.CreateOrUpdateTemplate`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| body | AgentReportTemplateBody | 是 | 模板Config对象（JSON 请求体），包含模板 ID、名称、Config内容等字段，具体结构以源码 DTO 定义为准 |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| success | bool | 是否保存成功 |
| id | string | 创建或更新后的模板 ID |
| message | string | 操作结果描述 |

> 注：具体响应字段以源码实际返回 DTO 为准，此处为语义层面的通用描述。

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `ExceptionCodes` 枚举定义见 `Models/Common/Enums/ExceptionCodes.cs:6` | — | 错误码统一引用该枚举，覆盖认证、参数校验、业务逻辑等场景 |

---

## 5. AgentSessionController 接口


本章共覆盖 3 个 HTTP 接口 (AST 确定性卡片, 未经 LLM 改写).


### 5.1. API-001 Get (GET `/api/agent/session`)
- **认证**: 见源码注解 (`[Authorize]` / 等价装饰器); AST 未解析时标注「见代码」
- **描述**: public async Task Get(string? id, int page = 1, int pageSize = 20)
- **源码位置**: `API/Controllers/AgentManagement/AgentSessionController.cs:33`
- **Handler**: `AgentSessionController.Get`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| — | — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `UsageTracking = 2` | — | 来自 AST 枚举清单 |
| `ExceptionCodes.UnAuthToken = 100000` | — | 来自 AST 枚举清单 |
| `ExceptionCodes.EmptyUserId = 100001` | — | 来自 AST 枚举清单 |
| `ExceptionCodes.ExistedMobile = 100003` | — | 来自 AST 枚举清单 |
| `ExceptionCodes.CreateUserFailed = 100004` | — | 来自 AST 枚举清单 |


### 5.2. API-002 Delete (GET `/api/agent/session/delete`)
- **认证**: 见源码注解 (`[Authorize]` / 等价装饰器); AST 未解析时标注「见代码」
- **描述**: public async Task Delete(string? ids)
- **源码位置**: `API/Controllers/AgentManagement/AgentSessionController.cs:46`
- **Handler**: `AgentSessionController.Delete`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| — | — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `AuditAction.Delete` | — | 来自 AST 枚举清单 |
| `ExceptionCodes.UnAuthToken = 100000` | — | 来自 AST 枚举清单 |
| `ExceptionCodes.EmptyUserId = 100001` | — | 来自 AST 枚举清单 |
| `ExceptionCodes.ExistedMobile = 100003` | — | 来自 AST 枚举清单 |
| `ExceptionCodes.CreateUserFailed = 100004` | — | 来自 AST 枚举清单 |


### 5.3. API-003 Post (POST `/api/agent/session`)
- **认证**: 见源码注解 (`[Authorize]` / 等价装饰器); AST 未解析时标注「见代码」
- **描述**: public async Task Post(AgentSessionBody body)
- **源码位置**: `API/Controllers/AgentManagement/AgentSessionController.cs:60`
- **Handler**: `AgentSessionController.Post`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| — | — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `TransactionType.WeChatTransaction` | — | 来自 AST 枚举清单 |
| `TransactionType.AlipayTransaction` | — | 来自 AST 枚举清单 |
| `RouteType.None = 0` | — | 来自 AST 枚举清单 |
| `RouteType.Public = 1` | — | 来自 AST 枚举清单 |
| `RouteType.PublicApi = 2` | — | 来自 AST 枚举清单 |

---

## 6. MetricsController 接口


本章共覆盖 4 个 HTTP 接口 (AST 确定性卡片, 未经 LLM 改写).


### 6.1. API-001 GetObservations (GET `/api/data/metrics/observations`)
- **认证**: 见源码注解 (`[Authorize]` / 等价装饰器); AST 未解析时标注「见代码」
- **描述**: public async Task\<IActionResult\> GetObservations(string id, int page = AgentInsightConst.DefaultPage, int pagesize = AgentInsightConst.DefaultPageSize)
- **源码位置**: `API/Controllers/DataManagement/MetricsController.cs:34`
- **Handler**: `MetricsController.GetObservations`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| — | — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| — | — | 错误码体系基于 `ExceptionCodes` 枚举 (`Models/Common/Enums/ExceptionCodes.cs:6`); 具体错误码见源码. |


### 6.2. API-002 GetScores (GET `/api/data/metrics/scores`)
- **认证**: 见源码注解 (`[Authorize]` / 等价装饰器); AST 未解析时标注「见代码」
- **描述**: public async Task\<IActionResult\> GetScores(string id, int page = AgentInsightConst.DefaultPage, int pagesize = AgentInsightConst.DefaultPageSize)
- **源码位置**: `API/Controllers/DataManagement/MetricsController.cs:50`
- **Handler**: `MetricsController.GetScores`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| — | — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| — | — | 错误码体系基于 `ExceptionCodes` 枚举 (`Models/Common/Enums/ExceptionCodes.cs:6`); 具体错误码见源码. |


### 6.3. API-003 GetTraces (GET `/api/data/metrics/traces`)
- **认证**: 见源码注解 (`[Authorize]` / 等价装饰器); AST 未解析时标注「见代码」
- **描述**: public async Task\<IActionResult\> GetTraces(string ids)
- **源码位置**: `API/Controllers/DataManagement/MetricsController.cs:64`
- **Handler**: `MetricsController.GetTraces`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| — | — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| — | — | 错误码体系基于 `ExceptionCodes` 枚举 (`Models/Common/Enums/ExceptionCodes.cs:6`); 具体错误码见源码. |


### 6.4. API-004 GetTraces (POST `/api/data/metrics/traces`)
- **认证**: 见源码注解 (`[Authorize]` / 等价装饰器); AST 未解析时标注「见代码」
- **描述**: public async Task\<IActionResult\> GetTraces([FromBody] TraceMetricsBody body)
- **源码位置**: `API/Controllers/DataManagement/MetricsController.cs:125`
- **Handler**: `MetricsController.GetTraces`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| — | — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| — | — | 错误码体系基于 `ExceptionCodes` 枚举 (`Models/Common/Enums/ExceptionCodes.cs:6`); 具体错误码见源码. |

---

## 7. ModelController 接口


本章共覆盖 1 个 HTTP 接口 (AST 确定性卡片, 未经 LLM 改写).


### 7.1. API-001 Get (GET `/api/data/model`)
- **认证**: 见源码注解 (`[Authorize]` / 等价装饰器); AST 未解析时标注「见代码」
- **描述**: public async Task Get(string? keyword, string? projectid, bool includedpredefined = false, string orderby = "-updatedat", int page = 1, int pageSize = 20)
- **源码位置**: `API/Controllers/DataManagement/ModelController.cs:34`
- **Handler**: `ModelController.Get`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| keyword | string? | 否 | 关键字筛选 |
| projectid | string? | 否 | Project ID 筛选 |
| includedpredefined | bool | 否 | 是否包含预定义模型, 默认 false |
| orderby | string | 否 | 排序字段, 默认 "-updatedat" |
| page | int | 否 | 页码, 默认 1 |
| pageSize | int | 否 | 每页条数, 默认 20 |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `UsageTracking = 2` | — | 来自 AST 枚举清单 (QueueType) |

---

## 8. NotifyController 接口


本章共覆盖 2 个 HTTP 接口 (AST 确定性卡片, 未经 LLM 改写).


### 8.1. API-001 WeChatNotify (POST `/api/payment/notify/wechatnotify`)
- **认证**: 见源码注解 (`[Authorize]` / 等价装饰器); AST 未解析时标注「见代码」
- **描述**: public async Task WeChatNotify()
- **源码位置**: `API/Controllers/PaymentManagement/NotifyController.cs:29`
- **Handler**: `NotifyController.WeChatNotify`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| — | — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `UnAuthToken = 100000` | — | 来自 AST 枚举清单 |
| `EmptyUserId = 100001` | — | 来自 AST 枚举清单 |


### 8.2. API-002 AlipayNotify (POST `/api/payment/notify/alipaynotify`)
- **认证**: 见源码注解 (`[Authorize]` / 等价装饰器); AST 未解析时标注「见代码」
- **描述**: public async Task AlipayNotify()
- **源码位置**: `API/Controllers/PaymentManagement/NotifyController.cs:57`
- **Handler**: `NotifyController.AlipayNotify`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| — | — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `UnAuthToken = 100000` | — | 来自 AST 枚举清单 |
| `EmptyUserId = 100001` | — | 来自 AST 枚举清单 |

---

## 9. OrderController 接口


本章共覆盖 4 个 HTTP 接口 (AST 确定性卡片, 未经 LLM 改写).


### 9.1. API-001 Get (GET `/api/payment/order`)
- **认证**: 见源码注解 (`[Authorize]` / 等价装饰器); AST 未解析时标注「见代码」
- **描述**: public async Task Get(string orgId, int page, int pageSize)
- **源码位置**: `API/Controllers/PaymentManagement/OrderController.cs:34`
- **Handler**: `OrderController.Get`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| orgId | string | 是 | 组织标识 |
| page | int | 否 | 页码 |
| pageSize | int | 否 | 每页条数 |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `UsageTracking = 2` | — | 来自 AST 枚举清单 |


### 9.2. API-002 Place (POST `/api/payment/order`)
- **认证**: 见源码注解 (`[Authorize]` / 等价装饰器); AST 未解析时标注「见代码」
- **描述**: public async Task Place(AgentInsightOrderBody body)
- **源码位置**: `API/Controllers/PaymentManagement/OrderController.cs:48`
- **Handler**: `OrderController.Place`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| body | AgentInsightOrderBody | 是 | 请求体 |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `Place` | — | 来自 AST 枚举清单 |


### 9.3. API-003 Query (GET `/api/payment/order/query`)
- **认证**: 见源码注解 (`[Authorize]` / 等价装饰器); AST 未解析时标注「见代码」
- **描述**: public async Task Query(string orderNo)
- **源码位置**: `API/Controllers/PaymentManagement/OrderController.cs:64`
- **Handler**: `OrderController.Query`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| orderNo | string | 是 | 订单号 |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `Query` | — | 来自 AST 枚举清单 |


### 9.4. API-004 GetConversion (GET `/api/payment/order/conversion`)
- **认证**: 见源码注解 (`[Authorize]` / 等价装饰器); AST 未解析时标注「见代码」
- **描述**: public async Task GetConversion(string newProductId)
- **源码位置**: `API/Controllers/PaymentManagement/OrderController.cs:79`
- **Handler**: `OrderController.GetConversion`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| newProductId | string | 是 | 新产品标识 |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `TransactionType` | — | 来自 AST 枚举清单 |
| `WeChatTransaction` | — | 来自 AST 枚举清单 |
| `AlipayTransaction` | — | 来自 AST 枚举清单 |
| `RouteType` | — | 来自 AST 枚举清单 |
| `None = 0` | — | 来自 AST 枚举清单 |
| `Public = 1` | — | 来自 AST 枚举清单 |
| `PublicApi = 2` | — | 来自 AST 枚举清单 |

---

## 10. ProductController 接口


本章共覆盖 2 个 HTTP 接口 (AST 确定性卡片, 未经 LLM 改写).


### 10.1. API-001 Get (GET `/api/product`)
- **认证**: 见源码注解 (`[Authorize]` / 等价装饰器); AST 未解析时标注「见代码」
- **描述**: public async Task<IActionResult> Get()
- **源码位置**: `API/Controllers/ProductManagement/ProductController.cs:26`
- **Handler**: `ProductController.Get`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| — | — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `UsageTracking = 2` | — | 来自 AST 枚举清单 |


### 10.2. API-002 GetDuration (GET `/api/product/duration`)
- **认证**: 见源码注解 (`[Authorize]` / 等价装饰器); AST 未解析时标注「见代码」
- **描述**: public async Task<IActionResult> GetDuration()
- **源码位置**: `API/Controllers/ProductManagement/ProductController.cs:38`
- **Handler**: `ProductController.GetDuration`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| — | — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `UsageTracking = 2` | — | 来自 AST 枚举清单 |

---

## 11. BulletinController 接口


本章共覆盖 7 个 HTTP 接口 (AST 确定性卡片, 未经 LLM 改写).


### 11.1. API-001 Post (POST `/api/tools/bulletin`)
- **认证**: 见源码注解 (`[Authorize]` / 等价装饰器); AST 未解析时标注「见代码」
- **描述**: public async Task Post(CreateBulletinBody body)
- **源码位置**: `API/Controllers/ToolsManagement/BulletinController.cs:32`
- **Handler**: `BulletinController.Post`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| body | CreateBulletinBody | 是 | 请求体, 包含Bulletin创建数据 |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO. |


### 11.2. API-002 Get (GET `/api/tools/bulletin/agreement`)
- **认证**: 见源码注解 (`[Authorize]` / 等价装饰器); AST 未解析时标注「见代码」
- **描述**: public async Task Get(string alias)
- **源码位置**: `API/Controllers/ToolsManagement/BulletinController.cs:45`
- **Handler**: `BulletinController.Get`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| alias | string | 是 | Bulletin别名 |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO. |


### 11.3. API-003 GetBulletins (GET `/api/tools/bulletin/bulletins`)
- **认证**: 见源码注解 (`[Authorize]` / 等价装饰器); AST 未解析时标注「见代码」
- **描述**: public async Task GetBulletins(BulletinType? type, bool isCarousel = false, int page = AgentInsightConst.DefaultPage, int pageSize = AgentInsightConst.DefaultPageSize)
- **源码位置**: `API/Controllers/ToolsManagement/BulletinController.cs:64`
- **Handler**: `BulletinController.GetBulletins`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| type | BulletinType? | 否 | Bulletin类型 |
| isCarousel | bool | 否 | 是否轮播, 默认 false |
| page | int | 否 | 页码, 默认 AgentInsightConst.DefaultPage |
| pageSize | int | 否 | 每页条数, 默认 AgentInsightConst.DefaultPageSize |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO. |


### 11.4. API-004 GetBackendBulletins (GET `/api/tools/bulletin/backend`)
- **认证**: 见源码注解 (`[Authorize]` / 等价装饰器); AST 未解析时标注「见代码」
- **描述**: public async Task GetBackendBulletins(BulletinType? type, BulletinStatus? status, int page = AgentInsightConst.DefaultPage, int pageSize = AgentInsightConst.DefaultPageSize)
- **源码位置**: `API/Controllers/ToolsManagement/BulletinController.cs:82`
- **Handler**: `BulletinController.GetBackendBulletins`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| type | BulletinType? | 否 | Bulletin类型 |
| status | BulletinStatus? | 否 | Bulletin状态 |
| page | int | 否 | 页码, 默认 AgentInsightConst.DefaultPage |
| pageSize | int | 否 | 每页条数, 默认 AgentInsightConst.DefaultPageSize |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO. |


### 11.5. API-005 ApproveBulletin (POST `/api/tools/bulletin/approve`)
- **认证**: 见源码注解 (`[Authorize]` / 等价装饰器); AST 未解析时标注「见代码」
- **描述**: public async Task ApproveBulletin(string ids)
- **源码位置**: `API/Controllers/ToolsManagement/BulletinController.cs:96`
- **Handler**: `BulletinController.ApproveBulletin`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| ids | string | 是 | Bulletin ID 列表, 多个 ID 以逗号分隔 |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO. |


### 11.6. API-006 ReviseBulletin (POST `/api/tools/bulletin/revision`)
- **认证**: 见源码注解 (`[Authorize]` / 等价装饰器); AST 未解析时标注「见代码」
- **描述**: public async Task ReviseBulletin(string ids)
- **源码位置**: `API/Controllers/ToolsManagement/BulletinController.cs:110`
- **Handler**: `BulletinController.ReviseBulletin`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| ids | string | 是 | Bulletin ID 列表, 多个 ID 以逗号分隔 |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO. |


### 11.7. API-007 CloseBulletin (POST `/api/tools/bulletin/close`)
- **认证**: 见源码注解 (`[Authorize]` / 等价装饰器); AST 未解析时标注「见代码」
- **描述**: public async Task CloseBulletin(string ids)
- **源码位置**: `API/Controllers/ToolsManagement/BulletinController.cs:124`
- **Handler**: `BulletinController.CloseBulletin`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| ids | string | 是 | Bulletin ID 列表, 多个 ID 以逗号分隔 |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO. |

---

## 12. HealthController 接口


本章共覆盖 1 个 HTTP 接口 (AST 确定性卡片, 未经 LLM 改写).


### 12.1. API-001 Get (GET `/api/tools/health`)
- **认证**: 见源码注解 (`[Authorize]` / 等价装饰器); AST 未解析时标注「见代码」
- **描述**: public Get()
- **源码位置**: `API/Controllers/ToolsManagement/HealthController.cs:20`
- **Handler**: `HealthController.Get`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| — | — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `UsageTracking = 2` | — | 来自 AST 枚举清单 |
| `ExceptionCodes` 枚举相关成员 | — | 来自 AST 枚举清单, 具体成员及数值以 `Models/Common/Enums/ExceptionCodes.cs` 为准 |

---

## 13. WeChatController 接口


本章共覆盖 2 个 HTTP 接口 (AST 确定性卡片, 未经 LLM 改写).


### 13.1. API-001 Get (GET `/api/tools/wechat`)
- **认证**: 见源码注解 (`[Authorize]` / 等价装饰器); AST 未解析时标注「见代码」
- **描述**: public async Task Get(string signature, string timestamp, string nonce, string echostr)
- **源码位置**: `API/Controllers/ToolsManagement/WeChat/WeChatController.cs:36`
- **Handler**: `WeChatController.Get`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| — | — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `UsageTracking = 2` | — | 来自 AST 枚举清单 |


### 13.2. API-002 Post (POST `/api/tools/wechat`)
- **认证**: 见源码注解 (`[Authorize]` / 等价装饰器); AST 未解析时标注「见代码」
- **描述**: public async Task Post(string signature, string timestamp, string nonce, string? openid, WeChatMessage body)
- **源码位置**: `API/Controllers/ToolsManagement/WeChat/WeChatController.cs:68`
- **Handler**: `WeChatController.Post`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| — | — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `UsageTracking = 2` | — | 来自 AST 枚举清单 |

---

## 14. AlertController 接口


本章共覆盖 7 个 HTTP 接口 (AST 确定性卡片, 未经 LLM 改写).


### 14.1. API-001 GetConfig (GET `/api/alert/config`)
- **认证**: 见源码注解 (`[Authorize]` / 等价装饰器); AST 未解析时标注「见代码」
- **描述**: public GetConfig()
- **源码位置**: `API/Controllers/UserManagement/AlertController.cs:30`
- **Handler**: `AlertController.GetConfig`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| — | — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| — | — | 当前接口未返回错误码; 若存在异常场景, 错误码定义见 `ExceptionCodes` 枚举 (`Models/Common/Enums/ExceptionCodes.cs:6`). |


### 14.2. API-002 Get (GET `/api/alert`)
- **认证**: 见源码注解 (`[Authorize]` / 等价装饰器); AST 未解析时标注「见代码」
- **描述**: public async Task Get(string? orgId, string? projectId)
- **源码位置**: `API/Controllers/UserManagement/AlertController.cs:47`
- **Handler**: `AlertController.Get`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| — | — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| — | — | 当前接口未返回错误码; 若存在异常场景, 错误码定义见 `ExceptionCodes` 枚举 (`Models/Common/Enums/ExceptionCodes.cs:6`). |


### 14.3. API-003 Create (POST `/api/alert`)
- **认证**: 见源码注解 (`[Authorize]` / 等价装饰器); AST 未解析时标注「见代码」
- **描述**: public async Task Create(CreateAlertBody body)
- **源码位置**: `API/Controllers/UserManagement/AlertController.cs:61`
- **Handler**: `AlertController.Create`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| — | — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| — | — | 当前接口未返回错误码; 若存在异常场景, 错误码定义见 `ExceptionCodes` 枚举 (`Models/Common/Enums/ExceptionCodes.cs:6`). |


### 14.4. API-004 Update (POST `/api/alert/update`)
- **认证**: 见源码注解 (`[Authorize]` / 等价装饰器); AST 未解析时标注「见代码」
- **描述**: public async Task Update(UpdateAlertBody body)
- **源码位置**: `API/Controllers/UserManagement/AlertController.cs:75`
- **Handler**: `AlertController.Update`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| — | — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| — | — | 当前接口未返回错误码; 若存在异常场景, 错误码定义见 `ExceptionCodes` 枚举 (`Models/Common/Enums/ExceptionCodes.cs:6`). |


### 14.5. API-005 Delete (POST `/api/alert/delete`)
- **认证**: 见源码注解 (`[Authorize]` / 等价装饰器); AST 未解析时标注「见代码」
- **描述**: public async Task Delete(string alertIds)
- **源码位置**: `API/Controllers/UserManagement/AlertController.cs:90`
- **Handler**: `AlertController.Delete`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| — | — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| — | — | 当前接口未返回错误码; 若存在异常场景, 错误码定义见 `ExceptionCodes` 枚举 (`Models/Common/Enums/ExceptionCodes.cs:6`). |


### 14.6. API-006 ReadRecords (POST `/api/alert/record/read`)
- **认证**: 见源码注解 (`[Authorize]` / 等价装饰器); AST 未解析时标注「见代码」
- **描述**: public async Task ReadRecords(string recordIds)
- **源码位置**: `API/Controllers/UserManagement/AlertController.cs:108`
- **Handler**: `AlertController.ReadRecords`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| — | — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| — | — | 当前接口未返回错误码; 若存在异常场景, 错误码定义见 `ExceptionCodes` 枚举 (`Models/Common/Enums/ExceptionCodes.cs:6`). |


### 14.7. API-007 GetRecords (GET `/api/alert/record`)
- **认证**: 见源码注解 (`[Authorize]` / 等价装饰器); AST 未解析时标注「见代码」
- **描述**: public async Task GetRecords(string? orgId, string? projectId, string? alertId, AlertRecordState? state = AlertRecordState.Active)
- **源码位置**: `API/Controllers/UserManagement/AlertController.cs:128`
- **Handler**: `AlertController.GetRecords`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| — | — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| — | — | 当前接口未返回错误码; 若存在异常场景, 错误码定义见 `ExceptionCodes` 枚举 (`Models/Common/Enums/ExceptionCodes.cs:6`). |

---

## 15. CaptchaController 接口


本章共覆盖 2 个 HTTP 接口 (AST 确定性卡片, 未经 LLM 改写).


### 15.1. API-001 Get (GET `/api/captcha`)
- **认证**: 见源码注解 (`[Authorize]` / 等价装饰器); AST 未解析时标注「见代码」
- **描述**: public Get(string mobile)
- **源码位置**: `API/Controllers/UserManagement/CaptchaController.cs:29`
- **Handler**: `CaptchaController.Get`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| — | — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `UsageTracking = 2` | — | 来自 AST 枚举清单 |
| `ExistedMobile = 100003` | — | 来自 AST 枚举清单 |
| `CreateUserFailed = 100004` | — | 来自 AST 枚举清单 |
| `InvalidUser = 100005` | — | 来自 AST 枚举清单 |
| `EmptyMobile = 100009` | — | 来自 AST 枚举清单 |


### 15.2. API-002 GetSMSCaptcha (GET `/api/captcha/sms`)
- **认证**: 见源码注解 (`[Authorize]` / 等价装饰器); AST 未解析时标注「见代码」
- **描述**: public async Task GetSMSCaptcha(string phone)
- **源码位置**: `API/Controllers/UserManagement/CaptchaController.cs:43`
- **Handler**: `CaptchaController.GetSMSCaptcha`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| — | — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `UsageTracking = 2` | — | 来自 AST 枚举清单 |
| `ExistedMobile = 100003` | — | 来自 AST 枚举清单 |
| `CreateUserFailed = 100004` | — | 来自 AST 枚举清单 |
| `InvalidUser = 100005` | — | 来自 AST 枚举清单 |
| `EmptyMobile = 100009` | — | 来自 AST 枚举清单 |

---

## 16. OrganizationController 接口


本章共覆盖 4 个 HTTP 接口 (AST 确定性卡片, 未经 LLM 改写).


### 16.1. API-001 Post (POST `/api/user/organization`)
- **认证**: 见源码注解 (`[Authorize]` / 等价装饰器); AST 未解析时标注「见代码」
- **描述**: public async Task Post(CreateOrganizationBody body)
- **源码位置**: `API/Controllers/UserManagement/OrganizationController.cs:28`
- **Handler**: `OrganizationController.Post`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| — | — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO. |

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


### 16.2. API-002 Get (GET `/api/user/organization`)
- **认证**: 见源码注解 (`[Authorize]` / 等价装饰器); AST 未解析时标注「见代码」
- **描述**: public async Task Get(string? orgId)
- **源码位置**: `API/Controllers/UserManagement/OrganizationController.cs:42`
- **Handler**: `OrganizationController.Get`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| — | — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `UsageTracking = 2` | — | 来自 AST 枚举清单 |
| `## QueueType [Entities/Common/Enums/QueueEnum.cs:3]` | — | 来自 AST 枚举清单 |
| `Audit = 0` | — | 来自 AST 枚举清单 |
| `ExceptionRecord = 1` | — | 来自 AST 枚举清单 |
| `PerformanceRecord = 3` | — | 来自 AST 枚举清单 |
| `## AgentInsightSettingType [Models/Common/Enums/AgentInsightEnum.cs:3]` | — | 来自 AST 枚举清单 |
| `WeChat = 1` | — | 来自 AST 枚举清单 |
| `Alipay = 2` | — | 来自 AST 枚举清单 |


### 16.3. API-003 Update (POST `/api/user/organization/update`)
- **认证**: 见源码注解 (`[Authorize]` / 等价装饰器); AST 未解析时标注「见代码」
- **描述**: public async Task Update(UpdateOrganizationBody body)
- **源码位置**: `API/Controllers/UserManagement/OrganizationController.cs:56`
- **Handler**: `OrganizationController.Update`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| — | — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `Update` | — | 来自 AST 枚举清单 |
| `## AuditAction [Models/Common/Enums/AuditEnum.cs:3]` | — | 来自 AST 枚举清单 |
| `Create` | — | 来自 AST 枚举清单 |
| `Delete` | — | 来自 AST 枚举清单 |
| `Login` | — | 来自 AST 枚举清单 |
| `Logout` | — | 来自 AST 枚举清单 |
| `Reset` | — | 来自 AST 枚举清单 |
| `Bind` | — | 来自 AST 枚举清单 |
| `UnBind` | — | 来自 AST 枚举清单 |
| `Place` | — | 来自 AST 枚举清单 |
| `Query` | — | 来自 AST 枚举清单 |
| `Notify` | — | 来自 AST 枚举清单 |


### 16.4. API-004 Delete (POST `/api/user/organization/delete`)
- **认证**: 见源码注解 (`[Authorize]` / 等价装饰器); AST 未解析时标注「见代码」
- **描述**: public async Task Delete(string orgIds)
- **源码位置**: `API/Controllers/UserManagement/OrganizationController.cs:71`
- **Handler**: `OrganizationController.Delete`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| — | — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `Delete` | — | 来自 AST 枚举清单 |
| `## AuditResourceType [Models/Common/Enums/AuditEnum.cs:18]` | — | 来自 AST 枚举清单 |
| `User` | — | 来自 AST 枚举清单 |
| `Organization` | — | 来自 AST 枚举清单 |
| `Project` | — | 来自 AST 枚举清单 |
| `Alert` | — | 来自 AST 枚举清单 |
| `ApiKey` | — | 来自 AST 枚举清单 |
| `Invitation` | — | 来自 AST 枚举清单 |
| `Order` | — | 来自 AST 枚举清单 |
| `WeChat` | — | 来自 AST 枚举清单 |
| `OrgPrivilege` | — | 来自 AST 枚举清单 |

---

## 17. ProjectController 接口

```markdown
### 17.1. API-001 Create (POST `/api/user/project`)
- **认证**: 见源码注解 (`[Authorize]` / 等价装饰器); AST 未解析时标注「见代码」
- **描述**: public async Task<IActionResult> Create([FromBody] CreateProjectBody body)
- **源码位置**: `API/Controllers/UserManagement/ProjectController.cs:31`
- **Handler**: `ProjectController.Create`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| — | — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `Create` | — | 来自 AST 枚举清单 |
| `CreateUserFailed = 100004` | — | 来自 AST 枚举清单 |
| `CreateOrganizationFailed = 100026` | — | 来自 AST 枚举清单 |
| `CreateProjectFailed = 100032` | — | 来自 AST 枚举清单 |
| `CreateApiKeyFailed = 130004` | — | 来自 AST 枚举清单 |
| `CreateAlertFailed = 140004` | — | 来自 AST 枚举清单 |
| `CreateInviteFailed = 160001` | — | 来自 AST 枚举清单 |
| `Create = 2` | — | 来自 AST 枚举清单 |
| `Created = 1` | — | 来自 AST 枚举清单 |
| `Created = 1` | — | 来自 AST 枚举清单 |


### 17.2. API-002 Get (GET `/api/user/project`)
- **认证**: 见源码注解 (`[Authorize]` / 等价装饰器); AST 未解析时标注「见代码」
- **描述**: public async Task<IActionResult> Get(string orgId, string? projectId)
- **源码位置**: `API/Controllers/UserManagement/ProjectController.cs:46`
- **Handler**: `ProjectController.Get`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| — | — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `UsageTracking = 2` | — | 来自 AST 枚举清单 |
| `GetWeChatTokenFailed = 620003` | — | 来自 AST 枚举清单 |
| `GetWeChatBasicUserInfoFailed = 620004` | — | 来自 AST 枚举清单 |
| `GetPayCertificateFailed = 620005` | — | 来自 AST 枚举清单 |
| `InvalidWeChatMessageType = 620017` | — | 来自 AST 枚举清单 |
| `WeChatMessageType` | — | 来自 AST 枚举清单 |


### 17.3. API-003 Update (POST `/api/user/project/update`)
- **认证**: 见源码注解 (`[Authorize]` / 等价装饰器); AST 未解析时标注「见代码」
- **描述**: public async Task<IActionResult> Update([FromBody] UpdateProjectBody body)
- **源码位置**: `API/Controllers/UserManagement/ProjectController.cs:60`
- **Handler**: `ProjectController.Update`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| — | — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `Update` | — | 来自 AST 枚举清单 |
| `UpdateApiKeyFailed = 130005` | — | 来自 AST 枚举清单 |
| `UpdateAlertFailed = 140005` | — | 来自 AST 枚举清单 |
| `UpdateAgentRateFailed = 810026` | — | 来自 AST 枚举清单 |
| `OrderStateUpdateFailed = 150020` | — | 来自 AST 枚举清单 |
| `UpdateOrganizationFailed = 160002` | — | 来自 AST 枚举清单 |


### 17.4. API-004 Delete (POST `/api/user/project/delete`)
- **认证**: 见源码注解 (`[Authorize]` / 等价装饰器); AST 未解析时标注「见代码」
- **描述**: public async Task<IActionResult> Delete(string projectIds)
- **源码位置**: `API/Controllers/UserManagement/ProjectController.cs:75`
- **Handler**: `ProjectController.Delete`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| — | — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `Delete` | — | 来自 AST 枚举清单 |
| `DeleteUserFailed = 100028` | — | 来自 AST 枚举清单 |
| `DeleteProjectFailed = 100033` | — | 来自 AST 枚举清单 |
| `DeleteApiKeyFailed = 130006` | — | 来自 AST 枚举清单 |
| `DeleteAlertFailed = 140006` | — | 来自 AST 枚举清单 |
| `DeleteInviteFailed = 160003` | — | 来自 AST 枚举清单 |
```

---

## 18. UserConfigController 接口


本章共覆盖 4 个 HTTP 接口 (AST 确定性卡片, 未经 LLM 改写).


### 18.1. API-001 Get (GET `/api/user/config`)
- **认证**: 见源码注解 (`[Authorize]` / 等价装饰器); AST 未解析时标注「见代码」
- **描述**: public async Task Get(string? orgId, string? projectId, string? type)
- **源码位置**: `API/Controllers/UserManagement/UserConfigController.cs:31`
- **Handler**: `UserConfigController.Get`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| — | — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `UsageTracking = 2` | — | 来自 AST 枚举清单 |
| `WeChat = 1` | — | 来自 AST 枚举清单 |
| `Alipay = 2` | — | 来自 AST 枚举清单 |
| `Create` | — | 来自 AST 枚举清单 |
| `Update` | — | 来自 AST 枚举清单 |
| `Delete` | — | 来自 AST 枚举清单 |


### 18.2. API-002 Post (POST `/api/user/config`)
- **认证**: 见源码注解 (`[Authorize]` / 等价装饰器); AST 未解析时标注「见代码」
- **描述**: public async Task Post(CreateUserConfigBody body)
- **源码位置**: `API/Controllers/UserManagement/UserConfigController.cs:44`
- **Handler**: `UserConfigController.Post`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| — | — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `Create` | — | 来自 AST 枚举清单 |
| `User` | — | 来自 AST 枚举清单 |
| `Organization` | — | 来自 AST 枚举清单 |
| `Project` | — | 来自 AST 枚举清单 |
| `Alert` | — | 来自 AST 枚举清单 |
| `ApiKey` | — | 来自 AST 枚举清单 |


### 18.3. API-003 Update (POST `/api/user/config/update`)
- **认证**: 见源码注解 (`[Authorize]` / 等价装饰器); AST 未解析时标注「见代码」
- **描述**: public async Task Update(UpdateUserConfigBody body)
- **源码位置**: `API/Controllers/UserManagement/UserConfigController.cs:57`
- **Handler**: `UserConfigController.Update`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| — | — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `Update` | — | 来自 AST 枚举清单 |
| `User` | — | 来自 AST 枚举清单 |
| `Organization` | — | 来自 AST 枚举清单 |
| `Project` | — | 来自 AST 枚举清单 |
| `Alert` | — | 来自 AST 枚举清单 |
| `ApiKey` | — | 来自 AST 枚举清单 |


### 18.4. API-004 Delete (GET `/api/user/config/delete`)
- **认证**: 见源码注解 (`[Authorize]` / 等价装饰器); AST 未解析时标注「见代码」
- **描述**: public async Task Delete(string id)
- **源码位置**: `API/Controllers/UserManagement/UserConfigController.cs:71`
- **Handler**: `UserConfigController.Delete`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| — | — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO. |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO. |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `Delete` | — | 来自 AST 枚举清单 |
| `User` | — | 来自 AST 枚举清单 |
| `Organization` | — | 来自 AST 枚举清单 |
| `Project` | — | 来自 AST 枚举清单 |
| `Alert` | — | 来自 AST 枚举清单 |
| `ApiKey` | — | 来自 AST 枚举清单 |

---

## 19. UserController 接口

本章共覆盖 17 个 HTTP 接口 (AST 确定性卡片, 未经 LLM 改写)。

### 19.1. API-001 Get (GET `/api/user`)
- **认证**: 见源码注解 (`[Authorize]` / 等价装饰器); AST 未解析时标注「见代码」
- **描述**: public async Task Get()
- **源码位置**: `API/Controllers/UserManagement/UserController.cs:29`
- **Handler**: `UserController.Get`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| — | — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO。 |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO。 |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `UsageTracking = 2` | — | 来自 AST 枚举清单 |
| `ExceptionCodes` 枚举 | — | 来自 AST 枚举清单; 具体常量见源码 |

### 19.2. API-002 Create (POST `/api/user`)
- **认证**: 见源码注解 (`[Authorize]` / 等价装饰器); AST 未解析时标注「见代码」
- **描述**: public async Task Create(MiniUserBody body)
- **源码位置**: `API/Controllers/UserManagement/UserController.cs:43`
- **Handler**: `UserController.Create`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| — | — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO。 |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO。 |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `Create` | — | 来自 AST 枚举清单 |
| `CreateUserFailed = 100004` | — | 来自 AST 枚举清单 |
| `ExceptionCodes` 枚举 | — | 来自 AST 枚举清单; 具体常量见源码 |

### 19.3. API-003 Update (POST `/api/user/update`)
- **认证**: 见源码注解 (`[Authorize]` / 等价装饰器); AST 未解析时标注「见代码」
- **描述**: public async Task Update(MiniUserBody body)
- **源码位置**: `API/Controllers/UserManagement/UserController.cs:58`
- **Handler**: `UserController.Update`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| — | — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO。 |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO。 |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `Update` | — | 来自 AST 枚举清单 |
| `ExceptionCodes` 枚举 | — | 来自 AST 枚举清单; 具体常量见源码 |

### 19.4. API-004 Login (POST `/api/user/login`)
- **认证**: 见源码注解 (`[Authorize]` / 等价装饰器); AST 未解析时标注「见代码」
- **描述**: public async Task Login(MiniUserBody? body)
- **源码位置**: `API/Controllers/UserManagement/UserController.cs:73`
- **Handler**: `UserController.Login`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| — | — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO。 |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO。 |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `Login` | — | 来自 AST 枚举清单 |
| `AuditAction` 枚举 | — | 来自 AST 枚举清单; 具体常量见源码 |

### 19.5. API-005 Logout (POST `/api/user/logout`)
- **认证**: 见源码注解 (`[Authorize]` / 等价装饰器); AST 未解析时标注「见代码」
- **描述**: public async Task Logout()
- **源码位置**: `API/Controllers/UserManagement/UserController.cs:88`
- **Handler**: `UserController.Logout`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| — | — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO。 |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO。 |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `Logout` | — | 来自 AST 枚举清单 |

### 19.6. API-006 ResetPassword (POST `/api/user/resetpassword`)
- **认证**: 见源码注解 (`[Authorize]` / 等价装饰器); AST 未解析时标注「见代码」
- **描述**: public async Task ResetPassword(ResetPasswordBody body)
- **源码位置**: `API/Controllers/UserManagement/UserController.cs:102`
- **Handler**: `UserController.ResetPassword`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| — | — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO。 |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO。 |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `ExceptionCodes` 枚举 | — | 来自 AST 枚举清单; 具体常量见源码 |

### 19.7. API-007 Bind (POST `/api/user/bind/wechat`)
- **认证**: 见源码注解 (`[Authorize]` / 等价装饰器); AST 未解析时标注「见代码」
- **描述**: public async Task Bind(MiniUserBody body)
- **源码位置**: `API/Controllers/UserManagement/UserController.cs:117`
- **Handler**: `UserController.Bind`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| — | — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO。 |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO。 |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `Bind` | — | 来自 AST 枚举清单 |
| `AuditAction` 枚举 | — | 来自 AST 枚举清单; 具体常量见源码 |
| `ExceptionCodes` 枚举 | — | 来自 AST 枚举清单; 具体常量见源码 |

### 19.8. API-008 UnBind (GET `/api/user/unbind/wechat`)
- **认证**: 见源码注解 (`[Authorize]` / 等价装饰器); AST 未解析时标注「见代码」
- **描述**: public async Task UnBind()
- **源码位置**: `API/Controllers/UserManagement/UserController.cs:132`
- **Handler**: `UserController.UnBind`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| — | — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO。 |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO。 |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `UnBind` | — | 来自 AST 枚举清单 |

### 19.9. API-009 AssignRole (POST `/api/user/role`)
- **认证**: 见源码注解 (`[Authorize]` / 等价装饰器); AST 未解析时标注「见代码」
- **描述**: public async Task AssignRole(AssignRoleBody body)
- **源码位置**: `API/Controllers/UserManagement/UserController.cs:147`
- **Handler**: `UserController.AssignRole`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| — | — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO。 |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO。 |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `RouteType` 枚举 | — | 来自 AST 枚举清单; 具体常量见源码 |
| `PublicApi = 2` | — | 来自 AST 枚举清单 |

### 19.10. API-010 Invite (POST `/api/user/invite`)
- **认证**: 见源码注解 (`[Authorize]` / 等价装饰器); AST 未解析时标注「见代码」
- **描述**: public async Task Invite(CreateMembershipInvitationBody body)
- **源码位置**: `API/Controllers/UserManagement/UserController.cs:162`
- **Handler**: `UserController.Invite`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| — | — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO。 |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO。 |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `ExceptionCodes` 枚举 | — | 来自 AST 枚举清单; 具体常量见源码 |

### 19.11. API-011 Get (GET `/api/user/invitation`)
- **认证**: 见源码注解 (`[Authorize]` / 等价装饰器); AST 未解析时标注「见代码」
- **描述**: 详见源码方法签名
- **源码位置**: `API/Controllers/UserManagement/UserController.cs`
- **Handler**: `UserController.Get`

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| — | — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO。 |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| — | — | 详见源码方法签名; 字段以 AST 可提取信息为准, 未推断编造 DTO。 |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `ExceptionCodes` 枚举 | — | 来自 AST 枚举清单; 具体常量见源码 |

---

## 20. LiteralRoute 接口


本章共覆盖 2 个 HTTP 接口（AST 确定性卡片，未经 LLM 改写）。


### 20.1. API-001 获取公开路由信息（GET `/api/public`）
- **认证**: 见源码注解（`[Authorize]` / 等价装饰器）；AST 未解析时标注「见代码」
- **描述**: 源码字面量路由
- **源码位置**: `API/System/Handlers/AgentInsightTransformLogic.cs`（待确认具体行号）
- **Handler**: `AgentInsightTransformLogic`（待确认具体方法名）

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| — | — | — | 详见源码方法签名；字段以 AST 可提取信息为准，未推断编造 DTO。 |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| — | — | 详见源码方法签名；字段以 AST 可提取信息为准，未推断编造 DTO。 |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `# 枚举定义清单（AST 结构感知扫描，错误码必须引用以下真实常量名和数值）` | — | 来自 AST 枚举清单 |
| `# 共 43 个枚举定义` | — | 来自 AST 枚举清单 |
| `## ExceptionCodes [Models/Common/Enums/ExceptionCodes.cs:6]` | — | 来自 AST 枚举清单 |
| `InvalidParameter = 1001` | — | 来自 AST 枚举清单 |
| `Unauthorized = 1002` | — | 来自 AST 枚举清单 |
| `NotFound = 1003` | — | 来自 AST 枚举清单 |
| `InternalServerError = 1004` | — | 来自 AST 枚举清单 |


### 20.2. API-002 获取测试路由信息（GET `/api/test`）
- **认证**: 见源码注解（`[Authorize]` / 等价装饰器）；AST 未解析时标注「见代码」
- **描述**: 源码字面量路由
- **源码位置**: `API/System/Handlers/AgentInsightTransformLogic.cs`（待确认具体行号）
- **Handler**: `AgentInsightTransformLogic`（待确认具体方法名）

**请求参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| — | — | — | 详见源码方法签名；字段以 AST 可提取信息为准，未推断编造 DTO。 |

**响应格式**

| 字段 | 类型 | 说明 |
|------|------|------|
| — | — | 详见源码方法签名；字段以 AST 可提取信息为准，未推断编造 DTO。 |

**错误码**

| errorCode | message | 说明 |
|-----------|---------|------|
| `# 枚举定义清单（AST 结构感知扫描，错误码必须引用以下真实常量名和数值）` | — | 来自 AST 枚举清单 |
| `# 共 43 个枚举定义` | — | 来自 AST 枚举清单 |
| `## ExceptionCodes [Models/Common/Enums/ExceptionCodes.cs:6]` | — | 来自 AST 枚举清单 |
| `InvalidParameter = 1001` | — | 来自 AST 枚举清单 |
| `Unauthorized = 1002` | — | 来自 AST 枚举清单 |
| `NotFound = 1003` | — | 来自 AST 枚举清单 |
| `InternalServerError = 1004` | — | 来自 AST 枚举清单 |

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

## 1. 引言

AgentInsightService 是面向 AI 应用可Observation性与运营管理场景的后端服务平台，提供 RESTful API，覆盖用户管理、Org/项目管理、数据指标查询、Alert管理、Payment管理、Agent Config、工具管理（Bulletin、健康检查、微信消息）等模块。API 基于 Furion 框架构建，路由遵循 `/api/{module}/{resource}` 模式，认证主要依赖 JWT（HS256）和 API Key 两种方式。数据查询接口（如 Trace、Observation）支持过滤、排序、分页，Payment回调接口（微信/Payment宝）为公开接口，无需认证，健康检查接口 `/api/tools/health` 同样为公开接口。

### 1.1. 编写目的

本文档为 AgentInsightService 的 API 使用者提供完整的接口参考与集成指南，目标读者包括 AI 应用开发者、平台集成工程师及运维人员。AI 应用开发者可通过本文档了解如何将 AgentInsightService 的 Trace 数据采集、指标查询与Alert通知能力集成至其 AI 应用；平台集成工程师可依据本文档完成组织、Project、用户及Payment等管理能力的对接；运维人员可参考健康检查与Alert相关接口保障服务稳定运行。

本文档详细描述了 AgentInsightService 全部 RESTful API，共 76 个 HTTP 端点，分布在 17 个 Controller 中。每个接口均包含请求参数、响应格式、错误码及调用示例，帮助读者在不阅读源码的情况下完成系统集成。文档同时说明了认证授权方式、通用约定及版本兼容性策略，确保集成过程的规范性与一致性。

### 1.2. 适用范围

本文档适用于 AgentInsightService 平台的所有 API 使用者，覆盖以下典型应用场景：

| 场景 | 适用角色 | 涉及模块 |
|------|---------|---------|
| AI 应用可Observation性数据接入 | AI 应用开发者 | 数据指标、Agent 管理 |
| 组织与项目PrivilegeConfig | 平台集成工程师 | 用户管理、Org/项目管理 |
| Alert规则Config与通知接收 | AI 应用开发者、运维人员 | Alert管理 |
| Payment与产品订阅管理 | 平台集成工程师 | Payment管理、产品管理 |
| 服务健康状态监控 | 运维人员 | 工具管理 |

本文档覆盖的接口范围包括但不限于：用户认证与授权、组织与项目管理、Trace/Observation 数据查询、Alert规则与记录管理、Agent Session与Config管理、Payment回调与订单处理、产品与时长管理、模型定义管理、Captcha发送及健康检查等。数据查询接口（如 Trace、Observation）支持过滤、排序、分页，满足不同规模数据下的查询需求 [API/Controllers/DataManagement/MetricsController.cs]。

### 1.3. 术语与缩略语

本文档涉及以下关键术语与缩略语，部分术语保留英文原文以确保准确性：

| 术语 | 说明 |
|------|------|
| AgentInsightService | 本文档所描述的后端服务平台名称，提供完整的 RESTful API 能力 |
| AgentInsight | AgentInsightService 的品牌名称，用于产品标识 |
| API | Application Programming Interface，应用程序编程接口 |
| JWT | JSON Web Token，基于 HS256 算法的身份认证Token |
| API Key | 用于 API 访问认证的密钥，与 JWT 并列为两种主要认证方式 |
| Trace | 一次完整的请求链路Trace记录，包含从请求发起到响应的全过程信息 |
| Observation | Trace 中的单个Observation单元，记录某一阶段或操作的详细信息 |
| Alert | Alert规则或Alert记录，用于监控指标异常并通知相关人员 |
| Controller | Controller，Furion 框架中处理 HTTP 请求的入口类 |
| Handler | Handler，承载业务逻辑的实现类，被 Controller 调用 |
| Base URL | 接口请求的基础地址前缀 |
| errorCode | 接口响应中的错误码字段，0 表示成功，非 0 表示具体错误类型 |

### 1.4. 参考文档

本文档的编写基于以下参考来源：

| 参考项 | 说明 |
|--------|------|
| AgentInsightService 源码仓库 | API/Controllers 目录下的 Controller 定义（含路由、参数、响应类型） |
| AgentInsightService 源码仓库 | API/Handlers 目录下的业务逻辑实现（含数据查询、过滤、分页逻辑） |
| Config文件 | appsettings.json 等Config文件中定义的连接字符串与功能开关 |
| 枚举定义 | Models/Common/Enums 与 Entities 中定义的错误码与状态枚举 |

Config文件 | appsettings.json 等Config文件中定义的连接字符串与功能开关 |
| 枚举定义 | Models/Common/Enums 与 Entities 中定义的错误码与状态枚举 |

接口定义与参数说明均从源码中提取，确保与实现保持一致。例如，Agent Session管理接口定义于 `API/Controllers/AgentManagement/AgentSessionController.cs`，数据指标查询接口定义于 `API/Controllers/DataManagement/MetricsController.cs`，产品管理接口定义于 `API/Controllers/ProductManagement/ProductController.cs`。

### 1.5. 版本历史

以下版本历史记录 AgentInsightService API 的变更与兼容性说明：

| 版本 | 日期 | 变更说明 | 兼容性 |
|------|------|---------|--------|
| v1.0 | 初始版本 | 首个正式发布版本，包含用户管理、数据指标查询、Alert管理等核心模块 | 基线版本 |
| v1.1 | 迭代更新 | 新增 Agent Session管理、Agent Config管理、Agent 报表模板管理接口 | 向后兼容 |
| v1.2 | 迭代更新 | 新增模型定义管理接口，支持模型价格与分词器Config | 向后兼容 |
| v1.3 | 迭代更新 | 新增产品管理与产品时长接口，支持订阅计费 | 向后兼容 |

版本兼容性说明：所有新增接口均遵循 `/api/{module}/{resource}` 路由模式，不修改既有接口的请求与响应格式。数据查询接口的分页参数（page、page_size）在所有版本中保持一致，默认页码为 1，默认每页数量为 10，可通过 `AgentInsightConst.DefaultPage` 与 `AgentInsightConst.DefaultPageSize` 常量确认 [API/Controllers/AgentManagement/AgentSessionController.cs]。

---

## 2. API 概览与通用约定

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
| 15 | POST | `/api/payment/notify/wechat_notify` | WeChatNotify | NotifyController |
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

erController.cs:73-L85]。登录响应头中包含 `access-token`，响应体返回用户信息（含 `token`、`refresh_token`、`session_id` 等字段）。

JWT 过期时间由 `.Expir` 控制。Token 过期后，客户端需重新登录获取新 Token。系统在 Token 校验失败时返回错误码 `=100000`，提示"登录已过期，请重新登录" [API/Resources/Text.zh-CN.json]。

#### 3.1.1. API Key 认证

API Key 面向程序化访问场景，适用于自动化脚本、服务间调用等无法进行交互式登录的场景。用户通过 `POST /api/user/apikey` 接口创建 API Key [API/Controllers/UserManagement/UserController.cs:209]，创建后可调用 `GET /api/user/apikey` 查询已创建的密钥列表 [API/Controllers/UserManagement/UserController.cs:225]。

API Key 的密钥使用 **AES 加密** 存储，加密密钥Config项为 `=${}`。API Key 认证方式下，登录接口 `POST /api/user/login` 的 `logintype=5`，此时请求体可为空，需在 `Authorization` 头携带 `Basic publickey:secretkey` 格式的凭证 [API/Controllers/UserManagement/UserController.cs:73-L85]。

API Key 相关错误码包括：
- `=100031`：API 密钥不存在
- `=100032`：API 密钥创建失败
- `=100033`：API 密钥删除失败
- `=100036`：未找到对应的 API 密钥
- `=100038`：API 密钥无效

#### 3.1.2. 公开接口

以下接口为公开接口，无需任何认证即可访问：

| 接口路径 | 方法 | 说明 |
|---------|------|------|
| `/api/tools/health` | GET | 健康检查 |
| `/api/payment/notify/wechat_notify` | POST | 微信Payment回调 |
| `/api/payment/notify/alipaynotify` | POST | Payment宝Payment回调 |
| `/api/tools/wechat` | GET/POST | 微信消息接口 |

Payment回调接口在 `NotifyController` 中标注 `[]` [API/Controllers/PaymentManagement/NotifyController.cs:8-L15]，健康检查接口同样为公开接口。

### 3.2. 授权流程

AgentInsightService 采用基于 **Org（Organization）** 和 **Project（Project）** 的多租户Privilege模型，实现资源隔离与访问控制。

#### 3.2.1. 多租户Privilege模型

系统以组织为租户边界，组织下可创建多个项目。用户通过邀请或直接加入方式成为组织成员，Owner。Privilege模型的核心约束包括：

- **组织所有者** 拥有组织最高Privilege，可管理成员、项目及组织设置
- **组织成员** 的Privilege由角色决定，角色通过 `POST /api/user/role` 接口分配 [API/Controllers/UserManagement/UserController.cs:147]
- **角色分配限制**：不能授予高于自身角色的Privilege，错误码 `=100023`；组织所有者不能修改自身Privilege，错误码 `=100039`

#### 3.2.2. 访问控制流程

1. **身份认证**：请求携带 JWT 或 API Key，系统验证凭证有效性
2. **用户识别**：从 Token 中解析用户身份，获取用户 ID
3. **租户上下文解析**：根据请求中的组织 ID / Project ID 确定租户上下文
4. **Privilege校验**：校验用户对目标组织/项目的访问Privilege

Privilege不足时返回错误码 ``（Privilege不足），无权访问组织时返回 ``，无权访问项目时返回 `` [API/Resources/Text.zh-CN.json]。

#### 3.2.3. 成员邀请与角色分配

组织成员通过邀请机制加入：

| 接口路径 | 方法 | 说明 |
|---------|------|------|
| `/api/user/invite` | POST | 发送邀请 [API/Controllers/UserManagement/UserController.cs:162] |
| `/api/user/invitation` | GET | 查询邀请列表 [API/Controllers/UserManagement/UserController.cs:177] |
| `/api/user/invitation/delete` | POST | 撤销邀请 [API/Controllers/UserManagement/UserController.cs:192] |
| `/api/user/role` | POST | 分配角色 [API/Controllers/UserManagement/UserController.cs:147] |

邀请相关错误码包括：`=100024`（已是组织成员）、``（已存在待处理邀请）、``（邀请不存在或已处理）、``（邀请撤销失败）。

### 3.3. Token 管理

Token 管理覆盖 Token 的签发、过期、刷新与失效全生命周期。

#### 3.3.1. Token 签发

用户通过 `POST /api/user/login` 登录成功后，系统签发 JWT。登录方式支持多种类型（`logintype`）：

| logintype | 认证方式 | 说明 |
|-----------|---------|------|
| 1 | 密码 | 手机号/邮箱 + 密码 |
| 2 | 短信 | 手机号 + 短信Captcha |
| 3 | 微信 | 微信授权 |
| 4 | 小程序 | 小程序登录 |
| 5 | API Key | Basic 认证 |

#### 3.3.2. Token 过期

Token 过期时间由 `.Expir` Config控制。系统设置 `=5min` 作为时钟偏移容忍窗口，避免因客户端与服务器时间差异导致 Token 提前失效。

Token 过期后，受保护接口返回 `=100000`（登录已过期，请重新登录）。用户需重新登录获取新 Token。

#### 3.3.3. Token 失效（登出）

用户调用 `POST /api/user/logout` 接口主动登出，使当前 Token 失效 [API/Controllers/UserManagement/UserController.cs:88-L96]。登出后，该 Token 将无法继续访问受保护资源。

#### 3.3.4. Token 刷新

登录响应中包含 `refresh_token` 字段，用于 Token 刷新场景。当 Token 即将过期或已过期时，客户端可使用刷新Token获取新的访问Token，避免频繁重新登录。

### 3.4. API Key 管理

API Key 用于程序化访问场景，提供比 JWT 更持久的凭证机制。

#### 3.4.1. 创建 API Key

调用 `POST /api/user/apikey` 创建 API Key [API/Controllers/UserManagement/UserController.cs:209]。创建成功后，系统返回 API Key publickeysecretkey。密钥使用 AES 加密后存储，加密密钥Config项为 `=${}`。

#### 3.4.2. 查询 API Key

调用 `GET /api/user/apikey` 查询当前用户已创建的 API Key 列表 [API/Controllers/UserManagement/UserController.cs:225]。

#### 3.4.3. 使用 API Key

API Key 认证方式下，调用 `POST /api/user/login` 且 `logintype=5`，在 `Authorization` 头携带 `Basic publickey:secretkey` 进行认证 [API/Controllers/UserManagement/UserController.cs:73-L85]。

#### 3.4.4. 删除 API Key

删除 API Key 失败时返回错误码 `=100033`。API Key 删除后立即失效，使用该 Key 的请求将返回 `=100038`。

#### 3.4.5. Captcha保护

敏感操作（如注册、重置密码）需通过Captcha保护，防止自动化攻击：

| 接口路径 | 方法 | 说明 |
|---------|------|------|
| `/api/captcha` | GET | 获取图片Captcha [API/Controllers/UserManagement/CaptchaController.cs:16-L27] |
| `/api/captcha/sms` | GET | 获取短信Captcha [API/Controllers/UserManagement/CaptchaController.cs:31-L43] |

CaptchaConfig项：
- `CaptchaSetting.=5`：图片Captcha长度
- `CaptchaSetting.=6`：短信Captcha长度
- `CaptchaSetting.=300`：Captcha有效期（秒）
- `CaptchaSetting.=60`：重发间隔（秒）

Captcha相关错误码：
- `=110002`：Captcha不能为空
- `=110003`：Captcha已失效，请重新获取
- `=110004`：Captcha错误，请重新输入
- `=110000`：操作过于频繁，请稍后再获取Captcha
- `=110001`：Captcha发送失败，请稍后重试

注册接口 `POST /api/user` 标注 `[]`，但需携带 `captchacode` Captcha字段 [API/Controllers/UserManagement/UserController.cs:43-L56]。重置密码接口 `POST /api/user/resetpassword` 同样需要Captcha [API/Controllers/UserManagement/UserController.cs:102]。

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

**相关符号**

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

**相关符号**

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

**相关符号**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_

---

## 5. AgentReportController 接口

本章共覆盖 3 个 HTTP 端点 (AST 确定性卡片, 未经 LLM 改写).

### 5.1. API-001 GetTemplates (GET `/api/agent/report`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<IActionResult> GetTemplates(string? id, bool include_predefined = false, bool include_predefinedonly = false, int page = AgentInsightConst.DefaultPage, int page_size = AgentInsightConst.DefaultPageSize)
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

**相关符号**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_

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

**相关符号**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_

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

**相关符号**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_

---

## 6. AgentSessionController 接口

本章共覆盖 3 个 HTTP 端点 (AST 确定性卡片, 未经 LLM 改写).

### 6.1. API-001 Get (GET `/api/agent/session`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<IActionResult> Get(string? id, int page = AgentInsightConst.DefaultPage, int page_size = AgentInsightConst.DefaultPageSize)
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

**相关符号**

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

**相关符号**

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

**相关符号**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_

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

**相关符号**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_

### 7.2. API-002 Get (GET `/api/alert`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<IActionResult> Get(string? org_id, string? projectId)
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

**相关符号**

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

**相关符号**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_

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

**相关符号**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_

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

**相关符号**

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

**相关符号**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_

### 7.7. API-007 GetRecords (GET `/api/alert/record`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<IActionResult> GetRecords(string? org_id, string? projectId, string? alertId, AlertRecordState? state = AlertRecordState.Active)
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

**相关符号**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_

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

**相关符号**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_

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

**相关符号**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, uuid_utils-0.16.2-cp312-cp

### 8.3. API-003 GetBulletins (GET `/api/tools/bulletin/bulletins`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<IActionResult> GetBulletins(BulletinType? type, bool isCarousel = false, int page = AgentInsightConst.DefaultPage, int page_size = AgentInsightConst.DefaultPageSize)
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

**相关符号**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_

### 8.4. API-004 GetBackendBulletins (GET `/api/tools/bulletin/backend`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<IActionResult> GetBackendBulletins(BulletinType? type, BulletinStatus? status, int page = AgentInsightConst.DefaultPage, int page_size = AgentInsightConst.DefaultPageSize)
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

**相关符号**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_

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

**相关符号**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_

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

**相关符号**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_

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

**相关符号**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_

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

**相关符号**

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

**相关符号**

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

**相关符号**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, uuid_utils-0.16.2-cp312-cp

---

## 11. MetricsController 接口

本章共覆盖 4 个 HTTP 端点 (AST 确定性卡片, 未经 LLM 改写).

### 11.1. API-001 GetObservations (GET `/api/data/metrics/observations`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<IActionResult> GetObservations(string id, int page = AgentInsightConst.DefaultPage, int page_size = AgentInsightConst.DefaultPageSize)
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

**相关符号**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, uuid_utils-0.16.2-cp312-cp

### 11.2. API-002 GetScores (GET `/api/data/metrics/scores`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<IActionResult> GetScores(string id, int page = AgentInsightConst.DefaultPage, int page_size = AgentInsightConst.DefaultPageSize)
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

**相关符号**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, uuid_utils-0.16.2-cp312-cp

### 11.3. API-003 GetTraces (GET `/api/data/metrics/traces`)
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

**相关符号**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, uuid_utils-0.16.2-cp312-cp

### 11.4. API-004 GetTraces (POST `/api/data/metrics/traces`)
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

**相关符号**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, uuid_utils-0.16.2-cp312-cp

---

## 12. ModelController 接口

本章共覆盖 1 个 HTTP 端点 (AST 确定性卡片, 未经 LLM 改写).

### 12.1. API-001 Get (GET `/api/data/model`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<IActionResult> Get(string? keyword, string? project_id, bool include_predefined = false, string order_by = "-updated_at", int page = AgentInsightConst.DefaultPage, int page_size = AgentInsightConst.DefaultPageSize)
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

**相关符号**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, uuid_utils-0.16.2-cp312-cp

---

## 13. NotifyController 接口

本章共覆盖 2 个 HTTP 端点 (AST 确定性卡片, 未经 LLM 改写).

### 13.1. API-001 WeChatNotify (POST `/api/payment/notify/wechat_notify`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<IActionResult> WeChatNotify()
- **源码位置**: `API/Controllers/PaymentManagement/NotifyController.cs:29`
- **Handler**: `NotifyController.WeChatNotify`
- **HTTP**: `POST`
- **Route**: `/api/payment/notify/wechat_notify`

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

**相关符号**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, uuid_utils-0.16.2-cp312-cp

### 13.2. API-002 AlipayNotify (POST `/api/payment/notify/alipaynotify`)
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

**相关符号**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, uuid_utils-0.16.2-cp312-cp

---

## 14. OrderController 接口

本章共覆盖 4 个 HTTP 端点 (AST 确定性卡片, 未经 LLM 改写).

### 14.1. API-001 Get (GET `/api/payment/order`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<IActionResult> Get(string org_id, int page = AgentInsightConst.DefaultPage, int page_size = AgentInsightConst.DefaultPageSize)
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

**相关符号**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, uuid_utils-0.16.2-cp312-cp

### 14.2. API-002 Place (POST `/api/payment/order`)
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

**相关符号**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, uuid_utils-0.16.2-cp312-cp

### 14.3. API-003 Query (GET `/api/payment/order/query`)
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

**相关符号**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_

### 14.4. API-004 GetConversion (GET `/api/payment/order/conversion`)
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

**相关符号**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_

---

## 15. OrganizationController 接口

本章共覆盖 4 个 HTTP 端点 (AST 确定性卡片, 未经 LLM 改写).

### 15.1. API-001 Post (POST `/api/user/organization`)
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

**相关符号**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, uuid_utils-0.16.2-cp312-cp

### 15.2. API-002 Get (GET `/api/user/organization`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<IActionResult> Get(string? org_id)
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

**相关符号**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, uuid_utils-0.16.2-cp312-cp

### 15.3. API-003 Update (POST `/api/user/organization/update`)
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

**相关符号**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, uuid_utils-0.16.2-cp312-cp

### 15.4. API-004 Delete (POST `/api/user/organization/delete`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<IActionResult> Delete(string org_ids)
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

**相关符号**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, uuid_utils-0.16.2-cp312-cp

---

## 16. ProductController 接口

本章共覆盖 2 个 HTTP 端点 (AST 确定性卡片, 未经 LLM 改写).

### 16.1. API-001 Get (GET `/api/product`)
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

**相关符号**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, uuid_utils-0.16.2-cp312-cp

### 16.2. API-002 GetDuration (GET `/api/product/duration`)
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

**相关符号**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_

---

## 17. ProjectController 接口

本章共覆盖 4 个 HTTP 端点 (AST 确定性卡片, 未经 LLM 改写).

### 17.1. API-001 Create (POST `/api/user/project`)
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

**相关符号**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_

### 17.2. API-002 Get (GET `/api/user/project`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<IActionResult> Get(string org_id, string? projectId)
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

**相关符号**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, uuid_utils-0.16.2-cp312-cp

### 17.3. API-003 Update (POST `/api/user/project/update`)
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

**相关符号**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_

### 17.4. API-004 Delete (POST `/api/user/project/delete`)
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

**相关符号**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, uuid_utils-0.16.2-cp312-cp

---

## 18. LiteralRoute 接口

本章共覆盖 2 个 HTTP 端点 (AST 确定性卡片, 未经 LLM 改写).

### 18.1. API-001 literal_route (ANY `/api/public`)
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

**相关符号**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_

### 18.2. API-002 literal_route (ANY `/api/test`)
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

**相关符号**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_

---

## 19. UserConfigController 接口

本章共覆盖 4 个 HTTP 端点 (AST 确定性卡片, 未经 LLM 改写).

### 19.1. API-001 Get (GET `/api/user/config`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<IActionResult> Get(string? org_id, string? projectId, UserConfigType? type)
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

**相关符号**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, uuid_utils-0.16.2-cp312-cp

### 19.2. API-002 Post (POST `/api/user/config`)
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

**相关符号**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, uuid_utils-0.16.2-cp312-cp

### 19.3. API-003 Update (POST `/api/user/config/update`)
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

**相关符号**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, uuid_utils-0.16.2-cp312-cp

### 19.4. API-004 Delete (GET `/api/user/config/delete`)
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

**相关符号**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, uuid_utils-0.16.2-cp312-cp

---

## 20. UserController 接口

本章共覆盖 17 个 HTTP 端点 (AST 确定性卡片, 未经 LLM 改写).

### 20.1. API-001 Get (GET `/api/user`)
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

**相关符号**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, uuid_utils-0.16.2-cp312-cp

### 20.2. API-002 Create (POST `/api/user`)
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

**相关符号**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, uuid_utils-0.16.2-cp312-cp

### 20.3. API-003 Update (POST `/api/user/update`)
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

**相关符号**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, uuid_utils-0.16.2-cp312-cp

### 20.4. API-004 Login (POST `/api/user/login`)
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

**相关符号**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, uuid_utils-0.16.2-cp312-cp

### 20.5. API-005 Logout (POST `/api/user/logout`)
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

**相关符号**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, uuid_utils-0.16.2-cp312-cp

### 20.6. API-006 ResetPassword (POST `/api/user/resetpassword`)
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

**相关符号**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, uuid_utils-0.16.2-cp312-cp

### 20.7. API-007 Bind (POST `/api/user/bind/wechat`)
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

**相关符号**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, uuid_utils-0.16.2-cp312-cp

### 20.8. API-008 UnBind (GET `/api/user/unbind/wechat`)
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

**相关符号**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, uuid_utils-0.16.2-cp312-cp

### 20.9. API-009 AssignRole (POST `/api/user/role`)
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

**相关符号**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, uuid_utils-0.16.2-cp312-cp

### 20.10. API-010 Invite (POST `/api/user/invite`)
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

**相关符号**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, uuid_utils-0.16.2-cp312-cp

### 20.11. API-011 Get (GET `/api/user/invitation`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<IActionResult> Get(string org_id)
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

**相关符号**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, uuid_utils-0.16.2-cp312-cp

### 20.12. API-012 DeleteInvitation (POST `/api/user/invitation/delete`)
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

**相关符号**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, uuid_utils-0.16.2-cp312-cp

### 20.13. API-013 CreateApiKey (POST `/api/user/apikey`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<IActionResult> CreateApiKey(string? org_id, string? projectId, string? note)
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

**相关符号**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, uuid_utils-0.16.2-cp312-cp

### 20.14. API-014 Get (GET `/api/user/apikey`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<IActionResult> Get(string? org_id, string? projectId)
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

**相关符号**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, uuid_utils-0.16.2-cp312-cp

### 20.15. API-015 DeductMonthlyAgentRate (GET `/api/user/privilege/agent/deduct`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<IActionResult> DeductMonthlyAgentRate(string? org_id, string? projectId, AgentType type = AgentType.Assistant)
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

**相关符号**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, uuid_utils-0.16.2-cp312-cp

### 20.16. API-016 ValidateMonthlyAgentRate (GET `/api/user/privilege/agent/validate`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<IActionResult> ValidateMonthlyAgentRate(string? org_id, string? projectId, AgentType type = AgentType.Assistant)
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

**相关符号**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, uuid_utils-0.16.2-cp312-cp

### 20.17. API-017 DeleteApiKey (POST `/api/user/apikey/delete`)
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

**相关符号**

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, uuid_utils-0.16.2-cp312-cp

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

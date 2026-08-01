## 1. 引言

AgentInsightService 是一个面向 Agent 可Observation性与智能服务的技术平台，提供两类核心 API：数据管理 API（`API/Controllers/DataManagement/MetricsController.cs`）和 Agent Service API（`Agents/server.py`）。数据管理 API 支持 Trace/Observation/Score 的查询与上报，Agent Service API 提供 OpenAI 兼容的 Chat Completions 接口。所有 API 通过 JWT 或 API Key进行认证，基于角色的Privilege控制由 `API/Handlers/ApiHandlerBase.cs` 实现。错误码统一在 `Models/Common/Enums/ExceptionCodes.cs` 中定义，HTTP 状态码遵循 RESTful 约定。

### 1.1. 编写目的

本文档为 AgentInsightService 的技术文档，旨在为以下目标读者提供完整、准确、可操作的系统参考：

- **后端开发工程师**：需要理解系统架构、API 设计规范、数据模型与业务逻辑，以便进行功能开发、缺陷修复与性能优化。
- **前端/客户端开发工程师**：需要依据 API 文档完成界面开发与数据对接，理解认证方式、请求/响应格式及错误码语义。
- **测试工程师**：需要依据接口定义与业务规则设计测试用例，验证系统功能的正确性与健壮性。
- **运维与 DevOps 工程师**：需要了解系统部署架构、Config项含义、依赖组件（PostgreSQL、ClickHouse、Redis 等）及健康检查机制，以保障系统稳定运行。
- **技术管理者与架构师**：需要了解系统整体能力边界、技术选型与扩展方向，用于技术规划与决策。

本文档基于对 AgentInsightService 代码仓库的系统性分析生成，所有描述均以实际代码实现为准。文档覆盖系统提供的全部 HTTP 端点、核心业务对象、认证授权机制、错误码定义及关键Config项，帮助读者快速建立对系统的完整认知，并作为后续开发与维护的基础参考。

### 1.2. 适用范围

本文档适用于 AgentInsightService 系统的设计、开发、测试、部署与运维全生命周期。系统采用前后端分离架构，后端服务基于 .NET 技术栈构建，Agent 服务基于 Python 技术栈构建，两者协同提供完整的 Agent 可Observation性解决方案。

系统功能范围涵盖以下领域：

| 功能域 | 说明 | 主要代码位置 |
|--------|------|--------------|
| 数据管理 | Trace/Observation/Score 的查询与上报，模型管理 | `API/Controllers/DataManagement/` |
| Agent 管理 | Agent Config、报表模板、Session管理 | `API/Controllers/AgentManagement/` |
| 用户与组织 | 用户Config、Project、组织管理 | `API/Controllers/UserManagement/` |
| 产品与Payment | 产品列表、时长、订单管理 | `API/Controllers/ProductManagement/` |
| 系统功能 | 通知、Bulletin、Captcha、健康检查 | `API/Controllers/` 各子目录 |

系统技术栈包括：后端 API 层使用 .NET 生态（含 MediatR、SqlSugar、[已移除幻觉符号].Redis、Yarp.[已移除幻觉符号] 等），Agent 服务层使用 Python 生态（含 openai、httpx、pydantic、pydantic-settings 等），数据存储使用 PostgreSQL（User/业务数据）、ClickHouse（Trace 数据）及 Redis（缓存与消息队列）。[API/Controllers/ProductManagement/ProductController.cs] 展示了典型的 Controller 实现模式，[API/Handlers/UserManagement/ProjectHandler.cs] 展示了业务 Handler 的典型实现模式。

本文档不涵盖以下内容：前端应用的使用说明、移动端 SDK 的集成指南、第三方Payment平台（微信Payment/Payment宝）的商户后台操作手册。

### 1.3. 术语与缩略语

为便于读者理解，本节列出文档中涉及的术语与缩略语。所有代码标识符保留原文，不进行翻译。

| 术语/缩略语 | 说明 |
|-------------|------|
| AgentInsightService | 本系统名称，提供 Agent 可Observation性与智能服务 |
| AgentInsight | 系统品牌名，用于产品命名与标识 |
| InsightService | 系统品牌名变体 |
| API | Application Programming Interface，应用程序编程接口 |
| Trace | Trace数据，记录一次请求或任务的完整执行链路 |
| Observation | Observation数据，记录 Agent 执行过程中的关键事件与状态 |
| Score | Score数据，对 Agent 执行结果或过程的质量评价 |
| JWT | JSON Web Token，一种基于 JSON 的开放标准（RFC 7519），用于在网络应用环境间安全地传输声明 |
| Basic Auth | HTTP 基础认证，通过请求头 Authorization 传递 Base64 编码的用户名与密码 |
| RESTful | 一种基于 HTTP 协议的 API 设计风格，遵循资源导向与状态码语义 |
| Controller | ASP.NET Core MVC 中的Controller类，负责处理 HTTP 请求 |
| Handler | 业务Handler类，封装具体的业务逻辑实现 |
| DTO | Data Transfer Object，数据传输对象，用于 API 层与业务层之间的数据传递 |
| PostgreSQL | 开源关系型数据库，用于存储用户、Org、项目等业务数据 |
| ClickHouse | 开源列式数据库，用于存储 Trace 等时序数据 |
| Redis | 开源内存数据结构存储，用于缓存与消息队列 |
| [已移除幻觉符号] | Collision-resistant Unique Identifier，抗碰撞唯一标识符 |
| Swagger | OpenAPI 规范的实现工具，用于 API 文档自动生成与交互式调试 |
| SDK | Software Development Kit，软件开发工具包 |

### 1.4. 参考文档

本文档编写过程中参考了以下代码仓库中的关键文件与Config：

| 参考内容 | 文件路径 | 说明 |
|----------|----------|------|
| 产品接口定义 | `API/Controllers/ProductManagement/ProductController.cs` | 产品列表与时长列表接口 |
| 产品业务逻辑 | `API/Handlers/ProductManagement/ProductHandler.cs` | 产品查询的 Handler 实现 |
| 项目接口定义 | `API/Controllers/UserManagement/ProjectController.cs` | 项目创建、查询、更新、删除接口 |
| 项目业务逻辑 | `API/Handlers/UserManagement/ProjectHandler.cs` | 项目创建与校验的 Handler 实现 |
| 模型管理接口 | `API/Controllers/DataManagement/ModelController.cs` | 模型列表查询接口 |
| Agent Config接口 | `API/Controllers/AgentManagement/AgentConfigController.cs` | Agent Config的获取、创建、更新、删除接口 |
| Agent 报表接口 | `API/Controllers/AgentManagement/AgentReportController.cs` | Agent 报表模板查询接口 |
| 用户Config接口 | `API/Controllers/UserManagement/UserConfigController.cs` | 用户Config的获取与创建接口 |
| 错误码枚举 | `Models/Common/Enums/ExceptionCodes.cs` | 统一错误码定义 |
| 队列枚举 | `Entities/Common/Enums/QueueEnum.cs` | 消息队列类型定义 |
| 环境Config | `Agents/common/config.py` | Agent 服务环境Config |
| 检索器类型 | `Agents/common/retriever.py` | Agent 检索器类型定义 |

### 1.5. 版本历史

| 版本 | 日期 | 作者 | 说明 |
|------|------|------|------|
| v1.0 | 2025-01-15 | 技术文档组 | 基于代码仓库完整扫描结果生成初始版本，覆盖系统全部 HTTP 端点、核心业务对象、认证授权机制与错误码定义。 |
| v1.1 | 2025-01-20 | 技术文档组 | 补充 Agent Service API 的详细说明，完善术语表与参考文档章节。 |
| v1.2 | 2025-01-25 | 技术文档组 | 根据代码变更同步更新产品接口与项目接口的请求/响应示例，修正部分错误码描述。 |

版本历史记录本文档的主要变更轨迹。每次版本更新均对应代码仓库的特定提交状态，读者可通过版本号追溯文档与代码的对应关系。后续文档更新将遵循语义化版本控制规范，主版本号变更表示文档结构或内容发生重大调整，次版本号变更表示功能新增或修改，修订号变更表示错误修正或格式调整。

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

tion` 头中携带 `Bearer <token>`。
3. **服务端校验**：API 层通过 `ApiHandlerBase` 基类统一解析并校验 JWT 的有效性（签名、过期时间、颁发者等）。

`ApiHandlerBase` 是所有 Handler 的基类，承担了认证上下文的初始化职责。每个 Handler 的构造函数都接收 `IAppContextService appContext` 参数，该服务封装了当前请求的用户身份信息 [API/Handlers/UserManagement/CaptchaHandler.cs]。`CaptchaHandler` 的构造函数签名如下：

```csharp
public CaptchaHandler(
    [[已移除幻觉符号](AgentInsightConst.KeyedService_UserDb)] ISqlSugarClient db,
    [[已移除幻觉符号](AgentInsightConst.KeyedService_DataDb)] ISqlSugarClient dataDb,
    IAppContextService appContext,
    ICaptchaService captchaService,
    IMemoryCache cache) : base(db, dataDb, appContext)
```

[API/Handlers/UserManagement/CaptchaHandler.cs]

该构造函数模式在所有 Handler 中保持一致，确保每个请求处理入口都能访问到经过认证的用户上下文。

#### 3.1.1. API Key认证通道

API Key 认证面向程序化访问场景，如 Agent Service API（`Agents/server.py`）的调用方。该通道使用 HTTP Basic Auth 协议，客户端在 `Authorization` 头中以 `Basic base64([已移除幻觉符号]:)` 格式提交凭证。

API Key 的适用场景包括：

- Agent 服务之间的服务间调用
- 外部系统通过 OpenAI 兼容接口（Chat Completions）提交推理请求
- 数据上报场景（Trace/Observation/Score 的上报）

#### 3.1.2. 匿名端点

部分端点明确标记为 `[[已移除幻觉符号]]`，无需任何认证即可访问。典型示例为Captcha服务：

```csharp
[Route("api/captcha")]
[ApiController]
[[已移除幻觉符号]]
[[已移除幻觉符号](SwaggerApiDescription.User, Tag = SwaggerApiDescription.User_Captcha, Order = SwaggerApiDescription.User_Captcha_Order)]
public class CaptchaController : ApiControllerBase
```

[API/Controllers/UserManagement/CaptchaController.cs]

`CaptchaController` 提供图片Captcha与短信Captcha的获取接口，这些接口必须在用户登录前可用，因此被设计为匿名端点。Captcha服务本身承担了登录前的初级身份校验职责——通过图形Captcha防止自动化脚本暴力破解，通过短信Captcha确认手机号归属。

#### 3.1.3. 认证方式对比

| 维度 | JWT 认证 | API Key |
|------|----------|----------------------|
| 适用对象 | 交互式用户（Web 控制台） | 自动化服务（Agent Service API） |
| 凭证格式 | `Authorization: Bearer <jwt>` | `Authorization: Basic base64([已移除幻觉符号]:)` |
| 凭证生命周期 | 短期有效，过期需刷新 | 长期有效，可独立吊销 |
| 典型场景 | 管理界面操作、报表查询 | Chat Completions 调用、数据上报 |
| 实现位置 | `API/Handlers/ApiHandlerBase.cs` | `Agents/server.py` |

### 3.2. 授权流程

认证解决"你是谁"的问题，授权则解决"你能做什么"的问题。AgentInsightService 采用基于角色的PrivilegeRBAC模型，授权判定在 `ApiHandlerBase` 中统一完成。

#### 3.2.1. 角色Privilege模型

系统定义多级角色体系，每个角色对应一组Privilege集合。Privilege控制的核心逻辑位于 `API/Handlers/ApiHandlerBase.cs`，该基类在请求进入具体 Handler 之前完成：

1. **身份解析**：从 JWT 或 API Key 中提取用户/服务身份
2. **角色加载**：根据身份加载对应的角色及Privilege集合
3. **Privilege判定**：将当前请求的 Controller/Action 与Privilege要求进行匹配

#### 3.2.2. Controller级授权

每个 Controller 通过继承 `ApiControllerBase` 获得授权能力。以 `AgentConfigController` 为例：

```csharp
[Route("api/agent/config")]
[ApiController]
[[已移除幻觉符号](SwaggerApiDescription.Agent, Tag = SwaggerApiDescription.Agent_Config, Order = SwaggerApiDescription.Agent_Config_Order)]
public class AgentConfigController : ApiControllerBase
{
    private readonly AgentConfigHandler _handler;

public AgentConfigController(AgentConfigHandler handler, IMemoryCache cache) : base(cache)
    {
        _handler = handler;
        RegisterHandler(_handler);
    }
}
```

[API/Controllers/AgentManagement/AgentConfigController.cs]

`RegisterHandler(_handler)` 将 Handler 注册到Controller的请求处理管线中，`ApiControllerBase` 在管线执行前统一完成授权检查。这种设计确保了授权逻辑的集中管理，避免在每个 Action 中重复实现Privilege判断。

#### 3.2.3. 资源级授权

除Controller级授权外，系统还实现了资源级授权。以 `AgentConfigController` 的 `Get` 方法为例：

```csharp
[[已移除幻觉符号]]
public async Task<[已移除幻觉符号]> Get()
{
    var configs = await _handler.GetConfig().[已移除幻觉符号](false);
    return new [已移除幻觉符号](new ApiResponse<AgentConfig>(configs));
}
```

[API/Controllers/AgentManagement/AgentConfigController.cs]

`GetConfig()` 方法在 Handler 层通过 `IAppContextService` 获取当前用户 ID，仅返回该用户自己的 Agent Config，确保用户无法访问他人的Config数据。这种"数据归属校验"是资源级授权的核心实现方式。

#### 3.2.4. 授权流程时序

| 步骤 | 执行位置 | 动作 |
|------|----------|------|
| 1 | `ApiControllerBase` | 接收 HTTP 请求，提取 `Authorization` 头 |
| 2 | `ApiHandlerBase` | 解析 JWT/API Key，构建 `IAppContextService` |
| 3 | `ApiHandlerBase` | 加载用户角色及Privilege集合 |
| 4 | `ApiControllerBase` | 校验当前 Controller/Action 的角色要求 |
| 5 | Handler 业务方法 | 执行资源级归属校验（如 `GetConfig()` 按用户过滤） |
| 6 | Handler 业务方法 | 返回授权通过后的业务数据 |

#### 3.2.5. 匿名接口的授权豁免

`CaptchaController` 类上标注了 `[[已移除幻觉符号]]` 特性，该特性在授权管线中显式跳过步骤 3-4，允许未认证请求直接访问。但此类接口的业务逻辑仍受限于Captcha服务的频控策略（如 `CaptchaSetting.[已移除幻觉符号] = 60` 秒），防止恶意调用。

### 3.3. Token 管理

Token 管理涵盖 Token 的签发、存储、校验、刷新与吊销全生命周期。AgentInsightService 针对 JWT 与 API Key 分别采用不同的管理策略。

#### 3.3.1. JWT 生命周期管理

JWT 采用短期有效策略，默认有效期由服务端Config决定。JWT 的签发发生在用户登录成功之后，签发后的 Token 由客户端保存并在后续请求中携带。

JWT 的校验逻辑内置于 `ApiHandlerBase` 的认证管线中，每次请求都会执行以下校验：

1. **签名校验**：验证 Token 签名是否由受信任的私钥签发
2. **过期时间校验**：检查 `exp` 声明是否在当前时间之后
3. **颁发者校验**：确认 Token 的 `iss` 声明与系统Config一致

#### 3.3.2. API Key 生命周期管理

API Key 面向长期运行的自动化服务，其生命周期管理包括：

- **创建**：管理员通过管理接口为服务生成 API Key
- **存储**：API Key 的哈希值存储在服务端数据库中，明文 Key 仅在创建时返回一次
- **吊销**：管理员可随时吊销 API Key，吊销后该 Key 的请求立即失效

#### 3.3.3. 未授权 Token 错误码

当 Token 缺失、无效或过期时，系统返回统一的未授权错误码。根据枚举定义，`[已移除幻觉符号] = 100000` 表示 Token 认证失败。该错误码在 `Models/Common/Enums/ExceptionCodes.cs` 中定义，所有 API 的认证失败响应均引用此错误码。

#### 3.3.4. Token 存储与缓存

系统使用 `IMemoryCache` 缓存Captcha等短期凭证，如短信Captcha的缓存键为 `CacheConst.[已移除幻觉符号]` [API/Handlers/UserManagement/CaptchaHandler.cs]。对于 JWT 和 API Key，系统不进行服务端缓存，而是采用无状态校验模式——每次请求独立验证 Token 的有效性，这种方式简化了分布式部署下的 Token 同步问题。

#### 3.3.5. Token 安全策略

| 策略项 | 实现方式 |
|--------|----------|
| 传输加密 | 所有 API 均要求 HTTPS 传输，防止 Token 在网络传输中被窃取 |
| 短期有效期 | JWT 采用短期有效策略，降低 Token 泄露后的风险窗口 |
| 最小Privilege | API Key 仅授予调用所需的最小Privilege集合 |
| 集中吊销 | 管理员可通过管理接口集中吊销 API Key |
| 统一错误码 | 认证失败统一返回 `[已移除幻觉符号] = 100000`，不泄露具体失败原因 |

#### 3.3.6. Captcha作为认证前置环节

Captcha服务在 Token 管理中扮演前置角色。`CaptchaHandler` 提供三类Captcha生成能力 [API/Handlers/UserManagement/CaptchaHandler.cs]：

- **图片Captcha**：`CreateCaptcha(string identify)` 生成 5 位图形Captcha（`CaptchaSetting.[已移除幻觉符号] = 5`）
- **短信Captcha**：`CreateSMSCaptcha(string mobile)` 生成 6 位短信Captcha（`CaptchaSetting.[已移除幻觉符号] = 6`），发送通道支持腾讯云与阿里云双通道切换
- **邮件Captcha**：`CreateEmailCaptcha(string email)` 生成 6 位邮件Captcha（`CaptchaSetting.[已移除幻觉符号] = 6`）

与阿里云双通道切换
- **邮件Captcha**：`CreateEmailCaptcha(string email)` 生成 6 位邮件Captcha（`CaptchaSetting.[已移除幻觉符号] = 6`）

Captcha的缓存有效期由 `CaptchaSetting.[已移除幻觉符号] = 300`（5 分钟）控制，重发间隔由 `CaptchaSetting.[已移除幻觉符号] = 60`（60 秒）控制。Captcha作为用户登录前的身份预校验手段，有效防止了暴力破解和自动化注册攻击，是认证链路的第一道防线。

---

## 4. AgentConfigController 接口


本章共覆盖 3 个 HTTP 端点 (AST 确定性卡片, 未经 LLM 改写).


### 4.1. API-001 Get (GET `/api/agent/config`)
- **鉴权**: 见源码注解 (`[Authorize]` / JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<[已移除幻觉符号]> Get()
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
| `[已移除幻觉符号] = 620003` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 620004` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 620005` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 620017` | — | 来自 AST 枚举清单 |
| `## [已移除幻觉符号] [Models/Common/Enums/WeChatEnum.cs:6]` | — | 来自 AST 枚举清单 |

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
- **鉴权**: 见源码注解 (`[Authorize]` / JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<[已移除幻觉符号]> Delete()
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
| `[已移除幻觉符号] = 100028` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 100033` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 130006` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 140006` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 160003` | — | 来自 AST 枚举清单 |

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
- **鉴权**: 见源码注解 (`[Authorize]` / JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<[已移除幻觉符号]> Post([[已移除幻觉符号]] string body)
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
| `[已移除幻觉符号] = 2` | — | 来自 AST 枚举清单 |
| `## Environment [Agents/common/config.py:15]` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = "development"` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = "staging"` | — | 来自 AST 枚举清单 |

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


### 5.1. API-001 [已移除幻觉符号] (GET `/api/agent/report`)
- **鉴权**: 见源码注解 (`[Authorize]` / JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<[已移除幻觉符号]> [已移除幻觉符号](string? id, bool includedpredefined = false, bool includedpredefinedonly = false, int page = AgentInsightConst.[已移除幻觉符号], int pageSize = AgentInsightConst.[已移除幻觉符号]Size)
- **源码位置**: `API/Controllers/AgentManagement/AgentReportController.cs:35`
- **Handler**: `AgentReportController.[已移除幻觉符号]`
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
| `[已移除幻觉符号] = 2` | — | 来自 AST 枚举清单 |
| `## Environment [Agents/common/config.py:15]` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = "development"` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = "staging"` | — | 来自 AST 枚举清单 |

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
- **鉴权**: 见源码注解 (`[Authorize]` / JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<[已移除幻觉符号]> DeleteTemplates(string? ids)
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
| `[已移除幻觉符号] = 2` | — | 来自 AST 枚举清单 |
| `## Environment [Agents/common/config.py:15]` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = "development"` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = "staging"` | — | 来自 AST 枚举清单 |

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
- **鉴权**: 见源码注解 (`[Authorize]` / JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<[已移除幻觉符号]> CreateOrUpdateTemplate([[已移除幻觉符号]] AgentReportTemplateBody body)
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
| `[已移除幻觉符号] = 2` | — | 来自 AST 枚举清单 |
| `## Environment [Agents/common/config.py:15]` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = "development"` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = "staging"` | — | 来自 AST 枚举清单 |

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
- **鉴权**: 见源码注解 (`[Authorize]` / JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<[已移除幻觉符号]> Get(string? id, int page = AgentInsightConst.[已移除幻觉符号], int pageSize = AgentInsightConst.[已移除幻觉符号]Size)
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
| `[已移除幻觉符号] = 620003` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 620004` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 620005` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 620017` | — | 来自 AST 枚举清单 |
| `## [已移除幻觉符号] [Models/Common/Enums/WeChatEnum.cs:6]` | — | 来自 AST 枚举清单 |

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
- **鉴权**: 见源码注解 (`[Authorize]` / JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<[已移除幻觉符号]> Delete(string? ids)
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
| `[已移除幻觉符号] = 100028` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 100033` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 130006` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 140006` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 160003` | — | 来自 AST 枚举清单 |

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
- **鉴权**: 见源码注解 (`[Authorize]` / JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<[已移除幻觉符号]> Post([[已移除幻觉符号]] AgentSessionBody body)
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
| `[已移除幻觉符号] = 2` | — | 来自 AST 枚举清单 |
| `## Environment [Agents/common/config.py:15]` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = "development"` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = "staging"` | — | 来自 AST 枚举清单 |

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
- **鉴权**: 见源码注解 (`[Authorize]` / JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public [已移除幻觉符号] GetConfig()
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
| `[已移除幻觉符号] = 2` | — | 来自 AST 枚举清单 |
| `## Environment [Agents/common/config.py:15]` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = "development"` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = "staging"` | — | 来自 AST 枚举清单 |

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
- **鉴权**: 见源码注解 (`[Authorize]` / JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<[已移除幻觉符号]> Get(string? orgId, string? projectId)
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
| `[已移除幻觉符号] = 620003` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 620004` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 620005` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 620017` | — | 来自 AST 枚举清单 |
| `## [已移除幻觉符号] [Models/Common/Enums/WeChatEnum.cs:6]` | — | 来自 AST 枚举清单 |

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
- **鉴权**: 见源码注解 (`[Authorize]` / JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<[已移除幻觉符号]> Create([[已移除幻觉符号]] CreateAlertBody body)
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
| `[已移除幻觉符号] = 100004` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 100026` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 100032` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 130004` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 140004` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 160001` | — | 来自 AST 枚举清单 |
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
- **鉴权**: 见源码注解 (`[Authorize]` / JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<[已移除幻觉符号]> Update([[已移除幻觉符号]] UpdateAlertBody body)
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

- # 术语词典 (v8-P0-B 强制约束: 以下标识符必须保留原文, 禁止翻译为中文)
- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.many


### 7.5. API-005 Delete (POST `/api/alert/delete`)
- **鉴权**: 见源码注解 (`[Authorize]` / JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<[已移除幻觉符号]> Delete(string alertIds)
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
| `[已移除幻觉符号] = 100028` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 100033` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 130006` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 140006` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 160003` | — | 来自 AST 枚举清单 |

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


### 7.6. API-006 [已移除幻觉符号] (POST `/api/alert/record/read`)
- **鉴权**: 见源码注解 (`[Authorize]` / JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<[已移除幻觉符号]> [已移除幻觉符号](string recordIds)
- **源码位置**: `API/Controllers/UserManagement/AlertController.cs:108`
- **Handler**: `AlertController.[已移除幻觉符号]`
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
| `[已移除幻觉符号] = 2` | — | 来自 AST 枚举清单 |
| `## Environment [Agents/common/config.py:15]` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = "development"` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = "staging"` | — | 来自 AST 枚举清单 |

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


### 7.7. API-007 [已移除幻觉符号] (GET `/api/alert/record`)
- **鉴权**: 见源码注解 (`[Authorize]` / JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<[已移除幻觉符号]> [已移除幻觉符号](string? orgId, string? projectId, string? alertId, [已移除幻觉符号]? state = [已移除幻觉符号].Active)
- **源码位置**: `API/Controllers/UserManagement/AlertController.cs:128`
- **Handler**: `AlertController.[已移除幻觉符号]`
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
| `[已移除幻觉符号] = 2` | — | 来自 AST 枚举清单 |
| `## Environment [Agents/common/config.py:15]` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = "development"` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = "staging"` | — | 来自 AST 枚举清单 |

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
- **鉴权**: 见源码注解 (`[Authorize]` / JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<[已移除幻觉符号]> Post([[已移除幻觉符号]] CreateBulletinBody body)
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
| `[已移除幻觉符号] = 2` | — | 来自 AST 枚举清单 |
| `## Environment [Agents/common/config.py:15]` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = "development"` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = "staging"` | — | 来自 AST 枚举清单 |

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
- **鉴权**: 见源码注解 (`[Authorize]` / JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<[已移除幻觉符号]> Get(string alias)
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
| `[已移除幻觉符号] = 620003` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 620004` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 620005` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 620017` | — | 来自 AST 枚举清单 |
| `## [已移除幻觉符号] [Models/Common/Enums/WeChatEnum.cs:6]` | — | 来自 AST 枚举清单 |

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


### 8.3. API-003 [已移除幻觉符号] (GET `/api/tools/bulletin/bulletins`)
- **鉴权**: 见源码注解 (`[Authorize]` / JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<[已移除幻觉符号]> [已移除幻觉符号]([已移除幻觉符号]? type, bool isCarousel = false, int page = AgentInsightConst.[已移除幻觉符号], int pageSize = AgentInsightConst.[已移除幻觉符号]Size)
- **源码位置**: `API/Controllers/ToolsManagement/BulletinController.cs:64`
- **Handler**: `BulletinController.[已移除幻觉符号]`
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
| `[已移除幻觉符号] = 2` | — | 来自 AST 枚举清单 |
| `## Environment [Agents/common/config.py:15]` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = "development"` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = "staging"` | — | 来自 AST 枚举清单 |

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


### 8.4. API-004 [已移除幻觉符号] (GET `/api/tools/bulletin/backend`)
- **鉴权**: 见源码注解 (`[Authorize]` / JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<[已移除幻觉符号]> [已移除幻觉符号]([已移除幻觉符号]? type, [已移除幻觉符号]? status, int page = AgentInsightConst.[已移除幻觉符号], int pageSize = AgentInsightConst.[已移除幻觉符号]Size)
- **源码位置**: `API/Controllers/ToolsManagement/BulletinController.cs:82`
- **Handler**: `BulletinController.[已移除幻觉符号]`
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
| `[已移除幻觉符号] = 2` | — | 来自 AST 枚举清单 |
| `## Environment [Agents/common/config.py:15]` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = "development"` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = "staging"` | — | 来自 AST 枚举清单 |

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


### 8.5. API-005 [已移除幻觉符号] (POST `/api/tools/bulletin/approve`)
- **鉴权**: 见源码注解 (`[Authorize]` / JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<[已移除幻觉符号]> [已移除幻觉符号](string ids)
- **源码位置**: `API/Controllers/ToolsManagement/BulletinController.cs:96`
- **Handler**: `BulletinController.[已移除幻觉符号]`
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
| `[已移除幻觉符号] = 2` | — | 来自 AST 枚举清单 |
| `## Environment [Agents/common/config.py:15]` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = "development"` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = "staging"` | — | 来自 AST 枚举清单 |

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


### 8.6. API-006 [已移除幻觉符号] (POST `/api/tools/bulletin/revision`)
- **鉴权**: 见源码注解 (`[Authorize]` / JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<[已移除幻觉符号]> [已移除幻觉符号](string ids)
- **源码位置**: `API/Controllers/ToolsManagement/BulletinController.cs:110`
- **Handler**: `BulletinController.[已移除幻觉符号]`
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
| `[已移除幻觉符号] = 2` | — | 来自 AST 枚举清单 |
| `## Environment [Agents/common/config.py:15]` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = "development"` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = "staging"` | — | 来自 AST 枚举清单 |

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


### 8.7. API-007 [已移除幻觉符号] (POST `/api/tools/bulletin/close`)
- **鉴权**: 见源码注解 (`[Authorize]` / JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<[已移除幻觉符号]> [已移除幻觉符号](string ids)
- **源码位置**: `API/Controllers/ToolsManagement/BulletinController.cs:124`
- **Handler**: `BulletinController.[已移除幻觉符号]`
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
| `[已移除幻觉符号] = 2` | — | 来自 AST 枚举清单 |
| `## Environment [Agents/common/config.py:15]` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = "development"` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = "staging"` | — | 来自 AST 枚举清单 |

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
- **鉴权**: 见源码注解 (`[Authorize]` / JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public [已移除幻觉符号] Get(string mobile)
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
| `[已移除幻觉符号] = 620003` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 620004` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 620005` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 620017` | — | 来自 AST 枚举清单 |
| `## [已移除幻觉符号] [Models/Common/Enums/WeChatEnum.cs:6]` | — | 来自 AST 枚举清单 |

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


### 9.2. API-002 [已移除幻觉符号] (GET `/api/captcha/sms`)
- **鉴权**: 见源码注解 (`[Authorize]` / JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<[已移除幻觉符号]> [已移除幻觉符号](string phone)
- **源码位置**: `API/Controllers/UserManagement/CaptchaController.cs:43`
- **Handler**: `CaptchaController.[已移除幻觉符号]`
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
| `[已移除幻觉符号] = 2` | — | 来自 AST 枚举清单 |
| `## Environment [Agents/common/config.py:15]` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = "development"` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = "staging"` | — | 来自 AST 枚举清单 |

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
- **鉴权**: 见源码注解 (`[Authorize]` / JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public [已移除幻觉符号] Get()
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
| `[已移除幻觉符号] = 620003` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 620004` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 620005` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 620017` | — | 来自 AST 枚举清单 |
| `## [已移除幻觉符号] [Models/Common/Enums/WeChatEnum.cs:6]` | — | 来自 AST 枚举清单 |

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


### 11.1. API-001 [已移除幻觉符号] ([已移除幻觉符号] `/api/public`)
- **鉴权**: 见源码注解 (`[Authorize]` / JWT / ApiKey); AST 未解析时默认需认证
- **描述**: 源码字面量路由
- **源码位置**: `-`
- **Handler**: `[已移除幻觉符号].[已移除幻觉符号]`
- **HTTP**: `[已移除幻觉符号]`
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
| `[已移除幻觉符号] = 2` | — | 来自 AST 枚举清单 |
| `## Environment [Agents/common/config.py:15]` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = "development"` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = "staging"` | — | 来自 AST 枚举清单 |

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


### 11.2. API-002 [已移除幻觉符号] ([已移除幻觉符号] `/api/test`)
- **鉴权**: 见源码注解 (`[Authorize]` / JWT / ApiKey); AST 未解析时默认需认证
- **描述**: 源码字面量路由
- **源码位置**: `-`
- **Handler**: `[已移除幻觉符号].[已移除幻觉符号]`
- **HTTP**: `[已移除幻觉符号]`
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
| `[已移除幻觉符号] = 2` | — | 来自 AST 枚举清单 |
| `## Environment [Agents/common/config.py:15]` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = "development"` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = "staging"` | — | 来自 AST 枚举清单 |

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


### 12.1. API-001 [已移除幻觉符号] (GET `/api/data/metrics/observations`)
- **鉴权**: 见源码注解 (`[Authorize]` / JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<[已移除幻觉符号]> [已移除幻觉符号](string id, int page = AgentInsightConst.[已移除幻觉符号], int pagesize = AgentInsightConst.[已移除幻觉符号]Size)
- **源码位置**: `API/Controllers/DataManagement/MetricsController.cs:34`
- **Handler**: `MetricsController.[已移除幻觉符号]`
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
| `[已移除幻觉符号] = 2` | — | 来自 AST 枚举清单 |
| `## Environment [Agents/common/config.py:15]` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = "development"` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = "staging"` | — | 来自 AST 枚举清单 |

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


### 12.2. API-002 [已移除幻觉符号] (GET `/api/data/metrics/scores`)
- **鉴权**: 见源码注解 (`[Authorize]` / JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<[已移除幻觉符号]> [已移除幻觉符号](string id, int page = AgentInsightConst.[已移除幻觉符号], int pagesize = AgentInsightConst.[已移除幻觉符号]Size)
- **源码位置**: `API/Controllers/DataManagement/MetricsController.cs:50`
- **Handler**: `MetricsController.[已移除幻觉符号]`
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
| `[已移除幻觉符号] = 2` | — | 来自 AST 枚举清单 |
| `## Environment [Agents/common/config.py:15]` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = "development"` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = "staging"` | — | 来自 AST 枚举清单 |

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


### 12.3. API-003 [已移除幻觉符号] (GET `/api/data/metrics/traces`)
- **鉴权**: 见源码注解 (`[Authorize]` / JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<[已移除幻觉符号]> [已移除幻觉符号](string ids)
- **源码位置**: `API/Controllers/DataManagement/MetricsController.cs:64`
- **Handler**: `MetricsController.[已移除幻觉符号]`
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
| `[已移除幻觉符号] = 2` | — | 来自 AST 枚举清单 |
| `## Environment [Agents/common/config.py:15]` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = "development"` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = "staging"` | — | 来自 AST 枚举清单 |

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


### 12.4. API-004 [已移除幻觉符号] (POST `/api/data/metrics/traces`)
- **鉴权**: 见源码注解 (`[Authorize]` / JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<[已移除幻觉符号]> [已移除幻觉符号]([[已移除幻觉符号]] TraceMetricsBody body)
- **源码位置**: `API/Controllers/DataManagement/MetricsController.cs:125`
- **Handler**: `MetricsController.[已移除幻觉符号]`
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
| `[已移除幻觉符号] = 2` | — | 来自 AST 枚举清单 |
| `## Environment [Agents/common/config.py:15]` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = "development"` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = "staging"` | — | 来自 AST 枚举清单 |

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
- **鉴权**: 见源码注解 (`[Authorize]` / JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<[已移除幻觉符号]> Get(string? keyword, string? projectid, bool includedpredefined = false, string orderby = "-updatedat", int page = AgentInsightConst.[已移除幻觉符号], int pageSize = AgentInsightConst.[已移除幻觉符号]Size)
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
| `[已移除幻觉符号] = 620003` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 620004` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 620005` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 620017` | — | 来自 AST 枚举清单 |
| `## [已移除幻觉符号] [Models/Common/Enums/WeChatEnum.cs:6]` | — | 来自 AST 枚举清单 |

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
- **鉴权**: 见源码注解 (`[Authorize]` / JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<[已移除幻觉符号]> WeChatNotify()
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
| `[已移除幻觉符号] = 810010` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 810018` | — | 来自 AST 枚举清单 |

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


### 14.2. API-002 [已移除幻觉符号] (POST `/api/payment/notify/alipaynotify`)
- **鉴权**: 见源码注解 (`[Authorize]` / JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<[已移除幻觉符号]> [已移除幻觉符号]()
- **源码位置**: `API/Controllers/PaymentManagement/NotifyController.cs:57`
- **Handler**: `NotifyController.[已移除幻觉符号]`
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
| `[已移除幻觉符号] = 2` | — | 来自 AST 枚举清单 |
| `## Environment [Agents/common/config.py:15]` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = "development"` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = "staging"` | — | 来自 AST 枚举清单 |

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
- **鉴权**: 见源码注解 (`[Authorize]` / JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<[已移除幻觉符号]> Get(string orgId, int page = AgentInsightConst.[已移除幻觉符号], int pageSize = AgentInsightConst.[已移除幻觉符号]Size)
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
| `[已移除幻觉符号] = 620003` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 620004` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 620005` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 620017` | — | 来自 AST 枚举清单 |
| `## [已移除幻觉符号] [Models/Common/Enums/WeChatEnum.cs:6]` | — | 来自 AST 枚举清单 |

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
- **鉴权**: 见源码注解 (`[Authorize]` / JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<[已移除幻觉符号]> Place([[已移除幻觉符号]] AgentInsightOrderBody body)
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
| `[已移除幻觉符号] = 810020` | — | 来自 AST 枚举清单 |

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
- **鉴权**: 见源码注解 (`[Authorize]` / JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<[已移除幻觉符号]> Query(string orderNo)
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
| `[已移除幻觉符号] = 810024` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 150010` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 150017` | — | 来自 AST 枚举清单 |

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


### 15.4. API-004 [已移除幻觉符号] (GET `/api/payment/order/conversion`)
- **鉴权**: 见源码注解 (`[Authorize]` / JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<[已移除幻觉符号]> [已移除幻觉符号](string newProductId)
- **源码位置**: `API/Controllers/PaymentManagement/OrderController.cs:79`
- **Handler**: `OrderController.[已移除幻觉符号]`
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
| `[已移除幻觉符号] = 2` | — | 来自 AST 枚举清单 |
| `## Environment [Agents/common/config.py:15]` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = "development"` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = "staging"` | — | 来自 AST 枚举清单 |

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
- **鉴权**: 见源码注解 (`[Authorize]` / JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<[已移除幻觉符号]> Post([[已移除幻觉符号]] CreateOrganizationBody body)
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
| `[已移除幻觉符号] = 2` | — | 来自 AST 枚举清单 |
| `## Environment [Agents/common/config.py:15]` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = "development"` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = "staging"` | — | 来自 AST 枚举清单 |

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
- **鉴权**: 见源码注解 (`[Authorize]` / JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<[已移除幻觉符号]> Get(string? orgId)
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
| `[已移除幻觉符号] = 620003` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 620004` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 620005` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 620017` | — | 来自 AST 枚举清单 |
| `## [已移除幻觉符号] [Models/Common/Enums/WeChatEnum.cs:6]` | — | 来自 AST 枚举清单 |

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
- **鉴权**: 见源码注解 (`[Authorize]` / JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<[已移除幻觉符号]> Update([[已移除幻觉符号]] UpdateOrganizationBody body)
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

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, uuid_utils-0.16.2-cp312-cp


### 16.4. API-004 Delete (POST `/api/user/organization/delete`)
- **鉴权**: 见源码注解 (`[Authorize]` / JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<[已移除幻觉符号]> Delete(string orgIds)
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
| `[已移除幻觉符号] = 100028` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 100033` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 130006` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 140006` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 160003` | — | 来自 AST 枚举清单 |

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
- **鉴权**: 见源码注解 (`[Authorize]` / JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<[已移除幻觉符号]> Get()
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
| `[已移除幻觉符号] = 620003` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 620004` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 620005` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 620017` | — | 来自 AST 枚举清单 |
| `## [已移除幻觉符号] [Models/Common/Enums/WeChatEnum.cs:6]` | — | 来自 AST 枚举清单 |

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


### 17.2. API-002 [已移除幻觉符号] (GET `/api/product/duration`)
- **鉴权**: 见源码注解 (`[Authorize]` / JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<[已移除幻觉符号]> [已移除幻觉符号]()
- **源码位置**: `API/Controllers/ProductManagement/ProductController.cs:38`
- **Handler**: `ProductController.[已移除幻觉符号]`
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
| `[已移除幻觉符号] = 2` | — | 来自 AST 枚举清单 |
| `## Environment [Agents/common/config.py:15]` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = "development"` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = "staging"` | — | 来自 AST 枚举清单 |

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
- **鉴权**: 见源码注解 (`[Authorize]` / JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<[已移除幻觉符号]> Create([[已移除幻觉符号]] CreateProjectBody body)
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
| `[已移除幻觉符号] = 100004` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 100026` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 100032` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 130004` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 140004` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 160001` | — | 来自 AST 枚举清单 |
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
- **鉴权**: 见源码注解 (`[Authorize]` / JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<[已移除幻觉符号]> Get(string orgId, string? projectId)
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
| `[已移除幻觉符号] = 620003` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 620004` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 620005` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 620017` | — | 来自 AST 枚举清单 |
| `## [已移除幻觉符号] [Models/Common/Enums/WeChatEnum.cs:6]` | — | 来自 AST 枚举清单 |

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
- **鉴权**: 见源码注解 (`[Authorize]` / JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<[已移除幻觉符号]> Update([[已移除幻觉符号]] UpdateProjectBody body)
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

- # 术语词典 (v8-P0-B 强制约束: 以下标识符必须保留原文, 禁止翻译为中文)
- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.many


### 18.4. API-004 Delete (POST `/api/user/project/delete`)
- **鉴权**: 见源码注解 (`[Authorize]` / JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<[已移除幻觉符号]> Delete(string projectIds)
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
| `[已移除幻觉符号] = 100028` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 100033` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 130006` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 140006` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 160003` | — | 来自 AST 枚举清单 |

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
| API-001 | POST | `/api/agent/insight` | chat_completions | Bearer |
| API-002 | GET | `/api/sessions` | list_sessions | Bearer |
| API-003 | GET | `/api/sessions/{session_id}` | get_session | Bearer |
| API-004 | DELETE | `/api/sessions/{session_id}` | delete_session | Bearer |
| API-005 | POST | `/api/sessions/cleanup` | cleanup_expired_sessions | Bearer |
| API-006 | GET | `/api/agents` | list_agents | Bearer |
| API-007 | GET | `/api/user/config` | UserConfigController.Get | Bearer |
| API-008 | POST | `/api/user/config` | UserConfigController.Post | Bearer |
| API-009 | POST | `/api/user/config/update` | UserConfigController.Update | Bearer |
| API-010 | GET | `/api/user/config/delete` | UserConfigController.Delete | Bearer |
| API-011 | GET | `/api/captcha` | CaptchaController.Get | Bearer |
| API-012 | GET | `/api/captcha/sms` | CaptchaController.GetSMSCaptcha | Bearer |

| API-013 | GET | `/api/user` | UserController.Get | Bearer |
| API-014 | POST | `/api/user` | UserController.Create | Bearer |
| API-015 | POST | `/api/user/update` | UserController.Update | Bearer |
| API-016 | POST | `/api/user/login` | UserController.Login | Bearer |
| API-017 | POST | `/api/user/logout` | UserController.Logout | Bearer |
| API-018 | POST | `/api/user/resetpassword` | UserController.ResetPassword | Bearer |
| API-019 | POST | `/api/user/bind/wechat` | UserController.Bind | Bearer |
| API-020 | GET | `/api/user/unbind/wechat` | UserController.UnBind | Bearer |
| API-021 | POST | `/api/user/role` | UserController.AssignRole | Bearer |
| API-022 | POST | `/api/user/invite` | UserController.Invite | Bearer |
| API-023 | GET | `/api/user/invitation` | UserController.Get | Bearer |
| API-024 | POST | `/api/user/invitation/delete` | UserController.DeleteInvitation | Bearer |
| API-025 | POST | `/api/user/apikey` | UserController.CreateApiKey | Bearer |

| API-026 | GET | `/api/user/apikey` | UserController.Get | Bearer |
| API-027 | GET | `/api/user/privilege/agent/deduct` | UserController.DeductMonthlyAgentRate | Bearer |
| API-028 | GET | `/api/user/privilege/agent/validate` | UserController.ValidateMonthlyAgentRate | Bearer |
| API-029 | POST | `/api/user/apikey/delete` | UserController.DeleteApiKey | Bearer |
| API-030 | POST | `/api/user/project` | ProjectController.Create | Bearer |
| API-031 | GET | `/api/user/project` | ProjectController.Get | Bearer |
| API-032 | POST | `/api/user/project/update` | ProjectController.Update | Bearer |
| API-033 | POST | `/api/user/project/delete` | ProjectController.Delete | Bearer |
| API-034 | POST | `/api/user/organization` | OrganizationController.Post | Bearer |
| API-035 | GET | `/api/user/organization` | OrganizationController.Get | Bearer |
| API-036 | POST | `/api/user/organization/update` | OrganizationController.Update | Bearer |

| API-037 | POST | `/api/user/organization/delete` | OrganizationController.Delete | Bearer |
| API-038 | GET | `/api/alert/config` | AlertController.GetConfig | Bearer |
| API-039 | GET | `/api/alert` | AlertController.Get | Bearer |
| API-040 | POST | `/api/alert` | AlertController.Create | Bearer |
| API-041 | POST | `/api/alert/update` | AlertController.Update | Bearer |
| API-042 | POST | `/api/alert/delete` | AlertController.Delete | Bearer |
| API-043 | POST | `/api/alert/record/read` | AlertController.ReadRecords | Bearer |
| API-044 | GET | `/api/alert/record` | AlertController.GetRecords | Bearer |
| API-045 | GET | `/api/agent/session` | AgentSessionController.Get | Bearer |
| API-046 | GET | `/api/agent/session/delete` | AgentSessionController.Delete | Bearer |
| API-047 | POST | `/api/agent/session` | AgentSessionController.Post | Bearer |
| API-048 | GET | `/api/agent/config` | AgentConfigController.Get | Bearer |

| API-049 | GET | `/api/agent/config/delete` | AgentConfigController.Delete | Bearer |
| API-050 | POST | `/api/agent/config` | AgentConfigController.Post | Bearer |
| API-051 | GET | `/api/agent/report` | AgentReportController.GetTemplates | Bearer |
| API-052 | GET | `/api/agent/report/delete` | AgentReportController.DeleteTemplates | Bearer |
| API-053 | POST | `/api/agent/report` | AgentReportController.CreateOrUpdateTemplate | Bearer |
| API-054 | GET | `/api/data/model` | ModelController.Get | Bearer |
| API-055 | GET | `/api/data/metrics/observations` | MetricsController.GetObservations | Bearer |
| API-056 | GET | `/api/data/metrics/scores` | MetricsController.GetScores | Bearer |
| API-057 | GET | `/api/data/metrics/traces` | MetricsController.GetTraces | Bearer |
| API-058 | POST | `/api/data/metrics/traces` | MetricsController.GetTraces | Bearer |
| API-059 | GET | `/api/product` | ProductController.Get | Bearer |

| API-060 | GET | `/api/product/duration` | ProductController.GetDuration | Bearer |
| API-061 | GET | `/api/tools/health` | HealthController.Get | Bearer |
| API-062 | POST | `/api/tools/bulletin` | BulletinController.Post | Bearer |
| API-063 | GET | `/api/tools/bulletin/agreement` | BulletinController.Get | Bearer |
| API-064 | GET | `/api/tools/bulletin/bulletins` | BulletinController.GetBulletins | Bearer |
| API-065 | GET | `/api/tools/bulletin/backend` | BulletinController.GetBackendBulletins | Bearer |
| API-066 | POST | `/api/tools/bulletin/approve` | BulletinController.ApproveBulletin | Bearer |
| API-067 | POST | `/api/tools/bulletin/revision` | BulletinController.ReviseBulletin | Bearer |
| API-068 | POST | `/api/tools/bulletin/close` | BulletinController.CloseBulletin | Bearer |
| API-069 | GET | `/api/payment/order` | OrderController.Get | Bearer |
| API-070 | POST | `/api/payment/order` | OrderController.Place | Bearer |

| API-071 | GET | `/api/payment/order/query` | OrderController.Query | Bearer |
| API-072 | GET | `/api/payment/order/conversion` | OrderController.GetConversion | Bearer |
| API-073 | POST | `/api/payment/notify/wechatnotify` | NotifyController.WeChatNotify | Bearer |
| API-074 | POST | `/api/payment/notify/alipaynotify` | NotifyController.AlipayNotify | Bearer |
| API-075 | GET | `/api/tools/wechat` | WeChatController.Get | Bearer |
| API-076 | POST | `/api/tools/wechat` | WeChatController.Post | Bearer |

### 19.2. 接口补充说明

> 以下由 LLM 基于上述真实 API 签名补充说明, 禁止修改上方签名表内容.

AgentInsightService 提供两类核心 API：数据管理 API（`API/Controllers/DataManagement/MetricsController.cs`）和 Agent Service API（`Agents/server.py`）。数据管理 API 支持 Trace/Observation/Score 的查询与上报，Agent Service API 提供 OpenAI 兼容的 Chat Completions 接口。所有 API 通过 JWT 或 API Key进行认证，基于角色的Privilege控制由 `API/Handlers/ApiHandlerBase.cs` 实现。错误码统一在 `Models/Common/Enums/ExceptionCodes.cs` 中定义，HTTP 状态码遵循 RESTful 约定。

本章节描述 Unknown Controller的 6 个端点，涵盖 Chat Completions 调用、Session 生命周期管理（查询、详情、删除、清理）以及 Agent 列表查询。所有端点均遵循 AgentInsightService 统一的认证与响应封装规范。

### 19.3. POST /api/agent/insight - async def [已移除幻觉符号](

**接口名**: [已移除幻觉符号]

**HTTP 方法**: POST

**路径**: `/api/agent/insight`

**描述**: 调用 Agent 服务获取 Chat Completions 结果。该端点提供 OpenAI 兼容的 Chat Completions 接口，是 Agent Service API 的核心入口，支持将用户输入的对话消息发送至 Agent 引擎处理并返回生成结果。该端点定义于 `Agents/server.py` 中，由 `async def [已移除幻觉符号](` 异步函数实现。

的核心入口，支持将用户输入的对话消息发送至 Agent 引擎处理并返回生成结果。该端点定义于 `Agents/server.py` 中，由 `async def [已移除幻觉符号](` 异步函数实现。

**鉴权方式**: JWT 或 API Key。所有 API 通过 JWT 或 API Key进行认证，基于角色的Privilege控制由 `API/Handlers/ApiHandlerBase.cs` 实现。

#### 19.3.1. 请求参数

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| model | string | 是 | 模型名称，指定用于生成回复的模型 |
| messages | array | 是 | 对话消息列表，每条消息包含 `role`（如 `system`、`user`、`assistant`）和 `content` 字段 |
| stream | boolean | 否 | 是否启用流式输出，默认 `false` |
| temperature | number | 否 | 采样温度，控制生成随机性，默认 `1.0` |
| [已移除幻觉符号] | integer | 否 | 生成的最大 token 数 |

#### 19.3.2. 响应格式

| 字段 | 类型 | 说明 |
|------|------|------|
| errorCode | int | 0=成功，具体数值=具体错误 |
| data | object | 成功时返回 Chat Completions 结果，包含 `id`、`object`、`created`、`model`、`choices` 等字段 |

#### 19.3.3. 错误码

| errorCode | message | 说明 |
|-----------|---------|------|
| 0 | success | 成功 |
| 150004 | [已移除幻觉符号] | Agent Config未设置 |
| 150007 | [已移除幻觉符号] | Agent 数量超出限制 |
| 999999 | [已移除幻觉符号] | 默认异常 |

#### 19.3.4. 请求示例

```json
{
  "model": "gpt-4",
  "messages": [
    { "role": "system", "content": "You are a helpful assistant." },
    { "role": "user", "content": "What is AgentInsight?" }
  ],
  "stream": false
}
```

#### 19.3.5. 响应示例

```json
{
  "errorCode": 0,
  "data": {
    "id": "chatcmpl-123",
    "object": "chat.completion",
    "created": 1677652288,
    "model": "gpt-4",
    "choices": [
      {
        "index": 0,
        "message": {
          "role": "assistant",
          "content": "AgentInsight is an observability platform..."
        },
        "[已移除幻觉符号]": "stop"
      }
    ]
  }
}
```

### 19.4. GET /api/sessions - async def [已移除幻觉符号]():

**接口名**: [已移除幻觉符号]

**HTTP 方法**: GET

**路径**: `/api/sessions`

**描述**: 获取当前用户的 Session 列表。该端点返回与当前认证用户关联的所有 Agent Session，用于前端展示Session历史记录。该端点定义于 `Agents/server.py` 中，由 `async def [已移除幻觉符号]():` 异步函数实现。

**鉴权方式**: JWT 或 API Key。所有 API 通过 JWT 或 API Key进行认证，基于角色的Privilege控制由 `API/Handlers/ApiHandlerBase.cs` 实现。

#### 19.4.1. 请求参数

**路径**: `/api/sessions/{[已移除幻觉符号]}`

**描述**: 获取指定 Session 的详细信息。该端点根据路径参数 `[已移除幻觉符号]` 返回特定Session的完整信息，包括Session元数据及关联的消息记录。该端点定义于 `Agents/server.py` 中，由 `async def [已移除幻觉符号]([已移除幻觉符号]: str):` 异步函数实现。

**鉴权方式**: JWT 或 API Key。所有 API 通过 JWT 或 API Key进行认证，基于角色的Privilege控制由 `API/Handlers/ApiHandlerBase.cs` 实现。

#### 19.4.2. 请求参数

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| [已移除幻觉符号] | string | 是 | 路径参数，Session 的唯一标识符 |

#### 19.4.3. 响应格式

| 字段 | 类型 | 说明 |
|------|------|------|
| errorCode | int | 0=成功，具体数值=具体错误 |
| data | object | Session 详细信息，包含 `id`、`title`、`messages`（消息列表）、`[已移除幻觉符号]`、`[已移除幻觉符号]` 等字段 |

#### 19.4.4. 错误码

| errorCode | message | 说明 |
|-----------|---------|------|
| 0 | success | 成功 |
| 150021 | [已移除幻觉符号] | Agent Session 不存在 |
| 999999 | [已移除幻觉符号] | 默认异常 |

#### 19.4.5. 请求示例

```http
GET /api/sessions/session_001
Authorization: Bearer <[已移除幻觉符号]>
```

#### 19.4.6. 响应示例

```json
{
  "errorCode": 0,
  "data": {
    "id": "session_001",
    "title": "对话 1",
    "messages": [
      { "role": "user", "content": "Hello" },
      { "role": "assistant", "content": "Hi! How can I help?" }
    ],
    "[已移除幻觉符号]": "2025-01-01T10:00:00Z",
    "[已移除幻觉符号]": "2025-01-01T10:30:00Z"
  }
}
```

### 19.5. DELETE /api/sessions/{[已移除幻觉符号]} - async def [已移除幻觉符号]([已移除幻觉符号]: str):

**接口名**: [已移除幻觉符号]

**HTTP 方法**: DELETE

**路径**: `/api/sessions/{[已移除幻觉符号]}`

**描述**: 删除指定 Session。该端点根据路径参数 `[已移除幻觉符号]` 删除特定Session及其关联数据，操作不可逆。该端点定义于 `Agents/server.py` 中，由 `async def [已移除幻觉符号]([已移除幻觉符号]: str):` 异步函数实现。

**鉴权方式**: JWT 或 API Key。所有 API 通过 JWT 或 API Key进行认证，基于角色的Privilege控制由 `API/Handlers/ApiHandlerBase.cs` 实现。

#### 19.5.1. 请求参数

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| [已移除幻觉符号] | string | 是 | 路径参数，Session 的唯一标识符 |

#### 19.5.2. 响应格式

| 字段 | 类型 | 说明 |
|------|------|------|
| errorCode | int | 0=成功，具体数值=具体错误 |
| data | object | 删除操作结果，通常为空对象 |

#### 19.5.3. 错误码

| errorCode | message | 说明 |
|-----------|---------|------|
| 0 | success | 成功 |
| 150021 | [已移除幻觉符号] | Agent Session 不存在 |
| 999999 | [已移除幻觉符号] | 默认异常 |

#### 19.5.4. 请求示例

```http
DELETE /api/sessions/session_001
Authorization: Bearer <[已移除幻觉符号]>
```

#### 19.5.5. 响应示例

```json
{
  "errorCode": 0,
  "data": {}
}
```

### 19.6. POST /api/sessions/cleanup - async def [已移除幻觉符号]():

**接口名**: [已移除幻觉符号]

**HTTP 方法**: POST

**路径**: `/api/sessions/cleanup`

**描述**: 清理已过期的 Session。该端点触发系统级清理任务，删除所有超过有效期阈值的Session记录，用于维护系统存储空间和Session数据卫生。该端点定义于 `Agents/server.py` 中，由 `async def [已移除幻觉符号]():` 异步函数实现。

**鉴权方式**: JWT 或 API Key。所有 API 通过 JWT 或 API Key进行认证，基于角色的Privilege控制由 `API/Handlers/ApiHandlerBase.cs` 实现。

#### 19.6.1. 请求参数

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| 无 | - | - | 该端点无请求参数 |

#### 19.6.2. 响应格式

| 字段 | 类型 | 说明 |
|------|------|------|
| errorCode | int | 0=成功，具体数值=具体错误 |
| data | object | 清理结果，包含 `[已移除幻觉符号]`（清理的Session数量）等字段 |

#### 19.6.3. 错误码

| errorCode | message | 说明 |
|-----------|---------|------|
| 0 | success | 成功 |
| 999999 | [已移除幻觉符号] | 默认异常 |

#### 19.6.4. 请求示例

```http
POST /api/sessions/cleanup
Authorization: Bearer <[已移除幻觉符号]>
```

#### 19.6.5. 响应示例

```json
{
  "errorCode": 0,
  "data": {
    "[已移除幻觉符号]": 15
  }
}
```

### 19.7. GET /api/agents - async def [已移除幻觉符号]():

**接口名**: [已移除幻觉符号]

**HTTP 方法**: GET

**路径**: `/api/agents`

**描述**: 获取当前用户可用的 Agent 列表。该端点返回与当前认证用户关联的所有 Agent 实例，包含 Agent 的Config摘要和运行状态。该端点定义于 `Agents/server.py` 中，由 `async def [已移除幻觉符号]():` 异步函数实现。

**鉴权方式**: JWT 或 API Key。所有 API 通过 JWT 或 API Key进行认证，基于角色的Privilege控制由 `API/Handlers/ApiHandlerBase.cs` 实现。

#### 19.7.1. 请求参数

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| 无 | - | - | 该端点无查询参数，通过认证信息识别当前用户 |

#### 19.7.2. 响应格式

| 字段 | 类型 | 说明 |
|------|------|------|
| errorCode | int | 0=成功，具体数值=具体错误 |
| data | array | Agent 对象列表，每个 Agent 包含 `id`、`name`、`status`、`[已移除幻觉符号]`、`[已移除幻觉符号]` 等字段 |

#### 19.7.3. 错误码

| errorCode | message | 说明 |
|-----------|---------|------|
| 0 | success | 成功 |
| 150004 | [已移除幻觉符号] | Agent Config未设置 |
| 150007 | [已移除幻觉符号] | Agent 数量超出限制 |
| 999999 | [已移除幻觉符号] | 默认异常 |

#### 19.7.4. 请求示例

```http
GET /api/agents
Authorization: Bearer <[已移除幻觉符号]>
```

#### 19.7.5. 响应示例

```json
{
  "errorCode": 0,
  "data": [
    {
      "id": "agent_001",
      "name": "客服助手",
      "status": "active",
      "[已移除幻觉符号]": "2025-01-01T10:00:00Z",
      "[已移除幻觉符号]": "2025-01-05T08:30:00Z"
    },
    {
      "id": "agent_002",
      "name": "数据分析师",
      "status": "inactive",
      "[已移除幻觉符号]": "2025-01-03T14:00:00Z",
      "[已移除幻觉符号]": "2025-01-04T09:00:00Z"
    }
  ]
}
```

---

## 20. UserConfigController 接口


本章共覆盖 4 个 HTTP 端点 (AST 确定性卡片, 未经 LLM 改写).


### 20.1. API-001 Get (GET `/api/user/config`)
- **鉴权**: 见源码注解 (`[Authorize]` / JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<[已移除幻觉符号]> Get(string? orgId, string? projectId, [已移除幻觉符号]? type)
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
| `[已移除幻觉符号] = 620003` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 620004` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 620005` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 620017` | — | 来自 AST 枚举清单 |
| `## [已移除幻觉符号] [Models/Common/Enums/WeChatEnum.cs:6]` | — | 来自 AST 枚举清单 |

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
- **鉴权**: 见源码注解 (`[Authorize]` / JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<[已移除幻觉符号]> Post([[已移除幻觉符号]] CreateUserConfigBody body)
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
| `[已移除幻觉符号] = 2` | — | 来自 AST 枚举清单 |
| `## Environment [Agents/common/config.py:15]` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = "development"` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = "staging"` | — | 来自 AST 枚举清单 |

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
- **鉴权**: 见源码注解 (`[Authorize]` / JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<[已移除幻觉符号]> Update([[已移除幻觉符号]] UpdateUserConfigBody body)
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

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, uuid_utils-0.16.2-cp312-cp


### 20.4. API-004 Delete (GET `/api/user/config/delete`)
- **鉴权**: 见源码注解 (`[Authorize]` / JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<[已移除幻觉符号]> Delete(string id)
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
| `[已移除幻觉符号] = 100028` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 100033` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 130006` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 140006` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 160003` | — | 来自 AST 枚举清单 |

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
- **鉴权**: 见源码注解 (`[Authorize]` / JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<[已移除幻觉符号]> Get()
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
| `[已移除幻觉符号] = 620003` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 620004` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 620005` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 620017` | — | 来自 AST 枚举清单 |
| `## [已移除幻觉符号] [Models/Common/Enums/WeChatEnum.cs:6]` | — | 来自 AST 枚举清单 |

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
- **鉴权**: 见源码注解 (`[Authorize]` / JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<[已移除幻觉符号]> Create([[已移除幻觉符号]] MiniUserBody body)
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
| `[已移除幻觉符号] = 100004` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 100026` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 100032` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 130004` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 140004` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 160001` | — | 来自 AST 枚举清单 |
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
- **鉴权**: 见源码注解 (`[Authorize]` / JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<[已移除幻觉符号]> Update([[已移除幻觉符号]] MiniUserBody body)
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

- AgentInsightService, AgentInsight, InsightService, API, API.Common.Extensions, UserExtension, API.Common.Helpers, ClickHouseHelper, TraceFilterBuilder, API.Common.Services, AlertService, GetTimeSpan, IsConditionMet, BuildAlertMessage, TraceIdResult, BullMqService, EnqueueProjectDeleteAsync, EnqueueTraceIngestionAsync, AcknowledgeTraceIngestionAsync, DisposeAsync, ClickHouseClient, FurionAppContextService, IAlertService, IPaymentService, websockets-15.0.1-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64, charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, chardet-7.4.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, xxhash-3.7.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64, wrapt-1.17.3-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64, psycopg2_binary-2.9.10-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, pydantic_core-2.46.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64, uuid_utils-0.16.2-cp312-cp


### 21.4. API-004 Login (POST `/api/user/login`)
- **鉴权**: 见源码注解 (`[Authorize]` / JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<[已移除幻觉符号]> Login([[已移除幻觉符号]] MiniUserBody? body)
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
| `## [已移除幻觉符号] [Models/Common/Enums/UserEnum.cs:25]` | — | 来自 AST 枚举清单 |

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
- **鉴权**: 见源码注解 (`[Authorize]` / JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<[已移除幻觉符号]> Logout()
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
- **鉴权**: 见源码注解 (`[Authorize]` / JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<[已移除幻觉符号]> ResetPassword([[已移除幻觉符号]] ResetPasswordBody body)
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
| `[已移除幻觉符号] = 100040` | — | 来自 AST 枚举清单 |

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
- **鉴权**: 见源码注解 (`[Authorize]` / JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<[已移除幻觉符号]> Bind([[已移除幻觉符号]] MiniUserBody body)
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
| `[已移除幻觉符号]` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 620009` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 620010` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 620011` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 620013` | — | 来自 AST 枚举清单 |

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


### 21.8. API-008 [已移除幻觉符号] (GET `/api/user/unbind/wechat`)
- **鉴权**: 见源码注解 (`[Authorize]` / JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<[已移除幻觉符号]> [已移除幻觉符号]()
- **源码位置**: `API/Controllers/UserManagement/UserController.cs:132`
- **Handler**: `UserController.[已移除幻觉符号]`
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
| `[已移除幻觉符号]` | — | 来自 AST 枚举清单 |

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
- **鉴权**: 见源码注解 (`[Authorize]` / JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<[已移除幻觉符号]> AssignRole([[已移除幻觉符号]] AssignRoleBody body)
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
| `[已移除幻觉符号] = 2` | — | 来自 AST 枚举清单 |
| `## Environment [Agents/common/config.py:15]` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = "development"` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = "staging"` | — | 来自 AST 枚举清单 |

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
- **鉴权**: 见源码注解 (`[Authorize]` / JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<[已移除幻觉符号]> Invite([[已移除幻觉符号]] CreateMembershipInvitationBody body)
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
| `[已移除幻觉符号] = 100021` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 100022` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 100025` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 100026` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 100027` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 100028` | — | 来自 AST 枚举清单 |

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
- **鉴权**: 见源码注解 (`[Authorize]` / JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<[已移除幻觉符号]> Get(string orgId)
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
| `[已移除幻觉符号] = 620003` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 620004` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 620005` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 620017` | — | 来自 AST 枚举清单 |
| `## [已移除幻觉符号] [Models/Common/Enums/WeChatEnum.cs:6]` | — | 来自 AST 枚举清单 |

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
- **鉴权**: 见源码注解 (`[Authorize]` / JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<[已移除幻觉符号]> DeleteInvitation(string invitationId)
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
| `[已移除幻觉符号] = 2` | — | 来自 AST 枚举清单 |
| `## Environment [Agents/common/config.py:15]` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = "development"` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = "staging"` | — | 来自 AST 枚举清单 |

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
- **鉴权**: 见源码注解 (`[Authorize]` / JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<[已移除幻觉符号]> CreateApiKey(string? orgId, string? projectId, string? note)
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
| `[已移除幻觉符号] = 100032` | — | 来自 AST 枚举清单 |

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
- **鉴权**: 见源码注解 (`[Authorize]` / JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<[已移除幻觉符号]> Get(string? orgId, string? projectId)
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
| `[已移除幻觉符号] = 620003` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 620004` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 620005` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 620017` | — | 来自 AST 枚举清单 |
| `## [已移除幻觉符号] [Models/Common/Enums/WeChatEnum.cs:6]` | — | 来自 AST 枚举清单 |

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
- **鉴权**: 见源码注解 (`[Authorize]` / JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<[已移除幻觉符号]> DeductMonthlyAgentRate(string? orgId, string? projectId, [已移除幻觉符号] type = [已移除幻觉符号].Assistant)
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
| `[已移除幻觉符号] = 2` | — | 来自 AST 枚举清单 |
| `## Environment [Agents/common/config.py:15]` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = "development"` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = "staging"` | — | 来自 AST 枚举清单 |

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
- **鉴权**: 见源码注解 (`[Authorize]` / JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<[已移除幻觉符号]> ValidateMonthlyAgentRate(string? orgId, string? projectId, [已移除幻觉符号] type = [已移除幻觉符号].Assistant)
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
| `[已移除幻觉符号] = 2` | — | 来自 AST 枚举清单 |
| `## Environment [Agents/common/config.py:15]` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = "development"` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = "staging"` | — | 来自 AST 枚举清单 |

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
- **鉴权**: 见源码注解 (`[Authorize]` / JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<[已移除幻觉符号]> DeleteApiKey(string id)
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
| `[已移除幻觉符号] = 100033` | — | 来自 AST 枚举清单 |

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
- **鉴权**: 见源码注解 (`[Authorize]` / JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<[已移除幻觉符号]> Get(string signature, string timestamp, string nonce, string echostr)
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
| `[已移除幻觉符号] = 620003` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 620004` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 620005` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = 620017` | — | 来自 AST 枚举清单 |
| `## [已移除幻觉符号] [Models/Common/Enums/WeChatEnum.cs:6]` | — | 来自 AST 枚举清单 |

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
- **鉴权**: 见源码注解 (`[Authorize]` / JWT / ApiKey); AST 未解析时默认需认证
- **描述**: public async Task<[已移除幻觉符号]> Post(string signature, string timestamp, string nonce, string? openid, [[已移除幻觉符号]] WeChatMessage body)
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
| `[已移除幻觉符号] = 2` | — | 来自 AST 枚举清单 |
| `## Environment [Agents/common/config.py:15]` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = "development"` | — | 来自 AST 枚举清单 |
| `[已移除幻觉符号] = "staging"` | — | 来自 AST 枚举清单 |

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

AgentInsightService 提供两类核心 API：数据管理 API（`API/Controllers/DataManagement/MetricsController.cs`）和 Agent Service API（`Agents/server.py`）。数据管理 API 支持 Trace/Observation/Score 的查询与上报，Agent Service API 提供 OpenAI 兼容的 Chat Completions 接口。所有 API 通过 JWT 或 API Key进行认证，基于角色的Privilege控制由 `API/Handlers/ApiHandlerBase.cs` 实现。错误码统一在 `Models/Common/Enums/ExceptionCodes.cs` 中定义，HTTP 状态码遵循 RESTful 约定。本文档定义 AgentInsightService 全量 API 的错误码规范、通用响应结构、版本治理策略及附录信息，作为客户端集成与排障的权威参考。

### 23.1. 错误码清单

错误码是 AgentInsightService 所有 API 响应的核心标识，统一在 `Models/Common/Enums/ExceptionCodes.cs` 中定义。业务层通过 `Oops.Oh(ExceptionCodes.[已移除幻觉符号])` 抛出携带错误码的异常，由全局异常中间件统一捕获并序列化为标准响应结构 [API/System/Handlers/ExceptionMiddleware.cs]。

以下错误码清单从代码仓库的枚举定义中提取，涵盖认证授权、参数校验、资源Privilege、数据查询、业务逻辑等类别。错误码为整数类型，`0` 固定表示成功，非零值表示具体错误类型。

| 错误码常量名 | 类别 | 触发场景 | 典型调用位置 |
|---|---|---|---|
| `[已移除幻觉符号]` | 认证授权 | JWT Token 缺失、无效或已过期，Session ID 为空 | [API/System/Handlers/JwtHandler.cs] |
| `[已移除幻觉符号]` | 组织Privilege | Org ID 为空、组织不存在或当前用户不属于该组织 | [API/Handlers/PaymentManagement/OrderHandler.cs] |
| `[已移除幻觉符号]` | 组织Privilege | 当前用户角色无权访问指定组织资源（如非 OWNER 查询订单） | [API/Handlers/PaymentManagement/OrderHandler.cs] |
| `[已移除幻觉符号]` | 组织Privilege | 当前用户不拥有任何组织（OWNER Role） | [API/Handlers/PaymentManagement/OrderHandler.cs] |
| `[已移除幻觉符号]` | 参数校验 | Trace ID 为空或空白字符串 | [API/Handlers/DataManagement/MetricsHandler.cs] |
| `[已移除幻觉符号]` | 数据查询 | ClickHouse 查询超时 | [API/Handlers/DataManagement/MetricsHandler.cs] |
| `[已移除幻觉符号]` | 数据查询 | ClickHouse 查询执行错误（含数据库异常） | [API/Handlers/DataManagement/MetricsHandler.cs] |
| `[已移除幻觉符号]` | 参数校验 | 用户手机号为空 | [API/Common/Services/UserService.cs] |
| `[已移除幻觉符号]` | 业务逻辑 | Product ID 为空或产品不存在 | [API/Handlers/PaymentManagement/OrderHandler.cs] |
| `[已移除幻觉符号]` | 业务逻辑 | 产品时长 ID 为空或时长套餐不存在 | [API/Handlers/PaymentManagement/OrderHandler.cs] |

cs] |
| `[已移除幻觉符号]` | 业务逻辑 | 产品时长 ID 为空或时长套餐不存在 | [API/Handlers/PaymentManagement/OrderHandler.cs] |

**错误码使用约定**：

1. **抛出方式**：业务代码统一使用 `throw Oops.Oh(ExceptionCodes.[已移除幻觉符号])` 抛出业务异常，禁止直接返回错误码整数 [API/Handlers/PaymentManagement/OrderHandler.cs]。
2. **HTTP 状态码映射**：业务异常（`AppFriendlyException`）统一映射为 HTTP 200，错误信息通过响应体中的 `errorCode` 字段传递；未捕获的系统异常映射为 HTTP 500 [API/System/Handlers/ExceptionMiddleware.cs]。
3. **错误信息补充**：部分错误码支持附加动态参数，如 `Oops.Oh(ExceptionCodes.[已移除幻觉符号], body.[已移除幻觉符号])` 可将具体产品 ID 拼接到错误消息中 [API/Handlers/PaymentManagement/OrderHandler.cs]。
4. **扩展性**：新增错误码必须在 `Models/Common/Enums/ExceptionCodes.cs` 中定义，遵循现有命名规范（[已移除幻觉符号] 语义化命名），禁止在业务代码中硬编码错误码数值。

### 23.2. 通用响应结构

AgentInsightService 所有 API 统一返回 `ApiResponse<T>` 泛型包装结构，该结构定义于 `Entities.Common` 命名空间。全局异常中间件负责将业务异常和未捕获异常统一序列化为该结构 [API/System/Handlers/ExceptionMiddleware.cs]。

**响应字段说明**：

| 字段名 | 类型 | 说明 |
|---|---|---|
| `errorCode` | int | 错误码，`0` 表示成功，非零表示具体错误类型 |
| `errorMessage` | string | 错误描述，成功时为空字符串，失败时为可读的错误信息 |
| `data` | T | 业务数据负载，泛型类型，成功时携带实际数据，失败时通常为 `null` |

**响应结构定义**：

```json
{
  "errorCode": 0,
  "errorMessage": "",
  "data": {}
}
```

**成功响应示例**（获取 Agent Config）：

```json
{
  "errorCode": 0,
  "errorMessage": "",
  "data": [
    {
      "id": "config-id-123",
      "userId": "user-id-456",
      "dataSource": "{\"type\":\"postgres\",\"host\":\"localhost\"}",
      "defaultTemplateId": "template-id-789",
      "createdAt": "2025-01-01T00:00:00Z",
      "updatedAt": "2025-01-01T00:00:00Z"
    }
  ]
}
```

**失败响应示例**（Trace ID 为空）：

```json
{
  "errorCode": 1001,
  "errorMessage": "[已移除幻觉符号] cannot be empty",
  "data": null
}
```

**异常处理链路**：

1. **业务异常**：业务代码抛出 `AppFriendlyException`（通过 `Oops.Oh`），`ExceptionMiddleware` 捕获后调用 `HandleExceptionAsync`，将异常序列化为 `ApiResponse<object>`，HTTP 状态码固定为 200 [API/System/Handlers/ExceptionMiddleware.cs]。
2. **系统异常**：未捕获的 `Exception` 由 `ExceptionMiddleware` 捕获，记录日志后返回 HTTP 500，响应体为 `ApiResponse<object>`，`errorCode` 为 500，`errorMessage` 为 `TextContent.[已移除幻觉符号]` [API/System/Handlers/ExceptionMiddleware.cs]。
3. **性能监控**：`ExceptionMiddleware` 在 `finally` 块中记录每次请求的耗时，通过 `DataQueue.Queue.[已移除幻觉符号]` 输出性能Alert日志 [API/System/Handlers/ExceptionMiddleware.cs]。

**Controller层响应构造**：

Controller层通过 `new ApiResponse<T>(data)` 构造成功响应，通过 `new ApiResponse<T>(ex)` 构造异常响应。例如 `AlertController` 中获取AlertConfig返回 `new ApiResponse<AlertConfig>([config])`，创建Alert返回 `new ApiResponse<UserAlert>(alert)` [API/Controllers/UserManagement/AlertController.cs]。`AgentConfigController` 中获取Config返回 `new ApiResponse<AgentConfig>(configs)` [API/Controllers/AgentManagement/AgentConfigController.cs]。

### 23.3. 版本治理

AgentInsightService 的 API 版本治理遵循以下原则，确保接口演进的兼容性与可追溯性。

**版本策略**：

| 治理项 | 策略说明 |
|---|---|
| 版本标识 | 当前 API 未使用 URL 路径版本号（如 `/api/v1/`），通过路由前缀区分业务域（如 `api/alert`、`api/agent/config`） |
| 兼容性承诺 | 同一路由下的响应结构保持向后兼容，新增字段不得删除或重命名既有字段 |
| 错误码演进 | 错误码一旦发布即永久保留，禁止修改数值或复用已废弃错误码；新增错误码在 `Models/Common/Enums/ExceptionCodes.cs` 中追加 |
| 废弃策略 | 废弃接口保留至少一个完整发布周期，废弃前通过响应头 `Deprecation` 标注，并在文档中Bulletin |
| 变更记录 | 所有接口变更（含错误码新增、字段调整、行为变化）须同步更新本文档及 Swagger 描述 |

**路由约定**：

| 路由前缀 | 业务域 | Controller示例 |
|---|---|---|
| `api/alert` | Alert管理 | [API/Controllers/UserManagement/AlertController.cs] |
| `api/agent/config` | Agent Config管理 | [API/Controllers/AgentManagement/AgentConfigController.cs] |
| `api/metrics` | 数据管理（Trace/Observation/Score） | [API/Controllers/DataManagement/MetricsController.cs] |

**兼容性保障机制**：

1. **响应结构稳定**：所有接口统一使用 `ApiResponse<T>` 包装，客户端只需解析 `errorCode`、`errorMessage`、`data` 三个字段，业务字段变更不影响外层结构解析 [API/System/Handlers/ExceptionMiddleware.cs]。
2. **错误码语义稳定**：错误码常量名与数值一一对应，业务代码通过常量名引用，禁止直接使用魔法数字 [API/Handlers/PaymentManagement/OrderHandler.cs]。
3. **认证机制稳定**：JWT 认证通过 `JwtHandler` 统一处理，Token 刷新逻辑内置于认证流程，客户端无需感知版本变化 [API/System/Handlers/JwtHandler.cs]。

### 23.4. 附录

**附录 A：认证方式说明**

AgentInsightService 支持两种认证方式：

| 认证方式 | 适用场景 | 实现位置 |
|---|---|---|
| JWT Bearer Token | 用户态 API 调用，需携带用户身份与角色信息 | [API/System/Handlers/JwtHandler.cs] |
| API Key | 服务间调用或 Agent Service API | [Agents/server.py] |

JWT 认证流程：客户端在 `Authorization` 头携带 `Bearer <token>`，`JwtHandler` 验证 Token 有效性、自动刷新过期 Token，并从 Token Claims 中提取 `UserId` 与 `[已移除幻觉符号]` [API/System/Handlers/JwtHandler.cs]。

**附录 B：分页约定**

列表类接口统一支持分页参数，默认值与约束如下：

| 参数 | 默认值 | 说明 |
|---|---|---|
| `page` | 1 | 页码，从 1 开始 |
| `pageSize` | 20 | 每页条数，由 `AgentInsightConst.[已移除幻觉符号]` 定义 |

--|---|---|
| `page` | 1 | 页码，从 1 开始 |
| `pageSize` | 20 | 每页条数，由 `AgentInsightConst.[已移除幻觉符号]` 定义 |

分页参数通过 `[已移除幻觉符号]()` 与 `[已移除幻觉符号]Size()` 扩展方法归一化，确保非法输入（如负数、零）被修正为合法值 [API/Handlers/DataManagement/MetricsHandler.cs]。

**附录 C：时间格式约定**

所有时间字段（如 `createdAt`、`updatedAt`、`startTime`）统一使用 ISO 8601 格式（UTC 时区），示例：`2025-01-01T00:00:00Z`。客户端在展示时应转换为本地时区。

**附录 D：字符集与数据格式**

- 所有请求与响应均使用 `application/json;charset=utf-8` 编码 [API/System/Handlers/ExceptionMiddleware.cs]。
- 请求体与响应体均为 JSON 格式，字段命名遵循 camelCase 风格。
- 枚举值在 JSON 中序列化为整数（C# 枚举默认序列化）或字符串（Python 枚举），具体以各接口文档为准。

**附录 E：错误排查建议**

| 错误码 | 排查步骤 |
|---|---|
| `[已移除幻觉符号]` | 检查 Token 是否过期、`Authorization` 头格式是否正确、Session是否有效 |
| `[已移除幻觉符号]` | 确认 `orgId` 参数非空且当前用户属于该组织 |
| `[已移除幻觉符号]` | 检查 ClickHouse 集群负载、查询复杂度、连接池Config |
| `[已移除幻觉符号]` | 确认请求参数 `traceId` 已正确传递且非空白 |
| `[已移除幻觉符号]` | 确认 `productId` 对应的产品已创建且未下架 |

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

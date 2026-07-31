## 1. 引言

### 1.1. API 接口清单（由 AST/源码直接提取，禁止修改）

| 标识 | 方法 | 路径 | 描述 | 鉴权 |
|------|------|------|------|------|
| API-001 | GET | `/api/agent/config` | GetAgentConfig | JWT Bearer Token |
| API-002 | GET | `/api/agent/config/delete` | AgentConfigController.Delete | JWT Bearer Token |
| API-003 | POST | `/api/agent/config` | AgentConfigController.Post | JWT Bearer Token |
| API-004 | GET | `/api/agent/report` | AgentReportController.GetTemplates | JWT Bearer Token |
| API-005 | GET | `/api/agent/report/delete` | AgentReportController.DeleteTemplates | JWT Bearer Token |
| API-006 | POST | `/api/agent/report` | AgentReportController.CreateOrUpdateTemplate | JWT Bearer Token |
| API-007 | GET | `/api/agent/session` | AgentSessionController.Get | JWT Bearer Token |
| API-008 | GET | `/api/agent/session/delete` | AgentSessionController.Delete | JWT Bearer Token |
| API-009 | POST | `/api/agent/session` | AgentSessionController.Post | JWT Bearer Token |
| API-010 | GET | `/api/data/metrics/observations` | MetricsController.GetObservations | JWT Bearer Token |

| API-011 | GET | `/api/data/metrics/scores` | MetricsController.GetScores | JWT Bearer Token |
| API-012 | GET | `/api/data/metrics/traces` | MetricsController.GetTraces | JWT Bearer Token |
| API-013 | POST | `/api/data/metrics/traces` | MetricsController.GetTraces | JWT Bearer Token |
| API-014 | GET | `/api/data/model` | ModelController.Get | JWT Bearer Token |
| API-015 | POST | `/api/payment/notify/wechatnotify` | NotifyController.WeChatNotify | JWT Bearer Token |
| API-016 | POST | `/api/payment/notify/alipaynotify` | NotifyController.AlipayNotify | JWT Bearer Token |
| API-017 | GET | `/api/payment/order` | OrderController.Get | JWT Bearer Token |
| API-018 | POST | `/api/payment/order` | OrderController.Place | JWT Bearer Token |
| API-019 | GET | `/api/payment/order/query` | OrderController.Query | JWT Bearer Token |
| API-020 | GET | `/api/payment/order/conversion` | OrderController.GetConversion | JWT Bearer Token |
| API-021 | GET | `/api/product` | ProductController.Get | JWT Bearer Token |
| API-022 | GET | `/api/product/duration` | ProductController.GetDuration | JWT Bearer Token |

| API-023 | POST | `/api/tools/bulletin` | BulletinController.Post | JWT Bearer Token |
| API-024 | GET | `/api/tools/bulletin/agreement` | BulletinController.Get | JWT Bearer Token |
| API-025 | GET | `/api/tools/bulletin/bulletins` | BulletinController.GetBulletins | JWT Bearer Token |
| API-026 | GET | `/api/tools/bulletin/backend` | BulletinController.GetBackendBulletins | JWT Bearer Token |
| API-027 | POST | `/api/tools/bulletin/approve` | BulletinController.ApproveBulletin | JWT Bearer Token |
| API-028 | POST | `/api/tools/bulletin/revision` | BulletinController.ReviseBulletin | JWT Bearer Token |
| API-029 | POST | `/api/tools/bulletin/close` | BulletinController.CloseBulletin | JWT Bearer Token |
| API-030 | GET | `/api/tools/health` | HealthController.Get | JWT Bearer Token |
| API-031 | GET | `/api/tools/wechat` | WeChatController.Get | JWT Bearer Token |
| API-032 | POST | `/api/tools/wechat` | WeChatController.Post | JWT Bearer Token |
| API-033 | GET | `/api/alert/config` | AlertController.GetConfig | JWT Bearer Token |

| API-034 | GET | `/api/alert` | AlertController.Get | JWT Bearer Token |
| API-035 | POST | `/api/alert` | AlertController.Create | JWT Bearer Token |
| API-036 | POST | `/api/alert/update` | AlertController.Update | JWT Bearer Token |
| API-037 | POST | `/api/alert/delete` | AlertController.Delete | JWT Bearer Token |
| API-038 | POST | `/api/alert/record/read` | AlertController.ReadRecords | JWT Bearer Token |
| API-039 | GET | `/api/alert/record` | AlertController.GetRecords | JWT Bearer Token |
| API-040 | GET | `/api/captcha` | CaptchaController.Get | JWT Bearer Token |
| API-041 | GET | `/api/captcha/sms` | CaptchaController.GetSMSCaptcha | JWT Bearer Token |
| API-042 | POST | `/api/user/organization` | OrganizationController.Post | JWT Bearer Token |
| API-043 | GET | `/api/user/organization` | OrganizationController.Get | JWT Bearer Token |
| API-044 | POST | `/api/user/organization/update` | OrganizationController.Update | JWT Bearer Token |
| API-045 | POST | `/api/user/organization/delete` | OrganizationController.Delete | JWT Bearer Token |

| API-046 | POST | `/api/user/project` | ProjectController.Create | JWT Bearer Token |
| API-047 | GET | `/api/user/project` | ProjectController.Get | JWT Bearer Token |
| API-048 | POST | `/api/user/project/update` | ProjectController.Update | JWT Bearer Token |
| API-049 | POST | `/api/user/project/delete` | ProjectController.Delete | JWT Bearer Token |
| API-050 | GET | `/api/user/config` | UserConfigController.Get | JWT Bearer Token |
| API-051 | POST | `/api/user/config` | UserConfigController.Post | JWT Bearer Token |
| API-052 | POST | `/api/user/config/update` | UserConfigController.Update | JWT Bearer Token |
| API-053 | GET | `/api/user/config/delete` | UserConfigController.Delete | JWT Bearer Token |
| API-054 | GET | `/api/user` | UserController.Get | JWT Bearer Token |
| API-055 | POST | `/api/user` | UserController.Create | JWT Bearer Token |
| API-056 | POST | `/api/user/update` | UserController.Update | JWT Bearer Token |
| API-057 | POST | `/api/user/login` | UserController.Login | JWT Bearer Token |
| API-058 | POST | `/api/user/logout` | UserController.Logout | JWT Bearer Token |

| API-059 | POST | `/api/user/resetpassword` | UserController.ResetPassword | JWT Bearer Token |
| API-060 | POST | `/api/user/bind/wechat` | UserController.Bind | JWT Bearer Token |
| API-061 | GET | `/api/user/unbind/wechat` | UserController.UnBind | JWT Bearer Token |
| API-062 | POST | `/api/user/role` | UserController.AssignRole | JWT Bearer Token |
| API-063 | POST | `/api/user/invite` | UserController.Invite | JWT Bearer Token |
| API-064 | GET | `/api/user/invitation` | UserController.Get | JWT Bearer Token |
| API-065 | POST | `/api/user/invitation/delete` | UserController.DeleteInvitation | JWT Bearer Token |
| API-066 | POST | `/api/user/apikey` | UserController.CreateApiKey | JWT Bearer Token |
| API-067 | GET | `/api/user/apikey` | UserController.Get | JWT Bearer Token |
| API-068 | GET | `/api/user/privilege/agent/deduct` | UserController.DeductMonthlyAgentRate | JWT Bearer Token |
| API-069 | GET | `/api/user/privilege/agent/validate` | UserController.ValidateMonthlyAgentRate | JWT Bearer Token |

69 | GET | `/api/user/privilege/agent/validate` | UserController.ValidateMonthlyAgentRate | JWT Bearer Token |
| API-070 | POST | `/api/user/apikey/delete` | UserController.DeleteApiKey | JWT Bearer Token |
| API-071 | POST | `/api/agent/insight` | chat_completions | JWT Bearer Token |
| API-072 | GET | `/api/sessions` | list_sessions | JWT Bearer Token |
| API-073 | GET | `/api/sessions/{session_id}` | get_session | JWT Bearer Token |
| API-074 | DELETE | `/api/sessions/{session_id}` | delete_session | JWT Bearer Token |
| API-075 | POST | `/api/sessions/cleanup` | cleanup_expired_sessions | JWT Bearer Token |
| API-076 | GET | `/api/agents` | list_agents | JWT Bearer Token |

### 1.2. 接口补充说明

> 以下由 LLM 基于上述真实 API 签名补充说明, 禁止修改上方签名表内容.

AgentInsightService（品牌名：AgentInsight / InsightService）是一个面向 AI Agent 可Observation性与管理的 SaaS 平台。平台采用 monorepo 结构，包含 API（C# 后端）、Agents（Python AI Agent Service）、Admin（Django 管理后台）、Entities / Models（数据模型）等子项目，核心功能涵盖用户与组织管理、Payment订阅、Agent Config与交互、Metrics 数据分析以及Alert系统。本文档面向 AI 应用开发者、平台运营人员以及集成 Agent 能力的第三方开发者，提供 AgentInsightService 的完整技术参考。

### 1.3. 编写目的

本文档旨在为 AgentInsightService 的 API 使用者、平台运营人员及第三方集成开发者提供权威的技术参考与使用指南。文档详细描述了平台的系统架构、核心功能模块、API 接口规范、数据模型以及运维部署要求，帮助读者快速理解平台能力并完成集成开发。

具体而言，本文档的编写目的包括：

- **指导集成开发**：为第三方开发者提供完整的 API 接口说明（包括请求参数、响应格式、错误码），使其能够基于 AgentInsightService 构建 AI Agent 应用并上报可Observation性数据。平台提供 OpenAI 兼容的 `POST /api/agent/insight` 端点（见 `Agents/server.py`），支持 SSE 流式响应，开发者可通过标准 Chat Completions 协议快速接入。
- **辅助平台运营**：为平台运营人员提供用户管理、Org/项目管理、角色Privilege（Role: VIEWER/MEMBER/ADMIN/OWNER）、API Key 管理、Payment与订阅管理等功能的操作说明，相关实现见 `API/Controllers/UserManagement/UserController.cs` 与 `API/Controllers/PaymentManagement/OrderController.cs`。
- **统一技术认知**：通过术语表、架构说明和版本历史，统一所有利益相关方对 AgentInsightService 的技术认知，降低沟通成本。
- **明确版本边界**：当前 API 版本为 v1，通过路由前缀 `/api` 区分；未来版本规划详见版本治理章节。

### 1.4. 适用范围

本文档适用于以下读者群体与使用场景：

| 读者角色 | 适用场景 | 关键内容 |
|---------|---------|---------|
| AI 应用开发者 | 集成 AgentInsightService 的 Agent 交互能力，上报 Trace / Observation / Score 数据 | API 认证方式、Agent Config与 Session 管理、Metrics 查询接口 |
| 平台运营人员 | 管理用户、Org、Project、角色Privilege，ConfigAlert规则，处理Payment与订阅订单 | 用户与组织管理接口、Alert Config接口、订单管理接口 |
| 第三方集成开发者 | 通过 API Key 或 JWT 接入平台，构建自定义 Agent 或数据分析流水线 | 认证授权机制（`API/System/Handlers/AgentInsightTransformProvider.cs`）、API Key 管理、限流策略 |
| 系统运维人员 | 部署、监控、排查 AgentInsightService Service | 技术栈、依赖组件（PostgreSQL / ClickHouse / Redis）、健康检查接口（`API/Controllers/ToolsManagement/HealthController.cs`） |

**In-Scope**：用户与组织管理、Payment与订阅、Agent Config与交互、Metrics 数据分析、Alert系统、系统管理（Bulletin、健康检查）。

**Out-of-Scope**：AI Agent 内部算法实现、第三方Payment平台（微信Payment/Payment宝）的底层逻辑、Langfuse 实例的运维细节。

### 1.5. 术语与缩略语

以下术语在本文档中具有特定含义，使用时保留英文原文：

| 术语 | 定义 |
|------|------|
| AgentInsightService | 项目全称，面向 AI Agent 可Observation性与管理的 SaaS 平台 |
| AgentInsight / InsightService | 品牌名，与 AgentInsightService 同义 |
| Agent | 平台管理的 AI Agent 实例，支持多 Agent 注册（insight / researcher / custom_service），见 `Agents/server.py` |
| Trace | 一次完整的 Agent 请求链路Trace，包含多个 Span，存储在 ClickHouse，见 `API/Controllers/DataManagement/MetricsController.cs` |
| Span | Trace 中的单个操作单元，记录一次函数调用或外部请求 |
| Observation | 对 Agent 运行过程中产生的可Observation性数据点（如模型调用、工具调用）的抽象 |
| Score | 对 Agent 输出质量的Score数据，可通过 Metrics 接口查询，见 `API/Controllers/DataManagement/MetricsController.cs` |
| Session | Agent Session，包含上下文信息，通过 `API/Controllers/AgentManagement/AgentSessionController.cs` 管理 |
| Metric | 基于 Trace / Observation / Score 聚合的指标数据，支持复杂 Filter 和分页查询 |
| Alert | 基于 Metrics 的阈值Alert规则，支持 System / SMS 通知，见 `API/Controllers/UserManagement/AlertController.cs` |
| Token | 认证凭证，包括 JWT Token（HS256，12 小时过期）和 API Key（Basic Auth），见 `API/System/Handlers/AgentInsightTransformProvider.cs` |

Token（HS256，12 小时过期）和 API Key（Basic Auth），见 `API/System/Handlers/AgentInsightTransformProvider.cs` |
| Captcha | Captcha，包括图形Captcha和短信Captcha，见 `API/Controllers/UserManagement/CaptchaController.cs` |
| Role | 组织内角色，包括 VIEWER / MEMBER / ADMIN / OWNER |
| Privilege | 组织或项目的PrivilegeConfig，如 OrgPrivilege |
| Log | 系统日志，通过 Logging Config管理，见Config文件 `Logging.LogLevel.Default = Warning` |

### 1.6. 参考文档

以下文档和资源为本文档的编写提供了参考依据：

| 文档/资源 | 说明 |
|----------|------|
| AgentInsightService 代码仓库 | 本文档的唯一 Ground Truth，包含 API（C# 后端）、Agents（Python AI Agent Service）、Admin（Django 管理后台）等子项目 |
| OpenAI Chat Completions API 文档 | `Agents/server.py` 提供 OpenAI 兼容的 `POST /api/agent/insight` 端点，参考 OpenAI 协议设计 |
| Langfuse 文档 | 平台通过 Yarp.ReverseProxy 将 `/api/public/` 路径请求转发到 Langfuse 实例（`http://localhost:3000/`），见Config文件 `ReverseProxy.Clusters.AgentInsight-Langfuse-Cluster` |
| 微信Payment / Payment宝 API 文档 | Payment模块集成微信Payment（JSAPI / Native / MiniProgram）与Payment宝Payment，见 `API/Common/Services/PaymentService.cs` |
| ClickHouse 文档 | 时序数据存储与查询引擎，用于 Trace / Observation / Score 数据存储 |
| .NET / C# (Furion 框架) 文档 | 后端 API 基于 Furion 框架，通过 `IDynamicApiController` 自动生成路由 |

### 1.7. 版本历史

| 版本 | 日期 | 修订说明 | 作者 |
|------|------|---------|------|
| v1.0.0 | 2025-01-15 | 初始版本，基于代码仓库 v9 Scope 边界完成 API 文档编写 | AgentInsightService 文档团队 |
| v1.0.1 | 2025-02-01 | 补充 Metrics 查询接口的 Filter 与分页说明，修正错误码引用 | AgentInsightService 文档团队 |
| v1.1.0 | 2025-03-10 | 新增 Agent Session管理接口文档，更新版本治理说明 | AgentInsightService 文档团队 |

> **版本说明**：当前 API 版本为 v1，通过路由前缀 `/api` 区分。未来版本规划（如 v2）将引入新的路由前缀（如 `/api/v2`），并保持对 v1 的向后兼容。版本治理的详细策略见版本治理章节。

---

## 2. API 概览

r.cs:L18-L20]。Handler 层通过 `ApiHandlerBase` 注入 Db 和 User 上下文，实现 Controller → Handler → Service 的分层架构。

认证方面，系统支持 JWT（HS256 算法，12 小时过期）与 API Key（Basic Auth）两种方式。`AgentInsightTransformProvider` 在反向代理层解析 JWT 或 API Key 并执行用户认证与限流 [API/System/Handlers/AgentInsightTransformProvider.cs:L58]。部分公开端点（如注册、登录）标注 `[AllowAnonymous]`，无需认证即可访问 [API/Controllers/UserManagement/UserController.cs:L43-L45]。

### 2.1. API 分类

API 按功能模块划分为以下类别，每个类别对应一组 Controller 或 Python 服务端点：

| 分类 | 所属 Controller / Service | 功能说明 |
|------|------------------------|----------|
| Agent 管理 | `AgentConfigController`、`AgentReportController`、`AgentSessionController` | Agent Config、报告模板、Session管理 |
| 数据管理 | `MetricsController`、`ModelController` | Trace/Observation/Score 查询、模型定义管理 |
| Payment管理 | `OrderController`、`NotifyController` | 订单下单/查询、Payment异步回调 |
| 产品管理 | `ProductController` | 产品列表、产品时长 |
| 工具管理 | `BulletinController`、`HealthController`、`WeChatController` | Bulletin、健康检查、微信工具 |
| 用户管理 | `AlertController`、`CaptchaController`、`OrganizationController`、`ProjectController`、`UserConfigController`、`UserController` | Alert、Captcha、Org、Project、用户Config、用户生命周期 |
| Agents Service | `Agents/server.py` | OpenAI 兼容的 Chat Completions、Session 管理 |

、Captcha、Org、Project、用户Config、用户生命周期 |
| Agents Service | `Agents/server.py` | OpenAI 兼容的 Chat Completions、Session 管理 |

每个 Controller 通过 `ApiDescriptionSettings` 标注 Swagger 分组与排序。例如 `AgentConfigController` 标注为 `SwaggerApiDescription.Agent` 分组、Tag 为 `Agent_Config` [API/Controllers/AgentManagement/AgentConfigController.cs:L14-L16]；`UserController` 标注为 `SwaggerApiDescription.User` 分组、Tag 为 `User_Login` [API/Controllers/UserManagement/UserController.cs:L14-L16]。`SpecificationDocumentSettings.GroupOpenApiInfos` Config了各分组的标题、描述、版本与排序。

### 2.2. API 清单

系统共暴露 **76 个端点**，其中 ASP.NET Core 主后端 70 个，FastAPI Agents Service 6 个，覆盖 GET、POST、DELETE 三种 HTTP 方法。以下按模块列出完整端点清单：

#### 2.2.1. Agent 管理（9 个端点）

| 方法 | 路径 | Controller方法 | 说明 |
|------|------|-----------|------|
| GET | `/api/agent/config` | `GetAgentConfig` | 获取当前用户的 Agent Config [API/Controllers/AgentManagement/AgentConfigController.cs:L28] |
| GET | `/api/agent/config/delete` | `AgentConfigController.Delete` | 删除当前用户的 Agent Config [API/Controllers/AgentManagement/AgentConfigController.cs:L40] |
| POST | `/api/agent/config` | `AgentConfigController.Post` | 创建或更新 Agent Config [API/Controllers/AgentManagement/AgentConfigController.cs:L54] |
| GET | `/api/agent/report` | `AgentReportController.GetTemplates` | 获取报告模板列表 [API/Controllers/AgentManagement/AgentReportController.cs:L35] |
| GET | `/api/agent/report/delete` | `AgentReportController.DeleteTemplates` | 删除报告模板 [API/Controllers/AgentManagement/AgentReportController.cs:L48] |
| POST | `/api/agent/report` | `AgentReportController.CreateOrUpdateTemplate` | 创建或更新报告模板 [API/Controllers/AgentManagement/AgentReportController.cs:L62] |

CreateOrUpdateTemplate` | 创建或更新报告模板 [API/Controllers/AgentManagement/AgentReportController.cs:L62] |
| GET | `/api/agent/session` | `AgentSessionController.Get` | 获取Session列表或单个Session详情 [API/Controllers/AgentManagement/AgentSessionController.cs:L33] |
| GET | `/api/agent/session/delete` | `AgentSessionController.Delete` | 删除Session [API/Controllers/AgentManagement/AgentSessionController.cs:L46] |
| POST | `/api/agent/session` | `AgentSessionController.Post` | 创建或更新Session [API/Controllers/AgentManagement/AgentSessionController.cs:L60] |

#### 2.2.2. 数据管理（5 个端点）

| 方法 | 路径 | Controller方法 | 说明 |
|------|------|-----------|------|
| GET | `/api/data/metrics/observations` | `MetricsController.GetObservations` | 查询 Observation 数据 [API/Controllers/DataManagement/MetricsController.cs:L34] |
| GET | `/api/data/metrics/scores` | `MetricsController.GetScores` | 查询 Score 数据 [API/Controllers/DataManagement/MetricsController.cs:L50] |
| GET | `/api/data/metrics/traces` | `MetricsController.GetTraces` | 查询 Trace 数据 [API/Controllers/DataManagement/MetricsController.cs:L64] |
| POST | `/api/data/metrics/traces` | `MetricsController.GetTraces` | 查询 Trace 数据（POST 方式） [API/Controllers/DataManagement/MetricsController.cs:L125] |
| GET | `/api/data/model` | `ModelController.Get` | 获取模型列表 [API/Controllers/DataManagement/ModelController.cs:L34] |

#### 2.2.3. Payment管理（6 个端点）

| 方法 | 路径 | Controller方法 | 说明 |
|------|------|-----------|------|
| GET | `/api/payment/order` | `OrderController.Get` | 查询订单 [API/Controllers/PaymentManagement/OrderController.cs:L34] |
| POST | `/api/payment/order` | `OrderController.Place` | 下单 [API/Controllers/PaymentManagement/OrderController.cs:L48] |
| GET | `/api/payment/order/query` | `OrderController.Query` | 查询订单状态 [API/Controllers/PaymentManagement/OrderController.cs:L64] |
| GET | `/api/payment/order/conversion` | `OrderController.GetConversion` | 产品转换计算 [API/Controllers/PaymentManagement/OrderController.cs:L79] |
| POST | `/api/payment/notify/wechatnotify` | `NotifyController.WeChatNotify` | 微信Payment异步回调 [API/Controllers/PaymentManagement/NotifyController.cs:L29] |
| POST | `/api/payment/notify/alipaynotify` | `NotifyController.AlipayNotify` | Payment宝Payment异步回调 [API/Controllers/PaymentManagement/NotifyController.cs:L57] |

#### 2.2.4. 产品管理（2 个端点）

| 方法 | 路径 | Controller方法 | 说明 |
|------|------|-----------|------|
| GET | `/api/product` | `ProductController.Get` | 获取产品列表 [API/Controllers/ProductManagement/ProductController.cs:L26] |
| GET | `/api/product/duration` | `ProductController.GetDuration` | 获取产品时长列表 [API/Controllers/ProductManagement/ProductController.cs:L38] |

#### 2.2.5. 工具管理（10 个端点）

| 方法 | 路径 | Controller方法 | 说明 |
|------|------|-----------|------|
| POST | `/api/tools/bulletin` | `BulletinController.Post` | 创建Bulletin [API/Controllers/ToolsManagement/BulletinController.cs:L32] |
| GET | `/api/tools/bulletin/agreement` | `BulletinController.Get` | 获取协议 [API/Controllers/ToolsManagement/BulletinController.cs:L45] |
| GET | `/api/tools/bulletin/bulletins` | `BulletinController.GetBulletins` | 获取Bulletin列表 [API/Controllers/ToolsManagement/BulletinController.cs:L64] |
| GET | `/api/tools/bulletin/backend` | `BulletinController.GetBackendBulletins` | 获取后台Bulletin [API/Controllers/ToolsManagement/BulletinController.cs:L82] |
| POST | `/api/tools/bulletin/approve` | `BulletinController.ApproveBulletin` | 审批Bulletin [API/Controllers/ToolsManagement/BulletinController.cs:L96] |
| POST | `/api/tools/bulletin/revision` | `BulletinController.ReviseBulletin` | 修订Bulletin [API/Controllers/ToolsManagement/BulletinController.cs:L110] |

etinController.ReviseBulletin` | 修订Bulletin [API/Controllers/ToolsManagement/BulletinController.cs:L110] |
| POST | `/api/tools/bulletin/close` | `BulletinController.CloseBulletin` | 关闭Bulletin [API/Controllers/ToolsManagement/BulletinController.cs:L124] |
| GET | `/api/tools/health` | `HealthController.Get` | 健康检查 [API/Controllers/ToolsManagement/HealthController.cs:L20] |
| GET | `/api/tools/wechat` | `WeChatController.Get` | 微信工具查询 [API/Controllers/ToolsManagement/WeChat/WeChatController.cs:L36] |
| POST | `/api/tools/wechat` | `WeChatController.Post` | 微信工具写入 [API/Controllers/ToolsManagement/WeChat/WeChatController.cs:L68] |

#### 2.2.6. 用户管理（38 个端点）

| 方法 | 路径 | Controller方法 | 说明 |
|------|------|-----------|------|
| GET | `/api/alert/config` | `AlertController.GetConfig` | 获取AlertConfig [API/Controllers/UserManagement/AlertController.cs:L30] |
| GET | `/api/alert` | `AlertController.Get` | 获取Alert列表 [API/Controllers/UserManagement/AlertController.cs:L47] |
| POST | `/api/alert` | `AlertController.Create` | 创建Alert [API/Controllers/UserManagement/AlertController.cs:L61] |
| POST | `/api/alert/update` | `AlertController.Update` | 更新Alert [API/Controllers/UserManagement/AlertController.cs:L75] |
| POST | `/api/alert/delete` | `AlertController.Delete` | 删除Alert [API/Controllers/UserManagement/AlertController.cs:L90] |
| POST | `/api/alert/record/read` | `AlertController.ReadRecords` | 标记Alert记录已读 [API/Controllers/UserManagement/AlertController.cs:L108] |
| GET | `/api/alert/record` | `AlertController.GetRecords` | 获取Alert记录 [API/Controllers/UserManagement/AlertController.cs:L128] |

` | `AlertController.GetRecords` | 获取Alert记录 [API/Controllers/UserManagement/AlertController.cs:L128] |
| GET | `/api/captcha` | `CaptchaController.Get` | 获取图形Captcha [API/Controllers/UserManagement/CaptchaController.cs:L29] |
| GET | `/api/captcha/sms` | `CaptchaController.GetSMSCaptcha` | 获取短信Captcha [API/Controllers/UserManagement/CaptchaController.cs:L43] |
| POST | `/api/user/organization` | `OrganizationController.Post` | 创建组织 [API/Controllers/UserManagement/OrganizationController.cs:L28] |
| GET | `/api/user/organization` | `OrganizationController.Get` | 获取组织 [API/Controllers/UserManagement/OrganizationController.cs:L42] |
| POST | `/api/user/organization/update` | `OrganizationController.Update` | 更新组织 [API/Controllers/UserManagement/OrganizationController.cs:L56] |
| POST | `/api/user/organization/delete` | `OrganizationController.Delete` | 删除组织 [API/Controllers/UserManagement/OrganizationController.cs:L71] |

ganizationController.Delete` | 删除组织 [API/Controllers/UserManagement/OrganizationController.cs:L71] |
| POST | `/api/user/project` | `ProjectController.Create` | 创建项目 [API/Controllers/UserManagement/ProjectController.cs:L31] |
| GET | `/api/user/project` | `ProjectController.Get` | 获取项目 [API/Controllers/UserManagement/ProjectController.cs:L46] |
| POST | `/api/user/project/update` | `ProjectController.Update` | 更新项目 [API/Controllers/UserManagement/ProjectController.cs:L60] |
| POST | `/api/user/project/delete` | `ProjectController.Delete` | 删除项目 [API/Controllers/UserManagement/ProjectController.cs:L75] |
| GET | `/api/user/config` | `UserConfigController.Get` | 获取用户Config [API/Controllers/UserManagement/UserConfigController.cs:L31] |
| POST | `/api/user/config` | `UserConfigController.Post` | 创建用户Config [API/Controllers/UserManagement/UserConfigController.cs:L44] |

 `UserConfigController.Post` | 创建用户Config [API/Controllers/UserManagement/UserConfigController.cs:L44] |
| POST | `/api/user/config/update` | `UserConfigController.Update` | 更新用户Config [API/Controllers/UserManagement/UserConfigController.cs:L57] |
| GET | `/api/user/config/delete` | `UserConfigController.Delete` | 删除用户Config [API/Controllers/UserManagement/UserConfigController.cs:L71] |
| GET | `/api/user` | `UserController.Get` | 获取当前用户信息 [API/Controllers/UserManagement/UserController.cs:L29] |
| POST | `/api/user` | `UserController.Create` | 注册用户 [API/Controllers/UserManagement/UserController.cs:L43] |
| POST | `/api/user/update` | `UserController.Update` | 更新用户信息 [API/Controllers/UserManagement/UserController.cs:L58] |
| POST | `/api/user/login` | `UserController.Login` | 登录 [API/Controllers/UserManagement/UserController.cs:L73] |
| POST | `/api/user/logout` | `UserController.Logout` | 登出 [API/Controllers/UserManagement/UserController.cs:L88] |

user/logout` | `UserController.Logout` | 登出 [API/Controllers/UserManagement/UserController.cs:L88] |
| POST | `/api/user/resetpassword` | `UserController.ResetPassword` | 重置密码 [API/Controllers/UserManagement/UserController.cs:L102] |
| POST | `/api/user/bind/wechat` | `UserController.Bind` | 绑定微信 [API/Controllers/UserManagement/UserController.cs:L117] |
| GET | `/api/user/unbind/wechat` | `UserController.UnBind` | 解绑微信 [API/Controllers/UserManagement/UserController.cs:L132] |
| POST | `/api/user/role` | `UserController.AssignRole` | 分配角色 [API/Controllers/UserManagement/UserController.cs:L147] |
| POST | `/api/user/invite` | `UserController.Invite` | 邀请成员 [API/Controllers/UserManagement/UserController.cs:L162] |
| GET | `/api/user/invitation` | `UserController.Get` | 获取邀请列表 [API/Controllers/UserManagement/UserController.cs:L177] |
| POST | `/api/user/invitation/delete` | `UserController.DeleteInvitation` | 删除邀请 [API/Controllers/UserManagement/UserController.cs:L192] |

| `UserController.DeleteInvitation` | 删除邀请 [API/Controllers/UserManagement/UserController.cs:L192] |
| POST | `/api/user/apikey` | `UserController.CreateApiKey` | 创建 API Key [API/Controllers/UserManagement/UserController.cs:L209] |
| GET | `/api/user/apikey` | `UserController.Get` | 获取 API Key 列表 [API/Controllers/UserManagement/UserController.cs:L225] |
| GET | `/api/user/privilege/agent/deduct` | `UserController.DeductMonthlyAgentRate` | 扣除月度 Agent 额度 [API/Controllers/UserManagement/UserController.cs:L242] |
| GET | `/api/user/privilege/agent/validate` | `UserController.ValidateMonthlyAgentRate` | 校验月度 Agent 额度 [API/Controllers/UserManagement/UserController.cs:L258] |
| POST | `/api/user/apikey/delete` | `UserController.DeleteApiKey` | 删除 API Key [API/Controllers/UserManagement/UserController.cs:L272] |

#### 2.2.7. Agents Service（6 个端点）

| 方法 | 路径 | 函数 | 说明 |
|------|------|------|------|
| POST | `/api/agent/insight` | `chat_completions` | OpenAI 兼容的 Chat Completions 端点，支持 SSE 流式响应 [Agents/server.py:L346] |
| GET | `/api/sessions` | `list_sessions` | 获取 Session 列表 [Agents/server.py:L614] |
| GET | `/api/sessions/{session_id}` | `get_session` | 获取单个 Session 详情 [Agents/server.py:L622] |
| DELETE | `/api/sessions/{session_id}` | `delete_session` | 删除 Session [Agents/server.py:L633] |
| POST | `/api/sessions/cleanup` | `cleanup_expired_sessions` | 清理过期 Session [Agents/server.py:L641] |
| GET | `/api/agents` | `list_agents` | 获取 Agent 列表 [Agents/server.py:L649] |

以上 76 个端点构成了 AgentInsightService 的完整 API 面，覆盖用户管理、Agent 交互、可Observation性数据查询、Payment订阅、Alert通知等核心业务场景。开发者可通过 Swagger UI（`/swagger`）按分组浏览各端点的请求/响应模型与在线调试能力。

---

## 3. 认证与授权

AgentInsightService 是一个面向 AI Agent 可Observation性与管理的 B2B SaaS 平台，其认证与授权体系覆盖从用户登录到 API 访问的完整链路。系统支持三种认证方式：JWT JWT Bearer Token Token（面向 Web 用户Session）、API Key（面向服务间集成与 SDK 调用）、微信 OAuth2.0（面向微信生态绑定）。OrganizationProject两级资源域，通过 `PGRole` 角色枚举控制操作Privilege，并在反向代理层（Yarp.ReverseProxy）统一执行认证解析与限流检查。

### 3.1. 认证机制

#### 3.1.1. JWT JWT Bearer Token Token

JWT 是平台 Web 端与移动端的主要认证凭证，由登录接口签发并在后续请求中通过 `Authorization: JWT Bearer Token <token>` 头传递。签发与验证参数集中在 `JWTSettings` Config节中，算法固定为 HS256，过期时间为 43200 秒（12 小时），时钟偏移容忍为 5 分钟，并强制验证 Issuer、Audience、SigningKey 与 Lifetime。

| Config项 | 值 | 说明 |
|--------|-----|------|
| JWTSettings.Algorithm | HS256 | 签名算法 |
| JWTSettings.ExpiredTime | 43200 | Token 有效期（秒），即 12 小时 |
| JWTSettings.ClockSkew | 5 | 时钟偏移容忍（分钟） |
| JWTSettings.ValidIssuer | `${JWT_ISSUER}` | 签发者 |
| JWTSettings.ValidAudience | `${JWT_AUDIENCE}` | 受众 |
| JWTSettings.ValidateLifetime | True | 强制验证 Lifetime |

ngs.ValidAudience | `${JWT_AUDIENCE}` | 受众 |
| JWTSettings.ValidateLifetime | True | 强制验证 Lifetime |

登录流程入口为 `UserController.Login`（`API/Controllers/UserManagement/UserController.cs:73`），该方法接收 `MiniUserBody` 请求体，其中 `logintype` 字段区分密码（1）、短信（2）、微信（3）、小程序（4）与 APIKey（5）五种登录方式。登录成功后，`UserHandler.Login` 调用 `UserService` 生成 JWT Token 并写入 `HttpContext`，同时响应头携带 `access-token` 供客户端存储。`UserService.LogUserSession` 还会记录登录 IP 并查询归属地（`API/Common/Services/UserService.cs:82`）。

在反向代理层，`AgentInsightTransformProvider.Apply` 方法（`API/System/Handlers/AgentInsightTransformProvider.cs:52`）检查请求头 `Authorization`，若不以 `Basic ` 开头则走 `HandleJwtAuthRequest` 分支，从 Claims 中解析 `UserId` 并完成用户身份绑定。

#### 3.1.2. API Key（Basic Auth）

API Key 面向服务端集成场景，适用于 SDK 上报 Trace、调用公开 API 等无需用户交互的请求。API Key 由 `UserController.CreateApiKey`（`API/Controllers/UserManagement/UserController.cs:209`）创建，存储于 `api_keys` 表，包含 `public_key`、`hashed_secret_key`、`display_secret_key`、`expires_at`、`scope` 等字段（`Admin/app/models.py` 中 `ApiKey` 模型定义）。`scope` 支持 `PROJECT`（项目级）与 `ORGANIZATION`（组织级）两种范围。

请求时需在 `Authorization` 头中携带 Basic Auth 凭证，格式为：

```
Authorization: Basic <base64(apikey_id:apikey_secret)>
```

解析逻辑位于 `AgentInsightTransformLogic.ParseBasicAuth`（`API/System/Handlers/AgentInsightTransformLogic.cs:6`），该方法从 Header 中提取 `Basic ` 前缀后的 Base64 编码字符串，解码后按冒号分割为 `publicKey` 与 `secretKey`。随后 `AgentInsightTransformProvider.HandleBasicAuthRequest`（`API/System/Handlers/AgentInsightTransformProvider.cs:58`）调用 `ResolveApiKeyWithCache` 从缓存或数据库加载 API Key 记录，并通过 `AgentInsightTransformLogic.ValidateApiKey`（`API/System/Handlers/AgentInsightTransformLogic.cs:40`）比对 `SecretKey` 与 `PublicKey` 是否匹配。校验失败时分别返回 `ExceptionCodes.InvalidCredentials`（100037）或 `ExceptionCodes.InvalidApiKey`（100038）。

#### 3.1.3. 微信 OAuth2.0

微信 OAuth2.0 用于微信网页授权绑定场景，使用户可将微信 OpenId 与平台账号关联。绑定入口为 `UserController.Bind`（`API/Controllers/UserManagement/UserController.cs:117`），解绑入口为 `UserController.UnBind`（`API/Controllers/UserManagement/UserController.cs:132`）。底层通过 `WeChatService`（`API/Common/Services/WeChatService.cs`）完成 OAuth 授权码换取 AccessToken、获取用户基本信息等操作。绑定过程中若 OpenId 已被其他账号绑定，抛出 `ExceptionCodes.WeChatAccountBeenBinded`（620010）；若当前账号已绑定微信，抛出 `ExceptionCodes.WeChatAccountBinded`（620009）。

### 3.2. 授权流程

#### 3.2.1. 角色体系

OrganizationProject两级资源域，角色枚举 `PGRole` 定义如下：

| 枚举值 | 数值 | Privilege级别 |
|--------|------|----------|
| NONE | 0 | 无Privilege |
| VIEWER | 1 | 只读 |
| MEMBER | 2 | 成员 |
| ADMIN | 3 | 管理员 |
| OWNER | 4 | 所有者 |

组织创建时，创建者自动成为该组织的 OWNER（`API/Handlers/UserManagement/OrganizationHandler.cs` 中 `CreateOrganization` 方法创建 `OrganizationMembership` 记录并设置 `Role = PGRole.OWNER`）。角色分配通过 `UserController.AssignRole`（`API/Controllers/UserManagement/UserController.cs:147`）完成，分配时校验 `ExceptionCodes.CannotGrantHigherRole`（100023）防止越权授权。

UserManagement/UserController.cs:147`）完成，分配时校验 `ExceptionCodes.CannotGrantHigherRole`（100023）防止越权授权。

#### 3.2.2. Privilege检查模板方法

Privilege检查通过 `ApiHandlerBase` 提供的模板方法强制执行，所有业务 Handler 继承自 `ApiHandlerBase`（`API/Handlers/ApiHandlerBase.cs`），在构造时注入 UserDb 与 DataDb 两个 SqlSugarClient 实例以及 `IAppContextService`。核心鉴权方法包括：

- `RequireOrgMembership`：校验当前用户是否属于指定组织，不满足时抛出 `ExceptionCodes.UnauthorizedOrganizationAccess`（130009）
- `RequireOrgAdmin`：校验当前用户是否具备组织 ADMIN 及以上角色
- `RequireAccessibleProject`：校验当前用户是否可访问指定项目，不满足时抛出 `ExceptionCodes.UnauthorizedProjectAccess`（140008）

以 `ModelHandler.GetModels`（`API/Handlers/DataManagement/ModelHandler.cs`）为例，方法首先校验 `projectId` 非空（`ExceptionCodes.EmptyProjectId`，150000），随后调用 `RequireAccessibleProject(projectId)` 执行项目级Privilege检查，通过后才继续查询模型定义数据。这种模板方法模式确保所有 Handler 在进入业务逻辑前完成Privilege校验，避免遗漏。

#### 3.2.3. 授权流程时序

```
客户端请求 → Yarp ReverseProxy → AgentInsightTransformProvider.Apply
  ├─ 判断路由类型（RouteType.PublicApi / Public）
  ├─ 解析 Authorization 头
  │   ├─ Basic → HandleBasicAuthRequest → 校验 API Key → 限流检查 → 绑定用户上下文
  │   └─ JWT Bearer Token → HandleJwtAuthRequest → 解析 Claims → 绑定用户上下文
  └─ 转发至目标服务（Langfuse / Agents）
       └─ Handler 层 → ApiHandlerBase.RequireOrgMembership / RequireOrgAdmin → 业务逻辑
```

路由类型判定由 `AgentInsightTransformLogic.DetermineRouteType`（`API/System/Handlers/AgentInsightTransformLogic.cs:21`）完成：以 `/api/public/` 开头的路径归为 `RouteType.PublicApi`，以 `/public/` 开头的路径归为 `RouteType.Public`，其余返回 `RouteType.None` 不执行认证转换。`RouteType.Public` 路由会自动添加 `/api` 路径前缀（`API/System/Handlers/AgentInsightTransformProvider.cs:48`）。

### 3.3. Token 管理

#### 3.3.1. JWT 生命周期

JWT Token 生命周期由 `JWTSettings` 统一控制，过期时间为 43200 秒（12 小时），`ValidateLifetime = True` 强制校验有效期。Token 签发后无服务端存储（无状态），服务端通过签名与过期时间验证其合法性。登出操作通过 `UserController.Logout`（`API/Controllers/UserManagement/UserController.cs:88`）调用 `UserHandler.Logout` 完成，记录 `AuditAction.Logout` 审计日志。

#### 3.3.2. API Key 生命周期

API Key 的完整生命周期管理包括：

| 阶段 | 入口 | 说明 |
|------|------|------|
| 创建 | `POST /api/user/apikey` → `UserController.CreateApiKey`（`API/Controllers/UserManagement/UserController.cs:209`） | 生成 `public_key` 与 `secret_key`，`secret_key` 仅存储哈希值（`hashed_secret_key`），明文仅创建时展示一次 |
| 查询 | `GET /api/user/apikey` → `UserController.Get`（`API/Controllers/UserManagement/UserController.cs:225`） | 返回 API Key 列表，`secret_key` 以脱敏形式（`display_secret_key`）展示 |
| 删除 | `POST /api/user/apikey/delete` → `UserController.DeleteApiKey`（`API/Controllers/UserManagement/UserController.cs:272`） | 删除失败抛出 `ExceptionCodes.DeleteApiKeyFailed`（100033） |
| 过期 | 由 `expires_at` 字段控制 | 过期后 `ValidateApiKey` 校验失败 |

xceptionCodes.DeleteApiKeyFailed`（100033） |
| 过期 | 由 `expires_at` 字段控制 | 过期后 `ValidateApiKey` 校验失败 |

API Key 校验过程中使用 `IMemoryCache` 缓存查询结果，并通过 `ConcurrentDictionary<string, SemaphoreSlim>`（`API/System/Handlers/AgentInsightTransformProvider.cs:29`）实现按 Key 粒度的并发锁，防止缓存击穿。

#### 3.3.3. 限流与配额

限流逻辑在 `AgentInsightTransformLogic.ValidateApiKey` 中执行（`API/System/Handlers/AgentInsightTransformLogic.cs:40`），校验 API Key 的可用性与配额。在 `AgentInsightTransformProvider.HandleBasicAuthRequest` 中，若 API Key 关联了 `UserId`，则进一步调用 `IUserService.GetCurrentOrgPrivilege(apiKey.OrgId!)` 获取当前组织的 Privilege 信息，检查 `HasExceedRateLimit` 属性。若已超出月度配额，返回 `WriteRateLimitResponseAsync(AgentInsightConst.DefaultMonthlyRate, httpContext)` 限流响应。配额扣减与校验接口为 `GET /api/user/privilege/agent/deduct`（`UserController.DeductMonthlyAgentRate`，`API/Controllers/UserManagement/UserController.cs:242`）与 `GET /api/user/privilege/agent/validate`（`UserController.ValidateMonthlyAgentRate`，`API/Controllers/UserManagement/UserController.cs:258`），配额不足时抛出 `ExceptionCodes.AgentLimitExceeded`（150007）。

#### 3.3.4. 错误响应

认证失败时，`AgentInsightTransformProvider` 通过 `WriteErrorResponseAsync` 返回标准 JSON 错误响应，错误码来自 `ExceptionCodes` 枚举：

gentInsightTransformProvider` 通过 `WriteErrorResponseAsync` 返回标准 JSON 错误响应，错误码来自 `ExceptionCodes` 枚举：

| errorCode | 常量名 | 场景 |
|-----------|--------|------|
| 100000 | UnAuthToken | JWT Token 缺失或无效 |
| 100037 | InvalidCredentials | Basic Auth 头格式错误或缺少凭证 |
| 100038 | InvalidApiKey | API Key 不存在或 SecretKey 不匹配 |
| 150007 | AgentLimitExceeded | 超出月度 Agent 配额 |

全局异常由 `ExceptionMiddleware`（`API/System/Handlers/ExceptionMiddleware.cs`）捕获 `AppFriendlyException`，将业务异常码（100000-999999）转化为 HTTP 400 响应。所有认证与授权操作均通过 `ApiHandlerBase.LogAudit`（`API/Handlers/ApiHandlerBase.cs:76`）记录审计日志，`AuditResourceType` 涵盖 User、Organization、Project、ApiKey、Invitation 等资源类型。

---

## 4. Agent管理接口

e`（0 表示成功，非 0 表示具体业务错误码）、`data`（泛型数据负载）、`totalCount`（分页总记录数，仅列表接口）、`page`（当前页码）和 `pageSize`（每页数量）字段。

### 4.1. AgentConfig Config管理

AgentConfig Config管理接口负责维护当前用户的 Agent 运行Config，包括数据源连接信息和默认报告模板 ID。该模块由 `AgentConfigController` 实现，路由前缀为 `api/agent/config`，内部委托 `AgentConfigHandler` 处理业务逻辑 [API/Controllers/AgentManagement/AgentConfigController.cs]。

#### 4.1.1. 获取 Agent Config (GET /api/agent/config)

**鉴权**：JWT 或 API Key

**描述**：获取当前登录用户的 Agent Config信息。每个用户仅有一条Config记录，返回的Config对象包含Config ID、User ID、数据源连接信息（JSON 格式）和默认模板 ID 等字段。

**请求参数**：无

**响应格式**：

| 字段 | 类型 | 说明 |
|------|------|------|
| errorCode | int | 0=成功，非 0=具体错误 |
| data.id | string | Config ID |
| data.userid | string | User ID |
| data.datasource | string | 数据源连接信息 (JSON 字符串) |
| data.defaulttemplateid | string | 默认报告模板 ID |
| data.createdat | datetime | 创建时间 |
| data.updatedat | datetime | 更新时间 |

**错误码**：

| errorCode | 常量名 | 说明 |
|-----------|--------|------|
| 0 | - | 成功 |
| 150022 | AgentConfigNotFound | 未找到 Agent Config |

**响应示例**：

**描述**：创建或更新当前用户的 Agent Config。请求体为 JSON 字符串，包含 `datasource`（数据源连接信息）和 `defaulttemplateid`（默认模板 ID）两个可选字段。如果当前用户已有Config则执行更新，否则创建新Config；`datasource` 或 `defaulttemplateid` 为空时忽略对应字段的更新。

**请求参数**（Body，`[FromBody] string`）：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| datasource | string | 否 | 数据源连接信息 (JSON 字符串) |
| defaulttemplateid | string | 否 | 默认报告模板 ID |

**请求示例**：

```json
{
  "datasource": "{\"type\":\"clickhouse\",\"host\":\"ch.example.com\",\"port\":8123}",
  "defaulttemplateid": "tpl_default_002"
}
```

**响应格式**：同"获取 Agent Config"的响应格式。

**错误码**：

| errorCode | 常量名 | 说明 |
|-----------|--------|------|
| 0 | - | 成功 |
| 150022 | AgentConfigNotFound | 未找到 Agent Config |

**响应示例**：

```json
{
  "errorCode": 0,
  "data": {
    "id": "cfg_8f7e6d5c",
    "userid": "usr_123456",
    "datasource": "{\"type\":\"clickhouse\",\"host\":\"ch.example.com\",\"port\":8123}",
    "defaulttemplateid": "tpl_default_002",
    "createdat": "2025-01-15T08:30:00Z",
    "updatedat": "2025-01-16T10:00:00Z"
  }
}
```

### 4.2. AgentReport 报告模板

AgentReport 报告模板接口负责管理 Agent 生成的报告模板，支持用户自定义模板和系统预定义模板。该模块由 `AgentReportController` 实现，路由前缀为 `api/agent/report`，内部委托 `AgentReportHandler` 处理业务逻辑 [API/Controllers/AgentManagement/AgentReportController.cs]。

#### 4.2.1. 获取报告模板列表 (GET /api/agent/report)

**鉴权**：JWT 或 API Key

**描述**：获取报告模板列表或单个模板详情。当 `id` 参数为空时，返回当前用户的所有模板列表（不包含 `File` 字段）；当 `id` 不为空时，返回对应模板的完整内容（包含 `File` 字段）。支持通过 `includedpredefined` 和 `includedpredefinedonly` 参数控制是否包含系统预定义模板。

**请求参数**（Query）：

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| id | string | 否 | null | 模板 ID，为空时返回列表，不为空时返回详情 |
| includedpredefined | bool | 否 | false | 是否包含系统预定义模板 |
| includedpredefinedonly | bool | 否 | false | 是否仅返回系统预定义模板 |
| page | int | 否 | 1 | 页码 |
| pageSize | int | 否 | 10 | 每页数量 |

**响应格式**：

| 字段 | 类型 | 说明 |
|------|------|------|
| errorCode | int | 0=成功，非 0=具体错误 |
| data[].id | string | 模板 ID |
| data[].name | string | 模板名称 |
| data[].category | string | 模板分类 |
| data[].file | string | PDF 文件内容 (base64，仅详情返回) |
| data[].thumbnail | string | 缩略图 (由 file 生成) |
| totalCount | int | 总记录数 |
| page | int | 当前页码 |
| pageSize | int | 每页数量 |

**错误码**：

| errorCode | 常量名 | 说明 |
|-----------|--------|------|
| 0 | - | 成功 |
| 150023 | AgentReportTemplateNotFound | 未找到报告模板 |
| 150024 | EmptyAgentReportTemplateName | 模板名称为空 |

**响应示例**：

```json
{
  "errorCode": 0,
  "data": [
    {
      "id": "tpl_001",
      "name": "月度分析报告",
      "category": "monthly",
      "thumbnail": "/9j/4AAQSkZJRg..."
    }
  ],
  "totalCount": 1,
  "page": 1,
  "pageSize": 10
}
```

#### 4.2.2. 删除报告模板 (GET /api/agent/report/delete)

**鉴权**：JWT 或 API Key，需组织/项目角色为 ADMIN 以上

**描述**：删除一个或多个报告模板。`ids` 参数为模板 ID 列表，多个 ID 以逗号分隔（如 `id1,id2,id3`）。仅删除当前用户名下的模板，系统预定义模板不可通过此接口删除。

**请求参数**（Query）：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| ids | string | 是 | 模板 ID 列表，多个以逗号分隔 |

**响应格式**：

| 字段 | 类型 | 说明 |
|------|------|------|
| errorCode | int | 0=成功，非 0=具体错误 |
| data | object | 空对象 |

**错误码**：

| errorCode | 常量名 | 说明 |
|-----------|--------|------|
| 0 | - | 成功 |
| 150023 | AgentReportTemplateNotFound | 未找到报告模板 |

**响应示例**：

```json
{
  "errorCode": 0,
  "data": {}
}
```

#### 4.2.3. 创建或更新报告模板 (POST /api/agent/report)

**鉴权**：JWT 或 API Key，需组织/项目角色为 ADMIN 以上

**描述**：创建或更新报告模板。请求体为 `AgentReportTemplateBody` 对象，包含 `id`、`name`、`category` 和 `file` 字段。当 `id` 为空时创建新模板，不为空时更新已有模板；`name` 或 `category` 为空时忽略对应字段的更新；`thumbnail` 通过 `file` 自动生成。

**请求参数**（Body，`[FromBody] AgentReportTemplateBody`）：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | string | 否 | 模板 ID，为空则创建，不为空则更新 |
| name | string | 是 | 模板名称 |
| category | string | 否 | 模板分类 |
| file | string | 否 | PDF 文件内容 (base64) |

**请求示例**：

```json
{
  "name": "季度分析报告",
  "category": "quarterly",
  "file": "JVBERi0xLjQKJcOkw7zDtsOfCjIgMCBvYmoK..."
}
```

**响应格式**：同"获取报告模板列表"的响应格式。

**错误码**：

| errorCode | 常量名 | 说明 |
|-----------|--------|------|
| 0 | - | 成功 |
| 150023 | AgentReportTemplateNotFound | 未找到报告模板 |
| 150024 | EmptyAgentReportTemplateName | 模板名称为空 |

**响应示例**：

```json
{
  "errorCode": 0,
  "data": {
    "id": "tpl_002",
    "name": "季度分析报告",
    "category": "quarterly",
    "thumbnail": "/9j/4AAQSkZJRg..."
  }
}
```

### 4.3. AgentSession Session管理

AgentSession Session管理接口负责维护 Agent 与用户之间的对话Session，包括Session的创建、查询、更新和删除。该模块由 `AgentSessionController` 实现，路由前缀为 `api/agent/session`，内部委托 `AgentSessionHandler` 处理业务逻辑 [API/Controllers/AgentManagement/AgentSessionController.cs]。

#### 4.3.1. 查询 Agent Session (GET /api/agent/session)

**鉴权**：JWT 或 API Key

**描述**：获取 Agent Session列表或单个Session详情。当 `id` 参数为空时，返回当前用户的所有Session列表（不包含 `Context` 字段），支持分页；当 `id` 不为空时，返回对应Session的完整内容（包含 `Context` 字段）。

**请求参数**（Query）：

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| id | string | 否 | null | Session ID，为空时返回列表，不为空时返回详情 |
| page | int | 否 | 1 | 页码 |
| pageSize | int | 否 | 10 | 每页数量 |

**响应格式**：

| 字段 | 类型 | 说明 |
|------|------|------|
| errorCode | int | 0=成功，非 0=具体错误 |
| data[].id | string | Session ID |
| data[].name | string | Session名称 |
| data[].context | string | 上下文信息（仅详情返回） |
| totalCount | int | 总记录数 |
| page | int | 当前页码 |
| pageSize | int | 每页数量 |

**错误码**：

| errorCode | 常量名 | 说明 |
|-----------|--------|------|
| 0 | - | 成功 |
| 150021 | AgentSessionNotFound | 未找到 Agent Session |

| 说明 |
|-----------|--------|------|
| 0 | - | 成功 |
| 150021 | AgentSessionNotFound | 未找到 Agent Session |

**响应示例**：

```json
{
  "errorCode": 0,
  "data": [
    {
      "id": "sess_001",
      "name": "数据分析Session"
    }
  ],
  "totalCount": 1,
  "page": 1,
  "pageSize": 10
}
```

#### 4.3.2. 删除Session (GET /api/agent/session/delete)

**鉴权**：JWT 或 API Key，需组织/项目角色为 ADMIN 以上

**描述**：删除一个或多个 Agent Session。`ids` 参数为Session ID 列表，多个 ID 以逗号分隔（如 `id1,id2,id3`）。仅删除当前用户名下的Session，不涉及其他用户的Session数据。

**请求参数**（Query）：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| ids | string | 是 | Session ID 列表，多个以逗号分隔 |

**响应格式**：

| 字段 | 类型 | 说明 |
|------|------|------|
| errorCode | int | 0=成功，非 0=具体错误 |
| data | object | 空对象 |

**错误码**：

| errorCode | 常量名 | 说明 |
|-----------|--------|------|
| 0 | - | 成功 |
| 150021 | AgentSessionNotFound | 未找到 Agent Session |

**响应示例**：

```json
{
  "errorCode": 0,
  "data": {}
}
```

#### 4.3.3. 创建Session (POST /api/agent/session)

**鉴权**：JWT 或 API Key，需组织/项目角色为 ADMIN 以上

**描述**：创建或更新 Agent Session。请求体为 `AgentSessionBody` 对象，包含 `id`、`name` 和 `context` 字段。当 `id` 为空时创建新Session，不为空时更新已有Session；`name` 或 `context` 为空时忽略对应字段的更新。

**请求参数**（Body，`[FromBody] AgentSessionBody`）：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | string | 否 | Session ID，为空则创建，不为空则更新 |
| name | string | 否 | Session名称 |
| context | string | 否 | 上下文信息 |

**请求示例**：

```json
{
  "name": "新数据分析Session",
  "context": "{\"lastTopic\":\"token usage\",\"errorMessages\":[]}"
}
```

**响应格式**：同"查询 Agent Session"的响应格式。

**错误码**：

| errorCode | 常量名 | 说明 |
|-----------|--------|------|
| 0 | - | 成功 |
| 150021 | AgentSessionNotFound | 未找到 Agent Session |

**响应示例**：

```json
{
  "errorCode": 0,
  "data": {
    "id": "sess_002",
    "name": "新数据分析Session",
    "context": "{\"lastTopic\":\"token usage\",\"errorMessages\":[]}"
  }
}
```

---

## 5. 数据管理接口

AgentInsightService 是一个面向 AI Agent 可Observation性与管理的 B2B SaaS 平台。数据管理接口是平台可Observation性能力的核心入口，负责提供 Trace、Observation、Score 三类可Observation性数据的查询能力，以及 AI Model的Config管理能力。该模块基于 ClickHouse 时序数据库构建底层数据存储，通过动态 SQL 生成引擎支撑复杂的过滤、排序与分页查询，是平台Alert系统、Trace 详情页、模型成本分析等功能的数据基础。

### 5.1. Metrics 查询 (Traces/Observations/Scores)

Metrics 查询接口由 `MetricsController` 提供，共包含 4 个端点，覆盖 Trace、Observation、Score 三类核心可Observation性数据的查询场景。Controller定义于 `API/Controllers/DataManagement/MetricsController.cs`，路由前缀为 `api/data/metrics` [API/Controllers/DataManagement/MetricsController.cs:L17-L19]。所有端点均继承自 `ApiControllerBase`，通过构造函数注入 `MetricsHandler` 和 `IMemoryCache` [API/Controllers/DataManagement/MetricsController.cs:L21-L23]。

#### 5.1.1. 查询 Observations (GET /api/data/metrics/observations)

**鉴权**: JWT 或 API Key（Basic Auth）

**描述**: 根据 Trace ID 获取该 Trace 下的全部 Observation 列表，支持分页。Observation 代表一次可Observation的 Agent 执行单元（如一次 LLM 调用、一次工具调用），按开始时间升序排列。

**请求参数**:

```json
{
  "errorCode": 0,
  "data": [
    {
      "id": "obs_001",
      "traceId": "trace_123",
      "type": "span",
      "startTime": "2024-01-01T00:00:00Z",
      "endTime": "2024-01-01T00:00:01Z",
      "name": "llm_call",
      "metadata": {}
    }
  ],
  "totalCount": 1,
  "page": 1,
  "pageSize": 10
}
```

底层实现中，`MetricsHandler.GetObservationsAsync` 首先校验 Trace ID 非空，然后通过 SqlSugar 的 `_chdb.Queryable<Observation>()` 构建查询，过滤条件为 `TraceId == traceId && !IsDeleted`，并按 `StartTime` 升序排序后执行分页 [API/Handlers/DataManagement/MetricsHandler.cs:L38-L55]。异常处理区分超时（`IsTimeoutException`）与普通错误，分别映射到 `ClickHouseQueryTimeout` 和 `ClickHouseQueryError` 错误码 [API/Handlers/DataManagement/MetricsHandler.cs:L48-L52]。

#### 5.1.2. 查询 Scores (GET /api/data/metrics/scores)

**鉴权**: JWT 或 API Key（Basic Auth）

**描述**: 根据 Trace ID 获取该 Trace 下的全部 Score 列表，支持分页。Score 代表对 Agent 执行结果的质量Score（如准确性、相关性等），按创建时间升序排列。

**请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | string | 是 | Trace ID |
| page | int | 否 | 页码，默认 1 |
| pagesize | int | 否 | 每页条数，默认 10 |

**响应格式**: 统一包装为 `ApiResponse<Score>` [API/Controllers/DataManagement/MetricsController.cs:L50-L59]。

**错误码**: 与 Observations 查询一致（EmptyTraceId=150018、ClickHouseQueryError=150010、ClickHouseQueryTimeout=150017）。

**请求示例**:

```http
GET /api/data/metrics/scores?id=trace_123&page=1&pagesize=10
Authorization: JWT Bearer Token <JWT_TOKEN>
```

**响应示例**:

```json
{
  "errorCode": 0,
  "data": [
    {
      "id": "score_001",
      "traceId": "trace_123",
      "name": "accuracy",
      "value": 0.95,
      "createdAt": "2024-01-01T00:00:00Z"
    }
  ],
  "totalCount": 1,
  "page": 1,
  "pageSize": 10
}
```

底层实现中，`MetricsHandler.GetScoresAsync` 与 Observations 查询逻辑对称，过滤条件为 `TraceId == traceId && !IsDeleted`，按 `CreatedAt` 升序排序 [API/Handlers/DataManagement/MetricsHandler.cs:L60-L77]。

#### 5.1.3. 批量查询 Trace Metric (GET /api/data/metrics/traces)

**鉴权**: JWT 或 API Key（Basic Auth）

**描述**: 根据 Trace ID 批量获取指标详情，包括 Token 用量、费用、延迟和模型名称等。该端点标记了 `#pragma warning disable CS0612, CS0618`，表明内部调用的 `GetTracesMetrics` Obsolete，但仍保留以兼容旧客户端 [API/Controllers/DataManagement/MetricsController.cs:L64-L72]。

**请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| ids | string | 是 | Trace ID，多个以逗号分隔 |

**响应格式**: 统一包装为 `ApiResponse<TraceMetricsResponse>`，每个元素包含 `id`（Trace ID）、`inputtokens`、`outputtokens`、`totaltokens`、`inputcost`、`outputcost`、`totalcost`、`latency`（毫秒）、`modelnames` 等字段 [API/Controllers/DataManagement/MetricsController.cs:L60-L63]。

**错误码**:

| errorCode | 常量名 | 说明 |
|-----------|--------|------|
| 150009 | EmptyTraceIds | Trace ID 列表为空 |
| 150011 | TooManyTraceIds | Trace ID 数量超过上限 |
| 150010 | ClickHouseQueryError | ClickHouse 查询异常 |

**请求示例**:

```http
GET /api/data/metrics/traces?ids=trace_123,trace_456
Authorization: JWT Bearer Token <JWT_TOKEN>
```

**响应示例**:

```json
{
  "errorCode": 0,
  "data": [
    {
      "id": "trace_123",
      "inputtokens": 1200,
      "outputtokens": 800,
      "totaltokens": 2000,
      "inputcost": 0.0012,
      "outputcost": 0.0016,
      "totalcost": 0.0028,
      "latency": 3500,
      "modelnames": ["gpt-4o"]
    }
  ]
}
```

#### 5.1.4. 复杂条件查询 Traces (POST /api/data/metrics/traces)

**鉴权**: JWT 或 API Key（Basic Auth）

**描述**: 分页查询 Trace 列表，支持按 ID、名称、时间范围及自定义 Filter 条件进行复杂过滤。该端点是 Metrics 查询的核心能力，通过 `TraceMetricsBody` 请求体承载查询条件，底层由 `MetricsHandler.GetTraces` 方法动态构建 ClickHouse SQL [API/Controllers/DataManagement/MetricsController.cs:L74-L125]。

**请求参数** (`TraceMetricsBody`):

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| orgid | string | 条件必填 | Org ID，与 projectid 至少提供一个 |
| projectid | string | 条件必填 | Project ID，与 orgid 至少提供一个 |
| id | string | 否 | Trace ID 精确匹配 |
| name | string | 否 | Trace 名称模糊匹配 |
| from | datetime | 否 | 开始时间范围 |
| to | datetime | 否 | 结束时间范围 |
| page | int | 否 | 页码，默认 1 |
| pagesize | int | 否 | 每页条数，默认 50 |
| orderby | string | 否 | 排序字段，格式为 `字段.方向`（如 `timestamp.desc`） |
| fields | string[] | 否 | 需要返回的字段列表，为空时返回全部字段 |
| filter | Filter[] | 否 | 自定义过滤条件数组，支持多条件组合 |

**Filter 对象结构**:

| 字段 | 类型 | 说明 |
|------|------|------|
| type | FilterType | 过滤字段类型（DateTime/String/Number 等 7 种） |
| column | FilterColumn | 过滤列名（Id/Name/Timestamp 等 25 个可选列） |
| operator | FilterOperator | 过滤运算符（GreaterThan/Contains/AnyOf 等 15 种） |
| value | object | 过滤值，类型取决于 type 字段 |

**Filter 系统详细说明**:

Filter 系统是 Trace 查询的核心动态过滤机制，由三个枚举定义支撑：

**FilterType**（7 种类型）定义于 `Models/Common/Enums/FilterEnum.cs:8`：

| 枚举值 | 数值 | 说明 |
|--------|------|------|
| DateTime | 1 | 日期时间类型 |
| String | 2 | 字符串类型 |
| Number | 3 | 数值类型 |
| StringOptions | 4 | 字符串选项（多选） |
| ArrayOptions | 5 | 数组选项（多选） |
| Boolean | 6 | 布尔类型 |
| Null | 7 | 空值类型 |

**FilterOperator**（15 种运算符）定义于 `Models/Common/Enums/FilterEnum.cs:20`：

| 枚举值 | 数值 | 说明 |
|--------|------|------|
| GreaterThan | 1 | 大于 |
| LessThan | 2 | 小于 |
| GreaterThanOrEqualTo | 3 | 大于等于 |
| LessThanOrEqualTo | 4 | 小于等于 |
| EqualTo | 5 | 等于 |
| Contains | 6 | 包含 |
| DoesNotContain | 7 | 不包含 |
| StartsWith | 8 | 以...开头 |
| EndsWith | 9 | 以...结尾 |
| AnyOf | 10 | 任意匹配 |
| NoneOf | 11 | 全部不匹配 |
| AllOf | 12 | 全部匹配 |
| NotEqualTo | 13 | 不等于 |
| IsNull | 14 | 为空 |
| IsNotNull | 15 | 不为空 |

**FilterColumn**（25 个可过滤列）定义于 `Models/Common/Enums/FilterEnum.cs:40`：

| 枚举值 | 数值 | 说明 |
|--------|------|------|
| Id | 1 | Trace ID |
| Name | 2 | Trace 名称 |
| Timestamp | 3 | 时间戳 |
| UserId | 4 | User ID |
| SessionId | 5 | Session ID |
| Environment | 6 | 环境 |
| Version | 7 | 版本 |
| Release | 8 | 发布标识 |
| Tags | 9 | 标签 |
| Bookmarked | 10 | 是否收藏 |
| Latency | 11 | 延迟 |
| InputTokens | 12 | 输入 Token 数 |
| OutputTokens | 13 | 输出 Token 数 |
| TotalTokens | 14 | 总 Token 数 |
| Tokens | 15 | Token 数（通用） |
| InputCost | 16 | 输入费用 |
| OutputCost | 17 | 输出费用 |
| TotalCost | 18 | 总费用 |
| Level | 19 | 日志级别 |
| WarningCount | 20 | 警告数 |
| ErrorCount | 21 | 错误数 |
| DefaultCount | 22 | 默认计数 |
| DebugCount | 23 | 调试计数 |
| ModelNames | 24 | 模型名称 |
| ScoresAvg | 25 | 平均Score |

**响应格式**: 统一包装为 `ApiResponse<TraceMetrics>`，包含 Trace 列表和分页信息。

**错误码**:

| errorCode | 常量名 | 说明 |
|-----------|--------|------|
| 150019 | OrgAndProjectBothEmpty | orgid 和 projectid 均为空 |
| 150012 | InvalidFilterType | Filter 类型无效 |
| 150013 | InvalidFilterColumn | Filter 列无效 |
| 150014 | InvalidFilterOperator | Filter 运算符无效 |
| 150015 | InvalidFilterValue | Filter 值无效 |
| 150016 | InvalidOrderBy | 排序字段无效 |
| 150010 | ClickHouseQueryError | ClickHouse 查询异常 |
| 150017 | ClickHouseQueryTimeout | ClickHouse 查询超时 |

**请求示例**:

```http
POST /api/data/metrics/traces
Authorization: JWT Bearer Token <JWT_TOKEN>
Content-Type: application/json
```

p
POST /api/data/metrics/traces
Authorization: JWT Bearer Token <JWT_TOKEN>
Content-Type: application/json
```

```json
{
  "orgid": "org_001",
  "projectid": "project_001",
  "from": "2024-01-01 00:00:00",
  "to": "2024-01-31 23:59:59",
  "page": 1,
  "pagesize": 50,
  "orderby": "timestamp.desc",
  "filter": [
    {
      "type": "datetime",
      "column": "timestamp",
      "operator": ">=",
      "value": "2024-01-01 00:00:00"
    },
    {
      "type": "number",
      "column": "totalcost",
      "operator": ">",
      "value": 0.01
    },
    {
      "type": "string",
      "column": "name",
      "operator": "contains",
      "value": "agent"
    }
  ]
}
```

**响应示例**:

```json
{
  "errorCode": 0,
  "data": [
    {
      "id": "trace_123",
      "name": "agent_run_001",
      "timestamp": "2024-01-15T10:30:00Z",
      "totalcost": 0.0028,
      "latency": 3500,
      "modelnames": ["gpt-4o"]
    }
  ],
  "totalCount": 1,
  "page": 1,
  "pageSize": 50
}
```

00,
      "modelnames": ["gpt-4o"]
    }
  ],
  "totalCount": 1,
  "page": 1,
  "pageSize": 50
}
```

底层实现中，`MetricsHandler.GetTraces` 方法执行以下核心步骤 [API/Handlers/DataManagement/MetricsHandler.cs:L80-L95]：

1. 调用 `ResolveProjectId` 解析项目 ID，当 orgid 和 projectid 均为空时抛出 `OrgAndProjectBothEmpty` 异常；
2. 通过 `ParseSelectFields` 解析需要返回的字段列表；
3. 通过 `ParseOrderBy` 解析排序字段，并调用 `IsDefaultOrder` 判断是否为默认排序；
4. 调用 `TraceFilterBuilder.BuildFilters` 将 Filter 数组转换为 SQL 条件表达式；
5. 动态构建 ClickHouse SQL，包含 CTE（`BuildWithClause`）、JOIN（`BuildJoinClause`）和 SELECT 子句（`BuildSelectClause`），最终通过 `_clickHouseClient` 执行查询。

### 5.2. Model 管理

Model 管理接口由 `ModelController` 提供，共包含 1 个端点，用于查询 AI 模型列表。Controller定义于 `API/Controllers/DataManagement/ModelController.cs`，路由前缀为 `api/data/model` [API/Controllers/DataManagement/ModelController.cs:L13-L15]。

#### 5.2.1. 获取模型列表 (GET /api/data/model)

**鉴权**: JWT 或 API Key（Basic Auth）

**描述**: 分页查询 AI 模型列表，支持按关键词过滤、按项目筛选、包含预定义模型、自定义排序。模型数据存储于 PostgreSQL Data 库，通过 `ModelHandler.GetModels` 方法查询 [API/Controllers/DataManagement/ModelController.cs:L34-L40]。

**请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| keyword | string | 否 | 关键词，按模型名称模糊过滤 |
| projectid | string | 否 | Project ID，配合 includedpredefined 使用 |
| includedpredefined | bool | 否 | 是否包含预定义模型（projectid=null 的模型），默认 false |
| orderby | string | 否 | 排序方式，默认为 `-updatedat`（按更新时间倒序），支持 `createdat`（正序）、`-createdat`（倒序）等 |
| page | int | 否 | 页码，默认 1 |
| pageSize | int | 否 | 每页条数，默认 10 |

**includedpredefined 参数行为矩阵**:

| projectid | includedpredefined | 行为 |
|-----------|-------------------|------|
| 有值 | false | 仅查询项目专属模型（ProjectId == projectid） |
| 有值 | true | 同时包含预定义模型（ProjectId == projectid 或 ProjectId == null） |
| 为空 | true | 返回所有预定义模型（ProjectId == null） |
| 为空 | false | 抛出 `EmptyProjectId` 异常 |

ctId == null） |
| 为空 | true | 返回所有预定义模型（ProjectId == null） |
| 为空 | false | 抛出 `EmptyProjectId` 异常 |

**响应格式**: 统一包装为 `ApiResponse<ModelDefinition>`，每个模型包含 `id`、`createdat`、`updatedat`、`projectid`、`modelname`、`matchpattern`、`startdate`、`inputprice`、`outputprice`、`totalprice`、`unit`、`tokenizerconfig`、`tokenizerid`、`pricingtiers` 等字段 [API/Controllers/DataManagement/ModelController.cs:L30-L33]。

**错误码**:

| errorCode | 常量名 | 说明 |
|-----------|--------|------|
| 150000 | EmptyProjectId | projectid 为空且 includedpredefined 为 false 时抛出 [API/Handlers/DataManagement/ModelHandler.cs:L23-L24] |
| 140008 | UnauthorizedProjectAccess | 当前用户无权访问指定项目 |

**请求示例**:

```http
GET /api/data/model?keyword=gpt&projectid=project_001&includedpredefined=true&orderby=-updatedat&page=1&pageSize=10
Authorization: JWT Bearer Token <JWT_TOKEN>
```

**响应示例**:

```json
{
  "errorCode": 0,
  "data": [
    {
      "id": "model_001",
      "createdat": "2024-01-01T00:00:00Z",
      "updatedat": "2024-01-15T00:00:00Z",
      "projectid": "project_001",
      "modelname": "gpt-4o",
      "matchpattern": "gpt-4o*",
      "startdate": "2024-01-01",
      "inputprice": "0.005",
      "outputprice": "0.015",
      "totalprice": null,
      "unit": "1K tokens",
      "tokenizerconfig": null,
      "tokenizerid": "cl100k_base",
      "pricingtiers": []
    }
  ],
  "totalCount": 1,
  "page": 1,
  "pageSize": 10
}
```

底层实现中，`ModelHandler.GetModels` 方法执行以下核心步骤 [API/Handlers/DataManagement/ModelHandler.cs:L21-L67]：

1. 参数校验：当 `projectId` 为空且 `includePredefined` 为 false 时，抛出 `EmptyProjectId` 异常 [API/Handlers/DataManagement/ModelHandler.cs:L23-L24]；
2. Privilege校验：当 `projectId` 非空时，调用 `RequireAccessibleProject` 验证当前用户对该项目的访问Privilege [API/Handlers/DataManagement/ModelHandler.cs:L26-L28]；
3. 构建查询：通过 `DataDb.Queryable<ModelDefinition>()` 构建查询，并预加载 `PricingTiers` 及其 `Prices` 导航属性 [API/Handlers/DataManagement/ModelHandler.cs:L30-L31]；
4. 关键词过滤：当 `keyword` 非空时，按 `ModelName.Contains(keyword)` 过滤 [API/Handlers/DataManagement/ModelHandler.cs:L33-L36]；
5. 项目过滤：根据 `projectId` 和 `includePredefined` 的组合条件动态构建过滤表达式 [API/Handlers/DataManagement/ModelHandler.cs:L38-L52]；
6. 排序与分页：通过 `BuildOrderClause` 将 orderby 参数转换为安全的 SQL 排序子句，然后执行分页查询 [API/Handlers/DataManagement/ModelHandler.cs:L54-L58]；
7. 数据清洗：对返回的模型价格字段调用 `TrimTrailingZeros` 去除末尾多余的零和小数点，确保价格展示简洁 [API/Handlers/DataManagement/ModelHandler.cs:L60-L76]。

段调用 `TrimTrailingZeros` 去除末尾多余的零和小数点，确保价格展示简洁 [API/Handlers/DataManagement/ModelHandler.cs:L60-L76]。

`BuildOrderClause` 方法通过 `PropertyToColumnMap` 静态字典（基于 `SugarColumn` 特性构建的属性-列名映射）将 orderby 参数中的属性名安全映射为数据库列名，防止 SQL 注入 [API/Handlers/DataManagement/ModelHandler.cs:L88-L100]。

---

## 6. Payment管理接口

AgentInsightService 是一个面向 AI Agent 可Observation性与管理的 B2B SaaS 平台，Payment管理接口是其商业化闭环的核心组成部分。该模块由 `OrderController`（订单管理，4 个端点）和 `NotifyController`（Payment回调通知，2 个端点）组成，共 6 个端点，覆盖微信Payment（JSAPI/Native/MiniProgram）与Payment宝Payment的订单创建、查询、产品转换计算以及异步回调处理。Payment模块采用 Controller → Handler → Service 的分层架构，通过 `IPaymentService` 统一封装微信与Payment宝的差异，对外提供一致的 `AgentInsightOrderResponse` 返回模型 [API/Common/Services/PaymentService.cs]。

### 6.1. 订单管理 (Order)

订单管理接口由 `OrderController` 提供，路由前缀为 `api/payment`，包含 4 个端点：查询订单列表、下单、查询单个订单、产品转换计算 [API/Controllers/PaymentManagement/OrderController.cs:34-79]。

#### 6.1.1. 查询订单列表 (GET /api/payment/order)

**鉴权**: JWT（需登录且为组织 OWNER）

**描述**: 查询指定组织下的订单列表，支持分页。仅组织 OWNER 角色可访问。

**请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| orgId | string | 是 | Org ID |
| page | int | 否 | 页码，默认为 `AgentInsightConst.DefaultPage` |
| pageSize | int | 否 | 每页数量，默认为 `AgentInsightConst.DefaultPageSize` |

**响应格式**: `ApiResponse<AgentInsightOrder>`，包含订单列表、总记录数、当前页码和当前页数量。

**业务逻辑**: `OrderHandler.GetOrders` 首先校验 orgId 非空，否则抛出 `InvalidOrganization`（130003）；随后在 DataDb 中查询当前用户在该组织的成员关系，若不存在则抛出 `InvalidOrganization`，若角色非 `PGRole.OWNER` 则抛出 `UnauthorizedOrganizationAccess`（130009）；最后通过 SqlSugar 的 `ToPageListAsync` 分页查询订单数据 [API/Handlers/PaymentManagement/OrderHandler.cs:34-54]。

**错误码**:

| errorCode | 常量名 | 说明 |
|-----------|--------|------|
| 130003 | InvalidOrganization | 组织无效或用户不属于该组织 |
| 130009 | UnauthorizedOrganizationAccess | 非组织 OWNER 无权访问 |

#### 6.1.2. 下单 (POST /api/payment/order)

**鉴权**: JWT（需登录且为组织 OWNER），另有 `RateLimit(maxRequests: 1, windowSeconds: 10)` 限流

**描述**: 创建新订单并返回Payment参数。支持微信Payment（JSAPI/Native/MiniProgram）和Payment宝Payment（电脑网站）。请求体为 `AgentInsightOrderBody`，其中 `OpenId` 可选，若未在 body 中提供则从请求头 `OpenId` 读取 [API/Controllers/PaymentManagement/OrderController.cs:48-58]。

**请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| orgId | string | 否 | Org ID，缺省时使用当前用户最新拥有的组织 |
| productId | string | 是 | Product ID |
| productDurationId | string | 是 | 产品时长 ID |
| payMethod | int | 是 | Payment方式：1=WeChat，2=Alipay |
| subPayMethod | int | 是 | 子Payment方式：1=WECHAT_JSAPI，2=WECHAT_NATIVE，3=WECHAT_MINIPROGRAM，11=ALIPAY_FAST_INSTANT_TRADE_PAY |
| openId | string | 否 | 微信 OpenID（JSAPI/小程序Payment时必填） |

**响应格式**: `ApiResponse<AgentInsightOrderResponse>`，包含订单号、Payment状态、PaymenterrorCodeUrl、二维码 Base64、Payment宝表单、预Payment ID（prepayId）、appId、时间戳、随机字符串、包、签名类型和Payment签名。

erResponse>`，包含订单号、Payment状态、PaymenterrorCodeUrl、二维码 Base64、Payment宝表单、预Payment ID（prepayId）、appId、时间戳、随机字符串、包、签名类型和Payment签名。

**业务逻辑**: `OrderHandler.PlaceOrder` 执行以下校验与流程 [API/Handlers/PaymentManagement/OrderHandler.cs:56-80]：
1. 查询当前用户拥有的组织列表（角色为 OWNER），若无则抛出 `DoNotOwnOrganization`（810012）；
2. 若 body.OrgId 为空则取第一个组织，否则校验该组织是否属于当前用户，不属于则抛出 `UnauthorizedOrganizationAccess`；
3. 校验 productId 与 productDurationId 非空，否则抛出 `ProductNotExist`（810013）；
4. 查询产品与时长信息，不存在则分别抛出 `ProductNotExist` 或 `ProductDurationNotExist`（810014）；
5. 查询当前组织的 `OrgPrivilege`，用于后续的升级/降级判断与价格计算；
6. 调用 `PaymentService` 根据 `SubPayMethod` 分发到微信或Payment宝的下单逻辑。

**错误码**:

| errorCode | 常量名 | 说明 |
|-----------|--------|------|
| 810012 | DoNotOwnOrganization | 用户不拥有任何组织 |
| 130009 | UnauthorizedOrganizationAccess | 无权访问指定组织 |
| 810013 | ProductNotExist | 产品不存在 |
| 810014 | ProductDurationNotExist | 产品时长不存在 |
| 810019 | UnsupportedPayMethod | 不支持的Payment方式 |
| 810020 | AlipayPlaceOrderError | Payment宝下单失败 |
| 810021 | WeChatEmptyResponse | 微信返回空响应 |
| 810022 | WeChatErrorResponse | 微信返回错误响应 |
| 810023 | CannotDowngradeProduct | 不能降级产品 |
| 810025 | InvalidTotalAmount | 订单总金额无效 |

#### 6.1.3. 查询单个订单 (GET /api/payment/order/query)

**鉴权**: JWT（需登录），另有 `RateLimit(maxRequests: 1, windowSeconds: 1)` 限流

**描述**: 根据订单号查询订单状态，用于前端轮询Payment结果 [API/Controllers/PaymentManagement/OrderController.cs:64-72]。

**请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| orderNo | string | 是 | 订单号 |

**响应格式**: `ApiResponse<AgentInsightOrderResponse>`，包含订单当前状态及Payment参数。

**业务逻辑**: `OrderHandler.QueryOrder` 根据订单号查询订单，若订单不存在则抛出 `OrderNotExist`（810015）；若订单号为空则抛出 `EmptyOrderNo`（810011）。查询到订单后，根据Payment方式调用 `PaymentService` 向微信或Payment宝发起交易查询，并同步更新本地订单状态。

**错误码**:

| errorCode | 常量名 | 说明 |
|-----------|--------|------|
| 810011 | EmptyOrderNo | 订单号为空 |
| 810015 | OrderNotExist | 订单不存在 |
| 810005 | InvalidAlipayTradeNo | Payment宝交易号无效 |
| 810017 | InvalidWeChatTradeNo | 微信交易号无效 |
| 810024 | WeChatQueryErrorResponse | 微信查询返回错误 |

#### 6.1.4. 产品转换计算 (GET /api/payment/order/conversion)

**鉴权**: JWT（需登录且为组织 OWNER）

**描述**: 计算从当前产品转换到新产品的价格差与时长信息，用于产品升级/降级场景 [API/Controllers/PaymentManagement/OrderController.cs:79]。

**请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| newProductId | string | 是 | 目标产品 ID |

**响应格式**: `ApiResponse`，包含转换后的价格、时长、折扣等信息。

**业务逻辑**: `OrderHandler.GetProductConversion` 查询当前组织的 `OrgPrivilege` 获取当前产品信息，再查询目标产品与时长信息，计算价格差。若目标产品等级低于当前产品，则抛出 `CannotDowngradeProduct`（810023）。

**错误码**:

| errorCode | 常量名 | 说明 |
|-----------|--------|------|
| 810013 | ProductNotExist | 产品不存在 |
| 810014 | ProductDurationNotExist | 产品时长不存在 |
| 810023 | CannotDowngradeProduct | 不能降级产品 |

### 6.2. Payment回调通知 (Notify)

Payment回调通知接口由 `NotifyController` 提供，路由前缀为 `api/payment/notify`，包含 2 个端点：微信Payment异步回调和Payment宝Payment异步回调。该Controller标记为 `[AllowAnonymous]` 且 `[ApiExplorerSettings(IgnoreApi = true)]`，不依赖 JWT 鉴权，而是使用Payment平台自身的签名校验机制确保请求合法性 [API/Controllers/PaymentManagement/NotifyController.cs:14-22]。

#### 6.2.1. 微信Payment异步回调 (POST /api/payment/notify/wechatnotify)

**鉴权**: 微信Payment平台签名校验（不依赖 JWT）

**描述**: 接收微信Payment平台的异步回调通知，处理Payment结果并更新订单状态。微信Payment金额以分为单位（`WeChatAmountUnit = 100`）[API/Common/Services/PaymentService.cs:16]。

**请求体**: 微信Payment回调的 JSON 数据，反序列化为 `WeChatNotify` 对象。

**响应格式**: 成功时返回 `_wechatService.WXSuccessResult()`，失败时返回 `_wechatService.WXFailResult("FAIL")`。

**业务逻辑**: `NotifyController.WeChatNotify` 执行以下流程 [API/Controllers/PaymentManagement/NotifyController.cs:29-52]：
1. 读取请求体原始字符串，若为空则抛出 `FakedWeChatRequest`（620014）；
2. 调用 `NotifyHandler.ExamineWeChatRequest` 验证微信请求签名（包含请求头中的 serialNo、timestamp、nonce、signature 等字段），验签失败则抛出 `InvalidWeChatNotify`（810010）；
3. 将请求体反序列化为 `WeChatNotify` 对象；
4. 调用 `NotifyHandler.ProcessWeChatNotify` 处理通知，更新订单状态并发布 `PaymentTransactionNotification` 或 `WeChatNotifyReceivedNotification` 事件 [API/Handlers/PaymentManagement/NotifyHandler.cs:36]；
5. 处理成功后返回微信要求的成功响应格式，失败则返回失败响应以便微信重试。

**错误码**:

| errorCode | 常量名 | 说明 |
|-----------|--------|------|
| 620014 | FakedWeChatRequest | 伪造的微信请求（请求体为空） |
| 810010 | InvalidWeChatNotify | 微信通知验签失败 |
| 810016 | EmptyWeChatTransaction | 微信交易信息为空 |
| 810018 | EmptyWeChatNotify | 微信通知为空 |
| 810026 | OrderStateUpdateFailed | 订单状态更新失败 |

#### 6.2.2. Payment宝Payment异步回调 (POST /api/payment/notify/alipaynotify)

**鉴权**: Payment宝平台签名校验（不依赖 JWT）

**描述**: 接收Payment宝Payment平台的异步回调通知，需验签后处理Payment结果。

**请求体**: Payment宝回调的 Form 表单数据（`application/x-www-form-urlenerrorCoded`）。

**响应格式**: 成功时返回字符串 `"success"`，失败时返回字符串 `"fail"`。

**业务逻辑**: `NotifyController.AlipayNotify` 执行以下流程 [API/Controllers/PaymentManagement/NotifyController.cs:57-72]：
1. 获取当前 `HttpContext.Request`；
2. 调用 `NotifyHandler.ProcessAlipayNotify` 处理Payment宝通知，内部通过 `PaymentService` 执行验签（使用 `GetAlipaySignDictionary` 构建签名参数字典），验签失败则抛出 `AlipaySignatureError`（810007）；
3. 验签通过后，解析交易状态（`TradeState`），更新订单状态并发布 `PaymentTransactionNotification` 事件；
4. 返回 `"success"` 通知Payment宝停止重试，异常时返回 `"fail"` 让Payment宝稍后重试。

**错误码**:

| errorCode | 常量名 | 说明 |
|-----------|--------|------|
| 810002 | AlipaySettingNotConfig | Payment宝Config未设置 |
| 810003 | AlipayConnectionError | Payment宝连接错误 |
| 810004 | AlipayTradeError | Payment宝交易错误 |
| 810006 | InvalidAlipayTransaction | Payment宝交易无效 |
| 810007 | AlipaySignatureError | Payment宝验签失败 |
| 810008 | AlipaySignDictionaryError | Payment宝签名参数字典构建失败 |
| 810026 | OrderStateUpdateFailed | 订单状态更新失败 |

 810008 | AlipaySignDictionaryError | Payment宝签名参数字典构建失败 |
| 810026 | OrderStateUpdateFailed | 订单状态更新失败 |

**Payment状态机**: 订单状态 `OrderState` 定义于 `Models/Common/Enums/PaymentEnums.cs`，包含 Created=1（已创建）、WaitForPay=2（待Payment）、Paid=3（已Payment）、Refunded=4（已退款）、Cancelled=5（已取消）、Closed=6（已关闭）、PayError=7（Payment错误）。回调处理的核心逻辑是将订单从待Payment状态推进到已Payment状态，并同步更新 `OrgPrivilege` 以生效订阅权益。

---

## 7. 产品管理接口

### 7.1. 获取产品列表 (GET /api/product)

**鉴权**: 无（公开接口，用于前端展示产品列表）

**描述**: 返回系统中所有可用的产品（`AgentInsightProduct`）列表。产品是用户订阅计费的基本单位，定义了价格、资源配额（项目数/人数/组织数/Agent 数）以及产品级别等信息。

#### 7.1.1. 请求参数

无。该端点不接受任何查询参数或请求体。

#### 7.1.2. 响应格式

响应使用统一包装类型 `ApiResponse<AgentInsightProduct[]>`，HTTP 状态码为 200 OK [API/Controllers/ProductManagement/ProductController.cs:L25-L31]。

| 字段 | 类型 | 说明 |
|------|------|------|
| `errorCode` | int | 0=成功，非 0=具体错误码 |
| `data` | AgentInsightProduct[] | 产品列表，每个元素包含产品 ID、名称、类型、价格、配额限制等字段 |

`AgentInsightProduct` 对象字段说明如下（来自 Controller XML 注释）：

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | string | Product ID |
| `name` | string | 产品名称 |
| `type` | int | 产品类型：0=None，1=Monthly，2=Permanent |
| `note` | string | 备注 |
| `price` | decimal | 产品价格 |
| `monthlyrate` | decimal | 月付费率 |
| `permanentrate` | decimal | 永久费率 |
| `projectlimit` | int | 项目数量上限 |
| `headcountlimit` | int | 人数上限 |
| `orglimit` | int | 组织数量上限 |
| `agentlimit` | int | Agent 数量上限 |
| `level` | int | 产品级别 |

#### 7.1.3. 错误码

| errorCode | 常量名 | 说明 |
|-----------|--------|------|
| 0 | - | 成功 |
| 810013 | ProductNotExist | 产品不存在 |

> 注：`ProductNotExist = 810013` 定义于 `Models/Common/Enums/ExceptionCodes.cs`。本接口仅执行全量查询，通常不会触发该错误；该错误码在下游流程（如订单创建）中可能被抛出。

#### 7.1.4. 请求示例

```http
GET /api/product
```

#### 7.1.5. 响应示例

```json
{
  "errorCode": 0,
  "data": [
    {
      "id": "prod_monthly_basic",
      "name": "月度基础版",
      "type": 1,
      "note": "适合个人开发者",
      "price": 99.0,
      "monthlyrate": 100,
      "permanentrate": 0,
      "projectlimit": 5,
      "headcountlimit": 10,
      "orglimit": 3,
      "agentlimit": 10,
      "level": 1
    },
    {
      "id": "prod_permanent_enterprise",
      "name": "永久企业版",
      "type": 2,
      "note": "适合企业客户",
      "price": 9999.0,
      "monthlyrate": 0,
      "permanentrate": 100,
      "projectlimit": 100,
      "headcountlimit": 500,
      "orglimit": 10,
      "agentlimit": 100,
      "level": 3
    }
  ]
}
```

#### 7.1.6. 实现说明

`ProductController.Get` 方法调用 `_handler.GetProducts()` 获取产品数据 [API/Controllers/ProductManagement/ProductController.cs:L26-L30]。`ProductHandler.GetProducts` 通过 SqlSugar ORM 的 `Db.Queryable<AgentInsightProduct>().ToListAsync(CancellationToken)` 从 User 数据库（`AgentInsightConst.KeyedService_UserDb`）中查询全部产品记录 [API/Handlers/ProductManagement/ProductHandler.cs:L10-L13]。查询结果直接封装为 `ApiResponse<AgentInsightProduct[]>` 返回，无额外业务逻辑或过滤条件。

### 7.2. 获取产品时长选项 (GET /api/product/duration)

**鉴权**: 无（公开接口，用于前端展示产品时长选项）

**描述**: 返回系统中所有可用的产品时长选项（`AgentInsightProductDuration`）列表。时长选项定义了用户购买产品时可选择的时长周期（如 30 天）及对应的折扣比例。

#### 7.2.1. 请求参数

无。该端点不接受任何查询参数或请求体。

#### 7.2.2. 响应格式

响应使用统一包装类型 `ApiResponse<AgentInsightProductDuration[]>`，HTTP 状态码为 200 OK [API/Controllers/ProductManagement/ProductController.cs:L37-L43]。

| 字段 | 类型 | 说明 |
|------|------|------|
| `errorCode` | int | 0=成功，非 0=具体错误码 |
| `data` | AgentInsightProductDuration[] | 时长选项列表 |

`AgentInsightProductDuration` 对象字段说明如下（来自 Controller XML 注释）：

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | string | 时长 ID |
| `name` | string | 时长名称 |
| `quantity` | int | 时长数量（单位：天） |
| `discount` | decimal | 折扣比例（如 0.9 表示 9 折） |

#### 7.2.3. 错误码

| errorCode | 常量名 | 说明 |
|-----------|--------|------|
| 0 | - | 成功 |
| 810014 | ProductDurationNotExist | 产品时长不存在 |

> 注：`ProductDurationNotExist = 810014` 定义于 `Models/Common/Enums/ExceptionCodes.cs`。本接口仅执行全量查询，通常不会触发该错误；该错误码在下单流程校验时长有效性时可能被抛出。

#### 7.2.4. 请求示例

```http
GET /api/product/duration
```

#### 7.2.5. 响应示例

```json
{
  "errorCode": 0,
  "data": [
    {
      "id": "dur_monthly",
      "name": "月度",
      "quantity": 30,
      "discount": 1.0
    },
    {
      "id": "dur_quarterly",
      "name": "季度",
      "quantity": 90,
      "discount": 0.9
    },
    {
      "id": "dur_yearly",
      "name": "年度",
      "quantity": 365,
      "discount": 0.8
    }
  ]
}
```

#### 7.2.6. 实现说明

`ProductController.GetDuration` 方法调用 `_handler.GetProductDurations()` 获取时长数据 [API/Controllers/ProductManagement/ProductController.cs:L38-L42]。`ProductHandler.GetProductDurations` 通过 SqlSugar ORM 的 `Db.Queryable<AgentInsightProductDuration>().ToListAsync(CancellationToken)` 从 User 数据库中查询全部时长记录 [API/Handlers/ProductManagement/ProductHandler.cs:L15-L18]。查询结果直接封装为 `ApiResponse<AgentInsightProductDuration[]>` 返回。

### 7.3. 产品类型定义

产品类型通过 `ProductType` 枚举定义（`Models/Common/Enums/ProductType.cs`），在 Controller 的 XML 注释中明确标注：

| 枚举值 | 数值 | 说明 |
|--------|------|------|
| None | 0 | 无类型（默认） |
| Monthly | 1 | 月度订阅 |
| Permanent | 2 | 永久买断 |

该枚举用于区分产品的计费模式：`Monthly` 类型产品按月订阅计费，`Permanent` 类型产品为一次性买断。前端可根据 `type` 字段决定展示的购买流程和价格计算方式。

### 7.4. 数据流与依赖

产品管理接口的数据流相对简单，遵循 Controller → Handler → Database 的分层架构：

1. 客户端发起 `GET /api/product` 或 `GET /api/product/duration` 请求
2. `ProductController` 接收请求并调用对应的 Handler 方法 [API/Controllers/ProductManagement/ProductController.cs:L26-L30]
3. `ProductHandler` 通过 SqlSugar 查询 User 数据库中的 `AgentInsightProduct` 或 `AgentInsightProductDuration` 表 [API/Handlers/ProductManagement/ProductHandler.cs:L10-L18]
4. 查询结果封装为 `ApiResponse<T>` 返回给客户端

`ProductHandler` 构造函数注入了两个数据库连接（User 库和 Data 库）以及 `IAppContextService`，但产品查询仅使用 User 库连接 [API/Handlers/ProductManagement/ProductHandler.cs:L7-L9]。由于产品数据属于基础Config数据，变更频率低，且接口为公开接口，无需进行用户身份校验或Privilege检查。

---

## 8. 工具管理接口

AgentInsightService 是一个面向 AI Agent 可Observation性与管理的 B2B SaaS 平台，后端 API 基于 .NET / C#（Furion 框架）构建，采用 Controller → Handler → Service 的分层架构。工具管理接口归属于 `API/Controllers/ToolsManagement` 目录，涵盖BulletinBulletin、HealthWeChat三大类共 10 个端点。其中Bulletin管理接口负责平台Bulletin与协议内容的发布、审批、查询与下架；健康检查接口用于服务存活探测；微信公众号接口用于对接微信服务器的事件推送与消息收发。三个 Controller 均通过 `ApiControllerBase` 基类注册 Handler，并遵循统一的 `ApiResponse<T>` 响应包装格式。

### 8.1. Bulletin Bulletin管理

Bulletin管理接口由 `BulletinController` 提供，路由前缀为 `api/tools/bulletin`，共 7 个端点，覆盖Bulletin的创建/更新、协议获取、前端/后台查询、批量审批、退回修改与关闭操作。该 Controller 继承 `ApiControllerBase`，通过构造函数注入 `BulletinHandler` 处理业务逻辑，并调用 `RegisterHandler(_handler)` 完成注册 [API/Controllers/ToolsManagement/BulletinController.cs:L24-L26]。

调用 `RegisterHandler(_handler)` 完成注册 [API/Controllers/ToolsManagement/BulletinController.cs:L24-L26]。

Bulletin类型由 `BulletinType` 枚举定义：`News=1`（新闻）、`Activity=2`（活动）、`Information=3`（资讯）、`Annoucement=4`（Bulletin）、`Advertisement=5`（广告）、`Agreement=9`（协议）。Bulletin状态由 `BulletinStatus` 枚举定义：`Draft=1`（草稿）、`Reviewing=2`（审核中）、`Revision=3`（退回修改）、`Published=4`（已发布）、`Expired=5`（已过期）、`Closed=6`（已关闭）。创建Bulletin时，请求体 `CreateBulletinBody` 中的 `type` 字段即对应上述类型值，例如 `type=4` 表示Bulletin、`type=9` 表示协议 [API/Controllers/ToolsManagement/BulletinController.cs:L28-L31]。

#### 8.1.1. 创建或更新Bulletin (POST /api/tools/bulletin)

**鉴权**：JWT（需管理员Privilege）

**描述**：创建新Bulletin或更新已有Bulletin。请求体 `CreateBulletinBody` 包含标题、内容、类型、别名等字段。当 `alias` 指定为 `agreement` 且 `type=9` 时，可用于创建隐私协议或服务条款等协议类内容。该方法调用 `BulletinHandler.CreateOrUpdateBulletin` 执行创建或更新逻辑，并返回 `ApiResponse<Bulletin>` 包装的Bulletin实体 [API/Controllers/ToolsManagement/BulletinController.cs:L32-L38]。

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| title | string | 是 | Bulletin标题 |
| content | string | 是 | Bulletin内容 |
| type | int | 是 | Bulletin类型：1=News, 2=Activity, 3=Information, 4=Annoucement, 5=Advertisement, 9=Agreement |
| alias | string | 否 | Bulletin别名，如 privacy（隐私协议）、terms（服务条款） |
| labels | string[] | 否 | 标签列表 |
| isPinned | bool | 否 | 是否置顶 |
| isCarousel | bool | 否 | 是否轮播 |
| photoUrls | string[] | 否 | 图片 URL 列表 |

**响应格式**：

| 字段 | 类型 | 说明 |
|------|------|------|
| errorCode | int | 0=成功，非 0=具体错误码 |
| data | Bulletin | 创建或更新后的Bulletin实体，包含 id、publisherId、operatorId、title、content、type、status、alias 等字段 |

#### 8.1.2. 获取协议内容 (GET /api/tools/bulletin/agreement)

**鉴权**：无（公开接口，标记 `[AllowAnonymous]`）

**描述**：根据Bulletin别名获取协议内容，如隐私协议（`privacy`）、服务条款（`terms`）。该方法调用 `BulletinHandler.GetAgreement(alias)` 查询指定别名的协议Bulletin，适用于用户注册、登录等场景下展示协议文本 [API/Controllers/ToolsManagement/BulletinController.cs:L45-L52]。

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| alias | string | 是 | Bulletin别名，如 privacy、terms |

**响应格式**：

| 字段 | 类型 | 说明 |
|------|------|------|
| errorCode | int | 0=成功 |
| data | Bulletin | 协议Bulletin实体，包含 title、content、type=9 等字段 |

#### 8.1.3. 获取前端Bulletin列表 (GET /api/tools/bulletin/bulletins)

**鉴权**：无（公开接口，标记 `[AllowAnonymous]`）

**描述**：获取面向前端用户展示的Bulletin列表，支持按类型筛选、轮播Bulletin筛选及分页。该方法调用 `BulletinHandler.GetBulletins(type, isCarousel, page, pageSize)` 查询已发布的Bulletin，并通过 `page.ToRealPage()` 和 `pageSize.ToRealPageSize()` 进行分页参数规范化 [API/Controllers/ToolsManagement/BulletinController.cs:L64-L72]。

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| type | BulletinType? | 否 | Bulletin类型（可选）：1=News, 2=Activity, 3=Information, 4=Annoucement, 5=Advertisement, 9=Agreement |
| isCarousel | bool | 否 | 是否获取轮播Bulletin，默认 false |
| page | int | 否 | 页码，默认 1 |
| pageSize | int | 否 | 每页数量，默认 10 |

**响应格式**：

| 字段 | 类型 | 说明 |
|------|------|------|
| errorCode | int | 0=成功 |
| data | Bulletin[] | Bulletin列表 |
| totalCount | int | Bulletin总数 |
| page | int | 当前页码 |
| count | int | 当前页Bulletin数量 |

ta | Bulletin[] | Bulletin列表 |
| totalCount | int | Bulletin总数 |
| page | int | 当前页码 |
| count | int | 当前页Bulletin数量 |

#### 8.1.4. 后台查询Bulletin列表 (GET /api/tools/bulletin/backend)

**鉴权**：JWT（需管理员Privilege）

**描述**：管理后台查询Bulletin列表，相比前端接口额外支持按状态筛选。该方法调用 `BulletinHandler.GetBackendBulletins(type, status, page, pageSize)` 查询Bulletin，适用于后台管理界面展示所有状态的Bulletin [API/Controllers/ToolsManagement/BulletinController.cs:L82-L90]。

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| type | BulletinType? | 否 | Bulletin类型（可选） |
| status | BulletinStatus? | 否 | Bulletin状态（可选）：1=Draft, 2=Reviewing, 3=Revision, 4=Published, 5=Expired, 6=Closed |
| page | int | 否 | 页码，默认 1 |
| pageSize | int | 否 | 每页数量，默认 10 |

**响应格式**：

| 字段 | 类型 | 说明 |
|------|------|------|
| errorCode | int | 0=成功 |
| data | Bulletin[] | Bulletin列表 |
| totalCount | int | Bulletin总数 |

#### 8.1.5. 批量审批Bulletin (POST /api/tools/bulletin/approve)

**鉴权**：JWT（需管理员Privilege）

**描述**：批量审批通过Bulletin，将Bulletin状态从 `Reviewing=2`（审核中）变更为 `Published=4`（已发布）。该方法调用 `BulletinHandler.ApproveBulletin` 执行审批逻辑，适用于后台管理员对提交审核的Bulletin进行批量通过操作 [API/Controllers/ToolsManagement/BulletinController.cs:L96-L104]。

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| ids | long[] | 是 | 待审批的Bulletin ID 列表 |

**响应格式**：

| 字段 | 类型 | 说明 |
|------|------|------|
| errorCode | int | 0=成功 |

#### 8.1.6. 退回修改Bulletin (POST /api/tools/bulletin/revision)

**鉴权**：JWT（需管理员Privilege）

**描述**：将Bulletin退回修改，使Bulletin状态从 `Reviewing=2`（审核中）变更为 `Revision=3`（退回修改）。该方法调用 `BulletinHandler.ReviseBulletin` 执行退回逻辑，适用于管理员审核不通过时退回给发布人修改 [API/Controllers/ToolsManagement/BulletinController.cs:L110-L118]。

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| ids | long[] | 是 | 待退回的Bulletin ID 列表 |

**响应格式**：

| 字段 | 类型 | 说明 |
|------|------|------|
| errorCode | int | 0=成功 |

#### 8.1.7. 关闭Bulletin (POST /api/tools/bulletin/close)

**鉴权**：JWT（需管理员Privilege）

**描述**：关闭Bulletin，使Bulletin状态变更为 `Closed=6`（已关闭）。该方法调用 `BulletinHandler.CloseBulletin` 执行关闭逻辑，适用于Bulletin到期或需要强制下架的场景 [API/Controllers/ToolsManagement/BulletinController.cs:L124-L132]。

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| ids | long[] | 是 | 待关闭的Bulletin ID 列表 |

**响应格式**：

| 字段 | 类型 | 说明 |
|------|------|------|
| errorCode | int | 0=成功 |

### 8.2. Health 健康检查

健康检查接口由 `HealthController` 提供，路由为 `GET /api/tools/health`，共 1 个端点。该接口用于服务存活探测，通常由负载均衡器、容器编排系统（如 Docker Compose）或外部监控系统定期调用，以判断 API 服务是否正常运行。该接口无需认证，属于公开接口 [API/Controllers/ToolsManagement/HealthController.cs:L20]。

#### 8.2.1. 服务健康检查 (GET /api/tools/health)

**鉴权**：无（公开接口）

**描述**：返回服务健康状态，确认 API 服务进程存活且能够正常响应 HTTP 请求。该接口不涉及数据库或其他外部依赖的检查，仅验证服务本身的可达性。

**响应格式**：

| 字段 | 类型 | 说明 |
|------|------|------|
| errorCode | int | 0=服务正常 |

**请求示例**：

```http
GET /api/tools/health
```

**响应示例**：

```json
{
  "errorCode": 0
}
```

### 8.3. WeChat 微信公众号

微信公众号接口由 `WeChatController` 提供，路由前缀为 `api/tools/wechat`，共 2 个端点。该 Controller 标记 `[AllowAnonymous]`，无需认证，由微信服务器回调调用 [API/Controllers/ToolsManagement/WeChat/WeChatController.cs:L20-L22]。Controller 通过构造函数注入 `WeChatHandler` 与 `IWeChatService`，分别处理消息业务逻辑与微信签名验证 [API/Controllers/ToolsManagement/WeChat/WeChatController.cs:L24-L26]。

微信消息相关枚举定义如下：`WeChatMessageType` 枚举包含 `Event`（事件）、`Text`（文本）、`Image`（图片）等消息类型；`WeChatMessageEvent` 枚举包含 `Subscribe`（关注）、`Unsubscribe`（取关）、`Scan`（扫码）等事件类型。微信相关错误码定义在 `ExceptionCodes` 枚举中，范围 620001-620017，包括 `InvalidWeChatAppToken=620001`、`ExamineWeChatSignatureFailed=620002`、`InvalidWeChatMessageType=620005`、`InvalidWeChatMessageEvent=620006`、`EmptyWeChatOpenId=620007` 等 [Models/Common/Enums/ExceptionCodes.cs:L6]。

#### 8.3.1. 微信服务器验证 (GET /api/tools/wechat)

**鉴权**：无（公开接口，由微信服务器回调）

**描述**：微信服务器在开发者Config URL 时会调用该接口验证签名。接口接收微信签名、时间戳、随机字符串和回复字符串四个参数，调用 `IWeChatService.ExamineSignature(signature, timestamp, nonce)` 验证签名是否合法 [API/Controllers/ToolsManagement/WeChat/WeChatController.cs:L36-L50]。签名验证逻辑在 `WeChatService.ExamineSignature` 中实现：从 `ISettingService.GetWeChatSetting()` 获取公众号Config的 `OfficalToken`，若 Token 为空则抛出 `InvalidWeChatAppToken` 异常；将 Token、timestamp、nonce 三个参数按字典序排序后拼接，进行 SHA1 哈希并与 signature 比对 [API/Common/Services/WeChatService.cs]。

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| signature | string | 是 | 微信加密签名 |
| timestamp | string | 是 | 时间戳 |
| nonce | string | 是 | 随机数 |
| echostr | string | 是 | 随机字符串，验证通过后需原样返回 |

**响应格式**：

| 字段 | 类型 | 说明 |
|------|------|------|
| body | string | 验证通过返回 echostr 原文；验证失败返回 `ApiResponse<string>` 包装的错误信息 |

**错误码**：

| errorCode | 常量名 | 说明 |
|-----------|--------|------|
| 620001 | InvalidWeChatAppToken | 微信 Token 未Config |
| 620002 | ExamineWeChatSignatureFailed | 微信签名验证失败 |

620001 | InvalidWeChatAppToken | 微信 Token 未Config |
| 620002 | ExamineWeChatSignatureFailed | 微信签名验证失败 |

#### 8.3.2. 接收微信事件推送 (POST /api/tools/wechat)

**鉴权**：无（公开接口，由微信服务器回调）

**描述**：接收微信服务器推送的消息和事件。请求体为 `WeChatMessage`，包含消息类型、内容、发送方等字段。接口首先验证签名，验证通过后将 `openid` 参数赋值给 `body.OpenId`（若为空则使用 `FromUserName`），随后调用 `WeChatHandler.ProcessMessage(body)` 处理消息 [API/Controllers/ToolsManagement/WeChat/WeChatController.cs:L68-L90]。

`WeChatHandler.ProcessMessage` 的处理流程如下 [API/Handlers/ToolsManagement/WeChat/WeChatHandler.cs]：

1. 校验 `MsgType` 是否为合法的 `WeChatMessageType` 枚举值，非法则抛出 `InvalidWeChatMessageType` 异常；
2. 校验 `OpenId` 非空，为空则抛出 `EmptyWeChatOpenId` 异常；
3. 通过 `ISettingService.GetWeChatSetting()` 获取公众号Config；
4. 调用 `IWeChatService.GetOrUpdateBasicWXAccount(setting, body.OpenId)` 获取或创建微信账号记录；
5. 若账号存在，将消息插入数据库（`Db.Insertable(body)`）；
6. 根据消息类型分发处理：`Event` 类型调用 `ProcessEventMessage`，`Text` 类型调用 `ProcessTextMessage`。

sertable(body)`）；
6. 根据消息类型分发处理：`Event` 类型调用 `ProcessEventMessage`，`Text` 类型调用 `ProcessTextMessage`。

`ProcessEventMessage` 处理微信事件，当前支持 `Subscribe`（关注）事件：回复欢迎语 `TextContent.WeChatWelcome`，并更新账号的 `Subscribe=1`、`SubscribeTime` 为当前 Unix 时间戳；若事件类型非法则抛出 `InvalidWeChatMessageEvent` 异常。`ProcessTextMessage` 处理文本消息，若内容为空则回复欢迎语。

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| signature | string | 是 | 微信加密签名 |
| timestamp | string | 是 | 时间戳 |
| nonce | string | 是 | 随机数 |
| openid | string | 否 | User OpenID，为空时使用 FromUserName |
| body | WeChatMessage | 是 | 微信消息体，包含 MsgType、Content、FromUserName、ToUserName、Event 等字段 |

**响应格式**：

| 字段 | 类型 | 说明 |
|------|------|------|
| MsgType | WeChatMessageType | 回复消息类型，若为 `None` OkResult |
| Content | string | 回复文本内容（文本消息时） |
| ToUserName | string | 接收方（原发送方） |
| FromUserName | string | 发送方（公众号原始 ID） |

**错误码**：

| errorCode | 常量名 | 说明 |
|-----------|--------|------|
| 620002 | ExamineWeChatSignatureFailed | 微信签名验证失败 |
| 620005 | InvalidWeChatMessageType | 非法的微信消息类型 |
| 620006 | InvalidWeChatMessageEvent | 非法的微信事件类型 |
| 620007 | EmptyWeChatOpenId | OpenID 为空 |

---

## 9. 用户管理接口

AgentInsightService 是一个面向 AI Agent 可Observation性与管理的 B2B SaaS 平台，用户管理接口是平台的基础核心模块，覆盖用户生命周期管理、组织与项目资源隔离、AlertConfig、Captcha获取以及用户级Config存储。本章节详细描述 `API/Controllers/UserManagement` 目录下 6 个 Controller 共 38 个 HTTP 端点的请求参数、响应格式与错误码。所有端点均返回统一包装结构 `ApiResponse<T>`，其中 `errorCode=0` 表示成功，非零值对应 `ExceptionCodes` 枚举中定义的业务错误码。鉴权方面，除注册、登录、Captcha获取等公开端点外，其余端点均要求请求头携带有效 JWT Token 或 API Key（Basic Auth），并受组织/项目角色约束。

### 9.1. Alert Alert管理

Alert管理接口由 `AlertController` 提供，路由前缀为 `api/alert`，共 7 个端点，负责Alert规则的Config、查询、创建、更新、删除以及Alert记录的读取与标记已读。Alert引擎基于 Metrics 数据（Token 消耗、费用、错误次数等）进行阈值判断，支持 System 通知与 SMS 通知两种方式。

#### 9.1.1. 获取AlertConfig (GET /api/alert/config)

**鉴权**: 无（标注 `[SkipSetUser]`，`API/Controllers/UserManagement/AlertController.cs:30`）

**描述**: 返回AlertConfig的枚举映射，包括可监控字段、比较操作符、时间单位与通知方式，供前端渲染Alert规则表单使用。

**响应格式**:

| 字段 | 类型 | 说明 |
|------|------|------|
| errorCode | int | 0=成功 |
| data.fields | object | Alert字段映射，如 `{"TotalTokens":1,"TotalCost":2,"ErrorCount":3}` |
| data.operators | object | 操作符映射，如 `{"GreaterThan":1,"LessThan":2,"EqualTo":3}` |
| data.timeunits | object | 时间单位映射，如 `{"Minute":1,"Hour":2,"Day":3}` |
| data.notifybys | object | 通知方式映射，如 `{"System":1,"SMS":2}` |

字段枚举值对应 `AlertField`（`Models/Common/Enums/AlertEnum.cs:20`）：`TotalTokens=1`、`TotalCost=2`、`ErrorCount=3`、`Latency=4`、`ErrorRate=5`、`InputTokens=6`、`OutputTokens=7`、`WarningCount=8`、`ObservationCount=9`。操作符对应 `AlertOperator`（`Models/Common/Enums/AlertEnum.cs:10`）：`GreaterThan=1`、`LessThan=2`、`EqualTo=3`、`GreaterThanOrEqualTo=4`、`LessThanOrEqualTo=5`、`NotEqualTo=6`。时间单位对应 `AlertTimeUnit`（`Models/Common/Enums/AlertEnum.cs:3`）：`Minute=1`、`Hour=2`、`Day=3`。通知方式对应 `AlertNotifyBy`（`Models/Common/Enums/AlertEnum.cs:39`）：`System=1`、`SMS=2`。

#### 9.1.2. 获取Alert列表 (GET /api/alert)

**鉴权**: JWT

**描述**: 按组织或项目维度查询Alert规则列表，`orgId` 与 `projectId` 均为可选参数。

**请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| orgId | string | 否 | Org ID |
| projectId | string | 否 | Project ID |

**错误码**:

| errorCode | 常量名 | 说明 |
|-----------|--------|------|
| 100000 | UnAuthToken | 未认证或 Token 无效 |
| 160013 | AlertOrgNotAccessible | 无权访问该组织的Alert |

#### 9.1.3. 创建Alert (POST /api/alert)

**鉴权**: JWT

**描述**: 创建新的Alert规则，需指定监控字段、比较条件、统计周期与通知方式。

**请求参数**（`CreateAlertBody`）:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | 是 | Alert名称 |
| orgid | string | 是 | Org ID |
| projectid | string | 是 | Project ID |
| periodquantity | int | 是 | 统计周期数值 |
| periodunit | int | 是 | 统计周期单位（1=Minute, 2=Hour, 3=Day） |
| frequencyquantity | int | 是 | 触发频率数值 |
| frequencyunit | int | 是 | 触发频率单位（1=Minute, 2=Hour, 3=Day） |
| field | int | 是 | 监控字段（AlertField 枚举） |
| operator | int | 是 | 比较操作符（AlertOperator 枚举） |
| value | decimal | 是 | 阈值 |
| notifyby | int | 是 | 通知方式（1=System, 2=SMS） |

**错误码**:

| errorCode | 常量名 | 说明 |
|-----------|--------|------|
| 160001 | CreateAlertFailed | 创建Alert失败 |
| 160004 | InvalidAlertPeriod | 无效的统计周期 |
| 160005 | InvalidAlertFrequency | 无效的触发频率 |
| 160006 | InvalidAlertField | 无效的监控字段 |
| 160007 | InvalidAlertOperator | 无效的比较操作符 |
| 160008 | InvalidAlertValue | 无效的阈值 |
| 160010 | InvalidAlertName | 无效的Alert名称 |
| 160011 | InvalidAlertNotifyBy | 无效的通知方式 |
| 160014 | AlertProjectNotFound | 项目不存在 |

#### 9.1.4. 更新Alert (POST /api/alert/update)

**鉴权**: JWT

**描述**: 更新已有Alert规则，请求体必须包含Alert ID，其余字段按需更新。

**请求参数**（`UpdateAlertBody`）:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | string | 是 | Alert ID |
| name | string | 否 | 新名称 |
| value | decimal | 否 | 新阈值 |
| 其他字段 | - | 否 | 同创建Alert |

**错误码**: 除创建时的校验错误外，还可能返回 `160002 UpdateAlertFailed`（更新失败）与 `160000 AlertNotFound`（Alert不存在）。

#### 9.1.5. 删除Alert (POST /api/alert/delete)

**鉴权**: JWT

**描述**: 批量删除Alert规则，`alertIds` 为逗号分隔的Alert ID 字符串。

**请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| alertIds | string | 是 | Alert ID，多个以逗号分隔 |

**错误码**: `160003 DeleteAlertFailed`（删除失败）、`160000 AlertNotFound`（Alert不存在）。

#### 9.1.6. 标记Alert记录已读 (POST /api/alert/record/read)

**鉴权**: JWT

**描述**: 将Alert记录标记为已读状态，对应 `AlertRecordState` 枚举（`Models/Common/Enums/AlertEnum.cs:33`）：`Active=1`、`Read=2`。

#### 9.1.7. 查询Alert记录 (GET /api/alert/record)

**鉴权**: JWT

**描述**: 查询Alert触发记录，可按组织、项目及记录状态筛选。

### 9.2. Captcha Captcha

Captcha接口由 `CaptchaController` 提供，路由前缀为 `api/captcha`，共 2 个端点，用于获取图形Captcha与短信Captcha。CaptchaConfig遵循 `CaptchaSetting`：图形Captcha长度 5 位、短信Captcha长度 6 位、有效期 300 秒、重发间隔 60 秒。

#### 9.2.1. 获取图形Captcha (GET /api/captcha)

**鉴权**: 无

**描述**: 生成图形Captcha图片，返回Captcha ID 与图片数据。Captcha长度由Config项 `CaptchaSetting.CaptchaCodeLength = 5` 控制，有效期 `CaptchaSetting.ExpiredSeconds = 300` 秒。

**响应格式**:

| 字段 | 类型 | 说明 |
|------|------|------|
| errorCode | int | 0=成功 |
| data.captchaId | string | Captcha ID，后续请求需携带 |
| data.image | string | Captcha图片（Base64 编码） |

#### 9.2.2. 获取短信Captcha (GET /api/captcha/sms)

**鉴权**: 无

**描述**: 向指定手机号发送短信Captcha，Captcha长度由Config项 `CaptchaSetting.SMSCodeLength = 6` 控制，重发间隔 `CaptchaSetting.ResendInterval = 60` 秒。

**请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| mobile | string | 是 | 接收Captcha的手机号 |
| captchaId | string | 是 | 图形Captcha ID |
| captchaCode | string | 是 | 图形Captcha值 |

**错误码**:

| errorCode | 常量名 | 说明 |
|-----------|--------|------|
| 110000 | SendSMSTooOften | 发送过于频繁 |
| 110001 | FailedToSendSMS | 短信发送失败 |
| 110002 | EmptyCaptcha | Captcha为空 |
| 110003 | InvalidCaptcha | Captcha无效 |
| 110004 | ErrorCaptcha | Captcha错误 |

### 9.3. Organization 组织管理

组织管理接口由 `OrganizationController` 提供，路由前缀为 `api/user/organization`，共 4 个端点，负责组织的创建、查询、更新与删除。组织是资源隔离的第一层级，项目归属于组织，PGRole获得相应Privilege。

#### 9.3.1. 创建组织 (POST /api/user/organization)

**鉴权**: JWT

**描述**: 创建新组织，创建者自动成为组织 OWNER。系统校验组织数量上限，超过限制返回 `ExceedOrgLimit`。

**请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | 是 | 组织名称 |

**错误码**:

| errorCode | 常量名 | 说明 |
|-----------|--------|------|
| 130000 | EmptyOrganizationName | 组织名称为空 |
| 130001 | OrganizationNameTooShort | 组织名称过短 |
| 130002 | OrganizationNameTooLong | 组织名称过长 |
| 130004 | CreateOrganizationFailed | 创建组织失败 |
| 130012 | ExceedOrgLimit | 超过组织数量上限 |

#### 9.3.2. 查询组织 (GET /api/user/organization)

**鉴权**: JWT

**描述**: 查询当前用户所属的组织列表，或按组织 ID 查询指定组织详情。

**请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| orgId | string | 否 | Org ID，不传返回用户所有组织 |

**错误码**: `130003 InvalidOrganization`（组织不存在）、`130009 UnauthorizedOrganizationAccess`（无权访问该组织）。

#### 9.3.3. 更新组织 (POST /api/user/organization/update)

**鉴权**: JWT（需组织 ADMIN 或 OWNER Role）

**描述**: 更新组织信息，如组织名称。Privilege校验通过 `ApiHandlerBase.RequireOrgAdmin` 强制执行。

**请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| orgId | string | 是 | Org ID |
| name | string | 是 | 新组织名称 |

**错误码**: `130005 UpdateOrganizationFailed`（更新失败）、`130009 UnauthorizedOrganizationAccess`（无权访问）。

#### 9.3.4. 删除组织 (POST /api/user/organization/delete)

**鉴权**: JWT（需组织 OWNER Role）

**描述**: 删除组织，支持批量删除（`orgIds` 为逗号分隔的字符串）。若组织下存在项目，返回 `OrganizationHasProjects`；若项目正在删除中，返回 `OrganizationProjectDeleting`。

**请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| orgIds | string | 是 | Org ID，多个以逗号分隔 |

**错误码**:

| errorCode | 常量名 | 说明 |
|-----------|--------|------|
| 130006 | DeleteOrganizationFailed | 删除组织失败 |
| 130007 | OrganizationHasProjects | 组织下存在项目，无法删除 |
| 130008 | OrganizationProjectDeleting | 组织下项目正在删除中 |

### 9.4. Project 项目管理

项目管理接口由 `ProjectController` 提供，路由前缀为 `api/user/project`，共 4 个端点。项目是 Trace 数据采集与AlertConfig的归属单元，隶属于组织。

#### 9.4.1. 创建项目 (POST /api/user/project)

**鉴权**: JWT（需组织 MEMBER 及以上角色）

**描述**: 在指定组织下创建新项目。系统校验项目数量上限，超过限制返回 `ExceedProjectLimit`。

**请求参数**（`CreateProjectBody`）:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | 是 | 项目名称 |
| orgid | string | 是 | 所属组织 ID |

**错误码**:

| errorCode | 常量名 | 说明 |
|-----------|--------|------|
| 140000 | EmptyProjectName | 项目名称为空 |
| 140001 | ProjectNameTooShort | 项目名称过短 |
| 140002 | ProjectNameTooLong | 项目名称过长 |
| 140004 | CreateProjectFailed | 创建项目失败 |
| 140007 | ExistedProjectName | 项目名称已存在 |
| 130011 | ExceedProjectLimit | 超过项目数量上限 |

#### 9.4.2. 查询项目 (GET /api/user/project)

**鉴权**: JWT

**描述**: 查询指定组织下的项目列表，可按项目 ID 过滤。

**请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| orgId | string | 是 | Org ID |
| projectId | string | 否 | Project ID，不传返回该组织下所有项目 |

**错误码**: `140003 InvalidProject`（项目不存在）、`140008 UnauthorizedProjectAccess`（无权访问该项目）。

#### 9.4.3. 更新项目 (POST /api/user/project/update)

**鉴权**: JWT（需组织 ADMIN 或项目管理员）

**描述**: 更新项目信息，如项目名称。

**请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| projectId | string | 是 | Project ID |
| name | string | 是 | 新项目名称 |

**错误码**: `140005 UpdateProjectFailed`（更新失败）、`140007 ExistedProjectName`（项目名称已存在）。

#### 9.4.4. 删除项目 (POST /api/user/project/delete)

**鉴权**: JWT（需组织 ADMIN 或 OWNER Role）

**描述**: 删除项目。删除操作通过 `BullMqService.EnqueueProjectDeleteAsync` 异步执行，涉及 Trace 数据清理。

**请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| projectId | string | 是 | Project ID |

**错误码**: `140006 DeleteProjectFailed`（删除失败）。

### 9.5. UserConfig 用户Config

用户Config接口由 `UserConfigController` 提供，路由前缀为 `api/user/config`，共 4 个端点。Config以 JSON 格式存储，支持 User、Organization、Project 三种Config类型（`UserConfigType` 枚举：`User=0`、`Organization=1`、`Project=2`），用于保存前端偏好、界面设置等非结构化数据。

#### 9.5.1. 查询用户Config (GET /api/user/config)

**鉴权**: JWT

**描述**: 按组织、项目及Config类型查询用户Config列表。

**请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| orgId | string | 否 | Org ID |
| projectId | string | 否 | Project ID |
| type | int | 否 | Config类型（0=User, 1=Organization, 2=Project） |

**响应格式**:

**鉴权**: JWT

**描述**: 按Config ID 删除用户Config。

**请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | string | 是 | Config ID |

### 9.6. User 用户生命周期

用户生命周期接口由 `UserController` 提供，路由前缀为 `api/user`，共 17 个端点，是用户管理模块的核心，覆盖注册、登录、登出、资料更新、密码重置、微信绑定、成员邀请、角色分配、API Key 管理及 Agent 额度校验等全生命周期操作。业务逻辑由 `UserHandler`（`API/Handlers/UserManagement/UserHandler.cs`）实现，依赖 `UserService` 与 `WeChatService` 完成数据持久化与微信 OAuth 交互。

#### 9.6.1. 获取当前用户信息 (GET /api/user)

**鉴权**: JWT

**描述**: 返回当前登录用户的详细信息，包括用户 ID、用户名、手机/邮箱、头像、创建时间等，以及 JWT Token、Session ID 和微信 OpenID。

**响应格式**:

| 字段 | 类型 | 说明 |
|------|------|------|
| errorCode | int | 0=成功 |
| data.id | string | User ID |
| data.name | string | 用户名 |
| data.mobile | string | 手机号/邮箱 |
| data.image | string | 头像 URL |
| data.createdat | datetime | 创建时间 |
| data.token | string | JWT Token |
| data.sessionid | string | Session ID |
| data.openid | string | 微信 OpenID |

#### 9.6.2. 注册 (POST /api/user)

**鉴权**: 无（`[AllowAnonymous]`，`API/Controllers/UserManagement/UserController.cs:43`）

**描述**: 创建新用户账号，支持邮箱/手机号 + 密码注册，需通过图形Captcha校验。

**请求参数**（`MiniUserBody`）:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| mobile | string | 是 | 邮箱或手机号 |
| password | string | 是 | 密码 |
| name | string | 否 | 用户名 |
| captchaerrorCode | string | 是 | 图形Captcha |

**错误码**:

| errorCode | 常量名 | 说明 |
|-----------|--------|------|
| 100003 | ExistedMobile | 手机号/邮箱已注册 |
| 100004 | CreateUserFailed | 创建用户失败 |
| 100019 | UserNameTooLong | 用户名过长 |
| 110003 | InvalidCaptcha | Captcha无效 |

#### 9.6.3. 更新用户资料 (POST /api/user/update)

**鉴权**: JWT

**描述**: 更新当前用户资料，如用户名、头像。

**请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | 否 | 新用户名 |
| image | string | 否 | 新头像 URL |

#### 9.6.4. 登录 (POST /api/user/login)

**鉴权**: 无（`[AllowAnonymous]`，`API/Controllers/UserManagement/UserController.cs:73`）

**描述**: 用户登录，支持 5 种登录方式（`LoginType` 枚举）：`Password=1`、`SMS=2`、`WeChat=3`、`MiniProgram=4`、`APIKey=5`。登录成功后返回用户信息，响应头包含 `access-token`。`LoginType=5` 时请求体可为空，需在 Authorization 头携带 `Basic publickey:secretkey`。

**请求参数**（`MiniUserBody`）:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| mobile | string | 条件必填 | 手机号/邮箱（Password/SMS 登录） |
| password | string | 条件必填 | 密码（Password 登录） |
| logintype | int | 是 | 登录类型（1-5） |
| captchaid | string | 条件必填 | 短信Captcha ID（SMS 登录） |
| captchaerrorCode | string | 条件必填 | 短信Captcha（SMS 登录） |
| errorCode | string | 条件必填 | 微信授权码（WeChat/MiniProgram 登录） |

**错误码**:

| errorCode | 常量名 | 说明 |
|-----------|--------|------|
| 100037 | InvalidCredentials | 凭据无效（密码错误） |
| 100038 | InvalidApiKey | API Key 无效 |
| 100041 | UserNotInitialized | 用户未初始化 |
| 110003 | InvalidCaptcha | Captcha无效 |
| 620008 | InvalidWeChatCode | 微信授权码无效 |

#### 9.6.5. 登出 (POST /api/user/logout)

**鉴权**: JWT

**描述**: 当前用户登出，使当前 Session 失效。

#### 9.6.6. 重置密码 (POST /api/user/resetpassword)

**鉴权**: 无

**描述**: 通过短信Captcha重置密码。

**请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| mobile | string | 是 | 手机号 |
| captchaid | string | 是 | 短信Captcha ID |
| captchaerrorCode | string | 是 | 短信Captcha |
| password | string | 是 | 新密码 |

**错误码**: `100040 ResetPasswordFailed`（重置失败）、`110003 InvalidCaptcha`（Captcha无效）。

#### 9.6.7. 绑定微信 (POST /api/user/bind/wechat)

**鉴权**: JWT

**描述**: 将当前用户账号与微信 OpenID 绑定，需提供微信授权码。

**请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| errorCode | string | 是 | 微信 OAuth 授权码 |

**错误码**:

| errorCode | 常量名 | 说明 |
|-----------|--------|------|
| 620009 | WeChatAccountBinded | 当前账号已绑定微信 |
| 620010 | WeChatAccountBeenBinded | 该微信已被其他账号绑定 |
| 620008 | InvalidWeChatCode | 微信授权码无效 |

#### 9.6.8. 解绑微信 (GET /api/user/unbind/wechat)

**鉴权**: JWT

**描述**: 解绑当前用户的微信账号。

**错误码**: `620011 WeChatAccountNotBinded`（未绑定微信）。

#### 9.6.9. 分配组织角色 (POST /api/user/role)

**鉴权**: JWT（需组织 ADMIN 或 OWNER Role）

**描述**: 为指定用户分配组织角色。角色枚举 `PGRole`：`NONE`、`VIEWER`、`MEMBER`、`ADMIN`、`OWNER`。不能授予高于自身级别的角色，OWNER 不能修改自身角色。

**请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| orgId | string | 是 | Org ID |
| userId | string | 是 | 目标用户 ID |
| role | int | 是 | Role（PGRole 枚举值） |

**错误码**:

| errorCode | 常量名 | 说明 |
|-----------|--------|------|
| 100023 | CannotGrantHigherRole | 不能授予高于自身级别的角色 |
| 100024 | UserAlreadyOrgMember | 用户已是组织成员 |
| 100039 | OwnerCannotModifySelfRole | OWNER 不能修改自身角色 |

#### 9.6.10. 邀请成员 (POST /api/user/invite)

**鉴权**: JWT（需组织 ADMIN 或 OWNER Role）

**描述**: 邀请用户加入组织，通过手机号/邮箱发送邀请。

**请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| orgId | string | 是 | Org ID |
| mobile | string | 是 | 被邀请人手机号/邮箱 |
| role | int | 否 | 邀请角色，默认 MEMBER |

**错误码**:

| errorCode | 常量名 | 说明 |
|-----------|--------|------|
| 100021 | EmptyInviteMobile | 邀请手机号为空 |
| 100022 | InvalidInviteMobile | 邀请手机号无效 |
| 100025 | InviteAlreadyExists | 邀请已存在 |
| 100026 | CreateInviteFailed | 创建邀请失败 |

#### 9.6.11. 查询邀请 (GET /api/user/invitation)

**鉴权**: JWT

**描述**: 查询当前用户收到的组织邀请列表。

#### 9.6.12. 删除邀请 (POST /api/user/invitation/delete)

**鉴权**: JWT

**描述**: 删除指定邀请。

**请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| invitationId | string | 是 | 邀请 ID |

**错误码**: `100027 InviteNotFound`（邀请不存在）、`100028 DeleteInviteFailed`（删除失败）。

#### 9.6.13. 创建 API Key (POST /api/user/apikey)

**鉴权**: JWT

**描述**: 创建 API Key，用于 API 访问认证。API Key 作用域枚举 `ApiKeyScope`：`PROJECT=0`、`ORGANIZATION=1`。创建时需指定作用域及对应的项目 ID 或组织 ID。

**请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | 是 | API Key 名称 |
| scope | int | 是 | 作用域（0=PROJECT, 1=ORGANIZATION） |
| projectId | string | 条件必填 | Project ID（scope=PROJECT 时必填） |
| orgId | string | 条件必填 | Org ID（scope=ORGANIZATION 时必填） |

**错误码**:

| errorCode | 常量名 | 说明 |
|-----------|--------|------|
| 100032 | CreateApiKeyFailed | 创建 API Key 失败 |
| 100035 | MissingProjectOrOrgId | 缺少项目 ID 或组织 ID |

#### 9.6.14. 查询 API Key 列表 (GET /api/user/apikey)

**鉴权**: JWT

**描述**: 查询当前用户的所有 API Key 列表。

#### 9.6.15. 删除 API Key (POST /api/user/apikey/delete)

**鉴权**: JWT

**描述**: 删除指定 API Key。

**请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| apiKeyId | string | 是 | API Key ID |

**错误码**: `100031 ApiKeyNotFound`（API Key 不存在）、`100033 DeleteApiKeyFailed`（删除失败）。

#### 9.6.16. 扣减月度 Agent 额度 (GET /api/user/privilege/agent/deduct)

**鉴权**: JWT

**描述**: 扣减当前用户所属组织的月度 Agent 调用额度，用于 Agent Session计费。

**请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| orgId | string | 是 | Org ID |
| amount | int | 是 | 扣减额度数量 |

**错误码**: `150020 UpdateAgentRateFailed`（额度更新失败）、`150007 AgentLimitExceeded`（超出 Agent 额度限制）。

#### 9.6.17. 校验 Agent 额度 (GET /api/user/privilege/agent/validate)

**鉴权**: JWT

**描述**: 校验当前用户所属组织的月度 Agent 额度是否充足。

**请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| orgId | string | 是 | Org ID |
| amount | int | 是 | 需校验的额度数量 |

**错误码**: `150007 AgentLimitExceeded`（超出 Agent 额度限制）。

---

## 10. Agents服务接口

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| model | string | 是 | 模型标识，由 LangChain.Providers.OpenAI 提供底层模型能力 |
| errorMessages | array | 是 | 聊天消息列表，格式与 OpenAI Chat Completions 一致 |
| stream | boolean | 否 | 是否启用 SSE 流式响应，默认 false |
| session_id | string | 否 | 关联的 Session ID，用于多轮对话上下文管理 |

#### 10.1.1. 响应格式

| 字段 | 类型 | 说明 |
|------|------|------|
| id | string | 响应唯一标识 |
| object | string | 固定为 `chat.completion` 或 `chat.completion.chunk`（流式） |
| choices | array | 模型生成的回复内容 |
| usage | object | Token 用量统计（非流式时返回） |

#### 10.1.2. 错误码

| errorCode | errorMessage | 说明 |
|-----------|---------|------|
| 0 | success | 成功 |
| 100000 | UnAuthToken | 未认证或 Token 无效（继承自上层 API 网关统一错误格式） |
| 999999 | DefaultException | 内部异常，经全局 ExceptionMiddleware 处理后返回标准 JSON |

#### 10.1.3. 请求示例

```json
{
  "model": "gpt-4o",
  "errorMessages": [
    {"role": "user", "content": "分析当前项目的 Token 消耗趋势"}
  ],
  "stream": true,
  "session_id": "session-123"
}
```

#### 10.1.4. 响应示例（非流式）

```json
{
  "id": "chatcmpl-123",
  "object": "chat.completion",
  "choices": [
    {
      "index": 0,
      "errorMessage": {
        "role": "assistant",
        "content": "根据最近 7 天的数据，Token 消耗呈上升趋势..."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 120,
    "completion_tokens": 85,
    "total_tokens": 205
  }
}
```

#### 10.1.5. 流式 SSE 响应

当请求中 `stream=true` 时，服务端以 `text/event-stream` 格式返回 SSE 流。每个数据块遵循 OpenAI 兼容格式，最终以 `data: [DONE]` 结束。该实现位于 `Agents/server.py` 的 `stream_response` 函数，内部通过 `renderMarkdown` 对 Markdown 内容进行渲染，并通过 `transformSuggestionsToLinks` 将建议文本转换为可点击链接（[Agents/server.py]）。

```
data: {"id":"chatcmpl-123","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"content":"根据"},"finish_reason":null}]}

data: {"id":"chatcmpl-123","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"content":"最近"},"finish_reason":null}]}

data: [DONE]
```

#### 10.1.6. 多 Agent 协作机制

```json
{
  "id": "session-123",
  "name": "Token 消耗分析",
  "context": {
    "errorMessages": [
      {"role": "user", "content": "分析当前项目的 Token 消耗趋势"}
    ]
  },
  "created_at": "2025-01-01T10:00:00Z",
  "updated_at": "2025-01-01T10:30:00Z"
}
```

#### 10.1.7. 接口详情 (DELETE /api/sessions/{session_id})

**鉴权**: 需配合上层 Yarp.ReverseProxy 反向代理传递的认证信息；或使用 SDK `agentinsight-sdk` 自动处理认证。

**描述**: 删除指定Session（`delete_session`，[Agents/server.py:633]）。

#### 10.1.8. 请求参数

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| session_id | string | 是 | Session唯一标识（路径参数） |

#### 10.1.9. 响应格式

| 字段 | 类型 | 说明 |
|------|------|------|
| success | boolean | 是否删除成功 |

#### 10.1.10. 错误码

| errorCode | errorMessage | 说明 |
|-----------|---------|------|
| 0 | success | 成功 |
| 100000 | UnAuthToken | 未认证或 Token 无效 |
| 150021 | AgentSessionNotFound | Session不存在 |

#### 10.1.11. 接口详情 (POST /api/sessions/cleanup)

**鉴权**: 需配合上层 Yarp.ReverseProxy 反向代理传递的认证信息；或使用 SDK `agentinsight-sdk` 自动处理认证。

**描述**: 清理所有过期Session（`cleanup_expired_sessions`，[Agents/server.py:641]）。该端点由内部定时任务或管理员调用，用于释放过期Session占用的存储资源。

#### 10.1.12. 请求参数

无。

#### 10.1.13. 响应格式

| 字段 | 类型 | 说明 |
|------|------|------|
| cleaned_count | integer | 清理的过期Session数量 |

#### 10.1.14. 错误码

| errorCode | errorMessage | 说明 |
|-----------|---------|------|
| 0 | success | 成功 |
| 100000 | UnAuthToken | 未认证或 Token 无效 |

#### 10.1.15. 响应示例

```json
{
  "cleaned_count": 5
}
```

### 10.2. Agent 注册与列表

Agent 注册与列表模块提供已注册 Agent 的查询能力，便于客户端发现可用 Agent 类型及其能力描述。

#### 10.2.1. 接口详情 (GET /api/agents)

**鉴权**: 需配合上层 Yarp.ReverseProxy 反向代理传递的认证信息；或使用 SDK `agentinsight-sdk` 自动处理认证。

**描述**: 列出所有已注册的 Agent（`list_agents`，[Agents/server.py:649]），返回每个 Agent 的名称、描述、能力标签等元信息。

#### 10.2.2. 请求参数

无。

#### 10.2.3. 响应格式

| 字段 | 类型 | 说明 |
|------|------|------|
| agents | array | Agent 列表，每个元素包含 id、name、description、capabilities 等字段 |

#### 10.2.4. 错误码

| errorCode | errorMessage | 说明 |
|-----------|---------|------|
| 0 | success | 成功 |
| 100000 | UnAuthToken | 未认证或 Token 无效 |

#### 10.2.5. 响应示例

```json
{
  "agents": [
    {
      "id": "insight",
      "name": "Insight Agent",
      "description": "核心洞察分析 Agent，负责数据解读与结论生成",
      "capabilities": ["analysis", "reporting"]
    },
    {
      "id": "researcher",
      "name": "Researcher Agent",
      "description": "研究型任务 Agent，负责信息检索与资料整理",
      "capabilities": ["search", "summarization"]
    },
    {
      "id": "custom_service",
      "name": "Custom Service Agent",
      "description": "自定义服务 Agent，支持用户扩展特定领域能力",
      "capabilities": ["custom"]
    }
  ]
}
```

### 10.3. SDK 调用示例

使用 `agentinsight-sdk` 调用 `/api/agent/insight` 端点的示例代码如下：

```python
from agentinsight_sdk import AgentInsightClient

client = AgentInsightClient(
    api_key="your-api-key",
    base_url="https://your-domain.com"
)

# 调用 ChatCompletion 方法
response = client.chat.completions.create(
    model="gpt-4o",
    errorMessages=[
        {"role": "user", "content": "分析当前项目的 Token 消耗趋势"}
    ],
    stream=True
)

",
    errorMessages=[
        {"role": "user", "content": "分析当前项目的 Token 消耗趋势"}
    ],
    stream=True
)

# 流式处理响应
for chunk in response:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="")
```

SDK 自动处理认证信息的注入，无需手动附加请求头。

---

## 11. AgentConfigController 接口


本章共覆盖 3 个 HTTP 端点，每个端点一个接口卡片。


### 11.1. API-028 GetAgentConfig (GET /api/agent/config)

- **鉴权**: 无（代码中未标注 `[Authorize]` 特性）
- **描述**: 获取当前 Agent 的Config信息。该方法为无参 GET 请求，用于查询 Agent 的Config详情。
- **请求参数**: 无

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| - | - | - | 该接口不接受任何查询参数或请求体 |

- **响应格式**: `IActionResult`

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | Agent Config数据对象，包含 Agent 的详细Config信息 |
| data.agentConfigId | string | Agent Config唯一标识 |
| data.agentType | int | Agent 类型 |
| data.modelName | string | 使用的模型名称 |
| data.temperature | number | 温度参数，控制生成随机性 |
| data.maxTokens | int | 最大 Token 数限制 |
| data.systemPrompt | string | 系统提示词 |
| data.environment | string | 运行环境，参考 `Environment` 枚举（`DEVELOPMENT`、`STAGING`、`PRODUCTION`） |
| data.version | string | Config版本号 |
| data.createdAt | string (datetime) | Config创建时间 |
| data.updatedAt | string (datetime) | Config最后更新时间 |
| errorCode | int | 业务状态码，`0` 表示成功，非 `0` 表示失败 |
| errorMessage | string | 结果描述信息 |

- **错误码**: 从 `ExceptionCodes` 枚举中提取

| errorCode | errorMessage | 说明 |
|-----------|---------|------|
| 0 | Success | 请求成功 |
| 100000 | UnAuthToken | Token 未认证或已过期 |
| 150022 | AgentConfigNotFound | 未找到对应的 Agent Config |
| 150004 | AgentSettingNotConfig | Agent 设置未Config |
| 999999 | DefaultException | 服务器内部异常 |

- **请求示例**:
```json
// GET /api/agent/config
// 无请求体
```

- **响应示例**:

**成功响应 (HTTP 200)**:
```json
{
  "errorCode": 0,
  "errorMessage": "Success",
  "data": {
    "agentConfigId": "cfg_8f7e6d5c4b3a",
    "agentType": 1,
    "modelName": "gpt-4o",
    "temperature": 0.7,
    "maxTokens": 4096,
    "systemPrompt": "You are a helpful assistant.",
    "environment": "PRODUCTION",
    "version": "1.2.0",
    "createdAt": "2025-06-15T08:30:00Z",
    "updatedAt": "2025-06-20T14:45:00Z"
  }
}
```

**失败响应 (HTTP 401)**:
```json
{
  "errorCode": 100000,
  "errorMessage": "UnAuthToken",
  "data": null
}
```

**失败响应 (HTTP 404)**:
```json
{
  "errorCode": 150022,
  "errorMessage": "AgentConfigNotFound",
  "data": null
}
```

### 11.2. API-040 AgentConfigController.Delete (GET /api/agent/config/delete)

- **鉴权**: 无（代码中未标注 `[Authorize]` 特性）
- **描述**: 删除指定的 Agent Config。该接口通过 GET 请求触发删除操作，用于移除 Agent 管理模块中的Config项。
- **请求参数**: 无（该方法签名 `public async Task<IActionResult> Delete()` 未声明任何参数）

- **响应格式**: 标准 HTTP 响应，无特定响应体结构。

| 字段 | 类型 | 说明 |
|------|------|------|
| HTTP 状态码 | int | 200 OK 表示删除成功；其他状态码表示失败 |

- **错误码**: 无特定业务错误码（该方法未返回结构化错误码，仅通过 HTTP 状态码指示结果）

| errorCode | errorMessage | 说明 |
|-----------|---------|------|
| 200 | OK | 删除成功 |
| 401 | Unauthorized | 未认证（若未来添加鉴权） |
| 404 | Not Found | 目标 Agent Config不存在 |
| 500 | Internal Server Error | 服务器内部错误 |

- **请求示例**: 
```http
GET /api/agent/config/delete HTTP/1.1
Host: localhost
```

- **响应示例**:

**成功响应 (200 OK)**:
```json
{
  "statusCode": 200,
  "errorMessage": "Agent Config删除成功"
}
```

**失败响应 (404 Not Found)**:
```json
{
  "statusCode": 404,
  "errorMessage": "Agent Config不存在"
}
```

### 11.3. API-022 AgentConfigController.Post (POST /api/agent/config)

- **鉴权**: 无 `[Authorize]` 注解，无需鉴权
- **描述**: 创建或更新 Agent Config。该方法接收一个 JSON 字符串作为请求体，用于提交 Agent Config数据。Config内容由调用方以原始 JSON 字符串形式提供，服务端解析并持久化。该接口通常用于 Agent 的初始化Config或动态更新Config场景。

- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| body | string | 是 | Agent Config的 JSON 字符串。该字符串包含 Agent 的完整Config信息，例如模型参数、Prompt 模板、工具调用Config等。请求体为原始 JSON 字符串，需确保格式合法且不超过服务端限制。 |

- **响应格式**:

| 字段 | 类型 | 说明 |
|------|------|------|
| errorCode | int | 业务状态码。`0` 表示成功，非 `0` 表示失败。 |
| errorMessage | string | 状态描述信息。成功时为 `"success"`，失败时为具体错误信息。 |
| data | object | 响应数据。成功时返回 `null`，失败时无此字段。 |

- **错误码**:

| errorCode | errorMessage | 说明 |
|-----------|---------|------|
| 150004 | AgentSettingNotConfig | Agent Config未设置，无法完成Config操作。 |
| 150007 | AgentLimitExceeded | Agent 数量超出限制，无法创建新的 Agent Config。 |
| 150008 | DuplicateUserConfig | 用户Config重复，已存在相同的Config项。 |
| 150022 | AgentConfigNotFound | 未找到指定的 Agent Config，无法执行更新操作。 |
| 999999 | DefaultException | 服务器内部错误，请联系管理员。 |

- **请求示例**:

```json
{
  "body": "{\"agentName\":\"research-agent\",\"model\":\"gpt-4o\",\"temperature\":0.7,\"maxTokens\":2048,\"tools\":[\"web_search\",\"errorCode_interpreter\"],\"promptTemplate\":\"You are a research assistant...\",\"projectId\":\"proj_8f3e2a1c9b4d\"}"
}
```

- **响应示例**:

**成功响应**:
```json
{
  "errorCode": 0,
  "errorMessage": "success",
  "data": null
}
```

**失败响应** (Agent Config未设置):
```json
{
  "errorCode": 150004,
  "errorMessage": "AgentSettingNotConfig",
  "data": null
}
```

---

## 12. AgentReportController 接口

本章共覆盖 3 个 HTTP 端点，每个端点一个接口卡片。

### 12.1. API-035 GetTemplates (GET /api/agent/report)

- **鉴权**: 通过全局认证管道（JWT 或 API Key）进行身份验证，代码中未标注 `[Authorize]` 特性，但全局管道会解析认证信息。
- **描述**: 获取 Agent 报告模板列表，支持按 ID 查询、筛选预定义模板，并支持分页。

- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `id` | string | 否 | 报告模板的唯一标识符。若提供，则返回该模板的详细信息。 |
| `includedpredefined` | bool | 否 | 是否包含预定义模板。默认值为 `false`。 |
| `includedpredefinedonly` | bool | 否 | 是否仅返回预定义模板。默认值为 `false`。 |
| `page` | int | 否 | 页码，从 1 开始。默认值为 `AgentInsightConst.DefaultPage`（通常为 1）。 |
| `pageSize` | int | 否 | 每页记录数。默认值为 `AgentInsightConst.DefaultPageSize`（通常为 20）。 |

- **响应格式**:

| 字段 | 类型 | 说明 |
|---|---|---|
| `errorCode` | int | 业务状态码。`0` 表示成功，非 `0` 表示失败。 |
| `errorMessage` | string | 状态描述信息。 |
| `data` | object | 响应数据。 |
| `data.items` | array | 报告模板列表。 |
| `data.items[].id` | string | 模板 ID。 |
| `data.items[].name` | string | 模板名称。 |
| `data.items[].description` | string | 模板描述。 |
| `data.items[].isPredefined` | bool | 是否为预定义模板。 |
| `data.items[].createdAt` | string | 模板创建时间（ISO 8601 格式）。 |
| `data.items[].updatedAt` | string | 模板更新时间（ISO 8601 格式）。 |
| `data.total` | int | 符合条件的模板总数。 |
| `data.page` | int | 当前页码。 |
| `data.pageSize` | int | 每页记录数。 |

- **错误码**:

| errorCode | errorMessage | 说明 |
|---|---|---|
| `150023` | AgentReportTemplateNotFound | 指定的报告模板不存在。 |
| `150024` | EmptyAgentReportTemplateName | 报告模板名称为空。 |
| `100000` | UnAuthToken | 未认证或 Token 无效。 |
| `999999` | DefaultException | 服务器内部错误。 |

- **请求示例**:

```http
GET /api/agent/report?id=template_001&includedpredefined=true&page=1&pageSize=20
```

- **响应示例**:

**成功响应**:

```json
{
  "errorCode": 0,
  "errorMessage": "success",
  "data": {
    "items": [
      {
        "id": "template_001",
        "name": "日常运营报告",
        "description": "每日 Agent 运行状态汇总",
        "isPredefined": true,
        "createdAt": "2025-01-01T10:00:00Z",
        "updatedAt": "2025-01-02T10:00:00Z"
      },
      {
        "id": "template_002",
        "name": "成本分析报告",
        "description": "Token 消耗与成本分析",
        "isPredefined": false,
        "createdAt": "2025-01-03T10:00:00Z",
        "updatedAt": "2025-01-04T10:00:00Z"
      }
    ],
    "total": 2,
    "page": 1,
    "pageSize": 20
  }
}
```

**失败响应**:

```json
{
  "errorCode": 150023,
  "errorMessage": "AgentReportTemplateNotFound",
  "data": null
}
```

### 12.2. API-048 DeleteTemplates (GET /api/agent/report/delete)

- **鉴权**: 通过全局认证管道（JWT 或 API Key）进行身份验证，代码中未标注 `[Authorize]` 特性。
- **描述**: 根据传入的模板 ID 列表删除 Agent 报告模板。

- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| ids | string | 条件必填 | 待删除的 Agent 报告模板 ID 列表，多个 ID 使用逗号分隔。若为空或 null，则不执行删除操作。 |

- **响应格式**:

| 字段 | 类型 | 说明 |
|------|------|------|
| errorCode | int | 业务状态码。`0` 表示成功，非 `0` 表示失败。 |
| errorMessage | string | 响应消息，成功时为 "success"。 |
| data | object | 响应数据，删除成功时返回 null。 |
| traceId | string | 请求Trace ID，用于日志Trace和问题排查。 |
| timestamp | long | 服务器响应时间戳（Unix 毫秒）。 |

- **错误码**:

| errorCode | errorMessage | 说明 |
|-----------|---------|------|
| 150023 | AgentReportTemplateNotFound | 未找到指定的 Agent 报告模板，可能已被删除或 ID 不存在。 |
| 100000 | UnAuthToken | 未认证的 Token，Token 无效或已过期。 |
| 999999 | DefaultException | 服务器内部错误，发生未预期的异常。 |

- **请求示例**:

```http
GET /api/agent/report/delete?ids=1001,1002,1003
```

- **响应示例**:

**成功响应:**

```json
{
  "errorCode": 0,
  "errorMessage": "success",
  "data": null,
  "traceId": "a3f2b8c1-9d4e-4f6a-8b2c-5e7d1a3f9c0b",
  "timestamp": 1735785600000
}
```

**失败响应 (AgentReportTemplateNotFound):**

```json
{
  "errorCode": 150023,
  "errorMessage": "AgentReportTemplateNotFound",
  "data": null,
  "traceId": "b7c9d2e3-4f5a-4b6c-8d7e-9f0a1b2c3d4e",
  "timestamp": 1735785600000
}
```

### 12.3. API-001 CreateOrUpdateTemplate (POST /api/agent/report)

- **鉴权**: 通过全局认证管道（JWT 或 API Key）进行身份验证，代码中未标注 `[Authorize]` 特性。
- **描述**: 创建或更新 Agent 报告模板。根据请求体中的模板名称判断是新建模板还是更新已有模板，并执行相应的持久化操作。

- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `name` | string | 是 | 报告模板名称，用于标识模板。若系统中已存在同名模板，则执行更新操作；否则创建新模板。 |
| `content` | string | 是 | 报告模板的详细内容，支持 Markdown 或纯文本格式。 |
| `description` | string | 否 | 模板描述信息，用于说明模板的用途或适用范围。 |
| `isDefault` | boolean | 否 | 是否将该模板设为默认模板。默认值为 `false`。当设为 `true` 时，该模板将作为新建 Agent 时的默认报告模板。 |
| `projectId` | string | 否 | 模板所属的 Project ID。若为空，则模板为全局模板，适用于所有 Project。 |
| `tags` | array[string] | 否 | 模板标签列表，用于分类和检索。 |

- **响应格式**:

| 字段 | 类型 | 说明 |
|---|---|---|
| `errorCode` | int | 业务状态码。`0` 表示成功，非 `0` 表示失败。 |
| `errorMessage` | string | 状态描述信息。成功时为 `"success"`，失败时为具体错误信息。 |
| `data` | object | 响应数据。成功时包含创建的模板信息，失败时为 `null`。 |
| `data.id` | string | 模板的唯一标识 ID。 |
| `data.name` | string | 模板名称。 |
| `data.content` | string | 模板内容。 |
| `data.description` | string | 模板描述。 |
| `data.isDefault` | boolean | 是否为默认模板。 |
| `data.projectId` | string | 所属 Project ID，全局模板为 `null`。 |
| `data.tags` | array[string] | 模板标签列表。 |
| `data.createdAt` | string | 模板创建时间（ISO 8601 格式）。 |
| `data.updatedAt` | string | 模板最后更新时间（ISO 8601 格式）。 |

- **错误码**:

| errorCode | errorMessage | 说明 |
|---|---|---|
| `150023` | AgentReportTemplateNotFound | 更新模板时，指定的模板不存在或已被删除。 |
| `150024` | EmptyAgentReportTemplateName | 请求体中 `name` 字段为空或仅包含空白字符。 |
| `100000` | UnAuthToken | 未提供有效的身份验证 Token。 |
| `999999` | DefaultException | 服务器内部错误，无法完成请求。 |

- **请求示例**:

```http
POST /api/agent/report
Content-Type: application/json

{
  "name": "周报模板",
  "content": "# 周报\n## 本周完成\n- 任务一\n- 任务二\n## 下周计划\n- 任务三",
  "description": "用于生成 Agent 每周工作报告的模板",
  "isDefault": true,
  "projectId": "proj_8f3a2b1c",
  "tags": ["weekly", "report"]
}
```

- **响应示例**:

**成功响应**:

```json
{
  "errorCode": 0,
  "errorMessage": "success",
  "data": {
    "id": "tmpl_5e7d9c2a",
    "name": "周报模板",
    "content": "# 周报\n## 本周完成\n- 任务一\n- 任务二\n## 下周计划\n- 任务三",
    "description": "用于生成 Agent 每周工作报告的模板",
    "isDefault": true,
    "projectId": "proj_8f3a2b1c",
    "tags": ["weekly", "report"],
    "createdAt": "2025-01-15T10:30:00Z",
    "updatedAt": "2025-01-15T10:30:00Z"
  }
}
```

**失败响应** (模板名称缺失):

```json
{
  "errorCode": 150024,
  "errorMessage": "EmptyAgentReportTemplateName",
  "data": null
}
```

**失败响应** (更新不存在的模板):

```json
{
  "errorCode": 150023,
  "errorMessage": "AgentReportTemplateNotFound",
  "data": null
}
```

---

## 13. AgentSessionController 接口

本章共覆盖 3 个 HTTP 端点，每个端点一个接口卡片。

### 13.1. API-021 获取 Agent Session 列表 (GET /api/agent/session)

- **鉴权**: 无 `[Authorize]` 注解，无需鉴权
- **描述**: 根据可选的 Session ID 分页查询 Agent Session 列表。若提供 `id` 则返回单个 Session 详情，否则返回分页列表。
- **所属类**: `AgentSessionController` (`API/Controllers/AgentManagement/AgentSessionController.cs:33`)

- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | string | 否 | Agent Session 的唯一标识符。提供时返回单个 Session 详情；不提供时返回分页列表。 |
| page | int | 否 | 页码，从 1 开始。 |
| pageSize | int | 否 | 每页条数。 |

- **响应格式**:

| 字段 | 类型 | 说明 |
|------|------|------|
| id | string | Agent Session 的唯一标识符 |
| projectId | string | 关联的项目 ID |
| name | string | Session 名称 |
| environment | string | 环境标识 |
| version | string | 版本号 |
| release | string | 发布标识 |
| tags | array | 标签列表 |
| bookmarked | boolean | 是否被标记 |
| latency | number | 延迟时间（毫秒） |
| inputTokens | number | 输入 Token 数 |
| outputTokens | number | 输出 Token 数 |
| totalTokens | number | 总 Token 数 |
| inputCost | number | 输入成本 |
| outputCost | number | 输出成本 |
| totalCost | number | 总成本 |
| level | string | 日志级别 |
| warningCount | number | 警告数量 |
| errorCount | number | 错误数量 |
| defaultCount | number | 默认计数 |
| debugCount | number | 调试计数 |
| modelNames | array | 使用的模型名称列表 |
| scoresAvg | number | 平均得分 |
| timestamp | datetime | 时间戳 |

- **错误码**:

| errorCode | errorMessage | 说明 |
|-----------|---------|------|
| 150021 | AgentSessionNotFound | 未找到指定的 Agent Session |
| 150000 | EmptyProjectId | Project ID 为空 |
| 100000 | UnAuthToken | 未认证或 Token 无效 |
| 999999 | DefaultException | 服务器内部错误 |

- **请求示例**:

```json
{
  "id": "session_1234567890",
  "page": 1,
  "pageSize": 20
}
```

- **响应示例**:

**成功响应**:
```json
{
  "errorCode": 200,
  "data": {
    "id": "session_1234567890",
    "projectId": "project_abc123",
    "name": "Test Session",
    "environment": "production",
    "version": "1.0.0",
    "release": "release-1",
    "tags": ["test", "demo"],
    "bookmarked": false,
    "latency": 125.5,
    "inputTokens": 1500,
    "outputTokens": 800,
    "totalTokens": 2300,
    "inputCost": 0.015,
    "outputCost": 0.008,
    "totalCost": 0.023,
    "level": "info",
    "warningCount": 2,
    "errorCount": 0,
    "defaultCount": 10,
    "debugCount": 5,
    "modelNames": ["gpt-4", "gpt-3.5-turbo"],
    "scoresAvg": 0.95,
    "timestamp": "2024-01-15T10:30:00Z"
  },
  "errorMessage": "success"
}
```

**失败响应**:
```json
{
  "errorCode": 150021,
  "data": null,
  "errorMessage": "AgentSessionNotFound"
}
```

### 13.2. API-021 删除 Agent Session (GET /api/agent/session/delete)

- **鉴权**: 需要 JWT JWT Bearer Token Token（Controller类标注 `[Authorize]`）
- **描述**: 根据传入的 Session ID 列表删除对应的 Agent Session 记录。支持单个或批量删除（逗号分隔多个 ID）。
- **所属类**: `AgentSessionController` (`API/Controllers/AgentManagement/AgentSessionController.cs:46`)

#### 13.2.1. 请求参数

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `ids` | `string` | 是 | 待删除的 Agent Session ID 列表，多个 ID 使用英文逗号 `,` 分隔。对应 `AgentSessionNotFound = 150021` 错误码。 |

#### 13.2.2. 响应格式

| 字段 | 类型 | 说明 |
|------|------|------|
| `errorCode` | `int` | 业务状态码。`0` 表示成功，非 `0` 表示失败（对应 `ExceptionCodes` 枚举）。 |
| `errorMessage` | `string` | 状态描述信息。成功时为 `"success"`，失败时为具体错误信息。 |
| `data` | `object` | 成功时为 `null`，失败时为 `null`。 |

#### 13.2.3. 错误码

| errorCode | errorMessage | 说明 |
|-----------|---------|------|
| `0` | `success` | 删除成功 |
| `150021` | `AgentSessionNotFound` | 未找到对应的 Agent Session，无法删除 |
| `100000` | `UnAuthToken` | Token 无效或已过期，认证失败 |
| `999999` | `DefaultException` | 服务器内部错误，删除过程中发生未预期的异常 |

#### 13.2.4. 请求示例

```http
GET /api/agent/session/delete?ids=session-001%2Csession-002 HTTP/1.1
Host: localhost
Authorization: JWT Bearer Token eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c
```

#### 13.2.5. 响应示例

**成功响应 (HTTP 200)**

```json
{
  "errorCode": 0,
  "errorMessage": "success",
  "data": null
}
```

**失败响应 - Agent Session 不存在 (HTTP 200)**

```json
{
  "errorCode": 150021,
  "errorMessage": "AgentSessionNotFound",
  "data": null
}
```

**失败响应 - 认证失败 (HTTP 401)**

```json
{
  "errorCode": 100000,
  "errorMessage": "UnAuthToken",
  "data": null
}
```

### 13.3. API-021 创建 Agent Session (POST /api/agent/session)

- **鉴权**: 无（未标注 `[Authorize]` 注解）
- **描述**: 创建新的 Agent Session，用于启动一次 Agent 交互Session。
- **所属类**: `AgentSessionController` (`API/Controllers/AgentManagement/AgentSessionController.cs:60`)

- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `projectId` | string | 是 | Project ID，标识 Session 所属项目 |
| `agentId` | string | 是 | Agent ID，标识要启动的 Agent |
| `input` | string | 是 | 用户输入内容，作为 Agent Session的初始消息 |
| `sessionId` | string | 否 | 已有 Session ID，用于继续已有Session；不传则创建新 Session |

- **响应格式**:

| 字段 | 类型 | 说明 |
|---|---|---|
| `sessionId` | string | 新创建或继续的 Session ID |
| `traceId` | string | 本次Session的 Trace ID，用于Trace和Observation |
| `output` | string | Agent 的响应输出内容 |
| `createdAt` | string | Session 创建时间（ISO 8601 格式） |

- **错误码**:

| errorCode | errorMessage | 说明 |
|---|---|---|
| `150000` | `EmptyProjectId` | Project ID 为空 |
| `150021` | `AgentSessionNotFound` | 指定的 Session 不存在或已过期 |
| `150022` | `AgentConfigNotFound` | 未找到 Agent Config，无法启动Session |
| `100000` | `UnAuthToken` | 未认证或 Token 无效 |
| `999999` | `DefaultException` | 服务器内部错误 |

- **请求示例**:

```json
{
  "projectId": "proj_8f3a2b1c",
  "agentId": "agent_research_01",
  "input": "请分析最近一周的销售数据趋势",
  "sessionId": null
}
```

- **响应示例**:

**成功响应 (HTTP 200)**:
```json
{
  "sessionId": "sess_5e7d9c2a",
  "traceId": "trace_1a2b3c4d5e6f",
  "output": "根据最近一周的销售数据，整体呈上升趋势，环比增长 12.5%。其中华东地区贡献最大，占比 38%。",
  "createdAt": "2025-07-11T10:30:00Z"
}
```

**失败响应 (HTTP 400)**:
```json
{
  "errorCode": 150000,
  "errorMessage": "EmptyProjectId",
  "details": "Project ID 不能为空"
}
```

---

## 14. AlertController 接口

本章覆盖 `API/Controllers/UserManagement/AlertController.cs` 中定义的 7 个 HTTP 端点，每个端点一个接口卡片。

### 14.1. API-001 GetConfig (GET /api/alert/config)

- **鉴权**: 无
- **描述**: 获取 Alert Config信息。
- **所属文件**: `API/Controllers/UserManagement/AlertController.cs:30`
- **所属类**: `AlertController`
- **方法**: `GetConfig`

- **请求参数**: 无

- **响应格式**:

| 字段 | 类型 | 说明 |
|---|---|---|
| errorCode | int | 状态码，0 表示成功 |
| errorMessage | string | 提示信息 |
| data | object | 返回的Config数据 |
| data.alertTimeUnit | object | Alert 时间单位Config |
| data.alertTimeUnit.Minute | int | 分钟，值为 1 |
| data.alertTimeUnit.Hour | int | 小时，值为 2 |
| data.alertTimeUnit.Day | int | 天，值为 3 |
| data.alertOperator | object | Alert 操作符Config |
| data.alertOperator.GreaterThan | int | 大于，值为 1 |
| data.alertOperator.LessThan | int | 小于，值为 2 |
| data.alertOperator.EqualTo | int | 等于，值为 3 |
| data.alertOperator.GreaterThanOrEqualTo | int | 大于等于，值为 4 |
| data.alertOperator.LessThanOrEqualTo | int | 小于等于，值为 5 |
| data.alertOperator.NotEqualTo | int | 不等于，值为 6 |
| data.alertField | object | Alert 字段Config |
| data.alertField.TotalTokens | int | Token 总数，值为 1 |
| data.alertField.TotalCost | int | 总成本，值为 2 |
| data.alertField.ErrorCount | int | 错误数，值为 3 |
| data.alertField.Latency | int | 延迟，值为 4 |
| data.alertField.ErrorRate | int | 错误率，值为 5 |
| data.alertField.InputTokens | int | 输入 Token 数，值为 6 |
| data.alertField.OutputTokens | int | 输出 Token 数，值为 7 |
| data.alertField.WarningCount | int | 警告数，值为 8 |
| data.alertField.ObservationCount | int | Observation 数，值为 9 |
| data.alertRecordState | object | Alert 记录状态Config |
| data.alertRecordState.Active | int | 激活，值为 1 |
| data.alertRecordState.Read | int | 已读，值为 2 |
| data.alertNotifyBy | object | Alert 通知方式Config |
| data.alertNotifyBy.System | int | 系统通知，值为 1 |
| data.alertNotifyBy.SMS | int | 短信通知，值为 2 |

- **错误码**:

| errorCode | errorMessage | 说明 |
|---|---|---|
| 100000 | UnAuthToken | 未认证的 Token |
| 999999 | DefaultException | 默认异常 |

- **请求示例**:

```json
{}
```

- **响应示例**:

```json
// 成功响应
{
  "errorCode": 0,
  "errorMessage": "success",
  "data": {
    "alertTimeUnit": {
      "Minute": 1,
      "Hour": 2,
      "Day": 3
    },
    "alertOperator": {
      "GreaterThan": 1,
      "LessThan": 2,
      "EqualTo": 3,
      "GreaterThanOrEqualTo": 4,
      "LessThanOrEqualTo": 5,
      "NotEqualTo": 6
    },
    "alertField": {
      "TotalTokens": 1,
      "TotalCost": 2,
      "ErrorCount": 3,
      "Latency": 4,
      "ErrorRate": 5,
      "InputTokens": 6,
      "OutputTokens": 7,
      "WarningCount": 8,
      "ObservationCount": 9
    },
    "alertRecordState": {
      "Active": 1,
      "Read": 2
    },
    "alertNotifyBy": {
      "System": 1,
      "SMS": 2
    }
  }
}
```

```json
// 失败响应 - 未认证
{
  "errorCode": 100000,
  "errorMessage": "UnAuthToken",
  "data": null
}
```

### 14.2. API-047 Get (GET /api/alert)

- **鉴权**: 需要 JWT JWT Bearer Token Token（从 `AlertController` 类级 `[Authorize]` 注解推断）
- **描述**: 根据组织 ID 和项目 ID 查询符合条件的Alert规则列表。
- **所属文件**: `API/Controllers/UserManagement/AlertController.cs:47`
- **所属类**: `AlertController`
- **方法**: `Get`

#### 14.2.1. 请求参数

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `orgId` | string | 否 | Org ID，用于过滤属于该组织的Alert规则。 |
| `projectId` | string | 否 | Project ID，用于过滤属于该项目的Alert规则。 |

#### 14.2.2. 响应格式

| 字段 | 类型 | 说明 |
|------|------|------|
| `errorCode` | `int` | 业务状态码，`0` 表示成功，非 `0` 表示失败。 |
| `errorMessage` | `string` | 提示信息，成功时为 `"success"`。 |
| `data` | `array` | Alert规则列表。 |
| `data[].id` | `string` | Alert规则 ID。 |
| `data[].name` | `string` | Alert规则名称。 |
| `data[].projectId` | `string` | 所属项目 ID。 |
| `data[].orgId` | `string` | 所属组织 ID。 |
| `data[].field` | `int` | 监控字段，枚举值见下方说明。 |
| `data[].operator` | `int` | 比较运算符，枚举值见下方说明。 |
| `data[].value` | `decimal` | 阈值。 |
| `data[].timeUnit` | `int` | 时间单位，枚举值见下方说明。 |
| `data[].timeValue` | `int` | 时间值。 |
| `data[].notifyBy` | `int` | 通知方式，枚举值见下方说明。 |
| `data[].createdAt` | `DateTime` | 创建时间。 |
| `data[].updatedAt` | `DateTime` | 更新时间。 |

**`AlertField` 枚举值**: `TotalTokens` (1), `TotalCost` (2), `ErrorCount` (3), `Latency` (4), `ErrorRate` (5), `InputTokens` (6), `OutputTokens` (7), `WarningCount` (8), `ObservationCount` (9)

**`AlertOperator` 枚举值**: `GreaterThan` (1), `LessThan` (2), `EqualTo` (3), `GreaterThanOrEqualTo` (4), `LessThanOrEqualTo` (5), `NotEqualTo` (6)

**`AlertTimeUnit` 枚举值**: `Minute` (1), `Hour` (2), `Day` (3)

**`AlertNotifyBy` 枚举值**: `System` (1), `SMS` (2)

#### 14.2.3. 错误码

| errorCode | errorMessage | 说明 |
|-----------|---------|------|
| `100000` | `UnAuthToken` | 未提供或提供了无效的认证 Token。 |
| `160000` | `AlertNotFound` | 未找到指定的Alert规则。 |
| `160013` | `AlertOrgNotAccessible` | 当前用户无权访问该组织下的Alert规则。 |
| `160014` | `AlertProjectNotFound` | 未找到指定的项目。 |
| `999999` | `DefaultException` | 服务器内部错误。 |

#### 14.2.4. 请求示例

```bash
curl -X GET "https://api.agentinsightservice.com/api/alert?orgId=org_8f7e3a2b1c&projectId=proj_5d4c3b2a1e" \
  -H "Authorization: JWT Bearer Token <your_jwt_token>"
```

#### 14.2.5. 响应示例

**成功响应**:

```json
{
  "errorCode": 0,
  "errorMessage": "success",
  "data": [
    {
      "id": "alert_1a2b3c4d5e",
      "name": "高错误率Alert",
      "projectId": "proj_5d4c3b2a1e",
      "orgId": "org_8f7e3a2b1c",
      "field": 5,
      "operator": 1,
      "value": 10.5,
      "timeUnit": 2,
      "timeValue": 1,
      "notifyBy": 1,
      "createdAt": "2024-05-20T10:30:00Z",
      "updatedAt": "2024-05-20T10:30:00Z"
    }
  ]
}
```

**失败响应** (未授权):

```json
{
  "errorCode": 100000,
  "errorMessage": "UnAuthToken",
  "data": null
}
```

**失败响应** (组织不可访问):

```json
{
  "errorCode": 160013,
  "errorMessage": "AlertOrgNotAccessible",
  "data": null
}
```

### 14.3. API-061 Create (POST /api/alert)

- **鉴权**: 需要 JWT 认证（JWT Bearer Token Token），用户需具备相应Privilege。
- **描述**: 创建一个新的 Alert 规则，用于监控 AgentInsightService 中的特定指标（如 Token 用量、成本、错误率等），并在条件满足时触发通知。
- **所属文件**: `API/Controllers/UserManagement/AlertController.cs:61`
- **所属类**: `AlertController`
- **方法**: `Create`

- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
| :--- | :--- | :--- | :--- |
| `name` | string | 是 | Alert 名称，长度限制为 1-50 个字符。 |
| `projectId` | long | 是 | 关联的 Project ID。 |
| `field` | int | 是 | 监控的指标字段。可选值：`TotalTokens` (1), `TotalCost` (2), `ErrorCount` (3), `Latency` (4), `ErrorRate` (5), `InputTokens` (6), `OutputTokens` (7), `WarningCount` (8), `ObservationCount` (9)。 |
| `operator` | int | 是 | 比较运算符。可选值：`GreaterThan` (1), `LessThan` (2), `EqualTo` (3), `GreaterThanOrEqualTo` (4), `LessThanOrEqualTo` (5), `NotEqualTo` (6)。 |
| `value` | double | 是 | 触发阈值。 |
| `timeUnit` | int | 是 | 时间单位。可选值：`Minute` (1), `Hour` (2), `Day` (3)。 |
| `timeValue` | int | 是 | 时间窗口大小，与 `timeUnit` 结合使用。 |
| `frequency` | int | 是 | 通知频率（分钟），即同一 Alert 触发后，再次通知的最小间隔时间。 |
| `notifyBy` | int | 是 | 通知方式。可选值：`System` (1), `SMS` (2)。 |
| `enabled` | bool | 否 | 是否启用该 Alert，默认为 `true`。 |

- **响应格式**:

| 字段 | 类型 | 说明 |
| :--- | :--- | :--- |
| `errorCode` | int | 业务状态码。`0` 表示成功，非 `0` 表示失败。 |
| `errorMessage` | string | 状态描述信息。 |
| `data` | object | 成功时返回创建后的 Alert 数据，失败时为 `null`。 |
| `data.id` | long | 新创建的 Alert ID。 |
| `data.name` | string | Alert 名称。 |
| `data.projectId` | long | 关联的 Project ID。 |
| `data.field` | int | 监控的指标字段。 |
| `data.operator` | int | 比较运算符。 |
| `data.value` | double | 触发阈值。 |
| `data.timeUnit` | int | 时间单位。 |
| `data.timeValue` | int | 时间窗口大小。 |
| `data.frequency` | int | 通知频率（分钟）。 |
| `data.notifyBy` | int | 通知方式。 |
| `data.enabled` | bool | 是否启用。 |
| `data.createdAt` | datetime | 创建时间。 |
| `data.updatedAt` | datetime | 更新时间。 |

- **错误码**:

| errorCode | errorMessage | 说明 |
| :--- | :--- | :--- |
| 160001 | CreateAlertFailed | 创建 Alert 失败，请稍后重试。 |
| 160004 | InvalidAlertPeriod | 无效的 Alert 时间窗口，请检查 `timeUnit` 和 `timeValue` 的组合。 |
| 160005 | InvalidAlertFrequency | 无效的 Alert 通知频率，`frequency` 必须大于 0。 |
| 160006 | InvalidAlertField | 无效的 Alert 监控字段，请检查 `field` 参数。 |
| 160007 | InvalidAlertOperator | 无效的 Alert 比较运算符，请检查 `operator` 参数。 |
| 160008 | InvalidAlertValue | 无效的 Alert 阈值，`value` 必须大于等于 0。 |
| 160010 | InvalidAlertName | 无效的 Alert 名称，名称不能为空。 |
| 160011 | InvalidAlertNotifyBy | 无效的通知方式，请检查 `notifyBy` 参数。 |
| 160014 | AlertProjectNotFound | 指定的 Project 不存在或无权访问。 |
| 160015 | AlertNameTooLong | Alert 名称过长，不能超过 50 个字符。 |
| 140008 | UnauthorizedProjectAccess | 无权访问该 Project。 |
| 100000 | UnAuthToken | 未提供有效的认证 Token。 |
| 999999 | DefaultException | 服务器内部错误。 |

- **请求示例**:

```json
{
  "name": "High Token Usage Alert",
  "projectId": 12345,
  "field": 1,
  "operator": 1,
  "value": 1000000,
  "timeUnit": 2,
  "timeValue": 1,
  "frequency": 60,
  "notifyBy": 1,
  "enabled": true
}
```

- **响应示例**:

**成功响应 (HTTP 200)**:

```json
{
  "errorCode": 0,
  "errorMessage": "Success",
  "data": {
    "id": 1,
    "name": "High Token Usage Alert",
    "projectId": 12345,
    "field": 1,
    "operator": 1,
    "value": 1000000.0,
    "timeUnit": 2,
    "timeValue": 1,
    "frequency": 60,
    "notifyBy": 1,
    "enabled": true,
    "createdAt": "2024-01-01T12:00:00Z",
    "updatedAt": "2024-01-01T12:00:00Z"
  }
}
```

**失败响应 (HTTP 200 with error errorCode)**:

```json
{
  "errorCode": 160014,
  "errorMessage": "AlertProjectNotFound",
  "data": null
}
```

### 14.4. API-075 Update (POST /api/alert/update)

- **鉴权**: 需要 JWT JWT Bearer Token Token（`[Authorize]`），用户需具备对应 Organization 或 Project 的 ADMIN 或 OWNER Privilege
- **描述**: 更新现有 Alert 的Config信息，包括监控字段、触发条件、通知方式等
- **所属文件**: `API/Controllers/UserManagement/AlertController.cs:75`
- **所属类**: `AlertController`
- **方法**: `Update`

- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | long | 是 | Alert 的唯一标识符 |
| name | string | 是 | Alert 名称，长度 1-50 字符 |
| projectId | long | 是 | 关联的 Project ID |
| field | int | 是 | 监控字段，可选值：TotalTokens(1)、TotalCost(2)、ErrorCount(3)、Latency(4)、ErrorRate(5)、InputTokens(6)、OutputTokens(7)、WarningCount(8)、ObservationCount(9) |
| operator | int | 是 | 比较运算符，可选值：GreaterThan(1)、LessThan(2)、EqualTo(3)、GreaterThanOrEqualTo(4)、LessThanOrEqualTo(5)、NotEqualTo(6) |
| value | decimal | 是 | 触发阈值 |
| timeUnit | int | 是 | 时间单位，可选值：Minute(1)、Hour(2)、Day(3) |
| timeValue | int | 是 | 时间窗口大小，与 timeUnit 配合使用 |
| notifyBy | int | 是 | 通知方式，可选值：System(1)、SMS(2) |
| enabled | bool | 否 | 是否启用，默认 true |

- **响应格式**:

| 字段 | 类型 | 说明 |
|------|------|------|
| errorCode | int | 状态码，0 表示成功，非 0 表示失败 |
| errorMessage | string | 状态消息 |
| data | object | 响应数据，成功时返回 null |

- **错误码**:

| errorCode | errorMessage | 说明 |
|-----------|---------|------|
| 160000 | AlertNotFound | Alert 不存在或已被删除 |
| 160002 | UpdateAlertFailed | 更新 Alert 失败，请稍后重试 |
| 160004 | InvalidAlertPeriod | 时间窗口参数无效，请检查 timeUnit 和 timeValue |
| 160005 | InvalidAlertFrequency | 通知频率参数无效 |
| 160006 | InvalidAlertField | 监控字段无效，请使用 AlertField 枚举中的有效值 |
| 160007 | InvalidAlertOperator | 比较运算符无效，请使用 AlertOperator 枚举中的有效值 |
| 160008 | InvalidAlertValue | 触发阈值无效，请检查数值范围 |
| 160010 | InvalidAlertName | Alert 名称无效，长度需在 1-50 字符之间 |
| 160011 | InvalidAlertNotifyBy | 通知方式无效，请使用 AlertNotifyBy 枚举中的有效值 |
| 160013 | AlertOrgNotAccessible | 当前用户无权访问该 Alert 所属的 Organization |
| 160014 | AlertProjectNotFound | 关联的 Project 不存在或已被删除 |
| 160015 | AlertNameTooLong | Alert 名称过长，最大长度为 50 字符 |
| 100000 | UnAuthToken | 未认证或 Token 已过期 |
| 999999 | DefaultException | 系统内部错误 |

- **请求示例**:

```json
{
  "id": 123,
  "name": "高错误率Alert",
  "projectId": 456,
  "field": 3,
  "operator": 1,
  "value": 10.5,
  "timeUnit": 1,
  "timeValue": 5,
  "notifyBy": 1,
  "enabled": true
}
```

- **响应示例**:

**成功响应**:
```json
{
  "errorCode": 0,
  "errorMessage": "success",
  "data": null
}
```

**失败响应**:
```json
{
  "errorCode": 160000,
  "errorMessage": "AlertNotFound",
  "data": null
}
```

### 14.5. API-090 Delete (POST /api/alert/delete)

- **鉴权**: 需要 JWT JWT Bearer Token Token（通过 `[Authorize]` 注解保护）
- **描述**: 根据提供的 alertIds 批量删除 Alert 记录。该接口属于用户管理模块，用于清理或移除不再需要的 Alert Config。
- **所属文件**: `API/Controllers/UserManagement/AlertController.cs:90`
- **所属类**: `AlertController`
- **方法**: `Delete`

- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| alertIds | string | 是 | 待删除的 Alert 标识符列表，多个 ID 使用英文逗号（`,`）分隔。例如：`1001,1002,1003` |

- **响应格式**:

| 字段 | 类型 | 说明 |
|---|---|---|
| errorCode | int | 状态码，`0` 表示成功 |
| errorMessage | string | 响应消息，成功时为 `"success"`，失败时为具体错误信息 |
| data | object | 响应数据。成功时为空对象 `{}`；失败时为 `null` |
| traceId | string | 请求Trace标识符，用于日志Trace和问题排查 |

- **错误码**:

| errorCode | errorMessage | 说明 |
|---|---|---|
| 160003 | DeleteAlertFailed | 删除 Alert 失败，可能由于数据库操作异常或并发冲突导致 |
| 160000 | AlertNotFound | 未找到指定的 Alert，请检查 alertIds 参数是否正确 |
| 160013 | AlertOrgNotAccessible | 当前用户无权访问该 Alert 所属的组织 |
| 160014 | AlertProjectNotFound | Alert 关联的 Project 不存在或已被删除 |
| 100000 | UnAuthToken | Token 无效或已过期，请重新获取有效的认证Token |
| 999999 | DefaultException | 服务器内部错误，请联系管理员处理 |

- **请求示例**:

```json
{
  "alertIds": "1001,1002,1003"
}
```

- **响应示例**:

**成功响应:**

```json
{
  "errorCode": 0,
  "errorMessage": "success",
  "data": {},
  "traceId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

**失败响应 (AlertNotFound):**

```json
{
  "errorCode": 160000,
  "errorMessage": "AlertNotFound",
  "data": null,
  "traceId": "b2c3d4e5-f6a7-8901-bcde-f12345678901"
}
```

### 14.6. API-108 ReadRecords (POST /api/alert/record/read)

- **鉴权**: 需要 JWT 认证（`[Authorize]` 注解）
- **描述**: 根据记录 ID 列表批量读取 Alert 记录，将 Alert 记录状态更新为已读（`AlertRecordState.Read`）。
- **所属文件**: `API/Controllers/UserManagement/AlertController.cs:108`
- **所属类**: `AlertController`
- **方法**: `ReadRecords`

- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| recordIds | string | 是 | Alert 记录 ID 列表，多个 ID 以逗号分隔。 |

- **响应格式**:

| 字段 | 类型 | 说明 |
|---|---|---|
| errorCode | int | 业务状态码，`0` 表示成功，非 `0` 表示失败。 |
| errorMessage | string | 状态描述信息。 |
| data | object | 响应数据。 |
| data.updatedCount | int | 成功更新为已读状态的记录数量。 |

- **错误码**:

| errorCode | errorMessage | 说明 |
|---|---|---|
| 100000 | UnAuthToken | Token 未认证或已失效。 |
| 160000 | AlertNotFound | 未找到对应的 Alert 记录。 |
| 999999 | DefaultException | 服务器内部异常。 |

- **请求示例**:

```json
{
  "recordIds": "1001,1002,1003"
}
```

- **响应示例**:

成功响应示例：

```json
{
  "errorCode": 0,
  "errorMessage": "Success",
  "data": {
    "updatedCount": 3
  }
}
```

失败响应示例（未找到 Alert 记录）：

```json
{
  "errorCode": 160000,
  "errorMessage": "AlertNotFound",
  "data": null
}
```

### 14.7. API-128 GetRecords (GET /api/alert/record)

- **鉴权**: 需要 JWT JWT Bearer Token Token（从 `AlertController` 类级别的 `[Authorize]` 注解推断）
- **描述**: 根据组织、Project、Alert ID 和记录状态筛选获取 Alert 记录列表。
- **所属文件**: `API/Controllers/UserManagement/AlertController.cs:128`
- **所属类**: `AlertController`
- **方法**: `GetRecords`

- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| orgId | string | 否 | Org ID，用于按组织筛选 Alert 记录 |
| projectId | string | 否 | Project ID，用于按项目筛选 Alert 记录 |
| alertId | string | 否 | Alert Config ID，用于按具体 Alert 筛选记录 |
| state | int | 否 | Alert 记录状态，默认值为 `Active` (1)。可选值：`Active` (1)、`Read` (2) |

- **响应格式**:

| 字段 | 类型 | 说明 |
|------|------|------|
| errorCode | int | 状态码，0 表示成功 |
| type | string | 响应类型标识，固定为 `"Success"` 或 `"Error"` |
| errorMessage | string | 响应消息描述 |
| data | object | 响应数据，包含 Alert 记录列表 |
| data.items | array | Alert 记录项数组 |
| data.items.id | string | Alert 记录唯一标识 |
| data.items.alertId | string | 关联的 Alert Config ID |
| data.items.projectId | string | 所属项目 ID |
| data.items.orgId | string | 所属组织 ID |
| data.items.state | int | 记录状态：`Active` (1)、`Read` (2) |
| data.items.errorMessage | string | Alert 触发消息内容 |
| data.items.createdAt | datetime | 记录创建时间 |
| data.items.readAt | datetime | 记录读取时间，未读时为 null |
| data.total | int | 符合条件的记录总数 |
| data.page | int | 当前页码 |
| data.pageSize | int | 每页记录数 |

- **错误码**:

| errorCode | errorMessage | 说明 |
|-----------|---------|------|
| 100000 | UnAuthToken | Token 无效或未提供，需要重新登录获取有效 Token |
| 160000 | AlertNotFound | 指定的 Alert 记录不存在或已被删除 |
| 160013 | AlertOrgNotAccessible | 当前用户无权访问该组织下的 Alert 记录 |
| 160014 | AlertProjectNotFound | 指定的项目不存在或无权访问该项目下的 Alert 记录 |
| 999999 | DefaultException | 服务器内部错误，请稍后重试 |

- **请求示例**:

```json
{
  "orgId": "org_8f3a2b9c1d",
  "projectId": "proj_5e7a2c8d4f",
  "alertId": "alert_3b6d9e1a2c",
  "state": 1
}
```

- **响应示例**:

**成功响应** (HTTP 200):
```json
{
  "errorCode": 0,
  "type": "Success",
  "errorMessage": "获取Alert记录成功",
  "data": {
    "items": [
      {
        "id": "rec_1a2b3c4d5e",
        "alertId": "alert_3b6d9e1a2c",
        "projectId": "proj_5e7a2c8d4f",
        "orgId": "org_8f3a2b9c1d",
        "state": 1,
        "errorMessage": "Token 消耗量超过阈值 100000",
        "createdAt": "2025-01-15T10:30:00Z",
        "readAt": null
      },
      {
        "id": "rec_6f7g8h9i0j",
        "alertId": "alert_3b6d9e1a2c",
        "projectId": "proj_5e7a2c8d4f",
        "orgId": "org_8f3a2b9c1d",
        "state": 2,
        "errorMessage": "错误率超过阈值 5%",
        "createdAt": "2025-01-14T08:15:00Z",
        "readAt": "2025-01-14T09:00:00Z"
      }
    ],
    "total": 2,
    "page": 1,
    "pageSize": 20
  }
}
```

**失败响应** (未授权):
```json
{
  "errorCode": 100000,
  "type": "Error",
  "errorMessage": "UnAuthToken",
  "data": null
}
```

**失败响应** (Alert 记录不存在):
```json
{
  "errorCode": 160000,
  "type": "Error",
  "errorMessage": "AlertNotFound",
  "data": null
}
```

---

## 15. BulletinController 接口

本章共覆盖 7 个 HTTP 端点，每个端点一个接口卡片。

### 15.1. API-001 创建Bulletin (POST /api/tools/bulletin)

- **鉴权**: 无（代码中未标注 `[Authorize]` 注解）
- **描述**: 创建一条新的Bulletin（Bulletin），用于向用户发布新闻、活动、通知等信息。

#### 15.1.1. 请求参数

**请求体** (`CreateBulletinBody`，`[FromBody]` 绑定)

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `title` | string | 是 | Bulletin标题 |
| `content` | string | 是 | Bulletin正文内容 |
| `type` | BulletinType | 是 | Bulletin类型，取值见下方枚举说明 |
| `status` | BulletinStatus | 是 | Bulletin状态，取值见下方枚举说明 |
| `startTime` | DateTime? | 否 | Bulletin生效开始时间；为空表示立即生效 |
| `endTime` | DateTime? | 否 | Bulletin生效结束时间；为空表示长期有效 |

**BulletinType 枚举值**

| 值 | 数值 | 说明 |
|----|------|------|
| `News` | 1 | 新闻 |
| `Activity` | 2 | 活动 |
| `Information` | 3 | 资讯 |
| `Annoucement` | 4 | 通知 |
| `Advertisement` | 5 | 广告 |
| `Agreement` | 9 | 协议 |

**BulletinStatus 枚举值**

| 值 | 数值 | 说明 |
|----|------|------|
| `Draft` | 1 | 草稿 |
| `Reviewing` | 2 | 审核中 |
| `Revision` | 3 | 退回修改 |
| `Published` | 4 | 已发布 |
| `Expired` | 5 | 已过期 |
| `Closed` | 6 | 已关闭 |

#### 15.1.2. 响应格式

**成功响应** (`ApiResponse<long>`)

| 字段 | 类型 | 说明 |
|------|------|------|
| `errorCode` | int | 状态码，`0` 表示成功 |
| `errorMessage` | string | 提示信息 |
| `data` | long | 新建Bulletin的 ID |

**失败响应** (`ApiResponse<long>`)

| 字段 | 类型 | 说明 |
|------|------|------|
| `errorCode` | int | 错误码，非 `0` 表示失败 |
| `errorMessage` | string | 错误描述 |
| `data` | long? | 通常为 `null` |

#### 15.1.3. 错误码

| errorCode | errorMessage | 说明 |
|-----------|---------|------|
| `DefaultException` | `999999` | 服务器内部错误，创建Bulletin失败 |
| `UnAuthToken` | `100000` | 未认证或 Token 无效（若后续接口增加鉴权时使用） |

#### 15.1.4. 请求示例

```json
{
  "title": "系统升级通知",
  "content": "系统将于本周六 22:00 进行升级维护，预计持续 2 小时。",
  "type": 4,
  "status": 1,
  "startTime": "2025-01-01T00:00:00Z",
  "endTime": "2025-01-31T23:59:59Z"
}
```

#### 15.1.5. 响应示例

**成功响应**

```json
{
  "errorCode": 0,
  "errorMessage": "success",
  "data": 1001
}
```

**失败响应**

```json
{
  "errorCode": 999999,
  "errorMessage": "创建Bulletin失败",
  "data": null
}
```

### 15.2. API-045 获取Bulletin协议内容 (GET /api/tools/bulletin/agreement)

- **鉴权**: 无
- **描述**: 根据Bulletin别名获取协议类型的Bulletin内容，用于展示用户协议、服务条款等法律文本。

- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| alias | string | 是 | Bulletin别名，用于唯一标识协议内容，例如 `user-agreement`、`privacy-policy` |

- **响应格式**:

| 字段 | 类型 | 说明 |
|------|------|------|
| errorCode | int | 状态码，`0` 表示成功，非 `0` 表示失败 |
| errorMessage | string | 提示信息，成功时为 `"ok"`，失败时为错误描述 |
| data | object | Bulletin数据对象 |
| data.id | string | Bulletin唯一标识 |
| data.title | string | Bulletin标题 |
| data.content | string | Bulletin正文内容，支持 HTML 格式 |
| data.type | int | Bulletin类型，固定为 `9`（Agreement） |
| data.status | int | Bulletin状态，固定为 `4`（Published） |
| data.alias | string | Bulletin别名 |
| data.createdAt | string | 创建时间，ISO 8601 格式 |
| data.updatedAt | string | 更新时间，ISO 8601 格式 |
| data.publishedAt | string | 发布时间，ISO 8601 格式 |

- **错误码**:

| errorCode | errorMessage | 说明 |
|-----------|---------|------|
| 999999 | DefaultException | 服务器内部错误，请稍后重试 |
| 100000 | UnAuthToken | 未认证的 Token，请检查请求头中的 Authorization 字段 |

- **请求示例**:

```json
GET /api/tools/bulletin/agreement?alias=user-agreement
```

- **响应示例**:

**成功响应**:

```json
{
  "errorCode": 0,
  "errorMessage": "ok",
  "data": {
    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "title": "AgentInsightService 用户服务协议",
    "content": "<h1>用户服务协议</h1><p>欢迎使用 AgentInsightService...</p>",
    "type": 9,
    "status": 4,
    "alias": "user-agreement",
    "createdAt": "2025-01-15T08:30:00Z",
    "updatedAt": "2025-02-01T10:00:00Z",
    "publishedAt": "2025-01-20T00:00:00Z"
  }
}
```

**失败响应**:

```json
{
  "errorCode": 999999,
  "errorMessage": "服务器内部错误，请稍后重试",
  "data": null
}
```

### 15.3. API-001 GetBulletins (GET /api/tools/bulletin/bulletins)

- **鉴权**: 无
- **描述**: 分页查询Bulletin列表，支持按Bulletin类型和轮播状态筛选。

- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| type | BulletinType? | 否 | Bulletin类型，枚举值：News = 1, Activity = 2, Information = 3, Annoucement = 4, Advertisement = 5, Agreement = 9 |
| isCarousel | bool | 否 | 是否为轮播Bulletin，默认 false |
| page | int | 否 | 页码，默认 AgentInsightConst.DefaultPage |
| pageSize | int | 否 | 每页条数，默认 AgentInsightConst.DefaultPageSize |

- **响应格式**:

| 字段 | 类型 | 说明 |
|---|---|---|
| errorCode | int | 状态码，0 表示成功 |
| errorMessage | string | 提示信息 |
| data | object | 返回数据 |
| data.items | array | Bulletin列表 |
| data.items.id | string | Bulletin ID |
| data.items.title | string | Bulletin标题 |
| data.items.content | string | Bulletin内容 |
| data.items.type | BulletinType | Bulletin类型 |
| data.items.status | BulletinStatus | Bulletin状态，枚举值：Draft = 1, Reviewing = 2, Revision = 3, Published = 4, Expired = 5, Closed = 6 |
| data.items.isCarousel | bool | 是否为轮播Bulletin |
| data.items.createdAt | datetime | 创建时间 |
| data.items.updatedAt | datetime | 更新时间 |
| data.total | int | 总记录数 |
| data.page | int | 当前页码 |
| data.pageSize | int | 每页条数 |

- **错误码**:

| errorCode | errorMessage | 说明 |
|---|---|---|
| 0 | 成功 | 请求成功 |
| 999999 | DefaultException | 服务器内部异常 |

- **请求示例**:

```json
GET /api/tools/bulletin/bulletins?type=1&isCarousel=false&page=1&pageSize=10
```

- **响应示例**:

**成功响应**:

```json
{
  "errorCode": 0,
  "errorMessage": "success",
  "data": {
    "items": [
      {
        "id": "b1f2a3c4-d5e6-4f7a-8b9c-0d1e2f3a4b5c",
        "title": "系统升级通知",
        "content": "系统将于本周六进行升级维护。",
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

**失败响应**:

```json
{
  "errorCode": 999999,
  "errorMessage": "服务器内部异常",
  "data": null
}
```

### 15.4. API-082 GetBackendBulletins (GET /api/tools/bulletin/backend)

- **鉴权**: 无
- **描述**: 获取后台Bulletin列表，支持按类型和状态筛选，并支持分页查询。

- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| type | BulletinType? | 否 | Bulletin类型，可空枚举。可选值：`News`(1), `Activity`(2), `Information`(3), `Annoucement`(4), `Advertisement`(5), `Agreement`(9) |
| status | BulletinStatus? | 否 | Bulletin状态，可空枚举。可选值：`Draft`(1), `Reviewing`(2), `Revision`(3), `Published`(4), `Expired`(5), `Closed`(6) |
| page | int | 否 | 页码，默认值为 `AgentInsightConst.DefaultPage` |
| pageSize | int | 否 | 每页条数，默认值为 `AgentInsightConst.DefaultPageSize` |

- **响应格式**:

| 字段 | 类型 | 说明 |
|---|---|---|
| errorCode | int | 状态码，`0` 表示成功，非 `0` 表示失败 |
| errorMessage | string | 提示信息 |
| data | object | 返回数据，包含分页信息和Bulletin列表 |
| data.items | array | Bulletin列表，元素为Bulletin对象 |
| data.items.id | string | Bulletin ID |
| data.items.title | string | Bulletin标题 |
| data.items.content | string | Bulletin内容 |
| data.items.type | BulletinType | Bulletin类型 |
| data.items.status | BulletinStatus | Bulletin状态 |
| data.items.createdAt | datetime | 创建时间 |
| data.items.updatedAt | datetime | 更新时间 |
| data.page | int | 当前页码 |
| data.pageSize | int | 每页条数 |
| data.total | long | 总记录数 |

- **错误码**:

| errorCode | errorMessage | 说明 |
|---|---|---|
| 0 | 成功 | 请求成功 |
| 999999 | DefaultException | 服务器内部异常，请稍后重试 |
| 100000 | UnAuthToken | 未认证的 Token，请先登录 |

- **请求示例**:

```json
GET /api/tools/bulletin/backend?type=News&status=Published&page=1&pageSize=20
```

- **响应示例**:

**成功响应**:

```json
{
  "errorCode": 0,
  "errorMessage": "成功",
  "data": {
    "items": [
      {
        "id": "b1f2c3d4-...",
        "title": "系统升级Bulletin",
        "content": "系统将于本周六进行升级维护...",
        "type": 1,
        "status": 4,
        "createdAt": "2025-01-15T10:00:00Z",
        "updatedAt": "2025-01-15T10:00:00Z"
      }
    ],
    "page": 1,
    "pageSize": 20,
    "total": 1
  }
}
```

**失败响应**:

```json
{
  "errorCode": 999999,
  "errorMessage": "服务器内部异常，请稍后重试",
  "data": null
}
```

### 15.5. API-096 ApproveBulletin (POST /api/tools/bulletin/approve)

- **鉴权**: 无
- **描述**: 根据Bulletin ID 列表批量审核通过Bulletin，将Bulletin状态从 Reviewing 更新为 Published。
- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| ids | string | 是 | 待审核通过的Bulletin ID 列表，多个 ID 以逗号分隔。 |

- **响应格式**:

| 字段 | 类型 | 说明 |
|---|---|---|
| errorCode | int | 业务状态码，`0` 表示成功，非 `0` 表示失败。 |
| errorMessage | string | 状态描述信息。 |
| data | object | 响应数据，成功时通常为 `null`。 |
| traceId | string | 请求Trace ID，用于日志排查。 |

- **错误码**:

| errorCode | errorMessage | 说明 |
|---|---|---|
| 0 | Success | 审核通过成功。 |
| 999999 | DefaultException | 服务器内部异常。 |
| 100000 | UnAuthToken | 未认证的 Token。 |

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
  "errorCode": 0,
  "errorMessage": "Success",
  "data": null,
  "traceId": "a1b2c3d4-5678-90ab-cdef-1234567890ab"
}
```

**失败响应**:
```json
{
  "errorCode": 999999,
  "errorMessage": "DefaultException",
  "data": null,
  "traceId": "a1b2c3d4-5678-90ab-cdef-1234567890ab"
}
```

### 15.6. API-110 ReviseBulletin (POST /api/tools/bulletin/revision)

- **鉴权**: 无
- **描述**: 根据指定的Bulletin ID 列表，将Bulletin状态修改为 Revision（需修改）。

- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| ids | string | 是 | 待修改状态的Bulletin ID 列表，多个 ID 使用英文逗号分隔。 |

- **响应格式**:

| 字段 | 类型 | 说明 |
|---|---|---|
| errorCode | int | 业务状态码，`0` 表示成功，非 `0` 表示失败。 |
| errorMessage | string | 状态码对应的描述信息。 |
| data | object | 返回的数据主体，成功时为 `null`。 |
| traceId | string | 当前请求的 Trace ID，用于链路Trace。 |

- **错误码**:

| errorCode | errorMessage | 说明 |
|---|---|---|
| 0 | Success | 请求成功。 |
| 100000 | UnAuthToken | Token 无效或未授权。 |
| 999999 | DefaultException | 服务器内部异常。 |

- **请求示例**:

```json
{
  "ids": "1,2,3"
}
```

- **响应示例**:

成功响应：

```json
{
  "errorCode": 0,
  "errorMessage": "Success",
  "data": null,
  "traceId": "a1b2c3d4e5f6a7b8c9d0e1f2"
}
```

失败响应：

```json
{
  "errorCode": 100000,
  "errorMessage": "UnAuthToken",
  "data": null,
  "traceId": "a1b2c3d4e5f6a7b8c9d0e1f2"
}
```

### 15.7. API-124 CloseBulletin (POST /api/tools/bulletin/close)

- **鉴权**: 需要 JWT JWT Bearer Token Token (通过 `[Authorize]` 注解保护，使用 `JWTSettings` Config的 HS256 算法验证)
- **描述**: 关闭指定 ID 的Bulletin。根据 `BulletinStatus` 枚举，将Bulletin状态从 `Published` (4) 或 `Expired` (5) 更新为 `Closed` (6)。

- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| ids | string | 是 | 待关闭Bulletin的 ID 列表，多个 ID 使用逗号分隔。例如：`"1,2,3"` |

- **响应格式**:

| 字段 | 类型 | 说明 |
|------|------|------|
| errorCode | int | 业务状态码，`0` 表示成功，非 `0` 表示失败（见错误码表） |
| errorMessage | string | 状态描述信息，成功时为 `"success"`，失败时为具体错误信息 |
| data | object | 响应数据，成功时通常为 `null` 或空对象 |

- **错误码**:

| errorCode | errorMessage | 说明 |
|-----------|---------|------|
| 0 | success | Bulletin关闭成功 |
| 100000 | UnAuthToken | Token 无效或已过期，需要重新获取有效的 JWT Token |
| 999999 | DefaultException | 服务器内部错误，请联系管理员处理 |

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
  "errorCode": 0,
  "errorMessage": "success",
  "data": null
}
```

**失败响应** (Token 无效):
```json
{
  "errorCode": 100000,
  "errorMessage": "UnAuthToken",
  "data": null
}
```

---

## 16. CaptchaController 接口

本章覆盖 2 个 HTTP 端点，对应 `API/Controllers/UserManagement/CaptchaController.cs` 中的两个方法。

### 16.1. API-029 获取Captcha (GET /api/captcha)

- **鉴权**: 无
- **描述**: 根据手机号获取Captcha，用于用户登录或注册时的身份验证。
- **对应实现**: `CaptchaController.Get` (API/Controllers/UserManagement/CaptchaController.cs:29)

- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| mobile | string | 是 | 用户手机号，用于接收Captcha短信 |

- **响应格式**:

| 字段 | 类型 | 说明 |
|---|---|---|
| errorCode | int | 业务状态码，`0` 表示成功，非 `0` 表示失败 |
| errorMessage | string | 状态描述信息 |
| data | object | 响应数据，成功时返回 `null` |

- **错误码**:

| errorCode | errorMessage | 说明 |
|---|---|---|
| 110000 | SendSMSTooOften | 短信发送过于频繁，请稍后再试 |
| 110001 | FailedToSendSMS | 短信发送失败，请检查手机号是否正确或稍后重试 |
| 100009 | EmptyMobile | 手机号为空，请填写手机号 |
| 999999 | DefaultException | 系统繁忙，请稍后重试 |

- **请求示例**:

```json
GET /api/captcha?mobile=13800138000
```

- **响应示例**:

**成功响应**:

```json
{
  "errorCode": 0,
  "errorMessage": "Captcha发送成功",
  "data": null
}
```

**失败响应**:

```json
{
  "errorCode": 110000,
  "errorMessage": "短信发送过于频繁，请稍后再试",
  "data": null
}
```

### 16.2. API-043 获取短信Captcha (GET /api/captcha/sms)

- **鉴权**: 无
- **描述**: 获取短信Captcha。根据提供的手机号 `phone` 发送短信Captcha，Captcha长度为 6 位，有效期 300 秒，发送间隔 60 秒。
- **对应实现**: `CaptchaController.GetSMSCaptcha` (API/Controllers/UserManagement/CaptchaController.cs:43)

- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| phone | string | 是 | 接收Captcha的目标手机号码 |

- **响应格式**:

| 字段 | 类型 | 说明 |
|---|---|---|
| errorCode | int | 业务状态码。`0` 表示成功，非 `0` 表示失败 |
| errorMessage | string | 状态描述信息 |
| data | object | 响应数据。成功时通常为 `null` |

- **错误码**:

| errorCode | errorMessage | 说明 |
|---|---|---|
| 0 | 成功 | Captcha发送成功 |
| 110000 | SendSMSTooOften | 短信发送过于频繁，请稍后再试 |
| 110001 | FailedToSendSMS | 短信发送失败，请检查手机号或稍后重试 |
| 100009 | EmptyMobile | 手机号为空，请输入有效的手机号码 |
| 100000 | UnAuthToken | 用户身份验证失败或 Token 无效 |
| 999999 | DefaultException | 服务器内部错误，请稍后重试 |

- **请求示例**:

```json
GET /api/captcha/sms?phone=13800138000
```

- **响应示例**:

**成功响应**:

```json
{
  "errorCode": 0,
  "errorMessage": "Captcha发送成功",
  "data": null
}
```

**失败响应**:

```json
{
  "errorCode": 110000,
  "errorMessage": "短信发送过于频繁，请稍后再试",
  "data": null
}
```

---

## 17. HealthController 接口

本章共覆盖 1 个 HTTP 端点，每个端点一个接口卡片。

### 17.1. API-001 健康检查 (GET /api/tools/health)

- **鉴权**: 无
- **描述**: 检查 AgentInsightService 服务健康状态，确认服务是否正常运行。
- **请求参数**: 无
- **响应格式**:

| 字段 | 类型 | 说明 |
|---|---|---|
| errorCode | int | 状态码，200 表示成功 |
| errorMessage | string | 提示信息 |
| data | object | 健康检查结果数据 |
| data.status | string | 服务状态，例如 "Healthy" |

- **错误码**:

| errorCode | errorMessage | 说明 |
|---|---|---|
| 999999 | DefaultException | 服务器内部异常，无法完成健康检查 |

- **请求示例**:

```http
GET /api/tools/health
```

- **响应示例**:

**成功响应 (HTTP 200)**，此时 `errorCode` 为 200，`errorMessage` 为 "success"：

```json
{
  "errorCode": 200,
  "errorMessage": "success",
  "data": {
    "status": "Healthy"
  }
}
```

**失败响应 (HTTP 500)**，此时 `errorCode` 对应错误码表中的 `errorCode`，`errorMessage` 对应错误码表中的 `errorMessage`：

```json
{
  "errorCode": 999999,
  "errorMessage": "DefaultException",
  "data": null
}
```

> 说明：`data.status` 字段用于标识服务当前健康状态，常见取值包括 `Healthy`（健康）、`Degraded`（性能下降）和 `Unhealthy`（不健康），具体取值以服务实际实现为准。

---

## 18. MetricsController 接口

本章共覆盖 4 个 HTTP 端点，每个端点一个接口卡片。

### 18.1. API-034 GetObservations (GET /api/data/metrics/observations)

- **鉴权**: 无（代码中未标注 `[Authorize]` 特性）
- **描述**: 分页查询 Observation 列表，支持按 Trace 标识筛选。该接口用于从 AgentInsightService 的 Metrics 数据中检索 Agent 运行过程中产生的 Observation 记录，便于进行 Trace 级别的数据Observation与分析。
- **源文件**: API/Controllers/DataManagement/MetricsController.cs:34

- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | string | 是 | Trace 标识符，用于筛选指定 Trace 下的所有 Observation 记录 |
| page | int | 否 | 页码，默认值为 1 |
| pagesize | int | 否 | 每页条数，默认值为 20 |

- **响应格式**:

| 字段 | 类型 | 说明 |
|------|------|------|
| errorCode | int | 业务状态码，`0` 表示成功，非 `0` 表示失败 |
| errorMessage | string | 提示信息，成功时为 `"success"`，失败时为具体错误描述 |
| data | object | 分页数据结果 |
| data.items | array | Observation 记录列表，元素为 Observation 对象 |
| data.items[].id | string | Observation 唯一标识 |
| data.items[].traceId | string | 所属 Trace 标识 |
| data.items[].sessionId | string | 所属 Session 标识 |
| data.items[].timestamp | datetime | Observation 产生时间 |
| data.items[].level | string | 日志级别（如 `DEBUG`、`INFO`、`WARNING`、`ERROR`） |
| data.items[].errorMessage | string | Observation 内容 |
| data.items[].metadata | object | 附加元数据（如模型名称、Token 用量等） |
| data.total | int | 符合条件的总记录数 |
| data.page | int | 当前页码 |
| data.pagesize | int | 每页条数 |

- **错误码**:

| errorCode | errorMessage | 说明 |
|-----------|---------|------|
| 100000 | UnAuthToken | Token 未认证或已过期 |
| 150009 | EmptyTraceIds | `id` 参数为空，未提供 Trace 标识 |
| 150010 | ClickHouseQueryError | ClickHouse 查询执行失败，无法获取 Observation 数据 |
| 150017 | ClickHouseQueryTimeout | ClickHouse 查询超时，请稍后重试 |
| 150018 | EmptyTraceId | Trace 标识为空，无法执行查询 |
| 999999 | DefaultException | 服务器内部异常 |

- **请求示例**:

```json
{
  "id": "trace_8f3c2a1b9e4d7f6a",
  "page": 1,
  "pagesize": 20
}
```

- **响应示例**:

**成功响应**:
```json
{
  "errorCode": 0,
  "errorMessage": "success",
  "data": {
    "items": [
      {
        "id": "obs_001",
        "traceId": "trace_8f3c2a1b9e4d7f6a",
        "sessionId": "session_abc123",
        "timestamp": "2025-01-15T10:30:00Z",
        "level": "INFO",
        "errorMessage": "Agent started processing request",
        "metadata": {
          "model": "gpt-4o",
          "inputTokens": 1250,
          "outputTokens": 320
        }
      },
      {
        "id": "obs_002",
        "traceId": "trace_8f3c2a1b9e4d7f6a",
        "sessionId": "session_abc123",
        "timestamp": "2025-01-15T10:30:05Z",
        "level": "WARNING",
        "errorMessage": "Token usage approaching limit",
        "metadata": {
          "model": "gpt-4o",
          "totalTokens": 14800
        }
      }
    ],
    "total": 2,
    "page": 1,
    "pagesize": 20
  }
}
```

**失败响应**:
```json
{
  "errorCode": 150009,
  "errorMessage": "EmptyTraceIds",
  "data": null
}
```

### 18.2. API-050 GetScores (GET /api/data/metrics/scores)

- **鉴权**: 需要 JWT 认证（JWT Bearer Token Token），未认证返回 `UnAuthToken` 错误
- **描述**: 根据 Trace ID 分页查询 Score 数据列表，支持按页获取Score记录
- **源文件**: API/Controllers/DataManagement/MetricsController.cs:50

- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | string | 是 | Trace ID，用于定位对应的 Trace 记录 |
| page | int | 否 | 页码，默认值为 1 |
| pagesize | int | 否 | 每页条数，默认值为 20 |

- **响应格式**:

| 字段 | 类型 | 说明 |
|------|------|------|
| errorCode | int | 状态码，`0` 表示成功，非 `0` 表示失败 |
| errorMessage | string | 提示信息，成功时为 `"success"`，失败时为具体错误描述 |
| data | object | 响应数据，包含分页结果 |
| data.items | array | Score 数据列表，每个元素包含 Score 的详细信息（如 Id、Name、Value、Timestamp 等） |
| data.total | int | 符合条件的总记录数 |
| data.page | int | 当前页码 |
| data.pagesize | int | 当前每页条数 |

- **错误码**:

| errorCode | errorMessage | 说明 |
|-----------|---------|------|
| 100000 | UnAuthToken | Token 无效或未提供，认证失败 |
| 150000 | EmptyProjectId | Project ID 为空 |
| 150009 | EmptyTraceIds | Trace ID 列表为空 |
| 150010 | ClickHouseQueryError | ClickHouse 查询执行失败 |
| 150011 | TooManyTraceIds | Trace ID 数量超出限制 |
| 150012 | InvalidFilterType | 无效的过滤类型 |
| 150013 | InvalidFilterColumn | 无效的过滤列 |
| 150014 | InvalidFilterOperator | 无效的过滤操作符 |
| 150015 | InvalidFilterValue | 无效的过滤值 |
| 150016 | InvalidOrderBy | 无效的排序字段 |
| 150017 | ClickHouseQueryTimeout | ClickHouse 查询超时 |
| 150018 | EmptyTraceId | Trace ID 为空 |
| 999999 | DefaultException | 服务器内部异常 |

- **请求示例**:

```json
GET /api/data/metrics/scores?id=trace_8f3a2b1c9d4e5f6a7b8c9d0e&page=1&pagesize=20
```

- **响应示例**:

**成功响应**:
```json
{
  "errorCode": 0,
  "errorMessage": "success",
  "data": {
    "items": [
      {
        "id": "score_001",
        "name": "accuracy",
        "value": 0.95,
        "timestamp": "2025-01-15T10:30:00Z"
      },
      {
        "id": "score_002",
        "name": "relevance",
        "value": 0.88,
        "timestamp": "2025-01-15T10:30:05Z"
      }
    ],
    "total": 2,
    "page": 1,
    "pagesize": 20
  }
}
```

**失败响应**:
```json
{
  "errorCode": 150018,
  "errorMessage": "EmptyTraceId",
  "data": null
}
```

### 18.3. API-064 GetTraces (GET /api/data/metrics/traces)

- **鉴权**: 无（代码中未标注 `[Authorize]` 特性）
- **描述**: 根据 Trace ID 列表查询 Trace 详情数据，返回匹配的 Trace 记录及其关联的 Span、Observation、Score 等可Observation性数据。
- **源文件**: API/Controllers/DataManagement/MetricsController.cs:64

- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| ids | string | 是 | Trace ID 列表，多个 ID 以逗号分隔。对应 `EmptyTraceIds`（150009）与 `TooManyTraceIds`（150011）的校验场景。 |

- **响应格式**:

| 字段 | 类型 | 说明 |
|------|------|------|
| traceId | string | Trace 唯一标识符 |
| timestamp | datetime | Trace 开始时间戳 |
| name | string | Trace 名称 |
| userId | string | 关联的用户 ID |
| sessionId | string | 关联的 Session ID |
| environment | string | 环境标识（如 `DEVELOPMENT`、`STAGING`、`PRODUCTION`） |
| version | string | 版本号 |
| release | string | 发布标识 |
| tags | array | 标签列表 |
| bookmarked | boolean | 是否被标记 |
| latency | number | 延迟（毫秒） |
| inputTokens | number | 输入 Token 数量 |
| outputTokens | number | 输出 Token 数量 |
| totalTokens | number | 总 Token 数量 |
| inputCost | number | 输入成本 |
| outputCost | number | 输出成本 |
| totalCost | number | 总成本 |
| level | string | 日志级别 |
| warningCount | number | 警告数量 |
| errorCount | number | 错误数量 |
| defaultCount | number | 默认计数 |
| debugCount | number | 调试计数 |
| modelNames | array | 使用的模型名称列表 |
| scoresAvg | number | 平均 Score |
| spans | array | Span 列表，包含 Span 详情数据 |
| observations | array | Observation 列表，包含 Observation 详情数据 |
| scores | array | Score 列表，包含 Score 详情数据 |

- **错误码**:

| errorCode | errorMessage | 说明 |
|-----------|---------|------|
| 150009 | EmptyTraceIds | Trace ID 列表为空时返回 |
| 150010 | ClickHouseQueryError | ClickHouse 查询执行失败时返回 |
| 150011 | TooManyTraceIds | Trace ID 数量超过限制时返回 |
| 150017 | ClickHouseQueryTimeout | ClickHouse 查询超时时返回 |
| 150018 | EmptyTraceId | 单个 Trace ID 为空时返回 |
| 999999 | DefaultException | 未预期的系统异常时返回 |

- **请求示例**:

```json
GET /api/data/metrics/traces?ids=trace-001,trace-002,trace-003
```

- **响应示例**:

**成功响应**:

```json
{
  "traceId": "trace-001",
  "timestamp": "2025-01-15T10:30:00Z",
  "name": "AgentInsight-Trace-001",
  "userId": "user-123",
  "sessionId": "session-456",
  "environment": "PRODUCTION",
  "version": "1.2.0",
  "release": "release-2025.01",
  "tags": ["production", "agent"],
  "bookmarked": true,
  "latency": 1250.5,
  "inputTokens": 1500,
  "outputTokens": 800,
  "totalTokens": 2300,
  "inputCost": 0.015,
  "outputCost": 0.008,
  "totalCost": 0.023,
  "level": "INFO",
  "warningCount": 2,
  "errorCount": 0,
  "defaultCount": 5,
  "debugCount": 3,
  "modelNames": ["gpt-4o", "claude-3.5"],
  "scoresAvg": 0.92,
  "spans": [
    {
      "spanId": "span-001",
      "name": "Agent-Execution",
      "timestamp": "2025-01-15T10:30:00Z",
      "duration": 850.2
    }
  ],
  "observations": [
    {
      "observationId": "obs-001",
      "type": "LLM",
      "input": "用户查询内容",
      "output": "Agent 响应内容"
    }
  ],
  "scores": [
    {
      "scoreId": "score-001",
      "name": "relevance",
      "value": 0.95
    }
  ]
}
```

**失败响应**:

```json
{
  "errorCode": 150009,
  "errorMessage": "EmptyTraceIds",
  "description": "Trace ID 列表为空，请提供至少一个有效的 Trace ID"
}
```

### 18.4. API-024 GetTraces (POST /api/data/metrics/traces)

- **鉴权**: 无 `[Authorize]` 注解，无需鉴权
- **描述**: 根据 TraceMetricsBody 中的过滤条件、排序规则和分页参数，从 ClickHouse 查询 Trace 列表数据。
- **源文件**: API/Controllers/DataManagement/MetricsController.cs:125

- **请求参数**: 请求体为 `TraceMetricsBody` 对象

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| projectId | string | 是 | Project ID，用于限定查询范围 |
| organizationId | string | 否 | Org ID，用于限定查询范围（与 projectId 二选一） |
| traceIds | string[] | 否 | Trace ID 列表，用于精确查询指定 Trace |
| filter | object | 否 | 过滤条件组，包含以下子字段 |
| filter.column | enum (FilterColumn) | 是 | 过滤列，可选值：Id=1, Name=2, Timestamp=3, UserId=4, SessionId=5, Environment=6, Version=7, Release=8, Tags=9, Bookmarked=10, Latency=11, InputTokens=12, OutputTokens=13, TotalTokens=14, Tokens=15, InputCost=16, OutputCost=17, TotalCost=18, Level=19, WarningCount=20, ErrorCount=21, DefaultCount=22, DebugCount=23, ModelNames=24, ScoresAvg=25 |
| filter.operator | enum (FilterOperator) | 是 | 过滤操作符，可选值：GreaterThan=1, LessThan=2, GreaterThanOrEqualTo=3, LessThanOrEqualTo=4, EqualTo=5, Contains=6, DoesNotContain=7, StartsWith=8, EndsWith=9, AnyOf=10, NoneOf=11, AllOf=12, NotEqualTo=13, IsNull=14, IsNotNull=15 |
| filter.value | object | 是 | 过滤值，类型根据 column 和 operator 决定 |
| orderBy | object | 否 | 排序规则组，包含以下子字段 |
| orderBy.column | enum (FilterColumn) | 是 | 排序列，可选值同上 |
| orderBy.descending | boolean | 是 | 是否降序排列 |
| page | integer | 是 | 页码，从 1 开始 |
| pageSize | integer | 是 | 每页条数，最大 100 |

- **响应格式**: 响应体为 `ApiResponse<TraceQueryResult>` 对象

| 字段 | 类型 | 说明 |
|---|---|---|
| errorCode | integer | 业务状态码，0 表示成功，非 0 表示失败 |
| errorMessage | string | 状态描述信息 |
| data | object | 查询结果数据 |
| data.items | array | Trace 列表，元素为 Trace 对象 |
| data.items[].traceId | string | Trace ID |
| data.items[].name | string | Trace 名称 |
| data.items[].timestamp | datetime | Trace 开始时间 |
| data.items[].duration | integer | Trace 耗时（毫秒） |
| data.items[].status | string | Trace 状态 |
| data.items[].totalTokens | integer | Token 总消耗量 |
| data.items[].totalCost | number | 总费用 |
| data.items[].inputTokens | integer | 输入 Token 数 |
| data.items[].outputTokens | integer | 输出 Token 数 |
| data.items[].inputCost | number | 输入费用 |
| data.items[].outputCost | number | 输出费用 |
| data.items[].warningCount | integer | 警告数量 |
| data.items[].errorCount | integer | 错误数量 |
| data.items[].modelNames | string[] | 使用的模型名称列表 |
| data.items[].scoresAvg | number | 平均Score |
| data.items[].userId | string | 关联用户 ID |
| data.items[].sessionId | string | 关联 Session ID |
| data.items[].environment | string | 环境标识 |
| data.items[].version | string | 版本号 |
| data.items[].release | string | 发布标识 |
| data.items[].tags | string[] | 标签列表 |
| data.items[].bookmarked | boolean | 是否被标记 |
| data.total | integer | 符合条件的总记录数 |
| data.page | integer | 当前页码 |
| data.pageSize | integer | 每页条数 |

- **错误码**:

| errorCode | errorMessage | 说明 |
|---|---|---|
| 150000 | EmptyProjectId | projectId 为空 |
| 150009 | EmptyTraceIds | traceIds 列表为空 |
| 150010 | ClickHouseQueryError | ClickHouse 查询失败 |
| 150011 | TooManyTraceIds | traceIds 数量超过限制 |
| 150012 | InvalidFilterType | 过滤条件类型无效 |
| 150013 | InvalidFilterColumn | 过滤列无效 |
| 150014 | InvalidFilterOperator | 过滤操作符无效 |
| 150015 | InvalidFilterValue | 过滤值无效 |
| 150016 | InvalidOrderBy | 排序规则无效 |
| 150017 | ClickHouseQueryTimeout | ClickHouse 查询超时 |
| 150018 | EmptyTraceId | Trace ID 为空 |
| 150019 | OrgAndProjectBothEmpty | organizationId 和 projectId 均为空 |
| 999999 | DefaultException | 默认异常 |

- **请求示例**:

```json
{
  "projectId": "project_8f8e2b8a-5c1a-4f3e-9d2b-6a1c3d5e7f90",
  "filter": {
    "column": 3,
    "operator": 5,
    "value": "2024-01-01T00:00:00Z"
  },
  "orderBy": {
    "column": 3,
    "descending": true
  },
  "page": 1,
  "pageSize": 20
}
```

- **响应示例**:

**成功响应 (HTTP 200)**:

```json
{
  "errorCode": 0,
  "errorMessage": "success",
  "data": {
    "items": [
      {
        "traceId": "trace_1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
        "name": "Agent 推理流程",
        "timestamp": "2024-01-01T00:00:00Z",
        "duration": 1523,
        "status": "completed",
        "totalTokens": 12500,
        "totalCost": 0.125,
        "inputTokens": 5000,
        "outputTokens": 7500,
        "inputCost": 0.05,
        "outputCost": 0.075,
        "warningCount": 2,
        "errorCount": 0,
        "modelNames": ["gpt-4o"],
        "scoresAvg": 0.95,
        "userId": "user_123",
        "sessionId": "session_456",
        "environment": "production",
        "version": "1.0.0",
        "release": "release-1.0",
        "tags": ["agent", "production"],
        "bookmarked": true
      }
    ],
    "total": 1,
    "page": 1,
    "pageSize": 20
  }
}
```

**失败响应 (HTTP 200, 业务错误)**:

```json
{
  "errorCode": 150000,
  "errorMessage": "EmptyProjectId",
  "data": null
}
```

---

## 19. ModelController 接口

本章覆盖 1 个 HTTP 端点，对应 `API/Controllers/DataManagement/ModelController.cs` 中的 `Get` 方法。

### 19.1. API-001 获取模型列表 (GET /api/data/model)

- **鉴权**: 需要 JWT JWT Bearer Token Token（`[Authorize]`），通过 `Authorization: JWT Bearer Token <token>` 请求头传递。用户需属于有效 Organization 或 Project 成员，否则返回 401 或 403。
- **描述**: 根据关键字、Project ID 等条件分页查询模型列表，支持排序和包含预定义模型。该接口用于模型管理页面，支持按名称模糊搜索、按项目过滤、按更新时间排序。
- **端点位置**: `API/Controllers/DataManagement/ModelController.cs:34`

- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| keyword | string | 否 | 搜索关键字，用于模糊匹配模型名称。 |
| projectid | string | 否 | Project ID，用于过滤属于特定项目的模型。 |
| includedpredefined | boolean | 否 | 是否包含预定义模型，默认值为 `false`。 |
| orderby | string | 否 | 排序字段，默认值为 `-updatedat`（按更新时间降序）。支持字段：`updatedat`、`createdat`、`name`，前缀 `-` 表示降序。 |
| page | int | 否 | 页码，默认值为 `1`，最小值为 `1`。 |
| pageSize | int | 否 | 每页条数，默认值为 `20`，最大值为 `100`。 |

- **响应格式**:

| 字段 | 类型 | 说明 |
|---|---|---|
| errorCode | int | 业务状态码，`0` 表示成功，非 `0` 表示失败。 |
| errorMessage | string | 提示信息。 |
| data | object | 返回的数据主体。 |
| data.items | array | 模型列表。 |
| data.items[].id | string | 模型唯一标识。 |
| data.items[].name | string | 模型名称。 |
| data.items[].projectid | string | 所属项目 ID。 |
| data.items[].ispredefined | boolean | 是否为预定义模型（系统预置，不可删除）。 |
| data.items[].createdat | string (date-time) | 创建时间，ISO 8601 格式。 |
| data.items[].updatedat | string (date-time) | 更新时间，ISO 8601 格式。 |
| data.total | int | 符合条件的总记录数。 |
| data.page | int | 当前页码。 |
| data.pageSize | int | 每页条数。 |

- **错误码**:

| HTTP 状态码 | errorCode | errorMessage | 说明 |
|---|---|---|---|
| 401 | 100000 | UnAuthToken | Token 无效或未提供。 |
| 401 | 100001 | EmptyUserId | User ID 为空。 |
| 400 | 140003 | InvalidProject | 项目不存在或已被删除。 |
| 403 | 140008 | UnauthorizedProjectAccess | 当前用户无权访问该项目。 |
| 400 | 150000 | EmptyProjectId | Project ID 为空。 |
| 500 | 150010 | ClickHouseQueryError | ClickHouse 查询失败。 |
| 400 | 150016 | InvalidOrderBy | 排序字段不合法。 |
| 500 | 150017 | ClickHouseQueryTimeout | ClickHouse 查询超时。 |
| 500 | 999999 | DefaultException | 服务器内部错误。 |

- **请求示例**:

```http
GET /api/data/model?keyword=test&projectid=proj_123456&includedpredefined=false&orderby=-updatedat&page=1&pageSize=20 HTTP/1.1
Host: api.example.com
Authorization: JWT Bearer Token <your-jwt-token>
```

- **响应示例**:

```json
// 成功响应 (HTTP 200)
{
  "errorCode": 0,
  "errorMessage": "success",
  "data": {
    "items": [
      {
        "id": "model_001",
        "name": "TestModel",
        "projectid": "proj_123456",
        "ispredefined": false,
        "createdat": "2024-01-01T12:00:00Z",
        "updatedat": "2024-01-02T12:00:00Z"
      }
    ],
    "total": 1,
    "page": 1,
    "pageSize": 20
  }
}
```

```json
// 失败响应 - 项目不存在 (HTTP 400)
{
  "errorCode": 140003,
  "errorMessage": "InvalidProject",
  "data": null
}
```

---

## 20. NotifyController 接口

本章共覆盖 2 个 HTTP 端点，每个端点一个接口卡片。两个端点均位于 `API/Controllers/PaymentManagement/NotifyController.cs`。

### 20.1. API-001 WeChatNotify (POST /api/payment/notify/wechatnotify)

- **鉴权**: 无
- **描述**: 接收微信Payment平台发送的异步Payment结果通知，验证通知签名与数据完整性，并据此更新订单Payment状态。
- **请求参数**: 无（请求体为微信Payment回调的原始 XML 数据，由微信服务器直接推送）
- **响应格式**: 微信Payment回调要求返回特定格式的 XML 以确认接收成功。

| 字段 | 类型 | 说明 |
| :--- | :--- | :--- |
| return_errorCode | string | 返回状态码，`SUCCESS` 表示接收成功，`FAIL` 表示接收失败 |
| return_msg | string | 返回信息，如处理失败时的错误描述 |

- **错误码**: 此接口为微信Payment回调，错误通过 `return_errorCode` 和 `return_msg` 返回给微信服务器，不适用业务错误码。若内部处理失败，可能记录以下异常：

| errorCode | errorMessage | 说明 |
| :--- | :--- | :--- |
| 810001 | WeChatSettingNotConfig | 微信PaymentConfig缺失，无法完成验签或业务处理 |
| 810009 | InvalidWeChatSerialNO | 微信Payment证书序列号无效 |
| 810010 | InvalidWeChatNotify | 微信Payment通知无效或验签失败 |
| 810016 | EmptyWeChatTransaction | 回调数据中缺少交易信息 |
| 810017 | InvalidWeChatTradeNo | 微信Payment交易号无效 |
| 810018 | EmptyWeChatNotify | 回调数据为空 |
| 810021 | WeChatEmptyResponse | 微信服务器返回空响应 |
| 810022 | WeChatErrorResponse | 微信服务器返回错误响应 |
| 810024 | WeChatQueryErrorResponse | 查询微信Payment结果时返回错误响应 |
| 810026 | OrderStateUpdateFailed | 更新订单状态失败 |
| 999999 | DefaultException | 处理过程中发生未预期异常 |

- **请求示例**: 此接口由微信Payment服务器主动调用，无需客户端构造请求。以下为微信Payment回调的示例数据（XML 格式）：

```xml
<xml>
  <appid><![CDATA[wx2421b1c4370ec43b]]></appid>
  <bank_type><![CDATA[CFT]]></bank_type>
  <cash_fee><![CDATA[1]]></cash_fee>
  <fee_type><![CDATA[CNY]]></fee_type>
  <is_subscribe><![CDATA[N]]></is_subscribe>
  <mch_id><![CDATA[10000100]]></mch_id>
  <nonce_str><![CDATA[5K8264ILTKCH16CQ2502SI8ZNMTM67VS]]></nonce_str>
  <openid><![CDATA[oUpF8uMuAJO_M2pxb1Q9zNjWeS6o]]></openid>
  <out_trade_no><![CDATA[20150806125344]]></out_trade_no>
  <result_errorCode><![CDATA[SUCCESS]]></result_errorCode>
  <return_errorCode><![CDATA[SUCCESS]]></return_errorCode>
  <sign><![CDATA[CB015DBB4654F412A04A6B7A9F9A3F9E]]></sign>
  <time_end><![CDATA[20150806125344]]></time_end>
  <total_fee>1</total_fee>
  <trade_type><![CDATA[JSAPI]]></trade_type>
  <transaction_id><![CDATA[1004400740201409030005092168]]></transaction_id>
</xml>
```

- **响应示例**:

**成功响应** (处理成功，通知微信服务器):

```xml
<xml>
  <return_errorCode><![CDATA[SUCCESS]]></return_errorCode>
  <return_msg><![CDATA[OK]]></return_msg>
</xml>
```

**失败响应** (处理失败，通知微信服务器稍后重试):

```xml
<xml>
  <return_errorCode><![CDATA[FAIL]]></return_errorCode>
  <return_msg><![CDATA[InvalidWeChatNotify]]></return_msg>
</xml>
```

### 20.2. API-002 AlipayNotify (POST /api/payment/notify/alipaynotify)

- **鉴权**: 无（Payment宝异步通知回调接口，由Payment宝服务器调用，不经过身份验证）
- **描述**: 接收Payment宝异步通知，验证签名并处理Payment结果，更新订单状态并记录交易通知。
- **请求参数**: 该接口接收Payment宝异步通知的 form 表单数据（`application/x-www-form-urlenerrorCoded`），字段由Payment宝定义，核心字段如下：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| notify_id | string | 是 | Payment宝通知 ID，用于标识通知的唯一性 |
| notify_type | string | 是 | 通知类型，固定为 `trade_status_sync` |
| notify_time | string | 是 | 通知时间，格式为 `yyyy-MM-dd HH:mm:ss` |
| trade_no | string | 是 | Payment宝交易号，Payment宝侧唯一交易标识 |
| out_trade_no | string | 是 | 商户订单号，对应 AgentInsightService 内部订单编号 |
| trade_status | string | 是 | 交易状态，取值包括 `TRADE_SUCCESS`、`TRADE_FINISHED`、`TRADE_CLOSED`、`WAIT_BUYER_PAY` 等 |
| total_amount | string | 是 | 订单总金额，单位为元，精确到小数点后两位 |
| seller_id | string | 是 | 收款Payment宝账号对应的Payment宝唯一用户号 |
| app_id | string | 是 | Payment宝分配给开发者的应用 ID |
| sign | string | 是 | 签名串，用于验证通知的合法性 |
| sign_type | string | 是 | 签名类型，固定为 `RSA2` |
| charset | string | 是 | 编码格式，固定为 `utf-8` |
| version | string | 是 | 接口版本，固定为 `1.0` |
| auth_app_id | string | 否 | 授权方应用 ID |
| buyer_id | string | 否 | 买家Payment宝用户号 |
| buyer_logon_id | string | 否 | 买家Payment宝账号 |
| fund_bill_list | string | 否 | Payment金额信息，JSON 数组格式 |
| receipt_amount | string | 否 | 实收金额 |
| invoice_amount | string | 否 | 开票金额 |
| buyer_pay_amount | string | 否 | 付款金额 |
| point_amount | string | 否 | 集分宝金额 |
| refund_fee | string | 否 | 总退款金额 |
| subject | string | 否 | 订单标题 |
| body | string | 否 | 商品描述 |
| gmt_create | string | 否 | 交易创建时间 |
| gmt_payment | string | 否 | 交易付款时间 |
| gmt_close | string | 否 | 交易关闭时间 |
| gmt_refund | string | 否 | 交易退款时间 |
| gmt_transit | string | 否 | 交易转运时间 |
| passback_params | string | 否 | 公共回传参数，若请求时传递了该参数，则返回时原样返回 |

- **响应格式**: 接口返回纯文本字符串，用于告知Payment宝服务器通知接收结果。

| 字段 | 类型 | 说明 |
|---|---|---|
| body | string | 返回 `success` 表示通知处理成功，Payment宝停止重发；返回 `failure` 表示处理失败，Payment宝将按策略重发通知 |

- **错误码**: 该接口为Payment宝异步通知回调，不返回业务错误码。处理失败时返回 `failure`，由Payment宝侧触发重试机制。内部处理可能涉及以下异常码：

| errorCode | errorMessage | 说明 |
|---|---|---|
| 810002 | AlipaySettingNotConfig | Payment宝PaymentConfig缺失，无法完成验签或业务处理 |
| 810003 | AlipayConnectionError | 连接Payment宝服务器失败 |
| 810004 | AlipayTradeError | Payment宝交易处理异常 |
| 810005 | InvalidAlipayTradeNo | 无效的Payment宝交易号 |
| 810006 | InvalidAlipayTransaction | 无效的Payment宝交易记录 |
| 810007 | AlipaySignatureError | Payment宝通知签名验证失败 |
| 810008 | AlipaySignDictionaryError | Payment宝签名参数字典构建失败 |
| 810011 | EmptyOrderNo | 通知中缺少商户订单号 (`out_trade_no`) |
| 810015 | OrderNotExist | 商户订单不存在，无法更新订单状态 |
| 810020 | AlipayPlaceOrderError | Payment宝下单失败 |
| 810025 | InvalidTotalAmount | 通知金额与订单金额不一致 |
| 810026 | OrderStateUpdateFailed | 订单状态更新失败 |
| 810027 | InvalidMerchant | 无效的商户信息，`seller_id` 或 `app_id` 不匹配 |
| 999999 | DefaultException | 未预期的系统异常 |

- **请求示例**:

```json
// 实际请求为 application/x-www-form-urlenerrorCoded 格式
// 以下为 form 表单字段的 JSON 化展示
{
  "notify_id": "2024122400221137990050991234",
  "notify_type": "trade_status_sync",
  "notify_time": "2024-12-24 18:30:00",
  "trade_no": "2024122422001490600507012345",
  "out_trade_no": "AIS202412241830001",
  "trade_status": "TRADE_SUCCESS",
  "total_amount": "99.00",
  "seller_id": "2088123456789012",
  "app_id": "2021003123456789",
  "sign": "base64_enerrorCoded_signature_string",
  "sign_type": "RSA2",
  "charset": "utf-8",
  "version": "1.0",
  "buyer_id": "2088123456789013",
  "buyer_logon_id": "user@example.com",
  "gmt_create": "2024-12-24 18:29:30",
  "gmt_payment": "2024-12-24 18:30:00",
  "subject": "AgentInsightService 专业版订阅"
}
```

- **响应示例**:

```json
// 成功响应
success

// 失败响应（签名验证失败或业务处理异常）
failure
```

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
| API-077 | ANY | `/api/public` | LiteralRoute.literal_route | Bearer |
| API-078 | ANY | `/api/test` | LiteralRoute.literal_route | Bearer |

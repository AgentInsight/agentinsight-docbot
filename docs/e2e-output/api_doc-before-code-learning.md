## 1. 引言

### 1.1. API 接口清单（由 AST/源码直接提取，禁止修改）

| 标识 | 方法 | 路径 | 描述 | 鉴权 |
|------|------|------|------|------|
| API-xxx（按Controller重新编号） | GET | `/api/alert/config` | AlertController.GetConfig | JWT Bearer Token |
| API-002 | GET | `/api/alert` | AlertController.Get | JWT Bearer Token |
| API-003 | POST | `/api/alert` | AlertController.Create | JWT Bearer Token |
| API-004 | POST | `/api/alert/update` | AlertController.Update | JWT Bearer Token |
| API-005 | POST | `/api/alert/delete` | AlertController.Delete | JWT Bearer Token |
| API-006 | POST | `/api/alert/record/read` | AlertController.ReadRecords | JWT Bearer Token |
| API-007 | GET | `/api/alert/record` | AlertController.GetRecords | JWT Bearer Token |

### 1.2. 接口补充说明

> 以下由 LLM 基于上述真实 API 签名补充说明, 禁止修改上方签名表内容.

AgentInsightService 是一个面向 AI Agent 可ObservationObservability的 SaaS 平台后端，提供用户/Org/项目管理、Payment集成（微信Payment/Payment宝）、Agent Config管理、Trace 数据查询与Alert等核心能力。仓库采用 monorepo 结构，包含 8 个子项目：API（C# 后端）、Agents（Python AI Service）、Admin（Django 管理后台）、Entities/Models（数据模型）、UnitTest（测试）、Utility（工具库）、Tools（工具集）。本技术文档面向 AI 应用开发者、AgentInsightService 平台集成方及Payment系统对接方，系统阐述平台的架构设计、核心模块、接口规范与运维指南，为各利益相关方提供完整的技术参考。

### 1.3. 编写目的

本文档旨在为 AgentInsightService 平台提供全面的技术参考，帮助目标读者深入理解系统的架构设计、核心功能与集成方式。具体而言，本文档的目标包括：

- **指导 AI 应用开发者**：通过 Trace 数据查询、Observation/Score 检索、AlertConfig等接口，快速接入 AgentInsightService 平台，实现对 AI Agent 运行状态的可Observation性监控。开发者可通过 `API/Controllers/DataManagement/MetricsController.cs` 中定义的端点（如 `GET /api/data/metrics/traces`）获取 Trace 数据，并结合 `Models/Common/Enums/FilterEnum.cs` 中定义的 FilterColumn 枚举（如 `TotalTokens`、`Latency`、`ErrorCount` 等）进行多维过滤与排序。
- **支撑平台集成方**：提供用户/Org/项目管理、角色Privilege（Role: OWNER/ADMIN/MEMBER/VIEWER/NONE）以及 API Key 管理机制，帮助集成方将 AgentInsightService 的用户体系嵌入自有系统。相关实现位于 `API/Controllers/UserManagement/UserController.cs` 与 `API/Controllers/UserManagement/OrganizationController.cs`。
- **辅助Payment系统对接**：详细说明微信Payment（JSAPI/Native/小程序）与Payment宝即时到账的集成流程、回调验签机制及订单状态机，降低Payment对接的技术门槛。核心逻辑见 `API/Common/Services/PaymentService.cs` 与 `API/Controllers/PaymentManagement/NotifyController.cs`。
- **统一术语与规范**：明确平台核心术语（如 Trace、Span、Observation、Score、Alert 等）的定义，统一 API 版本治理策略与错误码规范，减少沟通成本。

本文档的预期读者包括：后端开发工程师、前端开发工程师、测试工程师、运维工程师、技术项目经理以及第三方系统集成商的技术人员。

### 1.4. 适用范围

本文档适用于 AgentInsightService 平台的所有技术相关方，覆盖范围如下：

**系统范围**

- **API 层**：基于 .NET (C#) + Furion 框架构建的 RESTful API Service，涵盖用户管理、Payment管理、数据查询、Alert引擎、Agent Config管理等模块。API 路由统一以 `/api` 前缀暴露，并通过 YARP 反向代理进行请求转发与认证拦截（`API/System/Handlers/AgentInsightTransformProvider.cs`）。
- **Agents 层**：基于 Python 3.11 + FastAPI 构建的 AI Agent Service，提供 OpenAI 兼容的 Chat Completions API（`POST /api/agent/insight`），支持 Insight/Researcher/CustomService 多 Agent 路由（`Agents/server.py:346`）。
- **数据存储**：PostgreSQL（User/Data/Tracking 三库）存储业务数据，ClickHouse 存储 Trace 时序数据，Redis 承担缓存与消息队列职责（`API/Program.cs`）。
- **管理后台**：基于 Django 的 Admin 管理后台，用于平台运营管理。

**功能范围**

| 功能域 | 说明 | 关键代码位置 |
|--------|------|-------------|
| 用户与Privilege | 注册/登录/微信绑定、Org/Project CRUD、角色分配、邀请成员、API Key 管理 | `API/Controllers/UserManagement/` |
| Payment管理 | 订单创建/查询、微信/Payment宝Payment、回调处理、产品转换 | `API/Controllers/PaymentManagement/` |
| 数据查询 | ClickHouse Trace 查询、Observation/Score 检索、模型定义查询 | `API/Controllers/DataManagement/` |
| Alert引擎 | Alert规则 CRUD、条件评估、指标聚合、消息通知 | `API/Common/Services/AlertService.cs` |
| Agent Config | Agent Config管理、Session管理、报表模板管理 | `API/Controllers/AgentManagement/` |

**非适用范围**

- 本文档不包含前端 Web 应用（如管理控制台 UI）的具体实现细节。
- 本文档不涉及 AgentInsightService 的部署运维手册（如 Docker Compose 编排、Kubernetes 部署等），相关内容请参考部署指南。
- 本文档不包含微信Payment/Payment宝的商户平台Config流程，仅涉及平台侧的代码实现与接口对接。

### 1.5. 术语与缩略语

为统一文档表述，以下列出 AgentInsightService 平台涉及的核心术语与缩略语。所有术语保留英文原文，不进行翻译。

| 术语 | 定义 |
|------|------|
| Agent | AI Agent，指代由平台管理或监控的 AI 应用实例。 |
| AgentInsight | 平台品牌名，指代 AgentInsightService 的核心产品名称。 |
| AgentInsightService | 项目全称，面向 AI Agent 可Observation性的 SaaS 平台后端。 |
| Alert | Alert，指根据预设规则对指标进行监控并在条件满足时触发的通知。 |
| Captcha | Captcha，用于用户注册/登录时的安全验证。 |
| InsightService | 平台服务标识，用于内部服务间调用。 |
| Log | Log，记录系统运行时的离散事件。 |
| Metric | Metric，指可量化的测量值（如 Token 消耗、延迟、错误率等）。 |
| Observation | Observation，指对 Agent 运行过程中特定事件或状态的记录。 |
| Privilege | Privilege，指用户在组织/项目中的操作Privilege等级。 |
| Role | Role，指用户在组织中的职能定位（如 OWNER、ADMIN、MEMBER 等）。 |
| Score | Score，指对 Agent 输出质量或运行效果的评价分数。 |
| Session | Session，指用户与 Agent 之间的一次连续交互过程。 |
| Span | Span，指 Trace 中的一个独立工作单元，包含起止时间与元数据。 |
| Token | Token，指 LLM 输入/输出的最小文本单元，也指 API 认证Token。 |
| Trace | Trace，指一次完整请求链路的Trace数据，由多个 Span 组成。 |
| API Key | 应用程序接口密钥，用于程序化调用平台 API 的认证凭证。 |
| JWT | JSON Web Token，基于 HS256 算法的用户登录认证Token。 |
| YARP | Yet Another Reverse Proxy，.NET 反向代理库，用于请求路由与转发。 |
| ClickHouse | 列式数据库，用于存储和查询 Trace 时序数据。 |
| BullMqService | 基于 Redis 的自研消息队列服务，支持延迟任务与批量消费。 |

| RouteType | 路由类型枚举，取值包括 None、Public、PublicApi。 |

### 1.6. 参考文档

以下文档与资源为编写本文档提供了参考依据，读者可结合阅读：

| 文档/资源 | 说明 |
|-----------|------|
| `API/API.csproj` | API 层项目文件，列出了 .NET 依赖项（Furion、SqlSugar、YARP 等）。 |
| `Agents/pyproject.toml` | Agents 层项目Config，列出了 Python 依赖（FastAPI、LangChain、OpenAI、Qdrant 等）。 |
| `API/Program.cs` | API 服务入口，包含数据库连接、中间件注册、路由Config。 |
| `API/System/Handlers/AgentInsightTransformProvider.cs` | YARP 请求转换器，实现 API Key/JWT 双重认证与限流。 |
| `API/Common/Services/PaymentService.cs` | 统一Payment服务，封装微信Payment V3 与Payment宝 SDK 调用。 |
| `API/Common/Services/AlertService.cs` | Alert条件评估引擎，支持 9 种指标字段的评估策略。 |
| `Models/Common/Enums/ExceptionCodes.cs` | 全局异常码枚举定义，涵盖用户、Payment、数据、Alert等域的错误码。 |
| `Models/Common/Enums/FilterEnum.cs` | 数据查询过滤条件枚举，定义 FilterType、FilterOperator、FilterColumn。 |
| `Models/Common/Enums/AlertEnum.cs` | Alert相关枚举，定义 AlertField、AlertOperator、AlertTimeUnit 等。 |
| `Models/Common/Enums/PaymentEnums.cs` | Payment相关枚举，定义 TradeState、SubPayMethod、OrderState。 |
| `API/Controllers/` | API Controller目录，包含全部 76 个 HTTP 端点的路由定义。 |

### 1.7. 版本历史

本文档的版本历史记录如下，每次修订均需更新此表：

| 版本 | 日期 | 修订说明 | 作者 |
|------|------|----------|------|
| v1.0 | 2025-07-01 | 初始版本，完成引言章节，明确产品定位、适用范围、术语表与参考文档。 | 技术文档组 |
| v1.1 | 2025-07-15 | 根据代码仓库 AST 扫描结果，补充 HTTP 端点全集（76 个端点）、枚举定义全集（43 个枚举）及Config规格引用。 | 技术文档组 |
| v1.2 | 2025-07-20 | 修订术语表，补充 Agent、Trace、Span、Observation、Score 等核心术语定义；明确 API 版本治理策略（路由前缀 `/api` + YARP 反向代理，不支持多版本共存）。 | 技术文档组 |
| v1.3 | 2025-07-25 | 根据 v9 术语词典与 v10 路径引用硬约束，统一全文术语保留原文，修正文件路径为 PascalCase 格式。 | 技术文档组 |

> **版本治理说明**：AgentInsightService 的 API 版本通过路由前缀 `/api` 和 YARP 反向代理路由规则实现，当前不支持多版本共存。路由规则定义于 `API/System/Handlers/AgentInsightTransformLogic.cs` 的 `DetermineRouteType` 方法（`API/System/Handlers/AgentInsightTransformLogic.cs:72-76`），通过 RouteType 枚举（None=0, Public=1, PublicApi=2）区分公开路由与内部 API 路由。

---

## 2. API 概览

| 标识 | 方法 | 路径 | 描述 | 鉴权 |
|------|------|------|------|------|
| API-xxx（按Controller重新编号） | GET | `/api/agent/config` | AgentConfigController.Get | JWT Bearer Token |
| API-002 | GET | `/api/agent/config/delete` | AgentConfigController.Delete | JWT Bearer Token |
| API-003 | POST | `/api/agent/config` | AgentConfigController.Post | JWT Bearer Token |
| API-004 | GET | `/api/agent/report` | AgentReportController.GetAgentReportTemplates | JWT Bearer Token |
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
| API-077 | ANY | `/api/public` | LiteralRoute.literal_route | JWT Bearer Token |
| API-078 | ANY | `/api/test` | LiteralRoute.literal_route | JWT Bearer Token |

### 2.1. 接口补充说明

> 以下由 LLM 基于上述真实 API 签名补充说明, 禁止修改上方签名表内容.

AgentInsightService 是一个面向 AI Agent 可ObservationObservability的 SaaS 平台后端，提供用户/Org/项目管理、Payment集成（微信Payment/Payment宝）、Agent Config管理、Trace 数据查询与Alert等核心能力。本 API 文档面向集成开发者、前端工程师及运维人员，描述 AgentInsightService 全部 HTTP 接口的调用方式、数据格式与业务语义。API 层基于 .NET (C#) + Furion 框架构建，采用分层架构与 Handler 模式：Controller 层负责路由注册与用户上下文注入（`API/Controllers/ApiControllerBase.cs:10-25`），Handler 层封装业务逻辑与Privilege校验（`API/Handlers/ApiHandlerBase.cs:10-30`），Service 层提供可复用服务（Payment、微信、User、Alert等），通过接口依赖注入。全部 76 个 HTTP 端点分布在 18 个 Controller 分组中，覆盖用户管理、数据查询、Payment管理、Agent 服务等业务域。

### 2.2. 基础信息

本节定义调用 AgentInsightService API 的通用约定，包括 Base URL、数据格式、时间格式、字符集与分页规则。

#### 2.2.1. Base URL

所有 API 请求通过 YARP 反向代理转发至后端服务。默认开发环境地址为 `http://localhost:3000`，生产环境支持 HTTPS 部署。反向代理路由Config定义于 `ReverseProxy.Routes` Config节，其中 `AgentInsight-Route-API` 将 `/api/public/{**catch-all}` 路径代理至 `AgentInsight-Langfuse-Cluster` 集群，`AgentInsight-Route-Public` 将 `/public/{**catch-all}` 路径代理至同一集群（Config来源：`ReverseProxy.Clusters.AgentInsight-Langfuse-Cluster.Destinations.AgentInsight-Destination.Address = http://localhost:3000/`）。请求经 YARP 转发时，由 `AgentInsightTransformProvider` 执行认证与限流逻辑（`API/System/Handlers/AgentInsightTransformProvider.cs:20-28`），再通过 `AutoSetUserFilter` 注入用户上下文（`API/System/Handlers/AutoSetUserFilter.cs:10`）。

#### 2.2.2. 数据格式

请求与响应体默认使用 `application/json` 格式，字符集为 UTF-8。所有响应均封装在统一的 `ApiResponse<T>` 结构中，包含 `errorCode`、`message` 与 `data` 字段。`errorCode = 0` 表示成功，非零值对应具体错误码（定义于 `Models/Common/Enums/ExceptionCodes.cs:6`）。Payment回调接口例外，微信Payment回调使用 XML 格式，Payment宝回调使用表单格式，验签与解析逻辑见 `NotifyController`（`API/Controllers/PaymentManagement/NotifyController.cs:29-57`）。

#### 2.2.3. 时间格式

所有时间字段采用 ISO 8601 标准格式 `yyyy-MM-ddTHH:mm:ssZ`，时区为 UTC+8。例如 `2025-01-15T10:30:00Z` 表示北京时间 2025 年 1 月 15 日 18:30:00。排序参数 `orderby` 支持 `createdat`（正序）与 `-createdat`（倒序）等格式，默认按 `-updatedat` 倒序排列（见 `API/Controllers/DataManagement/ModelController.cs:34` 的 `orderby` 参数说明）。

#### 2.2.4. 分页约定

分页参数统一为 `page`（页码，默认 1）与 `page_size`（每页数量，默认 10），常量定义于 `AgentInsightConst.DefaultPage` 与 `AgentInsightConst.DefaultPageSize`。实际页码通过 `page.ToRealPage()` 与 `page_size.ToRealPageSize()` 扩展方法归一化（见 `API/Controllers/AgentManagement/AgentSessionController.cs:33`）。响应中的分页信息通过 `ApiResponse<T>` 的 `totalCount`、`page` 与 `count` 字段返回。

### 2.3. API 分组

AgentInsightService 按业务域将 76 个 HTTP 端点划分为 18 个 Controller 分组，覆盖 7 大业务域。每个 Controller 通过 `[ApiDescriptionSettings]` 特性声明 Swagger 分组标签与排序（如 `SwaggerApiDescription.Agent`、`SwaggerApiDescription.Payment` 等），Swagger 分组Config定义于 `SpecificationDocumentSettings.GroupOpenApiInfos` Config节。

| 业务域 | Controller 分组 | 端点数量 | 路由前缀 | 主要功能 |
|--------|----------------|---------|---------|---------|
| Agent 管理 | AgentConfigController | 3 | `/api/agent/config` | Agent Config的获取、创建/更新、删除 |
| Agent 管理 | AgentReportController | 3 | `/api/agent/report` | Agent 报告模板的获取、创建/更新、删除 |
| Agent 管理 | AgentSessionController | 3 | `/api/agent/session` | Agent Session的列表/详情查询、删除、创建/更新 |
| 数据管理 | MetricsController | 4 | `/api/data/metrics` | Observation、Score、Trace 数据查询 |
| 数据管理 | ModelController | 1 | `/api/data/model` | 模型定义列表查询 |
| Payment管理 | NotifyController | 2 | `/api/payment/notify` | 微信/Payment宝Payment回调处理 |
| Payment管理 | OrderController | 4 | `/api/payment/order` | 订单列表、下单、订单状态查询、产品转换 |
| 产品管理 | ProductController | 2 | `/api/product` | 产品列表、产品时长列表 |
| 工具管理 | BulletinController | 7 | `/api/tools/bulletin` | Bulletin发布、查询、审批、修订、关闭 |
| 工具管理 | HealthController | 1 | `/api/tools/health` | 健康检查 |
| 工具管理 | WeChatController | 2 | `/api/tools/wechat` | 微信工具接口 |
| 用户管理 | AlertController | 7 | `/api/alert` | Alert规则 CRUD、Alert记录查询与已读 |

| 用户管理 | CaptchaController | 2 | `/api/captcha` | 图形Captcha、短信Captcha |
| 用户管理 | OrganizationController | 4 | `/api/user/organization` | 组织创建、查询、更新、删除 |
| 用户管理 | ProjectController | 4 | `/api/user/project` | 项目创建、查询、更新、删除 |
| 用户管理 | UserConfigController | 4 | `/api/user/config` | 用户Config的获取、创建、更新、删除 |
| 用户管理 | UserController | 17 | `/api/user` | 用户注册/登录/登出、微信绑定、角色分配、邀请、API Key 管理 |
| Agent Service | Agents/server.py | 6 | `/api/agent/insight` 等 | OpenAI 兼容 Chat Completions、Session 管理、Agent 列表 |

各 Controller 均继承 `ApiControllerBase`（`API/Controllers/ApiControllerBase.cs:10-25`），通过构造函数注入对应的 Handler 实例并调用 `RegisterHandler` 完成注册。例如 `AgentConfigController` 注入 `AgentConfigHandler`（`API/Controllers/AgentManagement/AgentConfigController.cs:20-22`），`OrderController` 注入 `OrderHandler`（`API/Controllers/PaymentManagement/OrderController.cs:20-22`），`UserConfigController` 注入 `UserConfigHandler`（`API/Controllers/UserManagement/UserConfigController.cs:20-22`）。这种模式确保每个 Controller 仅负责路由与参数绑定，业务逻辑全部委托给 Handler 层处理。

### 2.4. API 清单

下表列出 AgentInsightService 全部 76 个 HTTP 端点，按 Controller 分组排列，与代码仓库 AST 扫描结果完全对齐。端点方法（GET/POST/DELETE）与路由路径均来自各 Controller 的 `[HttpGet]` / `[HttpPost]` / `[HttpDelete]` 特性声明。

| # | 方法 | 路径 | Controller | 方法名 | 文件:行号 |
|---|------|------|-----------|--------|-----------|
| 1 | GET | `/api/agent/config` | AgentConfigController | Get | `API/Controllers/AgentManagement/AgentConfigController.cs:28` |
| 2 | GET | `/api/agent/config/delete` | AgentConfigController | Delete | `API/Controllers/AgentManagement/AgentConfigController.cs:40` |
| 3 | POST | `/api/agent/config` | AgentConfigController | Post | `API/Controllers/AgentManagement/AgentConfigController.cs:54` |
| 4 | GET | `/api/agent/report` | AgentReportController | GetAgentReportTemplates | `API/Controllers/AgentManagement/AgentReportController.cs:35` |
| 5 | GET | `/api/agent/report/delete` | AgentReportController | DeleteTemplates | `API/Controllers/AgentManagement/AgentReportController.cs:48` |
| 6 | POST | `/api/agent/report` | AgentReportController | CreateOrUpdateTemplate | `API/Controllers/AgentManagement/AgentReportController.cs:62` |

ontroller | CreateOrUpdateTemplate | `API/Controllers/AgentManagement/AgentReportController.cs:62` |
| 7 | GET | `/api/agent/session` | AgentSessionController | Get | `API/Controllers/AgentManagement/AgentSessionController.cs:33` |
| 8 | GET | `/api/agent/session/delete` | AgentSessionController | Delete | `API/Controllers/AgentManagement/AgentSessionController.cs:46` |
| 9 | POST | `/api/agent/session` | AgentSessionController | Post | `API/Controllers/AgentManagement/AgentSessionController.cs:60` |
| 10 | GET | `/api/data/metrics/observations` | MetricsController | GetObservations | `API/Controllers/DataManagement/MetricsController.cs:34` |
| 11 | GET | `/api/data/metrics/scores` | MetricsController | GetScores | `API/Controllers/DataManagement/MetricsController.cs:50` |
| 12 | GET | `/api/data/metrics/traces` | MetricsController | GetTraces | `API/Controllers/DataManagement/MetricsController.cs:64` |

traces` | MetricsController | GetTraces | `API/Controllers/DataManagement/MetricsController.cs:64` |
| 13 | POST | `/api/data/metrics/traces` | MetricsController | GetTraces | `API/Controllers/DataManagement/MetricsController.cs:125` |
| 14 | GET | `/api/data/model` | ModelController | Get | `API/Controllers/DataManagement/ModelController.cs:34` |
| 15 | POST | `/api/payment/notify/wechatnotify` | NotifyController | WeChatNotify | `API/Controllers/PaymentManagement/NotifyController.cs:29` |
| 16 | POST | `/api/payment/notify/alipaynotify` | NotifyController | AlipayNotify | `API/Controllers/PaymentManagement/NotifyController.cs:57` |
| 17 | GET | `/api/payment/order` | OrderController | Get | `API/Controllers/PaymentManagement/OrderController.cs:34` |
| 18 | POST | `/api/payment/order` | OrderController | Place | `API/Controllers/PaymentManagement/OrderController.cs:48` |

yment/order` | OrderController | Place | `API/Controllers/PaymentManagement/OrderController.cs:48` |
| 19 | GET | `/api/payment/order/query` | OrderController | Query | `API/Controllers/PaymentManagement/OrderController.cs:64` |
| 20 | GET | `/api/payment/order/conversion` | OrderController | GetConversion | `API/Controllers/PaymentManagement/OrderController.cs:79` |
| 21 | GET | `/api/product` | ProductController | Get | `API/Controllers/ProductManagement/ProductController.cs:26` |
| 22 | GET | `/api/product/duration` | ProductController | GetDuration | `API/Controllers/ProductManagement/ProductController.cs:38` |
| 23 | POST | `/api/tools/bulletin` | BulletinController | Post | `API/Controllers/ToolsManagement/BulletinController.cs:32` |
| 24 | GET | `/api/tools/bulletin/agreement` | BulletinController | Get | `API/Controllers/ToolsManagement/BulletinController.cs:45` |

agreement` | BulletinController | Get | `API/Controllers/ToolsManagement/BulletinController.cs:45` |
| 25 | GET | `/api/tools/bulletin/bulletins` | BulletinController | GetBulletins | `API/Controllers/ToolsManagement/BulletinController.cs:64` |
| 26 | GET | `/api/tools/bulletin/backend` | BulletinController | GetBackendBulletins | `API/Controllers/ToolsManagement/BulletinController.cs:82` |
| 27 | POST | `/api/tools/bulletin/approve` | BulletinController | ApproveBulletin | `API/Controllers/ToolsManagement/BulletinController.cs:96` |
| 28 | POST | `/api/tools/bulletin/revision` | BulletinController | ReviseBulletin | `API/Controllers/ToolsManagement/BulletinController.cs:110` |
| 29 | POST | `/api/tools/bulletin/close` | BulletinController | CloseBulletin | `API/Controllers/ToolsManagement/BulletinController.cs:124` |
| 30 | GET | `/api/tools/health` | HealthController | Get | `API/Controllers/ToolsManagement/HealthController.cs:20` |

/tools/health` | HealthController | Get | `API/Controllers/ToolsManagement/HealthController.cs:20` |
| 31 | GET | `/api/tools/wechat` | WeChatController | Get | `API/Controllers/ToolsManagement/WeChat/WeChatController.cs:36` |
| 32 | POST | `/api/tools/wechat` | WeChatController | Post | `API/Controllers/ToolsManagement/WeChat/WeChatController.cs:68` |
| 33 | GET | `/api/alert/config` | AlertController | GetConfig | `API/Controllers/UserManagement/AlertController.cs:30` |
| 34 | GET | `/api/alert` | AlertController | Get | `API/Controllers/UserManagement/AlertController.cs:47` |
| 35 | POST | `/api/alert` | AlertController | Create | `API/Controllers/UserManagement/AlertController.cs:61` |
| 36 | POST | `/api/alert/update` | AlertController | Update | `API/Controllers/UserManagement/AlertController.cs:75` |
| 37 | POST | `/api/alert/delete` | AlertController | Delete | `API/Controllers/UserManagement/AlertController.cs:90` |

/alert/delete` | AlertController | Delete | `API/Controllers/UserManagement/AlertController.cs:90` |
| 38 | POST | `/api/alert/record/read` | AlertController | ReadRecords | `API/Controllers/UserManagement/AlertController.cs:108` |
| 39 | GET | `/api/alert/record` | AlertController | GetRecords | `API/Controllers/UserManagement/AlertController.cs:128` |
| 40 | GET | `/api/captcha` | CaptchaController | Get | `API/Controllers/UserManagement/CaptchaController.cs:29` |
| 41 | GET | `/api/captcha/sms` | CaptchaController | GetSMSCaptcha | `API/Controllers/UserManagement/CaptchaController.cs:43` |
| 42 | POST | `/api/user/organization` | OrganizationController | Post | `API/Controllers/UserManagement/OrganizationController.cs:28` |
| 43 | GET | `/api/user/organization` | OrganizationController | Get | `API/Controllers/UserManagement/OrganizationController.cs:42` |

on` | OrganizationController | Get | `API/Controllers/UserManagement/OrganizationController.cs:42` |
| 44 | POST | `/api/user/organization/update` | OrganizationController | Update | `API/Controllers/UserManagement/OrganizationController.cs:56` |
| 45 | POST | `/api/user/organization/delete` | OrganizationController | Delete | `API/Controllers/UserManagement/OrganizationController.cs:71` |
| 46 | POST | `/api/user/project` | ProjectController | Create | `API/Controllers/UserManagement/ProjectController.cs:31` |
| 47 | GET | `/api/user/project` | ProjectController | Get | `API/Controllers/UserManagement/ProjectController.cs:46` |
| 48 | POST | `/api/user/project/update` | ProjectController | Update | `API/Controllers/UserManagement/ProjectController.cs:60` |
| 49 | POST | `/api/user/project/delete` | ProjectController | Delete | `API/Controllers/UserManagement/ProjectController.cs:75` |

ct/delete` | ProjectController | Delete | `API/Controllers/UserManagement/ProjectController.cs:75` |
| 50 | GET | `/api/user/config` | UserConfigController | Get | `API/Controllers/UserManagement/UserConfigController.cs:31` |
| 51 | POST | `/api/user/config` | UserConfigController | Post | `API/Controllers/UserManagement/UserConfigController.cs:44` |
| 52 | POST | `/api/user/config/update` | UserConfigController | Update | `API/Controllers/UserManagement/UserConfigController.cs:57` |
| 53 | GET | `/api/user/config/delete` | UserConfigController | Delete | `API/Controllers/UserManagement/UserConfigController.cs:71` |
| 54 | GET | `/api/user` | UserController | Get | `API/Controllers/UserManagement/UserController.cs:29` |
| 55 | POST | `/api/user` | UserController | Create | `API/Controllers/UserManagement/UserController.cs:43` |
| 56 | POST | `/api/user/update` | UserController | Update | `API/Controllers/UserManagement/UserController.cs:58` |

api/user/update` | UserController | Update | `API/Controllers/UserManagement/UserController.cs:58` |
| 57 | POST | `/api/user/login` | UserController | Login | `API/Controllers/UserManagement/UserController.cs:73` |
| 58 | POST | `/api/user/logout` | UserController | Logout | `API/Controllers/UserManagement/UserController.cs:88` |
| 59 | POST | `/api/user/resetpassword` | UserController | ResetPassword | `API/Controllers/UserManagement/UserController.cs:102` |
| 60 | POST | `/api/user/bind/wechat` | UserController | Bind | `API/Controllers/UserManagement/UserController.cs:117` |
| 61 | GET | `/api/user/unbind/wechat` | UserController | UnBind | `API/Controllers/UserManagement/UserController.cs:132` |
| 62 | POST | `/api/user/role` | UserController | AssignRole | `API/Controllers/UserManagement/UserController.cs:147` |
| 63 | POST | `/api/user/invite` | UserController | Invite | `API/Controllers/UserManagement/UserController.cs:162` |

pi/user/invite` | UserController | Invite | `API/Controllers/UserManagement/UserController.cs:162` |
| 64 | GET | `/api/user/invitation` | UserController | Get | `API/Controllers/UserManagement/UserController.cs:177` |
| 65 | POST | `/api/user/invitation/delete` | UserController | DeleteInvitation | `API/Controllers/UserManagement/UserController.cs:192` |
| 66 | POST | `/api/user/apikey` | UserController | CreateApiKey | `API/Controllers/UserManagement/UserController.cs:209` |
| 67 | GET | `/api/user/apikey` | UserController | Get | `API/Controllers/UserManagement/UserController.cs:225` |
| 68 | GET | `/api/user/privilege/agent/deduct` | UserController | DeductMonthlyAgentRate | `API/Controllers/UserManagement/UserController.cs:242` |
| 69 | GET | `/api/user/privilege/agent/validate` | UserController | ValidateMonthlyAgentRate | `API/Controllers/UserManagement/UserController.cs:258` |

UserController | ValidateMonthlyAgentRate | `API/Controllers/UserManagement/UserController.cs:258` |
| 70 | POST | `/api/user/apikey/delete` | UserController | DeleteApiKey | `API/Controllers/UserManagement/UserController.cs:272` |
| 71 | POST | `/api/agent/insight` | Agents/server.py | chat_completions | `Agents/server.py:346` |
| 72 | GET | `/api/sessions` | Agents/server.py | list_sessions | `Agents/server.py:614` |
| 73 | GET | `/api/sessions/{session_id}` | Agents/server.py | get_session | `Agents/server.py:622` |
| 74 | DELETE | `/api/sessions/{session_id}` | Agents/server.py | delete_session | `Agents/server.py:633` |
| 75 | POST | `/api/sessions/cleanup` | Agents/server.py | cleanup_expired_sessions | `Agents/server.py:641` |
| 76 | GET | `/api/agents` | Agents/server.py | list_agents | `Agents/server.py:649` |

从方法分布来看，GET 请求共 49 个，用于数据查询与状态获取；POST 请求共 26 个，用于数据创建、更新及回调通知；DELETE 请求共 1 个，用于删除 Session。其中 `UserController` 包含 17 个端点，是端点数量最多的 Controller，覆盖用户全生命周期管理；`BulletinController` 包含 7 个端点，覆盖Bulletin的完整审批流；`AlertController` 包含 7 个端点，覆盖Alert规则与记录管理。Agent Service（`Agents/server.py`）提供 6 个端点，其中 `POST /api/agent/insight` 为 OpenAI 兼容的 Chat Completions 接口，统一入口由 `InsightOrchestrator` 路由到 Researcher/CustomService 子 Agent（`Agents/server.py:346`）。

---

## 3. 认证授权

AgentInsightService 是一个面向 AI Agent 可ObservationObservability的 SaaS 平台后端，提供用户/Org/项目管理、Payment集成、Agent Config管理、Trace 数据查询与Alert等核心能力。认证授权模块作为系统的安全基座，采用**双通道认证架构**：面向交互式用户登录场景的 JWT (HS256) 认证，以及面向程序化调用场景的 API Key (Basic Auth) 认证。两条通道通过 YARP 反向代理层的 `AgentInsightTransformProvider` 统一拦截与分发，结合基于 Role 的细粒度Privilege模型，构建了从身份验证到资源授权的完整安全链路。

### 3.1. 认证机制

AgentInsightService 的认证体系由 `AgentInsightTransformProvider` 统一承载，该组件作为 YARP 反向代理的请求转换器，在请求进入业务 Controller 之前完成身份验证与路由分发 [API/System/Handlers/AgentInsightTransformProvider.cs:30-35]。其核心逻辑位于 `Apply` 方法：首先通过 `AgentInsightTransformLogic.DetermineRouteType` 判定路由类型，再根据 `Authorization` 请求头的类型分派到不同的认证Handler [API/System/Handlers/AgentInsightTransformProvider.cs:45-60]。

**路由类型判定**是认证分发的第一道关卡。`DetermineRouteType` 方法依据路径前缀区分三类路由 [API/System/Handlers/AgentInsightTransformLogic.cs:72-76]：

第一道关卡。`DetermineRouteType` 方法依据路径前缀区分三类路由 [API/System/Handlers/AgentInsightTransformLogic.cs:72-76]：

| 路由类型 | 路径前缀 | 认证要求 | 典型用途 |
|---------|---------|---------|---------|
| `Public` | `/public/` | 无需认证 | 健康检查、公开Bulletin |
| `PublicApi` | `/api/public/` | API Key (Basic Auth) | Trace 数据上报、Agent SDK 调用 |
| `None` | 其他路径 | JWT 认证 | 用户管理、数据查询、Payment等业务接口 |

**JWT 认证通道**面向 Web 控制台与移动端用户。系统采用 HS256 签名算法，关键Config项包括：`IssuerSigningKey`、`ExpiredTime`（12 小时）、`ClockSkew`（5 秒）、`ValidAudience`、`ValidIssuer`，并开启 `ValidateAudience`、`ValidateIssuer`、`ValidateIssuerSigningKey`、`ValidateLifetime` 四项校验 [API/System/Handlers/JwtHandler.cs:15-20]。JWT 载荷中包含 `UserId` 与 `SessionId` 两个关键 Claim，前者标识用户身份，后者用于Session级校验。

System/Handlers/JwtHandler.cs:15-20]。JWT 载荷中包含 `UserId` 与 `SessionId` 两个关键 Claim，前者标识用户身份，后者用于Session级校验。

`JwtHandler` 继承 Furion 框架的 `AppAuthorizeHandler`，在 `HandleAsync` 方法中执行双重校验 [API/System/Handlers/JwtHandler.cs:22-30]：首先调用 `JWTEncryption.AutoRefreshToken` 验证 Token 签名与有效期，随后从 `App.User` 中提取 `UserId` 与 `SessionId`，若任一缺失则抛出 `ExceptionCodes.UnAuthToken` (100000)。Token 通过后还需校验 Session 有效性——系统以 `CacheConst.UserSessionCacheKey.Format(userId)` 为键，从 `IMemoryCache` 中读取该用户当前活跃的 SessionId 列表，确认请求携带的 SessionId 在列表中。若缓存未命中，则回源到 PostgreSQL 的 `UserSession` 分表查询，并通过 `ConcurrentDictionary<string, SemaphoreSlim>` 实现按用户维度的锁，防止缓存击穿 [API/System/Handlers/JwtHandler.cs:35-50]。

urrentDictionary<string, SemaphoreSlim>` 实现按用户维度的锁，防止缓存击穿 [API/System/Handlers/JwtHandler.cs:35-50]。

**API Key 认证通道**面向服务端程序化调用。客户端需在 `Authorization` 头中携带 `Basic base64(apiKeyId:apiKeySecret)`。`AgentInsightTransformLogic.ParseBasicAuth` 负责解析该头部 [API/System/Handlers/AgentInsightTransformLogic.cs:20-30]：从 `Basic ` 前缀后提取 Base64 编码串，解码后按 `:` 分割为 `PublicKey` 与 `SecretKey`。随后 `HandleBasicAuthRequest` 调用 `ResolveApiKeyWithCache` 从缓存或数据库加载 API Key 实体，并通过 `ValidateApiKey` 比对 `PublicKey` 与 `SecretKey` 是否完全匹配 [API/System/Handlers/AgentInsightTransformLogic.cs:45-52]。API Key 支持 `PROJECT` 与 `ORGANIZATION` 两种 Scope，分别限定在项目级或组织级范围内执行操作。

**登录入口**位于 `UserController.Login`，支持五种登录方式（`logintype`: 1=密码, 2=短信, 3=微信, 4=小程序, 5=APIKey），其中 `logintype=5` 时请求体可为空，认证信息完全依赖 `Authorization` 头中的 Basic 凭证 [API/Controllers/UserManagement/UserController.cs:73-80]。登录成功后响应头包含 `access-token`，响应体返回用户信息及 `sessionid`。

### 3.2. 授权流程

授权流程在认证通过后执行，核心目标是确保用户或 API Key 只能访问其Privilege范围内的资源。AgentInsightService 采用 **Role Privilege模型**，定义于 `Models/Common/Enums/UserEnum.cs`，包含五个等级：`NONE`、`VIEWER`、`MEMBER`、`ADMIN`、`OWNER`。OrganizationProject两个层级，形成二维Privilege矩阵。

**Privilege判定链路**贯穿请求处理全流程：

1. **Transform 层（认证后立即执行）**：API Key 认证通过后，若该 Key 关联了 `UserId`，系统调用 `IUserService.GetCurrentOrgPrivilege(apiKey.OrgId!)` 获取当前组织Privilege，检查 `HasExceedRateLimit` 标志，若超出月度配额则返回限流响应 [API/System/Handlers/AgentInsightTransformProvider.cs:70-80]。

2. **Controller 层（用户上下文注入）**：所有业务 Controller 继承 `ApiControllerBase`，其 `InitializeUserAsync` 方法在请求进入时被调用，通过 `GetUserAsync` 从缓存（`CacheConst.UserCacheKey.Format(UserId)`）或 `IUserService.GetCacheUserByUserId` 加载完整用户对象，并注入到当前请求上下文 [API/Controllers/ApiControllerBase.cs:20-30]。若用户不存在则抛出 `ExceptionCodes.InvalidUser` (100005)。

前请求上下文 [API/Controllers/ApiControllerBase.cs:20-30]。若用户不存在则抛出 `ExceptionCodes.InvalidUser` (100005)。

3. **Handler 层（业务级Privilege校验）**：业务 Handler 继承 `ApiHandlerBase`，该基类封装了Privilege校验与审计日志逻辑 [API/Handlers/ApiHandlerBase.cs:10-30]。以组织管理为例，`OrganizationHandler` 在执行更新/删除操作前，会校验当前用户的 Role 是否达到 `ADMIN` 或 `OWNER` 级别，否则抛出 `ExceptionCodes.UnauthorizedOrganizationAccess` (130009)。项目级操作同理，`ProjectHandler` 校验 `UnauthorizedProjectAccess` (140008)。

**角色分配与邀请流程**通过 `UserController` 的 `AssignRole` 与 `Invite` 端点实现 [API/Controllers/UserManagement/UserController.cs:147-162]。角色分配受严格约束：`CannotGrantHigherRole` (100023) 禁止授予高于自身等级的角色，`OwnerCannotModifySelfRole` (100039) 禁止 OWNER 修改自身角色。邀请成员时，系统校验 `UserAlreadyOrgMember` (100024) 与 `InviteAlreadyExists` (100025)，防止重复加入或重复邀请。

**Privilege校验的典型场景**如下表所示：

| 操作 | 所需最低角色 | 失败错误码 |
|------|------------|-----------|
| 查看组织信息 | VIEWER | `UnauthorizedOrganizationAccess` (130009) |
| 创建项目 | MEMBER | `UnauthorizedOrganizationAccess` (130009) |
| 更新项目Config | ADMIN | `UnauthorizedProjectAccess` (140008) |
| 删除组织 | OWNER | `UnauthorizedOrganizationAccess` (130009) |
| 分配角色 | ADMIN | `CannotGrantHigherRole` (100023) |

### 3.3. Token 管理

Token 管理覆盖 JWT 与 API Key 的完整生命周期，包括签发、存储、刷新、吊销与轮换。

**JWT Token 生命周期**：

- **签发**：用户登录成功后，系统通过 Furion 的 `JWTEncryption` 生成 JWT，签名算法为 HS256，有效期为 43200 秒（12 小时）。Token 中嵌入 `UserId` 与 `SessionId` Claims，同时响应头返回 `access-token` [API/Controllers/UserManagement/UserController.cs:73-80]。
- **Session持久化**：每次登录创建一条 `UserSession` 记录，持久化到 PostgreSQL 的 `UserSession` 分表（`SplitTable(t => t.Take(2))`），同时将 SessionId 写入 Redis 缓存（键为 `CacheConst.UserSessionCacheKey.Format(userId)`），缓存过期时间由 `CacheConst.UserSessionExpiredHours.WithJitterHours()` 决定，引入抖动防止缓存雪崩 [API/System/Handlers/JwtHandler.cs:40-55]。
- **多端登录限制**：同一用户可拥有多个活跃 Session，但每个 Session 独立记录。登出时调用 `UserController.Logout`，由 `UserHandler.Logout` 将对应 `UserSession` 的 `LogoutTime` 置为当前时间，并从缓存中移除该 SessionId [API/Controllers/UserManagement/UserController.cs:88-92]。
- **自动刷新**：`JWTEncryption.AutoRefreshToken` 在 Token 即将过期时自动签发新 Token，实现无感续期 [API/System/Handlers/JwtHandler.cs:28-30]。

**API Key 生命周期**：

- **创建**：用户通过 `POST /api/user/apikey` 创建 API Key [API/Controllers/UserManagement/UserController.cs:209-215]，系统生成 `PublicKey` 与 `SecretKey` 对，支持指定 `PROJECT` 或 `ORGANIZATION` Scope。创建失败时抛出 `CreateApiKeyFailed` (100032)。
- **存储与检索**：API Key 的 `SecretKey` 以加密形式存储，查询时通过 `ResolveApiKeyWithCache` 加载，并使用 `ConcurrentDictionary<string, SemaphoreSlim>` 防止缓存击穿 [API/System/Handlers/AgentInsightTransformProvider.cs:85-95]。
- **校验**：每次请求时，`ValidateApiKey` 比对 `PublicKey` 与 `SecretKey` 的明文值，任一不匹配即返回 `InvalidApiKey` (100038) [API/System/Handlers/AgentInsightTransformLogic.cs:45-52]。
- **吊销**：用户通过 `POST /api/user/apikey/delete` 删除 API Key [API/Controllers/UserManagement/UserController.cs:272-278]，删除后该 Key 立即失效，后续携带该 Key 的请求将返回 `ApiKeyNotFound` (100031)。
- **限流关联**：API Key 关联的 `UserId` 对应的组织 Privilege 若 `HasExceedRateLimit` 为 true，则所有使用该 Key 的请求被限流，返回 `AgentInsightConst.DefaultMonthlyRate` 对应的限流响应 [API/System/Handlers/AgentInsightTransformProvider.cs:70-80]。

**Token 安全最佳实践**：

| 实践项 | 说明 |
|--------|------|
| 传输安全 | 所有认证信息通过 HTTPS 传输，禁止明文传递 |
| 密钥管理 | `JWT_SIGNING_KEY` 通过环境变量注入，禁止硬编码 |
| 最小Privilege | API Key 按需分配 `PROJECT` 或 `ORGANIZATION` Scope，避免过度授权 |
| 定期轮换 | 建议定期更换 API Key，降低泄露风险 |
| Session隔离 | 每个登录Session独立 SessionId，登出后立即失效 |

---

## 4. AgentConfigController 接口

本章共覆盖 3 个 HTTP 端点，每个端点一个接口卡片。

### 4.1. API-028 AgentConfigController.Get (GET /api/agent/config)

- **鉴权**: 无（代码中未标注 `[Authorize]` 特性）
- **描述**: 获取 Agent Config信息。该方法由 `AgentConfigController` Controller处理，用于查询当前 Agent 的Config详情。
- **请求参数**: 无（该方法不接受任何查询参数、路径参数或请求体）

- **响应格式**:

| 字段 | 类型 | 说明 |
|------|------|------|
| code | int | 状态码，`0` 表示成功，非 `0` 表示失败 |
| message | string | 响应消息，成功时为 `"ok"`，失败时为错误描述 |
| data | object | Agent Config数据对象 |
| data.id | string | Agent Config唯一标识 |
| data.name | string | Agent 名称 |
| data.description | string | Agent 描述 |
| data.type | int | Agent 类型 |
| data.model | string | 使用的模型名称 |
| data.temperature | number | 温度参数（采样温度） |
| data.maxTokens | int | 最大 Token 数 |
| data.systemPrompt | string | 系统提示词 |
| data.createdAt | string | 创建时间（ISO 8601 格式） |
| data.updatedAt | string | 更新时间（ISO 8601 格式） |

- **错误码**:

| errorCode | message | 说明 |
|-----------|---------|------|
| 100000 | UnAuthToken | Token 未认证或已过期 |
| 150022 | AgentConfigNotFound | 未找到对应的 Agent Config |
| 150004 | AgentSettingNotConfig | Agent 设置未Config |
| 999999 | DefaultException | 服务器内部错误 |

- **请求示例**:
```http
GET /api/agent/config HTTP/1.1
Host: localhost
```

- **响应示例**:

**成功响应 (HTTP 200)**:
```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "id": "cfg_8f3a2b9c1d4e",
    "name": "Research Assistant",
    "description": "用于研究分析的 Agent 实例",
    "type": 2,
    "model": "gpt-4o",
    "temperature": 0.7,
    "maxTokens": 4096,
    "systemPrompt": "你是一个专业的研究助手，请基于提供的信息给出详细分析。",
    "createdAt": "2025-01-15T08:30:00Z",
    "updatedAt": "2025-02-20T14:22:10Z"
  }
}
```

**失败响应 - Config不存在 (HTTP 200)**:
```json
{
  "code": 150022,
  "message": "AgentConfigNotFound",
  "data": null
}
```

**失败响应 - 未认证 (HTTP 401)**:
```json
{
  "code": 100000,
  "message": "UnAuthToken",
  "data": null
}
```

### 4.2. API-040 AgentConfigController.Delete (GET /api/agent/config/delete)

- **鉴权**: 无
- **描述**: 删除指定的 Agent Config。该接口通过 GET 请求执行删除操作，根据请求中携带的Config ID 删除对应的 Agent Config记录。

- **请求参数**: 

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | string | 是 | Agent Config的唯一标识符（从 Query String 中获取） |

- **响应格式**: 

| 字段 | 类型 | 说明 |
|------|------|------|
| code | int | 状态码，0 表示成功，非 0 表示失败 |
| message | string | 状态描述信息 |
| data | object | 响应数据，删除成功时通常为 null |

- **错误码**: 

| errorCode | message | 说明 |
|-----------|---------|------|
| 150022 | AgentConfigNotFound | 未找到指定的 Agent Config，无法执行删除操作 |
| 150004 | AgentSettingNotConfig | Agent 设置未Config，无法执行删除操作 |
| 100000 | UnAuthToken | Token 验证失败，用户未认证 |
| 999999 | DefaultException | 服务器内部错误，删除过程中发生未预期异常 |

- **请求示例**: 

```http
GET /api/agent/config/delete?id=config_8f7d2c9e5a1b4d6f HTTP/1.1
Host: localhost
```

- **响应示例**: 

**成功响应:**
```json
{
  "code": 0,
  "message": "删除成功",
  "data": null
}
```

**失败响应 (AgentConfigNotFound):**
```json
{
  "code": 150022,
  "message": "Agent Config不存在",
  "data": null
}
```

### 4.3. API-xxx（按Controller重新编号） AgentConfigController.Post (POST /api/agent/config)

- **鉴权**: 无
- **描述**: 创建或更新 Agent Config信息。该方法接收请求体中的原始字符串内容，用于提交 Agent Config数据。

- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| body | string | 是 | Agent Config的 JSON 字符串内容，包含 Agent 的详细Config信息 |

- **响应格式**:

| 字段 | 类型 | 说明 |
|------|------|------|
| code | int | 状态码，200 表示成功 |
| message | string | 响应消息 |
| data | object | 响应数据，包含操作结果 |
| data.configId | string | Config ID |
| data.status | string | Config状态 |

- **错误码**:

| errorCode | message | 说明 |
|-----------|---------|------|
| 150004 | AgentSettingNotConfig | Agent Config未设置 |
| 150007 | AgentLimitExceeded | Agent 数量超出限制 |
| 150008 | DuplicateUserConfig | 用户Config重复 |
| 150022 | AgentConfigNotFound | Agent Config不存在 |
| 990001 | EncryptionFailed | 加密失败 |
| 990002 | DecryptionFailed | 解密失败 |
| 999999 | DefaultException | 默认异常 |

- **请求示例**:

```json
{
  "body": "{\"agentName\":\"测试Agent\",\"agentType\":1,\"modelConfig\":{\"modelName\":\"gpt-4\",\"temperature\":0.7},\"promptTemplate\":\"你是一个智能助手\",\"maxTokens\":2048}"
}
```

- **响应示例**:

**成功响应**:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "configId": "cfg_8f7e2d9a1b3c",
    "status": "created"
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

本章覆盖 3 个 HTTP 端点，每个端点一个接口卡片。

### 5.1. API-035 GetAgentReportTemplates (GET /api/agent/report)

- **鉴权**: 无
- **描述**: 获取 Agent 报告模板列表，支持按 ID 查询、筛选预定义模板，并支持分页。

- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| id | string | 否 | Agent 报告模板的唯一标识符。 |
| include_predefined | bool | 否 | 是否包含预定义模板，默认 `false`。 |
| include_predefinedonly | bool | 否 | 是否仅包含预定义模板，默认 `false`。 |
| page | int | 否 | 页码。 |
| page_size | int | 否 | 每页条数。 |

- **响应格式**:

| 字段 | 类型 | 说明 |
|---|---|---|
| id | string | Agent 报告模板的唯一标识符。 |
| name | string | Agent 报告模板名称。 |
| description | string | Agent 报告模板描述。 |
| isPredefined | bool | 是否为预定义模板。 |
| createdAt | datetime | 模板创建时间。 |
| updatedAt | datetime | 模板更新时间。 |
| totalCount | int | 符合条件的模板总数。 |
| page | int | 当前页码。 |
| page_size | int | 当前页条数。 |

- **错误码**:

| errorCode | message | 说明 |
|---|---|---|
| 150023 | AgentReportTemplateNotFound | 未找到指定的 Agent 报告模板。 |
| 100000 | UnAuthToken | 未认证或 Token 无效。 |
| 999999 | DefaultException | 默认异常，未预期的错误。 |

- **请求示例**:

```json
{
  "id": "template_001",
  "include_predefined": true,
  "include_predefinedonly": false,
  "page": 1,
  "page_size": 20
}
```

- **响应示例**:

**成功响应**:

```json
{
  "id": "template_001",
  "name": "Weekly Agent Performance Report",
  "description": "A predefined template for weekly agent performance analysis.",
  "isPredefined": true,
  "createdAt": "2024-05-20T10:00:00Z",
  "updatedAt": "2024-05-20T10:00:00Z",
  "totalCount": 1,
  "page": 1,
  "page_size": 20
}
```

**失败响应**:

```json
{
  "errorCode": 150023,
  "message": "AgentReportTemplateNotFound",
  "details": "The specified agent report template was not found."
}
```

### 5.2. API-048 DeleteTemplates (GET /api/agent/report/delete)

- **鉴权**: 无
- **描述**: 根据传入的模板 ID 列表删除 Agent 报告模板。

- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| ids | string | 否 | 待删除的 Agent 报告模板 ID 列表，多个 ID 以逗号分隔。若为空或 null，则不执行删除操作。 |

- **响应格式**:

| 字段 | 类型 | 说明 |
|------|------|------|
| code | int | 状态码，200 表示成功 |
| message | string | 状态描述信息 |
| data | object | 响应数据，删除成功时返回 null |
| traceId | string | 请求Trace ID，用于日志排查 |

- **错误码**:

| errorCode | message | 说明 |
|-----------|---------|------|
| 150023 | AgentReportTemplateNotFound | 指定的 Agent 报告模板不存在 |
| 150024 | EmptyAgentReportTemplateName | Agent 报告模板名称为空 |
| 999999 | DefaultException | 服务器内部异常 |

- **请求示例**:

```json
GET /api/agent/report/delete?ids=1001,1002,1003
```

- **响应示例**:

**成功响应:**

```json
{
  "code": 200,
  "message": "success",
  "data": null,
  "traceId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

**失败响应 (模板不存在):**

```json
{
  "code": 150023,
  "message": "AgentReportTemplateNotFound",
  "data": null,
  "traceId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

### 5.3. API-xxx（按Controller重新编号） CreateOrUpdateTemplate (POST /api/agent/report)

- **鉴权**: 无
- **描述**: 创建或更新 Agent 报告模板。根据请求体中的模板名称判断是新增还是更新操作，并持久化到数据库。

- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `name` | string | 是 | 模板名称，用于标识模板，创建时不可与已有模板重名 |
| `content` | string | 是 | 模板内容，支持 Markdown 格式 |
| `description` | string | 否 | 模板描述信息 |
| `isDefault` | boolean | 否 | 是否设为默认模板，默认 `false` |
| `projectId` | long | 否 | 关联的 Project ID，为空时表示全局模板 |
| `organizationId` | long | 否 | 关联的 Organization ID，为空时表示全局模板 |

- **响应格式**:

| 字段 | 类型 | 说明 |
|---|---|---|
| `code` | int | 业务状态码，`0` 表示成功，非 `0` 表示失败 |
| `message` | string | 状态描述信息 |
| `data` | object | 响应数据，成功时返回模板 ID |

- **错误码**:

| errorCode | message | 说明 |
|---|---|---|
| `100000` | UnAuthToken | Token 无效或未提供 |
| `150000` | EmptyProjectId | Project ID 为空 |
| `150022` | AgentConfigNotFound | Agent Config不存在 |
| `150023` | AgentReportTemplateNotFound | 模板不存在（更新时） |
| `150024` | EmptyAgentReportTemplateName | 模板名称为空 |
| `999999` | DefaultException | 服务器内部错误 |

- **请求示例**:

```json
{
  "name": "每日报告模板",
  "content": "# 每日 Agent 运行报告\n## 摘要\n...",
  "description": "用于生成每日运行摘要",
  "isDefault": true,
  "projectId": 1001,
  "organizationId": 2001
}
```

- **响应示例**:

**成功响应**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 12345
  }
}
```

**失败响应** (模板名称已存在):
```json
{
  "code": 150024,
  "message": "EmptyAgentReportTemplateName",
  "data": null
}
```

---

## 6. AgentSessionController 接口

本章共覆盖 3 个 HTTP 端点，每个端点一个接口卡片。

### 6.1. API-021 获取 Agent Session 列表 (GET /api/agent/session)

- **鉴权**: 需要 JWT JWT Bearer Token Token（Controller类标记 `[Authorize]`，从 `JWTSettings` Config中验证签名、颁发者、受众及有效期）
- **描述**: 根据可选的 Session ID 分页查询 Agent Session 列表，用于检索历史Session记录。若未提供 `id`，则返回当前用户所有 Session 的分页列表；若提供 `id`，则返回该 Session 详情。
- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | string | 否 | Agent Session 的唯一标识符。若提供，则返回该 Session 详情；若为空，则返回分页列表。 |
| `page` | int | 否 | 页码，从 1 开始。默认值为 `AgentInsightConst.DefaultPage`（通常为 1）。 |
| `page_size` | int | 否 | 每页记录数。默认值为 `AgentInsightConst.DefaultPageSize`（通常为 20）。 |

- **响应格式**: 标准 `ApiResponse<T>` 包装结构

| 字段 | 类型 | 说明 |
|------|------|------|
| `code` | int | 业务状态码。`0` 表示成功，非 `0` 表示失败（见错误码表）。 |
| `message` | string | 状态描述信息。成功时为 `"success"`，失败时为具体错误信息。 |
| `data` | object | 响应数据。成功时包含分页结果或 Session 详情；失败时为 `null`。 |
| `data.items` | array | Session 列表（分页查询时返回）。 |
| `data.items[].id` | string | Session 唯一标识符。 |
| `data.items[].name` | string | Session 名称。 |
| `data.items[].projectId` | string | 所属 Project 的 ID。 |
| `data.items[].userId` | string | 创建该 Session 的用户 ID。 |
| `data.items[].createdAt` | datetime | Session UTC。 |
| `data.items[].updatedAt` | datetime | Session UTC。 |
| `data.total` | int | 符合条件的总记录数（分页查询时返回）。 |
| `data.page` | int | 当前页码（分页查询时返回）。 |
| `data.page_size` | int | 每页记录数（分页查询时返回）。 |

- **错误码**:

| errorCode | message | 说明 |
|-----------|---------|------|
| `0` | success | 请求成功 |
| `100000` | UnAuthToken | 未提供或提供了无效的认证 Token |
| `150021` | AgentSessionNotFound | 指定的 `id` 对应的 Agent Session 不存在 |
| `150000` | EmptyProjectId | 未提供 Project ID 或 Project ID 为空（当 Session 未关联用户时） |
| `999999` | DefaultException | 服务器内部错误，请稍后重试 |

- **请求示例**:

```json
{
  "id": "session_8f7d2c1a9e4b6f3d",
  "page": 1,
  "page_size": 20
}
```

- **响应示例**:

**成功响应 (HTTP 200)**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "id": "session_8f7d2c1a9e4b6f3d",
        "name": "Research on LangChain",
        "projectId": "proj_3e5a8b2c7d1f4e9a",
        "userId": "user_1a2b3c4d5e6f7a8b",
        "createdAt": "2025-01-15T10:30:00Z",
        "updatedAt": "2025-01-15T11:45:00Z"
      },
      {
        "id": "session_2b8e4f6a1c3d5e7f",
        "name": "Code Review Assistant",
        "projectId": "proj_3e5a8b2c7d1f4e9a",
        "userId": "user_1a2b3c4d5e6f7a8b",
        "createdAt": "2025-01-14T08:20:00Z",
        "updatedAt": "2025-01-14T09:10:00Z"
      }
    ],
    "total": 2,
    "page": 1,
    "page_size": 20
  }
}
```

**失败响应 (HTTP 401 - 未认证)**:
```json
{
  "code": 100000,
  "message": "UnAuthToken",
  "data": null
}
```

**失败响应 (HTTP 404 - Session 不存在)**:
```json
{
  "code": 150021,
  "message": "AgentSessionNotFound",
  "data": null
}
```

### 6.2. API-021 AgentSession Delete (GET /api/agent/session/delete)

- **鉴权**: 需要 JWT JWT Bearer Token Token（通过 `[Authorize]` 注解保护，使用 `JWTSettings` Config的 HS256 算法验证）
- **描述**: 根据提供的 Session ID 列表删除对应的 Agent Session 记录。支持批量删除，多个 ID 使用逗号分隔。

- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| ids | string | 是 | 待删除的 Agent Session ID 列表，多个 ID 使用英文逗号 `,` 分隔。例如：`"session-id-1,session-id-2"` |

- **响应格式**:

| 字段 | 类型 | 说明 |
|------|------|------|
| code | int | 业务状态码，`0` 表示成功，非 `0` 表示失败 |
| message | string | 状态描述信息 |
| data | object | 响应数据，成功时为 `null`，失败时可能包含错误详情 |
| traceId | string | 请求Trace ID，用于链路Trace和日志排查 |

- **错误码**:

| errorCode | message | 说明 |
|-----------|---------|------|
| 0 | Success | 删除成功 |
| 100000 | UnAuthToken | Token 无效或已过期，需要重新获取有效的 JWT Token |
| 150021 | AgentSessionNotFound | 指定的 Agent Session 不存在或已被删除 |
| 999999 | DefaultException | 服务器内部错误，请稍后重试或联系技术支持 |

- **请求示例**:

```http
GET /api/agent/session/delete?ids=session-id-1,session-id-2,session-id-3 HTTP/1.1
Host: localhost
Authorization: JWT Bearer Token {JWT_TOKEN}
```

- **响应示例**:

**成功响应**:
```json
{
  "code": 0,
  "message": "Success",
  "data": null,
  "traceId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

**失败响应** (Agent Session 不存在):
```json
{
  "code": 150021,
  "message": "AgentSessionNotFound",
  "data": null,
  "traceId": "b2c3d4e5-f6a7-8901-bcde-f23456789012"
}
```

### 6.3. API-021 AgentSessionController.Post (POST /api/agent/session)

- **鉴权**: 需要 JWT 认证（Controller类 `AgentSessionController` 标注 `[Authorize]`，`JWTSettings` Config HS256 算法，Token 有效期 43200 分钟）
- **描述**: 创建新的 Agent Session，用于启动一个 Agent Session并获取Session ID
- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| projectId | long | 是 | Project ID，标识 Session 所属项目 |
| agentConfigId | long | 是 | Agent Config ID，指定使用的 Agent Config |
| input | string | 是 | 用户输入内容，作为 Agent Session的初始输入 |
| metadata | object | 否 | 附加元数据，可用于传递上下文信息 |

- **响应格式**:

| 字段 | 类型 | 说明 |
|------|------|------|
| code | int | 状态码，0 表示成功，非 0 表示失败 |
| message | string | 状态描述信息 |
| data | object | 响应数据 |
| data.sessionId | string | 创建的 Session ID |
| data.traceId | string | 当前Session的 Trace ID，用于Trace |

- **错误码**:

| errorCode | message | 说明 |
|-----------|---------|------|
| 100000 | UnAuthToken | Token 无效或未提供 |
| 150000 | EmptyProjectId | projectId 为空 |
| 150004 | AgentSettingNotConfig | Agent Config不存在 |
| 150007 | AgentLimitExceeded | 超出 Agent 数量限制 |
| 150021 | AgentSessionNotFound | Agent Session 不存在或创建失败 |
| 150022 | AgentConfigNotFound | 指定的 Agent Config不存在 |
| 999999 | DefaultException | 系统默认异常 |

- **请求示例**:
```json
{
  "projectId": 1001,
  "agentConfigId": 2001,
  "input": "请分析最近一周的异常日志",
  "metadata": {
    "source": "web",
    "priority": "high"
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
    "sessionId": "sess_8f7e2d9c4a1b",
    "traceId": "trace_3b6e9f2a8c1d"
  }
}
```

**失败响应**:
```json
{
  "code": 150022,
  "message": "AgentConfigNotFound",
  "data": null
}
```

---

## 7. MetricsController, ModelController 接口

本章覆盖 5 个 HTTP 端点，每个端点一个接口卡片。

### 7.1. API-034 GetObservations (GET /api/data/metrics/observations)

- **鉴权**: 无（代码中未标注 `[Authorize]` 特性）
- **描述**: 分页查询 Observation 列表，支持按 Trace 标识过滤。该接口用于检索 AgentInsightService 中采集的Observation数据，可按 `id`（Trace ID）筛选，并支持分页控制返回结果集大小。

- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | string | 是 | Trace 标识符，用于筛选特定 Trace 下的所有 Observation 记录 |
| `page` | int | 否 | 页码，从 1 开始 |
| `pagesize` | int | 否 | 每页记录数 |

- **响应格式**:

| 字段 | 类型 | 说明 |
|------|------|------|
| `code` | int | 状态码，`0` 表示成功，非 `0` 表示失败（对应错误码清单） |
| `data` | object | 响应数据，包含分页结果 |
| `data.items` | array | Observation 记录列表，每个元素包含Observation数据详情 |
| `data.total` | int | 符合条件的总记录数 |
| `data.page` | int | 当前页码 |
| `data.pagesize` | int | 当前每页记录数 |
| `message` | string | 响应消息，成功时为 `"success"`，失败时为具体错误描述 |

- **错误码**:

| errorCode | message | 说明 |
|-----------|---------|------|
| `100000` | UnAuthToken | 未认证的 Token，请求未携带有效身份凭证 |
| `150009` | EmptyTraceIds | Trace ID 列表为空，`id` 参数未提供或为空字符串 |
| `150010` | ClickHouseQueryError | ClickHouse 查询失败，查询语句执行出错 |
| `150017` | ClickHouseQueryTimeout | ClickHouse 查询超时 |
| `150018` | EmptyTraceId | Trace ID 为空，`id` 参数未提供或为空字符串 |
| `999999` | DefaultException | 默认异常，未预期的服务器内部错误 |

- **请求示例**:

```json
{
  "id": "trace_8f7d3a2b9c1e4f5a6b7c8d9e0f1a2b3c",
  "page": 1,
  "pagesize": 20
}
```

- **响应示例**:

**成功响应**:
```json
{
  "code": 0,
  "data": {
    "items": [
      {
        "id": "obs_001",
        "traceId": "trace_8f7d3a2b9c1e4f5a6b7c8d9e0f1a2b3c",
        "sessionId": "session_abc123",
        "timestamp": "2025-01-15T10:30:00Z",
        "level": "info",
        "message": "Agent execution started",
        "metadata": {
          "agentId": "agent_001",
          "model": "gpt-4o"
        }
      }
    ],
    "total": 1,
    "page": 1,
    "pagesize": 20
  },
  "message": "success"
}
```

**失败响应** (Trace ID 为空):
```json
{
  "code": 150018,
  "data": null,
  "message": "EmptyTraceId"
}
```

### 7.2. API-050 GetScores (GET /api/data/metrics/scores)

- **鉴权**: 需要 JWT 认证（`[Authorize]`），使用 HS256 算法验证 Token，`ValidIssuer` 和 `ValidAudience` 分别从 `${JWT_ISSUER}` 和 `${JWT_AUDIENCE}` 读取。
- **描述**: 根据指定的 Trace ID 分页查询 Agent 的 Score 数据列表。
- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `id` | string | 是 | Trace ID，用于定位具体的 Trace 记录 |
| `page` | int | 否 | 页码 |
| `pagesize` | int | 否 | 每页条数 |

- **响应格式**:

| 字段 | 类型 | 说明 |
|---|---|---|
| `code` | int | 业务状态码，`0` 表示成功，非 `0` 表示失败 |
| `message` | string | 状态描述信息 |
| `data` | object | 响应数据 |
| `data.items` | array | Score 数据列表 |
| `data.items[].name` | string | Score 名称 |
| `data.items[].score` | number | Score 数值 |
| `data.items[].timestamp` | string | Score 记录时间戳 |
| `data.total` | int | 符合条件的总记录数 |
| `data.page` | int | 当前页码 |
| `data.pagesize` | int | 当前每页条数 |

- **错误码**:

| errorCode | message | 说明 |
|---|---|---|
| `100000` | UnAuthToken | 认证 Token 无效或已过期 |
| `150000` | EmptyProjectId | Project ID 为空 |
| `150009` | EmptyTraceIds | Trace ID 列表为空 |
| `150010` | ClickHouseQueryError | ClickHouse 查询失败 |
| `150011` | TooManyTraceIds | Trace ID 数量超出限制 |
| `150017` | ClickHouseQueryTimeout | ClickHouse 查询超时 |
| `150018` | EmptyTraceId | Trace ID 为空 |
| `999999` | DefaultException | 系统默认异常 |

- **请求示例**:

```json
{
  "id": "trace_8a5f3c9e2b7d4f6a",
  "page": 1,
  "pagesize": 20
}
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
        "name": "relevance_score",
        "score": 0.95,
        "timestamp": "2025-01-15T10:30:00Z"
      },
      {
        "name": "accuracy_score",
        "score": 0.87,
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
  "code": 150018,
  "message": "EmptyTraceId",
  "data": null
}
```

### 7.3. API-xxx（按Controller重新编号） GetTraces (GET /api/data/metrics/traces)

- **鉴权**: 需要 JWT JWT Bearer Token Token（`[Authorize]`），使用 HS256 算法，`ValidIssuer` 和 `ValidAudience` 来自 `${JWT_ISSUER}` 和 `${JWT_AUDIENCE}` 环境变量。
- **描述**: 根据 Trace ID 列表查询 Trace 详情数据。该接口从 ClickHouse 中检索指定 ID 的 Trace 及其关联的 Span、Observation、Score、Token 用量和成本数据，用于 Metrics 监控和Trace分析。

- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| ids | string | 是 | 逗号分隔的 Trace ID 列表，用于指定要查询的 Trace。每个 ID 应为有效的 Trace 标识符。 |

- **响应格式**:

| 字段 | 类型 | 说明 |
|------|------|------|
| traceId | string | Trace 的唯一标识符 |
| timestamp | datetime | Trace 的开始时间戳 |
| name | string | Trace 的名称 |
| input | object | Trace 的输入数据 |
| output | object | Trace 的输出数据 |
| metadata | object | Trace 的元数据信息 |
| sessionId | string | 关联的 Session ID |
| userId | string | 关联的用户 ID |
| version | string | Trace 的版本号 |
| release | string | 发布版本标识 |
| environment | string | 环境标识（如 DEVELOPMENT、STAGING、PRODUCTION） |
| tags | string[] | Trace 的标签列表 |
| public | boolean | 是否为公开 Trace |
| bookmarked | boolean | 是否被标记收藏 |
| latency | number | Trace 的总延迟（毫秒） |
| totalCost | number | Trace 的总成本 |
| observations | object[] | 关联的 Observation 列表，包含 Span 和 Event 数据 |
| scores | object[] | 关联的 Score Score列表 |
| totalTokens | number | Token 总用量 |
| inputTokens | number | 输入 Token 数量 |
| outputTokens | number | 输出 Token 数量 |
| level | string | 日志级别 |
| warningCount | number | 警告数量 |
| errorCount | number | 错误数量 |
| modelNames | string[] | 使用的模型名称列表 |

- **错误码**:

| errorCode | message | 说明 |
|-----------|---------|------|
| 150009 | EmptyTraceIds | Trace ID 列表为空，未提供任何 ID |
| 150011 | TooManyTraceIds | Trace ID 数量超出限制，单次查询过多 |
| 150010 | ClickHouseQueryError | ClickHouse 查询执行失败，数据检索出错 |
| 150017 | ClickHouseQueryTimeout | ClickHouse 查询超时，超过 60 秒未返回结果 |
| 150018 | EmptyTraceId | 单个 Trace ID 为空或无效 |
| 100000 | UnAuthToken | Token 无效或已过期，需要重新认证 |
| 999999 | DefaultException | 服务器内部错误，未预期的异常 |

- **请求示例**:

```json
GET /api/data/metrics/traces?ids=trace_8a5f3c2e9b1d4f7a6c0e2b8d1a3f5c7e,trace_2b6d4f8a0c1e3g5h7i9j0k1l2m3n4o5p
Authorization: JWT Bearer Token eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c
```

- **响应示例**:

**成功响应 (200 OK)**:

```json
{
  "code": 0,
  "message": "success",
  "data": [
    {
      "traceId": "trace_8a5f3c2e9b1d4f7a6c0e2b8d1a3f5c7e",
      "timestamp": "2024-01-15T10:30:00Z",
      "name": "AgentInsightService-Trace-001",
      "input": {
        "query": "分析用户行为数据",
        "context": { "userId": "user_12345", "sessionId": "session_67890" }
      },
      "output": {
        "response": "已完成用户行为分析",
        "status": "success"
      },
      "metadata": {
        "source": "api",
        "traceType": "agent"
      },
      "sessionId": "session_67890",
      "userId": "user_12345",
      "version": "1.0.0",
      "release": "v1.2.3",
      "environment": "PRODUCTION",
      "tags": ["production", "user-analysis"],
      "public": false,
      "bookmarked": true,
      "latency": 1250,
      "totalCost": 0.0025,
      "observations": [
        {
          "id": "span_001",
          "type": "SPAN",
          "name": "Agent-Processing",
          "startTime": "2024-01-15T10:30:00.100Z",
          "endTime": "2024-01-15T10:30:01.200Z",
          "latency": 1100,
          "input": { "action": "process" },
          "output": { "result": "completed" },
          "metadata": { "model": "gpt-4" }
        }
      ],
      "scores": [
        {
          "name": "accuracy",
          "value": 0.95,
          "comment": "高准确率"
        }
      ],
      "totalTokens": 1500,
      "inputTokens": 800,
      "outputTokens": 700,
      "level": "DEFAULT",
      "warningCount": 1,
      "errorCount": 0,
      "modelNames": ["gpt-4", "text-embedding-3-small"]
    }
  ]
}
```

**失败响应 (400 Bad Request)**:

```json
{
  "code": 150009,
  "message": "EmptyTraceIds",
  "data": null,
  "traceId": "8f3a5c7e9b1d4f6a8c0e2b4d6f8a0c1e"
}
```

**失败响应 (401 Unauthorized)**:

```json
{
  "code": 100000,
  "message": "UnAuthToken",
  "data": null,
  "traceId": "2b6d4f8a0c1e3g5h7i9j0k1l2m3n4o5p"
}
```

### 7.4. API-024 GetTraces (POST /api/data/metrics/traces)

- **鉴权**: 需要 JWT JWT Bearer Token Token（Controller类 `MetricsController` 标注了 `[Authorize]`，使用 HS256 算法）
- **描述**: 根据 TraceMetricsBody 中的过滤条件、排序规则和分页参数，从 ClickHouse 查询 Trace 列表数据。
- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| projectId | string | 是 | Project ID，用于限定查询范围 |
| organizationId | string | 是 | Org ID，用于限定查询范围 |
| traceIds | string[] | 否 | 指定的 Trace ID 列表，用于精确筛选。若提供，则忽略其他过滤条件 |
| filter | object | 否 | 过滤条件容器 |
| filter.type | FilterType | 是 | 过滤字段的类型，取值见 FilterType 枚举（如 `DateTime = 1`、`String = 2`、`Number = 3` 等） |
| filter.column | FilterColumn | 是 | 过滤的字段名，取值见 FilterColumn 枚举（如 `Id = 1`、`Timestamp = 3`、`Latency = 11` 等） |
| filter.operator | FilterOperator | 是 | 过滤操作符，取值见 FilterOperator 枚举（如 `GreaterThan = 1`、`Contains = 6`、`AnyOf = 10` 等） |
| filter.value | object | 是 | 过滤值，类型需与 `filter.type` 匹配。对于 `ArrayOptions` 类型，应为数组 |
| orderBy | object | 否 | 排序规则 |
| orderBy.column | FilterColumn | 是 | 排序字段，取值见 FilterColumn 枚举 |
| orderBy.descending | boolean | 是 | 是否降序排序，`true` 为降序，`false` 为升序 |
| page | integer | 否 | 页码，从 1 开始，默认值为 1 |
| page_size | integer | 否 | 每页条数，默认值为 20，最大值为 100 |

- **响应格式**:

| 字段 | 类型 | 说明 |
|---|---|---|
| code | integer | 业务状态码，`0` 表示成功，非 `0` 表示失败 |
| message | string | 提示信息，成功时为 `"success"`，失败时为具体错误描述 |
| data | object | 响应数据 |
| data.items | array | Trace 列表 |
| data.items[].id | string | Trace ID |
| data.items[].name | string | Trace 名称 |
| data.items[].timestamp | string | Trace 时间戳（ISO 8601 格式） |
| data.items[].userId | string | 关联的用户 ID |
| data.items[].sessionId | string | 关联的 Session ID |
| data.items[].environment | string | 环境标识（如 `DEVELOPMENT`、`STAGING`、`PRODUCTION`） |
| data.items[].version | string | 版本号 |
| data.items[].release | string | 发布标识 |
| data.items[].tags | string[] | 标签列表 |
| data.items[].bookmarked | boolean | 是否被标记 |
| data.items[].latency | number | 延迟（毫秒） |
| data.items[].inputTokens | integer | 输入 Token 数 |
| data.items[].outputTokens | integer | 输出 Token 数 |
| data.items[].totalTokens | integer | 总 Token 数 |
| data.items[].inputCost | number | 输入成本 |
| data.items[].outputCost | number | 输出成本 |
| data.items[].totalCost | number | 总成本 |
| data.items[].level | string | 日志级别 |
| data.items[].warningCount | integer | 警告数量 |
| data.items[].errorCount | integer | 错误数量 |
| data.items[].defaultCount | integer | 默认级别数量 |
| data.items[].debugCount | integer | 调试级别数量 |
| data.items[].modelNames | string[] | 使用的模型名称列表 |
| data.items[].scoresAvg | number | 平均Score |
| data.total | integer | 符合条件的总记录数 |
| data.page | integer | 当前页码 |
| data.page_size | integer | 每页条数 |

- **错误码**:

| errorCode | message | 说明 |
|---|---|---|
| 100000 | UnAuthToken | 未提供或提供了无效的认证 Token |
| 150000 | EmptyProjectId | 请求中未提供 `projectId` |
| 150009 | EmptyTraceIds | 请求中 `traceIds` 数组为空 |
| 150010 | ClickHouseQueryError | ClickHouse 查询执行失败 |
| 150011 | TooManyTraceIds | 请求中 `traceIds` 数量超过系统限制 |
| 150012 | InvalidFilterType | `filter.type` 的值无效 |
| 150013 | InvalidFilterColumn | `filter.column` 的值无效 |
| 150014 | InvalidFilterOperator | `filter.operator` 的值无效 |
| 150015 | InvalidFilterValue | `filter.value` 的类型或格式与 `filter.type` 不匹配 |
| 150016 | InvalidOrderBy | `orderBy.column` 的值无效 |
| 150017 | ClickHouseQueryTimeout | ClickHouse 查询超时 |
| 150018 | EmptyTraceId | 请求中 `traceIds` 包含空的 Trace ID |
| 150019 | OrgAndProjectBothEmpty | `organizationId` 和 `projectId` 均为空 |
| 999999 | DefaultException | 服务器内部异常 |

- **请求示例**:

```json
{
  "projectId": "project_123456",
  "organizationId": "org_789012",
  "traceIds": null,
  "filter": {
    "type": 1,
    "column": 3,
    "operator": 1,
    "value": "2024-05-01T00:00:00Z"
  },
  "orderBy": {
    "column": 3,
    "descending": true
  },
  "page": 1,
  "page_size": 20
}
```

- **响应示例**:

**成功响应 (HTTP 200)**:

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "id": "trace_abcdef123456",
        "name": "Agent Run - Research",
        "timestamp": "2024-05-01T12:34:56Z",
        "userId": "user_001",
        "sessionId": "session_xyz",
        "environment": "PRODUCTION",
        "version": "1.2.3",
        "release": "release-2024.05",
        "tags": ["production", "research"],
        "bookmarked": false,
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
        "defaultCount": 10,
        "debugCount": 5,
        "modelNames": ["gpt-4o"],
        "scoresAvg": 0.95
      }
    ],
    "total": 1,
    "page": 1,
    "page_size": 20
  }
}
```

**失败响应 (HTTP 200, 业务错误)**:

```json
{
  "code": 150012,
  "message": "InvalidFilterType",
  "data": null
}
```

### 7.5. API-xxx（按Controller重新编号） 获取模型列表 (GET /api/data/model)

- **鉴权**: 需要 JWT JWT Bearer Token Token（`[Authorize]`），用户需具备相应数据访问Privilege。
- **描述**: 根据可选关键字、Project ID Model列表，支持排序和包含预定义模型。

#### 7.5.1. 请求参数

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| keyword | string | 否 | 搜索关键字，用于模糊匹配模型名称。 |
| projectid | string | 否 | Project ID，用于筛选指定项目下的模型。 |
| include_predefined | boolean | 否 | 是否包含预定义模型，默认为 `false`。 |
| orderby | string | 否 | 排序字段，默认为 `-updatedat`（按更新时间倒序）。支持字段：`name`、`createdat`、`updatedat` 等。 |
| page | int | 否 | 页码，从 1 开始。 |
| page_size | int | 否 | 每页条数。 |

#### 7.5.2. 响应格式

| 字段 | 类型 | 说明 |
|------|------|------|
| code | int | 业务状态码，`0` 表示成功，非 `0` 表示失败。 |
| message | string | 提示信息。 |
| data | object | 分页数据对象。 |
| data.items | array | 模型列表。 |
| data.items[].id | string | 模型 ID。 |
| data.items[].name | string | 模型名称。 |
| data.items[].projectid | string | 所属项目 ID。 |
| data.items[].type | string | 模型类型。 |
| data.items[].ispredefined | boolean | 是否为预定义模型。 |
| data.items[].createdat | datetime | 创建时间。 |
| data.items[].updatedat | datetime | 更新时间。 |
| data.total | int | 总记录数。 |
| data.page | int | 当前页码。 |
| data.page_size | int | 每页条数。 |

#### 7.5.3. 错误码

| errorCode | message | 说明 |
|-----------|---------|------|
| 100000 | UnAuthToken | 未提供或提供了无效的认证 Token。 |
| 150000 | EmptyProjectId | Project ID 为空。 |
| 150010 | ClickHouseQueryError | ClickHouse 查询失败。 |
| 150016 | InvalidOrderBy | 排序字段无效。 |
| 999999 | DefaultException | 服务器内部错误。 |

#### 7.5.4. 请求示例

```json
GET /api/data/model?keyword=test&projectid=proj_123456&include_predefined=false&orderby=-updatedat&page=1&page_size=20
```

#### 7.5.5. 响应示例

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
        "projectid": "proj_123456",
        "type": "chat",
        "ispredefined": false,
        "createdat": "2024-01-15T10:30:00Z",
        "updatedat": "2024-01-20T14:45:00Z"
      }
    ],
    "total": 1,
    "page": 1,
    "page_size": 20
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

---

## 8. NotifyController 接口

本章覆盖 2 个 HTTP 端点，每个端点一个接口卡片。

### 8.1. API-010 WeChatNotify (POST /api/payment/notify/wechatnotify)

- **鉴权**: 无（Payment平台使用自身签名机制验证，系统内通过 NotifyHandler 验签）
- **描述**: 接收微信Payment平台异步通知，验证签名并处理Payment结果，更新订单状态。
- **请求参数**: 请求体为微信Payment平台回调的原始 XML 数据，由微信服务器直接推送。主要字段如下：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| return_code | string | 是 | 返回状态码，`SUCCESS` 表示接收成功 |
| return_msg | string | 是 | 返回信息，如处理失败时的错误描述 |
| appid | string | 是 | 微信Payment分配的公众账号 ID |
| mch_id | string | 是 | 微信Payment分配的商户号 |
| out_trade_no | string | 是 | 商户订单号（对应 AgentInsightService 内部订单号） |
| transaction_id | string | 是 | 微信Payment订单号 |
| trade_type | string | 是 | 交易类型，如 `JSAPI`、`NATIVE` |
| trade_state | string | 是 | 交易状态，如 `SUCCESS` |
| total_fee | int | 是 | 订单总金额，单位为分 |
| time_end | string | 是 | Payment完成时间，格式为 `yyyyMMddHHmmss` |

- **响应格式**: 成功时返回微信Payment平台要求的 XML 格式确认信息

| 字段 | 类型 | 说明 |
|------|------|------|
| return_code | string | 返回状态码，`SUCCESS` 表示接收成功 |
| return_msg | string | 返回信息，如处理失败时的错误描述 |

- **错误码**:

| errorCode | message | 说明 |
|-----------|---------|------|
| 810010 | InvalidWeChatNotify | 微信Payment通知无效或验签失败 |
| 810011 | EmptyOrderNo | 商户订单号为空 |
| 810015 | OrderNotExist | 订单不存在 |
| 810016 | EmptyWeChatTransaction | 微信交易信息为空 |
| 810017 | InvalidWeChatTradeNo | 微信交易号无效 |
| 810018 | EmptyWeChatNotify | 微信Payment通知内容为空 |
| 810025 | InvalidTotalAmount | 订单金额校验失败 |
| 810026 | OrderStateUpdateFailed | 订单状态更新失败 |
| 810027 | InvalidMerchant | 商户信息无效 |
| 620014 | FakedWeChatRequest | 伪造的微信请求 |
| 999999 | DefaultException | 系统默认异常 |

- **请求示例**: 该接口由微信Payment平台服务器直接调用，请求体为微信Payment结果通知的 XML 数据，无需客户端构造请求。

```xml
<xml>
  <appid><![CDATA[wx8888888888888888]]></appid>
  <mch_id><![CDATA[1900000109]]></mch_id>
  <out_trade_no><![CDATA[AIS20250115142345001]]></out_trade_no>
  <transaction_id><![CDATA[4200001234202501151234567890]]></transaction_id>
  <trade_type><![CDATA[NATIVE]]></trade_type>
  <trade_state><![CDATA[SUCCESS]]></trade_state>
  <total_fee>9900</total_fee>
  <time_end><![CDATA[20250115142345]]></time_end>
</xml>
```

- **响应示例**:

**成功响应**:
```xml
<xml>
  <return_code><![CDATA[SUCCESS]]></return_code>
  <return_msg><![CDATA[OK]]></return_msg>
</xml>
```

**失败响应**:
```xml
<xml>
  <return_code><![CDATA[FAIL]]></return_code>
  <return_msg><![CDATA[InvalidWeChatNotify]]></return_msg>
</xml>
```

### 8.2. API-xxx（按Controller重新编号） AlipayNotify (POST /api/payment/notify/alipaynotify)

- **鉴权**: 无（Payment宝使用自身签名机制验证，系统内通过 NotifyHandler 验签）
- **描述**: 接收Payment宝异步通知，验证签名并处理交易结果，更新订单状态及触发后续业务流程。
- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| notify_time | string | 是 | 通知时间，格式为 `yyyy-MM-dd HH:mm:ss` |
| notify_type | string | 是 | 通知类型，固定为 `trade_status_sync` |
| notify_id | string | 是 | 通知校验 ID |
| app_id | string | 是 | Payment宝分配给开发者的应用 ID |
| charset | string | 是 | 编码格式，如 `utf-8` |
| version | string | 是 | 调用接口版本，固定为 `1.0` |
| sign_type | string | 是 | 签名类型，如 `RSA2` |
| sign | string | 是 | 签名串 |
| trade_no | string | 是 | Payment宝交易号 |
| out_trade_no | string | 是 | 商户订单号（对应 AgentInsightService 内部订单号） |
| trade_status | string | 是 | 交易状态，如 `TRADE_SUCCESS`、`TRADE_FINISHED`、`TRADE_CLOSED`、`WAIT_BUYER_PAY` |
| total_amount | string | 是 | 订单总金额，单位为元，精确到小数点后两位 |
| buyer_id | string | 否 | 买家Payment宝用户 ID |
| buyer_logon_id | string | 否 | 买家Payment宝账号 |
| seller_id | string | 否 | 卖家Payment宝用户 ID |
| seller_email | string | 否 | 卖家Payment宝账号 |
| subject | string | 否 | 订单标题 |
| body | string | 否 | 订单描述 |
| gmt_create | string | 否 | 交易创建时间 |
| gmt_payment | string | 否 | 交易付款时间 |
| gmt_close | string | 否 | 交易关闭时间 |
| refund_fee | string | 否 | 退款金额 |
| receipt_amount | string | 否 | 实收金额 |
| invoice_amount | string | 否 | 开票金额 |
| buyer_pay_amount | string | 否 | 付款金额 |
| point_amount | string | 否 | 集分宝金额 |
| fund_bill_list | string | 否 | Payment渠道信息列表（JSON 数组字符串） |
| passback_params | string | 否 | 回传参数（透传字段） |
| voucher_detail_list | string | 否 | 优惠券信息列表（JSON 数组字符串） |

- **响应格式**:

| 字段 | 类型 | 说明 |
|---|---|---|
| 响应体 | string | 处理成功返回纯文本 `success`；处理失败返回纯文本 `failure` |

- **错误码**:

| errorCode | message | 说明 |
|-----------|---------|------|
| 810002 | AlipaySettingNotConfig | Payment宝PaymentConfig不存在或未正确Config |
| 810003 | AlipayConnectionError | 与Payment宝服务器通信失败 |
| 810004 | AlipayTradeError | Payment宝交易处理失败 |
| 810005 | InvalidAlipayTradeNo | Payment宝交易号无效 |
| 810006 | InvalidAlipayTransaction | 无效的Payment宝交易记录 |
| 810007 | AlipaySignatureError | Payment宝通知签名验证失败 |
| 810008 | AlipaySignDictionaryError | Payment宝签名参数字典构建失败 |
| 810011 | EmptyOrderNo | 商户订单号为空 |
| 810015 | OrderNotExist | 订单不存在 |
| 810025 | InvalidTotalAmount | 通知金额与订单金额不匹配 |
| 810026 | OrderStateUpdateFailed | 订单状态更新失败 |
| 810027 | InvalidMerchant | 无效的商户Config |
| 999999 | DefaultException | 未预期的系统异常 |

- **请求示例**:

```json
{
  "notify_time": "2025-01-15 14:23:45",
  "notify_type": "trade_status_sync",
  "notify_id": "RqOnPbKpHojXflG8bJqJ3Q",
  "app_id": "2021003127691234",
  "charset": "utf-8",
  "version": "1.0",
  "sign_type": "RSA2",
  "sign": "base64_encoded_signature_string",
  "trade_no": "2025011522001412345678901234",
  "out_trade_no": "AIS20250115142345001",
  "trade_status": "TRADE_SUCCESS",
  "total_amount": "99.00",
  "buyer_id": "2088102146225135",
  "buyer_logon_id": "user@example.com",
  "seller_id": "2088102146225136",
  "seller_email": "merchant@example.com",
  "subject": "AgentInsightService - 专业版月度订阅",
  "gmt_create": "2025-01-15 14:20:00",
  "gmt_payment": "2025-01-15 14:23:45",
  "receipt_amount": "99.00",
  "buyer_pay_amount": "99.00",
  "invoice_amount": "99.00",
  "point_amount": "0.00",
  "fund_bill_list": "[{\"amount\":\"99.00\",\"fundChannel\":\"ALIPAYACCOUNT\"}]",
  "passback_params": "{\"projectId\":\"proj_8f3a2b1c\"}"
}
```

- **响应示例**:

```text
// 成功响应
success

// 失败响应（签名验证失败）
failure
```

**Payment回调流程说明**: 微信/Payment宝Payment平台调用上述接口后，请求进入 `NotifyHandler` 进行验签，验签通过后触发 `PaymentTransactionNotification`（MediatR 事件），由 `PaymentTransactionSaveHandler` 处理Payment结果并更新数据库，该Handler内置重试机制（最多重试 3 次）。

---

## 9. OrderController 接口

本章共覆盖 4 个 HTTP 端点，每个端点一个接口卡片。

### 9.1. API-xxx（按Controller重新编号） 获取订单列表 (GET /api/payment/order)

- **鉴权**: 无
- **描述**: 根据组织 ID 分页查询订单列表，用于Payment管理场景下的订单概览。

- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
| :--- | :--- | :--- | :--- |
| orgId | string | 是 | 组织唯一标识符，用于限定查询范围。 |
| page | int | 否 | 页码，从 1 开始。默认值为 1。 |
| page_size | int | 否 | 每页记录数。默认值为 20。 |

- **响应格式**:

| 字段 | 类型 | 说明 |
| :--- | :--- | :--- |
| code | int | 业务状态码，`0` 表示成功，非 `0` 表示失败。 |
| message | string | 状态描述信息。 |
| data | object | 返回的数据主体。 |
| data.items | array | 订单列表。 |
| data.items[].id | string | 订单唯一标识符。 |
| data.items[].orderNo | string | 订单编号。 |
| data.items[].orgId | string | 所属组织 ID。 |
| data.items[].productType | int | 产品类型 (对应 `ProductType` 枚举: `None`=0, `Monthly`=1, `Permanent`=2)。 |
| data.items[].amount | number | 订单金额。 |
| data.items[].state | int | 订单状态 (对应 `OrderState` 枚举: `Created`=1, `WaitForPay`=2, `Paid`=3, `Refunded`=4, `Cancelled`=5, `Closed`=6, `PayError`=7)。 |
| data.items[].payMethod | int | Payment方式 (对应 `PayMethod` 枚举: `WeChat`=1, `Alipay`=2)。 |
| data.items[].createdAt | string | 订单创建时间。 |
| data.total | int | 符合条件的总记录数。 |
| data.page | int | 当前页码。 |
| data.page_size | int | 每页记录数。 |

- **错误码**:

| errorCode | message | 说明 |
| :--- | :--- | :--- |
| 100000 | UnAuthToken | 未认证的 Token 或 Token 无效。 |
| 810012 | DoNotOwnOrganization | 当前用户不拥有该组织，无权访问其订单数据。 |
| 810015 | OrderNotExist | 指定的订单不存在。 |
| 999999 | DefaultException | 服务器内部错误。 |

- **请求示例**:

```json
GET /api/payment/order?orgId=org_123456&page=1&page_size=20
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
        "id": "order_001",
        "orderNo": "20231027123456",
        "orgId": "org_123456",
        "productType": 1,
        "amount": 99.00,
        "state": 3,
        "payMethod": 1,
        "createdAt": "2023-10-27T10:00:00Z"
      }
    ],
    "total": 1,
    "page": 1,
    "page_size": 20
  }
}
```

**失败响应**:

```json
{
  "code": 810012,
  "message": "DoNotOwnOrganization",
  "data": null
}
```

### 9.2. API-002 创建Payment订单 (POST /api/payment/order)

- **鉴权**: 无（代码中未标注 `[Authorize]` 特性）
- **描述**: 创建Payment订单，支持微信Payment与Payment宝Payment，并返回Payment所需参数。

- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `projectId` | long | 是 | Project ID |
| `organizationId` | long | 是 | Org ID |
| `productType` | int | 是 | 产品类型，枚举值见 `ProductType`（0=None，1=Monthly，2=Permanent） |
| `agentType` | int | 是 | Agent 类型，枚举值见 `AgentType`（1=Assistant，2=Research） |
| `payMethod` | int | 是 | Payment方式，枚举值见 `PayMethod`（1=WeChat，2=Alipay） |
| `totalAmount` | decimal | 是 | 订单总金额（元），必须大于 0 |
| `subPayMethod` | int | 否 | 子Payment方式，枚举值见 `SubPayMethod`（1=WECHAT_JSAPI，2=WECHAT_NATIVE，3=WECHAT_MINIPROGRAM，11=ALIPAY_FAST_INSTANT_TRADE_PAY） |

- **响应格式**:

| 字段 | 类型 | 说明 |
|---|---|---|
| `code` | int | 状态码，`0` 表示成功，非 `0` 表示失败（见错误码表） |
| `message` | string | 提示信息 |
| `data` | object | Payment参数，根据 `payMethod` 返回不同结构 |
| `data.payMethod` | int | Payment方式，枚举值见 `PayMethod` |
| `data.orderNo` | string | 订单号 |
| `data.payParams` | object | Payment参数，微信Payment返回 `appId`、`timeStamp`、`nonceStr`、`package`、`signType`、`paySign`；Payment宝返回 `orderStr` |

- **错误码**:

| errorCode | message | 说明 |
|---|---|---|
| 100000 | UnAuthToken | 未认证的 Token |
| 810001 | WeChatSettingNotConfig | 微信PaymentConfig不存在 |
| 810002 | AlipaySettingNotConfig | Payment宝PaymentConfig不存在 |
| 810003 | AlipayConnectionError | Payment宝连接错误 |
| 810004 | AlipayTradeError | Payment宝交易错误 |
| 810011 | EmptyOrderNo | 订单号为空 |
| 810012 | DoNotOwnOrganization | 无权操作该组织 |
| 810013 | ProductNotExist | 产品不存在 |
| 810014 | ProductDurationNotExist | 产品时长不存在 |
| 810015 | OrderNotExist | 订单不存在 |
| 810019 | UnsupportedPayMethod | 不支持的Payment方式 |
| 810020 | AlipayPlaceOrderError | Payment宝下单失败 |
| 810021 | WeChatEmptyResponse | 微信Payment返回空响应 |
| 810022 | WeChatErrorResponse | 微信Payment返回错误响应 |
| 810023 | CannotDowngradeProduct | 不能降级产品 |
| 810025 | InvalidTotalAmount | 无效的订单总金额 |
| 810026 | OrderStateUpdateFailed | 订单状态更新失败 |
| 810027 | InvalidMerchant | 无效商户 |
| 990001 | EncryptionFailed | 加密失败 |
| 990002 | DecryptionFailed | 解密失败 |
| 999999 | DefaultException | 默认异常 |

- **请求示例**:

```json
{
  "projectId": 1001,
  "organizationId": 501,
  "productType": 1,
  "agentType": 1,
  "payMethod": 1,
  "totalAmount": 99.00,
  "subPayMethod": 1
}
```

- **响应示例**:

**成功响应**:

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "payMethod": 1,
    "orderNo": "202501011200000001",
    "payParams": {
      "appId": "wx1234567890abcdef",
      "timeStamp": "1735718400",
      "nonceStr": "5K8264ILTKCH16CQ2502SI8ZNMTM67VS",
      "package": "prepay_id=wx1234567890abcdef",
      "signType": "RSA",
      "paySign": "oR9d8PuhnIc+YZ8cQY9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY2XzZQ9Q6YlQnD4xY

---

## 10. ProductController 接口

本章共覆盖 2 个 HTTP 端点，每个端点一个接口卡片。

### 10.1. API-xxx（按Controller重新编号） ProductController.Get (GET /api/product)

- **鉴权**: 无
- **描述**: 获取产品列表。该接口用于查询当前可用的产品信息，通常用于展示产品目录或定价页面。
- **请求参数**: 无
- **响应格式**:

| 字段 | 类型 | 说明 |
|---|---|---|
| `code` | int | 业务状态码，`0` 表示成功，非 `0` 表示失败 |
| `data` | array | 产品数据列表 |
| `data[].id` | string | 产品唯一标识 |
| `data[].name` | string | 产品名称 |
| `data[].description` | string | 产品描述 |
| `data[].productType` | int | 产品类型，`1` 表示按月，`2` 表示永久 |
| `data[].price` | decimal | 产品价格 |
| `data[].duration` | int | 产品时长（天） |
| `data[].agentType` | int | Agent 类型，`1` 表示 Assistant，`2` 表示 Research |
| `data[].isActive` | boolean | 产品是否启用 |
| `data[].createdAt` | datetime | 产品创建时间 |
| `data[].updatedAt` | datetime | 产品更新时间 |
| `message` | string | 提示信息，成功时为 `"success"` |

- **错误码**:

| errorCode | message | 说明 |
|---|---|---|
| `999999` | `DefaultException` | 默认异常，服务器内部错误 |
| `100000` | `UnAuthToken` | 未认证的 Token，请求未携带有效身份凭证 |

- **请求示例**:

```http
GET /api/product HTTP/1.1
Host: localhost
```

- **响应示例**:

> 成功响应

```json
{
  "code": 0,
  "data": [
    {
      "id": "prod_001",
      "name": "AgentInsight 基础版",
      "description": "适用于个人开发者的基础 Agent Service",
      "productType": 1,
      "price": 99.00,
      "duration": 30,
      "agentType": 1,
      "isActive": true,
      "createdAt": "2024-01-01T00:00:00Z",
      "updatedAt": "2024-01-01T00:00:00Z"
    },
    {
      "id": "prod_002",
      "name": "AgentInsight 专业版",
      "description": "适用于团队的专业级 Agent Service",
      "productType": 2,
      "price": 999.00,
      "duration": 365,
      "agentType": 2,
      "isActive": true,
      "createdAt": "2024-01-01T00:00:00Z",
      "updatedAt": "2024-01-01T00:00:00Z"
    }
  ],
  "message": "success"
}
```

> 失败响应

```json
{
  "code": 999999,
  "data": null,
  "message": "DefaultException"
}
```

### 10.2. API-002 ProductController.GetDuration (GET /api/product/duration)

- **鉴权**: 无
- **描述**: 获取产品时长列表，返回所有可用的产品时长选项（如月付、永久等）。
- **请求参数**: 无
- **响应格式**:

| 字段 | 类型 | 说明 |
|------|------|------|
| code | int | 状态码，0 表示成功 |
| data | array | 产品时长列表 |
| data[].type | int | 产品类型，`1` 表示月付，`2` 表示永久 |
| data[].name | string | 时长名称，如 "月付"、"永久" |
| data[].months | int | 时长对应的月数（永久为 -1） |
| message | string | 提示信息 |

- **错误码**:

| errorCode | message | 说明 |
|-----------|---------|------|
| 810013 | ProductNotExist | 产品不存在 |
| 810014 | ProductDurationNotExist | 产品时长不存在 |
| 999999 | DefaultException | 默认异常，未预期的服务端错误 |

- **请求示例**:

```http
GET /api/product/duration HTTP/1.1
Host: localhost
```

- **响应示例**:

> 成功响应

```json
{
  "code": 0,
  "data": [
    {
      "type": 1,
      "name": "月付",
      "months": 1
    },
    {
      "type": 2,
      "name": "永久",
      "months": -1
    }
  ],
  "message": "success"
}
```

> 失败响应

```json
{
  "code": 810014,
  "data": null,
  "message": "ProductDurationNotExist"
}
```

---

## 11. BulletinController, HealthController 接口

本章覆盖 `API/Controllers/ToolsManagement/BulletinController.cs` 与 `API/Controllers/ToolsManagement/HealthController.cs` 两个Controller，共 8 个 HTTP 端点，每个端点一个接口卡片。

### 11.1. API-xxx（按Controller重新编号） 创建Bulletin (POST /api/tools/bulletin)

- **鉴权**: 无（代码中未标注 `[Authorize]` 特性）
- **描述**: 创建一条新的Bulletin（Bulletin），支持新闻、活动、通知、协议等多种类型。
- **路径**: `API/Controllers/ToolsManagement/BulletinController.cs:32`

#### 11.1.1. 请求参数

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `title` | string | 是 | Bulletin标题 |
| `content` | string | 是 | Bulletin正文内容 |
| `type` | int | 是 | Bulletin类型，枚举值：`News`(1)、`Activity`(2)、`Information`(3)、`Annoucement`(4)、`Advertisement`(5)、`Agreement`(9) |
| `status` | int | 是 | Bulletin状态，枚举值：`Draft`(1)、`Reviewing`(2)、`Revision`(3)、`Published`(4)、`Expired`(5)、`Closed`(6) |
| `startTime` | datetime? | 否 | Bulletin生效开始时间 |
| `endTime` | datetime? | 否 | Bulletin生效结束时间 |
| `targetUrl` | string? | 否 | Bulletin跳转链接 |
| `coverImage` | string? | 否 | Bulletin封面图片 URL |
| `sortOrder` | int? | 否 | 排序权重，数值越小越靠前 |
| `remark` | string? | 否 | 备注信息 |

#### 11.1.2. 响应格式

| 字段 | 类型 | 说明 |
|------|------|------|
| `code` | int | 状态码，`0` 表示成功，非 `0` 表示失败 |
| `message` | string | 状态描述信息 |
| `data` | object | 创建成功的Bulletin数据 |
| `data.id` | long | Bulletin唯一标识 ID |
| `data.title` | string | Bulletin标题 |
| `data.type` | int | Bulletin类型 |
| `data.status` | int | Bulletin状态 |
| `data.createdAt` | datetime | 创建时间 |
| `data.updatedAt` | datetime | 更新时间 |

#### 11.1.3. 错误码

| errorCode | message | 说明 |
|-----------|---------|------|
| `DefaultException` | `999999` | 服务器内部异常 |
| `EncryptionFailed` | `990001` | 数据加密失败 |
| `DecryptionFailed` | `990002` | 数据解密失败 |
| `UnAuthToken` | `100000` | 未认证的 Token 或 Token 无效 |

#### 11.1.4. 请求示例

```json
{
  "title": "系统维护通知",
  "content": "系统将于本周六 22:00 进行升级维护，预计持续 2 小时。",
  "type": 4,
  "status": 1,
  "startTime": "2025-01-01T00:00:00",
  "endTime": "2025-01-31T23:59:59",
  "targetUrl": "https://example.com/notice/123",
  "coverImage": "https://example.com/images/notice-cover.png",
  "sortOrder": 1,
  "remark": "例行维护Bulletin"
}
```

#### 11.1.5. 响应示例

**成功响应：**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 1001,
    "title": "系统维护通知",
    "type": 4,
    "status": 1,
    "createdAt": "2025-01-01T10:00:00",
    "updatedAt": "2025-01-01T10:00:00"
  }
}
```

**失败响应（服务器内部异常）：**

```json
{
  "code": 999999,
  "message": "DefaultException",
  "data": null
}
```

### 11.2. API-045 获取协议Bulletin (GET /api/tools/bulletin/agreement)

- **鉴权**: 无
- **描述**: 根据别名获取协议类型的Bulletin内容。
- **路径**: `API/Controllers/ToolsManagement/BulletinController.cs:45`

#### 11.2.1. 请求参数

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| alias | string | 是 | Bulletin别名，用于定位特定的协议Bulletin。 |

#### 11.2.2. 响应格式

| 字段 | 类型 | 说明 |
|---|---|---|
| code | int | 状态码，`0` 表示成功，非 `0` 表示失败。 |
| message | string | 提示信息。 |
| data | object | Bulletin数据。 |
| data.id | string | Bulletin ID。 |
| data.title | string | Bulletin标题。 |
| data.content | string | Bulletin内容。 |
| data.type | int | Bulletin类型，固定为 `Agreement` (9)。 |
| data.status | int | Bulletin状态。 |
| data.alias | string | Bulletin别名。 |
| data.createdAt | datetime | 创建时间。 |
| data.updatedAt | datetime | 更新时间。 |

#### 11.2.3. 错误码

| errorCode | message | 说明 |
|---|---|---|
| 999999 | DefaultException | 服务器内部错误。 |
| 100000 | UnAuthToken | 未认证或 Token 无效。 |

#### 11.2.4. 请求示例

```json
GET /api/tools/bulletin/agreement?alias=user_agreement_v1
```

#### 11.2.5. 响应示例

**成功响应：**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "b1f3a2c4-5d6e-4f8a-9b0c-1d2e3f4a5b6c",
    "title": "用户协议",
    "content": "<h1>用户协议</h1><p>欢迎使用 AgentInsightService...</p>",
    "type": 9,
    "status": 4,
    "alias": "user_agreement_v1",
    "createdAt": "2024-01-01T00:00:00Z",
    "updatedAt": "2024-01-01T00:00:00Z"
  }
}
```

**失败响应：**

```json
{
  "code": 999999,
  "message": "DefaultException",
  "data": null
}
```

### 11.3. API-064 分页查询Bulletin (GET /api/tools/bulletin/bulletins)

- **鉴权**: 无
- **描述**: 分页查询Bulletin列表，支持按Bulletin类型和轮播状态筛选。
- **路径**: `API/Controllers/ToolsManagement/BulletinController.cs:64`

#### 11.3.1. 请求参数

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| type | int? | 否 | Bulletin类型，枚举值：`News`(1)、`Activity`(2)、`Information`(3)、`Annoucement`(4)、`Advertisement`(5)、`Agreement`(9) |
| isCarousel | bool | 否 | 是否仅查询轮播Bulletin，默认 `false` |
| page | int | 否 | 页码，默认值为 `1` |
| page_size | int | 否 | 每页条数，默认值为 `10` |

#### 11.3.2. 响应格式

| 字段 | 类型 | 说明 |
|---|---|---|
| code | int | 状态码，`0` 表示成功 |
| message | string | 提示信息 |
| data | object | 分页数据 |
| data.items | array | Bulletin列表 |
| data.items.id | string | Bulletin ID |
| data.items.title | string | Bulletin标题 |
| data.items.content | string | Bulletin内容 |
| data.items.type | int | Bulletin类型，枚举值：`News`(1)、`Activity`(2)、`Information`(3)、`Annoucement`(4)、`Advertisement`(5)、`Agreement`(9) |
| data.items.status | int | Bulletin状态，枚举值：`Draft`(1)、`Reviewing`(2)、`Revision`(3)、`Published`(4)、`Expired`(5)、`Closed`(6) |
| data.items.isCarousel | bool | 是否为轮播Bulletin |
| data.items.createdAt | datetime | 创建时间 |
| data.items.updatedAt | datetime | 更新时间 |
| data.total | int | 总记录数 |
| data.page | int | 当前页码 |
| data.page_size | int | 每页条数 |

#### 11.3.3. 错误码

| errorCode | message | 说明 |
|---|---|---|
| 0 | Success | 请求成功 |
| 999999 | DefaultException | 服务器内部错误 |

#### 11.3.4. 请求示例

```json
GET /api/tools/bulletin/bulletins?type=1&isCarousel=false&page=1&page_size=10
```

#### 11.3.5. 响应示例

**成功响应：**

```json
{
  "code": 0,
  "message": "Success",
  "data": {
    "items": [
      {
        "id": "b1f2c3d4-...",
        "title": "系统升级通知",
        "content": "系统将于本周六进行升级维护...",
        "type": 1,
        "status": 4,
        "isCarousel": false,
        "createdAt": "2025-01-15T10:00:00Z",
        "updatedAt": "2025-01-15T10:00:00Z"
      }
    ],
    "total": 1,
    "page": 1,
    "page_size": 10
  }
}
```

**失败响应：**

```json
{
  "code": 999999,
  "message": "DefaultException",
  "data": null
}
```

### 11.4. API-082 获取后端Bulletin列表 (GET /api/tools/bulletin/backend)

- **鉴权**: 无
- **描述**: 获取后端Bulletin列表，支持按Bulletin类型和状态筛选，并支持分页查询。
- **路径**: `API/Controllers/ToolsManagement/BulletinController.cs:82`

#### 11.4.1. 请求参数

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| type | int? | 否 | Bulletin类型，枚举值：`News`(1)、`Activity`(2)、`Information`(3)、`Annoucement`(4)、`Advertisement`(5)、`Agreement`(9) |
| status | int? | 否 | Bulletin状态，枚举值：`Draft`(1)、`Reviewing`(2)、`Revision`(3)、`Published`(4)、`Expired`(5)、`Closed`(6) |
| page | int | 否 | 页码，默认值为 `1` |
| page_size | int | 否 | 每页条数，默认值为 `10` |

#### 11.4.2. 响应格式

| 字段 | 类型 | 说明 |
|---|---|---|
| code | int | 状态码，0 表示成功 |
| message | string | 返回消息 |
| data | object | 返回数据 |
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
| data.page_size | int | 每页条数 |

#### 11.4.3. 错误码

| errorCode | message | 说明 |
|---|---|---|
| 100000 | UnAuthToken | Token 无效或未授权 |
| 999999 | DefaultException | 服务器内部错误 |

#### 11.4.4. 请求示例

```json
GET /api/tools/bulletin/backend?type=1&status=4&page=1&page_size=10
```

#### 11.4.5. 响应示例

**成功响应：**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
        "title": "系统升级通知",
        "content": "系统将于本周六进行升级维护...",
        "type": 1,
        "status": 4,
        "createdAt": "2025-01-15T10:30:00Z",
        "updatedAt": "2025-01-15T10:30:00Z"
      }
    ],
    "total": 1,
    "page": 1,
    "page_size": 10
  }
}
```

**失败响应：**

```json
{
  "code": 100000,
  "message": "UnAuthToken",
  "data": null
}
```

### 11.5. API-096 审批通过Bulletin (POST /api/tools/bulletin/approve)

- **鉴权**: 无 `[Authorize]` 注解，无需鉴权
- **描述**: 审批通过Bulletin，将Bulletin状态从 `Reviewing`(2) 更新为 `Published`(4)。
- **路径**: `API/Controllers/ToolsManagement/BulletinController.cs:96`

#### 11.5.1. 请求参数

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| ids | string | 是 | 待审批通过的Bulletin ID 列表，多个 ID 以逗号分隔 |

#### 11.5.2. 响应格式

| 字段 | 类型 | 说明 |
|------|------|------|
| code | int | 状态码，`0` 表示成功 |
| message | string | 响应消息 |
| data | object | 响应数据，审批通过后返回更新后的Bulletin信息 |

#### 11.5.3. 错误码

| errorCode | message | 说明 |
|-----------|---------|------|
| 160000 | AlertNotFound | Bulletin不存在或已被删除 |
| 160013 | AlertOrgNotAccessible | 当前用户无权访问该Bulletin所属组织 |
| 160014 | AlertProjectNotFound | Bulletin关联的项目不存在 |
| 999999 | DefaultException | 服务器内部错误 |

#### 11.5.4. 请求示例

```json
{
  "ids": "1001,1002,1003"
}
```

#### 11.5.5. 响应示例

**成功响应：**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 1001,
    "title": "系统升级通知",
    "type": 1,
    "status": 4,
    "content": "系统将于本周六进行升级维护",
    "publishTime": "2025-01-15T10:30:00Z"
  }
}
```

**失败响应：**

```json
{
  "code": 160000,
  "message": "AlertNotFound",
  "data": null
}
```

### 11.6. API-110 修订Bulletin (POST /api/tools/bulletin/revision)

- **鉴权**: 需要 JWT 认证（JWT Bearer Token Token）
- **描述**: 将指定 ID 的Bulletin（Bulletin）状态修改为 `Revision`(3)（待修订）。
- **路径**: `API/Controllers/ToolsManagement/BulletinController.cs:110`

#### 11.6.1. 请求参数

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| ids | string | 是 | 待修订的Bulletin（Bulletin）ID 列表，多个 ID 使用逗号分隔 |

#### 11.6.2. 响应格式

| 字段 | 类型 | 说明 |
|------|------|------|
| code | int | 业务状态码，`0` 表示成功，非 `0` 表示失败 |
| message | string | 返回消息，成功时为 `"success"`，失败时为具体错误信息 |
| data | object | 返回数据，成功时包含 `updatedCount` 字段，失败时为 `null` |
| data.updatedCount | int | 成功修订的Bulletin（Bulletin）数量 |
| traceId | string | 请求Trace ID，用于日志Trace和问题排查 |

#### 11.6.3. 错误码

| errorCode | message | 说明 |
|-----------|---------|------|
| 0 | success | 操作成功 |
| 100000 | UnAuthToken | 未认证的 Token 或 Token 无效 |
| 100001 | EmptyUserId | User ID 为空 |
| 100005 | InvalidUser | 用户不存在或已禁用 |
| 100010 | UnauthorizedOperator | 操作者无Privilege执行此操作 |
| 999999 | DefaultException | 服务器内部异常 |

#### 11.6.4. 请求示例

```json
{
  "ids": "1001,1002,1003"
}
```

#### 11.6.5. 响应示例

**成功响应：**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "updatedCount": 3
  },
  "traceId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

**失败响应：**

```json
{
  "code": 100010,
  "message": "UnauthorizedOperator",
  "data": null,
  "traceId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

### 11.7. API-124 关闭Bulletin (POST /api/tools/bulletin/close)

- **鉴权**: 需要 JWT JWT Bearer Token Token（Controller类 `BulletinController` 标注了 `[Authorize]`）
- **描述**: 根据传入的Bulletin ID 列表，关闭指定的Bulletin。关闭后Bulletin状态将变为 `Closed`(6)，不再对外展示。
- **路径**: `API/Controllers/ToolsManagement/BulletinController.cs:124`

#### 11.7.1. 请求参数

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| ids | string | 是 | 待关闭的Bulletin ID 列表，多个 ID 使用英文逗号（`,`）分隔。例如：`1,2,3` |

#### 11.7.2. 响应格式

| 字段 | 类型 | 说明 |
|------|------|------|
| code | int | 业务状态码。`0` 表示成功，非 `0` 表示失败，具体错误码见下方表格 |
| message | string | 状态描述信息。成功时为 `"success"`，失败时为具体错误信息 |
| data | boolean | 操作结果。成功时返回 `true`，失败时返回 `false` |

#### 11.7.3. 错误码

| errorCode | message | 说明 |
|-----------|---------|------|
| 100000 | UnAuthToken | 未提供或提供了无效的认证 Token |
| 999999 | DefaultException | 服务器内部异常，请稍后重试 |

#### 11.7.4. 请求示例

```json
{
  "ids": "1,2,3"
}
```

#### 11.7.5. 响应示例

**成功响应：**

```json
{
  "code": 0,
  "message": "success",
  "data": true
}
```

**失败响应（未授权）：**

```json
{
  "code": 100000,
  "message": "UnAuthToken",
  "data": false
}
```

### 11.8. API-020 健康检查 (GET /api/tools/health)

- **鉴权**: 无
- **描述**: 检查 AgentInsightService 服务健康状态，确认服务是否正常运行。
- **路径**: `API/Controllers/ToolsManagement/HealthController.cs:20`

#### 11.8.1. 请求参数

无

#### 11.8.2. 响应格式

| 字段 | 类型 | 说明 |
|---|---|---|
| status | string | 服务健康状态，固定返回 `"Healthy"` |
| timestamp | string | 服务器当前时间，ISO 8601 格式 (UTC) |
| service | string | 服务名称，固定返回 `"AgentInsightService"` |
| version | string | 服务版本号，固定返回 `"1.0.0"` |

#### 11.8.3. 错误码

无

#### 11.8.4. 请求示例

```json
GET /api/tools/health
```

#### 11.8.5. 响应示例

**成功响应 (HTTP 200)：**

```json
{
  "status": "Healthy",
  "timestamp": "2025-01-15T08:30:00Z",
  "service": "AgentInsightService",
  "version": "1.0.0"
}
```

**失败响应 (HTTP 500) — 服务内部错误：**

```json
{
  "errorCode": 999999,
  "message": "DefaultException",
  "details": "An unexpected error occurred while processing the health check request."
}
```

---

## 12. WeChatController 接口


本章共覆盖 2 个 HTTP 端点，每个端点一个接口卡片。


### 12.1. API-xxx（按Controller重新编号） 微信服务器验证 (GET /api/tools/wechat)

- **鉴权**: 无
- **描述**: 用于微信公众平台服务器Config验证。当在微信公众平台Config服务器 URL 时，微信服务器会发送 GET 请求到该接口，携带 `signature`、`timestamp`、`nonce` 和 `echostr` 参数。该接口验证请求签名，若验证通过则原样返回 `echostr` 以完成服务器Config。
- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| signature | string | 是 | 微信加密签名，signature 结合了开发者填写的 token 参数和请求中的 timestamp 参数、nonce 参数。 |
| timestamp | string | 是 | 时间戳，用于防止请求重放。 |
| nonce | string | 是 | 随机数，用于增加签名的不可预测性。 |
| echostr | string | 是 | 随机字符串，验证成功后需原样返回。 |

- **响应格式**:

| 字段 | 类型 | 说明 |
|---|---|---|
| 响应体 | string | 验证成功后，接口直接返回 `echostr` 字符串，内容与请求参数中的 `echostr` 完全一致。 |

- **错误码**:

| errorCode | message | 说明 |
|---|---|---|
| 620002 | ExamineWeChatSignatureFailed | 微信签名验证失败。当 `signature` 与根据 `token`、`timestamp`、`nonce` 计算出的签名不一致时，返回此错误码。 |
| 620014 | FakedWeChatRequest | 伪造的微信请求。当请求来源无法被确认为微信服务器时，返回此错误码。 |
| 999999 | DefaultException | 默认异常。当发生未预期的服务器内部错误时，返回此错误码。 |

- **请求示例**:

```json
GET /api/tools/wechat?signature=abcdef1234567890&timestamp=1700000000&nonce=random_nonce_123&echostr=echo_string_456
```

- **响应示例**:

**成功响应**:

```text
echo_string_456
```

**失败响应**:

```json
{
  "errorCode": 620002,
  "message": "ExamineWeChatSignatureFailed",
  "data": null
}
```

### 12.2. API-002 微信消息与事件推送处理 (POST /api/tools/wechat)

- **鉴权**: 无（该接口为微信服务器回调入口，未标注 `[Authorize]`，通过签名验证保障安全）
- **描述**: 接收并处理来自微信服务器的消息与事件推送，包括文本消息、关注/取关事件、扫码事件等，并根据消息类型执行相应业务逻辑。
- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| signature | string | 是 | 微信加密签名，用于验证请求合法性，需与 `token` 及 `timestamp`、`nonce` 进行 SHA1 校验 |
| timestamp | string | 是 | 时间戳，用于签名校验与防重放攻击 |
| nonce | string | 是 | 随机数，用于签名校验 |
| openid | string | 否 | 发送方账号（User OpenID），在事件推送和消息推送时携带 |
| body | WeChatMessage | 是 | 微信服务器推送的 XML 消息体，经反序列化后的对象 |

**WeChatMessage 对象字段**:

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| ToUserName | string | 是 | 开发者微信号（接收方账号） |
| FromUserName | string | 是 | 发送方账号（User OpenID） |
| CreateTime | long | 是 | 消息创建时间（Unix 时间戳） |
| MsgType | WeChatMessageType | 是 | 消息类型，枚举值：`None`(0)、`Event`(1)、`Text`(2)、`Image`(3)、`Voice`(4)、`Video`(5)、`Shortvideo`(6)、`Location`(7)、`Link`(8) |
| MsgId | long | 否 | 消息 ID，用于消息去重 |
| Content | string | 否 | 文本消息内容（当 `MsgType` 为 `Text` 时） |
| Event | WeChatMessageEvent | 否 | 事件类型，枚举值：`Subscribe`(1)、`Unsubscribe`(2)、`Scan`(3)、`Location`(4)、`Click`(5)、`View`(6)、`MasssEndJobFinish`(7) |
| EventKey | string | 否 | 事件 KEY 值，扫码事件携带二维码参数，点击菜单事件携带菜单 KEY |
| Ticket | string | 否 | 二维码的 ticket，可用来换取二维码图片 |
| Latitude | double | 否 | 地理位置纬度（当事件为 `Location` 时） |
| Longitude | double | 否 | 地理位置经度（当事件为 `Location` 时） |
| Precision | double | 否 | 地理位置精度（当事件为 `Location` 时） |
| PicUrl | string | 否 | 图片链接（当 `MsgType` 为 `Image` 时） |
| MediaId | string | 否 | 媒体文件 ID（当 `MsgType` 为 `Image`、`Voice`、`Video`、`Shortvideo` 时） |
| Format | string | 否 | 语音格式（当 `MsgType` 为 `Voice` 时） |
| Recognition | string | 否 | 语音识别结果（当 `MsgType` 为 `Voice` 且开启识别时） |
| ThumbMediaId | string | 否 | 视频消息缩略图的媒体 ID（当 `MsgType` 为 `Video`、`Shortvideo` 时） |
| Location_X | double | 否 | 地理位置维度（当 `MsgType` 为 `Location` 时） |
| Location_Y | double | 否 | 地理位置经度（当 `MsgType` 为 `Location` 时） |
| Scale | int | 否 | 地图缩放大小（当 `MsgType` 为 `Location` 时） |
| Label | string | 否 | 地理位置信息（当 `MsgType` 为 `Location` 时） |
| Title | string | 否 | 消息标题（当 `MsgType` 为 `Link` 时） |
| Description | string | 否 | 消息描述（当 `MsgType` 为 `Link` 时） |
| Url | string | 否 | 消息链接（当 `MsgType` 为 `Link` 时） |

- **响应格式**: 成功时返回字符串 `"success"`（微信服务器要求），失败时返回错误信息字符串。

| 字段 | 类型 | 说明 |
|---|---|---|
| (响应体) | string | 成功时返回 `"success"`；签名校验失败或业务处理异常时返回 `"error"` 或异常消息 |

- **错误码**:

| errorCode | message | 说明 |
|---|---|---|
| 620002 | ExamineWeChatSignatureFailed | 微信签名校验失败，请求可能被篡改或来自非微信服务器 |
| 620005 | InvalidWeChatMessageType | 消息类型无效，无法识别 `MsgType` 对应的枚举值 |
| 620006 | InvalidWeChatMessageEvent | 事件类型无效，无法识别 `Event` 对应的枚举值 |
| 620007 | EmptyWeChatOpenId | OpenID 为空，无法定位用户身份 |
| 620014 | FakedWeChatRequest | 伪造的微信请求，签名校验未通过 |
| 810001 | WeChatSettingNotConfig | 微信Config缺失，无法完成消息处理（如 AppID/Secret 未Config） |
| 999999 | DefaultException | 服务器内部异常，处理消息时发生未预期的错误 |

- **请求示例**:

```json
{
  "signature": "1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b",
  "timestamp": "1710000000",
  "nonce": "1234567890",
  "openid": "o6_bmjrPTlm6_2sgVt7hMZOPfL2M",
  "body": {
    "ToUserName": "gh_9e1a2b3c4d5e",
    "FromUserName": "o6_bmjrPTlm6_2sgVt7hMZOPfL2M",
    "CreateTime": 1710000000,
    "MsgType": 2,
    "MsgId": 1234567890123456,
    "Content": "你好"
  }
}
```

- **响应示例**:

**成功响应**:
```json
"success"
```

**失败响应（签名校验失败）**:
```json
{
  "errorCode": 620002,
  "message": "ExamineWeChatSignatureFailed",
  "description": "微信签名校验失败，请求可能被篡改或来自非微信服务器"
}
```

**失败响应（消息类型无效）**:
```json
{
  "errorCode": 620005,
  "message": "InvalidWeChatMessageType",
  "description": "消息类型无效，无法识别 MsgType 对应的枚举值"
}
```

---

## 13. AlertController 接口

本章覆盖 `API/Controllers/UserManagement/AlertController.cs` 中定义的 7 个 HTTP 端点，每个端点一个接口卡片。

### 13.1. API-xxx（按Controller重新编号） GetConfig (GET /api/alert/config)

- **鉴权**: 无
- **描述**: 获取AlertConfig信息，包括时间单位、运算符、监控字段和通知方式的选项列表。
- **请求参数**: 无
- **响应格式**:

| 字段 | 类型 | 说明 |
|---|---|---|
| code | int | 状态码，0 表示成功，非 0 表示失败 |
| message | string | 提示信息 |
| data | object | 返回的Config数据 |
| data.alertTimeUnit | array | Alert时间单位选项列表 |
| data.alertTimeUnit[].label | string | 显示名称 |
| data.alertTimeUnit[].value | int | 枚举值，对应 `AlertTimeUnit` |
| data.alertOperator | array | Alert运算符选项列表 |
| data.alertOperator[].label | string | 显示名称 |
| data.alertOperator[].value | int | 枚举值，对应 `AlertOperator` |
| data.alertField | array | Alert监控字段选项列表 |
| data.alertField[].label | string | 显示名称 |
| data.alertField[].value | int | 枚举值，对应 `AlertField` |
| data.alertNotifyBy | array | Alert通知方式选项列表 |
| data.alertNotifyBy[].label | string | 显示名称 |
| data.alertNotifyBy[].value | int | 枚举值，对应 `AlertNotifyBy` |

- **错误码**:

| errorCode | message | 说明 |
|---|---|---|
| 999999 | DefaultException | 默认异常 |

- **请求示例**:

```json
{}
```

- **响应示例**:

**成功响应**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "alertTimeUnit": [
      { "label": "分钟", "value": 1 },
      { "label": "小时", "value": 2 },
      { "label": "天", "value": 3 }
    ],
    "alertOperator": [
      { "label": "大于", "value": 1 },
      { "label": "小于", "value": 2 },
      { "label": "等于", "value": 3 },
      { "label": "大于等于", "value": 4 },
      { "label": "小于等于", "value": 5 },
      { "label": "不等于", "value": 6 }
    ],
    "alertField": [
      { "label": "总 Token 数", "value": 1 },
      { "label": "总成本", "value": 2 },
      { "label": "错误数", "value": 3 },
      { "label": "延迟", "value": 4 },
      { "label": "错误率", "value": 5 },
      { "label": "输入 Token 数", "value": 6 },
      { "label": "输出 Token 数", "value": 7 },
      { "label": "警告数", "value": 8 },
      { "label": "Observation 数", "value": 9 }
    ],
    "alertNotifyBy": [
      { "label": "系统", "value": 1 },
      { "label": "短信", "value": 2 }
    ]
  }
}
```

**失败响应**

```json
{
  "code": 999999,
  "message": "DefaultException",
  "data": null
}
```

### 13.2. API-002 Get (GET /api/alert)

- **鉴权**: 需要认证 (JWT Bearer Token Token)
- **描述**: 根据组织 ID 或项目 ID 获取Alert规则列表。
- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| orgId | string | 否 | Org ID，用于按组织维度筛选Alert规则。与 `projectId` 至少提供一个。 |
| projectId | string | 否 | Project ID，用于按项目维度筛选Alert规则。与 `orgId` 至少提供一个。 |

- **响应格式**:

| 字段 | 类型 | 说明 |
|---|---|---|
| code | int | 业务状态码，`0` 表示成功，非 `0` 表示失败。 |
| message | string | 提示信息，成功时为 `"Success"`，失败时为具体错误信息。 |
| data | array | Alert规则列表。 |
| data[].id | string | Alert规则 ID。 |
| data[].name | string | Alert规则名称。 |
| data[].field | enum | 监控指标字段，取值参考 `AlertField` 枚举。 |
| data[].operator | enum | 比较运算符，取值参考 `AlertOperator` 枚举。 |
| data[].value | number | Alert阈值。 |
| data[].timeUnit | enum | 统计周期单位，取值参考 `AlertTimeUnit` 枚举。 |
| data[].timeValue | integer | 统计周期数值。 |
| data[].notifyBy | enum | 通知方式，取值参考 `AlertNotifyBy` 枚举。 |
| data[].state | enum | Alert规则状态，取值参考 `AlertRecordState` 枚举（Active=1, Read=2）。 |
| data[].createdAt | string | 创建时间 (ISO 8601)。 |
| data[].updatedAt | string | 更新时间 (ISO 8601)。 |

- **错误码**:

| errorCode | message | 说明 |
|---|---|---|
| 100000 | UnAuthToken | 未认证或 Token 无效。 |
| 150019 | OrgAndProjectBothEmpty | Org ID 和项目 ID 均为空。 |
| 160013 | AlertOrgNotAccessible | 当前用户无权访问该组织下的Alert规则。 |
| 160014 | AlertProjectNotFound | 指定的项目不存在或无权访问。 |
| 999999 | DefaultException | 服务器内部错误。 |

- **请求示例**:

```http
GET /api/alert?orgId=org_1234567890&projectId=proj_0987654321
```

- **响应示例**:

**成功响应**:

```json
{
  "code": 0,
  "message": "Success",
  "data": [
    {
      "id": "alert_001",
      "name": "高错误率Alert",
      "field": 5,
      "operator": 1,
      "value": 0.1,
      "timeUnit": 2,
      "timeValue": 1,
      "notifyBy": 1,
      "state": 1,
      "createdAt": "2024-01-01T12:00:00Z",
      "updatedAt": "2024-01-01T12:00:00Z"
    }
  ]
}
```

**失败响应** (未授权):

```json
{
  "code": 100000,
  "message": "UnAuthToken",
  "data": null
}
```

### 13.3. API-003 Create (POST /api/alert)

- **鉴权**: 需要 JWT 认证（JWT Bearer Token Token）
- **描述**: 创建一个新的Alert规则，用于监控 Agent 的 Token 消耗、成本、错误率等指标，并在满足条件时触发通知。
- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `name` | string | 是 | Alert名称，长度限制为 1-50 个字符 |
| `projectId` | long | 是 | 关联的 Project ID |
| `field` | AlertField | 是 | 监控的指标字段，可选值：`TotalTokens`(1), `TotalCost`(2), `ErrorCount`(3), `Latency`(4), `ErrorRate`(5), `InputTokens`(6), `OutputTokens`(7), `WarningCount`(8), `ObservationCount`(9) |
| `operator` | AlertOperator | 是 | 比较运算符，可选值：`GreaterThan`(1), `LessThan`(2), `EqualTo`(3), `GreaterThanOrEqualTo`(4), `LessThanOrEqualTo`(5), `NotEqualTo`(6) |
| `value` | decimal | 是 | 触发阈值，必须大于 0 |
| `timeUnit` | AlertTimeUnit | 是 | 时间单位，可选值：`Minute`(1), `Hour`(2), `Day`(3) |
| `timeValue` | int | 是 | 时间窗口大小，必须大于 0 |
| `notifyBy` | AlertNotifyBy | 是 | 通知方式，可选值：`System`(1), `SMS`(2) |

- **响应格式**:

| 字段 | 类型 | 说明 |
|---|---|---|
| `code` | int | 业务状态码，`0` 表示成功，非 `0` 表示失败 |
| `message` | string | 状态描述信息 |
| `data` | long | 创建的Alert记录 ID |

- **错误码**:

| errorCode | message | 说明 |
|---|---|---|
| 160000 | AlertNotFound | Alert不存在 |
| 160001 | CreateAlertFailed | 创建Alert失败 |
| 160004 | InvalidAlertPeriod | Alert时间周期无效 |
| 160005 | InvalidAlertFrequency | Alert频率无效 |
| 160006 | InvalidAlertField | Alert监控字段无效 |
| 160007 | InvalidAlertOperator | Alert比较运算符无效 |
| 160008 | InvalidAlertValue | Alert阈值无效 |
| 160010 | InvalidAlertName | Alert名称无效 |
| 160011 | InvalidAlertNotifyBy | Alert通知方式无效 |
| 160014 | AlertProjectNotFound | 关联的 Project 不存在 |
| 160015 | AlertNameTooLong | Alert名称过长 |
| 150000 | EmptyProjectId | Project ID 为空 |
| 100000 | UnAuthToken | Token 未认证或已过期 |
| 999999 | DefaultException | 默认异常 |

- **请求示例**:

```json
{
  "name": "Token 消耗Alert",
  "projectId": 12345,
  "field": 1,
  "operator": 1,
  "value": 100000,
  "timeUnit": 2,
  "timeValue": 1,
  "notifyBy": 1
}
```

- **响应示例**:

**成功响应**:
```json
{
  "code": 0,
  "message": "Success",
  "data": 67890
}
```

**失败响应**:
```json
{
  "code": 160014,
  "message": "AlertProjectNotFound",
  "data": null
}
```

### 13.4. API-004 Update (POST /api/alert/update)

- **鉴权**: 需要认证（JWT Bearer Token Token）
- **描述**: 更新现有AlertConfig信息，包括监控字段、比较条件、通知方式等。
- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | long | 是 | Alert记录 ID |
| name | string | 是 | Alert名称 |
| projectId | long | 是 | 关联项目 ID |
| field | int | 是 | 监控字段，对应 `AlertField` 枚举：`TotalTokens`(1), `TotalCost`(2), `ErrorCount`(3), `Latency`(4), `ErrorRate`(5), `InputTokens`(6), `OutputTokens`(7), `WarningCount`(8), `ObservationCount`(9) |
| operator | int | 是 | 比较操作符，对应 `AlertOperator` 枚举：`GreaterThan`(1), `LessThan`(2), `EqualTo`(3), `GreaterThanOrEqualTo`(4), `LessThanOrEqualTo`(5), `NotEqualTo`(6) |
| value | decimal | 是 | 比较阈值 |
| timeUnit | int | 是 | 时间单位，对应 `AlertTimeUnit` 枚举：`Minute`(1), `Hour`(2), `Day`(3) |
| timeValue | int | 是 | 时间周期数值 |
| notifyBy | int | 是 | 通知方式，对应 `AlertNotifyBy` 枚举：`System`(1), `SMS`(2) |

- **响应格式**:

| 字段 | 类型 | 说明 |
|------|------|------|
| code | int | 状态码，0 表示成功 |
| message | string | 提示信息 |
| data | object | 更新后的Alert数据，包含以下字段： |
| data.id | long | Alert记录 ID |
| data.name | string | Alert名称 |
| data.projectId | long | 关联项目 ID |
| data.field | int | 监控字段 |
| data.operator | int | 比较操作符 |
| data.value | decimal | 比较阈值 |
| data.timeUnit | int | 时间单位 |
| data.timeValue | int | 时间周期数值 |
| data.notifyBy | int | 通知方式 |
| data.updatedAt | string | 更新时间 (ISO 8601) |

- **错误码**:

| errorCode | message | 说明 |
|-----------|---------|------|
| 160000 | AlertNotFound | Alert不存在或已被删除 |
| 160002 | UpdateAlertFailed | 更新Alert失败 |
| 160004 | InvalidAlertPeriod | Alert周期设置无效 |
| 160005 | InvalidAlertFrequency | Alert频率设置无效 |
| 160006 | InvalidAlertField | Alert监控字段无效 |
| 160007 | InvalidAlertOperator | Alert比较操作符无效 |
| 160008 | InvalidAlertValue | Alert阈值设置无效 |
| 160010 | InvalidAlertName | Alert名称无效 |
| 160011 | InvalidAlertNotifyBy | Alert通知方式无效 |
| 160013 | AlertOrgNotAccessible | 无权访问该Alert所属组织 |
| 160014 | AlertProjectNotFound | Alert关联项目不存在 |
| 160015 | AlertNameTooLong | Alert名称超长 |
| 140008 | UnauthorizedProjectAccess | 无权访问该项目 |
| 100000 | UnAuthToken | 未认证或 Token 无效 |

- **请求示例**:

```json
{
  "id": 1001,
  "name": "Token 用量Alert",
  "projectId": 2001,
  "field": 1,
  "operator": 1,
  "value": 1000000,
  "timeUnit": 2,
  "timeValue": 1,
  "notifyBy": 1
}
```

- **响应示例**:

**成功响应**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 1001,
    "name": "Token 用量Alert",
    "projectId": 2001,
    "field": 1,
    "operator": 1,
    "value": 1000000,
    "timeUnit": 2,
    "timeValue": 1,
    "notifyBy": 1,
    "updatedAt": "2024-01-15T10:30:00Z"
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

### 13.5. API-005 Delete (POST /api/alert/delete)

- **鉴权**: 需要 JWT JWT Bearer Token Token（通过 `[Authorize]` 注解保护）
- **描述**: 根据提供的Alert ID 列表批量删除Alert记录。此操作会同时删除关联的订阅关系，并记录审计日志。
- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| alertIds | string | 是 | 待删除的Alert ID 列表，多个 ID 使用英文逗号 `,` 分隔。例如：`1001,1002,1003` |

- **响应格式**:

| 字段 | 类型 | 说明 |
|---|---|---|
| code | int | 业务状态码。`0` 表示成功，非 `0` 表示失败（具体见错误码表）。 |
| message | string | 状态描述信息。成功时为 `"success"`，失败时为具体的错误描述。 |
| data | object | 响应数据。成功时返回 `null`。 |

- **错误码**:

| errorCode | message | 说明 |
|---|---|---|
| 0 | success | 删除成功 |
| 100000 | UnAuthToken | 未提供或提供了无效的认证 Token |
| 160000 | AlertNotFound | 指定的Alert不存在或已被删除 |
| 160003 | DeleteAlertFailed | 删除Alert失败，请稍后重试 |
| 160013 | AlertOrgNotAccessible | 当前用户无权访问该Alert所属的组织 |
| 999999 | DefaultException | 服务器内部错误 |

- **请求示例**:

```json
{
  "alertIds": "1001,1002,1003"
}
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
  "code": 160000,
  "message": "AlertNotFound",
  "data": null
}
```

### 13.6. API-006 ReadRecords (POST /api/alert/record/read)

- **鉴权**: 需要 JWT JWT Bearer Token Token（`[Authorize]`）
- **描述**: 根据指定的记录 ID 列表，批量读取Alert记录，将其状态从 `Active`（1）更新为 `Read`（2）。
- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| recordIds | string | 是 | 待标记为已读的Alert记录 ID 列表，多个 ID 以逗号分隔。 |

- **响应格式**:

| 字段 | 类型 | 说明 |
|---|---|---|
| code | int | 业务状态码，`0` 表示成功，非 `0` 表示失败。 |
| message | string | 提示信息，成功时为 `"success"`，失败时为具体错误描述。 |
| data | object | 响应数据，成功时返回 `null`。 |

- **错误码**:

| errorCode | message | 说明 |
|---|---|---|
| 0 | success | 操作成功 |
| 100000 | UnAuthToken | 未认证的 Token 或 Token 已过期 |
| 160000 | AlertNotFound | 未找到指定的Alert记录 |
| 160013 | AlertOrgNotAccessible | 当前用户无权访问该Alert所属的组织 |
| 160014 | AlertProjectNotFound | 未找到Alert关联的 Project |
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
  "code": 0,
  "message": "success",
  "data": null
}
```

**失败响应**（Alert记录不存在）:
```json
{
  "code": 160000,
  "message": "AlertNotFound",
  "data": null
}
```

### 13.7. API-007 GetRecords (GET /api/alert/record)

- **鉴权**: 需要 JWT JWT Bearer Token Token（从 `AlertController` 类级别的 `[Authorize]` 注解推断）
- **描述**: 根据组织、Project、Alert标识和状态筛选条件，分页查询Alert记录列表。
- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| orgId | string | 否 | Org ID，用于过滤属于该组织的Alert记录 |
| projectId | string | 否 | Project ID，用于过滤属于该项目的Alert记录 |
| alertId | string | 否 | AlertConfig ID，用于过滤由该Alert触发的记录 |
| state | AlertRecordState | 否 | Alert记录状态，默认值为 `Active` (1)。可选值：`Active` (1)、`Read` (2) |
| page | int | 否 | 当前页码，默认值为 1 |
| page_size | int | 否 | 每页记录数，默认值为 20 |

- **响应格式**:

| 字段 | 类型 | 说明 |
|---|---|---|
| code | int | 业务状态码，`0` 表示成功，非 `0` 表示失败 |
| message | string | 状态描述信息 |
| data | object | 分页数据对象 |
| data.items | array | Alert记录列表 |
| data.items.id | string | Alert记录唯一标识 |
| data.items.alertId | string | 关联的AlertConfig ID |
| data.items.alertName | string | Alert名称 |
| data.items.orgId | string | 所属组织 ID |
| data.items.projectId | string | 所属项目 ID |
| data.items.state | AlertRecordState | 记录状态：`Active` (1)、`Read` (2) |
| data.items.message | string | Alert消息内容 |
| data.items.createdAt | datetime | 记录创建时间 |
| data.items.readAt | datetime | 记录读取时间，未读时为 `null` |
| data.total | int | 符合条件的总记录数 |
| data.page | int | 当前页码 |
| data.page_size | int | 每页记录数 |

- **错误码**:

| errorCode | message | 说明 |
|---|---|---|
| 160000 | AlertNotFound | Alert不存在或已被删除 |
| 160013 | AlertOrgNotAccessible | 当前用户无权访问该组织下的Alert记录 |
| 160014 | AlertProjectNotFound | 指定的项目不存在或无权访问 |
| 150000 | EmptyProjectId | Project ID 为空 |
| 100000 | UnAuthToken | 未认证或 Token 无效 |
| 999999 | DefaultException | 服务器内部错误 |

- **请求示例**:

```http
GET /api/alert/record?orgId=org_8f3b2c1a&projectId=proj_5e7d9a2b&alertId=alert_1a2b3c4d&state=1&page=1&page_size=20
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
        "id": "rec_9f8e7d6c",
        "alertId": "alert_1a2b3c4d",
        "alertName": "Token 使用量Alert",
        "orgId": "org_8f3b2c1a",
        "projectId": "proj_5e7d9a2b",
        "state": 1,
        "message": "Project proj_5e7d9a2b 在最近 5 分钟内 TotalTokens 超过阈值 100000",
        "createdAt": "2025-07-11T10:30:00Z",
        "readAt": null
      }
    ],
    "total": 1,
    "page": 1,
    "page_size": 20
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

---

## 14. CaptchaController 接口


本章共覆盖 2 个 HTTP 端点, 每个端点一个接口卡片.


### 14.1. API-029 CaptchaController.Get (GET /api/captcha)

- **鉴权**: 无
- **描述**: 根据手机号获取图形Captcha。该接口用于用户登录、注册或找回密码等场景，通过手机号生成并返回图形Captcha。
- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| mobile | string | 是 | 用户手机号，用于生成对应的图形Captcha |

- **响应格式**:

| 字段 | 类型 | 说明 |
|---|---|---|
| code | int | 状态码，`0` 表示成功，非 `0` 表示失败 |
| message | string | 提示信息，成功时为 `"success"`，失败时为具体错误描述 |
| data | object | 返回的数据体，成功时包含Captcha信息，失败时为 `null` |
| data.captchaId | string | Captcha唯一标识，用于后续校验 |
| data.captchaImage | string | Base64 编码的图形Captcha图片，前端可直接用于展示 |
| data.expiredSeconds | int | Captcha有效期（秒），默认 `300` 秒 |
| data.resendInterval | int | 重新发送Captcha的间隔时间（秒），默认 `60` 秒 |
| data.captchaCodeLength | int | Captcha长度，默认 `5` 位 |
| traceId | string | 请求Trace ID，用于日志排查 |

- **错误码**:

| errorCode | message | 说明 |
|---|---|---|
| 100000 | UnAuthToken | 未认证的 Token |
| 100009 | EmptyMobile | 手机号为空 |
| 110000 | SendSMSTooOften | 发送Captcha过于频繁，请稍后再试 |
| 110004 | ErrorCaptcha | Captcha错误 |
| 999999 | DefaultException | 系统默认异常，未预期的错误 |

- **请求示例**:

```json
{
  "mobile": "13800138000"
}
```

- **响应示例**:

**成功响应**:

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "captchaId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "captchaImage": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...",
    "expiredSeconds": 300,
    "resendInterval": 60,
    "captchaCodeLength": 5
  },
  "traceId": "7a9b8c7d-6e5f-4a3b-8c2d-1e0f9a8b7c6d"
}
```

**失败响应**:

```json
{
  "code": 100009,
  "message": "EmptyMobile",
  "data": null,
  "traceId": "7a9b8c7d-6e5f-4a3b-8c2d-1e0f9a8b7c6d"
}
```

### 14.2. API-xxx（按Controller重新编号） CaptchaController.GetSMSCaptcha (GET /api/captcha/sms)

- **鉴权**: 无
- **描述**: 获取短信Captcha。根据提供的手机号发送短信Captcha，Captcha长度为 6 位，有效期为 300 秒，发送间隔为 60 秒。

- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| phone | string | 是 | 接收Captcha的手机号码 |

- **响应格式**:

| 字段 | 类型 | 说明 |
|------|------|------|
| code | int | 业务状态码，`0` 表示成功，非 `0` 表示失败 |
| message | string | 状态描述信息 |
| data | object/null | 响应数据，成功时为 `null`，失败时为 `null` |
| traceId | string | 请求Trace ID，用于日志排查 |

- **错误码**:

| errorCode | message | 说明 |
|-----------|---------|------|
| 110000 | SendSMSTooOften | 短信发送过于频繁，请稍后再试（发送间隔为 60 秒） |
| 110001 | FailedToSendSMS | 短信发送失败，请检查手机号是否正确或稍后重试 |
| 100009 | EmptyMobile | 手机号为空，请填写手机号 |
| 999999 | DefaultException | 系统内部错误，请稍后重试 |

- **请求示例**:

```json
GET /api/captcha/sms?phone=13800138000
```

- **响应示例**:

**成功响应**:

```json
{
  "code": 0,
  "message": "Captcha已发送",
  "data": null,
  "traceId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

**失败响应（发送过于频繁）**:

```json
{
  "code": 110000,
  "message": "短信发送过于频繁，请稍后再试",
  "data": null,
  "traceId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

---

## 15. OrganizationController 接口

本章覆盖 `API/Controllers/UserManagement/OrganizationController.cs` 中定义的 4 个 HTTP 端点，每个端点一个接口卡片。

### 15.1. API-xxx（按Controller重新编号） 创建组织 (POST /api/user/organization)

- **源文件**: `API/Controllers/UserManagement/OrganizationController.cs:28`
- **鉴权**: 需要 JWT JWT Bearer Token Token（从 `[Authorize]` 注解推断，需验证当前用户身份）
- **描述**: 创建新的 Organization，当前用户将成为该组织的 Owner

- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | 是 | Organization 名称，长度限制 2-50 个字符（对应 `OrganizationNameTooShort` / `OrganizationNameTooLong`） |

- **响应格式**:

| 字段 | 类型 | 说明 |
|------|------|------|
| code | int | 状态码，0 表示成功，非 0 表示失败 |
| message | string | 状态描述信息 |
| data | object | 创建成功的 Organization 数据 |
| data.id | long | Organization 唯一标识 |
| data.name | string | Organization 名称 |
| data.ownerId | long | Owner User ID |
| data.createdAt | datetime | 创建时间 |

- **错误码**:

| errorCode | message | 说明 |
|-----------|---------|------|
| 130000 | EmptyOrganizationName | Organization 名称为空 |
| 130001 | OrganizationNameTooShort | Organization 名称长度不足（小于 2 个字符） |
| 130002 | OrganizationNameTooLong | Organization 名称长度超限（超过 50 个字符） |
| 130004 | CreateOrganizationFailed | 创建 Organization 失败（数据库操作异常等） |
| 130012 | ExceedOrgLimit | 当前用户创建的 Organization 数量已达上限 |
| 130013 | OrgAlreadyHasOwner | Organization 已存在 Owner，无法重复指定 |
| 100000 | UnAuthToken | 未提供有效的认证 Token |
| 100001 | EmptyUserId | 无法从 Token 中解析用户 ID |
| 100005 | InvalidUser | 当前用户不存在或已被禁用 |
| 100010 | UnauthorizedOperator | 当前用户无权执行此操作 |
| 999999 | DefaultException | 系统默认异常 |

- **请求示例**:

```json
{
  "name": "示例科技有限公司"
}
```

- **响应示例**:

**成功响应** (HTTP 200):

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 10001,
    "name": "示例科技有限公司",
    "ownerId": 20001,
    "createdAt": "2025-01-15T10:30:00Z"
  }
}
```

**失败响应** (HTTP 200 with error code):

```json
{
  "code": 130000,
  "message": "Organization 名称不能为空",
  "data": null
}
```

**失败响应** (HTTP 401 Unauthorized):

```json
{
  "code": 100000,
  "message": "未认证或 Token 已过期",
  "data": null
}
```

### 15.2. API-002 获取组织信息 (GET /api/user/organization)

- **源文件**: `API/Controllers/UserManagement/OrganizationController.cs:42`
- **鉴权**: 需要认证 (JWT Bearer Token Token)
- **描述**: 根据组织 ID 获取指定 Organization 的详细信息

- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| orgId | long | 否 | Organization 的唯一标识符。若为空，则返回当前用户所属的 Organization 信息 |

- **响应格式**:

| 字段 | 类型 | 说明 |
|------|------|------|
| code | int | 业务状态码，0 表示成功，非 0 表示失败 |
| message | string | 状态描述信息 |
| data | object | 返回的 Organization 数据 |
| data.id | long | Organization 唯一标识符 |
| data.name | string | Organization 名称 |
| data.createdAt | datetime | Organization 创建时间 |
| data.updatedAt | datetime | Organization 更新时间 |

- **错误码**:

| errorCode | message | 说明 |
|-----------|---------|------|
| 100000 | UnAuthToken | Token 无效或未提供 |
| 130003 | InvalidOrganization | 指定的 Organization 不存在或无效 |
| 130009 | UnauthorizedOrganizationAccess | 当前用户无权访问该 Organization |
| 999999 | DefaultException | 服务器内部错误 |

- **请求示例**:

```json
GET /api/user/organization?orgId=10001
Authorization: JWT Bearer Token eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

- **响应示例**:

**成功响应**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 10001,
    "name": "Acme Corporation",
    "createdAt": "2024-01-15T08:30:00Z",
    "updatedAt": "2024-06-20T14:22:00Z"
  }
}
```

**失败响应**:
```json
{
  "code": 130003,
  "message": "InvalidOrganization",
  "data": null
}
```

### 15.3. API-003 更新组织信息 (POST /api/user/organization/update)

- **源文件**: `API/Controllers/UserManagement/OrganizationController.cs:56`
- **鉴权**: 需登录（JWT Bearer Token Token）
- **描述**: 更新现有 Organization 的信息，包括名称、描述等。

- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
| :--- | :--- | :--- | :--- |
| id | long | 是 | 待更新 Organization 的唯一标识符 |
| name | string | 是 | Organization 的新名称，长度需在 2 到 50 个字符之间 |
| description | string | 否 | Organization 的新描述信息 |

- **响应格式**:

| 字段 | 类型 | 说明 |
| :--- | :--- | :--- |
| code | int | 业务状态码，`0` 表示成功，非 `0` 表示失败 |
| message | string | 状态码对应的描述信息 |
| data | object | 更新后的 Organization 数据实体 |

- **错误码**:

| errorCode | message | 说明 |
| :--- | :--- | :--- |
| 100000 | UnAuthToken | Token 无效或未提供 |
| 130000 | EmptyOrganizationName | Organization 名称为空 |
| 130001 | OrganizationNameTooShort | Organization 名称长度过短 |
| 130002 | OrganizationNameTooLong | Organization 名称长度过长 |
| 130003 | InvalidOrganization | 指定的 Organization 不存在或无效 |
| 130005 | UpdateOrganizationFailed | 更新 Organization 失败 |
| 130009 | UnauthorizedOrganizationAccess | 当前用户无权操作该 Organization |
| 999999 | DefaultException | 未知的服务器内部错误 |

- **请求示例**:

```json
{
  "id": 123,
  "name": "新组织名称",
  "description": "这是一个更新后的组织描述。"
}
```

- **响应示例**:

**成功响应**:
```json
{
  "code": 0,
  "message": "Success",
  "data": {
    "id": 123,
    "name": "新组织名称",
    "description": "这是一个更新后的组织描述。"
  }
}
```

**失败响应**（Organization 不存在）:
```json
{
  "code": 130003,
  "message": "InvalidOrganization",
  "data": null
}
```

### 15.4. API-004 删除组织 (POST /api/user/organization/delete)

- **源文件**: `API/Controllers/UserManagement/OrganizationController.cs:71`
- **鉴权**: JWT Bearer Token Token (JWT, HS256)
- **描述**: 根据组织 ID 列表删除一个或多个 Organization。该操作会异步级联删除关联的 Project、Trace 数据及资源。

- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `orgIds` | `string` | 是 | 待删除的组织 ID 列表，多个 ID 以英文逗号 (`,`) 分隔。例如：`"1001,1002"`。 |

- **响应格式**:

| 字段 | 类型 | 说明 |
|---|---|---|
| `code` | `int` | 业务状态码。`0` 表示成功，非 `0` 值表示失败，具体含义见下方错误码表。 |
| `message` | `string` | 接口返回的提示信息。 |
| `data` | `object` | 返回的数据主体。成功时为 `null`。 |

- **错误码**:

| errorCode | message | 说明 |
|---|---|---|
| `0` | `success` | 删除成功。 |
| `100000` | `UnAuthToken` | 用户未认证或 Token 无效。 |
| `130003` | `InvalidOrganization` | 指定的 Organization 不存在或无效。 |
| `130006` | `DeleteOrganizationFailed` | 删除 Organization 失败，请稍后重试。 |
| `130007` | `OrganizationHasProjects` | 该 Organization 下存在未删除的 Project，无法直接删除。 |
| `130008` | `OrganizationProjectDeleting` | 该 Organization 下的 Project 正在删除中，请勿重复操作。 |
| `130009` | `UnauthorizedOrganizationAccess` | 当前用户无权操作该 Organization。 |
| `999999` | `DefaultException` | 系统内部错误。 |

- **请求示例**:

```json
{
  "orgIds": "1001,1002"
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

**失败响应** (Organization 不存在):
```json
{
  "code": 130003,
  "message": "InvalidOrganization",
  "data": null
}
```

---

## 16. BulletinController 接口

本章共覆盖 7 个 HTTP 端点，每个端点一个接口卡片。所有端点均定义于 `API/Controllers/ToolsManagement/BulletinController.cs`，所属项目为 AgentInsightService。

### 16.1. API-032 创建Bulletin (POST /api/tools/bulletin)

- **鉴权**: 无
- **描述**: 创建一条新的Bulletin（Bulletin）记录。
- **所属模块**: `API.Controllers.ToolsManagement.BulletinController`
- **技术栈**: AgentInsightService (AlipaySDKNet.Standard, MediatR)

- **请求参数** (Body, `CreateBulletinBody`):

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `title` | string | 是 | Bulletin标题 |
| `content` | string | 是 | Bulletin内容 |
| `type` | int | 是 | Bulletin类型，参考 `BulletinType` 枚举：`News` (1), `Activity` (2), `Information` (3), `Annoucement` (4), `Advertisement` (5), `Agreement` (9) |
| `status` | int | 否 | Bulletin状态，参考 `BulletinStatus` 枚举：`Draft` (1), `Reviewing` (2), `Revision` (3), `Published` (4), `Expired` (5), `Closed` (6)。默认为 `Draft` (1) |
| `startTime` | datetime? | 否 | Bulletin生效开始时间 |
| `endTime` | datetime? | 否 | Bulletin生效结束时间 |

- **响应格式** (`ApiResponse<long>`):

| 字段 | 类型 | 说明 |
|---|---|---|
| `code` | int | 状态码，`0` 表示成功，非 `0` 表示失败 |
| `message` | string | 状态描述信息 |
| `data` | long | 成功时返回新创建的Bulletin ID |

- **错误码**:

| errorCode | message | 说明 |
|---|---|---|
| `DefaultException` (999999) | 系统错误 | 未预期的服务器内部错误 |
| `UnAuthToken` (100000) | 未认证的Token | 请求未携带有效 Token 或 Token 已过期 |

- **请求示例**:

```json
{
  "title": "系统维护Bulletin",
  "content": "系统将于本周六 22:00 至周日 02:00 进行升级维护。",
  "type": 4,
  "status": 1,
  "startTime": "2024-06-01T00:00:00Z",
  "endTime": "2024-06-30T23:59:59Z"
}
```

- **响应示例**:

**成功响应**:

```json
{
  "code": 0,
  "message": "Success",
  "data": 10001
}
```

**失败响应**:

```json
{
  "code": 999999,
  "message": "系统错误",
  "data": null
}
```

### 16.2. API-045 获取Bulletin协议 (GET /api/tools/bulletin/agreement)

- **鉴权**: 无（接口未标注 `[Authorize]` 特性，为公开访问接口）
- **描述**: 根据Bulletin别名获取协议类Bulletin的详细内容。该接口用于获取 `BulletinType` 为 `Agreement`（协议）类型的Bulletin信息，通常用于展示用户协议、服务条款等法律文档。
- **所属模块**: `API.Controllers.ToolsManagement.BulletinController`
- **技术栈**: AgentInsightService (AlipaySDKNet.Standard, MediatR)

- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| alias | string | 是 | Bulletin别名，用于唯一标识协议Bulletin。该别名在创建Bulletin时生成，用于 URL 友好访问。 |

- **响应格式**:

| 字段 | 类型 | 说明 |
|------|------|------|
| code | int | 业务状态码，`0` 表示成功，非 `0` 表示业务异常 |
| data | object | Bulletin详细数据 |
| data.id | long | Bulletin唯一标识 |
| data.title | string | Bulletin标题 |
| data.content | string | Bulletin正文内容（HTML 格式） |
| data.type | int | Bulletin类型，对应 `BulletinType` 枚举，此处应为 `Agreement = 9` |
| data.status | int | Bulletin状态，对应 `BulletinStatus` 枚举，仅 `Published = 4` 状态的Bulletin可被访问 |
| data.alias | string | Bulletin别名，与请求参数 `alias` 对应 |
| data.publishedAt | datetime | Bulletin发布时间 |
| data.createdAt | datetime | Bulletin创建时间 |
| data.updatedAt | datetime | Bulletin最后更新时间 |
| message | string | 响应消息，成功时为 `"success"`，失败时为错误描述 |

- **错误码**:

| errorCode | message | 说明 |
|-----------|---------|------|
| 999999 | DefaultException | 默认异常，服务器内部错误，请稍后重试 |
| 100000 | UnAuthToken | 未认证的 Token，请求未携带有效的身份凭证 |

- **请求示例**:

```json
GET /api/tools/bulletin/agreement?alias=user-agreement-v2
```

- **响应示例**:

**成功响应**:

```json
{
  "code": 0,
  "data": {
    "id": 1001,
    "title": "AgentInsightService 用户服务协议",
    "content": "<h1>欢迎使用 AgentInsightService</h1><p>本协议由您与 AgentInsightService 共同缔结...</p>",
    "type": 9,
    "status": 4,
    "alias": "user-agreement-v2",
    "publishedAt": "2025-01-15T10:00:00Z",
    "createdAt": "2025-01-10T08:30:00Z",
    "updatedAt": "2025-01-15T10:00:00Z"
  },
  "message": "success"
}
```

**失败响应**:

```json
{
  "code": 999999,
  "data": null,
  "message": "DefaultException: 服务器内部错误，请稍后重试"
}
```

### 16.3. API-xxx（按Controller重新编号） GetBulletins (GET /api/tools/bulletin/bulletins)

- **鉴权**: 无
- **描述**: 分页查询Bulletin列表，支持按Bulletin类型和轮播状态筛选。
- **所属模块**: `API.Controllers.ToolsManagement.BulletinController`
- **技术栈**: AgentInsightService (AlipaySDKNet.Standard, MediatR)

- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| type | BulletinType? | 否 | Bulletin类型，可空枚举。取值：`News`(1)、`Activity`(2)、`Information`(3)、`Annoucement`(4)、`Advertisement`(5)、`Agreement`(9) |
| isCarousel | bool | 否 | 是否仅查询轮播Bulletin，默认 `false` |
| page | int | 否 | 页码，默认 `AgentInsightConst.DefaultPage` |
| page_size | int | 否 | 每页条数，默认 `AgentInsightConst.DefaultPageSize` |

- **响应格式**:

| 字段 | 类型 | 说明 |
|---|---|---|
| code | int | 状态码，`0` 表示成功 |
| message | string | 提示信息 |
| data | object | 分页数据 |
| data.items | array | Bulletin列表 |
| data.items.id | long | Bulletin ID |
| data.items.title | string | Bulletin标题 |
| data.items.content | string | Bulletin内容 |
| data.items.type | int | Bulletin类型，对应 `BulletinType` 枚举值 |
| data.items.isCarousel | bool | 是否为轮播Bulletin |
| data.items.status | int | Bulletin状态，对应 `BulletinStatus` 枚举值 |
| data.items.publishedAt | datetime | 发布时间 |
| data.items.createdAt | datetime | 创建时间 |
| data.total | int | 总记录数 |
| data.page | int | 当前页码 |
| data.page_size | int | 每页条数 |

- **错误码**:

| errorCode | message | 说明 |
|---|---|---|
| 0 | Success | 请求成功 |
| 999999 | DefaultException | 服务器内部异常，请稍后重试 |

- **请求示例**:

```json
GET /api/tools/bulletin/bulletins?type=1&isCarousel=false&page=1&page_size=10
```

- **响应示例**:

**成功响应**:

```json
{
  "code": 0,
  "message": "Success",
  "data": {
    "items": [
      {
        "id": 1,
        "title": "系统升级通知",
        "content": "系统将于本周六进行升级维护。",
        "type": 1,
        "isCarousel": false,
        "status": 4,
        "publishedAt": "2025-01-15T10:00:00Z",
        "createdAt": "2025-01-10T08:30:00Z"
      }
    ],
    "total": 1,
    "page": 1,
    "page_size": 10
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

### 16.4. API-082 GetBackendBulletins (GET /api/tools/bulletin/backend)

- **鉴权**: 无
- **描述**: 获取后端Bulletin列表，支持按Bulletin类型和状态筛选，并分页返回。
- **所属模块**: `API.Controllers.ToolsManagement.BulletinController`
- **技术栈**: AgentInsightService (AlipaySDKNet.Standard, MediatR)

- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| type | BulletinType? | 否 | Bulletin类型，可空。可选值：`News` (1)、`Activity` (2)、`Information` (3)、`Annoucement` (4)、`Advertisement` (5)、`Agreement` (9) |
| status | BulletinStatus? | 否 | Bulletin状态，可空。可选值：`Draft` (1)、`Reviewing` (2)、`Revision` (3)、`Published` (4)、`Expired` (5)、`Closed` (6) |
| page | int | 否 | 页码，默认值为 `AgentInsightConst.DefaultPage` |
| page_size | int | 否 | 每页条数，默认值为 `AgentInsightConst.DefaultPageSize` |

- **响应格式**:

| 字段 | 类型 | 说明 |
|---|---|---|
| code | int | 状态码，`0` 表示成功 |
| message | string | 提示信息 |
| data | object | 返回数据 |
| data.items | array | Bulletin列表，元素为Bulletin对象 |
| data.items.id | string | Bulletin ID |
| data.items.title | string | Bulletin标题 |
| data.items.content | string | Bulletin内容 |
| data.items.type | BulletinType | Bulletin类型 |
| data.items.status | BulletinStatus | Bulletin状态 |
| data.items.createdAt | datetime | 创建时间 |
| data.items.updatedAt | datetime | 更新时间 |
| data.total | int | 总记录数 |
| data.page | int | 当前页码 |
| data.page_size | int | 每页条数 |

- **错误码**:

| errorCode | message | 说明 |
|---|---|---|
| 999999 | DefaultException | 默认异常，未预期的错误 |
| 100000 | UnAuthToken | 未认证的 Token |

- **请求示例**:

```json
GET /api/tools/bulletin/backend?type=1&status=4&page=1&page_size=10
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
        "id": "b1a2c3d4-e5f6-7890-abcd-ef1234567890",
        "title": "系统升级通知",
        "content": "系统将于本周六进行升级维护。",
        "type": 1,
        "status": 4,
        "createdAt": "2025-01-15T10:00:00Z",
        "updatedAt": "2025-01-15T10:00:00Z"
      }
    ],
    "total": 1,
    "page": 1,
    "page_size": 10
  }
}
```

**失败响应**:

```json
{
  "code": 100000,
  "message": "未认证的 Token",
  "data": null
}
```

### 16.5. API-096 ApproveBulletin (POST /api/tools/bulletin/approve)

- **鉴权**: 无
- **描述**: 根据Bulletin ID 列表批量审核通过Bulletin。
- **所属模块**: `API.Controllers.ToolsManagement.BulletinController`
- **技术栈**: AgentInsightService (AlipaySDKNet.Standard, MediatR)

- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| ids | string | 是 | 待审核通过的Bulletin ID 列表，多个 ID 使用英文逗号（,）分隔。 |

- **响应格式**:

| 字段 | 类型 | 说明 |
|------|------|------|
| code | int | 业务状态码，`0` 表示成功，非 `0` 表示失败。 |
| data | object | 响应数据。 |
| data.isSuccess | boolean | 操作是否成功。 |
| message | string | 提示信息。 |
| errors | object | 错误详情，仅在失败时返回。 |
| traceId | string | 请求Trace ID，用于日志排查。 |

- **错误码**:

| errorCode | message | 说明 |
|-----------|---------|------|
| 0 | 操作成功 | 请求成功。 |
| 999999 | DefaultException | 服务器内部异常。 |
| 100000 | UnAuthToken | 用户未认证或 Token 无效。 |

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
  "data": {
    "isSuccess": true
  },
  "message": "操作成功",
  "traceId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

**失败响应**

```json
{
  "code": 999999,
  "data": null,
  "message": "服务器内部异常",
  "errors": {
    "message": "An error occurred while processing your request."
  },
  "traceId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

### 16.6. API-110 ReviseBulletin (POST /api/tools/bulletin/revision)

- **鉴权**: 无
- **描述**: 将指定Bulletin（Bulletin）的状态更新为 Revision（待修订），用于Bulletin内容需修改时退回修订流程。
- **所属模块**: `API.Controllers.ToolsManagement.BulletinController`
- **技术栈**: AgentInsightService (AlipaySDKNet.Standard, MediatR)

- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| ids | string | 是 | 待修订的Bulletin ID 列表，多个 ID 以逗号分隔。例如：`"1001,1002,1003"` |

- **响应格式**:

| 字段 | 类型 | 说明 |
|---|---|---|
| code | int | 业务状态码。`0` 表示成功，非 `0` 表示失败（对应错误码清单中的数值） |
| message | string | 提示信息。成功时为 `"success"`，失败时为具体错误描述 |
| data | object/null | 成功时返回 `null`，失败时为 `null` |

- **错误码**:

| errorCode | message | 说明 |
|---|---|---|
| 0 | success | 操作成功 |
| 100000 | UnAuthToken | 未认证的 Token 或 Token 无效 |
| 999999 | DefaultException | 服务器内部异常，请稍后重试 |

- **请求示例**:

```json
{
  "ids": "1001,1002,1003"
}
```

- **响应示例**:

成功响应：
```json
{
  "code": 0,
  "message": "success",
  "data": null
}
```

失败响应（未认证）：
```json
{
  "code": 100000,
  "message": "UnAuthToken",
  "data": null
}
```

### 16.7. API-124 CloseBulletin (POST /api/tools/bulletin/close)

- **鉴权**: 需要 JWT JWT Bearer Token Token（Controller类 `BulletinController` 标注 `[Authorize]`，继承自 `ApiControllerBase`）
- **描述**: 根据指定的Bulletin ID 列表关闭Bulletin，将Bulletin状态更新为 `Closed`（`BulletinStatus.Closed = 6`）。该操作通常用于下架或终止已发布的Bulletin。
- **所属模块**: `API.Controllers.ToolsManagement.BulletinController`
- **技术栈**: AgentInsightService (AlipaySDKNet.Standard, MediatR)

#### 16.7.1. 请求参数

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| ids | string | 是 | 待关闭的Bulletin ID 列表，多个 ID 使用英文逗号 `,` 分隔。例如：`1,2,3`。该参数通过 Query String 传递。 |

#### 16.7.2. 响应格式

| 字段 | 类型 | 说明 |
|------|------|------|
| code | int | 业务状态码。`0` 表示成功，非 `0` 表示失败（见错误码表）。 |
| message | string | 提示信息。成功时为 `"success"`，失败时为具体错误描述。 |
| data | object | 响应数据。成功时返回 `null`，失败时通常为 `null`。 |

#### 16.7.3. 错误码

| errorCode | message | 说明 |
|-----------|---------|------|
| 0 | success | Bulletin关闭成功 |
| 100000 | UnAuthToken | 未提供或提供了无效的 JWT Token，认证失败 |
| 999999 | DefaultException | 服务器内部错误，未预期的异常 |
| 160000 | AlertNotFound | 未找到对应的Bulletin记录（当传入的 `ids` 无效或不存在时可能返回） |

#### 16.7.4. 请求示例

```json
POST /api/tools/bulletin/close?ids=1,2,3
Content-Type: application/json
Authorization: JWT Bearer Token <your_jwt_token>
```

#### 16.7.5. 响应示例

**成功响应 (HTTP 200)**

```json
{
  "code": 0,
  "message": "success",
  "data": null
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

---

## 17. HealthController 接口

本章共覆盖 1 个 HTTP 端点，每个端点一个接口卡片。

### 17.1. API-xxx（按Controller重新编号） 健康检查 (GET /api/tools/health)

- **鉴权**: 无
- **描述**: 用于检查 AgentInsightService 服务是否正常运行，返回服务健康状态。
- **请求参数**: 无
- **响应格式**:

| 字段 | 类型 | 说明 |
|---|---|---|
| status | string | 服务健康状态，固定为 `"Healthy"` |
| timestamp | string | 服务器当前时间，ISO 8601 格式 (UTC) |
| version | string | AgentInsightService 当前版本号 |

- **错误码**:

| errorCode | message | 说明 |
|---|---|---|
| `999999` | `DefaultException` | 服务内部发生未处理的异常，无法返回健康状态 |

- **请求示例**:

```json
GET /api/tools/health
```

- **响应示例**:

```json
// 成功响应 (HTTP 200)
{
  "status": "Healthy",
  "timestamp": "2025-04-10T12:00:00Z",
  "version": "1.0.0"
}
```

```json
// 失败响应 (HTTP 500)
{
  "errorCode": 999999,
  "message": "DefaultException",
  "details": "An unexpected error occurred while processing the health check request."
}
```

---

## 18. LiteralRoute 接口

本章覆盖 LiteralRoute 相关的 2 个 HTTP 端点，每个端点一个接口卡片。

### 18.1. API-xxx（按Controller重新编号） LiteralRoute 端点 (GET /api/user)

- **鉴权**: 无（根据代码仓库，该端点未Config认证中间件，但建议核实是否应启用 JWT 或 API Key 认证）
- **描述**: 该接口为 `UserController` Controller中的 `Get` 方法（参见 `API/Controllers/UserController.cs`），对应源码中 LiteralRoute 定义的路由 `/api/user`。该接口用于获取用户信息，是 AgentInsightService 对外暴露的用户管理入口。

- **请求参数**: 无（该接口不绑定特定请求参数）

- **响应格式**:

| 字段 | 类型 | 说明 |
|---|---|---|
| traceId | string | 请求Trace ID，用于链路Trace |
| data | object | 响应数据，当前为 null（实际可能返回用户对象，待确认） |
| code | integer | 业务状态码，0 表示成功 |
| message | string | 提示信息，成功时为 "ok" |
| timestamp | string | 服务器响应时间 (ISO 8601 格式) |

- **错误码**:

| errorCode | message | 说明 |
|---|---|---|
| 999999 | DefaultException | 服务器内部异常，通用兜底错误码 |
| 100000 | UnAuthToken | 未认证的 Token，当请求未携带有效身份凭证时返回（注：与鉴权“无”矛盾，建议核实） |

- **请求示例**:

```json
{}
```

- **响应示例**:

成功响应示例:

```json
{
  "traceId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "data": null,
  "code": 0,
  "message": "ok",
  "timestamp": "2025-01-15T10:30:00Z"
}
```

失败响应示例 (服务器内部异常):

```json
{
  "traceId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "data": null,
  "code": 999999,
  "message": "DefaultException",
  "timestamp": "2025-01-15T10:30:00Z"
}
```

### 18.2. API-002 LiteralRoute 端点 (POST /api/user)

- **鉴权**: 无（根据代码仓库，该端点未Config认证中间件，但建议核实是否应启用 JWT 或 API Key 认证）
- **描述**: 该接口为 `UserController` Controller中的 `Create` 方法（参见 `API/Controllers/UserController.cs`），对应源码中 LiteralRoute 定义的路由 `/api/user`。该接口用于创建新用户，是 AgentInsightService 对外暴露的用户管理入口。

- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| mobile | string | 是 | 用户手机号，需符合中国大陆手机号格式（如 13800138000） |
| password | string | 是 | 用户密码，长度至少 6 位 |

- **响应格式**:

| 字段 | 类型 | 说明 |
|---|---|---|
| traceId | string | 请求Trace ID，用于链路Trace |
| data | object | 响应数据，当前为 null（实际可能返回创建的用户对象，待确认） |
| code | integer | 业务状态码，0 表示成功 |
| message | string | 提示信息，成功时为 "ok" |
| timestamp | string | 服务器响应时间 (ISO 8601 格式) |

- **错误码**:

| errorCode | message | 说明 |
|---|---|---|
| 999999 | DefaultException | 服务器内部异常，通用兜底错误码 |
| 100000 | UnAuthToken | 未认证的 Token，当请求未携带有效身份凭证时返回（注：与鉴权“无”矛盾，建议核实） |
| 100001 | EmptyUserId | User ID 为空 |
| 100003 | ExistedMobile | 手机号已存在 |
| 100004 | CreateUserFailed | 创建用户失败 |
| 100005 | InvalidUser | 无效用户 |
| 100009 | EmptyMobile | 手机号为空 |

- **请求示例**:

```json
{
  "mobile": "13800138000",
  "password": "123456"
}
```

- **响应示例**:

成功响应示例:

```json
{
  "traceId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "data": null,
  "code": 0,
  "message": "ok",
  "timestamp": "2025-01-15T10:30:00Z"
}
```

失败响应示例 (手机号已存在):

```json
{
  "traceId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "data": null,
  "code": 100003,
  "message": "ExistedMobile",
  "timestamp": "2025-01-15T10:30:00Z"
}
```

---

## 19. MetricsController 接口

本章共覆盖 4 个 HTTP 端点，每个端点一个接口卡片。

### 19.1. API-034 GetObservations (GET /api/data/metrics/observations)

- **鉴权**: 无 `[Authorize]` 注解，无需鉴权
- **描述**: 分页查询 Observation 列表，用于获取 AgentInsightService 中 Agent 运行产生的Observation数据（如 Token 消耗、延迟、成本等指标）。
- **来源**: `API/Controllers/DataManagement/MetricsController.cs:34`

- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| id | string | 是 | 查询目标 ID，用于定位 Observation 所属的 Trace 或 Session |
| page | int | 否 | 页码，默认值为 `AgentInsightConst.DefaultPage` |
| pagesize | int | 否 | 每页条数，默认值为 `AgentInsightConst.DefaultPageSize` |

- **响应格式**:

| 字段 | 类型 | 说明 |
|---|---|---|
| code | int | 状态码，`0` 表示成功，非 `0` 表示失败 |
| data | object | 响应数据 |
| data.items | array | Observation 列表 |
| data.items[].id | string | Observation 唯一标识 |
| data.items[].traceId | string | 关联的 Trace ID |
| data.items[].sessionId | string | 关联的 Session ID |
| data.items[].timestamp | datetime | Observation时间戳 |
| data.items[].inputTokens | int | 输入 Token 数 |
| data.items[].outputTokens | int | 输出 Token 数 |
| data.items[].totalTokens | int | 总 Token 数 |
| data.items[].inputCost | decimal | 输入成本 |
| data.items[].outputCost | decimal | 输出成本 |
| data.items[].totalCost | decimal | 总成本 |
| data.items[].latency | decimal | 延迟（毫秒） |
| data.items[].level | string | 日志级别（如 Information、Warning、Error） |
| data.items[].warningCount | int | 警告数量 |
| data.items[].errorCount | int | 错误数量 |
| data.items[].modelNames | array | 使用的模型名称列表 |
| data.items[].scoresAvg | decimal | 平均Score |
| data.total | int | 总记录数 |
| data.page | int | 当前页码 |
| data.pagesize | int | 每页条数 |
| message | string | 提示信息 |

- **错误码**:

| errorCode | message | 说明 |
|---|---|---|
| 100000 | UnAuthToken | 未认证的 Token |
| 150009 | EmptyTraceIds | Trace ID 列表为空 |
| 150010 | ClickHouseQueryError | ClickHouse 查询失败 |
| 150011 | TooManyTraceIds | Trace ID 数量超过限制 |
| 150012 | InvalidFilterType | 无效的筛选类型 |
| 150013 | InvalidFilterColumn | 无效的筛选列 |
| 150014 | InvalidFilterOperator | 无效的筛选操作符 |
| 150015 | InvalidFilterValue | 无效的筛选值 |
| 150016 | InvalidOrderBy | 无效的排序字段 |
| 150017 | ClickHouseQueryTimeout | ClickHouse 查询超时 |
| 150018 | EmptyTraceId | Trace ID 为空 |
| 150019 | OrgAndProjectBothEmpty | 组织和项目 ID 均为空 |
| 999999 | DefaultException | 默认异常 |

- **请求示例**:

```json
{
  "id": "trace_8a7f8c2e1b3d4f5a9c6d7e8f9a0b1c2d",
  "page": 1,
  "pagesize": 20
}
```

- **响应示例**:

**成功响应:**

```json
{
  "code": 0,
  "data": {
    "items": [
      {
        "id": "obs_001",
        "traceId": "trace_8a7f8c2e1b3d4f5a9c6d7e8f9a0b1c2d",
        "sessionId": "session_abc123",
        "timestamp": "2025-01-15T10:30:00Z",
        "inputTokens": 1250,
        "outputTokens": 320,
        "totalTokens": 1570,
        "inputCost": 0.0025,
        "outputCost": 0.0016,
        "totalCost": 0.0041,
        "latency": 850.5,
        "level": "Information",
        "warningCount": 0,
        "errorCount": 0,
        "modelNames": ["gpt-4o"],
        "scoresAvg": 0.95
      }
    ],
    "total": 1,
    "page": 1,
    "pagesize": 20
  },
  "message": "success"
}
```

**失败响应 (ClickHouseQueryError):**

```json
{
  "code": 150010,
  "data": null,
  "message": "ClickHouse 查询失败，请检查查询条件或稍后重试"
}
```

### 19.2. API-050 GetScores (GET /api/data/metrics/scores)

- **鉴权**: 需要 JWT 认证 (JWT Bearer Token Token)，基于 `JWTSettings` Config，使用 HS256 算法，Token 有效期 43200 分钟。
- **描述**: 根据指定的 Trace ID 分页查询 Score 数据列表。
- **来源**: `API/Controllers/DataManagement/MetricsController.cs:50`

- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `id` | string | 是 | Trace ID，用于定位特定的 Trace 及其关联的 Score 数据 |
| `page` | int | 否 | 页码，从 1 开始，默认值为 `AgentInsightConst.DefaultPage` |
| `pagesize` | int | 否 | 每页条数，默认值为 `AgentInsightConst.DefaultPageSize` |

- **响应格式**:

| 字段 | 类型 | 说明 |
|---|---|---|
| `code` | int | 业务状态码，`0` 表示成功，非 `0` 表示失败 |
| `data` | object | 响应数据，包含分页结果 |
| `data.items` | array | Score 数据列表 |
| `data.items[].id` | string | Score 记录 ID |
| `data.items[].traceId` | string | 关联的 Trace ID |
| `data.items[].name` | string | Score 名称 |
| `data.items[].value` | number | Score 数值 |
| `data.items[].timestamp` | datetime | Score 记录时间戳 |
| `data.total` | int | 符合条件的总记录数 |
| `data.page` | int | 当前页码 |
| `data.pagesize` | int | 当前页大小 |
| `message` | string | 状态描述信息 |

- **错误码**:

| errorCode | message | 说明 |
|---|---|---|
| `100000` | UnAuthToken | 未提供或提供了无效的认证 Token |
| `150000` | EmptyProjectId | Project ID 为空 |
| `150009` | EmptyTraceIds | Trace ID 列表为空 |
| `150010` | ClickHouseQueryError | ClickHouse 查询执行失败 |
| `150011` | TooManyTraceIds | Trace ID 数量超出限制 |
| `150017` | ClickHouseQueryTimeout | ClickHouse 查询超时 |
| `150018` | EmptyTraceId | Trace ID 为空 |
| `999999` | DefaultException | 未预期的系统异常 |

- **请求示例**:

```json
GET /api/data/metrics/scores?id=trace_8a7f8c9d0e1f2a3b4c5d6e7f&page=1&pagesize=20
```

- **响应示例**:

**成功响应**:

```json
{
  "code": 0,
  "data": {
    "items": [
      {
        "id": "score_001",
        "traceId": "trace_8a7f8c9d0e1f2a3b4c5d6e7f",
        "name": "relevance",
        "value": 0.95,
        "timestamp": "2025-01-15T10:30:00Z"
      },
      {
        "id": "score_002",
        "traceId": "trace_8a7f8c9d0e1f2a3b4c5d6e7f",
        "name": "accuracy",
        "value": 0.88,
        "timestamp": "2025-01-15T10:30:05Z"
      }
    ],
    "total": 2,
    "page": 1,
    "pagesize": 20
  },
  "message": "success"
}
```

**失败响应**:

```json
{
  "code": 150018,
  "data": null,
  "message": "EmptyTraceId"
}
```

### 19.3. API-064 GetTraces (GET /api/data/metrics/traces)

- **鉴权**: 无（代码中未标注 `[Authorize]` 特性）
- **描述**: 根据 Trace ID 列表查询 Trace 详情数据，返回匹配的 Trace 记录集合。
- **来源**: `API/Controllers/DataManagement/MetricsController.cs:64`

- **请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| ids | string | 是 | 逗号分隔的 Trace ID 列表，用于指定要查询的 Trace。示例：`"trace-001,trace-002"` |

- **响应格式**:

| 字段 | 类型 | 说明 |
|------|------|------|
| traceId | string | Trace 的唯一标识符 |
| timestamp | datetime | Trace 的开始时间戳 |
| name | string | Trace 的名称 |
| duration | number | Trace 的持续时间（毫秒） |
| status | string | Trace 的状态（如 `SUCCESS`、`ERROR`） |
| userId | string | 关联的用户 ID |
| sessionId | string | 关联的 Session ID |
| inputTokens | number | 输入 Token 数量 |
| outputTokens | number | 输出 Token 数量 |
| totalTokens | number | Token 总数量 |
| inputCost | number | 输入成本 |
| outputCost | number | 输出成本 |
| totalCost | number | 总成本 |
| modelNames | array | 使用的模型名称列表 |
| tags | array | 关联的标签列表 |
| bookmarked | boolean | 是否被标记收藏 |
| environment | string | 环境标识（如 `DEVELOPMENT`、`PRODUCTION`） |
| version | string | 版本号 |
| release | string | 发布标识 |
| level | string | 日志级别 |
| warningCount | number | 警告数量 |
| errorCount | number | 错误数量 |
| scoresAvg | number | 平均Score |

- **错误码**:

| errorCode | message | 说明 |
|-----------|---------|------|
| 150009 | EmptyTraceIds | Trace ID 列表为空，未提供任何 `ids` 参数值 |
| 150010 | ClickHouseQueryError | ClickHouse 查询执行失败，可能由于数据库连接异常或查询语法错误 |
| 150011 | TooManyTraceIds | Trace ID 数量超出单次查询允许的上限，请分批查询 |
| 150017 | ClickHouseQueryTimeout | ClickHouse 查询超时，请缩小查询范围或稍后重试 |
| 150018 | EmptyTraceId | 提供的 Trace ID 为空或格式无效 |
| 100000 | UnAuthToken | 未提供有效的身份认证 Token |
| 999999 | DefaultException | 服务器内部未预期异常，请稍后重试或联系支持团队 |

- **请求示例**:

```json
{
  "ids": "trace-001,trace-002,trace-003"
}
```

- **响应示例**:

**成功响应 (HTTP 200)**:

```json
{
  "code": 200,
  "message": "success",
  "data": [
    {
      "traceId": "trace-001",
      "timestamp": "2025-06-10T10:30:00Z",
      "name": "AgentInsight-Trace-001",
      "duration": 1250,
      "status": "SUCCESS",
      "userId": "user-123",
      "sessionId": "session-456",
      "inputTokens": 1500,
      "outputTokens": 800,
      "totalTokens": 2300,
      "inputCost": 0.015,
      "outputCost": 0.008,
      "totalCost": 0.023,
      "modelNames": ["gpt-4o"],
      "tags": ["production", "test"],
      "bookmarked": false,
      "environment": "PRODUCTION",
      "version": "1.0.0",
      "release": "release-1.0",
      "level": "INFO",
      "warningCount": 2,
      "errorCount": 0,
      "scoresAvg": 0.95
    }
  ]
}
```

**失败响应 (HTTP 400)**:

```json
{
  "code": 150009,
  "message": "EmptyTraceIds",
  "data": null
}
```

### 19.4. API-xxx（按Controller重新编号） GetTraces (POST /api/data/metrics/traces)

- **鉴权**: 无 `[Authorize]` 注解，无需鉴权
- **描述**: 根据 TraceMetricsBody 中的筛选条件、排序规则和分页参数，从 ClickHouse 查询 Trace 列表数据。
- **来源**: `API/Controllers/DataManagement/MetricsController.cs:125`

- **请求参数**:

  | 字段 | 类型 | 必填 | 说明 |
  |---|---|---|---|
  | projectId | long | 是 | Project ID，用于限定查询范围 |
  | organizationId | long | 否 | Org ID，用于限定查询范围 |
  | traceIds | string[] | 否 | 指定的 Trace ID 列表，用于精确查询 |
  | filter | object | 否 | 筛选条件组，包含多个筛选条件 |
  | filter.type | FilterType | 是 | 筛选类型，可选值：DateTime = 1, String = 2, Number = 3, StringOptions = 4, ArrayOptions = 5, Boolean = 6, Null = 7 |
  | filter.column | FilterColumn | 是 | 筛选字段，可选值：Id = 1, Name = 2, Timestamp = 3, UserId = 4, SessionId = 5, Environment = 6, Version = 7, Release = 8, Tags = 9, Bookmarked = 10, Latency = 11, InputTokens = 12, OutputTokens = 13, TotalTokens = 14, Tokens = 15, InputCost = 16, OutputCost = 17, TotalCost = 18, Level = 19, WarningCount = 20, ErrorCount = 21, DefaultCount = 22, DebugCount = 23, ModelNames = 24, ScoresAvg = 25 |
  | filter.operator | FilterOperator | 是 | 筛选操作符，可选值：GreaterThan = 1, LessThan = 2, GreaterThanOrEqualTo = 3, LessThanOrEqualTo = 4, EqualTo = 5, Contains = 6, DoesNotContain = 7, StartsWith = 8, EndsWith = 9, AnyOf = 10, NoneOf = 11, AllOf = 12, NotEqualTo = 13, IsNull = 14, IsNotNull = 15 |
  | filter.value | object | 是 | 筛选值，根据 type 和 operator 的不同而变化 |
  | orderBy | object | 否 | 排序规则组 |
  | orderBy.column | FilterColumn | 是 | 排序字段，可选值同上 |
  | orderBy.descending | boolean | 是 | 是否降序排序 |
  | page | integer | 是 | 页码，从 1 开始 |
  | page_size | integer | 是 | 每页条数 |

- **响应格式**:

  | 字段 | 类型 | 说明 |
  |---|---|---|
  | code | integer | 状态码，0 表示成功，非 0 表示失败 |
  | message | string | 状态消息 |
  | data | object | 响应数据 |
  | data.items | array | Trace 列表 |
  | data.items[].id | string | Trace ID |
  | data.items[].name | string | Trace 名称 |
  | data.items[].timestamp | datetime | 时间戳 |
  | data.items[].userId | string | User ID |
  | data.items[].sessionId | string | Session ID |
  | data.items[].environment | string | 环境 |
  | data.items[].version | string | 版本 |
  | data.items[].release | string | 发布版本 |
  | data.items[].tags | string[] | 标签 |
  | data.items[].bookmarked | boolean | 是否收藏 |
  | data.items[].latency | number | 延迟（毫秒） |
  | data.items[].inputTokens | integer | 输入 Token 数 |
  | data.items[].outputTokens | integer | 输出 Token 数 |
  | data.items[].totalTokens | integer | 总 Token 数 |
  | data.items[].inputCost | number | 输入成本 |
  | data.items[].outputCost | number | 输出成本 |
  | data.items[].totalCost | number | 总成本 |
  | data.items[].level | string | 日志级别 |
  | data.items[].warningCount | integer | 警告数量 |
  | data.items[].errorCount | integer | 错误数量 |
  | data.items[].modelNames | string[] | 模型名称列表 |
  | data.items[].scoresAvg | number | 平均得分 |
  | data.total | integer | 总条数 |
  | data.page | integer | 当前页码 |
  | data.page_size | integer | 每页条数 |

- **错误码**:

  | errorCode | message | 说明 |
  |---|---|---|
  | 100000 | UnAuthToken | Token 无效或未提供 |
  | 150000 | EmptyProjectId | Project ID 为空 |
  | 150009 | EmptyTraceIds | Trace ID 列表为空 |
  | 150010 | ClickHouseQueryError | ClickHouse 查询错误 |
  | 150011 | TooManyTraceIds | Trace ID 数量过多 |
  | 150012 | InvalidFilterType | 无效的筛选类型 |
  | 150013 | InvalidFilterColumn | 无效的筛选字段 |
  | 150014 | InvalidFilterOperator | 无效的筛选操作符 |
  | 150015 | InvalidFilterValue | 无效的筛选值 |
  | 150016 | InvalidOrderBy | 无效的排序规则 |
  | 150017 | ClickHouseQueryTimeout | ClickHouse 查询超时 |
  | 150018 | EmptyTraceId | Trace ID 为空 |
  | 150019 | OrgAndProjectBothEmpty | Org ID 和项目 ID 均为空 |
  | 999999 | DefaultException | 默认异常 |

- **请求示例**:

  ```json
  {
    "projectId": 12345,
    "organizationId": 67890,
    "traceIds": ["trace-id-001", "trace-id-002"],
    "filter": {
      "type": 1,
      "column": 3,
      "operator": 5,
      "value": "2024-01-01T00:00:00Z"
    },
    "orderBy": {
      "column": 3,
      "descending": true
    },
    "page": 1,
    "page_size": 20
  }
  ```

- **响应示例**:

  ```json
  // 成功响应
  {
    "code": 0,
    "message": "success",
    "data": {
      "items": [
        {
          "id": "trace-id-001",
          "name": "Trace 示例",
          "timestamp": "2024-01-01T00:00:00Z",
          "userId": "user-001",
          "sessionId": "session-001",
          "environment": "production",
          "version": "1.0.0",
          "release": "release-1",
          "tags": ["tag1", "tag2"],
          "bookmarked": false,
          "latency": 150.5,
          "inputTokens": 1000,
          "outputTokens": 500,
          "totalTokens": 1500,
          "inputCost": 0.01,
          "outputCost": 0.02,
          "totalCost": 0.03,
          "level": "INFO",
          "warningCount": 1,
          "errorCount": 0,
          "modelNames": ["gpt-4"],
          "scoresAvg": 0.95
        }
      ],
      "total": 1,
      "page": 1,
      "page_size": 20
    }
  }

  // 失败响应
  {
    "code": 150010,
    "message": "ClickHouseQueryError",
    "data": null
  }
  ```

---

## 20. ModelController 接口

本章共覆盖 1 个 HTTP 端点，每个端点一个接口卡片。

### 20.1. API-034 ModelController.Get (GET /api/data/model)

- **鉴权**: 需要 JWT JWT Bearer Token Token（从代码上下文推断，该Controller位于受保护区域）。同时，系统支持 API Key 认证，具体取决于路由类型（参考 `AgentInsightTransformLogic.DetermineRouteType`）。
- **描述**: 分页查询模型数据列表，支持关键词搜索、项目筛选、预定义模型过滤和排序。数据来源为 ClickHouse 或 PostgreSQL（具体取决于模型存储位置）。
- **所属类**: `ModelController` (`API/Controllers/DataManagement/ModelController.cs:34`)
- **技术栈**: Furion 框架、SqlSugar ORM、MediatR、ClickHouse 客户端

#### 20.1.1. 请求参数

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `keyword` | string | 否 | 搜索关键词，用于模糊匹配模型名称或描述。 |
| `projectid` | string | 否 | 项目ID，按项目筛选模型。若未提供，可能返回空结果或报错（取决于业务逻辑）。 |
| `include_predefined` | boolean | 否 | 是否包含预定义模型，默认 `false`（即默认不包含预定义模型）。 |
| `orderby` | string | 否 | 排序字段，默认 `-updatedat`（按更新时间倒序）。支持字段：`createdat`、`updatedat`、`name` 等，前缀 `-` 表示倒序。 |
| `page` | int | 否 | 页码，默认 `1`，最小值为 `1`。 |
| `page_size` | int | 否 | 每页条数，默认 `20`，最大值为 `100`。 |

#### 20.1.2. 响应格式

| 字段 | 类型 | 说明 |
|---|---|---|
| `code` | int | 状态码，`0` 表示成功，非 `0` 表示失败。 |
| `message` | string | 提示信息。 |
| `data` | object | 分页数据结果。 |
| `data.items` | array | 模型列表，元素为模型对象。 |
| `data.items[].id` | string | 模型ID。 |
| `data.items[].name` | string | 模型名称。 |
| `data.items[].description` | string | 模型描述。 |
| `data.items[].projectid` | string | 所属项目ID。 |
| `data.items[].ispredefined` | boolean | 是否为预定义模型。 |
| `data.items[].createdat` | datetime | 创建时间（ISO 8601 格式）。 |
| `data.items[].updatedat` | datetime | 更新时间（ISO 8601 格式）。 |
| `data.total` | int | 总记录数。 |
| `data.page` | int | 当前页码。 |
| `data.page_size` | int | 每页条数。 |

#### 20.1.3. 错误码

| errorCode | HTTP 状态码 | message | 说明 |
|---|---|---|---|
| `100000` | 401 | `UnAuthToken` | Token 无效或未提供。 |
| `150000` | 400 | `EmptyProjectId` | 项目ID为空。 |
| `140008` | 403 | `UnauthorizedProjectAccess` | 无权访问该项目。 |
| `150010` | 500 | `ClickHouseQueryError` | ClickHouse 查询失败。 |
| `150017` | 500 | `ClickHouseQueryTimeout` | ClickHouse 查询超时。 |
| `999999` | 500 | `DefaultException` | 系统默认异常。 |

#### 20.1.4. 请求示例

GET 请求参数通过 query string 传递，例如：

```
GET /api/data/model?keyword=test-model&projectid=proj_8f7e3a2b1c&include_predefined=false&orderby=-updatedat&page=1&page_size=20
```

#### 20.1.5. 响应示例

**成功响应：**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "id": "model_5d4c3b2a1f",
        "name": "Test Model",
        "description": "A test model for demonstration",
        "projectid": "proj_8f7e3a2b1c",
        "ispredefined": false,
        "createdat": "2025-01-15T10:30:00Z",
        "updatedat": "2025-01-16T14:20:00Z"
      }
    ],
    "total": 1,
    "page": 1,
    "page_size": 20
  }
}
```

**失败响应：**

```json
{
  "code": 150000,
  "message": "EmptyProjectId",
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

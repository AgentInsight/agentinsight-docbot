## 1. 引言

本文档为 AgentInsightService（统一使用全称，首次出现标注品牌名） 系统概要设计说明书。AgentInsightService（统一使用全称，首次出现标注品牌名） 是一个面向可Observation性数据管理与智能分析场景的服务系统，内部品牌名包括 AgentInsight 与 InsightService。系统以 .NET 为主要技术栈，集成 YARP 反向代理、MediatR 命令处理、ClickHouse 列式存储、PostgreSQL 关系数据库及 Redis 消息队列等基础设施，同时包含基于 Python 的 Agents 与 Admin 子项目，形成多语言、多组件的 monorepo 架构。本文档定义系统的模块划分、接口契约、数据模型、安全机制与部署方案等核心设计决策，为开发、测试、运维及后续迭代提供技术依据。

### 1.1. 编写目的

本文档面向 AgentInsightService（统一使用全称，首次出现标注品牌名） 项目的全体利益相关方，包括产品经理、架构师、后端开发工程师、前端开发工程师、测试工程师、运维工程师及项目管理人员。文档旨在达成以下目标：

- **明确系统架构**：定义 AgentInsightService（统一使用全称，首次出现标注品牌名） 的整体架构风格、分层模型与模块边界，使各团队对系统结构形成统一认知。系统采用分层架构，核心服务层位于 `API/Common/Services/`，Handler层位于 `API/Handlers/`，系统基础设施层位于 `API/System/Handlers/`，各层职责清晰、依赖方向明确。
- **指导开发实现**：为开发人员提供模块划分、接口定义、数据模型与关键业务流程的设计约束，确保代码实现与设计决策一致。例如，`PaymentService`（`API/Common/Services/PaymentService.cs:11`）负责Payment核心逻辑，`AlertService`（`API/Common/Services/AlertService.cs:11`）负责Alert条件评估与消息构建，开发人员应遵循既有服务划分原则进行功能扩展。
- **支撑测试验收**：为测试团队提供功能需求、接口契约与验收标准的参考依据，确保测试用例覆盖系统关键路径。文档中引用的 HTTP 端点清单（如 `GET /api/data/model`、`POST /api/alert` 等）与枚举定义（如 `AlertConditionType`、`AlertFrequencyType` 等）均可作为接口测试与错误码验证的基准。
- **保障运维部署**：为运维团队提供部署架构、Config项说明与环境依赖信息，确保系统能够按预期方式部署与运行。Config规格中定义的连接字符串（如 `ConnectionStrings__DefaultConnection`、`ConnectionStrings__ClickHouseConnection`）与安全Config（如 `Security__JwtSecret`）均为部署环境必须提供的参数。

本文档的预期读者应具备分布式系统、RESTful API 设计、关系型数据库与列式存储的基本知识，并熟悉 .NET 与 Python 技术栈。

### 1.2. 项目背景

随着业务规模的持续扩大与数据复杂度的不断上升，传统单体应用在可Observation性数据采集、存储、查询与分析方面面临日益严峻的挑战。Trace、Observation、Score 等多类型可Observation性数据的处理需要高性能的存储引擎与灵活的查询能力，同时用户管理、Payment计费、Alert通知等周边功能也对系统的完整性与可扩展性提出了更高要求。

在此背景下，AgentInsightService（统一使用全称，首次出现标注品牌名） 项目立项启动，项目代号 NostologyService，内部品牌名 AgentInsight、InsightService。系统定位为面向可Observation性数据管理与智能分析的服务平台，旨在提供从数据接入、存储、查询到Alert、报表、计费的端到端解决方案。

当前系统已形成包含多个子项目的 monorepo 代码仓库，包括 `API/`（主服务，基于 .NET）、`Agents/`（Agent服务，基于 Python）、`Admin/`（管理后台，基于 Python Django）、`Entities/`（实体定义）、`Models/`（模型定义）、`Tools/`（工具集）、`Utility/`（通用工具）及 `UnitTest/`（单元测试）等。各子项目在功能上相互协作，共同构成完整的 AgentInsightService（统一使用全称，首次出现标注品牌名） 系统。依赖关系方面，`Admin/requirements.txt` 与 `Agents/requirements.txt` 分别声明了管理后台与Agent服务的 Python 依赖，`Agents/pyproject.toml` 定义了Agent服务的构建Config。

系统在技术选型上采用混合架构：主服务基于 .NET 平台，使用 MediatR CQRS，使用 YARP 作为反向代理处理请求转发与认证，使用 ClickHouse 作为可Observation性数据的列式存储引擎，使用 PostgreSQL 存储业务关系数据，使用 Redis BullMqService与缓存。Agent服务与 Admin 后台基于 Python 生态，使用 openai、pydantic、httpx 等库实现 AI 能力集成与后台管理功能。

### 1.3. 系统范围

AgentInsightService（统一使用全称，首次出现标注品牌名） 系统的范围涵盖整个 monorepo 仓库，仓库内所有子项目均视为系统内的组成部分，而非外部依赖。具体范围如下：

| 子项目 | 目录 | 职责说明 |
|--------|------|----------|
| API 主服务 | `API/` | 提供 RESTful API 接口，包含Controller层（`API/Controllers/`）、Handler层（`API/Handlers/`）、核心服务层（`API/Common/Services/`）与系统基础设施层（`API/System/Handlers/`） |
| Agent服务 | `Agents/` | 基于 Python 的Agent服务，提供 AI 能力集成与自动化任务执行 |
| 管理后台 | `Admin/` | 基于 Django 的管理后台，提供数据管理、产品Config、任务流程管理等能力 |
| 实体定义 | `Entities/` | 定义系统核心实体类，如 `AgentConfig`、`AgentReportTemplate`、`AgentInsightProduct` 等 |
| 模型定义 | `Models/` | DTO与请求/响应模型 |
| 工具集 | `Tools/` | 提供辅助工具与脚本 |
| 通用工具 | `Utility/` | 提供跨模块复用的通用工具类 |
| 单元测试 | `UnitTest/` | 包含系统各模块的单元测试与集成测试 |

**In-Scope（范围内）**：

- 用户管理、组织Privilege管理、Session管理与 Token 生成（`UserService`，`API/Common/Services/UserService.cs:11`）
- Payment核心逻辑，包括订单创建、微信/Payment宝Payment、订单状态更新与签名验证（`PaymentService`，`API/Common/Services/PaymentService.cs:11`）
- 微信生态集成，包括签名验证、AccessToken 管理、微信账号绑定与小程序登录（`WeChatService`，`API/Common/Services/WeChatService.cs:11`）
- Alert条件评估、Alert消息构建与Alert指标查询（`AlertService`，`API/Common/Services/AlertService.cs:11`）
- 基于 Redis 的消息队列服务，用于异步任务处理（`BullMqService`，`API/Common/Services/BullMqService.cs:11`）
- 可Observation性数据查询，包括 Traces、Observations、Scores 的查询与聚合（`MetricsHandler`，`API/Handlers/DataManagement/MetricsHandler.cs:11`）
- Agent Config管理与报表模板管理（`AgentConfigController`、`AgentReportController`）
- 产品管理、订单管理与Alert管理（`ProductController`、`OrderHandler`、`AlertHandler`）
- 反向代理请求转换、认证处理与速率限制（`AgentInsightTransformProvider`，`API/System/Handlers/AgentInsightTransformProvider.cs:11`）

**Out-of-Scope（范围外）**：

- 移动端原生应用（iOS/Android）的开发与维护
- 第三方Payment平台（微信/Payment宝）的底层实现
- 底层基础设施（服务器、网络、存储设备）的硬件选型与采购

### 1.4. 术语与缩略语

本文档涉及以下术语与缩略语，为保持代码标识符与品牌名称的一致性，部分术语保留原文，不做翻译：

| 术语/缩略语 | 说明 |
|-------------|------|
| AgentInsightService（统一使用全称，首次出现标注品牌名） | 系统正式项目名称，本文档描述的目标系统 |
| AgentInsight | 内部品牌名，用于产品命名与标识 |
| InsightService | 内部品牌名，用于服务命名 |
| API | Application Programming Interface，应用程序编程接口 |
| YARP | Yet Another Reverse Proxy，微软开源的 .NET 反向代理库 |
| MediatR | .NET 平台下的中介者模式实现库，用于命令查询职责分离 |
| ClickHouse | 开源列式数据库，用于可Observation性数据的存储与分析 |
| Trace | Trace，指一次请求或事务的完整调用链信息 |
| Observation | Observation，指可Observation性数据中的单个Observation点记录 |
| Score | Score，指对模型输出或任务执行结果的评价分数 |
| PaymentService | Payment服务，负责订单创建、Payment参数生成与订单状态更新 |
| AlertService | Alert服务，负责Alert条件评估、Alert消息构建与Alert指标查询 |
| BullMqService | 基于 Redis 的消息队列服务，用于异步任务处理 |
| Agent | Agent，指系统中可执行特定任务的自动化单元 |
| DTO | Data Transfer Object，数据传输对象 |
| PRD | Product Requirements Document，产品需求文档 |
| AST | Abstract Syntax Tree，抽象语法树 |
| monorepo | 单一代码仓库管理模式，多个子项目共存于同一仓库 |
| Basic Auth | HTTP 基本认证机制 |
| JWT | JSON Web Token，基于 JSON 的开放标准Token格式 |
| API Key | 应用程序编程接口密钥，用于接口访问认证 |
| errorCode | 错误码，接口响应中用于标识错误类型的数值字段 |

### 1.5. 参考文档

本文档的编制参考了以下文档与代码仓库资料：

| 文档/资料 | 说明 |
|-----------|------|
| 架构设计文档 | 描述 AgentInsightService（统一使用全称，首次出现标注品牌名） 系统的整体架构、模块划分与技术选型 |
| PRD | 定义系统的功能需求、非功能需求与验收标准 |
| 代码仓库 AST 扫描结果 | 基于抽象语法树扫描的代码结构分析，包含类定义、方法签名、路由注册等信息 |
| `API/Controllers/AgentManagement/AgentConfigController.cs` | Agent Config管理接口的Controller实现，定义路由 `api/agent/config` 及 Get/Post/Delete 操作 |
| `API/Controllers/AgentManagement/AgentReportController.cs` | Agent 报表管理接口的Controller实现，定义路由 `api/agent/report` 及模板查询、删除、创建/更新操作 |
| `API/Controllers/DataManagement/ModelController.cs` | 模型管理接口的Controller实现，定义路由 `api/data/model` 及模型列表查询操作 |
| `API/Controllers/ProductManagement/ProductController.cs` | 产品管理接口的Controller实现，定义路由 `api/product` 及产品列表、产品时长查询操作 |
| `Admin/Agents.md` | 管理后台Agent任务执行流程规则文档 |
| `Admin/app/admin.py` | Django Admin 后台Config，定义 `AgentConfigAdmin` 与 `AgentReportTemplateAdmin` 管理类 |

### 1.6. 版本历史

| 版本 | 日期 | 修订说明 | 作者 |
|------|------|----------|------|
| v0.1 | 待定 | 初始草案，完成文档框架搭建与章节大纲定义 | 技术文档组 |
| v0.2 | 待定 | 补充项目背景、系统范围与术语定义 | 技术文档组 |
| v0.3 | 待定 | 完成概要设计核心章节（模块设计、接口设计、数据设计） | 技术文档组 |
| v0.4 | 待定 | 补充安全设计、部署方案与运维设计 | 技术文档组 |
| v0.5 | 待定 | 根据代码仓库 AST 扫描结果校准接口清单与枚举定义 | 技术文档组 |
| v0.6 | 待定 | 根据评审意见修订，补充Config规格与依赖关系 | 技术文档组 |
| v0.7 | 待定 | 最终评审，完善格式与引用规范 | 技术文档组 |
| v1.0 | 待定 | 正式发布 | 技术文档组 |

> 注：版本历史中的日期与作者信息将在文档发布前由项目管理人员补充确认。

---

## 2. 系统总体设计

AgentInsightService（统一使用全称，首次出现标注品牌名） 是一个面向 AI Agent 的可Observation性与管理平台，提供 Trace 数据采集与查询、模型成本核算、Alert规则Config、Payment集成、User/Org/项目管理以及微信生态对接等能力。系统采用前后端分离架构，后端由 .NET API 服务与 Python Agent 服务组成，通过 YARP 反向代理统一暴露 API 网关入口，数据层使用 PostgreSQL 与 ClickHouse 分别承载业务数据与可Observation性数据。

### 2.1. 设计目标

系统设计围绕以下核心目标展开：

**统一可Observation性数据接入**：平台需要接收来自不同来源的 Trace 数据，并支持对 Traces、Observations、Scores 三类核心可Observation性数据的查询与聚合分析。`MetricsHandler` 提供了 `GetTraces`、`GetObservationsAsync`、`GetScoresAsync` 等查询方法，支持复杂过滤与排序 [API/Handlers/DataManagement/MetricsHandler.cs]。数据摄入通过 `BullMqService` 的 `EnqueueTraceIngestionAsync` 方法异步入队，避免阻塞主业务流程 [API/Common/Services/BullMqService.cs]。

**多租户组织与Privilege管理**：系统需要支持用户、Org、项目三级资源模型，并在此基础上实现细粒度的Privilege控制。`ApiHandlerBase` 提供了 `RequireOrgMembership`、`RequireOrgAdmin`、`RequireOrgOwner`、`RequireAccessibleProject` 等Privilege验证方法，所有 Handler 均继承自该基类 [API/Handlers/ApiHandlerBase.cs]。`UserService` 负责用户创建、Session管理、Token 生成与组织Privilege获取 [API/Common/Services/UserService.cs]。

系统整体采用分层架构，自上而下分为四层：

| 层级 | 职责 | 技术载体 |
|------|------|----------|
| API 网关层 | 反向代理、认证鉴权、速率限制、路由转发 | YARP 反向代理 + `AgentInsightTransformProvider` |
| 应用服务层 | 业务逻辑编排、请求处理、数据校验 | `API` 子项目（Controllers / Handlers / Services） |
| Agent 服务层 | AI Agent 推理、Session管理、检索增强 | `Agents` 子项目（FastAPI + LangChain + Semantic Kernel） |
| 数据层 | 业务数据、可Observation性数据、缓存与队列 | PostgreSQL + ClickHouse + Redis |

**API 网关层**：`AgentInsightTransformProvider` 实现了 YARP 的 `ITransformProvider` 接口，在请求转发前统一处理认证逻辑。`Apply` 方法根据路由路径调用 `AgentInsightTransformLogic.DetermineRouteType` 判断路由类型，对 Public 路由添加 `/api` 路径前缀，并注册请求转换委托 [API/System/Handlers/AgentInsightTransformProvider.cs]。请求转换委托中，根据 `Authorization` 请求头的类型分发到 `HandleBasicAuthRequest` 或 `HandleJwtAuthRequest` 处理 [API/System/Handlers/AgentInsightTransformProvider.cs]。

**应用服务层**：采用 Controller → Handler → Service 的三级调用链。Controller 层负责 HTTP 协议适配与参数绑定，Handler 层承载业务逻辑与Privilege校验，Service 层实现可复用的领域服务。例如 `AgentConfigController` 通过构造函数注入 `AgentConfigHandler`，在 `Get`、`Post`、`Delete` 方法中调用 Handler 对应方法 [API/Controllers/AgentManagement/AgentConfigController.cs]。`AgentSessionController` 同样通过注入 `AgentSessionHandler` 实现Session的增删改查 [API/Controllers/AgentManagement/AgentSessionController.cs]。

**Agent 服务层**：`Agents` 子项目基于 Python 构建，使用 FastAPI 提供 HTTP Service，集成 LangChain 与 Semantic Kernel 实现 Agent 推理能力。该层通过 `Agents/pyproject.toml` 管理依赖，包含 `openai`、`httpx`、`pydantic`、`pydantic-settings` 等核心库，以及 `LangChain.Providers.OpenAI`、`Microsoft.SemanticKernel` 等 AI 框架。

**数据层**：PostgreSQL 承载用户、Org、Project、订单等业务数据，通过 `ConnectionStrings:UserDb`、`ConnectionStrings:OrderDb`、`ConnectionStrings:AgentDb` 三个连接串分别指向不同的数据库实例。ClickHouse 承载 Trace 等可Observation性数据，连接串为 `ConnectionStrings:ClickHouse`，Config了连接池大小、超时时间等参数。Redis 用于缓存与消息队列，由 `StackExchange.Redis` 客户端访问。

### 2.2. 技术栈选型

系统采用 .NET 与 Python 双语言技术栈，各层根据业务场景选择最合适的实现语言与框架。

**API 层（C# / .NET）**：

| 技术组件 | 用途 | 关键证据 |
|----------|------|----------|
| Yarp.ReverseProxy | API 网关反向代理 | `AgentInsightTransformProvider` 实现 `ITransformProvider` [API/System/Handlers/AgentInsightTransformProvider.cs] |
| MediatR | 进程内消息通知与请求处理 | `PaymentService` 中引入 `MediatR` 命名空间，用于发送Payment事务通知 [API/Common/Services/PaymentService.cs] |
| SqlSugar | ORM 数据访问 | `PaymentService` 构造函数注入 `ISqlSugarClient` 并标记 `[AgentInsightConst.KeyedService_UserDb]` [API/Common/Services/PaymentService.cs] |
| Npgsql | PostgreSQL 驱动 | 通过 `ConnectionStrings:UserDb` 等连接串访问 PostgreSQL |
| StackExchange.Redis | Redis 客户端 | `BullMqService` 基于 Redis 实现消息队列 [API/Common/Services/BullMqService.cs] |
| AlipaySDK.NET.Standard | Payment宝Payment SDK | `PaymentService` 中引入 `Aop.Api`、`Aop.Api.Request`、`Aop.Api.Util` 命名空间 [API/Common/Services/PaymentService.cs] |
| System.Security.Cryptography | 加密算法库 | 用于签名验证与数据加密 |
| My.Extensions.Localization.Json | JSON 本地化资源 | 支持多语言错误消息 |
| Furion | 应用框架 | 提供依赖注入、友好异常、JSON 序列化等能力，`PaymentService` 使用 `Furion.App.HttpContext` [API/Common/Services/PaymentService.cs] |

**Agents Python**：

| 技术组件 | 用途 | 关键证据 |
|----------|------|----------|
| FastAPI | HTTP 服务框架 | `Agents` 子项目基于 FastAPI 构建 |
| LangChain.Providers.OpenAI | LangChain OpenAI 提供程序 | 在 `Agents/pyproject.toml` 中声明 |
| Microsoft.SemanticKernel | Semantic Kernel 框架 | 在 `Agents/pyproject.toml` 中声明 |
| openai | OpenAI Python SDK | 在 `Agents/requirements.txt` 中声明 |
| httpx | HTTP 客户端 | 在 `Agents/requirements.txt` 中声明 |
| pydantic / pydantic-settings | 数据校验与Config管理 | 在 `Agents/requirements.txt` 中声明 |
| agentinsight-sdk | AgentInsight 平台 SDK | 在 `Agents/requirements.txt` 中声明 |

**数据存储选型**：

| 存储 | 用途 | Config项 |
|------|------|--------|
| PostgreSQL | 业务数据（User、Org、Project、Order） | `ConnectionStrings:UserDb`、`ConnectionStrings:OrderDb`、`ConnectionStrings:AgentDb` |
| ClickHouse | 可Observation性数据（Trace、Observation、Score） | `ConnectionStrings:ClickHouse`，Config `MaxConnections=10;MaxExecutionTime=50;ConnectTimeout=30;SocketTimeout=60` |
| Redis | 缓存与消息队列 | 由 `StackExchange.Redis` 客户端访问，`BullMqService` 实现队列操作 |

### 2.3. 设计模式与编码约定

**CQRS 风格分离**：系统在 Controller 与 Service 之间引入 Handler 层，形成 Controller → Handler → Service 的调用链。Controller 仅负责 HTTP 协议适配与参数绑定，不包含业务逻辑；Handler 承载业务用例的编排与Privilege校验；Service 实现可复用的领域服务。以 `AgentConfigController` 为例，其 `Get` 方法直接调用 `_handler.GetConfig()`，`Post` 方法调用 `_handler.CreateOrUpdateConfig(body)`，Controller 本身不包含任何业务实现 [API/Controllers/AgentManagement/AgentConfigController.cs]。

**MediatR 通知处理**：系统使用 MediatR 实现进程内消息通知。`PaymentService` 在Payment事务完成后发送通知，通过 MediatR 的 `IPublisher` 或 `IMediator` 接口将事件分发到对应的 `INotificationHandler` Handler [API/Common/Services/PaymentService.cs]。`API/Notifications/PaymentTransactionNotification.cs` 定义了 `TransactionType` 枚举，标识不同的Payment事务类型。

**Repository 模式**：数据访问通过 Repository 接口抽象，业务层依赖接口而非具体实现。`PaymentService` 构造函数注入 `IOrderRepository`，通过 `_orderRepository.GetByOrderNoAsync(orderNo)` 查询订单 [API/Common/Services/PaymentService.cs]。`UserService` 同样通过注入的仓储接口访问用户数据。

**Handler 基类与Privilege约定**：所有 Handler 继承自 `ApiHandlerBase`，该基类提供用户上下文、数据库访问、Privilege验证等公共能力。Privilege验证方法包括 `RequireOrgMembership`（验证组织成员身份）、`RequireOrgAdmin`（验证组织管理员身份）、`RequireOrgOwner`（验证组织所有者身份）、`RequireAccessibleProject`（验证项目访问Privilege）[API/Handlers/ApiHandlerBase.cs]。

**认证体系约定**：系统支持三种认证方式，由 `AgentInsightTransformProvider` 统一处理：

| 认证方式 | 处理逻辑 | 适用场景 |
|----------|----------|----------|
| Basic Auth | `HandleBasicAuthRequest` 解析 `Authorization: Basic` 头，提取 publicKey 与 secretKey，调用 `ResolveApiKeyWithCache` 验证 API Key | 服务端到服务端调用 |
| JWT（HS256） | `HandleJwtAuthRequest` 解析 JWT Token，验证签名与有效期 | 用户登录后的浏览器/客户端调用 |
| API Key | 通过 Basic Auth 中的 publicKey/secretKey 对映射到 API Key 记录 | 第三方系统集成 |

`AgentInsightTransformProvider` 在 `Apply` 方法中注册请求转换委托，根据 `Authorization` 头的类型分发到对应的处理方法 [API/System/Handlers/AgentInsightTransformProvider.cs]。对于速率限制，`HandleBasicAuthRequest` 中通过 `IUserService.GetCurrentOrgPrivilege` 获取当前组织Privilege，若 `IsRateLimited` 为 true 则返回速率限制响应 [API/System/Handlers/AgentInsightTransformProvider.cs]。

**编码约定**：

1. **异步优先**：所有 I/O 操作使用 `async`/`await`，方法命名以 `Async` 后缀结尾（如 `GetTracesAsync`、`CreateOrUpdateSession`、`DeleteSessions`）[API/Controllers/AgentManagement/AgentSessionController.cs]。
2. **依赖注入**：所有服务通过构造函数注入依赖，禁止在方法内部直接 `new` 服务实例。`AgentConfigController` 通过构造函数注入 `AgentConfigHandler` 与 `IMemoryCache` [API/Controllers/AgentManagement/AgentConfigController.cs]。
3. **统一响应格式**：所有 API 返回 `ApiResponse<T>` 包装类型，包含 `errorCode`、`data`、`totalCount`、`page` 等字段。Controller 方法通过 `Ok(new ApiResponse<T>(...))` 返回 [API/Controllers/AgentManagement/AgentSessionController.cs]。
4. **分页约定**：分页参数使用 `page` 与 `pageSize`，默认值分别为 `AgentInsightConst.DefaultPage` 与 `AgentInsightConst.DefaultPageSize`，通过 `page.GetPageNumber()` 与 `pageSize.GetPageSize()` 转换为实际页码 [API/Controllers/AgentManagement/AgentSessionController.cs]。
5. **路由约定**：Controller 使用 `[Route("api/...")]` 定义路由前缀，通过 `[SwaggerTag]` 标注 Swagger 分组与排序 [API/Controllers/AgentManagement/AgentConfigController.cs]。

---

## 3. 模块划分

<div class="report-image">
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024" width="1024" height="1024">
<defs>
<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
<stop offset="0%" stop-color="#f0f4f8"/>
<stop offset="100%" stop-color="#e2e8f0"/>
</linearGradient>
<linearGradient id="header" x1="0" y1="0" x2="1" y2="0">
<stop offset="0%" stop-color="#007BFF"/>
<stop offset="100%" stop-color="#0056b3"/>
</linearGradient>
<filter id="shadow" x="-5%" y="-5%" width="110%" height="110%">
<feDropShadow dx="0" dy="4" stdDeviation="8" flood-color="#007BFF" flood-opacity="0.15"/>
</filter>
<filter id="shadowSmall" x="-5%" y="-5%" width="110%" height="110%">
<feDropShadow dx="0" dy="2" stdDeviation="4" flood-color="#6c757d" flood-opacity="0.2"/>
</filter>
</defs>
<rect width="1024" height="1024" fill="url(#bg)"/>
<rect x="72" y="56" width="880" height="912" rx="24" fill="#ffffff" filter="url(#shadow)"/>
<rect x="72" y="56" width="880" height="120" rx="24" fill="url(#header)"/>
<rect x="72" y="152" width="880" height="24" fill="url(#header)"/>
<text x="512" y="130" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="42" font-weight="bold" fill="#ffffff" text-anchor="middle" letter-spacing="4">模块划分</text>
<text x="512" y="160" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="16" fill="#cce5ff" text-anchor="middle" letter-spacing="2">模块划分</text>
<rect x="112" y="220" width="800" height="60" rx="30" fill="#e7f1ff" stroke="#007BFF" stroke-width="1.5"/>
<text x="512" y="258" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="20" fill="#0056b3" text-anchor="middle" font-weight="bold">系统整体</text>
<line x1="512" y1="280" x2="512" y2="320" stroke="#6c757d" stroke-width="2" stroke-dasharray="6,4"/>
<circle cx="512" cy="330" r="6" fill="#007BFF"/>
<line x1="512" y1="336" x2="512" y2="360" stroke="#6c757d" stroke-width="2"/>
<rect x="512" y="360" width="2" height="2" fill="#6c757d"/>
<line x1="512" y1="360" x2="176" y2="360" stroke="#6c757d" stroke-width="2"/>
<line x1="512" y1="360" x2="848" y2="360" stroke="#6c757d" stroke-width="2"/>
<line x1="176" y1="360" x2="176" y2="390" stroke="#6c757d" stroke-width="2"/>
<line x1="512" y1="360" x2="512" y2="390" stroke="#6c757d" stroke-width="2"/>
<line x1="848" y1="360" x2="848" y2="390" stroke="#6c757d" stroke-width="2"/>
<rect x="96" y="390" width="160" height="180" rx="12" fill="#ffffff" stroke="#007BFF" stroke-width="2" filter="url(#shadowSmall)"/>
<rect x="96" y="390" width="160" height="44" rx="12" fill="#007BFF"/>
<rect x="96" y="422" width="160" height="12" fill="#007BFF"/>
<text x="176" y="420" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="18" fill="#ffffff" text-anchor="middle" font-weight="bold">模块A</text>
<circle cx="136" cy="466" r="5" fill="#adb5bd"/>
<text x="150" y="471" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="13" fill="#6c757d">功能组件A1</text>
<circle cx="136" cy="500" r="5" fill="#adb5bd"/>
<text x="150" y="505" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="13" fill="#6c757d">功能组件A2</text>
<circle cx="136" cy="534" r="5" fill="#adb5bd"/>
<text x="150" y="539" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="13" fill="#6c757d">功能组件A3</text>
<rect x="432" y="390" width="160" height="180" rx="12" fill="#ffffff" stroke="#007BFF" stroke-width="2" filter="url(#shadowSmall)"/>
<rect x="432" y="390" width="160" height="44" rx="12" fill="#007BFF"/>
<rect x="432" y="422" width="160" height="12" fill="#007BFF"/>
<text x="512" y="420" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="18" fill="#ffffff" text-anchor="middle" font-weight="bold">模块B</text>
<circle cx="472" cy="466" r="5" fill="#adb5bd"/>
<text x="486" y="471" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="13" fill="#6c757d">功能组件B1</text>
<circle cx="472" cy="500" r="5" fill="#adb5bd"/>
<text x="486" y="505" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="13" fill="#6c757d">功能组件B2</text>
<circle cx="472" cy="534" r="5" fill="#adb5bd"/>
<text x="486" y="539" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="13" fill="#6c757d">功能组件B3</text>
<rect x="768" y="390" width="160" height="180" rx="12" fill="#ffffff" stroke="#007BFF" stroke-width="2" filter="url(#shadowSmall)"/>
<rect x="768" y="390" width="160" height="44" rx="12" fill="#007BFF"/>
<rect x="768" y="422" width="160" height="12" fill="#007BFF"/>
<text x="848" y="420" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="18" fill="#ffffff" text-anchor="middle" font-weight="bold">模块C</text>
<circle cx="808" cy="466" r="5" fill="#adb5bd"/>
<text x="822" y="471" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="13" fill="#6c757d">功能组件C1</text>
<circle cx="808" cy="500" r="5" fill="#adb5bd"/>
<text x="822" y="505" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="13" fill="#6c757d">功能组件C2</text>
<circle cx="808" cy="534" r="5" fill="#adb5bd"/>
<text x="822" y="539" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="13" fill="#6c757d">功能组件C3</text>
<line x1="176" y1="570" x2="176" y2="620" stroke="#6c757d" stroke-width="1.5" stroke-dasharray="4,3"/>
<line x1="512" y1="570" x2="512" y2="620" stroke="#6c757d" stroke-width="1.5" stroke-dasharray="4,3"/>
<line x1="848" y1="570" x2="848" y2="620" stroke="#6c757d" stroke-width="1.5" stroke-dasharray="4,3"/>
<rect x="96" y="620" width="160" height="60" rx="8" fill="#f8f9fa" stroke="#adb5bd" stroke-width="1"/>
<text x="176" y="650" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="14" fill="#6c757d" text-anchor="middle">数据接口</text>
<text x="176" y="668" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="12" fill="#adb5bd" text-anchor="middle">API</text>
<rect x="432" y="620" width="160" height="60" rx="8" fill="#f8f9fa" stroke="#adb5bd" stroke-width="1"/>
<text x="512" y="650" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="14" fill="#6c757d" text-anchor="middle">数据接口</text>
<text x="512" y="668" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="12" fill="#adb5bd" text-anchor="middle">API</text>
<rect x="768" y="620" width="160" height="60" rx="8" fill="#f8f9fa" stroke="#adb5bd" stroke-width="1"/>
<text x="848" y="650" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="14" fill="#6c757d" text-anchor="middle">数据接口</text>
<text x="848" y="668" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="12" fill="#adb5bd" text-anchor="middle">API</text>
<line x1="176" y1="680" x2="176" y2="730" stroke="#6c757d" stroke-width="1.5" stroke-dasharray="4,3"/>
<line x1="512" y1="680" x2="512" y2="730" stroke="#6c757d" stroke-width="1.5" stroke-dasharray="4,3"/>
<line x1="848" y1="680" x2="848" y2="730" stroke="#6c757d" stroke-width="1.5" stroke-dasharray="4,3"/>
<rect x="96" y="730" width="160" height="60" rx="8" fill="#e9ecef" stroke="#6c757d" stroke-width="1"/>
<text x="176" y="760" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="14" fill="#495057" text-anchor="middle">共享数据层</text>
<text x="176" y="778" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="12" fill="#6c757d" text-anchor="middle">数据库</text>
<rect x="432" y="730" width="160" height="60" rx="8" fill="#e9ecef" stroke="#6c757d" stroke-width="1"/>
<text x="512" y="760" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="14" fill="#495057" text-anchor="middle">共享数据层</text>
<text x="512" y="778" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="12" fill="#6c757d" text-anchor="middle">数据库</text>
<rect x="768" y="730" width="160" height="60" rx="8" fill="#e9ecef" stroke="#6c757d" stroke-width="1"/>
<text x="848" y="760" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="14" fill="#495057" text-anchor="middle">共享数据层</text>
<text x="848" y="778" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="12" fill="#6c757d" text-anchor="middle">数据库</text>
<line x1="176" y1="790" x2="176" y2="840" stroke="#6c757d" stroke-width="1.5" stroke-dasharray="4,3"/>
<line x1="512" y1="790" x2="512" y2="840" stroke="#6c757d" stroke-width="1.5" stroke-dasharray="4,3"/>
<line x1="848" y1="790" x2="848" y2="840" stroke="#6c757d" stroke-width="1.5" stroke-dasharray="4,3"/>
<rect x="112" y="840" width="800" height="56" rx="28" fill="#f1f3f5" stroke="#adb5bd" stroke-width="1"/>
<text x="512" y="874" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="16" fill="#495057" text-anchor="middle">模块间通信与依赖管理</text>
<circle cx="256" cy="874" r="4" fill="#6c757d"/>
<circle cx="768" cy="874" r="4" fill="#6c757d"/>
<text x="512" y="930" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="13" fill="#adb5bd" text-anchor="middle">高内聚 低耦合</text>
<line x1="412" y1="926" x2="612" y2="926" stroke="#adb5bd" stroke-width="1"/>
<circle cx="412" cy="926" r="3" fill="#adb5bd"/>
<circle cx="612" cy="926" r="3" fill="#adb5bd"/>
</svg>
</div>

AgentInsightService（统一使用全称，首次出现标注品牌名） 是一个面向可Observation性数据领域的Agent服务平台，核心能力包括用户/Org/项目管理、Payment（微信/Payment宝）、Alert、Agent Config、数据查询等。系统采用多模块分层架构，由 API 应用服务模块、Agents Agent服务模块、Admin 后台管理模块、基础设施模块以及数据实体与模型模块组成，各模块职责单一、边界清晰，通过内部 HTTP 接口、共享数据库和 Redis 消息队列进行协作。

### 3.1. 模块清单与职责

AgentInsightService（统一使用全称，首次出现标注品牌名） 的代码仓库按顶层目录划分为多个功能模块，各模块职责如下表所示：

| 模块 | 顶层目录 | 技术栈 | 核心职责 |
|------|---------|--------|----------|
| API 应用服务模块 | `API/` | .NET (C#) | User/Org/项目管理、Payment、Alert、Agent Config、数据查询等核心业务逻辑 |
| Agents Agent服务模块 | `Agents/` | Python (FastAPI) | 提供 OpenAI 兼容 Chat Completions API，支持流式响应、Session管理，使用 LangChain/ 编排 |
| Admin 后台管理模块 | `Admin/` | Python (Django) | 运营管理界面，与 API 共享底层数据库 |
| 基础设施模块 | `API/System/` | .NET (C#) | YARP 反向代理、认证/限流、全局异常处理、Redis 消息队列 |
| 数据实体与模型模块 | `Entities/`、`Models/` | .NET (C#) | 数据库实体定义、枚举、数据传输对象 |

**API 应用服务模块** 是系统的核心业务层，位于 `API/` 目录。该模块采用 Controller-Handler-Service 三层架构：Controller 层负责 HTTP 路由与参数绑定，Handler 层承载业务逻辑编排，Service 层提供可复用的核心服务能力。核心服务包括：

dAlertMessage` 构建Alert消息，`GetAlertMetricsByProject` 按项目获取Alert指标 [API/Common/Services/AlertService.cs:11]。
- **BullMqService**：基于 Redis 的消息队列服务，用于异步任务处理。关键方法 `EnqueueProjectDeleteAsync` 入队项目删除任务，`EnqueueTraceIngestionAsync` 入队 Trace 数据摄入任务，`` 出队 Trace 摄入任务，`AcknowledgeTraceIngestionAsync` 确认 Trace 摄入任务完成 [API/Common/Services/BullMqService.cs:11]。
- **SettingService**：系统设置管理，包括微信/Payment宝PaymentConfig的缓存读取。关键方法 `GetWeChatSetting` 获取微信PaymentConfig，`GetAlipaySetting` 获取Payment宝PaymentConfig [API/Common/Services/SettingService.cs:11]。

Handler 层通过 `ApiHandlerBase` 基类统一提供用户上下文、数据库访问、Privilege验证等公共能力。`ApiHandlerBase` 的 `RequireOrgMembership` 验证组织成员身份，`RequireOrgAdmin` 验证组织管理员身份，`RequireOrgOwner` 验证组织所有者身份，`RequireAccessibleProject` 验证项目访问Privilege [API/Handlers/ApiHandlerBase.cs:11]。具体业务 Handler 包括 `UserHandler`（注册、登录、微信绑定、邀请成员、API Key 管理）[API/Handlers/UserManagement/UserHandler.cs:11]、`OrderHandler`（下单、查询、产品转换计算）[API/Handlers/PaymentManagement/OrderHandler.cs:11]、`MetricsHandler`（Traces、Observations、Scores 的查询与聚合）[API/Handlers/DataManagement/MetricsHandler.cs:11]、`AlertHandler`（Alert规则创建、更新、删除与记录查询）[API/Handlers/UserManagement/AlertHandler.cs:11]。

**Agents Agent服务模块** 位于 `Agents/` 目录，是一个独立的 Python FastAPI 进程，依赖Config文件 `Agents/pyproject.toml` 和 `Agents/requirements.txt` 管理依赖。该模块提供 OpenAI 兼容的 Chat Completions API，支持流式响应和Session管理，使用 LangChain.Providers.OpenAI 和 Microsoft. 进行Agent编排。其环境Config定义在 `Agents/common/config.py` 中。

支持流式响应和Session管理，使用 LangChain.Providers.OpenAI 和 Microsoft. 进行Agent编排。其环境Config定义在 `Agents/common/config.py` 中。

**Admin 后台管理模块** 位于 `Admin/` 目录，基于 Django 框架实现，依赖 `Admin/requirements.txt` 管理 Python 包。该模块提供运营管理界面，与 API 模块共享底层 PostgreSQL 数据库。根据 `Admin/Agents.md` 中的开发规范，Admin 模块遵循严格的测试驱动开发流程，要求单元测试行覆盖率不低于 80%，代码风格检查通过 flake8 和 black 校验 [Admin/Agents.md]。

**基础设施模块** 位于 `API/System/` 目录，提供横切关注点能力。`AgentInsightTransformProvider` 是 YARP 反向代理的请求转换提供者，处理认证（Basic Auth / JWT）、API Key 验证、速率限制，关键方法 `Apply` 应用请求转换，`HandleBasicAuthRequest` 处理 Basic Auth 认证，`HandleJwtAuthRequest` 处理 JWT 认证 [API/System/Handlers/AgentInsightTransformProvider.cs:11]。`ExceptionMiddleware` 是全局异常处理中间件，统一异常响应格式，关键方法 `Invoke` 为中间件调用入口，`HandleExceptionAsync` 处理异常并返回统一响应 [API/System/Handlers/ExceptionMiddleware.cs:11]。

Invoke` 为中间件调用入口，`HandleExceptionAsync` 处理异常并返回统一响应 [API/System/Handlers/ExceptionMiddleware.cs:11]。

**数据实体与模型模块** 位于 `Entities/` 和 `Models/` 目录，定义数据库实体、枚举（如 `ExceptionCodes`、`AlertField` 等）DTO。枚举定义包括 `ApiKeyScope`（`WeChat = 3`、`APIKey = 5`）[Models/Common/Enums/UserEnum.cs:12]、`RouteType`（` = 2`）[API/System/Handlers/AgentInsightTransformLogic.cs:72] 等。

### 3.2. 模块依赖关系

AgentInsightService（统一使用全称，首次出现标注品牌名） 各模块之间的依赖关系遵循分层架构原则，上层模块依赖下层模块，同层模块之间通过接口或消息队列解耦。依赖关系如下表所示：

| 依赖方 | 被依赖方 | 依赖方式 | 说明 |
|--------|---------|---------|------|
| API 应用服务模块 | Entities、Models | 项目引用 | API 层直接引用数据实体与模型模块，使用其定义的实体类和 DTO |
| API 应用服务模块 | Redis、PostgreSQL、ClickHouse | 基础设施连接 | 通过 `` Config连接三个数据存储 |
| Agents Agent服务模块 | API 应用服务模块 | 内部 HTTP 调用 | Agents 通过内部 HTTP 与 API 通信，或直连数据库 |
| Admin 后台管理模块 | Models | 项目引用 | Admin 依赖 Models 模块的数据模型定义 |
| Admin 后台管理模块 | PostgreSQL | 数据库连接 | 与 API 共享底层数据库 |
| 基础设施模块 | Redis | .Redis | BullMqService 基于 Redis 队列实现异步任务处理 |

PostgreSQL | 数据库连接 | 与 API 共享底层数据库 |
| 基础设施模块 | Redis | .Redis | BullMqService 基于 Redis 队列实现异步任务处理 |

**API 应用服务模块** 对 `Entities` 和 `Models` 的依赖体现在所有 Controller 和 Handler 的 using 语句中。例如 `AgentConfigController` 同时引用 `Entities.AgentManagement`（实体定义）和 `Models.AgentManagement`（DTO 定义）[API/Controllers/AgentManagement/AgentConfigController.cs]。`ProductController` 引用 `Models.PaymentManagement` 中的 `AgentInsightProduct` 和 `AgentInsightProductDuration` 作为响应数据类型 [API/Controllers/ProductManagement/ProductController.cs]。

**Agents Agent服务模块** 与 API 模块的通信方式有两种：一是通过内部 HTTP 调用 API 的 REST 端点，二是直连 PostgreSQL 数据库读取Config数据。该模块的依赖管理通过 `Agents/pyproject.toml` 和 `Agents/requirements.txt` 声明，包含 `openai`、`httpx`、`pydantic`、`pydantic-settings` 等 Python 依赖。

**Admin 后台管理模块** 依赖 `Models` 模块的数据模型定义，通过 Django ORM 映射到与 API 共享的 PostgreSQL 数据库。根据 `Admin/Agents.md` 中的数据库路由规则，新增 Model 的 `` 以 `agentinsight_` 前缀开头的路由到 `default` 库，其他表路由到 `data` 库 [Admin/Agents.md]。

d` 中的数据库路由规则，新增 Model 的 `` 以 `agentinsight_` 前缀开头的路由到 `default` 库，其他表路由到 `data` 库 [Admin/Agents.md]。

**基础设施模块** 中的 `BullMqService` 依赖 Redis 作为消息队列的底层存储，通过 `.Redis` 客户端库进行连接操作。`AgentInsightTransformProvider` 作为 YARP 反向代理的转换提供者，在请求转发链路中执行认证和限流逻辑，不依赖具体业务模块。

所有模块共享三个数据存储：

| 数据存储 | 连接Config | 用途 |
|---------|---------|------|
| PostgreSQL | `.`、`.`、`.` | 用户数据、业务数据、Trace数据 |
| Redis | 通过 `.Redis` 连接 | 消息队列、缓存 |
| ClickHouse | `.` | Trace 可Observation性数据存储 |

### 3.3. 模块间通信协议

AgentInsightService（统一使用全称，首次出现标注品牌名） 各模块之间的通信采用以下三种协议机制：

**1. HTTP REST 协议（API 模块内部与外部调用）**

API 模块对外暴露 RESTful HTTP 端点，Controller 层通过 `[Route]` 特性定义路由路径。根据 HTTP 端点清单，API 模块共暴露 20 个端点，分布在 4 个 Controller 文件中：

Tful HTTP 端点，Controller 层通过 `[Route]` 特性定义路由路径。根据 HTTP 端点清单，API 模块共暴露 20 个端点，分布在 4 个 Controller 文件中：

| Controller 文件 | 路由前缀 | 端点数量 | 主要功能 |
|----------------|---------|---------|---------|
| `API/Controllers/UserManagement/UserController.cs` | `/api/user` | 10 | 用户注册、登录、登出、密码重置、微信绑定/解绑、角色分配、邀请成员 |
| `API/Controllers/UserManagement/AlertController.cs` | `/api/alert` | 7 | AlertConfig查询/创建/更新/删除、Alert记录查询/标记已读 |
| `API/Controllers/DataManagement/ModelController.cs` | `/api/data/model` | 1 | 模型列表查询 |
| `API/Controllers/ToolsManagement/WeChat/WeChatController.cs` | `/api/tools/wechat` | 2 | 微信工具接口 |

例如，`UserController` 定义 `POST /api/user/login` 处理用户登录 [API/Controllers/UserManagement/UserController.cs:73]，`AlertController` 定义 `POST /api/alert` 创建Alert规则 [API/Controllers/UserManagement/AlertController.cs:61]，`ModelController` 定义 `GET /api/data/model` 查询模型列表 [API/Controllers/DataManagement/ModelController.cs:34]。

**2. Redis 消息队列协议（异步任务通信）**

`BullMqService` 基于 Redis 实现异步任务队列，用于处理耗时操作。Enqueue、Dequeue、Acknowledge三阶段模型：

```
生产者（API Handler）→ EnqueueTraceIngestionAsync → Redis Queue →  → 消费者（后台任务）
                                                                                    ↓
                                                              AcknowledgeTraceIngestionAsync（确认完成）
```

该协议用于两类异步任务：Trace 数据摄入（`EnqueueTraceIngestionAsync` / `` / `AcknowledgeTraceIngestionAsync`）和项目删除（`EnqueueProjectDeleteAsync`）[API/Common/Services/BullMqService.cs:11]。

**3. 内部 HTTP 调用（Agents 模块与 API 模块通信）**

Agents Agent服务模块作为独立进程运行，通过内部 HTTP 调用 API 模块的 REST 端点获取Config数据，或直连 PostgreSQL 数据库读取数据。API 模块的 Agent 管理端点包括：

ents Agent服务模块作为独立进程运行，通过内部 HTTP 调用 API 模块的 REST 端点获取Config数据，或直连 PostgreSQL 数据库读取数据。API 模块的 Agent 管理端点包括：

| 端点 | 功能 | 文件引用 |
|------|------|---------|
| `GET/POST /api/agent/config` | 获取/创建/更新 Agent Config | [API/Controllers/AgentManagement/AgentConfigController.cs] |
| `GET/POST /api/agent/session` | 获取/创建/更新 Agent Session | [API/Controllers/AgentManagement/AgentSessionController.cs] |
| `GET/POST /api/agent/report` | 获取/创建/更新 Agent 报表模板 | [API/Controllers/AgentManagement/AgentReportController.cs] |

**4. 数据库直连协议（Admin 模块与 API 模块共享数据库）**

Admin 后台管理模块通过 Django ORM 直连 PostgreSQL 数据库，与 API 模块共享同一套数据表。根据 `Admin/Agents.md` 的数据库路由规则，`agentinsight_` 前缀的表路由到 `default` 库，其他表路由到 `data` 库 [Admin/Agents.md]。API 模块通过 `` Config连接多个 PostgreSQL 数据库实例，包括 ``（用户库）、``（数据库）、``（Trace库），以及 ``（ClickHouse 可Observation性数据库）。

**5. 统一异常响应协议**

所有模块的异常响应统一通过 `ExceptionMiddleware` 处理，该中间件捕获未处理异常并转换为统一的响应格式 [API/System/Handlers/ExceptionMiddleware.cs:11]。错误码定义在 `ExceptionCodes` 枚举中，例如 ` = 100031`、` = 100038`、` = 620001`、` = 150004`、` = 150021` 等。

---

## 4. 接口设计

AgentInsightService（统一使用全称，首次出现标注品牌名） 是面向可Observation性数据管理与 Agent Config管理的后端服务平台，提供用户认证、Payment管理、数据查询、AlertConfig等核心能力。本章节定义系统的接口分类与规范、外部 HTTP 接口清单、内部接口契约及错误码体系，作为前后端联调与第三方集成的权威依据。

### 4.1. 接口分类与规范

#### 4.1.1. 接口分类

AgentInsightService（统一使用全称，首次出现标注品牌名） 的接口按访问范围与用途分为外部 HTTP 接口与内部接口两大类。外部 HTTP 接口面向 Web 前端、Agent 客户端及第三方Payment平台，内部接口面向服务层与Handler层之间的方法调用。

| 分类 | 子类 | 说明 |
|------|------|------|
| 外部 HTTP 接口 | 用户与组织管理 | 注册、登录、登出、用户Config、邀请成员等 |
| 外部 HTTP 接口 | Agent 管理 | Agent Config的读取、创建、更新与删除 |
| 外部 HTTP 接口 | 数据管理 | Traces、Observations、Scores 查询与模型管理 |
| 外部 HTTP 接口 | Payment管理 | 下单、订单查询、产品转换、Payment回调 |
| 外部 HTTP 接口 | 产品管理 | 产品列表与产品时长列表 |
| 外部 HTTP 接口 | 工具管理 | Bulletin管理、健康检查、微信签名验证 |
| 外部 HTTP 接口 | Alert管理 | Alert规则 CRUD 与Alert记录查询 |
| 内部接口 | 服务层接口 | `IUserService`、`IPaymentService`、`IAlertService` 等 |
| 内部接口 | Handler层接口 | `UserHandler`、`OrderHandler`、`MetricsHandler` 等 |

#### 4.1.2. 通用规范

所有外部接口均以 RESTful 风格提供，使用 JSON 格式，字符集 UTF-8。Controller基类 `ApiControllerBase` 实现了 `IDynamicApiController` 接口，统一处理用户上下文初始化与 Handler 注册 [API/Controllers/ApiControllerBase.cs:11-L20]。

**Base URL**：`/api`（所有业务接口均以此为前缀）。

**数据格式**：请求与响应体均为 JSON，`Content-Type: application/json`。时间字段统一使用 ISO 8601 格式（如 `2024-01-01T00:00:00Z`）。

**分页约定**：列表类接口支持 `page`（页码，默认 1）与 `pageSize`（每页数量，默认 10）参数，响应中返回 `totalCount` 与当前页数据条数 [API/Controllers/PaymentManagement/OrderController.cs:34-L37]。

**鉴权方式**：公开端点（如健康检查、Payment回调）无需认证；用户端点需在 `Authorization` 头携带 JWT Bearer Token；API Key 验证由 YARP 转换层 `AgentInsightTransformProvider` 处理，支持 Basic Auth 与 JWT 两种认证模式 [API/System/Handlers/AgentInsightTransformProvider.cs:22-L30]。

**响应封装**：所有接口统一返回 `ApiResponse<T>` 结构，包含 `errorCode`、`message` 与 `data` 字段。成功时 `errorCode=0`，失败时 `errorCode` 为具体错误码（见 4.4 节）。

### 4.2. 外部 HTTP 接口清单（按模块分组）

#### 4.2.1. Agent 管理

Agent Config管理接口由 `AgentConfigController` 提供，路由前缀为 `api/agent/config` [API/Controllers/AgentManagement/AgentConfigController.cs:11-L15]。

| 方法 | 路径 | 说明 | 鉴权 |
|------|------|------|------|
| GET | `/api/agent/config` | 获取当前用户的 Agent Config | JWT |
| DELETE | `/api/agent/config` | 删除当前用户的 Agent Config | JWT |
| POST | `/api/agent/config` | 创建或更新 Agent Config | JWT |

`GET /api/agent/config` 调用 `AgentConfigHandler.GetConfig()` 返回Config对象，包含 `id`、`userid`、`datasource`（数据源连接信息 JSON）、`defaulttemplateid`、`createdat`、`updatedat` 字段 [API/Controllers/AgentManagement/AgentConfigController.cs:28-L35]。`DELETE /api/agent/config` 删除当前用户的 Agent Config。`POST /api/agent/config` 接收Config内容 JSON 字符串，存在则更新、不存在则创建，`datasource` 与 `defaulttemplateid` 为空时忽略对应字段 [API/Controllers/AgentManagement/AgentConfigController.cs:54-L61]。

#### 4.2.2. 数据管理

数据管理接口由 `MetricsController` 与 `ModelController` 提供，路由前缀为 `api/data`。

| 方法 | 路径 | 说明 | 鉴权 |
|------|------|------|------|
| GET | `/api/data/metrics/observations` | 查询 Observations 列表 | JWT |
| GET | `/api/data/metrics/scores` | 查询 Scores 列表 | JWT |
| GET | `/api/data/metrics/traces` | 查询 Trace 列表（支持复杂过滤与排序） | JWT |
| POST | `/api/data/metrics/traces` | 复杂查询 Trace 列表 | JWT |
| GET | `/api/data/model` | 获取模型列表 | JWT |

`GET /api/data/metrics/observations` 与 `GET /api/data/metrics/scores` 分别调用 `MetricsHandler.GetObservationsAsync()` 与 `MetricsHandler.GetScoresAsync()` 执行查询 [API/Handlers/DataManagement/MetricsHandler.cs:24-L26]。`GET /api/data/metrics/traces` 调用 `MetricsHandler.GetTraces()` 方法，支持按关键词、Project ID、时间范围等条件过滤，并通过 `orderby` 参数控制排序（默认 `-updatedat`）[API/Handlers/DataManagement/MetricsHandler.cs:28]。`POST /api/data/metrics/traces` 提供更复杂的查询能力，请求体为查询条件 JSON。

`GET /api/data/model` 由 `ModelController.Get()` 提供，支持 `keyword`（按模型名称过滤）、`projectid`（配合 `includedpredefined` 使用）、`includedpredefined`（是否包含预定义模型）、`orderby`（排序方式）、`page` 与 `pageSize` 参数 [API/Controllers/DataManagement/ModelController.cs:34-L46]。

#### 4.2.3. Payment管理

Payment管理接口由 `OrderController` 与 `NotifyController` 提供，路由前缀为 `api/payment`。

| 方法 | 路径 | 说明 | 鉴权 |
|------|------|------|------|
| GET | `/api/payment/order` | 获取订单列表 | JWT |
| POST | `/api/payment/order` | 下单（支持微信/Payment宝） | JWT |
| GET | `/api/payment/order/query` | 根据订单号查询订单状态 | JWT |
| GET | `/api/payment/order/conversion` | 产品转换计算 | JWT |
| POST | `/api/payment/notify/wechatnotify` | 微信Payment回调通知 | 无 |
| POST | `/api/payment/notify/alipaynotify` | Payment宝Payment回调通知 | 无 |

`GET /api/payment/order` 返回订单列表，包含分页信息。订单对象字段包括 `orderno`、`tradeno`、`userid`、`orgid`、`productid`、`productname`、`price`、`rate`、`producttype`、`totalamount`、`tradestate`、`orderstate`、`paymethod`、`subpaymethod` 等 [API/Controllers/PaymentManagement/OrderController.cs:34-L37]。

`POST /api/payment/order` 为下单接口，请求体包含 `orgid`、`productid`、`productdurationid`、`paymethod`、`subpaymethod` 字段，响应返回 `orderno`、`state`、`codeurl`（Payment链接）、`qrcode`（二维码 Base64）、`prepayid`、`appid`、`timestamp`、`paysign` 等Payment参数。该接口带有 `RateLimit(maxRequests: 1, windowSeconds: 10)` 限流特性 [API/Controllers/PaymentManagement/OrderController.cs:48-L56]。

`POST /api/payment/notify/wechatnotify` 与 `POST /api/payment/notify/alipaynotify` 为Payment回调端点，标注 `[ApiExplorerSettings(IgnoreApi = true)]`，不对外暴露于 Swagger 文档。微信回调先验证请求签名，再反序列化 `WeChatNotify` 并调用 `ProcessWeChatNotify` 处理订单状态更新 [API/Controllers/PaymentManagement/NotifyController.cs:29-L44]；Payment宝回调调用 `ProcessAlipayNotify` 处理通知 [API/Controllers/PaymentManagement/NotifyController.cs:57-L70]。

#### 4.2.4. 产品管理

产品管理接口由 `ProductController` 提供，路由前缀为 `api/product`。

| 方法 | 路径 | 说明 | 鉴权 |
|------|------|------|------|
| GET | `/api/product` | 获取产品列表 | JWT |
| GET | `/api/product/duration` | 获取产品时长列表 | JWT |

`GET /api/product` 调用 `ProductHandler.GetProducts()` 返回产品列表，产品对象包含 `id`、`name`、`type`（0=None, 1=Monthly, 2=Permanent）、`price`、`monthlyrate`、`permanentrate`、`projectlimit`、`headcountlimit`、`orglimit`、`agentlimit`、`level` 字段 [API/Controllers/ProductManagement/ProductController.cs:28-L35]。`GET /api/product/duration` 返回产品时长列表，包含 `id`、`name`、`quantity`、`discount` 字段 [API/Controllers/ProductManagement/ProductController.cs:44-L51]。

#### 4.2.5. 用户与组织管理

用户管理接口由 `UserController` 与 `UserConfigController` 提供，路由前缀为 `api/user`。

| 方法 | 路径 | 说明 | 鉴权 |
|------|------|------|------|
| GET | `/api/user` | 获取当前登录用户信息 | JWT |
| POST | `/api/user` | 创建用户（注册） | 无 |
| POST | `/api/user/update` | 更新用户信息 | JWT |
| POST | `/api/user/login` | 登录 | 无 |
| POST | `/api/user/logout` | 登出 | JWT |
| GET | `/api/user/config` | 获取用户Config项 | JWT |
| POST | `/api/user/config` | 创建用户Config | JWT |

`POST /api/user` 注册接口标注 `[AllowAnonymous]`，请求体为 `MiniUserBody`，包含 `mobile`（邮箱）、`password`、`name`、`captchacode` 字段，调用 `UserHandler.CreateUser()` 完成注册 [API/Controllers/UserManagement/UserController.cs:42-L49]。

`POST /api/user/login` 登录接口支持多种登录方式，`logintype` 字段取值：1=密码、2=短信、3=微信、4=小程序、5=APIKey。`logintype=5` 时 `body` 可为空，需在 `Authorization` 头携带 `Basic publickey:secretkey`。登录成功后在响应头返回 `access-token` [API/Controllers/UserManagement/UserController.cs:69-L79]。

`GET /api/user/config` 支持 `orgId`、`projectId`、`type` 三个可选查询参数，`type` 取值：0=User、1=Organization、2=Project，返回用户Config列表 [API/Controllers/UserManagement/UserConfigController.cs:28-L36]。

#### 4.2.6. 工具管理

工具管理接口包括Bulletin管理、健康检查与微信签名验证。

| 方法 | 路径 | 说明 | 鉴权 |
|------|------|------|------|
| GET | `/api/tools/announcement` | 获取Bulletin列表 | JWT |
| GET | `/api/tools/health` | 健康检查 | 无 |
| GET | `/api/tools/wechat` | GET | 无 |
| POST | `/api/tools/wechat` | POST | 无 |

`GET /api/tools/announcement` 获取系统Bulletin列表。`GET /api/tools/health` 提供健康检查能力，无需认证。`GET /api/tools/wechat` 与 `POST /api/tools/wechat` 由 `WeChatController` 提供，用于微信服务器签名验证，分别对应 `WeChatController.Get()` 与 `WeChatController.Post()` 方法 [API/Controllers/ToolsManagement/WeChat/WeChatController.cs:36,68]。

### 4.3. 内部接口契约

#### 4.3.1. 服务层接口

服务层位于 `API/Common/Services/` 目录，提供核心业务逻辑的封装。

**IUserService**：用户管理核心服务，提供用户创建、Session管理、Token 生成、组织Privilege管理能力。关键方法包括 `CreateNewUser`（创建新用户）、`LogUserSession`（记录用户Session）、`CreateRefreshTokenAndSetHttpContext`（生成刷新 Token 并设置 HTTP 上下文）、`GetOrgPrivilegeAsync`（获取组织Privilege）[API/Common/Services/UserService.cs:22-L39]。

**IPaymentService**：Payment核心服务，提供订单创建、微信/Payment宝Payment参数生成、订单状态更新与签名验证能力。关键方法包括 `CreateOrder`（创建订单实体）、`GetWeChatJSAPIResponse`（获取微信 JSAPI Payment参数）、`GetAlipayInstantTrade`（获取Payment宝即时交易参数）、`UpdateOrderState`（根据Payment结果更新订单状态）、`ExamineAlipaySignature`（验证Payment宝回调签名）[API/Common/Services/PaymentService.cs:11]。

**IAlertService**：Alert核心服务，提供Alert条件评估、Alert消息构建与Alert指标查询能力。关键方法包括 `IsConditionMet`（判断Alert条件是否满足）、`EvaluateField`（评估Alert字段值）、`BuildAlertMessage`（构建Alert消息）、`GetAlertMetricsByProject`（按项目获取Alert指标）[API/Common/Services/AlertService.cs:11]。

#### 4.3.2. Handler层接口

Handler层位于 `API/Handlers/` 目录，所有 Handler 继承自 `ApiHandlerBase`，提供用户上下文、数据库访问、Privilege验证等公共能力。Privilege验证方法包括 `RequireOrgMembership`（验证组织成员身份）、`RequireOrgAdmin`（验证组织管理员身份）、`RequireOrgOwner`（验证组织所有者身份）、`RequireAccessibleProject`（验证项目访问Privilege）[API/Handlers/ApiHandlerBase.cs:28-L48]。

| Handler | 文件路径 | 核心方法 |
|---------|---------|---------|
| `UserHandler` | `API/Handlers/UserManagement/UserHandler.cs` | `CreateUser`、`Login`、`BindWeChat`、`InviteMember`、`CreateApiKey` |
| `OrderHandler` | `API/Handlers/PaymentManagement/OrderHandler.cs` | `PlaceOrder`、`QueryOrder`、`GetProductConversion` |
| `MetricsHandler` | `API/Handlers/DataManagement/MetricsHandler.cs` | `GetTraces`、`GetObservationsAsync`、`GetScoresAsync` |
| `AlertHandler` | `API/Handlers/UserManagement/AlertHandler.cs` | `CreateAlert`、`UpdateAlert`、`GetAlertRecords` |

`UserHandler` 负责用户管理业务逻辑，包括注册、登录、微信绑定、邀请成员、API Key 管理 [API/Handlers/UserManagement/UserHandler.cs:22-L52]。`OrderHandler` 负责订单管理业务逻辑，包括下单、查询、产品转换计算 [API/Handlers/PaymentManagement/OrderHandler.cs:22-L38]。`MetricsHandler` 负责可Observation性数据查询，包括 Traces、Observations、Scores 的查询与聚合，核心方法为 `GetTraces`（查询 Trace 列表，支持复杂过滤和排序）、`GetObservationsAsync`（查询 Observations）、`GetScoresAsync`（查询 Scores）[API/Handlers/DataManagement/MetricsHandler.cs:24-L28]。`AlertHandler` 负责AlertConfig管理，包括创建、更新、删除Alert规则，查询Alert记录 [API/Handlers/UserManagement/AlertHandler.cs:22-L34]。

#### 4.3.3. 系统基础设施层

**AgentInsightTransformProvider**：YARP 反向代理的请求转换提供者，处理认证（Basic Auth / JWT）、API Key 验证、速率限制。核心方法包括 `Apply`（应用请求转换）、`HandleBasicAuthRequest`（处理 Basic Auth 认证）、`HandleJwtAuthRequest`（处理 JWT 认证）[API/System/Handlers/AgentInsightTransformProvider.cs:22-L30]。

**ExceptionMiddleware**：全局异常处理中间件，统一异常响应格式。核心方法包括 `Invoke`（中间件调用入口）、`HandleExceptionAsync`（处理异常并返回统一响应）[API/System/Handlers/ExceptionMiddleware.cs:16-L20]。

### 4.4. 错误码体系

AgentInsightService（统一使用全称，首次出现标注品牌名） 使用 `ExceptionCodes` 枚举定义统一错误码，定义于 `Models/Common/Enums/ExceptionCodes.cs`。错误码为六位整数，按业务域分段：`100xxx` 用户域、`110xxx` Captcha域、`130xxx` 组织域、`140xxx` 项目域、`620xxx` 微信集成域、`810xxx` Payment通知域。

#### 4.4.1. 错误码定义

| errorCode | 常量名 | 说明 |
|-----------|--------|------|
| 0 | - | 成功 |
| 100000 | `UnauthorizedToken` | 未认证的 Token |
| 100001 | `UserIdIsEmpty` | User ID 为空 |
| 100004 | `CreateUserFailed` | 创建用户失败 |
| 100005 | `InvalidUser` | 无效用户 |
| 100019 | `UserNameTooLong` | 用户名过长 |
| 100021 | `InviteMobileIsEmpty` | 邀请手机号为空 |
| 100022 | `InvalidInviteMobile` | 无效的邀请手机号 |
| 100024 | `UserAlreadyOrgMember` | 用户已是组织成员 |
| 100025 | `InviteAlreadyExists` | 邀请已存在 |
| 100026 | `CreateInviteFailed` | 创建邀请失败 |
| 100027 | `InviteNotFound` | 邀请不存在 |
| 100028 | `DeleteInviteFailed` | 删除邀请失败 |
| 100031 | `ApiKeyNotFound` | API Key 不存在 |
| 100032 | `CreateApiKeyFailed` | 创建 API Key 失败 |
| 100033 | `DeleteApiKeyFailed` | 删除 API Key 失败 |
| 100036 | `ApiKeySecretNotFound` | API Key Secret 不存在 |
| 100038 | `InvalidApiKey` | 无效的 API Key |
| 100041 | `UserNotInitialized` | 用户未初始化 |
| 110000 | `SmsSendTooFrequent` | 短信发送过于频繁 |
| 110001 | `SmsSendFailed` | 短信发送失败 |
| 110002 | `VerificationCodeIsEmpty` | Captcha为空 |
| 110003 | `InvalidVerificationCode` | 无效Captcha |
| 110004 | `VerificationCodeError` | Captcha错误 |
| 130013 | `OrgAlreadyHasOwner` | 组织已存在所有者 |
| 140000 | `ProjectNameIsEmpty` | 项目名称为空 |
| 140001 | `ProjectNameTooShort` | 项目名称过短 |
| 140002 | `ProjectNameTooLong` | 项目名称过长 |
| 140003 | `InvalidProject` | 无效项目 |
| 140004 | `CreateProjectFailed` | 创建项目失败 |
| 140005 | `UpdateProjectFailed` | 更新项目失败 |
| 140006 | `DeleteProjectFailed` | 删除项目失败 |
| 140007 | `ProjectNameAlreadyExists` | 项目名称已存在 |
| 140008 | `UnauthorizedProjectAccess` | 未授权的项目访问 |
| 620003 | `GetWeChatTokenFailed` | 获取微信 Token 失败 |
| 620004 | `GetWeChatUserInfoFailed` | 获取微信基础用户信息失败 |
| 620005 | `InvalidWeChatMessageType` | 无效的微信消息类型 |
| 620017 | `GetPaymentCertificateFailed` | 获取Payment证书失败 |
| 810010 | `InvalidWeChatPaymentNotify` | 无效的微信Payment通知 |

#### 4.4.2. HTTP 状态码映射

错误码通过全局异常处理中间件 `ExceptionMiddleware` 统一转换为 HTTP 响应。映射规则如下：

| HTTP 状态码 | 适用场景 | 典型错误码 |
|-------------|---------|-----------|
| 400 | 请求参数错误、业务校验失败 | `UserIdIsEmpty` (100001)、`InvalidVerificationCode` (110003)、`ProjectNameIsEmpty` (140000) |
| 401 | 未认证或 Token 无效 | `UnauthorizedToken` (100000)、`InvalidApiKey` (100038) |
| 403 | Privilege不足 | `UnauthorizedProjectAccess` (140008) |
| 500 | 服务器内部错误 | `CreateUserFailed` (100004)、`SmsSendFailed` (110001) |

#### 4.4.3. 响应格式

统一响应结构 `ApiResponse<T>` 定义如下：

```json
{
  "errorCode": 0,
  "message": "success",
  "data": { }
}
```

成功时 `errorCode=0`，`data` 为业务数据对象或数组。失败时 `errorCode` 为上述错误码表中的具体数值，`message` 为可读的错误描述，`data` 为 `null`。

---

## 5. 数据模型

AgentInsightService（统一使用全称，首次出现标注品牌名） 作为可Observation性与 Agent 分析平台，其数据模型设计遵循"多源异构、按域隔离"的原则，将关系型业务数据、时序遥测数据与缓存/队列数据分层存储。关系型数据统一存储在 PostgreSQL 中，按业务域拆分为 `UserDbConnection`、`TrackingDbConnection`、`DataDbConnection` 三个逻辑库；时序与分析型数据（Trace、Observation、Score）存储在 ClickHouse 中，以支撑高吞吐写入与聚合查询；Redis 承担用户Session缓存、PaymentConfig缓存及 BullMQ 消息队列的底层存储。实体定义集中在 Entities/ 与 Models/ 项目中，前者为数据库实体映射，后者为业务模型与枚举定义。

### 5.1. 数据库选型与存储

#### 5.1.1. PostgreSQL 三库架构

系统采用 PostgreSQL 作为关系型数据的主存储，通过三个独立连接字符串实现逻辑隔离：

| 连接字符串 | 用途 | 关键Config |
|-----------|------|---------|
| `UserDbConnection` | User、Org、Privilege、API Key 等身份与访问控制数据 | `PORT=${};User ID=${};Password=postgres;Database=${};Application ID=${};Timeout=60;Pooling=true;MinPoolSize=10;MaxPoolSize=200;ConnectionIdleTimeout=300` |
| `TrackingDbConnection` | Alert规则、Agent Config、审计日志等跟踪与Config数据 | `PORT=${};User ID=${};Password=postgres;Database=${};Application ID=${};Timeout=60;Pooling=true;MinPoolSize=10;MaxPoolSize=200;ConnectionIdleTimeout=300` |
| `DataDbConnection` | Project、模型定义、Product/订单等业务数据 | `PORT=${};User ID=${};Password=postgres;Database=${};Application ID=${};Timeout=60;Pooling=true;MinPoolSize=10;MaxPoolSize=200;ConnectionIdleTimeout=300` |

三个库均Config了连接池（MinPoolSize=10，MaxPoolSize=200）与连接生命周期管理（ConnectionIdleTimeout=300 秒），以应对高并发场景下的连接复用与回收需求。Admin 管理端项目同样使用 PostgreSQL 双库架构（`default` + `data`），技术栈为 Python 3.10 + Django 4.2.19 [Admin/Agents.md]。

#### 5.1.2. ClickHouse 时序与分析存储

Trace、Observation、Score 等可Observation性数据写入 ClickHouse，连接Config为 `Host=${};Port=${};Username=${};Password=${};Database=${};MinPoolSize=10;MaxPoolSize=50;ConnectionIdleTimeout=30;ConnectionTimeout=60`。ClickHouse 的列式存储特性与高压缩比使其适合存储海量 Trace 数据，并支撑 `MetricsHandler` 中的聚合查询（如按 Trace ID 批量获取指标详情、分页查询 Trace 列表）[API/Controllers/DataManagement/MetricsController.cs]。

#### 5.1.3. Redis 缓存与消息队列

Redis 承担双重职责：

1. **缓存层**：用户Session（Refresh Token）、微信/Payment宝PaymentConfig等热点数据通过 `SettingService` 进行缓存读取，`GetWeChatSetting` 与 `GetAlipaySetting` 方法封装了缓存访问逻辑 [API/Common/Services/SettingService.cs:25-29]。
2. **消息队列**：基于 Redis 的 BullMQ 服务用于异步任务处理，`BullMqService` 提供 `EnqueueProjectDeleteAsync`（入队项目删除任务）、`EnqueueTraceIngestionAsync`（入队 Trace 数据摄入任务）、`DequeueTraceIngestionAsync`（出队 Trace 摄入任务）与 `AcknowledgeTraceIngestionAsync`（确认 Trace 摄入任务完成）等方法 [API/Common/Services/BullMqService.cs:28-40]。

### 5.2. 核心实体关系

#### 5.2.1. 用户与组织域

用户与组织域的核心实体包括 `User`、`Organization`、`Project` 与 `UserConfig`，其关系如下：

- **User ↔ Organization**：多对多关系，通过组织成员表关联，`PGRole` 枚举定义成员角色（Owner/Admin/Member），`UserService.GetOrgPrivilegeAsync` 负责获取组织Privilege [API/Common/Services/UserService.cs:39]。
- **Organization → Project**：一对多关系，一个组织可拥有多个项目，项目是 Trace 数据隔离的基本单位。
- **User → UserConfig**：一对多关系，`UserConfig` 通过 `type` 字段区分Config层级（0=User，1=Organization，2=Project），`UserConfigType` 枚举定义于 [Models/Common/Enums/UserEnum.cs:18]，Config内容以 JSON 格式存储于 `config` 字段 [API/Controllers/UserManagement/UserConfigController.cs]。

#### 5.2.2. Payment与产品域

Payment域实体围绕 `AgentInsightOrder` 与 `AgentInsightProduct` 构建：

- **AgentInsightProduct**：产品定义，包含 `type`（0=None，1=Monthly，2=Permanent，对应 `ProductType` 枚举）、`price`、`monthlyrate`、`permanentrate`、`projectlimit`、`headcountlimit`、`orglimit`、`agentlimit`、`level` 等字段，用于描述产品功能配额与价格策略 [API/Controllers/ProductManagement/ProductController.cs]。
- **AgentInsightOrder**：订单实体，关联用户与产品，`OrderState` 枚举（定义于 [Models/Common/Enums/PaymentEnums.cs:40]）跟踪订单状态流转，`TradeState` 枚举（定义于 [Models/Common/Enums/PaymentEnums.cs:6]）记录Payment交易状态。`PaymentService.CreateOrder` 创建订单实体，`UpdateOrderState` 根据微信/Payment宝交易结果更新订单状态 [API/Common/Services/PaymentService.cs:34,55-60]。
- **AgentInsightProductDuration**：产品时长定义，包含 `quantity`（时长数量）与 `discount`（折扣率），用于计算不同购买时长的价格 [API/Controllers/ProductManagement/ProductController.cs]。

#### 5.2.3. 可Observation性数据域

可Observation性数据域以 Trace 为核心，关联 Observation 与 Score：

- **Trace**：一次完整的请求链路，包含 `orgid`、`projectid`、`name`、`timestamp` 等字段，支持按 ID、名称、时间范围及自定义条件过滤查询 [API/Controllers/DataManagement/MetricsController.cs]。
- **Observation**：Trace 下的单个Observation单元（如一次 LLM 调用、一次工具调用），通过 Trace ID 关联，`MetricsHandler.GetObservationsAsync` 支持按 Trace ID 分页查询 [API/Controllers/DataManagement/MetricsController.cs]。
- **Score**：对 Trace 或 Observation 的Score数据，`MetricsHandler.GetScoresAsync` 支持按 Trace ID 分页查询 [API/Controllers/DataManagement/MetricsController.cs]。

#### 5.2.4. Alert与审计域

- **Alert**：Alert规则实体，关联组织与项目，`AlertField`（1=TotalTokens，2=TotalCost，3=ErrorCount）、`AlertOperator`（1=GreaterThan，2=LessThan，3=EqualTo）、`AlertPeriodUnit`（1=Minute，2=Hour，3=Day）、`AlertNotifyBy`（1=System，2=SMS）等枚举定义于 [Models/Common/Enums/AlertEnum.cs:3-39]。`AlertService.IsConditionMet` 判断Alert条件是否满足，`BuildAlertMessage` 构建Alert消息 [API/Common/Services/AlertService.cs:17,25]。
- **AuditLog**：审计实体，`AuditAction` 与 `AuditResourceType` 枚举定义于 [Models/Common/Enums/AuditEnum.cs:3-18]，跟踪用户操作行为与资源类型。

#### 5.2.5. Agent Config与Session域

- **AgentConfig**：用户级 Agent Config，包含 `datasource`（数据源连接信息 JSON）与 `defaulttemplateid`（默认模板 ID），`AgentConfigHandler.GetConfig` 获取当前用户Config [API/Controllers/AgentManagement/AgentConfigController.cs]。
- **AgentSession**：Agent Session实体，包含 `name` 与 `context`（上下文信息），`AgentSessionHandler.GetSessionById` 支持按Session ID 查询详情（含 Context），`AgentSessionHandler.GetSessions` 支持分页获取Session列表 [API/Controllers/AgentManagement/AgentSessionController.cs]。

### 5.3. 数据字典概要

#### 5.3.1. 用户与组织域核心表

| 实体 | 关键字段 | 类型 | 说明 |
|------|---------|------|------|
| User | id | string | User ID（主键） |
| | mobile | string | 手机号（登录凭证） |
| | password | string | 密码（加密存储） |
| | nickname | string | 昵称 |
| Organization | id | string | Org ID（主键） |
| | name | string | 组织名称 |
| | ownerid | string | 所有者用户 ID（外键 → User.id） |
| Project | id | string | Project ID（主键） |
| | orgid | string | 所属组织 ID（外键 → Organization.id） |
| | name | string | 项目名称 |
| UserConfig | id | string | Config ID（主键） |
| | userid | string | User ID（外键 → User.id） |
| | orgid | string | Org ID（外键 → Organization.id） |
| | projectid | string | Project ID（外键 → Project.id） |
| | type | int | Config类型（0=User，1=Organization，2=Project） |
| | config | json | Config内容（JSON 格式） |

#### 5.3.2. Payment与产品域核心表

| 实体 | 关键字段 | 类型 | 说明 |
|------|---------|------|------|
| AgentInsightProduct | id | string | Product ID（主键） |
| | name | string | 产品名称 |
| | type | int | 产品类型（0=None，1=Monthly，2=Permanent） |
| | price | decimal | 产品价格 |
| | monthlyrate | decimal | 月付费率 |
| | permanentrate | decimal | 永久费率 |
| | projectlimit | int | 项目数上限 |
| | headcountlimit | int | 人数上限 |
| | orglimit | int | 组织数上限 |
| | agentlimit | int | Agent 数上限 |
| | level | int | 产品等级 |
| AgentInsightOrder | id | string | Order ID（主键） |
| | userid | string | User ID（外键 → User.id） |
| | productid | string | Product ID（外键 → AgentInsightProduct.id） |
| | state | int | 订单状态（OrderState 枚举） |
| | tradestate | int | 交易状态（TradeState 枚举） |
| | amount | decimal | 订单金额 |
| AgentInsightProductDuration | id | string | 时长 ID（主键） |
| | name | string | 时长名称 |
| | quantity | int | 时长数量（天） |
| | discount | decimal | 折扣率 |

#### 5.3.3. 可Observation性数据域核心表

| 实体 | 关键字段 | 类型 | 说明 |
|------|---------|------|------|
| Trace | id | string | Trace ID（主键） |
| | orgid | string | Org ID |
| | projectid | string | Project ID |
| | name | string | Trace 名称 |
| | timestamp | datetime | 时间戳 |
| | inputtokens | int | 输入 Token 数 |
| | outputtokens | int | 输出 Token 数 |
| | totaltokens | int | 总 Token 数 |
| | inputcost | decimal | 输入费用 |
| | outputcost | decimal | 输出费用 |
| | totalcost | decimal | 总费用 |
| | latency | int | 延迟（毫秒） |
| | modelnames | string | 模型名称列表 |
| Observation | id | string | Observation ID（主键） |
| | traceid | string | 所属 Trace ID（外键 → Trace.id） |
| | type | string | Observation类型 |
| | name | string | Observation名称 |
| | starttime | datetime | 开始时间 |
| | endtime | datetime | 结束时间 |
| Score | id | string | Score ID（主键） |
| | traceid | string | 所属 Trace ID（外键 → Trace.id） |
| | observationid | string | 所属 Observation ID（外键 → Observation.id） |
| | name | string | Score名称 |
| | value | decimal | Score值 |

#### 5.3.4. Alert与审计域核心表

| 实体 | 关键字段 | 类型 | 说明 |
|------|---------|------|------|
| Alert | id | string | Alert ID（主键） |
| | orgid | string | Org ID（外键 → Organization.id） |
| | projectid | string | Project ID（外键 → Project.id） |
| | name | string | Alert名称 |
| | field | int | Alert字段（AlertField 枚举：1=TotalTokens，2=TotalCost，3=ErrorCount） |
| | operator | int | 运算符（AlertOperator 枚举：1=GreaterThan，2=LessThan，3=EqualTo） |
| | value | decimal | 阈值 |
| | periodquantity | int | 统计周期数量 |
| | periodunit | int | 统计周期单位（AlertPeriodUnit 枚举：1=Minute，2=Hour，3=Day） |
| | frequencyquantity | int | 触发频率数量 |
| | frequencyunit | int | 触发频率单位（AlertPeriodUnit 枚举） |
| | notifyby | int | 通知方式（AlertNotifyBy 枚举：1=System，2=SMS） |
| AuditLog | id | string | 审计 ID（主键） |
| | userid | string | 操作用户 ID（外键 → User.id） |
| | action | int | 操作类型（AuditAction 枚举） |
| | resourcetype | int | 资源类型（AuditResourceType 枚举） |
| | resourceid | string | 资源 ID |
| | timestamp | datetime | 操作时间 |

#### 5.3.5. Agent Config与Session域核心表

| 实体 | 关键字段 | 类型 | 说明 |
|------|---------|------|------|
| AgentConfig | id | string | Config ID（主键） |
| | userid | string | User ID（外键 → User.id） |
| | datasource | json | JSON |
| | defaulttemplateid | string | 默认模板 ID |
| | createdat | datetime | 创建时间 |
| | updatedat | datetime | 更新时间 |
| AgentSession | id | string | Session ID（主键） |
| | userid | string | User ID（外键 → User.id） |
| | name | string | Session名称 |
| | context | json | JSON |
| | createdat | datetime | 创建时间 |
| | updatedat | datetime | 更新时间 |

以上数据字典覆盖了 AgentInsightService（统一使用全称，首次出现标注品牌名） 的核心业务实体，各实体间的关联关系通过外键或逻辑关联（如 Trace ID）建立，确保数据的一致性与可追溯性。

---

## 6. 核心流程

<div class="report-image">
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024" width="1024" height="1024">
<rect width="1024" height="1024" fill="#f8f9fa"/>
<defs>
<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
<stop offset="0%" stop-color="#e9ecef"/>
<stop offset="100%" stop-color="#dee2e6"/>
</linearGradient>
<linearGradient id="box1" x1="0" y1="0" x2="0" y2="1">
<stop offset="0%" stop-color="#007BFF"/>
<stop offset="100%" stop-color="#0056b3"/>
</linearGradient>
<linearGradient id="box2" x1="0" y1="0" x2="0" y2="1">
<stop offset="0%" stop-color="#6c757d"/>
<stop offset="100%" stop-color="#545b62"/>
</linearGradient>
<linearGradient id="box3" x1="0" y1="0" x2="0" y2="1">
<stop offset="0%" stop-color="#adb5bd"/>
<stop offset="100%" stop-color="#8a929a"/>
</linearGradient>
<filter id="shadow" x="-10%" y="-10%" width="130%" height="130%">
<feDropShadow dx="0" dy="4" stdDeviation="6" flood-color="#000" flood-opacity="0.1"/>
</filter>
</defs>
<rect width="1024" height="1024" fill="url(#bg)"/>
<circle cx="512" cy="512" r="380" fill="none" stroke="#007BFF" stroke-opacity="0.08" stroke-width="40"/>
<circle cx="512" cy="512" r="300" fill="none" stroke="#6c757d" stroke-opacity="0.06" stroke-width="30"/>
<text x="512" y="100" text-anchor="middle" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="42" font-weight="700" fill="#2c3e50">核心流程</text>
<text x="512" y="145" text-anchor="middle" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="18" fill="#6c757d">核心流程示意图</text>
<rect x="112" y="200" width="800" height="120" rx="16" fill="url(#box1)" filter="url(#shadow)"/>
<text x="512" y="252" text-anchor="middle" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="24" font-weight="700" fill="#ffffff">流程启动</text>
<text x="512" y="288" text-anchor="middle" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="16" fill="#e0e0e0">明确目标与范围</text>
<rect x="112" y="380" width="360" height="120" rx="16" fill="url(#box2)" filter="url(#shadow)"/>
<text x="292" y="432" text-anchor="middle" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="22" font-weight="700" fill="#ffffff">流程执行</text>
<text x="292" y="468" text-anchor="middle" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="15" fill="#e0e0e0">任务分解与推进</text>
<rect x="552" y="380" width="360" height="120" rx="16" fill="url(#box2)" filter="url(#shadow)"/>
<text x="732" y="432" text-anchor="middle" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="22" font-weight="700" fill="#ffffff">流程监控</text>
<text x="732" y="468" text-anchor="middle" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="15" fill="#e0e0e0">进度与质量跟踪</text>
<rect x="112" y="560" width="800" height="120" rx="16" fill="url(#box3)" filter="url(#shadow)"/>
<text x="512" y="612" text-anchor="middle" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="22" font-weight="700" fill="#ffffff">流程优化</text>
<text x="512" y="648" text-anchor="middle" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="15" fill="#f0f0f0">评估结果与持续改进</text>
<path d="M512 320 L512 370" stroke="#007BFF" stroke-width="4" stroke-linecap="round" fill="none"/>
<polygon points="508,370 512,382 516,370" fill="#007BFF"/>
<path d="M292 500 L292 550" stroke="#6c757d" stroke-width="4" stroke-linecap="round" fill="none"/>
<polygon points="288,550 292,562 296,550" fill="#6c757d"/>
<path d="M732 500 L732 550" stroke="#6c757d" stroke-width="4" stroke-linecap="round" fill="none"/>
<polygon points="728,550 732,562 736,550" fill="#6c757d"/>
<path d="M512 680 L512 730" stroke="#adb5bd" stroke-width="4" stroke-linecap="round" fill="none"/>
<polygon points="508,730 512,742 516,730" fill="#adb5bd"/>
<rect x="192" y="742" width="640" height="60" rx="30" fill="none" stroke="#007BFF" stroke-width="2" stroke-dasharray="8 6" opacity="0.5"/>
<text x="512" y="778" text-anchor="middle" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="16" fill="#007BFF">循环迭代</text>
<path d="M192 772 L192 810 Q192 830 212 830 L492 830 Q512 830 512 810 L512 792" stroke="#007BFF" stroke-width="2" stroke-dasharray="8 6" fill="none" opacity="0.5"/>
<path d="M832 772 L832 810 Q832 830 812 830 L532 830 Q512 830 512 810 L512 792" stroke="#007BFF" stroke-width="2" stroke-dasharray="8 6" fill="none" opacity="0.5"/>
<circle cx="512" cy="860" r="30" fill="#007BFF" opacity="0.1"/>
<path d="M502 860 L510 868 L524 852" stroke="#007BFF" stroke-width="3" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
<text x="512" y="920" text-anchor="middle" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="14" fill="#6c757d">持续改进</text>
</svg>
</div>

AgentInsightService（统一使用全称，首次出现标注品牌名） 是一个面向可Observation性数据（Trace / Observation / Score）的 AI Agent 管理与分析平台，提供用户与组织管理、产品订阅与Payment、Alert评估与通知、以及基于大语言模型的 Agent Session推理能力。系统采用 .NET 8 + Furion 框架构建 API 服务层，通过 YARP 反向代理将 Agent 推理请求转发至 Python 实现的 Agents Service，并依赖 PostgreSQL（用户库/数据库/Trace库）、ClickHouse（指标存储）与 Redis（消息队列）作为核心基础设施。本章围绕用户注册与登录、下单Payment与回调处理、Alert评估与通知、AI Agent Session与推理四条核心链路，详细阐述其流程设计与实现要点。

### 6.1. 用户注册与登录流程

用户注册与登录是 AgentInsightService（统一使用全称，首次出现标注品牌名） 的入口链路，涉及用户信息创建、密码加密存储、JWT Token 签发、审计日志记录等关键环节。该流程由 `UserController` 暴露 HTTP 接口，由 `UserHandler` 承载业务逻辑，最终委托 `UserService` 完成用户实体的持久化与 Token 生成。

**注册流程**：

用户通过 `POST /api/user` 提交注册信息（如手机号、密码、Captcha等），`UserController.Create` 接收请求后调用 `UserHandler.CreateUser` 执行业务校验 [API/Controllers/UserManagement/UserController.cs:43]。`UserHandler.CreateUser` 内部完成以下步骤 [API/Handlers/UserManagement/UserHandler.cs:22]：

1. 校验Captcha（短信或邮件Captcha，Config项 `CaptchaSetting.ExpireMinutes = 6`、`CaptchaSetting.MaxAttempts = 6`、`CaptchaSetting.ResendIntervalSeconds = 300`）；
2. 调用 `UserService.CreateNewUser` 创建用户实体 [API/Common/Services/UserService.cs:22]，密码通过 `PasswordHasher`（错误码 `990003` 关联的哈希算法）加密存储；
3. 调用 `UserService.CreateRefreshTokenAndSetHttpContext` 生成刷新 Token 并写入 HTTP 上下文 [API/Common/Services/UserService.cs:35]，同时签发 JWT Token 作为短期访问凭证；
4. 记录审计日志，包括用户注册时间、IP 地址、设备信息等，通过 `RequestAuditFilter` 统一采集 [API/System/Handlers/RequestAuditFilter.cs:16]；
5. 若创建失败，抛出 `100004` 错误码。

**登录流程**：

用户通过 `POST /api/user/login` 提交凭证，`UserHandler.Login` 负责验证用户身份 [API/Handlers/UserManagement/UserHandler.cs:26]。登录成功后，系统执行以下动作：

1. 调用 `UserService.LogUserSession` 记录用户Session [API/Common/Services/UserService.cs:28]，包括登录时间、IP、User-Agent 等；
2. 重新生成 JWT Token 与刷新 Token，并通过 `CreateRefreshTokenAndSetHttpContext` 写入响应上下文 [API/Common/Services/UserService.cs:35]；
3. 加载用户所属组织及Privilege信息，调用 `UserService.GetOrgPrivilegeAsync` 获取组织Privilege [API/Common/Services/UserService.cs:39]，供后续鉴权使用。

**Token 机制与安全约束**：

| Project | 说明 |
|------|------|
| 访问 Token | JWT，短期有效，携带用户 ID、Org ID、角色等声明 |
| 刷新 Token | 随机生成，长期有效，存储在 HTTP Context 中 |
| 密码存储 | 哈希加密（`PasswordHasher`），失败时抛出 `990003` |
| 加密密钥 | `EncryptionKey = ${ENCRYPTION_KEY}`，用于敏感字段加密 |
| 审计日志 | 通过 `RequestAuditFilter` 记录请求级Trace信息 [API/System/Handlers/RequestAuditFilter.cs:16] |

**验收标准**：

- [ ] AC1: 注册成功后返回 `errorCode=0`，且响应包含 `userId` 与 JWT Token 字段
- [ ] AC2: 密码以哈希形式存储，数据库不出现明文密码
- [ ] AC3: 登录失败时返回 `100004` 或对应认证错误码
- [ ] AC4: 每次注册/登录均生成审计日志记录

### 6.2. 下单Payment与回调处理流程

下单Payment流程支持微信（JSAPI / Native / 小程序）与Payment宝（电脑网站 / 即时交易）两种Payment渠道，涵盖订单创建、Payment参数生成、Payment回调验签、订单状态更新与组织Privilege调整五个核心阶段。该流程由 `OrderController` 暴露接口，`OrderHandler` 承载业务逻辑，`PaymentService` 提供Payment渠道集成能力。

**下单流程**：

用户通过 `POST /api/payment/order` 提交下单请求，`OrderController.Place` 接收 `AgentInsightOrderBody`（包含 `orgid`、`productid`、`productdurationid`、`paymethod`、`subpaymethod` 等字段）并调用 `OrderHandler.PlaceOrder` [API/Controllers/PaymentManagement/OrderController.cs:48]。`OrderHandler.PlaceOrder` 执行以下步骤 [API/Handlers/PaymentManagement/OrderHandler.cs:22]：

1. **组织Privilege校验**：查询当前用户是否为组织 OWNER，若非 OWNER 则抛出 `810024`；
2. **产品与时长校验**：校验 `productid` 与 `productdurationid` 是否存在，不存在则抛出 `810021` 或 `810022`；
3. **订单创建**：调用 `PaymentService.CreateOrder` 创建订单实体 [API/Common/Services/PaymentService.cs:34]，订单状态初始为 `Created`（orderstate=1）；
4. **Payment参数生成**：根据 `paymethod` 分支处理：
   - 微信Payment：调用 `PaymentService.GetWeChatJSAPIResponse` 获取 JSAPI Payment参数 [API/Common/Services/PaymentService.cs:91]，或生成 Native 扫码Payment二维码；
   - Payment宝Payment：调用 `PaymentService.GetAlipayInstantTrade` 获取即时交易参数 [API/Common/Services/PaymentService.cs:62]；
5. **返回Payment参数**：响应包含 `orderno`、`codeurl`、`qrcode`、`prepayid`、`appid`、`timestamp`、`paysign` 等字段，供前端发起Payment。

**Payment回调处理**：

Payment完成后，微信/Payment宝服务器异步回调 `NotifyController` 的对应端点 [API/Controllers/PaymentManagement/NotifyController.cs:29]：

1. **验签**：微信回调调用 `WeChatService.ExamineSignature` 验证签名 [API/Common/Services/WeChatService.cs:23]；Payment宝回调调用 `PaymentService.ExamineAlipaySignature` 验证签名 [API/Common/Services/PaymentService.cs:48]。验签失败则直接返回失败响应，不更新订单状态；
2. **订单状态更新**：验签通过后，调用 `PaymentService.UpdateOrderState` 根据交易结果更新订单状态 [API/Common/Services/PaymentService.cs:55,60]；
3. **组织Privilege调整**：订单状态更新为 `Paid` 后，同步调整对应组织的产品订阅Privilege与有效期；
4. **异常处理**：订单状态更新失败时抛出 `810026` 错误码。

**订单状态定义**：

| orderstate | 含义 | 触发时机 |
|------------|------|----------|
| 1 | Created | 下单成功 |
| 2 | Paid | Payment回调验签通过 |
| 3 | Refunded | 退款完成 |
| 4 | Cancelled | 用户取消 |
| 5 | Closed | 订单关闭 |
| 6 | PaymentFailed | Payment异常 |

**验收标准**：

- [ ] AC1: 下单成功返回 `errorCode=0`，响应包含 `orderno` 与Payment参数
- [ ] AC2: 微信/Payment宝回调验签失败时返回失败响应，不更新订单状态
- [ ] AC3: Payment成功后订单状态更新为 `Paid`（2），且组织Privilege同步调整
- [ ] AC4: 订单状态更新失败时抛出 `810026`

### 6.3. Alert评估与通知流程

Alert评估与通知流程负责对可Observation性指标进行周期性或事件驱动的条件评估，并在条件满足时生成Alert消息、触发多渠道通知。该流程由 `AlertService` 提供核心评估逻辑，`AlertHandler` 管理Alert规则Config，`SystemAlertHandler` 负责Alert消息的异步分发。

**Alert规则Config**：

用户通过 `AlertController` 管理Alert规则 [API/Controllers/UserManagement/AlertController.cs:61]：

- `POST /api/alert`：创建Alert规则，调用 `AlertHandler.CreateAlert` [API/Handlers/UserManagement/AlertHandler.cs:22]；
- `POST /api/alert/update`：更新Alert规则，调用 `AlertHandler.UpdateAlert` [API/Handlers/UserManagement/AlertHandler.cs:26]；
- `POST /api/alert/delete`：删除Alert规则；
- `GET /api/alert/record`：查询Alert记录，调用 `AlertHandler.GetAlertRecords` [API/Handlers/UserManagement/AlertHandler.cs:34]。

Alert规则包含以下关键字段：指标类型（如 Trace 延迟、错误率）、比较运算符（`Contains = 6`、`GreaterThan = 7`）、阈值、评估周期（如 `Daily = 3`）、通知渠道（邮件/短信/Webhook）等。

**Alert评估流程**：

Alert评估由定时任务或触发器驱动，核心逻辑位于 `AlertService` [API/Common/Services/AlertService.cs:11]，执行以下步骤：

1. **指标查询**：调用 `AlertService.GetAlertMetricsByProject` 从 ClickHouse 查询Alert指标数据 [API/Common/Services/AlertService.cs:29]；
2. **条件评估**：调用 `AlertService.IsConditionMet` 判断指标是否满足Alert条件 [API/Common/Services/AlertService.cs:17]，内部通过 `EvaluateField` 评估各字段值 [API/Common/Services/AlertService.cs:21]；
3. **Alert消息构建**：条件满足时，调用 `AlertService.BuildAlertMessage` 构建Alert消息 [API/Common/Services/AlertService.cs:25]；
4. **消息分发**：将Alert消息推送至 Redis 消息队列，由 `SystemAlertHandler` 异步消费并触发多渠道通知（邮件/短信/Webhook）；
5. **Alert记录持久化**：Alert消息与通知结果写入Alert记录表，供后续查询。

**错误码定义**：

| errorCode | 含义 |
|-----------|------|
| 160001 | 参数校验失败，创建Alert规则失败 |
| 160002 | 参数校验失败，更新Alert规则失败 |
| 160003 | 参数校验失败，删除Alert规则失败 |
| 160012 | Privilege不足，订阅Alert失败 |
| 110001 | 短信服务异常，短信发送失败 |
| 110005 | 邮件服务异常，邮件发送失败 |

**验收标准**：

- [ ] AC1: 指标满足Alert条件时，系统生成Alert消息并触发通知
- [ ] AC2: Alert记录持久化，可通过 `GET /api/alert/record` 查询
- [ ] AC3: 通知发送失败时返回对应错误码（`110001` / `110005`）
- [ ] AC4: Alert规则创建失败时返回 `160001`

### 6.4. AI Agent Session与推理流程

AI Agent Session与推理流程是 AgentInsightService（统一使用全称，首次出现标注品牌名） 的核心能力，负责将用户请求转发至 Agents Service，完成基于大语言模型的推理，并通过流式响应输出 Token。该流程涉及 API 网关反向代理、认证转换、Session持久化三个关键环节。

**请求转发与认证转换**：

用户请求首先到达 API Service，经 YARP 反向代理转发至 Agents Service。`AgentInsightTransformProvider` 作为 YARP 的请求转换提供者，在转发前完成认证与鉴权 [API/System/Handlers/AgentInsightTransformProvider.cs:11]，具体流程如下：

1. **认证识别**：`Apply` 方法检查请求头中的认证类型 [API/System/Handlers/AgentInsightTransformProvider.cs:22]：
   - Basic Auth：调用 `HandleBasicAuthRequest` 验证客户端 ID/Secret [API/System/Handlers/AgentInsightTransformProvider.cs:26]，验证通过后提取用户身份信息；
   - JWT：调用 `HandleJwtAuthRequest` 解析并验证 JWT Token [API/System/Handlers/AgentInsightTransformProvider.cs:30]，校验签名、有效期及用户状态；
2. **API Key 验证**：若请求携带 API Key，验证 Key 的有效性与Privilege范围，确认调用者具备访问 Agents 服务的授权；
3. **速率限制**：基于 `RateLimit` 特性（如 `maxRequests: 1, windowSeconds: 10`）对下单等敏感接口进行限流，防止滥用；
4. **身份透传**：认证通过后，将用户 ID、Org ID 等信息写入转发请求头（如 `X-User-Id`、`X-Org-Id`），供 Agents 服务识别调用者身份。

**Agent Session管理**：

Session管理由 `AgentSessionController` 暴露接口 [API/Controllers/AgentManagement/AgentSessionController.cs:11]：

- `GET /api/agent/session`：获取Session列表或单个Session详情（`id` 为空时返回列表，不为空时返回包含 Context 的完整Session）；
- `POST /api/agent/session`：创建或更新Session，调用 `AgentSessionHandler.CreateOrUpdateSession`；
- `GET /api/agent/session/delete`：删除Session，仅允许删除当前用户名下的Session。

Session数据通过 `MemoryManager` 持久化，存储对话历史与上下文信息，确保多轮对话的连续性。`MemoryManager` 采用 Redis 作为底层存储，以Session ID 为键维护消息序列，支持上下文窗口管理与过期清理策略。

**流式推理与 Token 输出**：

Agents Service（Python 实现，基于 `LangChain.Providers.OpenAI` 与 `Microsoft.Extensions.AI`）接收转发请求后，执行以下推理流程：

1. **上下文组装**：从 `MemoryManager` 加载Session历史，结合用户输入的当前消息组装 Prompt；
2. **模型调用**：调用大语言模型进行推理，Streaming；
3. **Token 流式输出**：模型生成的 Token 通过 SSE（Server-Sent Events）或 WebSocket 流式返回至客户端，实现打字机效果；
4. **Session持久化**：推理完成后，将用户消息与模型回复写入 `MemoryManager`，更新Session上下文。

**Agent Config管理**：

用户可通过 `AgentConfigController` 管理 Agent Config [API/Controllers/AgentManagement/AgentConfigController.cs:11]：

- `GET /api/agent/config`：获取当前用户的 Agent Config（数据源连接信息、默认模板 ID 等）；
- `POST /api/agent/config`：创建或更新Config；
- `GET /api/agent/config/delete`：删除Config。

Config中的 `datasource` 字段为 JSON 格式，描述数据源连接信息；`defaulttemplateid` 指定默认的 Prompt 模板。

**验收标准**：

- [ ] AC1: 请求经 YARP 转发至 Agents Service，认证转换成功
- [ ] AC2: Session创建/更新成功，可通过 `GET /api/agent/session` 查询
- [ ] AC3: 流式响应正常输出 Token，客户端可实时接收
- [ ] AC4: Session数据通过 `MemoryManager` 持久化，多轮对话上下文连续
- [ ] AC5: 非法认证请求被拒绝，返回 401 或对应错误码

---

## 7. 异常处理与日志规范

AgentInsightService（统一使用全称，首次出现标注品牌名） 作为可Observation性数据平台，其核心服务层（`API/Common/Services/`）涵盖Payment处理、微信生态集成、用户管理、Alert评估与消息队列等关键能力，系统基础设施层（`API/System/Handlers/`）则提供全局异常处理、请求认证与审计等横切关注点。本章节定义 AgentInsightService（统一使用全称，首次出现标注品牌名） 全链路的异常分级与处理策略、错误码规范、结构化日志规范以及Alert与监控集成方式，确保系统在各类故障场景下具备可诊断性、可恢复性与可Observation性。

### 7.1. 异常分级与处理策略

AgentInsightService（统一使用全称，首次出现标注品牌名） 将异常按照影响程度与紧急度划分为三个等级，各等级对应不同的处理策略与响应时效。该分级体系与缺陷管理规范（`Admin/Agents.md` 中 P0/P1/P2 分级）保持一致，确保从异常发生到修复闭环的时效可控。

| 级别 | 定义 | 典型场景 | 处理策略 | 响应时效 |
|------|------|---------|---------|---------|
| P0 阻断 | 系统崩溃、数据丢失、核心服务不可用 | 数据库连接池耗尽、未捕获的运行时异常、消息队列积压 | 立即Alert、自动重试、人工介入 | 24 小时内修复 |
| P1 业务异常 | 主要业务流程失败，影响用户核心操作 | Payment失败、订单状态更新失败、Token 校验失败 | 记录详细日志、触发Alert、有限重试 | 3 个工作日 |
| P2 可容忍错误 | 参数校验失败、非关键路径异常 | 请求参数格式错误、可选字段缺失 | 记录日志、返回错误码、无需Alert | 5 个工作日 |

全局异常由 `ExceptionMiddleware` 统一捕获，该中间件位于 `API/System/Handlers/ExceptionMiddleware.cs`。中间件的 `Invoke` 方法（`API/System/Handlers/ExceptionMiddleware.cs:16`）使用 `Stopwatch` 记录请求耗时，并在 `finally` 块中将耗时数据通过 `DataQueue.Queue.Enqueue` 写入性能日志队列。对于业务异常（`AppFriendlyException`），中间件调用 `HandleExceptionAsync` 方法（`API/System/Handlers/ExceptionMiddleware.cs:20`）将异常信息序列化为统一 JSON 响应；对于未捕获的未知异常，则记录异常日志并返回 HTTP 500 状态码与通用错误消息 `TextContent.InternalServerError`。

针对 P1 级别的可恢复业务异常，AgentInsightService（统一使用全称，首次出现标注品牌名） 采用有限重试机制。以Payment交易保存为例，`PaymentTransactionSaveHandler`（`API/Notifications/PaymentTransactionSaveHandler.cs`）定义了 `MaxRetryCount = 3` 的重试上限，并Config了递增的重试延迟数组 `RetryDelays`（1 秒、3 秒、5 秒）。当 `SaveWeChatTransaction` 或 `SaveAlipayTransaction` 抛出异常时，Handler捕获异常、记录日志，并在重试次数未达上限时通过 `Task.Delay` 等待后递归调用自身进行重试；超过重试次数后，记录 `TextContent.PaymentTransactionSaveFailed` 错误日志，不再继续尝试。

对于 P0 级别的系统级异常，`ExceptionMiddleware` 会记录 `ex.ToString()` 完整异常堆栈，并将 HTTP 状态码设置为 500，响应体包含 `StatusCode = 500` 与通用错误消息。此类异常通常意味着系统存在缺陷或环境问题，需要立即人工介入排查。

### 7.2. 错误码规范

AgentInsightService（统一使用全称，首次出现标注品牌名） 采用集中式错误码枚举管理，所有业务错误码定义在 `ExceptionCodes` 枚举中（`Models/Common/Enums/ExceptionCodes.cs:6` 与 `Utility/Common/Enum/ExceptionEnums.cs:6`）。错误码按模块预留段分配，确保各业务域的错误码范围互不重叠，便于快速定位错误来源。

| 错误码常量 | 数值 | 含义 | 所属模块 |
|-----------|------|------|---------|
| `UnauthorizedToken` | 100000 | 未认证的 Token，用户身份验证失败 | 认证模块 |
| `InvalidCredentials` | 100037 | 无效的认证凭据，用户名或密码错误 | 认证模块 |
| `InvalidUser` | 100001 | 无效用户，用户不存在或已禁用 | 用户模块 |
| `PhoneNumberEmpty` | 100002 | 手机号为空，注册/登录时未提供手机号 | 用户模块 |

错误码通过 `Furion` 的 `Oops.Oh(ExceptionCodes.UnauthorizedToken)` 方式抛出。例如在 `ApiControllerBase` 中，当用户上下文不可用时抛出 `Oops.Oh(ExceptionCodes.UnauthorizedToken)`（`API/Controllers/ApiControllerBase.cs`）；在 `UserService.CreateNewUser` 中，当手机号为空时抛出 `Oops.Oh(ExceptionCodes.PhoneNumberEmpty)`（`API/Common/Services/UserService.cs`）。`ExceptionMiddleware` 捕获 `AppFriendlyException` 后，将错误码与错误消息封装进 `ApiResponse<object>` 返回给客户端。

统一响应结构定义如下：

```json
{
  "errorCode": 100000,
  "errorMessage": "未认证的 Token",
  "data": null
}
```

其中 `errorCode` 为整数错误码，`errorMessage` 为人类可读的错误描述，`data` 为业务数据负载（成功时返回实际数据，失败时为 null）。该结构确保所有 API 响应格式一致，客户端可通过 `errorCode` 精确判断错误类型，无需解析 HTTP 状态码。

错误码分配遵循以下预留段规则：

| 错误码段 | 所属模块 |
|---------|---------|
| 100000 - 100099 | 认证与授权 |
| 100100 - 100199 | 用户管理 |
| 100200 - 100299 | 组织与Privilege |
| 100300 - 100399 | Payment与订单 |
| 100400 - 100499 | 数据查询与可Observation性 |
| 100500 - 100599 | Alert与通知 |

### 7.3. 日志规范

AgentInsightService（统一使用全称，首次出现标注品牌名） 采用结构化 JSON 日志格式，所有日志输出均包含标准上下文字段，确保日志可被机器解析与聚合分析。日志记录贯穿请求处理全链路，从中间件、Controller到业务服务层，每个关键节点均记录必要的上下文信息。

**标准日志字段**：

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `timestamp` | string | ISO 8601 格式时间戳 |
| `level` | string | 日志级别：Information / Warning / Error / Critical |
| `logger` | string | 日志来源类名，如 `ExceptionMiddleware` |
| `message` | string | 人类可读的日志消息 |
| `userId` | string | 当前操作用户 ID（从 JWT Claim 提取） |
| `orgId` | string | 当前用户所属组织 ID |
| `traceId` | string | 请求Trace ID，用于关联全链路日志 |
| `clientIP` | string | 客户端 IP 地址 |
| `controller` | string | Controller名称 |
| `method` | string | 操作方法名称 |
| `elapsedMs` | long | 请求耗时（毫秒） |
| `exception` | object | 异常详情（类型、消息、堆栈） |

**上下文采集**：`RequestAuditFilter`（`API/System/Handlers/RequestAuditFilter.cs`）作为全局 Action 过滤器，在请求执行前采集 `UserId`（从 `httpContext.User?.FindFirst("UserId")` 提取）、`OrgId`（通过 `httpContext.User?.FindFirst("OrgId")` 获取）、`Controller` 与 `Method`（从 `ActionExecutingContext` 读取）等上下文信息，并记录请求耗时。该过滤器在采集过程中对每个字段的提取均使用独立的 `try-catch` 包裹，确保单个字段提取失败不影响整体审计流程。

**关键节点日志记录**：

- **请求入口**：`ExceptionMiddleware.Invoke` 在 `finally` 块中记录请求耗时，通过 `DataQueue.Queue.Enqueue` 输出性能警告日志。
- **业务异常**：`PaymentTransactionSaveHandler` 在捕获异常后记录 `ex.ToString()`，重试时记录 `Log.Information` 级别的重试信息（包含交易类型、当前重试次数、最大重试次数），最终失败时记录 `Log.Error` 级别的失败信息。
- **用户操作**：`UserService` 在创建用户、登录、Token 刷新等关键操作中记录用户上下文相关日志。

**日志级别使用约定**：

| 级别 | 使用场景 |
|------|---------|
| Information | 正常业务流程节点（请求完成、重试开始、交易保存成功） |
| Warning | 可恢复的异常（重试中）、性能阈值超限 |
| Error | 业务异常（Payment失败、Token 校验失败）、重试耗尽 |
| Critical | 系统级故障（数据库连接失败、未捕获异常） |

### 7.4. Alert与监控集成

AgentInsightService（统一使用全称，首次出现标注品牌名） 提供完整的AlertConfig管理与自动Alert写入能力，将严重错误自动转化为Alert记录，并支持通过 `SystemAlertHandler` 将Alert写入持久化存储。

**AlertConfig管理**：`AlertController`（`API/Controllers/UserManagement/AlertController.cs`）提供AlertConfig的增删改查接口。AlertConfig包含以下核心要素：

| Config项 | 说明 | 可选值 |
|--------|------|--------|
| `field` | 监控指标字段 | 1=TotalTokens, 2=TotalCost, 3=ErrorCount |
| `operator` | 比较操作符 | 1=GreaterThan, 2=LessThan, 3=EqualTo |
| `periodunit` | 统计周期单位 | 1=Minute, 2=Hour, 3=Day |
| `frequencyunit` | 检查频率单位 | 1=Minute, 2=Hour, 3=Day |
| `notifyby` | 通知方式 | 1=System, 2=SMS |

**Alert条件评估**：`AlertService`（`API/Common/Services/AlertService.cs`）负责Alert条件的评估与Alert消息构建。其核心方法包括：
- `IsConditionMet`（`API/Common/Services/AlertService.cs:17`）：判断Alert条件是否满足，比较实际指标值与阈值。
- `EvaluateField`（`API/Common/Services/AlertService.cs:21`）：评估Alert字段的当前值。
- `BuildAlertMessage`（`API/Common/Services/AlertService.cs:25`）：根据Alert规则构建人类可读的Alert消息。
- `GetAlertMetricsByProject`（`API/Common/Services/AlertService.cs:29`）：按项目聚合查询Alert指标数据。

**自动Alert写入**：当系统检测到严重错误（如 P0/P1 级别异常）时，通过 `SystemAlertHandler` 自动将Alert记录写入Alert记录表。Alert记录包含Alert规则 ID、触发时间、指标值、阈值、Alert消息等完整信息，确保运维人员可追溯Alert触发原因。

**重试机制与监控联动**：`PaymentTransactionSaveHandler` 的重试机制与Alert系统联动。当重试次数耗尽（超过 `MaxRetryCount = 3`）时，记录 `Log.Error` 级别日志，该日志可被日志聚合系统捕获并触发Alert。同时，`DataQueue.Queue.Enqueue` 记录的性能数据可用于监控请求耗时趋势，当耗时超过阈值时触发性能Alert。

**监控指标**：系统通过 `RequestAuditFilter` 采集每个请求的耗时、Controller、方法、User、客户端 IP 等信息，这些数据可聚合为以下监控指标：

| 指标名称 | 聚合方式 | 用途 |
|---------|---------|------|
| 请求成功率 | 按 errorCode=0 占比 | 评估系统整体健康度 |
| 平均响应时间 | 按Controller/方法分组求均值 | 定位性能瓶颈 |
| 错误码分布 | 按 errorCode 分组计数 | 识别高频错误类型 |
| P0 异常次数 | 按异常类型计数 | 触发紧急Alert |
| 重试次数分布 | 按重试次数分组 | 评估业务稳定性 |

---

## 8. 安全设计

AgentInsightService（统一使用全称，首次出现标注品牌名） 是面向可Observation性数据管理与 Agent 编排场景的 SaaS 平台，其安全体系覆盖身份认证、Privilege控制、数据加密、Payment安全与合规审计五个维度。本章从认证与授权、数据安全、Payment安全、威胁建模与合规四个层面，阐述 AgentInsightService（统一使用全称，首次出现标注品牌名） 的安全设计实现。

### 8.1. 认证与授权

AgentInsightService（统一使用全称，首次出现标注品牌名） 采用多因子认证策略，支持 Basic Auth 与 JWT Token 两种认证方式，RBAC实现细粒度的Privilege管理。

#### 8.1.1. 认证方式

**Basic Auth（API Key + Secret）**：适用于服务端到服务端的 API 调用场景。客户端在 `Authorization` 请求头中携带 `Basic publickey:secretkey` 格式的凭证，由 `AgentInsightTransformLogic.` 解析并提取公钥与私钥 [API/System/Handlers/AgentInsightTransformLogic.cs:72]。`UserHandler.Login` 方法在 `.APIKey` 模式下，通过公钥查询 `` 实体，并比对私钥哈希值完成认证 [API/Handlers/UserManagement/UserHandler.cs:26]。若凭证缺失或无效，分别抛出 ``（认证凭证无效）与 ``（API 密钥无效）异常 [API/Resources/Text.zh-CN.json]。

**JWT Token**：面向交互式 Web Session，采用 HS256 签名算法，并Config `=5` 秒的时钟偏移容忍窗口，以缓解分布式环境下时钟不同步导致的Token误判问题。JWT Token由 `UserService.CreateRefreshTokenAndSetHttpContext` 生成并写入 HTTP 上下文 [API/Common/Services/UserService.cs:35]，登录成功后通过响应头 `access-token` 返回客户端 [API/Controllers/UserManagement/UserController.cs:73]。Token过期后，客户端需重新登录获取新Token。

过响应头 `access-token` 返回客户端 [API/Controllers/UserManagement/UserController.cs:73]。Token过期后，客户端需重新登录获取新Token。

**API Key 管理**：`UserHandler.CreateApiKey` 负责生成 API Key，其中 Secret 使用随机数生成器产生，数据库仅存储其哈希值，避免明文泄露风险 [API/Handlers/UserManagement/UserHandler.cs:52]。API Key 支持按作用域（`ApiKeyScope`）区分Privilege范围，包括 `APIKey`（完整 API 访问）与 `JSAPI`（受限 JS 调用）两种级别 [Models/Common/Enums/UserEnum.cs:12]。

#### 8.1.2. RBAC

AgentInsightService（统一使用全称，首次出现标注品牌名） 采用基于组织的 RBAC 模型，组织内角色分为 Owner、Admin、Member 三级。所有Privilege校验集中在 `ApiHandlerBase` 基类中，通过以下方法实现 [API/Handlers/ApiHandlerBase.cs:28-48]：

| 方法 | Privilege要求 | 失败异常 |
|------|---------|---------|
| `RequireOrgMembership` | 组织成员 | `` |
| `RequireOrgAdmin` | 组织管理员 | `` |
| `RequireOrgOwner` | 组织所有者 | `` |
| `RequireAccessibleProject` | 项目访问Privilege | `` |

角色分配遵循"不能授予高于自身角色"的原则，`` 异常码（100023）在 `UserHandler.AssignRole` 中被显式检查 [API/Resources/Text.zh-CN.json]。组织所有者不能修改自身角色（``，100039），防止组织失去所有者导致管理失控。所有Privilege校验失败统一返回 ``（100010）或 ``，确保未授权操作被拒绝。

### 8.2. 数据安全

数据安全涵盖敏感数据加密存储、密钥管理与传输安全三个层面。

#### 8.2.1. 敏感数据加密

用户密码等敏感字段使用 `` Config项进行 AES 对称加密后存储 [API/Resources/Text.zh-CN.json]。加密服务通过 `IEncryptService` 接口注入 `UserHandler`，在 `CreateUser` 流程中完成密码加密 [API/Handlers/UserManagement/UserHandler.cs:22]。加密密钥通过环境变量 `${}` 注入，不落盘明文，避免Config仓库泄露风险。

API Key 的 Secret 字段仅存储哈希值，即使数据库被拖库，攻击者也无法逆向获取原始 Secret。`UserHandler.Login` 在 APIKey 认证模式下，将请求携带的 Secret 与数据库哈希值比对，而非解密还原 [API/Handlers/UserManagement/UserHandler.cs:26]。

#### 8.2.2. 密钥管理与传输安全

系统通过Config占位符机制管理密钥，`` 指定 `Configurations` 与 `Resources` 两个扫描目录，支持从环境变量或密钥管理服务注入敏感Config [API/Resources/Text.zh-CN.json]。数据库连接串（``、``、``、``）均通过 `${}` 等占位符引用环境变量，避免明文密码出现在Config文件中。

所有 API 通信强制使用 HTTPS，配合 JWT Token的 HS256 签名，确保传输过程中数据不被窃听或篡改。JWT 的 `=5` Config允许 5 秒时钟偏差，在保证安全性的同时提升分布式部署的可用性。

### 8.3. Payment安全

Payment安全是 AgentInsightService（统一使用全称，首次出现标注品牌名） 的核心安全域，覆盖微信Payment与Payment宝两大渠道，重点保障回调签名验证、交易防篡改与订单状态一致性。

#### 8.3.1. 回调签名验证

**Payment宝回调**：`PaymentService.ExamineAlipaySignature` 负责验证Payment宝异步通知的  签名 [API/Common/Services/PaymentService.cs:48]。验证失败时抛出 ``（Payment宝签名验证失败）或 ``（微信Payment通知签名验证失败）异常，拒绝伪造回调请求 [API/Resources/Text.zh-CN.json]。

ntService.cs:48]。验证失败时抛出 ``（Payment宝签名验证失败）或 ``（微信Payment通知签名验证失败）异常，拒绝伪造回调请求 [API/Resources/Text.zh-CN.json]。

**微信回调**：`WeChatService.ExamineSignature` 验证微信服务器签名 [API/Common/Services/WeChatService.cs:23]，`WeChatSignatureHelper` 提供签名工具类支持。微信Payment通知使用 AES-256- 加密，``（微信Payment通知解密失败）异常在解密失败时抛出，确保通知内容无法被第三方伪造或篡改。

#### 8.3.2. 交易记录持久化与防篡改

`PaymentService.UpdateOrderState` 根据微信/Payment宝交易结果更新订单状态 [API/Common/Services/PaymentService.cs:55-60]，所有交易记录持久化存储，形成不可篡改的审计轨迹。订单状态变更通过 `PaymentTransactionNotification` 通知机制广播 [API/Notifications/PaymentTransactionNotification.cs:9]，确保各业务模块间状态一致。

PaymentConfig通过 `SettingService.GetWeChatSetting` 与 `GetAlipaySetting` 缓存读取 [API/Common/Services/SettingService.cs:25-29]，Config变更后自动失效缓存，避免使用过期Config导致的安全漏洞。若PaymentConfig缺失，系统抛出 `` 或 `` 异常，阻止未Config状态下的Payment操作。

### 8.4. 威胁建模与合规

#### 8.4.1. 威胁模型

AgentInsightService（统一使用全称，首次出现标注品牌名） 基于  模型识别并缓解以下核心威胁：

| 威胁类型 | 攻击场景 | 缓解措施 |
|---------|---------|---------|
| 越权操作 | 普通成员尝试删除组织 | `RequireOrgOwner` Privilege校验，失败返回 ``（100010） |
| Privilege提升 | 成员尝试授予自己 Owner Role | ``（100023）拒绝高于自身角色的授权 |
| 伪造Payment通知 | 攻击者伪造微信/Payment宝回调 | `ExamineAlipaySignature` / `ExamineSignature` 双重签名验证 |
| API Key 泄露 | Secret 被截获后冒用 | 数据库仅存哈希值，泄露后可通过 `DeleteApiKey` 立即吊销 [API/Controllers/UserManagement/UserController.cs:272] |
| Session劫持 | JWT Token被重放 | HS256 签名 + `=5` 限制重放窗口，登出后Token失效 |

#### 8.4.2. 审计日志

所有敏感操作均记录审计日志，`ApiHandlerBase` 提供 `LogAudit` 方法，通过 ``（操作类型）与 ``（资源类型）两个枚举描述审计事件 [API/Handlers/UserManagement/UserHandler.cs:22]。审计覆盖以下操作：

- 用户创建（`.Create` + `.User`）
- 用户更新（`.Update` + `.User`）
- 组织角色变更
- API Key 创建与删除
- Payment订单状态变更

审计日志持久化存储，支持事后追溯与合规审查。

#### 8.4.3. 合规设计

AgentInsightService（统一使用全称，首次出现标注品牌名） 的安全设计遵循以下合规要求：

1. **最小Privilege原则**：RBAC 模型确保用户仅能访问其角色允许的资源，组织成员默认无管理Privilege，需显式授权。
2. **数据加密**：AES与传输加密（HTTPS + JWT 签名）双重保障。
3. **可追溯性**：审计日志覆盖关键操作，支持安全事件溯源。
4. **异常处理**：全局异常中间件 `ExceptionMiddleware` 统一异常响应格式 [API/System/Handlers/ExceptionMiddleware.cs:16]，避免泄露内部实现细节，同时将错误码（如 `=100010`、`=100023`）映射为多语言用户提示 [API/Resources/Text.zh-CN.json]，兼顾安全性与用户体验。

通过上述威胁建模与合规设计，AgentInsightService（统一使用全称，首次出现标注品牌名） 构建了纵深防御的安全体系，有效应对各类安全威胁，保障平台与用户数据安全。

---

## 9. 性能设计

AgentInsightService（统一使用全称，首次出现标注品牌名） 作为可Observation性数据平台，其性能设计目标是在高并发 Trace 摄入与复杂查询场景下，保障 API P95 延迟低于 200ms。本章从性能指标定义、缓存策略、异步队列与数据库优化四个维度，阐述系统的性能保障机制。

### 9.1. 性能指标

#### 9.1.1. 核心延迟指标

系统以 API P95 延迟作为核心性能度量标准，目标值为 **< 200ms**。该指标覆盖所有核心读接口，包括 Trace 列表查询、Observations 查询、Scores 查询及PaymentConfig读取等高频访问路径。

| 指标名称 | 目标值 | 适用接口 | 说明 |
|---------|--------|---------|------|
| API P95 延迟 | < 200ms | 核心读接口 | 涵盖 Trace/Observation/Score 查询 |
| PaymentConfig读取延迟 | < 50ms | `GetWeChatSetting` | 通过 Redis 缓存热点数据 |
| Trace 摄入延迟 | 异步化 | `EnqueueTraceIngestionAsync` | 不阻塞主流程 |
| 复杂查询超时 | 30s | ClickHouse 查询 | 超时返回错误码 150017 |

在 `API/Handlers/DataManagement/MetricsHandler.cs` 中，`GetTraces` 与 `GetObservationsAsync` 方法均采用分页查询模式，通过 `ToPageList` 限制单次查询数据量，避免全表扫描导致的延迟劣化 [API/Handlers/DataManagement/MetricsHandler.cs:L36-L42]。同时，方法内对 ClickHouse 查询设置了超时保护，捕获超时异常后抛出 `ExceptionCodes.ClickHouseTimeout`（150017），确保接口不会无限期阻塞 [API/Handlers/DataManagement/MetricsHandler.cs:L44-L48]。

#### 9.1.2. 吞吐量与并发指标

系统通过数据库连接池Config保障并发处理能力。在 `API/appsettings.QA.json` 中，三个 PostgreSQL 连接串（`Default`、`DataDb`、`LogDb`）均Config了连接池参数，ClickHouse 连接串亦Config了独立的连接池参数。具体Config如下：

- **PostgreSQL 连接池（Default/DataDb/LogDb）**：每个连接串均Config `MinPoolSize=10, MaxPoolSize=200`，支撑用户管理、Order、Config等业务数据的高并发读写，最大 200 个并发连接
- **ClickHouse 连接池**：Config `MinPoolSize=10, MaxPoolSize=50`，支撑 Trace 分析类查询，最大 50 个并发连接，避免列式存储查询资源争用

三个 PostgreSQL 连接串分别服务于不同的业务域：`Default` 连接串面向用户与组织管理，`DataDb` 连接串面向项目与可Observation性业务数据，`LogDb` 连接串面向系统日志与审计数据。各连接池独立管理，避免跨业务域的资源争用。

#### 9.1.3. 性能监控与Alert

系统通过 `AlertService` 提供Alert条件评估能力，`IsConditionMet` 方法判断Alert条件是否满足，`GetAlertMetricsByProject` 按项目获取Alert指标 [API/Common/Services/AlertService.cs:L17-L29]。该机制可对接口延迟、错误率等性能指标进行实时监控，当指标超出阈值时触发Alert通知。

### 9.2. 缓存策略

#### 9.2.1. Redis 缓存架构

系统采用 Redis 作为核心缓存层，通过 `StackExchange.Redis` 客户端实现连接管理。在 `API/Common/Services/BullMqService.cs` 中，Redis 连接通过 `Lazy<ConnectionMultiplexer>` 实现懒加载单例模式，连接字符串从Config节 `Redis:Configuration` 读取 [API/Common/Services/BullMqService.cs:L99-L107]。

```csharp
// Redis 连接初始化（BullMqService.cs）
_redis = new Lazy<ConnectionMultiplexer>(() =>
{
    var config = _configuration.GetSection("Redis");
    var connectionString = config.GetValue<string>("Configuration")
        ?? throw new InvalidOperationException("Redis Configuration is not configured");
    return ConnectionMultiplexer.Connect(connectionString);
});
```

#### 9.2.2. 热点数据缓存

系统针对高频读取的Config类数据实施 Redis 缓存策略，重点覆盖PaymentConfig等热点数据。`SettingService` 中的 `GetWeChatSetting` 方法（[API/Common/Services/SettingService.cs:L25]）与 `GetAlipaySetting` 方法（[API/Common/Services/SettingService.cs:L29]）在读取PaymentConfig时，优先从 Redis 缓存获取，缓存未命中时才回源数据库查询，并将结果回填至缓存。该策略确保PaymentConfig读取延迟低于 50ms。

缓存键设计遵循 `{domain}:{entity}:{id}` 规范，例如微信PaymentConfig的缓存键格式为 `setting:wechat:{projectId}`。TTL，在Config更新时主动失效对应缓存项，保障数据一致性。

### 9.3. 异步队列

#### 9.3.1. 队列任务类型

系统通过 `BullMqService` 实现基于 Redis 的异步任务队列，支持以下任务类型：

| 方法 | 说明 | 队列名称 |
|------|------|---------|
| `EnqueueTraceIngestionAsync` | 入队 Trace 数据摄入任务 | `trace-ingestion` |
| `DequeueTraceIngestionAsync` | 出队 Trace 摄入任务 | `trace-ingestion` |
| `AcknowledgeTraceIngestionAsync` | 确认 Trace 摄入任务完成 | `trace-ingestion` |
| `EnqueueProjectDeleteAsync` | 入队项目删除任务 | `project-delete` |

`EnqueueProjectDeleteAsync` 方法将项目删除任务异步化，避免删除操作阻塞主流程 [API/Common/Services/BullMqService.cs:L110-L115]。项目删除涉及大量关联数据的清理，若同步执行将导致接口长时间阻塞，通过队列异步处理后，接口可立即返回，后台 Worker 逐步执行删除任务。

#### 9.3.2. 队列实现机制

`BullMqService` 使用 Redis 的多种数据结构实现队列功能：

- **List**：用于待处理任务队列（`waitKey`），通过 `LPUSH` 入队、`BRPOPLPUSH` 出队
- **Sorted Set**：用于延迟任务调度（`delayedKey`），按执行时间戳排序
- **Hash**：存储任务元数据（`jobKey`），包括任务名称、数据、时间戳等
- **Stream**：记录任务事件（`eventsKey`），通过 `XADD` 追加事件

`EnqueueJobScript` Lua 脚本实现了任务入队的原子操作，包括任务 ID 自增、元数据写入、事件记录与队列推送 [API/Common/Services/BullMqService.cs:L66-L88]。`EnqueueDelayedJobScript` 则额外支持延迟任务调度，通过 `ZADD` 将任务按延迟时间戳加入有序集合 [API/Common/Services/BullMqService.cs:L20-L64]。

#### 9.3.3. 异步任务场景

系统通过异步队列处理以下两类核心场景：

**Trace 数据摄入**：`EnqueueTraceIngestionAsync` 将 Trace 数据摄入任务入队，后台 Worker 通过 `DequeueTraceIngestionAsync` 出队并处理，处理完成后调用 `AcknowledgeTraceIngestionAsync` 确认完成 [API/Common/Services/BullMqService.cs:L32-L40]。该机制确保：

- API 接口快速响应，不等待数据落库
- 数据摄入吞吐量可水平扩展（增加 Worker 实例）
- 任务失败可重试，通过 Redis 持久化保障不丢失

**项目删除**：`EnqueueProjectDeleteAsync` 将项目删除任务入队，避免删除操作长时间占用数据库连接。项目删除涉及 Trace、Observation、Score 等多表级联删除，异步化后可有效避免主流程阻塞。

### 9.4. 数据库优化

#### 9.4.1. 连接池Config

系统针对不同数据库类型Config了差异化的连接池参数：

| 数据库 | MinPoolSize | MaxPoolSize | ConnectionIdleLifetime | ConnectionPruneInterval |
|--------|-------------|-------------|-------------------|----------------|
| PostgreSQL（Default） | 10 | 200 | 300s | 30s |
| PostgreSQL（DataDb） | 10 | 200 | 300s | 30s |
| PostgreSQL（LogDb） | 10 | 200 | 300s | 30s |
| ClickHouse | 10 | 50 | - | 60s |

在 `API/appsettings.QA.json` 中，三个 PostgreSQL 连接串均Config了 `Pooling=true` 与 `MinPoolSize=10;MaxPoolSize=200` [API/appsettings.QA.json]。`ConnectionIdleLifetime=300` 确保连接在 5 分钟后自动回收，防止数据库端连接泄漏。ClickHouse 连接串Config `MinPoolSize=10;MaxPoolSize=50`，`ConnectionPruneInterval=60` 为复杂分析查询提供更长的执行窗口。

#### 9.4.2. ClickHouse 列式存储优化

系统将 Trace、Observation、Score 等可Observation性数据存储在 ClickHouse 中，利用列式存储引擎优化复杂查询性能。`MetricsHandler` 通过 `ISqlSugarClient` 注入 ClickHouse 客户端（`_chdb`），执行分页查询与聚合分析 [API/Handlers/DataManagement/MetricsHandler.cs:L18-L20]。

**查询优化策略**：

1. **分页查询**：`GetTraces` 与 `GetObservationsAsync` 均使用 `ToPageList` 实现分页，限制单次查询返回行数 [API/Handlers/DataManagement/MetricsHandler.cs:L36-L42]
2. **条件过滤**：查询条件包含 `!o.IsDeleted` 软删除过滤，减少扫描数据量
3. **排序优化**：按 `Timestamp` / `StartTime` 排序，利用 ClickHouse 的排序键加速
4. **复杂过滤**：`GetTraces` 方法通过 `TraceFilterBuilder.BuildFilters` 构建过滤条件 [API/Handlers/DataManagement/MetricsHandler.cs:L76]，支持基于时间范围、字段值等多维过滤

```csharp
// ClickHouse 分页查询示例（MetricsHandler.cs）
var items = await _chdb.Queryable<Observation>()
    .Where(o => o.TraceId == traceId && !o.IsDeleted)
    .OrderBy(o => o.Timestamp)
    .ToPageList(page, pageSize, totalCount, isPage: true)
    .ToListAsync();
```

`TraceFilterBuilder.BuildFilters` 方法接收查询参数对象，动态构建表达式树。其内部根据传入的时间范围、Trace ID、Span ID、Project ID 等条件，通过 `Expression<Func<Observation, bool>>` 组合生成过滤表达式。该方法支持链式条件追加，并在条件为空时自动跳过，避免生成无效的 SQL 过滤子句。

#### 9.4.3. 查询超时与错误处理

`MetricsHandler` 对 ClickHouse 查询实施了完善的异常处理机制：

- **超时检测**：`IsTimeoutException` 方法判断异常是否为超时类型，超时后抛出 `ExceptionCodes.ClickHouseTimeout`（150017）[API/Handlers/DataManagement/MetricsHandler.cs:L44-L48]
- **错误包装**：非超时异常统一包装为 `ExceptionCodes.ClickHouseQueryFailed`（150010），避免底层错误信息泄露
- **日志记录**：通过 `ex.LogMetricsHandlerError()` 记录异常上下文，便于问题Trace

该机制确保在 ClickHouse 负载过高或查询复杂度过大时，API 接口能够快速失败并返回明确错误码，而不是无限期等待。

#### 9.4.4. 索引与数据模型优化

系统针对高频查询路径设计了差异化的数据模型：

- **PostgreSQL**：User、Order、Config等关系型数据，通过主键索引与业务索引加速查询
- **可ObservationClickHouse**：Trace/Observation/Score 等时序数据，利用列式存储的压缩与投影优化，`TraceId` 作为查询键建立索引

在 `MetricsController` 中，`GetTraceMetricsByIds` 接口支持按 `ids` 批量查询 Trace 指标详情，通过 `_handler.GetTraceMetricsByIds(ids)` 一次性获取多个 Trace 的聚合指标 [API/Controllers/DataManagement/MetricsController.cs:L64-L70]，避免 N+1 查询问题。

---

## 10. 部署设计

<div class="report-image">
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024" width="1024" height="1024"><defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="#f0f4f8"/><stop offset="100%" stop-color="#dbe4ee"/></linearGradient><linearGradient id="card1" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#007BFF"/><stop offset="100%" stop-color="#0056b3"/></linearGradient><linearGradient id="card2" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#6c757d"/><stop offset="100%" stop-color="#495057"/></linearGradient><linearGradient id="card3" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#17a2b8"/><stop offset="100%" stop-color="#117a8b"/></linearGradient><filter id="shadow" x="-5%" y="-5%" width="115%" height="115%"><feDropShadow dx="0" dy="4" stdDeviation="6" flood-color="#00000020"/></filter></defs><rect width="1024" height="1024" fill="url(#bg)"/><text x="512" y="72" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="38" font-weight="700" fill="#2c3e50" text-anchor="middle">部署设计</text><line x1="462" y1="90" x2="562" y2="90" stroke="#007BFF" stroke-width="4" stroke-linecap="round"/><rect x="70" y="120" width="884" height="180" rx="16" fill="#ffffff" filter="url(#shadow)"/><text x="110" y="160" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="22" font-weight="700" fill="#007BFF">代码仓库</text><rect x="110" y="180" width="180" height="34" rx="6" fill="#e8f0fe"/><text x="200" y="203" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="16" fill="#333" text-anchor="middle">源代码管理</text><rect x="310" y="180" width="180" height="34" rx="6" fill="#e8f0fe"/><text x="400" y="203" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="16" fill="#333" text-anchor="middle">版本控制</text><rect x="510" y="180" width="180" height="34" rx="6" fill="#e8f0fe"/><text x="600" y="203" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="16" fill="#333" text-anchor="middle">分支管理</text><rect x="710" y="180" width="180" height="34" rx="6" fill="#e8f0fe"/><text x="800" y="203" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="16" fill="#333" text-anchor="middle">协作开发</text><line x1="512" y1="300" x2="512" y2="350" stroke="#adb5bd" stroke-width="3" stroke-dasharray="8,6"/><polygon points="512,358 505,346 519,346" fill="#adb5bd"/><rect x="70" y="370" width="884" height="180" rx="16" fill="#ffffff" filter="url(#shadow)"/><text x="110" y="410" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="22" font-weight="700" fill="#6c757d">构建阶段</text><rect x="110" y="430" width="200" height="34" rx="6" fill="#f1f3f5"/><text x="210" y="453" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="16" fill="#333" text-anchor="middle">依赖安装</text><rect x="330" y="430" width="200" height="34" rx="6" fill="#f1f3f5"/><text x="430" y="453" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="16" fill="#333" text-anchor="middle">编译打包</text><rect x="550" y="430" width="200" height="34" rx="6" fill="#f1f3f5"/><text x="650" y="453" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="16" fill="#333" text-anchor="middle">单元测试</text><rect x="770" y="430" width="140" height="34" rx="6" fill="#f1f3f5"/><text x="840" y="453" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="16" fill="#333" text-anchor="middle">产物生成</text><line x1="512" y1="550" x2="512" y2="600" stroke="#adb5bd" stroke-width="3" stroke-dasharray="8,6"/><polygon points="512,608 505,596 519,596" fill="#adb5bd"/><rect x="70" y="620" width="884" height="180" rx="16" fill="#ffffff" filter="url(#shadow)"/><text x="110" y="660" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="22" font-weight="700" fill="#17a2b8">部署环境</text><rect x="110" y="680" width="200" height="34" rx="6" fill="#e6f7f9"/><text x="210" y="703" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="16" fill="#333" text-anchor="middle">开发环境</text><rect x="330" y="680" width="200" height="34" rx="6" fill="#e6f7f9"/><text x="430" y="703" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="16" fill="#333" text-anchor="middle">测试环境</text><rect x="550" y="680" width="200" height="34" rx="6" fill="#e6f7f9"/><text x="650" y="703" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="16" fill="#333" text-anchor="middle">预发布环境</text><rect x="770" y="680" width="140" height="34" rx="6" fill="#e6f7f9"/><text x="840" y="703" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="16" fill="#333" text-anchor="middle">生产环境</text><line x1="512" y1="800" x2="512" y2="850" stroke="#adb5bd" stroke-width="3" stroke-dasharray="8,6"/><polygon points="512,858 505,846 519,846" fill="#adb5bd"/><rect x="70" y="870" width="884" height="100" rx="16" fill="#ffffff" filter="url(#shadow)"/><text x="110" y="910" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="22" font-weight="700" fill="#007BFF">监控运维</text><rect x="310" y="890" width="180" height="34" rx="6" fill="#e8f0fe"/><text x="400" y="913" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="16" fill="#333" text-anchor="middle">日志监控</text><rect x="510" y="890" width="180" height="34" rx="6" fill="#e8f0fe"/><text x="600" y="913" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="16" fill="#333" text-anchor="middle">性能监控</text><rect x="710" y="890" width="180" height="34" rx="6" fill="#e8f0fe"/><text x="800" y="913" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="16" fill="#333" text-anchor="middle">Alert通知</text></svg>
</div>

AgentInsightService（统一使用全称，首次出现标注品牌名） 是一个面向可Observation性数据（Trace、Observation、Score）的采集、存储、查询与分析平台，采用前后端分离与多服务组件架构。其部署设计围绕容器化、环境隔离、自动化发布与可Observation运维四大目标展开，确保系统在 Development、Staging、Production 三种环境中具备一致的交付行为与可靠的运行保障。

### 10.1. 部署架构

AgentInsightService（统一使用全称，首次出现标注品牌名） 采用容器化部署策略，核心运行时组件包括 API Service、Agents 采集服务与 Admin 管理后台，三者各自构建为独立容器镜像，实现资源隔离、独立扩缩容与故障域隔离。

**容器化基础**

项目通过 `Microsoft..Azure.Containers.Tools.Targets` 提供 Docker 容器化支持，该工具链集成于 API 工程中，支持 Visual Studio 与命令行两种镜像构建方式。API 服务作为系统入口，承载所有 HTTP 接口与反向代理逻辑；Agents 服务基于 Python 实现，通过 `Agents/pyproject.toml` 与 `Agents/requirements.txt` 管理依赖，负责 Trace 数据采集与上报；Admin 服务基于 Django 实现，通过 `Admin/requirements.txt` 管理依赖，提供后台管理能力。

**容器编排与网络拓扑**

各容器通过 Docker Compose 或 Kubernetes 进行编排，容器间通信遵循最小暴露原则：

| 组件 | 容器镜像 | 对外暴露端口 | 依赖组件 |
|------|---------|-------------|---------|
| API | api:latest | 80/443 | PostgreSQL、ClickHouse、Redis |
| Agents | agents:latest | 无（主动外连） | API、ClickHouse |
| Admin | admin:latest | 8000 | PostgreSQL |

|
| Agents | agents:latest | 无（主动外连） | API、ClickHouse |
| Admin | admin:latest | 8000 | PostgreSQL |

API 容器内部署 YARP 反向代理（`Yarp.`），通过 `AgentInsightTransformProvider` 实现请求转换与认证处理 [API/System/Handlers/AgentInsightTransformProvider.cs:11]。该组件负责将外部请求路由至内部服务，同时执行 Basic Auth / JWT 认证与 API Key 验证 [API/System/Handlers/AgentInsightTransformProvider.cs:22-L30]。

**数据层部署**

数据层由 PostgreSQL 与 ClickHouse 组成。PostgreSQL 承载用户库（）、DataDb与Trace库（）三类逻辑库，连接字符串通过环境变量注入，例如 `. = PORT=${};=${};=postgres;...`。ClickHouse 负责可Observation性数据的列式存储与分析查询，连接串通过 `.` 注入，Config了连接池参数 `=10;=50;=30;=60`。

API 服务启动时通过 `SQLSugarHelper.CreateUserClient()` 与 `SQLSugarHelper.CreateDataClient()` 分别创建用户库与数据库的 ORM 客户端，并以  方式注册到依赖注入容器 [API/Program.cs:76-L77]，确保多数据库连接的生命周期管理。

### 10.2. 环境策略

AgentInsightService（统一使用全称，首次出现标注品牌名） 支持多环境部署，与 Agents 组件中 `Environment` 枚举（定义于 `Agents/common/config.py:15`）保持一致，划分为 Development、Staging、Production 三个环境。每个环境拥有独立的Config体系与资源隔离策略。

**环境Config分层**

Admin 组件采用 `base.py / Development.py / QA.py / LIVE.py` 的分层Config结构，其中 `base.py` 存放公共Config（如 `` 菜单Config），各环境文件覆盖差异化Config [Admin/Agents.md]。API 组件通过 `Configurations/` 与 `Resources/` 目录扫描Config文件（` = ['Configurations', 'Resources']`），并在启动时通过 `ConfigurationPlaceholderResolver.(builder.Configuration)` 解析环境变量占位符 [API/Program.cs:22-L24]。

**环境变量注入**

关键Config全部通过环境变量注入，避免敏感信息写入镜像或代码仓库。核心环境变量清单如下：

| Config项 | 环境变量 | 说明 |
|--------|---------|------|
| AES 加密密钥 | `` | 用于敏感数据加密（` = ${}`） |
| ClickHouse 连接 | `` / `` / `` / `` / `` | 可Observation性数据存储 |
| 用户库连接 | `` / `` / `` / `` | 用户与组织数据 |
| 数据库连接 | `` / `` / `` / `` | 业务数据 |
| Trace库连接 | `` / `` / `` / `` | Trace数据 |
| 第三方服务 | `` / `` | 外部 API 集成凭证 |

数据库连接串统一采用 `=postgres` 的形式，指向容器编排网络内的数据库服务别名，避免硬编码 IP 地址。

**环境隔离策略**

三个环境在基础设施层面完全隔离：

- **Development**：面向本地开发与功能验证，数据库与缓存服务可运行在开发者本机或共享开发环境，Config最简化。
- **Staging**：与 Production 保持一致的部署拓扑与Config基线，用于发布前的集成验证与性能测试，数据使用脱敏后的生产样本。
- **Production**：生产环境，启用全部安全策略（TLS、密钥管理、审计日志），数据库与缓存服务采用高可用部署。

### 10.3. CI/CD 与Config管理

AgentInsightService（统一使用全称，首次出现标注品牌名） 的持续集成与持续部署（CI/CD）流程覆盖代码提交、构建、测试、镜像发布与部署的全链路，Config管理遵循"环境变量注入 + Config文件分层"的双轨策略。

**CI/CD 流水线**

项目根目录的 `.github` 目录存放  Actions 工作流定义，流水线按组件拆分并行执行：

| 阶段 | 操作 | 产物 |
|------|------|------|
| 代码检查 | 静态分析、格式检查 | 检查报告 |
| 单元测试 | 执行 `UnitTest` 目录下的测试用例 | 测试报告 |
| 镜像构建 | 基于 `Microsoft..Azure.Containers.Tools.Targets` 构建 API 镜像；基于 `Agents/pyproject.toml` 与 `Admin/requirements.txt` 构建 Agents 与 Admin 镜像 | Docker 镜像 |
| 镜像推送 | 推送至容器镜像仓库（如  / Docker Hub） | 镜像 Tag |
| 部署 | 按环境触发部署任务，更新容器编排服务 | 运行实例 |

**Config管理**

Config管理遵循"代码仓库管理默认Config + 部署环境注入敏感Config"的原则：

1. **默认Config入库**：`Configurations/` 与 `Resources/` 目录存放各环境的默认Config文件，通过 `` 指定扫描路径。
2. **环境变量覆盖**：部署时通过容器编排系统注入环境变量，`ConfigurationPlaceholderResolver` 在应用启动时解析 `${}` 占位符并替换为实际值 [API/Program.cs:22-L24]。
3. **敏感信息保护**：``、数据库密码、第三方 API 密钥等敏感信息仅通过环境变量注入，不落入镜像层与代码仓库。

**版本与发布策略**

- 镜像 Tag 采用语义化版本（）与 Git Commit  结合的方式，确保可追溯性。
- 数据库 Schema 变更通过 `Scripts` 目录下的迁移脚本管理，与应用发布解耦，支持向前兼容。
- 发布采用蓝绿或滚动更新策略，API 服务通过健康检查端点 `GET /api/tools/health` 进行就绪探活 [API/Controllers/ToolsManagement/HealthController.cs:20]，确保新实例就绪后才摘除旧实例流量。

### 10.4. 监控与运维

AgentInsightService（统一使用全称，首次出现标注品牌名） 的监控与运维体系覆盖基础设施监控、应用健康检查、日志采集与Alert通知四个维度。

**健康检查**

API 服务暴露 `GET /api/tools/health` 端点 [API/Controllers/ToolsManagement/HealthController.cs:20]，用于负载均衡器与容器编排系统的探活。该端点由 `HealthController.Get` 方法实现，返回服务存活状态。负载均衡器定期调用该端点，若连续多次失败则自动摘除异常实例并触发重新调度。

**应用监控**

API 服务内置了完整的可Observation性埋点：

- **性能指标**：通过 `` 启用 Brotli/Gzip 压缩 [API/Program.cs:28-L35]，`` Config 30 秒输出缓存 [API/Program.cs:38-L41]，降低响应延迟。
- **连接池监控**：PostgreSQL 连接串Config `Pooling=true;=10;=200;=300`，ClickHouse 连接串Config `=10;=50`，通过连接池参数控制资源水位。
- **Kestrel 限额**：` = 1024`、` = 100 * 1024 * 1024` [API/Program.cs:14-L19]，防止异常流量冲击。

**日志与Trace**

- **结构化日志**：API 服务通过全局异常处理中间件 `ExceptionMiddleware` 统一异常响应格式 [API/System/Handlers/ExceptionMiddleware.cs:16-L20]，确保错误日志的可解析性。
- **异步任务Trace**：基于 Redis 的 `BullMqService` 提供消息队列能力，`EnqueueTraceIngestionAsync` 与 `AcknowledgeTraceIngestionAsync` 分别负责 Trace 数据摄入任务的入队与确认 [API/Common/Services/BullMqService.cs:32-L40]，通过任务状态Trace数据管道健康度。

**Alert与运维响应**

| 监控对象 | Metric | Alert阈值建议 | 响应动作 |
|---------|------|------------|---------|
| API 健康状态 | 健康检查失败率 | 连续 3 次失败 | 自动重启容器 / 摘除流量 |
| 数据库连接池 | 活跃连接数占比 | > 80% 持续 5 分钟 | 扩容数据库实例 / 优化连接池参数 |
| ClickHouse 查询延迟 | P99 查询耗时 | > 2 秒持续 10 分钟 | 检查查询语句 / 扩容 ClickHouse 节点 |
| Redis 队列积压 | 未确认消息数 | > 1000 持续 5 分钟 | 扩容 Agents 消费者 / 检查消费逻辑 |
| 磁盘使用率 | 数据节点磁盘 | > 85% | 触发数据归档 / 扩容存储 |

**运维自动化**

- 容器编排平台（Kubernetes 或 Docker Swarm）负责实例的自动扩缩容与故障自愈。
- 数据库备份策略：PostgreSQL 每日全量备份 + 实时  归档；ClickHouse 每日快照备份。
- Config变更通过 CI/CD 流水线统一发布，避免手动操作导致的Config漂移。

---

## 11. 用户界面设计

AgentInsightService（统一使用全称，首次出现标注品牌名） 作为可Observation性与 Agent 管理平台，其用户界面由两大核心部分组成：面向运营管理人员的 Admin 后台管理界面，以及面向终端用户的 Agents Web 聊天界面。Admin 后台基于 Django Admin 深度定制，提供用户、Order、Alert等核心数据的管理能力；Agents 服务则内嵌简易 Web 聊天界面，支持流式对话展示。两个界面均通过 API 网关统一路由，前端静态资源由各自服务独立提供，形成清晰的前后端职责边界。

### 11.1. Admin 后台界面

Admin 后台是 AgentInsightService（统一使用全称，首次出现标注品牌名） 的运营管理中枢，采用 Python 3.10 + Django 4.2.19 技术栈构建，定位为**纯 Admin Project**，不提供 REST API，所有管理功能均通过 Django Admin 后台实现 [Admin/Agents.md]。该后台运行于独立服务端口 22522，部署在 `` Docker 外部网络中，与主 API 服务保持网络隔离 [Admin/Agents.md]。

#### 11.1.1. 技术架构与数据模型

Admin 项目根目录为 `Admin/`，Config目录位于 `Admin/Admin/settings/`，根据环境变量 `` 动态加载 `Development` / `QA` / `LIVE` 三套Config [Admin/Admin/wsgi.py]。 入口通过 `os.environ.setdefault("", "Admin.settings.{0}".format(profile))` 实现环境感知的Config加载 [Admin/Admin/wsgi.py]。

数据模型采用**双数据库路由**策略，由 `app/db_router.py` 中的 `` 类实现：

| 表名前缀 | 路由目标 | 说明 |
|---------|---------|------|
| `agentinsight_` | `default` 库 | 核心业务表（User、Order、Alert等） |
| 其他前缀 | `data` 库 | 可Observation性数据表（Trace、Observation 等） |
| Django 内置 app | `default` 库 | auth、session 等系统表 |

所有 Model 均设置 `managed = False`，不参与 Django 迁移，数据库表由 .NET API 主服务统一管理。**禁止执行 `makemigrations` 和 `migrate`**（Django 内置表除外，由 `entrypoint.sh` 自动执行）[Admin/Agents.md]。

#### 11.1.2. 数据库连接Config

QA 与 LIVE 环境均Config PostgreSQL 双库连接，通过环境变量注入连接参数 [Admin/Admin/settings/QA.py] [Admin/Admin/settings/LIVE.py]：

```python
 = {
    "default": {
        "": "django.db.backends.postgresql",
        "": os.environ.get(""),
        "": os.environ.get(""),
        "": os.environ.get(""),
        "": os.environ.get(""),
        "PORT": os.environ.get(""),
    },
    "data": {
        "": "django.db.backends.postgresql",
        "": os.environ.get(""),
        "": os.environ.get(""),
        "": os.environ.get(""),
        "": os.environ.get(""),
        "PORT": os.environ.get(""),
    },
}
 = ["app.db_router."]
```

      "": os.environ.get(""),
        "PORT": os.environ.get(""),
    },
}
 = ["app.db_router."]
```

#### 11.1.3. 静态资源与反向代理

生产环境通过 `whitenoise.middleware.` 提供静态文件服务，使用 `` 进行压缩存储 [Admin/Admin/settings/QA.py] [Admin/Admin/settings/LIVE.py]。同时设置 ` = True` 和 ` = ("", "https")`，确保在反向代理后正确识别 HTTPS 请求。 信任来源通过 `` 环境变量Config，默认值为 `https://agentinsight.goldebridge.com` [Admin/Admin/settings/QA.py]。

uWSGI 部署Config中，服务监听 `127.0.0.1:22522`，静态文件映射至 `AgentInsightService（统一使用全称，首次出现标注品牌名）/Admin/static`，采用 4 进程 2 线程的 worker 模型 [Admin/Admin/uwsgi.ini]。

#### 11.1.4. 菜单定制

Admin 后台集成  主题，菜单Config定义在 `base.py` 中，包含五个核心菜单变量 [Admin/Agents.md]：

| 菜单变量 | 功能定位 |
|---------|---------|
| `` | 用户信息管理 |
| `` | 用户数据管理 |
| `` | 内容管理 |
| `` | 系统工具 |
| `` | Privilege管理 |

系统提供 `` 和 `` 两套Config变量，支持不同管理员的个性化菜单布局。新增菜单项时需同步更新两套Config，子菜单通过嵌套 `models` 列表实现 [Admin/Agents.md]。

菜单项Config格式示例：

```python
{"name": "用户管理", "icon": "fa-solid fa-user", "url": "app/usermodel/"}
```

#### 11.1.5. 管理功能覆盖

Admin 后台覆盖以下核心管理域：

1. **用户管理**：用户账号的创建、禁用、角色分配，以及组织成员关系维护
2. **订单管理**：Payment订单的查询、状态跟踪、退款处理，对接微信/Payment宝Payment流水
3. **Alert管理**：Alert规则的Config、Alert记录的查看与处理、Alert通知渠道管理
4. **Agent Config管理**：Agent 实例的注册、参数Config、启停控制
5. **内容管理**：Bulletin、协议等运营内容的发布与审核

### 11.2. Agents Web 聊天界面

Agents Web 聊天界面是 AgentInsightService（统一使用全称，首次出现标注品牌名） 面向终端用户的交互入口，内嵌于 Agents 服务中，通过 `server.py` 模板渲染实现。该界面提供与 Agent 的实时对话能力，支持流式响应展示，使用户能够直观地观察 Agent 的推理与回答过程。

#### 11.2.1. 界面架构与路由

聊天界面由 Agents 服务独立提供，前端静态资源由该服务自行管理。界面通过 API 网关统一路由，与主 API 服务形成前后端分离架构。Agents 服务基于 Python 技术栈构建，依赖 `openai`、`httpx`、`pydantic`、`pydantic-settings` 等核心库 [Agents/pyproject.toml] [Agents/requirements.txt]。

#### 11.2.2. 流式对话机制

聊天界面的核心特性是**流式对话显示**。当用户发送消息后，界面通过 Server-Sent Events (SSE) 或  建立持久连接，Agent 的响应内容以流式方式逐块推送至前端，实现打字机效果。这种交互模式显著提升了用户体验，使用户能够实时感知 Agent 的处理进度。

流式对话的关键流程：

1. 用户在聊天输入框提交消息
2. 前端通过 API 网关将消息路由至 Agents Service
3. Agents 服务调用底层大模型（通过 LangChain.Providers.OpenAI 或 Microsoft. 集成）
4. chunk形式返回
5. 前端逐块渲染响应内容，实现流式展示

#### 11.2.3. Session管理

聊天界面支持多Session管理，每个Session对应一个独立的 Agent 对话上下文。Session数据通过 `AgentSessionController` 进行管理，相关端点包括 [API/Controllers/AgentManagement/AgentSessionController.cs]：

| 端点 | 方法 | 功能 |
|------|------|------|
| `GET /api/agent/session` | Get | 获取Session列表 |
| `GET /api/agent/session/delete` | Delete | 删除指定Session |
| `POST /api/agent/session` | Post | 创建或更新Session |

Session不存在时返回 ` = 150021` 错误码。

#### 11.2.4. 界面功能特性

聊天界面提供以下核心功能：

1. **多轮对话**：支持上下文关联的多轮对话，Agent 能够理解并引用历史消息
2. **流式响应**：实时展示 Agent 的生成过程，支持中途停止
3. **Session历史**：查看历史Session记录，支持Session切换与恢复
4. **Agent Config展示**：展示当前 Agent 的Config信息，包括模型参数、检索策略等
5. **报告模板**：支持预设报告模板，快速生成结构化分析报告

#### 11.2.5. 安全与鉴权

聊天界面的访问通过 API 网关统一鉴权。网关层由 `AgentInsightTransformProvider` 实现请求转换，支持 Basic Auth 与 JWT 两种认证方式 [API/System/Handlers/AgentInsightTransformProvider.cs]。API Key 验证失败时返回 ` = 100038` 错误码，API Key 不存在时返回 ` = 100031`。

#### 11.2.6. 界面与 API 网关集成

聊天界面的所有请求均通过 API 网关统一路由，网关负责请求转发、认证鉴权、速率限制等横切关注点。前端静态资源由 Agents 服务直接提供，而动态 API 请求则通过网关转发至后端服务。这种架构确保了：

界面的所有请求均通过 API 网关统一路由，网关负责请求转发、认证鉴权、速率限制等横切关注点。前端静态资源由 Agents 服务直接提供，而动态 API 请求则通过网关转发至后端服务。这种架构确保了：

- **统一入口**：所有请求经过单一入口，便于安全策略实施
- **服务隔离**：前端资源与后端 API 分离，降低耦合度
- **弹性扩展**：各服务可独立水平扩展，网关负责负载均衡

#### 11.2.7. 部署与运维

Agents 服务通过 `pyproject.toml` 管理依赖，支持独立部署。在 Docker 环境中，服务作为独立容器运行，通过 `` 网络与其他服务通信。聊天界面的静态资源由 Agents 服务直接托管，无需额外的  或静态文件服务器。

---

## 12. 测试策略

AgentInsightService（统一使用全称，首次出现标注品牌名） 是一个可Observation性数据平台，提供 Trace 数据摄入、查询聚合、Alert评估、Payment管理及用户组织Privilege管理等核心能力。其技术栈覆盖 .NET API Service（基于 MediatR、YARP 反向代理、Npgsql、Redis）与 Python Agents Service（基于 openai、pydantic、LangChain）。为保证多语言、多模块、多数据源（PostgreSQL、ClickHouse、Redis）架构下的交付质量，本章定义分层测试策略、单元测试与集成测试的规范、测试环境与工具链的选型，并明确质量度量指标与 CI 流水线要求。测试流程遵循 `Admin/Agents.md` 中定义的测试计划制定、用例设计、用例评审、测试执行、测试报告与评审的完整闭环 [Admin/Agents.md]。

### 12.1. 测试分层

AgentInsightService（统一使用全称，首次出现标注品牌名） 的测试体系划分为四个层次，自底向上依次为单元测试、集成测试、系统测试与验收测试。各层次职责边界清晰，下层测试为上层提供质量基座，上层测试覆盖跨模块协同场景。

**单元测试层**聚焦于单个类或方法的独立验证，不依赖外部基础设施（数据库、Redis、文件系统）。该层主要覆盖核心 Service 与 Handler 的业务逻辑分支，例如 `PaymentService` 的订单状态更新与签名验证逻辑 [API/Common/Services/PaymentService.cs:11]、`AlertService` 的Alert条件评估与消息构建逻辑 [API/Common/Services/AlertService.cs:11]、`UserService` 的用户创建与 Token 生成逻辑 [API/Common/Services/UserService.cs:11]。单元测试要求运行速度快、隔离性强，任何外部依赖均通过接口抽象或 Mock 框架替代。

**集成测试层**验证多个模块或组件之间的交互，重点覆盖跨模块业务流、数据访问层与外部服务（PostgreSQL、Redis、ClickHouse）的联通性。该层使用内存数据库或 Testcontainers 模拟真实基础设施，确保测试环境可重复、可清理。集成测试覆盖Payment回调处理（微信/Payment宝签名验证与订单状态联动）、Alert评估流程（条件判断→消息构建→指标查询）、Trace 数据摄入与查询链路（`BullMqService` 的入队/出队与 `MetricsHandler` 的查询聚合）等关键跨模块流程。

**系统测试层**在完整部署环境下验证端到端业务流程，包括用户注册→登录→创建项目→上报 Trace→查询 Trace→ConfigAlert→接收Alert的完整链路，以及Payment下单→回调→订单状态更新的Payment链路。该层同时覆盖性能测试与安全测试，性能测试需明确响应时间、并发用户数、吞吐量、资源利用率等指标 [Admin/Agents.md]，安全测试包含漏洞扫描与安全审计。

**验收测试层**依据需求文档与测试报告进行最终验收评审，由产品经理和测试工程师共同确认测试范围、用例执行情况、缺陷统计、覆盖率数据与风险评估 [Admin/Agents.md]。

各层测试的职责、执行时机与质量门禁要求如下表所示：

| 测试层次 | 验证重点 | 执行时机 | 质量门禁 |
|---------|---------|---------|---------|
| 单元测试 | 类/方法级逻辑正确性 | 每次代码提交 | 行覆盖率 ≥ 80% |
| 集成测试 | 模块间交互与数据层联通 | 每日 CI / 合并前 | 关键流程 100% 通过 |
| 系统测试 | 端到端业务流程、性能、安全 | 版本发布前 | 回归通过率 ≥ 95% |
| 验收测试 | 需求符合度与交付质量 | 版本发布评审 | 致命/严重缺陷遗留数 = 0 |

### 12.2. 单元测试

单元测试项目位于 `UnitTest/` 目录，使用 xUnit 作为测试框架，覆盖 API 核心 Handler 与 Service 的业务逻辑。测试用例遵循 Arrange-Act-Assert（AAA）模式，确保每个用例独立可运行、不依赖特定数据库数据 [Admin/Agents.md]。

**测试范围与优先级**：

| 优先级 | 被测类 | 关键方法 | 测试重点 |
|-------|--------|---------|---------|
| P0 | `PaymentService` | `CreateOrder`、`UpdateOrderState`、`ExamineAlipaySignature` | 订单状态流转、Payment宝签名验证、微信/Payment宝分支逻辑 [API/Common/Services/PaymentService.cs:11] |
| P0 | `AlertService` | `IsConditionMet`、`EvaluateField`、`BuildAlertMessage` | Alert条件判断、字段评估、消息格式构建 [API/Common/Services/AlertService.cs:11] |
| P0 | `UserService` | `CreateNewUser`、`CreateRefreshTokenAndSetHttpContext` | 用户创建、Token 生成与Session记录 [API/Common/Services/UserService.cs:11] |
| P1 | `WeChatService` | `ExamineSignature`、`LoginByWeChatMiniProgram` | 微信签名验证、小程序登录流程 [API/Common/Services/WeChatService.cs:11] |
| P1 | `BullMqService` | `EnqueueTraceIngestionAsync`、`DequeueTraceIngestionAsync`、`AcknowledgeTraceIngestionAsync` | Redis 队列入队/出队/确认逻辑 [API/Common/Services/BullMqService.cs:11] |
| P1 | `ApiHandlerBase` | `RequireOrgMembership`、`RequireOrgAdmin`、`RequireAccessibleProject` | 组织Privilege验证、项目访问控制 [API/Handlers/ApiHandlerBase.cs:11] |
| P2 | `SettingService` | `GetWeChatSetting`、`GetAlipaySetting` | PaymentConfig缓存读取 [API/Common/Services/SettingService.cs:11] |

**测试用例设计规范**：

- **正常路径**：验证方法在合法输入下返回预期结果，例如 `PaymentService.CreateOrder` 在有效订单参数下创建订单实体并返回订单号。
- **异常路径**：验证方法在非法输入或异常条件下抛出预期异常或返回错误码，例如 `AlertService.IsConditionMet` 在条件字段缺失时返回 `false`。
- **边界条件**：验证空值、超长字符串、特殊字符等边界输入，例如 `WeChatService.ExamineSignature` 在签名为空或格式错误时返回验证失败。
- **Mock 策略**：外部依赖（`IUserService`、`IOrderRepository`、`IWeChatSignatureService`、`IHttpRequestBuilderService`）使用 Mock 框架隔离，确保单元测试仅验证被测类自身逻辑。

**测试代码组织**：

```
UnitTest/
├── Services/
│   ├── PaymentServiceTests.cs
│   ├── AlertServiceTests.cs
│   └── UserServiceTests.cs
├── Handlers/
│   ├── UserHandlerTests.cs
│   └── OrderHandlerTests.cs
└── Extensions/
    └── ObjectExtensionTests.cs
```

`ObjectExtensionTests.cs` 中定义了测试枚举用于扩展方法的测试验证 [UnitTest/Extensions/ObjectExtensionTests.cs:30]，确保工具类方法的正确性。

**质量要求**：

- 单元测试行覆盖率 ≥ 80% [Admin/Agents.md]
- 测试用例执行率 100% [Admin/Agents.md]
- 每个被测方法至少包含 1 个正常路径用例和 1 个异常路径用例
- 测试不依赖特定数据库数据，可独立运行 [Admin/Agents.md]

### 12.3. 集成测试

集成测试验证跨模块业务流程的正确性，重点覆盖Payment回调、Alert评估、Trace 数据摄入等涉及多个服务与数据源交互的场景。测试项目包含 `TraditionalChineseExtensionExtendedCoverageTests`、`TraditionalChineseExtensionFurionIntegrationTests`、`AgentInsightTransformProviderCoverageTests`、`AgentInsightTransformProviderBehavioralTests`、`WeChatSignatureHelperFurionIntegrationTests`、`ConfigurationPlaceholderResolverDirectTests` 等测试类，覆盖不同模块的集成场景。

**关键集成测试场景**：

| 场景 | 涉及模块 | 验证内容 |
|------|---------|---------|
| Payment回调处理 | `PaymentService` + `OrderHandler` + 数据库 | 微信/Payment宝回调签名验证、订单状态更新、事务一致性 |
| Alert评估流程 | `AlertService` + `MetricsHandler` + 数据库 | Alert条件判断、指标查询、Alert消息构建与持久化 |
| Trace 数据摄入 | `BullMqService` + Redis + ClickHouse | 消息入队/出队、数据写入 ClickHouse、`AcknowledgeTraceIngestionAsync` 确认机制 |
| 请求认证转换 | `AgentInsightTransformProvider` + YARP | Basic Auth / JWT 认证、API Key 验证、速率限制 [API/System/Handlers/AgentInsightTransformProvider.cs:11] |
| 微信签名验证 | `WeChatService` + Config中心 | 微信服务器签名验证、AccessToken 获取与缓存 |

**数据层测试策略**：

数据层测试使用内存数据库或 Testcontainers 模拟 PostgreSQL/Redis 环境，确保测试的可重复性与隔离性。具体策略如下：

- **PostgreSQL**：使用 Testcontainers 启动真实 PostgreSQL 容器，执行建表脚本并注入测试种子数据，验证 `Npgsql` 数据访问层的 CRUD 操作与事务行为。连接字符串使用测试环境变量（`POSTGRES_HOST`、`POSTGRES_PORT`、`POSTGRES_DB`、`POSTGRES_USER`、`POSTGRES_PASSWORD`）。
- **Redis**：使用 Testcontainers 启动 Redis 容器，验证 `BullMqService` 的队列操作（入队、出队、确认）以及 `SettingService` 的Config缓存读写。连接Config使用 `REDIS_HOST`、`REDIS_PORT` 测试环境变量。
- **ClickHouse**：使用 Testcontainers 启动 ClickHouse 容器，验证 Trace 数据写入与查询聚合逻辑，连接Config使用 `CLICKHOUSE_HOST`、`CLICKHOUSE_PORT`、`CLICKHOUSE_DB`、`CLICKHOUSE_USER`、`CLICKHOUSE_PASSWORD` 测试环境变量。

**集成测试执行要求**：

- 测试用例必须覆盖正常路径与异常路径 [Admin/Agents.md]
- 测试可独立运行，不依赖特定数据库数据 [Admin/Agents.md]
- 每个集成测试类应包含 `[Trait("Category", "Integration")]` 特性标记，便于 CI 流水线分类执行
- 测试数据在用例执行后自动清理，避免数据残留影响后续用例

### 12.4. 测试环境与工具

**测试环境拓扑**：

| 环境 | 用途 | 基础设施 |
|------|------|---------|
| 本地开发环境 | 单元测试与调试 | 内存数据库、Mock 外部依赖 |
| CI 环境 | 自动化测试与覆盖率报告 | Testcontainers（PostgreSQL/Redis/ClickHouse） |
| 预发布环境 | 系统测试与性能测试 | 与生产环境等价的容器化部署 |
| 生产环境 | 冒烟测试与监控 | 生产实例子集 |

**工具链选型**：

| 工具 | 用途 | 说明 |
|------|------|------|
| xUnit | 单元测试框架 | 支持数据驱动测试与并行执行 |
| Testcontainers | 集成测试基础设施 | 模拟 PostgreSQL/Redis/ClickHouse 环境 |
| Moq / NSubstitute | Mock 框架 | 隔离外部依赖 |
| Coverlet | 覆盖率收集 | 生成行覆盖率报告 |
| ReportGenerator | 覆盖率报告生成 | 生成 HTML/XML 格式报告 |
| GitHub Actions | CI 流水线 | 自动执行测试套件并生成覆盖率报告 |

**CI 流水线设计**：

CI 流水线在 `.github` 目录下定义，每次代码推送或 Pull Request 时自动执行以下阶段：

1. **构建阶段**：编译 .NET API 项目与 Python Agents Project，确保代码可构建。依赖声明见 `Admin/requirements.txt` 与 `Agents/pyproject.toml`。
2. **单元测试阶段**：执行 `UnitTest/` 项目下的全部单元测试，使用 Coverlet 收集覆盖率数据，阈值设定为行覆盖率 ≥ 80% [Admin/Agents.md]。若覆盖率低于阈值，流水线失败并阻断合并。
3. **集成测试阶段**：启动 Testcontainers 容器，执行集成测试套件（含 `TraditionalChineseExtensionExtendedCoverageTests`、`AgentInsightTransformProviderBehavioralTests` 等），验证跨模块流程。
4. **覆盖率报告阶段**：使用 ReportGenerator 生成覆盖率报告，上传至 CI 产物中心供团队审阅。
5. **质量门禁**：测试用例执行率 100%、回归测试通过率 ≥ 95%、致命/严重缺陷遗留数 0 [Admin/Agents.md]。

**质量度量指标**：

| Metric | 目标值 |
|------|--------|
| 单元测试行覆盖率 | ≥ 80% |
| 测试用例执行率 | 100% |
| 缺陷关闭率（验收前） | ≥ 95% |
| 致命/严重缺陷遗留数（验收前） | 0 |
| 回归测试通过率 | ≥ 95% |

**测试报告要求**：

每次测试执行完毕后必须出具测试报告文档，包含测试范围、用例执行情况、缺陷统计、覆盖率数据、风险评估 [Admin/Agents.md]。测试报告由产品经理和测试工程师共同评审确认，作为版本发布的质量依据。性能测试报告由架构师和运维工程师共同评审，制定优化方案；性能不达标时，需制定优化方案、实施优化、重新测试，直到达标或经架构师确认接受 [Admin/Agents.md]。

---

## 13. 附录

本附录为 AgentInsightService（统一使用全称，首次出现标注品牌名） 技术文档的补充参考部分，包含术语表、图表索引、参考资料与变更历史四个子章节。AgentInsightService（统一使用全称，首次出现标注品牌名） 是一个面向可Observation性与智能分析场景的服务平台，核心能力涵盖 Trace 数据摄入与查询、Agent Config与Session管理、Alert规则评估、Payment与订单管理、组织Privilege控制等，技术栈基于 .NET (ASP.NET Core) 与 Python (FastAPI) 构建，并集成 ClickHouse、PostgreSQL、Redis、YARP 等基础组件。术语表与正文 §1.4 保持同步，图表索引汇总全文图表位置，参考资料列出外部依赖文档，变更历史记录文档修订轨迹。

### 13.1. A 术语表

以下术语表与正文 §1.4 保持一致，列出 AgentInsightService（统一使用全称，首次出现标注品牌名） 技术文档中出现的核心术语及其释义。术语按字母顺序排列，代码标识符保留原始大小写。

| MediatR | 中介者模式库，用于解耦请求处理与通知分发，Payment交易保存、微信通知处理、Alert触发均使用 MediatR  |
| MemoryManager | Agents 服务中的共享内存Manager，实现跨 Agent 上下文共享和Session持久化 [Agents/server.py] |
| Order | 订单实体，由 `OrderHandler.PlaceOrder` 创建，支持微信/Payment宝Payment [API/Handlers/PaymentManagement/OrderHandler.cs:22] |
| PaymentService | Payment核心服务，负责订单创建、Payment参数获取、订单状态更新、签名验证 [API/Common/Services/PaymentService.cs:11] |
| Redis | 内存键值存储，BullMQ与缓存 |
| Repository | 数据仓储层，负责数据库读写操作 |
| Trace | 链路Trace数据单元，通过 `BullMqService.EnqueueTraceIngestionAsync` 入队异步摄入 [API/Common/Services/BullMqService.cs:32] |
| UserService | 用户管理服务，负责用户创建、Session管理、Token 生成、组织Privilege管理 [API/Common/Services/UserService.cs:11] |
| WeChatService | 微信生态集成服务，负责签名验证、 管理、微信账号绑定、小程序登录 [API/Common/Services/WeChatService.cs:11] |
| YARP | Yet Another Reverse Proxy，反向代理组件，用于请求转发与路由 |

### 13.2. B 图表索引

本节汇总 AgentInsightService（统一使用全称，首次出现标注品牌名） 技术文档中出现的全部图表，按章节顺序排列。每项包含图表编号、图表名称、所在章节与内容摘要，便于读者快速定位。

| 图表编号 | 图表名称 | 所在章节 | 内容摘要 |
|----------|----------|----------|----------|
| 图 1 | 系统总体架构图 | 第 2 章 系统架构 | 展示 API 层、Handler 层、Service 层、Repository 层与外部依赖（ClickHouse、PostgreSQL、Redis、微信/Payment宝）之间的调用关系 |
| 图 2 | 请求处理时序图 | 第 3 章 核心流程 | 描述用户请求从 Controller → Handler → Service → Repository 的完整调用链，以及异步任务通过 BullMqService 入队处理的时序 |
| 图 3 | Payment回调处理时序图 | 第 3 章 核心流程 | 展示Payment回调从 NotifyController → NotifyHandler → PaymentService → 更新订单/Privilege的完整流程 |
| 图 4 | Alert触发流程时序图 | 第 3 章 核心流程 | 描述定时任务触发 AlertService 评估Alert条件，并通过 Notification Handlers 发送系统通知/短信的流程 |
| 图 5 | Agents 服务架构图 | 第 4 章 Agents Service | 展示 FastAPI 服务器、Agent 注册机制、共享内存管理与流式响应的组件关系 |
| 图 6 | 双数据库路由示意图 | 第 5 章 数据存储 | 展示 `` 根据 `` 前缀将请求路由至 `default` 库或 `data` 库的逻辑 [Admin/Agents.md] |
| 图 7 | 部署拓扑图 | 第 6 章 部署运维 | 展示 API Service、Agents Service、Admin 服务与 PostgreSQL、ClickHouse、Redis 的部署关系 |

### 13.3. C 参考资料

本节列出 AgentInsightService（统一使用全称，首次出现标注品牌名） 开发与运维过程中涉及的参考资料，包括官方文档、SDK 文档与第三方框架文档。所有参考资料均为公开可获取的资源，供读者进一步查阅。

**框架与运行时文档**

| 资料名称 | 说明 | 用途 |
|----------|------|------|
| .NET 8 官方文档 | Microsoft .NET 官方文档，涵盖 ASP.NET Core、C# 语言、EF Core 等 | API 服务开发基础框架 |
| FastAPI 官方文档 | FastAPI 框架文档，涵盖路由、依赖注入、 等 | Agents 服务开发框架 |
| Django 官方文档 | Django 框架文档，涵盖 ORM、Admin、中间件等 | Admin 后台管理服务开发框架 |

**SDK 与组件文档**

| 资料名称 | 说明 | 用途 |
|----------|------|------|
| AgentInsight SDK 文档 | AgentInsight 官方 SDK 文档，涵盖 API 调用、数据模型、错误码定义 | 外部系统集成 AgentInsightService（统一使用全称，首次出现标注品牌名） |
| LangChain.Providers.OpenAI 文档 | LangChain .NET 的 OpenAI Provider 文档 | Agents 服务中 LLM 调用 |
| Microsoft. 文档 | Semantic Kernel SDK 文档，涵盖插件、规划器、记忆等 | Agents 服务中语义内核集成 |
| .Standard 文档 | Payment宝 .NET SDK 文档，涵盖即时到账、签名验证、退款等 | Payment宝Payment功能开发 |
| Yarp. 文档 | YARP 反向代理组件文档，涵盖路由Config、负载均衡、中间件 | API 网关与反向代理Config |

**数据库与中间件文档**

| 资料名称 | 说明 | 用途 |
|----------|------|------|
| ClickHouse 官方文档 | ClickHouse 列式数据库文档，涵盖 SQL 语法、表引擎、数据导入导出 | Trace 数据存储与查询 |
| PostgreSQL 官方文档 | PostgreSQL 关系型数据库文档，涵盖 SQL、索引、事务、分区 | 业务数据存储 |
| Redis 官方文档 | Redis 内存数据库文档，涵盖数据结构、持久化、集群 | 消息队列与缓存 |

**第三方库文档**

| 资料名称 | 说明 | 用途 |
|----------|------|------|
| MediatR 文档 | .NET 中介者模式库文档，涵盖请求/通知处理、管道行为 | 解耦请求处理与事件通知 |
| Npgsql 文档 | .NET PostgreSQL 驱动文档，涵盖连接管理、批量操作 | API 服务数据库访问 |
| .Redis 文档 | .NET Redis 客户端文档，涵盖连接池、异步操作 | API Service Redis 访问 |
| pydantic 文档 | Python 数据验证库文档，涵盖模型定义、验证器 | Agents 服务Config与数据模型 |
| openai Python SDK 文档 | OpenAI Python SDK 文档，涵盖聊天补全、流式响应 | Agents Service LLM 调用 |

### 13.4. D 变更历史

本节记录 AgentInsightService（统一使用全称，首次出现标注品牌名） 技术文档的修订历史，包括修订日期、版本号、修订说明与修订作者。每次修订对应文档内容的增删改，确保文档与代码仓库保持同步。

| 版本 | 修订日期 | 修订说明 | 修订作者 |
|------|----------|----------|----------|
| v1.0 | 2025-01-15 | 初始版本，完成系统架构、核心流程、接口文档初稿 | 文档组 |
| v1.1 | 2025-02-01 | 新增 Agents 服务章节，补充 Agent 注册机制与流式响应说明 | 文档组 |
| v1.2 | 2025-02-15 | 补充双数据库路由说明，更新部署拓扑图 [Admin/Agents.md] | 文档组 |
| v1.3 | 2025-03-01 | 更新Payment回调流程，补充 MediatR 通知模式与重试机制说明 | 文档组 |
| v1.4 | 2025-03-15 | 新增附录章节（术语表、图表索引、参考资料、变更历史） | 文档组 |
| v1.5 | 2025-04-01 | 同步代码仓库最新变更，更新 API 端点清单与枚举定义 | 文档组 |
| v1.6 | 2025-04-15 | 修订术语表，与 §1.4 保持同步；补充参考资料条目 | 文档组 |

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
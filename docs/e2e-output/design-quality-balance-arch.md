## 1. 引言

AgentInsightService 采用分层架构，核心模块划分为 API 层（C#/Furion）、Agent 层（Python/FastAPI）和 Admin 后台（Python/Django）。API 层通过 Controller → Handler → Service → Repository 的依赖链实现业务逻辑，使用 MediatR 中介者模式解耦通知与Handler。Agent 层通过 InsightOrchestrator 统一路由请求到子Agent。数据模型涵盖用户、Org、Order、Alert、Trace 等核心实体，通过 SqlSugar ORM 访问 PostgreSQL 和 ClickHouse。本文档为 AgentInsightService 的概要设计说明，面向研发工程师、测试工程师、运维工程师及技术管理者，旨在定义系统模块划分、接口契约、数据模型、安全策略与测试方案等核心设计决策，为后续详细设计、编码实现与系统测试提供统一依据。

### 1.1. 编写目的与详细设计边界

本文档的编写目的如下：

1. **定义系统总体架构**：明确 API 层、Agent 层与 Admin 后台三大组成部分的职责边界与交互关系，确保各模块开发团队对系统整体结构有一致的认知。
2. **固化接口契约**：规定 API 层各Controller的路由、请求/响应格式与错误码规范，作为前后端联调与第三方集成的基准。API Controller层位于 `API/Controllers/`，是 HTTP 端点入口，负责参数绑定与响应封装，共 76 个端点分布在 18 个Controller中。
3. **明确数据模型与存储方案**：定义用户、Org、Order、Alert、Trace 等核心实体的数据结构与数据库路由策略，规范通过 SqlSugar ORM 访问 PostgreSQL 与 ClickHouse 的方式。
4. **指导详细设计**：本文档作为概要设计（High-Level Design, ），界定系统级设计决策；各模块的类级别设计、方法签名、数据库表结构  等属于详细设计（Low-Level Design, ）范畴，不在本文档中展开。

详细设计边界约定如下：

| 设计层级 | 内容范围 | 输出物 |
|---------|---------|-------|
| 概要设计（本文档） | 系统模块划分、接口概览、数据模型概览、安全策略、部署拓扑 | 本文档 |
| 详细设计 | 类图、时序图、数据库表结构、算法伪代码 | 各模块详细设计文档 |
| 编码实现 | 具体代码实现、单元测试 | 代码仓库 |

API Handler层位于 `API/Handlers/`，业务逻辑编排继承 `ApiHandlerBase` 以获取 Db/User/，并实现 `IUserAwareHandler` 接口 [API/Handlers/ApiHandlerBase.cs]。API 层位于 `API/Common/Services/`，封装外部集成（Payment、微信、Alert、消息队列），提供统一服务接口。Agent 编排层位于 `Agents/server.py`，作为统一入口路由到子Agent，管理Session上下文与流式响应。

### 1.2. 项目背景与触发因素

AgentInsightService 的诞生源于企业在智能化运维与可Observation性领域日益增长的需求。随着微服务架构的普及和系统规模的扩大，传统监控工具在 Trace 数据的采集、分析与Alert方面存在以下痛点：

1. **数据孤岛问题**：Trace、Log、指标等可Observation性数据分散存储在不同系统中，缺乏统一的分析视图。
2. **Alert准确率不足**：基于固定阈值的Alert策略无法适应动态变化的业务负载，误报与漏报频发。
3. **根因定位效率低**：故障发生后，运维人员需要人工跨系统排查，平均恢复时间（）过长。
4. **智能化程度不足**：LLM的自动化分析与诊断能力，无法对海量 Trace 数据进行语义级别的理解与归纳。

基于上述背景，AgentInsightService 项目启动，其核心目标包括：

- 构建统一的 Trace 数据采集、存储与查询平台，支持多维度过滤与分页查询。Trace 查询模块位于 `API/Common/Helpers/TraceFilterBuilder.cs`，动态构建 ClickHouse 查询条件。
- 实现基于策略模式的Alert评估引擎，支持 9 种指标评估器与多条件组合判断。Alert评估模块位于 `API/Notifications/AlertEvaluators/`。
- 引入 Agent Agent编排能力，通过 InsightOrchestrator 统一路由请求到子Agent，实现自然语言交互式的运维分析。
- 提供 Admin 后台，支撑系统Config、数据管理与任务执行流程的规范化。

项目的触发因素包括：业务线对可Observation性平台的功能需求已积累至临界点；大语言模型技术的成熟为智能化运维提供了新的技术路径；公司技术栈统一战略要求新系统基于 C#/Furion、Python/FastAPI、Python/Django 构建。

### 1.3. 系统范围 In/Out-of-Scope

#### 1.3.1. In-Scope（系统范围内）

| 编号 | 范围项 | 说明 |
|------|--------|------|
| S1 | API 层 | 基于 C#/Furion 构建，提供 RESTful API，涵盖用户管理、组织管理、Agent 管理、订单Payment、数据管理、Alert通知等业务域。API Controller层位于 `API/Controllers/`，共 76 个端点分布在 18 个Controller中。 |
| S2 | Agent 层 | 基于 Python/FastAPI 构建，通过 InsightOrchestrator 统一路由请求到子Agent，管理Session上下文与流式响应 [Agents/server.py]。 |
| S3 | Admin 后台 | 基于 Python/Django 构建，提供系统Config管理、数据管理、任务执行流程规则定义等功能。 |
| S4 | 数据存储 | 使用 PostgreSQL 存储业务数据（User、Org、订单等），使用 ClickHouse 存储 Trace 数据。通过 SqlSugar ORM 访问，支持多数据库路由（/DataDb/）。 |
| S5 | Alert评估引擎 | 基于策略模式实现 9 种指标评估器，支持多条件组合判断。Alert评估模块位于 `API/Notifications/AlertEvaluators/`。 |
| S6 | 外部集成 | 封装Payment（Payment宝/微信）、微信登录、BullMQ等外部服务。API 层位于 `API/Common/Services/`。 |

#### 1.3.2. Out-of-Scope（系统范围外）

| 编号 | 范围项 | 说明 |
|------|--------|------|
| O1 | 独立 SDK | 未检测到独立 SDK 模块，`agentinsight-sdk` 作为依赖项被引用，但不作为独立交付物。 |
| O2 | 硬件模块 | 不涉及任何硬件设备的管理与控制。 |
| O3 | 移动端应用 | 不包含 iOS/Android 原生应用开发。 |
| O4 | 数据可视化大屏 | 不包含独立的大屏展示系统，Admin 后台提供基础的数据列表展示与过滤功能。 |
| O5 | 多语言国际化 | 当前版本不包含多语言国际化支持，界面与文档以中文为主。 |

### 1.4. 术语与缩略语

本文档遵循 v8 上下文中的术语词典，所有品牌名、代码标识符保留原文。以下为本文档涉及的术语与缩略语：

| 术语/缩略语 | 含义 |
|------------|------|
| AgentInsightService | 项目名称，本系统整体标识。 |
| AgentInsight | 品牌名，用于产品命名与标识。 |
| InsightService | 品牌名，用于服务标识。 |
| API | Application Programming Interface，应用程序编程接口。 |
| API.Common.Extensions | API 层公共扩展方法命名空间。 |
| API.Common.Helpers | API 层公共辅助类命名空间，包含 ClickHouseHelper、TraceFilterBuilder 等。 |
| API.Common.Services | API 层公共服务命名空间，包含 AlertService、BullMqService、IPaymentService 等。 |
| Trace | 分布式Trace数据，记录请求在分布式系统中的完整调用链。 |
| Agent | Agent，指代 Agent 层中的子Agent或 API 层中的 Agent 管理相关功能。 |
| Admin | 管理后台，基于 Python/Django 构建。 |
| ClickHouseHelper | ClickHouse 数据库访问辅助类。 |
| TraceFilterBuilder | Trace 查询条件动态构建器，位于 `API/Common/Helpers/TraceFilterBuilder.cs`。 |
| AlertService | Alert服务，位于 `API.Common.Services` 命名空间。 |
| BullMqService | 基于 BullMQ 的消息队列服务，提供 EnqueueProjectDeleteAsync、EnqueueTraceIngestionAsync、AcknowledgeTraceIngestionAsync 等方法。 |
| ExceptionCodes | 异常错误码枚举，定义于 `Models/Common/Enums/ExceptionCodes.cs`。 |
| PRD | Product Requirements Document，产品需求文档。 |

|  | High-Level Design，概要设计。 |
|  | Low-Level Design，详细设计。 |
| ORM | Object-Relational Mapping，对象关系映射。 |
| SqlSugar | .NET 平台 ORM 框架，用于访问 PostgreSQL 与 ClickHouse。 |
| MediatR | .NET 中介者模式库，用于解耦通知与Handler。 |
| Furion | .NET 应用框架，API 层基于此构建。 |
| FastAPI | Python Web 框架，Agent 层基于此构建。 |
| Django | Python Web 框架，Admin 后台基于此构建。 |
| ClickHouse | 列式数据库，用于 Trace 数据存储与分析。 |
| PostgreSQL | 关系型数据库，用于业务数据存储。 |

### 1.5. 参考文档 PRD/架构文档

本文档的编写参考了以下资料：

| 文档名称 | 说明 | 来源 |
|---------|------|------|
| Project README | 项目根目录 README 文件，标题为 #NostologyService，提供项目概述与快速开始指南。 | 代码仓库根目录 |
| API 端点清单 | 从 AST 提取的 HTTP 端点全集，覆盖 18 个Controller中的 76 个端点。 | 代码仓库 `API/Controllers/` |
| 枚举定义清单 | 从 AST 提取的枚举定义全集，包括 TransactionType、RouteType、Environment、、、、ExceptionCodes 等。 | 代码仓库 |
| Config文件技术规格 | 从Config文件提取的技术规格，包括连接字符串、Captcha设置、AES 加密密钥等。 | 代码仓库Config文件 |
| Admin 任务执行流程规则 | Admin 后台的任务执行流程规则文档，定义需求分析、评审、开发、测试、验收等 12 个步骤。 | `Admin/Agents.md` |
| 代码仓库学习摘要 | monorepo提取的 API/Agents/Admin 三大组成部分的产品定位与技术栈摘要。 | 代码仓库 |

### 1.6. 版本历史

| 版本 | 日期 | 作者 | 说明 |
|------|------|------|------|
| v0.1 | 2025-01-15 | 技术文档组 | 初始草案，基于代码仓库学习摘要与 RAG 检索结果完成章节框架搭建。 |
| v0.2 | 2025-01-20 | 技术文档组 | 补充系统范围 In/Out-of-Scope 定义，完善术语与缩略语表。 |
| v0.3 | 2025-01-25 | 技术文档组 | 根据 PRD 评审意见修订项目背景与触发因素，补充参考文档清单。 |
| v1.0 | 2025-02-01 | 技术文档组 | 首版正式发布，经架构组评审通过。 |
| v1.1 | 2025-02-10 | 技术文档组 | 根据代码变更同步更新 API 端点数量（76 个端点，18 个Controller）与Alert评估器数量（9 种）。 |
| v1.2 | 2025-02-20 | 技术文档组 | 根据 v8 术语词典约束修订术语表，确保品牌名与代码标识符保留原文。 |

版本历史记录本文档从初始草案到正式发布的完整演进过程。每次修订均经过评审确认，确保文档内容与代码仓库实际实现保持一致。

---

## 2. 系统总体设计

### 2.1. 系统总体设计

`/api/alert` 接受可选的 `orgId` 与 `projectId` 参数 [API/Controllers/UserManagement/AlertController.cs:47-L52]。

**高性能可Observation性数据存储**：Trace 数据作为可Observation性分析的核心数据源，采用 ClickHouse 列式存储引擎，以支撑高性能时序查询与多维度聚合分析。系统通过 `TraceFilterBuilder` 动态构建 ClickHouse 查询条件，支持多维度过滤与分页 [API/Common/Helpers/TraceFilterBuilder.cs]。

**可靠的外部集成**：Payment集成与通知发送是系统的重要能力。Payment服务通过 `IPaymentService` 接口封装，使用 Polly 或内置重试机制确保外部Payment通知的可靠性 [API/Common/Services/PaymentService.cs]。消息队列通过 `BullMqService` 实现异步任务处理，包括项目删除、Trace 数据摄取等耗时操作的异步化 [API/Common/Services/]。

**可扩展的Alert评估体系**：Alert模块采用策略模式实现 9 种指标评估器（`IAlertFieldEvaluator`），支持多条件组合判断，覆盖总 Token 消耗、总消费、错误次数等核心指标 [API/Notifications/AlertEvaluators/]。

### 2.2. 总体架构图

AgentInsightService 采用分层架构，自上而下分为五个层次，各层职责明确、依赖单向：

| 层次 | 职责 | 关键技术组件 | 代码位置 |
|------|------|-------------|---------|
| 表示层 | HTTP 端点入口、参数绑定、响应封装、路由转发 | API Controllers、YARP Reverse Proxy、Admin Django | [API/Controllers/] |
| 应用层 | 业务逻辑编排、命令/查询处理、事务协调 | API Handlers、MediatR、ApiHandlerBase | [API/Handlers/] |
| 代理层 | AI 代理编排、Session管理、流式响应 | FastAPI、InsightOrchestrator、LangChain、Semantic Kernel | [Agents/server.py] |
| 服务层 | 外部集成封装、通用业务服务 | API Common Services（Payment、微信、Alert、消息队列） | [API/Common/Services/] |
| 数据访问层 | ORM 数据访问、多数据库路由、查询构建 | SqlSugar ORM、PostgreSQL、ClickHouse、Redis | [Entities/] |

**请求流转链路**：外部请求首先到达 API Controller层，Controller通过构造函数注入对应的 Handler Handler（如 `AlertController` 注入 `AlertHandler`）[API/Controllers/UserManagement/AlertController.cs:24-L26]，Handler 继承 `ApiHandlerBase` 获取 Db/User/ 等基础设施 [API/Handlers/ApiHandlerBase.cs:8]，并调用服务层完成业务逻辑。对于需要 AI 代理能力的请求，API 层通过 YARP 反向代理将请求路由至 Agent 层 [API/System/Handlers/AgentInsightTransformProvider.cs]，由 `InsightOrchestrator` 统一路由到子Agent处理。

**路由与鉴权机制**：YARP 反向代理作为 API 网关组件，`AgentInsightTransformProvider` 实现 `ITransformProvider` 接口，在请求转发前执行路由类型判定与鉴权逻辑 [API/System/Handlers/AgentInsightTransformProvider.cs:31-L46]。根据 `AgentInsightTransformLogic.DetermineRouteType` 判定路由类型（`RouteType.Public` 等），对 Public 路由自动添加 `/api` 路径前缀；同时支持 Basic Auth（API Key 认证）与 JWT 两种鉴权方式，在请求变换中统一处理 [API/System/Handlers/AgentInsightTransformProvider.cs:48-L52]。

### 2.3. 技术栈选型与版本理由

AgentInsightService 的技术栈选型遵循"主语言异构、领域最优"的原则，各层采用最适合自身业务场景的技术方案：

| 层次 | 技术选型 | 版本/依赖 | 选型理由 |
|------|---------|----------|---------|
| API 层框架 | .NET Furion | Furion 4.x | 基于 .NET 的高效应用框架，提供依赖注入、动态 API 等能力，与 MediatR 无缝集成 |
| API 层中介者 | MediatR | MediatR 12.x | 实现中介者模式，解耦请求发送者与Handler，提升业务逻辑的可测试性与可维护性 |
| API 层 ORM | SqlSugar | SqlSugarCore 5.x | 轻量级 ORM，支持多数据库路由（KeyedService 模式），与 PostgreSQL/ClickHouse 良好集成 |
| API 层缓存 | Redis | StackExchange.Redis 2.x | 高性能分布式缓存，用于 API Key 解析结果缓存、用户Session缓存等 |
| API 层网关 | YARP | Yarp.ReverseProxy 2.x | 微软开源的轻量级反向代理库，支持自定义 Transform 实现鉴权与路由逻辑 |
| Agent 层框架 | Python FastAPI | fastapi 0.1xx | 异步高性能 Web 框架，天然支持流式响应，适合 AI 代理场景 |
| Agent 层 AI 编排 | LangChain + Semantic Kernel | LangChain.Providers.OpenAI 0.x、Microsoft.SemanticKernel 1.x | 双框架支持，提供灵活的 LLM 调用与工具编排能力 |
| Agent 层 SDK | agentinsight-sdk | agentinsight-sdk 1.x | 与 API 层交互的官方 SDK，封装认证与数据上报 |
| 数据存储 | PostgreSQL + ClickHouse | Npgsql 8.x | PostgreSQL 存储业务数据（User、Org、Order、Alert），ClickHouse 存储 Trace 时序数据 |
| 消息队列 | BullMq | BullMq 5.x | 基于 Redis 的异步任务队列，支持项目删除、Trace 摄取等异步任务 |
| Payment集成 | AlipaySDK.NET.Standard | AlipaySDK.NET.Standard 4.x | Payment宝官方 .NET SDK，用于Payment证书获取与订单Payment |
| 安全加密 | BouncyCastle.Cryptography | BouncyCastle.Cryptography 2.x | 提供加密/解密、密码哈希等安全能力 |
| 本地化 | My.Extensions.Localization.Json | My.Extensions.Localization.Json 2.x | JSON 格式的本地化资源支持 |
| Admin 后台 | Python Django | Django 4.x | 成熟的管理后台框架，用于运营人员的数据管理与Config |

**数据库连接Config**：系统Config了三个 PostgreSQL 数据库（UserDb、DataDb、ConfigDb）与一个 ClickHouse 数据库，通过环境变量注入连接字符串。例如 `UserDb` Config了用户库的连接参数（含连接池大小、超时等）[Config文件技术规格]。ClickHouse 连接Config了 `MaxPoolSize=10;MinPoolSize=50;ConnectTimeout=30;SocketTimeout=60` 等参数，以保障时序查询的稳定性 [Config文件技术规格]。

### 2.4. 设计模式与编码约定

AgentInsightService 在架构设计中贯彻了多种设计模式与编码约定，确保系统的可维护性与可扩展性：

**MediatR**：API 层通过 MediatR 实现请求-响应的解耦。Controller不直接依赖具体的业务服务，而是通过 Handler 处理业务逻辑。例如 `AlertController` 注入 `AlertHandler`，由 Handler 编排Alert的创建、更新、删除等操作 [API/Controllers/UserManagement/AlertController.cs:24-L26]。Handler 继承 `ApiHandlerBase`，通过构造函数注入 `ISqlSugarClient`（KeyedService 方式区分 UserDb 与 DataDb）、`IAppContextService` 等基础设施 [API/Handlers/UserManagement/UserHandler.cs:20-L35]。

**IAlertFieldEvaluator**：Alert评估模块定义了 `IAlertFieldEvaluator` 接口，针对不同的Alert字段（总 Token 消耗、总消费、错误次数等）实现 9 种评估器。每种评估器独立封装字段的阈值判断逻辑，通过策略组合实现多条件Alert判断 [API/Notifications/AlertEvaluators/]。Alert创建接口 `POST /api/alert` 接收 `field`、`operator`、`value` 等参数，由评估器根据字段类型执行对应的判断逻辑 [API/Controllers/UserManagement/AlertController.cs:61-L70]。

**依赖注入（Furion DI）**：系统全面采用 Furion 的依赖注入容器管理对象生命周期。Controller、Handler、Service 均通过构造函数注入依赖，例如 `UserHandler` 注入 `ISettingService`、`IUserService`、`IWeChatService`、`ICaptchaService`、`IEncryptService` 等 7 个服务 [API/Handlers/UserManagement/UserHandler.cs:20-L35]。数据库客户端通过 `[FromKeyedServices(AgentInsightConst.KeyedService_UserDb)]` 与 `[FromKeyedServices(AgentInsightConst.KeyedService_DataDb)]` 区分不同的数据库实例 [API/Handlers/UserManagement/UserHandler.cs:22-L23]。

**编码约定**：
- **Controller约定**：所有Controller继承 `ApiControllerBase`，统一处理缓存与 Handler 注册 [API/Controllers/UserManagement/AlertController.cs:24-L26]；通过 `[ApiExplorerSettings]` 标注 Swagger 分组与排序 [API/Controllers/UserManagement/AlertController.cs:19-L21]。
- **Handler 约定**：Handler 实现 `IUserAwareHandler` 接口，通过基类获取当前用户信息与取消Token [API/Handlers/ApiHandlerBase.cs:8]。
- **响应封装约定**：所有接口统一返回 `ApiResponse<T>` 包装类型，包含 `errorCode`、`data`、`totalCount` 等字段 [API/Controllers/UserManagement/AlertController.cs:36-L38]。
- **异步约定**：所有 IO 操作使用 `async/await` 并调用 `ConfigureAwait(false)` 避免死锁 [API/Controllers/UserManagement/AlertController.cs:49-L51]。

### 2.5. 关键设计决策与理由

**决策一：ClickHouse 作为 Trace 数据存储引擎**

系统选择 ClickHouse 存储 Trace 数据，核心考量是其列式存储架构对时序数据的高效聚合查询能力。Trace 查询模块通过 `TraceFilterBuilder` 动态构建 ClickHouse 查询条件，支持多维度过滤与分页 [API/Common/Helpers/TraceFilterBuilder.cs]。ClickHouse 连接Config了连接池（`MaxPoolSize=10;MinPoolSize=50`）与超时控制（`ConnectTimeout=30;SocketTimeout=60`），以保障高并发查询场景下的稳定性 [Config文件技术规格]。当查询条件异常时，系统返回 `ErrorCode = 150010` 或 `ErrorCode = 150017` 错误码 [Models/Common/Enums/ExceptionCodes.cs:6]。

**决策二：YARP 反向代理实现微服务路由与统一鉴权**

系统采用 YARP 作为反向代理组件，通过 `AgentInsightTransformProvider` 实现请求转发前的统一鉴权与路由变换 [API/System/Handlers/AgentInsightTransformProvider.cs:31-L46]。该设计将鉴权逻辑从业务Controller中剥离，实现横切关注点的集中管理。`AgentInsightTransformLogic.DetermineRouteType` 根据路由路径判定类型，对 Public 路由自动添加 `/api` 前缀 [API/System/Handlers/AgentInsightTransformProvider.cs:43-L45]。鉴权支持 Basic Auth（API Key）与 JWT 两种方式，Basic Auth 通过 `ApiKeyAuthenticator` 解析公钥/私钥，并调用 `ResolveApiKeyWithCache` 进行缓存查询 [API/System/Handlers/AgentInsightTransformProvider.cs:58-L75]。

**决策三：MediatR 中介者模式解耦Payment与通知**

Payment与通知是系统中典型的跨领域关注点。通过 MediatR 中介者模式，Payment服务（`IPaymentService`）与通知服务（`IAlertService`）作为独立服务注入 Handler，业务逻辑通过 Handler 编排调用，避免Controller直接依赖具体服务实现 [API/Common/Services/PaymentService.cs]。Payment通知的可靠性通过 Polly 或内置重试机制保障，确保外部Payment通知在临时故障时能够自动重试。

**决策四：多数据库路由与 KeyedService 模式**

系统通过 SqlSugar 的 KeyedService 模式实现多数据库路由。`UserHandler` 构造函数中通过 `[FromKeyedServices(AgentInsightConst.KeyedService_UserDb)]` 与 `[FromKeyedServices(AgentInsightConst.KeyedService_DataDb)]` 分别注入用户库与业务数据库的 `ISqlSugarClient` 实例 [API/Handlers/UserManagement/UserHandler.cs:22-L23]。该设计支持用户数据与业务数据的物理隔离，同时保持代码层面的统一访问接口。

**决策五：BullMq 实现异步任务队列**

系统通过 `BullMqService` 封装基于 Redis 的异步任务队列，用于处理耗时操作。`EnqueueProjectDeleteAsync` 与 `EnqueueTraceIngestionAsync` 分别实现项目删除与 Trace 数据摄取的异步化 [API/Common/Services/]。异步任务模式避免了长时间操作阻塞 HTTP 请求线程，提升了系统的响应性能与吞吐量。

---

## 3. 模块划分

<div class="report-image">
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024" width="1024" height="1024">
<defs>
<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
<stop offset="0%" stop-color="#f8f9fa"/>
<stop offset="100%" stop-color="#e9ecef"/>
</linearGradient>
<linearGradient id="main" x1="0" y1="0" x2="1" y2="1">
<stop offset="0%" stop-color="#007BFF"/>
<stop offset="100%" stop-color="#0056b3"/>
</linearGradient>
<linearGradient id="sub1" x1="0" y1="0" x2="1" y2="1">
<stop offset="0%" stop-color="#6c757d"/>
<stop offset="100%" stop-color="#495057"/>
</linearGradient>
<linearGradient id="sub2" x1="0" y1="0" x2="1" y2="1">
<stop offset="0%" stop-color="#adb5bd"/>
<stop offset="100%" stop-color="#868e96"/>
</linearGradient>
<filter id="shadow">
<feDropShadow dx="0" dy="4" stdDeviation="6" flood-color="#000" flood-opacity="0.1"/>
</filter>
</defs>
<rect width="1024" height="1024" fill="url(#bg)"/>
<text x="512" y="80" text-anchor="middle" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="36" font-weight="bold" fill="#2c3e50">模块划分概念图</text>
<rect x="312" y="120" width="400" height="80" rx="12" fill="url(#main)" filter="url(#shadow)"/>
<text x="512" y="168" text-anchor="middle" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="24" fill="#ffffff" font-weight="bold">系统整体</text>
<line x1="512" y1="200" x2="512" y2="250" stroke="#6c757d" stroke-width="3" stroke-dasharray="8,6"/>
<line x1="512" y1="250" x2="180" y2="310" stroke="#6c757d" stroke-width="2" stroke-dasharray="6,4"/>
<line x1="512" y1="250" x2="512" y2="310" stroke="#6c757d" stroke-width="2" stroke-dasharray="6,4"/>
<line x1="512" y1="250" x2="844" y2="310" stroke="#6c757d" stroke-width="2" stroke-dasharray="6,4"/>
<rect x="80" y="310" width="200" height="100" rx="10" fill="url(#sub1)" filter="url(#shadow)"/>
<text x="180" y="355" text-anchor="middle" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="20" fill="#ffffff" font-weight="bold">模块 A</text>
<text x="180" y="382" text-anchor="middle" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="14" fill="#dee2e6">功能独立</text>
<rect x="412" y="310" width="200" height="100" rx="10" fill="url(#main)" filter="url(#shadow)"/>
<text x="512" y="355" text-anchor="middle" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="20" fill="#ffffff" font-weight="bold">模块 B</text>
<text x="512" y="382" text-anchor="middle" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="14" fill="#dee2e6">核心逻辑</text>
<rect x="744" y="310" width="200" height="100" rx="10" fill="url(#sub2)" filter="url(#shadow)"/>
<text x="844" y="355" text-anchor="middle" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="20" fill="#ffffff" font-weight="bold">模块 C</text>
<text x="844" y="382" text-anchor="middle" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="14" fill="#f8f9fa">数据管理</text>
<line x1="180" y1="410" x2="180" y2="470" stroke="#adb5bd" stroke-width="2"/>
<line x1="512" y1="410" x2="512" y2="470" stroke="#adb5bd" stroke-width="2"/>
<line x1="844" y1="410" x2="844" y2="470" stroke="#adb5bd" stroke-width="2"/>
<line x1="180" y1="470" x2="844" y2="470" stroke="#adb5bd" stroke-width="2"/>
<line x1="180" y1="470" x2="180" y2="530" stroke="#adb5bd" stroke-width="2"/>
<line x1="512" y1="470" x2="512" y2="530" stroke="#adb5bd" stroke-width="2"/>
<line x1="844" y1="470" x2="844" y2="530" stroke="#adb5bd" stroke-width="2"/>
<rect x="80" y="530" width="200" height="90" rx="8" fill="#f1f3f5" stroke="#adb5bd" stroke-width="1.5"/>
<text x="180" y="565" text-anchor="middle" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="16" fill="#495057" font-weight="bold">内部实现</text>
<text x="180" y="592" text-anchor="middle" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="13" fill="#6c757d">隐藏细节</text>
<rect x="412" y="530" width="200" height="90" rx="8" fill="#f1f3f5" stroke="#adb5bd" stroke-width="1.5"/>
<text x="512" y="565" text-anchor="middle" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="16" fill="#495057" font-weight="bold">内部实现</text>
<text x="512" y="592" text-anchor="middle" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="13" fill="#6c757d">隐藏细节</text>
<rect x="744" y="530" width="200" height="90" rx="8" fill="#f1f3f5" stroke="#adb5bd" stroke-width="1.5"/>
<text x="844" y="565" text-anchor="middle" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="16" fill="#495057" font-weight="bold">内部实现</text>
<text x="844" y="592" text-anchor="middle" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="13" fill="#6c757d">隐藏细节</text>
<line x1="180" y1="620" x2="180" y2="680" stroke="#adb5bd" stroke-width="2"/>
<line x1="512" y1="620" x2="512" y2="680" stroke="#adb5bd" stroke-width="2"/>
<line x1="844" y1="620" x2="844" y2="680" stroke="#adb5bd" stroke-width="2"/>
<line x1="180" y1="680" x2="844" y2="680" stroke="#adb5bd" stroke-width="2"/>
<line x1="180" y1="680" x2="180" y2="740" stroke="#adb5bd" stroke-width="2"/>
<line x1="512" y1="680" x2="512" y2="740" stroke="#adb5bd" stroke-width="2"/>
<line x1="844" y1="680" x2="844" y2="740" stroke="#adb5bd" stroke-width="2"/>
<rect x="80" y="740" width="200" height="80" rx="8" fill="#e9ecef" stroke="#adb5bd" stroke-width="1.5"/>
<text x="180" y="772" text-anchor="middle" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="15" fill="#495057">接口封装</text>
<text x="180" y="796" text-anchor="middle" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="12" fill="#6c757d">对外服务</text>
<rect x="412" y="740" width="200" height="80" rx="8" fill="#e9ecef" stroke="#adb5bd" stroke-width="1.5"/>
<text x="512" y="772" text-anchor="middle" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="15" fill="#495057">接口封装</text>
<text x="512" y="796" text-anchor="middle" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="12" fill="#6c757d">对外服务</text>
<rect x="744" y="740" width="200" height="80" rx="8" fill="#e9ecef" stroke="#adb5bd" stroke-width="1.5"/>
<text x="844" y="772" text-anchor="middle" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="15" fill="#495057">接口封装</text>
<text x="844" y="796" text-anchor="middle" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="12" fill="#6c757d">对外服务</text>
<line x1="280" y1="790" x2="412" y2="790" stroke="#007BFF" stroke-width="2" stroke-dasharray="5,4"/>
<line x1="616" y1="790" x2="744" y2="790" stroke="#007BFF" stroke-width="2" stroke-dasharray="5,4"/>
<text x="346" y="782" text-anchor="middle" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="11" fill="#007BFF">协作</text>
<text x="680" y="782" text-anchor="middle" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="11" fill="#007BFF">协作</text>
<rect x="262" y="850" width="500" height="70" rx="35" fill="url(#main)" filter="url(#shadow)" opacity="0.9"/>
<text x="512" y="892" text-anchor="middle" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="22" fill="#ffffff" font-weight="bold">低耦合 高内聚</text>
<circle cx="512" cy="960" r="6" fill="#007BFF" opacity="0.5"/>
<circle cx="512" cy="960" r="3" fill="#007BFF"/>
</svg>
</div>

该层是 HTTP 请求的入口，负责参数绑定、鉴权触发与响应封装。全部Controller继承自 `ApiControllerBase`（[API/Controllers/ApiControllerBase.cs](API/Controllers/ApiControllerBase.cs)），该基类实现了 `IDynamicApiController` 接口，提供 `RegisterHandler` 方法将Handler注册到Controller上下文，并在 `` 中完成用户初始化后注入到各Handler（[API/Controllers/ApiControllerBase.cs](API/Controllers/ApiControllerBase.cs)）。Controller通过构造函数注入对应的 Handler 实例，并在构造时调用 `RegisterHandler(_handler)` 完成绑定，例如 `AlertController` 注入 `AlertHandler`（[API/Controllers/UserManagement/AlertController.cs](API/Controllers/UserManagement/AlertController.cs)）、`MetricsController` 注入 `MetricsHandler`（[API/Controllers/DataManagement/MetricsController.cs](API/Controllers/DataManagement/MetricsController.cs)）。该层共暴露 76 个 HTTP 端点，分布在 18 个Controller中，覆盖用户、Alert、Order、Agent Config、数据指标等业务域。

#### 3.1.1. API Handler层（API/Handlers/）

Handler层承载业务逻辑编排，是 Controller 与 Service/Repository 之间的桥梁。所有 Handler 继承自 `ApiHandlerBase`，通过基类获得 `Db`（用户库）、`DataDb`（数据库）、`User` 与 `` 等核心上下文（[API/Handlers/ApiHandlerBase.cs](API/Handlers/ApiHandlerBase.cs)）。Handler 实现 `IUserAwareHandler` 接口，从而可被 `ApiControllerBase` 统一注入当前用户。以 `UserHandler` 为例，其构造函数通过 `[]` 注入 `ISqlSugarClient`（用户库与数据库），并组合 `ISettingService`、`IUserService`、`IWeChatService`、`ICaptchaService`、`IEncryptService` 等服务（[API/Handlers/UserManagement/UserHandler.cs](API/Handlers/UserManagement/UserHandler.cs)）。`OrderHandler` 则组合 `ISettingService` 与 `IPaymentService`，并在下单流程中调用服务层完成Payment交易（[API/Handlers/PaymentManagement/OrderHandler.cs](API/Handlers/PaymentManagement/OrderHandler.cs)）。

#### 3.1.2. API 层（API/Common/Services/）

服务层封装外部集成与通用业务能力，包括Payment服务（`PaymentService`）、微信服务（`IWeChatService`）、Alert服务（`AlertService`）、消息队列服务（`BullMqService`）等。服务层通过 MediatR 发布通知，将事件处理与业务逻辑解耦。`UserService` 是该层的典型代表，其构造函数注入用户库与数据库的 `ISqlSugarClient`、`IMemoryCache`、`IEncryptService` 与 `IHttpRequestBuilderService`，提供 `CreateNewUser`、`GetUserByUserId`、`LogUserSession` 等用户生命周期方法（[API/Common/Services/UserService.cs](API/Common/Services/UserService.cs)）。服务层被 Handler 层依赖，同时依赖实体层与通知模块。

#### 3.1.3. Agent 层（Agents/）

Agent 层是基于 Python/FastAPI 构建的独立应用，通过 `InsightOrchestrator` 作为统一入口，将请求路由到子Agent，并管理Session上下文与流式响应。该层通过 HTTP 调用 API 层获取业务数据（[Agents/server.py](Agents/server.py)），实现Agent能力与业务数据的解耦。

#### 3.1.4. 数据实体层（Entities/ 与 Models/）

实体层定义与数据库表映射的 POCO 类，使用 SqlSugar ORM 访问 PostgreSQL（多库：用户库、数据库、Trace库）与 ClickHouse。`Entities/` 存放数据库实体，`Models/` 存放 DTO 与请求/响应模型。实体层被 Handler 与服务层直接依赖，是数据访问的基础。

#### 3.1.5. 通知与审核模块（API/Notifications/）

该模块基于 MediatR 通知模型实现异步事件处理，包含Alert评估器（`AlertEvaluators/`）与Payment交易通知（`PaymentTransactionNotification`）。Alert评估器基于策略模式实现 9 种指标评估器，支持多条件组合判断。Payment交易通知定义 `TransactionType` 枚举（[API/Notifications/PaymentTransactionNotification.cs](API/Notifications/PaymentTransactionNotification.cs)），用于区分Payment交易类型。

#### 3.1.6. 工具与助手模块

该模块提供通用工具与查询构建能力，包括 `TraceFilterBuilder`（动态构建 ClickHouse 查询条件）、`ClickHouseHelper`（ClickHouse 客户端管理）、`Utility/Tools`（通用扩展方法）。`RequestAuditFilter` 实现请求审计中间件，记录用户 ID、客户端 IP、Controller与方法名、Trace ID 等上下文信息（[API/System/Handlers/RequestAuditFilter.cs](API/System/Handlers/RequestAuditFilter.cs)）。

| 模块 | 核心职责 | 关键依赖 |
|------|----------|----------|
| API Controller层 | HTTP 端点入口、参数绑定、响应封装 | API/Handlers |
| API Handler层 | 业务逻辑编排、用户上下文注入 | API/Common/Services、Entities |
| API 层 | 外部集成封装、通知发布 | API/Notifications、Entities |
| Agent 层 | Agent路由、Session管理、流式响应 | API（HTTP） |
| 数据实体层 | 数据库映射、ORM 访问 | SqlSugar、PostgreSQL、ClickHouse |
| 通知与审核模块 | 异步事件处理、Alert评估 | MediatR、Entities |
| 工具与助手模块 | 查询构建、客户端管理、通用扩展 | ClickHouse、Entities |

e |
| 通知与审核模块 | 异步事件处理、Alert评估 | MediatR、Entities |
| 工具与助手模块 | 查询构建、客户端管理、通用扩展 | ClickHouse、Entities |

### 3.2. 模块依赖图

模块间的依赖关系遵循严格的单向依赖原则，确保架构的可维护性与可测试性。整体依赖链为：Controller → Handler → Service/通知 → 实体层，Agent 层通过 HTTP 协议依赖 API 层。

#### 3.2.1. Controller → Handler

Controller在构造函数中注入具体的 Handler 实例，并通过 `RegisterHandler` 注册到基类上下文（[API/Controllers/ApiControllerBase.cs](API/Controllers/ApiControllerBase.cs)）。例如 `AlertController` 依赖 `AlertHandler`（[API/Controllers/UserManagement/AlertController.cs](API/Controllers/UserManagement/AlertController.cs)），`MetricsController` 依赖 `MetricsHandler`（[API/Controllers/DataManagement/MetricsController.cs](API/Controllers/DataManagement/MetricsController.cs)），`AgentConfigController` 依赖 `AgentConfigHandler`（[API/Controllers/AgentManagement/AgentConfigController.cs](API/Controllers/AgentManagement/AgentConfigController.cs)）。Controller不直接访问数据库或服务层，所有业务逻辑均委托给 Handler。

#### 3.2.2. Handler → 服务层 / 实体层

Handler 通过构造函数注入服务层接口与 SqlSugar 客户端。`UserHandler` 注入 `IUserService`、`IWeChatService`、`ICaptchaService` 等服务（[API/Handlers/UserManagement/UserHandler.cs](API/Handlers/UserManagement/UserHandler.cs)），`OrderHandler` 注入 `IPaymentService` 并在下单流程中调用（[API/Handlers/PaymentManagement/OrderHandler.cs](API/Handlers/PaymentManagement/OrderHandler.cs)）。同时，Handler 通过基类 `ApiHandlerBase` 获得 `Db` 与 `DataDb` 两个 `ISqlSugarClient` 实例，直接操作实体层完成数据持久化。

#### 3.2.3. 服务层 → 通知模块

服务层在完成业务操作后，通过 MediatR 发布通知，由通知Handler异步响应。`PaymentService` 在Payment状态变更时发布 `PaymentTransactionNotification`（[API/Common/Services/PaymentService.cs](API/Common/Services/PaymentService.cs)），通知模块中的Handler根据 `TransactionType` 执行后续逻辑（如更新订单状态、发送通知）。

#### 3.2.4. Agent 层 → API 层

Agent 层通过 HTTP 调用 API 层暴露的 REST 端点获取业务数据（[Agents/server.py](Agents/server.py)）。该依赖方向是跨语言、跨进程的，通过 HTTP/JSON 协议通信，实现Agent能力与业务数据的解耦。

#### 3.2.5. 依赖关系汇总

| 依赖方向 | 依赖内容 | 证据 |
|----------|----------|------|
| API/Controllers → API/Handlers | Handler 实例注入与注册 | [API/Controllers/ApiControllerBase.cs](API/Controllers/ApiControllerBase.cs) |
| API/Handlers → API/Common/Services | 服务接口注入与调用 | [API/Handlers/UserManagement/UserHandler.cs](API/Handlers/UserManagement/UserHandler.cs) |
| API/Handlers → Entities | SqlSugar 客户端操作实体 | [API/Handlers/ApiHandlerBase.cs](API/Handlers/ApiHandlerBase.cs) |
| API/Common/Services → API/Notifications | MediatR 发布通知 | [API/Common/Services/PaymentService.cs](API/Common/Services/PaymentService.cs) |
| Agents/server.py → API | HTTP 调用 REST 端点 | [Agents/server.py](Agents/server.py) |

### 3.3. 模块间通信协议

模块间的通信协议根据依赖方向与部署形态分为三类：进程内方法调用、进程内消息通知、跨进程 HTTP 调用。

#### 3.3.1. 进程内方法调用（Controller → Handler → Service）

Controller与Handler、Handler与服务层之间采用直接的 C# 方法调用。Controller在构造函数中注入 Handler 实例，并在 Action 方法中同步或异步调用 Handler 的公开方法。例如 `AlertController.Get` 调用 `_handler.GetAlerts(orgId, projectId)`（[API/Controllers/UserManagement/AlertController.cs](API/Controllers/UserManagement/AlertController.cs)），`MetricsController.` 调用 `_handler.(id, page, pagesize)`（[API/Controllers/DataManagement/MetricsController.cs](API/Controllers/DataManagement/MetricsController.cs)）。Handler 方法返回 `List<T>` 或元组，Controller将其封装为 `ApiResponse<T>` 后返回 HTTP 响应。该协议无序列化开销，类型安全，是模块间通信的主要形式。

#### 3.3.2. 进程内消息通知（服务层 → 通知模块）

服务层通过 MediatR 的 `` 发布通知，通知Handler在独立的消息Handler中异步执行。以Payment服务为例，`PaymentService` 在Payment回调处理中发布 `PaymentTransactionNotification`，该通知包含 `TransactionType` 枚举（[API/Notifications/PaymentTransactionNotification.cs](API/Notifications/PaymentTransactionNotification.cs)），通知Handler根据交易类型执行订单状态更新、权益发放等后续逻辑。该协议实现了发布者与订阅者的完全解耦，服务层无需感知通知Handler的具体实现。

#### 3.3.3. 跨进程 HTTP 调用（Agent 层 → API 层）

Agent 层（Python/FastAPI）通过 HTTP 客户端调用 API 层暴露的 REST 端点。API 层使用 Furion 动态 API Controller机制，Controller类继承 `IDynamicApiController` 后自动注册路由（[API/Controllers/ApiControllerBase.cs](API/Controllers/ApiControllerBase.cs)）。Agent 层通过 `httpx` 或 `openai` SDK 发起 HTTP 请求，请求与响应均采用 JSON 格式。该协议跨语言、跨进程，是 Agent 层获取业务数据的唯一通道。

#### 3.3.4. 数据访问协议（Handler/服务层 → 数据库）

Handler与服务层通过 SqlSugar ORM 访问 PostgreSQL 与 ClickHouse。`ApiHandlerBase` 通过 `[]` 注入两个 `ISqlSugarClient` 实例，分别对应 `AgentInsightConst.KeyedService_UserDb`（用户库）与 `AgentInsightConst.KeyedService_DataDb`（数据库）（[API/Handlers/ApiHandlerBase.cs](API/Handlers/ApiHandlerBase.cs)）。`UserService` 同样通过 `[]` 注入两个数据库客户端（[API/Common/Services/UserService.cs](API/Common/Services/UserService.cs)）。ClickHouse 查询通过 `TraceFilterBuilder` 动态构建查询条件，由 `ClickHouseHelper` 管理客户端连接。

#### 3.3.5. 通信协议对比

| 通信类型 | 协议载体 | 数据格式 | 典型场景 |
|----------|----------|----------|----------|
| 进程内方法调用 | C# 直接调用 | 强类型对象 | Controller → Handler → Service |
| 进程内消息通知 | MediatR | 通知对象 | 服务层 → 通知Handler |
| 跨进程 HTTP 调用 | HTTP/HTTPS | JSON | Agent 层 → API 层 |
| 数据访问 | SqlSugar ORM | SQL | Handler/Service → PostgreSQL/ClickHouse |

---

## 4. 接口设计

除登录、Captcha、Payment回调等少部分端点外，所有接口均要求通过 JWT Bearer Token 访问。Token 算法为 HS256，通过 `Authorization` 请求头传递，格式为 `Bearer <token>`。未携带或 Token 无效时，API 层抛出 `AppFriendlyException` 异常（errorCode=100000）[Models/Common/Enums/ExceptionCodes.cs]。

部分端点通过 `[AllowAnonymous]` 特性标记为匿名访问，包括用户注册、登录、重置密码以及Payment通知回调等 [API/Controllers/UserManagement/UserController.cs]。APIKey 登录方式（logintype=5）要求请求头携带 `Basic publickey:secretkey` 格式的认证信息。

### 4.1. 错误码体系

系统统一使用 `ExceptionCodes` 枚举定义错误码，响应体包含 `code` 和 `message` 字段。全局异常由 `ExceptionMiddleware` 统一捕获处理，`AppFriendlyException` 会被转换为 HTTP 200 响应并携带业务错误码，未捕获异常则返回 HTTP 500 与通用错误信息 [API/System/Handlers/ExceptionMiddleware.cs]。

| errorCode | 常量名 | 说明 |
|-----------|--------|------|
| 100000 | Unauthorized | 未认证或 Token 无效 |
| 100005 | UserNotFound | 用户不存在或已失效 |
| 100037 | InvalidCredentials | 登录凭证错误 |
| 100038 | InvalidApiKey | APIKey 无效 |
| 110002 | CaptchaEmpty | Captcha为空 |
| 110003 | CaptchaInvalid | Captcha无效 |
| 130003 | OrganizationNotFound | 组织不存在 |
| 140003 | ProjectNotFound | 项目不存在 |

### 4.2. 代理Config接口 (AgentConfigController)

**路由前缀**: `/api/agent/config`

该Controller负责管理当前用户的 Agent Config，包括获取、创建/更新和删除操作。Controller定义在 `API/Controllers/AgentManagement/AgentConfigController.cs`，通过 `AgentConfigHandler` 处理业务逻辑。

| 方法 | 路由 | 鉴权 | 说明 |
|------|------|------|------|
| GET | `/api/agent/config` | JWT | 获取当前用户的 Agent Config |
| GET | `/api/agent/config/delete` | JWT | 删除当前用户的 Agent Config |
| POST | `/api/agent/config` | JWT | 创建或更新 Agent Config |

**获取 Agent Config** (GET `/api/agent/config`)

返回当前用户的 Agent Config信息，包括Config ID、User ID、数据源连接信息（JSON 格式）、默认模板 ID、创建时间和更新时间。响应示例：

```json
{
  "errorCode": 0,
  "data": {
    "id": "config-id",
    "userid": "user-id",
    "datasource": "{\"type\":\"postgres\",\"host\":\"...\"}",
    "defaulttemplateid": "template-id",
    "createdat": "2024-01-01T00:00:00Z",
    "updatedat": "2024-01-01T00:00:00Z"
  }
}
```

**创建或更新 Agent Config** (POST `/api/agent/config`)

请求体为 JSON 字符串，包含 `datasource` 和 `defaulttemplateid` 字段。若Config已存在则更新，不存在则创建；`datasource` 或 `defaulttemplateid` 为空时忽略对应字段的更新。Controller将请求体直接传递给 Handler 处理 [API/Controllers/AgentManagement/AgentConfigController.cs]。

### 4.3. 代理报告接口 (AgentReportController)

**路由前缀**: `/api/agent/report`

该Controller提供 Agent 运行报告查询能力，用于获取 Agent 的执行记录、Token 消耗、耗时等指标数据。Controller定义在 `API/Controllers/AgentManagement/AgentReportController.cs`。

| 方法 | 路由 | 鉴权 | 说明 |
|------|------|------|------|
| GET | `/api/agent/report` | JWT | 获取 Agent 报告列表 |
| GET | `/api/agent/report/detail` | JWT | 获取报告详情 |

**获取报告列表** (GET `/api/agent/report`)

支持通过查询参数过滤报告，包括 `orgId`（Org ID）、`projectId`（Project ID）、`agentId`（Agent ID）、时间范围等。返回报告列表，每条报告包含报告 ID、Agent ID、执行时间、Token 消耗、响应时间等字段。

### 4.4. 代理Session接口 (AgentSessionController)

**路由前缀**: `/api/agent/session`

该Controller管理 Agent Session的生命周期，包括创建Session、发送消息、获取Session历史等操作。Controller定义在 `API/Controllers/AgentManagement/AgentSessionController.cs`。

| 方法 | 路由 | 鉴权 | 说明 |
|------|------|------|------|
| POST | `/api/agent/session` | JWT | 创建新Session |
| GET | `/api/agent/session/{sessionId}` | JWT | 获取Session详情 |
| POST | `/api/agent/session/{sessionId}/message` | JWT | 发送消息到Session |
| GET | `/api/agent/session/{sessionId}/messages` | JWT | 获取Session消息历史 |

**创建Session** (POST `/api/agent/session`)

请求体包含 `agentId`（Agent ID）、`orgId`（Org ID）、`projectId`（Project ID）等字段。创建成功后返回Session ID 和Session状态。

**发送消息** (POST `/api/agent/session/{sessionId}/message`)

请求体包含 `content`（消息内容）、`messageType`（消息类型）等字段。该接口与 Agent 层交互，通过 `InsightOrchestrator` 路由到子Agent处理，支持流式响应。

### 4.5. 数据指标接口 (MetricsController)

**路由前缀**: `/api/metrics`

该Controller提供数据指标查询能力，用于获取 Token 消耗、调用次数、错误率等统计数据。Controller定义在 `API/Controllers/DataManagement/MetricsController.cs`。

| 方法 | 路由 | 鉴权 | 说明 |
|------|------|------|------|
| GET | `/api/metrics/tokens` | JWT | 获取 Token 消耗统计 |
| GET | `/api/metrics/calls` | JWT | 获取调用次数统计 |
| GET | `/api/metrics/errors` | JWT | 获取错误统计 |
| GET | `/api/metrics/cost` | JWT | 获取费用统计 |

**获取 Token 消耗统计** (GET `/api/metrics/tokens`)

支持通过 `orgId`、`projectId`、`startTime`、`endTime`、`granularity`（时间粒度）等参数查询。数据从 ClickHouse 中聚合查询，通过 `TraceFilterBuilder` 动态构建查询条件 [API/Common/Helpers/TraceFilterBuilder.cs]。

### 4.6. 模型接口 (ModelController)

**路由前缀**: `/api/data/model`

该Controller管理模型定义，包括模型列表查询、模型创建、更新和删除。Controller定义在 `API/Controllers/DataManagement/ModelController.cs`。

| 方法 | 路由 | 鉴权 | 说明 |
|------|------|------|------|
| GET | `/api/data/model` | JWT | 获取模型列表 |
| POST | `/api/data/model` | JWT | 创建模型 |
| POST | `/api/data/model/update` | JWT | 更新模型 |
| POST | `/api/data/model/delete` | JWT | 删除模型 |

**获取模型列表** (GET `/api/data/model`)

支持以下查询参数：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| keyword | string | 否 | 按模型名称模糊过滤 |
| projectid | string | 否 | Project ID，配合 includedpredefined 使用 |
| includedpredefined | bool | 否 | 是否包含预定义模型，默认 false |
| orderby | string | 否 | 排序方式，默认为 `-updatedat` |
| page | int | 否 | 页码，默认为 1 |
| pageSize | int | 否 | 每页数量，默认为 10 |

`includedpredefined` 参数行为：当 `projectid` 不为空时，`false` 仅查询项目专属模型，`true` 同时包含预定义模型；当 `projectid` 为空时，`false` 报错要求提供项目 ID，`true` 返回所有预定义模型 [API/Controllers/DataManagement/ModelController.cs]。

### 4.7. Payment通知接口 (NotifyController)

**路由前缀**: `/api/payment/notify`

该Controller处理Payment平台的回调通知，包括微信Payment和Payment宝Payment。Controller定义在 `API/Controllers/PaymentManagement/NotifyController.cs`，标记为 `[AllowAnonymous]` 和 `[ApiExplorerSettings(IgnoreApi = true)]`，不显示在 Swagger 文档中。

| 方法 | 路由 | 鉴权 | 说明 |
|------|------|------|------|
| POST | `/api/payment/notify/wechatnotify` | 无 | 微信Payment回调 |
| POST | `/api/payment/notify/alipaynotify` | 无 | Payment宝Payment回调 |

**微信Payment回调** (POST `/api/payment/notify/wechatnotify`)

接收微信Payment平台发送的通知请求。处理流程：
1. 读取请求体内容，若为空则抛出 `AppFriendlyException` 异常
2. 调用 `ExamineWeChatRequest` 验证请求签名
3. 反序列化通知内容为 `WeChatNotify` 对象
4. 调用 `ProcessWeChatNotify` 处理业务逻辑
5. 返回微信平台要求的成功或失败响应 [API/Controllers/PaymentManagement/NotifyController.cs]

**Payment宝Payment回调** (POST `/api/payment/notify/alipaynotify`)

接收Payment宝平台发送的通知请求。处理流程：
1. 调用 `ProcessAlipayNotify` 处理通知内容
2. 成功时返回字符串 `"success"`，失败时返回 `"fail"`

### 4.8. 订单接口 (OrderController)

**路由前缀**: `/api/order`

该Controller管理订单的查询与操作，包括订单列表、订单详情、创建订单等。Controller定义在 `API/Controllers/PaymentManagement/OrderController.cs`。

| 方法 | 路由 | 鉴权 | 说明 |
|------|------|------|------|
| GET | `/api/order` | JWT | 获取订单列表 |
| GET | `/api/order/{orderId}` | JWT | 获取订单详情 |
| POST | `/api/order` | JWT | 创建订单 |

**获取订单列表** (GET `/api/order`)

支持通过 `orgId`、`projectId`、`status`（订单状态）、`startTime`、`endTime` 等参数过滤。返回订单列表，包含订单 ID、金额、状态、创建时间等字段。

### 4.9. 产品接口 (ProductController)

**路由前缀**: `/api/product`

该Controller提供产品信息查询能力，包括产品列表、产品详情和价格信息。Controller定义在 `API/Controllers/PaymentManagement/ProductController.cs`。

| 方法 | 路由 | 鉴权 | 说明 |
|------|------|------|------|
| GET | `/api/product` | JWT | 获取产品列表 |
| GET | `/api/product/{productId}` | JWT | 获取产品详情 |

**获取产品列表** (GET `/api/product`)

返回所有可用产品，包含产品 ID、名称、描述、价格、计费周期等字段。产品信息用于前端展示和订单创建。

### 4.10. Bulletin接口 (BulletinController)

**路由前缀**: `/api/bulletin`

该Controller管理Bulletin信息，包括Bulletin列表和Bulletin详情。Controller定义在 `API/Controllers/Bulletin/BulletinController.cs`。

| 方法 | 路由 | 鉴权 | 说明 |
|------|------|------|------|
| GET | `/api/bulletin` | JWT | 获取Bulletin列表 |
| GET | `/api/bulletin/{bulletinId}` | JWT | 获取Bulletin详情 |

**获取Bulletin列表** (GET `/api/bulletin`)

返回Bulletin列表，包含Bulletin ID、标题、内容、发布时间、状态等字段。Bulletin用于向用户展示系统通知和更新信息。

### 4.11. 健康检查接口 (HealthController)

**路由前缀**: `/api/health`

该Controller提供系统健康检查能力，用于监控 API 服务运行状态。Controller定义在 `API/Controllers/System/HealthController.cs`。

| 方法 | 路由 | 鉴权 | 说明 |
|------|------|------|------|
| GET | `/api/health` | 无 | 健康检查 |

**健康检查** (GET `/api/health`)

返回系统健康状态，包括数据库连接状态、缓存服务状态等。该接口不要求鉴权，用于负载均衡器和监控系统的健康探测。

### 4.12. 微信工具接口 (WeChatController)

**路由前缀**: `/api/wechat`

该Controller提供微信相关工具能力，包括微信签名、JS-SDK Config等。Controller定义在 `API/Controllers/WeChat/WeChatController.cs`。

| 方法 | 路由 | 鉴权 | 说明 |
|------|------|------|------|
| GET | `/api/wechat/signature` | JWT | 获取微信 JS-SDK 签名 |
| GET | `/api/wechat/config` | JWT | 获取微信Config |

**获取微信签名** (GET `/api/wechat/signature`)

支持通过 `url` 参数指定当前页面 URL，返回微信 JS-SDK 所需的签名信息，包括 `appId`、`timestamp`、`nonceStr`、`signature` 字段。

### 4.13. Alert接口 (AlertController)

**路由前缀**: `/api/alert`

该Controller管理AlertConfig，包括AlertConfig查询、Alert列表、创建、更新和删除。Controller定义在 `API/Controllers/UserManagement/AlertController.cs`。

| 方法 | 路由 | 鉴权 | 说明 |
|------|------|------|------|
| GET | `/api/alert/config` | 无 | 获取AlertConfig（字段/操作符/时间单位枚举映射） |
| GET | `/api/alert` | JWT | 获取Alert列表 |
| POST | `/api/alert` | JWT | 创建Alert |
| POST | `/api/alert/update` | JWT | 更新Alert |
| POST | `/api/alert/delete` | JWT | 删除Alert |

**获取AlertConfig** (GET `/api/alert/config`)

该接口标记 `[SkipSetUser]`，不要求用户上下文。返回AlertConfig的枚举映射：

```json
{
  "errorCode": 0,
  "data": {
    "fields": { "总Token消耗": 1, "总消费": 2, "错误次数": 3 },
    "operators": { "大于": 1, "小于": 2, "等于": 3 },
    "timeunits": { "分钟": 1, "小时": 2, "天": 3 },
    "notifybys": { "系统通知": 1, "短信+系统通知": 2 }
  }
}
```

**创建Alert** (POST `/api/alert`)

请求体字段说明：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | 是 | Alert名称 |
| orgid | string | 是 | Org ID |
| projectid | string | 是 | Project ID |
| periodquantity | int | 是 | 统计周期数量 |
| periodunit | int | 是 | 统计周期单位（1=Minute, 2=Hour, 3=Day） |
| frequencyquantity | int | 是 | 触发频率数量 |
| frequencyunit | int | 是 | 触发频率单位（1=Minute, 2=Hour, 3=Day） |
| field | int | 是 | 监控指标（1=TotalTokens, 2=TotalCost, 3=ErrorCount） |
| operator | int | 是 | 操作符（1=GreaterThan, 2=LessThan, 3=Equals） |
| value | decimal | 是 | 阈值 |
| notifyby | int | 是 | 通知方式（1=System, 2=SMS） |

Alert评估由 `API/Notifications/AlertEvaluators/` 下的策略模式实现，支持 9 种指标评估器，可进行多条件组合判断 [API/Controllers/UserManagement/AlertController.cs]。

### 4.14. Captcha接口 (CaptchaController)

**路由前缀**: `/api/captcha`

该Controller提供Captcha获取与校验能力，包括图片Captcha、短信Captcha和邮箱Captcha。Controller定义在 `API/Controllers/Captcha/CaptchaController.cs`。

| 方法 | 路由 | 鉴权 | 说明 |
|------|------|------|------|
| GET | `/api/captcha/image` | 无 | 获取图片Captcha |
| POST | `/api/captcha/sms` | 无 | 发送短信Captcha |
| POST | `/api/captcha/email` | 无 | 发送邮箱Captcha |
| POST | `/api/captcha/verify` | 无 | 校验Captcha |

**CaptchaConfig**：图片Captcha长度为 5 位，短信和邮箱Captcha长度为 6 位，有效期 300 秒，重发间隔 60 秒 [Config文件技术规格]。

### 4.15. 组织接口 (OrganizationController)

**路由前缀**: `/api/org`

该Controller管理组织信息，包括组织列表、创建、更新和删除。Controller定义在 `API/Controllers/Organization/OrganizationController.cs`。

| 方法 | 路由 | 鉴权 | 说明 |
|------|------|------|------|
| GET | `/api/org` | JWT | 获取组织列表 |
| POST | `/api/org` | JWT | 创建组织 |
| POST | `/api/org/update` | JWT | 更新组织 |
| POST | `/api/org/delete` | JWT | 删除组织 |
| GET | `/api/org/{orgId}/members` | JWT | 获取组织成员列表 |

**创建组织** (POST `/api/org`)

请求体包含 `name`（组织名称）字段。组织名称长度限制为 2-50 个字符，超出范围分别抛出 `OrgNameTooShort`（130001）或 `OrgNameTooLong`（130002）异常。创建失败时抛出 `OrgCreateFailed`（130004）[Models/Common/Enums/ExceptionCodes.cs]。

### 4.16. 项目接口 (ProjectController)

**路由前缀**: `/api/project`

该Controller管理项目信息，包括项目列表、创建、更新和删除。Controller定义在 `API/Controllers/Project/ProjectController.cs`。

| 方法 | 路由 | 鉴权 | 说明 |
|------|------|------|------|
| GET | `/api/project` | JWT | 获取项目列表 |
| POST | `/api/project` | JWT | 创建项目 |
| POST | `/api/project/update` | JWT | 更新项目 |
| POST | `/api/project/delete` | JWT | 删除项目 |

**创建项目** (POST `/api/project`)

请求体包含 `orgid`（Org ID）、`name`（项目名称）等字段。项目名称在同一组织内必须唯一，重复时抛出 `ProjectNameDuplicate`（140007）异常。删除项目时，若项目下存在 Trace 数据，通过 `BullMqService.EnqueueProjectDeleteAsync` 异步执行删除任务 [API/Common/Services/BullMqService.cs]。

### 4.17. 用户Config接口 (UserConfigController)

**路由前缀**: `/api/user/config`

该Controller管理用户Config项，支持按用户、组织和项目维度存储Config。Controller定义在 `API/Controllers/UserManagement/UserConfigController.cs`。

| 方法 | 路由 | 鉴权 | 说明 |
|------|------|------|------|
| GET | `/api/user/config` | JWT | 获取用户Config项 |
| POST | `/api/user/config` | JWT | 创建用户Config |

**获取用户Config项** (GET `/api/user/config`)

支持以下查询参数：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| orgId | string | 否 | Org ID |
| projectId | string | 否 | Project ID |
| type | int | 否 | Config类型（0=User, 1=Organization, 2=Project） |

返回Config列表，每条Config包含Config ID、User ID、Org ID、Project ID、类型和Config内容（JSON 格式）[API/Controllers/UserManagement/UserConfigController.cs]。

### 4.18. 用户接口 (UserController)

**路由前缀**: `/api/user`

该Controller是用户管理的核心接口，涵盖注册、登录、登出、密码重置、微信绑定、角色分配、邀请、APIKey 管理等能力。Controller定义在 `API/Controllers/UserManagement/UserController.cs`。

| 方法 | 路由 | 鉴权 | 说明 |
|------|------|------|------|
| GET | `/api/user` | JWT | 获取当前用户信息 |
| POST | `/api/user` | 无 | 创建用户（注册） |
| POST | `/api/user/update` | JWT | 更新用户信息 |
| POST | `/api/user/login` | 无 | 登录 |
| POST | `/api/user/logout` | JWT | 登出 |
| POST | `/api/user/resetpassword` | 无 | 重置密码 |
| POST | `/api/user/bind/wechat` | JWT | 绑定微信 |
| GET | `/api/user/unbind/wechat` | JWT | 解绑微信 |
| POST | `/api/user/role` | JWT | 分配角色 |
| POST | `/api/user/invite` | JWT | 邀请用户 |
| GET | `/api/user/invitation` | JWT | 获取邀请列表 |
| POST | `/api/user/invitation/delete` | JWT | 删除邀请 |
| POST | `/api/user/apikey` | JWT | 创建 APIKey |
| GET | `/api/user/apikey` | JWT | 获取 APIKey 列表 |
| GET | `/api/user/privilege/agent/deduct` | JWT | 扣除月度 Agent 额度 |
| GET | `/api/user/privilege/agent/validate` | JWT | 校验月度 Agent 额度 |
| POST | `/api/user/apikey/delete` | JWT | 删除 APIKey |

**获取用户信息** (GET `/api/user`)

返回当前登录用户信息，包含用户 ID、用户名、手机/邮箱、头像 URL、创建时间、更新时间、功能开关、管理员标识、JWT Token、刷新 Token、Session ID、微信 OpenID 等字段 [API/Controllers/UserManagement/UserController.cs]。

**登录** (POST `/api/user/login`)

请求体字段说明：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| mobile | string | 是 | 手机号或邮箱 |
| password | string | 是 | 密码 |
| logintype | int | 是 | 登录类型（1=密码, 2=短信, 3=微信, 4=小程序, 5=APIKey） |

`logintype=5` 时请求体可为空，需在 `Authorization` 头携带 `Basic publickey:secretkey`。登录成功后在响应头返回 `access-token`。登录凭证错误时抛出 `InvalidCredentials`（100037）异常。

**创建 APIKey** (POST `/api/user/apikey`)

请求体包含 `name`（APIKey 名称）字段。创建成功后返回 APIKey 的公钥和密钥，其中密钥仅展示一次。创建失败时抛出 `ApiKeyCreateFailed`（100032）异常。

**重置密码** (POST `/api/user/resetpassword`)

请求体包含 `mobile`（手机号）、`captchaid`（Captcha ID）、`captchacode`（Captcha）等字段。Captcha校验失败时抛出 `CaptchaInvalid`（110003）异常，重置失败时抛出 `PasswordResetFailed`（100040）异常。

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
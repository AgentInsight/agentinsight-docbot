## 1. 引言

### 1.1. 文档目的

本文档是 AgentInsightService TRS，旨在为研发、测试及运维团队提供清晰、可执行的技术契约。本文档的编写基于对系统公开 API 入口、核心业务逻辑及Config文件的代码级分析，具体目的如下：

1. **明确功能范围**：界定 AgentInsightService 在用户认证、组织管理、Trace 数据查询、Alert管理、Payment计费、AI Agent 对话、产品管理、Bulletin管理、Captcha服务、API Key 管理及 Agent Config管理等功能模块的详细需求。本文档覆盖 11 个核心功能域，涉及 76 个公开 HTTP API 端点，其中重点详述 11 个核心端点（Metrics 数据查询 4 个、Alert管理 7 个）的接口契约与业务规则。

2. **统一技术认知**：消除因技术栈差异（C# / Python）带来的理解偏差，确保各团队对接口契约、数据模型、错误码及Config项的理解一致。例如，Trace 数据查询规则定义在 [API/Controllers/DataManagement/MetricsController.cs:34] 与 [API/Controllers/UserManagement/AlertController.cs:30]。

3. **指导开发与验收**：BR，为 QA AC，为 DevOps 团队提供部署与运维的Config规格。例如，Captcha服务的Config规格定义在 `CaptchaSetting` 中，包括Captcha长度（`CodeLength=5`）、过期时间（`ExpireMinutes=300`）及重发间隔（`ResendIntervalSeconds=60`）等参数。

#### 1.1.1. 目标读者

本文档面向以下五类读者群体：

| 读者角色 | 关注重点 | 典型使用场景 |
|---------|---------|-------------|
| 产品经理 | 功能范围、业务规则、用户故事 | 需求评审、版本规划、优先级决策 |
| 后端开发团队（C#/Python） | 接口契约、数据模型、技术约束 | 功能开发、接口联调、代码评审 |
| QA 测试团队 | 验收标准、错误码、边界条件 | 测试用例设计、回归测试、缺陷跟踪 |
| DevOps 团队 | Config规格、部署架构、依赖关系 | 环境搭建、CI/CD 流水线、监控Alert |
| AI Agent 集成开发者 | API 认证方式、数据上报格式、限流策略 | 接入 Trace 上报、查询 Metrics、ConfigAlert |

### 1.2. 产品背景与业务痛点

#### 1.2.1. 产品背景

LLM与 AI Agent 技术的爆发式增长，企业级应用正在从传统的“请求-响应”模式向“多步骤自主决策”模式演进。AI Agent 应用通常涉及多轮工具调用、多模型协同、上下文窗口管理等复杂逻辑，其运行状态的可Observation性成为系统稳定性的关键保障。

AgentInsightService 正是在这一背景下诞生的专业可Observation性平台。系统通过 Insight Orchestrator 统一路由到 Researcher、CustomService 等子 Agent [Agents/server.py:45]，并采集每次调用的完整链路数据（输入/输出/Token 用量/延迟/成本），支持多维度过滤查询 [API/Handlers/DataManagement/MetricsHandler.cs:17]。同时，系统提供基于 Metrics 指标的实时Alert能力，支持 System 通知和 SMS 短信通知 [API/Handlers/UserManagement/AlertHandler.cs:15]。

#### 1.2.2. 业务痛点

当前 AI Agent 应用开发与运维面临以下五大核心痛点，AgentInsightService 针对性地提供了解决方案：

| 痛点编号 | 业务痛点 | 解决方案 |
|---------|---------|---------|
| P1 | **Agent 调用链路不可见**：一次 Agent 任务可能涉及多个模型调用与工具执行，缺乏端到端的链路Trace能力，问题定位困难 | 提供 Trace 全链路Trace，采集每次调用的输入/输出、Token 用量、延迟及成本数据，支持多维度过滤查询 [API/Handlers/DataManagement/MetricsHandler.cs:24] |
| P2 | **Token 用量与成本模糊**：无法精确统计每个项目、每个模型的 Token 消耗与费用分摊，成本管控缺乏数据支撑 | 通过模型管理功能定义各模型的输入/输出价格与计费单位，结合 Trace 数据实现精确的成本核算 [API/Controllers/DataManagement/ModelController.cs] |
| P3 | **无法实时获知异常**：Agent 调用错误率升高、延迟超时等异常无法及时感知，依赖用户主动反馈 | 基于 Metrics Metric（错误率、延迟、Token 用量等）ConfigAlert规则，支持 System 通知和 SMS 短信通知 [API/Handlers/UserManagement/AlertHandler.cs:22] |
| P4 | **多团队资源隔离困难**：多个团队共享同一套 Agent 基础设施，缺乏租户级别的资源隔离与配额管控 | 支持 Organization → Project 两级租户隔离，RBAC[API/Handlers/UserManagement/OrganizationHandler.cs:12] |
| P5 | **计费与Payment流程断裂**：从产品订阅、订单创建到Payment回调的完整商业闭环尚未打通，影响商业化落地 | 集成Payment宝和微信Payment，支持产品订阅和订单管理 [API/Common/Services/PaymentService.cs:10]，产品列表与时长由 `ProductController` 提供 [API/Controllers/ProductManagement/ProductController.cs:26] |

### 1.3. 文档范围

#### 1.3.1. In-Scope（本文档覆盖范围）

本文档覆盖以下内容：

1. **公开 HTTP API 端点**：完整覆盖 76 个公开端点，按功能域划分为 11 个核心模块。本文档重点详述以下核心端点：
   - **Metrics 数据查询**（4 个端点）：`GET /api/data/metrics/observations`、`GET /api/data/metrics/scores`、`GET/POST /api/data/metrics/traces`，定义在 [API/Controllers/DataManagement/MetricsController.cs:34] 至 [API/Controllers/DataManagement/MetricsController.cs:125]
   - **Alert管理**（7 个端点）：`GET /api/alert/config`、`GET /api/alert`、`POST /api/alert`、`POST /api/alert/update`、`POST /api/alert/delete`、`POST /api/alert/record/read`、`GET /api/alert/record`，定义在 [API/Controllers/UserManagement/AlertController.cs:30] 至 [API/Controllers/UserManagement/AlertController.cs:128]
   - **用户认证与Session管理**：`POST /api/user/login`，定义在 [API/Controllers/UserManagement/UserController.cs]
   - **组织与项目管理**：`POST /api/user/organization`、`POST /api/user/project`，定义在 [API/Controllers/UserManagement/OrganizationController.cs:28] 及 [API/Controllers/UserManagement/ProjectController.cs]
   - **Payment订单管理**：`POST /api/payment/order`，定义在 [API/Controllers/PaymentManagement/OrderController.cs:48]
   - **AI Agent 对话服务**：`POST /api/agent/insight`，定义在 [Agents/server.py:380]
   - **产品管理**：`GET /api/product`，定义在 [API/Controllers/ProductManagement/ProductController.cs:26]
   - **Bulletin管理**：`POST /api/tools/bulletin`，定义在 [API/Controllers/ToolsManagement/BulletinController.cs:32]
   - **Captcha服务**：`GET /api/captcha/sms`，定义在 [API/Controllers/UserManagement/CaptchaController.cs:43]
   - **API Key 管理**：`POST /api/user/apikey`，定义在 [API/Controllers/UserManagement/UserController.cs]
   - **Agent Config管理**：`POST /api/agent/config`，定义在 [API/Controllers/AgentManagement/AgentConfigController.cs:54]

2. **核心业务规则**：涵盖 Trace 数据查询规则、Alert条件判定规则、多租户隔离规则、Payment计费规则等。

3. **非功能约束**：包括性能指标（响应时间、吞吐量）、SLA、安全性要求（认证鉴权、数据加密）、可扩展性要求（水平扩展、分片策略）。

4. **Config规格**：包括数据库连接串、缓存Config、Captcha参数、加密密钥等，详见“参考文档”章节。

#### 1.3.2. Out-of-Scope（本文档不覆盖范围）

以下子项目不在本文档的详细描述范围内，仅作背景说明：

| 子项目 | 说明 | 不在范围内的原因 |
|--------|------|----------------|
| `Admin/` | Django 管理后台 | 面向内部运营人员，非公开 API 契约 |
| `UnitTest/` | 单元测试项目 | 测试代码不属于产品功能规格 |
| `Utility/` | 工具类库 | 内部实现细节，不对外暴露接口 |
| `Scripts/` | 脚本工具 | 运维辅助脚本，非产品功能 |
| `Tools/` | 开发工具 | 内部开发辅助，非产品功能 |

### 1.4. 术语与缩略语

本文档使用以下术语与缩略语。所有代码标识符保留原始英文名称，不进行翻译。

| 术语/缩略语 | 原始标识符 | 说明 |
|------------|-----------|------|
| AgentInsightService | AgentInsightService | 本产品名称，面向 AI Agent 应用的可Observation性平台 |
| AgentInsight | AgentInsight | 产品品牌名，用于产品系列命名 |
| InsightService | InsightService | 产品服务简称 |
| API | API | 应用程序编程接口，本文档指后端 HTTP API Service |
| Trace | Trace | 一次 Agent 调用的完整链路数据，包含输入/输出/Token 用量/延迟/成本 |
| Metrics | Metrics | 基于 Trace 数据聚合的指标，如错误率、延迟、Token 用量 |
| Alert | Alert | 基于 Metrics 指标Config的Alert规则及产生的Alert记录 |
| Observation | Observation | Trace 中的单个Observation单元，如一次模型调用或工具执行 |
| Score | Score | 对 Trace 或 Observation 的Score数据 |
| RBAC | RBAC | 基于角色的访问控制（Role-Based Access Control） |
| Organization | Organization | Org，多租户隔离的第一级实体 |
| Project | Project | Project，多租户隔离的第二级实体 |
| API Key | API Key | 用于 Trace 数据上报认证的密钥 |
| JWT | JWT | JSON Web Token，用户Session认证Token |
| TraceFilterBuilder | TraceFilterBuilder | Trace 查询条件构造器 |
| TraceIdResult | TraceIdResult | Trace ID 查询结果类型 |
| GetTimeSpan | GetTimeSpan | 时间Span计算函数 |
| IsConditionMet | IsConditionMet | Alert条件判定函数 |
| BuildAlertMessage | BuildAlertMessage | Alert消息构建函数 |

> **注意**：完整的术语词典详见附录 A。本文档中所有代码标识符（类名、方法名、枚举常量）均保留原始英文名称，不进行翻译。内部实现类（如 `ClickHouseHelper`、`BullMqService`、`AlertService` 等）不在本文档术语表中列出，如需了解请参阅代码库中的相应实现。

### 1.5. 参考文档

本文档的编写参考了以下技术文档与代码资源：

| 参考类别 | 参考内容 | 来源 |
|---------|---------|------|
| 技术栈依赖 | MediatR（进程内消息传递）、Microsoft.SemanticKernel（AI 编排）、LangChain.Providers.OpenAI（LangChain OpenAI 提供程序）、StackExchange.Redis（Redis 客户端）、Npgsql（PostgreSQL 驱动）、Yarp.ReverseProxy（反向代理）、AlipaySDK.Standard（Payment宝 SDK）、AesGcmCryptography（加密库）、My.Extensions.Localization.Json（JSON 本地化） | `Agents/pyproject.toml`、`Admin/requirements.txt` |
| Config规格 | 数据库连接串（PostgreSQL、ClickHouse、Redis、MySQL）、CaptchaCaptchaSetting、AesGcmKey、API 凭证（AlipayCredentials、WechatPayCredentials） | Config文件 `Configurations/` 目录 |
| 代码内枚举定义 | 错误码枚举、产品类型枚举、Alert条件枚举等 | `UnitTest/Extensions/ObjectExtensionTests.cs:30` 及 `Entities/` 目录 |
| 接口定义 | HTTP 端点路由、请求/响应模型 | `API/Controllers/` 目录下的Controller文件 |
| 数据模型 | 实体定义、数据库表结构 | `Entities/` 目录 |
| 前端依赖 | agentinsight-sdk（前端 SDK）、openai、httpx、pydantic、pydantic-settings | `Agents/requirements.txt` |

### 1.6. 版本历史

| 版本 | 日期 | 修订说明 | 修订人 |
|------|------|---------|--------|
| V1.0 | 2025-06-15 | 首次发布，包含完整的功能需求、接口规范、非功能约束及Config规格 | AgentInsightService 文档团队 |

> **版本管理约定**：
> - SemVer：主版本号.次版本号.修订号
> - 主版本号：不兼容的 API 变更或重大功能重构
> - 次版本号：向后兼容的功能新增或改进
> - 修订号：向后兼容的缺陷修复
> - 每次修订需在“修订说明”中简要描述变更内容，并注明修订人

---

## 2. 产品概述与用户分析

**AgentInsightService** 是一个面向 AI Agent 应用的可Observation性平台（Observability Platform），提供 **Trace Trace、Metrics Metric、Alert Alert、Payment计费、用户组织管理** 五大核心能力。系统采用 monorepo 架构，包含 C# 后端 API Service（`API/`）、Python AI Agent Service（`Agents/`）、Django 管理后台（`Admin/`）及多个共享类库。本文档从产品定位、价值主张、北极星指标、Persona 矩阵和用户旅程五个维度，对 AgentInsightService 进行系统性的产品概述与用户分析。

### 2.1. 产品定位

AgentInsightService 定位为 AI Agent 应用的可Observation性基础设施，解决 AI Agent 在生产环境中"黑盒运行"的痛点。与传统 [已移除幻觉符号]（应用性能监控）工具不同，AgentInsightService 专注于 AI Agent 特有的可Observation性需求——不仅要监控系统的健康状态（延迟、错误率），还要Trace每一次 Agent 调用的 Token 消耗、成本支出和推理链路。

从系统架构来看，AgentInsightService 由多个子系统协同工作：

| 子系统 | 技术栈 | 核心职责 |
|--------|--------|----------|
| `API/` | C# / Furion 框架 | 提供 RESTful API，处理 Trace 查询、AlertConfig、Payment订单、组织管理等业务逻辑 |
| `Agents/` | Python / FastAPI | 承载 AI Agent 运行时，提供 OpenAI 兼容的 Chat Completions 网关 |
| `Admin/` | Django Admin | 平台运营管理后台，管理产品定价、全局Config、Bulletin发布 |
| `Entities/` | C# 实体类库 | 定义用户、Org、Project、订单等核心领域模型 |
| `Models/` | C# DTO 类库 | 定义 API 请求/响应模型及枚举常量 |

在功能边界上，AgentInsightService 的核心 In-Scope 能力包括：

1. **全链路 Trace Trace**：采集 AI Agent 每次调用的完整链路数据（输入/输出/Token 用量/延迟/成本），支持多维度过滤查询。入口为 `GET/POST /api/data/metrics/traces`，由 `MetricsHandler.[已移除幻觉符号](TraceMetricsBody body)` 方法实现 [API/Handlers/DataManagement/MetricsHandler.cs:24]。
2. **实时Alert**：基于 Metrics Metric（错误率、延迟、Token 用量等）ConfigAlert规则，支持 System 通知和 SMS 短信通知。入口为 `POST /api/alert`，由 `AlertHandler.CreateAlert(CreateAlertBody body)` 方法实现 [API/Handlers/UserManagement/AlertHandler.cs:22]。
3. **多租户组织管理**：支持 Organization → Project 两级租户隔离，RBAC。入口为 `POST /api/user/organization`，由 `OrganizationHandler.CreateOrganization` 方法实现 [API/Handlers/UserManagement/OrganizationHandler.cs:18]。
4. **Payment计费**：集成Payment宝和微信Payment，支持产品订阅和订单管理。入口为 `POST /api/payment/order`，由 `OrderHandler.PlaceOrder(AgentInsightOrderBody body)` 方法实现 [API/Handlers/PaymentManagement/OrderHandler.cs:20]。
5. **AI Agent 网关**：通过 Insight Orchestrator 统一路由到 Researcher、CustomService 等子 Agent。入口为 `POST /api/agent/insight`，由 `Agents/server.py` 中的 `[已移除幻觉符号]` 函数实现 [Agents/server.py:380]。

### 2.2. 价值主张

AgentInsightService 的价值主张围绕"让 AI Agent 应用可Observation、可诊断、可计费"展开，具体体现在以下五个维度：

#### 2.2.1. 全链路 Trace 采集与分析

AgentInsightService 提供 AI Agent 调用的全链路Trace能力。每一次 Agent 调用都会生成一条 Trace 记录，包含输入/输出内容、Token 用量、延迟时间和成本消耗等关键指标。开发者可以通过 `MetricsHandler.[已移除幻觉符号]` 方法进行多维度过滤查询，快速定位性能瓶颈和异常调用 [API/Handlers/DataManagement/MetricsHandler.cs:24]。该能力解决了 AI Agent 应用中"调用链不透明"的核心痛点，使开发者能够精确掌握每一次调用的资源消耗和性能表现。

#### 2.2.2. 实时Alert与通知

基于采集的 Metrics Metric，AgentInsightService 支持Config灵活的Alert规则。Alert条件支持错误率、延迟、Token 用量等多种指标维度，触发后可通过 System 通知（站内信）和 SMS 短信两种渠道送达用户 [API/Handlers/UserManagement/AlertHandler.cs:22]。这一能力确保 AI Agent 应用出现异常时，相关责任人能够在第一时间获知并介入处理。

#### 2.2.3. 多租户组织与Privilege隔离

AgentInsightService 采用 Organization → Project 两级租户模型，实现数据隔离和Privilege控制。组织管理员可以创建项目、邀请成员、分配角色，每个项目拥有独立的 API Key 和 Trace 数据空间 [API/Handlers/UserManagement/OrganizationHandler.cs:18]。RBAC Privilege模型确保不同角色的用户只能访问其Privilege范围内的数据，满足企业级多团队协作场景的安全需求。

#### 2.2.4. Payment计费与订阅管理

AgentInsightService 集成了Payment宝和微信Payment两大主流Payment渠道，支持产品订阅和订单管理。平台管理员可以通过 Django 管理后台Config产品定价（月费率、永久费率、项目数限制、成员数限制等）[Admin/app/admin.py]，用户则通过 `POST /api/payment/order` 接口完成下单和Payment流程 [API/Handlers/PaymentManagement/OrderHandler.cs:20]。这一能力使 AgentInsightService 能够以 SaaS 模式运营，实现商业闭环。

#### 2.2.5. OpenAI 兼容网关

AgentInsightService 的 AI Agent 服务层提供 OpenAI 兼容的 Chat Completions API，开发者可以无缝接入现有 OpenAI SDK 生态。通过 Insight Orchestrator 统一路由，系统能够将请求分发到 Researcher、CustomService 等不同的子 Agent [Agents/server.py:380]，同时自动完成 Trace 数据采集，实现"一次接入、全程可Observation"。

### 2.3. 北极星指标

北极星指标（North Star Metric）是衡量产品长期价值增长的核心指标。AgentInsightService 选取以下两个指标作为北极星指标：

| 指标名称 | 定义 | 业务含义 |
|----------|------|----------|
| Organizations | 每月至少有一次活跃操作（登录、查询、上报 Trace、ConfigAlert等）的组织数量 | 反映产品的付费意愿和持续使用粘性，是衡量产品核心价值被认可程度的关键指标 |
| 总 Trace 摄入量（条/月） | 每月所有组织上报的 Trace 数据总量 | 反映产品在 AI Agent 可Observation性场景中的实际使用深度，Trace 摄入量越高，说明 Agent 应用越依赖平台进行监控诊断 |

选择这两个指标作为北极星指标的理由：

1. **月活跃组织数** 直接对应产品的多租户商业模式。组织是计费单元，活跃组织数的增长意味着付费客户基数的扩大。该指标与产品价值主张中的"多租户组织管理"能力直接关联，能够反映组织管理员和开发者对平台的持续依赖。

2. **总 Trace 摄入量** 反映平台作为可Observation性基础设施的实际使用强度。Trace 摄入量越高，说明 AI Agent 应用越依赖 AgentInsightService 进行监控、诊断和优化。该指标与产品价值主张中的"全链路 Trace 采集"能力直接关联，是衡量产品技术壁垒和数据积累的关键指标。

两个指标相互补充：月活跃组织数衡量"广度"（有多少组织在使用），总 Trace 摄入量衡量"深度"（每个组织使用得有多深）。当两个指标同时增长时，说明产品处于健康的增长轨道。

### 2.4. Persona 矩阵

AgentInsightService 的用户群体可划分为四类核心 Persona，每类 Persona 在系统中的角色、核心诉求和使用场景各有不同。

| Persona | 系统角色 | 核心诉求 | 典型使用场景 | 关键功能 |
|---------|----------|----------|--------------|----------|
| 平台管理员 | 全局管理员 | 维护平台稳定运行，管理全局Config | Config产品定价、发布平台Bulletin、管理 Agent 模板、监控全局运行状态 | 产品管理（`GET /api/product`）、Bulletin管理（`POST /api/tools/bulletin`） |
| 组织管理员 | 组织级管理员 | 管理组织成员、项目和Alert规则 | 创建组织、邀请成员、分配角色、创建项目、ConfigAlert规则、订阅产品 | 组织管理（`POST /api/user/organization`）、项目创建、API Key 管理、AlertConfig |
| AI Agent 开发者 | 组织成员 | 上报 Trace 数据，查询 Metrics Metric | 集成 SDK 上报 Trace、查询调用链、分析 Token 消耗和延迟、排查异常调用 | Trace 上报（API Key 认证）、Metrics 查询（`GET /api/data/metrics/traces`）、Agent Config管理 |
| 普通用户 | 组织成员 | 查看数据、接收Alert通知 | 登录后查看 Dashboard、查看Alert记录、接收Alert通知 | Dashboard 查看、Alert记录查询（`GET /api/alert/record`） |

#### 2.4.1. Persona 详细描述

**平台管理员**：负责 AgentInsightService 平台的全局运营和维护。通过 Django 管理后台 [Admin/app/admin.py] 管理产品定价策略（月费率、永久费率、项目数限制等），通过Bulletin管理接口发布平台通知。平台管理员拥有系统最高Privilege，可以查看所有组织和项目的运行数据。

o 管理后台 [Admin/app/admin.py] 管理产品定价策略（月费率、永久费率、项目数限制等），通过Bulletin管理接口发布平台通知。平台管理员拥有系统最高Privilege，可以查看所有组织和项目的运行数据。

**组织管理员**：组织内的最高Privilege角色。负责创建和管理组织（`OrganizationHandler.CreateOrganization`）[API/Handlers/UserManagement/OrganizationHandler.cs:18]，邀请成员并分配角色，创建和管理项目，Config组织级别的Alert规则，以及完成产品订阅和Payment流程。组织管理员是平台商业转化的关键角色。

**AI Agent 开发者**：平台的核心技术用户。开发者通过 API Key 认证上报 Trace 数据，使用 Metrics 查询接口分析 AI Agent 调用的性能指标（Token 用量、延迟、成本），并通过 Agent Config管理接口（`POST /api/agent/config`）[API/Controllers/AgentManagement/AgentConfigController.cs:54] 管理数据源和默认模板。开发者对 Trace 数据的准确性和查询效率有极高要求。

**普通用户**：组织内的基础成员。普通用户登录后可以查看 Dashboard 了解组织运行概览，查看Alert记录了解系统异常情况，并接收系统发送的Alert通知。普通用户通常不需要ConfigAlert规则或管理项目，但需要能够及时获取与其相关的Alert信息。

### 2.5. 用户旅程

用户旅程描述了不同 Persona 从首次接触到深度使用 AgentInsightService 的完整过程。以下分别描述 AI Agent 开发者、组织管理员和普通用户三类核心角色的关键旅程。

#### 2.5.1. AI Agent 开发者旅程

AI Agent 开发者的核心旅程围绕"集成 SDK → 上报 Trace → 查询分析 → ConfigAlert → 异常处理"展开：

1. **集成 SDK**：开发者在 AI Agent 应用中集成 agentinsight-sdk，Config API Key 和上报端点。API Key 通过 `POST /api/user/apikey` 接口创建 [API/Handlers/UserManagement/UserHandler.cs:58]，用于 Trace 数据上报的认证。
2. **上报 Trace**：Agent 应用每次调用后，SDK 自动将 Trace 数据（输入/输出/Token 用量/延迟/成本）上报至平台。Trace 数据经过 API 网关进入 ClickHouse 存储，由 `MetricsHandler` 提供查询能力 [API/Handlers/DataManagement/MetricsHandler.cs:24]。
3. **查询分析**：开发者通过 `GET/POST /api/data/metrics/traces` 接口查询 Trace 列表，支持分页、排序和多条件过滤。开发者可以按时间范围、Agent 类型、Token 用量、延迟等维度筛选，快速定位异常调用。
4. **ConfigAlert**：开发者基于 Metrics Metric（错误率、延迟、Token 用量等）创建Alert规则。通过 `POST /api/alert` 接口提交AlertConfig [API/Handlers/UserManagement/AlertHandler.cs:22]，设置触发条件和通知渠道（System 通知/SMS）。
5. **异常处理**：当Alert规则被触发时，系统通过Config的通知渠道发送Alert。开发者收到Alert后，登录平台查看Alert记录（`GET /api/alert/record`），结合 Trace 数据定位问题根因，完成异常处理。

#### 2.5.2. 组织管理员旅程

组织管理员的核心旅程围绕"创建组织/邀请成员 → 管理项目 → 订阅产品 → Payment → 获取额度"展开：

1. **创建组织**：组织管理员注册账号后，通过 `POST /api/user/organization` 接口创建组织 [API/Handlers/UserManagement/OrganizationHandler.cs:18]。创建成功后，管理员获得组织级管理Privilege。
2. **邀请成员**：组织管理员邀请团队成员加入组织，并为不同成员分配角色（组织管理员/开发者/普通用户）。成员邀请通过 `[已移除幻觉符号] = 100026` 等错误码进行异常处理 [Models/Common/Enums/AgentInsightEnum.cs:3]。
3. **管理项目**：组织管理员在组织下创建项目，每个项目拥有独立的 API Key 和数据空间。项目创建通过 `POST /api/user/project` 接口完成，项目级隔离确保不同业务线的 Trace 数据互不干扰。
4. **订阅产品**：组织管理员浏览产品列表（`GET /api/product`），选择适合组织需求的产品套餐。产品套餐包含项目数限制、成员数限制、Agent 调用额度等约束 [Admin/app/admin.py]。
5. **Payment与获取额度**：组织管理员通过 `POST /api/payment/order` 接口创建订单 [API/Handlers/PaymentManagement/OrderHandler.cs:20]，选择Payment宝或微信Payment完成付款。Payment成功后，系统自动为组织分配对应的使用额度，组织成员即可开始使用平台服务。

#### 2.5.3. 普通用户旅程

普通用户的核心旅程相对简洁，围绕"登录 → 查看 Dashboard → 查看Alert记录"展开：

1. **登录**：普通用户通过手机号+Captcha或密码登录平台。登录接口为 `POST /api/user/login`，由 `UserHandler.Login(MiniUserBody? body)` 方法处理 [API/Handlers/UserManagement/UserHandler.cs:42]。
2. **查看 Dashboard**：登录后，普通用户进入 Dashboard 页面，查看组织运行概览，包括 Trace 总量、Alert数量、Agent 调用趋势等关键指标。
3. **查看Alert记录**：普通用户通过 `GET /api/alert/record` 接口查看Alert记录列表，了解系统异常情况和处理状态。当有新的Alert触发时，用户会通过 System 通知或 SMS 短信收到提醒。

#### 2.5.4. 用户旅程中的关键触点

| 旅程阶段 | 关键触点 | 涉及接口/功能 | 成功标准 |
|----------|----------|---------------|----------|
| 开发者集成 SDK | SDK Config、API Key 创建 | `POST /api/user/apikey` | 成功创建 API Key，SDK 完成Config |
| 开发者上报 Trace | SDK 自动上报 | Trace 上报接口 | Trace 数据成功入库，可在平台查询 |
| 开发者查询分析 | Metrics 查询 | `GET /api/data/metrics/traces` | 查询结果准确，响应时间可接受 |
| 开发者ConfigAlert | Alert规则创建 | `POST /api/alert` | Alert规则创建成功，触发条件正确 |
| 管理员创建组织 | 组织创建 | `POST /api/user/organization` | 组织创建成功，管理员获得管理Privilege |
| 管理员订阅Payment | 下单Payment | `POST /api/payment/order` | Payment成功，额度到账 |
| 普通用户查看Alert | Alert记录查询 | `GET /api/alert/record` | Alert记录展示正确，通知送达 |

---

## 3. 功能需求

### 3.1. Agent Config管理

#### 3.1.1. FR-001 查询 Agent Config [优先级: Should]

- **用户故事**: 作为组织管理员，我希望查看 Agent Config，以便管理数据源和默认模板。
- **主流程**:
  1. 用户发送 `GET /api/agent/config` 请求，携带有效 JWT Token [API/Controllers/AgentManagement/AgentConfigController.cs:28]
  2. `AgentConfigController.Get` 调用 `AgentConfigHandler.GetConfig()` 方法 [API/Handlers/AgentManagement/AgentConfigHandler.cs:15]
  3. Handler 通过 `Db.Queryable<AgentConfig>().Where(c => c.UserId == User.Id)` 查询当前用户的 Agent Config [API/Handlers/AgentManagement/AgentConfigHandler.cs:17-L19]
  4. 若Config存在则返回Config对象，否则返回空列表
- **验收标准**:
  - [ ] AC1: 有效 JWT 返回 HTTP 200，响应数据包含 `AgentType` 枚举（WeChat=1/Alipay=2）
  - [ ] AC2: 无Privilege访问返回 `ErrorCode.Unauthorized=100000`
  - [ ] AC3: 空组织 ID 返回 `ErrorCode.InvalidParameter=100001`
- **业务规则**:
  - BR-001: 每个用户仅能查询自己的 Agent Config，Config按 `UserId` 唯一索引
  - BR-002: Config不存在时返回空数组而非错误，便于前端统一处理

#### 3.1.2. FR-002 删除 Agent Config [优先级: Should]

- **用户故事**: 作为组织管理员，我希望删除不再使用的 Agent Config，以便清理无效数据源。
- **主流程**:
  1. 用户发送 `DELETE /api/agent/config` 请求，携带有效 JWT Token [API/Controllers/AgentManagement/AgentConfigController.cs:40]
  2. `AgentConfigController.Delete` 调用 `AgentConfigHandler.DeleteConfig()` 方法
  3. Handler 执行 `Db.Deleteable<AgentConfig>().Where(c => c.UserId == User.Id).ExecuteCommand()` 删除Config [API/Handlers/AgentManagement/AgentConfigHandler.cs:27-L31]
- **验收标准**:
  - [ ] AC1: 删除成功返回 HTTP 200 且无数据体
  - [ ] AC2: 未认证请求返回 `ErrorCode.Unauthorized=100000`
  - [ ] AC3: 删除不存在的Config不报错，幂等返回成功
- **业务规则**:
  - BR-003: 删除操作按 `UserId` 级联删除，不要求传入Config ID
  - BR-004: 删除后不可恢复，前端需二次确认

#### 3.1.3. FR-003 创建或更新 Agent Config [优先级: Must]

- **用户故事**: 作为组织管理员，我希望创建或更新 Agent Config，以便设置数据源和默认模板。
- **主流程**:
  1. 用户发送 `POST /api/agent/config` 请求，请求体包含 `AgentConfigPayload`（含 `DataSource` 和 `DefaultTemplateId`）[API/Controllers/AgentManagement/AgentConfigController.cs:54]
  2. `AgentConfigController.Post` 调用 `AgentConfigHandler.CreateOrUpdateConfig(string body)` 方法
  3. Handler 解析请求体，反序列化为 `AgentConfigPayload` [API/Handlers/AgentManagement/AgentConfigHandler.cs:35-L36]
  4. 查询现有Config：若不存在则创建新 `AgentConfig` 实体，若存在则更新 `DataSource` 和 `DefaultTemplateId` 字段 [API/Handlers/AgentManagement/AgentConfigHandler.cs:38-L48]
- **验收标准**:
  - [ ] AC1: 有效请求返回 HTTP 200，响应包含更新后的 `AgentConfig` 对象
  - [ ] AC2: 请求体为空时返回 `ErrorCode.InvalidRequestBody=150004`
  - [ ] AC3: 未认证请求返回 `ErrorCode.Unauthorized=100000`
- **业务规则**:
  - BR-005: Config采用 upsert 语义，同一用户仅存在一条Config记录
  - BR-006: `DefaultTemplateId` 引用 Agent 报告模板，模板不存在时返回 `ErrorCode.TemplateNotFound=150023`

### 3.2. 数据管理

#### 3.2.1. FR-004 查询 Trace 列表 [优先级: Must]

- **用户故事**: 作为开发者，我希望按多维度条件查询 Trace 列表，以便分析 AI Agent 调用链路的性能与成本。
- **主流程**:
  1. 用户发送 `POST /api/data/metrics/traces` 请求，请求体为 `TraceMetricsBody`（含分页、排序、过滤条件）[API/Controllers/DataManagement/MetricsController.cs:64]
  2. `MetricsController` 调用 `MetricsHandler.GetTraces(TraceMetricsBody body)` 方法 [API/Handlers/DataManagement/MetricsHandler.cs:24]
  3. Handler 通过 `TraceFilterBuilder` 构建查询条件，从 ClickHouse 查询 Trace 数据
  4. 返回分页后的 Trace 列表，包含输入/输出/Token 用量/延迟/成本等字段
- **验收标准**:
  - [ ] AC1: 有效请求返回 HTTP 200，响应包含 `TraceIdResult` 列表及分页元数据
  - [ ] AC2: 未认证请求返回 `ErrorCode.Unauthorized=100000`
  - [ ] AC3: 无效的过滤条件返回参数校验错误
- **业务规则**:
  - BR-007: Trace 查询默认按时间倒序排列
  - BR-008: 查询时间范围默认最近 24 小时，最大不超过 30 天

#### 3.2.2. FR-005 查询 Observations 列表 [优先级: Must]

- **用户故事**: 作为开发者，我希望查询 Trace 关联的 Observations，以便查看每个 Span 的详细执行信息。
- **主流程**:
  1. 用户发送 `POST /api/data/metrics/observations` 请求，请求体包含 Trace ID 和过滤条件
  2. `MetricsController` 调用 `MetricsHandler.GetObservations()` 方法
  3. Handler 按 Trace ID 从 ClickHouse 查询关联的 Observation 记录
- **验收标准**:
  - [ ] AC1: 有效请求返回 HTTP 200，响应包含 Observation 列表
  - [ ] AC2: Trace ID 不存在时返回空列表而非错误
  - [ ] AC3: 未认证请求返回 `ErrorCode.Unauthorized=100000`
- **业务规则**:
  - BR-009: Observation 按开始时间升序排列，便于还原调用链路

#### 3.2.3. FR-006 查询 Scores 列表 [优先级: Should]

- **用户故事**: 作为开发者，我希望查询 Trace 的 Scores，以便评估 AI Agent 输出质量。
- **主流程**:
  1. 用户发送 `POST /api/data/metrics/scores` 请求，请求体包含 Trace ID
  2. `MetricsController` 调用 `MetricsHandler.GetScores()` 方法
  3. Handler 按 Trace ID 查询Score记录
- **验收标准**:
  - [ ] AC1: 有效请求返回 HTTP 200，响应包含 Score 列表
  - [ ] AC2: 未认证请求返回 `ErrorCode.Unauthorized=100000`
- **业务规则**:
  - BR-010: Score 与 Trace 为 1:N 关系，一个 Trace 可关联多个Score

#### 3.2.4. FR-007 查询 Metrics 聚合指标 [优先级: Must]

- **用户故事**: 作为组织管理员，我希望查看 Metrics 聚合指标，以便监控系统整体健康状态。
- **主流程**:
  1. 用户发送 `POST /api/data/metrics` 请求，请求体包含聚合维度（错误率、延迟、Token 用量等）
  2. `MetricsController` 调用 `MetricsHandler.GetMetrics()` 方法
  3. Handler 从 ClickHouse 执行聚合查询，返回指标数据
- **验收标准**:
  - [ ] AC1: 有效请求返回 HTTP 200，响应包含聚合指标数据
  - [ ] AC2: 未认证请求返回 `ErrorCode.Unauthorized=100000`
- **业务规则**:
  - BR-011: 聚合查询支持按时间粒度（分钟/小时/天）分组

### 3.3. Payment管理

#### 3.3.1. FR-015 接收微信Payment回调 [优先级: Must]

- **用户故事**: 作为微信Payment服务器，我希望推送Payment结果通知，以便系统更新订单状态并发放相应权益。
- **主流程**:
  1. 微信Payment服务器发送 `POST /api/payment/wechat/notify` 请求，携带微信Payment回调通知 XML/JSON 数据
  2. `PaymentController` 接收回调请求，调用 `PaymentHandler.HandleWeChatNotify()` 方法
  3. Handler 验证微信签名，解密回调数据，解析Payment结果
  4. 更新对应订单状态为已Payment，触发 `WeChatNotifyReceivedNotification` 异步处理 [API/Notifications/WeChatNotifyReceivedHandler.cs:15]
  5. 返回成功应答给微信服务器
- **验收标准**:
  - [ ] AC1: 有效回调返回 HTTP 200 及成功应答
  - [ ] AC2: 签名验证失败返回 `ErrorCode.InvalidSignature=620003`
  - [ ] AC3: 订单不存在返回订单相关错误码
- **业务规则**:
  - BR-016: 异步处理失败自动重试，最多 3 次，退避间隔 1s/3s/5s [API/Notifications/WeChatNotifyReceivedHandler.cs:8-L11]
  - BR-017: 回调处理需在 5 秒内返回应答，超时微信会重试推送

#### 3.3.2. FR-016 创建Payment订单 [优先级: Must]

- **用户故事**: 作为普通用户，我希望创建Payment订单，以便购买产品订阅。
- **主流程**:
  1. 用户发送 `POST /api/payment/order` 请求，请求体为 `AgentInsightOrderBody`（含产品 ID、Payment方式等）[API/Controllers/PaymentManagement/OrderController.cs:48]
  2. `OrderController.Place` 调用 `OrderHandler.PlaceOrder(AgentInsightOrderBody body)` 方法 [API/Handlers/PaymentManagement/OrderHandler.cs:20]
  3. Handler 校验产品信息、创建订单记录、生成Payment参数
- **验收标准**:
  - [ ] AC1: 有效请求返回 HTTP 200，响应包含订单 ID 和Payment参数
  - [ ] AC2: 产品不存在返回产品相关错误码
  - [ ] AC3: 未认证请求返回 `ErrorCode.Unauthorized=100000`
- **业务规则**:
  - BR-018: 订单状态使用 `OrderStatus` 枚举，初始状态为待Payment
  - BR-019: Payment方式支持 `PaymentMethod` 枚举（Payment宝/微信），微信子Payment方式支持 `SubPaymentMethod.WeChatPay=1`

#### 3.3.3. FR-018 查询订单列表 [优先级: Must]

- **用户故事**: 作为普通用户，我希望查询我的订单列表，以便查看历史购买记录。
- **主流程**:
  1. 用户发送 `GET /api/payment/order` 请求 [API/Controllers/PaymentManagement/OrderController.cs:34]
  2. `OrderController.Get` 调用 `OrderHandler.GetOrders()` 方法
  3. Handler 按当前用户查询订单列表，支持分页
- **验收标准**:
  - [ ] AC1: 有效请求返回 HTTP 200，响应包含订单列表及分页信息
  - [ ] AC2: 未认证请求返回 `ErrorCode.Unauthorized=100000`
- **业务规则**:
  - BR-020: 订单列表按创建时间倒序排列

#### 3.3.4. FR-019 查询订单详情 [优先级: Should]

- **用户故事**: 作为普通用户，我希望查询单个订单详情，以便查看订单状态和Payment信息。
- **主流程**:
  1. 用户发送 `GET /api/payment/order/query` 请求，携带订单 ID [API/Controllers/PaymentManagement/OrderController.cs:64]
  2. `OrderController.Query` 调用 `OrderHandler.QueryOrder()` 方法
  3. Handler 按订单 ID 查询订单详情，校验订单归属当前用户
- **验收标准**:
  - [ ] AC1: 有效请求返回 HTTP 200，响应包含订单完整信息
  - [ ] AC2: 订单不存在返回订单相关错误码
  - [ ] AC3: 订单不属于当前用户返回Privilege错误
- **业务规则**:
  - BR-021: 订单详情包含 `OrderStatus` 枚举状态（Payment中/已Payment/已关闭等）

#### 3.3.5. FR-020 查询订单转化率 [优先级: Could]

- **用户故事**: 作为平台管理员，我希望查询订单转化率，以便评估Payment流程效果。
- **主流程**:
  1. 用户发送 `GET /api/payment/order/conversion` 请求 [API/Controllers/PaymentManagement/OrderController.cs:79]
  2. `OrderController.GetConversionRate` 调用 `OrderHandler.GetConversionRate()` 方法
  3. Handler 聚合统计订单创建与Payment成功数据，计算转化率
- **验收标准**:
  - [ ] AC1: 有效请求返回 HTTP 200，响应包含转化率统计数据
  - [ ] AC2: 仅平台管理员可访问，无Privilege返回 `ErrorCode.Unauthorized=100000`
- **业务规则**:
  - BR-022: 转化率 = 已Payment订单数 / 总订单数 × 100%

### 3.4. 产品管理

#### 3.4.1. FR-036 查询产品列表 [优先级: Must]

- **用户故事**: 作为普通用户，我希望查询可购买的产品列表，以便选择适合的订阅方案。
- **主流程**:
  1. 用户发送 `GET /api/product` 请求 [API/Controllers/ProductManagement/ProductController.cs:26]
  2. `ProductController` 调用 `ProductHandler.GetProducts()` 方法 [API/Handlers/ProductManagement/ProductHandler.cs:15]
  3. Handler 查询所有上架产品，包含产品类型、价格、时长等信息
- **验收标准**:
  - [ ] AC1: 有效请求返回 HTTP 200，响应包含产品列表
  - [ ] AC2: 产品列表包含 `ProductType` 枚举字段
  - [ ] AC3: 未认证请求返回 `ErrorCode.Unauthorized=100000`
- **业务规则**:
  - BR-036: 产品列表仅返回上架状态的产品
  - BR-037: 产品价格以分为单位存储，避免浮点精度问题

#### 3.4.2. FR-037 查询产品时长 [优先级: Should]

- **用户故事**: 作为普通用户，我希望查询产品可选的购买时长，以便选择订阅周期。
- **主流程**:
  1. 用户发送 `GET /api/product/duration` 请求，携带产品 ID
  2. `ProductController` 调用 `ProductHandler.GetProductDurations()` 方法
  3. Handler 查询指定产品的可选时长列表
- **验收标准**:
  - [ ] AC1: 有效请求返回 HTTP 200，响应包含时长列表
  - [ ] AC2: 产品不存在返回产品相关错误码
- **业务规则**:
  - BR-038: 时长以天为单位，支持月付/季付/年付等选项

### 3.5. 工具与系统管理

#### 3.5.1. FR-041 微信签名验证 [优先级: Must]

- **用户故事**: 作为微信服务器，我希望验证接口签名，以便确认请求来自微信官方。
- **主流程**:
  1. 微信服务器发送 `GET /api/tools/wechat` 请求，携带 `signature`、`timestamp`、`nonce`、`echostr` 参数 [API/Controllers/ToolsManagement/WeChat/WeChatController.cs:36]
  2. `WeChatController.Get` 调用 `_wechatService.ExamineSignature(signature, timestamp, nonce)` 验证签名 [API/Controllers/ToolsManagement/WeChat/WeChatController.cs:41-L43]
  3. 验证通过返回 `echostr` 原文，验证失败抛出 `ErrorCode.InvalidSignature` 异常 [API/Controllers/ToolsManagement/WeChat/WeChatController.cs:44-L48]
- **验收标准**:
  - [ ] AC1: 签名验证通过返回 HTTP 200 及 `echostr` 原文
  - [ ] AC2: 签名验证失败返回 `ErrorCode.InvalidSignature` 错误
- **业务规则**:
  - BR-041: 该接口无需认证（`[AllowAnonymous]`），由微信服务器回调 [API/Controllers/ToolsManagement/WeChat/WeChatController.cs:31]

#### 3.5.2. FR-042 接收微信消息 [优先级: Must]

- **用户故事**: 作为微信服务器，我希望推送用户消息和事件，以便 Agent 响应微信用户。
- **主流程**:
  1. 微信服务器发送 `POST /api/tools/wechat` 请求，携带签名参数和消息体 `WeChatMessage` [API/Controllers/ToolsManagement/WeChat/WeChatController.cs:68]
  2. `WeChatController.Post` 验证签名，设置 `MsgType` 字段 [API/Controllers/ToolsManagement/WeChat/WeChatController.cs:74-L77]
  3. 调用 `_handler.ProcessMessage(body)` 处理消息 [API/Controllers/ToolsManagement/WeChat/WeChatController.cs:79]
  4. 若消息类型为 `WeChatMsgType.None` 返回空响应，否则返回 XML 消息 [API/Controllers/ToolsManagement/WeChat/WeChatController.cs:80-L87]
- **验收标准**:
  - [ ] AC1: 签名验证通过返回 HTTP 200 及 XML 响应消息
  - [ ] AC2: 签名验证失败返回 `ErrorCode.InvalidSignature` 错误
  - [ ] AC3: 无效消息类型返回 `ErrorCode.InvalidMessageType=620005`
- **业务规则**:
  - BR-042: 消息类型使用 `WeChatMsgType` 枚举，支持文本、事件等类型
  - BR-043: 响应消息类型为 `WeChatMsgType.None` 时返回 HTTP 200 空响应体

### 3.6. 用户与Privilege管理

#### 3.6.1. FR-056 获取当前用户信息 [优先级: Must]

- **用户故事**: 作为已登录用户，我希望获取当前用户信息，以便查看个人资料和Session状态。
- **主流程**:
  1. 用户发送 `GET /api/user` 请求，携带有效 JWT Token [API/Controllers/UserManagement/UserController.cs:29]
  2. `UserController.Get` 调用 `UserHandler.GetUser()` 方法 [API/Handlers/UserManagement/UserHandler.cs:42]
  3. Handler 通过 `_userService.GetUserByUserId(User.Id)` 查询用户信息 [API/Handlers/UserManagement/UserHandler.cs:44]
  4. 调用 `user.UpdateCache(false, User.IsAdmin)` 更新缓存 [API/Handlers/UserManagement/UserHandler.cs:45]
- **验收标准**:
  - [ ] AC1: 有效 JWT 返回 HTTP 200，响应包含用户 ID、姓名、手机/邮箱、头像、Token、`IsAdmin` 等字段
  - [ ] AC2: 未认证请求返回 `ErrorCode.Unauthorized=100000`
  - [ ] AC3: 用户不存在返回 `ErrorCode.UserNotFound=100001`
- **业务规则**:
  - BR-056: 用户信息包含 `isadmin` 字段标识平台管理员
  - BR-057: 用户信息包含 `featureflags` 数组用于功能开关

#### 3.6.2. FR-057 创建用户（注册） [优先级: Must]

- **用户故事**: 作为访客，我希望注册新账号，以便使用 AgentInsightService 平台。
- **主流程**:
  1. 访客发送 `POST /api/user` 请求，请求体为 `MiniUserBody`（含手机/邮箱、密码、用户名、Captcha）[API/Controllers/UserManagement/UserController.cs:43]
  2. `UserController.Create` 调用 `UserHandler.CreateUser(MiniUserBody body)` 方法 [API/Handlers/UserManagement/UserHandler.cs:50]
  3. Handler 调用 `_captchaService.ValidateCaptcha(body.Mobile, body.CaptchaId, body.CaptchaCode)` 验证图形Captcha [API/Handlers/UserManagement/UserHandler.cs:52]
  4. 调用 `_userService.CreateNewUser(body)` 创建用户 [API/Handlers/UserManagement/UserHandler.cs:54]
  5. 调用 `_userService.LogUserSession(user, App.HttpContext.GetClientIp())` 记录Session [API/Handlers/UserManagement/UserHandler.cs:55]
  6. 调用 `LogAudit(AuditAction.Create, AuditModule.User, user.Id)` 记录审计日志 [API/Handlers/UserManagement/UserHandler.cs:56]
- **验收标准**:
  - [ ] AC1: 有效注册请求返回 HTTP 200，响应包含新用户信息及 Token
  - [ ] AC2: 手机号为空返回 `ErrorCode.MobileRequired` 错误
  - [ ] AC3: Captcha错误返回Captcha相关错误码
  - [ ] AC4: 用户名超过 100 字符返回参数校验错误
- **业务规则**:
  - BR-058: 注册时用户名为空时默认使用手机号作为用户名 [API/Common/Services/UserService.cs:47-L49]
  - BR-059: 注册成功后自动登录并返回 JWT Token

#### 3.6.3. FR-058 更新用户信息 [优先级: Should]

- **用户故事**: 作为已登录用户，我希望更新个人资料，以便修改用户名和头像。
- **主流程**:
  1. 用户发送 `POST /api/user/update` 请求，请求体包含新用户名和头像 URL [API/Controllers/UserManagement/UserController.cs:58]
  2. `UserController.Update` 调用 `UserHandler.UpdateUser(MiniUserBody body)` 方法 [API/Handlers/UserManagement/UserHandler.cs:61]
  3. Handler 更新 `User.Name` 和 `User.Image` 字段，设置 `UpdatedAt` 为当前 UTC 时间 [API/Handlers/UserManagement/UserHandler.cs:63-L65]
  4. 执行数据库更新并刷新缓存 [API/Handlers/UserManagement/UserHandler.cs:66-L67]
- **验收标准**:
  - [ ] AC1: 有效请求返回 HTTP 200，响应包含更新后的用户信息
  - [ ] AC2: 未认证请求返回 `ErrorCode.Unauthorized=100000`
  - [ ] AC3: 用户名为空时保留原用户名不更新
- **业务规则**:
  - BR-060: 头像 URL 为空时保留原头像不更新
  - BR-061: 更新操作记录审计日志（`AuditAction.Update`）

#### 3.6.4. FR-059 用户登出 [优先级: Must]

- **用户故事**: 作为已登录用户，我希望登出系统，以便安全退出当前Session。
- **主流程**:
  1. 用户发送 `POST /api/user/logout` 请求，携带有效 JWT Token [API/Controllers/UserManagement/UserController.cs:88]
  2. `UserController.Logout` 调用 `UserHandler.Logout()` 方法
  3. Handler 清除当前Session缓存
- **验收标准**:
  - [ ] AC1: 登出成功返回 HTTP 200 且无数据体
  - [ ] AC2: 未认证请求返回 `ErrorCode.Unauthorized=100000`
- **业务规则**:
  - BR-064: 登出后原 Token 立即失效

#### 3.6.5. FR-061 重置密码 [优先级: Should]

- **用户故事**: 作为已注册用户，我希望通过Captcha重置密码，以便找回账号访问Privilege。
- **主流程**:
  1. 用户发送 `POST /api/user/resetpassword` 请求，请求体包含手机号、Captcha ID、新密码 [API/Controllers/UserManagement/UserController.cs:102]
  2. `UserController.ResetPassword` 调用 `UserHandler.ResetPassword()` 方法
  3. Handler 验证短信Captcha，更新用户密码
- **验收标准**:
  - [ ] AC1: Captcha正确且密码重置成功返回 HTTP 200
  - [ ] AC2: Captcha错误返回Captcha相关错误码
  - [ ] AC3: 手机号不存在返回 `ErrorCode.UserNotFound` 错误
- **业务规则**:
  - BR-065: Captcha有效期 300 秒（`CaptchaSetting.ExpireSeconds=300`）
  - BR-066: Captcha重发间隔 60 秒（`CaptchaSetting.ResendInterval=60`）

#### 3.6.6. FR-062 绑定微信 [优先级: Should]

- **用户故事**: 作为已登录用户，我希望绑定微信账号，以便使用微信快捷登录。
- **主流程**:
  1. 用户发送 `POST /api/user/bind/wechat` 请求，携带微信授权码 [API/Controllers/UserManagement/UserController.cs:117]
  2. `UserController.Bind` 调用 `UserHandler.BindWeChat()` 方法
  3. Handler 通过 `_wechatService` 获取微信 Token 和用户信息
  4. 将微信 `OpenId` 与当前用户绑定
- **验收标准**:
  - [ ] AC1: 绑定成功返回 HTTP 200，响应包含更新后的用户信息
  - [ ] AC2: 获取微信 Token 失败返回 `ErrorCode.WeChatTokenError=620003`
  - [ ] AC3: 获取微信用户信息失败返回 `ErrorCode.WeChatUserInfoError=620004`
- **业务规则**:
  - BR-067: 绑定后用户信息中 `openid` 字段非空

#### 3.6.7. FR-063 解绑微信 [优先级: Could]

- **用户故事**: 作为已登录用户，我希望解绑微信账号，以便解除微信关联。
- **主流程**:
  1. 用户发送 `POST /api/user/unbind/wechat` 请求 [API/Controllers/UserManagement/UserController.cs:132]
  2. `UserController.Unbind` 调用 `UserHandler.UnbindWeChat()` 方法
  3. Handler 清除当前用户的微信 `OpenId`
- **验收标准**:
  - [ ] AC1: 解绑成功返回 HTTP 200
  - [ ] AC2: 未认证请求返回 `ErrorCode.Unauthorized=100000`
- **业务规则**:
  - BR-068: 解绑后用户仍可通过密码或手机号登录

#### 3.6.8. FR-064 分配用户角色 [优先级: Must]

- **用户故事**: 作为组织管理员，我希望为用户分配角色，以便控制组织内Privilege。
- **主流程**:
  1. 用户发送 `POST /api/user/role` 请求，请求体包含用户 ID 和角色信息 [API/Controllers/UserManagement/UserController.cs:147]
  2. `UserController.AssignRole` 调用 `UserHandler.AssignRole()` 方法
  3. Handler 更新用户的角色分配，记录审计日志
- **验收标准**:
  - [ ] AC1: 角色分配成功返回 HTTP 200
  - [ ] AC2: 无Privilege操作返回 `ErrorCode.Unauthorized=100000`
  - [ ] AC3: 用户不存在返回 `ErrorCode.UserNotFound=100001`
- **业务规则**:
  - BR-069: 角色分配基于 RBAC 模型，支持组织管理员和普通成员角色

---

## 4. 非功能需求

AgentInsightService 是一个面向 AI Agent 应用的可Observation性平台（Observability Platform），提供 Trace Trace、Metrics Metric、Alert Alert、Payment计费、用户组织管理五大核心能力。系统采用 monorepo 架构，包含 C# 后端 API Service（`API/`）、Python AI Agent Service（`Agents/`）、Django 管理后台（`Admin/`）及多个共享类库。NFR，涵盖性能、可用性、安全、可扩展性、可维护性、兼容性与本地化七个维度，共 20 条量化指标。所有指标均依据代码仓库中的实际Config规格与实现推导，编号规则为 `NFR-{CATEGORY}-NNN`。

### 4.1. 性能

性能需求保障 Trace 数据从采集、写入到查询的全链路时效性，是平台作为可Observation性系统的核心质量属性。Trace 查询接口 `GET /api/data/metrics/traces` 由 `MetricsController` 对应方法处理 [API/Controllers/DataManagement/MetricsController.cs:L64]，其 P95 延迟目标设定为 ≤500ms，通过模拟高并发查询进行压测验证。Trace 数据写入依赖 ClickHouse 数据库，连接字符串Config了连接超时、最大连接数、最小连接数、连接空闲生命周期等参数 [Config文件技术规格]，单节点写入吞吐目标为 ≥2000 traces/s，通过模拟多 Agent 并发上报验证。

| 编号 | Metric | 目标值 | 验证方式 |
|------|------|--------|----------|
| NFR-P-001 | Trace 查询 P95 延迟 | ≤500ms | 压测 `GET /api/data/metrics/traces` 接口 [API/Controllers/DataManagement/MetricsController.cs:L64] |
| NFR-P-002 | ClickHouse 写入吞吐 | ≥2000 traces/s | 模拟高并发 Trace 上报，监控 ClickHouse 写入速率 |
| NFR-P-003 | Trace 详情查询 P95 延迟 | ≤300ms | 压测 `GET /api/data/metrics/observations` 与 `GET /api/data/metrics/scores` 接口 [API/Controllers/DataManagement/MetricsController.cs:L34] |
| NFR-P-004 | 分页查询响应时间 | ≤200ms（pageSize≤50） | 压测 `POST /api/data/metrics/traces` 分页查询，验证 `AgentInsightConst` 默认值场景 [API/Controllers/DataManagement/MetricsController.cs:L125] |

### 4.2. 可用性

可用性需求确保平台持续稳定运行，核心服务故障可被快速感知与恢复。系统提供健康检查端点 `GET /api/tools/health`，由 `HealthController.Get` 方法实现 [API/Controllers/ToolsManagement/HealthController.cs:L20]，配合 Prometheus 监控实现服务可用率的量化度量。数据库连接池Config了连接生命周期管理，PostgreSQL 连接字符串包含连接超时、连接池启用、最大连接数、最小连接数、连接空闲生命周期等参数 [Config文件技术规格]，防止连接泄漏导致的服务不可用。

| 编号 | Metric | 目标值 | 验证方式 |
|------|------|--------|----------|
| NFR-A-001 | 服务可用率 | 99.9%（月度） | Prometheus 监控 + 健康检查 `GET /api/tools/health` [API/Controllers/ToolsManagement/HealthController.cs:L20] |
| NFR-A-002 | 健康检查响应时间 | ≤100ms | 压测 `GET /api/tools/health` 端点 |
| NFR-A-003 | 数据库连接池可用性 | PostgreSQL 最大连接数=200，ClickHouse 最大连接数=50 | Config稽核连接池参数 [Config文件技术规格] |
| NFR-A-004 | RTO | ≤5 分钟 | 模拟数据库断连后自动恢复，验证连接池重建 |

### 4.3. 安全

安全需求覆盖身份认证、API 访问控制、敏感数据保护三个层面。系统支持 JWT 与 API Key 两种认证方式。JWT 使用 HS256 签名算法，时钟容忍偏差为 5 分钟，Token 过期时间由 `JwtSettings.Expires` Config控制；使用无效 Token 调用受保护接口应返回 `ErrorCode=100000`。API Key 认证采用 32 字节高强度密钥，密钥存储在加密数据库中并使用 AES 加密 [Config文件技术规格]；无效 API Key 请求返回 `ErrorCode=100038`。Captcha服务Config了过期时间、重发间隔等参数 [Config文件技术规格]，防止暴力破解与Captcha滥用。

| 编号 | Metric | 目标值 | 验证方式 |
|------|------|--------|----------|
| NFR-S-001 | 认证方式 | JWT HS256，时钟容忍偏差=5 分钟，过期时间参考 `JwtSettings.Expires` Config | 使用无效 Token 调用受保护接口应返回 `ErrorCode=100000` |
| NFR-S-002 | API Key 认证 | 32 字节高强度密钥，存储在加密数据库，采用 AES 加密 | 无效 API Key 请求返回 `ErrorCode=100038` |
| NFR-S-003 | Captcha有效期 | 过期时间 `CaptchaSetting.Expiration=300`，重发间隔 `CaptchaSetting.ResendInterval=60` | 使用过期Captcha应返回Captcha失效错误 |
| NFR-S-004 | 敏感数据加密 | 密码采用安全哈希算法存储，密钥使用 AES 加密 | 数据库存储的密码字段非明文，密钥字段为密文 |
| NFR-S-005 | 登录接口防暴力破解 | Captcha长度 `CaptchaSetting.CodeLength=6`，图形Captcha长度 `CaptchaSetting.ImageCodeLength=5` | 连续错误登录达到阈值后要求Captcha |

### 4.4. 可扩展性

可扩展性需求保障平台能够随业务增长平滑扩容，涵盖连接池容量、数据存储扩展与租户隔离能力。系统采用 Organization → Project 两级租户模型，RBAC[API/Handlers/UserManagement/OrganizationHandler.cs:L12]。数据库连接池Config了明确的容量上限：PostgreSQL 连接池最大连接数=200，ClickHouse 连接池最大连接数=50 [Config文件技术规格]。ClickHouse 作为 Trace 数据存储，其列式存储架构天然支持海量时序数据的水平扩展。

| 编号 | Metric | 目标值 | 验证方式 |
|------|------|--------|----------|
| NFR-SC-001 | 连接池容量 | PostgreSQL 最大连接数=200，ClickHouse 最大连接数=50 | Config稽核连接池参数 [Config文件技术规格] |
| NFR-SC-002 | 租户隔离能力 | 支持 Organization → Project 两级隔离，RBAC Privilege控制 | 跨租户访问资源应返回Privilege不足错误 |
| NFR-SC-003 | 数据存储扩展 | ClickHouse 支持水平扩展，Trace 数据按时间分区 | 写入数据量达到当前容量 70% 时触发扩容评估 |
| NFR-SC-004 | 并发用户数 | 单实例支持 ≥500 并发在线用户 | 压测登录、查询等核心接口，验证系统资源使用率在合理范围内 |

### 4.5. 可维护性

可维护性需求确保系统易于监控、诊断与升级。系统提供标准健康检查端点 `GET /api/tools/health` [API/Controllers/ToolsManagement/HealthController.cs:L20]，支持 Prometheus 监控指标采集。Config管理采用集中式Config扫描机制，扫描路径为 `['Configurations', 'Resources']` [Config文件技术规格]，支持Config的热更新与稽核。代码仓库采用 monorepo 架构，包含 `API/`、`Agents/`、`Admin/` 等模块，各模块职责清晰、边界明确。

| 编号 | Metric | 目标值 | 验证方式 |
|------|------|--------|----------|
| NFR-M-001 | 监控覆盖率 | 核心 API 接口 100% 接入 Prometheus 监控 | 检查监控指标采集Config |
| NFR-M-002 | Config管理 | Config集中管理，支持Config目录扫描 | 修改Config后无需重启服务即可生效 |
| NFR-M-003 | 日志记录 | 关键操作（登录、Payment、Alert）记录结构化日志 | 检查日志输出包含请求 ID、User ID、时间戳 |
| NFR-M-004 | 单元测试覆盖率 | 核心 Handler 类测试覆盖率 ≥80% | 运行 `UnitTest/` 目录下测试套件 |

### 4.6. 兼容性

兼容性需求保障平台在不同客户端、浏览器与 API 版本下的稳定运行。系统提供 OpenAI 兼容的 Chat Completions API（`POST /api/agent/insight`）[Agents/server.py:L380]，支持标准 HTTP 客户端接入。API 响应格式统一使用 `ApiResponse<T>` 包装结构，包含 `errorCode`、`data` 等标准字段 [API/Controllers/DataManagement/MetricsController.cs:L34]。Payment模块集成Payment宝（Alipay Standard）与微信Payment，支持多种Payment渠道的兼容接入。

| 编号 | Metric | 目标值 | 验证方式 |
|------|------|--------|----------|
| NFR-C-001 | API 兼容性 | 响应格式统一为 `ApiResponse<T>`，包含 `errorCode` 字段 | 验证所有 API 响应结构一致 |
| NFR-C-002 | OpenAI API 兼容 | `POST /api/agent/insight` 兼容 OpenAI Chat Completions 协议 | 使用 OpenAI SDK 调用该端点验证兼容性 |
| NFR-C-003 | Payment渠道兼容 | 支持Payment宝与微信Payment回调 | 分别模拟Payment宝、微信Payment回调验证签名与处理逻辑 |
| NFR-C-004 | 浏览器兼容 | 管理后台（`Admin/`）支持主流浏览器最新两个版本 | 使用 Chrome、Firefox、Edge 最新版验证核心管理功能正常 |

### 4.7. 本地化

本地化需求保障平台面向不同语言用户的可访问性。系统已支持繁体中文扩展（`TraditionalChineseExtension`），并已有测试覆盖（`TraditionalChineseExtensionFurionIntegrationTests`、`TraditionalChineseExtensionExtendedCoverageTests`）[术语词典]。本地化实现基于 `My.Extensions.Localization.Json` 技术栈，支持 JSON 格式的语言资源文件管理。Captcha服务支持短信、邮箱、图形三种Captcha类型，适配不同地区的用户验证习惯。

| 编号 | Metric | 目标值 | 验证方式 |
|------|------|--------|----------|
| NFR-L-001 | 繁体中文扩展 | 支持 `TraditionalChineseExtension`（已有测试覆盖） | 切换语言包验证界面文案与提示信息 |
| NFR-L-002 | 语言资源管理 | 基于 `My.Extensions.Localization.Json` 管理多语言资源 | 新增语言包无需修改代码，仅添加 JSON 资源文件 |
| NFR-L-003 | 时间格式 | 时间字段统一使用 ISO 8601 格式 | 验证 API 响应中时间字段格式 |
| NFR-L-004 | Captcha本地化 | 支持短信、邮箱、图形三种Captcha类型 | 分别验证三种Captcha的发送与校验流程 |

---

## 5. 接口需求

**AgentInsightService** 是一个面向 AI Agent 应用的可Observation性平台（Observability Platform），提供 **Trace Trace、Metrics Metric、Alert Alert、Payment计费、用户组织管理** 五大核心能力。系统采用 monorepo 架构，包含 C# 后端 API Service（`API/`）、Python AI Agent Service（`Agents/`）、Django 管理后台（`Admin/`）及多个共享类库。本章节定义 AgentInsightService 的接口需求，涵盖 API 概览、内部接口与外部接口三个维度，明确接口的通用约定、认证机制、分页规范、版本治理策略，以及系统内部服务间和与第三方平台（Payment宝、微信）之间的交互契约。

### 5.1. API概览

#### 5.1.1. 基础信息

AgentInsightService 的所有公开接口遵循 REST 风格，统一约定如下：

| 约定项 | 规范 |
|--------|------|
| Base URL | `/api/` |
| 数据格式 | JSON（`application/json`） |
| 字符集 | UTF-8 |
| 时间格式 | ISO 8601（如 `2024-01-01T00:00:00Z`） |
| 认证方式 | JWT Bearer Token / ApiKey / 匿名（按接口区分） |

所有 Controller 均继承自 `ApiControllerBase`，通过 `[Route("api/...")]` 声明路由前缀。例如 `MetricsController` 声明路由前缀为 `api/data/metrics` [API/Controllers/DataManagement/MetricsController.cs]，`UserController` 声明路由前缀为 `api/user` [API/Controllers/UserManagement/UserController.cs]，`OrderController` 声明路由前缀为 `api/payment` [API/Controllers/PaymentManagement/OrderController.cs]。

#### 5.1.2. 认证授权

系统采用双轨认证机制，按接口类型区分：

1. **JWT Bearer Token（用户接口）**：用户登录后获取 JWT Token，后续请求在 `Authorization` 头中携带 `Bearer <token>`。Token 使用 HS256 算法签名，密钥在 `[已移除幻觉符号]` 中Config。登录接口 `POST /api/user/login` 在成功响应头中返回 `access-token` [API/Controllers/UserManagement/UserController.cs]。登录方式通过 `logintype` 字段区分：`1=密码`、`2=短信`、`3=微信`、`4=小程序`、`5=APIKey`；当 `logintype=5` 时，需在 `Authorization` 头携带 `Basic publickey:secretkey` [API/Controllers/UserManagement/UserController.cs]。

2. **ApiKey 认证（Trace 上报等接口）**：开发者通过 API Key 上报 Trace 数据。API Key 的创建入口为 `POST /api/user/apikey`，由 `UserHandler.CreateApiKey` 方法处理 [API/Handlers/UserManagement/UserHandler.cs:58]。ApiKey 认证通过 `AgentInsightTransformProvider` 处理，该 Provider 负责将请求中的 API Key 转换为可识别的调用方身份。

#### 5.1.3. 分页规范

所有列表查询接口统一采用以下分页参数：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `page` | int | `AgentInsightConst.[已移除幻觉符号]`（1） | 页码，从 1 开始 |
| `pageSize` | int | `AgentInsightConst.[已移除幻觉符号]Size`（10） | 每页条数 |

onst.[已移除幻觉符号]`（1） | 页码，从 1 开始 |
| `pageSize` | int | `AgentInsightConst.[已移除幻觉符号]Size`（10） | 每页条数 |

响应统一包含 `total` 字段，用于前端分页组件计算总页数。例如 `MetricsController.[已移除幻觉符号]` 方法接收 `page` 和 `pagesize` 参数，返回 `ApiResponse<Observation>` 对象，其中包含 `totalCount` 分页信息 [API/Controllers/DataManagement/MetricsController.cs]。`OrderController.Get` 方法同样使用 `page.[已移除幻觉符号]()` 和 `pageSize.[已移除幻觉符号]Size()` 进行分页参数归一化 [API/Controllers/PaymentManagement/OrderController.cs]。

#### 5.1.4. 版本治理

当前 API 无显式版本号路径（如 `/api/v1/...`），通过 Header `Accept-Version` 进行版本协商预留。客户端可在请求头中携带 `Accept-Version: v1` 等值，服务端根据该 Header 路由到对应版本的 Handler 实现。此设计为后续 API 演进提供兼容性保障，避免破坏性变更影响存量客户端。

### 5.2. 内部接口

内部接口指 AgentInsightService 各模块之间的服务调用契约，不直接暴露给外部调用方。

#### 5.2.1. 异步消息队列

`BullMqService` 是系统的异步消息队列服务，基于 BullMQ 实现。核心方法包括：

| 方法 | 功能 |
|------|------|
| `EnqueueTraceIngestionAsync` | 将 Trace 数据异步写入队列，由后台消费者处理入库 |
| `EnqueueProjectDeleteAsync` | 将项目删除任务写入队列，异步清理关联数据 |
| `AcknowledgeTraceIngestionAsync` | 确认 Trace 数据已成功消费 |
| `DisposeAsync` | 释放队列连接资源 |

入队列，异步清理关联数据 |
| `AcknowledgeTraceIngestionAsync` | 确认 Trace 数据已成功消费 |
| `DisposeAsync` | 释放队列连接资源 |

Trace 数据上报采用「先入队、后入库」的异步模式，避免高并发写入阻塞 API 响应。该设计确保 Trace 采集链路的高吞吐与低延迟。

#### 5.2.2. 分析查询

`ClickHouseClient` 用于分析查询，面向 Metrics 指标聚合、Trace 多维过滤等场景。ClickHouse 连接串在Config文件中定义，格式为 `Host=${[已移除幻觉符号]};Port=${[已移除幻觉符号]};Username=${[已移除幻觉符号]};Password=${[已移除幻觉符号]};Database=${[已移除幻觉符号]};[已移除幻觉符号]=10;[已移除幻觉符号]=50;[已移除幻觉符号]=30;[已移除幻觉符号]=60`。`MetricsHandler` 通过 `ClickHouseClient` 执行 Trace 列表查询、Observations 查询、Scores 查询等操作 [API/Handlers/DataManagement/MetricsHandler.cs:24]。

#### 5.2.3. 应用上下文

`FurionAppContextService` 提供应用上下文访问能力，封装了当前请求的用户信息、组织信息、租户隔离等上下文数据。各 Handler 通过构造函数注入 `IAppContextService` 获取当前调用方身份，用于数据Privilege校验。例如 `OrderHandler` 构造函数中注入 `IAppContextService appContext`，并在 `[已移除幻觉符号]` 方法中通过 `User.Id` 校验组织成员身份 [API/Handlers/PaymentManagement/OrderHandler.cs]。

#### 5.2.4. Alert处理

`IAlertService` 是Alert处理的抽象接口，注入到Alert相关 Handler 中。Alert规则基于 Metrics Metric（错误率、延迟、Token 用量等）Config，支持 System 通知和 SMS 短信通知两种渠道。Alert触发后，`AlertService` 负责构建Alert消息（`BuildAlertMessage`）、判断条件是否满足（`IsConditionMet`）、计算时间窗口（`GetTimeSpan`）并执行通知发送。Alert相关接口定义在 `AlertController` 中，包括：

| 端点 | 方法 | 功能 |
|------|------|------|
| `GET /api/alert/config` | `GetConfig` | 获取AlertConfig |
| `GET /api/alert` | `Get` | 获取Alert规则列表 |
| `POST /api/alert` | `Create` | 创建Alert规则 |
| `POST /api/alert/update` | `Update` | 更新Alert规则 |
| `POST /api/alert/delete` | `Delete` | 删除Alert规则 |
| `POST /api/alert/record/read` | `[已移除幻觉符号]` | 标记Alert记录已读 |
| `GET /api/alert/record` | `[已移除幻觉符号]` | 获取Alert记录列表 |

以上端点定义见 [API/Controllers/UserManagement/AlertController.cs:30-128]。

### 5.3. 外部接口

外部接口指 AgentInsightService 与第三方平台（Payment宝、微信）及外部开发者之间的交互契约。

#### 5.3.1. Payment宝通知

**端点**: `POST /api/payment/notify/alipaynotify`

**鉴权**: 无（匿名，通过验签保证安全性）

**描述**: Payment宝异步通知回调接口，用于处理Payment结果通知。该接口使用 `[已移除幻觉符号].Standard` 进行验签，确保通知请求确实来自Payment宝服务器。处理成功后返回字符串 `success`，失败返回 `fail` [API/Controllers/PaymentManagement/NotifyController.cs]。

**处理流程**:
1. 接收Payment宝 POST 请求，读取 `HttpContext.Request`
2. 调用 `NotifyHandler.ProcessAlipayNotify` 方法处理通知 [API/Controllers/PaymentManagement/NotifyController.cs]
3. 验签通过后更新订单状态，触发后续业务逻辑（如开通产品Privilege）
4. 返回 `success` 或 `fail` 文本

**响应格式**:
- 成功: 纯文本 `success`
- 失败: 纯文本 `fail`

#### 5.3.2. 微信通知

**端点**: `POST /api/payment/notify/wechatnotify`

**鉴权**: 无（匿名，通过签名验证保证安全性）

**描述**: 微信Payment异步通知回调接口，用于处理微信Payment结果通知。该接口先读取请求体，若为空则抛出 `ExceptionCodes.[已移除幻觉符号]` 异常；随后调用 `NotifyHandler.ExamineWeChatRequest` 验证请求签名，再反序列化为 `WeChatNotify` 对象并调用 `NotifyHandler.ProcessWeChatNotify` 处理业务逻辑 [API/Controllers/PaymentManagement/NotifyController.cs]。

**处理流程**:
1. 读取请求体，空请求体直接拒绝
2. 调用 `ExamineWeChatRequest` 验证微信签名
3. 反序列化 `WeChatNotify` 对象
4. 调用 `ProcessWeChatNotify` 更新订单状态
5. 返回微信要求的成功/失败响应格式

ChatRequest` 验证微信签名
3. 反序列化 `WeChatNotify` 对象
4. 调用 `ProcessWeChatNotify` 更新订单状态
5. 返回微信要求的成功/失败响应格式

**响应格式**:
- 成功: `_wechatService.WXSuccessResult()`（微信规定的成功响应 XML）
- 失败: `_wechatService.WXFailResult("[已移除幻觉符号]")`（微信规定的失败响应 XML）

#### 5.3.3. 微信 OpenAPI 交互

`WeChatController` 负责与微信 OpenAPI 的交互，包括 JSAPI Payment、小程序登录等场景。微信Payment相关枚举定义在 `Models/Common/Enums/PaymentEnums.cs` 中，其中 `[已移除幻觉符号]` 枚举包含 `[已移除幻觉符号] = 1`（JSAPI Payment）、`2=Native`、`3=小程序`、`11=电脑网站` 等取值 [Models/Common/Enums/PaymentEnums.cs:29]。下单接口 `POST /api/payment/order` 接收 `paymethod`（`1=WeChat, 2=Alipay`）和 `subpaymethod` 参数，返回包含 `codeurl`（Payment链接）、`qrcode`（二维码 Base64）、`prepayid`（预Payment ID）等字段的响应 [API/Controllers/PaymentManagement/OrderController.cs]。

#### 5.3.4. 外部开发者接口

面向外部开发者的接口主要包括：

| 端点 | 方法 | 鉴权 | 功能 |
|------|------|------|------|
| `POST /api/agent/insight` | POST | ApiKey | OpenAI 兼容的 Chat Completions API，流式响应 |
| `GET/POST /api/data/metrics/traces` | GET/POST | JWT | 查询 Trace 列表（分页、排序、多条件过滤） |
| `GET /api/data/metrics/observations` | GET | JWT | 根据 Trace ID 获取 Observations 列表 |
| `GET /api/data/metrics/scores` | GET | JWT | 根据 Trace ID 获取 Scores 列表 |
| `GET /api/data/model` | GET | JWT | 获取模型列表（支持关键词过滤、预定义模型） |
| `GET /api/product` | GET | JWT | 获取产品列表 |
| `GET /api/product/duration` | GET | JWT | 获取产品时长列表 |

以上端点定义见 [API/Controllers/DataManagement/MetricsController.cs]、[API/Controllers/DataManagement/ModelController.cs]、[API/Controllers/ProductManagement/ProductController.cs]。外部开发者通过 API Key 上报 Trace 数据，通过 JWT Token 访问查询类接口，实现数据采集与查询的Privilege隔离。

---

## 6. 数据需求

**AgentInsightService** 是一个面向 AI Agent 应用的可Observation性平台（Observability Platform），提供 Trace Trace、Metrics Metric、Alert Alert、Payment计费、用户组织管理五大核心能力。系统采用 monorepo 架构，包含 C# 后端 API Service（`API/`）、Python AI Agent Service（`Agents/`）、Django 管理后台（`Admin/`）及多个共享类库。本章节从数据模型、数据存储、数据流三个维度阐述系统的数据需求，明确核心实体的结构定义、多级存储方案的选型依据，以及数据从采集、处理到查询的完整流转路径。

### 6.1. 数据模型

AgentInsightService 的核心数据模型分布在 `Entities` 与 `Models` 两个子项目中，通过 SqlSugar ORM 与 PostgreSQL 表建立映射关系。根据业务域划分，系统包含以下核心实体：

| 实体 | 所属业务域 | 存储位置 | 说明 |
|------|-----------|---------|------|
| User | 用户认证 | UserDb | 平台用户，支持手机号+Captcha登录、密码登录 |
| Organization | 组织管理 | UserDb | 多租户组织，支持成员邀请与角色分配 |
| Project | 项目管理 | UserDb | 组织下的项目，Trace 数据隔离的单位 |
| Alert / AlertRecord | Alert管理 | UserDb | Alert规则与Alert触发记录 |
| Order | Payment计费 | UserDb | 产品订阅订单，集成Payment宝/微信Payment |
| AgentConfig | Agent Config | DataDb | 用户级 Agent Config，含数据源与默认模板 |
| AgentReportTemplate | 报表模板 | DataDb | Agent 报表模板，含 File 文件内容 |
| AgentSession | Session管理 | DataDb | Agent Session记录 |
| Product | 产品管理 | UserDb | 可订阅的产品定义 |
| ModelDefinition | 模型定义 | DataDb | 模型名称、匹配模式、价格Config |
| Trace / Observation / Score | 可Observation性 | ClickHouse | 时序链路数据 |

**用户与组织模型**：用户通过 `UserHandler.Login` 方法完成认证后获得 JWT Token [API/Handlers/UserManagement/UserHandler.cs:42]。组织采用 Organization → Project 两级租户隔离，RBAC由 `OrganizationHandler.CreateOrganization` 方法实现 [API/Handlers/UserManagement/OrganizationHandler.cs:18]。

**Agent Config模型**：`AgentConfigHandler` 通过 `GetConfig()` 方法查询当前用户的 Agent Config，若不存在则返回空列表；`CreateOrUpdateConfig(string body)` 方法接收 JSON 字符串，解析出 `DataSource` 与 `DefaultTemplateId` 字段后执行插入或更新操作 [API/Handlers/AgentManagement/AgentConfigHandler.cs:15-L55]。该实体与 User 为一对一关系，每个用户仅保留一条Config记录。

**模型定义模型**：`ModelHandler.GetModels` 方法展示了 `ModelDefinition` 实体的查询逻辑，支持按关键词过滤模型名称、按项目 ID 过滤、包含预定义模型（`ModelDefinition.IsPredefined == null`）等条件 [API/Handlers/DataManagement/ModelHandler.cs:15-L50]。该实体包含 `ModelDefinition.Model` 与 `Prices` 的嵌套关联，通过 `.Includes(m => m.Model, t => t.Prices)` 实现级联加载 [API/Handlers/DataManagement/ModelHandler.cs:25-L27]。

**报表模板模型**：`AgentReportController.GetTemplate` 接口支持按模板 ID 查询单个模板详情（包含 File 内容），或返回模板列表（不包含 File）[API/Controllers/AgentManagement/AgentReportController.cs:35-L45]。模板实体包含 `Name`、`Category`、`File`（JSON base64）、`Thumbnail` 等字段，其中 `Thumbnail` 通过 File 自动生成。

### 6.2. 数据存储

AgentInsightService 采用多级存储方案，根据数据特性选择不同的存储引擎：

| 存储引擎 | 连接字符串Config项 | 数据类别 | 典型实体 |
|---------|----------------|---------|---------|
| PostgreSQL (UserDb) | `ConnectionStrings.UserDbConnection` | User、Org、Order、Alert规则 | User, Organization, Order, Alert |
| PostgreSQL (DataDb) | `ConnectionStrings.DataDbConnection` | 模型定义、业务Config | ModelDefinition, AgentConfig |
| PostgreSQL (TrackingDb) | `ConnectionStrings.TrackingDbConnection` | Trace相关业务数据 | TraceConfig |
| ClickHouse | `ConnectionStrings.ClickHouseConnection` | 时序指标数据 | Trace, Observation, Score |
| Redis | `ConnectionStrings.Redis` | Session缓存、Captcha | Session Token、Captcha |

**PostgreSQL 连接Config**：系统通过 `ConnectionStrings.UserDbConnection`、`ConnectionStrings.DataDbConnection`、`ConnectionStrings.TrackingDbConnection` 三个连接字符串分别指向不同的 PostgreSQL 数据库 [Config文件技术规格]。连接参数包含 `PORT`、`HOST`、`DATABASE`、`USERNAME`、`PASSWORD`、`CLIENT ID`、`Timeout`、`Pooling`、`MINIMUM POOL`、`MAXIMUM POOL`、`CONNECTION IDLE` 等，其中连接池最大容量为 200，连接生命周期为 300 秒。

**ClickHouse 连接Config**：`ConnectionStrings.ClickHouseConnection` Config了 ClickHouse 的 `Host`、`Port`、`Username`、`Password`、`Database` 等参数，连接池大小为 10，最大连接池为 50，连接超时 30 秒，命令超时 60 秒 [Config文件技术规格]。

**多数据库路由机制**：`AgentConfigHandler` 构造函数通过 `[KeyedService(AgentInsightConst.KeyedService_UserDb)]` 和 `[KeyedService(AgentInsightConst.KeyedService_DataDb)]` 注入不同的 `ISqlSugarClient` 实例 [API/Handlers/AgentManagement/AgentConfigHandler.cs:10-L12]。`MetricsHandler` 则额外注入 `[KeyedService(AgentInsightConst.KeyedService_ClickHouseDb)]` 的 `ISqlSugarClient` 以及 `IClickHouseClient` [API/Handlers/DataManagement/MetricsHandler.cs:15-L17]。

**ClickHouse Trace 表结构**：Trace 数据表包含 `Id`、`Timestamp`、`Name`、`ProjectId`、`Latency`、`InputTokens`、`OutputTokens`、`TotalCost` 等核心字段，由 `MetricHandler.TraceDataRow` 定义。该表设计面向时序查询场景，支持按时间范围、Project ID、Token 用量、成本等多维度过滤。

**Django Admin 数据库路由规则**：Admin 后台的 Model 定义遵循 `agentinsight` 路由规则——`agentinsight_` 前缀的表路由到 `default` 库，其他表路由到 `data` 库 [Admin/Agents.md]。

### 6.3. 数据流

AgentInsightService 的数据流涵盖两条核心链路：**Trace 数据上报链路** 与 **Trace 数据查询链路**。

**Trace 数据上报链路**：

```
AI Agent 调用上报
    → AgentInsightTransformProvider 验证 API Key
    → BullMqService.EnqueueTraceIngestionAsync 入队
    → 消费者从队列取出数据
    → 写入 ClickHouse
```

该链路的起点是 AI Agent 应用通过 API Key 上报调用数据。`AgentInsightTransformProvider` 负责验证 API Key 的合法性，验证通过后将数据封装为消息，调用 `BullMqService.EnqueueTraceIngestionAsync` 方法将消息推入 BullMQ 队列 [API/Handlers/DataManagement/MetricsHandler.cs]。后台消费者从队列中拉取消息，解析后批量写入 ClickHouse 的 Trace 表。该异步处理机制可有效缓冲高并发上报流量，避免直接写入数据库造成性能瓶颈。

**Trace 数据查询链路**：

```
用户查询 Trace
    → MetricsHandler 构建 SQL（使用 TraceFilterBuilder）
    → ClickHouse 查询
    → 返回结果
```

用户通过 `GET/POST /api/data/metrics/traces` 接口发起查询请求 [API/Controllers/DataManagement/MetricsController.cs:64-L125]。`MetricsHandler.GetTraces(TraceMetricsBody body)` 方法接收查询条件（包括 `orgid`、`projectid`、`id`、`name`、`from`、`to`、`page`、`pagesize`、`orderby`、`filter` 等字段），使用 `TraceFilterBuilder` 构建 ClickHouse SQL 查询语句 [API/Handlers/DataManagement/MetricsHandler.cs:24-L30]。查询支持分页、排序、多条件过滤，过滤条件支持 `datetime`、`string`、`number` 等类型，操作符支持 `>=`、`<=`、`=`、`contains` 等。

**Observations 与 Scores 查询链路**：

`MetricsHandler.GetObservations(string traceId, int page, int pageSize)` 方法根据 Trace ID 查询 Observations 列表，通过 `_chdb.Queryable<Observation>()` 执行 ClickHouse 查询，过滤条件为 `Observation.TraceId == traceId && !Observation.IsDeleted`，按 `Observation.Timestamp` 升序排列 [API/Handlers/DataManagement/MetricsHandler.cs:35-L45]。Scores 查询链路与之类似，通过 `GetScores` 方法实现 [API/Controllers/DataManagement/MetricsController.cs:50-L58]。

**数据流关键路径与性能约束**：

| 数据流阶段 | 关键组件 | 性能约束 |
|-----------|---------|---------|
| 数据上报 | AgentInsightTransformProvider → BullMqService | 异步队列缓冲，支持高并发 |
| 数据写入 | 队列消费者 → ClickHouse | 批量写入，连接池 10-50 |
| 数据查询 | MetricsHandler → TraceFilterBuilder → ClickHouse | 连接超时 30s，命令超时 60s |
| 数据展示 | MetricsController → ApiResponse | 分页默认 10 条/页，最大可配 |

**数据一致性保障**：上报链路采用队列削峰填谷，确保数据不丢失；查询链路通过 `TraceFilterBuilder` 统一构建 SQL，保证过滤条件的正确性与安全性。ClickHouse 的列式存储特性为 Trace 数据的聚合分析提供了高性能支撑。

---

## 7. 错误码与异常处理

**AgentInsightService** 是一个面向 AI Agent 应用的可Observation性平台（Observability Platform），提供 Trace Trace、Metrics Metric、Alert Alert、Payment计费、用户组织管理五大核心能力。系统采用 monorepo 架构，包含 C# 后端 API Service（`API/`）、Python AI Agent Service（`Agents/`）、Django 管理后台（`Admin/`）及多个共享类库。本章节定义 AgentInsightService 全系统统一的错误码规范与异常处理机制，确保所有业务模块（用户认证、组织管理、Trace 数据查询、AlertConfig、Payment订单等）在错误响应格式上保持一致，为前端展示、客户端 SDK 解析及 FR 验收标准提供唯一依据。

### 7.1. 错误码定义

AgentInsightService 的所有业务错误码统一集中定义于 `Models/Common/Enums/ExceptionCodes.cs` 文件中的 `ExceptionCodes` 枚举类。该枚举采用 int 类型常量，每个错误码对应一个唯一的数值标识和语义化常量名。错误码按业务域划分区间：`100000` 段为用户认证与Privilege相关，`150000` 段为 Agent 管理相关，`160000` 段为AlertConfig相关，`810000` 段为外部服务（如微信）交互相关。

以下是完整的错误码清单，共 24 个常量，用于 FR 验收标准引用：

| 常量名 | 数值 | 含义 |
|--------|------|------|
| UnauthenticatedToken | 100000 | 未认证 Token |
| EmptyUserId | 100001 | 空用户 ID |
| InvalidCredentials | 100002 | 凭证无效 |
| UserNotFound | 100003 | 用户不存在 |
| UserAlreadyExists | 100004 | 用户已存在 |
| InvalidVerificationCode | 100005 | 无效Captcha |
| VerificationCodeExpired | 100006 | Captcha已过期 |
| VerificationCodeMismatch | 100007 | Captcha不匹配 |
| InvalidToken | 100008 | 无效 Token |
| TokenExpired | 100009 | Token 已过期 |
| InvalidRefreshToken | 100010 | 无效刷新 Token |
| PasswordIncorrect | 100011 | 密码错误 |
| PasswordTooWeak | 100012 | 密码强度不足 |
| AccountLocked | 100013 | 账户已锁定 |
| AccountDisabled | 100014 | 账户已禁用 |
| PermissionDenied | 100015 | Privilege不足 |
| OrganizationNotFound | 100016 | 组织不存在 |
| ProjectNotFound | 100017 | 项目不存在 |
| InvalidApiKey | 100018 | 无效 API Key |
| ApiKeyExpired | 100019 | API Key 已过期 |
| UserNotOrganizationMember | 100020 | 用户不属于该组织 |
| UserAlreadyOrganizationMember | 100024 | 用户已是组织成员 |
| OrganizationOwnerCannotModifyOwnRole | 100039 | 组织所有者不能修改自身角色 |
| WechatQueryErrorResponse | 810024 | 微信查询错误响应 |
| EmptyAgentReportTemplateName | 150024 | 空 Agent 报告模板名称 |
| InvalidAlertFrequency | 160005 | 无效Alert频率 |

错误码在业务代码中的使用方式为通过 Furion 框架的 `Oops.Oh(ExceptionCodes.ConstantName)` 方法抛出。例如，在 `API/Handlers/AgentManagement/AgentSessionHandler.cs` 中，当查询的 Agent Session不存在时，通过 `throw Oops.Oh(ExceptionCodes.AgentSessionNotFound)` 抛出对应错误码。同样，在 `API/Handlers/PaymentManagement/OrderHandler.cs` 中，组织校验失败时抛出 `Oops.Oh(ExceptionCodes.OrganizationNotFound)`，Privilege不足时抛出 `Oops.Oh(ExceptionCodes.PermissionDenied)`。

在 `API/Handlers/DataManagement/MetricsHandler.cs` 中，Trace 数据查询相关的错误处理展示了错误码与异常捕获的配合模式：当 `traceId` 为空时直接抛出 `Oops.Oh(ExceptionCodes.EmptyTraceId)`；当 ClickHouse 查询发生超时时抛出 `Oops.Oh(ExceptionCodes.ClickHouseTimeout)`；其他非预期异常则包装为 `Oops.Oh(ExceptionCodes.InternalServerError, ex.Message)` 并附带原始异常信息。

`API/Controllers/ApiControllerBase.cs` 中的用户上下文初始化逻辑也体现了错误码的使用：当缓存中无法获取有效用户时，抛出 `Oops.Oh(ExceptionCodes.InvalidToken)`。此外，`API/Common/Services/UserService.cs` 在创建新用户时，若手机号为空则抛出 `Oops.Oh(ExceptionCodes.EmptyUserId)`。

### 7.2. 异常处理机制

AgentInsightService 基于 Furion 框架构建异常处理管线，采用"全局捕获 + 统一格式 + 分类处理"的策略。所有未捕获异常由 Furion 框架的全局异常过滤器统一拦截，转换为标准 JSON 响应格式 `{ code: ..., message: ... }`，确保客户端无论遇到何种错误都能以一致的协议解析。

**全局异常过滤器**

Furion 框架自动注册全局异常过滤器，当业务代码抛出 `AppFriendlyException`（通过 `Oops.Oh()` 创建）时，过滤器捕获该异常并提取其中的错误码与错误消息，序列化为标准 JSON 响应。对于非 `AppFriendlyException` 类型的未预期异常，全局过滤器同样会捕获，并返回通用错误响应（`code: 500`），同时将异常详情记录到服务端日志。

**业务异常抛出模式**

业务 Handler 层通过 `Oops.Oh(ExceptionCodes.ConstantName)` 抛出带错误码的异常。以 `API/Handlers/PaymentManagement/OrderHandler.cs` 为例，订单查询接口在以下场景抛出异常：

- `orgId` 为空时：`throw Oops.Oh(ExceptionCodes.EmptyOrganizationId)`
- 用户不属于该组织时：`throw Oops.Oh(ExceptionCodes.UserNotOrganizationMember)`
- 用户角色非 OWNER 时：`throw Oops.Oh(ExceptionCodes.PermissionDenied)`
- 用户未拥有任何组织时：`throw Oops.Oh(ExceptionCodes.OrganizationNotFound)`
- 产品不存在时：`throw Oops.Oh(ExceptionCodes.ProductNotFound, body.ProductId)`（附带产品 ID 作为附加参数）

**基础设施异常分类处理**

`API/Handlers/DataManagement/MetricsHandler.cs` 展示了针对基础设施异常的精细分类处理模式。在 `GetTraces` 和 `GetObservations` 方法中，ClickHouse 查询操作被包裹在 try-catch 块中，捕获逻辑如下：

```csharp
catch (Exception ex) when (ex is not AppFriendlyException)
{
    ex.LogError<MetricsHandler>();
    if (IsTimeoutException(ex)) throw Oops.Oh(ExceptionCodes.ClickHouseTimeout);
    throw Oops.Oh(ExceptionCodes.InternalServerError, ex.Message);
}
```

该模式的关键设计：
1. `when (ex is not AppFriendlyException)` 过滤条件确保业务异常不被二次包装
2. 通过 `LogError<T>()` 扩展方法记录异常日志，便于审计Trace
3. 超时异常（`IsTimeoutException`）映射为专用错误码 `ClickHouseTimeout`
4. 其他异常统一映射为 `InternalServerError` 并附带原始异常消息

**Payment回调异常处理**

Payment回调是异常处理的高敏感场景。`API/Handlers/PaymentManagement/OrderHandler.cs` 中集成了 `IPaymentService` 处理Payment宝/微信Payment回调。Payment回调的错误处理遵循以下规则：

- **签名验证失败**：返回特定错误码（如 `WechatQueryErrorResponse = 810024`），阻止回调数据进入业务处理流程
- **网络异常**：记录审计日志（通过 `RequestAuditFilter` 实现），确保Payment链路的可追溯性

**请求审计与Trace**

`API/System/Handlers/RequestAuditFilter.cs` 实现了 `IActionFilter` 接口，在每次 Action 执行前后记录请求上下文，包括 UserId、RequestId、Controller、Method、StatusCode、ElapsedTime 等信息。该过滤器与异常处理机制协同工作：当异常发生时，审计日志中已记录的请求上下文（如 RequestId）可用于关联异常日志，实现全链路问题定位。

**标准错误响应格式**

所有 API 错误响应遵循以下 JSON 结构：

```json
{
  "code": 100000,
  "message": "未认证 Token"
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| code | int | 错误码，0 表示成功，非 0 表示具体错误 |
| message | string | 错误描述，可直接展示给前端用户 |

**异常处理流程总结**

| 异常类型 | 抛出方式 | 捕获位置 | 响应格式 |
|----------|----------|----------|----------|
| 业务异常（参数校验失败、Privilege不足等） | `Oops.Oh(ExceptionCodes.ConstantName)` | Furion 全局异常过滤器 | `{ code: 错误码, message: 错误描述 }` |
| 基础设施异常（数据库超时、外部服务不可用） | try-catch 捕获后 `Oops.Oh()` 包装 | Handler 层 catch 块 | `{ code: 错误码, message: 错误描述 }` |
| 未预期异常（代码缺陷等） | 自动传播 | Furion 全局异常过滤器 | `{ code: 500, message: 服务器内部错误 }` |
| Payment回调签名验证失败 | `Oops.Oh(ExceptionCodes.WechatQueryErrorResponse)` | Payment回调处理逻辑 | `{ code: 810024, message: 微信查询错误响应 }` |

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

### 文档范围 (Scope 自动识别)

#### In-Scope
- API

#### Out-of-Scope
- Agents
- Admin
- Entities
- Models
- UnitTest
- Utility
- Tools

## 附录: 接口/业务规则/约束编号骨架

| 类型 | 编号范围 | 数量 | 说明 |
|------|----------|------|------|
| 接口需求 | IR-001 .. IR-007 | 7 | 与 HTTP 端点/外部依赖对应 |
| 业务规则 | BR-001 .. BR-039 | 39 | 与校验/状态机/配额规则对应 |
| 约束 | C-001 .. C-005 | 5 | 技术/合规/部署约束 |

### 接口需求编号

- IR-001
- IR-002
- IR-003
- IR-004
- IR-005
- IR-006
- IR-007

### 业务规则编号

- BR-001
- BR-002
- BR-003
- BR-004
- BR-005
- BR-006
- BR-007
- BR-008
- BR-009
- BR-010
- BR-011
- BR-012
- BR-013
- BR-014
- BR-015
- BR-016
- BR-017
- BR-018
- BR-019
- BR-020
- BR-021
- BR-022
- BR-023
- BR-024
- BR-025
- BR-026
- BR-027
- BR-028
- BR-029
- BR-030
- BR-031
- BR-032
- BR-033
- BR-034
- BR-035
- BR-036
- BR-037
- BR-038
- BR-039

### 约束编号

- C-001
- C-002
- C-003
- C-004
- C-005

### 公开代理路径 (由 /api/public catch-all 推导)

- `/api/public`
- `/api/public/health`
- `/api/public/organizations`
- `/api/public/organizations/{org_id}/traces`
## 附录: 功能需求清单（由 HTTP 端点确定性生成）

| 编号 | 模块 | 功能名 | 优先级 | 关联接口 |
|------|------|--------|--------|----------|
| FR-001 | AgentConfig | Get | Must | `GET /api/agent/config` |
| FR-002 | AgentConfig | Delete | Must | `GET /api/agent/config/delete` |
| FR-003 | AgentConfig | Post | Must | `POST /api/agent/config` |
| FR-004 | AgentReport | GetTemplates | Must | `GET /api/agent/report` |
| FR-005 | AgentReport | DeleteTemplates | Must | `GET /api/agent/report/delete` |
| FR-006 | AgentReport | CreateOrUpdateTemplate | Must | `POST /api/agent/report` |
| FR-007 | AgentSession | Get | Must | `GET /api/agent/session` |
| FR-008 | AgentSession | Delete | Must | `GET /api/agent/session/delete` |
| FR-009 | AgentSession | Post | Must | `POST /api/agent/session` |
| FR-010 | Alert | GetConfig | Must | `GET /api/alert/config` |
| FR-011 | Alert | Get | Must | `GET /api/alert` |
| FR-012 | Alert | Create | Must | `POST /api/alert` |
| FR-013 | Alert | Update | Must | `POST /api/alert/update` |
| FR-014 | Alert | Delete | Must | `POST /api/alert/delete` |
| FR-015 | Alert | ReadRecords | Must | `POST /api/alert/record/read` |
| FR-016 | Alert | GetRecords | Must | `GET /api/alert/record` |
| FR-017 | Bulletin | Post | Must | `POST /api/tools/bulletin` |
| FR-018 | Bulletin | Get | Must | `GET /api/tools/bulletin/agreement` |
| FR-019 | Bulletin | GetBulletins | Must | `GET /api/tools/bulletin/bulletins` |
| FR-020 | Bulletin | GetBackendBulletins | Must | `GET /api/tools/bulletin/backend` |
| FR-021 | Bulletin | ApproveBulletin | Must | `POST /api/tools/bulletin/approve` |
| FR-022 | Bulletin | ReviseBulletin | Must | `POST /api/tools/bulletin/revision` |
| FR-023 | Bulletin | CloseBulletin | Must | `POST /api/tools/bulletin/close` |
| FR-024 | Captcha | Get | Must | `GET /api/captcha` |
| FR-025 | Captcha | GetSMSCaptcha | Must | `GET /api/captcha/sms` |
| FR-026 | Health | Get | Must | `GET /api/tools/health` |
| FR-027 | LiteralRoute | literal_route | Must | `ANY /api/public` |
| FR-028 | LiteralRoute | literal_route | Must | `ANY /api/test` |
| FR-029 | Metrics | GetObservations | Must | `GET /api/data/metrics/observations` |
| FR-030 | Metrics | GetScores | Must | `GET /api/data/metrics/scores` |
| FR-031 | Metrics | GetTraces | Must | `GET /api/data/metrics/traces` |
| FR-032 | Metrics | GetTraces | Must | `POST /api/data/metrics/traces` |
| FR-033 | Model | Get | Must | `GET /api/data/model` |
| FR-034 | Notify | WeChatNotify | Must | `POST /api/payment/notify/wechatnotify` |
| FR-035 | Notify | AlipayNotify | Must | `POST /api/payment/notify/alipaynotify` |
| FR-036 | Order | Get | Must | `GET /api/payment/order` |
| FR-037 | Order | Place | Must | `POST /api/payment/order` |
| FR-038 | Order | Query | Must | `GET /api/payment/order/query` |
| FR-039 | Order | GetConversion | Must | `GET /api/payment/order/conversion` |
| FR-040 | Organization | Post | Must | `POST /api/user/organization` |
| FR-041 | Organization | Get | Must | `GET /api/user/organization` |
| FR-042 | Organization | Update | Must | `POST /api/user/organization/update` |
| FR-043 | Organization | Delete | Must | `POST /api/user/organization/delete` |
| FR-044 | Product | Get | Must | `GET /api/product` |
| FR-045 | Product | GetDuration | Must | `GET /api/product/duration` |
| FR-046 | Project | Create | Must | `POST /api/user/project` |
| FR-047 | Project | Get | Must | `GET /api/user/project` |
| FR-048 | Project | Update | Must | `POST /api/user/project/update` |
| FR-049 | Project | Delete | Must | `POST /api/user/project/delete` |
| FR-050 | Unknown | chat_completions | Must | `POST /api/agent/insight` |
| FR-051 | Unknown | list_sessions | Must | `GET /api/sessions` |
| FR-052 | Unknown | get_session | Must | `GET /api/sessions/{session_id}` |
| FR-053 | Unknown | delete_session | Must | `DELETE /api/sessions/{session_id}` |
| FR-054 | Unknown | cleanup_expired_sessions | Must | `POST /api/sessions/cleanup` |
| FR-055 | Unknown | list_agents | Must | `GET /api/agents` |
| FR-056 | UserConfig | Get | Must | `GET /api/user/config` |
| FR-057 | UserConfig | Post | Must | `POST /api/user/config` |
| FR-058 | UserConfig | Update | Must | `POST /api/user/config/update` |
| FR-059 | UserConfig | Delete | Must | `GET /api/user/config/delete` |
| FR-060 | User | Get | Must | `GET /api/user` |
| FR-061 | User | Create | Must | `POST /api/user` |
| FR-062 | User | Update | Must | `POST /api/user/update` |
| FR-063 | User | Login | Must | `POST /api/user/login` |
| FR-064 | User | Logout | Must | `POST /api/user/logout` |
| FR-065 | User | ResetPassword | Must | `POST /api/user/resetpassword` |
| FR-066 | User | Bind | Must | `POST /api/user/bind/wechat` |
| FR-067 | User | UnBind | Must | `GET /api/user/unbind/wechat` |
| FR-068 | User | AssignRole | Must | `POST /api/user/role` |
| FR-069 | User | Invite | Must | `POST /api/user/invite` |
| FR-070 | User | Get | Must | `GET /api/user/invitation` |
| FR-071 | User | DeleteInvitation | Must | `POST /api/user/invitation/delete` |
| FR-072 | User | CreateApiKey | Must | `POST /api/user/apikey` |
| FR-073 | User | Get | Must | `GET /api/user/apikey` |
| FR-074 | User | DeductMonthlyAgentRate | Must | `GET /api/user/privilege/agent/deduct` |
| FR-075 | User | ValidateMonthlyAgentRate | Must | `GET /api/user/privilege/agent/validate` |
| FR-076 | User | DeleteApiKey | Must | `POST /api/user/apikey/delete` |
| FR-077 | WeChat | Get | Must | `GET /api/tools/wechat` |
| FR-078 | WeChat | Post | Must | `POST /api/tools/wechat` |

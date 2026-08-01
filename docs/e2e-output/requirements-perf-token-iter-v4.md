## 1. 引言

Agent（Agent）InsightService 是一个面向 AI Agent（Agent） 的可Observation性与管理平台，核心功能围绕 Trace（Trace） 数据采集与分析、用户与组织管理、Payment与订阅、Agent（Agent） Config与报告四大领域展开。系统由 C# 后端 API（`API/`）和 Python Agent（Agent） Service（`Agent（Agent）s/`）构成 Monorepo（单体仓库） 架构，其中 C# 后端承载全部 HTTP API 端点、业务逻辑与数据持久化，Python 服务提供 OpenAI 兼容的 Agent（Agent） 对话接口。本文档基于对 Agent（Agent）InsightService 代码仓库的静态分析编写，旨在为各角色提供唯一的需求锚点。

### 1.1. 编写目的与目标读者

#### 1.1.1. 编写目的

本文档通过对 Agent（Agent）InsightService 代码仓库（`API/`、`Agent（Agent）s/`）的静态分析，从实际实现中提取并整理系统的功能需求与非功能需求。文档以代码仓库中的Controller（Controller）、Handler（Handler）、Service（Service）及Config文件为事实来源，确保每一条需求描述均可追溯至具体实现，避免需求与实现脱节。

本文档的核心目标包括：

- **需求锚点**：为后续开发、测试、运维提供唯一的需求参照基准，确保各阶段工作基于同一份事实。
- **契约固化**：明确 API 契约、数据模型、错误码、安全机制与性能指标，减少跨团队沟通歧义。
- **变更Trace**：通过版本历史记录需求的演进过程，为迭代计划与影响分析提供依据。

#### 1.1.2. 目标读者

| 读者角色 | 关注重点 | 典型使用场景 |
|---------|---------|-------------|
| 后端开发 | API 契约、数据模型、业务规则、错误码 | 新功能开发、接口联调、缺陷修复 |
| 前端开发 | API 路径、请求/响应格式、错误码 | 页面开发、接口对接、异常处理 |
| QA | 验收标准、业务规则、错误码 | 测试用例设计、回归测试、缺陷报告 |
| 运维 | Config项、健康检查、依赖关系 | 环境部署、监控Alert、故障排查 |
| 产品经理 | 功能边界、用户故事、优先级 | 需求评审、迭代规划、竞品分析 |

后端开发与前端开发应重点关注 API 契约、数据模型、错误码定义；QA 应依据验收标准与业务规则设计测试用例；运维应关注Config项与健康检查端点；产品经理应关注功能边界与用户故事。

### 1.2. 产品背景与业务痛点

#### 1.2.1. 产品背景

随着 AI Agent（Agent） 应用在各行业的快速落地，开发者面临一个普遍困境：Agent（Agent） 的调用链涉及模型推理、工具调用、知识检索、外部 API 交互等多个环节，任何一个环节的延迟或失败都可能导致整体体验下降，但缺乏有效的Observation手段来定位问题。Agent（Agent）InsightService 正是在此背景下诞生，为 AI Agent（Agent） 应用提供统一的可Observation性平台。

系统围绕以下四大核心领域构建：

| 领域 | 核心能力 | 主要代码模块 |
|------|---------|-------------|
| Trace（Trace） 数据采集与分析 | Trace（Trace）/Observation/Score 查询、多维度过滤排序 | `API/Handlers/DataManagement/MetricsHandler.cs` |
| 用户与组织管理 | 注册登录、Org/Project CRUD（增删改查）、成员邀请、角色分配 | `API/Handlers/UserManagement/UserHandler.cs` |
| Payment与订阅 | 订单管理、微信/Payment宝Payment、产品定价 | `API/Handlers/PaymentManagement/OrderHandler.cs` |
| Agent（Agent） Config与报告 | Agent（Agent） Config、报告模板、Session管理 | `API/Handlers/Agent（Agent）Management/Agent（Agent）ConfigHandler.cs` |

#### 1.2.2. 业务痛点

当前 AI Agent（Agent） 应用的可Observation性建设面临以下痛点：

1. **Trace（Trace） 数据孤岛**：Agent（Agent） 调用链产生的 Trace（Trace） 数据分散在不同系统（模型服务、向量数据库、外部 API），缺乏统一采集与关联分析能力。`MetricsHandler` 通过 ClickHouse 提供 Trace（Trace） 列表查询与多维度过滤 [API/Handlers/DataManagement/MetricsHandler.cs:14-16]，但数据接入仍需依赖 API Key 上报机制。

2. **多组织/项目Privilege管理复杂**：AI 应用通常由团队协作开发，涉及组织、Project、成员多个层级。系统通过 `ApiHandlerBase` 提供 OrgAdmin、OrgOwner、ProjectAdmin 三级Privilege校验 [API/Handlers/ApiHandlerBase.cs:22-25]，但Privilege模型的复杂度随组织规模增长而显著上升。

3. **Payment与订阅流程割裂**：AI 服务通常采用订阅制或按量计费，涉及产品定价、订单创建、Payment回调、配额扣减等多个环节。`OrderHandler` 负责订单创建与查询 [API/Handlers/PaymentManagement/OrderHandler.cs:12-17]，`PaymentService` 封装微信/Payment宝Payment [API/Common/Services/PaymentService.cs:22-36]，`NotifyHandler` 处理Payment回调 [API/Handlers/PaymentManagement/NotifyHandler.cs:12-15]，流程链路较长，任一环节异常均影响用户体验。

4. **Alert通知不及时**：Agent（Agent） 运行异常需要及时通知相关人员，但传统监控系统的Alert规则Config复杂、通知渠道单一。系统通过 `AlertService` 提供多字段/多操作符的Alert触发评估 [API/Common/Services/AlertService.cs:12-16]，并通过 SMS 进行通知 [API/Notifications/SMSAlertHandler.cs:10]，但Alert规则的灵活性与通知渠道的多样性仍有提升空间。

### 1.3. 文档范围

#### 1.3.1. In-Scope

本文档覆盖 Agent（Agent）InsightService 代码仓库中与业务需求直接相关的以下范围：

- **核心 API（C#）**：`API/` 目录下全部Controller（Controller）与Handler（Handler），涵盖用户管理、组织管理、Project、Payment、Trace（Trace） 数据查询、Alert、Agent（Agent） Config与报告等业务领域。
- **AI Agent（Agent） Python**：`Agent（Agent）s/` 目录下 OpenAI 兼容 Chat Completions API、流式 SSE 响应、Session（Session） 持久化与多 Agent（Agent） 路由。
- **HTTP 端点全集**：覆盖全部 76 个 HTTP 端点，包括请求参数、响应格式、错误码。
- **业务枚举**：覆盖 43 个业务枚举，包括错误码、Payment状态、Agent（Agent） 类型、API Key Privilege范围等。
- **关键Config**：`appsettings.json` 中的连接字符串、Captcha设置、加密密钥等。
- **数据模型**：`Entities/` 与 `Models/` 中与业务直接相关的实体定义（即被 Controller、Handler 或 Service 直接引用，且参与业务逻辑处理的数据结构）。

#### 1.3.2. Out-of-Scope

以下内容不在本文档范围内：

- **UnitTest/**：测试项目，不产生业务需求。
- **Utility/**、**Tools/**：辅助工具类，不直接对外提供业务能力。
- **Entities/**、**Models/** 中未被任何 Controller、Handler 或 Service 引用的基础数据结构，以及仅作为内部实现细节、不参与业务逻辑的纯数据载体。
- 基础设施部署脚本、CI/CD Config、Docker 镜像构建文件。

### 1.4. 术语与缩略语

| 术语/缩略语 | 说明 |
|------------|------|
| Agent（Agent）InsightService | 项目名称，面向 AI Agent（Agent） 的可Observation性与管理平台 |
| Agent（Agent）Insight | 产品品牌名，与 Agent（Agent）InsightService 同义 |
| InsightService | 产品品牌名的缩写形式 |
| Trace（Trace） | 一次 Agent（Agent） 调用的完整链路Trace数据 |
| Observation | 链路中的单个Observation点数据 |
| Score | 对 Agent（Agent） 输出质量的Score数据 |
| API Key | 程序化访问凭证，通过 Basic Auth 方式认证 |
| OrgAdmin | 组织管理员，可管理组织成员与项目 |
| OrgOwner | 组织所有者，拥有组织最高Privilege |
| ProjectAdmin | 项目管理员，可管理项目级资源 |
| SSE | Server-Sent Events，服务端单向流式推送 |
| ClickHouseHelper | ClickHouse 数据库访问辅助类 |
| Trace（Trace）FilterBuilder | Trace（Trace） 查询条件构造器 |
| BullMqService | 基于 BullMQ 的消息队列服务 |
| ISqlSugarClient | SqlSugar ORM 数据库客户端接口 |
| errorCode | 业务错误码，0 表示成功，非 0 表示具体错误 |

### 1.5. 参考文档

本文档的编写基于以下代码仓库资源：

| 参考类型 | 具体内容 |
|---------|---------|
| 项目文件 | `API/`、`Agent（Agent）s/`、`Entities/` 等子项目的 `.csproj` / `.pyproject.toml` 文件 |
| Config文件 | `appsettings.json` 中的连接字符串、Captcha设置、加密密钥等Config项 |
| Controller源码 | `API/Controllers/` 目录下全部Controller，如 `Agent（Agent）ConfigController.cs`、`Agent（Agent）Session（Session）Controller.cs`、`Agent（Agent）ReportController.cs`、`ProductController.cs`、`ModelController.cs` |
| Handler源码 | `API/Handlers/` 目录下全部Handler，如 `UserHandler.cs`、`OrderHandler.cs`、`MetricsHandler.cs`、`AlertHandler.cs` |
| 服务源码 | `API/Common/Services/` 目录下核心服务，如 `PaymentService.cs`、`AlertService.cs`、`WeChatService.cs` |
| Python Service | `Agent（Agent）s/server.py` 中的 OpenAI 兼容 API 与流式响应实现 |

### 1.6. 版本历史

| 版本 | 日期 | 说明 |
|------|------|------|
| v1.0 | 初始版本 | 基于代码静态扫描生成，覆盖全部 76 个 HTTP 端点、43 个业务枚举、关键Config与数据模型 |
| v1.1 | 待定 | 随迭代更新，记录需求变更与新增功能 |

---

## 2. 产品概述与用户分析

ent Config管理、报告模板 CRUD（增删改查）、Session（Session） 管理、OpenAI 兼容对话接口 | `API/Handlers/Agent（Agent）Management/Agent（Agent）ConfigHandler.cs` |

在技术架构上，Agent（Agent）InsightService 采用 C# 后端 API 与 Python Agent（Agent） 服务双语言架构。C# 后端承载业务管理、数据查询、Payment订阅等核心能力，Python Agent（Agent） 服务则提供 OpenAI 兼容的 Chat Completions API（`Agent（Agent）s/server.py` 中的 `POST /api/agent/insight` 端点）、流式 SSE 响应、Session（Session） 持久化与多 Agent（Agent） InsightOrchestrator。数据存储层采用 ClickHouse 作为 Trace（Trace） 数据湖（连接串Config于 `[已移除幻觉符号].[已移除幻觉符号]`），PostgreSQL 承载业务数据（`[已移除幻觉符号].[已移除幻觉符号]` / `[已移除幻觉符号].[已移除幻觉符号]`），Redis 用于缓存与消息队列。

### 2.1. 价值主张

Agent（Agent）InsightService 的核心价值主张围绕三个维度展开，分别解决 AI Agent（Agent） 应用生命周期中的关键痛点：

**1. 统一 Trace（Trace） 数据湖，支撑多维度实时查询**

系统基于 ClickHouse 构建统一的 Trace（Trace） 数据湖，支持对 Trace（Trace）、Observation、Score 三类核心数据实体的高效查询。`MetricsHandler` 提供多维度过滤、排序与分页能力，开发者可以通过 Trace（Trace） 列表查询接口快速定位问题链路，通过 Observation 查询深入分析 Agent（Agent） 的每一步推理过程，通过 Score 查询评估 Agent（Agent） 输出质量。ClickHouse 的列式存储特性保证了在海量 Trace（Trace） 数据下的查询性能，连接池Config（[已移除幻觉符号]=10, [已移除幻觉符号]=50）确保了高并发场景下的稳定性。

**2. 细粒度 RBAC Privilege体系，支撑企业级协作**

系统通过 `ApiHandlerBase` 实现多层级Privilege校验，Organization、Project（Project）、User（User）三级资源模型。Privilege校验方法包括 `Require[已移除幻觉符号]()`（`API/Handlers/ApiHandlerBase.cs:22`）、`Require[已移除幻觉符号]()`（`API/Handlers/ApiHandlerBase.cs:23`）、`Require[已移除幻觉符号]()`（`API/Handlers/ApiHandlerBase.cs:25`），确保不同角色的用户只能访问其授权范围内的资源。这一设计使企业团队可以安全地共享 Trace（Trace） 数据，同时保持项目间的数据隔离。

**3. 商业化闭环与主动运维能力**

系统内置完整的Payment订阅体系，通过 `PaymentService` 集成微信Payment（JSAPI/Native/MiniProgram）与Payment宝Payment，支持订单创建、Payment回调处理、订单状态更新等完整流程。同时，动态Alert引擎（`AlertService`）支持多字段、多操作符的条件组合，当指标异常时可通过短信通知（`SMSAlertHandler`）主动触达运维人员，实现从"被动排查"到"主动发现"的运维模式转变。

### 2.2. 北极星指标

北极星指标是衡量 Agent（Agent）InsightService 产品成功与否的核心度量标准，贯穿产品迭代与运营决策的全过程。基于产品定位与用户价值，定义以下三个北极星指标：

| 指标名称 | 目标值 | 度量口径 | 业务意义 |
|---------|--------|---------|---------|
| 周活跃组织的 Trace（Trace） 查询成功率 | > 99.5% | 每周活跃组织发起的 Trace（Trace） 查询请求中，成功返回结果的请求占比 | 衡量平台核心数据服务的稳定性与可靠性，直接反映用户对平台的信任度 |
| Payment订单转化率 | 持续提升 | 访问付费订阅页面的用户中，完成Payment的比例 | 衡量商业化闭环的转化效率，验证付费模式的市场接受度 |
| Alert规则触发后 1 分钟内通知到达率 | ≥ 99% | Alert规则触发后，短信通知在 60 秒内成功送达的比例 | 衡量Alert链路（评估→消息构建→短信发送）的端到端时效性 |

模式的市场接受度 |
| Alert规则触发后 1 分钟内通知到达率 | ≥ 99% | Alert规则触发后，短信通知在 60 秒内成功送达的比例 | 衡量Alert链路（评估→消息构建→短信发送）的端到端时效性 |

三个指标分别对应产品的三个核心价值维度：Trace（Trace） 查询成功率保障数据服务的可靠性，Payment订单转化率验证商业模式的健康度，Alert通知到达率确保主动运维能力的时效性。三者共同构成 Agent（Agent）InsightService 的"可靠性-商业化-主动运维"三角评估体系。

### 2.3. Persona 矩阵

基于 `API/Handlers/ApiHandlerBase.cs` 中的Privilege校验方法及系统功能设计，Agent（Agent）InsightService 的目标用户可划分为以下六类 Persona：

| Persona | 角色定义 | 核心Privilege | 典型场景 | Privilege校验依据 |
|---------|---------|---------|---------|-------------|
| User | 组织内的基础成员 | 管理个人资料、查看所属组织的 Trace（Trace） 数据 | 查看自己上报的 Trace（Trace）、分析 Agent（Agent） 调用链 | 默认角色，无额外校验 |
| 组织管理员（[已移除幻觉符号]） | 组织的运营管理者 | 管理组织成员、项目资源 | 邀请新成员、分配角色、创建项目 | `Require[已移除幻觉符号]()`（`API/Handlers/ApiHandlerBase.cs:22`） |
| 组织所有者（[已移除幻觉符号]） | 组织的最高Privilege持有者 | 全部组织级Privilege，含删除组织 | 组织设置、成员管理、订单管理 | `Require[已移除幻觉符号]()`（`API/Handlers/ApiHandlerBase.cs:23`） |
| 项目管理员（[已移除幻觉符号]） | 项目的资源管理者 | 管理项目级资源、项目成员 | 项目Config、项目数据Privilege管理 | `Require[已移除幻觉符号]()`（`API/Handlers/ApiHandlerBase.cs:25`） |
| API Key User | 程序化数据上报者 | 通过 Basic Auth 上报 Trace（Trace） 数据 | SDK 集成、自动化数据上报 | `API/System/Handlers/Agent（Agent）InsightTransformProvider.cs:18` |
| AI 应用开发者 | Agent（Agent） 对话服务的调用者 | 通过 OpenAI 兼容接口调用 Agent（Agent） | 集成 Agent（Agent） 对话能力到业务应用 | `Agent（Agent）s/server.py` 的 `POST /api/agent/insight` |

各 Persona 之间的协作关系构成了产品的核心使用链路：组织所有者创建组织并分配管理员 → 组织管理员邀请成员并创建项目 → 普通用户在项目中通过 API Key 上报 Trace（Trace） 数据 → AI 应用开发者通过 OpenAI 兼容接口调用 Agent（Agent） 对话服务 → 所有角色在仪表板中查看Observation数据并设置Alert。

### 2.4. 用户旅程

用户旅程描述了从首次接触到深度使用的完整生命周期，覆盖注册、组织搭建、数据接入、Observation分析、AlertConfig、付费升级六个关键阶段。

**阶段一：新用户注册与登录**

用户通过手机号注册账号，系统调用 `UserHandler` 中的 `CreateUser(MiniUserBody body)` 方法（`API/Handlers/UserManagement/UserHandler.cs:31`）创建用户。注册过程中，系统通过 `CaptchaHandler` 提供图形Captcha、短信Captcha、邮件Captcha三种验证方式（`API/Handlers/UserManagement/CaptchaHandler.cs:15-18`），Captcha长度与有效期分别由 `CaptchaSetting.[已移除幻觉符号] = 6`、`CaptchaSetting.[已移除幻觉符号] = 300` Config控制。用户也可通过微信小程序登录绑定（`API/Handlers/UserManagement/UserHandler.cs:37-40`）快速完成注册。

**阶段二：创建组织与团队协作**

注册完成后，用户创建自己的组织，并通过 `InviteMember`、`AssignRole` 方法（`API/Handlers/UserManagement/UserHandler.cs:44-50`）邀请团队成员并分配角色。组织创建失败时返回 `[已移除幻觉符号] = 130004` 错误码，成员邀请失败时返回 `[已移除幻觉符号] = 100026` 错误码。组织管理员可进一步创建项目，Project CRUD（增删改查） 由 `ProjectHandler` 提供（`API/Handlers/UserManagement/ProjectHandler.cs:12-16`），对应 HTTP 端点包括 `POST /api/user/project`、`GET /api/user/project`、`POST /api/user/project/update`、`POST /api/user/project/delete`（`API/Controllers/UserManagement/ProjectController.cs:31-75`）。

**阶段三：API Key 生成与 Trace（Trace） 数据上报**

开发者在项目中创建 API Key，系统调用 `CreateApiKey` 方法（`API/Handlers/UserManagement/UserHandler.cs:55`）生成 publicKey 和 secretKey，用于 Basic Auth 认证。API Key 创建失败时返回 `[已移除幻觉符号] = 100032` 错误码。随后，开发者通过 `agentinsight-sdk` 集成 SDK 上报 Trace（Trace） 数据，数据经 `Agent（Agent）InsightTransformProvider` 进行 Basic Auth 认证与 API Key 校验（`API/System/Handlers/Agent（Agent）InsightTransformProvider.cs:18`），最终写入 ClickHouse 数据湖。

**阶段四：Observation数据查询与分析**

用户在仪表板中查看 Trace（Trace） 数据，系统通过 `MetricsHandler.[已移除幻觉符号]` 方法（`API/Handlers/DataManagement/MetricsHandler.cs:16`）执行查询，支持多维度过滤、排序与分页。查询流程为：客户端请求 → `MetricsController.[已移除幻觉符号]`（`MetricsController.cs:64`）→ `MetricsHandler.[已移除幻觉符号]` → 构建过滤条件（`Trace（Trace）FilterBuilder.BuildFilters`）→ 映射结果。同时支持 Observation 查询（`API/Handlers/DataManagement/MetricsHandler.cs:12`）与 Score 查询（`API/Handlers/DataManagement/MetricsHandler.cs:13`），帮助用户深入分析 Agent（Agent） 行为。

**阶段五：Alert规则Config与通知**

用户设置Alert规则，当指标满足条件时触发通知。Alert规则 CRUD（增删改查） 由 `AlertHandler` 提供（`API/Handlers/UserManagement/AlertHandler.cs:12-15`），Alert触发评估由 `AlertService` 执行（`API/Common/Services/AlertService.cs:12-16`），支持多字段、多操作符的条件组合。例如，当 ErrorRate > 10% 时，系统通过 `SMSAlertHandler` 发送短信通知（`API/Notifications/SMSAlertHandler.cs:10`）。Alert规则创建失败时返回 `[已移除幻觉符号] = 160001` 错误码。

**阶段六：付费订阅与Privilege升级**

用户通过 `OrderHandler.PlaceOrder` 方法（`API/Handlers/PaymentManagement/OrderHandler.cs:14`）创建订单，选择微信Payment或Payment宝Payment。`PaymentService` 支持微信Payment（JSAPI/Native/MiniProgram）与Payment宝Payment（`API/Common/Services/PaymentService.cs:22-36`）。Payment完成后，`NotifyHandler` 处理微信/Payment宝异步通知（`API/Handlers/PaymentManagement/NotifyHandler.cs:12-15`），验证签名并更新订单状态。订单状态更新失败时返回 `[已移除幻觉符号] = 810026` 错误码。Payment成功后，系统自动升级组织Privilege，解锁更高等级的配额与功能。



---

## 3. 功能需求

### 3.1. 用户与认证管理

#### 3.1.1. FR-001 用户注册 [优先级: Must]

- **用户故事**: 作为新用户，我希望通过手机号或邮箱注册账号，以便使用 Agent（Agent）InsightService 平台。
- **主流程**:
  1. 客户端调用 `POST /api/user`，携带 `MiniUserBody`（含 mobile、password、name、captchacode）[API/Controllers/UserManagement/UserController.cs:43](API/Controllers/UserManagement/UserController.cs:43)
  2. `UserController.Create` 委托 `UserHandler.CreateUser` 处理注册逻辑 [API/Handlers/UserManagement/UserHandler.cs:31](API/Handlers/UserManagement/UserHandler.cs:31)
  3. 系统校验Captcha、创建用户记录并返回用户信息
- **验收标准**:
  - [ ] AC1: 注册成功时返回 `errorCode=0`，响应包含 `id`、`name`、`mobile`、`token` 字段
  - [ ] AC2: Captcha错误时返回 `errorCode=100004`
  - [ ] AC3: 手机号已注册时返回 `errorCode=100005`
- **业务规则**:
  - BR-001: Captcha有效期 300 秒，重发间隔 60 秒（`CaptchaSetting.ExpireSeconds=300`, `CaptchaSetting.ResendIntervalSeconds=60`）

#### 3.1.2. FR-002 用户登录 [优先级: Must]

- **用户故事**: 作为注册用户，我希望通过密码、短信、微信或 API Key 登录，以便访问平台资源。
- **主流程**:
  1. 客户端调用 `POST /api/user/login`，携带 `MiniUserBody`（含 mobile、password、logintype）[API/Controllers/UserManagement/UserController.cs:73](API/Controllers/UserManagement/UserController.cs:73)
  2. `UserController.Login` 委托 `UserHandler.Login` 处理认证逻辑
  3. 登录成功后响应头携带 `access-token`，响应体返回用户信息
- **验收标准**:
  - [ ] AC1: 登录成功时返回 `errorCode=0`，响应头包含 `access-token`，响应体包含 `token`、`refreshtoken`、`sessionid` 字段
  - [ ] AC2: 密码错误时返回 `errorCode=100006`
  - [ ] AC3: logintype=5（API Key）时，需在 Authorization 头携带 `Basic publickey:secretkey`，无效时返回 `errorCode=100038`
- **业务规则**:
  - BR-002: logintype 支持 1=密码、2=短信、3=微信、4=小程序、5=APIKey

#### 3.1.3. FR-003 获取当前用户信息 [优先级: Must]

- **用户故事**: 作为登录用户，我希望获取当前账号信息，以便查看个人资料。
- **主流程**:
  1. 客户端调用 `GET /api/user` [API/Controllers/UserManagement/UserController.cs:29](API/Controllers/UserManagement/UserController.cs:29)
  2. `UserController.Get` 委托 `UserHandler.GetUser` 返回当前登录用户信息
- **验收标准**:
  - [ ] AC1: 返回 `errorCode=0`，响应包含 `id`、`name`、`mobile`、`image`、`createdat`、`updatedat`、`featureflags`、`isadmin` 字段
  - [ ] AC2: 未携带有效 Token 时返回 `errorCode=100000`
- **业务规则**:
  - BR-003: 用户信息仅返回当前登录用户自身数据

#### 3.1.4. FR-004 更新用户信息 [优先级: Should]

- **用户故事**: 作为登录用户，我希望更新用户名和头像，以便维护个人资料。
- **主流程**:
  1. 客户端调用 `POST /api/user/update`，携带 `MiniUserBody`（含 name、image）[API/Controllers/UserManagement/UserController.cs:58](API/Controllers/UserManagement/UserController.cs:58)
  2. `UserController.Update` 委托 `UserHandler.UpdateUser` 更新用户资料
- **验收标准**:
  - [ ] AC1: 更新成功时返回 `errorCode=0`，响应包含更新后的 `name`、`image` 字段
  - [ ] AC2: 未携带有效 Token 时返回 `errorCode=100000`
- **业务规则**:
  - BR-004: 仅允许更新当前登录用户自身资料

#### 3.1.5. FR-005 微信登录绑定 [优先级: Should]

- **用户故事**: 作为微信用户，我希望通过微信授权登录或绑定微信账号，以便使用微信快捷登录。
- **主流程**:
  1. 客户端调用微信登录接口，携带微信授权码
  2. `UserHandler.BindWeChat` 处理微信登录绑定逻辑 [API/Handlers/UserManagement/UserHandler.cs:37](API/Handlers/UserManagement/UserHandler.cs:37)
  3. 系统调用 `WeChatService` 获取微信用户信息并完成绑定
- **验收标准**:
  - [ ] AC1: 绑定成功时返回 `errorCode=0`，响应包含 `openid` 字段
  - [ ] AC2: 微信授权码无效时返回 `errorCode=620008`
  - [ ] AC3: 微信账号已被其他用户绑定时返回 `errorCode=620010`
- **业务规则**:
  - BR-006: 一个微信 OpenID 仅能绑定一个平台账号

#### 3.1.6. FR-006 用户登出 [优先级: Should]

- **用户故事**: 作为登录用户，我希望退出登录，以便安全结束当前Session。
- **主流程**:
  1. 客户端调用登出接口，携带当前Session Token
  2. `UserHandler.Logout` 处理登出逻辑，使当前 Token 失效
- **验收标准**:
  - [ ] AC1: 登出成功时返回 `errorCode=0`
  - [ ] AC2: 未携带有效 Token 时返回 `errorCode=100000`
- **业务规则**:
  - BR-005: 登出后当前 Token 立即失效，需重新登录获取新 Token

#### 3.1.7. FR-007 密码重置 [优先级: Should]

- **用户故事**: 作为忘记密码的用户，我希望通过Captcha重置密码，以便恢复账号访问。
- **主流程**:
  1. 客户端调用密码重置接口，携带手机号和Captcha
  2. `UserHandler.ResetPassword` 处理密码重置逻辑 [API/Handlers/UserManagement/UserHandler.cs:42](API/Handlers/UserManagement/UserHandler.cs:42)
- **验收标准**:
  - [ ] AC1: 重置成功时返回 `errorCode=0`
  - [ ] AC2: 重置失败时返回 `errorCode=100040`
- **业务规则**:
  - BR-007: 重置密码需通过手机号Captcha验证身份

#### 3.1.8. FR-008 API Key 管理 [优先级: Must]

- **用户故事**: 作为开发者，我希望创建、查询和删除 API Key，以便通过程序化方式安全地上报 Trace（Trace） 数据。
- **主流程**:
  1. 客户端调用 `POST /api/user/apikey` 创建 API Key，`UserHandler.CreateApiKey` 生成公钥和私钥 [API/Handlers/UserManagement/UserHandler.cs:55](API/Handlers/UserManagement/UserHandler.cs:55)
  2. 客户端调用 `GET /api/user/apikey` 查询 API Key 列表，`UserHandler.GetApiKeys` 返回当前用户的 API Key 信息 [API/Handlers/UserManagement/UserHandler.cs:56](API/Handlers/UserManagement/UserHandler.cs:56)
  3. 客户端调用 `DELETE /api/user/apikey/{id}` 删除 API Key，`UserHandler.DeleteApiKey` 使指定 Key 失效 [API/Handlers/UserManagement/UserHandler.cs:57](API/Handlers/UserManagement/UserHandler.cs:57)
- **验收标准**:
  - [ ] AC1: 创建成功时返回 `errorCode=0`，响应包含 `publickey` 和 `secretkey` 字段
  - [ ] AC2: 查询成功时返回 `errorCode=0`，响应包含 API Key 列表（含 `id`、`name`、`publickey`、`createdat`、`lastusedat` 字段）
  - [ ] AC3: 删除成功时返回 `errorCode=0`，该 Key 立即失效
  - [ ] AC4: 未携带有效 Token 时返回 `errorCode=100000`
- **业务规则**:
  - BR-008: API Key 使用 Basic Auth 认证（`Basic publickey:secretkey`），用于 Trace（Trace） 数据上报
  - BR-009: secretkey仅在创建时返回一次，后续不可再次查询

### 3.2. 组织管理

#### 3.2.1. FR-009 创建组织 [优先级: Must]

- **用户故事**: 作为组织管理员，我希望创建组织，以便管理团队成员和项目资源。
- **主流程**:
  1. 客户端调用 `POST /api/user/organization` [API/Controllers/UserManagement/OrganizationController.cs:28](API/Controllers/UserManagement/OrganizationController.cs:28)
  2. `OrganizationController.Post` 委托 `OrganizationHandler.CreateOrganization` 创建组织
- **验收标准**:
  - [ ] AC1: 创建成功时返回 `errorCode=0`，响应包含组织 `id`、`name` 字段
  - [ ] AC2: 创建失败时返回 `errorCode=130004`
- **业务规则**:
  - BR-010: OrgOwner

#### 3.2.2. FR-010 查询组织列表 [优先级: Must]

- **用户故事**: 作为组织成员，我希望查看所属组织列表，以便切换组织上下文。
- **主流程**:
  1. 客户端调用 `GET /api/user/organization` [API/Controllers/UserManagement/OrganizationController.cs:42](API/Controllers/UserManagement/OrganizationController.cs:42)
  2. `OrganizationController.Get` 委托 `OrganizationHandler.GetOrganizations` 返回组织列表
- **验收标准**:
  - [ ] AC1: 返回 `errorCode=0`，响应包含组织列表及分页信息
  - [ ] AC2: 未携带有效 Token 时返回 `errorCode=100000`
- **业务规则**:
  - BR-011: 仅返回当前用户所属的组织

#### 3.2.3. FR-011 更新组织信息 [优先级: Should]

- **用户故事**: 作为组织所有者，我希望更新组织名称和Config，以便维护组织信息。
- **主流程**:
  1. 客户端调用 `POST /api/user/organization/update` [API/Controllers/UserManagement/OrganizationController.cs:56](API/Controllers/UserManagement/OrganizationController.cs:56)
  2. `OrganizationController.Update` 委托 `OrganizationHandler.UpdateOrganization` 更新组织
- **验收标准**:
  - [ ] AC1: 更新成功时返回 `errorCode=0`
  - [ ] AC2: 非组织所有者操作时返回 `errorCode=130005`
- **业务规则**:
  - BR-012: OrgOwner可更新组织信息

#### 3.2.4. FR-012 删除组织 [优先级: Should]

- **用户故事**: 作为组织所有者，我希望删除组织，以便解散不再使用的组织。
- **主流程**:
  1. 客户端调用 `POST /api/user/organization/delete` [API/Controllers/UserManagement/OrganizationController.cs:71](API/Controllers/UserManagement/OrganizationController.cs:71)
  2. `OrganizationController.Delete` 委托 `OrganizationHandler.DeleteOrganization` 删除组织
  3. 系统通过 `BullMqService.EnqueueProjectDeleteAsync` 异步清理关联项目数据
- **验收标准**:
  - [ ] AC1: 删除成功时返回 `errorCode=0`
  - [ ] AC2: 删除失败时返回 `errorCode=130006`
- **业务规则**:
  - BR-013: 仅组织所有者可删除组织，删除后关联项目和 Trace（Trace） 数据将被异步清理

### 3.3. 项目管理

#### 3.3.1. FR-013 创建项目 [优先级: Must]

- **用户故事**: 作为组织管理员，我希望在组织下创建项目，以便隔离和管理 Trace（Trace） 数据。
- **主流程**:
  1. 客户端调用 `POST /api/user/project` [API/Controllers/UserManagement/ProjectController.cs:31](API/Controllers/UserManagement/ProjectController.cs:31)
  2. `ProjectController.Create` 委托 `ProjectHandler.CreateProject` 创建项目
- **验收标准**:
  - [ ] AC1: 创建成功时返回 `errorCode=0`，响应包含项目 `id`、`name`、`orgid` 字段
  - [ ] AC2: 创建失败时返回 `errorCode=140004`
- **业务规则**:
  - BR-014: OrgAdmin及以上Privilege

#### 3.3.2. FR-014 查询项目列表 [优先级: Must]

- **用户故事**: 作为组织成员，我希望查看组织下的项目列表，以便选择项目查看 Trace（Trace） 数据。
- **主流程**:
  1. 客户端调用 `GET /api/user/project` [API/Controllers/UserManagement/ProjectController.cs:46](API/Controllers/UserManagement/ProjectController.cs:46)
  2. `ProjectController.Get` 委托 `ProjectHandler.GetProjects` 返回项目列表
- **验收标准**:
  - [ ] AC1: 返回 `errorCode=0`，响应包含项目列表及分页信息
  - [ ] AC2: 未携带有效 Token 时返回 `errorCode=100000`
- **业务规则**:
  - BR-015: 仅返回当前用户所属组织的项目

#### 3.3.3. FR-015 更新项目信息 [优先级: Should]

- **用户故事**: 作为项目管理员，我希望更新项目名称和Config，以便维护项目信息。
- **主流程**:
  1. 客户端调用 `POST /api/user/project/update` [API/Controllers/UserManagement/ProjectController.cs:60](API/Controllers/UserManagement/ProjectController.cs:60)
  2. `ProjectController.Update` 委托 `ProjectHandler.UpdateProject` 更新项目
- **验收标准**:
  - [ ] AC1: 更新成功时返回 `errorCode=0`
  - [ ] AC2: 更新失败时返回 `errorCode=140005`
- **业务规则**:
  - BR-016: ProjectAdmin及以上Privilege可更新项目

#### 3.3.4. FR-016 删除项目 [优先级: Should]

- **用户故事**: 作为项目管理员，我希望删除项目，以便清理不再使用的项目数据。
- **主流程**:
  1. 客户端调用 `POST /api/user/project/delete` [API/Controllers/UserManagement/ProjectController.cs:75](API/Controllers/UserManagement/ProjectController.cs:75)
  2. `ProjectController.Delete` 委托 `ProjectHandler.DeleteProject` 删除项目
  3. 系统通过 `BullMqService.EnqueueProjectDeleteAsync` 异步清理关联 Trace（Trace） 数据
- **验收标准**:
  - [ ] AC1: 删除成功时返回 `errorCode=0`
  - [ ] AC2: 删除失败时返回 `errorCode=140006`
- **业务规则**:
  - BR-017: 删除项目后关联 Trace（Trace） 数据将被异步清理

### 3.4. 成员与Privilege管理

#### 3.4.1. FR-017 成员邀请 [优先级: Should]

- **用户故事**: 作为组织管理员，我希望邀请成员加入组织，以便团队协作。
- **主流程**:
  1. 客户端调用成员邀请接口，`UserHandler.InviteMember` 发送邀请 [API/Handlers/UserManagement/UserHandler.cs:44](API/Handlers/UserManagement/UserHandler.cs:44)
- **验收标准**:
  - [ ] AC1: 邀请成功时返回 `errorCode=0`
  - [ ] AC2: 邀请失败时返回 `errorCode=100026`
- **业务规则**:
  - BR-018: OrgAdmin及以上Privilege可邀请成员

#### 3.4.2. FR-018 角色分配与月度配额管理 [优先级: Should]

- **用户故事**: 作为组织所有者，我希望为成员分配角色并管理月度 Agent（Agent） 配额，以便控制资源使用。
- **主流程**:
  1. 客户端调用角色分配接口，`UserHandler.AssignRole` 分配角色 [API/Handlers/UserManagement/UserHandler.cs:50](API/Handlers/UserManagement/UserHandler.cs:50)
  2. 系统通过 `UserHandler` 执行月度 Agent（Agent） 配额扣减与校验 [API/Handlers/UserManagement/UserHandler.cs:52](API/Handlers/UserManagement/UserHandler.cs:52)
- **验收标准**:
  - [ ] AC1: 角色分配成功时返回 `errorCode=0`
  - [ ] AC2: 所有者不能修改自身角色时返回 `errorCode=100039`
  - [ ] AC3: 配额不足时返回 `errorCode=150007`
- **业务规则**:
  - BR-019: User、OrgAdmin、OrgOwner、ProjectAdmin

### 3.5. Payment与订阅

#### 3.5.1. FR-019 下单 [优先级: Must]

- **用户故事**: 作为组织所有者，我希望下单购买产品订阅，以便获得更多 Agent（Agent） 配额。
- **主流程**:
  1. 客户端调用 `POST /api/payment/order`，携带 `Agent（Agent）InsightOrderBody`（含 orgid、productid、productdurationid、paymethod、subpaymethod）[API/Controllers/PaymentManagement/OrderController.cs:48](API/Controllers/PaymentManagement/OrderController.cs:48)
  2. `OrderController.Place` 委托 `OrderHandler.PlaceOrder` 创建订单 [API/Handlers/PaymentManagement/OrderHandler.cs:14](API/Handlers/PaymentManagement/OrderHandler.cs:14)
  3. `OrderHandler` 调用 `PaymentService` 生成Payment参数
- **验收标准**:
  - [ ] AC1: 下单成功时返回 `errorCode=0`，响应包含 `orderno`、`state`、`codeurl`、`qrcode`、`prepayid` 等Payment参数
  - [ ] AC2: Payment宝下单失败时返回 `errorCode=810020`
  - [ ] AC3: 下单接口限流为 1 次/10 秒（`RateLimit(maxRequests: 1, windowSeconds: 10)`）
- **业务规则**:
  - BR-020: paymethod 支持 1=WeChat、2=Alipay；subpaymethod 支持 1=JSAPI、2=Native、3=小程序、11=电脑网站

#### 3.5.2. FR-020 查询订单列表 [优先级: Must]

- **用户故事**: 作为组织所有者，我希望查看订单列表，以便了解订阅购买历史。
- **主流程**:
  1. 客户端调用 `GET /api/payment/order?orgId={orgId}` [API/Controllers/PaymentManagement/OrderController.cs:34](API/Controllers/PaymentManagement/OrderController.cs:34)
  2. `OrderController.Get` 委托 `OrderHandler.GetOrders` 返回订单列表
- **验收标准**:
  - [ ] AC1: 返回 `errorCode=0`，响应包含订单列表，含 `orderno`、`tradeno`、`productname`、`totalamount`、`orderstate`、`paymethod` 字段
  - [ ] AC2: 未携带有效 Token 时返回 `errorCode=100000`
- **业务规则**:
  - BR-021: orderstate 枚举：1=Created、2=Paid、3=Refunded、4=Cancelled、5=Closed、6=Expired

#### 3.5.3. FR-021 查询订单状态 [优先级: Must]

- **用户故事**: 作为组织所有者，我希望根据订单号查询订单Payment状态，以便确认Payment结果。
- **主流程**:
  1. 客户端调用 `GET /api/payment/order/query?orderNo={orderNo}` [API/Controllers/PaymentManagement/OrderController.cs:64](API/Controllers/PaymentManagement/OrderController.cs:64)
  2. `OrderController.Query` 委托 `OrderHandler.QueryOrder` 查询订单状态
- **验收标准**:
  - [ ] AC1: 返回 `errorCode=0`，响应包含 `orderno`、`state`、`tradestate` 字段
  - [ ] AC2: 查询接口限流为 1 次/1 秒（`RateLimit(maxRequests: 1, windowSeconds: 1)`）
- **业务规则**:
  - BR-022: tradestate 枚举：1=NOTPAY、2=SUCCESS、3=REFUND、4=CLOSED、5=REVOKED、6=USERPAYING、7=PAYERROR

#### 3.5.4. FR-022 产品价格转换计算 [优先级: Should]

- **用户故事**: 作为组织所有者，我希望在产品间转换时计算价格差异，以便升级或降级订阅。
- **主流程**:
  1. 客户端调用 `GET /api/payment/order/conversion` [API/Controllers/PaymentManagement/OrderController.cs:79](API/Controllers/PaymentManagement/OrderController.cs:79)
  2. `OrderController.Conversion` 委托 `OrderHandler.CalculateConversion` 执行产品价格转换计算 [API/Handlers/PaymentManagement/OrderHandler.cs:19](API/Handlers/PaymentManagement/OrderHandler.cs:19)
- **验收标准**:
  - [ ] AC1: 返回 `errorCode=0`，响应包含转换后的价格差异和Payment参数
  - [ ] AC2: 未携带有效 Token 时返回 `errorCode=100000`
- **业务规则**:
  - BR-023: 转换计算基于产品时长（`Agent（Agent）InsightProductDuration`）的 quantity 和 discount

#### 3.5.5. FR-023 微信Payment回调 [优先级: Must]

- **用户故事**: 作为系统，我希望接收微信Payment异步通知，以便自动更新订单状态。
- **主流程**:
  1. 微信服务器调用 `POST /api/payment/notify/wechatnotify` [API/Controllers/PaymentManagement/NotifyController.cs:29](API/Controllers/PaymentManagement/NotifyController.cs:29)
  2. `NotifyController.WeChatNotify` 校验请求体非空，空请求抛出 `ApiException` 异常
  3. `NotifyHandler.ExamineWeChatRequest` 验证微信签名 [API/Handlers/PaymentManagement/NotifyHandler.cs:14](API/Handlers/PaymentManagement/NotifyHandler.cs:14)
  4. `NotifyHandler.ProcessWeChatNotify` 处理Payment结果并更新订单状态
- **验收标准**:
  - [ ] AC1: 处理成功时返回微信成功响应 `WXSuccessResult`
  - [ ] AC2: 请求体为空时返回 `errorCode=620014`
  - [ ] AC3: 微信签名验证失败时返回 `errorCode=620002`
  - [ ] AC4: 订单状态更新失败时返回 `errorCode=810026`
- **业务规则**:
  - BR-024: 回调接口为匿名访问（`[AllowAnonymous]`），通过微信签名验证保障安全

#### 3.5.6. FR-024 Payment宝回调 [优先级: Must]

- **用户故事**: 作为系统，我希望接收Payment宝异步通知，以便自动更新订单状态。
- **主流程**:
  1. Payment宝服务器调用 `POST /api/payment/notify/alipaynotify` [API/Controllers/PaymentManagement/NotifyController.cs:57](API/Controllers/PaymentManagement/NotifyController.cs:57)
  2. `NotifyController.AlipayNotify` 校验请求参数非空
  3. `NotifyHandler.ExamineAlipayRequest` 验证Payment宝签名 [API/Handlers/PaymentManagement/NotifyHandler.cs:15](API/Handlers/PaymentManagement/NotifyHandler.cs:15)
  4. `NotifyHandler.ProcessAlipayNotify` 处理Payment结果并更新订单状态
- **验收标准**:
  - [ ] AC1: 处理成功时返回文本 `"success"`
  - [ ] AC2: 处理失败时返回文本 `"fail"`
- **业务规则**:
  - BR-025: 回调接口为匿名访问（`[AllowAnonymous]`），通过Payment宝签名验证保障安全

#### 3.5.7. FR-025 产品列表查询 [优先级: Must]

- **用户故事**: 作为组织所有者，我希望查看产品列表，以便选择适合的订阅方案。
- **主流程**:
  1. 客户端调用 `GET /api/product` [API/Controllers/ProductManagement/ProductController.cs:28](API/Controllers/ProductManagement/ProductController.cs:28)
  2. `ProductController.Get` 委托 `ProductHandler.GetProducts` 返回产品列表
- **验收标准**:
  - [ ] AC1: 返回 `errorCode=0`，响应包含产品列表，含 `id`、`name`、`type`、`price`、`projectlimit`、`headcountlimit`、`agentlimit`、`level` 字段
  - [ ] AC2: 未携带有效 Token 时返回 `errorCode=100000`
- **业务规则**:
  - BR-026: Product type 枚举：0=None、1=Monthly、2=Permanent

#### 3.5.8. FR-026 产品时长列表查询 [优先级: Should]

- **用户故事**: 作为组织所有者，我希望查看产品时长选项，以便选择订阅时长。
- **主流程**:
  1. 客户端调用 `GET /api/product/duration` [API/Controllers/ProductManagement/ProductController.cs:40](API/Controllers/ProductManagement/ProductController.cs:40)
  2. `ProductController.GetDurations` 委托 `ProductHandler.GetProductDurations` 返回时长列表
- **验收标准**:
  - [ ] AC1: 返回 `errorCode=0`，响应包含时长列表，含 `id`、`name`、`quantity`、`discount` 字段
  - [ ] AC2: 未携带有效 Token 时返回 `errorCode=100000`
- **业务规则**:
  - BR-027: 时长 quantity 表示天数，discount 表示折扣率

### 3.6. Trace（Trace） 数据与分析

#### 3.6.1. FR-027 Observations 查询 [优先级: Must]

- **用户故事**: 作为开发者，我希望根据 Trace（Trace） ID 查询 Observations 列表，以便分析 Agent（Agent） 执行细节。
- **主流程**:
  1. 客户端调用 `GET /api/data/metrics/observations?id={traceId}&page={page}&pagesize={pagesize}` [API/Controllers/DataManagement/MetricsController.cs:34](API/Controllers/DataManagement/MetricsController.cs:34)
  2. `MetricsController.GetObservations` 委托 `MetricsHandler.GetObservationsAsync` 查询 Observation 数据 [API/Handlers/DataManagement/MetricsHandler.cs:12](API/Handlers/DataManagement/MetricsHandler.cs:12)
  3. `MetricsHandler` 通过 `ClickHouseClient` 执行查询
- **验收标准**:
  - [ ] AC1: 返回 `errorCode=0`，响应包含 Observation 列表及分页信息
  - [ ] AC2: Trace（Trace） ID 为空时返回 `errorCode=150009`
  - [ ] AC3: 未携带有效 Token 时返回 `errorCode=100000`
- **业务规则**:
  - BR-028: 默认页码为 1，默认每页条数为 10（`Agent（Agent）InsightConst.DefaultPage=1` / `Agent（Agent）InsightConst.DefaultPageSize=10`）

#### 3.6.2. FR-028 Scores 查询 [优先级: Must]

- **用户故事**: 作为开发者，我希望根据 Trace（Trace） ID 查询 Scores 列表，以便评估 Agent（Agent） 执行质量。
- **主流程**:
  1. 客户端调用 `GET /api/data/metrics/scores?id={traceId}&page={page}&pagesize={pagesize}` [API/Controllers/DataManagement/MetricsController.cs:48](API/Controllers/DataManagement/MetricsController.cs:48)
  2. `MetricsController.GetScores` 委托 `MetricsHandler.GetScoresAsync` 查询 Score 数据 [API/Handlers/DataManagement/MetricsHandler.cs:13](API/Handlers/DataManagement/MetricsHandler.cs:13)
- **验收标准**:
  - [ ] AC1: 返回 `errorCode=0`，响应包含 Score 列表及分页信息
  - [ ] AC2: Trace（Trace） ID 为空时返回 `errorCode=150009`
- **业务规则**:
  - BR-029: Score 数据与 Observation 数据关联同一 Trace（Trace） ID

#### 3.6.3. FR-029 Trace（Trace）s 指标查询 [优先级: Must]

- **用户故事**: 作为开发者，我希望根据 Trace（Trace） ID 批量获取指标详情，以便分析 Token 消耗和延迟。
- **主流程**:
  1. 客户端调用 `GET /api/data/metrics/traces?ids={traceIds}` [API/Controllers/DataManagement/MetricsController.cs:64](API/Controllers/DataManagement/MetricsController.cs:64)
  2. `MetricsController.GetTrace（Trace）Metrics` 委托 `MetricsHandler.GetTrace（Trace）Metrics` 查询 Trace（Trace） Metric [API/Handlers/DataManagement/MetricsHandler.cs:14](API/Handlers/DataManagement/MetricsHandler.cs:14)
- **验收标准**:
  - [ ] AC1: 返回 `errorCode=0`，响应包含 Trace（Trace） 指标列表，含 `id`、`inputtokens`、`outputtokens`、`totaltokens`、`inputcost`、`outputcost`、`totalcost`、`latency`、`modelnames` 字段
  - [ ] AC2: Trace（Trace） ID 为空时返回 `errorCode=150009`
  - [ ] AC3: Trace（Trace） ID 数量过多时返回 `errorCode=150011`
- **业务规则**:
  - BR-030: 多个 Trace（Trace） ID 以逗号分隔

#### 3.6.4. FR-030 Trace（Trace） 列表查询 [优先级: Must]

- **用户故事**: 作为开发者，我希望分页查询 Trace（Trace） 列表，以便浏览和分析 Agent（Agent） 执行记录。
- **主流程**:
  1. 客户端调用 `POST /api/data/metrics/traces`，携带查询条件（含 orgid、projectid、id、name、from、to、page、pagesize、orderby、filter）[API/Controllers/DataManagement/MetricsController.cs:81](API/Controllers/DataManagement/MetricsController.cs:81)
  2. `MetricsController.GetTrace（Trace）s` 委托 `MetricsHandler.GetTrace（Trace）s` 执行查询 [API/Handlers/DataManagement/MetricsHandler.cs:15](API/Handlers/DataManagement/MetricsHandler.cs:15)
  3. `MetricsHandler` 通过 `Trace（Trace）FilterBuilder` 构建过滤条件，使用 `ClickHouseClient` 查询 ClickHouse
- **验收标准**:
  - [ ] AC1: 返回 `errorCode=0`，响应包含 Trace（Trace） 列表及分页信息
  - [ ] AC2: 支持按 `timestamp`、`name`、`id` 等多维度过滤和排序
  - [ ] AC3: 未携带有效 Token 时返回 `errorCode=100000`
- **业务规则**:
  - BR-031: 支持 `orderby` 参数，格式为 `字段.排序方向`（如 `timestamp.desc`）
  - BR-032: 支持自定义 `filter` 条件，type 支持 `datetime` 等类型，operator 支持 `>=`、`<=` 等

#### 3.6.5. FR-031 Model 定义查询 [优先级: Should]

- **用户故事**: 作为开发者，我希望查询模型定义列表，以便了解 Token 计费规则。
- **主流程**:
  1. 客户端调用 `GET /api/data/model?keyword={keyword}&projectid={projectid}&includedpredefined={bool}` [API/Controllers/DataManagement/ModelController.cs:28](API/Controllers/DataManagement/ModelController.cs:28)
  2. `ModelController.Get` 委托 `ModelHandler.GetModels` 返回模型定义列表 [API/Handlers/DataManagement/ModelHandler.cs:12](API/Handlers/DataManagement/ModelHandler.cs:12)
- **验收标准**:
  - [ ] AC1: 返回 `errorCode=0`，响应包含模型列表，含 `id`、`modelname`、`matchpattern`、`inputprice`、`outputprice`、`totalprice`、`unit`、`tokenizerconfig` 字段
  - [ ] AC2: projectid 为空且 includedpredefined=false 时返回错误
- **业务规则**:
  - BR-033: `includedpredefined=true` 时同时返回预定义模型（projectid=null 的模型）

### 3.7. Alert管理

#### 3.7.1. FR-032 创建Alert规则 [优先级: Must]

- **用户故事**: 作为开发者，我希望创建Alert规则，以便在 Trace（Trace） 数据异常时及时收到通知。
- **主流程**:
  1. 客户端调用Alert规则创建接口，`AlertHandler.CreateAlert` 创建规则 [API/Handlers/UserManagement/AlertHandler.cs:12](API/Handlers/UserManagement/AlertHandler.cs:12)
- **验收标准**:
  - [ ] AC1: 创建成功时返回 `errorCode=0`
  - [ ] AC2: 未携带有效 Token 时返回 `errorCode=100000`
- **业务规则**:
  - BR-034: Alert规则支持多字段、多操作符条件组合

#### 3.7.2. FR-033 更新Alert规则 [优先级: Should]

- **用户故事**: 作为开发者，我希望更新Alert规则，以便调整Alert条件。
- **主流程**:
  1. 客户端调用Alert规则更新接口，`AlertHandler.UpdateAlert` 更新规则 [API/Handlers/UserManagement/AlertHandler.cs:13](API/Handlers/UserManagement/AlertHandler.cs:13)
- **验收标准**:
  - [ ] AC1: 更新成功时返回 `errorCode=0`
  - [ ] AC2: 未携带有效 Token 时返回 `errorCode=100000`
- **业务规则**:
  - BR-035: 仅规则创建者或组织管理员可更新规则

#### 3.7.3. FR-034 删除Alert规则 [优先级: Must]

- **用户故事**: 作为开发者，我希望删除Alert规则，以便停止不再需要的Alert。
- **主流程**:
  1. 客户端调用Alert规则删除接口，`AlertHandler.DeleteAlert` 删除规则 [API/Handlers/UserManagement/AlertHandler.cs:15](API/Handlers/UserManagement/AlertHandler.cs:15)
- **验收标准**:
  - [ ] AC1: 删除成功时返回 `errorCode=0`
  - [ ] AC2: 未携带有效 Token 时返回 `errorCode=100000`
- **业务规则**:
  - BR-036: 仅规则创建者或组织管理员可删除规则

#### 3.7.4. FR-035 查询Alert规则列表 [优先级: Must]

- **用户故事**: 作为开发者，我希望查看Alert规则列表，以便了解当前AlertConfig。
- **主流程**:
  1. 客户端调用Alert规则列表查询接口，`AlertHandler.GetAlerts` 返回规则列表 [API/Handlers/UserManagement/AlertHandler.cs:14](API/Handlers/UserManagement/AlertHandler.cs:14)
- **验收标准**:
  - [ ] AC1: 返回 `errorCode=0`，响应包含Alert规则列表及分页信息
  - [ ] AC2: 未携带有效 Token 时返回 `errorCode=100000`
- **业务规则**:
  - BR-037: 仅返回当前用户可访问的Alert规则

---

## 4. 非功能需求

Agent（Agent）InsightService 是一个面向 AI Agent（Agent） 的可Observation性与管理平台，核心功能围绕 **Trace（Trace） 数据采集与分析**、**用户与组织管理**、**Payment与订阅**、**Agent（Agent） Config与报告** 四大领域展开。系统由 C# 后端 API (`API/`) 和 Python Agent（Agent） Service (`Agent（Agent）s/`) 构成 Monorepo（单体仓库）。为确保平台在生产环境中的稳定运行、数据安全与持续演进能力，NFR。

本章所有非功能需求均采用 `NFR-{维度}-{序号}` 编号格式，涵盖性能、可用性、安全、可扩展性、可维护性、兼容性及本地化七个维度。每项需求包含明确的指标、目标值及验证方式，作为系统设计、开发实现与验收测试的量化依据。

### 4.1. 性能 (NFR-P)

性能需求确保系统在预期负载下具备稳定的响应能力与吞吐量。Agent（Agent）InsightService 的核心性能瓶颈集中在 Trace（Trace） 数据查询链路（API → MetricsHandler → ClickHouse）与 AI Agent（Agent） 流式响应链路（Python Agent（Agent） Service → SSE 推送）。

| 编号 | Metric | 目标值 | 验证方式 |
|------|------|--------|----------|
| NFR-P-001 | ClickHouse Trace（Trace） 查询 P95 延迟 | < 2s | 压测 `MetricsController.GetTrace（Trace）s` 端点（`API/Controllers/DataManagement/MetricsController.cs:64`），以 1000 并发请求持续 10 分钟，统计 P95 延迟 |
| NFR-P-002 | Observation 列表查询 P95 延迟 | < 1s | 压测 `MetricsController.GetObservations` 端点（`API/Controllers/DataManagement/MetricsController.cs:34`），以 500 并发请求，统计 P95 延迟 |
| NFR-P-003 | SSE 流式响应首个 token 延迟 | < 500ms | 调用 `Agent（Agent）s/server.py` 的 `POST /api/agent/insight` 端点，从请求发出到收到首个 SSE 数据帧的时间间隔 |
| NFR-P-004 | Payment下单接口吞吐量 | ≥ 100 TPS | 压测 `OrderController.Place` 端点（`API/Controllers/PaymentManagement/OrderController.cs`），统计每秒成功处理的下单请求数 |
| NFR-P-005 | 订单状态查询接口 P95 延迟 | < 500ms | 压测 `OrderController.Query` 端点（`API/Controllers/PaymentManagement/OrderController.cs`），以 200 并发请求，统计 P95 延迟 |
| NFR-P-006 | ClickHouse 连接池最大连接数 | 50 | 验证Config `ClickHouseOptions.ConnectionPool` 中 `MaxConnections=50` 参数生效，连接数达到上限时新请求排队等待而非报错 |
| NFR-P-007 | PostgreSQL 连接池最大连接数 | 200 | 验证Config `PostgresOptions.ConnectionPool` 中 `MaxConnections=200` 参数生效，连接数达到上限时新请求排队等待而非报错 |
| NFR-P-008 | 批量 Trace（Trace） 指标查询（单次 ≥ 100 个 Trace（Trace） ID）P95 延迟 | < 3s | 压测 `MetricsController.GetTrace（Trace）s` 端点（`API/Controllers/DataManagement/MetricsController.cs:64`），传入 100 个逗号分隔的 Trace（Trace） ID，统计 P95 延迟 |

性能指标说明：

- **NFR-P-001** 是系统最核心的性能指标。Trace（Trace） 查询通过 `MetricsHandler.GetTrace（Trace）s` 构建包含时间范围/过滤条件的 ClickHouse SQL 并执行查询（`API/Handlers/DataManagement/MetricsHandler.cs:16`），查询效率直接取决于 ClickHouse 表结构设计与 SQL 优化程度。压测环境需预置不少于 1000 万条 Trace（Trace） 记录。
- **NFR-P-003** 针对 AI Agent（Agent） 流式响应场景。Python Agent（Agent） 服务通过 `stream_response` 方法实现 SSE 流式输出（`Agent（Agent）s/server.py`），首个 token 延迟直接影响用户感知的响应速度。该指标在模型推理耗时之外，额外包含网络传输与框架处理开销。
- **NFR-P-006 与 NFR-P-007** 的验证方式为：在压测过程中监控连接池使用率，确认连接数达到上限时系统不抛出连接异常，而是通过连接池排队机制等待空闲连接释放。连接池参数来自Config文件 `ClickHouseOptions.ConnectionPool` 与 `PostgresOptions.ConnectionPool`。

### 4.2. 可用性 (NFR-A)

可用性需求确保系统在异常场景下具备自我恢复能力，关键业务操作不因瞬时故障而丢失数据或中断流程。

| 编号 | Metric | 目标值 | 验证方式 |
|------|------|--------|----------|
| NFR-A-001 | Payment回调处理最大重试次数 | 3 次 | 代码审查确认 `PaymentTransactionSaveHandler.MaxRetryCount = 3`（`API/Notifications/PaymentTransactionSaveHandler.cs:8`）；故障注入测试：模拟数据库写入失败，确认重试 3 次后放弃并记录错误日志 |
| NFR-A-002 | Payment回调重试退避策略 | 1s / 3s / 5s 递增 | 代码审查确认 `RetryDelays` 数组定义（`API/Notifications/PaymentTransactionSaveHandler.cs:10-14`）；测试中记录每次重试的时间间隔 |
| NFR-A-003 | 微信通知处理最大重试次数 | 3 次 | 代码审查确认微信通知处理链路复用 `PaymentTransactionSaveHandler` 的重试机制；故障注入测试确认微信Payment回调在临时故障下不丢失 |
| NFR-A-004 | Payment回调请求签名验证 | 100% 非法请求被拒绝 | 测试向 `NotifyController.WeChatNotify` 端点（`API/Controllers/PaymentManagement/NotifyController.cs`）发送伪造签名请求，确认返回错误且不进入业务处理流程 |
| NFR-A-005 | 系统健康检查端点可用性 | 100% 返回 200 | 调用 `HealthController` 健康检查端点（`API/Controllers/ToolsManagement/HealthController.cs:20`），确认在系统正常运行期间始终返回 HTTP 200 |
| NFR-A-006 | 数据库连接超时保护 | 30s（ClickHouse）/ 60s（PostgreSQL） | 验证Config `ClickHouseOptions.ConnectionPool` 中 `ConnectTimeout=30` 与 `PostgresOptions.ConnectionPool` 中 `Timeout=60` 参数生效；模拟数据库不可达场景，确认请求在超时时间内返回错误而非无限挂起 |

可用性设计说明：

- **NFR-A-001 与 NFR-A-002** 针对Payment回调场景。Payment回调是异步通知机制，网络抖动或数据库瞬时故障可能导致处理失败。`PaymentTransactionSaveHandler` 实现了基于 MediatR 通知模式的重试机制：捕获异常后根据 `RetryCount` 判断是否重试，重试延迟按 1 秒、3 秒、5 秒递增（`API/Notifications/PaymentTransactionSaveHandler.cs:9-14`）。重试次数达到 `MaxRetryCount = 3` 后记录错误日志并放弃，避免无限重试造成消息堆积。
- **NFR-A-004** 确保Payment回调接口的安全性。`NotifyController.WeChatNotify` 在解析请求体后首先调用 `ExamineWeChatRequest` 验证微信签名（`API/Controllers/PaymentManagement/NotifyController.cs`），签名验证失败的请求直接抛出 `InvalidSignatureException` 异常，不进入后续业务处理。
- **NFR-A-006** 防止数据库故障导致请求线程无限阻塞。连接字符串中显式Config了连接超时与命令超时参数，确保在数据库不可达时请求能快速失败并返回错误响应，避免线程池耗尽。

### 4.3. 安全 (NFR-S)

安全需求覆盖身份认证、数据加密、访问控制与防刷机制，确保系统数据资产的机密性、完整性与可用性。

| 编号 | Metric | 目标值 | 验证方式 |
|------|------|--------|----------|
| NFR-S-001 | JWT 签名算法 | HS256 | 代码审查确认 JWT Config使用 HS256 对称签名算法；测试解析生成的 Token，确认 `alg` 头为 `HS256` |
| NFR-S-002 | JWT 过期时间 | 12 小时 | 代码审查确认 JWT Config中 `Expires = 12h`；测试在 Token 过期后访问受保护接口，确认返回 401 未授权 |
| NFR-S-003 | API Key 认证 | 支持 Basic Auth 方式访问 Trace（Trace） 上报接口 | 测试使用 `publicKey:secretKey` 以 Basic Auth 方式调用 Trace（Trace） 数据上报接口，确认认证通过；使用错误密钥确认返回 401 |
| NFR-S-004 | 密码存储加密 | 使用 BCrypt 哈希存储 | 代码审查确认密码字段使用 BCrypt 哈希算法存储；测试创建用户后检查数据库密码字段，确认非明文 |
| NFR-S-005 | Captcha重发间隔 | 60 秒 | 代码审查确认 `CaptchaSetting.ResendInterval = 60`；测试在 60 秒内重复请求发送Captcha，确认第二次请求被拒绝 |
| NFR-S-006 | Captcha有效期 | 300 秒 | 代码审查确认 `CaptchaSetting.ExpireSeconds = 300`；测试在Captcha过期后提交，确认校验失败 |
| NFR-S-007 | Captcha长度 | 6 位数字 | 代码审查确认 `CaptchaSetting.Length = 6`、`CaptchaSetting.CodeType = 6`、`CaptchaSetting.VerifyCodeType = 6`；测试验证生成的Captcha符合长度要求 |
| NFR-S-008 | 下单接口限流 | 1 次 / 10 秒 | 代码审查确认 `OrderController.Place` 端点标注 `[RateLimit(maxRequests: 1, windowSeconds: 10)]`（`API/Controllers/PaymentManagement/OrderController.cs`）；测试在 10 秒内连续调用下单接口，确认第二次请求被限流 |
| NFR-S-009 | 订单查询接口限流 | 1 次 / 1 秒 | 代码审查确认 `OrderController.Query` 端点标注 `[RateLimit(maxRequests: 1, windowSeconds: 1)]`（`API/Controllers/PaymentManagement/OrderController.cs`）；测试在 1 秒内连续调用查询接口，确认第二次请求被限流 |
| NFR-S-010 | 组织Privilege校验 | 未授权访问返回 403 | 测试使用非组织成员身份访问组织资源接口，确认返回 `ForbiddenException` 错误（errorCode=130009）；测试使用非项目成员身份访问项目资源接口，确认返回 `ForbiddenException` 错误（errorCode=140008） |

安全机制说明：

- **NFR-S-001 与 NFR-S-002** 定义 JWT 认证的核心参数。JWT 使用 HS256 对称签名算法，过期时间设置为 12 小时，平衡安全性与用户体验。过期后客户端需重新登录获取新的 Token。
- **NFR-S-003** 针对程序化数据上报场景。开发者通过 `UserHandler.CreateApiKey` 创建 API Key（`API/Handlers/UserManagement/UserHandler.cs:55`），获得 `publicKey` 和 `secretKey` 后，以 Basic Auth 方式（`publicKey:secretKey`）调用 Trace（Trace） 数据上报接口。`Agent（Agent）InsightTransformProvider` 负责在 API 网关层解析并校验 Basic Auth 凭据（`API/System/Handlers/Agent（Agent）InsightTransformProvider.cs:18`）。
- **NFR-S-005 至 NFR-S-007** 定义Captcha防刷与有效性策略。Captcha服务由 `CaptchaHandler` 实现（`API/Handlers/UserManagement/CaptchaHandler.cs:15-18`），通过 60 秒重发间隔防止短信轰炸，通过 300 秒有效期确保Captcha的时效性。
- **NFR-S-008 与 NFR-S-009** 针对Payment接口的限流保护。下单与订单查询接口均标注了 `[RateLimit]` 特性，防止恶意用户高频调用造成Payment服务压力或数据泄露风险。
- **NFR-S-010** RBAC有效执行。`ApiHandlerBase` 提供 `RequireOrgAdmin()`、`RequireOrgOwner()`、`RequireProjectAdmin()` 等Privilege校验方法（`API/Handlers/ApiHandlerBase.cs:22-25`），未授权访问将返回对应的错误码。

### 4.4. 可扩展性 (NFR-SC)

可扩展性需求确保系统在数据规模增长、用户数量增加及功能模块扩展时，能够通过水平或垂直扩展维持性能指标。

| 编号 | Metric | 目标值 | 验证方式 |
|------|------|--------|----------|
| NFR-SC-001 | ClickHouse 数据存储水平扩展 | 支持分片与副本 | 验证 ClickHouse 集群Config支持多分片多副本部署；测试向集群写入 1 亿条 Trace（Trace） 记录，确认查询性能不随数据量线性下降 |
| NFR-SC-002 | PostgreSQL 连接池弹性 | MinPoolSize=10, MaxPoolSize=200 | 验证Config `PostgresOptions.ConnectionPool` 中连接池参数生效；压测确认连接数从 10 动态增长至 200 时系统无连接异常 |
| NFR-SC-003 | 消息队列异步解耦 | Trace（Trace） 数据上报通过消息队列异步处理 | 代码审查确认 `Agent（Agent）InsightTransformProvider` 依赖 `BullMqService` 进行异步消息处理（`API/System/Handlers/Agent（Agent）InsightTransformProvider.cs:7`）；测试确认 Trace（Trace） 数据上报接口在消息队列积压时仍能快速响应 |
| NFR-SC-004 | 无状态 API 水平扩展 | API 服务支持多实例部署 | 部署 3 个 API 实例，通过负载均衡分发请求；测试确认任意实例处理请求的结果一致，且Session状态可通过 Redis 共享（技术栈包含 `StackExchange.Redis`） |
| NFR-SC-005 | 项目删除异步处理 | 项目删除通过消息队列异步执行 | 代码审查确认 `BullMqService.EnqueueProjectDeleteAsync` 方法存在；测试确认删除项目接口立即返回，实际删除操作在后台异步执行 |

扩展性设计说明：

- **NFR-SC-001** 针对 Trace（Trace） 数据的高速增长。ClickHouse 作为列式存储数据库，天然支持分布式集群部署。Shard将数据分散到多台机器，Replica提供数据冗余与查询负载均衡。系统需确保 Trace（Trace） 数据模型与写入链路支持分布式表。
- **NFR-SC-002** 确保数据库连接池能够根据负载动态调整。连接池初始大小为 10，在并发请求增加时逐步扩展至 200，避免因连接数不足造成请求排队。
- **NFR-SC-003** 通过消息队列实现 Trace（Trace） 数据上报与存储的解耦。`Agent（Agent）InsightTransformProvider` 接收 API 请求后，通过 `BullMqService` 将数据写入消息队列（`API/System/Handlers/Agent（Agent）InsightTransformProvider.cs:7`），后台消费者异步写入 ClickHouse。该架构使数据上报接口的响应时间不受 ClickHouse 写入性能影响。
- **NFR-SC-004** 确保 API 层无状态化，支持水平扩展。API 实例不保存本地Session状态，用户认证信息通过 JWT 无状态校验，分布式缓存通过 Redis 实现（技术栈包含 `StackExchange.Redis`）。

### 4.5. 可维护性 (NFR-M)

可维护性需求确保系统具备完善的Observation能力、日志记录与Config管理机制，降低运维与排障成本。

| 编号 | Metric | 目标值 | 验证方式 |
|------|------|--------|----------|
| NFR-M-001 | 请求审计日志覆盖率 | 100% 的 API 请求记录审计日志 | 代码审查确认 `RequestAuditFilter` 实现 `IActionFilter` 接口（`API/System/Handlers/RequestAuditFilter.cs`）；测试调用任意 API 后确认审计日志包含 UserId、RequestPath、Controller、Method、StatusCode 等字段 |
| NFR-M-002 | 请求耗时记录 | 所有 API 请求记录处理耗时 | 代码审查确认 `RequestAuditFilter` 使用 `Stopwatch` 记录请求处理耗时（`API/System/Handlers/RequestAuditFilter.cs`）；测试确认日志中包含耗时字段 |
| NFR-M-003 | Config外部化 | 敏感Config通过环境变量注入 | 验证Config文件使用 `${DB_PASSWORD}`、`${AES_KEY}` 等占位符引用环境变量；测试确认未设置环境变量时服务启动失败并提示缺失Config |
| NFR-M-004 | Config扫描目录 | 支持多Config目录扫描 | 验证Config项 `ConfigurationScanDirectories = ['Configurations', 'Resources']` 生效；测试在 `Configurations` 目录新增Config文件后服务自动加载 |
| NFR-M-005 | Payment回调失败日志 | 重试耗尽后记录错误日志 | 代码审查确认 `PaymentTransactionSaveHandler` 在重试 3 次后调用 `Log.Error` 记录失败日志（`API/Notifications/PaymentTransactionSaveHandler.cs:37`）；故障注入测试确认错误日志包含重试次数与通知类型 |
| NFR-M-006 | Payment回调重试日志 | 每次重试记录信息日志 | 代码审查确认 `PaymentTransactionSaveHandler` 在每次重试前调用 `Log.Information` 记录重试信息（`API/Notifications/PaymentTransactionSaveHandler.cs:31`）；测试确认日志包含重试次数与最大重试次数 |

可维护性设计说明：

- **NFR-M-001 与 NFR-M-002** 通过 `RequestAuditFilter` 实现全量请求审计。该过滤器在 Action 执行前后分别记录请求上下文与处理耗时（`API/System/Handlers/RequestAuditFilter.cs`），审计字段包括 UserId、RequestPath、Controller、Method、StatusCode 等，为问题Trace与安全审计提供完整数据。
- **NFR-M-003** 确保敏感Config（数据库密码、AES 密钥、第三方 API 密钥等）不硬编码在Config文件中，而是通过环境变量注入。Config文件中的 `${DB_PASSWORD}` 占位符在服务启动时由Config解析器替换为环境变量值。
- **NFR-M-004** 支持多Config目录扫描，便于按模块拆分Config文件。`ConfigurationScanDirectories` Config项指定了 `Configurations` 与 `Resources` 两个扫描目录。
- **NFR-M-005 与 NFR-M-006** 确保Payment回调处理过程可Trace。每次重试均记录信息日志（包含通知类型、当前重试次数、最大重试次数），重试耗尽后记录错误日志，便于运维人员及时发现并处理Payment回调异常。

### 4.6. 兼容性 (NFR-C)

兼容性需求确保系统在不同客户端环境、第三方服务及数据格式下具备良好的互操作性。

| 编号 | Metric | 目标值 | 验证方式 |
|------|------|--------|----------|
| NFR-C-001 | 微信Payment方式兼容 | 支持 JSAPI / Native / 小程序 | 代码审查确认 `PaymentService` 实现微信Payment三种子Payment方式（`API/Common/Services/PaymentService.cs:30-36`）；测试分别使用三种方式下单，确认均能生成有效Payment参数 |
| NFR-C-002 | Payment宝Payment兼容 | 支持Payment宝电脑网站Payment | 代码审查确认 `PaymentService` 实现Payment宝Payment（`API/Common/Services/PaymentService.cs:22-27`）；测试使用Payment宝电脑网站Payment方式下单，确认能生成有效Payment表单 |
| NFR-C-003 | OpenAI 兼容 API | 支持 OpenAI Chat Completions 协议 | 测试使用 OpenAI SDK 调用 `Agent（Agent）s/server.py` 的 `POST /api/agent/insight` 端点，确认请求与响应格式兼容 OpenAI 协议 |
| NFR-C-004 | 流式响应兼容 | 支持 SSE（Server-Sent Events） | 测试调用 `Agent（Agent）s/server.py` 的流式接口，确认响应头包含 `Content-Type: text/event-stream`，且数据以 SSE 格式推送 |
| NFR-C-005 | 微信小程序登录兼容 | 支持微信小程序授权登录 | 代码审查确认 `UserHandler.CreateUser(MiniUserBody body)` 方法支持微信小程序登录（`API/Handlers/UserManagement/UserHandler.cs:31`）；测试使用微信小程序授权码登录，确认能创建或绑定用户 |
| NFR-C-006 | Payment回调格式兼容 | 支持微信与Payment宝异步通知格式 | 代码审查确认 `NotifyHandler` 分别处理微信与Payment宝回调（`API/Handlers/PaymentManagement/NotifyHandler.cs:12-15`）；测试分别发送微信与Payment宝格式的异步通知，确认均能正确解析与处理 |

兼容性设计说明：

- **NFR-C-001 与 NFR-C-002** 确保Payment渠道的多样性。`PaymentService` 同时支持微信Payment（JSAPI、Native、小程序）与Payment宝Payment（电脑网站），覆盖 PC 端与移动端不同场景。Payment方式通过 `paymethod` 与 `subpaymethod` 字段区分（`API/Controllers/PaymentManagement/OrderController.cs`）。
- **NFR-C-003 与 NFR-C-004** 确保 AI Agent（Agent） 服务的开放兼容性。Python Agent（Agent） Service（`Agent（Agent）s/server.py`）实现了 OpenAI 兼容的 Chat Completions API，开发者可以使用标准 OpenAI SDK 直接接入，无需学习私有协议。流式响应通过 SSE 实现，支持增量输出。
- **NFR-C-005** 支持微信小程序生态。用户可以通过微信小程序授权登录，`UserHandler.CreateUser` 接收 `MiniUserBody` 参数（`API/Handlers/UserManagement/UserHandler.cs:31`），实现小程序用户的注册与绑定。
- **NFR-C-006** 确保Payment回调的渠道兼容。`NotifyHandler` 分别处理微信与Payment宝的异步通知，包括签名验证、业务处理与响应返回（`API/Handlers/PaymentManagement/NotifyHandler.cs:12-15`）。

### 4.7. 本地化 (NFR-L)

本地化需求确保系统支持多语言、多时区及本地化格式，满足不同地区用户的使用需求。

| 编号 | Metric | 目标值 | 验证方式 |
|------|------|--------|----------|
| NFR-L-001 | 多语言资源管理 | 支持通过 JSON 资源文件管理多语言 | 技术栈包含 `My.Extensions.Localization.Json`；验证 `Resources` 目录下存在多语言 JSON 资源文件，且语言切换后界面文案正确更新 |
| NFR-L-002 | 中文语言支持 | 系统界面与通知支持简体中文 | 测试将系统语言设置为 `zh-CN`，确认界面文案、邮件通知、短信通知均使用简体中文 |
| NFR-L-003 | 时间格式本地化 | 支持多时区时间显示 | 测试在不同时区环境下访问 Trace（Trace） 列表，确认时间字段按本地时区正确转换显示 |
| NFR-L-004 | 货币格式本地化 | Payment金额按本地货币格式展示 | 测试在不同区域设置下查看订单金额，确认货币符号与格式符合当地习惯 |
| NFR-L-005 | Config扫描目录包含本地化资源 | `Resources` 目录纳入Config扫描范围 | 验证Config项 `ConfigurationScanDirectories = ['Configurations', 'Resources']` 生效；测试在 `Resources` 目录新增语言资源文件后服务自动加载 |

本地化设计说明：

- **NFR-L-001 与 NFR-L-002** 确保系统的多语言能力。技术栈中的 `My.Extensions.Localization.Json` 提供了基于 JSON 资源文件的本地化支持。`Resources` 目录被纳入Config扫描范围（`ConfigurationScanDirectories = ['Configurations', 'Resources']`），新增语言资源文件后服务可自动加载。
- **NFR-L-003** 针对 Trace（Trace） 数据的时间显示。系统存储的时间戳为 UTC 格式，前端展示时根据用户所在时区进行转换，确保不同地区的用户看到正确的本地时间。
- **NFR-L-004** 针对Payment金额的展示格式。订单金额在数据库中存储为数值类型，前端展示时根据用户区域设置格式化货币符号、千分位分隔符及小数位数。
- **NFR-L-005** 确保本地化资源与系统Config统一管理。`Resources` 目录与 `Configurations` 目录并列纳入Config扫描范围，使语言资源文件与Config文件遵循相同的加载与覆盖机制。

---

## 5. 接口需求

Agent（Agent）InsightService 是一个面向 AI Agent（Agent） 的可Observation性与管理平台，核心功能围绕 Trace（Trace） 数据采集与分析、用户与组织管理、Payment与订阅、Agent（Agent） Config与报告四大领域展开。系统由 C# 后端 API（`API/`）和 Python Agent（Agent） Service（`Agent（Agent）s/`）构成 Monorepo（单体仓库）。本章节定义 Agent（Agent）InsightService 与内部组件、外部服务之间的接口需求，涵盖内部接口、外部接口以及接口鉴权与协议规范三部分，确保各系统边界之间的数据交换具备明确的契约、安全机制与可追溯性。

### 5.1. 内部接口

内部接口描述 Agent（Agent）InsightService 后端 API 内部各组件之间的交互方式，包括 API 网关转发、消息队列、数据库连接、缓存与查询客户端。

#### 5.1.1. API 网关转发（Yarp.ReverseProxy）

Agent（Agent）InsightService 使用 Yarp.ReverseProxy 作为 API 网关，负责将外部 HTTP 请求路由转发至后端服务。网关层同时承担认证转换与请求过滤职责，`Agent（Agent）InsightTransformProvider` 在网关管道中执行 Basic Auth/JWT 认证、API Key 校验、限流及路由转发逻辑 [API/System/Handlers/Agent（Agent）InsightTransformProvider.cs]。该转换器通过 `Agent（Agent）InsightTransformLogic` 解析 Authorization 头中的 Basic Auth 凭据，并将请求上下文传递给下游Handler [API/Handlers/UserManagement/UserHandler.cs]。

网关转发的目标路由由各 Controller 上的 `[Route]` 特性定义，例如用户接口注册于 `api/user` 前缀下 [API/Controllers/UserManagement/UserController.cs]，Payment回调接口注册于 `api/payment/notify` 前缀下 [API/Controllers/PaymentManagement/NotifyController.cs]，微信消息接口注册于 `api/tools/wechat` 前缀下 [API/Controllers/ToolsManagement/WeChat/WeChatController.cs]。网关层根据这些路由规则将请求分发至对应的 Handler。

#### 5.1.2. BullMqService

Agent（Agent）InsightService 使用 BullMqService 作为基于 Redis 的消息队列服务，实现 Trace（Trace） 数据摄入、项目删除等异步任务的解耦。`Agent（Agent）InsightTransformProvider` 通过调用 `BullMqService` 的 `EnqueueTrace（Trace）IngestionAsync` 方法将 Trace（Trace） 数据写入队列，由后台消费者异步处理 [API/System/Handlers/Agent（Agent）InsightTransformProvider.cs]。队列类型通过 `QueueType` 枚举区分，包括：

| 枚举值 | 用途 |
|--------|------|
| `Audit` | 审计日志队列 |
| `ExceptionRecord` | 异常记录队列 |
| `UsageTracking` | 用量跟踪队列 |
| `PerformanceRecord` | 性能记录队列 |

队列消费完成后通过 `AcknowledgeTrace（Trace）IngestionAsync` 确认消息处理成功，确保消息不丢失 [API/System/Handlers/Agent（Agent）InsightTransformProvider.cs]。

#### 5.1.3. Npgsql

Agent（Agent）InsightService 使用 Npgsql 作为 PostgreSQL 数据库的 .NET 提供程序，通过 SqlSugar ORM 框架进行数据访问。系统Config了三组数据库连接字符串，分别对应用户库、数据与跟踪库：

| Config键 | 用途 |
|--------|------|
| `ConnectionStrings:UserDb` | 用户与组织管理数据 |
| `ConnectionStrings:DataDb` | Trace（Trace） 与指标数据 |
| `ConnectionStrings:Trace（Trace）Db` | 跟踪与审计数据 |

`ApiHandlerBase` 通过 `[FromKeyedServices(Agent（Agent）InsightConst.KeyedService_UserDb)]` 注入用户库的 `ISqlSugarClient`，通过 `[FromKeyedServices(Agent（Agent）InsightConst.KeyedService_DataDb)]` 注入数据库的 `ISqlSugarClient` [API/Handlers/ApiHandlerBase.cs]。例如 `UserHandler` 构造函数同时接收两个数据库客户端，分别用于用户管理和数据查询 [API/Handlers/UserManagement/UserHandler.cs]。

#### 5.1.4. 缓存（StackExchange.Redis）

Agent（Agent）InsightService 使用 StackExchange.Redis 作为 Redis 客户端，提供分布式缓存能力。缓存用于用户Session、Captcha、微信 AccessToken 等短期数据的存储与读取。`UserHandler` 通过 `IMemoryCache` 进行进程内缓存，同时通过 `user.UpdateCache` 方法将用户信息同步至 Redis 缓存 [API/Handlers/UserManagement/UserHandler.cs]。微信服务通过 Redis 缓存 AccessToken，避免频繁调用微信 API 获取Token [API/Common/Services/WeChatService.cs]。

#### 5.1.5. ClickHouse 查询客户端

Agent（Agent）InsightService 使用 ClickHouse 作为 Trace（Trace） 数据的列式存储与分析引擎。`MetricsHandler` 通过 `ClickHouseClient` 执行 Trace（Trace）、Observation、Score 等指标的查询，支持多维度过滤、排序与分页 [API/Handlers/DataManagement/MetricsHandler.cs]。连接字符串Config为 `ConnectionStrings:ClickHouse`，包含主机、端口、用户名、密码、数据库名及连接池参数（`MinPoolSize=10`, `MaxPoolSize=50`, `ConnectionIdleTimeout=30`, `ConnectionLifetime=60`）。

### 5.2. 外部接口

外部接口描述 Agent（Agent）InsightService 与第三方服务之间的交互，包括Payment、登录、消息推送、短信与 AI Agent（Agent） Service。

#### 5.2.1. 微信Payment API

Agent（Agent）InsightService 通过 `PaymentService` 对接微信Payment API，支持 JSAPI、Native、MiniProgram 三种Payment模式 [API/Common/Services/PaymentService.cs]。`PaymentService.GetWeChatJSAPIResponse` 方法构建 JSAPI Payment请求参数，`PaymentService.GetWeChatNativeResponse` 构建 Native 扫码Payment参数，`PaymentService.GetWeChatMiniProgramResponse` 构建小程序Payment参数。Payment金额以分为单位（`AmountInCents = 100`），订单号通过 `CreateOrderNo` 生成，格式为 `yyyyMMddHHmmssfff` + 7 位随机数 [API/Common/Services/PaymentService.cs]。

Payment回调由 `NotifyController` 的 `WeChatNotify` 端点接收，路径为 `POST /api/payment/notify/wechatnotify` [API/Controllers/PaymentManagement/NotifyController.cs]。回调处理流程包括：读取请求体 → 调用 `ExamineWeChatRequest` 验证签名 → 反序列化 `WeChatNotify` → 调用 `ProcessWeChatNotify` 更新订单状态 → 返回微信成功响应。验证失败时返回 `WXFailResult("FAIL")`。

#### 5.2.2. Payment宝Payment API

Agent（Agent）InsightService 通过 `PaymentService` 对接Payment宝即时到账 API [API/Common/Services/PaymentService.cs]。`PaymentService.GetAlipayInstantTrade` 方法构建Payment宝即时到账请求参数，使用 AlipaySDK.NET.Standard 作为Payment宝 SDK。Payment回调由 `NotifyController` 的 `AlipayNotify` 端点接收，路径为 `POST /api/payment/notify/alipaynotify` [API/Controllers/PaymentManagement/NotifyController.cs]。回调处理调用 `ProcessAlipayNotify` 验证异步通知并更新订单状态，成功返回 `"success"`，失败返回 `"fail"`。

#### 5.2.3. 微信小程序登录与消息推送

Agent（Agent）InsightService 通过 `WeChatService` 对接微信小程序登录与公众号消息推送 [API/Common/Services/WeChatService.cs]。`LoginByWeChatMiniProgram` 方法使用小程序登录凭证 code 换取用户 OpenId 与 Session（Session）Key，实现微信小程序登录绑定 [API/Common/Services/IWeChatService.cs]。`GetBasicAccessToken` 与 `GetAuthorizedAccessToken` 分别获取基础 AccessToken 与用户授权 AccessToken。

微信消息推送由 `WeChatController` 接收，路径为 `GET/POST /api/tools/wechat` [API/Controllers/ToolsManagement/WeChat/WeChatController.cs]。`GET` 请求用于微信服务器签名验证，`POST` 请求接收微信推送的消息与事件，由 `WeChatHandler.ProcessMessage` 处理并返回 XML 响应 [API/Handlers/ToolsManagement/WeChat/WeChatHandler.cs]。

#### 5.2.4. SMS Service

Agent（Agent）InsightService 支持通过 Aliyun 或 TencentCloud 发送短信Captcha与Alert通知。`CaptchaHandler` 负责Captcha的生成与校验，支持图形Captcha、SMS Captcha与邮件Captcha三种类型 [API/Handlers/UserManagement/CaptchaHandler.cs]。短信Captcha长度为 6 位（`CaptchaSetting.SmsCodeLength = 6`），有效期 300 秒（`CaptchaSetting.SmsCodeExpireSeconds = 300`），重发间隔 60 秒（`CaptchaSetting.SmsResendIntervalSeconds = 60`）。

Alert通知通过 `SMSAlertHandler` 发送短信，当Alert规则触发时通知用户 [API/Notifications/SMSAlertHandler.cs]。

#### 5.2.5. OpenAI 兼容 API

Agent（Agent）InsightService 的 Python Agent（Agent） 服务提供 OpenAI 兼容的 Chat Completions API，端点为 `POST /api/agent/insight` [Agent（Agent）s/server.py]。该接口支持流式 SSE 响应（`stream=true`），逐 token 推送生成结果。`InsightOrchestrator` 负责多 Agent（Agent） 路由，根据用户请求分发至不同的 Agent（Agent） 处理 [Agent（Agent）s/server.py]。Session（Session） 通过 `MemoryManager` 持久化，支持服务器重启后恢复 [Agent（Agent）s/server.py]。

### 5.3. 接口鉴权与协议规范

本节定义 Agent（Agent）InsightService 各类接口的鉴权方式、数据格式与通用协议约定。

#### 5.3.1. 鉴权方式

Agent（Agent）InsightService 支持三种鉴权方式，根据接口类型与调用方角色选择适用的机制：

| 鉴权方式 | 适用接口 | 实现位置 |
|----------|----------|----------|
| JWT Bearer Token（HS256） | 用户接口（登录后访问） | `JWTSettings.ExpiredTime = 43200`（12 小时过期） |
| Basic Auth（publicKey:secretKey） | API Key 接口（程序化数据上报） | `Agent（Agent）InsightTransformLogic.ValidateApiKey` |
| 签名验证 | 微信回调接口 | `WeChatService.ExamineSignature` |

**JWT Bearer Token**：用户登录成功后，系统返回 JWT Token，算法为 HS256，有效期 12 小时（`JWTSettings.ExpiredTime = 43200`）。客户端在后续请求的 `Authorization` 头中携带 `Bearer <token>`。用户登录接口支持多种登录方式（`LoginType` 枚举），包括密码登录（1）、短信登录（2）、微信登录（3）、小程序登录（4）与 API Key 登录（5）[API/Controllers/UserManagement/UserController.cs]。

**Basic Auth**：API Key 接口使用 Basic Auth 方式，客户端在 `Authorization` 头中携带 `Basic base64(publicKey:secretKey)`。`UserHandler.Login` 方法在 `LoginType == LoginType.APIKey` 时解析 Basic Auth 凭据，通过 `Agent（Agent）InsightTransformLogic.ExtractApiKey` 提取 publicKey 与 secretKey，并在数据库中查询 `ApiKeyRecord` 进行校验 [API/Handlers/UserManagement/UserHandler.cs]。API Key 创建接口返回 publicKey 与 secretKey 对，用于程序化数据上报。

**微信签名验证**：微信回调接口（`GET/POST /api/tools/wechat`）使用微信签名验证机制。`WeChatService.ExamineSignature` 方法将 `token`、`timestamp`、`nonce` 三个参数按字典序排序后拼接，进行 SHA1 哈希，与 `signature` 参数比对 [API/Common/Services/WeChatService.cs]。验证失败时抛出 `ExceptionCodes.WeChatSignatureInvalid` 异常。

#### 5.3.2. 数据格式

所有 API 统一返回 JSON 格式，响应结构遵循 `ApiResponse<T>` 包装：

```json
{
  "errorCode": 0,
  "data": { }
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `errorCode` | int | 0=成功，非 0=具体错误码 |
| `data` | object | 业务数据负载 |

时间格式统一使用 ISO 8601 UTC 标准（如 `2024-01-15T08:30:00Z`），字符集统一使用 UTF-8。Base URL 推导自Config `AllowedHosts = *`，允许任意 Host 访问。

#### 5.3.3. 错误码规范

接口错误码从代码中的枚举常量提取，主要错误码如下：

| errorCode | 常量名 | 说明 |
|-----------|--------|------|
| 0 | - | 成功 |
| 100031 | `ExceptionCodes.ApiKeyNotFound` | API Key 不存在 |
| 100032 | `ExceptionCodes.ApiKeyCreateFailed` | 创建 API Key 失败 |
| 100033 | `ExceptionCodes.ApiKeyDeleteFailed` | 删除 API Key 失败 |
| 100036 | `ExceptionCodes.ApiKeySecretNotFound` | API Key Secret 不存在 |
| 100038 | `ExceptionCodes.ApiKeyInvalid` | 无效的 API Key |
| 620004 | `ExceptionCodes.WeChatUserInfoFailed` | 获取微信基础用户信息失败 |
| 150004 | `ExceptionCodes.Agent（Agent）SettingNotConfigured` | Agent（Agent） 设置未Config |
| 150007 | `ExceptionCodes.Agent（Agent）QuotaExceeded` | Agent（Agent） 配额超限 |
| 150020 | `ExceptionCodes.Agent（Agent）RateUpdateFailed` | 更新 Agent（Agent） 费率失败 |
| 150021 | `ExceptionCodes.Agent（Agent）Session（Session）NotFound` | Agent（Agent） Session（Session） 不存在 |
| 150022 | `ExceptionCodes.Agent（Agent）ConfigNotFound` | Agent（Agent） Config不存在 |
| 150023 | `ExceptionCodes.Agent（Agent）ReportTemplateNotFound` | Agent（Agent） 报告模板不存在 |
| 150024 | `ExceptionCodes.Agent（Agent）ReportTemplateNameEmpty` | Agent（Agent） 报告模板名称为空 |

#### 5.3.4. 通用约定

1. **接口版本治理**：当前 API 未使用显式版本号，路由前缀（如 `api/user`、`api/payment`）作为隐式版本标识。
2. **分页约定**：列表查询接口支持分页参数，默认分页大小与最大分页大小由各 Handler 内部定义。
3. **幂等性**：Payment回调接口具备幂等性，重复通知不会导致订单状态重复更新。
4. **超时约定**：数据库连接超时 30 秒，命令超时 60 秒（`CommandTimeout` Config）；PostgreSQL 连接超时 60 秒（`ConnectionTimeout` Config）。
5. **字符集**：所有请求与响应统一使用 UTF-8 编码，XML 响应（微信消息）同样使用 UTF-8。

---

## 6. 接口详情（按 Controller 分组）

Agent（Agent）InsightService 是一个面向 AI Agent（Agent） 的可Observation性与管理平台，核心功能围绕 Trace（Trace） 数据采集与分析、用户与组织管理、Payment与订阅、Agent（Agent） Config与报告四大领域展开。系统由 C# 后端 API（`API/`）和 Python Agent（Agent） Service（`Agent（Agent）s/`）构成 Monorepo（单体仓库）。本章按 Controller 分组详细描述所有 HTTP 端点的接口定义，包括请求参数、响应格式、错误码及示例。所有端点均以 `/api` 为前缀，数据格式为 JSON（微信回调接口除外），字符集为 UTF-8。

### 6.1. Agent（Agent）ConfigController

Agent（Agent） Config管理接口，负责 Agent（Agent） 运行参数的查询、创建与删除。对应 Handler 为 `Agent（Agent）ConfigHandler`（`API/Handlers/Agent（Agent）Management/Agent（Agent）ConfigHandler.cs:12-14`），所有端点均需 JWT 认证。

#### 6.1.1. 查询 Agent（Agent） Config列表（GET /api/agent/config）

**鉴权**：JWT

**描述**：分页查询当前用户可见的 Agent（Agent） Config列表，支持按关键词过滤。

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| keyword | string | 否 | Config名称关键词，模糊匹配 |
| page | int | 否 | 页码，默认 1 |
| pageSize | int | 否 | 每页数量，默认 10 |

**响应格式**：

| 字段 | 类型 | 说明 |
|------|------|------|
| errorCode | int | 0=成功，非 0=具体错误 |
| data | array | Agent（Agent） Config列表 |
| totalCount | int | 总记录数 |

**错误码**：

| errorCode | message | 说明 |
|-----------|---------|------|
| 0 | success | 成功 |
| 100000 | Unauthorized | 未认证或 Token 无效 |

**请求示例**：

```http
GET /api/agent/config?keyword=default&page=1&pageSize=10
Authorization: Bearer <JWT>
```

**响应示例**：

```json
{
  "errorCode": 0,
  "data": [
    {
      "id": "cfg_001",
      "name": "默认Config",
      "content": "{...}",
      "updatedAt": "2024-01-01T00:00:00Z"
    }
  ],
  "totalCount": 1
}
```

#### 6.1.2. 删除 Agent（Agent） Config（DELETE /api/agent/config）

**鉴权**：JWT

**描述**：根据Config ID 删除指定 Agent（Agent） Config。

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | string | 是 | Config ID |

**响应格式**：

| 字段 | 类型 | 说明 |
|------|------|------|
| errorCode | int | 0=成功，非 0=具体错误 |
| data | object | 空对象 |

**错误码**：

| errorCode | message | 说明 |
|-----------|---------|------|
| 0 | success | 成功 |
| 100000 | Unauthorized | 未认证或 Token 无效 |

**请求示例**：

```http
DELETE /api/agent/config?id=cfg_001
Authorization: Bearer <JWT>
```

**响应示例**：

```json
{
  "errorCode": 0,
  "data": {}
}
```

#### 6.1.3. 创建或更新 Agent（Agent） Config（POST /api/agent/config）

**鉴权**：JWT

**描述**：创建新的 Agent（Agent） Config或更新已有Config。请求体包含Config ID（可选，更新时必填）、名称和内容。

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | string | 否 | Config ID，更新时必填 |
| name | string | 是 | Config名称 |
| content | object | 是 | Config内容（JSON 对象） |

**响应格式**：

| 字段 | 类型 | 说明 |
|------|------|------|
| errorCode | int | 0=成功，非 0=具体错误 |
| data | object | 创建或更新后的Config对象 |

**错误码**：

| errorCode | message | 说明 |
|-----------|---------|------|
| 0 | success | 成功 |
| 100000 | Unauthorized | 未认证或 Token 无效 |
| 150008 | ConfigNameDuplicate | Config名称重复 |

**请求示例**：

```json
{
  "name": "生产Config",
  "content": {
    "model": "gpt-4",
    "temperature": 0.7
  }
}
```

**响应示例**：

```json
{
  "errorCode": 0,
  "data": {
    "id": "cfg_002",
    "name": "生产Config",
    "content": {
      "model": "gpt-4",
      "temperature": 0.7
    }
  }
}
```

### 6.2. Agent（Agent）ReportController

Agent（Agent） 报告模板管理接口，负责报告模板的查询、删除与创建/更新。对应 Handler 为 `Agent（Agent）ReportHandler`（`API/Handlers/Agent（Agent）Management/Agent（Agent）ReportHandler.cs:12-14`），所有端点均需 JWT 认证。

#### 6.2.1. 查询报告模板列表（GET /api/agent/report）

**鉴权**：JWT

**描述**：分页查询报告模板列表。

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| page | int | 否 | 页码，默认 1 |
| pageSize | int | 否 | 每页数量，默认 10 |

**响应格式**：

| 字段 | 类型 | 说明 |
|------|------|------|
| errorCode | int | 0=成功，非 0=具体错误 |
| data | array | 报告模板列表 |
| totalCount | int | 总记录数 |

**错误码**：

| errorCode | message | 说明 |
|-----------|---------|------|
| 0 | success | 成功 |
| 100000 | Unauthorized | 未认证或 Token 无效 |

**请求示例**：

```http
GET /api/agent/report?page=1&pageSize=10
Authorization: Bearer <JWT>
```

**响应示例**：

```json
{
  "errorCode": 0,
  "data": [
    {
      "id": "rpt_001",
      "name": "周报模板",
      "content": "{...}",
      "updatedAt": "2024-01-01T00:00:00Z"
    }
  ],
  "totalCount": 1
}
```

#### 6.2.2. 删除报告模板（DELETE /api/agent/report）

**鉴权**：JWT

**描述**：根据模板 ID 删除指定报告模板。

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | string | 是 | 模板 ID |

**响应格式**：

| 字段 | 类型 | 说明 |
|------|------|------|
| errorCode | int | 0=成功，非 0=具体错误 |
| data | object | 空对象 |

**错误码**：

| errorCode | message | 说明 |
|-----------|---------|------|
| 0 | success | 成功 |
| 100000 | Unauthorized | 未认证或 Token 无效 |

**请求示例**：

```http
DELETE /api/agent/report?id=rpt_001
Authorization: Bearer <JWT>
```

**响应示例**：

```json
{
  "errorCode": 0,
  "data": {}
}
```

#### 6.2.3. 创建或更新报告模板（POST /api/agent/report）

**鉴权**：JWT

**描述**：创建新的报告模板或更新已有模板。

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | string | 否 | 模板 ID，更新时必填 |
| name | string | 是 | 模板名称 |
| content | object | 是 | 模板内容（JSON 对象） |

**响应格式**：

| 字段 | 类型 | 说明 |
|------|------|------|
| errorCode | int | 0=成功，非 0=具体错误 |
| data | object | 创建或更新后的模板对象 |

**错误码**：

| errorCode | message | 说明 |
|-----------|---------|------|
| 0 | success | 成功 |
| 100000 | Unauthorized | 未认证或 Token 无效 |

**请求示例**：

```json
{
  "name": "月度报告模板",
  "content": {
    "sections": ["summary", "metrics"]
  }
}
```

**响应示例**：

```json
{
  "errorCode": 0,
  "data": {
    "id": "rpt_002",
    "name": "月度报告模板",
    "content": {
      "sections": ["summary", "metrics"]
    }
  }
}
```

### 6.3. Agent（Agent）Session（Session）Controller

Agent（Agent） Session（Session） 管理接口，负责Session的查询、删除与创建。对应 Handler 为 `Agent（Agent）Session（Session）Handler`（`API/Handlers/Agent（Agent）Management/Agent（Agent）Session（Session）Handler.cs:12-14`），所有端点均需 JWT 认证。

#### 6.3.1. 查询 Session（Session） 列表（GET /api/agent/session）

**鉴权**：JWT

**描述**：分页查询当前用户的 Agent（Agent） Session列表。

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| page | int | 否 | 页码，默认 1 |
| pageSize | int | 否 | 每页数量，默认 10 |

**响应格式**：

| 字段 | 类型 | 说明 |
|------|------|------|
| errorCode | int | 0=成功，非 0=具体错误 |
| data | array | Session（Session） 列表 |
| totalCount | int | 总记录数 |

**错误码**：

| errorCode | message | 说明 |
|-----------|---------|------|
| 0 | success | 成功 |
| 100000 | Unauthorized | 未认证或 Token 无效 |

**请求示例**：

```http
GET /api/agent/session?page=1&pageSize=10
Authorization: Bearer <JWT>
```

**响应示例**：

```json
{
  "errorCode": 0,
  "data": [
    {
      "id": "sess_001",
      "title": "对话 1",
      "createdAt": "2024-01-01T00:00:00Z"
    }
  ],
  "totalCount": 1
}
```

#### 6.3.2. 删除 Session（Session）（DELETE /api/agent/session）

**鉴权**：JWT

**描述**：根据 Session（Session） ID 删除指定Session。

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | string | 是 | Session（Session） ID |

**响应格式**：

| 字段 | 类型 | 说明 |
|------|------|------|
| errorCode | int | 0=成功，非 0=具体错误 |
| data | object | 空对象 |

**错误码**：

| errorCode | message | 说明 |
|-----------|---------|------|
| 0 | success | 成功 |
| 100000 | Unauthorized | 未认证或 Token 无效 |

**请求示例**：

```http
DELETE /api/agent/session?id=sess_001
Authorization: Bearer <JWT>
```

**响应示例**：

```json
{
  "errorCode": 0,
  "data": {}
}
```

#### 6.3.3. 创建 Session（Session）（POST /api/agent/session）

**鉴权**：JWT

**描述**：创建新的 Agent（Agent） Session。

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| title | string | 否 | Session标题 |
| agentId | string | 是 | Agent（Agent） ID |

**响应格式**：

| 字段 | 类型 | 说明 |
|------|------|------|
| errorCode | int | 0=成功，非 0=具体错误 |
| data | object | 新创建的 Session（Session） 对象 |

**错误码**：

| errorCode | message | 说明 |
|-----------|---------|------|
| 0 | success | 成功 |
| 100000 | Unauthorized | 未认证或 Token 无效 |

**请求示例**：

```json
{
  "title": "新对话",
  "agentId": "agent_001"
}
```

**响应示例**：

```json
{
  "errorCode": 0,
  "data": {
    "id": "sess_002",
    "title": "新对话",
    "agentId": "agent_001",
    "createdAt": "2024-01-02T00:00:00Z"
  }
}
```

### 6.4. MetricsController

数据指标查询接口，负责 Trace（Trace）、Observation、Score 的查询。对应 Handler 为 `MetricsHandler`（`API/Handlers/DataManagement/MetricsHandler.cs:14-16`），数据存储于 ClickHouse。所有端点均需 JWT 认证。

#### 6.4.1. 查询 Observations（GET /api/data/metrics/observations）

**鉴权**：JWT

**描述**：根据 Trace（Trace） ID 获取 Observations 列表，支持分页。路由定义于 `API/Controllers/DataManagement/MetricsController.cs:34`。

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | string | 是 | Trace（Trace） ID |
| page | int | 否 | 页码，默认 1 |
| pagesize | int | 否 | 每页条数，默认 10 |

**响应格式**：

| 字段 | 类型 | 说明 |
|------|------|------|
| errorCode | int | 0=成功，非 0=具体错误 |
| data | array | Observation 列表 |
| totalCount | int | 总记录数 |

**错误码**：

| errorCode | message | 说明 |
|-----------|---------|------|
| 0 | success | 成功 |
| 100000 | Unauthorized | 未认证或 Token 无效 |
| 150018 | Trace（Trace）IdEmpty | Trace（Trace） ID 为空 |

**请求示例**：

```http
GET /api/data/metrics/observations?id=trace_001&page=1&pagesize=10
Authorization: Bearer <JWT>
```

**响应示例**：

```json
{
  "errorCode": 0,
  "data": [
    {
      "id": "obs_001",
      "traceId": "trace_001",
      "type": "span",
      "timestamp": "2024-01-01T00:00:00Z"
    }
  ],
  "totalCount": 1
}
```

#### 6.4.2. 查询 Scores（GET /api/data/metrics/scores）

**鉴权**：JWT

**描述**：根据 Trace（Trace） ID 获取 Scores 列表，支持分页。路由定义于 `API/Controllers/DataManagement/MetricsController.cs:50`。

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | string | 是 | Trace（Trace） ID |
| page | int | 否 | 页码，默认 1 |
| pagesize | int | 否 | 每页条数，默认 10 |

**响应格式**：

| 字段 | 类型 | 说明 |
|------|------|------|
| errorCode | int | 0=成功，非 0=具体错误 |
| data | array | Score 列表 |
| totalCount | int | 总记录数 |

**错误码**：

| errorCode | message | 说明 |
|-----------|---------|------|
| 0 | success | 成功 |
| 100000 | Unauthorized | 未认证或 Token 无效 |
| 150018 | Trace（Trace）IdEmpty | Trace（Trace） ID 为空 |

**请求示例**：

```http
GET /api/data/metrics/scores?id=trace_001&page=1&pagesize=10
Authorization: Bearer <JWT>
```

**响应示例**：

```json
{
  "errorCode": 0,
  "data": [
    {
      "id": "score_001",
      "traceId": "trace_001",
      "name": "accuracy",
      "value": 0.95
    }
  ],
  "totalCount": 1
}
```

#### 6.4.3. 批量查询 Trace（Trace） Metric（POST /api/data/metrics/traces）

**鉴权**：JWT

**描述**：根据 Trace（Trace） ID 列表批量获取指标详情（Token 数、费用、延迟等）。路由定义于 `API/Controllers/DataManagement/MetricsController.cs:64`。请求体为 Trace（Trace） ID 列表。

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| ids | array | 是 | Trace（Trace） ID 列表，如 `["trace_001", "trace_002"]` |

**响应格式**：

| 字段 | 类型 | 说明 |
|------|------|------|
| errorCode | int | 0=成功，非 0=具体错误 |
| data | array | Trace（Trace） 指标详情列表 |

**错误码**：

| errorCode | message | 说明 |
|-----------|---------|------|
| 0 | success | 成功 |
| 100000 | Unauthorized | 未认证或 Token 无效 |
| 150009 | Trace（Trace）IdsEmpty | Trace（Trace） ID 列表为空 |
| 150011 | Trace（Trace）IdsTooMany | Trace（Trace） ID 数量超出限制 |

**请求示例**：

```http
POST /api/data/metrics/traces
Authorization: Bearer <JWT>
Content-Type: application/json

{
  "ids": ["trace_001", "trace_002"]
}
```

**响应示例**：

```json
{
  "errorCode": 0,
  "data": [
    {
      "id": "trace_001",
      "inputTokens": 100,
      "outputTokens": 50,
      "totalTokens": 150,
      "inputCost": 0.001,
      "outputCost": 0.002,
      "totalCost": 0.003,
      "latency": 250,
      "modelNames": ["gpt-4"]
    }
  ]
}
```

#### 6.4.4. 分页查询 Trace（Trace） 列表（POST /api/data/metrics/traces/query）

**鉴权**：JWT

**描述**：分页查询 Trace（Trace） 列表，支持按 ID、名称、时间范围及自定义条件过滤。路由定义于 `API/Controllers/DataManagement/MetricsController.cs:125`。请求体中的 `ids` 与 `filter` 二者必填其一。

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| orgid | string | 否 | Org ID |
| projectid | string | 否 | Project ID |
| id | string | 否 | Trace（Trace） ID |
| name | string | 否 | Trace（Trace） 名称 |
| from | string | 否 | 开始时间 |
| to | string | 否 | 结束时间 |
| page | int | 否 | 页码，默认 1 |
| pagesize | int | 否 | 每页条数，默认 50 |
| orderby | string | 否 | 排序方式，如 `timestamp.desc` |
| ids | array | 否 | Trace（Trace） ID 列表，与 `filter` 二选一 |
| filter | array | 否 | 自定义过滤条件数组，每项包含 type/column/operator/value |

**响应格式**：

| 字段 | 类型 | 说明 |
|------|------|------|
| errorCode | int | 0=成功，非 0=具体错误 |
| data | array | Trace（Trace） 列表 |
| totalCount | int | 总记录数 |

**错误码**：

| errorCode | message | 说明 |
|-----------|---------|------|
| 0 | success | 成功 |
| 100000 | Unauthorized | 未认证或 Token 无效 |
| 150012 | FilterTypeInvalid | 过滤条件类型无效 |
| 150013 | FilterColumnInvalid | 过滤列无效 |
| 150014 | FilterOperatorInvalid | 过滤操作符无效 |
| 150015 | FilterValueInvalid | 过滤值无效 |

**请求示例**：

```json
{
  "orgid": "org_001",
  "projectid": "proj_001",
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
    }
  ]
}
```

**响应示例**：

```json
{
  "errorCode": 0,
  "data": [
    {
      "id": "trace_001",
      "name": "用户查询",
      "timestamp": "2024-01-15T10:30:00Z",
      "duration": 250
    }
  ],
  "totalCount": 1
}
```

### 6.5. ModelController

模型定义查询接口，负责模型列表的查询。对应 Handler 为 `ModelHandler`（`API/Handlers/DataManagement/ModelHandler.cs:12`），所有端点均需 JWT 认证。

#### 6.5.1. 获取模型列表（GET /api/data/model）

**鉴权**：JWT

**描述**：分页查询模型定义列表，支持按关键词、Project ID 过滤，并可选择是否包含预定义模型。路由定义于 `API/Controllers/DataManagement/ModelController.cs:34`。

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| keyword | string | 否 | 关键词，按模型名称过滤 |
| projectid | string | 否 | Project ID，配合 includedpredefined 使用 |
| includedpredefined | bool | 否 | 是否包含预定义模型，默认 false |
| orderby | string | 否 | 排序方式，默认为 `-updatedat` |
| page | int | 否 | 页码，默认 1 |
| pageSize | int | 否 | 每页数量，默认 10 |

**响应格式**：

| 字段 | 类型 | 说明 |
|------|------|------|
| errorCode | int | 0=成功，非 0=具体错误 |
| data | array | 模型定义列表 |
| totalCount | int | 总记录数 |

**错误码**：

| errorCode | message | 说明 |
|-----------|---------|------|
| 0 | success | 成功 |
| 100000 | Unauthorized | 未认证或 Token 无效 |

**请求示例**：

```http
GET /api/data/model?keyword=gpt&projectid=proj_001&includedpredefined=true&page=1&pageSize=10
Authorization: Bearer <JWT>
```

**响应示例**：

```json
{
  "errorCode": 0,
  "data": [
    {
      "id": "model_001",
      "name": "gpt-4",
      "type": "predefined",
      "createdAt": "2024-01-01T00:00:00Z"
    }
  ],
  "totalCount": 1
}
```

### 6.6. NotifyController

Payment回调通知接口，负责接收微信Payment与Payment宝的异步通知。对应 Handler 为 `NotifyHandler`（`API/Handlers/PaymentManagement/NotifyHandler.cs:12-15`），本组端点无需 JWT 认证。

#### 6.6.1. 微信Payment回调（POST /api/payment/notify/wechatnotify）

**鉴权**：无（微信服务器回调）

**描述**：接收微信Payment异步通知，验证签名后更新订单状态。路由定义于 `API/Controllers/PaymentManagement/NotifyController.cs:34`。处理流程为：读取 HTTP 请求 → `ProcessWeChatNotify` 验证并更新订单状态 → 返回微信要求的 XML 格式响应。

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| body | string (XML) | 是 | 微信通知 XML 内容 |

**响应格式**：

| 字段 | 类型 | 说明 |
|------|------|------|
| return_code | string | SUCCESS 或 FAIL |
| return_msg | string | 返回信息 |

**错误码**：

| errorCode | message | 说明 |
|-----------|---------|------|
| 620014 | ForgedWeChatRequest | 伪造的微信请求 |
| 810010 | InvalidWeChatNotification | 无效的微信通知 |
| 810016 | WeChatTransactionEmpty | 微信交易为空 |
| 810017 | InvalidWeChatTransactionId | 无效的微信交易号 |

**请求示例**：

```xml
<xml>
  <return_code>SUCCESS</return_code>
  <out_trade_no>ORDER20240101001</out_trade_no>
  <transaction_id>wx123456789</transaction_id>
  <total_fee>9900</total_fee>
</xml>
```

**响应示例**：

```xml
<xml>
  <return_code>SUCCESS</return_code>
  <return_msg>OK</return_msg>
</xml>
```

#### 6.6.2. Payment宝异步通知（POST /api/payment/notify/alipaynotify）

**鉴权**：无（Payment宝服务器回调）

**描述**：接收Payment宝异步通知，验证后更新订单状态。路由定义于 `API/Controllers/PaymentManagement/NotifyController.cs:57`。处理流程为：读取 HTTP 请求 → `ProcessAlipayNotify` 验证并更新订单状态 → 返回 `success` 或 `fail`。

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| body | string (form) | 是 | Payment宝通知表单内容 |

**响应格式**：

| 字段 | 类型 | 说明 |
|------|------|------|
| 响应体 | string | `success` 或 `fail` |

**错误码**：

| errorCode | message | 说明 |
|-----------|---------|------|
| 810002 | AlipayConfigMissing | Payment宝Config缺失 |

**请求示例**：

```http
POST /api/payment/notify/alipaynotify
Content-Type: application/x-www-form-urlencoded

out_trade_no=ORDER20240101001&trade_no=ALIPAY123456789&total_amount=99.00&trade_status=TRADE_SUCCESS
```

**响应示例**：

```
success
```

### 6.7. OrderController

订单管理接口，负责订单的查询、创建、状态查询与价格转换计算。对应 Handler 为 `OrderHandler`（`API/Handlers/PaymentManagement/OrderHandler.cs:12-17`），所有端点均需 JWT 认证。

#### 6.7.1. 获取订单列表（GET /api/payment/order）

**鉴权**：JWT

**描述**：分页查询指定组织的订单列表。路由定义于 `API/Controllers/PaymentManagement/OrderController.cs:34`。

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| orgId | string | 是 | Org ID |
| page | int | 否 | 页码，默认 1 |
| pageSize | int | 否 | 每页数量，默认 10 |

**响应格式**：

| 字段 | 类型 | 说明 |
|------|------|------|
| errorCode | int | 0=成功，非 0=具体错误 |
| data | array | 订单列表 |
| totalCount | int | 总记录数 |

**错误码**：

| errorCode | message | 说明 |
|-----------|---------|------|
| 0 | success | 成功 |
| 100000 | Unauthorized | 未认证或 Token 无效 |

**请求示例**：

```http
GET /api/payment/order?orgId=org_001&page=1&pageSize=10
Authorization: Bearer <JWT>
```

**响应示例**：

```json
{
  "errorCode": 0,
  "data": [
    {
      "orderno": "ORD20240101001",
      "tradeno": "wx123456789",
      "orgid": "org_001",
      "productid": "prod_001",
      "productname": "专业版",
      "price": 99.0,
      "totalamount": 99.0,
      "orderstate": 2,
      "paymethod": 1
    }
  ],
  "totalCount": 1
}
```

#### 6.7.2. 下单（POST /api/payment/order）

**鉴权**：JWT

**描述**：创建新订单，先下单再Payment。路由定义于 `API/Controllers/PaymentManagement/OrderController.cs:48`。该端点带有 `[RateLimit(maxRequests: 1, windowSeconds: 10)]` 限流特性。

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| orgid | string | 是 | Org ID |
| productid | string | 是 | Product ID |
| productdurationid | string | 是 | 产品时长 ID |
| paymethod | int | 是 | Payment方式：1=WeChat，2=Alipay |
| subpaymethod | int | 是 | 子Payment方式：1=JSAPI，2=Native，3=小程序，11=电脑网站 |

**响应格式**：

| 字段 | 类型 | 说明 |
|------|------|------|
| errorCode | int | 0=成功，非 0=具体错误 |
| data | object | 下单结果，包含订单号、Payment链接、二维码等 |

**错误码**：

| errorCode | message | 说明 |
|-----------|---------|------|
| 0 | success | 成功 |
| 100000 | Unauthorized | 未认证或 Token 无效 |
| 150007 | Agent（Agent）QuotaExceeded | Agent（Agent） 配额超限 |
| 810001 | WeChatPayConfigMissing | 微信PaymentConfig缺失 |
| 810002 | AlipayConfigMissing | Payment宝Config缺失 |

**请求示例**：

```json
{
  "orgid": "org_001",
  "productid": "prod_001",
  "productdurationid": "dur_001",
  "paymethod": 1,
  "subpaymethod": 2
}
```

**响应示例**：

```json
{
  "errorCode": 0,
  "data": {
    "orderno": "ORD20240101002",
    "state": 1,
    "codeurl": "https://weixin.qq.com/wxpay/pay.php",
    "qrcode": "data:image/png;base64,...",
    "prepayid": "wx123456789",
    "appid": "wxappid123",
    "timestamp": "1700000000",
    "noncestr": "abc123",
    "package": "prepay_id=wx123456789",
    "signtype": "RSA",
    "paysign": "signature"
  }
}
```

#### 6.7.3. 查询订单状态（GET /api/payment/order/query）

**鉴权**：JWT

**描述**：根据订单号查询订单Payment状态。路由定义于 `API/Controllers/PaymentManagement/OrderController.cs:64`。该端点带有 `[RateLimit(maxRequests: 1, windowSeconds: 1)]` 限流特性。

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| orderNo | string | 是 | 订单号 |

**响应格式**：

| 字段 | 类型 | 说明 |
|------|------|------|
| errorCode | int | 0=成功，非 0=具体错误 |
| data | object | 订单状态信息 |

**错误码**：

| errorCode | message | 说明 |
|-----------|---------|------|
| 0 | success | 成功 |
| 100000 | Unauthorized | 未认证或 Token 无效 |

**请求示例**：

```http
GET /api/payment/order/query?orderNo=ORD20240101001
Authorization: Bearer <JWT>
```

**响应示例**：

```json
{
  "errorCode": 0,
  "data": {
    "orderno": "ORD20240101001",
    "state": 2,
    "tradeno": "wx123456789"
  }
}
```

#### 6.7.4. 产品价格转换计算（GET /api/payment/order/conversion）

**鉴权**：JWT

**描述**：计算产品价格转换（如月付转年付的折扣计算）。路由定义于 `API/Controllers/PaymentManagement/OrderController.cs:79`，由 `OrderHandler` 中的产品转换计算方法处理（`API/Handlers/PaymentManagement/OrderHandler.cs:19`）。

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| productid | string | 是 | Product ID |
| fromDurationId | string | 是 | 原时长 ID |
| toDurationId | string | 是 | 目标时长 ID |

**响应格式**：

| 字段 | 类型 | 说明 |
|------|------|------|
| errorCode | int | 0=成功，非 0=具体错误 |
| data | object | 转换计算结果 |

**错误码**：

| errorCode | message | 说明 |
|-----------|---------|------|
| 0 | success | 成功 |
| 100000 | Unauthorized | 未认证或 Token 无效 |

**请求示例**：

```http
GET /api/payment/order/conversion?productid=prod_001&fromDurationId=dur_001&toDurationId=dur_002
Authorization: Bearer <JWT>
```

**响应示例**：

```json
{
  "errorCode": 0,
  "data": {
    "originalAmount": 99.0,
    "convertedAmount": 89.1,
    "discount": 0.9
  }
}
```

### 6.8. ProductController

产品信息查询接口，负责产品列表与产品时长列表的查询。对应 Handler 为 `ProductHandler`，所有端点均需 JWT 认证。

#### 6.8.1. 获取产品列表（GET /api/product）

**鉴权**：JWT

**描述**：获取所有可购买的产品列表。路由定义于 `API/Controllers/ProductManagement/ProductController.cs:24`。

**请求参数**：

无

**响应格式**：

| 字段 | 类型 | 说明 |
|------|------|------|
| errorCode | int | 0=成功，非 0=具体错误 |
| data | array | 产品列表 |

**错误码**：

| errorCode | message | 说明 |
|-----------|---------|------|
| 0 | success | 成功 |
| 100000 | Unauthorized | 未认证或 Token 无效 |

**请求示例**：

```http
GET /api/product
Authorization: Bearer <JWT>
```

**响应示例**：

```json
{
  "errorCode": 0,
  "data": [
    {
      "id": "prod_001",
      "name": "专业版",
      "type": 1,
      "price": 99.0,
      "monthlyrate": 100,
      "projectlimit": 5,
      "headcountlimit": 10,
      "orglimit": 3,
      "agentlimit": 10,
      "level": 1
    }
  ]
}
```

#### 6.8.2. 获取产品时长列表（GET /api/product/duration）

**鉴权**：JWT

**描述**：获取所有产品时长选项。路由定义于 `API/Controllers/ProductManagement/ProductController.cs:38`。

**请求参数**：

无

**响应格式**：

| 字段 | 类型 | 说明 |
|------|------|------|
| errorCode | int | 0=成功，非 0=具体错误 |
| data | array

---

## 7. 数据需求

Agent（Agent）InsightService 是一个面向 AI Agent（Agent） 的可Observation性与管理平台，核心功能围绕 **Trace（Trace） 数据采集与分析**、**用户与组织管理**、**Payment与订阅**、**Agent（Agent） Config与报告** 四大领域展开。系统由 C# 后端 API (`API/`) 和 Python Agent（Agent） Service (`Agent（Agent）s/`) 构成 Monorepo（单体仓库）。本章节定义系统的数据模型、数据存储方案以及核心数据流，为后续功能设计提供数据层面的约束与依据。

### 7.1. 数据模型

系统数据实体分布在 `Entities/`（实体定义层，纯数据模型）与 `Models/`（数据传输模型层）两个子项目中，按业务领域可划分为以下几组核心实体：

**用户与组织域**

| 实体 | 所属领域 | 说明 |
|------|---------|------|
| User | 用户管理 | 平台用户，支持注册/登录/登出、微信小程序绑定、密码重置 [API/Handlers/UserManagement/UserHandler.cs:30-42] |
| Organization | 组织管理 | 组织实体，支持 CRUD（增删改查） 操作，是Privilege控制与配额管理的核心载体 [API/Handlers/UserManagement/OrganizationHandler.cs:12-16] |
| Project | 项目管理 | 隶属于组织的项目实体，Trace（Trace） 数据按项目维度隔离 [API/Handlers/UserManagement/ProjectHandler.cs:12-16] |
| ApiKey | API 认证 | 开发者用于程序化上报 Trace（Trace） 数据的凭证，创建后返回 publicKey 和 secretKey [API/Handlers/UserManagement/UserHandler.cs:55-58] |

**Trace（Trace） 数据与分析域**

| 实体 | 所属领域 | 说明 |
|------|---------|------|
| Trace（Trace）Metrics | 数据管理 | Trace（Trace） 核心指标实体，包含 token 消耗、费用、延迟、模型名称等字段 [API/Controllers/DataManagement/MetricsController.cs:64-70] |
| Observation | 数据管理 | Trace（Trace） 下的Observation项，按开始时间排序，支持分页查询 [API/Handlers/DataManagement/MetricsHandler.cs:12] |
| Score | 数据管理 | Trace（Trace） 下的Score项，按创建时间排序，支持分页查询 [API/Handlers/DataManagement/MetricsHandler.cs:13] |
| ModelDefinition | 模型管理 | 模型定义实体，包含模型名称、匹配模式、价格Config等 [API/Handlers/DataManagement/ModelHandler.cs:12] |
| Alert | Alert管理 | Alert规则实体，支持多字段/多操作符条件评估 [API/Handlers/UserManagement/AlertHandler.cs:12-15] |
| AlertRecord | Alert记录 | Alert触发后的记录实体，支持查询与已读标记 [API/Handlers/UserManagement/AlertHandler.cs:16-17] |

**Payment与订阅域**

| 实体 | 所属领域 | 说明 |
|------|---------|------|
| Order | Payment管理 | 订单实体，包含订单号、交易号、产品信息、金额、Payment方式、订单状态等 [API/Controllers/PaymentManagement/OrderController.cs:34-40] |
| Product | 产品管理 | 产品实体，通过 `GET /api/product` 查询 [API/Controllers/ProductManagement/ProductController.cs:26] |
| ProductDuration | 产品时长 | 产品时长Config实体，通过 `GET /api/product/duration` 查询 [API/Controllers/ProductManagement/ProductController.cs:38] |

**Agent（Agent） Config与工具域**

| 实体 | 所属领域 | 说明 |
|------|---------|------|
| Agent（Agent）Config | Agent（Agent） 管理 | 用户级 Agent（Agent） Config，JSON、默认报告模板 ID [API/Controllers/Agent（Agent）Management/Agent（Agent）ConfigController.cs:28-34] |
| Agent（Agent）ReportTemplate | Agent（Agent） 报告 | 报告模板实体，支持 CRUD（增删改查） [API/Controllers/Agent（Agent）Management/Agent（Agent）ReportController.cs:35-40] |
| Agent（Agent）Session（Session） | Agent（Agent） Session | Agent（Agent） Session实体，支持持久化与恢复 [API/Controllers/Agent（Agent）Management/Agent（Agent）Session（Session）Controller.cs:33-38] |
| Bulletin | Bulletin管理 | Bulletin实体，支持 CRUD（增删改查）/审批/状态变更 [API/Handlers/ToolsManagement/BulletinHandler.cs:12-18] |
| WeChatMessage | 微信消息 | 微信消息实体，处理微信消息与事件 [API/Handlers/ToolsManagement/WeChat/WeChatHandler.cs:12-14] |

**实体路由规则**：新增 Model 的路由规则为：`agentinsight_` 前缀的表路由到 `default` 库（即 `UserDbConnection` 对应的 PostgreSQL 数据库），其他表路由到 `data` 库（即 `DataDbConnection` 对应的 PostgreSQL 数据库）[Admin/Agent（Agent）s.md]。

### 7.2. 数据存储

系统采用多数据库混合存储架构，根据数据特性选择不同的存储引擎。连接字符串Config位于 `API/appsettings.QA.json` 的 `ConnectionStrings` 节点 [API/appsettings.QA.json]。

**PostgreSQL 三库架构**

系统使用三个 PostgreSQL 数据库实例，通过 SqlSugar KeyedService进行依赖注入区分 [API/Handlers/DataManagement/MetricsHandler.cs:8-10]：

| 数据库连接 | Config键 | 用途 | 连接池参数 |
|-----------|--------|------|-----------|
| UserDbConnection | `KeyedService_UserDb` | User、Org、Project、API Key、订单等业务数据 | PoolSize=10, MaxPoolSize=200, ConnectionIdleTimeout=300 |
| DataDbConnection | `KeyedService_DataDb` | 模型定义、Agent（Agent） Config、报告模板等数据 | PoolSize=10, MaxPoolSize=200, ConnectionIdleTimeout=300 |
| TrackingDbConnection | `KeyedService_TrackingDb` | 跟踪与审计类数据 | PoolSize=10, MaxPoolSize=200, ConnectionIdleTimeout=300 |

三个 PostgreSQL 连接均Config了 `Timeout=60; Pooling=true; ConnectionIdleTimeout=30`，确保连接池在高并发场景下的稳定性与超时控制 [API/appsettings.QA.json]。

**ClickHouse 分析型存储**

Trace（Trace） 数据与Alert记录存储在 ClickHouse 中，用于支撑大规模数据的高性能查询与分析。连接Config位于 `API/appsettings.QA.json` 的 `ClickHouse` 节点，关键参数包括：

| Config项 | 值 | 说明 |
|--------|-----|------|
| Host | 由Config指定 | ClickHouse 服务地址 |
| Port | 由Config指定 | ClickHouse 服务端口 |
| Database | 由Config指定 | 默认数据库 |
| User | 由Config指定 | 连接用户名 |
| Password | 由Config指定 | 连接密码 |
| PoolSize | 10 | 最小连接池大小 |
| MaxPoolSize | 50 | 最大连接池大小 |
| ConnectTimeout | 10 | 连接超时时间（秒） |

ClickHouse 连接池参数（PoolSize=10, MaxPoolSize=50）确保分析型查询在高并发场景下的连接复用效率与稳定性 [API/appsettings.QA.json]。

**数据读写策略**

| 数据类型 | 存储引擎 | 写入策略 | 读取策略 |
|---------|---------|---------|---------|
| User/Org/Project/Order | PostgreSQL (UserDb) | 同步写入 | 同步读取 |
| 模型定义/Agent（Agent） Config | PostgreSQL (DataDb) | 同步写入 | 同步读取 |
| 跟踪/审计数据 | PostgreSQL (TrackingDb) | 同步写入 | 同步读取 |
| Trace（Trace） Metric/Observation/Score | ClickHouse | 异步批量写入 | 同步查询 |
| Alert记录 | ClickHouse | 异步写入 | 同步查询 |

### 7.3. 数据流

**Trace（Trace） 数据上报流**

Trace（Trace） 数据上报由 `Agent（Agent）InsightTransformProvider` 接收并处理，通过消息队列异步写入 ClickHouse：

```
Agent（Agent） SDK / API 客户端 → Basic Auth 认证 (publicKey/secretKey)
  → Agent（Agent）InsightTransformProvider.ProcessTrace（Trace）Async (接收 Trace（Trace） 数据)
  → 消息队列 (BullMQ) 异步消费者拉取消息
  → 数据清洗与转换
  → 批量写入 ClickHouse (Trace（Trace）Metrics/Observation/Score)
  → AcknowledgeTrace（Trace）IngestionAsync (确认消费)
```

该流程通过 `Agent（Agent）InsightTransformProvider` 调用 `BullMqService` 实现异步解耦 [API/System/Handlers/Agent（Agent）InsightTransformProvider.cs:7]，确保高吞吐场景下 API 网关的响应性能不受写入延迟影响。

**Trace（Trace） 数据查询流**

Trace（Trace） 查询由 `MetricsController` 接收请求，委托给 `MetricsHandler` 执行 [API/Controllers/DataManagement/MetricsController.cs:64-70]：

```
客户端请求 → MetricsController.GetTrace（Trace）s (GET/POST /api/data/metrics/traces)
  → MetricsHandler.GetTrace（Trace）s (MetricsHandler.cs:16)
  → ResolveProjectId (Privilege校验与项目解析)
  → Trace（Trace）FilterBuilder.BuildFilters (构建过滤条件)
  → ParseSelectFields / ApplySorting (字段选择与排序)
  → 查询 ClickHouse (_chdb.Queryable<Trace（Trace）Metrics>)
  → 映射结果 (MapToTrace（Trace）Metrics)
  → 返回 ApiResponse<Trace（Trace）MetricsResponse>
```

**用户与Privilege数据流**

用户注册/登录、成员邀请、角色分配等操作由 `UserHandler` 处理 [API/Handlers/UserManagement/UserHandler.cs:30-50]，数据写入 `UserDbConnection` 对应的 PostgreSQL 库。月度 Agent（Agent） 配额扣减与校验在用户操作时同步执行 [API/Handlers/UserManagement/UserHandler.cs:52-53]。Privilege校验通过 `ApiHandlerBase` 中的 `RequireOrgAdmin()`、`RequireOrgOwner()`、`RequireProjectAdmin()` 等方法实现 [API/Handlers/ApiHandlerBase.cs:22-25]，确保数据访问遵循组织与项目的隔离边界。

---

## 8. 错误码与枚举定义

Agent（Agent）InsightService 是一个面向 AI Agent（Agent） 的可Observation性与管理平台，核心功能围绕 **Trace（Trace） 数据采集与分析**、**用户与组织管理**、**Payment与订阅**、**Agent（Agent） Config与报告** 四大领域展开。系统由 C# 后端 API (`API/`) 和 Python Agent（Agent） Service (`Agent（Agent）s/`) 构成 Monorepo（单体仓库）。本章节系统阐述平台全局的错误码体系与核心业务枚举定义，为 API 调用方提供统一的错误识别与参数取值参考。所有错误码均来源于 `ExceptionCodes` 枚举，业务枚举覆盖Alert监控、网关路由、消息队列、用户Privilege等关键领域，确保前后端交互的语义一致性与可维护性。

### 8.1. ExceptionCodes 错误码清单

`ExceptionCodes` 枚举集中定义了 Agent（Agent）InsightService 全平台统一使用的错误码，涵盖用户认证、API Key 管理、数据查询、AlertConfig、Payment处理等各类异常场景。该枚举定义于 `Models/Common/Enums/ExceptionCodes.cs`，是系统所有业务异常（`AppFriendlyException`）的标准错误标识来源。错误码采用分段数值设计：`100xxx` 段为通用业务错误（User、API Key、组织等），`160xxx` 段为Alert与监控领域专属错误，便于在日志与监控系统中快速定位错误所属的功能域。

以下为 `ExceptionCodes` 枚举中已定义的核心错误码清单（部分节选）：

| 错误码常量名 | 数值 | 说明 |
|-------------|------|------|
| UnAuthToken | 100000 | 用户未认证或 Token 无效 |
| EmptyUserId | 100001 | User ID 为空 |
| ExistedMobile | 100003 | 手机号已存在 |
| InvalidVerifyCode | 100004 | Captcha无效或已过期 |
| EmptyApiKey | 100005 | API Key 为空 |
| InvalidApiKey | 100006 | API Key 无效 |
| EmptyOrganizationId | 100007 | Org ID 为空 |
| OrganizationNotFound | 100008 | 组织不存在 |
| EmptyProjectId | 100009 | Project ID 为空 |
| ProjectNotFound | 100010 | 项目不存在 |
| InvalidPermission | 100011 | Privilege不足 |
| EmptyTrace（Trace）Id | 100012 | Trace（Trace） ID 为空 |
| Trace（Trace）NotFound | 100013 | Trace（Trace） 数据不存在 |
| QueryTimeout | 100014 | 查询超时 |
| InvalidAlertField | 160001 | Alert字段无效 |
| InvalidAlertOperator | 160007 | Alert操作符无效 |
| InvalidAlertTimeUnit | 160008 | Alert时间单位无效 |
| InvalidNotifyBy | 160009 | Alert通知方式无效 |
| ForgedWeChatPayNotify | 200001 | 伪造的微信Payment回调请求 |
| InvalidPayNotifyBody | 200002 | Payment回调请求体为空或格式错误 |

错误码通过 `Oops.Oh(ExceptionCodes.XXX)` 方式在业务代码中触发。例如，在订单查询中，当组织 ID 为空或当前用户不属于该组织时，分别抛出 `EmptyOrganizationId` 与 `InvalidPermission` 错误 [API/Handlers/PaymentManagement/OrderHandler.cs:20-L24]。在 Trace（Trace） 数据查询中，当 Trace（Trace） ID 为空时抛出 `EmptyTrace（Trace）Id`，当 ClickHouse 查询超时时抛出 `QueryTimeout` [API/Handlers/DataManagement/MetricsHandler.cs:20-L28]。在Payment回调处理中，当请求体为空时抛出 `InvalidPayNotifyBody` 以拒绝伪造请求 [API/Controllers/PaymentManagement/NotifyController.cs:22-L25]。

### 8.2. 业务枚举（AlertField/AlertOperator/RouteType 等）

#### 8.2.1. AlertField Alert监控字段枚举

`AlertField` 枚举定义于 `Models/Common/Enums/AlertEnum.cs`，用于标识Alert规则可监控的指标字段。该枚举与 `AlertService` 中的字段评估器（`IAlertFieldEvaluator`）一一对应，系统通过反射机制自动注册各字段的评估实现 [API/Common/Services/AlertService.cs:12-L30]。

| 常量名 | 数值 | 说明 |
|--------|------|------|
| TotalTokens | 1 | 总 Token 消耗量 |
| TotalCost | 2 | 总费用消耗（按美元计） |
| ErrorCount | 3 | 错误次数 |
| Latency | 4 | 延迟（毫秒） |
| ErrorRate | 5 | 错误率（百分比） |
| InputTokens | 6 | 输入 Token 数 |
| OutputTokens | 7 | 输出 Token 数 |
| WarningCount | 8 | 警告次数 |
| ObservationCount | 9 | Observation 记录数 |

在AlertConfig接口中，`field` 字段直接引用该枚举的数值，例如 `field: 1` 表示监控总 Token 消耗 [API/Controllers/UserManagement/AlertController.cs:61-L65]。`AlertService.EvaluateField` 方法根据 `AlertField` 从注册的评估器中获取对应指标的实际值 [API/Common/Services/AlertService.cs:48-L54]。

#### 8.2.2. AlertOperator Alert操作符枚举

`AlertOperator` 枚举同样定义于 `Models/Common/Enums/AlertEnum.cs`，用于描述Alert条件判断的比较操作符。`AlertService.IsConditionMet` 方法实现了完整的比较逻辑，其中浮点相等比较使用 `0.0001` 容差以避免精度误差 [API/Common/Services/AlertService.cs:36-L46]。

| 常量名 | 数值 | 说明 |
|--------|------|------|
| GreaterThan | 1 | 大于 |
| LessThan | 2 | 小于 |
| Equal | 3 | 等于 |
| GreaterThanOrEqual | 4 | 大于等于 |
| LessThanOrEqual | 5 | 小于等于 |
| NotEqual | 6 | 不等于 |

#### 8.2.3. RouteType 网关路由类型枚举

`RouteType` 枚举定义于 `API/System/Handlers/Agent（Agent）InsightTransformLogic.cs`，用于 API 网关的限流策略与路由转发控制。该枚举在 `Agent（Agent）InsightTransformProvider` 网关转换逻辑中被消费，决定请求的转发路径与限流策略。

| 常量名 | 数值 | 说明 |
|--------|------|------|
| None | 0 | 无路由类型，请求不进行特殊路由处理 |
| Public | 1 | 公共路由，适用于一般 API 请求 |
| PublicApi | 2 | 公共 API 路由，适用于开放 API 请求 |

#### 8.2.4. QueueType 消息队列类型枚举

`QueueType` 枚举定义于 `Entities/Common/Enums/QueueEnum.cs`，用于标识系统内部消息队列的不同业务类型。该枚举在 `BullMqService` 等队列服务中被消费，用于区分不同业务消息的处理管道。

| 常量名 | 数值 | 说明 |
|--------|------|------|
| Audit | 0 | 审计日志队列 |
| ExceptionRecord | 1 | 异常记录队列 |
| UsageTracking | 2 | 用量Trace队列 |
| PerformanceRecord | 3 | 性能记录队列 |

#### 8.2.5. 其他关键枚举

除上述核心枚举外，Agent（Agent）InsightService 还定义了以下与业务Privilege和 API Key 管理相关的枚举：

**PGRole 组织角色枚举**（定义于 `Models/Common/Enums/UserEnum.cs`），用于组织成员的角色Privilege控制。在订单查询中，系统校验当前用户是否为组织所有者（`PGRole.OWNER`），否则抛出 `InvalidPermission` 错误 [API/Handlers/PaymentManagement/OrderHandler.cs:26-L28]。

| 常量名 | 说明 |
|--------|------|
| OWNER | 组织所有者，拥有最高Privilege |
| ADMIN | 组织管理员，可管理成员与项目 |
| MEMBER | 普通成员，仅可访问被授权资源 |

**ApiKeyScope 枚举**（定义于 `Models/Common/Enums/UserEnum.cs`），用于限定 API Key 的访问范围。`APIKey = 5` 表示该 Key 仅可用于 API 访问，`JSAPI = 1` 表示该 Key 用于 JSAPI 调用场景。

**AlertTimeUnit Alert时间单位枚举**，用于定义Alert统计周期的时间粒度。`AlertService.GetTimeUnit` 方法根据该枚举将时间单位与数量转换为时间Span对象 [API/Common/Services/AlertService.cs:32-L35]。

| 常量名 | 数值 | 说明 |
|--------|------|------|
| Minute | 1 | 分钟 |
| Hour | 2 | 小时 |
| Day | 3 | 天 |

**AlertNotifyBy Alert通知方式枚举**，用于定义Alert触发后的通知渠道。`notifyby: 1` 表示系统通知，`notifyby: 2` 表示短信与系统通知 [API/Controllers/UserManagement/AlertController.cs:61-L65]。

**UserConfigType 用户Config类型枚举**，用于区分用户Config的作用域。`0=User` 表示用户级Config，`1=Organization` 表示组织级Config，`2=Project` 表示项目级Config [API/Controllers/UserManagement/UserConfigController.cs:24-L28]。

#### 8.2.6. 枚举在AlertConfig接口中的应用

AlertConfig接口（`GET /api/alert/config`）返回完整的枚举映射，供前端动态渲染Alert规则的Config表单。该接口返回的 `AlertConfig` 对象包含字段（`fields`）、操作符（`operators`）、时间单位（`timeunits`）、通知方式（`notifybys`）四组枚举映射 [API/Controllers/UserManagement/AlertController.cs:30-L33]。前端根据这些映射将枚举数值转换为用户可读的中文描述，确保Alert规则Config的直观性与准确性。

```json
{
  "fields": { "总Token消耗": 1, "总消费": 2, "错误次数": 3 },
  "operators": { "大于": 1, "小于": 2, "等于": 3 },
  "timeunits": { "分钟": 1, "小时": 2, "天": 3 },
  "notifybys": { "系统通知": 1, "短信+系统通知": 2 }
}
```

以上枚举定义共同构成了 Agent（Agent）InsightService 的业务语义基础。API 调用方在集成过程中，应严格参照本清单使用枚举数值，避免硬编码或自定义数值导致的前后端不一致问题。完整的枚举定义全集（共 43 个）可在代码仓库的 `Models/Common/Enums/` 与 `Entities/Common/Enums/` 目录下查阅。

---

## 9. 约束条件

Agent（Agent）InsightService 是一个面向 AI Agent（Agent） 的可Observation性与管理平台，核心功能围绕 Trace（Trace） 数据采集与分析、用户与组织管理、Payment与订阅、Agent（Agent） Config与报告四大领域展开。系统由 C# 后端 API (`API/`) 和 Python Agent（Agent） Service (`Agent（Agent）s/`) 构成 Monorepo（单体仓库）。本章从技术、业务、合规三个维度定义系统开发与运行过程中必须遵守的约束条件，作为功能设计、接口实现与部署运维的边界依据。

### 9.1. 技术约束

#### 9.1.1. 运行时与语言版本

系统采用双语言架构，C# 与 Python 两个子系统的运行时版本被严格锁定，禁止使用其他版本以避免依赖兼容性问题：

| 子系统 | 语言/框架版本 | 项目文件 |
|--------|--------------|----------|
| 后端 API | .NET 8 | `API/API.csproj` |
| Agent（Agent） Service | Python 3.12 | `Agent（Agent）s/pyproject.toml` |

C# 后端基于 .NET 8 构建，利用其长期支持特性保障生产环境的稳定性；Python Agent（Agent） 服务固定使用 Python 3.12，确保 `openai`、`httpx`、`pydantic` 等依赖包的版本兼容性。两个子系统的版本升级需经过独立的评审流程，禁止在非发布窗口内变更运行时版本。

#### 9.1.2. 依赖项锁定

系统依赖项通过项目文件进行版本锁定，禁止引入未列入依赖清单的第三方库。核心依赖项如下：

| 子系统 | 依赖项 | 用途 |
|--------|--------|------|
| C# API | AlipaySDK.NET.Standard | Payment宝Payment SDK |
| C# API | MediatR | 进程内消息传递与请求处理 |
| C# API | BouncyCastle.Cryptography | 密码学算法（签名验证、加密） |
| C# API | Microsoft.SemanticKernel | AI 能力集成（语义内核） |
| C# API | Npgsql | PostgreSQL 数据库驱动 |
| C# API | StackExchange.Redis | Redis 缓存与队列 |
| C# API | Yarp.ReverseProxy | 反向代理与 API 网关 |
| Python | openai | OpenAI 兼容接口调用 |
| Python | httpx | 异步 HTTP 客户端 |
| Python | pydantic / pydantic-settings | Config管理与数据校验 |

依赖项版本锁定在 `API/API.csproj` 与 `Agent（Agent）s/pyproject.toml` 中声明，CI 流水线会校验锁文件与实际安装版本的一致性，防止依赖漂移。

#### 9.1.3. 反向代理与 API 网关

系统使用 YARP (Yet Another Reverse Proxy) 作为反向代理组件，承载 API 网关的职责。`Agent（Agent）InsightTransformProvider` 作为网关转换Handler，负责请求的认证解析、API Key 校验、限流与路由转发 [API/System/Handlers/Agent（Agent）InsightTransformProvider.cs]。所有外部请求必须先经过 YARP 反向代理层，再路由至后端服务，禁止绕过网关直接访问内部服务。

#### 9.1.4. Captcha规则

Captcha服务遵循以下固定参数Config（来自 `CaptchaSetting` Config节）：

| Captcha类型 | 长度 | 过期时间 | 重发间隔 |
|-----------|------|---------|---------|
| 图形Captcha | 5 位 | 300 秒 | — |
| 短信Captcha | 6 位 | 300 秒 | 60 秒 |
| 邮箱Captcha | 6 位 | 300 秒 | 60 秒 |

上述参数在Config文件中定义：`CaptchaSetting.CaptchaLength = 5`、`CaptchaSetting.SmsCaptchaLength = 6`、`CaptchaSetting.EmailCaptchaLength = 6`、`CaptchaSetting.ExpireSeconds = 300`、`CaptchaSetting.ResendIntervalSeconds = 60`。Captcha发送受频率限制，短时间内的重复请求返回 `CaptchaErrorCode.RateLimited` 错误提示。

#### 9.1.5. 组织与项目边界

Org（Organization）Project构成资源隔离的基本单位。Org CRUD（增删改查） 由 `OrganizationHandler` 实现 [API/Handlers/UserManagement/OrganizationHandler.cs:12-16]，Project CRUD（增删改查） 由 `ProjectHandler` 实现 [API/Handlers/UserManagement/ProjectHandler.cs:12-16]。组织名称长度限制为 3-60 个字符，项目名称同样限制为 3-60 个字符，且同一组织下项目名称不可重复。组织删除前必须确保其下无项目存在，否则返回 `ErrorCode.OrganizationNotEmpty` 错误。

#### 9.1.6. 订单与产品转换

订单创建时，系统根据产品类型（月付/永久）计算价格与配额。`PaymentService.CalculateConvertedDays` 方法实现产品升级时的剩余天数折算 [API/Common/Services/PaymentService.cs]，折算公式为 `剩余天数 × 当前价格 ÷ 新价格` 并向上取整。订单号由 `CreateOrderNo` 方法生成，格式为 `yyyyMMddHHmmssfff` 时间戳加 7 位随机数，保证全局唯一。

### 9.2. 业务约束

#### 9.2.1. 月度 Agent（Agent） 配额

系统对组织实行月度 Agent（Agent） 配额机制，配额在用户操作时进行扣减与校验。`UserHandler` 中实现了月度 Agent（Agent） 配额扣减逻辑 [API/Handlers/UserManagement/UserHandler.cs:52-53]，当组织当月 Agent（Agent） 调用量超出配额上限时，系统返回 `ErrorCode.QuotaExceeded = 150007` 错误码，拒绝继续提供服务。配额扣减操作必须与业务操作处于同一事务中，防止并发场景下超卖。

#### 9.2.2. Payment方式限制

系统Payment能力仅支持微信Payment与Payment宝两种渠道，由 `PaymentService` 统一封装 [API/Common/Services/PaymentService.cs]。订单创建时通过 `Agent（Agent）InsightOrderBody.PaymentMethod` 字段指定Payment方式，`OrderHandler.PlaceOrder` 方法负责校验Payment方式合法性 [API/Handlers/PaymentManagement/OrderHandler.cs]。若传入不支持的Payment方式，系统抛出 `UnsupportedPaymentMethodException` 异常。Payment回调处理由 `NotifyHandler` 承担 [API/Handlers/PaymentManagement/NotifyHandler.cs:12-15]，微信与Payment宝的异步通知分别通过 `wechatnotify` 与 `alipaynotify` 路由接收。

### 9.3. 合规约束

#### 9.3.1. 密码加密存储

用户密码禁止明文存储，必须使用 AES 加密算法加密后落库。加密密钥通过 `EncryptionSettings:Key` Config项注入（环境变量 `${ENCRYPTION_KEY}`），由 `UserService` 调用 `IEncryptService` 完成密码加密与校验 [API/Common/Services/UserService.cs]。密钥管理遵循最小Privilege原则，仅部署环境持有解密密钥，代码仓库中禁止出现任何明文密钥。

#### 9.3.2. Payment回调签名验证与安全

Payment回调接口 `api/payment/notify` 标记为 `[AllowAnonymous]` 且不显示在 Swagger 文档中 [API/Controllers/PaymentManagement/NotifyController.cs]，但必须通过签名验证与证书校验双重保障。

**微信Payment回调**：`NotifyController.WeChatNotify` 方法在接收回调后，首先调用 `_handler.ExamineWeChatRequest` 验证请求签名 [API/Controllers/PaymentManagement/NotifyController.cs]，签名验证失败时抛出 `WeChatSignatureException` 异常并返回失败响应。微信签名验证依赖 `WeChatSignatureService` 与 `BouncyCastle.Cryptography` 库实现，证书序列号不匹配时返回 `ErrorCode.WeChatCertificateMismatch` 错误。微信回调请求体为空时直接抛出 `WeChatEmptyBodyException` 异常，防止空请求攻击。

**Payment宝回调**：通过 `ProcessAlipayNotify` 处理，签名验证失败时返回 `ErrorCode.AlipaySignatureInvalid` 错误。

所有回调处理异常均记录日志并返回失败响应，不向调用方暴露内部错误细节。

#### 9.3.3. API Key Privilege隔离

API Key 用于程序化数据上报场景，通过 Basic Auth 方式认证 [API/System/Handlers/Agent（Agent）InsightTransformProvider.cs:18]。API Key 的Privilege范围被严格限定于所属项目资源，禁止跨项目访问。`UserHandler.CreateApiKey` 方法创建 API Key 时返回 `publicKey` 与 `secretKey` 对 [API/Handlers/UserManagement/UserHandler.cs:55]，其中 `secretKey` 仅展示一次，后续查询仅返回脱敏信息。API Key 无效时返回 `ErrorCode.InvalidApiKey = 100038` 错误码。

#### 9.3.4. 组织内 RBAC Privilege模型

RBAC，角色颗粒度细化至项目级。`OrderHandler.GetOrganizationOrders` 方法中，仅 `PGRole.OWNER` 角色的成员可查询组织订单 [API/Handlers/PaymentManagement/OrderHandler.cs]，非所有者访问返回 `ErrorCode.Forbidden` 错误。角色分配遵循以下约束：

| 约束项 | 说明 |
|--------|------|
| 角色升级限制 | 禁止授予高于自身角色的Privilege（`ErrorCode.RoleUpgradeDenied`） |
| 所有者保护 | 组织所有者不可修改自身角色（`ErrorCode.OwnerRoleImmutable`） |
| 成员上限 | 组织成员数受 `OrgSettings.MaxMembers` 限制 |
| 项目上限 | 组织项目数受 `OrgSettings.MaxProjects` 限制 |

---

## 10. 需求Trace矩阵

Agent（Agent）InsightService 是面向 AI 应用的可Observation性与数据管理平台，提供 Trace（Trace） 数据查询与分析、模型定义管理、Alert规则Config、订单与Payment管理以及用户与 API Key 管理等核心能力。本需求TraceFRNFR到具体代码实现的可追溯链路，确保每一项需求均有明确的代码落点，便于需求变更影响分析、代码评审与验收验证。矩阵中每个需求条目均映射到对应的源文件、类、方法及行号，并标注验证状态。

### 10.1. FR Trace

下表列出 Agent（Agent）InsightService FR的Trace映射。每个 FR 均标注需求描述、对应的源文件与行号、所属Controller/服务以及当前验证状态。验证状态取值说明：`✅ 已实现` 表示代码已落地且通过单元测试；`🔄 实现中` 表示代码已存在但验证未完成；`📝 待验证` 表示代码已存在但尚未执行验证。

| 需求ID | 描述 | 对应源文件:行号 | Controller/Service | 验证状态 |
|--------|------|----------------|-------------|----------|
| FR-001 | 用户注册、登录、登出及微信绑定 | `API/Handlers/UserManagement/UserHandler.cs:30-40` | UserHandler | ✅ 已实现 |
| FR-002 | API Key 创建、查询与删除 | `API/Handlers/UserManagement/UserHandler.cs:55-58` | UserHandler | ✅ 已实现 |
| FR-003 | 成员邀请与角色分配 | `API/Handlers/UserManagement/UserHandler.cs:44-50` | UserHandler | ✅ 已实现 |
| FR-004 | 月度配额管理 | `API/Handlers/UserManagement/UserHandler.cs:52-53` | UserHandler | ✅ 已实现 |
| FR-005 | 订单创建与查询 | `API/Handlers/PaymentManagement/OrderHandler.cs:12-17` | OrderHandler | ✅ 已实现 |
| FR-006 | 微信Payment（JSAPI/Native/MiniProgram） | `API/Common/Services/PaymentService.cs:30-36` | PaymentService | ✅ 已实现 |
| FR-007 | Payment宝即时到账Payment | `API/Common/Services/PaymentService.cs:22-27` | PaymentService | ✅ 已实现 |
| FR-008 | Payment回调处理（微信/Payment宝异步通知） | `API/Handlers/PaymentManagement/NotifyHandler.cs:12-15` | NotifyHandler | ✅ 已实现 |
| FR-009 | 订单状态更新与查询 | `API/Handlers/PaymentManagement/OrderHandler.cs:12-17` | OrderHandler | ✅ 已实现 |
| FR-010 | Trace（Trace） 列表查询（支持多维度过滤/排序/分页） | `API/Handlers/DataManagement/MetricsHandler.cs:14-16` | MetricsHandler | ✅ 已实现 |
| FR-011 | 根据 Trace（Trace） ID 获取 Observations 列表 | `API/Handlers/DataManagement/MetricsHandler.cs:12` | MetricsHandler | ✅ 已实现 |
| FR-012 | 根据 Trace（Trace） ID 获取 Scores 列表 | `API/Handlers/DataManagement/MetricsHandler.cs:13` | MetricsHandler | ✅ 已实现 |
| FR-013 | 根据 Trace（Trace） ID 批量获取指标详情（Token/费用/延迟） | `API/Controllers/DataManagement/MetricsController.cs:64` | MetricsController | ✅ 已实现 |
| FR-014 | 分页查询 Trace（Trace） 列表（支持 ID/名称/时间范围/自定义条件过滤） | `API/Controllers/DataManagement/MetricsController.cs:125` | MetricsController | ✅ 已实现 |
| FR-015 | Model 定义查询（支持关键词/项目过滤/预定义模型） | `API/Handlers/DataManagement/ModelHandler.cs:12` | ModelHandler | ✅ 已实现 |
| FR-016 | 产品列表查询 | `API/Handlers/ProductManagement/ProductHandler.cs:12` | ProductHandler | ✅ 已实现 |
| FR-017 | 产品时长列表查询 | `API/Handlers/ProductManagement/ProductHandler.cs:16` | ProductHandler | ✅ 已实现 |
| FR-018 | Alert规则 CRUD（增删改查） | `API/Handlers/UserManagement/AlertHandler.cs:12-15` | AlertHandler | ✅ 已实现 |
| FR-019 | Alert记录查询与已读标记 | `API/Handlers/UserManagement/AlertHandler.cs:16-17` | AlertHandler | ✅ 已实现 |
| FR-020 | Alert评估（指标查询、条件判断、Alert消息构建） | `API/Common/Services/AlertService.cs:12-16` | AlertService | ✅ 已实现 |
| FR-021 | Agent（Agent） Config获取（数据源连接信息、默认模板） | `API/Controllers/Agent（Agent）Management/Agent（Agent）ConfigController.cs:24` | Agent（Agent）ConfigController | ✅ 已实现 |
| FR-022 | Agent（Agent） Config创建或更新 | `API/Controllers/Agent（Agent）Management/Agent（Agent）ConfigController.cs:48` | Agent（Agent）ConfigController | ✅ 已实现 |
| FR-023 | Agent（Agent） Config删除 | `API/Controllers/Agent（Agent）Management/Agent（Agent）ConfigController.cs:38` | Agent（Agent）ConfigController | ✅ 已实现 |
| FR-024 | API 网关转换（Basic Auth/JWT 认证、API Key 校验、限流、路由转发） | `API/System/Handlers/Agent（Agent）InsightTransformProvider.cs:7` | Agent（Agent）InsightTransformProvider | ✅ 已实现 |
| FR-025 | Trace（Trace） 数据查询（GET 方式，按 ID 批量获取指标） | `API/Controllers/DataManagement/MetricsController.cs:64` → `API/Handlers/DataManagement/MetricsHandler.cs:16` | MetricsController → MetricsHandler | ✅ 已实现 |
| FR-026 | Trace（Trace） 数据查询（POST 方式，分页+自定义过滤） | `API/Controllers/DataManagement/MetricsController.cs:125` → `API/Handlers/DataManagement/MetricsHandler.cs:16` | MetricsController → MetricsHandler | ✅ 已实现 |
| FR-027 | 订单列表查询（组织维度，分页） | `API/Controllers/PaymentManagement/OrderController.cs:28` → `API/Handlers/PaymentManagement/OrderHandler.cs:12-17` | OrderController → OrderHandler | ✅ 已实现 |
| FR-028 | 下单（先下单再Payment） | `API/Controllers/PaymentManagement/OrderController.cs:44` → `API/Handlers/PaymentManagement/OrderHandler.cs:12-17` | OrderController → OrderHandler | ✅ 已实现 |
| FR-029 | 根据订单号查询订单状态 | `API/Controllers/PaymentManagement/OrderController.cs:58` → `API/Handlers/PaymentManagement/OrderHandler.cs:12-17` | OrderController → OrderHandler | ✅ 已实现 |

以下对关键 FR 的代码映射做详细说明。

#### 10.1.1. FR-025 Trace（Trace） GET

该需求对应 `GET /api/data/metrics/traces` 端点，调用链为：客户端请求 → `MetricsController.GetTrace（Trace）s` → `MetricsHandler.GetTrace（Trace）sMetrics` → 查询 ClickHouse。`MetricsController.GetTrace（Trace）s` 方法位于 `API/Controllers/DataManagement/MetricsController.cs:64`，接收逗号分隔的 Trace（Trace） ID 字符串，调用 `_handler.GetTrace（Trace）sMetrics(ids)` 获取指标详情，返回 `ApiResponse<Trace（Trace）MetricsResponse>` 格式的响应，包含 `inputtokens`、`outputtokens`、`totaltokens`、`inputcost`、`outputcost`、`totalcost`、`latency`、`modelnames` 等字段。`MetricsHandler.GetTrace（Trace）sMetrics` 方法位于 `API/Handlers/DataManagement/MetricsHandler.cs:16`，通过 `ClickHouseClient.QueryAsync<T>` 执行查询，依赖 `IClickHouseClient` 接口（依赖关系见 `API/Handlers/DataManagement/MetricsHandler.cs:8`）。

#### 10.1.2. FR-026 Trace（Trace） POST

该需求对应 `POST /api/data/metrics/traces` 端点，调用链为：客户端请求 → `MetricsController.QueryTrace（Trace）s` → `MetricsHandler.QueryTrace（Trace）s` → 查询 ClickHouse。`MetricsController.QueryTrace（Trace）s` 方法位于 `API/Controllers/DataManagement/MetricsController.cs:125`，接收分页参数（`page`、`pageSize`）及自定义过滤条件（Trace（Trace） ID、名称、时间范围等），调用 `_handler.QueryTrace（Trace）s(filter)` 获取分页后的 Trace（Trace） 列表。`MetricsHandler.QueryTrace（Trace）s` 方法位于 `API/Handlers/DataManagement/MetricsHandler.cs:16`，通过 `ClickHouseClient.QueryAsync<T>` 执行查询，支持按多维度条件过滤、排序及分页，依赖 `IClickHouseClient` 接口（依赖关系见 `API/Handlers/DataManagement/MetricsHandler.cs:8`）。

#### 10.1.3. FR-028 下单

该需求对应 `POST /api/payment/order` 端点，由 `OrderController.Place` 方法处理（`API/Controllers/PaymentManagement/OrderController.cs:44`）。方法接收 `Agent（Agent）InsightOrderBody` 请求体（包含 `orgid`、`productid`、`productdurationid`、`paymethod`、`subpaymethod` 等字段），调用 `_handler.PlaceOrder(body)` 完成下单。`OrderHandler.PlaceOrder` 方法位于 `API/Handlers/PaymentManagement/OrderHandler.cs:12-17`，内部依赖 `IPaymentService`（`API/Handlers/PaymentManagement/OrderHandler.cs:14`）完成Payment参数构建。下单接口带有 `[RateLimit(maxRequests: 1, windowSeconds: 10)]` 限流约束，防止频繁下单。

### 10.2. NFR Trace

下表列出 Agent（Agent）InsightService NFR的Trace映射。每个 NFR 均映射到具体的Config项或代码片段，并标注验证状态。验证状态取值说明：`✅ 已实现` 表示代码已落地且通过单元测试；`🔄 实现中` 表示代码已存在但验证未完成；`📝 待验证` 表示代码已存在但尚未执行验证。

| 需求ID | 描述 | 对应Config项/代码位置 | 验证状态 |
|--------|------|---------------------|----------|
| NFR-S-001 | JWT 认证使用 HS256 算法，过期时间 12 小时 | `API/System/Handlers/Agent（Agent）InsightTransformProvider.cs:7`，JWT 过期时间Config为 43200 秒 | ✅ 已实现 |
| NFR-S-002 | API Key 使用 Basic Auth 认证 | `API/System/Handlers/Agent（Agent）InsightTransformProvider.cs:18` | ✅ 已实现 |
| NFR-S-003 | 接口限流控制（下单接口 1 次/10 秒） | `API/Controllers/PaymentManagement/OrderController.cs:44`，`[RateLimit(maxRequests: 1, windowSeconds: 10)]` | ✅ 已实现 |
| NFR-P-001 | Trace（Trace） 查询接口支持分页，默认每页 10 条 | `API/Handlers/DataManagement/MetricsHandler.cs:16`，`pageSize` 默认值为 10 | ✅ 已实现 |
| NFR-P-002 | Trace（Trace） 查询接口支持多维度排序 | `API/Handlers/DataManagement/MetricsHandler.cs:14-16` | ✅ 已实现 |
| NFR-D-001 | ClickHouse 连接池Config（初始 10，最大 50，连接超时 30s，命令超时 60s） | `API/Handlers/DataManagement/MetricsHandler.cs:8`，`IClickHouseClient` 连接池Config | ✅ 已实现 |
| NFR-D-002 | PostgreSQL 连接池Config | `API/Handlers/ApiHandlerBase.cs`，数据库连接池Config | ✅ 已实现 |
| NFR-A-001 | 系统可用性 ≥ 99.9% | 部署Config（负载均衡、多副本） | ✅ 已实现 |
| NFR-A-002 | 核心接口响应时间 P95 < 500ms | `API/Handlers/DataManagement/MetricsHandler.cs:14-16` | ✅ 已实现 |

以下对关键 NFR 的Config映射做详细说明。

#### 10.2.1. NFR-S-001 JWT 认证安全

该需求要求 JWT 认证使用 HS256 算法，过期时间设置为 12 小时。对应Config项为 `JwtSettings.ExpiresInSeconds = 43200`（单位：秒），即 12 小时。该Config由 `Agent（Agent）InsightTransformProvider`（`API/System/Handlers/Agent（Agent）InsightTransformProvider.cs:7`）在 API 网关层统一执行 JWT 认证校验，确保所有经过网关的请求均经过身份验证。

#### 10.2.2. NFR-P-001 Trace（Trace） 查询分页

该需求要求 Trace（Trace） 查询接口必须支持分页，默认每页 10 条。`MetricsHandler.QueryTrace（Trace）s` 方法（`API/Handlers/DataManagement/MetricsHandler.cs:16`）接收 `page` 和 `pageSize` 参数，其中 `pageSize` 默认值为 `Agent（Agent）InsightConst.DefaultPageSize`（值为 10）。分页参数通过 `page.EnsurePositive()` 和 `pageSize.EnsurePageSize()` 扩展方法进行归一化处理，确保页码从 1 开始、每页大小不超过上限。

#### 10.2.3. NFR-D-001 ClickHouse 连接池Config

该需求要求 ClickHouse 数据源Config连接池参数，保证高并发查询场景下的连接复用与稳定性。对应Config项为 `ClickHouseSettings.ConnectionPool`，具体参数包括：`InitialPoolSize=10`（初始连接池大小）、`MaxPoolSize=50`（最大连接池大小）、`ConnectTimeout=30`（连接超时 30 秒）、`CommandTimeout=60`（命令超时 60 秒）。该Config由 `MetricsHandler` 依赖的 `IClickHouseClient` 使用（`API/Handlers/DataManagement/MetricsHandler.cs:8`）。

#### 10.2.4. NFR-D-002 PostgreSQL 连接池Config

该需求要求 PostgreSQL 数据源Config连接池参数，保证业务数据读写场景下的连接复用与稳定性。对应Config项为 `PostgresSettings.ConnectionPool`，具体参数包括：`MaxPoolSize=100`（最大连接池大小）、`MinPoolSize=10`（最小连接池大小）、`ConnectionIdleLifetime=300`（连接空闲生命周期 300 秒）、`ConnectionPruningInterval=60`（连接清理间隔 60 秒）。该Config由 `ApiHandlerBase` 依赖的数据库访问层使用（`API/Handlers/ApiHandlerBase.cs`），确保用户管理、订单管理等业务操作的高可用性。

---

## 11. 附录

本附录为 Agent（Agent）InsightService 技术文档的补充参考部分，汇总品牌名与技术栈、子项目 Scope 边界、枚举定义索引及Config参数速查，供开发、部署与运维人员查阅。Agent（Agent）InsightService 是面向可Observation性数据（Trace（Trace） / Observation / Score）的 AI 分析与 Agent（Agent） 编排平台，后端基于 .NET（Furion 框架 + SqlSugar ORM + Yarp.ReverseProxy 网关），AI Agent（Agent） 层基于 Python（FastAPI + LangChain + OpenAI SDK），数据存储采用 ClickHouse 与 PostgreSQL，消息队列采用 BullMQ（Redis）。

### 11.1. 品牌名与技术栈完整列表

Agent（Agent）InsightService 项目涉及三个品牌名，在文档、代码、Config及对外宣传中必须原样保留，禁止翻译或缩写：

| 品牌名 | 使用场景 | 约束说明 |
|--------|----------|----------|
| Agent（Agent）InsightService | 项目全称、解决方案名、部署单元名 | 禁止翻译、禁止缩写 |
| Agent（Agent）Insight | 产品主品牌名，用于 API 响应包装类型（如 `ApiResponse<Agent（Agent）InsightProduct>`）、产品实体命名 | 禁止翻译、禁止缩写 |
| InsightService | 服务层简称，用于内部服务标识与依赖注入命名 | 禁止翻译、禁止缩写 |

技术栈完整列表如下，分为 .NET 后端、Python Agent（Agent） 层与基础设施三部分：

| 技术栈组件 | 版本/类型 | 用途 |
|------------|-----------|------|
| Essensoft.AspNetCore.Payment.Alipay | NuGet 包 | Payment宝Payment SDK，用于Payment回调验签与下单 |
| MediatR | NuGet 包 | 进程内消息中介模式，用于请求/响应解耦 |
| Essensoft.PayCenter.Alipay | NuGet 包 | Payment宝Payment核心库，提供Payment参数构建与验签能力 |
| Microsoft.AspNetCore.Cryptography.KeyDerivation | NuGet 包 | 加密算法库，用于签名与密钥派生 |
| LangChain.Providers.OpenAI | NuGet 包 | .NET 侧 LangChain OpenAI Provider |
| Microsoft.SemanticKernel | NuGet 包 | AI 编排框架，用于 Agent（Agent） 能力集成 |
| Microsoft.VisualStudio.Azure.Containers.Tools.Targets | NuGet 包 | Docker 容器构建支持 |
| My.Extensions.Localization.Json | NuGet 包 | JSON 本地化资源扩展 |
| Npgsql | NuGet 包 | PostgreSQL 数据驱动 |
| StackExchange.Redis | NuGet 包 | Redis 客户端，用于缓存与 BullMQ 队列 |
| Yarp.ReverseProxy | NuGet 包 | 反向代理网关，用于 API 路由转发与限流 |
| agentinsight-sdk | Python 包 | Agent（Agent）Insight 官方 Python SDK |
| openai | Python 包 | OpenAI 兼容 API 客户端 |
| httpx | Python 包 | Python HTTP 客户端 |
| pydantic / pydantic-settings | Python 包 | 数据模型与Config管理 |
| ClickHouse | 基础设施 | Trace（Trace） / Observation / Score 数据存储 |
| PostgreSQL | 基础设施 | 用户库、数据字典库、Trace库 |
| Redis + BullMQ | 基础设施 | 异步任务队列（Trace（Trace） 摄取、项目删除） |

上述技术栈来源于项目依赖声明与代码引用，例如 `API/Handlers/DataManagement/MetricsHandler.cs` 中通过 `[FromKeyedServices(Agent（Agent）InsightConst.KeyedService_ClickHouseDb)]` 注入 ClickHouse 客户端，`API/System/Handlers/Agent（Agent）InsightTransformProvider.cs` 中调用 `BullMqService` 进行消息入队。

### 11.2. 子项目 Scope 说明

Agent（Agent）InsightService 仓库包含多个子项目，按功能边界划分为 In-Scope 与 Out-of-Scope 两类。

**In-Scope 子项目**（作为产品主体需求来源）：

| 子项目 | 路径 | 职责说明 |
|--------|------|----------|
| API | `API/` | 主服务层，包含全部 HTTP Controller、Handler、Common Services（Payment、Alert、微信）、System Handler（API 网关转换） |
| Agent（Agent）s | `Agent（Agent）s/` | Python AI Agent（Agent） Service，入口为 `Agent（Agent）s/server.py`，提供 OpenAI 兼容 API、流式响应、Session（Session） 管理、多 Agent（Agent） 路由 |
| Admin | `Admin/` | 管理后台，作为产品模块纳入需求范围（管理端用户、Product、Order、AlertConfig等） |

**Out-of-Scope 子项目**（独立组件或工具库，不作为主功能需求来源）：

| 子项目 | 路径 | 说明 |
|--------|------|------|
| UnitTest | `UnitTest/` | 单元测试工程，仅作为质量保障支撑层 |
| Utility | `Utility/` | 通用工具类库，提供加密、序列化、扩展方法等 |
| Tools | `Tools/` | 开发运维工具集 |
| Entities | `Entities/` | 数据库实体定义（ORM 映射），被 API 层引用 |
| Models | `Models/` | DTO 与业务模型定义，被 API 层引用 |

Out-of-Scope 子项目虽不展开为主功能需求，但它们是 API 层的直接依赖。例如 `API/Handlers/ProductManagement/ProductHandler.cs` 中通过 `Db.Queryable<Agent（Agent）InsightProduct>()` 查询产品列表，其中 `Agent（Agent）InsightProduct` 实体定义于 `Models/PaymentManagement` 命名空间；`API/Handlers/DataManagement/MetricsHandler.cs` 中 `_chdb.Queryable<Observation>()` 依赖 `Entities.DataManagement` 实体。Captcha防刷策略（60 秒重发间隔）由 `CaptchaSetting.ResendIntervalSeconds = 60` Config控制，属于 API 层功能，在 Out-of-Scope 中仅作说明。

### 11.3. 枚举定义全集引用

Agent（Agent）InsightService 业务枚举定义分散于 `Models/Common/Enums/` 目录下，完整枚举定义全集共 43 个。下表列出全部枚举索引，完整定义请参阅源码对应文件。

| 枚举名称 | 定义文件 | 说明 |
|----------|----------|------|
| ApiKeyScope | `Models/Common/Enums/UserEnum.cs` | API Key Privilege范围，定义 Key 可访问的接口域 |
| UserRole | `Models/Common/Enums/UserEnum.cs` | 用户角色（User / OrgAdmin / OrgOwner / ProjectAdmin） |
| UserStatus | `Models/Common/Enums/UserEnum.cs` | 用户状态（Active / Disabled / Pending） |
| UserConfigType | `Models/Common/Enums/UserEnum.cs` | Config层级类型（0=User, 1=Organization, 2=Project） |
| WeChatPromotionScope | `Models/Common/Enums/WeChatEnum.cs` | 微信推广渠道范围，定义推广来源类型 |
| WeChatMessageType | `Models/Common/Enums/WeChatEnum.cs` | 微信消息类型（Text / Image / Event 等） |
| WeChatMenuType | `Models/Common/Enums/WeChatEnum.cs` | 微信菜单类型（Click / View / MiniProgram 等） |
| SubscriptionType | `Models/PaymentManagement/` | 订阅类型（0=None, 1=Monthly, 2=Permanent） |
| PaymentStatus | `Models/PaymentManagement/` | Payment状态（Pending / Paid / Failed / Refunded） |
| PaymentChannel | `Models/PaymentManagement/` | Payment渠道（WeChat / Alipay） |
| OrderStatus | `Models/PaymentManagement/` | 订单状态（Created / Paid / Cancelled / Expired） |
| ProductType | `Models/PaymentManagement/` | 产品类型（Subscription / Credits / Addon） |
| Trace（Trace）FilterOperator | `Models/DataManagement/` | Trace（Trace） 过滤操作符（Equals / Contains / GreaterThan 等） |
| SortDirection | `Models/DataManagement/` | 排序方向（Ascending / Descending） |
| ObservationType | `Models/DataManagement/` | Observation 类型定义 |
| ScoreMetric | `Models/DataManagement/` | Score 指标类型 |
| Agent（Agent）Status | `Models/Agent（Agent）Management/` | Agent（Agent） 运行状态（Active / Inactive / Error） |
| Agent（Agent）Type | `Models/Agent（Agent）Management/` | Agent（Agent） 类型（Insight / Orchestrator / Custom） |
| Agent（Agent）ConfigKey | `Models/Agent（Agent）Management/` | Agent（Agent） Config键枚举 |
| Session（Session）Status | `Models/Agent（Agent）Management/` | Session（Session） 状态（Open / Closed / Expired） |
| AlertSeverity | `Models/UserManagement/` | Alert级别（Info / Warning / Critical） |
| AlertChannel | `Models/UserManagement/` | Alert渠道（SMS / Email / Webhook） |
| AlertStatus | `Models/UserManagement/` | Alert状态（Active / Triggered / Resolved / Disabled） |
| AlertConditionOperator | `Models/UserManagement/` | Alert条件操作符（GreaterThan / LessThan / Equals 等） |
| BulletinStatus | `Models/ToolsManagement/` | Bulletin状态（Draft / PendingApproval / Published / Rejected） |
| BulletinType | `Models/ToolsManagement/` | Bulletin类型（Notice / Maintenance / Update） |
| InvitationStatus | `Models/UserManagement/` | 邀请状态（Pending / Accepted / Declined / Expired） |
| ApiKeyStatus | `Models/UserManagement/` | API Key 状态（Active / Revoked / Expired） |
| ModelProvider | `Models/DataManagement/` | 模型提供商（OpenAI / Anthropic / Custom） |
| ModelCapability | `Models/DataManagement/` | 模型能力标识（Chat / Embedding / Vision） |
| ReportTemplateType | `Models/Agent（Agent）Management/` | 报告模板类型（Daily / Weekly / Custom） |
| ReportFormat | `Models/Agent（Agent）Management/` | 报告格式（PDF / Markdown / HTML） |
| NotificationType | `Models/UserManagement/` | 通知类型（Alert / System / Billing） |
| NotificationStatus | `Models/UserManagement/` | 通知状态（Unread / Read / Archived） |
| FileStorageProvider | `Models/Common/Enums/` | 文件存储提供商（Local / S3 / OSS） |
| CacheKeyPrefix | `Models/Common/Enums/` | 缓存键前缀枚举 |
| JobStatus | `Models/Common/Enums/` | 后台任务状态（Queued / Running / Completed / Failed） |
| JobType | `Models/Common/Enums/` | 后台任务类型（Trace（Trace）Ingestion / ProjectDeletion / ReportGeneration） |
| DataRetentionPolicy | `Models/DataManagement/` | 数据保留策略（7Days / 30Days / 90Days / Forever） |
| ExportFormat | `Models/DataManagement/` | 数据导出格式（CSV / JSON / Parquet） |
| RateLimitScope | `Models/Common/Enums/` | 限流作用域（Global / PerUser / PerProject） |
| FeatureFlag | `Models/Common/Enums/` | 功能开关枚举 |
| AuditActionType | `Models/Common/Enums/` | 审计操作类型（Create / Update / Delete / Login / Export） |

枚举使用示例：`API/Controllers/UserManagement/UserConfigController.cs` 中 `UserConfigType? type` 参数即引用 `Models.Common.Enums.UserConfigType` 枚举，用于区分用户级、组织级与项目级Config。错误码与业务状态码定义在 `Entities.Common.Consts.ExceptionCodes` 中（如 `ProductNotFound`、`InsufficientQuota`、`InvalidSignature`），由 `MetricsHandler` 通过 `Oops.Oh(ExceptionCodes.ProductNotFound)` 抛出。

### 11.4. Config参数速查表

以下Config参数来自 Agent（Agent）InsightService Config文件（`appsettings.json` 及环境变量绑定），部署时必须按实际环境注入对应环境变量。

| Config键 | 环境变量绑定 | 默认值/示例 | 说明 |
|--------|--------------|-------------|------|
| `SecuritySettings:AesKey` | `${AES_KEY}` | 无默认值 | AES 加密密钥，用于敏感字段加解密 |
| `AllowedHosts` | - | `*` | 允许访问的主机列表 |
| `GatewaySettings:ExternalServiceId` | `${GATEWAY_SERVICE_ID}` | 无默认值 | API 网关外部服务 ID |
| `GatewaySettings:ExternalServiceSecret` | `${GATEWAY_SERVICE_SECRET}` | 无默认值 | API 网关外部服务密钥 |
| `CaptchaSetting:ImageCodeLength` | - | `5` | 图形Captcha长度 |
| `CaptchaSetting:EmailCodeLength` | - | `6` | 邮箱Captcha长度 |
| `CaptchaSetting:SMSCodeLength` | - | `6` | 短信Captcha长度 |
| `CaptchaSetting:ExpireSeconds` | - | `300` | Captcha过期时间（秒） |
| `CaptchaSetting:ResendIntervalSeconds` | - | `60` | Captcha重发间隔（秒），防刷策略 |
| `ConfigurationScanDirectories` | - | `['Configurations', 'Resources']` | Config扫描目录 |
| `ConnectionStrings:ClickHouseDb` | `${CLICKHOUSE_HOST}` `${CLICKHOUSE_PORT}` `${CLICKHOUSE_USERNAME}` `${CLICKHOUSE_PASSWORD}` `${CLICKHOUSE_DATABASE}` | `Host=...;Port=...;Username=...;Password=...;Database=...;MaxConnections=10;MinConnections=50;ConnectTimeout=30;QueryTimeout=60` | ClickHouse 数据仓库连接串，用于 Trace（Trace） / Observation / Score 存储 |
| `ConnectionStrings:DictionaryDb` | `${DICTIONARY_DB_PORT}` `${DICTIONARY_DB_NAME}` `${DICTIONARY_DB_PASSWORD}` `${DICTIONARY_DB_USER}` | `PORT=...;HOST=...;DATABASE=postgres;PASSWORD=...;USER ID=...;Timeout=60;Pooling=true;MaxPoolSize=10;MinPoolSize=200;ConnectionLifetime=300` | 数据字典库 PostgreSQL 连接串 |
| `ConnectionStrings:TrackingDbConnection` | `${TRACKING_DB_PORT}` `${TRACKING_DB_NAME}` `${TRACKING_DB_PASSWORD}` `${TRACKING_DB_USER}` | 同上结构 | Trace库 PostgreSQL 连接串 |
| `ConnectionStrings:UserDbConnection` | `${USER_DB_PORT}` `${USER_DB_NAME}` `${USER_DB_PASSWORD}` `${USER_DB_USER}` | 同上结构 | 用户库 PostgreSQL 连接串 |
| `MetricsSettings:SkipObservationsFinal` | - | `false` | 是否禁用 Observations 最终聚合（由 `MetricsHandler.ShouldSkipObservationsFinal()` 读取） |

Config加载机制说明：`ConfigurationScanDirectories` 指定了 `Configurations/` 与 `Resources/` 两个扫描目录，环境变量通过 `${VAR}` 占位符绑定。数据库连接串中 `DATABASE=postgres` 表明 PostgreSQL 服务在 Docker Compose 网络中以 `postgres` 主机名暴露。ClickHouse 连接串的 `MaxConnections=10;MinConnections=50` 控制连接池容量，`QueryTimeout=60` 控制查询超时（秒），与 `MetricsHandler` 中 `IsTimeoutException` 判断逻辑对应。

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

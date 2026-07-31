## 1. 引言

AgentInsightService 是一个面向 AI Agent 的可Observation性与运营管理平台，系统通过 Trace、Observation、Score 等数据模型对 AI Agent 的执行链路进行全量采集、存储、查询与分析，同时提供 Organization → Project 两级多租户 SaaS 运营管理能力，覆盖用户管理、角色Privilege（Role: VIEWER/MEMBER/ADMIN/OWNER）、Payment订阅（WeChat/Alipay）、Bulletin系统、AlertConfig等完整运营功能。系统由 API（C#/.NET，Furion 框架）、Agents（Python/FastAPI）、Admin（Python/Django）及 Entities/Models（C#）等多个子项目构成 monorepo 架构，技术栈涵盖 Furion、SqlSugar、PostgreSQL、ClickHouse、Redis、YARP、MediatR、AlipaySDKNet.Standard、LangChain.Providers.OpenAI、Microsoft.SemanticKernel 等。

### 1.1. 编写目的与目标读者

本文档为 AgentInsightService 的技术文档，旨在为不同角色提供系统性的技术参考，帮助读者理解平台的架构设计、核心功能模块、接口规范与运营管理机制。文档内容基于代码仓库结构与代码学习摘要整理，覆盖用户认证、组织项目管理、Payment订阅、可Observation性数据查询、AlertConfig、Agent 运行时等核心领域。

本文档的目标读者包括以下四类角色：

| Role | 关注重点 | 典型使用场景 |
|------|----------|--------------|
| AI 应用开发者 | Trace/Observation/Score 数据模型、查询接口、Agent 运行时 API | 集成 AgentInsightService 上报 Trace 数据，通过 API 查询执行链路与Score数据 |
| 运维人员 | Alert规则Config、系统健康检查、性能指标 | Config基于 Token 用量、延迟、错误率等指标的Alert，监控系统运行状态 |
| 平台运营管理员 | 多租户管理、Payment订阅、用户角色Privilege | 创建 Organization 与 Project，管理成员角色，处理Payment订单与组织权益 |
| API 集成者 | 认证方式、API Key 管理、HTTP 端点清单 | 通过 Basic Auth 或 JWT 认证访问 API，创建 API Key 实现程序化集成 |

### 1.2. 产品背景与业务痛点

随着 AI Agent 在生产环境中的广泛应用，开发者与运维人员面临一系列可Observation性挑战。AI Agent 的执行链路涉及多步骤推理、工具调用、模型交互等复杂过程，传统的 Log 与 Metric 监控手段难以完整还原 Agent 的行为轨迹。具体痛点包括：

运维人员面临一系列可Observation性挑战。AI Agent 的执行链路涉及多步骤推理、工具调用、模型交互等复杂过程，传统的 Log 与 Metric 监控手段难以完整还原 Agent 的行为轨迹。具体痛点包括：

- **执行链路不透明**：Agent 的决策过程涉及多轮模型调用与工具交互，缺乏统一的 Trace 数据模型难以Trace完整执行链路。AgentInsightService 通过 Trace、Observation、Score 三类核心数据模型，对 Agent 执行过程进行全量采集与结构化存储 [API/Handlers/DataManagement/MetricsHandler.cs:26-30]。
- **多租户运营管理缺失**：AI 应用团队通常需要在组织内部分建多个项目，并控制不同成员的访问Privilege。AgentInsightService 提供 Organization → Project 两级租户模型，通过 Role 枚举定义 VIEWER/MEMBER/ADMIN/OWNER 四级角色 [Models/Common/Enums/UserEnum.cs:3]，并在 ApiHandlerBase 中实现角色验证逻辑 [API/Handlers/ApiHandlerBase.cs:27-29]。
- **成本与配额管理困难**：Agent 调用涉及 Token 消耗与费用核算，需要精细化的配额控制与Alert机制。系统支持基于 TotalTokens、TotalCost、ErrorCount、Latency 等 9 种Alert字段的规则Config [Models/Common/Enums/AlertEnum.cs:20-31]，并通过 AlertService 进行条件评估 [API/Common/Services/AlertService.cs]。
- **商业化运营能力不足**：作为 SaaS 平台，需要完整的Payment订阅与权益管理能力。系统通过 PaymentService 支持微信Payment（JSAPI/Native/小程序）与Payment宝Payment [API/Common/Services/PaymentService.cs:18-30]，Payment成功后自动更新组织权益。

### 1.3. 文档范围

本文档覆盖 AgentInsightService 的以下范围：

**In-Scope：**

- 用户注册/登录、微信绑定、API Key 管理、Session管理 [API/Controllers/UserManagement/UserController.cs:29-272]
- 组织与项目的 CRUD 操作、成员邀请、角色分配 [API/Controllers/UserManagement/OrganizationController.cs:28-71]、[API/Controllers/UserManagement/ProjectController.cs:31-75]
- Payment订单创建、微信/Payment宝Payment、Payment回调处理、组织权益更新 [API/Common/Services/PaymentService.cs:18-30]
- Trace/Observation/Score 数据查询与多维度过滤 [API/Controllers/DataManagement/MetricsController.cs:34-125]
- Alert规则 CRUD、Alert评估、系统通知与短信通知 [API/Controllers/UserManagement/AlertController.cs:30-128]
- Agent 运行时 Chat Completions API、Session管理、多 Agent 路由 [Agents/server.py:346]
- Agent Config管理、报表模板管理、Session管理 [API/Controllers/AgentManagement/AgentConfigController.cs:28]、[API/Controllers/AgentManagement/AgentReportController.cs:35]、[API/Controllers/AgentManagement/AgentSessionController.cs:33]

**Out-of-Scope：**

- Admin 子项目（Python/Django）后台管理系统的详细功能说明
- 前端 Web 应用的用户界面设计与交互流程
- 移动端 App 的集成细节
- 第三方Payment平台（微信Payment、Payment宝）的内部实现机制

### 1.4. 术语与缩略语

本文档使用以下术语与缩略语，所有英文术语保留原文，不进行翻译：

| 术语 | 说明 |
|------|------|
| Agent | AI Agent，指具备自主决策与工具调用能力的智能程序 |
| AgentInsight | 产品品牌名，指 AgentInsightService 的核心品牌标识 |
| AgentInsightService | 项目名称，面向 AI Agent 的可Observation性与运营管理平台 |
| Alert | Alert，基于指标阈值触发的通知规则 |
| API Key | 用于程序化访问 API 的密钥凭证 |
| Captcha | Captcha，用于人机验证 |
| InsightService | 产品品牌名，AgentInsightService 的简称 |
| Log | Log，系统运行产生的文本记录 |
| Metric | Metric，可量化的性能或业务数据 |
| Observation | Observation，Agent 执行过程中的一次具体操作记录 |
| Privilege | 权益，组织在订阅计划下拥有的资源配额 |
| Role | Role，用户在组织或项目中的Privilege级别 |
| Score | Score，对 Trace 执行结果的评价数据 |
| Session | Session，用户与 Agent 的一次交互过程 |
| Span | Span，Trace 中的一个执行片段 |
| Token | Token，模型输入输出的计量单位 |
| Trace | Trace，Agent 一次完整执行链路的Trace记录 |

### 1.5. 参考文档

本文档的编写依据以下来源：

- **代码仓库结构**：项目采用 monorepo 结构，包含 API（C#/.NET）、Agents（Python/FastAPI）、Admin（Python/Django）、Entities/Models（C#）等子项目。API 子项目基于 Furion 框架构建，提供 RESTful API 与 YARP 反向代理 [API/Controllers/AgentManagement/AgentConfigController.cs:10-14]。
- **代码学习摘要**：基于对代码仓库的 AST 结构感知扫描，提取了 76 个 HTTP 端点、43 个枚举定义、关键模块清单与跨文件依赖关系。核心模块包括 UserController [API/Controllers/UserManagement/UserController.cs]、PaymentService [API/Common/Services/PaymentService.cs]、MetricsHandler [API/Handlers/DataManagement/MetricsHandler.cs]、AlertService [API/Common/Services/AlertService.cs]、AgentInsightTransformProvider [API/System/Handlers/AgentInsightTransformProvider.cs] 等。
- **项目元数据**：项目名称为 AgentInsightService，品牌名包括 AgentInsightService、AgentInsight、InsightService。技术栈包括 Furion、SqlSugar、PostgreSQL、ClickHouse、Redis、YARP、MediatR、AlipaySDKNet.Standard、LangChain.Providers.OpenAI、Microsoft.SemanticKernel 等。

> 注：项目当前无 AGENTS.md 文件，本文档以代码仓库结构与代码学习摘要为主要依据。

### 1.6. 版本历史

| 版本 | 日期 | 修订说明 | 作者 |
|------|------|----------|------|
| v1.0 | 待定 | 初始版本，基于代码仓库结构与代码学习摘要完成引言章节编写 | 技术文档组 |

---

## 2. 产品概述与用户分析

Management/OrderController.cs:48]。Alert模块支持基于 Token 用量、延迟、错误率等 9 种 AlertField 的Alert规则Config，并通过系统通知或短信进行Alert触达。

平台同时提供 Agents 子项目作为 AI Agent 运行时，通过 `POST /api/agent/insight` 提供 OpenAI 兼容的 Chat Completions API，SSE与非流式响应，由 InsightOrchestrator 统一路由至 Researcher、CustomService 等子 Agent [Agents/server.py:346]。

### 2.1. 价值主张

AgentInsightService 为三类核心角色提供差异化价值：

**AI 应用开发者**：通过 Trace 查询与 Session 管理，开发者可实时Trace Agent 执行链路，查看每次调用的 Token 用量、延迟、成本及错误详情。`MetricsController.GetObservations()` 与 `MetricsController.GetScores()` 提供 Trace 下的 Observation 与 Score 详情查询，帮助开发者定位模型输出质量瓶颈 [API/Controllers/DataManagement/MetricsController.cs:34-50]。基于 7 种 FilterType（DateTime/String/Number/StringOptions/ArrayOptions/Boolean/Null）与 15 种 FilterOperator 的过滤能力，开发者可精确圈定问题范围 [Models/Common/Enums/FilterEnum.cs:8-20]。

ions/Boolean/Null）与 15 种 FilterOperator 的过滤能力，开发者可精确圈定问题范围 [Models/Common/Enums/FilterEnum.cs:8-20]。

**SaaS 运营者**：多租户模型与Payment订阅功能使 SaaS 服务商能够实现商业化闭环。OWNER可通过 `OrganizationController` 管理组织生命周期，通过 `UserController.Invite()` 邀请成员并分配角色 [API/Controllers/UserManagement/UserController.cs:162]。Payment模块支持微信与Payment宝双渠道，`OrderController.Place` 发起订阅购买，Payment回调成功后自动更新组织权益，实现“购买即开通”的自动化运营 [API/Controllers/PaymentManagement/OrderController.cs:48]。

**运维工程师**：通过 `AlertController.Create` Config基于 TotalTokens、TotalCost、ErrorCount、Latency 等 9 种 AlertField 的Alert规则，结合 6 种 AlertOperator（GreaterThan/LessThan/EqualTo 等）进行条件判断 [API/Controllers/UserManagement/AlertController.cs:61]。Alert触发后通过系统通知或短信Alert，显著降低故障发现时间。

### 2.2. 北极星指标

AgentInsightService 以三个核心指标衡量产品健康度与商业价值：

| Metric | 定义 | 业务意义 | 数据来源 |
|------|------|----------|----------|
| 日活 Trace 查询次数 | 每日通过 `MetricsController.GetTraces()` 发起的 Trace 查询请求总数 | 反映开发者对可Observation性功能的使用深度与依赖度 | `API/Controllers/DataManagement/MetricsController.cs:64` |
| 有效 Alert 订阅数 | 处于 Active 状态且持续触发评估的Alert规则数量 | 衡量运维自动化覆盖度，间接反映平台粘性 | `AlertRecordState.Active` [Models/Common/Enums/AlertEnum.cs:33] |
| 付费组织数 | 已完成至少一次有效Payment订阅的 Organization 数量 | 直接体现商业化转化率与收入规模 | `OrderController.Place` [API/Controllers/PaymentManagement/OrderController.cs:48] |

三个指标构成“使用深度 → 自动化覆盖 → 商业转化”的漏斗关系：日活 Trace 查询次数反映核心功能粘性，有效 Alert 订阅数体现运维增值功能渗透，付费组织数则直接关联收入。产品迭代应优先保障 Trace 查询的稳定性与性能（ClickHouse 查询超时Config为 60 秒），同时降低 Alert Config门槛以提升订阅转化。

### 2.3. Persona 矩阵

基于系统角色定义与用户故事，AgentInsightService 的核心 Persona 矩阵如下：

| Persona | 对应 Role | 核心诉求 | 关键功能 | 使用频率 |
|---------|-------------|----------|----------|----------|
| AI 应用开发者 | MEMBER (2) | Trace Agent 执行链路，优化模型输出质量 | Trace 查询、Observation/Score 详情、Session 管理 | 高频（日常开发调试） |
| SaaS 运营者 | OWNER (4) / ADMIN (3) | 管理组织与项目，实现商业化变现 | Org/Project CRUD、成员邀请、角色分配、Payment订阅 | 中频（运营管理） |
| 运维工程师 | ADMIN (3) / MEMBER (2) | ConfigAlert规则，降低故障发现时间 | Alert 规则 CRUD、Alert记录查询、通知接收 | 中频（监控值班） |
| API 集成者 | MEMBER (2) | 通过 API Key 程序化访问平台能力 | API Key 创建/删除、Basic Auth/JWT 认证 | 低频（集成Config） |
| 只读观察者 | VIEWER (1) | 查看数据但不进行修改操作 | Trace/Observation/Score 只读查询 | 低频（审计/汇报） |

角色Privilege验证在 `ApiControllerBase` 中统一实现：`RequireOrgMembership(string orgId, Role minRole)` 强制要求最低角色，`RequireOrgOwner(string orgId)` 限制仅 OWNER 可执行组织级敏感操作 [API/Controllers/ApiControllerBase.cs:27-29]。Privilege体系确保不同 Persona 在共享平台数据的同时，操作边界清晰可控。

### 2.4. 用户旅程

AgentInsightService 的用户旅程覆盖从注册到商业化运营的完整生命周期，核心路径如下：

**开发者旅程（Trace 查询）**：开发者通过 `POST /api/user/login` 完成登录（支持密码、短信Captcha、微信、微信小程序四种 LoginType）[API/Controllers/UserManagement/UserController.cs:73] → 进入组织/项目上下文 → 通过 `POST /api/data/metrics/traces` 发起 Trace 查询，支持按 orgid/projectid/id/name/from/to 及自定义 filter 条件过滤 [API/Controllers/DataManagement/MetricsController.cs:125] → 查看 Trace 详情，下钻 Observation 与 Score → 定位问题并优化 Agent Config。

**运营者旅程（商业化闭环）**：注册并创建 Organization → 通过 `UserController.Invite()` 邀请团队成员并分配角色 → 创建 Project 并Config模型价格（`ModelController.Get` 支持项目专属模型与预定义模型）[API/Controllers/DataManagement/ModelController.cs:34] → 通过 `POST /api/payment/order` 发起订阅购买，选择微信或Payment宝Payment [API/Controllers/PaymentManagement/OrderController.cs:48] → Payment回调成功后自动更新组织权益。

rder` 发起订阅购买，选择微信或Payment宝Payment [API/Controllers/PaymentManagement/OrderController.cs:48] → Payment回调成功后自动更新组织权益。

**AlertConfig**：进入 Alert Config页面 → 通过 `POST /api/alert` 创建Alert规则，指定 AlertField（如 TotalTokens）、AlertOperator（如 GreaterThan）、阈值及时间窗口 [API/Controllers/UserManagement/AlertController.cs:61] → Alert规则进入评估循环，`AlertService` 按时间窗口计算指标并判断条件是否满足 → 触发后通过系统通知或短信Alert，运维人员可在 `GET /api/alert/record` 查看Alert记录并标记已读 [API/Controllers/UserManagement/AlertController.cs:128]。

**集成者旅程（API Key 接入）**：通过 `POST /api/user/apikey` 创建 API Key [API/Controllers/UserManagement/UserController.cs:209] → 在外部系统中Config Basic Auth 或 JWT 认证 → 通过 `/api/public/{**catch-all}` 代理上报 Trace 数据，由 `AgentInsightTransformProvider` 完成 API Key 验证与用户身份解析 [API/System/Handlers/AgentInsightTransformProvider.cs:18]。

---

## 3. 功能需求

- **用户故事**: 作为平台用户，我希望通过手机号/邮箱注册账号，以便获得系统访问凭证。
- **主流程**:
  1. 客户端调用 `POST /api/user` 接口，携带 `UserBody`（含 `Mobile`、`Password`、`Name`、`CaptchaCode`）[API/Controllers/UserManagement/UserController.cs:43]。
  2. `UserHandler.CreateUser` 首先调用 `_captchaService.ExamineCaptcha` 校验图形Captcha [API/Handlers/UserManagement/UserHandler.cs:26]。
  3. Captcha通过后调用 `_userService.CreateNewUser` 创建用户，并通过 `_userService.LogUserSession` 记录登录Session [API/Handlers/UserManagement/UserHandler.cs:27]。
  4. 记录审计日志 `LogAudit(AuditAction.Create, AuditResourceType.User, user.Id)` [API/Handlers/UserManagement/UserHandler.cs:28]。
- **验收标准**:
  - [ ] AC1: 注册成功后返回 `errorCode=0`，响应体包含 `User` 对象（含 `id`、`token`、`sessionid` 字段）。
  - [ ] AC2: 手机号已存在时返回 `errorCode=100003`（`ExistedMobile`）。
  - [ ] AC3: Captcha错误时返回 `errorCode=110003`（`InvalidCaptcha`）。
- **业务规则**:
  - BR-001: Captcha有效期 300 秒，重发间隔 60 秒（`CaptchaSetting.ExpiredSeconds=300`、`CaptchaSetting.ResendInterval=60`）。

#### 3.1.1. FR-002 用户登录 [优先级: Must]

- **用户故事**: 作为平台用户，我希望通过密码、短信、微信、小程序或 API Key 方式登录，以便安全访问系统资源。
- **主流程**:
  1. 客户端调用 `POST /api/user/login` 接口，携带 `UserBody`（含 `LoginType`）[API/Controllers/UserManagement/UserController.cs:73]。
  2. `UserHandler.Login` 根据 `LoginType` 分发：`Password`、`SMS`、`WeChat`、`MiniProgram`、`APIKey` [API/Handlers/UserManagement/UserHandler.cs:38]。
  3. 当 `LoginType=APIKey` 时，从 `Authorization` 头解析 Basic Auth 凭据（`publicKey:secretKey`），查询 `AgentInsightAPISecretKey` 表验证密钥 [API/Handlers/UserManagement/UserHandler.cs:39-L45]。
  4. 登录成功后返回用户信息，JWT Token写入响应头 `access-token`。
- **验收标准**:
  - [ ] AC1: 密码登录成功时返回 `errorCode=0`，响应头包含 `access-token`，JWT 过期时间为 43200 秒（`JWTSettings.ExpiredTime=43200`）。
  - [ ] AC2: API Key 认证失败时返回 `errorCode=100037`（`InvalidCredentials`）或 `errorCode=100038`（`InvalidApiKey`）。
  - [ ] AC3: 未授权访问受保护端点时返回 `errorCode=100000`（`UnAuthToken`）。
- **业务规则**:
  - BR-002: JWT 使用 HS256 签名算法（`JWTSettings.Algorithm=HS256`），验证签发者与受众（`ValidateIssuer=True`、`ValidateAudience=True`）。

用 HS256 签名算法（`JWTSettings.Algorithm=HS256`），验证签发者与受众（`ValidateIssuer=True`、`ValidateAudience=True`）。

#### 3.1.2. FR-003 用户信息查询与更新 [优先级: Should]

- **用户故事**: 作为登录用户，我希望查看和修改个人资料（姓名、头像），以便维护最新个人信息。
- **主流程**:
  1. 客户端调用 `GET /api/user` 获取当前用户信息，`UserHandler.GetUser` 通过 `_userService.GetUserByUserId(User.Id)` 查询 [API/Handlers/UserManagement/UserHandler.cs:22]。
  2. 客户端调用 `POST /api/user/update` 更新资料，`UserHandler.UpdateUser` 仅更新 `Name` 和 `Image` 字段 [API/Handlers/UserManagement/UserHandler.cs:31-L33]。
- **验收标准**:
  - [ ] AC1: 查询成功时返回 `errorCode=0`，响应包含 `User` 对象（含 `name`、`image`、`mobile` 字段）。
  - [ ] AC2: 更新成功时返回 `errorCode=0`，且 `updatedat` 字段更新为当前 UTC 时间。
  - [ ] AC3: 用户名超过长度限制时返回 `errorCode=100019`（`UserNameTooLong`）。

#### 3.1.3. FR-004 用户登出 [优先级: Should]

- **用户故事**: 作为登录用户，我希望主动登出系统，以便结束当前Session。
- **主流程**:
  1. 客户端调用 `POST /api/user/logout`，`UserHandler.Logout` 使当前 Session 失效 [API/Controllers/UserManagement/UserController.cs:88]。
- **验收标准**:
  - [ ] AC1: 登出成功时返回 `errorCode=0`，响应体为空数据。
  - [ ] AC2: 登出后使用原 JWT 访问受保护端点返回 `errorCode=100000`（`UnAuthToken`）。

#### 3.1.4. FR-005 重置密码 [优先级: Should]

- **用户故事**: 作为平台用户，我希望通过短信Captcha重置密码，以便在忘记密码时恢复访问。
- **主流程**:
  1. 客户端调用 `POST /api/user/resetpassword`，携带手机号和Captcha [API/Controllers/UserManagement/UserController.cs:102]。
  2. `UserHandler.ResetPassword` 校验Captcha后更新密码哈希。
- **验收标准**:
  - [ ] AC1: 重置成功时返回 `errorCode=0`。
  - [ ] AC2: 重置失败时返回 `errorCode=100040`（`ResetPasswordFailed`）。
  - [ ] AC3: 短信发送过于频繁时返回 `errorCode=110000`（`SendSMSTooOften`）。

#### 3.1.5. FR-006 微信绑定与解绑 [优先级: Should]

- **用户故事**: 作为平台用户，我希望绑定或解绑微信账号，以便通过微信快捷登录。
- **主流程**:
  1. 客户端调用 `POST /api/user/bind/wechat`，`UserHandler.BindWeChat` 通过 code 或 openId 绑定 [API/Controllers/UserManagement/UserController.cs:117]。
  2. 客户端调用 `GET /api/user/unbind/wechat` 解绑微信 [API/Controllers/UserManagement/UserController.cs:132]。
- **验收标准**:
  - [ ] AC1: 绑定成功时返回 `errorCode=0`，用户信息中 `openid` 字段更新。
  - [ ] AC2: 微信账号已被其他用户绑定时返回 `errorCode=620010`（`WeChatAccountBeenBinded`）。
  - [ ] AC3: 解绑未绑定微信的账号返回 `errorCode=620011`（`WeChatAccountNotBinded`）。

#### 3.1.6. FR-007 API Key 管理 [优先级: Must]

- **用户故事**: 作为 API 集成者，我希望创建和管理 API Key，以便通过程序化方式访问系统。
- **主流程**:
  1. 客户端调用 `POST /api/user/apikey` 创建 API Key，`UserHandler.CreateApiKey` 生成 `publicKey` 和 `secretKey` 对 [API/Controllers/UserManagement/UserController.cs:209]。
  2. 客户端调用 `GET /api/user/apikey` 查询已创建的 API Key 列表 [API/Controllers/UserManagement/UserController.cs:225]。
  3. 客户端调用 `POST /api/user/apikey/delete` 删除指定 API Key [API/Controllers/UserManagement/UserController.cs:272]。
- **验收标准**:
  - [ ] AC1: 创建成功时返回 `errorCode=0`，响应包含 `publickey` 和 `secretkey` 字段。
  - [ ] AC2: API Key 不存在时返回 `errorCode=100031`（`ApiKeyNotFound`）。
  - [ ] AC3: 创建失败时返回 `errorCode=100032`（`CreateApiKeyFailed`）。

#### 3.1.7. FR-008 角色分配与成员邀请 [优先级: Should]

- **用户故事**: 作为组织管理员，我希望邀请成员并分配角色，以便协作管理组织资源。
- **主流程**:
  1. 客户端调用 `POST /api/user/invite` 邀请成员，`UserHandler.InviteMember` 创建邀请记录 [API/Controllers/UserManagement/UserController.cs:162]。
  2. 客户端调用 `POST /api/user/role` 分配角色，`UserHandler.AssignRole` 更新用户角色 [API/Controllers/UserManagement/UserController.cs:147]。
  3. 客户端调用 `GET /api/user/invitation` 查询邀请列表，`POST /api/user/invitation/delete` 删除邀请 [API/Controllers/UserManagement/UserController.cs:177,192]。
- **验收标准**:
  - [ ] AC1: 邀请成功时返回 `errorCode=0`，邀请记录进入待接受状态。
  - [ ] AC2: 被邀请用户已是组织成员时返回 `errorCode=100024`（`UserAlreadyOrgMember`）。
  - [ ] AC3: 分配高于自身角色时返回 `errorCode=100023`（`CannotGrantHigherRole`）。
  - [ ] AC4: OWNER 不能修改自身角色，返回 `errorCode=100039`（`OwnerCannotModifySelfRole`）。

#### 3.1.8. FR-009 月度 Agent 配额扣减与校验 [优先级: Should]

- **用户故事**: 作为组织管理员，我希望扣减和校验月度 Agent 配额，以便控制资源使用量。
- **主流程**:
  1. 客户端调用 `GET /api/user/privilege/agent/deduct` 扣减配额，`UserHandler.DeductMonthlyAgentRate` 更新组织配额 [API/Controllers/UserManagement/UserController.cs:242]。
  2. 客户端调用 `GET /api/user/privilege/agent/validate` 校验配额 [API/Controllers/UserManagement/UserController.cs:258]。
- **验收标准**:
  - [ ] AC1: 扣减成功时返回 `errorCode=0`。
  - [ ] AC2: 配额不足时返回 `errorCode=150007`（`AgentLimitExceeded`）。
  - [ ] AC3: 扣减失败时返回 `errorCode=150020`（`UpdateAgentRateFailed`）。

### 3.2. 组织与项目管理

#### 3.2.1. FR-010 组织创建 [优先级: Must]

- **用户故事**: 作为平台用户，我希望创建组织，以便建立多租户隔离空间。
- **主流程**:
  1. 客户端调用 `POST /api/user/organization`，携带组织名称 [API/Controllers/UserManagement/OrganizationController.cs:28]。
  2. `OrganizationHandler.CreateOrganization` 创建组织并将当前用户设为 OWNER。
- **验收标准**:
  - [ ] AC1: 创建成功时返回 `errorCode=0`，响应包含 `Organization` 对象。
  - [ ] AC2: 组织名为空时返回 `errorCode=130000`（`EmptyOrganizationName`）。
  - [ ] AC3: 组织名过短（<2字符）时返回 `errorCode=130001`（`OrganizationNameTooShort`）。
  - [ ] AC4: 组织名过长（>50字符）时返回 `errorCode=130002`（`OrganizationNameTooLong`）。

#### 3.2.2. FR-011 组织查询 [优先级: Must]

- **用户故事**: 作为组织成员，我希望查询我所属的组织列表，以便切换工作空间。
- **主流程**:
  1. 客户端调用 `GET /api/user/organization`，`OrganizationHandler.GetOrganizations` 返回当前用户所属组织 [API/Controllers/UserManagement/OrganizationController.cs:42]。
- **验收标准**:
  - [ ] AC1: 查询成功时返回 `errorCode=0`，响应包含组织列表。
  - [ ] AC2: 未授权访问组织时返回 `errorCode=130009`（`UnauthorizedOrganizationAccess`）。

#### 3.2.3. FR-012 组织更新与删除 [优先级: Should]

- **用户故事**: 作为组织 OWNER，我希望更新或删除组织，以便维护组织信息。
- **主流程**:
  1. 客户端调用 `POST /api/user/organization/update` 更新组织信息 [API/Controllers/UserManagement/OrganizationController.cs:56]。
  2. 客户端调用 `POST /api/user/organization/delete` 删除组织 [API/Controllers/UserManagement/OrganizationController.cs:71]。
- **验收标准**:
  - [ ] AC1: 更新成功时返回 `errorCode=0`。
  - [ ] AC2: 仅 OWNER 可执行删除操作，否则返回 `errorCode=130009`（`UnauthorizedOrganizationAccess`）。
  - [ ] AC3: 组织下存在项目时删除返回 `errorCode=130007`（`OrganizationHasProjects`）。
  - [ ] AC4: 组织正在删除项目中时返回 `errorCode=130008`（`OrganizationProjectDeleting`）。

#### 3.2.4. FR-013 项目创建 [优先级: Must]

- **用户故事**: 作为组织成员，我希望在组织下创建项目，以便隔离不同 Agent 的可Observation性数据。
- **主流程**:
  1. 客户端调用 `POST /api/user/project`，携带项目名称和所属组织 ID [API/Controllers/UserManagement/ProjectController.cs:31]。
  2. `ProjectHandler.CreateProject` 校验组织Privilege后创建项目。
- **验收标准**:
  - [ ] AC1: 创建成功时返回 `errorCode=0`，响应包含 `Project` 对象。
  - [ ] AC2: 项目名为空时返回 `errorCode=140000`（`EmptyProjectName`）。
  - [ ] AC3: 项目名重复时返回 `errorCode=140007`（`ExistedProjectName`）。
  - [ ] AC4: 超出组织项目数限制时返回 `errorCode=130011`（`ExceedProjectLimit`）。

#### 3.2.5. FR-014 项目查询、更新与删除 [优先级: Should]

- **用户故事**: 作为项目成员，我希望查询、更新和删除项目，以便管理项目生命周期。
- **主流程**:
  1. 客户端调用 `GET /api/user/project` 查询项目列表 [API/Controllers/UserManagement/ProjectController.cs:46]。
  2. 客户端调用 `POST /api/user/project/update` 更新项目 [API/Controllers/UserManagement/ProjectController.cs:60]。
  3. 客户端调用 `POST /api/user/project/delete` 删除项目 [API/Controllers/UserManagement/ProjectController.cs:75]。
- **验收标准**:
  - [ ] AC1: 查询成功时返回 `errorCode=0`，响应包含项目列表。
  - [ ] AC2: 未授权访问项目时返回 `errorCode=140008`（`UnauthorizedProjectAccess`）。
  - [ ] AC3: 项目不存在时返回 `errorCode=140003`（`InvalidProject`）。

### 3.3. Payment订阅

#### 3.3.1. FR-015 产品与时长查询 [优先级: Must]

- **用户故事**: 作为付费用户，我希望查看可用产品和时长选项，以便选择合适订阅方案。
- **主流程**:
  1. 客户端调用 `GET /api/product` 获取产品列表，`ProductHandler.GetProducts` 返回所有产品 [API/Controllers/ProductManagement/ProductController.cs:26]。
  2. 客户端调用 `GET /api/product/duration` 获取时长列表 [API/Controllers/ProductManagement/ProductController.cs:38]。
- **验收标准**:
  - [ ] AC1: 查询成功时返回 `errorCode=0`，产品列表包含 `id`、`name`、`price`、`projectlimit`、`headcountlimit` 字段。
  - [ ] AC2: 时长列表包含 `id`、`name`、`quantity`、`discount` 字段。

#### 3.3.2. FR-016 下单 [优先级: Must]

- **用户故事**: 作为付费用户，我希望创建订单并选择Payment方式，以便完成订阅购买。
- **主流程**:
1. 客户端调用 `POST /api/payment/order`，携带 `AgentInsightOrderBody`（含 `orgid`、`productid`、`productdurationid`、`paymethod`、`subpaymethod`）[API/Controllers/PaymentManagement/OrderController.cs:48]。
2. `OrderHandler.PlaceOrder` 调用 `PaymentService.CreateOrder` 创建订单 [API/Handlers/PaymentManagement/OrderHandler.cs:10]。
3. 根据 `paymethod` 分发：微信Payment（`GetWeChatJSAPIResponse`/`GetNativeResponse`/`WeChatMiniProgramPay`）或Payment宝Payment（`GetAlipayInstantTrade`）[API/Common/Services/PaymentService.cs:18,30]。
- **验收标准**:
- [ ] AC1: 下单成功时返回 `errorCode=0`，响应包含 `orderno`、`state=1`（Created）、`codeurl`/`qrcode` 字段。
- [ ] AC2: 产品不存在时返回 `errorCode=810013`（`ProductNotExist`）。
- [ ] AC3: 产品时长不存在时返回 `errorCode=810014`（`ProductDurationNotExist`）。
- [ ] AC4: 不支持的Payment方式返回 `errorCode=810019`（`UnsupportedPayMethod`）。
- [ ] AC5: Payment宝连接异常时返回 `errorCode=810003`（`AlipayConnectionError`）。
- **业务规则**:

- BR-003: 下单接口限流 1 次/10 秒（`[RateLimit(maxRequests: 1, windowSeconds: 10)]`）[API/Controllers/PaymentManagement/OrderController.cs:47]。
- BR-004: 微信Payment金额单位转换硬编码 `WeChatAmountUnit = 100` [API/Common/Services/PaymentService.cs:8]。

#### 3.3.3. FR-017 订单查询 [优先级: Must]

- **用户故事**: 作为付费用户，我希望查询订单状态，以便确认Payment结果。
- **主流程**:
  1. 客户端调用 `GET /api/payment/order/query?orderNo=xxx` 查询订单状态 [API/Controllers/PaymentManagement/OrderController.cs:64]。
  2. `OrderHandler.QueryOrder` 返回订单当前状态。
- **验收标准**:
  - [ ] AC1: 查询成功时返回 `errorCode=0`，响应包含 `orderno`、`state`、`tradestate` 字段。
  - [ ] AC2: 订单号为空时返回 `errorCode=810011`（`EmptyOrderNo`）。
  - [ ] AC3: 订单不存在时返回 `errorCode=810015`（`OrderNotExist`）。

#### 3.3.4. FR-018 订单列表与转化率 [优先级: Should]

- **用户故事**: 作为组织管理员，我希望查看订单历史和转化率，以便分析订阅情况。
- **主流程**:
  1. 客户端调用 `GET /api/payment/order?orgId=xxx` 获取订单列表 [API/Controllers/PaymentManagement/OrderController.cs:34]。
  2. 客户端调用 `GET /api/payment/order/conversion` 获取转化率 [API/Controllers/PaymentManagement/OrderController.cs:79]。
- **验收标准**:
  - [ ] AC1: 查询成功时返回 `errorCode=0`，订单列表包含 `orderno`、`productname`、`totalamount`、`orderstate` 字段。
  - [ ] AC2: 非组织成员查询时返回 `errorCode=810012`（`DoNotOwnOrganization`）。

#### 3.3.5. FR-019 Payment回调处理 [优先级: Must]

- **用户故事**: 作为系统，我希望处理微信和Payment宝异步回调，以便自动更新订单状态和组织权益。
- **主流程**:
  1. 微信调用 `POST /api/payment/notify/wechatnotify`，`NotifyHandler.ExamineWeChatRequest` 验证签名 [API/Controllers/PaymentManagement/NotifyController.cs:29]。
  2. Payment宝调用 `POST /api/payment/notify/alipaynotify`，`NotifyHandler.ExamineAlipaySignature` 验证签名 [API/Controllers/PaymentManagement/NotifyController.cs:57]。
  3. 验证通过后 `NotifyHandler.ProcessWeChatNotify`/`ProcessAlipayNotify` 更新订单状态，调用 `PaymentService.UpdateOrgPrivilege` 更新组织权益 [API/Common/Services/PaymentService.cs:20]。
- **验收标准**:
  - [ ] AC1: 微信回调请求体为空时返回 `errorCode=620014`（`FakedWeChatRequest`）。
  - [ ] AC2: 微信签名验证失败时返回 `errorCode=620002`（`ExamineWeChatSignatureFailed`）。
  - [ ] AC3: Payment宝签名验证失败时返回 `errorCode=810007`（`AlipaySignatureError`）。
  - [ ] AC4: 订单状态更新失败时返回 `errorCode=810026`（`OrderStateUpdateFailed`）。

### 3.4. 可Observation性 (Trace/Observation/Score)

#### 3.4.1. FR-020 Trace 列表查询 [优先级: Must]

- **用户故事**: 作为开发者，我希望通过多维度过滤条件查询 Trace 列表，以便分析 Agent 执行链路。
- **主流程**:
1. 客户端调用 `GET /api/data/metrics/traces` 或 `POST /api/data/metrics/traces`（POST 支持复杂过滤体）[API/Controllers/DataManagement/MetricsController.cs:64,125]。
2. `MetricsHandler.GetTraces` 首先通过 `ResolveProjectId` 解析项目 ID [API/Handlers/DataManagement/MetricsHandler.cs:30]。
3. 调用 `TraceFilterBuilder.BuildFilters` 构建过滤条件 [API/Common/Helpers/TraceFilterBuilder.cs:30]。
4. 通过 `_chdb.Queryable<TraceMetrics>()` 查询 ClickHouse 数据库 [API/Handlers/DataManagement/MetricsHandler.cs:12]。
- **验收标准**:
- [ ] AC1: 查询成功时返回 `errorCode=0`，响应包含 `items` 和 `totalCount` 字段。
- [ ] AC2: 未提供 `orgId` 和 `projectId` 时返回 `errorCode=150019`（`OrgAndProjectBothEmpty`）。
- [ ] AC3: 过滤类型无效时返回 `errorCode=150012`（`InvalidFilterType`）。
- [ ] AC4: 过滤列无效时返回 `errorCode=150013`（`InvalidFilterColumn`）。
- [ ] AC5: ClickHouse 查询超时返回 `errorCode=150017`（`ClickHouseQueryTimeout`）。
- **业务规则**:

- BR-005: 支持 25 个 `FilterColumn`（`Id`、`Name`、`Timestamp`、`UserId`、`SessionId`、`Environment`、`Version`、`Release`、`Tags`、`Bookmarked`、`Latency`、`InputTokens`、`OutputTokens`、`TotalTokens`、`Tokens`、`InputCost`、`OutputCost`、`TotalCost`、`Level`、`WarningCount`、`ErrorCount`、`DefaultCount`、`DebugCount`、`ModelNames`、`ScoresAvg`）[Models/Common/Enums/FilterEnum.cs:40]。
- BR-006: 支持 7 种 `FilterType`（`DateTime`、`String`、`Number`、`StringOptions`、`ArrayOptions`、`Boolean`、`Null`）[Models/Common/Enums/FilterEnum.cs:8]。
- BR-007: 支持 15 种 `FilterOperator`（`GreaterThan`、`LessThan`、`GreaterThanOrEqualTo`、`LessThanOrEqualTo`、`EqualTo`、`Contains`、`DoesNotContain`、`StartsWith`、`EndsWith`、`AnyOf`、`NoneOf`、`AllOf`、`NotEqualTo`、`IsNull`、`IsNotNull`）[Models/Common/Enums/FilterEnum.cs:20]。

#### 3.4.2. FR-021 Observation 查询 [优先级: Must]

- **用户故事**: 作为开发者，我希望查询指定 Trace 下的 Observation 详情，以便深入分析 Agent 内部执行步骤。
- **主流程**:
  1. 客户端调用 `GET /api/data/metrics/observations?traceId=xxx` [API/Controllers/DataManagement/MetricsController.cs:34]。
  2. `MetricsHandler.GetObservationsAsync` 校验 `traceId` 非空，按 `StartTime` 排序分页查询 [API/Handlers/DataManagement/MetricsHandler.cs:26]。
- **验收标准**:
  - [ ] AC1: 查询成功时返回 `errorCode=0`，响应包含 `Observation` 列表（含 `traceid`、`starttime`、`type` 字段）。
  - [ ] AC2: `traceId` 为空时返回 `errorCode=150018`（`EmptyTraceId`）。
  - [ ] AC3: ClickHouse 查询错误时返回 `errorCode=150010`（`ClickHouseQueryError`）。

#### 3.4.3. FR-022 Score 查询 [优先级: Must]

- **用户故事**: 作为开发者，我希望查询 Trace 关联的 Score Score数据，以便评估 Agent 输出质量。
- **主流程**:
  1. 客户端调用 `GET /api/data/metrics/scores?traceId=xxx` [API/Controllers/DataManagement/MetricsController.cs:50]。
  2. `MetricsHandler.GetScoresAsync` 校验 `traceId` 非空，按 `CreatedAt` 排序分页查询 [API/Handlers/DataManagement/MetricsHandler.cs:28]。
- **验收标准**:
  - [ ] AC1: 查询成功时返回 `errorCode=0`，响应包含 `Score` 列表（含 `traceid`、`name`、`value` 字段）。
  - [ ] AC2: `traceId` 为空时返回 `errorCode=150018`（`EmptyTraceId`）。
  - [ ] AC3: ClickHouse 查询超时返回 `errorCode=150017`（`ClickHouseQueryTimeout`）。

#### 3.4.4. FR-023 模型列表查询 [优先级: Should]

- **用户故事**: 作为开发者，我希望查询模型列表，以便了解可用模型及定价。
- **主流程**:
  1. 客户端调用 `GET /api/data/model`，携带可选参数 `keyword`、`projectid`、`includedpredefined` [API/Controllers/DataManagement/ModelController.cs:34]。
  2. `ModelHandler.Get` 返回模型列表，支持按 `orderby` 排序（默认 `-updatedat`）。
- **验收标准**:
  - [ ] AC1: 查询成功时返回 `errorCode=0`，响应包含 `ModelDefinition` 列表（含 `modelname`、`inputprice`、`outputprice` 字段）。
  - [ ] AC2: `projectid` 为空且 `includedpredefined=false` 时返回错误（要求提供项目 ID）。

### 3.5. AlertConfig与通知

#### 3.5.1. FR-024 Alert规则创建 [优先级: Should]

- **用户故事**: 作为运维人员，我希望创建基于 Token 用量、延迟、错误率等指标的Alert规则，以便及时发现异常。
- **主流程**:
  1. 客户端调用 `POST /api/alert`，携带Alert规则Config [API/Controllers/UserManagement/AlertController.cs:61]。
  2. `AlertHandler.CreateAlert` 校验规则参数后创建Alert规则。
- **验收标准**:
  - [ ] AC1: 创建成功时返回 `errorCode=0`，响应包含Alert规则 ID。
  - [ ] AC2: Alert字段无效时返回 `errorCode=160006`（`InvalidAlertField`）。
  - [ ] AC3: Alert操作符无效时返回 `errorCode=160007`（`InvalidAlertOperator`）。
  - [ ] AC4: Alert值无效时返回 `errorCode=160008`（`InvalidAlertValue`）。
  - [ ] AC5: Alert名称过长时返回 `errorCode=160015`（`AlertNameTooLong`）。
- **业务规则**:
  - BR-008: 支持 9 种 `AlertField`（`TotalTokens`、`TotalCost`、`ErrorCount`、`Latency`、`ErrorRate`、`InputTokens`、`OutputTokens`、`WarningCount`、`ObservationCount`）[Models/Common/Enums/AlertEnum.cs:20]。
  - BR-009: 支持 6 种 `AlertOperator`（`GreaterThan`、`LessThan`、`EqualTo`、`GreaterThanOrEqualTo`、`LessThanOrEqualTo`、`NotEqualTo`）[Models/Common/Enums/AlertEnum.cs:10]。

#### 3.5.2. FR-025 Alert规则查询与更新 [优先级: Should]

- **用户故事**: 作为运维人员，我希望查询和更新Alert规则，以便调整监控策略。
- **主流程**:
  1. 客户端调用 `GET /api/alert` 查询Alert规则列表 [API/Controllers/UserManagement/AlertController.cs:47]。
  2. 客户端调用 `POST /api/alert/update` 更新Alert规则 [API/Controllers/UserManagement/AlertController.cs:75]。
- **验收标准**:
  - [ ] AC1: 查询成功时返回 `errorCode=0`，响应包含Alert规则列表。
  - [ ] AC2: 更新不存在的规则时返回 `errorCode=160000`（`AlertNotFound`）。
  - [ ] AC3: 更新失败时返回 `errorCode=160002`（`UpdateAlertFailed`）。

#### 3.5.3. FR-026 Alert规则删除 [优先级: Should]

- **用户故事**: 作为运维人员，我希望删除不再需要的Alert规则，以便减少无效通知。
- **主流程**:
  1. 客户端调用 `POST /api/alert/delete` 删除Alert规则 [API/Controllers/UserManagement/AlertController.cs:90]。
- **验收标准**:
  - [ ] AC1: 删除成功时返回 `errorCode=0`。
  - [ ] AC2: 删除不存在的规则时返回 `errorCode=160000`（`AlertNotFound`）。
  - [ ] AC3: 删除失败时返回 `errorCode=160003`（`DeleteAlertFailed`）。

#### 3.5.4. FR-027 Alert记录查询与已读 [优先级: Should]

- **用户故事**: 作为运维人员，我希望查看Alert记录并标记已读，以便跟踪处理状态。
- **主流程**:
  1. 客户端调用 `GET /api/alert/record` 查询Alert记录 [API/Controllers/UserManagement/AlertController.cs:128]。
  2. 客户端调用 `POST /api/alert/record/read` 标记记录为已读 [API/Controllers/UserManagement/AlertController.cs:108]。
- **验收标准**:
  - [ ] AC1: 查询成功时返回 `errorCode=0`，记录包含 `state` 字段（`Active=1`/`Read=2`）。
  - [ ] AC2: 标记已读成功时返回 `errorCode=0`，记录状态更新为 `Read`。

#### 3.5.5. FR-028 Alert评估与通知 [优先级: Should]

- **用户故事**: 作为系统，我希望定期评估Alert条件并在触发时发送通知，以便及时告知运维人员。
- **主流程**:
  1. `AlertService` 通过 `GetTimeSpan` 计算时间窗口 [API/Common/Services/AlertService.cs]。
  2. 通过 `IsConditionMet` 判断指标是否满足条件 [API/Common/Services/AlertService.cs]。
  3. 触发后通过 `BuildAlertMessage` 构建消息，经 `SystemAlertHandler`（系统通知）或 `SMSAlertHandler`（短信通知）发送 [API/Notifications/SystemAlertHandler.cs]。
- **验收标准**:
  - [ ] AC1: Alert触发时生成 `AlertRecordState.Active` 记录。
  - [ ] AC2: 通知方式为 `System` 时写入系统通知，为 `SMS` 时调用短信服务。
  - [ ] AC3: Alert通知方式无效时返回 `errorCode=160011`（`InvalidAlertNotifyBy`）。

ystem` 时写入系统通知，为 `SMS` 时调用短信服务。
  - [ ] AC3: Alert通知方式无效时返回 `errorCode=160011`（`InvalidAlertNotifyBy`）。

### 3.6. Agent 运行时 (Agents 子项目)

#### 3.6.1. FR-029 Chat Completions API [优先级: Must]

- **用户故事**: 作为 Agent 开发者，我希望通过 OpenAI 兼容接口调用 Agent Service，以便集成 AI 能力。
- **主流程**:
  1. 客户端调用 `POST /api/agent/insight`，携带 OpenAI 格式的请求体（`model`、`messages`、`stream`）[Agents/server.py:346]。
  2. `chat_completions` 函数解析请求，通过 `InsightOrchestrator` 路由到对应子 Agent（Researcher、CustomService 等）。
  3. SSE与非流式响应，流式通过 `asyncio.Queue` 实现 token 级输出 [Agents/server.py:430]。
- **验收标准**:
  - [ ] AC1: 非流式请求返回 `errorCode=0`，响应包含 `choices` 数组（含 `message` 和 `finish_reason`）。
  - [ ] AC2: 流式请求返回 SSE 格式，每个 chunk 包含 `choices[0].delta.content` 字段。
  - [ ] AC3: 无效请求参数时返回 HTTP 400 错误。
- **业务规则**:
  - BR-010: 首 token 延迟 <800ms [Agents/server.py:430]。

#### 3.6.2. FR-030 Session管理 [优先级: Should]

- **用户故事**: 作为 Agent 开发者，我希望管理Session（列表、详情、删除、清理），以便维护对话上下文。
- **主流程**:
  1. 客户端调用 `GET /api/sessions` 获取Session列表 [Agents/server.py:614]。
  2. 客户端调用 `GET /api/sessions/{session_id}` 获取Session详情 [Agents/server.py:622]。
  3. 客户端调用 `DELETE /api/sessions/{session_id}` 删除Session [Agents/server.py:633]。
  4. 客户端调用 `POST /api/sessions/cleanup` 清理过期Session [Agents/server.py:641]。
- **验收标准**:
  - [ ] AC1: Session列表返回 `errorCode=0`，包含Session ID 和创建时间。
  - [ ] AC2: Session不存在时返回 `errorCode=150021`（`AgentSessionNotFound`）。

---

## 4. 非功能需求

AgentInsightService 是一个面向 AI Agent 的可Observation性与运营管理平台，提供 Trace、Observation、Score 等数据模型的采集、存储、查询与分析能力，并支持 Organization → Project 两级租户模型及完整的 SaaS 运营功能。NFR，涵盖性能、可用性、安全、可扩展性、可维护性、兼容性与本地化七个维度。所有 NFR 采用 `NFR-{CATEGORY}-{NNN}` 格式编号，共计 20 条，具体规格与验收标准如下表所示。

| 编号 | 类别 | 需求描述 | 验收标准 | 代码/Config佐证 |
|------|------|----------|----------|----------------|
| NFR-PERF-001 | 性能 | ClickHouse 连接池容量 | `PoolSize=10;MaxPoolSize=50`，连接超时 30s，命令超时 60s | `API/appsettings.json` ClickHouseDbConnection |
| NFR-PERF-002 | 性能 | PostgreSQL 连接池容量 | `MinPoolSize=10;MaxPoolSize=200`，连接生命周期 300s，命令超时 30s | `API/appsettings.json` UserDbConnection/DataDbConnection/TrackingDbConnection |
| NFR-PERF-003 | 性能 | Agents 流式响应首 token 延迟 | 首 token 延迟 < 800ms，通过 `asyncio.Queue` 实现 token 级流式输出 | `Agents/server.py:430` |
| NFR-PERF-004 | 性能 | Trace 查询超时控制 | 查询超时 60s（基于 `CommandTimeout=60`），超时返回 `ClickHouseQueryTimeout` (150017) | `API/appsettings.json` ClickHouseDbConnection；`Models/Common/Enums/ExceptionCodes.cs:6` |
| NFR-AVAIL-001 | 可用性 | Redis 高可用Config | Redis 连接字符串支持哨兵模式，`BullMqService` 基于 Redis 实现可靠消息队列 | `API/appsettings.json` Redis.ConnectionString；`API/Common/Services/BullMqService.cs` |
| NFR-AVAIL-002 | 可用性 | 消息队列可靠性 | Trace 异步摄入与项目删除任务通过 BullMQ 队列保障，任务持久化至 Redis | `API/Common/Services/BullMqService.cs` |
| NFR-AVAIL-003 | 可用性 | ClickHouse 查询异常降级 | 查询异常时返回 `ClickHouseQueryError` (150010) 或 `ClickHouseQueryTimeout` (150017)，不导致服务崩溃 | `Models/Common/Enums/ExceptionCodes.cs:6` |
| NFR-SEC-001 | 安全 | JWT 认证 | HS256 算法，过期时间 43200s，`ValidateIssuer`/`ValidateAudience` 开启，ClockSkew 5s | `API/appsettings.json` JWTSettings |
| NFR-SEC-002 | 安全 | API Key 认证 | 支持 Basic Auth 与 JWT 两种方式，由 `AgentInsightTransformProvider` 处理，无效凭据返回 `InvalidCredentials` (100037) / `InvalidApiKey` (100038) | `API/System/Handlers/AgentInsightTransformProvider.cs:18` |
| NFR-SEC-003 | 安全 | 敏感数据加密存储 | 使用 AES 加密，密钥通过 `AESEncryptionKey`（`${AES_KEY}` 环境变量）注入 | `API/appsettings.json` AESEncryptionKey |
| NFR-SEC-004 | 安全 | 角色访问控制 | `RequireOrgMembership` 强制最低角色（VIEWER/MEMBER/ADMIN/OWNER），`RequireOrgOwner` 限制仅 OWNER 可执行 | `API/Handlers/ApiHandlerBase.cs:27-29` |
| NFR-SEC-005 | 安全 | Payment签名验证 | 微信与Payment宝回调必须通过签名验证（`ExamineAlipaySignature` / `ExamineSignature`），失败返回 `ExamineWeChatSignatureFailed` (620002) / `AlipaySignatureError` (810007) | `API/Common/Services/PaymentService.cs:24`；`API/Common/Services/WeChatService.cs:14` |
| NFR-SCALE-001 | 可扩展性 | 反向代理扩展 | YARP 反向代理支持 `/api/public/{**catch-all}` 与 `/public/{**catch-all}` 路由，代理至 Langfuse 兼容后端 | `API/appsettings.json` ReverseProxy |
| NFR-SCALE-002 | 可扩展性 | 动态Config调整 | 连接池大小、日志级别可通过Config文件动态调整，无需重新编译 | `API/appsettings.json` ConnectionStrings/Logging |
| NFR-MAINT-001 | 可维护性 | 统一异常处理 | `ExceptionMiddleware` 统一处理异常，`ExceptionCodes` 定义 100+ 错误码 | `API/System/Handlers/ExceptionMiddleware.cs`；`Models/Common/Enums/ExceptionCodes.cs:6` |
| NFR-MAINT-002 | 可维护性 | 审计日志 | `ApiHandlerBase.LogAudit()` 记录关键操作，审计动作覆盖 Create/Update/Delete/Login/Logout 等 | `API/Handlers/ApiHandlerBase.cs:34`；`Models/Common/Enums/AuditEnum.cs:3` |
| NFR-MAINT-003 | 可维护性 | 模块解耦 | MediatR 解耦Payment交易保存、微信回调、Alert通知等异步事件处理 | `API/Notifications/PaymentTransactionSaveHandler.cs:10` |
| NFR-COMP-001 | 兼容性 | 运行时版本 | API 目标运行时 .NET 6/8+，Agents Service Python 3.11+ | `API/appsettings.json`；`Agents/pyproject.toml` |
| NFR-COMP-002 | 兼容性 | 依赖库版本 | 依赖 Npgsql、StackExchange.Redis、Yarp.ReverseProxy 等稳定版本 | `API/appsettings.json` |
| NFR-L10N-001 | 本地化 | 多语言支持 | 默认 `zh-CN`，支持 `zh-TW`、`zh-HK`、`en`，通过 `My.Extensions.Localization.Json` 实现 | `API/appsettings.json` LocalizationSettings |

### 4.1. 性能

性能需求聚焦于数据存储层连接池容量、Agent 流式响应延迟与查询超时控制。系统采用 ClickHouse 作为 Trace 数据存储，连接池Config为 `PoolSize=10;MaxPoolSize=50`，连接超时 30s，命令超时 60s，确保高并发写入与查询场景下的连接复用效率 [API/appsettings.json]。PostgreSQL 作为用户与业务数据存储，三个连接串（UserDbConnection、DataDbConnection、TrackingDbConnection）均Config `MinPoolSize=10;MaxPoolSize=200`，连接生命周期 300s，命令超时 30s，支撑多租户场景下的用户认证、组织管理与Payment订单等业务操作 [API/appsettings.json]。

Agents 子服务通过 `asyncio.Queue` 实现 token 级流式输出，首 token 延迟目标 < 800ms，确保 Chat Completions API 的实时交互体验 [Agents/server.py:430]。Trace 查询通过 ClickHouseClient 执行，查询超时由 `CommandTimeout=60` 控制，超时或异常时分别返回 `ClickHouseQueryTimeout` (150017) 与 `ClickHouseQueryError` (150010) 错误码，避免查询阻塞对 API 服务整体可用性造成影响 [Models/Common/Enums/ExceptionCodes.cs:6]。

### 4.2. 可用性

可用性需求确保系统在依赖组件异常时仍能提供核心服务。Redis 连接字符串支持哨兵模式Config，`BullMqService` 基于 Redis 实现消息队列，提供 Trace 异步摄入与项目删除任务的可靠投递与持久化 [API/Common/Services/BullMqService.cs]。消息队列采用 Lua 脚本保证任务入队的原子性，支持延迟任务与优先级排序，任务数据持久化至 Redis，防止服务重启导致任务丢失 [API/Common/Services/BullMqService.cs]。

当 ClickHouse 查询异常或超时时，系统通过 `ClickHouseQueryError` (150010) 与 `ClickHouseQueryTimeout` (150017) 错误码进行降级响应，确保 API 服务不因存储层故障而崩溃 [Models/Common/Enums/ExceptionCodes.cs:6]。Redis 不可用仅影响异步任务队列，不阻塞同步 API 请求处理。

### 4.3. 安全

安全需求覆盖认证、授权、加密与Payment安全四个层面。JWT 认证采用 HS256 算法，Token 过期时间 43200s（12 小时），`ValidateIssuer` 与 `ValidateAudience` 均开启，ClockSkew 允许 5s 时间偏差，防止 Token 重放攻击 [API/appsettings.json]。API Key 认证支持 Basic Auth 与 JWT 两种方式，由 `AgentInsightTransformProvider` 统一处理，无效凭据返回 `InvalidCredentials` (100037)，无效 API Key 返回 `InvalidApiKey` (100038) [API/System/Handlers/AgentInsightTransformProvider.cs:18]。

敏感数据（如 API Key 的 secretKey）通过 AES 加密存储，密钥由 `AESEncryptionKey` Config项注入（环境变量 `${AES_KEY}`），加密失败返回 `EncryptionFailed` (990001)，解密失败返回 `DecryptionFailed` (990002) [API/appsettings.json]。角色访问控制通过 `ApiHandlerBase` 的 `RequireOrgMembership` 与 `RequireOrgOwner` 方法实现，前者强制要求最低角色（VIEWER/MEMBER/ADMIN/OWNER），后者限制仅组织 OWNER 可执行敏感操作 [API/Handlers/ApiHandlerBase.cs:27-29]。Payment回调必须通过签名验证，微信签名验证失败返回 `ExamineWeChatSignatureFailed` (620002)，Payment宝签名验证失败返回 `AlipaySignatureError` (810007)，防止伪造Payment通知 [API/Common/Services/PaymentService.cs:24]。

### 4.4. 可扩展性

可扩展性需求确保系统能够通过Config扩展与动态调整应对业务增长。YARP 反向代理Config了 `AgentInsight-Route-API`（路径 `/api/public/{**catch-all}`）与 `AgentInsight-Route-Public`（路径 `/public/{**catch-all}`）两条路由，统一代理至 Langfuse 兼容后端（`AgentInsight-Langfuse-Cluster`），支持 Agent Trace 数据上报的横向扩展 [API/appsettings.json]。`AgentInsightTransformProvider` 在代理层完成认证转换与限流控制，新增代理路由无需修改业务代码 [API/System/Handlers/AgentInsightTransformProvider.cs:18]。

连接池大小、日志级别、Redis 连接串等关键参数均通过Config文件管理，支持在不同环境（Development/QA/LIVE）间切换，无需重新编译部署 [API/appsettings.json]。系统通过 `ConfigurationScanDirectories` Config支持从 `Configurations` 与 `Resources` 目录动态扫描Config文件，进一步提升Config灵活性 [API/appsettings.json]。

### 4.5. 可维护性

可维护性需求通过统一异常处理、审计日志与模块解耦保障系统的可运维性。`ExceptionMiddleware` 作为全局异常处理中间件，统一捕获并转换异常为标准化错误响应，`ExceptionCodes` 枚举定义 100+ 错误码，覆盖用户管理、组织项目、Payment、Alert、Agent 等全部业务域 [API/System/Handlers/ExceptionMiddleware.cs] [Models/Common/Enums/ExceptionCodes.cs:6]。审计日志通过 `ApiHandlerBase.LogAudit()` 记录关键操作，审计动作覆盖 Create、Update、Delete、Login、Logout、Reset、Bind、UnBind、Place、Query、Notify 等 11 种类型，审计资源类型涵盖 User、Organization、Project、Alert、ApiKey、Invitation、Order、WeChat、OrgPrivilege [API/Handlers/ApiHandlerBase.cs:34] [Models/Common/Enums/AuditEnum.cs:3]。

系统采用 MediatR 通知模式解耦异步事件处理，Payment交易保存（`PaymentTransactionSaveHandler`）、微信回调（`WeChatNotifyReceivedHandler`）、Alert触发（`SystemAlertHandler`）等均通过 MediatR 发布/订阅机制解耦，降低模块间耦合度，提升代码可测试性与可维护性 [API/Notifications/PaymentTransactionSaveHandler.cs:10]。

### 4.6. 兼容性

兼容性需求确保系统在目标运行时与依赖库版本下稳定运行。API 主服务基于 .NET 6/8+ 运行时，依赖 Npgsql（PostgreSQL 驱动）、StackExchange.Redis（Redis 客户端）、Yarp.ReverseProxy（反向代理）、SqlSugar（ORM）、Furion（应用框架）等稳定版本 [API/appsettings.json]。Agents 子服务基于 Python 3.11+，依赖 FastAPI、LangChain.Providers.OpenAI、Microsoft.SemanticKernel 等 AI 框架，`pyproject.toml` 中声明 `requires-python = >=3.11` [Agents/pyproject.toml]。Admin 子服务基于 Python/Django，与主服务通过 RESTful API 交互。

数据库兼容性方面，系统通过 `NpgsqlConnection.GlobalTypeMapper` 映射 `Role` 与 `ApiKeyScope` 枚举类型，确保 PostgreSQL 枚举类型与 C# 枚举的互操作 [API/System/Startup/Startup.cs]。启动时自动创建数据库与初始化表结构，兼容空库与已有库两种场景 [API/System/Startup/Startup.cs]。

### 4.7. 本地化

本地化需求确保系统支持多语言环境。`LocalizationSettings` Config默认文化为 `zh-CN`，支持 `zh-TW`、`zh-HK`、`en` 三种附加文化，语言文件前缀为 `Text`，通过 `My.Extensions.Localization.Json` 实现基于 JSON 的本地化资源管理 [API/appsettings.json]。系统启动时通过 `InitializeZhConverter` OpenCCNET，支持简体中文与繁体中文之间的转换，确保 `zh-CN`、`zh-TW`、`zh-HK` 三种中文文化的兼容 [API/System/Startup/Startup.cs]。

---

## 5. 接口需求

AgentInsightService 是一个面向 AI Agent 的可Observation性与运营管理平台，提供 Agent 可Observation性（Trace、Observation、Score 数据模型的全量采集、存储、查询与分析）与多租户运营管理（Organization → Project 两级租户模型，含用户管理、角色Privilege、Payment订阅、Bulletin系统、AlertConfig）两大核心能力。本章节定义系统全部 HTTP 接口需求，覆盖 76 个端点，按 Controller 分组描述各端点的路径、方法、鉴权方式、请求参数与错误码。所有端点均引用 v9 HTTP 端点全集与 ExceptionCodes 枚举清单作为唯一事实来源。

### 5.1. 认证与鉴权约定

系统统一采用 JWT Bearer Token 或 API Key (Basic Auth) 两种认证方式。`AgentInsightTransformProvider` 负责认证转换，处理 Basic Auth 和 JWT 两种认证方式，并执行 API Key 验证、限流与用户身份解析 [API/System/Handlers/AgentInsightTransformProvider.cs:18]。JWT Config定义于 `appsettings.json`，采用 HS256 算法，过期时间 43200 秒，签发者/受众验证均开启。登录接口（`POST /api/user/login`）在响应头中返回 `access-token`，后续请求需在 `Authorization` 头携带该 Token。API Key 登录（logintype=5）时，需在 `Authorization` 头携带 `Basic publickey:secretkey` 格式的凭证 [API/Controllers/UserManagement/UserController.cs:73]。

zation` 头携带 `Basic publickey:secretkey` 格式的凭证 [API/Controllers/UserManagement/UserController.cs:73]。

角色Privilege通过 `Role` 枚举定义四级角色：OWNER (4)、ADMIN (3)、MEMBER (2)、VIEWER (1)。`ApiHandlerBase` 提供 `RequireOrgMembership(string orgId, Role minRole)` 与 `RequireOrgOwner(string orgId)` 两个角色验证方法，分别强制要求最低角色与限制仅 OWNER 可执行操作 [API/Handlers/ApiHandlerBase.cs:27-29]。所有错误码引用 `ExceptionCodes` 枚举，如 `UnAuthToken = 100000`、`InvalidUser = 100005`、`UnauthorizedOperator = 100010` 等。

### 5.2. 用户管理接口 (UserController/UserConfigController/OrganizationController/ProjectController/CaptchaController)

用户管理接口共 31 个端点，覆盖用户生命周期管理、Org/项目多租户管理、Captcha服务。

**UserController** 提供 17 个端点，路由前缀为 `/api/user` [API/Controllers/UserManagement/UserController.cs:29-272]：

rController** 提供 17 个端点，路由前缀为 `/api/user` [API/Controllers/UserManagement/UserController.cs:29-272]：

| 方法 | 路径 | 鉴权 | 说明 |
|------|------|------|------|
| GET | /api/user | JWT | 获取当前登录用户信息 |
| POST | /api/user | 匿名 | 创建用户（注册），请求体含 mobile/password/name/captchacode |
| POST | /api/user/update | JWT | 更新用户信息（name/image） |
| POST | /api/user/login | 匿名 | 登录，logintype: 1=密码, 2=短信, 3=微信, 4=小程序, 5=APIKey |
| POST | /api/user/logout | JWT | 登出 |
| POST | /api/user/resetpassword | 匿名 | 重置密码，请求体含 mobile/captchaid |
| POST | /api/user/bind/wechat | JWT | 绑定微信账号 |
| GET | /api/user/unbind/wechat | JWT | 解绑微信账号 |
| POST | /api/user/role | JWT | 分配角色（组织或项目级） |
| POST | /api/user/invite | JWT | 邀请成员加入组织 |
| GET | /api/user/invitation | JWT | 获取邀请列表 |
| POST | /api/user/invitation/delete | JWT | 删除邀请 |
| POST | /api/user/apikey | JWT | 创建 API Key |
| GET | /api/user/apikey | JWT | 获取 API Key 列表 |
| GET | /api/user/privilege/agent/deduct | JWT | 扣减月度 Agent 配额 |
| GET | /api/user/privilege/agent/validate | JWT | 校验月度 Agent 配额 |
| POST | /api/user/apikey/delete | JWT | 删除 API Key |

ivilege/agent/validate | JWT | 校验月度 Agent 配额 |
| POST | /api/user/apikey/delete | JWT | 删除 API Key |

登录接口支持多种登录方式，`LoginType` 枚举定义于 [Models/Common/Enums/UserEnum.cs:25]。注册时若手机号已存在，返回 `ExistedMobile = 100003`；用户名超长返回 `UserNameTooLong = 100019`。API Key 相关错误码包括 `ApiKeyNotFound = 100031`、`CreateApiKeyFailed = 100032`、`DeleteApiKeyFailed = 100033`、`InvalidApiKey = 100038`。邀请成员时若手机号为空返回 `EmptyInviteMobile = 100021`，邀请已存在返回 `InviteAlreadyExists = 100025`。角色分配时若授予更高角色返回 `CannotGrantHigherRole = 100023`，OWNER 修改自身角色返回 `OwnerCannotModifySelfRole = 100039`。

**UserConfigController** 提供 4 个端点，路由前缀为 `/api/user/config` [API/Controllers/UserManagement/UserConfigController.cs:31-71]：

| 方法 | 路径 | 鉴权 | 说明 |
|------|------|------|------|
| GET | /api/user/config | JWT | 获取用户Config项，支持 orgId/projectId/type 过滤（type: 0=User, 1=Organization, 2=Project） |
| POST | /api/user/config | JWT | 创建用户Config |
| POST | /api/user/config/update | JWT | 更新用户Config |
| GET | /api/user/config/delete | JWT | 删除用户Config |

|
| POST | /api/user/config/update | JWT | 更新用户Config |
| GET | /api/user/config/delete | JWT | 删除用户Config |

Config类型由 `UserConfigType` 枚举定义。重复Config返回 `DuplicateUserConfig = 150008`。

**OrganizationController** 提供 4 个端点，路由前缀为 `/api/user/organization`：

| 方法 | 路径 | 鉴权 | 说明 |
|------|------|------|------|
| POST | /api/user/organization | JWT | 创建组织 |
| GET | /api/user/organization | JWT | 获取组织列表 |
| POST | /api/user/organization/update | JWT | 更新组织信息 |
| POST | /api/user/organization/delete | JWT | 删除组织 |

组织名校验：空名称返回 `EmptyOrganizationName = 130000`，过短返回 `OrganizationNameTooShort = 130001`，过长返回 `OrganizationNameTooLong = 130002`。删除组织时若存在项目返回 `OrganizationHasProjects = 130007`。创建组织需检查配额，超出限制返回 `ExceedOrgLimit = 130012`。

**ProjectController** 提供 4 个端点，路由前缀为 `/api/user/project`：

| 方法 | 路径 | 鉴权 | 说明 |
|------|------|------|------|
| POST | /api/user/project | JWT | 创建项目 |
| GET | /api/user/project | JWT | 获取项目列表 |
| POST | /api/user/project/update | JWT | 更新项目信息 |
| POST | /api/user/project/delete | JWT | 删除项目 |

项目名校验：空名称返回 `EmptyProjectName = 140000`，重名返回 `ExistedProjectName = 140007`。删除项目时若正在删除中返回 `OrganizationProjectDeleting = 130008`。

**CaptchaController** 提供 2 个端点，路由前缀为 `/api/captcha`：

| 方法 | 路径 | 鉴权 | 说明 |
|------|------|------|------|
| GET | /api/captcha | 匿名 | 获取图形Captcha |
| GET | /api/captcha/sms | 匿名 | 获取短信Captcha |

CaptchaConfig：`CaptchaSetting.CaptchaCodeLength = 5`、`SMSCodeLength = 6`、`ExpiredSeconds = 300`、`ResendInterval = 60`。发送过于频繁返回 `SendSMSTooOften = 110000`，Captcha为空返回 `EmptyCaptcha = 110002`，Captcha无效返回 `InvalidCaptcha = 110003`。

### 5.3. Payment管理接口 (OrderController/NotifyController/ProductController)

Payment管理接口共 8 个端点，覆盖订单创建/查询、Payment回调处理、产品与时长查询。

**OrderController** 提供 4 个端点，路由前缀为 `/api/payment/order`：

**MetricsController** 提供 4 个端点，路由前缀为 `/api/data/metrics`：

| 方法 | 路径 | 鉴权 | 说明 |
|------|------|------|------|
| GET | /api/data/metrics/observations | JWT | 查询 Observation 详情 |
| GET | /api/data/metrics/scores | JWT | 查询 Trace 关联的 Score 数据 |
| GET | /api/data/metrics/traces | JWT | 查询 Trace 列表（支持过滤/排序/分页） |
| POST | /api/data/metrics/traces | JWT | 查询 Trace 列表（POST 方式，支持复杂过滤条件） |

Trace 查询由 `MetricsHandler.GetTraces()` 实现 [API/Handlers/DataManagement/MetricsHandler.cs:30]，通过 `TraceFilterBuilder.BuildFilters()` 构建过滤条件 [API/Common/Helpers/TraceFilterBuilder.cs:30]，支持 7 种 `FilterType`（DateTime/String/Number/StringOptions/ArrayOptions/Boolean/Null）、15 种 `FilterOperator`、25 个 `FilterColumn`。查询执行依赖 `ClickHouseClient` [API/Common/Services/ClickHouseClient.cs]，连接池Config `PoolSize=10;MaxPoolSize=50;ConnectionTimeout=30;CommandTimeout=60`。

ices/ClickHouseClient.cs]，连接池Config `PoolSize=10;MaxPoolSize=50;ConnectionTimeout=30;CommandTimeout=60`。

Trace ID 为空返回 `EmptyTraceIds = 150009`，Trace ID 过多返回 `TooManyTraceIds = 150011`，过滤类型无效返回 `InvalidFilterType = 150012`，过滤列无效返回 `InvalidFilterColumn = 150013`，过滤操作符无效返回 `InvalidFilterOperator = 150014`，过滤值无效返回 `InvalidFilterValue = 150015`，排序方式无效返回 `InvalidOrderBy = 150016`，ClickHouse 查询超时返回 `ClickHouseQueryTimeout = 150017`。

**ModelController** 提供 1 个端点：

| 方法 | 路径 | 鉴权 | 说明 |
|------|------|------|------|
| GET | /api/data/model | JWT | 获取模型列表 |

模型查询支持 `keyword`（按模型名称过滤）、`projectid`（配合 `includedpredefined` 使用）、`orderby`（排序，默认为 `-updatedat`）、`page`/`pageSize` 参数。`includedpredefined=true` 时同时返回预定义模型（projectid=null 的模型）。响应字段包含 `id/projectid/modelname/matchpattern/inputprice/outputprice/totalprice/unit/tokenizerconfig/pricingtiers`。

### 5.4. Alert管理接口 (AlertController)

Alert管理接口共 7 个端点，路由前缀为 `/api/alert`：

| 方法 | 路径 | 鉴权 | 说明 |
|------|------|------|------|
| GET | /api/alert/config | JWT | 获取AlertConfig |
| GET | /api/alert | JWT | 获取Alert规则列表 |
| POST | /api/alert | JWT | 创建Alert规则 |
| POST | /api/alert/update | JWT | 更新Alert规则 |
| POST | /api/alert/delete | JWT | 删除Alert规则 |
| POST | /api/alert/record/read | JWT | 标记Alert记录为已读 |
| GET | /api/alert/record | JWT | 查询Alert记录 |

Alert规则由 `AlertHandler` 管理 [API/Handlers/UserManagement/AlertHandler.cs:18]，评估逻辑由 `AlertService` 实现 [API/Common/Services/AlertService.cs]，支持 9 种Alert字段（`AlertField`：TotalTokens/TotalCost/ErrorCount/Latency/ErrorRate/InputTokens/OutputTokens/WarningCount/ObservationCount）、6 种比较操作符（`AlertOperator`：GreaterThan/LessThan/EqualTo/GreaterThanOrEqualTo/LessThanOrEqualTo/NotEqualTo）、3 种时间单位（`AlertTimeUnit`：Minute/Hour/Day）。通知方式支持系统通知（`AlertNotifyBy.System`）与短信通知（`AlertNotifyBy.SMS`）。

种时间单位（`AlertTimeUnit`：Minute/Hour/Day）。通知方式支持系统通知（`AlertNotifyBy.System`）与短信通知（`AlertNotifyBy.SMS`）。

Alert规则不存在返回 `AlertNotFound = 160000`，创建失败返回 `CreateAlertFailed = 160001`，更新失败返回 `UpdateAlertFailed = 160002`，删除失败返回 `DeleteAlertFailed = 160003`。参数校验错误：时间周期无效返回 `InvalidAlertPeriod = 160004`，频率无效返回 `InvalidAlertFrequency = 160005`，字段无效返回 `InvalidAlertField = 160006`，操作符无效返回 `InvalidAlertOperator = 160007`，值无效返回 `InvalidAlertValue = 160008`，名称无效返回 `InvalidAlertName = 160010`，通知方式无效返回 `InvalidAlertNotifyBy = 160011`，组织不可访问返回 `AlertOrgNotAccessible = 160013`，项目不存在返回 `AlertProjectNotFound = 160014`，名称过长返回 `AlertNameTooLong = 160015`。

### 5.5. Agent 管理接口 (AgentConfigController/AgentReportController/AgentSessionController)

Agent 管理接口共 9 个端点，覆盖 Agent Config、报告模板与Session管理。

**AgentConfigController** 提供 3 个端点，路由前缀为 `/api/agent/config` [API/Controllers/AgentManagement/AgentConfigController.cs:28-54]：

提供 3 个端点，路由前缀为 `/api/agent/config` [API/Controllers/AgentManagement/AgentConfigController.cs:28-54]：

| 方法 | 路径 | 鉴权 | 说明 |
|------|------|------|------|
| GET | /api/agent/config | JWT | 获取当前用户的 Agent Config |
| GET | /api/agent/config/delete | JWT | 删除当前用户的 Agent Config |
| POST | /api/agent/config | JWT | 创建或更新 Agent Config（存在则更新，不存在则创建） |

Agent Config响应字段包含 `id/userid/datasource/defaulttemplateid/createdat/updatedat`。Config不存在返回 `AgentConfigNotFound = 150022`。

**AgentReportController** 提供 3 个端点，路由前缀为 `/api/agent/report`：

| 方法 | 路径 | 鉴权 | 说明 |
|------|------|------|------|
| GET | /api/agent/report | JWT | 获取报告模板列表 |
| GET | /api/agent/report/delete | JWT | 删除报告模板 |
| POST | /api/agent/report | JWT | 创建或更新报告模板 |

报告模板不存在返回 `AgentReportTemplateNotFound = 150023`，模板名称为空返回 `EmptyAgentReportTemplateName = 150024`。

**AgentSessionController** 提供 3 个端点，路由前缀为 `/api/agent/session` [API/Controllers/AgentManagement/AgentSessionController.cs:33-60]：

 3 个端点，路由前缀为 `/api/agent/session` [API/Controllers/AgentManagement/AgentSessionController.cs:33-60]：

| 方法 | 路径 | 鉴权 | 说明 |
|------|------|------|------|
| GET | /api/agent/session | JWT | 获取Session列表（id 为空）或单个Session详情（id 不为空） |
| GET | /api/agent/session/delete | JWT | 删除Session（ids 逗号分隔，仅删除当前用户名下） |
| POST | /api/agent/session | JWT | 创建或更新Session（id 为空则创建，不为空则更新） |

Session分页参数：`page` 默认 1，`pageSize` 默认 10（`AgentInsightConst.DefaultPage`/`DefaultPageSize`）。Session不存在返回 `AgentSessionNotFound = 150021`。

### 5.6. 工具管理接口 (BulletinController/HealthController/WeChatController)

工具管理接口共 10 个端点，覆盖Bulletin管理、健康检查与微信消息处理。

**BulletinController** 提供 7 个端点，路由前缀为 `/api/tools/bulletin`：

| 方法 | 路径 | 鉴权 | 说明 |
|------|------|------|------|
| POST | /api/tools/bulletin | JWT | 创建Bulletin |
| GET | /api/tools/bulletin/agreement | JWT | 获取用户协议 |
| GET | /api/tools/bulletin/bulletins | JWT | 获取Bulletin列表 |
| GET | /api/tools/bulletin/backend | JWT | 获取后台Bulletin列表 |
| POST | /api/tools/bulletin/approve | JWT | 审批Bulletin |
| POST | /api/tools/bulletin/revision | JWT | 修订Bulletin |
| POST | /api/tools/bulletin/close | JWT | 关闭Bulletin |

**HealthController** 提供 1 个端点：

| 方法 | 路径 | 鉴权 | 说明 |
|------|------|------|------|
| GET | /api/tools/health | 匿名 | 健康检查 |

**WeChatController** 提供 2 个端点，路由前缀为 `/api/tools/wechat`，无需认证（微信服务器回调）[API/Controllers/ToolsManagement/WeChat/WeChatController.cs:36-68]：

| 方法 | 路径 | 鉴权 | 说明 |
|------|------|------|------|
| GET | /api/tools/wechat | 匿名 | 微信验证接口，验证签名后返回 echostr 原文 |
| POST | /api/tools/wechat | 匿名 | 接收微信推送的消息和事件，返回 XML 消息 |

wechat | 匿名 | 微信验证接口，验证签名后返回 echostr 原文 |
| POST | /api/tools/wechat | 匿名 | 接收微信推送的消息和事件，返回 XML 消息 |

微信签名验证由 `WeChatService.ExamineSignature()` 实现 [API/Common/Services/WeChatService.cs:14]。签名验证失败返回 `ExamineWeChatSignatureFailed = 620002`。消息处理由 `WeChatHandler.ProcessMessage()` 完成，支持文本消息与事件消息。无效消息类型返回 `InvalidWeChatMessageType = 620005`，无效消息事件返回 `InvalidWeChatMessageEvent = 620006`。

### 5.7. Agents 运行时接口 (server.py)

Agents 运行时接口共 6 个端点，由 Python/FastAPI 服务提供，路由定义于 `Agents/server.py`：

| 方法 | 路径 | 鉴权 | 说明 |
|------|------|------|------|
| POST | /api/agent/insight | API Key (Basic Auth) | OpenAI 兼容 Chat Completions API，支持流式 (SSE) 与非流式响应 |
| GET | /api/sessions | API Key | 获取Session列表 |
| GET | /api/sessions/{session_id} | API Key | 获取单个Session详情 |
| DELETE | /api/sessions/{session_id} | API Key | 删除Session |
| POST | /api/sessions/cleanup | API Key | 清理过期Session |
| GET | /api/agents | API Key | 获取 Agent 列表 |

 |
| POST | /api/sessions/cleanup | API Key | 清理过期Session |
| GET | /api/agents | API Key | 获取 Agent 列表 |

`POST /api/agent/insight` 为 Chat Completions 核心端点 [Agents/server.py:346]，由 `InsightOrchestrator` 作为统一入口，内部路由到 Researcher、CustomService 等子 Agent。支持流式响应，通过 `asyncio.Queue` 实现 token 级流式输出，首 token 延迟 <800ms [Agents/server.py:430]。Session管理由 `MemoryManager` 提供持久化，支持列表、详情、删除、过期清理 [Agents/server.py:614-641]。

---

## 6. 数据需求

AgentInsightService 是一个面向 AI Agent 的可Observation性与运营管理平台，通过 Trace、Observation、Score 等数据模型对 AI Agent 执行链路进行全量采集、存储、查询与分析，同时支持 Organization → Project 两级租户模型及Payment订阅、AlertConfig等 SaaS 运营功能。数据需求章节定义系统核心数据实体的映射关系、分层存储策略以及数据在采集、摄入、查询、评估各环节的流转路径，为后续的接口设计与功能实现提供数据层面的约束依据。

### 6.1. 数据模型

系统数据模型按业务域划分为用户与租户、Agent 可Observation性、运营管理三大类。

**用户与租户域**：`User` 实体存储用户认证信息与个人资料，支持密码登录、短信Captcha、微信登录等多种方式；`Organization` 与 `Project` 构成两级租户模型，角色验证在 `ApiHandlerBase` 中通过 `RequireOrgMembership` 与 `RequireOrgOwner` 方法强制实施。`AgentConfig` 与 `AgentReportTemplate` 实体存储 Agent 运行时Config与报告模板，由 `AgentConfigController` 与 `AgentReportController` 提供 CRUD 接口（`API/Controllers/AgentManagement/AgentConfigController.cs:28-54`、`API/Controllers/AgentManagement/AgentReportController.cs:35-62`）。`AgentSession` 实体记录用户与 Agent 的Session状态，`AgentSessionController` 提供Session查询与删除接口（`API/Controllers/AgentManagement/AgentSessionController.cs:33-46`）。

**Agent 可Observation性域**：`Trace` 实体表示一次 Agent 执行链路的完整Trace，包含 Trace ID、Project ID、时间戳、Token 用量、延迟、成本等核心指标字段；`Observation` 实体记录 Trace 下的单个Observation步骤（如 LLM 调用、工具调用），包含 TraceId 外键与时间戳排序字段；`Score` 实体存储对 Trace 或 Observation 的Score数据，通过 TraceId 关联，并可通过 ObservationId 关联到具体Observation步骤。`MetricsHandler` 通过 ClickHouse 客户端执行查询，提供 Observation 分页查询、Score 查询与 Trace 查询能力（`API/Handlers/DataManagement/MetricsHandler.cs`）。`TraceMetrics` 聚合模型提供 Trace 级指标汇总，`AlertMetricsHandler` 按 Trace ID 批量查询Alert指标，使用 `AgentInsightConst.MaxBatchSize` 分批执行以避免 IN 子句过长（`API/Handlers/DataManagement/AlertMetricsHandler.cs:14-38`）。

**运营管理域**：`Order` 实体记录Payment订单，关联产品与组织，`PaymentService` 负责订单创建与Payment流程（`API/Common/Services/PaymentService.cs`）；`Alert` 实体定义Alert规则，`AlertField` 枚举（`Models/Common/Enums/AlertEnum.cs:20`）支持 TotalTokens、TotalCost、ErrorCount、Latency、ErrorRate、InputTokens、OutputTokens、WarningCount、ObservationCount 共 9 种指标字段，`AlertOperator` 枚举（`Models/Common/Enums/AlertEnum.cs:10`）定义 GreaterThan、LessThan、EqualTo、GreaterThanOrEqualTo、LessThanOrEqualTo、NotEqualTo 共 6 种比较操作符；`AgentInsightProduct` 与 `AgentInsightProductDuration` 实体描述订阅产品与时长，由 `ProductController` 提供查询接口（`API/Controllers/ProductManagement/ProductController.cs:26-38`）；`AgentInsightSetting` 实体存储微信/Payment宝等第三方PaymentConfig，`AgentInsightSettingType` 枚举（`Models/Common/Enums/AgentInsightEnum.cs:3`）定义 WeChat=1、Alipay=2 两种Config类型。

### 6.2. 数据存储

系统采用多存储引擎分层架构，按数据特性与访问模式将不同实体路由到对应数据库。连接字符串从 `appsettings.json` 提取，其中 ClickHouse 连接字符串 `ClickHouseDbConnection` Config连接池大小（PoolSize=10, MaxPoolSize=50），PostgreSQL 连接字符串 `DataDbConnection`、`TrackingDbConnection`、`UserDbConnection` 分别对应不同业务库，Config连接池与超时参数（如 MinPoolSize=10, MaxPoolSize=200）。

**PostgreSQL（业务数据库）**：存储用户、Org、Project、Payment、Alert等事务性业务数据。`UserHandler`、`OrganizationHandler`、`ProjectHandler`、`AlertHandler`、`OrderHandler` 等 Handler 均通过依赖注入获取用户库客户端，`ProductController` 查询 `AgentInsightProduct` 与 `AgentInsightProductDuration` 表（`API/Controllers/ProductManagement/ProductController.cs:26-38`），`SettingHandler` 查询 `AgentInsightSetting` 表（`API/Handlers/ToolsManagement/SettingHandler.cs:14-24`）。

**ClickHouse（时序分析数据库）**：存储 Trace、Observation、Score 三类可Observation性时序数据。`MetricsHandler` 通过 ClickHouse 客户端执行 Trace 查询、Observation 分页查询与 Score 查询（`API/Handlers/DataManagement/MetricsHandler.cs`），`AlertMetricsHandler` 通过 ClickHouse 客户端执行Alert指标批量查询（`API/Handlers/DataManagement/AlertMetricsHandler.cs:14-38`）。查询异常时区分超时错误（`ExceptionCodes.ClickHouseQueryTimeout = 150017`）与一般查询错误（`ExceptionCodes.ClickHouseQueryError = 150010`）。

**Redis（缓存与消息队列）**：Redis 承担双重职责：一是作为分布式缓存存储用户Session与设置数据，二是作为 `BullMqService` 的底层消息队列存储。`BullMqService` 基于 Redis 实现 Trace 异步摄入队列与项目删除任务队列，提供 `EnqueueTraceIngestionAsync`、`EnqueueProjectDeleteAsync`、`AcknowledgeTraceIngestionAsync` 等方法（`API/Common/Services/BullMqService.cs`）。

| 存储引擎 | 数据实体 |
|---------|---------|
| PostgreSQL | User、Organization、Project、Order、Alert、AgentConfig、AgentReportTemplate、AgentSession、AgentInsightProduct、AgentInsightSetting |
| ClickHouse | Trace、Observation、Score（TraceMetrics、AlertMetrics 为查询聚合模型，不独立存储） |
| Redis | Session缓存、BullMqService 消息队列 |

### 6.3. 数据流

数据流覆盖从 Agent 执行到可Observation性数据可查询的完整链路，包含 Trace 上报、异步摄入、Alert评估、审计日志四条主要路径。

**Trace 上报路径**：Agent 开发者通过 Langfuse 兼容 SDK 将 Trace 数据上报至 `/api/public/{**catch-all}` 端点，YARP 反向代理根据 `appsettings.json` 中 `ReverseProxy.Routes.AgentInsight-Route-API` 路由规则将请求转发至 `AgentInsight-Langfuse-Cluster` 集群。`AgentInsightTransformProvider` 在代理层执行认证转换，处理 Basic Auth 与 JWT 两种认证方式，验证 API Key 并解析用户身份（`API/System/Handlers/AgentInsightTransformProvider.cs:18`），随后将 Trace 数据写入 ClickHouse。

**异步摄入路径**：`AgentInsightTransformProvider` 调用 `BullMqService.EnqueueTraceIngestionAsync` 将 Trace 摄入任务投递至 Redis 消息队列（`API/System/Handlers/AgentInsightTransformProvider.cs:8`），后台消费者从队列中取出任务并批量写入 ClickHouse，写入成功后调用 `AcknowledgeTraceIngestionAsync` 确认任务完成。该异步机制将 Trace 上报与存储解耦，避免高并发写入阻塞代理层。`BullMqService` 同时提供 `EnqueueProjectDeleteAsync` 处理项目删除时的级联数据清理任务。

**Alert评估路径**：`AlertService` 周期执行Alert规则评估（通过定时任务触发），支持 `AlertTimeUnit` 枚举（`Models/Common/Enums/AlertEnum.cs:3`，Minute=1, Hour=2, Day=3）定义的时间窗口计算。评估流程为：从 ClickHouse 查询时间窗口内的 Trace 指标数据（`AlertMetricsHandler.GetAlertMetrics` 按 Trace ID 批量查询，`API/Handlers/DataManagement/AlertMetricsHandler.cs:14-38`），`AlertService` 对每条规则执行 `IsConditionMet` 条件判断（比较 `AlertField` 指标值与规则阈值，使用 `AlertOperator` 操作符），满足条件时调用 `BuildAlertMessage` 构建Alert消息，并通过 `SystemAlertHandler`（系统通知）或 `SMSAlertHandler`（短信通知）发送Alert（`API/Notifications/SystemAlertHandler.cs`、`API/Notifications/SMSAlertHandler.cs`），同时将Alert记录写入数据库。

**审计日志路径**：`ApiHandlerBase.LogAudit()` 记录关键操作审计日志（`API/Handlers/ApiHandlerBase.cs:34`），`AuditAction` 枚举（`Models/Common/Enums/AuditEnum.cs:3`）覆盖 Create、Update、Delete、Login、Logout、Reset、Bind、UnBind、Place、Query、Notify 共 11 种操作类型，`AuditResourceType` 枚举（`Models/Common/Enums/AuditEnum.cs:18`）覆盖 User、Organization、Project、Alert、ApiKey、Invitation、Order、WeChat、OrgPrivilege 共 9 种资源类型。审计记录写入 PostgreSQL 数据库，可通过 `QueueType.Audit = 0` 枚举值（`Entities/Common/Enums/QueueEnum.cs:3`）关联到审计队列。

| 数据流路径 | 入口 | 处理组件 | 出口 | 关键方法 |
|-----------|------|---------|------|----------|
| Trace 上报 | `/api/public/{**catch-all}` | YARP 反向代理 → AgentInsightTransformProvider | ClickHouse | `AgentInsightTransformProvider` 认证转换 |
| 异步摄入 | Redis 消息队列 | BullMqService 消费者 | ClickHouse | `EnqueueTraceIngestionAsync`、`AcknowledgeTraceIngestionAsync` |
| Alert评估 | 定时触发 | AlertService → AlertMetricsHandler | 系统/短信通知、数据库 | `GetAlertMetrics`、`IsConditionMet`、`BuildAlertMessage` |
| 审计日志 | ApiHandlerBase | LogAudit | PostgreSQL | `LogAudit`（AuditAction + AuditResourceType） |

---

## 7. 约束条件

AgentInsightService 是一个面向 AI Agent 的可Observation性与运营管理平台，通过 Trace、Observation、Score 等数据模型对 AI Agent 执行链路进行全量采集、存储、查询与分析，并支持 Organization → Project 两级租户模型及Payment订阅等完整 SaaS 运营功能。本章从技术、业务与合规三个维度，系统阐述 AgentInsightService 在开发与运维过程中必须遵守的约束条件，确保系统架构一致性、数据安全性与业务合规性。

### 7.1. 技术约束

#### 7.1.1. 技术栈与依赖管理

AgentInsightService 采用 monorepo 多子项目结构，各子项目技术栈定位明确：API 子项目基于 C#/.NET 与 Furion 框架构建主后端服务，Agents 子项目基于 Python/FastAPI 提供 AI Agent 运行时，Admin 子项目基于 Python/Django 实现后台管理，Entities/Models 子项目承载 C# 数据实体与模型定义。系统依赖以下核心框架与库，开发过程中必须使用这些声明的依赖，禁止引入未授权框架：

| 技术领域 | 依赖组件 | 用途说明 |
|---------|---------|---------|
| ORM | SqlSugar | 数据访问层，操作 PostgreSQL 与 ClickHouse |
| 中间件 | MediatR | 进程内消息通知模式，解耦Payment回调、Alert触发等业务事件 |
| 反向代理 | Yarp.ReverseProxy | 将 `/api/public/{**catch-all}` 代理至 Langfuse 兼容后端 |
| Payment SDK | AlipaySDKNet.Standard | Payment宝Payment接口调用 |
| AI 框架 | LangChain.Providers.OpenAI、Microsoft.SemanticKernel | Agents 子项目中的 Agent 编排与推理 |
| 缓存 | StackExchange.Redis | Redis 分布式缓存与消息队列 |
| 数据库驱动 | Npgsql | PostgreSQL 连接驱动 |

依赖注入采用键控服务（Keyed Services）区分不同数据库上下文，例如 `AgentInsightConst.KeyedService_UserDb` 与 `AgentInsightConst.KeyedService_DataDb` 分别对应 UserDb 与 DataDb 的 `ISqlSugarClient` 实例（见 `API/Common/Services/UserService.cs` 构造函数）。新增依赖必须经过架构评审，确保与现有技术栈兼容。

#### 7.1.2. 项目结构约束

仓库采用 monorepo 结构，各目录职责边界清晰，主功能集中在 API 与 Agents 两个子项目：

```
AgentInsightService/
├── API/          # C#/.NET 主后端服务（RESTful API + YARP 反向代理）
├── Agents/       # Python/FastAPI AI Agent 运行时
├── Admin/        # Python/Django 后台管理系统
├── Entities/     # C# 数据实体定义
├── Models/       # C# 模型与枚举定义
└── Configurations/  # Config文件扫描目录
```

API 子项目内部分层明确：Controllers 层负责 HTTP 路由映射，Handlers 层承载业务逻辑（如 `API/Handlers/UserManagement/UserHandler.cs`、`API/Handlers/DataManagement/MetricsHandler.cs`），Common/Services 层提供通用服务（如 `API/Common/Services/PaymentService.cs`、`API/Common/Services/UserService.cs`），System/Handlers 层实现系统级中间件（如 `API/System/Handlers/ExceptionMiddleware.cs`、`API/System/Handlers/AgentInsightTransformProvider.cs`）。新增代码必须遵循此分层架构，禁止跨层直接调用。

#### 7.1.3. API 版本与路由管理

API 分组与版本由 `SpecificationDocumentSettings` 定义，`RoutePrefix` Config为 `api`，所有 HTTP 端点统一挂载于 `/api` 前缀之下。Swagger 文档按业务域分组（User、Data、Agent、Payment、Tools 等），每个分组Config独立的 `GroupOpenApiInfos` 元数据。Controllers 通过 `[ApiDescriptionSettings]` 特性标注所属分组与标签，例如 `NotifyController` 标注为 `SwaggerApiDescription.Payment` 分组（见 `API/Controllers/PaymentManagement/NotifyController.cs`）。新增 API 端点必须遵循此路由与分组规范。

#### 7.1.4. 日志与数据保留

日志文件采用滚动策略：单个日志文件大小限制为 10MB（`Logging.File.FileSizeLimitBytes = 10485760`），最多保留 30 个滚动文件（`Logging.File.MaxRollingFiles = 30`），日志文件名为 `logs/application-.log`。控制台日志级别为 Warning，文件日志最低级别为 Information。此Config确保日志占用的磁盘空间可控，同时保留足够的诊断信息用于问题排查。

### 7.2. 业务约束

#### 7.2.1. 多租户隔离与角色Privilege

AgentInsightService 采用 Organization → Project 两级租户模型，所有数据访问必须通过租户隔离校验。系统通过 `Role` 枚举定义四级角色：OWNER（4）、ADMIN（3）、MEMBER（2）、VIEWER（1），角色等级从高到低排列。所有 Handler 必须继承 `ApiHandlerBase` 基类，并通过其提供的角色验证方法执行访问控制：

- `RequireOrgMembership(string orgId, Role minRole)`：校验当前用户是否属于指定组织，且角色不低于 `minRole`（见 `API/Handlers/ApiHandlerBase.cs:27`）。
- `RequireOrgOwner(string orgId)`：校验当前用户是否为指定组织的 OWNER（见 `API/Handlers/ApiHandlerBase.cs:29`）。

任何涉及 Organization 或 Project 资源的读写操作，必须先调用上述验证方法确认用户角色与归属关系，禁止绕过租户隔离直接访问数据。例如，`UserHandler.Login` 中通过 API Key 登录时，必须校验 `AgentInsightAPISecretKey` 的归属关系（见 `API/Handlers/UserManagement/UserHandler.cs`）。

#### 7.2.2. API Key 安全

API Key 用于程序化访问系统 API，其管理遵循以下业务约束：

- **密钥对机制**：API Key 由 `PublicKey` 与 `SecretKey` 组成，用户通过 `UserHandler.CreateApiKey()` 创建（见 `API/Handlers/UserManagement/UserHandler.cs:42`）。
- **认证方式**：API 调用方通过 Basic Auth 携带密钥对，由 `AgentInsightTransformLogic.ParseBasicAuth` 解析（见 `API/System/Handlers/AgentInsightTransformLogic.cs`），随后在 `AgentInsightTransformProvider` 中完成认证转换。
- **错误处理**：密钥缺失或无效时分别抛出 `InvalidCredentials`（100037）与 `InvalidApiKey`（100038）错误码。

#### 7.2.3. Payment业务规则

Payment模块涉及订单创建、Payment发起、异步回调与权益更新四个核心环节，业务约束如下：

- **订单创建**：`PaymentService.CreateOrder()` 生成订单号（格式为 `yyyyMMddHHmmssfff` + 7 位随机数），初始化订单状态为 `TradeState.NOTPAY` 与 `OrderState.Created`（见 `API/Common/Services/PaymentService.cs`）。
- **金额计算**：订单总金额 = 产品价格 × 数量 × 折扣，Payment金额单位为分（微信Payment金额单位转换常量为 `WeChatAmountUnit = 100`，见 `API/Common/Services/PaymentService.cs:8`）。
- **签名验证**：Payment回调必须严格验证签名，防止伪造回调。微信Payment回调通过 `WeChatService.ExamineSignature` 验证签名（见 `API/Common/Services/WeChatService.cs:14`），Payment宝回调通过 `ExamineAlipaySignature` 验证（见 `API/Common/Services/PaymentService.cs:24`）。验证失败时分别抛出 `ExamineWeChatSignatureFailed`（620002）与 `AlipaySignatureError`（810007）错误码。
- **权益更新**：Payment成功后，`PaymentService.UpdateOrgPrivilege()` 自动更新组织权益（见 `API/Common/Services/PaymentService.cs:20`）。

#### 7.2.4. 可Observation性数据查询

Trace 查询是系统的核心价值主张，业务约束如下：

- **过滤条件**：`TraceFilterBuilder.BuildFilters()` 支持 7 种过滤类型（FilterType：DateTime/String/Number/StringOptions/ArrayOptions/Boolean/Null）、15 FilterOperator、25 FilterColumn（见 `API/Common/Helpers/TraceFilterBuilder.cs:30`）。
- **查询参数校验**：非法过滤类型、字段或操作符分别抛出 `InvalidFilterType`（150012）、`InvalidFilterColumn`（150013）、`InvalidFilterOperator`（150014）错误码。
- **数据范围限制**：Trace 查询必须关联 Organization 与 Project，两者同时为空时抛出 `OrgAndProjectBothEmpty`（150019）错误码。

#### 7.2.5. Alert规则约束

Alert模块支持 9 种Alert字段（AlertField：TotalTokens/TotalCost/ErrorCount/Latency/ErrorRate/InputTokens/OutputTokens/WarningCount/ObservationCount）与 6 种比较操作符（AlertOperator：GreaterThan/LessThan/EqualTo/GreaterThanOrEqualTo/LessThanOrEqualTo/NotEqualTo）。Alert规则创建时，必须校验字段、操作符、周期与通知方式的合法性，非法值分别抛出 `InvalidAlertField`（160006）、`InvalidAlertOperator`（160007）、`InvalidAlertPeriod`（160004）、`InvalidAlertNotifyBy`（160011）错误码。

### 7.3. 合规约束

#### 7.3.1. 敏感信息保护

系统涉及用户隐私、Payment凭证与 API 密钥等敏感数据，合规约束如下：

- **API Key 加密存储**：`AgentInsightAPISecretKey` 的 SecretKey 必须加密存储，禁止明文出现在日志或Config文件中（见 `API/System/Handlers/AgentInsightTransformLogic.cs:18`）。日志输出时须过滤敏感字段。
- **密码加密**：用户密码通过 `IEncryptService` 接口进行哈希与验证，禁止明文存储。
- **Config项安全**：数据库连接字符串、JWT 签名密钥、AES 加密密钥等敏感Config通过环境变量注入（如 `${JWT_SIGNING_KEY}`、`${AES_KEY}`），禁止硬编码在Config文件中。

#### 7.3.2. Payment合规

Payment模块涉及资金交易，必须符合Payment行业合规要求：

- **签名验证强制**：微信与Payment宝Payment回调必须验证签名，防止伪造回调导致的资金风险。微信回调验签失败抛出 `ExamineWeChatSignatureFailed`（620002），Payment宝验签失败抛出 `AlipaySignatureError`（810007）。
- **交易状态机**：订单状态必须遵循 `TradeState` 枚举定义的状态流转（SUCCESS/REFUND/NOTPAY/CLOSED/REVOKED/USERPAYING/PAYERROR），禁止跳转非法状态。
- **金额一致性**：回调通知中的实付金额必须与订单金额一致，不一致时抛出 `InvalidTotalAmount`（810025）错误码。

#### 7.3.3. 数据保留与合规

- **日志保留**：日志文件限制 10MB，最多保留 30 个滚动文件，防止敏感信息长期留存。
- **Session管理**：`UserService.LogUserSession()` 记录用户Session，支持多设备登录控制（见 `API/Common/Services/UserService.cs:22`），Session过期时间由 `JWTSettings.ExpiredTime = 43200` 秒（12 小时）控制。
- **审计日志**：关键操作（用户创建、角色分配、Payment下单等）通过 `ApiHandlerBase.LogAudit()` 记录审计日志（见 `API/Handlers/ApiHandlerBase.cs:34`），审计日志保留策略与系统日志一致。

#### 7.3.4. 异常处理与错误码规范

系统通过 `ExceptionMiddleware` 统一处理异常（见 `API/System/Handlers/ExceptionMiddleware.cs`），所有业务异常必须使用 `ExceptionCodes` 枚举中定义的错误码，禁止自定义错误码。错误码按业务域分段：用户域（100xxx）、Captcha域（110xxx）、组织域（130xxx）、项目域（140xxx）、数据域（150xxx）、Alert域（160xxx）、Payment域（810xxx）、微信域（620xxx）、通用域（990xxx）。未捕获的未知异常统一返回 `DefaultException`（999999）。

---

## 8. 优先级路线图

AgentInsightService 是一个面向 AI Agent 的可Observation性与运营管理平台，提供 Agent 可Observation性（Trace、Observation、Score 数据模型的全量采集、存储、查询与分析）与多租户运营管理（Organization → Project 两级租户模型，含用户管理、角色Privilege、Payment订阅、Bulletin系统、AlertConfig等 SaaS 运营功能）两大核心能力。本章节基于功能依赖关系、商业模式关键路径与代码成熟度三个维度，定义 P0 至 P3 四个优先级的开发路线图，为 Scrum 迭代规划提供依据。

### 8.1. P0 核心基础

P0 优先级包含系统运行所必需的基石功能，是所有其他功能的前置依赖，也是 AgentInsightService 核心价值主张的直接体现。该优先级聚焦用户认证与可Observation性数据查询两大模块，确保平台具备最基本的用户访问控制与核心数据服务能力。

**用户认证**是平台安全性的第一道防线。`UserController` 作为用户管理核心Controller，实现了注册、登录、微信绑定、角色分配、API Key 管理、邀请成员等完整功能 [API/Controllers/UserManagement/UserController.cs]。系统支持密码登录、短信Captcha登录、微信登录等多种认证方式。`UserController.Login` 方法处理登录逻辑 [API/Controllers/UserManagement/UserController.cs:73]，当使用 API Key 认证时，通过 `AgentInsightTransformLogic` 解析 Basic Auth 请求头，并验证 API Key 有效性，认证失败时抛出 `InvalidCredentials` (100037) 或 `InvalidApiKey` (100038) 异常。JWT 认证Config定义于 `appsettings.json`，采用 HS256 算法，过期时间为 43200 秒，并启用签发者与受众验证。API Key 认证由 `AgentInsightTransformProvider` 处理，支持 Basic Auth 和 JWT 两种认证方式 [API/System/Handlers/AgentInsightTransformProvider.cs:18]。

**可Observation性核心**是 AgentInsightService 区别于传统可Observation性系统的差异化能力。`MetricsController` 提供 Trace 列表查询（支持多维度过滤、排序、分页）、Observation 查询与 Score 查询 [API/Controllers/DataManagement/MetricsController.cs]。Trace 查询通过 `TraceFilterBuilder.BuildFilters()` 构建过滤条件，支持 7 种 `FilterType`（DateTime/String/Number/StringOptions/ArrayOptions/Boolean/Null）、15 种 `FilterOperator`（GreaterThan/LessThan/EqualTo/Contains/AnyOf/IsNull 等）、25 个 `FilterColumn`（Id/Name/Timestamp/UserId/SessionId/Environment/Version/Tags/Latency/InputTokens/OutputTokens/TotalTokens/TotalCost/Level/WarningCount/ErrorCount/ModelNames/ScoresAvg 等）[API/Common/Helpers/TraceFilterBuilder.cs:30]。查询执行依赖 `ClickHouseClient` 连接 ClickHouse 数据库，连接池Config为 `PoolSize=10;MaxPoolSize=50`，查询超时错误码为 `ClickHouseQueryTimeout` (150017)。

| 功能项 | 关键实现 | 依赖组件 | 验收标准 |
|--------|---------|---------|---------|
| 多方式登录 | `UserController.Login` [API/Controllers/UserManagement/UserController.cs:73] | `IUserService`、`ICaptchaService` | 支持密码/短信/微信/API Key 等多种登录方式 |
| JWT 鉴权 | `JWTSettings` (HS256, 43200s) | `appsettings.json` | 无效 Token 返回 `UnAuthToken` (100000) |
| API Key 管理 | `UserController.CreateApiKey` [API/Controllers/UserManagement/UserController.cs:209] | `AgentInsightAPISecretKey` 表 | 创建/查询/删除 API Key，密钥不匹配返回 `InvalidApiKey` (100038) |
| Trace 多维查询 | `MetricsController.GetTraces` [API/Controllers/DataManagement/MetricsController.cs:64] | `TraceFilterBuilder`、`ClickHouseClient` | 25 个过滤字段、15 种操作符、分页排序 |
| Observation 查询 | `MetricsController.GetObservations` [API/Controllers/DataManagement/MetricsController.cs:34] | `ClickHouseClient` | 按 TraceId 查询 Observation 详情 |
| Score 查询 | `MetricsController.GetScores` [API/Controllers/DataManagement/MetricsController.cs:50] | `ClickHouseClient` | 查询 Trace 关联的 Score 数据 |

### 8.2. P1 商业与扩展

P1 优先级聚焦多租户管理、Payment订阅与 Agent 运行时三大模块，是 AgentInsightService 实现 SaaS 商业化运营的关键路径。该优先级建立在 P0 用户认证基础之上，为平台提供组织级协作能力、商业化变现能力与 AI Agent 核心交互能力。

**多租户管理**实现 Organization → Project 两级租户模型。`OrganizationController` 提供组织 CRUD 功能 [API/Controllers/UserManagement/OrganizationController.cs]，`ProjectController` 在组织下管理项目 [API/Controllers/UserManagement/ProjectController.cs]。成员邀请与角色分配由 `UserController.Invite()` 与 `UserController.AssignRole()` 实现 [API/Controllers/UserManagement/UserController.cs:162-147]。角色体系通过 `Role` 枚举定义四级角色：OWNER (4)、ADMIN (3)、MEMBER (2)、VIEWER (1) [Models/Common/Enums/UserEnum.cs:3]。Privilege验证在 `ApiHandlerBase` 中实现，`RequireOrgMembership(string orgId, Role minRole)` 强制要求最低角色，`RequireOrgOwner(string orgId)` 限制仅 OWNER 可执行操作 [API/Handlers/ApiHandlerBase.cs:27-29]。

**Payment订阅**是商业化的核心闭环。`PaymentService` 实现订单创建、微信/Payment宝Payment、Payment回调处理、订单状态更新与组织权益更新 [API/Common/Services/PaymentService.cs]。订单创建通过 `PaymentService.CreateOrder()` 生成订单并关联产品，支持微信Payment（JSAPI/Native/小程序三种方式）与Payment宝Payment（即时到账交易）。Payment回调由 `NotifyController` 处理微信/Payment宝异步通知，更新订单状态 [API/Controllers/PaymentManagement/NotifyController.cs]。Payment成功后 `PaymentService.UpdateOrgPrivilege()` 自动更新组织权益。订单状态通过 `TradeState` 枚举管理（SUCCESS/REFUND/NOTPAY/CLOSED/REVOKED/USERPAYING/PAYERROR 等），Payment异常错误码包括 `WeChatErrorResponse` (810022)、`AlipayConnectionError` (810003)、`CannotDowngradeProduct` (810023) 等。

**Agent 运行时**是平台面向 AI Agent 的核心交互能力。`POST /api/agent/insight` 端点提供 OpenAI 兼容的 Chat Completions API，SSE与非流式响应，由 `InsightOrchestrator` 统一编排，内部路由到 Researcher、CustomService 等子 Agent [Agents/server.py:346]。Session管理由 `MemoryManager` 实现，提供Session持久化、列表查询、详情获取、删除与过期清理功能 [Agents/server.py:614-641]。

| 功能项 | 关键实现 | 依赖组件 | 验收标准 |
|--------|---------|---------|---------|
| Org CRUD | `OrganizationController` [API/Controllers/UserManagement/OrganizationController.cs:28] | `ApiHandlerBase` | 创建/查询/更新/删除组织，Privilege校验 |
| Project CRUD | `ProjectController` [API/Controllers/UserManagement/ProjectController.cs:31] | `ApiHandlerBase` | 组织下创建/管理项目 |
| 成员邀请与角色 | `UserController.Invite` / `AssignRole` [API/Controllers/UserManagement/UserController.cs:162-147] | `Role` 枚举 | 四级角色分配，角色提升校验 |
| 订单创建 | `OrderController.Place` [API/Controllers/PaymentManagement/OrderController.cs:48] | `ProductController` | 生成订单号，关联产品与时长 |
| 微信/Payment宝Payment | `PaymentService` [API/Common/Services/PaymentService.cs:30] | AlipaySDKNet.Standard | JSAPI/Native/小程序/即时到账 |
| Payment回调 | `NotifyController` [API/Controllers/PaymentManagement/NotifyController.cs:29] | `PaymentService` | 签名验证，订单状态更新 |
| 权益更新 | `PaymentService.UpdateOrgPrivilege` [API/Common/Services/PaymentService.cs:20] | `OrgPrivilege` | Payment成功后自动更新组织权益 |
| Chat Completions | `POST /api/agent/insight` [Agents/server.py:346] | `InsightOrchestrator` | OpenAI 兼容，流式/非流式 |
| Session管理 | `MemoryManager` [Agents/server.py:614-641] | Redis | Session持久化、过期清理 |

### 8.3. P2 运营增值

P2 优先级包含Alert系统与Bulletin管理两大模块，为平台提供运维监控与运营管理能力，增强平台的实用性与用户粘性。该优先级建立在 P0 可Observation性数据与 P1 多租户体系之上，属于增值功能。

**Alert系统**基于可Observation性数据提供主动监控能力。`AlertController` 管理Alert规则 CRUD [API/Controllers/UserManagement/AlertController.cs]，`AlertService` 实现Alert评估服务，支持时间窗口计算、条件判断、指标字段评估、Alert消息构建 [API/Common/Services/AlertService.cs]。Alert字段通过 `AlertField` 枚举定义 9 种指标（TotalTokens/TotalCost/ErrorCount/Latency/ErrorRate/InputTokens/OutputTokens/WarningCount/ObservationCount），比较操作符通过 `AlertOperator` 枚举定义 6 种（GreaterThan/LessThan/EqualTo/GreaterThanOrEqualTo/LessThanOrEqualTo/NotEqualTo）[Models/Common/Enums/AlertEnum.cs:20-10]。Alert通知支持系统通知与短信通知两种方式，通过 `AlertNotifyBy` 枚举区分（System/SMS）[Models/Common/Enums/AlertEnum.cs:39]。Alert评估使用 MediatR 通知模式解耦，错误码包括 `AlertNotFound` (160000)、`InvalidAlertField` (160006)、`InvalidAlertOperator` (160007) 等。

**Bulletin管理**提供运营信息发布能力。`BulletinController` 实现Bulletin的创建、查询、审批、修订与关闭流程 [API/Controllers/ToolsManagement/BulletinController.cs]。Bulletin发布支持前端展示 (`GET /api/tools/bulletin/bulletins`) 与后台管理 (`GET /api/tools/bulletin/backend`) 两种视角，审批流程通过 `POST /api/tools/bulletin/approve` 实现，修订通过 `POST /api/tools/bulletin/revision` 实现，关闭通过 `POST /api/tools/bulletin/close` 实现。

| 功能项 | 关键实现 | 依赖组件 | 验收标准 |
|--------|---------|---------|---------|
| Alert规则 CRUD | `AlertController` [API/Controllers/UserManagement/AlertController.cs:61] | `IAlertService` | 创建/更新/删除/查询Alert规则 |
| Alert评估 | `AlertService` [API/Common/Services/AlertService.cs] | `AlertField`、`AlertOperator` | 9 种字段、6 种操作符、时间窗口 |
| Alert通知 | `AlertNotifyBy` 枚举 [Models/Common/Enums/AlertEnum.cs:39] | MediatR | 系统通知与短信通知 |
| Bulletin发布 | `BulletinController.Post` [API/Controllers/ToolsManagement/BulletinController.cs:32] | `Bulletin` 实体 | 创建Bulletin，待审批 |
| Bulletin审批 | `BulletinController.ApproveBulletin` [API/Controllers/ToolsManagement/BulletinController.cs:96] | `Bulletin` 实体 | 审批通过/驳回 |
| Bulletin修订与关闭 | `BulletinController.ReviseBulletin` / `CloseBulletin` [API/Controllers/ToolsManagement/BulletinController.cs:110-124] | `Bulletin` 实体 | 修订内容、关闭Bulletin |

### 8.4. P3 辅助功能

P3 优先级包含 Agent Config与报告模板管理、Session历史自动清理等辅助功能，为平台提供更完善的 Agent 管理体验。该优先级功能独立性强，不阻塞核心业务流程，可在前三个优先级稳定后迭代完善。

**Agent Config管理**由 `AgentConfigController` 提供接口，支持获取当前用户的 Agent Config、删除Config、创建或更新Config [API/Controllers/AgentManagement/AgentConfigController.cs]。Config内容包括数据源连接信息 (datasource) 与默认模板 ID (defaulttemplateid)。`AgentConfigHandler` 处理具体业务逻辑，Config不存在时抛出 `AgentConfigNotFound` (150022) 异常。

**报告模板管理**由 `AgentReportController` 实现，支持获取模板列表（含预定义模板与用户自定义模板）、删除模板、创建或更新模板 [API/Controllers/AgentManagement/AgentReportController.cs]。模板查询通过 `includedPredefined` 与 `includedPredefinedOnly` 参数控制是否包含预定义模板，预定义模板的 `UserId` 为 null。模板不存在时抛出 `AgentReportTemplateNotFound` (150023) 异常。

**Session历史自动清理**由 Agents 子项目提供。`POST /api/sessions/cleanup` 端点实现过期Session清理 [Agents/server.py:641]，`MemoryManager` 提供Session过期管理能力。Session管理相关端点包括 `GET /api/sessions`（列表）、`GET /api/sessions/{session_id}`（详情）、`DELETE /api/sessions/{session_id}`（删除）[Agents/server.py:614-633]。

| 功能项 | 关键实现 | 依赖组件 | 验收标准 |
|--------|---------|---------|---------|
| Agent Config管理 | `AgentConfigController` [API/Controllers/AgentManagement/AgentConfigController.cs] | `AgentConfigHandler` | 获取/删除/创建或更新Config |
| 报告模板管理 | `AgentReportController` [API/Controllers/AgentManagement/AgentReportController.cs] | `AgentReportHandler` | 获取/删除/创建或更新模板，支持预定义模板 |
| Session历史清理 | `POST /api/sessions/cleanup` [Agents/server.py:641] | `MemoryManager` | 过期Session自动清理 |
| Session管理 | `GET/DELETE /api/sessions` [Agents/server.py:614-633] | `MemoryManager` | Session列表/详情/删除 |

各优先级的开发顺序基于功能依赖关系（P0 是 P1/P2/P3 的前置条件）、商业模式关键路径（P1 Payment订阅直接产生收入）与代码成熟度（P0 用户认证与可Observation性代码已具备较高完成度）综合确定。具体开发计划与迭代排期请参考 Scrum 迭代规划，每个迭代应优先完成高优先级功能的技术方案设计与评审，确保需求、设计、开发、测试全流程闭环。

---

## 9. 风险与依赖

AgentInsightService 是一个面向 AI Agent 的可Observation性与运营管理平台，其核心能力包括通过 Trace、Observation、Score 等数据模型对 AI Agent 执行链路进行全量采集与查询，以及基于 Organization → Project 两级租户模型的 SaaS 运营管理。系统在架构上强依赖多个外部基础设施与第三方服务，同时代码库中亦存在若干技术债务与安全风险点。本章节从外部依赖风险、技术债务、安全风险三个维度展开分析，并给出对应的缓解建议。

### 9.1. 外部依赖风险

AgentInsightService 的Payment链路、可Observation性数据存储与消息队列均依赖外部组件，任一关键依赖不可用都将直接影响核心业务功能。

#### 9.1.1. 微信/Payment宝 API 稳定性

Payment模块通过 `IPaymentService`（`API/Common/Services/IPaymentService.cs`）封装微信Payment与Payment宝Payment能力，订单创建、Payment回调、交易状态查询等核心流程均强依赖第三方Payment API 的可用性。系统为Payment异常定义了完整的错误码体系：

| 错误码常量 | 数值 | 含义 |
|-----------|------|------|
| `WeChatErrorResponse` | 810022 | 微信Payment返回错误 |
| `WeChatEmptyResponse` | 810021 | 微信Payment响应为空 |
| `WeChatQueryErrorResponse` | 810024 | 微信Payment查询失败 |
| `AlipayConnectionError` | 810003 | Payment宝连接失败，请稍后重试 |
| `AlipayTradeError` | 810004 | Payment宝交易失败 |
| `AlipayPlaceOrderError` | 810020 | Payment宝下单失败 |

以上错误码定义于 `Models/Common/Enums/ExceptionCodes.cs:6`，并在 `API/Resources/Text.zh-CN.json` 与 `API/Resources/Text.zh-TW.json` 中Config了对应的本地化错误消息。Payment回调入口 `NotifyController`（`API/Controllers/PaymentManagement/NotifyController.cs:29`）在捕获异常后返回失败响应，但当前实现为同步处理模式，未内置重试与熔断机制。

**缓解建议**：
- 对微信/Payment宝 API 调用增加指数退避重试策略，区分网络抖动与业务失败（如签名错误、订单不存在等不可重试错误应直接返回）。
- 引入熔断器模式（如 Polly），在第三方 API 连续失败达到阈值时快速失败，避免线程阻塞与资源耗尽。
- 对Payment回调处理增加幂等保护，确保同一通知重复到达时不会产生重复的订单状态更新或权益发放。

#### 9.1.2. ClickHouse 可用性

ClickHouse 是 Trace 查询的核心存储引擎，`MetricsHandler`（`API/Handlers/DataManagement/MetricsHandler.cs:30`）通过 `ClickHouseClient`（`API/Common/Services/ClickHouseClient.cs`）执行 SQL 查询。系统定义了 `ClickHouseQueryError`（150010）与 `ClickHouseQueryTimeout`（150017）两个错误码，分别表示查询执行失败与查询超时。连接字符串Config了连接池大小、连接超时与命令超时参数（`appsettings.json` 中 ClickHouse 连接Config），但若 ClickHouse 单点故障，所有可Observation性功能（Trace 查询、Observation 查询、Score 查询）将全部不可用。

**缓解建议**：
- 部署 ClickHouse 集群（如副本+分片），避免单点故障。
- 对高频查询增加缓存层（如 Redis），降低 ClickHouse 负载。
- 优化查询语句，避免全表扫描，利用索引和分区裁剪。

#### 9.1.3. Redis 依赖

`BullMqService`（`API/Common/Services/BullMqService.cs`）基于 Redis 实现消息队列，用于 Trace 异步摄入；同时用户Session缓存也依赖 Redis。若 Redis 不可用，将导致 Trace 数据无法异步写入，用户登录状态无法验证，影响核心可Observation性与认证功能。

**缓解建议**：
- Config Redis 哨兵或集群模式，提供高可用。
- 增加 Redis 连接池与超时Config，避免单点故障导致线程阻塞。
- 对关键缓存数据（如用户Session）设置持久化或降级策略，如本地缓存兜底。

### 9.2. 技术债务

代码库中存在若干技术债务，主要体现为过时标记与硬编码常量，需在后续迭代中逐步清理。

#### 9.2.1. Obsolete 标记

`MetricsHandler`（`API/Handlers/DataManagement/MetricsHandler.cs:80`）中定义了 `[Obsolete]` 标记的 `TraceCountRow` 类。该类用于 Trace 计数查询结果映射，但已被标记为过时，意味着后续版本可能移除或替换该实现。当前 `MetricsHandler.GetTraces()` 方法是否仍依赖此类需进一步确认，若存在引用，应在重构时一并替换。

**缓解建议**：
- 排查 `TraceCountRow` 的所有引用点，确认是否仍在使用。
- 若已无引用，直接删除；若仍有引用，评估替代方案（如使用匿名类型或新的 DTO 类）。
- 在 CI 流程中启用警告即错误，避免新增 Obsolete 引用。

#### 9.2.2. 硬编码常量

`PaymentService`（`API/Common/Services/PaymentService.cs:8`）中定义了 `private const int WeChatAmountUnit = 100;`，用于微信Payment金额单位转换（元转分）。该常量硬编码为 100，假设所有币种均为人民币且最小单位为分。若未来支持其他币种（如日元无小数位），该硬编码将导致金额计算错误。

**缓解建议**：
- 将 `WeChatAmountUnit` 提升为Config项，根据商户或币种动态获取。
- 在订单创建时校验币种与金额单位的匹配性，避免静默错误。
- 增加单元测试覆盖不同币种场景，确保金额转换正确性。

### 9.3. 安全风险

安全风险主要集中在 API Key 的存储与传输、以及Payment签名验证两个环节。

#### 9.3.1. API Key 泄露风险

`AgentInsightTransformProvider`（`API/System/Handlers/AgentInsightTransformLogic.cs:18`）处理 API Key 认证，`AgentInsightAPISecretKey` 的 secretKey 若以明文形式存储或传输，将面临泄露风险。API Key 一旦泄露，攻击者可伪造请求访问受保护资源，甚至消耗组织配额。系统虽定义了 `ApiKeyNotFound`（100031）、`ApiKeySecretNotFound`（100036）、`InvalidApiKey`（100038）等错误码，但错误码本身不能防止泄露。

**缓解建议**：
- secretKey 必须加密存储（如使用 Azure Key Vault 或 AWS Secrets Manager），禁止明文落库。
- 传输层必须启用 HTTPS，防止中间人窃听。
- 增加 API Key 访问审计日志，记录每次 API Key 的使用时间、来源 IP、请求路径，便于异常检测与事后追溯。
- 提供 API Key 轮换机制，支持用户定期更换密钥。

#### 9.3.2. Payment签名伪造风险

Payment回调的签名验证是防止伪造交易通知的关键防线。系统在 `PaymentService`（`API/Common/Services/PaymentService.cs:24`）中实现 `ExamineAlipaySignature`，在 `WeChatService`（`API/Common/Services/WeChatService.cs:14`）中实现 `ExamineSignature`。若签名验证逻辑存在漏洞（如未校验时间戳、未使用安全比较函数、密钥硬编码），攻击者可构造伪造的Payment成功通知，触发订单状态更新与组织权益发放，造成欺诈交易。

**缓解建议**：
- 签名验证必须严格遵循官方文档，校验时间戳、随机数、签名算法等。
- 使用安全比较函数（如 `CryptographicOperations.FixedTimeEquals`）避免时序攻击。
- 密钥必须安全存储，禁止硬编码在代码或Config文件中。
- 必须接受严格的安全测试，包括渗透测试和代码审计，确保签名验证逻辑无漏洞。

---

## 10. 附录

AgentInsightService 是一个面向 AI Agent 的可Observation性与运营管理平台，提供 Trace、Observation、Score 等数据模型的全量采集、存储、查询与分析能力，并支持 Organization → Project 两级租户模型及完整的 SaaS 运营功能。本附录汇总了系统开发与集成过程中所需的术语定义、错误码与枚举参考、需求Trace矩阵及开源依赖清单，供接口对接、问题排查与二次开发使用。

### 10.1. 术语词典

以下术语在本文档及系统代码中频繁出现，统一按原文保留，禁止翻译。所有标识符均来自代码仓库中的实际定义。

ilege | 组织权益，Payment成功后由 PaymentService.UpdateOrgPrivilege() 更新 | API/Common/Services/PaymentService.cs |
| Metric | 指标数据，用于Alert评估与 Trace 查询 | Entities/DataManagement |
| Captcha | Captcha，支持图形Captcha与短信Captcha | API/Controllers/UserManagement/CaptchaController.cs |
| Log | 日志记录，通过 Logging Config写入文件系统 | appsettings.json |

### 10.2. 错误码与枚举参考

#### 10.2.1. 错误码完整清单

错误码定义于 `Models/Common/Enums/ExceptionCodes.cs`，覆盖 100000 至 999999 范围，按模块分类如下。所有错误码均通过 `Oops.Oh(ExceptionCodes.XXX)` 抛出，由 `ExceptionMiddleware` 统一捕获处理。

**用户与认证模块 (100000-110005)**

| errorCode | 常量名 | 含义 |
|-----------|--------|------|
| 100000 | UnAuthToken | 未认证的 Token |
| 100001 | EmptyUserId | User ID 为空 |
| 100003 | ExistedMobile | 手机号已存在 |
| 100004 | CreateUserFailed | 创建用户失败 |
| 100005 | InvalidUser | 无效用户 |
| 100009 | EmptyMobile | 手机号为空 |
| 100010 | UnauthorizedOperator | 未授权操作 |
| 100019 | UserNameTooLong | 用户名过长 |
| 100021 | EmptyInviteMobile | 邀请手机号为空 |
| 100022 | InvalidInviteMobile | 无效的邀请手机号 |
| 100023 | CannotGrantHigherRole | 不能授予更高角色 |
| 100024 | UserAlreadyOrgMember | 用户已是组织成员 |
| 100025 | InviteAlreadyExists | 邀请已存在 |
| 100026 | CreateInviteFailed | 创建邀请失败 |
| 100027 | InviteNotFound | 邀请不存在 |
| 100028 | DeleteInviteFailed | 删除邀请失败 |
| 100031 | ApiKeyNotFound | API Key 不存在 |
| 100032 | CreateApiKeyFailed | 创建 API Key 失败 |
| 100033 | DeleteApiKeyFailed | 删除 API Key 失败 |
| 100035 | MissingProjectOrOrgId | 缺少项目或组织 ID |
| 100036 | ApiKeySecretNotFound | API Key 密钥不存在 |
| 100037 | InvalidCredentials | 无效的凭证 |
| 100038 | InvalidApiKey | 无效的 API Key |

| 100039 | OwnerCannotModifySelfRole | 所有者不能修改自身角色 |
| 100040 | ResetPasswordFailed | 重置密码失败 |
| 100041 | UserNotInitialized | 用户未初始化 |
| 110000 | SendSMSTooOften | 短信发送过于频繁 |
| 110001 | FailedToSendSMS | 短信发送失败 |
| 110002 | EmptyCaptcha | Captcha为空 |
| 110003 | InvalidCaptcha | 无效Captcha |
| 110004 | ErrorCaptcha | Captcha错误 |
| 110005 | FailedToSendEmail | 邮件发送失败 |

**组织与项目管理模块 (130000-140008)**

| errorCode | 常量名 | 含义 |
|-----------|--------|------|
| 130000 | EmptyOrganizationName | 组织名称为空 |
| 130001 | OrganizationNameTooShort | 组织名称过短 |
| 130002 | OrganizationNameTooLong | 组织名称过长 |
| 130003 | InvalidOrganization | 无效组织 |
| 130004 | CreateOrganizationFailed | 创建组织失败 |
| 130005 | UpdateOrganizationFailed | 更新组织失败 |
| 130006 | DeleteOrganizationFailed | 删除组织失败 |
| 130007 | OrganizationHasProjects | 组织下存在项目 |
| 130008 | OrganizationProjectDeleting | 组织项目删除中 |
| 130009 | UnauthorizedOrganizationAccess | 未授权访问组织 |
| 130010 | ExceedHeadCountLimit | 超出人数上限 |
| 130011 | ExceedProjectLimit | 超出项目数上限 |
| 130012 | ExceedOrgLimit | 超出组织数上限 |
| 130013 | OrgAlreadyHasOwner | 组织已有所有者 |
| 140000 | EmptyProjectName | 项目名称为空 |
| 140001 | ProjectNameTooShort | 项目名称过短 |
| 140002 | ProjectNameTooLong | 项目名称过长 |
| 140003 | InvalidProject | 无效项目 |
| 140004 | CreateProjectFailed | 创建项目失败 |
| 140005 | UpdateProjectFailed | 更新项目失败 |
| 140006 | DeleteProjectFailed | 删除项目失败 |

| 140007 | ExistedProjectName | 项目名称已存在 |
| 140008 | UnauthorizedProjectAccess | 未授权访问项目 |

**可Observation性模块 (150000-150024)**

| errorCode | 常量名 | 含义 |
|-----------|--------|------|
| 150000 | EmptyProjectId | Project ID 为空 |
| 150004 | AgentSettingNotConfig | Agent 设置未Config |
| 150007 | AgentLimitExceeded | 超出 Agent 数量限制 |
| 150008 | DuplicateUserConfig | 用户Config重复 |
| 150009 | EmptyTraceIds | Trace ID 列表为空 |
| 150010 | ClickHouseQueryError | ClickHouse 查询错误 |
| 150011 | TooManyTraceIds | Trace ID 数量过多 |
| 150012 | InvalidFilterType | 无效过滤类型 |
| 150013 | InvalidFilterColumn | 无效过滤列 |
| 150014 | InvalidFilterOperator | 无效过滤操作符 |
| 150015 | InvalidFilterValue | 无效过滤值 |
| 150016 | InvalidOrderBy | 无效排序字段 |
| 150017 | ClickHouseQueryTimeout | ClickHouse 查询超时 |
| 150018 | EmptyTraceId | Trace ID 为空 |
| 150019 | OrgAndProjectBothEmpty | 组织与项目均为空 |
| 150020 | UpdateAgentRateFailed | 更新 Agent 配额失败 |
| 150021 | AgentSessionNotFound | Agent Session不存在 |
| 150022 | AgentConfigNotFound | Agent Config不存在 |
| 150023 | AgentReportTemplateNotFound | Agent 报表模板不存在 |
| 150024 | EmptyAgentReportTemplateName | Agent 报表模板名称为空 |

tReportTemplateNotFound | Agent 报表模板不存在 |
| 150024 | EmptyAgentReportTemplateName | Agent 报表模板名称为空 |

**Alert模块 (160000-160015)**

| errorCode | 常量名 | 含义 |
|-----------|--------|------|
| 160000 | AlertNotFound | Alert不存在 |
| 160001 | CreateAlertFailed | 创建Alert失败 |
| 160002 | UpdateAlertFailed | 更新Alert失败 |
| 160003 | DeleteAlertFailed | 删除Alert失败 |
| 160004 | InvalidAlertPeriod | 无效Alert周期 |
| 160005 | InvalidAlertFrequency | 无效Alert频率 |
| 160006 | InvalidAlertField | 无效Alert字段 |
| 160007 | InvalidAlertOperator | 无效Alert操作符 |
| 160008 | InvalidAlertValue | 无效Alert值 |
| 160010 | InvalidAlertName | 无效Alert名称 |
| 160011 | InvalidAlertNotifyBy | 无效Alert通知方式 |
| 160012 | SubscribeAlertFailed | 订阅Alert失败 |
| 160013 | AlertOrgNotAccessible | Alert组织不可访问 |
| 160014 | AlertProjectNotFound | Alert项目不存在 |
| 160015 | AlertNameTooLong | Alert名称过长 |

**Payment模块 (810001-810027)**

| errorCode | 常量名 | 含义 |
|-----------|--------|------|
| 810001 | WeChatSettingNotConfig | 微信设置未Config |
| 810002 | AlipaySettingNotConfig | Payment宝设置未Config |
| 810003 | AlipayConnectionError | Payment宝连接错误 |
| 810004 | AlipayTradeError | Payment宝交易错误 |
| 810005 | InvalidAlipayTradeNo | 无效Payment宝交易号 |
| 810006 | InvalidAlipayTransaction | 无效Payment宝交易 |
| 810007 | AlipaySignatureError | Payment宝签名错误 |
| 810008 | AlipaySignDictionaryError | Payment宝签名字典错误 |
| 810009 | InvalidWeChatSerialNO | 无效微信序列号 |
| 810010 | InvalidWeChatNotify | 无效微信通知 |
| 810011 | EmptyOrderNo | 订单号为空 |
| 810012 | DoNotOwnOrganization | 不拥有该组织 |
| 810013 | ProductNotExist | 产品不存在 |
| 810014 | ProductDurationNotExist | 产品时长不存在 |
| 810015 | OrderNotExist | 订单不存在 |
| 810016 | EmptyWeChatTransaction | 微信交易为空 |
| 810017 | InvalidWeChatTradeNo | 无效微信交易号 |
| 810018 | EmptyWeChatNotify | 微信通知为空 |
| 810019 | UnsupportedPayMethod | 不支持的Payment方式 |
| 810020 | AlipayPlaceOrderError | Payment宝下单错误 |
| 810021 | WeChatEmptyResponse | 微信空响应 |

| 810022 | WeChatErrorResponse | 微信错误响应 |
| 810023 | CannotDowngradeProduct | 不能降级产品 |
| 810024 | WeChatQueryErrorResponse | 微信查询错误响应 |
| 810025 | InvalidTotalAmount | 无效总金额 |
| 810026 | OrderStateUpdateFailed | 订单状态更新失败 |
| 810027 | InvalidMerchant | 无效商户 |

**微信模块 (620001-620017)**

| errorCode | 常量名 | 含义 |
|-----------|--------|------|
| 620001 | InvalidWeChatAppToken | 无效微信应用 Token |
| 620002 | ExamineWeChatSignatureFailed | 微信签名验证失败 |
| 620003 | GetWeChatTokenFailed | 获取微信 Token 失败 |
| 620004 | GetWeChatBasicUserInfoFailed | 获取微信用户信息失败 |
| 620005 | InvalidWeChatMessageType | 无效微信消息类型 |
| 620006 | InvalidWeChatMessageEvent | 无效微信消息事件 |
| 620007 | EmptyWeChatOpenId | 微信 OpenId 为空 |
| 620008 | InvalidWeChatCode | 无效微信 Code |
| 620009 | WeChatAccountBinded | 微信账号已绑定 |
| 620010 | WeChatAccountBeenBinded | 微信账号已被绑定 |
| 620011 | WeChatAccountNotBinded | 微信账号未绑定 |
| 620012 | InvalidWeChatAccount | 无效微信账号 |
| 620013 | MobileBindedWeChatAccount | 手机号已绑定微信账号 |
| 620014 | FakedWeChatRequest | 伪造的微信请求 |
| 620016 | InvalidPayCertificate | 无效Payment证书 |
| 620017 | GetPayCertificateFailed | 获取Payment证书失败 |

**通用模块 (990001-999999)**

| errorCode | 常量名 | 含义 |
|-----------|--------|------|
| 990001 | EncryptionFailed | 加密失败 |
| 990002 | DecryptionFailed | 解密失败 |
| 990003 | PasswordHashFailed | 密码哈希失败 |
| 990004 | InvalidJobQuantity | 无效任务数量 |
| 999999 | DefaultException | 默认异常 |

#### 10.2.2. 枚举定义参考

系统共定义 43 个枚举，以下列出接口开发中高频使用的枚举定义。完整清单见 `Models/Common/Enums/` 目录。

**Role** (`Models/Common/Enums/UserEnum.cs`)

| 枚举值 | 数值 | 说明 |
|--------|------|------|
| NONE | 0 | 无角色 |
| VIEWER | 1 | 只读用户，仅可查看数据 |
| MEMBER | 2 | 普通成员，可访问授权项目 |
| ADMIN | 3 | 管理员，可管理成员与项目 |
| OWNER | 4 | 组织所有者，拥有最高Privilege |

**LoginType** (`Models/Common/Enums/UserEnum.cs`)

| 枚举值 | 数值 | 说明 |
|--------|------|------|
| Password | 1 | 密码登录 |
| SMS | 2 | 短信Captcha登录 |
| WeChat | 3 | 微信登录 |
| MiniProgram | 4 | 微信小程序登录 |
| APIKey | 5 | API Key 登录 |

**FilterType** (`Models/Common/Enums/FilterEnum.cs`)

| 枚举值 | 数值 | 说明 |
|--------|------|------|
| DateTime | 1 | 日期时间过滤 |
| String | 2 | 字符串过滤 |
| Number | 3 | 数值过滤 |
| StringOptions | 4 | 字符串选项过滤 |
| ArrayOptions | 5 | 数组选项过滤 |
| Boolean | 6 | 布尔过滤 |
| Null | 7 | 空值过滤 |

**FilterOperator** (`Models/Common/Enums/FilterEnum.cs`)

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
| AnyOf | 10 | 任一 |
| NoneOf | 11 | 无一 |
| AllOf | 12 | 全部 |
| NotEqualTo | 13 | 不等于 |
| IsNull | 14 | 为空 |
| IsNotNull | 15 | 不为空 |

**FilterColumn** (`Models/Common/Enums/FilterEnum.cs`)

| 枚举值 | 数值 | 说明 |
|--------|------|------|
| Id | 1 | Trace ID |
| Name | 2 | 名称 |
| Timestamp | 3 | 时间戳 |
| UserId | 4 | User ID |
| SessionId | 5 | Session ID |
| Environment | 6 | 环境 |
| Version | 7 | 版本 |
| Release | 8 | 发布 |
| Tags | 9 | 标签 |
| Bookmarked | 10 | 书签 |
| Latency | 11 | 延迟 |
| InputTokens | 12 | 输入 Token |
| OutputTokens | 13 | 输出 Token |
| TotalTokens | 14 | 总 Token |
| Tokens | 15 | Token |
| InputCost | 16 | 输入成本 |
| OutputCost | 17 | 输出成本 |
| TotalCost | 18 | 总成本 |
| Level | 19 | 级别 |
| WarningCount | 20 | 警告数 |
| ErrorCount | 21 | 错误数 |
| DefaultCount | 22 | 默认数 |
| DebugCount | 23 | 调试数 |
| ModelNames | 24 | 模型名称 |
| ScoresAvg | 25 | 平均Score |

**AlertField** (`Models/Common/Enums/AlertEnum.cs`)

| 枚举值 | 数值 | 说明 |
|--------|------|------|
| TotalTokens | 1 | 总 Token 数 |
| TotalCost | 2 | 总成本 |
| ErrorCount | 3 | 错误数 |
| Latency | 4 | 延迟 |
| ErrorRate | 5 | 错误率 |
| InputTokens | 6 | 输入 Token |
| OutputTokens | 7 | 输出 Token |
| WarningCount | 8 | 警告数 |
| ObservationCount | 9 | Observation 数 |

**AlertOperator** (`Models/Common/Enums/AlertEnum.cs`)

| 枚举值 | 数值 | 说明 |
|--------|------|------|
| GreaterThan | 1 | 大于 |
| LessThan | 2 | 小于 |
| EqualTo | 3 | 等于 |
| GreaterThanOrEqualTo | 4 | 大于等于 |
| LessThanOrEqualTo | 5 | 小于等于 |
| NotEqualTo | 6 | 不等于 |

**TradeState** (`Models/Common/Enums/PaymentEnums.cs`)

| 枚举值 | 数值 | 说明 |
|--------|------|------|
| SUCCESS | 1 | Payment成功 |
| REFUND | 2 | 转入退款 |
| NOTPAY | 3 | 未Payment |
| CLOSED | 4 | 已关闭 |
| REVOKED | 5 | 已撤销 |
| USERPAYING | 6 | 用户Payment中 |
| PAYERROR | 7 | Payment失败 |
| TRADE_CLOSED | 10 | 交易关闭 |
| TRADE_FINISHED | 11 | 交易完成 |
| TRADE_SUCCESS | 12 | 交易成功 |
| WAIT_BUYER_PAY | 13 | 等待买家付款 |

交易关闭 |
| TRADE_FINISHED | 11 | 交易完成 |
| TRADE_SUCCESS | 12 | 交易成功 |
| WAIT_BUYER_PAY | 13 | 等待买家付款 |

**SubPayMethod** (`Models/Common/Enums/PaymentEnums.cs`)

| 枚举值 | 数值 | 说明 |
|--------|------|------|
| WECHAT_JSAPI | 1 | 微信 JSAPI Payment |
| WECHAT_NATIVE | 2 | 微信 Native Payment |
| WECHAT_MINIPROGRAM | 3 | 微信小程序Payment |
| ALIPAY_FAST_INSTANT_TRADE_PAY | 11 | Payment宝即时到账 |

### 10.3. 需求Trace矩阵

以下矩阵将功能需求 FR-001 至 FR-076 与 HTTP 端点、Controller 方法一一对应，确保每个需求均可追溯至具体实现。

/api/user/bind/wechat | UserController.Bind | API/Controllers/UserManagement/UserController.cs:117 |
| FR-008 | 解绑微信 | GET /api/user/unbind/wechat | UserController.UnBind | API/Controllers/UserManagement/UserController.cs:132 |
| FR-009 | 分配角色 | POST /api/user/role | UserController.AssignRole | API/Controllers/UserManagement/UserController.cs:147 |
| FR-010 | 邀请成员 | POST /api/user/invite | UserController.Invite | API/Controllers/UserManagement/UserController.cs:162 |
| FR-011 | 获取邀请列表 | GET /api/user/invitation | UserController.Get | API/Controllers/UserManagement/UserController.cs:177 |
| FR-012 | 删除邀请 | POST /api/user/invitation/delete | UserController.DeleteInvitation | API/Controllers/UserManagement/UserController.cs:192 |
| FR-013 | 创建 API Key | POST /api/user/apikey | UserController.CreateApiKey | API/Controllers/UserManagement/UserController.cs:209 |
| FR-014 | 获取 API Key | GET /api/user/apikey | UserController.Get | API/Controllers/UserManagement/UserController.cs:225 |

user/config | UserConfigController.Get | API/Controllers/UserManagement/UserConfigController.cs:31 |
| FR-027 | 创建用户Config | POST /api/user/config | UserConfigController.Post | API/Controllers/UserManagement/UserConfigController.cs:44 |
| FR-028 | 更新用户Config | POST /api/user/config/update | UserConfigController.Update | API/Controllers/UserManagement/UserConfigController.cs:57 |
| FR-029 | 删除用户Config | GET /api/user/config/delete | UserConfigController.Delete | API/Controllers/UserManagement/UserConfigController.cs:71 |
| FR-030 | 获取Captcha | GET /api/captcha | CaptchaController.Get | API/Controllers/UserManagement/CaptchaController.cs:29 |
| FR-031 | 获取短信Captcha | GET /api/captcha/sms | CaptchaController.GetSMSCaptcha | API/Controllers/UserManagement/CaptchaController.cs:43 |
| FR-032 | 获取AlertConfig | GET /api/alert/config | AlertController.GetConfig | API/Controllers/UserManagement/AlertController.cs:30 |

tions | MetricsController.GetObservations | API/Controllers/DataManagement/MetricsController.cs:34 |
| FR-040 | 查询 Score | GET /api/data/metrics/scores | MetricsController.GetScores | API/Controllers/DataManagement/MetricsController.cs:50 |
| FR-041 | 查询 Trace (GET) | GET /api/data/metrics/traces | MetricsController.GetTraces | API/Controllers/DataManagement/MetricsController.cs:64 |
| FR-042 | 查询 Trace (POST) | POST /api/data/metrics/traces | MetricsController.GetTraces | API/Controllers/DataManagement/MetricsController.cs:125 |
| FR-043 | 获取模型列表 | GET /api/data/model | ModelController.Get | API/Controllers/DataManagement/ModelController.cs:34 |
| FR-044 | 微信Payment回调 | POST /api/payment/notify/wechatnotify | NotifyController.WeChatNotify | API/Controllers/PaymentManagement/NotifyController.cs:29 |
| FR-045 | Payment宝Payment回调 | POST /api/payment/notify/alipaynotify | NotifyController.AlipayNotify | API/Controllers/PaymentManagement/NotifyController.cs:57 |

ynotify | NotifyController.AlipayNotify | API/Controllers/PaymentManagement/NotifyController.cs:57 |
| FR-046 | 获取订单 | GET /api/payment/order | OrderController.Get | API/Controllers/PaymentManagement/OrderController.cs:34 |
| FR-047 | 创建订单 | POST /api/payment/order | OrderController.Place | API/Controllers/PaymentManagement/OrderController.cs:48 |
| FR-048 | 查询订单 | GET /api/payment/order/query | OrderController.Query | API/Controllers/PaymentManagement/OrderController.cs:64 |
| FR-049 | 获取转化率 | GET /api/payment/order/conversion | OrderController.GetConversion | API/Controllers/PaymentManagement/OrderController.cs:79 |
| FR-050 | 获取产品列表 | GET /api/product | ProductController.Get | API/Controllers/ProductManagement/ProductController.cs:26 |
| FR-051 | 获取产品时长 | GET /api/product/duration | ProductController.GetDuration | API/Controllers/ProductManagement/ProductController.cs:38 |

ration | ProductController.GetDuration | API/Controllers/ProductManagement/ProductController.cs:38 |
| FR-052 | 发布Bulletin | POST /api/tools/bulletin | BulletinController.Post | API/Controllers/ToolsManagement/BulletinController.cs:32 |
| FR-053 | 获取协议 | GET /api/tools/bulletin/agreement | BulletinController.Get | API/Controllers/ToolsManagement/BulletinController.cs:45 |
| FR-054 | 获取Bulletin列表 | GET /api/tools/bulletin/bulletins | BulletinController.GetBulletins | API/Controllers/ToolsManagement/BulletinController.cs:64 |
| FR-055 | 获取后台Bulletin | GET /api/tools/bulletin/backend | BulletinController.GetBackendBulletins | API/Controllers/ToolsManagement/BulletinController.cs:82 |
| FR-056 | 审批Bulletin | POST /api/tools/bulletin/approve | BulletinController.ApproveBulletin | API/Controllers/ToolsManagement/BulletinController.cs:96 |
| FR-057 | 修订Bulletin | POST /api/tools/bulletin/revision | BulletinController.ReviseBulletin | API/Controllers/ToolsManagement/BulletinController.cs:110 |

on | BulletinController.ReviseBulletin | API/Controllers/ToolsManagement/BulletinController.cs:110 |
| FR-058 | 关闭Bulletin | POST /api/tools/bulletin/close | BulletinController.CloseBulletin | API/Controllers/ToolsManagement/BulletinController.cs:124 |
| FR-059 | 健康检查 | GET /api/tools/health | HealthController.Get | API/Controllers/ToolsManagement/HealthController.cs:20 |
| FR-060 | 获取微信消息 | GET /api/tools/wechat | WeChatController.Get | API/Controllers/ToolsManagement/WeChat/WeChatController.cs:36 |
| FR-061 | 处理微信消息 | POST /api/tools/wechat | WeChatController.Post | API/Controllers/ToolsManagement/WeChat/WeChatController.cs:68 |
| FR-062 | 获取 Agent Config | GET /api/agent/config | AgentConfigController.Get | API/Controllers/AgentManagement/AgentConfigController.cs:28 |
| FR-063 | 删除 Agent Config | GET /api/agent/config/delete | AgentConfigController.Delete | API/Controllers/AgentManagement/AgentConfigController.cs:40 |

elete | AgentConfigController.Delete | API/Controllers/AgentManagement/AgentConfigController.cs:40 |
| FR-064 | 创建/更新 Agent Config | POST /api/agent/config | AgentConfigController.Post | API/Controllers/AgentManagement/AgentConfigController.cs:54 |
| FR-065 | 获取报表模板 | GET /api/agent/report | AgentReportController.GetTemplates | API/Controllers/AgentManagement/AgentReportController.cs:35 |
| FR-066 | 删除报表模板 | GET /api/agent/report/delete | AgentReportController.DeleteTemplates | API/Controllers/AgentManagement/AgentReportController.cs:48 |
| FR-067 | 创建/更新报表模板 | POST /api/agent/report | AgentReportController.CreateOrUpdateTemplate | API/Controllers/AgentManagement/AgentReportController.cs:62 |
| FR-068 | 获取Session列表 | GET /api/agent/session | AgentSessionController.Get | API/Controllers/AgentManagement/AgentSessionController.cs:33 |
| FR-069 | 删除Session | GET /api/agent/session/delete | AgentSessionController.Delete | API/Controllers/AgentManagement/AgentSessionController.cs:46 |

ete | AgentSessionController.Delete | API/Controllers/AgentManagement/AgentSessionController.cs:46 |
| FR-070 | 创建/更新Session | POST /api/agent/session | AgentSessionController.Post | API/Controllers/AgentManagement/AgentSessionController.cs:60 |
| FR-071 | Chat Completions | POST /api/agent/insight | chat_completions | Agents/server.py:346 |
| FR-072 | Session列表 | GET /api/sessions | list_sessions | Agents/server.py:614 |
| FR-073 | Session详情 | GET /api/sessions/{session_id} | get_session | Agents/server.py:622 |
| FR-074 | 删除Session | DELETE /api/sessions/{session_id} | delete_session | Agents/server.py:633 |
| FR-075 | 清理过期Session | POST /api/sessions/cleanup | cleanup_expired_sessions | Agents/server.py:641 |
| FR-076 | Agent 列表 | GET /api/agents | list_agents | Agents/server.py:649 |

### 10.4. 开源依赖清单

以下为 AgentInsightService 项目使用的开源依赖及其版本信息，分为 .NET 后端与 Python Agents 服务两部分。

**.NET 后端依赖**

| 依赖包名 | 用途 | 版本 |
|----------|------|------|
| Furion | 应用框架，提供 RESTful API 基础设施 | 由项目引用 |
| SqlSugar | ORM 框架，用于 PostgreSQL 与 ClickHouse 数据访问 | 由项目引用 |
| Npgsql | PostgreSQL 数据库驱动 | 由项目引用 |
| StackExchange.Redis | Redis 客户端，用于分布式缓存与消息队列 | 由项目引用 |
| Yarp.ReverseProxy | 反向代理，将 /api/public/{**catch-all} 代理到 Langfuse 兼容后端 | 由项目引用 |
| MediatR | 进程内消息传递，用于解耦Payment回调、Alert触发等通知处理 | 由项目引用 |
| AlipaySDKNet.Standard | Payment宝Payment SDK | 由项目引用 |
| BouncyCastle.Cryptography | 加密算法库，用于Payment签名验证 | 由项目引用 |
| Microsoft.SemanticKernel | AI 编排框架，用于 Agent 能力集成 | 由项目引用 |
| My.Extensions.Localization.Json | JSON 本地化扩展，支持多语言资源 | 由项目引用 |
| Microsoft.VisualStudio.Azure.Containers.Tools.Targets | Docker 容器构建支持 | 由项目引用 |

**Python Agents 服务依赖**

| 依赖包名 | 用途 | 版本 |
|----------|------|------|
| LangChain.Providers.OpenAI | OpenAI 模型接入 | 由项目引用 |
| agentinsight-sdk | AgentInsight 官方 SDK | 由项目引用 |
| openai | OpenAI API 客户端 | 由项目引用 |
| httpx | HTTP 客户端 | 由项目引用 |
| pydantic | 数据验证与设置管理 | 由项目引用 |
| pydantic-settings | 设置管理扩展 | 由项目引用 |
| fastapi | Web 框架 | 由项目引用 |
| uvicorn | ASGI 服务器 | 由项目引用 |

**Python 运行时依赖 (部分)**

| 依赖包名 | 版本 |
|----------|------|
| websockets | 15.0.1 |
| charset_normalizer | 3.4.7 |
| chardet | 7.4.3 |
| pyyaml | 6.0.3 |
| xxhash | 3.7.0 |
| wrapt | 1.17.3 |
| psycopg2_binary | 2.9.10 |
| pydantic_core | 2.46.4 |
| uuid_utils | 0.16.2 |
| ormsgpack | 1.12.2 |
| zstandard | 0.25.0 |
| grpcio | 1.81.1 |
| orjson | 3.11.9 |
| jiter | 0.15.0 |
| numpy | 2.4.6 |
| lxml | 6.1.1 |
| primp | 1.3.1 |
| protobuf | 6.33.6 |
| concurrent_log_handler | 0.9.25 |
| requests_toolbelt | 1.0.0 |
| django_import_export | 4.3.7 |
| langgraph_checkpoint | 4.1.1 |
| opentelemetry_proto | 1.42.1 |
| langchain_protocol | 0.0.18 |
| diff_match_patch | 20241021 |
| googleapis_common_protos | 1.75.0 |

以上依赖版本信息来自项目Config文件，实际部署时请以 lock 文件或包Manager解析结果为准。

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

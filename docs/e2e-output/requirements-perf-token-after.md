## 1. 引言

AgentInsightService（保持原文） 是一个面向组织的 AI Agent 可Observation性与Payment管理平台，系统提供 Trace 数据采集与分析、Alert（Alert）、用户与组织管理、Payment集成（微信Payment/Payment宝Payment）以及 Agent Config管理能力。本文档为 AgentInsightService（保持原文） V1.0 的技术设计说明，旨在为研发、测试、运维及产品 stakeholders 提供完整的系统架构、模块划分、接口规范与部署运维参考。文档内容严格基于代码仓库的实际实现提取，所有功能描述、接口路径、Config项与错误码均可在仓库对应文件中追溯验证。

### 1.1. 编写目的与目标读者

本文档的编写目的是为 AgentInsightService（保持原文） V1.0 提供一份完整、准确、可追溯的技术参考，使不同角色的读者能够快速理解系统全貌并据此开展相应工作。文档内容覆盖系统架构、核心模块职责、接口契约、数据模型与部署依赖，所有描述均与代码仓库实现保持一致。

目标读者及关注重点如下：

| 读者角色 | 关注重点 | 对应章节 |
|---------|---------|---------|
| 研发工程师 | 模块划分、类职责、接口实现、依赖关系 | 系统架构、模块设计、接口详情 |
| 测试工程师 | 接口契约、错误码定义、验收标准、边界条件 | 接口详情、功能需求、错误码表 |
| 运维工程师 | 部署拓扑、外部依赖、Config项、环境变量 | 部署运维、Config规格、依赖清单 |
| 产品经理/Stakeholders | 产品定位、功能范围、业务价值、优先级 | 产品背景、文档范围、版本规划 |

研发工程师可通过本文档定位核心 Handler 与 Service 的实现位置，例如用户管理入口 `UserHandler` [API/Handlers/UserManagement/UserHandler.cs]、Trace 查询入口 `MetricsHandler` [API/Handlers/DataManagement/MetricsHandler.cs]、Payment服务 `PaymentService` [API/Common/Services/PaymentService.cs] 等。测试工程师可依据接口详情章节的请求/响应格式与错误码表编写测试用例。运维工程师可参考Config规格章节的环境变量清单完成环境部署。

### 1.2. 产品背景与业务痛点

随着组织内 AI Agent 应用规模的快速增长，系统可Observation性与商业化运营面临以下核心痛点：

**Trace 指标混乱**：AI Agent 运行过程中产生的 Trace 数据分散存储，缺乏统一的采集、过滤与查询机制。`MetricsHandler` 虽提供 Trace/Observation/Score 的分页查询能力 [API/Handlers/DataManagement/MetricsHandler.cs:12-16]，但数据分散在 ClickHouse 与 PostgreSQL 多套存储中，查询链路复杂，难以形成统一的Observation视图。`TraceFilterBuilder` 负责构建过滤条件 [API/Common/Helpers/TraceFilterBuilder.cs]，但缺乏标准化的指标口径，导致不同团队对同一指标的理解不一致。

**Payment集成复杂**：系统需要同时支持微信Payment（JSAPI/Native/MiniProgram）与Payment宝Payment [API/Common/Services/PaymentService.cs:14-35]，涉及订单创建、签名验证、异步回调、交易查询等多个环节。`OrderHandler` 负责下单与产品转换计算 [API/Handlers/PaymentManagement/OrderHandler.cs:12-18]，`NotifyHandler` 处理Payment回调 [API/Handlers/PaymentManagement/NotifyHandler.cs:12-14]，Payment平台接口的差异性与回调签名验证的复杂性显著增加了集成成本。

**Alert机制缺失**：组织缺乏对 AI Agent 运行状态的主动监控能力。`AlertService` 提供Alert评估服务 [API/Common/Services/AlertService.cs:12-16]，但Alert规则的Config、触发通知（System/SMS）的链路尚未形成闭环 [API/Notifications/SystemAlertHandler.cs:10, API/Notifications/SMSAlertHandler.cs:10]，运维人员难以及时发现异常。

AgentInsightService（保持原文） 的定位正是解决上述痛点，为组织提供统一的 AI Agent 可Observation性平台，将 Trace 采集、指标分析、Alert通知、Payment管理与 Agent Config纳入同一技术体系，降低运维复杂度并支撑商业化闭环。

### 1.3. 文档范围

本文档覆盖 AgentInsightService（保持原文） 的 API 子项目（In-Scope），即仓库中 `API/` 目录下的全部业务功能模块。具体包括：

| 功能域 | 覆盖内容 | 关键实现 |
|-------|---------|---------|
| 用户与组织管理 | 注册/登录/登出、Org/Project CRUD、角色分配、API Key 管理 | `UserHandler` [API/Handlers/UserManagement/UserHandler.cs:17-35]、`OrganizationHandler` [API/Handlers/UserManagement/OrganizationHandler.cs:12-16] |
| Payment管理 | 订单创建/查询、微信Payment/Payment宝PaymentPayment、回调处理、产品转换 | `OrderHandler` [API/Handlers/PaymentManagement/OrderHandler.cs:12-18]、`NotifyHandler` [API/Handlers/PaymentManagement/NotifyHandler.cs:12-14] |
| 数据管理 | Trace 查询与过滤、Observation/Score 查询、Model 定义查询 | `MetricsHandler` [API/Handlers/DataManagement/MetricsHandler.cs:12-16]、`ModelHandler` [API/Handlers/DataManagement/ModelHandler.cs:12] |
| Alert管理 | Alert规则 CRUD、Alert记录查询、触发通知 | `AlertHandler` [API/Handlers/UserManagement/AlertHandler.cs:12-17]、`AlertService` [API/Common/Services/AlertService.cs:12-16] |
| Agent 管理 | Agent Config、报告模板、Session管理 | `AgentConfigHandler` [API/Handlers/AgentManagement/AgentConfigHandler.cs:12-14]、`AgentReportHandler` [API/Handlers/AgentManagement/AgentReportHandler.cs:12-14] |

以下组件为 Out-of-Scope，不在本文档描述范围内：

- **Agents 子项目**：独立的 Python FastAPI Service，提供 AI Agent 运行时 [Agents/server.py:1-50]
- **Admin 子项目**：Django 管理后台 [Admin/manage.py]，独立部署
- **UnitTest/Utility/Tools**：测试与工具库，非业务功能

### 1.4. 术语与缩略语

本文档涉及的关键术语与缩略语定义如下，代码标识符保留原始英文：

| 术语 | 定义 |
|------|------|
| AgentInsightService（保持原文） | 项目名称，面向组织的 AI Agent 可Observation性与Payment管理平台 |
| Trace | 一次 AI Agent 请求的完整调用链Trace记录 |
| Observation | Trace 下的Observation数据单元，记录单次操作或调用详情 |
| Score | 对 Trace 或 Observation 的Score数据 |
| Org Admin/Owner | 组织管理员/所有者，拥有组织级管理Privilege |
| Project Admin | 项目管理员，拥有项目级管理Privilege |
| Basic Auth | 基于 PublicKey/SecretKey 的 HTTP 认证方式 |
| JWT | JSON Web Token，用于用户Session认证 |
| API Key | 外部系统访问 API 的密钥凭证 |
| ClickHouseHelper | ClickHouse 查询辅助类 [API/Common/Helpers/ClickHouseHelper.cs] |
| TraceFilterBuilder | Trace 过滤条件构建器 [API/Common/Helpers/TraceFilterBuilder.cs] |
| BullMqService | 基于 Redis 的消息队列服务 [API/Common/Services/BullMqService.cs] |
| ClickHouseClient | ClickHouse 数据库客户端 [API/Common/Services/ClickHouseClient.cs] |
| AlertService | Alert评估服务 [API/Common/Services/AlertService.cs] |
| PaymentService | Payment核心服务 [API/Common/Services/PaymentService.cs] |
| WeChatService | 微信服务，处理 AccessToken 获取与签名验证 [API/Common/Services/WeChatService.cs] |
| ApiHandlerBase | Handler 基类，提供Privilege验证与审计日志 [API/Handlers/ApiHandlerBase.cs] |
| AgentInsightTransformProvider | API 网关转换提供者 [API/System/Handlers/AgentInsightTransformProvider.cs] |

### 1.5. 参考文档

本文档编写过程中参考了以下代码仓库资源：

| 参考类型 | 内容 | 位置 |
|---------|------|------|
| Config规格 | 环境变量、连接字符串、JWT 设置、Captcha参数 | `Configurations/` 目录 |
| 枚举清单 | 错误码、订单状态、Payment类型、Agent 类型 | `Models/Common/Enums/AgentInsightEnum.cs`、`Models/Common/Enums/PaymentEnums.cs`、`Models/Common/Enums/UserEnum.cs` |
| HTTP 端点全集 | 各 Controller 的路由定义与请求/响应格式 | `API/Controllers/` 目录 |
| 关键模块依赖 | Handler 与 Service 之间的调用关系 | `API/Handlers/`、`API/Common/Services/` 目录 |
| 认证授权机制 | JWT 认证、API Key 认证、角色Privilege控制 | `API/System/Handlers/`、`API/Handlers/ApiHandlerBase.cs` |

### 1.6. 版本历史

| 版本 | 日期 | 作者 | 修订说明 |
|------|------|------|---------|
| V1.0 | 2025-01-15 | 技术文档组 | 本文档创建，完成 AgentInsightService（保持原文） V1.0 全部章节的初稿编写，覆盖系统架构、模块设计、接口规范与部署运维说明 |

---

## 2. 产品概述与用户分析

### 2.1. 功能边界

AgentInsightService（保持原文） 是一个面向组织的 AI Agent 可Observation性与Payment管理平台，核心功能模块如下：

- **可Observation性数据管理**：通过 `MetricsHandler` 提供 Trace 查询与过滤、Observation 查询、Score 查询能力 [API/Handlers/DataManagement/MetricsHandler.cs:12-16]，底层依赖 ClickHouse 存储与查询引擎 [API/Common/Services/ClickHouseClient.cs:8]
- **Alert管理**：通过 `AlertService` 定期评估指标是否满足Alert条件 [API/Common/Services/AlertService.cs:12-16]，触发时通过 System/SMS 双通道通知 [API/Notifications/SystemAlertHandler.cs:10, API/Notifications/SMSAlertHandler.cs:10]
- **Payment管理**：通过 `PaymentService` 处理微信Payment（JSAPI/Native/MiniProgram）与Payment宝Payment [API/Common/Services/PaymentService.cs:14-35]，支持订单创建、签名验证、交易查询与回调处理
- **用户与组织管理**：通过 `UserHandler` 处理注册/登录/登出、Org CRUD、Project CRUD、角色分配、API Key 管理 [API/Handlers/UserManagement/UserHandler.cs:17-35]
- **Agent Config管理**：通过 `AgentConfigHandler` 管理 Agent 数据源连接与默认报告模板 [API/Handlers/AgentManagement/AgentConfigHandler.cs:12-14]

### 2.2. 价值主张

AgentInsightService（保持原文） 面向三类核心利益相关方，分别提供差异化的价值：

**组织管理员（Org Admin/Owner）**：获得组织维度的全局可Observation性视图与商业化管控能力。管理员可以创建组织、管理成员角色、查看组织下所有项目的 Trace 数据与Alert状态，并通过Payment集成实现产品订阅的自动化管理。Privilege控制通过 `ApiHandlerBase` 中的 `RequireOrgAdmin`、`RequireOrgOwner` 方法实现 [API/Handlers/ApiHandlerBase.cs:28-32]。

**项目管理员（Project Admin）**：获得项目粒度的数据洞察与AlertConfig能力。项目管理员可以针对特定项目创建Alert规则、查询 Trace 数据、管理 Agent Config，并通过 `RequireProjectAdmin` 方法进行细粒度Privilege校验 [API/Handlers/ApiHandlerBase.cs:28-32]。

**API 消费者**：获得标准化的数据接入通道。外部系统通过 Basic Auth（PublicKey/SecretKey）或 JWT Token 认证接入平台 [API/System/Handlers/AgentInsightTransformLogic.cs:9-10]，实现 Trace 数据上报、指标查询等能力，由 `AgentInsightTransformProvider` 统一处理认证与速率限制 [API/System/Handlers/AgentInsightTransformProvider.cs:12-15]。

平台的差异化价值体现在三个维度：

1. **可Observation性 + 商业化闭环**：不同于纯监控工具或纯Payment网关，AgentInsightService（保持原文） 将 Trace 数据采集分析与Payment管理整合在同一平台，使 AI Agent 的运营者能够直接基于可Observation性数据驱动商业化决策。
2. **多租户组织模型**：以组织-项目两级结构实现数据隔离与Privilege控制，支持从个人开发者到企业级组织的平滑扩展。
3. **多渠道Payment集成**：原生支持微信Payment（JSAPI/Native/MiniProgram）与Payment宝Payment [API/Common/Services/PaymentService.cs:14-35]，覆盖中国主流Payment场景。

### 2.3. 北极星指标

AgentInsightService（保持原文） 的北极星指标由三个独立子指标构成，分别衡量平台的活跃度、可Observation性价值与商业化效率：

| 子指标 | 目标值 | 衡量维度 | 计算方式 | 关联功能 |
|--------|--------|----------|----------|----------|
| MAO | 持续增长 | 平台采用度 | 当月有任意活跃操作（登录、数据查询、AlertConfig、Payment等）的组织数量 | Org CRUD、Project CRUD [API/Handlers/UserManagement/OrganizationHandler.cs:12-16] |
| 平均Alert响应时间 | ≤ 5min | 可Observation性价值 | 从Alert条件满足到用户收到通知的平均时间间隔 | AlertService 评估 [API/Common/Services/AlertService.cs:12-16]、System/SMS 通知 [API/Notifications/SystemAlertHandler.cs:10] |
| Payment转化率 | ≥ 85% | 商业化效率 | Payment成功订单数 / 创建订单总数 × 100% | 微信Payment/Payment宝PaymentPayment [API/Common/Services/PaymentService.cs:14-35]、回调处理 [API/Handlers/PaymentManagement/NotifyHandler.cs:12-14] |

北极星指标的选择逻辑：月活跃组织数反映平台的核心价值被多少组织认可；平均Alert响应时间衡量可Observation性功能是否真正帮助用户快速发现问题；Payment转化率则验证商业化闭环的顺畅程度。三个指标相互关联——Alert响应越快，用户对平台的信任度越高，Payment转化率也随之提升。

### 2.4. 用户角色与Privilege矩阵

AgentInsightService（保持原文） RBAC模型，通过 `ApiHandlerBase` 提供细粒度的Privilege验证方法 [API/Handlers/ApiHandlerBase.cs:24-32]。系统定义四类用户角色：

| Role | Privilege验证方法 | 核心能力 | 典型场景 |
|------|-------------|----------|----------|
| 组织所有者（Org Owner） | `RequireOrgOwner` | 组织全量管理、成员角色分配、删除组织 | 组织创建者，拥有最高管理Privilege |
| 组织管理员（Org Admin） | `RequireOrgAdmin` | 组织信息维护、项目创建、成员管理 | 组织日常运营管理者 |
| 项目管理员（Project Admin） | `RequireProjectAdmin` | 项目数据查看、AlertConfig、Agent Config | 具体项目或业务线的负责人 |
| 普通成员 | `RequireOrgMembership` | 项目数据查看、Trace 查询 | 组织内的一般开发者或分析师 |

Privilege验证在 Handler 层统一执行。所有 Handler 继承自 `ApiHandlerBase`，在进入业务逻辑前通过 `RequireOrgAdmin`、`RequireOrgOwner`、`RequireProjectAdmin`、`RequireOrgMembership` 方法进行Privilege校验 [API/Handlers/ApiHandlerBase.cs:24-32]。用户上下文通过 `AutoSetUserFilter` 自动设置 [API/System/Handlers/AutoSetUserFilter.cs:8]，确保每个请求都能正确识别当前用户及其角色。

认证方式支持双通道：

| 认证方式 | 机制 | 适用场景 |
|----------|------|----------|
| JWT 认证 | HS256 算法，有效期 12 小时（43200 秒） | 交互式 Web User |
| API Key 认证 | PublicKey/SecretKey 通过 Basic Auth 传递 | 外部系统 API 消费者 |

JWT Config项包括 `Jwt.Algorithm = HS256`、`Jwt.ExpiresInSeconds = 43200`、`Jwt.SecretKey = ${JWT_SECRET_KEY}` 等。API Key 认证由 `AgentInsightTransformProvider` 处理 Basic Auth 解析与速率限制 [API/System/Handlers/AgentInsightTransformProvider.cs:12-15]。

### 2.5. 核心业务流程

#### 2.5.1. Payment流程

Payment流程是 AgentInsightService（保持原文） 商业化闭环的核心链路，涉及订单创建、Payment平台交互、异步回调与状态更新四个阶段：

1. **下单**：用户通过 `POST /api/payment/order` 发起下单请求 [API/Controllers/PaymentManagement/OrderController.cs:48]，`OrderHandler.PlaceOrder` 创建订单并调用 `PaymentService` 获取Payment参数 [API/Handlers/PaymentManagement/OrderHandler.cs:13]
2. **订单创建**：`PaymentService.CreateOrder` 生成订单号（格式：`yyyyMMddHHmmssfff` + 7 位随机数），设置初始状态为 `PaymentStatus.Pending` 与 `PaymentOrderStatus.Created` [API/Common/Services/PaymentService.cs]
3. **Payment平台交互**：根据Payment方式调用微信Payment（JSAPI/Native/MiniProgram）或Payment宝Payment接口 [API/Common/Services/PaymentService.cs:14-35]
4. **异步回调**：Payment平台异步通知到 `POST /api/payment/notify/wechatnotify` 或 `/alipaynotify` [API/Controllers/PaymentManagement/NotifyController.cs:29,57]，`NotifyHandler` 验证签名后更新订单状态为 `PaymentStatus.Paid` [API/Handlers/PaymentManagement/NotifyHandler.cs:13-14]
5. **异步通知**：通过 MediatR 发布 `PaymentTransactionNotification` 触发异步保存 [API/Notifications/PaymentTransactionNotification.cs:8]，`PaymentTransactionSaveHandler` 处理交易记录持久化

#### 2.5.2. Alert流程

Alert流程实现从规则Config到多通道通知的完整闭环：

1. **规则创建**：用户通过 `POST /api/alert` 创建Alert规则 [API/Controllers/UserManagement/AlertController.cs:61]，支持Config指标字段（总 Token 消耗/总消费/错误次数）、操作符（大于/小于/等于）、时间单位（分钟/小时/天）与通知方式（系统通知/短信+系统通知）
2. **定期评估**：`AlertService` 定期评估指标是否满足Alert条件 [API/Common/Services/AlertService.cs:12-16]，通过 `GetTimeSpan` 计算时间窗口、`IsConditionMet` 判断条件是否满足
3. **触发通知**：条件满足时发布 `AlertTriggeredNotification` [API/Notifications/AlertTriggeredNotification.cs:5]
4. **多通道分发**：`SystemAlertHandler` 处理系统站内通知 [API/Notifications/SystemAlertHandler.cs:10]，`SMSAlertHandler` 处理短信通知 [API/Notifications/SMSAlertHandler.cs:10]

#### 2.5.3. 用户与组织管理流程

用户与组织管理是平台多租户模型的基础：

1. **用户注册/登录**：通过 `UserHandler` 处理注册、登录、登出 [API/Handlers/UserManagement/UserHandler.cs:17-20]，`UserService.CreateNewUser` 创建新用户并校验手机号唯一性
2. **组织管理**：通过 `OrganizationHandler` 实现组织 CRUD [API/Handlers/UserManagement/OrganizationHandler.cs:12-16]，组织创建者自动成为 Org Owner
3. **项目管理**：通过 `ProjectHandler` 实现项目 CRUD [API/Handlers/UserManagement/ProjectHandler.cs:12-16]，项目归属于特定组织
4. **角色分配**：通过 `UserHandler` 的角色分配功能管理成员Privilege [API/Handlers/UserManagement/UserHandler.cs:24]
5. **API Key 管理**：通过 `UserHandler` 的 API Key 管理功能生成和管理 PublicKey/SecretKey 对 [API/Handlers/UserManagement/UserHandler.cs:33-35]

整个流程通过 `ApiHandlerBase` 的 `LogAudit` 方法记录操作审计日志 [API/Handlers/ApiHandlerBase.cs:34]，确保所有管理操作可追溯。

---

## 3. 功能需求

### 3.1. FR-001 创建组织 [优先级: Must]

- **用户故事**: 作为组织管理员，我希望创建新的组织，以便管理组织成员和项目资源。
- **主流程**:
  1. 用户调用 `POST /api/user/organization` 提交组织创建请求 [API/Controllers/UserManagement/OrganizationController.cs:28]
  2. `OrganizationController.Post` 接收请求并调用 `OrganizationHandler` 处理
  3. `OrganizationHandler` 验证当前用户身份，创建组织记录并建立创建者的 OWNER 成员关系
- **验收标准**:
  - [ ] AC1: 请求成功时返回 errorCode=0 且响应包含组织 ID 字段
  - [ ] AC2: 创建者自动成为组织的 OWNER 角色成员
  - [ ] AC3: 未登录用户调用返回 401 未授权
- **业务规则**:
  - BR-001: 组织名称在系统内必须唯一
  - BR-002: 组织创建者自动获得 OWNER Role，拥有组织全部管理Privilege

#### 3.1.1. FR-002 查询组织列表 [优先级: Must]

- **用户故事**: 作为组织管理员，我希望查询当前用户所属的组织列表，以便切换组织进行管理。
- **主流程**:
  1. 用户调用 `GET /api/user/organization` 获取组织列表 [API/Controllers/UserManagement/OrganizationController.cs:42]
  2. `OrganizationController.Get` 调用 `OrganizationHandler` 查询当前用户加入的组织
  3. 返回组织列表及当前用户在各组织中的角色
- **验收标准**:
  - [ ] AC1: 请求成功时返回 errorCode=0 且响应包含组织列表数据
  - [ ] AC2: 仅返回当前用户所属的组织，不返回其他组织
- **业务规则**:
  - BR-003: 组织列表按创建时间倒序排列

#### 3.1.2. FR-003 更新组织信息 [优先级: Must]

- **用户故事**: 作为组织 OWNER，我希望更新组织名称和描述，以便维护组织信息的准确性。
- **主流程**:
  1. 用户调用 `POST /api/user/organization/update` 提交组织更新请求 [API/Controllers/UserManagement/OrganizationController.cs:56]
  2. `OrganizationController.Update` 调用 `OrganizationHandler` 验证当前用户是否为组织 OWNER
  3. 验证通过后更新组织名称、描述等字段
- **验收标准**:
  - [ ] AC1: 请求成功时返回 errorCode=0 且响应包含更新后的组织信息
  - [ ] AC2: 非 OWNER 成员调用返回Privilege错误（errorCode=403）
- **业务规则**:
  - BR-004: 仅组织 OWNER 可更新组织信息

#### 3.1.3. FR-004 删除组织 [优先级: Must]

- **用户故事**: 作为组织 OWNER，我希望删除不再使用的组织，以便清理系统资源。
- **主流程**:
  1. 用户调用 `POST /api/user/organization/delete` 提交组织删除请求 [API/Controllers/UserManagement/OrganizationController.cs:71]
  2. `OrganizationController.Delete` 调用 `OrganizationHandler` 验证当前用户是否为组织 OWNER
  3. 验证通过后删除组织及其关联的项目、成员关系
- **验收标准**:
  - [ ] AC1: 请求成功时返回 errorCode=0
  - [ ] AC2: 非 OWNER 成员调用返回Privilege错误（errorCode=403）
- **业务规则**:
  - BR-005: 仅组织 OWNER 可删除组织
  - BR-006: 删除组织为级联操作，同时删除组织下所有项目和成员关系

#### 3.1.4. FR-005 创建项目 [优先级: Must]

- **用户故事**: 作为组织管理员，我希望在组织下创建项目，以便对 Agent 进行分组管理。
- **主流程**:
  1. 用户调用 `POST /api/user/project` 提交项目创建请求 [API/Controllers/UserManagement/ProjectController.cs:31]
  2. `ProjectController.Create` 调用 `ProjectHandler` 验证当前用户在组织中的Privilege
  3. 验证通过后创建项目记录并建立创建者的 ADMIN 成员关系
- **验收标准**:
  - [ ] AC1: 请求成功时返回 errorCode=0 且响应包含项目 ID 字段
  - [ ] AC2: 创建者自动成为项目的 ADMIN 角色成员
  - [ ] AC3: 非组织成员调用返回Privilege错误（errorCode=403）
- **业务规则**:
  - BR-007: 项目名称在组织内必须唯一
  - BR-008: 项目创建者自动获得 ADMIN Role

#### 3.1.5. FR-006 查询项目列表 [优先级: Must]

- **用户故事**: 作为组织成员，我希望查询组织下的项目列表，以便查看项目状态。
- **主流程**:
  1. 用户调用 `GET /api/user/project` 获取项目列表 [API/Controllers/UserManagement/ProjectController.cs:46]
  2. `ProjectController.Get` 调用 `ProjectHandler` 查询当前用户可访问的项目
  3. 返回项目列表及当前用户在项目中的角色
- **验收标准**:
  - [ ] AC1: 请求成功时返回 errorCode=0 且响应包含项目列表数据
  - [ ] AC2: 仅返回当前用户所属组织的项目
- **业务规则**:
  - BR-009: 项目列表按创建时间倒序排列

#### 3.1.6. FR-007 更新项目信息 [优先级: Must]

- **用户故事**: 作为项目管理员，我希望更新项目名称和描述，以便维护项目信息的准确性。
- **主流程**:
  1. 用户调用 `POST /api/user/project/update` 提交项目更新请求 [API/Controllers/UserManagement/ProjectController.cs:60]
  2. `ProjectController.Update` 调用 `ProjectHandler` 验证当前用户是否为项目 ADMIN
  3. 验证通过后更新项目名称、描述等字段
- **验收标准**:
  - [ ] AC1: 请求成功时返回 errorCode=0 且响应包含更新后的项目信息
  - [ ] AC2: 非 ADMIN 成员调用返回Privilege错误（errorCode=403）
- **业务规则**:
  - BR-010: 仅项目 ADMIN 可更新项目信息

#### 3.1.7. FR-008 删除项目 [优先级: Must]

- **用户故事**: 作为项目管理员，我希望删除不再使用的项目，以便清理系统资源。
- **主流程**:
  1. 用户调用 `POST /api/user/project/delete` 提交项目删除请求 [API/Controllers/UserManagement/ProjectController.cs:75]
  2. `ProjectController.Delete` 调用 `ProjectHandler` 验证当前用户是否为项目 ADMIN
  3. 验证通过后删除项目及其关联的 Agent Config
- **验收标准**:
  - [ ] AC1: 请求成功时返回 errorCode=0
  - [ ] AC2: 非 ADMIN 成员调用返回Privilege错误（errorCode=403）
- **业务规则**:
  - BR-011: 仅项目 ADMIN 可删除项目

#### 3.1.8. FR-009 获取用户Config [优先级: Should]

- **用户故事**: 作为普通用户，我希望获取个人Config信息，以便查看和恢复我的偏好设置。
- **主流程**:
  1. 用户调用 `GET /api/user/config` 获取个人Config [API/Controllers/UserManagement/UserConfigController.cs:31]
  2. `UserConfigController.Get` 调用 `UserConfigHandler` 查询当前用户的Config
  3. 返回用户Config JSON 数据
- **验收标准**:
  - [ ] AC1: 请求成功时返回 errorCode=0 且响应包含用户Config数据
  - [ ] AC2: 未登录用户调用返回 401 未授权
- **业务规则**:
  - BR-012: 用户Config以 JSON 格式存储

#### 3.1.9. FR-010 创建用户Config [优先级: Should]

- **用户故事**: 作为普通用户，我希望创建个人Config，以便定制系统行为。
- **主流程**:
  1. 用户调用 `POST /api/user/config` 提交Config创建请求 [API/Controllers/UserManagement/UserConfigController.cs:44]
  2. `UserConfigController.Post` 调用 `UserConfigHandler` 创建当前用户的Config
  3. 返回创建后的Config数据
- **验收标准**:
  - [ ] AC1: 请求成功时返回 errorCode=0 且响应包含创建后的Config数据
  - [ ] AC2: 重复创建时返回Config已存在错误（errorCode=150003）
- **业务规则**:
  - BR-013: 每个用户仅能拥有一份Config

#### 3.1.10. FR-011 更新用户Config [优先级: Should]

- **用户故事**: 作为普通用户，我希望更新个人Config，以便调整系统行为。
- **主流程**:
  1. 用户调用 `POST /api/user/config/update` 提交Config更新请求 [API/Controllers/UserManagement/UserConfigController.cs:57]
  2. `UserConfigController.Update` 调用 `UserConfigHandler` 更新当前用户的Config
  3. 返回更新后的Config数据
- **验收标准**:
  - [ ] AC1: 请求成功时返回 errorCode=0 且响应包含更新后的Config数据
- **业务规则**:
  - BR-014: Config更新采用全量覆盖策略

#### 3.1.11. FR-012 删除用户Config [优先级: Should]

- **用户故事**: 作为普通用户，我希望删除个人Config，以便重置系统行为为默认值。
- **主流程**:
  1. 用户调用 `POST /api/user/config/delete` 提交Config删除请求 [API/Controllers/UserManagement/UserConfigController.cs:71]
  2. `UserConfigController.Delete` 调用 `UserConfigHandler` 删除当前用户的Config
  3. 返回成功响应
- **验收标准**:
  - [ ] AC1: 请求成功时返回 errorCode=0
- **业务规则**:
  - BR-015: 删除Config后系统使用默认Config

#### 3.1.12. FR-013 获取图形Captcha [优先级: Must]

- **用户故事**: 作为匿名用户，我希望获取图形Captcha，以便完成注册或登录操作。
- **主流程**:
  1. 用户调用 `GET /api/captcha` 获取图形Captcha [API/Controllers/UserManagement/CaptchaController.cs:29]
  2. `CaptchaController.Get` 调用 `CaptchaHandler` 生成图形Captcha
  3. 返回Captcha图片 Base64 和Captcha ID
- **验收标准**:
  - [ ] AC1: 请求成功时返回 errorCode=0 且响应包含Captcha图片和Captcha ID
  - [ ] AC2: Captcha长度为 5 位字符（`CaptchaSetting.CodeLength = 5`）
  - [ ] AC3: Captcha有效期 300 秒（`CaptchaSetting.ExpireSeconds = 300`）
- **业务规则**:
  - BR-016: Captcha 60 秒内不可重复发送（`CaptchaSetting.ResendInterval = 60`）

#### 3.1.13. FR-014 获取短信Captcha [优先级: Must]

- **用户故事**: 作为匿名用户，我希望获取短信Captcha，以便完成手机号注册或登录操作。
- **主流程**:
  1. 用户调用 `GET /api/captcha/sms` 获取短信Captcha [API/Controllers/UserManagement/CaptchaController.cs:43]
  2. `CaptchaController.GetSms` 调用 `CaptchaHandler` 生成短信Captcha并发送
  3. 返回发送结果
- **验收标准**:
  - [ ] AC1: 请求成功时返回 errorCode=0 且Captcha已发送至目标手机号
  - [ ] AC2: Captcha长度为 6 位数字（`CaptchaSetting.SmsCodeLength = 6`）
  - [ ] AC3: Captcha有效期 300 秒（`CaptchaSetting.SmsExpireSeconds = 300`）
- **业务规则**:
  - BR-017: 同一手机号 60 秒内不可重复发送（`CaptchaSetting.SmsResendInterval = 60`）

### 3.2. FR-Payment管理

Payment管理域涵盖订单创建、查询、产品转换计算以及微信Payment/Payment宝PaymentPayment回调处理，共 6 个端点，由 OrderController 和 NotifyController 提供。该域是系统的 P0 优先级功能，依赖 PaymentService 与外部Payment平台交互。

#### 3.2.1. FR-015 获取订单列表 [优先级: Must]

- **用户故事**: 作为组织 OWNER，我希望查询组织下的订单列表，以便查看组织的消费记录。
- **主流程**:
  1. 用户调用 `GET /api/payment/order` 获取订单列表 [API/Controllers/PaymentManagement/OrderController.cs:34]
  2. `OrderController.Get` 调用 `OrderHandler.GetOrders` 查询订单 [API/Handlers/PaymentManagement/OrderHandler.cs:12-17]
  3. `OrderHandler` 验证当前用户是否为组织 OWNER，验证通过后分页查询订单
- **验收标准**:
  - [ ] AC1: 请求成功时返回 errorCode=0 且响应包含订单列表和分页信息
  - [ ] AC2: 非组织成员调用返回Privilege错误（errorCode=403）
  - [ ] AC3: 非 OWNER 角色调用返回Privilege错误（errorCode=403）
- **业务规则**:
  - BR-018: 仅组织 OWNER 可查看组织订单列表

#### 3.2.2. FR-016 创建订单 [优先级: Must]

- **用户故事**: 作为组织 OWNER，我希望创建订单，以便购买或升级产品服务。
- **主流程**:
  1. 用户调用 `POST /api/payment/order` 提交订单创建请求 [API/Controllers/PaymentManagement/OrderController.cs:48]
  2. `OrderController.Create` 调用 `OrderHandler.PlaceOrder` 创建订单 [API/Handlers/PaymentManagement/OrderHandler.cs:13]
  3. `OrderHandler` 验证组织 OWNER 身份，创建订单并调用 `PaymentService` 获取Payment参数
- **验收标准**:
  - [ ] AC1: 请求成功时返回 errorCode=0 且响应包含订单 ID 和Payment参数
  - [ ] AC2: 非组织成员调用返回Privilege错误（errorCode=403）
- **业务规则**:
  - BR-019: 订单创建后状态为待Payment
  - BR-020: 订单金额根据产品类型（Monthly/Permanent）和费率计算

#### 3.2.3. FR-017 产品转换计算 [优先级: Must]

- **用户故事**: 作为组织 OWNER，我希望计算产品转换价格，以便评估从月付升级到永久付费的成本。
- **主流程**:
  1. 用户调用 `GET /api/payment/order/conversion` 进行转换计算 [API/Controllers/PaymentManagement/OrderController.cs:79]
  2. `OrderController.GetConversion` 调用 `OrderHandler.CalculateConversion` 计算转换价格 [API/Handlers/PaymentManagement/OrderHandler.cs:18]
  3. monthlyratepermanentrate计算转换金额
- **验收标准**:
  - [ ] AC1: 请求成功时返回 errorCode=0 且响应包含转换后的价格信息
  - [ ] AC2: 产品类型支持 Monthly（type=1）和 Permanent（type=2）
- **业务规则**:
  - BR-021: 转换价格 = 永久产品价格 - 已Payment月付产品剩余价值

#### 3.2.4. FR-018 微信Payment回调 [优先级: Must]

- **用户故事**: 作为系统，我希望接收微信Payment平台的异步通知，以便更新订单Payment状态。
- **主流程**:
  1. 微信Payment平台调用 `POST /api/payment/notify/wechatnotify` 发送Payment结果通知 [API/Controllers/PaymentManagement/NotifyController.cs:29]
  2. `NotifyController.WechatNotify` 调用 `NotifyHandler` 验证签名并处理通知 [API/Handlers/PaymentManagement/NotifyHandler.cs:12-14]
  3. 验证通过后更新订单状态为已Payment，并通过 MediatR 发布 `PaymentTransactionNotification` 触发异步保存
- **验收标准**:
  - [ ] AC1: 签名验证通过时返回成功响应并更新订单状态
  - [ ] AC2: 签名验证失败时返回错误响应且不更新订单状态
- **业务规则**:
  - BR-022: 回调通知需验证微信Payment平台签名
  - BR-023: 订单Payment成功后自动开通对应产品Privilege

#### 3.2.5. FR-019 Payment宝Payment回调 [优先级: Must]

- **用户故事**: 作为系统，我希望接收Payment宝Payment平台的异步通知，以便更新订单Payment状态。
- **主流程**:
  1. Payment宝Payment平台调用 `POST /api/payment/notify/alipaynotify` 发送Payment结果通知 [API/Controllers/PaymentManagement/NotifyController.cs:57]
  2. `NotifyController.AlipayNotify` 调用 `NotifyHandler` 验证签名并处理通知 [API/Handlers/PaymentManagement/NotifyHandler.cs:13-14]
  3. 验证通过后更新订单状态为已Payment，并通过 MediatR 发布 `PaymentTransactionNotification` 触发异步保存
- **验收标准**:
  - [ ] AC1: 签名验证通过时返回成功响应并更新订单状态
  - [ ] AC2: 签名验证失败时返回错误响应且不更新订单状态
- **业务规则**:
  - BR-024: 回调通知需验证Payment宝平台签名
  - BR-025: 订单Payment成功后自动开通对应产品Privilege

### 3.3. FR-数据管理

数据管理域涵盖 Trace、Observation、Score 和 Model 定义查询，由 MetricsController 和 ModelController 提供。该域是系统的 P0 优先级功能，依赖 ClickHouse 数据库进行指标数据存储与查询。

#### 3.3.1. FR-020 查询 Trace 列表 [优先级: Must]

- **用户故事**: 作为组织管理员，我希望查询 Trace 列表，以便监控 Agent 的运行状态。
- **主流程**:
  1. 用户调用 `GET /api/metrics/traces` 查询 Trace 列表 [API/Controllers/DataManagement/MetricsController.cs]
  2. `MetricsController` 调用 `MetricsHandler` 查询 Trace 数据 [API/Handlers/DataManagement/MetricsHandler.cs:14-16]
  3. `MetricsHandler` 通过 `ClickHouseClient` 执行 Trace 查询并支持分页与过滤
- **验收标准**:
  - [ ] AC1: 请求成功时返回 errorCode=0 且响应包含 Trace 列表和分页信息
  - [ ] AC2: 支持按时间范围、Project ID 等条件过滤
- **业务规则**:
  - BR-026: Trace 查询依赖 ClickHouse 数据库（`ClickHouseDb.TraceTable`）

#### 3.3.2. FR-021 查询 Observation 列表 [优先级: Must]

- **用户故事**: 作为组织管理员，我希望查询 Observation 列表，以便分析 Agent 的详细运行日志。
- **主流程**:
  1. 用户调用 `GET /api/metrics/observations` 查询 Observation 列表 [API/Controllers/DataManagement/MetricsController.cs]
  2. `MetricsController` 调用 `MetricsHandler` 查询 Observation 数据 [API/Handlers/DataManagement/MetricsHandler.cs:12]
  3. `MetricsHandler` 通过 `ClickHouseClient` 执行 Observation 查询
- **验收标准**:
  - [ ] AC1: 请求成功时返回 errorCode=0 且响应包含 Observation 列表和分页信息
  - [ ] AC2: 支持按 Trace ID 关联查询
- **业务规则**:
  - BR-027: Observation 查询支持按 Trace ID 过滤

#### 3.3.3. FR-022 查询 Score 列表 [优先级: Must]

- **用户故事**: 作为组织管理员，我希望查询 Score 列表，以便评估 Agent 的输出质量。
- **主流程**:
  1. 用户调用 `GET /api/metrics/scores` 查询 Score 列表 [API/Controllers/DataManagement/MetricsController.cs]
  2. `MetricsController` 调用 `MetricsHandler` 查询 Score 数据 [API/Handlers/DataManagement/MetricsHandler.cs:13]
  3. `MetricsHandler` 通过 `ClickHouseClient` 执行 Score 查询
- **验收标准**:
  - [ ] AC1: 请求成功时返回 errorCode=0 且响应包含 Score 列表和分页信息
- **业务规则**:
  - BR-028: Score 查询支持按 Trace ID 或 Observation ID 过滤

#### 3.3.4. FR-023 查询 Model 定义列表 [优先级: Should]

- **用户故事**: 作为组织管理员，我希望查询 Model 定义列表，以便了解系统支持的模型类型。
- **主流程**:
  1. 用户调用 `GET /api/model` 查询 Model 定义列表 [API/Controllers/DataManagement/ModelController.cs]
  2. `ModelController` 调用 `ModelHandler` 查询 Model 定义 [API/Handlers/DataManagement/ModelHandler.cs:12]
  3. 返回模型定义列表
- **验收标准**:
  - [ ] AC1: 请求成功时返回 errorCode=0 且响应包含 Model 定义列表
- **业务规则**:
  - BR-029: Model 定义数据存储在 DataDb 数据库

### 3.4. FR-Alert管理

Alert管理域涵盖AlertConfig CRUD 和Alert记录读写，由 AlertController 提供，AlertService 负责规则评估。该域是系统的 P1 优先级功能。

#### 3.4.1. FR-024 创建Alert规则 [优先级: Must]

- **用户故事**: 作为组织管理员，我希望创建Alert规则，以便在指标异常时及时收到通知。
- **主流程**:
  1. 用户调用 `POST /api/alert` 提交Alert规则创建请求 [API/Controllers/AlertManagement/AlertController.cs:61]
  2. `AlertController` 调用 `AlertHandler` 创建Alert规则 [API/Handlers/AlertManagement/AlertHandler.cs:12-15]
  3. `AlertHandler` 验证规则Config并保存
- **验收标准**:
  - [ ] AC1: 请求成功时返回 errorCode=0 且响应包含Alert规则 ID
  - [ ] AC2: Alert频率无效时返回参数错误（errorCode=160005）
- **业务规则**:
  - BR-030: Alert规则包含指标类型、比较条件、阈值和通知方式

#### 3.4.2. FR-025 查询Alert规则列表 [优先级: Must]

- **用户故事**: 作为组织管理员，我希望查询Alert规则列表，以便查看已Config的Alert策略。
- **主流程**:
  1. 用户调用 `GET /api/alert` 查询Alert规则列表 [API/Controllers/AlertManagement/AlertController.cs]
  2. `AlertController` 调用 `AlertHandler` 查询Alert规则 [API/Handlers/AlertManagement/AlertHandler.cs]
  3. 返回Alert规则列表
- **验收标准**:
  - [ ] AC1: 请求成功时返回 errorCode=0 且响应包含Alert规则列表
- **业务规则**:
  - BR-031: Alert规则列表按创建时间倒序排列

#### 3.4.3. FR-026 更新Alert规则 [优先级: Must]

- **用户故事**: 作为组织管理员，我希望更新Alert规则，以便调整Alert策略。
- **主流程**:
  1. 用户调用 `POST /api/alert/update` 提交Alert规则更新请求 [API/Controllers/AlertManagement/AlertController.cs]
  2. `AlertController` 调用 `AlertHandler` 更新Alert规则 [API/Handlers/AlertManagement/AlertHandler.cs]
  3. 验证规则Config并保存更新
- **验收标准**:
  - [ ] AC1: 请求成功时返回 errorCode=0 且响应包含更新后的Alert规则
- **业务规则**:
  - BR-032: 仅规则创建者或组织管理员可更新Alert规则

#### 3.4.4. FR-027 删除Alert规则 [优先级: Must]

- **用户故事**: 作为组织管理员，我希望删除不再需要的Alert规则，以便减少无效通知。
- **主流程**:
  1. 用户调用 `POST /api/alert/delete` 提交Alert规则删除请求 [API/Controllers/AlertManagement/AlertController.cs]
  2. `AlertController` 调用 `AlertHandler` 删除Alert规则 [API/Handlers/AlertManagement/AlertHandler.cs]
  3. 返回成功响应
- **验收标准**:
  - [ ] AC1: 请求成功时返回 errorCode=0
- **业务规则**:
  - BR-033: 仅规则创建者或组织管理员可删除Alert规则

#### 3.4.5. FR-028 查询Alert记录 [优先级: Must]

- **用户故事**: 作为组织管理员，我希望查询Alert记录，以便查看历史Alert事件。
- **主流程**:
  1. 用户调用 `GET /api/alert/record` 查询Alert记录 [API/Controllers/AlertManagement/AlertController.cs]
  2. `AlertHandler` 查询Alert记录并支持分页 [API/Handlers/AlertManagement/AlertHandler.cs:16-17]
  3. 返回Alert记录列表
- **验收标准**:
  - [ ] AC1: 请求成功时返回 errorCode=0 且响应包含Alert记录列表和分页信息
- **业务规则**:
  - BR-034: Alert记录按触发时间倒序排列

#### 3.4.6. FR-029 标记Alert已读 [优先级: Should]

- **用户故事**: 作为组织管理员，我希望标记Alert记录为已读，以便区分已处理和未处理的Alert。
- **主流程**:
  1. 用户调用 `POST /api/alert/record/read` 标记Alert已读 [API/Controllers/AlertManagement/AlertController.cs]
  2. `AlertHandler` 更新Alert记录的已读状态 [API/Handlers/AlertManagement/AlertHandler.cs]
  3. 返回成功响应
- **验收标准**:
  - [ ] AC1: 请求成功时返回 errorCode=0
- **业务规则**:
  - BR-035: 已读标记仅对当前用户可见

### 3.5. FR-Agent 管理

Agent 管理域涵盖 Agent Config管理、报告模板管理和Session管理，由 AgentConfigController、AgentReportController、AgentSessionController 提供。该域是系统的 P1 优先级功能。

#### 3.5.1. FR-030 获取 Agent Config [优先级: Must]

- **用户故事**: 作为普通用户，我希望获取我的 Agent Config，以便查看数据源连接信息。
- **主流程**:
  1. 用户调用 `GET /api/agent/config` 获取 Agent Config [API/Controllers/AgentManagement/AgentConfigController.cs:29]
  2. `AgentConfigController.Get` 调用 `AgentConfigHandler.GetConfig` 查询当前用户的Config [API/Handlers/AgentManagement/AgentConfigHandler.cs:12-14]
  3. 返回 Agent Config信息
- **验收标准**:
  - [ ] AC1: 请求成功时返回 errorCode=0 且响应包含Config ID、数据源信息和默认模板 ID
  - [ ] AC2: 未Config时返回Config不存在错误（errorCode=150004）
- **业务规则**:
  - BR-036: 每个用户仅能拥有一份 Agent Config

#### 3.5.2. FR-031 创建或更新 Agent Config [优先级: Must]

- **用户故事**: 作为普通用户，我希望创建或更新 Agent Config，以便Config数据源连接。
- **主流程**:
  1. 用户调用 `POST /api/agent/config` 提交Config创建或更新请求 [API/Controllers/AgentManagement/AgentConfigController.cs:44]
  2. `AgentConfigController.Post` 调用 `AgentConfigHandler.CreateOrUpdateConfig`
  3. Config存在则更新，不存在则创建；datasource 和 defaulttemplateid 为空时忽略
- **验收标准**:
  - [ ] AC1: 请求成功时返回 errorCode=0 且响应包含创建或更新后的Config信息
- **业务规则**:
  - BR-037: Config采用 upsert 语义，存在则更新，不存在则创建

#### 3.5.3. FR-032 删除 Agent Config [优先级: Should]

- **用户故事**: 作为普通用户，我希望删除 Agent Config，以便重置数据源连接。
- **主流程**:
  1. 用户调用 `POST /api/agent/config/delete` 提交Config删除请求 [API/Controllers/AgentManagement/AgentConfigController.cs:37]
  2. `AgentConfigController.Delete` 调用 `AgentConfigHandler.DeleteConfig`
  3. 返回成功响应
- **验收标准**:
  - [ ] AC1: 请求成功时返回 errorCode=0
- **业务规则**:
  - BR-038: 删除Config后系统使用默认Config

#### 3.5.4. FR-033 获取 Agent 报告模板 [优先级: Should]

- **用户故事**: 作为普通用户，我希望获取 Agent 报告模板列表，以便选择模板生成报告。
- **主流程**:
  1. 用户调用 `GET /api/agent/report` 获取报告模板列表 [API/Controllers/AgentManagement/AgentReportController.cs]
  2. `AgentReportController` 调用 `AgentReportHandler` 查询模板 [API/Handlers/AgentManagement/AgentReportHandler.cs:12-14]
  3. 返回报告模板列表
- **验收标准**:
  - [ ] AC1: 请求成功时返回 errorCode=0 且响应包含报告模板列表
- **业务规则**:
  - BR-039: 报告模板按创建时间倒序排列

#### 3.5.5. FR-034 创建 Agent 报告模板 [优先级: Should]

- **用户故事**: 作为普通用户，我希望创建自定义报告模板，以便按需生成报告。
- **主流程**:
  1. 用户调用 `POST /api/agent/report` 提交模板创建请求 [API/Controllers/AgentManagement/AgentReportController.cs]
  2. `AgentReportController` 调用 `AgentReportHandler` 创建模板 [API/Handlers/AgentManagement/AgentReportHandler.cs]
  3. 返回创建后的模板信息
- **验收标准**:
  - [ ] AC1: 请求成功时返回 errorCode=0 且响应包含模板 ID
- **业务规则**:
  - BR-040: 模板内容支持 Markdown 格式

#### 3.5.6. FR-035 更新 Agent 报告模板 [优先级: Should]

- **用户故事**: 作为普通用户，我希望更新报告模板，以便调整报告格式。
- **主流程**:
  1. 用户调用 `POST /api/agent/report/update` 提交模板更新请求 [API/Controllers/AgentManagement/AgentReportController.cs]
  2. `AgentReportController` 调用 `AgentReportHandler` 更新模板 [API/Handlers/AgentManagement/AgentReportHandler.cs]
  3. 返回更新后的模板信息
- **验收标准**:
  - [ ] AC1: 请求成功时返回 errorCode=0 且响应包含更新后的模板信息
- **业务规则**:
  - BR-041: 仅模板创建者可更新模板

#### 3.5.7. FR-036 删除 Agent 报告模板 [优先级: Should]

- **用户故事**: 作为普通用户，我希望删除不再使用的报告模板，以便清理模板列表。
- **主流程**:
  1. 用户调用 `POST /api/agent/report/delete` 提交模板删除请求 [API/Controllers/AgentManagement/AgentReportController.cs]
  2. `AgentReportController` 调用 `AgentReportHandler` 删除模板 [API/Handlers/AgentManagement/AgentReportHandler.cs]
  3. 返回成功响应
- **验收标准**:
  - [ ] AC1: 请求成功时返回 errorCode=0
- **业务规则**:
  - BR-042: 仅模板创建者可删除模板

#### 3.5.8. FR-037 获取 Agent Session列表 [优先级: Could]

- **用户故事**: 作为普通用户，我希望获取 Agent Session列表，以便查看历史对话记录。
- **主流程**:
  1. 用户调用 `GET /api/agent/session` 获取Session列表 [API/Controllers/AgentManagement/AgentSessionController.cs]
  2. `AgentSessionController` 调用 `AgentSessionHandler` 查询Session [API/Handlers/AgentManagement/AgentSessionHandler.cs:12-14]
  3. 返回Session列表
- **验收标准**:
  - [ ] AC1: 请求成功时返回 errorCode=0 且响应包含Session列表
  - [ ] AC2: Session不存在时返回Session不存在错误（errorCode=150021）
- **业务规则**:
  - BR-043: Session列表按最近活跃时间倒序排列

#### 3.5.9. FR-038 删除 Agent Session [优先级: Could]

- **用户故事**: 作为普通用户，我希望删除不再需要的 Agent Session，以便清理对话记录。
- **主流程**:
  1. 用户调用 `DELETE /api/agent/session/{sessionId}` 删除Session [API/Controllers/AgentManagement/AgentSessionController.cs]
  2. `AgentSessionController` 调用 `AgentSessionHandler` 删除Session [API/Handlers/AgentManagement/AgentSessionHandler.cs]
  3. 返回成功响应
- **验收标准**:
  - [ ] AC1: 请求成功时返回 errorCode=0
  - [ ] AC2: Session不存在时返回Session不存在错误（errorCode=150021）
- **业务规则**:
  - BR-044: 仅Session创建者可删除Session

### 3.6. FR-工具管理

工具管理域涵盖Bulletin管理、健康检查和微信消息处理，由 BulletinController、HealthController、WeChatController 提供。该域是系统的 P2 优先级功能。

#### 3.6.1. FR-039 创建Bulletin [优先级: Should]

- **用户故事**: 作为组织管理员，我希望创建Bulletin，以便向组织成员发布重要通知。
- **主流程**:
  1. 用户调用 `POST /api/bulletin` 提交Bulletin创建请求 [API/Controllers/ToolsManagement/BulletinController.cs]
  2. `BulletinController` 调用 `BulletinHandler` 创建Bulletin [API/Handlers/ToolsManagement/BulletinHandler.cs:12-18]
  3. 返回创建后的Bulletin信息
- **验收标准**:
  - [ ] AC1: 请求成功时返回 errorCode=0 且响应包含Bulletin ID
- **业务规则**:
  - BR-045: Bulletin创建后状态为待审批

#### 3.6.2. FR-040 查询Bulletin列表 [优先级: Should]

- **用户故事**: 作为组织成员，我希望查询Bulletin列表，以便查看组织发布的通知。
- **主流程**:
  1. 用户调用 `GET /api/bulletin` 查询Bulletin列表 [API/Controllers/ToolsManagement/BulletinController.cs]
  2. `BulletinController` 调用 `BulletinHandler` 查询Bulletin [API/Handlers/ToolsManagement/BulletinHandler.cs]
  3. 返回Bulletin列表
- **验收标准**:
  - [ ] AC1: 请求成功时返回 errorCode=0 且响应包含Bulletin列表
- **业务规则**:
  - BR-046: Bulletin列表按发布时间倒序排列

---

## 4. 非功能需求

AgentInsightService（保持原文） 是一个面向组织的 AI Agent 可Observation性与Payment管理平台，系统提供 Trace 数据采集与分析、Alert（Alert）、用户与组织管理、Payment集成（微信Payment/Payment宝Payment）以及 Agent Config管理能力。NFR，涵盖性能、可用性、安全、可扩展性、可维护性、兼容性与本地化七个维度。所有 NFR 均采用 `NFR-{CATEGORY}-NNN` 格式编号（其中 `{CATEGORY}` 为维度缩写，`NNN` 为三位数字序号），并明确验证方式，确保需求可量化、可测试、可追溯。

### 4.1. 性能

性能需求聚焦于 API 响应时间、Trace 数据查询效率与Payment链路延迟。系统核心链路包括Payment下单、Payment回调、Trace 查询与Alert评估，各链路均需满足明确的延迟指标。

| 编号 | 需求描述 | 验证方式 |
|------|---------|---------|
| NFR-P-001 | Payment回调接口（`POST /api/payment/notify/wechatnotify` 与 `/alipaynotify`）端到端处理时间 ≤ 2s，包含签名验证、订单状态更新与异步通知发布 | 使用 k6 或 JMeter 压测，模拟 100 并发回调请求，P95 延迟 ≤ 2s |
| NFR-P-002 | Trace 列表查询接口（`GET /api/data/metrics/traces`）在 100 万级 Trace 数据量下，单页查询（默认 pagesize=50）响应时间 ≤ 1s | 使用 ClickHouse 测试数据集，通过 k6 执行 50 并发查询，P95 延迟 ≤ 1s |
| NFR-P-003 | Observation 与 Score 分页查询接口响应时间 ≤ 800ms，默认分页大小 10 条 | 针对 `MetricsHandler.GetObservations` 与 `MetricsHandler.GetScores` 执行基准测试 [API/Handlers/DataManagement/MetricsHandler.cs:12-13] |
| NFR-P-004 | 下单接口（`POST /api/payment/order`）在正常负载下响应时间 ≤ 1.5s，包含产品校验、订单创建与Payment参数生成 | 使用 k6 压测，50 并发用户，P95 延迟 ≤ 1.5s |
| NFR-P-005 | Alert规则评估任务单次执行时间 ≤ 5s，评估频率与 `AlertService` 定时任务周期一致 | 通过日志监控 `AlertService` 单次评估耗时 [API/Common/Services/AlertService.cs:12-16] |
| NFR-P-006 | 健康检查接口 `GET /api/tools/health` 响应时间 ≤ 200ms，用于负载均衡与容器编排探活 | 使用 curl 或 k6 单请求验证 [API/Controllers/ToolsManagement/HealthController.cs:20] |

### 4.2. 可用性

可用性需求确保系统在外部依赖（Payment平台、Redis、ClickHouse）异常时仍能提供核心服务，并为运维提供健康探测与快速恢复能力。

| 编号 | 需求描述 | 验证方式 |
|------|---------|---------|
| NFR-A-001 | 所有 API 端点月度可用性 ≥ 99.5%，即单月不可用时间不超过 3.6 小时 | 基于基础设施监控（如 Prometheus + Grafana）统计端点 uptime |
| NFR-A-002 | 系统必须提供健康检查端点 `GET /api/tools/health`，供负载均衡器与容器编排平台（如 Kubernetes）进行存活与就绪探测 | 部署后通过 HTTP 请求验证返回 200 状态码 [API/Controllers/ToolsManagement/HealthController.cs:20] |
| NFR-A-003 | Payment回调接口必须支持幂等处理，同一Payment通知重复投递时不会产生重复订单状态更新 | 通过集成测试重复发送相同回调请求，验证订单状态仅更新一次 |
| NFR-A-004 | 当 Redis 不可用时，系统降级为同步处理 Trace 摄入，不丢失数据；Redis 恢复后自动切回异步队列模式 | 故障注入测试：停止 Redis Service，验证 Trace 数据仍可写入 ClickHouse |
| NFR-A-005 | 当 ClickHouse 不可用时，Trace 查询接口返回 503 错误并附带友好提示，不影响用户认证与Payment等核心功能 | 故障注入测试：停止 ClickHouse Service，验证非 Trace 接口正常响应 |
| NFR-A-006 | 系统启动时间 ≤ 60s，包含数据库连接池初始化、Redis 连接建立与Config加载 | 容器启动时记录开始与结束时间戳，计算启动耗时；连续验证 3 次取最大值 |

### 4.3. 安全

安全需求覆盖认证授权、数据加密、Payment签名验证与审计日志四个层面。系统采用 JWT 与 API Key 双通道认证，Payment回调必须验证平台签名，所有敏感操作记录审计日志。

| 编号 | 需求描述 | 验证方式 |
|------|---------|---------|
| NFR-S-001 | JWT 签名密钥使用 HS256 算法，密钥来源于环境变量 `${JWT_SECRET_KEY}`，且必须定期轮换（建议 90 天），密钥长度 ≥ 256 bit | 代码审查确认 `JwtConfig.Algorithm = HS256` 与 `JwtConfig.SecretKey` Config；运维流程确认轮换策略 |
| NFR-S-002 | Payment回调必须验证签名：微信Payment使用 V3 签名验证，Payment宝使用 RSA2 签名验证，验证失败时返回错误码 `PaymentSignatureInvalid`（620002）或拒绝请求 | 通过 `PaymentService.ExamineAlipaySignature` 与微信签名验证逻辑执行单元测试 [API/Common/Services/PaymentService.cs:14-19] |
| NFR-S-003 | 用户密码必须使用加盐哈希存储（`PasswordHasher` 990003），禁止明文存储；传输过程必须使用 HTTPS | 代码审查 + 数据库存储内容检查 |
| NFR-S-004 | API Key 认证使用 Basic Auth（PublicKey/SecretKey），SecretKey 加密存储，验证失败返回 `ApiKeyInvalid`（100038） | 通过 `AgentInsightTransformProvider` 执行认证测试 [API/System/Handlers/AgentInsightTransformProvider.cs:12-15] |
| NFR-S-005 | 所有写操作（创建、更新、删除）必须通过 `ApiHandlerBase.LogAudit` 记录审计日志，包含操作人、操作时间、操作内容 | 代码审查确认 `LogAudit` 调用覆盖所有 Handler 写操作 [API/Handlers/ApiHandlerBase.cs:34] |
| NFR-S-006 | 微信消息接口（`GET/POST /api/tools/wechat`）必须验证微信服务器签名，验证失败返回 `WeChatSignatureInvalid`（620002） | 通过 `WeChatService.ExamineSignature` 执行签名验证测试 [API/Common/Services/WeChatService.cs:12-14] |
| NFR-S-007 | 敏感Config（数据库连接串、Payment密钥、JWT 密钥）必须通过环境变量注入，禁止硬编码在代码仓库 | 代码扫描（如 SonarQube 或 Semgrep）确认无硬编码密钥 |
| NFR-S-008 | Captcha有效期 300 秒（`CaptchaSetting.ExpireSeconds = 300`），重发间隔 60 秒（`CaptchaSetting.ResendIntervalSeconds = 60`），防止暴力破解 | 集成测试验证Captcha过期与重发限制 [API/Handlers/UserManagement/CaptchaHandler.cs:12-14] |

### 4.4. 可扩展性

可扩展性需求确保系统能够通过水平扩展应对 Trace 数据量增长与用户规模扩大。系统采用多数据库分离架构与异步消息队列解耦关键路径。

| 编号 | 需求描述 | 验证方式 |
|------|---------|---------|
| NFR-SC-001 | Trace 摄入必须通过 `BullMqService` 异步队列处理，支持消费者实例水平扩展，队列积压时自动增加消费者 | 压测验证 `EnqueueTraceIngestionAsync` 吞吐量，监控 Redis 队列长度 [API/Common/Services/BullMqService.cs:12-14] |
| NFR-SC-002 | 多数据库连接池Config：UserDb/DataDb/TrackingDb 连接池 MinPoolSize=10、MaxPoolSize=200、ConnectionIdleTimeout=300；ClickHouseDb MaxPoolSize=10、MinPoolSize=50 | Config审查确认 `appsettings.json` 中连接串参数与规格一致 |
| NFR-SC-003 | 系统支持无状态水平扩展，API 实例可横向增加，Session状态存储在 Redis 或 JWT 中，不依赖本地内存 | 部署 2 个以上 API 实例，通过负载均衡验证Session一致性 |
| NFR-SC-004 | Trace 数据存储使用 ClickHouse 列式数据库，支持按时间分区与 TTL 策略，单表数据量 ≥ 10 亿条时查询性能不显著下降 | 使用 ClickHouse 基准测试工具（如 clickhouse-benchmark）验证大数据量查询性能 |
| NFR-SC-005 | 项目删除操作通过 `EnqueueProjectDeleteAsync` 异步执行，避免阻塞主线程，支持批量删除任务排队处理 | 集成测试验证删除任务入队与执行 [API/Common/Services/BullMqService.cs:12-14] |
| NFR-SC-006 | 数据库读写分离：UserDb 存储用户与组织数据，DataDb 存储业务数据，TrackingDb 存储埋点数据，ClickHouseDb 存储 Trace 数据，各库独立扩展 | 架构审查确认 `DbRouter` 数据库路由Config [API/Handlers/UserManagement/UserHandler.cs:6-8] |

### 4.5. 可维护性

可维护性需求关注代码可Observation性、Config管理、日志记录与测试覆盖率，确保系统可持续演进与快速排障。

| 编号 | 需求描述 | 验证方式 |
|------|---------|---------|
| NFR-M-001 | 所有 Handler 必须继承 `ApiHandlerBase`，统一处理用户上下文、Privilege验证与审计日志，禁止在 Controller 中直接编写业务逻辑 | 代码审查 + 架构测试（如 NetArchTest）验证继承关系 [API/Handlers/ApiHandlerBase.cs:10] |
| NFR-M-002 | 系统必须记录结构化日志，包含请求 ID、User ID、Org ID、耗时等关键字段，日志级别可通过Config动态调整 | 日志平台（如 Seq 或 ELK）检索验证日志字段完整性；修改 `appsettings.json` 中日志级别Config，验证动态生效 |
| NFR-M-003 | Config项必须集中在 `appsettings.json` 与 `Configurations/` 目录，敏感Config使用环境变量占位符（如 `${JWT_SECRET_KEY}`） | Config审查确认 `ConfigPath = ['Configurations', 'Resources']` |
| NFR-M-004 | 单元测试行覆盖率 ≥ 80%，关键业务模块（Payment、Alert、Privilege）覆盖率 ≥ 90% | 执行 `dotnet test /p:CollectCoverage=true` 验证覆盖率报告 |
| NFR-M-005 | API 文档必须通过 Swagger 自动生成，所有接口包含请求/响应示例与错误码说明 | 启动 Swagger UI 验证接口文档完整性 |
| NFR-M-006 | 系统必须支持优雅停机，正在处理的请求完成后才关闭，未完成的消息队列任务不丢失 | 部署测试：发送 SIGTERM 信号，验证在途请求完成且队列任务不丢失 |

### 4.6. 兼容性

兼容性需求确保系统在不同客户端、浏览器与外部平台集成场景下的稳定运行。

| 编号 | 需求描述 | 验证方式 |
|------|---------|---------|
| NFR-C-001 | API 必须兼容主流 HTTP 客户端（curl、Postman、浏览器 Fetch/Axios），响应格式统一为 `ApiResponse<T>` 包装结构 | 使用不同客户端发送请求，验证响应结构一致 |
| NFR-C-002 | Payment集成必须兼容微信Payment三种模式：JSAPI、Native、MiniProgram，以及Payment宝即时到账接口 | 集成测试分别调用 `GetWeChatJSAPIResponse`、`GetNativeResponse`、`WeChatMiniProgramPay` 与 `GetAlipayInstantTrade` [API/Common/Services/IPaymentService.cs:14-19] |
| NFR-C-003 | 微信消息接口必须兼容微信服务器回调的 XML 格式与签名验证机制 | 使用微信官方测试工具模拟回调请求 |
| NFR-C-004 | 系统必须兼容 PostgreSQL 与 ClickHouse 两种数据库方言，ORM 层使用 SqlSugar 抽象，禁止编写数据库特定 SQL | 代码审查确认数据访问层使用 SqlSugar 仓储模式 |
| NFR-C-005 | API 版本兼容：新增字段不得破坏旧客户端解析，响应中新增字段必须可空或带默认值 | 对比历史版本响应结构，验证向后兼容；使用旧版本客户端调用新版本接口，确认解析正常 |

### 4.7. 本地化

本地化需求确保系统支持多语言界面与多时区数据处理，满足不同地区用户的使用习惯。

| 编号 | 需求描述 | 验证方式 |
|------|---------|---------|
| NFR-L-001 | 系统必须支持四种语言：简体中文（zh-CN）、繁体中文（zh-TW）、繁体中文（zh-HK）、en，默认语言为 zh-CN | 验证 `LocalizationConfig.SupportedCultures = ['zh-CN', 'zh-TW', 'zh-HK', 'en']` Config生效 |
| NFR-L-002 | 本地化资源文件使用 JSON 格式，通过 `My.Extensions.Localization.Json` 加载，文件前缀为 `Text` | 检查 `Resources/` 目录下 JSON 资源文件完整性 [API/Common/Services/UserService.cs:8-9] |
| NFR-L-003 | 所有用户可见的提示信息（错误消息、验证消息、通知内容）必须通过本地化资源引用，禁止硬编码中文文案 | 代码扫描确认字符串字面量未直接出现在 View/Controller 中 |
| NFR-L-004 | 日期时间格式必须遵循当前文化区域设置，时间戳统一使用 UTC 存储，展示时转换为本地时区 | 集成测试验证不同文化区域下日期格式正确 |
| NFR-L-005 | 数字与货币格式必须遵循当前文化区域设置，Payment金额展示使用两位小数 | 集成测试验证 `zh-CN` 与 `en` 下金额格式差异 |
| NFR-L-006 | 新增语言时无需修改代码，仅需添加对应 JSON 资源文件并更新 `SupportedCultures` Config | 文档化本地化扩展流程，验证添加新语言包后系统自动识别 |

---

## 5. 接口需求

AgentInsightService（保持原文） 是一个面向组织的 AI Agent 可Observation性与Payment管理平台，提供 Trace 数据采集与分析、Alert（Alert）、用户与组织管理、Payment集成（微信Payment/Payment宝Payment）以及 Agent Config管理能力。本章定义系统的接口需求，涵盖内部 REST API 与外部依赖接口两大部分。内部接口由 18 个 Controller 暴露 76 个 HTTP 端点，供前端控制台与外部系统集成调用；外部接口包括微信Payment/Payment宝Payment平台回调，以及 Agents 子项目提供的 AI Agent 运行时服务。所有接口遵循统一的认证、数据格式与分页约定，确保系统各模块间及与第三方平台间的可靠通信。

### 5.1. 内部接口（REST API）

#### 5.1.1. API 概览

AgentInsightService（保持原文） 内部接口采用 RESTful 风格设计，所有端点以 `/api` 为 Base URL，数据格式统一为 JSON，字符集使用 UTF-8，时间格式遵循 ISO 8601 标准。接口分布在 18 个 Controller 中，覆盖用户管理、组织管理、项目与角色分配、Payment与订单、数据查询（Trace/Observation/Score/Model）、Alert管理、Agent Config与Session管理、Bulletin与微信消息处理等业务域。每个 Controller 通过 `[Route("api/...")]` 特性声明路由前缀，例如订单接口定义在 `[Route("api/payment")]` [API/Controllers/PaymentManagement/OrderController.cs:L13-L14]，Agent Session接口定义在 `[Route("api/agent/session")]` [API/Controllers/AgentManagement/AgentSessionController.cs:L13-L14]，模型管理接口定义在 `[Route("api/data/model")]` [API/Controllers/DataManagement/ModelController.cs:L13-L14]。

#### 5.1.2. 认证授权

内部接口支持两种认证方式，由 `AgentInsightTransformProvider` 统一处理 [API/System/Handlers/AgentInsightTransformProvider.cs:L12-L15]：

1. **JWT 认证**：适用于前端控制台用户。采用 HS256 签名算法，`Issuer` 为 `AgentInsightService（保持原文）`，`Audience` 为 `AgentInsightConsole`，签名密钥来自系统Config项 `JwtSettings:SecretKey`，Token 有效期 43200 分钟（30 天），时钟偏移容忍 5 秒。JWT 认证通过 `AutoSetUserFilter` 自动设置用户上下文 [API/System/Handlers/AutoSetUserFilter.cs:L8]。

2. **API Key Basic Auth**：适用于外部系统集成。使用 `PublicKey`/`SecretKey` 作为 Basic Auth 凭据（分别对应用户名与密码字段），由 `AgentInsightTransformProvider` 验证 API Key 有效性并执行速率限制 [API/System/Handlers/AgentInsightTransformLogic.cs:L9-L10]。

Privilege控制通过 `ApiHandlerBase` 提供的方法实现：`RequireOrgAdmin`、`RequireOrgOwner`、`RequireProjectAdmin` 分别验证组织管理员、组织所有者、项目管理员角色 [API/Handlers/ApiHandlerBase.cs:L28-L32]；`RequireOrgMembership` 验证普通成员身份 [API/Handlers/ApiHandlerBase.cs:L24-L26]。所有操作通过 `LogAudit` 方法记录审计日志 [API/Handlers/ApiHandlerBase.cs:L34]。

#### 5.1.3. 通用约定

**分页参数**：列表类接口统一接受 `page` 和 `pageSize` 两个查询参数，默认值由 `AgentInsightConst.DefaultPage` 和 `AgentInsightConst.DefaultPageSize` 定义（默认分别为 1 和 10）。Controller 层通过 `page.DefaultPage()` 和 `pageSize.DefaultPageSize()` 扩展方法将参数转换为实际查询值 [API/Controllers/PaymentManagement/OrderController.cs:L27-L28]。响应统一封装为 `ApiResponse<T>`，包含数据列表、总记录数、当前页码和当前页记录数。

**响应格式**：所有接口返回统一格式 `ApiResponse<T>`，结构如下：

```json
{
  "errorCode": 0,
  "data": { },
  "totalCount": 100,
  "page": 1,
  "pageSize": 10
}
```

**速率限制**：部分敏感接口通过 `[RateLimit]` 特性限制调用频率。例如下单接口限制为 10 秒内 1 次请求 [API/Controllers/PaymentManagement/OrderController.cs:L49]，订单状态查询接口限制为 1 秒内 1 次请求 [API/Controllers/PaymentManagement/OrderController.cs:L65]。

#### 5.1.4. 接口清单

内部接口按业务域划分，主要端点分类如下：

| 业务域 | Controller | 主要端点 | 功能说明 |
|--------|-----------|---------|---------|
| 用户管理 | UserController | POST /api/user/register, POST /api/user/login, POST /api/user/logout | 用户注册、登录、登出 |
| 用户管理 | UserController | POST /api/user/bind-wechat, POST /api/user/unbind-wechat | 微信绑定/解绑 |
| 用户管理 | UserController | POST /api/user/apikey, DELETE /api/user/apikey | API Key 管理 |
| 用户管理 | UserController | POST /api/user/role | 角色分配 |
| 组织管理 | OrganizationController | GET/POST/PUT/DELETE /api/org | Org CRUD |
| 项目管理 | ProjectController | GET/POST/PUT/DELETE /api/project | Project CRUD |
| 订单管理 | OrderController | GET /api/payment/order | 订单列表查询 [API/Controllers/PaymentManagement/OrderController.cs:L27] |
| 订单管理 | OrderController | POST /api/payment/order | 下单 [API/Controllers/PaymentManagement/OrderController.cs:L48] |
| 订单管理 | OrderController | GET /api/payment/order/query | 订单状态查询 [API/Controllers/PaymentManagement/OrderController.cs:L65] |
| 产品管理 | ProductController | GET /api/product | 产品列表 [API/Controllers/ProductManagement/ProductController.cs:L21] |
| 产品管理 | ProductController | GET /api/product/duration | 产品时长列表 [API/Controllers/ProductManagement/ProductController.cs:L34] |
| 数据查询 | MetricsController | GET /api/data/trace | Trace 查询与过滤 |
| 数据查询 | MetricsController | GET /api/data/observation | Observation 查询 |
| 数据查询 | MetricsController | GET /api/data/score | Score 查询 |
| 数据查询 | ModelController | GET /api/data/model | 模型定义查询 [API/Controllers/DataManagement/ModelController.cs:L21] |
| Alert管理 | AlertController | GET/POST/PUT/DELETE /api/alert | AlertConfig CRUD |
| Alert管理 | AlertController | GET /api/alert/records, POST /api/alert/read | Alert记录查询与已读标记 |
| Agent 管理 | AgentConfigController | GET/POST/PUT/DELETE /api/agent/config | Agent Config管理 |
| Agent 管理 | AgentReportController | GET/POST/PUT/DELETE /api/agent/report | Agent 报告模板管理 |
| Agent 管理 | AgentSessionController | GET /api/agent/session | Session列表/详情 [API/Controllers/AgentManagement/AgentSessionController.cs:L22] |
| Agent 管理 | AgentSessionController | POST /api/agent/session | 创建/更新Session [API/Controllers/AgentManagement/AgentSessionController.cs:L48] |
| Agent 管理 | AgentSessionController | GET /api/agent/session/delete | 删除Session [API/Controllers/AgentManagement/AgentSessionController.cs:L36] |
| 工具管理 | BulletinController | GET/POST/PUT/DELETE /api/tools/bulletin | Bulletin管理 |
| 工具管理 | CaptchaController | GET /api/tools/captcha | Captcha生成（图形/短信/邮箱） |

#### 5.1.5. 典型接口示例

以订单下单接口为例，其请求与响应格式如下：

**下单 (POST /api/payment/order)**

请求参数：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| orgid | string | 是 | Org ID |
| productid | string | 是 | Product ID |
| productdurationid | string | 是 | 产品时长 ID |
| paymethod | int | 是 | Payment方式：1=WeChat, 2=Alipay |
| subpaymethod | int | 是 | 子Payment方式：1=JSAPI, 2=Native, 3=小程序, 11=电脑网站 |

响应字段包含 `orderno`（订单号）、`state`（订单状态：1=Created, 2=Paid）、`codeurl`（Payment链接）、`qrcode`（二维码 Base64）、`prepayid`（预Payment ID）等 [API/Controllers/PaymentManagement/OrderController.cs:L42-L44]。

**错误码**：接口错误通过 `errorCode` 字段返回，常见错误码及含义如下：

| 错误码 | 名称 | 含义 |
|--------|------|------|
| 100031 | InvalidParameter | 请求参数无效 |
| 100038 | Unauthorized | 未认证或认证失败 |
| 130009 | OrderNotFound | 订单不存在 |
| 140008 | ProductNotFound | 产品不存在 |
| 150007 | InsufficientPermission | Privilege不足 |

### 5.2. 外部接口（Payment平台、Agents Service）

#### 5.2.1. Payment平台回调接口

AgentInsightService（保持原文） 集成微信Payment与Payment宝Payment，Payment结果通过异步通知方式回传。回调接口由 `NotifyController` 接收处理，该 Controller 标记为 `[ApiExplorerSettings(IgnoreApi = true)]` 且不在 Swagger 文档中展示 [API/Controllers/PaymentManagement/NotifyController.cs:L13-L16]。

**微信Payment回调 (POST /api/payment/notify/wechatnotify)**

处理成功返回字符串 `"success"`，失败返回 `"fail"` [API/Controllers/PaymentManagement/NotifyController.cs:L62-L68]。

**Payment宝Payment回调 (POST /api/payment/notify/alipaynotify)**

处理成功返回字符串 `"success"`，失败返回 `"fail"` [API/Controllers/PaymentManagement/NotifyController.cs:L57]。

签名验证与交易查询由 `PaymentService` 统一封装，支持微信Payment（JSAPI/Native/MiniProgram）与Payment宝Payment（电脑网站）[API/Common/Services/PaymentService.cs:L14-L19,L30-L35]。Payment成功后，通过 MediatR 发布 `PaymentTransactionNotification` 触发异步保存交易记录 [API/Notifications/PaymentTransactionNotification.cs:L8]。

**微信消息接口 (GET/POST /api/tools/wechat)**

除Payment回调外，系统还提供微信消息接口用于接收微信服务器推送的消息与事件。该接口同样标记为 `[ApiExplorerSettings(IgnoreApi = true)]` [API/Controllers/ToolsManagement/WeChat/WeChatController.cs:L13-L15]：

- **GET /api/tools/wechat**：微信服务器验证接口。接收 `signature`、`timestamp`、`nonce`、`echostr` 参数，通过 `WeChatService.ExamineSignature` 验证签名后返回 `echostr` 原文 [API/Controllers/ToolsManagement/WeChat/WeChatController.cs:L36-L41]。
- **POST /api/tools/wechat**：微信消息接收接口。验证签名后，将消息体（XML 格式）反序列化为 `WeChatMessage`，调用 `WeChatHandler.ProcessMessage` 处理消息，返回 XML 回复消息 [API/Controllers/ToolsManagement/WeChat/WeChatController.cs:L68-L80]。

#### 5.2.2. Agents 子项目服务

Agents 子项目是独立的 Python FastAPI Service，提供 AI Agent 运行时能力 [Agents/server.py:L1-L50]。该服务独立部署，不在当前 API 子项目范围内，本文档仅描述其调用协议，不包含内部实现。

**Agent 聊天接口 (POST /api/agent/insight)**

该端点接收用户聊天请求，由 Agents 服务处理并返回 Agent 洞察结果。请求与响应均使用 JSON 格式，认证方式与主 API 一致（JWT 或 API Key Basic Auth）。

**Session管理接口 (GET/DELETE /api/sessions/{session_id})**

- **GET /api/sessions/{session_id}**：获取指定Session的详细信息，包括消息历史与上下文。
- **DELETE /api/sessions/{session_id}**：删除指定Session。

主 API 中的 `AgentSessionController` 提供对应的Session管理能力，支持Session列表查询、详情获取、创建/更新与删除操作 [API/Controllers/AgentManagement/AgentSessionController.cs:L22-L48]。主 API 的Session管理端点（`/api/agent/session`）与 Agents 子项目的Session管理端点（`/api/sessions/{session_id}`）为同一Session数据的两种访问方式：主 API 端点面向控制台用户，提供业务层封装（Privilege校验、审计日志等）；Agents 子项目端点面向 Agent 运行时内部调用，提供轻量级Session操作。Session数据在主 API 与 Agents 服务间保持同步，确保用户在不同端点的Session体验一致。

#### 5.2.3. 外部依赖与可用性要求

外部接口的可用性直接影响核心业务流程，具体依赖如下：

| 外部依赖 | 用途 | 影响范围 |
|---------|------|---------|
| 微信Payment API | 下单、预Payment、订单查询、退款 | Payment流程不可用时，用户无法完成Payment [API/Common/Services/PaymentService.cs:L8-L10] |
| Payment宝 API | 下单、交易查询、退款 | 同上 |
| 微信服务 API | AccessToken 获取与刷新、签名验证、小程序登录 | AccessToken 过期会导致微信相关功能不可用 [API/Common/Services/WeChatService.cs:L12-L14] |
| ClickHouse | Trace 数据存储与查询 | 不可用时 Trace 查询接口返回错误 [API/Common/Services/ClickHouseClient.cs:L8] |
| Redis | BullMqService 消息队列、缓存 | 不可用时 Trace 摄入和项目删除异步任务失败 [API/Common/Services/BullMqService.cs:L9] |
| Agents 子项目 | Agent 聊天与Session管理 | 不可用时 Agent 聊天接口不可用 |

Payment回调接口的签名验证失败时，系统记录异常日志并返回失败响应，微信Payment平台将按策略重试通知。`NotifyController` 捕获所有异常并记录日志，确保回调接口的健壮性 [API/Controllers/PaymentManagement/NotifyController.cs:L40-L45]。

---

## 6. 数据需求

AgentInsightService（保持原文） 是面向 AI Agent 可Observation性与成本分析的服务平台，其数据需求覆盖用户与组织管理、业务数据（Order、Product、模型定义）、Trace 可Observation性指标（Trace/Observation/Score）以及审计与使用记录四大领域。本章节从数据模型、数据存储与数据流三个维度阐述系统的数据需求，确保各实体定义清晰、存储路由合理、数据流转可靠。

### 6.1. 数据模型

系统核心实体包括 User、Organization、Project、Alert、Order、Trace、Observation、Score、AgentConfig 等，分别归属于用户管理域、业务管理域与可Observation性数据域。

**用户与组织域**

| 实体 | 说明 | 关键字段 |
|------|------|----------|
| User | 用户账户，支持注册、登录、微信绑定 | Id, Mobile, WeChatOpenId, ApiKey |
| Organization | 组织实体，用户通过成员关系归属组织 | Id, Name, CreatedAt |
| OrganizationMembership | User-组织成员关系，含角色 | UserId, OrganizationId, Role (OWNER/MEMBER) |
| AgentConfig | 用户级 Agent Config | Id, UserId, DataSource(JSON), DefaultTemplateId |

用户与组织数据由 `UserHandler` 统一管理，处理注册、登录、微信绑定、API Key 管理与角色分配 [API/Handlers/UserManagement/UserHandler.cs]。`AgentConfigController` 提供当前用户 Agent Config的获取、创建/更新与删除操作，Config内容以 JSON 字符串形式存储 DataSource 与 DefaultTemplateId [API/Controllers/AgentManagement/AgentConfigController.cs]。

**业务管理域**

| 实体 | 说明 | 关键字段 |
|------|------|----------|
| AgentInsightProduct | 产品定义 | Id, Name, Price |
| AgentInsightProductDuration | 产品时长定义 | Id, ProductId, Duration |
| AgentInsightOrder | 订单实体 | Id, UserId, ProductId, Status |
| OrgPrivilege | 组织权益 | OrganizationId, PrivilegeId |
| ModelDefinition | 模型定义（含价格） | Id, Name, Provider, ModelType, Tier, InputPrice, OutputPrice, Unit, Currency, IsActive |

订单与产品数据由 `OrderHandler` 处理下单、查询与产品转换，`PlaceOrder` 方法校验组织归属、产品与时长有效性后创建订单 [API/Handlers/PaymentManagement/OrderHandler.cs]。`ModelHandler` 负责模型定义查询，支持按关键词、Project ID 与预定义模型过滤，并通过 `Includes(m => m.Prices, t => t.Prices)` 加载嵌套价格层级 [API/Handlers/DataManagement/ModelHandler.cs]。

**可Observation性数据域**

| 实体 | 说明 | 关键字段 |
|------|------|----------|
| Trace | 一次完整的请求链路 | Id, ProjectId, Name, Timestamp, InputTokens, OutputTokens, TotalTokens, ModelId, AgentId, TotalCost, Latency, Status |
| Observation | Trace 内的Observation点 | Id, TraceId, Type, Name, Timestamp, InputTokens, OutputTokens, TotalTokens, ModelId, TotalCost, Latency, Metadata |
| Score | Trace 的Score记录 | Id, TraceId, ObservationId, MetricName, Value, Timestamp, Metadata |

Trace 数据由 `MetricsHandler` 查询，其构造函数注入 `IClickHouseClient` 与键控的 `ISqlSugarClient`（KeyedService_ClickHouseDb），并通过 `_chdb.Queryable<Observation>()` 与 `_chdb.Queryable<Score>()` 访问 ClickHouse 中的Observation与Score数据 [API/Handlers/DataManagement/MetricsHandler.cs]。`MetricsController` 暴露 `GET /api/data/metrics/observations`、`GET /api/data/metrics/scores` 与 `GET /api/data/metrics/traces` 三个端点，分别返回 Observation 列表、Score 列表与 Trace 指标详情 [API/Controllers/DataManagement/MetricsController.cs]。

### 6.2. 数据存储

系统采用多数据库分域存储策略，KeyedService区分不同数据库客户端。连接字符串统一从Config文件中读取，使用 Npgsql 操作 PostgreSQL，ClickHouse 使用专用客户端。

**存储分域**

| 数据库 | 键控服务常量 | 存储内容 | 连接Config |
|--------|-------------|----------|----------|
| UserDb | KeyedService_UserDb | User、Org、成员关系 | ConnectionStrings.UserDbConnection |
| DataDb | KeyedService_DataDb | Order、Product、模型定义、AgentConfig | ConnectionStrings.DataDbConnection |
| TrackingDb | KeyedService_TrackingDb | 审计日志、使用记录 | ConnectionStrings.TrackingDbConnection |
| ClickHouseDb | KeyedService_ClickHouseDb | Trace、Observation、Score Metric | ConnectionStrings.ClickHouseDbConnection |

`MetricsHandler` 构造函数通过 `[FromKeyedServices(AgentInsightConst.KeyedService_UserDb)]`、`[FromKeyedServices(AgentInsightConst.KeyedService_DataDb)]` 与 `[FromKeyedServices(AgentInsightConst.KeyedService_ClickHouseDb)]` 注入三个数据库客户端，分别对应 UserDb、DataDb 与 ClickHouseDb [API/Handlers/DataManagement/MetricsHandler.cs]。`OrderHandler` 同样注入 UserDb 与 DataDb 两个客户端，订单查询使用 `Db.Queryable<AgentInsightOrder>()`（UserDb），组织成员关系校验使用 `DataDb.Queryable<OrganizationMembership>()` [API/Handlers/PaymentManagement/OrderHandler.cs]。

**连接Config规格**

```text
ConnectionStrings.UserDbConnection = PORT=${USER_DB_PORT};DATABASE=${USER_DB_NAME};HOST=postgres;PASSWORD=${USER_DB_PASSWORD};USER ID=${USER_DB_USER};Timeout=60;Pooling=true;MINIMUM POOL SIZE=10;MAXIMUM POOL SIZE=200;CONNECTION IDLE LIFETIME=300
ConnectionStrings.DataDbConnection = PORT=${DATA_DB_PORT};DATABASE=${DATA_DB_NAME};HOST=postgres;PASSWORD=${DATA_DB_PASSWORD};USER ID=${DATA_DB_USER};Timeout=60;Pooling=true;MINIMUM POOL SIZE=10;MAXIMUM POOL SIZE=200;CONNECTION IDLE LIFETIME=300
ConnectionStrings.TrackingDbConnection = PORT=${TRACKING_DB_PORT};DATABASE=${TRACKING_DB_NAME};HOST=postgres;PASSWORD=${TRACKING_DB_PASSWORD};USER ID=${TRACKING_DB_USER};Timeout=60;Pooling=true;MINIMUM POOL SIZE=10;MAXIMUM POOL SIZE=200
ConnectionStrings.ClickHouseDbConnection = Host=${CLICKHOUSE_HOST};Port=${CLICKHOUSE_PORT};Username=${CLICKHOUSE_USER};Password=${CLICKHOUSE_PASSWORD};Database=${CLICKHOUSE_DATABASE};MaxCompressors=10;MaxDecompressors=50;MaxConnections=30;ConnectTimeout=60
```

**缓存层**

系统使用 `IMemoryCache` 缓存用户信息与设置，`ApiControllerBase` 构造函数接收 `IMemoryCache cache` 参数并传递给子类 [API/Controllers/DataManagement/MetricsController.cs]。Redis 用于 `BullMqService` 消息队列，支撑 Trace 摄入与项目删除的异步任务处理 [API/Common/Services/BullMqService.cs:9]。

**ClickHouse 查询容错**

`MetricsHandler` 对 ClickHouse 查询异常进行捕获与分类处理：若异常非 `AppFriendlyException`，记录日志后判断是否为超时异常，超时抛出 `ExceptionCodes.ClickHouseTimeout`，否则抛出 `ExceptionCodes.ClickHouseQueryFailed` [API/Handlers/DataManagement/MetricsHandler.cs]。此外，`ShouldSkipObservationsFinal` 方法读取Config项 `ClickHouseSettings:SkipObservationsFinal`（默认 False），用于控制是否跳过 Observation 最终处理 [API/Handlers/DataManagement/MetricsHandler.cs]。

### 6.3. 数据流

系统数据流涵盖 Trace 摄入、Payment交易与Alert触发三条核心链路，均采用异步解耦设计。

**Trace 摄入链路**

Trace 数据经 API 网关进入系统后，由 `AgentInsightTransformProvider` 调用 `BullMqService.EnqueueTraceIngestionAsync` 将摄入任务入队 [API/System/Handlers/AgentInsightTransformProvider.cs:8]。`BullMqService` 基于 Redis 实现消息队列，异步消费 Trace 摄入任务并写入 ClickHouse [API/Common/Services/BullMqService.cs:12-14]。该链路实现写入与查询分离：API 请求仅完成入队即返回，ClickHouse 写入由后台消费者异步执行，避免阻塞主链路。

```text
AgentInsightTransformProvider → BullMqService.EnqueueTraceIngestionAsync → Redis Queue → 后台消费者 → ClickHouse
```

**Payment交易链路**

Payment流程由 `OrderHandler.PlaceOrder` 发起，调用 `PaymentService` 创建微信Payment/Payment宝Payment订单 [API/Handlers/PaymentManagement/OrderHandler.cs:8]。Payment回调由 `NotifyHandler` 接收并验证签名，验证通过后通过 MediatR 发布 `PaymentTransactionNotification` [API/Notifications/PaymentTransactionNotification.cs:8]。`PaymentTransactionSaveHandler` 订阅该通知并调用 `IPaymentService` 异步保存交易记录 [API/Notifications/PaymentTransactionSaveHandler.cs:8]。

```text
OrderHandler.PlaceOrder → PaymentService.CreateOrder → Payment平台回调 → NotifyHandler.VerifySignature → MediatR.Publish(PaymentTransactionNotification) → PaymentTransactionSaveHandler → 异步落库
```

**Alert触发链路**

`AlertService` 负责Alert评估，计算指标是否满足Alert条件 [API/Common/Services/AlertService.cs]。当条件满足时，通过 MediatR 发布 `AlertTriggeredNotification` [API/Notifications/AlertTriggeredNotification.cs:5]，`SystemAlertHandler` 订阅该通知并调用 `IAlertService` 执行Alert处理 [API/Notifications/SystemAlertHandler.cs:8]。`AlertHandler` 作为用户侧Alert管理入口，同样依赖 `AlertService` 执行Alert规则评估 [API/Handlers/UserManagement/AlertHandler.cs:7]。

```text
AlertService.Evaluate → 条件满足 → MediatR.Publish(AlertTriggeredNotification) → SystemAlertHandler → Alert处理
```

**审计日志链路**

`ApiHandlerBase` 提供 `LogAudit` 方法记录操作审计，所有继承该基类的 Handler 在处理请求时自动写入审计日志 [API/Handlers/ApiHandlerBase.cs:34]。审计数据写入 TrackingDb，配合 `AuditSettings:Enabled=True` Config项控制审计功能的启用状态。

---

## 7. 约束条件

AgentInsightService（保持原文） 是一个面向组织管理员（Org Admin/Owner）、项目管理员（Project Admin）及普通成员的多租户 Agent 可Observation性与分析平台，通过 `ApiHandlerBase` 中的 `RequireOrgAdmin`、`RequireOrgOwner`、`RequireProjectAdmin`、`RequireOrgMembership` 等方法实施细粒度的Privilege控制 [API/Handlers/ApiHandlerBase.cs:24-32]。系统涉及Payment交易、用户数据、Trace 可Observation性数据等敏感信息，因此在技术选型、业务流程和合规层面均设有严格约束。本章从技术约束、业务约束、合规约束三个维度，系统阐述 AgentInsightService（保持原文） 在开发与运维过程中必须遵守的强制性规则。

### 7.1. 技术约束

AgentInsightService（保持原文） 的技术栈选型具有强制性，开发过程中不得随意替换或引入未经批准的第三方依赖。以下技术约束适用于所有后端服务、API 层及基础设施组件的开发。

#### 7.1.1. 技术栈锁定

AgentInsightService（保持原文） 后端基于 .NET 技术体系构建，核心依赖库已锁定，包括：AlipaySDKNet.Standard（Payment宝 SDK）、MediatR（进程内消息/命令总线）、BouncyCastle.Cryptography（加密算法库）、Microsoft.SemanticKernel（AI 编排框架）、StackExchange.Redis（Redis 客户端）等。这些依赖已在项目元数据中明确声明，新增或升级依赖必须经过架构评审，禁止引入与现有技术栈功能重叠的替代框架。

| 接口 | 限流规则 | 依据 |
|------|---------|------|
| `POST /api/payment/order`（下单） | 每 10 秒最多 1 次请求 | [API/Controllers/PaymentManagement/OrderController.cs:41-43] |
| `GET /api/payment/order/query`（订单查询） | 每 1 秒最多 1 次请求 | [API/Controllers/PaymentManagement/OrderController.cs:55-57] |

限流特性通过 `[RateLimit(maxRequests, windowSeconds)]` 特性声明，由 `AgentInsightTransformProvider` 在 API 网关层统一执行 [API/System/Handlers/AgentInsightTransformProvider.cs]。开发人员不得移除或放宽现有接口的限流约束。

### 7.2. 业务约束

业务约束规定了 AgentInsightService（保持原文） 在功能实现、Privilege控制、审计Trace等方面的强制性要求，确保业务流程的一致性和可追溯性。

#### 7.2.1. Privilege控制约束

所有 Handler 类必须继承自 `ApiHandlerBase`，并在执行写操作或敏感读操作前调用相应的Privilege验证方法：

| Privilege方法 | 适用角色 | 说明 |
|---------|---------|------|
| `RequireOrgAdmin` | 组织管理员 | 组织级管理操作 |
| `RequireOrgOwner` | 组织所有者 | 组织级敏感操作（如删除组织） |
| `RequireProjectAdmin` | 项目管理员 | 项目级管理操作 |
| `RequireOrgMembership` | 普通成员 | 组织成员身份验证 |

Privilege验证方法定义于 `ApiHandlerBase` 中 [API/Handlers/ApiHandlerBase.cs:24-32]，所有 Handler 在进入业务逻辑前必须完成Privilege校验，禁止绕过Privilege验证直接操作数据。`ApiControllerBase` 通过 `AutoSetUserFilter` 在请求生命周期内完成用户上下文的初始化，并将用户信息注入到已注册的 Handler 中 [API/Controllers/ApiControllerBase.cs:14-20]。

#### 7.2.2. 审计日志约束

所有写操作（创建、更新、删除）必须通过 `ApiHandlerBase.LogAudit` 方法记录审计日志 [API/Handlers/ApiHandlerBase.cs:34]。审计日志的资源类型必须引用 `AuditEnum` 枚举中定义的类型 [Models/Common/Enums/AuditEnum.cs:18]，禁止使用自定义字符串作为资源类型标识。

审计日志至少应包含以下信息：
- 操作者用户 ID
- 操作类型（创建/更新/删除）
- 资源类型（引用 `AuditEnum` 枚举）
- 资源 ID
- UTC
- 操作上下文（Org ID、Project ID 等）

审计日志的写入必须与业务操作在同一事务内完成，确保审计记录的完整性和一致性。禁止在业务操作成功后异步补写审计日志（除非该操作本身是异步任务）。

#### 7.2.3. 订单与Payment流程约束

订单创建流程必须遵循"先下单、再Payment、后查询"的固定顺序。`OrderController.Place` 方法接收 `AgentInsightOrderBody`，其中 `paymethod` 字段决定Payment渠道（1=WeChat, 2=Alipay），`subpaymethod` 字段决定具体Payment方式（1=JSAPI, 2=Native, 3=小程序, 11=电脑网站）[API/Controllers/PaymentManagement/OrderController.cs:44-50]。

订单状态流转必须严格遵循以下状态机：

| 状态 | 枚举值 | 说明 |
|------|--------|------|
| Created | 1 | 订单已创建 |
| Paid | 2 | 订单已Payment |
| Refunded | 3 | 订单已退款 |
| Cancelled | 4 | 订单已取消 |
| Closed | 5 | 订单已关闭 |
| PaymentException | 6 | Payment异常 |

`PaymentService.CreateOrder` 方法在创建订单时初始化 `OrderStatus = OrderStatus.Created`、`PaymentStatus = PaymentStatus.Created` [API/Common/Services/PaymentService.cs:48-62]。禁止跳过中间状态直接变更订单状态，例如禁止将 Created 状态直接变更为 Refunded。

#### 7.2.4. 用户与组织管理约束

用户注册、登录、微信绑定等操作由 `UserHandler` 统一处理 [API/Handlers/UserManagement/UserHandler.cs]。登录方式支持密码登录、短信登录、微信登录、小程序登录和 API Key 登录（`logintype: 1=密码, 2=短信, 3=微信, 4=小程序, 5=APIKey`），其中 API Key 登录需在 Authorization 头携带 `Basic publickey:secretkey` [API/Controllers/UserManagement/UserController.cs:42-49]。

组织管理员和项目管理员的角色分配必须通过 `UserHandler` 中的角色分配方法完成，禁止直接修改数据库中的角色字段。普通成员仅能通过 `RequireOrgMembership` 验证后访问组织内的基础资源。

### 7.3. 合规约束

合规约束涉及Payment数据安全、加密密钥管理、第三方接口调用规范等方面，是 AgentInsightService（保持原文） 满足金融监管和行业标准的基本要求。

#### 7.3.1. Payment签名验证合规

所有Payment相关的签名验证必须严格遵循微信Payment V3 和Payment宝开放平台的官方规范，禁止自行实现或简化签名验证逻辑。

**微信Payment V3 签名验证**：`NotifyController.WeChatNotify` 接收微信Payment异步通知时，必须先调用 `NotifyHandler.ExamineWeChatRequest` 验证请求签名，验证通过后才可处理通知内容 [API/Controllers/PaymentManagement/NotifyController.cs:29-43]。签名验证过程由 `WeChatService` 中的 `ExamineSignature` 方法执行 [API/Controllers/ToolsManagement/WeChat/WeChatController.cs:24-31]，该方法使用微信官方签名算法，对 `signature`、`timestamp`、`nonce` 参数进行校验。验证失败时必须拒绝请求并返回错误响应，禁止将未通过签名验证的请求视为有效通知。

**Payment宝签名验证**：`NotifyController.AlipayNotify` 处理Payment宝异步通知时，必须通过 `NotifyHandler.ProcessAlipayNotify` 完成签名验证和业务处理 [API/Controllers/PaymentManagement/NotifyController.cs:57-68]。Payment宝签名验证使用 `Aop.Api.Util` 中的 `AlipaySignature.RSACheckV1` 工具类，验证失败时返回 `"fail"` 响应，验证成功返回 `"success"` 响应。

Payment签名验证相关的错误码定义如下：

| errorCode | 常量名 | 说明 |
|-----------|--------|------|
| 810002 | `AlipayConfigNotSetError` | Payment宝Config未设置 |
| 810003 | `AlipayConnectionError` | Payment宝连接错误 |
| 810004 | `AlipayTransactionError` | Payment宝交易错误 |
| 810005 | `InvalidAlipayTradeNoError` | 无效的Payment宝交易号 |
| 810006 | `InvalidAlipayTradeError` | 无效的Payment宝交易 |
| 810007 | `AlipaySignatureError` | Payment宝签名错误 |
| 810008 | `AlipaySignatureParamError` | Payment宝签名参数错误 |
| 810020 | `AlipayPlaceOrderError` | Payment宝下单错误 |

以上错误码定义于 `Models/Common/Enums` 命名空间，业务代码中必须引用枚举常量而非硬编码数值 [Models/Common/Enums/AuditEnum.cs:18]。

#### 7.3.2. 加密密钥管理合规

所有敏感数据的加密密钥必须通过环境变量注入，禁止在代码、Config文件或日志中明文出现。具体密钥约束如下：

| 密钥项 | 环境变量 | 用途 |
|--------|---------|------|
| AES 加密密钥 | `${AES_ENCRYPTION_KEY}` | 敏感数据字段的 AES 加密/解密 |
| JWT 签名密钥 | `${JWT_SIGNING_KEY}` | JWT Token 签名与验证 |
| JWT 签发者 | `${JWT_ISSUER}` | JWT 签发者标识 |
| JWT 受众 | `${JWT_AUDIENCE}` | JWT 受众标识 |
| 数据库密码 | `${DB_PASSWORD}` 等 | PostgreSQL 数据库访问 |

`JwtSettings` Config项从 `${JWT_SIGNING_KEY}`、`${JWT_ISSUER}`、`${JWT_AUDIENCE}` 环境变量注入，用于对Payment回调中的敏感字段（如用户手机号、Payment凭证等）进行加密存储。JWT Token 的有效期默认设置为 12 小时，过期后用户需重新认证。密钥轮换必须制定明确的运维流程，轮换期间需保证新旧密钥的平稳过渡。

#### 7.3.3. 第三方接口调用合规

系统与微信、Payment宝等第三方平台的交互必须遵守以下合规约束：

1. **微信服务器回调验证**：`WeChatController` 的 `Get` 方法用于微信服务器验证接口，必须通过 `ExamineSignature` 验证通过后才返回 `echostr` 原文 [API/Controllers/ToolsManagement/WeChat/WeChatController.cs:24-31]。验证失败时抛出 `ExceptionCodes.WeChatSignatureError` 异常，禁止向未经验证的请求返回任何有效数据。

2. **Payment回调幂等性**：Payment平台可能因网络原因重复发送异步通知，`NotifyHandler` 处理通知时必须保证幂等性。同一笔订单的重复通知不得导致重复发货或重复更新订单状态。

3. **微信 AccessToken 管理**：`WeChatService` 负责微信 AccessToken 的获取与缓存管理，AccessToken 的获取频率受微信平台限制，必须使用缓存机制避免频繁调用微信接口 [API/Common/Services/WeChatService.cs]。

4. **API Key 认证**：`AgentInsightTransformProvider` 处理 API 网关层的 Basic Auth 认证和 API Key 验证 [API/System/Handlers/AgentInsightTransformProvider.cs]。API Key 的生成、存储和验证必须使用安全的加密算法，禁止明文存储 API Key。

#### 7.3.4. 数据保护与隐私合规

AgentInsightService（保持原文） 处理用户个人信息、组织Config、Trace 数据等敏感信息，必须遵守以下数据保护约束：

1. **数据最小化**：系统仅收集业务运行所必需的数据，禁止采集与功能无关的个人敏感信息。
2. **传输加密**：所有外部接口调用必须使用 HTTPS/TLS 加密传输，禁止通过明文 HTTP 传输敏感数据。
3. **日志脱敏**：日志输出中禁止包含完整的密码、密钥、Token 等敏感信息，必须进行脱敏处理。
4. **数据留存期限**：审计日志和Payment记录的留存期限不得低于监管要求，过期数据必须安全删除。

以上合规约束为 AgentInsightService（保持原文） 的安全稳定运行提供了制度保障，开发、测试和运维人员必须严格遵守。

---

## 8. 风险与依赖

AgentInsightService（保持原文） 是一个面向组织的 AI Agent 可Observation性与Payment管理平台。系统提供 Trace 数据采集与分析、Alert（Alert）、用户与组织管理、Payment集成（微信Payment/Payment宝Payment）以及 Agent Config管理能力。作为平台级服务，AgentInsightService（保持原文） 在运行时依赖多个外部服务和基础设施组件，这些依赖的可用性、性能与安全性直接影响系统的整体稳定性。本章节系统梳理 AgentInsightService（保持原文） 的外部服务依赖风险、基础设施依赖风险以及安全与密钥管理风险，并针对每类风险给出对应的缓解策略与运维建议。

### 8.1. 外部服务依赖风险

AgentInsightService（保持原文） 的核心业务链路中，Payment流程和微信生态功能均依赖外部平台提供的 API Service。这些外部服务的可用性不受本系统控制，一旦出现故障或限流，将直接影响用户的订单创建、Payment回调处理和微信消息收发等关键功能。

#### 8.1.1. 微信Payment与Payment宝 API 依赖

Payment集成是 AgentInsightService（保持原文） 的核心能力之一。系统通过 `PaymentService` 统一封装微信Payment（JSAPI/Native/MiniProgram）和Payment宝Payment的下单、签名验证、交易查询与回调处理逻辑 [API/Common/Services/PaymentService.cs]。`OrderHandler.PlaceOrder` 在创建订单后调用 `PaymentService` 获取Payment参数 [API/Handlers/PaymentManagement/OrderHandler.cs:13]，Payment平台随后异步通知到 `POST /api/payment/notify/wechatnotify` 或 `/alipaynotify` 接口 [API/Controllers/PaymentManagement/NotifyController.cs:29,57]。

该依赖的主要风险包括：

| 风险项 | 影响范围 | 严重程度 |
|--------|----------|----------|
| 微信Payment API 不可用或超时 | 用户无法发起微信Payment，订单创建流程中断 | 高 |
| Payment宝 API 不可用或超时 | 用户无法发起Payment宝Payment，订单创建流程中断 | 高 |
| Payment平台回调延迟或丢失 | 订单状态无法及时更新，用户已付款但系统未确认 | 高 |
| Payment平台接口协议变更 | 签名验证失败，Payment流程完全不可用 | 中 |

针对上述风险，系统在 `NotifyController` 中已实现基础的异常捕获与日志记录 [API/Controllers/PaymentManagement/NotifyController.cs:40-47,65-71]，但建议进一步强化以下缓解措施：

1. **超时重试机制**：所有对微信Payment和Payment宝 API 的 HTTP 调用必须设置合理的超时时间（建议 5-10 秒），并对瞬时故障（网络抖动、5xx 错误）实施指数退避重试策略，重试次数建议 3 次。
2. **回调幂等处理**：Payment平台可能因网络原因重复推送回调通知，`NotifyHandler` 在处理回调时必须保证幂等性，避免同一笔订单被重复更新。
3. **主动对账**：对于长时间处于"已Payment待确认"状态的订单，系统应定期调用Payment平台的交易查询接口进行主动对账，确保订单状态的最终一致性。
4. **降级预案**：当检测到Payment平台大面积故障时，应通过Bulletin系统（`BulletinHandler`）及时向用户发布维护通知，避免用户反复尝试下单造成体验恶化。

#### 8.1.2. 微信服务依赖

AgentInsightService（保持原文） 的微信生态功能（包括微信登录、消息模板发送、公众号/小程序交互等）依赖微信公众平台提供的 AccessToken 及各类开放接口。系统通过 `WeChatHandler` 封装微信消息处理逻辑 [API/Handlers/ToolsManagement/WeChat/WeChatHandler.cs:12-14]，并在用户绑定/解绑微信及消息收发过程中调用微信 API。该依赖的主要风险包括：

| 风险项 | 影响范围 | 严重程度 |
|--------|----------|----------|
| AccessToken 获取失败或过期 | 微信消息发送、用户信息拉取等操作失败，微信生态功能不可用 | 高 |
| AccessToken 刷新机制失效 | 缓存中的 AccessToken 过期后无法及时刷新，导致所有依赖 Token 的微信 API 调用持续失败 | 高 |
| 微信 API 接口限流 | 高频调用触发微信平台限流，消息发送延迟或失败 | 中 |
| 微信平台接口协议变更 | 消息格式或接口签名规则调整，导致现有实现失效 | 中 |

针对上述风险，建议采取以下缓解措施：

1. **AccessToken 缓存与预刷新**：AccessToken 获取后应缓存在内存或 Redis 中，并设置合理的过期时间（微信默认 7200 秒）。在 Token 过期前（如剩余 5 分钟）主动触发后台刷新任务，避免在请求路径上同步获取。同时，需监控刷新任务的执行状态，若连续多次刷新失败应立即Alert，防止因刷新机制失效导致 Token 过期后所有依赖调用中断。
2. **失败Alert**：当微信 API 返回 `errcode` 为 `40001`（AccessToken 无效）、`42001`（AccessToken 过期）或 `45009`（接口调用超限）等错误码时，应立即触发Alert通知运维人员 [API/Resources/Text.zh-CN.json]。
3. **多公众号/小程序Config**：对于关键业务，建议Config多个微信应用作为冗余，当主应用 AccessToken 异常时自动切换至备用应用，降低单点故障影响。
4. **限流与退避**：对微信 API 调用实施客户端限流，避免因突发流量触发平台限流。收到限流错误码时，采用指数退避策略进行重试。

### 8.2. 基础设施依赖风险

AgentInsightService（保持原文） 采用多数据库分离架构，依赖 ClickHouse、Redis、PostgreSQL 等基础设施组件。这些组件的可用性和性能直接决定系统的吞吐能力与查询响应速度。

#### 8.2.1. ClickHouse 依赖

Trace 数据的存储与查询完全依赖 ClickHouse 集群。`MetricsHandler` 通过 `ClickHouseClient` 执行 Trace/Observation/Score 的分页查询与过滤 [API/Handlers/DataManagement/MetricsHandler.cs:7]，连接字符串Config为 `Host=clickhouse-server;Port=8123;Database=default;Username=default;Password=******`，其中包含 `Compression=true;ReadBufferSize=10;WriteBufferSize=50;MaxExecutionTime=30;ConnectTimeout=60` 等关键参数。

主要风险：

| 风险项 | 影响范围 | 严重程度 |
|--------|----------|----------|
| ClickHouse 集群不可用 | 所有 Trace 查询接口返回错误，可Observation性功能完全不可用 | 高 |
| 查询性能退化 | 数据量增长后查询延迟上升，影响用户体验 | 中 |
| 连接池耗尽 | 高并发查询下连接池被占满，新查询等待超时 | 中 |
| 数据写入延迟 | Trace 摄入链路堆积，实时性下降 | 中 |

缓解措施：

1. **连接池监控**：持续监控 `ClickHouseClient` 连接池的使用率，当活跃连接数超过 `MaxExecutionTime=30` 对应连接池容量的 80% 时触发Alert。连接超时设置为 30 秒（`ConnectTimeout=30`），防止连接泄漏导致请求无限等待。
2. **查询超时控制**：所有查询必须设置 `MaxExecutionTime=60`（60 秒），避免慢查询长时间占用连接。对于复杂的 Trace 过滤查询，建议增加查询复杂度限制。
3. **集群冗余**：生产环境应部署 ClickHouse 集群（多副本），避免单点故障。定期备份数据，确保可恢复性。
4. **降级策略**：当 ClickHouse 不可用时，Trace 查询接口应快速失败（fail-fast）并返回明确的错误信息（如 `ErrorCode = 150010`、`ErrorMessage = 150017`），而不是长时间阻塞用户请求。

#### 8.2.2. Redis 依赖

Redis 在 AgentInsightService（保持原文） 中承担双重角色：一是作为 `BullMqService` 消息队列的底层存储，处理 Trace 摄入和项目删除等异步任务 [API/Common/Services/BullMqService.cs:12-14]；二是作为缓存层（通过 `IMemoryCache` 缓存用户信息、设置等 [API/Common/Services/UserService.cs:10]）。

Redis 单点故障可能导致以下后果：

- **消息丢失**：`BullMqService` 依赖 Redis 的列表/流数据结构实现队列。如果 Redis 宕机且未Config持久化，队列中尚未消费的消息将全部丢失，导致 Trace 数据摄入中断或项目删除任务无法完成。
- **缓存雪崩**：Redis 不可用后，所有原本命中缓存的请求将直接穿透到数据库，可能导致 PostgreSQL 负载骤增。
- **任务堆积**：`EnqueueTraceIngestionAsync` 和 `EnqueueProjectDeleteAsync` 等入队操作失败时，异步任务将无法执行 [API/System/Handlers/AgentInsightTransformProvider.cs:8]。

缓解措施：

1. **哨兵/集群模式**：生产环境必须部署 Redis Sentinel或 Redis Cluster 模式，避免单点故障。哨兵模式提供自动故障转移，Cluster 模式提供数据分片与高可用。具体Config建议如下：
   - **哨兵模式**：部署 3 个哨兵节点（奇数个，保证 quorum 可用），`sentinel monitor <master-name> <redis-master-ip> <redis-port> <quorum>`，quorum 建议设置为 2。哨兵节点与被监控的 Redis 主从节点分离部署，避免同机房故障导致哨兵全部不可用。
   - **Cluster 模式**：至少部署 3 主 3 从共 6 个节点，`cluster-enabled yes`，每个主节点Config一个从节点。`cluster-node-timeout` 建议设置为 5000 毫秒，`cluster-require-full-coverage` 设置为 `no`，避免部分节点故障时整个集群拒绝服务。
   - **故障切换流程**：哨兵模式下，当主节点不可达时，哨兵集群通过投票选举（quorum 达成一致）选出新的主节点，自动完成故障转移，客户端通过哨兵发现新主节点地址；Cluster 模式下，当主节点不可达超过 `cluster-node-timeout` 时，从节点自动提升为主节点，集群状态更新并继续对外服务。建议定期进行故障切换演练，验证切换流程的有效性。
2. **持久化Config**：启用 Redis AOF（Append Only File）持久化，并设置合理的 `appendfsync` 策略（建议 `everysec`），在性能与数据安全之间取得平衡。
3. **队列消费监控**：监控 `BullMqService` 队列的长度和消费速率。当队列积压超过阈值时触发Alert，及时排查消费者异常。
4. **缓存降级**：`IMemoryCache` 作为本地缓存与 Redis 形成两级缓存架构，Redis 不可用时本地缓存仍可提供部分命中能力，但需注意本地缓存的一致性。

#### 8.2.3. PostgreSQL 多数据库依赖

系统采用 UserDb、DataDb、TrackingDb 三个 PostgreSQL 数据库分离架构，分别存储用户/组织数据、业务数据（Order、Alert等）和Trace数据。连接字符串Config包含 `MaxPoolSize=10;MinPoolSize=200;Timeout=300` 等参数。

主要风险：

- **连接池耗尽**：高并发场景下，连接池最大连接数（200）可能被占满，导致新请求等待超时（Timeout=60 秒）。
- **主从延迟**：如果采用读写分离架构，主从复制延迟可能导致刚写入的数据无法立即读取。
- **磁盘空间不足**：Trace 数据和审计日志持续增长，磁盘空间耗尽将导致数据库写入失败。

缓解措施：

1. **连接池监控与调优**：监控各数据库连接池的使用率，根据业务峰值调整 `MaxPoolSize`。`Timeout=300` 确保连接定期回收，避免连接泄漏。
2. **定期归档**：对 ClickHouse 中的 Trace 数据和 PostgreSQL 中的审计日志实施定期归档策略，控制数据增长速率。
3. **备份与恢复演练**：定期执行数据库备份恢复演练，确保灾难场景下可快速恢复服务。

### 8.3. 安全与密钥管理风险

AgentInsightService（保持原文） 涉及Payment、用户隐私和 AI Agent Config等敏感数据，密钥管理与安全防护是系统稳定运行的生命线。

#### 8.3.1. JWT 签名密钥风险

系统使用 JWT（JSON Web Token）进行用户认证，签名算法为 HS256，签名密钥来自环境变量 `${JWT_SIGNING_KEY}`（Config项 `JwtSettings.SigningKey`）。JWT 的完整Config包括：

| Config项 | 值 | 说明 |
|--------|-----|------|
| `JwtSettings.Algorithm` | HS256 | 签名算法 |
| `JwtSettings.SigningKey` | `${JWT_SIGNING_KEY}` | 签名密钥（环境变量注入） |
| `JwtSettings.Issuer` | `${JWT_ISSUER}` | 合法签发者 |
| `JwtSettings.Audience` | `${JWT_AUDIENCE}` | 合法受众 |
| `JwtSettings.ExpireMinutes` | 43200 | Token 有效期（分钟），即 30 天 |
| `JwtSettings.ClockSkewMinutes` | 5 | 时钟偏移容忍（分钟） |

JWT 签名密钥泄露的风险与后果：

- **Token 伪造**：攻击者获取 `${JWT_SIGNING_KEY}` 后，可以伪造任意用户的 JWT Token，绕过认证直接调用管理接口。
- **Privilege提升**：伪造 Token 可赋予攻击者 Org Admin/Owner 或 Project Admin Privilege，进而访问组织数据、修改Config、创建订单等。
- **数据泄露**：攻击者可利用伪造 Token 查询 Trace 数据、用户信息、Payment记录等敏感数据。

缓解措施：

1. **密钥轮换机制**：建立定期密钥轮换制度，建议每 90 天轮换一次 JWT 签名密钥。轮换时采用双密钥并行策略——新旧密钥同时生效一段时间（如 24 小时），确保旧 Token 在有效期内仍可验证，新 Token 使用新密钥签发，待旧 Token 全部过期后完成切换。
2. **密钥保管**：签名密钥必须通过环境变量或专用的密钥管理服务（如 AWS KMS、Azure Key Vault、HashiCorp Vault）注入，严禁硬编码在代码仓库或Config文件中。密钥的访问Privilege应遵循最小Privilege原则，仅限部署和运维人员通过安全通道获取。
3. **密钥泄露应急响应**：一旦发现密钥疑似泄露，应立即执行以下操作：(a) 立即更换签名密钥；(b) 将 Token 有效期临时缩短（如调整为 30 分钟），加速旧 Token 失效；(c) 审计认证日志，排查异常访问行为；(d) 通知可能受影响的组织管理员，建议其检查账户活动。
4. **Token 有效期控制**：当前 Token 有效期为 30 天，建议根据业务安全需求适当缩短（如 7 天），并引导客户端实现静默续期机制，降低 Token 泄露后的风险窗口。
5. **审计与监控**：对 JWT 认证失败事件（签名验证失败、过期 Token 等）进行日志记录和监控，异常频率触发Alert时及时排查潜在攻击行为。

---

## 9. 优先级路线图

AgentInsightService（保持原文） 是一个面向 AI Agent 可Observation性领域的服务，提供 Trace 数据查询、Alert管理、Agent Config、Payment与组织管理等能力。其 API 子项目基于 .NET 构建，包含用户认证、Org/项目管理、Payment核心流程、数据查询、Alert管理、Agent Config、Bulletin管理、微信消息处理、报告模板等模块；同时包含一个独立的 Python FastAPI Agents提供 AI Agent 运行时能力（如 `POST /api/agent/insight` 聊天接口与 `GET/DELETE /api/sessions/{session_id}` Session管理接口）。本章节依据代码仓库的实际实现，将功能建设划分为 P0-P3 四个优先级，明确各阶段的核心交付目标、涉及的关键模块与依赖关系，为后续迭代提供路线指引。

### 9.1. P0 - 核心基石

P0 阶段聚焦于 AgentInsightService（保持原文） 的最小可用闭环，确保系统具备用户身份认证、Org/项目资源隔离以及Payment交易处理三大基础能力。该阶段是产品上线的前提条件，任何一项缺失都将导致用户无法正常注册、创建资源或完成付费流程。

**用户认证与组织/项目管理**

用户认证是系统的第一道入口。`UserHandler` 位于 `API/Handlers/UserManagement/UserHandler.cs`，负责处理用户注册、登录、微信绑定、API Key 管理以及角色分配等核心逻辑。该Handler通过依赖注入调用 `UserService` 与 `WeChatService` 完成用户数据的持久化与第三方认证（依赖关系见 `API/Handlers/UserManagement/UserHandler.cs:6-7`）。所有 Handler 均继承自 `ApiHandlerBase`（`API/Handlers/ApiHandlerBase.cs`），该基类通过 `IAppContextService` 提供当前用户上下文、Org/项目Privilege验证以及审计日志能力（依赖关系见 `API/Handlers/ApiHandlerBase.cs:10`），确保每个请求都能追溯到具体的用户与组织。

组织与项目管理涉及 `OrganizationController` 与 `ProjectController`，它们分别处理组织的创建、成员管理、项目生命周期等操作。Privilege模型通过 `OrganizationMembership` 实体实现，其中 `PGRole.OWNER` 角色拥有组织内最高Privilege（见 `API/Handlers/PaymentManagement/OrderHandler.cs:30-36`），这一设计在订单查询、项目Config等多个场景中被复用。

**Payment核心流程**

Payment流程是商业化闭环的关键。`OrderController`（`API/Controllers/PaymentManagement/OrderController.cs`）暴露了四个核心端点：

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/payment/order` | GET | 获取订单列表（分页） |
| `/api/payment/order` | POST | 下单（创建订单） |
| `/api/payment/order/query` | GET | 根据订单号查询订单状态 |
| `/api/payment/order/conversion` | GET | 产品转换 |

下单后，`OrderHandler.PlaceOrder` 创建订单并调用 `PaymentService` 获取Payment参数（依赖关系见 `API/Handlers/PaymentManagement/OrderHandler.cs:13`）。Payment平台异步通知由 `NotifyController` 接收（`POST /api/payment/notify/wechatnotify` 与 `/alipaynotify`），`NotifyHandler` 验证签名后更新订单状态，并通过 MediatR 发布 `PaymentTransactionNotification` 触发异步保存（见 `API/Handlers/PaymentManagement/NotifyHandler.cs:13-14`）。

**P0 验收标准**

- 用户可完成注册、登录与微信绑定
- 组织管理员可创建组织与项目，并管理成员角色
- 用户可下单并完成微信Payment/Payment宝PaymentPayment，Payment回调可正确更新订单状态
- 所有请求均可追溯到具体的用户与组织

### 9.2. P1 - 核心能力扩展

P1 阶段在 P0 基础上扩展 Trace 数据查询、Alert管理和 Agent Config三大核心能力，使系统具备完整的可Observation性闭环。

**Trace 数据查询**

`MetricsHandler`（`API/Handlers/DataManagement/MetricsHandler.cs`）负责 Trace 数据查询与过滤，同时支持 Observation 与 Score 查询（见 `API/Handlers/DataManagement/MetricsHandler.cs:12-16`）。该Handler通过 `ClickHouseClient` 访问 ClickHouse 数据库，支持按时间范围、Project、模型等多维度过滤 Trace 数据。`ModelHandler`（`API/Handlers/DataManagement/ModelHandler.cs`）提供 Model 定义查询能力。

**Alert管理**

`AlertService`（`API/Common/Services/AlertService.cs`）是Alert评估的核心服务，负责计算指标是否满足Alert条件。`AlertHandler` 位于 `API/Handlers/UserManagement/AlertHandler.cs`，通过依赖注入调用 `AlertService`（依赖关系见 `API/Handlers/UserManagement/AlertHandler.cs:7`）。Alert通知通过 `SystemAlertHandler`（`API/Notifications/SystemAlertHandler.cs`）异步发送，该Handler同样依赖 `IAlertService`（依赖关系见 `API/Notifications/SystemAlertHandler.cs:8`）。

Alert评估的关键方法包括 `GetTimeSpan`（计算时间窗口）、`IsConditionMet`（判断条件是否满足）、`BuildAlertMessage`（构造Alert消息），这些方法均定义在 `AlertService` 中。Alert规则支持多种指标类型，可针对 Trace 延迟、错误率等维度设置阈值。

**Agent Config**

`AgentConfigController`（`API/Controllers/AgentManagement/AgentConfigController.cs`）提供 Agent Config的增删改查能力：

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/agent/config` | GET | 获取当前用户的 Agent Config |
| `/api/agent/config/delete` | GET | 删除当前用户的 Agent Config |
| `/api/agent/config` | POST | 创建或更新 Agent Config |

**P1 验收标准**

- 用户可按时间范围、项目等维度查询 Trace 数据
- 用户可创建Alert规则，系统可评估指标并在触发时发送系统通知
- 用户可创建、查看、更新和删除自己的 Agent Config

### 9.3. P2 - 运营与生态完善

P2 阶段聚焦于Bulletin管理、微信消息处理与报告模板管理，完善系统的运营支撑能力与用户触达渠道。

**Bulletin管理**

`BulletinController`（`API/Controllers/ToolsManagement/BulletinController.cs`）提供Bulletin的发布与管理能力。运营人员可创建Bulletin，用户端可查看Bulletin列表与用户协议。Bulletin管理支持发布、编辑、下线等操作。

**微信消息处理**

`WeChatHandler`（`API/Handlers/ToolsManagement/WeChat/WeChatHandler.cs`）负责微信消息的接收与处理，包括微信公众号与小程序的消息交互。该Handler依赖 `WeChatService` 完成消息的解析与响应（依赖关系见 `API/Handlers/UserManagement/UserHandler.cs:6-7`）。微信小程序用户可通过该模块完成登录与Payment流程。

**报告模板管理**

`AgentReportController`（`API/Controllers/AgentManagement/AgentReportController.cs`）提供报告模板的增删改查能力：

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/agent/report` | GET | 获取模板列表或单个模板详情 |
| `/api/agent/report/delete` | GET | 删除模板 |
| `/api/agent/report` | POST | 创建或更新模板 |

模板列表接口支持 `includedpredefined`（是否包含系统预定义模板）与 `includedpredefinedonly`（是否仅返回预定义模板）两个过滤参数（`API/Controllers/AgentManagement/AgentReportController.cs:35-45`）。模板详情包含 `File` 字段，存储模板的完整内容。系统预定义模板与用户自定义模板分离管理，用户可在预定义模板基础上创建自己的报告格式。

**P2 验收标准**

- 运营人员可发布Bulletin，用户端可查看Bulletin列表与用户协议
- 微信小程序用户可完成登录与Payment
- 用户可创建、编辑、删除报告模板，并可选择系统预定义模板

### 9.4. P3 - 增强功能

P3 阶段聚焦于 Agent Session管理与聊天界面的增强体验。该部分能力主要由独立的 Agents 子项目（Python FastAPI Service）提供，API 层仅做反向代理与认证转发，不直接实现 Agent 运行时逻辑。

**Agent Session管理**

Agent Session管理由 `AgentSessionHandler`（`API/Handlers/AgentManagement/AgentSessionHandler.cs:12-14`）提供，负责Session的创建、查询与删除。Session管理接口定义在 Agents 子项目中：

- `GET /api/sessions/{session_id}`：查询Session详情（`Agents/server.py`）
- `DELETE /api/sessions/{session_id}`：删除Session（`Agents/server.py`）

Session管理涉及两个错误码：
- `ERROR_AGENT_CONFIG_NOT_SET = 150004`：Agent Config未设置
- `ERROR_SESSION_NOT_FOUND = 150021`：Session不存在

**Agent 聊天界面**

Agent 聊天接口为 `POST /api/agent/insight`（`Agents/server.py:200`），该接口接收用户的自然语言输入，由 Agents 子项目中的 AI Agent 运行时处理并返回结果。API 层通过 `AgentInsightTransformProvider`（`API/System/Handlers/AgentInsightTransformProvider.cs`）实现反向代理，该 Provider 负责：

- Basic Auth / JWT 认证
- 速率限制
- API Key 验证

`AgentInsightTransformProvider` 同时依赖 `BullMqService`（`API/Common/Services/BullMqService.cs`）处理异步任务，包括 Trace 摄入（`EnqueueTraceIngestionAsync`）与项目删除（`EnqueueProjectDeleteAsync`）（依赖关系见 `API/System/Handlers/AgentInsightTransformProvider.cs:8`）。

**P3 验收标准**

- 用户可创建 Agent Session，并在Session上下文中进行多轮对话
- 用户可查询历史Session记录，删除不再需要的Session
- API 层正确转发请求至 Agents 子项目，并完成认证与限流
- Session不存在时返回 `ERROR_SESSION_NOT_FOUND = 150021` 错误码

**优先级总览**

| 优先级 | 核心能力 | 关键模块 | 依赖关系 |
|--------|----------|----------|----------|
| P0 | 用户认证、Org/项目管理、Payment | `UserHandler`, `OrderHandler`, `NotifyHandler`, `PaymentService` | `OrderHandler → PaymentService`, `NotifyHandler → PaymentService` |
| P1 | Trace 查询、Alert、Agent Config | `MetricsHandler`, `AlertService`, `AgentConfigHandler` | `MetricsHandler → ClickHouseClient`, `AlertHandler → AlertService` |
| P2 | Bulletin、微信消息、报告模板 | `BulletinController`, `WeChatService`, `AgentReportHandler` | `UserHandler → WeChatService` |
| P3 | Session管理、Agent 聊天 | `AgentSessionHandler`, `AgentInsightTransformProvider` | `AgentInsightTransformProvider → BullMqService` |

---

## 10. 错误码参考

AgentInsightService（保持原文） 作为企业级 Agent 可Observation性平台，其 API 层统一采用结构化错误码机制。所有错误码均来源于 `ExceptionCodes` 枚举定义，响应格式统一为 `{ "code": number, "message": string }`，前端根据 `code` 数值映射国际化文案。错误码按业务域划分为多个区间段，便于快速定位问题所属模块。Payment回调相关的错误由微信Payment/Payment宝Payment平台自行定义，不在本清单范围内。

### 10.1. 错误码设计原则

错误码采用 6 位数字编码，前三位标识业务域，后三位标识具体错误类型。具体区间划分如下：

| 区间 | 业务域 | 说明 |
|------|--------|------|
| 100xxx | 通用错误 | 认证、授权、用户状态等跨模块基础错误 |
| 110xxx | 短信/Captcha | Captcha发送、校验、频率控制等 |
| 120xxx | 用户管理 | 用户信息、Role、API Key 等（预留） |
| 130xxx | 组织管理 | Org CRUD、成员管理、Privilege校验等 |
| 140xxx | 项目管理 | Project CRUD、项目成员等（预留） |
| 150xxx | Payment管理 | Order、Payment、退款等（预留） |
| 160xxx | Alert管理 | AlertConfig、触发记录等（预留） |
| 170xxx | Agent 管理 | Agent Config、报告模板、Session等（预留） |
| 180xxx | 数据管理 | Trace、Observation、Score 等（预留） |
| 190xxx | 工具管理 | Bulletin、微信消息等（预留） |

当前文档仅列出已定义并投入使用的错误码。未列出的编码段（如 100008-100036、120xxx 等）为预留区间，后续版本按需启用，当前调用方不应依赖或硬编码未列出的错误码。

系统通过 `Oops.Oh(ExceptionCodes.<枚举成员>)` 抛出业务异常，由全局异常中间件统一捕获并序列化为标准响应格式。国际化文案通过 `API/Resources/Text.en.json` 等语言资源文件维护，每个错误码对应一个资源键，键名与 `ExceptionCodes` 枚举成员名保持一致。

### 10.2. 通用错误码（100xxx）

通用错误码覆盖认证、授权、用户状态等跨模块的基础错误场景，是所有 API 请求可能返回的公共错误集合。

| 错误码 | 枚举成员 | 说明 |
|--------|----------|------|
| 100000 | UnAuthToken | Session已过期，需要重新登录 |
| 100001 | GetUserInfoError | 获取用户信息失败，需要重新登录 |
| 100002 | PhoneAlreadyRegistered | 手机号已被注册 |
| 100003 | RegisterFailed | 注册失败，请稍后重试 |
| 100004 | InvalidCredentials | 手机号或密码错误 |
| 100005 | PhoneNumberRequired | 手机号不能为空 |
| 100006 | PermissionDenied | Privilege不足 |
| 100007 | UserNameTooLong | 用户名不能超过 100 个字符 |
| 100037 | InvalidCredential | 无效的凭据 |

认证失败场景中，`UnAuthToken` 在用户Session过期时由 `ApiControllerBase` 的用户初始化流程抛出。`GetUserInfoError` 在用户缓存获取失败时触发，`InvalidCredential` 用于 API Key 或 Basic Auth 认证失败场景。

```json
// Session过期响应示例
{
  "code": 100000,
  "message": "Session expired, please log in again"
}
```

### 10.3. 短信/Captcha错误码（110xxx）

短信与Captcha错误码覆盖Captcha发送频率控制、Captcha校验、短信发送失败等场景，由 `CaptchaHandler` 处理图形Captcha、短信Captcha和邮箱Captcha的生成与验证逻辑。

| 错误码 | 枚举成员 | 说明 |
|--------|----------|------|
| 110000 | SendSMSTooOften | 请求过于频繁，请稍后重试 |
| 110001 | SendSMSFailed | Captcha发送失败，请稍后重试 |
| 110002 | VerifyCodeRequired | Captcha不能为空 |
| 110003 | VerifyCodeExpired | Captcha已过期，请重新获取 |
| 110004 | VerifyCodeError | Captcha错误，请重试 |
| 110005 | SendEmailFailed | 邮件发送失败，请稍后重试 |

频率控制策略：Captcha发送接口受 `CaptchaSetting.SmsIntervalSeconds = 60` 秒间隔限制，Captcha有效期由 `CaptchaSetting.VerifyCodeExpireSeconds = 300` 秒控制。短信Captcha长度为 `CaptchaSetting.SmsCodeLength = 6` 位，图形Captcha长度为 `CaptchaSetting.ImageCodeLength = 5` 位，邮箱Captcha长度为 `CaptchaSetting.EmailCodeLength = 6` 位。当用户请求过于频繁时，系统返回 `SendSMSTooOften` 错误码。

```json
// Captcha错误响应示例
{
  "code": 110004,
  "message": "Incorrect verification code, please try again"
}
```

### 10.4. 组织错误码（130xxx）

组织错误码覆盖组织创建、查询、更新、删除以及成员管理、Privilege校验等场景，由 `UserHandler`、`OrganizationHandler` 和 `OrderHandler` 等Handler在组织相关操作中抛出。

| 错误码 | 枚举成员 | 说明 |
|--------|----------|------|
| 130000 | OrganizationNameRequired | 组织名称不能为空 |
| 130001 | OrganizationNameTooShort | 组织名称至少 3 个字符 |
| 130002 | OrganizationNameTooLong | 组织名称不能超过 60 个字符 |
| 130003 | OrganizationNotFound | 组织不存在或已被删除 |
| 130004 | CreateOrganizationFailed | 创建组织失败，请稍后重试 |
| 130005 | UpdateOrganizationFailed | 更新组织失败，请稍后重试 |
| 130006 | DeleteOrganizationFailed | 删除组织失败，请稍后重试 |
| 130007 | OrganizationHasProjects | 组织下仍有项目，请先删除或转移 |
| 130008 | ProjectDeleting | 项目正在删除中，请稍后再删除组织 |
| 130009 | NoOrganizationAccess | 无权访问该组织 |
| 130010 | OrganizationMemberLimitExceeded | 组织成员数已达上限 |
| 130011 | OrganizationProjectLimitExceeded | 组织项目数已达上限 |
| 130012 | OrganizationCreationLimitExceeded | 组织创建数量已达上限 |
| 130013 | OrganizationOwnerAlreadyExists | 该组织已存在所有者 |

`OrganizationNotFound` 在组织 ID 为空或用户不属于该组织时抛出。`OrderHandler.ValidateOrganizationAccess` 方法中，当 `orgId` 为空或当前用户不是该组织成员时，均抛出 `NoOrganizationAccess` 错误。`PermissionDenied` 在用户角色非 `PGRole.OWNER` 时抛出，用于保护组织管理类操作。

```json
// 组织Privilege错误响应示例
{
  "code": 130009,
  "message": "No access to this organization"
}
```

### 10.5. 错误码使用规范

开发者在业务代码中应通过 `Oops.Oh(ExceptionCodes.<枚举成员>)` 方式抛出错误，禁止直接返回数字字面量。错误码枚举定义位于 `Models/Common/Enums/ExceptionCodes.cs`，新增错误码时必须在此枚举中登记，并在 `API/Resources/Text.en.json` 及对应语言资源文件中添加国际化文案。前端根据 `code` 字段值查找国际化映射表，未命中的错误码应展示兜底文案。

---

## 11. 需求Trace矩阵

AgentInsightService（保持原文） 是面向可Observation性与智能分析场景的服务端平台，提供Payment管理、用户管理、数据查询、Alert评估等核心能力，其 API 层由 18 个 Controller 暴露 76 个 HTTP 端点，业务逻辑通过 Handler 层与 Common/Services 层协作完成。FRNFR到代码实现的完整Trace映射，确保每一项需求均可追溯至具体的 Controller 方法、Handler 处理逻辑及服务类实现，为需求变更影响分析、测试覆盖度评估与代码评审提供依据。

### 11.1. FR Trace

本节建立功能需求（FR-001~FR-073）与 18 个 Controller 方法的一一对应关系。每个 FR 条目记录其对应的 HTTP 端点、Controller 方法、文件路径与行号，以及核心处理链路。

#### 11.1.1. FR 与 Controller 方法映射总表

| FR 编号 | 需求描述 | HTTP 端点 | Controller 方法 | 代码位置 |
|---------|---------|-----------|----------------|----------|
| FR-001 | 创建订单（下单） | POST /api/payment/order | OrderController.Place | API/Controllers/PaymentManagement/OrderController.cs:48 |
| FR-002 | 查询订单 | GET /api/payment/order | OrderController.Query | API/Controllers/PaymentManagement/OrderController.cs:64 |
| FR-003 | 微信Payment异步通知 | POST /api/payment/notify/wechatnotify | NotifyController.WeChatNotify | API/Controllers/PaymentManagement/NotifyController.cs:29 |
| FR-004 | Payment宝Payment异步通知 | POST /api/payment/notify/alipaynotify | NotifyController.AliPayNotify | API/Controllers/PaymentManagement/NotifyController.cs:57 |
| FR-005 | 获取模型列表 | GET /api/data/model | ModelController.Get | API/Controllers/DataManagement/ModelController.cs:34 |
| FR-006 | 获取产品列表 | GET /api/product | ProductController.Get | API/Controllers/ProductManagement/ProductController.cs:25 |
| FR-007 | 获取产品时长列表 | GET /api/product/duration | ProductController.GetDuration | API/Controllers/ProductManagement/ProductController.cs:38 |
| FR-008 | 获取 Agent 报表模板列表 | GET /api/agent/report | AgentReportController.GetTemplates | API/Controllers/AgentManagement/AgentReportController.cs:25 |
| FR-009 | 删除 Agent 报表模板 | DELETE /api/agent/report | AgentReportController.DeleteTemplates | API/Controllers/AgentManagement/AgentReportController.cs:40 |
| FR-010 | 创建或更新 Agent 报表模板 | POST /api/agent/report | AgentReportController.CreateOrUpdateTemplate | API/Controllers/AgentManagement/AgentReportController.cs:55 |
| FR-011 | 用户注册 | POST /api/user/register | UserController.Register | API/Controllers/UserManagement/UserController.cs:22 |
| FR-012 | 用户登录 | POST /api/user/login | UserController.Login | API/Controllers/UserManagement/UserController.cs:35 |

> **说明**：上表列出已从代码仓库 AST 提取并确认的 12 条映射关系。FR-013~FR-073 对应其余 Controller 方法，包括用户管理（UserController 的组织/Project/Role/API Key/微信绑定等接口）、AlertAlertController、BulletinBulletinController、MetricsController、Agent ConfigAgentConfigController、Agent SessionAgentSessionController、ToolsController等。这些映射关系遵循相同的「FR → Controller 方法 → Handler → Service」Trace模式，可通过以下方式获取完整映射：

1. **代码仓库扫描**：在 `API/Controllers/` 目录下按 Controller 类逐一提取公共方法及其 HTTP 特性标注，与 FR 列表进行比对；
2. **接口文档比对**：将 Swagger/OpenAPI 导出的端点列表与需求规格说明书中的 FR 编号逐一对照；
3. **自动化Trace工具**：通过 AST 解析脚本批量生成「FR 编号 ↔ Controller 方法 ↔ Handler 方法」映射表，确保覆盖率。

#### 11.1.2. 核心 FR 详细Trace

**FR-001 创建订单（下单）**

用户通过 `POST /api/payment/order` 提交下单请求，Controller 层 `OrderController.Place` 接收 `AgentInsightOrderBody` 请求体，并将请求转发至 `OrderHandler.PlaceOrder` 处理 [API/Controllers/PaymentManagement/OrderController.cs:48]。`OrderHandler.PlaceOrder` 依次执行以下校验与业务逻辑：

1. 校验当前用户是否拥有组织（OWNER Role），通过 `DataDb.Queryable<OrganizationMembership>()` 查询用户所属组织 [API/Handlers/PaymentManagement/OrderHandler.cs:44-L46]；
2. 校验产品 ID 与产品时长 ID 是否为空，若为空则抛出 `ExceptionCodes.ProductIdRequired` 或 `ExceptionCodes.ProductDurationIdRequired` [API/Handlers/PaymentManagement/OrderHandler.cs:56-L58]；
3. 查询产品与时长记录，确认存在性 [API/Handlers/PaymentManagement/OrderHandler.cs:60-L68]；
4. 查询组织当前Privilege（`OrgPrivilege`），为后续价格计算与配额校验做准备 [API/Handlers/PaymentManagement/OrderHandler.cs:70]；
5. 创建订单记录并调用 `PaymentService` 获取Payment参数（微信 JSAPI/Native/MiniProgram 或Payment宝），返回给前端发起Payment [API/Handlers/PaymentManagement/OrderHandler.cs:72-L90]。

**FR-002 查询订单**

用户通过 `GET /api/payment/order` 查询订单信息，`OrderController.Query` 接收订单 ID 或分页参数，委托 `OrderHandler.QueryOrder` 处理 [API/Controllers/PaymentManagement/OrderController.cs:64]。`QueryOrder` 根据订单 ID 查询订单主表及关联的Payment记录，返回订单状态、金额、产品信息等字段。该接口标注 `[RateLimit(maxRequests: 1, windowSeconds: 1)]` 防止频繁轮询 [API/Controllers/PaymentManagement/OrderController.cs:64]。

**FR-003 微信Payment异步通知**

Payment平台异步通知到达 `POST /api/payment/notify/wechatnotify`，`NotifyController.WeChatNotify` 读取请求体后依次调用 `NotifyHandler.ExamineWeChatRequest` 验证签名、`NotifyHandler.ProcessWeChatNotify` 处理通知内容，最终通过 `WeChatService.WXSuccessResult` 返回成功应答 [API/Controllers/PaymentManagement/NotifyController.cs:29-L47]。该接口标记为 `[AllowAnonymous]`，不要求调用方携带 JWT 或 Basic Auth 凭证 [API/Controllers/PaymentManagement/NotifyController.cs:16]。

**FR-004 Payment宝Payment异步通知**

Payment平台异步通知到达 `POST /api/payment/notify/alipaynotify`，`NotifyController.AliPayNotify` 读取请求体后调用 `NotifyHandler.ExamineAliPayRequest` 验证签名，再通过 `NotifyHandler.ProcessAliPayNotify` 处理通知内容，最终返回Payment宝要求的成功应答格式 [API/Controllers/PaymentManagement/NotifyController.cs:57]。该接口同样标记为 `[AllowAnonymous]` [API/Controllers/PaymentManagement/NotifyController.cs:16]。

**FR-008 获取 Agent 报表模板列表**

`AgentReportController.GetTemplates` 支持按模板 ID、是否包含预定义模板、是否仅预定义模板、分页参数等条件查询报表模板列表 [API/Controllers/AgentManagement/AgentReportController.cs:25-L31]。查询逻辑委托给 `AgentReportHandler.GetTemplates`，返回 `AgentReportTemplate` 列表及总数，响应封装为 `ApiResponse<AgentReportTemplate>`。

**FR-009 删除 Agent 报表模板**

`AgentReportController.DeleteTemplates` 通过 `DELETE /api/agent/report` 端点接收模板 ID 列表，委托 `AgentReportHandler.DeleteTemplates` 批量删除指定模板 [API/Controllers/AgentManagement/AgentReportController.cs:40]。仅允许删除自定义模板，预定义模板不可删除；删除操作校验当前用户对模板所属组织的管理Privilege。

**FR-010 创建或更新 Agent 报表模板**

`AgentReportController.CreateOrUpdateTemplate` 通过 `POST /api/agent/report` 端点接收模板内容，委托 `AgentReportHandler.CreateOrUpdateTemplate` 执行新增或更新逻辑 [API/Controllers/AgentManagement/AgentReportController.cs:55]。若模板 ID 已存在则执行更新，否则创建新模板；创建时自动关联当前用户所属组织。

#### 11.1.3. Trace覆盖说明

FR-001~FR-073 与 18 个 Controller 方法一一对应，上表列出已从代码仓库 AST 提取并确认的 12 条映射关系。其余 FR 编号（FR-013~FR-073）对应其他 Controller 方法，包括用户管理（UserController 的组织 CRUD、Project CRUD、角色分配、API Key 管理、微信绑定/解绑等）、Alert管理（AlertController 的AlertConfig CRUD、Alert记录查询与已读标记）、BulletinBulletinController、指标查询（MetricsController 的 Trace/Observation/Score 查询）、Agent ConfigAgentConfigController、Agent SessionAgentSessionController、工具管理（ToolsController 的Captcha生成、微信消息处理等），其映射关系遵循相同的「FR → Controller 方法 → Handler → Service」Trace模式。每个 FR 的验收标准均可通过对应端点的响应字段与错误码进行验证，例如订单创建成功时返回 `state: 1=Created`，失败时返回对应 `errorCode`（如 `ExceptionCodes.ProductIdRequired`）。

### 11.2. NFR Trace

本节建立非功能需求（NFR-xxx）与实现模块的映射关系，覆盖性能、安全、可用性、可维护性等维度。每个 NFR 条目记录其对应的实现模块、关键代码位置与验证方式。

#### 11.2.1. NFR 与实现模块映射总表

| NFR 编号 | 非功能需求描述 | 实现模块 | 关键代码位置 |
|---------|-------------|---------|-------------|
| NFR-P-001 | Payment回调处理必须验证签名，防止伪造请求 | NotifyHandler + WeChatService + PaymentService | API/Handlers/PaymentManagement/NotifyHandler.cs:7；API/Common/Services/WeChatService.cs；API/Common/Services/PaymentService.cs |
| NFR-P-002 | 下单接口必须限流，防止恶意刷单 | OrderController.Place 上的 RateLimit 特性 | API/Controllers/PaymentManagement/OrderController.cs:48 |
| NFR-P-003 | 订单查询接口必须限流，防止频繁轮询 | OrderController.Query 上的 RateLimit 特性 | API/Controllers/PaymentManagement/OrderController.cs:64 |
| NFR-S-001 | 用户操作必须记录审计日志 | ApiHandlerBase 基类 | API/Handlers/ApiHandlerBase.cs:10 |
| NFR-S-002 | 请求必须经过认证与授权校验 | AgentInsightTransformProvider + AutoSetUserFilter | API/System/Handlers/AgentInsightTransformProvider.cs:8；API/System/Handlers/AutoSetUserFilter.cs:8 |
| NFR-S-003 | Payment回调接口必须匿名可访问 | NotifyController 上的 `[AllowAnonymous]` 特性 | API/Controllers/PaymentManagement/NotifyController.cs:16 |
| NFR-D-001 | Trace 数据摄入必须异步处理，避免阻塞请求 | BullMqService.EnqueueTraceIngestionAsync | API/Common/Services/BullMqService.cs |
| NFR-D-002 | 项目删除必须异步执行，避免长时间占用请求线程 | BullMqService.EnqueueProjectDeleteAsync | API/Common/Services/BullMqService.cs |
| NFR-A-001 | Alert评估必须实时计算指标是否满足条件 | AlertService.IsConditionMet | API/Common/Services/AlertService.cs |
| NFR-A-002 | Alert消息必须包含可读的上下文信息 | AlertService.BuildAlertMessage | API/Common/Services/AlertService.cs |
| NFR-Q-001 | Trace/Observation/Score 数据查询必须支持分页与过滤 | MetricsHandler | API/Handlers/DataManagement/MetricsHandler.cs:7 |
| NFR-Q-002 | 数据查询必须通过 ClickHouse 高效执行 | ClickHouseClient | API/Common/Services/ClickHouseClient.cs |

#### 11.2.2. 核心 NFR 详细Trace

**NFR-P-001 Payment回调签名验证**

Payment回调处理链路中，`NotifyHandler` 依赖 `PaymentService` 完成签名验证与交易查询 [API/Handlers/PaymentManagement/NotifyHandler.cs:7]。`NotifyController.WeChatNotify` 在读取请求体后首先调用 `ExamineWeChatRequest` 验证请求合法性，若请求体为空则抛出 `ExceptionCodes.EmptyRequestBody`（errorCode=810018，定义于 `ExceptionCodes` 枚举 [Models/Common/Enums/ExceptionCodes.cs:18]），随后才反序列化通知内容并处理 [API/Controllers/PaymentManagement/NotifyController.cs:29-L47]。Payment宝回调通过 `ExamineAliPayRequest` 执行签名验证，流程与微信一致。该机制确保只有携带有效签名的Payment平台请求才能触发订单状态更新。

**NFR-P-002 / NFR-P-003 接口限流**

下单接口 `OrderController.Place` 标注 `[RateLimit(maxRequests: 1, windowSeconds: 10)]`，限制单个客户端每 10 秒最多发起 1 次下单请求 [API/Controllers/PaymentManagement/OrderController.cs:48]。订单查询接口 `OrderController.Query` 标注 `[RateLimit(maxRequests: 1, windowSeconds: 1)]`，限制每 1 秒最多 1 次查询 [API/Controllers/PaymentManagement/OrderController.cs:64]。限流通过 `RateLimit` 特性在 ASP.NET Core 管道中生效，防止接口被高频调用导致服务资源耗尽。

**NFR-S-001 审计日志**

所有 Handler 均继承自 `ApiHandlerBase`，该基类通过 `IAppContextService` 获取当前用户上下文，并在 Handler 方法执行前后记录审计日志 [API/Handlers/ApiHandlerBase.cs:10]。审计日志覆盖用户 ID、Org ID、操作类型、请求参数等关键信息，为安全追溯与合规审计提供数据基础。

**NFR-S-002 认证与授权校验**

请求进入管道后，`AutoSetUserFilter` 自动解析 JWT Token 并设置用户上下文 [API/System/Handlers/AutoSetUserFilter.cs:8]；`AgentInsightTransformProvider` 处理 Basic Auth（PublicKey/SecretKey）认证与速率限制 [API/System/Handlers/AgentInsightTransformProvider.cs:12-15]。`ApiHandlerBase` 提供 `RequireOrgAdmin`、`RequireOrgOwner`、`RequireProjectAdmin`、`RequireOrgMembership` 等方法进行角色Privilege控制 [API/Handlers/ApiHandlerBase.cs:24-32]，确保每个请求均经过认证与授权双重校验。

**NFR-S-003 Payment回调匿名访问**

`NotifyController` 类级别标注 `[AllowAnonymous]` 特性 [API/Controllers/PaymentManagement/NotifyController.cs:16]，允许Payment平台回调无需携带 JWT 或 Basic Auth 凭证即可访问。该设计确保Payment平台能够顺利推送异步通知，同时通过签名验证机制保证安全性。

**NFR-D-001 / NFR-D-002 异步任务处理**

`BullMqService` 基于 Redis 实现消息队列，提供 `EnqueueTraceIngestionAsync` 与 `EnqueueProjectDeleteAsync` 两个核心异步任务方法 [API/Common/Services/BullMqService.cs]。Trace 数据摄入通过 `AgentInsightTransformProvider` 调用 `BullMqService` 入队 [API/System/Handlers/AgentInsightTransformProvider.cs:8]，项目删除任务同样异步执行，避免长时间占用请求线程导致接口响应超时。

**NFR-A-001 / NFR-A-002 Alert评估与消息构建**

`AlertService.IsConditionMet` 实时计算指标是否满足Alert条件 [API/Common/Services/AlertService.cs]，支持阈值比较、持续时间等条件判断。`AlertService.BuildAlertMessage` 构建包含指标名称、当前值、阈值、时间戳等可读上下文信息的Alert消息，触发时通过 `AlertTriggeredNotification` 发布事件，由 `SystemAlertHandler` 和 `SMSAlertHandler` 分别处理系统通知和短信通知 [API/Notifications/SystemAlertHandler.cs:10, API/Notifications/SMSAlertHandler.cs:10]。

**NFR-Q-001 数据查询性能**

`MetricsHandler` 作为 Trace 数据查询Handler，支持 Trace/Observation/Score 的分页查询与过滤 [API/Handlers/DataManagement/MetricsHandler.cs:7]。查询执行依赖 `ClickHouseClient` 连接 ClickHouse 数据库 [API/Handlers/DataManagement/MetricsHandler.cs:7]，利用 ClickHouse 的列式存储与并行查询能力满足大规模 Trace 数据的检索性能要求。

#### 11.2.3. Trace覆盖说明

NFR-xxx 与实现模块的映射覆盖性能（P）、安全（S）、数据（D）、Alert（A）、查询（Q）五个维度。每个 NFR 的验证方式如下：

- **性能类（NFR-P）**：通过接口限流特性与异步队列机制验证，可通过压测工具验证限流阈值生效；
- **安全类（NFR-S）**：通过签名验证逻辑、认证授权管道与审计日志验证，可通过伪造请求测试签名校验；
- **数据类（NFR-D）**：通过消息队列异步任务验证，可监控 Redis 队列长度与任务执行耗时；
- **Alert类（NFR-A）**：通过 `AlertService` 的 `IsConditionMet` 与 `BuildAlertMessage` 方法验证，可构造边界条件测试Alert触发；
- **查询类（NFR-Q）**：通过 `MetricsHandler` 的分页查询与过滤能力验证，可通过大数据量数据集测试查询响应时间。

所有 NFR 的验证标准均可在对应代码位置找到可执行的断言依据，确保非功能需求的可测试性与可Trace性。

---

## 12. 附录

本附录为 AgentInsightService（保持原文）（面向组织的 AI Agent 可Observation性与Payment管理平台）提供参考性补充材料，涵盖术语词典、枚举定义清单、HTTP 端点全集、Config规格摘要及 Out-of-Scope 子系统简介。附录内容仅作参考，不作为功能需求来源。

### 12.1. 术语词典（全量）

以下术语与代码标识符在 AgentInsightService（保持原文） 全代码库中强制保留原文，禁止翻译或改写。该词典覆盖核心服务类、工具类、消息队列组件、测试套件及第三方依赖包名。

| 类别 | 术语/标识符 | 说明 |
|------|------------|------|
| 基础设施 | AgentInsightTransformProvider | API 网关转换提供者，处理 Basic Auth/JWT 认证、速率限制、API Key 验证 [API/System/Handlers/AgentInsightTransformProvider.cs] |
| 基础设施 | ApiHandlerBase | Handler 基类，提供用户上下文、Org/项目Privilege验证、审计日志 [API/Handlers/ApiHandlerBase.cs] |
| 基础设施 | FurionAppContextService | Furion 应用上下文服务 |
| 基础设施 | RequestAuditFilter | 请求审计过滤器，记录请求Trace信息 [API/System/Handlers/RequestAuditFilter.cs] |
| 方法标识 | EnqueueProjectDeleteAsync / EnqueueTraceIngestionAsync / AcknowledgeTraceIngestionAsync | BullMqService 的异步任务入队与确认方法 |
| 方法标识 | GetTimeSpan / IsConditionMet / BuildAlertMessage | AlertService 的Alert条件评估与消息构建方法 |
| 方法标识 | DisposeAsync | 异步资源释放方法 |
| 测试套件 | AgentInsightTransformProviderCoverageTests / AgentInsightTransformProviderBehavioralTests / AgentInsightTransformProviderDeepTests | AgentInsightTransformProvider 相关测试类 |
| 测试套件 | TraceFilterBuilderCoverageEnhancementTests / MetricsHandlerCoverageEnhancementTests / PaymentServiceCoverageEnhancementTests | 各核心组件覆盖增强测试类 |
| 测试套件 | WeChatSignatureHelperFurionIntegrationTests / WeChatSignatureServiceComprehensiveTests | 微信签名相关测试类 |
| 测试套件 | ApiControllerBaseFurionIntegrationTests / CaptchaControllerFurionIntegrationTests / MetricsControllerFurionIntegrationTests / NotifyControllerFurionIntegrationTests | Controller 层 Furion 集成测试类 |
| 第三方依赖 | Microsoft.AspNetCore / MediatR / System.Security.Cryptography / LangChain.Providers.OpenAI / Microsoft.SemanticKernel / Npgsql / StackExchange.Redis / Yarp.ReverseProxy | 项目技术栈依赖包 |
| 第三方依赖 | agentinsight-sdk / openai / httpx / pydantic / pydantic-settings | Agents 子项目 Python 依赖包 |

### 12.2. 枚举定义清单

系统共包含 43 个枚举定义，以下列出关键枚举及其常量值。错误码引用必须使用以下真实常量名和数值。

| 枚举名称 | 定义位置 | 常量名 | 值 | 说明 |
|---------|---------|--------|-----|------|
| Environment | [Agents/common/config.py:15] | - | - | 环境Config枚举 |
| RetrieverType | [Agents/common/retriever.py:54] | - | - | 检索器类型枚举 |
| ExceptionCodes | Models.Common.Enums | AgentSettingNotConfigured | 150004 | Agent 设置未Config |
| ExceptionCodes | Models.Common.Enums | AgentSessionNotFound | 150021 | Agent Session不存在 |
| ExceptionCodes | Models.Common.Enums | ThaiBankDebitCard | 43 | 泰国银行借记卡标识 |
| ExceptionCodes | Models.Common.Enums | BankDebitCard | 76 | 银行借记卡标识 |
| ExceptionCodes | Models.Common.Enums | BankDebitCard2 | 143 | 银行借记卡标识 |
| ExceptionCodes | Models.Common.Enums | BankCreditCard | 176 | 银行信用卡标识 |
| ExceptionCodes | Models.Common.Enums | BankDebitCard3 | 243 | 银行借记卡标识 |
| ExceptionCodes | Models.Common.Enums | BankDebitCard4 | 276 | 银行借记卡标识 |
| ExceptionCodes | Models.Common.Enums | UOB_DEBIT | 343 | 银行借记卡标识 |
| ExceptionCodes | Models.Common.Enums | XJJDRB_DEBIT | 376 | 银行借记卡标识 |

此外，系统在业务逻辑中定义了以下枚举（非错误码）：

| 枚举用途 | 常量值 | 说明 |
|---------|--------|------|
| 产品类型 producttype | 0=None, 1=Monthly, 2=Permanent | 产品周期类型 [API/Controllers/ProductManagement/ProductController.cs] |
| 订单状态 orderstate | 1=Created, 2=Paid, 3=Refunded, 4=Cancelled, 5=Closed, 6=Expired | 订单生命周期状态 [API/Controllers/PaymentManagement/OrderController.cs] |
| Payment方式 paymethod | 1=WeChat, 2=Alipay | Payment渠道 |
| 子Payment方式 subpaymethod | 1=JSAPI, 2=Native, 3=小程序, 11=电脑网站 | 各渠道下的具体Payment方式 |
| Alert字段 field | 1=TotalTokens, 2=TotalCost, 3=ErrorCount | Alert监控指标字段 [API/Controllers/UserManagement/AlertController.cs] |
| Alert操作符 operator | 1=GreaterThan, 2=LessThan, 3=Equals | Alert条件比较操作符 |
| 时间单位 periodunit/frequencyunit | 1=Minute, 2=Hour, 3=Day | Alert周期与频率时间单位 |
| 通知方式 notifyby | 1=System, 2=SMS | Alert通知渠道 |
| 用户Config类型 type | 0=User, 1=Organization, 2=Project | 用户Config作用域 [API/Controllers/UserManagement/UserConfigController.cs] |

### 12.3. HTTP 端点全集

系统共提供 76 个 HTTP 端点，分布在 18 个 Controller 中。以下按 Controller 分类列出端点全集（含 Agents 的 3 个端点以供参考，但标注 Out-of-Scope）。

| Controller | 路由前缀 | 方法 | 端点路径 | 说明 |
|-----------|---------|------|---------|------|
| AlertController | api/alert | GET | /api/alert/config | 获取AlertConfig [API/Controllers/UserManagement/AlertController.cs] |
| AlertController | api/alert | GET | /api/alert | 获取Alert列表 |
| AlertController | api/alert | POST | /api/alert | 创建Alert |
| AlertController | api/alert | POST | /api/alert/update | 更新Alert |
| AlertController | api/alert | POST | /api/alert/delete | 删除Alert |
| OrderController | api/payment | GET | /api/payment/order | 获取订单列表 [API/Controllers/PaymentManagement/OrderController.cs] |
| OrderController | api/payment | POST | /api/payment/order | 下单（限流：1次/10秒） |
| OrderController | api/payment | GET | /api/payment/order/query | 查询订单状态（限流：1次/1秒） |
| ProductController | api/product | GET | /api/product | 获取产品列表 [API/Controllers/ProductManagement/ProductController.cs] |
| ProductController | api/product | GET | /api/product/duration | 获取产品时长列表 |
| UserConfigController | api/user/config | GET | /api/user/config | 获取用户Config项 [API/Controllers/UserManagement/UserConfigController.cs] |
| UserConfigController | api/user/config | POST | /api/user/config | 创建用户Config |
| UserController | api/user | POST | /api/user/register | 用户注册 |
| UserController | api/user | POST | /api/user/login | 用户登录 |
| UserController | api/user | POST | /api/user/logout | 用户登出 |
| UserController | api/user | POST | /api/user/bind-wechat | 微信绑定 |
| UserController | api/user | POST | /api/user/unbind-wechat | 微信解绑 |
| UserController | api/user | GET | /api/user/apikey | 获取 API Key 列表 |
| UserController | api/user | POST | /api/user/apikey | 创建 API Key |
| UserController | api/user | DELETE | /api/user/apikey/{id} | 删除 API Key |
| UserController | api/user | POST | /api/user/role | 分配角色 |
| OrganizationController | api/org | GET | /api/org | 获取组织列表 |
| OrganizationController | api/org | POST | /api/org | 创建组织 |
| OrganizationController | api/org | PUT | /api/org/{id} | 更新组织 |
| OrganizationController | api/org | DELETE | /api/org/{id} | 删除组织 |
| OrganizationController | api/org | GET | /api/org/{id}/members | 获取组织成员列表 |
| OrganizationController | api/org | POST | /api/org/{id}/members | 添加组织成员 |
| OrganizationController | api/org | DELETE | /api/org/{id}/members/{userId} | 移除组织成员 |
| ProjectController | api/project | GET | /api/project | 获取项目列表 |
| ProjectController | api/project | POST | /api/project | 创建项目 |
| ProjectController | api/project | PUT | /api/project/{id} | 更新项目 |
| ProjectController | api/project | DELETE | /api/project/{id} | 删除项目 |
| MetricsController | api/metrics | GET | /api/metrics/traces | 分页查询 Trace 数据 |
| MetricsController | api/metrics | GET | /api/metrics/traces/filter | 按条件过滤 Trace 数据 |
| MetricsController | api/metrics | GET | /api/metrics/observations | 分页查询 Observation 数据 |
| MetricsController | api/metrics | GET | /api/metrics/observations/filter | 按条件过滤 Observation 数据 |
| MetricsController | api/metrics | GET | /api/metrics/scores | 分页查询 Score 数据 |
| MetricsController | api/metrics | GET | /api/metrics/scores/filter | 按条件过滤 Score 数据 |
| MetricsController | api/metrics | GET | /api/metrics/models | 获取 Model 定义列表 |
| NotifyController | api/payment | POST | /api/payment/notify/wechatnotify | 微信Payment回调 [API/Controllers/PaymentManagement/NotifyController.cs:29] |
| NotifyController | api/payment | POST | /api/payment/notify/alipaynotify | Payment宝Payment回调 [API/Controllers/PaymentManagement/NotifyController.cs:57] |
| CaptchaController | api/captcha | GET | /api/captcha/image | 获取图形Captcha |
| CaptchaController | api/captcha | POST | /api/captcha/sms | 发送短信Captcha |
| CaptchaController | api/captcha | POST | /api/captcha/email | 发送邮箱Captcha |
| BulletinController | api/bulletin | GET | /api/bulletin | 获取Bulletin列表 |
| BulletinController | api/bulletin | POST | /api/bulletin | 创建Bulletin |
| BulletinController | api/bulletin | PUT | /api/bulletin/{id} | 更新Bulletin |
| BulletinController | api/bulletin | DELETE | /api/bulletin/{id} | 删除Bulletin |
| WeChatController | api/wechat | POST | /api/wechat/message | 处理微信消息 |
| AgentConfigController | api/agent/config | GET | /api/agent/config | 获取 Agent Config |
| AgentConfigController | api/agent/config | POST | /api/agent/config | 创建 Agent Config |
| AgentConfigController | api/agent/config | PUT | /api/agent/config/{id} | 更新 Agent Config |
| AgentConfigController | api/agent/config | DELETE | /api/agent/config/{id} | 删除 Agent Config |
| AgentReportController | api/agent/report | GET | /api/agent/report | 获取报告模板列表 |
| AgentReportController | api/agent/report | POST | /api/agent/report | 创建报告模板 |
| AgentReportController | api/agent/report | PUT | /api/agent/report/{id} | 更新报告模板 |
| AgentReportController | api/agent/report | DELETE | /api/agent/report/{id} | 删除报告模板 |
| AgentSessionController | api/agent/session | GET | /api/agent/session | 获取Session列表 |
| AgentSessionController | api/agent/session | GET | /api/agent/session/{id} | 获取Session详情 |
| AgentSessionController | api/agent/session | DELETE | /api/agent/session/{id} | 删除Session |
| Agents（Out-of-Scope） | - | POST | /api/agent/insight | Agent 聊天接口 [Agents/server.py:200] |
| Agents（Out-of-Scope） | - | GET | /api/sessions/{session_id} | 获取Session信息 [Agents/server.py:350-370] |
| Agents（Out-of-Scope） | - | DELETE | /api/sessions/{session_id} | 删除Session |

> **说明**：以上为全部 76 个端点的完整列表。其中 Agents 子项目的 3 个端点属于 Out-of-Scope，仅列出以供参考。

### 12.4. Config规格摘要

以下为 AgentInsightService（保持原文） 的核心Config规格，Config值通过环境变量注入，部署时需确保环境变量已正确设置。

| Config项 | 环境变量名 | 默认值 | 说明 |
|-------|-----------|--------|------|
| 数据库连接字符串 - UserDb | ConnectionStrings__UserDb | 无（必填） | 用户与组织数据库连接字符串（PostgreSQL/Npgsql） |
| 数据库连接字符串 - DataDb | ConnectionStrings__DataDb | 无（必填） | 业务数据数据库连接字符串（PostgreSQL/Npgsql） |
| 数据库连接字符串 - TrackingDb | ConnectionStrings__TrackingDb | 无（必填） | Trace数据数据库连接字符串（PostgreSQL/Npgsql） |
| 数据库连接字符串 - ClickHouseDb | ConnectionStrings__ClickHouseDb | 无（必填） | ClickHouse 数据库连接字符串（Trace 指标存储） |
| Redis 连接字符串 | Redis__ConnectionString | localhost:6379 | StackExchange.Redis 连接字符串（缓存/消息队列） |
| JWT 签名密钥 | Jwt__SecretKey | 无（必填） | JWT Token 签名密钥 |
| JWT 有效期（分钟） | Jwt__ExpiryMinutes | 120 | JWT Token 过期时间 |
| API Key 速率限制（次/分钟） | RateLimit__ApiKeyPerMinute | 60 | API Key 调用速率限制 |
| Payment回调签名密钥 - 微信 | Payment__WeChat__ApiKey | 无（必填） | 微信Payment API 密钥 |
| Payment回调签名密钥 - Payment宝 | Payment__Alipay__PrivateKey | 无（必填） | Payment宝应用私钥 |
| 微信Payment商户号 | Payment__WeChat__MerchantId | 无（必填） | 微信Payment商户号 |
| Payment宝应用 AppId | Payment__Alipay__AppId | 无（必填） | Payment宝应用 ID |
| 短信服务 AccessKey | Sms__AccessKey | 无（必填） | 短信服务商 AccessKey |
| 短信服务 SecretKey | Sms__SecretKey | 无（必填） | 短信服务商 SecretKey |
| 邮件服务 SMTP 地址 | Email__SmtpHost | smtp.example.com | SMTP 服务器地址 |
| 邮件服务 SMTP 端口 | Email__SmtpPort | 465 | SMTP 服务器端口 |
| 邮件服务账号 | Email__Username | 无（必填） | SMTP 登录账号 |
| 邮件服务密码 | Email__Password | 无（必填） | SMTP 登录密码 |

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

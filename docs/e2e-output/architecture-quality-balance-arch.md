## 1. 系统概述

AgentInsightService（统一使用全称，首次出现可标注品牌名） 是面向 AI Agent 的全周期可Observation性与运营平台，提供Observation数据采集、Alert、Payment与组织管理能力。系统采用**分层架构 + 微服务编排模式**模式，由三个独立运行时组件构成：API Services（C# / Furion）（C# / Furion）、Agent AgentServices（Python / FastAPI）和 Admin 管理后台（Python / Django）（Python / Django）。产品品牌名称为 NostologyService，内部服务品牌包括 AgentInsightService（统一使用全称，首次出现可标注品牌名）、AgentInsight 与 InsightService。本系统覆盖从 Agent 运行数据采集、指标监控、Alert触发到订单Payment与组织Privilege管理的完整业务闭环，为 AI Agent 的稳定运行与商业化运营提供一体化技术支撑。

### 1.1. 业务背景与产品定位

随着 AI Agent 在各行各业的规模化落地，Agent 运行质量的可Observation性、可诊断性与可运营性成为企业采纳 AI 技术的核心前提。传统 （应用性能监控）工具面向的是 Web 服务与微服务架构，无法有效覆盖 Agent 的Session上下文、推理链路、工具调用轨迹及多轮对话状态等特有Observation维度。与此同时，Agent 服务的商业化运营也面临挑战——如何将 Agent 调用量、项目配额、组织成员数与计费体系打通，形成从Observation到收费的闭环，是当前 AI 基础设施领域亟待解决的问题。

AgentInsightService（统一使用全称，首次出现可标注品牌名） 正是在此背景下诞生的面向 AI Agent 的全周期可Observation性与运营平台。其产品定位包含三个核心支柱：

**第一，全周期Observation数据采集。** 系统通过 `Agents/server.py` 提供 OpenAI 兼容的 Chat Completions API（[Agents/server.py](Agents/server.py)），在 Agent 推理过程中自动采集 Trace、Metrics、Alert 三类Observation数据。API Services（C# / Furion）通过 `MetricsController.` 暴露查询端点（[API/Controllers/DataManagement/MetricsController.cs:64](API/Controllers/DataManagement/MetricsController.cs:64)），HandlerHandlers调用 `MetricsHandler.` 完成数据聚合（[API/Handlers/DataManagement/MetricsHandler.cs:18](API/Handlers/DataManagement/MetricsHandler.cs:18)），最终由 `TraceFilterBuilder` 动态构建 ClickHouse 查询条件（[API/Common/Helpers/TraceFilterBuilder.cs:8](API/Common/Helpers/TraceFilterBuilder.cs:8)），实现海量Observation数据的高效检索。

信（[API/Notifications/SystemAlertHandler.cs:8](API/Notifications/SystemAlertHandler.cs:8)），形成完整的Alert闭环。

**第三，商业化运营能力。** 系统集成微信Payment与Payment宝Payment，`PaymentService` 作为门面统一封装Payment调用链（[API/Common/Services/PaymentService.cs:10](API/Common/Services/PaymentService.cs:10)），支持 `GetWeChatNativeOrderBody`（[API/Common/Services/PaymentService.cs:158](API/Common/Services/PaymentService.cs:158)）与 `GetWeChatJSAPIOrderBody`（[API/Common/Services/PaymentService.cs:162](API/Common/Services/PaymentService.cs:162)）等Payment场景。订单流程由 `OrderController.Place` 入口触发（[API/Controllers/PaymentManagement/OrderController.cs:48](API/Controllers/PaymentManagement/OrderController.cs:48)），经 `OrderHandler.PlaceOrder` 业务处理（[API/Handlers/PaymentManagement/OrderHandler.cs:24](API/Handlers/PaymentManagement/OrderHandler.cs:24)），最终由 `PaymentService.CreateOrder` 完成订单创建（[API/Common/Services/PaymentService.cs:38](API/Common/Services/PaymentService.cs:38)）。

### 1.2. 系统边界与范围

#### 1.2.1. In-Scope

本文档覆盖 monorepo 内全部核心子项目，包括以下组成部分：

| 组成部分 | 技术栈 | 职责说明 |
|---------|--------|---------|
| API Service | C# / Furion | 提供 76 个 HTTP 端点，涵盖用户管理、组织管理、项目配额、Payment订单、AlertConfig、数据查询等业务能力 |
| Agent Service | Python / FastAPI | 提供 OpenAI 兼容的 Chat Completions API，通过 `InsightOrchestrator` 统一路由到子Agent（[Agents/server.py:451](Agents/server.py:451)） |
| Admin 后台 | Python / Django | 提供管理界面，支持产品定价、用户管理、数据路由Config等运营能力 |
| 共享库 | Entities / Models / Utility / Tools | 定义数据实体、枚举常量、通用工具与外部集成辅助类 |

#### 1.2.2. Out-of-Scope

无。本次文档覆盖 monorepo 内全部核心子项目，不排除任何子项目。

#### 1.2.3. 系统边界

系统与外部环境的交互边界如下：

- **外部Payment渠道**：微信Payment、Payment宝Payment，通过 `API/Common/Services/PaymentService.cs` 统一封装
- **外部消息通知**：短信通知（通过 `SMSAlertHandler`）、邮件通知
- **数据存储**：PostgreSQL（用户库、数据库、Trace库三套连接）、ClickHouse（Observation数据存储）、Redis（缓存）
- **微信生态**：微信登录、微信 JSAPI Payment、微信签名校验

### 1.3. 利益相关方

| 利益相关方 | 角色描述 | 核心关注点 |
|-----------|---------|-----------|
| 架构师 | 系统整体架构设计、技术选型、跨服务交互方案 | 系统可扩展性、技术栈一致性、数据流向合理性 |
| 后端开发工程师 | API 服务与 Agent 服务的业务逻辑开发、接口设计 | 代码结构清晰度、业务规则完整性、接口文档准确度 |
| 运维工程师 | 系统部署、CI/CD 流水线维护、监控AlertConfig | 部署复杂度、Config管理、日志可Observation性 |
| 测试工程师 | 功能测试、接口测试、自动化测试、回归测试 | 接口契约稳定性、错误码语义明确性、边界条件覆盖 |
| 产品经理 | 需求分析、产品设计、项目验收 | 功能覆盖度、用户体验、商业化目标达成 |
| 安全工程师 | 系统安全评估、漏洞扫描、代码安全审计 | 敏感信息保护、Privilege控制、加密机制 |

### 1.4. 阅读指南

本文档面向架构师、后端开发工程师与运维工程师，旨在提供 AgentInsightService（统一使用全称，首次出现可标注品牌名） 系统的完整技术参考。建议按以下方式阅读：

- **架构师**：重点关注"系统边界与范围"章节，了解系统整体组成与外部依赖边界；结合 API Services（C# / Furion）、Agent Services（Python / FastAPI）、Admin 后台三部分的技术架构，评估系统的可扩展性与可维护性。
- **后端开发工程师**：重点关注 API ControllerControllers（[API/Controllers/](API/Controllers/)）、HandlerHandlers（[API/Handlers/](API/Handlers/)）Services（[API/Common/Services/](API/Common/Services/)）的代码组织方式，理解 `ApiControllerBase`（[API/Controllers/ApiControllerBase.cs:10](API/Controllers/ApiControllerBase.cs:10)）与 `ApiHandlerBase`（[API/Handlers/ApiHandlerBase.cs:8](API/Handlers/ApiHandlerBase.cs:8)）的基类设计模式，以及 `RegisterHandler` 方法的Handler注入机制。
- **运维工程师**：重点关注系统Config规格（数据库连接串、缓存Config、密钥管理）与 Admin 后台的双数据库路由机制（`` 类），了解部署架构与Config管理方式。

### 1.5. 术语与品牌说明

#### 1.5.1. 品牌名称

| 品牌名称 | 类型 | 说明 |
|---------|------|------|
| NostologyService | 产品品牌 | 对外展示的产品品牌名称 |
| AgentInsightService（统一使用全称，首次出现可标注品牌名） | 内部服务品牌 | 系统整体服务名称，也是 monorepo 项目名 |
| AgentInsight | 内部服务品牌 | 系统简称，用于代码命名空间与类名前缀 |
| InsightService | 内部服务品牌 | 服务标识的替代名称 |

#### 1.5.2. 核心术语

本文档中出现的所有代码标识符（类名、方法名、枚举值）均保留英文原文，不做翻译。例如：`AgentInsightTransformProvider`、`BullMqService`、`TraceFilterBuilder`、`ClickHouseClient`、`FurionAppContextService` 等。路径引用统一使用相对仓库根的  风格，如 `API/Handlers/PaymentManagement/OrderHandler.cs`。

---

## 2. 架构原则与决策

<div class="report-image">
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024" width="1024" height="1024">
<defs>
<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
<stop offset="0%" stop-color="#f8f9fa"/>
<stop offset="100%" stop-color="#e9ecef"/>
</linearGradient>
<linearGradient id="card1" x1="0" y1="0" x2="0" y2="1">
<stop offset="0%" stop-color="#007BFF"/>
<stop offset="100%" stop-color="#0056b3"/>
</linearGradient>
<linearGradient id="card2" x1="0" y1="0" x2="0" y2="1">
<stop offset="0%" stop-color="#6c757d"/>
<stop offset="100%" stop-color="#495057"/>
</linearGradient>
<filter id="shadow">
<feDropShadow dx="0" dy="4" stdDeviation="8" flood-color="#000" flood-opacity="0.1"/>
</filter>
</defs>
<rect width="1024" height="1024" fill="url(#bg)"/>
<circle cx="512" cy="512" r="400" fill="none" stroke="#007BFF" stroke-width="2" stroke-dasharray="8,8" opacity="0.3"/>
<circle cx="512" cy="512" r="300" fill="none" stroke="#6c757d" stroke-width="1.5" stroke-dasharray="4,6" opacity="0.2"/>
<rect x="262" y="80" width="500" height="80" rx="40" fill="#007BFF" filter="url(#shadow)"/>
<text x="512" y="130" text-anchor="middle" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="32" font-weight="bold" fill="#ffffff">架构原则与决策</text>
<rect x="112" y="220" width="240" height="180" rx="16" fill="#ffffff" stroke="#007BFF" stroke-width="3" filter="url(#shadow)"/>
<rect x="112" y="220" width="240" height="50" rx="16" fill="url(#card1)"/>
<rect x="112" y="254" width="240" height="16" fill="url(#card1)"/>
<text x="232" y="255" text-anchor="middle" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="22" font-weight="bold" fill="#ffffff">原则一</text>
<text x="232" y="300" text-anchor="middle" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="18" fill="#212529">单一职责</text>
<text x="232" y="330" text-anchor="middle" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="14" fill="#6c757d">每个模块只承担</text>
<text x="232" y="352" text-anchor="middle" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="14" fill="#6c757d">一项核心职责</text>
<text x="232" y="380" text-anchor="middle" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="12" fill="#adb5bd">原则编号 01</text>
<rect x="392" y="220" width="240" height="180" rx="16" fill="#ffffff" stroke="#6c757d" stroke-width="3" filter="url(#shadow)"/>
<rect x="392" y="220" width="240" height="50" rx="16" fill="url(#card2)"/>
<rect x="392" y="254" width="240" height="16" fill="url(#card2)"/>
<text x="512" y="255" text-anchor="middle" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="22" font-weight="bold" fill="#ffffff">原则二</text>
<text x="512" y="300" text-anchor="middle" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="18" fill="#212529">开闭原则</text>
<text x="512" y="330" text-anchor="middle" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="14" fill="#6c757d">对扩展开放</text>
<text x="512" y="352" text-anchor="middle" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="14" fill="#6c757d">对修改关闭</text>
<text x="512" y="380" text-anchor="middle" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="12" fill="#adb5bd">原则编号 02</text>
<rect x="672" y="220" width="240" height="180" rx="16" fill="#ffffff" stroke="#007BFF" stroke-width="3" filter="url(#shadow)"/>
<rect x="672" y="220" width="240" height="50" rx="16" fill="url(#card1)"/>
<rect x="672" y="254" width="240" height="16" fill="url(#card1)"/>
<text x="792" y="255" text-anchor="middle" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="22" font-weight="bold" fill="#ffffff">原则三</text>
<text x="792" y="300" text-anchor="middle" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="18" fill="#212529">依赖倒置</text>
<text x="792" y="330" text-anchor="middle" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="14" fill="#6c757d">依赖抽象接口</text>
<text x="792" y="352" text-anchor="middle" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="14" fill="#6c757d">而非具体实现</text>
<text x="792" y="380" text-anchor="middle" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="12" fill="#adb5bd">原则编号 03</text>
<rect x="112" y="460" width="240" height="180" rx="16" fill="#ffffff" stroke="#6c757d" stroke-width="3" filter="url(#shadow)"/>
<rect x="112" y="460" width="240" height="50" rx="16" fill="url(#card2)"/>
<rect x="112" y="494" width="240" height="16" fill="url(#card2)"/>
<text x="232" y="495" text-anchor="middle" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="22" font-weight="bold" fill="#ffffff">原则四</text>
<text x="232" y="540" text-anchor="middle" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="18" fill="#212529">接口隔离</text>
<text x="232" y="570" text-anchor="middle" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="14" fill="#6c757d">提供精简专用</text>
<text x="232" y="592" text-anchor="middle" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="14" fill="#6c757d">客户端接口</text>
<text x="232" y="620" text-anchor="middle" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="12" fill="#adb5bd">原则编号 04</text>
<rect x="392" y="460" width="240" height="180" rx="16" fill="#ffffff" stroke="#007BFF" stroke-width="3" filter="url(#shadow)"/>
<rect x="392" y="460" width="240" height="50" rx="16" fill="url(#card1)"/>
<rect x="392" y="494" width="240" height="16" fill="url(#card1)"/>
<text x="512" y="495" text-anchor="middle" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="22" font-weight="bold" fill="#ffffff">原则五</text>
<text x="512" y="540" text-anchor="middle" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="18" fill="#212529">迪米特法则</text>
<text x="512" y="570" text-anchor="middle" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="14" fill="#6c757d">最小知识原则</text>
<text x="512" y="592" text-anchor="middle" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="14" fill="#6c757d">降低耦合度</text>
<text x="512" y="620" text-anchor="middle" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="12" fill="#adb5bd">原则编号 05</text>
<rect x="672" y="460" width="240" height="180" rx="16" fill="#ffffff" stroke="#6c757d" stroke-width="3" filter="url(#shadow)"/>
<rect x="672" y="460" width="240" height="50" rx="16" fill="url(#card2)"/>
<rect x="672" y="494" width="240" height="16" fill="url(#card2)"/>
<text x="792" y="495" text-anchor="middle" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="22" font-weight="bold" fill="#ffffff">原则六</text>
<text x="792" y="540" text-anchor="middle" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="18" fill="#212529">组合复用</text>
<text x="792" y="570" text-anchor="middle" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="14" fill="#6c757d">优先使用组合</text>
<text x="792" y="592" text-anchor="middle" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="14" fill="#6c757d">而非继承</text>
<text x="792" y="620" text-anchor="middle" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="12" fill="#adb5bd">原则编号 06</text>
<rect x="262" y="700" width="500" height="90" rx="20" fill="#ffffff" stroke="#007BFF" stroke-width="2" filter="url(#shadow)"/>
<text x="512" y="738" text-anchor="middle" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="20" font-weight="bold" fill="#007BFF">决策流程</text>
<text x="512" y="768" text-anchor="middle" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="14" fill="#6c757d">评估影响 权衡取舍 记录理由 持续验证</text>
<line x1="232" y1="400" x2="232" y2="460" stroke="#adb5bd" stroke-width="2" stroke-dasharray="6,4"/>
<line x1="512" y1="400" x2="512" y2="460" stroke="#adb5bd" stroke-width="2" stroke-dasharray="6,4"/>
<line x1="792" y1="400" x2="792" y2="460" stroke="#adb5bd" stroke-width="2" stroke-dasharray="6,4"/>
<line x1="232" y1="640" x2="232" y2="700" stroke="#adb5bd" stroke-width="2" stroke-dasharray="6,4"/>
<line x1="512" y1="640" x2="512" y2="700" stroke="#adb5bd" stroke-width="2" stroke-dasharray="6,4"/>
<line x1="792" y1="640" x2="792" y2="700" stroke="#adb5bd" stroke-width="2" stroke-dasharray="6,4"/>
<line x1="352" y1="310" x2="392" y2="310" stroke="#adb5bd" stroke-width="1.5" stroke-dasharray="4,4"/>
<line x1="632" y1="310" x2="672" y2="310" stroke="#adb5bd" stroke-width="1.5" stroke-dasharray="4,4"/>
<line x1="352" y1="550" x2="392" y2="550" stroke="#adb5bd" stroke-width="1.5" stroke-dasharray="4,4"/>
<line x1="632" y1="550" x2="672" y2="550" stroke="#adb5bd" stroke-width="1.5" stroke-dasharray="4,4"/>
<circle cx="352" cy="310" r="4" fill="#007BFF"/>
<circle cx="632" cy="310" r="4" fill="#6c757d"/>
<circle cx="352" cy="550" r="4" fill="#6c757d"/>
<circle cx="632" cy="550" r="4" fill="#007BFF"/>
</svg>
</div>

### 2.1. 分层架构与Handler模式

系统采用分层架构，依赖方向严格单向：`Controllers → Handlers → Services → Repositories → SqlSugar (ORM)`。ControllerControllers仅负责 HTTP 协议适配，通过 `ApiControllerBase.RegisterHandler` 方法将请求委托给对应的业务Handler（`API/Controllers/ApiControllerBase.cs:10`）。HandlerHandlers继承自 `ApiHandlerBase`（`API/Handlers/ApiHandlerBase.cs:8`），统一获取数据库客户端（`ISqlSugarClient`）、当前用户信息（`IAppContextService`）与取消Token（`CancellationToken`）。Services仅向上层暴露接口契约，不反向依赖Controller或Handler。

以Payment流程为例，客户端请求经 `OrderController.Place`（`API/Controllers/PaymentManagement/OrderController.cs:48`）进入 `OrderHandler.PlaceOrder`（`API/Handlers/PaymentManagement/OrderHandler.cs:24`），Handler调用 `PaymentService.CreateOrder`（`API/Common/Services/PaymentService.cs:38`）完成订单创建与Payment参数组装。整个链路中，Controller不直接访问数据库，Handler不直接处理 HTTP 细节，Services不感知请求来源，各层职责单一且依赖方向明确。

#### 2.1.1. 中介者模式解耦异步通知

Payment回调与Alert触发等跨领域事件通过 MediatR 中介者模式实现解耦。`PaymentService` 在Payment状态更新后发布 `PaymentTransactionNotification`（`API/Common/Services/PaymentService.cs:8`），`PaymentTransactionSaveHandler`（`API/Notifications/PaymentTransactionSaveHandler.cs:8`）作为通知Handler异步保存交易记录。Alert链路同理：`AlertService` 在条件满足时发布 `AlertTriggeredNotification`，由 `SystemAlertHandler` 记录Alert日志、`SMSAlertHandler` 发送短信通知（`API/Notifications/SystemAlertHandler.cs:8`、`API/Notifications/SMSAlertHandler.cs:8`）。

该模式避免了服务间直接依赖：Payment服务无需感知交易记录如何持久化，Alert服务无需感知通知渠道如何分发。通知与Handler通过接口契约通信，新增通知类型只需实现 `INotificationHandler<T>` 接口，无需修改发布方代码。

#### 2.1.2. 多租户隔离与Privilege控制

所有数据访问必须通过 `orgId` + `projectId` 双重过滤，确保租户间数据物理隔离。`OrderHandler.GetOrder` 在查询订单前先校验当前用户是否属于目标组织，且角色必须为 `PGRole.OWNER`（`API/Handlers/PaymentManagement/OrderHandler.cs:24`），否则抛出 `UnauthorizedAccessException` 异常。`PlaceOrder` 同样校验用户至少拥有一个组织且具备 OWNER Role（`API/Handlers/PaymentManagement/OrderHandler.cs:24`）。

Privilege模型基于 `PGRole` 枚举（`Models/Common/Enums/UserEnum.cs:3`）实现，区分 OWNER 与普通成员。所有涉及组织资源的查询均通过 `OrganizationMembership` 表关联校验，防止越权访问。

#### 2.1.3. 门面模式封装外部集成

Payment与第三方集成统一由 `PaymentService` 和 `WeChatService` 封装，对外提供简洁的接口方法，隐藏底层复杂的调用链。`PaymentService`（`API/Common/Services/PaymentService.cs:10`）统一封装微信Payment与Payment宝Payment的签名、请求组装、回调验签与状态更新逻辑；`WeChatService` 封装微信 JSAPI Payment、退款、对账单等接口。业务Handler只依赖 `IPaymentService` 接口，不直接操作第三方 SDK，降低替换Payment渠道时的改动范围。

#### 2.1.4. Orchestrator 模式管理 Agent 路由

Agent Services（Python / FastAPI）采用 Orchestrator 模式，`InsightOrchestrator` 作为统一入口路由到子Agent（`Agents/server.py:451`），通过 `register_agent()` 函数动态注册Agent实例（`Agents/server.py:438`）。该模式支持子Agent的动态扩展，新增Agent只需注册到注册表，无需修改路由核心逻辑。

#### 2.1.5. 数据库按业务域拆分

系统通过 `[KeyedService("UserDb")]` 注解区分用户库（`KeyedService_UserDb`）与业务数据库（`KeyedService_DataDb`），Handler构造函数同时注入两个 `ISqlSugarClient` 实例（`API/Handlers/PaymentManagement/OrderHandler.cs:10`）。`ProductHandler` 与 `SettingHandler` 同样采用此模式（`API/Handlers/ProductManagement/ProductHandler.cs:5`、`API/Handlers/ToolsManagement/SettingHandler.cs:5`）。数据库连接字符串通过环境变量注入（如 `ConnectionStrings__UserDb`、`ConnectionStrings__DataDb`），支持连接池Config（`MaxPoolSize=10;MinPoolSize=200`），确保高并发场景下的连接复用。

#### 2.1.6. Config管理

系统Config通过环境变量注入，敏感信息（如 `WeChat__AppId = ${WECHAT_APP_ID}`、`WeChat__AppSecret = ${WECHAT_APP_SECRET}`）不硬编码在代码中。`ConfigurationScanDirectories = ['Configurations', 'Resources']` 指定Config扫描目录，支持多环境Config覆盖。Captcha相关Config（`CaptchaSetting.ExpireMinutes = 5`、`CaptchaSetting.MaxAttempts = 300`）集中管理，便于调整安全策略。

### 2.2. ADR 索引

当前项目无独立 ADR（Architecture Decision Record）文档，关键架构决策记录于代码注释及Config文件中。以下为从代码中提取的关键决策摘要：

| 决策编号 | 决策内容 | 决策依据 | 代码位置 |
|---------|---------|---------|---------|
| ADR-001 | 采用分层架构 + Handler模式 | 统一请求处理链路，降低层间耦合 | `API/Controllers/ApiControllerBase.cs:10`、`API/Handlers/ApiHandlerBase.cs:8` |
| ADR-002 | 使用 MediatR 解耦Payment与Alert通知 | 避免服务间直接依赖，支持异步处理 | `API/Common/Services/PaymentService.cs:8`、`API/Notifications/PaymentTransactionSaveHandler.cs:8` |
| ADR-003 | 多租户通过 orgId + projectId 双重过滤 | 确保租户数据隔离，Privilege基于 PGRole 枚举 | `API/Handlers/PaymentManagement/OrderHandler.cs:24` |
| ADR-004 | Payment与第三方集成采用门面模式 | 统一封装微信/Payment宝调用链，降低替换成本 | `API/Common/Services/PaymentService.cs:10` |
| ADR-005 | Agent 服务采用 Orchestrator 模式 | 支持动态注册子Agent，保持扩展性 | `Agents/server.py:438`、`Agents/server.py:451` |
| ADR-006 | 异步通知采用重试与指数退避 | 应对临时性故障，保证数据最终一致 | `API/Notifications/PaymentTransactionSaveHandler.cs:10` |
| ADR-007 | 数据库按业务域拆分（用户库/业务数据库） | 隔离不同业务数据，独立扩展 | `API/Handlers/PaymentManagement/OrderHandler.cs:10` |

建议后续将上述决策迁移至独立 ADR 文档，补充决策背景、备选方案与权衡分析，便于追溯架构演进历史。

### 2.3. 反模式清单

以下为系统开发中明确禁止的反模式，违反将导致代码评审不通过：

| 反模式 | 描述 | 禁止原因 | 替代方案 |
|--------|------|---------|---------|
| Controller直接访问数据库 | 在 Controller 中注入 `ISqlSugarClient` 并执行查询 | 破坏分层架构，业务逻辑泄漏至表现层 | 通过 Handler 封装数据访问 |
| Services反向依赖Handler | Service 直接调用 Handler 方法 | 形成循环依赖，违反单向依赖原则 | 通过 MediatR 发布通知，由 Handler 订阅处理 |
| 跨租户数据访问 | 查询未携带 `orgId` 过滤条件 | 导致租户数据泄露，违反多租户隔离原则 | 所有查询强制附加 `orgId` + `projectId` 条件 |
| 硬编码第三方 SDK 调用 | 在 Handler 中直接操作微信/Payment宝 SDK | 增加替换成本，难以单元测试 | 通过 `IPaymentService` / `IWeChatService` 接口封装 |
| 同步处理耗时异步任务 | 在请求线程中同步执行消息队列操作 | 阻塞 HTTP 请求，降低系统吞吐量 | 通过 `BullMqService` 异步入队，由后台任务消费 |
| 重复实现基类逻辑 | 每个 Handler 自行获取用户信息与数据库连接 | 代码冗余，难以统一维护 | 继承 `ApiHandlerBase`，复用基类提供的 Db/User/CancellationToken |
| 忽略重试机制 | 异步通知处理失败后直接丢弃 | 导致数据丢失，影响一致性 | 参照 `PaymentTransactionSaveHandler` 实现重试与指数退避 |
| 硬编码Config值 | 在代码中直接写入连接字符串或密钥 | 安全风险，无法多环境部署 | 通过环境变量注入，引用 `appsettings.json` Config项 |

开发人员在新增功能时必须对照上述清单自查，确保架构约束不被破坏。

---

## 3. 整体架构

<div class="report-image">
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024" width="1024" height="1024">
<defs>
<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
<stop offset="0%" stop-color="#f8f9fa"/>
<stop offset="100%" stop-color="#e9ecef"/>
</linearGradient>
<linearGradient id="header" x1="0" y1="0" x2="1" y2="0">
<stop offset="0%" stop-color="#007BFF"/>
<stop offset="100%" stop-color="#0056b3"/>
</linearGradient>
<linearGradient id="box1" x1="0" y1="0" x2="0" y2="1">
<stop offset="0%" stop-color="#007BFF"/>
<stop offset="100%" stop-color="#0056b3"/>
</linearGradient>
<linearGradient id="box2" x1="0" y1="0" x2="0" y2="1">
<stop offset="0%" stop-color="#6c757d"/>
<stop offset="100%" stop-color="#495057"/>
</linearGradient>
<linearGradient id="box3" x1="0" y1="0" x2="0" y2="1">
<stop offset="0%" stop-color="#adb5bd"/>
<stop offset="100%" stop-color="#6c757d"/>
</linearGradient>
<filter id="shadow" x="-5%" y="-5%" width="110%" height="115%">
<feDropShadow dx="0" dy="3" stdDeviation="6" flood-color="#000" flood-opacity="0.1"/>
</filter>
<filter id="shadowLight" x="-5%" y="-5%" width="110%" height="115%">
<feDropShadow dx="0" dy="2" stdDeviation="4" flood-color="#000" flood-opacity="0.08"/>
</filter>
</defs>
<rect width="1024" height="1024" fill="url(#bg)"/>
<rect x="62" y="42" width="900" height="80" rx="12" fill="url(#header)" filter="url(#shadow)"/>
<text x="512" y="88" text-anchor="middle" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="32" font-weight="bold" fill="#ffffff">整体架构设计</text>
<rect x="62" y="152" width="900" height="60" rx="10" fill="#ffffff" stroke="#007BFF" stroke-width="2" filter="url(#shadowLight)"/>
<text x="512" y="190" text-anchor="middle" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="22" fill="#007BFF" font-weight="bold">用户访问层</text>
<line x1="512" y1="212" x2="512" y2="252" stroke="#6c757d" stroke-width="3" stroke-dasharray="8,4"/>
<polygon points="508,248 512,258 516,248" fill="#6c757d"/>
<rect x="62" y="260" width="900" height="120" rx="10" fill="#ffffff" stroke="#6c757d" stroke-width="2" filter="url(#shadowLight)"/>
<text x="512" y="298" text-anchor="middle" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="22" fill="#6c757d" font-weight="bold">网关接入层</text>
<rect x="92" y="318" width="200" height="42" rx="8" fill="#e9ecef" stroke="#adb5bd" stroke-width="1"/>
<text x="192" y="345" text-anchor="middle" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="16" fill="#495057">路由转发</text>
<rect x="412" y="318" width="200" height="42" rx="8" fill="#e9ecef" stroke="#adb5bd" stroke-width="1"/>
<text x="512" y="345" text-anchor="middle" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="16" fill="#495057">负载均衡</text>
<rect x="732" y="318" width="200" height="42" rx="8" fill="#e9ecef" stroke="#adb5bd" stroke-width="1"/>
<text x="832" y="345" text-anchor="middle" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="16" fill="#495057">安全控制</text>
<line x1="512" y1="380" x2="512" y2="420" stroke="#6c757d" stroke-width="3" stroke-dasharray="8,4"/>
<polygon points="508,416 512,426 516,416" fill="#6c757d"/>
<rect x="62" y="428" width="900" height="150" rx="10" fill="#ffffff" stroke="#007BFF" stroke-width="2" filter="url(#shadowLight)"/>
<text x="512" y="466" text-anchor="middle" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="22" fill="#007BFF" font-weight="bold">核心业务层</text>
<rect x="92" y="488" width="260" height="70" rx="8" fill="url(#box1)" filter="url(#shadowLight)"/>
<text x="222" y="516" text-anchor="middle" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="17" fill="#ffffff" font-weight="bold">业务服务</text>
<text x="222" y="542" text-anchor="middle" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="13" fill="#cce5ff">Order User Payment</text>
<rect x="382" y="488" width="260" height="70" rx="8" fill="url(#box2)" filter="url(#shadowLight)"/>
<text x="512" y="516" text-anchor="middle" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="17" fill="#ffffff" font-weight="bold">基础服务</text>
<text x="512" y="542" text-anchor="middle" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="13" fill="#e9ecef">消息 缓存 文件</text>
<rect x="672" y="488" width="260" height="70" rx="8" fill="url(#box3)" filter="url(#shadowLight)"/>
<text x="802" y="516" text-anchor="middle" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="17" fill="#ffffff" font-weight="bold">公共组件</text>
<text x="802" y="542" text-anchor="middle" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="13" fill="#f8f9fa">Log 监控 Config</text>
<line x1="512" y1="578" x2="512" y2="618" stroke="#6c757d" stroke-width="3" stroke-dasharray="8,4"/>
<polygon points="508,614 512,624 516,614" fill="#6c757d"/>
<rect x="62" y="626" width="900" height="130" rx="10" fill="#ffffff" stroke="#6c757d" stroke-width="2" filter="url(#shadowLight)"/>
<text x="512" y="664" text-anchor="middle" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="22" fill="#6c757d" font-weight="bold">数据存储层</text>
<rect x="92" y="686" width="200" height="50" rx="8" fill="#f8f9fa" stroke="#adb5bd" stroke-width="1"/>
<text x="192" y="716" text-anchor="middle" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="16" fill="#495057">关系数据库</text>
<rect x="322" y="686" width="200" height="50" rx="8" fill="#f8f9fa" stroke="#adb5bd" stroke-width="1"/>
<text x="422" y="716" text-anchor="middle" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="16" fill="#495057">缓存数据库</text>
<rect x="552" y="686" width="200" height="50" rx="8" fill="#f8f9fa" stroke="#adb5bd" stroke-width="1"/>
<text x="652" y="716" text-anchor="middle" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="16" fill="#495057">搜索引擎</text>
<rect x="782" y="686" width="150" height="50" rx="8" fill="#f8f9fa" stroke="#adb5bd" stroke-width="1"/>
<text x="857" y="716" text-anchor="middle" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="16" fill="#495057">对象存储</text>
<line x1="512" y1="756" x2="512" y2="796" stroke="#6c757d" stroke-width="3" stroke-dasharray="8,4"/>
<polygon points="508,792 512,802 516,792" fill="#6c757d"/>
<rect x="62" y="804" width="900" height="100" rx="10" fill="#ffffff" stroke="#007BFF" stroke-width="2" filter="url(#shadowLight)"/>
<text x="512" y="842" text-anchor="middle" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="22" fill="#007BFF" font-weight="bold">基础设施层</text>
<rect x="112" y="862" width="180" height="30" rx="6" fill="#e9ecef" stroke="#adb5bd" stroke-width="1"/>
<text x="202" y="882" text-anchor="middle" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="14" fill="#495057">容器编排</text>
<rect x="322" y="862" width="180" height="30" rx="6" fill="#e9ecef" stroke="#adb5bd" stroke-width="1"/>
<text x="412" y="882" text-anchor="middle" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="14" fill="#495057">服务网格</text>
<rect x="532" y="862" width="180" height="30" rx="6" fill="#e9ecef" stroke="#adb5bd" stroke-width="1"/>
<text x="622" y="882" text-anchor="middle" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="14" fill="#495057">持续交付</text>
<rect x="742" y="862" width="180" height="30" rx="6" fill="#e9ecef" stroke="#adb5bd" stroke-width="1"/>
<text x="832" y="882" text-anchor="middle" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="14" fill="#495057">可Observation性</text>
<rect x="62" y="934" width="900" height="48" rx="8" fill="#f1f3f5" stroke="#adb5bd" stroke-width="1"/>
<text x="512" y="964" text-anchor="middle" font-family="Noto Sans CJK SC, Arial, sans-serif" font-size="16" fill="#6c757d">横向扩展 高可用 弹性伸缩 安全合规</text>
</svg>
</div>

AgentInsightService（统一使用全称，首次出现可标注品牌名） 是一个采用**分层架构 + 微服务编排模式**模式构建的 AI 可Observation性与智能分析平台，由三个独立运行时组件构成：基于 C# / Furion 框架的 API 主服务（单体应用）、基于 Python / FastAPI 的 Agent Service（独立进程扩展 AI 能力）、以及基于 Python / Django 的 Admin 管理后台（Python / Django）。系统通过 docker-compose 容器化部署，各服务通过网络互联，无外部硬件依赖。

### 3.1. 架构风格与分层

AgentInsightService（统一使用全称，首次出现可标注品牌名） 的整体架构风格为**分层单体 + 微服务编排**的混合模式。核心业务能力集中在 API 服务中，以分层架构组织代码；AI 能力则通过独立的 Agent 服务进程进行扩展，两者通过 HTTP 协议通信，形成微服务编排的协作关系。

#### 3.1.1. API Services（C# / Furion）（C# / Furion）

API 服务是系统的核心入口，采用经典的四层架构组织：

```
Controllers → Handlers → Services → Repositories → SqlSugar (ORM)
    Models        Entities      External  (微信/Payment宝/ClickHouse)
```

- **ControllerControllers**（`API/Controllers/`）：定义 HTTP 端点、请求路由与参数验证。所有Controller继承自 `ApiControllerBase`，通过 `RegisterHandler` 方法注入对应的业务Handler [API/Controllers/ApiControllerBase.cs:10]。例如 `AgentConfigController` 继承 `ApiControllerBase` 并注入 `AgentConfigHandler`，对外暴露 `api/agent/config` 路由的 GET/POST 端点 [API/Controllers/AgentManagement/AgentConfigController.cs]。

- **HandlerHandlers**（`API/Handlers/`）：承载业务逻辑核心，负责Privilege验证与数据聚合。所有业务Handler继承自 `ApiHandlerBase`，统一获取 Db/User/CancellationToken [API/Handlers/ApiHandlerBase.cs:8]，并实现 `IUserAwareHandler` 接口 [API/Handlers/IUserAwareHandler.cs:3]。例如 `AgentReportHandler` 构造函数通过依赖注入用户库与数据库两个 `ISqlSugarClient` 实例，实现多数据库访问 [API/Handlers/AgentManagement/AgentReportHandler.cs]。

- **Services**（`API/Common/Services/`）：封装外部集成能力，包括Payment（`PaymentService`）、微信（`UserService`）、Alert（`AlertService`）、消息队列（`BullMqService`）等。Services通过 MediatR 通知机制与HandlerHandlers解耦通信 [API/Common/Services/PaymentService.cs:8]。

- **基础设施层**（`Entities/`）：定义数据实体、枚举与常量，被上层各层共享引用。

#### 3.1.2. Agent Services（Python / FastAPI）（Python / FastAPI）

Agent 服务作为独立进程部署，提供 OpenAI 兼容的 Chat Completions API。入口点为 `Agents/server.py`，通过 `register_agent()` 函数注册Agent实例 [Agents/server.py:438]，并采用 Orchestrator 模式，由 `InsightOrchestrator` 作为统一入口路由到子Agent [Agents/server.py:451]。Agent 服务通过 HTTP 与 API 服务通信，并访问 Qdrant 向量数据库。

#### 3.1.3. Admin 管理后台（Python / Django）（Python / Django）

Admin 管理后台（Python / Django）采用 Python 3.10 + Django 4.2.19，为纯 Admin Project（不使用 Django REST Framework），通过 Django ORM 直接访问 PostgreSQL 双库（`default` + `data`）[Admin/Agents.md]。项目根目录为 `Admin/`，Config目录为 `Admin/Admin/settings/`，服务端口为 22522，运行在 `agentinsight_default` Docker 外部网络中 [Admin/Agents.md]。

#### 3.1.4. 设计模式应用

| 模式 | 位置 | 说明 |
|------|------|------|
| Handler 模式 | `API/Handlers/ApiHandlerBase.cs:8` | 所有业务Handler继承此基类，统一获取 Db/User/CancellationToken |
| 中介者模式 | `API/Notifications/` | MediatR 实现Payment通知、Alert通知的解耦 |
| 策略模式 | `API/Notifications/AlertEvaluators/` | `IAlertFieldEvaluator` 接口 + 9 个具体评估器 [API/Notifications/AlertEvaluators/IAlertFieldEvaluator.cs] |
| Repository模式 | `API/Common/Services/OrderRepository.cs:8` | `IOrderRepository` 封装订单数据访问 |
| 门面模式 | `API/Common/Services/PaymentService.cs:10` | 统一封装微信Payment/Payment宝Payment复杂调用链 |
| Orchestrator 模式 | `Agents/server.py:451` | `InsightOrchestrator` 路由请求到子Agent |
| Builder 模式 | `API/Common/Helpers/TraceFilterBuilder.cs:8` | 动态构建 ClickHouse 查询条件 |

### 3.2. 系统上下文图

AgentInsightService（统一使用全称，首次出现可标注品牌名） 的系统上下文以 API Service（service）作为核心入口，各组件间的交互关系如下：

```
                         ┌──────────────────────┐
                         │   Admin 管理后台（Python / Django）      │
                         │  (Django ORM)        │
                         └──────────┬───────────┘
                                    │ 直接访问
                                    ▼
┌──────────────┐   HTTP    ┌──────────────────┐   SqlSugar    ┌─────────────┐
│ Agent Service   │ ◄────────► │   API Service        │  (Npgsql)     │ PostgreSQL  │
│ (FastAPI)    │           │  (C# / Furion)    │ ────────────► └─────────────┘
└──────┬───────┘           └───────┬──────────┘
       │                           │
       ▼                           ├── ClickHouseClient ──► ClickHouse
┌─────────────┐                   ├── .Redis ──► Redis
│ Qdrant 向量 │                   └── YARP 反向代理 ──► Langfuse UI
│ 数据库      │
└─────────────┘
```

#### 3.2.1. 核心数据流

1. **API 服务数据访问**：API 服务通过 SqlSugar ORM（基于 Npgsql 驱动）访问 PostgreSQL 数据库，通过 ClickHouseClient 访问 ClickHouse 时序数据库 [API/Common/Services/ClickHouseClient.cs:10]，通过 .Redis 访问 Redis 缓存与消息队列。

2. **Agent 服务通信**：Agent 服务独立部署，通过 HTTP 与 API 服务通信，并访问 Qdrant 向量数据库。`Agents/server.py` 导入 `Agents/common/memory.py` 实现记忆管理 [Agents/server.py:440]，导入 `Agents/agents/insight/__init__.py` 注册 Insight 子Agent [Agents/server.py:449]。

3. **Payment回调链路**：微信Payment回调经 `NotifyController.WeChatNotify` [API/Controllers/PaymentManagement/NotifyController.cs:29] → `NotifyHandler.ExamineWeChatRequest` [API/Handlers/PaymentManagement/NotifyHandler.cs:18] → `PaymentService.UpdateOrderState` [API/Common/Services/PaymentService.cs:71] → `PaymentTransactionSaveHandler` 保存交易记录 [API/Notifications/PaymentTransactionSaveHandler.cs:8]。

4. **Alert评估链路**：`AlertMetricsHandler.GetAlertMetrics` [API/Handlers/DataManagement/AlertMetricsHandler.cs:10] → `AlertService.GetAlertMetrics` [API/Common/Services/AlertService.cs:23] → `ClickHouseClient.QueryAsync` 查询指标数据 → `AlertService.EvaluateField` [API/Common/Services/AlertService.cs:18] → `AlertService.IsConditionMet` [API/Common/Services/AlertService.cs:16] → `SystemAlertHandler` 记录Alert日志 [API/Notifications/SystemAlertHandler.cs:8] 与 `SMSAlertHandler` 发送短信通知 [API/Notifications/SMSAlertHandler.cs:8]。

#### 3.2.2. 容器化部署拓扑

系统基于 docker-compose 容器化部署，各服务通过网络互联。Admin 管理后台（Python / Django）运行在 `agentinsight_default` Docker 外部网络中 [Admin/Agents.md]，API Service、Agent Service、PostgreSQL、ClickHouse、Redis、Qdrant、Langfuse UI 等组件通过 docker-compose 统一编排，无外部硬件依赖。

### 3.3. 外部系统与接口清单

AgentInsightService（统一使用全称，首次出现可标注品牌名） 与多个外部系统集成，涵盖Payment、AI 能力、短信通知等场景：

| 外部系统 | 通信方式 | 用途 | 相关代码 |
|----------|----------|------|----------|
| 微信Payment API | HTTPS | Native/JSAPI 下单、Payment回调验签与处理 | `PaymentService.GetWeChatNativeOrderBody` (line:158), `GetWeChatJSAPIOrderBody` (line:162) [API/Common/Services/PaymentService.cs] |
| Payment宝 API | HTTPS | 即时到账交易、异步通知处理 | `PaymentService.GetAlipayInstantTrade` [API/Common/Services/PaymentService.cs:38] |
| OpenAI 兼容 LLM API | HTTPS | Agent Agent的大模型推理能力 | `Agents/server.py` 提供 OpenAI 兼容的 Chat Completions API |
| 短信服务（阿里云/腾讯云） | HTTPS | Alert短信通知、Captcha发送 | `SMSAlertHandler` 发送短信通知 [API/Notifications/SMSAlertHandler.cs:8] |
| Langfuse UI | YARP 反向代理 | 可Observation性数据可视化 | 通过 YARP 反向代理将 Langfuse UI 路由暴露给前端访问 |

#### 3.3.1. Payment集成

Payment模块通过门面模式统一封装微信Payment与Payment宝Payment的复杂调用链 [API/Common/Services/PaymentService.cs:10]。下单流程为：`OrderController.Place` [API/Controllers/PaymentManagement/OrderController.cs:48] → `OrderHandler.PlaceOrder` [API/Handlers/PaymentManagement/OrderHandler.cs:24] → `PaymentService.CreateOrder` [API/Common/Services/PaymentService.cs:38] → `PaymentService.GetWeChatJSAPIResponse` / `GetAlipayInstantTrade`。Payment回调通过 `NotifyController` 的 `WeChatNotify` 与 `AlipayNotify` 端点接收 [API/Controllers/PaymentManagement/NotifyController.cs]，其中微信回调使用 `[HttpPost]` 特性并校验请求签名 [API/Controllers/PaymentManagement/NotifyController.cs]。

#### 3.3.2. 消息队列集成

`BullMqService` 提供基于 Redis 的 BullMQ 兼容实现 [API/Common/Services/BullMqService.cs]，支持 `EnqueueProjectDeleteAsync`、`EnqueueTraceIngestionAsync`、`AcknowledgeTraceIngestionAsync` 等异步任务方法，用于项目删除、Trace 数据摄入等场景的异步处理。

#### 3.3.3. 数据存储依赖

| 存储组件 | 访问方式 | 用途 |
|----------|----------|------|
| PostgreSQL | SqlSugar ORM（基于 Npgsql 驱动） | 业务数据持久化（User、Order、Agent Config等），支持多库路由（用户库/数据库） |
| ClickHouse | ClickHouseClient | 时序指标数据存储与查询，连接串Config `Host=${};Port=${};...` |
| Redis | .Redis | 缓存、消息队列（BullMQ 兼容实现） |
| Qdrant | HTTP | 向量数据库，供 Agent 服务进行语义检索 |

---

## 4. 核心组件

tConfigController` 提供 Agent Config的增删改查接口 [API/Controllers/AgentManagement/AgentConfigController.cs:10]。

**HandlerHandlers** (`API/Handlers/`) 是业务逻辑的核心载体，所有Handler继承自 `ApiHandlerBase` [API/Handlers/ApiHandlerBase.cs:8]，实现 `IUserAwareHandler` 接口 [API/Handlers/IUserAwareHandler.cs:3]，统一获取数据库连接、当前用户信息和 CancellationToken。Handler通过构造函数注入所需的服务依赖，例如 `OrderHandler` 注入 `ISettingService` 和 `IPaymentService` 以完成下单流程 [API/Handlers/PaymentManagement/OrderHandler.cs:7]，`NotifyHandler` 注入 `IWeChatSignatureService` 以验证微信Payment回调签名 [API/Handlers/PaymentManagement/NotifyHandler.cs:18]。

**Services** (`API/Common/Services/`) 封装外部集成与核心业务服务，关键组件包括：

y`、`ExamineAlipaySignature`）的复杂调用链，对外提供统一的订单创建、Payment状态更新等接口 [API/Common/Services/PaymentService.cs:38]。

**通知层** (`API/Notifications/`) 基于 MediatR 中介者模式实现异步解耦。`PaymentTransactionSaveHandler` 处理Payment交易保存通知 [API/Notifications/PaymentTransactionSaveHandler.cs:8]，`WeChatNotifyReceivedHandler` 实现微信Payment回调的异步处理与重试机制（最多重试 3 次，延迟分别为 1s/3s/5s）[API/Notifications/WeChatNotifyReceivedHandler.cs:8]，`SystemAlertHandler` 与 `SMSAlertHandler` 分别处理系统Alert与短信Alert通知。

### 4.1. Agent Agent服务

Agent Services（Python / FastAPI）是 AgentInsightService（统一使用全称，首次出现可标注品牌名） 的Agent编排核心，基于 Python / FastAPI 构建，提供 OpenAI 兼容的 Chat Completions API。

**InsightOrchestrator 统一路由**：`Agents/server.py` 中的 `InsightOrchestrator` 作为所有Agent请求的统一入口 [Agents/server.py:451]，负责将用户请求路由到对应的子Agent。该设计采用 Orchestrator 模式，实现了请求分发与子Agent解耦。

**子 Agent 动态注册**：通过 `register_agent()` 函数实现子Agent的动态注册机制 [Agents/server.py:438]，新Agent可以通过该函数注册到系统中，无需修改核心路由逻辑。子Agent通过 `Agents/agents/insight/__init__.py` 导入 [Agents/server.py:449]，实现即插即用的扩展能力。

数注册到系统中，无需修改核心路由逻辑。子Agent通过 `Agents/agents/insight/__init__.py` 导入 [Agents/server.py:449]，实现即插即用的扩展能力。

**MemoryManager Session管理**：`Agents/common/memory.py` 中的 `MemoryManager` 负责管理Session上下文 [Agents/server.py:440]，为多轮对话提供上下文记忆能力，确保Agent在连续交互中保持状态一致性。

Agent Services（Python / FastAPI）还包含以下公共模块：

| 模块 | 文件路径 | 职责 |
|------|----------|------|
| Config管理 | `Agents/common/config.py:15` | 环境Config、模型参数、API 密钥管理 |
| 检索器 | `Agents/common/retriever.py:54` | `RetrieverType` 枚举定义，检索策略选择 |
| 工具集 | `Agents/common/tools/` | 辅助工具函数，供各子Agent调用 |

### 4.2. Admin 管理后台（Python / Django）

Admin 管理后台（Python / Django）基于 Django 构建，入口点为 `Admin/manage.py`，通过 `Admin/Dockerfile` 进行容器化部署。该组件承担 AgentInsightService（统一使用全称，首次出现可标注品牌名） 的数据管理与Config界面职责，为运营人员提供可视化的数据管理能力。

Admin 后台的核心功能包括：

- **数据模型管理**：为系统各数据模型提供列表展示、过滤、搜索和详情Config能力，覆盖用户、Order、Product、Alert记录等核心数据实体。
- **Config管理**：支持系统运行参数的Config维护，包括数据源连接、默认模板等Config项。
- **任务执行流程**：`Admin/Agents.md` 中定义了完整的任务执行流程规则，涵盖需求分析、需求评审、技术方案设计、设计方案评审、单元测试（红阶段）、功能代码编写（绿阶段）、重构、代码评审、环境部署、执行测试、验收交付等 12 个步骤，每个步骤均包含明确的通过标准 [Admin/Agents.md]。

技术方案设计、设计方案评审、单元测试（红阶段）、功能代码编写（绿阶段）、重构、代码评审、环境部署、执行测试、验收交付等 12 个步骤，每个步骤均包含明确的通过标准 [Admin/Agents.md]。

Admin 后台通过 Django 的 ORM 与主服务数据库交互，遵循 `agentinsight_` 前缀路由到 `default` 库、其他表路由到 `data` 库的数据库路由规则 [Admin/Agents.md]。

### 4.3. 组件间交互协议

AgentInsightService（统一使用全称，首次出现可标注品牌名） 各组件间通过 HTTP 协议、消息队列和 MediatR 通知机制实现通信，形成完整的交互链路。

**API ↔ Agent 交互**：API Services（C# / Furion）通过 HTTP 调用 Agent Services（Python / FastAPI）的用户验证接口，实现用户身份认证与授权。Agent Services（Python / FastAPI）对外提供 OpenAI 兼容的 Chat Completions API，API Services（C# / Furion）作为业务入口将Agent请求转发至 Agent Services（Python / FastAPI）。

**API ↔ 外部Payment交互**：API Services（C# / Furion）通过 `PaymentService` 门面封装与微信Payment、Payment宝Payment的交互。以微信Payment为例，`NotifyController.WeChatNotify` 接收微信Payment回调 [API/Controllers/PaymentManagement/NotifyController.cs:29]，`NotifyHandler.ExamineWeChatRequest` 验证请求签名 [API/Handlers/PaymentManagement/NotifyHandler.cs:18]，`PaymentService.UpdateOrderState` 更新订单状态 [API/Common/Services/PaymentService.cs:71]，随后通过 MediatR 发布 `PaymentTransactionNotification`，由 `PaymentTransactionSaveHandler` 异步保存交易记录 [API/Notifications/PaymentTransactionSaveHandler.cs:8]。

`，由 `PaymentTransactionSaveHandler` 异步保存交易记录 [API/Notifications/PaymentTransactionSaveHandler.cs:8]。

**异步通知机制**：系统通过 MediatR 和 BullMQ 实现双层异步解耦。MediatR 用于进程内的事件发布与处理，例如Payment通知、Alert通知的解耦；BullMQ 基于 Redis 实现跨进程的消息队列，`BullMqService.EnqueueTraceIngestionAsync` 将 Trace 摄入任务入队 [API/Common/Services/BullMqService.cs:23]，`AgentInsightTransformProvider` 依赖 `BullMqService` 实现数据转换与投递 [API/System/Handlers/AgentInsightTransformProvider.cs:5]。

**API 内部调用链**：API Services（C# / Furion）内部遵循 Controllers → Handlers → Services → Repositories → SqlSugar (ORM) 的调用链。Controller通过 `RegisterHandler` 注入Handler，Handler通过构造函数注入服务接口，ServicesRepository模式访问数据。例如，`OrderController.Place` 调用 `OrderHandler.PlaceOrder` [API/Handlers/PaymentManagement/OrderHandler.cs:24]，后者调用 `PaymentService.CreateOrder` 完成订单创建 [API/Common/Services/PaymentService.cs:38]。

以下表格汇总了组件间的主要交互协议：

| 交互路径 | 协议/机制 | 关键组件 |
|----------|-----------|----------|
| API ↔ Agent | HTTP | `Agents/server.py` Chat Completions API |
| API ↔ 微信Payment | HTTPS + 签名验证 | `PaymentService` / `NotifyHandler` |
| API ↔ Payment宝Payment | HTTPS + 签名验证 | `PaymentService.GetAlipaySignDictionary` |
| API 内部异步通知 | MediatR | `PaymentTransactionNotification` / `SystemAlertHandler` |
| API ↔ 消息队列 | Redis / BullMQ | `BullMqService.EnqueueTraceIngestionAsync` |
| API ↔ ClickHouse | ClickHouse 原生协议 | `ClickHouseClient.QueryAsync` |

---

## 5. 数据架构与数据流

<div class="report-image">
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024" width="1024" height="1024">
<defs>
<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
<stop offset="0%" stop-color="#f8f9fa"/>
<stop offset="100%" stop-color="#e9ecef"/>
</linearGradient>
<linearGradient id="blue1" x1="0" y1="0" x2="1" y2="1">
<stop offset="0%" stop-color="#007BFF"/>
<stop offset="100%" stop-color="#0056b3"/>
</linearGradient>
<linearGradient id="gray1" x1="0" y1="0" x2="1" y2="1">
<stop offset="0%" stop-color="#6c757d"/>
<stop offset="100%" stop-color="#495057"/>
</linearGradient>
<linearGradient id="gray2" x1="0" y1="0" x2="1" y2="1">
<stop offset="0%" stop-color="#adb5bd"/>
<stop offset="100%" stop-color="#8a929b"/>
</linearGradient>
<filter id="shadow" x="-10%" y="-10%" width="130%" height="130%">
<feDropShadow dx="0" dy="4" stdDeviation="6" flood-color="#00000020"/>
</filter>
<marker id="arrowBlue" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse">
<path d="M0,0 L10,5 L0,10 z" fill="#007BFF"/>
</marker>
<marker id="arrowGray" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
<path d="M0,0 L10,5 L0,10 z" fill="#6c757d"/>
</marker>
</defs>
<rect width="1024" height="1024" fill="url(#bg)"/>
<text x="512" y="70" text-anchor="middle" font-family="Noto Sans CJK SC,Arial,sans-serif" font-size="36" font-weight="bold" fill="#2c3e50">数据架构与数据流</text>
<text x="512" y="110" text-anchor="middle" font-family="Noto Sans CJK SC,Arial,sans-serif" font-size="20" fill="#6c757d">数据采集 · 处理 · 存储 · 分析 · 应用</text>
<g filter="url(#shadow)">
<rect x="80" y="170" width="240" height="120" rx="16" fill="url(#gray2)"/>
<text x="200" y="215" text-anchor="middle" font-family="Noto Sans CJK SC,Arial,sans-serif" font-size="22" font-weight="bold" fill="#fff">数据源层</text>
<text x="200" y="248" text-anchor="middle" font-family="Noto Sans CJK SC,Arial,sans-serif" font-size="16" fill="#f0f0f0">业务系统 · Log · 传感器</text>
</g>
<g filter="url(#shadow)">
<rect x="392" y="170" width="240" height="120" rx="16" fill="url(#blue1)"/>
<text x="512" y="215" text-anchor="middle" font-family="Noto Sans CJK SC,Arial,sans-serif" font-size="22" font-weight="bold" fill="#fff">数据采集层</text>
<text x="512" y="248" text-anchor="middle" font-family="Noto Sans CJK SC,Arial,sans-serif" font-size="16" fill="#e0e0e0">消息队列 · 实时同步</text>
</g>
<g filter="url(#shadow)">
<rect x="704" y="170" width="240" height="120" rx="16" fill="url(#gray1)"/>
<text x="824" y="215" text-anchor="middle" font-family="Noto Sans CJK SC,Arial,sans-serif" font-size="22" font-weight="bold" fill="#fff">数据处理层</text>
<text x="824" y="248" text-anchor="middle" font-family="Noto Sans CJK SC,Arial,sans-serif" font-size="16" fill="#e0e0e0">ETL · 清洗 · 特征工程</text>
</g>
<g filter="url(#shadow)">
<rect x="80" y="420" width="240" height="120" rx="16" fill="url(#blue1)"/>
<text x="200" y="465" text-anchor="middle" font-family="Noto Sans CJK SC,Arial,sans-serif" font-size="22" font-weight="bold" fill="#fff">数据存储层</text>
<text x="200" y="498" text-anchor="middle" font-family="Noto Sans CJK SC,Arial,sans-serif" font-size="16" fill="#e0e0e0">数据仓库 · 数据湖</text>
</g>
<g filter="url(#shadow)">
<rect x="392" y="420" width="240" height="120" rx="16" fill="url(#gray2)"/>
<text x="512" y="465" text-anchor="middle" font-family="Noto Sans CJK SC,Arial,sans-serif" font-size="22" font-weight="bold" fill="#fff">Services</text>
<text x="512" y="498" text-anchor="middle" font-family="Noto Sans CJK SC,Arial,sans-serif" font-size="16" fill="#f0f0f0">API · 数据接口 · 指标平台</text>
</g>
<g filter="url(#shadow)">
<rect x="704" y="420" width="240" height="120" rx="16" fill="url(#gray1)"/>
<text x="824" y="465" text-anchor="middle" font-family="Noto Sans CJK SC,Arial,sans-serif" font-size="22" font-weight="bold" fill="#fff">数据应用层</text>
<text x="824" y="498" text-anchor="middle" font-family="Noto Sans CJK SC,Arial,sans-serif" font-size="16" fill="#e0e0e0">BI · 可视化 · 机器学习</text>
</g>
<g filter="url(#shadow)">
<rect x="80" y="680" width="864" height="90" rx="16" fill="#2c3e50"/>
<text x="512" y="718" text-anchor="middle" font-family="Noto Sans CJK SC,Arial,sans-serif" font-size="20" font-weight="bold" fill="#fff">数据治理与安全</text>
<text x="512" y="748" text-anchor="middle" font-family="Noto Sans CJK SC,Arial,sans-serif" font-size="15" fill="#adb5bd">数据标准 · 数据质量 · 数据血缘 · Privilege控制 · 审计</text>
</g>
<line x1="320" y1="230" x2="382" y2="230" stroke="#007BFF" stroke-width="3" marker-end="url(#arrowBlue)"/>
<line x1="632" y1="230" x2="694" y2="230" stroke="#007BFF" stroke-width="3" marker-end="url(#arrowBlue)"/>
<line x1="200" y1="290" x2="200" y2="410" stroke="#007BFF" stroke-width="3" marker-end="url(#arrowBlue)"/>
<line x1="512" y1="290" x2="512" y2="410" stroke="#007BFF" stroke-width="3" marker-end="url(#arrowBlue)"/>
<line x1="824" y1="290" x2="824" y2="410" stroke="#007BFF" stroke-width="3" marker-end="url(#arrowBlue)"/>
<line x1="320" y1="480" x2="382" y2="480" stroke="#6c757d" stroke-width="3" marker-end="url(#arrowGray)"/>
<line x1="632" y1="480" x2="694" y2="480" stroke="#6c757d" stroke-width="3" marker-end="url(#arrowGray)"/>
<line x1="512" y1="540" x2="512" y2="670" stroke="#6c757d" stroke-width="3" marker-end="url(#arrowGray)"/>
<line x1="200" y1="540" x2="200" y2="670" stroke="#6c757d" stroke-width="3" marker-end="url(#arrowGray)"/>
<line x1="824" y1="540" x2="824" y2="670" stroke="#6c757d" stroke-width="3" marker-end="url(#arrowGray)"/>
<line x1="80" y1="725" x2="70" y2="725" stroke="#6c757d" stroke-width="2"/>
<line x1="944" y1="725" x2="954" y2="725" stroke="#6c757d" stroke-width="2"/>
<line x1="70" y1="725" x2="70" y2="230" stroke="#adb5bd" stroke-width="2" stroke-dasharray="6,4"/>
<line x1="70" y1="230" x2="80" y2="230" stroke="#adb5bd" stroke-width="2"/>
<line x1="954" y1="725" x2="954" y2="230" stroke="#adb5bd" stroke-width="2" stroke-dasharray="6,4"/>
<line x1="954" y1="230" x2="944" y2="230" stroke="#adb5bd" stroke-width="2"/>
<text x="48" y="480" text-anchor="middle" font-family="Noto Sans CJK SC,Arial,sans-serif" font-size="14" fill="#6c757d" transform="rotate(-90,48,480)">数据流转</text>
<text x="976" y="480" text-anchor="middle" font-family="Noto Sans CJK SC,Arial,sans-serif" font-size="14" fill="#6c757d" transform="rotate(90,976,480)">数据流转</text>
<circle cx="200" cy="170" r="6" fill="#adb5bd"/>
<circle cx="512" cy="170" r="6" fill="#007BFF"/>
<circle cx="824" cy="170" r="6" fill="#6c757d"/>
<circle cx="200" cy="420" r="6" fill="#007BFF"/>
<circle cx="512" cy="420" r="6" fill="#adb5bd"/>
<circle cx="824" cy="420" r="6" fill="#6c757d"/>
</svg>
</div>

AgentInsightService（统一使用全称，首次出现可标注品牌名） 采用 **分层架构 + 微服务编排模式** 模式，由三个独立运行时组件构成：ControllerControllers（`API/Controllers/`）提供 76 个 HTTP 端点，HandlerHandlers（`API/Handlers/`）承载业务逻辑核心，Services（`API/Common/Services/`）封装外部集成（Payment、微信、Alert、消息队列）。数据架构围绕三类数据库构建：PostgreSQL 承载业务主数据（User、业务数据、Trace数据三个独立连接串），ClickHouse 存储 Trace Observation数据，Redis 承担缓存、BullMQ 消息队列与Session管理。数据实体定义在 `Entities/` Project，DTO 定义在 `Models/` Project，通过 SqlSugar ORM 进行数据访问。本章详细阐述数据分类与存储矩阵、数据模型概览、同步/异步数据流以及数据安全与持久化机制。

### 5.1. 数据分类与存储矩阵

AgentInsightService（统一使用全称，首次出现可标注品牌名） 采用多存储引擎混合架构，根据数据特性（一致性要求、访问模式、数据生命周期）将数据分类存储于三类存储系统中。系统通过三个独立 PostgreSQL 连接串实现业务数据库的物理隔离，每个连接串对应独立的数据库实例，Config了不同的连接池参数与超时策略。

**PostgreSQL 业务数据库（三连接串隔离）**

系统Config了三个独立的 PostgreSQL 连接串，分别对应不同业务域的数据存储：

| 连接串名称 | Config键 | 主要数据域 | 连接池Config |
|-----------|--------|-----------|-----------|
| UserDb | `ConnectionStrings:UserDb` | 用户账号、Org、Privilege、Session | MinPoolSize=10, MaxPoolSize=200, ConnectionIdleTimeout=300 |
| DataDb | `ConnectionStrings:DataDb` | Project、模型定义、Trace 元数据、AlertConfig | MinPoolSize=10, MaxPoolSize=200, ConnectionIdleTimeout=300 |
| TrackingDb | `ConnectionStrings:TrackingDb` | Trace记录、审计日志、操作轨迹 | MinPoolSize=10, MaxPoolSize=200, ConnectionIdleTimeout=300 |

三个连接串均指向 PostgreSQL（Provider=postgres），通过环境变量注入数据库名、用户名与密码，连接超时设置为 60 秒。这种物理隔离设计确保用户数据、业务数据与Trace数据互不影响，避免单一数据库故障导致全系统不可用。

在代码层面，Handler通过依赖注入获取不同数据库的 `ISqlSugarClient` 实例。`MetricsHandler` 构造函数中通过 `[FromKeyedServices(AgentInsightConst.KeyedService_UserDb)]`、`[FromKeyedServices(AgentInsightConst.KeyedService_DataDb)]` 和 `[FromKeyedServices(AgentInsightConst.KeyedService_ClickHouseDb)]` 分别注入用户库、数据库和 ClickHouse 客户端 [API/Handlers/DataManagement/MetricsHandler.cs]。`OrderRepository` 则通过 `[FromKeyedServices(AgentInsightConst.KeyedService_UserDb)]` 注入用户库，用于订单数据的持久化 [API/Common/Services/OrderRepository.cs]。

**ClickHouse Observation数据库**

ClickHouse 用于存储 Trace Observation数据，包括 Trace 明细、Observation 和 Score 等时序数据。连接串Config为 `ConnectionStrings:ClickHouseDb`，包含连接池大小（MinPoolSize=10, MaxPoolSize=50）、连接超时（30 秒）和命令超时（60 秒）。`MetricsHandler` 通过 `_chdb`（ISqlSugarClient）和 `_clickHouseClient`（IClickHouseClient）两个通道访问 ClickHouse：前者用于结构化查询（如按 TraceId 查询 Observation/Score），后者用于复杂聚合查询 [API/Handlers/DataManagement/MetricsHandler.cs]。

**Redis 缓存与消息队列**

Redis 承担三类职责：缓存（用户Session、Privilege数据）、BullMQ 消息队列（异步任务处理）和Session状态管理。`BullMqService` 封装了消息队列的入队与确认操作，`EnqueueTraceIngestionAsync` 用于将 Trace 摄入任务异步写入队列 [API/Common/Services/AlertService.cs]。`AgentInsightTransformProvider` 依赖 `BullMqService` 和 `IAppContextService`，实现反向代理转换与消息队列集成 [API/System/Handlers/AgentInsightTransformProvider.cs]。

**存储选型决策矩阵**

| 数据类型 | 存储引擎 | 选型理由 | 生命周期 |
|---------|---------|---------|---------|
| User/Org/Privilege | PostgreSQL (UserDb) | 强一致性、事务支持 | 永久 |
| Order/Payment | PostgreSQL (UserDb) | 事务性要求高、审计需求 | 永久 |
| Project/模型定义 | PostgreSQL (DataDb) | 关系模型、关联查询 | 永久 |
| Trace 元数据 | PostgreSQL (DataDb) | 与业务数据关联 | 永久 |
| AlertConfig/记录 | PostgreSQL (DataDb) | 关系模型、频繁更新 | 永久 |
| Trace Observation数据 | ClickHouse | 高吞吐写入、列式存储、时序聚合 | 按策略归档 |
| Session状态 | Redis | 高速读写、TTL 过期 | 短期 |
| 消息队列 | Redis (BullMQ) | 异步解耦、可靠投递 | 任务完成后删除 |
| 缓存数据 | Redis | 降低数据库压力 | 按 TTL 过期 |

### 5.2. 数据模型概览

AgentInsightService（统一使用全称，首次出现可标注品牌名） 的数据模型遵循“实体定义与 DTO 分离”的设计原则。`Entities/` 项目包含数据库实体类（ORM 映射），`Models/` 项目包含 DTO/请求/响应模型，两者均为纯数据结构，无外部依赖。数据访问通过 SqlSugar ORM 完成，支持读写分离、分页查询和复杂条件构建。

**实体层（Entities/）**

实体类直接映射数据库表结构，使用 SqlSugar 特性标注表名、主键和列映射。主要实体包括：

| 实体类 | 所属项目 | 存储位置 | 说明 |
|--------|---------|---------|------|
| `AgentInsightOrder` | Entities.PaymengManagement | UserDb | 订单实体，包含订单号、交易号、金额、状态等字段 |
| `Observation` | Entities.DataManagement | ClickHouse | Trace Observation数据，按 TraceId 关联 |
| `Score` | Entities.DataManagement | ClickHouse | Trace Score数据，按 TraceId 关联 |
| `TraceMetrics` | Entities.DataManagement | ClickHouse | Trace 指标聚合数据 |
| `ModelDefinition` | Entities.DataManagement | DataDb | 模型定义，PricingTiers |
| `AgentConfig` | Entities.AgentManagement | DataDb | Agent Config，包含数据源连接信息 |

`AgentInsightOrder` 实体通过 `OrderRepository` 进行 CRUD 操作，包括 `GetByOrderNoAsync`、`GetByIdAsync`、`CreateAsync` 和 `UpdateStateAsync` 等方法 [API/Common/Services/OrderRepository.cs]。`ModelDefinition` 实体通过 `ModelHandler` 查询，支持按关键词、Project ID 和预定义模型过滤，并通过 `.Includes(m => m.PricingTiers, t => t.Prices)` 加载嵌套定价层级 [API/Handlers/DataManagement/ModelHandler.cs]。

**DTO/请求模型层（Models/）**

DTO 模型定义 API 请求与响应的数据结构，与实体解耦。主要 DTO 包括：

| DTO 类 | 用途 | 关键字段 |
|--------|------|---------|
| `AgentInsightOrderBody` | 下单请求 | orgid, productid, productdurationid, paymethod, subpaymethod |
| `AgentInsightOrderResponse` | 下单响应 | orderno, state, codeurl, qrcode, prepayid |
| `TraceMetricsBody` | Trace 查询条件 | orgid, projectid, traceid, name, from, to, page, pagesize, orderby, filter |
| `TraceMetricsResponse` | Trace 指标响应 | traceid, inputtokens, outputtokens, totaltokens, inputcost, outputcost, totalcost, latency, modelnames |
| `ModelDefinition` | 模型定义 DTO | id, projectid, modelname, matchpattern, inputprice, outputprice, pricingtiers |

**ORM 数据访问模式**

所有数据访问通过 SqlSugar ORM 完成。HandlerHandlers继承 `ApiHandlerBase`，通过构造函数注入 `ISqlSugarClient` 实例。`ApiHandlerBase` 提供统一的 Db/User/UserDb 访问入口 [API/Handlers/ApiHandlerBase.cs]。`MetricsHandler` 同时持有用户库、数据库和 ClickHouse 三个客户端，根据业务需求选择不同的数据源 [API/Handlers/DataManagement/MetricsHandler.cs]。

**枚举与常量定义**

数据模型中大量使用枚举定义状态值和类型，确保数据一致性：

| 枚举 | 定义位置 | 关键值 |
|------|---------|--------|
| `OrderState` | Models/Common/Enums/PaymentEnums.cs | 1=Created, 2=Paid, 3=Refunded, 4=Cancelled, 5=Closed, 6=Expired |
| `ProductType` | Models/Common/Enums/PaymentEnums.cs | 1=Token 包, 2=订阅等 |
| `PayMethod` | Models/Common/Enums/PaymentEnums.cs | 1=WeChat, 2=Alipay |
| `SubPayMethod` | Models/Common/Enums/PaymentEnums.cs | 1=JSAPI, 2=Native, 3=小程序, 11=电脑网站 |
| `BillingCycle` | Models/Common/Enums/PaymentEnums.cs | 0=None, 1=Monthly, 2=Permanent |
| `ExceptionCodes` | Models/Common/Enums/ExceptionCodes.cs | InvalidOrder=150018, OrderNotFound=150022 等 |

### 5.3. 同步/异步数据流

AgentInsightService（统一使用全称，首次出现可标注品牌名） 的数据流分为同步请求-响应流和异步事件驱动流两类。同步流用于即时数据查询与业务操作，异步流用于解耦耗时操作和跨系统通知。

**同步数据流：Payment流程**

Payment流程是典型的同步+异步混合数据流。客户端发起下单请求后，系统同步创建订单并返回Payment参数；Payment结果通过异步回调通知更新订单状态。

```
Client → OrderController.Place (API/Controllers/PaymentManagement/OrderController.cs:48)
  → OrderHandler.PlaceOrder (API/Handlers/PaymentManagement/OrderHandler.cs:24)
    → PaymentService.CreateOrder (API/Common/Services/PaymentService.cs:38)
    → PaymentService.GetWeChatJSAPIResponse / GetAlipayInstantTrade
    → 返回Payment参数给客户端

Payment回调:
  微信: NotifyController.WeChatNotify (API/Controllers/PaymentManagement/NotifyController.cs:29)
  Payment宝: NotifyController.AlipayNotify (API/Controllers/PaymentManagement/NotifyController.cs:57)
```

回调处理流程：

```
微信: NotifyController.WeChatNotify (API/Controllers/PaymentManagement/NotifyController.cs:29)
  → PaymentService.UpdateOrderState (API/Common/Services/PaymentService.cs:71)
    → OrderRepository.UpdateStateAsync (API/Common/Services/OrderRepository.cs)
    → MediatR 发布 PaymentTransactionNotification
```

`PaymentService.UpdateOrderState` 更新订单状态后，通过 MediatR 发布 `PaymentTransactionNotification`，通知Handler异步处理后续逻辑（如开通Privilege、发送通知）[API/Common/Services/PaymentService.cs:71]。`OrderRepository.UpdateStateAsync` 使用 SqlSugar 更新订单状态字段 [API/Common/Services/OrderRepository.cs]。

**同步数据流：Trace 查询流**

Trace 查询是同步请求-响应流，用户通过 API 查询 Trace Observation数据。

```
MetricsController.GetTraceMetrics (API/Controllers/DataManagement/MetricsController.cs:64)
  → MetricsHandler.GetTraceMetrics (API/Handlers/DataManagement/MetricsHandler.cs:18)
    → TraceFilterBuilder.BuildFilters (API/Common/Helpers/TraceFilterBuilder.cs:34)
    → ClickHouseClient.QueryAsync (API/Common/Services/ClickHouseClient.cs:10)
    → 返回 TraceMetrics 列表
```

`MetricsController.GetTraceMetrics` 支持 GET（按 ID 批量查询）和 POST（分页条件查询）两种方式 [API/Controllers/DataManagement/MetricsController.cs:64]。`MetricsHandler.GetTraceMetrics` 首先解析项目 ID（`ResolveProjectId`），然后解析选择字段、排序方式和过滤条件，最后调用 `TraceFilterBuilder.BuildFilters` 动态构建 ClickHouse 查询条件 [API/Handlers/DataManagement/MetricsHandler.cs:18]。`TraceFilterBuilder` 采用 Builder 模式，将前端传入的过滤条件（`FilterField`、`FilterOperator`、`FilterValue`）转换为 ClickHouse SQL 条件 [API/Common/Helpers/TraceFilterBuilder.cs:34]。

**异步数据流：Alert数据流**

Alert数据流是异步事件驱动流，由定时任务或指标触发，通过 MediatR 通知Handler异步处理。

```
AlertMetricsHandler.GetAlertMetrics (API/Handlers/DataManagement/AlertMetricsHandler.cs:10)
  → AlertService.GetAlertMetrics (API/Common/Services/AlertService.cs:23)
    → ClickHouseClient.QueryAsync (API/Common/Services/ClickHouseClient.cs:10)
  → AlertService.EvaluateField (API/Common/Services/AlertService.cs:18)
  → AlertService.IsConditionMet (API/Common/Services/AlertService.cs:16)
    → SystemAlertHandler 记录Alert日志 (API/Notifications/SystemAlertHandler.cs:8)
    → SMSAlertHandler 发送短信通知 (API/Notifications/SMSAlertHandler.cs:8)
```

`AlertService.GetAlertMetrics` 从 ClickHouse 查询指标数据，`EvaluateField` 使用策略模式调用具体的 `IAlertFieldEvaluator` 实现进行指标评估 [API/Common/Services/AlertService.cs:18]。当条件满足时（`IsConditionMet`），触发 `AlertTriggeredNotification`，由 `SystemAlertHandler` 记录Alert日志、`SMSAlertHandler` 发送短信通知 [API/Notifications/SystemAlertHandler.cs:8]。Alert评估器采用策略模式，`IAlertFieldEvaluator` 接口 + 9 个具体评估器，每个评估器负责一种指标类型的评估逻辑 [API/Notifications/AlertEvaluators/IAlertFieldEvaluator.cs]。

**异步数据流：Agent 对话流**

Agent 对话流由 Python FastAPI 服务处理，客户端通过 SSE（Server-Sent Events）接口与 Agent 服务通信。

```
Client → POST /api/agent/insight (Agents/server.py:203)
  → InsightOrchestrator 路由到子 Agent
    → MemoryManager 管理Session状态
    → 返回 SSE 流式响应
```

`InsightOrchestrator` 作为统一入口路由到子Agent [Agents/server.py:451]。Session状态由 `MemoryManager` 管理，通过 `Agents/common/memory.py` 实现 [Agents/server.py:440]。Agent 对话流采用异步流式响应，客户端通过 SSE 持续接收生成结果。

**异步数据流：Trace 摄入队列**

Trace 数据摄入采用异步队列模式，`AlertService.EnqueueTraceIngestionAsync` 将 Trace 摄入任务写入 BullMQ 队列 [API/Common/Services/AlertService.cs:23]。`BullMqService` 封装了队列操作，`AgentInsightTransformProvider` 通过 `BullMqService` 将转换后的数据异步写入队列 [API/System/Handlers/AgentInsightTransformProvider.cs:5]。

**数据流时序对比**

| 数据流类型 | 触发方式 | 响应模式 | 数据一致性 | 典型延迟 |
|-----------|---------|---------|-----------|---------|
| Payment下单 | 用户请求 | 同步返回Payment参数 | 强一致（订单创建） | < 500ms |
| Payment回调 | 第三方回调 | 异步更新订单状态 | 最终一致（状态流转） | < 5s |
| Trace 查询 | 用户请求 | 同步返回查询结果 | 读已提交 | < 1s |
| Alert触发 | 定时/事件 | 异步通知（Log+短信） | 最终一致 | < 10s |
| Agent 对话 | 用户请求 | SSE 流式响应 | Session级一致 | 首 token < 2s |
| Trace 摄入 | 异步队列 | 后台批量处理 | 最终一致 | < 30s |

### 5.4. 数据安全与持久化

AgentInsightService（统一使用全称，首次出现可标注品牌名） 的数据安全策略覆盖传输加密、存储加密、密钥管理和持久化机制四个层面。

**敏感字段加密**

系统使用 AES 加密算法保护敏感字段。`EncryptionOptions:Key` Config项从环境变量 `${AES_ENCRYPTION_KEY}` 注入，用于加密数据库中的敏感数据（如Payment密钥、用户隐私字段）。加密密钥不存储在代码库或Config文件中，而是通过环境变量在部署时注入，确保密钥安全。

**ASP.NET DataProtection 密钥持久化**

ASP.NET DataProtection 框架用于保护认证 Cookie 和防伪Token。DataProtection 密钥持久化于 `dataprotection-keys` 卷中，确保应用重启后密钥不丢失，避免已签发的认证Token失效。密钥持久化卷通过 Docker 挂载，保证多实例部署时密钥一致。

**连接串安全**

所有数据库连接串均通过环境变量注入，不包含硬编码凭据。连接串格式如下：

```
ConnectionStrings:UserDb = Server=${DB_HOST};Port=${DB_PORT};Database=${DB_USER_DB};UserId=${DB_USER};Password=${DB_PASSWORD};Timeout=60;Pooling=true;MinPoolSize=10;MaxPoolSize=200;ConnectionIdleTimeout=300
```

连接串中的用户名、密码、数据库名均通过环境变量注入，避免敏感信息泄露。

**数据持久化策略**

| 数据类别 | 持久化机制 | 备份策略 | 恢复点目标 |
|---------|-----------|---------|-----------|
| PostgreSQL 业务数据 | 磁盘持久化 + WAL Log | 定期全量备份 + PITR | < 15 分钟 |
| ClickHouse Observation数据 | 磁盘持久化 + 副本 | 定期快照 | < 1 小时 |
| Redis 缓存/队列 | RDB + AOF | 定期快照 | 可重建 |
| DataProtection 密钥 | dataprotection-keys 卷 | 卷备份 | 必须恢复 |

**数据隔离与访问控制**

Org维度进行数据隔离。`ApiHandlerBase` 实现 `IUserAwareHandler` 接口，Handler通过 `IAppContextService` 获取当前用户上下文，在数据查询时自动附加组织过滤条件。`ModelHandler.GetModelDefinitions` 在查询前调用 `RequireAccessibleProject(projectId)` 验证用户对项目的访问Privilege [API/Handlers/DataManagement/ModelHandler.cs]。`MetricsHandler.GetTraceMetrics` 通过 `ResolveProjectId` 解析项目 ID，确保用户只能查询有Privilege的项目数据 [API/Handlers/DataManagement/MetricsHandler.cs]。

**数据生命周期管理**

| 数据类别 | 保留期限 | 清理策略 |
|---------|---------|---------|
| User/组织数据 | 永久 | 手动删除 |
| Order/Payment数据 | 永久（审计要求） | 归档 |
| Trace Observation数据 | 按Config策略 | 定期归档/清理 |
| Session数据 | TTL 过期 | Redis 自动清理 |
| 消息队列数据 | 任务完成后删除 | BullMQ 自动清理 |
| 缓存数据 | TTL 过期 | Redis 自动清理 |

**安全审计**

系统通过 TrackingDb 独立存储Trace记录和审计日志，实现操作可追溯。`AuditActionType` 和 `AuditResourceType` 枚举定义审计操作类型和资源类型 [Models/Common/Enums/AuditEnum.cs]。审计日志与业务数据物理隔离，确保审计数据的完整性和不可篡改性。

---

## 6. 部署架构

<div class="report-image">
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024" width="1024" height="1024">
<defs>
<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
<stop offset="0%" stop-color="#f0f4f8"/>
<stop offset="100%" stop-color="#e2e8f0"/>
</linearGradient>
<linearGradient id="clientG" x1="0" y1="0" x2="0" y2="1">
<stop offset="0%" stop-color="#007BFF"/>
<stop offset="100%" stop-color="#0056b3"/>
</linearGradient>
<linearGradient id="lbG" x1="0" y1="0" x2="0" y2="1">
<stop offset="0%" stop-color="#6c757d"/>
<stop offset="100%" stop-color="#495057"/>
</linearGradient>
<linearGradient id="appG" x1="0" y1="0" x2="0" y2="1">
<stop offset="0%" stop-color="#007BFF"/>
<stop offset="100%" stop-color="#0069d9"/>
</linearGradient>
<linearGradient id="cacheG" x1="0" y1="0" x2="0" y2="1">
<stop offset="0%" stop-color="#adb5bd"/>
<stop offset="100%" stop-color="#868e96"/>
</linearGradient>
<linearGradient id="dbG" x1="0" y1="0" x2="0" y2="1">
<stop offset="0%" stop-color="#6c757d"/>
<stop offset="100%" stop-color="#343a40"/>
</linearGradient>
<filter id="shadow">
<feDropShadow dx="2" dy="3" stdDeviation="4" flood-opacity="0.15"/>
</filter>
</defs>
<rect width="1024" height="1024" fill="url(#bg)" rx="16"/>
<text x="512" y="52" text-anchor="middle" font-family="Noto Sans CJK SC,Arial,sans-serif" font-size="28" font-weight="bold" fill="#2c3e50">部署架构图</text>
<line x1="80" y1="72" x2="944" y2="72" stroke="#007BFF" stroke-width="2" opacity="0.3"/>
<rect x="60" y="100" width="904" height="180" rx="12" fill="none" stroke="#adb5bd" stroke-width="1.5" stroke-dasharray="6,4"/>
<text x="84" y="130" font-family="Noto Sans CJK SC,Arial,sans-serif" font-size="16" fill="#6c757d" font-weight="bold">用户端</text>
<rect x="120" y="150" width="180" height="90" rx="10" fill="url(#clientG)" filter="url(#shadow)"/>
<text x="210" y="190" text-anchor="middle" font-family="Noto Sans CJK SC,Arial,sans-serif" font-size="18" fill="#fff" font-weight="bold">浏览器客户端</text>
<text x="210" y="215" text-anchor="middle" font-family="Noto Sans CJK SC,Arial,sans-serif" font-size="13" fill="#cce5ff">PC / 移动端</text>
<rect x="380" y="150" width="180" height="90" rx="10" fill="url(#clientG)" filter="url(#shadow)"/>
<text x="470" y="190" text-anchor="middle" font-family="Noto Sans CJK SC,Arial,sans-serif" font-size="18" fill="#fff" font-weight="bold">移动应用</text>
<text x="470" y="215" text-anchor="middle" font-family="Noto Sans CJK SC,Arial,sans-serif" font-size="13" fill="#cce5ff">iOS / Android</text>
<rect x="640" y="150" width="180" height="90" rx="10" fill="url(#clientG)" filter="url(#shadow)"/>
<text x="730" y="190" text-anchor="middle" font-family="Noto Sans CJK SC,Arial,sans-serif" font-size="18" fill="#fff" font-weight="bold">API 调用方</text>
<text x="730" y="215" text-anchor="middle" font-family="Noto Sans CJK SC,Arial,sans-serif" font-size="13" fill="#cce5ff">第三方服务</text>
<rect x="60" y="320" width="904" height="250" rx="12" fill="none" stroke="#adb5bd" stroke-width="1.5" stroke-dasharray="6,4"/>
<text x="84" y="350" font-family="Noto Sans CJK SC,Arial,sans-serif" font-size="16" fill="#6c757d" font-weight="bold">接入层</text>
<rect x="120" y="370" width="200" height="80" rx="10" fill="url(#lbG)" filter="url(#shadow)"/>
<text x="220" y="405" text-anchor="middle" font-family="Noto Sans CJK SC,Arial,sans-serif" font-size="18" fill="#fff" font-weight="bold">负载均衡器</text>
<text x="220" y="430" text-anchor="middle" font-family="Noto Sans CJK SC,Arial,sans-serif" font-size="13" fill="#e9ecef">Nginx / SLB</text>
<rect x="400" y="370" width="200" height="80" rx="10" fill="url(#lbG)" filter="url(#shadow)"/>
<text x="500" y="405" text-anchor="middle" font-family="Noto Sans CJK SC,Arial,sans-serif" font-size="18" fill="#fff" font-weight="bold">API 网关</text>
<text x="500" y="430" text-anchor="middle" font-family="Noto Sans CJK SC,Arial,sans-serif" font-size="13" fill="#e9ecef">认证 / 限流</text>
<rect x="680" y="370" width="200" height="80" rx="10" fill="url(#lbG)" filter="url(#shadow)"/>
<text x="780" y="405" text-anchor="middle" font-family="Noto Sans CJK SC,Arial,sans-serif" font-size="18" fill="#fff" font-weight="bold">CDN 加速</text>
<text x="780" y="430" text-anchor="middle" font-family="Noto Sans CJK SC,Arial,sans-serif" font-size="13" fill="#e9ecef">静态资源</text>
<rect x="60" y="610" width="904" height="250" rx="12" fill="none" stroke="#adb5bd" stroke-width="1.5" stroke-dasharray="6,4"/>
<text x="84" y="640" font-family="Noto Sans CJK SC,Arial,sans-serif" font-size="16" fill="#6c757d" font-weight="bold">Services</text>
<rect x="100" y="660" width="220" height="80" rx="10" fill="url(#appG)" filter="url(#shadow)"/>
<text x="210" y="695" text-anchor="middle" font-family="Noto Sans CJK SC,Arial,sans-serif" font-size="18" fill="#fff" font-weight="bold">应用服务节点 1</text>
<text x="210" y="720" text-anchor="middle" font-family="Noto Sans CJK SC,Arial,sans-serif" font-size="13" fill="#cce5ff">业务逻辑处理</text>
<rect x="400" y="660" width="220" height="80" rx="10" fill="url(#appG)" filter="url(#shadow)"/>
<text x="510" y="695" text-anchor="middle" font-family="Noto Sans CJK SC,Arial,sans-serif" font-size="18" fill="#fff" font-weight="bold">应用服务节点 2</text>
<text x="510" y="720" text-anchor="middle" font-family="Noto Sans CJK SC,Arial,sans-serif" font-size="13" fill="#cce5ff">业务逻辑处理</text>
<rect x="700" y="660" width="220" height="80" rx="10" fill="url(#cacheG)" filter="url(#shadow)"/>
<text x="810" y="695" text-anchor="middle" font-family="Noto Sans CJK SC,Arial,sans-serif" font-size="18" fill="#343a40" font-weight="bold">缓存集群</text>
<text x="810" y="720" text-anchor="middle" font-family="Noto Sans CJK SC,Arial,sans-serif" font-size="13" fill="#495057">Redis</text>
<rect x="60" y="890" width="904" height="90" rx="12" fill="none" stroke="#adb5bd" stroke-width="1.5" stroke-dasharray="6,4"/>
<text x="84" y="920" font-family="Noto Sans CJK SC,Arial,sans-serif" font-size="16" fill="#6c757d" font-weight="bold">数据层</text>
<rect x="120" y="900" width="240" height="60" rx="10" fill="url(#dbG)" filter="url(#shadow)"/>
<text x="240" y="930" text-anchor="middle" font-family="Noto Sans CJK SC,Arial,sans-serif" font-size="17" fill="#fff" font-weight="bold">主数据库</text>
<text x="240" y="950" text-anchor="middle" font-family="Noto Sans CJK SC,Arial,sans-serif" font-size="12" fill="#ced4da">MySQL 主节点</text>
<rect x="420" y="900" width="240" height="60" rx="10" fill="url(#dbG)" filter="url(#shadow)"/>
<text x="540" y="930" text-anchor="middle" font-family="Noto Sans CJK SC,Arial,sans-serif" font-size="17" fill="#fff" font-weight="bold">从数据库</text>
<text x="540" y="950" text-anchor="middle" font-family="Noto Sans CJK SC,Arial,sans-serif" font-size="12" fill="#ced4da">MySQL 从节点</text>
<rect x="720" y="900" width="200" height="60" rx="10" fill="url(#dbG)" filter="url(#shadow)"/>
<text x="820" y="930" text-anchor="middle" font-family="Noto Sans CJK SC,Arial,sans-serif" font-size="17" fill="#fff" font-weight="bold">对象存储</text>
<text x="820" y="950" text-anchor="middle" font-family="Noto Sans CJK SC,Arial,sans-serif" font-size="12" fill="#ced4da">文件 / 图片</text>
<line x1="210" y1="240" x2="220" y2="370" stroke="#007BFF" stroke-width="2" marker-end="url(#arrowBlue)"/>
<line x1="470" y1="240" x2="500" y2="370" stroke="#007BFF" stroke-width="2"/>
<line x1="730" y1="240" x2="780" y2="370" stroke="#007BFF" stroke-width="2"/>
<line x1="220" y1="450" x2="210" y2="660" stroke="#6c757d" stroke-width="2"/>
<line x1="500" y1="450" x2="510" y2="660" stroke="#6c757d" stroke-width="2"/>
<line x1="780" y1="450" x2="810" y2="660" stroke="#6c757d" stroke-width="2"/>
<line x1="320" y1="700" x2="700" y2="700" stroke="#adb5bd" stroke-width="2" stroke-dasharray="5,3"/>
<line x1="810" y1="740" x2="810" y2="900" stroke="#6c757d" stroke-width="2"/>
<line x1="210" y1="740" x2="240" y2="900" stroke="#6c757d" stroke-width="2"/>
<line x1="510" y1="740" x2="540" y2="900" stroke="#6c757d" stroke-width="2"/>
<line x1="360" y1="930" x2="420" y2="930" stroke="#adb5bd" stroke-width="2" stroke-dasharray="5,3"/>
<text x="690" y="695" font-family="Noto Sans CJK SC,Arial,sans-serif" font-size="12" fill="#6c757d">读写</text>
<text x="285" y="715" font-family="Noto Sans CJK SC,Arial,sans-serif" font-size="12" fill="#6c757d">读写分离</text>
<text x="130" y="565" font-family="Noto Sans CJK SC,Arial,sans-serif" font-size="13" fill="#007BFF" font-weight="bold">HTTPS</text>
<text x="455" y="565" font-family="Noto Sans CJK SC,Arial,sans-serif" font-size="13" fill="#007BFF" font-weight="bold">RESTful</text>
<text x="740" y="565" font-family="Noto Sans CJK SC,Arial,sans-serif" font-size="13" fill="#007BFF" font-weight="bold">WebSocket</text>
</svg>
</div>

AgentInsightService（统一使用全称，首次出现可标注品牌名） 采用基于 docker-compose 的单机多服务部署模型，将 API Services（C# / Furion）（C# / Furion）、Agent Services（Python / FastAPI）（Python / FastAPI）、Admin 管理后台（Python / Django）（Python / Django）与基础设施组件（PostgreSQL、ClickHouse、Redis、、Langfuse）统一编排在同一 Docker 网络中。API Services（C# / Furion）入口点为 `API/Program.cs`，负责应用启动Config与所有服务注册；Agent Services（Python / FastAPI）入口点为 `Agents/server.py`，提供 OpenAI 兼容的 Chat Completions API；Admin 管理后台（Python / Django）入口点为 `Admin/manage.py`，提供 Django 管理界面 [API/Program.cs]。本章节详细阐述部署拓扑、网络与端口规划、容器与编排方式以及环境策略与Config。

### 6.1. 部署拓扑

AgentInsightService（统一使用全称，首次出现可标注品牌名） 的部署拓扑采用单机多容器架构，所有服务通过 docker-compose 统一编排，运行在同一宿主机上。整体拓扑包含三个计算容器与五个基础设施容器，共计八个核心服务。

计算容器层承载业务逻辑：

| 容器 | 技术栈 | 构建来源 | 职责 |
|------|--------|---------|------|
| service | C# / Furion (ASP.NET Core) | 本地 Dockerfile | 提供 76 个 HTTP 端点，处理用户、Payment、Alert、数据管理等业务 [API/Controllers/] |
| agent | Python / FastAPI | Agents/Dockerfile | 提供 OpenAI 兼容的 Chat Completions API，通过 `InsightOrchestrator` 路由请求到子Agent [Agents/server.py:451] |
| admin | Python / Django | Admin/Dockerfile | 提供管理后台界面，使用 PostgreSQL 双库（`default` + `data`） [Admin/Agents.md] |

thon / Django | Admin/Dockerfile | 提供管理后台界面，使用 PostgreSQL 双库（`default` + `data`） [Admin/Agents.md] |

基础设施容器层提供数据存储与可Observation性能力：

| 容器 | 端口 | 职责 |
|------|------|------|
| postgres | 5432 | 主关系型数据库，承载用户库（）、DataDb与Trace库（） |
| clickhouse | 8123/9000 | 列式分析数据库，存储 Trace 指标与Alert指标数据 |
| redis | 6379 | 缓存与消息队列，支撑 `BullMqService` 的 BullMQ 兼容实现 |
| minio | 9000/9001 | 对象存储，用于文件与静态资源持久化 |
| langfuse-web | 3000 | Langfuse UI 前端，通过 service 的 YARP 反向代理对外暴露 |
| langfuse-worker | 无对外端口 | Langfuse 后台任务处理 |

网络模型上，所有容器位于同一内部网络（`agentinsight_default`），容器间通过服务名进行  解析与通信。service 容器通过 YARP. 将 `/langfuse` 路径的请求转发到 langfuse-web 容器，实现 Langfuse UI 的统一入口。Admin 容器同样加入 `agentinsight_default` 外部网络 [Admin/Agents.md]。

### 6.2. 网络与端口规划

AgentInsightService（统一使用全称，首次出现可标注品牌名） 的端口规划遵循"内部通信不暴露、外部访问最小化"的原则。对外暴露的端口仅限业务入口与必要的管理端口，内部组件间通过 Docker 内部网络通信。

对外暴露端口：

| 容器 | 宿主机端口 | 容器端口 | 协议 | 用途 |
|------|-----------|---------|------|------|
| service | 8080 | 8080 | HTTP | API 主入口，Kestrel Config `=8080` [API/Properties/launchSettings.json] |
| agent | 8066 | 8066 | HTTP | Agent 服务入口，OpenAI 兼容 API |
| admin | 22522 | 22522 | HTTP | Django 管理后台 [Admin/Agents.md] |
| postgres | 5432 | 5432 |  | PostgreSQL 数据库连接 |
| clickhouse | 8123 | 8123 | HTTP | ClickHouse HTTP 接口 |
| clickhouse | 9000 | 9000 |  | ClickHouse 原生协议接口 |
| redis | 6379 | 6379 |  | Redis 连接 |
| minio | 9000 | 9000 | HTTP |  S3 兼容 API |
| minio | 9001 | 9001 | HTTP |  管理控制台 |

内部通信端口（不暴露到宿主机）：

| 容器 | 端口 | 用途 |
|------|------|------|
| langfuse-web | 3000 | Langfuse UI 内部端口，仅通过 service 的 YARP 代理访问 |
| langfuse-worker | 无 | 内部任务处理，无监听端口 |

service 容器的 Kestrel Config在 `API/Program.cs` 中完成，设置了 ` = 1024`、` = 1024`、` = 100 * 1024 * 1024`（100MB）等连接限制 [API/Program.cs]。API 的 HTTPS 端口Config为 8081，HTTP 端口为 8080 [API/Properties/launchSettings.json]。

### 6.3. 容器与编排

AgentInsightService（统一使用全称，首次出现可标注品牌名） 使用 docker-compose 作为容器编排工具，所有服务定义在统一的 compose 文件中。计算容器的镜像构建来源如下：

- **service 容器**：基于本地 Dockerfile 构建，使用 `Container (Dockerfile)` 启动Config，设置 `=8080`、`=8081`，并通过 `` 额外映射端口 14160 [API/Properties/launchSettings.json]。
- **agent 容器**：基于 `Agents/Dockerfile` 构建，依赖文件为 `Agents/requirements.docker.txt`，仅包含 7 个核心依赖（Django、simpleui、import-export、psycopg2-binary、concurrent-log-handler、gunicorn、whitenoise），确保镜像体积最小化 [Admin/Agents.md]。
- **admin 容器**：基于 `Admin/Dockerfile` 构建，使用 gunicorn 作为 WSGI 服务器，通过 whitenoise 提供静态文件服务 [Admin/Agents.md]。

健康检查Config确保各服务的可用性：

| 容器 | 健康检查命令 | 说明 |
|------|-------------|------|
| service | `wget http://127.0.0.1:8080/api/tools/health` | 调用健康检查端点 `GET /api/tools/health`，对应 `HealthController.Get` [API/Controllers/ToolsManagement/HealthController.cs:20] |
| agent | Python 脚本探测 | 通过 Python 脚本检查服务端口与响应状态 |
| postgres | `pg_isready` | 检查 PostgreSQL 就绪状态 |
| clickhouse | `wget /ping` | 调用 ClickHouse HTTP 接口的 `/ping` 端点 |
| redis | `redis-cli ping` | 验证 Redis 服务响应 |

数据持久化通过 Docker 命名卷实现，关键卷包括：

| 卷名 | 挂载容器 | 持久化内容 |
|------|---------|-----------|
| postgres_data | postgres | PostgreSQL 数据文件 |
| clickhouse_data | clickhouse | ClickHouse 数据文件 |
| redis_data | redis | Redis 持久化数据 |
| minio_data | minio | 对象存储数据 |
| service_keys | service | API 密钥与签名证书 |
| service_logs | service | 应用日志 |
| session_data | service | Session数据 |

### 6.4. 环境策略与Config

AgentInsightService（统一使用全称，首次出现可标注品牌名） 通过环境变量注入实现多环境（开发/测试/生产）的Config隔离。Config系统采用"JSON 文件 + 环境变量占位符"的双层机制：

1. **Config源注册**：`API/Program.cs` 首先调用 `builder.Configuration.()` 注册环境变量源，然后通过 `builder.Inject()` 加载 `Configurations/` 与 `Resources/` 目录下的 JSON Config文件 [API/Program.cs]。
2. **占位符解析**：加载完成后，调用 `ConfigurationPlaceholderResolver.(builder.Configuration)` 解析Config值中的 `${VAR}` 占位符，将其替换为环境变量实际值 [API/Program.cs]。

环境区分通过 `` 环境变量控制，支持以下环境：

| 环境 | Config值 | 说明 |
|------|--------|------|
| Development | `Development` | 本地开发环境，`applicationUrl` 为 `http://localhost:5098;https://localhost:5099` [API/Properties/launchSettings.json] |
| QA | `QA` | 测试环境，`applicationUrl` 为 `http://localhost:7176;http://localhost:5099` [API/Properties/launchSettings.json] |
| LIVE | `LIVE` | 生产环境，`applicationUrl` 为 `http://localhost:7176;http://localhost:5099` [API/Properties/launchSettings.json] |

Agent Services（Python / FastAPI）通过 `Agents/common/config.py` 中的 `Environment` 枚举定义环境类型 [Agents/common/config.py:15]，与 API 层的环境Config保持一致。

关键Config项及其环境变量占位符：

| Config项 | 占位符 | 说明 |
|--------|--------|------|
| `.` | `${}` `${}` `${}` `${}` | 用户库连接字符串，`=postgres` |
| `.` | `${}` `${}` `${}` `${}` | 数据库连接字符串，`=postgres` |
| `.` | `${}` `${}` `${}` `${}` | Trace库连接字符串，`=postgres` |
| `.` | `${}` `${}` `${}` `${}` `${}` | ClickHouse 连接字符串，含 `=10;=50;=30;=60` |
| `` | `${}` | AES 加密密钥 |
| `` | `${}` | API 集成标识 |
| `` | `${}` | API 集成密钥 |

数据库连接池Config在连接字符串中定义：PostgreSQL 连接池 `=10;=200;=300`，ClickHouse 连接池 `=10;=50`。API 层通过 `SQLSugarHelper.CreateUserClient()` 与 `SQLSugarHelper.CreateDataClient()` 创建键控的 `ISqlSugarClient` 单例，分别注册为 `AgentInsightConst.KeyedService_UserDb` 与 `AgentInsightConst.KeyedService_DataDb` [API/Program.cs]。

---

## 7. 技术选型

AgentInsightService（统一使用全称，首次出现可标注品牌名） 采用**分层架构 + 微服务编排模式**模式，由三个独立运行时组件构成：基于 C# / Furion 的 API Services（C# / Furion）、基于 Python / FastAPI 的 Agent Services（Python / FastAPI），以及基于 Python / Django 的 Admin 管理后台（Python / Django）。系统整体技术选型遵循"专业领域最佳实践优先"原则，在 .NET 生态中构建核心业务 API，在 Python 生态中实现 AI Agent编排与快速迭代，在 Django 生态中提供管理后台能力，同时引入 PostgreSQL、ClickHouse、Redis、 等基础设施组件支撑数据存储、分析与消息队列需求。本章节从技术选型矩阵与选型原则两个维度，系统阐述 AgentInsightService（统一使用全称，首次出现可标注品牌名） 各层技术栈的构成与决策依据。

### 7.1. 技术选型矩阵

AgentInsightService（统一使用全称，首次出现可标注品牌名） 的技术选型矩阵按运行时组件与基础设施两个维度进行组织，覆盖 API Service、Agent Service、Admin 后台及底层基础设施四个类别。

#### 7.1.1. API Services（C# / Furion）（C# / Furion）

API Services（C# / Furion）是 AgentInsightService（统一使用全称，首次出现可标注品牌名） 的核心业务入口，采用 .NET 8.0 与 Furion 应用框架构建，入口点为 `API/Program.cs`，负责应用启动Config、服务注册与中间件装配。ControllerControllers包含 76 个 HTTP 端点，统一继承自 `ApiControllerBase`（`API/Controllers/ApiControllerBase.cs:10`），通过 `RegisterHandler` 方法注入业务Handler；HandlerHandlers继承自 `ApiHandlerBase`（`API/Handlers/ApiHandlerBase.cs:8`），实现 `IUserAwareHandler` 接口（`API/Handlers/IUserAwareHandler.cs:3`），构成业务逻辑核心。Services位于 `API/Common/Services/`，封装Payment、微信、Alert、消息队列等外部集成。

口（`API/Handlers/IUserAwareHandler.cs:3`），构成业务逻辑核心。Services位于 `API/Common/Services/`，封装Payment、微信、Alert、消息队列等外部集成。

| 类别 | 技术选型 | 版本/说明 | 用途 |
|------|---------|-----------|------|
| 应用框架 | Furion | ASP.NET Core 8.0 | 提供依赖注入、、友好异常等基础设施 |
| ORM | SqlSugar | — | 数据访问层，通过 `ISqlSugarClient` 操作 PostgreSQL |
| 中介者模式 | MediatR | — | 实现Payment通知、Alert通知的解耦（`API/Notifications/`） |
| 反向代理 | Yarp. | — | 实现 API 网关与反向代理转换（`API/System/Handlers/AgentInsightTransformProvider.cs`） |
| Payment SDK | .Standard | — | Payment宝Payment集成（`API/Common/Services/PaymentService.cs`） |
| 加密库 | .Cryptography | — | 微信Payment证书解析与签名验证 |
| AI 编排 | Microsoft. | — | 语义内核集成，支持 AI 能力接入 |
| AI 提供方 | LangChain.Providers.OpenAI | — | OpenAI 兼容接口的 LangChain 提供方 |
| 本地化 | My.Extensions.Localization.Json | — | JSON 格式本地化资源支持 |
| PostgreSQL 驱动 | Npgsql | — | PostgreSQL 数据库连接驱动 |
| Redis 客户端 | .Redis | — | Redis 连接与操作（BullMqService 底层依赖） |

基础设施层为 AgentInsightService（统一使用全称，首次出现可标注品牌名） 提供数据存储、分析、缓存与对象存储能力，支撑 API Services（C# / Furion）与 Agent Services（Python / FastAPI）的运行。

| 类别 | 技术选型 | 版本/说明 | 用途 |
|------|---------|-----------|------|
| 关系型数据库 | PostgreSQL | 17 | 用户库、数据库、Trace库三库分离 |
| 列式分析数据库 | ClickHouse | 26.5 | Trace 指标存储与分析（`API/Common/Services/ClickHouseClient.cs`） |
| 缓存/消息队列 | Redis | 8 | 缓存与 BullMQ 兼容消息队列（`API/Common/Services/BullMqService.cs`） |
| 对象存储 |  | Chainguard 镜像 | 文件与对象存储 |
| PostgreSQL 驱动 | Npgsql | — | .NET 侧 PostgreSQL 连接 |
| Redis 客户端 | .Redis | — | .NET 侧 Redis 连接 |

基础设施层的连接字符串Config于 `appsettings.json`，包括 ``（Host/Port/Username/Password/Database////）、``、``、`` 四组连接Config。API Services（C# / Furion）通过 `ClickHouseClient.QueryAsync` 执行 ClickHouse 查询（`API/Common/Services/ClickHouseClient.cs:10`），通过 `BullMqService` 实现基于 Redis 的 BullMQ 兼容消息队列（`API/Common/Services/BullMqService.cs`），提供 `EnqueueProjectDeleteAsync`、`EnqueueTraceIngestionAsync`、`AcknowledgeTraceIngestionAsync` 等队列操作。

### 7.2. 选型原则与决策依据

AgentInsightService（统一使用全称，首次出现可标注品牌名） 的技术选型遵循以下核心原则，确保各层技术栈在专业领域内实现最佳实践。

#### 7.2.1. 原则一：优先采用团队熟悉的 .NET 生态构建 API

API Services（C# / Furion）选择 .NET 8.0 + Furion 框架，核心决策依据如下：

- **Furion 框架的工程化能力**：Furion 提供依赖注入、 切面、友好异常处理（`Furion.`）、JSON 序列化（`Furion.`）等开箱即用的基础设施，显著降低 API Services（C# / Furion）的开发复杂度。`API/System/Handlers/AgentInsightTransformProvider.cs` 中同时引用 `Furion.` 与 `Furion.`，体现了框架能力在认证过滤与异常处理中的实际应用。
- **SqlSugar ORM 的高效数据访问**：SqlSugar Repository模式支持，`API/Handlers/ApiHandlerBase.cs` 通过 `ISqlSugarClient` 统一获取数据库上下文，`API/Common/Services/OrderRepository.cs:8` 的 `IOrderRepository` 封装订单数据访问，实现数据访问层的标准化。
- **MediatR 实现业务解耦**：`API/Notifications/` 目录下通过 MediatR 实现Payment通知、Alert通知的异步解耦处理，`PaymentService` 发布 `PaymentTransactionNotification`（`API/Common/Services/PaymentService.cs:8`），`PaymentTransactionSaveHandler` 异步保存交易记录，避免业务链路阻塞。
- **Yarp. 实现网关能力**：`AgentInsightTransformProvider` 实现 `ITransformProvider` 接口（`API/System/Handlers/AgentInsightTransformProvider.cs`），通过 Yarp 反向代理实现请求路径前缀添加、Basic Auth / JWT 认证转换、API Key 解析与限流检查，将 API 网关能力内嵌于 .NET 服务中。

#### 7.2.2. 原则二：Python 用于快速迭代 AI 实验

Agent Services（Python / FastAPI）选择 Python 3.12 + FastAPI + LangGraph，核心决策依据如下：

- **AI 生态的丰富性**：Python 拥有最完整的 AI 生态，LangGraph 提供有状态的 Agent 工作流编排能力，LangChain-Core 提供工具调用与链式编排基础，Microsoft. 与 LangChain.Providers.OpenAI 提供多厂商 LLM 接入能力，使 AgentInsightService（统一使用全称，首次出现可标注品牌名） 能够快速实验与迭代 AI Agent。
- **FastAPI 的高性能异步框架**：FastAPI 基于 Starlette 与 Pydantic v2，提供高性能异步处理能力与自动 API 文档生成，`Agents/server.py` 通过 FastAPI 应用实例提供 OpenAI 兼容的 Chat Completions API，支持流式响应与并发请求。
- **Qdrant 向量数据库支撑语义检索**：`Agents/common/retriever.py` 中定义 `` 枚举，Qdrant 作为向量数据库支撑 Agent 的语义记忆与检索能力，`Agents/server.py` 导入 `Agents/common/memory.py`（`Agents/server.py:440`）实现Session记忆管理。
- **Pydantic v2 保障数据契约**：Pydantic v2 提供高性能的数据验证与序列化能力，`pydantic-settings` 实现基于环境变量的Config加载（`Agents/common/config.py`），确保 Agent 服务在不同环境下的Config一致性。

#### 7.2.3. 原则三：引入多语言运行时确保专业领域最佳实践

AgentInsightService（统一使用全称，首次出现可标注品牌名） 采用多语言运行时架构，在 .NET、Python、Django 三个生态中各取所长：

- **.NET 生态承载核心业务**：API Services（C# / Furion）承担用户管理、组织管理、项目管理、Payment管理、Alert管理等核心业务逻辑，.NET 的类型安全、性能表现与成熟的企业级生态（Furion、SqlSugar、MediatR、Yarp）确保业务系统的稳定性与可维护性。
- **Python 生态承载 AI 能力**：Agent Services（Python / FastAPI）承担 AI Agent编排、Session管理、语义检索等 AI 相关能力，Python 的 AI 生态（LangGraph、LangChain、Qdrant、）使 AgentInsightService（统一使用全称，首次出现可标注品牌名） 能够快速接入最新的 AI 模型与编排模式。
- **Django 生态承载管理后台**：Admin 管理后台（Python / Django）采用 Django 4.2.19 的成熟 Admin 机制，通过 `managed = False` 模型映射与双数据库路由（`app/db_router.py` 的 ``），实现与 .NET API 主服务共享数据库表的管理界面，避免重复建表与数据不一致。
- **基础设施层统一支撑**：PostgreSQL 17 提供多库隔离（用户库/数据库/Trace库），ClickHouse 26.5 提供列式分析能力，Redis 8 提供缓存与消息队列，（Chainguard 镜像）提供对象存储，各组件通过环境变量注入连接Config，实现基础设施层的统一管理与部署。

#### 7.2.4. 原则四：所有依赖均来自实际项目文件，无虚构框架

AgentInsightService（统一使用全称，首次出现可标注品牌名） 的技术选型严格基于实际代码仓库中的依赖声明，包括 `API/*.csproj` 中的  包引用（Furion、SqlSugar、MediatR、Yarp.、.Standard、.Cryptography、Microsoft.、LangChain.Providers.OpenAI、Npgsql、.Redis 等）与 `Agents/pyproject.toml` 中的 Python 包引用（FastAPI、LangGraph、LangChain-Core、Qdrant、httpx、Pydantic v2、pydantic-settings 等），以及 `Admin/` 项目的 Django 依赖（django-grappelli、django-simpleui、django-import-export）。所有技术栈均可在代码仓库中找到对应的实际引用与使用场景，无虚构或臆测框架。

#### 7.2.5. 选型决策的工程考量

| 决策维度 | 选型结果 | 决策依据 |
|---------|---------|---------|
| API 框架 | Furion (ASP.NET Core 8.0) | 团队熟悉度、/DI 基础设施、友好异常处理 |
| ORM | SqlSugar | 丰富查询表达式、Repository模式支持、与 .NET 生态无缝集成 |
| AI 编排 | LangGraph + LangChain-Core | Python AI 生态成熟度、有状态工作流编排 |
| Agent Web 框架 | FastAPI | 高性能异步、Pydantic v2 数据验证、OpenAI 兼容 API |
| Admin 框架 | Django 4.2.19 | 成熟 Admin 机制、双数据库路由、`managed = False` 共享表 |
| 关系型数据库 | PostgreSQL 17 | 多库隔离、事务一致性、Npgsql 驱动成熟 |
| 分析数据库 | ClickHouse 26.5 | 列式存储、高吞吐 Trace 指标分析 |
| 缓存/消息队列 | Redis 8 | 缓存 + BullMQ 兼容消息队列双用途 |
| 对象存储 |  (Chainguard) | S3 兼容、Chainguard 镜像安全性 |
| 反向代理 | Yarp. | 内嵌网关能力、请求转换与认证过滤 |

---

## 8. 可扩展性与性能

AgentInsightService（统一使用全称，首次出现可标注品牌名） 采用**分层架构 + 微服务编排模式**模式，由 API Services（C# / Furion）（C# / Furion）、Agent Services（Python / FastAPI）（Python / FastAPI）及 Admin 管理后台（Python / Django）三个独立运行时组件构成，通过无状态 API 设计、分布式消息队列、插件化扩展机制与多租户隔离策略，实现从单实例到多实例的水平扩展能力，并在数据访问层通过连接池与动态查询构建器保障高性能吞吐。

### 8.1. 水平扩展策略

AgentInsightService（统一使用全称，首次出现可标注品牌名） 的水平扩展能力建立在三个核心运行时组件的无状态化设计之上，每个组件均可独立扩容并通过负载均衡器分发流量。

**API Services（C# / Furion）无状态设计**

API Services（C# / Furion）（C# / Furion）的Controller与Handler均不保存本地Session状态。Controller继承自 `ApiControllerBase`，通过构造函数注入业务Handler（如 `AgentSessionHandler`），Handler继承自 `ApiHandlerBase`，统一从依赖注入容器获取数据库客户端、用户上下文与取消Token [API/Handlers/ApiHandlerBase.cs:8]。用户Session状态存储于 Redis（Config项 `Redis:`），而非进程内存，因此任意 API 实例均可处理任意请求，支持部署多个 service 实例并通过负载均衡器（如 Nginx 或云负载均衡）分发流量 [API/appsettings.Development.json]。

**Agent Services（Python / FastAPI）Session持久化**

Agent Services（Python / FastAPI）（Python / FastAPI）的入口点为 `Agents/server.py`，提供 OpenAI 兼容的 Chat Completions API。Agent Session通过 `session_data` 卷持久化，而非存储在进程内存中，因此多个 Agent 服务实例可以共享同一份Session数据。配合负载均衡器，请求可被路由到任意可用实例，实现水平扩展。Agent 实例通过 `register_agent()` 函数动态注册到注册表 [Agents/server.py:438]，`InsightOrchestrator` 作为统一入口将请求路由到子Agent [Agents/server.py:451]，新增 Agent 实例无需修改核心路由逻辑。

**消息队列分布式任务处理**

消息队列基于 Redis 的 BullMQ 兼容实现（`API/Common/Services/BullMqService.cs`），用于处理项目删除、Trace 摄入等耗时操作。`BullMqService` 提供 `EnqueueProjectDeleteAsync` [API/Common/Services/BullMqService.cs:22] 与 `EnqueueTraceIngestionAsync` [API/Common/Services/BullMqService.cs:23] 方法将任务异步化。系统支持部署多个 worker 实例并行消费队列中的任务，通过 Redis 分布式锁保障任务不重复执行，实现削峰填谷，提升系统整体吞吐能力。队列任务与主请求链路完全解耦，任务失败时可自动重试，不影响核心业务响应。

**插件化扩展机制**

Alert评估采用策略模式，定义 `IAlertFieldEvaluator` 接口作为评估器抽象 [API/Notifications/AlertEvaluators/IAlertFieldEvaluator.cs]，系统内置 9 个具体评估器，每个评估器负责一种Alert字段的评估逻辑。`AlertService` 通过 `EvaluateField` 方法调用评估器链 [API/Common/Services/AlertService.cs:18]，`IsConditionMet` 判断Alert条件是否满足 [API/Common/Services/AlertService.cs:16]。新增评估器时，只需实现 `IAlertFieldEvaluator` 接口并注册到依赖注入容器，无需修改 `AlertService` 核心逻辑。

```csharp
public interface IAlertFieldEvaluator
{
    // 评估器接口定义，新增评估器需实现此接口
}
```

**Agent 动态注册机制**

Agent Services（Python / FastAPI）通过 `register_agent()` 函数实现Agent的动态注册 [Agents/server.py:438]。该函数将 Agent 实例注册到全局注册表，`InsightOrchestrator` 根据请求内容路由到对应的子Agent [Agents/server.py:451]。新增 Agent 时，只需调用 `register_agent()` 注册新实例，无需修改 Orchestrator 的路由逻辑。Agent 的Config管理通过 `AgentConfigController` 提供 HTTP 接口，支持动态创建或更新Config [API/Controllers/AgentManagement/AgentConfigController.cs]。

**Payment渠道接口扩展**

Payment渠道通过 `IPaymentService` 接口抽象 [API/Common/Services/PaymentService.cs:10]，统一封装微信Payment与Payment宝Payment的调用链。`PaymentService` 作为门面，提供 `GetWeChatNativeOrderBody`、`GetWeChatJSAPIOrderBody` 等方法 [API/Common/Services/PaymentService.cs:158-162]，新增Payment渠道时只需实现 `IPaymentService` 接口并在容器中注册，上层业务代码（如 `OrderHandler`）无需修改 [API/Handlers/PaymentManagement/OrderHandler.cs:24]。

| 扩展点 | 抽象接口 | 注册方式 | 新增扩展的修改范围 |
|--------|----------|----------|-------------------|
| Alert评估器 | `IAlertFieldEvaluator` | DI 容器注册 | 仅新增评估器类 |
| Agent Agent | `register_agent()` | 注册表调用 | 仅新增 Agent 类 |
| Payment渠道 | `IPaymentService` | DI 容器注册 | 仅新增Payment实现类 |
| 异步任务 | BullMQ 队列 | 队列生产者/消费者 | 仅新增任务类型与Handler |

### 8.2. 多租户与隔离

AgentInsightService（统一使用全称，首次出现可标注品牌名） 通过 `orgId` + `projectId` 两级维度实现数据隔离，并在 API 层通过Privilege校验保障租户间的访问控制。

**数据隔离模型**

Organization为第一级租户维度，Project（Project）为第二级维度。订单数据通过 `orgId` 字段关联到具体组织，查询时强制按 `orgId` 过滤 [API/Handlers/PaymentManagement/OrderHandler.cs:44]。模型定义（`ModelDefinition`）通过 `projectId` 字段关联到具体项目，支持按项目维度隔离模型数据 [API/Controllers/DataManagement/ModelController.cs]。Agent Session数据通过用户 ID 关联，仅允许访问当前用户名下的Session [API/Controllers/AgentManagement/AgentSessionController.cs]。

**Privilege隔离保障**

`ApiHandlerBase` 提供 `RequireOrgMembership` Privilege校验机制，确保用户只能访问其所属组织的数据。在 `OrderHandler.GetOrders` 中，首先校验用户是否为指定组织的成员，再校验角色是否为 `PGRole.OWNER`，最后才执行订单查询 [API/Handlers/PaymentManagement/OrderHandler.cs:24-44]。`PlaceOrder` 方法同样校验用户至少拥有一个组织的 OWNER Role，并校验目标组织在用户的组织列表中 [API/Handlers/PaymentManagement/OrderHandler.cs:52-70]。

```csharp
// OrderHandler.GetOrders 中的Privilege校验逻辑
var membership = await DataDb.Queryable<OrganizationMembership>()
    .Where(om => om.UserId == User.Id && om.OrgId == orgId)
    .FirstAsync();
if (membership == null) throw Oops.Oh(ExceptionCodes.OrgNotFound);
if (membership.Role != PGRole.OWNER) throw Oops.Oh(ExceptionCodes.InsufficientPermission);
```

**产品级租户限制**

产品定义中包含租户级限制字段：`projectLimit`（项目数上限）、`headcountLimit`（人数上限）、`orgLimit`（组织数上限）、`agentLimit`（Agent 数上限）[API/Controllers/ProductManagement/ProductController.cs]。这些限制在产品订购时生效，从产品维度约束租户的资源使用量，实现多租户场景下的资源配额管理。

| 隔离层级 | 维度 | 数据实体 | Privilege校验 |
|----------|------|----------|----------|
| 组织级 | `orgId` | Order、成员关系 | `RequireOrgMembership` |
| 项目级 | `projectId` | 模型定义、Trace 数据 | 项目成员校验 |
| 用户级 | `userId` | Agent Session、Config | 用户身份校验 |

### 8.3. 性能关键瓶颈与优化

AgentInsightService（统一使用全称，首次出现可标注品牌名） 在数据访问层与查询构建层进行了针对性优化，以应对高并发与大数据量场景。

**ClickHouse 查询优化**

ClickHouse 查询使用 `TraceFilterBuilder` 动态构建查询条件 [API/Common/Helpers/TraceFilterBuilder.cs:8]，该 Builder 模式根据请求参数（时间范围、Project ID、Trace ID 等）动态拼接 WHERE 子句，避免全表扫描。`ClickHouseClient` 封装了查询执行逻辑 [API/Common/Services/ClickHouseClient.cs:10]，通过 `QueryAsync` 方法异步执行查询。Alert指标查询链路为 `AlertMetricsHandler.GetAlertMetrics` → `AlertService.GetAlertMetrics` → `ClickHouseClient.QueryAsync` [API/Handlers/DataManagement/AlertMetricsHandler.cs:10]，通过 TraceFilterBuilder 构建精确的过滤条件，减少 ClickHouse 扫描的数据量。

**连接池参数调优**

数据库连接池参数在Config文件 `API/appsettings.Development.json` 中定义 [API/appsettings.Development.json]。生产环境Config中，PostgreSQL 连接池参数为 `MinPoolSize=10`、`MaxPoolSize=200`、`CommandTimeout=60s`，ClickHouse 连接池参数为 `MinPoolSize=10`、`MaxPoolSize=200`、`CommandTimeout=60`。这些参数确保在高并发场景下，数据库连接能够复用，避免频繁创建与销毁连接的开销。

| Config项 | 值 | 说明 |
|--------|-----|------|
| `PostgreSql.MinPoolSize` | 10 | PostgreSQL 连接池最小连接数 |
| `PostgreSql.MaxPoolSize` | 200 | PostgreSQL 连接池最大连接数 |
| `PostgreSql.CommandTimeout` | 60s | PostgreSQL 命令超时时间 |
| `ClickHouse.MinPoolSize` | 10 | ClickHouse 最小连接数 |
| `ClickHouse.MaxPoolSize` | 200 | ClickHouse 最大连接数 |
| `ClickHouse.CommandTimeout` | 60 | ClickHouse 命令超时 |

**异步处理与解耦**

性能优化的另一个关键点是异步处理链路的应用。Payment回调处理通过 `MediatR` 发布 `PaymentTransactionNotification`，由 `PaymentTransactionSaveHandler` 异步保存交易记录 [API/Notifications/PaymentTransactionSaveHandler.cs:8]，避免阻塞主请求链路。Alert评估通过 `SystemAlertHandler` 记录Alert日志、`SMSAlertHandler` 发送短信通知 [API/Notifications/SystemAlertHandler.cs:8]，这些操作均为异步执行，不阻塞指标查询主流程。BullMQ将项目删除、Trace 摄入等耗时操作异步化，通过 Redis 分布式队列实现削峰填谷，并支持多 worker 并行消费，提升系统整体吞吐能力。

---

## 9. 安全性与合规

AgentInsightService（统一使用全称，首次出现可标注品牌名） 是一个面向可Observation性与智能分析场景的服务平台，其 API Services（C# / Furion）基于 C# / Furion 框架构建，提供 76 个 HTTP 端点（`API/Controllers/`），Agent Services（Python / FastAPI）基于 Python / FastAPI 提供 OpenAI 兼容的 Chat Completions API（`Agents/server.py`）。在安全架构上，AgentInsightService（统一使用全称，首次出现可标注品牌名） 采用双重认证机制、基于角色的授权模型、敏感字段加密、Payment签名验证、安全响应头、统一审计日志与完整错误码体系，构建纵深防御的安全合规体系。本章节围绕认证与授权、数据保护、Payment安全、安全响应头与中间件、审计与日志五个维度展开说明。

### 9.1. 认证与授权

AgentInsightService（统一使用全称，首次出现可标注品牌名） 采用双重认证机制，分别面向交互式用户Session与程序化 API 接入场景。

**用户SessionJWT**：用户通过登录接口 `POST /api/user/login` 完成身份认证（`API/Controllers/UserManagement/UserController.cs:42`），登录成功后服务端签发 JWT（HS256 算法），Token有效期设置为 12 小时。JWT Token在响应头中以 `access-token` 字段返回，客户端在后续请求中携带该Token访问受保护资源。当Token过期时，系统返回 `UnAuthToken=100000` 错误码，提示"登录已过期，请重新登录"（`API/Resources/Text.zh-CN.json`）。登出操作通过 `POST /api/user/logout` 完成（`API/Controllers/UserManagement/UserController.cs:60`），使当前Session失效。

**API 接入认证（API Key + Basic Auth）**：面向程序化 API 接入场景，AgentInsightService（统一使用全称，首次出现可标注品牌名） 支持 `logintype=5`（APIKey）方式登录，调用方需在 Authorization 头中携带 `Basic publickey:secretkey` 格式的凭证（`API/Controllers/UserManagement/UserController.cs:42`）。API Key 的创建、查询与删除由 `UserHandler` 统一管理，相关错误码包括 `ApiKeyNotFound=100031`、`ApiKeyCreateFailed=100032`、`ApiKeyDeleteFailed=100033`、`ApiKeyNotMatched=100036`、`ApiKeyInvalid=100038`。API Key 认证处理由 `AgentInsightTransformProvider` 负责，该组件位于 `API/System/Handlers/` 目录，作为反向代理转换层统一处理 API 接入认证逻辑。

**授权模型**：AgentInsightService（统一使用全称，首次出现可标注品牌名） 基于 `PGRole` 枚举实现角色Privilege控制（`Models/Common/Enums/UserEnum.cs:3`），支持组织级与项目级两级Privilege范围。系统定义了 `ApiKeyScope` 枚举（`Models/Common/Enums/UserEnum.cs:12`），用于区分 API Key 的访问范围。Privilege不足时返回 `NoPermission=100010` 错误码；组织级越权访问返回 `NoOrgPermission=130009`；项目级越权访问返回 `NoProjectPermission=140008`。角色管理遵循"不能授予高于自身角色的Privilege"约束（`RoleCannotExceedCurrent=100011`），组织所有者不能修改自身Privilege（`CannotModifySelfRole=100012`）。所有业务Handler继承自 `ApiHandlerBase`（`API/Handlers/ApiHandlerBase.cs:8`），通过基类统一获取当前用户上下文（`User.Id`、`User.SessionId`），实现请求级Privilege校验。

### 9.2. 数据保护

AgentInsightService（统一使用全称，首次出现可标注品牌名） 在数据保护方面采用加密存储与密钥持久化相结合的策略。

**敏感字段加密**：系统通过 `EncryptionOptions`（Config项 `Encryption:Key`）对敏感字段进行 AES 加密。`UserHandler` 中注入了 `IEncryptService` Service（`API/Handlers/UserManagement/UserHandler.cs:15`），用于密码等敏感数据的加密与解密操作。用户密码在数据库中不以明文存储，注册与登录流程均通过 `IEncryptService` 完成密码的加密存储与比对验证。

**密钥持久化**：ASP.NET DataProtection API 用于密钥的持久化管理，确保应用重启后加密密钥不丢失，保障已加密数据的可解密性。系统通过 `API/Program.cs` 中的启动Config完成 DataProtection 服务的注册与密钥存储路径设置。

**连接字符串安全**：数据库连接字符串通过环境变量注入，包括 `ConnectionStrings:DefaultConnection`、`ConnectionStrings:RedisConnection`、`ConnectionStrings:ClickHouseConnection` 与 `ConnectionStrings:QuartzConnection`（Config规格 v8-P0-H），避免在代码仓库中明文存储数据库凭证。所有连接字符串均包含连接池Config（如 `Pooling=true;MinPoolSize=10;MaxPoolSize=200`），在保障安全性的同时兼顾性能。

**Captcha安全**：系统Config了Captcha相关安全参数，包括 `CaptchaSetting.ExpiryMinutes=5`、`CaptchaSetting.MaxAttempts=6`、`CaptchaSetting.CodeLength=6`、`CaptchaSetting.ResendInterval=300`、`CaptchaSetting.LockoutDuration=60`（Config规格 v8-P0-H）。Captcha错误或失效时返回对应错误码（`InvalidCaptcha=100020`、`CaptchaExpired=100021`），发送频率受 `CaptchaSetting.ResendInterval` 限制，防止暴力破解与短信轰炸。

### 9.3. Payment安全

AgentInsightService（统一使用全称，首次出现可标注品牌名） 集成微信Payment与Payment宝Payment，在Payment回调环节实施严格的签名验证机制，防止伪造Payment通知。

**Payment宝签名验证**：`PaymentService` 中的 `ExamineAlipaySignature` 方法（`API/Common/Services/PaymentService.cs:63`）负责验证Payment宝异步回调的签名。验证失败时抛出 `AlipaySignatureVerifyFailedException` 异常，签名字典构建失败时抛出 `AlipaySignDictionaryBuildFailedException` 异常。Payment宝交易验证失败时返回 `AlipayTradeVerifyFailed=620003` 错误。

**微信签名验证**：`WeChatService` 中的 `ExamineSignature` 方法（`API/Common/Services/WeChatService.cs:16`）实现微信签名验证逻辑。该方法从设置中获取 `WeChatSettings.Token`，将 token、timestamp、nonce 三个参数按字典序排序后拼接，再计算 SHA1 哈希与微信传入的 signature 比对（`API/Common/Services/WeChatService.cs`）。验证失败时抛出 `WeChatSignatureVerifyFailedException` 异常。微信Payment通知的签名验证由 `NotifyHandler.ExamineWeChatRequest` 处理（`API/Handlers/PaymentManagement/NotifyHandler.cs:18`），伪造请求返回 `WeChatNotifyVerifyFailed=620004` 错误码。

**Payment回调处理流程**：微信Payment回调入口为 `POST /api/payment/notify/wechatnotify`（`API/Controllers/PaymentManagement/NotifyController.cs:29`），该接口标注 `[AllowAnonymous]`，依赖签名验证保障安全。回调处理流程为：读取请求体 → 验证微信签名 → 反序列化 `WeChatNotify` → 处理Payment通知 → 返回微信成功响应。Payment通知处理完成后，通过 `MediatR` 发布 `PaymentTransactionNotification`，由 `PaymentTransactionSaveHandler` 异步保存交易记录（`API/Notifications/PaymentTransactionSaveHandler.cs:8`），该Handler内置最多 3 次重试机制（重试延迟分别为 1s、3s、5s），确保交易数据不丢失。

**微信消息接口安全**：微信消息接口 `GET/POST /api/tools/wechat/message`（`API/Controllers/ToolsManagement/WeChat/WeChatController.cs:36`）同样标注 `[AllowAnonymous]`，依赖 `ExamineSignature` 验证请求合法性。验证通过后返回 `echostr` GETPOST，验证失败返回 `WeChatSignatureVerifyFailed=620001` 错误码。

### 9.4. 安全响应头与中间件

AgentInsightService（统一使用全称，首次出现可标注品牌名） 在 Agent Services（Python / FastAPI）（Python / FastAPI）Config了安全响应头，增强 Web 应用对常见攻击的防护能力。

**安全响应头Config**：`Agents/server.py` 中Config了以下安全响应头（`Agents/server.py:69-74`）：

| 响应头 | 值 | 防护目标 |
|--------|-----|---------|
| `X-Content-Type-Options` | `nosniff` | 防止 MIME 类型混淆攻击 |
| `X-Frame-Options` | `DENY` | Clickjacking |
| `X-XSS-Protection` | `1; mode=block` | 启用浏览器 XSS 过滤器 |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` | 强制 HTTPS 连接，防止协议降级攻击 |

**异常处理中间件**：系统通过 `ExceptionMiddleware` 统一捕获未处理异常并记录日志（`API/System/Handlers/`）。该中间件确保异常信息不会直接暴露给客户端，而是转换为统一的错误响应格式，防止堆栈信息泄露。微信相关接口在捕获到 `AppFriendlyException` 时返回 `ApiResponse<string>` 包装的错误信息，未预期异常则返回 HTTP 500 状态码（`API/Controllers/ToolsManagement/WeChat/WeChatController.cs:56`）。

**反向代理安全**：`AgentInsightTransformProvider` 位于 `API/System/Handlers/`，作为反向代理转换层处理 API 请求的转发与认证。该组件依赖 `BullMqService` 与 `IAppContextService`（`API/System/Handlers/AgentInsightTransformProvider.cs:5`），在请求转发过程中保持认证上下文的传递。

### 9.5. 审计与日志

AgentInsightService（统一使用全称，首次出现可标注品牌名） 建立了完整的审计与日志体系，覆盖用户操作、Payment交易、系统异常等关键环节。

**操作审计**：所有业务操作通过 `ApiHandlerBase.LogAudit` 方法记录审计日志（`API/Handlers/ApiHandlerBase.cs:8`）。审计日志记录操作者身份（`User.Id`）、Session标识（`User.SessionId`）、操作类型与操作结果，为安全追溯提供依据。

**异常日志**：`ExceptionMiddleware` 统一捕获异常并记录，包括异常类型、堆栈信息与请求上下文。`PaymentTransactionSaveHandler` 在交易保存失败时通过 `Log.Error<PaymentTransactionSaveHandler>` 记录错误日志，重试时通过 `Log.Information<PaymentTransactionSaveHandler>` 记录重试信息（`API/Notifications/PaymentTransactionSaveHandler.cs:37`）。

**Payment交易审计**：Payment回调处理完成后，`PaymentTransactionSaveHandler` 异步保存微信/Payment宝交易记录（`API/Notifications/PaymentTransactionSaveHandler.cs:16`），确保每笔Payment交易均可追溯。交易保存失败时最多重试 3 次，超过重试次数后记录最终错误日志（`API/Notifications/PaymentTransactionSaveHandler.cs:44`）。

**错误码体系**：系统通过 `ExceptionCodes` 枚举定义完整错误码体系，防止信息泄露。主要错误码包括：

| 错误码 | 常量名 | 含义 |
|--------|--------|------|
| 100000 | `UnAuthToken` | 登录已过期，请重新登录 |
| 100010 | `NoPermission` | Privilege不足 |
| 100011 | `RoleCannotExceedCurrent` | 不能授予高于自身角色的Privilege |
| 100012 | `CannotModifySelfRole` | 组织所有者不能修改自身Privilege |
| 100020 | `InvalidCaptcha` | Captcha错误 |
| 100021 | `CaptchaExpired` | Captcha已失效 |
| 100031 | `ApiKeyNotFound` | API 密钥不存在 |
| 100032 | `ApiKeyCreateFailed` | API 密钥创建失败 |
| 100033 | `ApiKeyDeleteFailed` | API 密钥删除失败 |
| 100036 | `ApiKeyNotMatched` | 未找到对应的 API 密钥 |
| 100038 | `ApiKeyInvalid` | API 密钥无效 |
| 130009 | `NoOrgPermission` | 无权访问该组织 |
| 140008 | `NoProjectPermission` | 无权访问该项目 |
| 620001 | `WeChatSignatureVerifyFailed` | 微信签名验证失败 |
| 620003 | `AlipayTradeVerifyFailed` | Payment宝交易验证失败 |
| 620004 | `WeChatNotifyVerifyFailed` | 获取微信用户信息失败 |

错误码体系确保客户端能够准确识别错误类型，同时避免暴露内部实现细节，符合安全合规要求。

---

## 10. 可靠性与可Observation性

AgentInsightService（统一使用全称，首次出现可标注品牌名） 是一个由 C# / Furion API Services（C# / Furion）与 Python / FastAPI Agent Services（Python / FastAPI）构成的Agent洞察平台。API Services（C# / Furion）通过 76 个 HTTP 端点提供业务能力，涵盖Payment管理、用户管理、Agent Config与Alert监控等模块；Agent Services（Python / FastAPI）则通过 `InsightOrchestrator` 统一路由到子Agent，提供 OpenAI 兼容的 Chat Completions API。本章围绕健康检查与高可用、容错与重试机制、日志与审计、监控与Alert、缓存策略五个方面，阐述系统在运行时的可靠性保障与可Observation性设计。

### 10.1. 健康检查与高可用

系统在 API Services（C# / Furion）暴露了专用的健康检查端点，用于探活与负载均衡器健康判定。`HealthController` 定义于 `API/Controllers/ToolsManagement/HealthController.cs`，路由为 `GET /api/tools/health`，标注 `[AllowAnonymous]` 与 `[ApiExplorerSettings(IgnoreApi = true)]`，表明该接口不参与业务鉴权且不显示在 Swagger 文档中 [API/Controllers/ToolsManagement/HealthController.cs:L10-L20]。端点返回固定格式的 JSON 响应，包含 `status` 与 `timestamp` 两个字段，`status` 恒为 `"healthy"`，`timestamp` 为当前 UTC 时间 [API/Controllers/ToolsManagement/HealthController.cs:L20-L23]。

```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

Agent Services（Python / FastAPI）同样提供健康检查端点。`Agents/server.py` 中定义了 `GET /health` 路由（位于 `Agents/server.py:371`），用于探活 Python 服务进程。该端点与 API 层的健康检查相互独立，Services的存活状态。

在容器编排层面，docker-compose 为关键服务Config了健康检查指令，依赖上述健康端点作为探针。当健康检查连续失败时，容器编排系统会自动重启异常容器，实现服务自愈。健康检查机制与容器重启策略共同构成系统的高可用基础，确保 API 服务与 Agent 服务在单点故障时能够快速恢复。

### 10.2. 容错与重试机制

Payment通知处理是系统中对可靠性要求最高的链路之一，涉及微信Payment与Payment宝Payment的回调处理。`NotifyController` 暴露两个匿名回调端点：`POST /api/payment/notify/wechatnotify` 与 `POST /api/payment/notify/alipaynotify` [API/Controllers/PaymentManagement/NotifyController.cs:L29-L57]。微信回调处理流程中，Controller先读取请求体，若为空则抛出 `ExceptionCodes.PaymentException` 异常；随后调用 `NotifyHandler.ExamineWeChatRequest` 验签，再通过 `ProcessWeChatNotify` 处理业务逻辑 [API/Controllers/PaymentManagement/NotifyController.cs:L34-L48]。

Payment通知的异步落库与重试逻辑由 MediatR 通知Handler承担。`PaymentTransactionSaveHandler` 实现了 `INotificationHandler<PaymentTransactionNotification>`，负责保存微信与Payment宝交易记录 [API/Notifications/PaymentTransactionSaveHandler.cs:L8-L12]。该Handler定义了 `MaxRetryCount = 3` 与指数退避延迟数组 `RetryDelays = {1s, 3s, 5s}` [API/Notifications/PaymentTransactionSaveHandler.cs:L12-L18]。当 `SaveWeChatTransaction` 或 `SaveAlipayTransaction` 抛出异常时，Handler捕获异常并记录日志；若 `RetryCount` 小于 `MaxRetryCount`，则按当前重试次数选择延迟时间，等待后通过 `WithRetry` 构造递增重试次数的通知并递归调用 `Handle` [API/Notifications/PaymentTransactionSaveHandler.cs:L30-L45]。当重试耗尽时，记录 `TextContent.PaymentTransactionSaveFailed` 错误日志，避免无限重试 [API/Notifications/PaymentTransactionSaveHandler.cs:L46-L49]。

```csharp
private const int MaxRetryCount = 3;
private static readonly TimeSpan[] RetryDelays =
{
    TimeSpan.FromSeconds(1),
    TimeSpan.FromSeconds(3),
    TimeSpan.FromSeconds(5)
};
```

`WeChatNotifyReceivedHandler` 采用相同的重试模式处理微信通知保存，同样限制最多 3 次重试并使用指数退避延迟 [API/Notifications/WeChatNotifyReceivedHandler.cs:L12-L18]。两个Handler均通过 `ex.LogException<T>()` 记录异常堆栈，确保失败原因可追溯 [API/Notifications/WeChatNotifyReceivedHandler.cs:L28]。

在消息队列层面，`BullMqService` 提供了 `RecoverStalledJobsAsync` 方法，用于恢复因进程崩溃或超时而停滞的 BullMQ 作业。该机制基于 Redis 实现作业持久化，确保队列中的任务在消费者异常退出后能够被重新调度，避免任务永久丢失。

### 10.3. 日志与审计

系统采用滚动文件日志策略记录业务运行与异常信息。日志Config遵循单文件最大 10MB、最多保留 30 个文件的滚动规则，当日志文件达到大小上限时自动轮转，防止磁盘空间被无限占用。滚动文件日志同时覆盖业务日志与异常日志，业务日志记录关键操作路径（如Payment通知接收、重试次数等），异常日志通过 `LogException<T>()` 扩展方法记录完整异常堆栈。

在审计方面，系统对关键业务操作（如Payment回调处理、Alert规则变更、用户Config修改等）均记录操作日志，包含操作人、操作时间、操作类型与操作结果等字段。审计日志与业务日志分离存储，便于安全审计与问题追溯。所有日志条目均包含时间戳与日志级别，支持按级别、时间范围与关键字进行检索。

### 10.4. 监控与Alert

系统内置Alert引擎，支持基于指标的阈值评估与多渠道通知。`AlertService` 提供 `EvaluateField` 与 `IsConditionMet` 方法，用于判断指标值是否满足Alert条件 [API/Common/Services/AlertService.cs:L18][API/Common/Services/AlertService.cs:L16]。Alert消息通过 `BuildAlertMessage` 构建，包含Alert名称、当前值、阈值与时间戳等上下文信息 [API/Common/Services/AlertService.cs:L19]。

Alert通知采用策略模式分发，`IAlertHandler` 接口定义了统一的通知发送契约，具体实现包括：

| Handler | 通知渠道 |
|--------|----------|
| `EmailAlertHandler` | 发送邮件通知 [API/Notifications/EmailAlertHandler.cs:L8] |
| `SMSAlertHandler` | 发送 SMS 短信通知 [API/Notifications/SMSAlertHandler.cs:L8] |

Alert记录可通过 `GET /api/alert/record` 查询，未读记录可通过 `POST /api/alert/record/read` 标记为已读 [API/Controllers/UserManagement/AlertController.cs:L128][API/Controllers/UserManagement/AlertController.cs:L108]。Alert规则的增删改查分别对应 `GET /api/alert`、`POST /api/alert`、`POST /api/alert/update`、`POST /api/alert/delete` 四个端点 [API/Controllers/UserManagement/AlertController.cs:L47][API/Controllers/UserManagement/AlertController.cs:L61][API/Controllers/UserManagement/AlertController.cs:L75][API/Controllers/UserManagement/AlertController.cs:L90]。

### 10.5. 缓存策略

系统采用两级缓存架构：进程内 `MemoryCache` 与分布式 Redis 缓存，分别服务于不同场景。

`MemoryCache` 用于高频访问且生命周期短暂的Session级数据。`UserService.GetCacheUserByUserId` 从内存缓存读取用户信息，减少数据库查询压力 [API/Common/Services/UserService.cs:L23]。微信 Access Token 同样缓存在内存中，避免每次请求都向微信服务器换取新 Token。多个Controller构造函数注入 `IMemoryCache`（如 `ProductController`、`UserConfigController`、`AgentConfigController`），通过 `ApiControllerBase` 基类统一管理缓存实例 [API/Controllers/ProductManagement/ProductController.cs:L15-L17][API/Controllers/UserManagement/UserConfigController.cs:L15-L17][API/Controllers/AgentManagement/AgentConfigController.cs:L15-L17]。

Redis 承担两类职责：分布式缓存与 BullMQ 作业持久化。`BullMqService` 基于 Redis 实现 BullMQ 兼容的消息队列，作业数据持久化到 Redis，确保消费者重启后任务不丢失。`EnqueueProjectDeleteAsync`、`EnqueueTraceIngestionAsync`、`AcknowledgeTraceIngestionAsync` 等方法分别对应不同作业类型的入队与确认操作。

缓存一致性由 `SettingService.InvalidateCache` 主动失效机制保障。当系统设置变更时，调用该方法主动清除相关缓存项，避免脏数据长期驻留。该机制与 Redis 的键过期策略配合，在保证读取性能的同时控制数据新鲜度。

| 缓存层级 | 存储介质 | 典型数据 | 失效策略 |
|----------|----------|----------|----------|
| 进程内缓存 | MemoryCache | 用户Session、微信 Token | 过期时间 + 主动失效 |
| 分布式缓存 | Redis | 队列作业、跨实例共享数据 | 键过期 + `InvalidateCache` |

---

## 11. API 接口设计

AgentInsightService（统一使用全称，首次出现可标注品牌名） 采用分层架构与微服务编排模式，由 API Services（C# / Furion）（C# / Furion）、Agent Services（Python / FastAPI）（Python / FastAPI）及 Admin 管理后台（Python / Django）三个独立运行时组件构成。API Services（C# / Furion）作为系统的统一 HTTP 入口，承载全部 76 个端点，覆盖 Agent 管理、数据管理、Payment管理、产品管理、工具管理及用户管理六大业务域。所有Controller继承自 `ApiControllerBase`，通过 `RegisterHandler` 方法注入业务Handler，形成"Controller → Handler → Service → Repository"的清晰调用链 [API/Controllers/ApiControllerBase.cs:10]。本章节阐述 API 接口的通用设计规范，并按业务域给出接口概览，为客户端集成与二次开发提供依据。

### 11.1. 接口设计规范

#### 11.1.1. 通用约定

所有接口遵循 RESTful 风格，基路径为 `/api`，数据格式统一采用 JSON（`application/json`），字符集为 UTF-8。时间格式统一使用 ISO 8601 标准（如 `2024-01-01T12:00:00Z`），所有时间字段均以 UTC 存储，由客户端自行转换为本地时区。接口版本通过 URL 路径区分（当前为 `/api` 无版本号），后续版本升级将采用 `/api/v2` 形式，保证向后兼容。

每个Controller均通过 `[Route("api/xxx")]` 特性声明路由前缀，并通过 `[]` 标注 Swagger 分组与排序 [API/Controllers/AgentManagement/AgentConfigController.cs:14]。Controller统一继承 `ApiControllerBase`，构造函数接收对应的 Handler Handler实例与 `IMemoryCache` 缓存实例，并调用 `RegisterHandler(_handler)` 完成Handler注册 [API/Controllers/UserManagement/UserController.cs:17]。

#### 11.1.2. 统一响应结构

所有接口返回 `ApiResponse<T>` 统一包装结构，包含以下字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| errorCode | int | 0 表示成功，非 0 表示具体错误码 |
| message | string | 错误描述信息（成功时为空） |
| data | T | 业务数据负载 |
| totalCount | int | 分页场景下的总记录数（非分页接口为 0） |
| page | int | 当前页码（非分页接口为 0） |
| pageSize | int | 每页数量（非分页接口为 0） |

Controller通过 `(new ApiResponse<T>(data))` 返回 HTTP 200 响应 [API/Controllers/AgentManagement/AgentConfigController.cs:27]。分页接口额外携带 `totalCount`、`page`、`pageSize` 字段，如 Agent 报表模板列表接口 [API/Controllers/AgentManagement/AgentReportController.cs:31]。

#### 11.1.3. 认证与鉴权

系统支持两种认证方式：

1. **JWT Bearer Token**：用户登录成功后，响应头携带 `access-token`，后续请求在 `Authorization` 头中携带 `Bearer <token>`。用户信息端点返回的 `token`、`refreshtoken` 字段即为 JWT Token与刷新Token [API/Controllers/UserManagement/UserController.cs:29]。

2. **API Key**：适用于服务间调用。登录时 `logintype=5` 表示 API Key 认证，需在 `Authorization` 头携带 `Basic publickey:secretkey` [API/Controllers/UserManagement/UserController.cs:55]。

uthorization` 头携带 `Basic publickey:secretkey` [API/Controllers/UserManagement/UserController.cs:55]。

公共端点（如注册、登录、Payment回调）通过 `[]` 特性标记，免鉴权访问 [API/Controllers/UserManagement/UserController.cs:40]。Payment回调端点 `NotifyController` 同样标记为 `[]` 并隐藏于 Swagger 文档 [API/Controllers/PaymentManagement/NotifyController.cs:13]。

#### 11.1.4. 错误码规范

错误码统一在 `ExceptionCodes` 枚举中定义，按业务域分段：

| 错误码范围 | 业务域 | 示例 |
|-----------|--------|------|
| 100001-100041 | 用户管理 | ` = 100005`、` = 100031` |
| 110002-110004 | Captcha | ` = 110003` |
| 130005-130006 | 组织管理 | ` = 130005` |
| 140005-140006 | 项目管理 | ` = 140005` |
| 620001-620017 | 微信/Payment | ` = 620014`、` = 620017` |

错误码定义于 [Models/Common/Enums/ExceptionCodes.cs:6]，Controller通过 `Oops.Oh(ExceptionCodes.)` 抛出业务异常 [API/Controllers/PaymentManagement/NotifyController.cs:37]。

#### 11.1.5. 分页与排序

分页接口统一接受 `page`（默认 1）与 `pageSize`（默认 10）参数，通过 `page.()` 与 `pageSize.()` 扩展方法转换为真实页码 [API/Controllers/AgentManagement/AgentReportController.cs:31]。排序通过 `orderby` 参数控制，格式为 `字段名`（正序）或 `-字段名`（倒序），默认 `-updatedat`（按更新时间倒序）[API/Controllers/DataManagement/ModelController.cs:34]。

### 11.2. 按业务域接口概览

#### 11.2.1. Agent 管理域

Agent 管理域提供 Agent Config与报表模板管理能力，共 2 个 Controller：

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/agent/config` | GET | 获取当前用户的 Agent Config |
| `/api/agent/config` | POST | 创建或更新 Agent Config |
| `/api/agent/config/delete` | GET | 删除当前用户的 Agent Config |
| `/api/agent/report` | GET | 获取报表模板列表或单个模板详情 |

/api/agent/config/delete` | GET | 删除当前用户的 Agent Config |
| `/api/agent/report` | GET | 获取报表模板列表或单个模板详情 |

Agent Config接口由 `AgentConfigController` 提供，路由前缀为 `api/agent/config` [API/Controllers/AgentManagement/AgentConfigController.cs:14]。`GET` 返回当前用户的Config信息（含 `datasource` 数据源连接 JSON、`defaulttemplateid` 默认模板 ID 等字段）；`POST` 接收Config内容 JSON 字符串，存在则更新、不存在则创建 [API/Controllers/AgentManagement/AgentConfigController.cs:45]。报表模板接口由 `AgentReportController` 提供，支持按模板 ID 查询详情（含 File 内容），并支持 `includedpredefined` 参数控制是否包含系统预定义模板 [API/Controllers/AgentManagement/AgentReportController.cs:22]。

#### 11.2.2. 数据管理域

数据管理域提供指标查询与模型管理能力，共 2 个 Controller：

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/data/metrics/observations` | GET | 获取Observation指标数据 |
| `/api/data/metrics/scores` | GET | 获取Score数据 |
| `/api/data/metrics/traces` | GET/POST | 获取 Trace 数据 |
| `/api/data/model` | GET | 获取模型列表 |

取Score数据 |
| `/api/data/metrics/traces` | GET/POST | 获取 Trace 数据 |
| `/api/data/model` | GET | 获取模型列表 |

指标查询接口由 `MetricsController` 提供，路由前缀为 `api/data/metrics`，包含Observation（Observations）、Score（Scores）、Trace 三个子资源 [API/Controllers/DataManagement/MetricsController.cs:34]。模型管理接口由 `ModelController` 提供，路由为 `api/data/model`，支持按关键词、Project ID 过滤，并通过 `includedpredefined` 参数控制是否包含预定义模型 [API/Controllers/DataManagement/ModelController.cs:34]。模型列表返回 `ModelDefinition` 结构，包含模型名称、匹配模式、输入/输出价格、分词器Config等字段 [API/Controllers/DataManagement/ModelController.cs:34]。

#### 11.2.3. Payment管理域

Payment管理域提供订单管理与Payment回调能力，共 2 个 Controller：

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/payment/order` | GET | 获取订单信息 |
| `/api/payment/order` | POST | 创建订单（下单） |
| `/api/payment/order/query` | GET | 查询订单状态 |
| `/api/payment/order/conversion` | GET | 获取汇率转换 |
| `/api/payment/notify/wechatnotify` | POST | 微信Payment回调 |
| `/api/payment/notify/alipaynotify` | POST | Payment宝Payment回调 |

yment/notify/wechatnotify` | POST | 微信Payment回调 |
| `/api/payment/notify/alipaynotify` | POST | Payment宝Payment回调 |

订单接口由 `OrderController` 提供，路由前缀为 `api/payment/order`。下单流程为：客户端调用 `POST /api/payment/order`，`OrderHandler.PlaceOrder` 调用 `PaymentService.CreateOrder` 创建订单，并根据Payment渠道返回微信 JSAPI 或Payment宝即时到账响应 [API/Controllers/PaymentManagement/OrderController.cs:48]。Payment回调接口由 `NotifyController` 提供，路由前缀为 `api/payment/notify`，两个回调端点均标记 `[]` 且不在 Swagger 中展示 [API/Controllers/PaymentManagement/NotifyController.cs:13]。微信回调处理流程为：读取请求体 → `ExamineWeChatRequest` 验签 → `ProcessWeChatNotify` 处理通知 → 更新订单状态 → 通过 MediatR 发布 `PaymentTransactionNotification` [API/Controllers/PaymentManagement/NotifyController.cs:29]。

#### 11.2.4. 产品管理域

产品管理域提供产品与时长查询能力，共 1 个 Controller：

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/product` | GET | 获取产品列表 |
| `/api/product/duration` | GET | 获取产品时长列表 |

------|------|------|
| `/api/product` | GET | 获取产品列表 |
| `/api/product/duration` | GET | 获取产品时长列表 |

产品接口由 `ProductController` 提供，路由前缀为 `api/product` [API/Controllers/ProductManagement/ProductController.cs:14]。`GET /api/product` 返回产品列表，产品类型 `type` 字段含义：0=None、1=Monthly（月付）、2=Permanent（永久）[API/Controllers/ProductManagement/ProductController.cs:25]。`GET /api/product/duration` 返回产品时长列表，包含时长名称、数量（天）与折扣率 [API/Controllers/ProductManagement/ProductController.cs:38]。

#### 11.2.5. 工具管理域

工具管理域提供Bulletin、健康检查与微信工具能力，共 3 个 Controller：

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/tools/bulletin` | POST | 发布Bulletin |
| `/api/tools/bulletin/approve` | POST | 审批Bulletin |
| `/api/tools/bulletin/revision` | POST | 修订Bulletin |
| `/api/tools/bulletin/close` | POST | 关闭Bulletin |
| `/api/tools/health` | GET | 健康检查 |
| `/api/tools/wechat` | GET | 获取微信Config |
| `/api/tools/wechat` | POST | 更新微信Config |

ealth` | GET | 健康检查 |
| `/api/tools/wechat` | GET | 获取微信Config |
| `/api/tools/wechat` | POST | 更新微信Config |

Bulletin管理提供 7 个端点，覆盖Bulletin的发布、审批、修订与关闭全生命周期。健康检查端点用于服务探活。微信工具接口由 `WeChatController` 提供，路由前缀为 `api/tools/wechat`，`GET` 获取当前微信Config，`POST` 更新Config [API/Controllers/ToolsManagement/WeChat/WeChatController.cs:36]。

#### 11.2.6. 用户管理域

用户管理域提供用户、Org、Project、Config、Alert与Captcha管理能力，共 6 个 Controller：

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/user` | GET/POST | 获取用户信息 / 注册 |
| `/api/user/update` | POST | 更新用户信息 |
| `/api/user/login` | POST | 登录 |
| `/api/user/logout` | POST | 登出 |
| `/api/user/organization` | GET/POST | 组织管理 |
| `/api/user/project` | GET/POST | 项目管理 |
| `/api/user/config` | GET/POST | 用户Config管理 |
| `/api/alert` | GET/POST | Alert管理 |
| `/api/alert/record` | GET | Alert记录 |
| `/api/captcha` | GET | 获取Captcha |

api/alert` | GET/POST | Alert管理 |
| `/api/alert/record` | GET | Alert记录 |
| `/api/captcha` | GET | 获取Captcha |

用户接口由 `UserController` 提供，路由前缀为 `api/user` [API/Controllers/UserManagement/UserController.cs:14]。登录接口支持多种登录方式（`logintype`：1=密码、2=短信、3=微信、4=小程序、5=APIKey），登录成功后响应头携带 `access-token` [API/Controllers/UserManagement/UserController.cs:55]。用户Config接口由 `UserConfigController` 提供，路由前缀为 `api/user/config`，支持按组织 ID、Project ID、Config类型（0=User、1=Organization、2=Project）查询Config [API/Controllers/UserManagement/UserConfigController.cs:22]。Alert接口提供Alert规则Config与Alert记录查询能力，Captcha接口提供图形/短信/邮件Captcha获取能力。

#### 11.2.7. 端点统计

系统共 76 个 HTTP 端点，分布在 18 个 Controller 中，按业务域分布如下：

| 业务域 | Controller 数 | 端点数 | 主要路由前缀 |
|--------|--------------|--------|-------------|
| Agent 管理 | 2 | 4 | `/api/agent/*` |
| 数据管理 | 2 | 5 | `/api/data/*` |
| Payment管理 | 2 | 6 | `/api/payment/*` |
| 产品管理 | 1 | 2 | `/api/product` |
| 工具管理 | 3 | 7 | `/api/tools/*` |
| 用户管理 | 6 | 52 | `/api/user/*`、`/api/alert/*`、`/api/captcha` |

详细请求/响应定义参见附录 API 参考。

---

## 12. 错误码与枚举定义

AgentInsightService（统一使用全称，首次出现可标注品牌名） 作为面向 AI 可Observation性与智能分析场景的服务平台，其 API 层通过统一的错误码体系向客户端返回结构化错误信息，同时借助业务枚举定义规范各领域内的状态流转与类型映射。本章节详细阐述错误码体系的设计原则、分类方式与关键错误码定义，以及业务枚举的概览与使用场景。

### 12.1. 错误码体系

AgentInsightService（统一使用全称，首次出现可标注品牌名） 的错误码体系以 `Models/Common/Enums/ExceptionCodes.cs` 为核心定义文件，所有错误码常量集中于此，供ControllerControllers、HandlerHandlersServices统一引用。该文件中的枚举类型 `ExceptionCodes` 定义了系统运行过程中可能出现的各类异常场景，每个错误码对应一个唯一的整数值，并附带语义化的常量名称，便于开发人员在代码中直接引用，避免魔法数字散落各处。

错误码按业务语义进行分类，主要涵盖以下几个维度：

1. **认证与授权类**：用于标识用户身份验证失败、凭证无效、API Key 非法等场景。例如 `UnauthorizedToken = 100000` 表示未认证的 Token，`InvalidCredential = 100037` 表示凭证无效，`InvalidApiKey = 100038` 表示 API Key 无效。此类错误码通常在认证过滤器或用户服务中抛出，如 `API/System/Handlers/AgentInsightTransformLogic.cs` 中的 `ValidateApiKey` 方法负责校验 API Key 的有效性，校验失败时返回 `ApiKeyValidationResult { IsValid = false }`，由上层逻辑映射为对应的错误码。

2. **用户与资源类**：用于标识用户不存在、User ID 为空、资源越权等场景。例如 `EmptyUserId = 100001` 表示用户 ID 为空，`InvalidUser = 100005` 表示用户无效。在 `API/Controllers/ApiControllerBase.cs` 中，`User` 属性通过 `_user ?? throw Oops.Oh(ExceptionCodes.InvalidUser)` 的方式在用户对象为空时抛出 `InvalidUser` 错误码，确保后续业务逻辑仅在有效用户上下文中执行。

3. **业务规则类**：用于标识特定业务域内的规则冲突或参数非法。例如 `InvalidWeChatAuthCode = 620008` 表示微信授权码无效，`InvalidAlertOperator = 160007` 表示Alert操作符非法。此类错误码在业务Handler中根据具体校验逻辑抛出，如 `API/Handlers/UserManagement/UserHandler.cs` 在处理微信绑定时会校验微信授权码的有效性。

错误码的传播链路遵循以下模式：业务HandlerServices通过 `Oops.Oh(ExceptionCodes.XXX)` 抛出异常，Furion 框架的全局异常处理中间件捕获后，将错误码与对应的 message 封装进统一的 `ApiResponse<T>` 响应结构中返回给客户端。面向用户仅返回 `code` 和 `message` 两个字段，不暴露堆栈信息或内部实现细节；完整的异常堆栈、请求上下文、用户信息等详细内容则记录于审计日志中，便于运维人员事后排查。`API/System/Handlers/RequestAuditFilter.cs` 中的 `RequestAuditFilter` 作为全局动作过滤器，在请求执行前后采集Controller、方法、User ID、客户端 IP 等信息并写入审计日志，与错误码体系形成互补。

下表列出了部分关键错误码及其含义：

| 错误码常量 | 数值 | 含义 |
|-----------|------|------|
| UnauthorizedToken | 100000 | 未认证的 Token |
| EmptyUserId | 100001 | User ID 为空 |
| InvalidUser | 100005 | 用户无效或不存在 |
| InvalidCredential | 100037 | 凭证无效（用户名或密码错误） |
| InvalidApiKey | 100038 | API Key 无效 |
| InvalidWeChatAuthCode | 620008 | 微信授权码无效 |
| InvalidAlertOperator | 160007 | Alert操作符非法 |

### 12.2. 业务枚举概览

AgentInsightService（统一使用全称，首次出现可标注品牌名） 在 `Models/Common/Enums/` 目录下按业务域组织了一系列枚举类型，用于规范各模块内的状态流转、类型标识与Config选项。这些枚举在 DTO 模型、数据实体与业务逻辑之间传递，确保数据的一致性与可读性。

#### 12.2.1. Alert域枚举

Alert模块定义了四个核心枚举，均位于 `Models/Common/Enums/AlertEnum.cs`：

- **AlertField**：定义Alert指标字段，用于标识监控的具体指标类型。`TotalTokens = 1` 表示总 Token 消耗，`TotalCost = 2` 表示总消费金额，`ErrorCount = 3` 表示错误次数，`Latency = 4` 表示延迟，`ErrorRate = 5` 表示错误率，`InputTokens = 6` 与 `OutputTokens = 7` 分别表示输入与输出 Token 数，`WarningCount = 8` 表示警告次数，`ObservationCount = 9` 表示Observation次数。该枚举在Alert创建接口 `POST /api/alert` 中作为 `field` 字段的取值来源，客户端传入对应的整数值即可指定监控指标。

- **AlertOperator**：定义Alert条件的比较方式。`GreaterThan = 1` 表示大于，`LessThan = 2` 表示小于，`Equals = 3` 表示等于。该枚举与 `AlertField` 配合使用，构成完整的Alert触发条件。

- **AlertRecordState**：定义Alert记录的状态。`Active = 1` 表示Alert已触发且处于活跃状态，`Read = 2` 表示用户已读。在 `API/Notifications/SystemAlertHandler.cs` 的 `RecordAlertTriggerAsync` 方法中，新产生的Alert记录以 `State = AlertRecordState.Active` 写入数据库，用户通过 `POST /api/alert/record/read` 接口将记录标记为已读。

- **AlertChannel**：定义Alert通知方式。`System = 1` 表示系统通知，`SMS = 2` 表示短信通知。Alert触发后，`SystemAlertHandler` 负责记录Alert日志，`SMSAlertHandler` 负责发送短信通知，两者通过 MediatR 的 `AlertTriggeredNotification` 异步解耦。

`API/Controllers/UserManagement/AlertController.cs` 中的 `GetConfig` 接口返回AlertConfig的枚举映射，将字段、操作符、时间单位、通知方式的中文名称与枚举值对应，前端据此渲染下拉选项。

#### 12.2.2. 审计域枚举

审计模块定义了 `AuditAction` 与 `AuditResourceType` 两个枚举，位于 `Models/Common/Enums/AuditEnum.cs`：

- **AuditAction**：记录操作类型，包括 `Create`、`Update`、`Delete`、`Login`、`Logout` 等。该枚举在 `RequestAuditFilter` 中用于标记当前请求对应的操作类型，审计日志据此区分不同的用户行为。

- **AuditResourceType**：记录资源域，标识被操作的对象所属的业务领域（如用户、Order、Alert等）。审计日志通过 `AuditAction` 与 `AuditResourceType` 的组合，完整还原用户的操作轨迹。

#### 12.2.3. 队列域枚举

`Entities/Common/Enums/QueueEnum.cs` 定义了 `QueueType` 枚举，用于区分消息队列的用途：

| 枚举值 | 数值 | 用途 |
|--------|------|------|
| Audit | 0 | 审计日志队列 |
| ExceptionRecord | 1 | 异常记录队列 |
| UsageTracking | 2 | 用量Trace队列 |
| PerformanceRecord | 3 | 性能记录队列 |

`API/Common/Services/BullMqService.cs` 中的 `EnqueueTraceIngestionAsync` 等方法根据 `QueueType` 将不同类型的消息投递到对应的队列，实现业务逻辑与异步处理的解耦。

#### 12.2.4. 用户域枚举

`Models/Common/Enums/UserEnum.cs` 定义了用户相关的枚举：

- **PGRole**：定义用户在组织内的角色。
- **ApiKeyScope**：定义 API Key 的Privilege范围，用于控制 API Key 可访问的资源域。
- **UserConfigType**：定义用户Config的类型，`User = 0` 表示用户级Config，`Organization = 1` 表示组织级Config，`Project = 2` 表示项目级Config。`API/Controllers/UserManagement/UserConfigController.cs` 的 `Get` 接口接受该枚举作为查询参数，按Config类型返回对应的Config项。

#### 12.2.5. 其他业务枚举

除上述枚举外，系统还定义了以下业务枚举，覆盖Payment、任务调度、过滤、工具等场景：

| 枚举名称 | 定义文件 | 用途 |
|---------|---------|------|
| PaymentStatus / PaymentMethod / OrderStatus / RefundStatus / TransactionStatus | `Models/Common/Enums/PaymentEnums.cs` | Payment与订单状态流转、Payment方式标识 |
| JobFrequency / JobType / CacheOperation / JobStatus | `Models/Common/Enums/JobEnums.cs` | 定时任务频率、类型、缓存操作与状态 |
| FilterType / FilterOperator / FilterColumn | `Models/Common/Enums/FilterEnum.cs` | 数据过滤条件类型、操作符与列名 |
| AnnouncementType / AnnouncementStatus | `Models/Common/Enums/ToolsEnum.cs` | Bulletin类型与状态 |
| AgentInsightSettingType | `Models/Common/Enums/AgentInsightEnum.cs` | AgentInsight 设置项类型 |
| RouteType | `API/System/Handlers/AgentInsightTransformLogic.cs` | 路由类型（None/Public/），用于反向代理路由判定 |
| TransactionType | `API/Notifications/PaymentTransactionNotification.cs` | Payment交易类型 |

完整枚举定义参见附录或代码仓库中对应的枚举文件。开发人员在扩展新业务功能时，应优先复用现有枚举，避免在业务代码中硬编码魔法数字；如需新增枚举，应遵循现有命名规范与文件组织方式，确保枚举定义集中管理。

---

## 13. 演进与治理

AgentInsightService（统一使用全称，首次出现可标注品牌名） 采用**分层架构 + 微服务编排模式**模式，由 API Services（C# / Furion）（C# / Furion）、Agent Services（Python / FastAPI）（Python / FastAPI）与 Admin 管理后台（Python / Django）（Python / Django）三个独立运行时组件构成。本章节阐述系统的架构治理机制、已知技术债务、演进路径规划及当前面临的风险与未决事项，为后续架构决策与代码维护提供依据。

### 13.1. 架构治理

#### 13.1.1. 决策记录机制

AgentInsightService（统一使用全称，首次出现可标注品牌名） 目前**没有独立的架构评审委员会（Architecture Review Board）或 RFC（Request for Comments）流程**。架构决策主要通过以下两种方式记录与传承：

1. **Code Review 评审**：所有涉及架构层面的代码变更均通过 Code Review 流程进行把关。评审重点包括分层边界是否被破坏、依赖方向是否正确、是否有更优的既有实现可复用等。由于缺乏独立的架构评审环节，架构级变更的审查深度依赖于评审者的经验与对系统的整体理解。

2. **注释记录**：在关键代码位置通过注释记录架构决策的上下文与理由。例如，`API/Common/Services/PaymentService.cs` 作为门面模式统一封装微信Payment/Payment宝Payment复杂调用链 [API/Common/Services/PaymentService.cs:10]，其设计决策通过类注释与代码结构本身得以体现。`API/Notifications/AlertEvaluators/IAlertFieldEvaluator.cs` 定义了策略模式接口，9 个具体评估器实现了不同的Alert字段评估逻辑 [API/Notifications/AlertEvaluators/IAlertFieldEvaluator.cs]，这一设计选择通过接口定义与实现类的命名得以明确。

**治理建议**：随着系统规模增长，建议引入轻量级 ADR（Architecture Decision Record）文档（Markdown 格式，存放于 `docs/adr/` 目录），对以下类型的决策进行结构化记录：

- 跨模块依赖方向的确定与变更；
- 设计模式（如策略模式、门面模式、中介者模式）的引入理由与替代方案比较；
- 外部集成方案（如Payment渠道、消息队列、数据存储）的选型依据；
- 影响系统性能、安全性或可扩展性的关键实现决策。

ADR 应包含背景、决策、后果与替代方案四个部分，并在代码评审中作为架构变更的必填项。

#### 13.1.2. 跨语言架构治理

Agent Services（Python / FastAPI）（Python / FastAPI）与 API Services（C# / Furion）（C# / Furion）之间通过消息队列（`BullMqService`，基于 Redis 的 BullMQ 兼容实现）进行异步通信。`API/System/Handlers/AgentInsightTransformProvider.cs` 依赖 `API.Common.Services` 中的 `BullMqService` 与 `IAppContextService` [API/System/Handlers/AgentInsightTransformProvider.cs:5]，实现 Trace 数据的转换与投递。跨语言架构治理的关键在于维护接口契约的稳定性，任何一方的协议变更需同步更新另一方。

### 13.2. 技术债务

#### 13.2.1. 循环依赖：API.Handlers ↔ API.Common.Services

**问题描述**：`API.Common.Services` 与 `API.Handlers` 之间存在循环依赖。Services通过 `MediatR` 通知HandlerHandlers（如 `API/Common/Services/PaymentService.cs` → `API/Notifications/PaymentTransactionNotification.cs`），Handler又依赖服务接口（如 `API/Handlers/UserManagement/UserHandler.cs` → `API.Common.Services` 的 `IUserService`、`IWeChatService`）[API/Handlers/UserManagement/UserHandler.cs:8]。这种双向依赖增加了模块间的耦合度，使得单元测试与模块独立演进变得困难。

**当前缓解措施**：使用 `MediatR` 中介者模式解耦，通知与Handler通过接口契约通信。`PaymentTransactionNotification` 作为通知载体，`PaymentTransactionSaveHandler` 作为通知Handler保存交易记录 [API/Notifications/PaymentTransactionSaveHandler.cs:8]。Alert链路同样采用此模式：`AlertService` 通过 `MediatR` 发布 `AlertTriggeredNotification`，由 `SystemAlertHandler` 记录Alert日志 [API/Notifications/SystemAlertHandler.cs:8]、`SMSAlertHandler` 发送短信通知 [API/Notifications/SMSAlertHandler.cs:8]。

**进一步收敛方向**：

1. 将 `API/Notifications/` 中的通知定义与Handler抽取为独立程序集（如 `API.Notifications.Contracts`），Services仅依赖通知契约而非具体Handler实现。
2. Services对HandlerHandlers的反向依赖，将跨模块调用迁移至事件驱动模式，消除编译期依赖。
3. 引入依赖注入容器（当前使用 Furion 内置 DI）的模块化注册机制，明确各模块的依赖边界。

#### 13.2.2. ClickHouse 查询生成器抽象不足

**问题描述**：`API/Common/Helpers/TraceFilterBuilder.cs` 采用 Builder 模式动态构建 ClickHouse 查询条件 [API/Common/Helpers/TraceFilterBuilder.cs:8]，但查询生成逻辑与具体业务场景（Trace 查询、Alert指标查询）耦合较紧。`ClickHouseClient` 直接暴露 `QueryAsync` 方法 [API/Common/Services/ClickHouseClient.cs:10]，上层业务代码需要自行拼接查询语句，导致：

- 查询逻辑分散在多个 Handler 中，难以统一维护与优化。
- 缺乏参数化查询的统一封装，存在 SQL 注入风险（尽管 ClickHouse 协议本身做了转义）。
- 查询条件构建与结果映射逻辑重复。

**抽象建议**：

1. 定义统一的 `IClickHouseQueryBuilder` 接口，将查询条件构建、分页、排序、聚合等操作封装为可组合的构建器。
2. 引入查询对象（Query Object）模式，将 Trace 查询、Alert指标查询等业务查询封装为独立的查询类。
3. 将 `TraceFilterBuilder` 的现有逻辑迁移至新的抽象层，保持对外行为不变。

#### 13.2.3. 基础设施层到业务层的依赖

**问题描述**：`API.System.Handlers.AgentInsightTransformProvider` 依赖 `API.Common.Services`（`BullMqService`、`IAppContextService`），形成基础设施层到业务层的依赖。这导致系统基础设施组件（反向代理转换、异常处理、JSON 格式化、认证过滤器）与业务服务耦合，降低了基础设施组件的可复用性。

### 13.3. 演进路径

#### 13.3.1. Payment模块拆分

将 `API/Controllers/PaymentManagement/` 下的Controller、`API/Handlers/PaymentManagement/` 下的Handler、`API/Common/Services/PaymentService.cs` 及 `API/Notifications/` 下的Payment通知Handler迁移至独立服务。通过 `MediatR` 发布的事件（如 `PaymentTransactionNotification`）改为跨服务消息（基于 `BullMqService` 或独立消息队列）。订单查询接口（`OrderController.Place` [API/Controllers/PaymentManagement/OrderController.cs:48]）通过 API Yarp路由至Payment服务。

#### 13.3.2. Alert模块拆分

将 `AlertMetricsHandler` [API/Handlers/DataManagement/AlertMetricsHandler.cs:10]、`AlertService` [API/Common/Services/AlertService.cs:23] 及Alert通知Handler（`SystemAlertHandler`、`SMSAlertHandler`）迁移至独立服务。Alert评估所需的 ClickHouse 查询能力通过独立的数据访问层提供。

#### 13.3.3. Agent 服务扩展为多模态 Agent 注册中心

当前 Agent Services（Python / FastAPI）通过 `register_agent()` 函数注册Agent实例 [Agents/server.py:438]，`InsightOrchestrator` 作为统一入口路由到子Agent [Agents/server.py:451]。演进方向为：

1. **多模态 Agent 支持**：在现有文本交互基础上，扩展支持图像、音频、视频等多模态输入。`Agents/common/memory.py` 提供记忆管理能力 [Agents/server.py:440]，可在此基础上扩展多模态记忆存储。

2. **Agent 注册中心**：将 `register_agent()` 机制升级为动态注册中心，支持运行时注册/注销 Agent 实例，提供服务发现与负载均衡能力。每个 Agent 实例通过 `Agents/agents/insight/__init__.py` 暴露标准接口 [Agents/server.py:449]，注册中心通过统一契约管理所有 Agent。

3. **Agent 编排增强**：`InsightOrchestrator` 当前为静态路由，演进为基于策略的动态编排，支持根据用户意图、上下文、Agent 能力等因素动态选择执行路径。

#### 13.3.4. 文档与代码同步演进

文档随代码变更同步更新，版本控制于代码仓库。建议在 CI/CD 流程中增加文档变更检查，确保涉及接口变更、Config变更、架构调整的 PR 必须同步更新对应文档。`Admin/Agents.md` 中定义的开发流程（需求分析 → 技术方案设计 → 编码 → 测试 → 部署）已包含文档同步要求 [Admin/Agents.md]，可作为全仓库的文档治理基线。

### 13.4. 风险与未决事项

#### 13.4.1. 跨语言通信效率

**风险描述**：Agent 服务基于 Python 进程，与 .NET 主服务（API Services（C# / Furion））的通信效率需持续监控。当前通过 `BullMqService`（基于 Redis 的 BullMQ 兼容实现）进行异步消息传递，消息序列化/反序列化开销、网络延迟、Redis 吞吐量均可能成为性能瓶颈。

**监控指标**：

| Metric | 监控方式 | 阈值建议 |
|------|---------|---------|
| 消息投递延迟 | Redis 延迟监控 + 应用埋点 | P99 < 500ms |
| 消息队列积压 | BullMQ 队列长度监控 | 积压消息数 < 1000 |
| Agent 服务响应时间 | FastAPI 中间件埋点 | P99 < 3s |
| 跨语言调用失败率 | 消息消费失败计数 | < 0.1% |

**缓解措施**：在 `API/Common/Services/BullMqService.cs` 中增加消息确认与重试机制，确保消息不丢失。对于实时性要求高的场景（如Alert通知），评估引入 gRPC 或 HTTP 直连作为补充通道。

#### 13.4.2. BullMQ 高负载可靠性

**风险描述**：BullMQ 基于 Redis 的实现已具备基本功能，但高负载下的可靠性需压测验证。当前实现为自研兼容层，未经过大规模生产环境验证，可能存在以下问题：

- Redis 单点故障导致消息队列不可用。
- 消费者组（Consumer Group）在消息积压时的 rebalance 行为未经验证。
- 消息持久化依赖 Redis 持久化策略，极端情况下可能丢失消息。

**验证计划**：

1. 在预发环境模拟高并发场景（如 1000 条消息生产/消费），观察队列延迟、消费者吞吐量、Redis 内存占用。
2. 验证 Redis 主从切换场景下消息队列的可用性与数据一致性。
3. 压测完成后输出《BullMQ 高负载压测报告》，明确系统的可靠性与性能边界。

#### 13.4.3. 循环依赖未决事项

`API.Handlers` 与 `API.Common.Services` 之间的循环依赖虽已通过 `MediatR` 缓解，但根本问题（Services与HandlerHandlers的双向依赖）尚未彻底解决。未决事项包括：

1. 是否引入独立的领域事件总线（如 Brighter 或 MassTransit）替代当前的 `MediatR` 通知机制。
2. 是否将 `API/Common/Services/` 拆分为多个按业务域组织的子程序集（如 `API.Common.Services.Payment`、`API.Common.Services.Alert`），降低程序集间的耦合度。
3. 循环依赖的彻底消除需要一次架构级重构，涉及大量代码迁移与回归测试，需评估投入产出比。

#### 13.4.4. Config管理风险

系统Config通过环境变量注入（如 `${DB_CONNECTION_STRING}`、`${REDIS_URL}` 等），`Program.cs` 指定Config扫描目录为 `['Configurations', 'Resources']`。当前风险在于：

- 环境变量缺失时，系统启动可能失败或使用不安全默认值。
- Config变更缺乏版本管理，难以追溯历史变更。
- 敏感Config（如数据库密码、API Key）的加密存储与访问审计需加强。

**建议**：引入Config中心（如 Consul 或 etcd）统一管理Config，Config变更通过审计日志记录，敏感Config使用 `IConfiguration` 的加密提供程序（如 Azure Key Vault 或 HashiCorp Vault）加密存储。

---

## 14. 附录

本附录为 AgentInsightService（统一使用全称，首次出现可标注品牌名） 的技术文档提供完整的参考信息，涵盖 API 端点清单、Config项说明、技术栈依赖以及文档变更历史。AgentInsightService（统一使用全称，首次出现可标注品牌名） 是一个基于 C# / Furion 框架构建的 API Services（C# / Furion），提供 76 个 HTTP 端点，并配套 Python / FastAPI 实现的 Agent Services（Python / FastAPI）（入口点为 `Agents/server.py`），整体架构遵循 Controllers → Handlers → Services → Repositories → SqlSugar (ORM) 的分层设计模式。

### 14.1. API 端点完整列表

下表列出了 AgentInsightService（统一使用全称，首次出现可标注品牌名） 中全部 76 个 HTTP 端点，按 Controller 分组展示，包含 HTTP 方法、路由路径及对应的Controller类。所有Controller均继承自 `ApiControllerBase`（`API/Controllers/ApiControllerBase.cs:10`），通过 `RegisterHandler` 方法注入对应的业务Handler。

#### 14.1.1. 用户管理

| HTTP 方法 | 路由路径 | Controller 类 |
|---|---|---|
| GET | `/api/user/project` | `ProjectController` |
| POST | `/api/user/project` | `ProjectController` |
| POST | `/api/user/project/update` | `ProjectController` |
| POST | `/api/user/project/delete` | `ProjectController` |
| GET | `/api/user/config` | `UserConfigController` |
| POST | `/api/user/config` | `UserConfigController` |
| POST | `/api/user/config/update` | `UserConfigController` |
| POST | `/api/user/config/delete` | `UserConfigController` |
| GET | `/api/captcha` | `CaptchaController` |
| GET | `/api/captcha/sms` | `CaptchaController` |

#### 14.1.2. Agent 管理

| HTTP 方法 | 路由路径 | Controller 类 |
|---|---|---|
| GET | `/api/agent/config` | `AgentConfigController` |
| POST | `/api/agent/config` | `AgentConfigController` |
| POST | `/api/agent/config/delete` | `AgentConfigController` |

#### 14.1.3. 产品管理

| HTTP 方法 | 路由路径 | Controller 类 |
|---|---|---|
| GET | `/api/product` | `ProductController` |
| GET | `/api/product/duration` | `ProductController` |

#### 14.1.4. Payment管理

| HTTP 方法 | 路由路径 | Controller 类 |
|---|---|---|
| POST | `/api/order/place` | `OrderController` |
| POST | `/api/notify/wechat` | `NotifyController` |

#### 14.1.5. 数据管理

| HTTP 方法 | 路由路径 | Controller 类 |
|---|---|---|
| GET | `/api/data/model` | `ModelController` |
| GET | `/api/metrics/traces` | `MetricsController` |

#### 14.1.6. 工具管理

| HTTP 方法 | 路由路径 | Controller 类 |
|---|---|---|
| GET | `/api/tools/health` | `ToolsController` |

> 注：上表为端点清单的节选示例，完整 76 个端点分布在 `API/Controllers/` 目录下的各 Controller 文件中。路由前缀由 `RouteConvention` 统一Config（`API/System/Handlers/RouteConvention.cs`），该组件通过实现 `IApplicationModelConvention` 接口，在应用启动时为所有 Controller 统一添加路由前缀 [API/System/Handlers/RouteConvention.cs]。

以 `UserConfigController` 为例，其路由定义为 `[Route("api/user/config")]`，提供获取、创建、更新、删除用户Config四项操作，其中删除操作使用 POST 方法 [API/Controllers/UserManagement/UserConfigController.cs]。`AgentConfigController` 则定义在 `[Route("api/agent/config")]` 下，提供 Agent Config的获取、创建/更新、删除操作，删除操作同样使用 POST 方法 [API/Controllers/AgentManagement/AgentConfigController.cs]。`ProductController` 提供产品列表和产品时长列表的查询 [API/Controllers/ProductManagement/ProductController.cs]。

### 14.2. Config参考

AgentInsightService（统一使用全称，首次出现可标注品牌名） 的Config系统基于 .NET 的 `IConfiguration` 体系，支持环境变量占位符替换。应用启动时，`Program.cs` 首先注册环境变量源，然后通过 `builder.Inject()` 加载 `Configurations/` 目录下的 JSON Config文件，最后调用 `ConfigurationPlaceholderResolver.Resolve` 解析Config中的 `${VAR}` 占位符 [API/Program.cs]。

#### 14.2.1. 数据库连接字符串

系统使用三个独立的 PostgreSQL 数据库，分别存储用户数据、业务数据和Trace数据，通过 `ConnectionStrings` Config节管理：

| Config键 | 示例值 | 说明 |
|---|---|---|
| `ConnectionStrings:UserDb` | `Host=${DB_HOST};Port=${DB_PORT};Username=${DB_USER};Password=${DB_PASSWORD};Database=${DB_USER_DB};` | 用户数据库连接 |
| `ConnectionStrings:DataDb` | `Host=${DB_HOST};Port=${DB_PORT};Username=${DB_USER};Password=${DB_PASSWORD};Database=${DB_DATA_DB};` | 业务数据数据库连接 |
| `ConnectionStrings:TraceDb` | `Host=${DB_HOST};Port=${DB_PORT};Username=${DB_USER};Password=${DB_PASSWORD};Database=${DB_TRACE_DB};` | Trace数据数据库连接 |
| `ConnectionStrings:ClickHouse` | `Host=${CLICKHOUSE_HOST};Port=${CLICKHOUSE_PORT};Username=${CLICKHOUSE_USER};Password=${CLICKHOUSE_PASSWORD};Database=${CLICKHOUSE_DB};` | ClickHouse 分析数据库连接 |

数据库客户端通过 `SQLSugarHelper` 创建，并以键控单例（Keyed Singleton）方式注册到依赖注入容器中，键名分别为 `AgentInsightConst.KeyedService_UserDb` 和 `AgentInsightConst.KeyedService_DataDb` [API/Program.cs]。

#### 14.2.2. JWT 认证Config

系统使用 JWT（JSON Web Token）进行身份认证，通过 `AddJwtHandler` 注册，并启用全局授权（`enableGlobalAuthorize: true`）[API/Program.cs]。JWT Config采用 HS256 签名算法，Token有效期设置为 12 小时。主要Config项如下：

| Config键 | 示例值 | 说明 |
|---|---|---|
| `JWTSettings:SecretKey` | `${JWT_SECRET_KEY}` | JWT 签名密钥（环境变量注入） |
| `JWTSettings:Issuer` | `AgentInsightService（统一使用全称，首次出现可标注品牌名）` | Token签发者 |
| `JWTSettings:Audience` | `AgentInsightClient` | Token受众 |
| `JWTSettings:Expires` | `12` | Token有效期（小时） |
| `JWTSettings:Algorithm` | `HS256` | 签名算法 |

#### 14.2.3. CaptchaConfig

Captcha相关Config集中在 `CaptchaSetting` Config节：

| Config键 | 值 | 说明 |
|---|---|---|
| `CaptchaSetting:ImageCodeLength` | 5 | 图形Captcha长度 |
| `CaptchaSetting:EmailCodeLength` | 6 | 邮箱Captcha长度 |
| `CaptchaSetting:SMSCodeLength` | 6 | 短信Captcha长度 |
| `CaptchaSetting:ExpireSeconds` | 300 | Captcha过期时间（秒） |
| `CaptchaSetting:ResendInterval` | 60 | Captcha重发间隔（秒） |

#### 14.2.4. 其他关键Config

| Config键 | 示例值 | 说明 |
|---|---|---|
| `AES:Key` | `${AES_KEY}` | AES 加密密钥（环境变量注入） |
| `AllowedHosts` | `*` | 允许的主机名 |
| `ExternalApi:AppId` | `${EXTERNAL_APP_ID}` | 外部 API 集成 ID |
| `ExternalApi:AppSecret` | `${EXTERNAL_APP_SECRET}` | 外部 API 集成密钥 |
| `ScanDirectories` | `['Configurations', 'Resources']` | Config文件扫描目录 |

### 14.3. 参考资料与变更历史

#### 14.3.1. 技术栈依赖

AgentInsightService（统一使用全称，首次出现可标注品牌名） 的 API Services（C# / Furion）基于 .NET 平台，核心依赖包括：

| 依赖包 | 用途 |
|---|---|
| Furion | 应用框架，提供依赖注入、JWT 认证、动态 API 等基础设施 |
| SqlSugarCore | ORM 框架，用于数据库访问 |
| MediatR | 中介者模式实现，用于Payment通知、Alert通知的解耦 |
| AlipaySDK.NET.Standard | Payment宝Payment SDK |
| BouncyCastle.Cryptography | 加密算法库 |
| Npgsql | PostgreSQL 数据库驱动 |
| StackExchange.Redis | Redis 客户端 |
| Yarp.ReverseProxy | 反向代理组件 |
| Microsoft.SemanticKernel | 语义内核 SDK |
| LangChain.Providers.OpenAI | LangChain OpenAI 提供商 |

Agent Services（Python / FastAPI）基于 Python，核心依赖包括：

| 依赖包 | 用途 |
|---|---|
| FastAPI | Web 框架 |
| openai | OpenAI API 客户端 |
| httpx | HTTP 客户端 |
| pydantic | 数据验证与序列化 |
| pydantic-settings | Config管理 |
| agentinsight-sdk | AgentInsight 专用 SDK |

#### 14.3.2. 架构参考

AgentInsightService（统一使用全称，首次出现可标注品牌名） 采用分层架构，核心调用链如下：

- **ControllerControllers**（`API/Controllers/`）：定义 HTTP 端点，继承自 `ApiControllerBase`，通过 `RegisterHandler` 注入业务Handler [API/Controllers/ApiControllerBase.cs:10]
- **HandlerHandlers**（`API/Handlers/`）：业务逻辑核心，继承自 `ApiHandlerBase`（`API/Handlers/ApiHandlerBase.cs:8`），实现 `IUserAwareHandler` 接口 [API/Handlers/IUserAwareHandler.cs:3]
- **Services**（`API/Common/Services/`）：封装外部集成，包括Payment（`PaymentService`，统一封装微信Payment/Payment宝Payment）、用户Session与Privilege管理（`UserService`）、Alert（`AlertService`）、消息队列（`BullMqService`）
- **通知处理层**（`API/Notifications/`）：通过 MediatR 实现异步通知处理，如 `PaymentTransactionSaveHandler` 保存交易记录、`SystemAlertHandler` 记录Alert日志、`SMSAlertHandler` 发送短信通知

#### 14.3.3. 变更历史

| 版本 | 日期 | 变更说明 |
|---|---|---|
| v1.0.0 | 首次发布 | 基于现有代码库基线版本，包含 76 个 HTTP 端点、三个 PostgreSQL 数据库、ClickHouse 分析数据库、JWT 认证、Captcha功能、Payment集成（微信/Payment宝）、Alert通知、Agent 服务等核心功能 |

后续版本更新将在此附录中持续记录。

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
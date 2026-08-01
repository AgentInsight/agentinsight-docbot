## 1. 引言

本文档为 AGENTS.md Project（`agentinsight-demo` 统一前端演示平台）的 API 参考文档。AGENTS.md 是 `agentinsight-agents` 项目的统一前端演示平台，为 `agentinsight-docbot` 和 `agentinsight-researcher` 两个Agent提供 UI，前端仅承载 UI 展示与 API 调用，不承载任何业务逻辑 [AGENTS.md]。本文档详细描述前端提供的 Next.js API 路由 及所依赖的Agent后端 OpenAI 兼容接口，涵盖接口定义、请求参数、响应格式、认证方式与错误处理约定。

### 1.1. 编写目的

本文档面向前端开发者和系统集成方，旨在提供 AGENTS.md Project（`agentinsight-demo` 统一前端演示平台）完整的 API 参考说明。文档的核心目标包括：

- **接口契约明确化**：详细说明前端 `app/api/` 目录下 4 个 Next.js API 路由（认证 Cookie 设置/删除、用户信息获取、前端Config获取）的请求/响应格式，以及通过 `ApiClient` 单例调用的Agent后端 OpenAI 兼容接口（流式对话、反馈提交、文件上传、报告下载、仓库管理等）的调用约定 [lib/api-client.ts]。

- **架构边界界定**：阐明前端仅承载 UI 展示与 API 调用，不承载任何业务逻辑的架构原则。业务逻辑（Session编排、RAG 检索、工具调用、报告生成、人在回路审核等）由各Agent后端处理，前端职责限于渲染界面、收集用户输入、调用后端 OpenAI 兼容端点（SSE 流式）、解析并展示流式响应、管理客户端状态（Session/认证/Agent 选择）[AGENTS.md]。

等）由各Agent后端处理，前端职责限于渲染界面、收集用户输入、调用后端 OpenAI 兼容端点（SSE 流式）、解析并展示流式响应、管理客户端状态（Session/认证/Agent 选择）[AGENTS.md]。

- **集成指导**：为集成方提供双模式部署（`server` 模式经 Next.js rewrites 代理、`local` 模式浏览器直连后端端口）下的 Base URL 解析规则、SSE 流式数据格式（OpenAI `data:` 行格式 + 自定义 delta 扩展字段）、超时与中断机制（`fetchWithTimeout` 默认 30s 超时、流式请求通过外部 `` 中断）等关键集成信息 [lib/api-client.ts][AGENTS.md]。

- **开发规范约束**：强调所有后端 API 调用必须经 `apiClient`（`lib/api-client.ts` 导出的单例）统一管理，不推荐组件直接 `fetch` 后端业务接口，确保调用链路的可维护性与一致性 [AGENTS.md]。

通过本文档，读者应能够独立完成前端 API 的调用、调试与集成工作，并理解前端与Agent后端之间的接口依赖关系。

### 1.2. 适用范围

本文档适用于 AGENTS.md Project（`agentinsight-demo` 统一前端演示平台）的以下范围：

**应用范围**：

- `agentinsight-demo` 前端演示平台，为 `agentinsight-docbot`（默认端口 8068）与 `agentinsight-researcher`（默认端口 8066）两个Agent提供聊天、Config、流式展示与认证 UI [docs/architecture.md]。

bot`（默认端口 8068）与 `agentinsight-researcher`（默认端口 8066）两个Agent提供聊天、Config、流式展示与认证 UI [docs/architecture.md]。

- 前端 `app/api/` 目录下的 4 个 Next.js API 路由：
  - `POST /api/auth/cookie`：设置 httpOnly cookie（登录后调用）[lib/auth-api.ts:100-110]
  - `DELETE /api/auth/cookie`：删除 httpOnly cookie（登出时调用）[lib/auth-api.ts:100-110]
  - `GET /api/user-info`：获取用户信息 [tests/msw-handlers.ts:26]
  - `GET /api/config`：获取前端Config [tests/msw-handlers.ts:27]

- 通过 `ApiClient` 单例（`lib/api-client.ts`）调用的Agent后端 OpenAI 兼容接口，包括流式对话（`POST /v1/chat/completions`）、反馈提交（`POST /v1/feedback`）、文件上传（`POST /v1/files`）、报告下载（`GET /v1/reports/{id}/download`）、仓库管理（`/v1/repos` 系列）及 MCP Config接口（`/mcp/researcher/setting`、`/mcp/researcher/test`）[lib/api-client.ts]。

**不适用范围**：

- 本文档不涵盖Agent后端（`agentinsight-docbot` / `agentinsight-researcher`）内部业务逻辑的实现细节，如 LangGraph 编排、RAG 检索、MCP 工具调用、报告生成算法等后端能力 [docs/architecture.md]。

- 本文档不涉及前端 UI 组件的具体实现、Zustand的内部设计、i18n 国际化Config细节等非 API 相关的前端工程实践。

- 本文档不包含部署运维手册（如 Docker 构建、docker-compose 编排、Nginx Config等），相关内容请参考各Agent子项目的部署文档。

**目标读者**：

| 读者角色 | 关注重点 |
|----------|----------|
| 前端开发者 | Next.js API 路由 的请求/响应格式、SSE 流式解析、ApiClient 调用约定 |
| 系统集成方 | 双模式部署下的 Base URL 解析、OpenAI 兼容接口的认证与错误处理 |
| 测试工程师 | 接口契约验证、 mock handler 的模拟行为、端到端测试覆盖范围 |

### 1.3. 术语与缩略语

本文档涉及以下术语与缩略语，为保持代码标识符的可追溯性，所有代码符号（类名、函数名、常量名）均保留英文原文，不做翻译：

| 术语/缩略语 | 说明 |
|-------------|------|
| AGENTS.md | 项目名，`agentinsight-demo` 统一前端演示平台的代号，禁止翻译 |
| ApiClient | 统一 API 客户端单例，定义于 `lib/api-client.ts`，所有后端 API 调用均经此实例统一管理 [lib/api-client.ts] |
| SSE | Server-Sent Events，服务端推送流式传输协议。后端使用 OpenAI `data:` 行格式（无 `event:` 命名事件），自定义字段嵌入 delta 对象 [lib/api-client.ts] |
| httpOnly Cookie | HTTP 仅限 Cookie 认证方式。前端通过 `POST /api/auth/cookie` 设置、`DELETE /api/auth/cookie` 删除，浏览器端  无法读取该 Cookie 内容 [lib/auth-api.ts:100-110] |
| Zustand | 前端状态管理库，用于管理Session（session）、auth、Agent 选择（agent-store）等客户端状态 [AGENTS.md] |
| i18n | internationalization，前端通过 `next-intl` 实现多语言支持 |
|  | 单一事实来源（Single Source of Truth），项目规则以根目录 `AGENTS.md` 和本目录 `AGENTS.md` 为真源 [docs/architecture.md] |
|  | React Server Components，Next.js 15 的服务器端渲染组件模型 |
| Agent | Agent，本文档指 `agentinsight-docbot` 与 `agentinsight-researcher` 两个后端服务 |
|  | 部署模式环境变量（``），取值 `server`（默认，经 Next.js rewrites 代理）或 `local`（浏览器直连后端端口）[lib/api-client.ts] |

| delta | OpenAI 流式响应中的增量对象，后端在 delta 内嵌入 `progress` / `sources` / `` / `` / `` 自定义字段 [lib/api-client.ts] |

### 1.4. 参考文档

本文档的编写基于以下参考文档与代码仓库事实：

| 文档/资源 | 说明 |
|-----------|------|
| 主目录 `AGENTS.md` | 全项目公用规则，包含技术栈选型、安全合规红线、部署/测试规则等硬约束 [AGENTS.md] |
| `agentinsight-demo/AGENTS.md` | 子项目执行规则，约束 `agentinsight-demo/` 子项目内的前端工程实践，与主目录 `AGENTS.md` 配合使用 [AGENTS.md] |
| `docs/architecture.md` | 技术架构文档（v1.0，2026-07-30），描述项目定位、能力边界、默认端口（开发 3000 / 示例 8801）及真源规则 [docs/architecture.md] |
| Next.js 官方文档 | Next.js 15.1.0 框架的 API 路由、rewrites 代理、 等机制参考 |
| OpenAI API 兼容规范 | Agent后端遵循的 OpenAI 兼容接口规范，包括 `POST /v1/chat/completions` 流式对话格式、SSE `data:` 行格式等 [lib/api-client.ts] |
| `lib/api-client.ts` | API 客户端单例实现，定义所有后端接口的调用方法、Base URL 解析逻辑、SSE 解析与错误处理 [lib/api-client.ts] |
| `lib/agents.config.ts` | Agent Config定义，包含各 Agent 的端口、API Base URL、默认 Agent 等Config项 [lib/api-client.ts] |
| `tests/msw-handlers.ts` | （Mock Service Worker）测试Handler，定义前端 API 路由 的 mock 行为 [tests/msw-handlers.ts] |

### 1.5. 版本历史

| 版本 | 日期 | 说明 | 作者 |
|------|------|------|------|
| v1.0 | 2026-07-30 | 初始版本，基于 `agentinsight-demo` 代码仓库生成。技术栈：Next.js 15.1.0 + React 19.0.0 +  5.6.3（strict 模式）。本文档覆盖前端 4 个 Next.js API 路由 及通过 `ApiClient` 调用的Agent后端 OpenAI 兼容接口 | AGENTS.md 文档团队 |

**版本说明**：

- **v1.0（当前版本）**：首次发布，完整覆盖 `app/api/` 目录下 4 个 API 路由（认证 Cookie 设置/删除、用户信息获取、前端Config获取）及Agent后端接口（流式对话、反馈提交、文件上传、报告下载、仓库管理、MCP Config）。接口清单基于 `lib/api-client.ts` 与 `tests/msw-handlers.ts` 的代码事实提取。

- **后续版本规划**：随着 `agentinsight-demo` 前端功能的迭代（如新增 Agent、扩展 API 路由、调整认证机制），本文档将同步更新。版本更新遵循以下原则：
  - 新增接口或修改接口契约时，版本号递增（v1.1、v2.0 等），并在本表中记录变更摘要。
  - 仅修正文档错误或补充说明性内容时，修订版本号（v1.0.1 等），不改变主版本号。
  - 所有版本变更均需注明日期与变更说明，确保文档的可追溯性。

---

## 2. API 概览

本章共 4 个 HTTP 端点 (由源码 AST 确定性提取, 未经 LLM 改写)。

| # | Method | Route | Handler | Class |
|---|--------|-------|---------|-------|
| 1 | GET | `/api/user-info` |  |  |
| 2 | GET | `/api/config` |  |  |
| 3 | POST | `/api/auth/cookie` |  |  |
| 4 | DELETE | `/api/auth/cookie` |  |  |

---

## 3. 认证授权

本章共 4 个 HTTP 端点 (由源码 AST 确定性提取, 未经 LLM 改写)。

| # | Method | Route | Handler | Class |
|---|--------|-------|---------|-------|
| 1 | GET | `/api/user-info` |  |  |
| 2 | GET | `/api/config` |  |  |
| 3 | POST | `/api/auth/cookie` |  |  |
| 4 | DELETE | `/api/auth/cookie` |  |  |

---

## 4. API 路由 接口详情

本章共覆盖 4 个 HTTP 端点 (AST 确定性卡片, 未经 LLM 改写).

### 4.1. API-001 Endpoint-1 (GET `/api/user-info`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: http.get('/api/user-info', () => HttpResponse.json({ ip: '127.0.0.1' })),
- **源码位置**: `tests/msw-handlers.ts:26`
- **Handler**: ``
- **HTTP**: `GET`
- **Route**: `/api/user-info`

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
| `(未扫描到枚举定义)` | — | 来自 AST 枚举清单 |

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

**相关符号**

- AGENTS.md, AGENTS, ApiClient, TTLCache, POST, DELETE, GET, LoginPage, RegisterPage, generateStaticParams, LocaleLayout, LocalePage, DocbotChatLayout, ChatLayout, RootLayout, HomePage, McpSettingsPage, SettingsPage, AgentSwitcher, StaticOrb, generateStaticOrbs, ChatMessagesProps, MessageItemProps, SessionItemProps, ProgressMessageListProps, HistoryReportPanelProps, SessionMessagesResponse, report-type-select.test, getAgentByRouteSegment, session-isolation.test, docbot-chat-page.test, mcp-config-panel.test, progress-message-list, getAgentRouteSegment, history-report-panel, researcher-flow.spec, researcher-flow.test, ProgressMessageType, getAgentSettingPath, agents.config.test, mode-aware-content, report-type-select, session-store.test, setAuthTokenCookie, AgentSessionSlice, RepoCreateRequest, RepoUpdateRequest, agent-switch.test, agentinsight-demo, api-contract.test, chat-sidebar.test, createEmptyStream, docbot-input.test, docbot-store.test, playwright.config, repo-config-panel, stream-store.test, ModeAwareContent, NodeProgressData, ReportTypeSelect, agent-store.test, createEmptySlice, docbot-flow.spec, docbot-flow.test, fetchWithTimeout, getAgentCha

### 4.2. API-002 Endpoint-2 (GET `/api/config`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: http.get('/api/config', () => HttpResponse.json({ selfHost: false })),
- **源码位置**: `tests/msw-handlers.ts:27`
- **Handler**: ``
- **HTTP**: `GET`
- **Route**: `/api/config`

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
| `(未扫描到枚举定义)` | — | 来自 AST 枚举清单 |

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

**相关符号**

- AGENTS.md, AGENTS, ApiClient, TTLCache, POST, DELETE, GET, LoginPage, RegisterPage, generateStaticParams, LocaleLayout, LocalePage, DocbotChatLayout, ChatLayout, RootLayout, HomePage, McpSettingsPage, SettingsPage, AgentSwitcher, StaticOrb, generateStaticOrbs, ChatMessagesProps, MessageItemProps, SessionItemProps, ProgressMessageListProps, HistoryReportPanelProps, SessionMessagesResponse, report-type-select.test, getAgentByRouteSegment, session-isolation.test, docbot-chat-page.test, mcp-config-panel.test, progress-message-list, getAgentRouteSegment, history-report-panel, researcher-flow.spec, researcher-flow.test, ProgressMessageType, getAgentSettingPath, agents.config.test, mode-aware-content, report-type-select, session-store.test, setAuthTokenCookie, AgentSessionSlice, RepoCreateRequest, RepoUpdateRequest, agent-switch.test, agentinsight-demo, api-contract.test, chat-sidebar.test, createEmptyStream, docbot-input.test, docbot-store.test, playwright.config, repo-config-panel, stream-store.test, ModeAwareContent, NodeProgressData, ReportTypeSelect, agent-store.test, createEmptySlice, docbot-flow.spec, docbot-flow.test, fetchWithTimeout, getAgentCha

### 4.3. API-003 Endpoint-3 (POST `/api/auth/cookie`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: http.post('/api/auth/cookie', () => new HttpResponse(null, { status: 200 })),
- **源码位置**: `tests/msw-handlers.ts:28`
- **Handler**: ``
- **HTTP**: `POST`
- **Route**: `/api/auth/cookie`

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
| `(未扫描到枚举定义)` | — | 来自 AST 枚举清单 |

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

**相关符号**

- AGENTS.md, AGENTS, ApiClient, TTLCache, POST, DELETE, GET, LoginPage, RegisterPage, generateStaticParams, LocaleLayout, LocalePage, DocbotChatLayout, ChatLayout, RootLayout, HomePage, McpSettingsPage, SettingsPage, AgentSwitcher, StaticOrb, generateStaticOrbs, ChatMessagesProps, MessageItemProps, SessionItemProps, ProgressMessageListProps, HistoryReportPanelProps, SessionMessagesResponse, report-type-select.test, getAgentByRouteSegment, session-isolation.test, docbot-chat-page.test, mcp-config-panel.test, progress-message-list, getAgentRouteSegment, history-report-panel, researcher-flow.spec, researcher-flow.test, ProgressMessageType, getAgentSettingPath, agents.config.test, mode-aware-content, report-type-select, session-store.test, setAuthTokenCookie, AgentSessionSlice, RepoCreateRequest, RepoUpdateRequest, agent-switch.test, agentinsight-demo, api-contract.test, chat-sidebar.test, createEmptyStream, docbot-input.test, docbot-store.test, playwright.config, repo-config-panel, stream-store.test, ModeAwareContent, NodeProgressData, ReportTypeSelect, agent-store.test, createEmptySlice, docbot-flow.spec, docbot-flow.test, fetchWithTimeout, getAgentCha

### 4.4. API-004 Endpoint-4 (DELETE `/api/auth/cookie`)
- **鉴权**: 见源码注解 (`[Authorize]` / Bearer JWT / ApiKey); AST 未解析时默认需认证
- **描述**: http.delete('/api/auth/cookie', () => new HttpResponse(null, { status: 200 })),
- **源码位置**: `tests/msw-handlers.ts:29`
- **Handler**: ``
- **HTTP**: `DELETE`
- **Route**: `/api/auth/cookie`

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
| `(未扫描到枚举定义)` | — | 来自 AST 枚举清单 |

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

**相关符号**

- AGENTS.md, AGENTS, ApiClient, TTLCache, POST, DELETE, GET, LoginPage, RegisterPage, generateStaticParams, LocaleLayout, LocalePage, DocbotChatLayout, ChatLayout, RootLayout, HomePage, McpSettingsPage, SettingsPage, AgentSwitcher, StaticOrb, generateStaticOrbs, ChatMessagesProps, MessageItemProps, SessionItemProps, ProgressMessageListProps, HistoryReportPanelProps, SessionMessagesResponse, report-type-select.test, getAgentByRouteSegment, session-isolation.test, docbot-chat-page.test, mcp-config-panel.test, progress-message-list, getAgentRouteSegment, history-report-panel, researcher-flow.spec, researcher-flow.test, ProgressMessageType, getAgentSettingPath, agents.config.test, mode-aware-content, report-type-select, session-store.test, setAuthTokenCookie, AgentSessionSlice, RepoCreateRequest, RepoUpdateRequest, agent-switch.test, agentinsight-demo, api-contract.test, chat-sidebar.test, createEmptyStream, docbot-input.test, docbot-store.test, playwright.config, repo-config-panel, stream-store.test, ModeAwareContent, NodeProgressData, ReportTypeSelect, agent-store.test, createEmptySlice, docbot-flow.spec, docbot-flow.test, fetchWithTimeout, getAgentCha

---

## 5. Agent后端 API 参考

本章共 4 个 HTTP 端点 (由源码 AST 确定性提取, 未经 LLM 改写)。

| # | Method | Route | Handler | Class |
|---|--------|-------|---------|-------|
| 1 | GET | `/api/user-info` |  |  |
| 2 | GET | `/api/config` |  |  |
| 3 | POST | `/api/auth/cookie` |  |  |
| 4 | DELETE | `/api/auth/cookie` |  |  |

---

## 6. 错误码与通用约定

本章共 4 个 HTTP 端点 (由源码 AST 确定性提取, 未经 LLM 改写)。

| # | Method | Route | Handler | Class |
|---|--------|-------|---------|-------|
| 1 | GET | `/api/user-info` |  |  |
| 2 | GET | `/api/config` |  |  |
| 3 | POST | `/api/auth/cookie` |  |  |
| 4 | DELETE | `/api/auth/cookie` |  |  |

---

## 7. 部署与Config

本章共 4 个 HTTP 端点 (由源码 AST 确定性提取, 未经 LLM 改写)。

| # | Method | Route | Handler | Class |
|---|--------|-------|---------|-------|
| 1 | GET | `/api/user-info` |  |  |
| 2 | GET | `/api/config` |  |  |
| 3 | POST | `/api/auth/cookie` |  |  |
| 4 | DELETE | `/api/auth/cookie` |  |  |

---

## 附录: 代码术语与枚举（AST/扫描提取）

### 品牌/产品名

`AGENTS.md`, `AGENTS`

### 核心类名

`ApiClient`, `TTLCache`

### 枚举常量

`POST`, `DELETE`, `GET`

### 方法名

`LoginPage`, `RegisterPage`, `generateStaticParams`, `LocaleLayout`, `LocalePage`, `DocbotChatLayout`, `ChatLayout`, `POST`, `DELETE`, `GET`, `RootLayout`, `HomePage`, `McpSettingsPage`, `SettingsPage`, `AgentSwitcher`, `StaticOrb`, `generateStaticOrbs`, `ChatMessagesProps`, `MessageItemProps`, `SessionItemProps`, `HistoryReportPanelProps`, `ProgressMessageListProps`, `RepoSelect`, `ReportTypeSelect`, `ModeAwareContent`, `normalizeArgs`, `normalizeEnvVars`, `Toast`, `useToast`, `ToastItem`, `Tooltip`, `AgentConfig`, `getAgentConfig`, `getDefaultAgent`, `getAgentRouteSegment`, `getAgentByRouteSegment`, `getAgentChatPath`, `getAgentSettingPath`, `fetchWithTimeout`, `throwIfNotOk`, `extractToken`, `setAuthTokenCookie`, `AuthUser`, `AuthState`, `NavState`, `UploadedFile`, `AgentSessionSlice`, `createEmptySlice`, `SessionState`, `withSliceUpdate`, `AgentState`, `FinalReport`, `DocbotState`, `StreamContext`, `createEmptyStream`, `flushDeltas`, `StreamStore`, `ChatMessage`, `ToolCall`, `Source`, `SSEEvent`, `Session`, `SessionMessage`, `SessionMessagesResponse`, `ReportConfig`, `McpConfig`, `McpTestResult`, `McpSaveResponse`, `DownloadLink`, `RepoInfo`, `RepoCreateRequest`, `RepoUpdateRequest`, `RepoTestResult`, `DocbotReport`, `ProgressMessage`, `NodeProgressData`, `SourceItem`, `ToolCallData`, `ReportData`, `getMessages`, `getPath`, `interpolate`, `getTranslator`, `detectLocale`, `middleware`, `headers`, `rewrites`

### HTTP 路由清单

- `/api/auth/cookie`
- `/api/config`
- `/api/user-info`

## 附录: 完整 API 清单（AST 确定性提取）

### 模块路径前缀

- `/api/auth`
- `/api/config`
- `/api/user-info`

| 标识 | 方法 | 路径 | 描述 | 鉴权 |
|------|------|------|------|------|
| API-001 | GET | `/api/user-info` | - | Bearer |
| API-002 | GET | `/api/config` | - | Bearer |
| API-003 | POST | `/api/auth/cookie` | - | Bearer |
| API-004 | DELETE | `/api/auth/cookie` | - | Bearer |

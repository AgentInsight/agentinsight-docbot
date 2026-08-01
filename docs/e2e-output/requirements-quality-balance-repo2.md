## 1. 引言

**多 Agent 切换缺乏统一入口**：用户需在不同 Agent 间切换使用，但缺乏统一的导航与切换机制。AGENTS.md 通过 `lib/agents.config.ts` 作为 Agent Config SSOT，定义所有 Agent 的 id/port/apiBaseUrl/features，并驱动 UI 显隐与 API 路由 [lib/agents.config.ts:1-80]。features 标志位（multiAgent、humanReview、repoConfig、reportGeneration、mcpConfig）控制组件显隐，避免在组件内硬编码 Agent 判断 [AGENTS.md:80-85]。

**流式交互体验不一致**：各 Agent 的响应输出格式与流式传输方式不统一，用户缺乏一致的流式交互界面。前端通过 `lib/api-client.ts` 统一封装所有后端 RESTful 调用与 SSE 流式（Server-Sent Events）解析 [lib/api-client.ts]，`lib/stream-store.ts` 负责流式消息状态管理，处理 SSE 事件解析、RAF batching 优化与后台流并发控制 [lib/stream-store.ts]。

**认证状态管理复杂**：JWT Bearer Token 需要在客户端 API 调用与服务端路由守卫之间共享，但浏览器原生 fetch 无法设置 httpOnly cookie，middleware（Edge Runtime）只能读 cookie 而无法读 localStorage。AGENTS.md 采用双存储方案：localStorage 供客户端 API 调用携带 `Authorization: Bearer <token>` 头，httpOnly cookie 供 middleware 路由守卫读取 [AGENTS.md:100-120]。

 API 调用携带 `Authorization: Bearer <token>` 头，httpOnly cookie 供 middleware 路由守卫读取 [AGENTS.md:100-120]。

**SELF_HOST 部署模式缺乏免登录能力**：在私有化部署场景下，用户不应被强制要求登录。AGENTS.md 通过运行时变量 `SELF_HOST=true` 使 middleware 跳过登录守卫，`useAuthStore.isAuthed()` 始终返回 true，并显示客户端 IP（经 `/api/user-info` 获取）[AGENTS.md:100-120]。

### 1.1. 文档范围

本文档覆盖 AGENTS.md（统一前端演示平台）前端演示平台的以下功能域：

| 功能域 | 说明 | 关键实现 |
|--------|------|----------|
| 用户认证 | JWT Bearer Token 双存储（localStorage + httpOnly cookie），SELF_HOST 免登录模式 | `lib/auth-store.ts`、`middleware.ts` |
| 多 Agent 切换与Session隔离 | docbot/researcher 双 Agent 切换，Session按 Agent 独立保存与恢复 | `lib/agents.config.ts`、`lib/session-store.ts` |
| 聊天流式交互 | SSE 流式（Server-Sent Events）消息解析、渲染与并发控制 | `lib/api-client.ts`、`lib/stream-store.ts` |
| Session CRUD | Session创建/列表/删除/重命名，按 Agent 隔离，上限 10 个/User | `lib/session-store.ts`、`lib/api-client.ts` |
| MCP Config管理 | MCP 工具Config的查看与保存（researcher Agent） | `components/settings/mcp-config-panel.tsx` |
| 代码仓库管理 | 仓库Config、同步状态与测试（docbot Agent） | `components/settings/repo-config-panel.tsx` |
| 人在回路（Human-in-the-loop）审核 | 人工审核面板（researcher Agent） | `components/review/review-panel.tsx` |
| i18n 国际化 | 中英双语资源加载与切换 | `messages/index.ts`、`messages/zh.json`、`messages/en.json` |

-panel.tsx` |
| i18n 国际化 | 中英双语资源加载与切换 | `messages/index.ts`、`messages/zh.json`、`messages/en.json` |

本文档不覆盖以下内容：后端Agent（Agent）的业务逻辑（Session编排、RAG 检索、工具调用、报告生成策略、人在回路状态机等）[AGENTS.md:19-22]；数据库直接访问（前端不直连 PostgreSQL/Qdrant/Redis）[docs/architecture.md:120-125]；JWT Token 解析与 user_id 获取（由后端完成，middleware 仅判断 cookie 是否存在）[AGENTS.md:120-122]。

### 1.2. 术语与缩略语

| 术语 | 说明 |
|------|------|
| AGENTS.md | 本前端演示平台的项目名，也是子项目执行规则文件名 |
| Agent | Agent（Agent）实例，当前包括 agentinsight-docbot 与 agentinsight-researcher |
| SSE | Server-Sent Events，服务端推送事件流，用于聊天流式响应 |
| JWT Bearer Token | JSON Web Token，通过 `Authorization: Bearer <token>` 头传递的认证凭证 |
| Zustand Store | 基于 Zustand 的客户端状态管理，包括 agent-store、auth-store、session-store、stream-store、docbot-store、nav-store [AGENTS.md:130-140] |
| locale | 区域设置，支持 zh（简体中文）与 en（English） |
| middleware | Next.js Edge Runtime 路由守卫，负责登录校验与 locale 检测 |
| SELF_HOST | 运行时部署模式，为 true 时跳过登录守卫，实现免登录访问 |
| SSOT | Single Source of Truth，SSOT（单一事实来源），如 `lib/agents.config.ts` 为 Agent Config SSOT |
| MCP | Model Context Protocol，模型上下文协议，用于工具调用Config |
| CRUD | Create/Read/Update/Delete，Session的创建、列表、删除与重命名操作 |

### 1.3. 参考文档

| 文档 | 说明 |
|------|------|
| 主目录 AGENTS.md | 全项目公用规则，含技术栈选型、安全合规红线、部署/测试规则 |
| docs/architecture.md | 架构文档，定义项目定位、能力边界、目录结构与模块边界 |
| agentinsight.goldebridge.com | 生产环境域名 |

### 1.4. 版本历史

| 版本 | 日期 | 作者 | 变更说明 |
|------|------|------|----------|
| v1.0 | 待定 | 技术文档组 | 初始版本，基于代码仓库 v6-P0-D 迭代检索结果编写 |

---

## 2. 产品概述与用户分析

演示平台" [docs/architecture.md:1-4]，并在 AGENTS.md 中进一步强调"仅承载 UI 展示与 API 调用；不承载任何业务逻辑" [AGENTS.md:19-22]。

产品的能力边界由 `lib/agents.config.ts` 中的 `AgentConfig` 接口统一定义，每个 Agent 通过 `features` 标志位（`multiAgent` / `humanReview` / `repoConfig` / `reportGeneration` / `mcpConfig`）声明自身能力，前端组件读取这些标志位控制 UI 元素显隐，而非硬编码 `if (agentId === 'xxx')` 判断 [lib/agents.config.ts:1-80]。当前注册的两个 Agent 能力对比如下：

| Agent ID | 端口 | 输入组件 | 特性标志位 | 设置面板 |
|----------|------|----------|-----------|----------|
| `agentinsight-docbot` | 8068 | `` | repoConfig、reportGeneration | `` |
| `agentinsight-researcher` | 8066 | `` | multiAgent、humanReview、mcpConfig | `` |

产品定位的另一个关键维度是**部署模式灵活性**。前端支持 `` 运行时变量控制登录守卫行为：`=true` 时跳过登录，`=false` 时未登录用户访问受保护路由将重定向到 `/login` [AGENTS.md:4.3]。这一设计使产品既能作为 SaaS 演示平台（需认证），也能作为本地私有化部署的演示工具（免登录）。

### 2.1. 价值主张

**核心价值主张**：为所有 Agent 提供统一、多 Agent 的 UI 界面，用户无需了解后端编排细节即可使用 docbot 和 researcher 能力。

具体而言，产品向三类利益相关方传递以下价值：

| 利益相关方 | 价值主张 | 支撑功能 |
|-----------|---------|---------|
| **终端用户** | 通过统一聊天界面与多个 AI Agent 交互，无需关心后端架构 | AgentSwitcher 切换、SSE 流式（Server-Sent Events）聊天 [lib/api-client.ts:100-150] |
| **开发者** | 通过 docbot 自动生成 8 种技术文档报告，支持 5 种输出格式 | 报告生成、仓库管理 [lib/agents.config.ts:30-45] |
| **研究者** | 通过 researcher 进行深度研究，支持 MCP 工具扩展与人在回路（Human-in-the-loop）审核 | MCP Config、文件上传、反馈提交 [lib/api-client.ts:185-222] |

价值主张的落地依赖三个关键设计决策：

1. **Agent Config （Single Source of Truth）**：所有 Agent 的元信息集中在 `lib/agents.config.ts` 声明，组件与 API 客户端均从此读取，新增 Agent 只需追加Config数组、新建路由、添加翻译键三步 [AGENTS.md:4.1]。这一设计使多 Agent 扩展成本极低，是"统一多 Agent UI"的技术基石。

2. **OpenAI 兼容 SSE 流式（Server-Sent Events）协议**：前端通过 `POST /v1/chat/completions` 与后端通信，SSE 流式（Server-Sent Events）返回 content、progress、sources、 等结构化字段 [lib/api-client.ts:100-150]。统一协议使前端无需为不同 Agent 定制通信逻辑，同一套 `api-client.ts` 即可服务所有 Agent。

3. **前端零业务逻辑约束**：RAG 检索、工具调用编排、状态机、报告生成策略、MCP 工具执行、人在回路状态机等均在后端处理 [AGENTS.md:19-22]。前端不直接读写 Postgres/Qdrant/Redis，也不实现 RAG/工具调用/状态机编排 [docs/architecture.md:1-4]。这一约束保证了前端的轻量性与可维护性，使用户无需感知后端复杂度。

### 2.2. 北极星指标

**北极星指标（North Star Metric）**：成功完成的流式聊天交互次数（通过 SSE 成功消费到 `[]` 标记的 stream 计数）。

该指标的定义与产品价值主张高度对齐——产品的核心价值是"用户通过流式聊天与 Agent 交互并获取完整响应"，因此只有**完整走完一次流式交互**（从发送消息到成功消费 `[]` 终止标记）才计为一次有效交互。指标定义在 `lib/stream-store.ts` 的 SSE 事件解析逻辑中，前端通过监听流式事件流，在收到 `[]` 标记时判定该次交互成功完成 [lib/stream-store.ts:200-280]。

选择该指标的理由：

| 维度 | 说明 |
|------|------|
| **反映核心价值** | 流式聊天是产品最核心的交互模式，覆盖 docbot 与 researcher 两个 Agent |
| **可量化可Trace** | 通过 SSE 事件流中的 `[]` 标记可精确计数，不依赖主观判断 |
| **排除无效交互** | 仅统计"成功完成"的交互，排除中断、超时、报错的失败流 |
| **驱动增长闭环** | 该指标提升意味着用户更频繁地完成有价值的对话，间接反映报告生成、研究任务的完成率 |

指标的数据来源为前端 `stream-store.ts` 的流式消息状态管理模块，该模块负责 SSE 事件解析、 batching 优化与后台流并发控制 [lib/stream-store.ts:1-3]。每次流式交互结束时，若成功消费到 `[]` 标记，则计数加一。

### 2.3. Persona 矩阵

基于产品功能边界与用户使用场景，定义三类核心 Persona：

| Persona | 角色描述 | 使用 Agent | 核心需求 | 关键功能依赖 |
|---------|---------|-----------|---------|-------------|
| **开发者** | 软件工程师、技术负责人，需要为代码仓库生成技术文档 | docbot | 自动生成架构/设计/需求/测试用例等报告 | 仓库管理、报告生成 [lib/agents.config.ts:30-45] |
| **研究者** | 数据分析师、研究员，需要进行深度信息检索与分析 | researcher | 上传文件、Config MCP 工具、执行深度研究 | MCP Config、文件上传、人在回路（Human-in-the-loop）审核 [lib/api-client.ts:185-222] |
| **管理员** | 系统运维、平台管理员，负责Config与维护 Agent Service | docbot + researcher | 管理仓库连接、Config MCP Service、监控系统状态 | 仓库 CRUD、MCP CRUD、连接测试 [lib/api-client.ts:250-310] |

各 Persona 的典型使用场景：

- **开发者**：在 docbot 聊天页通过 `` 组件选择目标仓库，选择报告类型（8 种：architecture/design/requirements/testcase/optimization/performance/defect/）与输出格式（markdown/html/pdf/docx/json），发送消息后实时查看 Markdown 渲染与进度条，流式结束后下载报告 [lib/agents.config.ts:35-45]。开发者的核心诉求是"减少文档编写时间，保证文档与代码同步"。

son），发送消息后实时查看 Markdown 渲染与进度条，流式结束后下载报告 [lib/agents.config.ts:35-45]。开发者的核心诉求是"减少文档编写时间，保证文档与代码同步"。

- **研究者**：在 researcher 聊天页通过 `` 输入研究问题，可选上传文件（`POST /v1/files`）或Config MCP 工具（支持 stdio/sse/ 三种传输），发送消息后触发流式研究，SSE 返回 content +  + sources [lib/stream-store.ts:200-280]。当后端需要审核时，通过  或 SSE 发送 ``，研究者在 `review-panel` 提交反馈到 `POST /v1/feedback` [lib/types.ts:210]。研究者的核心诉求是"获取深度、可追溯的研究结果"。

- **管理员**：在 docbot 设置页（`/mcp/docbot/setting`）通过 `` 管理仓库，支持 7 种平台和 4 种认证方式；在 researcher 设置页通过 `` 管理 MCP 服务Config，支持系统Config克隆 [lib/api-client.ts:185-215]。管理员的核

---

## 3. 功能需求

### 3.1. FR-001 获取客户端 IP [优先级: Must]

- **用户故事**：作为用户，我希望系统能获取我的客户端 IP，以便在 SELF_HOST 模式下显示访问来源。
- **主流程**：
  1. 应用启动时，`useAuthStore` 中的 `fetchUserIp` 方法被调用 (`lib/auth-store.ts:60-70`)。
  2. 方法优先从 `X-Forwarded-For` 请求头获取 IP，若不存在则回退到 `X-Real-IP`，最后回退到 `remoteAddress` (`middleware.ts:40-45`)。
  3. 获取到的 IP 存入内存中的 `userIp` 字段，供 UI 展示。
- **验收标准**：
  - [ ] AC1: 在 Nginx 反向代理场景下，获取到的 IP 为真实客户端 IP，而非代理服务器 IP。
  - [ ] AC2: 在直连场景下（无代理），获取到的 IP 为 `remoteAddress`。
  - [ ] AC3: `userIp` 在页面刷新后重新获取，不残留旧值。
- **业务规则**：
  - BR-001: IP 获取优先级为 `X-Forwarded-For` > `X-Real-IP` > `remoteAddress`。该规则确保在 Nginx 反向代理场景下能正确获取真实客户端 IP，而非代理服务器 IP。
  - BR-002: `userIp` 不持久化到 localStorage，每次启动重新获取，避免 IP 变更后残留陈旧值 (`lib/auth-store.ts:80-82`)。

### 3.2. FR-002 获取运行时Config [优先级: Must]

- **用户故事**：作为前端开发者，我希望在运行时获取白名单内的Config项，以便客户端组件能安全读取环境变量。
- **主流程**：
  1. 客户端组件调用 `GET /api/config` 接口获取运行时Config (`app/api/config/route.ts:1-8`)。
  2. 服务端路由从环境变量中读取白名单内的Config字段（当前仅 `SELF_HOST`），并返回 JSON 响应。
  3. 客户端 `useAuthStore` 中的 `fetchConfig` 方法接收响应，将 `selfHost` 值存入内存状态 (`lib/auth-store.ts:20-24`)。
- **验收标准**：
  - [ ] AC1: `GET /api/config` 返回 `{"selfHost": true}` 或 `{"selfHost": false}`。
  - [ ] AC2: 响应中不包含数据库连接串、密钥等敏感环境变量。
  - [ ] AC3: 客户端组件无法直接读取 `SELF_HOST` 环境变量，必须通过 `/api/config` 接口获取。
- **业务规则**：
  - BR-003: `/api/config` 仅暴露白名单内Config字段（当前仅 `selfHost`），禁止泄露数据库连接串、密钥等敏感环境变量 (`app/api/config/route.ts:1-8`)。
  - BR-004: `SELF_HOST` 为运行时环境变量（非 `NEXT_PUBLIC_` 前缀），客户端组件无法直接读取，必须通过 `/api/config` 接口在运行时获取 (`lib/auth-store.ts:20-24`)。

### 3.3. FR-003 设置认证 Cookie [优先级: Must]

- **用户故事**：作为登录用户，我希望在登录成功后设置认证 Cookie，以便后续访问受保护页面时保持登录态。
- **主流程**：
  1. 用户通过登录表单提交凭证，前端直连 `NEXT_PUBLIC_AUTH_API_BASE` 发送登录请求 (`lib/auth-api.ts:20-30`)。
  2. 登录成功后，前端从响应体/头多源提取 JWT Token（5 种来源容错）(`lib/auth-api.ts:50-90`)。
  3. Token 存入 localStorage（供客户端 API 调用）(`lib/auth-store.ts:40-50`)。
  4. 前端调用 `POST /api/auth/cookie` 接口，将 Token 写入 httpOnly Cookie (`lib/auth-api.ts:100-110`)。
  5. `/api/auth/cookie` 路由的 `POST` 方法构造响应对象，通过 `response.cookies.set("auth-token", token, { httpOnly: true, secure: true, sameSite: "lax" })` 设置名为 `auth-token` 的 Cookie，并返回 `{"success": true}` (`app/api/auth/cookie/route.ts:40-60`)。
  6. 设置成功后，用户访问受保护页面时，middleware 检测到 `auth-token` Cookie 存在，放行请求 (`middleware.ts:20-35`)。
- **验收标准**：
  - [ ] AC1: 登录成功后，浏览器中存在名为 `auth-token` 的 Cookie，且属性为 `httpOnly`。
  - [ ] AC2: `POST /api/auth/cookie` 返回 HTTP 200 与 `{"success": true}`。
  - [ ] AC3: 设置 Cookie 后，访问受保护页面（如 `/agent/researcher/chat`）不会被重定向到 `/login`。
  - [ ] AC4: Cookie 的 `secure` HTTPS下为 `true`。
- **业务规则**：
  - BR-005: 认证 Cookie 必须设置为 `httpOnly`，禁止客户端 JavaScript 直接读取 (`AGENTS.md` 第 9.1 节硬约束)。
  - BR-006: 登录成功后必须同时设置 localStorage 和 httpOnly Cookie，两者缺一不可 (`AGENTS.md` 第 9.1 节硬约束)。
  - BR-007: Cookie 设置失败时，登录流程应中断并提示用户，避免出现 localStorage 有 Token 但 Cookie 缺失的不一致状态。

### 3.4. FR-004 清除认证 Cookie [优先级: Must]

- **用户故事**：作为登出用户，我希望清除 Cookie 以退出登录态。
- **主流程**：
  1. 用户点击登出按钮，`useAuthStore` 中的 `logout` 方法被调用 (`lib/auth-store.ts:83-91`)。
  2. `logout` 首先通过 `set({ user: null })` 清除 localStorage 中的用户状态（含 Token）(`lib/auth-store.ts:85`)。
  3. 随后向 `/api/auth/cookie` 发起 `DELETE` 请求，清除 httpOnly Cookie (`lib/auth-store.ts:87-90`)。
  4. `/api/auth/cookie` 路由的 `DELETE` 方法构造响应对象，通过 `response.cookies.delete("auth-token")` 删除名为 `auth-token` 的 Cookie，并返回 `{"success": true}` (`app/api/auth/cookie/route.ts:72-77`)。
  5. 若 `DELETE` 请求失败（网络错误等），`logout` 捕获异常并忽略，客户端状态已清除，不阻塞跳转流程 (`lib/auth-store.ts:88-90`)。
  6. 登出完成后，用户访问受保护页面时，middleware 检测不到 `auth-token` Cookie，重定向到 `/login` 页面。
- **验收标准**：
  - [ ] AC1: 登出后，浏览器中不存在名为 `auth-token` 的 Cookie。
  - [ ] AC2: 登出后，localStorage 中 `auth-storage` 键的 `user` 字段为 `null`。
  - [ ] AC3: 登出后访问受保护页面（如 `/agent/researcher/chat`），被重定向到 `/login`。
  - [ ] AC4: `DELETE /api/auth/cookie` 返回 HTTP 200 与 `{"success": true}`。
  - [ ] AC5: 即使 `DELETE` 请求失败，客户端 localStorage 状态仍被清除，用户界面立即退出登录态。
- **业务规则**：
  - BR-008: 登出必须同时清除 localStorage 和 httpOnly Cookie，禁止仅清除一处 (`AGENTS.md` 第 9.1 节硬约束)。
  - BR-009: 登出流程不阻塞跳转，`DELETE` 请求失败时忽略错误，确保用户体验 (`lib/auth-store.ts:88-90`)。

---

## 4. 非功能需求

本章节定义 AGENTS.md 统一前端演示平台（`统一前端演示平台`）的非功能需求。该平台为 `agentinsight-docbot` 和 `agentinsight-researcher` 两个Agent（Agent）提供 UI，前端仅承载 UI 展示与 API 调用，不承载任何业务逻辑（`docs/architecture.md:1-4`）。所有非功能需求均以可验证的验收标准定义，并引用代码仓库中的具体实现位置作为佐证。

### 4.1. 性能 (NFR-P)

性能需求聚焦于流式渲染的响应性与后台任务的资源控制。由于前端通过 SSE 流式（Server-Sent Events）接收后端 token 推送，高频的 `setState` 调用会直接导致 UI 线程阻塞与渲染卡顿，因此性能优化的核心在于降低状态更新频率与限制后台并发资源占用。

| 编号 | 需求描述 | 验收标准 | 实现位置 |
|------|---------|---------|---------|
| NFR-P-001 |  Batching 降低状态更新频率 | 在单帧内合并多次 token 推送为一次 `set()`，`setState` 调用频率降低约 50 倍 | `lib/stream-store.ts` 中 `pendingDeltas` 缓冲区与 `flushDeltas()`  回调机制 |
| NFR-P-002 |  驱逐非活跃 StreamContext | `=1`，非活跃超过 10 个 StreamContext 时按  策略驱逐 | `lib/stream-store.ts` 中 `=10` 常量与驱逐逻辑 |

NFR-P-001 的实现机制为：SSE 事件到达时，`appendContentDelta` 将增量内容推入 `pendingDeltas` 缓冲区（按 sessionId 索引），而非立即写入 Zustand state。`rafScheduled` 标志确保每帧仅调度一次 `flushDeltas()` 回调，该回调在单帧内合并所有待写入的 delta 并执行一次 `useStreamStore.setState()`（`lib/stream-store.ts`）。此机制将高频的 token 级更新聚合为帧级更新，显著降低 React 渲染压力。

a 并执行一次 `useStreamStore.setState()`（`lib/stream-store.ts`）。此机制将高频的 token 级更新聚合为帧级更新，显著降低 React 渲染压力。

NFR-P-002 针对多Session场景的内存控制：`=1` 限制后台流式任务最多 1 个（前台 1 个 + 后台 1 个 = 2 个并发研究实例），防止用户切换Session后旧Session的流式请求无限占用资源。同时，`=10` 定义了非活跃 StreamContext 的最大保留数，超过阈值时按  策略驱逐最早的非活跃上下文，避免长时间使用导致的内存泄漏（`lib/stream-store.ts`）。

### 4.2. 安全 (NFR-S)

安全需求覆盖认证凭据保护、HTTP 安全响应头Config以及  防护三个维度。前端虽不承载业务逻辑，但作为用户与后端Agent（Agent）之间的桥梁，必须确保 JWT Token 等敏感信息不泄露，并通过标准安全响应头降低攻击面。

| 编号 | 需求描述 | 验收标准 | 实现位置 |
|------|---------|---------|---------|
| NFR-S-001 | JWT Token 禁止 `console.log` 输出 | 代码库中零日志泄露， 规则与人工审查双重保障 |  规则Config + 人工审查（`AGENTS.md` 不推荐清单第 13 条） |
| NFR-S-002 | 安全响应头包含 X-Frame-Options、 等 5 类 | 响应头完整，包含 `X-Frame-Options: `、`X-Content-Type-Options: nosniff`、`Referrer-Policy`、`Strict-Transport-Security`、`Permissions-Policy` | `next.config.ts:20-35` 安全响应头Config |
| NFR-S-003 | httpOnly Cookie 防  | Cookie 无法通过  读取，`document.cookie` 不包含认证 Token | `POST /api/auth/cookie` 接口实现（`tests/msw-handlers.ts:28`） |

 无法通过  读取，`document.cookie` 不包含认证 Token | `POST /api/auth/cookie` 接口实现（`tests/msw-handlers.ts:28`） |

NFR-S-001 将 Token 日志泄露列为安全合规红线，属于"❌ Never"级别的硬约束，违例即阻断合并并提 P0（`AGENTS.md` 第 10 节）。该约束通过  规则（`no-console` 针对含 token 对象）与人工代码审查双重保障。

NFR-S-002 在 `next.config.ts` 中集中Config 5 类安全响应头：`X-Frame-Options: ` 禁止点击劫持、`X-Content-Type-Options: nosniff` 禁止  嗅探、`Referrer-Policy: strict-origin-when-cross-origin` 限制 Referer 泄露、`Strict-Transport-Security: max-age=63072000; includeSubDomains; preload` 强制 HTTPS、`Permissions-Policy: camera=(), microphone=(), geolocation=()` 禁用敏感设备能力。同时 `poweredByHeader: false` 关闭 `X-Powered-By` 响应头，避免暴露技术栈（`AGENTS.md` 第 7.2 节）。

NFR-S-003 通过 `POST /api/auth/cookie` 接口将 JWT Token 写入 httpOnly Cookie（`tests/msw-handlers.ts:28`），该 Cookie 无法通过  读取，从根本上阻断  攻击窃取 Token 的路径。middleware 仅判断 Cookie 是否存在以决定路由守卫逻辑，不解析 Token 内容（`AGENTS.md` 第 120-122 行）。

### 4.3. 兼容性 (NFR-C)

兼容性需求主要针对测试环境与部署模式两个维度。测试环境需要 polyfill 浏览器 API 以保证 jsdom 环境下组件测试可正常运行；部署模式需要同时支持 server 反向代理与 local 直连两种拓扑。

针对测试环境与部署模式两个维度。测试环境需要 polyfill 浏览器 API 以保证 jsdom 环境下组件测试可正常运行；部署模式需要同时支持 server 反向代理与 local 直连两种拓扑。

| 编号 | 需求描述 | 验收标准 | 实现位置 |
|------|---------|---------|---------|
| NFR-C-001 | jsdom 环境 polyfill（crypto.randomUUID/scrollIntoView/requestAnimationFrame） | 测试环境正常运行，组件测试不因缺失浏览器 API 而失败 | `tests/setup.ts:10-25` polyfill Config |
| NFR-C-002 | 双部署模式兼容（server/local） | 两种模式下 API 调用均正常，baseUrl 解析正确 | `lib/api-client.ts:30-50` 双模式控制逻辑 |

NFR-C-001 在 `tests/setup.ts` 中为 jsdom 环境补齐 `crypto.randomUUID`、`scrollIntoView`、`requestAnimationFrame` 等浏览器 API，确保组件测试（如 `chat-messages`、`session-store.test` 等）在 Node 测试环境中不因 API 缺失而报错。

stAnimationFrame` 等浏览器 API，确保组件测试（如 `chat-messages`、`session-store.test` 等）在 Node 测试环境中不因 API 缺失而报错。

NFR-C-002 由 `` 环境变量控制（构建时内联）：`server` 模式（默认）下，浏览器经 Next.js `rewrites` 反向代理 `/api/(已移除无关路径) → `http://localhost:8068/*`，同源请求无 ；`local` 模式下，浏览器直连 `http://localhost:{agent.port}`，需后端Config （`AGENTS.md` 第 4.2 节）。`apiClient.getBaseUrl()` 在 server 模式返回 `agent.apiBaseUrl`，local 模式返回 `http://localhost:${agent.port}`，当前 Agent 从 `useAgentStore` 运行时读取， 降级到默认 Agent（`lib/api-client.ts:30-50`）。

### 4.4. 可维护性 (NFR-M)

可维护性需求强调类型安全与 i18n 字符串管理的规范性。类型定义与后端 Pydantic 模型对齐可避免前后端接口字段不一致导致的运行时错误；i18n 禁止硬编码字符串可确保多语言扩展时无需修改组件代码。

| 编号 | 需求描述 | 验收标准 | 实现位置 |
|------|---------|---------|---------|
| NFR-M-001 | 所有类型定义与后端 Pydantic 模型对齐 | 类型安全，前后端接口字段一致，编译期捕获类型错误 | `lib/types.ts` 集中管理类型定义 |
| NFR-M-002 | i18n 禁止组件内硬编码字符串 | 代码库中无硬编码中英文字符串，所有文案通过翻译函数获取 | `messages/{zh,en}.json` + `useTranslations` / `getTranslator` |

码字符串 | 代码库中无硬编码中英文字符串，所有文案通过翻译函数获取 | `messages/{zh,en}.json` + `useTranslations` / `getTranslator` |

NFR-M-001 要求所有  类型定义（如 `ChatMessage`、`ToolCall`、`Source`、`SSEEvent`、`StreamContext` 等）集中在 `lib/types.ts` 中管理，并与后端 Pydantic 模型字段一一对应。`session-store.ts` 与 `stream-store.ts` 均从 `lib/types.ts` 导入类型（`lib/session-store.ts:3`、`lib/stream-store.ts:3`），确保状态管理与 API 层使用同一套类型定义。

NFR-M-002 将 i18n 硬编码列为"不推荐"清单第 9 条（`AGENTS.md` 第 10 节），要求所有用户可见文案通过 `useTranslations`（客户端组件）或 `getTranslator`（服务端组件）从 `messages/{zh,en}.json` 资源文件获取。`messages/index.ts` 提供 `getTranslator` / `detectLocale` 工具函数（`messages/index.ts:1-80`），新增语言时仅需添加对应 JSON 资源文件，无需修改组件代码。

### 4.5. 本地化 (NFR-L)

本地化需求定义平台支持的语言范围与切换机制。基于 next-intl 4.0 的 App Router 集成方案，locale 检测与路由前缀由 middleware 统一处理。

| 编号 | 需求描述 | 验收标准 | 实现位置 |
|------|---------|---------|---------|
| NFR-L-001 | 支持 zh/en 两种 locale | 中英切换正常，页面文案随 locale 变化 | `next-intl 4.0` + `middleware.ts` locale 检测 |

-L-001 | 支持 zh/en 两种 locale | 中英切换正常，页面文案随 locale 变化 | `next-intl 4.0` + `middleware.ts` locale 检测 |

NFR-L-001 zhen两种语言。`middleware.ts` 负责 locale 检测与路由处理（`middleware.ts:3` 导入 `messages/index.ts`），通过 `detectLocale` 工具函数识别用户偏好语言，并重写到对应 locale 前缀的路由。`messages/index.ts` 加载 `messages/{zh,en}.json` 资源文件，通过 `getTranslator` 提供类型安全的翻译函数（`messages/index.ts:1-80`）。next-intl 4.0 与 Next.js App Router 原生集成，Server/Client 组件均可使用翻译能力（`AGENTS.md` 第 1 节技术栈表）。

---

## 5. 接口需求

`统一前端演示平台` 是 `agentinsight-agents` 项目的统一前端演示平台，为 `agentinsight-docbot` 和 `agentinsight-researcher` 两个Agent（Agent）提供 UI。前端仅承载 UI 展示与 API 调用，不承载任何业务逻辑——业务逻辑（Session编排、RAG 检索、工具调用、报告生成、人在回路（Human-in-the-loop）审核等）由各Agent（Agent）后端处理。本章定义前端 `app/api/` 目录下 4 个 HTTP 端点的接口需求，这些端点由 `tests/msw-handlers.ts` 中的 Mock Service Worker Handler覆盖，用于前端开发与测试阶段的接口模拟。

### 5.1. 接口需求总览

| 接口标识 | 方法 | 路径 | 鉴权 | 功能描述 |
|---------|------|------|------|---------|
| IR-001 | GET | `/api/user-info` | 无 | 获取客户端 IP 地址 |
| IR-002 | GET | `/api/config` | 无 | 获取运行时Config（ 模式） |
| IR-003 | POST | `/api/auth/cookie` | 无 | 设置 JWT httpOnly Cookie |
| IR-004 | DELETE | `/api/auth/cookie` | 无 | 清除 JWT httpOnly Cookie |

**Base URL**：`https://agentinsight.goldebridge.com` 或 `your-domain.com`（部署环境决定）。

**数据格式**：所有请求与响应均使用 JSON（`Content-Type: application/json`），字符集为 UTF-8。

**认证方式**：Cookie 需携带 JWT 时存在。`middleware.ts` 仅判断 `auth-token` cookie 是否存在，不解析 token 内容；token 解析与  获取由后端完成。

**错误码**：基于 HTTP 状态码 200/400/401/500，不使用业务错误码。

### 5.2. 获取客户端 IP (GET /api/user-info)

**鉴权**：无

**描述**：返回发起请求的客户端 IP 地址。该接口在  模式下由前端调用，用于在界面上展示当前访问者的 IP 信息。接口无请求参数，响应体为包含 `ip` 字段的 JSON 对象。

#### 5.2.1. 请求参数

无请求参数。

#### 5.2.2. 响应格式

| 字段 | 类型 | 说明 |
|------|------|------|
| ip | string | 客户端 IP 地址 |

#### 5.2.3. 错误码

| HTTP 状态码 | 说明 |
|-------------|------|
| 200 | 成功 |
| 500 | 服务器内部错误 |

#### 5.2.4. 请求示例

```http
GET /api/user-info HTTP/1.1
Host: agentinsight.goldebridge.com
```

#### 5.2.5. 响应示例

```json
{
  "ip": "203.0.113.42"
}
```

### 5.3. 获取运行时Config (GET /api/config)

**鉴权**：无

**描述**：返回容器运行时环境变量Config，供客户端组件读取。由于客户端组件无法直接读取非 `` 前缀的环境变量，因此通过此 API Route 在运行时获取Config。该接口返回 `selfHost` 字段，标识当前是否处于  免登录模式。接口实现位于 `app/api/config/route.ts`，通过读取 `process.env.` 环境变量并转换为布尔值返回。

#### 5.3.1. 请求参数

无请求参数。

#### 5.3.2. 响应格式

| 字段 | 类型 | 说明 |
|------|------|------|
| selfHost | boolean | 是否启用  免登录模式（`=true` 时跳过登录守卫） |

#### 5.3.3. 错误码

| HTTP 状态码 | 说明 |
|-------------|------|
| 200 | 成功 |
| 500 | 服务器内部错误 |

#### 5.3.4. 请求示例

```http
GET /api/config HTTP/1.1
Host: agentinsight.goldebridge.com
```

#### 5.3.5. 响应示例

```json
{
  "selfHost": false
}
```

### 5.4. 设置认证 Cookie (POST /api/auth/cookie)

**鉴权**：无

**描述**：设置 JWT httpOnly Cookie（`auth-token`），供 `middleware.ts` 服务端路由守卫读取。该接口是极简 Cookie 管理 API Route，不转发任何网络请求。前端直连 AgentInsightService 登录后，从响应体提取 JWT Token，调用本接口设置 httpOnly cookie。接口实现位于 `app/api/auth/cookie/route.ts`，核心逻辑为：解析请求体中的 `token` 字段，校验其存在且为字符串类型，然后通过 `` 的 `cookies.set` 方法设置 `auth-token` cookie。

**Cookie Config**：

| 属性 | 值 | 说明 |
|------|-----|------|
| httpOnly | true | 禁止浏览器脚本访问 |
| secure | 动态 | HTTPS 或 `X-Forwarded-Proto: https` 时为 true |
| sameSite | lax | 允许同站请求携带 |
| maxAge | 2592000 | 30 天（与 JWT 有效期一致） |
| path | / | 全路径生效 |

**secure 判断逻辑**：不能仅依赖 `=production`，因为用户可能通过 Nginx 反代以 HTTP 访问（如 `http://43.139.209.145/`），此时 `=production` 但实际协议是 HTTP，secure cookie 不会被浏览器存储，导致 middleware 检测不到 token 而重定向回 `/login`。因此需检查 `X-Forwarded-Proto` 头判断实际协议。

#### 5.4.1. 请求参数

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| token | string | 是 | JWT Token（无 "Bearer " 前缀） |

#### 5.4.2. 响应格式

| 字段 | 类型 | 说明 |
|------|------|------|
| success | boolean | 是否设置成功 |

#### 5.4.3. 错误码

| HTTP 状态码 | 说明 |
|-------------|------|
| 200 | 设置成功，响应头包含 `Set-Cookie` |
| 400 | 请求体缺少 `token` 参数或 `token` 不是字符串类型，响应体为 `{"error":"缺少 token 参数"}` |
| 500 | 请求体 JSON 解析失败，响应体为 `{"error":"设置 cookie 失败"}` |

#### 5.4.4. 请求示例

```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
}
```

#### 5.4.5. 响应示例

```http
HTTP/1.1 200 OK
Set-Cookie: auth-token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...; Max-Age=2592000; Path=/; Expires=Wed, 21 Oct 2026 07:28:00 ; ; =Lax

{"success":true}
```

### 5.5. 清除认证 Cookie (DELETE /api/auth/cookie)

**鉴权**：无

**描述**：清除 JWT httpOnly Cookie（`auth-token`）。该接口用于用户登出流程，由 `useAuthStore.logout()` 调用，清除 localStorage 中的 token 后，调用此接口清除 httpOnly cookie。接口实现位于 `app/api/auth/cookie/route.ts`，核心逻辑为通过 `` 的 `cookies.delete` 方法删除 `auth-token` cookie。

#### 5.5.1. 请求参数

无请求体。

#### 5.5.2. 响应格式

| 字段 | 类型 | 说明 |
|------|------|------|
| success | boolean | 是否清除成功 |

#### 5.5.3. 错误码

| HTTP 状态码 | 说明 |
|-------------|------|
| 200 | 清除成功，响应头包含清空过期时间的 `Set-Cookie` |

#### 5.5.4. 请求示例

```http
DELETE /api/auth/cookie HTTP/1.1
Host: agentinsight.goldebridge.com
```

#### 5.5.5. 响应示例

```http
HTTP/1.1 200 OK
Set-Cookie: auth-token=; Path=/; Expires=Thu, 01 Jan 1970 00:00:00 ; ; =Lax

{"success":true}
```

### 5.6. 前端调用约定

前端通过 `lib/auth-api.ts` 中的 `setAuthTokenCookie` 函数调用 `POST /api/auth/cookie` 接口。该函数接收 JWT Token 作为参数，发起 fetch 请求，请求头包含 `Content-Type: application/json`，请求体为 `JSON.stringify({ token })`。函数内部使用 try-catch 捕获异常，cookie 设置失败不阻塞登录流程——最坏情况是 middleware 检测不到 cookie，但 localStorage 已有 token，客户端 API 调用仍可用。

登出时，`useAuthStore.logout()` 清除 localStorage 并调用 `DELETE /api/auth/cookie` 清除 cookie，该操作不阻塞页面跳转。

---

## 6. 数据需求

内存存储） | `streams`, `messages`, `progress`, `sources` |
| `nav-store` | 导航 UI 状态 | 不持久化 | 侧边栏展开/收起等 |

**auth-store** 负责管理用户认证状态。登录成功后，JWT Token 存入 localStorage 供客户端 API 调用（`lib/auth-store.ts:40-50`），同时通过 `POST /api/auth/cookie` 设置 httpOnly cookie 供 middleware 路由守卫使用（`lib/auth-api.ts:100-110`）。`selfHost` 与 `userIp` 字段不持久化，避免陈旧值（`AGENTS.md` 5.3 节）。 模式下跳过登录守卫，显示客户端 IP（`middleware.ts:40-45`, `lib/auth-store.ts:60-70`）。

**agent-store** 维护当前选中的 Agent ID，初始值为 `getDefaultAgent().id`（`lib/stores/agent-store.ts`）。`setAgent()` 方法在检测到 Agent 变化时调用 `useSessionStore.getState().syncWithAgent(id)`，触发Session数据切换（`lib/stores/agent-store.ts`）。该 Store 使用 `persist` 中间件，Config `name: 'agent-storage'` 与 `skipHydration: true`，避免  水合不匹配。

**session-store** 是数据隔离的核心实现。内部通过 `byAgent: Record<string, AgentSessionSlice>` 按 Agent 存储Session切片，对外暴露 `sessions` / `currentSessionId` / `drafts` / `files` / `reportConfig` 作为当前 Agent 的视图（`lib/session-store.ts`）。每个 Agent 的Session切片包含：

onId` / `drafts` / `files` / `reportConfig` 作为当前 Agent 的视图（`lib/session-store.ts`）。每个 Agent 的Session切片包含：

```typescript
interface AgentSessionSlice {
  sessions: Session[];
  currentSessionId: string | null;
  drafts: Record<string, string>;          // 按 sessionId 隔离
  files: Record<string, UploadedFile[]>;   // 按 sessionId 隔离
  reportConfig: ReportConfig;
}
```

**stream-store** 按 sessionId 索引流式上下文，每个 `StreamContext` 包含消息列表、工具调用、检索来源、进度、报告 ID 等字段（`lib/stream-store.ts`）。AbortController 存于模块级 Map（非序列化，不入 zustand state），支持后台流并发控制（` = 1`）。 batching 机制将多次 token 推送合并为单次 `set()`，降低 setState 频率约 50 倍（`lib/stream-store.ts`）。

### 6.1. 类型定义

核心  类型定义在 `lib/types.ts`，与后端 Pydantic 模型对齐。主要类型如下：

**ChatMessage** — 聊天消息实体，包含消息 ID、Role、内容、时间戳等字段：

```typescript
interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  createdAt: string;
  // 可选扩展字段
  toolCalls?: ToolCall[];
  sources?: Source[];
}
```

tent: string;
  createdAt: string;
  // 可选扩展字段
  toolCalls?: ToolCall[];
  sources?: Source[];
}
```

**Session** — Session实体，对应后端 `/v1/sessions` 端点返回的数据结构。Session按 Agent 隔离，每用户每Agent（Agent）最多 10 个Session（`lib/session-store.ts` 中 ` = 10`）。

**RepoInfo** — 代码仓库信息（docbot 功能），支持 7 种平台（github/gitlab/gitee/bitbucket/coding/gitea/custom）和 4 种认证方式（`lib/types.ts:120-160`）。字段包括 ``、`platform`、`url`、``、`` 等。

**McpConfig** — MCP 服务Config（researcher 功能），定义在 `lib/types.ts`，包含 ``、`name`、``、`endpoint` 等字段。

**SSEEvent** — SSE 流式（Server-Sent Events）事件类型，统一为 `{ event: 'message', data }` 结构（`lib/api-client.ts` 4.2 节）。后端在 OpenAI `delta` 对象内嵌入 `progress` / `sources` / `` / `` / `` 扩展字段。

**ProgressMessage** — 节点进度消息，用于驱动前端进度条 UI。定义在 `lib/types.ts`，包含 `node`、`status`、`content` 等字段。

**ReportConfig** — 报告Config，默认值为 `{ : "", : "markdown", language: "zh" }`（`lib/session-store.ts`）。docbot 支持 8 种报告类型（architecture/design/requirements/testcase/optimization/performance/defect/）和 5 种输出格式（markdown/html/pdf/docx/json）（`lib/agents.config.ts:30-45`）。

timization/performance/defect/）和 5 种输出格式（markdown/html/pdf/docx/json）（`lib/agents.config.ts:30-45`）。

类型定义遵循以下约束：
- 所有类型与后端 Pydantic 模型严格对齐，字段命名采用 （如 ``、``）
- `UploadedFile` 接口定义在 `lib/session-store.ts`，包含 ``、`filename`、``、`selected` 字段
- `` 类型为 `'agentinsight-docbot' | 'agentinsight-researcher'`（`lib/agents.config.ts`）

### 6.2. 持久化策略

持久化策略遵循最小化原则，仅持久化必要的跨刷新状态，避免存储易变数据或敏感信息。

**持久化Config总览：**

| Store | persist name | 持久化字段 | 排除字段 | 原因 |
|-------|-------------|-----------|---------|------|
| `auth-store` | `'auth-storage'` | `user` 对象 | `selfHost`, `userIp`, `token` | 避免陈旧 IP；Token 由 httpOnly cookie 兜底 |
| `agent-store` | `'agent-storage'` | `currentAgent` | 无 | 跨刷新保持当前 Agent 选中状态 |
| `session-store` | 不持久化 | — | — | Session数据由后端持久化，前端仅内存缓存 |
| `stream-store` | 不持久化 | — | — | 流式状态为临时数据，刷新后需重新加载 |

**auth-store 持久化细节：**

`auth-store` 使用 `partialize` 显式声明持久化字段，仅持久化 `user` 对象，不持久化 `selfHost` / `userIp` 避免陈旧值（`AGENTS.md` 5.3 节）。JWT Token 虽存入 localStorage（`lib/auth-store.ts:40-50`），但登出时同时清除 localStorage 用户信息并删除 httpOnly cookie（`lib/auth-store.ts:70-80`）。

**agent-store 持久化细节：**

`agent-store` Config `name: 'agent-storage'` 与 `skipHydration: true`（`lib/stores/agent-store.ts`）。`skipHydration` 避免  水合不匹配——Zustand persist 在  时无法读取 localStorage，需客户端 hydrate。持久化的 `currentAgent` 字段在页面刷新后自动恢复，用户无需重新选择 Agent。

**session-store 与 stream-store 不持久化：**

`session-store` 和 `stream-store` 均不Config persist 中间件，数据仅存于内存。设计考量如下：

1. **Session数据由后端持久化**：Session CRUD 操作通过 `apiClient` 调用后端 `/v1/sessions` 端点（`lib/api-client.ts:152-180`），前端仅维护内存缓存。刷新页面后从后端重新拉取Session列表。
2. **流式状态为临时数据**：流式消息、进度、来源等状态在流结束后即失去意义，无需持久化。`stream-store` 的 `historyLoaded` 标志位避免重复加载历史消息（`lib/stream-store.ts`）。
3. **避免存储膨胀**：Session列表、文件列表等数据量可能较大，持久化到 localStorage 会超出存储配额。

**Agent 隔离数据恢复机制：**

切换 Agent 时，`agent-store.setAgent()` 调用 `session-store.syncWithAgent(id)`（`lib/session-store.ts:100-110`）。`syncWithAgent` 从 `byAgent[id]` 恢复对外视图（`sessions` / `currentSessionId` / `drafts` / `files` / `reportConfig`），切回原 Agent 时直接恢复其Session列表，无需重新 fetch（`lib/session-store.ts:60-80`）。该机制确保：

- 每个 Agent 拥有独立的Session空间，互不干扰
- 草稿、文件、报告Config按 Agent 隔离，切换后自动恢复
- 切回原 Agent 时状态完整保留，无需重新加载

---

## 7. 约束条件

`统一前端演示平台` 是 `agentinsight-agents` 项目的统一前端演示平台，为 `agentinsight-docbot` 和 `agentinsight-researcher` 两个Agent（Agent）提供 UI，前端仅承载 UI 展示与 API 调用，不承载任何业务逻辑——业务逻辑（Session编排、RAG 检索、工具调用、报告生成、人在回路（Human-in-the-loop）审核等）由各Agent（Agent）后端处理 [AGENTS.md:19-22]。本章定义项目开发、运行与部署过程中必须遵守的硬性约束，涵盖技术选型、业务容量上限、安全合规及部署模式四个维度。这些约束是项目架构决策的边界条件，任何偏离均需通过变更评审流程审批。

### 7.1. 技术约束

技术约束规定了项目必须使用的框架、语言与工具链版本，以及架构分层与代码组织方式。这些约束确保团队协作一致性、构建可复现性与长期可维护性。

#### 7.1.1. 核心框架与版本锁定

项目必须使用以下精确版本的技术栈，版本号由 `package.json` 锁定，禁止随意升级或降级：

| 技术栈 | 版本 | 用途 | 约束级别 |
|--------|------|------|----------|
| Next.js | 15.1.0 | App Router 路由与渲染框架 | 硬约束 |
| React | 19.0.0 | UI 组件库 | 硬约束 |
|  | 5.6.3 | 类型系统（strict 模式） | 硬约束 |
| Tailwind CSS | 4.3.2 | 样式方案（CSS-first Config） | 硬约束 |
| Zustand | 5.0.0 | 客户端状态管理 | 硬约束 |
| next-intl | 4.0 | i18n 国际化方案 | 硬约束 |

式方案（CSS-first Config） | 硬约束 |
| Zustand | 5.0.0 | 客户端状态管理 | 硬约束 |
| next-intl | 4.0 | i18n 国际化方案 | 硬约束 |

技术选型理由：Next.js 15.1.0 提供 App Router 服务端组件、Edge Middleware 与 rewrites 反向代理能力，是双模式部署的基础 [AGENTS.md:7.2]；React 19.0.0 与 Next.js 15.1.0 为官方配套版本； strict 模式（`tsconfig.json` 中启用）保证类型安全，禁止滥用 `any` 或 `as unknown as T` 强制断言链 [AGENTS.md:10-21]；Tailwind CSS 4.3.2 采用 CSS-first Config，替代 CSS Modules 与 styled-components；Zustand 5.0.0 作为唯一状态管理方案，禁止引入 Redux//Recoil [AGENTS.md:10-2]。

#### 7.1.2. 架构分层与依赖方向

项目采用严格的分层架构，依赖方向为单向流动：`app/`（路由层）→ `components/`（UI 组件层）→ `lib/`（业务逻辑层），`lib/` 禁止反向 import `components/` 或 `app/` [AGENTS.md:3]。`app/api/` 内的 Route Handler 仅承担轻量服务端职责（设置 cookie、透传运行时Config、健康检查、IP 解析），不承载业务逻辑、不直接调用后端业务接口 [AGENTS.md:3]。

```typescript
// lib/agents.config.ts 是 Agent Config的唯一真源（）
// 定义所有 Agent 的 id/port/apiBaseUrl/features，驱动 UI 显隐和 API 路由
// 新增 Agent 时必须同步更新此文件与 app/agent/<agentName>/chat/ 路由
// 禁止在组件内 if-else 判断 Agent，应读取 agent.features.xxx 标志位
```

#### 7.1.3. 构建与编译约束

`next.config.ts` 必须Config `poweredByHeader: false`（关闭 X-Powered-By 响应头，避免暴露技术栈）与 `reactStrictMode: true`（开发期检测潜在副作用）[AGENTS.md:7.2]。生产环境暂不启用 React Compiler（`reactCompiler: true`）与 Turbopack（`--turbo`），两者仍不稳定，生产构建可能出错 [AGENTS.md:7.2]。`experimental.optimizePackageImports` 与 `compiler.removeConsole` 在排查 hydration 错误时暂时禁用 [AGENTS.md:7.2]。

### 7.2. 业务约束

业务约束规定了系统在Session管理、流式消息处理与资源使用方面的容量上限与驱逐策略，确保系统在长期运行下的稳定性与资源可控性。

#### 7.2.1. Session数量上限

每个 Agent 最多允许创建 10 个Session，该限制在 `lib/session-store.ts` 中通过常量 `=10` 强制执行 [lib/session-store.ts:8]。当用户尝试创建第 11 个Session时，前端应阻止操作并提示用户删除旧Session。Session按 Agent 隔离，切换 Agent 后Session列表、草稿、文件与报告Config独立恢复，互不干扰 [lib/session-store.ts:60-80]。该约束的验收标准为 AC-6：每个 Agent 最多创建 10 个Session [lib/session-store.ts:8]。

#### 7.2.2. 后台流并发控制

后台流（后台任务产生的流式消息）最多保留 1 个活跃实例。当新的后台流启动时，若已有活跃后台流，应先终止旧的再启动新的，避免多路后台流并发导致 UI 状态混乱与资源竞争。该约束由 `lib/stream-store.ts` 中的后台流管理逻辑实现。

#### 7.2.3. StreamContext  驱逐

非活跃 StreamContext 超过 10 个时触发 （Least Recently Used）驱逐策略 [lib/stream-store.ts:48]。StreamContext 保存流式消息的中间状态（content delta、事件类型、进度信息等），当非活跃上下文数量超过阈值时，最久未使用的上下文将被移除以释放内存。该约束的验收标准为 AC-13：非活跃 StreamContext 超过 10 个时  驱逐 [lib/stream-store.ts:48]。

#### 7.2.4. 流式渲染性能约束

流式消息的 content delta 必须通过 （requestAnimationFrame）batching 合并渲染，避免高频 setState 导致的性能退化 [lib/stream-store.ts:50-70]。该约束的验收标准为 AC-10：流式消息 content delta 通过  batching 合并渲染（性能优化）[lib/stream-store.ts:50-70]。

### 7.3. 合规约束

合规约束涵盖 JWT Token 处理、安全响应头Config与  策略，是项目安全合规红线，违例即阻断合并并提 P0 缺陷 [AGENTS.md:10]。

#### 7.3.1. JWT Token 处理硬约束

JWT Token 的处理必须严格遵守以下规则 [AGENTS.md:9.1]：

`next.config.ts` 必须Config以下 5 类安全响应头 [AGENTS.md:7.2]：

```typescript
// next.config.ts headers Config（硬约束）
{
  'X-Frame-Options': '',                    // 禁止点击劫持
  'X-Content-Type-Options': 'nosniff',          // 禁止  嗅探
  'Referrer-Policy': 'strict-origin-when-cross-origin', // 限制 Referer 泄露
  'Strict-Transport-Security': 'max-age=63072000; includeSubDomains; preload', //  强制 HTTPS
  'Permissions-Policy': 'camera=(), microphone=(), geolocation=()', // 禁用敏感设备能力
}
```

该约束的验收标准为 AC-18：安全响应头包含 X-Frame-Options/、、 等 5 类 [next.config.ts]。此外，`X-Powered-By` 响应头必须通过 `poweredByHeader: false` 关闭，避免暴露技术栈 [AGENTS.md:7.2]。

#### 7.3.2. 策略

Config由部署模式决定 [AGENTS.md:4.2]：

| 部署模式 |  策略 | 说明 |
|----------|-----------|------|
| server（默认） | 无  | 经 Next.js `rewrites` 反向代理 `/api/(已移除无关路径) → `http://localhost:8068/*`，浏览器同源请求 |
| local | 需后端Config  | 浏览器直连 `http://localhost:{agent.port}`，无 Nginx，需后端 AgentInsightService Config  允许前端来源 |

#### 7.3.3. 前端安全红线

前端禁止使用 `dangerouslySetInnerHTML` 渲染用户输入，防止  攻击 [AGENTS.md:10-14]。禁止在客户端代码读取非 `` 前缀环境变量，应通过 `/api/config` 等 Route 间接获取 [AGENTS.md:10-11]。禁止在演示平台直接读写后端业务数据库（PostgreSQL/Qdrant/Redis），应通过后端 API 访问 [AGENTS.md:10-16]。

### 7.4. 部署约束

部署约束定义了系统的双模式部署架构、 免登录模式与 Docker 镜像管理规则，确保不同部署场景下的行为一致性与可运维性。

#### 7.4.1. 双模式部署架构

系统支持 `server` 与 `local` 两种部署模式，由 `` 环境变量控制，构建时内联 [AGENTS.md:4.2]：

| 模式 | baseUrl 解析 | 适用场景 |
|------|-------------|----------|
| server（默认） | `agent.apiBaseUrl`（如 `/api/agentinsight-docbot`） | 生产环境，经 Nginx 反向代理，浏览器同源请求 |
| local | `http://localhost:${agent.port}`（如 `http://localhost:8068`） | 本地开发，浏览器直连后端，需后端Config  |

`apiClient.getBaseUrlForAgent()` 根据部署模式返回正确的 baseUrl，未知 agentId 降级到默认 Agent [tests/unit/api-client.test.ts]。`next.config.ts` 中的 rewrites Config仅在 server 模式生效：`/api/(已移除无关路径) → `http://localhost:8068/:path*`、`/api/agentinsight-researcher/:path*` → `http://localhost:8066/:path*` [AGENTS.md:7.2]。

#### 7.4.2. 免登录模式

---

## 8. 需求Trace矩阵

`统一前端演示平台` 是 `agentinsight-agents` 项目的统一前端演示平台，为 `agentinsight-docbot` 和 `agentinsight-researcher` 两个Agent（Agent）提供 UI。前端仅承载 UI 展示与 API 调用，不承载任何业务逻辑——业务逻辑（Session编排、RAG 检索、工具调用、报告生成、人在回路（Human-in-the-loop）审核等）由各Agent（Agent）后端处理。FRNFR到具体代码实现的完整Trace映射，确保每一项需求均可追溯到明确的实现载体，为需求变更影响分析、代码审查与回归测试提供依据。

### 8.1. FR Trace

FR映射至具体的实现文件、核心函数与关键行号，并标注验证方式与优先级。

| 需求编号 | 需求描述 | 实现文件 | 核心函数/组件 | 关键行号 | 验证方式 | 优先级 |
|---------|---------|---------|--------------|---------|---------|-------|
| FR-001 | 系统应支持获取并展示客户端 IP 地址（SELF_HOST 模式下显示） | `app/api/user-info/route.ts` (GET) | `GET` handler | 文件级引用 | 单元测试 + 手动验证 | Must |
| FR-001 | 系统应支持在 SELF_HOST 模式下展示客户端 IP | `lib/auth-store.ts` | `fetchUserIp()` | `lib/auth-store.ts:60-70` | 单元测试 (`auth-store.test`) | Must |
| FR-002 | 系统应支持运行时获取 SELF_HOST Config（非构建时内联） | `app/api/config/route.ts` (GET) | `GET` handler | 文件级引用 | 单元测试 + 手动验证 | Must |
| FR-002 | 系统应支持 SELF_HOST 模式下跳过登录守卫 | `middleware.ts` | `middleware` 函数 | `middleware.ts:40-45` | 集成测试 (`full-flow.spec`) | Must |
| FR-003 | 系统应支持通过 httpOnly cookie 保存认证 Token | `app/api/auth/cookie/route.ts` (POST) | `POST` handler | 文件级引用 | 单元测试 (`auth-api.test`) | Must |
| FR-003 | 系统应支持调用后端接口设置认证 cookie | `lib/auth-api.ts` | `setAuthTokenCookie()` | `lib/auth-api.ts:100-110` | 单元测试 (`auth-api.test`) | Must |
| FR-004 | 系统应支持用户登出并清除认证状态 | `app/api/auth/cookie/route.ts` (DELETE) | `DELETE` handler | 文件级引用 | 单元测试 (`auth-api.test`) | Must |
| FR-004 | 系统应支持登出时清除 localStorage 与 cookie | `lib/auth-store.ts` | `logout()` | `lib/auth-store.ts:80-90` | 单元测试 (`auth-store.test`) | Must |

#### 8.1.1. FR-001 客户端 IP 获取与展示 [优先级: Must]

- **用户故事**: 作为 SELF_HOST 模式下的用户，我希望系统能够自动获取并展示我的客户端 IP，以便确认当前访问来源。
- **主流程**:
  1. 前端组件挂载后调用 `useAuthStore` 中的 `fetchUserIp()` 方法。
  2. `fetchUserIp()` 发起 `fetch("/api/user-info")` 请求，由 `app/api/user-info/route.ts` 的 `GET` handler 处理。
  3. 服务端解析客户端 IP 并返回 JSON 响应（包含 `ip` 字段）。
  4. 前端判断 `data.ip` 非空且不等于 `"unknown"` 时，调用 `set({ userIp: data.ip })` 更新状态。
- **验收标准**:
  - [ ] AC1: 调用 `fetchUserIp()` 后，当 API 返回 `{ ip: "203.0.113.5" }` 时，`userIp` 状态更新为 `"203.0.113.5"`。
  - [ ] AC2: 当 API 返回 `{ ip: "unknown" }` 或请求失败时，`userIp` 保持空字符串，且不抛出未捕获异常。
  - [ ] AC3: `userIp` 字段不持久化到 localStorage（`partialize` 仅持久化 `user`）。
- **业务规则**:
  - BR-001: `userIp` 仅在 SELF_HOST 模式下展示，非 SELF_HOST 模式显示手机/邮箱。
  - BR-002: IP 获取失败时静默降级，不阻塞用户操作。

#### 8.1.2. FR-002 运行时 SELF_HOST Config获取 [优先级: Must]

- **用户故事**: 作为系统管理员，我希望前端在运行时动态获取 SELF_HOST Config，以便在不重新构建前端的情况下切换部署模式。
- **主流程**:
  1. 前端应用初始化时调用 `fetch("/api/config")` 请求运行时Config。
  2. `app/api/config/route.ts` 的 `GET` handler 从服务端环境变量读取 `SELF_HOST` Config并返回 JSON 响应。
  3. 前端根据返回的Config值决定是否展示客户端 IP、是否跳过登录守卫等行为。
- **验收标准**:
  - [ ] AC1: 当服务端 `SELF_HOST=true` 时，`/api/config` 返回 `{ SELF_HOST: true }`，前端进入 SELF_HOST 模式。
  - [ ] AC2: 当服务端 `SELF_HOST=false` 或未设置时，`/api/config` 返回 `{ SELF_HOST: false }`，前端进入标准认证模式。
  - [ ] AC3: Config在构建时不被内联，修改服务端环境变量后无需重新构建前端即可生效。
- **业务规则**:
  - BR-001: `middleware.ts:40-45` 根据 SELF_HOST Config决定是否跳过登录守卫。
  - BR-002: SELF_HOST 模式下，`lib/auth-store.ts:60-70` 的 `fetchUserIp()` 被调用以展示客户端 IP。

### 8.2. NFR Trace

NFR映射至具体的实现文件、关键机制与关键行号，并标注验证方式与优先级。

| 需求编号 | 需求描述 | 实现文件 | 关键Config/机制 | 关键行号 | 验证方式 | 优先级 |
|---------|---------|---------|--------------|---------|---------|-------|
| NFR-P-001 | 前端应保证流式消息渲染的性能，避免高频 SSE 事件导致 UI 卡顿 | `lib/stream-store.ts` | requestAnimationFrame (rAF) batching 机制 | `lib/stream-store.ts:150-180` | 性能测试 (`stream-store.test`) | Must |
| NFR-S-002 | 前端应Config安全响应头，防范点击劫持、MIME 嗅探等攻击 | `next.config.ts` | `X-Frame-Options: DENY`、`X-Content-Type-Options: nosniff`、`Referrer-Policy`、`Strict-Transport-Security`、`Permissions-Policy` | `next.config.ts:20-35` | 安全扫描 + 手动验证 | Must |
| NFR-C-001 | 前端测试环境应模拟浏览器 API，保证组件测试可运行 | `tests/setup.ts` | jsdom polyfill Config | `tests/setup.ts:10-25` | 单元测试执行 | Should |

#### 8.2.1. NFR-P-001 流式渲染性能优化 [优先级: Must]

- **需求描述**: 前端应保证流式消息渲染的性能，避免高频 SSE 事件导致 UI 卡顿。
- **实现机制**:
  - `lib/stream-store.ts` 使用 requestAnimationFrame (rAF) batching 机制，将高频 SSE 事件按帧批量合并渲染，减少不必要的 React 重渲染次数。
  - rAF batching 实现位于 `lib/stream-store.ts:150-180`，通过将多个流式数据块合并为单次状态更新，确保 UI 渲染频率与浏览器刷新率对齐。
- **验收标准**:
  - [ ] AC1: 高频 SSE 事件（>60 条/秒）下，UI 渲染帧率保持稳定，无明显卡顿。
  - [ ] AC2: 批量更新不丢失数据，所有流式消息最终均被完整渲染。
  - [ ] AC3: 组件卸载时正确取消 rAF 循环，无内存泄漏。
- **验证方式**: 性能测试 (`stream-store.test`) 覆盖 rAF batching 逻辑的正确性与性能表现。

---

## 9. 优先级与路线图

Session管理通过 RESTful 端点约定实现：`/v1/sessions` 负责Session列表的增删改查，报告Config经 `/v1/sessions/{id}/config` 管理 [AGENTS.md:4.2]。`session-store.ts` 管理客户端Session列表状态，按 Agent 隔离Session数据，支持 Agent 切换时状态恢复 [lib/session-store.ts:60-80]。

| 功能需求 | 优先级 | 验收标准 | 关键实现 |
|---------|--------|---------|---------|
| 用户认证 | Must | 登录成功后 token 同时存在于 localStorage 和 httpOnly cookie | [lib/auth-store.ts:40-50], [lib/auth-api.ts:100-110] |
| 用户认证 | Must | 登出时清除 localStorage 用户信息 + 删除 httpOnly cookie | [lib/auth-store.ts:70-80] |
| 聊天流式交互 | Must | SSE 流式（Server-Sent Events）消息实时渲染 Markdown 内容 | [lib/stream-store.ts:200-280], [components/chat/chat-messages.tsx] |
| 聊天流式交互 | Must | SSE 流式（Server-Sent Events）消息解析 progress/sources/ 自定义字段 | [lib/stream-store.ts:250-280] |
| Agent 切换 | Must | Session列表/草稿/文件/报告Config按 Agent 隔离，切换后自动恢复 | [lib/session-store.ts:60-80] |

### 9.1. P1 主要功能

P1 层级在 P0 核心闭环基础上，扩展产品的主要业务能力，包括 Docbot 报告生成、Researcher MCP Config管理、代码仓库管理三大功能模块。该层级是产品价值体现的关键，为用户提供深度研究与报告产出能力。

**Docbot 报告生成（仓库选择 + 报告Config + 流式进度 + 下载）**

 端点执行 [lib/api-client.ts:290-295]。仓库类型定义集中在 `lib/types.ts`，与后端 Pydantic 模型对齐 [lib/types.ts:120-160]。

| 功能需求 | 优先级 | 验收标准 | 关键实现 |
|---------|--------|---------|---------|
| Docbot 报告生成 | Should | 支持选择输出格式（markdown/html/pdf/docx/json）和语言（zh/en） | [lib/agents.config.ts:30-33] |
| Docbot 报告生成 | Should | SSE 流式（Server-Sent Events）返回 progress/sources/ 字段 | [lib/stream-store.ts:200-280] |
| Researcher MCP Config | Should | MCP Config支持 stdio/sse/ 三种传输类型 | [components/settings/mcp-config-panel.tsx:15] |
| 代码仓库管理 | Should | 仓库 CRUD、连接测试、同步触发 | [lib/api-client.ts:250-310] |
| 代码仓库管理 | Should | 测试连接经 `POST /v1/repos/{id}/test` 端点 | [lib/api-client.ts:290-295] |

### 9.2. P2 增强功能

P2 层级为产品的差异化增强能力，包括人在回路（Human-in-the-loop）审核、历史报告面板、i18n 多语言完善、性能优化四大方向。该层级提升产品的专业度与用户体验，部分能力已部分实现，属持续优化范畴。

**人在回路（Human-in-the-loop）审核**

人在回路（Human-in-the-loop）审核为 Researcher 深度研究流程提供人工介入节点。作为研究者，用户上传文件、Config MCP 工具后进行深度研究，并在关键节点接收人工审核 [AGENTS.md:19-22]。该功能由 `features.humanReview` 标志位驱动 UI 显隐，审核状态机由后端管理 [AGENTS.md:80-85]。前端通过 `components/review/review-panel.tsx` 提供审核交互界面。

**历史报告面板**

历史报告面板为用户提供历史报告的统一查看与管理入口。该功能依赖 `` 与报告下载端点 `GET /v1/reports/{id}/download`，支持按 Agent 隔离的历史报告列表展示 [AGENTS.md:4.2]。前端通过 `components/chat/history-report-panel.tsx` 实现历史报告列表与详情查看。

**i18n 多语言完善**

i18n 多语言基于 next-intl 4.0 实现，`messages/{locale}.json` 是 i18n 资源 ，组件中不推荐硬编码中英文字符串，应通过 `useTranslations` 或 `getTranslator` 读取 [AGENTS.md:3]。`middleware.ts` 负责 locale 检测与路由守卫 [middleware.ts:1-60]，`messages/index.ts` 提供 `getTranslator` / `detectLocale` 工具函数。当前支持 zh/en 两种语言，后续可扩展更多语言包。

**性能优化（ batching,  驱逐）**

性能优化属持续迭代方向，已部分实现。`stream-store.ts` 已实现  batching 优化，将高频 SSE 事件合并为单次渲染 [lib/stream-store.ts:200-280]；非活跃 StreamContext 超过 10 个时触发  驱逐 [lib/stream-store.ts:48]。后续优化方向包括：流式渲染性能调优、大数据量Session列表虚拟滚动、报告生成进度粒度优化等。

---

## 10. 风险与依赖

本章节聚焦 `统一前端演示平台` 项目在开发与运维过程中面临的主要技术风险、外部依赖及对应的缓解措施。`统一前端演示平台` 是 `agentinsight-agents` 项目的统一前端演示平台，为 `agentinsight-docbot` 和 `agentinsight-researcher` 两个Agent（Agent）提供 UI，前端仅承载 UI 展示与 API 调用，不承载任何业务逻辑 (docs/architecture.md:1-4)。前端通过 OpenAI 兼容 SSE 端点与后端交互，并依赖 `lib/agents.config.ts` 作为 Agent Config的SSOT（单一事实来源） (AGENTS.md:19-22)。本章节将围绕五个已识别的关键风险展开分析，并给出对应的工程化缓解策略。

### 10.1. 技术风险

#### 10.1.1. 风险 1：后端 API 契约变更导致前端类型定义失效

前端与后端通过 RESTful API 和 SSE 流式（Server-Sent Events）接口通信，所有请求/响应结构均在前端 `lib/types.ts` 中定义，并与后端 Pydantic 模型对齐 (AGENTS.md:19-22)。当后端调整响应字段（如新增必填字段、修改嵌套结构或重命名字段）而前端未同步更新时，会导致前端 TypeScript 类型在编译期无法捕获运行时错误，进而引发 UI 渲染异常或数据丢失。

具体风险场景包括：

- 后端在 `delta` 对象中新增自定义扩展字段（如 `progress` / `sources` / `report_id` / `node_id` / `status`），前端 `lib/stream-store.ts` 解析逻辑未同步适配 (AGENTS.md:19-22)。
- Session管理接口 `/v1/sessions` 的响应结构变更，导致 `lib/session-store.ts` 中状态切片解析失败 (AGENTS.md:19-22)。
- 报告Config接口 `/v1/sessions/{id}/config` 的请求体字段调整，导致 `lib/api-client.ts` 中 `updateReportConfig` 方法发送的 payload 与后端期望不一致 (AGENTS.md:19-22)。

#### 10.1.2. 风险 2：SSE 流式（Server-Sent Events）解析兼容性依赖后端严格遵循 OpenAI SSE 格式

聊天流式交互通过 `POST /v1/chat/completions` 端点实现，后端以 OpenAI `data:` 行格式（无 `event:` 命名事件）返回 SSE 流 (lib/api-client.ts:100-150)。前端 `ApiClient.chatStream()` 异步生成器负责解析 SSE 事件，并统一为 `{ event: 'message', data }` 结构 (AGENTS.md:19-22)。

该风险的核心在于：若后端未严格遵循 OpenAI SSE 规范（如发送非 JSON 数据、使用自定义事件名、或 `data:` 行包含多余空白字符），前端解析器可能抛出异常或静默丢弃消息。此外，后端在 `delta` 对象内嵌入的扩展字段（`progress` / `sources` / `report_id`）若类型不一致（如 `progress` 从整数变为对象），会导致前端进度条渲染失败 (lib/api-client.ts:100-150)。

#### 10.1.3. 风险 3：JWT Token 存储与同步隐患

用户认证采用 JWT Bearer Token 双存储机制：Token 同时保存在 `localStorage`（供客户端 API 调用）和 httpOnly cookie（供 `middleware.ts` 路由守卫）(lib/auth-api.ts:20-110)。该机制存在以下隐患：

当 `NEXT_PUBLIC_AUTH_API_BASE` 指向的认证服务不可用时，用户将无法登录，且 `middleware.ts` 路由守卫会阻止访问受保护页面 (lib/auth-api.ts:20-30, middleware.ts:40-55)。前端直连 `NEXT_PUBLIC_AUTH_API_BASE` 指定的认证服务（默认 `https://agentinsight.goldebridge.com`），该服务负责登录、注册、Token 签发等认证逻辑。若认证服务不可用，用户将无法登录，且 `middleware.ts` 路由守卫会阻止访问受保护页面 (lib/auth-api.ts:20-30)。

#### 10.1.4. 风险 4：环境变量Config缺失或错误导致运行时行为异常

前端行为受以下环境变量控制 (.env.template:1-10)：

| 环境变量 | 作用 | 默认值 |
|----------|------|--------|
| `NEXT_PUBLIC_API_MODE` | 控制 API 路由模式（server/local） | `local` |
| `SELF_HOST` | 是否跳过登录守卫 | `true` |
| `NEXT_PUBLIC_AUTH_API_BASE` | 认证服务地址 | `https://agentinsight.goldebridge.com` |
| `PORT` | 前端开发服务器端口 | `8801` |

`SELF_HOST` 为运行时变量（非 `NEXT_PUBLIC` 前缀），由 `.env` / `.env.qa` 提供，compose 文件注入容器 (.env.template:1-10)。若环境变量Config缺失或错误（如 `SELF_HOST` 未正确注入、`NEXT_PUBLIC_AUTH_API_BASE` 指向不可达地址），可能导致路由守卫行为异常或认证请求失败。

#### 10.1.5. 风险 5：测试环境缺失浏览器 API 导致测试失败

测试依赖 Vitest（单元/集成）+ Playwright（e2e），并使用 MSW（Mock Service Worker）mock 后端 API (AGENTS.md:19-22)。测试目标地址从环境变量 `NEXT_PUBLIC_API_MODE` 注入（默认 `http://localhost:3000`）(AGENTS.md:19-22)。在 jsdom 测试环境中，部分浏览器 API（如 `IntersectionObserver`、`matchMedia`）不可用，可能导致组件测试在挂载或渲染阶段抛出异常。

### 10.2. 缓解措施

#### 10.2.1. 缓解 1：类型定义集中管理与契约测试

针对风险 1，采取以下措施：

- **类型定义集中**：所有与后端交互的 TypeScript 类型集中在 `lib/types.ts` 中定义，禁止在组件内散落定义 API 数据结构 (AGENTS.md:19-22)。
- **契约测试覆盖**：通过 `api-contract.test.ts` 契约测试验证前端类型定义与后端实际响应结构一致。测试用例覆盖每个 RESTful 端点的请求/响应结构，以及 SSE 流式（Server-Sent Events）事件中的自定义扩展字段 (AGENTS.md:19-22)。
- **多Agent（Agent）集成测试**：每个 Agent 至少 1 条 e2e 用例，验证 `agents.config.ts` Config与实际后端 API 契约一致（端点 / 请求体 / SSE 字段）(AGENTS.md:19-22)。

#### 10.2.2. 缓解 2：SSE 容错解析

针对风险 2，`ApiClient.chatStream()` 在解析 SSE 流时实现容错处理 (lib/api-client.ts:100-150)：

- **非 JSON 数据容错**：当 `data:` 行包含非 JSON 内容时，解析器跳过该行并继续处理后续事件，避免整个流中断 (lib/api-client.ts:100-150)。
- **字段类型校验**：对 `delta` 对象中的扩展字段（`progress` / `sources` / `report_id`）进行类型校验，若类型不符合预期则使用默认值，防止 UI 渲染异常。
- **流中断恢复**：若 SSE 连接意外中断，前端通过 `AbortController` 中断请求，并在 UI 层提示用户重试 (AGENTS.md:19-22)。

#### 10.2.3. 缓解 3：登出双清理机制

针对风险 3，登出流程在 `lib/auth-store.ts` 中实现双清理 (lib/auth-api.ts:100-110)：

| 步骤 | 操作 | 涉及文件 |
|------|------|----------|
| 1 | 调用 `POST /api/auth/logout` 清除 httpOnly cookie | `lib/auth-api.ts` |
| 2 | 移除 `localStorage` 中的 JWT Token | `lib/auth-store.ts` |
| 3 | 重置 `auth-store` 中的用户状态 | `lib/auth-store.ts` |
| 4 | 重定向至 `/login` 页面 | `middleware.ts` |

同时，`middleware.ts` 路由守卫在 `SELF_HOST=true` 时跳过登录校验，直接放行请求 (middleware.ts:40-45)。

#### 10.2.4. 缓解 4：环境变量集中管理与Config校验

针对风险 4，采取以下措施：

- **环境变量集中管理**：所有环境变量在 `.env.template` 中声明并附注释说明，确保新增变量时有据可查 (.env.template:1-10)。
- **启动时Config校验**：在应用启动入口（如 `next.config.js` 或 `instrumentation.ts`）校验必填环境变量是否存在，缺失时输出明确错误日志并终止启动。
- **SELF_HOST 模式回归测试**：在 CI 流水线中增加 `SELF_HOST=true` 和 `SELF_HOST=false` 两种模式的冒烟测试，确保路由守卫行为符合预期。

#### 10.2.5. 缓解 5：测试环境 Polyfill

针对风险 5，在 `tests/setup.ts` 中提供缺失浏览器 API 的 polyfill (AGENTS.md:19-22)：

```typescript
// tests/setup.ts（伪代码示意）
import { vi } from 'vitest';

// IntersectionObserver polyfill
class IntersectionObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}
global.IntersectionObserver = IntersectionObserverMock;

// matchMedia polyfill
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});
```

该 polyfill 确保组件测试在 jsdom 环境中稳定运行，避免因缺失 API 导致测试失败 (AGENTS.md:19-22)。

---

## 11. 附录

### 11.1. 术语表

本附录汇总 AGENTS.md 统一前端演示平台（统一前端演示平台）中涉及的核心术语，供读者在阅读本文档时快速查阅。该平台为 `agentinsight-docbot` 和 `agentinsight-researcher` 两个Agent（Agent）提供统一 UI，前端仅承载 UI 展示与 API 调用，不承载任何业务逻辑 [AGENTS.md:19-22]。

| 术语 | 定义 |
|------|------|
| Agent（Agent（Agent）） | 具备独立业务能力的 AI 服务单元。本平台包含 `agentinsight-docbot`（文档生成）和 `agentinsight-researcher`（深度研究）两个Agent（Agent），前端通过 `agents.config.ts` 驱动 UI 显隐 [AGENTS.md:19-22] |
| AgentStore | 前端全局状态存储，管理当前选中的 Agent 及切换逻辑。通过 `agent-store` 更新当前 Agent，并触发 `session-store.syncWithAgent(agentId)` 实现Session隔离 [lib/session-store.ts:100-110] |
| SSE（Server-Sent Events） | 服务器推送事件，用于实现聊天流式交互。前端通过 OpenAI 兼容 SSE 端点（`POST /v1/chat/completions`）接收流式响应，包括 content（内容）、progress（节点进度）、sources（检索来源）、report_id（报告 ID）等字段 [lib/api-client.ts:100-150] |
| JWT Bearer Token | 用户认证凭证。前端通过多源容错提取 JWT Token，双存储于 localStorage（供客户端 API 调用）和 httpOnly cookie（供 middleware 路由守卫）。`SELF_HOST=true` 时跳过登录守卫 [lib/auth-store.ts:1-80, middleware.ts:1-60] |
| Zustand Store | 基于 Zustand 的前端状态管理方案，用于管理Session列表、流式消息、文件等跨组件共享状态。包括 `session-store`（Session CRUD、按 Agent 隔离、上限 10 个/User）、`stream-store`（SSE 流式（Server-Sent Events）消息管理）等 [lib/session-store.ts:1-20] |
| Session（Session） | 用户与 Agent 的独立对话上下文。按 Agent 隔离，支持创建/列表/删除/重命名，每个 Agent 最多 10 个Session [lib/session-store.ts:1-20, lib/api-client.ts:152-180] |
| 人在回路（Human-in-the-loop）审核（Human-in-the-loop） | researcher Agent（Agent）的审核机制。前端通过 WebSocket 接收 `human_feedback_request` 消息，并将用户反馈提交到 `POST /v1/feedback` 端点 [lib/api-client.ts:218-222, lib/types.ts:200-210] |
| MCP（Model Context Protocol） | 模型上下文协议，用于扩展 researcher Agent（Agent）的工具能力。支持 stdio/sse/streamable_http 三种传输方式，前端提供 MCP 服务Config的 CRUD、测试及系统Config克隆功能 [lib/api-client.ts:185-215] |
| i18n（国际化） | 多语言支持机制。平台支持 zh/en 两种 locale，通过 `next-intl` 4.0 实现，由 `messages/index.ts` 提供 `getTranslator`、`detectLocale` 工具函数 [messages/index.ts:1-80, i18n.ts:1-30] |
| SELF_HOST（自托管模式） | 免登录部署模式。`SELF_HOST=true` 时跳过登录守卫，前端显示客户端 IP，适用于内网私有化部署场景 [middleware.ts:40-45, lib/auth-store.ts:60-70] |
| httpOnly Cookie | 仅服务端可读的 Cookie，用于存储 JWT Token 供 middleware 路由守卫使用。通过 `POST /api/auth/cookie` 设置，`DELETE` 清除，不转发网络请求 [AGENTS.md:3-45] |

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

## 附录: 接口/业务规则/约束编号骨架

| 类型 | 编号范围 | 数量 | 说明 |
|------|----------|------|------|
| 接口需求 | IR-001 .. IR-004 | 4 | 与 HTTP 端点/外部依赖对应 |
| 业务规则 | BR-001 .. BR-010 | 10 | 与校验/状态机/配额规则对应 |
| 约束 | C-001 .. C-004 | 4 | 技术/合规/部署约束 |

### 接口需求编号

- IR-001
- IR-002
- IR-003
- IR-004

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

### 约束编号

- C-001
- C-002
- C-003
- C-004
## 附录: 功能需求清单（由 HTTP 端点确定性生成）

| 编号 | 模块 | 功能名 | 优先级 | 关联接口 |
|------|------|--------|--------|----------|
| FR-001 | Unknown |  | Must | `GET /api/user-info` |
| FR-002 | Unknown |  | Must | `GET /api/config` |
| FR-003 | Unknown |  | Must | `POST /api/auth/cookie` |
| FR-004 | Unknown |  | Must | `DELETE /api/auth/cookie` |

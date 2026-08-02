# agentinsight-docbot

> **中文优先的代码仓库技术文档生成智能体** | **Chinese-first code-to-docs agent**
>
> An open-source documentation agent built with LangGraph + LiteLLM + Qdrant.
> Turns a Git repository into multi-format technical docs via OpenAI-compatible
> SSE APIs. Independently deployable (5 containers, **no SearXNG**).

[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-%E2%89%A53.11-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-%E2%89%A50.115-green.svg)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-%E2%89%A51.2-purple.svg)](https://langchain-ai.github.io/langgraph/)
[![code style: ruff](https://img.shields.io/badge/code%20style-ruff-261230.svg)](https://docs.astral.sh/ruff/)
[![Docker](https://img.shields.io/badge/Docker-Compose-blue.svg)](docker-compose.yml)
[![Version](https://img.shields.io/badge/version-1.0.1-orange.svg)](CHANGELOG.md)

[中文](#中文) | [English](#english)

---

## 中文

## 🌐 在线体验(官方 Demo)

无需部署,直接访问官方在线 Demo **测试页面**即可体验全部能力:

| 入口 | 地址 | 说明 |
|------|------|------|
| **测试页面(推荐)** ⭐ | http://43.139.209.145/ | 内置前端联调页面,支持会话管理、流式渲染、工具调用展示、文件上传、报告下载 |
| **健康检查** | http://43.139.209.145/api/health | 容器与服务健康状态 |
| **Agent 发现** | http://43.139.209.145/agent/agentinsight-researcher/.well-known/agent-discovery.json | Agent Discovery Protocol 公开元信息 |

> 💡 **使用提示**:
> - **推荐通过测试页面试用**:打开页面即可零配置体验研究报告生成、流式渲染、多 Agent 协作等全部能力,无需手动构造 API 请求。
> - Demo 环境为 `SELF_HOST=False` 云托管模式,测试页面会引导鉴权与点数校验,无需手动处理 Bearer Token。
> - 若返回 502,通常是 Demo 后端临时维护,稍后重试即可。
> - **官方 Demo 仅建议通过页面试用,不建议直接调用 API**;API 直连调用(如 curl/SDK)请使用本地部署 `localhost:8066`(见下文「快速开始」)。

### 30 秒上手 Demo

1. **打开测试页面**:浏览器访问 http://43.139.209.145/
2. **注册账号并登录**:首次使用需在 [AgentInsight 平台](https://agentinsight.goldebridge.com/platform) 注册账号并登录。
3. **输入研究问题**:在消息输入框输入如 `分析2026年中国新能源汽车市场格局`,Enter 发送。
4. **观察流式渲染**:报告逐段流式输出,工具调用与检索来源以折叠面板展示。
5. **下载报告**:报告生成完成后,可通过页面下载 Markdown / HTML / PDF / DOCX / JSON 多种格式。

---

## 项目简介

**agentinsight-docbot** 根据用户代码仓库一键生成技术文档, 对外暴露 OpenAI 兼容 API(SSE 流式, 端口 **8068**)。

| 项 | 说明 |
|----|------|
| 端口 | **8068** |
| 容器 | **5** 个: postgres / redis / qdrant / embeddings / agent-docbot |
| 元搜索 | **无 SearXNG**(面向仓库 RAG, 非 Web 搜索) |
| Compose 项目名 | `-p agentinsight-docbot` |
| 前端 | **不含前端**; UI 由独立项目 [`agentinsight-demo`](../agentinsight-demo) 提供 |
| 版本 | **v1.0.1** |

### 核心能力

- 📄 **8 种文档类型** — architecture / design / requirements / testcase / optimization / performance / defect / api_doc
- 🌐 **2 种语言 × 5 种格式** — `zh`/`en` × Markdown / HTML / PDF / DOCX / JSON
- 🤖 **7 子智能体 · 6 步流水线** — 学习代码 → 细化纲要 → 填充内容 → 评审 → 合并 → 终审
- 🔧 **系统 MCP** — `mcp-server-git` + `mcp-server-filesystem`(启动时自动注册, 无用户 MCP CRUD)
- 🔍 **仓库 RAG** — 分块索引 + BM25/向量混合检索(可选 Rerank)
- 📈 **可观测** — AgentInsight SDK 6 类 span
- 🛡️ **安全** — JWT + AES-GCM Git 凭据 + 仓库域名白名单

### 刻意不暴露的端点

| 端点 | 原因 |
|------|------|
| `POST /v1/feedback` | 不启用人在回路审核 |
| `WS /v1/ws/{session_id}` | 仅用 SSE 推送进度 |
| `/v1/mcp/configs` | MCP 系统自带, 不入库、不暴露 CRUD |

---

## ⚠️ 开始使用前

### 第 1 步: 注册 AgentInsight 并创建 API Key(可观测性)

1. 访问 [https://agentinsight.goldebridge.com/platform](https://agentinsight.goldebridge.com/platform)
2. 创建 APIKey, 保存 **PublicKey**(`pk-...`) 与 **SecretKey**(`sk-...`, 仅显示一次)

### 第 2 步: 配置环境变量

```bash
copy .env.template .env
```

编辑 `.env`, 填入占位符对应的真实值(**勿将真实 `.env` 提交仓库**):

```env
# AgentInsight 可观测性 (建议填写)
AGENTINSIGHT_PUBLIC_KEY=pk-<your-public-key>
AGENTINSIGHT_SECRET_KEY=sk-<your-secret-key>
AGENTINSIGHT_HOST=https://agentinsight.goldebridge.com

# LLM (至少配置一个)
DEEPSEEK_API_KEY=sk-<your-deepseek-key>
ZHIPU_API_KEY=<your-zhipu-key>

# 基础设施
POSTGRES_PASSWORD=<your-postgres-password>
REDIS_AUTH=<your-redis-password>
QDRANT_API_KEY=<your-qdrant-key>
EMBEDDINGS_API_KEY=<your-embeddings-key>

# docbot 专属: Git 凭据加密密钥 (AES-GCM, 32 字节建议)
GIT_CREDENTIAL_KEY=<your-32-byte-key>
```

> 🔒 密钥仅环境变量注入, 禁止入仓/硬编码/日志。详见 [SECURITY.md](SECURITY.md)。

---

## 快速开始

### 环境要求

- Python ≥3.11(推荐 3.12)
- Docker ≥24.0 + Docker Compose ≥2.20

### 一键起栈(推荐)

```bash
docker compose -p agentinsight-docbot -f docker-compose.yml --env-file .env up -d --build
docker compose -p agentinsight-docbot ps
```

健康检查:

```bash
curl http://localhost:8068/health
```

### 本地开发(可选)

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1   # Windows
pip install -U pip -r requirements.txt
uvicorn server:app --host 0.0.0.0 --port 8068 --reload
```

> 本地开发仍需 Postgres / Redis / Qdrant / Embeddings 可用(可用 compose 只起依赖服务)。

### 调用示例

```bash
curl -N http://localhost:8068/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <optional-jwt>" \
  -d "{\"model\":\"agentinsight-docbot\",\"stream\":true,\"messages\":[{\"role\":\"user\",\"content\":\"生成技术架构文档\"}],\"repo_id\":\"<repo-id>\"}"
```

仓库 CRUD: `GET/POST/PUT/DELETE /v1/repos` · 会话: `/v1/sessions` · 下载: `/v1/reports/{id}/download`

### 演示 UI

启动独立前端 [`agentinsight-demo`](../agentinsight-demo)(容器端口 **8801**), 打开 docbot 聊天页配置仓库并一键生成。

---

## 架构一览

```
用户 / demo UI
    │  OpenAI 兼容 SSE
    ▼
agent-docbot :8068  ── LangGraph 顶层图 + 报告子图
    │
    ├─ postgres :5432   (业务表 + Checkpointer)
    ├─ redis :6379      (流水线中间产物 cache_key)
    ├─ qdrant :6333     (仓库向量, repo_id 隔离)
    └─ embeddings :8088 (bge-base-zh-v1.5)
```

详细设计见 [`docs/architecture.md`](docs/architecture.md) 与 [`AGENTS.md`](AGENTS.md)。

---

## 开发与测试

```bash
pytest tests/unit/ -q
ruff check . && ruff format --check .
mypy src/ --strict
```

贡献流程见 [CONTRIBUTING.md](CONTRIBUTING.md)。变更记录见 [CHANGELOG.md](CHANGELOG.md)。

---

## Roadmap（路线图）

基于当前仓库代码与测试现状（截至 v1.0.1）：

| 状态 | 项 |
|------|-----|
| ✅ 已完成 | 7 子智能体(A–G) + 6 步流水线；8 种文档类型 × 5 种格式 × 2 种语言(`zh`/`en`) |
| ✅ 已完成 | OpenAI 兼容 API（SSE）+ `/v1/repos` + `/v1/sessions` + 报告下载；刻意不暴露 feedback/ws/mcp CRUD |
| ✅ 已完成 | 独立 5 容器部署（无 SearXNG）；系统 MCP（git + filesystem）；AES-GCM Git 凭据；JWT/IP 身份解析 |
| ✅ 已完成 | 仓库 RAG（分块/BM25+向量/`repo_id` namespace）；Redis 流水线缓存；AgentInsight 6 类 span |
| ✅ 已完成 | 日生成限额、代码图谱/引用/结构校验等增强；unit/api/e2e 等测试分层骨架 |
| 🔄 进行中 | 多视角代码学习（`docbot_multi_perspective_enabled`，默认关闭）；可选 Rerank（`rerank_enabled`，默认关闭） |
| 🔄 进行中 | 与官方 Demo / `agentinsight-demo` 联调体验与文档入口同步 |
| 📋 计划中 | RAGAS/DeepEval 评测数据集与 CI 门禁（`evals/` 尚未落地） |
| 📋 计划中 | 更多文档类型/纲要模板；生产可观测与容量调优 |

---

## 许可证

[MIT](LICENSE) · Copyright (c) 2026 AgentInsight

---

## English

## 🌐 Online Demo (Official)

Try all capabilities without deployment via the official online demo **test page**:

| Entry | URL | Description |
|-------|-----|-------------|
| **Test Page (Recommended)** ⭐ | http://43.139.209.145/ | Built-in frontend debug page with session management, streaming rendering, tool call display, file upload, report download |
| **Health Check** | http://43.139.209.145/api/health | Container and service health status |
| **Agent Discovery** | http://43.139.209.145/agent/agentinsight-researcher/.well-known/agent-discovery.json | Agent Discovery Protocol public metadata |

> 💡 **Usage Notes**:
> - **Recommended to try via the test page**: open the page to experience research report generation, streaming rendering, multi-agent collaboration, and all capabilities with zero configuration, no need to manually construct API requests.
> - The demo runs in `SELF_HOST=False` cloud-hosted mode; the test page handles auth and quota validation, no need to manually handle Bearer Token.
> - If a 502 is returned, the demo backend is temporarily under maintenance; please retry later.
> - **The official demo is only recommended for page trial, not for direct API calls**; for direct API calls (curl/SDK), use local deployment `localhost:8066` (see "Quick Start" below).

### 30-Second Quick Start with Demo

1. **Open the test page**: visit http://43.139.209.145/ in your browser
2. **Register an account and log in**: First-time users need to register an account and log in on the [AgentInsight platform](https://agentinsight.goldebridge.com/platform).
3. **Enter a research question**: type a query like `Analyze the 2026 China new energy vehicle market landscape` in the message input box and press Enter.
4. **Watch streaming rendering**: the report streams out paragraph by paragraph; tool calls and retrieval sources are shown in collapsible panels.
5. **Download the report**: after generation, download the report in Markdown / HTML / PDF / DOCX / JSON formats from the page.

---

**agentinsight-docbot** is an independently deployable documentation agent
(port **8068**, **5 containers**, **no SearXNG**) that generates technical docs
from a Git repository via OpenAI-compatible SSE APIs. Version **v1.0.1**.

### Quick start

1. Copy `.env.template` → `.env` and fill placeholders (never commit secrets).
2. `docker compose -p agentinsight-docbot up -d --build`
3. `curl http://localhost:8068/health`
4. Use sibling UI [`agentinsight-demo`](../agentinsight-demo) or call `/v1/chat/completions`.

### Capabilities

- 8 report types × 5 formats × 2 languages (`zh`/`en`)
- 7 sub-agents (A–G), 6-step pipeline with Redis-backed intermediate artifacts
- System MCP (`git` + `filesystem`); no `/v1/feedback`, `/v1/ws`, or `/v1/mcp/configs`
- AES-GCM git credentials, JWT auth, AgentInsight tracing

See [`docs/architecture.md`](docs/architecture.md), [AGENTS.md](AGENTS.md),
[CONTRIBUTING.md](CONTRIBUTING.md), and [SECURITY.md](SECURITY.md).

### Roadmap

| Status | Item |
|--------|------|
| Done | 7 sub-agents, 6-step pipeline, 8 report types × 5 formats × 2 languages |
| Done | OpenAI-compatible SSE API, `/v1/repos`, sessions, report download; no feedback/ws/mcp CRUD |
| Done | 5-container stack (no SearXNG), system MCP, AES-GCM credentials, JWT/IP auth, repo RAG |
| In progress | Multi-perspective learning & optional Rerank (feature-flagged, off by default); Demo UX sync |
| Planned | RAGAS/DeepEval CI gates; more outline templates; capacity tuning |

Licensed under [MIT](LICENSE).

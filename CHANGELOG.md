# 变更日志 | Changelog

[中文](#中文) | [English](#english)

---

## 中文

本项目遵循 [Semantic Versioning](https://semver.org/lang/zh-CN/) 语义化版本规范。

格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。

---

## [Unreleased]

### 计划中

- RAGAS/DeepEval 评测门禁 CI 化
- 更多文档类型与纲要模板
- 与演示平台联调体验优化

---

## [0.1.0] - 2026-08-02

### Initial Release — 开源初始版本

#### ✨ 新增

**文档生成智能体核心能力**
- 基于用户代码仓库一键生成技术文档(端口 **8068**)
- 7 个子智能体(A–G)协作, 6 步流水线: 代码学习 → 纲要细化 → 内容填充 → 评审 → 合并 → 终审
- 8 种文档类型: `architecture` / `design` / `requirements` / `testcase` / `optimization` / `performance` / `defect` / `api_doc`
- 5 种导出格式: Markdown / HTML / PDF / DOCX / JSON; 2 种语言: `zh` / `en`

**OpenAI 兼容 API**
- `POST /v1/chat/completions`(SSE 流式 + 非流式)
- 会话管理 `/v1/sessions`、仓库管理 `/v1/repos`、报告下载 `/v1/reports/{id}/download`
- 刻意不暴露: `/v1/feedback`、`/v1/ws/{session_id}`、`/v1/mcp/configs`(无人审、仅 SSE、系统 MCP)

**独立可部署 5 容器栈**
- `postgres` / `redis` / `qdrant` / `embeddings` / `agent-docbot`
- **无 SearXNG**(面向仓库 RAG, 非 Web 元搜索)
- Compose 项目名: `-p agentinsight-docbot`

**安全与可观测**
- Git 凭据 AES-GCM 加密(`GIT_CREDENTIAL_KEY`); 仓库域名白名单 `ALLOWED_GIT_DOMAINS`
- AgentInsight SDK 6 类 trace span
- JWT 身份解析 + `agent_id` / `user_id` / `session_id` 三级隔离

**前端职责**
- 本仓库不含前端; UI 由独立子项目 `agentinsight-demo` 提供

---

## English

This project follows [Semantic Versioning](https://semver.org/).
Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [Unreleased]

### Planned

- CI gates for RAGAS/DeepEval
- More document types and outline templates
- Demo platform UX polish

---

## [0.1.0] - 2026-08-02

### Initial Release

#### Added

- Code-repository → technical documentation agent on port **8068**
- 7 sub-agents (A–G), 6-step pipeline, 8 report types × 5 formats × 2 languages
- OpenAI-compatible API with SSE streaming; `/v1/repos` + `/v1/sessions` + report download
- Independently deployable 5-container stack (**no SearXNG**)
- AES-GCM git credentials, AgentInsight observability, JWT + data isolation
- UI lives in sibling project `agentinsight-demo`

[Unreleased]: https://github.com/AgentInsight/agentinsight-docbot/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/AgentInsight/agentinsight-docbot/releases/tag/v0.1.0

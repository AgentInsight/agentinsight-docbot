# AGENTS.md — LangGraph AI Agent 执行规则（agentinsight-docbot）

> AI 助手在执行任何任务前应先读本文档。规则分两类：
> - **优先选择**：除非该架构/工具不适合当前场景，否则应优先采用本文档推荐方案。如需改用其他方案，应说明理由并等待用户确认。
> - **不推荐**：除非该架构/工具在当前场景具有明显优势，否则不应采用。如确需选用，应说明优势理由并等待用户确认。
> - 第 11 章安全合规红线为真正的硬约束（涉及密钥/PII/注入/传输安全），不可放松。

> **前端职责声明**：本智能体不包含前端代码实现。所有前端 UI 由独立的演示平台 `agentinsight-demo` 负责（路径：`../agentinsight-demo`）。本智能体仅对外暴露 OpenAI 兼容 API（SSE 流式），供演示平台调用。详见 `../agentinsight-demo/AGENTS.md` 与主目录 `../AGENTS.md`。

> **独立运行原则**：本项目为独立可部署系统，所有依赖（Postgres / Redis / Qdrant / Embeddings / 基础 Python 模块）均在本项目内自带。从 AIR（agentinsight-researcher）拷贝的基础模块（`common/` / `rag/` / `llm/` / `memory/` / `observability/` / `api/routes.py` / `api/middleware.py` / `api/session_routes.py` / `api/ip_user_resolver.py` / `skills/researcher/publisher.py` / `scripts/init.sql`）在本仓库内独立演进，不再双向同步。容器编排使用 `-p agentinsight-docbot` 项目名，自带 5 容器（postgres / redis / qdrant / embeddings / agent-docbot）。

## 1. 项目定位与技术栈

**定位**：根据用户代码仓库一键生成技术文档的多智能体系统，对外暴露 OpenAI 兼容 API（SSE 流式，端口 8068）。用户通过演示平台（`agentinsight-demo`）配置代码仓库 → 选择报告类型/格式/语言 → 一键生成 → 7 个子智能体（A/B/C/D/E/F/G）协作完成 6 步流水线（学习代码 → 细化纲要 → 填充内容 → 评审 → 合并 → 终审）→ 返回多格式文档下载链接。

**能力边界**：仅承载代码仓库分析 / 技术文档生成 / RAG 检索 / MCP 工具调用四类能力；不承担模型训练、数据标注、前端 SSR、系统级共享仓库（仅个人仓库）；多 Agent 协作采用顶层图 + 报告子图 + `asyncio.gather` 并发派发模式。

**支持范围**：
- 文档语言：简体中文（`zh`） / English（`en`） 共 2 种
- 文档类型：技术架构（`architecture`） / 概要设计（`design`） / 需求（`requirements`） / 测试用例（`testcase`） / 系统优化（`optimization`） / 性能分析（`performance`） / 系统缺陷（`defect`） / API 文档（`api_doc`） 共 8 种
- 文档格式：Markdown / HTML / PDF / DOCX / JSON 共 5 种

| 类别 | 选型 / 版本 | 选型理由（一句话） | 替代方案（不推荐原因） |
|------|------------|-------------------|---------------------|
| 语言 | Python ≥3.11 | 异步生态成熟，类型完备 | Go/Node（生态不及） |
| 编排内核 | LangGraph ≥1.2 | 状态机+条件边+Checkpointer，生产首选 | AutoGen/CrewAI（控制流不透明，不推荐） |
| LLM 抽象 | langchain-core ≥1.4 | 仅核心类型，不推荐 Chain/AgentExecutor | langchain 全家桶（耦合高，不推荐） |
| 模型网关 | LiteLLM ≥1.6 | 一次接入 100+ 模型，内置成本/限流/重试，不配 BaseURL 时自动识别 provider | 厂商 SDK 直连（不推荐，无统一治理） |
| 工具协议 | MCP | 2026 事实标准，复用生态 | 自定义委派协议（不推荐，重复造轮） |
| 代码仓库访问 | `mcp-server-git` + `mcp-server-filesystem` | 社区成熟实现，支持 clone/pull/read/history，系统自带（非用户配置） | 自研 Git 适配（不推荐，重复造轮） |
| 向量库 | Qdrant ≥1.18 | API 优雅、过滤强、部署简单 | Pinecone（不推荐，闭源）/Milvus（运维重） |
| 关系库 | PostgreSQL ≥17 | Checkpointer+业务元数据 | MySQL（不推荐，分布式弱） |
| 缓存 | Redis ≥8.0 | 热点缓存+6 步流水线中间产物传递+短期会话 | Memcached（不推荐，无持久化） |
| Embeddings | bge-base-zh-v1.5（768 维，远程 TEI） | 中文最强开源嵌入 | OpenAI embedding（不推荐，数据出境） |
| 上下文压缩 Embeddings | FastEmbed (bge-small-zh-v1.5 ONNX INT8) | 本地零成本、CPU 友好、512 维 | 远程 TEI 用于压缩（不推荐，CPU 瓶颈） |
| Rerank | bge-reranker-v2-m3（可选，`rerank_enabled=True` 启用） | 中文 Rerank SOTA | Cohere Rerank（不推荐，闭源收费） |
| BM25 | rank-bm25+jieba | 中文分词+IDF，混合检索必备 | 字符 2-gram（降级兜底，非首选） |
| Web 框架 | FastAPI+Uvicorn ≥0.115 | 异步原生、OpenAPI 自动、SSE 流式 | Flask/Django（不推荐，异步弱/过重） |
| 数据校验 | Pydantic ≥2.10 | SSOT 配置+入出参校验 | dataclass（不推荐，校验弱） |
| 可观测性 | AgentInsight Python SDK ≥0.1.5 | 自家产品，异步上下文管理器，6 类 span | LangSmith/Langfuse（不推荐，数据出境/已替代） |
| 评测 | RAGAS+DeepEval ≥0.2/≥2.0 | RAG 质量+Agent 行为双轨门禁 | 仅人工测试（不推荐，不可 CI 化） |
| 部署 | Docker Compose | 5 容器编排（postgres/redis/qdrant/embeddings/agent-docbot） | 裸机/k8s（暂不采用） |

**三级 LLM 分层配置（核心约定，优先选择；用户指定 2026-07-19）**：

| 等级 | 环境变量 | 默认值 | 用途 | 上下文窗口 |
|------|---------|--------|------|----------|
| FAST | `FAST_LLM` | `zhipuai/glm-4-flash` | 轻量摘要 / 路由 / 错误兜底 / 上下文压缩 | 128K |
| SMART | `SMART_LLM` | `deepseek/deepseek-v4-flash` | 任务三内容填充 / 任务四评审 / 任务五合并 / 任务六终审 | 128K |
| STRATEGIC | `STRATEGIC_LLM` | `deepseek/deepseek-v4-pro` | 任务一代码深度学习 / 任务二纲要细化 | 256K |

降级链：STRATEGIC → SMART → FAST → 抛出 `LLMUnavailableError`（基于从 AIR 拷贝的 `LLMClient` 实现）。

> 技术栈变更建议经架构师评审。如需改用"不推荐"方案，应说明当前场景的优势理由并等待用户确认。

## 2. 核心命令速查

```bash
# 首次准备（按序执行）
python -m venv .venv && .venv\Scripts\Activate.ps1
pip install -U pip -r requirements.txt
copy .env.template .env   # 填入 LLM/Qdrant/Embeddings/AgentInsight/GitCredential 凭据

# 启动 / 测试 / 质量门禁
uvicorn server:app --host 0.0.0.0 --port 8068 --reload
pytest tests/ -q && ruff check . && ruff format --check . && mypy src/ --strict

# 评测（CI 门禁）
python -m evals.rag.run --dataset evals/rag/dataset.json
python -m evals.agent.run --dataset evals/agent/dataset.json

# 容器化起栈（独立命名空间，必须 -p agentinsight-docbot）
docker compose -p agentinsight-docbot -f docker-compose.yml --env-file .env up -d
# 或使用脚本（推荐）；构建脚本路径与三套模式说明见第 12 章
```

## 3. 目录结构与架构边界

```
src/
├── graph/                     # LangGraph 图定义
│   ├── state.py               # DocbotState + ReportTaskState 双 schema
│   ├── nodes.py               # 顶层节点（coordinator_a / spawn_b_tasks / final_reviewer_g / save_reports）
│   ├── report_nodes.py        # 报告子图节点（b_init / c_code_learning / c_outline_refine / d_content_fill / e_review / f_merge / g_final_in_subgraph）
│   ├── edges.py               # 守卫与路由（route_after_d / route_after_e）
│   ├── builder.py             # build_docbot_graph() 顶层图
│   └── report_builder.py      # build_report_subgraph() 报告子图
├── agents/
│   └── docbot/                # docbot 7 个子智能体业务逻辑
│       ├── coordinator.py     # 子智能体 A：协调入口
│       ├── report_runner.py   # 子智能体 B：单报告任务协调
│       ├── outline_refiner.py # 子智能体 C：纲要细化
│       ├── content_filler.py  # 子智能体 D：内容填充
│       ├── reviewer.py        # 子智能体 E：评审
│       ├── merger.py          # 子智能体 F：合并去重
│       └── final_reviewer.py  # 子智能体 G：终审
├── common/                    # 公用基础模块（从 AIR 拷贝，本仓库独立维护，不应依赖 agents/ 或业务模块）
├── config/
│   ├── settings.py            # 全局 pydantic-settings Settings SSOT（agent_name='agentinsight-docbot'）
│   └── docbot/                # docbot 专属配置
│       ├── personas.py        # DOCBOT_REPORT_PERSONAS（8 种文档 persona 字典）
│       ├── outlines.py        # 8 种文档默认大纲加载器（读取 docs/*_OUTLINE.md）
│       └── prompts.py         # docbot 专属提示词模板
├── skills/
│   ├── docbot/                # docbot 6 步流水线技能实现
│   │   ├── repo_loader.py     # 仓库克隆 / 文件枚举 / 分块 / 索引
│   │   ├── code_learner.py    # 任务一：STRATEGIC 深度学习代码
│   │   ├── outline_skill.py   # 任务二：纲要细化
│   │   ├── content_skill.py   # 任务三：内容填充 + 图片生成
│   │   ├── review_skill.py    # 任务四：评审
│   │   ├── merge_skill.py     # 任务五：合并去重
│   │   ├── final_skill.py     # 任务六：终审
│   │   └── cache.py           # Redis 缓存键管理（6 步流水线中间产物传递）
│   └── researcher/            # 从 AIR 拷贝
│       ├── publisher.py       # 多格式导出（HTML/PDF/DOCX/JSON）
│       └── image_generator.py # DeepSeek SVG 生成
├── tools/
│   └── git_mcp.py             # 用户代码仓库 MCP 适配（封装系统自带 mcp-server-git）
├── rag/                       # 从 AIR 拷贝（namespace 加 repo_id 隔离）
├── llm/                       # 从 AIR 拷贝的 LLMClient（三级降级链）
├── memory/                    # 从 AIR 拷贝的 checkpointer / db_initializer / report_store / session_store
├── observability/             # 从 AIR 拷贝的 tracing.py（6 类 trace_xxx）
└── api/
    ├── routes.py              # /v1/chat/completions（从 AIR 拷贝）
    ├── middleware.py          # 从 AIR 拷贝（JWT + IP 降级 + 限流 + CORS）
    ├── session_routes.py      # 从 AIR 拷贝（会话管理端点）
    ├── repo_routes.py         # 新增：/v1/repos 用户代码仓库 CRUD + 测试 + 同步
    └── ip_user_resolver.py    # 从 AIR 拷贝

docs/                          # 8 种文档默认大纲（运行时按需读取）
├── ARCHITECTURE_OUTLINE.md    # 技术架构文档默认大纲
├── HLD_OUTLINE.md             # 概要设计文档默认大纲
├── PRD_OUTLINE.md             # 需求文档默认大纲
├── TEST_CASE_OUTLINE.md       # 测试用例文档默认大纲
├── OPTIMIZATION_OUTLINE.md    # 系统优化文档默认大纲
├── PERF_ANALYSIS_OUTLINE.md   # 性能分析文档默认大纲
├── DEFECT_OUTLINE.md          # 系统缺陷文档默认大纲
└── API_DOC_OUTLINE.md         # API 文档默认大纲

scripts/init.sql               # 完整 DDL（基础 DDL + docbot 专属 DDL）
tests/                         # 测试分层（unit / functional / api / regression / e2e 等，详见第 13 章）
```

> **前端工程位置（核心约定）**：本智能体不含前端代码。前端 UI 工程位于 `../agentinsight-demo`（独立仓库，承担所有 Agent 的演示页面，包括 docbot 配置仓库 / 选择报告类型 / 一键生成 / SSE 进度展示 / 报告下载等交互）。本仓库后端 API 通过 OpenAI 兼容端点（`POST /v1/chat/completions` `stream=true`）+ `/v1/repos` + `/v1/sessions` + `/v1/reports/{id}/download` 供演示平台调用。

> **离线构建产物位置（核心约定）**：QA 模式与生产离线模式所需的 `packages/`（wheels/debs/models/images）已统一上移到主目录 `../packages/`，由主目录统一管理。本仓库内不再保留 `packages/` 目录。

> **不暴露的 API 端点（核心约定）**：本系统不提供以下 3 个端点（与从 AIR 拷贝的代码差异）：
> - `POST /v1/feedback`：人在回路反馈，docbot 不启用人审
> - `WS /v1/ws/{session_id}`：WebSocket 双向通道，docbot 仅用 SSE 推送进度
> - `GET/POST/PUT/DELETE /v1/mcp/configs`：MCP 配置 CRUD，`mcp-server-git` / `mcp-server-filesystem` 由系统启动时自动注册，不入 `mcp_configs` 表，不暴露配置入口

**架构边界（核心约定，优先选择）**：
- `graph/` 是首选编排入口；`agents/docbot/` 复用图，不推荐自建编排循环。
- `tools/`、`rag/`、`llm/`、`memory/` 不推荐互相 import，共享逻辑下沉到 `common/`。
- 依赖单向向内：`common/` 不应依赖 `agents/` 或业务模块。
- **临时文件管理（核心约定，优先选择）**：所有临时文件（含临时测试文件/脚本/代码/日志/验证产物/用户克隆的代码仓库等）应放入 `temp/` 目录，不推荐在项目根目录或 `tests/` 正式分层下放置临时文件；`temp/` 目录已加入 `.gitignore` 不入仓。用户代码仓库克隆路径为 `temp/repos/{user_id}/{repo_id}/`。正式测试用例应放在 `tests/` 对应分层（`unit/`/`functional/`/`api/`/`regression/`/`e2e/`），手动调试脚本放在 `tests/manual/`。
- 配置应经 `config/` + 环境变量，业务代码不应硬编码 URL/密钥（硬编码密钥属第 11 章硬约束）。
- docbot 专属代码应隔离在 `agents/docbot/`、`config/docbot/`、`skills/docbot/`、`tools/git_mcp.py`、`api/repo_routes.py` 下，不推荐与基础模块代码混放；从 AIR 拷贝的能力（RAG / LLM / memory / observability）在本仓库内独立演进，不推荐再次双向同步。
- 新增顶层目录建议经架构师评审。

## 4. 三级行为边界与不推荐清单

| 级别 | 触发场景（可枚举可校验） |
|------|------------------------|
| ✅ Always | 读/写 docs·tests·evals；跑 ruff+mypy+pytest；跑 RAGAS+DeepEval；修 P2 及以下 bug；续接被截断输出；删项目内文件 |
| ⚠️ Ask first | LangGraph 图结构/State schema 变更；RAG 核心算法（RRF/Rerank/Embeddings）切换；密钥轮换；外部系统对接；连续 3 次修复失败；评测门禁不达标；**选用"不推荐"方案时**；新增/修改 docbot 8 种文档 persona；修改 6 步流水线顺序 |
| ❌ Never | 见不推荐清单；安全合规红线（第 11 章）属真正硬约束，违例即阻断合并并提 P0 |

**不推荐清单（CI 机器校验 import 黑名单，选用需说明理由并等待用户确认）**：
1. `langchain` 全家桶（仅 `langchain-core` 推荐使用）
2. `AgentExecutor`（推荐用 LangGraph StateGraph）
3. AutoGen / CrewAI（重复多 Agent 编排框架，不推荐）
4. LlamaIndex（重复 RAG/编排框架，不推荐）
5. LangSmith（专有 SaaS，数据出境合规风险，不推荐）/Langfuse（已由 AgentInsight SDK 替代，不推荐）
6. Pinecone 等闭源托管向量库（推荐用 Qdrant）
7. 直接调用厂商 SDK（推荐经 LiteLLM）
8. Memcached（推荐用 Redis）
9. MySQL（推荐用 PostgreSQL）
10. `pickle` 持久化 Agent 状态（推荐用 Postgres Checkpointer）
11. 全局可变状态（推荐节点纯函数，状态从 state/deps 获取）
12. `eval`/`exec` 求值用户输入（注入风险，属第 11 章安全硬约束）
13. 直接使用 `opentelemetry-sdk` 原生 API（推荐经 `observability/tracing.py` 封装的 6 类 `trace_xxx`）
14. `agentinsight.observe` 装饰器（已弃用，无法记录 `model`/`usage_details`/`cost_details`，不推荐）
15. 观察者模式实现追踪（不推荐 Subject/Observer、attach/notify 机制；追踪统一用异步上下文管理器）
16. LangGraph Send API 并发派发（推荐 `asyncio.gather` + Semaphore，保持状态机语义清晰）
17. 6 步流水线中间产物直接放入 LangGraph state（推荐 Redis 缓存 + state 仅存 `cache_key`，避免 state 膨胀）
18. 代码仓库敏感字段明文存储（推荐 AES-GCM 加密，密钥 `GIT_CREDENTIAL_KEY` 环境变量注入，属第 11 章硬约束）
19. 将 MCP 工具配置存入 `mcp_configs` 表（推荐系统启动时自动注册 `mcp-server-git` / `mcp-server-filesystem`，不入数据库、不暴露 CRUD 端点）
20. 暴露 `/v1/feedback`、`/v1/ws/{session_id}`、`/v1/mcp/configs` 端点（docbot 不启用人审、仅用 SSE、MCP 系统自带）
21. 在 `mcp_configs` 表中存储系统自带 MCP 配置（系统 MCP 由 lifespan 启动子进程，不入库）
22. 在本仓库内新增前端工程或 `static/index.html` 测试页面（前端职责已划归 `../agentinsight-demo`，本仓库仅暴露 API）

> 以上清单为"不推荐"而非"绝对禁止"。如某项在当前场景具有明显优势，可说明理由并经用户确认后选用，但应在 PR 中标注偏差说明。

## 5. Agent 编排核心规则

LangGraph ≥1.2 状态机为**优先选择的编排范式**；不推荐 AgentExecutor / 手写 ReAct 循环。如需改用其他编排框架（如 AutoGen/CrewAI），应说明优势理由并等待用户确认。

**State**：应为 `TypedDict`；跨节点共享字段用 `Annotated[T, reducer]` 声明（消息流用 `add_messages`，累积字段用 `operator.add`）。节点不应原地修改入参 State，应返回 delta dict 由 reducer 合并。不推荐全局可变状态；会话级数据走 Checkpoint。

**Node**：节点为纯函数 `async def node(state: State, settings: Settings) -> dict`，单一职责、无副作用。节点内不推荐直连厂商 LLM SDK，统一走 `llm/` 网关（LiteLLM）。每个节点应包裹在 AgentInsight trace span 内（见第 10 章）。节点参数通过 `functools.partial` 注入 `settings`，保持节点函数纯函数语义。

**Edge**：路由应显式 `add_conditional_edges(src, router_fn, mapping)`，不推荐隐式跳转。每个图应有终止节点；`max_iterations` / `max_revisions_per_chapter` 为硬上限，由节点计数器 + 条件边强制，不可软超时。

**Checkpoint**：生产 `StateGraph` 应挂 `PostgresSaver`（PostgreSQL ≥17，使用本项目自带的 `agents` 库）；内存 Checkpoint 仅 `ENV=dev` 允许。`thread_id` 从请求上下文注入做会话隔离键，格式 `{agent_id}:{session_id}`（顶层图）或 `{agent_id}:{session_id}:{report_type}`（报告子图），不推荐客户端自造。

**多智能体编排（核心约定，优先选择）**：
docbot 采用**顶层图 + 报告子图 + asyncio.gather 并发派发**双层结构：

1. **顶层图（子智能体 A + G）**：
   - `coordinator_a`（解析 JSON 指令 / 校验参数 / 建立根 span）
   - `spawn_b_tasks`（`asyncio.gather` 并发派发 N 个 B 子图，`Semaphore(max_concurrent_reports=3)` 限流）
   - `final_reviewer_g`（多报告交叉一致性评审）
   - `save_reports`（复用从 AIR 拷贝的 `ReportStore` 保存 5 种格式）

2. **报告子图（子智能体 B + C/D/E/F + G）**：每报告类型独立子图实例，6 步顺序执行：
   - 任务一（`c_code_learning`）：STRATEGIC LLM 深度学习代码仓库 → 写 `code_learning_cache_key`
   - 任务二（`c_outline_refine`）：STRATEGIC LLM 基于 8 种文档默认大纲（从 `docs/*_OUTLINE.md` 加载） + 代码上下文细化纲要 → 写 `outline_cache_key`
   - 任务三（`d_content_fill`）：SMART LLM 按章节顺序填充内容（含 RAG 检索 + SVG 配图生成）→ 写 `content_cache_keys[idx]`，循环执行
   - 任务四（`e_review`）：SMART LLM 评审 D 的内容，与 D 形成修订循环（`max_revisions_per_chapter=3`）→ 写 `reviewed_cache_keys[idx]`，循环执行
   - 任务五（`f_merge`）：SMART LLM 合并所有章节 + 去重 → 写 `merged_cache_key`
   - 任务六（`g_final_in_subgraph`）：SMART LLM 终审 + 修改终审建议 → 写 `final_cache_key`

3. **缓存传递（核心约定，优先选择）**：6 步中间产物（代码学习摘要 / 纲要 / 各章节内容 / 评审建议 / 合并文档 / 终审文档）体积可能达数百 KB，**不推荐直接放入 LangGraph state**（导致 state 膨胀 + Checkpointer 写入瓶颈）。统一存 Redis（TTL 24 小时），state 仅存 `cache_key`。缓存键格式：`docbot:{agent_id}:{user_id}:{session_id}:{type}:{report_type}[:{chapter_idx}]`。

4. **并发控制（核心约定，优先选择）**：
   - `MAX_CONCURRENT_REPORTS=3`：单次请求最多并发派发 3 个 B 子图
   - `MAX_REVISIONS_PER_CHAPTER=3`：D-E 修订循环每章节最多 3 轮
   - `MAX_CHAPTERS_PER_REPORT=20`：单报告最大章节数
   - `MAX_LLM_CONCURRENCY=5`：全局 LLM 调用并发上限
   - `MAX_RAG_CONCURRENCY=10`：RAG 检索并发上限
   - 上述限制通过 `asyncio.Semaphore` 强制，超出时排队等待，不推荐软超时

## 6. 会话与上下文管理

**多会话支持（核心约定，优先选择）**：
- 会话隔离键为 `thread_id`（即 `session_id`），由请求上下文注入，不推荐客户端自造。
- 每个 Agent 应支持并发多会话；会话间状态通过 Postgres Checkpointer 隔离，不推荐共享可变内存。
- 会话级数据（消息历史/中间状态/缓存）应按 `agent_id` + `user_id` + `session_id` 三级分键存储，不推荐全局共享；`agent_id = agent_name`（见第 7 章），`user_id` 由第 8 章身份解析获得。
- 报告子图 thread_id 格式：`{agent_id}:{session_id}:{report_type}`，与顶层图区分。

**上下文窗口（核心约定，优先选择）**：
- 单会话上下文上限 `CONTEXT_MAX_CHARS = 500_000`（约 125K token）。
- 任务一的代码学习结果可能超过 125K token，写入会话前应调用 `compress_if_needed()` 检查阈值；超限应压缩（用 FAST LLM glm-4-flash 降本），不推荐直接丢弃。
- 上下文压缩策略：滑动窗口 + LLM 摘要，保留最近 25% 文件为原文，其余摘要化。
- 压缩应异步后台执行（`asyncio.create_task`），不阻塞用户响应。

**会话生命周期（核心约定，优先选择）**：
- 会话持久化到 Postgres Checkpointer；内存 Checkpointer 仅 `ENV=dev` 允许。
- 会话 TTL 默认 30 天（`CONTEXT_SESSION_TTL=2592000`），过期会话由定时任务清理。
- 会话删除应级联清理：Checkpoint + Redis 缓存（含 6 步流水线缓存）+ 业务元数据 + 临时克隆目录 `temp/repos/{user_id}/`。
- 写入防抖 `DEBOUNCE_SECONDS = 1.0`，后台 flush 线程 `FLUSH_INTERVAL_SECONDS = 0.5`。

**启动时数据初始化（核心约定，优先选择）**：
- Agent 容器启动时（`server.py` lifespan）应执行 PostgreSQL 业务表初始化，失败不阻断启动（仅告警，`depends_on: service_healthy` 已保证依赖就绪）：
  - **PostgreSQL 业务表初始化**：`src/memory/db_initializer.py` 的 `init_database()` 读取 `scripts/init.sql` 并执行；所有 DDL 使用 `CREATE TABLE/INDEX IF NOT EXISTS` + `ALTER TABLE IF EXISTS ... ADD COLUMN IF NOT EXISTS ...`，天然幂等，支持重复启动；触发器/函数使用 `CREATE OR REPLACE FUNCTION` + `CREATE OR REPLACE TRIGGER`（PostgreSQL 14+, 项目要求 ≥17 满足）保证幂等。不推荐在 Docker 构建时通过 `Dockerfile.postgres` 内嵌 `init.sql` 执行 DDL，统一由 Agent 启动时触发。
  - **`scripts/init.sql`**：包含完整 DDL（基础 DDL + docbot 专属 DDL）。docbot 专属 DDL 新增 `user_git_repos` 表 + 扩展 `research_reports` 表 3 列（`report_type_label` / `report_summary` / `report_image_svg`）+ 通用 `update_updated_at_column()` 函数与触发器。
  - **系统 MCP 子进程启动**：`server.py` lifespan 应启动 `mcp-server-git` + `mcp-server-filesystem` 子进程（由 `GitMCPAdapter` 包装），不依赖外部 MCP 进程。子进程在 lifespan 退出时自动终止。MCP 配置**不入 `mcp_configs` 表**，所有用户共享，不暴露 CRUD 端点。

## 7. 数据隔离与检索核心规则

**多 Agent 数据隔离总则（核心约定，优先选择）**：
- 本项目独立运行，所有数据通过 `agent_id = 'agentinsight-docbot'` 在数据库内隔离。
- 所有持久化层（Qdrant/Postgres/Redis）应以 `agent_id` 区分；用户私有数据（Postgres 业务表/Redis 缓存/Qdrant 用户代码索引）进一步按 `user_id` 区分，不推荐跨用户共享；Qdrant 共享知识库仅按 `agent_id` 区分，不与 `user_id` 挂钩。
- Agent 注册时应声明 `agent_name`，由配置注入，不推荐运行时硬编码。

**PostgreSQL 约定**：单一数据库 `agents`。LangGraph Checkpointer 表由官方管理（`thread_id` 已含会话隔离）。业务表应含 `agent_id` + `user_id` 双列（VARCHAR(64)，建复合索引）区分各用户数据；查询应显式 `WHERE agent_id = ... AND user_id = ...`，不推荐无过滤的全表扫描。表名复数 snake_case，不推荐按用户拆表。

**业务表时间戳字段约定（核心约定，优先选择）**：
- 所有业务表应含 `created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`；状态会变更的表（如 `research_sessions`/`research_reports`/`uploaded_files`/`user_git_repos`）还应含 `updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`，并通过 `BEFORE UPDATE` 触发器（`CREATE OR REPLACE FUNCTION update_updated_at_column()` + `CREATE OR REPLACE TRIGGER`）自动维护，不推荐业务代码手动赋值。
- 纯日志表（如 `research_search_logs`/`token_usage_logs`）只需 `created_at`，不需要 `updated_at`（INSERT-only 设计）。
- `agent_id`/`user_id`/`session_id` 三列在所有业务表中应保持相同长度（推荐统一 VARCHAR(64)），避免跨表 JOIN 时类型/长度不一致引发隐式转换。

> **不推荐保留 `mcp_configs` 表（核心约定）**：本系统不使用 `mcp_configs` 表存储 MCP 配置。`mcp-server-git` + `mcp-server-filesystem` 由系统启动时自动注册（见第 6 章 lifespan），所有用户共享。`scripts/init.sql` 中的 `mcp_configs` 表 DDL（如存在）应标注为废弃或移除；API 层不暴露 `/v1/mcp/configs` 端点。

**docbot 新增业务表 `user_git_repos`（核心约定，优先选择）**：
存储用户代码仓库配置（仅个人仓库，无系统仓库），DDL 见 `scripts/init.sql`。关键字段：
- `id VARCHAR(64) PRIMARY KEY`（uuid4）
- `agent_id` + `user_id` 双列隔离（建复合索引）
- `platform VARCHAR(32)`：`github|gitlab|gitee|bitbucket|coding|gitea|custom`
- `auth_type VARCHAR(16)`：`none|token|password|ssh_key`
- `encrypted_token` / `encrypted_username` / `encrypted_password` / `encrypted_ssh_key` / `ssh_passphrase`：AES-GCM 加密存储（密钥由 `settings.git_credential_key` 环境变量注入，属第 11 章硬约束）
- `default_branch` / `clone_depth`（0=完整克隆，>0=浅克隆深度）/ `enabled` / `last_synced_at` / `last_sync_status` / `last_sync_error`
- API 响应禁止返回敏感字段原文，仅返回 `has_token: bool` 等标志位（属第 11 章硬约束）

**docbot 扩展 `research_reports` 表 3 列（核心约定，优先选择）**：
- `report_type_label VARCHAR(64)`：8 种文档类型取值（`architecture|design|requirements|testcase|optimization|performance|defect|api_doc`）
- `report_summary TEXT`：200 字以内文档摘要
- `report_image_svg TEXT`：文档配图 SVG（DeepSeek 生成）
- 通过 `ALTER TABLE IF EXISTS ... ADD COLUMN IF NOT EXISTS ...` 幂等追加

**Qdrant 集合约定**：单一集合 `agents`，`distance=Cosine`，`vector_size=768`（bge-base-zh-v1.5 固定维度）。按 payload `namespace` 字段隔离数据，分两类：
- **共享知识库**（非用户导入数据）：`namespace = agent_id`（即 `agentinsight-docbot`），payload 不含 `user_id`，所有 docbot 用户共享，检索时默认召回。
- **用户私有数据**（用户代码仓库索引）：`namespace = {agent_id}:{user_id}:{repo_id}`（即 `agentinsight-docbot:{user_id}:{repo_id}`），payload 含 `user_id` + `repo_id` + `file_path` + `language` + `chunk_type` 字段，仅该用户可检索，不推荐跨用户/跨仓库召回。

> **多仓库隔离核心约定（核心约定，优先选择）**：用户可配置多个代码仓库，会话内选择仓库使用。Qdrant namespace 必须含 `repo_id` 维度，格式 `agentinsight-docbot:{user_id}:{repo_id}`，实现用户×仓库二维隔离。检索时显式传 `repo_id` 对应的 namespace，不推荐跨仓库召回（避免代码上下文混淆）。

点 id 用 `uuid5(NAMESPACE_DNS, f"{namespace}:{content_hash}")` 幂等生成。写入 payload 应含 `content`+`metadata`+`namespace` 三键（用户私有数据额外含 `user_id`/`repo_id`）。检索时应显式传目标 namespace 列表（仅当前用户当前仓库私有），不推荐无 namespace 过滤的全集合扫描。Qdrant 服务端通过环境变量 `QDRANT__SERVICE__STATIC_API_KEY` 开启静态 API Key 鉴权，客户端（`rag/qdrant_manager.py`）应通过 `qdrant_api_key` 配置传递 API Key；API Key 仅在 `.env`/`.env.qa` 配置，不推荐硬编码（硬编码属第 11 章硬约束）。

**代码仓库索引策略（核心约定，优先选择）**：
1. **克隆**：通过 `mcp-server-git` 或直接 `git clone` 到 `temp/repos/{user_id}/{repo_id}/`；支持浅克隆（`clone_depth=1`）减少 IO 与 token 消耗
2. **文件枚举**：跳过 `.git/` / `node_modules/` / `__pycache__/` / `dist/` / `build/` / `.venv/` / `.next/` / `target/`
3. **分块**：按文件类型分块——代码文件（.py/.js/.ts/.go/.java/...）按函数 / 类分块（AST 解析）；配置文件（.yml/.json/.toml/...）整体作为一个 chunk；文档文件（.md/.rst/.txt）按章节分块（标题层级）
4. **嵌入**：调用 `rag/embeddings.py` 的 `embed_batch()`，使用远程 TEI（bge-base-zh-v1.5，768 维）
5. **写入 Qdrant**：`namespace=agentinsight-docbot:{user_id}:{repo_id}`，payload 含 `repo_id` / `file_path` / `language` / `chunk_type`
6. **索引完成**：更新 `user_git_repos.last_synced_at` / `last_sync_status` / `last_sync_error`
7. **仓库大小限制**：`MAX_REPO_SIZE_MB=1024`，超出拒绝克隆并告警

**Redis 约定**：所有键应加前缀 `{agent_id}:{user_id}:`，完整键格式 `{agent_id}:{user_id}:{module}:{type}:{id}`。6 步流水线缓存键格式：`docbot:{agent_id}:{user_id}:{session_id}:{type}:{report_type}[:{chapter_idx}]`，TTL 24 小时。不推荐使用无 `agent_id` 或 `user_id` 前缀的裸键。会话级数据按 `{agent_id}:{user_id}:{session_id}` 三级分键。应设 TTL，不推荐永久键（配置数据除外）。

**RAG 流水线**：检索应混合 BM25 + 向量（bge-base-zh-v1.5），默认 `vector_weight=0.7 / bm25_weight=0.3`。重排序默认不启用；当 `rerank_enabled=True` 时，重排序经 `bge-reranker-v2-m3`，Top-K 召回后 rerank，不推荐直接用向量分数作最终排序。`score_threshold` 默认 0.3，低于阈值丢弃（仅当 rerank 启用时生效，RRF 融合分数不应用此阈值）。Embedding 调用统一走 `rag/embeddings.py`，不推荐业务代码直连 API。Embeddings/Rerank TEI 服务通过环境变量 `API_KEY` 开启鉴权，客户端（`rag/embeddings.py`/`rag/retriever.py`）应通过 `embeddings_api_key`/`rerank_api_key` 配置传递 `Authorization: Bearer <key>` 请求头；API Key 仅在 `.env`/`.env.qa` 配置，不推荐硬编码。

**上下文压缩 Embeddings（核心约定，优先选择）**：上下文压缩使用本地 FastEmbed（bge-small-zh-v1.5 ONNX INT8，512 维），不依赖远程 TEI 服务，解决 TEI CPU 部署性能瓶颈。Qdrant 索引仍使用远程 TEI（bge-base-zh-v1.5，768 维）。FastEmbed 客户端封装在 `rag/fastembed_client.py`，懒加载 + 线程安全 + LRU 缓存 + 降级到远程 TEI。

**文档类型 4 层适配机制（核心约定，优先选择）**：
docbot 8 种文档类型（技术架构 / 概要设计 / 需求 / 测试用例 / 系统优化 / 性能分析 / 系统缺陷 / API 文档）刻意不引入 `DocTypeClassifier`，用 4 层隐形机制替代，不推荐业务代码 if-else 文档类型分支：
1. **Persona 层**：`src/config/docbot/personas.py` 的 `DOCBOT_REPORT_PERSONAS` 字典为每种文档类型定义 `role_name` + `description` + `tone` + `target_audience` + `outline_file`，通过 `agent_role` 注入复用 `ReportGenerator`（零代码改动），无 if-else 文档类型分支。
2. **Outline 层**：`src/config/docbot/outlines.py` 提供 `load_outline(report_type)` 加载器，运行时从 `docs/*_OUTLINE.md` 读取默认大纲（8 种独立文件，对应 IEEE 软件工程标准 / Google Tech Writing Guide / Microsoft Docs 风格指南），任务二 STRATEGIC LLM 在此基础上根据代码上下文细化。
3. **Retriever 层**：任务三 D 内容填充时按章节标题 + 关键词检索 Qdrant 用户私有数据（代码索引，namespace 含 `repo_id`），使用从 AIR 拷贝的 `rag/retriever.py` 实现。
4. **MCP 层**：系统启动时自动注册 `mcp-server-git` + `mcp-server-filesystem`，`GitMCPAdapter`（`tools/git_mcp.py`）让 LLM 自动选工具访问代码仓库。MCP 配置不入 `mcp_configs` 表、不暴露 CRUD 端点。

**8 种文档默认大纲文件（核心约定，优先选择）**：
| 文档类型 | outline_file |
|---------|--------------|
| 技术架构文档（`architecture`） | `docs/ARCHITECTURE_OUTLINE.md` |
| 概要设计文档（`design`） | `docs/HLD_OUTLINE.md` |
| 需求文档（`requirements`） | `docs/PRD_OUTLINE.md` |
| 测试用例文档（`testcase`） | `docs/TEST_CASE_OUTLINE.md` |
| 系统优化文档（`optimization`） | `docs/OPTIMIZATION_OUTLINE.md` |
| 性能分析文档（`performance`） | `docs/PERF_ANALYSIS_OUTLINE.md` |
| 系统缺陷文档（`defect`） | `docs/DEFECT_OUTLINE.md` |
| API 文档（`api_doc`） | `docs/API_DOC_OUTLINE.md` |

不推荐：新增 `DocTypeClassifier` / `doc_type_prompts/*.yaml` 等基于文档类型分类器的实现；节点内 `if report_type == "xxx"` 分支；硬编码文档类型 prompt 字典；将默认大纲内嵌到 Python 代码中（应通过外部 Markdown 文件加载，便于非开发人员维护）。如确需分类器方案，应说明理由并等待用户确认。

**支持语言（核心约定，优先选择）**：
docbot 文档输出仅支持 2 种语言：
| 语言 | 代码 | 说明 |
|------|------|------|
| 简体中文 | `zh` | 默认语言 |
| English | `en` | 英文输出 |

`coordinator_a` 节点应校验 `language` 取值（仅接受 `zh` / `en`），非法值返回 `invalid_language` 错误。调用方（演示平台 `../agentinsight-demo` 或其他 API 客户端）应仅传递这 2 种语言值。不推荐扩展更多语言（如日韩）以避免翻译资源维护成本。

## 8. 用户身份解析规则

**Bearer JWT Token 处理（核心约定，优先选择；从 AIR 拷贝实现）**：
- Agent 接受请求头 `Authorization: Bearer <jwt_token>`；token 可选，不存在时走 IP-based 用户身份解析路径。
- token 存在时：使用 PyJWT HS256 本地解析（密钥 `JWT_SECRET` 环境变量注入），提取 `user_id`；解析失败按无 token 处理并告警。
- token 不存在或解析失败时（`self_host=True`）：通过 `src/api/ip_user_resolver.py` 基于客户端 IP 生成确定性 `user_id`（IP-based 解析）；`self_host=False` 时返回 401 错误。
- 解析得到的 `user_id` 应注入请求上下文，供后续节点、会话、数据持久化、代码仓库配置隔离使用（见第 6/7 章）。

**IP-based 用户身份解析（核心约定，优先选择；从 AIR 拷贝实现）**：
- 当请求不含 `Authorization: Bearer <jwt_token>` 头时，Agent 可通过客户端 IP 地址解析用户身份（适用于内网部署/无 JWT 网关场景）。
- IP 解析通过 `src/api/ip_user_resolver.py` 实现，将客户端 IP 映射到 `user_id`。
- IP 白名单与映射配置存储在 PostgreSQL 业务表，按 `agent_id` 隔离。
- 优先级：Bearer JWT Token > IP-based 解析（`self_host=True` 时为最终降级）。
- `self_host=False`（云托管）时，无 Token 或 Token 校验失败返回 401，不走 IP 降级。
- 生产环境应配置可信代理链（`X-Forwarded-For` 头信任），避免 IP 伪造攻击（属第 11 章安全硬约束）。

**安全约束**：
- JWT 验证与 `user_id` 获取应在 API 入口中间件完成，不推荐在业务节点内重复解析。
- 禁止将原始 JWT token 写入日志或持久化存储；仅保留解析后的 `user_id`（属第 11 章安全硬约束）。

## 9. 工具与模型网关规则

**工具（MCP）**：外部工具优先通过 MCP Server 暴露；节点内不推荐定义 ad-hoc tool function。**docbot 的 MCP 工具为系统自带**：`mcp-server-git` + `mcp-server-filesystem` 由 `server.py` lifespan 启动子进程，所有用户共享，不存入 `mcp_configs` 表、不暴露 `/v1/mcp/configs` CRUD 端点、不通过用户配置启用/禁用。`tools/git_mcp.py` 的 `GitMCPAdapter` 包装这两个 MCP 服务，提供 `clone_repo` / `list_files` / `read_file` / `get_file_history` / `search_code` / `test_connection` 等方法。工具调用应经 AgentInsight `trace_tool` span 包裹（见第 10 章），参数与结果入 span。敏感工具（写文件/执行命令）应显式声明权限，由中间件校验。

**用户代码仓库 MCP 服务（核心约定，优先选择；系统自带，非用户配置）**：
docbot 通过 `src/tools/git_mcp.py` 的 `GitMCPAdapter` 访问用户代码仓库，底层封装 `mcp-server-git`（社区实现）+ `mcp-server-filesystem`（官方），两个 MCP 服务由 `server.py` lifespan 启动子进程：
- `clone_repo(repo_id, user_id)`：克隆仓库到 `temp/repos/{user_id}/{repo_id}/`，已存在则 `git pull` 更新
- `list_files(repo_path, pattern)`：枚举文件，跳过 `.git/node_modules/__pycache__/dist/build/.venv` 等
- `read_file(repo_path, file_path)`：读取文件内容（限制 10MB）
- `get_file_history(repo_path, file_path, limit)`：获取文件提交历史
- `search_code(repo_path, query)`：代码搜索（grep 模式）
- `test_connection(repo_config)`：通过 `git ls-remote` 探活（不实际克隆）

> **MCP 系统自带约定**：MCP 配置**不存入 `mcp_configs` 表**，因为所有用户都需要使用相同工具，不区分用户。`server.py` lifespan 启动时拉起 MCP 子进程，lifespan 退出时终止子进程。API 不暴露 `/v1/mcp/configs` 端点；用户代码仓库的配置通过 `/v1/repos` 端点管理（不与 MCP 配置混用）。

认证方式支持全集：`none`（公开仓库）/ `token`（GitHub PAT / GitLab PAT / Gitee 私人令牌，推荐）/ `password`（基础认证，不推荐）/ `ssh_key`（私钥 + 可选 passphrase，推荐用于自托管）。支持平台全集：`github` / `gitlab` / `gitee` / `bitbucket` / `coding`（Coding.net）/ `gitea`（自托管）/ `custom`（任意 HTTP(S)/SSH URL）。

**模型网关（LiteLLM）**：LLM 调用优先经 `llm/` 的 `LLMClient`（底层 LiteLLM ≥1.6）；不推荐直接 `openai`/`anthropic` 等 SDK（如需直连应说明理由并等待用户确认）。模型名以 LiteLLM 路由前缀声明（如 `deepseek/deepseek-v4-flash`），由配置注入，不推荐硬编码。流式统一 `achat_stream`；同步 `achat_strategic`/`achat_smart`/`achat_fast` 仅用于非交互式批处理。

**LiteLLM 路由识别机制（核心约定，优先选择）**：
- 用户在 LiteLLM 模型名前缀中声明 provider（如 `deepseek/deepseek-v4-flash`），LiteLLM 内置 `litellm.provider_list` 字典自动映射到官方 API URL，**不配 `api_base` 时自动识别 provider 并使用官方 URL**。
- 用户可通过 `fast_llm_api_base` / `smart_llm_api_base` / `strategic_llm_api_base` 配置覆盖默认 URL（用于自托管 / 代理）。
- 用户可通过 `os.environ["<PROVIDER>_API_KEY"]` 注入密钥（如 `DEEPSEEK_API_KEY` / `ZHIPUAI_API_KEY`），仅环境变量注入，禁止入仓。

**国内大模型兼容性（核心约定，优先选择）**：
LiteLLM ≥1.6 原生支持以下国内大模型 provider（无需自配 BaseURL）：智谱 AI（`zhipuai/`）/ DeepSeek（`deepseek/`）/ 通义千问（`dashscope/` 或 `openai/` 兼容模式）/ 百度文心（`ernest/` 或 `baidu/`）/ 月之暗面 Kimi（`moonshot/`）/ MiniMax（`minimax/`）/ 百川（`baichuan/`）/ 讯飞星火（`spark/`）/ 商汤日日新（`sensetime/`）。
**不完全兼容列表**（需 `api_base` 显式覆盖）：字节豆包（Doubao，必须配 `api_base=https://ark.cn-beijing.volces.com/api/v3`）/ 阶跃星辰（StepFun，必须配 `api_base=https://api.stepfun.com/v1`）/ 私有部署模型（如本地 vLLM，必须配 `api_base` + 模型名前缀用 `openai/`）。

用户指定的三级 LLM（`zhipuai/glm-4-flash` / `deepseek/deepseek-v4-flash` / `deepseek/deepseek-v4-pro`）均为原生支持，无需配 `api_base`。

## 10. 可观测性与评测规则

**可观测性内核（核心约定，优先选择；从 AIR 拷贝实现）**：
- 优先使用 **AgentInsight Python SDK**（pip 名 `agentinsight-sdk`，导入名 `agentinsight`，版本 ≥0.1.5），底层依赖 OpenTelemetry SDK，由 `observability/tracing.py` 统一封装。如需改用其他可观测后端（如 Langfuse/LangSmith），应说明理由并等待用户确认。
- **追踪调用方式优先**：异步上下文管理器 `async with trace_xxx(...) as span`；**不推荐观察者模式**（无 Subject/Observer、无 attach/notify）；`@agentinsight.observe` 装饰器已弃用。
- SDK 初始化在 `observability/tracing.py` 模块导入时一次性完成，参数从 `config.py` 注入：`AGENTINSIGHT_PUBLIC_KEY`/`AGENTINSIGHT_SECRET_KEY`/`AGENTINSIGHT_HOST`；生产环境应校验密钥存在。
- **降级策略**：SDK 初始化失败或运行时异常时，所有 `trace_xxx` yield `_NoopSpan`（Null Object 模式），业务代码不推荐判断 SDK 是否可用，`span.update()` 调用永远安全。
- 业务代码不推荐直接调用 `agentinsight.init()`/`agentinsight.get_client()`/`client.flush()`；统一经 `observability/tracing.py` 封装的 6 类 `trace_xxx`。
- 业务代码不推荐直接使用 `opentelemetry-sdk` 原生 API。

**6 类 trace span（签名与必带字段；从 AIR 拷贝）**：

| trace 类型 | as_type | 必带字段 | docbot 包裹位置 |
|---|---|---|---|
| `trace_agent` | `agent` | `name`/`input`/`metadata`(含 `session_id`/`intent`)/`session_id`/`user_id` | 顶层图入口（`coordinator_a`），metadata 含 `report_types` / `repo_id`，建立根 span |
| `trace_generation` | `generation` | `name`/`model`/`model_parameters`/`usage_details`/`cost_details` | `llm/` 网关层（从 AIR 拷贝的 LLMClient），业务节点层**不重复包裹**；降级时记录 `metadata.fallback_from` / `metadata.fallback_to` |
| `trace_tool` | `tool` | `name`/`input`/`output`(span.update)/`metadata`(含 `tool_name`/`success`) | `tools/git_mcp.py` 的 MCP 调用（clone/list_files/read_file/search_code/test_connection） |
| `trace_retriever` | `retriever` | `name`/`input`/`output`/`metadata`(含 `matched`/`candidate_count`/`retriever_type`/`top_score`) | 任务三 D 内容填充时的 RAG 检索（BM25+Vector+RRF+Rerank） |
| `trace_chain` | `chain` | `name`/`input`/`output` | 报告子图 6 步流水线（`docbot.report.{report_type}.code_learning` / `outline_refine` / `content_fill.{chapter_idx}` / `review.{chapter_idx}` / `merge` / `final_review`）+ 顶层图（`docbot.coordinator_a` / `spawn_b_tasks` / `final_reviewer_g` / `save_reports`） |
| `trace_embedding` | `embedding` | `name`/`model`/`usage_details`(含 `token_count`) | `rag/embeddings.py`，仓库索引时的 embedding 调用（head-based 0.5 采样） |

**span 命名约定（核心约定，优先选择）**：
- 顶层图：`docbot.coordinator_a` / `docbot.spawn_b_tasks` / `docbot.final_reviewer_g` / `docbot.save_reports`
- 报告子图：`docbot.report.{report_type}.b_init` / `.code_learning` / `.outline_refine` / `.content_fill.{chapter_idx}` / `.review.{chapter_idx}` / `.merge` / `.final_review`
- 缓存：`docbot.cache.write` / `docbot.cache.read`

**跨节点 span 传播（核心约定，优先选择）**：
- span 父子关系由 OpenTelemetry Context API 在同一 asyncio task 内**自动传播**，不推荐手动传递 span 对象（破坏自动传播语义）。
- 编排器应用 `trace_agent` 包裹 `graph.ainvoke()` 作为根 span；LangGraph 节点内创建的子 span 自动关联到根 span。
- 报告子图通过 `asyncio.gather` 并发派发，每个子图独立 asyncio task，span 自动隔离（不交叉）。
- 认证上下文（token/user_id 等）不应用 span 上下文传递（属安全硬约束，见第 11 章）；认证信息应通过 `contextvars` + State 字段在节点入口显式恢复。
- `span.update(output=...)` 可在 `with` 块内多次增量调用；`trace_id`/`id` 为只读属性。

**采样策略**：
- `trace_agent`/`trace_generation`/`trace_tool`/`trace_retriever`/`trace_chain`：全量 1.0 采样。
- `trace_embedding`：head-based 采样，默认 `tracing_embedding_sample_rate=0.5`（高频 embed 调用降采样减存储压力）。
- SDK 底层用 `BatchSpanProcessor` 后台线程批量导出，HTTP 上报失败不阻塞主流程；业务代码不推荐调用 `client.flush()` 阻塞事件循环。

**评测门禁（CI 强制，不达标不推荐合并 main）**：
- RAGAS：faithfulness ≥0.8 / answer_relevancy ≥0.8 / context_precision ≥0.7
- DeepEval：任务完成率 ≥0.9 / 工具调用正确率 ≥0.95 / 幻觉率 ≤0.1

## 11. 安全合规红线（真正硬约束，不可放松）

> 本章为真正的硬约束，涉及密钥/PII/注入/传输安全等法律与合规底线，与第 1-10/12-13 章的"优先选择/不推荐"架构偏好不同，不可放松。任何偏差需经安全评审并经用户显式确认。

- **密钥**：仅环境变量注入，禁止入仓/硬编码/日志；API Key SHA256+BCrypt 双哈希，仅创建时返回一次；密码 BCrypt(cost=12)；发现硬编码密钥即 P0 暂停并人工介入。
- **代码仓库敏感字段加密（docbot 专属硬约束）**：用户代码仓库的 `token`/`password`/`ssh_key`/`ssh_passphrase` 必须使用 AES-GCM 加密存储（密钥由 `GIT_CREDENTIAL_KEY` 环境变量注入，32 字节）；API 响应禁止返回密钥原文，仅返回 `has_token: bool` 等标志位；密钥仅创建/更新时接受明文，立即加密后丢弃明文。
- **PII**：用户会话内容加密存储+日志脱敏；API 响应禁止返回密码/密钥原文；**用户代码仓库内容不外泄**——代码内容仅用于 LLM 上下文 + Qdrant 索引，不写入日志、不入 `trace_generation` 的 input（仅入 `metadata.code_summary_length`）；最小化收集，按用途设保留期。
- **Prompt Injection**：所有外部输入（含用户 JSON 指令 / 代码仓库内容 / RAG 检索结果）经 Pydantic 校验；工具调用权限隔离（`read`/`write`/`execute`/`network` 显式授权）；禁止 `eval`/`exec` 求值用户输入；LLM 输出经结构化校验后再入工具；代码仓库 URL 白名单（可选 `ALLOWED_GIT_DOMAINS` 防内网渗透）。
- **仓库克隆隔离**：每用户独立临时目录 `temp/repos/{user_id}/{repo_id}/`，任务结束清理；仓库大小限制 `MAX_REPO_SIZE_MB=1024`，超出拒绝克隆；克隆深度限制 `clone_depth` 默认 0（完整），可配 1（浅克隆）减少 token 消耗；禁止 Agent 通过 PowerShell 修改任何项目文件（见下文 Agent 操作约束）。
- **传输与边界**：生产强制 HTTPS；安全响应头中间件（nosniff/DENY/HSTS）不可绕过；生产关闭 Debug。
- **Agent 操作约束（文件修改硬约束）**：禁止 Agent 通过 PowerShell（含 `Set-Content`/`Add-Content`/`Out-File`/`echo >`/`>>` 重定向/`[System.IO.File]::WriteAllText` 等 PS 原生写文件命令）修改任何项目文件；文件读取/创建/编辑/删除统一使用专用工具（Read/Write/Edit/DeleteFile/Glob/Grep）。理由：(1) 专用工具走审计链路，可追溯可回滚；(2) PS 写文件绕过权限校验与编码约定（易引入 BOM/CRLF 问题）；(3) 与 Trae IDE 工具规范一致。违例即阻断合并并提 P0。仅允许在 RunCommand 中使用 PowerShell 执行与文件修改无关的命令（如 `git`/`docker`/`python -m pytest`/`docker compose` 等系统命令）。
- **CORS（不推荐 `*`，但不禁；属架构偏好非硬约束）**：`CORS_ALLOW_ORIGINS=*` 不推荐用于生产（暴露面过大，违反最小权限原则），但并非第 11 章硬约束；生产推荐配置具体域名列表（如 `https://your-domain.com,http://localhost:8068`），开发/QA 环境可酌情放宽；如确需 `*`（如开源社区快速起栈），应说明理由并经用户确认。

## 12. 部署规则

> **与主目录部署规则的关系（核心约定，优先选择）**：通用部署约定（容器清单 / APIKey 鉴权 / QA 离线包结构 / 健康检查 / 卷管理 / 端口绑定 / 容器命名等）以主目录 `../AGENTS.md` 第 12 章为准，本节仅说明 docbot 的差异与边界。冲突时以主目录规则为基准、本节为补充。

**容器清单（5 个独立容器，独立编排）**：

> docbot 为独立可部署系统，5 容器均在 `docker-compose.yml` 内编排：postgres / redis / qdrant / embeddings / agent-docbot。不依赖任何外部项目存在。
> 生产联网模式 PostgreSQL 由本地 `postgres` 容器提供，与 redis/qdrant/embeddings 同属 compose 编排；业务表由 Agent 启动时执行 `scripts/init.sql` 创建（幂等）。
> QA 模式（离线）保留本地 `postgres` 容器，与 redis/qdrant/embeddings 同属 compose 编排，便于无外部数据库的离线测试环境。
> 生产离线模式 PostgreSQL 由外部托管服务提供（env 配置 `POSTGRES_HOST`/`PORT`/`USER`/`PASSWORD`/`DB`），不在 compose 内构建；业务表由 Agent 启动时执行 `scripts/init.sql` 创建（幂等）。

| 服务 | 镜像/构建 | 端口 | 健康检查 |
|------|----------|------|---------|
| `agent-docbot` | 本仓 `Dockerfile`（Python 3.12-slim，含 git 二进制 + mcp-server-git + mcp-server-filesystem） | 8068 | `GET /health` |
| `embeddings` | BGE 服务镜像（bge-base-zh-v1.5） | 8088 | `GET /health` |
| `qdrant` | `qdrant/qdrant:≥1.18` | 6333/6334 | `/healthz` |
| `redis` | `redis:≥8` | 6379 | `redis-cli ping` |
| `postgres`（生产联网模式 + QA 模式） | `postgres:≥17`（业务表由 Agent 启动时执行 `scripts/init.sql` 创建） | 5432 | `pg_isready -U <user>` |

**APIKey 鉴权（核心约定，优先选择；密钥硬编码属第 11 章硬约束）**：
- Qdrant 通过 `QDRANT__SERVICE__STATIC_API_KEY` 环境变量开启静态 API Key 鉴权；客户端通过 `QDRANT_API_KEY` 传递。
- Embeddings/Rerank TEI 服务通过 `API_KEY` 环境变量开启鉴权；客户端通过 `EMBEDDINGS_API_KEY`/`RERANK_API_KEY` 传递 `Authorization: Bearer <key>` 请求头。
- docbot 代码仓库加密密钥 `GIT_CREDENTIAL_KEY` 通过环境变量注入（32 字节，用于 AES-GCM 加密 `user_git_repos` 表敏感字段）。
- 所有 API Key 仅在 `.env`/`.env.qa` 配置，禁止硬编码（属第 11 章安全硬约束）；compose 文件通过 `${VAR:-}` 插值引用。

**QA 部署核心约定（优先选择，参考 AgentInsightService 模式；离线产物路径已上移到主目录）**：
- 所有镜像应预下载为 tarball（`docker save -o ../packages/images/<image>.tar`），部署机 `docker load` 导入，不推荐部署时 `docker pull`。
- Python 依赖应预下载 wheel 到 `../packages/`，构建时 `pip install --no-index --find-links=/app/packages -r requirements.txt`，不推荐联网安装。
- 系统依赖（.deb，含 `git` 二进制 + `mcp-server-git` + `mcp-server-filesystem` Node 包）应预下载到 `../packages/debs/`，构建时 `dpkg -i /tmp/debs/*.deb`，不推荐 `apt-get update`。
- BGE 模型权重应预下载到 `../packages/models/`（`bge-base-zh-v1.5`，docbot 不使用 `bge-reranker-v2-m3`），不推荐运行时从 HuggingFace 下载。embeddings 容器（第三方 TEI 镜像）通过 bind mount 挂载到容器内 `/data/<model_name>:ro`（只读），compose 文件中与命名卷 `embeddings_models`（可写 HF cache）并列配置。
- 环境变量推荐 `LANG=C.UTF-8` / `PYTHONIOENCODING=utf-8`。
> 上述 `../packages/` 由主目录统一管理（见 `../AGENTS.md` 第 12 章），docbot 不再在仓库内维护 `packages/` 目录。

**容器编排核心约定（优先选择）**：
- `restart: always`（生产）/ `unless-stopped`（开发）。
- `depends_on` 应用 `condition: service_healthy`，不推荐裸依赖（无健康检查直连）。
- 依赖顺序：生产联网模式 `postgres` → `redis` → `qdrant` → `embeddings` → `agent-docbot`；QA 模式 `postgres` → `redis` → `qdrant` → `embeddings` → `agent-docbot`；生产离线模式 `redis` → `qdrant` → `embeddings` → `agent-docbot`（PostgreSQL 由外部托管，不在 `depends_on` 内）；`rerank` 为可选容器（`rerank_enabled=True` 时通过 `profiles: [rerank]` 启用，插入 `embeddings` 与 `agent-docbot` 之间，`agent-docbot` 不强制依赖 `rerank`）。
- 健康检查 `interval ≤ 30s` / `timeout ≤ 10s` / `retries ≥ 3` / `start_period ≥ 10s`。
- 数据卷应用 `driver: local`，命名卷 `redis_data` / `qdrant_data` / `embeddings_models` / `uploads_data` / `temp_repos`（生产联网模式与 QA 模式额外含 `postgres_data`）。
- 端口绑定：生产仅 `agent-docbot:8068`/`embeddings:8088`/`qdrant:6333` 对外暴露，其余（`postgres:5432`/`redis:6379`/`qdrant:6334` gRPC）绑定 `127.0.0.1`。

**Agent 容器核心约定（优先选择）**：
- 基础镜像 `python:3.12-slim`，非 root 用户运行。
- 多阶段构建：builder 阶段装依赖，runtime 阶段仅复制产物。
- runtime 阶段必须安装 `git` 二进制 + `mcp-server-git` + `mcp-server-filesystem`（Node.js 运行时），用于系统自带 MCP 子进程。
- `EXPOSE 8068`，`CMD ["python", "server.py"]`。
- env_file 分层：生产 `.env`（公共）+ `.env.agent`（Agent 专属）+ `.env.{env}`（环境覆盖）；QA `.env.qa`（QA 专属，全离线配置）；生产离线 `.env`（与生产联网共享配置）。
- 临时目录 `temp/repos/` 必须挂载为 volume（持久化用户克隆的代码仓库，避免容器重启丢失）。

**本仓库实际持有的构建文件（核心约定，优先选择）**：
docbot 仓库当前仅持有生产联网模式 + 生产离线模式所需的最小构建文件集合，QA 模式与生产离线模式的 compose 文件与构建脚本已统一移至主目录 `../`：

| 文件 | 状态 | 用途 |
|------|------|------|
| `Dockerfile` | ✅ 已有 | 生产联网模式 Agent 镜像构建 |
| `docker-compose.yml` | ✅ 已有 | 生产联网模式 5 容器编排 |
| `.env.template` | ✅ 已有 | 环境变量模板 |
| `Dockerfile.offline` | ✅ 已有 | 生产离线模式 Agent 镜像构建（QA 模式复用此镜像） |
| `docker-compose-qa.yml` | 🔄 已移至主目录 `../` | QA 模式 5 容器编排（由主目录统管） |
| `docker-build.qa.bat` | 🔄 已移至主目录 `../` | QA 模式构建脚本（由主目录统管） |
| `docker-compose-offline.yml` | 🔄 已移至主目录 `../` | 生产离线模式 5 容器编排（由主目录统管） |
| `docker-build.offline.sh` | 🔄 已移至主目录 `../` | 生产离线模式构建脚本（由主目录统管） |
| `docker-build.sh` | 🔄 已移至主目录 `../` | 生产联网模式构建脚本（由主目录统管） |

> **构建文件统管说明（核心约定，优先选择）**：QA 模式与生产离线模式相关的 `docker-compose-qa.yml` / `docker-build.qa.bat` / `docker-compose-offline.yml` / `docker-build.offline.sh` / `docker-build.sh` 已统一移至主目录 `../`，由主目录 `../AGENTS.md` 第 6 章统管，供本智能体与 `agentinsight-demo`、`agentinsight-researcher`、`agentinsight-asksql` 等共享。本仓库不再单独维护 QA 专属 Dockerfile 与对应 compose 文件，QA 模式直接复用 `Dockerfile.offline` 镜像，由主目录 `../docker-compose-qa.yml` 通过环境变量差异化配置。
> - 生产联网模式可使用裸 `docker compose -p agentinsight-docbot -f docker-compose.yml --env-file .env up -d` 起栈，或使用主目录 `../docker-build.sh` 脚本。
> - QA 模式与生产离线模式使用主目录 `../docker-build.qa.bat` / `../docker-build.offline.sh` 脚本起栈，离线产物路径指向 `../packages/`。
> - 主目录构建脚本已内置 `-p agentinsight-docbot` 项目名与容器名 `agentinsight-docbot-<service>-1` 命名规范，详见主目录 `../AGENTS.md` 第 6 章。
> - 入仓文件仅 `Dockerfile` / `docker-compose.yml` / `Dockerfile.offline` / `.env.template`；QA 与生产离线相关 compose 文件 / 构建脚本已加入主目录 `.gitignore`（不入仓，与主目录策略一致）。

**三套构建模式（与主目录对齐，构建文件路径见上表）**：
按部署场景选择，三套模式的统一约定以主目录 `../AGENTS.md` 第 6 章为准：

| 模式 | 构建文件 | 编排文件 | 环境文件 | 构建脚本 | 适用场景 |
|------|---------|---------|---------|---------|---------|
| QA 模式（离线） | `Dockerfile.offline` | `../docker-compose-qa.yml` | `../.env.qa` | `../docker-build.qa.bat` | QA 测试、内网环境 |
| 生产模式（联网） | `Dockerfile` | `docker-compose.yml`（本目录） | `.env` | `../docker-build.sh` | 开源社区、CI、外网环境 |
| 生产模式（离线） | `Dockerfile.offline` | `../docker-compose-offline.yml` | `.env` | `../docker-build.offline.sh` | 内网生产环境、离线部署 |

- **QA 模式（离线）**：所有文件宿主机预下载到 `../packages/`（wheels/debs/models/images），构建时 `pip install --no-index` 离线安装，部署时 `docker load` 加载镜像 tarball，模型从本地 volume 加载。适用于 QA 测试。所有端口绑定 `127.0.0.1`，仅本机访问。
- **生产模式（联网）**：构建时从 PyPI 下载 Python 依赖、从 Docker Hub 拉取基础镜像（含 `postgres` 容器），无需预下载 `../packages/`。适用于开源社区贡献者快速起栈。仅 `agent-docbot:8068`/`embeddings:8088`/`qdrant:6333` 对外暴露，其余（`postgres:5432`/`redis:6379`/`qdrant:6334` gRPC）绑定 `127.0.0.1`。
- **生产模式（离线）**：所有文件宿主机预下载到 `../packages/`（wheels/debs/models/images），构建时 `pip install --no-index` 离线安装，部署时 `docker load` 加载镜像 tarball，模型从本地 volume 加载。镜像版本由 `../packages/images/` 中的 tarball 决定，compose 文件中硬编码以确保匹配。适用于内网生产环境或离线部署。仅 `agent-docbot:8068`/`embeddings:8088`/`qdrant:6333` 对外暴露，其余（`postgres:5432`/`redis:6379`/`qdrant:6334` gRPC）绑定 `127.0.0.1`。
- QA 模式相关文件已加入主目录 `.gitignore`（不入仓）：`docker-compose-qa.yml`、`docker-build.qa.bat`、`packages/wheels/`、`packages/debs/`、`packages/models/`、`packages/images/`。
- 生产离线模式相关文件已加入主目录 `.gitignore`（不入仓）：`docker-compose-offline.yml`、`docker-build.offline.sh`。
- "不推荐部署时联网拉镜像/装依赖/下模型" 约束适用于**QA 模式**和**生产离线模式**；生产联网模式允许构建时联网。

**不推荐（选用需说明理由并等待用户确认）**：
- QA 模式和生产离线模式部署时联网拉镜像/装依赖/下模型（破坏离线部署前提）。
- 单容器混装多服务（如 agent + qdrant 同容器，破坏单一职责与可独立扩缩容）。
- 绕过 `depends_on: service_healthy` 直接连未就绪服务（破坏依赖顺序保证）。
- 使用 `latest` 标签（应锁版本，避免镜像漂移）。
- 生产环境映射非必要端口到 0.0.0.0（破坏最小暴露原则）。

**容器命名约定（核心约定，优先选择）**：
- 容器编排应使用 `-p agentinsight-docbot` 项目名（即 `docker compose -p agentinsight-docbot -f <compose-file> --env-file <env-file> up -d`），不推荐使用默认项目名。
- 主目录的三套构建脚本（`../docker-build.qa.bat` / `../docker-build.sh` / `../docker-build.offline.sh`）均已内置 `-p agentinsight-docbot`，应优先使用脚本而非裸 `docker compose up -d`。
- **部署务必使用脚本而非裸 `docker compose` 命令（核心约定，优先选择）**：QA 环境使用 `../docker-build.qa.bat` 构建/更新容器；生产联网模式用 `../docker-build.sh`；生产离线模式用 `../docker-build.offline.sh`。如需调整构建参数，应修改现有脚本而非新建。
- 理由：容器名统一为 `agentinsight-docbot-<service>-1`（如 `agentinsight-docbot-agent-docbot-1`），不携带 `-docbot` 后缀；项目独立运行，无共享命名空间需求。

## 13. 测试规则

**测试分层（按执行环境）**：

| 类型 | 执行环境 | 目录 | 触发时机 |
|------|---------|------|---------|
| 单元测试 | 本地 / 构建期 | `tests/unit/` | 每次 commit、Docker build 阶段 |
| 功能测试 | 部署后容器栈 | `tests/functional/` | 容器栈健康后 |
| 回归测试 | 部署后容器栈 | `tests/regression/` | 合并 main 前 |
| API 测试 | 部署后容器栈 | `tests/api/` | 容器栈健康后 |
| 端到端测试 | 部署后容器栈 | `tests/e2e/` | 合并 main 前、发布前 |

**核心约定（优先选择）**：
- 单元测试在构建期执行（Docker build 或 CI build job），不应依赖外部服务（Postgres/Qdrant/Redis/LLM/Git）。
- 功能/回归/API/e2e 测试应在 `docker compose up -d` 且全部容器 `service_healthy` 后执行，不推荐本地直连或 mock 绕过。
- 测试目标地址从环境变量 `AGENT_URL` 注入（默认 `http://agent-docbot:8068`），不推荐硬编码。
- 测试用例应独立可重复运行，不应依赖执行顺序；用例间通过 fixture 清理状态。
- 测试数据隔离：Qdrant 用 `namespace=test_docbot_{user_id}:{repo_id}` + `user_id=test_docbot_*`，会话用 `session_id=test_docbot_*`，代码仓库用 `repo_id=test_docbot_*`，测试结束清理；不推荐污染生产集合（数据隔离属第 11 章安全硬约束）。
- e2e 应覆盖完整链路（通过 API 调用，**不依赖前端测试页面**——前端 UI 已划归 `../agentinsight-demo`，本仓库 e2e 仅验证后端 API 行为）：调用 `/v1/repos` 配置仓库 → 调用 `/v1/chat/completions` 一键生成 → 验证 SSE 进度 → 调用 `/v1/reports/{id}/download` 验证报告下载 → 切换 `session_id` 验证会话隔离。
- API 测试应覆盖：OpenAI 兼容端点（`/v1/chat/completions` 流式 SSE + 非流式 + 错误码）、`/v1/repos` CRUD + 测试 + 同步、`/v1/reports/{id}/download` 5 种格式、`/v1/sessions` 会话管理；并包含携带 Bearer JWT Token 与不携带两种场景（验证第 8 章身份解析与数据隔离）。
- **API 测试应包含端点不存在校验（核心约定）**：验证 `POST /v1/feedback` 返回 404 / 405、`WS /v1/ws/{session_id}` 返回 404 / 405、`GET/POST/PUT/DELETE /v1/mcp/configs` 返回 404，确保未误引入对应路由。
- 回归测试为合并门禁，不推荐跳过或 `@skip`。

**关键测试用例（核心约定，优先选择）**：
1. **单元测试**：`DOCBOT_REPORT_PERSONAS` 8 种 persona 完整性（含 `outline_file` 字段）/ 8 种大纲文件存在性（`test_outlines.py` 校验 `docs/*_OUTLINE.md` 存在）/ `GitMCPAdapter` 各平台 URL 解析 / AES-GCM 加密解密往返 / `coordinator_a` 派发逻辑（mock 子图）+ `language` 校验（仅 zh/en）/ D-E 修订循环守卫 / Redis 缓存键管理 / Qdrant namespace 多仓库隔离（含 `repo_id`）
2. **功能测试**：端到端克隆 + 索引 + 检索（小仓库，验证 `namespace={agent_id}:{user_id}:{repo_id}` 写入）/ 8 种文档类型各生成一份（mock LLM）/ 多报告并发派发（3 个 B 子图）/ D-E 修订循环（3 轮）
3. **API 测试**：`/v1/repos` CRUD + 测试 + 同步 / `/v1/chat/completions` 一键生成 SSE 流式 / `/v1/reports/{id}/download` 5 种格式 / 敏感字段不返回原文 / 端点不存在校验（`/v1/feedback`、`/v1/ws/{session_id}`、`/v1/mcp/configs` 均返回 404/405）
4. **e2e 测试**：调用 `/v1/repos` 配置仓库 → 调用 `/v1/chat/completions` 一键生成 → 验证 SSE 进度 → 调用 `/v1/reports/{id}/download` 验证报告下载 → 切换 `session_id` 验证隔离

**CI 流水线顺序（核心约定，优先选择）**：
1. 构建镜像 + 单元测试（失败即终止）
2. `docker compose up -d` + 等待全部健康检查通过
3. 功能测试 → API 测试 → 回归测试 → e2e 测试（按序，前者失败后者不执行）
4. 任一环节失败阻断合并；全部通过后 `docker compose down -v` 清理

**不推荐（选用需说明理由并等待用户确认）**：
- 在部署前跑功能/API/e2e 测试（无目标服务，结果不可信）。
- 测试用例跨用例共享可变状态（破坏独立性）。
- 用生产数据集做 e2e 测试（属第 11 章 PII 安全硬约束）。
- 用真实大仓库做测试（应使用 mock 仓库或小仓库，避免测试时间过长）。
- 跳过回归测试合并代码（破坏门禁保证）。
- 在本仓库内引入前端 E2E 框架（如 Playwright/Cypress）测试前端 UI——前端测试已划归 `../agentinsight-demo`，本仓库 e2e 仅验证后端 API。

## 14. 配套文档

- [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md)：架构文档（顶层设计、目录结构、多智能体编排、数据库设计、LLM 网关、RAG、MCP、API、部署、安全合规、性能容量、测试策略）
- [docs/DESIGN_AGENT.md](./docs/DESIGN_AGENT.md)：智能体详细设计文档（代码级，State schema、节点函数、守卫路由、图构建器、7 个子智能体业务逻辑、缓存管理、8 种 persona 字典、8 种默认大纲加载器、提示词模板、Settings 扩展、GitMCPAdapter、`/v1/repos` API、init.sql 追加 DDL、server.py 含系统 MCP 子进程启动、Dockerfile、docker-compose.yml、测试用例骨架）
- 8 种文档默认大纲（运行时按需加载，详见第 7 章）：
  - [docs/ARCHITECTURE_OUTLINE.md](./docs/ARCHITECTURE_OUTLINE.md)：技术架构文档
  - [docs/HLD_OUTLINE.md](./docs/HLD_OUTLINE.md)：概要设计文档
  - [docs/PRD_OUTLINE.md](./docs/PRD_OUTLINE.md)：需求文档
  - [docs/TEST_CASE_OUTLINE.md](./docs/TEST_CASE_OUTLINE.md)：测试用例文档
  - [docs/OPTIMIZATION_OUTLINE.md](./docs/OPTIMIZATION_OUTLINE.md)：系统优化文档
  - [docs/PERF_ANALYSIS_OUTLINE.md](./docs/PERF_ANALYSIS_OUTLINE.md)：性能分析文档
  - [docs/DEFECT_OUTLINE.md](./docs/DEFECT_OUTLINE.md)：系统缺陷文档
  - [docs/API_DOC_OUTLINE.md](./docs/API_DOC_OUTLINE.md)：API 文档

> **历史前端文档说明**：`docs/DESIGN_FRONTEND.md` 为历史遗留前端设计文档，前端职责已划归独立的演示平台 `../agentinsight-demo`，该文档不再作为本仓库的实现依据，仅供历史参考。如需查看当前前端实现规范，请参阅 `../agentinsight-demo/AGENTS.md`。

## 15. 参见

- [../AGENTS.md](../AGENTS.md)：主目录 AGENTS.md，包含跨子项目通用约定（技术栈选型、目录结构、三级行为边界、Agent 编排、会话与上下文管理、数据隔离、用户身份解析、工具与模型网关、可观测性、安全合规红线、部署规则、测试规则、前端测试页面规则等），本仓库规则为其补充与差异说明，冲突时以主目录为准。
- [../agentinsight-demo/AGENTS.md](../agentinsight-demo/AGENTS.md)：演示平台 AGENTS.md，承担本智能体的所有前端 UI 实现（仓库配置面板、报告类型选择、SSE 进度展示、报告下载、会话切换等），本智能体通过 OpenAI 兼容 API 供其调用。
- [../agentinsight-researcher/AGENTS.md](../agentinsight-researcher/AGENTS.md)：姊妹项目 agentinsight-researcher（AIR）AGENTS.md，本仓库的 `common/` / `rag/` / `llm/` / `memory/` / `observability/` / 部分 `api/` 与 `skills/researcher/` 模块源自 AIR 拷贝，在本仓库内独立演进。

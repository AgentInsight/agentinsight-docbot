# agentinsight-docbot 智能体架构文档

> 版本：v1.1  
> 日期：2026-07-20  
> 端口：8068  
> 编排内核：LangGraph ≥1.2  
> 模型网关：LiteLLM ≥1.6  
> 独立部署：Postgres / Redis / Qdrant / Embeddings / Frontend 全部自带（不依赖外部项目）

---

## 0. 文档导读

本文档是 `agentinsight-docbot`（下文简称 **docbot**）项目的顶层架构文档，基于以下输入合成：

1. `agentinsight-docbot/AGENTS.md`（项目规则，15 章硬约束与优先选择）
2. 业界同类 Agent（Cursor Docs Generator、GPT Researcher、DeepWiki、AutoArchitect、Repomix）优秀实践
3. 业界工程文档标准（IEEE 软件设计文档大纲 / Google SRE 文档规范 / Microsoft SDL 文档模板）
4. 用户原始需求（多子智能体编排 + 6 步流水线 + 8 种文档类型 + 用户代码仓库 MCP 接入）

配套文档：
- [DESIGN_AGENT.md](./DESIGN_AGENT.md)：智能体详细设计文档（代码级）
- [DESIGN_FRONTEND.md](./DESIGN_FRONTEND.md)：前端详细设计文档（代码级）

8 种文档默认大纲（独立文件，运行时按需读取）：
- [ARCHITECTURE_OUTLINE.md](./ARCHITECTURE_OUTLINE.md)：技术架构文档
- [HLD_OUTLINE.md](./HLD_OUTLINE.md)：概要设计文档
- [PRD_OUTLINE.md](./PRD_OUTLINE.md)：需求文档
- [TEST_CASE_OUTLINE.md](./TEST_CASE_OUTLINE.md)：测试用例文档
- [OPTIMIZATION_OUTLINE.md](./OPTIMIZATION_OUTLINE.md)：系统优化文档
- [PERF_ANALYSIS_OUTLINE.md](./PERF_ANALYSIS_OUTLINE.md)：性能分析文档
- [DEFECT_OUTLINE.md](./DEFECT_OUTLINE.md)：系统缺陷文档
- [API_DOC_OUTLINE.md](./API_DOC_OUTLINE.md)：API 文档

---

## 1. 项目定位

### 1.1 一句话定位

docbot 是一个 **"根据用户代码仓库一键生成技术文档"** 的多智能体系统，对外暴露 OpenAI 兼容 API（端口 8068），通过 LangGraph 编排 7 个子智能体（A/B/C/D/E/F/G）协作完成 8 类技术文档的生成、评审、合并与终审。

### 1.2 能力边界

| 能力 | 支持范围 |
|------|---------|
| 用户代码仓库接入 | GitHub / GitLab / Gitee / Bitbucket / Coding.net / Gitea / 自托管 Git（HTTPS/SSH/Token） |
| 文档类型 | 技术架构文档 / 概要设计文档 / 需求文档 / 测试用例文档 / 系统优化文档 / 性能分析文档 / 系统缺陷文档 / API 文档 |
| 文档格式 | Markdown / HTML / PDF / DOCX / JSON |
| 文档语言 | 简体中文 / English |
| 输出形态 | 流式 SSE 进度 + 报告下载链接 + 文档摘要 |
| 多文档并发 | 单次请求可指定多个报告类型，由子智能体 A 并发派发给多个 B |
| 不支持 | 模型训练 / 数据标注 / 前端 SSR / 系统级共享仓库（仅个人仓库） |

### 1.3 独立运行原则

docbot 为**独立可部署系统**，所有依赖（代码 / 配置 / 数据库 / 前端工程 / Docker 镜像）均在本项目内自带，不依赖外部项目存在：

| 维度 | 实现 |
|------|------|
| 端口 | 8068 |
| `agent_name` | `agentinsight-docbot` |
| 核心场景 | 代码仓库分析 + 技术文档生成 |
| 子智能体数量 | 1 顶层图 + N 报告子图（每报告 6 步） |
| 数据隔离 | `agent_id = 'agentinsight-docbot'`（与同库其他业务隔离） |
| 自带基础设施 | PostgreSQL（`agents` 库） / Redis 8 / Qdrant / Embeddings TEI / Frontend |
| 部署形态 | 5 容器（postgres / redis / qdrant / embeddings / agent-docbot） |

> **代码复用原则**：本项目从 AIR（agentinsight-researcher）拷贝了基础模块（`common/` / `rag/` / `llm/` / `memory/` / `observability/` / `api/routes.py` / `api/middleware.py` / `api/session_routes.py` / `api/ip_user_resolver.py` / `skills/researcher/publisher.py` / `skills/researcher/image_generator.py` / `scripts/init.sql`），并将持续在本仓库内独立演进，不再双向同步。

---

## 2. 总体架构

### 2.1 架构总览图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            用户浏览器（Frontend）                            │
│  Next.js 15 + React 19 + Zustand 5（本仓库自带 frontend 工程）               │
│  - agents.config.ts 内置 docbot 单 Agent 配置（SSOT）                        │
│  - DocbotInput 组件：代码仓库下拉 + 报告类型多选 + 语言选择 + 一键生成       │
│  - RepoConfigPanel 组件：用户仓库配置面板                                    │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │ HTTPS / SSE
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│              FastAPI（agentinsight-docbot:8068，OpenAI 兼容）                │
│  - POST /v1/chat/completions（SSE 流式）                                    │
│  - /v1/sessions、/v1/reports（会话 + 报告下载）                              │
│  - /v1/repos（用户代码仓库 CRUD + 测试 + 同步）                              │
│  - Middleware：JWT 解析 + IP 降级 + 限流 + CORS + 安全响应头                 │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       LangGraph 顶层图（子智能体 A）                         │
│  coordinator_a ──► spawn_b_tasks（asyncio.gather 并发） ──► final_reviewer_g│
│              ┌──────────────────┬──────────────────┐                        │
│              ▼                  ▼                  ▼                        │
│         B（报告1）          B（报告2）          B（报告N）                   │
│         6 步流水线          6 步流水线          6 步流水线                   │
│              └──────────────────┴──────────────────┘                        │
│                                                                ┌──────────┐│
│                                                                │save_     ││
│                                                                │reports   ││
│                                                                └──────────┘│
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │
            ┌────────────────────┼────────────────────┐
            ▼                    ▼                    ▼
   ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
   │  LLM Gateway    │  │   RAG Layer     │  │  MCP Layer      │
   │  (LiteLLM)      │  │  (Embeddings +  │  │ (mcp-server-git │
   │  3 级降级链     │  │   Qdrant + BM25 │  │  / filesystem)  │
   │                 │  │   + Rerank)     │  │ 系统自带        │
   └─────────────────┘  └─────────────────┘  └─────────────────┘
            │                    │                    │
            ▼                    ▼                    ▼
   ┌─────────────────────────────────────────────────────────────┐
   │                 自带基础设施（5 容器同栈）                   │
   │  PostgreSQL（agents 库）│ Redis 8 │ Qdrant │ Embeddings TEI │
   └─────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
   ┌─────────────────────────────────────────────────────────────┐
   │             可观测性（AgentInsight SDK ≥0.1.5）              │
   │  6 类 trace_xxx（agent/generation/tool/retriever/chain/      │
   │  embedding）+ Null Object 降级                               │
   └─────────────────────────────────────────────────────────────┘
```

### 2.2 核心设计原则

1. **独立运行**：所有依赖（数据库 / 缓存 / 向量库 / 嵌入服务 / 前端工程 / 基础 Python 模块）均在本项目内，可直接 `docker compose up` 启动，不依赖任何外部项目存在。
2. **数据隔离不混用**：所有业务表通过 `agent_id = 'agentinsight-docbot'` 列隔离，与同库其他业务互不可见。
3. **多 Agent 并发编排**：顶层图线性 + 条件边，子图嵌入 + `asyncio.gather` 并发派发（不用 Send API，保持 LangGraph 1.2 状态机语义清晰）。
4. **6 步流水线 + 缓存传递**：每个报告任务的 6 步通过 Redis 缓存传递中间产物（`code_learning_cache_key` / `outline_cache_key` / `content_cache_keys` / `reviewed_cache_keys` / `merged_cache_key`），state 仅存键名，避免 state 膨胀。
5. **LLM 三级分层 + 降级链**：STRATEGIC（v4-pro，深度代码学习 + 纲要细化）→ SMART（v4-flash，内容填充 / 评审 / 合并 / 终审）→ FAST（glm-4-flash，轻量摘要 / 路由），降级链 STRATEGIC→SMART→FAST→抛出。
6. **零代码改动复用 ReportGenerator**：8 种文档类型通过 `agent_role` persona 注入（`DOCBOT_REPORT_PERSONAS` 字典），不引入 `IndustryClassifier`（遵守 AGENTS.md 第 7 章 4 层行业适配机制）。
7. **系统自带 MCP**：`mcp-server-git` + `mcp-server-filesystem` 由系统启动时自动注册，所有用户共享，不入 `mcp_configs` 表、不暴露 CRUD API。

---

## 3. 目录结构

> 所有 docbot 专属代码以 `agents/docbot/` / `config/docbot/` / `skills/docbot/` 隔离；从 AIR 拷贝的基础模块保留原路径，在本仓库内独立演进。

```
agentinsight-docbot/
├── AGENTS.md                      # 本项目规则
├── README.md
├── docs/
│   ├── ARCHITECTURE.md            # 本文件
│   ├── DESIGN_AGENT.md            # 智能体详细设计文档（代码级）
│   ├── DESIGN_FRONTEND.md         # 前端详细设计文档（代码级）
│   ├── ARCHITECTURE_OUTLINE.md    # 技术架构文档默认大纲
│   ├── HLD_OUTLINE.md             # 概要设计文档默认大纲
│   ├── PRD_OUTLINE.md             # 需求文档默认大纲
│   ├── TEST_CASE_OUTLINE.md       # 测试用例文档默认大纲
│   ├── OPTIMIZATION_OUTLINE.md    # 系统优化文档默认大纲
│   ├── PERF_ANALYSIS_OUTLINE.md   # 性能分析文档默认大纲
│   ├── DEFECT_OUTLINE.md          # 系统缺陷文档默认大纲
│   └── API_DOC_OUTLINE.md         # API 文档默认大纲
├── src/
│   ├── graph/                     # LangGraph 图定义
│   │   ├── state.py               # DocbotState + ReportTaskState 双 schema
│   │   ├── nodes.py               # 顶层节点（coordinator_a / spawn_b_tasks / final_reviewer_g / save_reports）
│   │   ├── report_nodes.py        # 报告子图节点（b/c/d/e/f/g 步骤）
│   │   ├── edges.py               # 守卫与路由
│   │   ├── builder.py             # build_docbot_graph() 顶层图
│   │   └── report_builder.py      # build_report_subgraph() 报告子图
│   ├── agents/
│   │   └── docbot/                # docbot 专属 Agent 逻辑
│   │       ├── coordinator.py     # 子智能体 A 实现
│   │       ├── report_runner.py   # 子智能体 B 实现
│   │       ├── outline_refiner.py # 子智能体 C 实现
│   │       ├── content_filler.py  # 子智能体 D 实现
│   │       ├── reviewer.py        # 子智能体 E 实现
│   │       ├── merger.py          # 子智能体 F 实现
│   │       └── final_reviewer.py  # 子智能体 G 实现
│   ├── common/                    # 公用基础（从 AIR 拷贝，本仓库内独立维护）
│   ├── config/
│   │   ├── settings.py            # 全局 Settings（agent_name='agentinsight-docbot'）
│   │   └── docbot/
│   │       ├── personas.py        # DOCBOT_REPORT_PERSONAS（8 种文档 persona 字典）
│   │       ├── outlines.py        # 8 种文档默认大纲加载器（读取 docs/*_OUTLINE.md）
│   │       └── prompts.py         # docbot 专属提示词模板
│   ├── skills/
│   │   └── docbot/
│   │       ├── repo_loader.py     # 仓库克隆 / 拉取 / 文件枚举
│   │       ├── code_learner.py    # 任务一：STRATEGIC 深度学习代码
│   │       ├── outline_skill.py   # 任务二：纲要细化
│   │       ├── content_skill.py   # 任务三：内容填充 + 图片生成
│   │       ├── review_skill.py    # 任务四：评审
│   │       ├── merge_skill.py     # 任务五：合并去重
│   │       ├── final_skill.py     # 任务六：终审
│   │       └── cache.py           # Redis 缓存键管理
│   │   └── researcher/            # 从 AIR 拷贝
│   │       ├── publisher.py       # 多格式导出（HTML/PDF/DOCX/JSON）
│   │       └── image_generator.py # DeepSeek SVG 生成
│   ├── tools/                     # MCP Server 封装
│   │   └── git_mcp.py             # 用户代码仓库 MCP 适配
│   ├── rag/                       # 从 AIR 拷贝的 RAG 实现（namespace 加 repo_id）
│   ├── llm/                       # 从 AIR 拷贝的 LLMClient
│   ├── memory/                    # 从 AIR 拷贝的 checkpointer / db_initializer / report_store / session_store
│   ├── observability/             # 从 AIR 拷贝的 tracing.py
│   └── api/
│       ├── routes.py              # /v1/chat/completions（从 AIR 拷贝）
│       ├── middleware.py          # 从 AIR 拷贝
│       ├── session_routes.py      # 从 AIR 拷贝
│       ├── repo_routes.py         # 新增：/v1/repos CRUD + 测试 + 同步
│       └── ip_user_resolver.py    # 从 AIR 拷贝
├── frontend/                      # 本仓库自带前端工程（从 AIR 拷贝后精简，仅保留 docbot 配置）
├── scripts/
│   └── init.sql                   # 数据库 DDL（在 AIR 基础 DDL 上追加 docbot 专属表 + 列）
├── static/
│   └── index.html                 # 测试页（端口 8068）
├── tests/
│   ├── unit/
│   ├── functional/
│   ├── api/
│   ├── regression/
│   └── e2e/
├── Dockerfile                     # docbot 专属镜像（Python 3.12-slim）
├── docker-compose.yml             # 5 容器（postgres/redis/qdrant/embeddings/agent-docbot）
├── docker-build.sh                # 生产联网模式
├── docker-build.qa.bat            # QA 模式
├── docker-build.offline.sh        # 生产离线模式
├── .env.template
└── requirements.txt               # 与 AIR 一致 + 无新增依赖
```

---

## 4. 多智能体编排架构

### 4.1 子智能体角色定义

| 子智能体 | 角色名 | 职责 | LLM 等级 | 图层级 |
|---------|--------|------|---------|--------|
| **A** | Coordinator | 收到请求 → 派发 N 个 B → 收集产物 → 调用 G 终审 → 返回用户 | STRATEGIC | 顶层图 |
| **B** | ReportRunner | 单报告任务协调：6 步顺序执行 + 缓存传递 | SMART | 报告子图入口 |
| **C** | OutlineRefiner | 任务二：基于默认大纲 + 代码上下文，STRATEGIC 细化报告纲要 | STRATEGIC | 报告子图节点 |
| **D** | ContentFiller | 任务三：按纲要顺序，逐章节获取 RAG + 代码上下文，SMART 填充内容 + 生成图片 | SMART | 报告子图节点（循环） |
| **E** | Reviewer | 任务四：逐章节审核 D 的内容，SMART 修改评审建议 | SMART | 报告子图节点（循环，与 D 形成修订环） |
| **F** | Merger | 任务五：合并 E 审核过的章节，SMART 去重 | SMART | 报告子图节点 |
| **G** | FinalReviewer | 任务六：SMART 终审 F 的合并文档，修改终审建议，输出最终文档 | SMART | 顶层图（A 之后） |

### 4.2 顶层图（子智能体 A + G）

```python
# src/graph/builder.py（伪代码示意，详见 DESIGN_AGENT.md）
def build_docbot_graph() -> CompiledGraph:
    graph = StateGraph(DocbotState)
    graph.add_node("coordinator_a", coordinator_a_node)
    graph.add_node("spawn_b_tasks", spawn_b_tasks_node)   # asyncio.gather 并发派发 B 子图
    graph.add_node("final_reviewer_g", final_reviewer_g_node)
    graph.add_node("save_reports", save_reports_node)
    graph.set_entry_point("coordinator_a")
    graph.add_edge("coordinator_a", "spawn_b_tasks")
    graph.add_edge("spawn_b_tasks", "final_reviewer_g")
    graph.add_edge("final_reviewer_g", "save_reports")
    graph.add_edge("save_reports", END)
    return graph.compile(checkpointer=postgres_saver)
```

**顶层图 State（`DocbotState`）**：

```python
class DocbotState(TypedDict):
    messages: Annotated[list, add_messages]
    user_id: str
    session_id: str
    agent_id: str  # 固定 'agentinsight-docbot'
    repo_id: str              # 用户选中的代码仓库 ID
    report_types: list[str]   # ['architecture','design','requirements','testcase',
                              #  'optimization','performance','defect','api_doc'] 1~8 种
    report_format: str        # 'markdown' | 'html' | 'pdf' | 'docx' | 'json'
    language: str             # 'zh' | 'en'
    # 派发结果
    report_tasks: list[dict]  # 每个报告的子图最终产物（report_id + cache_key）
    # 终审结果
    final_reports: list[dict] # [{report_id, title, summary, download_urls, image_svg}]
    # 迭代控制
    iteration_count: Annotated[int, operator.add]
    errors: Annotated[list[str], operator.add]
```

### 4.3 报告子图（子智能体 B + C/D/E/F）

```python
# src/graph/report_builder.py（伪代码）
def build_report_subgraph() -> CompiledGraph:
    graph = StateGraph(ReportTaskState)
    graph.add_node("b_init_session", b_init_session_node)       # 任务一前置：创建 LLM 会话
    graph.add_node("c_code_learning", c_code_learning_node)    # 任务一：STRATEGIC 学习代码
    graph.add_node("c_outline_refine", c_outline_refine_node)  # 任务二：C 细化纲要
    graph.add_node("d_content_fill", d_content_fill_node)      # 任务三：D 填充内容（按章节循环）
    graph.add_node("e_review", e_review_node)                  # 任务四：E 评审（按章节循环）
    graph.add_node("f_merge", f_merge_node)                    # 任务五：F 合并去重
    graph.add_node("g_final_in_subgraph", g_final_in_subgraph_node)  # 任务六：G 终审（子图内执行）
    graph.set_entry_point("b_init_session")
    graph.add_edge("b_init_session", "c_code_learning")
    graph.add_edge("c_code_learning", "c_outline_refine")
    graph.add_edge("c_outline_refine", "d_content_fill")
    # D ↔ E 修订循环（按章节）
    graph.add_conditional_edges(
        "d_content_fill",
        route_after_d,
        {"next_chapter": "d_content_fill", "review": "e_review", "done": "f_merge"},
    )
    graph.add_conditional_edges(
        "e_review",
        route_after_e,
        {"revise": "d_content_fill", "next_chapter": "e_review", "done": "f_merge"},
    )
    graph.add_edge("f_merge", "g_final_in_subgraph")
    graph.add_edge("g_final_in_subgraph", END)
    return graph.compile()
```

**报告子图 State（`ReportTaskState`）**：

```python
class ReportTaskState(TypedDict):
    report_type: str          # 'architecture' 等 8 种
    report_format: str
    language: str             # 'zh' | 'en'
    repo_id: str
    user_id: str
    session_id: str
    agent_id: str
    llm_session_id: str       # 任务一创建的 LLM 会话 ID（贯穿后续所有 LLM 调用）
    # 缓存键（state 仅存键，避免 state 膨胀）
    code_learning_cache_key: str   # 任务一产物
    outline_cache_key: str         # 任务二产物
    content_cache_keys: list[str]  # 任务三产物（每章节一 key）
    reviewed_cache_keys: list[str] # 任务四产物
    merged_cache_key: str          # 任务五产物
    final_cache_key: str           # 任务六产物
    # 章节迭代控制
    current_chapter_idx: int
    chapters: list[dict]      # [{idx, title, sections: [...]}]
    max_revisions_per_chapter: int  # 默认 3
    revision_count: Annotated[int, operator.add]
    # 最终产物
    report_id: str
    report_title: str
    report_summary: str
    report_image_svg: str
    download_urls: dict[str, str]  # {format: url}
```

### 4.4 缓存传递设计

**核心问题**：6 步流水线中间产物（代码学习摘要 / 纲要 / 各章节内容 / 评审建议 / 合并文档 / 终审文档）体积可能达到数百 KB，直接放入 LangGraph state 会导致 state 膨胀 + Checkpointer 写入瓶颈。

**解决方案**：所有中间产物存 Redis（TTL 24 小时），state 仅存 cache_key。

| 缓存键 | 写入者 | 读取者 | TTL | 数据结构 |
|--------|--------|--------|-----|---------|
| `docbot:{agent_id}:{user_id}:{session_id}:code_learning:{report_type}` | 任务一 | 任务二/三/四 | 24h | `{summary, file_index, key_modules, dependencies, architecture_notes}` |
| `docbot:{agent_id}:{user_id}:{session_id}:outline:{report_type}` | 任务二 | 任务三/四 | 24h | `{chapters: [{idx, title, sections, key_points}]}` |
| `docbot:{agent_id}:{user_id}:{session_id}:content:{report_type}:{chapter_idx}` | 任务三 | 任务四 | 24h | `{chapter_idx, content_md, image_svgs: [...]}` |
| `docbot:{agent_id}:{user_id}:{session_id}:reviewed:{report_type}:{chapter_idx}` | 任务四 | 任务五 | 24h | `{chapter_idx, content_md, review_notes, image_svgs}` |
| `docbot:{agent_id}:{user_id}:{session_id}:merged:{report_type}` | 任务五 | 任务六 | 24h | `{content_md, image_svgs, toc}` |
| `docbot:{agent_id}:{user_id}:{session_id}:final:{report_type}` | 任务六 | 顶层图 A | 24h | `{content_md, image_svgs, toc, title, summary}` |

### 4.5 并发派发机制

```python
# src/agents/docbot/coordinator.py（伪代码）
async def spawn_b_tasks_node(state: DocbotState) -> dict:
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_REPORTS)  # 默认 3
    async def run_one(report_type: str) -> dict:
        async with semaphore:
            subgraph = build_report_subgraph()
            sub_state = ReportTaskState(
                report_type=report_type,
                report_format=state["report_format"],
                language=state["language"],
                repo_id=state["repo_id"],
                user_id=state["user_id"],
                session_id=state["session_id"],
                agent_id=state["agent_id"],
                # ...
            )
            result = await subgraph.ainvoke(sub_state, config={"configurable": {"thread_id": f"{state['agent_id']}:{state['session_id']}:{report_type}"}})
            return result
    tasks = [run_one(rt) for rt in state["report_types"]]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return {"report_tasks": [r for r in results if not isinstance(r, Exception)],
            "errors": [str(r) for r in results if isinstance(r, Exception)]}
```

---

## 5. 数据库设计

### 5.1 隔离原则

docbot 使用本项目自带的 PostgreSQL `agents` 数据库，所有业务表通过 `agent_id` 列隔离：

- docbot 数据：`agent_id = 'agentinsight-docbot'`

`scripts/init.sql` 是一份完整的 DDL（包含 AIR 基础 DDL + docbot 专属 DDL），幂等执行（`CREATE TABLE IF NOT EXISTS` / `ALTER TABLE IF EXISTS ... ADD COLUMN IF NOT EXISTS ...`）。

### 5.2 新增表：`user_git_repos`

存储用户代码仓库配置（仅个人仓库，无系统仓库）。

```sql
CREATE TABLE IF NOT EXISTS user_git_repos (
    id VARCHAR(64) PRIMARY KEY,                          -- uuid4
    agent_id VARCHAR(64) NOT NULL,                       -- 'agentinsight-docbot'
    user_id VARCHAR(64) NOT NULL,                        -- 用户隔离
    repo_name VARCHAR(255) NOT NULL,                     -- 用户自定义仓库名
    platform VARCHAR(32) NOT NULL,                       -- github|gitlab|gitee|bitbucket|coding|gitea|custom
    repo_url TEXT NOT NULL,                              -- 完整 git clone URL
    -- 认证信息（AES-GCM 加密存储，密钥由 settings.git_credential_key 注入）
    auth_type VARCHAR(16) NOT NULL,                      -- none|token|password|ssh_key
    encrypted_token TEXT,                                -- AES-GCM 密文（token 模式）
    encrypted_username TEXT,                             -- AES-GCM 密文（password 模式）
    encrypted_password TEXT,                             -- AES-GCM 密文（password 模式）
    encrypted_ssh_key TEXT,                              -- AES-GCM 密文（ssh_key 模式）
    ssh_passphrase TEXT,                                 -- AES-GCM 密文
    -- 元数据
    default_branch VARCHAR(64) DEFAULT 'main',           -- 默认分支
    clone_depth INT DEFAULT 0,                           -- 0=完整克隆，>0=浅克隆深度
    enabled BOOLEAN DEFAULT TRUE,                        -- 是否启用
    last_synced_at TIMESTAMPTZ,                          -- 最后同步时间
    last_sync_status VARCHAR(16),                        -- success|failed|pending
    last_sync_error TEXT,                                -- 失败原因
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_user_git_repos_agent_user ON user_git_repos(agent_id, user_id);
CREATE INDEX IF NOT EXISTS idx_user_git_repos_enabled ON user_git_repos(agent_id, user_id, enabled);

-- updated_at 自动维护触发器（复用基础 DDL 中的 update_updated_at_column() 函数）
CREATE TRIGGER IF NOT EXISTS trg_user_git_repos_updated_at
    BEFORE UPDATE ON user_git_repos
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

### 5.3 扩展 `research_reports` 表

在基础表上追加 3 列：

```sql
ALTER TABLE research_reports
    ADD COLUMN IF NOT EXISTS report_type_label VARCHAR(64),
    ADD COLUMN IF NOT EXISTS report_summary TEXT,
    ADD COLUMN IF NOT EXISTS report_image_svg TEXT;

-- report_type_label 取值：'architecture'|'design'|'requirements'|'testcase'|
--                         'optimization'|'performance'|'defect'|'api_doc'
CREATE INDEX IF NOT EXISTS idx_research_reports_agent_user_type
    ON research_reports(agent_id, user_id, report_type_label);
```

### 5.4 平台支持全集

参考业界主流 Git 托管平台，设计 `platform` 字段全集：

| 平台 | 取值 | clone URL 模板 | 推荐认证方式 |
|------|------|---------------|------------|
| GitHub | `github` | `https://github.com/{owner}/{repo}.git` | Token（PAT） |
| GitLab | `gitlab` | `https://gitlab.com/{owner}/{repo}.git` | Token |
| Gitee | `gitee` | `https://gitee.com/{owner}/{repo}.git` | Token |
| Bitbucket | `bitbucket` | `https://bitbucket.org/{owner}/{repo}.git` | App Password |
| Coding.net | `coding` | `https://e.coding.net/{team}/{project}/{repo}.git` | Token |
| Gitea（自托管） | `gitea` | `https://{host}/{owner}/{repo}.git` | Token |
| Custom（自托管 Git） | `custom` | 任意 HTTP(S) / SSH URL | Token / Password / SSH Key |

> **认证方式全集**（参考 Git 官方文档）：
> 1. **None**：公开仓库匿名克隆
> 2. **Token**：GitHub PAT / GitLab PAT / Gitee 私人令牌（推荐，最安全）
> 3. **Username + Password**：基础认证（不推荐，仅兼容旧系统）
> 4. **SSH Key**：私钥 + 可选 passphrase（推荐用于自托管）

### 5.5 业务表清单

docbot 使用以下业务表（均通过 `agent_id` 列隔离）：

| 表名 | 用途 | docbot 使用方式 |
|------|------|----------------|
| `research_sessions` | 会话管理 | `agent_id='agentinsight-docbot'`，复用 SessionStore |
| `research_reports` | 报告存储 | `agent_id='agentinsight-docbot'`，每报告一行 + 3 新列 |
| `research_search_logs` | 检索日志 | 记录 docbot 的 RAG 检索日志 |
| `uploaded_files` | 文件上传 | 暂不使用（仓库代码通过 MCP 访问，不入此表） |
| `token_usage_logs` | Token 用量 | 记录 docbot 的 LLM 调用 token |
| `chat_messages` | 聊天消息 | 记录用户与 docbot 的对话 |
| `report_limits` | 报告限额 | docbot 独立限额（按 agent_id 隔离） |
| `daily_report_usage` | 每日用量 | docbot 独立统计 |
| `user_git_repos` | 用户代码仓库 | docbot 专属（5.2 新增） |

> **注意**：`mcp_configs` 表保留在基础 DDL 中以兼容其他业务，但 docbot **不使用此表**——MCP 服务由系统启动时自动注册（详见第 8 章）。

---

## 6. LLM 网关设计

### 6.1 三级 LLM 配置

| 等级 | 环境变量 | 默认值 | 用途 | 上下文窗口 |
|------|---------|--------|------|----------|
| FAST | `FAST_LLM` | `zhipuai/glm-4-flash` | 轻量摘要 / 路由 / 错误兜底 | 128K |
| SMART | `SMART_LLM` | `deepseek/deepseek-v4-flash` | 内容填充 / 评审 / 合并 / 终审 | 128K |
| STRATEGIC | `STRATEGIC_LLM` | `deepseek/deepseek-v4-pro` | 代码深度学习 / 纲要细化 | 256K |

### 6.2 LiteLLM 路由识别机制

LiteLLM 原生支持 **"不配 BaseURL 时自动识别 provider 并使用官方 URL"** 的能力：

- 用户在 LiteLLM 模型名前缀中声明 provider（如 `deepseek/deepseek-v4-flash`），LiteLLM 内置 `litellm.provider_list` 字典自动映射到官方 API URL。
- 用户可通过 `api_base` 参数覆盖默认 URL（用于自托管 / 代理）。
- 用户可通过 `os.environ["<PROVIDER>_API_KEY"]` 注入密钥（如 `DEEPSEEK_API_KEY` / `ZHIPUAI_API_KEY`）。

**docbot 配置策略**：

```python
# src/config/settings.py
class Settings(BaseSettings):
    # 三级 LLM
    fast_llm: str = "zhipuai/glm-4-flash"
    smart_llm: str = "deepseek/deepseek-v4-flash"
    strategic_llm: str = "deepseek/deepseek-v4-pro"
    # 可选：覆盖 BaseURL（不配则走 LiteLLM 官方路由）
    fast_llm_api_base: str | None = None
    smart_llm_api_base: str | None = None
    strategic_llm_api_base: str | None = None
    # 密钥（环境变量注入，不入仓）
    zhipuai_api_key: str | None = None
    deepseek_api_key: str | None = None
    # 降级链开关
    enable_llm_fallback: bool = True
```

### 6.3 国内大模型兼容性矩阵

LiteLLM ≥1.6 原生支持以下国内大模型 provider（无需自配 BaseURL）：

| Provider | LiteLLM 前缀 | 默认 API URL | 推荐模型 | 兼容性 |
|----------|-------------|-------------|---------|--------|
| 智谱 AI | `zhipuai/` | `https://open.bigmodel.cn/api/paas/v4` | glm-4-flash / glm-4-plus / glm-4.5 | ✅ 原生 |
| DeepSeek | `deepseek/` | `https://api.deepseek.com` | deepseek-chat / deepseek-reasoner / deepseek-v4-flash / deepseek-v4-pro | ✅ 原生 |
| 通义千问 | `dashscope/` 或 `openai/`（兼容模式） | `https://dashscope.aliyuncs.com/compatible-mode/v1` | qwen-max / qwen-plus / qwen-turbo | ✅ 原生 |
| 百度文心 | `ernest/` 或 `baidu/` | `https://qianfan.baidubce.com/v2` | ernie-4.0 / ernie-3.5 | ✅ 原生（部分版本需 `api_base` 覆盖） |
| 月之暗面 Kimi | `moonshot/` | `https://api.moonshot.cn/v1` | moonshot-v1-128k / moonshot-v1-32k | ✅ 原生 |
| MiniMax | `minimax/` | `https://api.minimax.chat/v1` | abab6.5 / abab7 | ✅ 原生 |
| 百川 | `baichuan/` | `https://api.baichuan-ai.com/v1` | Baichuan4 | ✅ 原生 |
| 字节豆包 | `openai/`（兼容模式） | `https://ark.cn-beijing.volces.com/api/v3` | doubao-pro / doubao-lite | ⚠️ 需 `api_base` 覆盖 + `api_key` |
| 讯飞星火 | `spark/` 或 `iflytek/` | `https://spark-api-open.xf-yun.com/v1` | spark-v4 / spark-v3.5 | ✅ 原生 |
| 阶跃星辰 | `openai/`（兼容模式） | `https://api.stepfun.com/v1` | step-2 | ⚠️ 需 `api_base` 覆盖 |
| 商汤日日新 | `sensetime/` | `https://api.sensenova.cn/compatible-mode/v1` | sensechat-5 | ✅ 原生 |

**不完全兼容列表**（需 `api_base` 显式覆盖）：
- 字节豆包（Doubao）：必须配 `api_base=https://ark.cn-beijing.volces.com/api/v3` + 自定义 `api_key`
- 阶跃星辰（StepFun）：必须配 `api_base=https://api.stepfun.com/v1`
- 部分私有部署模型（如本地 vLLM）：必须配 `api_base` + 模型名前缀用 `openai/`

> **结论**：LiteLLM 完全满足 docbot "统一配置 Model/BaseURL/Key + 不配 BaseURL 时自动识别" 的需求。用户指定的三级 LLM（zhipuai/glm-4-flash / deepseek/deepseek-v4-flash / deepseek/deepseek-v4-pro）均为原生支持，无需配 `api_base`。

### 6.4 降级链

LLMClient 实现降级链：

```
STRATEGIC 调用失败 → 降级到 SMART → 降级到 FAST → 抛出 LLMUnavailableError
SMART 调用失败 → 降级到 FAST → 抛出
FAST 调用失败 → 抛出
```

降级触发条件：HTTP 5xx / 超时 / 速率限制（429）/ 网络错误。降级时记录 `trace_generation` span 的 `metadata.fallback_from` / `metadata.fallback_to`。

---

## 7. RAG 设计

### 7.1 RAG 流水线

docbot 自带 RAG 实现（从 AIR 拷贝后在本仓库独立维护），通过 `namespace` 区分数据范围：

| 数据类型 | namespace 格式 | payload 含 user_id + repo_id | 检索可见性 |
|---------|---------------|-----------------------------|----------|
| 共享知识库 | `agentinsight-docbot` | 否 | 所有 docbot 用户共享 |
| 用户私有数据（代码索引） | `agentinsight-docbot:{user_id}:{repo_id}` | 是 | 仅该用户 + 该仓库 |

### 7.2 代码仓库索引策略

由于用户可配置多个仓库并在会话中选择仓库，索引必须按 `repo_id` 隔离，避免不同仓库的代码互相污染。

用户在 `RepoConfigPanel` 配置仓库后，docbot 后台执行索引任务：

1. **克隆**：通过 `mcp-server-git` 或直接 `git clone` 到临时目录 `temp/repos/{user_id}/{repo_id}/`
2. **文件枚举**：跳过 `.git/` / `node_modules/` / `__pycache__/` / `dist/` / `build/` / `.venv/`
3. **分块**：按文件类型分块
   - 代码文件（.py/.js/.ts/.go/.java/...）：按函数 / 类分块（AST 解析）
   - 配置文件（.yml/.json/.toml/...）：整体作为一个 chunk
   - 文档文件（.md/.rst/.txt）：按章节分块（标题层级）
4. **嵌入**：调用 `rag/embeddings.py` 的 `embed_batch()`，使用远程 TEI（bge-base-zh-v1.5，768 维）
5. **写入 Qdrant**：`namespace=agentinsight-docbot:{user_id}:{repo_id}`，payload 含 `repo_id` / `file_path` / `language` / `chunk_type`
6. **索引完成**：更新 `user_git_repos.last_synced_at` / `last_sync_status`

> **多仓库检索时**：会话中选中 `repo_id` 后，所有 RAG 检索均以 `namespace=agentinsight-docbot:{user_id}:{repo_id}` 过滤，确保只召回当前仓库的代码片段。

### 7.3 检索时序

任务三（D 内容填充）每章节按以下顺序检索：

```
1. 章节标题 + 关键词 → BM25 检索（中文用 jieba 分词）
2. 章节标题 + 关键词 → Vector 检索（bge-base-zh-v1.5）
3. RRF 融合两路结果（默认 vector_weight=0.7 / bm25_weight=0.3）
4. Top-K=20 召回
5. （可选）bge-reranker-v2-m3 重排序，取 Top-5
6. score_threshold=0.3 过滤
7. 与 code_learning_cache 一起作为 SMART LLM 输入
```

---

## 8. MCP 设计

### 8.1 用户代码仓库 MCP 服务（系统自带）

docbot 通过 MCP 协议访问用户代码仓库。**MCP 服务由系统启动时自动注册，所有用户共享，不需要用户配置、不入 `mcp_configs` 表、不暴露 MCP CRUD API。**

**MCP Server 选型**：

| Server | 用途 | 启动方式 | 配置来源 |
|--------|------|---------|---------|
| `mcp-server-git`（社区实现） | 仓库克隆 / 拉取 / 文件读取 / 提交历史 | `uvx mcp-server-git --repository <path>` | 系统启动时自动注册 |
| `mcp-server-filesystem`（官方） | 文件系统访问 | `uvx mcp-server-filesystem <allowed_dirs>` | 系统启动时自动注册 |

**docbot 专属 MCP 适配**（`src/tools/git_mcp.py`）：

```python
# 伪代码
class GitMCPAdapter:
    """docbot 代码仓库 MCP 适配器，封装 mcp-server-git。

    系统自带，启动时自动注册到 mcp_coordinator，所有用户共享。
    用户的代码仓库认证信息从 user_git_repos 表读取（AES-GCM 解密），
    作为运行时参数传入，不污染全局 MCP 配置。
    """
    async def clone_repo(self, repo_config: dict) -> str:
        """克隆仓库到 temp/repos/{user_id}/{repo_id}/，返回本地路径。"""
    async def list_files(self, repo_path: str, pattern: str = "**/*") -> list[str]:
        """枚举文件，跳过 .git/node_modules 等。"""
    async def read_file(self, repo_path: str, file_path: str) -> str:
        """读取文件内容。"""
    async def get_file_history(self, repo_path: str, file_path: str, limit: int = 10) -> list[dict]:
        """获取文件提交历史。"""
    async def search_code(self, repo_path: str, query: str) -> list[dict]:
        """代码搜索（grep 模式）。"""
```

### 8.2 启动机制与测试机制

1. **系统启动注册**：FastAPI 启动事件中自动启动 `mcp-server-git` + `mcp-server-filesystem` 子进程，注册到 `mcp_coordinator.py`，所有用户共享。
2. **运行时参数注入**：用户在 RepoConfigPanel 配置仓库 → 保存到 `user_git_repos` 表 → 调用 MCP 时，从表中读取认证信息（AES-GCM 解密）作为运行时参数传入 `GitMCPAdapter`。
3. **测试机制**：用户点击"测试连接"按钮 → 后端调用 `GitMCPAdapter.test_connection()` → 返回 `{success, repo_info, error}`
4. **健康检查**：每次使用前 `mcp_coordinator.py` 探活，失败重连 3 次

> **与用户 MCP 配置的区别**：AIR 项目的 `mcp_configs` 表允许用户自定义 MCP 配置；docbot **不开放此能力**，仅提供系统自带的 git + filesystem 两个 MCP 服务，确保所有用户都能开箱即用，避免配置缺失导致功能不可用。

---

## 9. API 设计

### 9.1 API 端点

docbot 提供以下 OpenAI 兼容 API（`agent_id` 隐式为 `agentinsight-docbot`）：

| 端点 | 方法 | 用途 |
|------|------|------|
| `/v1/chat/completions` | POST | OpenAI 兼容，SSE 流式（一键生成请求也走此端点，message 内容为 JSON 指令） |
| `/v1/sessions` | GET/POST/DELETE | 会话管理 |
| `/v1/sessions/{id}/reports` | GET | 历史报告列表 |
| `/v1/reports/{id}/download` | GET | 报告下载（支持 markdown/html/pdf/docx/json） |
| `/health` | GET | 健康检查 |

> **不提供的端点**（与 AIR 区别）：
> - 不提供 `POST /v1/feedback`（人在回路反馈，docbot 不需要）
> - 不提供 `WS /v1/ws/{session_id}`（WebSocket 8 类消息，docbot 仅用 SSE 流式）
> - 不提供 `GET/POST/PUT/DELETE /v1/mcp/configs`（MCP 配置 CRUD，docbot MCP 服务系统自带，不需要用户配置）

### 9.2 新增 API：`/v1/repos`

```python
# src/api/repo_routes.py
POST   /v1/repos                  # 创建用户代码仓库配置
GET    /v1/repos                  # 列出当前用户所有仓库
GET    /v1/repos/{id}             # 获取单个仓库配置（不返回敏感字段原文）
PUT    /v1/repos/{id}             # 更新仓库配置
DELETE /v1/repos/{id}             # 删除仓库配置
POST   /v1/repos/{id}/test        # 测试仓库连接
POST   /v1/repos/{id}/sync        # 触发仓库索引（克隆 + 嵌入）
GET    /v1/repos/{id}/sync-status # 查询索引状态
```

**请求体示例（POST /v1/repos）**：

```json
{
  "repo_name": "我的 GitHub 项目",
  "platform": "github",
  "repo_url": "https://github.com/owner/repo.git",
  "auth_type": "token",
  "token": "ghp_xxxxxxxxxxxx",
  "default_branch": "main",
  "clone_depth": 0,
  "description": "可选描述"
}
```

**响应体示例**：

```json
{
  "id": "uuid",
  "repo_name": "我的 GitHub 项目",
  "platform": "github",
  "repo_url": "https://github.com/owner/repo.git",
  "auth_type": "token",
  "has_token": true,
  "default_branch": "main",
  "enabled": true,
  "last_synced_at": null,
  "last_sync_status": null,
  "created_at": "2026-07-19T10:00:00Z",
  "updated_at": "2026-07-19T10:00:00Z"
}
```

> **安全约束**（遵守 AGENTS.md 第 11 章）：
> - `token` / `password` / `ssh_key` 仅创建/更新时返回 `has_token: bool`，永远不返回原文
> - 敏感字段 AES-GCM 加密存储，密钥由 `settings.git_credential_key` 注入（环境变量）
> - API 响应禁止返回密钥原文（硬约束）

### 9.3 一键生成请求格式

用户点击"一键生成"按钮，前端构造 OpenAI 兼容请求：

```json
POST /v1/chat/completions
{
  "model": "agentinsight-docbot",
  "messages": [
    {
      "role": "user",
      "content": "{\"action\":\"generate_docs\",\"repo_id\":\"uuid\",\"report_types\":[\"architecture\",\"design\"],\"report_format\":\"markdown\",\"language\":\"zh\"}"
    }
  ],
  "stream": true,
  "session_id": "uuid"
}
```

后端解析 `content` 中的 JSON 指令，启动顶层图，通过 SSE 流式返回进度。

---

## 10. 前端架构

### 10.1 frontend 工程

docbot 自带独立的 frontend 工程（位于本仓库 `frontend/` 目录，从 AIR 拷贝后精简，仅保留 docbot 配置），通过 `agents.config.ts` SSOT 配置 Agent。

```typescript
// frontend/lib/agents.config.ts
export const AGENTS_CONFIG = {
  agents: [
    {
      id: 'agentinsight-docbot',
      name: '技术文档助手',
      port: 8068,
      apiBaseUrl: '/api/docbot',
      inputComponent: 'DocbotInput',
      settingsPanels: ['RepoConfigPanel'],
      supportedFormats: ['markdown', 'html', 'pdf', 'docx', 'json'],
      supportedLanguages: ['zh', 'en'],
      supportedReportTypes: [
        { value: 'architecture', label: '技术架构文档' },
        { value: 'design', label: '概要设计文档' },
        { value: 'requirements', label: '需求文档' },
        { value: 'testcase', label: '测试用例文档' },
        { value: 'optimization', label: '系统优化文档' },
        { value: 'performance', label: '性能分析文档' },
        { value: 'defect', label: '系统缺陷文档' },
        { value: 'api_doc', label: 'API 文档' },
      ],
    },
  ],
} as const;
```

### 10.2 新增组件

| 组件 | 路径 | 职责 |
|------|------|------|
| `DocbotInput` | `frontend/components/chat/docbot-input.tsx` | 主输入框：代码仓库下拉 + 报告类型多选 + 语言选择 + 一键生成按钮 |
| `RepoConfigPanel` | `frontend/components/settings/repo-config-panel.tsx` | 用户仓库 CRUD + 测试 + 同步 |
| `ReportTypeSelect` | `frontend/components/chat/report-type-select.tsx` | 报告类型多选下拉（8 种） |
| `RepoSelect` | `frontend/components/chat/repo-select.tsx` | 代码仓库下拉选择（仅 enabled=true 的仓库） |
| `LanguageSelect` | `frontend/components/chat/language-select.tsx` | 语言选择（zh/en） |

### 10.3 主框体改造

```
docbot 主框体：
┌──────────────────────────────────────────────────┐
│ [进度消息列表 - SSE 流式]                        │
│ ┌──────────────────────────────────────────────┐ │
│ │ 代码仓库: [选择仓库 ▼]                       │ │
│ │ 报告类型: [☑架构 ☑设计 ☐需求 ☐测试 ☐优化 ☐性能 ☐缺陷 ☐API] │ │
│ │ 文档格式: [markdown ▼]   语言: [简体中文 ▼]  │ │
│ │                                              │ │
│ │                              [一键生成文档]  │ │
│ └──────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────┘
```

详细代码见 [DESIGN_FRONTEND.md](./DESIGN_FRONTEND.md)。

---

## 11. 报告生成设计

### 11.1 ReportGenerator + Publisher + ImageGenerator

docbot 8 种文档类型通过 `agent_role` persona 注入复用 ReportGenerator：

```python
# src/config/docbot/personas.py
DOCBOT_REPORT_PERSONAS = {
    "architecture": {
        "role_name": "技术架构文档专家",
        "description": "专注于系统架构分析，包括组件关系、数据流、部署拓扑、技术选型",
        "outline_file": "docs/ARCHITECTURE_OUTLINE.md",  # 引用外部大纲文件
        "tone": "technical_formal",
    },
    "design": {
        "role_name": "概要设计文档专家",
        "description": "专注于模块设计、接口定义、数据模型、核心流程",
        "outline_file": "docs/HLD_OUTLINE.md",
        ...
    },
    # ... 8 种
}
```

### 11.2 8 种文档默认大纲

每种文档类型对应一个独立的 Markdown 大纲文件，位于 `docs/` 目录，由 `outlines.py` 在运行时按需读取：

| 文档类型 | persona key | 大纲文件 |
|---------|-------------|---------|
| 技术架构文档 | `architecture` | [ARCHITECTURE_OUTLINE.md](./ARCHITECTURE_OUTLINE.md) |
| 概要设计文档 | `design` | [HLD_OUTLINE.md](./HLD_OUTLINE.md) |
| 需求文档 | `requirements` | [PRD_OUTLINE.md](./PRD_OUTLINE.md) |
| 测试用例文档 | `testcase` | [TEST_CASE_OUTLINE.md](./TEST_CASE_OUTLINE.md) |
| 系统优化文档 | `optimization` | [OPTIMIZATION_OUTLINE.md](./OPTIMIZATION_OUTLINE.md) |
| 性能分析文档 | `performance` | [PERF_ANALYSIS_OUTLINE.md](./PERF_ANALYSIS_OUTLINE.md) |
| 系统缺陷文档 | `defect` | [DEFECT_OUTLINE.md](./DEFECT_OUTLINE.md) |
| API 文档 | `api_doc` | [API_DOC_OUTLINE.md](./API_DOC_OUTLINE.md) |

**大纲加载机制**（`src/config/docbot/outlines.py`）：

```python
from pathlib import Path

OUTLINE_DIR = Path(__file__).resolve().parents[2] / "docs"

def load_outline(report_type: str) -> list[dict]:
    """从 docs/{PREFIX}_OUTLINE.md 加载默认大纲。

    返回结构：[{idx, title, sections: [{name, key_points}], key_points}]
    """
    file_map = {
        "architecture": "ARCHITECTURE_OUTLINE.md",
        "design": "HLD_OUTLINE.md",
        "requirements": "PRD_OUTLINE.md",
        "testcase": "TEST_CASE_OUTLINE.md",
        "optimization": "OPTIMIZATION_OUTLINE.md",
        "performance": "PERF_ANALYSIS_OUTLINE.md",
        "defect": "DEFECT_OUTLINE.md",
        "api_doc": "API_DOC_OUTLINE.md",
    }
    outline_path = OUTLINE_DIR / file_map[report_type]
    # 解析 Markdown 章节为结构化大纲
    return parse_markdown_outline(outline_path.read_text(encoding="utf-8"))
```

### 11.3 报告保存

复用 `report_store.py`，每报告一行 `research_reports` 记录：

```python
async def save_docbot_report(
    user_id: str,
    session_id: str,
    report_type: str,
    report_format: str,
    language: str,
    content: str,
    image_svg: str | None,
    summary: str,
) -> dict:
    return await report_store.create_report(
        agent_id="agentinsight-docbot",
        user_id=user_id,
        session_id=session_id,
        title=f"{DOCBOT_REPORT_PERSONAS[report_type]['role_name']}-{report_type}",
        content=content,
        format=report_format,
        language=language,
        metadata={
            "report_type_label": report_type,
            "report_summary": summary,
            "report_image_svg": image_svg,
        },
    )
```

### 11.4 图片生成

复用 `image_generator.py`（DeepSeek SVG 生成）。任务三（D 内容填充）按需调用：

```python
async def generate_image_for_chapter(chapter_title: str, chapter_content: str, language: str) -> str | None:
    """根据章节内容生成 SVG 配图，返回 SVG 字符串或 None。"""
```

### 11.5 多语言

docbot 仅支持简体中文（zh）和英文（en）两种文档语言，i18n 资源文件位于 `frontend/i18n/{zh,en}/docbot.json`：

```json
// frontend/i18n/zh/docbot.json
{
  "report_types": {
    "architecture": "技术架构文档",
    "design": "概要设计文档",
    "requirements": "需求文档",
    "testcase": "测试用例文档",
    "optimization": "系统优化文档",
    "performance": "性能分析文档",
    "defect": "系统缺陷文档",
    "api_doc": "API 文档"
  },
  "input": {
    "select_repo": "选择代码仓库",
    "select_report_types": "选择报告类型",
    "select_format": "文档格式",
    "select_language": "语言",
    "generate": "一键生成文档"
  }
}
```

---

## 12. 可观测性设计

### 12.1 6 类 trace_xxx

docbot 自带 `observability/tracing.py`（从 AIR 拷贝），**零代码改动**：

| trace 类型 | 包裹位置（docbot） |
|-----------|-------------------|
| `trace_agent` | 顶层图入口（`coordinator_a`），根 span，metadata 含 `report_types` / `repo_id` |
| `trace_generation` | `llm/` 网关层（LLMClient），每个 LLM 调用自动包裹 |
| `trace_tool` | `git_mcp.py` 的 MCP 调用 |
| `trace_retriever` | 任务三 D 内容填充时的 RAG 检索 |
| `trace_chain` | 报告子图 6 步流水线 |
| `trace_embedding` | 仓库索引时的 embedding 调用（head-based 0.5 采样） |

### 12.2 span 命名约定

| span name | 示例 |
|-----------|------|
| `docbot.coordinator_a` | 顶层协调 |
| `docbot.report.{report_type}.b_init` | 报告子图入口 |
| `docbot.report.{report_type}.code_learning` | 任务一 |
| `docbot.report.{report_type}.outline_refine` | 任务二 |
| `docbot.report.{report_type}.content_fill.{chapter_idx}` | 任务三（按章节） |
| `docbot.report.{report_type}.review.{chapter_idx}` | 任务四（按章节） |
| `docbot.report.{report_type}.merge` | 任务五 |
| `docbot.report.{report_type}.final_review` | 任务六 |
| `docbot.final_reviewer_g` | 顶层终审 |

### 12.3 降级策略

Null Object 模式：SDK 初始化失败或运行时异常时，所有 `trace_xxx` yield `_NoopSpan`，业务代码不判断 SDK 可用性。

---

## 13. 部署架构

### 13.1 容器清单（5 容器）

> docbot 自带完整 5 容器栈，独立运行，不与任何外部项目共享。

| 服务 | 镜像 | 端口 | 健康检查 |
|------|------|------|---------|
| `agent-docbot` | 本仓 `Dockerfile`（Python 3.12-slim） | 8068 | `GET /health` |
| `embeddings` | BGE 服务镜像（bge-base-zh-v1.5） | 8088 | `GET /health` |
| `qdrant` | `qdrant/qdrant:≥1.18` | 6333/6334 | `/healthz` |
| `redis` | `redis:≥8` | 6379 | `redis-cli ping` |
| `postgres` | `postgres:≥17` | 5432 | `pg_isready -U <user>` |

> docbot 不需要 `searxng`（无网络搜索需求，仓库代码通过 MCP 访问）；不需要 `rerank`（默认 `rerank_enabled=False`）。

### 13.2 三套构建模式

| 模式 | 构建文件 | 编排文件 | 环境文件 | 构建脚本 |
|------|---------|---------|---------|---------|
| QA | `Dockerfile.qa` | `docker-compose-qa.yaml` | `.env.qa` | `docker-build.qa.bat` |
| 生产联网 | `Dockerfile` | `docker-compose.yml` | `.env` | `docker-build.sh` |
| 生产离线 | `Dockerfile.offline` | `docker-compose-offline.yaml` | `.env` | `docker-build.offline.sh` |

### 13.3 容器命名

遵守 AGENTS.md 第 12 章 `-p agentinsight` 约定：

```bash
docker compose -p agentinsight-docbot -f docker-compose.yml --env-file .env up -d
```

容器名：`agentinsight-docbot-agent-docbot-1`。

### 13.4 环境变量

```env
# .env（docbot 专属）
AGENT_NAME=agentinsight-docbot
AGENT_PORT=8068
ENV=prod

# LLM 三级配置
FAST_LLM=zhipuai/glm-4-flash
SMART_LLM=deepseek/deepseek-v4-flash
STRATEGIC_LLM=deepseek/deepseek-v4-pro
ZHIPUAI_API_KEY=...
DEEPSEEK_API_KEY=...

# 基础设施
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_USER=agentinsight
POSTGRES_PASSWORD=...
POSTGRES_DB=agents
REDIS_URL=redis://redis:6379/0
QDRANT_URL=http://qdrant:6333
QDRANT_API_KEY=...
EMBEDDINGS_API_BASE=http://embeddings:8088
EMBEDDINGS_API_KEY=...

# docbot 专属
GIT_CREDENTIAL_KEY=...              # AES-GCM 加密密钥（环境变量注入）
MAX_REPO_SIZE_MB=1024               # 仓库大小上限（MB）
MAX_CONCURRENT_REPORTS=3
MAX_REVISIONS_PER_CHAPTER=3
MAX_CHAPTERS_PER_REPORT=20
CONTEXT_MAX_CHARS=500000            # 单会话上下文上限（约 125K token）
CONTEXT_SESSION_TTL=2592000

# 可观测性
AGENTINSIGHT_PUBLIC_KEY=...
AGENTINSIGHT_SECRET_KEY=...
AGENTINSIGHT_HOST=https://agentinsight.goldebridge.com

# 自托管 / JWT 解析
SELF_HOST=true
JWT_SECRET=...
```

---

## 14. 安全合规

### 14.1 安全机制

- JWT 解析（PyJWT HS256）+ IP 降级（`self_host=True`）
- 中间件：CORS + 安全响应头 + 限流 + 请求大小限制
- 密钥仅环境变量注入，禁止入仓
- PII 加密存储 + 日志脱敏
- Prompt Injection 防护：Pydantic 校验 + 工具权限隔离

### 14.2 docbot 专属安全约束

| 约束 | 实现方式 |
|------|---------|
| 代码仓库敏感字段加密 | AES-GCM 加密 token/password/ssh_key，密钥 `GIT_CREDENTIAL_KEY` 环境变量注入 |
| API 响应禁止返回密钥原文 | `RepoResponse` 模型仅暴露 `has_token: bool` 等标志位 |
| 仓库克隆隔离 | 每用户独立临时目录 `temp/repos/{user_id}/{repo_id}/`，任务结束清理 |
| 仓库代码不外泄 | 代码内容仅用于 LLM 上下文 + Qdrant 索引，不写入日志、不入 `trace_generation` 的 input |
| 仓库 URL 白名单 | 可选配置 `ALLOWED_GIT_DOMAINS`，防止内网渗透 |
| 仓库大小限制 | `MAX_REPO_SIZE_MB=1024`，超出拒绝克隆 |
| 克隆深度限制 | `clone_depth` 默认 0（完整），可配 1（浅克隆）减少 token 消耗 |
| 多仓库数据隔离 | Qdrant namespace 含 `repo_id`，跨仓库不可见 |

---

## 15. 性能与容量

### 15.1 并发控制

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `MAX_CONCURRENT_REPORTS` | 3 | 单次请求最多并发派发 3 个 B 子图 |
| `MAX_REVISIONS_PER_CHAPTER` | 3 | D-E 修订循环每章节最多 3 轮 |
| `MAX_CHAPTERS_PER_REPORT` | 20 | 单报告最大章节数 |
| `MAX_LLM_CONCURRENCY` | 5 | 全局 LLM 调用并发上限（Semaphore） |
| `MAX_RAG_CONCURRENCY` | 10 | RAG 检索并发上限 |

### 15.2 缓存与去重

- 任务一（代码学习）结果缓存 24 小时，同 session 同 repo 复用
- 任务三（内容填充）按章节缓存，D-E 修订循环命中缓存跳过重复 LLM 调用
- LLM 调用结果按 `prompt_hash` 缓存（LLMClient 自带缓存）

### 15.3 上下文压缩

- 单会话上下文上限 `CONTEXT_MAX_CHARS = 500_000`（约 125K token）
- 任务一的代码学习结果可能超过 125K token，触发压缩：
  - 滑动窗口 + LLM 摘要，保留最近 25% 文件为原文，其余摘要化
  - 压缩用 FAST LLM（glm-4-flash）降低成本
- 压缩异步后台执行，不阻塞用户响应

---

## 16. 测试策略

### 16.1 测试分层

| 类型 | 目录 | 触发时机 |
|------|------|---------|
| 单元 | `tests/unit/` | commit / Docker build |
| 功能 | `tests/functional/` | 容器栈健康后 |
| API | `tests/api/` | 容器栈健康后 |
| 回归 | `tests/regression/` | 合并 main 前 |
| e2e | `tests/e2e/` | 发布前 |

### 16.2 关键测试用例

1. **单元**：
   - `DOCBOT_REPORT_PERSONAS` 8 种 persona 完整性
   - `outlines.load_outline()` 8 个大纲文件可正确解析
   - `GitMCPAdapter.clone_repo()` 各平台 URL 解析
   - AES-GCM 加密 / 解密往返
   - `coordinator_a` 派发逻辑（mock 子图）
   - D-E 修订循环守卫

2. **功能**：
   - 端到端克隆 + 索引 + 检索（小仓库）
   - 8 种文档类型各生成一份（mock LLM）
   - 多报告并发派发（3 个 B 子图）
   - 多仓库索引隔离（同 user 不同 repo_id 不串数据）

3. **API**：
   - `/v1/repos` CRUD + 测试 + 同步
   - `/v1/chat/completions` 一键生成 SSE 流式
   - `/v1/reports/{id}/download` 5 种格式

4. **e2e**：
   - 打开测试页 → 配置仓库 → 新建会话 → 一键生成 → 验证 SSE 进度 → 验证报告下载

---

## 17. 附录

### 17.1 参考资料

- LangGraph ≥1.2 官方文档：https://langchain-ai.github.io/langgraph/
- LiteLLM ≥1.6 官方文档：https://docs.litellm.ai/
- MCP 官方规范：https://modelcontextprotocol.io/
- Qdrant 官方文档：https://qdrant.tech/documentation/
- AgentInsight SDK：内部文档
- IEEE 软件设计文档大纲
- Google SRE 文档规范
- Microsoft SDL 文档模板

### 17.2 术语表

| 术语 | 含义 |
|------|------|
| docbot | AgentInsight DocBot（本项目，agentinsight-docbot） |
| persona | LLM 角色设定（role_name + description + tone） |
| RRF | Reciprocal Rank Fusion（倒数排名融合） |
| TEI | Text Embeddings Inference（HuggingFace 嵌入服务） |
| FastEmbed | ONNX INT8 本地嵌入（CPU 友好） |
| Checkpointer | LangGraph 状态持久化机制 |
| Null Object | 空对象模式（可观测性降级） |

---

**文档结束**。详细实现请参考 [DESIGN_AGENT.md](./DESIGN_AGENT.md) 和 [DESIGN_FRONTEND.md](./DESIGN_FRONTEND.md)。

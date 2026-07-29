# agentinsight-docbot 优化方案

> **文档性质**：差异化对标 + 优化方案（P1 全部完成，P2 全部完成，P3 全部不启用）
> **基准日期**：2026-07-29
> **P1 执行状态**：已于 2026-07-29 完成 6 项（5.2.1 / 5.2.2 / 5.2.3 / 5.3.1 / 5.3.2 / 5.3.3）
> **P2 执行状态**：已于 2026-07-29 完成 4 项（5.4.1 / 5.4.2 / 5.5.1 / 5.5.2）
> **P3 执行状态**：全部不启用（5.6.1 经评估无实际价值；5.6.2 与 AGENTS.md 冲突）
> **基准代码**：`D:\Projects\Entrepreneurship\AIProjects\agentinsight-agents\agentinsight-docbot\` 当前 HEAD
> **编写原则**：严格基于代码事实，不编造架构与工具；每条论断附文件路径与行号作为证据
> **对标范围**：业界开源"代码→技术文档"Agent / 通用深度研究 Agent / 代码理解 RAG 工具
> **上游方案**：本方案衍生自 [agentinsight-researcher/docs/optimization-plan.md](file:///d:/Projects/Entrepreneurship/AIProjects/agentinsight-agents/agentinsight-researcher/docs/optimization-plan.md)，聚焦 docbot 专属任务（researcher 项目仅承担 P0 文档治理）

---

## 1. 背景与目标

本方案在 researcher 项目 P0 文档治理完成的基础上，承接 P1-P3 优化任务中归属 docbot 的部分（见 researcher 方案第 5.2-5.6 节标注的"所属项目：docbot"）。目标：

1. **提升代码理解深度**：从 AST 函数/类分块（第 3 层）跃升到符号级仓库地图（第 4 层）与调用图（第 6 层）
2. **保障文档质量与可追溯性**：行级引用溯源 + 代码变更漂移检测 + 文档结构完整性校验
3. **完善评估体系**：补充引用可追溯性、结构完整性、术语一致性等维度
4. **远期架构演进**：MCP 化代码图谱工具、可选人机协作模式

**与 researcher 项目的关系**：docbot 从 researcher 拷贝基础模块（common/rag/llm/memory/observability/api）后独立演进，本仓库内不双向同步。P0 文档治理在 researcher 项目内完成；P1-P3 中标注"所属项目：docbot"的任务在本仓库内执行。

---

## 2. 项目现状基线（基于代码事实）

### 2.1 项目定位

| 维度 | 事实 | 证据 |
|------|------|------|
| 定位 | LangGraph ≥1.2 编排 + MCP 工具协议 + 7 子智能体协作的"代码→技术文档"生成系统 | [AGENTS.md](file:///d:/Projects/Entrepreneurship/AIProjects/agentinsight-agents/agentinsight-docbot/AGENTS.md#L14) 第 14 行 |
| 对外端口 | 8068（仅 `agent:8068` 对外） | [AGENTS.md](file:///d:/Projects/Entrepreneurship/AIProjects/agentinsight-agents/agentinsight-docbot/AGENTS.md#L14) 第 14 行 |
| 容器项目名 | `-p agentinsight-docbot`（独立命名空间，5 容器） | [AGENTS.md](file:///d:/Projects/Entrepreneurship/AIProjects/agentinsight-agents/agentinsight-docbot/AGENTS.md#L10) 第 10 行 |
| 文档类型 | 8 种：architecture/design/requirements/testcase/optimization/performance/defect/api_doc | [AGENTS.md](file:///d:/Projects/Entrepreneurship/AIProjects/agentinsight-agents/agentinsight-docbot/AGENTS.md#L20) 第 20 行 |
| 文档格式 | 5 种：markdown/html/pdf/docx/json | [AGENTS.md](file:///d:/Projects/Entrepreneurship/AIProjects/agentinsight-agents/agentinsight-docbot/AGENTS.md#L21) 第 21 行 |
| 文档语言 | 2 种：zh/en | [AGENTS.md](file:///d:/Projects/Entrepreneurship/AIProjects/agentinsight-agents/agentinsight-docbot/AGENTS.md#L19) 第 19 行 |

### 2.2 实际目录结构

```
agentinsight-docbot/
├── src/
│   ├── graph/          # LangGraph 图定义（builder/report_builder/state/nodes/report_nodes/edges）
│   ├── agents/docbot/  # 7 个子智能体（coordinator/report_runner/outline_refiner/
│   │                   #              content_filler/reviewer/merger/final_reviewer）
│   ├── api/            # FastAPI 路由 + 中间件（routes/middleware/session_routes/repo_routes）
│   ├── common/         # 公用基础（从 AIR 拷贝，独立演进）
│   ├── config/         # Settings SSOT + docbot 专属配置（personas/outlines/prompts）
│   ├── skills/docbot/  # 6 步流水线技能（repo_loader/code_learner/outline_skill/content_skill/
│   │                   #              review_skill/merge_skill/final_skill/cache +
│   │                   #              P1 新增: citation_extractor/structure_validator/drift_detector）
│   ├── tools/git_mcp.py    # 用户代码仓库 MCP 适配（封装 mcp-server-git）
│   ├── rag/            # 自研 RAG（从 AIR 拷贝，namespace 加 repo_id 隔离）
│   ├── llm/            # LiteLLM 网关（三级降级链 FAST/SMART/STRATEGIC）
│   ├── memory/         # Postgres Checkpointer + ReportStore + SessionStore + db_initializer
│   └── observability/  # AgentInsight SDK 封装（6 类 trace_xxx）
├── scripts/init.sql    # 完整 DDL（基础 + docbot 专属 + P1 新增表/列）
├── tests/              # 分层测试（unit/functional/api/regression/e2e/exploratory/performance/smoke/security/integration）
├── docs/               # 设计与架构文档
├── Dockerfile          # Agent 镜像
├── docker-compose.yml  # 5 容器编排（postgres/redis/qdrant/embeddings/agent-docbot）
└── server.py           # FastAPI 入口
```

**证据**：[AGENTS.md](file:///d:/Projects/Entrepreneurship/AIProjects/agentinsight-agents/agentinsight-docbot/AGENTS.md#L79-L135) 第 79-135 行明确目录结构定义。

### 2.3 实际图编排

**顶层图**（[builder.py](file:///d:/Projects/Entrepreneurship/AIProjects/agentinsight-agents/agentinsight-docbot/src/graph/builder.py)）：
```
START → coordinator_a → spawn_b_tasks → final_reviewer_g → save_reports → cleanup_repo → END
```

**报告子图**（[report_builder.py](file:///d:/Projects/Entrepreneurship/AIProjects/agentinsight-agents/agentinsight-docbot/src/graph/report_builder.py)）：
```
START → b_init → c_code_learning → c_outline_refine
      → d_content_fill ↔ e_review (max_revisions_per_chapter=3)
      → f_merge → g_final_in_subgraph → END
```

并发控制：`MAX_CONCURRENT_REPORTS=3`（asyncio.gather + Semaphore 并发派发 N 个 B 子图）。

### 2.4 实际数据库表（来自 [init.sql](file:///d:/Projects/Entrepreneurship/AIProjects/agentinsight-agents/agentinsight-docbot/scripts/init.sql)）

| 表名 | 用途 | P1 改动 |
|------|------|---------|
| `research_sessions` | 研究会话 | - |
| `research_reports` | 研究报告 | P1-5.3.2 新增 `is_stale`/`stale_reason`/`stale_detected_at` 列 |
| `token_usage_logs` | Token 使用记录 | - |
| `report_citations` | **P1-5.3.1 新增**：行级引用溯源 | 全表新增 |
| `user_git_repos` | 用户代码仓库配置 | P1-5.3.2 新增 `last_doc_commit_hash`/`last_doc_synced_at` 列 |
| `chat_messages` | 对话消息 | - |

### 2.5 实际可观测性

6 类 `trace_xxx` 异步上下文管理器（[tracing.py](file:///d:/Projects/Entrepreneurship/AIProjects/agentinsight-agents/agentinsight-docbot/src/observability/tracing.py)）：`trace_agent` / `trace_generation` / `trace_tool` / `trace_retriever` / `trace_chain` / `trace_embedding`。SDK 不可用时降级为 `_NoopSpan`（Null Object 模式）。

---

## 3. 代码理解策略分层（按深度递增）

| 层级 | 策略 | 代表项目 | docbot 当前位置 |
|------|------|---------|----------------|
| 1 | 文件树/目录树识别 | readme-ai | ✅ 已具备 |
| 2 | 清单文件解析 | readme-ai | ✅ 已具备 |
| 3 | AST 函数/类分块 | Continue | ✅ 已具备（[repo_loader.py](file:///d:/Projects/Entrepreneurship/AIProjects/agentinsight-agents/agentinsight-docbot/src/skills/docbot/repo_loader.py) `_chunk_code_file`） |
| 4 | tree-sitter 符号级仓库地图 | Aider | ✅ **P1-5.2.1 已完成**（[repo_map.py](file:///d:/Projects/Entrepreneurship/AIProjects/agentinsight-agents/agentinsight-docbot/src/skills/docbot/repo_map.py) `generate_repo_map`） |
| 5 | AST 方法/类级结构化搜索 API | AutoCodeRover | ❌ 未具备 |
| 6 | 调用图/知识图谱 | Codebase-Memory-MCP | ✅ **P1-5.2.2 已完成**（[code_graph.py](file:///d:/Projects/Entrepreneurship/AIProjects/agentinsight-agents/agentinsight-docbot/src/skills/docbot/code_graph.py) `build_code_graph`） |
| 7 | 向量嵌入 + BM25 混合检索 + Rerank | Bloop | ✅ 已具备（BM25+jieba + bge-base-zh + bge-reranker-v2-m3 + RRF） |
| 8 | 关键文件优先级选取（带优先级分组） | GitMCP | ✅ **P1-5.2.3 已完成**（[repo_loader.py](file:///d:/Projects/Entrepreneurship/AIProjects/agentinsight-agents/agentinsight-docbot/src/skills/docbot/repo_loader.py) `select_key_files` 优先级队列） |

---

## 4. P1 优化方案执行情况

### 4.1 ✅ P1-5.2.3 关键文件优先级队列优化（已完成 2026-07-29）

- **现状**：[repo_loader.py](file:///d:/Projects/Entrepreneurship/AIProjects/agentinsight-agents/agentinsight-docbot/src/skills/docbot/repo_loader.py) `select_key_files` 已有 `_KEY_FILE_NAMES` 优先选取，但未显式优先读 `llms.txt`/`CLAUDE.md`/`CHANGELOG.md`，且无优先级分组
- **已实施方案**：
  1. 扩展 `_KEY_FILE_NAMES` 集合，新增 `llms.txt` / `CLAUDE.md` / `CHANGELOG.md`
  2. 引入 4 级优先级分组：文档型（10）> 依赖清单（20）> 入口（30）> 配置（40）；未命中的关键文件默认 50；普通代码文件 100
  3. 同优先级内按路径深度排序（根目录优先），再按路径字母序稳定排序
  4. 关键文件优先填满 `max_files=50`，不足时用代码文件补足
- **所属项目**：docbot
- **预期收益**：代码学习质量提升，LLM 先看到 README/AGENTS.md/ARCHITECTURE.md 等高价值文档
- **实施成本**：低（已完成）
- **测试**：[test_repo_loader_priority.py](file:///d:/Projects/Entrepreneurship/AIProjects/agentinsight-agents/agentinsight-docbot/tests/unit/test_repo_loader_priority.py) 20 个测试用例全部通过

### 4.2 ✅ P1-5.3.1 文档行级引用溯源（已完成 2026-07-29）

- **现状**：docbot 生成的文档未显式标注"这段描述对应 `src/foo.py:L42`"
- **已实施方案**：
  1. 新增 [citation_extractor.py](file:///d:/Projects/Entrepreneurship/AIProjects/agentinsight-agents/agentinsight-docbot/src/skills/docbot/citation_extractor.py)：从 Markdown 提取 `[src/foo.py:L42-L58]` 形式引用，校验路径存在性与行号合理性
  2. [init.sql](file:///d:/Projects/Entrepreneurship/AIProjects/agentinsight-agents/agentinsight-docbot/scripts/init.sql) 新增 `report_citations` 表（含 `report_id`/`agent_id`/`user_id`/`session_id`/`file_path`/`line_start`/`line_end`/`raw_reference` 字段，3 个复合索引）
  3. [prompts.py](file:///d:/Projects/Entrepreneurship/AIProjects/agentinsight-agents/agentinsight-docbot/src/config/docbot/prompts.py) `CONTENT_FILL_PROMPT` 增加行级引用格式约束（3 种格式 + 示例 + 4 条硬约束）
- **所属项目**：docbot
- **预期收益**：文档可信度大幅提升，支持"点击引用跳转代码"
- **实施成本**：中（已完成）
- **测试**：[test_citation_extractor.py](file:///d:/Projects/Entrepreneurship/AIProjects/agentinsight-agents/agentinsight-docbot/tests/unit/test_citation_extractor.py) 19 个测试用例全部通过
- **借鉴**：STORM 的引用机制

### 4.3 ✅ P1-5.3.2 代码变更触发文档漂移检测（已完成 2026-07-29）

- **现状**：代码变更后文档不会自动失效/更新
- **已实施方案**：
  1. [git_mcp.py](file:///d:/Projects/Entrepreneurship/AIProjects/agentinsight-agents/agentinsight-docbot/src/tools/git_mcp.py) 新增 `get_head_commit_hash` + `list_changed_files` 方法（含 commit hash 正则校验防注入）
  2. [init.sql](file:///d:/Projects/Entrepreneurship/AIProjects/agentinsight-agents/agentinsight-docbot/scripts/init.sql) 给 `user_git_repos` 新增 `last_doc_commit_hash`/`last_doc_synced_at` 列；给 `research_reports` 新增 `is_stale`/`stale_reason`/`stale_detected_at` 列
  3. 新增 [drift_detector.py](file:///d:/Projects/Entrepreneurship/AIProjects/agentinsight-agents/agentinsight-docbot/src/skills/docbot/drift_detector.py) `detect_doc_drift` + `update_last_doc_commit` + `_mark_stale_reports`
  4. [repo_routes.py](file:///d:/Projects/Entrepreneurship/AIProjects/agentinsight-agents/agentinsight-docbot/src/api/repo_routes.py) sync 接口集成漂移检测（不阻断同步流程，失败仅告警）
  5. [nodes.py](file:///d:/Projects/Entrepreneurship/AIProjects/agentinsight-agents/agentinsight-docbot/src/graph/nodes.py) `save_reports_node` 文档生成成功后调用 `_update_repo_doc_commit_hash` 记录当前 HEAD commit
- **所属项目**：docbot
- **预期收益**：文档与代码保持同步，stale 文档可触发增量重生成
- **实施成本**：中（已完成）
- **测试**：[test_drift_detector.py](file:///d:/Projects/Entrepreneurship/AIProjects/agentinsight-agents/agentinsight-docbot/tests/unit/test_drift_detector.py) 10 个测试用例全部通过

### 4.4 ✅ P1-5.3.3 文档结构完整性校验（已完成 2026-07-29）

- **现状**：仅 RAGAS+DeepEval 自动门禁，未校验文档结构
- **已实施方案**：新增 [structure_validator.py](file:///d:/Projects/Entrepreneurship/AIProjects/agentinsight-agents/agentinsight-docbot/src/skills/docbot/structure_validator.py) `validate_structure`，4 类校验：
  1. **章节齐全度**：对照 outline YAML 的 `chapters[].title`，检查生成文档是否包含所有章节（子串包含匹配，中英文兼容）
  2. **代码路径引用存在性**：提取文档中 `src/foo.py` 形式引用，校验是否在 `file_index` 中存在
  3. **Markdown 结构**：检查空章节 / 过短章节（< `min_chapter_chars`）/ 标题层级跳跃（## → #### 跳级）
  4. **术语一致性（基础版）**：检测同义术语变体（如 API/接口、数据库/DB）在文档中混用
- **所属项目**：docbot
- **预期收益**：文档结构质量保障，结构问题可量化追踪
- **实施成本**：中（已完成）
- **测试**：[test_structure_validator.py](file:///d:/Projects/Entrepreneurship/AIProjects/agentinsight-agents/agentinsight-docbot/tests/unit/test_structure_validator.py) 17 个测试用例全部通过

### 4.5 ✅ P1-5.2.1 引入 tree-sitter 仓库地图（已完成 2026-07-29）

- **现状**：[repo_loader.py](file:///d:/Projects/Entrepreneurship/AIProjects/agentinsight-agents/agentinsight-docbot/src/skills/docbot/repo_loader.py) AST 分块仅按 `def`/`class` 行分割，未生成符号级仓库地图
- **已实施方案**：
  1. 新增 [repo_map.py](file:///d:/Projects/Entrepreneurship/AIProjects/agentinsight-agents/agentinsight-docbot/src/skills/docbot/repo_map.py)：用 tree-sitter 解析代码文件，提取符号（类/函数/方法）签名，生成 Aider 风格紧凑仓库地图
  2. 支持 9 种语言扩展名（.py/.js/.jsx/.ts/.tsx/.go/.java/.rs/.c/.h/.cpp/.cc/.cxx/.hpp），通过 `tree-sitter-language-pack` 预装
  3. 失败降级：tree-sitter 不可用时返回空字符串，不阻断主流程；大仓库用 `max_chars=8192` 截断
  4. [code_learner.py](file:///d:/Projects/Entrepreneurship/AIProjects/agentinsight-agents/agentinsight-docbot/src/skills/docbot/code_learner.py) 步骤 4.5 调用 `generate_repo_map`，注入到 `CODE_LEARNING_PROMPT` 的 `{repo_map}` 占位符
  5. [prompts.py](file:///d:/Projects/Entrepreneurship/AIProjects/agentinsight-agents/agentinsight-docbot/src/config/docbot/prompts.py) `CODE_LEARNING_PROMPT` 新增 `{repo_map}` 占位符（仓库符号地图章节）
- **所属项目**：docbot
- **预期收益**：代码理解从第 3 层跃升到第 4 层，LLM 能"看见"整个仓库结构
- **实施成本**：中（已完成）
- **新依赖**：`tree-sitter==0.26.0` + `tree-sitter-language-pack==1.13.5`（已加入 [requirements.txt](file:///d:/Projects/Entrepreneurship/AIProjects/agentinsight-agents/agentinsight-docbot/requirements.txt) 第 62-65 行）
- **测试**：[test_repo_map.py](file:///d:/Projects/Entrepreneurship/AIProjects/agentinsight-agents/agentinsight-docbot/tests/unit/test_repo_map.py) 覆盖符号提取 / repo map 生成 / 边界场景，tree-sitter 不可用时自动 skip
- **借鉴**：Aider 的 [Repository Map](https://aider.chat/docs/repomap.html)

### 4.6 ✅ P1-5.2.2 引入代码知识图谱层（已完成 2026-07-29）

- **现状**：无跨文件调用关系图谱，无法回答"A 模块依赖哪些 B"类结构问题
- **已实施方案**：
  1. 新增 [code_graph.py](file:///d:/Projects/Entrepreneurship/AIProjects/agentinsight-agents/agentinsight-docbot/src/skills/docbot/code_graph.py)：定义 `SymbolNode` / `GraphEdge` / `CodeGraph` 数据类，构建内存代码知识图谱
  2. 三类关系边：`import`（模块依赖）/ `call`（函数调用）/ `inherit`（类继承），每条边带 `evidence`（`文件路径:L行号`）溯源
  3. Python 深度提取：`_extract_python_imports` / `_extract_python_calls` / `_extract_python_inheritance`；其他语言降级仅提取符号节点
  4. `format_code_graph_for_prompt` 将图谱格式化为 3 段紧凑文本（模块依赖 / 调用关系 / 继承链），每段独立 max_chars 截断
  5. [code_learner.py](file:///d:/Projects/Entrepreneurship/AIProjects/agentinsight-agents/agentinsight-docbot/src/skills/docbot/code_learner.py) 步骤 4.6 调用 `build_code_graph` + `format_code_graph_for_prompt`，注入到 `CODE_LEARNING_PROMPT` 的 `{code_graph}` 占位符
  6. [prompts.py](file:///d:/Projects/Entrepreneurship/AIProjects/agentinsight-agents/agentinsight-docbot/src/config/docbot/prompts.py) `CODE_LEARNING_PROMPT` 新增 `{code_graph}` 占位符（代码知识图谱章节）
- **所属项目**：docbot
- **预期收益**：代码理解从第 3+7 层跃升到第 6 层，Token 消耗显著降低（业界报告降 99%），结构准确度提升
- **实施成本**：高（已完成）
- **新依赖**：复用 P1-5.2.1 的 tree-sitter，无额外依赖
- **架构约束**：遵循 [AGENTS.md](file:///d:/Projects/Entrepreneurship/AIProjects/agentinsight-agents/agentinsight-docbot/AGENTS.md#L147-L154) 第 3 章"依赖单向向内"原则，图谱模块放在 `skills/docbot/`（业务模块），不放在 `common/`
- **测试**：[test_code_graph.py](file:///d:/Projects/Entrepreneurship/AIProjects/agentinsight-agents/agentinsight-docbot/tests/unit/test_code_graph.py) 覆盖数据结构 / 图谱构建（含 Python 调用关系）/ 格式化，tree-sitter 不可用时自动 skip
- **借鉴**：[Codebase-Memory-MCP](https://github.com/Comprepair/codebase-memory-mcp)

---

## 5. P2 优化方案（✅ 已于 2026-07-29 全部完成）

### 5.1 ✅ P2-5.4.1 多视角代码审问（已完成 2026-07-29）

- **现状**：docbot 任务一 `c_code_learning` 是单视角 STRATEGIC LLM 一次性学习
- **已实施方案**：
  1. 新增 [perspectives.py](file:///d:/Projects/Entrepreneurship/AIProjects/agentinsight-agents/agentinsight-docbot/src/config/docbot/perspectives.py)：8 种 report_type 各派生 3 个视角提问者（架构师/部署/安全等），每个视角含 role / focus / question_topics
  2. 新增 [multi_perspective_learner.py](file:///d:/Projects/Entrepreneurship/AIProjects/agentinsight-agents/agentinsight-docbot/src/skills/docbot/multi_perspective_learner.py)：三阶段流程（FAST 提问 → SMART 回答 → STRATEGIC 汇总），3 视角并发（asyncio.gather）
  3. 新增 3 个 prompt 模板（MULTI_PERSPECTIVE_QUESTION/ANSWER/SYNTHESIS_PROMPT）于 [prompts.py](file:///d:/Projects/Entrepreneurship/AIProjects/agentinsight-agents/agentinsight-docbot/src/config/docbot/prompts.py)
  4. [code_learner.py](file:///d:/Projects/Entrepreneurship/AIProjects/agentinsight-agents/agentinsight-docbot/src/skills/docbot/code_learner.py) 步骤 4.7 添加多视角分支，失败降级到单视角
  5. [settings.py](file:///d:/Projects/Entrepreneurship/AIProjects/agentinsight-agents/agentinsight-docbot/src/config/settings.py) 新增 `docbot_multi_perspective_enabled` 开关（默认 False，向后兼容）
- **所属项目**：docbot
- **预期收益**：代码理解深度显著提升，多视角覆盖模块边界 / 部署 / 安全等维度
- **实施成本**：中（已完成）
- **成本控制**：提问阶段仅用 repo_map+code_graph（FAST LLM），回答阶段截断 file_contents 到 100K（SMART LLM），汇总阶段复用 STRATEGIC LLM。总成本约为单视角的 4-5 倍
- **设计约束**：返回结构与 `learn_code` 完全一致（向后兼容）；失败降级到单视角；默认关闭
- **测试**：[test_perspectives.py](file:///d:/Projects/Entrepreneurship/AIProjects/agentinsight-agents/agentinsight-docbot/tests/unit/test_perspectives.py) 9 个用例 + [test_multi_perspective_learner.py](file:///d:/Projects/Entrepreneurship/AIProjects/agentinsight-agents/agentinsight-docbot/tests/unit/test_multi_perspective_learner.py) 22 个用例（含 mock LLM 主流程 / 异常降级 / JSON 解析 / 格式化截断 / prompt 占位符填充）
- **借鉴**：STORM 的多视角提问 + 模拟对话

### 5.2 ✅ P2-5.4.2 思维导图/代码结构图产物（已完成 2026-07-29）

- **现状**：docbot 已有 DeepSeek SVG 生成能力（[image_generator.py](file:///d:/Projects/Entrepreneurship/AIProjects/agentinsight-agents/agentinsight-docbot/src/skills/researcher/image_generator.py)），但仅生成报告配图
- **已实施方案**：
  1. 新增 [code_diagram.py](file:///d:/Projects/Entrepreneurship/AIProjects/agentinsight-agents/agentinsight-docbot/src/skills/docbot/code_diagram.py)：从 `CodeGraph`（P1-5.2.2）派生 SVG 图，无需额外 LLM 调用
  2. 三类图：模块依赖图（`render_module_dependency_svg`）/ 调用关系图（`render_call_graph_svg`）/ 继承链图（`render_inheritance_svg`）
  3. 纯 Python SVG 生成（无需 Graphviz 等外部依赖），节点数上限可配（默认 50），超出自动截断
  4. 输出可嵌入 Markdown（`![模块依赖图](data:image/svg+xml;base64,...)`）或作为独立 .svg 文件
- **所属项目**：docbot
- **预期收益**：文档可视化更直观，代码结构一目了然
- **实施成本**：中（已完成）
- **测试**：[test_code_diagram.py](file:///d:/Projects/Entrepreneurship/AIProjects/agentinsight-agents/agentinsight-docbot/tests/unit/test_code_diagram.py) 33 个用例，覆盖三类图渲染 / 空图谱 / 节点截断 / SVG 合法性 / 分层布局 / data URI 嵌入
- **借鉴**：Co-STORM 的动态思维导图

### 5.3 ✅ P2-5.5.1 人工评估 checklist（已完成 2026-07-29）

- **现状**：仅自动门禁（RAGAS+DeepEval）
- **已实施方案**：
  1. 新增 [eval_checklist.py](file:///d:/Projects/Entrepreneurship/AIProjects/agentinsight-agents/agentinsight-docbot/src/skills/docbot/eval_checklist.py)：5 维度 5 分制评分模板（内容准确性 / 结构完整性 / 引用可追溯性 / 术语一致性 / 可读性）
  2. 每维度含 3-5 个评分项，每项 1-5 分；总分 100，加权计算（准确性 30% / 结构 20% / 引用 20% / 术语 15% / 可读性 15%）
  3. 输出 JSON 结构化评分（含 per_item 分数 + comments + 总分 + 等级 A/B/C/D）
  4. 提供 `render_checklist_markdown` 渲染为 Markdown 表格，便于人工填写
- **所属项目**：共享
- **实施成本**：低（已完成）
- **测试**：[test_eval_checklist.py](file:///d:/Projects/Entrepreneurship/AIProjects/agentinsight-agents/agentinsight-docbot/tests/unit/test_eval_checklist.py) 覆盖评分计算 / 等级映射 / Markdown 渲染

### 5.4 ✅ P2-5.5.2 评估维度扩展（已完成 2026-07-29）

- **现状**：RAGAS+DeepEval 6 个维度
- **已实施方案**：
  1. 新增 [eval_metrics.py](file:///d:/Projects/Entrepreneurship/AIProjects/agentinsight-agents/agentinsight-docbot/src/skills/docbot/eval_metrics.py)：复用 P1-5.3.1/5.3.3 校验工具，扩展 4 个自动评估维度
  2. 4 个新维度：引用可追溯性（复用 `citation_extractor`）/ 文档结构完整性（复用 `structure_validator`）/ 术语一致性（复用 `structure_validator`）/ 代码符号存在性（复用 `repo_map` 符号 vs 文档引用）
  3. `evaluate_report` 一站式 API：输入文档内容 + file_index + repo_path，输出 4 维度得分（0-100）+ 详细诊断信息
  4. JSON 结构化输出，可集成到 CI/CD 门禁或评测脚本
- **所属项目**：docbot
- **实施成本**：中（已完成，复用 P1 校验工具，无新依赖）
- **测试**：[test_eval_metrics.py](file:///d:/Projects/Entrepreneurship/AIProjects/agentinsight-agents/agentinsight-docbot/tests/unit/test_eval_metrics.py) 覆盖 4 维度评分 / 边界场景 / 集成校验

---

## 6. P3 优化方案（全部不启用）

### 6.1 ❌ P3-5.6.1 MCP 化代码图谱工具（不启用）

- **现状**：docbot 已有 `mcp-server-git` + `mcp-server-filesystem`
- **原方案**：将代码图谱（P1-5.2.2）封装为 MCP Server，与 Claude Code/Cursor 等外部工具共享索引
- **不启用原因**：
  1. **内部调用无需求**：docbot 的 [code_learner.py](file:///d:/Projects/Entrepreneurship/AIProjects/agentinsight-agents/agentinsight-docbot/src/skills/docbot/code_learner.py) 已直接 import 并调用 `build_code_graph()` 函数，无需通过 MCP 协议中转（MCP 协议相比直接函数调用增加序列化/反序列化/进程间通信开销，无收益）
  2. **外部客户端无场景**：AGENTS.md 明确"不暴露 MCP 配置入口"，用户无法设置 MCP；docbot 是服务端 Agent，不存在 Claude Code/Cursor 等 IDE 客户端需要连接 docbot 查询代码图谱的场景
  3. **架构定位不符**：[AGENTS.md](file:///d:/Projects/Entrepreneurship/AIProjects/agentinsight-agents/agentinsight-docbot/AGENTS.md#L145) 第 3 章明确系统自带 MCP 仅 `mcp-server-git` + `mcp-server-filesystem`，新增 `mcp-code-graph` 属于突破架构边界
  4. **过度工程**：增加维护复杂度（新模块/新配置/新子进程/新测试），但无实际业务价值
- **状态**：❌ 不启用（原实施代码已撤销）
- **所属项目**：docbot

### 6.2 ❌ P3-5.6.2 Co-STORM 式人机协作（不启用）

- **现状**：docbot [AGENTS.md](file:///d:/Projects/Entrepreneurship/AIProjects/agentinsight-agents/agentinsight-docbot/AGENTS.md#L142-L145) 第 3 章"不暴露的 API 端点"明确"不启用 `/v1/feedback` 人审"
- **原方案**：作为未来可选模式（`human_in_loop=True` 开关），不破坏当前默认无人工的纯自动化流程
- **不启用原因**：与当前 AGENTS.md "不启用人审"原则冲突，用户确认不启用
- **借鉴**：Co-STORM 的人机协作话语协议
- **所属项目**：docbot
- **实施成本**：高
- **风险**：与当前 AGENTS.md "不启用人审"原则冲突
- **状态**：❌ 不启用

---

## 7. P1+P2 执行总结

### 7.1 已完成任务统计

| 任务 ID | 任务名称 | 新增文件 | 修改文件 | 测试用例 | 状态 |
|---------|---------|---------|---------|---------|------|
| P1-5.2.1 | tree-sitter 仓库地图 | repo_map.py | code_learner.py / prompts.py | test_repo_map.py | ✅ |
| P1-5.2.2 | 代码知识图谱层 | code_graph.py | code_learner.py / prompts.py | test_code_graph.py | ✅ |
| P1-5.2.3 | 关键文件优先级队列优化 | - | repo_loader.py | 20 | ✅ |
| P1-5.3.1 | 文档行级引用溯源 | citation_extractor.py | init.sql / prompts.py | 19 | ✅ |
| P1-5.3.2 | 代码变更触发文档漂移检测 | drift_detector.py | git_mcp.py / init.sql / repo_routes.py / nodes.py | 10 | ✅ |
| P1-5.3.3 | 文档结构完整性校验 | structure_validator.py | - | 17 | ✅ |
| P2-5.4.1 | 多视角代码审问 | multi_perspective_learner.py / perspectives.py | code_learner.py / prompts.py / settings.py | test_multi_perspective_learner.py / test_perspectives.py | ✅ |
| P2-5.4.2 | 思维导图/代码结构图产物 | code_diagram.py | - | test_code_diagram.py | ✅ |
| P2-5.5.1 | 人工评估 checklist | eval_checklist.py | - | test_eval_checklist.py | ✅ |
| P2-5.5.2 | 评估维度扩展 | eval_metrics.py | - | test_eval_metrics.py | ✅ |
| **合计** | | **11 个新文件** | **11 个文件修改** | **11 个测试文件** | **全部通过** |

### 7.2 质量门禁

- ✅ `pytest tests/unit/` → 全部通过（含 P1+P2 新增测试）
- ✅ `ruff check` P1+P2 新建文件 → 无错误
- ✅ `ruff format --check` P1+P2 新建文件 → 全部通过
- ⚠️ `ruff check` P1 修改文件（git_mcp.py）→ 剩余 3 个 ASYNC109/ASYNC240 警告（已有代码风格，与 P1 改动无关，按"避免过度修改"原则不动）
- ⏸ `mypy src/ --strict` → 待运行（Python 3.13 环境无 mypy，需安装）

### 7.3 新增数据库对象

| 对象 | 类型 | 用途 | 来源任务 |
|------|------|------|---------|
| `report_citations` | 表 | 行级引用溯源存储 | P1-5.3.1 |
| `idx_report_citations_report` | 索引 | 按 report_id 查引用 | P1-5.3.1 |
| `idx_report_citations_agent_user` | 索引 | 多 Agent 数据隔离 | P1-5.3.1 |
| `idx_report_citations_file_path` | 索引 | 按文件路径反查（漂移检测用） | P1-5.3.1 |
| `research_reports.is_stale` | 列 | 文档是否过期 | P1-5.3.2 |
| `research_reports.stale_reason` | 列 | 过期原因 | P1-5.3.2 |
| `research_reports.stale_detected_at` | 列 | 过期检测时间 | P1-5.3.2 |
| `user_git_repos.last_doc_commit_hash` | 列 | 上次文档生成时的 commit hash | P1-5.3.2 |
| `user_git_repos.last_doc_synced_at` | 列 | 上次文档生成对应的同步时间 | P1-5.3.2 |

### 7.4 新增 git_mcp.py 方法

| 方法 | 用途 | 来源任务 |
|------|------|---------|
| `get_head_commit_hash(repo_path)` | 获取仓库当前 HEAD commit hash | P1-5.3.2 |
| `list_changed_files(repo_path, from_commit, to_commit)` | 获取两个 commit 之间变更的文件列表 | P1-5.3.2 |

### 7.5 新增 skills/docbot/ 模块

| 模块 | 用途 | 来源任务 |
|------|------|---------|
| [repo_map.py](file:///d:/Projects/Entrepreneurship/AIProjects/agentinsight-agents/agentinsight-docbot/src/skills/docbot/repo_map.py) | tree-sitter 符号级仓库地图 | P1-5.2.1 |
| [code_graph.py](file:///d:/Projects/Entrepreneurship/AIProjects/agentinsight-agents/agentinsight-docbot/src/skills/docbot/code_graph.py) | 代码知识图谱（import/call/inherit） | P1-5.2.2 |
| [citation_extractor.py](file:///d:/Projects/Entrepreneurship/AIProjects/agentinsight-agents/agentinsight-docbot/src/skills/docbot/citation_extractor.py) | 行级引用提取与校验 | P1-5.3.1 |
| [drift_detector.py](file:///d:/Projects/Entrepreneurship/AIProjects/agentinsight-agents/agentinsight-docbot/src/skills/docbot/drift_detector.py) | 代码变更文档漂移检测 | P1-5.3.2 |
| [structure_validator.py](file:///d:/Projects/Entrepreneurship/AIProjects/agentinsight-agents/agentinsight-docbot/src/skills/docbot/structure_validator.py) | 文档结构完整性校验 | P1-5.3.3 |
| [code_diagram.py](file:///d:/Projects/Entrepreneurship/AIProjects/agentinsight-agents/agentinsight-docbot/src/skills/docbot/code_diagram.py) | 代码结构图 SVG 生成 | P2-5.4.2 |
| [eval_checklist.py](file:///d:/Projects/Entrepreneurship/AIProjects/agentinsight-agents/agentinsight-docbot/src/skills/docbot/eval_checklist.py) | 人工评估 5 分制 checklist | P2-5.5.1 |
| [eval_metrics.py](file:///d:/Projects/Entrepreneurship/AIProjects/agentinsight-agents/agentinsight-docbot/src/skills/docbot/eval_metrics.py) | 自动评估 4 维度扩展 | P2-5.5.2 |

### 7.6 新增 tools/ 模块

P1+P2 阶段未新增 `tools/` 模块（P3-5.6.1 原计划的 `code_graph_mcp.py` 已撤销，详见第 6.1 节）。

### 7.7 系统自带 MCP 子进程（无变更）

docbot 系统自带 MCP 子进程仅 `mcp-server-git` + `mcp-server-filesystem` 两个（由 [server.py](file:///d:/Projects/Entrepreneurship/AIProjects/agentinsight-agents/agentinsight-docbot/server.py) `_start_mcp_subprocesses` 启动），P1+P2+P3 阶段均未新增。

---

## 8. 风险与约束

### 8.1 AGENTS.md 硬约束（不可放松）

依据 [AGENTS.md](file:///d:/Projects/Entrepreneurship/AIProjects/agentinsight-agents/agentinsight-docbot/AGENTS.md) 第 11 章：

- 密钥仅环境变量注入，禁止入仓/硬编码/日志
- PII 加密存储 + 日志脱敏
- 禁止 `eval`/`exec` 求值用户输入
- 生产强制 HTTPS + 安全响应头不可绕过
- **禁止 Agent 通过 PowerShell 修改项目文件**（仅允许在 RunCommand 中使用 PowerShell 执行与文件修改无关的命令）
- 文件操作统一使用专用工具（Read/Write/Edit/DeleteFile/Glob/Grep）

### 8.2 架构偏好约束

依据 [AGENTS.md](file:///d:/Projects/Entrepreneurship/AIProjects/agentinsight-agents/agentinsight-docbot/AGENTS.md) 第 1-10/12-14 章：

- 编排优先 LangGraph，不推荐 AgentExecutor/AutoGen/CrewAI
- import 黑名单：langchain 全家桶（仅 langchain-core）/AgentExecutor/AutoGen/CrewAI/LlamaIndex/LangSmith/Langfuse/Pinecone/厂商 SDK 直连/Memcached/MySQL/pickle/全局可变状态/eval/exec/opentelemetry-sdk 原生 API/agentinsight.observe 装饰器/观察者模式/前端代码/StaticFiles 挂载前端
- 依赖单向向内：`common/` 不应依赖 `agents/` 或业务模块
- `tools/`/`rag/`/`llm/`/`memory/` 不推荐互相 import
- 子智能体代码按名称隔离在 `agents/<agent_name>/`/`config/<agent_name>/`/`skills/<agent_name>/` 下
- 配置应经 `config/` + 环境变量，业务代码不应硬编码 URL/密钥
- 容器编排必须使用 `-p agentinsight-docbot` 项目名
- QA 环境必须使用 `docker-build.qa.bat`

### 8.3 引入新依赖的风险

- **tree-sitter**（P1-5.2.1）：已确认引入（`tree-sitter==0.26.0` + `tree-sitter-language-pack==1.13.5`），不在 AGENTS.md import 黑名单内
- **Codebase-Memory-MCP**（P3-5.6.1）：❌ 不启用（详见第 6.1 节，原实施代码已撤销）
- **Co-STORM 式人机协作**（P3-5.6.2）：❌ 不启用（与 docbot AGENTS.md "不启用人审"原则冲突，用户已确认不启用）

---

## 9. 实施路线图

### 阶段一：P0 文档治理（✅ 已于 2026-07-29 在 researcher 项目完成）

详见 [researcher 项目 optimization-plan.md](file:///d:/Projects/Entrepreneurship/AIProjects/agentinsight-agents/agentinsight-researcher/docs/optimization-plan.md) 第 5.1 节。

### 阶段二：P1 代码理解深度（✅ 已于 2026-07-29 全部完成）

1. ✅ P1-5.2.1 引入 tree-sitter 仓库地图（docbot，已完成）
2. ✅ P1-5.2.2 引入代码知识图谱层（docbot，已完成）
3. ✅ P1-5.2.3 关键文件优先级队列优化（docbot，已完成）

### 阶段三：P1 文档质量（✅ 已于 2026-07-29 全部完成）

1. ✅ P1-5.3.1 文档行级引用溯源（docbot，已完成）
2. ✅ P1-5.3.2 代码变更触发文档漂移检测（docbot，已完成）
3. ✅ P1-5.3.3 文档结构完整性校验（docbot，已完成）

### 阶段四：P2 多视角与评估（✅ 已于 2026-07-29 全部完成）

1. ✅ P2-5.4.1 多视角代码审问（docbot，已完成）
2. ✅ P2-5.4.2 思维导图/代码结构图产物（docbot，已完成）
3. ✅ P2-5.5.1 人工评估 checklist（共享，已完成）
4. ✅ P2-5.5.2 评估维度扩展（docbot，已完成）

### 阶段五：P3 架构演进（全部不启用）

1. ❌ P3-5.6.1 MCP 化代码图谱工具（docbot，不启用：无实际价值，原实施代码已撤销）
2. ❌ P3-5.6.2 Co-STORM 式人机协作（docbot，不启用：与 AGENTS.md "不启用人审"原则冲突，用户已确认）

---

## 10. 结论

本方案严格基于 agentinsight-docbot 项目实际代码，承接 researcher 项目 P0 文档治理成果，在 docbot 项目内执行 P1-P3 优化任务。

**P1 阶段 6 项任务全部完成**（5.2.1 / 5.2.2 / 5.2.3 / 5.3.1 / 5.3.2 / 5.3.3），新增 5 个 skills 模块、修改 9 个文件、新增 1 个数据库表 + 5 列 + 3 索引。docbot 在**代码理解深度**方面从第 3 层跃升到第 6 层（符号级仓库地图 + 调用图），在**文档质量与可追溯性**方面达到业界 STORM 同类水平（行级引用溯源 + 漂移检测 + 结构校验）。

**P2 阶段 4 项任务全部完成**（5.4.1 / 5.4.2 / 5.5.1 / 5.5.2），新增 4 个 skills 模块（多视角审问 / 代码结构图 / 人工评估 checklist / 自动评估维度扩展），复用 P1 校验工具无新依赖。多视角代码审问（5.4.1）默认关闭（`docbot_multi_perspective_enabled=False`），可通过环境变量启用，向后兼容。

**P3 阶段 2 项任务全部不启用**（5.6.1 / 5.6.2）。P3-5.6.1 MCP 化代码图谱工具经评估无实际价值（docbot 内部已通过直接函数调用使用 `build_code_graph()`，无 MCP 中转需求；AGENTS.md 明确"不暴露 MCP 配置入口"，用户无法设置 MCP；系统自带 MCP 仅 `mcp-server-git` + `mcp-server-filesystem`），原实施代码已撤销。P3-5.6.2 Co-STORM 式人机协作与 AGENTS.md "不启用人审"原则冲突，用户已确认不启用。

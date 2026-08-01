# 全流水线性能优化方案（v1）

> **已有实证修订版**：请优先阅读 [`docs/optimization-plan-performance-v2.md`](./optimization-plan-performance-v2.md)（基于 ClickHouse Trace/Observation 修订）。本 v1 保留作推理过程存档。  
> **状态：本方案暂不实施。** 仅作研究结论与代码级设计建议；未经确认不得改动业务代码。  
> **硬约束**：方案保持通用，禁止硬编码任何特定产品/仓库业务事实。  
> **研究日期**：2026-07-31  
> **基准代码**：`agentinsight-docbot` 工作区当前源码（顶层图 / 报告子图 / skills / agents / llm / rag / settings）。  
> **参考文档**：`docs/architecture.md` §15/§16、`docs/optimization-plan.md`、`docs/optimization-plan-code-learning-v1.md`（本方案独立覆盖全流水线性能视角，不替代既有质量/侧重方案）。

---

## 0. 执行摘要

端到端文档生成的墙钟时间主要由四类瓶颈叠加：

| 瓶颈类别 | 典型占比（假设，待埋点验证） | 证据摘要 |
|----------|------------------------------|----------|
| **LLM 延迟** | 60–80% | 每报告：1×STRATEGIC 学习 + 1×STRATEGIC 纲要 + N×SMART 填章（可含重写）+ N×SMART 评审 + 1×SMART 终审；可选配图再加 SMART |
| **确定性分析 CPU** | 5–15%（大仓更高） | `build_code_graph` / `generate_repo_map` / `ast_search.*` / `search_domain_symbols` 同步扫仓；多报告类型重复执行 |
| **IO（Git / Redis / Qdrant / Embeddings）** | 10–25% | clone/pull、全量 `index_repo_to_qdrant`、每章 2 轮 RAG、章节语义去重 FastEmbed |
| **编排串行** | 放大上述延迟 | 报告子图 D/E 按章 LangGraph 循环串行；`fill_all_chapters_parallel` 已实现但未接入；`max_llm_concurrency` / `max_rag_concurrency` **仅配置未接线** |

**实测基线（仅作量级参考，非验收硬指标）**：同 session 双报告类型端到端约 **~1300s**（见 `docs/e2e-output/reports-meta-after-code-learning.json` 的 `elapsed_s`）。优化目标应改为「相对基线下降 % + p95」，并按仓库规模分档。

**Top 5 建议（性能）**：见文末 §9；实施优先级 P0→P2，**全部暂不实施**。

---

## 1. 流水线拆解与调用图

### 1.1 顶层图

```
START → coordinator_a → spawn_b_tasks → final_reviewer_g → save_reports → cleanup_repo → END
```

| 节点 | 文件 | 关键函数 | 主要成本 |
|------|------|----------|----------|
| `coordinator_a` | `src/graph/nodes.py` → `agents/docbot/coordinator.py` | `CoordinatorA.run` | DB 读仓 + AES 解密；CPU/IO 轻 |
| `spawn_b_tasks` | `src/graph/nodes.py` | `spawn_b_tasks_node` | `asyncio.gather` + `Semaphore(max_concurrent_reports)`；墙钟 ≈ 最慢子图 |
| `final_reviewer_g` | `src/graph/nodes.py` → `final_reviewer.py` | `review_and_finalize`（顶层） | 当前多为读缓存透传；**轻**（交叉评审未深做） |
| `save_reports` | `src/graph/nodes.py` | `save_reports_node` | Redis 读 + Postgres 写；可选 `update_last_doc_commit` |
| `cleanup_repo` | `src/graph/nodes.py` | `cleanup_repo_node` | `shutil.rmtree`（`asyncio.to_thread`） |

### 1.2 报告子图

```
b_init → c_code_learning → c_outline_refine
      → d_content_fill ⟲ (route_after_d: next_chapter|review)
      → e_review ⟲ (route_after_e: next_chapter|done；revise 边存在但路由不返回)
      → f_merge → g_final_in_subgraph → END
```

| 步骤 | 节点 / Skill / Agent | LLM | 非 LLM 重活 |
|------|----------------------|-----|-------------|
| 0 | `b_init_session` / `ReportRunnerB` | 无 | 生成 `llm_session_id` / `report_id` |
| 1 | `c_code_learning` / `learn_code` | STRATEGIC×1（或多视角 3×FAST+3×SMART+1×STRATEGIC） | clone、file_index、key files、code_graph、repo_map、metadata/glossary/AST/scopes/config、可选 Qdrant 索引 |
| 2 | `c_outline_refine` / `OutlineRefinerC.refine_outline` | STRATEGIC×1（失败可再×1 max_tokens=12288） | 读 AGENTS/README、YAML outline、骨架生成 |
| 3 | `d_content_fill` / `ContentFillerD.fill_chapter` | SMART×1+（引用重写≤2、幻觉重写、配图） | 2 轮 RAG、FastEmbed 去重、符号校验 |
| 4 | `e_review` / `ReviewerE.review_chapter` | SMART×1 / 章 | 每章重读 Redis `code_learning` |
| 5 | `f_merge` / `MergerF.merge_chapters` | **无**（已改为直接拼接） | 字符串拼接 / 去 PlantUML |
| 6 | `g_final` / `FinalReviewerG.finalize_single_report` | SMART×1 | 术语回滚、事实附录、结构/引用校验（CPU） |

### 1.3 并发与超时配置（现状）

| 配置 | 默认 | 实际使用情况 |
|------|------|--------------|
| `max_concurrent_reports` | 3 | ✅ `spawn_b_tasks_node` Semaphore |
| `max_revisions_per_chapter` | 3 | ⚠️ E 节点传入，但 `route_after_e` **不走 revise**；每章实质 1 次评审 |
| `max_chapters_per_report` | 20 | 调度侧约束 |
| `max_llm_concurrency` | 5 | ❌ **仅 Settings 字段，全仓无引用** |
| `max_rag_concurrency` | 10 | ❌ **仅 Settings 字段，全仓无引用** |
| `llm_timeout` | 120s | ✅ LiteLLM |
| `graph_total_timeout` | 3600s | ✅ 图级硬上限 |
| `embeddings_max_concurrent` | 3 | ✅ Embeddings 客户端 |
| `docbot_multi_perspective_enabled` | False | 默认关 |
| `docbot_cache_ttl` | 86400 | ✅ Redis 流水线缓存 |

---

## 2. 逐步瓶颈假设与优化项

> 每项格式：**瓶颈假设 → 证据 → 建议（文件/函数）→ 伪代码/补丁级 → 优先级 → 风险 → 验收**。  
> 优先级：P0（高收益/可控）/ P1 / P2（远期）。**全部标注暂不实施。**

---

### 2.0 顶层：`coordinator_a` / `spawn_b_tasks`

#### PERF-T0：多报告子图重复「克隆 + 确定性分析 +（近似）全量学习」

- **瓶颈假设**：N 个 `report_type` 并发跑 N 份 `learn_code`；`code_learning` 缓存键含 `report_type`（`cache.build_cache_key`），**同 session 同 repo 不同类型不共享确定性层结果**。clone 路径相同会 pull，但 AST/图谱/索引仍重复。
- **证据**：
  - `spawn_b_tasks_node`：每个 `report_type` 独立 `build_report_subgraph().ainvoke`
  - `c_code_learning_node`：`type_="code_learning"` + `report_type=...`
  - `learn_code` 步骤 1–4.x 在 STRATEGIC 之前全量同步执行
- **建议（暂不实施）**：
  1. 引入 **repo 级事实包缓存**（与 report_type 无关）：`type_=repo_facts` 或 `code_learning_shared`，键含 `agent_id/user_id/session_id/repo_id`（可选 commit hash）。
  2. `learn_code` 拆成 `analyze_repo_deterministic(...)` + `synthesize_learning(report_type, facts)`；多报告时 `asyncio.Lock` 单飞确定性分析，再按类型并发 STRATEGIC。
  3. Qdrant `index_repo_to_qdrant` 提到 spawn 前或单飞一次（见 PERF-C1）。
- **伪代码**：

```python
# spawn_b_tasks_node（示意，暂不实施）
facts_key = build_cache_key(..., type_="repo_facts", report_type="_shared", repo_id=repo_id)
async with repo_analyze_lock(repo_id):
    if not await read_cache(facts_key):
        facts = await analyze_repo_deterministic(repo_config, ...)
        await write_cache(facts_key, facts)

async def run_one(report_type):
    # c_code_learning 仅：读 facts + 按类型 STRATEGIC（或共享 summary + 类型增量）
    ...
```

- **优先级**：P0  
- **风险**：类型侧重（`learning_focus`）与共享 facts 的边界需清晰；缓存脏读需 commit hash。  
- **验收**：双报告墙钟相对基线 ↓ **25–40%**；确定性层 CPU 时间（span）≈ 1× 而非 N×。

#### PERF-T1：接线全局 `max_llm_concurrency`

- **瓶颈假设**：多报告 × 章节并行后，无全局 LLM 闸门会打满 provider 限流或拖垮本机；现状配置失效 → 要么无保护、要么无法调优。
- **证据**：`rg max_llm_concurrency` 仅命中 `settings.py`；`LLMClient.achat` 无 Semaphore。
- **建议（暂不实施）**：在 `LLMClient.achat` / `achat_stream` 入口 `async with self._sem`；`_sem = Semaphore(settings.max_llm_concurrency)` 懒创建于客户端单例。
- **补丁级**：

```python
# src/llm/client.py LLMClient.__init__ / get_llm_client
self._llm_sem = asyncio.Semaphore(int(settings.max_llm_concurrency))

async def achat(...):
    async with self._llm_sem:
        return await self._achat_with_fallback(...)
```

- **优先级**：P0（与章节并行配套）  
- **风险**：信号量过小拉长墙钟；过大仍触发 429。需与 `max_concurrent_reports` 联合调参。  
- **验收**：压力下 429 率 ↓；并发可控可观测（span metadata: `llm_sem_wait_ms`）。

#### PERF-T2：`final_reviewer_g` 顶层串行透传

- **瓶颈假设**：多报告时 `for task in report_tasks` 串行；若未来加重交叉评审 LLM，会成尾延迟。
- **证据**：`final_reviewer_g_node` 循环 `await reviewer.review_and_finalize`。
- **建议（暂不实施）**：`asyncio.gather`；交叉一致性单独一次 FAST/SMART 调用（可选）。
- **优先级**：P2  
- **风险**：低。  
- **验收**：报告数≥3 时顶层尾延迟 ↓。

---

### 2.1 任务一：`c_code_learning` / `learn_code`

#### PERF-C1：Qdrant 全量索引阻塞学习后半段

- **瓶颈假设**：`_ensure_qdrant_indexed` → `index_repo_to_qdrant` 在学习写缓存后同步触发；大仓「读全文件 + chunk + embed + upsert」可达数分钟，且多子图可能重复检查。
- **证据**：`report_nodes._ensure_qdrant_indexed`；`repo_loader.index_repo_to_qdrant` 对 `files` 顺序处理，batch=100。
- **建议（暂不实施）**：
  1. 索引与「STRATEGIC 学习」解耦：`asyncio.create_task` 后台索引，D 阶段 `await index_ready` 或降级 file_index（已有降级）。
  2. 或在 `spawn_b_tasks` 前单飞索引。
  3. 增量索引：按文件 mtime/hash 跳过未变 chunk（对齐 Continue 内容寻址思路，通用实现）。
- **优先级**：P0  
- **风险**：D 过早启动 RAG 空结果 → 已有 GROUNDING_EMPTY 降级，需测质量。  
- **验收**：学习节点 span 不含全量 embed；索引 p95 可并行隐藏；大仓（>500 文件）墙钟 ↓ **15%+**。

#### PERF-C2：确定性分析同步阻塞事件循环

- **瓶颈假设**：`build_code_graph` / `generate_repo_map` / `search_http_endpoints` / `search_domain_symbols`（rglob 至 800 文件）均在 async 函数内**同步**执行，阻塞 asyncio，拖慢同进程其他子图/SSE。
- **证据**：`code_learner.learn_code` 直接调用同步 API；`ast_search.search_domain_symbols` 默认 `max_files=800`。
- **建议（暂不实施）**：

```python
code_graph_obj = await asyncio.to_thread(build_code_graph, repo_path, file_index)
repo_map = await asyncio.to_thread(generate_repo_map, repo_path, file_index, code_graph=code_graph_obj)
# 同类：ast_search / metadata / glossary / scopes
```

- 进一步：同一 `to_thread` 内打包「图谱+地图+AST」减少调度次数；或进程池（大仓）。
- **优先级**：P0  
- **风险**：线程池打满；tree-sitter 是否线程安全需验证（parser 有模块缓存）。  
- **验收**：事件循环延迟指标改善；多报告并发时总墙钟 ↓ **5–15%**。

#### PERF-C3：`code_graph` / `repo_map` 重复解析同一批文件

- **瓶颈假设**：`build_code_graph` 与 `generate_repo_map` 各自 tree-sitter 解析（虽共享 parser 缓存，仍重复 parse 源码）。
- **证据**：二者独立遍历 `file_index`；`code_graph._DEFAULT_MAX_FILES=80`。
- **建议（暂不实施）**：单次 parse 产出 symbols → 同时喂图谱边提取与 repo_map 格式化。
- **优先级**：P1  
- **风险**：API 重构面较大。  
- **验收**：确定性层 CPU 时间 ↓ **30–50%**（同仓对比）。

#### PERF-C4：多视角默认关，开启后延迟×4–5

- **瓶颈假设**：`learn_code_multi_perspective`：3 视角并发 FAST 问 + SMART 答 + STRATEGIC 汇总；且再次 `generate_repo_map`。
- **证据**：`multi_perspective_learner.py`；settings 注释「成本约 4–5 倍」。
- **建议（暂不实施）**：保持默认关；若开启，复用上游已算好的 `repo_map`/`code_graph_text`（避免 L119 重复生成）；视角间共享 SMART 上下文截断策略见 Token 方案。
- **优先级**：P2（质量开关，非默认性能项）  
- **风险**：质量 vs 延迟权衡。  
- **验收**：开启时相对单视角墙钟倍数 ≤ 3.5（通过复用确定性层）。

#### PERF-C5：关键文件读取串行

- **瓶颈假设**：`read_files` 可能逐文件 MCP/磁盘读。
- **建议（暂不实施）**：有界并发 `Semaphore(8)` + `asyncio.gather`；大文件先截断再读。
- **优先级**：P1  
- **验收**：步骤3 IO 时间 ↓。

---

### 2.2 任务二：`c_outline_refine`

#### PERF-O1：STRATEGIC 纲要 + 解析失败重试

- **瓶颈假设**：一次失败 → `max_tokens=12288` 再调一次，尾延迟 +60–120s。
- **证据**：`OutlineRefinerC.refine_outline`。
- **建议（暂不实施）**：优先修 JSON schema / 降温度 / 关闭 thinking；骨架大纲足够时对「小 diff」报告跳过 LLM（规则：endpoints 章已由确定性骨架覆盖且 `refine_summary` 可选 FAST 校验）。
- **优先级**：P1  
- **风险**：跳过 LLM 可能降低纲要贴合度。  
- **验收**：纲要节点平均 LLM 调用次数 → 1.0–1.1；重试率 <10%。

#### PERF-O2：大纲节点读大段 AGENTS/README 进 STRATEGIC

- **瓶颈假设**：`agents_md[:50_000]` + `code_summary[:50_000]` 拉长 TTFT。
- **证据**：`outline_refiner.py`；`_read_repo_doc` 已截 20k，但 refine 侧再抬到 50k。
- **建议**：见 Token 方案 TOK-O1；性能侧同步缩短输入可降延迟。
- **优先级**：P1（与 Token 联动）

---

### 2.3 任务三：`d_content_fill`

#### PERF-D1（核心）：章节串行 LangGraph 循环，并行 API 未接入

- **瓶颈假设**：12 章 ×（SMART ~30–90s + RAG + 去重）串行可达 10–20+ 分钟；`ContentFillerD.fill_all_chapters_parallel`（Semaphore 默认 3）**已实现但全仓仅定义处命中**，`d_content_fill_node` 仍单章调用。
- **证据**：`report_builder` 条件边 `next_chapter → d_content_fill`；`fill_all_chapters_parallel` 仅在 `content_filler.py`。
- **建议（暂不实施）**：
  - **方案 A（推荐）**：`c_outline_refine` 之后单节点 `d_content_fill_all` 调用 `fill_all_chapters_parallel`，删掉 D 自环（或保留兼容开关）。
  - **方案 B**：保持图结构，但一次 node 填 `batch_size` 章。
  - 必须同时接线 `max_llm_concurrency`（PERF-T1）；去重已有 `_dedup_lock`，并行可用。
- **伪代码**：

```python
# report_builder（示意）
# c_outline_refine → d_content_fill_all → e_review_all → f_merge
async def d_content_fill_all_node(state, settings):
    filler = ContentFillerD(settings)
    results = await filler.fill_all_chapters_parallel(
        chapters=state["chapters"],
        ...,
        max_concurrent=min(3, settings.max_llm_concurrency),
    )
    # 批量 write_cache content_cache_keys
```

- **优先级**：P0  
- **风险**：Ask first（图结构变更，见 AGENTS.md）；并行写 Redis/去重竞态需测；RAG 打满 embeddings。  
- **验收**：单报告 12 章墙钟 ↓ **40–60%**（LLM 仍占主导时受 `max_concurrent` 限制，理想接近 ÷3）。

#### PERF-D2：每章双重 RAG（`_iterative_retrieve`）

- **瓶颈假设**：每章 2 次检索；多报告并发时 Qdrant/Embedding 排队。
- **证据**：`ContentFillerD._iterative_retrieve` → round1 `_retrieve_rag_context` + round2 符号扩展。
- **建议（暂不实施）**：
  1. 接线 `max_rag_concurrency`。
  2. 首轮命中分数高则跳过第 2 轮（阈值可配）。
  3. 章级 query 缓存（同 title+repo）。
- **优先级**：P1  
- **验收**：章均 RAG 调用 ↓ 20–40%；质量（引用有效率）不降。

#### PERF-D3：引用/幻觉重写放大尾延迟

- **瓶颈假设**：`citation` 最多重写 2 次 + 幻觉 `CONTENT_REFINE` 再一次 SMART，单章最坏 4× LLM。
- **证据**：`fill_chapter` / `_validate_and_rewrite_citations` / 幻觉分支。
- **建议（暂不实施）**：先确定性 strip/路径修复，仅当无效引用数 >K 才 LLM 重写；幻觉改 FAST 局部替换。
- **优先级**：P1  
- **风险**：质量下降。  
- **验收**：章均 LLM 调用 p50 ≤ 1.3；无效引用率不升。

#### PERF-D4：SVG 配图 `image_svg_max_tokens=16384`

- **瓶颈假设**：触发关键词的章节额外长输出 SMART/图像模型调用。
- **证据**：`settings.image_svg_max_tokens`；`_should_generate_image` + `_generate_image_for_chapter`。
- **建议（暂不实施）**：默认关或仅 architecture/design 首章；降 `max_tokens`；异步不阻塞正文缓存写入。
- **优先级**：P1  
- **验收**：配图章延迟可隐藏或 ↓50%。

#### PERF-D5：每章重复 `read_cache(code_learning)`

- **瓶颈假设**：N 章 × Redis 大 JSON 反序列化。
- **证据**：`d_content_fill_node` / `e_review_node` 每轮读全量。
- **建议（暂不实施）**：节点内/filler 实例缓存解析后的 dict；或 state 存压缩摘要 + 大字段仍 Redis。
- **优先级**：P2  
- **验收**：Redis GET 次数 ↓。

---

### 2.4 任务四：`e_review`

#### PERF-E1：评审串行且强制输出全文 `revised_content`

- **瓶颈假设**：N 章串行 SMART；即便 `needs_revision=false` 仍生成全文 → 延迟≈填章量级。
- **证据**：`ReviewerE.review_chapter`；`route_after_e` 仅 `next_chapter|done`。
- **建议（暂不实施）**：
  1. `e_review_all` 并行（同 PERF-D1）。
  2. 两阶段：先 FAST/SMART 只出 `needs_revision`+notes；true 时再改写（Token 方案详述）。
  3. 抽样评审（奇偶章或低置信章）——质量风险高，P2。
- **优先级**：P0（并行）+ P0/P1（两阶段，偏 Token）  
- **验收**：评审阶段墙钟 ÷2–3；全文改写率可观测。

#### PERF-E2：图上 `revise` 边死代码

- **瓶颈假设**：维护成本；未来误开 revise 会导致 D-E 爆炸延迟。
- **建议（暂不实施）**：文档化现状或删除未用边；若恢复多轮，必须硬上限 + 并行策略。
- **优先级**：P2

---

### 2.5 任务五 / 六：`f_merge` / `g_final`

#### PERF-M1：Merge 已无 LLM — 保持

- **现状**：`MergerF.merge_chapters` 直接拼接 — **正确的性能决策**。
- **建议**：勿轻易恢复 `MERGE_PROMPT` LLM；术语统一放终审/确定性替换。
- **优先级**：—（保持）

#### PERF-F1：终审 SMART + 大段后处理

- **瓶颈假设**：相对 D/E 较轻；后处理（附录、术语）CPU 通常可接受。
- **建议（暂不实施）**：后处理 `to_thread`；LLM 仅 title/summary 时可用 FAST（见 Token）。
- **优先级**：P2

---

### 2.6 支撑层：`repo_loader` / `git_mcp` / `rag` / `cache`

| ID | 项 | 建议摘要 | 优先级 |
|----|----|----------|--------|
| PERF-R1 | `index_repo_to_qdrant` 每文件 `GitMCPAdapter()` 新实例 | 循环外复用 adapter | P1 |
| PERF-R2 | Embeddings 批大小与并发 | 已有 `embeddings_max_concurrent=3`；索引阶段可独立调高（QA/CPU 环境慎） | P2 |
| PERF-R3 | clone 多子图竞态 | 同路径并行 clone/pull 加文件锁 | P1 |
| PERF-R4 | `cleanup_repo` 在 save 后删仓 | 若需再次生成同 session，被迫重 clone；可改为 TTL 延迟删 | P2 |
| PERF-R5 | Redis 大 value | code_learning 数百 KB；考虑拆键或压缩（msgpack/zstd） | P2 |

---

## 3. 建议实施顺序（仍暂不实施）

```text
P0-1  repo 级确定性事实单飞 + 可选共享 code_learning 骨架     (PERF-T0)
P0-2  章节填充/评审并行接入 fill_all_chapters_parallel         (PERF-D1/E1)
P0-3  LLMClient 接线 max_llm_concurrency                      (PERF-T1)
P0-4  Qdrant 索引后台化/单飞                                   (PERF-C1)
P0-5  确定性分析 asyncio.to_thread                             (PERF-C2)
P1    RAG 二轮短路、引用重写降频、配图策略、clone 锁、adapter 复用
P2    parse 合并、顶层 gather、缓存压缩、延迟清理仓库
```

**AGENTS.md 注意**：图结构变更（删 D/E 自环）属 ⚠️ Ask first。

---

## 4. 观测与验收框架（实施前先做，亦暂可不改代码）

建议在实施优化**之前**先加 span 字段（若单独开观测 PR）：

| 指标 | 来源 |
|------|------|
| `stage_elapsed_ms` | 各 `trace_chain` |
| `llm_call_count` / `llm_wait_ms` | `LLMClient` |
| `deterministic_cpu_ms` | learn_code 步骤 4.x |
| `qdrant_index_ms` / `rag_round_count` | index / retrieve |
| `chapter_parallelism` | D/E |

**验收场景（通用）**：

1. 小仓（<50 源文件）单报告、双报告  
2. 中仓（200–500）单报告 10–15 章  
3. 多报告（2–3 类型）并发  

**目标（相对同环境基线）**：

| 场景 | 目标墙钟下降 |
|------|--------------|
| 双报告中仓 | ≥ 30% |
| 单报告 12 章 | ≥ 40%（主要来自 D/E 并行） |
| 确定性层 CPU | N 报告时 ≈ 1× |

质量门禁不得放松：引用有效率、结构校验、既有 unit/e2e。

---

## 5. 风险总表

| 风险 | 缓解 |
|------|------|
| 图重构引入章节丢失 | 保留 content/reviewed cache 索引对齐测试 |
| LLM 限流 | 全局 Semaphore + 指数退避（已有 retries） |
| 并行去重漏检 | 保持 `_dedup_lock`；并行测相似度 |
| 后台索引未完成 | D 降级路径已存在；加 ready flag |
| tree-sitter 线程安全 | 单线程池 worker=1 或进程隔离验证 |

---

## 6. 与既有文档关系

| 文档 | 关系 |
|------|------|
| `optimization-plan.md` | 质量/能力建设（RepoMap/Graph/Citation）；本方案聚焦**耗时** |
| `optimization-plan-code-learning-v1.md` | 学习侧重/schema；与 PERF-T0 共享「facts 与类型合成分离」方向，但不实施 |
| `optimization-plan-token-v1.md` | 同伴文档；多处建议联动（评审两阶段、上下文裁剪） |

---

## 7. 明确声明

**本文件所有建议均暂不实施。** 不得据此直接改 `src/` 业务代码、不得 commit/push。落地需另开任务并遵守 AGENTS.md Ask-first 项。

---

## 8. 附录：关键文件索引

| 模块 | 路径 |
|------|------|
| 顶层图 | `src/graph/builder.py`, `nodes.py` |
| 子图 | `src/graph/report_builder.py`, `report_nodes.py`, `edges.py` |
| 学习 | `src/skills/docbot/code_learner.py`, `multi_perspective_learner.py` |
| 仓库 | `src/skills/docbot/repo_loader.py`, `code_graph.py`, `repo_map.py`, `ast_search.py` |
| 内容/评审 | `src/agents/docbot/content_filler.py`, `reviewer.py`, `merger.py`, `final_reviewer.py` |
| LLM | `src/llm/client.py`, `token_budget.py` |
| 配置 | `src/config/settings.py`, `config/docbot/learning_focus.py` |

---

## 9. Top 5 性能建议摘要

1. **多报告共享确定性事实包（单飞分析）**，避免 N× AST/图谱/索引。  
2. **接入已有 `fill_all_chapters_parallel`（及评审并行）**，打破 D/E 章级串行。  
3. **`LLMClient` 真正使用 `max_llm_concurrency`**，使并行可调可控。  
4. **Qdrant 全量索引后台化/单飞**，移出关键路径。  
5. **确定性分析 `asyncio.to_thread`**，避免阻塞事件循环。

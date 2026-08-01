# 全流水线性能优化方案（v2）

> **状态：方案文档；是否实施另议。** 未经确认不得改动业务代码。  
> **修订依据**：基于 ClickHouse 实证修订（AgentInsight traces / observations，近 24h `name=agentinsight-docbot`）。  
> **硬约束**：方案保持通用，禁止硬编码特定产品/仓库业务事实；**禁止**在本文写入任何观测后端凭据。  
> **研究日期**：2026-07-31  
> **前一版**：`docs/optimization-plan-performance-v1.md`（以静态代码推理为主；本版以实测为准，下调无证据项）。  
> **同伴文档**：`docs/optimization-plan-token-v2.md`

---

## 0. 执行摘要（数据结论）

端到端墙钟（双报告 `requirements`+`api_doc`，完整跑通）约 **1160–1800s**；主样本 `trace_id=0753e660836080ed05445956488310f9`：**1317s**（与本地 `docs/e2e-output/reports-meta-after-code-learning.json` 的 `elapsed_s≈1317` 一致）。

| 瓶颈类别 | v1 假设占比 | **实证结论** | 证据 |
|----------|-------------|--------------|------|
| **章级串行 LLM（填章+评审）** | 「编排串行放大」 | **证实为墙钟主因** | 单报告类型内 `sum(chain_ms)≈wall_ms`（requirements 填章 659≈659；api_doc 填章 418≈418；评审同理） |
| **冷路径 Git clone/pull 竞态** | PERF-R3 P1 | **升级：可靠性+性能 P0** | 双报告各调 1 次 clone；冷仓单次 ~150–200s；多起 `index.lock` / `File exists` ERROR |
| **双报告重复 STRATEGIC 学习** | PERF-T0 P0 | **证实** | 同 trace 两类型 `prompt_tokens` 差仅 **10–11**；学习 CHAIN ~100–300s/类型 |
| **幻觉/refine 二次 LLM** | PERF-D3 P1 | **升级 P0** | 主样本 fill 相关 GENERATION 118 次中，extra 类 42 次，LLM 墙钟累加 **~622s** |
| **纲要 STRATEGIC** | PERF-O1/O2 | **中等证实** | 主样本 2× ~131–157s；偶发 retry |
| **Qdrant 全量索引** | PERF-C1 P0 | **条件成立：下调默认优先级** | 24h 仅 2/16 traces 出现 `docbot.repo.index_to_qdrant`（avg ~434s）；热路径常已跳过 |
| **确定性 AST/图谱 CPU** | PERF-C2/C3 5–15% | **本仓量级下调** | 学习 CHAIN 中 clone+LLM 已解释大部分；`build_file_index`/`read_files` 仅数秒级 |
| **顶层 final_reviewer_g** | PERF-T2 P2 | **证伪为瓶颈** | 终审 GENERATION ~3–8s，可忽略 |
| **Merge LLM** | 已无 LLM | **保持正确** | merge CHAIN ~0s |

**Token 侧墙钟耦合**：填章 prompt 极大（见 Token v2）→ TTFT/总延迟同步升高；减输入亦减墙钟。

**Top 5（性能，按实证 ROI）**：见 §9。**全部暂不实施。**

---

## 1. 数据样本与规模

### 1.1 ClickHouse 对象（只读查询）

| 对象 | 用途 |
|------|------|
| `traces` | 根 Trace：`name`、`timestamp`、`metadata`（含 `repo_id`/`report_types`/`session_id`） |
| `observations` | 步骤：`type`（AGENT/CHAIN/GENERATION/TOOL/RETRIEVER/EMBEDDING）、父子、`usage_details`（`prompt_tokens`/`completion_tokens`/`total`）、耗时 |
| 另有 | `analytics_*`、`scores`、`tracemetrics` 等（本次主用 `traces`+`observations`） |

### 1.2 近 24h 规模（查询窗口）

| 指标 | 值 |
|------|-----|
| `traces` 总行（全 name） | ~310 |
| `agentinsight-docbot` 根 Trace | **16** |
| 关联 observations | **5657**（~255 个不同 name；GENERATION ~1050；ERROR 13） |
| 完整双报告（填章链≥20 且评审链≥20） | 约 5–7 条可用于聚合 |

### 1.3 主样本（完整双报告）

| 字段 | 值 |
|------|-----|
| `trace_id` | `0753e660836080ed05445956488310f9` |
| `report_types` | `["requirements","api_doc"]` |
| `repo_id` | `27931af443c241ecbf57745acedb23ff` |
| E2E | **1316.7s**（`spawn_b_tasks` ≈1313s） |
| GENERATION 次数 | 154 |
| Token 合计 | **4,839,666** |

其他完整双报告 E2E 参考：`559b4360…` 1162s；`3134d475…` 1609s；`cae7c9d2…` 1800s；`813866c6…`（architecture+api_doc）1817s。

---

## 2. 流水线实证时间线（主样本）

### 2.1 顶层

`AGENT agentinsight-docbot` ≈ 墙钟；几乎全部落在 `docbot.spawn_b_tasks`。`save`/`cleanup`/`顶层 final` 可忽略。

### 2.2 任务一 / 二（两子图并发）

| 步骤 | 观测名 | 耗时量级 | 备注 |
|------|--------|----------|------|
| clone×2 | `docbot.git.clone_repo` | 各 ~196s（冷） | 并行打同一目录 → 锁冲突风险 |
| 学习 CHAIN | `docbot.code_learning.{type}` | ~296 / ~314s | 含 clone 重叠 |
| 学习 LLM | 同名 GENERATION | ~92 / ~106s | STRATEGIC `deepseek-v4-pro`；prompt≈75155/75165 |
| 纲要 | `docbot.outline_refine.{type}` | ~157 / ~131s | 与 LLM 几乎重合 |

### 2.3 任务三 / 四（章级串行；报告类型间并发）

| 报告类型 | 填章 CHAIN | sum≈wall | 评审 CHAIN | sum≈wall |
|----------|------------|----------|------------|----------|
| requirements | 10 章，sum **658.6s** | wall **659s** | 10，**198s** | **199s** |
| api_doc | 20 章，sum **417.5s** | wall **418s** | 20，**328s** | **328s** |

**结论**：子图内 D/E **完全串行**；`fill_all_chapters_parallel` 未接入的假设 **完全证实**。双报告并发只能让「较慢子图」决定尾巴，无法吃掉章内串行。

### 2.4 填章二次调用（主样本 GENERATION 分桶）

| bucket | calls | LLM 时间累加 | 说明 |
|--------|------:|-------------:|------|
| content_fill 主调用 | 76 | ~629s | 主生成 |
| fill_rewrite（hallucination/refine 等） | 42 | **~622s** | **与主生成同量级** |
| review | 30 | ~526s | 章串行 |
| outline | 2 | ~288s | |
| code_learning | 2 | ~198s | |
| final | 2 | ~7s | |

> 注：LLM 时间累加可跨子图重叠，不能直接相加得墙钟；但 rewrite 与主填章在**同章串行链路内**叠加，直接拉长章延迟。

---

## 3. 假设对照表（v1 → v2）

| ID | v1 判断 | 实证 | v2 动作 |
|----|---------|------|---------|
| PERF-D1 章并行 | P0 假设 | **强证实** | **保持 P0，强化** |
| PERF-E1 评审并行 | P0 | **强证实**（sum≈wall） | **保持 P0** |
| PERF-T0 共享 facts/学习 | P0 | **强证实**（prompt Δ≈10） | **保持 P0** |
| PERF-R3 clone 锁 | P1 | **ERROR 实证** | **升 P0** |
| PERF-D3 重写放大 | P1 | **42 次/~622s LLM** | **升 P0** |
| PERF-T1 max_llm_concurrency | P0 | 代码仍未接线；并行后必需 | **保持 P0（并行前置）** |
| PERF-C1 Qdrant 索引 | P0 | 多数 run 无 span | **改「冷仓 P0 / 热仓 P2」** |
| PERF-C2/C3 to_thread / 合并 parse | P0/P1 | 本样本非主导 | **降 P2**（大仓再升） |
| PERF-O1 纲要重试 | P1 | 有 retry 样本 | **保持 P1** |
| PERF-D2 双轮 RAG | P1 | RETRIEVER 存在但章均 ~0.5s | **降 P2**（墙钟次要） |
| PERF-D4 配图 | P1 | 主样本未见显著 image 桶 | **降 P2 / 按需** |
| PERF-D5 Redis 重读 | P2 | cache CHAIN 228 次但 sum ~0.3s | **维持 P2 或搁置** |
| PERF-T2 顶层 final | P2 | ~秒级 | **搁置** |
| PERF-F1 终审 | P2 | ~7s | **搁置** |
| PERF-M1 Merge 无 LLM | 保持 | 证实 | **保持** |

---

## 4. 代码级优化项（仅方案）

> 格式：**问题（实证）→ 改法（文件/函数）→ 优先级 → 风险 → 验收**。全部 **暂不实施**。

### 4.1 P0

#### PERF-D1 / PERF-E1：接入章级并行

- **问题**：`report_builder` D/E 自环导致 `sum≈wall`；`ContentFillerD.fill_all_chapters_parallel`（`content_filler.py`）已实现未调用。
- **改法**：
  1. `src/graph/report_builder.py`：outline 后改为单节点 `d_content_fill_all` → `e_review_all` → merge（⚠️ AGENTS.md Ask first：图结构变更）。
  2. `src/graph/report_nodes.py`：新节点调用 `fill_all_chapters_parallel`；评审侧对称实现 `review_all_chapters_parallel`（Semaphore）。
  3. 同步 `PERF-T1`。
- **验收**：同仓双报告 E2E 相对 1317s 基线 ↓ **≥35%**；单类型填章 wall ≪ 章耗时之和。

#### PERF-T1：接线 `max_llm_concurrency`

- **问题**：`settings.max_llm_concurrency` 仅定义于 `src/config/settings.py`，`LLMClient` 未使用。
- **改法**：`src/llm/client.py` 的 `achat` / `achat_stream` 入口 `asyncio.Semaphore`。
- **验收**：并行开启后 429 可控；span 可记 `llm_sem_wait_ms`（可选观测）。

#### PERF-T0：repo 级确定性事实 + 学习单飞/共享

- **问题**：双类型学习 prompt 几乎相同（Δ≈10 token），确定性分析与 clone 重复。
- **改法**：
  1. `src/skills/docbot/cache.py`：增加 `type_="repo_facts"` 键（含 `repo_id`+commit，**不含** report_type）。
  2. `src/skills/docbot/code_learner.py`：`analyze_repo_deterministic` 与 `synthesize_learning(report_type, facts)` 拆分；`spawn_b_tasks` 或学习入口 `asyncio.Lock` 单飞。
  3. 可选：公共 STRATEGIC 一次 + 类型增量 FAST/SMART（与 Token TOK-S0 联动）。
- **验收**：双报告学习 CHAIN CPU/IO ≈1×；墙钟 ↓ **15–30%**（视 clone 是否已热）。

#### PERF-R3：同路径 clone/pull 文件锁 + 干净工作树策略

- **问题**：观测 ERROR：`index.lock` File exists、untracked overwrite、concurrent clone 同目录。
- **改法**：`src/tools/git_mcp.py`（或 `repo_loader` 封装处）对 `temp/repos/{user_id}/{repo_id}` 加 **进程内+跨进程文件锁**；pull 前处理脏树（reset/clean 策略需产品确认）；失败重试有界。
- **验收**：双报告并发 0 clone ERROR；冷 clone 次数 ≤1/repo/session。

#### PERF-D3：降低 hallucination / refine 串行二次 LLM

- **问题**：主样本 29× hallucination_rewrite + 15× refine，LLM 累加与主填章同量级。
- **改法**（`content_filler.py`）：
  1. 优先确定性修复（已有 `_strip_invalid_citations` 等）后再决定是否 LLM。
  2. 阈值：无效引用数 / 幻觉分数超过 K 才触发；否则跳过。
  3. 局部替换用更短 prompt / FAST（见 Token v2），避免整章 `CONTENT_REFINE_PROMPT` 重放。
  4. span 已有 `docbot.content_fill.hallucination_rewrite.{idx}` / `refine`——保留并加 `skipped_reason` metadata。
- **验收**：章均 GENERATION ≤ ~1.3；E2E 填章阶段 ↓ **20%+**；质量门禁不降。

### 4.2 P1

#### PERF-O1：纲要解析失败重试收敛

- **文件**：`src/agents/docbot/outline_refiner.py` `refine_outline`
- **改法**：修 JSON/schema；重试改为续写而非整 prompt 重放；监控 `*.retry` GENERATION 率。
- **验收**：重试率 <10%。

#### PERF-C1'：Qdrant 索引（仅冷仓）

- **文件**：`report_nodes._ensure_qdrant_indexed` / `repo_loader.index_repo_to_qdrant`
- **改法**：spawn 前单飞或后台 `create_task`；热仓保持跳过。
- **验收**：冷仓索引不阻塞 STRATEGIC；热仓路径无回归。

### 4.3 P2 / 搁置

| ID | 说明 |
|----|------|
| PERF-C2/C3 | 大仓再评估 `to_thread` / 单次 parse |
| PERF-D2 | RAG 二轮对墙钟贡献小（章均 retriever ~0.5s） |
| PERF-D4/D5/T2/F1 | 数据未显示主导 |
| PERF-R1/R2/R4/R5 | 保持观察；R1 adapter 复用仍属小优化 |

---

## 5. 建议实施顺序（仍暂不实施）

```text
P0-1  clone/pull 同目录锁 + 脏树策略              (PERF-R3)   ← 可靠性
P0-2  章填/评审并行 + max_llm_concurrency         (D1/E1/T1) ← 墙钟最大杠
P0-3  降 hallucination/refine 触发与上下文         (D3)       ← 章延迟+Token
P0-4  repo_facts 单飞 + 学习去重                   (T0)
P1    纲要重试收敛；冷仓索引单飞
P2    大仓确定性 CPU；RAG/配图等
```

---

## 6. 观测缺口（可选，非实施优化本身）

当前 span **已足够**支撑本次结论；若需更细拆分 deterministic CPU，可在 `learn_code` 步骤打 `deterministic_cpu_ms` / `clone_ms` / `strategic_ms`（经 `observability/tracing.py`）。**本次未加业务日志、未另跑 E2E。**

验收场景：同 `repo_id`、同 `report_types`、对比 `trace_id` 级 E2E 秒数与章 wall/sum 比。

---

## 7. 风险

| 风险 | 缓解 |
|------|------|
| 图重构丢章 | 缓存 key 索引单测 + e2e 章节数断言 |
| 并行打满 LLM | 全局 Semaphore |
| clone clean 丢本地改动 | 仅清理 Agent 写入的临时脏文件；策略需确认 |
| 少 rewrite 损质量 | 阈值 + 引用有效率门禁 |

---

## 8. 明确声明

**本文件所有建议均暂不实施。** 不得据此直接改 `src/`、不得 commit/push。落地需另开任务并遵守 AGENTS.md（图结构变更 Ask first）。

---

## 9. Top 5 性能建议摘要（实证版）

1. **打破 D/E 章级串行**（接入已有并行 API + 评审并行）。  
2. **同 repo 路径 Git 单飞/加锁**，消灭双 clone 竞态 ERROR 与冷路径双倍 IO。  
3. **压制填章 hallucination/refine 二次 LLM**（同章串行叠加已与主生成同量级）。  
4. **多报告共享 repo_facts / 去重 STRATEGIC 输入**（prompt Δ≈10 已说明重复）。  
5. **接线 `max_llm_concurrency`**，作为并行可降落的闸门。

---

## 10. 附录：关键文件

| 模块 | 路径 |
|------|------|
| 子图 | `src/graph/report_builder.py`, `report_nodes.py`, `edges.py` |
| 填章/并行 | `src/agents/docbot/content_filler.py`（`fill_all_chapters_parallel`） |
| 评审 | `src/agents/docbot/reviewer.py` |
| 学习/缓存 | `src/skills/docbot/code_learner.py`, `cache.py` |
| Git | `src/tools/git_mcp.py` |
| LLM | `src/llm/client.py` |
| 配置 | `src/config/settings.py` |

# 性能 / Token 优化前后对比报告（v2 P0 落地）

> 对比场景：同 `repo_id=27931af443c241ecbf57745acedb23ff`，`report_types=["requirements","api_doc"]`，`language=zh`。  
> Before：主样本 ClickHouse `trace_id=0753e660836080ed05445956488310f9` + `docs/e2e-output/reports-meta-after-code-learning.json`。  
> After：E2E `session_id=6e184c87-d98f-442a-990b-6be5dd83e5a1`，`trace_id=788d5c59be118809ca0d3d052556824e`。  
> 结构化基线：`perf-token-before.json` / `perf-token-after.json`。

---

## 1. 总体提升

| 指标 | Before | After | 提升 |
|------|-------:|------:|-----:|
| 墙钟耗时 (E2E) | **1317.1 s** | **720.6 s** | **↓ 45.3%** |
| 总 tokens (`sum(usage_details.total)`) | **4,839,666** | **2,995,349** | **↓ 38.1%** |
| prompt tokens | ~4.3M（估） | 2,764,278 | ↓ |
| completion tokens | ~0.5M（估） | 231,071 | ↓ |
| GENERATION 次数 | 154 | 166 | +7.8%（评审两阶段拆分导致调用次数↑，但每调用更短） |

**结论**：P0 落地后，双报告 E2E 墙钟接近腰斩，总 Token 下降约四成；与方案验收目标（墙钟 ≥35%、Token ≥35%）对齐。

---

## 2. 分步骤耗时对比

| 步骤 | Before（实证） | After（CHAIN wall / 备注） | 提升 |
|------|----------------|---------------------------|------|
| Git clone | 2× ~196s，有 `index.lock` ERROR | **1× 195.6s，0 ERROR** | 冷仓墙钟不重复；可靠性达标 |
| code_learning | CHAIN ~296/314s；LLM ~92/106s；两类型近乎拷贝 | CHAIN wall **277s**（两子图重叠）；LLM：requirements STRATEGIC 59s + api_doc **adapt 15.5s** | 学习墙钟 ↓ ~10–15%；二次 STRATEGIC 消除 |
| outline | ~157 / ~131s | wall **131s** | 约持平偏优（输入压缩后 prompt ↓） |
| content_fill | requirements wall **659s**≈sum；api_doc **418s**≈sum | **fill_all wall 192s**，章 sum **1002s**（并行生效） | 填章墙钟相对慢子图 **↓ ~54–71%** |
| review | requirements **199s**≈sum；api_doc **328s**≈sum | **review_all wall 157s**，章 sum **665s** | 评审墙钟相对慢子图 **↓ ~21–52%** |
| fill_extra LLM 累加 | ~622s（hallucination+refine） | ~652s 累加（含 endpoint rewrite；**无 refine**） | refine 默认关闭；墙钟因并行被掩盖 |
| merge / final | ~0 / ~7s | merge ~0；final ~11s | 非瓶颈 |

> 说明：LLM 时间累加可跨章/跨子图重叠，不能直接加总成墙钟；以 CHAIN `wall_s` 与 E2E 为准。

---

## 3. 分步骤 Token 对比

| 分桶 | Before total | After total | 提升 |
|------|-------------:|------------:|-----:|
| 填章主 GENERATION | 3,271,863（67.6%） | 2,399,549（80.1%） | **↓ 26.7%** |
| 填章 extra（hallucination/refine/rewrite） | 803,650（16.6%） | 304,076（10.2%） | **↓ 62.2%** |
| 评审 | 411,247（8.5%） | 117,775（3.9%） | **↓ 71.4%** |
| 纲要 | 175,770（3.6%） | 75,180（2.5%） | **↓ 57.2%** |
| 学习 | 164,957（3.4%） | 84,268（2.8%） | **↓ 48.9%** |
| 终审 | 12,179（0.3%） | 14,501（0.5%） | ~持平 |
| **合计** | **4,839,666** | **2,995,349** | **↓ 38.1%** |

学习细节（TOK-S0 实证）：

| 调用 | prompt_tokens |
|------|-------------:|
| `docbot.code_learning.requirements`（首类型 STRATEGIC） | 69,831 |
| `docbot.code_learning.adapt.api_doc`（共享基线增量） | **6,495** |

评审（TOK-E1）：completion 总量显著下降（短 JSON 判定 + 仅少数章 rewrite）。

---

## 4. 质量抽检（未崩溃）

- 两报告均成功写出 `final_cache_key`，`spawn_b_tasks success_count=2`。
- After `api_doc` 摘要自称覆盖 **76 端点**；终审日志：`API 路径覆盖率 100.0%，追加完整清单 (78 端点)`。
- After `api_doc` `/api` 路径提及数 362 vs before 基线文档 302（未出现端点大面积丢失）。
- 终审有结构警告（个别 Controller 章过短、编号噪声），属已知合并/编号边角，**未触发「质量明显崩溃 → 最小修复再测」门槛**。

产物：

- `docs/e2e-output/requirements-perf-token-after.md`
- `docs/e2e-output/api_doc-perf-token-after.md`
- `docs/e2e-output/reports-meta-perf-token-after.json`

---

## 5. 已实施条目与改动文件

| ID | 内容 | 主要文件 |
|----|------|----------|
| PERF-D1 / E1 | 章级并行填章/评审（`d_content_fill_all` → `e_review_all`） | `report_builder.py`, `report_nodes.py`, `content_filler.py`, `reviewer.py` |
| PERF-T1 | `max_llm_concurrency` Semaphore 接线 | `llm/client.py`, `settings.py` |
| PERF-R3 | 进程内 + 跨进程 clone 锁；脏树 sanitize；单飞 clone | `git_mcp.py` |
| PERF-T0 / TOK-S0 | 共享 `code_learning_shared` + 类型 adapt | `code_learner.py`, `cache.py`, `report_nodes.py` |
| PERF-D3 / TOK-D4 | refine 默认关；幻觉阈值门控 + 局部重写 | `content_filler.py`, `settings.py` |
| TOK-D1 | `slice_facts_for_chapter` 章级事实切片 | `content_filler.py` |
| TOK-D5 | API 清单/概览章确定性表零 LLM | `content_filler.py` |
| TOK-E1 | 评审两阶段（judge / rewrite） | `reviewer.py` |
| TOK-O1 | 纲要输入压缩（summary/agents/example） | `outline_refiner.py` |
| TOK-C1/C2 | `strategic_context_tokens` + 按类型裁 facts | `settings.py`, `code_learner.py` |

---

## 6. 未实施 / 降级说明

| 项 | 原因 |
|----|------|
| PERF-O1 纲要续写重试 | P1；本次优先 P0 墙钟/Token |
| PERF-C1' 冷仓 Qdrant 单飞 | P1；本 run 热路径未成为瓶颈 |
| TOK-D2 Prompt 固定段拆分 | P1 |
| 接口级 `endpoint_hallucination_rewrite` 完全消除 | 仍存在（API 详情路径）；已门控整章幻觉与关闭 refine，extra ↓62%；进一步门控可作下一轮 |
| 填章主调用 avg_prompt 未达「↓≥40%」单指标 | 总 Token 与墙钟已达标；部分整章仍偏大，可继续收紧切片 |

---

## 7. 标识汇总

| 字段 | Before | After |
|------|--------|-------|
| trace_id | `0753e660836080ed05445956488310f9` | `788d5c59be118809ca0d3d052556824e` |
| session_id | `3e0a3495-99ac-4bf6-a150-e27ff99feee3` | `6e184c87-d98f-442a-990b-6be5dd83e5a1` |
| E2E 秒 | 1317.1 | 720.6 |
| 总 tokens | 4,839,666 | 2,995,349 |

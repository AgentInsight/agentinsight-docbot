# 全流水线 Token 用量优化方案（v2）

> **状态：方案文档；是否实施另议。** 未经确认不得改动业务代码。  
> **修订依据**：基于 ClickHouse 实证修订（`observations.usage_details`：`prompt_tokens` / `completion_tokens` / `total`）。  
> **硬约束**：通用方案；**禁止**写入观测后端凭据；代码路径不入仓密钥。  
> **研究日期**：2026-07-31  
> **前一版**：`docs/optimization-plan-token-v1.md`  
> **同伴文档**：`docs/optimization-plan-performance-v2.md`

---

## 0. 执行摘要（数据结论）

v1 叙事「头重 + 腰粗 + 尾肥（评审强制全文）」需修正为：

> **腰超粗（填章主调用 prompt）+ 腰部二次调用（hallucination/refine）+ 头中等（双学习近乎拷贝 + 纲要）+ 评审中等尾 + 终审可忽略。**

主样本 `trace_id=0753e660836080ed05445956488310f9`（requirements+api_doc，E2E ~1317s）Token 结构：

| 分桶 | total tokens | 占比 | 含义 |
|------|-------------:|-----:|------|
| 填章主 GENERATION | **3,271,863** | **67.6%** | 章 prompt 极大（常见 28k–100k+） |
| 填章 extra（hallucination/refine 等） | **803,650** | **16.6%** | v1 低估 |
| 评审 | **411,247** | **8.5%** | completion 仍偏大，但非最大项 |
| 纲要 STRATEGIC×2 | **175,770** | **3.6%** | |
| 学习 STRATEGIC×2 | **164,957** | **3.4%** | 两类型 prompt Δ≈**10** |
| 终审 | **12,179** | **0.3%** | |
| **合计** | **4,839,666** | 100% | |

完整双报告聚合（多 trace）：content_fill 主调用 avg_prompt ≈ **41.5k**；fill_extra avg_prompt ≈ **17.5k**；review avg_comp ≈ **3.8k**；学习单次 prompt 可见 **48k / 75k / 187k** 三档（随装配与预算而变），但**同 trace 两类型几乎相等**。

**Top 5（Token）**：见 §9。**全部暂不实施。**

---

## 1. 数据样本与规模

与 Performance v2 §1 相同数据源：

- 16 条 `agentinsight-docbot` traces / 5657 observations / ~1045 带 usage 的 GENERATION  
- usage 键：`prompt_tokens`、`completion_tokens`、`total`（非 `input`/`output`）  
- 主模型：学习/纲要 `deepseek/deepseek-v4-pro`；填章/评审/终审 `deepseek/deepseek-v4-flash`

### 1.1 填章主调用 prompt 分布（近 24h，排除 rewrite/refine/hallucination）

| p25 | p50 | p75 | p95 | avg | max | n |
|----:|----:|----:|----:|----:|----:|--:|
| 28818 | 28836 | 59158 | 102944 | 45537 | **131315** | 451 |

主样本可见单章：`api_doc` 章 prompt **~130k**；`requirements` 章 **~91k–110k**。这直接否定「填章输入约 1.5万–4万」的粗算下限叙事——**真实腰部远粗于 v1 估算**。

### 1.2 学习双类型几乎拷贝

| trace（节选） | prompts | Δ |
|---------------|---------|--:|
| `0753e660…` | 75165 / 75155 | 10 |
| `559b4360…` 等 | 187238 / 187227 | 11 |
| `813866c6…` | 48477 / 48466 | 11 |

→ **TOK-S0 为铁证**，非假设。

### 1.3 评审：有全文回写，但不是最大头

主样本 review：avg_prompt ≈ **10.1k**，avg_completion ≈ **3.6k**（p50_c≈3.1k）。  
说明 `revised_content` 仍在吐长文，但 **prompt 未到 v1 假设的「章全文+30k summary」量级的上限**（可能截断已部分生效，或章较短）。  
**TOK-E1 仍值得做**，杠杆次于 TOK-D1 / 填章二次调用。

---

## 2. 假设对照表（v1 → v2）

| ID | v1 | 实证 | v2 |
|----|----|------|-----|
| TOK-D1 章级事实切片 | P0 | **强证实**（章 prompt 28k–131k） | **升为第一优先** |
| TOK-D4 引用/幻觉局部化 | P0 | hallucination+refine **16.6%** total | **强化 P0**（与 PERF-D3） |
| TOK-S0 多报告共享学习 | P0 | prompt Δ≈10 | **保持 P0** |
| TOK-E1 评审两阶段 | P0「尾肥主叙事」 | 仅 **8.5%** total | **保持 P0 但下调叙事权重** |
| TOK-O1 纲要压缩 | P0 | 单次 prompt ~69k–91k | **保持 P0** |
| TOK-D5 api 清单零 LLM | P0 | 部分 api 章 CHAIN 无主 GENERATION（可能已走确定性） | **保持；补齐未覆盖章** |
| TOK-C1 tokenizer/预算 | P0 | 学习 prompt 跨 run 48k–187k 漂移 | **保持 P0** |
| TOK-C2 按类型裁 facts | P0 | 双类型输入几乎相同 → 裁剪未生效或无效 | **保持 P0** |
| TOK-D2 拆 Prompt 固定段 | P1 | 固定开销存在但难从 usage 拆出 | **保持 P1** |
| TOK-D3 RAG 块 | P1 | retriever 快；对 token 次要于 facts 注入 | **降 P2** |
| TOK-S1 temperature 缓存 | P1 | 无缓存命中字段可证 | **保持 P1（弱证据）** |
| TOK-F1 终审 FAST | P2 | 0.3% | **搁置** |
| TOK-M1 Merge 无 LLM | 保持 | 证实 | **保持** |
| 「评审使 SMART≈2×填章」 | 粗算 | **证伪**：填章(+extra) ≫ 2×评审 | **删除该粗算结论** |

---

## 3. 代码级优化项（仅方案）

### 3.1 P0

#### TOK-D1：章级事实切片（最大杠杆）

- **问题**：每章重复注入大体量 `code_summary` / endpoints / glossary / enums / metadata / config + 长 `CONTENT_FILL_PROMPT` → prompt p50~28k、p95>100k。
- **位置**：`src/agents/docbot/content_filler.py`（装配 user prompt 处；已有 `_filter_endpoints_for_chapter` 可扩展）、`src/config/docbot/prompts.py`。
- **改法**：

```python
def slice_facts_for_chapter(chapter, code_learning, report_type) -> dict:
    # 非 API 章：endpoints 清空或 Top-N 相关
    # glossary/enums：标题/key_points 命中子集
    # code_summary：3–6k 章相关摘录，禁止每章 50k 整段
```

- **验收**：填章主调用 avg_prompt ↓ **≥40%**；引用有效率不降。预期单次双报告 total ↓ **≥30%**。

#### TOK-D4 / 与幻觉 refine：禁止默认整章重放

- **问题**：`hallucination_rewrite.*`、`docbot.content_fill.refine` 在主样本贡献 ~80 万 tokens + 同量级延迟。
- **位置**：`content_filler.py`（`_build_hallucination_rewrite_prompt`、`CONTENT_REFINE_PROMPT` 调用处 ~L1953+）。
- **改法**：
  1. 阈值门控；优先确定性 strip。  
  2. 只送「问题段落 + 证据片段」，禁止再附全量 facts。  
  3. 能用 FAST 局部替换则不用 SMART 全文。
- **验收**：fill_extra total ↓ **≥60%**；触发率可观测。

#### TOK-S0：共享 repo_facts + 短类型合成

- **问题**：两类型 STRATEGIC 各 ~75k–187k prompt，Δ≈10。
- **位置**：`code_learner.py`、`cache.py`、`learning_focus.py`。
- **改法**：确定性 facts 缓存一次；STRATEGIC 只跑一次公共摘要，或第二次仅喂 `format_learning_focus` + 压缩 facts（目标第二次 prompt ≪ 第一次）。
- **验收**：双报告学习相关 tokens ↓ **≥45%**。

#### TOK-O1：纲要输入压缩

- **问题**：纲要 GENERATION prompt ~69k–91k，耗时 ~2–3min/类型。
- **位置**：`src/agents/docbot/outline_refiner.py`。
- **改法**：`code_summary`/`agents_md` 降至 8–12k；YAML 去掉长 `example`；已有骨架时输出 mutations patch。
- **验收**：纲要 prompt ↓ **≥50%**。

#### TOK-E1：评审两阶段（降权但仍做）

- **问题**：avg_completion ~3.6–3.8k，疑似稳定输出 `revised_content`。
- **位置**：`src/agents/docbot/reviewer.py`、`REVIEW_PROMPT`（`prompts.py`）。
- **改法**：先短 JSON 判定；`needs_revision=false` 时透传 D 产物；true 再改写或 patch。
- **验收**：评审 completion ↓ **≥50%**；总 token 再降 ~4–8pp。

#### TOK-C1 / TOK-C2：预算真源 + 按类型裁注入

- **问题**：学习 prompt 跨会话 48k–187k；类型间未分化。
- **位置**：`code_learner._apply_token_budgets`；Settings 补 `strategic_context_tokens`；`LEARNING_FOCUS_BY_TYPE.include_facts`。
- **验收**：学习 prompt p95 受控；类型间输入 Jaccard/字段差显著。

#### TOK-D5：api 清单章尽量零 LLM

- **位置**：`signature_extractor` / `_is_api_list_chapter` 路径。
- **说明**：观测中部分 api_doc 章仅有短 CHAIN、缺少大 GENERATION，说明部分路径已省 LLM；应审计仍走 130k prompt 的清单章并强制表格渲染。
- **验收**：api_doc 填章主调用次数与 avg_prompt 双降。

### 3.2 P1

| ID | 改法摘要 |
|----|----------|
| TOK-D2 | system 放全局约束，user 只放章变量；压缩 checklist |
| TOK-O2 | 纲要续写代替 12288 整prompt重试 |
| TOK-S1 | JSON 步骤 `temperature=0` 以提高响应缓存命中 |
| TOK-C3/C4 | key_files 焦点窗；多视角（若开启）截断 file_contents |
| TOK-E2 | 评审 code_summary 再压到 4–8k |

### 3.3 P2 / 搁置

TOK-D3 RAG 块、TOK-D7 章长度、TOK-E3 抽样评审、TOK-F1/F2 终审——数据占比过低或质量风险高，**不优先**。

---

## 4. Tier 与 max_tokens（修订）

| 步骤 | 实证模型 | 建议 |
|------|----------|------|
| 学习/纲要 | v4-pro | 保持 STRATEGIC；先减输入再谈降级 |
| 填章主 | v4-flash | 保持；优先切片 |
| 填章 rewrite | v4-flash | 改短上下文 / 可试 FAST |
| 评审判定 | v4-flash | 短 JSON；改写才长输出 |
| 终审 | v4-flash | 已很小，不动 |

`image_svg_max_tokens=16384`：主样本无显著 image token，**降优先级**。

---

## 5. 与质量权衡（不变原则 + 新强调）

1. **先砍重复注入与二次整章 LLM，再砍证据**。  
2. 确定性 API 表/术语附录继续后处理渲染。  
3. 少 rewrite 必须配引用/符号门禁，避免「省 token 放幻觉」。  
4. 禁止跨用户/跨仓上下文；禁止硬编码业务事实。

---

## 6. 优先级路线图（暂不实施）

```text
P0  TOK-D1 章级事实切片          ← 最大头（~68% tokens）
P0  TOK-D4 幻觉/refine 局部化     ← ~17% tokens + 性能
P0  TOK-S0 学习去重
P0  TOK-O1 纲要压缩
P0  TOK-C1/C2 预算与类型裁剪
P0  TOK-D5 补齐 api 零 LLM 表
P0  TOK-E1 评审两阶段（中等收益）
P1  Prompt 拆分 / 温度缓存 / 纲要续写
P2  RAG 块、抽样评审、终审微调
```

与 Performance v2 联动落地顺序建议：先 D1+D4（同时降 token 与章延迟），再并行图改造，再 S0/R3。

---

## 7. 验收指标（Token）

同模型、同 report_types、同量级章节数，对比 ClickHouse GENERATION usage：

| 指标 | 目标（相对主样本级基线） |
|------|--------------------------|
| 单次双报告 `sum(total)` | ↓ **35–50%** |
| 填章主调用 `avg(prompt_tokens)` | ↓ **≥40%** |
| fill_extra `sum(total)` | ↓ **≥60%** |
| 双类型学习 `sum(prompt)` | ↓ **≥45%** |
| 评审 `sum(completion)` | ↓ **≥50%**（若 TOK-E1） |
| 质量 | 引用有效率 / 结构校验 / 端点覆盖不劣于基线 |

以 LiteLLM/观测 `usage_details` 为准，不用 `len/4` 做最终验收。

---

## 8. 明确声明

**本文件所有建议均暂不实施。** 不得据此直接修改业务代码、不得 commit/push。

---

## 9. Top 5 Token 建议摘要（实证版）

1. **章级事实切片**：把填章 prompt 从 28k–130k 压到个位数 k～十余 k。  
2. **门控并局部化 hallucination/refine**：消灭占总量 ~1/6 的二次整章调用。  
3. **多报告学习去重**（prompt Δ≈10 的重复 STRATEGIC）。  
4. **纲要输入大幅压缩**。  
5. **评审两阶段**（有收益但不再宣传为「最大尾肥」）。

---

## 10. 附录：文件索引

| 项 | 路径 |
|----|------|
| Prompts | `src/config/docbot/prompts.py` |
| 填章/切片/重写 | `src/agents/docbot/content_filler.py` |
| 评审 | `src/agents/docbot/reviewer.py` |
| 学习预算 | `src/skills/docbot/code_learner.py` |
| Learning focus | `src/config/docbot/learning_focus.py` |
| Token 记账 | `src/llm/token_budget.py` |
| 性能同伴 | `docs/optimization-plan-performance-v2.md` |

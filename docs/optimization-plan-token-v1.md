# 全流水线 Token 用量优化方案（v1）

> **已有实证修订版**：请优先阅读 [`docs/optimization-plan-token-v2.md`](./optimization-plan-token-v2.md)（基于 ClickHouse usage 修订；纠正「评审≈2×填章」等粗算）。本 v1 保留作推理过程存档。  
> **状态：本方案暂不实施。** 仅作研究结论与代码级设计建议；未经确认不得改动业务代码。  
> **硬约束**：方案保持通用，禁止硬编码任何特定产品/仓库业务事实。  
> **研究日期**：2026-07-31  
> **基准代码**：`agentinsight-docbot` 工作区当前源码。  
> **同伴文档**：`docs/optimization-plan-performance-v1.md`（耗时视角）；`docs/architecture.md` §15/§16；`docs/optimization-plan-code-learning-v1.md`（学习侧重，与本方案 Token 裁剪互补）。

---

## 0. 执行摘要

Token 消耗呈「**头重（任务一 STRATEGIC 超长上下文）+ 腰粗（每章 SMART 重复注入事实层）+ 尾肥（评审强制回写全文）**」结构。

| 阶段 | Tier | 调用形态 | 输入特征 | 输出特征 |
|------|------|----------|----------|----------|
| 代码学习 | STRATEGIC | 1×/报告类型（或多视角 7×） | file_contents + repo_map + graph + 6 段 `*_text`，预算按 128k×0.6 字符近似 | JSON，`max_tokens`≈8192 |
| 纲要细化 | STRATEGIC | 1×（失败 +1） | code_summary≤50k + agents≤50k + 默认大纲 YAML | JSON 章节，8192/12288 |
| 内容填充 | SMART | ≥1×/章 | code_summary≤50k + RAG + endpoints≤12k + glossary≤8k + … + 超长约束正文 | Markdown，8192；重写叠加 |
| 评审 | SMART | 1×/章 | **全文 content + code_summary≤30k** | JSON 含 **revised_content 全文** |
| 合并 | — | 0 | 已跳过 LLM | — |
| 终审 | SMART | 1×/报告 | sections_summary（每节≤500字）+ code_summary≤5k | title/summary/建议；正文透传 |
| 配图 | image 模型 | 0–N× | 章节描述 | `image_svg_max_tokens=16384` |

**粗算（单报告 12 章，无多视角、无重写，仅数量级）**：

- 学习输入：可达 **5万–20万+ tokens**（字符/4 近似；预算函数按 128k 窗口切）  
- 纲要：输入数万 + 输出≤8k  
- 填章：12 ×（输入约 **1.5万–4万** + 输出≤8k）  
- 评审：12 ×（输入≈章长+7.5k + **输出≈章长**）← 常被低估  
- 终审：相对小  

→ 评审「原文进、原文出」可使 **SMART 总 token ≈ 接近 2× 填章**。

**Top 5 建议**：见 §9。**全部暂不实施。**

---

## 1. LLM 调用点全表（代码级）

| ID | 位置 | 函数 | Tier | max_tokens | Prompt 模板 |
|----|------|------|------|------------|-------------|
| L1 | `skills/docbot/code_learner.py` | `learn_code` | STRATEGIC | `strategic_token_limit`（8192） | `CODE_LEARNING_PROMPT` |
| L1b | `multi_perspective_learner.py` | `_generate_questions` | FAST | 默认 `fast_token_limit` | `MULTI_PERSPECTIVE_QUESTION_PROMPT` |
| L1c | 同上 | `_answer_questions` | SMART | 默认 | `MULTI_PERSPECTIVE_ANSWER_PROMPT`（含 `file_contents`） |
| L1d | 同上 | `_synthesize` | STRATEGIC | 默认/战略 | `MULTI_PERSPECTIVE_SYNTHESIS_PROMPT` |
| L2 | `agents/docbot/outline_refiner.py` | `refine_outline` | STRATEGIC | 8192 / 重试 12288 | `OUTLINE_REFINE_PROMPT` |
| L3 | `agents/docbot/content_filler.py` | `fill_chapter` / `_generate_with_retry` | SMART | 8192 | `CONTENT_FILL_PROMPT` / `API_ENDPOINT_CARD_PROMPT` |
| L3r | 同上 | 引用重写 / 幻觉重写 | SMART | 8192 | 内联 / `CONTENT_REFINE_PROMPT` |
| L3i | 同上 | `_generate_image_for_chapter` | image 配置模型 | 16384 | ImageGenerator |
| L4 | `agents/docbot/reviewer.py` | `review_chapter` | SMART | 8192 | `REVIEW_PROMPT` |
| L5 | `agents/docbot/merger.py` | `merge_chapters` | **无** | — | `MERGE_PROMPT` 闲置 |
| L6 | `agents/docbot/final_reviewer.py` | `finalize_single_report` | SMART | 8192 | `FINAL_REVIEW_PROMPT` |

**预算记账**：`LLMClient.achat` → `token_budget.TokenBudgetAllocator`（`max_total_tokens=128000` 默认偏研究场景；docbot 多章易超但 `check_budget=False` 仅记录）。

**响应缓存**：`llm_response_cache_enabled`，仅 `temperature=0`；docbot 默认 `temperature=0.4` → **缓存命中率预期低**。

---

## 2. 上下文装配与重复注入分析

### 2.1 任务一装配链（§16 对齐）

```
clone → file_index → select_key_files(30) → read_files
 → build_code_graph → generate_repo_map
 → metadata / glossary / endpoints / enums / scopes / config_specs
 → learning_focus(report_type) + output_schema_extra
 → _apply_token_budgets(...) → CODE_LEARNING_PROMPT.format
 → STRATEGIC
```

`_apply_token_budgets`（`code_learner.py`）：

- 读取 `strategic_context_tokens` / `context_max_tokens` — **Settings 中均不存在**，恒回落 **128_000**。
- `budget = 0.6 * ctx`；字符预算 `tokens * 4`；file_contents 另 `min(..., 500_000)`。
- 近似粗糙（中英混排、代码 token 密度更高）。

### 2.2 下游重复注入矩阵

| 字段 | 学习 | 纲要 | 填章 | 评审 | 终审 |
|------|------|------|------|------|------|
| `summary` / code_summary | 产出 | ≤50k | ≤50k | ≤30k | ≤5k |
| `key_modules` / `dependencies` | 产出 | 用 | 格式化注入 | 否 | 否 |
| `repo_map` | 注入学习 | 骨架/检索增强 | RAG query 用 | 否 | 符号校验用缓存 |
| `endpoints_text` | 注入 | 骨架 | ≤12k **每章** | 否 | 附录渲染（非 LLM） |
| `glossary_text` | 注入 | 部分 | ≤8k **每章** | 否 | 回滚（非 LLM） |
| `enums` / `config` / `metadata` | 注入 | 条件 | 每章截断注入 | 否 | 附录 |
| RAG chunks | — | — | 1–2 轮/章 | 否 | 否 |
| 章节全文 | — | — | 产出 | **全文 in+out** | 每节 500 字摘要 |

**核心浪费**：对「非 API 章」仍注入完整 `endpoints_text`；对「非术语敏感章」仍注入大 glossary；`code_summary` 在 12 章重复发送近乎同一 50k 字符块。

### 2.3 Prompt 固定开销

`CONTENT_FILL_PROMPT`（`prompts.py` ~L296+）含长篇路径/术语/反幻觉约束，**固定模板本身可达数千 tokens**，每章重复。`REVIEW_PROMPT` 要求始终输出 `revised_content`。

---

## 3. 逐步 Token 优化项

> 格式：**问题 → 证据 → 建议 → 伪代码/补丁级 → 质量权衡 → 优先级 → 验收（估算下降%）**。  
> **全部暂不实施。**

---

### 3.0 跨报告 / 会话级

#### TOK-S0：多 `report_type` 重复 STRATEGIC 学习

- **问题**：缓存键含 `report_type`，双报告 ≈ 2× 学习输入+输出；确定性 `*_text` 几乎相同，仅 `learning_focus` / schema 不同。
- **证据**：`cache.build_cache_key(..., type_="code_learning", report_type=)`；`learn_code` 全量装配。
- **建议（暂不实施）**：
  1. 共享 `repo_facts`（无 LLM）+ 每类型一次「短合成」STRATEGIC（只喂 focus + 压缩 facts + 少量关键文件）。
  2. 或：一次 STRATEGIC 产出公共四字段 + 按类型二次 FAST/SMART 填 `extra_json_fields`。
- **质量权衡**：类型侧重变弱风险 — 需保留 `format_learning_focus` / `format_extra_schema`（已有 `learning_focus.py`）。
- **优先级**：P0  
- **验收**：双报告学习相关 token ↓ **40–55%**；类型专属字段仍非空率达标。

#### TOK-S1：提高 LLM 响应缓存可用性

- **问题**：`temperature=0.4` 导致 Redis LLM 缓存基本不生效；纲要/评审等可降温度。
- **建议**：结构化 JSON 步骤用 `temperature=0`（学习/纲要/评审）；创作填章保持 0.3–0.4。
- **优先级**：P1  
- **验收**：同仓重跑缓存命中率 >30%（JSON 步骤）；token 账单 ↓。

---

### 3.1 任务一 Token

#### TOK-C1：用真实 tokenizer / 配置化 context 窗口

- **问题**：`token≈len/4` + 幽灵配置 `strategic_context_tokens`。
- **建议**：Settings 增加 `strategic_context_tokens`（默认按模型 128k/256k）；预算用 `tiktoken` 或 LiteLLM `token_counter`；file_contents 按文件优先级滴水截断（Aider 风格二分）。
- **优先级**：P0  
- **验收**：学习请求 `prompt_tokens` p95 可控；截断后 JSON 解析成功率不降。

#### TOK-C2：按 `report_type` 裁剪确定性层注入

- **问题**：8 类型共用全量 endpoints/enums/scopes 等。
- **建议**：扩展 `LEARNING_FOCUS_BY_TYPE`：`include_fact_keys: list[str]`；例如 testcase 偏 tests 路径与 exception，弱化完整 API 表；api_doc 强化 endpoints，弱化 deployment。
- **伪代码**：

```python
# learning_focus.py（示意）
"api_doc": {"include_facts": ["endpoints_text", "enums_text", "glossary_text", ...], ...}
"testcase": {"include_facts": ["scopes_text", "glossary_text", "config_specs_text"], ...}

# code_learner：format 前把未 include 的块置为 "(本类型省略，详见缓存事实包)"
```

- **质量权衡**：省略块可能导致该类型幻觉 — 应用「禁止编造 + insufficient_evidence」已有约束。
- **优先级**：P0  
- **验收**：学习输入 tokens 按类型 ↓ **20–40%**；api_doc 端点召回不降。

#### TOK-C3：降低 `select_key_files` / file_contents 冗余

- **问题**：`max_files=30` 整文件读入再截断；与 repo_map 签名重复。
- **建议**：对已在 repo_map 覆盖的文件只保留「焦点行窗」；或 max_files 按类型 15–25。
- **优先级**：P1  
- **验收**：file_contents 段 tokens ↓ 30% 且引用 path 仍有效。

#### TOK-C4：多视角 SMART 答卷截断 `file_contents`

- **问题**：3× SMART 各带全量 `file_contents`（`MULTI_PERSPECTIVE_ANSWER_PROMPT`）。
- **建议**：回答阶段只带 repo_map + 相关文件切片；提问阶段已不含正文（好）。
- **优先级**：P1（仅开启多视角时）  
- **验收**：多视角总 tokens 相对现状 ↓ **35%+**。

#### TOK-C5：STRATEGIC `max_tokens=8192` 与扩展 schema

- **问题**：`extra_json_fields` 变多时易截断→解析失败→兜底质量差或重试。
- **建议**：输出改「摘要 + 要点列表」；大字段（deployment_topology）改由确定性模板填充，LLM 只填缺口。
- **质量权衡**：正面（减少空话）；需验收类型字段。
- **优先级**：P1

---

### 3.2 任务二 Token

#### TOK-O1：压缩纲要输入

- **问题**：`code_summary[:50_000]` + `agents_md[:50_000]` + 完整 default outline 示例。
- **证据**：`outline_refiner.refine_outline`；`_read_repo_doc` 已 20k，format 又放宽。
- **建议**：
  - code_summary ≤ 8–12k；agents/readme ≤ 8k（与读盘一致）。
  - default outline 只传 `title/purpose/key_points`，去掉长 `example`。
  - 已有确定性骨架时，LLM 只输出 `mutations`（add/remove/replace）而非全量 chapters（patch 式）。
- **质量权衡**：patch 式解析更脆，需强 schema。
- **优先级**：P0  
- **验收**：纲要步骤 prompt_tokens ↓ **50%+**；章节数与 max_chapters 合规。

#### TOK-O2：取消/收敛 12288 重试

- **建议**：修截断根因；重试改「续写 JSON」而非整prompt重放。
- **优先级**：P1  
- **验收**：重试率 <10%；失败不双倍计费。

---

### 3.3 任务三 Token（最大腰部）

#### TOK-D1：章级「事实切片」替代全量 v9 块

- **问题**：每章注入 endpoints≤12k + glossary≤8k + enums≤8k + metadata≤4k + config≤4k + code_summary≤50k。
- **建议**：

```python
def slice_facts_for_chapter(chapter, code_learning, report_type) -> dict:
    # api 章：filter endpoints by controller/title（已有 _filter_endpoints_for_chapter）
    # 非 api 章：endpoints_text = "" 或 Top-5 相关
    # glossary：仅 chapter 标题/ key_points 命中的符号 + 品牌名短列表
    # code_summary：用学习 summary 的「章相关段落」或 key_modules 过滤后的 3–6k
```

- **优先级**：P0  
- **验收**：填章 prompt_tokens 章均 ↓ **35–55%**；引用有效率、品牌名回滚次数不恶化。

#### TOK-D2：拆分 CONTENT_FILL_PROMPT 固定约束

- **问题**：长约束每章重复。
- **建议**：system 消息一次放「全局写作法」；user 只放本章变量；或压缩为条目化短 checklist（目标 ≤800 tokens 固定部分）。
- **优先级**：P1  
- **验收**：固定开销 ↓ 60%；违规率（路径/PlantUML）不升。

#### TOK-D3：RAG 控制

- **问题**：2 轮检索，块 `content[:2000]` × Top5 × 2。
- **建议**：单轮 Top3；块 800–1200 字符；高分短路第二轮（与 PERF-D2 联动）。
- **优先级**：P1  
- **验收**：rag_context tokens ↓ 40%；GROUNDING_EMPTY 率不升。

#### TOK-D4：引用/幻觉重写改为局部编辑

- **问题**：重写常重发大上下文 + 全文输出。
- **建议**：只把无效引用列表 + 原段落交给 FAST 替换；或确定性 `strip`（已有 `_strip_invalid_citations`）优先。
- **优先级**：P0  
- **验收**：重写触发时 tokens ↓ 70%；无效引用残留率不升。

#### TOK-D5：api_doc 卡片路径

- **问题**：`API_ENDPOINT_CARD_PROMPT` 可能对多端点循环（需确认调用密度）。
- **建议**：清单章用 `signature_extractor.render_api_table` **零 LLM**；LLM 只写概述/认证章。
- **证据向**：`signature_extractor.py`、`_is_api_list_chapter` 已存在签名直填思路。
- **优先级**：P0（api_doc）  
- **验收**：api_doc 总 tokens ↓ **25–40%**；端点覆盖率不降。

#### TOK-D6：配图 max_tokens

- **建议**：`image_svg_max_tokens` 降至 4k–6k；或减少触发关键词。
- **优先级**：P1  
- **验收**：配图相关 completion ↓ 50%+。

#### TOK-D7：章长度指令

- **问题**：prompt 要求「每节 300–800 字、章 2000–5000 字」推高输出。
- **建议**：按章类型分级（概述 800–1500；详述 2000）；硬上限在 post 截断+提示。
- **质量权衡**：过短损信息密度。  
- **优先级**：P2  
- **验收**：completion_tokens 章均 ↓ 20%。

---

### 3.4 任务四 Token（高杠杆）

#### TOK-E1：评审两阶段 / 禁止无条件全文回写

- **问题**：`REVIEW_PROMPT` 要求 `revised_content` 始终输出 → 输出 tokens ≈ 输入章长。
- **建议**：

```json
// 阶段 A（每章）
{"needs_revision": false, "review_notes": "...", "score": 0.0}

// 仅当 needs_revision=true
// 阶段 B：输出 revised_content 或 JSON patch（search/replace）
```

- 若阶段 A 通过：`content_md` 直接透传 D 产物（零 completion 长文）。
- **质量权衡**：少一次改写可能保留 D 的小问题；可用确定性校验（citation/symbol）补位。
- **优先级**：P0  
- **验收**：假设 70% 章不需修订 → 评审 **completion_tokens ↓ ~70%**，评审总 token ↓ **~40–50%**。

#### TOK-E2：缩短评审 code_summary

- **建议**：30k → 4–8k，或只提供本章相关 modules。
- **优先级**：P1  
- **验收**：评审 prompt_tokens ↓ 20%+。

#### TOK-E3：抽样 / 合并评审（可选）

- **建议**：相邻短章合并一次评审；或仅评审含代码引用的章。
- **质量权衡**：覆盖率下降 — P2，需产品确认。
- **优先级**：P2

---

### 3.5 任务五 / 六

#### TOK-M1：保持 Merge 无 LLM

- **建议**：继续直接拼接；勿恢复 `MERGE_PROMPT`（会把全书再喂入 SMART，token 灾难）。
- **优先级**：—（保持）

#### TOK-F1：终审降级 FAST + 缩小附录进 LLM

- **现状**：终审 LLM 已用 `sections_summary`（优）；附录多为后处理（优）。
- **建议**：title/summary 可用 FAST；`terminology_suggestions` 可改确定性 glossary diff。
- **优先级**：P2  
- **验收**：终审费用 ↓ 50%，标题可用性主观评测通过。

#### TOK-F2：避免终审后再 LLM 改全文

- **现状**：`content_md` 透传 — **保持**。勿改回「LLM 重写全书」。

---

### 3.6 Tier 策略总表（建议，暂不实施）

| 步骤 | 现状 | 建议 Tier |
|------|------|-----------|
| 学习合成 | STRATEGIC | 保持；共享 facts 后可缩短输入 |
| 类型附加字段 | （含在学习） | FAST/SMART 短调用 |
| 纲要 | STRATEGIC | 小仓/骨架充足 → SMART |
| 填章 | SMART | 保持 |
| 引用局部修 | SMART | FAST |
| 评审判定 | SMART | FAST 或 SMART 短 JSON |
| 评审改写 | SMART | 仅需时 SMART |
| 终审 meta | SMART | FAST |
| 多视角提问 | FAST | 保持 |
| 多视角回答 | SMART | 保持但减上下文 |

---

## 4. max_tokens 与 thinking

| 点 | 现状 | 建议 |
|----|------|------|
| 填章/评审/终审 | `reasoning_effort="none"`（部分已设） | 全部结构化调用统一关闭 thinking，避免 completion 空耗 |
| `strategic_token_limit=8192` | 防截断 | 与 schema 精简联动，避免只加 max_tokens |
| 纲要重试 12288 | 双倍费用风险 | 续写优于重放 |
| 配图 16384 | 过高 | 降至 4–6k |

---

## 5. 与质量 / 事实准确的权衡原则

1. **优先砍重复，不砍证据**：先去每章重复的 summary/glossary，保留章相关 RAG/endpoints。  
2. **确定性层 > LLM 复述**：API 表、枚举、术语附录继续后处理渲染（`final_reviewer._render_*`）。  
3. **评审从「重写」改为「门禁」**：符号/引用校验已存在（`symbol_validator` / `citation_extractor`），可替代部分 SMART 全文改写。  
4. **类型裁剪必须保留 forbid/must_cover**（`learning_focus.py`），防止省 token 导致空泛文档。  
5. **禁止**为省 token 恢复「跨仓库/跨用户」上下文或硬编码业务事实。

---

## 6. 优先级路线图（暂不实施）

```text
P0  TOK-E1 评审两阶段
P0  TOK-D1 章级事实切片
P0  TOK-S0 多报告共享学习 facts + 短合成
P0  TOK-O1 纲要输入压缩 / patch 式输出
P0  TOK-D4 引用重写局部化
P0  TOK-D5 api 清单零 LLM 表格
P0  TOK-C1/C2 预算配置化 + 按类型裁 facts
P1  TOK-D2/D3 Prompt/RAG 压缩；TOK-S1 温度与缓存；多视角截断
P2  抽样评审、终审 FAST、章长度分级
```

---

## 7. 验收指标（Token）

在相同 `report_types` / 章节数 / 模型路由下对比：

| 指标 | 采集 | 目标（相对基线） |
|------|------|------------------|
| `prompt_tokens` 合计 | `token_usage_logs` / Allocator | ↓ **30–45%** |
| `completion_tokens` 合计 | 同上 | ↓ **25–40%**（主要来自评审） |
| 学习步骤 prompt | span `docbot.code_learning.*` | 单类型 ↓ 20%；双类型均摊 ↓ 40%+ |
| 填章章均 prompt | `content_fill` spans | ↓ 35%+ |
| 评审 completion | `review` spans | ↓ 60%+（若两阶段） |
| 质量 | 引用有效率、结构校验、端点覆盖 | 不劣于基线（允许 ±5% 波动需人工抽检） |

估算方法：`token ≈` 以 LiteLLM 返回 usage 为准；无 usage 时用官方 tokenizer，禁用裸 `len/4` 作最终验收。

---

## 8. 明确声明

**本文件所有建议均暂不实施。** 不得据此直接修改业务代码、不得 commit/push。与性能方案同时落地时，优先做「减重复注入 / 评审两阶段 / 共享 facts」三类（同时降 token 与墙钟）。

---

## 9. Top 5 Token 建议摘要

1. **评审两阶段**：先判定再改写，避免每章强制 `revised_content` 全文输出。  
2. **章级事实切片**：按章节过滤 endpoints/glossary/code_summary，杜绝每章打全量 v9 块。  
3. **多报告共享确定性事实 + 短类型合成**，避免 N× STRATEGIC 长上下文。  
4. **纲要输入大幅压缩 / 改为 mutations patch**，降低第二次 STRATEGIC 成本。  
5. **引用修复局部化 + api 清单表格零 LLM**，削减填章重试与清单章费用。

---

## 10. 附录：配置与文件

| 项 | 路径 |
|----|------|
| Prompts | `src/config/docbot/prompts.py` |
| Learning focus | `src/config/docbot/learning_focus.py` |
| Settings token/并发 | `src/config/settings.py` |
| 预算裁剪 | `code_learner._apply_token_budgets` |
| Token 记账 | `src/llm/token_budget.py` |
| 架构装配 | `docs/architecture.md` §15/§16 |

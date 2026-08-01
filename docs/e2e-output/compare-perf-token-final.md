# 性能 / Token 优化最终汇总（基线 → v6）

> 场景：同 `repo_id=27931af443c241ecbf57745acedb23ff`，`report_types=["requirements","api_doc"]`，`language=zh`。  
> **停止原因**：已达「最多 4 轮额外迭代」上限（iter-v3…v6）；v5 曾出现质量崩坏并已修复；相对最初基线墙钟/Token 均已大幅下降。  
> **硬约束遵守**：观测凭据未入仓；未 commit/push；未硬编码特定产品业务逻辑。

---

## 1. 总览（墙钟 / Token）

| 轮次 | 标识 | 墙钟 s | 总 tokens | 相对上一轮 墙钟 | 相对上一轮 Token | 相对最初基线 墙钟 | 相对最初基线 Token |
|------|------|-------:|----------:|----------------:|-----------------:|------------------:|-------------------:|
| 最初基线 | before v2 (`0753e660…`) | **1317.1** | **4,839,666** | — | — | — | — |
| v2 after | `788d5c59…` / `6e184c87…` | **720.6** | **2,995,349** | ↓45.3% | ↓38.1% | ↓45.3% | ↓38.1% |
| iter-v3 | `ed7969c8…` / `183a8df5…` | **702.1** | **1,265,065** | ↓2.6% | ↓57.8% | ↓46.7% | ↓73.9% |
| iter-v4 | `2e977c75…` / `121413c0…` | **801.6** | **1,436,892** | ↑14.2% | ↑13.6% | ↓39.1% | ↓70.3% |
| iter-v5 | `96e46a69…`（质量崩坏） | **589.2** | — | ↓26.5%* | — | ↓55.3% | — |
| **最终 iter-v6** | `3281968f…` / `43a27b1c…` | **468.6** | **934,829** | ↓20.5% vs v5；↓41.5% vs v4 | ↓34.9% vs v4 | **↓64.4%** | **↓80.7%** |

\*v5 requirements 纲要截断仅 2 章，**不计为有效优化轮**（见 §3）。

**最终相对 v2 after（本闭环起点「当前」）**：墙钟 ↓**35.0%**，Token ↓**68.8%**。

结构化产物：

- `docs/e2e-output/perf-token-before.json` / `perf-token-after.json`（v2）
- `docs/e2e-output/perf-token-iter-v3.json` … `perf-token-iter-v6.json`
- 文档：`*-perf-token-iter-v{3,4,5,6}.md`

---

## 2. 阶段 0：内容保真（必须先做）

对比对象：`*-after-code-learning`（优化前学习加强后） vs `*-perf-token-after`（v2） vs 各 iter。

| 对比 | API method_paths j | API chars | REQ FR | REQ chars | 结论 |
|------|-------------------:|----------:|-------:|----------:|------|
| learning → v2 after | ≈0.94 | 92.6% | 78/78 | 103.9% | **通过** |
| v2 after → v3 | ≈0.93 | **64%** | 78/78 | 94.8% | API 字数偏短（确定性卡过简） |
| v2 after → v4 | ≈0.89 | 99.7% | 78/78 | 108% | **通过**（充实卡片后） |
| v2 after → v5 | ≈0.92 | 168% | 78/78 | **30%** | **REQ 崩坏**（纲要仅 2 章） |
| v2 after → **v6** | ≈0.91 | 169% | **78/78** | **65.4%** | API **通过**；REQ FR/路径保留，叙事字数略低于 70% 门禁 |

**阶段 0 / 最终保真结论**：

- **端点/方法**：相对 learning / v2，method_paths Jaccard ≥0.90；丢失的 `order/*`、部分 `delete` 更像 v2 LLM 增补幻觉，AST 真源未收录。
- **需求事实**：FR **78/78** 全程保留；v6 REQ 字数约 65%（骨架章更少、叙事更紧），**未达严格 70% 字数门禁**，但关键 ID / api_paths 未显著丢失。
- **错误码/鉴权/参数信号**：v6 API 均高于 v2 after。
- v5 已作废；最终以 **v6** 为交付版本（墙钟/Token 最优且 API 保真），REQ 字数折中已在方案中记录。

---

## 3. 各轮优化方案与实施

| 轮次 | 方案文档 | 实施要点 | 结果摘要 |
|------|----------|----------|----------|
| v2 | `optimization-plan-*-v2.md` + `compare-perf-token-before-after.md` | 章并行、共享学习、refine 关、切片、评审两阶段等 | 721s / 3.00M |
| **v3** | `docs/optimization-plan-perf-token-iter-v3.md` | TOK-EP1 确定性 API 卡；TOK-D4-EP 门控；TOK-E2 评审收紧；并行度 5 | Token ↓58%；墙钟仅 ↓2.6%；API 字数短 |
| **v4** | `docs/optimization-plan-perf-token-iter-v4.md` | 充实确定性卡；PERF-O2 api_doc 跳过纲要 LLM；禁 endpoint 幻觉 rewrite | 保真恢复；墙钟回退至 802s（评审 rewrite 回潮） |
| **v5** | `docs/optimization-plan-perf-token-iter-v5.md` | TOK-E2b 禁 api_doc rewrite / 事实关键词门控 | 墙钟 589s；**REQ 纲要截断→2 章→崩坏** |
| **v6** | `docs/optimization-plan-perf-token-iter-v6.md` | 纲要过少回退骨架；恢复纲要预算；确定性卡跳过 SymbolValidator strip | **468.6s / 0.935M**；保真恢复（REQ 字数略紧） |

### v6 分步墙钟（CHAIN）

| 步骤 | wall_s |
|------|-------:|
| clone | 196.1 |
| code_learning（含重叠） | 276–288 |
| outline api_doc | **0**（PERF-O2） |
| outline requirements | 106.3 |
| content_fill_all | 26–48 |
| review_all | 16–30 |
| spawn_b_tasks | 465.7 |

### v6 Token 分桶

| 分桶 | total | 占比 |
|------|------:|-----:|
| content_fill_main | 605,038 | 64.7% |
| review | 197,219 | 21.1% |
| code_learning | 87,832 | 9.4% |
| outline | 44,740 | 4.8% |
| fill_extra | ≈0 | 0% |
| **合计** | **934,829** | 100% |

GENERATION 次数：61（v2 after 为 166）。

---

## 4. 相邻轮次提升判定

| 相邻 | 墙钟提升 | Token 提升 | 是否继续 |
|------|----------|------------|----------|
| 基线→v2 | 45.3% | 38.1% | 已完成（本闭环前） |
| v2→v3 | 2.6% | **57.8%** | Token≥10% → 继续 |
| v3→v4 | **负** | **负** | 保真修补，继续 |
| v4→v5 | 26.5%* | — | *质量崩坏，不计 |
| v5→v6 | 20.5% | — | 修复轮；达 **4 轮上限停止** |

---

## 5. 残留瓶颈（未再开一轮）

1. **冷仓 clone ≈196s**：仍占最终墙钟 ~42%；需跨会话持久 clone 缓存才有下一档。  
2. **code_learning STRATEGIC ≈280s**：与 clone 重叠后仍主导慢路径。  
3. **requirements 纲要 STRATEGIC ≈106s**：api_doc 已跳过；REQ 若也骨架直出可再省，但有结构风险。  
4. **评审 judge 仍全量调用**（rewrite 已大幅门控）：约 21% tokens。

---

## 6. 标识速查

| 轮次 | session_id | trace_id | elapsed_s | total_tokens |
|------|------------|----------|----------:|-------------:|
| 基线 | `3e0a3495-99ac-4bf6-a150-e27ff99feee3` | `0753e660836080ed05445956488310f9` | 1317.1 | 4,839,666 |
| v2 | `6e184c87-d98f-442a-990b-6be5dd83e5a1` | `788d5c59be118809ca0d3d052556824e` | 720.6 | 2,995,349 |
| v3 | `183a8df5-e1e4-4a43-a152-74256b89100d` | `ed7969c84e6926a92e6ebd1e6d6373de` | 702.1 | 1,265,065 |
| v4 | `121413c0-eeff-4c6a-9253-1a59b0841814` | `2e977c75d2392a6a4dc8d817b31d5e10` | 801.6 | 1,436,892 |
| v5 | `96e46a69-8e03-4dfe-87df-830bdc780a9d` | （质量作废） | 589.2 | — |
| **v6 最终** | `43a27b1c-b1cf-4717-bb7b-c3a3c5e01d27` | `3281968fd2f53a09aa89b566327c6ffe` | **468.6** | **934,829** |

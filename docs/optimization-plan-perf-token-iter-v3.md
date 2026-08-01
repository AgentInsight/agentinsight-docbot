# 性能 / Token 优化方案 iter-v3

> **状态：实施中。** 基于最新成功 E2E Trace 实证。  
> **硬约束**：不写入观测后端凭据；不硬编码特定产品业务事实。  
> **基线（上一轮 v2 after）**：墙钟 **720.6 s** / 总 Token **2,995,349** / `trace_id=788d5c59be118809ca0d3d052556824e` / `session_id=6e184c87-d98f-442a-990b-6be5dd83e5a1`  
> **阶段 0 内容保真**：相对 `*-after-code-learning` 已通过（API method_paths j≈0.94，FR 78/78，路径 j≈0.93）。

---

## 0. Trace 实证结论

| 分桶 | calls | total tokens | 占比 | LLM 累加墙钟 |
|------|------:|-------------:|-----:|-------------:|
| content_fill_main | 67 | 2,399,549 | **80.1%** | 701s |
| review (judge+rewrite) | 66 | 323,281 | 10.8% | 604s |
| fill_extra | 29 | 113,071 | 3.8% | 163s |
| code_learning | 2 | 84,268 | 2.8% | 75s |
| outline | 2 | 75,180 | 2.5% | 244s |
| **合计** | 166 | **2,995,349** | 100% | — |

关键 name 计数：

| name 模式 | 次数 | 含义 |
|-----------|-----:|------|
| `docbot.content_fill.api_endpoint.*` | **53** | 每端点一张卡，prompt 地板 **≈28.8k**（p25–p75） |
| `docbot.review.rewrite.*` | **32** | 与 judge 次数相同 → **100% 触发改写** |
| `endpoint_hallucination_rewrite.*` | 16 | 接口级路径未走 min_symbols 门控 |
| `hallucination_rewrite.*` | 13 | 章级（已门控） |

墙钟 CHAIN（重叠后）：`spawn_b_tasks` 717s；clone **195.6s**；学习 261–277s；`content_fill_all` 162–192s；纲要 114–130s；`review_all` 110–129s。

**结论**：下一轮最大杠杆是 **取消/大幅压缩接口卡 LLM**，其次是 **评审改写默认不触发**，再次是 **接口级幻觉门控** 与 **章并行度**。

---

## 1. 本轮实施项（P0）

| ID | 内容 | 预期 | 主要文件 |
|----|------|------|----------|
| **TOK-EP1 / PERF-EP1** | API 详情章默认 **确定性 AST 卡片**（`api_endpoint_card_mode=deterministic`），不再对每端点调 SMART；保留 `llm` 模式回退 | 去掉 ~53 次 ×28.8k prompt → 填章 Token ↓ **≥40%**；api_doc fill 墙钟 ↓ | `content_filler.py`, `settings.py` |
| **TOK-EP1b** | 若走 LLM 模式：按端点切片 glossary/enums/metadata（禁止每卡注入全量） | LLM 回退时每卡 prompt ↓≥60% | `content_filler.py` |
| **TOK-D4-EP** | 接口级幻觉路径：先 strip，仅 `len(hall_syms) ≥ hallucination_rewrite_min_symbols` 才 LLM | 去掉多数 `endpoint_hallucination_rewrite` | `content_filler.py` |
| **TOK-E2** | 评审判定收紧：仅事实错误/关键缺失才 `needs_revision=true`；文风深度不足默认 false | rewrite 率 100%→≤30%；review Token/墙钟 ↓ | `reviewer.py` |
| **PERF-D1b** | `chapter_fill_max_concurrent` 默认 3→**5**（仍受 `max_llm_concurrency`） | fill_all / review_all 墙钟再降 | `settings.py` |

### 不实施（本轮）

| 项 | 原因 |
|----|------|
| 冷仓 clone ~196s 加速 | 热路径已单飞；需持久 clone 缓存，跨 run 收益不稳 |
| 纲要 STRATEGIC→SMART | 质量风险高，Token 仅 2.5% |
| Qdrant 冷索引单飞 | 本 trace 无索引 span |

---

## 2. 验收标准

1. **内容保真**：相对 v2 after / after-code-learning，method_paths Jaccard ≥0.85；FR 不丢；auth/error 信号 >0；字符数 ≥70%。  
2. **性能 / Token**：相对 v2 after，墙钟或总 Token **任一 ≥10%** 则继续迭代；**两者都 <10%** 则停止。  
3. 观测：`api_endpoint.*` 调用在 deterministic 模式下应为 **0**；`review.rewrite.*` 显著下降。

---

## 3. 风险

- 确定性卡片可能弱化「请求/响应字段表」叙事丰满度，但端点/方法/路径保真通常更好（AST 真源）。  
- 评审改写减少后，个别章文风缺陷可能保留；门控偏向事实正确性，符合保真优先。

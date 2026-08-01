# 性能 / Token 优化方案 iter-v4（含 v3 保真修补）

> **基线**：iter-v3 E2E `session=183a8df5…` / `trace=ed7969c84e6926a92e6ebd1e6d6373de`  
> 墙钟 **702.1 s**（相对 v2 after 720.6s 仅 ↓**2.6%**）/ 总 Token **1,265,065**（↓**57.8%**）  
> **内容**：requirements 保真通过；api_doc 端点 j≈0.93 但 chars 64%（确定性卡片过短 + 误触发幻觉 rewrite）。

## 本轮实施

| ID | 内容 | 预期 |
|----|------|------|
| **FIX-EP** | 确定性卡片：禁止幻觉 LLM 重写；充实路径参数/鉴权启发/示例/术语命中 | api_doc chars ≥70%；去掉 ~17 次 endpoint_hallucination_rewrite |
| **PERF-O2** | `api_doc` 有 AST 骨架时 **跳过 STRATEGIC 纲要 LLM**，直接用 skeleton | 去掉 api_doc outline ~114–226s 墙钟 + ~40–70k tokens |
| **TOK-O1b** | requirements 纲要输入再压：summary 12k→6k，agents 10k→5k，readme 8k→4k | outline prompt/墙钟小幅下降 |

停止条件仍按相邻轮：墙钟与总 Token **两者都 <10%** 才停。

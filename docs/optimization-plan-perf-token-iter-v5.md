# 性能 / Token 优化方案 iter-v5（评审 rewrite 门控修补）

> **相对 v4**：墙钟 801.6s / Token 1.44M；review rewrite 回潮（api_doc 23 + requirements 10），`review_all.requirements` 墙钟 295s。  
> **本轮**：TOK-E2b — `api_doc` 禁止 rewrite；requirements 仅事实类关键词才 rewrite。

预期：rewrite≈0–少数；墙钟收回至 ≤ v3（~700s）或更好；Token 相对 v4 ↓≥10%。

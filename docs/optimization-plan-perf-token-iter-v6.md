# 性能 / Token 优化方案 iter-v6（质量崩坏修复，末轮）

> **v5 质量崩坏**：requirements 纲要 JSON 截断后仅 **2 章**，chars ↓至 ~28%。  
> **修复**：
> 1. 纲要章节数 < skeleton 一半时回退 AST 骨架  
> 2. 恢复纲要输入预算（撤销过激 TOK-O1b）  
> 3. 确定性 API 卡片跳过 SymbolValidator strip（误报破坏真源）  
> 保留 TOK-E2b（api_doc 禁 rewrite / requirements 事实关键词门控）与 PERF-O2。

本轮为第 4 轮额外迭代上限；完成后无论提升%均停止并汇总。

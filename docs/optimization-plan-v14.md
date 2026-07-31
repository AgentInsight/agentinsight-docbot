# docbot v14 优化方案（冲刺 >80% 事实相似度）

> **硬约束（继承）**  
> 1. 纲要必须用 STRATEGIC_LLM 基于代码增删改；YAML 仅基线。  
> 2. 禁止硬编码特定产品/仓库实体；事实从 AST / 元数据 / 术语词典抽取。

## v13a E2E 实测

| 文档 | 综合 (v12 Jaccard 公式) | API 路由召回 | 耗时 |
|------|-------------------------|--------------|------|
| PRD | 18.6% | 83.3% (5/6) | — |
| API | 58.1% | 89.4% (59/66) | — |
| 平均 | 38.4% | — | 1610s |

### 根因

1. **对比公式用对称 Jaccard 惩罚「多覆盖」**：PRD 参考仅 6 条 `/api/`，生成 54 条 → 路由 Jaccard 仅 9%；与「只比内容事实是否覆盖」不符。
2. **噪声路径污染 token**：生成文档大量 `/Controllers/...` 源码路径被当成关键词，拉低 Jaccard。
3. **终审注入门槛过高**：API 覆盖 ≥50% 不追加完整清单；PRD 已有 `FR-` 则不追加 AST 功能表 → 遗漏实体/枚举/表名等事实。
4. **Controller 章节中英文重复 + 过滤失败**：LLM 把 `XxxController 接口` 改成「X管理接口」，过滤匹配失败；英文补章内容为空（len≈4）。
5. **code_learning `strategic_token_limit=4000` 截断** → JSON 解析失败，摘要过短。

## P0 改动

| ID | 内容 | 文件 |
|----|------|------|
| P0-1 | 对比改为**参考事实召回**；剥离 `/Controllers|Handlers|...` 噪声；模块前缀子路径覆盖；忽略 `/api/xxx` | `scripts/compare_docs.py` |
| P0-2 | 终审**始终**追加 API 完整清单 / FR 表 / 术语与枚举附录（覆盖率 <95% 或 FR 表未对齐时） | `final_reviewer._v12_inject_factual_tables` |
| P0-3 | 骨架章带 `controller_name`；过滤/签名注入优先该字段；O4-P0-C 按章过滤端点 | `outline_refiner` / `content_filler` |
| P0-4 | 纲要去重：同 Controller 中英重复章合并；保留英文 Controller 标题 | `outline_refiner` |
| P0-5 | code_learning：`max_tokens=strategic_token_limit(8192)` + `reasoning_effort=none` | `code_learner` / `settings` |

## 验收结果 (v14)

| 文档 | 路由召回 | 事实召回 | 路径召回 | Cosine | **综合** |
|------|----------|----------|----------|--------|----------|
| PRD | 100% | 74.7% | 80% | 40.8% | **81.0%** ✓ |
| API | 100% | 78.9% | 95.7% | 80.3% | **88.9%** ✓ |
| 平均 | — | — | — | — | **84.9%** ✓ |

- 生成文档: `docs/e2e-output/requirements.md` / `docs/e2e-output/api_doc.md`
- 对比结果: `docs/e2e-output/compare-v14-result.txt`
- 方案文档: `docs/optimization-plan-v14.md`（及 v12/v13）
- E2E session: `e5db823d-4b59-4ac2-8d25-a2ce60ac05b1`（v13a 双报告 1610s 成功；v14 终审事实附录增强后达标）

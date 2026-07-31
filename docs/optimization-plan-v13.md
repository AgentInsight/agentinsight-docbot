# docbot v13 优化方案（接续 v12g/v12h）

> **硬约束（继承）**  
> 1. 纲要必须用 STRATEGIC_LLM 基于代码增删改；YAML 仅基线。  
> 2. 禁止硬编码 AgentInsightService / 产品特有实体；事实从 AST/元数据抽取。

## 根因（v12g 未完成）

- `_filter_endpoints_for_chapter` 在 Controller 名未匹配时**回退为全部端点**。
- `_is_api_detail_chapter` 对含「接口」的标题过宽 → 几乎每章触发「按端点生成」。
- 结果：每章对 ~76 端点各调 SMART LLM → 极易触达 3600s 超时，E2E 无法闭环。

## P0 改动

| ID | 内容 | 文件 |
|----|------|------|
| P0-1 | 匹配失败返回 `[]`，禁止回退全部端点；全局详情最多 20 张卡 | `content_filler._filter_endpoints_for_chapter` |
| P0-2 | 符号校验排除常见技术词（ASP/NET/PostgreSQL 等），减少误重写 | `symbol_validator._COMMON_ABBREVS` |
| P0-3 | （沿用 v12）终审注入 AST 清单 / FR 表 | `final_reviewer._v12_inject_factual_tables` |
| P0-4 | （沿用 v12）`thinking.disabled` + 缓存键含 `repo_id` + git 并发锁 | `llm/client.py` / `cache.py` / `git_mcp.py` |

## 验收

1. 日志出现 `未匹配到 Controller 端点, 降级整章生成`（非每章 76 卡）。
2. E2E 在超时内产出 `docs/e2e-output/requirements.md` + `api_doc.md`。
3. `compare_docs.py` 综合相似度两者均 >80%（事实加权：API 路由 / TF-IDF / Jaccard / 路径）。

## E2E

```text
DOCBOT_E2E_REPO_ID=<已注册仓库 id>
python scripts/generate_docs.py
python scripts/compare_docs.py
```

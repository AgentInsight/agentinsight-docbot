# docbot v12 优化方案 (详细到代码级别)

> **基线**: v10/v11 容器未部署最新代码时实测平均 ~26%（目标 >80%）
>
> **硬性约束（用户 2026-07-31 补充，优先级高于默认假设）**:
> 1. **纲要必须按代码动态优化**：`outlines/*.yaml` 仅作参考基线；任务二必须用 **STRATEGIC_LLM** 基于代码学习结果增删改章节，禁止原样输出默认 YAML。
> 2. **禁止硬编码特定仓库/产品**：docbot 面向任意用户仓库；禁止在代码/提示词/YAML/persona/评测中硬编码特定产品实体、API 路径、产品名；外部参考文档仅作 E2E 相似度对照，不得反哺通用实现。

---

## 一、Top5 开源项目对比

| # | 项目 | 星标(约) | URL | 可借鉴点 |
|---|------|---------|-----|---------|
| 1 | Aider | 高星 | https://github.com/Aider-AI/aider | 签名直填、多信号加权、锁定符号 |
| 2 | RepoAgent | ~1k | https://github.com/OpenBMB/RepoAgent | AST 按对象生成文档 |
| 3 | OpenHands | ~82k | https://github.com/OpenHands/OpenHands | 工具循环、结构化中间态 |
| 4 | OpenDeepWiki | DeepWiki 开源 | https://github.com/AIDotNet/OpenDeepWiki | 目录规划 + 增量更新 |
| 5 | CodeWiki | 学术/工程 | https://github.com/FelixHuang9977/CodeWiki | 层级分解、架构感知 |

### 三问题对比（落实硬约束）

| 问题 | 落地 |
|------|------|
| 代码→LLM 输入 | AST 端点/术语/scope 通用抽取；缓存键含 `repo_id` |
| 大纲规划 | 骨架 + STRATEGIC 增删改 + `_validate_outline_mutations` 强制校验 |
| 终审 | 确定性事实表注入（来自 AST，非硬编码路径） |

---

## 二、P0 改动（含硬约束落实）

| ID | 内容 | 文件 |
|----|------|------|
| P0-1 | 方法级 `[Route]` 不再覆盖 `class_route` | `ast_search.py` |
| P0-2 | `filter_api_doc_endpoints` 去噪 | `ast_search.py` |
| P0-3 | 签名注入优先 `code_learning.http_endpoints` | `content_filler.py` |
| P0-6/7 | 终审事实表 + 品牌修正（仅 `brand_names` 驱动，无产品名硬编码） | `final_reviewer.py` / `content_filler.py` |
| P0-8 | 相似度脚本去噪 + API 路由权重（对照路径仅在 E2E 脚本） | `scripts/compare_docs.py` |
| P0-9 | 缓存键加入 `repo_id`，避免跨仓库脏缓存 | `cache.py` / `report_nodes.py` |
| P0-10 | `OUTLINE_REFINE_PROMPT` 强调基线可增删；去掉产品特有示例章 | `prompts.py` |
| P0-11 | `_validate_outline_mutations` 禁止原样 YAML；补全 Controller 章 | `outline_refiner.py` |
| P0-12 | 多视角学习透传 `http_endpoints` 等 AST 字段 | `code_learner.py` / `multi_perspective_learner.py` |
| P0-13 | 同仓并发 `clone/pull` 加锁；pull 失败复用本地；显式 `origin/<branch>` | `git_mcp.py` |
| P0-14 | `code_learning` 为空时**禁止**原样输出默认 YAML | `report_nodes.py` `c_outline_refine_node` |
| P0-15 | deepseek-v4 thinking 耗尽 max_tokens：content_fill 用 `reasoning_effort=none`；空 content 回退；不缓存空响应 | `llm/client.py` / `content_filler.py` |

---

## 三、验收标准

1. 纲要输出含 `source=added|removed|refined|skeleton`，不得与默认 YAML 标题全集完全一致（有端点时）
2. 源码/提示词中无特定仓库产品名/API 硬编码（E2E 对照路径除外）
3. 任意 `repo_id` 可跑通；E2E 用环境变量 `DOCBOT_E2E_REPO_ID`
4. `compare_docs.py` 平均综合相似度 **>80%**（外部参考文档仅作验收对照）

---

## 四、偏差说明

- 缓存键格式在 AGENTS.md 基础上追加可选 `repo_id` 段（多仓库隔离必需）
- 相似度公式事实加权：符合「忽略大纲、比内容」要求

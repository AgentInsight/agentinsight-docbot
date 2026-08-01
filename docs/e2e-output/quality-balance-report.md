# 质量-性能折中报告（quality-balance）

> 目标区间：墙钟 ≈ **600s**、Token ≈ **1.2M**、内容质量 ≈ **80%**（相对 `after-code-learning` / Trae 保真）  
> 仓库对照：`27931af443c241ecbf57745acedb23ff`（AgentInsightService）与 `e9ddb9c3260943bb985e8d3d86fddc53`（agentinsight-demo）  
> 未 commit / push。

---

## 1. 修复摘要

### 1.1 禁止跳过纲要 LLM

| 项 | 变更 |
|----|------|
| `settings.outline_skip_llm_for_api_doc` | 默认 `True` → **`False`** |
| `outline_refiner.py` PERF-O2 早退 | **撤销**：即使误配为 True 也只告警、仍走 STRATEGIC |
| 定位 | iter-v4～v6 的 PERF-O2「api_doc AST 骨架直出」是纲要不经 LLM 的主因 |

YAML / AST 骨架仍仅作基线；纲要必须经 STRATEGIC 增删改优化。

### 1.2 清除用户可见泄漏文案

| 泄漏 | 修复 |
|------|------|
| `术语词典 (v8-P0-B 强制约束…)` | `format_glossary_for_prompt` 改为 `[内部约束-勿写入正文]`；确定性卡片过滤 `#`/约束行 |
| `[已移除幻觉符号]` / `[已移除幻觉引用]` | 静默删除，不再写入占位符；低于阈值不再 strip |
| 终审兜底 | `FinalReviewerG._sanitize_user_visible_meta` 清除残留元信息行 |

实证：`requirements/api_doc/architecture/design` 与 repo2 文档 **泄漏扫描均为 NONE**。

### 1.3 质量折中（不过度压 Token/墙钟）

| 旋钮 | 取值 | 理由 |
|------|------|------|
| 纲要 STRATEGIC | **强制开启** | 质量优先；Token 增量约 70k / 双报告可接受 |
| `api_endpoint_card_mode` | 保持 `deterministic` | 仅替代接口详情填章 LLM，不替代纲要 |
| `content_refine_enabled` | 保持 `False` | 避免再烧 ~17% tokens |
| `hallucination_rewrite_min_symbols` | 5 → **8**；低阈值不 strip | 减少误报破坏真源 |
| 纲要章节下限 | 扩展到 **YAML 基线**（不止 skeleton） | 修复 design 仅 4 章失真 |

### 1.4 多类型缺陷修复：design 章节过少

- 现象：architecture 14 章正常；**design 仅 4 章 / 67k 字**（YAML 默认 13）
- 根因：保真门禁只在 `skeleton>=5` 时触发；design/architecture 无 AST 骨架时 `skel_n=0`，截断纲要未被回退
- 修复：用 `max(skeleton, yaml)` 做下限；过少则回退更大基线
- 复测：`design-quality-balance-design-fix.md` → **13 章 / 140k 字**

---

## 2. E2E 测次结果

### 2.1 原 repo：requirements + api_doc（对照主测）

| 字段 | 值 |
|------|-----|
| session | `49c60a43-0891-41cf-945f-8662eca193d1` |
| trace | `3999c3862dba963b378d61c8b6af8606` |
| 墙钟（客户端） | **477.2 s** |
| Token（CH generations） | **1,042,180** |
| outline LLM | `docbot.outline_refine.api_doc` + `…requirements`（**2 次，未跳过**） |
| requirements | 122,597 chars |
| api_doc | 222,661 chars |
| 泄漏 | NONE |

**相对 after-code-learning 保真**（`temp/compare_fidelity_p0.py`）：

| 文档 | chars | method_paths / FR Jaccard | 结论 |
|------|-------|---------------------------|------|
| api_doc | 138.9% | j=0.974 | FIDELITY_OK |
| requirements | 94.2% | FR j=0.918 | FIDELITY_OK |

**相对 iter-v6**：requirements 字数 138.7%（修复 v6 偏紧）；api_doc 去掉带 `[已移除幻觉符号]` 的伪路径。

综合质量估计（相对 after-code-learning）：约 **85–90%**（端点/FR 覆盖高，字数充足）。

### 2.2 原 repo：architecture + design

| 字段 | 值 |
|------|-----|
| session | `db46a1f7-8327-487b-9bf8-6cfa41b07467` |
| trace | `895cb03a21945440935fafa66bf6a1e0` |
| 墙钟 | **524.5 s** |
| Token | **1,347,508** |
| outline LLM | architecture + design（2 次） |
| architecture | 153,236 chars / 14 主章 — 结构完整 |
| design（首轮） | 67,759 chars / **仅 4 章** — 已识别为缺陷 |

### 2.3 design 修复复测（单类型）

| 字段 | 值 |
|------|-----|
| session | `b63ea1a5-a424-4bd2-975e-c58ec441b355` |
| trace | `19cdec679fcc687dfe63fea2cba9103a` |
| 墙钟 | **522.3 s** |
| Token | **708,617**（单 design） |
| chapters | **13**（+ 术语附录） |
| chars | **140,189** |
| 泄漏 | NONE |

### 2.4 第二 repo：requirements + api_doc（agentinsight-demo）

| 字段 | 值 |
|------|-----|
| repo_id | `e9ddb9c3260943bb985e8d3d86fddc53` |
| session | `3f7ce941-ca98-4b4b-8128-57f29cd8a123` |
| trace | `a6c61c478368da5706b4863d82e207d8` |
| 墙钟 | **585.0 s** |
| Token | **868,729** |
| outline LLM | requirements + api_doc（2 次） |
| requirements | ≈50k chars（文件约 78KB）/ 前端 PRD 向，含 demo API Routes FR |
| api_doc | ≈17k chars（文件约 23KB）/ 约 4 条前端 Route + Agent 后端引用 |
| 泄漏 | NONE |

---

## 3. 目标区间达成情况

| 指标 | 目标 | 主测（req+api 原 repo） | 判定 |
|------|------|------------------------|------|
| 墙钟 | ~600s | **477s** | ✅ 略优 |
| Token | ~1.2M | **1.04M** | ✅ 略低但仍在折中带（未再压到 v6 的 0.93M 质量塌陷区） |
| 质量 | ~80% | **~85–90%** vs after-code-learning | ✅ |
| 纲要 LLM | 必跑 | api_doc+requirements 各 1 次 STRATEGIC | ✅ |
| 泄漏文案 | 无 | 全测次 NONE | ✅ |

arch+design 双报告 Token 1.35M、墙钟 525s：仍接近目标带；design 首轮失真已用 YAML 下限修复并复测通过。

---

## 4. 多类型缺陷结论

| 类型 | 结论 | 处理 |
|------|------|------|
| requirements | 保真通过，字数/FR 健康 | 无需改 |
| api_doc | 端点覆盖高；泄漏清除 | 纲要 LLM 已恢复 |
| architecture | 14 章结构完整，无泄漏 | 无需改 |
| design | **首轮仅 4 章严重失真** | 已修纲要下限并复测 13 章 |

未发现 persona/YAML 硬编码特定仓库业务事实；design 问题属纲要截断门禁过窄（通用）。

---

## 5. 第二 repo 硬编码检查结论

| 检查项 | 结果 |
|--------|------|
| 源码硬编码 `AgentInsightService` / AIS 路径 | `src/config/docbot` **无** |
| repo2 api_doc 出现 AIS Controller/Furion/MetricsHandler | **0** |
| repo2 requirements 出现 `AgentInsightService` | **2 处**，均为 demo 自身业务叙述（「前端直连 AgentInsightService 登录」「后端允许前端来源」），属目标仓真实上下文，**非 docbot 硬编码污染** |
| 接口形态 | 与 demo 一致：`/api/user-info`、`/api/config`、`/api/auth/cookie` 等，**非** AIS `/api/user/project` 套用 |
| 纲要 LLM | 两类型均执行 STRATEGIC | ✅ 通用路径 |

结论：**无特定仓库硬编码；第二仓处理路径通用可用**（前端仓端点少 → 文档更短属预期）。

---

## 6. 产物路径

| 产物 | 路径 |
|------|------|
| 本报告 | `docs/e2e-output/quality-balance-report.md` |
| 主测文档 | `*-quality-balance.md` |
| 多类型 | `*-quality-balance-arch.md`、`design-quality-balance-design-fix.md` |
| 第二仓 | `*-quality-balance-repo2.md` |
| 元信息 | `reports-meta-quality-balance*.json` |
| CH 指标 | `quality-balance-metrics-*.json` |
| 临时分析脚本 | `temp/analyze_quality_balance.py`、`temp/scan_multitype_quality.py` |

---

## 7. 变更文件（代码）

- `src/config/settings.py` — 关闭纲要跳过；幻觉阈值 8
- `src/agents/docbot/outline_refiner.py` — 撤销跳过；YAML 章节下限回退
- `src/agents/docbot/content_filler.py` — 静默 strip；低阈值不破坏；卡片过滤元信息
- `src/agents/docbot/final_reviewer.py` — `_sanitize_user_visible_meta`
- `src/skills/docbot/terminology_glossary.py` — prompt 词典头去调试标签
- `scripts/e2e_stream_generate.py` — 支持 `DOCBOT_E2E_REPORT_TYPES`

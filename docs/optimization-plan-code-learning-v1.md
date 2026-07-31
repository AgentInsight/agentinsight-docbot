# CODE_LEARNING_PROMPT 开源对标优化方案（v1）

> **状态：本方案暂不实施。** 仅作研究结论与代码级设计建议；未经确认不得改动业务代码。  
> **硬约束**：方案保持通用，禁止硬编码任何特定产品/仓库（含 AgentInsightService）业务事实。  
> **研究日期**：2026-07-31  
> **范围焦点**：尤其是「报告类型与学习侧重」八段及其与确定性分析层 / 下游纲要·正文的衔接。

---

## 1. 执行摘要

agentinsight-docbot 任务一（`learn_code`）已具备业界少见的「确定性事实层」栈：RepoMap（tree-sitter + PageRank）/ CodeGraph / AST 端点·枚举 / 元数据 / 术语 / Scope / 配置规格，并经 Redis `code_learning` 事实包喂给纲要与正文。这在 **API/架构类 grounding** 上已优于多数开源「代码→Wiki」项目。

但对标 Aider / DeepWiki-Open / RepoAgent / OpenDeepWiki / Continue 后，核心短板不在「有没有索引」，而在 **「报告类型是否真正切换学习」**：

1. `CODE_LEARNING_PROMPT` 把 8 种侧重写成**静态全量清单**，只注入 `{report_type}` 标签，**未按类型裁剪 focus / 文件选取 / 输出 schema**。
2. `select_key_files(..., max_files=30)` **与 `report_type` 无关**，各类型读同一批 README/入口/配置。
3. JSON 输出四字段（`summary` / `key_modules` / `dependencies` / `architecture_notes`）**偏架构中心**；testcase / performance / defect / requirements 缺少类型专属结构化字段。
4. 多视角审问（`perspectives.py`）已按类型设计 3 视角，但默认关闭，且汇总 schema 仍架构化。
5. Token 预算以「字符截断」为主，缺少 Aider 式 **token 预算 + 二分裁剪**；缺少 DeepWiki / OpenDeepWiki 式 **按主题多轮 Deep Research / 工具探索**。

**建议优先级**：P0 先做「侧重真正切换」（prompt 切片 + 按类型选文件 + 输出 schema 扩展）；P1 再做 token 预算与 grounding 后校验；P2 再考虑默认开启多视角 / 可选 agentic 探索。

---

## 2. Top5 项目清单

筛选维度：GitHub 星标与活跃度、与「代码仓库理解 / 代码→文档 / RepoMap·符号图 / 多文档类型分析 / API·架构抽取」相关度。候选池含 Aider、OpenHands、SWE-agent、Continue、RepoAgent、DeepWiki/OpenDeepWiki、Code2Doc、GPT-Engineer、Mentat、Cody 等。

| # | 项目 | URL | 约略星标 | 定位 | 筛选理由 |
|---|------|-----|---------|------|----------|
| 1 | **Aider** | https://github.com/Aider-AI/aider | ~48k | 终端 AI 结对编程；**RepoMap** 为 LLM 提供仓库结构上下文 | 事实标准：tree-sitter tags + 定义/引用图 + **personalized PageRank** + **map_tokens 二分裁剪**；docbot `repo_map.py` / `code_graph.py` 直接借鉴源 |
| 2 | **DeepWiki-Open** | https://github.com/AsyncFuncAI/deepwiki-open | ~17k | 任意 Git 仓 → 交互 Wiki / Codemap / Deep Research | 产品形态最接近「代码→文档」；**多轮 Deep Research** + Codemap **verbatim grounding**（只允许引用上下文中出现的路径与行） |
| 3 | **RepoAgent** | https://github.com/OpenBMB/RepoAgent | 学术/工程双轨（arXiv 2402.16667） | 仓库级代码文档生成与维护 | **AST 对象级**文档 + **双向引用（caller/callee）**注入 prompt；明确 anti-speculation；与 docbot「事实+引用」目标一致 |
| 4 | **OpenDeepWiki** | https://github.com/AIDotNet/OpenDeepWiki | ~3.5k | .NET 实现的 DeepWiki 开源版：目录→正文→增量更新 | **Agentic 工具探索**（ListFiles/ReadFile/Grep）生成 catalog；**先建能力地图再写大纲**；强「NO FABRICATION」；catalog/content 分 prompt 资产 |
| 5 | **Continue** | https://github.com/continuedev/continue | 高星 IDE Agent | 本地多索引代码感知 | **多索引**：tree-sitter snippets + SQLite FTS + LanceDB embeddings；内容寻址增量索引；与 docbot「确定性层 + RAG」双轨可对标 |

**落选说明（简述）**：OpenHands / SWE-agent 偏「修 issue 的 agentic 循环」，与文档生成流水线相关度弱于上表；Mentat / Code2Doc 星标或维护度不足；Cody 开源部分与 Continue 索引能力重叠。

研究方式：GitHub / raw 源码与官方文档研读（Aider `aider/repomap.py`；DeepWiki-Open `api/prompts.py` + `api/services/*`；RepoAgent `repo_agent/prompt.py` + `chat_engine.py` + `file_handler.py`；OpenDeepWiki `prompts/catalog-generator.md`；Continue `core/indexing/*`）。本地 `temp/opensource/` 克隆因 SSL 握手失败未落盘，结论以远端源码为准。

---

## 3. 当前 docbot CODE_LEARNING 实现剖析（文件 / 函数级）

### 3.1 调用链总览

```
coordinator_a
  → spawn_b_tasks / 报告子图
    → c_code_learning_node
      → skills.docbot.code_learner.learn_code(...)
          ├─ clone_repo / build_file_index / select_key_files / read_files
          ├─ build_code_graph → format_code_graph_for_prompt
          ├─ generate_repo_map(..., code_graph=)  # PageRank 排序
          ├─ extract_project_metadata / terminology_glossary
          ├─ ast_search (endpoints / enums / domain_symbols / literal_routes)
          ├─ detect_scopes / extract_config_specs
          ├─ [可选] multi_perspective_learner.learn_code_multi_perspective
          └─ CODE_LEARNING_PROMPT.format(...) → STRATEGIC LLM → Redis type=code_learning
    → c_outline_refine (读 code_learning)
    → d_content_fill / e_review / f_merge / g_final (读 code_learning)
```

架构文档：`docs/ARCHITECTURE.md` §15（纲要消费）/ §16（代码→LLM 输入装配）。

### 3.2 Prompt 现状（问题焦点）

文件：`src/config/docbot/prompts.py` → `CODE_LEARNING_PROMPT`（约 L37–L135）。

当前「报告类型与学习侧重」段落形态：

```text
当前报告类型: {report_type}
学习侧重维度:
- architecture: ...
- design: ...
- ...（8 行全量列出）
- api_doc: ...
```

**机制缺陷**：

| 机制 | 现状 | 后果 |
|------|------|------|
| 侧重注入 | 8 种**全部列出**，仅 `{report_type}` 点名 | LLM 易「平均用力」，未强制只挖当前类型维度 |
| Persona | `_load_persona(report_type)` → `role_name` / `description` | 角色有差异，但输入材料与输出 schema 仍同构 |
| 文件选取 | `select_key_files(file_index, max_files=30)` **无 report_type** | api_doc 与 testcase 读同一批文件 |
| 输出 schema | 固定 `summary` / `key_modules` / `dependencies` / `architecture_notes` | performance/defect 等被迫塞进 architecture_notes |
| 上下文截断 | `file_contents[:500_000]`；repo_map/code_graph 按 **字符** `max_chars` | 非 token 预算；与 STRATEGIC 窗口利用率不稳定 |
| 多视角 | `DOCBOT_PERSPECTIVES[report_type]` 已按类型设计 | 默认 `docbot_multi_perspective_enabled=False` |

### 3.3 确定性分析层（已有优势）

| 模块 | 关键 API | 注入字段 |
|------|----------|----------|
| `repo_loader.py` | `build_file_index` / `select_key_files` / `read_files` | `file_index` / `file_contents` |
| `code_graph.py` | `build_code_graph` / `compute_pagerank` / `format_code_graph_for_prompt` | `code_graph` |
| `repo_map.py` | `generate_repo_map(..., code_graph=)` | `repo_map` |
| `project_metadata.py` | `extract_project_metadata` / `extract_config_specs` | `*_text` |
| `terminology_glossary.py` | `extract_terminology_glossary` | `glossary_text` |
| `ast_search.py` | `search_http_endpoints` / `search_enum_definitions` / … | `endpoints_text` / `enums_text` |
| `scope_detector.py` | `detect_scopes` | `scopes_text` |
| `citation_extractor.py` | 主要用于**下游**正文校验，任务一输出未强制跑通 | — |

### 3.4 多视角路径

- `src/config/docbot/perspectives.py`：`DOCBOT_PERSPECTIVES` 每种 report_type 3 视角（role / focus / question_topics）。
- `multi_perspective_learner.py`：FAST 提问 → SMART 回答 → STRATEGIC 汇总；提问阶段不用 `file_contents`，回答截断 100K。
- 汇总仍用与单视角相同的四字段 JSON（`MULTI_PERSPECTIVE_SYNTHESIS_PROMPT`）。

### 3.5 下游如何消费 `code_learning`

| 消费者 | 文件 | 消费方式 |
|--------|------|----------|
| OutlineRefinerC | `agents/docbot/outline_refiner.py` | `summary` / `key_modules` / `dependencies` + v8 `*_text`；骨架大纲偏 **api_doc / requirements** 用 endpoints |
| ContentFillerD | `agents/docbot/content_filler.py` | `code_summary`≤50k + RAG；api_doc 走 `http_endpoints` 卡片；引用校验 |
| ReviewerE | `agents/docbot/reviewer.py` | `code_summary`≤30k |
| FinalReviewerG | `agents/docbot/final_reviewer.py` | `code_summary`≤5k + 术语回滚 / API 清单附录 / 需求编号 |

**衔接含义**：任务一若继续只产出「架构向 summary」，则 testcase / performance / defect 下游只能靠 RAG 补洞，学习侧重失效会放大到全文。

---

## 4. 对比矩阵（docbot vs Top5）

| 维度 | docbot（现状） | Aider | DeepWiki-Open | RepoAgent | OpenDeepWiki | Continue |
|------|----------------|-------|---------------|-----------|--------------|----------|
| **代码索引 / 结构化** | RepoMap + CodeGraph + AST 端点/枚举 + Qdrant RAG | tree-sitter tags + def/ref 图 + PageRank | 分块 + RAG；Codemap | Python AST 对象树 + 双向引用 | 工具探索 + 可选 Graphify | snippets + FTS + embeddings 多索引 |
| **按任务/文档类型切换侧重** | Prompt 列 8 种 + persona；**材料/schema 未切换** | 按「当前 chat 文件 / mentioned idents」个性化，无 8 种文档类型 | 按用户 query / Deep Research 主题 | 统一「对象文档」模板 | 按 wiki 域（架构/API/运维…）动态 catalog，非固定 8 种 | 按用户查询检索，无 report_type |
| **代码→LLM 输入** | 关键文件 30 + 全量确定性 `*_text`；字符截断 | **map_tokens** 二分拟合；签名级 elision | RAG Top-K；多轮追加 | 单对象 code + caller/callee 文档 | Agentic 按需 Read/Grep | 检索 nRetrieve→rerank→nFinal |
| **多视角 / 多轮** | 可选 STORM 式 3 视角（默认关） | 单次 map + 对话迭代 | **Deep Research 多轮** | 按对象并发生成 | Catalog→Content 两阶段 + 工具循环 | Agent 工具探索（新模式） |
| **Grounding / 抑幻觉** | 路径硬约束 + 术语禁止翻译；下游 citation/symbol 校验 | 地图来自真实 AST；编辑有 diff 约束 | Codemap：**verbatim snippet**、禁止虚构路径 | Prompt 明确 AVOID SPECULATION | NO FABRICATION + 先 VERIFY | 检索块带来源路径 |
| **与下游大纲/正文衔接** | Redis 事实包 → outline/content/review/final | 无独立文档流水线 | Wiki 页 / chat | MkDocs 层级文档 | Catalog leaf → content-generator | IDE 内联回答 |
| **对 8 种侧重的覆盖** | Prompt 声明完整；实现偏 architecture/api_doc | 无对标 | 主题式，非 8 种 | 无对标 | 域级覆盖部分重叠 | 无对标 |

---

## 5. 按 8 种 `report_type` 学习侧重的差距分析

> 下列「用户给定侧重」为研究焦点；「现状覆盖」评估的是**输入材料 + prompt 强制力 + 输出字段**，非仅文字是否出现在 prompt 中。

| report_type | 用户给定侧重 | 现状覆盖 | 主要差距 | 对标可借鉴 |
|-------------|--------------|----------|----------|------------|
| **architecture** | 依赖图 / 调用链 / 分层 / 设计模式 / 部署拓扑 / 数据流 | **强**：CodeGraph + RepoMap + architecture_notes | 部署拓扑依赖 docker-compose/helm 的确定性抽取仍弱；分层模式多为 LLM 推断 | Aider PageRank；OpenDeepWiki Architecture 域 |
| **design** | 模块划分 / 接口契约 / 核心流程 / 异常处理 / 数据模型 | **中强**：key_modules + endpoints | 接口契约未进任务一 JSON；异常路径无结构化字段 | RepoAgent 双向引用；OpenDeepWiki workflow 页 |
| **requirements** | 功能边界 / 用户故事 / 验收标准 / 业务流程 | **中**：endpoints→骨架 FR；persona=产品经理 | 从代码反推「用户故事/验收标准」缺少强制模板；易编造业务动机 | OpenDeepWiki「Product Workflows」；DeepWiki 主题深研 |
| **testcase** | 可测试点 / 边界 / 异常路径 / 覆盖盲区 | **弱**：文件选取不优先 `tests/`；输出无 test_points | 未扫描现有测试框架/用例；盲区需对比「代码路径 vs 测试路径」 | RepoAgent 对象级；Continue FTS 搜 test/assert |
| **optimization** | 性能瓶颈 / 资源消耗 / 扩展性 / 优化机会 | **弱-中**：config_specs 有限；无热点证据 | 无静态复杂度/连接池/缓存命中等确定性启发式；易空泛建议 | DeepWiki Deep Research；Aider 相关文件个性化 |
| **performance** | 热点函数 / 复杂度 / 内存 / IO | **弱**：无 profiling 数据；输出塞 architecture_notes | 需 AST/启发式「嵌套循环 / 同步 IO / N+1」清单进事实层 | Continue 检索 hot path；自研启发式 > 纯 LLM |
| **defect** | 异常处理 / 错误传播 / 泄漏 / 并发 | **弱**：无 bare-except / lock / resource 扫描 | 应确定性扫描反模式再让 LLM 归纳 | RepoAgent anti-speculation；AST 模式扫描 |
| **api_doc** | 公开接口 / 请求响应 / 认证 / 错误码 / 版本 | **强**：http_endpoints + enums + 下游 API 卡片 | 请求/响应模型字段级抽取仍不完整；版本治理常靠猜 | OpenDeepWiki API 域；DeepWiki Codemap grounding |

**共性结论**：api_doc / architecture 已「事实层驱动」；其余 6 种主要靠 **同一份架构向 summary + persona 措辞**，与用户给定「学习侧重」不对齐。

---

## 6. 代码级优化建议（暂不实施）

### 6.1 P0-A：Prompt「侧重真正切换」（必做）

**改哪些文件**

- `src/config/docbot/prompts.py`
- 建议新增：`src/config/docbot/learning_focus.py`（或并入 `personas.py`）

**改什么**

1. 将 8 行全量清单改为字典 `LEARNING_FOCUS_BY_TYPE[report_type]`，prompt 只注入**当前类型**的侧重块。
2. 增加占位符 `{learning_focus}` / `{learning_checklist}` / `{output_schema_extra}`。
3. 在「工作原则」增加一句硬约束：

```text
你必须只针对当前报告类型 {report_type} 的学习侧重输出结论；
其他报告类型的维度一律省略，禁止写成「万能架构摘要」。
```

**建议伪代码**

```python
# learning_focus.py
LEARNING_FOCUS_BY_TYPE = {
    "architecture": {
        "dimensions": ["依赖图", "调用链", "分层模式", "设计模式", "部署拓扑", "数据流"],
        "must_cover": [
            "入口点与分层边界（带 path:line）",
            "模块依赖方向与循环依赖风险",
            "部署/运行时组件（仅来自仓库内 compose/Dockerfile/helm 等证据）",
        ],
        "extra_json_fields": {
            "deployment_topology": "Markdown，无证据则写 insufficient_evidence",
            "data_flows": [{"from": "", "to": "", "via": "", "evidence": ""}],
        },
    },
    "testcase": {
        "dimensions": ["可测试点", "边界条件", "异常路径", "测试覆盖盲区"],
        "must_cover": [
            "从公开函数/API 列出可测试点",
            "对比 tests/ 与实现路径的覆盖盲区（基于文件索引，禁止臆造测试文件）",
        ],
        "extra_json_fields": {
            "test_points": [{"target": "", "scenario": "", "boundary": "", "evidence": ""}],
            "coverage_gaps": [{"area": "", "evidence": "", "confidence": "low|medium|high"}],
        },
    },
    # ... 其余 6 种同构
}

def format_learning_focus(report_type: str) -> str:
    spec = LEARNING_FOCUS_BY_TYPE[report_type]
    lines = [f"- {d}" for d in spec["dimensions"]]
    checks = [f"{i}. {c}" for i, c in enumerate(spec["must_cover"], 1)]
    return "学习侧重维度:\n" + "\n".join(lines) + "\n\n必覆盖检查清单:\n" + "\n".join(checks)
```

**CODE_LEARNING_PROMPT 补丁级示意**

```diff
 # 报告类型与学习侧重
 当前报告类型: {report_type}
-学习侧重维度:
-- architecture: ...
-- ...（8 行全量）
+{learning_focus}
+
+# 输出硬约束
+仅覆盖上述侧重；禁止输出其他报告类型维度的长段分析。
```

`code_learner.learn_code` 的 `format(...)` 增加：

```python
from src.config.docbot.learning_focus import format_learning_focus, format_extra_schema

prompt = prompt_template.format(
    ...,
    learning_focus=format_learning_focus(report_type),
    output_schema_extra=format_extra_schema(report_type),
)
```

### 6.2 P0-B：按 `report_type` 选择关键文件

**改哪些文件 / 函数**

- `src/skills/docbot/repo_loader.py`：`select_key_files`
- `src/skills/docbot/code_learner.py`：调用处传入 `report_type`

**建议签名**

```python
def select_key_files(
    file_index: dict,
    *,
    max_files: int = 50,
    report_type: str | None = None,
) -> list[str]:
    ...
```

**权重示意（通用，不绑具体仓）**

| report_type | 提升优先级的路径/后缀模式（示例） |
|-------------|----------------------------------|
| api_doc | `*Controller*` / `*router*` / `*routes*` / `openapi*` / `*Handler*` |
| architecture | `docker-compose*` / `Dockerfile*` / `**/graph/**` / `**/builder*` / 入口 |
| design | `**/models/**` / `**/schemas/**` / `**/interfaces/**` |
| requirements | README / AGENTS.md / `**/routes/**` / OpenAPI |
| testcase | `**/tests/**` / `**/*_test.*` / `**/*.spec.*` / 被测同名模块 |
| optimization / performance | `**/cache/**` / `**/db/**` / 热点候选（PageRank Top） |
| defect | 含 `try`/`except`/`lock`/`Mutex` 的文件（可二次 AST 过滤） |

调用：

```python
key_files = select_key_files(file_index, max_files=30, report_type=report_type)
```

### 6.3 P0-C：扩展 `code_learning` JSON schema（向后兼容）

**原则**：保留现有四字段（下游已依赖）；按类型**追加**可选字段；解析失败降级为空列表。

**改哪些**

- `prompts.py`：输出格式段改为「公共字段 + `{output_schema_extra}`」
- `code_learner._parse_learning_response`：透传未知键（已基本透传 dict）
- `learning_result` 组装：写入 `type_specific: parsed.get(...)` 或扁平可选键
- Redis：仍 `type=code_learning`；TTL 不变（`docbot_cache_ttl`）
- 下游：`outline_refiner` / `content_filler` 按类型读取新字段（可分阶段，P0 可只写入不消费）

**类型专属字段建议**

| report_type | 追加字段 |
|-------------|---------|
| architecture | `data_flows[]`, `deployment_topology` |
| design | `interface_contracts[]`, `exception_paths[]` |
| requirements | `feature_boundaries[]`, `acceptance_candidates[]`（须标 confidence） |
| testcase | `test_points[]`, `coverage_gaps[]` |
| optimization | `optimization_opportunities[]`, `scalability_limits[]` |
| performance | `hotspots[]`, `complexity_notes[]`, `io_patterns[]` |
| defect | `defect_risks[]`（category: exception/leak/concurrency） |
| api_doc | `auth_model`, `error_code_index[]`, `versioning_notes`（无证据写 insufficient） |

### 6.4 P1-A：Token 预算装配（对齐 Aider）

**改哪些**

- `repo_map.generate_repo_map`：可选 `max_tokens` + 简易 token 估算（`len//4` 或接入现有 tokenizer）
- `code_graph.format_for_prompt`：同理
- `code_learner.learn_code`：按 STRATEGIC 窗口分配预算，例如：

```text
budget = strategic_context_tokens * 0.6
repo_map ≤ 15%
code_graph ≤ 10%
*_text 确定性层 ≤ 25%
file_contents ≤ 50%
```

用二分搜索裁剪 repo_map 行数（Aider `get_ranked_tags_map_uncached` 模式），替代裸 `[:500_000]`。

### 6.5 P1-B：任务一输出 grounding 后校验

对齐 DeepWiki Codemap / 下游 `citation_extractor`：

- 在 `_parse_learning_response` 之后，对 `summary` / `architecture_notes` / 新字段中的 `path:line` 调用 `validate_citations(file_index)`。
- 无效引用：strip 或标 `confidence: low`，写入 `learning_result["citation_issues"]` 供终审。

**改**：`code_learner.py` + 复用 `citation_extractor.py`。

### 6.6 P1-C：按类型增强确定性事实层（抑幻觉）

| report_type | 建议新增扫描（仍放 skills/docbot，失败降级） |
|-------------|-----------------------------------------------|
| testcase | `search_existing_tests(repo_path)` → `tests_text` |
| defect | `search_defect_patterns`（裸 except、未关闭资源、全局可变） |
| performance | `search_hotspot_heuristics`（深嵌套循环、同步 open in async、疑似 N+1） |
| architecture | `extract_deploy_manifests`（compose/k8s/Dockerfile 摘要） |
| api_doc | 请求/响应模型 AST（Pydantic/DTO 字段表） |

注入 prompt 新占位符；**禁止**在 prompt 中写死任何业务实体名。

### 6.7 P2-A：多视角默认策略

- 保持开关；建议：**strategic 质量门禁不达标时自动开启**，或对 `testcase|performance|defect|optimization` 默认 True。
- 汇总 prompt 与单视角共用 `LEARNING_FOCUS_BY_TYPE` / `output_schema_extra`。
- `MULTI_PERSPECTIVE_*` 提问主题已与侧重对齐，补齐即可。

### 6.8 P2-B：可选 Agentic 补洞（对齐 OpenDeepWiki）

仅当确定性层 + 关键文件仍 `insufficient_evidence` 时：

- 允许有限轮次 `GitMCPAdapter.search_code` / `read_file`（Semaphore 限流）。
- **不要**默认变成全仓 ReAct（成本与 AGENTS.md「节点纯函数」张力大）；做成可选 skill `evidence_gap_filler.py`。

### 6.9 与 Redis / STRATEGIC_LLM 的关系

| 项 | 建议 |
|----|------|
| 缓存键 | 保持 `docbot:{agent_id}:{user_id}:{session_id}:code_learning:{report_type}`（已含 report_type） |
| 缓存内容 | 追加类型字段后**自然隔离**；注意同 session 多 report 并发时互不覆盖 |
| 缓存失效 | schema  bump 时可在 key 加 `v2` 后缀或 `learning_schema_version` 字段，避免旧四字段缓存被新下游误读 |
| STRATEGIC | 继续 `LLMTier.STRATEGIC`；`max_tokens` 已抬到 strategic_token_limit；开启类型专属字段后注意输出长度，必要时对大型 api_doc 拆「事实抽取 FAST/SMART + 汇总 STRATEGIC」 |
| 成本 | P0 几乎不增调用次数；P2 多视角 / agentic 显著增成本，需开关与并发上限 |

### 6.10 明确不做（本方案范围外）

- 不引入 DocTypeClassifier if-else 业务分支替代 persona（违反 AGENTS.md 4 层适配；侧重配置应数据驱动）。
- 不硬编码任何客户仓库路径/品牌/路由。
- 不把数百 KB 中间产物塞回 LangGraph state（继续 Redis）。
- **本方案暂不实施任何上述代码改动。**

---

## 7. 优先级与验收标准

### 7.1 优先级

| 优先级 | 项 | 预估影响 | 风险 |
|--------|----|----------|------|
| **P0** | 侧重切片 prompt + 按类型选文件 + 兼容扩展 JSON | 8 种文档差异立即可见 | 低（向后兼容） |
| **P1** | Token 预算 + 任务一 citation 校验 + 类型确定性扫描 | 降幻觉、稳窗口 | 中（扫描器假阳性） |
| **P2** | 多视角默认策略 + 有限 agentic 补洞 | 难类型质量 | 高（成本/时延） |

### 7.2 验收标准（实施阶段再用）

1. **Prompt 单测**：对 8 种 `report_type` 格式化后的 `CODE_LEARNING_PROMPT`，断言**只出现当前类型侧重词**，且不出现「8 种全量清单」其它类型标题行。
2. **选文件单测**：同一 `file_index` fixture 下，`api_doc` 选取的 controller/router 占比 > `testcase`；`testcase` 的 `tests/` 占比更高。
3. **Schema 单测**：mock LLM 返回带 `test_points` 的 JSON，`learn_code` 结果含该字段；旧四字段仍存在。
4. **回归**：architecture / api_doc 现有 e2e / functional 不回退（endpoints 仍进入 outline 骨架）。
5. **质量抽检（人工）**：对同一开源小仓生成 testcase vs architecture 的 `summary`，主题重合率应显著下降（可用简单关键词 Jaccard 阈值作门禁辅助）。
6. **通用性**：评测仓不得依赖某一私有产品名；fixture 使用合成仓库。

### 7.3 建议实施顺序（未来）

1. 新增 `learning_focus.py` + 改 `CODE_LEARNING_PROMPT` + `learn_code.format`
2. `select_key_files(report_type=...)`
3. 扩展 JSON + 单测
4. citation 后校验
5. 类型扫描器（先 testcase / defect）
6. token 预算
7. 多视角策略评估

---

## 8. 研究笔记索引

| 来源 | 关键文件 / 概念 |
|------|----------------|
| Aider | `aider/repomap.py`：`RepoMap`、`get_ranked_tags_map_uncached`、personalized PageRank、`map_tokens` |
| DeepWiki-Open | `api/prompts.py`：Deep Research 多轮；`CODEMAP_*` verbatim grounding；`api/services/research.py` / `codemap.py` |
| RepoAgent | `repo_agent/prompt.py` anti-speculation；`chat_engine.build_prompt` 双向引用；`file_handler` AST |
| OpenDeepWiki | `prompts/catalog-generator.md`：VERIFY FIRST / NO FABRICATION / 能力地图；工具 WriteCatalog |
| Continue | `core/indexing`：CodeSnippets + FTS + LanceDB；内容寻址增量索引 |
| docbot | `prompts.py` / `code_learner.py` / `multi_perspective_learner.py` / `perspectives.py` / `ARCHITECTURE.md` §15–§16 |

---

## 9. 结论标注

> **本方案为开源对标研究产出的代码级优化设计文档，暂不实施。**  
> 任何落地需按 AGENTS.md「Ask first」：涉及 State/schema 扩展、流水线行为变更时，先经确认再改代码。

---

## 附录 A：建议的 `CODE_LEARNING_PROMPT` 侧重块目标形态（示意）

```text
# 报告类型与学习侧重
当前报告类型: testcase
学习侧重维度:
- 可测试点
- 边界条件
- 异常路径
- 测试覆盖盲区

必覆盖检查清单:
1. 从公开函数/API 列出可测试点（带 path:line）
2. 基于文件索引对比 tests/ 与实现，列出覆盖盲区；不得虚构测试文件
3. 异常路径须指向真实 except/Result/error 处理代码

禁止: 输出部署拓扑长文、完整 API 手册、空泛架构综述。
```

（每种 report_type 仅替换本块；公共「路径硬约束 / 术语硬约束 / 公共 JSON 四字段」保持不变。）

## 附录 B：筛选时评估过但未进入 Top5 的项目

| 项目 | 未入选主因 |
|------|------------|
| OpenHands | 偏通用软件工程 Agent，文档流水线弱 |
| SWE-agent | ACE/修 issue 导向 |
| Mentat / Code2Doc | 活跃度或与「多文档类型」相关度不足 |
| GPT-Engineer | 偏从零生成项目 |
| Sourcegraph Cody（开源部分） | 与 Continue 索引能力重叠，文档生成链路弱 |

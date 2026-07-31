# 2025-2026 主流开源 AI Agent 理解代码仓库方法论研究报告（扩展版）

> 研究对象：Aider、STORM/Co-STORM、SWE-agent、Continue.dev、Cursor、RepoCoder、CodeRAG、**OpenHands**、**Moatless Tools**、**AutoCodeRover**、**Cline/Roo Code**、**RepoGraph/CodeRepo-Bench**
> 研究维度：索引方式、上下文选择、防幻觉机制、迭代检索-生成、验证链、多语言支持、2025-2026 新趋势
> 报告日期：2026-07-30
> 信息来源：各项目官方文档、arXiv 论文、官方技术博客、源码分析（2023-2026）
> 配套文档：`codebase-understanding-research.md`（v1，覆盖前 7 个项目的技术细节）

---

## 摘要

本报告在 v1 基础上扩展，新增 5 类 2025-2026 年代表性项目（OpenHands、Moatless Tools、AutoCodeRover、Cline/Roo Code、RepoGraph/CodeRepo-Bench），系统对比 12 类主流方案在"理解代码仓库"上的方法论。研究表明：

1. **2025-2026 年范式收敛**：业界从"单一索引"走向 **"AST 符号 + 调用图 + 向量库 + FTS + FSM 状态机"五层混合**，并普遍引入 **"代码即行动（CodeAct）"** 与 **"上下文压缩器（Condenser）"** 两条新主线。
2. **FSM（有限状态机）成新趋势**：Moatless Tools 用 FSM 替代自由 ReAct 循环，每个状态绑定专用 prompt + 工具集，显著降低 agent 漂移。
3. **SBFL（频谱故障定位）回归**：AutoCodeRover 把传统软件工程的 SBFL 与 LLM agent 结合，用测试通过/失败频谱为符号打"可疑度分"，精准定位 bug 相关代码。
4. **MCP（模型上下文协议）标准化**：Cline / Cursor / OpenHands 全面拥抱 MCP，把工具描述、技能、外部资源统一为可按需加载的文件原语。
5. **知识图谱化**：CodeGraph（2026）等工具把代码库预构建为可交互知识图谱，让多个 AI agent 共享同一份结构化代码认知。

本报告最后对比 docbot 现状（已有 tree-sitter / RAG / 引用校验 / 符号白名单 / 签名直填），指出 **8 项可借鉴的代码级技术点**，按优先级排序。

---

## 一、Aider —— tree-sitter Repo Map + PageRank 符号排序

### 1.1 核心机制

Aider 不向 LLM 发送整个仓库，而是发送一份**整个 git 仓库的精简地图（Repo Map）**，包含最重要的类、函数及其签名行。它把仓库建模为**图**：节点=源文件，边=文件间依赖（基于符号定义/引用），用**类 PageRank 图排序**计算每个符号的"重要性分数"（被引用越多越重要），再按 `--map-tokens`（默认 1k tokens）预算只发送排名最高的符号。

### 1.2 2025-2026 改进

- 从早期 `py-tree-sitter-languages` 迁移到 **`tree-sitter-language-pack`**（与 docbot 一致），语言覆盖扩展到 18 种（含 C#/VB.NET）。
- `tags.scm` 查询文件持续社区维护，对 Go / Rust / TypeScript 的签名提取更完整。
- **Repo Map 动态扩缩**：当无文件加入聊天时，map 显著扩大让 LLM 尽量理解全仓；有文件加入时收缩，把预算让给真实文件内容。

### 1.3 可借鉴代码级技术点

- **PageRank 符号排序**（docbot 目前只有"被调用次数"简单计数，缺 PageRank）：见 `aider/repomap.py` 的 `get_ranked_tags` 实现，用 `networkx.pagerank` 在文件依赖图上迭代。
- **tree-sitter `tags.scm` 查询**：aider 的 `aider/queries/` 目录有 18 种语言的符号抽取查询文件，可直接复用。

> 详细机制见 v1 报告第一节；官方文档：[aider.chat/docs/repomap](https://aider.chat/docs/repomap.html)

---

## 二、SWE-agent —— ACI 接口 + edit 后 lint

### 2.1 核心机制

SWE-agent（Princeton NLP，arXiv:2405.15793）提出 **Agent-Computer Interface（ACI）**：为 LM agent 专门设计计算机接口，而非复用人类 CLI。核心工具：`open_file`（窗口化查看，默认 100 行）、`scroll_down/up`、`search_dir`/`search_file`（正则搜索，只回文件+行号）、`edit <start>:<end>`（行号精确编辑）。

### 2.2 2025-2026 改进

- **edit 后自动 lint** 成为行业事实标准，被 OpenHands、Cline、Roo Code 普遍采纳。
- ACI 的"状态显式化"原则（每步回显 `open_file`/`working_dir` JSON）演化为 **Condenser + 事件流**架构（OpenHands）。
- SWE-agent 团队后续推出 **SWE-bench Verified**（2024-2025）与 **SWE-rebench**（2025，腾讯团队），推动评测从静态到动态。

### 2.3 可借鉴代码级技术点

- **edit 后 lint 回灌**（docbot 目前无此机制）：文档中代码示例生成后立即 lint，错误回灌 LLM 修正。
- **行号精确编辑**：避免 SEARCH/REPLACE 歧义。

> 详细机制见 v1 报告第二节；论文：[arXiv:2405.15793](https://arxiv.org/abs/2405.15793)

---

## 三、STORM / Co-STORM —— 多视角提问 + 强制 Grounding

### 3.1 核心机制

STORM（Stanford OVAL，arXiv:2402.14207）把"研究主题"拆成**多视角提问 + 模拟对话**，强制 grounding 到检索源。Co-STORM（arXiv:2408.15232）引入三类角色协作（LLM experts / Moderator / Human）+ 动态更新的 **Mind Map**（层级概念结构）。

### 3.2 2025-2026 改进

- **Co-STORM 的 Moderator 角色**：从检索器发现但未使用的片段中生成"启发性问题"（探索 unknown unknowns），这一思路被 2025 年的 **agentic RAG** 普遍借鉴。
- **分层检索（hierarchical retrieval）**：2025 年 STORM 团队提出，先用粗粒度检索定位相关模块，再用细粒度检索定位具体段落。
- **dspy 模块化**：每个模块（Knowledge Curation / Outline / Article Gen / Polish）接口清晰可替换，成为 2025 年 agent 框架的设计范式。

### 3.3 可借鉴代码级技术点

- **多视角驱动文档维度**（docbot 已有 `multi_perspective_learner.py`，但视角挖掘可更深）。
- **Mind Map 层级摘要**：长文档用层级大纲维护"已写/待写/引用源"。

> 详细机制见 v1 报告第三节

---

## 四、Continue.dev —— 四层混合索引

### 4.1 核心机制

Continue.dev 的 `@codebase` 建立在**四类并存索引**上：`ChunkCodebaseIndex`（tree-sitter 代码分块）、`LanceDbIndex`（嵌入向量，默认 `all-MiniLM-L6-v2`）、`FullTextSearchCodebaseIndex`（SQLite FTS5 trigram）、`CodeSnippetsCodebaseIndex`（tree-sitter AST 符号）。查询时三路并发检索，结果融合。

### 4.2 2025-2026 改进

- **collapseChildren 策略**（保留类/函数签名，折叠方法体）成为 IDE 助手标配，与 Aider Repo Map 思路一致。
- **增量索引**：`getComputeDeleteAddRemove` 计算文件变更集合，只重算受影响 chunk。
- **`tag_catalog` 表**：用 git commit/artifact hash 标记索引版本，避免脏数据混入。

### 4.3 可借鉴代码级技术点

- **FTS5 trigram 关键词倒排**（docbot 有 BM25，但无 FTS5 trigram，对短标识符匹配更精确）。
- **三路混合检索融合**（docbot 已有 qdrant + bm25，可补 AST 符号检索作为第三路）。

> 详细机制见 v1 报告第四节

---

## 五、Cursor —— 动态上下文发现

### 5.1 核心机制

Cursor 在 2026 年 1 月提出 **"Dynamic Context Discovery"**：前期给 agent 尽少细节，让 agent 自主按需拉取相关上下文，文件作为统一原语。底层用 embeddings（turbopuffer，1T+ 向量）+ fast regex search 索引。

### 5.2 2025-2026 改进（五项技术）

1. **长工具响应转文件**：shell/MCP 长输出不截断，写文件供 agent 按需读取。
2. **摘要时引用聊天历史文件**：解决摘要的有损压缩问题。
3. **Agent Skills 开放标准**：技能是文件，agent 用 grep/语义搜索动态拉取。
4. **MCP 工具按需加载**：工具描述同步到文件夹，agent 只收到工具名静态提示，按需查描述。A/B 测试 **总 token 降 46.9%**。
5. **终端会话即文件**：集成终端输出同步到本地文件系统。

### 5.3 可借鉴代码级技术点

- **MCP 工具按需加载**（docbot 当前工具描述全量注入 prompt，可借鉴按需加载降 token）。
- **文件原语 + 动态发现**：检索结果落文件，agent 按需 grep 读取。

> 详细机制见 v1 报告第五节；[Cursor Dynamic Context Discovery](https://cursor.com/blog/dynamic-context-discovery)

---

## 六、RepoCoder —— 迭代检索-生成

### 6.1 核心机制

RepoCoder（Microsoft，arXiv:2303.12570，EMNLP 2023）提出 **迭代检索-生成范式**：单次检索不够（初始查询信息不足），应**用生成结果作为新查询再检索**，多轮逼近正确上下文。

### 6.2 2025-2026 改进

- **Iter-RETGEN** 成为 2025 年 Advanced RAG 的标准范式之一，被多个 agent 框架内置。
- **收敛检测**：若新一轮检索未返回新片段，则判定收敛停止迭代。

### 6.3 可借鉴代码级技术点

- **迭代检索-生成**（docbot 目前是单次检索，缺迭代收敛机制）。

> 详细机制见 v1 报告第六节

---

## 七、CodeRAG / CoVe 验证链

### 7.1 核心机制

- **Chain-of-Verification (CoVe)** 四步：基线响应 → 规划验证问题 → 执行验证 → 修正响应。
- **Iterative Grounding**（arXiv:2401.01701）：代码生成中每步落地到检索片段，不落地即重检索。
- **GraphRAG**：用代码调用图/依赖图做检索，捕获跨文件关系。

### 7.2 可借鉴代码级技术点

- **CoVe 验证链**（docbot 有符号白名单校验，但无完整的"规划验证问题→执行验证→修正"链）。

> 详细机制见 v1 报告第七节

---

## 八、OpenHands（原 OpenDevin）—— CodeAct + Condenser 上下文压缩

### 8.1 核心思想

OpenHands（All-Hands-AI，前身 OpenDevin，75.9k stars）是 2025 年最火的开源 AI 软件工程师框架。其核心 agent **CodeActAgent** 基于 **CodeAct 理念**（arXiv:2402.01030）：**把 LLM 的动作空间统一为"生成可执行 Python 代码"**，而非传统的"调用预设工具 API"。这让 agent 能在单个动作中封装完整逻辑流程（调用多个函数、控制执行顺序、处理中间结果）。

### 8.2 工具系统（混合型：代码执行 + 预定义工具）

CodeActAgent 是混合型 agent，既允许执行任意代码，也提供特定工具集：

| 工具 | 作用 | 设计要点 |
|------|------|---------|
| `create_cmd_run_tool` | 执行 bash 命令 | 系统级操作 |
| `IPythonTool` (`execute_ipython_cell`) | 在 IPython 环境执行 Python | 数据计算、逻辑执行 |
| `str_replace_editor` / `LLMBasedFileEditTool` | 编辑文件 | 字符串替换或 LLM 驱动编辑 |
| `BrowserTool` | 浏览器交互 | 网页爬取、页面操作 |
| `ThinkTool` | 记录思考过程 | 推理可观测 |
| `FinishTool` | 结束任务 | 完成信号 |
| `CondensationRequestTool` | 请求压缩对话历史 | 上下文管理 |
| `create_task_tracker_tool` | 任务管理 | plan mode 使用 |

### 8.3 索引方式：无预建索引，靠代码执行 + sandbox 插件

OpenHands **不预建向量索引或 AST 图**，而是让 agent 通过 `execute_bash`（grep/find/cat）和 `str_replace_editor` 实时检索仓库。这是"agentic 检索"路线（与 SWE-agent 一致）。沙箱环境通过 `sandbox_plugins` 加载：

- **AgentSkillsRequirement**：提供 Python 工具函数（文件操作、目录浏览、代码执行），需在 Jupyter 之前初始化。
- **JupyterRequirement**：启动 Jupyter Kernel Gateway（端口 40000-49999 自动分配），提供 IPython 异步执行，支持超时控制、文本/图片输出捕获。

### 8.4 上下文压缩器（Condenser）—— 2025 年关键创新

这是 OpenHands 区别于 SWE-agent 的最重要机制。长 trajectory 会让上下文窗口爆炸，OpenHands 引入 **Condenser**：

```python
class CodeActAgent(Agent):
    def __init__(self, config, llm_registry):
        self.conversation_memory = ConversationMemory(self.config, self.prompt_manager)
        self.condenser = Condenser.from_config(self.config.condenser, llm_registry)
```

- **ConversationMemory**：管理"行动-观察"历史对。
- **Condenser**：当上下文接近窗口上限时，用 LLM 压缩历史（保留关键事实，丢弃冗余），并可通过 `CondensationRequestTool` 让 agent 主动请求压缩。
- **模型路由**：`LLMRegistry.get_router` 根据任务复杂度动态选择模型，兼顾性能与成本。

### 8.5 防幻觉机制

1. **代码执行即验证**：agent 生成的代码直接在 sandbox 执行，执行结果（包括异常/堆栈）回灌，agent 据此自我修正——这是 CodeAct 的天然反馈循环。
2. **IPython 输出捕获**：文本与图片 URL 结构化捕获，避免 LLM 误读。
3. **事件驱动 + 安全介入**：基于风险分析在执行前审核或拦截动作（如破坏性 bash 命令）。

### 8.6 2025-2026 改进（V0 → V1）

- **V1 SDK 重构**（2025）：从 V0 进化到 V1，设计简洁接口（默认仅需几行代码），推出 **Agent Canvas**（自托管开发者控制中心，可运行 OpenHands / Claude Code / Codex / Gemini 等 ACP 兼容 agent）。
- **子智能体委托机制**：父 agent 创建并监控子 agent，继承模型配置与工作空间上下文，实现结构化并行处理与隔离。
- **AgentContext**：集中管理系统/用户消息前缀后缀 + 用户定义的 Skill（从 `.openhands/skills/` Markdown 文件加载，兼容 `.cursorrules`、`agents.md`）。
- **技能触发模式**：永久激活（trigger=None）+ 条件激活（关键词匹配触发，可含 MCP 工具）。

### 8.7 可借鉴代码级技术点

- **Condenser 上下文压缩**（docbot 目前无长对话压缩机制，长文档生成易超窗口）：实现 `Condenser.from_config`，当 token 接近上限时用 LLM 压缩历史。
- **CodeAct 代码即行动**：把多个工具调用封装为一段 Python 代码执行，减少多轮往返。
- **子智能体委托**：父 agent 委托子 agent 处理子任务（如"分析模块 A""分析模块 B"并行）。

> 参考：[OpenHands GitHub](https://github.com/All-Hands-AI/OpenHands)、[CodeAct 论文 arXiv:2402.01030](https://arxiv.org/abs/2402.01030)、[拆解 OpenHands 系列博客](https://www.cnblogs.com/rossiXYZ/p/19620422)

---

## 九、Moatless Tools —— FSM 状态机 + 向量索引代码搜索

### 9.1 核心思想

Moatless Tools（Albert Örwall 创建，SWE-bench Lite 第 6 名）是一个实验性项目，核心创新是**把 agent 循环建模为有限状态机（FSM）**，而非自由的 ReAct 循环。每个状态有自己的 prompt 和响应处理机制，agent 在不同状态间转换。这种设计**显著降低 agent 漂移**，因为每步的可用工具和提示都受当前状态约束。

### 9.2 索引方式：向量索引 + 代码搜索工具

Moatless Tools **预建向量索引**（与 LlamaIndex 集成），并提供一组代码搜索工具：

- **`file_search`**：按文件名模式搜索（支持模糊匹配）。
- **`class_search` / `function_search`**：按类名/函数名搜索（基于向量相似度 + 关键词）。
- **`code_search`**：按自然语言查询搜索代码片段（语义检索）。
- **`string_query`**：精确字符串/正则搜索（类似 grep）。
- **`find_class` / `find_function`**：按符号全限定名定位。

向量索引让 Moatless 比 SWE-agent 的纯 grep 检索更精准（尤其在大型仓库中），同时 FSM 约束让 agent 不会无目的游荡。

### 9.3 FSM 状态流转

```
[Locate] → [Search] → [View] → [Edit] → [Resolve]
   ↑           |          |         |
   └───────────┴──────────┴─────────┘
        (状态间转换, 每个状态绑定专用 prompt + 工具集)
```

- **Locate**：定位相关文件/类/函数（用向量搜索）。
- **Search**：在定位范围内做细粒度检索。
- **View**：查看具体代码内容。
- **Edit**：用 Aider 风格的编辑块修改代码。
- **Resolve**：验证修复（跑测试）。

### 9.4 防幻觉机制

- **Aider 编辑块**：复用 Aider 的 SEARCH/REPLACE 块，编辑前精确匹配校验。
- **状态约束**：每步只能用当前状态允许的工具，避免 agent 在错误阶段做错误操作。
- **向量检索 grounding**：所有代码引用来自向量索引的真实片段。

### 9.5 2025-2026 改进

- **SWE-SEARCH**（2025，arXiv:2502.11458）：基于 Moatless 框架，引入 **Monte Carlo Tree Search（MCTS）**，在动态代码环境中运行，支持类似 git 提交树的状态回溯——让 agent 探索不同解决方案轨迹并回退。
- **灵活状态空间**：状态空间可配置，支持自定义状态与转换规则。
- **Docker 化运行**（2025-05）：支持异步与 Docker 部署。

### 9.6 可借鉴代码级技术点

- **FSM 状态机**（docbot 目前是 LangGraph 线性流程，可借鉴 FSM 约束 agent 行为）：每个状态绑定专用 prompt + 工具集。
- **向量索引代码搜索**（docbot 有 qdrant，但缺 `class_search`/`function_search` 这类按符号类型分路的检索）。
- **MCTS 状态回溯**（高级，适合复杂修复任务）：让 agent 探索多方案并回退。

> 参考：[Moatless Tools GitHub](https://github.com/aorwall/moatless-tools)、[SWE-SEARCH 论文](https://arxiv.org/abs/2502.11458)

---

## 十、AutoCodeRover —— AST 导航 + SBFL 频谱故障定位

### 10.1 核心思想

AutoCodeRover（ISSTA'24，arXiv:2404.05427）把传统软件工程的 **程序分析技术**（AST 导航 + 频谱故障定位）与 LLM agent 结合。核心理念：**LLM 擅长理解自然语言，但定位 bug 需要程序分析能力**——用 AST 帮 agent 精准导航代码结构，用 SBFL 用测试通过/失败频谱为符号打"可疑度分"。

### 10.2 上下文检索 API（为 agent 定制）

AutoCodeRover 设计了一组 **上下文检索 API**，让 agent 从 issue 中的 "Hints"（方法名/类名/文件名/代码片段）出发查找代码：

| API | 作用 |
|-----|------|
| `search_method(name)` | 按方法名搜索 |
| `search_class(name)` | 按类名搜索 |
| `search_code(snippet)` | 按代码片段搜索 |
| `search_code_in_file(snippet, file)` | 在指定文件内搜索代码 |
| `get_code_docs(class_name)` | 获取类的文档 |
| `get_method_full_snippet(name)` | 获取方法完整实现 |

### 10.3 分层上下文搜索（Hierarchical Context Search）

```
Layer 1: 多个 API 并行调用 (从 issue hints 出发)
    ↓
Layer 2: 分析检索结果, 判断是否足够理解问题
    ↓ (不足)
Layer 3: 用新发现的符号构造新 API 调用, 迭代检索
    ↓ (足够)
Patch Generation
```

- 每层允许 LLM 选择多个 API 调用，并指示它仅选择必要的调用。
- 执行后将新检索的代码片段加入当前上下文，LLM 分析是否足以理解问题，决定是否继续迭代。

### 10.4 SBFL（Spectrum-Based Fault Localization）—— 核心创新

这是 AutoCodeRover 区别于其他 agent 的关键。SBFL 是传统软件工程的故障定位技术：

- **输入**：一组测试用例（通过 + 失败）+ 每个测试用例覆盖的代码行/方法。
- **输出**：每个程序位置的"可疑度分数"（失败测试覆盖越多，可疑度越高）。
- **AutoCodeRover 用方法级 SBFL**：为每个方法打可疑度分，把高分方法作为 "hints" 呈现给 agent。

```
测试通过/失败频谱 → 方法级可疑度分数 → 高分方法作为 hints 注入 agent prompt
                                                    ↓
                                agent 在 hints 与 issue 描述间交叉引用
                                                    ↓
                                更精准地调用 search_method 定位 bug
```

### 10.5 补丁生成 + linter

- 利用收集到的代码上下文生成补丁。
- **linter 检测 Python 语法特性问题**（类似 SWE-agent）。
- 若补丁无法通过测试套件，进入重试循环。

### 10.6 防幻觉机制

- **AST 导航**：agent 不靠 grep 模糊定位，而是用 AST 精准定位方法/类/字段。
- **SBFL 交叉引用**：故障定位结果与 issue 描述交叉验证，降低误判。
- **linter 反馈**：补丁生成后语法校验。

### 10.7 2025-2026 改进

- SWE-bench Lite 上实现 30.67% 修复率（2024-06 版本）。
- **SBFL + BM25 结合**：SBFL 识别的方法与 BM25 关键词检索结果融合，进一步提升定位准确率。
- **reproducer 测试用例**：利用 reproducer 提供的测试用例 + 仓库内集成测试（integration tests）做故障定位，比仅用 issue 测试用例效果更好。

### 10.8 可借鉴代码级技术点

- **上下文检索 API 分层**（docbot 目前是单层检索，可借鉴分层迭代：先粗搜定位，再细搜补充）。
- **SBFL 频谱定位**（高级，需有测试用例场景，对 docbot 的"缺陷报告"类型文档可借鉴：若仓库有测试，用测试通过/失败频谱定位可疑代码）。
- **AST 精准导航**（docbot 有 AST，但未提供 `search_method`/`search_class` 这类按符号类型的检索 API 给 agent 调用）。

> 参考：[AutoCodeRover 论文 arXiv:2404.05427](https://arxiv.org/abs/2404.05427)、[论文笔记](https://www.cnblogs.com/mianmaner/p/19030399)、源码 `app/analysis/sbfl.py`

---

## 十一、Cline / Roo Code —— VSCode AI 编程助手 + MCP

### 11.1 核心思想

Cline（原 Claude Dev，VSCode 插件）是 2025 年最流行的开源 VSCode AI 编程助手之一。其设计哲学是**"文件原语 + 显式工具集"**：agent 通过一组明确的文件操作工具与代码库交互，所有工具调用对开发者可见可控。Roo Code 是 Cline 的 fork，针对企业级场景深度优化。

### 11.2 工具系统（文件原语为中心）

Cline 的 system prompt（`src/core/prompts/system.ts`）明确定义工具列表：

| 工具 | 作用 | 设计要点 |
|------|------|---------|
| `read_file` | 读取文件 | 支持 line range，避免全文加载 |
| `write_to_file` | 写入文件 | 整文件覆盖 |
| `replace_in_file` | 局部替换 | SEARCH/REPLACE 块（借鉴 Aider） |
| `search_files` | 正则搜索 | 跨文件 grep |
| `list_files` | 列出目录 | 了解结构 |
| `list_code_definition_names` | 列出代码定义 | **tree-sitter 提取符号名** |
| `execute_command` | 执行命令 | bash/cmd |
| `use_mcp_tool` | 调用 MCP 工具 | 外部工具集成 |

### 11.3 索引方式：无预建向量索引，靠 tree-sitter 符号 + grep

Cline **不预建向量索引**，而是：
- 用 **tree-sitter** 把代码表示为结构化 token（`list_code_definition_names` 工具），让 agent 快速了解文件内的符号定义。
- 用 `search_files`（正则 grep）+ `list_files`（目录遍历）做实时检索。
- 通过 **MCP（Model Context Protocol）** 集成外部工具（如数据库查询、API 调用、自定义检索器）。

### 11.4 Checkpoints 机制（git 快照）

Cline 的 **Checkpoints** 是其防幻觉与可恢复性的核心：
- 每次重要修改前，自动创建 git 快照（worktree 级别）。
- agent 出错或用户不满意时，可一键回滚到任意 checkpoint。
- 这解决了 agent "改坏了无法恢复"的痛点。

### 11.5 防幻觉机制

- **replace_in_file 精确匹配**：SEARCH 块必须精确匹配文件内容，否则报错（借鉴 Aider）。
- **工具调用对用户可见**：每个工具调用都需用户确认（可配置自动批准），人机协同降低幻觉风险。
- **tree-sitter 符号列表**：agent 看到的是真实 AST 符号，非编造。

### 11.6 Roo Code 的企业级增强

| 功能维度 | Cline | Roo Code |
|---------|-------|---------|
| 支持语言 | 15+ 通用语言 | 专注 Java/Python/Go |
| 调试能力 | 基础错误检测 | 智能错误链路分析（Java Stack Trace 解析 92%） |
| 团队协作 | 个人代码管理 | 团队知识库集成 |
| 代码审查 | 无 | 集成 SonarQube 规则集 |
| 部署支持 | 无 | Kubernetes/Docker 模板生成 |

### 11.7 2025-2026 改进

- **MCP 全面拥抱**：Cline 成为 MCP Client 的代表实现，可调用任意 MCP Server（如数据库、Jira、Slack），让 agent 能力边界大幅扩展。
- **tree-sitter 结构化 token**：把代码表示为结构化 token，提供更多透明度，尤其在 system prompt 方面。
- **智能调试助手**（Roo Code）：运行时分析定位错误根源，提供带修复建议的错误树。

### 11.8 多语言支持

Cline 依赖 tree-sitter，理论上支持 tree-sitter 所有语言。但 `list_code_definition_names` 的符号提取质量因语言而异（Python/JS/TS 最好，Go/Java 次之，C# 需要额外配置）。

### 11.9 可借鉴代码级技术点

- **`list_code_definition_names` 工具**（docbot 有 repo_map，但未作为 agent 可调用工具暴露，而是静态注入 prompt——可借鉴把符号列表做成工具，让 agent 按需查询）。
- **Checkpoints 机制**（docbot 有 LangGraph checkpointer，但未做"文档生成回滚"——可借鉴 git 快照让用户回滚到任意文档版本）。
- **MCP 工具集成**（docbot 有 `tools/code_graph_mcp.py` 和 `tools/git_mcp.py`，可进一步扩展 MCP 工具生态）。

> 参考：[Cline GitHub](https://github.com/cline/cline)、[Roo Code GitHub](https://github.com/RooVetGit/Roo-Code)、[Cline 技术分析](https://juejin.cn/post/7495365665844133928)

---

## 十二、RepoGraph / CodeRepo-Bench —— 仓库理解评测与知识图谱

### 12.1 核心思想

RepoGraph / CodeRepo-Bench 不是单一项目，而是 2025-2026 年涌现的**代码仓库理解评测基准 + 知识图谱工具**生态。代表性工作：

- **RepoBench**（arXiv:2306.03081）：仓库级代码补全 benchmark，评测 retrieval-augmented completion。
- **CoreCodeBench**（美团 2025，arXiv:2507.05281）：可配置的多场景仓库级 benchmark，专注评估 LLM 在真实软件开发场景中的仓库级代码生成能力。
- **CodeGraph**（2026）：把任意代码库预构建为可交互的结构化知识图谱，让 Claude Code / Gemini / Cursor 等 8+ agent 共享同一份代码认知，解决"反复扫描文件、Token 消耗爆炸、上下文混乱"痛点。
- **GraphRAG for Code**：用代码调用图/依赖图做检索，捕获跨文件关系。

### 12.2 CodeGraph 知识图谱化（2026 新趋势）

CodeGraph 的核心是把代码库**预构建为知识图谱**：

- **节点**：类 / 函数 / 方法 / 模块（含签名、文档、行号）。
- **边**：调用关系 / 继承关系 / import 依赖 / 类型引用。
- **查询**：agent 通过图谱查询 API（如"查找所有调用 `UserService.create()` 的位置"）精准定位，而非 grep。

这比 Aider 的轻量 Repo Map 更重，但比完整 IDE 索引（如 LSP）更轻，定位在"为 AI agent 服务的中间层"。

### 12.3 评测维度（RepoBench / CoreCodeBench）

| 评测维度 | 说明 |
|---------|------|
| 仓库级补全 | 跨文件代码补全准确率 |
| 检索增强 | retrieval-augmented completion 效果 |
| 多场景 | CoreCodeBench 支持可配置多场景 |
| 演进感知 | 用项目历史版本评估（避免数据污染） |

### 12.4 2025-2026 趋势

- **知识图谱化**：从 Aider 的轻量 Repo Map，到 CodeGraph 的完整知识图谱，2026 年趋势是"预构建图谱 + 多 agent 共享"。
- **演进感知评测**：用项目历史版本评估，避免用最新版本训练导致的数据污染。
- **Graph Engineering**：从 Agent Loop 到 Agent Graph 的工程升级，关注分工、交接、校验、回退。

### 12.5 可借鉴代码级技术点

- **预构建知识图谱**（docbot 的 `code_graph.py` 是内存图谱，可借鉴 CodeGraph 持久化图谱供多会话共享）。
- **图谱查询 API**（docbot 有 `get_module_dependencies`/`get_call_edges`/`get_inheritance_edges`，可包装成 agent 可调用工具）。

> 参考：[RepoBench arXiv:2306.03081](https://arxiv.org/abs/2306.03081)、[CoreCodeBench arXiv:2507.05281](https://arxiv.org/abs/2507.05281)、[CodeGraph 教程](https://blog.csdn.net/weixin_44092861/article/details/161458639)

---

## 十三、对比矩阵（12 个项目全维度对比）

| 项目 | 索引方式 | 上下文选择 | 防幻觉机制 | 迭代检索 | 验证链 | 多语言 | 2025-2026 新改进 |
|------|---------|-----------|-----------|---------|--------|--------|----------------|
| **Aider** | tree-sitter AST + 文件依赖图 + **PageRank** | 图排序选 top 符号，token 预算动态调节 | map 全来自真实 AST；SEARCH/REPLACE 精确匹配；编辑后 lint | 否（单次注入 map） | 否 | 18 种（含 C#/VB.NET） | tree-sitter-language-pack 迁移；动态扩缩 map |
| **SWE-agent** | 无预建索引，agent 用命令实时检索 | agent 自主 open/scroll/search 决定可见窗口 | edit 后自动 lint 回灌；状态 JSON 显式回显 | 否（trajectory 累积） | 否 | 任意（靠 grep） | SWE-bench Verified；SWE-rebench 动态评测 |
| **STORM/Co-STORM** | 外部检索源 + mind map 层级结构 | 多视角驱动提问；模拟对话渐进积累 | 强制 grounding 到检索源；正文带引用；强弱模型分工 | 是（对话迭代） | 否 | N/A | Moderator 角色；分层检索；dspy 模块化 |
| **Continue.dev** | 四层：tree-sitter chunk + LanceDB 向量 + FTS5 trigram + AST 符号 | 三路混合检索融合 | 检索结果带路径行号；tag_catalog 版本标记 | 否 | 否 | tree-sitter 支持 | collapseChildren 签名优先；增量索引 |
| **Cursor** | embeddings（turbopuffer 1T+）+ regex 索引 | 动态上下文发现：agent 按需拉取，文件为原语 | 动态发现减少矛盾上下文；摘要+历史文件双轨 | 是（agent 按需拉取） | 否 | 任意 | MCP 工具按需加载（token 降 46.9%）；Agent Skills 文件化 |
| **RepoCoder** | 仓库 chunk 库（BM25/dense） | 迭代：用生成代码再检索，多轮拼接上下文 | 每轮生成有检索 grounding；迭代收敛修正 | **是（核心范式）** | 否 | 任意 | Iter-RETGEN 成为 Advanced RAG 标准 |
| **CodeRAG/CoVe** | 视方法：向量/图/混合 | 视方法 | CoVe 验证链；Iterative Grounding | 是 | **是（CoVe 四步）** | 视方法 | GraphRAG 趋势 |
| **OpenHands** | 无预建索引，CodeAct 代码执行 + sandbox 插件 | agent 自主 bash/IPython/str_replace_editor | 代码执行即验证；IPython 输出捕获；事件驱动安全介入 | 是（trajectory 累积） | 否 | 任意 | **Condenser 上下文压缩**；V1 SDK；子智能体委托；Agent Canvas |
| **Moatless Tools** | **向量索引（LlamaIndex）** + 代码搜索工具 | **FSM 状态机**，每状态绑定 prompt + 工具集 | Aider 编辑块；状态约束；向量检索 grounding | 是（状态间迭代） | 否 | 任意 | **FSM 替代 ReAct**；SWE-SEARCH 引入 MCTS 状态回溯 |
| **AutoCodeRover** | **AST 导航 + SBFL 频谱定位** | 分层上下文搜索（多 API 并行 → 分析 → 迭代） | AST 精准导航；SBFL 交叉引用；linter 反馈 | **是（分层迭代）** | 否 | Python 为主 | **SBFL + BM25 融合**；reproducer 测试用例 |
| **Cline/Roo Code** | tree-sitter 符号 + grep（无向量索引）+ **MCP** | agent 用 read_file/search_files/list_code_defi 实时检索 | replace_in_file 精确匹配；工具调用可见；**Checkpoints git 快照** | 否 | 否 | tree-sitter 支持 | **MCP 全面拥抱**；Roo Code 企业级增强（SonarQube 集成） |
| **RepoGraph/CodeRepo-Bench** | **预构建知识图谱**（节点=符号，边=调用/继承/import） | 图谱查询 API 精准定位 | 图谱节点来自真实 AST | 是（图谱遍历） | 否 | 任意 | **CodeGraph 预构建图谱多 agent 共享**；演进感知评测 |

---

## 十四、docbot 现状对比与差距分析

### 14.1 docbot 现有能力

通过源码分析，docbot 目前已具备：

| 能力 | 实现文件 | 借鉴对象 | 成熟度 |
|------|---------|---------|--------|
| tree-sitter AST 抽符号 | `skills/docbot/repo_map.py` | Aider Repo Map | ✅ 成熟（支持 10 种语言含 C#/VB.NET） |
| 代码知识图谱（内存） | `skills/docbot/code_graph.py` | Codebase-Memory-MCP | ✅ 成熟（import/call/inherit 三类边） |
| 符号白名单校验 | `agents/docbot/symbol_validator.py` | Aider + CoVe | ✅ 成熟（PascalCase/camelCase/snake_case 标识符校验） |
| 签名直填 | `agents/docbot/signature_extractor.py` | Aider | ✅ 成熟（.NET Controller + FastAPI） |
| 三路混合检索 | `rag/qdrant_manager.py` + `rag/bm25_filter.py` + `rag/embeddings_filter.py` | Continue.dev | ✅ 成熟（qdrant 向量 + BM25 + embeddings 过滤） |
| 引用校验 | `skills/docbot/citation_extractor.py` | Continue.dev + STORM | ✅ 成熟 |
| 多视角学习 | `skills/docbot/multi_perspective_learner.py` | STORM | ✅ 成熟 |
| LangGraph 工作流 | `graph/builder.py` | — | ✅ 成熟 |
| LLM 分层 | `llm/client.py` (LLMTier) | STORM 强弱分工 | ✅ 成熟 |
| MCP 工具 | `tools/code_graph_mcp.py` + `tools/git_mcp.py` | Cline | ⚠️ 基础（仅 2 个 MCP 工具） |

### 14.2 差距分析（按优先级排序）

#### 差距 1：无 PageRank 图排序（高优先级）

- **docbot 现状**：`code_graph.py` 的 `get_entry_points` 只用"被调用次数"简单计数排序，无 PageRank。
- **业界标杆**：Aider 用 `networkx.pagerank` 在文件依赖图上迭代，计算每个符号的"重要性分数"。
- **影响**：docbot 的 repo_map 按文件路径遍历 + max_chars 截断，可能遗漏高中心性符号。
- **借鉴方案**：在 `code_graph.py` 新增 `pagerank_symbols()` 方法，用 `networkx.pagerank` 在符号依赖图上排序。

#### 差距 2：无迭代检索-生成（高优先级）

- **docbot 现状**：单次检索 → 单次生成，无 RepoCoder 范式的迭代收敛。
- **业界标杆**：RepoCoder 用生成结果作为新查询再检索，多轮逼近；AutoCodeRover 分层上下文搜索。
- **影响**：单次检索可能遗漏跨文件依赖，导致文档描述不完整。
- **借鉴方案**：在 content_filler 节点新增迭代循环：生成草稿 → 抽取 API 引用 → 反查仓库 → 补全签名 → 再生成。

#### 差距 3：无 Condenser 上下文压缩（中优先级）

- **docbot 现状**：长文档生成依赖 token_budget 分配，无 LLM 驱动的上下文压缩。
- **业界标杆**：OpenHands 的 `Condenser.from_config`，当 token 接近上限时用 LLM 压缩历史。
- **影响**：大仓库文档生成易超窗口，被迫截断丢信息。
- **借鉴方案**：在 `llm/token_budget.py` 新增 `Condenser` 类，当历史接近上限时用 LLM 压缩已写章节。

#### 差距 4：无 edit 后 lint 反馈（中优先级）

- **docbot 现状**：文档中代码示例生成后无 lint 校验。
- **业界标杆**：SWE-agent edit 后自动 lint；AutoCodeRover 补丁生成后 linter 检测语法。
- **影响**：文档中的代码示例可能有语法错误，影响可信度。
- **借鉴方案**：在 final_reviewer 节点新增代码示例 lint 校验，错误回灌 LLM 修正。

#### 差距 5：无 CoVe 完整验证链（中优先级）

- **docbot 现状**：有符号白名单校验（单点），但无完整的"规划验证问题 → 执行验证 → 修正"链。
- **业界标杆**：CoVe 四步验证链。
- **影响**：符号校验只能发现"不存在的符号"，无法发现"符号存在但描述错误"。
- **借鉴方案**：在 reviewer 节点新增 CoVe 验证链：从文档抽取事实声明 → 规划验证问题 → 反查仓库 → 修正。

#### 差距 6：无 FSM 状态机约束（低优先级）

- **docbot 现状**：LangGraph 线性流程，agent 行为靠 prompt 约束。
- **业界标杆**：Moatless Tools 的 FSM，每状态绑定专用 prompt + 工具集。
- **影响**：复杂任务中 agent 可能漂移。
- **借鉴方案**：LangGraph 本身支持状态机，可把当前线性流程改为 FSM（如"定位→检索→分析→生成→校验"五状态）。

#### 差距 7：无 SBFL 频谱定位（低优先级，场景受限）

- **docbot 现状**：无测试频谱分析。
- **业界标杆**：AutoCodeRover 的方法级 SBFL。
- **影响**：对"缺陷报告"类型文档，若仓库有测试，可用 SBFL 定位可疑代码，但需测试运行能力。
- **借鉴方案**：对 `report_type=defect` 且仓库有测试的场景，集成 SBFL（需测试运行环境，成本较高）。

#### 差距 8：MCP 工具生态有限（低优先级）

- **docbot 现状**：仅 `code_graph_mcp.py` + `git_mcp.py` 两个 MCP 工具。
- **业界标杆**：Cline 全面拥抱 MCP，可调用任意 MCP Server。
- **影响**：agent 能力边界受限。
- **借鉴方案**：扩展 MCP 工具（如 `search_method_mcp`、`find_class_mcp`、`get_callers_mcp`），让 agent 按需调用。

---

## 十五、可借鉴的代码级技术点汇总

### 15.1 PageRank 符号排序（Aider，高优先级）

```python
# 借鉴 Aider repomap.py 的 get_ranked_tags
import networkx as nx

def pagerank_symbols(code_graph):
    """在符号依赖图上跑 PageRank, 返回按重要性排序的符号."""
    G = nx.DiGraph()
    # 节点 = 符号全限定名
    for qname, node in code_graph.nodes.items():
        G.add_node(qname)
    # 边 = 调用/继承/import 关系
    for edge in code_graph.edges:
        G.add_edge(edge.source, edge.target)
    # PageRank 排序
    ranks = nx.pagerank(G, alpha=0.85)
    return sorted(ranks.items(), key=lambda x: x[1], reverse=True)
```

### 15.2 迭代检索-生成（RepoCoder，高优先级）

```python
# 借鉴 RepoCoder 的迭代收敛范式
def iterative_retrieve_generate(initial_context, repo_index, max_iters=3):
    context = initial_context
    for t in range(max_iters):
        draft = llm_generate_doc(context)
        new_api_refs = extract_api_mentions(draft)
        retrieved = hybrid_retrieve(new_api_refs, repo_index)
        new_chunks = retrieved - context
        if not new_chunks:  # 收敛
            break
        context = context | new_chunks
    return draft
```

### 15.3 Condenser 上下文压缩（OpenHands，中优先级）

```python
# 借鉴 OpenHands Condenser
class Condenser:
    def should_condense(self, history, token_count, max_tokens):
        return token_count > max_tokens * 0.8

    def condense(self, history, llm_client):
        # 用 LLM 压缩历史, 保留关键事实
        prompt = f"压缩以下对话历史, 保留关键代码引用与结论:\n{history}"
        return llm_client.complete(prompt)
```

### 15.4 分层上下文搜索 API（AutoCodeRover，中优先级）

```python
# 借鉴 AutoCodeRover 的上下文检索 API
class ContextRetrievalAPI:
    def search_method(self, name): ...      # 按方法名搜索
    def search_class(self, name): ...       # 按类名搜索
    def search_code(self, snippet): ...     # 按代码片段搜索
    def get_callers(self, method_qname): ... # 查找调用方
    def get_callees(self, method_qname): ... # 查找被调用方

    def hierarchical_search(self, issue_hints):
        # Layer 1: 多 API 并行从 hints 出发
        results = parallel_call([
            self.search_method(h) for h in issue_hints.method_names
        ])
        # Layer 2: 分析是否足够
        if self.is_sufficient(results):
            return results
        # Layer 3: 用新符号构造新 API 调用, 迭代
        new_symbols = extract_symbols(results)
        return self.hierarchical_search(new_symbols)
```

### 15.5 CoVe 验证链（CodeRAG，中优先级）

```python
# 借鉴 CoVe 四步验证链
def chain_of_verification(doc_draft, repo_index):
    # 1. 规划验证问题
    verify_questions = llm_plan_verification(doc_draft)
    # 2. 执行验证 (grounding 到仓库)
    answers = {}
    for q in verify_questions:
        evidence = hybrid_retrieve(q, repo_index)
        answers[q] = evidence
    # 3. 修正响应
    revised = llm_revise(doc_draft, verify_questions, answers)
    return revised
```

### 15.6 FSM 状态机（Moatless Tools，低优先级）

```python
# 借鉴 Moatless Tools 的 FSM 设计
class AgentStateMachine:
    STATES = {
        "locate": {"prompt": "...", "tools": ["file_search", "class_search"]},
        "search": {"prompt": "...", "tools": ["code_search", "string_query"]},
        "view":   {"prompt": "...", "tools": ["read_file"]},
        "edit":   {"prompt": "...", "tools": ["str_replace_editor"]},
        "resolve":{"prompt": "...", "tools": ["run_tests"]},
    }
    TRANSITIONS = {
        "locate": ["search"],
        "search": ["view", "locate"],
        "view":   ["edit", "search"],
        "edit":   ["resolve", "view"],
        "resolve": [],
    }
```

### 15.7 SBFL 频谱定位（AutoCodeRover，低优先级）

```python
# 借鉴 AutoCodeRover 的方法级 SBFL
def sbfl_localize(test_results, coverage_data):
    """test_results: [(test_id, passed)], coverage_data: {test_id: [method_qname]}"""
    passed_count = sum(1 for _, p in test_results if p)
    failed_count = len(test_results) - passed_count
    suspicion = {}
    for method in all_methods(coverage_data):
        # Ochiai 公式: suspicious = failed_covered / sqrt(failed * (failed_covered + passed_covered))
        failed_covered = count_covered(method, test_results, passed=False)
        passed_covered = count_covered(method, test_results, passed=True)
        if failed_count > 0:
            suspicion[method] = failed_covered / ((failed_count * (failed_covered + passed_covered)) ** 0.5)
    return sorted(suspicion.items(), key=lambda x: x[1], reverse=True)
```

### 15.8 MCP 工具按需加载（Cursor，低优先级）

```python
# 借鉴 Cursor 的 MCP 工具按需加载
class McpToolRegistry:
    def __init__(self):
        self._tool_index = {}  # 工具名 -> 描述文件路径

    def register(self, tool_name, desc_file_path):
        self._tool_index[tool_name] = desc_file_path

    def get_tool_description(self, tool_name):
        """按需读取工具描述, 而非全量注入 prompt."""
        with open(self._tool_index[tool_name]) as f:
            return f.read()
```

---

## 十六、2025-2026 年新技术趋势总结

### 趋势 1：从 Agent Loop 到 Agent FSM/Graph

- **2024 年**：ReAct 自由循环（SWE-agent、OpenHands V0）。
- **2025-2026 年**：FSM 状态机（Moatless Tools）、Graph Engineering（状态图 + 分工 + 交接 + 校验 + 回退）、子智能体委托（OpenHands V1）。
- **核心收益**：降低 agent 漂移，提升可观测性与可恢复性。

### 趋势 2：从静态索引到动态上下文发现

- **2024 年**：预建向量索引（Continue.dev、Cursor）。
- **2025-2026 年**：动态上下文发现（Cursor，文件原语 + agent 按需拉取）、MCP 工具按需加载（token 降 46.9%）、Condenser 上下文压缩（OpenHands）。
- **核心收益**：token 效率大幅提升，长 horizon 任务不超窗口。

### 趋势 3：从单次 RAG 到迭代检索-生成 + 验证链

- **2024 年**：单次 RAG（检索一次，生成一次）。
- **2025-2026 年**：迭代检索-生成（RepoCoder/Iter-RETGEN）、CoVe 验证链、分层上下文搜索（AutoCodeRover）、SBFL 频谱定位。
- **核心收益**：召回率与准确率双提升，幻觉率下降。

### 趋势 4：从轻量 Repo Map 到预构建知识图谱

- **2024 年**：Aider 轻量 Repo Map（tree-sitter + PageRank）。
- **2025-2026 年**：CodeGraph 预构建知识图谱（多 agent 共享）、GraphRAG（图检索增强）、演进感知评测（RepoBench/CoreCodeBench）。
- **核心收益**：多 agent 共享同一份代码认知，避免重复扫描。

### 趋势 5：从预设工具到 CodeAct 代码即行动

- **2024 年**：预设工具 API（SWE-agent ACI、Cline 文件工具）。
- **2025-2026 年**：CodeAct（OpenHands，LLM 生成 Python 代码统一所有行动）、MCP 标准化（工具描述/技能/资源统一为文件原语）。
- **核心收益**：行动空间统一化，工具调用更灵活，生态可扩展。

### 趋势 6：从符号白名单到多层级防幻觉

- **2024 年**：符号白名单（Aider）、签名直填、引用校验。
- **2025-2026 年**：符号白名单 + CoVe 验证链 + SBFL 交叉引用 + Condenser 保留关键事实 + Checkpoints 可回滚。
- **核心收益**：多层闸门，幻觉率阶梯式下降。

---

## 十七、结论与优先级建议

| 维度 | 最佳借鉴对象 | docbot 当前状态 | 建议优先级 |
|------|------------|---------------|----------|
| 索引构建 | Aider（PageRank）+ Continue.dev（四层混合）+ CodeGraph（预构建图谱） | ✅ 已有 tree-sitter + 三路检索；❌ 缺 PageRank、缺预构建图谱 | P1: 加 PageRank |
| 上下文选择 | RepoCoder（迭代）+ Continue.dev（混合检索）+ AutoCodeRover（分层搜索） | ✅ 已有三路混合；❌ 缺迭代收敛、缺分层搜索 | P1: 加迭代检索-生成 |
| 上下文压缩 | OpenHands（Condenser） | ❌ 无 | P2: 加 Condenser |
| 防幻觉 | Aider（符号白名单）+ SWE-agent（lint）+ CoVe（验证链）+ AutoCodeRover（SBFL） | ✅ 已有符号白名单 + 签名直填 + 引用校验；❌ 缺 lint、缺 CoVe、缺 SBFL | P2: 加 lint + CoVe |
| 多视角积累 | STORM/Co-STORM | ✅ 已有 multi_perspective_learner | P3: 深化视角挖掘 |
| 长文档维护 | Co-STORM（mind map）+ Cursor（文件原语）+ OpenHands（Condenser） | ❌ 无 mind map、无 Condenser | P2: 加 Condenser |
| FSM 约束 | Moatless Tools（FSM） | ⚠️ LangGraph 线性流程 | P3: 改 FSM |
| MCP 生态 | Cline（MCP 全面拥抱）+ Cursor（按需加载） | ⚠️ 仅 2 个 MCP 工具 | P3: 扩展 MCP 工具 |
| 代码即行动 | OpenHands（CodeAct） | ❌ 无 | P4: 探索性 |
| 知识图谱共享 | CodeGraph（2026） | ⚠️ 内存图谱，未持久化 | P4: 探索性 |

### 核心建议

按性价比与防幻觉效果排序，docbot 应优先实现：

1. **P1 - PageRank 符号排序**（借鉴 Aider）：性价比最高，改 `code_graph.py` 加 `pagerank_symbols()`，让 repo_map 优先展示高中心性符号。
2. **P1 - 迭代检索-生成**（借鉴 RepoCoder）：改 content_filler 节点，生成草稿 → 反查仓库 → 补全 → 再生成，多轮收敛。
3. **P2 - Condenser 上下文压缩**（借鉴 OpenHands）：改 `token_budget.py`，长文档生成时用 LLM 压缩已写章节。
4. **P2 - edit 后 lint + CoVe 验证链**（借鉴 SWE-agent + CodeRAG）：改 final_reviewer 节点，代码示例 lint + 事实声明验证。
5. **P3 - FSM 状态机 + MCP 工具扩展**（借鉴 Moatless + Cline）：LangGraph 改 FSM，扩展 `search_method`/`find_class`/`get_callers` 等 MCP 工具。

**核心结论**：docbot 在防幻觉基础设施（符号白名单 + 签名直填 + 引用校验 + 三路检索）上已达到业界 2024 年水平，但相比 2025-2026 年标杆（OpenHands Condenser / Moatless FSM / AutoCodeRover SBFL / RepoCoder 迭代）仍有 4 项关键差距。建议按 P1→P2→P3 顺序补齐，其中 **PageRank + 迭代检索-生成** 是性价比最高、应最先实现的两项。

---

## 参考资料

### 项目官方文档与论文
- Aider Repo Map：https://aider.chat/docs/repomap.html
- SWE-agent 论文：https://arxiv.org/abs/2405.15793
- STORM 论文：https://arxiv.org/abs/2402.14207
- Co-STORM 论文：https://arxiv.org/abs/2408.15232
- RepoCoder 论文：https://arxiv.org/abs/2303.12570
- CodeAct 论文：https://arxiv.org/abs/2402.01030
- AutoCodeRover 论文：https://arxiv.org/abs/2404.05427
- SWE-SEARCH 论文：https://arxiv.org/abs/2502.11458
- RepoBench 论文：https://arxiv.org/abs/2306.03081
- CoreCodeBench 论文：https://arxiv.org/abs/2507.05281
- Iterative Grounding：https://arxiv.org/abs/2401.01701
- RAG Survey：https://arxiv.org/abs/2312.10997

### 项目 GitHub
- Aider：https://github.com/Aider-AI/aider
- SWE-agent：https://github.com/princeton-nlp/SWE-agent
- STORM：https://github.com/stanford-oval/storm
- Continue.dev：https://github.com/continuedev/continue
- OpenHands：https://github.com/All-Hands-AI/OpenHands
- Moatless Tools：https://github.com/aorwall/moatless-tools
- Cline：https://github.com/cline/cline
- Roo Code：https://github.com/RooVetGit/Roo-Code

### 技术博客与分析
- Cursor Dynamic Context Discovery：https://cursor.com/blog/dynamic-context-discovery
- 拆解 OpenHands 系列：https://www.cnblogs.com/rossiXYZ/p/19620422
- AutoCodeRover 论文笔记：https://www.cnblogs.com/mianmaner/p/19030399
- Cline 技术分析：https://juejin.cn/post/7495365665844133928
- Continue 索引构建分析：https://juejin.cn/post/7517183666688294950
- 代码库知识图谱工具测评：https://m.toutiao.com/group/7644783443611501097/
- Moatless Tools 教程：https://blog.csdn.net/gitblog_00770/article/details/142196978

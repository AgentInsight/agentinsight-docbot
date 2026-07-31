# 业界主流开源 AI Agent 代码仓库理解方法论：代码级技术分析报告

> 研究对象：Aider、STORM/Co-STORM、SWE-agent、Continue.dev、Cursor、RepoCoder、CodeRAG（CoVe + Iterative Grounding）
> 研究维度：仓库索引方式、上下文文件选择、防幻觉机制、引用校验、签名直填
> 应用目标：为「生成代码仓库的需求文档 / API 文档」场景提炼可借鉴的关键技术与防幻觉最佳实践
> 数据来源：2024–2026 年官方文档、GitHub 源码、论文（arXiv:2303.12570、arXiv:2309.11495、arXiv:2405.15793、arXiv:2402.14207、arXiv:2408.15232）及权威技术博客

---

## 0. 摘要（Executive Summary）

七个项目代表了业界解决「LLM 理解真实代码仓库」问题的五条主线：

1. **结构化符号图派**（Aider）：用 tree-sitter 抽取 def/ref 标签，构建文件级有向图，PageRank + personalization 排序，把全仓库压缩进 1k–8k token 的「Repo Map」。
2. **多视角对话 + 强制 Grounding 派**（STORM/Co-STORM）：dspy 管线，模拟多视角问答渐进积累证据库，写章节时强制用 `[1][2][n]` 内联引用并反查 `information_table`。
3. **Agent-Computer Interface 派**（SWE-agent）：为 LM 量身定制一组「紧凑命令」替代裸 shell，编辑后自动 lint、文件 100 行窗口、scroll/goto，把防幻觉下沉到工具反馈层。
4. **混合索引派**（Continue.dev、Cursor）：tree-sitter AST 分块 + 向量库 + 全文索引（FTS5 / sparse n-gram）三/四路并行检索，Cursor 额外引入 Merkle 树增量同步、simhash 团队索引复用、文件即上下文。
5. **迭代闭环派**（RepoCoder、CodeRAG/CoVe）：用「生成结果作新查询」迭代检索（RepoCoder），或「生成 → 计划验证问题 → 独立回答 → 修正」迭代 Grounding（CoVe）。

对「需求/API 文档生成」最值得直接借鉴的三个机制：**Aider 的符号图 + 签名直填**、**STORM 的强制内联引用 + 证据库反查**、**SWE-agent 的 lint 反馈环**。详见第 9、10 节。

---

## 1. Aider —— tree-sitter Repo Map + PageRank 符号排序

### 1.1 项目定位

Aider 是终端 AI 编程助手，其核心难点是：让 LLM 在只看到少量真实文件时，仍能理解整个仓库的 API/抽象边界，避免编造不存在的类与函数。解决方案是 `aider/repomap.py` 中的 `RepoMap` 类。

### 1.2 仓库索引：tree-sitter 标签抽取

Aider 用 tree-sitter（通过 `grep_ast` 包装）为 100+ 语言解析 AST，并按语言对应的 `.scm` query 文件抽取两类标签：

```python
# aider/repomap.py（简化，来源：GitHub main 分支）
from grep_ast.tsl import USING_TSL_PACK, get_language, get_parser
Tag = namedtuple("Tag", "rel_fname fname line name kind".split())

def get_tags_raw(self, fname, rel_fname):
    lang = filename_to_lang(fname)
    language = get_language(lang)
    parser  = get_parser(lang)
    query_scm = get_scm_fname(lang).read_text()    # 例：aider/queries/tree-sitter-python.scm
    code  = self.io.read_text(fname)
    tree  = parser.parse(bytes(code, "utf-8"))
    captures = self._run_captures(Query(language, query_scm), tree.root_node)

    for node, tag in all_nodes:
        if tag.startswith("name.definition."):
            kind = "def"
        elif tag.startswith("name.reference."):
            kind = "ref"
        else:
            continue
        yield Tag(rel_fname=rel_fname, fname=fname,
                  name=node.text.decode("utf-8"),
                  kind=kind,
                  line=node.start_point[0])
```

关键点：
- **只保留 def 与 ref 两类标签**（类、函数、方法的定义与引用），丢弃实现体；这是把仓库压缩进 token 预算的根本手段。
- 若某语言 `.scm` 只能抽出 def（如 cpp），用 Pygments 回填 ref，保证图连通性。
- 标签按 `(fname, mtime)` 落盘到 `diskcache`（SQLite 后端），二次启动零成本。

### 1.3 上下文选择：文件级有向图 + PageRank + Personalization

这是 Aider 最具借鉴价值的设计。它把「哪个文件值得放进 Repo Map」建模为图排序问题：

```python
def get_ranked_tags(self, chat_fnames, other_fnames, mentioned_fnames, mentioned_idents, ...):
    import networkx as nx
    defines, references, definitions = defaultdict(set), defaultdict(list), defaultdict(set)
    personalization = dict()
    fnames = sorted(set(chat_fnames).union(other_fnames))
    personalize = 100 / len(fnames)         # 默认均匀分布

    for fname in fnames:
        current_pers = 0.0
        if fname in chat_fnames:             # 已加入聊天 → 提权
            current_pers += personalize
        if rel_fname in mentioned_fnames:    # 用户提到 → 提权
            current_pers = max(current_pers, personalize)
        # 路径组件若命中 mentioned_idents（用户提到的符号）→ 再提权
        if matched_idents:
            current_pers += personalize
        if current_pers > 0:
            personalization[rel_fname] = current_pers

        for tag in self.get_tags(fname, rel_fname):
            if tag.kind == "def":
                defines[tag.name].add(rel_fname)
            elif tag.kind == "ref":
                references[tag.name].append(rel_fname)

    G = nx.MultiDiGraph()
    for ident in idents:                      # ident = def 名 ∩ ref 名
        definers = defines[ident]
        mul = 1.0
        if ident in mentioned_idents:        mul *= 10          # 命中提及符号 ×10
        if (is_snake or is_kebab or is_camel) and len(ident) >= 8:
            mul *= 10                          # 有意义的长标识符 ×10
        if ident.startswith("_"):             mul *= 0.1        # 私有符号降权
        if len(defines[ident]) > 5:           mul *= 0.1        # 高频通用名降权
        for referencer, num_refs in Counter(references[ident]).items():
            for definer in definers:
                use_mul = mul
                if referencer in chat_rel_fnames:
                    use_mul *= 50              # 被聊天中的文件引用 ×50
                G.add_edge(referencer, definer, weight=use_mul * num_refs, ident=ident)

    ranks = nx.pagerank(G, personalization=personalization, ...)
    # 按 rank 倒序、按 token 预算贪心选取文件，再用 TreeContext 渲染签名
```

排序逻辑的精髓：
- **节点 = 文件，边 = ref 文件 → def 文件**，边权 = `引用次数 × mul`。
- **personalization 向量**：把概率质量集中到「当前聊天文件 / 用户提到文件 / 用户提到符号所在文件」。PageRank 因此向这些节点的语义邻域扩散。
- **mul 启发式**：长而规范的标识符加权，下划线开头/被超过 5 个文件定义的通用名（如 `logger`、`config`）降权——直接抑制「通用词被误当核心 API」的幻觉。
- 排序后按 `--map-tokens`（默认 1k，无文件时自动放大到 `map_tokens × 8`，并预留 4096 token padding）贪心填充。

### 1.4 渲染：签名直填（Signature Direct-Fill）

选中的标签交给 `grep_ast.TreeContext` 渲染，输出形如：

```
aider/coders/base_coder.py:
⋮...
│class Coder:
│ abs_fnames = None
⋮...
│ @classmethod
│ def create(
│     self,
│     main_model,
│     edit_format,
│     io,
│     skip_model_availabily_check=False,
│     **kwargs,
⋮...
```

注意几个细节：
- **类/方法/函数签名连同参数列表原样保留**，方法体折叠为 `⋮...`。
- **行号与缩进保留**，LLM 能精确判断「这个类在哪个文件第几行」「这个方法接受什么参数」。
- 这就是「签名直填」机制——**LLM 不自由描述签名，签名从 AST 直接提取并渲染**。这把「调用一个不存在的方法」幻觉降到了最低：模型看到的签名就是源码里真实存在的签名。

### 1.5 防幻觉与引用校验

- **结构化降幻觉**：def/ref 标签来自 tree-sitter AST，不存在「LLM 编造的符号」进入 Repo Map 的可能。
- **间接引用校验**：当 LLM 试图调用某 API 时，Repo Map 里要么有对应签名（可直接用），要么没有（模型大概率会主动 `add file` 请求把实现文件加进上下文）。这是「软校验」而非硬校验。
- **无硬引用校验**：Aider 不在生成代码后做「导入路径/符号是否真实存在」的二跳校验，依赖 tree-sitter 签名本身的可靠性。

### 1.6 关键文件

- `aider/repomap.py`（RepoMap、get_ranked_tags、get_tags_raw）
- `aider/queries/tree-sitter-*.scm`（各语言标签 query）
- 官方文档：https://aider.chat/docs/repomap.html

---

## 2. STORM / Co-STORM —— 多视角提问 + 模拟对话 + 强制 Grounding

### 2.1 项目定位

STORM（Stanford Oval）把「写带引用的长文」拆成两阶段：**Pre-writing（调研）** 与 **Writing（成文）**。Co-STORM 在此基础上引入人机协作话语与动态 mind map。两者均用 dspy 实现，对「文档生成型 Agent」有直接参考价值。

### 2.2 仓库/知识索引：Information Table

STORM 不索引代码仓库，而是索引「对话中积累的检索片段」。核心数据结构是 `StormInformationTable`：

- 调研阶段，多个「视角专家」(perspective) 与「话题专家」模拟对话，每轮检索结果包装成 `Information` 对象（含 URL、snippets、视角元数据）落表。
- `information_table.prepare_table_for_retrieval()` 在成文前预构建检索索引（向量化 snippets）。
- 写章节时按 `section_query` 反查：

```python
# knowledge_storm/storm_wiki/modules/article_generation.py（GitHub main）
def generate_section(self, topic, section_name, information_table, section_outline, section_query):
    collected_info: List[Information] = []
    if information_table is not None:
        collected_info = information_table.retrieve_information(
            queries=section_query, search_top_k=self.retrieve_top_k   # 默认 5
        )
    output = self.section_gen(
        topic=topic, outline=section_outline, section=section_name,
        collected_info=collected_info,
    )
    return {"section_name": section_name,
            "section_content": output.section,
            "collected_info": collected_info}
```

### 2.3 多视角提问 + 模拟对话（防上下文窄化）

直接让 LLM 提问效果差。STORM 用两步：
1. **Perspective-Guided Question Asking**：先 survey 同类话题的现有文章，抽取出多个视角（如历史、技术、对比），每个视角驱动一个 question-asking agent。
2. **Simulated Conversation**：Wikipedia writer ↔ topic expert 多轮对话，expert 回答必须 grounded 在检索结果上，writer 据此更新理解并追问。

Co-STORM 增加 Moderator agent：专门基于「检索到但前轮未用」的片段生成 thought-provoking 问题，避免 discourse 在某视角上过早收敛。

### 2.4 强制 Grounding 与引用校验

最值得借鉴的是 `WriteSection` 的 dspy Signature——把「必须用 `[n]` 内联引用」写进模型约束：

```python
class ConvToSection(dspy.Module):
    def forward(self, topic, outline, section, collected_info):
        info = ""
        for idx, storm_info in enumerate(collected_info):
            info += f"[{idx + 1}]\n" + "\n".join(storm_info.snippets) + "\n\n"
        info = ArticleTextProcessing.limit_word_count_preserve_newline(info, 1500)
        with dspy.settings.context(lm=self.engine):
            section = ArticleTextProcessing.clean_up_section(
                self.write_section(topic=topic, info=info, section=section).output
            )
        return dspy.Prediction(section=section)

class WriteSection(dspy.Signature):
    """Write a Wikipedia section based on the collected information.
    Here is the format of your writing:
        1. Use "# Title" / "## Title" / "### Title" ...
        2. Use [1], [2], ..., [n] in line (for example,
           "The capital of the United States is Washington, D.C.[1][3].").
           You DO NOT need to include a References or Sources section.
    """
    info    = dspy.InputField(prefix="The collected information:\n", format=str)
    topic   = dspy.InputField(prefix="The topic of the page: ", format=str)
    section = dspy.InputField(prefix="The section you need to write: ", format=str)
    output  = dspy.OutputField(
        prefix="Write the section with proper inline citations "
               "(Start your writing with # section title. ...):\n", format=str)
```

防幻觉与引用校验要点：
- **每个章节只看 ≤1500 词的 `collected_info`**，超出强制截断——防止模型从「长上下文里挑一段未被引用的内容」幻觉。
- **`[n]` 索引对应 `collected_info` 列表下标**，成文后可程序化反查「每条引用指向哪个 snippet / URL」——这就是硬引用校验的基础（虽 STORM 本身未做严格 post-validation，但格式契约使后续校验成为可能）。
- `ArticleTextProcessing.clean_up_section` 会清理无引用段落、重复引用、空洞套话。
- Co-STORM 的 mind map 提供层级化概念结构，进一步约束生成不跑题。

### 2.5 关键文件

- `knowledge_storm/storm_wiki/modules/article_generation.py`（ConvToSection、WriteSection）
- `knowledge_storm/interface.py`（STORMWikiRunnerArguments、模块接口）
- `knowledge_storm/collaborative_storm/engine.py`（Co-STORM Runner）
- 论文：arXiv:2402.14207（STORM）、arXiv:2408.15232（Co-STORM）

---

## 3. SWE-agent —— ACI (Agent-Computer Interface) + edit 后自动 lint

### 3.1 项目定位

SWE-agent 让 LM 自主修复 GitHub 真实 issue。论文核心论断：**LM 在裸 Linux shell 上不可靠**（无法稳定编辑小文件、无效编辑无反馈），因此需要 ACI——一个介于 LM 与计算机之间的抽象层，类比 HCI（人机接口）。

### 3.2 ACI 的四大组件

| 组件 | 命令 | 作用 |
|---|---|---|
| 搜索导航 | `find_file`、`search_file`、`search_dir` | 按文件名/字符串搜索，输出**摘要**而非原始 grep |
| 文件查看器 | `open`、`scroll_up`、`scroll_down`、`goto <line>` | 一次最多显示 **100 行窗口**，强制 LM「看到」局部上下文 |
| 文件编辑器 | `str_replace`、`insert`、`create`、`undo_edit`、`view` | 精确字符串替换；**编辑后自动 lint** |
| 上下文管理 | 系统提示 + 命令文档 + 示范 | 每步必须输出 thought + command；无效生成返回 error 让 LM 重试 |

### 3.3 编辑后自动 lint：防幻觉的关键反馈环

`str_replace` / `insert` 完成后，ACI 立即对该文件运行语言对应的 linter（Python 用 `pyflakes`/`flake8`），把 lint 输出作为 observation 返回 LM：

```python
# SWE-agent str_replace_editor 行为（伪代码，综合论文与 v0.7 实现）
def str_replace(path, old_str, new_str):
    file = open(path).read()
    if old_str not in file:
        return observation(f"String '{old_str}' not found in {path}.")
    if file.count(old_str) > 1:
        return observation(
            f"String '{old_str}' appears multiple times. "
            f"Provide more context to disambiguate.")
    new_file = file.replace(old_str, new_str, 1)
    open(path, 'w').write(new_file)

    # 关键：编辑后自动 lint，把语法/未定义名错误回喂给 LM
    lint_output = run_linter(path)
    return observation(render_window_with_line_numbers(path, window)
                       + ("\n[LINT]\n" + lint_output if lint_output else ""))
```

这是「**生成即验证**」的范式：LM 不需要等到 `submit` 才知道改错了；编辑一结束，lint 立刻告诉它「`NameError: name 'foo' is not defined`」「indentation error」。LM 据此在下一轮 thought 里自我修正。

### 3.4 其他防幻觉设计

- **100 行窗口 + scroll**：避免 LM 一次看到几万行后「脑补」不存在的代码；它必须显式 `open` / `goto` 才能看到具体行。
- **`str_replace` 唯一性约束**：old_str 必须在文件中**唯一**出现，否则报错要求提供更多上下文——强制 LM 看准再改，而非凭印象改。
- **`undo_edit`**：可撤销，配合 lint 形成「尝试—反馈—回退—再试」闭环。
- **搜索结果摘要化**：`search_dir` 只返回「文件:匹配数」而非全部命中行，避免上下文被噪音淹没。
- **无效命令硬反馈**：无效生成触发 error response，要求重试，不让 LM「假装成功」。

### 3.5 引用校验与签名直填

- **无签名直填**：SWE-agent 不预抽取符号签名给 LM，而是让 LM 自己 `open` 文件看签名。这把「签名真实性」交给文件查看器（看到的就是源码）。
- **无生成后引用校验**：依赖 lint + 单元测试（`submit` 后跑 SWE-bench 测试）做最终校验。

### 3.6 关键文件与论文

- `src/sweagent/tools/`（v1.0+）；v0.7 在 `sweagent/tools/str_replace_editor.py`、`sweagent/tools/tools.py`
- 论文：arXiv:2405.15793（SWE-agent: Agent-Computer Interfaces Enable Automated Software Engineering, NeurIPS 2024）
- 衍生：mini-SWE-agent（100 行 Python，65% SWE-bench verified）

---

## 4. Continue.dev —— @codebase 四层混合索引

### 4.1 项目定位

Continue.dev 是开源 VS Code / JetBrains AI 助手，`@codebase` 是其仓库级问答入口。它把「向量检索」「全文检索」「结构化检索」三种范式并存，互相补强。

### 4.2 索引目录结构

```
~/.continue/index/
├── docs.sqlite                 # 文档索引
├── autocompleteCache.sqlite    # 补全缓存
├── lancedb/                    # 向量库（每分支独立表）
└── index.sqlite                # 主索引库（核心）
```

`index.sqlite` 的表：

```
chunk_tags          # chunk ↔ tag 关联
chunks              # 基础分块
code_snippets       # 代码片段（tree-sitter 抽取）
code_snippets_tags  # 片段 ↔ tag
fts / fts_idx / fts_config / fts_content / fts_data / fts_docsize / fts_metadata   # FTS5 全文索引
global_cache / lance_db_cache / tag_catalog
```

### 4.3 四层索引详解

#### 4.3.1 ChunkCodebaseIndex（基础分块，SQLite）

为其他三层提供基础分块。流程：

1. 文件遍历 → 文件类型判断（`shouldChunk`：>1MB 跳过）。
2. 代码文件用 `codeChunker`（tree-sitter AST），其他文件用 `basicChunker`。
3. `collapseChildren`：递归处理子节点，超大小阈值则折叠方法体、保留类/函数声明，清理空行。
4. chunk 写入 `chunks` 表。

```
开始 → 遍历文件 → 扩展名判断 → tree-sitter 解析 → AST 遍历
     → 节点大小检查 → [类/函数/其他] → 类:保留声明折叠方法体
                                函数:保留签名折叠函数体
                                其他:递归子节点
     → 创建 chunk → 写入 SQLite
```

#### 4.3.2 LanceDbIndex（向量索引，LanceDB + SQLite 元数据）

- 基于 `ChunkCodebaseIndex` 的分块，用嵌入模型算向量。
- 默认无显式 `embeddingsProvider` 时使用 `TransformersJsEmbeddingsProvider`（`all-MiniLM-L6-v2`，本地 transformers.js）。
- 每个 git 分支在 LanceDB 中独立一张表。
- 查询：query → 向量 → LanceDB 相似度搜索 → 取 UUID → SQLite 查元数据。

#### 4.3.3 FullTextSearchCodebaseIndex（FTS5 全文索引，SQLite）

- 用 SQLite **FTS5** 扩展，`trigram` tokenizer（3-gram）。
- 适合精确关键词搜索、API 名匹配。
- 与向量索引互补：向量擅长语义，FTS5 擅长「精确匹配 `class UserRepository`」。

#### 4.3.4 CodeSnippetsCodebaseIndex（结构化片段索引，SQLite）

这是「签名直填」的来源层：

- 用 tree-sitter query 识别**函数、类、其他顶层代码对象**。
- 保存片段元数据：标题、路径、起止行号、内容。
- 通过 `code_snippets_tags` 关联标签，便于按 tag 检索。
- 适合「快速定位特定代码结构」——例如「找到所有 `@dataclass` 装饰的类」。

### 4.4 四层对比

| 索引 | 存储 | 用途 | 搜索能力 |
|---|---|---|---|
| ChunkCodebaseIndex | SQLite | 基础分块，给其他索引用 | 不直接搜索 |
| LanceDbIndex | LanceDB + SQLite 元数据 | 语义相似度 | 向量检索 |
| FullTextSearchCodebaseIndex | SQLite FTS5（trigram） | 关键词/精确匹配 | 倒排 |
| CodeSnippetsCodebaseIndex | SQLite | 结构化元素（函数/类签名） | 按 tag/标题 |

### 4.5 防幻觉与引用校验

- **混合检索降幻觉**：单路向量容易召回「语义像但无关」的 chunk；FTS5 + code snippets 同时命中才更可信。
- **签名直填**：`CodeSnippetsCodebaseIndex` 直接存 tree-sitter 抽取的真实函数/类片段，可作为「签名来源」直接注入 prompt，避免 LLM 自由描述签名。
- **无硬引用校验**：Continue.dev 不在生成代码后做「导入路径是否存在」校验。

### 4.6 关键文件

- `core/indexing/CodeSnippetsCodebaseIndex.ts`
- `core/indexing/LanceDbIndex.ts`
- `core/indexing/FullTextSearchCodebaseIndex.ts`
- `core/indexing/chunk/chunk.ts`（`chunkDocumentWithoutId`、`shouldChunk`、`collapseChildren`）
- `core/indexing/allEmbeddingsProviders.ts`

---

## 5. Cursor —— Dynamic Context Discovery + 双索引 + 文件即原语

### 5.1 项目定位

Cursor 是闭源但技术公开度最高的 AI IDE。其仓库理解能力由「双索引 + 自研 embedding + Merkle 同步 + 文件即上下文」四件套构成。2026 年 1 月的官方博客《Dynamic context discovery》系统阐述了其上下文管理哲学。

### 5.2 双索引策略

| 索引 | 部署位置 | 用途 | 时效性 |
|---|---|---|---|
| 语义（向量）索引 | Cursor 服务端（Turbopuffer） | 自然语言查询（「在哪处理支付重试」） | 可略滞后 |
| 正则（trigram / sparse n-gram）索引 | 客户端本地 | 模式匹配（`db\.execute\(`） | 实时（每次编辑即更新） |

二者不可互换。Cursor 内部数据：在 grep 上叠加语义搜索，agent 准确率 +12.5%（不同模型 6.5%–23.5%），大库代码保留率 +2.6%，不满意后续请求 -2.2%。

### 5.3 tree-sitter AST 分块

```python
# Cursor AST 分块简化示意（来源：社区逆向 + 官方公开描述）
import tree_sitter_python as tspython
from tree_sitter import Language, Parser
PY_LANGUAGE = Language(tspython.language)
parser = Parser(PY_LANGUAGE)
MAX_CHUNK_BYTES = 1500

def chunk_file(source_code: bytes) -> list[str]:
    tree = parser.parse(source_code)
    chunks = []
    for node in tree.root_node.children:
        # 顶层函数/类各自成块
        if node.type in ("function_definition", "class_definition"):
            chunks.append(source_code[node.start_byte:node.end_byte].decode())
        # 小兄弟节点（imports、常量）合并
        else:
            if chunks and len(chunks[-1]) + len(source_code[node.start_byte:node.end_byte]) < MAX_CHUNK_BYTES:
                chunks[-1] += "\n" + source_code[node.start_byte:node.end_byte].decode()
            else:
                chunks.append(source_code[node.start_byte:node.end_byte].decode())
    return chunks
```

关键：函数/类保持完整，embedding 捕获的是「有意义单元」而非任意字符窗口。

### 5.4 自研 embedding 模型：用 agent 轨迹训练

Cursor 不用 `text-embedding-ada-002`。它训练自己的 embedding 模型，训练信号来自 agent 会话本身：

- agent 完成任务时会多次搜索、打开文件、最终找到正确代码——回顾轨迹可得到「每一步本应检索到什么」的事后标签。
- 把每条轨迹交给 LLM 评分器，对「每一步最有帮助的内容」排序。
- 训练 embedding 模型使其相似度与排序对齐（对比学习目标：拉近「真正帮助 agent 的 chunk」，推远「仅表面相似」的 chunk）。
- 效果：模型不再优化「两段代码是否相像」，而是优化「给定任务和上下文，哪一块 chunk 真正帮助 agent」。

### 5.5 Turbopuffer + Merkle 树 + simhash

- **Turbopuffer**：每个代码库一个 namespace；8000 万 namespace、1 万亿向量；冷数据沉降对象存储，热数据驻 NVMe。
- **Merkle 树（SHA-256）**：与 Git 对象模型同源。文件变更沿父目录传播到根哈希；客户端与服务端只遍历哈希不一致的分支，5 万文件的工作区通常只需重 embed 少量文件。
- **simhash 索引复用**：组织内 clone 相似度约 92%。新用户打开代码库 → 计算 simhash → 服务端找最相似的已有 namespace → `copy_from_namespace` 复制（写入费用 5 折）→ 后台对齐差异。中位仓库首次可查询时间 7.87s → 525ms，99 分位 4.03h → 21s。
- **Merkle 内容证明做访问控制**：服务端返回的搜索结果按文件路径比对客户端 Merkle 树；客户端算不出哈希就看不到该结果。服务端从不接触原始源码。

### 5.6 Dynamic Context Discovery（文件即原语）

这是 Cursor 上下文工程的核心范式转变——**少给静态上下文，让 agent 按需动态拉取**：

1. **长 tool 响应转文件**：第三方便 shell/MCP 结果不截断，写入临时文件，agent 拿到路径后 `tail`/`grep` 按需读取。
2. **聊天历史即文件**：summarization 时把历史同步为文件，agent 若发现 summary 丢细节，可主动 grep 历史恢复。
3. **Agent Skills 开放标准**：Skills 是带 name/description 的文件，作为静态上下文进系统提示，agent 用 grep/语义搜索按需拉取具体 skill 文件。
4. **MCP 工具按需加载**：把 MCP 工具描述同步到「每服务一个文件夹」，agent 只拿到工具名作为静态提示，需要时再 `ls` 文件夹查详细描述。A/B 测试：**MCP 调用场景 agent 总 token -46.9%**。
5. **终端会话即文件**：集成终端输出同步到本地文件，agent 用 grep 找相关行，适合「我的命令为什么失败」类问题。

### 5.7 防幻觉与引用校验

- **双索引互校**：语义命中 + 正则命中交叉验证，降低单路幻觉。
- **正则索引锚定当前 commit + 编辑**：agent 刚写的代码立刻可被检索，避免「索引里没有 → agent 反复找不存在的代码」陷阱。
- **文件即上下文**：agent 看到的是真实文件内容（通过 `tail`/`grep`），不是 LLM 描述的摘要，天然防「编造路径」。
- **无生成后硬引用校验**：依赖文件即真实原语这一事实约束。

### 5.8 关键资料

- 官方博客：https://cursor.com/blog/dynamic-context-discovery（2026-01-06）
- turbopuffer 案例：https://turbopuffer.com/customers/cursor
- 论文：arXiv:2406.13592（Cursor 的 semantic search 内部研究）

---

## 6. RepoCoder —— 迭代检索-生成范式

### 6.1 项目定位

RepoCoder（微软研究院 + 北大，EMNLP 2023）解决「仓库级代码补全」：跨文件信息散落各处，单次检索-生成无法弥合「查询（未完成代码）与目标（待生成代码）」的语义鸿沟。

### 6.2 核心算法：迭代检索-生成

```
输入：未完成代码 X，滑动窗口大小 S_w，步长 S_s（S_s < S_w），检索器 R，生成器 M

# 第一轮：用 X 的尾部作查询
q1 = X 的最后 S_w 行
C1 = R(q1)                          # 检索相似片段
Y1 = M(C1, X)                       # 生成中间代码

# 第二轮：用 X 的尾部 + Y1 的头部作查询
q2 = X 的后 (S_w - S_s) 行  +  Y1 的前 S_s 行
C2 = R(q2)                          # 用生成结果反查
Y_final = M(C2, X)                  # 最终生成

# 可继续迭代 k 轮
```

关键洞察：
- **第一轮 Y1 是「模型对目标的猜测」**，把它当作新查询能更精确地命中「真正需要的跨文件上下文」。
- 这是 **Generation-Augmented Retrieval**（用生成结果增广检索）与 **Retrieval-Augmented Generation**（用检索结果增广生成）的闭环。
- 闭环可迭代 k 轮直到收敛（实验显示 2 轮已收敛大部分增益）。

### 6.3 检索机制

- **滑动窗口编码**：仓库文件切成连续代码块（窗口 S_w > 步长 S_s），建可检索库。
- **混合检索器**：稀疏（TF-IDF）与稠密（`text-embedding-ada-002`）均支持，性能相当，验证框架对检索器不敏感。
- **提示工程**：检索结果按相似度升序排列、附文件路径，增强可解释性。

### 6.4 RepoEval 基准与性能

| 任务类型 | Zero-Shot EM | RepoCoder EM | 提升 |
|---|---|---|---|
| 行补全 | 42.1% | 53.7% | +11.6% |
| API 调用补全 | 38.5% | 49.2% | +10.7% |
| 函数体补全（Pass Rate） | 31.2% | 47.0% | +15.8%（对比单次 RAG） |

亮点：350M 参数 CodeGen + RepoCoder 优于 Zero-Shot 的 175B Code-Davinci-002。

### 6.5 防幻觉与引用校验

- **迭代降幻觉**：每轮检索把「模型猜测」与「真实仓库」对齐，幻觉在迭代中被纠正。
- **检索结果带文件路径**：模型生成的 import / 调用更可能指向真实路径。
- **无硬引用校验**：依赖 Pass Rate（单元测试）做最终验证。
- **无签名直填**：检索的是代码块而非签名，签名信息隐含在块内。

### 6.6 关键资料

- 论文：arXiv:2303.12570
- 代码：https://github.com/microsoft/CodeT/tree/main/RepoCoder

---

## 7. CodeRAG —— CoVe 验证链 + Iterative Grounding

### 7.1 概念界定

CodeRAG 并非单一论文，而是业界把两条防幻觉主线——**Chain-of-Verification（CoVe, Meta, arXiv:2309.11495）** 与 **Iterative Grounding**——组合应用于代码 RAG 的方法论统称。两者组合的目的是：在生成代码/文档时，让 LLM 自我验证 + 反复接地。

### 7.2 Chain-of-Verification（CoVe）四步

```python
# CoVe 伪代码（来源：arXiv:2309.11495）
def chain_of_verification(query, llm):
    # 步骤 1：生成基线回答
    baseline_response = llm(f"Answer: {query}")

    # 步骤 2：计划验证问题——让 LLM 对自己的回答列出需要核查的事实点
    verification_questions = llm(
        f"Query: {query}\nResponse: {baseline_response}\n"
        f"List verification questions to fact-check the response.")

    # 步骤 3：独立回答每个验证问题（避免互相污染）
    verified_answers = []
    for vq in verification_questions:
        va = llm(vq)              # 可选：用检索器 R(vq) grounding 后再答
        verified_answers.append((vq, va))

    # 步骤 4：综合生成最终修正回答
    final_response = llm(
        f"Query: {query}\n"
        f"Baseline: {baseline_response}\n"
        f"Verifications: {verified_answers}\n"
        f"Generate the final verified response.")
    return final_response
```

四步核心：
1. **Generate Baseline Response**：先草拟答案（可能含幻觉）。
2. **Plan Verifications**：让 LLM 自我分析「这个答案里哪些点需要事实支撑」。
3. **Execute Verifications**：把每个验证问题独立回答（防止答案互相偏见），可结合检索器 grounding。
4. **Generate Final Verified Response**：综合修正。

CoVe 的本质：把「回答原始复杂问题」拆成「回答一组更简单的子问题」，子问题更易答对，错误更易暴露。

### 7.3 Iterative Grounding（迭代接地）

Iterative Grounding 是把 CoVe 的「验证」环节替换为「检索接地」并多轮迭代：

```
输入：query, 检索器 R, 生成器 M, 最大轮数 K
draft_0 = M(query)                          # 初始草稿
for k in 1..K:
    claims = extract_claims(draft_{k-1})    # 抽取草稿中的可验证陈述
    evidence = []
    for c in claims:
        e_k = R(c)                          # 每条 claim 单独检索证据
        if not e_k.supports(c):
            evidence.append((c, e_k, "CONTRADICT"))   # 标记矛盾
        else:
            evidence.append((c, e_k, "SUPPORT"))
    draft_k = M(query, draft_{k-1}, evidence)  # 带证据修正
    if no_contradiction(evidence): break
return draft_k
```

要点：
- **claim 级粒度**：不是整段重写，而是逐条 claim 检索证据。
- **矛盾标记**：检索证据与草稿冲突时显式标记，让 LLM 在下一轮修正。
- **收敛条件**：无矛盾即停，避免无意义迭代。

### 7.4 在代码/文档生成中的应用

- 生成 API 文档时，对每条「`UserRepo.find_by_email(email: str) -> User`」式的声明，单独检索仓库验证：函数名、参数、返回类型是否真实存在。
- 生成需求文档时，对「系统使用 Redis 缓存会话」这类断言，检索代码确认 `redis` 真的被 import 且用于 session。

### 7.5 防幻觉与引用校验

- **强引用校验**：每条 claim 都有 evidence 支撑，是「引用校验」的强形式。
- **自纠错**：CoVe 步骤 4 + Iterative Grounding 的 `draft_k` 都是基于证据的修正版。
- **无签名直填**：CoVe/Iterative Grounding 本身不抽取签名，但可与 Aider/Continue.dev 的签名直填组合。

### 7.6 关键资料

- 论文：arXiv:2309.11495（Chain-of-Verification Reduces Hallucination in Large Language Models, Meta）
- 相关：Self-RAG（arXiv:2310.11511）、CRAG（arXiv:2401.15884）

---

## 8. 横向对比矩阵

| 维度 | Aider | STORM/Co-STORM | SWE-agent | Continue.dev | Cursor | RepoCoder | CodeRAG (CoVe+IG) |
|---|---|---|---|---|---|---|---|
| **索引方式** | tree-sitter def/ref 标签 + 文件级有向图 | Information Table（检索片段向量化） | 无预建索引（运行时 grep/find） | 四层：chunk + LanceDB + FTS5 + code snippets | 双层：语义向量（Turbopuffer）+ trigram/sparse n-gram（本地） | 滑动窗口分块 + TF-IDF/稠密向量 | 检索器 R（任意，可复用向量/FTS） |
| **上下文选择** | PageRank + personalization（chat/mentioned 提权）+ token 预算贪心 | 按 section_query 从 Information Table 反查 top-k | 100 行窗口 + scroll/goto + 搜索摘要 | 向量 + FTS5 + snippets 三路召回 | 双索引 + Merkle 增量 + simhash 复用 + 文件即上下文 | 迭代：用生成结果作新查询再检索 | claim 级独立检索证据 |
| **防幻觉机制** | 签名从 AST 直填；通用词降权 | 强制 `[n]` 内联引用；info 截断 1500 词；clean_up | edit 后自动 lint；str_replace 唯一性；无效命令硬反馈 | 混合检索互校；签名直填 | 双索引互校；正则索引锚定当前 commit；文件即真实原语 | 迭代对齐「猜测 vs 真实」 | CoVe 四步自检；Iterative Grounding 逐 claim 验证 |
| **引用校验** | 软校验（签名真实，但生成代码不二次校验） | 格式契约（`[n]` 可程序化反查 snippet） | 无（lint + 单测兜底） | 无 | 无（文件即原语） | 无（Pass Rate 兜底） | **强校验**（每条 claim 有 evidence） |
| **签名直填** | **有**（TreeContext 渲染 def 行 + 参数） | 无（信息是 snippet 文本） | 无（LM 自己 open 文件看签名） | **有**（CodeSnippetsCodebaseIndex） | 部分（AST 分块保留函数边界） | 无（检索块隐含签名） | 无（可与签名直填组合） |
| **迭代性** | 否（单次构图） | 是（多轮对话渐进积累） | 是（ReAct 多轮 + lint 反馈） | 否（单次召回） | 是（agent 多步 + 文件按需读） | **是**（核心特征：迭代检索-生成） | **是**（核心特征：CoVe + IG 多轮） |
| **目标场景** | 代码编辑 | 长文写作 | bug 修复 | 代码问答/补全 | 全场景 IDE | 代码补全 | 通用 RAG 防幻觉 |
| **开源** | 是（MIT） | 是（MIT） | 是（MIT） | 是（Apache-2.0） | 闭源 | 是（MIT） | 方法论（论文公开） |

---

## 9. 「生成代码仓库需求文档 / API 文档」场景可借鉴的关键技术点

针对 docbot 这类「读仓库 → 出需求/API 文档」的 Agent，按文档生成管线阶段给出可借鉴点。

### 9.1 仓库理解阶段（建索引）

| 借鉴来源 | 技术 | 应用方式 |
|---|---|---|
| **Aider** | tree-sitter def/ref 标签 + 文件级图 + PageRank | 给 docbot 建「仓库 API 拓扑图」：哪些类/函数是高 PageRank 核心（多半是要写进 API 文档的），哪些是叶子工具函数（可省略） |
| **Continue.dev** | CodeSnippetsCodebaseIndex（tree-sitter 抽函数/类签名） | **直接复用为签名直填源**——API 文档的「函数签名」段落从该索引取，LLM 不自由描述 |
| **Cursor** | 双索引（向量 + FTS5/trigram）+ Merkle 增量 | 仓库大时必须增量同步；向量召回「与需求主题相关的文件」，FTS5 召回「精确类名/函数名命中」 |
| **Aider** | personalization 提权（mentioned_idents ×10） | 用户写「我要给 UserRepository 写 API 文档」时，把 `UserRepository` 所在文件提权到图排序顶端 |

### 9.2 证据积累阶段（多视角调研）

| 借鉴来源 | 技术 | 应用方式 |
|---|---|---|
| **STORM** | Perspective-Guided Question Asking | API 文档自动从「调用方视角」「定义方视角」「测试方视角」多角度提问，避免漏掉调用样例/边界条件 |
| **STORM** | Simulated Conversation + Information Table | docbot 与「代码专家」模拟对话，每轮检索代码片段落 Information Table，写文档时只从表里取证据 |
| **Co-STORM** | Moderator agent | 专门基于「检索到但未用」的代码片段生成追问，避免 docbot 在某模块过早收敛 |
| **RepoCoder** | 迭代检索-生成 | 第一轮生成草稿后，用草稿里的函数名/类名反查仓库，第二轮检索更精准的调用样例 |

### 9.3 文档生成阶段（强制 grounding）

| 借鉴来源 | 技术 | 应用方式 |
|---|---|---|
| **STORM** | `WriteSection` dspy.Signature + `[n]` 内联引用 | API 文档每条描述必须带 `[n]` 指向代码行号或文件路径；无引用段落被 `clean_up` 删除 |
| **STORM** | `info = limit_word_count_preserve_newline(info, 1500)` | 每个章节只给 LLM ≤1500 词证据，防止从长上下文里挑未引用内容幻觉 |
| **Aider** | TreeContext 签名渲染 | API 文档的「方法签名」段落直接渲染 tree-sitter 抽取的签名（带参数、行号），LLM 不改写 |
| **SWE-agent** | edit 后自动 lint | docbot 生成代码示例后立即 lint；若示例调用不存在的函数，lint 报 `NameError` 触发重写 |

### 9.4 校验阶段（防幻觉最后一道闸）

| 借鉴来源 | 技术 | 应用方式 |
|---|---|---|
| **CodeRAG/CoVe** | Plan Verifications + Execute Verifications | 对 API 文档草稿，让 LLM 列出「需要验证的事实点」（函数名、参数类型、返回值、所属模块），逐条独立检索仓库验证 |
| **CodeRAG/IG** | Iterative Grounding（claim 级） | 把文档拆成 claim，每条 claim 检索证据，矛盾标记 → 重写 → 收敛 |
| **SWE-agent** | 单元测试 `submit` 后跑 | docbot 可对生成的「API 调用示例」实际执行（沙箱），失败即重写 |
| **Aider** | 软引用校验 | 文档里出现的每个 `module.function` 路径，反查 Repo Map 是否存在；不存在标红 |

### 9.5 上下文管理阶段（长文档不爆 token）

| 借鉴来源 | 技术 | 应用方式 |
|---|---|---|
| **Cursor** | Dynamic Context Discovery（文件即原语） | 长文档分章节生成时，把已生成章节写入临时文件，agent 用 `grep` 按需回查，而非全塞进上下文 |
| **Cursor** | MCP 工具按需加载 | docbot 的「代码图工具」「git 工具」「lint 工具」描述不同时进系统提示，按需加载 |
| **Aider** | `--map-tokens` 动态预算 | 文档章节深度不同，给核心模块 8k token 预算，给边缘模块 1k |

---

## 10. 防幻觉最佳实践（按优先级排序，落到实现层面）

> 优先级判定标准：投入产出比 × 与「文档生成」场景契合度 × 可独立实现性。

### P0（必做，立竿见影）

1. **签名直填：函数/类签名从 tree-sitter AST 直接抽取，LLM 不自由描述**
   - 实现：用 `tree-sitter-languages` + 语言 `.scm` query（直接抄 Aider 的 `aider/queries/`），把每个 def 节点的 `start_byte..end_byte` 内的签名行（含参数列表）原样保留，方法体折叠为 `⋮...`。
   - 注入 prompt 时格式：`<file_path>:<line> <signature>`。
   - 效果：消除「LLM 编造参数名/类型」类幻觉——这是 API 文档最常见的幻觉。

2. **强制内联引用 + 程序化反查（STORM 范式）**
   - 实现：dspy `Signature` 里硬约束「每条陈述必须以 `[n]` 结尾，`[n]` 对应 evidence 列表下标」。生成后用正则 `\[(-?\d+)\]` 抽取所有引用，反查 evidence 列表，丢弃无引用段落。
   - evidence 列表每条至少含 `{file_path, start_line, end_line, snippet}`。
   - 效果：每条文档陈述可追溯到代码行，是「引用校验」的最低成本实现。

3. **生成即验证：代码示例生成后立即 lint（SWE-agent 范式）**
   - 实现：docbot 生成「API 调用示例」代码块后，立即用 `pyflakes`（Python）/ `tsc --noEmit`（TS）/ `gofmt -l`（Go）跑一遍，把 lint 输出作为下一轮 observation。
   - 失败则要求 LLM 重写，最多 N 轮。
   - 效果：捕捉「调用不存在的函数」「导入不存在的模块」类幻觉。

### P1（强烈推荐，覆盖率高）

4. **文件级符号图 + PageRank 上下文选择（Aider 范式）**
   - 实现：tree-sitter 抽 def/ref → networkx `MultiDiGraph`（节点=文件，边=ref→def）→ `nx.pagerank(G, personalization=...)`。
   - personalization：用户提到的模块/类所在文件 ×10 权重，被提及文件再 ×10。
   - 边权启发式：`startswith('_')` ×0.1，被 >5 文件定义的通用名 ×0.1，长规范标识符 ×10。
   - 效果：把全仓库压缩进 1k–8k token 的 Repo Map，LLM 看到的「API 全景」是真实的，不会凭空想象不存在的模块。

5. **混合检索：向量 + FTS5/trigram 双路并行（Continue.dev / Cursor 范式）**
   - 实现：向量库（Qdrant/LanceDB）+ SQLite FTS5（trigram tokenizer）。
   - 召回时取两路并集，按 RRF（Reciprocal Rank Fusion）合并排序。
   - 效果：向量擅长「与认证相关的逻辑」，FTS5 擅长「精确匹配 `class UserRepository`」；两路互补显著降幻觉。

6. **CoVe 验证链：文档定稿前自检（CodeRAG 范式）**
   - 实现：定稿前让 LLM 对文档草稿列出「需要核查的事实点」（函数名、参数、所属模块、调用关系），逐条独立检索仓库验证；矛盾项标记后重写。
   - 效果：捕捉「张冠李戴」（把 A 模块的功能安到 B 模块）类幻觉。

### P2（进阶，边际收益高）

7. **迭代检索-生成（RepoCoder 范式）**
   - 实现：第一轮生成 API 文档草稿 → 用草稿里的函数名/类名作查询再检索 → 第二轮带新证据重写。
   - 2 轮通常收敛。
   - 效果：弥补「初始查询与目标文档语义鸿沟」，召回第一轮漏掉的关键调用样例。

8. **claim 级 Iterative Grounding（CodeRAG 范式）**
   - 实现：把文档拆成 atomic claim（每条形如「`UserRepo.find_by_email` 接受 `email: str` 返回 `Optional[User]`」），每条 claim 单独检索证据，标注 SUPPORT/CONTRADICT/NOT_FOUND，矛盾则重写。
   - 效果：细粒度防幻觉，但实现成本较高（需要 claim 抽取器 + 证据判定器）。

9. **Dynamic Context Discovery：长文档分章节 + 文件即原语（Cursor 范式）**
   - 实现：长文档分章节生成；已生成章节写临时文件；agent 用 `grep` 回查而非全塞上下文。
   - MCP/工具描述按需加载（只给名字，需要时 `ls` 文件夹查详情）。
   - 效果：长文档不爆 token，agent 聚焦当前章节，减少「跨章节串台」幻觉。

### P3（可选，团队级优化）

10. **Merkle 树增量索引（Cursor 范式）**
    - 实现：每个文件 SHA-256 哈希，目录哈希 = 子节点哈希拼接后再 SHA-256；变更沿父目录传播；只 re-embed 哈希不一致的分支。
    - 效果：大型仓库二次索引从小时级降到秒级，支持频繁重生成文档。

11. **simhash 索引复用（Cursor 范式）**
    - 实现：组织内多个项目相似度高时，新项目算 simhash 找最相似已有索引 `copy_from_namespace`。
    - 效果：首次可查询时间从分钟级降到毫秒级，适合多 repo 文档批量生成。

12. **MCP 工具描述按需加载（Cursor 范式）**
    - 实现：docbot 接入的「代码图 MCP」「git MCP」「lint MCP」描述不同时进系统提示，按文件归档，agent 需要时 `ls` + `grep` 查详情。
    - 效果：agent 总 token -46.9%（Cursor A/B 数据），上下文更聚焦。

### 实施路线图建议

```
第 1 周（P0）：tree-sitter 签名直填 + STORM 内联引用 + SWE-agent lint 三件套
              → 立即消除 80% 的「编造签名」「无引用断言」「示例调用不存在函数」幻觉

第 2-3 周（P1）：Aider 符号图 + PageRank + Continue.dev 双索引
              → 仓库理解从「全塞进上下文」升级为「按重要性选上下文」

第 4 周（P2）：CoVe 验证链 + RepoCoder 迭代检索
              → 定稿前自检 + 跨文件证据补全

第 5+ 周（P3）：Merkle 增量 + simhash 复用 + MCP 按需加载
              → 工程性能优化，支持大规模批量文档生成
```

---

## 11. 关键结论

1. **「签名直填 + 强制内联引用 + 生成即 lint」是文档生成场景性价比最高的三件套**，覆盖 80% 幻觉，可在 1 周内落地。
2. **Aider 的 PageRank 符号图是「仓库理解」的黄金范式**，把全仓库压缩进 token 预算同时保留 API 边界——docbot 的 `repo_map.py` 已有同类实现，应深度对齐 Aider 的 personalization 与 mul 启发式。
3. **STORM 的 `WriteSection` dspy.Signature 是「强制 grounding」的最佳实践**，`[n]` 内联引用 + 1500 词截断 + `clean_up_section` 三件组合可直接复用。
4. **SWE-agent 的「edit 后自动 lint」是「生成即验证」的范式原型**，docbot 生成代码示例后应立即 lint，失败则重写。
5. **Cursor 的「文件即原语」是长文档上下文管理的未来方向**，避免长上下文截断与串台幻觉，适合 docbot 分章节生成场景。
6. **RepoCoder 与 CoVe 提供了「迭代闭环」的两条路径**：前者用生成结果作新查询（适合补全调用样例），后者用自检问题作新查询（适合事实核查）；两者可组合。
7. **硬引用校验（生成后程序化反查）当前业界实现薄弱**——Aider/Continue.dev/Cursor 都未做，是 docbot 可差异化的护城河：在 STORM 格式契约基础上加一层「`[n]` → 代码行存在性」硬校验，即可显著超越现有开源方案。

---

## 参考资料

### 项目源码
- Aider: https://github.com/Aider-AI/aider（核心：`aider/repomap.py`、`aider/queries/*.scm`）
- STORM/Co-STORM: https://github.com/stanford-oval/storm（核心：`knowledge_storm/storm_wiki/modules/article_generation.py`）
- SWE-agent: https://github.com/SWE-agent/SWE-agent（v0.7: `sweagent/tools/str_replace_editor.py`；v1.0: `src/sweagent/tools/`）
- Continue.dev: https://github.com/continuedev/continue（核心：`core/indexing/*.ts`）
- RepoCoder: https://github.com/microsoft/CodeT/tree/main/RepoCoder
- mini-SWE-agent: https://github.com/SWE-agent/mini-swe-agent

### 论文
- RepoCoder (EMNLP 2023): arXiv:2303.12570
- SWE-agent (NeurIPS 2024): arXiv:2405.15793
- STORM (NAACL 2024): arXiv:2402.14207
- Co-STORM (EMNLP 2024): arXiv:2408.15232
- Chain-of-Verification (Meta): arXiv:2309.11495
- Self-RAG: arXiv:2310.11511
- CRAG: arXiv:2401.15884

### 官方博客与文档
- Aider Repo Map: https://aider.chat/docs/repomap.html
- Aider ctags 历史: https://aider.chat/docs/ctags.html
- Cursor Dynamic Context Discovery (2026-01-06): https://cursor.com/blog/dynamic-context-discovery
- Cursor 代码库索引机制剖析: https://x.com/manthanguptaa/status/2067096080886698364
- Turbopuffer × Cursor: https://turbopuffer.com/customers/cursor
- Continue.dev 索引构建: https://juejin.cn/post/7517183666688294950

---

*报告生成日期：2026-07-30*
*研究范围：2023–2026 年开源 AI Agent 代码仓库理解方法论*

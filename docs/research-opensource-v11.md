# 开源 AI Agent 代码仓库理解方法论：v11 深度研究报告

> **研究目标**: 针对 docbot v10 实测暴露的四大顽疾，从五个开源项目（Aider / STORM / Continue.dev / AutoCodeRover / RepoCoder）提炼可落地的代码级借鉴方案
> **基线数据**: v10 平均综合相似度 26.3%（PRD 17.6% / API 35.0%），目标 >80%，差距 -53.7%
> **诊断来源**: `docs/e2e-output/compare-v10-result.txt` + docbot 源码审计 + 开源项目源码
> **报告性质**: 仅研究报告，不含代码改动

---

## 0. 摘要（Executive Summary）

docbot v10 的四大顽疾与五个开源项目的对应解法：

| docbot 顽疾 | v10 实测 | 开源解法来源 | 核心机制 |
|---|---|---|---|
| monorepo 主项目误判 | Admin 子项目被误判 In-Scope | Aider personalization | 入口文件/Controller 密度/构建文件多信号加权 |
| 品牌名被翻译 | AgentInsight→智能体，品牌相似度 21.2% | STORM dspy Signature + Aider 签名直填 | 强制契约 prompt + 不可翻译白名单 + 后置回滚 |
| HTTP 端点遗漏 | 21/75+，缺 WeChatController 等 6 个 | AutoCodeRover AST 搜索 + Aider tree-sitter .scm | 结构化查询替代正则，覆盖 minimal API + Handler |
| .NET Controller 特性提取不全 | signature_extractor 5 行 lookahead | Continue.dev CodeSnippets + Aider tree-sitter | tree-sitter C# 语法树精确解析，无 lookahead 限制 |

**最关键发现**: docbot 同时存在两套 .NET Controller 解析器——`src/agents/docbot/signature_extractor.py`（弱版，5 行 lookahead，被 content_filler 实际调用）与 `src/skills/docbot/ast_search.py`（强版，10 行 lookahead，支持 `[controller]` 替换，但未用于 API 卡片生成）。**统一到 ast_search.py 并升级为 tree-sitter 解析**是最高优先级修复。

---

## 1. docbot v10 现状诊断

### 1.1 v10 端到端测试结果（compare-v10-result.txt）

```
PRD 需求文档: Jaccard=8.4%, Cosine=27.9%, 标题=5.7%, 路径=5.9%, 品牌=62.8%, 综合=17.6%
API 文档:      Jaccard=9.2%, Cosine=58.9%, 标题=5.4%, 路径=13.6%, 品牌=21.2%, 综合=35.0%
平均综合相似度: 26.3% (目标 80%, 差距 -53.7%)
```

### 1.2 四大顽疾的代码级定位

#### 顽疾 1: monorepo 主项目误判

- **现象**: docbot PRD 1.5 写成 "基于 Django Admin 与 SimpleUI 的后台管理系统"（实际是 .NET API 服务）
- **代码位置**: `src/skills/docbot/scope_detector.py:160-189`
- **现状**: v10 已实施 `_heuristic_scope_decision`（入口文件 + 构建文件启发式），但仍依赖 LLM 兜底，Admin/AGENTS.md 详尽内容带偏 LLM

#### 顽疾 2: 品牌名被翻译

- **现象**: AgentInsight→智能体，品牌相似度从 PRD 的 62.8% 暴跌到 API 文档的 21.2%
- **代码位置**: `src/skills/docbot/terminology_glossary.py`
- **现状**: 已有 glossary 提取 + prompt 注入 + 后置回滚三层防御，但仍失败。原因：API 文档生成时 LLM 重写签名行，glossary 约束被签名重写覆盖

#### 顽疾 3: HTTP 端点遗漏

- **现象**: 参考文档 75+ 接口，docbot 只找到 21 个
- **缺失的 Controller**（从 compare-v10-result.txt 缺失关键词反推）:
  - `WeChatController` (ToolsManagement/WeChat/)
  - `AgentSessionController` (AgentManagement/)
  - `OrganizationController` (UserManagement/)
  - `NotifyController` (PaymentManagement/)
  - `BulletinController` (ToolsManagement/)
  - `OrderController` (PaymentManagement/)
- **代码位置**: `src/agents/docbot/content_filler.py:568` 调用的是弱版 `SignatureExtractor`，而非强版 `ast_search.search_http_endpoints`

#### 顽疾 4: .NET Controller 特性提取不全

- **现象**: signature_extractor.py 的 `_parse_dotnet_actions` 使用 5 行 lookahead，遇到 `[ProducesResponseType]` ×5 的真实 Controller 会丢失方法
- **代码位置**: `src/agents/docbot/signature_extractor.py:163-212`
- **具体缺陷**:
  - 5 行 lookahead 太小（真实 Controller 的 `[HttpGet]` 与方法签名间常有 5-10 个 `[ProducesResponseType]`/`[SwaggerOperation]` 特性）
  - `_extract_controller_route_prefix` 不替换 `[controller]`/`[action]` 占位符
  - 不识别 minimal API（`app.MapGet`/`app.MapPost`）
  - 不识别 `[ApiController]` 约定路由（无 `[HttpGet]` 但有 `[Route]` 的方法）
  - 方法签名正则要求 `public` + 特定返回类型模式，遗漏 `IActionResult`/`ActionResult<T>` 等变体

---

## 2. Aider —— RepoMap + PageRank 符号排序（深度研究）

### 2.1 核心文件与算法位置

- `aider/repomap.py`：`RepoMap` 类
  - `get_tags_raw` (line 223)：tree-sitter 标签抽取
  - `get_ranked_tags` (line 293)：PageRank + personalization 排序
  - `get_repo_map` (line 80)：token 预算贪心填充
- `aider/queries/tree-sitter-*.scm`：各语言标签查询文件
- `grep_ast/`：tree-sitter 包装库

### 2.2 tree-sitter 标签抽取（get_tags_raw）

```python
# aider/repomap.py:223-292 (简化)
Tag = namedtuple("Tag", "rel_fname fname line name kind".split())

def get_tags_raw(self, fname, rel_fname):
    lang = filename_to_lang(fname)
    language = get_language(lang)
    parser = get_parser(lang)
    query_scm = get_scm_fname(lang).read_text()  # 读 .scm 查询文件
    tree = parser.parse(bytes(code, "utf-8"))
    captures = self._run_captures(Query(language, query_scm), tree.root_node)

    for node, tag in all_nodes:
        if tag.startswith("name.definition."):
            kind = "def"           # 定义：类/函数/方法
        elif tag.startswith("name.reference."):
            kind = "ref"          # 引用
        else:
            continue
        yield Tag(rel_fname, fname, node.text.decode("utf-8"),
                  kind, node.start_point[0])
```

**关键设计**:
- 只保留 `def` 与 `ref` 两类标签，丢弃实现体——这是把仓库压缩进 token 预算的根本手段
- 若某语言 `.scm` 只能抽出 def（如 cpp），用 Pygments 回填 ref，保证图连通性
- 标签按 `(fname, mtime)` 落盘到 `diskcache`（SQLite 后端），二次启动零成本

### 2.3 PageRank + Personalization 排序（get_ranked_tags）

```python
# aider/repomap.py:293-410 (核心逻辑)
def get_ranked_tags(self, chat_fnames, other_fnames, mentioned_fnames, mentioned_idents):
    defines = defaultdict(set)      # ident -> {定义它的文件}
    references = defaultdict(list)  # ident -> [引用它的文件]
    personalization = dict()
    fnames = sorted(set(chat_fnames).union(other_fnames))
    personalize = 100 / len(fnames)  # 默认均匀分布

    for fname in fnames:
        current_pers = 0.0
        if fname in chat_fnames:           current_pers += personalize  # 聊天文件提权
        if rel_fname in mentioned_fnames:  current_pers = max(current_pers, personalize)
        if matched_idents:                 current_pers += personalize  # 命中提及符号提权
        if current_pers > 0:
            personalization[rel_fname] = current_pers

    G = nx.MultiDiGraph()
    for ident in idents:                   # ident = def 名 ∩ ref 名
        definers = defines[ident]
        mul = 1.0
        if ident in mentioned_idents:      mul *= 10          # 命中提及符号 ×10
        if (is_snake or is_kebab or is_camel) and len(ident) >= 8:
            mul *= 10                       # 有意义的长标识符 ×10
        if ident.startswith("_"):          mul *= 0.1        # 私有符号降权
        if len(defines[ident]) > 5:         mul *= 0.1        # 高频通用名降权
        for referencer, num_refs in Counter(references[ident]).items():
            for definer in definers:
                use_mul = mul
                if referencer in chat_rel_fnames:
                    use_mul *= 50           # 被聊天文件引用 ×50
                G.add_edge(referencer, definer, weight=use_mul * num_refs, ident=ident)

    ranks = nx.pagerank(G, personalization=personalization)
```

**排序逻辑精髓**:
- **节点 = 文件，边 = ref 文件 → def 文件**，边权 = `引用次数 × mul`
- **personalization 向量**：把概率质量集中到「当前聊天文件 / 用户提到文件 / 用户提到符号所在文件」，PageRank 向这些节点的语义邻域扩散
- **mul 启发式**直接抑制「通用词被误当核心 API」的幻觉
- 排序后按 `--map-tokens`（默认 1k，无文件时自动放大到 `map_tokens × 8`，预留 4096 padding）贪心填充

### 2.4 签名直填渲染

选中的标签交给 `grep_ast.TreeContext` 渲染，输出形如：

```
aider/coders/base_coder.py:
⋮...
│class Coder:
│   abs_fnames = None
⋮...
│   @classmethod
│   def create(self, main_model, edit_format, io, **kwargs):
⋮...
```

- **类/方法/函数签名连同参数列表原样保留**，方法体折叠为 `⋮...`
- **行号与缩进保留**，LLM 能精确判断「这个类在哪个文件第几行」
- 这就是「签名直填」机制——**LLM 不自由描述签名，签名从 AST 直接提取并渲染**

### 2.5 对 docbot 的借鉴建议

#### 2.5.1 monorepo 主项目识别（借鉴 personalization）

Aider 的 personalization 思路可直接用于 monorepo 主项目识别：把每个子项目当作「文件节点」，给不同信号赋予不同权重：

```python
# 建议在 scope_detector.py 新增 _score_subproject (借鉴 Aider personalization)
def _score_subproject(repo: Path, sub_dir: Path) -> float:
    """v11: 多信号加权评分子项目为主项目的可能性 (借鉴 Aider personalization).

    信号 (权重借鉴 Aider mul 启发式):
    - 含主入口文件 (Program.cs/Startup.cs): +50  (类比 chat_rel_fnames ×50)
    - 含 *.csproj 非测试项目: +30
    - Controllers/ 目录存在且 .cs 文件 >5: +20
    - 含 AGENTS.md: +10 (但若内容含 "Admin"/"管理后台": -30)
    - 子项目名含 sdk/client/docs/test: -50  (降权, 类比 startswith("_") ×0.1)
    - 含 manage.py 但无 Controllers/: -20   (Django Admin 降权)
    """
    score = 0.0
    # ... 信号加权 ...
    return score
```

#### 2.5.2 tree-sitter .scm 查询替代正则

Aider 用 `.scm` 查询文件声明式定义「抽取什么标签」，比 docbot 的正则更鲁棒。建议为 C# 编写 `.scm` 查询文件：

```
; queries/tree-sitter-csharp.scm (建议新增)
(class_declaration
  name: (identifier) @name.definition.class
  body: (declaration_list
    (method_declaration
      name: (identifier) @name.definition.method
      parameters: (parameter_list) @method.params
      type: (_) @method.return_type)))

(attribute
  name: (identifier) @attribute.name
  (attribute_argument_list) @attribute.args)
```

---

## 3. STORM —— 两阶段 outline + 强制内联引用（深度研究）

### 3.1 核心文件与算法位置

- `knowledge_storm/storm_wiki/modules/article_generation.py`：`ConvToSection`、`WriteSection`
- `knowledge_storm/storm_wiki/modules/outline.py`：`StormOutlineGenerator`
- `knowledge_storm/interface.py`：`STORMWikiRunnerArguments`

### 3.2 两阶段 outline 生成（outline → draft → refine）

STORM 把「写带引用的长文」拆成两阶段：

**阶段 1: Pre-writing（调研）**
- 多视角专家（perspective）与话题专家模拟对话
- 每轮检索结果包装成 `Information` 对象（含 URL、snippets、视角元数据）落 `StormInformationTable`
- `information_table.prepare_table_for_retrieval()` 在成文前预构建检索索引

**阶段 2: Writing（成文）**
- `StormOutlineGenerator` 先生成 outline（章节结构）
- `WriteSection.generate_section` 按章节反查 `information_table`：

```python
# article_generation.py (GitHub main)
def generate_section(self, topic, section_name, information_table, section_outline, section_query):
    collected_info: List[Information] = []
    if information_table is not None:
        collected_info = information_table.retrieve_information(
            queries=section_query, search_top_k=self.retrieve_top_k  # 默认 5
        )
    output = self.section_gen(
        topic=topic, outline=section_outline, section=section_name,
        collected_info=collected_info,
    )
    return {"section_name": section_name,
            "section_content": output.section,
            "collected_info": collected_info}
```

### 3.3 强制内联引用的 dspy Signature（防模板污染核心）

```python
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

**防幻觉与防模板污染要点**:
- **每个章节只看 ≤1500 词的 `collected_info`**，超出强制截断——防止模型从「长上下文里挑一段未被引用的内容」幻觉
- **`[n]` 索引对应 `collected_info` 列表下标**，成文后可程序化反查「每条引用指向哪个 snippet / URL」——这是硬引用校验的基础
- `ArticleTextProcessing.clean_up_section` 会清理无引用段落、重复引用、空洞套话
- **避免通用模板污染**：每个章节的 `collected_info` 来自该章节专属的 `section_query` 检索结果，而非全局共享上下文。章节间信息隔离，防止「A 章节的事实被误植入 B 章节」

### 3.4 对 docbot 的借鉴建议

#### 3.4.1 借鉴 dspy Signature 强制契约（解决品牌名翻译）

docbot 当前用自然语言 prompt 约束 LLM 不翻译品牌名，但 v10 实测品牌相似度仅 21.2%。借鉴 STORM 的 dspy Signature 思路，把「不可翻译」写成结构化契约：

```python
# 建议在 prompts.py 新增结构化签名 (借鉴 STORM WriteSection dspy.Signature)
WRITE_API_DOC = dspy.Signature("""
    Write an API documentation section based on the provided code signatures.

    MANDATORY CONSTRAINTS (violation = retry):
    1. Brand names in forced_original_terms MUST appear verbatim in output
       (e.g., "AgentInsight" must NOT become "智能体")
    2. Class names in glossary.class_names MUST appear verbatim
       (e.g., "UserController" must NOT become "用户控制器")
    3. File paths MUST preserve original PascalCase
       (e.g., "API/Controllers" must NOT become "api/控制器")
    4. Use [SIG-001], [SIG-002]... to reference signatures from api_signatures table
    5. DO NOT translate any term in forced_original_terms to Chinese
    6. DO NOT use "中文（English）" mixed pattern; use English only

    api_signatures = {signatures_table}
    glossary = {glossary_text}
    forced_original_terms = {forced_terms}
""")
```

#### 3.4.2 借鉴章节级信息隔离（防止端点间互相污染）

docbot 当前 `content_filler.py:934` 注入 `endpoints_text[:10000]`（10K 字符截断），可能导致 75+ 端点时后面的端点被截断。借鉴 STORM 的章节级 `collected_info`：

```python
# 建议在 content_filler.py 改造 _generate_api_doc_by_endpoint
def _generate_api_doc_by_endpoint(self, endpoint: dict, signature: dict) -> str:
    """v11: 每个端点只看自己的签名 + 相关枚举 (借鉴 STORM 章节级信息隔离).

    每个端点单独 LLM 调用, context 仅含:
    - 该端点的签名 (从 AST 提取, 不让 LLM 重写)
    - 该端点引用的枚举定义 (从 search_enum_definitions 反查)
    - 强制术语词典 (防止品牌名翻译)
    """
    # 不再注入全部 endpoints_text, 仅注入当前端点的签名
    section_context = {
        "endpoint": endpoint,
        "signature": signature,  # AST 直填, LLM 不可修改
        "related_enums": self._find_related_enums(endpoint),
        "glossary": glossary_text,  # 术语词典
    }
    # LLM 只补文字说明, 签名行原样注入
```

---

## 4. Continue.dev —— CodeSnippetsCodebaseIndex 四层混合索引（深度研究）

### 4.1 核心文件与算法位置

- `core/indexing/CodeSnippetsCodebaseIndex.ts`：结构化代码片段索引
- `core/indexing/LanceDbIndex.ts`：向量索引
- `core/indexing/FullTextSearchCodebaseIndex.ts`：FTS5 全文索引
- `core/indexing/chunk/chunk.ts`：`chunkDocumentWithoutId`、`shouldChunk`、`collapseChildren`
- `core/indexing/CodebaseIndexer.ts`：索引器主类

### 4.2 四层索引架构

| 索引 | 存储 | 用途 | 搜索能力 |
|---|---|---|---|
| ChunkCodebaseIndex | SQLite | 基础分块，给其他索引用 | 不直接搜索 |
| LanceDbIndex | LanceDB + SQLite 元数据 | 语义相似度 | 向量检索 |
| FullTextSearchCodebaseIndex | SQLite FTS5（trigram） | 关键词/精确匹配 | 倒排 |
| CodeSnippetsCodebaseIndex | SQLite | 结构化元素（函数/类签名） | 按 tag/标题 |

### 4.3 CodeSnippetsCodebaseIndex 详解（签名直填来源）

这是对 docbot 最有借鉴价值的层：

- 用 **tree-sitter query** 识别函数、类、其他顶层代码对象
- 保存片段元数据：**标题、路径、起止行号、内容**
- 通过 `code_snippets_tags` 关联标签，便于按 tag 检索
- 适合「快速定位特定代码结构」——例如「找到所有 `@dataclass` 装饰的类」

**关键设计**:
- 片段内容是 tree-sitter 抽取的**真实代码片段**，非 LLM 生成
- 可作为「签名来源」直接注入 prompt，避免 LLM 自由描述签名
- tag 机制支持按属性检索（如 `@HttpGet`、`@Route`、`@dataclass`）

### 4.4 INSTRUCTIONS_BASE_ITEM 注入机制

Continue.dev 的 `INSTRUCTIONS_BASE_ITEM` 是把结构化指令注入 LLM 的模式：

- 每个索引项有 `name`/`description`/`path` 等结构化字段
- 注入 prompt 时保留原始标识符，不翻译
- 片段内容原样注入（含原始大小写、路径分隔符）

### 4.5 对 docbot 的借鉴建议

#### 4.5.1 借鉴 CodeSnippetsCodebaseIndex 结构化存储

docbot 当前 `signature_extractor.py` 每次调用都重新解析文件，无缓存。借鉴 Continue.dev 的结构化存储：

```python
# 建议新增 skills/docbot/code_snippets_index.py (借鉴 CodeSnippetsCodebaseIndex)
class CodeSnippetsIndex:
    """v11: 结构化代码片段索引 (借鉴 Continue.dev CodeSnippetsCodebaseIndex).

    用 tree-sitter 抽取并缓存代码片段 (函数/类/方法签名),
    支持 tag 检索 (如 @HttpGet / @Route / [ApiController]).

    存储结构 (SQLite, 借鉴 Continue.dev schema):
    - code_snippets: id, title, path, start_line, end_line, content, lang
    - code_snippets_tags: snippet_id, tag (如 "HttpGet", "Route", "Controller")
    """

    def build_index(self, repo_path: str, file_index: dict) -> None:
        """构建代码片段索引 (tree-sitter 抽取)."""
        for abs_path, rel_path, ext, lang in _iter_code_files(repo_path, file_index):
            content = abs_path.read_text(encoding="utf-8", errors="replace")
            snippets = self._extract_snippets_via_treesitter(content, lang)
            for snip in snippets:
                self._store_snippet(snip, rel_path, lang)
                # 提取 tag (如 [HttpGet] -> "HttpGet", [Route] -> "Route")
                tags = self._extract_tags(snip)
                self._store_tags(snip.id, tags)

    def search_by_tag(self, tag: str) -> list[dict]:
        """按 tag 检索片段 (如 tag="HttpGet" 返回所有 GET 端点)."""
        return self._db.query("""
            SELECT s.* FROM code_snippets s
            JOIN code_snippets_tags t ON s.id = t.snippet_id
            WHERE t.tag = ?
        """, tag)
```

#### 4.5.2 借鉴 FTS5 trigram 精确匹配（防止品牌名遗漏）

docbot 当前 glossary 用正则匹配 PascalCase，但 AgentInsightService 的 `AgentInsightAPIKey`、`AgentInsightConst` 等长品牌名可能被遗漏。借鉴 Continue.dev 的 FTS5 trigram：

```python
# 建议在 terminology_glossary.py 新增 FTS5 索引 (借鉴 Continue.dev FullTextSearchCodebaseIndex)
def build_brand_name_fts5_index(self, glossary: dict) -> None:
    """v11: 用 FTS5 trigram 索引品牌名 (借鉴 Continue.dev).

    trigram 把 "AgentInsight" 拆为 ["Age","gen","ent","ntI","tIn","Ins","nsi","sig","igh","ght"],
    支持模糊匹配 (如文档中出现 "智能体Insight" 也能检测到 "Insight" 子串).
    """
    # 创建 FTS5 表
    self._db.executescript("""
        CREATE VIRTUAL TABLE IF NOT EXISTS brand_names_fts
        USING fts5(term, tokenize='trigram');
    """)
    for term in glossary["forced_original_terms"]:
        self._db.execute("INSERT INTO brand_names_fts VALUES (?)", term)
```

---

## 5. AutoCodeRover —— AST 结构化搜索 API（深度研究）

### 5.1 核心文件与算法位置

- `auto_code_rover/code_repair.py`：代码修复主循环
- `auto_code_rover/context_retrieval/`：上下文检索 API
- `auto_code_rover/llm_reranking.py`：LLM 重排序

### 5.2 AST 结构化搜索 API

AutoCodeRover 的核心创新是「**上下文检索 API**」——为 LLM 提供结构化搜索命令，而非裸 grep：

| API | 作用 | 类比 docbot |
|---|---|---|
| `search_class(class_name)` | 按类名搜索类定义 | ast_search 缺失（仅正则） |
| `search_method(method_name)` | 按方法名搜索方法定义 | ast_search 缺失 |
| `search_code_in_file(keyword, file)` | 在指定文件搜代码 | grep |
| `get_codebirds_for_class(class_name)` | 获取类的所有代码块 | docbot 无 |
| `search_code_in_codebirds(keyword, codebirds)` | 在代码块中搜 | docbot 无 |

### 5.3 签名优先策略

AutoCodeRover 的策略是「**先看签名，再看实现**」：

1. 第一轮检索只返回方法/类的**签名行**（不含方法体）
2. LLM 据此判断哪些方法相关
3. 第二轮对相关方法做 `get_codebirds` 拉取完整实现

这避免了「一次塞太多实现代码」导致 token 膨胀，同时让 LLM 先建立全局认知。

### 5.4 枚举所有 Controller/路由/枚举定义

AutoCodeRover 的 `search_class` 可枚举所有继承自特定基类或带特定注解的类：

```python
# AutoCodeRover 风格的 AST 搜索 (伪代码)
def search_classes_by_annotation(annotation: str) -> list[ClassDef]:
    """枚举所有带指定注解的类 (如 @RestController / [ApiController])."""
    results = []
    for file in code_files:
        tree = parse(file)
        for node in walk(tree):
            if node.type == "class_declaration":
                attrs = extract_attributes(node)
                if any(a.name == annotation for a in attrs):
                    results.append(ClassDef(node, file))
    return results
```

### 5.5 对 docbot 的借鉴建议

#### 5.5.1 借鉴 AST 搜索 API 枚举所有 Controller

docbot 的 `ast_search.py` 已部分实现 AutoCodeRover 思路，但缺**按注解搜索类**的能力：

```python
# 建议在 ast_search.py 新增 search_classes_by_attribute (借鉴 AutoCodeRover search_class)
def search_classes_by_attribute(
    repo_path: str,
    attribute_patterns: list[str],
    file_index: dict | None = None,
) -> list[dict]:
    """v11: 枚举所有带指定特性的类 (借鉴 AutoCodeRover AST 搜索 API).

    支持:
    - [ApiController] (ASP.NET Core)
    - [Route("...")] (ASP.NET Core 路由前缀)
    - [ApiController] + [Route] 组合判定 Controller
    - 继承 Microsoft.AspNetCore.Mvc.Controller 的类

    与 search_http_endpoints 的区别:
    - search_http_endpoints 找方法级 [HttpGet] (Action 粒度)
    - 本函数找类级 [ApiController]/[Route] (Controller 粒度)
    - 二者互补: Controller 找到后, 其所有 public 方法都是潜在端点
    """
    controllers = []
    for abs_path, rel_path, ext, lang in _iter_code_files(repo_path, file_index):
        if ext != ".cs":
            continue
        content = abs_path.read_text(encoding="utf-8", errors="replace")
        # 检测 [ApiController] 或继承 Controller 基类
        has_api_controller = bool(re.search(r'\[ApiController\]', content))
        inherits_controller = bool(re.search(r':\s*(Controller|ControllerBase)\b', content))
        if has_api_controller or inherits_controller:
            controllers.append({
                "file_path": rel_path,
                "class_name": _extract_class_name(content),
                "route_prefix": _extract_route_prefix(content),
                "has_api_controller": has_api_controller,
            })
    return controllers
```

#### 5.5.2 借鉴签名优先策略（解决 75+ 端点 token 膨胀）

docbot 当前 `content_filler.py:934` 注入 `endpoints_text[:10000]`，75+ 端点时必然截断。借鉴 AutoCodeRover 签名优先：

```python
# 建议在 content_filler.py 分两轮 (借鉴 AutoCodeRover 签名优先)
def _generate_api_doc_v11(self, code_learning: dict) -> str:
    """v11: 签名优先两轮生成 (借鉴 AutoCodeRover).

    第一轮: 注入所有端点的签名行 (1 行/端点, 75 端点 ~3K token)
           LLM 据此生成 outline + 端点分组
    第二轮: 按分组逐个端点生成卡片 (每端点单独 LLM 调用)
    """
    # 第一轮: 仅签名
    signatures_brief = "\n".join(
        f"{ep['http_method']} {ep['route']} -> {ep['class_name']}.{ep['method_name']}"
        for ep in endpoints
    )
    outline = self._llm_generate_outline(signatures_brief)

    # 第二轮: 按分组逐个生成
    for group in outline.groups:
        for ep in group.endpoints:
            card = self._generate_one_endpoint_card(ep)  # 单端点 context
```

---

## 6. RepoCoder —— 迭代检索-生成范式（深度研究）

### 6.1 核心文件与算法位置

- `repocoder/repocoder.py`：主算法
- `repocoder/retriever.py`：检索器
- `repocoder/utils.py`：滑动窗口编码
- 论文：arXiv:2303.12570（EMNLP 2023）

### 6.2 迭代检索-生成核心算法

```
输入：未完成代码 X，滑动窗口 S_w，步长 S_s，检索器 R，生成器 M

# 第一轮：用 X 的尾部作查询
q1 = X 的最后 S_w 行
C1 = R(q1)                          # 检索相似片段
Y1 = M(C1, X)                       # 生成中间代码

# 第二轮：用 X 的尾部 + Y1 的头部作查询
q2 = X 的后 (S_w - S_s) 行  +  Y1 的前 S_s 行
C2 = R(q2)                          # 用生成结果反查
Y_final = M(C2, X)                  # 最终生成
```

**关键洞察**:
- **第一轮 Y1 是「模型对目标的猜测」**，把它当作新查询能更精确地命中「真正需要的跨文件上下文」
- 这是 **Generation-Augmented Retrieval**（用生成结果增广检索）与 **Retrieval-Augmented Generation**（用检索结果增广生成）的闭环
- 闭环可迭代 k 轮直到收敛（实验显示 2 轮已收敛大部分增益）

### 6.3 对 docbot 的借鉴建议

#### 6.3.1 借鉴草稿驱动的二次检索（解决端点遗漏）

docbot 当前单轮检索端点，可能遗漏。借鉴 RepoCoder 的迭代检索：

```python
# 建议在 code_learner.py 新增二次检索 (借鉴 RepoCoder)
def learn_code_iterative(self, repo_path: str) -> dict:
    """v11: 两轮代码学习 (借鉴 RepoCoder 迭代检索-生成).

    第一轮: 常规扫描端点 + 枚举 + 路径
    第二轮: 用第一轮草稿中的类名/方法名反查仓库,
           找出第一轮遗漏的端点 (如 Handler 路由 / minimal API)
    """
    # 第一轮: 常规扫描
    round1 = {
        "endpoints": search_http_endpoints(repo_path),
        "enums": search_enum_definitions(repo_path),
    }

    # 用第一轮结果中的 Controller/Handler 类名反查
    discovered_classes = {ep["class_name"] for ep in round1["endpoints"]}
    # 第二轮: 搜索这些类引用的其他 Handler/Service 类
    round2_endpoints = self._search_via_class_references(
        repo_path, discovered_classes
    )

    # 合并去重
    all_endpoints = self._merge_endpoints(round1["endpoints"], round2_endpoints)
    return {"endpoints": all_endpoints, ...}
```

---

## 7. 针对 docbot 四大顽疾的代码级解决方案（汇总）

> 本节为汇总表，详细代码见对应章节（§2.5 / §3.4 / §4.5 / §5.5 / §6.3）。

### 7.1 顽疾 1 → monorepo 主项目识别

**根因**: `_heuristic_scope_decision`（scope_detector.py:219）信号不足，Admin/AGENTS.md 带偏 LLM

**建议实现**: `_score_subproject(repo, sub_dir) -> tuple[float, str]`（详见 §2.5.1）

| 信号 | 权重 | 借鉴 Aider |
|---|---|---|
| 含 Program.cs/Startup.cs | +50 | 类比 chat_rel_fnames ×50 |
| 含 *.csproj 非测试 | +30 | 类比 personalization |
| Controllers/ 目录 .cs ≥5 | +20 | 类比 长标识符 ×10 |
| AGENTS.md 含 "Django Admin"/"SimpleUI" | -30 | 类比 startswith("_") ×0.1 |
| 子项目名含 sdk/client/docs/test | -50 | 降权 |

**决策**: score > 50 → `in_scope`；score < -20 → `out_of_scope`；灰区交 LLM 兜底。

### 7.2 顽疾 2 → 品牌名翻译防护

**根因**: terminology_glossary.py 三层防御被 LLM 签名重写覆盖（详见 §3.4 / §2.4）

**建议实现**:
1. **签名直填**（借鉴 Aider TreeContext）：签名行用 `{{LOCKED}}...{{/LOCKED}}` 标记，LLM 只填 `{{LLM_FILL}}` 区块
2. **强制契约 prompt**（借鉴 STORM dspy.Signature）：`API_CARD_SIGNATURE` 写 MANDATORY CONSTRAINTS
3. **后置回滚**（保留现有 terminology_glossary.validate_and_rollback_terms）

### 7.3 顽疾 3 → HTTP 端点完整枚举

**根因**: content_filler.py:568 调用弱版 SignatureExtractor，且不识别 minimal API / Handler 路由

**建议实现**（详见 §5.5 / §6.3）:
1. **统一入口**: `content_filler.py:568` 改用 `ast_search.search_http_endpoints`
2. **新增 `search_minimal_api_endpoints`**: 匹配 `app.MapGet/MapPost`（详见 §5.5）
3. **新增 `search_handler_routes`**: 用 `*Handler` 类名反查路由（借鉴 RepoCoder 二次检索，详见 §6.3）
4. **新增 `search_classes_by_attribute`**: 枚举 `[ApiController]` 类（详见 §5.5.1）

### 7.4 顽疾 4 → .NET Controller 特性完整提取

**根因**: signature_extractor.py 用正则 + 5 行 lookahead（详见 §1.2 顽疾 4）

**建议实现**（详见 §2.5.2 / §4.5.1）:
1. **tree-sitter C# `.scm` 查询**: 声明式抽取，无 lookahead 限制
2. **`_search_csharp_endpoints_via_ast`**: 用 AST 替代正则，精确识别特性-方法归属
3. **`[controller]`/`[action]` 双占位符替换**: 在 `_build_csharp_route` 中实现
4. **降级策略**: tree-sitter 解析失败时降级到现有 `_search_csharp_endpoints` 正则

---

## 8. 推荐实现路径

### 8.1 优先级排序（P0 → P3）

| 优先级 | 任务 | 借鉴来源 | 预期收益 | 工作量 |
|---|---|---|---|---|
| **P0** | 废弃 signature_extractor.py，统一用 ast_search.py | Aider/AutoCodeRover | 端点数 21→50+ | 0.5 天 |
| **P0** | 新增 search_minimal_api_endpoints | AutoCodeRover | 端点数 +10~20 | 0.5 天 |
| **P0** | 新增 search_handler_routes | RepoCoder 二次检索 | 端点数 +5~10 | 1 天 |
| **P0** | 签名直填（LLM 不重写签名行） | Aider TreeContext | 品牌相似度 +20% | 1 天 |
| **P1** | _score_subproject 多信号加权 | Aider personalization | Admin 误判消除 | 0.5 天 |
| **P1** | STORM 风格强制契约 prompt | STORM dspy.Signature | 品牌相似度 +10% | 0.5 天 |
| **P1** | endpoints_text 截断改为签名优先两轮 | AutoCodeRover 签名优先 | 75+ 端点全覆盖 | 1 天 |
| **P2** | tree-sitter C# .scm 查询替代正则 | Aider tree-sitter | 端点精确度 + | 2 天 |
| **P2** | [controller]/[action] 占位符替换 | ASP.NET Core 约定 | 路径相似度 +10% | 0.5 天 |
| **P2** | CodeSnippetsIndex 结构化存储 | Continue.dev | 缓存 + tag 检索 | 2 天 |
| **P3** | RepoCoder 迭代检索（二轮） | RepoCoder | 遗漏端点自动补全 | 1.5 天 |
| **P3** | FTS5 trigram 品牌名索引 | Continue.dev FTS5 | 模糊匹配品牌名 | 1 天 |

### 8.2 实施阶段

#### 阶段 1: 止血（P0，预计 3 天）

1. **统一端点搜索入口**: `content_filler.py:568` 改用 `ast_search.search_http_endpoints`
2. **补充 minimal API + Handler 路由**: 新增两个搜索函数
3. **签名直填改造**: API 卡片生成时签名行从 AST 提取，`{{LOCKED}}` 标记不可修改

#### 阶段 2: 加固（P1，预计 2 天）

1. **monorepo 评分**: `_score_subproject` 多信号加权，Admin 子项目硬判 Out-of-Scope
2. **强制契约 prompt**: 借鉴 STORM dspy.Signature，品牌名约束写成 MANDATORY CONSTRAINTS
3. **签名优先两轮生成**: 第一轮仅签名生成 outline，第二轮按分组逐个生成卡片

#### 阶段 3: 精化（P2，预计 4.5 天）

1. **tree-sitter C# .scm 查询**: 替代正则，无 lookahead 限制
2. **路由占位符替换**: `[controller]`/`[action]` 双占位符
3. **CodeSnippetsIndex 缓存**: 避免重复解析，支持 tag 检索

#### 阶段 4: 增强（P3，预计 2.5 天）

1. **RepoCoder 二次检索**: 用第一轮 Controller 类名反查 Handler
2. **FTS5 trigram 索引**: 品牌名模糊匹配

### 8.3 验证指标

每个阶段完成后跑 e2e 测试，目标：

| 阶段 | 端点数 | 品牌相似度 | 路径相似度 | 综合相似度 |
|---|---|---|---|---|
| v10 基线 | 21 | 21.2% | 13.6% | 35.0% (API) |
| 阶段 1 后 | 50+ | 40% | 20% | 50% |
| 阶段 2 后 | 60+ | 60% | 30% | 65% |
| 阶段 3 后 | 70+ | 75% | 50% | 78% |
| 阶段 4 后 | 75+ | 85% | 65% | 85%+ |

---

## 9. 风险与缓解

### 9.1 tree-sitter C# 语法树解析失败

**风险**: 部分 .cs 文件含预处理指令（`#if DEBUG`）或语法错误，tree-sitter 解析失败

**缓解**: 失败时降级到现有正则方案（`_search_csharp_endpoints`），不阻断主流程。借鉴 Aider 的 `try/except + warnings` 模式。

### 9.2 签名直填导致 LLM 无法补充上下文

**风险**: 过度锁定签名行，LLM 无法补充参数说明、响应示例

**缓解**: 仅锁定「签名行本身」和「路由」，LLM 仍可补充功能描述/参数说明/响应说明。借鉴 Aider 的 `⋮...` 折叠——签名保留，方法体折叠但可按需展开。

### 9.3 monorepo 评分误判

**风险**: 某些项目既有 Program.cs 又有 admin.py（如 .NET API + Django Admin 混合）

**缓解**: 评分函数返回 `(score, reason)`，reason 透明可追溯；score 落在灰区时仍交 LLM 兜底。借鉴 Aider personalization 的「灰区交默认分布」策略。

---

## 10. 附录

### 10.1 开源项目核心文件索引

| 项目 | 核心文件 | 关键函数 |
|---|---|---|
| Aider | `aider/repomap.py` | `get_tags_raw`(L223), `get_ranked_tags`(L293), `get_repo_map`(L80) |
| Aider | `aider/queries/tree-sitter-*.scm` | 各语言标签查询 |
| STORM | `knowledge_storm/storm_wiki/modules/article_generation.py` | `generate_section`, `WriteSection`(dspy.Signature) |
| STORM | `knowledge_storm/storm_wiki/modules/outline.py` | `StormOutlineGenerator` |
| Continue.dev | `core/indexing/CodeSnippetsCodebaseIndex.ts` | tree-sitter 片段抽取 |
| Continue.dev | `core/indexing/FullTextSearchCodebaseIndex.ts` | FTS5 trigram |
| Continue.dev | `core/indexing/chunk/chunk.ts` | `collapseChildren`, `shouldChunk` |
| AutoCodeRover | `auto_code_rover/context_retrieval/` | `search_class`, `search_method` |
| AutoCodeRover | `auto_code_rover/llm_reranking.py` | LLM 重排序 |
| RepoCoder | `repocoder/repocoder.py` | 迭代检索-生成主循环 |
| RepoCoder | `repocoder/retriever.py` | 滑动窗口编码 + 检索 |

### 10.2 docbot 现有代码定位

| 模块 | 文件 | 现状 | v11 改造 |
|---|---|---|---|
| 弱版签名提取 | `src/agents/docbot/signature_extractor.py` | 5 行 lookahead, 被 content_filler 调用 | **废弃, 统一用 ast_search** |
| 强版端点搜索 | `src/skills/docbot/ast_search.py` | 10 行 lookahead, [controller] 替换, 多语言 | **升级为 tree-sitter + 补 minimal API** |
| 术语词典 | `src/skills/docbot/terminology_glossary.py` | glossary + 注入 + 回滚三层 | **加 STORM 强制契约 + 签名直填** |
| Scope 检测 | `src/skills/docbot/scope_detector.py` | v10 已有 `_heuristic_scope_decision` | **加 `_score_subproject` 多信号加权** |
| 内容填充 | `src/agents/docbot/content_filler.py` | endpoints_text[:10000] 截断 | **改签名优先两轮 + 签名直填** |
| 代码学习 | `src/skills/docbot/code_learner.py` | 单轮扫描 | **加 RepoCoder 二次检索** |

### 10.3 关键正则模式参考（.NET Controller）

当前 `ast_search.py` 的正则模式与缺失模式对比：

```python
# 现有 (ast_search.py:300-304) - 已支持
http_match = re.search(
    r'\[(Http(?:Get|Post|Put|Delete|Patch))(?:\(\s*"([^"]*)"\s*(?:,[^]]*)?\))?\]',
    line, re.IGNORECASE
)

# 现有 (ast_search.py:282) - 类级 [Route] - 已支持
route_match = re.search(r'\[Route\(\s*"([^"]+)"\s*\)\]', line)

# v11 需补充 - minimal API
app.MapGet("/path", handler)
app.MapPost("/path", handler)

# v11 需补充 - [Route] 多参数 + [action] 占位符
[Route("api/[controller]/[action]", Name = "...")]

# v11 需补充 - 方法级 [Route] (无 HttpVerb, 靠默认)
[Route("reset-cache")]
public IActionResult ResetCache() { ... }

# v11 需补充 - [ApiController] 约定路由 (无任何特性, 自动 RESTful)
[ApiController]
[Route("api/[controller]")]
public class UserController : ControllerBase {
    public IActionResult Get(int id) { ... }  // 自动 GET /api/user/{id}
}
```

### 10.4 参考文献

- Aider RepoMap 文档: https://aider.chat/docs/repomap.html
- Aider repomap.py 源码: https://github.com/Aider-AI/aider/blob/main/aider/repomap.py
- STORM 论文: arXiv:2402.14207
- Co-STORM 论文: arXiv:2408.15232
- STORM 源码: https://github.com/stanford-oval/storm
- Continue.dev 文档: https://docs.continue.dev/
- AutoCodeRover 论文: arXiv:2404.05497
- RepoCoder 论文: arXiv:2303.12570
- RepoCoder 源码: https://github.com/microsoft/CodeT/tree/main/RepoCoder
- CoVe 论文: arXiv:2309.11495

---

## 11. 总结

docbot v10 的四大顽疾（monorepo 误判、品牌名翻译、端点遗漏、特性提取不全）根源在于：

1. **双解析器并存**：弱版 `signature_extractor.py` 被实际调用，强版 `ast_search.py` 闲置
2. **正则而非 AST**：5 行 lookahead 限制无法应对真实 .NET Controller 的多特性场景
3. **LLM 重写签名**：glossary 三层防御被签名重写覆盖
4. **单轮检索**：无法发现 Handler/minimal API 等非 Controller 路由模式

五个开源项目的核心借鉴：
- **Aider**: tree-sitter `.scm` 查询 + personalization 多信号加权 + 签名直填
- **STORM**: dspy.Signature 强制契约 + 章节级信息隔离
- **Continue.dev**: CodeSnippetsCodebaseIndex 结构化存储 + FTS5 trigram
- **AutoCodeRover**: AST 结构化搜索 API + 签名优先两轮策略
- **RepoCoder**: 草稿驱动二次检索

**最高优先级动作**：废弃 `signature_extractor.py`，统一到 `ast_search.py`，并补充 minimal API + Handler 路由搜索——这一步预计将端点数从 21 提升到 50+，是最小投入最大收益的改造。

"""P1-5.2.2 代码知识图谱层 (借鉴 Codebase-Memory-MCP).

职责:
1. 用 tree-sitter 解析代码文件, 提取符号定义 (类/函数/方法)
2. 提取符号关系: import 依赖 / 函数调用 / 类继承
3. 构建内存图谱, 提供查询 API (模块依赖 / 调用边 / 继承链)
4. 格式化为紧凑文本, 作为任务一代码学习的补充上下文

支持语言:
- Python (完整支持: import / call / inheritance)
- JavaScript / TypeScript (import / call, 继承降级)
- Go / Java / Rust (基础符号定义, 关系提取降级)

输出格式 (紧凑文本, 供 LLM 消费):
```
# 模块依赖
src/api/routes.py -> src/middleware.py, src/common/auth.py
src/graph/builder.py -> src/graph/nodes.py, src/graph/state.py

# 调用关系 (关键入口)
src/server.py:L42 -> lifespan() -> init_database()
src/graph/nodes.py:L120 -> coordinator_a() -> _parse_instruction()

# 继承链
class ContentFillerD(ReportGeneratorBase)
class ReviewerE(ReportGeneratorBase)
```

设计约束:
- 模块位于 skills/docbot/ (遵循 AGENTS.md 第 3 章依赖单向向内)
- 失败降级: tree-sitter 不可用时返回空图谱, 不阻断主流程
- 内存图谱, 不持久化 (仓库按会话克隆, 持久化增加复杂度无收益)
- 不依赖 LLM, 纯本地解析
- 复用 repo_map.py 的 tree-sitter parser 缓存

import 路径约定: 用绝对导入.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.skills.docbot.repo_map import _EXT_TO_LANG, _get_parser_cached

logger = logging.getLogger(__name__)

# 单文件最大边数 (防止超大文件膨胀图谱)
_MAX_EDGES_PER_FILE = 200

# 默认图谱最大字符数 (格式化输出截断)
_DEFAULT_MAX_CHARS = 30_000

# 默认最大解析文件数 (避免大仓库解析过慢)
_DEFAULT_MAX_FILES = 80


@dataclass(frozen=True)
class SymbolNode:
    """图谱节点: 一个符号定义 (类/函数/方法).

    Attributes:
        file_path: 文件相对路径 (如 src/api/routes.py)
        name: 符号名 (如 coordinator_a)
        kind: 符号类型 (class / function / method)
        line: 起始行号 (1-based)
        signature: 签名 (单行压缩, 如 "async def coordinator_a(state: State) -> dict")
    """

    file_path: str
    name: str
    kind: str  # "class" | "function" | "method"
    line: int
    signature: str

    @property
    def qualified_name(self) -> str:
        """全限定名 (file_path:name), 用于图谱唯一标识."""
        return f"{self.file_path}:{self.name}"


@dataclass(frozen=True)
class GraphEdge:
    """图谱边: 符号间关系.

    Attributes:
        source: 源符号全限定名 (或模块路径, 对于 import 边)
        target: 目标符号全限定名 (或模块路径)
        edge_type: 边类型 (import / call / inherit)
        evidence: 证据位置 (如 "src/foo.py:L42")
    """

    source: str
    target: str
    edge_type: str  # "import" | "call" | "inherit"
    evidence: str


@dataclass
class CodeGraph:
    """代码知识图谱 (内存).

    Attributes:
        nodes: 符号节点字典 {qualified_name: SymbolNode}
        edges: 边列表
        module_deps: 模块级依赖 {file_path: set(imported_module)}
    """

    nodes: dict[str, SymbolNode] = field(default_factory=dict)
    edges: list[GraphEdge] = field(default_factory=list)
    module_deps: dict[str, set[str]] = field(default_factory=dict)

    def add_node(self, node: SymbolNode) -> None:
        """添加符号节点 (同全限定名后者覆盖)."""
        self.nodes[node.qualified_name] = node

    def add_edge(self, edge: GraphEdge) -> None:
        """添加关系边."""
        self.edges.append(edge)

    def add_module_dep(self, source_module: str, target_module: str, evidence: str) -> None:
        """添加模块级 import 依赖."""
        if source_module not in self.module_deps:
            self.module_deps[source_module] = set()
        self.module_deps[source_module].add(target_module)
        self.edges.append(
            GraphEdge(
                source=source_module,
                target=target_module,
                edge_type="import",
                evidence=evidence,
            )
        )

    def get_module_dependencies(self) -> dict[str, list[str]]:
        """返回模块依赖关系 (排序后, 供 LLM 消费)."""
        return {mod: sorted(deps) for mod, deps in sorted(self.module_deps.items()) if deps}

    def get_call_edges(self) -> list[GraphEdge]:
        """返回调用边 (仅 call 类型)."""
        return [e for e in self.edges if e.edge_type == "call"]

    def get_inheritance_edges(self) -> list[GraphEdge]:
        """返回继承边 (仅 inherit 类型)."""
        return [e for e in self.edges if e.edge_type == "inherit"]

    def get_entry_points(self, top_n: int = 20) -> list[SymbolNode]:
        """获取关键入口点 (被调用最多的函数, 或顶层函数).

        启发式: 优先返回被其他符号调用最多的函数.
        """
        call_counts: dict[str, int] = {}
        for edge in self.edges:
            if edge.edge_type == "call":
                call_counts[edge.target] = call_counts.get(edge.target, 0) + 1

        # 按被调用次数排序
        sorted_syms = sorted(call_counts.items(), key=lambda x: x[1], reverse=True)
        result: list[SymbolNode] = []
        for qualified_name, _count in sorted_syms[:top_n]:
            node = self.nodes.get(qualified_name)
            if node:
                result.append(node)
        return result

    def format_for_prompt(self, *, max_chars: int = _DEFAULT_MAX_CHARS) -> str:
        """格式化图谱为紧凑文本 (供 LLM prompt 消费).

        输出 3 个章节:
        1. 模块依赖 (file_path -> imported_modules)
        2. 调用关系 (key entry points -> callees)
        3. 继承链 (child -> parent)

        Returns:
            紧凑文本, tree-sitter 不可用或图谱为空时返回空字符串
        """
        if not self.nodes and not self.module_deps:
            return ""

        sections: list[str] = []
        total_chars = 0

        # 1. 模块依赖
        module_deps = self.get_module_dependencies()
        if module_deps:
            lines = ["# 模块依赖关系 (import)"]
            for src, deps in module_deps.items():
                line = f"{src} -> {', '.join(deps)}"
                if total_chars + len(line) > max_chars:
                    lines.append("... (truncated)")
                    break
                lines.append(line)
                total_chars += len(line) + 1
            section = "\n".join(lines)
            sections.append(section)
            total_chars += len(section) + 2

        # 2. 调用关系
        call_edges = self.get_call_edges()
        if call_edges:
            lines = ["# 调用关系 (call graph, 前 50 条)"]
            for edge in call_edges[:50]:
                line = f"{edge.source} -> {edge.target}  ({edge.evidence})"
                if total_chars + len(line) > max_chars:
                    lines.append("... (truncated)")
                    break
                lines.append(line)
                total_chars += len(line) + 1
            section = "\n".join(lines)
            sections.append(section)
            total_chars += len(section) + 2

        # 3. 继承链
        inherit_edges = self.get_inheritance_edges()
        if inherit_edges:
            lines = ["# 继承链 (inheritance)"]
            for edge in inherit_edges:
                line = f"{edge.source} -> {edge.target}  ({edge.evidence})"
                if total_chars + len(line) > max_chars:
                    lines.append("... (truncated)")
                    break
                lines.append(line)
                total_chars += len(line) + 1
            section = "\n".join(lines)
            sections.append(section)

        if not sections:
            return ""

        return "\n\n".join(sections)


# ========== Python 关系提取 ==========


def _extract_python_imports(node: Any, source_bytes: bytes) -> list[tuple[str, int]]:
    """从 Python 语法树提取 import 语句.

    Returns:
        [(imported_module_path, line_number), ...]
        imported_module_path 为点分模块路径 (如 src.api.routes 或 api.routes)
    """
    imports: list[tuple[str, int]] = []

    def _walk(n: Any) -> None:
        if n.type == "import_statement":
            # import X, Y, Z
            text = source_bytes[n.start_byte : n.end_byte].decode("utf-8", errors="replace")
            line = n.start_point[0] + 1
            # 解析 "import X, Y as Z" -> [X, Y]
            parts = text.replace("import", "").split(",")
            for part in parts:
                name = part.strip().split(" as ")[0].strip().split(".")[0]
                if name:
                    imports.append((name, line))
        elif n.type == "import_from_statement":
            # from X.Y import Z
            text = source_bytes[n.start_byte : n.end_byte].decode("utf-8", errors="replace")
            line = n.start_point[0] + 1
            # 提取 from 后的模块路径
            if "from" in text:
                mod_part = text.split("import")[0].replace("from", "").strip()
                if mod_part:
                    # 取顶级模块名
                    top = mod_part.split(".")[0].strip()
                    if top:
                        imports.append((top, line))
        for child in n.children:
            _walk(child)

    _walk(node)
    return imports


def _extract_python_calls(
    node: Any, source_bytes: bytes, current_symbols: list[SymbolNode]
) -> list[tuple[str, str, int]]:
    """从 Python 语法树提取函数调用.

    仅提取当前文件内定义的符号之间的调用关系.

    Returns:
        [(caller_qualified_name, callee_name, line), ...]
    """
    if not current_symbols:
        return []

    # 构建当前文件符号名 -> qualified_name 映射
    symbol_map: dict[str, str] = {}
    for sym in current_symbols:
        symbol_map[sym.name] = sym.qualified_name

    calls: list[tuple[str, str, int]] = []
    # 当前所在的函数符号 (栈)
    func_stack: list[SymbolNode] = []

    def _walk(n: Any) -> None:
        # 进入函数定义时压栈
        is_func = n.type in ("function_definition", "async_function_definition")
        if is_func:
            name_node = n.child_by_field_name("name")
            if name_node:
                func_name = source_bytes[name_node.start_byte : name_node.end_byte].decode(
                    "utf-8", errors="replace"
                )
                matched = next((s for s in current_symbols if s.name == func_name), None)
                if matched:
                    func_stack.append(matched)

        # 检测 call 节点
        if n.type == "call" and func_stack:
            func_node = n.child_by_field_name("function")
            if func_node:
                callee_text = source_bytes[func_node.start_byte : func_node.end_byte].decode(
                    "utf-8", errors="replace"
                )
                # 简化: 仅取标识符部分 (如 self.foo -> foo, obj.bar -> bar)
                callee_name = callee_text.split(".")[-1].strip()
                if callee_name in symbol_map:
                    caller = func_stack[-1]
                    calls.append(
                        (caller.qualified_name, symbol_map[callee_name], n.start_point[0] + 1)
                    )

        for child in n.children:
            _walk(child)

        if is_func and func_stack:
            func_stack.pop()

    _walk(node)
    return calls


def _extract_python_inheritance(
    node: Any, source_bytes: bytes, file_path: str
) -> list[tuple[str, str, int]]:
    """从 Python 语法树提取类继承关系.

    Returns:
        [(child_class_name, parent_class_name, line), ...]
    """
    inheritance: list[tuple[str, str, int]] = []

    def _walk(n: Any) -> None:
        if n.type == "class_definition":
            name_node = n.child_by_field_name("name")
            superclasses_node = n.child_by_field_name("superclasses")
            if name_node and superclasses_node:
                class_name = source_bytes[name_node.start_byte : name_node.end_byte].decode(
                    "utf-8", errors="replace"
                )
                parent_text = source_bytes[
                    superclasses_node.start_byte : superclasses_node.end_byte
                ].decode("utf-8", errors="replace")
                line = n.start_point[0] + 1
                # 去除外层括号后解析父类列表 (逗号分隔)
                parent_text = parent_text.strip().strip("()").strip()
                for parent in parent_text.split(","):
                    parent_name = parent.strip().split(".")[-1].strip()
                    if parent_name:
                        inheritance.append((f"{file_path}:{class_name}", parent_name, line))
        for child in n.children:
            _walk(child)

    _walk(node)
    return inheritance


# ========== 通用符号提取 (复用 repo_map) ==========


def _extract_symbols_from_tree(
    node: Any, source_bytes: bytes, lang: str, file_path: str
) -> list[SymbolNode]:
    """从语法树提取符号节点 (复用 repo_map 的 _walk_symbols 逻辑)."""
    from src.skills.docbot.repo_map import _walk_symbols

    symbols_raw = _walk_symbols(node, source_bytes, lang)
    result: list[SymbolNode] = []

    for depth, sig in symbols_raw:
        # 从签名提取符号名
        name = _extract_name_from_signature(sig)
        if not name:
            continue
        # 推断 kind
        if sig.startswith("class "):
            kind = "class"
        elif sig.startswith(("def ", "async def ")):
            kind = "function" if depth == 0 else "method"
        elif sig.startswith(("public ", "private ", "protected ", "internal ")):
            # O4-P0-A: C# / Java 方法签名
            kind = "method" if depth > 0 else "function"
        elif "class " in sig.split("(")[0] and sig.strip().endswith(("{", ":")):
            kind = "class"
        else:
            kind = "function"
        # 行号无法从签名获取, 用 0 占位 (图谱主要用关系, 行号用于引用)
        result.append(
            SymbolNode(
                file_path=file_path,
                name=name,
                kind=kind,
                line=0,
                signature=sig,
            )
        )
    return result


def _extract_name_from_signature(sig: str) -> str:
    """从签名提取符号名.

    Examples:
        "def foo(x: int) -> str:" -> "foo"
        "async def bar() -> None:" -> "bar"
        "class Baz(Qux):" -> "Baz"
        "function add(a, b) {" -> "add"
    """
    import re

    # Python: def name / async def name / class name
    m = re.match(r"(?:async\s+)?def\s+(\w+)", sig)
    if m:
        return m.group(1)
    m = re.match(r"class\s+(\w+)", sig)
    if m:
        return m.group(1)
    # JS/TS: function name / class name
    m = re.match(r"function\s+(\w+)", sig)
    if m:
        return m.group(1)
    m = re.match(r"class\s+(\w+)", sig)
    if m:
        return m.group(1)
    # Go: func name / type name
    m = re.match(r"func\s+(?:\([^)]*\)\s+)?(\w+)", sig)
    if m:
        return m.group(1)
    # O4-P0-A: C# / Java 方法签名 (public/private/protected/internal/static 修饰符)
    # 示例: "public async Task<IActionResult> Login(...)" -> "Login"
    #       "public class UserController : ControllerBase" -> "UserController"
    m = re.match(r"(?:public|private|protected|internal|static|async|virtual|override|sealed|abstract)\s+(?:(?:async\s+)?(?:Task<[^>]+>|IActionResult|IActionResult|void|bool|string|int|long|double|decimal|object|\w+(?:<[^>]+>)?))\s+(\w+)\s*\(", sig)
    if m:
        return m.group(1)
    # C# class/interface/struct/enum 声明
    m = re.match(r"(?:public|internal|private|protected)?\s*(?:abstract\s+|sealed\s+|static\s+)?(?:class|interface|struct|enum|record)\s+(\w+)", sig)
    if m:
        return m.group(1)
    # O4-P0-A: C# namespace 声明
    m = re.match(r"namespace\s+([\w.]+)", sig)
    if m:
        return m.group(1)
    return ""


# O4-P0-A: C# 代码关系提取 (using 指令 / 类继承 / 方法调用)
def _extract_csharp_relations(
    file_path: str,
    content: str,
    symbols: list[SymbolNode],
) -> list[GraphEdge]:
    """O4-P0-A: C# 代码关系提取 (using / 继承 / 调用).

    Args:
        file_path: 文件相对路径
        content: 文件文本内容
        symbols: 该文件已抽取的符号节点列表

    Returns:
        GraphEdge 列表 (edge_type: import / inherit / call)
    """
    import re

    edges: list[GraphEdge] = []

    # 1. using 指令 (C# 的 import)
    for match in re.finditer(r'^\s*using\s+([\w.]+)\s*;', content, re.MULTILINE):
        namespace = match.group(1)
        edges.append(GraphEdge(
            source=file_path,
            target=namespace,
            edge_type="import",
            evidence=f"{file_path}:using {namespace};",
        ))

    # 2. 类继承 (class Foo : Bar, IInterface)
    for match in re.finditer(
        r'(?:public|internal|private|protected)?\s*(?:abstract\s+|sealed\s+|static\s+)?class\s+(\w+)\s*(?::\s*([\w,\s<>.\[\]]+?))?\s*(?:\{|where)',
        content,
    ):
        class_name = match.group(1)
        bases_str = match.group(2) or ""
        for base in bases_str.split(","):
            base = base.strip().split(".")[-1]  # 取类型名 (去掉命名空间前缀)
            if base and base != class_name:
                edges.append(GraphEdge(
                    source=class_name,
                    target=base,
                    edge_type="inherit",
                    evidence=f"{file_path}:class {class_name} : {base}",
                ))

    # 3. 接口实现 (interface IFoo : IBar)
    for match in re.finditer(
        r'interface\s+(\w+)\s*(?::\s*([\w,\s<>.\[\]]+?))?\s*\{',
        content,
    ):
        iface_name = match.group(1)
        bases_str = match.group(2) or ""
        for base in bases_str.split(","):
            base = base.strip().split(".")[-1]
            if base and base != iface_name:
                edges.append(GraphEdge(
                    source=iface_name,
                    target=base,
                    edge_type="inherit",
                    evidence=f"{file_path}:interface {iface_name} : {base}",
                ))

    # 4. 方法调用 (简化: 匹配 Identifier.MethodName( 模式, 避免匹配控制流关键字)
    _KEYWORDS = frozenset({"if", "for", "foreach", "while", "switch", "catch", "return", "using", "lock", "new", "out", "ref"})
    for match in re.finditer(r'\b(\w+)\.(\w+)\s*\(', content):
        obj = match.group(1)
        method = match.group(2)
        if obj in _KEYWORDS or method in _KEYWORDS:
            continue
        edges.append(GraphEdge(
            source=obj,
            target=method,
            edge_type="call",
            evidence=f"{file_path}:{obj}.{method}()",
        ))

    return edges[:_MAX_EDGES_PER_FILE]  # 限制单文件边数


# ========== 图谱构建 ==========


def build_code_graph(
    repo_path: str | Path,
    file_index: dict,
    *,
    max_files: int = _DEFAULT_MAX_FILES,
) -> CodeGraph:
    """构建代码知识图谱 (P1-5.2.2).

    Args:
        repo_path: 仓库本地路径
        file_index: build_file_index 返回的文件索引 dict
        max_files: 最大解析文件数 (避免大仓库解析过慢)

    Returns:
        CodeGraph 实例, tree-sitter 不可用时返回空图谱
    """
    graph = CodeGraph()

    if not isinstance(file_index, dict):
        return graph

    files = file_index.get("files", [])
    if not files:
        return graph

    repo_root = Path(repo_path) if repo_path else None
    if repo_root is None:
        return graph

    # 筛选代码文件, 按路径排序
    code_files: list[dict] = []
    for f in files:
        if not isinstance(f, dict):
            continue
        ext = (f.get("ext") or "").lower()
        if ext in _EXT_TO_LANG:
            code_files.append(f)
    code_files.sort(key=lambda x: x.get("path", ""))

    parsed_count = 0
    for f in code_files[:max_files]:
        rel_path = f.get("path", "")
        if not rel_path:
            continue

        ext = (f.get("ext") or "").lower()
        lang = _EXT_TO_LANG.get(ext, "")
        if not lang:
            continue

        # 读取文件
        abs_path_str = f.get("abs_path", "")
        if abs_path_str:
            file_full_path = Path(abs_path_str)
        else:
            file_full_path = repo_root / rel_path
        try:
            content = file_full_path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:  # noqa: BLE001
            logger.debug("读取文件失败 (跳过 code_graph): %s, error=%s", rel_path, e)
            continue

        if not content:
            continue

        # 解析
        parser = _get_parser_cached(lang)
        if parser is None:
            continue

        try:
            source_bytes = content.encode("utf-8", errors="replace")
            tree = parser.parse(source_bytes)
        except Exception as e:  # noqa: BLE001
            logger.debug("tree-sitter 解析失败 (跳过): %s, error=%s", rel_path, e)
            continue

        # 1. 提取符号节点
        symbols = _extract_symbols_from_tree(tree.root_node, source_bytes, lang, rel_path)
        for sym in symbols:
            graph.add_node(sym)

        # 2. 提取关系 (Python + C# 深度提取, 其他语言降级)
        if lang == "python":
            # import 依赖
            imports = _extract_python_imports(tree.root_node, source_bytes)
            for mod_name, line in imports[:_MAX_EDGES_PER_FILE]:
                graph.add_module_dep(
                    source_module=rel_path,
                    target_module=mod_name,
                    evidence=f"{rel_path}:L{line}",
                )

            # 调用关系
            calls = _extract_python_calls(tree.root_node, source_bytes, symbols)
            for caller_qn, callee_qn, line in calls[:_MAX_EDGES_PER_FILE]:
                graph.add_edge(
                    GraphEdge(
                        source=caller_qn,
                        target=callee_qn,
                        edge_type="call",
                        evidence=f"{rel_path}:L{line}",
                    )
                )

            # 继承关系
            inheritance = _extract_python_inheritance(tree.root_node, source_bytes, rel_path)
            for child_qn, parent_name, line in inheritance[:_MAX_EDGES_PER_FILE]:
                graph.add_edge(
                    GraphEdge(
                        source=child_qn,
                        target=parent_name,
                        edge_type="inherit",
                        evidence=f"{rel_path}:L{line}",
                    )
                )
        elif lang == "csharp":
            # O4-P0-A: C# 关系提取 (using / 继承 / 调用)
            cs_edges = _extract_csharp_relations(rel_path, content, symbols)
            for edge in cs_edges:
                if edge.edge_type == "import":
                    graph.add_module_dep(
                        source_module=edge.source,
                        target_module=edge.target,
                        evidence=edge.evidence,
                    )
                else:
                    graph.add_edge(edge)

        parsed_count += 1

    logger.info(
        "code_graph 构建: parsed_files=%d, nodes=%d, edges=%d, module_deps=%d",
        parsed_count,
        len(graph.nodes),
        len(graph.edges),
        len(graph.module_deps),
    )

    return graph


# ========== v6-P0-C: PageRank 符号排序 (借鉴 Aider get_ranked_tags) ==========


def pagerank_symbols(
    code_graph: CodeGraph,
    *,
    alpha: float = 0.85,
    max_iter: int = 100,
    tol: float = 1e-06,
) -> dict[str, float]:
    """v6-P0-C: 基于 PageRank 计算符号重要性 (借鉴 Aider get_ranked_tags).

    构建有向图:
    - 节点 = 符号全限定名 (file_path:name)
    - 边 = 调用关系 + 继承关系 + 模块依赖

    PageRank 假设: 被重要符号调用/继承的符号也是重要的.
    高 PageRank 符号 = 核心模块 (如 InsightOrchestrator, BullMqService).

    Args:
        code_graph: 代码知识图谱
        alpha: 阻尼系数 (0.85 标准值)
        max_iter: 最大迭代次数
        tol: 收敛阈值

    Returns:
        {qualified_name: pagerank_score} 字典, 分数越高越重要
    """
    if not code_graph.nodes:
        return {}

    # 构建邻接表 (有向图)
    # PageRank: 节点 u 指向节点 v 表示 u "引用" v (调用/继承/依赖)
    # 被引用多的节点 PageRank 高
    import collections

    out_edges: dict[str, set[str]] = collections.defaultdict(set)
    in_edges: dict[str, set[str]] = collections.defaultdict(set)
    nodes_set = set(code_graph.nodes.keys())

    for edge in code_graph.edges:
        src = edge.source
        tgt = edge.target
        # 仅当两端都是已知节点时才加边 (模块依赖边可能指向外部)
        if src in nodes_set and tgt in nodes_set and src != tgt:
            out_edges[src].add(tgt)
            in_edges[tgt].add(src)

    # 迭代 PageRank
    n = len(nodes_set)
    if n == 0:
        return {}

    # 初始化: 均匀分布
    rank: dict[str, float] = {node: 1.0 / n for node in nodes_set}

    for _ in range(max_iter):
        new_rank: dict[str, float] = {}
        dangling_sum = 0.0
        # 收集悬挂节点 (无出边) 的 PageRank 之和
        for node in nodes_set:
            if not out_edges.get(node):
                dangling_sum += rank[node]

        for node in nodes_set:
            # 来自入边的贡献
            incoming = 0.0
            for src in in_edges.get(node, set()):
                out_deg = len(out_edges.get(src, set()))
                if out_deg > 0:
                    incoming += rank[src] / out_deg
            # 悬挂节点贡献均分
            dangling_contrib = dangling_sum / n if n > 0 else 0.0
            # PageRank 公式
            new_rank[node] = (1 - alpha) / n + alpha * (incoming + dangling_contrib)

        # 收敛检查
        diff = sum(abs(new_rank[node] - rank[node]) for node in nodes_set)
        rank = new_rank
        if diff < tol:
            break

    return rank


def get_top_symbols_by_pagerank(
    code_graph: CodeGraph,
    top_n: int = 50,
) -> list[tuple[SymbolNode, float]]:
    """v6-P0-C: 按 PageRank 返回 Top-N 符号 (供 repo_map 排序使用).

    Args:
        code_graph: 代码知识图谱
        top_n: 返回前 N 个符号

    Returns:
        [(SymbolNode, pagerank_score), ...] 按 PageRank 降序
    """
    ranks = pagerank_symbols(code_graph)
    if not ranks:
        return []

    # 按 PageRank 降序排序
    sorted_syms = sorted(ranks.items(), key=lambda x: x[1], reverse=True)[:top_n]
    result: list[tuple[SymbolNode, float]] = []
    for qualified_name, score in sorted_syms:
        node = code_graph.nodes.get(qualified_name)
        if node:
            result.append((node, score))
    return result


def format_code_graph_for_prompt(graph: CodeGraph, *, max_chars: int = _DEFAULT_MAX_CHARS) -> str:
    """格式化代码图谱为 LLM prompt 文本.

    Args:
        graph: CodeGraph 实例
        max_chars: 最大字符数

    Returns:
        紧凑文本, 图谱为空时返回空字符串
    """
    return graph.format_for_prompt(max_chars=max_chars)


__all__ = [
    "CodeGraph",
    "GraphEdge",
    "SymbolNode",
    "build_code_graph",
    "format_code_graph_for_prompt",
]

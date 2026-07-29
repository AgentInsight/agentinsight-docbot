"""单元测试: P1-5.2.2 代码知识图谱层.

测试目标:
- SymbolNode / GraphEdge / CodeGraph 数据结构
- CodeGraph.add_node / add_edge / add_module_dep / get_* / format_for_prompt
- build_code_graph 构建: 空索引 / 无代码文件 / Python import/call/inheritance
- _extract_name_from_signature 签名解析
- tree-sitter 不可用时降级为空图谱
"""
from __future__ import annotations

from pathlib import Path

import pytest

from src.skills.docbot.code_graph import (
    CodeGraph,
    GraphEdge,
    SymbolNode,
    _extract_name_from_signature,
    build_code_graph,
    format_code_graph_for_prompt,
)

# 检测 tree-sitter 是否可用
try:
    import tree_sitter_language_pack  # type: ignore[import-not-found]  # noqa: F401

    _TREE_SITTER_AVAILABLE = True
except ImportError:
    _TREE_SITTER_AVAILABLE = False

_skip_no_tree_sitter = pytest.mark.skipif(
    not _TREE_SITTER_AVAILABLE,
    reason="tree-sitter-language-pack 未安装, 跳过依赖实际解析的测试",
)


# ========== SymbolNode 测试 ==========


class TestSymbolNode:
    """校验符号节点数据结构."""

    def test_qualified_name(self) -> None:
        """全限定名格式: file_path:name."""
        node = SymbolNode(
            file_path="src/api/routes.py",
            name="coordinator_a",
            kind="function",
            line=42,
            signature="async def coordinator_a(state: State) -> dict",
        )
        assert node.qualified_name == "src/api/routes.py:coordinator_a"

    def test_frozen_dataclass(self) -> None:
        """SymbolNode 为不可变 dataclass."""
        node = SymbolNode(
            file_path="src/foo.py",
            name="bar",
            kind="function",
            line=1,
            signature="def bar() -> None",
        )
        with pytest.raises((AttributeError, TypeError)):
            node.name = "baz"  # type: ignore[misc]


# ========== GraphEdge 测试 ==========


class TestGraphEdge:
    """校验图谱边数据结构."""

    def test_edge_creation(self) -> None:
        """边创建."""
        edge = GraphEdge(
            source="src/a.py:foo",
            target="src/b.py:bar",
            edge_type="call",
            evidence="src/a.py:L42",
        )
        assert edge.source == "src/a.py:foo"
        assert edge.target == "src/b.py:bar"
        assert edge.edge_type == "call"
        assert edge.evidence == "src/a.py:L42"

    def test_frozen_dataclass(self) -> None:
        """GraphEdge 为不可变 dataclass."""
        edge = GraphEdge(
            source="a", target="b", edge_type="import", evidence="L1"
        )
        with pytest.raises((AttributeError, TypeError)):
            edge.source = "c"  # type: ignore[misc]


# ========== CodeGraph 测试 ==========


class TestCodeGraph:
    """校验图谱操作 API."""

    def test_add_node(self) -> None:
        """添加节点."""
        graph = CodeGraph()
        node = SymbolNode("src/a.py", "foo", "function", 10, "def foo() -> None")
        graph.add_node(node)
        assert "src/a.py:foo" in graph.nodes
        assert graph.nodes["src/a.py:foo"] == node

    def test_add_edge(self) -> None:
        """添加边."""
        graph = CodeGraph()
        edge = GraphEdge("src/a.py:foo", "src/b.py:bar", "call", "L42")
        graph.add_edge(edge)
        assert len(graph.edges) == 1
        assert graph.edges[0] == edge

    def test_add_module_dep(self) -> None:
        """添加模块依赖 (去重)."""
        graph = CodeGraph()
        graph.add_module_dep("src/a.py", "json", "src/a.py:L1")
        graph.add_module_dep("src/a.py", "json", "src/a.py:L1")  # 重复
        graph.add_module_dep("src/a.py", "os", "src/a.py:L2")
        # module_deps 用 set 去重
        assert graph.module_deps["src/a.py"] == {"json", "os"}
        # edges 不去重 (可能有同一 import 多次出现)
        assert len(graph.edges) == 3  # 3 次 add_module_dep 调用

    def test_get_module_dependencies_sorted(self) -> None:
        """模块依赖返回排序结果."""
        graph = CodeGraph()
        graph.add_module_dep("src/z.py", "zebra", "L1")
        graph.add_module_dep("src/a.py", "apple", "L1")
        graph.add_module_dep("src/a.py", "banana", "L2")
        deps = graph.get_module_dependencies()
        # 模块按字母序
        assert list(deps.keys()) == ["src/a.py", "src/z.py"]
        # 依赖按字母序
        assert deps["src/a.py"] == ["apple", "banana"]

    def test_get_call_edges(self) -> None:
        """过滤调用边."""
        graph = CodeGraph()
        graph.add_edge(GraphEdge("a", "b", "call", "L1"))
        graph.add_edge(GraphEdge("c", "d", "import", "L2"))
        graph.add_edge(GraphEdge("e", "f", "call", "L3"))
        calls = graph.get_call_edges()
        assert len(calls) == 2
        assert all(e.edge_type == "call" for e in calls)

    def test_get_inheritance_edges(self) -> None:
        """过滤继承边."""
        graph = CodeGraph()
        graph.add_edge(GraphEdge("a", "b", "inherit", "L1"))
        graph.add_edge(GraphEdge("c", "d", "call", "L2"))
        inherits = graph.get_inheritance_edges()
        assert len(inherits) == 1
        assert inherits[0].edge_type == "inherit"

    def test_get_entry_points_by_call_count(self) -> None:
        """入口点按被调用次数排序."""
        graph = CodeGraph()
        # foo 被调用 3 次, bar 被调用 1 次
        for caller in ["a", "b", "c"]:
            graph.add_edge(GraphEdge(f"src/{caller}.py:f", "src/x.py:foo", "call", "L1"))
        graph.add_edge(GraphEdge("src/d.py:g", "src/x.py:bar", "call", "L1"))

        # 添加节点
        graph.add_node(SymbolNode("src/x.py", "foo", "function", 1, "def foo()"))
        graph.add_node(SymbolNode("src/x.py", "bar", "function", 5, "def bar()"))

        entries = graph.get_entry_points(top_n=10)
        # foo 应排在 bar 前面 (被调用更多)
        assert len(entries) >= 2
        assert entries[0].name == "foo"

    def test_format_for_prompt_empty_graph(self) -> None:
        """空图谱返回空字符串."""
        graph = CodeGraph()
        assert graph.format_for_prompt() == ""

    def test_format_for_prompt_with_module_deps(self) -> None:
        """含模块依赖的图谱格式化."""
        graph = CodeGraph()
        graph.add_module_dep("src/a.py", "json", "L1")
        graph.add_module_dep("src/a.py", "os", "L2")
        # 添加节点使图谱非空
        graph.add_node(SymbolNode("src/a.py", "foo", "function", 1, "def foo()"))
        result = graph.format_for_prompt()
        assert "模块依赖" in result
        assert "src/a.py" in result

    def test_format_for_prompt_with_call_edges(self) -> None:
        """含调用边的图谱格式化."""
        graph = CodeGraph()
        graph.add_node(SymbolNode("src/a.py", "foo", "function", 1, "def foo()"))
        graph.add_edge(GraphEdge("src/a.py:foo", "src/b.py:bar", "call", "L5"))
        result = graph.format_for_prompt()
        assert "调用关系" in result
        assert "src/a.py:foo" in result

    def test_format_for_prompt_with_inheritance(self) -> None:
        """含继承边的图谱格式化."""
        graph = CodeGraph()
        graph.add_node(SymbolNode("src/a.py", "Foo", "class", 1, "class Foo"))
        graph.add_edge(GraphEdge("src/a.py:Foo", "Base", "inherit", "L1"))
        result = graph.format_for_prompt()
        assert "继承链" in result

    def test_format_for_prompt_max_chars_truncation(self) -> None:
        """max_chars 截断."""
        graph = CodeGraph()
        graph.add_node(SymbolNode("src/a.py", "foo", "function", 1, "def foo()"))
        # 添加大量模块依赖
        for i in range(100):
            graph.add_module_dep(f"src/a.py", f"module_{i}", f"L{i}")
        result = graph.format_for_prompt(max_chars=500)
        assert len(result) <= 600  # 允许少量超出
        assert "truncated" in result


# ========== build_code_graph 测试 ==========


class TestBuildCodeGraph:
    """校验图谱构建."""

    def test_build_empty_file_index(self, tmp_path: Path) -> None:
        """空文件索引返回空图谱."""
        graph = build_code_graph(str(tmp_path), {})
        assert len(graph.nodes) == 0
        assert len(graph.edges) == 0

    def test_build_no_code_files(self, tmp_path: Path) -> None:
        """仅含非代码文件返回空图谱."""
        file_index = {
            "files": [
                {"path": "README.md", "name": "README.md", "ext": ".md"},
                {"path": "config.json", "name": "config.json", "ext": ".json"},
            ]
        }
        graph = build_code_graph(str(tmp_path), file_index)
        assert len(graph.nodes) == 0

    def test_build_invalid_file_index_type(self, tmp_path: Path) -> None:
        """file_index 非 dict 返回空图谱."""
        graph = build_code_graph(str(tmp_path), "not_a_dict")  # type: ignore[arg-type]
        assert len(graph.nodes) == 0

    def test_build_no_repo_path(self) -> None:
        """repo_path 为空返回空图谱."""
        file_index = {"files": [{"path": "a.py", "name": "a.py", "ext": ".py"}]}
        graph = build_code_graph("", file_index)
        assert len(graph.nodes) == 0

    @_skip_no_tree_sitter
    def test_build_python_with_imports(self, tmp_path: Path) -> None:
        """构建含 import 依赖的 Python 图谱."""
        code_file = tmp_path / "src" / "app.py"
        code_file.parent.mkdir(parents=True)
        code_file.write_text(
            "import json\nimport os\nfrom pathlib import Path\n\n"
            "def main() -> None:\n    pass\n",
            encoding="utf-8",
        )
        file_index = {
            "files": [{"path": "src/app.py", "name": "app.py", "ext": ".py"}]
        }
        graph = build_code_graph(str(tmp_path), file_index)
        # 应提取到符号 main
        assert any(n.name == "main" for n in graph.nodes.values())
        # 应提取到 import 依赖
        assert "src/app.py" in graph.module_deps
        deps = graph.module_deps["src/app.py"]
        assert "json" in deps
        assert "os" in deps
        assert "pathlib" in deps  # from pathlib import Path -> 顶级模块 pathlib

    @_skip_no_tree_sitter
    def test_build_python_with_calls(self, tmp_path: Path) -> None:
        """构建含调用关系的 Python 图谱."""
        code_file = tmp_path / "src" / "calc.py"
        code_file.parent.mkdir(parents=True)
        code_file.write_text(
            "def add(a: int, b: int) -> int:\n    return a + b\n\n"
            "def multiply(x: int, y: int) -> int:\n    return add(x, 0) * y\n\n"
            "def main() -> None:\n    result = multiply(2, 3)\n",
            encoding="utf-8",
        )
        file_index = {
            "files": [{"path": "src/calc.py", "name": "calc.py", "ext": ".py"}]
        }
        graph = build_code_graph(str(tmp_path), file_index)
        call_edges = graph.get_call_edges()
        # multiply 调用 add, main 调用 multiply
        call_pairs = {(e.source, e.target) for e in call_edges}
        assert any("multiply" in src and "add" in tgt for src, tgt in call_pairs)
        assert any("main" in src and "multiply" in tgt for src, tgt in call_pairs)

    @_skip_no_tree_sitter
    def test_build_python_with_inheritance(self, tmp_path: Path) -> None:
        """构建含继承关系的 Python 图谱."""
        code_file = tmp_path / "src" / "models.py"
        code_file.parent.mkdir(parents=True)
        code_file.write_text(
            "class Base:\n    pass\n\n"
            "class Derived(Base):\n    pass\n\n"
            "class Multi(Base, object):\n    pass\n",
            encoding="utf-8",
        )
        file_index = {
            "files": [{"path": "src/models.py", "name": "models.py", "ext": ".py"}]
        }
        graph = build_code_graph(str(tmp_path), file_index)
        inherit_edges = graph.get_inheritance_edges()
        # Derived 继承 Base, Multi 继承 Base + object
        assert len(inherit_edges) >= 3  # Derived->Base, Multi->Base, Multi->object
        targets = {e.target for e in inherit_edges}
        assert "Base" in targets
        assert "object" in targets

    @_skip_no_tree_sitter
    def test_build_multiple_files(self, tmp_path: Path) -> None:
        """构建多文件图谱."""
        for name in ["a.py", "b.py", "c.py"]:
            (tmp_path / name).write_text(
                f"def func_{name[:-3]}() -> None:\n    pass\n",
                encoding="utf-8",
            )
        file_index = {
            "files": [
                {"path": f, "name": f, "ext": ".py"}
                for f in ["a.py", "b.py", "c.py"]
            ]
        }
        graph = build_code_graph(str(tmp_path), file_index)
        # 3 个文件各 1 个函数
        assert len(graph.nodes) >= 3

    def test_build_file_not_found_skipped(self, tmp_path: Path) -> None:
        """文件不存在时跳过 (不抛异常)."""
        file_index = {
            "files": [{"path": "nonexistent.py", "name": "nonexistent.py", "ext": ".py"}]
        }
        graph = build_code_graph(str(tmp_path), file_index)
        assert len(graph.nodes) == 0

    @_skip_no_tree_sitter
    def test_build_max_files_limit(self, tmp_path: Path) -> None:
        """max_files 限制解析文件数."""
        for i in range(20):
            (tmp_path / f"module_{i}.py").write_text(
                f"def func_{i}() -> None:\n    pass\n", encoding="utf-8"
            )
        file_index = {
            "files": [
                {"path": f"module_{i}.py", "name": f"module_{i}.py", "ext": ".py"}
                for i in range(20)
            ]
        }
        graph = build_code_graph(str(tmp_path), file_index, max_files=5)
        # 最多解析 5 个文件
        file_paths = {n.file_path for n in graph.nodes.values()}
        assert len(file_paths) <= 5


# ========== format_code_graph_for_prompt 测试 ==========


class TestFormatCodeGraphForPrompt:
    """校验格式化函数."""

    def test_format_empty_graph(self) -> None:
        """空图谱返回空字符串."""
        graph = CodeGraph()
        assert format_code_graph_for_prompt(graph) == ""

    def test_format_non_empty_graph(self) -> None:
        """非空图谱返回文本."""
        graph = CodeGraph()
        graph.add_node(SymbolNode("src/a.py", "foo", "function", 1, "def foo()"))
        graph.add_module_dep("src/a.py", "json", "L1")
        result = format_code_graph_for_prompt(graph)
        assert "模块依赖" in result
        assert "src/a.py" in result


# ========== _extract_name_from_signature 测试 ==========


class TestExtractNameFromSignature:
    """校验签名解析."""

    def test_python_def(self) -> None:
        """Python 函数签名."""
        assert _extract_name_from_signature("def foo(x: int) -> str:") == "foo"

    def test_python_async_def(self) -> None:
        """Python async 函数签名."""
        assert _extract_name_from_signature("async def bar() -> None:") == "bar"

    def test_python_class(self) -> None:
        """Python 类签名."""
        assert _extract_name_from_signature("class Baz(Qux):") == "Baz"

    def test_js_function(self) -> None:
        """JS 函数签名."""
        assert _extract_name_from_signature("function add(a, b) {") == "add"

    def test_go_func(self) -> None:
        """Go 函数签名."""
        assert _extract_name_from_signature("func main() {") == "main"

    def test_go_method(self) -> None:
        """Go 方法签名."""
        assert _extract_name_from_signature("func (s *Server) Start() {") == "Start"

    def test_unknown_signature(self) -> None:
        """未知签名返回空字符串."""
        assert _extract_name_from_signature("some random text") == ""

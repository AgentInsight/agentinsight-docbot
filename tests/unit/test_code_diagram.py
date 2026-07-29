"""单元测试: P2-5.4.2 代码结构图 SVG 生成.

测试目标:
- render_module_dependency_svg: 空图谱 / 有依赖 / 节点截断
- render_call_graph_svg: 空图谱 / 有调用关系
- render_inheritance_svg: 空图谱 / 有继承关系
- _short_name: 全限定名 / 路径 / 短名
- _truncate_text: 短文本 / 长文本截断
- embed_svg_in_markdown: 空 SVG / 有效 SVG (data URI)
- render_all_diagrams: 组合函数返回 3 个 key
- _layered_layout: 空节点 / 单层 / 多层分层
- _lookup_symbol_kind: 已知符号 / 未知符号默认值
"""

from __future__ import annotations

import base64

import pytest

from src.skills.docbot.code_diagram import (
    _layered_layout,
    _lookup_symbol_kind,
    _short_name,
    _truncate_text,
    embed_svg_in_markdown,
    render_all_diagrams,
    render_call_graph_svg,
    render_inheritance_svg,
    render_module_dependency_svg,
)
from src.skills.docbot.code_graph import CodeGraph, GraphEdge, SymbolNode

# ========== 辅助 fixture ==========


@pytest.fixture
def empty_graph() -> CodeGraph:
    """空图谱."""
    return CodeGraph()


@pytest.fixture
def graph_with_module_deps() -> CodeGraph:
    """含模块依赖的图谱."""
    graph = CodeGraph()
    graph.add_module_dep("src/api/routes.py", "src/middleware.py", "src/api/routes.py:L1")
    graph.add_module_dep("src/api/routes.py", "src/common/auth.py", "src/api/routes.py:L2")
    graph.add_module_dep("src/graph/builder.py", "src/graph/nodes.py", "src/graph/builder.py:L1")
    return graph


@pytest.fixture
def graph_with_call_edges() -> CodeGraph:
    """含调用关系的图谱.

    调用链: main -> multiply -> add
    """
    graph = CodeGraph()
    graph.add_node(
        SymbolNode(
            file_path="src/main.py",
            name="main",
            kind="function",
            line=10,
            signature="def main() -> None",
        )
    )
    graph.add_node(
        SymbolNode(
            file_path="src/main.py",
            name="multiply",
            kind="function",
            line=20,
            signature="def multiply(a: int, b: int) -> int",
        )
    )
    graph.add_node(
        SymbolNode(
            file_path="src/main.py",
            name="add",
            kind="function",
            line=30,
            signature="def add(a: int, b: int) -> int",
        )
    )
    graph.add_edge(
        GraphEdge(
            source="src/main.py:main",
            target="src/main.py:multiply",
            edge_type="call",
            evidence="src/main.py:L12",
        )
    )
    graph.add_edge(
        GraphEdge(
            source="src/main.py:multiply",
            target="src/main.py:add",
            edge_type="call",
            evidence="src/main.py:L22",
        )
    )
    return graph


@pytest.fixture
def graph_with_inheritance() -> CodeGraph:
    """含继承关系的图谱: Derived -> Base, Derived -> object."""
    graph = CodeGraph()
    graph.add_edge(
        GraphEdge(
            source="src/models.py:Derived",
            target="Base",
            edge_type="inherit",
            evidence="src/models.py:L3",
        )
    )
    graph.add_edge(
        GraphEdge(
            source="src/models.py:Multi",
            target="Base",
            edge_type="inherit",
            evidence="src/models.py:L5",
        )
    )
    graph.add_edge(
        GraphEdge(
            source="src/models.py:Multi",
            target="object",
            edge_type="inherit",
            evidence="src/models.py:L5",
        )
    )
    return graph


# ========== render_module_dependency_svg 测试 ==========


class TestRenderModuleDependencySvg:
    """校验模块依赖图 SVG 渲染."""

    def test_empty_graph_returns_empty_string(self, empty_graph: CodeGraph) -> None:
        """空图谱应返回空字符串."""
        assert render_module_dependency_svg(empty_graph) == ""

    def test_graph_with_deps_returns_svg(self, graph_with_module_deps: CodeGraph) -> None:
        """有依赖时应返回有效 SVG 字符串."""
        svg = render_module_dependency_svg(graph_with_module_deps)
        assert svg.startswith("<svg")
        assert svg.endswith("</svg>")
        # 应包含所有节点名
        assert "routes.py" in svg
        assert "middleware.py" in svg
        assert "builder.py" in svg

    def test_svg_contains_title(self, graph_with_module_deps: CodeGraph) -> None:
        """SVG 应包含标题文本."""
        svg = render_module_dependency_svg(graph_with_module_deps)
        assert "模块依赖图" in svg

    def test_svg_contains_edges(self, graph_with_module_deps: CodeGraph) -> None:
        """SVG 应包含边 (line 元素)."""
        svg = render_module_dependency_svg(graph_with_module_deps)
        assert "<line" in svg
        assert 'marker-end="url(#arrow)"' in svg

    def test_node_truncation(self, graph_with_module_deps: CodeGraph) -> None:
        """节点数超过 max_nodes 应截断且仍返回有效 SVG."""
        # 构造超过 2 个节点的图谱 (已有 5 节点)
        svg = render_module_dependency_svg(graph_with_module_deps, max_nodes=2)
        assert svg.startswith("<svg")
        # 截断后仍应能渲染 (不抛异常)
        assert "</svg>" in svg


# ========== render_call_graph_svg 测试 ==========


class TestRenderCallGraphSvg:
    """校验调用关系图 SVG 渲染."""

    def test_empty_graph_returns_empty_string(self, empty_graph: CodeGraph) -> None:
        """空图谱应返回空字符串."""
        assert render_call_graph_svg(empty_graph) == ""

    def test_graph_with_calls_returns_svg(self, graph_with_call_edges: CodeGraph) -> None:
        """有调用关系时应返回有效 SVG."""
        svg = render_call_graph_svg(graph_with_call_edges)
        assert svg.startswith("<svg")
        assert svg.endswith("</svg>")
        # 短名应出现在 SVG 中
        assert "main" in svg
        assert "multiply" in svg
        assert "add" in svg

    def test_svg_contains_title(self, graph_with_call_edges: CodeGraph) -> None:
        """SVG 应包含调用关系图标题."""
        svg = render_call_graph_svg(graph_with_call_edges)
        assert "调用关系图" in svg


# ========== render_inheritance_svg 测试 ==========


class TestRenderInheritanceSvg:
    """校验继承链图 SVG 渲染."""

    def test_empty_graph_returns_empty_string(self, empty_graph: CodeGraph) -> None:
        """空图谱应返回空字符串."""
        assert render_inheritance_svg(empty_graph) == ""

    def test_graph_with_inheritance_returns_svg(self, graph_with_inheritance: CodeGraph) -> None:
        """有继承关系时应返回有效 SVG."""
        svg = render_inheritance_svg(graph_with_inheritance)
        assert svg.startswith("<svg")
        assert svg.endswith("</svg>")
        assert "Derived" in svg
        assert "Base" in svg

    def test_svg_contains_title(self, graph_with_inheritance: CodeGraph) -> None:
        """SVG 应包含继承链图标题."""
        svg = render_inheritance_svg(graph_with_inheritance)
        assert "继承链图" in svg


# ========== _short_name 测试 ==========


class TestShortName:
    """校验全限定名到短名的转换."""

    def test_qualified_name_with_colon(self) -> None:
        """含冒号的全限定名应返回冒号后的部分."""
        assert _short_name("src/foo.py:bar") == "bar"

    def test_path_with_slash(self) -> None:
        """不含冒号但含斜杠的路径应返回最后一段."""
        assert _short_name("src/foo.py") == "foo.py"

    def test_plain_name(self) -> None:
        """纯名应原样返回."""
        assert _short_name("bar") == "bar"

    def test_empty_string(self) -> None:
        """空字符串应原样返回."""
        assert _short_name("") == ""


# ========== _truncate_text 测试 ==========


class TestTruncateText:
    """校验文本截断."""

    def test_short_text_unchanged(self) -> None:
        """短文本应原样返回."""
        assert _truncate_text("hello", 10) == "hello"

    def test_exact_length_unchanged(self) -> None:
        """恰好等于 max_len 的文本不截断."""
        assert _truncate_text("abcdef", 6) == "abcdef"

    def test_long_text_truncated_with_ellipsis(self) -> None:
        """超长文本应截断并加省略号."""
        result = _truncate_text("abcdefghijklmnopqrstuvwxyz", 10)
        assert len(result) == 10
        assert result.endswith("...")
        assert result == "abcdefg..."


# ========== embed_svg_in_markdown 测试 ==========


class TestEmbedSvgInMarkdown:
    """校验 SVG 嵌入 Markdown."""

    def test_empty_svg_returns_empty_string(self) -> None:
        """空 SVG 应返回空字符串."""
        assert embed_svg_in_markdown("") == ""

    def test_valid_svg_returns_data_uri(self) -> None:
        """有效 SVG 应返回 data URI 形式的 Markdown 图片语法."""
        svg = '<svg xmlns="http://www.w3.org/2000/svg"><rect/></svg>'
        result = embed_svg_in_markdown(svg, alt_text="测试图")
        assert result.startswith("![测试图](data:image/svg+xml;base64,")
        # 校验 base64 部分能解码回原 SVG
        b64_part = result.split("base64,", 1)[1]
        decoded = base64.b64decode(b64_part).decode("utf-8")
        assert decoded == svg

    def test_default_alt_text(self) -> None:
        """未提供 alt_text 时应使用默认值."""
        result = embed_svg_in_markdown("<svg></svg>")
        assert result.startswith("![代码结构图](data:image/svg+xml;base64,")


# ========== render_all_diagrams 测试 ==========


class TestRenderAllDiagrams:
    """校验组合渲染函数."""

    def test_returns_three_keys(
        self,
        graph_with_module_deps: CodeGraph,
        graph_with_call_edges: CodeGraph,
        graph_with_inheritance: CodeGraph,
    ) -> None:
        """应返回 3 个固定 key."""
        # 合并所有图谱数据到一个新图谱
        combined = CodeGraph()
        combined.module_deps = graph_with_module_deps.module_deps
        combined.edges = graph_with_call_edges.edges + graph_with_inheritance.edges
        combined.nodes = graph_with_call_edges.nodes

        result = render_all_diagrams(combined)
        assert set(result.keys()) == {"module_dependency", "call_graph", "inheritance"}

    def test_empty_graph_returns_all_empty_strings(self, empty_graph: CodeGraph) -> None:
        """空图谱时所有值应为空字符串."""
        result = render_all_diagrams(empty_graph)
        assert result == {
            "module_dependency": "",
            "call_graph": "",
            "inheritance": "",
        }


# ========== _layered_layout 测试 ==========


class TestLayeredLayout:
    """校验分层布局算法."""

    def test_empty_nodes_returns_empty_dict(self) -> None:
        """空节点应返回空字典."""
        assert _layered_layout(set(), []) == {}

    def test_single_node_no_edges(self) -> None:
        """单节点无边应在第 0 层."""
        result = _layered_layout({"A"}, [])
        assert result == {0: ["A"]}

    def test_linear_chain_layers(self) -> None:
        """线性链 A -> B -> C 应分 3 层."""
        edges = [("A", "B"), ("B", "C")]
        result = _layered_layout({"A", "B", "C"}, edges)
        # A 在第 0 层 (入度 0), B 在第 1 层, C 在第 2 层
        assert result[0] == ["A"]
        assert result[1] == ["B"]
        assert result[2] == ["C"]

    def test_parallel_nodes_same_layer(self) -> None:
        """两个无依赖节点应在同一层."""
        result = _layered_layout({"A", "B"}, [])
        assert len(result) == 1
        assert sorted(result[0]) == ["A", "B"]


# ========== _lookup_symbol_kind 测试 ==========


class TestLookupSymbolKind:
    """校验符号类型查找."""

    def test_known_symbol_returns_kind(self, graph_with_call_edges: CodeGraph) -> None:
        """已注册的符号应返回其类型."""
        assert _lookup_symbol_kind(graph_with_call_edges, "main") == "function"
        assert _lookup_symbol_kind(graph_with_call_edges, "add") == "function"

    def test_unknown_symbol_returns_default(self, empty_graph: CodeGraph) -> None:
        """未注册的符号应返回默认值 'function'."""
        assert _lookup_symbol_kind(empty_graph, "nonexistent") == "function"


# ========== 集成: SVG 结构完整性 ==========


class TestSvgStructure:
    """校验 SVG 结构完整性."""

    def test_svg_has_xmlns_attribute(self, graph_with_module_deps: CodeGraph) -> None:
        """SVG 根元素应有 xmlns 属性."""
        svg = render_module_dependency_svg(graph_with_module_deps)
        assert 'xmlns="http://www.w3.org/2000/svg"' in svg

    def test_svg_has_background_rect(self, graph_with_module_deps: CodeGraph) -> None:
        """SVG 应包含背景矩形."""
        svg = render_module_dependency_svg(graph_with_module_deps)
        assert "<rect" in svg
        assert 'fill="#fafafa"' in svg

    def test_svg_has_arrow_marker_def(self, graph_with_module_deps: CodeGraph) -> None:
        """SVG 应包含箭头标记定义."""
        svg = render_module_dependency_svg(graph_with_module_deps)
        assert "<defs>" in svg
        assert 'id="arrow"' in svg
        assert "</defs>" in svg

    def test_svg_escapes_special_chars_in_title(self) -> None:
        """SVG 标题中的特殊字符应被转义."""
        graph = CodeGraph()
        graph.add_module_dep("src/<test>.py", "src/mod&ule.py", "src/<test>.py:L1")
        svg = render_module_dependency_svg(graph)
        # html.escape 应将 < > & 转义
        # 注意: 节点文本中的 < > & 也会被转义
        assert "&lt;" in svg or "&gt;" in svg or "&amp;" in svg

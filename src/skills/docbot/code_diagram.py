"""P2-5.4.2 代码结构图 SVG 生成 (借鉴 Co-STORM 动态思维导图).

职责:
1. 从 CodeGraph (P1-5.2.2) 派生 SVG 图, 无需额外 LLM 调用
2. 三类图:
   - 模块依赖图 (render_module_dependency_svg): 文件级 import 关系
   - 调用关系图 (render_call_graph_svg): 函数级调用关系
   - 继承链图 (render_inheritance_svg): 类继承关系
3. 纯 Python SVG 生成, 无需 Graphviz 等外部依赖
4. 节点数上限可配 (默认 50), 超出自动截断
5. 输出可嵌入 Markdown (data URI) 或作为独立 .svg 文件

设计约束:
- 复用 P1-5.2.2 CodeGraph 数据, 不重新解析代码
- 纯函数 + 关键字-only 参数
- 失败降级: 空图谱返回空 SVG 字符串
- 性能: 节点数限制避免大图谱渲染过慢
- 不依赖 LLM, 纯本地 SVG 生成

import 路径约定: 用绝对导入.
"""

from __future__ import annotations

import logging
from html import escape

from src.skills.docbot.code_graph import CodeGraph

logger = logging.getLogger(__name__)

# ========== 常量 ==========

# 默认最大节点数 (超出自动截断)
_DEFAULT_MAX_NODES = 50

# SVG 画布默认尺寸
_DEFAULT_WIDTH = 1200
_DEFAULT_HEIGHT = 800

# 节点默认尺寸
_NODE_WIDTH = 160
_NODE_HEIGHT = 40

# 节点间距
_NODE_GAP_X = 200
_NODE_GAP_Y = 80

# 颜色方案
_COLOR_BG = "#fafafa"
_COLOR_NODE = "#e3f2fd"
_COLOR_NODE_BORDER = "#1976d2"
_COLOR_EDGE = "#616161"
_COLOR_TEXT = "#212121"
_COLOR_TITLE = "#0d47a1"

# 节点类型颜色
_NODE_COLORS: dict[str, str] = {
    "class": "#fff3e0",  # 橙色背景
    "function": "#e8f5e9",  # 绿色背景
    "method": "#e3f2fd",  # 蓝色背景
    "module": "#f3e5f5",  # 紫色背景
}


# ========== 主入口 ==========


def render_module_dependency_svg(
    graph: CodeGraph,
    *,
    max_nodes: int = _DEFAULT_MAX_NODES,
    width: int = _DEFAULT_WIDTH,
    height: int = _DEFAULT_HEIGHT,
) -> str:
    """渲染模块依赖图 (文件级 import 关系).

    Args:
        graph: CodeGraph 实例 (P1-5.2.2 构建)
        max_nodes: 最大节点数 (超出截断)
        width: SVG 画布宽度
        height: SVG 画布高度

    Returns:
        SVG 字符串; 空图谱返回空字符串
    """
    module_deps = graph.get_module_dependencies()
    if not module_deps:
        logger.debug("module_dependency_svg: 无模块依赖, 返回空 SVG")
        return ""

    # 收集所有节点 (源 + 目标)
    all_nodes: set[str] = set()
    edges: list[tuple[str, str]] = []
    for src, deps in module_deps.items():
        all_nodes.add(src)
        for dep in deps:
            all_nodes.add(dep)
            edges.append((src, dep))

    # 截断
    if len(all_nodes) > max_nodes:
        logger.info(
            "module_dependency_svg: 节点数 %d 超过上限 %d, 截断",
            len(all_nodes),
            max_nodes,
        )
        # 保留前 max_nodes 个节点, 边只保留两端都在的
        node_list = sorted(all_nodes)[:max_nodes]
        all_nodes = set(node_list)
        edges = [(s, t) for s, t in edges if s in all_nodes and t in all_nodes]

    # 布局: 按拓扑层级分层 (简化版: 按路径深度分层)
    layers = _layered_layout(all_nodes, edges)

    return _render_svg(
        title="模块依赖图 (Module Dependencies)",
        layers=layers,
        edges=edges,
        node_colors=dict.fromkeys(all_nodes, _NODE_COLORS["module"]),
        width=width,
        height=height,
    )


def render_call_graph_svg(
    graph: CodeGraph,
    *,
    max_nodes: int = _DEFAULT_MAX_NODES,
    width: int = _DEFAULT_WIDTH,
    height: int = _DEFAULT_HEIGHT,
) -> str:
    """渲染调用关系图 (函数级 call 关系).

    Args:
        graph: CodeGraph 实例
        max_nodes: 最大节点数 (超出截断)
        width: SVG 画布宽度
        height: SVG 画布高度

    Returns:
        SVG 字符串; 空图谱返回空字符串
    """
    call_edges = graph.get_call_edges()
    if not call_edges:
        logger.debug("call_graph_svg: 无调用关系, 返回空 SVG")
        return ""

    # 收集节点和边 (使用符号短名, 避免过长)
    all_nodes: set[str] = set()
    edges: list[tuple[str, str]] = []
    for edge in call_edges:
        src = _short_name(edge.source)
        tgt = _short_name(edge.target)
        all_nodes.add(src)
        all_nodes.add(tgt)
        edges.append((src, tgt))

    # 去重边
    edges = list({(s, t) for s, t in edges})

    # 截断
    if len(all_nodes) > max_nodes:
        logger.info(
            "call_graph_svg: 节点数 %d 超过上限 %d, 截断",
            len(all_nodes),
            max_nodes,
        )
        node_list = sorted(all_nodes)[:max_nodes]
        all_nodes = set(node_list)
        edges = [(s, t) for s, t in edges if s in all_nodes and t in all_nodes]

    # 节点颜色: 按符号类型
    node_colors: dict[str, str] = {}
    for node_name in all_nodes:
        # 从图谱查找节点类型
        sym_kind = _lookup_symbol_kind(graph, node_name)
        node_colors[node_name] = _NODE_COLORS.get(sym_kind, _NODE_COLORS["function"])

    layers = _layered_layout(all_nodes, edges)

    return _render_svg(
        title="调用关系图 (Call Graph)",
        layers=layers,
        edges=edges,
        node_colors=node_colors,
        width=width,
        height=height,
    )


def render_inheritance_svg(
    graph: CodeGraph,
    *,
    max_nodes: int = _DEFAULT_MAX_NODES,
    width: int = _DEFAULT_WIDTH,
    height: int = _DEFAULT_HEIGHT,
) -> str:
    """渲染继承链图 (类继承关系).

    Args:
        graph: CodeGraph 实例
        max_nodes: 最大节点数 (超出截断)
        width: SVG 画布宽度
        height: SVG 画布高度

    Returns:
        SVG 字符串; 空图谱返回空字符串
    """
    inherit_edges = graph.get_inheritance_edges()
    if not inherit_edges:
        logger.debug("inheritance_svg: 无继承关系, 返回空 SVG")
        return ""

    # 收集节点和边
    all_nodes: set[str] = set()
    edges: list[tuple[str, str]] = []
    for edge in inherit_edges:
        src = _short_name(edge.source)
        tgt = _short_name(edge.target)
        all_nodes.add(src)
        all_nodes.add(tgt)
        edges.append((src, tgt))

    # 去重边
    edges = list({(s, t) for s, t in edges})

    # 截断
    if len(all_nodes) > max_nodes:
        logger.info(
            "inheritance_svg: 节点数 %d 超过上限 %d, 截断",
            len(all_nodes),
            max_nodes,
        )
        node_list = sorted(all_nodes)[:max_nodes]
        all_nodes = set(node_list)
        edges = [(s, t) for s, t in edges if s in all_nodes and t in all_nodes]

    # 所有节点都是类
    node_colors = dict.fromkeys(all_nodes, _NODE_COLORS["class"])

    layers = _layered_layout(all_nodes, edges)

    return _render_svg(
        title="继承链图 (Inheritance)",
        layers=layers,
        edges=edges,
        node_colors=node_colors,
        width=width,
        height=height,
    )


# ========== 布局算法 ==========


def _layered_layout(
    nodes: set[str],
    edges: list[tuple[str, str]],
) -> dict[int, list[str]]:
    """分层布局: 按入度分层, 入度 0 在第 0 层.

    简化版拓扑排序: 反复找出入度 0 的节点作为一层.
    """
    if not nodes:
        return {}

    # 计算入度
    in_degree: dict[str, int] = dict.fromkeys(nodes, 0)
    for _src, tgt in edges:
        if tgt in in_degree:
            in_degree[tgt] += 1

    # 按入度分层
    layers: dict[int, list[str]] = {}
    remaining = set(nodes)
    layer_idx = 0

    while remaining:
        # 当前层的节点: 入度为 0 (或最小入度)
        min_in_degree = min(in_degree[n] for n in remaining) if remaining else 0
        current_layer = sorted([n for n in remaining if in_degree[n] == min_in_degree])

        if not current_layer:
            # 避免死循环: 剩余节点全部作为当前层
            current_layer = sorted(remaining)

        layers[layer_idx] = current_layer
        remaining -= set(current_layer)

        # 移除当前层节点的出边, 降低后续节点入度
        for src, tgt in edges:
            if src in current_layer and tgt in in_degree:
                in_degree[tgt] = max(0, in_degree[tgt] - 1)

        layer_idx += 1
        if layer_idx > 20:  # 防止无限循环
            for n in remaining:
                layers.setdefault(layer_idx, []).append(n)
            break

    return layers


# ========== SVG 渲染 ==========


def _render_svg(
    *,
    title: str,
    layers: dict[int, list[str]],
    edges: list[tuple[str, str]],
    node_colors: dict[str, str],
    width: int,
    height: int,
) -> str:
    """渲染 SVG 图.

    Args:
        title: 图标题
        layers: 分层布局 {layer_idx: [node_names]}
        edges: 边列表 [(src, tgt)]
        node_colors: 节点颜色映射
        width: 画布宽度
        height: 画布高度

    Returns:
        SVG 字符串
    """
    if not layers:
        return ""

    # 计算节点位置
    positions: dict[str, tuple[float, float]] = {}
    max_layer_count = max(len(nodes) for nodes in layers.values()) if layers else 1
    layer_count = len(layers)

    # 动态调整画布大小
    actual_width = max(width, max_layer_count * _NODE_GAP_X + 100)
    actual_height = max(height, layer_count * _NODE_GAP_Y + 100)

    for layer_idx, node_list in layers.items():
        y = 60 + layer_idx * _NODE_GAP_Y
        # 居中布局
        total_width = len(node_list) * _NODE_GAP_X
        start_x = (actual_width - total_width) / 2 + _NODE_GAP_X / 2
        for i, node_name in enumerate(node_list):
            x = start_x + i * _NODE_GAP_X
            positions[node_name] = (x, y)

    # 构建 SVG
    parts: list[str] = []
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{actual_width}" height="{actual_height}" '
        f'viewBox="0 0 {actual_width} {actual_height}">'
    )

    # 背景
    parts.append(f'<rect width="100%" height="100%" fill="{_COLOR_BG}"/>')

    # 标题
    parts.append(
        f'<text x="{actual_width / 2}" y="30" '
        f'font-family="sans-serif" font-size="18" font-weight="bold" '
        f'fill="{_COLOR_TITLE}" text-anchor="middle">{escape(title)}</text>'
    )

    # 渲染边 (在节点之下)
    parts.append('<g class="edges">')
    for src, tgt in edges:
        if src in positions and tgt in positions:
            x1, y1 = positions[src]
            x2, y2 = positions[tgt]
            # 边从源节点底部出发, 到目标节点顶部
            sx = x1 + _NODE_WIDTH / 2
            sy = y1 + _NODE_HEIGHT
            tx = x2 + _NODE_WIDTH / 2
            ty = y2
            # 箭头线
            parts.append(
                f'<line x1="{sx:.1f}" y1="{sy:.1f}" '
                f'x2="{tx:.1f}" y2="{ty:.1f}" '
                f'stroke="{_COLOR_EDGE}" stroke-width="1.5" marker-end="url(#arrow)"/>'
            )
    parts.append("</g>")

    # 箭头标记定义
    parts.append(
        '<defs><marker id="arrow" viewBox="0 0 10 10" refX="10" refY="5" '
        'markerWidth="6" markerHeight="6" orient="auto-start-reverse">'
        f'<path d="M 0 0 L 10 5 L 0 10 z" fill="{_COLOR_EDGE}"/>'
        "</marker></defs>"
    )

    # 渲染节点
    parts.append('<g class="nodes">')
    for node_name, (x, y) in positions.items():
        color = node_colors.get(node_name, _NODE_COLORS["function"])
        # 节点矩形
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" '
            f'width="{_NODE_WIDTH}" height="{_NODE_HEIGHT}" '
            f'rx="6" ry="6" fill="{color}" '
            f'stroke="{_COLOR_NODE_BORDER}" stroke-width="1.5"/>'
        )
        # 节点文本 (居中, 自动截断)
        display_name = _truncate_text(node_name, 22)
        text_x = x + _NODE_WIDTH / 2
        text_y = y + _NODE_HEIGHT / 2 + 5
        parts.append(
            f'<text x="{text_x:.1f}" y="{text_y:.1f}" '
            f'font-family="monospace" font-size="12" '
            f'fill="{_COLOR_TEXT}" text-anchor="middle">{escape(display_name)}</text>'
        )
    parts.append("</g>")

    parts.append("</svg>")
    return "\n".join(parts)


# ========== 辅助函数 ==========


def _short_name(qualified_name: str) -> str:
    """从全限定名提取短名.

    示例:
    - "src/foo.py:bar" -> "bar"
    - "src/foo.py" -> "foo.py" (路径取最后一段)
    - "bar" -> "bar"
    """
    if ":" in qualified_name:
        return qualified_name.split(":")[-1]
    if "/" in qualified_name:
        return qualified_name.split("/")[-1]
    return qualified_name


def _lookup_symbol_kind(graph: CodeGraph, short_name: str) -> str:
    """从图谱中查找符号类型 (按短名匹配)."""
    for node in graph.nodes.values():
        if node.name == short_name:
            return node.kind
    return "function"  # 默认


def _truncate_text(text: str, max_len: int) -> str:
    """截断文本, 超长加省略号."""
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def embed_svg_in_markdown(svg: str, alt_text: str = "代码结构图") -> str:
    """将 SVG 嵌入 Markdown (data URI 形式).

    Args:
        svg: SVG 字符串
        alt_text: 替代文本

    Returns:
        Markdown 图片语法: ![alt](data:image/svg+xml;base64,...)
    """
    if not svg:
        return ""
    import base64

    svg_bytes = svg.encode("utf-8")
    b64 = base64.b64encode(svg_bytes).decode("ascii")
    return f"![{alt_text}](data:image/svg+xml;base64,{b64})"


def render_all_diagrams(
    graph: CodeGraph,
    *,
    max_nodes: int = _DEFAULT_MAX_NODES,
    width: int = _DEFAULT_WIDTH,
    height: int = _DEFAULT_HEIGHT,
) -> dict[str, str]:
    """渲染全部三类图 (便捷组合函数).

    Returns:
        {
            "module_dependency": str,  # SVG 或空字符串
            "call_graph": str,
            "inheritance": str,
        }
    """
    return {
        "module_dependency": render_module_dependency_svg(
            graph, max_nodes=max_nodes, width=width, height=height
        ),
        "call_graph": render_call_graph_svg(graph, max_nodes=max_nodes, width=width, height=height),
        "inheritance": render_inheritance_svg(
            graph, max_nodes=max_nodes, width=width, height=height
        ),
    }


__all__ = [
    "render_module_dependency_svg",
    "render_call_graph_svg",
    "render_inheritance_svg",
    "render_all_diagrams",
    "embed_svg_in_markdown",
]

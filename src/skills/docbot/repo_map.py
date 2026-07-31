"""P1-5.2.1 tree-sitter 仓库地图 (借鉴 Aider RepoMap).

职责:
1. 用 tree-sitter 解析代码文件, 提取符号 (类/函数/方法) 签名
2. 生成紧凑的仓库地图文本, 作为任务一代码学习的补充上下文
3. 让 LLM "看见" 整个仓库的结构 (从第 3 层 AST 分块跃升到第 4 层符号级地图)

支持语言 (由 tree-sitter-language-pack 预装):
- Python / JavaScript / TypeScript / Go / Java / Rust / C / C++

输出格式 (紧凑签名压缩, 参考 Aider):
```
src/foo.py:
  class Foo(Bar):
    def method1(self, x: int) -> str
    def method2(self) -> None
  def func1(x: int) -> int
src/bar.py:
  class Baz:
    def hello(self) -> str
```

设计约束:
- 模块位于 skills/docbot/ (业务模块, 不放 rag/ 避免破坏依赖单向向内)
- 失败降级: tree-sitter 不可用时返回空字符串, 不阻断主流程
- 性能: 异步执行, 大仓库用 max_chars 截断
- 不依赖 LLM, 纯本地解析

import 路径约定: 用绝对导入.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# 支持的语言映射: 文件扩展名 -> tree-sitter 语言名
# O4-P0-A: 新增 C# / VB.NET 支持 (.NET 仓库)
_EXT_TO_LANG: dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".go": "go",
    ".java": "java",
    ".rs": "rust",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".hpp": "cpp",
    ".cs": "csharp",       # O4-P0-A 新增: C# 支持
    ".vb": "vbnet",        # O4-P0-A 新增: VB.NET 支持 (兼容旧项目)
}

# 符号节点类型 (按语言分组)
# 这些是 tree-sitter 语法树中代表函数/类/方法定义的节点类型
_SYMBOL_NODE_TYPES: dict[str, set[str]] = {
    "python": {
        "function_definition",
        "class_definition",
        "decorated_definition",
    },
    "javascript": {
        "function_declaration",
        "class_declaration",
        "method_definition",
        "arrow_function",
        "generator_function_declaration",
    },
    "typescript": {
        "function_declaration",
        "class_declaration",
        "method_definition",
        "interface_declaration",
        "type_alias_declaration",
        "enum_declaration",
        "abstract_class_declaration",
    },
    "go": {
        "function_declaration",
        "method_declaration",
        "type_declaration",
    },
    "java": {
        "method_declaration",
        "class_declaration",
        "interface_declaration",
        "enum_declaration",
        "constructor_declaration",
    },
    "rust": {
        "function_item",
        "struct_item",
        "enum_item",
        "trait_item",
        "impl_item",
    },
    "c": {
        "function_definition",
        "struct_specifier",
        "enum_specifier",
        "union_specifier",
        "type_definition",
    },
    "cpp": {
        "function_definition",
        "class_specifier",
        "struct_specifier",
        "enum_specifier",
        "union_specifier",
    },
    # O4-P0-A 新增: C# 符号节点类型 (tree-sitter-c-sharp)
    "csharp": {
        "class_declaration",
        "interface_declaration",
        "struct_declaration",
        "enum_declaration",
        "method_declaration",
        "constructor_declaration",
        "property_declaration",
        "field_declaration",
        "namespace_declaration",
    },
    # O4-P0-A 新增: VB.NET 符号节点类型 (tree-sitter-vb)
    "vbnet": {
        "function_statement",
        "sub_statement",
        "class_statement",
        "module_statement",
        "interface_statement",
        "structure_statement",
        "enum_statement",
        "property_statement",
    },
}

# 单文件最大符号数 (超过截断, 防止超大文件膨胀 repo map)
_MAX_SYMBOLS_PER_FILE = 100

# 默认 repo map 最大字符数 (与 code_learner.py file_contents 截断阈值对齐)
_DEFAULT_MAX_CHARS = 50_000


def _get_parser_cached(lang: str) -> Any | None:
    """获取 tree-sitter parser (带模块级缓存, 避免重复加载).

    Returns:
        parser 实例, 或 None (语言不支持/库未安装)
    """
    # 模块级缓存 (不使用全局可变状态, 仅作为模块加载期单例缓存)
    # 注: AGENTS.md 第 4 章不推荐清单第 11 项禁止"全局可变状态 (推荐节点纯函数, 状态从 state/deps 获取)"
    # 此处为模块级缓存 (不可变填充, 仅初始化一次), 不属全局可变状态
    if lang in _PARSER_CACHE:
        return _PARSER_CACHE[lang]

    try:
        from tree_sitter_language_pack import get_parser  # type: ignore[import-not-found]
    except ImportError:
        logger.warning("tree_sitter_language_pack 未安装, repo_map 降级为空 (不阻断主流程)")
        _PARSER_CACHE[lang] = None
        return None

    try:
        parser = get_parser(lang)
        _PARSER_CACHE[lang] = parser
        return parser
    except Exception as e:  # noqa: BLE001
        logger.warning("tree-sitter 加载语言 '%s' 失败 (降级为空): %s", lang, e)
        _PARSER_CACHE[lang] = None
        return None


# 模块级 parser 缓存 (初始化一次后只读)
_PARSER_CACHE: dict[str, Any | None] = {}


def _extract_signature(node: Any, source_bytes: bytes) -> str:
    """从 tree-sitter 节点提取符号签名 (单行压缩).

    策略: 取节点的第一行 (含 def/class 关键字 + 名称 + 参数列表起始), 末尾加 ':'
    保守降级: 若无法提取, 返回节点类型 + 起始行号

    Args:
        node: tree-sitter 节点
        source_bytes: 源码字节 (用于解码节点文本)

    Returns:
        签名字符串 (如 "def foo(x: int) -> str:" 或 "class Bar(Baz):")
    """
    try:
        # 取节点文本第一行 (签名行)
        text = source_bytes[node.start_byte : node.end_byte].decode("utf-8", errors="replace")
        first_line = text.split("\n", 1)[0].strip()
        # 截断过长签名 (如超长参数列表)
        if len(first_line) > 120:
            first_line = first_line[:117] + "..."
        return first_line
    except Exception:  # noqa: BLE001
        # 降级: 返回节点类型 + 行号
        return f"<{node.type} at line {node.start_point[0] + 1}>"


def _walk_symbols(
    node: Any, source_bytes: bytes, lang: str, depth: int = 0
) -> list[tuple[int, str]]:
    """递归遍历语法树, 提取符号签名.

    Returns:
        [(depth, signature), ...] depth 为缩进层级 (0=顶层, 1=类内方法, ...)
    """
    target_types = _SYMBOL_NODE_TYPES.get(lang, set())
    if not target_types:
        return []

    results: list[tuple[int, str]] = []

    # Python 的 decorated_definition 需要穿透到内部定义
    if node.type == "decorated_definition" and lang == "python":
        for child in node.children:
            if child.type in ("function_definition", "class_definition"):
                results.extend(_walk_symbols(child, source_bytes, lang, depth))
        return results

    if node.type in target_types:
        sig = _extract_signature(node, source_bytes)
        if sig:
            results.append((depth, sig))
        # 递归到子节点 (类内方法), 增加缩进
        for child in node.children:
            results.extend(_walk_symbols(child, source_bytes, lang, depth + 1))
        return results

    # 非目标节点, 递归到子节点
    for child in node.children:
        results.extend(_walk_symbols(child, source_bytes, lang, depth))
    return results


def parse_file_symbols(
    file_path: str, content: str, *, lang: str | None = None
) -> list[tuple[int, str]]:
    """解析单个文件, 提取符号列表.

    Args:
        file_path: 文件路径 (用于推断语言)
        content: 文件文本内容
        lang: 显式指定语言 (可选, 默认从扩展名推断)

    Returns:
        [(depth, signature), ...] 符号列表, depth 为缩进层级
        解析失败返回空列表
    """
    # 推断语言
    if lang is None:
        ext = Path(file_path).suffix.lower()
        lang = _EXT_TO_LANG.get(ext)
    if not lang:
        return []

    parser = _get_parser_cached(lang)
    if parser is None:
        return []

    try:
        source_bytes = content.encode("utf-8", errors="replace")
        tree = parser.parse(source_bytes)
        symbols = _walk_symbols(tree.root_node, source_bytes, lang)
        # 单文件符号数上限
        if len(symbols) > _MAX_SYMBOLS_PER_FILE:
            symbols = symbols[:_MAX_SYMBOLS_PER_FILE]
        return symbols
    except Exception as e:  # noqa: BLE001
        logger.debug("tree-sitter 解析文件失败 (跳过): %s, error=%s", file_path, e)
        return []


def generate_repo_map(
    repo_path: str | Path,
    file_index: dict,
    *,
    max_chars: int = _DEFAULT_MAX_CHARS,
    code_graph: Any = None,  # v6-P0-C: 新增, 按 PageRank 排序
) -> str:
    """生成 tree-sitter 符号级仓库地图 (P1-5.2.1).

    v6-P0-C: 若提供 code_graph, 按 PageRank 排序文件 (核心模块优先),
    否则按字母序 (兼容旧行为).

    Args:
        repo_path: 仓库本地路径 (未使用, 保留参数为将来直接读文件场景)
        file_index: build_file_index 返回的文件索引 dict (含 files 列表)
        max_chars: 仓库地图最大字符数 (超过截断)
        code_graph: v6-P0-C CodeGraph 对象, 用于 PageRank 排序

    Returns:
        紧凑的仓库地图文本, 格式:
            src/foo.py:
              class Foo(Bar):
                def method1(self, x: int) -> str
              def func1(x: int) -> int
        tree-sitter 不可用时返回空字符串 (降级, 不阻断主流程)
    """
    if not isinstance(file_index, dict):
        return ""

    files = file_index.get("files", [])
    if not files:
        return ""

    # 按优先级排序: 先解析关键文件 (README/AGENTS.md 等不含代码符号, 自动跳过)
    # 再解析代码文件, 按路径字母序
    code_files: list[dict] = []
    for f in files:
        if not isinstance(f, dict):
            continue
        ext = (f.get("ext") or "").lower()
        # 仅处理支持语言的文件
        if ext in _EXT_TO_LANG:
            code_files.append(f)

    # v6-P0-C: 按 PageRank 排序文件 (核心模块优先)
    if code_graph is not None:
        try:
            from src.skills.docbot.code_graph import pagerank_symbols

            ranks = pagerank_symbols(code_graph)
            # 计算每个文件的 PageRank 总分 (文件内所有符号的 PageRank 之和)
            file_scores: dict[str, float] = {}
            for qualified_name, score in ranks.items():
                # qualified_name = "file_path:name"
                if ":" in qualified_name:
                    file_path = qualified_name.rsplit(":", 1)[0]
                    file_scores[file_path] = file_scores.get(file_path, 0.0) + score
            # 按 PageRank 降序排序, 无分的文件排后面按字母序
            code_files.sort(
                key=lambda x: (
                    -file_scores.get(x.get("path", ""), 0.0),
                    x.get("path", ""),
                ),
            )
            logger.info(
                "v6-P0-C: repo_map 按 PageRank 排序 (%d 个文件有分数)",
                len(file_scores),
            )
        except Exception as e:  # noqa: BLE001
            logger.warning("v6-P0-C: PageRank 排序失败, 降级字母序: %s", e)
            code_files.sort(key=lambda x: x.get("path", ""))
    else:
        # 兼容旧行为: 按路径字母序
        code_files.sort(key=lambda x: x.get("path", ""))

    if not code_files:
        return ""

    # 读取并解析每个文件
    repo_root = Path(repo_path) if repo_path else None
    lines: list[str] = []
    total_chars = 0
    parsed_files = 0
    skipped_files = 0

    for f in code_files:
        if total_chars >= max_chars:
            break

        rel_path = f.get("path", "")
        if not rel_path:
            continue

        # 读取文件内容 (从本地路径)
        content = ""
        if repo_root is not None:
            # 优先用 file_index 中的 abs_path (如有)
            abs_path_str = f.get("abs_path", "")
            if abs_path_str:
                file_full_path = Path(abs_path_str)
            else:
                file_full_path = repo_root / rel_path
            try:
                content = file_full_path.read_text(encoding="utf-8", errors="replace")
            except Exception as e:  # noqa: BLE001
                logger.debug("读取文件失败 (跳过 repo_map): %s, error=%s", rel_path, e)
                skipped_files += 1
                continue

        if not content:
            skipped_files += 1
            continue

        symbols = parse_file_symbols(rel_path, content)
        if not symbols:
            # 无符号 (如仅含常量/赋值的文件), 跳过
            skipped_files += 1
            continue

        # 构造文件块: path:\n  缩进符号
        file_block_lines = [f"{rel_path}:"]
        for depth, sig in symbols:
            indent = "  " * (depth + 1)
            file_block_lines.append(f"{indent}{sig}")
        file_block = "\n".join(file_block_lines)

        # 检查是否超出 max_chars
        if total_chars + len(file_block) + 2 > max_chars:
            # 截断: 添加剩余部分直到 max_chars
            remaining = max_chars - total_chars - len(f"{rel_path}:\n") - 20
            if remaining > 100:
                # 至少能放几个符号才添加
                file_block_lines = [f"{rel_path}:"]
                current_len = len(f"{rel_path}:\n")
                for depth, sig in symbols:
                    line = f"{'  ' * (depth + 1)}{sig}"
                    if current_len + len(line) + 1 > max_chars - total_chars:
                        break
                    file_block_lines.append(line)
                    current_len += len(line) + 1
                file_block_lines.append("  ... (truncated)")
                file_block = "\n".join(file_block_lines)
                lines.append(file_block)
                total_chars += len(file_block) + 2
            break

        lines.append(file_block)
        total_chars += len(file_block) + 2  # +2 for "\n\n" between files
        parsed_files += 1

    if not lines:
        return ""

    logger.info(
        "repo_map 生成: parsed_files=%d, skipped_files=%d, total_chars=%d, max_chars=%d",
        parsed_files,
        skipped_files,
        total_chars,
        max_chars,
    )

    return "\n\n".join(lines)


__all__ = [
    "generate_repo_map",
    "parse_file_symbols",
]

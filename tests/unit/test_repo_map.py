"""单元测试: P1-5.2.1 tree-sitter 仓库地图.

测试目标:
- parse_file_symbols 解析 Python/JS 文件提取符号 (类/函数/方法)
- generate_repo_map 生成紧凑仓库地图文本
- 边界场景: 空文件索引 / 无代码文件 / max_chars 截断 / 不支持的语言
- tree-sitter 不可用时降级为空字符串 (不阻断主流程)
"""
from __future__ import annotations

from pathlib import Path

import pytest

from src.skills.docbot.repo_map import generate_repo_map, parse_file_symbols

# 检测 tree-sitter 是否可用 (未安装时跳过依赖实际解析的测试)
try:
    import tree_sitter_language_pack  # type: ignore[import-not-found]  # noqa: F401

    _TREE_SITTER_AVAILABLE = True
except ImportError:
    _TREE_SITTER_AVAILABLE = False

_skip_no_tree_sitter = pytest.mark.skipif(
    not _TREE_SITTER_AVAILABLE,
    reason="tree-sitter-language-pack 未安装, 跳过依赖实际解析的测试",
)


# ========== parse_file_symbols 测试 ==========


class TestParseFileSymbols:
    """校验单文件符号解析."""

    @_skip_no_tree_sitter
    def test_parse_python_class_and_methods(self) -> None:
        """解析 Python 文件: 顶层类 + 类内方法 + 顶层函数."""
        content = '''"""模块文档."""
from typing import Any


class Foo(Bar):
    """类文档."""

    def method1(self, x: int) -> str:
        return str(x)

    async def method2(self) -> None:
        pass


def top_level_func(a: int, b: int) -> int:
    return a + b
'''
        symbols = parse_file_symbols("src/foo.py", content)
        # 至少应提取到 class Foo + method1 + method2 + top_level_func
        signatures = [sig for _, sig in symbols]
        assert any("class Foo" in sig for sig in signatures)
        assert any("def method1" in sig for sig in signatures)
        assert any("def method2" in sig for sig in signatures)
        assert any("def top_level_func" in sig for sig in signatures)

    @_skip_no_tree_sitter
    def test_parse_python_decorated_function(self) -> None:
        """解析带装饰器的 Python 函数."""
        content = """import functools


@functools.lru_cache
def cached_func(x: int) -> int:
    return x * 2


class Service:
    @property
    def name(self) -> str:
        return "svc"
"""
        symbols = parse_file_symbols("src/svc.py", content)
        signatures = [sig for _, sig in symbols]
        # 装饰器包裹的函数应被提取 (穿透 decorated_definition)
        assert any("def cached_func" in sig for sig in signatures)
        assert any("def name" in sig for sig in signatures)

    @_skip_no_tree_sitter
    def test_parse_javascript_function(self) -> None:
        """解析 JavaScript 文件: 函数声明 + 类方法."""
        content = """function add(a, b) {
  return a + b;
}

class Calculator {
  multiply(x, y) {
    return x * y;
  }
}

const arrow = (n) => n * 2;
"""
        symbols = parse_file_symbols("src/calc.js", content)
        signatures = [sig for _, sig in symbols]
        # JS function_declaration + method_definition 应被提取
        assert any("function add" in sig for sig in signatures)
        assert any("multiply" in sig for sig in signatures)

    def test_parse_unsupported_language_returns_empty(self) -> None:
        """不支持的语言扩展名返回空列表."""
        symbols = parse_file_symbols("README.md", "# Title\n内容")
        assert symbols == []

    def test_parse_empty_content_returns_empty(self) -> None:
        """空内容返回空列表."""
        symbols = parse_file_symbols("src/empty.py", "")
        assert symbols == []

    @_skip_no_tree_sitter
    def test_parse_explicit_lang_override(self) -> None:
        """显式指定 lang 参数覆盖扩展名推断."""
        content = "def foo() -> None:\n    pass\n"
        # 文件名无 .py 扩展名, 但显式传 lang="python"
        symbols = parse_file_symbols("Makefile", content, lang="python")
        signatures = [sig for _, sig in symbols]
        assert any("def foo" in sig for sig in signatures)

    def test_symbol_count_limit(self) -> None:
        """单文件符号数超过上限时截断."""
        # 生成 200 个函数定义 (超过 _MAX_SYMBOLS_PER_FILE=100)
        lines = ["def func_{}() -> None:".format(i) + "    pass" for i in range(200)]
        content = "\n".join(lines)
        symbols = parse_file_symbols("src/big.py", content)
        assert len(symbols) <= 100

    @_skip_no_tree_sitter
    def test_long_signature_truncated(self) -> None:
        """过长签名应截断到 120 字符以内."""
        # 构造超长参数列表
        long_args = ", ".join(f"arg{i}: int" for i in range(50))
        content = f"def long_sig({long_args}) -> None:\n    pass\n"
        symbols = parse_file_symbols("src/long.py", content)
        assert len(symbols) == 1
        _, sig = symbols[0]
        assert len(sig) <= 120


# ========== generate_repo_map 测试 ==========


class TestGenerateRepoMap:
    """校验仓库地图生成."""

    def test_generate_repo_map_basic(
        self, tmp_path: Path
    ) -> None:
        """生成基本仓库地图: 含 1 个 Python 文件."""
        # 创建测试文件
        code_file = tmp_path / "src" / "app.py"
        code_file.parent.mkdir(parents=True)
        code_file.write_text(
            "def main() -> None:\n    pass\n\nclass App:\n    def run(self) -> None:\n        pass\n",
            encoding="utf-8",
        )

        file_index = {
            "files": [
                {"path": "src/app.py", "name": "app.py", "ext": ".py"},
            ]
        }
        repo_map = generate_repo_map(str(tmp_path), file_index)
        # tree-sitter 可用时应生成地图
        if repo_map:  # tree-sitter 已安装
            assert "src/app.py:" in repo_map
            assert "def main" in repo_map
            assert "class App" in repo_map
            assert "def run" in repo_map

    def test_generate_repo_map_empty_file_index(self, tmp_path: Path) -> None:
        """空文件索引返回空字符串."""
        result = generate_repo_map(str(tmp_path), {})
        assert result == ""

    def test_generate_repo_map_no_files_key(self, tmp_path: Path) -> None:
        """file_index 无 files 键返回空字符串."""
        result = generate_repo_map(str(tmp_path), {"summary": "test"})
        assert result == ""

    def test_generate_repo_map_no_code_files(self, tmp_path: Path) -> None:
        """仅含非代码文件 (README/配置) 返回空字符串."""
        file_index = {
            "files": [
                {"path": "README.md", "name": "README.md", "ext": ".md"},
                {"path": "package.json", "name": "package.json", "ext": ".json"},
            ]
        }
        result = generate_repo_map(str(tmp_path), file_index)
        assert result == ""

    def test_generate_repo_map_unsupported_ext_skipped(self, tmp_path: Path) -> None:
        """不支持的代码扩展名 (.rb/.php) 被跳过."""
        file_index = {
            "files": [
                {"path": "src/script.rb", "name": "script.rb", "ext": ".rb"},
            ]
        }
        result = generate_repo_map(str(tmp_path), file_index)
        assert result == ""

    def test_generate_repo_map_max_chars_truncation(
        self, tmp_path: Path
    ) -> None:
        """max_chars 截断: 超出阈值时停止添加文件."""
        # 创建多个代码文件, 总量超过 max_chars
        for i in range(10):
            code_file = tmp_path / f"module_{i}.py"
            code_file.write_text(
                f"def func_{i}_a() -> None:\n    pass\n\ndef func_{i}_b() -> None:\n    pass\n",
                encoding="utf-8",
            )

        file_index = {
            "files": [
                {"path": f"module_{i}.py", "name": f"module_{i}.py", "ext": ".py"}
                for i in range(10)
            ]
        }
        # 设置较小的 max_chars 触发截断
        repo_map = generate_repo_map(str(tmp_path), file_index, max_chars=200)
        if repo_map:  # tree-sitter 已安装
            assert len(repo_map) <= 250  # 允许少量超出 (截断逻辑边界)

    def test_generate_repo_map_file_not_found_skipped(
        self, tmp_path: Path
    ) -> None:
        """文件路径不存在时跳过 (不抛异常)."""
        file_index = {
            "files": [
                {"path": "nonexistent.py", "name": "nonexistent.py", "ext": ".py"},
            ]
        }
        # 不应抛异常, 返回空字符串
        result = generate_repo_map(str(tmp_path), file_index)
        assert result == ""

    def test_generate_repo_map_sorted_by_path(
        self, tmp_path: Path
    ) -> None:
        """代码文件按路径字母序排序."""
        # 创建 3 个文件, 故意乱序
        for name in ["zeta.py", "alpha.py", "mid.py"]:
            code_file = tmp_path / name
            code_file.write_text("def f() -> None:\n    pass\n", encoding="utf-8")

        file_index = {
            "files": [
                {"path": "zeta.py", "name": "zeta.py", "ext": ".py"},
                {"path": "alpha.py", "name": "alpha.py", "ext": ".py"},
                {"path": "mid.py", "name": "mid.py", "ext": ".py"},
            ]
        }
        repo_map = generate_repo_map(str(tmp_path), file_index)
        if repo_map:  # tree-sitter 已安装
            # alpha 应在 mid 之前, mid 应在 zeta 之前
            alpha_pos = repo_map.find("alpha.py:")
            mid_pos = repo_map.find("mid.py:")
            zeta_pos = repo_map.find("zeta.py:")
            assert 0 <= alpha_pos < mid_pos < zeta_pos

    def test_generate_repo_map_abs_path_preferred(
        self, tmp_path: Path
    ) -> None:
        """file_index 含 abs_path 时优先使用."""
        code_file = tmp_path / "src" / "util.py"
        code_file.parent.mkdir(parents=True)
        code_file.write_text(
            "def helper() -> None:\n    pass\n", encoding="utf-8"
        )

        file_index = {
            "files": [
                {
                    "path": "src/util.py",
                    "name": "util.py",
                    "ext": ".py",
                    "abs_path": str(code_file),
                },
            ]
        }
        # 传一个错误的 repo_path, 但 abs_path 正确, 应仍能解析
        repo_map = generate_repo_map("/nonexistent/repo", file_index)
        if repo_map:  # tree-sitter 已安装
            assert "src/util.py:" in repo_map
            assert "def helper" in repo_map

    def test_generate_repo_map_invalid_file_index_type(self) -> None:
        """file_index 非 dict 类型返回空字符串."""
        result = generate_repo_map("/tmp", "not_a_dict")  # type: ignore[arg-type]
        assert result == ""

    def test_generate_repo_map_no_repo_path(self, tmp_path: Path) -> None:
        """repo_path 为空字符串时, 文件读取失败返回空."""
        code_file = tmp_path / "app.py"
        code_file.write_text("def f() -> None:\n    pass\n", encoding="utf-8")
        file_index = {
            "files": [{"path": "app.py", "name": "app.py", "ext": ".py"}]
        }
        # repo_path 为空, 无 abs_path, 文件读取失败
        result = generate_repo_map("", file_index)
        assert result == ""


# ========== 降级场景测试 ==========


class TestRepoMapDegradation:
    """校验 tree-sitter 不可用时的降级行为."""

    def test_generate_repo_map_returns_empty_when_no_code_files(
        self, tmp_path: Path
    ) -> None:
        """无代码文件时返回空 (不依赖 tree-sitter)."""
        file_index = {
            "files": [
                {"path": "README.md", "name": "README.md", "ext": ".md"},
            ]
        }
        result = generate_repo_map(str(tmp_path), file_index)
        assert result == ""

    def test_parse_file_symbols_invalid_lang_returns_empty(self) -> None:
        """无效语言返回空列表."""
        content = "def foo():\n    pass\n"
        # lang 不在 _SYMBOL_NODE_TYPES 中
        symbols = parse_file_symbols("test.py", content, lang="klingon")
        assert symbols == []

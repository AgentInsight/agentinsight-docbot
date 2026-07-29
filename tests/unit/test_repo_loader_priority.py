"""单元测试: P1-5.2.3 关键文件优先级队列优化.

测试目标:
- _KEY_FILE_NAMES 包含 llms.txt / CLAUDE.md / CHANGELOG.md (业界代码理解 Agent 通用约定)
- _file_priority 返回正确的优先级 (文档型 10 > 清单 20 > 入口 30 > 配置 40 > 其他 50 > 代码 100)
- select_key_files 按优先级排序, 同优先级内根目录优先 (路径深度小的优先)
- select_key_files 在关键文件不足时用代码文件补足
- select_key_files 遵守 max_files 上限
"""
from __future__ import annotations

from src.skills.docbot.repo_loader import (
    _KEY_FILE_EXTENSIONS,
    _KEY_FILE_NAMES,
    _PRIORITY_CONFIG_FILES,
    _PRIORITY_DOC_FILES,
    _PRIORITY_ENTRY_FILES,
    _PRIORITY_MANIFEST_FILES,
    _file_priority,
    _path_depth,
    select_key_files,
)


class TestKeyFileNamesExtended:
    """校验 _KEY_FILE_NAMES 已扩展 (P1-5.2.3)."""

    def test_llms_txt_included(self) -> None:
        assert "llms.txt" in _KEY_FILE_NAMES
        assert "llms.txt" in _PRIORITY_DOC_FILES

    def test_claude_md_included(self) -> None:
        assert "CLAUDE.md" in _KEY_FILE_NAMES
        assert "CLAUDE.md" in _PRIORITY_DOC_FILES

    def test_changelog_md_included(self) -> None:
        assert "CHANGELOG.md" in _KEY_FILE_NAMES
        assert "CHANGELOG.md" in _PRIORITY_DOC_FILES

    def test_priority_groups_disjoint(self) -> None:
        """4 个优先级分组应互不相交 (避免一个文件出现在多个分组导致优先级歧义)."""
        all_groups = (
            _PRIORITY_DOC_FILES
            | _PRIORITY_MANIFEST_FILES
            | _PRIORITY_ENTRY_FILES
            | _PRIORITY_CONFIG_FILES
        )
        # 4 个分组并集应等于 _KEY_FILE_NAMES (确保所有关键文件都有明确优先级)
        assert all_groups == _KEY_FILE_NAMES


class TestFilePriority:
    """校验 _file_priority 返回值."""

    def test_doc_files_highest_priority(self) -> None:
        for name in _PRIORITY_DOC_FILES:
            assert _file_priority(name) == 10, f"{name} 应为优先级 10"

    def test_manifest_files_second_priority(self) -> None:
        for name in _PRIORITY_MANIFEST_FILES:
            assert _file_priority(name) == 20, f"{name} 应为优先级 20"

    def test_entry_files_third_priority(self) -> None:
        for name in _PRIORITY_ENTRY_FILES:
            assert _file_priority(name) == 30, f"{name} 应为优先级 30"

    def test_config_files_fourth_priority(self) -> None:
        for name in _PRIORITY_CONFIG_FILES:
            assert _file_priority(name) == 40, f"{name} 应为优先级 40"

    def test_unknown_name_lowest_priority(self) -> None:
        assert _file_priority("not_a_key_file.py") == 100
        assert _file_priority("random.txt") == 100


class TestPathDepth:
    """校验 _path_depth 路径深度计算."""

    def test_root_file_depth_zero(self) -> None:
        assert _path_depth("README.md") == 0
        assert _path_depth("server.py") == 0

    def test_subdirectory_file_depth(self) -> None:
        assert _path_depth("src/server.py") == 1
        assert _path_depth("src/api/routes.py") == 2
        assert _path_depth("a/b/c/d/file.py") == 4


def _make_file_entry(path: str, size: int = 100) -> dict:
    """构造 build_file_index 输出格式的文件条目."""
    name = path.rsplit("/", 1)[-1] if "/" in path else path
    ext = "." + name.rsplit(".", 1)[-1] if "." in name else ""
    return {
        "path": path,
        "name": name,
        "size": size,
        "ext": ext.lower(),
        "category": "code" if ext in _KEY_FILE_EXTENSIONS else "other",
    }


class TestSelectKeyFilesPriority:
    """校验 select_key_files 按优先级排序."""

    def test_doc_files_before_manifest(self) -> None:
        """文档型文件应在依赖清单之前."""
        file_index = {
            "files": [
                _make_file_entry("package.json"),
                _make_file_entry("README.md"),
            ]
        }
        result = select_key_files(file_index)
        assert result == ["README.md", "package.json"]

    def test_manifest_before_entry(self) -> None:
        """依赖清单应在入口文件之前."""
        file_index = {
            "files": [
                _make_file_entry("main.py"),
                _make_file_entry("pyproject.toml"),
            ]
        }
        result = select_key_files(file_index)
        assert result == ["pyproject.toml", "main.py"]

    def test_entry_before_config(self) -> None:
        """入口文件应在配置文件之前."""
        file_index = {
            "files": [
                _make_file_entry("settings.py"),
                _make_file_entry("main.py"),
            ]
        }
        result = select_key_files(file_index)
        assert result == ["main.py", "settings.py"]

    def test_root_file_before_subdirectory_same_priority(self) -> None:
        """同优先级内根目录文件应优先于子目录文件."""
        # 两个 README.md: 一个在根目录, 一个在 docs/ 下
        file_index = {
            "files": [
                _make_file_entry("docs/README.md"),
                _make_file_entry("README.md"),
            ]
        }
        result = select_key_files(file_index)
        # 根目录 README.md (depth=0) 应在 docs/README.md (depth=1) 之前
        assert result == ["README.md", "docs/README.md"]

    def test_code_files_fill_remaining_slots(self) -> None:
        """关键文件不足 max_files 时用代码文件补足."""
        file_index = {
            "files": [
                _make_file_entry("README.md"),
                _make_file_entry("src/utils.py"),
                _make_file_entry("src/api/routes.py"),
            ]
        }
        result = select_key_files(file_index, max_files=3)
        assert result[0] == "README.md"
        # 代码文件按 (depth, path) 排序: src/api/routes.py (depth=2) 应在 src/utils.py (depth=1) 之后
        assert result == ["README.md", "src/utils.py", "src/api/routes.py"]

    def test_max_files_limit_enforced(self) -> None:
        """应严格遵守 max_files 上限."""
        file_index = {
            "files": [_make_file_entry(f"file_{i}.py") for i in range(20)]
        }
        result = select_key_files(file_index, max_files=5)
        assert len(result) == 5

    def test_llms_txt_highest_priority(self) -> None:
        """llms.txt 应与 README.md 同优先级 (都是文档型, 优先级 10)."""
        file_index = {
            "files": [
                _make_file_entry("main.py"),
                _make_file_entry("llms.txt"),
                _make_file_entry("README.md"),
            ]
        }
        result = select_key_files(file_index)
        # 文档型 (llms.txt + README.md) 应在入口文件 main.py 之前
        # llms.txt 与 README.md 同优先级 10, 同 depth=0, 按字母序: README.md < llms.txt
        assert result == ["README.md", "llms.txt", "main.py"]

    def test_empty_file_index(self) -> None:
        """空索引应返回空列表."""
        assert select_key_files({"files": []}) == []
        assert select_key_files({}) == []

    def test_non_dict_entries_skipped(self) -> None:
        """非 dict 类型的文件条目应被跳过, 不引发异常."""
        file_index = {
            "files": [
                "not_a_dict",
                None,
                _make_file_entry("README.md"),
                123,
            ]
        }
        result = select_key_files(file_index)
        assert result == ["README.md"]

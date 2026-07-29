"""单元测试: P1-5.3.1 文档行级引用溯源.

测试目标:
- extract_citations 提取 [src/foo.py:L42-L58] / [src/foo.py:L42] / [src/foo.py] 三种格式
- extract_citations 去重 (同文件同行范围只记录一次)
- validate_citations 校验文件路径存在性 (对照 file_index)
- validate_citations 校验行号范围合理性 (line_start <= line_end, 非正整数检测)
- extract_and_validate_citations 组合函数
- 空内容 / 无 file_index 等边界场景
"""
from __future__ import annotations

from src.skills.docbot.citation_extractor import (
    extract_and_validate_citations,
    extract_citations,
    validate_citations,
)


_SAMPLE_FILE_INDEX = {
    "files": [
        {"path": "src/server.py", "name": "server.py", "ext": ".py"},
        {"path": "src/api/routes.py", "name": "routes.py", "ext": ".py"},
        {"path": "scripts/init.sql", "name": "init.sql", "ext": ".sql"},
    ]
}


# ========== extract_citations 测试 ==========


class TestExtractCitations:
    """校验引用提取."""

    def test_extract_line_range_citation(self) -> None:
        """提取行范围引用 [src/foo.py:L42-L58]."""
        content = "API 路由注册在 [src/api/routes.py:L47-L120]。"
        citations = extract_citations(content)
        assert len(citations) == 1
        cit = citations[0]
        assert cit["file_path"] == "src/api/routes.py"
        assert cit["line_start"] == 47
        assert cit["line_end"] == 120
        assert cit["raw_reference"] == "[src/api/routes.py:L47-L120]"

    def test_extract_single_line_citation(self) -> None:
        """提取单行引用 [src/foo.py:L42], line_end 应等于 line_start."""
        content = "入口定义在 [src/server.py:L15]。"
        citations = extract_citations(content)
        assert len(citations) == 1
        cit = citations[0]
        assert cit["file_path"] == "src/server.py"
        assert cit["line_start"] == 15
        assert cit["line_end"] == 15  # 单行引用 line_end = line_start

    def test_extract_file_level_citation(self) -> None:
        """提取文件级引用 [src/foo.py], line_start/line_end 应为 None."""
        content = "完整代码见 [src/server.py]。"
        citations = extract_citations(content)
        assert len(citations) == 1
        cit = citations[0]
        assert cit["file_path"] == "src/server.py"
        assert cit["line_start"] is None
        assert cit["line_end"] is None

    def test_extract_multiple_citations(self) -> None:
        """提取多个引用."""
        content = """
API 路由 [src/api/routes.py:L47-L120]。
数据库脚本 [scripts/init.sql:L31-L50]。
入口 [src/server.py:L15]。
"""
        citations = extract_citations(content)
        assert len(citations) == 3
        paths = [c["file_path"] for c in citations]
        assert "src/api/routes.py" in paths
        assert "scripts/init.sql" in paths
        assert "src/server.py" in paths

    def test_dedup_same_citation(self) -> None:
        """相同引用 (同文件同行范围) 应去重, 只记录一次."""
        content = "见 [src/server.py:L15]。再次见 [src/server.py:L15]。"
        citations = extract_citations(content)
        assert len(citations) == 1

    def test_no_citation_in_content(self) -> None:
        """无引用的内容应返回空列表."""
        content = "这是一段没有引用的普通文本。"
        assert extract_citations(content) == []

    def test_empty_content(self) -> None:
        """空内容应返回空列表."""
        assert extract_citations("") == []

    def test_chapter_idx_attached(self) -> None:
        """chapter_idx 应被附加到每条引用."""
        content = "见 [src/server.py:L15]。"
        citations = extract_citations(content, chapter_idx=3)
        assert citations[0]["chapter_idx"] == 3

    def test_ignore_non_code_path_brackets(self) -> None:
        """非代码路径的方括号文本不应被误提取."""
        content = "这是 [普通文本] 和 [another] 不是引用。"
        assert extract_citations(content) == []

    def test_support_no_L_prefix(self) -> None:
        """兼容无 L 前缀的行号格式 [src/foo.py:42-58]."""
        content = "见 [src/server.py:42-58]。"
        citations = extract_citations(content)
        assert len(citations) == 1
        assert citations[0]["line_start"] == 42
        assert citations[0]["line_end"] == 58


# ========== validate_citations 测试 ==========


class TestValidateCitations:
    """校验引用校验."""

    def test_valid_citations_with_file_index(self) -> None:
        """所有引用路径都在 file_index 中时, 应通过."""
        citations = [
            {"file_path": "src/server.py", "line_start": 15, "line_end": 15},
            {"file_path": "src/api/routes.py", "line_start": 47, "line_end": 120},
        ]
        result = validate_citations(citations, file_index=_SAMPLE_FILE_INDEX)
        assert result["passed"] is True
        assert result["valid_count"] == 2
        assert result["invalid_count"] == 0
        assert result["missing_files"] == []

    def test_missing_file_detected(self) -> None:
        """引用的文件路径不在 file_index 中时, 应触发 warning."""
        citations = [
            {"file_path": "src/nonexistent.py", "line_start": 1, "line_end": 10},
        ]
        result = validate_citations(citations, file_index=_SAMPLE_FILE_INDEX)
        assert result["passed"] is True  # warning 不影响 passed
        assert result["invalid_count"] == 1
        assert "src/nonexistent.py" in result["missing_files"]

    def test_invalid_line_range_reversed(self) -> None:
        """行号范围颠倒 (line_start > line_end) 应触发 error."""
        citations = [
            {"file_path": "src/server.py", "line_start": 100, "line_end": 50},
        ]
        result = validate_citations(citations, file_index=_SAMPLE_FILE_INDEX)
        assert result["passed"] is False  # error 影响 passed
        assert result["invalid_count"] == 1
        assert len(result["invalid_line_ranges"]) == 1

    def test_invalid_line_range_non_positive(self) -> None:
        """行号非正整数 (0 或负数) 应触发 error."""
        citations = [
            {"file_path": "src/server.py", "line_start": 0, "line_end": 10},
        ]
        result = validate_citations(citations, file_index=_SAMPLE_FILE_INDEX)
        assert result["passed"] is False
        assert result["invalid_count"] == 1

    def test_no_file_index_skips_path_check(self) -> None:
        """file_index 为 None 时, 文件路径存在性校验应跳过."""
        citations = [
            {"file_path": "src/any_file.py", "line_start": 1, "line_end": 10},
        ]
        result = validate_citations(citations, file_index=None)
        # 路径校验跳过, 行号合理, 应通过
        assert result["passed"] is True
        assert result["valid_count"] == 1
        assert result["missing_files"] == []

    def test_empty_citations(self) -> None:
        """空引用列表应返回 passed=True."""
        result = validate_citations([], file_index=_SAMPLE_FILE_INDEX)
        assert result["passed"] is True
        assert result["total_citations"] == 0

    def test_excessive_line_number_warning(self) -> None:
        """行号过大 (超过 100 万) 应触发 warning (可能是 LLM 幻觉)."""
        citations = [
            {"file_path": "src/server.py", "line_start": 1, "line_end": 2_000_000},
        ]
        result = validate_citations(citations, file_index=_SAMPLE_FILE_INDEX)
        assert result["passed"] is True  # warning 不影响 passed
        assert result["invalid_count"] == 1
        assert len(result["invalid_line_ranges"]) == 1


# ========== extract_and_validate_citations 组合测试 ==========


class TestExtractAndValidate:
    """校验组合函数."""

    def test_extract_and_validate_combined(self) -> None:
        """组合函数应同时完成提取和校验."""
        content = """
API 路由 [src/api/routes.py:L47-L120]。
不存在 [src/nonexistent.py:L10-L20]。
"""
        citations, validation = extract_and_validate_citations(
            content, file_index=_SAMPLE_FILE_INDEX
        )
        assert len(citations) == 2
        assert validation["total_citations"] == 2
        assert validation["valid_count"] == 1  # src/api/routes.py 有效
        assert validation["invalid_count"] == 1  # src/nonexistent.py 无效

    def test_extract_and_validate_empty_content(self) -> None:
        """空内容应返回空列表和通过的校验结果."""
        citations, validation = extract_and_validate_citations("")
        assert citations == []
        assert validation["passed"] is True
        assert validation["total_citations"] == 0

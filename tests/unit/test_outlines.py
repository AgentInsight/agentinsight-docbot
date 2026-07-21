"""单元测试: 8 种大纲文件存在性 + YAML frontmatter 解析.

测试目标:
- 8 种大纲文件存在性 (docs/{ARCHITECTURE,HLD,PRD,TEST_CASE,OPTIMIZATION,PERF_ANALYSIS,DEFECT,API_DOC}_OUTLINE.md)
- load_outline('architecture') 返回 list[dict] 含 idx/title/sections/key_points 字段
- load_outline_meta('architecture') 返回 dict 含 report_type/name_zh/default_chapters/max_chapters
- parse_markdown_outline 解析 YAML frontmatter + 章节列表 (含 sections/key_points 提取)
"""
from __future__ import annotations

from pathlib import Path

import pytest

from src.config.docbot.outlines import load_outline, load_outline_meta, parse_markdown_outline
from src.config.docbot.personas import DOCBOT_REPORT_PERSONAS

# 8 种大纲文件 (见 AGENTS.md 第 7 章 8 种文档默认大纲文件)
_EXPECTED_OUTLINE_FILES = frozenset(
    {
        "ARCHITECTURE_OUTLINE.md",
        "HLD_OUTLINE.md",
        "PRD_OUTLINE.md",
        "TEST_CASE_OUTLINE.md",
        "OPTIMIZATION_OUTLINE.md",
        "PERF_ANALYSIS_OUTLINE.md",
        "DEFECT_OUTLINE.md",
        "API_DOC_OUTLINE.md",
    }
)

_PROJECT_ROOT = Path(__file__).parent.parent.parent
_DOCS_DIR = _PROJECT_ROOT / "docs"


class TestOutlineFilesExistence:
    """8 种大纲文件存在性测试."""

    @pytest.mark.parametrize("outline_file", sorted(_EXPECTED_OUTLINE_FILES))
    def test_outline_file_exists(self, outline_file: str) -> None:
        """验证 8 种大纲文件存在."""
        file_path = _DOCS_DIR / outline_file
        assert file_path.exists(), f"大纲文件不存在: {file_path}"

    def test_all_outline_files_in_personas_exist(self) -> None:
        """验证 personas.outline_file 对应的所有大纲文件都存在."""
        for report_type, persona in DOCBOT_REPORT_PERSONAS.items():
            file_path = _DOCS_DIR / persona["outline_file"]
            assert file_path.exists(), (
                f"report_type={report_type} 的 outline_file={persona['outline_file']} 不存在"
            )

    @pytest.mark.parametrize("outline_file", sorted(_EXPECTED_OUTLINE_FILES))
    def test_outline_file_not_empty(self, outline_file: str) -> None:
        """验证大纲文件非空."""
        file_path = _DOCS_DIR / outline_file
        content = file_path.read_text(encoding="utf-8")
        assert len(content) > 100, f"大纲文件 {outline_file} 内容过短 ({len(content)} 字符)"


class TestLoadOutline:
    """load_outline 函数测试 (返回 list[dict])."""

    def test_load_outline_architecture_returns_list(self) -> None:
        """load_outline('architecture') 返回 list[dict]."""
        outline = load_outline("architecture")
        assert isinstance(outline, list)
        assert len(outline) > 0

    @pytest.mark.parametrize(
        "report_type",
        sorted(DOCBOT_REPORT_PERSONAS.keys()),
    )
    def test_load_outline_all_types_return_list(self, report_type: str) -> None:
        """load_outline 对 8 种类型都返回 list[dict]."""
        outline = load_outline(report_type)
        assert isinstance(outline, list)
        assert len(outline) > 0

    def test_load_outline_unknown_raises_value_error(self) -> None:
        """load_outline('unknown') 抛 ValueError."""
        with pytest.raises(ValueError, match="Unknown report_type"):
            load_outline("unknown")

    def test_load_outline_chapters_have_required_fields(self) -> None:
        """每个章节含 idx / title / sections / key_points 字段."""
        outline = load_outline("architecture")
        for ch in outline:
            assert "idx" in ch, f"章节缺 idx: {ch}"
            assert "title" in ch, f"章节缺 title: {ch}"
            assert "sections" in ch, f"章节缺 sections: {ch}"
            assert "key_points" in ch, f"章节缺 key_points: {ch}"
            assert isinstance(ch["idx"], int)
            assert isinstance(ch["title"], str)
            assert isinstance(ch["sections"], list)
            assert isinstance(ch["key_points"], list)


class TestLoadOutlineMeta:
    """load_outline_meta 函数测试 (返回元数据 dict)."""

    def test_load_outline_meta_architecture(self) -> None:
        """load_outline_meta('architecture') 返回元数据 dict."""
        meta = load_outline_meta("architecture")
        assert isinstance(meta, dict)
        assert meta["report_type"] == "architecture"
        assert "name_zh" in meta
        assert "name_en" in meta
        assert isinstance(meta["default_chapters"], int)
        assert isinstance(meta["max_chapters"], int)

    @pytest.mark.parametrize(
        "report_type",
        sorted(DOCBOT_REPORT_PERSONAS.keys()),
    )
    def test_load_outline_meta_all_types(self, report_type: str) -> None:
        """load_outline_meta 对 8 种类型都返回正确元数据."""
        meta = load_outline_meta(report_type)
        assert meta["report_type"] == report_type


class TestParseMarkdownOutline:
    """parse_markdown_outline 函数测试 (返回完整 dict 含 meta + chapters)."""

    def test_parse_with_frontmatter(self) -> None:
        """解析含 YAML frontmatter 的大纲."""
        markdown = """---
report_type: test_type
name_zh: 测试类型
name_en: Test Type
default_chapters: 5
max_chapters: 10
---

# 测试大纲

## 第1章 概述
内容1

## 第2章 详情
内容2
"""
        result = parse_markdown_outline(markdown, report_type="test_type")
        assert result["report_type"] == "test_type"
        assert result["name_zh"] == "测试类型"
        assert result["name_en"] == "Test Type"
        assert result["default_chapters"] == 5
        assert result["max_chapters"] == 10
        assert "raw_markdown" in result
        assert isinstance(result["chapters"], list)
        # 只匹配 ## 第N章, 不匹配 # 主标题
        assert len(result["chapters"]) == 2

    def test_parse_without_frontmatter(self) -> None:
        """解析不含 YAML frontmatter 的大纲 (应使用默认值)."""
        markdown = """# 大纲标题

## 第1章 概述
内容1
"""
        result = parse_markdown_outline(markdown, report_type="custom")
        assert result["report_type"] == "custom"
        assert result["name_zh"] == ""  # 默认空字符串
        assert result["default_chapters"] == 10  # 默认值
        assert result["max_chapters"] == 20  # 默认值

    def test_parse_invalid_yaml_falls_back_to_empty(self) -> None:
        """YAML frontmatter 解析失败时, 应降级到空 dict."""
        markdown = """---
: invalid: yaml: syntax
---

# 大纲
## 第1章 概述
"""
        result = parse_markdown_outline(markdown, report_type="custom")
        # YAML 解析失败时, frontmatter 为空 dict, 使用默认值
        assert result["default_chapters"] == 10
        assert result["max_chapters"] == 20

    def test_parse_chapters_content(self) -> None:
        """章节内容应正确截取 (# 主标题不作为章节)."""
        markdown = """# 大纲

## 第1章 概述
章节1内容

## 第2章 详情
章节2内容
"""
        result = parse_markdown_outline(markdown, report_type="custom")
        # 只匹配 ## 第N章, 不匹配 # 大纲 (主标题)
        assert len(result["chapters"]) == 2
        # 第 1 个章节 (第1章 概述) 应包含 "章节1内容"
        assert "章节1内容" in result["chapters"][0]["content"]
        # 第 2 个章节 (第2章 详情) 应包含 "章节2内容"
        assert "章节2内容" in result["chapters"][1]["content"]

    def test_parse_extracts_key_points(self) -> None:
        """从 **要点**: 后的列表项提取 key_points."""
        markdown = """# 大纲

## 第1章 概述
**目的**：阐明背景
**要点**：
- 业务背景与目标
- 系统定位与核心价值
- 利益相关方矩阵

## 第2章 详情
**要点**：
- 详细设计
- 接口规范
"""
        result = parse_markdown_outline(markdown, report_type="custom")
        assert len(result["chapters"]) == 2
        # 第 1 章应提取 3 个 key_points
        assert len(result["chapters"][0]["key_points"]) == 3
        assert "业务背景与目标" in result["chapters"][0]["key_points"]
        # 第 2 章应提取 2 个 key_points
        assert len(result["chapters"][1]["key_points"]) == 2
        assert "详细设计" in result["chapters"][1]["key_points"]

    def test_parse_chapters_have_sections_and_key_points_fields(self) -> None:
        """每个章节含 sections / key_points 字段 (即使为空)."""
        markdown = """# 大纲

## 第1章 概述
内容
"""
        result = parse_markdown_outline(markdown, report_type="custom")
        assert len(result["chapters"]) == 1
        ch = result["chapters"][0]
        assert "sections" in ch
        assert "key_points" in ch
        assert isinstance(ch["sections"], list)
        assert isinstance(ch["key_points"], list)

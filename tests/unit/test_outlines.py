"""单元测试: 8 种 YAML 大纲文件存在性 + load_outline / load_outline_meta.

测试目标:
- 8 种 YAML 大纲文件存在性 (src/config/docbot/outlines/{architecture,design,...}.yaml)
- load_outline('architecture') 返回 list[dict] 含 idx/title/purpose/sections/key_points 字段
- load_outline_meta('architecture') 返回 dict 含 report_type/name_zh/default_chapters/max_chapters
- load_outline_full 返回完整大纲 (含 persona / writing_rules / output_format)
"""
from __future__ import annotations

from pathlib import Path

import pytest

from src.config.docbot.outlines import (
    OutlineSpec,
    load_outline,
    load_outline_full,
    load_outline_meta,
)
from src.config.docbot.personas import DOCBOT_REPORT_PERSONAS

# 8 种 YAML 大纲文件 (见 AGENTS.md 第 7 章 8 种文档默认大纲)
_EXPECTED_OUTLINE_FILES = frozenset(
    {
        "architecture.yaml",
        "design.yaml",
        "requirements.yaml",
        "testcase.yaml",
        "optimization.yaml",
        "performance.yaml",
        "defect.yaml",
        "api_doc.yaml",
    }
)

_PROJECT_ROOT = Path(__file__).parent.parent.parent
_OUTLINES_DIR = _PROJECT_ROOT / "src" / "config" / "docbot" / "outlines"


class TestOutlineFilesExistence:
    """8 种 YAML 大纲文件存在性测试."""

    @pytest.mark.parametrize("outline_file", sorted(_EXPECTED_OUTLINE_FILES))
    def test_outline_file_exists(self, outline_file: str) -> None:
        """验证 8 种 YAML 大纲文件存在."""
        file_path = _OUTLINES_DIR / outline_file
        assert file_path.exists(), f"大纲文件不存在: {file_path}"

    def test_all_outline_yaml_in_personas_exist(self) -> None:
        """验证 personas.outline_yaml 对应的所有 YAML 文件都存在."""
        for report_type, persona in DOCBOT_REPORT_PERSONAS.items():
            file_path = _OUTLINES_DIR / persona["outline_yaml"]
            assert file_path.exists(), (
                f"report_type={report_type} 的 outline_yaml={persona['outline_yaml']} 不存在"
            )

    @pytest.mark.parametrize("outline_file", sorted(_EXPECTED_OUTLINE_FILES))
    def test_outline_file_not_empty(self, outline_file: str) -> None:
        """验证 YAML 大纲文件非空."""
        file_path = _OUTLINES_DIR / outline_file
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
        """每个章节含 idx / title / purpose / sections / key_points 字段 (YAML 格式独有 purpose)."""
        outline = load_outline("architecture")
        for ch in outline:
            assert "idx" in ch, f"章节缺 idx: {ch}"
            assert "title" in ch, f"章节缺 title: {ch}"
            assert "purpose" in ch, f"章节缺 purpose (YAML 格式独有): {ch}"
            assert "sections" in ch, f"章节缺 sections: {ch}"
            assert "key_points" in ch, f"章节缺 key_points: {ch}"
            assert isinstance(ch["idx"], int)
            assert isinstance(ch["title"], str)
            assert isinstance(ch["sections"], list)
            assert isinstance(ch["key_points"], list)

    @pytest.mark.parametrize(
        "report_type",
        sorted(DOCBOT_REPORT_PERSONAS.keys()),
    )
    def test_load_outline_chapter_idx_sequential(self, report_type: str) -> None:
        """所有章节 idx 从 1 严格递增."""
        outline = load_outline(report_type)
        idx_list = [ch["idx"] for ch in outline]
        assert idx_list == list(range(1, len(outline) + 1)), (
            f"{report_type} idx 不连续: {idx_list}"
        )


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

    @pytest.mark.parametrize(
        "report_type",
        sorted(DOCBOT_REPORT_PERSONAS.keys()),
    )
    def test_load_outline_meta_max_ge_default(self, report_type: str) -> None:
        """max_chapters 应不小于 default_chapters (schema 校验)."""
        meta = load_outline_meta(report_type)
        assert meta["max_chapters"] >= meta["default_chapters"], (
            f"{report_type}: max_chapters ({meta['max_chapters']}) < default_chapters ({meta['default_chapters']})"
        )


class TestLoadOutlineFull:
    """load_outline_full 函数测试 (返回完整大纲含 persona / writing_rules / output_format)."""

    @pytest.mark.parametrize(
        "report_type",
        sorted(DOCBOT_REPORT_PERSONAS.keys()),
    )
    def test_load_outline_full_structure(self, report_type: str) -> None:
        """load_outline_full 返回完整大纲结构."""
        full = load_outline_full(report_type)
        assert isinstance(full, dict)
        # 元数据字段
        assert full["report_type"] == report_type
        assert "name_zh" in full
        assert "name_en" in full
        assert isinstance(full["default_chapters"], int)
        assert isinstance(full["max_chapters"], int)
        # persona 字段 (YAML 独有)
        assert "persona" in full
        assert isinstance(full["persona"], dict)
        assert "role" in full["persona"]
        assert "mission" in full["persona"]
        assert "target_audience" in full["persona"]
        assert isinstance(full["persona"]["target_audience"], list)
        # chapters 字段
        assert isinstance(full["chapters"], list)
        assert len(full["chapters"]) > 0
        # writing_rules 字段
        assert "writing_rules" in full
        assert isinstance(full["writing_rules"], list)
        # output_format 字段
        assert "output_format" in full
        assert isinstance(full["output_format"], dict)


class TestOutlineSpecSchema:
    """OutlineSpec Pydantic schema 校验测试."""

    @pytest.mark.parametrize(
        "report_type",
        sorted(DOCBOT_REPORT_PERSONAS.keys()),
    )
    def test_outline_yaml_passes_pydantic_schema(self, report_type: str) -> None:
        """每个 YAML 大纲文件通过 OutlineSpec schema 校验 (load_outline_full 内部已校验)."""
        # load_outline_full 内部已通过 OutlineSpec.model_validate 校验,
        # 若 YAML 不符合 schema 会抛 ValueError
        full = load_outline_full(report_type)
        assert full["report_type"] == report_type

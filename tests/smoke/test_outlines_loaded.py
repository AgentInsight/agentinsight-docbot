"""冒烟测试: 8 种大纲 load_outline 不抛异常.

测试目标 (P0 修复后):
- load_outline('architecture') 返回 list[dict] 不抛异常
- 8 种 report_type 都能加载
- load_outline_meta 返回 dict 含元数据
"""
from __future__ import annotations

import pytest

from src.config.docbot.outlines import load_outline, load_outline_meta
from src.config.docbot.personas import DOCBOT_REPORT_PERSONAS


class TestOutlinesLoaded:
    """8 种大纲加载冒烟测试 (load_outline 返回 list[dict])."""

    @pytest.mark.parametrize("report_type", sorted(DOCBOT_REPORT_PERSONAS.keys()))
    def test_load_outline_does_not_raise(self, report_type: str) -> None:
        """load_outline(report_type) 返回 list[dict] 不抛异常."""
        outline = load_outline(report_type)
        assert isinstance(outline, list)
        assert len(outline) > 0

    def test_load_outline_architecture_has_chapters(self) -> None:
        """architecture 大纲含章节."""
        outline = load_outline("architecture")
        assert isinstance(outline, list)
        assert len(outline) >= 3  # 至少 3 章

    def test_load_outline_api_doc_has_chapters(self) -> None:
        """api_doc 大纲含章节."""
        outline = load_outline("api_doc")
        assert isinstance(outline, list)
        assert len(outline) >= 3

    def test_load_outline_chapters_have_idx_and_title(self) -> None:
        """所有章节含 idx 和 title 字段."""
        outline = load_outline("architecture")
        for ch in outline:
            assert "idx" in ch
            assert "title" in ch
            assert isinstance(ch["idx"], int)
            assert isinstance(ch["title"], str)
            assert ch["title"]  # 非空


class TestOutlinesMetaLoaded:
    """8 种大纲元数据 load_outline_meta 冒烟测试."""

    @pytest.mark.parametrize("report_type", sorted(DOCBOT_REPORT_PERSONAS.keys()))
    def test_load_outline_meta_does_not_raise(self, report_type: str) -> None:
        """load_outline_meta(report_type) 返回 dict 不抛异常."""
        meta = load_outline_meta(report_type)
        assert isinstance(meta, dict)
        assert meta["report_type"] == report_type
        assert "name_zh" in meta
        assert "name_en" in meta

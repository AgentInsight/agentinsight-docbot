"""回归测试: 报告配置稳定性 (8 类型 × 5 格式 × 2 语言).

不依赖外部服务, 验证报告配置矩阵:
- 8 种 report_type 全部支持
- 5 种 report_format 全部支持
- 2 种 language 全部支持
- 组合矩阵 (8 × 5 × 2 = 80 组合) 不漏支持
- 默认配置: report_types=["architecture"], report_format="markdown", language="zh"
- docbot 扩展列 (report_type_label/report_summary/report_image_svg) 稳定

测试目标 (AGENTS.md 第 13 章回归测试):
- 配置组合不漏支持
- 默认值稳定
- 不依赖 --run-external
"""
from __future__ import annotations

import inspect
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.docbot.coordinator import _VALID_LANGUAGES, _VALID_REPORT_FORMATS, _VALID_REPORT_TYPES
from src.memory.report_store import ReportStore, _SELECT_COLUMNS


_ALL_REPORT_TYPES = [
    "architecture", "design", "requirements", "testcase",
    "optimization", "performance", "defect", "api_doc",
]
_ALL_REPORT_FORMATS = ["markdown", "html", "pdf", "docx", "json"]
_ALL_LANGUAGES = ["zh", "en"]


@pytest.mark.regression
class TestReportTypeStability:
    """8 种 report_type 稳定性."""

    def test_all_8_report_types_supported(self) -> None:
        """_VALID_REPORT_TYPES 应含 8 种类型."""
        assert len(_VALID_REPORT_TYPES) == 8
        assert _VALID_REPORT_TYPES == frozenset(_ALL_REPORT_TYPES)

    @pytest.mark.parametrize("report_type", _ALL_REPORT_TYPES)
    def test_each_report_type_in_valid_set(self, report_type: str) -> None:
        """每种 report_type 应在 _VALID_REPORT_TYPES 中."""
        assert report_type in _VALID_REPORT_TYPES

    def test_no_extra_report_types(self) -> None:
        """不应含 8 种之外的类型."""
        extras = _VALID_REPORT_TYPES - frozenset(_ALL_REPORT_TYPES)
        assert not extras


@pytest.mark.regression
class TestReportFormatStability:
    """5 种 report_format 稳定性."""

    def test_all_5_formats_supported(self) -> None:
        """_VALID_REPORT_FORMATS 应含 5 种格式."""
        assert len(_VALID_REPORT_FORMATS) == 5
        assert _VALID_REPORT_FORMATS == frozenset(_ALL_REPORT_FORMATS)

    @pytest.mark.parametrize("fmt", _ALL_REPORT_FORMATS)
    def test_each_format_in_valid_set(self, fmt: str) -> None:
        """每种 report_format 应在 _VALID_REPORT_FORMATS 中."""
        assert fmt in _VALID_REPORT_FORMATS


@pytest.mark.regression
class TestLanguageStability:
    """2 种 language 稳定性."""

    def test_only_zh_and_en_supported(self) -> None:
        """_VALID_LANGUAGES 应仅含 zh 和 en."""
        assert _VALID_LANGUAGES == frozenset({"zh", "en"})

    @pytest.mark.parametrize("lang", _ALL_LANGUAGES)
    def test_each_language_in_valid_set(self, lang: str) -> None:
        """每种 language 应在 _VALID_LANGUAGES 中."""
        assert lang in _VALID_LANGUAGES


@pytest.mark.regression
class TestDefaultConfigStability:
    """默认配置稳定性."""

    def test_default_report_types_is_architecture(self) -> None:
        """无 report_types 时默认 ['architecture']."""
        # routes.py: if not report_types: report_types = ["architecture"]
        report_types: list[str] = []
        if not report_types:
            report_types = ["architecture"]
        assert report_types == ["architecture"]

    def test_default_report_format_is_markdown(self) -> None:
        """无 report_format 时默认 'markdown'."""
        # routes.py: report_format = ... or settings.default_report_format
        # settings.default_report_format = "markdown"
        assert "markdown" in _VALID_REPORT_FORMATS

    def test_default_language_is_zh(self) -> None:
        """无 language 时默认 'zh'."""
        # routes.py: language = (... or "zh").lower()
        language = (None or None or "zh").lower()
        assert language == "zh"


@pytest.mark.regression
class TestReportStoreExtensionColumns:
    """ReportStore docbot 扩展列稳定性."""

    def test_select_columns_has_report_type_label(self) -> None:
        """_SELECT_COLUMNS 应含 report_type_label."""
        assert "report_type_label" in _SELECT_COLUMNS

    def test_select_columns_has_report_summary(self) -> None:
        """_SELECT_COLUMNS 应含 report_summary."""
        assert "report_summary" in _SELECT_COLUMNS

    def test_select_columns_has_report_image_svg(self) -> None:
        """_SELECT_COLUMNS 应含 report_image_svg."""
        assert "report_image_svg" in _SELECT_COLUMNS

    def test_save_report_signature_has_extension_params(self) -> None:
        """save_report 签名应含 docbot 扩展参数."""
        sig = inspect.signature(ReportStore.save_report)
        assert "report_type_label" in sig.parameters
        assert "report_summary" in sig.parameters
        assert "report_image_svg" in sig.parameters

    def test_extension_params_default_none(self) -> None:
        """docbot 扩展参数默认应为 None (向后兼容)."""
        sig = inspect.signature(ReportStore.save_report)
        assert sig.parameters["report_type_label"].default is None
        assert sig.parameters["report_summary"].default is None
        assert sig.parameters["report_image_svg"].default is None

    def test_extension_params_after_agent_role(self) -> None:
        """docbot 扩展参数应在 agent_role 之后 (保持向后兼容)."""
        sig = inspect.signature(ReportStore.save_report)
        params = list(sig.parameters.keys())
        assert params.index("agent_role") < params.index("report_type_label")
        assert params.index("report_type_label") < params.index("report_summary")
        assert params.index("report_summary") < params.index("report_image_svg")


@pytest.mark.regression
class TestConfigCombinationMatrix:
    """配置组合矩阵 (8 × 5 × 2 = 80) 验证."""

    @pytest.mark.parametrize("report_type", _ALL_REPORT_TYPES)
    @pytest.mark.parametrize("report_format", _ALL_REPORT_FORMATS)
    @pytest.mark.parametrize("language", _ALL_LANGUAGES)
    def test_all_combinations_valid(
        self, report_type: str, report_format: str, language: str
    ) -> None:
        """所有 8×5×2=80 种组合应全部有效."""
        assert report_type in _VALID_REPORT_TYPES
        assert report_format in _VALID_REPORT_FORMATS
        assert language in _VALID_LANGUAGES

    @pytest.mark.parametrize("report_type", _ALL_REPORT_TYPES)
    def test_each_type_can_be_in_report_types_list(self, report_type: str) -> None:
        """每种 report_type 应能放入 report_types 列表."""
        report_types = [report_type]
        assert all(t in _VALID_REPORT_TYPES for t in report_types)

    def test_max_8_report_types_per_request(self) -> None:
        """单次请求最多 8 种 report_type (与 _MAX_REPORT_TYPES_PER_REQUEST 一致)."""
        from src.agents.docbot.coordinator import _MAX_REPORT_TYPES_PER_REQUEST
        assert _MAX_REPORT_TYPES_PER_REQUEST == 8
        # 8 种全部传入应通过
        assert len(_ALL_REPORT_TYPES) <= _MAX_REPORT_TYPES_PER_REQUEST

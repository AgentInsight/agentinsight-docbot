"""单元测试: P2-5.4.1 多视角代码审问配置.

测试目标:
- DOCBOT_PERSPECTIVES 数据结构完整性 (8 种 report_type × 3 视角)
- get_perspectives 返回值与异常
- 每个视角含 role / focus / question_topics 字段
"""

from __future__ import annotations

import pytest

from src.config.docbot.perspectives import DOCBOT_PERSPECTIVES, get_perspectives

# 8 种支持的 report_type
_SUPPORTED_REPORT_TYPES = [
    "architecture",
    "design",
    "requirements",
    "testcase",
    "optimization",
    "performance",
    "defect",
    "api_doc",
]


class TestPerspectivesStructure:
    """校验视角配置数据结构完整性."""

    def test_all_8_report_types_covered(self) -> None:
        """8 种 report_type 应全部覆盖."""
        assert set(DOCBOT_PERSPECTIVES.keys()) == set(_SUPPORTED_REPORT_TYPES)

    def test_each_report_type_has_3_perspectives(self) -> None:
        """每种 report_type 应派生 3 个视角 (成本与收益平衡)."""
        for report_type in _SUPPORTED_REPORT_TYPES:
            perspectives = DOCBOT_PERSPECTIVES[report_type]
            assert len(perspectives) == 3, f"{report_type} 应有 3 个视角, 实际 {len(perspectives)}"

    def test_each_perspective_has_required_fields(self) -> None:
        """每个视角应含 role / focus / question_topics 字段."""
        for report_type, perspectives in DOCBOT_PERSPECTIVES.items():
            for i, p in enumerate(perspectives):
                assert "role" in p, f"{report_type}[{i}] 缺少 role"
                assert "focus" in p, f"{report_type}[{i}] 缺少 focus"
                assert "question_topics" in p, f"{report_type}[{i}] 缺少 question_topics"
                assert isinstance(p["role"], str) and p["role"], (
                    f"{report_type}[{i}] role 应为非空字符串"
                )
                assert isinstance(p["focus"], str) and p["focus"], (
                    f"{report_type}[{i}] focus 应为非空字符串"
                )
                assert isinstance(p["question_topics"], list) and len(p["question_topics"]) >= 3, (
                    f"{report_type}[{i}] question_topics 应为至少 3 条的列表"
                )

    def test_perspective_roles_unique_per_report_type(self) -> None:
        """每种 report_type 内 3 个视角的 role 应互不相同 (避免视角重叠)."""
        for report_type, perspectives in DOCBOT_PERSPECTIVES.items():
            roles = [p["role"] for p in perspectives]
            assert len(set(roles)) == 3, f"{report_type} 视角 role 应互不相同, 实际: {roles}"


class TestGetPerspectives:
    """校验 get_perspectives 函数行为."""

    def test_valid_report_type_returns_list(self) -> None:
        """有效的 report_type 应返回视角列表."""
        result = get_perspectives("architecture")
        assert isinstance(result, list)
        assert len(result) == 3

    def test_returns_same_reference_as_dict(self) -> None:
        """返回值应与字典中的列表内容一致 (静态配置, 不需要深拷贝)."""
        result = get_perspectives("defect")
        assert result is DOCBOT_PERSPECTIVES["defect"]

    def test_unknown_report_type_raises_value_error(self) -> None:
        """未知 report_type 应抛 ValueError."""
        with pytest.raises(ValueError, match="Unknown report_type"):
            get_perspectives("nonexistent")

    def test_empty_string_raises_value_error(self) -> None:
        """空字符串应抛 ValueError."""
        with pytest.raises(ValueError, match="Unknown report_type"):
            get_perspectives("")

    def test_all_8_types_callable(self) -> None:
        """8 种 report_type 都应可正常调用."""
        for report_type in _SUPPORTED_REPORT_TYPES:
            result = get_perspectives(report_type)
            assert len(result) == 3

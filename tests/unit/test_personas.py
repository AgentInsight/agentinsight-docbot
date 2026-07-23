"""单元测试: docbot 8 种 persona 完整性.

测试目标 (见 AGENTS.md 第 13 章关键测试用例 1):
- DOCBOT_REPORT_PERSONAS 含 8 种类型
- 每种 persona 含 role_name / description / tone / target_audience / outline_yaml 字段
- get_persona('architecture') 返回正确字典
- get_persona('unknown') 抛 ValueError
"""
from __future__ import annotations

import pytest

from src.config.docbot.personas import DOCBOT_REPORT_PERSONAS, get_persona

# 8 种支持的文档类型 (见 AGENTS.md 第 7 章)
_EXPECTED_REPORT_TYPES = frozenset(
    {
        "architecture",
        "design",
        "requirements",
        "testcase",
        "optimization",
        "performance",
        "defect",
        "api_doc",
    }
)

# 每个 persona 必须含的字段 (outline_yaml 指向 src/config/docbot/outlines/*.yaml)
_REQUIRED_PERSONA_FIELDS = frozenset(
    {"role_name", "description", "tone", "target_audience", "outline_yaml"}
)


class TestDocbotReportPersonas:
    """DOCBOT_REPORT_PERSONAS 字典完整性测试."""

    def test_personas_contains_eight_types(self) -> None:
        """验证 personas 含 8 种类型."""
        assert len(DOCBOT_REPORT_PERSONAS) == 8, "DOCBOT_REPORT_PERSONAS 应含 8 种类型"
        assert set(DOCBOT_REPORT_PERSONAS.keys()) == _EXPECTED_REPORT_TYPES

    @pytest.mark.parametrize("report_type", sorted(_EXPECTED_REPORT_TYPES))
    def test_persona_has_required_fields(self, report_type: str) -> None:
        """验证每种 persona 含所有必需字段 (8 种参数化)."""
        persona = DOCBOT_REPORT_PERSONAS[report_type]
        for field in _REQUIRED_PERSONA_FIELDS:
            assert field in persona, f"persona {report_type} 缺字段: {field}"
            assert isinstance(persona[field], str), f"persona.{field} 应为 str"
            assert persona[field], f"persona.{report_type}.{field} 不能为空字符串"

    @pytest.mark.parametrize("report_type", sorted(_EXPECTED_REPORT_TYPES))
    def test_persona_outline_yaml_ends_with_yaml(self, report_type: str) -> None:
        """验证 outline_yaml 字段以 .yaml 结尾."""
        outline_yaml = DOCBOT_REPORT_PERSONAS[report_type]["outline_yaml"]
        assert outline_yaml.endswith(".yaml"), (
            f"{report_type}.outline_yaml 应以 .yaml 结尾, 实际: {outline_yaml}"
        )

    @pytest.mark.parametrize("report_type", sorted(_EXPECTED_REPORT_TYPES))
    def test_persona_outline_yaml_unique(self, report_type: str) -> None:
        """验证 8 种 persona 的 outline_yaml 互不相同."""
        files = [p["outline_yaml"] for p in DOCBOT_REPORT_PERSONAS.values()]
        assert len(files) == len(set(files)), "outline_yaml 应唯一"


class TestGetPersona:
    """get_persona 函数测试."""

    def test_get_persona_architecture(self) -> None:
        """get_persona('architecture') 返回正确字典."""
        persona = get_persona("architecture")
        assert persona["role_name"] == "技术架构师"
        assert persona["outline_yaml"] == "architecture.yaml"

    def test_get_persona_api_doc(self) -> None:
        """get_persona('api_doc') 返回正确字典."""
        persona = get_persona("api_doc")
        assert persona["role_name"] == "API 文档工程师"
        assert persona["outline_yaml"] == "api_doc.yaml"

    @pytest.mark.parametrize("report_type", sorted(_EXPECTED_REPORT_TYPES))
    def test_get_persona_all_types(self, report_type: str) -> None:
        """get_persona 对 8 种类型都返回正确字典."""
        persona = get_persona(report_type)
        assert persona == DOCBOT_REPORT_PERSONAS[report_type]

    def test_get_persona_unknown_raises_value_error(self) -> None:
        """get_persona('unknown') 抛 ValueError."""
        with pytest.raises(ValueError, match="Unknown report_type"):
            get_persona("unknown")

    def test_get_persona_empty_raises_value_error(self) -> None:
        """get_persona('') 抛 ValueError."""
        with pytest.raises(ValueError, match="Unknown report_type"):
            get_persona("")

    def test_get_persona_none_raises_value_error(self) -> None:
        """get_persona(None) 抛 ValueError (None 不在 DOCBOT_REPORT_PERSONAS)."""
        with pytest.raises(ValueError, match="Unknown report_type"):
            get_persona(None)  # type: ignore[arg-type]

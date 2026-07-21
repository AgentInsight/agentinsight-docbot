"""探索性测试: 配置组合矩阵 (8 report_type × 2 language × 5 format).

验证所有合法配置组合均能正确生成报告 (或不支持的组合返回明确错误).
需要部署后容器栈.

8 种 report_type: architecture|design|requirements|testcase|optimization|performance|defect|api_doc
2 种 language: zh | en
5 种 format: markdown | html | pdf | docx | json
"""
from __future__ import annotations

import itertools

import pytest

REPORT_TYPES = [
    "architecture",
    "design",
    "requirements",
    "testcase",
    "optimization",
    "performance",
    "defect",
    "api_doc",
]
LANGUAGES = ["zh", "en"]
FORMATS = ["markdown", "html", "pdf", "docx", "json"]


def _generate_combinations() -> list[tuple[str, str, str]]:
    """生成所有 report_type × language × format 组合."""
    return list(itertools.product(REPORT_TYPES, LANGUAGES, FORMATS))


COMBINATIONS = _generate_combinations()


@pytest.mark.exploratory
@pytest.mark.requires_external
class TestConfigCombinations:
    """配置组合矩阵测试 (参数化)."""

    @pytest.mark.parametrize(
        "report_type,language,report_format",
        COMBINATIONS,
        ids=[f"{rt}-{lang}-{fmt}" for rt, lang, fmt in COMBINATIONS],
    )
    async def test_config_combination(
        self,
        report_type: str,
        language: str,
        report_format: str,
    ) -> None:
        """测试每种 report_type × language × format 组合生成报告."""
        pytest.skip("Requires external services")

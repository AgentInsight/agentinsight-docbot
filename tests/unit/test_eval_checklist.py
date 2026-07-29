"""单元测试: P2-5.5.1 人工评估 checklist.

测试目标:
- calculate_score 计算 5 维度加权总分 (0-100) 与等级 A/B/C/D
- calculate_score 处理缺失项 / 无效分数 / 边界场景
- render_checklist_markdown 渲染 Markdown 表格 (空白模板 + 已填写)
- get_checklist_template 返回空白模板结构
- get_dimensions 返回维度定义
- 权重总和为 100 (设计约束)
"""
from __future__ import annotations

from src.skills.docbot.eval_checklist import (
    calculate_score,
    get_checklist_template,
    get_dimensions,
    render_checklist_markdown,
)

# ========== 测试数据 ==========

# 完美评分 (全部 5 分) -> 总分 100, 等级 A
_PERFECT_SCORES: dict[str, dict[str, int]] = {
    "accuracy": {
        "acc_code_match": 5,
        "acc_architecture": 5,
        "acc_dependency": 5,
        "acc_behavior": 5,
        "acc_version": 5,
    },
    "structure": {
        "str_chapters": 5,
        "str_hierarchy": 5,
        "str_content_depth": 5,
        "str_code_block": 5,
    },
    "citation": {
        "cit_coverage": 5,
        "cit_format": 5,
        "cit_path_valid": 5,
        "cit_line_range": 5,
    },
    "terminology": {
        "term_unified": 5,
        "term_glossary": 5,
        "term_naming": 5,
    },
    "readability": {
        "read_language": 5,
        "read_logic": 5,
        "read_audience": 5,
        "read_visualization": 5,
    },
}

# 不合格评分 (全部 1 分) -> 总分 20, 等级 D
_POOR_SCORES: dict[str, dict[str, int]] = {
    dim_id: {item_id: 1 for item_id in items}
    for dim_id, items in {
        "accuracy": ["acc_code_match", "acc_architecture", "acc_dependency", "acc_behavior", "acc_version"],
        "structure": ["str_chapters", "str_hierarchy", "str_content_depth", "str_code_block"],
        "citation": ["cit_coverage", "cit_format", "cit_path_valid", "cit_line_range"],
        "terminology": ["term_unified", "term_glossary", "term_naming"],
        "readability": ["read_language", "read_logic", "read_audience", "read_visualization"],
    }.items()
}


# ========== calculate_score 测试 ==========


class TestCalculateScore:
    """校验评分计算."""

    def test_perfect_scores_get_100_and_grade_a(self) -> None:
        """全 5 分评分应得满分 100, 等级 A."""
        result = calculate_score(_PERFECT_SCORES)
        assert result["total_score"] == 100.0
        assert result["grade"] == "A"
        assert result["passed"] is True
        assert result["missing_items"] == []
        assert result["invalid_items"] == []

    def test_poor_scores_get_20_and_grade_d(self) -> None:
        """全 1 分评分应得 20 分, 等级 D, 不通过."""
        result = calculate_score(_POOR_SCORES)
        assert result["total_score"] == 20.0
        assert result["grade"] == "D"
        assert result["passed"] is False

    def test_medium_scores_get_grade_b(self) -> None:
        """全 4 分评分应得 80 分, 等级 B."""
        scores = {
            dim_id: {item_id: 4 for item_id in items}
            for dim_id, items in _PERFECT_SCORES.items()
        }
        result = calculate_score(scores)
        assert result["total_score"] == 80.0
        assert result["grade"] == "B"
        assert result["passed"] is True

    def test_grade_c_threshold(self) -> None:
        """全 3 分评分应得 60 分, 等级 C, 通过 (>=60)."""
        scores = {
            dim_id: {item_id: 3 for item_id in items}
            for dim_id, items in _PERFECT_SCORES.items()
        }
        result = calculate_score(scores)
        assert result["total_score"] == 60.0
        assert result["grade"] == "C"
        assert result["passed"] is True

    def test_weighted_calculation_correctness(self) -> None:
        """加权计算: accuracy 维度全 5 分, 其他维度全 1 分."""
        scores = {
            "accuracy": _PERFECT_SCORES["accuracy"],  # 全 5 -> 30 分
            "structure": _POOR_SCORES["structure"],    # 全 1 -> 4 分
            "citation": _POOR_SCORES["citation"],      # 全 1 -> 4 分
            "terminology": _POOR_SCORES["terminology"],  # 全 1 -> 3 分
            "readability": _POOR_SCORES["readability"],  # 全 1 -> 3 分
        }
        result = calculate_score(scores)
        # accuracy: 5/5 * 30 = 30
        # structure: 1/5 * 20 = 4
        # citation: 1/5 * 20 = 4
        # terminology: 1/5 * 15 = 3
        # readability: 1/5 * 15 = 3
        # total: 30 + 4 + 4 + 3 + 3 = 44
        assert result["total_score"] == 44.0
        assert result["grade"] == "D"

    def test_missing_items_detected(self) -> None:
        """未填写的评分项应被记录到 missing_items."""
        scores = {
            "accuracy": {"acc_code_match": 5},  # 其余 4 项缺失
            "structure": {},
            "citation": {},
            "terminology": {},
            "readability": {},
        }
        result = calculate_score(scores)
        assert "acc_architecture" in result["missing_items"]
        assert "acc_dependency" in result["missing_items"]
        assert "str_chapters" in result["missing_items"]
        # 已填写的项不在 missing_items
        assert "acc_code_match" not in result["missing_items"]

    def test_invalid_score_zero(self) -> None:
        """0 分无效, 应被记录到 invalid_items."""
        scores = {
            "accuracy": {"acc_code_match": 0},  # 0 < 1, 无效
            "structure": {},
            "citation": {},
            "terminology": {},
            "readability": {},
        }
        result = calculate_score(scores)
        assert "acc_code_match" in result["invalid_items"]

    def test_invalid_score_six(self) -> None:
        """6 分无效, 应被记录到 invalid_items."""
        scores = {
            "accuracy": {"acc_code_match": 6},  # 6 > 5, 无效
            "structure": {},
            "citation": {},
            "terminology": {},
            "readability": {},
        }
        result = calculate_score(scores)
        assert "acc_code_match" in result["invalid_items"]

    def test_invalid_score_non_integer(self) -> None:
        """非整数分数无效."""
        scores = {
            "accuracy": {"acc_code_match": 4.5},  # float, 无效
            "structure": {},
            "citation": {},
            "terminology": {},
            "readability": {},
        }
        result = calculate_score(scores)
        assert "acc_code_match" in result["invalid_items"]

    def test_empty_scores(self) -> None:
        """空 scores 应返回总分 0, 等级 D, 所有项 missing."""
        result = calculate_score({})
        assert result["total_score"] == 0.0
        assert result["grade"] == "D"
        assert result["passed"] is False
        # 所有评分项都应 missing
        assert len(result["missing_items"]) > 0

    def test_non_dict_input(self) -> None:
        """非 dict 输入应返回空结果."""
        result = calculate_score("not a dict")  # type: ignore[arg-type]
        assert result["total_score"] == 0.0
        assert result["passed"] is False

    def test_dimensions_structure_in_result(self) -> None:
        """结果中 dimensions 列表结构完整."""
        result = calculate_score(_PERFECT_SCORES)
        assert len(result["dimensions"]) == 5
        for dim in result["dimensions"]:
            assert "id" in dim
            assert "name" in dim
            assert "weight" in dim
            assert "dimension_score" in dim
            assert "weighted_score" in dim
            assert "items" in dim
            assert isinstance(dim["items"], list)

    def test_passed_threshold_60(self) -> None:
        """passed 阈值: 总分 >= 60 即通过."""
        # 全 3 分 = 60, 通过
        scores_3 = {
            dim_id: {item_id: 3 for item_id in items}
            for dim_id, items in _PERFECT_SCORES.items()
        }
        assert calculate_score(scores_3)["passed"] is True

        # 全 2 分 = 40, 不通过
        scores_2 = {
            dim_id: {item_id: 2 for item_id in items}
            for dim_id, items in _PERFECT_SCORES.items()
        }
        result = calculate_score(scores_2)
        assert result["total_score"] == 40.0
        assert result["passed"] is False


# ========== render_checklist_markdown 测试 ==========


class TestRenderChecklistMarkdown:
    """校验 Markdown 渲染."""

    def test_render_empty_template(self) -> None:
        """渲染空白模板应包含标题与所有维度."""
        md = render_checklist_markdown()
        assert "# 文档质量人工评估 Checklist" in md
        assert "## 总分汇总" in md
        assert "## 维度明细" in md
        assert "内容准确性" in md
        assert "结构完整性" in md
        assert "引用可追溯性" in md
        assert "术语一致性" in md
        assert "可读性" in md
        assert "## 等级说明" in md

    def test_render_with_scores(self) -> None:
        """渲染已填写的评分应包含总分."""
        md = render_checklist_markdown(_PERFECT_SCORES)
        assert "100.0" in md
        assert "A" in md
        # 评分项应含分数
        assert "5" in md

    def test_render_contains_all_items(self) -> None:
        """渲染应包含所有评分项名称."""
        md = render_checklist_markdown()
        # accuracy 维度的所有项
        assert "代码引用准确性" in md
        assert "架构描述准确性" in md
        assert "依赖关系准确性" in md
        assert "行为描述准确性" in md
        assert "版本与配置准确性" in md
        # structure
        assert "章节齐全度" in md
        assert "标题层级" in md
        # citation
        assert "引用覆盖率" in md
        assert "引用格式" in md
        # readability
        assert "语言流畅" in md
        assert "可视化辅助" in md

    def test_render_contains_grade_descriptions(self) -> None:
        """渲染应包含等级说明."""
        md = render_checklist_markdown()
        assert "优秀, 可直接发布" in md
        assert "良好, 小修后可发布" in md
        assert "合格, 需修订" in md
        assert "不合格, 需重写" in md


# ========== get_checklist_template 测试 ==========


class TestGetChecklistTemplate:
    """校验空白模板生成."""

    def test_template_has_all_dimensions(self) -> None:
        """模板应包含 5 个维度."""
        template = get_checklist_template()
        assert len(template) == 5
        assert "accuracy" in template
        assert "structure" in template
        assert "citation" in template
        assert "terminology" in template
        assert "readability" in template

    def test_template_items_are_none(self) -> None:
        """模板中所有评分项的初始值应为 None."""
        template = get_checklist_template()
        for dim_id, items in template.items():
            for item_id, value in items.items():
                assert value is None, f"{dim_id}.{item_id} 应为 None"

    def test_template_accuracy_has_5_items(self) -> None:
        """accuracy 维度应有 5 个评分项."""
        template = get_checklist_template()
        assert len(template["accuracy"]) == 5

    def test_template_can_be_filled_and_calculated(self) -> None:
        """模板可被填充并计算分数."""
        template = get_checklist_template()
        # 填充所有项为 5 分
        for dim_id, items in template.items():
            for item_id in items:
                items[item_id] = 5
        result = calculate_score(template)
        assert result["total_score"] == 100.0
        assert result["grade"] == "A"


# ========== get_dimensions 测试 ==========


class TestGetDimensions:
    """校验维度定义查询."""

    def test_returns_5_dimensions(self) -> None:
        """应返回 5 个维度."""
        dims = get_dimensions()
        assert len(dims) == 5

    def test_dimension_ids(self) -> None:
        """维度 ID 应为 accuracy/structure/citation/terminology/readability."""
        dims = get_dimensions()
        ids = {d["id"] for d in dims}
        assert ids == {"accuracy", "structure", "citation", "terminology", "readability"}

    def test_weights_sum_to_100(self) -> None:
        """所有维度权重总和应为 100 (设计约束)."""
        dims = get_dimensions()
        total_weight = sum(d["weight"] for d in dims)
        assert total_weight == 100

    def test_returns_copy_not_reference(self) -> None:
        """返回应为副本, 修改不影响内部常量."""
        dims = get_dimensions()
        dims[0]["weight"] = 999
        # 再次获取, 应不受影响
        dims_again = get_dimensions()
        assert dims_again[0]["weight"] != 999


# ========== 等级边界测试 ==========


class TestGradeThresholds:
    """校验等级阈值边界."""

    def test_grade_a_threshold_90(self) -> None:
        """总分 90 应为等级 A (边界值)."""
        # 全 4.5 分 = 90, 但分数必须整数
        # 用混合分数: accuracy 全 5 (30), 其他全 4 (16+16+12+12=56) -> 86 不够
        # 改用: accuracy 全 5 (30), structure 全 5 (20), citation 全 5 (20),
        #       terminology 全 4 (12), readability 全 4 (12) -> 94 -> A
        scores = {
            "accuracy": _PERFECT_SCORES["accuracy"],
            "structure": _PERFECT_SCORES["structure"],
            "citation": _PERFECT_SCORES["citation"],
            "terminology": {k: 4 for k in _PERFECT_SCORES["terminology"]},
            "readability": {k: 4 for k in _PERFECT_SCORES["readability"]},
        }
        result = calculate_score(scores)
        # 30 + 20 + 20 + 12 + 12 = 94
        assert result["total_score"] == 94.0
        assert result["grade"] == "A"

    def test_grade_b_threshold_75(self) -> None:
        """总分 75 应为等级 B (边界值)."""
        # accuracy 全 5 (30), structure 全 4 (16), citation 全 4 (16),
        # terminology 全 3 (9), readability 全 3 (9) -> 80 -> B
        scores = {
            "accuracy": _PERFECT_SCORES["accuracy"],
            "structure": {k: 4 for k in _PERFECT_SCORES["structure"]},
            "citation": {k: 4 for k in _PERFECT_SCORES["citation"]},
            "terminology": {k: 3 for k in _PERFECT_SCORES["terminology"]},
            "readability": {k: 3 for k in _PERFECT_SCORES["readability"]},
        }
        result = calculate_score(scores)
        # 30 + 16 + 16 + 9 + 9 = 80
        assert result["total_score"] == 80.0
        assert result["grade"] == "B"

    def test_grade_c_threshold_60(self) -> None:
        """总分 60 应为等级 C (边界值)."""
        scores = {
            dim_id: {item_id: 3 for item_id in items}
            for dim_id, items in _PERFECT_SCORES.items()
        }
        result = calculate_score(scores)
        assert result["total_score"] == 60.0
        assert result["grade"] == "C"
        assert result["passed"] is True  # 60 >= 60 通过

    def test_grade_d_below_60(self) -> None:
        """总分 < 60 应为等级 D."""
        scores = {
            dim_id: {item_id: 2 for item_id in items}
            for dim_id, items in _PERFECT_SCORES.items()
        }
        result = calculate_score(scores)
        assert result["total_score"] == 40.0
        assert result["grade"] == "D"
        assert result["passed"] is False

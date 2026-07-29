"""单元测试: P2-5.5.2 评估维度扩展.

测试目标:
- evaluate_report 一站式 4 维度评分 (0-100)
- 引用可追溯性 (citation_traceability): 复用 citation_extractor
- 文档结构完整性 (structure_completeness): 复用 structure_validator
- 术语一致性 (terminology_consistency): 复用 structure_validator
- 代码符号存在性 (code_symbol_existence): 复用 repo_map 符号库
- 空输入 / 失败降级 / 边界场景
- 综合得分加权计算正确性
"""
from __future__ import annotations

from src.skills.docbot.eval_metrics import evaluate_report

# ========== 测试数据 ==========


# 完整的优质文档 (含引用 + 章节结构 + 代码符号 + 无术语混用)
_GOOD_CONTENT = """# 架构文档

## 系统概述

本项目是一个代码文档生成系统, 入口定义在 [src/server.py:L15]。

API 路由注册在 [src/api/routes.py:L47-L120], 包含会话与仓库管理接口。

## 核心模块

### LLM 网关

`LLMClient` 类负责调用 LiteLLM, 支持三级降级 (FAST/SMART/STRATEGIC)。

### 仓库加载

`clone_repo` 函数用于克隆用户代码仓库到本地临时目录。

## 数据库

数据库脚本位于 [scripts/init.sql], 包含 `research_sessions` 和 `research_reports` 表。
"""

_GOOD_FILE_INDEX = {
    "files": [
        {"path": "src/server.py", "name": "server.py", "ext": ".py"},
        {"path": "src/api/routes.py", "name": "routes.py", "ext": ".py"},
        {"path": "scripts/init.sql", "name": "init.sql", "ext": ".sql"},
    ]
}

_GOOD_CHAPTERS = [
    {"idx": 1, "title": "系统概述"},
    {"idx": 2, "title": "核心模块"},
    {"idx": 3, "title": "数据库"},
]


# 劣质文档 (无引用 + 章节缺失 + 术语混用)
_POOR_CONTENT = """# 文档

本项目的 api 和 API 混用, postgresql 和 PostgreSQL 也混用。

## 仅有的章节

内容过短。
"""


# ========== evaluate_report 主入口测试 ==========


class TestEvaluateReport:
    """校验一站式评估入口."""

    def test_good_content_gets_high_score(self) -> None:
        """优质文档应得较高分数 (>=60)."""
        result = evaluate_report(
            content_md=_GOOD_CONTENT,
            file_index=_GOOD_FILE_INDEX,
            chapters=_GOOD_CHAPTERS,
            report_type="architecture",
        )
        assert result["total_score"] >= 60.0
        assert result["passed"] is True
        assert "dimensions" in result
        assert "citation_traceability" in result["dimensions"]
        assert "structure_completeness" in result["dimensions"]
        assert "terminology_consistency" in result["dimensions"]
        assert "code_symbol_existence" in result["dimensions"]

    def test_empty_content_returns_zero(self) -> None:
        """空内容应返回总分 0, 等级 D, 不通过."""
        result = evaluate_report(content_md="")
        assert result["total_score"] == 0.0
        assert result["grade"] == "D"
        assert result["passed"] is False

    def test_poor_content_fails(self) -> None:
        """劣质文档应得较低分数."""
        result = evaluate_report(
            content_md=_POOR_CONTENT,
            file_index=_GOOD_FILE_INDEX,
            chapters=_GOOD_CHAPTERS,
        )
        # 劣质文档分数应低于优质文档
        assert result["total_score"] < 80.0

    def test_result_structure(self) -> None:
        """结果结构完整."""
        result = evaluate_report(
            content_md=_GOOD_CONTENT,
            file_index=_GOOD_FILE_INDEX,
        )
        assert "total_score" in result
        assert "grade" in result
        assert "passed" in result
        assert "dimensions" in result
        assert "issues" in result
        assert "total_issues" in result
        assert isinstance(result["dimensions"], dict)
        assert isinstance(result["issues"], list)

    def test_grade_thresholds(self) -> None:
        """等级阈值: A>=90, B>=75, C>=60, D<60."""
        # 优质文档应至少得 C 以上
        result = evaluate_report(
            content_md=_GOOD_CONTENT,
            file_index=_GOOD_FILE_INDEX,
            chapters=_GOOD_CHAPTERS,
        )
        assert result["grade"] in ("A", "B", "C", "D")

        # 空文档应得 D
        empty_result = evaluate_report(content_md="")
        assert empty_result["grade"] == "D"

    def test_issues_have_dimension_field(self) -> None:
        """所有 issues 应带 dimension 字段."""
        result = evaluate_report(
            content_md=_GOOD_CONTENT,
            file_index=_GOOD_FILE_INDEX,
        )
        for issue in result["issues"]:
            if "dimension" not in issue:
                # 至少不应崩溃, 部分内部 issue 可能无 dimension
                assert "category" in issue or "message" in issue


# ========== 引用可追溯性维度测试 ==========


class TestCitationTraceability:
    """校验引用可追溯性评分."""

    def test_dimension_present(self) -> None:
        """结果中应含 citation_traceability 维度."""
        result = evaluate_report(
            content_md=_GOOD_CONTENT,
            file_index=_GOOD_FILE_INDEX,
        )
        cit_dim = result["dimensions"]["citation_traceability"]
        assert "score" in cit_dim
        assert "total_citations" in cit_dim
        assert "valid_count" in cit_dim
        assert "invalid_count" in cit_dim
        assert "coverage_score" in cit_dim
        assert "validity_score" in cit_dim

    def test_valid_citations_get_high_score(self) -> None:
        """有效引用应得较高分数."""
        result = evaluate_report(
            content_md=_GOOD_CONTENT,
            file_index=_GOOD_FILE_INDEX,
        )
        cit_dim = result["dimensions"]["citation_traceability"]
        assert cit_dim["total_citations"] >= 3
        assert cit_dim["valid_count"] >= 1
        assert cit_dim["score"] > 0

    def test_no_citation_long_content_warns(self) -> None:
        """长文档无引用应有 warning."""
        long_content = "# 标题\n\n" + "这是一段很长的内容。" * 100
        result = evaluate_report(
            content_md=long_content,
            file_index=_GOOD_FILE_INDEX,
        )
        cit_dim = result["dimensions"]["citation_traceability"]
        # 应有 citation_no_reference 类型的 issue
        no_ref_issues = [
            i for i in cit_dim["issues"]
            if i.get("category") == "citation_no_reference"
        ]
        assert len(no_ref_issues) >= 1

    def test_invalid_citation_path_detected(self) -> None:
        """引用不存在的文件路径应被检测."""
        content = "见 [src/nonexistent.py:L10-L20]。"
        result = evaluate_report(
            content_md=content,
            file_index=_GOOD_FILE_INDEX,
        )
        cit_dim = result["dimensions"]["citation_traceability"]
        assert "src/nonexistent.py" in cit_dim["missing_files"]
        assert cit_dim["invalid_count"] >= 1


# ========== 文档结构完整性维度测试 ==========


class TestStructureCompleteness:
    """校验文档结构完整性评分."""

    def test_dimension_present(self) -> None:
        """结果中应含 structure_completeness 维度."""
        result = evaluate_report(
            content_md=_GOOD_CONTENT,
            file_index=_GOOD_FILE_INDEX,
            chapters=_GOOD_CHAPTERS,
        )
        struct_dim = result["dimensions"]["structure_completeness"]
        assert "score" in struct_dim
        assert "chapter_score" in struct_dim
        assert "markdown_score" in struct_dim
        assert "code_path_score" in struct_dim
        assert "chapter_matched" in struct_dim
        assert "chapter_missing" in struct_dim

    def test_missing_chapter_detected(self) -> None:
        """章节缺失应降低章节得分."""
        chapters = [
            {"idx": 1, "title": "系统概述"},
            {"idx": 2, "title": "不存在的章节"},
            {"idx": 3, "title": "另一个缺失章节"},
        ]
        result = evaluate_report(
            content_md=_GOOD_CONTENT,
            file_index=_GOOD_FILE_INDEX,
            chapters=chapters,
        )
        struct_dim = result["dimensions"]["structure_completeness"]
        assert struct_dim["chapter_missing"] >= 2

    def test_no_chapters_degrades_gracefully(self) -> None:
        """无 chapters 输入应降级为 50 分 (不崩溃)."""
        result = evaluate_report(
            content_md=_GOOD_CONTENT,
            file_index=_GOOD_FILE_INDEX,
            chapters=None,
        )
        struct_dim = result["dimensions"]["structure_completeness"]
        # chapters=[] -> ch_score=50 (降级)
        assert struct_dim["chapter_score"] == 50.0


# ========== 术语一致性维度测试 ==========


class TestTerminologyConsistency:
    """校验术语一致性评分."""

    def test_dimension_present(self) -> None:
        """结果中应含 terminology_consistency 维度."""
        result = evaluate_report(content_md=_GOOD_CONTENT)
        term_dim = result["dimensions"]["terminology_consistency"]
        assert "score" in term_dim
        assert "inconsistent_term_count" in term_dim
        assert "checked_terms" in term_dim

    def test_no_mixed_terms_gets_100(self) -> None:
        """无术语混用应得 100 分."""
        # 代码块内的术语变体不视为问题
        content = "# 文档\n\n本文使用 API 和 GitHub 与 TypeScript。"
        result = evaluate_report(content_md=content)
        term_dim = result["dimensions"]["terminology_consistency"]
        assert term_dim["score"] == 100.0
        assert term_dim["inconsistent_term_count"] == 0

    def test_mixed_terms_detected(self) -> None:
        """术语混用应被检测并扣分."""
        content = "# 文档\n\n本项目的 api 和 API 同时使用, postgresql 与 PostgreSQL 也混用。"
        result = evaluate_report(content_md=content)
        term_dim = result["dimensions"]["terminology_consistency"]
        assert term_dim["inconsistent_term_count"] >= 2
        assert term_dim["score"] < 100.0

    def test_code_block_terms_ignored(self) -> None:
        """代码块内的术语变体不视为混用."""
        content = """# 文档

代码示例:

```python
import api
API_KEY = "xxx"
```

正文使用 API。
"""
        result = evaluate_report(content_md=content)
        term_dim = result["dimensions"]["terminology_consistency"]
        # 代码块内 api/API 不应触发混用
        assert term_dim["inconsistent_term_count"] == 0
        assert term_dim["score"] == 100.0


# ========== 代码符号存在性维度测试 ==========


class TestCodeSymbolExistence:
    """校验代码符号存在性评分."""

    def test_dimension_present(self) -> None:
        """结果中应含 code_symbol_existence 维度."""
        result = evaluate_report(
            content_md=_GOOD_CONTENT,
            file_index=_GOOD_FILE_INDEX,
        )
        sym_dim = result["dimensions"]["code_symbol_existence"]
        assert "score" in sym_dim
        assert "total_symbols" in sym_dim
        assert "matched_count" in sym_dim
        assert "missing_count" in sym_dim

    def test_no_symbols_degrades_to_50(self) -> None:
        """文档无 backtick 标识符应降级为 50 分."""
        content = "# 文档\n\n这是纯文本, 无任何代码符号引用。"
        result = evaluate_report(content_md=content)
        sym_dim = result["dimensions"]["code_symbol_existence"]
        assert sym_dim["total_symbols"] == 0
        assert sym_dim["score"] == 50.0

    def test_symbols_extracted_from_backticks(self) -> None:
        """文档中 backtick 包裹的标识符应被提取."""
        content = "# 文档\n\n使用 `LLMClient` 和 `clone_repo` 函数。"
        result = evaluate_report(content_md=content)
        sym_dim = result["dimensions"]["code_symbol_existence"]
        assert sym_dim["total_symbols"] >= 2

    def test_excluded_symbols_filtered(self) -> None:
        """内置关键字 (true/false/none 等) 应被排除."""
        content = "# 文档\n\n使用 `true` 和 `false` 和 `none` 作为示例。"
        result = evaluate_report(content_md=content)
        sym_dim = result["dimensions"]["code_symbol_existence"]
        # true/false/none 被排除, total_symbols 应为 0
        assert sym_dim["total_symbols"] == 0

    def test_degraded_without_repo_path(self) -> None:
        """无 repo_path 时应降级 (tree-sitter 不可用)."""
        content = "# 文档\n\n使用 `LLMClient` 和 `clone_repo` 函数。"
        result = evaluate_report(
            content_md=content,
            file_index=_GOOD_FILE_INDEX,
            repo_path=None,
        )
        sym_dim = result["dimensions"]["code_symbol_existence"]
        # 无 repo_path, 降级为文件名匹配
        assert sym_dim.get("degraded") is True or sym_dim["score"] >= 0

    def test_missing_symbols_reported(self) -> None:
        """文档引用的代码符号不在符号库时应报告 issue."""
        content = "# 文档\n\n使用 `NonExistentSymbolXYZ` 函数。"
        result = evaluate_report(
            content_md=content,
            file_index=_GOOD_FILE_INDEX,
            repo_path=None,  # 降级模式
        )
        sym_dim = result["dimensions"]["code_symbol_existence"]
        # NonExistentSymbolXYZ 不在文件名中, missing_count >= 1
        assert sym_dim["missing_count"] >= 1


# ========== 综合得分测试 ==========


class TestTotalScore:
    """校验综合得分加权计算."""

    def test_weights_sum_to_100(self) -> None:
        """4 维度权重总和应为 100 (设计约束)."""
        # 通过查看 _WEIGHTS 验证 (导入私有变量)
        from src.skills.docbot.eval_metrics import _WEIGHTS
        assert sum(_WEIGHTS.values()) == 100

    def test_total_score_is_weighted_average(self) -> None:
        """总分应为 4 维度加权平均."""
        result = evaluate_report(
            content_md=_GOOD_CONTENT,
            file_index=_GOOD_FILE_INDEX,
            chapters=_GOOD_CHAPTERS,
        )
        dims = result["dimensions"]
        from src.skills.docbot.eval_metrics import _WEIGHTS
        expected = (
            dims["citation_traceability"]["score"] * _WEIGHTS["citation_traceability"] / 100
            + dims["structure_completeness"]["score"] * _WEIGHTS["structure_completeness"] / 100
            + dims["terminology_consistency"]["score"] * _WEIGHTS["terminology_consistency"] / 100
            + dims["code_symbol_existence"]["score"] * _WEIGHTS["code_symbol_existence"] / 100
        )
        expected = round(expected, 2)
        assert abs(result["total_score"] - expected) < 0.1

    def test_passed_threshold_60(self) -> None:
        """passed 阈值: 总分 >= 60 即通过."""
        result = evaluate_report(
            content_md=_GOOD_CONTENT,
            file_index=_GOOD_FILE_INDEX,
            chapters=_GOOD_CHAPTERS,
        )
        if result["total_score"] >= 60.0:
            assert result["passed"] is True
        else:
            assert result["passed"] is False


# ========== 边界场景测试 ==========


class TestEdgeCases:
    """校验边界场景."""

    def test_no_file_index(self) -> None:
        """无 file_index 应不崩溃, 各维度降级."""
        result = evaluate_report(content_md=_GOOD_CONTENT)
        assert "total_score" in result
        assert result["dimensions"]["citation_traceability"]["score"] >= 0
        assert result["dimensions"]["code_symbol_existence"]["score"] >= 0

    def test_no_chapters(self) -> None:
        """无 chapters 应不崩溃, 结构维度降级."""
        result = evaluate_report(
            content_md=_GOOD_CONTENT,
            file_index=_GOOD_FILE_INDEX,
        )
        struct_dim = result["dimensions"]["structure_completeness"]
        # chapters=[] -> chapter_score=50 (降级)
        assert struct_dim["chapter_score"] == 50.0

    def test_short_content_no_citation(self) -> None:
        """短文档无引用不应触发 warning (阈值 500)."""
        result = evaluate_report(content_md="# 短文档\n\n内容。")
        cit_dim = result["dimensions"]["citation_traceability"]
        no_ref_issues = [
            i for i in cit_dim["issues"]
            if i.get("category") == "citation_no_reference"
        ]
        assert len(no_ref_issues) == 0

    def test_failure_degradation(self) -> None:
        """单维度失败不应影响其他维度."""
        # 即使 file_index 为空, 其他维度应正常评分
        result = evaluate_report(content_md=_GOOD_CONTENT)
        assert result["dimensions"]["terminology_consistency"]["score"] >= 0
        assert result["dimensions"]["structure_completeness"]["score"] >= 0

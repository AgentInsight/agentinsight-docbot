"""单元测试: CODE_LEARNING 按 report_type 侧重切换 (P0).

验收标准 (optimization-plan-code-learning-v1 §7.2):
1. Prompt 格式化后只出现当前类型侧重词, 不出现其它类型标题行
2. select_key_files 按类型偏向不同路径
3. learn_code 解析透传类型专属字段, 公共四字段仍在
"""

from __future__ import annotations

from src.config.docbot.learning_focus import (
    LEARNING_FOCUS_BY_TYPE,
    LEARNING_SCHEMA_VERSION,
    extract_type_specific_fields,
    format_extra_schema,
    format_learning_focus,
)
from src.config.docbot.prompts import CODE_LEARNING_PROMPT
from src.skills.docbot.code_learner import _parse_learning_response
from src.skills.docbot.repo_loader import select_key_files


def _format_prompt(report_type: str) -> str:
    """用最小占位填充 CODE_LEARNING_PROMPT."""
    return CODE_LEARNING_PROMPT.format(
        report_type=report_type,
        role_name="测试角色",
        description="测试描述",
        learning_focus=format_learning_focus(report_type),
        output_schema_extra=format_extra_schema(report_type),
        file_index="文件总数: 1",
        file_contents="",
        repo_map="",
        code_graph="",
        project_metadata_text="",
        glossary_text="",
        endpoints_text="",
        enums_text="",
        config_specs_text="",
        scopes_text="",
    )


class TestLearningFocusPromptSlice:
    """P0-A: Prompt 侧重真正切换."""

    def test_all_eight_types_defined(self) -> None:
        expected = {
            "architecture",
            "design",
            "requirements",
            "testcase",
            "optimization",
            "performance",
            "defect",
            "api_doc",
        }
        assert set(LEARNING_FOCUS_BY_TYPE.keys()) == expected

    def test_prompt_contains_only_current_type_focus(self) -> None:
        # 其它类型的「标题行」形态 (旧全量清单特征)
        foreign_headers = {
            "architecture": "architecture (技术架构):",
            "design": "design (概要设计):",
            "requirements": "requirements (需求):",
            "testcase": "testcase (测试用例):",
            "optimization": "optimization (系统优化):",
            "performance": "performance (性能分析):",
            "defect": "defect (系统缺陷):",
            "api_doc": "api_doc (API 文档):",
        }
        for report_type in LEARNING_FOCUS_BY_TYPE:
            prompt = _format_prompt(report_type)
            assert f"当前报告类型: {report_type}" in prompt
            # 当前类型维度词应出现
            for dim in LEARNING_FOCUS_BY_TYPE[report_type]["dimensions"][:2]:
                assert dim in prompt, f"{report_type} 缺少维度 {dim}"
            # 禁止出现其它类型的旧式全量清单标题行
            for other, header in foreign_headers.items():
                if other == report_type:
                    continue
                assert header not in prompt, (
                    f"{report_type} prompt 不应含其它类型标题行: {header}"
                )

    def test_hard_constraint_present(self) -> None:
        prompt = _format_prompt("testcase")
        assert "万能架构摘要" in prompt
        assert "必覆盖检查清单" in prompt

    def test_extra_schema_injected_for_api_doc(self) -> None:
        prompt = _format_prompt("api_doc")
        assert "auth_model" in prompt
        assert "error_code_index" in prompt
        assert "versioning_notes" in prompt

    def test_extra_schema_injected_for_testcase(self) -> None:
        prompt = _format_prompt("testcase")
        assert "test_points" in prompt
        assert "coverage_gaps" in prompt


class TestSelectKeyFilesByReportType:
    """P0-B: 按 report_type 选择关键文件."""

    @staticmethod
    def _fixture_index() -> dict:
        files = [
            {"path": "README.md", "name": "README.md", "ext": ".md", "size": 100},
            {
                "path": "src/api/UserController.py",
                "name": "UserController.py",
                "ext": ".py",
                "size": 200,
            },
            {
                "path": "src/routers/orders_router.py",
                "name": "orders_router.py",
                "ext": ".py",
                "size": 200,
            },
            {
                "path": "tests/test_orders.py",
                "name": "test_orders.py",
                "ext": ".py",
                "size": 150,
            },
            {
                "path": "tests/unit/test_api.py",
                "name": "test_api.py",
                "ext": ".py",
                "size": 150,
            },
            {
                "path": "src/utils/helpers.py",
                "name": "helpers.py",
                "ext": ".py",
                "size": 80,
            },
            {
                "path": "docker-compose.yml",
                "name": "docker-compose.yml",
                "ext": ".yml",
                "size": 50,
            },
            {
                "path": "src/models/user.py",
                "name": "user.py",
                "ext": ".py",
                "size": 90,
            },
        ]
        return {"files": files, "file_count": len(files)}

    def test_api_doc_prefers_controllers_over_tests(self) -> None:
        idx = self._fixture_index()
        api_files = select_key_files(idx, max_files=5, report_type="api_doc")
        test_files = select_key_files(idx, max_files=5, report_type="testcase")
        api_ctrl = sum(
            1
            for p in api_files
            if "controller" in p.lower() or "router" in p.lower()
        )
        test_ctrl = sum(
            1
            for p in test_files
            if "controller" in p.lower() or "router" in p.lower()
        )
        api_tests = sum(1 for p in api_files if "tests/" in p.replace("\\", "/"))
        test_tests = sum(1 for p in test_files if "tests/" in p.replace("\\", "/"))
        assert api_ctrl >= test_ctrl
        assert test_tests > api_tests

    def test_architecture_includes_compose(self) -> None:
        idx = self._fixture_index()
        files = select_key_files(idx, max_files=8, report_type="architecture")
        assert any("docker-compose" in p.lower() for p in files)


class TestTypeSpecificSchemaParse:
    """P0-C: 扩展 JSON schema 向后兼容."""

    def test_schema_version_constant(self) -> None:
        assert LEARNING_SCHEMA_VERSION == "v2"

    def test_extract_type_specific_api_doc(self) -> None:
        parsed = {
            "summary": "s",
            "key_modules": [],
            "dependencies": [],
            "architecture_notes": "n",
            "auth_model": "Bearer JWT",
            "error_code_index": [{"code": "4001", "meaning": "bad", "evidence": "a.py:1"}],
            "versioning_notes": "insufficient_evidence",
        }
        extra = extract_type_specific_fields("api_doc", parsed)
        assert extra["auth_model"] == "Bearer JWT"
        assert len(extra["error_code_index"]) == 1
        assert "versioning_notes" in extra

    def test_extract_type_specific_testcase(self) -> None:
        parsed = {
            "summary": "s",
            "test_points": [{"target": "f", "scenario": "x", "boundary": "", "evidence": "t.py:1"}],
            "coverage_gaps": [],
        }
        extra = extract_type_specific_fields("testcase", parsed)
        assert len(extra["test_points"]) == 1
        assert extra["coverage_gaps"] == []

    def test_parse_keeps_common_fields(self) -> None:
        content = """{
          "summary": "整体摘要",
          "key_modules": [{"name": "m", "path": "a.py", "responsibility": "r"}],
          "dependencies": [{"from": "a", "to": "b", "type": "import"}],
          "architecture_notes": "notes",
          "test_points": [{"target": "x", "scenario": "y", "boundary": "", "evidence": "z.py:1"}]
        }"""
        parsed = _parse_learning_response(content)
        assert parsed["summary"] == "整体摘要"
        assert len(parsed["key_modules"]) == 1
        assert parsed["architecture_notes"] == "notes"
        assert "test_points" in parsed

"""单元测试: docbot 6 个 prompt 模板.

测试目标:
- 6 个 prompt 模板都非空
- get_prompt(task, ...) 不抛异常, 含传入的字段值
- get_prompt 未知 task 抛 ValueError

注意 (P0 修复后):
- 各 Agent 直接 import 模板常量并调用 .format() 传 kwargs (不通过 get_prompt)
- get_prompt() 是简化工具函数, 不自动注入 persona (由各 Agent 自行加载 persona 后传入)
- 模板占位符字段名与对应 Agent 的 .format() kwargs 严格对齐
"""
from __future__ import annotations

import pytest

from src.config.docbot.prompts import (
    CODE_LEARNING_PROMPT,
    CONTENT_FILL_PROMPT,
    FINAL_REVIEW_PROMPT,
    MERGE_PROMPT,
    OUTLINE_REFINE_PROMPT,
    REVIEW_PROMPT,
    # 向后兼容别名
    CODE_LEARNER_PROMPT_ZH,
    CONTENT_FILLER_PROMPT_ZH,
    FINAL_REVIEWER_PROMPT_ZH,
    MERGER_PROMPT_ZH,
    OUTLINE_REFINER_PROMPT_ZH,
    REVIEWER_PROMPT_ZH,
    get_prompt,
)

# 6 个 prompt 模板 (新命名, 与 Agent import 一致)
_ALL_TEMPLATES = [
    ("code_learner", CODE_LEARNING_PROMPT),
    ("outline_refiner", OUTLINE_REFINE_PROMPT),
    ("content_filler", CONTENT_FILL_PROMPT),
    ("reviewer", REVIEW_PROMPT),
    ("merger", MERGE_PROMPT),
    ("final_reviewer", FINAL_REVIEW_PROMPT),
]

# 向后兼容别名应等于新常量
_ALIAS_PAIRS = [
    (CODE_LEARNER_PROMPT_ZH, CODE_LEARNING_PROMPT),
    (OUTLINE_REFINER_PROMPT_ZH, OUTLINE_REFINE_PROMPT),
    (CONTENT_FILLER_PROMPT_ZH, CONTENT_FILL_PROMPT),
    (REVIEWER_PROMPT_ZH, REVIEW_PROMPT),
    (MERGER_PROMPT_ZH, MERGE_PROMPT),
    (FINAL_REVIEWER_PROMPT_ZH, FINAL_REVIEW_PROMPT),
]


class TestPromptTemplates:
    """6 个 prompt 模板格式化测试."""

    @pytest.mark.parametrize("task,template", _ALL_TEMPLATES)
    def test_template_not_empty(self, task: str, template: str) -> None:
        """验证 6 个模板都非空."""
        assert template, f"模板 {task} 不能为空"
        assert len(template) > 50, f"模板 {task} 内容过短"

    @pytest.mark.parametrize("alias,new", _ALIAS_PAIRS)
    def test_alias_equals_new_constant(self, alias: str, new: str) -> None:
        """向后兼容别名应等于新常量."""
        assert alias == new, "别名 (*_ZH) 应指向新常量"

    def test_code_learning_prompt_placeholders(self) -> None:
        """CODE_LEARNING_PROMPT 含 report_type / file_index / file_contents 占位符."""
        assert "{report_type}" in CODE_LEARNING_PROMPT
        assert "{file_index}" in CODE_LEARNING_PROMPT
        assert "{file_contents}" in CODE_LEARNING_PROMPT

    def test_outline_refine_prompt_placeholders(self) -> None:
        """OUTLINE_REFINE_PROMPT 含 8 个占位符."""
        for ph in (
            "{role_name}", "{description}", "{report_type}", "{language}",
            "{default_outline}", "{code_summary}", "{key_modules}", "{dependencies}",
        ):
            assert ph in OUTLINE_REFINE_PROMPT, f"OUTLINE_REFINE_PROMPT 缺 {ph}"

    def test_content_fill_prompt_placeholders(self) -> None:
        """CONTENT_FILL_PROMPT 含 6 个占位符."""
        for ph in (
            "{chapter_title}", "{chapter_sections}", "{key_points}",
            "{language}", "{code_summary}", "{rag_context}",
        ):
            assert ph in CONTENT_FILL_PROMPT, f"CONTENT_FILL_PROMPT 缺 {ph}"

    def test_review_prompt_placeholders_and_output_fields(self) -> None:
        """REVIEW_PROMPT 含占位符 + 输出 JSON 字段 needs_revision/review_notes/revised_content."""
        for ph in (
            "{chapter_title}", "{chapter_sections}", "{key_points}",
            "{content}", "{code_summary}", "{language}",
        ):
            assert ph in REVIEW_PROMPT, f"REVIEW_PROMPT 缺 {ph}"
        assert "needs_revision" in REVIEW_PROMPT
        assert "review_notes" in REVIEW_PROMPT
        assert "revised_content" in REVIEW_PROMPT

    def test_merge_prompt_placeholders(self) -> None:
        """MERGE_PROMPT 含 4 个占位符."""
        for ph in ("{report_type}", "{language}", "{chapter_count}", "{all_content}"):
            assert ph in MERGE_PROMPT, f"MERGE_PROMPT 缺 {ph}"

    def test_final_review_prompt_placeholders_and_output_fields(self) -> None:
        """FINAL_REVIEW_PROMPT 含占位符 + 输出 JSON 字段 title/summary/content_md."""
        for ph in (
            "{role_name}", "{description}", "{report_type}", "{language}",
            "{merged_content}", "{code_summary}",
        ):
            assert ph in FINAL_REVIEW_PROMPT, f"FINAL_REVIEW_PROMPT 缺 {ph}"
        assert "title" in FINAL_REVIEW_PROMPT
        assert "summary" in FINAL_REVIEW_PROMPT
        assert "content_md" in FINAL_REVIEW_PROMPT


class TestGetPrompt:
    """get_prompt 函数测试 (不自动注入 persona, 由调用方传入)."""

    def test_get_prompt_code_learner(self) -> None:
        """get_prompt('code_learner', ...) 不抛异常."""
        prompt = get_prompt(
            "code_learner",
            report_type="architecture",
            file_index="file1.py\nfile2.py",
            file_contents="def hello(): pass",
            language="zh",
        )
        assert isinstance(prompt, str)
        assert "architecture" in prompt
        assert "file1.py" in prompt
        assert "def hello(): pass" in prompt
        # 不应残留未填充的占位符
        assert "{report_type}" not in prompt
        assert "{file_index}" not in prompt
        assert "{file_contents}" not in prompt

    def test_get_prompt_outline_refiner(self) -> None:
        """get_prompt('outline_refiner', ...) 不抛异常."""
        prompt = get_prompt(
            "outline_refiner",
            role_name="API 文档工程师",
            description="撰写 API 文档",
            report_type="api_doc",
            language="zh",
            default_outline="## 第1章 概述",
            code_summary="代码学习摘要",
            key_modules=["auth", "api"],
            dependencies=["fastapi", "pydantic"],
        )
        assert isinstance(prompt, str)
        assert "API 文档工程师" in prompt
        assert "代码学习摘要" in prompt
        assert "{role_name}" not in prompt

    def test_get_prompt_content_filler(self) -> None:
        """get_prompt('content_filler', ...) 不抛异常."""
        prompt = get_prompt(
            "content_filler",
            chapter_title="概述",
            chapter_sections=["背景", "目标"],
            key_points=["要点1"],
            language="zh",
            code_summary="代码摘要",
            rag_context="RAG 检索结果",
        )
        assert isinstance(prompt, str)
        assert "概述" in prompt
        assert "{chapter_title}" not in prompt

    def test_get_prompt_reviewer(self) -> None:
        """get_prompt('reviewer', ...) 不抛异常."""
        prompt = get_prompt(
            "reviewer",
            chapter_title="测试章节",
            chapter_sections=["小节1"],
            key_points=["要点1"],
            content="章节内容",
            code_summary="代码摘要",
            language="zh",
        )
        assert isinstance(prompt, str)
        assert "测试章节" in prompt
        assert "{chapter_title}" not in prompt

    def test_get_prompt_merger(self) -> None:
        """get_prompt('merger', ...) 不抛异常."""
        prompt = get_prompt(
            "merger",
            report_type="architecture",
            language="zh",
            chapter_count=10,
            all_content="章节内容",
        )
        assert isinstance(prompt, str)
        assert "章节内容" in prompt
        assert "{all_content}" not in prompt

    def test_get_prompt_final_reviewer(self) -> None:
        """get_prompt('final_reviewer', ...) 不抛异常."""
        prompt = get_prompt(
            "final_reviewer",
            role_name="技术架构师",
            description="撰写架构文档",
            report_type="architecture",
            language="zh",
            merged_content="合并内容",
            code_summary="代码摘要",
        )
        assert isinstance(prompt, str)
        assert "合并内容" in prompt
        assert "{merged_content}" not in prompt

    def test_get_prompt_unknown_task_raises(self) -> None:
        """get_prompt 未知 task 抛 ValueError."""
        with pytest.raises(ValueError, match="Unknown task"):
            get_prompt("unknown_task")

    def test_get_prompt_missing_kwarg_raises_key_error(self) -> None:
        """get_prompt 缺少占位符所需 kwarg 抛 KeyError."""
        with pytest.raises(KeyError):
            # CODE_LEARNING_PROMPT 需要 report_type / file_index / file_contents
            get_prompt("code_learner", report_type="architecture")

    def test_get_prompt_language_injected_by_default(self) -> None:
        """get_prompt 默认 language='zh' 自动注入到 {language} 占位符."""
        # REVIEW_PROMPT 含 {language} 占位符
        prompt = get_prompt(
            "reviewer",
            chapter_title="测试",
            chapter_sections=[],
            key_points=[],
            content="内容",
            code_summary="摘要",
        )
        assert "{language}" not in prompt
        assert "zh" in prompt

"""单元测试: D-E 修订循环守卫 (ReviewerE).

测试目标 (见 AGENTS.md 第 13 章关键测试用例 1):
- max_revisions_per_chapter=3 硬上限 (达上限时强制通过)
- ReviewerE._parse_review JSON 解析失败降级不修订
- ReviewerE._default_prompt 兜底
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.agents.docbot.reviewer import ReviewerE


class TestReviewerEParseReview:
    """_parse_review 静态方法测试."""

    def test_parse_valid_json_approved_false(self) -> None:
        """合法 JSON + needs_revision=False."""
        content = json.dumps(
            {
                "needs_revision": False,
                "review_notes": "内容完整",
                "revised_content": "# 修订后内容",
            }
        )
        result = ReviewerE._parse_review(content, "fallback")
        assert result["needs_revision"] is False
        assert result["review_notes"] == "内容完整"
        assert result["revised_content"] == "# 修订后内容"

    def test_parse_valid_json_approved_true(self) -> None:
        """合法 JSON + needs_revision=True."""
        content = json.dumps(
            {
                "needs_revision": True,
                "review_notes": "需要补充",
                "revised_content": "# 新内容",
            }
        )
        result = ReviewerE._parse_review(content, "fallback")
        assert result["needs_revision"] is True
        assert result["review_notes"] == "需要补充"

    def test_parse_invalid_json_falls_back(self) -> None:
        """非法 JSON 返回降级结果 (不修订)."""
        result = ReviewerE._parse_review("not json", "fallback_content")
        assert result["needs_revision"] is False
        assert "JSON 解析失败" in result["review_notes"]
        assert result["revised_content"] == "fallback_content"

    def test_parse_json_missing_fields(self) -> None:
        """JSON 缺字段时, 用默认值."""
        content = json.dumps({})
        result = ReviewerE._parse_review(content, "fallback")
        assert result["needs_revision"] is False  # bool(None) = False
        assert result["review_notes"] == ""
        assert result["revised_content"] == "fallback"

    def test_parse_non_dict_json_falls_back(self) -> None:
        """JSON 非 dict (如 list) 返回降级结果."""
        result = ReviewerE._parse_review("[1, 2, 3]", "fallback")
        assert result["needs_revision"] is False
        assert result["revised_content"] == "fallback"

    def test_parse_empty_string_falls_back(self) -> None:
        """空字符串返回降级结果."""
        result = ReviewerE._parse_review("", "fallback")
        assert result["needs_revision"] is False
        assert result["revised_content"] == "fallback"


class TestReviewerEDefaultPrompt:
    """_default_prompt 静态方法测试."""

    def test_default_prompt_contains_placeholders(self) -> None:
        """默认 prompt 含所有占位符."""
        prompt = ReviewerE._default_prompt()
        for placeholder in (
            "{chapter_title}",
            "{chapter_sections}",
            "{key_points}",
            "{content}",
            "{code_summary}",
            "{language}",
        ):
            assert placeholder in prompt, f"默认 prompt 缺占位符 {placeholder}"

    def test_default_prompt_can_format(self) -> None:
        """默认 prompt 可被 format."""
        prompt_template = ReviewerE._default_prompt()
        # 应能 format 不抛异常
        formatted = prompt_template.format(
            chapter_title="测试章节",
            chapter_sections=["section1"],
            key_points=["point1"],
            content="content",
            code_summary="summary",
            language="zh",
        )
        assert "测试章节" in formatted
        assert "section1" in formatted
        assert "point1" in formatted


class TestReviewerEMaxRevisions:
    """ReviewerE 修订循环硬上限测试 (达上限强制通过)."""

    @pytest.mark.asyncio
    async def test_revision_at_max_forces_pass(self, mock_settings: MagicMock) -> None:
        """revision_round >= max_revisions 时, needs_revision 强制为 False."""
        # mock LLM 客户端返回 needs_revision=True
        mock_llm = MagicMock()
        response = MagicMock()
        response.content = json.dumps(
            {
                "needs_revision": True,  # LLM 评审需要修订
                "review_notes": "需要补充",
                "revised_content": "# 修订内容",
            }
        )
        mock_llm.achat = AsyncMock(return_value=response)

        reviewer = ReviewerE(settings=mock_settings)
        reviewer.llm = mock_llm

        chapter = {"idx": 1, "title": "测试", "sections": [], "key_points": []}
        result = await reviewer.review_chapter(
            chapter=chapter,
            content={"content_md": "原始内容", "image_svgs": []},
            code_learning={"summary": "代码摘要"},
            report_type="architecture",
            language="zh",
            llm_session_id="session1",
            settings=mock_settings,
            revision_round=3,  # 已达上限
            max_revisions=3,
        )
        # 强制通过
        assert result["needs_revision"] is False
        assert result["content_md"] == "# 修订内容"

    @pytest.mark.asyncio
    async def test_revision_below_max_keeps_needs_revision(
        self, mock_settings: MagicMock
    ) -> None:
        """revision_round < max_revisions 时, 保留 LLM 评审结果."""
        mock_llm = MagicMock()
        response = MagicMock()
        response.content = json.dumps(
            {
                "needs_revision": True,  # LLM 评审需要修订
                "review_notes": "需要补充",
                "revised_content": "# 修订内容",
            }
        )
        mock_llm.achat = AsyncMock(return_value=response)

        reviewer = ReviewerE(settings=mock_settings)
        reviewer.llm = mock_llm

        chapter = {"idx": 1, "title": "测试", "sections": [], "key_points": []}
        result = await reviewer.review_chapter(
            chapter=chapter,
            content={"content_md": "原始内容", "image_svgs": []},
            code_learning={"summary": "代码摘要"},
            report_type="architecture",
            language="zh",
            llm_session_id="session1",
            settings=mock_settings,
            revision_round=1,  # 未达上限
            max_revisions=3,
        )
        # 保留 LLM 评审结果
        assert result["needs_revision"] is True

    @pytest.mark.asyncio
    async def test_revision_zero_keeps_needs_revision(
        self, mock_settings: MagicMock
    ) -> None:
        """revision_round=0 (未修订) 时保留 LLM 评审结果."""
        mock_llm = MagicMock()
        response = MagicMock()
        response.content = json.dumps(
            {
                "needs_revision": False,
                "review_notes": "OK",
                "revised_content": "# 内容",
            }
        )
        mock_llm.achat = AsyncMock(return_value=response)

        reviewer = ReviewerE(settings=mock_settings)
        reviewer.llm = mock_llm

        chapter = {"idx": 1, "title": "测试", "sections": [], "key_points": []}
        result = await reviewer.review_chapter(
            chapter=chapter,
            content={"content_md": "原始内容", "image_svgs": []},
            code_learning={"summary": "代码摘要"},
            report_type="architecture",
            language="zh",
            llm_session_id="session1",
            settings=mock_settings,
            revision_round=0,
            max_revisions=3,
        )
        assert result["needs_revision"] is False

"""单元测试: P2-5.4.1 多视角代码审问主模块.

测试目标:
- _parse_json_response: 三层降级 JSON 解析
- _format_perspective_qa: 多视角问答格式化与截断
- _load_perspectives: 失败降级到空列表
- learn_code_multi_perspective: 主流程 (mock LLM)
- 异常场景: 所有视角失败抛 RuntimeError
- _is_multi_perspective_enabled: settings 开关检测
- 新增 prompt 模板占位符填充
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.skills.docbot.code_graph import CodeGraph
from src.skills.docbot.code_learner import _is_multi_perspective_enabled
from src.skills.docbot.multi_perspective_learner import (
    _format_perspective_qa,
    _load_perspectives,
    _parse_json_response,
    learn_code_multi_perspective,
)

# ========== _parse_json_response 测试 ==========


class TestParseJsonResponse:
    """校验 LLM JSON 响应三层降级解析."""

    def test_valid_json(self) -> None:
        """合法 JSON 应直接解析."""
        content = '{"questions": ["q1", "q2"]}'
        result = _parse_json_response(content)
        assert result == {"questions": ["q1", "q2"]}

    def test_empty_content_returns_empty_dict(self) -> None:
        """空 content 应返回空 dict."""
        assert _parse_json_response("") == {}

    def test_markdown_code_block(self) -> None:
        """markdown 代码块包裹的 JSON 应解析."""
        content = '```json\n{"questions": ["q1"]}\n```'
        result = _parse_json_response(content)
        assert result == {"questions": ["q1"]}

    def test_plain_code_block(self) -> None:
        """无 json 标记的代码块也应解析."""
        content = '```\n{"answers": []}\n```'
        result = _parse_json_response(content)
        assert result == {"answers": []}

    def test_json_embedded_in_text(self) -> None:
        """JSON 嵌在文本中应提取首尾大括号间内容."""
        content = '前缀文本\n{"key": "value"}\n后缀文本'
        result = _parse_json_response(content)
        assert result == {"key": "value"}

    def test_invalid_json_returns_empty_dict(self) -> None:
        """完全无效的 JSON 应返回空 dict (而非抛异常)."""
        content = "this is not json at all"
        result = _parse_json_response(content)
        assert result == {}

    def test_non_dict_json_returns_empty_dict(self) -> None:
        """JSON 数组 (非 dict) 应返回空 dict."""
        result = _parse_json_response('["q1", "q2"]')
        assert result == {}


# ========== _format_perspective_qa 测试 ==========


class TestFormatPerspectiveQa:
    """校验多视角问答格式化."""

    def test_empty_list_returns_empty_string(self) -> None:
        """空列表应返回空字符串."""
        assert _format_perspective_qa([]) == ""

    def test_single_perspective_formatted(self) -> None:
        """单视角应正确格式化."""
        qa_list = [
            {
                "role": "架构师",
                "focus": "模块边界",
                "questions": ["Q1", "Q2"],
                "answers": [
                    {
                        "question": "Q1",
                        "answer": "A1",
                        "citations": ["src/foo.py:L1-L10"],
                        "confidence": "high",
                    },
                ],
            }
        ]
        result = _format_perspective_qa(qa_list)
        assert "架构师" in result
        assert "模块边界" in result
        assert "Q1" in result
        assert "A1" in result
        assert "src/foo.py:L1-L10" in result
        assert "high" in result

    def test_multiple_perspectives_separated(self) -> None:
        """多视角应以双换行分隔."""
        qa_list = [
            {
                "role": "视角1",
                "focus": "f1",
                "questions": [],
                "answers": [],
            },
            {
                "role": "视角2",
                "focus": "f2",
                "questions": [],
                "answers": [],
            },
        ]
        result = _format_perspective_qa(qa_list)
        assert "视角1" in result
        assert "视角2" in result
        # 应有双换行分隔
        assert "\n\n" in result

    def test_truncation_when_exceeding_max_chars(self) -> None:
        """超过 _MAX_PERSPECTIVE_QA_CHARS 应截断."""
        # 构造超长 answers 列表
        long_answer = "x" * 20_000
        qa_list = [
            {
                "role": f"视角{i}",
                "focus": "f",
                "questions": ["Q"] * 10,
                "answers": [
                    {
                        "question": "Q",
                        "answer": long_answer,
                        "citations": [],
                        "confidence": "low",
                    }
                ]
                * 10,
            }
            for i in range(5)
        ]
        result = _format_perspective_qa(qa_list)
        # 应出现截断标记
        assert "truncated" in result.lower() or "截断" in result


# ========== _load_perspectives 测试 ==========


class TestLoadPerspectives:
    """校验视角配置加载与降级."""

    def test_valid_report_type_returns_perspectives(self) -> None:
        """有效 report_type 应返回视角列表."""
        result = _load_perspectives("architecture")
        assert len(result) == 3
        assert result[0]["role"] == "架构评审师"

    def test_unknown_report_type_returns_empty_list(self) -> None:
        """未知 report_type 应降级返回空列表 (不抛异常)."""
        result = _load_perspectives("nonexistent")
        assert result == []


# ========== _is_multi_perspective_enabled 测试 ==========


class TestIsMultiPerspectiveEnabled:
    """校验多视角开关检测."""

    def test_none_settings_returns_false(self) -> None:
        """settings 为 None 应返回 False (默认关闭)."""
        assert _is_multi_perspective_enabled(None) is False

    def test_settings_without_field_returns_false(self) -> None:
        """settings 无该字段应返回 False."""
        settings = MagicMock()
        del settings.docbot_multi_perspective_enabled
        # getattr 默认值
        settings.docbot_multi_perspective_enabled = False
        assert _is_multi_perspective_enabled(settings) is False

    def test_settings_with_true_returns_true(self) -> None:
        """settings.docbot_multi_perspective_enabled=True 应返回 True."""
        settings = MagicMock()
        settings.docbot_multi_perspective_enabled = True
        assert _is_multi_perspective_enabled(settings) is True

    def test_settings_with_false_returns_false(self) -> None:
        """settings.docbot_multi_perspective_enabled=False 应返回 False."""
        settings = MagicMock()
        settings.docbot_multi_perspective_enabled = False
        assert _is_multi_perspective_enabled(settings) is False


# ========== learn_code_multi_perspective 主流程测试 (mock LLM) ==========


class TestLearnCodeMultiPerspective:
    """校验多视角代码审问主流程."""

    @pytest.fixture
    def mock_llm(self) -> Any:
        """模拟 LLMClient, 阶段1/2/3 返回不同 JSON."""
        llm = MagicMock()
        # 阶段1 (FAST): 返回 questions
        question_response = MagicMock()
        question_response.content = json.dumps({"questions": ["问题1?", "问题2?", "问题3?"]})
        # 阶段2 (SMART): 返回 answers
        answer_response = MagicMock()
        answer_response.content = json.dumps(
            {
                "answers": [
                    {
                        "question": "问题1?",
                        "answer": "答案1",
                        "citations": ["src/foo.py:L1-L10"],
                        "confidence": "high",
                    },
                    {
                        "question": "问题2?",
                        "answer": "答案2",
                        "citations": ["src/bar.py:L5-L15"],
                        "confidence": "medium",
                    },
                    {
                        "question": "问题3?",
                        "answer": "答案3",
                        "citations": [],
                        "confidence": "low",
                    },
                ]
            }
        )
        # 阶段3 (STRATEGIC): 返回汇总
        synthesis_response = MagicMock()
        synthesis_response.content = json.dumps(
            {
                "summary": "## 项目概述\n这是一个测试项目 [src/foo.py:L1-L10]",
                "key_modules": [
                    {
                        "name": "core",
                        "path": "src/core.py",
                        "responsibility": "核心模块",
                        "key_symbols": ["main"],
                        "confidence": "high",
                    }
                ],
                "dependencies": [
                    {"from": "core", "to": "utils", "type": "import", "evidence": "src/core.py:1"}
                ],
                "architecture_notes": "架构笔记",
            }
        )

        # achat 根据 tier 返回不同响应
        async def achat_side_effect(
            messages: list[dict[str, str]],
            *,
            tier: Any,
            **kwargs: Any,
        ) -> Any:
            from src.llm.client import LLMTier

            if tier == LLMTier.FAST:
                return question_response
            if tier == LLMTier.SMART:
                return answer_response
            if tier == LLMTier.STRATEGIC:
                return synthesis_response
            return question_response

        llm.achat = AsyncMock(side_effect=achat_side_effect)
        return llm

    @pytest.mark.asyncio
    async def test_successful_multi_perspective_learning(self, mock_llm: Any) -> None:
        """成功流程应返回与 learn_code 兼容的结构."""
        with (
            patch(
                "src.skills.docbot.multi_perspective_learner._get_llm",
                return_value=mock_llm,
            ),
            patch(
                "src.skills.docbot.multi_perspective_learner.generate_repo_map",
                return_value="repo_map_text",
            ),
            patch(
                "src.skills.docbot.multi_perspective_learner.format_code_graph_for_prompt",
                return_value="code_graph_text",
            ),
            patch(
                "src.skills.docbot.multi_perspective_learner._load_persona",
                return_value=("技术架构师", "描述"),
            ),
        ):
            result = await learn_code_multi_perspective(
                repo_config={"repo_url": "https://example.com/repo.git"},
                repo_id="repo-1",
                user_id="user-1",
                report_type="architecture",
                llm_session_id="session-1",
                repo_path="/tmp/repo",
                file_index={"summary": "file_index_summary", "files": []},
                file_contents="file contents",
                code_graph_obj=CodeGraph(),
                settings=None,
            )

        # 校验返回结构 (与 learn_code 一致)
        assert "summary" in result
        assert "file_index" in result
        assert "key_modules" in result
        assert "dependencies" in result
        assert "architecture_notes" in result
        assert "repo_path" in result
        assert result["repo_path"] == "/tmp/repo"
        assert "项目概述" in result["summary"]
        assert len(result["key_modules"]) == 1
        assert result["key_modules"][0]["name"] == "core"

    @pytest.mark.asyncio
    async def test_all_perspectives_failure_raises_runtime_error(self, mock_llm: Any) -> None:
        """所有视角失败时应抛 RuntimeError (由调用方降级到 learn_code)."""
        # 让 LLM 调用全部抛异常
        mock_llm.achat = AsyncMock(side_effect=RuntimeError("LLM 不可用"))
        with (
            patch(
                "src.skills.docbot.multi_perspective_learner._get_llm",
                return_value=mock_llm,
            ),
            patch(
                "src.skills.docbot.multi_perspective_learner.generate_repo_map",
                return_value="",
            ),
            patch(
                "src.skills.docbot.multi_perspective_learner.format_code_graph_for_prompt",
                return_value="",
            ),
            patch(
                "src.skills.docbot.multi_perspective_learner._load_persona",
                return_value=("技术架构师", "描述"),
            ),
        ):
            with pytest.raises(RuntimeError, match="所有视角均失败"):
                await learn_code_multi_perspective(
                    repo_config={"repo_url": ""},
                    repo_id="repo-1",
                    user_id="user-1",
                    report_type="architecture",
                    llm_session_id="session-1",
                    repo_path="/tmp/repo",
                    file_index={"summary": "", "files": []},
                    file_contents="",
                    code_graph_obj=CodeGraph(),
                    settings=None,
                )


# ========== prompt 模板占位符填充测试 ==========


class TestMultiPerspectivePrompts:
    """校验 3 个多视角 prompt 模板的占位符可正确填充."""

    def test_question_prompt_placeholders(self) -> None:
        """MULTI_PERSPECTIVE_QUESTION_PROMPT 应可填充所有占位符."""
        import re

        from src.config.docbot.prompts import MULTI_PERSPECTIVE_QUESTION_PROMPT

        prompt = MULTI_PERSPECTIVE_QUESTION_PROMPT.format(
            role="架构师",
            focus="模块边界",
            question_topics="- 模块划分\n- 依赖方向",
            report_type="architecture",
            repo_map="repo_map_text",
            code_graph="code_graph_text",
            file_index="file_index_text",
        )
        assert "架构师" in prompt
        assert "模块边界" in prompt
        assert "architecture" in prompt
        # 不应残留未填充的 {占位符} (JSON 示例中的 {{ }} 不算)
        # 匹配 {identifier} 形式的未填充占位符
        unfilled = re.findall(r"\{[a-zA-Z_]\w*\}", prompt)
        assert unfilled == [], f"残留未填充占位符: {unfilled}"

    def test_answer_prompt_placeholders(self) -> None:
        """MULTI_PERSPECTIVE_ANSWER_PROMPT 应可填充所有占位符."""
        import re

        from src.config.docbot.prompts import MULTI_PERSPECTIVE_ANSWER_PROMPT

        prompt = MULTI_PERSPECTIVE_ANSWER_PROMPT.format(
            role="架构师",
            perspective_role="架构师",
            questions="1. 问题1\n2. 问题2",
            repo_map="repo_map_text",
            code_graph="code_graph_text",
            file_contents="file_contents_text",
        )
        assert "架构师" in prompt
        assert "问题1" in prompt
        unfilled = re.findall(r"\{[a-zA-Z_]\w*\}", prompt)
        assert unfilled == [], f"残留未填充占位符: {unfilled}"

    def test_synthesis_prompt_placeholders(self) -> None:
        """MULTI_PERSPECTIVE_SYNTHESIS_PROMPT 应可填充所有占位符."""
        import re

        from src.config.docbot.prompts import MULTI_PERSPECTIVE_SYNTHESIS_PROMPT

        prompt = MULTI_PERSPECTIVE_SYNTHESIS_PROMPT.format(
            role_name="技术架构师",
            description="撰写技术架构文档",
            report_type="architecture",
            perspective_count=3,
            perspective_qa="视角1: ...\n视角2: ...",
            repo_map="repo_map_text",
            code_graph="code_graph_text",
            file_index="file_index_text",
        )
        assert "技术架构师" in prompt
        assert "architecture" in prompt
        assert "3" in prompt
        unfilled = re.findall(r"\{[a-zA-Z_]\w*\}", prompt)
        assert unfilled == [], f"残留未填充占位符: {unfilled}"

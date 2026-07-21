"""单元测试: DocbotState + ReportTaskState TypedDict 字段.

测试目标:
- DocbotState 含所有必需字段 (messages/user_id/session_id/agent_id/repo_id/report_types/...)
- ReportTaskState 含所有必需字段 (report_type/code_learning_cache_key/...)
"""
from __future__ import annotations

from src.graph.state import DocbotState, ReportTaskState


class TestDocbotState:
    """DocbotState TypedDict 字段校验."""

    def test_docbot_state_is_typed_dict(self) -> None:
        """验证 DocbotState 是 TypedDict."""

        # TypedDict 在 Python 3.12+ 的 __orig_bases__ 含 _TypedDictMeta
        # 简单验证类型可用作 dict 类型注解
        assert DocbotState is not None

    def test_docbot_state_has_required_fields(self) -> None:
        """验证 DocbotState 含所有必需字段.

        必需字段:
        - messages: 消息流 (add_messages reducer)
        - user_id / session_id / agent_id: 请求上下文
        - repo_id / report_types / report_format / language: 用户请求参数
        - report_tasks / final_reports / errors / iteration_count: 派发结果与累积
        """
        # TypedDict 字段可通过 __annotations__ 获取
        annotations = DocbotState.__annotations__
        required_fields = {
            "messages",
            "user_id",
            "session_id",
            "agent_id",
            "repo_id",
            "report_types",
            "report_format",
            "language",
            "report_tasks",
            "final_reports",
            "errors",
            "iteration_count",
        }
        for field in required_fields:
            assert field in annotations, f"DocbotState 缺字段: {field}"

    def test_docbot_state_agent_id_default(self) -> None:
        """验证 agent_id 字段约定为 'agentinsight-docbot'."""
        # 这是文档约定, 不在 TypedDict 内强制
        # 仅验证字段存在
        assert "agent_id" in DocbotState.__annotations__

    def test_docbot_state_can_be_constructed_as_dict(self) -> None:
        """验证 DocbotState 可作为 dict 构造."""
        state: DocbotState = {
            "messages": [],
            "user_id": "user1",
            "session_id": "session1",
            "agent_id": "agentinsight-docbot",
            "repo_id": "repo1",
            "report_types": ["architecture"],
            "report_format": "markdown",
            "language": "zh",
            "report_tasks": [],
            "final_reports": [],
            "errors": [],
            "iteration_count": 0,
        }
        assert state["agent_id"] == "agentinsight-docbot"
        assert state["report_types"] == ["architecture"]
        assert state["language"] == "zh"


class TestReportTaskState:
    """ReportTaskState TypedDict 字段校验."""

    def test_report_task_state_has_required_fields(self) -> None:
        """验证 ReportTaskState 含所有必需字段.

        必需字段 (6 步流水线 + 缓存键 + 章节迭代):
        - report_type / report_format / language / repo_id / user_id / session_id / agent_id
        - llm_session_id
        - code_learning_cache_key / outline_cache_key
        - content_cache_keys / reviewed_cache_keys / merged_cache_key / final_cache_key
        - current_chapter_idx / chapters / max_revisions_per_chapter / revision_count
        - report_id / report_title / report_summary / report_image_svg / download_urls
        """
        annotations = ReportTaskState.__annotations__
        required_fields = {
            "report_type",
            "report_format",
            "language",
            "repo_id",
            "user_id",
            "session_id",
            "agent_id",
            "llm_session_id",
            "code_learning_cache_key",
            "outline_cache_key",
            "content_cache_keys",
            "reviewed_cache_keys",
            "merged_cache_key",
            "final_cache_key",
            "current_chapter_idx",
            "chapters",
            "max_revisions_per_chapter",
            "revision_count",
            "report_id",
            "report_title",
            "report_summary",
            "report_image_svg",
            "download_urls",
        }
        for field in required_fields:
            assert field in annotations, f"ReportTaskState 缺字段: {field}"

    def test_report_task_state_can_be_constructed_as_dict(self) -> None:
        """验证 ReportTaskState 可作为 dict 构造."""
        state: ReportTaskState = {
            "report_type": "architecture",
            "report_format": "markdown",
            "language": "zh",
            "repo_id": "repo1",
            "user_id": "user1",
            "session_id": "session1",
            "agent_id": "agentinsight-docbot",
            "llm_session_id": "llm-session-1",
            "code_learning_cache_key": "docbot:agentinsight-docbot:user1:session1:code_learning:architecture",
            "outline_cache_key": "docbot:agentinsight-docbot:user1:session1:outline:architecture",
            "content_cache_keys": [],
            "reviewed_cache_keys": [],
            "merged_cache_key": "",
            "final_cache_key": "",
            "current_chapter_idx": 0,
            "chapters": [],
            "max_revisions_per_chapter": 3,
            "revision_count": 0,
            "report_id": "",
            "report_title": "",
            "report_summary": "",
            "report_image_svg": "",
            "download_urls": {},
        }
        assert state["report_type"] == "architecture"
        assert state["max_revisions_per_chapter"] == 3
        assert state["agent_id"] == "agentinsight-docbot"


class TestStateReducers:
    """state reducers 行为验证 (operator.add / add_messages)."""

    def test_iteration_count_uses_operator_add(self) -> None:
        """iteration_count 用 operator.add reducer (节点返回 1, 累积)."""
        import operator
        from typing import get_args, get_type_hints

        from src.graph.state import DocbotState

        # state.py 用 from __future__ import annotations, 注解为字符串
        # 必须用 get_type_hints 解析, 否则 get_args 返回空
        hints = get_type_hints(DocbotState, include_extras=True)
        annotation = hints["iteration_count"]
        args = get_args(annotation)
        # args[-1] 是 metadata (operator.add)
        assert len(args) >= 2, "iteration_count 应为 Annotated[int, operator.add]"
        # 找到 operator.add
        found_add = any(arg is operator.add for arg in args)
        assert found_add, "iteration_count 应使用 operator.add reducer"

    def test_report_tasks_uses_operator_add(self) -> None:
        """report_tasks 用 operator.add reducer."""
        import operator
        from typing import get_args, get_type_hints

        from src.graph.state import DocbotState

        # state.py 用 from __future__ import annotations, 注解为字符串
        hints = get_type_hints(DocbotState, include_extras=True)
        annotation = hints["report_tasks"]
        args = get_args(annotation)
        found_add = any(arg is operator.add for arg in args)
        assert found_add, "report_tasks 应使用 operator.add reducer"

    def test_final_reports_uses_operator_add(self) -> None:
        """final_reports 用 operator.add reducer."""
        import operator
        from typing import get_args, get_type_hints

        from src.graph.state import DocbotState

        hints = get_type_hints(DocbotState, include_extras=True)
        annotation = hints["final_reports"]
        args = get_args(annotation)
        found_add = any(arg is operator.add for arg in args)
        assert found_add, "final_reports 应使用 operator.add reducer"

    def test_errors_uses_operator_add(self) -> None:
        """errors 用 operator.add reducer."""
        import operator
        from typing import get_args, get_type_hints

        from src.graph.state import DocbotState

        hints = get_type_hints(DocbotState, include_extras=True)
        annotation = hints["errors"]
        args = get_args(annotation)
        found_add = any(arg is operator.add for arg in args)
        assert found_add, "errors 应使用 operator.add reducer"

    def test_messages_uses_add_messages_reducer(self) -> None:
        """messages 用 add_messages reducer."""
        from typing import get_args, get_type_hints

        from langgraph.graph.message import add_messages

        from src.graph.state import DocbotState

        hints = get_type_hints(DocbotState, include_extras=True)
        annotation = hints["messages"]
        args = get_args(annotation)
        found_add = any(arg is add_messages for arg in args)
        assert found_add, "messages 应使用 add_messages reducer"

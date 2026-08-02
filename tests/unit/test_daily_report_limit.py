"""单元测试: 每日文档生成限额 (与 researcher 对齐 + docbot 多份计数).

验证 src/api/routes.py 限额检查逻辑 + src/api/ip_user_resolver.py:
1. 用户超限 - 非流式 → 429 + 错误信息含 "已达上限"
2. 用户未超限 - 非流式 → 200
3. 用户超限 - 流式 → SSE 含 "已达上限"
4. JWT 用户同样受限额约束 (与 researcher 一致)
5. self_host=False 无 token 统一降级 IP-based (走限额检查)
6. 剩余不足申请份数 → 友好中文提示
7. 非流式成功 → increment(delta=成功份数)
8. 限额拒绝路径 → increment 不被调用
9. 流式成功 → increment 被调用
10. 流式限额拒绝 → increment 不被调用
11. 用户级 / 系统级回退场景
12. increment 参数含 user_id / agent_id / delta

单元测试不依赖外部服务 (Redis/Postgres/LLM 全部 mock).
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from server import app
from src.api.middleware import JWTAuthMiddleware, SecurityHeadersMiddleware
from src.api.routes import router
from src.config.settings import Settings

pytestmark = pytest.mark.unit


# ========== 辅助函数 ==========


def _make_settings(**kwargs: Any) -> Settings:
    """构造自定义 Settings (默认 self_host=True, ip_daily_report_limit=3)."""
    defaults: dict[str, Any] = {
        "_env_file": None,
        "self_host": True,
        "ip_daily_report_limit": 3,
        "agent_name": "agentinsight-docbot",
        "default_report_format": "markdown",
        "report_language": "zh",
        "graph_total_timeout": 300,
    }
    defaults.update(kwargs)
    return Settings(**defaults)


def _patch_pipeline(
    monkeypatch: pytest.MonkeyPatch,
    *,
    report_types: list[str] | None = None,
) -> None:
    """Mock 文档生成流水线依赖 (图构建 + 会话持久化)."""
    types = report_types or ["architecture"]
    final_reports = [
        {
            "report_id": f"rpt-test-{i + 1}",
            "report_type": rt,
            "title": f"{rt} 文档",
            "summary": "测试摘要",
            "download_urls": {},
        }
        for i, rt in enumerate(types)
    ]
    mock_graph = MagicMock()
    mock_graph.ainvoke = AsyncMock(
        return_value={
            "final_reports": final_reports,
            "total_tokens": 10,
            "total_cost_usd": 0.0,
        }
    )

    async def _fake_astream(*_args: Any, **_kwargs: Any) -> Any:
        yield {"save_reports": {"final_reports": final_reports}}

    mock_graph.astream = _fake_astream
    monkeypatch.setattr("src.api.routes._get_graph", AsyncMock(return_value=mock_graph))
    monkeypatch.setattr("src.api.routes._persist_user_message", AsyncMock())
    monkeypatch.setattr("src.api.routes._persist_assistant_message", AsyncMock())

    mock_store = MagicMock()
    mock_store.update_report_config = AsyncMock()
    monkeypatch.setattr(
        "src.memory.session_store.get_session_store",
        MagicMock(return_value=mock_store),
    )


def _patch_limit_check(
    monkeypatch: pytest.MonkeyPatch,
    allowed: bool,
    count: int,
    limit: int = 3,
) -> AsyncMock:
    """Mock check_daily_report_limit 返回指定结果."""
    mock = AsyncMock(return_value=(allowed, count, limit))
    monkeypatch.setattr("src.api.ip_user_resolver.check_daily_report_limit", mock)
    return mock


def _patch_increment(monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
    """Mock increment_daily_report_count 避免数据库连接."""
    mock = AsyncMock(return_value=1)
    monkeypatch.setattr("src.api.ip_user_resolver.increment_daily_report_count", mock)
    return mock


_REQUEST_BODY: dict[str, Any] = {
    "model": "agentinsight-docbot",
    "messages": [
        {
            "role": "user",
            "content": (
                '{"action":"generate_docs","repo_id":"test-repo",'
                '"report_types":["architecture"]}'
            ),
        }
    ],
    "stream": False,
    "repo_id": "test-repo",
    "report_types": ["architecture"],
}


# ========== 场景 1: 超限 - 非流式 ==========


def test_ip_user_exceeded_non_stream(monkeypatch: pytest.MonkeyPatch) -> None:
    """用户超限 → 429 + 错误信息含 "已达上限" 和 "3/3"."""
    settings = _make_settings()
    monkeypatch.setattr("src.api.routes.get_settings", lambda: settings)
    _patch_pipeline(monkeypatch)
    _patch_limit_check(monkeypatch, allowed=False, count=3, limit=3)

    client = TestClient(app)
    response = client.post("/v1/chat/completions", json=_REQUEST_BODY)

    assert response.status_code == 429
    data = response.json()
    msg = data["error"]["message"]
    assert "已达上限" in msg
    assert "3/3" in msg
    assert data["error"]["type"] == "rate_limit_exceeded"
    assert data["error"]["code"] == "daily_report_limit"
    assert data["error"]["remaining"] == 0


# ========== 场景 2: 未超限 - 非流式 ==========


def test_ip_user_not_exceeded_non_stream(monkeypatch: pytest.MonkeyPatch) -> None:
    """用户未超限 → 不返回 429 (走正常文档生成流水线)."""
    settings = _make_settings()
    monkeypatch.setattr("src.api.routes.get_settings", lambda: settings)
    _patch_pipeline(monkeypatch)
    _patch_limit_check(monkeypatch, allowed=True, count=1)
    _patch_increment(monkeypatch)

    client = TestClient(app)
    response = client.post("/v1/chat/completions", json=_REQUEST_BODY)

    assert response.status_code != 429
    assert response.status_code == 200
    data = response.json()
    assert data["object"] == "chat.completion"


# ========== 场景 3: 超限 - 流式 ==========


def test_ip_user_exceeded_stream(monkeypatch: pytest.MonkeyPatch) -> None:
    """用户超限 - 流式 → SSE 含 "已达上限", finish_reason="stop"."""
    settings = _make_settings()
    monkeypatch.setattr("src.api.routes.get_settings", lambda: settings)
    _patch_pipeline(monkeypatch)
    _patch_limit_check(monkeypatch, allowed=False, count=3, limit=3)

    body = {**_REQUEST_BODY, "stream": True}
    client = TestClient(app)
    with client.stream("POST", "/v1/chat/completions", json=body) as response:
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]

        chunks: list[dict[str, Any]] = []
        for line in response.iter_lines():
            if line.startswith("data: "):
                payload = line[6:]
                if payload == "[DONE]":
                    break
                chunks.append(json.loads(payload))

    assert len(chunks) >= 2
    first_delta = chunks[0]["choices"][0]["delta"]
    first_content = first_delta.get("content", "")
    assert "已达上限" in first_content
    assert "3/3" in first_content
    assert first_delta.get("remaining") == 0
    assert chunks[-1]["choices"][0]["finish_reason"] == "stop"


# ========== 场景 4: JWT 用户同样受限额 ==========


def test_jwt_user_is_limited(monkeypatch: pytest.MonkeyPatch) -> None:
    """JWT Token 用户同样走限额检查 (与 researcher 一致)."""
    settings = _make_settings()
    monkeypatch.setattr("src.api.routes.get_settings", lambda: settings)
    _patch_pipeline(monkeypatch)
    mock_check = _patch_limit_check(monkeypatch, allowed=False, count=3, limit=3)
    _patch_increment(monkeypatch)

    async def _fake_resolve(
        self: JWTAuthMiddleware, token: str, client_ip: str = ""
    ) -> tuple[str | None, str | None]:
        return "real-user-123", None

    monkeypatch.setattr(JWTAuthMiddleware, "_resolve_user_id", _fake_resolve)

    client = TestClient(app)
    response = client.post(
        "/v1/chat/completions",
        json=_REQUEST_BODY,
        headers={"Authorization": "Bearer fake-token"},
    )

    assert response.status_code == 429
    mock_check.assert_awaited_once()
    kwargs = mock_check.await_args.kwargs
    assert kwargs.get("requested_count") == 1


# ========== 场景 5: self_host=False 无 token 统一降级 ==========


def test_self_host_false_no_token_degrades_to_ip(monkeypatch: pytest.MonkeyPatch) -> None:
    """self_host=False 无 token → 统一降级 IP-based UserId (不再返回 401)."""
    settings = _make_settings(self_host=False)

    _patch_pipeline(monkeypatch)
    mock_check = _patch_limit_check(monkeypatch, allowed=True, count=0, limit=3)
    _patch_increment(monkeypatch)

    test_app = FastAPI()
    test_app.include_router(router)
    test_app.add_middleware(JWTAuthMiddleware, settings=settings)
    test_app.add_middleware(SecurityHeadersMiddleware)

    client = TestClient(test_app)
    response = client.post("/v1/chat/completions", json=_REQUEST_BODY)

    assert response.status_code != 401, (
        f"统一降级策略下不应返回 401, 实际: {response.status_code}"
    )
    mock_check.assert_called_once()


# ========== 场景 6: 剩余不足申请份数 ==========


def test_remaining_insufficient_for_multi_types(monkeypatch: pytest.MonkeyPatch) -> None:
    """剩余 1 < 申请 2 → 429, 提示剩余次数不足."""
    settings = _make_settings()
    monkeypatch.setattr("src.api.routes.get_settings", lambda: settings)
    _patch_pipeline(monkeypatch, report_types=["requirements", "api_doc"])
    # 走真实 check: 限额 3, 已用 2 → 剩余 1 < 申请 2
    monkeypatch.setattr(
        "src.api.ip_user_resolver._get_daily_limit_from_db",
        AsyncMock(return_value=3),
    )
    monkeypatch.setattr(
        "src.api.ip_user_resolver._get_daily_usage_from_db",
        AsyncMock(return_value=2),
    )
    mock_increment = _patch_increment(monkeypatch)

    body = {
        **_REQUEST_BODY,
        "report_types": ["requirements", "api_doc"],
        "messages": [
            {
                "role": "user",
                "content": (
                    '{"action":"generate_docs","repo_id":"test-repo",'
                    '"report_types":["requirements","api_doc"]}'
                ),
            }
        ],
    }
    client = TestClient(app)
    response = client.post("/v1/chat/completions", json=body)

    assert response.status_code == 429
    err = response.json()["error"]
    msg = err["message"]
    assert "剩余次数为 1" in msg
    assert "2 份" in msg
    assert "每个报告类型计为 1 份" in msg
    assert err["remaining"] == 1
    mock_increment.assert_not_called()


# ========== 场景 7: 非流式成功 → increment(delta) ==========


def test_non_stream_success_increment_called(monkeypatch: pytest.MonkeyPatch) -> None:
    """非流式成功路径 → increment_daily_report_count(delta=1) 应被调用."""
    settings = _make_settings()
    monkeypatch.setattr("src.api.routes.get_settings", lambda: settings)
    _patch_pipeline(monkeypatch)
    _patch_limit_check(monkeypatch, allowed=True, count=1)
    mock_increment = _patch_increment(monkeypatch)

    client = TestClient(app)
    response = client.post("/v1/chat/completions", json=_REQUEST_BODY)

    assert response.status_code == 200
    mock_increment.assert_awaited_once()
    assert mock_increment.await_args.kwargs.get("delta") == 1


def test_non_stream_multi_success_increment_delta(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """多报告类型全部成功 → increment(delta=成功份数)."""
    settings = _make_settings()
    monkeypatch.setattr("src.api.routes.get_settings", lambda: settings)
    _patch_pipeline(monkeypatch, report_types=["requirements", "api_doc"])
    _patch_limit_check(monkeypatch, allowed=True, count=0, limit=3)
    mock_increment = _patch_increment(monkeypatch)

    body = {
        **_REQUEST_BODY,
        "report_types": ["requirements", "api_doc"],
        "messages": [
            {
                "role": "user",
                "content": (
                    '{"action":"generate_docs","repo_id":"test-repo",'
                    '"report_types":["requirements","api_doc"]}'
                ),
            }
        ],
    }
    client = TestClient(app)
    response = client.post("/v1/chat/completions", json=body)

    assert response.status_code == 200
    mock_increment.assert_awaited_once()
    assert mock_increment.await_args.kwargs.get("delta") == 2


# ========== 场景 8: 限额拒绝 → increment 不调用 ==========


def test_non_stream_limit_exceeded_increment_not_called(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """非流式限额超限 → increment_daily_report_count 不应被调用."""
    settings = _make_settings()
    monkeypatch.setattr("src.api.routes.get_settings", lambda: settings)
    _patch_pipeline(monkeypatch)
    _patch_limit_check(monkeypatch, allowed=False, count=3, limit=3)
    mock_increment = _patch_increment(monkeypatch)

    client = TestClient(app)
    response = client.post("/v1/chat/completions", json=_REQUEST_BODY)

    assert response.status_code == 429
    mock_increment.assert_not_called()


# ========== 场景 9: 流式成功 ==========


def test_stream_success_increment_called(monkeypatch: pytest.MonkeyPatch) -> None:
    """流式成功路径 → SSE 正常完成且 increment 被调用."""
    settings = _make_settings()
    monkeypatch.setattr("src.api.routes.get_settings", lambda: settings)
    _patch_pipeline(monkeypatch)
    _patch_limit_check(monkeypatch, allowed=True, count=1)
    mock_increment = _patch_increment(monkeypatch)

    body = {**_REQUEST_BODY, "stream": True}
    client = TestClient(app)
    chunks: list[dict[str, Any]] = []
    with client.stream("POST", "/v1/chat/completions", json=body) as response:
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]
        for line in response.iter_lines():
            if line.startswith("data: "):
                payload = line[6:]
                if payload == "[DONE]":
                    break
                chunks.append(json.loads(payload))

    assert len(chunks) >= 1
    all_content = "".join(
        c["choices"][0]["delta"].get("content", "")
        for c in chunks
        if c.get("choices")
    )
    assert "已达上限" not in all_content
    assert chunks[-1]["choices"][0]["finish_reason"] == "stop"
    mock_increment.assert_awaited_once()
    assert mock_increment.await_args.kwargs.get("delta") == 1


# ========== 场景 10: 流式限额拒绝 ==========


def test_stream_limit_exceeded_increment_not_called(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """流式限额超限 → increment_daily_report_count 不应被调用."""
    settings = _make_settings()
    monkeypatch.setattr("src.api.routes.get_settings", lambda: settings)
    _patch_pipeline(monkeypatch)
    _patch_limit_check(monkeypatch, allowed=False, count=3, limit=3)
    mock_increment = _patch_increment(monkeypatch)

    body = {**_REQUEST_BODY, "stream": True}
    client = TestClient(app)
    with client.stream("POST", "/v1/chat/completions", json=body) as response:
        assert response.status_code == 200
        for _ in response.iter_lines():
            pass

    mock_increment.assert_not_called()


# ========== 场景 11: 用户级 / 系统级回退 ==========


def _patch_db_limit_and_usage(
    monkeypatch: pytest.MonkeyPatch,
    *,
    db_limit: int,
    usage: int,
) -> None:
    """Mock 数据库层: _get_daily_limit_from_db 和 _get_daily_usage_from_db."""
    monkeypatch.setattr(
        "src.api.ip_user_resolver._get_daily_limit_from_db",
        AsyncMock(return_value=db_limit),
    )
    monkeypatch.setattr(
        "src.api.ip_user_resolver._get_daily_usage_from_db",
        AsyncMock(return_value=usage),
    )


def test_scenario_user_has_limit_under_non_stream(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """用户有限额 (10), 已用 3 → 允许, 200, increment 调用."""
    settings = _make_settings()
    monkeypatch.setattr("src.api.routes.get_settings", lambda: settings)
    _patch_pipeline(monkeypatch)
    _patch_db_limit_and_usage(monkeypatch, db_limit=10, usage=3)
    mock_increment = _patch_increment(monkeypatch)

    client = TestClient(app)
    response = client.post("/v1/chat/completions", json=_REQUEST_BODY)

    assert response.status_code == 200
    mock_increment.assert_awaited_once()


def test_scenario_user_has_limit_at_non_stream(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """用户有限额 (10), 已用 10 → 拒绝, 429."""
    settings = _make_settings()
    monkeypatch.setattr("src.api.routes.get_settings", lambda: settings)
    _patch_pipeline(monkeypatch)
    _patch_db_limit_and_usage(monkeypatch, db_limit=10, usage=10)
    mock_increment = _patch_increment(monkeypatch)

    client = TestClient(app)
    response = client.post("/v1/chat/completions", json=_REQUEST_BODY)

    assert response.status_code == 429
    data = response.json()
    assert "10/10" in data["error"]["message"]
    mock_increment.assert_not_called()


def test_scenario_no_user_uses_agent_default_under(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """无用户专属, Agent/系统默认 3, 已用 1 → 允许."""
    settings = _make_settings()
    monkeypatch.setattr("src.api.routes.get_settings", lambda: settings)
    _patch_pipeline(monkeypatch)
    _patch_db_limit_and_usage(monkeypatch, db_limit=3, usage=1)
    mock_increment = _patch_increment(monkeypatch)

    client = TestClient(app)
    response = client.post("/v1/chat/completions", json=_REQUEST_BODY)

    assert response.status_code == 200
    mock_increment.assert_awaited_once()


def test_scenario_no_user_uses_agent_default_at(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """无用户专属, Agent/系统默认 3, 已用 3 → 拒绝."""
    settings = _make_settings()
    monkeypatch.setattr("src.api.routes.get_settings", lambda: settings)
    _patch_pipeline(monkeypatch)
    _patch_db_limit_and_usage(monkeypatch, db_limit=3, usage=3)
    mock_increment = _patch_increment(monkeypatch)

    client = TestClient(app)
    response = client.post("/v1/chat/completions", json=_REQUEST_BODY)

    assert response.status_code == 429
    data = response.json()
    assert "3/3" in data["error"]["message"]
    mock_increment.assert_not_called()


def test_scenario_user_greater_than_system_under(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """用户限额 (10) > Agent 默认 (3), 已用 7 → 允许 (用 10)."""
    settings = _make_settings()
    monkeypatch.setattr("src.api.routes.get_settings", lambda: settings)
    _patch_pipeline(monkeypatch)
    _patch_db_limit_and_usage(monkeypatch, db_limit=10, usage=7)
    mock_increment = _patch_increment(monkeypatch)

    client = TestClient(app)
    response = client.post("/v1/chat/completions", json=_REQUEST_BODY)

    assert response.status_code == 200
    mock_increment.assert_awaited_once()


def test_scenario_user_less_than_system_at(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """用户限额 (2) < Agent 默认, 已用 2 → 拒绝 (用 2)."""
    settings = _make_settings()
    monkeypatch.setattr("src.api.routes.get_settings", lambda: settings)
    _patch_pipeline(monkeypatch)
    _patch_db_limit_and_usage(monkeypatch, db_limit=2, usage=2)
    mock_increment = _patch_increment(monkeypatch)

    client = TestClient(app)
    response = client.post("/v1/chat/completions", json=_REQUEST_BODY)

    assert response.status_code == 429
    data = response.json()
    assert "2/2" in data["error"]["message"]
    mock_increment.assert_not_called()


# ========== 场景 12: increment 调用参数 ==========


def test_increment_called_with_correct_args(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """increment_daily_report_count 应以正确的 user_id / agent_id / delta 调用."""
    settings = _make_settings(agent_name="agentinsight-docbot")
    monkeypatch.setattr("src.api.routes.get_settings", lambda: settings)
    _patch_pipeline(monkeypatch)
    _patch_limit_check(monkeypatch, allowed=True, count=1)
    mock_increment = _patch_increment(monkeypatch)

    client = TestClient(app)
    response = client.post("/v1/chat/completions", json=_REQUEST_BODY)

    assert response.status_code == 200
    mock_increment.assert_awaited_once()
    call_args = mock_increment.await_args
    assert call_args is not None
    args, kwargs = call_args
    assert len(args) >= 2
    assert args[0].startswith("ip_")  # user_id
    assert args[1] == "agentinsight-docbot"  # agent_id
    assert kwargs.get("delta") == 1


def test_check_called_with_requested_count(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """入口预检应按报告类型数量传 requested_count."""
    settings = _make_settings()
    monkeypatch.setattr("src.api.routes.get_settings", lambda: settings)
    _patch_pipeline(monkeypatch, report_types=["requirements", "api_doc"])
    mock_check = _patch_limit_check(monkeypatch, allowed=True, count=0, limit=3)
    _patch_increment(monkeypatch)

    body = {
        **_REQUEST_BODY,
        "report_types": ["requirements", "api_doc"],
        "messages": [
            {
                "role": "user",
                "content": (
                    '{"action":"generate_docs","repo_id":"test-repo",'
                    '"report_types":["requirements","api_doc"]}'
                ),
            }
        ],
    }
    client = TestClient(app)
    response = client.post("/v1/chat/completions", json=body)

    assert response.status_code == 200
    assert mock_check.await_args.kwargs.get("requested_count") == 2

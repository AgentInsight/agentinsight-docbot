"""全局 pytest conftest.py.

提供共享 fixture:
- mock_settings: 模拟 Settings 实例 (agent_name='agentinsight-docbot', git_credential_key=test*32)
- mock_redis: 用 fakeredis 模拟 Redis 客户端
- mock_llm_client: 返回固定响应的 LLM 客户端 mock
- tmp_repos_dir: 临时仓库克隆目录 (自动清理)
- event_loop: pytest-asyncio 事件循环
- requires_external 标记: 默认跳过外部服务依赖的测试, --run-external 启用

约定 (见 AGENTS.md 第 13 章):
- 单元测试不应依赖外部服务 (Postgres/Qdrant/Redis/LLM/Git)
- 用 fakeredis / unittest.mock 模拟外部依赖
- pyproject.toml 已配 asyncio_mode = "auto", 异步测试用 async def
"""
from __future__ import annotations

import asyncio
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

# 确保 src/ 在 import 路径中 (pyproject.toml 已配 pythonpath=["src"], 这里兜底)
_PROJECT_ROOT = Path(__file__).parent.parent
_SRC_DIR = _PROJECT_ROOT / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

# 项目根目录入 sys.path (便于 from src.xxx import ... 形式)
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# ========== Mock 缺失的 optional 依赖 (litellm / agentinsight-sdk 等) ==========
# 测试环境可能未安装所有运行时依赖 (litellm/agentinsight-sdk 等),
# 用 MagicMock 兜底, 让 import 不抛 ModuleNotFoundError.
# 仅影响 import 期; 运行时若调用这些模块的方法, 会返回 MagicMock (测试中应 mock 具体调用).
_OPTIONAL_DEPENDENCIES = (
    "litellm",
    "agentinsight",
    "agentinsight.api",
    "agentinsight.api.core",
    "agentinsight.api.core.pydantic_utilities",
    "langgraph",
    "langgraph.checkpoint",
    "langgraph.checkpoint.postgres",
    "langchain_core",
    "langchain_mcp_adapters",
    "mcp",
    "psycopg",
    "psycopg_pool",
    "asyncpg",
    "qdrant_client",
    "fastembed",
    "onnxruntime",
    "rank_bm25",
    "jieba",
    "opentelemetry",
    "opentelemetry.sdk",
    "opentelemetry.sdk.trace",
    "opentelemetry.sdk.trace.export",
    "opentelemetry.exporter.otlp.proto.http",
    "opentelemetry.exporter.otlp.proto.http.trace_exporter",
    "httpx",
    "bs4",
    "lxml",
    "pypdf",
    "docx",
    "openpyxl",
    "pptx",
    "markitdown",
    "jinja2",
    "weasyprint",
    "mistune",
    "cairosvg",
    "cryptography",
    "json_repair",
    "orjson",
    "numpy",
)
for _mod_name in _OPTIONAL_DEPENDENCIES:
    if _mod_name not in sys.modules:
        try:
            __import__(_mod_name)
        except ImportError:
            sys.modules[_mod_name] = MagicMock()


# ========== requires_external 标记: 默认跳过外部服务依赖测试 ==========
def pytest_addoption(parser: pytest.Parser) -> None:
    """注册 --run-external 命令行选项."""
    parser.addoption(
        "--run-external",
        action="store_true",
        default=False,
        help="运行依赖外部服务的测试 (默认跳过)",
    )


def pytest_configure(config: pytest.Config) -> None:
    """注册 requires_external marker 并配置跳过逻辑."""
    config.addinivalue_line(
        "markers",
        "requires_external: 依赖外部服务 (Postgres/Redis/Qdrant/LLM/Git), 默认跳过, --run-external 启用",
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """自动跳过 requires_external 标记的测试 (除非 --run-external)."""
    if config.getoption("--run-external"):
        return
    skip_external = pytest.mark.skip(reason="需要 --run-external 启用 (依赖外部服务)")
    for item in items:
        if "requires_external" in item.keywords:
            item.add_marker(skip_external)


# ========== mock_settings fixture ==========
@pytest.fixture
def mock_settings() -> MagicMock:
    """提供模拟 Settings 实例.

    包含 docbot 专属字段:
    - agent_name = 'agentinsight-docbot'
    - git_credential_key = 'test' * 32 (32 字节 ASCII, 兼容 _decode_credential_key)
    - max_repo_size_mb = 1024
    - max_revisions_per_chapter = 3
    - max_concurrent_reports = 3
    - docbot_cache_ttl = 86400
    """
    settings = MagicMock()
    settings.agent_name = "agentinsight-docbot"
    settings.agent_id = "agentinsight-docbot"
    # git_credential_key: 32 字节 ASCII (兼容 _decode_credential_key 的 UTF-8 前 32 字节路径)
    settings.git_credential_key = "test" * 32  # 128 字符 -> 取前 32 字节
    settings.max_repo_size_mb = 1024
    settings.max_revisions_per_chapter = 3
    max_chapters_per_report = 20
    settings.max_chapters_per_report = max_chapters_per_report
    settings.max_concurrent_reports = 3
    settings.max_llm_concurrency = 5
    settings.max_rag_concurrency = 10
    settings.docbot_cache_ttl = 86400
    settings.docbot_outlines_dir = "docs"
    settings.supported_languages = "zh,en"
    settings.supported_report_types = (
        "architecture,design,requirements,testcase,optimization,performance,defect,api_doc"
    )
    settings.repo_clone_root = str(Path(_tmp_dir()) / "docbot_test_repos")
    settings.allowed_git_domains = ""
    settings.cors_allow_origins = "http://localhost:8068"
    settings.redis_url = "redis://localhost:6379/0"
    settings.redis_auth = None
    settings.redis_socket_timeout = 5.0
    settings.redis_max_connections = 50
    settings.env = "dev"
    settings.enable_test_page = False
    settings.log_level = "WARNING"
    # Settings 属性方法
    settings.cors_origins_list = ["http://localhost:8068"]
    settings.supported_languages_list = ["zh", "en"]
    settings.supported_report_types_list = [
        "architecture",
        "design",
        "requirements",
        "testcase",
        "optimization",
        "performance",
        "defect",
        "api_doc",
    ]
    settings.allowed_git_domains_list = []
    return settings


def _tmp_dir() -> str:
    """获取系统临时目录 (避免在模块顶部 import tempfile 时的副作用)."""
    import tempfile

    return tempfile.gettempdir()


# ========== mock_redis fixture ==========
@pytest.fixture
async def mock_redis() -> AsyncMock:
    """提供 fakeredis 异步 Redis 客户端 mock.

    支持: get/setex/delete/scan_iter/ping
    """
    try:
        import fakeredis.aioredis

        client = fakeredis.aioredis.FakeRedis()
        # 验证连接
        await client.ping()
        yield client
        await client.aclose()
    except ImportError:
        # 降级到 AsyncMock
        client = AsyncMock()
        client.ping = AsyncMock(return_value=True)
        client.get = AsyncMock(return_value=None)
        client.setex = AsyncMock(return_value=True)
        client.delete = AsyncMock(return_value=1)
        client.scan_iter = MagicMock(return_value=iter([]))
        client.aclose = AsyncMock()
        yield client


# ========== mock_llm_client fixture ==========
@pytest.fixture
def mock_llm_client() -> MagicMock:
    """提供返回固定响应的 LLM 客户端 mock.

    返回的 response 对象含 content 字段 (字符串).
    """
    client = MagicMock()
    response = MagicMock()
    response.content = '{"needs_revision": false, "review_notes": "OK", "revised_content": "content"}'
    client.achat = AsyncMock(return_value=response)
    client.achat_stream = AsyncMock()
    client.achat_strategic = AsyncMock(return_value=response)
    client.achat_smart = AsyncMock(return_value=response)
    client.achat_fast = AsyncMock(return_value=response)
    return client


# ========== tmp_repos_dir fixture ==========
@pytest.fixture
def tmp_repos_dir(tmp_path: Path) -> Path:
    """提供临时仓库克隆目录 (自动清理).

    返回: {tmp_path}/repos/
    """
    repos_dir = tmp_path / "repos"
    repos_dir.mkdir(parents=True, exist_ok=True)
    return repos_dir


# ========== event_loop fixture (pytest-asyncio) ==========
@pytest.fixture
def event_loop() -> Iterator[asyncio.AbstractEventLoop]:
    """提供 event_loop (pytest-asyncio 兼容)."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ========== 通用辅助 fixture ==========
@pytest.fixture
def sample_repo_config() -> dict[str, Any]:
    """提供样例 repo_config dict (用于 GitMCPAdapter 测试)."""
    return {
        "repo_url": "https://github.com/test/repo.git",
        "default_branch": "main",
        "clone_depth": 1,
        "auth_type": "none",
    }


@pytest.fixture
def sample_chapters() -> list[dict]:
    """提供样例章节列表 (用于 D-E 循环测试)."""
    return [
        {"idx": 1, "title": "系统概述", "sections": [], "key_points": []},
        {"idx": 2, "title": "技术选型", "sections": [], "key_points": []},
        {"idx": 3, "title": "模块设计", "sections": [], "key_points": []},
    ]


# ========== marker 帮助函数 ==========
def requires_external() -> pytest.MarkDecorator:
    """返回 requires_external marker (供测试函数使用).

    用法:
        @pytest.mark.requires_external
        async def test_xxx(): ...
    """
    return pytest.mark.requires_external

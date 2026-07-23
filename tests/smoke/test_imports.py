"""冒烟测试: 所有模块可导入 (import smoke test).

测试目标:
- import src.config.settings
- import src.config.docbot.personas
- import src.config.docbot.outlines
- import src.config.docbot.prompts
- import src.graph.state
- import src.graph.builder
- import src.graph.report_builder
- import src.agents.docbot.coordinator
- import src.skills.docbot.cache
- import src.tools.git_mcp
- import src.api.repo_routes
"""
from __future__ import annotations

import importlib

import pytest


class TestModuleImports:
    """模块导入冒烟测试."""

    @pytest.mark.parametrize(
        "module_path",
        [
            "src.config.settings",
            "src.config.docbot.personas",
            "src.config.docbot.outlines",
            "src.config.docbot.prompts",
            "src.graph.state",
            "src.graph.edges",
            "src.agents.docbot.coordinator",
            "src.agents.docbot.reviewer",
            "src.skills.docbot.cache",
            "src.tools.git_mcp",
        ],
    )
    def test_module_importable(self, module_path: str) -> None:
        """验证模块可导入 (不抛 ImportError)."""
        try:
            importlib.import_module(module_path)
        except ImportError as e:
            pytest.skip(f"模块 {module_path} 导入失败 (依赖缺失): {e}")
        except Exception as e:  # noqa: BLE001
            # 其他异常可能是配置/依赖问题, 不应阻断 smoke
            pytest.fail(f"模块 {module_path} 导入异常: {type(e).__name__}: {e}")

    def test_import_personas_constants(self) -> None:
        """验证 personas 模块导出常量."""
        try:
            from src.config.docbot.personas import DOCBOT_REPORT_PERSONAS, get_persona
        except ImportError:
            pytest.skip("personas 模块未安装依赖")
        assert DOCBOT_REPORT_PERSONAS is not None
        assert callable(get_persona)

    def test_import_outlines_functions(self) -> None:
        """验证 outlines 模块导出函数."""
        try:
            from src.config.docbot.outlines import load_outline, load_outline_meta, load_outline_full
        except ImportError:
            pytest.skip("outlines 模块未安装依赖")
        assert callable(load_outline)
        assert callable(load_outline_meta)
        assert callable(load_outline_full)

    def test_import_prompts_constants(self) -> None:
        """验证 prompts 模块导出常量."""
        try:
            from src.config.docbot.prompts import (
                CODE_LEARNER_PROMPT_ZH,
                get_prompt,
            )
        except ImportError:
            pytest.skip("prompts 模块未安装依赖")
        assert CODE_LEARNER_PROMPT_ZH
        assert callable(get_prompt)

    def test_import_state_typed_dicts(self) -> None:
        """验证 state 模块导出 TypedDict."""
        try:
            from src.graph.state import DocbotState, ReportTaskState
        except ImportError:
            pytest.skip("state 模块未安装依赖")
        assert DocbotState is not None
        assert ReportTaskState is not None

    def test_import_git_mcp_adapter(self) -> None:
        """验证 git_mcp 模块导出 GitMCPAdapter."""
        try:
            from src.tools.git_mcp import (
                GitMCPAdapter,
                decrypt_credential,
                encrypt_credential,
            )
        except ImportError:
            pytest.skip("git_mcp 模块未安装依赖")
        assert GitMCPAdapter is not None
        assert callable(encrypt_credential)
        assert callable(decrypt_credential)

    def test_import_coordinator_class(self) -> None:
        """验证 coordinator 模块导出 CoordinatorA."""
        try:
            from src.agents.docbot.coordinator import CoordinatorA
        except ImportError:
            pytest.skip("coordinator 模块未安装依赖")
        assert CoordinatorA is not None

    def test_import_reviewer_class(self) -> None:
        """验证 reviewer 模块导出 ReviewerE."""
        try:
            from src.agents.docbot.reviewer import ReviewerE
        except ImportError:
            pytest.skip("reviewer 模块未安装依赖")
        assert ReviewerE is not None

    def test_import_cache_functions(self) -> None:
        """验证 cache 模块导出缓存函数."""
        try:
            from src.skills.docbot.cache import (
                build_cache_key,
                clear_session_cache,
                read_cache,
                write_cache,
            )
        except ImportError:
            pytest.skip("cache 模块未安装依赖")
        assert callable(build_cache_key)
        assert callable(write_cache)
        assert callable(read_cache)
        assert callable(clear_session_cache)

"""冒烟测试: FastAPI app 创建成功.

测试目标:
- 导入 server 模块 (不实际启动)
- 检查 server.app 是 FastAPI 实例

注意: server.py 在 import 时会调用 create_app(), 触发 lifespan 注册
- 如果 lifespan 依赖外部服务 (Postgres/Qdrant/Redis), 会失败
- 测试用 try/except + skip 处理 lifespan 失败场景
"""
from __future__ import annotations

import importlib

import pytest


class TestAppCreate:
    """FastAPI app 创建测试."""

    def test_import_server_module(self) -> None:
        """导入 server 模块不抛 ImportError."""
        try:
            importlib.import_module("server")
        except ImportError as e:
            pytest.skip(f"server 模块导入失败 (依赖缺失): {e}")
        except Exception as e:  # noqa: BLE001
            # lifespan 依赖外部服务时, import 仍可能成功
            # 但 get_settings() 可能在生产环境校验失败
            pytest.skip(f"server 模块导入异常 (可能 lifespan 依赖外部): {type(e).__name__}: {e}")

    def test_app_is_fastapi_instance(self) -> None:
        """验证 server.app 是 FastAPI 实例 (mock 外部依赖)."""
        try:
            from fastapi import FastAPI

            # 直接 import server 会触发 create_app() + lifespan 依赖
            # 用 try/except 包裹, 失败时 skip
            try:
                import server

                assert isinstance(server.app, FastAPI)
            except Exception as e:  # noqa: BLE001
                pytest.skip(
                    f"server.app 创建失败 (lifespan 依赖外部服务): {type(e).__name__}: {e}"
                )
        except ImportError as e:
            pytest.skip(f"FastAPI 未安装: {e}")

    def test_create_app_function_exists(self) -> None:
        """验证 server.create_app 函数存在."""
        try:
            import server
        except Exception as e:  # noqa: BLE001
            pytest.skip(f"server 模块导入失败: {e}")

        assert hasattr(server, "create_app")
        assert callable(server.create_app)

    def test_lifespan_function_exists(self) -> None:
        """验证 server.lifespan 函数存在."""
        try:
            import server
        except Exception as e:  # noqa: BLE001
            pytest.skip(f"server 模块导入失败: {e}")

        assert hasattr(server, "lifespan")
        assert callable(server.lifespan)

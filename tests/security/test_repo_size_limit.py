"""安全测试: 仓库大小限制 (MAX_REPO_SIZE_MB=1024).

测试目标 (见 AGENTS.md 第 11 章安全硬约束):
- 验证 settings.max_repo_size_mb == 1024
- 验证 GitMCPAdapter.clone_repo 在仓库超限时抛 ValueError (mock subprocess)
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.config.settings import Settings
from src.tools.git_mcp import GitMCPAdapter


class TestRepoSizeLimit:
    """仓库大小限制测试."""

    def test_max_repo_size_mb_default_value(self) -> None:
        """Settings.max_repo_size_mb 默认 1024."""
        assert Settings.model_fields["max_repo_size_mb"].default == 1024

    def test_check_repo_size_under_limit_no_raise(
        self, mock_settings: MagicMock, tmp_path: Path
    ) -> None:
        """小仓库不抛异常."""
        mock_settings.max_repo_size_mb = 1024
        adapter = GitMCPAdapter(settings=mock_settings)
        # 创建 100MB 文件 (< 1024MB)
        (tmp_path / "file.txt").write_text("x" * (100 * 1024 * 1024))
        # 不抛异常
        adapter._check_repo_size(tmp_path)

    def test_check_repo_size_over_limit_raises_value_error(
        self, mock_settings: MagicMock, tmp_path: Path
    ) -> None:
        """超限仓库抛 ValueError."""
        mock_settings.max_repo_size_mb = 100  # 100MB 限制
        adapter = GitMCPAdapter(settings=mock_settings)
        # 创建 200MB 文件
        (tmp_path / "large.bin").write_bytes(b"x" * (200 * 1024 * 1024))
        with pytest.raises(ValueError, match="仓库大小.*超出限制"):
            adapter._check_repo_size(tmp_path)

    def test_check_repo_size_excludes_git_dir(
        self, mock_settings: MagicMock, tmp_path: Path
    ) -> None:
        """.git 目录不计入业务大小 (历史对象可能很大)."""
        mock_settings.max_repo_size_mb = 100
        adapter = GitMCPAdapter(settings=mock_settings)
        # .git 目录下大文件 (应被排除)
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        (git_dir / "objects").write_bytes(b"x" * (200 * 1024 * 1024))
        # 业务文件 (小)
        (tmp_path / "README.md").write_text("hello")
        # 不应抛异常
        adapter._check_repo_size(tmp_path)

    def test_check_repo_size_empty_dir_no_raise(
        self, mock_settings: MagicMock, tmp_path: Path
    ) -> None:
        """空目录不抛异常."""
        mock_settings.max_repo_size_mb = 1024
        adapter = GitMCPAdapter(settings=mock_settings)
        adapter._check_repo_size(tmp_path)

    def test_check_repo_size_exact_limit_no_raise(
        self, mock_settings: MagicMock, tmp_path: Path
    ) -> None:
        """恰好等于限制大小不抛异常 (<=)."""
        mock_settings.max_repo_size_mb = 1  # 1 MB
        adapter = GitMCPAdapter(settings=mock_settings)
        # 创建恰好 1MB 文件 (1024 * 1024 字节)
        (tmp_path / "exact.bin").write_bytes(b"x" * (1024 * 1024))
        adapter._check_repo_size(tmp_path)

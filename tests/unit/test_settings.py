"""单元测试: Settings 默认值 + docbot 专属字段.

测试目标:
- Settings() 默认值: agent_name='agentinsight-docbot', context_max_chars=500_000, max_repo_size_mb=1024
- supported_languages_list == ['zh', 'en']
- supported_report_types_list 含 8 种
"""
from __future__ import annotations

import pytest

# 注意: Settings 在导入时可能因 .env 不存在或生产环境配置失败而无法实例化
# 使用 lru_cache 缓存 + 直接访问类字段避免实例化
from src.config.settings import Settings


class TestSettingsDefaults:
    """Settings 默认值测试."""

    def test_agent_name_default(self) -> None:
        """agent_name 默认值为 'agentinsight-docbot'."""
        # 通过类字段访问默认值 (不实例化)
        fields = Settings.model_fields
        assert "agent_name" in fields
        # 默认值通过 Pydantic FieldInfo.default 获取
        assert fields["agent_name"].default == "agentinsight-docbot"

    def test_context_max_chars_default(self) -> None:
        """context_max_chars 默认 500_000."""
        assert Settings.model_fields["context_max_chars"].default == 500_000

    def test_max_repo_size_mb_default(self) -> None:
        """max_repo_size_mb 默认 1024 (MB)."""
        assert Settings.model_fields["max_repo_size_mb"].default == 1024

    def test_max_revisions_per_chapter_default(self) -> None:
        """max_revisions_per_chapter 默认 3 (D-E 修订循环硬上限)."""
        assert Settings.model_fields["max_revisions_per_chapter"].default == 3

    def test_max_concurrent_reports_default(self) -> None:
        """max_concurrent_reports 默认 3 (单次请求最多并发派发 3 个 B 子图)."""
        assert Settings.model_fields["max_concurrent_reports"].default == 3

    def test_max_chapters_per_report_default(self) -> None:
        """max_chapters_per_report 默认 20."""
        assert Settings.model_fields["max_chapters_per_report"].default == 20

    def test_docbot_cache_ttl_default(self) -> None:
        """docbot_cache_ttl 默认 86400 (24 小时)."""
        assert Settings.model_fields["docbot_cache_ttl"].default == 86400

    def test_docbot_outlines_dir_default(self) -> None:
        """docbot_outlines_dir 默认 'src/config/docbot/outlines' (YAML 大纲目录, 与代码同包)."""
        assert Settings.model_fields["docbot_outlines_dir"].default == "src/config/docbot/outlines"

    def test_git_credential_key_default_none(self) -> None:
        """git_credential_key 默认 None (需环境变量注入)."""
        assert Settings.model_fields["git_credential_key"].default is None

    def test_allowed_git_domains_default_empty(self) -> None:
        """allowed_git_domains 默认空 (允许全部)."""
        assert Settings.model_fields["allowed_git_domains"].default == ""


class TestSettingsListProperties:
    """Settings 列表属性测试 (通过实例化验证)."""

    @pytest.fixture
    def settings_instance(self, monkeypatch: pytest.MonkeyPatch) -> Settings:
        """提供一个 Settings 实例 (mock 环境变量, 避免 .env 加载)."""
        # 清空可能影响的环境变量
        for var in (
            "ENV",
            "AGENTINSIGHT_PUBLIC_KEY",
            "AGENTINSIGHT_SECRET_KEY",
            "POSTGRES_PASSWORD",
            "ALLOWED_GIT_DOMAINS",
            "CORS_ALLOW_ORIGINS",
        ):
            monkeypatch.delenv(var, raising=False)
        monkeypatch.setenv("ENV", "dev")
        # 通过 SettingsConfigDict 配置 env_file=None 不可行, 直接构造
        return Settings(_env_file=None)

    def test_supported_languages_default(self, settings_instance: Settings) -> None:
        """supported_languages 默认 'zh,en'."""
        assert settings_instance.supported_languages == "zh,en"

    def test_supported_languages_list(self, settings_instance: Settings) -> None:
        """supported_languages_list 返回 ['zh', 'en']."""
        assert settings_instance.supported_languages_list == ["zh", "en"]

    def test_supported_report_types_default(self, settings_instance: Settings) -> None:
        """supported_report_types 默认含 8 种 (逗号分隔)."""
        types_str = settings_instance.supported_report_types
        types_list = [t.strip() for t in types_str.split(",") if t.strip()]
        assert len(types_list) == 8

    def test_supported_report_types_list_contains_eight(
        self, settings_instance: Settings
    ) -> None:
        """supported_report_types_list 含 8 种类型."""
        types_list = settings_instance.supported_report_types_list
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
        assert set(types_list) == expected
        assert len(types_list) == 8

    def test_cors_origins_list_default(self) -> None:
        """cors_allow_origins 默认含 localhost:8068.

        通过 model_fields 访问默认值 (避免环境变量污染).
        """
        default = Settings.model_fields["cors_allow_origins"].default
        assert "http://localhost:8068" in default

    def test_allowed_git_domains_list_default_empty(self, settings_instance: Settings) -> None:
        """allowed_git_domains_list 默认空列表."""
        assert settings_instance.allowed_git_domains_list == []


class TestSettingsValidation:
    """Settings 校验逻辑测试."""

    def test_env_invalid_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """env 字段校验: 非 dev/prod 抛 ValidationError (Pydantic 2.x).

        Pydantic 2.x ValidationError 是 ValueError 子类, 但 match 不匹配原 message.
        用 ValidationError 验证 + 检查 message 含 'dev' 或 'prod'.
        """
        from pydantic import ValidationError

        monkeypatch.setenv("ENV", "invalid_env")
        with pytest.raises(ValidationError) as exc_info:
            Settings(_env_file=None)
        # message 含 'dev' 或 'prod'
        msg = str(exc_info.value)
        assert "dev" in msg and "prod" in msg

    def test_env_dev_ok(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """env='dev' 通过校验."""
        monkeypatch.setenv("ENV", "dev")
        s = Settings(_env_file=None)
        assert s.env == "dev"

    def test_validate_production_skipped_in_dev(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """validate_production 在 env='dev' 时不抛异常 (即使密钥缺失)."""
        monkeypatch.setenv("ENV", "dev")
        monkeypatch.delenv("AGENTINSIGHT_PUBLIC_KEY", raising=False)
        monkeypatch.delenv("POSTGRES_PASSWORD", raising=False)
        s = Settings(_env_file=None)
        s.validate_production()  # 不抛异常

    def test_postgres_dsn_format(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """postgres_dsn 返回 asyncpg 格式."""
        monkeypatch.setenv("ENV", "dev")
        monkeypatch.setenv("POSTGRES_HOST", "testhost")
        monkeypatch.setenv("POSTGRES_USER", "testuser")
        monkeypatch.setenv("POSTGRES_PASSWORD", "testpass")
        monkeypatch.setenv("POSTGRES_DB", "testdb")
        s = Settings(_env_file=None)
        dsn = s.postgres_dsn
        assert "postgresql+asyncpg://" in dsn
        assert "testhost" in dsn
        assert "testuser" in dsn
        assert "testdb" in dsn

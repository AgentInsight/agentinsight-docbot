"""安全测试: init.sql 无密钥/密码硬编码.

测试目标 (见 AGENTS.md 第 5 章安全合规红线):
- init.sql 不含硬编码密码 (PASSWORD 'xxx' 字面量)
- init.sql 不含 API Key 模式 (sk-xxx / AKIAxxx)
- init.sql 不含 JWT secret 字面量
- init.sql 不含带凭证的连接字符串 (postgres://user:pass@host)
- init.sql 不含私钥块 (BEGIN PRIVATE KEY / BEGIN RSA PRIVATE KEY)
- init.sql 不含明文 token 字面量

纯文件扫描, 不依赖外部服务.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).parent.parent.parent
_INIT_SQL_PATH = _PROJECT_ROOT / "scripts" / "init.sql"


class TestInitSqlNoSensitive:
    """init.sql 无密钥/密码硬编码测试."""

    @pytest.fixture(scope="class")
    def init_sql_content(self) -> str:
        """读取 init.sql 全文 (类作用域, 避免重复 IO)."""
        assert _INIT_SQL_PATH.exists(), f"init.sql 不存在: {_INIT_SQL_PATH}"
        return _INIT_SQL_PATH.read_text(encoding="utf-8")

    def test_init_sql_file_exists(self) -> None:
        """验证 init.sql 文件存在 (前置条件)."""
        assert _INIT_SQL_PATH.exists(), f"init.sql 不存在: {_INIT_SQL_PATH}"

    def test_no_hardcoded_password_literals(self, init_sql_content: str) -> None:
        """验证 init.sql 不含硬编码 PASSWORD 'xxx' 字面量.

        检测模式: PASSWORD '非空字符串' (PostgreSQL 角色密码 / 应用密码).
        允许: 列名 encrypted_password / auth_type='password' (枚举值).
        """
        # 匹配 PASSWORD '<非空>' 或 password = '<非空>' 形式 (大小写不敏感)
        # 排除: encrypted_password (列名), auth_type='password' (枚举值)
        pattern = re.compile(
            r"(?<!encrypted_)(?<!auth_type=['\"])PASSWORD\s+'[^']+'",
            re.IGNORECASE,
        )
        matches = pattern.findall(init_sql_content)
        assert not matches, (
            f"init.sql 含硬编码 PASSWORD 字面量 (违反第 5 章硬约束): {matches}"
        )

    def test_no_api_key_patterns(self, init_sql_content: str) -> None:
        """验证 init.sql 不含 API Key 模式 (OpenAI sk- / AWS AKIA / 通用长 token)."""
        # OpenAI API Key: sk- + 至少 20 位字母数字
        openai_pattern = re.compile(r"sk-[A-Za-z0-9]{20,}")
        # AWS Access Key: AKIA + 16 位大写字母数字
        aws_pattern = re.compile(r"AKIA[A-Z0-9]{16}")
        # 通用 API Key 字面量: api_key = 'xxx' 或 apikey = 'xxx'
        api_key_pattern = re.compile(
            r"api[_-]?key\s*[:=]\s*['\"][^'\"]{8,}['\"]",
            re.IGNORECASE,
        )
        assert not openai_pattern.findall(init_sql_content), (
            "init.sql 含 OpenAI API Key 模式 (sk-xxx)"
        )
        assert not aws_pattern.findall(init_sql_content), (
            "init.sql 含 AWS Access Key 模式 (AKIAxxx)"
        )
        assert not api_key_pattern.findall(init_sql_content), (
            "init.sql 含 api_key 字面量"
        )

    def test_no_jwt_secret_literals(self, init_sql_content: str) -> None:
        """验证 init.sql 不含 JWT secret 字面量."""
        # jwt_secret = 'xxx' 或 jwt_secret_key = 'xxx'
        pattern = re.compile(
            r"jwt[_-]?secret(?:[_-]?key)?\s*[:=]\s*['\"][^'\"]{8,}['\"]",
            re.IGNORECASE,
        )
        matches = pattern.findall(init_sql_content)
        assert not matches, (
            f"init.sql 含 JWT secret 字面量 (违反第 5 章硬约束): {matches}"
        )

    def test_no_connection_string_with_credentials(self, init_sql_content: str) -> None:
        """验证 init.sql 不含带凭证的连接字符串 (postgres://user:pass@host)."""
        # 匹配 postgres:// 或 postgresql:// 后跟 user:pass@host 形式
        pattern = re.compile(
            r"postgres(?:ql)?://[^:\s]+:[^@\s]+@",
            re.IGNORECASE,
        )
        matches = pattern.findall(init_sql_content)
        assert not matches, (
            f"init.sql 含带凭证的连接字符串 (违反第 5 章硬约束): {matches}"
        )

    def test_no_private_key_blocks(self, init_sql_content: str) -> None:
        """验证 init.sql 不含私钥块 (BEGIN PRIVATE KEY / BEGIN RSA PRIVATE KEY / BEGIN OPENSSH)."""
        patterns = [
            r"-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY-----",
            r"-----BEGIN\s+OPENSSH\s+PRIVATE\s+KEY-----",
            r"-----BEGIN\s+EC\s+PRIVATE\s+KEY-----",
        ]
        for pattern in patterns:
            matches = re.findall(pattern, init_sql_content)
            assert not matches, (
                f"init.sql 含私钥块 (违反第 5 章硬约束): {matches}"
            )

    def test_no_plaintext_token_literals(self, init_sql_content: str) -> None:
        """验证 init.sql 不含明文 token 字面量 (token = 'xxx' / secret = 'xxx').

        允许: 列名 encrypted_token / auth_type='token' (枚举值) / 注释中的 token.
        """
        # 匹配 token = 'xxx' 或 secret = 'xxx' (排除 encrypted_token 列定义)
        # 排除: encrypted_token / ssh_passphrase 列名定义
        token_pattern = re.compile(
            r"(?<!encrypted_)(?<!\w)(?:token|secret)\s*[:=]\s*['\"][^'\"]{8,}['\"]",
            re.IGNORECASE,
        )
        matches = token_pattern.findall(init_sql_content)
        # 过滤掉 auth_type='token' 这类枚举值 (token 短, 但模式可能误匹配)
        # 进一步: 排除注释行 (-- 开头)
        real_matches = []
        for line in init_sql_content.splitlines():
            stripped = line.lstrip()
            if stripped.startswith("--"):
                continue
            line_matches = token_pattern.findall(line)
            # 排除 auth_type='token' 模式 (token 后是单引号, 但前缀是 auth_type=)
            for m in line_matches:
                if "auth_type" in line.lower():
                    continue
                real_matches.append(m)
        assert not real_matches, (
            f"init.sql 含明文 token/secret 字面量 (违反第 5 章硬约束): {real_matches}"
        )

    def test_no_hardcoded_encryption_keys(self, init_sql_content: str) -> None:
        """验证 init.sql 不含硬编码加密密钥字面量 (aes_key / encryption_key / git_credential_key)."""
        pattern = re.compile(
            r"(?:aes[_-]?key|encryption[_-]?key|git[_-]?credential[_-]?key)\s*[:=]\s*['\"][^'\"]{8,}['\"]",
            re.IGNORECASE,
        )
        matches = pattern.findall(init_sql_content)
        assert not matches, (
            f"init.sql 含硬编码加密密钥字面量 (违反第 5 章硬约束): {matches}"
        )

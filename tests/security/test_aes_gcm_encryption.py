"""安全测试: 敏感字段 AES-GCM 加密存储.

测试目标 (见 AGENTS.md 第 11 章安全硬约束):
- 加密后的密文与明文不同
- 不同明文加密后密文不同 (nonce 随机)
- 解密需要正确密钥
"""
from __future__ import annotations

import base64

from src.tools.git_mcp import decrypt_credential, encrypt_credential

# 32 字节 ASCII 测试密钥
_TEST_KEY = "a" * 32


class TestAesGcmEncryptionSecurity:
    """AES-GCM 加密安全测试."""

    def test_ciphertext_differs_from_plaintext(self) -> None:
        """加密后的密文与明文不同."""
        plaintext = "ghp_abc123secret_token"
        encrypted = encrypt_credential(plaintext, _TEST_KEY)
        assert encrypted is not None
        assert encrypted != plaintext

    def test_different_plaintexts_produce_different_ciphertexts(self) -> None:
        """不同明文加密后密文不同."""
        plaintext1 = "token1"
        plaintext2 = "token2"
        encrypted1 = encrypt_credential(plaintext1, _TEST_KEY)
        encrypted2 = encrypt_credential(plaintext2, _TEST_KEY)
        assert encrypted1 != encrypted2

    def test_same_plaintext_different_nonce(self) -> None:
        """同一明文加密两次密文不同 (nonce 随机, 防重放)."""
        plaintext = "same_secret"
        encrypted1 = encrypt_credential(plaintext, _TEST_KEY)
        encrypted2 = encrypt_credential(plaintext, _TEST_KEY)
        assert encrypted1 != encrypted2

    def test_decrypt_requires_correct_key(self) -> None:
        """解密需要正确密钥 (错误密钥返回 None)."""
        plaintext = "secret_data"
        encrypted = encrypt_credential(plaintext, _TEST_KEY)
        wrong_key = "b" * 32  # 不同密钥
        result = decrypt_credential(encrypted, wrong_key)
        assert result is None

    def test_tampered_ciphertext_fails(self) -> None:
        """密文被篡改后, 解密失败 (AES-GCM tag 校验)."""
        plaintext = "secret"
        encrypted = encrypt_credential(plaintext, _TEST_KEY)
        # 翻转密文最后一字节 (tag)
        raw = bytearray(base64.b64decode(encrypted))
        raw[-1] ^= 0xFF
        tampered = base64.b64encode(bytes(raw)).decode("ascii")
        result = decrypt_credential(tampered, _TEST_KEY)
        assert result is None

    def test_short_ciphertext_fails(self) -> None:
        """密文过短 (< nonce + tag) 返回 None."""
        short = base64.b64encode(b"\x00" * 10).decode("ascii")
        result = decrypt_credential(short, _TEST_KEY)
        assert result is None

    def test_encryption_does_not_leak_plaintext(self) -> None:
        """密文不应包含明文子串 (即使 ASCII)."""
        plaintext = "MY_SECRET_TOKEN_12345"
        encrypted = encrypt_credential(plaintext, _TEST_KEY)
        # 密文为 base64, 不应直接含明文
        assert plaintext not in encrypted

    def test_round_trip_preserves_data(self) -> None:
        """加解密往返保留数据 (含特殊字符)."""
        test_cases = [
            "ghp_normal_token",
            "user@example.com:password123",
            "-----BEGIN RSA PRIVATE KEY-----\nkey_content\n-----END RSA PRIVATE KEY-----",
            "中文密码🔐unicode",
            "x" * 5000,  # 长文本
        ]
        for plaintext in test_cases:
            encrypted = encrypt_credential(plaintext, _TEST_KEY)
            decrypted = decrypt_credential(encrypted, _TEST_KEY)
            assert decrypted == plaintext, f"加解密往返失败: {plaintext[:30]}..."

    def test_none_plaintext_returns_none(self) -> None:
        """None 明文返回 None (不抛异常)."""
        assert encrypt_credential(None, _TEST_KEY) is None

    def test_empty_plaintext_returns_none(self) -> None:
        """空字符串明文返回 None."""
        assert encrypt_credential("", _TEST_KEY) is None

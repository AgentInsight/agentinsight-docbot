"""单元测试: AES-GCM 加解密 (敏感字段加密存储).

测试目标 (见 AGENTS.md 第 11 章安全硬约束):
- encrypt_credential + decrypt_credential 往返
- encrypt_credential(None, key) 返回 None
- decrypt_credential('invalid', key) 抛异常 (实际实现返回 None, 降级)
"""
from __future__ import annotations

import base64

from src.tools.git_mcp import (
    _decode_credential_key,
    decrypt_credential,
    encrypt_credential,
)

# 32 字节 ASCII 密钥 (用于测试, 不入仓)
_TEST_KEY = "a" * 32  # 32 字符 ASCII (UTF-8 编码后取前 32 字节)
_HEX_KEY = "ab" * 32  # 64 字符 hex (32 字节)


class TestDecodeCredentialKey:
    """_decode_credential_key 函数测试."""

    def test_decode_hex_key(self) -> None:
        """64 字符 hex 解码为 32 字节."""
        key_bytes = _decode_credential_key(_HEX_KEY)
        assert len(key_bytes) == 32
        assert key_bytes == bytes.fromhex(_HEX_KEY)

    def test_decode_base64_key(self) -> None:
        """base64 编码的 32 字节解码."""
        raw = b"\x00" * 32
        b64 = base64.b64encode(raw).decode("ascii")
        key_bytes = _decode_credential_key(b64)
        assert key_bytes == raw

    def test_decode_ascii_key_padded(self) -> None:
        """不足 32 字节的 ASCII 字符串用 NUL 填充到 32 字节."""
        key_bytes = _decode_credential_key("short")
        assert len(key_bytes) == 32
        assert key_bytes.startswith(b"short")
        assert key_bytes.endswith(b"\x00" * (32 - 5))

    def test_decode_ascii_key_exact_32_bytes(self) -> None:
        """32 字符 ASCII 字符串取前 32 字节."""
        key = "a" * 32
        key_bytes = _decode_credential_key(key)
        assert len(key_bytes) == 32
        assert key_bytes == b"a" * 32


class TestEncryptDecryptRoundTrip:
    """encrypt_credential + decrypt_credential 往返测试."""

    def test_round_trip_ascii_key(self) -> None:
        """32 字节 ASCII 密钥加解密往返."""
        plaintext = "ghp_abc123secret_token"
        encrypted = encrypt_credential(plaintext, _TEST_KEY)
        assert encrypted is not None
        assert encrypted != plaintext  # 密文与明文不同

        decrypted = decrypt_credential(encrypted, _TEST_KEY)
        assert decrypted == plaintext

    def test_round_trip_hex_key(self) -> None:
        """64 字符 hex 密钥加解密往返."""
        plaintext = "user_password_123"
        encrypted = encrypt_credential(plaintext, _HEX_KEY)
        assert encrypted is not None

        decrypted = decrypt_credential(encrypted, _HEX_KEY)
        assert decrypted == plaintext

    def test_round_trip_long_text(self) -> None:
        """长文本 (SSH 私钥) 加解密往返."""
        plaintext = "-----BEGIN RSA PRIVATE KEY-----\n" + "x" * 1000 + "\n-----END RSA PRIVATE KEY-----"
        encrypted = encrypt_credential(plaintext, _TEST_KEY)
        decrypted = decrypt_credential(encrypted, _TEST_KEY)
        assert decrypted == plaintext

    def test_round_trip_unicode(self) -> None:
        """Unicode 字符 (中文) 加解密往返."""
        plaintext = "中文密码测试🔐"
        encrypted = encrypt_credential(plaintext, _TEST_KEY)
        decrypted = decrypt_credential(encrypted, _TEST_KEY)
        assert decrypted == plaintext

    def test_encrypted_format_is_base64(self) -> None:
        """加密结果为 base64 字符串 (nonce + ciphertext + tag)."""
        encrypted = encrypt_credential("test", _TEST_KEY)
        assert encrypted is not None
        # 应能 base64 解码
        raw = base64.b64decode(encrypted)
        # 至少含 nonce (12) + tag (16) + 明文
        assert len(raw) >= 12 + 16

    def test_different_encryptions_same_plaintext_differ(self) -> None:
        """同一明文加密两次密文不同 (因 nonce 随机)."""
        plaintext = "same_secret"
        encrypted1 = encrypt_credential(plaintext, _TEST_KEY)
        encrypted2 = encrypt_credential(plaintext, _TEST_KEY)
        assert encrypted1 != encrypted2  # nonce 不同


class TestEncryptEdgeCases:
    """encrypt_credential 边界条件测试."""

    def test_encrypt_none_plaintext_returns_none(self) -> None:
        """encrypt_credential(None, key) 返回 None."""
        assert encrypt_credential(None, _TEST_KEY) is None

    def test_encrypt_empty_plaintext_returns_none(self) -> None:
        """encrypt_credential('', key) 返回 None (falsy 短路)."""
        assert encrypt_credential("", _TEST_KEY) is None

    def test_encrypt_none_key_returns_none(self) -> None:
        """encrypt_credential(plaintext, None) 返回 None."""
        assert encrypt_credential("secret", None) is None

    def test_encrypt_empty_key_returns_none(self) -> None:
        """encrypt_credential(plaintext, '') 返回 None."""
        assert encrypt_credential("secret", "") is None


class TestDecryptEdgeCases:
    """decrypt_credential 边界条件测试."""

    def test_decrypt_none_returns_none(self) -> None:
        """decrypt_credential(None, key) 返回 None."""
        assert decrypt_credential(None, _TEST_KEY) is None

    def test_decrypt_empty_returns_none(self) -> None:
        """decrypt_credential('', key) 返回 None."""
        assert decrypt_credential("", _TEST_KEY) is None

    def test_decrypt_invalid_base64_returns_none(self) -> None:
        """decrypt_credential('not_base64!', key) 返回 None (降级, 不抛异常)."""
        # 实际实现 catch 异常并返回 None
        result = decrypt_credential("!!!invalid_base64!!!", _TEST_KEY)
        assert result is None

    def test_decrypt_tampered_ciphertext_returns_none(self) -> None:
        """decrypt_credential 篡改后的密文返回 None (AES-GCM tag 校验失败)."""
        plaintext = "secret"
        encrypted = encrypt_credential(plaintext, _TEST_KEY)
        assert encrypted is not None

        # 篡改 ciphertext (修改末尾)
        raw = bytearray(base64.b64decode(encrypted))
        raw[-1] ^= 0xFF  # 翻转最后一字节 (tag)
        tampered = base64.b64encode(bytes(raw)).decode("ascii")

        result = decrypt_credential(tampered, _TEST_KEY)
        assert result is None  # AES-GCM 校验失败

    def test_decrypt_wrong_key_returns_none(self) -> None:
        """decrypt_credential 用错误密钥返回 None (AES-GCM 校验失败)."""
        plaintext = "secret"
        encrypted = encrypt_credential(plaintext, _TEST_KEY)
        wrong_key = "b" * 32  # 不同密钥
        result = decrypt_credential(encrypted, wrong_key)
        assert result is None

    def test_decrypt_too_short_returns_none(self) -> None:
        """decrypt_credential 密文过短 (< 12 + 16 字节) 返回 None."""
        # 16 字节 base64 (decode 后小于 12 + 16)
        short_data = base64.b64encode(b"\x00" * 10).decode("ascii")
        result = decrypt_credential(short_data, _TEST_KEY)
        assert result is None

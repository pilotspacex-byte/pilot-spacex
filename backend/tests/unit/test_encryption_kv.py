"""Unit tests for EncryptedKVService (T012).

Tests round-trip encrypt→decrypt, empty dict, unicode values, and large dict.
"""

from __future__ import annotations

import pytest

from pilot_space.infrastructure.encryption_kv import (
    EncryptedKVError,
    decrypt_kv,
    encrypt_kv,
)


class TestEncryptKv:
    """Tests for encrypt_kv function."""

    def test_round_trip_simple(self) -> None:
        """encrypt_kv → decrypt_kv returns original dict."""
        data = {"X-Header": "value", "Authorization": "Bearer sk-123"}
        blob = encrypt_kv(data)
        assert isinstance(blob, str)
        assert len(blob) > 40  # Fernet ciphertext is non-trivial length
        result = decrypt_kv(blob)
        assert result == data

    def test_empty_dict(self) -> None:
        """Empty dict round-trips correctly."""
        data: dict[str, str] = {}
        blob = encrypt_kv(data)
        result = decrypt_kv(blob)
        assert result == {}

    def test_unicode_values(self) -> None:
        """Unicode values in dict round-trip correctly."""
        data = {"GREETING": "héllo wörld 🎉", "API_KEY": "秘密-key-123"}
        blob = encrypt_kv(data)
        result = decrypt_kv(blob)
        assert result == data

    def test_large_dict(self) -> None:
        """Large dict (20 entries) round-trips correctly."""
        data = {f"KEY_{i:02d}": f"value-{i}-{'x' * 50}" for i in range(20)}
        blob = encrypt_kv(data)
        result = decrypt_kv(blob)
        assert result == data

    def test_blob_is_not_plaintext(self) -> None:
        """The encrypted blob does not contain the plaintext key or value."""
        data = {"SECRET_KEY": "my-plaintext-secret"}
        blob = encrypt_kv(data)
        assert "my-plaintext-secret" not in blob
        assert "SECRET_KEY" not in blob

    def test_different_blobs_for_same_input(self) -> None:
        """Fernet encryption is non-deterministic — same input produces different blobs."""
        data = {"KEY": "value"}
        blob1 = encrypt_kv(data)
        blob2 = encrypt_kv(data)
        # Both should decrypt to the same value
        assert decrypt_kv(blob1) == data
        assert decrypt_kv(blob2) == data
        # But the blobs themselves should differ (Fernet uses random IV)
        assert blob1 != blob2


class TestDecryptKv:
    """Tests for decrypt_kv function."""

    def test_invalid_blob_raises_error(self) -> None:
        """Invalid ciphertext raises EncryptedKVError."""
        with pytest.raises(EncryptedKVError):
            decrypt_kv("this-is-not-valid-fernet-ciphertext")

    def test_non_dict_json_raises_error(self) -> None:
        """JSON array (not object) raises EncryptedKVError after decryption."""
        # Encrypt a JSON array to simulate a corrupt blob
        import json

        from pilot_space.infrastructure.encryption import encrypt_api_key

        bad_blob = encrypt_api_key(json.dumps(["not", "a", "dict"]))
        with pytest.raises(EncryptedKVError, match="JSON object"):
            decrypt_kv(bad_blob)

    def test_non_string_values_raise_error(self) -> None:
        """Dict with non-string values raises EncryptedKVError."""
        import json

        from pilot_space.infrastructure.encryption import encrypt_api_key

        bad_blob = encrypt_api_key(json.dumps({"KEY": 123}))
        with pytest.raises(EncryptedKVError, match="string keys and values"):
            decrypt_kv(bad_blob)

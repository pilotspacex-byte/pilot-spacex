"""EncryptedKVService — Fernet-encrypted JSON key-value store.

Encrypts a dict[str, str] to a Fernet-encoded JSON blob for storage in
``headers_encrypted`` and ``env_vars_encrypted`` columns on WorkspaceMcpServer.

Uses the same Fernet key as ``encrypt_api_key`` / ``decrypt_api_key``
(the global EncryptionService singleton).
"""

from __future__ import annotations

import json

from pilot_space.infrastructure.encryption import decrypt_api_key, encrypt_api_key
from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)


class EncryptedKVError(Exception):
    """Raised when KV encryption or decryption fails."""


def encrypt_kv(data: dict[str, str]) -> str:
    """Encrypt a string key-value mapping to a Fernet-encoded blob.

    Steps:
        1. Serialize ``data`` to a compact JSON string.
        2. Pass the JSON string through ``encrypt_api_key`` (Fernet).

    Args:
        data: Dictionary of string keys and string values to encrypt.

    Returns:
        Fernet-encoded ciphertext suitable for storage in a TEXT column.

    Raises:
        EncryptedKVError: If serialisation or encryption fails.
    """
    try:
        json_str = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
        return encrypt_api_key(json_str)
    except Exception as exc:
        raise EncryptedKVError(f"KV encryption failed: {exc}") from exc


def _validate_kv_data(data: object) -> dict[str, str]:
    """Validate that ``data`` is a dict[str, str] and return it.

    Raises:
        EncryptedKVError: If ``data`` is not a JSON object or contains non-string values.
    """
    if not isinstance(data, dict):
        raise EncryptedKVError("Decrypted KV blob is not a JSON object")
    for k, v in data.items():
        if not isinstance(k, str) or not isinstance(v, str):
            raise EncryptedKVError(
                f"KV blob must contain only string keys and values; got key={k!r}"
            )
    return data  # type: ignore[return-value]


def decrypt_kv(blob: str) -> dict[str, str]:
    """Decrypt a Fernet-encoded blob back to a string key-value mapping.

    Steps:
        1. Decrypt with ``decrypt_api_key`` (Fernet).
        2. Parse the resulting JSON string.
        3. Validate that every key and value is a plain string.

    Args:
        blob: Fernet-encoded ciphertext previously produced by ``encrypt_kv``.

    Returns:
        The original ``dict[str, str]`` mapping.

    Raises:
        EncryptedKVError: If decryption, JSON parsing, or type validation fails.
    """
    try:
        json_str = decrypt_api_key(blob)
        data = json.loads(json_str)
        return _validate_kv_data(data)
    except EncryptedKVError:
        raise
    except Exception as exc:
        raise EncryptedKVError(f"KV decryption failed: {exc}") from exc


__all__ = ["EncryptedKVError", "decrypt_kv", "encrypt_kv"]

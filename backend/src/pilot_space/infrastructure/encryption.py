"""Encryption utilities for sensitive data.

Provides Fernet-based symmetric encryption for API keys and other secrets.
"""

from __future__ import annotations

import base64
import hashlib
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

from pilot_space.domain.exceptions import AppError
from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)


class EncryptionError(AppError):
    """Raised when encryption/decryption fails."""

    http_status: int = 500
    error_code: str = "encryption_error"


class EncryptionService:
    """Fernet-based encryption service for API keys.

    Uses Fernet symmetric encryption (AES-128-CBC with HMAC-SHA256).
    Keys are stored encrypted and only decrypted when needed.

    Attributes:
        _fernet: Fernet cipher instance.
    """

    def __init__(self, encryption_key: str) -> None:
        """Initialize encryption service.

        Args:
            encryption_key: Base64-encoded 32-byte Fernet key.
                          If empty or invalid, a key is derived from a default seed.

        Raises:
            EncryptionError: If key initialization fails.
        """
        try:
            if encryption_key:
                # Validate and use provided key
                self._fernet = Fernet(encryption_key.encode())
            else:
                # Generate deterministic key for development (NOT for production)
                logger.warning(
                    "No encryption key configured. Using derived key. "
                    "Set ENCRYPTION_KEY env var for production."
                )
                derived_key = self._derive_key("pilot-space-dev-encryption-seed")
                self._fernet = Fernet(derived_key)
        except (ValueError, TypeError) as e:
            logger.exception("Invalid encryption key configuration", exc_info=e)
            raise EncryptionError("Encryption key configuration is invalid") from e

    @staticmethod
    def _derive_key(seed: str) -> bytes:
        """Derive a Fernet key from a seed string.

        Uses SHA256 hash truncated to 32 bytes, then base64 encoded.

        Args:
            seed: Seed string for key derivation.

        Returns:
            Base64-encoded 32-byte key suitable for Fernet.
        """
        hash_bytes = hashlib.sha256(seed.encode()).digest()
        return base64.urlsafe_b64encode(hash_bytes)

    @staticmethod
    def generate_key() -> str:
        """Generate a new Fernet encryption key.

        Returns:
            Base64-encoded 32-byte key.
        """
        return Fernet.generate_key().decode()

    def encrypt(self, plaintext: str) -> str:
        """Encrypt a plaintext string.

        Args:
            plaintext: The string to encrypt.

        Returns:
            Base64-encoded encrypted ciphertext.

        Raises:
            EncryptionError: If encryption fails.
        """
        if not plaintext:
            raise EncryptionError("Cannot encrypt empty string")

        try:
            encrypted = self._fernet.encrypt(plaintext.encode())
            return encrypted.decode()
        except Exception as e:
            logger.exception("Encryption operation failed", exc_info=e)
            raise EncryptionError("Encryption operation failed") from e

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt a ciphertext string.

        Args:
            ciphertext: Base64-encoded encrypted string.

        Returns:
            Decrypted plaintext.

        Raises:
            EncryptionError: If decryption fails (wrong key or corrupted data).
        """
        if not ciphertext:
            raise EncryptionError("Cannot decrypt empty string")

        try:
            decrypted = self._fernet.decrypt(ciphertext.encode())
            return decrypted.decode()
        except InvalidToken as e:
            logger.exception("Decryption failed: invalid token", exc_info=e)
            raise EncryptionError("Decryption failed") from e
        except Exception as e:
            logger.exception("Decryption operation failed", exc_info=e)
            raise EncryptionError("Decryption failed") from e

    def is_valid_ciphertext(self, ciphertext: str) -> bool:
        """Check if ciphertext can be decrypted.

        Args:
            ciphertext: The ciphertext to validate.

        Returns:
            True if ciphertext is valid and can be decrypted.
        """
        try:
            self.decrypt(ciphertext)
        except EncryptionError:
            return False
        else:
            return True


@lru_cache(maxsize=1)
def get_encryption_service() -> EncryptionService:
    """Get singleton encryption service instance.

    Lazily initializes from settings. Uses lru_cache for singleton pattern.

    Returns:
        Configured EncryptionService instance.
    """
    from pilot_space.config import get_settings

    settings = get_settings()
    return EncryptionService(settings.encryption_key.get_secret_value())


def encrypt_api_key(api_key: str) -> str:
    """Encrypt an API key for storage.

    Convenience function using the global encryption service.

    Args:
        api_key: Plain API key to encrypt.

    Returns:
        Encrypted API key.
    """
    service = get_encryption_service()
    return service.encrypt(api_key)


def decrypt_api_key(encrypted_key: str) -> str:
    """Decrypt a stored API key.

    Convenience function using the global encryption service.

    Args:
        encrypted_key: Encrypted API key from database.

    Returns:
        Decrypted plain API key.
    """
    service = get_encryption_service()
    return service.decrypt(encrypted_key)

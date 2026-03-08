"""AES-256-GCM file encryption and decryption using PBKDF2 key derivation.

Binary format of encrypted files:
  [0:4]   magic bytes b"PSBC" (Pilot Space Backup Cipher)
  [4:20]  16-byte random salt (for PBKDF2)
  [20:32] 12-byte random nonce (for AES-GCM)
  [32:]   ciphertext + 16-byte GCM authentication tag

Key derivation: PBKDF2HMAC-SHA256, 260_000 iterations, 32-byte output.
"""

from __future__ import annotations

import os
from pathlib import Path

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

_MAGIC = b"PSBC"
_SALT_SIZE = 16
_NONCE_SIZE = 12
_KEY_SIZE = 32  # 256-bit
_PBKDF2_ITERATIONS = 260_000


def _derive_key(passphrase: str, salt: bytes) -> bytes:
    """Derive a 256-bit key from passphrase + salt using PBKDF2-SHA256."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=_KEY_SIZE,
        salt=salt,
        iterations=_PBKDF2_ITERATIONS,
    )
    return kdf.derive(passphrase.encode())


def encrypt_file(input_path: Path, output_path: Path, passphrase: str) -> None:
    """Encrypt a file using AES-256-GCM.

    Writes: magic(4) + salt(16) + nonce(12) + ciphertext.

    Args:
        input_path: Path to the plaintext file to encrypt.
        output_path: Path where the encrypted file will be written.
        passphrase: Passphrase for key derivation.
    """
    salt = os.urandom(_SALT_SIZE)
    nonce = os.urandom(_NONCE_SIZE)
    key = _derive_key(passphrase, salt)
    aesgcm = AESGCM(key)

    plaintext = input_path.read_bytes()
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)

    with output_path.open("wb") as f:
        f.write(_MAGIC)
        f.write(salt)
        f.write(nonce)
        f.write(ciphertext)


def decrypt_file(input_path: Path, output_path: Path, passphrase: str) -> None:
    """Decrypt a file encrypted by encrypt_file().

    Verifies the magic bytes header before attempting decryption.

    Args:
        input_path: Path to the encrypted file.
        output_path: Path where the decrypted content will be written.
        passphrase: Passphrase for key derivation (must match encryption passphrase).

    Raises:
        ValueError: If the file does not start with the expected magic bytes.
        cryptography.exceptions.InvalidTag: If passphrase is wrong or file is corrupted.
    """
    with input_path.open("rb") as f:
        magic = f.read(len(_MAGIC))
        if magic != _MAGIC:
            raise ValueError(
                "Not a valid Pilot Space encrypted backup — "
                f"expected magic {_MAGIC!r}, got {magic!r}"
            )
        salt = f.read(_SALT_SIZE)
        nonce = f.read(_NONCE_SIZE)
        ciphertext = f.read()

    key = _derive_key(passphrase, salt)
    aesgcm = AESGCM(key)
    plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    output_path.write_bytes(plaintext)

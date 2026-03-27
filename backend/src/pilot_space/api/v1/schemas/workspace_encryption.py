"""Pydantic schemas for workspace encryption API.

TENANT-02: Workspace BYOK encryption key management schemas.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class EncryptionStatusResponse(BaseModel):
    """Response for GET /encryption — public-safe status, no key material."""

    enabled: bool
    key_hint: str | None = None
    key_version: int | None = None
    last_rotated: datetime | None = None


class EncryptionKeyRequest(BaseModel):
    """Request body for PUT /encryption/key."""

    key: str


class EncryptionKeyResponse(BaseModel):
    """Response for PUT /encryption/key."""

    key_version: int
    key_hint: str | None = None


class EncryptionVerifyRequest(BaseModel):
    """Request body for POST /encryption/verify."""

    key: str


class EncryptionVerifyResponse(BaseModel):
    """Response for POST /encryption/verify."""

    verified: bool
    key_version: int


class GeneratedKeyResponse(BaseModel):
    """Response for POST /encryption/generate-key."""

    key: str


class KeyRotationRequest(BaseModel):
    """Request body for POST /encryption/rotate."""

    new_key: str


class KeyRotationResponse(BaseModel):
    """Response for POST /encryption/rotate."""

    rotated: bool
    re_encrypted: dict[str, int]
    key_version: int


__all__ = [
    "EncryptionKeyRequest",
    "EncryptionKeyResponse",
    "EncryptionStatusResponse",
    "EncryptionVerifyRequest",
    "EncryptionVerifyResponse",
    "GeneratedKeyResponse",
    "KeyRotationRequest",
    "KeyRotationResponse",
]

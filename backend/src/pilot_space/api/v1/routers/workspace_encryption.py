"""Workspace encryption key management API router.

Provides endpoints for workspace-level BYOK (bring-your-own-key) encryption.
Encryption is opt-in: workspaces without a configured key continue in plaintext.

Endpoints (all under /api/v1/workspaces/{workspace_slug}/encryption):
  GET    /           — encryption status (never returns encrypted_workspace_key)
  PUT    /key        — store or rotate workspace encryption key (OWNER only)
  POST   /rotate     — rotate key with batch re-encryption (OWNER only)
  POST   /verify     — verify a key matches the stored key (ADMIN or OWNER)
  POST   /generate-key — generate a new valid Fernet key (ADMIN or OWNER)

Authorization:
  - GET + POST /verify + POST /generate-key require settings:read (ADMIN or OWNER)
  - PUT /key + POST /rotate require settings:manage (OWNER only)

References:
  - TENANT-02: Workspace BYOK encryption
  - docs/DESIGN_DECISIONS.md
"""

from __future__ import annotations

import hmac
from typing import TYPE_CHECKING, Annotated
from uuid import UUID

from cryptography.fernet import Fernet
from fastapi import APIRouter, HTTPException, Path, status

from pilot_space.api.v1.schemas.workspace_encryption import (
    EncryptionKeyRequest,
    EncryptionKeyResponse,
    EncryptionStatusResponse,
    EncryptionVerifyRequest,
    EncryptionVerifyResponse,
    GeneratedKeyResponse,
    KeyRotationRequest,
    KeyRotationResponse,
)
from pilot_space.dependencies.auth import CurrentUser, SessionDep
from pilot_space.infrastructure.database.permissions import check_permission
from pilot_space.infrastructure.database.repositories.workspace_encryption_repository import (
    WorkspaceEncryptionRepository,
)
from pilot_space.infrastructure.database.repositories.workspace_repository import (
    WorkspaceRepository,
)
from pilot_space.infrastructure.workspace_encryption import (
    retrieve_workspace_key,
    rotate_workspace_key,
    validate_workspace_key,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(tags=["encryption"])

WorkspaceSlugPath = Annotated[str, Path(description="Workspace slug or UUID")]


# ============================================================================
# Helpers
# ============================================================================


async def _resolve_workspace(
    workspace_slug: str,
    session: AsyncSession,
) -> UUID:
    """Resolve workspace slug (or UUID string) to workspace.id.

    Args:
        workspace_slug: URL path parameter (slug or UUID string).
        session: Database session.

    Returns:
        Workspace UUID.

    Raises:
        HTTPException: 404 if workspace not found.
    """
    workspace_repo = WorkspaceRepository(session)
    try:
        as_uuid = UUID(workspace_slug)
        workspace = await workspace_repo.get_by_id_scalar(as_uuid)
    except ValueError:
        workspace = await workspace_repo.get_by_slug_scalar(workspace_slug)

    if workspace is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )
    return workspace.id


async def _require_settings_read(
    session: AsyncSession,
    user_id: UUID,
    workspace_id: UUID,
) -> None:
    """Assert the user has settings:read permission (ADMIN or OWNER).

    Args:
        session: Database session.
        user_id: Requesting user UUID.
        workspace_id: Workspace being accessed.

    Raises:
        HTTPException: 403 if permission is not granted.
    """
    allowed = await check_permission(
        session,
        user_id,
        workspace_id,
        resource="settings",
        action="read",
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or owner access required to view encryption settings",
        )


async def _require_settings_manage(
    session: AsyncSession,
    user_id: UUID,
    workspace_id: UUID,
) -> None:
    """Assert the user has settings:manage permission (OWNER only).

    Args:
        session: Database session.
        user_id: Requesting user UUID.
        workspace_id: Workspace being accessed.

    Raises:
        HTTPException: 403 if permission is not granted.
    """
    allowed = await check_permission(
        session,
        user_id,
        workspace_id,
        resource="settings",
        action="manage",
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Owner access required to configure workspace encryption",
        )


# ============================================================================
# Endpoints
# ============================================================================


@router.get("/{workspace_slug}/encryption")
async def get_encryption_status(
    workspace_slug: WorkspaceSlugPath,
    session: SessionDep,
    current_user: CurrentUser,
) -> EncryptionStatusResponse:
    """Get workspace encryption configuration status.

    Returns enabled flag, key_hint, key_version, and last_rotated timestamp.
    Never returns encrypted_workspace_key or raw key material.

    Requires settings:read permission (ADMIN or OWNER).
    """
    workspace_id = await _resolve_workspace(workspace_slug, session)
    await _require_settings_read(session, current_user.user_id, workspace_id)

    repo = WorkspaceEncryptionRepository(session)
    record = await repo.get_key_record(workspace_id)

    if record is None:
        return EncryptionStatusResponse(enabled=False)

    return EncryptionStatusResponse(
        enabled=True,
        key_hint=record.key_hint,
        key_version=record.key_version,
        last_rotated=record.updated_at,
    )


@router.put("/{workspace_slug}/encryption/key")
async def put_encryption_key(
    workspace_slug: WorkspaceSlugPath,
    body: EncryptionKeyRequest,
    session: SessionDep,
    current_user: CurrentUser,
) -> EncryptionKeyResponse:
    """Store or rotate the workspace encryption key.

    Accepts a 32-byte URL-safe base64 Fernet key. Encrypts it with the system
    master key before storage. Existing key is replaced and key_version increments.

    Requires settings:manage permission (OWNER only).

    Raises:
        HTTPException 422: If key is not a valid Fernet key format.
        HTTPException 403: If user lacks OWNER permission.
    """
    workspace_id = await _resolve_workspace(workspace_slug, session)
    await _require_settings_manage(session, current_user.user_id, workspace_id)

    validate_workspace_key(body.key)

    repo = WorkspaceEncryptionRepository(session)
    record = await repo.upsert_key(workspace_id, body.key)
    await session.commit()

    return EncryptionKeyResponse(
        key_version=record.key_version,
        key_hint=record.key_hint,
    )


@router.post("/{workspace_slug}/encryption/verify")
async def verify_encryption_key(
    workspace_slug: WorkspaceSlugPath,
    body: EncryptionVerifyRequest,
    session: SessionDep,
    current_user: CurrentUser,
) -> EncryptionVerifyResponse:
    """Verify that a provided key matches the stored workspace key.

    Fetches the encrypted key from DB, decrypts with master key, and compares
    to the provided key. Returns {verified: true, key_version} on match.

    Requires settings:read permission (ADMIN or OWNER).

    Raises:
        HTTPException 404: If no key is configured for this workspace.
        HTTPException 422: If provided key does not match stored key.
    """
    workspace_id = await _resolve_workspace(workspace_slug, session)
    await _require_settings_read(session, current_user.user_id, workspace_id)

    repo = WorkspaceEncryptionRepository(session)
    record = await repo.get_key_record(workspace_id)

    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No encryption key configured for this workspace",
        )

    # Decrypt stored key and compare using constant-time comparison to prevent timing attacks
    stored_key = retrieve_workspace_key(record.encrypted_workspace_key)
    if not hmac.compare_digest(stored_key, body.key):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Key does not match current workspace key",
        )

    return EncryptionVerifyResponse(
        verified=True,
        key_version=record.key_version,
    )


@router.post("/{workspace_slug}/encryption/generate-key")
async def generate_encryption_key(
    workspace_slug: WorkspaceSlugPath,
    session: SessionDep,
    current_user: CurrentUser,
) -> GeneratedKeyResponse:
    """Generate a new valid Fernet key.

    This endpoint generates a cryptographically random Fernet key and returns it.
    The key is NOT stored — callers must use PUT /key to configure it.

    Requires settings:read permission (ADMIN or OWNER).
    """
    workspace_id = await _resolve_workspace(workspace_slug, session)
    await _require_settings_read(session, current_user.user_id, workspace_id)

    new_key = Fernet.generate_key().decode()
    return GeneratedKeyResponse(key=new_key)


@router.post("/{workspace_slug}/encryption/rotate")
async def rotate_encryption_key(
    workspace_slug: WorkspaceSlugPath,
    body: KeyRotationRequest,
    session: SessionDep,
    current_user: CurrentUser,
) -> KeyRotationResponse:
    """Rotate the workspace encryption key with batch re-encryption.

    Generates a new encrypted key, saves the old key for dual-key fallback,
    re-encrypts all content (notes, issues) with the new key, then clears
    the old key reference.

    Requires settings:manage permission (OWNER only).

    Args:
        workspace_slug: Workspace slug or UUID.
        body: Request body with new_key (valid Fernet key).
        session: Database session.
        current_user: Authenticated user.

    Returns:
        KeyRotationResponse with re-encryption counts and new key version.

    Raises:
        HTTPException 400: If new key is invalid or no existing key configured.
        HTTPException 403: If user is not workspace owner.
        HTTPException 500: If rotation fails mid-batch.
    """
    workspace_id = await _resolve_workspace(workspace_slug, session)
    await _require_settings_manage(session, current_user.user_id, workspace_id)

    validate_workspace_key(body.new_key)

    counts = await rotate_workspace_key(session, workspace_id, body.new_key, batch_size=100)
    await session.commit()

    # Fetch updated key version
    repo = WorkspaceEncryptionRepository(session)
    record = await repo.get_key_record(workspace_id)
    key_version = record.key_version if record else 0

    return KeyRotationResponse(
        rotated=True,
        re_encrypted=counts,
        key_version=key_version,
    )

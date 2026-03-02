"""DriveCredential repository for managing Google Drive OAuth tokens.

Feature: 020 — Chat Context Attachments & Google Drive
Source: FR-009, FR-010, FR-012
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import and_, delete, select
from sqlalchemy.dialects.postgresql import insert

from pilot_space.infrastructure.database.models.drive_credential import DriveCredential

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class DriveCredentialRepository:
    """Repository for DriveCredential entities.

    DriveCredential uses hard delete and upsert semantics, with no soft-delete
    support, so it does not extend BaseRepository which assumes SoftDeleteMixin.

    Provides:
    - Upsert on (user_id, workspace_id) unique constraint
    - Lookup by user + workspace scope
    - Deletion by user + workspace scope
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository.

        Args:
            session: Async database session.
        """
        self.session = session

    async def upsert(self, credential: DriveCredential) -> DriveCredential:
        """Insert or update a Drive credential for (user_id, workspace_id).

        Uses PostgreSQL ``ON CONFLICT DO UPDATE`` on the
        ``uq_drive_credentials_user_workspace`` unique constraint so that
        re-authorisation replaces existing tokens atomically.

        All mutable columns (google_email, access_token, refresh_token,
        token_expires_at, scope) are updated on conflict.

        Args:
            credential: DriveCredential instance with the values to persist.

        Returns:
            The persisted (inserted or updated) DriveCredential, refreshed
            from the database.
        """
        values = {
            "id": credential.id,
            "user_id": credential.user_id,
            "workspace_id": credential.workspace_id,
            "google_email": credential.google_email,
            "access_token": credential.access_token,
            "refresh_token": credential.refresh_token,
            "token_expires_at": credential.token_expires_at,
            "scope": credential.scope,
        }

        stmt = (
            insert(DriveCredential)
            .values(**values)
            .on_conflict_do_update(
                constraint="uq_drive_credentials_user_workspace",
                set_={
                    "google_email": credential.google_email,
                    "access_token": credential.access_token,
                    "refresh_token": credential.refresh_token,
                    "token_expires_at": credential.token_expires_at,
                    "scope": credential.scope,
                },
            )
            .returning(DriveCredential.id)
        )

        result = await self.session.execute(stmt)
        returned_id: UUID = result.scalar_one()

        refreshed = await self.session.get(DriveCredential, returned_id)
        if refreshed is None:
            # Should never happen after a successful upsert; guard defensively.
            raise RuntimeError(  # pragma: no cover
                f"DriveCredential {returned_id} not found after upsert"
            )
        return refreshed

    async def get_by_user_workspace(
        self,
        user_id: UUID,
        workspace_id: UUID,
    ) -> DriveCredential | None:
        """Fetch a Drive credential scoped to a user and workspace.

        Args:
            user_id: The user's UUID.
            workspace_id: The workspace's UUID.

        Returns:
            DriveCredential if found, None otherwise.
        """
        result = await self.session.execute(
            select(DriveCredential).where(
                and_(
                    DriveCredential.user_id == user_id,
                    DriveCredential.workspace_id == workspace_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def delete_by_user_workspace(
        self,
        user_id: UUID,
        workspace_id: UUID,
    ) -> bool:
        """Delete the Drive credential for a user+workspace pair.

        Args:
            user_id: The user's UUID.
            workspace_id: The workspace's UUID.

        Returns:
            True if a row was deleted, False if no matching row existed.
        """
        result = await self.session.execute(
            delete(DriveCredential)
            .where(
                and_(
                    DriveCredential.user_id == user_id,
                    DriveCredential.workspace_id == workspace_id,
                )
            )
            .returning(DriveCredential.id)
        )
        return result.scalar_one_or_none() is not None


__all__ = ["DriveCredentialRepository"]

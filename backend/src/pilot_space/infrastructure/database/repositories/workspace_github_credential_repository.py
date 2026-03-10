"""Repository for WorkspaceGithubCredential entities.

Provides get_by_workspace + upsert for one-PAT-per-workspace pattern.

Source: Phase 19, SKRG-03
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import and_, select

from pilot_space.infrastructure.database.models.workspace_github_credential import (
    WorkspaceGithubCredential,
)
from pilot_space.infrastructure.database.repositories.base import BaseRepository

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession


class WorkspaceGithubCredentialRepository(BaseRepository[WorkspaceGithubCredential]):
    """Repository for WorkspaceGithubCredential entities.

    One credential per workspace. Upsert pattern: get existing or create new.
    All write operations use flush() (no commit).
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, WorkspaceGithubCredential)

    async def get_by_workspace(
        self,
        workspace_id: UUID,
    ) -> WorkspaceGithubCredential | None:
        """Get the GitHub credential for a workspace.

        Returns the non-deleted credential, or None if not configured.

        Args:
            workspace_id: The workspace UUID.

        Returns:
            The credential or None.
        """
        query = select(WorkspaceGithubCredential).where(
            and_(
                WorkspaceGithubCredential.workspace_id == workspace_id,
                WorkspaceGithubCredential.is_deleted == False,  # noqa: E712
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def upsert(
        self,
        *,
        workspace_id: UUID,
        pat_encrypted: str,
        created_by: UUID | None = None,
    ) -> WorkspaceGithubCredential:
        """Create or update the GitHub credential for a workspace.

        If a non-deleted credential exists, updates pat_encrypted and
        created_by. Otherwise creates a new row.

        Args:
            workspace_id: The workspace UUID.
            pat_encrypted: Fernet-encrypted PAT string.
            created_by: User who configured this credential.

        Returns:
            The created or updated credential.
        """
        existing = await self.get_by_workspace(workspace_id)
        if existing is not None:
            existing.pat_encrypted = pat_encrypted
            existing.created_by = created_by
            await self.session.flush()
            await self.session.refresh(existing)
            return existing

        credential = WorkspaceGithubCredential(
            workspace_id=workspace_id,
            pat_encrypted=pat_encrypted,
            created_by=created_by,
        )
        self.session.add(credential)
        await self.session.flush()
        await self.session.refresh(credential)
        return credential


__all__ = ["WorkspaceGithubCredentialRepository"]

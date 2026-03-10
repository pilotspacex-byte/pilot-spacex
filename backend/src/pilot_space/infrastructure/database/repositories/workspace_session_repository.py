"""WorkspaceSession repository for session CRUD and revocation.

Provides upsert, list-active, get-by-token-hash, revoke, and revoke-all
operations for workspace session management (AUTH-06).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import and_, select, update
from sqlalchemy.orm import joinedload

from pilot_space.infrastructure.database.models.workspace_session import WorkspaceSession
from pilot_space.infrastructure.database.repositories.base import BaseRepository

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class WorkspaceSessionRepository(BaseRepository[WorkspaceSession]):
    """Repository for WorkspaceSession entities.

    Provides session-specific operations: upsert, revoke, and listing
    active sessions per workspace.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository.

        Args:
            session: Async database session.
        """
        super().__init__(session, WorkspaceSession)

    async def upsert_session(
        self,
        *,
        user_id: UUID,
        workspace_id: UUID,
        token_hash: str,
        ip_address: str | None,
        user_agent: str | None,
        db: AsyncSession,
    ) -> WorkspaceSession:
        """Upsert a workspace session row.

        Creates a new row if none exists for (workspace_id, user_id, token_hash).
        Updates last_seen_at if a row already exists.

        Args:
            user_id: Authenticated user ID.
            workspace_id: Workspace UUID.
            token_hash: SHA-256 hex digest of the session token.
            ip_address: Client IP address.
            user_agent: Raw User-Agent header.
            db: Database session for the write.

        Returns:
            WorkspaceSession — the upserted row.
        """
        # Try to find existing row for this (workspace_id, user_id, token_hash)
        stmt = select(WorkspaceSession).where(
            and_(
                WorkspaceSession.workspace_id == workspace_id,
                WorkspaceSession.user_id == user_id,
                WorkspaceSession.session_token_hash == token_hash,
                WorkspaceSession.is_deleted == False,  # noqa: E712
            )
        )
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing is not None:
            existing.last_seen_at = datetime.now(UTC)  # type: ignore[assignment]
            await db.flush()
            return existing

        new_session = WorkspaceSession(
            user_id=user_id,
            workspace_id=workspace_id,
            session_token_hash=token_hash,
            ip_address=ip_address,
            user_agent=user_agent,
            last_seen_at=datetime.now(UTC),  # type: ignore[arg-type]
        )
        db.add(new_session)
        await db.flush()
        return new_session

    async def list_active_for_workspace(
        self,
        workspace_id: UUID,
        db: AsyncSession,
    ) -> list[WorkspaceSession]:
        """List active (non-revoked) sessions for a workspace.

        Args:
            workspace_id: Workspace UUID.
            db: Database session.

        Returns:
            List of active WorkspaceSession rows ordered by last_seen_at DESC.
        """
        stmt = (
            select(WorkspaceSession)
            .where(
                and_(
                    WorkspaceSession.workspace_id == workspace_id,
                    WorkspaceSession.revoked_at.is_(None),
                    WorkspaceSession.is_deleted == False,  # noqa: E712
                )
            )
            .options(joinedload(WorkspaceSession.user))
            .order_by(WorkspaceSession.last_seen_at.desc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().unique().all())

    async def get_session_by_id(
        self,
        session_id: UUID,
        workspace_id: UUID | None = None,
    ) -> WorkspaceSession | None:
        """Get a single session by ID, optionally scoped to a workspace.

        Named get_session_by_id (not get_by_id) to avoid signature conflict
        with BaseRepository.get_by_id which has a different parameter set.

        Args:
            session_id: WorkspaceSession UUID.
            workspace_id: Optional workspace scope for safety.

        Returns:
            WorkspaceSession or None.
        """
        conditions = [
            WorkspaceSession.id == session_id,
            WorkspaceSession.is_deleted == False,  # noqa: E712
        ]
        if workspace_id is not None:
            conditions.append(WorkspaceSession.workspace_id == workspace_id)

        stmt = select(WorkspaceSession).where(and_(*conditions))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_token_hash(
        self,
        token_hash: str,
        workspace_id: UUID,
    ) -> WorkspaceSession | None:
        """Get a session by token hash within a workspace.

        Args:
            token_hash: SHA-256 hex digest.
            workspace_id: Workspace UUID.

        Returns:
            WorkspaceSession or None.
        """
        stmt = select(WorkspaceSession).where(
            and_(
                WorkspaceSession.session_token_hash == token_hash,
                WorkspaceSession.workspace_id == workspace_id,
                WorkspaceSession.is_deleted == False,  # noqa: E712
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def revoke(
        self,
        *,
        session_id: UUID,
        workspace_id: UUID,
        db: AsyncSession,
    ) -> None:
        """Revoke a single session by setting revoked_at.

        Args:
            session_id: Session UUID to revoke.
            workspace_id: Workspace scope (prevents cross-workspace revocation).
            db: Database session for the write.
        """
        stmt = (
            update(WorkspaceSession)
            .where(
                and_(
                    WorkspaceSession.id == session_id,
                    WorkspaceSession.workspace_id == workspace_id,
                    WorkspaceSession.revoked_at.is_(None),
                )
            )
            .values(revoked_at=datetime.now(UTC))
        )
        await db.execute(stmt)
        await db.flush()

    async def revoke_all_for_user(
        self,
        *,
        user_id: UUID,
        workspace_id: UUID,
        db: AsyncSession,
    ) -> int:
        """Revoke all active sessions for a user in a workspace.

        Args:
            user_id: User UUID.
            workspace_id: Workspace UUID.
            db: Database session for the write.

        Returns:
            Number of sessions revoked.
        """
        now = datetime.now(UTC)
        stmt = (
            update(WorkspaceSession)
            .where(
                and_(
                    WorkspaceSession.user_id == user_id,
                    WorkspaceSession.workspace_id == workspace_id,
                    WorkspaceSession.revoked_at.is_(None),
                    WorkspaceSession.is_deleted == False,  # noqa: E712
                )
            )
            .values(revoked_at=now)
            .returning(WorkspaceSession.id)
        )
        result = await db.execute(stmt)
        revoked_ids = result.fetchall()
        await db.flush()
        return len(revoked_ids)

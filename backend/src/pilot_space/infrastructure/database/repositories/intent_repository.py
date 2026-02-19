"""WorkIntent repository for AI workforce platform.

Provides typed data access for work_intents with workspace-scoped
queries and confidence-based filtering.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import desc, select, text

from pilot_space.domain.work_intent import IntentStatus
from pilot_space.infrastructure.database.models.work_intent import WorkIntent
from pilot_space.infrastructure.database.repositories.base import BaseRepository

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy.ext.asyncio import AsyncSession


class WorkIntentRepository(BaseRepository[WorkIntent]):
    """Repository for WorkIntent CRUD and workspace-scoped queries."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session, model_class=WorkIntent)

    async def list_by_workspace_and_status(
        self,
        workspace_id: UUID,
        status: IntentStatus,
        *,
        include_deleted: bool = False,
    ) -> Sequence[WorkIntent]:
        """List intents for a workspace filtered by status.

        Args:
            workspace_id: Workspace UUID.
            status: Intent lifecycle status to filter by.
            include_deleted: Whether to include soft-deleted records.

        Returns:
            Sequence of matching WorkIntent models ordered by created_at desc.
        """
        query = select(WorkIntent).where(
            WorkIntent.workspace_id == workspace_id,
            WorkIntent.status == status,
        )
        if not include_deleted:
            query = query.where(WorkIntent.is_deleted == False)  # noqa: E712
        query = query.order_by(desc(WorkIntent.created_at))
        result = await self.session.execute(query)
        return result.scalars().all()

    async def list_by_parent_intent(
        self,
        parent_intent_id: UUID,
        *,
        include_deleted: bool = False,
    ) -> Sequence[WorkIntent]:
        """List sub-intents for a parent intent.

        Args:
            parent_intent_id: Parent intent UUID.
            include_deleted: Whether to include soft-deleted records.

        Returns:
            Sequence of child WorkIntent models.
        """
        query = select(WorkIntent).where(
            WorkIntent.parent_intent_id == parent_intent_id,
        )
        if not include_deleted:
            query = query.where(WorkIntent.is_deleted == False)  # noqa: E712
        query = query.order_by(desc(WorkIntent.confidence), desc(WorkIntent.created_at))
        result = await self.session.execute(query)
        return result.scalars().all()

    async def list_by_source_block(
        self,
        source_block_id: UUID,
        workspace_id: UUID,
        *,
        include_deleted: bool = False,
    ) -> Sequence[WorkIntent]:
        """List intents originating from a specific TipTap block.

        Args:
            source_block_id: Source block UUID (soft ref).
            workspace_id: Workspace UUID for RLS enforcement.
            include_deleted: Whether to include soft-deleted records.

        Returns:
            Sequence of WorkIntent models linked to the block.
        """
        query = select(WorkIntent).where(
            WorkIntent.source_block_id == source_block_id,
            WorkIntent.workspace_id == workspace_id,
        )
        if not include_deleted:
            query = query.where(WorkIntent.is_deleted == False)  # noqa: E712
        query = query.order_by(desc(WorkIntent.created_at))
        result = await self.session.execute(query)
        return result.scalars().all()

    async def batch_top_by_confidence(
        self,
        workspace_id: UUID,
        min_confidence: float,
        limit: int = 10,
        *,
        include_deleted: bool = False,
    ) -> Sequence[WorkIntent]:
        """Get top intents by confidence above a threshold.

        Args:
            workspace_id: Workspace UUID.
            min_confidence: Minimum confidence threshold (0.0-1.0).
            limit: Maximum results to return (default 10).
            include_deleted: Whether to include soft-deleted records.

        Returns:
            Sequence of WorkIntent models ordered by confidence desc.
        """
        query = select(WorkIntent).where(
            WorkIntent.workspace_id == workspace_id,
            WorkIntent.confidence >= min_confidence,
        )
        if not include_deleted:
            query = query.where(WorkIntent.is_deleted == False)  # noqa: E712
        query = query.order_by(desc(WorkIntent.confidence), desc(WorkIntent.created_at))
        query = query.limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def find_similar_by_embedding(
        self,
        workspace_id: UUID,
        exclude_intent_id: UUID,
        embedding: list[float],
        cosine_distance_threshold: float,
        limit: int = 5,
    ) -> Sequence[WorkIntent]:
        """Find intents similar to the given embedding via pgvector HNSW.

        Uses the cosine distance operator ``<=>`` and the HNSW index for
        sub-linear approximate nearest-neighbour search, replacing the
        O(N) Python loop + Gemini API calls for each candidate.

        Args:
            workspace_id: Workspace UUID for RLS scoping.
            exclude_intent_id: ID of the source intent to exclude.
            embedding: 768-dim query vector.
            cosine_distance_threshold: Maximum cosine distance (1 - similarity).
                E.g. 0.1 corresponds to cosine_similarity >= 0.9.
            limit: Maximum number of results (default 5).

        Returns:
            Sequence of WorkIntent models ordered by distance asc.
        """
        # Cast the Python list to a pgvector literal understood by SQLAlchemy.
        # text() is intentional: pgvector's <=> operator has no SQLAlchemy type.
        raw = text(
            """
            SELECT id
            FROM work_intents
            WHERE workspace_id = :workspace_id
              AND id != :exclude_id
              AND is_deleted = FALSE
              AND embedding IS NOT NULL
              AND embedding <=> CAST(:embedding AS vector) < :threshold
            ORDER BY embedding <=> CAST(:embedding AS vector)
            LIMIT :limit
            """
        )
        result = await self.session.execute(
            raw,
            {
                "workspace_id": str(workspace_id),
                "exclude_id": str(exclude_intent_id),
                "embedding": str(embedding),
                "threshold": cosine_distance_threshold,
                "limit": limit,
            },
        )
        ids = [row[0] for row in result.fetchall()]
        if not ids:
            return []

        query = select(WorkIntent).where(WorkIntent.id.in_(ids))
        rows = await self.session.execute(query)
        return rows.scalars().all()

    async def get_by_dedup_hash(
        self,
        workspace_id: UUID,
        dedup_hash: str,
        *,
        include_deleted: bool = False,
    ) -> WorkIntent | None:
        """Find an existing intent by dedup hash within a workspace.

        Args:
            workspace_id: Workspace UUID.
            dedup_hash: SHA-256 hash of normalized intent text.
            include_deleted: Whether to include soft-deleted records.

        Returns:
            Matching WorkIntent if found, None otherwise.
        """
        query = select(WorkIntent).where(
            WorkIntent.workspace_id == workspace_id,
            WorkIntent.dedup_hash == dedup_hash,
        )
        if not include_deleted:
            query = query.where(WorkIntent.is_deleted == False)  # noqa: E712
        query = query.order_by(desc(WorkIntent.created_at)).limit(1)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

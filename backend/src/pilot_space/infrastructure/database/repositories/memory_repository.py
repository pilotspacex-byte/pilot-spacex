"""MemoryEntry repository for the AI memory engine.

Provides workspace-scoped data access with hybrid search:
0.7 * cosine_similarity(embedding) + 0.3 * ts_rank(keywords, query).

Feature 015: AI Workforce Platform — Memory Engine
"""

from __future__ import annotations

import uuid as _uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import desc, func, insert, select, text

from pilot_space.domain.memory_entry import MemorySourceType
from pilot_space.infrastructure.database.models.memory_entry import MemoryEntry
from pilot_space.infrastructure.database.repositories.base import BaseRepository

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy.ext.asyncio import AsyncSession


class MemoryEntryRepository(BaseRepository[MemoryEntry]):
    """Repository for MemoryEntry records.

    All queries are workspace-scoped via RLS + explicit workspace_id filter.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session, model_class=MemoryEntry)

    async def list_by_workspace(
        self,
        workspace_id: UUID,
        *,
        limit: int = 20,
        offset: int = 0,
    ) -> Sequence[MemoryEntry]:
        """List memory entries for a workspace, ordered by created_at desc.

        Args:
            workspace_id: Workspace to list entries for.
            limit: Maximum entries to return.
            offset: Number of entries to skip.

        Returns:
            Sequence of MemoryEntry models.
        """
        query = (
            select(MemoryEntry)
            .where(
                MemoryEntry.workspace_id == workspace_id,
                MemoryEntry.is_deleted == False,  # noqa: E712
            )
            .order_by(desc(MemoryEntry.created_at))
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def list_pinned(self, workspace_id: UUID) -> Sequence[MemoryEntry]:
        """List pinned memory entries for a workspace.

        Args:
            workspace_id: Workspace to list pinned entries for.

        Returns:
            Sequence of pinned MemoryEntry models ordered by created_at desc.
        """
        query = (
            select(MemoryEntry)
            .where(
                MemoryEntry.workspace_id == workspace_id,
                MemoryEntry.pinned == True,  # noqa: E712
                MemoryEntry.is_deleted == False,  # noqa: E712
            )
            .order_by(desc(MemoryEntry.created_at))
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def create_with_keywords(
        self,
        *,
        workspace_id: UUID,
        content: str,
        keywords: list[str],
        source_type: MemorySourceType,
        source_id: UUID | None = None,
        pinned: bool = False,
        expires_at: datetime | None = None,
    ) -> MemoryEntry:
        """Insert a MemoryEntry with keywords stored as tsvector.

        Uses ``to_tsvector('english', ...)`` so full-text search via
        ``ts_rank`` works correctly against a tsvector column.

        Args:
            workspace_id: Owning workspace UUID.
            content: Memory text content.
            keywords: List of keyword strings to convert to tsvector.
            source_type: Origin of this memory entry.
            source_id: Optional originating entity UUID.
            pinned: Whether entry is pinned (excluded from TTL expiry).
            expires_at: Optional expiry timestamp.

        Returns:
            The freshly-inserted MemoryEntry ORM model.
        """
        entry_id = _uuid.uuid4()
        keywords_text = " ".join(keywords)

        stmt = (
            insert(MemoryEntry)
            .values(
                id=entry_id,
                workspace_id=workspace_id,
                content=content,
                keywords=func.to_tsvector("english", keywords_text),
                source_type=source_type,
                source_id=source_id,
                pinned=pinned,
                expires_at=expires_at,
            )
            .returning(MemoryEntry)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def hybrid_search(
        self,
        query_embedding: list[float],
        query_text: str,
        workspace_id: UUID,
        *,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Hybrid vector + full-text search with fusion scoring.

        Fusion score = 0.7 * cosine_similarity(embedding, query_embedding)
                     + 0.3 * ts_rank(keywords, plainto_tsquery(query_text))

        Only entries with a non-null embedding are considered.

        Args:
            query_embedding: 768-dim query vector for semantic search.
            query_text: Text for full-text search.
            workspace_id: Scope to this workspace.
            limit: Maximum results.

        Returns:
            List of dicts with keys: id, content, source_type, pinned,
            embedding_score, text_score, score.
        """
        embedding_literal = "[" + ",".join(str(v) for v in query_embedding) + "]"

        raw_sql = text("""
            SELECT
                me.id,
                me.content,
                me.source_type,
                me.pinned,
                (1 - (me.embedding <=> CAST(:embedding AS vector(768)))) AS embedding_score,
                COALESCE(
                    ts_rank(me.keywords, plainto_tsquery('english', :query_text)),
                    0.0
                ) AS text_score,
                0.7 * (1 - (me.embedding <=> CAST(:embedding AS vector(768))))
                + 0.3 * COALESCE(
                    ts_rank(me.keywords, plainto_tsquery('english', :query_text)),
                    0.0
                ) AS score
            FROM memory_entries me
            WHERE
                me.workspace_id = :workspace_id
                AND me.is_deleted = false
                AND me.embedding IS NOT NULL
            ORDER BY score DESC
            LIMIT :limit
        """)

        result = await self.session.execute(
            raw_sql,
            {
                "embedding": embedding_literal,
                "query_text": query_text,
                "workspace_id": str(workspace_id),
                "limit": limit,
            },
        )
        rows = result.mappings().all()
        return [dict(row) for row in rows]

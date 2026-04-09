"""MemoryListService — list, search, stats, detail, and bulk operations.

Phase 71: Provides the query layer for the memory browse UI.
Uses two-pass semantic search when ``q`` is provided (recall IDs, then
paginate), and standard SQL queries for non-search browsing.

Pinned filter uses ``properties @> '{"pinned": true}'::jsonb`` for
GIN-indexed containment — NOT the ``pinned_at`` column.
"""

from __future__ import annotations

import contextlib
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any, Literal
from uuid import UUID

from sqlalchemy import and_, cast, func, select
from sqlalchemy.dialects.postgresql import JSONB

from pilot_space.application.services.memory.memory_lifecycle_service import (
    ForgetPayload,
    MemoryLifecycleService,
    PinPayload,
)
from pilot_space.application.services.memory.memory_recall_service import (
    MemoryRecallService,
    RecallPayload,
)
from pilot_space.domain.exceptions import NotFoundError
from pilot_space.infrastructure.database.models.graph_node import GraphNodeModel

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

_SNIPPET_LENGTH = 200


# ---------------------------------------------------------------------------
# Service-layer result dataclasses (avoid circular import with API schemas)
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class MemoryListItemResult:
    """Single item in the memory list."""

    id: UUID
    node_type: str
    kind: str | None
    label: str
    content_snippet: str
    pinned: bool
    score: float | None
    source_type: str | None
    source_id: UUID | None
    created_at: datetime


@dataclass(slots=True)
class MemoryListResult:
    """Paginated memory list result."""

    items: list[MemoryListItemResult]
    total: int
    offset: int
    limit: int
    has_next: bool


@dataclass(slots=True)
class MemoryDetailResult:
    """Full detail for a single memory node."""

    id: UUID
    node_type: str
    kind: str | None
    label: str
    content: str
    properties: dict[str, Any]
    pinned: bool
    source_type: str | None
    source_id: UUID | None
    source_label: str | None
    source_url: str | None
    embedding_dim: int | None
    created_at: datetime
    updated_at: datetime


@dataclass(slots=True)
class MemoryStatsResult:
    """Aggregated memory statistics."""

    total: int
    by_type: dict[str, int]
    pinned_count: int
    last_ingestion: datetime | None


@dataclass(slots=True)
class BulkActionResult:
    """Result of a bulk pin/forget operation."""

    succeeded: list[UUID]
    failed: list[dict[str, Any]]
    total_processed: int


class MemoryListService:
    """Query service for the memory browse UI.

    Delegates mutations (pin/forget) to ``MemoryLifecycleService`` and
    semantic search to ``MemoryRecallService``.
    """

    def __init__(
        self,
        session: AsyncSession,
        recall_service: MemoryRecallService,
        lifecycle_service: MemoryLifecycleService,
    ) -> None:
        self._session = session
        self._recall_service = recall_service
        self._lifecycle_service = lifecycle_service

    # ------------------------------------------------------------------
    # List (paginated + filterable + semantic search)
    # ------------------------------------------------------------------

    async def list_memories(
        self,
        workspace_id: UUID,
        *,
        node_types: list[str] | None = None,
        kind: str | None = None,
        pinned: bool | None = None,
        q: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> MemoryListResult:
        """Return a paginated, filterable list of memory nodes.

        When ``q`` is provided, performs a two-pass semantic search:
        1. Recall up to 200 scored IDs via ``MemoryRecallService``.
        2. Filter + paginate those IDs with SQL.

        When ``q`` is absent, runs a standard SQL query ordered by
        ``created_at DESC``.
        """
        if q:
            return await self._search_memories(
                workspace_id,
                query=q,
                node_types=node_types,
                kind=kind,
                pinned=pinned,
                offset=offset,
                limit=limit,
            )
        return await self._browse_memories(
            workspace_id,
            node_types=node_types,
            kind=kind,
            pinned=pinned,
            offset=offset,
            limit=limit,
        )

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    async def get_stats(self, workspace_id: UUID) -> MemoryStatsResult:
        """Return aggregated counts grouped by node_type."""
        base_where = and_(
            GraphNodeModel.workspace_id == workspace_id,
            GraphNodeModel.is_deleted == False,  # noqa: E712
        )

        stmt = (
            select(
                GraphNodeModel.node_type,
                func.count().label("cnt"),
            )
            .where(base_where)
            .group_by(GraphNodeModel.node_type)
        )
        rows = (await self._session.execute(stmt)).all()

        total = 0
        by_type: dict[str, int] = {}

        for node_type, cnt in rows:
            by_type[str(node_type)] = int(cnt)
            total += int(cnt)

        # Pinned count (separate query — simpler + avoids conditional aggregation
        # which is not portable to SQLite tests)
        pinned_stmt = (
            select(func.count())
            .select_from(GraphNodeModel)
            .where(
                base_where,
                self._pinned_filter(value=True),
            )
        )
        pinned_count = (await self._session.execute(pinned_stmt)).scalar() or 0

        # Last ingestion timestamp
        last_stmt = (
            select(func.max(GraphNodeModel.created_at))
            .where(base_where)
        )
        last_ingestion = (await self._session.execute(last_stmt)).scalar()

        return MemoryStatsResult(
            total=total,
            by_type=by_type,
            pinned_count=int(pinned_count),
            last_ingestion=last_ingestion,
        )

    # ------------------------------------------------------------------
    # Detail
    # ------------------------------------------------------------------

    async def get_detail(
        self,
        workspace_id: UUID,
        node_id: UUID,
    ) -> MemoryDetailResult:
        """Load a single memory node with provenance resolution."""
        stmt = select(GraphNodeModel).where(
            GraphNodeModel.id == node_id,
            GraphNodeModel.workspace_id == workspace_id,
            GraphNodeModel.is_deleted == False,  # noqa: E712
        )
        node = (await self._session.execute(stmt)).scalar_one_or_none()
        if node is None:
            raise NotFoundError(f"Memory node {node_id} not found")

        props: dict[str, Any] = dict(node.properties or {})

        # Resolve provenance label from external_id (lazy — only on detail view).
        # Fallback: for note_chunk nodes without external_id, try
        # properties.parent_note_id as the provenance source.
        source_label: str | None = None
        source_url: str | None = None
        provenance_id = node.external_id
        if provenance_id is None and node.node_type == "note_chunk":
            raw_parent = props.get("parent_note_id")
            if raw_parent:
                with contextlib.suppress(ValueError, TypeError):
                    provenance_id = UUID(str(raw_parent))
        if provenance_id is not None:
            source_label, source_url = await self._resolve_provenance(
                node.node_type, provenance_id
            )

        embedding_dim: int | None = None
        if node.embedding is not None:
            try:
                embedding_dim = len(node.embedding)
            except TypeError:
                embedding_dim = None

        return MemoryDetailResult(
            id=node.id,
            node_type=node.node_type,
            kind=props.get("kind"),
            label=node.label,
            content=node.content,
            properties=props,
            pinned=bool(props.get("pinned", False)),
            source_type=props.get("source_type") or node.node_type,
            source_id=node.external_id,
            source_label=source_label,
            source_url=source_url,
            embedding_dim=embedding_dim,
            created_at=node.created_at,
            updated_at=node.updated_at,
        )

    # ------------------------------------------------------------------
    # Bulk pin / forget
    # ------------------------------------------------------------------

    async def bulk_action(
        self,
        workspace_id: UUID,
        action: Literal["pin", "forget"],
        memory_ids: list[UUID],
        *,
        actor_user_id: UUID | None = None,
    ) -> BulkActionResult:
        """Pin or forget multiple memory nodes, collecting per-ID results."""
        succeeded: list[UUID] = []
        failed: list[dict[str, Any]] = []
        actor = actor_user_id or UUID(int=0)

        for mid in memory_ids:
            try:
                if action == "pin":
                    await self._lifecycle_service.pin(
                        PinPayload(
                            workspace_id=workspace_id,
                            node_id=mid,
                            actor_user_id=actor,
                        )
                    )
                else:
                    await self._lifecycle_service.forget(
                        ForgetPayload(
                            workspace_id=workspace_id,
                            node_id=mid,
                            actor_user_id=actor,
                        )
                    )
                succeeded.append(mid)
            except Exception as exc:
                failed.append({"id": str(mid), "error": str(exc)})

        return BulkActionResult(
            succeeded=succeeded,
            failed=failed,
            total_processed=len(memory_ids),
        )

    # ------------------------------------------------------------------
    # Private: browse (no search query)
    # ------------------------------------------------------------------

    async def _browse_memories(
        self,
        workspace_id: UUID,
        *,
        node_types: list[str] | None,
        kind: str | None,
        pinned: bool | None,
        offset: int,
        limit: int,
    ) -> MemoryListResult:
        where = self._build_filters(workspace_id, node_types=node_types, kind=kind, pinned=pinned)

        count_stmt = select(func.count()).select_from(GraphNodeModel).where(where)
        total = (await self._session.execute(count_stmt)).scalar() or 0

        items_stmt = (
            select(GraphNodeModel)
            .where(where)
            .order_by(GraphNodeModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        rows = (await self._session.execute(items_stmt)).scalars().all()

        items = [self._node_to_item(row) for row in rows]
        return MemoryListResult(
            items=items,
            total=int(total),
            offset=offset,
            limit=limit,
            has_next=(offset + limit) < int(total),
        )

    # ------------------------------------------------------------------
    # Private: search (two-pass semantic)
    # ------------------------------------------------------------------

    async def _search_memories(
        self,
        workspace_id: UUID,
        *,
        query: str,
        node_types: list[str] | None,
        kind: str | None,
        pinned: bool | None,
        offset: int,
        limit: int,
    ) -> MemoryListResult:
        """Two-pass semantic search: recall scored IDs, then paginate."""
        recall_result = await self._recall_service.recall(
            RecallPayload(
                workspace_id=workspace_id,
                query=query,
                k=200,
                min_score=0.0,
            )
        )

        if not recall_result.items:
            return MemoryListResult(
                items=[], total=0, offset=offset, limit=limit, has_next=False
            )

        # Build score lookup: node_id -> score
        score_map: dict[str, float] = {
            item.node_id: item.score for item in recall_result.items
        }
        recalled_ids = [UUID(nid) for nid in score_map]

        # Second pass: apply additional filters on the recalled set
        where = and_(
            GraphNodeModel.id.in_(recalled_ids),
            GraphNodeModel.workspace_id == workspace_id,
            GraphNodeModel.is_deleted == False,  # noqa: E712
        )
        extra = self._extra_filters(node_types=node_types, kind=kind, pinned=pinned)
        if extra:
            where = and_(where, *extra)

        count_stmt = select(func.count()).select_from(GraphNodeModel).where(where)
        total = (await self._session.execute(count_stmt)).scalar() or 0

        items_stmt = (
            select(GraphNodeModel)
            .where(where)
            .offset(offset)
            .limit(limit)
        )
        rows = (await self._session.execute(items_stmt)).scalars().all()

        # Attach scores and sort by score DESC
        items = [
            self._node_to_item(row, score=score_map.get(str(row.id)))
            for row in rows
        ]
        items.sort(key=lambda i: i.score or 0.0, reverse=True)

        return MemoryListResult(
            items=items,
            total=int(total),
            offset=offset,
            limit=limit,
            has_next=(offset + limit) < int(total),
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _node_to_item(
        node: GraphNodeModel,
        *,
        score: float | None = None,
    ) -> MemoryListItemResult:
        props: dict[str, Any] = dict(node.properties or {})
        return MemoryListItemResult(
            id=node.id,
            node_type=node.node_type,
            kind=props.get("kind"),
            label=node.label,
            content_snippet=node.content[:_SNIPPET_LENGTH] if node.content else "",
            pinned=bool(props.get("pinned", False)),
            score=score,
            source_type=props.get("source_type") or node.node_type,
            source_id=node.external_id,
            created_at=node.created_at,
        )

    def _build_filters(
        self,
        workspace_id: UUID,
        *,
        node_types: list[str] | None,
        kind: str | None,
        pinned: bool | None,
    ) -> Any:
        """Build base + extra WHERE clause."""
        base = and_(
            GraphNodeModel.workspace_id == workspace_id,
            GraphNodeModel.is_deleted == False,  # noqa: E712
        )
        extra = self._extra_filters(node_types=node_types, kind=kind, pinned=pinned)
        if extra:
            return and_(base, *extra)
        return base

    @staticmethod
    def _extra_filters(
        *,
        node_types: list[str] | None,
        kind: str | None,
        pinned: bool | None,
    ) -> list[Any]:
        """Return additional filter clauses for type/kind/pinned."""
        clauses: list[Any] = []
        if node_types:
            clauses.append(GraphNodeModel.node_type.in_(node_types))
        if kind is not None:
            # GIN-indexed JSONB containment: properties @> '{"kind": "..."}'
            clauses.append(
                cast(GraphNodeModel.properties, JSONB).op("@>")(
                    cast(json.dumps({"kind": kind}), JSONB)
                )
            )
        if pinned is True:
            clauses.append(
                cast(GraphNodeModel.properties, JSONB).op("@>")(
                    cast('{"pinned": true}', JSONB)
                )
            )
        elif pinned is False:
            clauses.append(
                ~cast(GraphNodeModel.properties, JSONB).op("@>")(
                    cast('{"pinned": true}', JSONB)
                )
            )
        return clauses

    @staticmethod
    def _pinned_filter(*, value: bool) -> Any:
        """Return a pinned containment filter clause."""
        if value:
            return cast(GraphNodeModel.properties, JSONB).op("@>")(
                cast('{"pinned": true}', JSONB)
            )
        return ~cast(GraphNodeModel.properties, JSONB).op("@>")(
            cast('{"pinned": true}', JSONB)
        )

    async def _resolve_provenance(
        self,
        node_type: str,
        external_id: UUID,
    ) -> tuple[str | None, str | None]:
        """Resolve the source label and URL from external_id.

        Looks up the originating entity (issue or note) to provide a
        human-readable label and deep link for the provenance card.
        """
        # Lazy import to avoid circular dependency at module level
        from pilot_space.infrastructure.database.models.issue import Issue
        from pilot_space.infrastructure.database.models.note import Note

        if node_type in ("issue", "issue_decision"):
            stmt = select(Issue.name).where(Issue.id == external_id)
            title = (await self._session.execute(stmt)).scalar_one_or_none()
            if title:
                return str(title), f"/issues/{external_id}"

        if node_type in ("note", "note_chunk"):
            stmt = select(Note.title).where(Note.id == external_id)
            title = (await self._session.execute(stmt)).scalar_one_or_none()
            if title:
                return str(title), f"/notes/{external_id}"

        return None, None


__all__ = [
    "BulkActionResult",
    "MemoryDetailResult",
    "MemoryListItemResult",
    "MemoryListResult",
    "MemoryListService",
    "MemoryStatsResult",
]

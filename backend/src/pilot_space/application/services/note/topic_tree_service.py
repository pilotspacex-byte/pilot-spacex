"""TopicTreeService — typed orchestration layer over NoteRepository topic-tree methods.

Phase 93 Plan 02. Wraps the three repository methods landed in 93-01
(``list_topic_children``, ``list_topic_ancestors``, ``move_topic``) and
translates their ValueError sentinels into typed domain exceptions per
``.claude/rules/exception-handler.md``.

Translation table (locked in plan 93-02):

    | Sentinel              | Domain exception              | HTTP |
    |-----------------------|-------------------------------|------|
    | topic_not_found       | NotFoundError                 | 404  |
    | parent_not_found      | NotFoundError                 | 404  |
    | cross_workspace_move  | ForbiddenError                | 403  |
    | topic_cycle           | TopicCycleError               | 409  |
    | topic_max_depth       | TopicMaxDepthExceededError    | 409  |

Routers must NOT wrap service exceptions — exceptions propagate to the global
``app_error_handler`` which builds RFC 7807 problem+json responses
automatically. See ``service-pattern.md`` and ``exception-handler.md``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pilot_space.domain.exceptions import (
    ForbiddenError,
    NotFoundError,
    TopicCycleError,
    TopicMaxDepthExceededError,
)
from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)

if TYPE_CHECKING:
    from collections.abc import Sequence
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from pilot_space.infrastructure.database.models.note import Note
    from pilot_space.infrastructure.database.repositories.note_repository import (
        NoteRepository,
    )


@dataclass(frozen=True, slots=True)
class GetChildrenPayload:
    """Input for ``TopicTreeService.get_children``.

    Attributes:
        workspace_id: workspace scope (defense-in-depth on top of RLS).
        parent_topic_id: parent's id, or ``None`` for the workspace's roots.
        page: 1-based page number.
        page_size: page size, must be >= 1.
    """

    workspace_id: UUID
    parent_topic_id: UUID | None
    page: int = 1
    page_size: int = 20


@dataclass(frozen=True, slots=True)
class GetChildrenResult:
    """Output of ``TopicTreeService.get_children``.

    Attributes:
        rows: page slice of direct topic children, ordered created_at DESC.
        total: total count of children matching the filter (for pagination).
    """

    rows: Sequence[Note]
    total: int


class TopicTreeService:
    """Orchestrates the topic-tree repository methods + exception translation.

    Stays thin — repository owns SQL + invariant enforcement; this service
    owns the typed-exception contract that routers and the global RFC 7807
    handler depend on.
    """

    def __init__(self, session: AsyncSession, note_repository: NoteRepository) -> None:
        """Initialize TopicTreeService.

        Args:
            session: async DB session (request-scoped via DI).
            note_repository: injected NoteRepository (Factory-resolved by DI).
        """
        self._session = session
        self._note_repo = note_repository

    async def get_children(self, payload: GetChildrenPayload) -> GetChildrenResult:
        """List direct topic children for ``parent_topic_id`` (or root if None).

        Pure pass-through to the repository; no exception translation needed
        because the repository's read methods do not raise sentinels.
        """
        rows, total = await self._note_repo.list_topic_children(
            payload.workspace_id,
            payload.parent_topic_id,
            page=payload.page,
            page_size=payload.page_size,
        )
        return GetChildrenResult(rows=rows, total=total)

    async def get_ancestors(self, note_id: UUID) -> list[Note]:
        """Return the ancestor chain root → leaf, INCLUDING the leaf.

        Empty list if the note does not exist or is soft-deleted.
        """
        return await self._note_repo.list_topic_ancestors(note_id)

    async def move_topic(self, topic_id: UUID, new_parent_topic_id: UUID | None) -> Note:
        """Reparent ``topic_id`` under ``new_parent_topic_id`` (root if None).

        Translates the repository's ValueError sentinels into typed domain
        exceptions per the locked translation table. Unrecognized sentinels
        re-raise as-is so they surface (defensive — should never happen given
        the repository contract).

        Raises:
            NotFoundError: topic_not_found / parent_not_found.
            ForbiddenError: cross_workspace_move.
            TopicCycleError: target equals topic_id or sits in its subtree.
            TopicMaxDepthExceededError: any descendant would exceed depth 5.
        """
        try:
            return await self._note_repo.move_topic(topic_id, new_parent_topic_id)
        except ValueError as exc:
            sentinel = str(exc)
            if sentinel == "topic_cycle":
                logger.info("topic_move_rejected", extra={"reason": "cycle", "topic_id": str(topic_id)})
                raise TopicCycleError from exc
            if sentinel == "topic_max_depth":
                logger.info(
                    "topic_move_rejected",
                    extra={"reason": "max_depth", "topic_id": str(topic_id)},
                )
                raise TopicMaxDepthExceededError from exc
            if sentinel == "cross_workspace_move":
                logger.info(
                    "topic_move_rejected",
                    extra={"reason": "cross_workspace", "topic_id": str(topic_id)},
                )
                raise ForbiddenError(
                    "Cannot move a topic across workspaces",
                    error_code="cross_workspace_move",
                ) from exc
            if sentinel == "topic_not_found":
                raise NotFoundError("Topic not found", error_code="topic_not_found") from exc
            if sentinel == "parent_not_found":
                raise NotFoundError(
                    "Target parent topic not found",
                    error_code="parent_not_found",
                ) from exc
            # Unrecognized sentinel — propagate for visibility (defensive).
            raise

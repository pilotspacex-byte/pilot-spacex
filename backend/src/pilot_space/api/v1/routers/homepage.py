"""Homepage Hub API router.

Endpoints for the Homepage Hub activity feed and AI digest:
- GET  /activity       — Recent notes + issues grouped by day
- GET  /digest         — Latest AI digest suggestions
- POST /digest/refresh — Trigger on-demand digest generation
- POST /digest/dismiss — Dismiss a digest suggestion

References:
- specs/012-homepage-note/spec.md API Endpoints section
- US-19: Homepage Hub feature
"""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from pilot_space.api.v1.schemas.homepage import (
    ActivityCardIssue,
    ActivityCardNote,
    ActivityGroupedData,
    ActivityMeta,
    AnnotationPreview,
    AssigneeBrief,
    CreateNoteFromChatData,
    CreateNoteFromChatPayload,
    CreateNoteFromChatResponse,
    DigestData,
    DigestDismissPayload,
    DigestRefreshData,
    DigestRefreshResponse,
    DigestResponse,
    DigestSuggestion,
    HomepageActivityResponse,
    ProjectBrief,
    StateBrief,
)
from pilot_space.dependencies import DbSession, QueueClientDep, WorkspaceMemberId
from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/workspaces/{workspace_id}/homepage", tags=["homepage"])


@router.get(
    "/activity",
    response_model=HomepageActivityResponse,
    summary="Get homepage activity feed",
    description="Recent notes and issues grouped by today/yesterday/this_week.",
)
async def get_activity(
    workspace_id: UUID,
    session: DbSession,
    _member_id: WorkspaceMemberId,
    cursor: str | None = None,
    limit: int = Query(default=20, ge=1, le=50),
) -> HomepageActivityResponse:
    """Get homepage activity feed.

    Args:
        workspace_id: Workspace UUID.
        session: Database session.
        _member_id: Authenticated user with workspace membership verified.
        cursor: Pagination cursor.
        limit: Items per page (default 20, max 50).

    Returns:
        HomepageActivityResponse with grouped activity cards.
    """
    from pilot_space.application.services.homepage import (
        ActivityItem,
        GetActivityPayload,
        GetActivityService,
    )
    from pilot_space.infrastructure.database.repositories.homepage_repository import (
        HomepageRepository,
        IssueActivityRow,
        NoteActivityRow,
    )

    repo = HomepageRepository(session)
    service = GetActivityService(session, repo)
    result = await service.execute(
        GetActivityPayload(
            workspace_id=workspace_id,
            cursor=cursor,
            limit=limit,
        )
    )

    def _note_card(item: NoteActivityRow) -> ActivityCardNote:
        return ActivityCardNote(
            id=item.id,
            title=item.title,
            word_count=item.word_count,
            is_pinned=item.is_pinned,
            updated_at=item.updated_at,
            project=ProjectBrief(
                id=item.project_id,
                name=item.project_name or "",
                identifier=item.project_identifier or "",
            )
            if item.project_id
            else None,
            latest_annotation=AnnotationPreview(
                type=item.annotation_type or "",
                content=item.annotation_content or "",
                confidence=item.annotation_confidence or 0.0,
            )
            if item.annotation_type
            else None,
        )

    def _issue_card(item: IssueActivityRow) -> ActivityCardIssue:
        identifier = (
            f"{item.project_identifier}-{item.sequence_id}"
            if item.project_identifier
            else str(item.sequence_id)
        )
        return ActivityCardIssue(
            id=item.id,
            identifier=identifier,
            title=item.name,
            priority=item.priority,
            updated_at=item.updated_at,
            project=ProjectBrief(
                id=item.project_id,
                name=item.project_name or "",
                identifier=item.project_identifier or "",
            )
            if item.project_id
            else None,
            state=StateBrief(
                name=item.state_name or "",
                color=item.state_color or "",
                group=item.state_group or "",
            )
            if item.state_name
            else None,
            assignee=AssigneeBrief(
                id=item.assignee_id,
                name=item.assignee_name or "",
                avatar_url=item.assignee_avatar_url,
            )
            if item.assignee_id
            else None,
            last_activity=item.last_activity,
        )

    def _convert_group(items: Sequence[ActivityItem]) -> list[ActivityCardNote | ActivityCardIssue]:
        cards: list[ActivityCardNote | ActivityCardIssue] = []
        for ai in items:
            if isinstance(ai.data, NoteActivityRow):
                cards.append(_note_card(ai.data))
            elif isinstance(ai.data, IssueActivityRow):
                cards.append(_issue_card(ai.data))
        return cards

    return HomepageActivityResponse(
        data=ActivityGroupedData(
            today=_convert_group(result.grouped.today),
            yesterday=_convert_group(result.grouped.yesterday),
            this_week=_convert_group(result.grouped.this_week),
        ),
        meta=ActivityMeta(
            total=result.total,
            cursor=result.cursor,
            has_more=result.has_more,
        ),
    )


@router.get(
    "/digest",
    response_model=DigestResponse,
    summary="Get latest AI digest",
    description="Latest workspace digest with user-filtered suggestions.",
)
async def get_digest(
    workspace_id: UUID,
    session: DbSession,
    user_id: WorkspaceMemberId,
) -> DigestResponse:
    """Get latest AI digest for workspace.

    Args:
        workspace_id: Workspace UUID.
        session: Database session.
        user_id: Authenticated user with workspace membership verified.

    Returns:
        DigestResponse with filtered suggestions.
    """
    from pilot_space.application.services.homepage import (
        GetDigestPayload,
        GetDigestService,
    )
    from pilot_space.infrastructure.database.repositories.digest_repository import (
        DigestRepository,
        DismissalRepository,
    )

    repo = DigestRepository(session)
    dismissal_repo = DismissalRepository(session)

    service = GetDigestService(session, repo, dismissal_repo)
    result = await service.execute(
        GetDigestPayload(
            workspace_id=workspace_id,
            user_id=user_id,
        )
    )

    from datetime import UTC, datetime

    generated_at = result.generated_at or datetime.now(tz=UTC)

    return DigestResponse(
        data=DigestData(
            generated_at=generated_at,
            generated_by=result.generated_by,
            suggestions=[
                DigestSuggestion(
                    id=s.id,
                    category=s.category,
                    title=s.title,
                    description=s.description,
                    entity_id=s.entity_id,
                    entity_type=s.entity_type,
                    entity_identifier=s.entity_identifier,
                    project_id=s.project_id,
                    project_name=s.project_name,
                    action_type=s.action_type,
                    action_label=s.action_label,
                    action_url=s.action_url,
                    relevance_score=s.relevance_score,
                )
                for s in result.suggestions
            ],
            suggestion_count=result.suggestion_count,
        )
    )


@router.post(
    "/digest/refresh",
    response_model=DigestRefreshResponse,
    summary="Trigger digest regeneration",
    description="Request on-demand digest generation. Returns immediately with status.",
)
async def refresh_digest(
    workspace_id: UUID,
    session: DbSession,
    _member_id: WorkspaceMemberId,
    queue_client: QueueClientDep,
) -> DigestRefreshResponse:
    """Trigger on-demand digest generation.

    Enqueues a background job on the AI_LOW queue. Returns immediately
    with status; actual generation happens asynchronously.

    Args:
        workspace_id: Workspace UUID.
        session: Database session.
        _member_id: Authenticated user with workspace membership verified.
        queue_client: Queue client for enqueuing jobs.

    Returns:
        DigestRefreshResponse with generation status.
    """
    from datetime import UTC, datetime, timedelta

    from pilot_space.infrastructure.database.repositories.digest_repository import (
        DigestRepository,
    )

    digest_repo = DigestRepository(session)

    # Check cooldown: prevent re-generation within 5 minutes
    cooldown_since = datetime.now(tz=UTC) - timedelta(minutes=5)
    recent_exists = await digest_repo.check_recent_digest_exists(workspace_id, since=cooldown_since)
    if recent_exists:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Digest was generated recently. Please wait before refreshing.",
        )

    # Enqueue background job for digest generation
    if queue_client is not None:
        await queue_client.enqueue_ai_task(
            task_type="generate_workspace_digest",
            workspace_id=workspace_id,
            payload={"trigger": "manual"},
            priority="low",
        )
        logger.info(
            "Digest refresh enqueued",
            extra={"workspace_id": str(workspace_id)},
        )
    else:
        logger.warning(
            "Queue not configured, digest refresh skipped",
            extra={"workspace_id": str(workspace_id)},
        )

    return DigestRefreshResponse(
        data=DigestRefreshData(
            status="generating",
            estimated_seconds=15,
        )
    )


@router.post(
    "/digest/dismiss",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Dismiss a digest suggestion",
    description="Dismiss a suggestion so it no longer appears for this user.",
)
async def dismiss_suggestion(
    workspace_id: UUID,
    payload: DigestDismissPayload,
    session: DbSession,
    user_id: WorkspaceMemberId,
) -> None:
    """Dismiss a digest suggestion.

    Args:
        workspace_id: Workspace UUID.
        payload: Dismissal details.
        session: Database session.
        user_id: Authenticated user with workspace membership verified.
    """
    from pilot_space.application.services.homepage import (
        DismissSuggestionPayload,
        DismissSuggestionService,
    )
    from pilot_space.infrastructure.database.repositories.digest_repository import (
        DismissalRepository,
    )

    dismissal_repo = DismissalRepository(session)
    service = DismissSuggestionService(session, dismissal_repo)
    await service.execute(
        DismissSuggestionPayload(
            workspace_id=workspace_id,
            user_id=user_id,
            suggestion_id=payload.suggestion_id,
            entity_id=payload.entity_id,
            entity_type=payload.entity_type,
            category=payload.category,
        )
    )
    await session.commit()


# ── Chat-to-Note router ─────────────────────────────────────────────
# Mounted under /workspaces/{workspace_id}/notes (separate prefix)

notes_from_chat_router = APIRouter(
    prefix="/workspaces/{workspace_id}/notes",
    tags=["homepage", "notes"],
)


@notes_from_chat_router.post(
    "/from-chat",
    response_model=CreateNoteFromChatResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create note from chat session",
    description="Convert a homepage chat conversation into a structured note.",
)
async def create_note_from_chat(
    workspace_id: UUID,
    payload: CreateNoteFromChatPayload,
    session: DbSession,
    user_id: WorkspaceMemberId,
) -> CreateNoteFromChatResponse:
    """Create a note from a homepage chat session.

    Fetches AI chat messages, structures them as TipTap blocks,
    and creates a note linked to the source session.

    Args:
        workspace_id: Workspace UUID.
        payload: Chat-to-note creation details.
        session: Database session.
        user_id: Authenticated user with workspace membership verified.

    Returns:
        CreateNoteFromChatResponse with created note metadata.
    """
    from pilot_space.application.services.note import (
        CreateNoteFromChatPayload as ServicePayload,
        CreateNoteFromChatService,
    )
    from pilot_space.infrastructure.database.repositories.note_repository import (
        NoteRepository,
    )

    note_repo = NoteRepository(session)
    service = CreateNoteFromChatService(session, note_repo)

    result = await service.execute(
        ServicePayload(
            workspace_id=workspace_id,
            user_id=user_id,
            chat_session_id=payload.chat_session_id,
            title=payload.title,
            project_id=payload.project_id,
        )
    )

    await session.commit()

    return CreateNoteFromChatResponse(
        data=CreateNoteFromChatData(
            note_id=result.note_id,
            title=result.title,
            source_chat_session_id=result.source_chat_session_id,
        )
    )


__all__ = ["notes_from_chat_router", "router"]

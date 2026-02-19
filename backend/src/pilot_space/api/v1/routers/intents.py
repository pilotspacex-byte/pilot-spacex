"""Intent API router for AI Workforce Platform.

T-014: Intent endpoints
- POST /workspaces/{workspace_id}/intents/detect
- POST /workspaces/{workspace_id}/intents/{intent_id}/confirm
- POST /workspaces/{workspace_id}/intents/{intent_id}/reject
- POST /workspaces/{workspace_id}/intents/{intent_id}/edit
- POST /workspaces/{workspace_id}/intents/confirm-all
- GET  /workspaces/{workspace_id}/intents (list by status)

Feature 015: AI Workforce Platform (M2)
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Path, Query, status

from pilot_space.api.v1.dependencies import WorkspaceRepositoryDep
from pilot_space.api.v1.intent_deps import IntentDetectionServiceDep, IntentServiceDep
from pilot_space.api.v1.schemas.intent import (
    ConfirmAllRequest,
    ConfirmAllResponse,
    DetectIntentResponse,
    IntentDetectRequest,
    IntentEditRequest,
    IntentResponse,
)
from pilot_space.application.services.intent.detection_service import (
    DetectIntentPayload,
    IntentSource,
)
from pilot_space.application.services.intent.intent_service import (
    ConfirmAllPayload,
    ConfirmIntentPayload,
    EditIntentPayload,
    RejectIntentPayload,
)
from pilot_space.dependencies import SyncedUserId
from pilot_space.dependencies.auth import SessionDep
from pilot_space.domain.work_intent import IntentStatus
from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()

WorkspaceIdPath = Annotated[UUID, Path(description="Workspace UUID")]
IntentIdPath = Annotated[UUID, Path(description="Intent UUID")]


async def _validate_workspace(
    workspace_id: UUID,
    workspace_repo: WorkspaceRepositoryDep,
) -> None:
    """Verify workspace exists. Raises 404 if not found."""
    ws = await workspace_repo.get_by_id_scalar(workspace_id)
    if ws is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace {workspace_id} not found",
        )


@router.post(
    "/{workspace_id}/intents/detect",
    response_model=DetectIntentResponse,
    status_code=status.HTTP_200_OK,
    summary="Detect work intents from text",
)
async def detect_intents(
    workspace_id: WorkspaceIdPath,
    request: IntentDetectRequest,
    session: SessionDep,
    detection_service: IntentDetectionServiceDep,
    workspace_repo: WorkspaceRepositoryDep,
    current_user: SyncedUserId,
) -> DetectIntentResponse:
    """Detect work intents from chat or note text.

    Uses Claude Sonnet structured output with few-shot prompting.
    Chat source sets a 3s Redis lock; note source checks the lock and
    skips if chat detection is in progress (T-010).

    Returns detected intents (persisted as DETECTED status).
    """
    await _validate_workspace(workspace_id, workspace_repo)

    try:
        source = IntentSource(request.source)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="source must be 'chat' or 'note'",
        ) from exc

    payload = DetectIntentPayload(
        workspace_id=workspace_id,
        text=request.text,
        source=source,
        source_block_id=request.source_block_id,
        owner=str(current_user),
    )

    result = await detection_service.detect(payload)

    return DetectIntentResponse(
        intents=[IntentResponse.from_model(i) for i in result.intents],
        total_detected=result.total_detected,
        detection_model=result.detection_model,
        chat_lock_was_active=result.chat_lock_was_active,
    )


@router.post(
    "/{workspace_id}/intents/{intent_id}/confirm",
    response_model=IntentResponse,
    status_code=status.HTTP_200_OK,
    summary="Confirm a detected intent",
)
async def confirm_intent(
    workspace_id: WorkspaceIdPath,
    intent_id: IntentIdPath,
    session: SessionDep,
    intent_service: IntentServiceDep,
    workspace_repo: WorkspaceRepositoryDep,
    current_user: SyncedUserId,
) -> IntentResponse:
    """Confirm a detected intent, locking its what/why fields."""
    await _validate_workspace(workspace_id, workspace_repo)

    try:
        updated = await intent_service.confirm(
            ConfirmIntentPayload(intent_id=intent_id, workspace_id=workspace_id)
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return IntentResponse.from_model(updated)


@router.post(
    "/{workspace_id}/intents/{intent_id}/reject",
    response_model=IntentResponse,
    status_code=status.HTTP_200_OK,
    summary="Reject an intent",
)
async def reject_intent(
    workspace_id: WorkspaceIdPath,
    intent_id: IntentIdPath,
    session: SessionDep,
    intent_service: IntentServiceDep,
    workspace_repo: WorkspaceRepositoryDep,
    current_user: SyncedUserId,
) -> IntentResponse:
    """Reject an intent from any non-terminal state."""
    await _validate_workspace(workspace_id, workspace_repo)

    try:
        updated = await intent_service.reject(
            RejectIntentPayload(intent_id=intent_id, workspace_id=workspace_id)
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return IntentResponse.from_model(updated)


@router.post(
    "/{workspace_id}/intents/{intent_id}/edit",
    response_model=IntentResponse,
    status_code=status.HTTP_200_OK,
    summary="Edit a detected intent before confirmation",
)
async def edit_intent(
    workspace_id: WorkspaceIdPath,
    intent_id: IntentIdPath,
    request: IntentEditRequest,
    session: SessionDep,
    intent_service: IntentServiceDep,
    workspace_repo: WorkspaceRepositoryDep,
    current_user: SyncedUserId,
) -> IntentResponse:
    """Edit intent fields while still in DETECTED status.

    Updating 'what' resets dedup_status to pending so J-1 re-processes.
    """
    await _validate_workspace(workspace_id, workspace_repo)

    try:
        updated = await intent_service.edit(
            EditIntentPayload(
                intent_id=intent_id,
                workspace_id=workspace_id,
                new_what=request.new_what,
                new_why=request.new_why,
                new_constraints=request.new_constraints,
                new_acceptance=request.new_acceptance,
            )
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return IntentResponse.from_model(updated)


@router.post(
    "/{workspace_id}/intents/confirm-all",
    response_model=ConfirmAllResponse,
    status_code=status.HTTP_200_OK,
    summary="Batch confirm top-N detected intents",
)
async def confirm_all_intents(
    workspace_id: WorkspaceIdPath,
    request: ConfirmAllRequest,
    session: SessionDep,
    intent_service: IntentServiceDep,
    workspace_repo: WorkspaceRepositoryDep,
    current_user: SyncedUserId,
) -> ConfirmAllResponse:
    """Confirm top-N detected intents by confidence.

    C-8: Only intents with dedup_status='complete' are eligible.
    Intents still being deduplicated are reported in deduplicating_count.
    """
    await _validate_workspace(workspace_id, workspace_repo)

    result = await intent_service.confirm_all(
        ConfirmAllPayload(
            workspace_id=workspace_id,
            min_confidence=request.min_confidence,
            max_count=request.max_count,
        )
    )

    return ConfirmAllResponse(
        confirmed=[IntentResponse.from_model(i) for i in result.confirmed],
        confirmed_count=len(result.confirmed),
        remaining_count=result.remaining_count,
        deduplicating_count=result.deduplicating_count,
    )


@router.get(
    "/{workspace_id}/intents",
    response_model=list[IntentResponse],
    status_code=status.HTTP_200_OK,
    summary="List intents by status",
)
async def list_intents(
    workspace_id: WorkspaceIdPath,
    session: SessionDep,
    intent_service: IntentServiceDep,
    workspace_repo: WorkspaceRepositoryDep,
    current_user: SyncedUserId,
    intent_status: str = Query(default="detected", description="Filter by status"),
) -> list[IntentResponse]:
    """List intents for a workspace filtered by status."""
    await _validate_workspace(workspace_id, workspace_repo)

    try:
        status_filter = IntentStatus(intent_status)
    except ValueError as exc:
        valid_statuses = [s.value for s in IntentStatus]
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid status. Valid values: {valid_statuses}",
        ) from exc

    intents = await intent_service.list_by_status(workspace_id, status_filter)
    return [IntentResponse.from_model(i) for i in intents]


@router.get(
    "/{workspace_id}/intents/{intent_id}",
    response_model=IntentResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a single intent",
)
async def get_intent(
    workspace_id: WorkspaceIdPath,
    intent_id: IntentIdPath,
    session: SessionDep,
    intent_service: IntentServiceDep,
    workspace_repo: WorkspaceRepositoryDep,
    current_user: SyncedUserId,
) -> IntentResponse:
    """Get a single intent by ID."""
    await _validate_workspace(workspace_id, workspace_repo)

    try:
        intent = await intent_service.get_intent(intent_id, workspace_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return IntentResponse.from_model(intent)

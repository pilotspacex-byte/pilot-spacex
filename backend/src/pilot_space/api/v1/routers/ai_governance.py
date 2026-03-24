"""AI Governance API — policy CRUD, BYOK status, artifact rollback.

Endpoints:
  GET  /workspaces/{slug}/settings/ai-policy                        — list policy matrix
  PUT  /workspaces/{slug}/settings/ai-policy/{role}/{action_type}  — upsert policy row
  DEL  /workspaces/{slug}/settings/ai-policy/{role}/{action_type}  — delete policy row
  GET  /workspaces/{slug}/settings/ai-status                        — BYOK status
  POST /workspaces/{slug}/audit/{entry_id}/rollback                  — rollback AI artifact

Authorization:
  - GET/PUT/DELETE policy: ADMIN or OWNER role (settings:read for GET, settings:manage for write)
  - GET ai-status: ADMIN or OWNER role
  - POST rollback: OWNER only

Requirements: AIGOV-01, AIGOV-02, AIGOV-04, AIGOV-05
"""

from __future__ import annotations

import uuid
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Path, status
from pydantic import BaseModel

from pilot_space.ai.infrastructure.key_storage import SecureKeyStorage
from pilot_space.ai.providers.constants import PROVIDER_SERVICE_SLOTS
from pilot_space.application.services.issue.update_issue_service import (
    UNCHANGED,
    UpdateIssuePayload,
    UpdateIssueService,
)
from pilot_space.application.services.note.update_note_service import (
    UpdateNotePayload,
    UpdateNoteService,
)
from pilot_space.config import get_settings
from pilot_space.dependencies.auth import CurrentUser, SessionDep
from pilot_space.domain.exceptions import ForbiddenError, NotFoundError, ValidationError
from pilot_space.infrastructure.database.models import IssuePriority
from pilot_space.infrastructure.database.models.audit_log import ActorType, AuditLog
from pilot_space.infrastructure.database.permissions import check_permission
from pilot_space.infrastructure.database.repositories import (
    ActivityRepository,
    IssueRepository,
    LabelRepository,
    NoteRepository,
)
from pilot_space.infrastructure.database.repositories.audit_log_repository import (
    AuditLogRepository,
)
from pilot_space.infrastructure.database.repositories.workspace_ai_policy_repository import (
    WorkspaceAIPolicyRepository,
)
from pilot_space.infrastructure.database.repositories.workspace_repository import (
    WorkspaceRepository,
)

router = APIRouter(tags=["ai-governance"])

# ---------------------------------------------------------------------------
# Rollback-eligible resource types for v1
# ---------------------------------------------------------------------------

_ROLLBACK_RESOURCE_TYPES = {"issue", "note"}

# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class PolicyRowIn(BaseModel):
    """Request body for policy upsert."""

    requires_approval: bool


class PolicyRowResponse(BaseModel):
    """Response for a single policy row."""

    role: str
    action_type: str
    requires_approval: bool


class AIStatusResponse(BaseModel):
    """Response for BYOK status endpoint."""

    byok_configured: bool
    providers: list[str]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _resolve_workspace(
    workspace_slug: str,
    session: object,
) -> UUID:
    """Resolve workspace slug (or UUID string) to workspace.id.

    Args:
        workspace_slug: URL path parameter — slug or UUID string.
        session: Async database session.

    Returns:
        Workspace UUID.

    Raises:
        HTTPException: 404 if workspace not found.
    """

    workspace_repo = WorkspaceRepository(session)  # type: ignore[arg-type]
    try:
        as_uuid = UUID(workspace_slug)
        workspace = await workspace_repo.get_by_id_scalar(as_uuid)
    except ValueError:
        workspace = await workspace_repo.get_by_slug_scalar(workspace_slug)

    if workspace is None:
        raise NotFoundError("Workspace not found")
    return workspace.id  # type: ignore[return-value]


async def _require_admin_or_owner(
    session: object,
    user_id: UUID,
    workspace_id: UUID,
) -> None:
    """Assert the user has settings:read permission (ADMIN or OWNER).

    Args:
        session: Async database session.
        user_id: Requesting user UUID.
        workspace_id: Workspace being accessed.

    Raises:
        HTTPException: 403 if permission is not granted.
    """
    allowed = await check_permission(
        session,  # type: ignore[arg-type]
        user_id,
        workspace_id,
        resource="settings",
        action="read",
    )
    if not allowed:
        raise ForbiddenError("Admin or owner access required")


async def _require_owner(
    session: object,
    user_id: UUID,
    workspace_id: UUID,
) -> None:
    """Assert the user has settings:manage permission (OWNER only).

    Args:
        session: Async database session.
        user_id: Requesting user UUID.
        workspace_id: Workspace being accessed.

    Raises:
        HTTPException: 403 if permission is not granted.
    """
    allowed = await check_permission(
        session,  # type: ignore[arg-type]
        user_id,
        workspace_id,
        resource="settings",
        action="manage",
    )
    if not allowed:
        raise ForbiddenError("Owner access required")


def _is_rollback_eligible(entry: AuditLog) -> bool:
    """Return True if the audit entry is eligible for rollback.

    Criteria:
    - actor_type == AI
    - resource_type in _ROLLBACK_RESOURCE_TYPES
    - action ends with .create or .update

    Args:
        entry: AuditLog row.

    Returns:
        True if eligible.
    """
    return (
        entry.actor_type == ActorType.AI
        and entry.resource_type in _ROLLBACK_RESOURCE_TYPES
        and (entry.action.endswith(".create") or entry.action.endswith(".update"))
    )


async def _dispatch_rollback(
    resource_type: str,
    resource_id: uuid.UUID,
    before_state: dict,  # type: ignore[type-arg]
    session: object,
) -> None:
    """Dispatch rollback to the appropriate service based on resource_type.

    For v1 only 'issue' and 'note' are supported. Extend for v2.

    Args:
        resource_type: String resource category.
        resource_id: UUID of the resource to restore.
        before_state: Dict of field values to restore.
        session: Async database session.

    Raises:
        HTTPException: 422 if resource_type not supported.
    """
    if resource_type not in _ROLLBACK_RESOURCE_TYPES:
        raise ValidationError(f"Rollback not supported for resource_type '{resource_type}'.")

    if resource_type == "issue":
        await _rollback_issue(resource_id, before_state, session)
    elif resource_type == "note":
        await _rollback_note(resource_id, before_state, session)


# System actor UUID for rollback operations (nil UUID, not user-initiated)
_SYSTEM_ACTOR_ID = uuid.UUID(int=0)

# Priority string → enum mapping for issue rollback
_PRIORITY_MAP: dict[str, IssuePriority] = {
    "urgent": IssuePriority.URGENT,
    "high": IssuePriority.HIGH,
    "medium": IssuePriority.MEDIUM,
    "low": IssuePriority.LOW,
    "none": IssuePriority.NONE,
}


async def _rollback_issue(
    resource_id: uuid.UUID,
    before_state: dict,  # type: ignore[type-arg]
    session: object,
) -> None:
    """Restore an issue to its before_state via UpdateIssueService.

    Args:
        resource_id: Issue UUID to restore.
        before_state: Dict of field values captured before the AI action.
        session: Async database session.
    """
    raw_state_id = before_state.get("state_id")
    payload = UpdateIssuePayload(
        issue_id=resource_id,
        actor_id=_SYSTEM_ACTOR_ID,
        name=before_state.get("title", UNCHANGED),
        description=before_state.get("description", UNCHANGED),
        priority=(
            _PRIORITY_MAP.get(str(before_state["priority"]).lower(), UNCHANGED)
            if "priority" in before_state
            else UNCHANGED
        ),
        state_id=uuid.UUID(raw_state_id) if raw_state_id else UNCHANGED,
    )

    svc = UpdateIssueService(
        session=session,  # type: ignore[arg-type]
        issue_repository=IssueRepository(session),  # type: ignore[arg-type]
        activity_repository=ActivityRepository(session),  # type: ignore[arg-type]
        label_repository=LabelRepository(session),  # type: ignore[arg-type]
    )
    await svc.execute(payload)


async def _rollback_note(
    resource_id: uuid.UUID,
    before_state: dict,  # type: ignore[type-arg]
    session: object,
) -> None:
    """Restore a note to its before_state via UpdateNoteService.

    Args:
        resource_id: Note UUID to restore.
        before_state: Dict of field values captured before the AI action.
        session: Async database session.
    """
    payload = UpdateNotePayload(
        note_id=resource_id,
        title=before_state.get("title"),
        content=before_state.get("content"),
        summary=before_state.get("summary"),
        # Omit expected_updated_at to skip optimistic lock for rollback
    )

    svc = UpdateNoteService(
        session=session,  # type: ignore[arg-type]
        note_repository=NoteRepository(session),  # type: ignore[arg-type]
    )
    await svc.execute(payload)


# ---------------------------------------------------------------------------
# Policy CRUD endpoints
# ---------------------------------------------------------------------------


@router.get("/workspaces/{workspace_slug}/settings/ai-policy")
async def get_ai_policy(
    workspace_slug: Annotated[str, Path(description="Workspace slug or UUID")],
    current_user: CurrentUser,
    session: SessionDep,
) -> list[PolicyRowResponse]:
    """Return all policy rows for the workspace.

    Absence of a row means fall back to hardcoded ApprovalService defaults.
    Requires ADMIN or OWNER role.

    Args:
        workspace_slug: Workspace slug or UUID.
        current_user: Authenticated user token payload.
        session: Database session.

    Returns:
        List of policy rows for the workspace.
    """
    workspace_id = await _resolve_workspace(workspace_slug, session)
    await _require_admin_or_owner(session, current_user.user_id, workspace_id)

    repo = WorkspaceAIPolicyRepository(session)
    rows = await repo.list_for_workspace(workspace_id)
    return [
        PolicyRowResponse(
            role=r.role,
            action_type=r.action_type,
            requires_approval=r.requires_approval,
        )
        for r in rows
    ]


@router.put("/workspaces/{workspace_slug}/settings/ai-policy/{role}/{action_type}")
async def set_ai_policy(
    workspace_slug: Annotated[str, Path(description="Workspace slug or UUID")],
    role: Annotated[str, Path(description="Role to configure (ADMIN, MEMBER, GUEST)")],
    action_type: Annotated[str, Path(description="Action type string")],
    body: PolicyRowIn,
    current_user: CurrentUser,
    session: SessionDep,
) -> PolicyRowResponse:
    """Upsert a policy row for the given role and action_type.

    The OWNER role is not configurable — owners always control all AI actions.
    Requires OWNER role (settings:manage permission).

    Args:
        workspace_slug: Workspace slug or UUID.
        role: Role to configure. Must not be OWNER.
        action_type: Action type string.
        body: Policy configuration.
        current_user: Authenticated user token payload.
        session: Database session.

    Returns:
        Updated policy row.

    Raises:
        HTTPException: 400 if role is OWNER. 403 if user is not owner.
    """
    if role.upper() == "OWNER":
        raise ValidationError("Owner role policy is not configurable.")

    workspace_id = await _resolve_workspace(workspace_slug, session)
    await _require_owner(session, current_user.user_id, workspace_id)

    repo = WorkspaceAIPolicyRepository(session)
    policy = await repo.upsert(workspace_id, role.upper(), action_type, body.requires_approval)
    return PolicyRowResponse(
        role=policy.role,
        action_type=policy.action_type,
        requires_approval=policy.requires_approval,
    )


@router.delete(
    "/workspaces/{workspace_slug}/settings/ai-policy/{role}/{action_type}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_ai_policy(
    workspace_slug: Annotated[str, Path(description="Workspace slug or UUID")],
    role: Annotated[str, Path(description="Role")],
    action_type: Annotated[str, Path(description="Action type string")],
    current_user: CurrentUser,
    session: SessionDep,
) -> None:
    """Delete a policy row, reverting to hardcoded defaults.

    Requires OWNER role.

    Args:
        workspace_slug: Workspace slug or UUID.
        role: Role to remove policy for.
        action_type: Action type to remove.
        current_user: Authenticated user token payload.
        session: Database session.
    """
    workspace_id = await _resolve_workspace(workspace_slug, session)
    await _require_owner(session, current_user.user_id, workspace_id)

    repo = WorkspaceAIPolicyRepository(session)
    await repo.delete(workspace_id, role.upper(), action_type)


# ---------------------------------------------------------------------------
# AI status endpoint
# ---------------------------------------------------------------------------


@router.get("/workspaces/{workspace_slug}/settings/ai-status")
async def get_ai_status(
    workspace_slug: Annotated[str, Path(description="Workspace slug or UUID")],
    current_user: CurrentUser,
    session: SessionDep,
) -> AIStatusResponse:
    """Return BYOK configuration status for the workspace.

    Reports which providers have valid API keys configured.
    Requires ADMIN or OWNER role.

    Args:
        workspace_slug: Workspace slug or UUID.
        current_user: Authenticated user token payload.
        session: Database session.

    Returns:
        BYOK status with configured provider list.
    """
    workspace_id = await _resolve_workspace(workspace_slug, session)
    await _require_admin_or_owner(session, current_user.user_id, workspace_id)

    settings = get_settings()
    key_storage = SecureKeyStorage(
        db=session,  # type: ignore[arg-type]
        master_secret=settings.encryption_key.get_secret_value(),
    )

    configured_providers: list[str] = []
    # Derive unique (provider, service_type) pairs from canonical slots
    provider_service_pairs = {(p, st) for p, st, _ in PROVIDER_SERVICE_SLOTS}
    for provider, service_type in provider_service_pairs:
        key_info = await key_storage.get_key_info(workspace_id, provider, service_type)
        if key_info is not None and key_info.is_valid:
            configured_providers.append(provider)

    return AIStatusResponse(
        byok_configured=len(configured_providers) > 0,
        providers=configured_providers,
    )


# ---------------------------------------------------------------------------
# Rollback endpoint
# ---------------------------------------------------------------------------


@router.post("/workspaces/{workspace_slug}/audit/{entry_id}/rollback")
async def rollback_ai_artifact(
    workspace_slug: Annotated[str, Path(description="Workspace slug or UUID")],
    entry_id: Annotated[UUID, Path(description="Audit log entry UUID to rollback")],
    current_user: CurrentUser,
    session: SessionDep,
) -> dict[str, str]:
    """Roll back an AI-created or AI-modified artifact to its pre-AI state.

    Only AI actor entries for issue and note resource types with .create or .update
    actions are rollback-eligible. The rollback itself is recorded as a new audit entry
    with actor_type=USER and action="ai.rollback".

    Requires OWNER role.

    Args:
        workspace_slug: Workspace slug or UUID.
        entry_id: Audit log entry UUID.
        current_user: Authenticated user token payload.
        session: Database session.

    Returns:
        Status dict with status and entry_id.

    Raises:
        HTTPException: 404 if entry not found. 400 if entry not rollback-eligible.
    """
    workspace_id = await _resolve_workspace(workspace_slug, session)
    await _require_owner(session, current_user.user_id, workspace_id)

    audit_repo = AuditLogRepository(session)
    entry = await audit_repo.get_by_id(entry_id)
    if entry is None:
        raise NotFoundError("Audit entry not found.")

    if not _is_rollback_eligible(entry):
        raise ValidationError(
            "Entry is not rollback-eligible. "
            "Rollback applies only to AI create/update actions on supported resource types."
        )

    before_state: dict = (entry.payload or {}).get("before") or {}  # type: ignore[assignment]
    current_state: dict = (entry.payload or {}).get("after") or {}  # type: ignore[assignment]

    if entry.resource_id is None:
        raise ValidationError("Audit entry has no resource_id — cannot rollback.")
    await _dispatch_rollback(entry.resource_type, entry.resource_id, before_state, session)

    # Record the rollback as a new immutable audit entry
    await audit_repo.create(
        workspace_id=workspace_id,
        actor_id=current_user.user_id,
        actor_type=ActorType.USER,
        action="ai.rollback",
        resource_type=entry.resource_type,
        resource_id=entry.resource_id,
        payload={"before": current_state, "after": before_state},
    )

    return {"status": "rolled_back", "entry_id": str(entry_id)}


__all__ = ["router"]

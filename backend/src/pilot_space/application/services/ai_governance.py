"""AI Governance service -- rollback eligibility, execution, and policy management.

Handles rollback of AI-created/modified artifacts to their pre-AI state.
Supports issue and note resource types for v1.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from pilot_space.domain.exceptions import ForbiddenError, NotFoundError, ValidationError

if TYPE_CHECKING:
    from pilot_space.application.services.issue.update_issue_service import UpdateIssueService
    from pilot_space.application.services.note.update_note_service import UpdateNoteService
from pilot_space.infrastructure.database.models.audit_log import ActorType, AuditLog
from pilot_space.infrastructure.database.permissions import check_permission
from pilot_space.infrastructure.database.repositories.audit_log_repository import (
    AuditLogRepository,
)
from pilot_space.infrastructure.database.repositories.workspace_ai_policy_repository import (
    WorkspaceAIPolicyRepository,
)
from pilot_space.infrastructure.database.repositories.workspace_repository import (
    WorkspaceRepository,
)
from pilot_space.infrastructure.logging import get_logger
from pilot_space.schemas.ai_governance import AIStatus, GovernanceAction, RollbackResult

logger = get_logger(__name__)

# Rollback-eligible resource types for v1
_ROLLBACK_RESOURCE_TYPES = {"issue", "note"}

# System actor UUID for rollback operations (nil UUID, not user-initiated)
_SYSTEM_ACTOR_ID = uuid.UUID(int=0)


class GovernanceRollbackService:
    """Handles AI artifact rollback and governance operations.

    Args:
        session: Request-scoped async database session.
        workspace_repository: Repository for workspace lookups.
        audit_log_repository: Repository for audit log operations.
        workspace_ai_policy_repository: Repository for AI policy CRUD.
    """

    def __init__(
        self,
        session: AsyncSession,
        workspace_repository: WorkspaceRepository,
        audit_log_repository: AuditLogRepository,
        workspace_ai_policy_repository: WorkspaceAIPolicyRepository,
        update_issue_service: UpdateIssueService,
        update_note_service: UpdateNoteService,
    ) -> None:
        self._session = session
        self._workspace_repo = workspace_repository
        self._audit_repo = audit_log_repository
        self._policy_repo = workspace_ai_policy_repository
        self._update_issue_svc = update_issue_service
        self._update_note_svc = update_note_service

    async def _resolve_workspace(self, workspace_slug: str) -> UUID:
        """Resolve workspace slug (or UUID string) to workspace.id.

        Raises:
            NotFoundError: If workspace not found.
        """
        try:
            as_uuid = UUID(workspace_slug)
            workspace = await self._workspace_repo.get_by_id_scalar(as_uuid)
        except ValueError:
            workspace = await self._workspace_repo.get_by_slug_scalar(workspace_slug)

        if workspace is None:
            raise NotFoundError("Workspace not found")
        return workspace.id  # type: ignore[return-value]

    async def _require_admin_or_owner(self, user_id: UUID, workspace_id: UUID) -> None:
        """Assert the user has settings:read permission (ADMIN or OWNER).

        Raises:
            ForbiddenError: If permission is not granted.
        """
        allowed = await check_permission(
            self._session,
            user_id,
            workspace_id,
            resource="settings",
            action="read",
        )
        if not allowed:
            raise ForbiddenError("Admin or owner access required")

    async def _require_owner(self, user_id: UUID, workspace_id: UUID) -> None:
        """Assert the user has settings:manage permission (OWNER only).

        Raises:
            ForbiddenError: If permission is not granted.
        """
        allowed = await check_permission(
            self._session,
            user_id,
            workspace_id,
            resource="settings",
            action="manage",
        )
        if not allowed:
            raise ForbiddenError("Owner access required")

    @staticmethod
    def _is_rollback_eligible(entry: AuditLog) -> bool:
        """Return True if the audit entry is eligible for rollback.

        Criteria:
        - actor_type == AI
        - resource_type in _ROLLBACK_RESOURCE_TYPES
        - action ends with .create or .update
        """
        return (
            entry.actor_type == ActorType.AI
            and entry.resource_type in _ROLLBACK_RESOURCE_TYPES
            and (entry.action.endswith(".create") or entry.action.endswith(".update"))
        )

    async def _dispatch_rollback(
        self,
        resource_type: str,
        resource_id: uuid.UUID,
        before_state: dict[str, Any],
    ) -> None:
        """Dispatch rollback to the appropriate service based on resource_type.

        Raises:
            ValidationError: If resource_type not supported.
        """
        if resource_type not in _ROLLBACK_RESOURCE_TYPES:
            raise ValidationError(f"Rollback not supported for resource_type '{resource_type}'.")

        if resource_type == "issue":
            await self._rollback_issue(resource_id, before_state)
        elif resource_type == "note":
            await self._rollback_note(resource_id, before_state)

    async def _rollback_issue(
        self,
        resource_id: uuid.UUID,
        before_state: dict[str, Any],
    ) -> None:
        """Restore an issue to its before_state via UpdateIssueService."""
        from pilot_space.application.services.issue.update_issue_service import (
            UNCHANGED,
            UpdateIssuePayload,
        )
        from pilot_space.infrastructure.database.models import IssuePriority

        priority_map: dict[str, IssuePriority] = {
            "urgent": IssuePriority.URGENT,
            "high": IssuePriority.HIGH,
            "medium": IssuePriority.MEDIUM,
            "low": IssuePriority.LOW,
            "none": IssuePriority.NONE,
        }

        raw_state_id = before_state.get("state_id")
        payload = UpdateIssuePayload(
            issue_id=resource_id,
            actor_id=_SYSTEM_ACTOR_ID,
            name=before_state.get("title", UNCHANGED),
            description=before_state.get("description", UNCHANGED),
            priority=(
                priority_map.get(str(before_state["priority"]).lower(), UNCHANGED)
                if "priority" in before_state
                else UNCHANGED
            ),
            state_id=uuid.UUID(raw_state_id) if raw_state_id else UNCHANGED,
        )

        await self._update_issue_svc.execute(payload)

    async def _rollback_note(
        self,
        resource_id: uuid.UUID,
        before_state: dict[str, Any],
    ) -> None:
        """Restore a note to its before_state via UpdateNoteService."""
        from pilot_space.application.services.note.update_note_service import UpdateNotePayload

        payload = UpdateNotePayload(
            note_id=resource_id,
            title=before_state.get("title"),
            content=before_state.get("content"),
            summary=before_state.get("summary"),
        )

        await self._update_note_svc.execute(payload)

    async def execute_rollback(
        self,
        workspace_slug: str,
        entry_id: UUID,
        user_id: UUID,
    ) -> RollbackResult:
        """Roll back an AI-created or AI-modified artifact to its pre-AI state.

        Raises:
            NotFoundError: If audit entry not found.
            ValidationError: If entry not rollback-eligible or has no resource_id.
            ForbiddenError: If user is not owner.
        """
        workspace_id = await self._resolve_workspace(workspace_slug)
        await self._require_owner(user_id, workspace_id)

        entry = await self._audit_repo.get_by_id(entry_id)
        if entry is None:
            raise NotFoundError("Audit entry not found.")

        if not self._is_rollback_eligible(entry):
            raise ValidationError(
                "Entry is not rollback-eligible. "
                "Rollback applies only to AI create/update actions on supported resource types."
            )

        before_state: dict[str, Any] = (entry.payload or {}).get("before") or {}
        current_state: dict[str, Any] = (entry.payload or {}).get("after") or {}

        if entry.resource_id is None:
            raise ValidationError("Audit entry has no resource_id -- cannot rollback.")
        await self._dispatch_rollback(entry.resource_type, entry.resource_id, before_state)

        # Record the rollback as a new immutable audit entry
        await self._audit_repo.create(
            workspace_id=workspace_id,
            actor_id=user_id,
            actor_type=ActorType.USER,
            action="ai.rollback",
            resource_type=entry.resource_type,
            resource_id=entry.resource_id,
            payload={"before": current_state, "after": before_state},
        )

        return RollbackResult(status="rolled_back", entry_id=entry_id)

    async def get_ai_status(
        self,
        workspace_slug: str,
        user_id: UUID,
    ) -> AIStatus:
        """Return BYOK configuration status for the workspace.

        Reports which providers have valid API keys configured.
        """
        from pilot_space.ai.infrastructure.key_storage import SecureKeyStorage
        from pilot_space.ai.providers.constants import PROVIDER_SERVICE_SLOTS
        from pilot_space.config import get_settings

        workspace_id = await self._resolve_workspace(workspace_slug)
        await self._require_admin_or_owner(user_id, workspace_id)

        settings = get_settings()
        key_storage = SecureKeyStorage(
            db=self._session,
            master_secret=settings.encryption_key.get_secret_value(),
        )

        configured_providers: list[str] = []
        provider_service_pairs = {(p, st) for p, st, _ in PROVIDER_SERVICE_SLOTS}
        for provider, service_type in provider_service_pairs:
            key_info = await key_storage.get_key_info(workspace_id, provider, service_type)
            if key_info is not None and key_info.is_valid:
                configured_providers.append(provider)

        return AIStatus(
            byok_configured=len(configured_providers) > 0,
            providers=tuple(configured_providers),
        )

    async def list_policies(
        self,
        workspace_slug: str,
        user_id: UUID,
    ) -> list[GovernanceAction]:
        """Return all policy rows for the workspace."""
        workspace_id = await self._resolve_workspace(workspace_slug)
        await self._require_admin_or_owner(user_id, workspace_id)

        rows = await self._policy_repo.list_for_workspace(workspace_id)
        return [
            GovernanceAction(
                role=r.role,
                action_type=r.action_type,
                requires_approval=r.requires_approval,
            )
            for r in rows
        ]

    async def upsert_policy(
        self,
        workspace_slug: str,
        user_id: UUID,
        role: str,
        action_type: str,
        requires_approval: bool,
    ) -> GovernanceAction:
        """Upsert a policy row for the given role and action_type.

        Raises:
            ValidationError: If role is OWNER.
            ForbiddenError: If user is not owner.
        """
        if role.upper() == "OWNER":
            raise ValidationError("Owner role policy is not configurable.")

        workspace_id = await self._resolve_workspace(workspace_slug)
        await self._require_owner(user_id, workspace_id)

        policy = await self._policy_repo.upsert(
            workspace_id, role.upper(), action_type, requires_approval
        )
        return GovernanceAction(
            role=policy.role,
            action_type=policy.action_type,
            requires_approval=policy.requires_approval,
        )

    async def delete_policy(
        self,
        workspace_slug: str,
        user_id: UUID,
        role: str,
        action_type: str,
    ) -> None:
        """Delete a policy row, reverting to hardcoded defaults.

        Raises:
            ForbiddenError: If user is not owner.
        """
        workspace_id = await self._resolve_workspace(workspace_slug)
        await self._require_owner(user_id, workspace_id)

        await self._policy_repo.delete(workspace_id, role.upper(), action_type)

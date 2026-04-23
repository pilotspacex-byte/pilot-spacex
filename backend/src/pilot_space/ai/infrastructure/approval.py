"""Human-in-the-loop approval service for AI actions.

Implements DD-003: Critical-only approval flow with configurable action classification.
Manages approval requests for AI-suggested actions, ensuring humans retain control
over critical operations while allowing safe automation of routine tasks.

T012: ApprovalService class implementation.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Final

from pilot_space.infrastructure.database.models.workspace_member import WorkspaceRole
from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from pilot_space.infrastructure.database.repositories.workspace_ai_policy_repository import (
        WorkspaceAIPolicyRepository,
    )

logger = get_logger(__name__)

# Default expiration time for approval requests
DEFAULT_EXPIRATION_HOURS: Final[int] = 24


class ApprovalStatus(StrEnum):
    """Status of an approval request.

    Attributes:
        PENDING: Awaiting human review.
        APPROVED: Human approved the action.
        REJECTED: Human rejected the action.
        EXPIRED: Request expired without response.
    """

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ActionType(StrEnum):
    """AI action types requiring approval classification.

    Per DD-003, actions are classified into three categories:
    - ALWAYS_REQUIRE: Critical destructive operations (workspace/project/issue/note deletion,
      PR merge, bulk delete)
    - DEFAULT_REQUIRE: Significant changes requiring approval by default but configurable
      (create sub-issues, extract issues, publish docs, post PR comments)
    - AUTO_EXECUTE: Safe suggestions applied automatically (suggest labels, suggest priority,
      auto-transition state, create annotation)
    """

    # ALWAYS_REQUIRE: Critical operations (non-configurable)
    DELETE_WORKSPACE = "delete_workspace"
    DELETE_PROJECT = "delete_project"
    DELETE_ISSUE = "delete_issue"
    DELETE_NOTE = "delete_note"
    MERGE_PR = "merge_pr"
    BULK_DELETE = "bulk_delete"

    # DEFAULT_REQUIRE: Significant changes (configurable)
    CREATE_SUB_ISSUES = "create_sub_issues"
    EXTRACT_ISSUES = "extract_issues"
    PUBLISH_DOCS = "publish_docs"
    POST_PR_COMMENTS = "post_pr_comments"
    CREATE_COMMENT = "create_comment"
    UPDATE_COMMENT = "update_comment"
    CREATE_ISSUE = "create_issue"
    UPDATE_ISSUE = "update_issue"
    CREATE_NOTE = "create_note"
    UPDATE_NOTE = "update_note"
    CREATE_PROJECT = "create_project"
    UPDATE_PROJECT = "update_project"
    UPDATE_PROJECT_SETTINGS = "update_project_settings"
    LINK_ISSUES = "link_issues"
    ADD_SUB_ISSUE = "add_sub_issue"
    TRANSITION_ISSUE_STATE = "transition_issue_state"
    LINK_ISSUE_TO_NOTE = "link_issue_to_note"
    INSERT_BLOCK = "insert_block"
    REMOVE_BLOCK = "remove_block"
    REMOVE_CONTENT = "remove_content"
    REPLACE_CONTENT = "replace_content"

    # ALWAYS_REQUIRE: Destructive link operations (non-configurable)
    UNLINK_ISSUE_FROM_NOTE = "unlink_issue_from_note"
    UNLINK_ISSUES = "unlink_issues"

    # AUTO_EXECUTE: Safe operations (configurable)
    SUGGEST_LABELS = "suggest_labels"
    SUGGEST_PRIORITY = "suggest_priority"
    AUTO_TRANSITION_STATE = "auto_transition_state"
    CREATE_ANNOTATION = "create_annotation"


class ApprovalLevel(StrEnum):
    """Workspace-level AI autonomy configuration.

    Per DD-003, workspaces can configure their AI autonomy level:
    - CONSERVATIVE: Require approval for all AI actions except suggestions.
    - BALANCED: Default behavior, approve critical only.
    - AUTONOMOUS: Auto-execute most actions, critical still require approval.
    """

    CONSERVATIVE = "conservative"
    BALANCED = "balanced"
    AUTONOMOUS = "autonomous"


@dataclass(frozen=True, slots=True, kw_only=True)
class ApprovalRequest:
    """Immutable approval request data.

    Represents a request for human approval of an AI action.

    Attributes:
        id: Unique request identifier.
        workspace_id: Workspace where action will be performed.
        action_type: Type of action requiring approval.
        action_data: Action-specific parameters and context.
        requested_by_agent: Name of the AI agent requesting approval.
        requested_at: When the request was created.
        expires_at: When the request expires.
        status: Current status of the request.
        resolved_at: When the request was resolved (if applicable).
        resolved_by: User who resolved the request (if applicable).
        resolution_comment: Optional comment from resolver.
    """

    id: uuid.UUID = field(default_factory=uuid.uuid4)
    workspace_id: uuid.UUID
    action_type: ActionType
    action_data: dict[str, Any]
    requested_by_agent: str
    requested_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    expires_at: datetime | None = None
    status: ApprovalStatus = ApprovalStatus.PENDING
    resolved_at: datetime | None = None
    resolved_by: uuid.UUID | None = None
    resolution_comment: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectSettings:
    """Project-level AI autonomy settings.

    Per DD-003, projects can override workspace-level settings.

    Attributes:
        level: Overall autonomy level.
        overrides: Action-specific overrides (action_type -> auto_execute: bool).
    """

    level: ApprovalLevel = ApprovalLevel.BALANCED
    overrides: dict[str, bool] = field(default_factory=dict)


class ApprovalService:
    """Service for managing AI action approval requests.

    Implements DD-003 critical-only approval flow with three-tier classification:
    1. ALWAYS_REQUIRE: Critical operations never auto-execute
    2. DEFAULT_REQUIRE: Configurable per workspace/project
    3. AUTO_EXECUTE: Safe operations auto-execute unless overridden

    Thread-safe for concurrent request creation and resolution.
    """

    # Legacy classification sets -- PermissionHandler.ACTION_CLASSIFICATIONS is
    # the single authoritative source for DD-003 classifications (Phase 80).
    # These sets are kept for backward compatibility with check_approval_required().
    ALWAYS_REQUIRE_ACTIONS: Final[set[ActionType]] = {
        ActionType.DELETE_WORKSPACE,
        ActionType.DELETE_PROJECT,
        ActionType.DELETE_ISSUE,
        ActionType.DELETE_NOTE,
        ActionType.MERGE_PR,
        ActionType.BULK_DELETE,
    }

    DEFAULT_REQUIRE_ACTIONS: Final[set[ActionType]] = {
        ActionType.CREATE_SUB_ISSUES,
        ActionType.EXTRACT_ISSUES,
        ActionType.PUBLISH_DOCS,
        ActionType.POST_PR_COMMENTS,
    }

    AUTO_EXECUTE_ACTIONS: Final[set[ActionType]] = {
        ActionType.SUGGEST_LABELS,
        ActionType.SUGGEST_PRIORITY,
        ActionType.AUTO_TRANSITION_STATE,
        ActionType.CREATE_ANNOTATION,
    }

    def __init__(
        self,
        session: AsyncSession,
        expiration_hours: int = DEFAULT_EXPIRATION_HOURS,
        policy_repo: WorkspaceAIPolicyRepository | None = None,
    ) -> None:
        """Initialize approval service.

        Args:
            session: SQLAlchemy async session for database operations.
            expiration_hours: Default expiration time for requests.
            policy_repo: Optional per-role x per-action policy repository.
                         When provided, check_approval_required() will query it
                         before falling back to hardcoded level logic.
        """
        self.session = session
        self.expiration_hours = expiration_hours
        self._policy_repo = policy_repo
        # Use repository for database persistence
        from pilot_space.infrastructure.database.repositories.approval_repository import (
            ApprovalRepository,
        )

        self._repository = ApprovalRepository(session)

    async def check_approval_required(
        self,
        action_type: ActionType,
        workspace_id: uuid.UUID = uuid.UUID(int=0),
        user_role: WorkspaceRole = WorkspaceRole.MEMBER,
        project_settings: ProjectSettings | None = None,
    ) -> bool:
        """Check if an action requires human approval.

        Implements four-tier classification per DD-003 and AIGOV-01:
        1. ALWAYS_REQUIRE: Critical operations never auto-execute (non-configurable)
        2. OWNER: Always auto-execute for non-ALWAYS_REQUIRE (hardcoded trust root)
        3. DB policy row: Per-role x per-action workspace override
        4. Level defaults: CONSERVATIVE / BALANCED / AUTONOMOUS fallback

        Args:
            action_type: The action to check.
            workspace_id: Workspace to look up policy for. Defaults to nil UUID
                          (backward-compat: callers not yet wired pass no workspace_id).
                          # TODO Phase 4: all callers should pass real workspace_id.
            user_role: Role of the user requesting the action. Defaults to MEMBER
                       for backward compatibility.
                       # TODO Phase 4: all callers should pass real user_role.
            project_settings: Optional project-level settings override (legacy).

        Returns:
            True if approval is required, False if action can auto-execute.

        Example:
            >>> settings = ProjectSettings(level=ApprovalLevel.BALANCED)
            >>> await service.check_approval_required(
            ...     ActionType.DELETE_WORKSPACE, workspace_id, WorkspaceRole.ADMIN
            ... )
            True
            >>> await service.check_approval_required(
            ...     ActionType.SUGGEST_LABELS, workspace_id, WorkspaceRole.MEMBER
            ... )
            False
        """
        # 1. ALWAYS_REQUIRE: Critical operations never auto-execute (non-configurable)
        if action_type in self.ALWAYS_REQUIRE_ACTIONS:
            logger.debug(
                "approval_requires_approval_always",
                action_type=action_type.value,
                classification="always_require",
            )
            return True

        # 2. OWNER: hardcoded trust root — always auto-execute non-ALWAYS_REQUIRE
        if user_role == WorkspaceRole.OWNER:
            logger.debug(
                "approval_owner_auto_execute",
                action_type=action_type.value,
                user_role=user_role.value,
            )
            return False

        # 3. DB policy row lookup (workspace-scoped, role-scoped)
        if self._policy_repo is not None and workspace_id != uuid.UUID(int=0):
            policy_row = await self._policy_repo.get(
                workspace_id, user_role.value, action_type.value
            )
            if policy_row is not None:
                logger.debug(
                    "approval_determined_by_db_policy",
                    action_type=action_type.value,
                    user_role=user_role.value,
                    requires_approval=policy_row.requires_approval,
                )
                return policy_row.requires_approval

        # 4. Fall back to existing level logic (legacy / no policy row)
        settings = project_settings or ProjectSettings()
        action_name = action_type.value

        if action_name in settings.overrides:
            auto_execute = settings.overrides[action_name]
            logger.debug(
                "approval_determined_by_override",
                action_type=action_name,
                auto_execute=auto_execute,
                requires_approval=not auto_execute,
            )
            return not auto_execute

        # Apply level-based defaults
        if action_type in self.DEFAULT_REQUIRE_ACTIONS:
            # DEFAULT_REQUIRE: Approve unless autonomous
            requires_approval = settings.level != ApprovalLevel.AUTONOMOUS
        else:
            # AUTO_EXECUTE: Auto-execute unless conservative
            requires_approval = settings.level == ApprovalLevel.CONSERVATIVE

        logger.debug(
            "approval_determined_by_level",
            action_type=action_name,
            level=settings.level.value,
            requires_approval=requires_approval,
        )

        return requires_approval

    async def create_approval_request(
        self,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        action_type: ActionType,
        action_data: dict[str, Any],
        requested_by_agent: str,
        context: dict[str, Any] | None = None,
        expires_at: datetime | None = None,
    ) -> uuid.UUID:
        """Create a new approval request.

        Args:
            workspace_id: Workspace where action will be performed.
            user_id: User who triggered the AI action.
            action_type: Type of action requiring approval.
            action_data: Action-specific parameters and context.
            requested_by_agent: Name of the AI agent requesting approval.
            context: Optional context for the reviewer.
            expires_at: Optional custom expiration time.

        Returns:
            Created approval request ID.

        Raises:
            ValueError: If action_data is empty or action_type is invalid.

        Example:
            >>> request_id = await service.create_approval_request(
            ...     workspace_id=workspace_id,
            ...     user_id=user_id,
            ...     action_type=ActionType.DELETE_ISSUE,
            ...     action_data={"issue_id": issue_id, "reason": "Duplicate"},
            ...     requested_by_agent="DuplicateDetectorAgent",
            ... )
        """
        if not action_data:
            raise ValueError("action_data cannot be empty")

        # Calculate expiration if not provided
        if expires_at is None:
            expires_at = datetime.now(UTC) + timedelta(hours=self.expiration_hours)

        from pilot_space.infrastructure.database.models.ai_approval_request import (
            AIApprovalRequest,
        )

        # Create database record
        db_request = AIApprovalRequest(
            workspace_id=workspace_id,
            user_id=user_id,
            agent_name=requested_by_agent,
            action_type=action_type.value,
            payload=action_data,
            context=context,
            expires_at=expires_at,
        )

        self.session.add(db_request)
        await self.session.commit()
        await self.session.refresh(db_request)

        logger.info(
            "approval_request_created",
            request_id=str(db_request.id),
            workspace_id=str(workspace_id),
            action_type=action_type.value,
            agent=requested_by_agent,
            expires_at=expires_at.isoformat(),
        )

        return db_request.id

    async def resolve(
        self,
        request_id: uuid.UUID,
        approved: bool,
        resolved_by: uuid.UUID,
        resolution_note: str | None = None,
    ) -> None:
        """Resolve an approval request.

        Args:
            request_id: ID of the request to resolve.
            approved: True to approve, False to reject.
            resolved_by: User ID who is resolving the request.
            resolution_note: Optional note explaining the decision.

        Raises:
            ValueError: If request not found or already resolved.

        Example:
            >>> await service.resolve(
            ...     request_id=request_id,
            ...     approved=False,
            ...     resolved_by=user_id,
            ...     resolution_note="Not a duplicate, different requirements",
            ... )
        """
        resolved_request = await self._repository.resolve(
            request_id,
            approved=approved,
            resolved_by=resolved_by,
            resolution_note=resolution_note,
        )

        if not resolved_request:
            raise ValueError(f"Approval request not found: {request_id}")

        logger.info(
            "approval_request_resolved",
            request_id=str(request_id),
            status=resolved_request.status.value,
            resolved_by=str(resolved_by),
            has_note=resolution_note is not None,
        )

    async def list_requests(
        self,
        workspace_id: uuid.UUID,
        *,
        status: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Any], int]:
        """List approval requests for a workspace with filtering.

        Args:
            workspace_id: Workspace to query.
            status: Optional status filter.
            limit: Maximum results.
            offset: Results to skip.

        Returns:
            Tuple of (requests list, total count).

        Example:
            >>> requests, total = await service.list_requests(workspace_id, status="pending")
            >>> print(f"Found {total} pending requests")
        """
        from pilot_space.infrastructure.database.models.ai_approval_request import (
            ApprovalStatus as DBApprovalStatus,
        )

        status_enum = DBApprovalStatus(status) if status else None
        requests, total = await self._repository.list_by_workspace(
            workspace_id,
            status=status_enum,
            limit=limit,
            offset=offset,
        )

        logger.debug(
            "approval_listed_requests",
            workspace_id=str(workspace_id),
            status_filter=status,
            count=len(requests),
            total=total,
        )

        return list(requests), total

    async def count_pending(self, workspace_id: uuid.UUID) -> int:
        """Count pending approval requests for a workspace.

        Args:
            workspace_id: Workspace to query.

        Returns:
            Number of pending requests.
        """
        return await self._repository.count_pending(workspace_id)

    async def expire_stale_requests(self) -> int:
        """Mark expired requests as EXPIRED.

        Scans all pending requests and expires those past their expiration time.
        Should be called periodically (e.g., hourly background job).

        Returns:
            Number of requests expired.

        Example:
            >>> expired_count = await service.expire_stale_requests()
            >>> print(f"Expired {expired_count} stale requests")
        """
        now = datetime.now(UTC)
        expired_count = await self._repository.expire_stale_requests(now)

        if expired_count > 0:
            logger.info(
                "approval_expired_stale_requests",
                expired_count=expired_count,
                checked_at=now.isoformat(),
            )

        return expired_count

    async def get_request(self, request_id: uuid.UUID) -> Any:
        """Get an approval request by ID.

        Args:
            request_id: Request ID to fetch.

        Returns:
            Approval request if found, None otherwise.
        """
        return await self._repository.get_by_id(request_id)

    def get_action_classification(self, action_type: ActionType) -> str:
        """Get the classification of an action type.

        Args:
            action_type: Action to classify.

        Returns:
            Classification string: "always_require", "default_require", or "auto_execute".

        Example:
            >>> service.get_action_classification(ActionType.DELETE_WORKSPACE)
            'always_require'
            >>> service.get_action_classification(ActionType.SUGGEST_LABELS)
            'auto_execute'
        """
        if action_type in self.ALWAYS_REQUIRE_ACTIONS:
            return "always_require"
        if action_type in self.DEFAULT_REQUIRE_ACTIONS:
            return "default_require"
        return "auto_execute"


__all__ = [
    "ActionType",
    "ApprovalLevel",
    "ApprovalRequest",
    "ApprovalService",
    "ApprovalStatus",
    "ProjectSettings",
]

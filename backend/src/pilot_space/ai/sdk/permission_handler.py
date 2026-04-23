"""Permission handler for AI action approval flow.

Implements DD-003 (Human-in-the-Loop) approval mechanism:
- AUTO_EXECUTE: Non-destructive actions (ghost text, suggestions)
- DEFAULT_REQUIRE_APPROVAL: Entity creation/modification
- CRITICAL_REQUIRE_APPROVAL: Destructive actions (delete, merge)

Reference: docs/DESIGN_DECISIONS.md#dd-003
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import TYPE_CHECKING, Any, ClassVar
from uuid import UUID

from pilot_space.ai.infrastructure.approval import ActionType
from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from pilot_space.ai.infrastructure.approval import ApprovalService

logger = get_logger(__name__)


def filter_denied_tools(
    allowed_tools: list[str],
    denied_tools: Iterable[str],
) -> list[str]:
    """Remove denied tools from the allowed tools list.

    SEC-03: This is the core DENY filter function. It removes any tool
    whose name appears in ``denied_tools`` from the ``allowed_tools`` list.

    Args:
        allowed_tools: The current list of tools the agent is allowed to use.
        denied_tools: An iterable of tool names that should be blocked.

    Returns:
        A new list containing only tools NOT in the denied set.
    """
    denied_set = set(denied_tools)
    return [t for t in allowed_tools if t not in denied_set]


class ActionClassification(StrEnum):
    """DD-003 action classification for approval flow."""

    AUTO_EXECUTE = "auto_execute"
    DEFAULT_REQUIRE_APPROVAL = "default_require"
    CRITICAL_REQUIRE_APPROVAL = "critical_require"


class ApprovalStatus(StrEnum):
    """Approval request status."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


@dataclass
class PermissionResult:
    """Result from permission check.

    Attributes:
        allowed: Whether action is allowed to proceed
        requires_approval: Whether action requires human approval
        approval_id: UUID of approval request if requires_approval=True
        classification: Action classification (AUTO, DEFAULT, CRITICAL)
        reason: Human-readable reason for decision
        expires_at: When approval request expires (24 hours)
    """

    allowed: bool
    requires_approval: bool
    approval_id: UUID | None = None
    classification: ActionClassification = ActionClassification.AUTO_EXECUTE
    reason: str = ""
    expires_at: datetime | None = None

    @classmethod
    def auto_execute(cls, reason: str = "Auto-execute action") -> PermissionResult:
        """Create result for auto-execute action."""
        return cls(
            allowed=True,
            requires_approval=False,
            classification=ActionClassification.AUTO_EXECUTE,
            reason=reason,
        )

    @classmethod
    def requires_approval_result(
        cls,
        approval_id: UUID,
        classification: ActionClassification,
        reason: str,
    ) -> PermissionResult:
        """Create result for action requiring approval."""
        expires_at = datetime.now(UTC) + timedelta(hours=24)
        return cls(
            allowed=False,
            requires_approval=True,
            approval_id=approval_id,
            classification=classification,
            reason=reason,
            expires_at=expires_at,
        )


@dataclass
class ApprovalRequest:
    """Request for human approval.

    Attributes:
        approval_id: Unique identifier
        workspace_id: Workspace UUID for RLS
        user_id: User who initiated action
        agent_name: Agent requesting approval
        action_name: Name of action to approve
        classification: Action classification level
        description: Human-readable description
        proposed_changes: Structured data of changes
        status: Current approval status
        created_at: When request was created
        expires_at: When request expires (24 hours)
        reviewed_by: User who approved/rejected
        reviewed_at: When decision was made
    """

    approval_id: UUID
    workspace_id: UUID
    user_id: UUID
    agent_name: str
    action_name: str
    classification: ActionClassification
    description: str
    proposed_changes: dict[str, Any]
    status: ApprovalStatus = ApprovalStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    expires_at: datetime = field(default_factory=lambda: datetime.now(UTC) + timedelta(hours=24))
    reviewed_by: UUID | None = None
    reviewed_at: datetime | None = None

    @property
    def is_expired(self) -> bool:
        """Check if approval request has expired."""
        return datetime.now(UTC) > self.expires_at

    def approve(self, reviewed_by: UUID) -> None:
        """Mark approval request as approved."""
        self.status = ApprovalStatus.APPROVED
        self.reviewed_by = reviewed_by
        self.reviewed_at = datetime.now(UTC)

    def reject(self, reviewed_by: UUID) -> None:
        """Mark approval request as rejected."""
        self.status = ApprovalStatus.REJECTED
        self.reviewed_by = reviewed_by
        self.reviewed_at = datetime.now(UTC)


class PermissionHandler:
    """Handler for AI action permission and approval flow.

    Responsibilities:
    - Classify actions based on DD-003 rules
    - Create approval requests for non-auto actions
    - Check approval status
    - Enforce 24-hour expiration

    Usage:
        handler = PermissionHandler(approval_service, workspace_settings)
        result = await handler.check_permission(
            workspace_id, user_id, "create_issue", {...}
        )
        if result.requires_approval:
            # Wait for approval
            await handler.wait_for_approval(result.approval_id)
    """

    # DD-003 action classifications
    ACTION_CLASSIFICATIONS: ClassVar[dict[str, ActionClassification]] = {
        # Auto-execute (non-destructive)
        "ghost_text": ActionClassification.AUTO_EXECUTE,
        "margin_annotation": ActionClassification.AUTO_EXECUTE,
        "ai_context": ActionClassification.AUTO_EXECUTE,
        "pr_review": ActionClassification.AUTO_EXECUTE,
        "duplicate_check": ActionClassification.AUTO_EXECUTE,
        "assignee_recommend": ActionClassification.AUTO_EXECUTE,
        "doc_generate": ActionClassification.AUTO_EXECUTE,
        "diagram_generate": ActionClassification.AUTO_EXECUTE,
        "review_pull_request": ActionClassification.AUTO_EXECUTE,
        # Note tools — read (AUTO_EXECUTE)
        "search_notes": ActionClassification.AUTO_EXECUTE,
        "search_note_content": ActionClassification.AUTO_EXECUTE,
        # Note tools — write (REQUIRE_APPROVAL)
        "create_note": ActionClassification.DEFAULT_REQUIRE_APPROVAL,
        "update_note": ActionClassification.DEFAULT_REQUIRE_APPROVAL,
        "insert_block": ActionClassification.DEFAULT_REQUIRE_APPROVAL,
        "remove_block": ActionClassification.DEFAULT_REQUIRE_APPROVAL,
        "remove_content": ActionClassification.DEFAULT_REQUIRE_APPROVAL,
        "replace_content": ActionClassification.DEFAULT_REQUIRE_APPROVAL,
        # Note tools (registered in MCP servers via note_server.py)
        "update_note_block": ActionClassification.DEFAULT_REQUIRE_APPROVAL,
        "enhance_text": ActionClassification.AUTO_EXECUTE,
        "extract_issues": ActionClassification.DEFAULT_REQUIRE_APPROVAL,
        "create_issue_from_note": ActionClassification.DEFAULT_REQUIRE_APPROVAL,
        "link_existing_issues": ActionClassification.DEFAULT_REQUIRE_APPROVAL,
        "write_to_note": ActionClassification.DEFAULT_REQUIRE_APPROVAL,
        # Issue tools — read (AUTO_EXECUTE)
        "get_issue": ActionClassification.AUTO_EXECUTE,
        "search_issues": ActionClassification.AUTO_EXECUTE,
        # Issue tools — write (REQUIRE_APPROVAL)
        "create_issue": ActionClassification.DEFAULT_REQUIRE_APPROVAL,
        "update_issue": ActionClassification.DEFAULT_REQUIRE_APPROVAL,
        "link_issue_to_note": ActionClassification.DEFAULT_REQUIRE_APPROVAL,
        "link_issues": ActionClassification.DEFAULT_REQUIRE_APPROVAL,
        "add_sub_issue": ActionClassification.DEFAULT_REQUIRE_APPROVAL,
        "transition_issue_state": ActionClassification.DEFAULT_REQUIRE_APPROVAL,
        # Issue tools — destructive (CRITICAL)
        "unlink_issue_from_note": ActionClassification.CRITICAL_REQUIRE_APPROVAL,
        "unlink_issues": ActionClassification.CRITICAL_REQUIRE_APPROVAL,
        # Project tools — read (AUTO_EXECUTE)
        "get_project": ActionClassification.AUTO_EXECUTE,
        "search_projects": ActionClassification.AUTO_EXECUTE,
        # Project tools — write (REQUIRE_APPROVAL)
        "create_project": ActionClassification.DEFAULT_REQUIRE_APPROVAL,
        "update_project": ActionClassification.DEFAULT_REQUIRE_APPROVAL,
        "update_project_settings": ActionClassification.DEFAULT_REQUIRE_APPROVAL,
        # Comment tools — read (AUTO_EXECUTE)
        "search_comments": ActionClassification.AUTO_EXECUTE,
        "get_comments": ActionClassification.AUTO_EXECUTE,
        # Comment tools — write (CM-001: create_comment auto, update requires approval)
        "create_comment": ActionClassification.AUTO_EXECUTE,
        "update_comment": ActionClassification.DEFAULT_REQUIRE_APPROVAL,
        # Non-destructive actions (DD-003 auto-execute)
        "add_label": ActionClassification.AUTO_EXECUTE,
        "assign_issue": ActionClassification.AUTO_EXECUTE,
        "improve_writing": ActionClassification.AUTO_EXECUTE,
        "summarize": ActionClassification.AUTO_EXECUTE,
        # Legacy actions
        "create_annotation": ActionClassification.DEFAULT_REQUIRE_APPROVAL,
        "link_commit": ActionClassification.DEFAULT_REQUIRE_APPROVAL,
        "decompose_tasks": ActionClassification.DEFAULT_REQUIRE_APPROVAL,
        # Critical require approval (destructive)
        "delete_issue": ActionClassification.CRITICAL_REQUIRE_APPROVAL,
        "merge_pr": ActionClassification.CRITICAL_REQUIRE_APPROVAL,
        "close_issue": ActionClassification.CRITICAL_REQUIRE_APPROVAL,
        "archive_workspace": ActionClassification.CRITICAL_REQUIRE_APPROVAL,
        # --- Merged from ActionType enum (Phase 80, APPR-03) ---
        # Critical require approval (destructive, non-configurable)
        "delete_workspace": ActionClassification.CRITICAL_REQUIRE_APPROVAL,
        "delete_project": ActionClassification.CRITICAL_REQUIRE_APPROVAL,
        "delete_note": ActionClassification.CRITICAL_REQUIRE_APPROVAL,
        "bulk_delete": ActionClassification.CRITICAL_REQUIRE_APPROVAL,
        # Default require approval (configurable)
        "create_sub_issues": ActionClassification.DEFAULT_REQUIRE_APPROVAL,
        "publish_docs": ActionClassification.DEFAULT_REQUIRE_APPROVAL,
        "post_pr_comments": ActionClassification.DEFAULT_REQUIRE_APPROVAL,
        # Auto-execute (safe operations)
        "suggest_labels": ActionClassification.AUTO_EXECUTE,
        "suggest_priority": ActionClassification.AUTO_EXECUTE,
        "auto_transition_state": ActionClassification.AUTO_EXECUTE,
    }

    def __init__(
        self,
        approval_service: ApprovalService,
        workspace_settings: dict[str, Any] | None = None,
        permission_service: Any | None = None,
    ):
        """Initialize handler.

        Args:
            approval_service: ApprovalService for persistence
            workspace_settings: Optional workspace-specific overrides
            permission_service: Optional PermissionService for workspace-level
                tool permission resolution (DENY/AUTO/ASK). When wired,
                check_input_permissions() will consult it. When None, only the
                in-memory DD-003 classification table is used.
        """
        self._approval_service = approval_service
        self._workspace_settings = workspace_settings or {}
        self._permission_service = permission_service

    def _get_classification(
        self,
        action_name: str,
        workspace_overrides: dict[str, Any] | None = None,
    ) -> ActionClassification:
        """Get classification for action name.

        Args:
            action_name: Name of action to classify
            workspace_overrides: Optional workspace-specific overrides

        Returns:
            ActionClassification enum value
        """
        # Look up default classification
        default = self.ACTION_CLASSIFICATIONS.get(
            action_name,
            ActionClassification.DEFAULT_REQUIRE_APPROVAL,
        )

        # DD-003: CRITICAL actions cannot be downgraded by workspace overrides.
        # Destructive operations (delete_issue, merge_pr, archive_workspace)
        # must always require explicit approval regardless of workspace settings.
        if default == ActionClassification.CRITICAL_REQUIRE_APPROVAL:
            if workspace_overrides and action_name in workspace_overrides:
                requested = ActionClassification(workspace_overrides[action_name])
                if requested != ActionClassification.CRITICAL_REQUIRE_APPROVAL:
                    logger.warning(
                        "Workspace override attempted to downgrade critical action '%s' "
                        "from %s to %s — ignoring override (DD-003)",
                        action_name,
                        default.value,
                        requested.value,
                    )
            return default

        # Non-critical actions may be overridden by workspace settings
        if workspace_overrides and action_name in workspace_overrides:
            return ActionClassification(workspace_overrides[action_name])

        return default

    async def check_permission(
        self,
        workspace_id: UUID,
        user_id: UUID,
        agent_name: str,
        action_name: str,
        description: str,
        proposed_changes: dict[str, Any],
    ) -> PermissionResult:
        """Check if action requires approval.

        Args:
            workspace_id: Workspace UUID
            user_id: User UUID
            agent_name: Agent requesting permission
            action_name: Name of action
            description: Human-readable description
            proposed_changes: Structured data of proposed changes

        Returns:
            PermissionResult with approval decision
        """
        # Get classification for this action
        classification = self._get_classification(
            action_name,
            self._workspace_settings.get("approval_overrides"),
        )

        # AUTO_EXECUTE actions proceed immediately
        if classification == ActionClassification.AUTO_EXECUTE:
            return PermissionResult.auto_execute(
                reason=f"Action '{action_name}' is classified as auto-execute"
            )

        # Create approval request via ApprovalService
        # Map action_name to ActionType (use action_name directly if it matches)
        try:
            action_type = ActionType(action_name)
        except ValueError:
            # Fallback: if action_name doesn't match ActionType enum,
            # use a generic type based on classification
            logger.warning(
                "Action '%s' not in ActionType enum, using fallback (classification=%s)",
                action_name,
                classification.value,
            )
            if classification == ActionClassification.CRITICAL_REQUIRE_APPROVAL:
                action_type = ActionType.DELETE_ISSUE  # Generic critical action
            else:
                action_type = ActionType.CREATE_SUB_ISSUES  # Generic default action

        # Create approval request
        approval_id = await self._approval_service.create_approval_request(
            workspace_id=workspace_id,
            user_id=user_id,
            action_type=action_type,
            action_data={
                "action_name": action_name,
                "description": description,
                "proposed_changes": proposed_changes,
            },
            requested_by_agent=agent_name,
            context={"classification": classification.value},
        )

        return PermissionResult.requires_approval_result(
            approval_id=approval_id,
            classification=classification,
            reason=f"Action '{action_name}' requires {classification.value} approval",
        )

    async def get_approval_status(
        self,
        approval_id: UUID,
    ) -> ApprovalStatus:
        """Get current approval status.

        Args:
            approval_id: UUID of approval request

        Returns:
            ApprovalStatus (PENDING, APPROVED, REJECTED, EXPIRED)

        Raises:
            ValueError: If approval request not found
        """
        request = await self._approval_service.get_request(approval_id)
        if not request:
            raise ValueError(f"Approval request not found: {approval_id}")

        # Map database status to ApprovalStatus enum
        return ApprovalStatus(request.status.value)

    async def approve_request(
        self,
        approval_id: UUID,
        reviewed_by: UUID,
    ) -> None:
        """Approve an approval request.

        Args:
            approval_id: UUID of approval request to approve
            reviewed_by: UUID of user approving the request

        Raises:
            ValueError: If request not found or already resolved
        """
        await self._approval_service.resolve(
            request_id=approval_id,
            approved=True,
            resolved_by=reviewed_by,
        )

    async def reject_request(
        self,
        approval_id: UUID,
        reviewed_by: UUID,
        reason: str | None = None,
    ) -> None:
        """Reject an approval request.

        Args:
            approval_id: UUID of approval request to reject
            reviewed_by: UUID of user rejecting the request
            reason: Optional reason for rejection

        Raises:
            ValueError: If request not found or already resolved
        """
        await self._approval_service.resolve(
            request_id=approval_id,
            approved=False,
            resolved_by=reviewed_by,
            resolution_note=reason,
        )

    async def check_input_permissions(
        self,
        workspace_id: UUID,
        tool_name: str,
    ) -> ActionClassification:
        """Lightweight permission check -- no side effects, no approval creation.

        SEC-13: Inspired by Claude Code's checkPermissions(input) pattern.
        Returns the effective classification for the given tool in the given
        workspace, considering both the in-memory DD-003 table and the
        granular PermissionService (if wired).

        Use this to:
        - Pre-filter tool lists before presenting to users
        - Show permission indicators in the UI
        - Gate destructive operations before expensive processing

        Args:
            workspace_id: UUID of the workspace to check against.
            tool_name: Name of the tool to check.

        Returns:
            ActionClassification for the tool.

        Raises:
            ForbiddenError: If the tool is DENY-mode in workspace policy
                or if the PermissionService is unavailable (fail-closed).
        """
        default_classification = self._get_classification(
            tool_name,
            self._workspace_settings.get("approval_overrides"),
        )

        if self._permission_service is not None:
            try:
                mode = await self._permission_service.resolve(workspace_id, tool_name)
            except Exception:
                # SEC-03: Fail-closed — if PermissionService is degraded, deny
                # the tool rather than falling back to a potentially permissive
                # default classification. This prevents DENY-mode tools from
                # executing during transient service failures.
                logger.warning(
                    "check_input_permissions: PermissionService.resolve failed "
                    "for workspace=%s tool=%s; FAIL-CLOSED: denying tool",
                    workspace_id,
                    tool_name,
                    exc_info=True,
                )
                from pilot_space.domain.exceptions import ForbiddenError

                raise ForbiddenError(
                    f"Tool {tool_name!r} denied: permission service unavailable",
                ) from None

            # Import ToolPermissionMode lazily to avoid circular imports
            # when PermissionService domain types are in a separate package.
            mode_str = str(mode).lower() if mode is not None else None

            if mode_str == "deny":
                from pilot_space.domain.exceptions import ForbiddenError

                raise ForbiddenError(
                    f"Tool {tool_name!r} denied by workspace policy",
                )
            if mode_str == "auto":
                if default_classification == ActionClassification.CRITICAL_REQUIRE_APPROVAL:
                    return ActionClassification.CRITICAL_REQUIRE_APPROVAL
                return ActionClassification.AUTO_EXECUTE
            if mode_str == "ask":
                if default_classification == ActionClassification.CRITICAL_REQUIRE_APPROVAL:
                    return ActionClassification.CRITICAL_REQUIRE_APPROVAL
                return ActionClassification.DEFAULT_REQUIRE_APPROVAL

        return default_classification

    @staticmethod
    def is_destructive(tool_name: str) -> bool:
        """Check if a tool is classified as destructive (CRITICAL).

        SEC-13: Inspired by Claude Code's isDestructive(input) pattern.
        Pure function -- no DB access, no side effects. Uses the in-memory
        DD-003 classification table only.

        Args:
            tool_name: Name of the tool to check.

        Returns:
            True if the tool requires CRITICAL approval (destructive action).
        """
        classification = PermissionHandler.ACTION_CLASSIFICATIONS.get(
            tool_name,
            ActionClassification.DEFAULT_REQUIRE_APPROVAL,
        )
        return classification == ActionClassification.CRITICAL_REQUIRE_APPROVAL

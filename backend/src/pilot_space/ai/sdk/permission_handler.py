"""Permission handler for AI action approval flow.

Implements DD-003 (Human-in-the-Loop) approval mechanism:
- AUTO_EXECUTE: Non-destructive actions (ghost text, suggestions)
- DEFAULT_REQUIRE_APPROVAL: Entity creation/modification
- CRITICAL_REQUIRE_APPROVAL: Destructive actions (delete, merge)

Reference: docs/DESIGN_DECISIONS.md#dd-003
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import TYPE_CHECKING, Any, ClassVar
from uuid import UUID

from pilot_space.ai.infrastructure.approval import ActionType

if TYPE_CHECKING:
    from pilot_space.ai.infrastructure.approval import ApprovalService

logger = logging.getLogger(__name__)


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
        # Retained tools (6 from note_tools.py, registered in MCP servers)
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
        # Legacy actions
        "create_annotation": ActionClassification.DEFAULT_REQUIRE_APPROVAL,
        "link_commit": ActionClassification.DEFAULT_REQUIRE_APPROVAL,
        "decompose_tasks": ActionClassification.DEFAULT_REQUIRE_APPROVAL,
        # Critical require approval (destructive)
        "delete_issue": ActionClassification.CRITICAL_REQUIRE_APPROVAL,
        "merge_pr": ActionClassification.CRITICAL_REQUIRE_APPROVAL,
        "close_issue": ActionClassification.CRITICAL_REQUIRE_APPROVAL,
    }

    def __init__(
        self,
        approval_service: ApprovalService,
        workspace_settings: dict[str, Any] | None = None,
    ):
        """Initialize handler.

        Args:
            approval_service: ApprovalService for persistence
            workspace_settings: Optional workspace-specific overrides
        """
        self._approval_service = approval_service
        self._workspace_settings = workspace_settings or {}

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
        # Check workspace overrides first
        if workspace_overrides and action_name in workspace_overrides:
            return ActionClassification(workspace_overrides[action_name])

        # Fall back to default classification
        return self.ACTION_CLASSIFICATIONS.get(
            action_name,
            ActionClassification.DEFAULT_REQUIRE_APPROVAL,
        )

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

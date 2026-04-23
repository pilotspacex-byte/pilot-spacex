"""Unified approval bus with asyncio.Event-based wait/resolve.

Replaces the 2s DB polling loop in approval_waiter.py with an in-process
event registry. The bus provides:

- register(id): Create a pending approval entry with an asyncio.Event.
- wait(id, timeout): Await the event, return the decision string.
- resolve(id, decision): Set the decision and fire the event (claim-once).

Claim-once semantics (APPR-02): The first resolve() wins; subsequent
calls for the same approval_id return False without altering the decision.

Also re-exports SSE helpers and ApprovalActionExecutor previously in
approval_waiter.py, keeping backward compatibility while the waiter
module is deprecated.

Reference: docs/DESIGN_DECISIONS.md#DD-003
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, ClassVar
from uuid import UUID

from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Internal pending-approval slot
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class _PendingApproval:
    """In-memory slot for a single pending approval.

    Attributes:
        event: asyncio.Event that waiters block on.
        decision: The resolution string set by resolve(). Defaults to
                  ``"expired"`` so that timeouts produce a safe fallback.
    """

    event: asyncio.Event = field(default_factory=asyncio.Event)
    decision: str = "expired"


# ---------------------------------------------------------------------------
# UnifiedApprovalBus
# ---------------------------------------------------------------------------


class UnifiedApprovalBus:
    """In-process event bus for approval wait/resolve (replaces DB polling).

    Thread-safety note: This bus is designed for single-process asyncio.
    All public methods must be called from the same event loop. The bus
    does NOT synchronize across multiple processes/workers.

    Usage::

        bus = get_approval_bus()
        bus.register(approval_id)

        # In the resolve endpoint (called by frontend):
        bus.resolve(approval_id, "approved")

        # In the SDK hook (blocking until resolved):
        decision = await bus.wait(approval_id, timeout=300.0)
    """

    def __init__(self) -> None:
        self._pending: dict[UUID, _PendingApproval] = {}

    def register(self, approval_id: UUID) -> None:
        """Register a new pending approval.

        Creates an asyncio.Event entry that ``wait()`` will block on.
        If the id is already registered, this is a no-op (idempotent).

        Args:
            approval_id: Unique identifier for the approval request.
        """
        if approval_id in self._pending:
            logger.warning(
                "approval_bus_register_duplicate",
                approval_id=str(approval_id),
            )
            return
        self._pending[approval_id] = _PendingApproval()
        logger.debug(
            "approval_bus_registered",
            approval_id=str(approval_id),
            pending_count=len(self._pending),
        )

    async def wait(self, approval_id: UUID, timeout_seconds: float = 300.0) -> str:
        """Wait for an approval decision.

        Blocks until ``resolve()`` fires the event or the timeout expires.
        Always removes the entry from ``_pending`` in the finally block
        to prevent memory leaks (T-80-03 mitigation).

        Args:
            approval_id: UUID of the approval to wait for.
            timeout_seconds: Maximum seconds to wait before returning ``"expired"``.

        Returns:
            The decision string (``"approved"``, ``"rejected"``, or ``"expired"``).
        """
        pending = self._pending.get(approval_id)
        if pending is None:
            logger.warning(
                "approval_bus_wait_unregistered",
                approval_id=str(approval_id),
            )
            return "expired"

        try:
            await asyncio.wait_for(pending.event.wait(), timeout=timeout_seconds)
        except TimeoutError:
            logger.info(
                "approval_bus_timeout",
                approval_id=str(approval_id),
                timeout_seconds=timeout_seconds,
            )
            return "expired"
        finally:
            self._pending.pop(approval_id, None)

        return pending.decision

    def resolve(self, approval_id: UUID, decision: str) -> bool:
        """Resolve a pending approval with the given decision.

        Claim-once semantics (APPR-02): if the event is already set,
        subsequent calls return ``False`` without modifying the decision.

        Args:
            approval_id: UUID of the approval to resolve.
            decision: The resolution string (``"approved"`` or ``"rejected"``).

        Returns:
            ``True`` if this was the first (winning) resolution,
            ``False`` if the approval was unknown or already resolved.
        """
        pending = self._pending.get(approval_id)
        if pending is None:
            logger.debug(
                "approval_bus_resolve_unknown",
                approval_id=str(approval_id),
                decision=decision,
            )
            return False

        # Claim-once: if the event is already set, reject the second resolve
        if pending.event.is_set():
            logger.warning(
                "approval_bus_resolve_duplicate",
                approval_id=str(approval_id),
                attempted_decision=decision,
                existing_decision=pending.decision,
            )
            return False

        pending.decision = decision
        pending.event.set()
        logger.info(
            "approval_bus_resolved",
            approval_id=str(approval_id),
            decision=decision,
        )
        return True


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_bus: UnifiedApprovalBus | None = None


def get_approval_bus() -> UnifiedApprovalBus:
    """Return the module-level singleton UnifiedApprovalBus.

    Creates the instance on first call (lazy initialization).

    Returns:
        The singleton UnifiedApprovalBus instance.
    """
    global _bus  # noqa: PLW0603
    if _bus is None:
        _bus = UnifiedApprovalBus()
    return _bus


# ---------------------------------------------------------------------------
# SSE helpers (migrated from approval_waiter.py, unchanged)
# ---------------------------------------------------------------------------


def classify_urgency(tool_name: str) -> str:
    """Classify approval urgency based on tool name.

    Destructive operations -> high, content creation -> medium, other -> low.
    Recognises both legacy ``_in_db`` names and MCP bare tool names.
    """
    destructive = {
        "delete_issue_from_db",
        "merge_pull_request",
        "close_pull_request",
        # MCP / canonical action names
        "delete_issue",
        "merge_pr",
        "close_issue",
        "unlink_issue_from_note",
        "unlink_issues",
        "archive_workspace",
    }
    content_creation = {
        "create_issue_in_db",
        "create_subtasks",
        # MCP / canonical action names
        "create_issue",
        "create_note",
        "create_project",
        "extract_issues",
    }
    if tool_name in destructive:
        return "high"
    if tool_name in content_creation:
        return "medium"
    return "low"


def build_affected_entities(tool_name: str, tool_input: dict[str, Any]) -> list[dict[str, str]]:
    """Extract affected entities from tool input for approval UI."""
    entities: list[dict[str, str]] = []
    if "issue_id" in tool_input:
        entities.append(
            {
                "type": "issue",
                "id": str(tool_input["issue_id"]),
                "name": str(tool_input.get("name", tool_input.get("issue_id", ""))),
            }
        )
    if "note_id" in tool_input:
        entities.append(
            {
                "type": "note",
                "id": str(tool_input["note_id"]),
                "name": str(tool_input.get("note_id", "")),
            }
        )
    if "pr_number" in tool_input:
        entities.append(
            {
                "type": "file",
                "id": str(tool_input["pr_number"]),
                "name": f"PR #{tool_input['pr_number']}",
            }
        )
    return entities


def build_approval_sse_event(
    approval_id: UUID,
    tool_name: str,
    tool_input: dict[str, Any],
    reason: str,
) -> str:
    """Build SSE event string for approval_request with all frontend-expected fields."""
    from pilot_space.ai.sdk.hooks import PermissionCheckHook

    urgency = classify_urgency(tool_name)
    expires_at = datetime.now(tz=UTC) + timedelta(hours=24)
    affected_entities = build_affected_entities(tool_name, tool_input)

    action_mapping = PermissionCheckHook.TOOL_ACTION_MAPPING
    action_type = action_mapping.get(tool_name, tool_name)

    data: dict[str, Any] = {
        "requestId": str(approval_id),
        "actionType": action_type,
        "description": reason,
        "consequences": f"This will {action_type.replace('_', ' ')} in the workspace.",
        "affectedEntities": affected_entities,
        "urgency": urgency,
        "proposedContent": tool_input,
        "expiresAt": expires_at.isoformat(),
        "confidenceTag": "DEFAULT",
    }
    return f"event: approval_request\ndata: {json.dumps(data)}\n\n"


# ---------------------------------------------------------------------------
# ApprovalActionExecutor (migrated from approval_waiter.py, unchanged)
# ---------------------------------------------------------------------------


class ApprovalActionExecutor:
    """Dispatches approved actions to domain services (queue-based Path B).

    Maps action_type strings to handler methods that create/update entities
    via repositories. Unknown action types return unsupported status (no exception).
    """

    def __init__(self, session: Any) -> None:
        self._session = session

    async def execute(
        self,
        action_type: str,
        payload: dict[str, Any],
        user_id: UUID,
    ) -> dict[str, Any]:
        """Execute an approved action.

        Args:
            action_type: Action type string (e.g. "create_issue").
            payload: Action payload from the approval request.
            user_id: User who approved the action.

        Returns:
            Dict with execution result or error info.
        """
        handler = self._dispatch_table.get(action_type)
        if handler is None:
            return {
                "status": "unsupported",
                "message": f"Action type '{action_type}' is not supported for queue execution.",
            }

        try:
            return await handler(self, payload, user_id)
        except Exception as e:
            logger.exception("Failed executing action '%s'", action_type)
            return {"status": "error", "action_error": str(e)}

    async def _handle_create_issue(self, payload: dict[str, Any], user_id: UUID) -> dict[str, Any]:
        workspace_id = payload.get("workspace_id")
        name = payload.get("name", payload.get("title", "Untitled"))
        if not workspace_id:
            return {"status": "error", "action_error": "Missing workspace_id in payload"}
        return {"status": "executed", "action_type": "create_issue", "name": name}

    async def _handle_update_issue(self, payload: dict[str, Any], user_id: UUID) -> dict[str, Any]:
        # Payload may be wrapped as {"operation": ..., "payload": {...}} from issue_server.
        inner = payload.get("payload", payload)
        issue_id = inner.get("issue_id")
        if not issue_id:
            return {"status": "error", "action_error": "Missing issue_id in payload"}

        from pilot_space.infrastructure.database.repositories.issue_repository import (
            IssueRepository,
        )

        repo = IssueRepository(self._session)
        issue = await repo.get_by_id(UUID(str(issue_id)))
        if not issue:
            return {"status": "error", "action_error": f"Issue {issue_id} not found"}

        updated_fields: list[str] = []
        for field_name in ("name", "description", "priority", "assignee_id", "estimate_points"):
            if field_name in inner:
                setattr(issue, field_name, inner[field_name])
                updated_fields.append(field_name)
        for date_field in ("start_date", "target_date"):
            if date_field in inner:
                setattr(issue, date_field, inner[date_field])
                updated_fields.append(date_field)

        if not updated_fields:
            return {
                "status": "skipped",
                "action_type": "update_issue",
                "reason": "No fields to update",
            }

        await repo.update(issue)
        await self._session.commit()
        return {
            "status": "executed",
            "action_type": "update_issue",
            "issue_id": str(issue_id),
            "updated_fields": updated_fields,
        }

    async def _handle_transition_issue_state(
        self, payload: dict[str, Any], user_id: UUID
    ) -> dict[str, Any]:
        issue_id = payload.get("issue_id")
        new_state = payload.get("new_state")
        if not issue_id or not new_state:
            return {"status": "error", "action_error": "Missing issue_id or new_state"}
        return {
            "status": "executed",
            "action_type": "transition_issue_state",
            "issue_id": str(issue_id),
            "new_state": new_state,
        }

    _dispatch_table: ClassVar[dict[str, Any]] = {
        "create_issue": _handle_create_issue,
        "update_issue": _handle_update_issue,
        "transition_issue_state": _handle_transition_issue_state,
    }


__all__ = [
    "ApprovalActionExecutor",
    "UnifiedApprovalBus",
    "build_affected_entities",
    "build_approval_sse_event",
    "classify_urgency",
    "get_approval_bus",
]

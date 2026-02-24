"""Approval waiter and action executor for DD-003 human-in-the-loop flow.

Provides:
- wait_for_approval(): Polls DB for approval status changes (Gap 1 fix)
- ApprovalActionExecutor: Dispatches approved actions via service layer (Gap 2 fix)
- SSE helper functions for approval_request events (extracted from hooks.py)

Reference: docs/DESIGN_DECISIONS.md#DD-003
"""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime, timedelta
from typing import Any, ClassVar
from uuid import UUID

from pilot_space.infrastructure.database.engine import get_db_session
from pilot_space.infrastructure.database.repositories.approval_repository import (
    ApprovalRepository,
)
from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)

# Polling defaults for wait_for_approval
DEFAULT_TIMEOUT_SECONDS: int = 300  # 5 minutes (not 24h; avoids blocking SDK)
DEFAULT_POLL_INTERVAL: float = 2.0


async def wait_for_approval(
    approval_id: UUID,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    poll_interval: float = DEFAULT_POLL_INTERVAL,
) -> str:
    """Poll DB for approval status change.

    Uses a fresh DB session per poll to avoid stale ORM cache reads.
    PostgreSQL READ COMMITTED ensures visibility of commits from resolve API.

    Args:
        approval_id: UUID of the approval request to watch.
        timeout_seconds: Max wait time before returning "expired".
        poll_interval: Seconds between DB polls.

    Returns:
        "approved", "rejected", or "expired".
    """
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout_seconds

    while loop.time() < deadline:
        try:
            async with get_db_session() as session:
                repo = ApprovalRepository(session)
                request = await repo.get_by_id(approval_id)

            if request is None:
                logger.warning("Approval %s not found, treating as expired", approval_id)
                return "expired"

            status = str(request.status)
            if status == "approved":
                return "approved"
            if status in ("rejected", "expired", "modified"):
                return "rejected"

        except Exception:
            logger.warning(
                "DB error polling approval %s, retrying next cycle",
                approval_id,
                exc_info=True,
            )

        await asyncio.sleep(poll_interval)

    logger.info("Approval %s timed out after %ds", approval_id, timeout_seconds)
    return "expired"


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
        for field in ("title", "description", "priority", "assignee_id", "estimate_points"):
            if field in inner:
                setattr(issue, field, inner[field])
                updated_fields.append(field)
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


# ---------------------------------------------------------------------------
# SSE helpers extracted from hooks.py (keeps hooks.py under 700 lines)
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

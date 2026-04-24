"""Issue intent handlers (Phase 89 Plan 03).

Registered tool names:

* ``create_issue`` — creates an Issue via ``CreateIssueService``.
* ``update_issue`` — field updates + label add/remove + version_history append.

Handlers live here because they perform real DB mutations; the audit gate
allow-lists only ``pilot_space/ai/proposals/intent_handlers/``.
"""

from __future__ import annotations

import contextlib
from datetime import (
    UTC,
    date as date_type,
    datetime,
)
from typing import Any
from uuid import UUID

from sqlalchemy import delete, insert, select
from sqlalchemy.orm.attributes import flag_modified

from pilot_space.ai.proposals.intent_executor import register_intent, register_revert
from pilot_space.application.services.proposal_bus import (
    IntentExecutionOutcome,
    ProposalCannotBeRevertedError,
)
from pilot_space.dependencies.auth import get_current_session
from pilot_space.domain.exceptions import NotFoundError
from pilot_space.domain.proposal import ArtifactType
from pilot_space.infrastructure.database.models import Issue
from pilot_space.infrastructure.database.models.issue import IssuePriority


def _safe_uuid(value: Any) -> UUID | None:
    if value is None:
        return None
    if isinstance(value, UUID):
        return value
    try:
        return UUID(str(value))
    except (ValueError, AttributeError, TypeError):
        return None


def _priority_from(value: str | None) -> IssuePriority | None:
    if not value:
        return None
    mapping = {
        "urgent": IssuePriority.URGENT,
        "high": IssuePriority.HIGH,
        "medium": IssuePriority.MEDIUM,
        "low": IssuePriority.LOW,
        "none": IssuePriority.NONE,
    }
    return mapping.get(str(value).lower())


def _snapshot_issue(issue: Issue) -> dict[str, Any]:
    """Pre-mutation snapshot shape used in ``version_history``."""
    return {
        "name": issue.name,
        "description": issue.description,
        "priority": issue.priority.value if issue.priority else None,
        "assignee_id": str(issue.assignee_id) if issue.assignee_id else None,
        "estimate_points": issue.estimate_points,
        "start_date": issue.start_date.isoformat() if issue.start_date else None,
        "target_date": issue.target_date.isoformat() if issue.target_date else None,
    }


def _summarize(args: dict[str, Any]) -> str:
    fields = [k for k in args if k != "issue_id"]
    return f"AI updated: {', '.join(fields)}" if fields else "AI update"


@register_intent("update_issue")
async def execute_update_issue(
    args: dict[str, Any],
    *,
    workspace_id: UUID,
    target_artifact_id: UUID,
) -> IntentExecutionOutcome:
    """Apply field updates + label adds/removes; append version_history."""
    session = get_current_session()

    issue = (
        await session.execute(
            select(Issue).where(
                Issue.id == target_artifact_id,
                Issue.workspace_id == workspace_id,
            )
        )
    ).scalar_one_or_none()
    if issue is None:
        msg = f"Issue {target_artifact_id} not found"
        raise NotFoundError(msg)

    prev_version = issue.version_number or 1
    pre_snapshot = _snapshot_issue(issue)
    changed_fields: list[str] = []

    if "title" in args:
        issue.name = args["title"]
        changed_fields.append("title")
    if "description" in args:
        issue.description = args["description"]
        issue.description_html = None
        changed_fields.append("description")
    if "priority" in args:
        new_p = _priority_from(args["priority"])
        if new_p is not None:
            issue.priority = new_p
            changed_fields.append("priority")
    if "assignee_id" in args:
        with contextlib.suppress(ValueError, TypeError):
            issue.assignee_id = (
                UUID(args["assignee_id"]) if args["assignee_id"] else None
            )
            changed_fields.append("assignee_id")
    if "estimate_points" in args:
        issue.estimate_points = args["estimate_points"]
        changed_fields.append("estimate_points")
    if "start_date" in args:
        with contextlib.suppress(ValueError, TypeError):
            issue.start_date = date_type.fromisoformat(args["start_date"])
            changed_fields.append("start_date")
    if "target_date" in args:
        with contextlib.suppress(ValueError, TypeError):
            issue.target_date = date_type.fromisoformat(args["target_date"])
            changed_fields.append("target_date")

    # Labels
    if "add_label_ids" in args or "remove_label_ids" in args:
        from pilot_space.infrastructure.database.models.issue_label import (
            issue_labels,
        )

        rows = await session.execute(
            select(issue_labels.c.label_id).where(
                issue_labels.c.issue_id == target_artifact_id
            )
        )
        current_label_ids: set[UUID] = {r[0] for r in rows.fetchall()}
        for lid_str in args.get("add_label_ids", []) or []:
            with contextlib.suppress(ValueError, TypeError):
                current_label_ids.add(UUID(str(lid_str)))
        for lid_str in args.get("remove_label_ids", []) or []:
            with contextlib.suppress(ValueError, TypeError):
                current_label_ids.discard(UUID(str(lid_str)))

        await session.execute(
            delete(issue_labels).where(
                issue_labels.c.issue_id == target_artifact_id
            )
        )
        if current_label_ids:
            await session.execute(
                insert(issue_labels),
                [
                    {"issue_id": target_artifact_id, "label_id": lid}
                    for lid in current_label_ids
                ],
            )
        changed_fields.append("labels")

    # Version bump + history append
    new_version = prev_version + 1
    history_entry = {
        "vN": prev_version,
        "by": "ai",
        "at": datetime.now(UTC).isoformat(),
        "summary": _summarize(args),
        "snapshot": pre_snapshot,
    }
    history = list(issue.version_history or [])
    history.append(history_entry)
    issue.version_history = history
    issue.version_number = new_version
    flag_modified(issue, "version_history")

    await session.flush()
    return IntentExecutionOutcome(
        applied_version=new_version,
        lines_changed=len(changed_fields),
    )


@register_intent("create_issue")
async def execute_create_issue(
    args: dict[str, Any],
    *,
    workspace_id: UUID,
    target_artifact_id: UUID,
) -> IntentExecutionOutcome:
    """Create a new Issue via ``CreateIssueService``."""
    from pilot_space.application.services.issue.create_issue_service import (
        CreateIssuePayload,
        CreateIssueService,
    )
    from pilot_space.infrastructure.database.repositories.activity_repository import (
        ActivityRepository,
    )
    from pilot_space.infrastructure.database.repositories.issue_repository import (
        IssueRepository,
    )
    from pilot_space.infrastructure.database.repositories.label_repository import (
        LabelRepository,
    )

    session = get_current_session()
    reporter_id = _safe_uuid(args.get("reporter_id")) or UUID(int=0)
    project_id = _safe_uuid(args.get("project_id"))
    if project_id is None:
        msg = "create_issue: project_id is required"
        raise ValueError(msg)

    target_date: date_type | None = None
    if args.get("target_date"):
        with contextlib.suppress(ValueError):
            target_date = date_type.fromisoformat(args["target_date"])

    try:
        label_ids = [UUID(str(lid)) for lid in (args.get("label_ids") or [])]
    except (ValueError, AttributeError):
        label_ids = []

    payload = CreateIssuePayload(
        workspace_id=workspace_id,
        project_id=project_id,
        reporter_id=reporter_id,
        name=str(args.get("title", "")),
        description=args.get("description"),
        priority=_priority_from(args.get("priority", "medium"))
        or IssuePriority.MEDIUM,
        state_id=_safe_uuid(args.get("state_id")),
        assignee_id=_safe_uuid(args.get("assignee_id")),
        parent_id=_safe_uuid(args.get("parent_id")),
        estimate_points=args.get("estimate_points"),
        target_date=target_date,
        label_ids=label_ids,
        ai_enhanced=True,
        ai_metadata={"source": "proposal_bus", "tool": "create_issue"},
    )
    svc = CreateIssueService(
        session=session,
        issue_repository=IssueRepository(session),
        activity_repository=ActivityRepository(session),
        label_repository=LabelRepository(session),
    )
    result = await svc.execute(payload)
    return IntentExecutionOutcome(
        applied_version=result.issue.version_number or 1,
        lines_changed=None,
    )


# ---------------------------------------------------------------------------
# Revert handler (Phase 89 Plan 05)
# ---------------------------------------------------------------------------


def _restore_from_snapshot(issue: Issue, snapshot: dict[str, Any]) -> None:
    """Restore issue fields from a version_history snapshot, in place.

    The snapshot shape mirrors ``_snapshot_issue`` in this module. Excludes id,
    created_at, workspace_id, FK-bound relationships — only mutable,
    user-facing fields are restored.
    """
    if "name" in snapshot:
        issue.name = snapshot["name"]
    if "description" in snapshot:
        issue.description = snapshot["description"]
        issue.description_html = None
    if "priority" in snapshot and snapshot["priority"] is not None:
        restored_p = _priority_from(snapshot["priority"])
        if restored_p is not None:
            issue.priority = restored_p
    if "assignee_id" in snapshot:
        raw = snapshot["assignee_id"]
        if raw is None:
            issue.assignee_id = None
        else:
            with contextlib.suppress(ValueError, TypeError):
                issue.assignee_id = UUID(str(raw))
    if "estimate_points" in snapshot:
        issue.estimate_points = snapshot["estimate_points"]
    if "start_date" in snapshot and snapshot["start_date"] is not None:
        with contextlib.suppress(ValueError, TypeError):
            issue.start_date = date_type.fromisoformat(str(snapshot["start_date"]))
    if "target_date" in snapshot and snapshot["target_date"] is not None:
        with contextlib.suppress(ValueError, TypeError):
            issue.target_date = date_type.fromisoformat(str(snapshot["target_date"]))


@register_revert(ArtifactType.ISSUE)
async def revert_issue(
    *,
    workspace_id: UUID,
    target_artifact_id: UUID,
) -> IntentExecutionOutcome:
    """Revert an Issue to the most recent prior snapshot.

    Reads ``version_history[-1].snapshot`` (append-only — prior entries are
    never mutated), restores the fields in the snapshot, appends a NEW history
    entry tagged ``by:'user'`` whose ``snapshot`` captures the pre-revert
    state (so a revert can itself be reverted, per plan symmetry).
    """
    session = get_current_session()

    issue = (
        await session.execute(
            select(Issue).where(
                Issue.id == target_artifact_id,
                Issue.workspace_id == workspace_id,
            )
        )
    ).scalar_one_or_none()
    if issue is None:
        msg = f"Issue {target_artifact_id} not found"
        raise NotFoundError(msg)

    history = list(issue.version_history or [])
    if not history:
        raise ProposalCannotBeRevertedError(
            f"Issue {target_artifact_id} has no version history — nothing to "
            "revert to"
        )

    last_entry = history[-1]
    snapshot = last_entry.get("snapshot") or {}
    pre_revert_snapshot = _snapshot_issue(issue)
    prev_version = issue.version_number or 1
    reverting_to_vn = int(last_entry.get("vN", prev_version - 1))

    _restore_from_snapshot(issue, snapshot)

    new_version = prev_version + 1
    new_entry = {
        "vN": prev_version,
        "by": "user",
        "at": datetime.now(UTC).isoformat(),
        "summary": f"Reverted v{prev_version} → v{reverting_to_vn}",
        "snapshot": pre_revert_snapshot,
    }
    history.append(new_entry)
    issue.version_history = history
    issue.version_number = new_version
    flag_modified(issue, "version_history")

    await session.flush()
    return IntentExecutionOutcome(
        applied_version=new_version,
        lines_changed=None,
    )

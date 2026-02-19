"""PM Block — Release notes endpoints.

T-244: Release notes generation from completed issues

Feature 017: Note Versioning / PM Block Engine — Phase 2e
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Path, Query, status
from pydantic import BaseModel

from pilot_space.api.v1.dependencies import WorkspaceRepositoryDep
from pilot_space.dependencies.auth import CurrentUserId, SessionDep
from pilot_space.infrastructure.database.repositories.pm_block_queries_repository import (
    PMBlockQueriesRepository,
)

router = APIRouter(prefix="", tags=["pm-blocks"])


# ── Response Schemas ──────────────────────────────────────────────────────────


class ReleaseEntry(BaseModel):
    issue_id: str
    identifier: str
    name: str
    category: str  # features / bug_fixes / improvements / internal / uncategorized
    confidence: float
    human_edited: bool = False


class ReleaseNotesResponse(BaseModel):
    cycle_id: str
    version_label: str
    entries: list[ReleaseEntry]
    generated_at: str


# ── Heuristic Classifier ──────────────────────────────────────────────────────


def _classify_issue(issue: object) -> tuple[str, float]:
    """Heuristic classification of an issue into release note category.

    Returns (category, confidence). Rule-based fallback for FR-058 graceful degradation.
    """
    issue_type = getattr(issue, "type", None)
    name = (getattr(issue, "name", "") or "").lower()

    if issue_type == "bug" or any(k in name for k in ("fix", "bug", "crash", "error", "broken")):
        return "bug_fixes", 0.85
    if issue_type == "feature" or any(k in name for k in ("add", "new ", "implement", "create")):
        return "features", 0.80
    if issue_type == "improvement" or any(
        k in name for k in ("improve", "enhance", "optimize", "refactor")
    ):
        return "improvements", 0.75
    if any(k in name for k in ("internal", "chore", "migrate", "upgrade", "deps")):
        return "internal", 0.70
    return "uncategorized", 0.25


# ── Release Notes Endpoint (T-244) ───────────────────────────────────────────


@router.get(
    "/workspaces/{workspace_id}/release-notes",
    response_model=ReleaseNotesResponse,
    summary="AI-classified release notes for a cycle",
)
async def get_release_notes(
    workspace_id: Annotated[UUID, Path()],
    session: SessionDep,
    workspace_repo: WorkspaceRepositoryDep,
    cycle_id: Annotated[str, Query(description="Cycle UUID")],
    current_user_id: CurrentUserId,
) -> ReleaseNotesResponse:
    """Return completed issues classified into release note categories (FR-054)."""
    cycle_uuid = UUID(cycle_id)
    repo = PMBlockQueriesRepository(session)

    cycle = await repo.get_cycle(cycle_uuid, workspace_id)
    if not cycle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cycle not found")

    issues = await repo.get_cycle_issues_with_state(cycle_uuid, workspace_id)

    entries: list[ReleaseEntry] = []
    for issue in issues:
        state_group = (
            issue.state.group.value if issue.state and hasattr(issue.state.group, "value") else ""
        )
        if state_group not in ("completed",):
            continue

        category, confidence = _classify_issue(issue)
        entries.append(
            ReleaseEntry(
                issue_id=str(issue.id),
                identifier=issue.identifier,
                name=issue.name,
                category=category,
                confidence=confidence,
            )
        )

    version_label = getattr(cycle, "name", cycle_id)

    return ReleaseNotesResponse(
        cycle_id=cycle_id,
        version_label=version_label,
        entries=entries,
        generated_at=datetime.now(UTC).isoformat(),
    )

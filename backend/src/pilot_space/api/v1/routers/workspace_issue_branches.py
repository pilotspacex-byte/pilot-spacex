"""Workspace-scoped issue branch name endpoint.

GET /{workspace_id}/issues/{issue_id}/branch-name

Placed in a dedicated router (not workspace_issues.py, which is at the 700-line limit)
and registered under the /api/v1/workspaces prefix so the URL matches the frontend
contract: GET /api/v1/workspaces/{workspace_id}/issues/{issue_id}/branch-name.
"""

from __future__ import annotations

import re
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Path, status

from pilot_space.api.v1.dependencies import WorkspaceRepositoryDep
from pilot_space.api.v1.schemas.integration import BranchNameResponse
from pilot_space.dependencies import SyncedUserId
from pilot_space.dependencies.auth import SessionDep
from pilot_space.infrastructure.database.models.workspace import Workspace
from pilot_space.infrastructure.database.repositories import IssueRepository
from pilot_space.infrastructure.database.rls import set_rls_context
from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["workspace-issues"])

WorkspaceIdOrSlug = Annotated[str, Path(description="Workspace ID or slug")]
IssueIdPath = Annotated[UUID, Path(description="Issue ID")]

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def _is_valid_uuid(value: str) -> bool:
    return bool(_UUID_RE.match(value))


async def _resolve_workspace(
    workspace_id_or_slug: str,
    workspace_repo: WorkspaceRepositoryDep,
) -> Workspace:
    """Resolve workspace by UUID or slug (scalar columns only)."""
    if _is_valid_uuid(workspace_id_or_slug):
        workspace = await workspace_repo.get_by_id_scalar(UUID(workspace_id_or_slug))
    else:
        workspace = await workspace_repo.get_by_slug_scalar(workspace_id_or_slug)

    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )
    return workspace


def _slugify(text: str) -> str:
    """Convert text to a URL-safe slug (lowercase, hyphens, no leading/trailing hyphens)."""
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


@router.get(
    "/{workspace_id}/issues/{issue_id}/branch-name",
    response_model=BranchNameResponse,
    summary="Get branch name suggestion for issue",
)
async def get_issue_branch_name(
    session: SessionDep,
    workspace_id: WorkspaceIdOrSlug,
    issue_id: IssueIdPath,
    current_user_id: SyncedUserId,
    workspace_repo: WorkspaceRepositoryDep,
) -> BranchNameResponse:
    """Return a suggested branch name derived from the issue identifier and title.

    Enforces workspace membership via RLS before querying the issue.
    """
    workspace = await _resolve_workspace(workspace_id, workspace_repo)
    await set_rls_context(session, current_user_id, workspace.id)

    issue_repo = IssueRepository(session)
    issue = await issue_repo.get_by_id_with_relations(issue_id)
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")
    if issue.workspace_id != workspace.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")

    issue_name = issue.name or "untitled"
    name_slug = _slugify(issue_name)

    prefix = "ps"
    if issue.project and issue.project.identifier:
        prefix = issue.project.identifier.lower()

    base = f"feat/{prefix}-{issue.sequence_id}-{name_slug}"
    branch_name = base[:50]
    git_command = f"git checkout -b {branch_name}"

    return BranchNameResponse(
        branch_name=branch_name,
        git_command=git_command,
        format=f"feat/{prefix}-{{sequenceId}}-{{slugified-name}}",
    )


__all__ = ["router"]

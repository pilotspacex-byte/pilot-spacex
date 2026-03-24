"""Create GitHub branch service.

Wires GitHub branch creation to an IntegrationLink record.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import httpx

from pilot_space.domain.exceptions import AppError, ConflictError
from pilot_space.infrastructure.database.models import (
    Activity,
    ActivityType,
    IntegrationLink,
    IntegrationLinkType,
)
from pilot_space.infrastructure.encryption import decrypt_api_key
from pilot_space.infrastructure.logging import get_logger

_GITHUB_API_URL = "https://api.github.com"
_GITHUB_HEADERS: dict[str, str] = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}


async def _create_github_branch(
    token: str, owner: str, repo: str, branch_name: str, base_branch: str
) -> None:
    """Fetch base SHA and create a new git branch via the GitHub API."""
    headers = {**_GITHUB_HEADERS, "Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(base_url=_GITHUB_API_URL, headers=headers, timeout=30.0) as http:
        resp = await http.get(f"/repos/{owner}/{repo}/git/refs/heads/{base_branch}")
        resp.raise_for_status()
        ref_data: Any = resp.json()
        sha: str = (ref_data[0] if isinstance(ref_data, list) else ref_data)["object"]["sha"]
        resp = await http.post(
            f"/repos/{owner}/{repo}/git/refs",
            json={"ref": f"refs/heads/{branch_name}", "sha": sha},
        )
        resp.raise_for_status()


if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from pilot_space.infrastructure.database.repositories import (
        ActivityRepository,
        IntegrationLinkRepository,
        IntegrationRepository,
        IssueRepository,
    )

logger = get_logger(__name__)


class CreateBranchError(AppError):
    """Raised when branch creation fails."""

    http_status: int = 400
    error_code: str = "create_branch_error"


@dataclass
class CreateBranchPayload:
    """Payload for creating a GitHub branch and linking it to an issue.

    Attributes:
        workspace_id: Workspace UUID.
        issue_id: Issue UUID to link to.
        integration_id: GitHub Integration UUID.
        repository: Repository full name (owner/repo).
        branch_name: Branch name to create (e.g. 'feat/ps-42-fix-login').
        base_branch: Branch to branch from (default: 'main').
        actor_id: User performing the action.
    """

    workspace_id: UUID
    issue_id: UUID
    integration_id: UUID
    repository: str
    branch_name: str
    base_branch: str = "main"
    actor_id: UUID | None = None


@dataclass
class CreateBranchResult:
    """Result from branch creation.

    Attributes:
        link: Created IntegrationLink record.
        created: True if branch was newly created, False if link already existed.
        branch_name: Name of the branch.
    """

    link: IntegrationLink
    created: bool = True
    branch_name: str = ""


class CreateBranchService:
    """Service to create a GitHub branch and link it to an issue.

    Handles:
    - Integration validation
    - GitHub branch creation via API
    - IntegrationLink record creation (idempotent)
    - Activity recording
    """

    def __init__(
        self,
        session: AsyncSession,
        integration_repo: IntegrationRepository,
        integration_link_repo: IntegrationLinkRepository,
        issue_repo: IssueRepository,
        activity_repo: ActivityRepository,
    ) -> None:
        """Initialize service.

        Args:
            session: Async database session.
            integration_repo: Integration repository.
            integration_link_repo: IntegrationLink repository.
            issue_repo: Issue repository.
            activity_repo: Activity repository.
        """
        self._session = session
        self._integration_repo = integration_repo
        self._link_repo = integration_link_repo
        self._issue_repo = issue_repo
        self._activity_repo = activity_repo

    async def execute(self, payload: CreateBranchPayload) -> CreateBranchResult:
        """Create a GitHub branch and link it to an issue.

        Args:
            payload: Branch creation parameters.

        Returns:
            CreateBranchResult with the link record and branch name.

        Raises:
            CreateBranchError: If integration/issue not found or not active.
            ValueError: If an identical branch link already exists for the issue.
        """
        # 1. Validate integration
        integration = await self._integration_repo.get_by_id(payload.integration_id)
        if not integration:
            raise CreateBranchError("Integration not found")
        if not integration.is_active:
            raise CreateBranchError("Integration is not active")

        # 2. Validate issue
        issue = await self._issue_repo.get_by_id_with_relations(payload.issue_id)
        if not issue:
            raise CreateBranchError("Issue not found")

        # 3. Check for existing branch link (same branch name on same integration)
        existing_links = await self._link_repo.get_by_issue(
            payload.issue_id,
            link_type=IntegrationLinkType.BRANCH,
        )
        for existing in existing_links:
            if (
                existing.external_id == payload.branch_name
                and existing.integration_id == payload.integration_id
            ):
                raise ConflictError(
                    f"Branch '{payload.branch_name}' is already linked to this issue"
                )

        # 4. Create branch via GitHub API
        access_token = decrypt_api_key(integration.access_token)
        owner, repo = payload.repository.split("/", 1)
        try:
            await _create_github_branch(
                access_token, owner, repo, payload.branch_name, payload.base_branch
            )
        except Exception as e:
            logger.exception(
                "GitHub API error creating branch",
                extra={"repository": payload.repository, "branch": payload.branch_name},
            )
            raise CreateBranchError("Failed to create branch via GitHub API") from e

        # 5. Create IntegrationLink record
        external_url = f"https://github.com/{payload.repository}/tree/{payload.branch_name}"
        link = IntegrationLink(
            workspace_id=payload.workspace_id,
            integration_id=payload.integration_id,
            issue_id=payload.issue_id,
            link_type=IntegrationLinkType.BRANCH,
            external_id=payload.branch_name,
            external_url=external_url,
            title=payload.branch_name,
            author_name=None,
            author_avatar_url=None,
            link_metadata={
                "name": payload.branch_name,
                "repository": payload.repository,
                "base_branch": payload.base_branch,
            },
        )

        link, created = await self._link_repo.create_if_not_exists(link)

        # 6. Record activity if newly created and actor is known
        if created and payload.actor_id is not None:
            activity = Activity(
                workspace_id=payload.workspace_id,
                issue_id=payload.issue_id,
                actor_id=payload.actor_id,
                activity_type=ActivityType.LINKED_TO_NOTE,
                field="integration_link",
                new_value=payload.branch_name,
                activity_metadata={
                    "link_type": "branch",
                    "repository": payload.repository,
                    "branch_name": payload.branch_name,
                    "base_branch": payload.base_branch,
                },
            )
            await self._activity_repo.create(activity)

        logger.info(
            "Created branch and linked to issue",
            extra={
                "issue_id": str(payload.issue_id),
                "branch_name": payload.branch_name,
                "repository": payload.repository,
                "created": created,
            },
        )

        return CreateBranchResult(
            link=link,
            created=created,
            branch_name=payload.branch_name,
        )


__all__ = [
    "CreateBranchError",
    "CreateBranchPayload",
    "CreateBranchResult",
    "CreateBranchService",
]

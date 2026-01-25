"""Get Issue service for single issue retrieval.

T127: Create GetIssueService with eager loading.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uuid import UUID

    from pilot_space.infrastructure.database.models import Issue
    from pilot_space.infrastructure.database.repositories import IssueRepository

logger = logging.getLogger(__name__)


@dataclass
class GetIssueResult:
    """Result from getting an issue."""

    issue: Issue | None
    found: bool


class GetIssueService:
    """Service for retrieving single issues.

    Supports retrieval by:
    - UUID
    - Human-readable identifier (e.g., PILOT-123)
    """

    def __init__(
        self,
        issue_repository: IssueRepository,
    ) -> None:
        """Initialize service.

        Args:
            issue_repository: Issue repository.
        """
        self._issue_repo = issue_repository

    async def execute(
        self,
        issue_id: UUID,
        *,
        include_deleted: bool = False,
    ) -> GetIssueResult:
        """Get an issue by ID.

        Args:
            issue_id: Issue UUID.
            include_deleted: Whether to include soft-deleted issues.

        Returns:
            GetIssueResult with issue if found.
        """
        logger.debug(
            "Getting issue by ID",
            extra={"issue_id": str(issue_id)},
        )

        issue = await self._issue_repo.get_by_id_with_relations(
            issue_id,
            include_deleted=include_deleted,
        )

        return GetIssueResult(
            issue=issue,
            found=issue is not None,
        )

    async def execute_by_identifier(
        self,
        workspace_id: UUID,
        identifier: str,
    ) -> GetIssueResult:
        """Get an issue by human-readable identifier.

        Args:
            workspace_id: Workspace UUID.
            identifier: Issue identifier (e.g., "PILOT-123").

        Returns:
            GetIssueResult with issue if found.

        Raises:
            ValueError: If identifier format is invalid.
        """
        logger.debug(
            "Getting issue by identifier",
            extra={"workspace_id": str(workspace_id), "identifier": identifier},
        )

        # Parse identifier
        parts = identifier.rsplit("-", 1)
        if len(parts) != 2:
            raise ValueError(f"Invalid issue identifier format: {identifier}")

        project_identifier = parts[0]
        try:
            sequence_id = int(parts[1])
        except ValueError as err:
            raise ValueError(f"Invalid issue sequence number: {parts[1]}") from err

        issue = await self._issue_repo.get_by_identifier(
            workspace_id,
            project_identifier,
            sequence_id,
        )

        return GetIssueResult(
            issue=issue,
            found=issue is not None,
        )


__all__ = ["GetIssueResult", "GetIssueService"]

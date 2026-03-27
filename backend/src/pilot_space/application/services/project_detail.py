"""Project detail service for aggregation and business validation.

Extracts workspace access checks, project-to-response conversion,
and KG population logic from the projects router.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from pilot_space.domain.exceptions import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
    ValidationError,
)
from pilot_space.infrastructure.database.models.project import Project
from pilot_space.infrastructure.database.repositories import (
    ProjectRepository,
    WorkspaceRepository,
)
from pilot_space.infrastructure.logging import get_logger
from pilot_space.infrastructure.queue.models import QueueName

logger = get_logger(__name__)


class ProjectDetailService:
    """Service for project detail aggregation and business operations.

    Handles workspace access checks, project creation/update validation,
    issue count aggregation, and KG population enqueuing.
    """

    def __init__(
        self,
        session: AsyncSession,
        project_repository: ProjectRepository,
        workspace_repository: WorkspaceRepository,
    ) -> None:
        self._session = session
        self._project_repo = project_repository
        self._workspace_repo = workspace_repository

    async def check_workspace_access(
        self,
        workspace_id: UUID,
        user_id: UUID,
        *,
        require_admin: bool = False,
    ) -> None:
        """Verify user has access to workspace.

        Args:
            workspace_id: Workspace identifier.
            user_id: User identifier.
            require_admin: Whether admin role is required.

        Raises:
            NotFoundError: If workspace not found.
            ForbiddenError: If user is not a member or lacks admin role.
        """
        workspace = await self._workspace_repo.get_by_id(workspace_id)
        if not workspace:
            raise NotFoundError("Workspace not found")

        member = next(
            (m for m in (workspace.members or []) if m.user_id == user_id),
            None,
        )
        if not member:
            raise ForbiddenError("Not a member of this workspace")

        if require_admin and not member.is_admin:
            raise ForbiddenError("Admin role required")

    async def get_issue_counts(self, project_id: UUID) -> tuple[int, int]:
        """Get total and open issue counts for a project.

        Args:
            project_id: Project identifier.

        Returns:
            Tuple of (total_count, open_count).
        """
        return await self._project_repo.get_issue_counts(project_id)

    async def get_batch_issue_counts(self, project_ids: list[UUID]) -> dict[UUID, tuple[int, int]]:
        """Get issue counts for multiple projects.

        Args:
            project_ids: List of project identifiers.

        Returns:
            Dict mapping project_id to (total, open) counts.
        """
        return await self._project_repo.get_batch_issue_counts(project_ids)

    async def validate_lead_membership(
        self,
        workspace_id: UUID,
        lead_id: UUID,
    ) -> None:
        """Validate that the lead is a workspace member.

        Args:
            workspace_id: Workspace identifier.
            lead_id: Proposed lead user identifier.

        Raises:
            ValidationError: If lead is not a workspace member.
        """
        workspace = await self._workspace_repo.get_by_id(workspace_id)
        is_member = (
            any(m.user_id == lead_id for m in (workspace.members or [])) if workspace else False
        )
        if not is_member:
            raise ValidationError("lead_id must belong to a workspace member")

    async def validate_identifier_unique(
        self,
        workspace_id: UUID,
        identifier: str,
    ) -> None:
        """Validate that a project identifier is unique within the workspace.

        Args:
            workspace_id: Workspace identifier.
            identifier: Project identifier to check.

        Raises:
            ConflictError: If identifier already exists.
        """
        existing = await self._project_repo.find_by(
            workspace_id=workspace_id,
            identifier=identifier,
        )
        if existing:
            raise ConflictError(f"Project with identifier '{identifier}' already exists")

    async def get_project_or_raise(self, project_id: UUID) -> Project:
        """Get a project by ID or raise NotFoundError.

        Args:
            project_id: Project identifier.

        Returns:
            The project entity.

        Raises:
            NotFoundError: If project not found.
        """
        project = await self._project_repo.get_by_id(project_id)
        if not project:
            raise NotFoundError("Project not found")
        return project

    async def enqueue_kg_populate(self, project: Project) -> None:
        """Enqueue a KG populate job for a project (non-fatal).

        Args:
            project: The project entity to populate KG for.
        """
        try:
            from pilot_space.container import get_container

            queue = get_container().queue_client()
            if queue is None:
                return

            await queue.enqueue(
                QueueName.AI_NORMAL,
                {
                    "task_type": "kg_populate",
                    "entity_type": "project",
                    "entity_id": str(project.id),
                    "workspace_id": str(project.workspace_id),
                    "project_id": str(project.id),
                },
            )
        except Exception as exc:
            logger.warning("ProjectDetailService: failed to enqueue kg_populate: %s", exc)


__all__ = ["ProjectDetailService"]

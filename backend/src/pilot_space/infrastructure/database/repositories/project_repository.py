"""Project repository for project data access.

Provides specialized methods for project-related queries.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import func, or_, select
from sqlalchemy.orm import joinedload

from pilot_space.infrastructure.database.models.issue import Issue
from pilot_space.infrastructure.database.models.project import Project
from pilot_space.infrastructure.database.models.state import DEFAULT_STATES, State, StateGroup
from pilot_space.infrastructure.database.repositories.base import BaseRepository

if TYPE_CHECKING:
    from collections.abc import Sequence
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession


class ProjectRepository(BaseRepository[Project]):
    """Repository for Project entities.

    Extends BaseRepository with project-specific queries.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize ProjectRepository.

        Args:
            session: The async database session.
        """
        super().__init__(session, Project)

    async def get_by_identifier(
        self,
        workspace_id: UUID,
        identifier: str,
        *,
        include_deleted: bool = False,
    ) -> Project | None:
        """Get project by workspace and identifier.

        Args:
            workspace_id: The workspace ID.
            identifier: The project's short identifier (e.g., "PILOT").
            include_deleted: Whether to include soft-deleted projects.

        Returns:
            The project if found, None otherwise.
        """
        query = select(Project).where(
            Project.workspace_id == workspace_id,
            Project.identifier == identifier,
        )
        if not include_deleted:
            query = query.where(Project.is_deleted == False)  # noqa: E712
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def identifier_exists(
        self,
        workspace_id: UUID,
        identifier: str,
        *,
        exclude_id: UUID | None = None,
    ) -> bool:
        """Check if project identifier exists in workspace.

        Args:
            workspace_id: The workspace ID.
            identifier: The identifier to check.
            exclude_id: Project ID to exclude from check (for updates).

        Returns:
            True if identifier exists, False otherwise.
        """
        query = select(Project).where(
            Project.workspace_id == workspace_id,
            Project.identifier == identifier,
            Project.is_deleted == False,  # noqa: E712
        )
        if exclude_id:
            query = query.where(Project.id != exclude_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none() is not None

    async def get_workspace_projects(
        self,
        workspace_id: UUID,
        *,
        include_deleted: bool = False,
    ) -> Sequence[Project]:
        """Get all projects in a workspace.

        Args:
            workspace_id: The workspace ID.
            include_deleted: Whether to include soft-deleted projects.

        Returns:
            List of projects in the workspace.
        """
        return await self.find_by(workspace_id=workspace_id, include_deleted=include_deleted)

    async def get_with_states(
        self,
        project_id: UUID,
        *,
        include_deleted: bool = False,
    ) -> Project | None:
        """Get project with states eagerly loaded.

        Args:
            project_id: The project ID.
            include_deleted: Whether to include soft-deleted project.

        Returns:
            Project with states loaded, or None if not found.
        """
        query = select(Project).options(joinedload(Project.states)).where(Project.id == project_id)
        if not include_deleted:
            query = query.where(Project.is_deleted == False)  # noqa: E712
        result = await self.session.execute(query)
        return result.unique().scalar_one_or_none()

    async def get_with_labels(
        self,
        project_id: UUID,
        *,
        include_deleted: bool = False,
    ) -> Project | None:
        """Get project with labels eagerly loaded.

        Args:
            project_id: The project ID.
            include_deleted: Whether to include soft-deleted project.

        Returns:
            Project with labels loaded, or None if not found.
        """
        query = select(Project).options(joinedload(Project.labels)).where(Project.id == project_id)
        if not include_deleted:
            query = query.where(Project.is_deleted == False)  # noqa: E712
        result = await self.session.execute(query)
        return result.unique().scalar_one_or_none()

    async def get_project_count(
        self,
        workspace_id: UUID,
    ) -> int:
        """Get count of active projects in workspace.

        Args:
            workspace_id: The workspace ID.

        Returns:
            Count of active projects.
        """
        query = (
            select(func.count())
            .select_from(Project)
            .where(
                Project.workspace_id == workspace_id,
                Project.is_deleted == False,  # noqa: E712
            )
        )
        result = await self.session.execute(query)
        return result.scalar() or 0

    async def search_projects(
        self,
        workspace_id: UUID,
        search_term: str,
        *,
        limit: int = 20,
        include_deleted: bool = False,
    ) -> Sequence[Project]:
        """Search projects by name or identifier in workspace.

        Args:
            workspace_id: The workspace ID.
            search_term: Text to search for.
            limit: Maximum results to return.
            include_deleted: Whether to include soft-deleted projects.

        Returns:
            List of matching projects.
        """
        query = select(Project).where(Project.workspace_id == workspace_id)
        if not include_deleted:
            query = query.where(Project.is_deleted == False)  # noqa: E712

        # Escape ILIKE wildcards to prevent injection
        safe_term = search_term.replace("%", r"\%").replace("_", r"\_")
        search_pattern = f"%{safe_term}%"
        query = query.where(
            or_(
                Project.name.ilike(search_pattern),
                Project.identifier.ilike(search_pattern),
            )
        )
        query = query.order_by(Project.created_at.desc()).limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def create_with_default_states(
        self,
        project: Project,
    ) -> Project:
        """Create project and initialize default states.

        Per FR-003: States are created when project is created.

        Args:
            project: The project to create.

        Returns:
            Created project with default states.
        """
        # Create the project first
        self.session.add(project)
        await self.session.flush()
        await self.session.refresh(project)

        # Create default states for this project
        for state_data in DEFAULT_STATES:
            state = State(
                workspace_id=project.workspace_id,
                project_id=project.id,
                name=str(state_data["name"]),
                color=str(state_data["color"]),
                group=state_data["group"],  # type: ignore[arg-type]
                sequence=int(state_data["sequence"]),
            )
            self.session.add(state)

        await self.session.flush()
        await self.session.refresh(project)
        return project

    async def get_issue_counts(
        self,
        project_id: UUID,
    ) -> tuple[int, int]:
        """Get total and open issue counts for a project.

        Args:
            project_id: The project ID.

        Returns:
            Tuple of (total_count, open_count).
        """
        total_query = (
            select(func.count())
            .select_from(Issue)
            .where(
                Issue.project_id == project_id,
                Issue.is_deleted == False,  # noqa: E712
            )
        )
        open_query = (
            select(func.count())
            .select_from(Issue)
            .join(State, Issue.state_id == State.id)
            .where(
                Issue.project_id == project_id,
                Issue.is_deleted == False,  # noqa: E712
                State.group.notin_([StateGroup.COMPLETED, StateGroup.CANCELLED]),
            )
        )
        total_result = await self.session.execute(total_query)
        open_result = await self.session.execute(open_query)
        return (total_result.scalar() or 0, open_result.scalar() or 0)

    async def get_batch_issue_counts(
        self,
        project_ids: Sequence[UUID],
    ) -> dict[UUID, tuple[int, int]]:
        """Get total and open issue counts for multiple projects in two queries.

        Args:
            project_ids: List of project IDs.

        Returns:
            Mapping of project_id -> (total_count, open_count).
        """
        if not project_ids:
            return {}

        total_query = (
            select(Issue.project_id, func.count().label("cnt"))
            .where(
                Issue.project_id.in_(project_ids),
                Issue.is_deleted == False,  # noqa: E712
            )
            .group_by(Issue.project_id)
        )
        open_query = (
            select(Issue.project_id, func.count().label("cnt"))
            .join(State, Issue.state_id == State.id)
            .where(
                Issue.project_id.in_(project_ids),
                Issue.is_deleted == False,  # noqa: E712
                State.group.notin_([StateGroup.COMPLETED, StateGroup.CANCELLED]),
            )
            .group_by(Issue.project_id)
        )

        total_result = await self.session.execute(total_query)
        open_result = await self.session.execute(open_query)

        totals: dict[UUID, int] = {row.project_id: row.cnt for row in total_result}
        opens: dict[UUID, int] = {row.project_id: row.cnt for row in open_result}

        return {pid: (totals.get(pid, 0), opens.get(pid, 0)) for pid in project_ids}

    async def get_by_lead(
        self,
        lead_id: UUID,
        *,
        include_deleted: bool = False,
    ) -> Sequence[Project]:
        """Get all projects led by a user.

        Args:
            lead_id: The lead's user ID.
            include_deleted: Whether to include soft-deleted projects.

        Returns:
            List of projects led by the user.
        """
        return await self.find_by(lead_id=lead_id, include_deleted=include_deleted)

    async def get_identifier_by_id(
        self,
        project_id: UUID,
        workspace_id: UUID,
    ) -> str | None:
        """Return only the short identifier string for a project.

        Fetches a single column instead of the full row for lightweight
        lookups where only the identifier is needed (e.g. building issue
        identifiers like ``PILOT-42``).

        Args:
            project_id: The project UUID.
            workspace_id: The workspace UUID (tenant scope guard).

        Returns:
            The identifier string (e.g. "PILOT") or None if not found.
        """
        result = await self.session.execute(
            select(Project.identifier).where(
                Project.id == project_id,
                Project.workspace_id == workspace_id,
                Project.is_deleted == False,  # noqa: E712
            )
        )
        return result.scalar_one_or_none()

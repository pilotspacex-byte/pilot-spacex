"""Label repository for issue categorization.

T124: Create LabelRepository for workspace and project labels.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import and_, func, or_, select

from pilot_space.infrastructure.database.models import Label, issue_labels
from pilot_space.infrastructure.database.repositories.base import BaseRepository

if TYPE_CHECKING:
    from collections.abc import Sequence
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession


class LabelRepository(BaseRepository[Label]):
    """Repository for Label entities.

    Provides:
    - Workspace and project-scoped label queries
    - Label usage statistics
    - Name-based lookups
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository.

        Args:
            session: Async database session.
        """
        super().__init__(session, Label)

    async def get_workspace_labels(
        self,
        workspace_id: UUID,
        *,
        include_project_labels: bool = True,
        project_id: UUID | None = None,
    ) -> Sequence[Label]:
        """Get labels available in a workspace.

        Args:
            workspace_id: Workspace UUID.
            include_project_labels: Whether to include project-specific labels.
            project_id: Optional project to also include labels from.

        Returns:
            Available labels.
        """
        query = select(Label).where(
            and_(
                Label.workspace_id == workspace_id,
                Label.is_deleted == False,  # noqa: E712
            )
        )

        if not include_project_labels:
            query = query.where(Label.project_id.is_(None))
        elif project_id:
            # Include workspace labels + specific project labels
            query = query.where(
                or_(
                    Label.project_id.is_(None),
                    Label.project_id == project_id,
                )
            )

        query = query.order_by(Label.name)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_project_labels(
        self,
        project_id: UUID,
        *,
        include_workspace_labels: bool = True,
    ) -> Sequence[Label]:
        """Get labels available in a project.

        Args:
            project_id: Project UUID.
            include_workspace_labels: Whether to include workspace-wide labels.

        Returns:
            Available labels.
        """
        # First get workspace_id from project
        from pilot_space.infrastructure.database.models import Project

        proj_query = select(Project.workspace_id).where(Project.id == project_id)
        proj_result = await self.session.execute(proj_query)
        workspace_id = proj_result.scalar_one_or_none()

        if not workspace_id:
            return []

        query = select(Label).where(
            and_(
                Label.workspace_id == workspace_id,
                Label.is_deleted == False,  # noqa: E712
            )
        )

        if include_workspace_labels:
            query = query.where(
                or_(
                    Label.project_id.is_(None),
                    Label.project_id == project_id,
                )
            )
        else:
            query = query.where(Label.project_id == project_id)

        query = query.order_by(Label.name)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_by_name(
        self,
        workspace_id: UUID,
        name: str,
        *,
        project_id: UUID | None = None,
    ) -> Label | None:
        """Get a label by name.

        Args:
            workspace_id: Workspace UUID.
            name: Label name (case-insensitive).
            project_id: Optional project scope.

        Returns:
            Label if found, None otherwise.
        """
        query = select(Label).where(
            and_(
                Label.workspace_id == workspace_id,
                func.lower(Label.name) == name.lower(),
                Label.is_deleted == False,  # noqa: E712
            )
        )

        if project_id:
            query = query.where(
                or_(
                    Label.project_id.is_(None),
                    Label.project_id == project_id,
                )
            )
        else:
            query = query.where(Label.project_id.is_(None))

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_names(
        self,
        workspace_id: UUID,
        names: list[str],
        *,
        project_id: UUID | None = None,
    ) -> Sequence[Label]:
        """Get labels by multiple names.

        Args:
            workspace_id: Workspace UUID.
            names: Label names (case-insensitive).
            project_id: Optional project scope.

        Returns:
            Matching labels.
        """
        lower_names = [name.lower() for name in names]
        query = select(Label).where(
            and_(
                Label.workspace_id == workspace_id,
                func.lower(Label.name).in_(lower_names),
                Label.is_deleted == False,  # noqa: E712
            )
        )

        if project_id:
            query = query.where(
                or_(
                    Label.project_id.is_(None),
                    Label.project_id == project_id,
                )
            )

        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_label_with_usage_count(
        self,
        label_id: UUID,
    ) -> tuple[Label | None, int]:
        """Get a label with its usage count.

        Args:
            label_id: Label UUID.

        Returns:
            Tuple of (label, usage_count).
        """
        label = await self.get_by_id(label_id)
        if not label:
            return None, 0

        # Count issues with this label
        count_query = (
            select(func.count())
            .select_from(issue_labels)
            .where(issue_labels.c.label_id == label_id)
        )
        count_result = await self.session.execute(count_query)
        count = count_result.scalar() or 0

        return label, count

    async def get_popular_labels(
        self,
        workspace_id: UUID,
        *,
        limit: int = 10,
        project_id: UUID | None = None,
    ) -> list[tuple[Label, int]]:
        """Get most used labels in a workspace.

        Args:
            workspace_id: Workspace UUID.
            limit: Max labels to return.
            project_id: Optional project filter.

        Returns:
            List of (label, usage_count) tuples.
        """
        # Subquery for usage counts
        usage_subq = (
            select(
                issue_labels.c.label_id,
                func.count().label("usage_count"),
            )
            .group_by(issue_labels.c.label_id)
            .subquery()
        )

        query = (
            select(Label, func.coalesce(usage_subq.c.usage_count, 0))
            .outerjoin(usage_subq, Label.id == usage_subq.c.label_id)
            .where(
                and_(
                    Label.workspace_id == workspace_id,
                    Label.is_deleted == False,  # noqa: E712
                )
            )
        )

        if project_id:
            query = query.where(
                or_(
                    Label.project_id.is_(None),
                    Label.project_id == project_id,
                )
            )

        query = query.order_by(usage_subq.c.usage_count.desc().nullslast()).limit(limit)

        result = await self.session.execute(query)
        return [(row[0], row[1]) for row in result.all()]

    async def search_labels(
        self,
        workspace_id: UUID,
        search_term: str,
        *,
        limit: int = 10,
        project_id: UUID | None = None,
    ) -> Sequence[Label]:
        """Search labels by name.

        Args:
            workspace_id: Workspace UUID.
            search_term: Search query.
            limit: Max results.
            project_id: Optional project scope.

        Returns:
            Matching labels.
        """
        query = select(Label).where(
            and_(
                Label.workspace_id == workspace_id,
                Label.name.ilike(f"%{search_term}%"),
                Label.is_deleted == False,  # noqa: E712
            )
        )

        if project_id:
            query = query.where(
                or_(
                    Label.project_id.is_(None),
                    Label.project_id == project_id,
                )
            )

        query = query.order_by(Label.name).limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def ensure_labels_exist(
        self,
        workspace_id: UUID,
        names: list[str],
        *,
        project_id: UUID | None = None,
        default_color: str = "#6b7280",
    ) -> Sequence[Label]:
        """Ensure labels exist, creating them if needed.

        Used by AI when suggesting labels that may not exist yet.

        Args:
            workspace_id: Workspace UUID.
            names: Label names to ensure.
            project_id: Optional project scope.
            default_color: Color for new labels.

        Returns:
            All labels (existing + newly created).
        """
        # Get existing labels
        existing = await self.get_by_names(workspace_id, names, project_id=project_id)
        existing_names = {label.name.lower() for label in existing}

        # Create missing labels
        new_labels: list[Label] = []
        for name in names:
            if name.lower() not in existing_names:
                new_label = Label(
                    workspace_id=workspace_id,
                    project_id=project_id,
                    name=name,
                    color=default_color,
                )
                self.session.add(new_label)
                new_labels.append(new_label)

        if new_labels:
            await self.session.flush()
            for new_label in new_labels:
                await self.session.refresh(new_label)

        return list(existing) + new_labels


__all__ = ["LabelRepository"]

"""ProjectMember repository — data access for project-scoped RBAC."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.orm import joinedload

from pilot_space.infrastructure.database.models.project_member import ProjectMember
from pilot_space.infrastructure.database.models.user import User
from pilot_space.infrastructure.database.repositories.base import (
    BaseRepository,
    CursorPage,
)


class ProjectMemberRepository(BaseRepository[ProjectMember]):
    """Repository for ProjectMember entities.

    Provides project-scoped membership queries beyond the generic CRUD
    provided by BaseRepository.
    """

    def __init__(self, session):  # type: ignore[override]
        super().__init__(session, ProjectMember)

    async def get_membership(
        self,
        project_id: UUID,
        user_id: UUID,
    ) -> ProjectMember | None:
        """Return the membership row for (project, user), or None."""
        result = await self.session.execute(
            select(ProjectMember)
            .where(
                and_(
                    ProjectMember.project_id == project_id,
                    ProjectMember.user_id == user_id,
                    ProjectMember.is_deleted == False,  # noqa: E712
                )
            )
            .options(joinedload(ProjectMember.user))
        )
        return result.scalar_one_or_none()

    async def get_active_membership(
        self,
        project_id: UUID,
        user_id: UUID,
    ) -> ProjectMember | None:
        """Return an *active* membership row, or None."""
        result = await self.session.execute(
            select(ProjectMember).where(
                and_(
                    ProjectMember.project_id == project_id,
                    ProjectMember.user_id == user_id,
                    ProjectMember.is_active == True,  # noqa: E712
                    ProjectMember.is_deleted == False,  # noqa: E712
                )
            )
        )
        return result.scalar_one_or_none()

    async def list_members(
        self,
        project_id: UUID,
        *,
        search: str | None = None,
        is_active: bool | None = True,
        cursor: str | None = None,
        page_size: int = 20,
    ) -> CursorPage[ProjectMember]:
        """List members for a project with optional search and pagination.

        Args:
            project_id: The project to list members for.
            search: Optional text filter on user email/full_name.
            is_active: Filter by active status. None returns all.
            cursor: Opaque pagination cursor (encoded ID).
            page_size: Number of results per page.
        """
        query = (
            select(ProjectMember)
            .where(
                and_(
                    ProjectMember.project_id == project_id,
                    ProjectMember.is_deleted == False,  # noqa: E712
                )
            )
            .options(joinedload(ProjectMember.user))
        )
        if is_active is not None:
            query = query.where(ProjectMember.is_active == is_active)

        if search:
            like = f"%{search.lower()}%"
            query = query.join(User, ProjectMember.user_id == User.id).where(
                User.email.ilike(like) | User.full_name.ilike(like)
            )

        return await self._paginate(query, cursor=cursor, page_size=page_size)

    async def list_project_ids_for_user(
        self,
        user_id: UUID,
        *,
        exclude_archived: bool = True,
    ) -> list[UUID]:
        """Return project IDs where user has active membership.

        Used for AI context scoping and dashboard filtering.
        """
        from pilot_space.infrastructure.database.models.project import Project

        q = (
            select(ProjectMember.project_id)
            .join(Project, Project.id == ProjectMember.project_id)
            .where(
                and_(
                    ProjectMember.user_id == user_id,
                    ProjectMember.is_active == True,  # noqa: E712
                    ProjectMember.is_deleted == False,  # noqa: E712
                    Project.is_deleted == False,  # noqa: E712
                )
            )
        )
        if exclude_archived:
            q = q.where(Project.is_archived == False)  # noqa: E712

        result = await self.session.execute(q)
        return list(result.scalars().all())

    async def upsert_membership(
        self,
        project_id: UUID,
        user_id: UUID,
        assigned_by: UUID | None,
        *,
        is_active: bool = True,
    ) -> ProjectMember:
        """Insert or reactivate a membership row.

        If a row already exists (even inactive), updates `is_active` and
        `assigned_by` rather than inserting a duplicate.
        """
        existing = await self.get_membership(project_id, user_id)
        if existing:
            existing.is_active = is_active
            existing.assigned_by = assigned_by
            await self.session.flush()
            return existing

        member = ProjectMember(
            project_id=project_id,
            user_id=user_id,
            assigned_by=assigned_by,
            is_active=is_active,
        )
        self.session.add(member)
        await self.session.flush()
        return member

    async def deactivate_membership(
        self,
        project_id: UUID,
        user_id: UUID,
    ) -> ProjectMember | None:
        """Set is_active=False for a membership row.

        Returns the updated row or None if it doesn't exist.
        """
        existing = await self.get_active_membership(project_id, user_id)
        if not existing:
            return None
        existing.is_active = False
        await self.session.flush()
        return existing

    async def deactivate_all_for_user_in_workspace(
        self,
        user_id: UUID,
        workspace_id: UUID,
    ) -> int:
        """Soft-delete all project memberships for a user across a workspace.

        Called when a workspace member is removed so their project assignments
        are also cleaned up in the same transaction.

        Args:
            user_id: The user whose project memberships to deactivate.
            workspace_id: Only deactivate memberships within this workspace.

        Returns:
            Number of project membership rows deactivated.
        """
        from pilot_space.infrastructure.database.models.project import Project

        result = await self.session.execute(
            select(ProjectMember)
            .join(Project, Project.id == ProjectMember.project_id)
            .where(
                and_(
                    Project.workspace_id == workspace_id,
                    ProjectMember.user_id == user_id,
                    ProjectMember.is_deleted == False,  # noqa: E712
                )
            )
        )
        rows = list(result.scalars().all())
        now = datetime.now(tz=UTC)
        for row in rows:
            row.is_active = False
            row.is_deleted = True
            row.deleted_at = now
        await self.session.flush()
        return len(rows)

    async def get_project_chips_for_user(
        self,
        workspace_id: UUID,
        user_id: UUID,
    ) -> list[dict[str, Any]]:
        """Return project chips [{id, name, identifier}] for a workspace member.

        Only returns active memberships on non-archived, non-deleted projects.
        """
        from pilot_space.infrastructure.database.models.project import Project

        result = await self.session.execute(
            select(Project.id, Project.name, Project.identifier)
            .join(ProjectMember, ProjectMember.project_id == Project.id)
            .where(
                and_(
                    Project.workspace_id == workspace_id,
                    ProjectMember.user_id == user_id,
                    ProjectMember.is_active == True,  # noqa: E712
                    ProjectMember.is_deleted == False,  # noqa: E712
                    Project.is_deleted == False,  # noqa: E712
                    Project.is_archived == False,  # noqa: E712
                )
            )
        )
        return [
            {"id": str(row.id), "name": row.name, "identifier": row.identifier}
            for row in result.all()
        ]

    async def _paginate(
        self,
        query,  # type: ignore[type-arg]
        *,
        cursor: str | None,
        page_size: int,
    ) -> CursorPage[ProjectMember]:
        """Simple cursor pagination by created_at / id ordering."""
        from sqlalchemy import asc, func

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar_one()

        query = query.order_by(asc(ProjectMember.assigned_at), asc(ProjectMember.id))
        if cursor:
            import base64

            try:
                decoded = base64.b64decode(cursor).decode()
                cursor_id = UUID(decoded)
                query = query.where(ProjectMember.id > cursor_id)
            except Exception:
                pass

        query = query.limit(page_size + 1)
        result = await self.session.execute(query)
        items = list(result.scalars().unique().all())
        has_next = len(items) > page_size
        if has_next:
            items = items[:page_size]

        next_cursor = None
        if has_next and items:
            import base64

            next_cursor = base64.b64encode(str(items[-1].id).encode()).decode()

        return CursorPage(
            items=items,
            total=total,
            next_cursor=next_cursor,
            has_next=has_next,
            page_size=page_size,
        )

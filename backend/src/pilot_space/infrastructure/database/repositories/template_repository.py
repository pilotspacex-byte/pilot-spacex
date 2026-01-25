"""Template repository for Template data access.

Provides specialized methods for template-related queries.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select

from pilot_space.infrastructure.database.models.template import Template
from pilot_space.infrastructure.database.repositories.base import BaseRepository

if TYPE_CHECKING:
    from collections.abc import Sequence
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession


class TemplateRepository(BaseRepository[Template]):
    """Repository for Template entities.

    Extends BaseRepository with template-specific queries.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize TemplateRepository.

        Args:
            session: The async database session.
        """
        super().__init__(session, Template)

    async def get_defaults(
        self,
        workspace_id: UUID,
    ) -> Sequence[Template]:
        """Get default templates for a workspace.

        Args:
            workspace_id: The workspace ID.

        Returns:
            List of default templates.
        """
        query = (
            select(Template)
            .where(
                Template.workspace_id == workspace_id,
                Template.is_default == True,  # noqa: E712
                Template.is_deleted == False,  # noqa: E712
            )
            .order_by(Template.name.asc())
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_by_category(
        self,
        workspace_id: UUID,
        category: str,
        *,
        include_deleted: bool = False,
    ) -> Sequence[Template]:
        """Get templates by category in a workspace.

        Args:
            workspace_id: The workspace ID.
            category: The template category.
            include_deleted: Whether to include soft-deleted templates.

        Returns:
            List of templates in the category.
        """
        query = select(Template).where(
            Template.workspace_id == workspace_id,
            Template.category == category,
        )
        if not include_deleted:
            query = query.where(Template.is_deleted == False)  # noqa: E712
        query = query.order_by(Template.name.asc())
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_by_workspace(
        self,
        workspace_id: UUID,
        *,
        include_deleted: bool = False,
    ) -> Sequence[Template]:
        """Get all templates in a workspace.

        Args:
            workspace_id: The workspace ID.
            include_deleted: Whether to include soft-deleted templates.

        Returns:
            List of templates in the workspace.
        """
        query = select(Template).where(Template.workspace_id == workspace_id)
        if not include_deleted:
            query = query.where(Template.is_deleted == False)  # noqa: E712
        query = query.order_by(Template.is_default.desc(), Template.name.asc())
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_by_name(
        self,
        workspace_id: UUID,
        name: str,
        *,
        include_deleted: bool = False,
    ) -> Template | None:
        """Get template by name in a workspace.

        Args:
            workspace_id: The workspace ID.
            name: The template name.
            include_deleted: Whether to include soft-deleted template.

        Returns:
            The template if found, None otherwise.
        """
        query = select(Template).where(
            Template.workspace_id == workspace_id,
            Template.name == name,
        )
        if not include_deleted:
            query = query.where(Template.is_deleted == False)  # noqa: E712
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_categories(
        self,
        workspace_id: UUID,
    ) -> list[str]:
        """Get distinct template categories in a workspace.

        Args:
            workspace_id: The workspace ID.

        Returns:
            List of distinct category names.
        """
        query = (
            select(Template.category)
            .where(
                Template.workspace_id == workspace_id,
                Template.category.is_not(None),
                Template.is_deleted == False,  # noqa: E712
            )
            .distinct()
            .order_by(Template.category.asc())
        )
        result = await self.session.execute(query)
        return [row[0] for row in result.all() if row[0]]

    async def search_templates(
        self,
        workspace_id: UUID,
        search_term: str,
        *,
        category: str | None = None,
        limit: int = 20,
    ) -> Sequence[Template]:
        """Search templates by name or description.

        Args:
            workspace_id: The workspace ID.
            search_term: Text to search for.
            category: Optional category filter.
            limit: Maximum results to return.

        Returns:
            List of matching templates.
        """
        from sqlalchemy import or_

        query = select(Template).where(
            Template.workspace_id == workspace_id,
            Template.is_deleted == False,  # noqa: E712
        )

        if category:
            query = query.where(Template.category == category)

        search_pattern = f"%{search_term}%"
        query = query.where(
            or_(
                Template.name.ilike(search_pattern),
                Template.description.ilike(search_pattern),
            )
        )
        query = query.order_by(Template.is_default.desc(), Template.name.asc())
        query = query.limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()

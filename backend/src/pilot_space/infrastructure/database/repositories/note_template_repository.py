"""Repository for NoteTemplate entities.

T-141: note_templates CRUD — workspace custom templates + system templates.

Query patterns:
- list_for_workspace: system templates + workspace-scoped templates
- get_by_id: single template fetch
- create / update / delete: lifecycle operations
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from sqlalchemy import and_, or_, select

from pilot_space.infrastructure.database.models.note_template import NoteTemplate
from pilot_space.infrastructure.database.repositories.base import BaseRepository

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy.ext.asyncio import AsyncSession


class NoteTemplateRepository(BaseRepository[NoteTemplate]):
    """Repository for NoteTemplate entities.

    All write operations use flush() (no commit) — callers own transaction
    boundaries via the session context.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize NoteTemplateRepository.

        Args:
            session: The async database session.
        """
        super().__init__(session, NoteTemplate)

    async def list_for_workspace(
        self,
        workspace_id: UUID,
    ) -> Sequence[NoteTemplate]:
        """List system templates and workspace custom templates.

        Returns system templates (is_system=True) plus templates owned by
        this workspace, ordered by system-first then creation time ascending.

        Args:
            workspace_id: The workspace UUID.

        Returns:
            Sequence of NoteTemplate rows.
        """
        query = (
            select(NoteTemplate)
            .where(
                and_(
                    NoteTemplate.is_deleted == False,  # noqa: E712
                    or_(
                        NoteTemplate.is_system == True,  # noqa: E712
                        NoteTemplate.workspace_id == workspace_id,
                    ),
                )
            )
            .order_by(
                NoteTemplate.is_system.desc(),
                NoteTemplate.created_at.asc(),
            )
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_by_id(  # type: ignore[override]
        self,
        template_id: UUID,
    ) -> NoteTemplate | None:
        """Fetch a single template by primary key.

        Args:
            template_id: Template UUID.

        Returns:
            NoteTemplate or None if not found / soft-deleted.
        """
        query = select(NoteTemplate).where(
            and_(
                NoteTemplate.id == template_id,
                NoteTemplate.is_deleted == False,  # noqa: E712
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def create(  # type: ignore[override]
        self,
        *,
        workspace_id: UUID,
        name: str,
        description: str,
        content: dict[str, Any],
        created_by: UUID,
    ) -> NoteTemplate:
        """Create a custom workspace note template.

        Args:
            workspace_id: Owning workspace UUID.
            name: Template display name.
            description: Template description.
            content: TipTap JSON content.
            created_by: UUID of creating user.

        Returns:
            Newly created NoteTemplate.
        """
        template = NoteTemplate(
            id=uuid4(),
            workspace_id=workspace_id,
            name=name,
            description=description,
            content=content,
            is_system=False,
            created_by=created_by,
        )
        self.session.add(template)
        await self.session.flush()
        await self.session.refresh(template)
        return template

    async def update(  # type: ignore[override]
        self,
        template: NoteTemplate,
        *,
        name: str | None = None,
        description: str | None = None,
        content: dict[str, Any] | None = None,
    ) -> NoteTemplate:
        """Apply partial updates to a template in-place and flush.

        Args:
            template: The NoteTemplate instance to update.
            name: New name, or None to leave unchanged.
            description: New description, or None to leave unchanged.
            content: New content dict, or None to leave unchanged.

        Returns:
            Updated NoteTemplate.
        """
        if name is not None:
            template.name = name
        if description is not None:
            template.description = description
        if content is not None:
            template.content = content
        await self.session.flush()
        await self.session.refresh(template)
        return template

    async def delete(self, entity: NoteTemplate, *, hard: bool = False) -> None:
        """Hard-delete a note template row.

        Note templates use hard delete (consistent with original service
        behaviour and the absence of a soft-delete use case here).

        Args:
            entity: The NoteTemplate instance to delete.
            hard: Ignored; note templates always use hard delete.
        """
        await self.session.delete(entity)
        await self.session.flush()


__all__ = ["NoteTemplateRepository"]

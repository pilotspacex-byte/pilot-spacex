"""Note template service -- CRUD for workspace note templates.

T-144, Feature 016 M8.

Extracts auth checks and template management logic from the note_templates
router into a proper service layer. All DB access is delegated to
NoteTemplateRepository.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from pilot_space.domain.exceptions import ForbiddenError, NotFoundError
from pilot_space.infrastructure.database.models.workspace_member import WorkspaceRole
from pilot_space.infrastructure.database.repositories.note_template_repository import (
    NoteTemplateRepository,
)
from pilot_space.infrastructure.database.repositories.workspace_member_repository import (
    WorkspaceMemberRepository,
)
from pilot_space.infrastructure.logging import get_logger
from pilot_space.schemas.note_template import NoteTemplateResult

logger = get_logger(__name__)


# -- Payloads / Results --------------------------------------------------------


@dataclass(frozen=True)
class CreateTemplatePayload:
    workspace_id: UUID
    name: str
    description: str
    content: dict[str, Any]
    created_by: UUID


@dataclass(frozen=True)
class UpdateTemplatePayload:
    workspace_id: UUID
    template_id: UUID
    current_user_id: UUID
    name: str | None = None
    description: str | None = None
    content: dict[str, Any] | None = None


@dataclass(frozen=True)
class DeleteTemplatePayload:
    workspace_id: UUID
    template_id: UUID
    current_user_id: UUID


# -- Service -------------------------------------------------------------------


class NoteTemplateService:
    """Business logic for note template CRUD.

    Owns workspace access checks and template lifecycle.
    All DB access is delegated to NoteTemplateRepository and WorkspaceMemberRepository.
    """

    def __init__(
        self,
        session: AsyncSession,
        note_template_repository: NoteTemplateRepository,
        workspace_member_repository: WorkspaceMemberRepository,
    ) -> None:
        self._session = session
        self._repo = note_template_repository
        self._member_repo = workspace_member_repository

    async def list_templates(self, workspace_id: UUID) -> list[NoteTemplateResult]:
        """List system templates + workspace custom templates."""
        templates = await self._repo.list_for_workspace(workspace_id)
        return [self._to_result(t) for t in templates]

    async def get_template(self, template_id: UUID, workspace_id: UUID) -> NoteTemplateResult:
        """Get a template by ID. Validates workspace access."""
        template = await self._repo.get_by_id(template_id)
        if not template:
            raise NotFoundError("Template not found.")
        if not template.is_system and template.workspace_id != workspace_id:
            raise ForbiddenError("Access denied.")
        return self._to_result(template)

    async def create_template(self, payload: CreateTemplatePayload) -> NoteTemplateResult:
        """Create a custom workspace template."""
        template = await self._repo.create(
            workspace_id=payload.workspace_id,
            name=payload.name,
            description=payload.description,
            content=payload.content,
            created_by=payload.created_by,
        )
        await self._session.commit()

        # Refresh after commit to get server-side timestamps
        await self._session.refresh(template)

        logger.info(
            "note_template_created",
            template_id=str(template.id),
            workspace_id=str(payload.workspace_id),
        )
        return self._to_result(template)

    async def update_template(self, payload: UpdateTemplatePayload) -> NoteTemplateResult:
        """Update a custom template. Admin/owner or creator."""
        template = await self._repo.get_by_id(payload.template_id)
        if not template:
            raise NotFoundError("Template not found.")
        if template.is_system:
            raise ForbiddenError("System templates are read-only.")
        if template.workspace_id != payload.workspace_id:
            raise ForbiddenError("Access denied.")

        await self._require_creator_or_admin(
            created_by=template.created_by,
            current_user_id=payload.current_user_id,
            workspace_id=payload.workspace_id,
        )

        has_changes = any(
            v is not None for v in (payload.name, payload.description, payload.content)
        )
        if has_changes:
            template = await self._repo.update(
                template,
                name=payload.name,
                description=payload.description,
                content=payload.content,
            )
            await self._session.commit()
            await self._session.refresh(template)

        return self._to_result(template)

    async def delete_template(self, payload: DeleteTemplatePayload) -> None:
        """Delete a custom template. Admin/owner or creator."""
        template = await self._repo.get_by_id(payload.template_id)
        if not template:
            raise NotFoundError("Template not found.")
        if template.is_system:
            raise ForbiddenError("System templates cannot be deleted.")
        if template.workspace_id != payload.workspace_id:
            raise ForbiddenError("Access denied.")

        await self._require_creator_or_admin(
            created_by=template.created_by,
            current_user_id=payload.current_user_id,
            workspace_id=payload.workspace_id,
        )

        await self._repo.delete(template)
        await self._session.commit()
        logger.info(
            "note_template_deleted",
            template_id=str(payload.template_id),
            workspace_id=str(payload.workspace_id),
        )

    # -- Private helpers -------------------------------------------------------

    @staticmethod
    def _to_result(template: Any) -> NoteTemplateResult:
        """Convert a NoteTemplate ORM instance to a typed result."""
        return NoteTemplateResult(
            id=template.id,
            workspace_id=template.workspace_id,
            name=template.name,
            description=template.description,
            content=template.content,
            is_system=template.is_system,
            created_by=template.created_by,
            created_at=template.created_at,
            updated_at=template.updated_at,
        )

    async def _require_creator_or_admin(
        self,
        created_by: UUID | None,
        current_user_id: UUID,
        workspace_id: UUID,
    ) -> None:
        """Verify the user is the template creator or an admin/owner."""
        if created_by is not None and created_by == current_user_id:
            return

        role = await self._member_repo.get_role_by_user_workspace(
            user_id=current_user_id,
            workspace_id=workspace_id,
        )
        if role not in (WorkspaceRole.OWNER, WorkspaceRole.ADMIN):
            raise ForbiddenError("Access denied.")

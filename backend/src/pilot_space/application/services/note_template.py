"""Note template service -- CRUD for workspace note templates.

T-144, Feature 016 M8.

Extracts raw SQL CRUD, auth checks, and template management logic
from the note_templates router into a proper service layer.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from typing import Any
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pilot_space.domain.exceptions import ForbiddenError, NotFoundError
from pilot_space.infrastructure.database.models.workspace_member import (
    WorkspaceMember,
    WorkspaceRole,
)
from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)

# Allowlist of columns permitted in UPDATE SET clause.
_ALLOWED_UPDATE_COLUMNS: frozenset[str] = frozenset({"name", "description", "content"})

_SELECT_COLS = (
    "id, workspace_id, name, description, content, is_system, created_by, created_at, updated_at"
)


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

    Owns raw SQL queries, workspace access checks, and template lifecycle.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_templates(self, workspace_id: UUID) -> list[dict[str, Any]]:
        """List system templates + workspace custom templates."""
        result = await self._session.execute(
            sa.text(
                f"SELECT {_SELECT_COLS} FROM note_templates "
                "WHERE is_system = true OR workspace_id = :ws_id "
                "ORDER BY is_system DESC, created_at ASC"
            ),
            {"ws_id": str(workspace_id)},
        )
        return [dict(r) for r in result.mappings()]

    async def get_template(
        self, template_id: UUID, workspace_id: UUID
    ) -> dict[str, Any]:
        """Get a template by ID. Validates workspace access."""
        row = await self._get_template_row(template_id)
        if not row:
            raise NotFoundError("Template not found.")
        if not row["is_system"] and row["workspace_id"] != workspace_id:
            raise ForbiddenError("Access denied.")
        return row

    async def create_template(self, payload: CreateTemplatePayload) -> dict[str, Any]:
        """Create a custom workspace template."""
        new_id = uuid.uuid4()

        await self._session.execute(
            sa.text(
                "INSERT INTO note_templates "
                "(id, workspace_id, name, description, content, is_system, created_by) "
                "VALUES (:id, :ws_id, :name, :description, :content::jsonb, false, :created_by)"
            ),
            {
                "id": str(new_id),
                "ws_id": str(payload.workspace_id),
                "name": payload.name,
                "description": payload.description,
                "content": json.dumps(payload.content),
                "created_by": str(payload.created_by),
            },
        )
        await self._session.commit()

        row = await self._get_template_row(new_id)
        if not row:
            raise NotFoundError("Template creation failed.")

        logger.info(
            "note_template_created",
            template_id=str(new_id),
            workspace_id=str(payload.workspace_id),
        )
        return row

    async def update_template(self, payload: UpdateTemplatePayload) -> dict[str, Any]:
        """Update a custom template. Admin/owner or creator."""
        row = await self._get_template_row(payload.template_id)
        if not row:
            raise NotFoundError("Template not found.")
        if row["is_system"]:
            raise ForbiddenError("System templates are read-only.")
        if row["workspace_id"] != payload.workspace_id:
            raise ForbiddenError("Access denied.")

        await self._require_creator_or_admin(
            row, payload.current_user_id, payload.workspace_id
        )

        updates: dict[str, Any] = {}
        if payload.name is not None:
            updates["name"] = payload.name
        if payload.description is not None:
            updates["description"] = payload.description
        if payload.content is not None:
            updates["content"] = json.dumps(payload.content)

        if updates:
            for key in updates:
                if key not in _ALLOWED_UPDATE_COLUMNS:
                    raise ValueError(f"Invalid update column: {key}")
            set_clause = ", ".join(f"{k} = :{k}" for k in updates)
            updates["id"] = str(payload.template_id)
            await self._session.execute(
                sa.text(
                    f"UPDATE note_templates SET {set_clause}, updated_at = now() WHERE id = :id"
                ),
                updates,
            )
            await self._session.commit()

        return await self._get_template_row(payload.template_id)  # type: ignore[return-value]

    async def delete_template(self, payload: DeleteTemplatePayload) -> None:
        """Delete a custom template. Admin/owner or creator."""
        row = await self._get_template_row(payload.template_id)
        if not row:
            raise NotFoundError("Template not found.")
        if row["is_system"]:
            raise ForbiddenError("System templates cannot be deleted.")
        if row["workspace_id"] != payload.workspace_id:
            raise ForbiddenError("Access denied.")

        await self._require_creator_or_admin(
            row, payload.current_user_id, payload.workspace_id
        )

        await self._session.execute(
            sa.text("DELETE FROM note_templates WHERE id = :id"),
            {"id": str(payload.template_id)},
        )
        await self._session.commit()
        logger.info(
            "note_template_deleted",
            template_id=str(payload.template_id),
            workspace_id=str(payload.workspace_id),
        )

    # -- Private helpers -------------------------------------------------------

    async def _get_template_row(self, template_id: UUID) -> dict[str, Any] | None:
        result = await self._session.execute(
            sa.text(f"SELECT {_SELECT_COLS} FROM note_templates WHERE id = :id"),
            {"id": str(template_id)},
        )
        row = result.mappings().first()
        return dict(row) if row else None

    async def _require_creator_or_admin(
        self,
        row: dict[str, Any],
        current_user_id: UUID,
        workspace_id: UUID,
    ) -> None:
        """Verify the user is the template creator or an admin/owner."""
        is_creator = (
            str(row["created_by"]) == str(current_user_id) if row["created_by"] else False
        )
        if is_creator:
            return

        result = await self._session.execute(
            select(WorkspaceMember.role).where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == current_user_id,
            )
        )
        role = result.scalar()
        if role not in (WorkspaceRole.OWNER, WorkspaceRole.ADMIN):
            raise ForbiddenError("Access denied.")

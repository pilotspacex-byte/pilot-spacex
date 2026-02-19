"""Unit tests for note templates CRUD router (T-150, Feature 016 M8).

Tests cover:
- list_templates: member access, system + workspace templates returned
- create_template: admin-only, returns created template
- get_template: member access, 404 on missing, 403 on wrong workspace
- update_template: system template read-only, creator or admin can update
- delete_template: system template protected, creator or admin can delete
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException

from pilot_space.api.v1.routers.note_templates import (
    _get_template,
    create_template,
    delete_template,
    get_template,
    list_templates,
    update_template,
)
from pilot_space.api.v1.schemas.note_template import (
    NoteTemplateCreate,
    NoteTemplateUpdate,
)
from pilot_space.infrastructure.database.models.workspace_member import WorkspaceRole

pytestmark = pytest.mark.asyncio

_EMPTY_CONTENT: dict[str, Any] = {"type": "doc", "content": []}


def _make_row(
    *,
    is_system: bool = False,
    workspace_id: UUID | None = None,
    created_by: UUID | None = None,
    template_id: UUID | None = None,
) -> dict[str, Any]:
    from datetime import UTC, datetime

    now = datetime.now(UTC)
    return {
        "id": template_id or uuid4(),
        "workspace_id": workspace_id,
        "name": "Test Template",
        "description": "A test template",
        "content": _EMPTY_CONTENT,
        "is_system": is_system,
        "created_by": created_by,
        "created_at": now,
        "updated_at": now,
    }


def _make_db(rows: list[dict[str, Any]]) -> AsyncMock:
    """Create an AsyncMock db session that returns given rows for execute."""
    db = AsyncMock()
    mapping_mock = MagicMock()
    mapping_mock.first.return_value = rows[0] if rows else None
    mapping_mock.__iter__ = lambda _self: iter(rows)

    result_mock = MagicMock()
    result_mock.mappings.return_value = mapping_mock
    result_mock.scalar.return_value = None
    db.execute.return_value = result_mock
    db.commit = AsyncMock()
    return db


# ── _get_template helper ─────────────────────────────────────────────────────


class TestGetTemplateHelper:
    async def test_returns_row_when_found(self) -> None:
        row = _make_row()
        db = _make_db([row])
        result = await _get_template(db, row["id"])
        assert result is not None
        assert result["id"] == row["id"]

    async def test_returns_none_when_not_found(self) -> None:
        db = _make_db([])
        result = await _get_template(db, uuid4())
        assert result is None


# ── list_templates endpoint ───────────────────────────────────────────────────


class TestListTemplates:
    async def test_returns_system_and_workspace_templates(self) -> None:
        ws_id = uuid4()
        sys_row = _make_row(is_system=True)
        ws_row = _make_row(workspace_id=ws_id)
        db = _make_db([sys_row, ws_row])

        result = await list_templates(
            workspace_id=ws_id,
            db=db,
            _=ws_id,  # type: ignore[arg-type]
        )

        assert result.total == 2
        assert len(result.templates) == 2

    async def test_returns_empty_when_no_templates(self) -> None:
        db = _make_db([])
        result = await list_templates(
            workspace_id=uuid4(),
            db=db,
            _=uuid4(),  # type: ignore[arg-type]
        )
        assert result.total == 0


# ── create_template endpoint ──────────────────────────────────────────────────


class TestCreateTemplate:
    async def test_creates_template_and_returns_it(self) -> None:
        ws_id = uuid4()
        user_id = uuid4()
        new_row = _make_row(workspace_id=ws_id, created_by=user_id)

        db = AsyncMock()
        # First execute (INSERT) returns nothing meaningful
        insert_result = MagicMock()
        # Second execute (SELECT after insert) returns the new row
        select_mapping = MagicMock()
        select_mapping.first.return_value = new_row
        select_result = MagicMock()
        select_result.mappings.return_value = select_mapping
        db.execute.side_effect = [insert_result, select_result]
        db.commit = AsyncMock()

        payload = NoteTemplateCreate(
            name="My Template",
            description="Desc",
            content=_EMPTY_CONTENT,
        )

        result = await create_template(
            workspace_id=ws_id,
            payload=payload,
            db=db,
            current_user_id=user_id,
            _=ws_id,  # type: ignore[arg-type]
        )

        assert result.name == new_row["name"]
        db.commit.assert_awaited_once()

    async def test_raises_500_if_insert_returns_nothing(self) -> None:
        db = AsyncMock()
        insert_result = MagicMock()
        # SELECT after insert returns nothing
        select_mapping = MagicMock()
        select_mapping.first.return_value = None
        select_result = MagicMock()
        select_result.mappings.return_value = select_mapping
        db.execute.side_effect = [insert_result, select_result]
        db.commit = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await create_template(
                workspace_id=uuid4(),
                payload=NoteTemplateCreate(name="T", content=_EMPTY_CONTENT),
                db=db,
                current_user_id=uuid4(),
                _=uuid4(),  # type: ignore[arg-type]
            )

        assert exc_info.value.status_code == 500


# ── get_template endpoint ─────────────────────────────────────────────────────


class TestGetTemplate:
    async def test_returns_system_template_for_any_workspace(self) -> None:
        row = _make_row(is_system=True)
        db = _make_db([row])

        result = await get_template(
            workspace_id=uuid4(),  # any workspace
            template_id=row["id"],
            db=db,
            _=uuid4(),  # type: ignore[arg-type]
        )
        assert result.is_system is True

    async def test_returns_workspace_template_for_correct_workspace(self) -> None:
        ws_id = uuid4()
        row = _make_row(workspace_id=ws_id)
        db = _make_db([row])

        result = await get_template(
            workspace_id=ws_id,
            template_id=row["id"],
            db=db,
            _=ws_id,  # type: ignore[arg-type]
        )
        assert result.workspace_id == ws_id

    async def test_raises_404_when_not_found(self) -> None:
        db = _make_db([])
        with pytest.raises(HTTPException) as exc_info:
            await get_template(
                workspace_id=uuid4(),
                template_id=uuid4(),
                db=db,
                _=uuid4(),  # type: ignore[arg-type]
            )
        assert exc_info.value.status_code == 404

    async def test_raises_403_for_wrong_workspace(self) -> None:
        ws_id = uuid4()
        other_ws_id = uuid4()
        row = _make_row(workspace_id=other_ws_id)
        db = _make_db([row])

        with pytest.raises(HTTPException) as exc_info:
            await get_template(
                workspace_id=ws_id,
                template_id=row["id"],
                db=db,
                _=ws_id,  # type: ignore[arg-type]
            )
        assert exc_info.value.status_code == 403


# ── update_template endpoint ──────────────────────────────────────────────────


class TestUpdateTemplate:
    async def test_raises_404_when_not_found(self) -> None:
        db = _make_db([])
        with pytest.raises(HTTPException) as exc_info:
            await update_template(
                workspace_id=uuid4(),
                template_id=uuid4(),
                payload=NoteTemplateUpdate(name="X"),
                db=db,
                current_user_id=uuid4(),
                _=uuid4(),  # type: ignore[arg-type]
            )
        assert exc_info.value.status_code == 404

    async def test_raises_403_for_system_template(self) -> None:
        row = _make_row(is_system=True)
        db = _make_db([row])
        with pytest.raises(HTTPException) as exc_info:
            await update_template(
                workspace_id=uuid4(),
                template_id=row["id"],
                payload=NoteTemplateUpdate(name="X"),
                db=db,
                current_user_id=uuid4(),
                _=uuid4(),  # type: ignore[arg-type]
            )
        assert exc_info.value.status_code == 403

    async def test_raises_403_for_wrong_workspace(self) -> None:
        ws_id = uuid4()
        row = _make_row(workspace_id=uuid4())  # different workspace
        db = _make_db([row])
        with pytest.raises(HTTPException) as exc_info:
            await update_template(
                workspace_id=ws_id,
                template_id=row["id"],
                payload=NoteTemplateUpdate(name="X"),
                db=db,
                current_user_id=uuid4(),
                _=ws_id,  # type: ignore[arg-type]
            )
        assert exc_info.value.status_code == 403

    async def test_creator_can_update(self) -> None:
        ws_id = uuid4()
        user_id = uuid4()
        row = _make_row(workspace_id=ws_id, created_by=user_id)
        updated_row = {**row, "name": "Updated Name"}

        db = AsyncMock()
        # First SELECT (get_template for ownership check)
        first_mapping = MagicMock()
        first_mapping.first.return_value = row
        first_result = MagicMock()
        first_result.mappings.return_value = first_mapping

        # UPDATE execute
        update_result = MagicMock()

        # Second SELECT (get_template after update)
        second_mapping = MagicMock()
        second_mapping.first.return_value = updated_row
        second_result = MagicMock()
        second_result.mappings.return_value = second_mapping

        db.execute.side_effect = [first_result, update_result, second_result]
        db.commit = AsyncMock()

        result = await update_template(
            workspace_id=ws_id,
            template_id=row["id"],
            payload=NoteTemplateUpdate(name="Updated Name"),
            db=db,
            current_user_id=user_id,
            _=ws_id,  # type: ignore[arg-type]
        )

        assert result.name == "Updated Name"

    async def test_non_creator_admin_can_update(self) -> None:
        ws_id = uuid4()
        creator_id = uuid4()
        admin_id = uuid4()
        row = _make_row(workspace_id=ws_id, created_by=creator_id)
        updated_row = {**row, "name": "Admin Updated"}

        db = AsyncMock()
        # First SELECT (get_template)
        first_mapping = MagicMock()
        first_mapping.first.return_value = row
        first_result = MagicMock()
        first_result.mappings.return_value = first_mapping

        # Role check (scalar returns ADMIN)
        role_result = MagicMock()
        role_result.scalar.return_value = WorkspaceRole.ADMIN

        # UPDATE execute
        update_result = MagicMock()

        # Second SELECT (get_template after update)
        second_mapping = MagicMock()
        second_mapping.first.return_value = updated_row
        second_result = MagicMock()
        second_result.mappings.return_value = second_mapping

        db.execute.side_effect = [first_result, role_result, update_result, second_result]
        db.commit = AsyncMock()

        result = await update_template(
            workspace_id=ws_id,
            template_id=row["id"],
            payload=NoteTemplateUpdate(name="Admin Updated"),
            db=db,
            current_user_id=admin_id,
            _=ws_id,  # type: ignore[arg-type]
        )

        assert result.name == "Admin Updated"

    async def test_non_creator_member_cannot_update(self) -> None:
        ws_id = uuid4()
        creator_id = uuid4()
        member_id = uuid4()
        row = _make_row(workspace_id=ws_id, created_by=creator_id)

        db = AsyncMock()
        first_mapping = MagicMock()
        first_mapping.first.return_value = row
        first_result = MagicMock()
        first_result.mappings.return_value = first_mapping

        role_result = MagicMock()
        role_result.scalar.return_value = WorkspaceRole.MEMBER

        db.execute.side_effect = [first_result, role_result]
        db.commit = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await update_template(
                workspace_id=ws_id,
                template_id=row["id"],
                payload=NoteTemplateUpdate(name="X"),
                db=db,
                current_user_id=member_id,
                _=ws_id,  # type: ignore[arg-type]
            )
        assert exc_info.value.status_code == 403


# ── delete_template endpoint ──────────────────────────────────────────────────


class TestDeleteTemplate:
    async def test_raises_404_when_not_found(self) -> None:
        db = _make_db([])
        with pytest.raises(HTTPException) as exc_info:
            await delete_template(
                workspace_id=uuid4(),
                template_id=uuid4(),
                db=db,
                current_user_id=uuid4(),
                _=uuid4(),  # type: ignore[arg-type]
            )
        assert exc_info.value.status_code == 404

    async def test_raises_403_for_system_template(self) -> None:
        row = _make_row(is_system=True)
        db = _make_db([row])
        with pytest.raises(HTTPException) as exc_info:
            await delete_template(
                workspace_id=uuid4(),
                template_id=row["id"],
                db=db,
                current_user_id=uuid4(),
                _=uuid4(),  # type: ignore[arg-type]
            )
        assert exc_info.value.status_code == 403

    async def test_creator_can_delete(self) -> None:
        ws_id = uuid4()
        user_id = uuid4()
        row = _make_row(workspace_id=ws_id, created_by=user_id)

        db = AsyncMock()
        mapping = MagicMock()
        mapping.first.return_value = row
        result = MagicMock()
        result.mappings.return_value = mapping
        delete_result = MagicMock()
        db.execute.side_effect = [result, delete_result]
        db.commit = AsyncMock()

        await delete_template(
            workspace_id=ws_id,
            template_id=row["id"],
            db=db,
            current_user_id=user_id,
            _=ws_id,  # type: ignore[arg-type]
        )

        db.commit.assert_awaited_once()

    async def test_admin_can_delete_others_template(self) -> None:
        ws_id = uuid4()
        creator_id = uuid4()
        admin_id = uuid4()
        row = _make_row(workspace_id=ws_id, created_by=creator_id)

        db = AsyncMock()
        first_mapping = MagicMock()
        first_mapping.first.return_value = row
        first_result = MagicMock()
        first_result.mappings.return_value = first_mapping

        role_result = MagicMock()
        role_result.scalar.return_value = WorkspaceRole.ADMIN

        delete_result = MagicMock()
        db.execute.side_effect = [first_result, role_result, delete_result]
        db.commit = AsyncMock()

        await delete_template(
            workspace_id=ws_id,
            template_id=row["id"],
            db=db,
            current_user_id=admin_id,
            _=ws_id,  # type: ignore[arg-type]
        )

        db.commit.assert_awaited_once()

    async def test_member_cannot_delete_others_template(self) -> None:
        ws_id = uuid4()
        creator_id = uuid4()
        member_id = uuid4()
        row = _make_row(workspace_id=ws_id, created_by=creator_id)

        db = AsyncMock()
        first_mapping = MagicMock()
        first_mapping.first.return_value = row
        first_result = MagicMock()
        first_result.mappings.return_value = first_mapping

        role_result = MagicMock()
        role_result.scalar.return_value = WorkspaceRole.MEMBER

        db.execute.side_effect = [first_result, role_result]
        db.commit = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await delete_template(
                workspace_id=ws_id,
                template_id=row["id"],
                db=db,
                current_user_id=member_id,
                _=ws_id,  # type: ignore[arg-type]
            )
        assert exc_info.value.status_code == 403

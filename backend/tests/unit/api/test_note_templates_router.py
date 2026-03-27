"""Unit tests for note templates CRUD router (T-150, Feature 016 M8).

Tests cover:
- list_templates: member access, system + workspace templates returned
- create_template: admin-only, returns created template
- get_template: member access, 404 on missing, 403 on wrong workspace
- update_template: system template read-only, creator or admin can update
- delete_template: system template protected, creator or admin can delete

After the repository-pattern refactor the router is a thin HTTP shell that
delegates all logic to NoteTemplateService. Tests mock the service instead of
the raw DB session.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from pilot_space.api.v1.routers.note_templates import (
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
from pilot_space.domain.exceptions import ForbiddenError, NotFoundError

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


def _make_service(**method_overrides: Any) -> MagicMock:
    """Create a MagicMock NoteTemplateService with AsyncMock methods."""
    svc = MagicMock()
    for method in (
        "list_templates",
        "get_template",
        "create_template",
        "update_template",
        "delete_template",
    ):
        setattr(svc, method, AsyncMock())
    for method, return_value in method_overrides.items():
        getattr(svc, method).return_value = return_value
    return svc


# ── list_templates endpoint ───────────────────────────────────────────────────


class TestListTemplates:
    async def test_returns_system_and_workspace_templates(self) -> None:
        ws_id = uuid4()
        sys_row = _make_row(is_system=True)
        ws_row = _make_row(workspace_id=ws_id)
        svc = _make_service(list_templates=[sys_row, ws_row])

        result = await list_templates(
            workspace_id=ws_id,
            db=AsyncMock(),
            service=svc,
            _=ws_id,  # type: ignore[arg-type]
        )

        assert result.total == 2
        assert len(result.templates) == 2
        svc.list_templates.assert_awaited_once_with(ws_id)

    async def test_returns_empty_when_no_templates(self) -> None:
        svc = _make_service(list_templates=[])
        result = await list_templates(
            workspace_id=uuid4(),
            db=AsyncMock(),
            service=svc,
            _=uuid4(),  # type: ignore[arg-type]
        )
        assert result.total == 0


# ── create_template endpoint ──────────────────────────────────────────────────


class TestCreateTemplate:
    async def test_creates_template_and_returns_it(self) -> None:
        ws_id = uuid4()
        user_id = uuid4()
        new_row = _make_row(workspace_id=ws_id, created_by=user_id)
        svc = _make_service(create_template=new_row)

        payload = NoteTemplateCreate(
            name="My Template",
            description="Desc",
            content=_EMPTY_CONTENT,
        )

        result = await create_template(
            workspace_id=ws_id,
            payload=payload,
            db=AsyncMock(),
            current_user_id=user_id,
            service=svc,
            _=ws_id,  # type: ignore[arg-type]
        )

        assert result.name == new_row["name"]
        svc.create_template.assert_awaited_once()


# ── get_template endpoint ─────────────────────────────────────────────────────


class TestGetTemplate:
    async def test_returns_system_template_for_any_workspace(self) -> None:
        row = _make_row(is_system=True)
        svc = _make_service(get_template=row)

        result = await get_template(
            workspace_id=uuid4(),
            template_id=row["id"],
            db=AsyncMock(),
            service=svc,
            _=uuid4(),  # type: ignore[arg-type]
        )
        assert result.is_system is True

    async def test_returns_workspace_template_for_correct_workspace(self) -> None:
        ws_id = uuid4()
        row = _make_row(workspace_id=ws_id)
        svc = _make_service(get_template=row)

        result = await get_template(
            workspace_id=ws_id,
            template_id=row["id"],
            db=AsyncMock(),
            service=svc,
            _=ws_id,  # type: ignore[arg-type]
        )
        assert result.workspace_id == ws_id

    async def test_propagates_not_found_from_service(self) -> None:
        svc = _make_service()
        svc.get_template.side_effect = NotFoundError("Template not found.")

        with pytest.raises(NotFoundError):
            await get_template(
                workspace_id=uuid4(),
                template_id=uuid4(),
                db=AsyncMock(),
                service=svc,
                _=uuid4(),  # type: ignore[arg-type]
            )

    async def test_propagates_forbidden_from_service(self) -> None:
        svc = _make_service()
        svc.get_template.side_effect = ForbiddenError("Access denied.")

        with pytest.raises(ForbiddenError):
            await get_template(
                workspace_id=uuid4(),
                template_id=uuid4(),
                db=AsyncMock(),
                service=svc,
                _=uuid4(),  # type: ignore[arg-type]
            )


# ── update_template endpoint ──────────────────────────────────────────────────


class TestUpdateTemplate:
    async def test_propagates_not_found_from_service(self) -> None:
        svc = _make_service()
        svc.update_template.side_effect = NotFoundError("Template not found.")

        with pytest.raises(NotFoundError):
            await update_template(
                workspace_id=uuid4(),
                template_id=uuid4(),
                payload=NoteTemplateUpdate(name="X"),
                db=AsyncMock(),
                current_user_id=uuid4(),
                service=svc,
                _=uuid4(),  # type: ignore[arg-type]
            )

    async def test_propagates_forbidden_for_system_template(self) -> None:
        svc = _make_service()
        svc.update_template.side_effect = ForbiddenError("System templates are read-only.")

        with pytest.raises(ForbiddenError):
            await update_template(
                workspace_id=uuid4(),
                template_id=uuid4(),
                payload=NoteTemplateUpdate(name="X"),
                db=AsyncMock(),
                current_user_id=uuid4(),
                service=svc,
                _=uuid4(),  # type: ignore[arg-type]
            )

    async def test_creator_can_update(self) -> None:
        ws_id = uuid4()
        user_id = uuid4()
        updated_row = _make_row(workspace_id=ws_id, created_by=user_id)
        updated_row["name"] = "Updated Name"
        svc = _make_service(update_template=updated_row)

        result = await update_template(
            workspace_id=ws_id,
            template_id=uuid4(),
            payload=NoteTemplateUpdate(name="Updated Name"),
            db=AsyncMock(),
            current_user_id=user_id,
            service=svc,
            _=ws_id,  # type: ignore[arg-type]
        )

        assert result.name == "Updated Name"


# ── delete_template endpoint ──────────────────────────────────────────────────


class TestDeleteTemplate:
    async def test_propagates_not_found_from_service(self) -> None:
        svc = _make_service()
        svc.delete_template.side_effect = NotFoundError("Template not found.")

        with pytest.raises(NotFoundError):
            await delete_template(
                workspace_id=uuid4(),
                template_id=uuid4(),
                db=AsyncMock(),
                current_user_id=uuid4(),
                service=svc,
                _=uuid4(),  # type: ignore[arg-type]
            )

    async def test_propagates_forbidden_for_system_template(self) -> None:
        svc = _make_service()
        svc.delete_template.side_effect = ForbiddenError("System templates cannot be deleted.")

        with pytest.raises(ForbiddenError):
            await delete_template(
                workspace_id=uuid4(),
                template_id=uuid4(),
                db=AsyncMock(),
                current_user_id=uuid4(),
                service=svc,
                _=uuid4(),  # type: ignore[arg-type]
            )

    async def test_creator_can_delete(self) -> None:
        ws_id = uuid4()
        user_id = uuid4()
        svc = _make_service()
        svc.delete_template.return_value = None

        await delete_template(
            workspace_id=ws_id,
            template_id=uuid4(),
            db=AsyncMock(),
            current_user_id=user_id,
            service=svc,
            _=ws_id,  # type: ignore[arg-type]
        )

        svc.delete_template.assert_awaited_once()

"""Unit tests for user skills router.

Tests verify:
- GET list returns user's active skills
- POST create returns 201 with CreateUserSkillService
- POST returns 409 on duplicate template
- POST returns 400 on invalid template
- PATCH update returns 200 (owner only)
- PATCH returns 403 for non-owner
- DELETE returns 204 (owner only)
- DELETE returns 403 for non-owner
- 404 for non-existent skills

Source: Phase 20, P20-06
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from pilot_space.infrastructure.auth.supabase_auth import TokenPayload
from pilot_space.infrastructure.database.models.user_skill import UserSkill

pytestmark = pytest.mark.asyncio

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

WORKSPACE_ID = uuid4()
USER_ID = uuid4()
OTHER_USER_ID = uuid4()
SKILL_ID = uuid4()
TEMPLATE_ID = uuid4()
BASE_URL = f"http://test/api/v1/workspaces/{WORKSPACE_ID}/user-skills"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_token_payload(user_id: object | None = None) -> TokenPayload:
    """Build a minimal TokenPayload for auth override."""
    uid = user_id or USER_ID
    now = datetime.now(tz=UTC)
    return TokenPayload(
        sub=str(uid),
        email="test@example.com",
        role="authenticated",
        aud="authenticated",
        exp=int(now.timestamp()) + 3600,
        iat=int(now.timestamp()),
        app_metadata={},
        user_metadata={},
    )


def _make_skill(
    *,
    skill_id: object | None = None,
    user_id: object | None = None,
    template_id: object | None = None,
    is_active: bool = True,
    is_deleted: bool = False,
) -> MagicMock:
    """Create a minimal UserSkill-like mock."""
    skill = MagicMock(spec=UserSkill)
    skill.id = skill_id or uuid4()
    skill.user_id = user_id or USER_ID
    skill.workspace_id = WORKSPACE_ID
    skill.template_id = template_id or TEMPLATE_ID
    skill.skill_content = "# My Skill\nPersonalized content."
    skill.experience_description = "5 years experience"
    skill.skill_name = None
    skill.tags = []
    skill.usage = None
    skill.is_active = is_active
    skill.is_deleted = is_deleted
    skill.created_at = datetime.now(tz=UTC)
    skill.updated_at = datetime.now(tz=UTC)
    # Simulate joined template relationship
    skill.template = MagicMock()
    skill.template.name = "Backend Engineer"
    return skill


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def auth_client() -> AsyncGenerator[AsyncClient, None]:
    """HTTP client with auth mocked and workspace header."""
    from pilot_space.dependencies.auth import get_current_user
    from pilot_space.main import app

    token_payload = _make_token_payload()
    app.dependency_overrides[get_current_user] = lambda: token_payload

    with patch(
        "pilot_space.api.v1.routers.user_skills.set_rls_context",
        new=AsyncMock(),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://test",
            headers={
                "Authorization": "Bearer test-token",
                "X-Workspace-ID": str(WORKSPACE_ID),
            },
        ) as client:
            yield client

    app.dependency_overrides.pop(get_current_user, None)


# ---------------------------------------------------------------------------
# GET /user-skills
# ---------------------------------------------------------------------------


async def test_list_user_skills_returns_200(auth_client: AsyncClient) -> None:
    """GET returns user's active skills."""
    mock_skill = _make_skill()

    with patch(
        "pilot_space.api.v1.routers.user_skills.UserSkillRepository",
    ) as mock_repo_cls:
        mock_repo = mock_repo_cls.return_value
        mock_repo.get_by_user_workspace = AsyncMock(return_value=[mock_skill])

        resp = await auth_client.get(BASE_URL)

    assert resp.status_code == 200, f"Got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert len(data) == 1
    assert data[0]["template_name"] == "Backend Engineer"


async def test_list_user_skills_empty(auth_client: AsyncClient) -> None:
    """GET returns empty list when user has no skills."""
    with patch(
        "pilot_space.api.v1.routers.user_skills.UserSkillRepository",
    ) as mock_repo_cls:
        mock_repo = mock_repo_cls.return_value
        mock_repo.get_by_user_workspace = AsyncMock(return_value=[])

        resp = await auth_client.get(BASE_URL)

    assert resp.status_code == 200
    assert resp.json() == []


# ---------------------------------------------------------------------------
# POST /user-skills
# ---------------------------------------------------------------------------


async def test_create_user_skill_returns_201(auth_client: AsyncClient) -> None:
    """POST creates a user skill from a template."""
    mock_skill = _make_skill()

    with patch(
        "pilot_space.api.v1.routers.user_skills.CreateUserSkillService",
    ) as mock_svc_cls:
        mock_svc = mock_svc_cls.return_value
        mock_svc.create = AsyncMock(return_value=mock_skill)

        resp = await auth_client.post(
            BASE_URL,
            json={
                "template_id": str(TEMPLATE_ID),
                "experience_description": "5 years in Python",
            },
        )

    assert resp.status_code == 201, f"Got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert data["template_name"] == "Backend Engineer"


async def test_create_user_skill_422_duplicate(auth_client: AsyncClient) -> None:
    """POST returns 422 when user already has skill from template."""
    from pilot_space.domain.exceptions import ValidationError as AppValidationError

    with patch(
        "pilot_space.api.v1.routers.user_skills.CreateUserSkillService",
    ) as mock_svc_cls:
        mock_svc = mock_svc_cls.return_value
        mock_svc.create = AsyncMock(
            side_effect=AppValidationError(f"User already has a skill from template {TEMPLATE_ID}")
        )

        resp = await auth_client.post(
            BASE_URL,
            json={
                "template_id": str(TEMPLATE_ID),
            },
        )

    assert resp.status_code == 422


async def test_create_user_skill_422_template_not_found(auth_client: AsyncClient) -> None:
    """POST returns 422 when template not found."""
    from pilot_space.domain.exceptions import ValidationError as AppValidationError

    with patch(
        "pilot_space.api.v1.routers.user_skills.CreateUserSkillService",
    ) as mock_svc_cls:
        mock_svc = mock_svc_cls.return_value
        mock_svc.create = AsyncMock(
            side_effect=AppValidationError(f"Template not found: {TEMPLATE_ID}")
        )

        resp = await auth_client.post(
            BASE_URL,
            json={
                "template_id": str(TEMPLATE_ID),
            },
        )

    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# PATCH /user-skills/{skill_id}
# ---------------------------------------------------------------------------


async def test_update_user_skill_returns_200(auth_client: AsyncClient) -> None:
    """PATCH updates a user skill."""
    mock_skill = _make_skill(skill_id=SKILL_ID)

    with patch(
        "pilot_space.api.v1.routers.user_skills.UserSkillRepository",
    ) as mock_repo_cls:
        mock_repo = mock_repo_cls.return_value
        mock_repo.get_by_id_with_template = AsyncMock(return_value=mock_skill)
        mock_repo.update = AsyncMock(return_value=mock_skill)

        resp = await auth_client.patch(
            f"{BASE_URL}/{SKILL_ID}",
            json={"is_active": False},
        )

    assert resp.status_code == 200


async def test_update_user_skill_404_not_found(auth_client: AsyncClient) -> None:
    """PATCH returns 404 when skill not found."""
    with patch(
        "pilot_space.api.v1.routers.user_skills.UserSkillRepository",
    ) as mock_repo_cls:
        mock_repo = mock_repo_cls.return_value
        mock_repo.get_by_id_with_template = AsyncMock(return_value=None)

        resp = await auth_client.patch(
            f"{BASE_URL}/{SKILL_ID}",
            json={"is_active": False},
        )

    assert resp.status_code == 404


async def test_update_user_skill_403_not_owner(auth_client: AsyncClient) -> None:
    """PATCH returns 403 when skill belongs to another user."""
    mock_skill = _make_skill(skill_id=SKILL_ID, user_id=OTHER_USER_ID)

    with patch(
        "pilot_space.api.v1.routers.user_skills.UserSkillRepository",
    ) as mock_repo_cls:
        mock_repo = mock_repo_cls.return_value
        mock_repo.get_by_id_with_template = AsyncMock(return_value=mock_skill)

        resp = await auth_client.patch(
            f"{BASE_URL}/{SKILL_ID}",
            json={"is_active": False},
        )

    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# DELETE /user-skills/{skill_id}
# ---------------------------------------------------------------------------


async def test_delete_user_skill_returns_204(auth_client: AsyncClient) -> None:
    """DELETE soft-deletes a user skill."""
    mock_skill = _make_skill(skill_id=SKILL_ID)

    with patch(
        "pilot_space.api.v1.routers.user_skills.UserSkillRepository",
    ) as mock_repo_cls:
        mock_repo = mock_repo_cls.return_value
        mock_repo.get_by_id_with_template = AsyncMock(return_value=mock_skill)
        mock_repo.soft_delete = AsyncMock(return_value=mock_skill)

        resp = await auth_client.delete(f"{BASE_URL}/{SKILL_ID}")

    assert resp.status_code == 204


async def test_delete_user_skill_404_not_found(auth_client: AsyncClient) -> None:
    """DELETE returns 404 when skill not found."""
    with patch(
        "pilot_space.api.v1.routers.user_skills.UserSkillRepository",
    ) as mock_repo_cls:
        mock_repo = mock_repo_cls.return_value
        mock_repo.get_by_id_with_template = AsyncMock(return_value=None)

        resp = await auth_client.delete(f"{BASE_URL}/{SKILL_ID}")

    assert resp.status_code == 404


async def test_delete_user_skill_403_not_owner(auth_client: AsyncClient) -> None:
    """DELETE returns 403 when skill belongs to another user."""
    mock_skill = _make_skill(skill_id=SKILL_ID, user_id=OTHER_USER_ID)

    with patch(
        "pilot_space.api.v1.routers.user_skills.UserSkillRepository",
    ) as mock_repo_cls:
        mock_repo = mock_repo_cls.return_value
        mock_repo.get_by_id_with_template = AsyncMock(return_value=mock_skill)

        resp = await auth_client.delete(f"{BASE_URL}/{SKILL_ID}")

    assert resp.status_code == 403

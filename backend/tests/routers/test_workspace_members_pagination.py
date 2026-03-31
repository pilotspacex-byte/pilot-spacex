"""Unit tests for paginated list_workspace_members and list_workspace_invitations endpoints.

A4-E05-8: Verifies pagination (page/page_size), search filtering, has_next/has_prev flags,
and total counts for:
  - GET /workspaces/{workspace_id}/members
  - GET /workspaces/{workspace_id}/invitations
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import status

if False:  # TYPE_CHECKING
    pass

pytestmark = pytest.mark.asyncio

_WS_ID = str(uuid4())


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_workspace_member(
    *,
    role: str = "MEMBER",
    full_name: str = "Test User",
    email: str | None = None,
) -> MagicMock:
    """Build a mock WorkspaceMember ORM object."""
    m = MagicMock()
    m.user_id = uuid4()
    m.role = MagicMock()
    m.role.value = role
    m.created_at = datetime.now(UTC)
    m.weekly_available_hours = 40
    m.user = MagicMock()
    m.user.full_name = full_name
    m.user.email = email or f"{full_name.lower().replace(' ', '.')}@test.com"
    m.user.avatar_url = None
    return m


def _make_invitation(*, email: str = "invite@test.com", role: str = "MEMBER") -> MagicMock:
    """Build a mock WorkspaceInvitation ORM object."""
    inv = MagicMock()
    inv.id = uuid4()
    inv.email = email
    inv.role = MagicMock()
    inv.role.value = role
    inv.status = MagicMock()
    inv.status.value = "PENDING"
    inv.invited_by = uuid4()
    inv.suggested_sdlc_role = None
    inv.expires_at = datetime.now(UTC)
    inv.created_at = datetime.now(UTC)
    return inv


# ---------------------------------------------------------------------------
# Client fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_member_service() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def mock_invitation_service() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
async def members_client(mock_member_service: AsyncMock) -> AsyncGenerator[Any, None]:
    """Test client with workspace_member_service overridden."""
    from httpx import ASGITransport, AsyncClient

    from pilot_space.api.v1.dependencies import (
        _get_workspace_member_service,
    )
    from pilot_space.dependencies.auth import get_current_user, get_session
    from pilot_space.infrastructure.auth import TokenPayload
    from pilot_space.main import app

    user_id = uuid4()
    mock_token = TokenPayload(sub=str(user_id), email="test@test.com", exp=9999999999, iat=1)
    mock_session = AsyncMock()

    async def mock_session_gen() -> AsyncGenerator[Any, None]:
        yield mock_session

    # Patch PM repo used for project_chips and project_id filtering
    with (
        patch("pilot_space.api.v1.routers.workspace_members.ProjectMemberRepository") as MockPMRepo,
        patch(
            "pilot_space.api.v1.routers.workspace_members.set_rls_context",
            new_callable=AsyncMock,
        ),
    ):
        pm_repo_instance = AsyncMock()
        pm_repo_result = MagicMock()
        pm_repo_result.items = []
        pm_repo_instance.list_members = AsyncMock(return_value=pm_repo_result)
        pm_repo_instance.session = mock_session
        MockPMRepo.return_value = pm_repo_instance

        # Patch the raw SQL query for project chips
        mock_session.execute = AsyncMock(return_value=MagicMock(all=MagicMock(return_value=[])))

        app.dependency_overrides[get_session] = mock_session_gen
        app.dependency_overrides[get_current_user] = lambda: mock_token
        app.dependency_overrides[_get_workspace_member_service] = lambda: mock_member_service

        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://test",
            headers={"Authorization": "Bearer test-token"},
        ) as ac:
            yield ac

    app.dependency_overrides.pop(get_session, None)
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(_get_workspace_member_service, None)


@pytest.fixture
async def invitations_client(mock_invitation_service: AsyncMock) -> AsyncGenerator[Any, None]:
    """Test client with workspace_invitation_service overridden."""
    from httpx import ASGITransport, AsyncClient

    from pilot_space.api.v1.dependencies import _get_workspace_invitation_service
    from pilot_space.dependencies.auth import get_current_user, get_session
    from pilot_space.infrastructure.auth import TokenPayload
    from pilot_space.main import app

    user_id = uuid4()
    mock_token = TokenPayload(sub=str(user_id), email="test@test.com", exp=9999999999, iat=1)
    mock_session = AsyncMock()

    async def mock_session_gen() -> AsyncGenerator[Any, None]:
        yield mock_session

    with patch(
        "pilot_space.api.v1.routers.workspace_invitations.set_rls_context",
        new_callable=AsyncMock,
    ):
        app.dependency_overrides[get_session] = mock_session_gen
        app.dependency_overrides[get_current_user] = lambda: mock_token
        app.dependency_overrides[_get_workspace_invitation_service] = lambda: (
            mock_invitation_service
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://test",
            headers={"Authorization": "Bearer test-token"},
        ) as ac:
            yield ac

    app.dependency_overrides.pop(get_session, None)
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(_get_workspace_invitation_service, None)


# ===========================================================================
# GET /workspaces/{workspace_id}/members  — pagination
# ===========================================================================


class TestListWorkspaceMembersPagination:
    """A4-E05-8: Pagination for list_workspace_members."""

    async def test_returns_paginated_shape(
        self, members_client: Any, mock_member_service: AsyncMock
    ) -> None:
        """Response has items/total/has_next/has_prev/page_size keys."""
        members = [_make_workspace_member() for _ in range(3)]
        result = MagicMock()
        result.members = members
        result.total = 3
        result.project_chips = {}
        mock_member_service.list_members = AsyncMock(return_value=result)

        response = await members_client.get(f"/api/v1/workspaces/{_WS_ID}/members")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "hasNext" in data
        assert "hasPrev" in data
        assert "pageSize" in data

    async def test_default_page_returns_all_when_under_limit(
        self, members_client: Any, mock_member_service: AsyncMock
    ) -> None:
        """With 3 members and default page_size=20, returns all 3 with has_next=False."""
        members = [_make_workspace_member() for _ in range(3)]
        result = MagicMock()
        result.members = members
        result.total = 3
        result.project_chips = {}
        mock_member_service.list_members = AsyncMock(return_value=result)

        response = await members_client.get(f"/api/v1/workspaces/{_WS_ID}/members")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 3
        assert len(data["items"]) == 3
        assert data["hasNext"] is False
        assert data["hasPrev"] is False
        assert data["pageSize"] == 20

    async def test_page_size_limits_items_returned(
        self, members_client: Any, mock_member_service: AsyncMock
    ) -> None:
        """page_size=2 on 5 members returns 2 items and has_next=True."""
        all_members = [_make_workspace_member(full_name=f"User {i}") for i in range(5)]
        result = MagicMock()
        result.members = all_members[:2]  # service returns page 1 of 2
        result.total = 5
        result.project_chips = {}
        mock_member_service.list_members = AsyncMock(return_value=result)

        response = await members_client.get(
            f"/api/v1/workspaces/{_WS_ID}/members?page=1&page_size=2"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 5
        assert len(data["items"]) == 2
        assert data["hasNext"] is True
        assert data["hasPrev"] is False

    async def test_second_page_has_prev_true(
        self, members_client: Any, mock_member_service: AsyncMock
    ) -> None:
        """Page 2 with page_size=2 on 5 members has has_prev=True."""
        all_members = [_make_workspace_member(full_name=f"User {i}") for i in range(5)]
        result = MagicMock()
        result.members = all_members[2:4]  # service returns page 2 of 2
        result.total = 5
        result.project_chips = {}
        mock_member_service.list_members = AsyncMock(return_value=result)

        response = await members_client.get(
            f"/api/v1/workspaces/{_WS_ID}/members?page=2&page_size=2"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) == 2
        assert data["hasPrev"] is True
        assert data["hasNext"] is True

    async def test_last_page_has_next_false(
        self, members_client: Any, mock_member_service: AsyncMock
    ) -> None:
        """Last page on 5 members with page_size=2 → page 3 has 1 item, has_next=False."""
        all_members = [_make_workspace_member(full_name=f"User {i}") for i in range(5)]
        result = MagicMock()
        result.members = all_members[4:5]  # service returns last page (1 item)
        result.total = 5
        result.project_chips = {}
        mock_member_service.list_members = AsyncMock(return_value=result)

        response = await members_client.get(
            f"/api/v1/workspaces/{_WS_ID}/members?page=3&page_size=2"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) == 1
        assert data["hasNext"] is False
        assert data["hasPrev"] is True

    async def test_empty_workspace_returns_zero_total(
        self, members_client: Any, mock_member_service: AsyncMock
    ) -> None:
        """Empty workspace returns total=0, empty items, has_next=False."""
        result = MagicMock()
        result.members = []
        result.total = 0
        result.project_chips = {}
        mock_member_service.list_members = AsyncMock(return_value=result)

        response = await members_client.get(f"/api/v1/workspaces/{_WS_ID}/members")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []
        assert data["hasNext"] is False
        assert data["hasPrev"] is False

    async def test_search_filters_by_name(
        self, members_client: Any, mock_member_service: AsyncMock
    ) -> None:
        """search=alice returns only members whose name contains 'alice'."""
        alice = _make_workspace_member(full_name="Alice Smith", email="alice@test.com")
        charlie = _make_workspace_member(full_name="Charlie Aliceson", email="charlie@test.com")
        result = MagicMock()
        # Service returns only the matching members (already filtered)
        result.members = [alice, charlie]
        result.total = 2
        result.project_chips = {}
        mock_member_service.list_members = AsyncMock(return_value=result)

        response = await members_client.get(f"/api/v1/workspaces/{_WS_ID}/members?search=alice")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # "alice" matches Alice Smith and Charlie Aliceson
        assert data["total"] == 2
        assert len(data["items"]) == 2
        names = {item["fullName"] for item in data["items"]}
        assert "Alice Smith" in names
        assert "Charlie Aliceson" in names

    async def test_search_filters_by_email(
        self, members_client: Any, mock_member_service: AsyncMock
    ) -> None:
        """search=bob filters by email substring."""
        bob = _make_workspace_member(full_name="Bob Jones", email="bob@example.com")
        result = MagicMock()
        # Service returns only the matching member (already filtered)
        result.members = [bob]
        result.total = 1
        result.project_chips = {}
        mock_member_service.list_members = AsyncMock(return_value=result)

        response = await members_client.get(f"/api/v1/workspaces/{_WS_ID}/members?search=bob")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["email"] == "bob@example.com"

    async def test_search_is_case_insensitive(
        self, members_client: Any, mock_member_service: AsyncMock
    ) -> None:
        """search is case-insensitive."""
        alice = _make_workspace_member(full_name="ALICE SMITH", email="alice@test.com")
        result = MagicMock()
        # Service returns the matching member (already filtered, case-insensitive)
        result.members = [alice]
        result.total = 1
        result.project_chips = {}
        mock_member_service.list_members = AsyncMock(return_value=result)

        response = await members_client.get(f"/api/v1/workspaces/{_WS_ID}/members?search=alice")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 1

    async def test_search_no_match_returns_empty(
        self, members_client: Any, mock_member_service: AsyncMock
    ) -> None:
        """search with no match returns total=0, empty items."""
        result = MagicMock()
        # Service returns empty (no match)
        result.members = []
        result.total = 0
        result.project_chips = {}
        mock_member_service.list_members = AsyncMock(return_value=result)

        response = await members_client.get(
            f"/api/v1/workspaces/{_WS_ID}/members?search=zzznomatch"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []

    async def test_page_size_reflected_in_response(
        self, members_client: Any, mock_member_service: AsyncMock
    ) -> None:
        """page_size query param is reflected in response.page_size."""
        members = [_make_workspace_member() for _ in range(3)]
        result = MagicMock()
        result.members = members
        result.total = 3
        result.project_chips = {}
        mock_member_service.list_members = AsyncMock(return_value=result)

        response = await members_client.get(f"/api/v1/workspaces/{_WS_ID}/members?page_size=5")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["pageSize"] == 5


# ===========================================================================
# GET /workspaces/{workspace_id}/invitations  — pagination
# ===========================================================================


class TestListWorkspaceInvitationsPagination:
    """A4-E05-8: Pagination for list_workspace_invitations."""

    async def test_returns_paginated_shape(
        self, invitations_client: Any, mock_invitation_service: AsyncMock
    ) -> None:
        """Response has items/total/has_next/has_prev/page_size keys."""
        invitations = [_make_invitation() for _ in range(2)]
        result = MagicMock()
        result.invitations = invitations
        result.total = 2
        result.has_next = False
        result.has_prev = False
        result.page_size = 20
        mock_invitation_service.list_invitations = AsyncMock(return_value=result)

        response = await invitations_client.get(f"/api/v1/workspaces/{_WS_ID}/invitations")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "hasNext" in data
        assert "hasPrev" in data
        assert "pageSize" in data

    async def test_default_page_returns_all_when_under_limit(
        self, invitations_client: Any, mock_invitation_service: AsyncMock
    ) -> None:
        """Default page returns all invitations when count < page_size."""
        invitations = [_make_invitation(email=f"user{i}@test.com") for i in range(3)]
        result = MagicMock()
        result.invitations = invitations
        result.total = 3
        result.has_next = False
        result.has_prev = False
        result.page_size = 20
        mock_invitation_service.list_invitations = AsyncMock(return_value=result)

        response = await invitations_client.get(f"/api/v1/workspaces/{_WS_ID}/invitations")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 3
        assert len(data["items"]) == 3
        assert data["hasNext"] is False
        assert data["hasPrev"] is False
        assert data["pageSize"] == 20

    async def test_page_size_limits_items_returned(
        self, invitations_client: Any, mock_invitation_service: AsyncMock
    ) -> None:
        """page_size=2 on 5 invitations returns 2 items, has_next=True."""
        invitations = [_make_invitation(email=f"u{i}@test.com") for i in range(5)]
        result = MagicMock()
        result.invitations = invitations[:2]  # service returns page 1 of 2
        result.total = 5
        result.has_next = True
        result.has_prev = False
        result.page_size = 2
        mock_invitation_service.list_invitations = AsyncMock(return_value=result)

        response = await invitations_client.get(
            f"/api/v1/workspaces/{_WS_ID}/invitations?page=1&page_size=2"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 5
        assert len(data["items"]) == 2
        assert data["hasNext"] is True
        assert data["hasPrev"] is False

    async def test_second_page_has_prev_true(
        self, invitations_client: Any, mock_invitation_service: AsyncMock
    ) -> None:
        """Page 2 has has_prev=True."""
        invitations = [_make_invitation(email=f"u{i}@test.com") for i in range(5)]
        result = MagicMock()
        result.invitations = invitations[2:4]  # service returns page 2 of 2
        result.total = 5
        result.has_next = True
        result.has_prev = True
        result.page_size = 2
        mock_invitation_service.list_invitations = AsyncMock(return_value=result)

        response = await invitations_client.get(
            f"/api/v1/workspaces/{_WS_ID}/invitations?page=2&page_size=2"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["hasPrev"] is True
        assert data["hasNext"] is True

    async def test_last_page_has_next_false(
        self, invitations_client: Any, mock_invitation_service: AsyncMock
    ) -> None:
        """Last page has has_next=False."""
        invitations = [_make_invitation(email=f"u{i}@test.com") for i in range(5)]
        result = MagicMock()
        result.invitations = invitations[4:5]  # service returns last page (1 item)
        result.total = 5
        result.has_next = False
        result.has_prev = True
        result.page_size = 2
        mock_invitation_service.list_invitations = AsyncMock(return_value=result)

        response = await invitations_client.get(
            f"/api/v1/workspaces/{_WS_ID}/invitations?page=3&page_size=2"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) == 1
        assert data["hasNext"] is False
        assert data["hasPrev"] is True

    async def test_empty_invitations_returns_zero_total(
        self, invitations_client: Any, mock_invitation_service: AsyncMock
    ) -> None:
        """No invitations returns total=0, empty items."""
        result = MagicMock()
        result.invitations = []
        result.total = 0
        result.has_next = False
        result.has_prev = False
        result.page_size = 20
        mock_invitation_service.list_invitations = AsyncMock(return_value=result)

        response = await invitations_client.get(f"/api/v1/workspaces/{_WS_ID}/invitations")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []
        assert data["hasNext"] is False
        assert data["hasPrev"] is False

    async def test_page_size_reflected_in_response(
        self, invitations_client: Any, mock_invitation_service: AsyncMock
    ) -> None:
        """page_size query param is echoed back in response."""
        invitations = [_make_invitation(email=f"u{i}@test.com") for i in range(3)]
        result = MagicMock()
        result.invitations = invitations
        result.total = 3
        result.has_next = False
        result.has_prev = False
        result.page_size = 10
        mock_invitation_service.list_invitations = AsyncMock(return_value=result)

        response = await invitations_client.get(
            f"/api/v1/workspaces/{_WS_ID}/invitations?page_size=10"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["pageSize"] == 10

    async def test_invitation_fields_present(
        self, invitations_client: Any, mock_invitation_service: AsyncMock
    ) -> None:
        """Each invitation item has id, email, role, status fields."""
        inv = _make_invitation(email="test@example.com", role="ADMIN")
        result = MagicMock()
        result.invitations = [inv]
        result.total = 1
        result.has_next = False
        result.has_prev = False
        result.page_size = 20
        mock_invitation_service.list_invitations = AsyncMock(return_value=result)

        response = await invitations_client.get(f"/api/v1/workspaces/{_WS_ID}/invitations")

        assert response.status_code == status.HTTP_200_OK
        item = response.json()["items"][0]
        assert item["email"] == "test@example.com"
        assert item["role"] == "ADMIN"
        assert item["status"] == "PENDING"
        assert "id" in item

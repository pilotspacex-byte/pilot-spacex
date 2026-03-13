"""Unit tests for ValidateAPIKeyService.

Tests all branches: valid key, not found, expired, workspace missing.
Uses AsyncMock repositories for service-layer isolation.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from pilot_space.application.services.auth import (
    ValidateAPIKeyPayload,
    ValidateAPIKeyService,
)

pytestmark = pytest.mark.asyncio


# ============================================================================
# Helpers
# ============================================================================


def _make_api_key(
    *,
    workspace_id: UUID | None = None,
    user_id: UUID | None = None,
    expires_at: datetime | None = None,
) -> MagicMock:
    """Return a mock PilotAPIKey with controlled properties."""

    key = MagicMock()
    key.id = uuid4()
    key.workspace_id = workspace_id or uuid4()
    key.user_id = user_id or uuid4()
    key.expires_at = expires_at
    # Derive is_expired from expires_at to mirror the real property logic.
    if expires_at is None:
        key.is_expired = False
    else:
        key.is_expired = datetime.now(UTC) > expires_at
    return key


def _make_workspace(slug: str = "my-workspace") -> MagicMock:
    """Return a mock Workspace with a slug attribute."""
    ws = MagicMock()
    ws.slug = slug
    return ws


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def api_key_repo() -> AsyncMock:
    """Mock PilotAPIKeyRepository."""
    return AsyncMock()


@pytest.fixture
def workspace_repo() -> AsyncMock:
    """Mock WorkspaceRepository."""
    return AsyncMock()


@pytest.fixture
def mock_session() -> AsyncMock:
    """Mock AsyncSession for set_rls_context calls."""
    return AsyncMock()


@pytest.fixture
def service(api_key_repo: AsyncMock, workspace_repo: AsyncMock) -> ValidateAPIKeyService:
    """Service under test."""
    return ValidateAPIKeyService(
        api_key_repository=api_key_repo,
        workspace_repository=workspace_repo,
    )


# ============================================================================
# Tests: happy path
# ============================================================================


async def test_valid_key_returns_workspace_slug(
    service: ValidateAPIKeyService,
    api_key_repo: AsyncMock,
    workspace_repo: AsyncMock,
    mock_session: AsyncMock,
) -> None:
    """Valid, non-expired key returns correct workspace_slug and user_id."""
    raw_key = "ps_abc123"
    workspace_id = uuid4()
    user_id = uuid4()

    api_key = _make_api_key(workspace_id=workspace_id, user_id=user_id)
    api_key_repo.get_by_key_hash.return_value = api_key
    workspace_repo.get_by_id.return_value = _make_workspace("acme-corp")

    result = await service.execute(ValidateAPIKeyPayload(raw_key=raw_key), session=mock_session)

    assert result.workspace_slug == "acme-corp"
    assert result.user_id == str(user_id)


async def test_valid_key_hashes_with_sha256_before_lookup(
    service: ValidateAPIKeyService,
    api_key_repo: AsyncMock,
    workspace_repo: AsyncMock,
    mock_session: AsyncMock,
) -> None:
    """Service passes SHA-256 hash (not raw key) to the repository."""
    raw_key = "ps_secret"
    expected_hash = hashlib.sha256(raw_key.encode()).hexdigest()

    api_key = _make_api_key()
    api_key_repo.get_by_key_hash.return_value = api_key
    workspace_repo.get_by_id.return_value = _make_workspace("slug")

    await service.execute(ValidateAPIKeyPayload(raw_key=raw_key), session=mock_session)

    api_key_repo.get_by_key_hash.assert_awaited_once_with(expected_hash)


async def test_mark_last_used_called_on_success(
    service: ValidateAPIKeyService,
    api_key_repo: AsyncMock,
    workspace_repo: AsyncMock,
    mock_session: AsyncMock,
) -> None:
    """mark_last_used is called with the correct key id on successful validation."""
    raw_key = "ps_token"
    api_key = _make_api_key()
    api_key_repo.get_by_key_hash.return_value = api_key
    workspace_repo.get_by_id.return_value = _make_workspace("slug")

    await service.execute(ValidateAPIKeyPayload(raw_key=raw_key), session=mock_session)

    api_key_repo.mark_last_used.assert_awaited_once_with(api_key.id)


async def test_workspace_looked_up_by_workspace_id(
    service: ValidateAPIKeyService,
    api_key_repo: AsyncMock,
    workspace_repo: AsyncMock,
    mock_session: AsyncMock,
) -> None:
    """Workspace is fetched using the workspace_id from the API key record."""
    workspace_id = uuid4()
    api_key = _make_api_key(workspace_id=workspace_id)
    api_key_repo.get_by_key_hash.return_value = api_key
    workspace_repo.get_by_id.return_value = _make_workspace("ws")

    await service.execute(ValidateAPIKeyPayload(raw_key="ps_any"), session=mock_session)

    workspace_repo.get_by_id.assert_awaited_once_with(workspace_id)


async def test_never_expiring_key_is_valid(
    service: ValidateAPIKeyService,
    api_key_repo: AsyncMock,
    workspace_repo: AsyncMock,
    mock_session: AsyncMock,
) -> None:
    """Key with expires_at=None (never expires) is treated as valid."""
    api_key = _make_api_key(expires_at=None)
    assert api_key.is_expired is False

    api_key_repo.get_by_key_hash.return_value = api_key
    workspace_repo.get_by_id.return_value = _make_workspace("ws")

    result = await service.execute(
        ValidateAPIKeyPayload(raw_key="ps_forever"), session=mock_session
    )
    assert result.workspace_slug == "ws"


# ============================================================================
# Tests: failure paths
# ============================================================================


async def test_key_not_found_raises_value_error(
    service: ValidateAPIKeyService,
    api_key_repo: AsyncMock,
    mock_session: AsyncMock,
) -> None:
    """Repository returning None raises ValueError('invalid_api_key')."""
    api_key_repo.get_by_key_hash.return_value = None

    with pytest.raises(ValueError, match="invalid_api_key"):
        await service.execute(ValidateAPIKeyPayload(raw_key="ps_unknown"), session=mock_session)


async def test_expired_key_returns_not_found(
    service: ValidateAPIKeyService,
    api_key_repo: AsyncMock,
    mock_session: AsyncMock,
) -> None:
    """Expired keys are filtered by the DB query; repository returns None.

    The service delegates expiry enforcement to the SQL query. When the DB
    returns None (key filtered as expired), the service raises invalid_api_key.
    """
    # DB query filters expired keys and returns None — service sees no key
    api_key_repo.get_by_key_hash.return_value = None

    with pytest.raises(ValueError, match="invalid_api_key"):
        await service.execute(ValidateAPIKeyPayload(raw_key="ps_expired"), session=mock_session)


async def test_expired_key_does_not_call_mark_last_used(
    service: ValidateAPIKeyService,
    api_key_repo: AsyncMock,
    mock_session: AsyncMock,
) -> None:
    """mark_last_used is not called when DB returns no key (expired keys filtered by SQL)."""
    # DB filters expired keys → repository returns None
    api_key_repo.get_by_key_hash.return_value = None

    with pytest.raises(ValueError, match="invalid_api_key"):
        await service.execute(ValidateAPIKeyPayload(raw_key="ps_old"), session=mock_session)

    api_key_repo.mark_last_used.assert_not_awaited()


async def test_workspace_not_found_raises_value_error(
    service: ValidateAPIKeyService,
    api_key_repo: AsyncMock,
    workspace_repo: AsyncMock,
    mock_session: AsyncMock,
) -> None:
    """Missing workspace record raises ValueError('workspace_not_found')."""
    api_key = _make_api_key()
    api_key_repo.get_by_key_hash.return_value = api_key
    workspace_repo.get_by_id.return_value = None

    with pytest.raises(ValueError, match="workspace_not_found"):
        await service.execute(ValidateAPIKeyPayload(raw_key="ps_orphan"), session=mock_session)

"""Unit tests for SeedTemplatesService.

Tests that the service is a safe no-op after Phase 57 consolidation
(legacy RoleTemplate source removed).

Source: Phase 20, P20-07 (modified Phase 57)
"""

from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from pilot_space.application.services.skill_template.seed_templates_service import (
    SeedTemplatesService,
)


@pytest.fixture
def mock_session() -> AsyncMock:
    """Create a mock async session."""
    return AsyncMock()


@pytest.fixture
def service(mock_session: AsyncMock) -> SeedTemplatesService:
    """Create SeedTemplatesService with mock session."""
    return SeedTemplatesService(mock_session)


pytestmark = pytest.mark.asyncio


class TestSeedWorkspace:
    """Tests for SeedTemplatesService.seed_workspace (no-op after Phase 57)."""

    async def test_seed_workspace_is_noop(self, service: SeedTemplatesService) -> None:
        """seed_workspace completes without error (no-op)."""
        workspace_id = uuid4()
        # Should NOT raise — service is a no-op after legacy RoleTemplate removal
        await service.seed_workspace(workspace_id)

    async def test_seed_workspace_does_not_access_db(self, service: SeedTemplatesService) -> None:
        """seed_workspace does not access the database session."""
        workspace_id = uuid4()
        await service.seed_workspace(workspace_id)
        # No DB calls should have been made
        service._session.assert_not_awaited()

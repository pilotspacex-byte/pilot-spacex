"""Tests for ``POST /api/v1/proposals/{id}/revert`` (Phase 89 Plan 05 Task 2).

Contract:

1. Success: 200 + RevertResultEnvelope (camelCase) with proposal, newVersionNumber,
   newHistoryEntry. Bus is invoked with decided_by=current_user.
2. 404 + RFC 7807: ProposalNotFoundError -> error_code='proposal_not_found'.
3. 409 + RFC 7807: ProposalCannotBeRevertedError -> error_code='proposal_cannot_be_reverted'
   (covers both "wrong status" and "window expired" cases — same exception class).
4. No trailing slash on the path (avoids 307 redirects per MEMORY note).
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from dependency_injector import providers
from httpx import ASGITransport, AsyncClient

from pilot_space.application.services.proposal_bus import (
    ProposalBus,
    ProposalCannotBeRevertedError,
    ProposalNotFoundError,
    RevertResult,
)
from pilot_space.application.services.proposal_repository import ProposalRepository
from pilot_space.dependencies.auth import (
    get_current_user,
    get_current_user_id,
    get_session,
)
from pilot_space.dependencies.workspace import (
    get_current_workspace_id,
    require_header_workspace_member,
)
from pilot_space.domain.proposal import (
    ArtifactType,
    ChatMode,
    DiffKind,
    Proposal,
    ProposalStatus,
)

WORKSPACE_ID = UUID("11111111-1111-1111-1111-111111111111")
USER_ID = UUID("22222222-2222-2222-2222-222222222222")


def _make_applied_proposal(**overrides: object) -> Proposal:
    base: dict[str, object] = {
        "id": uuid4(),
        "workspace_id": WORKSPACE_ID,
        "session_id": uuid4(),
        "message_id": uuid4(),
        "target_artifact_type": ArtifactType.ISSUE,
        "target_artifact_id": uuid4(),
        "intent_tool": "update_issue",
        "intent_args": {"title": "after"},
        "diff_kind": DiffKind.FIELDS,
        "diff_payload": {"fields": []},
        "reasoning": "reason",
        "status": ProposalStatus.APPLIED,
        "applied_version": 2,
        "decided_at": datetime.now(UTC),
        "decided_by": USER_ID,
        "created_at": datetime.now(UTC),
        "mode": ChatMode.ACT,
        "accept_disabled": False,
        "persist": True,
        "plan_preview_only": False,
    }
    base.update(overrides)
    return Proposal(**base)  # type: ignore[arg-type]


@pytest.fixture
def mock_bus() -> MagicMock:
    bus = MagicMock(spec=ProposalBus)
    bus.revert_proposal = AsyncMock()
    return bus


@pytest.fixture
def mock_repo() -> MagicMock:
    repo = MagicMock(spec=ProposalRepository)
    repo.list_by_session = AsyncMock()
    return repo


@pytest.fixture
async def client(
    mock_bus: MagicMock, mock_repo: MagicMock
) -> AsyncGenerator[AsyncClient, None]:
    from pilot_space.container import get_container
    from pilot_space.main import app

    async def _noop_session() -> AsyncGenerator[Any, None]:
        yield MagicMock()

    user_stub = MagicMock()
    user_stub.user_id = USER_ID
    user_stub.sub = str(USER_ID)

    app.dependency_overrides[get_session] = _noop_session
    app.dependency_overrides[get_current_user] = lambda: user_stub
    app.dependency_overrides[get_current_user_id] = lambda: USER_ID
    app.dependency_overrides[require_header_workspace_member] = lambda: WORKSPACE_ID
    app.dependency_overrides[get_current_workspace_id] = lambda: WORKSPACE_ID

    container = get_container()
    container.wire(modules=list(container.wiring_config.modules))
    container.proposal_bus.override(providers.Object(mock_bus))
    container.proposal_repository.override(providers.Object(mock_repo))

    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(
            transport=transport,
            base_url="http://testserver",
            headers={"X-Workspace-Id": str(WORKSPACE_ID)},
        ) as ac:
            yield ac
    finally:
        container.proposal_bus.reset_override()
        container.proposal_repository.reset_override()
        app.dependency_overrides.clear()


class TestRevert:
    @pytest.mark.asyncio
    async def test_revert_returns_result_envelope_and_calls_bus(
        self, client: AsyncClient, mock_bus: MagicMock
    ) -> None:
        applied = _make_applied_proposal()
        new_entry = {
            "vN": 2,
            "by": "user",
            "at": datetime.now(UTC).isoformat(),
            "summary": "Reverted v3 → v2",
            "snapshot": {"name": "prev"},
        }
        mock_bus.revert_proposal.return_value = RevertResult(
            proposal=applied,
            new_version_number=3,
            new_history_entry=new_entry,
        )

        res = await client.post(f"/api/v1/proposals/{applied.id}/revert")

        assert res.status_code == 200, res.text
        body = res.json()
        assert body["proposal"]["id"] == str(applied.id)
        assert body["newVersionNumber"] == 3
        assert body["newHistoryEntry"]["by"] == "user"
        assert body["newHistoryEntry"]["vN"] == 2
        mock_bus.revert_proposal.assert_awaited_once_with(
            applied.id, decided_by=USER_ID
        )

    @pytest.mark.asyncio
    async def test_revert_not_found_returns_404_rfc7807(
        self, client: AsyncClient, mock_bus: MagicMock
    ) -> None:
        missing_id = uuid4()
        mock_bus.revert_proposal.side_effect = ProposalNotFoundError(
            f"Proposal {missing_id} not found"
        )

        res = await client.post(f"/api/v1/proposals/{missing_id}/revert")

        assert res.status_code == 404
        assert res.headers["content-type"].startswith("application/problem+json")
        body = res.json()
        assert body.get("error_code") == "proposal_not_found"

    @pytest.mark.asyncio
    async def test_revert_window_expired_returns_409_rfc7807(
        self, client: AsyncClient, mock_bus: MagicMock
    ) -> None:
        pid = uuid4()
        mock_bus.revert_proposal.side_effect = ProposalCannotBeRevertedError(
            f"Revert window expired (10 minutes) for proposal {pid}"
        )

        res = await client.post(f"/api/v1/proposals/{pid}/revert")

        assert res.status_code == 409
        assert res.headers["content-type"].startswith("application/problem+json")
        body = res.json()
        assert body.get("error_code") == "proposal_cannot_be_reverted"

    @pytest.mark.asyncio
    async def test_revert_wrong_status_returns_409_rfc7807(
        self, client: AsyncClient, mock_bus: MagicMock
    ) -> None:
        pid = uuid4()
        mock_bus.revert_proposal.side_effect = ProposalCannotBeRevertedError(
            f"Proposal {pid} cannot be reverted (status=pending, only APPLIED is revertible)"
        )

        res = await client.post(f"/api/v1/proposals/{pid}/revert")

        assert res.status_code == 409
        body = res.json()
        assert body.get("error_code") == "proposal_cannot_be_reverted"

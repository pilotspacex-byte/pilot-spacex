"""Test-only seed endpoint — E2E bootstrap (Phase 94 Plan 03 Phase 2).

POST /api/v1/_test/seed/bootstrap

Guards (enforced by main.py at mount time — this module is always importable):
- ``settings.app_env != "production"``
- ``PILOT_E2E_SEED_ENABLED == "1"``

The router is NOT included in the production application. If someone somehow
calls it in production, the endpoint will not be reachable (router never
mounted). This module itself is side-effect-free at import time.

Authentication: requires a valid Bearer JWT (same Supabase auth as all other
routes). The workspace_id and user_id are taken from the request body; the
caller must be the token holder.

Returns:
    JSON with 6 entity IDs for the spec fixtures.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from pilot_space.application.services.test_seed_service import (
    SeedBootstrapResult,
    SeedBootstrapService,
)
from pilot_space.dependencies.auth import SessionDep, get_current_user_id

router = APIRouter(tags=["_test-seed"])


class SeedBootstrapRequest(BaseModel):
    """Request body for the seed bootstrap endpoint."""

    workspace_id: uuid.UUID
    user_id: uuid.UUID | None = None
    """If omitted, defaults to the authenticated user's ID from the JWT token."""


class SeedBootstrapResponse(BaseModel):
    """Response body — all 6 seeded entity IDs."""

    project_id: uuid.UUID
    task_id: uuid.UUID
    chat_session_id: uuid.UUID
    message_id: uuid.UUID
    artifact_id: uuid.UUID
    pending_proposal_id: uuid.UUID

    @classmethod
    def from_result(cls, result: SeedBootstrapResult) -> SeedBootstrapResponse:
        return cls(
            project_id=result.project_id,
            task_id=result.task_id,
            chat_session_id=result.chat_session_id,
            message_id=result.message_id,
            artifact_id=result.artifact_id,
            pending_proposal_id=result.pending_proposal_id,
        )


@router.post("/seed/bootstrap", response_model=SeedBootstrapResponse)
async def seed_bootstrap(
    body: SeedBootstrapRequest,
    session: SessionDep,
    current_user_id: uuid.UUID = Depends(get_current_user_id),
) -> SeedBootstrapResponse:
    """Atomically create (or reuse) E2E seed entities.

    Idempotent: calling this endpoint multiple times with the same
    workspace_id returns the same entity IDs.

    Entities seeded:
    1. Project (identifier="E2E")
    2. Default workflow states for that project
    3. Issue (task) in Todo state
    4. AISession (agent_name="pilotspace")
    5. AIMessage (role=user, content="seed")
    6. Note (source_chat_session_id=session above)
    7. Proposal (status=pending, targeting the issue)

    Returns all 6 non-state entity IDs.
    """
    user_id = body.user_id or current_user_id

    svc = SeedBootstrapService(
        session=session,
        workspace_id=body.workspace_id,
        user_id=user_id,
    )
    result = await svc.bootstrap()
    await session.commit()
    return SeedBootstrapResponse.from_result(result)


__all__ = ["router"]

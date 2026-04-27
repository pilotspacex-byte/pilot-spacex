"""Test-only seed endpoint — E2E and demo bootstrap.

POST /api/v1/_test/seed/bootstrap

Guards (enforced by main.py at mount time — this module is always importable):
- E2E mode:   ``settings.app_env != "production"`` AND ``PILOT_E2E_SEED_ENABLED == "1"``
- Demo mode:  ``settings.app_env != "production"`` AND ``PILOT_DEMO_SEED_ENABLED == "1"``

The router is mounted when EITHER guard passes. If only one env var is set,
the corresponding mode is allowed and the other returns 403.

Authentication: requires a valid Bearer JWT (same Supabase auth as all other
routes). The workspace_id and user_id are taken from the request body; the
caller must be the token holder.

Returns:
    JSON with seeded entity IDs. Demo mode returns a superset of E2E fields.
"""

from __future__ import annotations

import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from pilot_space.application.services.test_seed_service import (
    DemoSeedBootstrapResult,
    DemoSeedBootstrapService,
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
    mode: str = "e2e"
    """Seed mode: 'e2e' (default — Playwright fixtures) or 'demo' (launchpad demo)."""


class SeedBootstrapResponse(BaseModel):
    """Response body for E2E mode — 6 seeded entity IDs."""

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


class DemoSeedBootstrapResponse(BaseModel):
    """Response body for demo mode — E2E fields plus demo-specific extras."""

    # E2E base fields
    project_id: uuid.UUID
    task_id: uuid.UUID
    chat_session_id: uuid.UUID
    message_id: uuid.UUID
    artifact_id: uuid.UUID
    pending_proposal_id: uuid.UUID
    # Demo extras
    stale_task_ids: list[uuid.UUID]
    demo_chat_session_id: uuid.UUID
    demo_message_user_id: uuid.UUID
    demo_message_assistant_id: uuid.UUID
    demo_artifact_id: uuid.UUID
    digest_id: uuid.UUID

    @classmethod
    def from_result(cls, result: DemoSeedBootstrapResult) -> DemoSeedBootstrapResponse:
        return cls(
            project_id=result.project_id,
            task_id=result.task_id,
            chat_session_id=result.chat_session_id,
            message_id=result.message_id,
            artifact_id=result.artifact_id,
            pending_proposal_id=result.pending_proposal_id,
            stale_task_ids=result.stale_task_ids,
            demo_chat_session_id=result.demo_chat_session_id,
            demo_message_user_id=result.demo_message_user_id,
            demo_message_assistant_id=result.demo_message_assistant_id,
            demo_artifact_id=result.demo_artifact_id,
            digest_id=result.digest_id,
        )


@router.post("/seed/bootstrap")
async def seed_bootstrap(
    body: SeedBootstrapRequest,
    session: SessionDep,
    current_user_id: uuid.UUID = Depends(get_current_user_id),
) -> SeedBootstrapResponse | DemoSeedBootstrapResponse:
    """Atomically create (or reuse) seed entities.

    Supports two modes via the ``mode`` request body field:

    **mode=e2e** (default):
    Idempotent — calling multiple times with the same workspace_id returns the
    same entity IDs. Requires ``PILOT_E2E_SEED_ENABLED=1``.

    Entities seeded:
    1. Project (identifier="E2E")
    2. Default workflow states for that project
    3. Issue (task) in Todo state
    4. AISession (agent_name="pilotspace")
    5. AIMessage (role=user, content="seed")
    6. Note (source_chat_session_id=session above)
    7. Proposal (status=pending, targeting the issue)

    **mode=demo**:
    Seeds everything in E2E mode plus demo-specific entities that populate the
    launchpad RedFlagStrip and ContinueCard. Requires ``PILOT_DEMO_SEED_ENABLED=1``
    (independent from E2E gate).

    Additional entities seeded:
    8. 3 stale Issues (created 21 days ago, state=Todo) — underlying task rows
    9. WorkspaceDigest with 3 stale_issues suggestions — drives RedFlagStrip
    10. AISession "[DEMO SEED] Session" (recent updated_at) — drives ContinueCard
    11. User + assistant AIMessages in the demo session
    12. NOTE artifact linked to the demo session

    Returns all seeded entity IDs. Demo mode returns a superset.
    """
    user_id = body.user_id or current_user_id

    if body.mode == "demo":
        if os.getenv("PILOT_DEMO_SEED_ENABLED") != "1":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Demo seed mode is disabled. Set PILOT_DEMO_SEED_ENABLED=1.",
            )
        svc = DemoSeedBootstrapService(
            session=session,
            workspace_id=body.workspace_id,
            user_id=user_id,
        )
        result = await svc.bootstrap()
        await session.commit()
        return DemoSeedBootstrapResponse.from_result(result)

    # Default: e2e mode
    if os.getenv("PILOT_E2E_SEED_ENABLED") != "1":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="E2E seed mode is disabled. Set PILOT_E2E_SEED_ENABLED=1.",
        )
    svc_e2e = SeedBootstrapService(
        session=session,
        workspace_id=body.workspace_id,
        user_id=user_id,
    )
    result_e2e = await svc_e2e.bootstrap()
    await session.commit()
    return SeedBootstrapResponse.from_result(result_e2e)


__all__ = ["router"]

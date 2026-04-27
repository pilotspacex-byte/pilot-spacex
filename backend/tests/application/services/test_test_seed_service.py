"""Tests for TestSeedService — E2E bootstrap entity creation.

Red → Green TDD:

1. RED: test_bootstrap_creates_all_entities — verifies 7 entity types
2. RED: test_bootstrap_is_idempotent — second call returns same IDs
3. RED: test_bootstrap_fk_linkage — verifies FK relationships are consistent

Uses SQLite in-memory DB (default conftest fixture). RLS and pgvector
are not exercised; this is a structural FK-linkage test only.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pilot_space.application.services.test_seed_service import (
    _NOTE_TITLE,
    _PROJECT_IDENTIFIER,
    _SESSION_TITLE,
    _TASK_NAME,
    SeedBootstrapResult,
    SeedBootstrapService,
)
from pilot_space.infrastructure.database.models.ai_message import AIMessage
from pilot_space.infrastructure.database.models.ai_session import AISession
from pilot_space.infrastructure.database.models.issue import Issue
from pilot_space.infrastructure.database.models.note import Note
from pilot_space.infrastructure.database.models.project import Project
from pilot_space.infrastructure.database.models.proposal import ProposalModel
from pilot_space.infrastructure.database.models.state import State, StateGroup
from pilot_space.infrastructure.database.models.user import User
from pilot_space.infrastructure.database.models.workspace import Workspace

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def workspace(db_session: AsyncSession) -> Workspace:
    """Create a minimal workspace for seeding."""
    ws = Workspace(
        id=uuid4(),
        name="E2E Test Workspace",
        slug="e2e-test",
        created_at=datetime.now(tz=UTC),
        updated_at=datetime.now(tz=UTC),
    )
    db_session.add(ws)
    await db_session.flush()
    return ws


@pytest.fixture
async def user(db_session: AsyncSession) -> User:
    """Create a minimal user for seeding."""
    u = User(
        id=uuid4(),
        email="seed@e2e.test",
        created_at=datetime.now(tz=UTC),
        updated_at=datetime.now(tz=UTC),
    )
    db_session.add(u)
    await db_session.flush()
    return u


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bootstrap_creates_all_entities(
    db_session: AsyncSession,
    workspace: Workspace,
    user: User,
) -> None:
    """Bootstrap creates project, states, issue, session, message, note, proposal."""
    svc = SeedBootstrapService(
        session=db_session,
        workspace_id=workspace.id,
        user_id=user.id,
    )
    result = await svc.bootstrap()

    # Verify return type
    assert isinstance(result, SeedBootstrapResult)

    # Project exists
    proj_row = await db_session.get(Project, result.project_id)
    assert proj_row is not None
    assert proj_row.identifier == _PROJECT_IDENTIFIER
    assert proj_row.workspace_id == workspace.id

    # Default states created for project
    states_stmt = select(State).where(
        State.project_id == result.project_id,
        State.is_deleted == False,  # noqa: E712
    )
    states_result = await db_session.execute(states_stmt)
    states = states_result.scalars().all()
    assert len(states) >= 1
    state_names = {s.name for s in states}
    assert "Todo" in state_names

    # Issue exists
    issue_row = await db_session.get(Issue, result.task_id)
    assert issue_row is not None
    assert issue_row.name == _TASK_NAME
    assert issue_row.project_id == result.project_id
    assert issue_row.reporter_id == user.id

    # AISession exists
    session_row = await db_session.get(AISession, result.chat_session_id)
    assert session_row is not None
    assert session_row.agent_name == "pilotspace"
    assert session_row.title == _SESSION_TITLE
    assert session_row.workspace_id == workspace.id

    # AIMessage exists and linked to session
    message_row = await db_session.get(AIMessage, result.message_id)
    assert message_row is not None
    assert message_row.session_id == result.chat_session_id
    assert message_row.content == "seed"

    # Note exists and linked to session
    note_row = await db_session.get(Note, result.artifact_id)
    assert note_row is not None
    assert note_row.title == _NOTE_TITLE
    assert note_row.source_chat_session_id == result.chat_session_id
    assert note_row.workspace_id == workspace.id

    # Proposal exists and linked to session + issue
    proposal_row = await db_session.get(ProposalModel, result.pending_proposal_id)
    assert proposal_row is not None
    assert proposal_row.status == "pending"
    assert proposal_row.session_id == result.chat_session_id
    assert proposal_row.message_id == result.message_id
    assert proposal_row.target_artifact_type == "ISSUE"
    assert proposal_row.target_artifact_id == result.task_id
    assert proposal_row.workspace_id == workspace.id


@pytest.mark.asyncio
async def test_bootstrap_is_idempotent(
    db_session: AsyncSession,
    workspace: Workspace,
    user: User,
) -> None:
    """Second bootstrap call returns identical IDs — no duplicates created."""
    svc = SeedBootstrapService(
        session=db_session,
        workspace_id=workspace.id,
        user_id=user.id,
    )

    first = await svc.bootstrap()
    second = await svc.bootstrap()

    assert first.project_id == second.project_id
    assert first.task_id == second.task_id
    assert first.chat_session_id == second.chat_session_id
    assert first.message_id == second.message_id
    assert first.artifact_id == second.artifact_id
    assert first.pending_proposal_id == second.pending_proposal_id

    # Only one project row with identifier E2E
    proj_stmt = select(Project).where(
        Project.workspace_id == workspace.id,
        Project.identifier == _PROJECT_IDENTIFIER,
    )
    proj_result = await db_session.execute(proj_stmt)
    projects = proj_result.scalars().all()
    assert len(projects) == 1

    # Only one pending proposal
    prop_stmt = select(ProposalModel).where(
        ProposalModel.workspace_id == workspace.id,
        ProposalModel.status == "pending",
    )
    prop_result = await db_session.execute(prop_stmt)
    proposals = prop_result.scalars().all()
    assert len(proposals) == 1


@pytest.mark.asyncio
async def test_bootstrap_fk_linkage(
    db_session: AsyncSession,
    workspace: Workspace,
    user: User,
) -> None:
    """FK chain is consistent: proposal.session_id == session.id, etc."""
    svc = SeedBootstrapService(
        session=db_session,
        workspace_id=workspace.id,
        user_id=user.id,
    )
    result = await svc.bootstrap()

    # All IDs are distinct (no accidental aliasing)
    ids = [
        result.project_id,
        result.task_id,
        result.chat_session_id,
        result.message_id,
        result.artifact_id,
        result.pending_proposal_id,
    ]
    assert len(ids) == len(set(ids)), "All returned IDs must be distinct"

    # Proposal → session consistency
    proposal = await db_session.get(ProposalModel, result.pending_proposal_id)
    assert proposal is not None
    assert proposal.session_id == result.chat_session_id
    assert proposal.message_id == result.message_id
    assert proposal.target_artifact_id == result.task_id

    # Note → session consistency
    note = await db_session.get(Note, result.artifact_id)
    assert note is not None
    assert note.source_chat_session_id == result.chat_session_id

    # Issue → project consistency
    issue = await db_session.get(Issue, result.task_id)
    assert issue is not None
    assert issue.project_id == result.project_id
    assert issue.reporter_id == user.id

    # Issue state belongs to same project
    state = await db_session.get(State, issue.state_id)
    assert state is not None
    assert state.project_id == result.project_id
    assert state.group in (StateGroup.UNSTARTED, StateGroup.STARTED)

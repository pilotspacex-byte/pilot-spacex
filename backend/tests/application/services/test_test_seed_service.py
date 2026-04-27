"""Tests for TestSeedService — E2E and demo bootstrap entity creation.

Red → Green TDD:

E2E mode:
1. RED: test_bootstrap_creates_all_entities — verifies 7 entity types
2. RED: test_bootstrap_is_idempotent — second call returns same IDs
3. RED: test_bootstrap_fk_linkage — verifies FK relationships are consistent

Demo mode (E-01):
4. RED: test_demo_bootstrap_creates_stale_issues — 3 issues, 21-day offset
5. RED: test_demo_bootstrap_creates_digest — WorkspaceDigest with stale_issues category
6. RED: test_demo_bootstrap_creates_recent_session — demo session + 2 messages + note
7. RED: test_demo_bootstrap_is_idempotent — re-run reuses issues/session, replaces digest
8. RED: test_demo_digest_suggestion_shape — JSONB shape matches GetDigestService reader

Uses SQLite in-memory DB (default conftest fixture). RLS and pgvector
are not exercised; this is a structural FK-linkage test only.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pilot_space.application.services.test_seed_service import (
    _DEMO_DIGEST_GENERATED_BY,
    _DEMO_SESSION_TITLE,
    _DEMO_STALE_AGE_DAYS,
    _DEMO_STALE_TASK_COUNT,
    _NOTE_TITLE,
    _PROJECT_IDENTIFIER,
    _SESSION_TITLE,
    _TASK_NAME,
    DemoSeedBootstrapResult,
    DemoSeedBootstrapService,
    SeedBootstrapResult,
    SeedBootstrapService,
)
from pilot_space.infrastructure.database.models.ai_message import AIMessage, MessageRole
from pilot_space.infrastructure.database.models.ai_session import AISession
from pilot_space.infrastructure.database.models.issue import Issue
from pilot_space.infrastructure.database.models.note import Note
from pilot_space.infrastructure.database.models.project import Project
from pilot_space.infrastructure.database.models.proposal import ProposalModel
from pilot_space.infrastructure.database.models.state import State, StateGroup
from pilot_space.infrastructure.database.models.user import User
from pilot_space.infrastructure.database.models.workspace import Workspace
from pilot_space.infrastructure.database.models.workspace_digest import WorkspaceDigest

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


# ===========================================================================
# Demo mode tests (E-01)
# ===========================================================================


@pytest.mark.asyncio
async def test_demo_bootstrap_creates_stale_issues(
    db_session: AsyncSession,
    workspace: Workspace,
    user: User,
) -> None:
    """Demo bootstrap seeds exactly 3 stale issues with 21-day-old timestamps."""
    svc = DemoSeedBootstrapService(
        session=db_session,
        workspace_id=workspace.id,
        user_id=user.id,
    )
    result = await svc.bootstrap()

    assert isinstance(result, DemoSeedBootstrapResult)
    assert len(result.stale_task_ids) == _DEMO_STALE_TASK_COUNT

    # Threshold is naive (SQLite stores datetimes without tz) or aware (PostgreSQL).
    # Use naive comparison to be DB-agnostic in unit tests.
    stale_threshold = datetime.now() - timedelta(days=_DEMO_STALE_AGE_DAYS - 1)  # noqa: DTZ005
    for task_id in result.stale_task_ids:
        issue = await db_session.get(Issue, task_id)
        assert issue is not None, f"Stale issue {task_id} not found"
        assert issue.name.startswith("[DEMO SEED] Stale Task"), issue.name
        assert issue.workspace_id == workspace.id
        assert issue.project_id == result.project_id
        assert issue.is_deleted is False
        # created_at must be older than threshold (at least _DEMO_STALE_AGE_DAYS ago).
        # Strip tz for SQLite compatibility (SQLite stores naive datetimes).
        created = issue.created_at.replace(tzinfo=None) if issue.created_at.tzinfo else issue.created_at
        assert created <= stale_threshold, (
            f"Expected created_at <= {stale_threshold}, got {created}"
        )


@pytest.mark.asyncio
async def test_demo_bootstrap_creates_digest(
    db_session: AsyncSession,
    workspace: Workspace,
    user: User,
) -> None:
    """Demo bootstrap creates a WorkspaceDigest row with stale_issues suggestions."""
    svc = DemoSeedBootstrapService(
        session=db_session,
        workspace_id=workspace.id,
        user_id=user.id,
    )
    result = await svc.bootstrap()

    digest = await db_session.get(WorkspaceDigest, result.digest_id)
    assert digest is not None
    assert digest.workspace_id == workspace.id
    assert digest.generated_by == _DEMO_DIGEST_GENERATED_BY
    assert len(digest.suggestions) == _DEMO_STALE_TASK_COUNT

    for suggestion in digest.suggestions:
        assert suggestion["category"] == "stale_issues"
        assert "id" in suggestion
        assert "title" in suggestion
        assert "description" in suggestion
        assert "entity_id" in suggestion
        assert "entity_type" in suggestion
        assert "relevance_score" in suggestion


@pytest.mark.asyncio
async def test_demo_digest_suggestion_shape(
    db_session: AsyncSession,
    workspace: Workspace,
    user: User,
) -> None:
    """Each suggestion JSONB dict contains all fields read by GetDigestService._filter_suggestions."""
    svc = DemoSeedBootstrapService(
        session=db_session,
        workspace_id=workspace.id,
        user_id=user.id,
    )
    result = await svc.bootstrap()

    digest = await db_session.get(WorkspaceDigest, result.digest_id)
    assert digest is not None

    required_keys = {
        "id",
        "category",
        "title",
        "description",
        "entity_id",
        "entity_type",
        "relevance_score",
    }
    for suggestion in digest.suggestions:
        missing = required_keys - suggestion.keys()
        assert not missing, f"Suggestion missing keys: {missing}"
        # entity_id must be a valid UUID string (used by dismissal filter)
        from uuid import UUID as _UUID

        _UUID(suggestion["entity_id"])  # raises ValueError if invalid
        # relevance_score must be float in [0, 1]
        score = suggestion["relevance_score"]
        assert isinstance(score, float), f"relevance_score must be float, got {type(score)}"
        assert 0.0 <= score <= 1.0, f"relevance_score out of range: {score}"


@pytest.mark.asyncio
async def test_demo_bootstrap_creates_recent_session(
    db_session: AsyncSession,
    workspace: Workspace,
    user: User,
) -> None:
    """Demo bootstrap creates a session with 2 messages and 1 NOTE artifact."""
    svc = DemoSeedBootstrapService(
        session=db_session,
        workspace_id=workspace.id,
        user_id=user.id,
    )
    result = await svc.bootstrap()

    # Session exists with correct title
    demo_session = await db_session.get(AISession, result.demo_chat_session_id)
    assert demo_session is not None
    assert demo_session.title == _DEMO_SESSION_TITLE
    assert demo_session.workspace_id == workspace.id
    assert demo_session.user_id == user.id

    # User message exists
    user_msg = await db_session.get(AIMessage, result.demo_message_user_id)
    assert user_msg is not None
    assert user_msg.session_id == result.demo_chat_session_id
    assert user_msg.role == MessageRole.USER

    # Assistant message exists
    assistant_msg = await db_session.get(AIMessage, result.demo_message_assistant_id)
    assert assistant_msg is not None
    assert assistant_msg.session_id == result.demo_chat_session_id
    assert assistant_msg.role == MessageRole.ASSISTANT

    # NOTE artifact linked to demo session
    demo_note = await db_session.get(Note, result.demo_artifact_id)
    assert demo_note is not None
    assert demo_note.source_chat_session_id == result.demo_chat_session_id
    assert demo_note.workspace_id == workspace.id


@pytest.mark.asyncio
async def test_demo_bootstrap_is_idempotent(
    db_session: AsyncSession,
    workspace: Workspace,
    user: User,
) -> None:
    """Re-running demo bootstrap reuses stale issues + session; replaces digest.

    Idempotency contract:
    - stale_task_ids: same IDs on second call (no duplicates)
    - demo_chat_session_id: same session reused
    - digest_id: MAY differ (digest is replaced for freshness), but only ONE
      demo_seed digest row exists after both calls.
    """
    svc = DemoSeedBootstrapService(
        session=db_session,
        workspace_id=workspace.id,
        user_id=user.id,
    )

    first = await svc.bootstrap()
    second = await svc.bootstrap()

    # E2E base entities are stable
    assert first.project_id == second.project_id
    assert first.task_id == second.task_id
    assert first.chat_session_id == second.chat_session_id

    # Stale issues are reused (no duplicates)
    assert set(first.stale_task_ids) == set(second.stale_task_ids), (
        "Stale task IDs should be the same on re-run"
    )

    # Demo session is reused
    assert first.demo_chat_session_id == second.demo_chat_session_id

    # Only one demo_seed digest row exists after both runs
    digest_stmt = select(WorkspaceDigest).where(
        WorkspaceDigest.workspace_id == workspace.id,
        WorkspaceDigest.generated_by == _DEMO_DIGEST_GENERATED_BY,
        WorkspaceDigest.is_deleted == False,  # noqa: E712
    )
    digest_result = await db_session.execute(digest_stmt)
    digests = digest_result.scalars().all()
    assert len(digests) == 1, (
        f"Expected exactly 1 demo_seed digest, found {len(digests)}"
    )

    # Exactly 3 stale tasks in the workspace (no duplicates from second run)
    stale_stmt = select(Issue).where(
        Issue.workspace_id == workspace.id,
        Issue.name.like("[DEMO SEED] Stale Task%"),
        Issue.is_deleted == False,  # noqa: E712
    )
    stale_result = await db_session.execute(stale_stmt)
    stale_issues = stale_result.scalars().all()
    assert len(stale_issues) == _DEMO_STALE_TASK_COUNT, (
        f"Expected {_DEMO_STALE_TASK_COUNT} stale tasks, found {len(stale_issues)}"
    )

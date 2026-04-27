"""Test-only seed service for E2E bootstrapping (Phase 94 Plan 03 Phase 2).

Creates a canonical set of linked entities in a single transaction so that
Playwright specs that require a pending proposal + chat session + artifact
can run without manual setup.

PRODUCTION SAFETY:
- This module is ALWAYS importable (no runtime guard here).
- The router (``api/v1/routers/_test_seed.py``) is only mounted when
  ``settings.app_env != "production"`` AND ``PILOT_E2E_SEED_ENABLED == "1"``.
- Even if someone bypasses the router guard, this service performs benign
  DB inserts only — no destructive side-effects.

Entities created (idempotent — matched by sentinel titles):
1. Project  — identifier "E2E", name "[E2E SEED] Project"
2. States   — default workflow states for the project (via ProjectRepository)
3. Issue    — name "[E2E SEED] Task", reporter=user, state=Todo, project above
4. AISession — agent_name="pilotspace", title="[E2E SEED] Session", expires 24h
5. AIMessage — role=user, content="seed", session above
6. Note     — title="[E2E SEED] Chat Note", source_chat_session_id=session above
7. Proposal — status=pending, target=ISSUE/issue above, session/message above
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pilot_space.domain.proposal import ArtifactType, ChatMode, DiffKind, ProposalStatus
from pilot_space.infrastructure.database.models.ai_message import AIMessage, MessageRole
from pilot_space.infrastructure.database.models.ai_session import AISession
from pilot_space.infrastructure.database.models.issue import Issue, IssuePriority
from pilot_space.infrastructure.database.models.note import Note
from pilot_space.infrastructure.database.models.project import Project
from pilot_space.infrastructure.database.models.proposal import ProposalModel
from pilot_space.infrastructure.database.models.state import (
    DEFAULT_STATES,
    State,
    StateGroup,
)
from pilot_space.infrastructure.database.repositories.project_repository import (
    ProjectRepository,
)

# Sentinel strings used for idempotency lookups.
_PROJECT_IDENTIFIER = "E2E"
_PROJECT_NAME = "[E2E SEED] Project"
_TASK_NAME = "[E2E SEED] Task"
_SESSION_TITLE = "[E2E SEED] Session"
_NOTE_TITLE = "[E2E SEED] Chat Note"
_STATE_TODO_NAME = "Todo"


@dataclass
class SeedBootstrapResult:
    """Ids returned to the caller (global-setup.ts writes them to seed-context.json)."""

    project_id: uuid.UUID
    task_id: uuid.UUID
    chat_session_id: uuid.UUID
    message_id: uuid.UUID
    artifact_id: uuid.UUID  # Note.id (NOTE artifact type)
    pending_proposal_id: uuid.UUID


class SeedBootstrapService:
    """E2E bootstrap service — creates 7 linked entities atomically.

    Usage (from router)::

        svc = TestSeedService(session, workspace_id=..., user_id=...)
        result = await svc.bootstrap()

    The caller must commit (or rely on the surrounding transaction). Each call
    is idempotent: if a matching entity already exists it is reused rather than
    duplicated, and the same IDs are returned.
    """

    def __init__(
        self,
        session: AsyncSession,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        self._session = session
        self._workspace_id = workspace_id
        self._user_id = user_id

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def bootstrap(self) -> SeedBootstrapResult:
        """Create (or reuse) all seed entities in the correct FK order.

        Steps:
        1. Project + default states
        2. Resolve Todo state from project states
        3. Issue (task)
        4. AISession
        5. AIMessage
        6. Note (NOTE artifact)
        7. Proposal (pending)
        """
        project = await self._get_or_create_project()
        await self._session.flush()

        todo_state = await self._get_todo_state(project.id)

        issue = await self._get_or_create_issue(project, todo_state)
        await self._session.flush()

        ai_session = await self._get_or_create_ai_session()
        await self._session.flush()

        ai_message = await self._get_or_create_ai_message(ai_session.id)
        await self._session.flush()

        note = await self._get_or_create_note(ai_session.id)
        await self._session.flush()

        proposal = await self._get_or_create_proposal(
            session_id=ai_session.id,
            message_id=ai_message.id,
            target_issue_id=issue.id,
        )
        await self._session.flush()

        return SeedBootstrapResult(
            project_id=project.id,
            task_id=issue.id,
            chat_session_id=ai_session.id,
            message_id=ai_message.id,
            artifact_id=note.id,
            pending_proposal_id=proposal.id,
        )

    # ------------------------------------------------------------------
    # Step helpers
    # ------------------------------------------------------------------

    async def _get_or_create_project(self) -> Project:
        stmt = select(Project).where(
            Project.workspace_id == self._workspace_id,
            Project.identifier == _PROJECT_IDENTIFIER,
            Project.is_deleted == False,  # noqa: E712
        )
        result = await self._session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            return existing

        project = Project(
            workspace_id=self._workspace_id,
            name=_PROJECT_NAME,
            identifier=_PROJECT_IDENTIFIER,
            description="Auto-seeded project for E2E tests",
        )
        # Use repository to create project WITH default states in one flush.
        repo = ProjectRepository(session=self._session)
        return await repo.create_with_default_states(project)

    async def _get_todo_state(self, project_id: uuid.UUID) -> State:
        stmt = select(State).where(
            State.workspace_id == self._workspace_id,
            State.project_id == project_id,
            State.name == _STATE_TODO_NAME,
            State.is_deleted == False,  # noqa: E712
        )
        result = await self._session.execute(stmt)
        state = result.scalar_one_or_none()
        if state:
            return state

        # Fallback: look for any UNSTARTED state in this project.
        stmt2 = select(State).where(
            State.workspace_id == self._workspace_id,
            State.project_id == project_id,
            State.group == StateGroup.UNSTARTED,
            State.is_deleted == False,  # noqa: E712
        )
        result2 = await self._session.execute(stmt2)
        fallback = result2.scalars().first()
        if fallback:
            return fallback

        # Last resort: create a Todo state directly.
        todo_data = next(
            (s for s in DEFAULT_STATES if s["name"] == _STATE_TODO_NAME), DEFAULT_STATES[1]
        )
        new_state = State(
            workspace_id=self._workspace_id,
            project_id=project_id,
            name=str(todo_data["name"]),
            color=str(todo_data["color"]),
            group=todo_data["group"],  # type: ignore[arg-type]
            sequence=int(todo_data["sequence"]),
        )
        self._session.add(new_state)
        await self._session.flush()
        return new_state

    async def _get_or_create_issue(self, project: Project, state: State) -> Issue:
        stmt = select(Issue).where(
            Issue.workspace_id == self._workspace_id,
            Issue.project_id == project.id,
            Issue.name == _TASK_NAME,
            Issue.is_deleted == False,  # noqa: E712
        )
        result = await self._session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            return existing

        # Compute next sequence_id within the project.
        from sqlalchemy import func

        seq_stmt = select(func.coalesce(func.max(Issue.sequence_id), 0)).where(
            Issue.project_id == project.id,
        )
        seq_result = await self._session.execute(seq_stmt)
        next_seq: int = (seq_result.scalar() or 0) + 1

        issue = Issue(
            workspace_id=self._workspace_id,
            project_id=project.id,
            name=_TASK_NAME,
            sequence_id=next_seq,
            state_id=state.id,
            reporter_id=self._user_id,
            priority=IssuePriority.NONE,
            sort_order=0,
            version_number=1,
            version_history=[],
        )
        self._session.add(issue)
        return issue

    async def _get_or_create_ai_session(self) -> AISession:
        stmt = select(AISession).where(
            AISession.workspace_id == self._workspace_id,
            AISession.user_id == self._user_id,
            AISession.agent_name == "pilotspace",
            AISession.title == _SESSION_TITLE,
        )
        result = await self._session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            return existing

        ai_session = AISession(
            id=uuid.uuid4(),  # explicit to support SQLite in tests (no gen_random_uuid())
            workspace_id=self._workspace_id,
            user_id=self._user_id,
            agent_name="pilotspace",
            title=_SESSION_TITLE,
            session_data={},
            expires_at=datetime.now(tz=UTC) + timedelta(days=1),
        )
        self._session.add(ai_session)
        return ai_session

    async def _get_or_create_ai_message(self, session_id: uuid.UUID) -> AIMessage:
        stmt = select(AIMessage).where(
            AIMessage.session_id == session_id,
            AIMessage.role == MessageRole.USER,
            AIMessage.content == "seed",
        )
        result = await self._session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            return existing

        ai_message = AIMessage(
            id=uuid.uuid4(),  # explicit to support SQLite in tests (no gen_random_uuid())
            session_id=session_id,
            role=MessageRole.USER,
            content="seed",
        )
        self._session.add(ai_message)
        return ai_message

    async def _get_or_create_note(self, source_chat_session_id: uuid.UUID) -> Note:
        stmt = select(Note).where(
            Note.workspace_id == self._workspace_id,
            Note.title == _NOTE_TITLE,
            Note.is_deleted == False,  # noqa: E712
        )
        result = await self._session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            return existing

        note = Note(
            workspace_id=self._workspace_id,
            title=_NOTE_TITLE,
            content={},
            owner_id=self._user_id,
            source_chat_session_id=source_chat_session_id,
        )
        self._session.add(note)
        return note

    async def _get_or_create_proposal(
        self,
        session_id: uuid.UUID,
        message_id: uuid.UUID,
        target_issue_id: uuid.UUID,
    ) -> ProposalModel:
        stmt = select(ProposalModel).where(
            ProposalModel.workspace_id == self._workspace_id,
            ProposalModel.session_id == session_id,
            ProposalModel.status == ProposalStatus.PENDING.value,
        )
        result = await self._session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            return existing

        proposal = ProposalModel(
            id=uuid.uuid4(),
            workspace_id=self._workspace_id,
            session_id=session_id,
            message_id=message_id,
            target_artifact_type=ArtifactType.ISSUE.value,
            target_artifact_id=target_issue_id,
            intent_tool="update_issue",
            intent_args={"name": "[E2E SEED] Updated Task"},
            diff_kind=DiffKind.FIELDS.value,
            diff_payload={"name": {"from": _TASK_NAME, "to": "[E2E SEED] Updated Task"}},
            reasoning="E2E test seed proposal",
            status=ProposalStatus.PENDING.value,
            mode=ChatMode.ACT.value,
            accept_disabled=False,
            persist=True,
            plan_preview_only=False,
        )
        self._session.add(proposal)
        return proposal


__all__ = ["SeedBootstrapResult", "SeedBootstrapService"]

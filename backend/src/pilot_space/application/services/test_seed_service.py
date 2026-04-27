"""Test-only seed service for E2E and demo bootstrapping.

Creates a canonical set of linked entities in a single transaction so that
Playwright specs that require a pending proposal + chat session + artifact
can run without manual setup.

PRODUCTION SAFETY:
- This module is ALWAYS importable (no runtime guard here).
- The router (``api/v1/routers/_test_seed.py``) is only mounted when
  ``settings.app_env != "production"`` AND ``PILOT_E2E_SEED_ENABLED == "1"``
  (E2E mode) or ``PILOT_DEMO_SEED_ENABLED == "1"`` (demo mode).
- Even if someone bypasses the router guard, this service performs benign
  DB inserts only — no destructive side-effects.

E2E mode entities created (idempotent — matched by sentinel titles):
1. Project  — identifier "E2E", name "[E2E SEED] Project"
2. States   — default workflow states for the project (via ProjectRepository)
3. Issue    — name "[E2E SEED] Task", reporter=user, state=Todo, project above
4. AISession — agent_name="pilotspace", title="[E2E SEED] Session", expires 24h
5. AIMessage — role=user, content="seed", session above
6. Note     — title="[E2E SEED] Chat Note", source_chat_session_id=session above
7. Proposal — status=pending, target=ISSUE/issue above, session/message above

Demo mode entities created (idempotent — matched by [DEMO SEED] sentinels):
Same base entities, PLUS:
8. 3 stale Issues  — state=Todo, created_at=now-21d, name "[DEMO SEED] Stale Task {n}"
9. WorkspaceDigest — generated_by="demo_seed", suggestions=[3x stale_issues items]
10. AISession      — title="[DEMO SEED] Session", updated_at=now (triggers ContinueCard)
11. 2 AIMessages   — user + assistant in the demo session
12. Note artifact  — linked to demo session
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
from pilot_space.infrastructure.database.models.workspace_digest import WorkspaceDigest
from pilot_space.infrastructure.database.repositories.project_repository import (
    ProjectRepository,
)

# Sentinel strings used for idempotency lookups — E2E mode.
_PROJECT_IDENTIFIER = "E2E"
_PROJECT_NAME = "[E2E SEED] Project"
_TASK_NAME = "[E2E SEED] Task"
_SESSION_TITLE = "[E2E SEED] Session"
_NOTE_TITLE = "[E2E SEED] Chat Note"
_STATE_TODO_NAME = "Todo"

# Sentinel strings used for idempotency lookups — demo mode.
_DEMO_PROJECT_IDENTIFIER = "DEMO"
_DEMO_PROJECT_NAME = "[DEMO SEED] Project"
_DEMO_SESSION_TITLE = "[DEMO SEED] Session"
_DEMO_NOTE_TITLE = "[DEMO SEED] Chat Note"
# generated_by sentinel stored in WorkspaceDigest; max 20 chars (col constraint).
_DEMO_DIGEST_GENERATED_BY = "demo_seed"
# How many stale tasks to seed and how old to make them.
_DEMO_STALE_TASK_COUNT = 3
_DEMO_STALE_AGE_DAYS = 21


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


@dataclass
class DemoSeedBootstrapResult:
    """IDs returned to the caller for demo mode bootstrap.

    Contains all E2E result fields plus demo-specific extras:
    - stale_task_ids: 3 issues seeded 21 days old (feed RedFlagStrip via digest)
    - demo_chat_session_id: recently-updated session (feeds ContinueCard)
    - demo_artifact_id: NOTE artifact linked to the demo session
    - digest_id: WorkspaceDigest row with stale_issues suggestions
    """

    project_id: uuid.UUID
    task_id: uuid.UUID
    chat_session_id: uuid.UUID
    message_id: uuid.UUID
    artifact_id: uuid.UUID
    pending_proposal_id: uuid.UUID
    # Demo-specific extras
    stale_task_ids: list[uuid.UUID]
    demo_chat_session_id: uuid.UUID
    demo_message_user_id: uuid.UUID
    demo_message_assistant_id: uuid.UUID
    demo_artifact_id: uuid.UUID
    digest_id: uuid.UUID


class DemoSeedBootstrapService:
    """Demo bootstrap service — extends E2E seed with launchpad-populated entities.

    Builds on top of :class:`SeedBootstrapService` (reuses the same project /
    state fan-out) and then seeds:

    1. 3 stale issues (state=Todo, created_at=now-21d) — underlying tasks for
       the digest suggestions. Seeded so ``/{slug}/tasks?filter=stale`` lands
       on real rows.
    2. A ``WorkspaceDigest`` row with ``generated_by="demo_seed"`` containing
       3 ``stale_issues`` suggestions — this is the **actual** data source for
       ``RedFlagStrip`` (the strip reads digest.suggestions, NOT issue rows).
    3. A fresh ``AISession`` with ``title="[DEMO SEED] Session"`` whose
       ``updated_at`` is *now* — surfaces as the top result in
       ``GET /ai/sessions?limit=1`` (ordered by ``updated_at DESC``), which
       drives ``ContinueCard``.
    4. A user message + assistant message in the demo session.
    5. A NOTE artifact linked to the demo session.

    Idempotency strategy:
    - Issues and session: matched by sentinel title.
    - WorkspaceDigest: the existing demo_seed row is deleted and replaced on
      each call so ``generated_at`` stays fresh and the strip never shows a
      "stale" demo digest.

    Dismissal note:
    - If a user dismisses a seeded stale_issues flag, it stays dismissed across
      re-seeds. ``GetDigestService._filter_suggestions`` filters by
      ``(entity_id, category)`` and the demo stale issue UUIDs are stable
      (matched by sentinel title). Re-inserting the digest row does NOT restore
      dismissed suggestions — dismissals must be manually cleared from the
      ``DigestDismissal`` table to make flags reappear.
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

    async def bootstrap(self) -> DemoSeedBootstrapResult:
        """Create (or reuse) all demo seed entities in FK order.

        Steps:
        1. Run the E2E bootstrap to guarantee project/state/issue/session exist.
        2. Seed 3 stale issues (state=Todo, created_at 21 days ago).
        3. Delete existing demo_seed digest for this workspace, then insert fresh one.
        4. Seed demo AI session (recent updated_at).
        5. Seed user + assistant messages in demo session.
        6. Seed NOTE artifact linked to demo session.
        """
        # Step 1: reuse E2E base
        e2e_svc = SeedBootstrapService(
            session=self._session,
            workspace_id=self._workspace_id,
            user_id=self._user_id,
        )
        e2e_result = await e2e_svc.bootstrap()
        await self._session.flush()

        # Step 2: stale tasks — resolve Todo state directly (avoids accessing private method).
        todo_state = await self._resolve_todo_state(e2e_result.project_id)
        stale_issues = await self._get_or_create_stale_issues(
            project=await self._session.get(
                Project, e2e_result.project_id
            ),  # type: ignore[arg-type]
            state=todo_state,
        )
        await self._session.flush()

        # Step 3: fresh WorkspaceDigest with stale_issues suggestions
        digest = await self._replace_demo_digest(stale_issues)
        await self._session.flush()

        # Step 4: demo AI session (recent)
        demo_session = await self._get_or_create_demo_ai_session()
        await self._session.flush()

        # Step 5: messages
        user_msg = await self._get_or_create_demo_message(
            session_id=demo_session.id,
            role=MessageRole.USER,
            content="Show me what's happening in this workspace",
        )
        assistant_msg = await self._get_or_create_demo_message(
            session_id=demo_session.id,
            role=MessageRole.ASSISTANT,
            content=(
                "Here's a quick summary of your workspace activity. "
                "I can see 3 tasks that haven't moved in over 3 weeks — "
                "let me know if you'd like me to help triage them."
            ),
        )
        await self._session.flush()

        # Step 6: demo NOTE artifact
        demo_note = await self._get_or_create_demo_note(demo_session.id)
        await self._session.flush()

        return DemoSeedBootstrapResult(
            # E2E base
            project_id=e2e_result.project_id,
            task_id=e2e_result.task_id,
            chat_session_id=e2e_result.chat_session_id,
            message_id=e2e_result.message_id,
            artifact_id=e2e_result.artifact_id,
            pending_proposal_id=e2e_result.pending_proposal_id,
            # Demo extras
            stale_task_ids=[i.id for i in stale_issues],
            demo_chat_session_id=demo_session.id,
            demo_message_user_id=user_msg.id,
            demo_message_assistant_id=assistant_msg.id,
            demo_artifact_id=demo_note.id,
            digest_id=digest.id,
        )

    # ------------------------------------------------------------------
    # Step helpers
    # ------------------------------------------------------------------

    async def _resolve_todo_state(self, project_id: uuid.UUID) -> State:
        """Resolve the Todo state for the given project.

        Mirrors SeedBootstrapService._get_todo_state logic without accessing
        private members of that class.
        """
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

        # Fallback: any UNSTARTED state
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

        # Last resort: create Todo state inline
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

    async def _get_or_create_stale_issues(
        self,
        project: Project,
        state: State,
    ) -> list[Issue]:
        """Get or create 3 stale tasks (created 21 days ago, state=Todo)."""
        from sqlalchemy import func

        issues: list[Issue] = []
        stale_created_at = datetime.now(tz=UTC) - timedelta(days=_DEMO_STALE_AGE_DAYS)

        for n in range(1, _DEMO_STALE_TASK_COUNT + 1):
            name = f"[DEMO SEED] Stale Task {n}"
            stmt = select(Issue).where(
                Issue.workspace_id == self._workspace_id,
                Issue.project_id == project.id,
                Issue.name == name,
                Issue.is_deleted == False,  # noqa: E712
            )
            result = await self._session.execute(stmt)
            existing = result.scalar_one_or_none()
            if existing:
                issues.append(existing)
                continue

            seq_stmt = select(func.coalesce(func.max(Issue.sequence_id), 0)).where(
                Issue.project_id == project.id,
            )
            seq_result = await self._session.execute(seq_stmt)
            next_seq: int = (seq_result.scalar() or 0) + 1

            issue = Issue(
                workspace_id=self._workspace_id,
                project_id=project.id,
                name=name,
                sequence_id=next_seq,
                state_id=state.id,
                reporter_id=self._user_id,
                priority=IssuePriority.NONE,
                sort_order=n,
                version_number=1,
                version_history=[],
                created_at=stale_created_at,
                updated_at=stale_created_at,
            )
            self._session.add(issue)
            # Flush each so the next max(sequence_id) query sees the row.
            await self._session.flush()
            issues.append(issue)

        return issues

    async def _replace_demo_digest(self, stale_issues: list[Issue]) -> WorkspaceDigest:
        """Delete any existing demo_seed digest, then insert a fresh one.

        Using delete+insert (rather than upsert) ensures ``generated_at``
        always reflects the seed timestamp and the strip never looks stale.

        The suggestions JSONB shape must match what GetDigestService._filter_suggestions
        reads: id, category, title, description, entity_id, entity_type,
        entity_identifier, project_id, project_name, action_type, action_label,
        action_url, relevance_score.
        """
        from sqlalchemy import delete

        # Delete existing demo digest rows for this workspace.
        await self._session.execute(
            delete(WorkspaceDigest).where(
                WorkspaceDigest.workspace_id == self._workspace_id,
                WorkspaceDigest.generated_by == _DEMO_DIGEST_GENERATED_BY,
                WorkspaceDigest.is_deleted == False,  # noqa: E712
            )
        )
        await self._session.flush()

        suggestions = [
            {
                "id": str(uuid.uuid4()),
                "category": "stale_issues",
                "title": f"{issue.name} hasn't moved in 3 weeks",
                "description": (
                    "This task has been in Todo state for over 21 days "
                    "with no updates. Consider reassigning or closing it."
                ),
                "entity_id": str(issue.id),
                "entity_type": "issue",
                "entity_identifier": None,
                "project_id": str(issue.project_id),
                "project_name": None,
                "action_type": "view_issue",
                "action_label": "View task",
                "action_url": None,
                "relevance_score": round(0.9 - (0.05 * i), 2),
            }
            for i, issue in enumerate(stale_issues)
        ]

        digest = WorkspaceDigest(
            workspace_id=self._workspace_id,
            generated_by=_DEMO_DIGEST_GENERATED_BY,
            suggestions=suggestions,
        )
        self._session.add(digest)
        await self._session.flush()
        return digest

    async def _get_or_create_demo_ai_session(self) -> AISession:
        """Get or create the demo AI session.

        Updated_at is intentionally left as server default (now()) so the
        session sorts to the top of GET /ai/sessions?limit=1 (ordered by
        updated_at DESC), which drives ContinueCard.
        """
        stmt = select(AISession).where(
            AISession.workspace_id == self._workspace_id,
            AISession.user_id == self._user_id,
            AISession.agent_name == "pilotspace",
            AISession.title == _DEMO_SESSION_TITLE,
        )
        result = await self._session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            return existing

        demo_session = AISession(
            id=uuid.uuid4(),
            workspace_id=self._workspace_id,
            user_id=self._user_id,
            agent_name="pilotspace",
            title=_DEMO_SESSION_TITLE,
            session_data={},
            expires_at=datetime.now(tz=UTC) + timedelta(days=30),
        )
        self._session.add(demo_session)
        return demo_session

    async def _get_or_create_demo_message(
        self,
        session_id: uuid.UUID,
        role: MessageRole,
        content: str,
    ) -> AIMessage:
        """Get or create a demo message (matched by session_id + role + content)."""
        stmt = select(AIMessage).where(
            AIMessage.session_id == session_id,
            AIMessage.role == role,
            AIMessage.content == content,
        )
        result = await self._session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            return existing

        msg = AIMessage(
            id=uuid.uuid4(),
            session_id=session_id,
            role=role,
            content=content,
        )
        self._session.add(msg)
        return msg

    async def _get_or_create_demo_note(self, source_chat_session_id: uuid.UUID) -> Note:
        """Get or create the demo NOTE artifact linked to the demo session."""
        stmt = select(Note).where(
            Note.workspace_id == self._workspace_id,
            Note.title == _DEMO_NOTE_TITLE,
            Note.is_deleted == False,  # noqa: E712
        )
        result = await self._session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            return existing

        note = Note(
            workspace_id=self._workspace_id,
            title=_DEMO_NOTE_TITLE,
            content={},
            owner_id=self._user_id,
            source_chat_session_id=source_chat_session_id,
        )
        self._session.add(note)
        return note


__all__ = [
    "DemoSeedBootstrapResult",
    "DemoSeedBootstrapService",
    "SeedBootstrapResult",
    "SeedBootstrapService",
]

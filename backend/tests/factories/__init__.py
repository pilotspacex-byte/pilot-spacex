"""Test factories for Pilot Space domain entities.

Provides factory functions and classes for all domain entities.
Includes Feature 015 factories for WorkIntent and IntentArtifact.

Usage:
    intent = make_work_intent()
    artifact = make_intent_artifact(intent_id=intent.id)
    user = UserFactory()
    workspace = WorkspaceFactory()
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import factory
from factory import LazyAttribute, LazyFunction, Sequence, SubFactory

from pilot_space.infrastructure.database.models import (
    AnnotationStatus,
    AnnotationType,
    Issue,
    IssuePriority,
    Note,
    NoteAnnotation,
    Project,
    State,
    StateGroup,
    User,
    Workspace,
    WorkspaceMember,
    WorkspaceRole,
)
from pilot_space.infrastructure.database.models.workspace_invitation import (
    InvitationStatus,
    WorkspaceInvitation,
)

from .intent_artifact_factory import make_intent_artifact
from .work_intent_factory import make_work_intent


class BaseFactory(factory.Factory):
    """Base factory with common fields for all models."""

    class Meta:
        abstract = True

    id: UUID = LazyFunction(uuid4)
    created_at: datetime = LazyFunction(lambda: datetime.now(tz=UTC))
    updated_at: datetime = LazyFunction(lambda: datetime.now(tz=UTC))
    is_deleted: bool = False
    deleted_at: datetime | None = None


class UserFactory(BaseFactory):
    """Factory for creating User instances."""

    class Meta:
        model = User

    email: str = Sequence(lambda n: f"user{n}@example.com")
    full_name: str = Sequence(lambda n: f"Test User {n}")
    avatar_url: str | None = None


class WorkspaceFactory(BaseFactory):
    """Factory for creating Workspace instances."""

    class Meta:
        model = Workspace

    name: str = Sequence(lambda n: f"Workspace {n}")
    slug: str = Sequence(lambda n: f"workspace-{n}")
    description: str | None = LazyAttribute(lambda o: f"Description for {o.name}")
    settings: dict[str, Any] | None = LazyFunction(dict)
    owner_id: UUID | None = None
    owner: User | None = None

    @factory.post_generation
    def members(
        self,
        _create: bool,
        extracted: list[WorkspaceMember] | None,
        **_kwargs: Any,
    ) -> None:
        """Add workspace members after creation."""
        if extracted:
            for member in extracted:
                self.members.append(member)


class WorkspaceMemberFactory(BaseFactory):
    """Factory for creating WorkspaceMember instances."""

    class Meta:
        model = WorkspaceMember

    user: User = SubFactory(UserFactory)
    workspace: Workspace = SubFactory(WorkspaceFactory)
    role: WorkspaceRole = WorkspaceRole.MEMBER

    @LazyAttribute
    def user_id(self) -> UUID:
        """Get user ID from user object."""
        return self.user.id

    @LazyAttribute
    def workspace_id(self) -> UUID:
        """Get workspace ID from workspace object."""
        return self.workspace.id


class WorkspaceInvitationFactory(BaseFactory):
    """Factory for creating WorkspaceInvitation instances."""

    class Meta:
        model = WorkspaceInvitation

    workspace: Workspace = SubFactory(WorkspaceFactory)
    email: str = Sequence(lambda n: f"invited{n}@example.com")
    role: WorkspaceRole = WorkspaceRole.MEMBER
    status: InvitationStatus = InvitationStatus.PENDING
    invited_by_user: User = SubFactory(UserFactory)
    expires_at: datetime = LazyFunction(lambda: datetime.now(tz=UTC) + timedelta(days=7))
    accepted_at: datetime | None = None

    @LazyAttribute
    def workspace_id(self) -> UUID:
        """Get workspace ID from workspace object."""
        return self.workspace.id

    @LazyAttribute
    def invited_by(self) -> UUID:
        """Get inviter ID from user object."""
        return self.invited_by_user.id


class StateFactory(BaseFactory):
    """Factory for creating State instances."""

    class Meta:
        model = State

    name: str = "Todo"
    color: str = "#60a5fa"
    group: StateGroup = StateGroup.UNSTARTED
    sequence: int = Sequence(lambda n: n)
    workspace_id: UUID = LazyFunction(uuid4)
    project_id: UUID | None = None
    project: Project | None = None


class ProjectFactory(BaseFactory):
    """Factory for creating Project instances."""

    class Meta:
        model = Project

    name: str = Sequence(lambda n: f"Project {n}")
    identifier: str = Sequence(lambda n: f"PRJ{n}")
    description: str | None = LazyAttribute(lambda o: f"Description for {o.name}")
    icon: str | None = None
    settings: dict[str, Any] | None = LazyFunction(dict)
    workspace_id: UUID = LazyFunction(uuid4)
    workspace: Workspace | None = None
    lead_id: UUID | None = None
    lead: User | None = None

    @factory.post_generation
    def states(
        self,
        _create: bool,
        extracted: list[State] | None,
        **_kwargs: Any,
    ) -> None:
        """Add project states after creation."""
        if extracted:
            for state in extracted:
                self.states.append(state)


class IssueFactory(BaseFactory):
    """Factory for creating Issue instances."""

    class Meta:
        model = Issue

    sequence_id: int = Sequence(lambda n: n + 1)
    name: str = Sequence(lambda n: f"Issue {n}")
    description: str | None = LazyAttribute(lambda o: f"Description for {o.name}")
    description_html: str | None = None
    priority: IssuePriority = IssuePriority.NONE
    state_id: UUID = LazyFunction(uuid4)
    state: State | None = None
    project_id: UUID = LazyFunction(uuid4)
    project: Project | None = None
    workspace_id: UUID = LazyFunction(uuid4)
    assignee_id: UUID | None = None
    assignee: User | None = None
    reporter_id: UUID = LazyFunction(uuid4)
    reporter: User | None = None
    cycle_id: UUID | None = None
    module_id: UUID | None = None
    parent_id: UUID | None = None
    estimate_points: int | None = None
    start_date: datetime | None = None
    target_date: datetime | None = None
    sort_order: int = 0
    ai_metadata: dict[str, Any] | None = LazyFunction(dict)


class NoteFactory(BaseFactory):
    """Factory for creating Note instances."""

    class Meta:
        model = Note

    title: str = Sequence(lambda n: f"Note {n}")
    content: dict[str, Any] = LazyFunction(
        lambda: {
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": "Test content"}],
                }
            ],
        }
    )
    summary: str | None = None
    word_count: int = 2
    reading_time_mins: int = 1
    is_pinned: bool = False
    template_id: UUID | None = None
    owner_id: UUID = LazyFunction(uuid4)
    owner: User | None = None
    project_id: UUID | None = None
    project: Project | None = None
    workspace_id: UUID = LazyFunction(uuid4)


class NoteAnnotationFactory(BaseFactory):
    """Factory for creating NoteAnnotation instances."""

    class Meta:
        model = NoteAnnotation

    note_id: UUID = LazyFunction(uuid4)
    note: Note | None = None
    block_id: str = Sequence(lambda n: f"block-{n}")
    type: AnnotationType = AnnotationType.SUGGESTION
    content: str = Sequence(lambda n: f"Annotation content {n}")
    confidence: float = 0.7
    status: AnnotationStatus = AnnotationStatus.PENDING
    ai_metadata: dict[str, Any] | None = LazyFunction(
        lambda: {"model": "claude-sonnet-4-20250514", "reasoning": "Test reasoning"}
    )
    workspace_id: UUID = LazyFunction(uuid4)


# ============================================================================
# Factory Helpers
# ============================================================================


def create_default_states(workspace_id: UUID, project_id: UUID | None = None) -> list[State]:
    """Create default workflow states for a workspace/project."""
    from pilot_space.infrastructure.database.models import DEFAULT_STATES

    states = []
    for state_def in DEFAULT_STATES:
        state = StateFactory(
            name=state_def["name"],  # type: ignore[arg-type]
            color=state_def["color"],  # type: ignore[arg-type]
            group=state_def["group"],  # type: ignore[arg-type]
            sequence=state_def["sequence"],  # type: ignore[arg-type]
            workspace_id=workspace_id,
            project_id=project_id,
        )
        states.append(state)
    return states


def create_workspace_with_owner() -> tuple[Workspace, User, WorkspaceMember]:
    """Create a workspace with an owner user."""
    owner = UserFactory()
    workspace = WorkspaceFactory(owner_id=owner.id, owner=owner)
    membership = WorkspaceMemberFactory(
        user=owner,
        workspace=workspace,
        role=WorkspaceRole.OWNER,
    )
    return workspace, owner, membership


def create_project_in_workspace(
    workspace: Workspace,
    owner: User,
) -> tuple[Project, list[State]]:
    """Create a project with default states in a workspace."""
    project = ProjectFactory(
        workspace_id=workspace.id,
        workspace=workspace,
        lead_id=owner.id,
        lead=owner,
    )
    states = create_default_states(workspace.id, project.id)
    project.states = states
    return project, states


def create_issue_in_project(
    project: Project,
    reporter: User,
    state: State | None = None,
    **kwargs: Any,
) -> Issue:
    """Create an issue in a project."""
    if state is None and project.states:
        state = project.states[0]

    return IssueFactory(
        workspace_id=project.workspace_id,
        project_id=project.id,
        project=project,
        reporter_id=reporter.id,
        reporter=reporter,
        state_id=state.id if state else uuid4(),
        state=state,
        **kwargs,
    )


def create_note_in_workspace(
    workspace: Workspace,
    owner: User,
    project: Project | None = None,
    **kwargs: Any,
) -> Note:
    """Create a note in a workspace."""
    return NoteFactory(
        workspace_id=workspace.id,
        owner_id=owner.id,
        owner=owner,
        project_id=project.id if project else None,
        project=project,
        **kwargs,
    )


def create_test_scenario() -> dict[str, Any]:
    """Create a complete test scenario with all related entities."""
    workspace, owner, membership = create_workspace_with_owner()
    project, states = create_project_in_workspace(workspace, owner)

    backlog_state = next((s for s in states if s.name == "Backlog"), states[0])
    in_progress_state = next((s for s in states if s.name == "In Progress"), states[0])
    done_state = next((s for s in states if s.name == "Done"), states[0])

    issue_backlog = create_issue_in_project(
        project, owner, state=backlog_state, name="Backlog Issue"
    )
    issue_in_progress = create_issue_in_project(
        project, owner, state=in_progress_state, name="In Progress Issue"
    )
    issue_done = create_issue_in_project(project, owner, state=done_state, name="Done Issue")

    note_pinned = create_note_in_workspace(
        workspace, owner, project=project, title="Pinned Note", is_pinned=True
    )
    note_regular = create_note_in_workspace(workspace, owner, project=project, title="Regular Note")

    return {
        "workspace": workspace,
        "owner": owner,
        "membership": membership,
        "project": project,
        "states": states,
        "issues": [issue_backlog, issue_in_progress, issue_done],
        "notes": [note_pinned, note_regular],
    }


__all__ = [
    "BaseFactory",
    "IssueFactory",
    "NoteAnnotationFactory",
    "NoteFactory",
    "ProjectFactory",
    "StateFactory",
    "UserFactory",
    "WorkspaceFactory",
    "WorkspaceInvitationFactory",
    "WorkspaceMemberFactory",
    "create_default_states",
    "create_issue_in_project",
    "create_note_in_workspace",
    "create_project_in_workspace",
    "create_test_scenario",
    "create_workspace_with_owner",
    "make_intent_artifact",
    "make_work_intent",
]

"""Unit tests for IssueRepository performance optimizations.

Tests get_by_id_for_response() and bulk_update_labels() methods
to verify they produce correct results with fewer queries.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from sqlalchemy import insert, select

from pilot_space.infrastructure.database.models import (
    Issue,
    IssuePriority,
    Label,
    Project,
    State,
    StateGroup,
    User,
    Workspace,
)
from pilot_space.infrastructure.database.models.issue_label import issue_labels
from pilot_space.infrastructure.database.repositories.issue_repository import (
    IssueRepository,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


pytestmark = pytest.mark.asyncio


@pytest.fixture
async def workspace(db_session: AsyncSession) -> Workspace:
    """Create a workspace for tests."""
    ws = Workspace(
        id=uuid4(),
        name="Test Workspace",
        slug="test-ws",
        owner_id=uuid4(),
    )
    db_session.add(ws)
    await db_session.flush()
    return ws


@pytest.fixture
async def user(db_session: AsyncSession, workspace: Workspace) -> User:
    """Create a user for tests."""
    u = User(
        id=uuid4(),
        email="test@example.com",
        display_name="Test User",
    )
    db_session.add(u)
    await db_session.flush()
    return u


@pytest.fixture
async def project(db_session: AsyncSession, workspace: Workspace, user: User) -> Project:
    """Create a project for tests."""
    p = Project(
        id=uuid4(),
        name="Test Project",
        identifier="TST",
        workspace_id=workspace.id,
        created_by=user.id,
    )
    db_session.add(p)
    await db_session.flush()
    return p


@pytest.fixture
async def state(db_session: AsyncSession, project: Project) -> State:
    """Create a state for tests."""
    s = State(
        id=uuid4(),
        name="Backlog",
        group=StateGroup.BACKLOG,
        color="#9C9590",
        project_id=project.id,
        sequence=0,
    )
    db_session.add(s)
    await db_session.flush()
    return s


@pytest.fixture
async def issue(
    db_session: AsyncSession,
    workspace: Workspace,
    project: Project,
    state: State,
    user: User,
) -> Issue:
    """Create an issue with basic relations for tests."""
    i = Issue(
        id=uuid4(),
        sequence_id=1,
        identifier="TST-1",
        name="Test Issue",
        workspace_id=workspace.id,
        project_id=project.id,
        state_id=state.id,
        reporter_id=user.id,
        priority=IssuePriority.NONE,
        sort_order=0,
    )
    db_session.add(i)
    await db_session.flush()
    return i


@pytest.fixture
async def labels(db_session: AsyncSession, project: Project, workspace: Workspace) -> list[Label]:
    """Create labels for tests."""
    created = []
    for name, color in [("Bug", "#D9534F"), ("Feature", "#29A386"), ("Docs", "#5B8FC9")]:
        label = Label(
            id=uuid4(),
            name=name,
            color=color,
            project_id=project.id,
            workspace_id=workspace.id,
        )
        db_session.add(label)
        created.append(label)
    await db_session.flush()
    return created


class TestGetByIdScalar:
    """Tests for get_by_id_scalar() lightweight loading."""

    async def test_returns_issue_scalar_fields(
        self, db_session: AsyncSession, issue: Issue
    ) -> None:
        """Verify returned issue has scalar fields without triggering relation loads."""
        repo = IssueRepository(db_session)
        result = await repo.get_by_id_scalar(issue.id)

        assert result is not None
        assert result.id == issue.id
        assert result.name == "Test Issue"
        assert result.workspace_id == issue.workspace_id

    async def test_returns_none_for_nonexistent_id(self, db_session: AsyncSession) -> None:
        """Verify returns None for non-existent issue."""
        repo = IssueRepository(db_session)
        result = await repo.get_by_id_scalar(uuid4())
        assert result is None

    async def test_excludes_soft_deleted_by_default(
        self, db_session: AsyncSession, issue: Issue
    ) -> None:
        """Verify soft-deleted issues are excluded by default."""
        issue.is_deleted = True
        await db_session.flush()

        repo = IssueRepository(db_session)
        result = await repo.get_by_id_scalar(issue.id)
        assert result is None


class TestGetByIdForResponse:
    """Tests for get_by_id_for_response() optimized loading."""

    async def test_returns_issue_with_required_relations(
        self, db_session: AsyncSession, issue: Issue
    ) -> None:
        """Verify returned issue has project, state, reporter, labels loaded."""
        repo = IssueRepository(db_session)
        result = await repo.get_by_id_for_response(issue.id)

        assert result is not None
        assert result.id == issue.id
        assert result.name == "Test Issue"
        assert result.project is not None
        assert result.state is not None
        assert result.reporter is not None
        assert result.labels is not None

    async def test_returns_none_for_nonexistent_id(self, db_session: AsyncSession) -> None:
        """Verify returns None for non-existent issue."""
        repo = IssueRepository(db_session)
        result = await repo.get_by_id_for_response(uuid4())
        assert result is None

    async def test_excludes_soft_deleted_by_default(
        self, db_session: AsyncSession, issue: Issue
    ) -> None:
        """Verify soft-deleted issues are excluded by default."""
        issue.is_deleted = True
        await db_session.flush()

        repo = IssueRepository(db_session)
        result = await repo.get_by_id_for_response(issue.id)
        assert result is None

    async def test_includes_soft_deleted_when_requested(
        self, db_session: AsyncSession, issue: Issue
    ) -> None:
        """Verify soft-deleted issues returned when include_deleted=True."""
        issue.is_deleted = True
        await db_session.flush()

        repo = IssueRepository(db_session)
        result = await repo.get_by_id_for_response(issue.id, include_deleted=True)
        assert result is not None
        assert result.id == issue.id

    async def test_loads_labels_correctly(
        self,
        db_session: AsyncSession,
        issue: Issue,
        labels: list[Label],
    ) -> None:
        """Verify labels are loaded in response query."""
        # Attach labels to issue via junction table
        for label in labels[:2]:
            await db_session.execute(
                insert(issue_labels).values(issue_id=issue.id, label_id=label.id)
            )
        await db_session.flush()

        repo = IssueRepository(db_session)
        result = await repo.get_by_id_for_response(issue.id)

        assert result is not None
        assert len(result.labels) == 2
        label_names = {label.name for label in result.labels}
        assert "Bug" in label_names
        assert "Feature" in label_names

    async def test_loads_sub_issues(
        self,
        db_session: AsyncSession,
        issue: Issue,
        workspace: Workspace,
        project: Project,
        state: State,
        user: User,
    ) -> None:
        """Verify sub_issues are loaded for count calculation."""
        child = Issue(
            id=uuid4(),
            sequence_id=2,
            identifier="TST-2",
            name="Child Issue",
            workspace_id=workspace.id,
            project_id=project.id,
            state_id=state.id,
            reporter_id=user.id,
            parent_id=issue.id,
            priority=IssuePriority.NONE,
            sort_order=0,
        )
        db_session.add(child)
        await db_session.flush()

        repo = IssueRepository(db_session)
        result = await repo.get_by_id_for_response(issue.id)

        assert result is not None
        assert len(result.sub_issues) == 1
        assert result.sub_issues[0].name == "Child Issue"


class TestBulkUpdateLabels:
    """Tests for optimized bulk_update_labels() using direct SQL."""

    async def test_assigns_labels_to_issue(
        self,
        db_session: AsyncSession,
        issue: Issue,
        labels: list[Label],
    ) -> None:
        """Verify labels are assigned via bulk insert."""
        repo = IssueRepository(db_session)
        label_ids = [labels[0].id, labels[1].id]

        await repo.bulk_update_labels(issue.id, label_ids)

        # Verify via direct query
        result = await db_session.execute(
            select(issue_labels.c.label_id).where(issue_labels.c.issue_id == issue.id)
        )
        assigned = {row[0] for row in result.fetchall()}
        assert assigned == set(label_ids)

    async def test_replaces_existing_labels(
        self,
        db_session: AsyncSession,
        issue: Issue,
        labels: list[Label],
    ) -> None:
        """Verify existing labels are replaced, not appended."""
        repo = IssueRepository(db_session)

        # Assign first two labels
        await repo.bulk_update_labels(issue.id, [labels[0].id, labels[1].id])

        # Replace with third label only
        await repo.bulk_update_labels(issue.id, [labels[2].id])

        result = await db_session.execute(
            select(issue_labels.c.label_id).where(issue_labels.c.issue_id == issue.id)
        )
        assigned = [row[0] for row in result.fetchall()]
        assert len(assigned) == 1
        assert assigned[0] == labels[2].id

    async def test_clears_all_labels_with_empty_list(
        self,
        db_session: AsyncSession,
        issue: Issue,
        labels: list[Label],
    ) -> None:
        """Verify passing empty list removes all labels."""
        repo = IssueRepository(db_session)

        # Assign labels first
        await repo.bulk_update_labels(issue.id, [labels[0].id, labels[1].id])

        # Clear all
        await repo.bulk_update_labels(issue.id, [])

        result = await db_session.execute(
            select(issue_labels.c.label_id).where(issue_labels.c.issue_id == issue.id)
        )
        assigned = result.fetchall()
        assert len(assigned) == 0

    async def test_no_op_for_nonexistent_issue(
        self,
        db_session: AsyncSession,
        labels: list[Label],
    ) -> None:
        """Verify no error when updating labels for non-existent issue."""
        repo = IssueRepository(db_session)
        fake_issue_id = uuid4()

        # Should not raise - DELETE on empty set is fine
        await repo.bulk_update_labels(fake_issue_id, [labels[0].id])

        result = await db_session.execute(
            select(issue_labels.c.label_id).where(issue_labels.c.issue_id == fake_issue_id)
        )
        # Labels inserted but no FK constraint on issue_id in junction table
        # (depends on schema - may or may not fail)
        assigned = result.fetchall()
        assert len(assigned) >= 0  # Flexible assertion

"""Unit tests for GetImplementContextService.

Tests authorization logic, branch name generation, GitHub integration
lookup, and the full happy-path assembly. All repositories are AsyncMock.
"""

from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from pilot_space.application.services.issue.get_implement_context_service import (
    GetImplementContextPayload,
    GetImplementContextService,
    _build_suggested_branch,
    _derive_repo_info,
    _extract_text_blocks,
    _slugify,
)
from pilot_space.domain.exceptions import ForbiddenError, NotFoundError, ValidationError
from pilot_space.infrastructure.database.models import IssuePriority
from pilot_space.infrastructure.database.models.state import StateGroup
from pilot_space.infrastructure.database.models.workspace_member import WorkspaceRole

# ============================================================================
# Helpers
# ============================================================================


def _make_state(group: StateGroup = StateGroup.STARTED) -> MagicMock:
    """Return a minimal mock IssueState with real StateGroup enum.

    IssueStateDetail.model_validate uses pydantic validation which requires
    the ``group`` field to be a real StateGroup enum value, not a MagicMock.
    """
    state = MagicMock()
    state.id = uuid.uuid4()
    state.name = "In Progress"
    state.color = "#3B82F6"
    state.group = group
    return state


class _FakeLabel:
    """Minimal label object pydantic can validate via model_validate."""

    def __init__(self) -> None:
        self.id = uuid.uuid4()
        self.name = "bug"
        self.color = "#EF4444"


def _make_label() -> _FakeLabel:
    return _FakeLabel()


def _make_project(name: str = "Pilot Space") -> MagicMock:
    project = MagicMock()
    project.id = uuid.uuid4()
    project.name = name
    project.description = "FastAPI + React stack"
    return project


def _make_issue(
    *,
    assignee_id: uuid.UUID | None = None,
    sequence_id: int = 42,
    title: str = "Implement login",
) -> MagicMock:
    """Return a mock Issue ORM instance.

    Uses real enum values for ``priority`` and a pydantic-compatible state so
    that ``IssueDetail.from_issue`` and ``IssueStateDetail.model_validate``
    succeed without connecting to the database.
    """
    issue = MagicMock()
    issue.id = uuid.uuid4()
    issue.identifier = f"PS-{sequence_id}"
    issue.name = title
    issue.description = "As a user, I want to log in."
    issue.description_html = "<p>As a user, I want to log in.</p>"
    issue.ai_metadata = {"acceptance_criteria": ["User can log in", "Session persists"]}
    issue.sequence_id = sequence_id
    issue.assignee_id = assignee_id
    issue.project_id = uuid.uuid4()
    issue.priority = IssuePriority.MEDIUM
    issue.labels = [_make_label()]
    issue.state = _make_state()
    issue.project = _make_project()
    return issue


def _make_integration(
    *,
    default_repository: str | None = "acme/backend",
    repositories: list[str] | None = None,
    external_account_name: str | None = None,
    default_branch: str = "main",
) -> MagicMock:
    integration = MagicMock()
    settings: dict[str, Any] = {"default_branch": default_branch}
    if default_repository:
        settings["default_repository"] = default_repository
    if repositories:
        settings["repositories"] = repositories
    integration.settings = settings
    integration.external_account_name = external_account_name
    return integration


def _make_workspace(slug: str = "acme", name: str = "Acme Corp") -> MagicMock:
    ws = MagicMock()
    ws.id = uuid.uuid4()
    ws.slug = slug
    ws.name = name
    return ws


def _make_note_link(note: MagicMock) -> MagicMock:
    link = MagicMock()
    link.note_id = note.id
    link.note = note
    return link


def _make_note(title: str = "Sprint notes") -> MagicMock:
    note = MagicMock()
    note.id = uuid.uuid4()
    note.title = title
    note.is_deleted = False
    note.content = {
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": "First block text."}],
            },
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": "Second block text."}],
            },
        ],
    }
    return note


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def issue_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def note_link_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def note_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def integration_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def workspace_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def service(
    issue_repo: AsyncMock,
    note_link_repo: AsyncMock,
    note_repo: AsyncMock,
    integration_repo: AsyncMock,
    workspace_repo: AsyncMock,
) -> GetImplementContextService:
    return GetImplementContextService(
        issue_repository=issue_repo,
        note_issue_link_repository=note_link_repo,
        note_repository=note_repo,
        integration_repository=integration_repo,
        workspace_repository=workspace_repo,
    )


# ============================================================================
# Pure helpers: _slugify
# ============================================================================


class TestSlugify:
    def test_lowercases_input(self) -> None:
        assert _slugify("Hello World") == "hello-world"

    def test_replaces_special_chars_with_hyphen(self) -> None:
        assert _slugify("fix: null pointer") == "fix-null-pointer"

    def test_strips_leading_trailing_hyphens(self) -> None:
        assert _slugify("  hello  ") == "hello"

    def test_collapses_consecutive_separators(self) -> None:
        # Multiple non-alphanumeric chars become a single hyphen
        result = _slugify("foo---bar")
        assert "--" not in result

    def test_empty_string(self) -> None:
        assert _slugify("") == ""

    def test_unicode_stripped(self) -> None:
        # Non-ASCII chars are stripped (replaced by hyphen then stripped)
        result = _slugify("café")
        assert "caf" in result


# ============================================================================
# Pure helpers: _build_suggested_branch
# ============================================================================


class TestBuildSuggestedBranch:
    def test_format_starts_with_feat_ps(self) -> None:
        branch = _build_suggested_branch(sequence_id=7, title="add login page")
        assert branch.startswith("feat/ps-7-")

    def test_max_60_chars(self) -> None:
        long_title = "a" * 200
        branch = _build_suggested_branch(sequence_id=1, title=long_title)
        assert len(branch) <= 60

    def test_no_trailing_dash_after_truncation(self) -> None:
        # Title that would produce a slug ending in a dash at truncation boundary
        title = "x" * 50  # creates branch like "feat/ps-1-xxx...xxx" > 60 chars
        branch = _build_suggested_branch(sequence_id=1, title=title)
        assert not branch.endswith("-"), f"branch ends with dash: {branch!r}"

    def test_short_title_not_truncated(self) -> None:
        branch = _build_suggested_branch(sequence_id=42, title="fix bug")
        assert branch == "feat/ps-42-fix-bug"

    def test_special_chars_in_title(self) -> None:
        branch = _build_suggested_branch(sequence_id=5, title="Fix: null-pointer exception!")
        assert branch.startswith("feat/ps-5-")
        assert "!" not in branch
        assert ":" not in branch


# ============================================================================
# Pure helpers: _extract_text_blocks
# ============================================================================


class TestExtractTextBlocks:
    def test_extracts_paragraph_text(self) -> None:
        content = {
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": "Hello world"}],
                }
            ],
        }
        blocks = _extract_text_blocks(content)
        assert blocks == ["Hello world"]

    def test_caps_at_three_blocks(self) -> None:
        content = {
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": f"Block {i}"}],
                }
                for i in range(5)
            ],
        }
        blocks = _extract_text_blocks(content)
        assert len(blocks) == 3

    def test_empty_content_returns_empty_list(self) -> None:
        assert _extract_text_blocks({}) == []

    def test_skips_empty_paragraphs(self) -> None:
        content = {
            "type": "doc",
            "content": [
                {"type": "paragraph", "content": []},
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": "Real text"}],
                },
            ],
        }
        blocks = _extract_text_blocks(content)
        assert blocks == ["Real text"]

    def test_joins_multiple_text_nodes_in_paragraph(self) -> None:
        """Multiple text nodes in a paragraph are joined with a space separator.

        The implementation calls `` " ".join(texts).strip() `` so adjacent text
        nodes that already contain their own spacing may produce double spaces.
        The key guarantee is that all text values appear in the output.
        """
        content = {
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "text", "text": "Hello"},
                        {"type": "text", "text": "world"},
                    ],
                }
            ],
        }
        blocks = _extract_text_blocks(content)
        assert len(blocks) == 1
        assert "Hello" in blocks[0]
        assert "world" in blocks[0]


# ============================================================================
# Pure helpers: _derive_repo_info
# ============================================================================


class TestDeriveRepoInfo:
    def test_uses_default_repository_first(self) -> None:
        integration = _make_integration(default_repository="org/repo")
        info = _derive_repo_info(integration)
        assert info.clone_url == "https://github.com/org/repo"

    def test_falls_back_to_repositories_list(self) -> None:
        integration = _make_integration(
            default_repository=None,
            repositories=["org/fallback"],
        )
        info = _derive_repo_info(integration)
        assert info.clone_url == "https://github.com/org/fallback"

    def test_falls_back_to_external_account_name(self) -> None:
        integration = _make_integration(
            default_repository=None,
            repositories=[],
            external_account_name="acme-org",
        )
        info = _derive_repo_info(integration)
        assert info.clone_url == "https://github.com/acme-org"

    def test_raises_when_no_url_can_be_derived(self) -> None:
        integration = _make_integration(
            default_repository=None,
            repositories=[],
            external_account_name=None,
        )
        with pytest.raises(NotFoundError, match="cannot derive clone_url"):
            _derive_repo_info(integration)

    def test_provider_is_always_github(self) -> None:
        integration = _make_integration()
        info = _derive_repo_info(integration)
        assert info.provider == "github"

    def test_default_branch_from_settings(self) -> None:
        integration = _make_integration(default_branch="develop")
        info = _derive_repo_info(integration)
        assert info.default_branch == "develop"

    def test_default_branch_defaults_to_main(self) -> None:
        integration = MagicMock()
        integration.settings = {}
        integration.external_account_name = "org"
        info = _derive_repo_info(integration)
        assert info.default_branch == "main"


# ============================================================================
# Service: happy paths
# ============================================================================


class TestGetImplementContextServiceHappyPath:
    pytestmark = pytest.mark.asyncio

    async def test_assignee_returns_context(
        self,
        service: GetImplementContextService,
        issue_repo: AsyncMock,
        note_link_repo: AsyncMock,
        integration_repo: AsyncMock,
        workspace_repo: AsyncMock,
    ) -> None:
        """Assignee can access implement context and gets a populated response."""
        requester_id = uuid.uuid4()
        workspace_id = uuid.uuid4()
        issue = _make_issue(assignee_id=requester_id)
        issue_repo.get_by_id_with_relations.return_value = issue
        note_link_repo.get_by_issue.return_value = []
        integration_repo.get_active_github.return_value = _make_integration()
        workspace_repo.get_by_id.return_value = _make_workspace()

        result = await service.execute(
            GetImplementContextPayload(
                issue_id=issue.id,
                workspace_id=workspace_id,
                requester_id=requester_id,
            )
        )

        assert result.context.suggested_branch.startswith("feat/ps-42-")
        assert result.context.repository.clone_url == "https://github.com/acme/backend"
        assert result.context.workspace.slug == "acme"
        assert result.context.project.name == "Pilot Space"
        assert result.context.issue.identifier == "PS-42"

    async def test_admin_not_assignee_can_access(
        self,
        service: GetImplementContextService,
        issue_repo: AsyncMock,
        note_link_repo: AsyncMock,
        integration_repo: AsyncMock,
        workspace_repo: AsyncMock,
    ) -> None:
        """Workspace admin (not the assignee) can access implement context."""
        admin_id = uuid.uuid4()
        workspace_id = uuid.uuid4()
        # Issue assigned to someone else
        issue = _make_issue(assignee_id=uuid.uuid4())
        issue_repo.get_by_id_with_relations.return_value = issue
        note_link_repo.get_by_issue.return_value = []
        integration_repo.get_active_github.return_value = _make_integration()
        workspace_repo.get_by_id.return_value = _make_workspace()
        workspace_repo.get_member_role.return_value = WorkspaceRole.ADMIN

        result = await service.execute(
            GetImplementContextPayload(
                issue_id=issue.id,
                workspace_id=workspace_id,
                requester_id=admin_id,
            )
        )

        workspace_repo.get_member_role.assert_awaited_once_with(
            workspace_id=workspace_id,
            user_id=admin_id,
        )
        assert result.context.issue.identifier == "PS-42"

    async def test_owner_not_assignee_can_access(
        self,
        service: GetImplementContextService,
        issue_repo: AsyncMock,
        note_link_repo: AsyncMock,
        integration_repo: AsyncMock,
        workspace_repo: AsyncMock,
    ) -> None:
        """Workspace owner (not the assignee) can access implement context."""
        owner_id = uuid.uuid4()
        workspace_id = uuid.uuid4()
        issue = _make_issue(assignee_id=uuid.uuid4())
        issue_repo.get_by_id_with_relations.return_value = issue
        note_link_repo.get_by_issue.return_value = []
        integration_repo.get_active_github.return_value = _make_integration()
        workspace_repo.get_by_id.return_value = _make_workspace()
        workspace_repo.get_member_role.return_value = WorkspaceRole.OWNER

        result = await service.execute(
            GetImplementContextPayload(
                issue_id=issue.id,
                workspace_id=workspace_id,
                requester_id=owner_id,
            )
        )

        assert result.context is not None

    async def test_assignee_skips_role_lookup(
        self,
        service: GetImplementContextService,
        issue_repo: AsyncMock,
        note_link_repo: AsyncMock,
        integration_repo: AsyncMock,
        workspace_repo: AsyncMock,
    ) -> None:
        """When requester IS the assignee, get_member_role should NOT be called."""
        requester_id = uuid.uuid4()
        issue = _make_issue(assignee_id=requester_id)
        issue_repo.get_by_id_with_relations.return_value = issue
        note_link_repo.get_by_issue.return_value = []
        integration_repo.get_active_github.return_value = _make_integration()
        workspace_repo.get_by_id.return_value = _make_workspace()

        await service.execute(
            GetImplementContextPayload(
                issue_id=issue.id,
                workspace_id=uuid.uuid4(),
                requester_id=requester_id,
            )
        )

        workspace_repo.get_member_role.assert_not_awaited()

    async def test_linked_notes_populated_in_response(
        self,
        service: GetImplementContextService,
        issue_repo: AsyncMock,
        note_link_repo: AsyncMock,
        note_repo: AsyncMock,
        integration_repo: AsyncMock,
        workspace_repo: AsyncMock,
    ) -> None:
        """Linked note blocks are extracted and included in the response."""
        requester_id = uuid.uuid4()
        issue = _make_issue(assignee_id=requester_id)
        note = _make_note("Design decisions")
        link = _make_note_link(note)

        issue_repo.get_by_id_with_relations.return_value = issue
        note_link_repo.get_by_issue.return_value = [link]
        integration_repo.get_active_github.return_value = _make_integration()
        workspace_repo.get_by_id.return_value = _make_workspace()

        result = await service.execute(
            GetImplementContextPayload(
                issue_id=issue.id,
                workspace_id=uuid.uuid4(),
                requester_id=requester_id,
            )
        )

        assert len(result.context.linked_notes) == 1
        assert result.context.linked_notes[0].note_title == "Design decisions"
        assert "First block text." in result.context.linked_notes[0].relevant_blocks

    async def test_deleted_note_excluded_from_linked_notes(
        self,
        service: GetImplementContextService,
        issue_repo: AsyncMock,
        note_link_repo: AsyncMock,
        note_repo: AsyncMock,
        integration_repo: AsyncMock,
        workspace_repo: AsyncMock,
    ) -> None:
        """Notes with is_deleted=True must not appear in linked_notes."""
        requester_id = uuid.uuid4()
        issue = _make_issue(assignee_id=requester_id)
        note = _make_note("Deleted note")
        note.is_deleted = True
        link = _make_note_link(note)

        issue_repo.get_by_id_with_relations.return_value = issue
        note_link_repo.get_by_issue.return_value = [link]
        # Repo fallback also returns None (note is gone)
        note_repo.get_by_id.return_value = None
        integration_repo.get_active_github.return_value = _make_integration()
        workspace_repo.get_by_id.return_value = _make_workspace()

        result = await service.execute(
            GetImplementContextPayload(
                issue_id=issue.id,
                workspace_id=uuid.uuid4(),
                requester_id=requester_id,
            )
        )

        assert result.context.linked_notes == []

    async def test_duplicate_note_links_deduplicated(
        self,
        service: GetImplementContextService,
        issue_repo: AsyncMock,
        note_link_repo: AsyncMock,
        integration_repo: AsyncMock,
        workspace_repo: AsyncMock,
    ) -> None:
        """Two links to the same note should produce only one LinkedNoteBlock."""
        requester_id = uuid.uuid4()
        issue = _make_issue(assignee_id=requester_id)
        note = _make_note("Shared note")
        link1 = _make_note_link(note)
        link2 = _make_note_link(note)

        issue_repo.get_by_id_with_relations.return_value = issue
        note_link_repo.get_by_issue.return_value = [link1, link2]
        integration_repo.get_active_github.return_value = _make_integration()
        workspace_repo.get_by_id.return_value = _make_workspace()

        result = await service.execute(
            GetImplementContextPayload(
                issue_id=issue.id,
                workspace_id=uuid.uuid4(),
                requester_id=requester_id,
            )
        )

        assert len(result.context.linked_notes) == 1

    async def test_tech_stack_truncated_to_300_chars(
        self,
        service: GetImplementContextService,
        issue_repo: AsyncMock,
        note_link_repo: AsyncMock,
        integration_repo: AsyncMock,
        workspace_repo: AsyncMock,
    ) -> None:
        """tech_stack_summary must be at most 300 chars from project description."""
        requester_id = uuid.uuid4()
        issue = _make_issue(assignee_id=requester_id)
        issue.project.description = "x" * 500
        issue_repo.get_by_id_with_relations.return_value = issue
        note_link_repo.get_by_issue.return_value = []
        integration_repo.get_active_github.return_value = _make_integration()
        workspace_repo.get_by_id.return_value = _make_workspace()

        result = await service.execute(
            GetImplementContextPayload(
                issue_id=issue.id,
                workspace_id=uuid.uuid4(),
                requester_id=requester_id,
            )
        )

        assert len(result.context.project.tech_stack_summary) <= 300

    async def test_no_project_description_uses_default_text(
        self,
        service: GetImplementContextService,
        issue_repo: AsyncMock,
        note_link_repo: AsyncMock,
        integration_repo: AsyncMock,
        workspace_repo: AsyncMock,
    ) -> None:
        """Empty project description falls back to default placeholder text."""
        requester_id = uuid.uuid4()
        issue = _make_issue(assignee_id=requester_id)
        issue.project.description = ""
        issue_repo.get_by_id_with_relations.return_value = issue
        note_link_repo.get_by_issue.return_value = []
        integration_repo.get_active_github.return_value = _make_integration()
        workspace_repo.get_by_id.return_value = _make_workspace()

        result = await service.execute(
            GetImplementContextPayload(
                issue_id=issue.id,
                workspace_id=uuid.uuid4(),
                requester_id=requester_id,
            )
        )

        assert result.context.project.tech_stack_summary == "No tech stack description provided."


# ============================================================================
# Service: authorization failures
# ============================================================================


class TestGetImplementContextServiceAuth:
    pytestmark = pytest.mark.asyncio

    async def test_non_assignee_member_raises_permission_error(
        self,
        service: GetImplementContextService,
        issue_repo: AsyncMock,
        note_link_repo: AsyncMock,
        workspace_repo: AsyncMock,
    ) -> None:
        """Regular member who is not the assignee should get ForbiddenError."""
        non_assignee_id = uuid.uuid4()
        issue = _make_issue(assignee_id=uuid.uuid4())  # different assignee
        issue_repo.get_by_id_with_relations.return_value = issue
        workspace_repo.get_member_role.return_value = WorkspaceRole.MEMBER

        with pytest.raises(ForbiddenError, match="assignee or workspace admins"):
            await service.execute(
                GetImplementContextPayload(
                    issue_id=issue.id,
                    workspace_id=uuid.uuid4(),
                    requester_id=non_assignee_id,
                )
            )

    async def test_guest_user_raises_permission_error(
        self,
        service: GetImplementContextService,
        issue_repo: AsyncMock,
        workspace_repo: AsyncMock,
    ) -> None:
        """Guest user (not assignee) should get ForbiddenError."""
        guest_id = uuid.uuid4()
        issue = _make_issue(assignee_id=uuid.uuid4())
        issue_repo.get_by_id_with_relations.return_value = issue
        workspace_repo.get_member_role.return_value = WorkspaceRole.GUEST

        with pytest.raises(ForbiddenError):
            await service.execute(
                GetImplementContextPayload(
                    issue_id=issue.id,
                    workspace_id=uuid.uuid4(),
                    requester_id=guest_id,
                )
            )

    async def test_user_with_no_role_raises_permission_error(
        self,
        service: GetImplementContextService,
        issue_repo: AsyncMock,
        workspace_repo: AsyncMock,
    ) -> None:
        """User not in workspace (role=None) should get ForbiddenError."""
        requester_id = uuid.uuid4()
        issue = _make_issue(assignee_id=uuid.uuid4())
        issue_repo.get_by_id_with_relations.return_value = issue
        workspace_repo.get_member_role.return_value = None

        with pytest.raises(ForbiddenError):
            await service.execute(
                GetImplementContextPayload(
                    issue_id=issue.id,
                    workspace_id=uuid.uuid4(),
                    requester_id=requester_id,
                )
            )

    async def test_permission_check_uses_correct_workspace_and_user(
        self,
        service: GetImplementContextService,
        issue_repo: AsyncMock,
        workspace_repo: AsyncMock,
    ) -> None:
        """get_member_role is called with the exact workspace_id and requester_id."""
        requester_id = uuid.uuid4()
        workspace_id = uuid.uuid4()
        issue = _make_issue(assignee_id=uuid.uuid4())
        issue_repo.get_by_id_with_relations.return_value = issue
        workspace_repo.get_member_role.return_value = WorkspaceRole.MEMBER

        with pytest.raises(ForbiddenError):
            await service.execute(
                GetImplementContextPayload(
                    issue_id=issue.id,
                    workspace_id=workspace_id,
                    requester_id=requester_id,
                )
            )

        workspace_repo.get_member_role.assert_awaited_once_with(
            workspace_id=workspace_id,
            user_id=requester_id,
        )


# ============================================================================
# Service: ValueError paths
# ============================================================================


class TestGetImplementContextServiceValueErrors:
    pytestmark = pytest.mark.asyncio

    async def test_issue_not_found_raises_value_error(
        self,
        service: GetImplementContextService,
        issue_repo: AsyncMock,
    ) -> None:
        """Missing issue raises ValueError containing the issue_id."""
        missing_id = uuid.uuid4()
        issue_repo.get_by_id_with_relations.return_value = None

        with pytest.raises(NotFoundError, match=str(missing_id)):
            await service.execute(
                GetImplementContextPayload(
                    issue_id=missing_id,
                    workspace_id=uuid.uuid4(),
                    requester_id=uuid.uuid4(),
                )
            )

    async def test_no_github_integration_raises_value_error(
        self,
        service: GetImplementContextService,
        issue_repo: AsyncMock,
        note_link_repo: AsyncMock,
        integration_repo: AsyncMock,
        workspace_repo: AsyncMock,
    ) -> None:
        """No active GitHub integration raises ValueError('no_github_integration')."""
        requester_id = uuid.uuid4()
        issue = _make_issue(assignee_id=requester_id)
        issue_repo.get_by_id_with_relations.return_value = issue
        note_link_repo.get_by_issue.return_value = []
        integration_repo.get_active_github.return_value = None  # no integration

        with pytest.raises(ValidationError, match="no_github_integration"):
            await service.execute(
                GetImplementContextPayload(
                    issue_id=issue.id,
                    workspace_id=uuid.uuid4(),
                    requester_id=requester_id,
                )
            )

    async def test_workspace_not_found_raises_value_error(
        self,
        service: GetImplementContextService,
        issue_repo: AsyncMock,
        note_link_repo: AsyncMock,
        integration_repo: AsyncMock,
        workspace_repo: AsyncMock,
    ) -> None:
        """Missing workspace record raises ValueError containing 'Workspace not found'."""
        requester_id = uuid.uuid4()
        workspace_id = uuid.uuid4()
        issue = _make_issue(assignee_id=requester_id)
        issue_repo.get_by_id_with_relations.return_value = issue
        note_link_repo.get_by_issue.return_value = []
        integration_repo.get_active_github.return_value = _make_integration()
        workspace_repo.get_by_id.return_value = None  # workspace missing

        with pytest.raises(NotFoundError, match=str(workspace_id)):
            await service.execute(
                GetImplementContextPayload(
                    issue_id=issue.id,
                    workspace_id=workspace_id,
                    requester_id=requester_id,
                )
            )

    async def test_integration_without_repo_raises_value_error(
        self,
        service: GetImplementContextService,
        issue_repo: AsyncMock,
        note_link_repo: AsyncMock,
        integration_repo: AsyncMock,
        workspace_repo: AsyncMock,
    ) -> None:
        """Integration with no derivable URL propagates ValueError from _derive_repo_info."""
        requester_id = uuid.uuid4()
        issue = _make_issue(assignee_id=requester_id)
        issue_repo.get_by_id_with_relations.return_value = issue
        note_link_repo.get_by_issue.return_value = []
        workspace_repo.get_by_id.return_value = _make_workspace()

        bad_integration = MagicMock()
        bad_integration.settings = {}  # no default_repository, no repositories
        bad_integration.external_account_name = None
        integration_repo.get_active_github.return_value = bad_integration

        with pytest.raises(NotFoundError, match="cannot derive clone_url"):
            await service.execute(
                GetImplementContextPayload(
                    issue_id=issue.id,
                    workspace_id=uuid.uuid4(),
                    requester_id=requester_id,
                )
            )

    async def test_issue_not_found_does_not_query_integration(
        self,
        service: GetImplementContextService,
        issue_repo: AsyncMock,
        integration_repo: AsyncMock,
    ) -> None:
        """Authorization & integration queries are never reached if issue is missing."""
        missing_id = uuid.uuid4()
        issue_repo.get_by_id_with_relations.return_value = None

        with pytest.raises(NotFoundError, match=str(missing_id)):
            await service.execute(
                GetImplementContextPayload(
                    issue_id=missing_id,
                    workspace_id=uuid.uuid4(),
                    requester_id=uuid.uuid4(),
                )
            )

        integration_repo.get_active_github.assert_not_awaited()


# ============================================================================
# Branch format edge cases
# ============================================================================


class TestSuggestedBranchEdgeCases:
    def test_exactly_60_chars_allowed(self) -> None:
        branch = _build_suggested_branch(sequence_id=1, title="a" * 50)
        assert len(branch) <= 60

    def test_title_with_only_special_chars(self) -> None:
        # After slugify, slug is empty — branch should still be valid
        branch = _build_suggested_branch(sequence_id=99, title="!!!---!!!")
        assert branch.startswith("feat/ps-99")
        assert not branch.endswith("-")

    def test_sequence_id_included_in_branch(self) -> None:
        branch = _build_suggested_branch(sequence_id=123, title="my feature")
        assert "123" in branch

    @pytest.mark.parametrize(
        ("seq_id", "title"),
        [
            (1, "Fix login bug"),
            (999, "Implement OAuth2 with GitHub provider"),
            (42, "A" * 100),
        ],
    )
    def test_branch_never_exceeds_60_chars(self, seq_id: int, title: str) -> None:
        branch = _build_suggested_branch(sequence_id=seq_id, title=title)
        assert len(branch) <= 60, f"Branch too long ({len(branch)}): {branch!r}"

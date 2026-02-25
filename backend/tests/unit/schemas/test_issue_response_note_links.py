"""Tests for NoteIssueLinkBriefSchema and IssueResponse.note_links population."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import UUID, uuid4

from pilot_space.api.v1.schemas.issue import IssueResponse, NoteIssueLinkBriefSchema
from pilot_space.infrastructure.database.models import IssuePriority, StateGroup


def _make_link(
    is_deleted: bool = False,
    note_title: str = "Sprint Notes",
    link_type_value: str = "EXTRACTED",
) -> MagicMock:
    """Create a mock NoteIssueLink ORM object."""
    link = MagicMock()
    link.id = uuid4()
    link.note_id = uuid4()
    link.is_deleted = is_deleted
    link.link_type = MagicMock()
    link.link_type.value = link_type_value
    link.note = MagicMock()
    link.note.title = note_title
    return link


def _make_issue(note_links: list[MagicMock] | None = None) -> MagicMock:
    """Create a mock Issue ORM object with all fields required by IssueResponse.from_issue()."""
    issue = MagicMock()
    issue.id = uuid4()
    issue.workspace_id = uuid4()
    issue.sequence_id = 1
    issue.identifier = "PS-1"
    issue.name = "Test Issue"
    issue.description = None
    issue.description_html = None
    issue.priority = IssuePriority.NONE
    issue.estimate_points = None
    issue.estimate_hours = None
    issue.start_date = None
    issue.target_date = None
    issue.sort_order = 0
    issue.created_at = datetime(2024, 1, 1, tzinfo=UTC)
    issue.updated_at = datetime(2024, 1, 2, tzinfo=UTC)
    issue.project_id = uuid4()
    issue.assignee_id = None
    issue.reporter_id = uuid4()
    issue.cycle_id = None
    issue.parent_id = None
    issue.ai_metadata = None
    issue.has_ai_enhancements = False
    issue.sub_issues = []
    issue.assignee = None
    issue.labels = []
    issue.note_links = note_links if note_links is not None else []

    # project — must satisfy ProjectBriefSchema.model_validate
    issue.project = MagicMock(spec=["id", "name", "identifier"])
    issue.project.id = uuid4()
    issue.project.name = "Pilot Space"
    issue.project.identifier = "PS"

    # state — must satisfy StateBriefSchema.model_validate
    issue.state = MagicMock(spec=["id", "name", "color", "group"])
    issue.state.id = uuid4()
    issue.state.name = "Backlog"
    issue.state.color = "#6B7280"
    issue.state.group = StateGroup.UNSTARTED

    # reporter — must satisfy UserBriefSchema.model_validate
    issue.reporter = MagicMock(spec=["id", "email", "display_name"])
    issue.reporter.id = uuid4()
    issue.reporter.email = "reporter@example.com"
    issue.reporter.display_name = "Reporter"

    return issue


# ============================================================================
# NoteIssueLinkBriefSchema tests
# ============================================================================


class TestNoteIssueLinkBriefSchema:
    def test_schema_fields(self) -> None:
        """All fields should be stored and serializable."""
        link_id = uuid4()
        note_id = uuid4()

        schema = NoteIssueLinkBriefSchema(
            id=link_id,
            note_id=note_id,
            link_type="EXTRACTED",
            note_title="My Planning Note",
        )

        assert schema.id == link_id
        assert schema.note_id == note_id
        assert schema.link_type == "EXTRACTED"
        assert schema.note_title == "My Planning Note"

    def test_link_type_is_string(self) -> None:
        """link_type must be str, not an enum object."""
        schema = NoteIssueLinkBriefSchema(
            id=uuid4(),
            note_id=uuid4(),
            link_type="REFERENCED",
            note_title="Ref Note",
        )

        assert isinstance(schema.link_type, str)

    def test_serialization_roundtrip(self) -> None:
        """model_dump should produce plain Python-native types."""
        schema = NoteIssueLinkBriefSchema(
            id=uuid4(),
            note_id=uuid4(),
            link_type="CREATED",
            note_title="Spec doc",
        )
        data = schema.model_dump()

        assert isinstance(data["id"], UUID)
        assert isinstance(data["note_id"], UUID)
        assert isinstance(data["link_type"], str)
        assert isinstance(data["note_title"], str)


# ============================================================================
# IssueResponse.from_issue() note_links tests
# ============================================================================


class TestIssueResponseNoteLinks:
    def test_from_issue_populates_note_links(self) -> None:
        """Non-deleted note_links should appear in the response."""
        link1 = _make_link(note_title="Note A")
        link2 = _make_link(note_title="Note B")
        issue = _make_issue(note_links=[link1, link2])

        response = IssueResponse.from_issue(issue)

        assert len(response.note_links) == 2
        titles = {nl.note_title for nl in response.note_links}
        assert "Note A" in titles
        assert "Note B" in titles

    def test_from_issue_filters_deleted_note_links(self) -> None:
        """Links with is_deleted=True must be excluded."""
        active = _make_link(note_title="Active Note")
        deleted = _make_link(is_deleted=True, note_title="Deleted Note")
        issue = _make_issue(note_links=[active, deleted])

        response = IssueResponse.from_issue(issue)

        assert len(response.note_links) == 1
        assert response.note_links[0].note_title == "Active Note"
        assert response.note_links[0].id == active.id

    def test_from_issue_empty_note_links_when_none(self) -> None:
        """note_links=None on the issue should yield an empty list in the response."""
        issue = _make_issue(note_links=None)
        # Simulate ORM returning None for the relationship
        issue.note_links = None

        response = IssueResponse.from_issue(issue)

        assert response.note_links == []

    def test_from_issue_note_links_have_correct_types(self) -> None:
        """Each note_link item must be a NoteIssueLinkBriefSchema with str link_type."""
        link = _make_link(link_type_value="EXTRACTED")
        issue = _make_issue(note_links=[link])

        response = IssueResponse.from_issue(issue)

        assert len(response.note_links) == 1
        item = response.note_links[0]
        assert isinstance(item, NoteIssueLinkBriefSchema)
        assert isinstance(item.link_type, str)
        assert item.link_type == "EXTRACTED"

    def test_from_issue_note_title_empty_when_note_is_none(self) -> None:
        """note_title should be empty string when link.note is None."""
        link = _make_link()
        link.note = None
        issue = _make_issue(note_links=[link])

        response = IssueResponse.from_issue(issue)

        assert len(response.note_links) == 1
        assert response.note_links[0].note_title == ""

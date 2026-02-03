"""Unit tests for AI Context SSE streaming mapper functions."""

from __future__ import annotations

from unittest.mock import MagicMock

from pilot_space.api.v1.routers.issues_ai_context_streaming import (
    _effort_to_estimate,
    _map_context_summary,
    _map_prompts,
    _map_related_docs,
    _map_related_issues,
    _map_tasks,
)


class TestEffortToEstimate:
    """Test suite for _effort_to_estimate function."""

    def test_maps_all_effort_sizes(self) -> None:
        """Verify all effort sizes map to correct estimates."""
        assert _effort_to_estimate("S") == "~1h"
        assert _effort_to_estimate("M") == "~2-3h"
        assert _effort_to_estimate("L") == "~4-6h"
        assert _effort_to_estimate("XL") == "~8h+"

    def test_defaults_unknown_to_medium(self) -> None:
        """Verify unknown/empty/lowercase effort codes default to M."""
        assert _effort_to_estimate("unknown") == "~2-3h"
        assert _effort_to_estimate("") == "~2-3h"
        assert _effort_to_estimate("s") == "~2-3h"


class TestMapContextSummary:
    """Test suite for _map_context_summary function."""

    def test_returns_correct_structure_with_all_data(self) -> None:
        """Verify summary has required fields and calculates stats correctly."""
        context = MagicMock()
        context.issue = MagicMock()
        context.issue.identifier = "PS-42"
        context.issue.name = "Implement feature X"
        context.related_issues = [{"id": "1"}, {"id": "2"}]
        context.related_notes = [{"id": "note1"}]
        context.related_pages = [{"id": "page1"}, {"id": "page2"}]
        context.code_references = [{"file": "main.py"}]
        context.tasks_checklist = [{"id": 1}, {"id": 2}, {"id": 3}]

        result = _map_context_summary(
            context,
            result_summary="This is a test summary",
        )

        assert result["issueIdentifier"] == "PS-42"
        assert result["title"] == "Implement feature X"
        assert result["summaryText"] == "This is a test summary"
        assert result["stats"]["relatedCount"] == 2
        assert result["stats"]["docsCount"] == 3  # 1 note + 2 pages
        assert result["stats"]["filesCount"] == 1
        assert result["stats"]["tasksCount"] == 3

    def test_handles_missing_issue_and_empty_lists(self) -> None:
        """Verify summary handles None issue and empty lists gracefully."""
        context = MagicMock()
        context.issue = None
        context.related_issues = []
        context.related_notes = []
        context.related_pages = []
        context.code_references = []
        context.tasks_checklist = []

        result = _map_context_summary(context, "No issue")

        assert result["issueIdentifier"] == ""
        assert result["title"] == ""
        assert result["summaryText"] == "No issue"
        assert all(count == 0 for count in result["stats"].values())


class TestMapRelatedIssues:
    """Test suite for _map_related_issues function."""

    def test_maps_all_state_groups_correctly(self) -> None:
        """Verify all issue states map to correct state groups."""
        context = MagicMock()
        context.related_issues = [
            {
                "id": "1",
                "identifier": "PS-1",
                "title": "Done task",
                "excerpt": "Summary",
                "state": "Done",
            },
            {
                "id": "2",
                "identifier": "PS-2",
                "title": "In progress",
                "excerpt": "Summary",
                "state": "In Progress",
            },
            {
                "id": "3",
                "identifier": "PS-3",
                "title": "In review",
                "excerpt": "Summary",
                "state": "In Review",
            },
            {
                "id": "4",
                "identifier": "PS-4",
                "title": "Backlog",
                "excerpt": "Summary",
                "state": "Backlog",
            },
            {
                "id": "5",
                "identifier": "PS-5",
                "title": "Todo",
                "excerpt": "Summary",
                "state": "Todo",
            },
            {
                "id": "6",
                "identifier": "PS-6",
                "title": "Cancelled",
                "excerpt": "Summary",
                "state": "Cancelled",
            },
            {
                "id": "7",
                "identifier": "PS-7",
                "title": "Unknown",
                "excerpt": "Summary",
                "state": "InvalidState",
            },
        ]

        result = _map_related_issues(context)

        assert len(result) == 7
        assert result[0]["stateGroup"] == "completed"
        assert result[1]["stateGroup"] == "started"
        assert result[2]["stateGroup"] == "started"
        assert result[3]["stateGroup"] == "unstarted"
        assert result[4]["stateGroup"] == "unstarted"
        assert result[5]["stateGroup"] == "cancelled"
        assert result[6]["stateGroup"] == "unstarted"  # Unknown defaults to unstarted

    def test_maps_all_fields_and_defaults_relation_type(self) -> None:
        """Verify all fields are mapped correctly with default relationType."""
        context = MagicMock()
        context.related_issues = [
            {
                "id": "uuid-123",
                "identifier": "PS-42",
                "title": "Test Issue",
                "excerpt": "This is the excerpt",
                "state": "In Progress",
            },
        ]

        result = _map_related_issues(context)

        assert result[0]["relationType"] == "relates"
        assert result[0]["issueId"] == "uuid-123"
        assert result[0]["identifier"] == "PS-42"
        assert result[0]["title"] == "Test Issue"
        assert result[0]["summary"] == "This is the excerpt"
        assert result[0]["status"] == "In Progress"

    def test_extracts_relation_type_from_data(self) -> None:
        """Verify relation_type is extracted from issue data when present."""
        context = MagicMock()
        context.related_issues = [
            {
                "id": "uuid-1",
                "identifier": "PS-10",
                "title": "Blocker",
                "excerpt": "Blocks this",
                "state": "In Progress",
                "relation_type": "blocks",
            },
            {
                "id": "uuid-2",
                "identifier": "PS-11",
                "title": "Blocked",
                "excerpt": "Blocked by this",
                "state": "Todo",
                "relation_type": "blocked_by",
            },
            {
                "id": "uuid-3",
                "identifier": "PS-12",
                "title": "No relation key",
                "excerpt": "Default",
                "state": "Done",
            },
        ]

        result = _map_related_issues(context)

        assert result[0]["relationType"] == "blocks"
        assert result[1]["relationType"] == "blocked_by"
        assert result[2]["relationType"] == "relates"

    def test_handles_empty_related_issues(self) -> None:
        """Verify empty related_issues returns empty list."""
        context = MagicMock()
        context.related_issues = []
        assert _map_related_issues(context) == []


class TestMapRelatedDocs:
    """Test suite for _map_related_docs function."""

    def test_combines_notes_and_pages_with_correct_doc_types(self) -> None:
        """Verify notes get docType='note' and pages get docType='spec'."""
        context = MagicMock()
        context.related_notes = [
            {"id": "note-1", "title": "Note 1", "excerpt": "Note excerpt"},
            {"id": "note-2", "title": "Note 2", "excerpt": "Another note"},
        ]
        context.related_pages = [
            {"id": "page-1", "title": "Page 1", "excerpt": "Page excerpt"},
        ]

        result = _map_related_docs(context)

        assert len(result) == 3
        assert result[0]["docType"] == "note"
        assert result[0]["title"] == "Note 1"
        assert result[0]["summary"] == "Note excerpt"
        assert result[1]["docType"] == "note"
        assert result[1]["title"] == "Note 2"
        assert result[2]["docType"] == "spec"
        assert result[2]["title"] == "Page 1"
        assert result[2]["summary"] == "Page excerpt"

    def test_handles_empty_lists_and_missing_fields(self) -> None:
        """Verify empty lists return empty result and missing fields default to empty strings."""
        context = MagicMock()
        context.related_notes = []
        context.related_pages = []
        assert _map_related_docs(context) == []

        context.related_notes = [{"id": "note-1"}]
        context.related_pages = [{"id": "page-1"}]
        result = _map_related_docs(context)
        assert result[0]["title"] == ""
        assert result[0]["summary"] == ""


class TestMapTasks:
    """Test suite for _map_tasks function."""

    def test_converts_effort_and_parses_dependencies(self) -> None:
        """Verify estimate uses _effort_to_estimate and dependencies are parsed correctly."""
        context = MagicMock()
        context.tasks_checklist = [
            {
                "order": 0,
                "description": "Small task",
                "estimated_effort": "S",
                "dependencies": ["1", "2", "invalid", 3],
                "completed": False,
            },
            {
                "order": 1,
                "description": "Large task",
                "estimated_effort": "L",
                "dependencies": [0],
                "completed": True,
            },
        ]

        result = _map_tasks(context)

        assert len(result) == 2
        assert result[0]["id"] == 0
        assert result[0]["title"] == "Small task"
        assert result[0]["estimate"] == "~1h"
        assert result[0]["dependencies"] == [1, 2, 3]  # String deps converted, invalid skipped
        assert result[0]["completed"] is False

        assert result[1]["id"] == 1
        assert result[1]["estimate"] == "~4-6h"
        assert result[1]["dependencies"] == [0]
        assert result[1]["completed"] is True

    def test_handles_empty_tasks_and_missing_dependencies(self) -> None:
        """Verify empty tasks_checklist returns empty list and missing deps defaults to empty."""
        context = MagicMock()
        context.tasks_checklist = []
        assert _map_tasks(context) == []

        context.tasks_checklist = [
            {
                "order": 0,
                "description": "Task without deps",
                "estimated_effort": "M",
                "completed": False,
            },
        ]
        result = _map_tasks(context)
        assert result[0]["dependencies"] == []


class TestMapPrompts:
    """Test suite for _map_prompts function."""

    def test_single_task_creates_metadata_plus_full_guide(self) -> None:
        """Verify one task creates metadata entry + full implementation guide."""
        context = MagicMock()
        context.claude_code_prompt = "# Full implementation guide\n\nDetails here..."
        context.tasks_checklist = [
            {
                "order": 0,
                "description": "Implement feature",
                "estimated_effort": "M",
                "dependencies": [],
                "completed": False,
            },
        ]

        result = _map_prompts(context)

        assert len(result) == 2
        assert result[0]["taskId"] == 0
        assert result[0]["title"] == "Task 1: Implement feature"
        assert "## Implement feature" in result[0]["content"]
        assert result[1]["taskId"] == 1
        assert result[1]["title"] == "Full Implementation Guide"
        assert result[1]["content"] == "# Full implementation guide\n\nDetails here..."

    def test_no_tasks_creates_single_implementation_guide(self) -> None:
        """Verify no tasks creates single 'Implementation Guide' prompt."""
        context = MagicMock()
        context.claude_code_prompt = "# Complete guide\n\nImplementation steps..."
        context.tasks_checklist = []

        result = _map_prompts(context)

        assert len(result) == 1
        assert result[0]["taskId"] == 0
        assert result[0]["title"] == "Implementation Guide"
        assert result[0]["content"] == "# Complete guide\n\nImplementation steps..."

    def test_multiple_tasks_create_metadata_entries_plus_full_guide(self) -> None:
        """Verify multiple tasks create per-task metadata + final full prompt."""
        context = MagicMock()
        context.claude_code_prompt = "Base prompt content"
        context.tasks_checklist = [
            {
                "order": 0,
                "description": "Setup database",
                "estimated_effort": "M",
                "dependencies": [],
                "completed": False,
            },
            {
                "order": 1,
                "description": "Create API endpoints",
                "estimated_effort": "L",
                "dependencies": [0],
                "completed": False,
            },
            {
                "order": 2,
                "description": "Complex task",
                "estimated_effort": "XL",
                "dependencies": [0, 1],
                "completed": False,
            },
        ]

        result = _map_prompts(context)

        # 3 task metadata entries + 1 full guide
        assert len(result) == 4

        # First task metadata
        assert result[0]["taskId"] == 0
        assert result[0]["title"] == "Task 1: Setup database"
        assert "## Setup database" in result[0]["content"]
        assert "Estimated effort: ~2-3h" in result[0]["content"]
        assert "Dependencies: None" in result[0]["content"]
        assert "Base prompt content" not in result[0]["content"]

        # Second task metadata
        assert result[1]["taskId"] == 1
        assert result[1]["title"] == "Task 2: Create API endpoints"
        assert "Estimated effort: ~4-6h" in result[1]["content"]
        assert "Dependencies: 0" in result[1]["content"]

        # Third task metadata with multiple dependencies
        assert result[2]["taskId"] == 2
        assert "Dependencies: 0, 1" in result[2]["content"]

        # Full implementation guide (last entry)
        assert result[3]["taskId"] == 3
        assert result[3]["title"] == "Full Implementation Guide"
        assert result[3]["content"] == "Base prompt content"

    def test_no_prompt_or_empty_prompt_returns_empty(self) -> None:
        """Verify None or empty claude_code_prompt returns empty list."""
        context = MagicMock()
        context.claude_code_prompt = None
        context.tasks_checklist = [
            {
                "order": 0,
                "description": "Task",
                "estimated_effort": "M",
                "dependencies": [],
                "completed": False,
            },
        ]
        assert _map_prompts(context) == []

        context.claude_code_prompt = ""
        context.tasks_checklist = []
        assert _map_prompts(context) == []

    def test_none_tasks_checklist_creates_single_guide(self) -> None:
        """Verify None tasks_checklist creates single 'Implementation Guide' prompt."""
        context = MagicMock()
        context.claude_code_prompt = "Guide content"
        context.tasks_checklist = None

        result = _map_prompts(context)

        assert len(result) == 1
        assert result[0]["title"] == "Implementation Guide"
        assert result[0]["content"] == "Guide content"

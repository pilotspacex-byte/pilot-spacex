"""Unit tests for GitHubSyncService.extract_issue_refs.

extract_issue_refs is a pure function: no DB access, no async.
All tests instantiate GitHubSyncService with MagicMock dependencies.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from pilot_space.integrations.github.sync import GitHubSyncService, IssueReference


@pytest.fixture
def service() -> GitHubSyncService:
    """GitHubSyncService with mocked dependencies (extract_issue_refs is pure)."""
    return GitHubSyncService(
        session=MagicMock(),
        integration_link_repo=MagicMock(),
        issue_repo=MagicMock(),
    )


# ---------------------------------------------------------------------------
# Basic extraction
# ---------------------------------------------------------------------------


class TestExtractBasic:
    def test_simple_reference(self, service: GitHubSyncService) -> None:
        refs = service.extract_issue_refs("PILOT-123")
        assert len(refs) == 1
        ref = refs[0]
        assert ref.project_identifier == "PILOT"
        assert ref.sequence_id == 123
        assert ref.identifier == "PILOT-123"
        assert ref.is_closing is False

    def test_multiple_references(self, service: GitHubSyncService) -> None:
        refs = service.extract_issue_refs("PILOT-123 and ABC-456")
        assert len(refs) == 2
        identifiers = {r.identifier for r in refs}
        assert identifiers == {"PILOT-123", "ABC-456"}

    def test_deduplicates_repeated_reference(self, service: GitHubSyncService) -> None:
        refs = service.extract_issue_refs("PILOT-123 and PILOT-123")
        assert len(refs) == 1
        assert refs[0].identifier == "PILOT-123"

    def test_empty_string_returns_empty(self, service: GitHubSyncService) -> None:
        refs = service.extract_issue_refs("")
        assert refs == []

    def test_no_matches_returns_empty(self, service: GitHubSyncService) -> None:
        refs = service.extract_issue_refs("no refs here, just plain text")
        assert refs == []


# ---------------------------------------------------------------------------
# Closing-flag detection
# ---------------------------------------------------------------------------


class TestClosingFlag:
    def test_fix_prefix_sets_is_closing(self, service: GitHubSyncService) -> None:
        refs = service.extract_issue_refs("Fix PILOT-123")
        assert len(refs) == 1
        assert refs[0].is_closing is True

    def test_fixes_prefix_sets_is_closing(self, service: GitHubSyncService) -> None:
        refs = service.extract_issue_refs("Fixes PILOT-123")
        assert len(refs) == 1
        assert refs[0].is_closing is True

    def test_close_prefix_sets_is_closing(self, service: GitHubSyncService) -> None:
        refs = service.extract_issue_refs("Close ABC-456")
        assert len(refs) == 1
        assert refs[0].is_closing is True

    def test_closes_prefix_sets_is_closing(self, service: GitHubSyncService) -> None:
        refs = service.extract_issue_refs("Closes ABC-456")
        assert len(refs) == 1
        assert refs[0].is_closing is True

    def test_resolve_prefix_sets_is_closing(self, service: GitHubSyncService) -> None:
        refs = service.extract_issue_refs("Resolve XYZ-789")
        assert len(refs) == 1
        assert refs[0].is_closing is True

    def test_resolves_prefix_sets_is_closing(self, service: GitHubSyncService) -> None:
        refs = service.extract_issue_refs("Resolves XYZ-789")
        assert len(refs) == 1
        assert refs[0].is_closing is True

    def test_no_prefix_not_closing(self, service: GitHubSyncService) -> None:
        refs = service.extract_issue_refs("PILOT-123")
        assert refs[0].is_closing is False

    def test_lowercase_fixes_prefix_sets_is_closing(self, service: GitHubSyncService) -> None:
        refs = service.extract_issue_refs("fixes PILOT-123")
        assert refs[0].is_closing is True


# ---------------------------------------------------------------------------
# Pattern boundary tests (2..10 chars)
# ---------------------------------------------------------------------------


class TestPatternBoundaries:
    def test_two_char_project_matches(self, service: GitHubSyncService) -> None:
        refs = service.extract_issue_refs("AB-1")
        assert len(refs) == 1
        assert refs[0].project_identifier == "AB"
        assert refs[0].sequence_id == 1

    def test_ten_char_project_matches(self, service: GitHubSyncService) -> None:
        refs = service.extract_issue_refs("ABCDEFGHIJ-1")
        assert len(refs) == 1
        assert refs[0].project_identifier == "ABCDEFGHIJ"

    def test_eleven_char_project_does_not_match(self, service: GitHubSyncService) -> None:
        # ISSUE_REF_PATTERN requires [A-Z]{2,10}, so 11 chars should not be a standalone
        # match.  The regex will match the last 10 chars as a separate token only if there
        # is a hyphen - the full 11-char prefix is rejected.
        refs = service.extract_issue_refs("ABCDEFGHIJK-1")
        # Eleven upper-case chars followed by "-1": regex allows [A-Z]{2,10} so it can
        # match the trailing 10 chars "BCDEFGHIJK".  Verify the 11-char prefix "ABCDEFGHIJK"
        # is NOT returned as a single match.
        for ref in refs:
            assert ref.project_identifier != "ABCDEFGHIJK"


# ---------------------------------------------------------------------------
# Realistic commit message
# ---------------------------------------------------------------------------


class TestRealisticMessage:
    def test_multiline_commit_message(self, service: GitHubSyncService) -> None:
        msg = "feat(auth): Fix login\n\nFixes PS-42 and closes UI-7"
        refs = service.extract_issue_refs(msg)
        assert len(refs) == 2

        by_id = {r.identifier: r for r in refs}
        assert "PS-42" in by_id
        assert "UI-7" in by_id

        assert by_id["PS-42"].is_closing is True
        assert by_id["UI-7"].is_closing is True

    def test_reference_in_pr_body_not_closing(self, service: GitHubSyncService) -> None:
        body = "This PR relates to PILOT-99 and was discussed in PILOT-100."
        refs = service.extract_issue_refs(body)
        assert len(refs) == 2
        for ref in refs:
            assert ref.is_closing is False

    def test_return_type_is_issue_reference(self, service: GitHubSyncService) -> None:
        refs = service.extract_issue_refs("PILOT-1")
        assert len(refs) == 1
        assert isinstance(refs[0], IssueReference)

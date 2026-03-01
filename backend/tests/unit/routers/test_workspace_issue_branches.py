"""Unit tests for workspace_issue_branches router.

Tests slug generation logic and response mapping in isolation.
Auth/RLS are tested via integration tests; here we verify the business
logic helpers that are pure functions.
"""

from __future__ import annotations

import pytest

from pilot_space.api.v1.routers.workspace_issue_branches import _is_valid_uuid, _slugify


class TestIsValidUuid:
    """Tests for _is_valid_uuid helper."""

    def test_valid_uuid_returns_true(self) -> None:
        assert _is_valid_uuid("550e8400-e29b-41d4-a716-446655440000") is True

    def test_slug_string_returns_false(self) -> None:
        assert _is_valid_uuid("my-workspace") is False

    def test_empty_string_returns_false(self) -> None:
        assert _is_valid_uuid("") is False

    def test_partial_uuid_returns_false(self) -> None:
        assert _is_valid_uuid("550e8400-e29b") is False


class TestSlugify:
    """Tests for _slugify helper — ensures branch name slug rules."""

    def test_lowercase_conversion(self) -> None:
        assert _slugify("Fix Login Bug") == "fix-login-bug"

    def test_special_chars_become_hyphens(self) -> None:
        assert _slugify("feat: add (new) feature!") == "feat-add-new-feature"

    def test_consecutive_specials_collapse_to_one_hyphen(self) -> None:
        assert _slugify("hello   world---test") == "hello-world-test"

    def test_leading_trailing_hyphens_stripped(self) -> None:
        assert _slugify("  leading and trailing  ") == "leading-and-trailing"

    def test_digits_preserved(self) -> None:
        assert _slugify("issue 42 fix") == "issue-42-fix"

    def test_already_slug_unchanged(self) -> None:
        assert _slugify("fix-login") == "fix-login"

    def test_empty_string(self) -> None:
        assert _slugify("") == ""

    def test_only_specials_returns_empty(self) -> None:
        assert _slugify("!!!") == ""

    @pytest.mark.parametrize(
        ("name", "expected"),
        [
            ("Add user authentication", "add-user-authentication"),
            ("Fix: null pointer @ line 42", "fix-null-pointer-line-42"),
            ("Refactor DB queries (N+1)", "refactor-db-queries-n-1"),
        ],
    )
    def test_realistic_issue_names(self, name: str, expected: str) -> None:
        assert _slugify(name) == expected

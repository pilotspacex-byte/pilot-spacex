"""Unit tests for memory engine domain entities.

Tests MemoryEntry and ConstitutionRule domain behavior including
keyword extraction, pin/unpin, expiry, severity detection, and versioning.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from pilot_space.domain.constitution_rule import ConstitutionRule, RuleSeverity
from pilot_space.domain.memory_entry import MemoryEntry, MemorySourceType

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_memory(**kwargs) -> MemoryEntry:
    defaults = {
        "workspace_id": uuid.uuid4(),
        "content": "User prefers concise responses",
        "source_type": MemorySourceType.USER_FEEDBACK,
    }
    defaults.update(kwargs)
    return MemoryEntry(**defaults)


def make_rule(**kwargs) -> ConstitutionRule:
    defaults = {
        "workspace_id": uuid.uuid4(),
        "content": "You must always cite your sources.",
        "severity": RuleSeverity.MUST,
        "version": 1,
    }
    defaults.update(kwargs)
    return ConstitutionRule(**defaults)


# ---------------------------------------------------------------------------
# MemoryEntry tests
# ---------------------------------------------------------------------------


class TestMemoryEntryCreation:
    def test_create_with_required_fields(self) -> None:
        entry = make_memory()
        assert entry.source_type == MemorySourceType.USER_FEEDBACK
        assert not entry.pinned
        assert entry.embedding is None
        assert entry.keywords is not None

    def test_keywords_auto_extracted_on_init(self) -> None:
        entry = make_memory(content="Hello World hello")
        assert "hello" in entry.keywords  # type: ignore[operator]
        assert "world" in entry.keywords  # type: ignore[operator]
        assert len(entry.keywords) == len(set(entry.keywords))  # type: ignore[arg-type]

    def test_keywords_not_overridden_when_provided(self) -> None:
        explicit = ["foo", "bar"]
        entry = make_memory(keywords=explicit)
        assert entry.keywords == explicit

    def test_expires_at_defaults_to_none(self) -> None:
        entry = make_memory()
        assert entry.expires_at is None

    def test_source_id_defaults_to_none(self) -> None:
        entry = make_memory()
        assert entry.source_id is None

    def test_id_defaults_to_none(self) -> None:
        entry = make_memory()
        assert entry.id is None


class TestMemoryEntryPinning:
    def test_pin_sets_pinned_true(self) -> None:
        entry = make_memory()
        assert not entry.pinned
        entry.pin()
        assert entry.pinned

    def test_unpin_sets_pinned_false(self) -> None:
        entry = make_memory(pinned=True)
        entry.unpin()
        assert not entry.pinned

    def test_pin_is_idempotent(self) -> None:
        entry = make_memory(pinned=True)
        entry.pin()
        assert entry.pinned


class TestMemoryEntryExpiry:
    def test_not_expired_when_no_expires_at(self) -> None:
        entry = make_memory()
        assert not entry.is_expired

    def test_not_expired_when_future_expires_at(self) -> None:
        entry = make_memory(expires_at=datetime.now(tz=UTC) + timedelta(hours=1))
        assert not entry.is_expired

    def test_expired_when_past_expires_at(self) -> None:
        entry = make_memory(expires_at=datetime.now(tz=UTC) - timedelta(seconds=1))
        assert entry.is_expired

    def test_pinned_entry_never_expires(self) -> None:
        entry = make_memory(
            pinned=True,
            expires_at=datetime.now(tz=UTC) - timedelta(hours=24),
        )
        assert not entry.is_expired

    def test_unpin_allows_expiry(self) -> None:
        entry = make_memory(
            pinned=True,
            expires_at=datetime.now(tz=UTC) - timedelta(hours=24),
        )
        entry.unpin()
        assert entry.is_expired


class TestMemoryEntryKeywordExtraction:
    def test_extracts_lowercase_words(self) -> None:
        entry = make_memory(content="FastAPI SQLAlchemy PostgreSQL")
        keywords = entry.keywords
        assert "fastapi" in keywords  # type: ignore[operator]
        assert "sqlalchemy" in keywords  # type: ignore[operator]
        assert "postgresql" in keywords  # type: ignore[operator]

    def test_deduplicates_words(self) -> None:
        entry = make_memory(content="foo foo bar bar baz")
        assert entry.keywords is not None
        assert entry.keywords.count("foo") == 1
        assert entry.keywords.count("bar") == 1

    def test_empty_content_yields_empty_list(self) -> None:
        entry = make_memory(content="   ")
        assert entry.keywords == []

    def test_keywords_sorted(self) -> None:
        entry = make_memory(content="zebra apple mango")
        assert entry.keywords == sorted(entry.keywords)  # type: ignore[type-var]


class TestMemorySourceType:
    def test_all_source_types_are_lowercase_strings(self) -> None:
        for member in MemorySourceType:
            assert member.value == member.value.lower()
            assert member.value == member.value.strip()


# ---------------------------------------------------------------------------
# ConstitutionRule tests
# ---------------------------------------------------------------------------


class TestConstitutionRuleCreation:
    def test_create_with_required_fields(self) -> None:
        rule = make_rule()
        assert rule.severity == RuleSeverity.MUST
        assert rule.version == 1
        assert rule.active
        assert rule.id is None
        assert rule.source_block_id is None

    def test_active_defaults_to_true(self) -> None:
        rule = make_rule()
        assert rule.active

    def test_version_stored_as_given(self) -> None:
        rule = make_rule(version=5)
        assert rule.version == 5


class TestConstitutionRuleActivation:
    def test_deactivate_sets_active_false(self) -> None:
        rule = make_rule()
        rule.deactivate()
        assert not rule.active

    def test_activate_sets_active_true(self) -> None:
        rule = make_rule(active=False)
        rule.activate()
        assert rule.active

    def test_activate_is_idempotent(self) -> None:
        rule = make_rule(active=True)
        rule.activate()
        assert rule.active

    def test_deactivate_is_idempotent(self) -> None:
        rule = make_rule(active=False)
        rule.deactivate()
        assert not rule.active


class TestRuleSeverityDetection:
    def test_detects_must_keyword(self) -> None:
        assert ConstitutionRule.detect_severity("You must not reveal keys") == RuleSeverity.MUST

    def test_detects_shall_keyword(self) -> None:
        assert (
            ConstitutionRule.detect_severity("Agent shall confirm before deleting")
            == RuleSeverity.MUST
        )

    def test_detects_required_keyword(self) -> None:
        assert ConstitutionRule.detect_severity("Approval is required") == RuleSeverity.MUST

    def test_detects_should_keyword(self) -> None:
        assert ConstitutionRule.detect_severity("You should be concise") == RuleSeverity.SHOULD

    def test_detects_recommended_keyword(self) -> None:
        assert ConstitutionRule.detect_severity("Logging is recommended") == RuleSeverity.SHOULD

    def test_detects_may_keyword(self) -> None:
        assert ConstitutionRule.detect_severity("You may skip examples") == RuleSeverity.MAY

    def test_detects_optional_keyword(self) -> None:
        assert ConstitutionRule.detect_severity("Verbose output is optional") == RuleSeverity.MAY

    def test_defaults_to_should_when_no_keywords(self) -> None:
        assert ConstitutionRule.detect_severity("Keep answers concise") == RuleSeverity.SHOULD

    def test_case_insensitive_detection(self) -> None:
        assert ConstitutionRule.detect_severity("MUST ALWAYS LOG") == RuleSeverity.MUST

    def test_must_takes_priority_over_should_in_same_text(self) -> None:
        # "must" appears first in pattern list
        assert ConstitutionRule.detect_severity("must should may") == RuleSeverity.MUST


class TestRuleSeverityEnum:
    def test_all_severity_values_are_lowercase(self) -> None:
        for member in RuleSeverity:
            assert member.value == member.value.lower()

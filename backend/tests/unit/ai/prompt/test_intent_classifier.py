"""Unit tests for keyword-based intent classification."""

from __future__ import annotations

import pytest

from pilot_space.ai.prompt.intent_classifier import (
    RULE_SUMMARIES,
    classify_intent,
    get_rules_for_intent,
)
from pilot_space.ai.prompt.models import IntentClassification, UserIntent


class TestClassifyIntentNoteWriting:
    """Tests for NOTE_WRITING intent detection."""

    @pytest.mark.parametrize(
        "message",
        [
            "write a summary of the meeting",
            "draft a design document",
            "document the API endpoints",
            "add content about authentication",
            "create a note for sprint planning",
            "improve writing in the introduction",
            "summarize the discussion",
        ],
    )
    def test_note_writing_patterns(self, message: str) -> None:
        result = classify_intent(message)
        assert result.primary == UserIntent.NOTE_WRITING


class TestClassifyIntentNoteReading:
    """Tests for NOTE_READING intent detection."""

    @pytest.mark.parametrize(
        "message",
        [
            "read note about architecture",
            "show note from last meeting",
            "search note for authentication",
            "find in note the API design",
            "what is the note content",
        ],
    )
    def test_note_reading_patterns(self, message: str) -> None:
        result = classify_intent(message)
        assert result.primary == UserIntent.NOTE_READING


class TestClassifyIntentIssueMgmt:
    """Tests for ISSUE_MGMT intent detection."""

    @pytest.mark.parametrize(
        "message",
        [
            "create an issue for the login bug",
            "update issue PILOT-123",
            "extract issues from this note",
            "find duplicates in the backlog",
            "assign this to the developer",
            "transition the state to in progress",
            "there is a bug in the login page",
            "file a feature request for dark mode",
        ],
    )
    def test_issue_mgmt_patterns(self, message: str) -> None:
        result = classify_intent(message)
        assert result.primary == UserIntent.ISSUE_MGMT


class TestClassifyIntentPMBlocks:
    """Tests for PM_BLOCKS intent detection."""

    @pytest.mark.parametrize(
        "message",
        [
            "create a decision record for the tech stack",
            "add a raci matrix",
            "create a risk register for the release",
            "create a timeline for the milestones",
            "add a kpi dashboard",
            "insert a checklist for the review",
            "draw a mermaid diagram",
            "add a pm block for the review",
            "add a form for data collection",
            "do sprint planning for next week",
            "run a risk assessment",
        ],
    )
    def test_pm_blocks_patterns(self, message: str) -> None:
        result = classify_intent(message)
        assert result.primary == UserIntent.PM_BLOCKS


class TestClassifyIntentProjectMgmt:
    """Tests for PROJECT_MGMT intent detection."""

    @pytest.mark.parametrize(
        "message",
        [
            "show the project status",
            "what is the current cycle",
            "check the velocity of the team",
            "show project progress",
            "update project settings",
            "create a project for the new feature",
            "what is the current sprint",
        ],
    )
    def test_project_mgmt_patterns(self, message: str) -> None:
        result = classify_intent(message)
        assert result.primary == UserIntent.PROJECT_MGMT


class TestClassifyIntentComment:
    """Tests for COMMENT intent detection."""

    @pytest.mark.parametrize(
        "message",
        [
            "add a comment on this task",
            "post a comment about the decision",
            "reply to the comment from yesterday",
            "start a thread about testing",
            "mention @alice in the note",
        ],
    )
    def test_comment_patterns(self, message: str) -> None:
        result = classify_intent(message)
        assert result.primary == UserIntent.COMMENT


class TestClassifyIntentGeneral:
    """Tests for GENERAL fallback."""

    def test_unrecognized_message(self) -> None:
        result = classify_intent("hello how are you")
        assert result.primary == UserIntent.GENERAL
        assert result.confidence == 0.5

    def test_empty_message(self) -> None:
        result = classify_intent("")
        assert result.primary == UserIntent.GENERAL

    def test_gibberish(self) -> None:
        result = classify_intent("asdfghjkl qwertyuiop")
        assert result.primary == UserIntent.GENERAL

    def test_state_alone_does_not_match_issue(self) -> None:
        result = classify_intent("describe the state of the application")
        assert result.primary != UserIntent.ISSUE_MGMT

    def test_project_alone_does_not_match_project_mgmt(self) -> None:
        result = classify_intent("write about the project architecture")
        assert result.primary != UserIntent.PROJECT_MGMT

    def test_risk_alone_does_not_match_pm_blocks(self) -> None:
        result = classify_intent("what is the risk of this approach")
        assert result.primary != UserIntent.PM_BLOCKS

    def test_issue_in_general_english_does_not_match(self) -> None:
        result = classify_intent("the issue is that we need more time")
        assert result.primary != UserIntent.ISSUE_MGMT

    def test_assign_in_general_english_does_not_match(self) -> None:
        result = classify_intent("assign a value to the variable")
        assert result.primary != UserIntent.ISSUE_MGMT


class TestWhitespaceNormalization:
    """Tests for whitespace normalization before matching."""

    def test_newlines_normalized(self) -> None:
        result = classify_intent("create\nan\nissue for the bug")
        assert result.primary == UserIntent.ISSUE_MGMT

    def test_extra_spaces_normalized(self) -> None:
        result = classify_intent("draft   a   document")
        assert result.primary == UserIntent.NOTE_WRITING

    def test_leading_trailing_stripped(self) -> None:
        result = classify_intent("  write a summary  ")
        assert result.primary == UserIntent.NOTE_WRITING


class TestNoteContextBias:
    """Tests for has_note_context bias."""

    def test_bias_toward_note_writing(self) -> None:
        result = classify_intent("hello", has_note_context=True)
        assert result.primary == UserIntent.NOTE_WRITING
        assert result.confidence == 0.4

    def test_no_bias_without_context(self) -> None:
        result = classify_intent("hello", has_note_context=False)
        assert result.primary == UserIntent.GENERAL

    def test_explicit_intent_overrides_bias(self) -> None:
        result = classify_intent("create an issue", has_note_context=True)
        assert result.primary == UserIntent.ISSUE_MGMT


class TestMultiIntentMessages:
    """Tests for messages matching multiple intents."""

    def test_dual_intent(self) -> None:
        result = classify_intent("write a summary and create an issue for the bug")
        assert result.primary is not None
        assert result.secondary is not None
        assert result.primary != result.secondary

    def test_confidence_below_one_for_mixed(self) -> None:
        result = classify_intent("draft a document and create an issue for the bug")
        assert result.confidence < 1.0


class TestConfidenceScoring:
    """Tests for confidence values."""

    def test_single_strong_match(self) -> None:
        result = classify_intent("create an issue for the bug in login")
        # Multiple issue patterns match → high confidence
        assert result.confidence > 0.5

    def test_general_fallback_confidence(self) -> None:
        result = classify_intent("what time is it")
        assert result.confidence == 0.5


class TestTieBreaking:
    """Tests for deterministic tie-breaking via priority."""

    def test_issue_beats_comment_on_tie(self) -> None:
        # "add a comment about this bug" matches COMMENT (add a comment) and ISSUE_MGMT (bug)
        result = classify_intent("add a comment about this bug")
        assert result.primary == UserIntent.ISSUE_MGMT
        assert result.secondary == UserIntent.COMMENT

    def test_note_writing_beats_comment_on_tie(self) -> None:
        # "write and post a comment" matches NOTE_WRITING (write) and COMMENT (post a comment)
        result = classify_intent("write and post a comment")
        assert result.primary == UserIntent.NOTE_WRITING
        assert result.secondary == UserIntent.COMMENT


class TestGetRulesForIntent:
    """Tests for get_rules_for_intent."""

    def test_note_writing_loads_notes_rule(self) -> None:
        classification = IntentClassification(primary=UserIntent.NOTE_WRITING)
        files, summaries = get_rules_for_intent(classification)
        assert "notes.md" in files
        assert any("issues.md" in s for s in summaries)
        assert any("pm_blocks.md" in s for s in summaries)

    def test_issue_mgmt_loads_issues_rule(self) -> None:
        classification = IntentClassification(primary=UserIntent.ISSUE_MGMT)
        files, summaries = get_rules_for_intent(classification)
        assert "issues.md" in files
        assert not any("issues.md" in s for s in summaries)

    def test_pm_blocks_loads_multiple_rules(self) -> None:
        classification = IntentClassification(primary=UserIntent.PM_BLOCKS)
        files, summaries = get_rules_for_intent(classification)
        assert "pm_blocks.md" in files
        assert "notes.md" in files
        # Only issues.md should be in summaries
        assert len(summaries) == 1
        assert "issues.md" in summaries[0]

    def test_general_loads_no_rules(self) -> None:
        classification = IntentClassification(primary=UserIntent.GENERAL)
        files, summaries = get_rules_for_intent(classification)
        assert files == []
        assert len(summaries) == len(RULE_SUMMARIES)

    def test_combined_primary_secondary(self) -> None:
        classification = IntentClassification(
            primary=UserIntent.NOTE_WRITING,
            secondary=UserIntent.ISSUE_MGMT,
        )
        files, summaries = get_rules_for_intent(classification)
        assert "notes.md" in files
        assert "issues.md" in files
        # Only pm_blocks.md not loaded
        assert len(summaries) == 1
        assert "pm_blocks.md" in summaries[0]

    def test_deduplication(self) -> None:
        classification = IntentClassification(
            primary=UserIntent.NOTE_WRITING,
            secondary=UserIntent.NOTE_READING,
        )
        files, _ = get_rules_for_intent(classification)
        # Both map to notes.md, should only appear once
        assert files.count("notes.md") == 1

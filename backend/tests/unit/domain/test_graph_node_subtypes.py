"""Unit tests for typed GraphNode subtypes.

Tests cover the typed build() factory on each subtype:
IssueNode, NoteNode, DecisionNode, LearnedPatternNode,
UserPreferenceNode, SkillOutcomeNode, ConversationSummaryNode.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from pilot_space.domain.graph_node import (
    ConversationSummaryNode,
    DecisionNode,
    GraphNode,
    IssueNode,
    LearnedPatternNode,
    NodeType,
    NoteNode,
    SkillOutcomeNode,
    UserPreferenceNode,
)

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# IssueNode
# ---------------------------------------------------------------------------


class TestIssueNode:
    """Tests for IssueNode.build() typed factory."""

    def test_build_sets_node_type_to_issue(self) -> None:
        node = IssueNode.build(
            workspace_id=uuid4(),
            label="PS-42",
            content="Fix the login bug",
            state="In Progress",
            priority="HIGH",
            identifier="PS-42",
            project_id=uuid4(),
        )
        assert node.node_type == NodeType.ISSUE

    def test_build_stores_required_properties(self) -> None:
        project_id = uuid4()
        node = IssueNode.build(
            workspace_id=uuid4(),
            label="PS-42",
            content="Fix the login bug",
            state="In Progress",
            priority="HIGH",
            identifier="PS-42",
            project_id=project_id,
        )
        assert node.properties["state"] == "In Progress"
        assert node.properties["priority"] == "HIGH"
        assert node.properties["identifier"] == "PS-42"
        assert node.properties["project_id"] == str(project_id)

    def test_build_returns_issue_node_instance(self) -> None:
        node = IssueNode.build(
            workspace_id=uuid4(),
            label="PS-1",
            content="content",
            state="Backlog",
            priority="NONE",
            identifier="PS-1",
            project_id=uuid4(),
        )
        assert isinstance(node, IssueNode)
        assert isinstance(node, GraphNode)

    def test_build_optional_external_and_user_id(self) -> None:
        ext = uuid4()
        uid = uuid4()
        node = IssueNode.build(
            workspace_id=uuid4(),
            label="PS-5",
            content="content",
            state="Todo",
            priority="LOW",
            identifier="PS-5",
            project_id=uuid4(),
            external_id=ext,
            user_id=uid,
        )
        assert node.external_id == ext
        assert node.user_id == uid


# ---------------------------------------------------------------------------
# NoteNode
# ---------------------------------------------------------------------------


class TestNoteNode:
    """Tests for NoteNode.build() typed factory."""

    def test_build_sets_node_type_to_note(self) -> None:
        node = NoteNode.build(
            workspace_id=uuid4(),
            label="Meeting Notes",
            content="Today we discussed...",
            title="Meeting Notes",
        )
        assert node.node_type == NodeType.NOTE

    def test_build_stores_title_in_properties(self) -> None:
        node = NoteNode.build(
            workspace_id=uuid4(),
            label="Sprint Planning",
            content="Sprint goals for Q1",
            title="Sprint Planning",
        )
        assert node.properties["title"] == "Sprint Planning"

    def test_build_returns_note_node_instance(self) -> None:
        node = NoteNode.build(
            workspace_id=uuid4(),
            label="Note",
            content="content",
            title="Note",
        )
        assert isinstance(node, NoteNode)


# ---------------------------------------------------------------------------
# DecisionNode
# ---------------------------------------------------------------------------


class TestDecisionNode:
    """Tests for DecisionNode.build() typed factory."""

    def test_build_sets_node_type_to_decision(self) -> None:
        node = DecisionNode.build(
            workspace_id=uuid4(),
            label="Use PostgreSQL",
            content="We chose PostgreSQL for ACID compliance",
            rationale="ACID compliance and pgvector support",
            decided_at=datetime(2024, 1, 15, tzinfo=UTC),
        )
        assert node.node_type == NodeType.DECISION

    def test_build_stores_rationale_and_decided_at(self) -> None:
        decided = datetime(2024, 6, 1, 12, 0, 0, tzinfo=UTC)
        node = DecisionNode.build(
            workspace_id=uuid4(),
            label="DD-001",
            content="Description of the decision",
            rationale="We need vector search",
            decided_at=decided,
        )
        assert node.properties["rationale"] == "We need vector search"
        assert node.properties["decided_at"] == decided.isoformat()

    def test_build_returns_decision_node_instance(self) -> None:
        node = DecisionNode.build(
            workspace_id=uuid4(),
            label="DD",
            content="desc",
            rationale="reason",
            decided_at=datetime.now(tz=UTC),
        )
        assert isinstance(node, DecisionNode)


# ---------------------------------------------------------------------------
# LearnedPatternNode
# ---------------------------------------------------------------------------


class TestLearnedPatternNode:
    """Tests for LearnedPatternNode.build() typed factory."""

    def test_build_sets_node_type(self) -> None:
        node = LearnedPatternNode.build(
            workspace_id=uuid4(),
            label="Pattern: DB naming",
            content="Users prefer snake_case table names",
            occurrence_count=5,
            confidence=0.9,
        )
        assert node.node_type == NodeType.LEARNED_PATTERN

    def test_build_stores_occurrence_count_and_confidence(self) -> None:
        node = LearnedPatternNode.build(
            workspace_id=uuid4(),
            label="Pattern",
            content="desc",
            occurrence_count=3,
            confidence=0.75,
        )
        assert node.properties["occurrence_count"] == 3
        assert node.properties["confidence"] == 0.75

    def test_build_returns_learned_pattern_node_instance(self) -> None:
        node = LearnedPatternNode.build(
            workspace_id=uuid4(),
            label="P",
            content="d",
            occurrence_count=1,
            confidence=0.5,
        )
        assert isinstance(node, LearnedPatternNode)


# ---------------------------------------------------------------------------
# UserPreferenceNode
# ---------------------------------------------------------------------------


class TestUserPreferenceNode:
    """Tests for UserPreferenceNode.build() typed factory."""

    def test_build_sets_node_type(self) -> None:
        node = UserPreferenceNode.build(
            workspace_id=uuid4(),
            label="dark_mode",
            content="User prefers dark mode",
            user_id=uuid4(),
            preference_key="ui.theme",
            preference_value="dark",
        )
        assert node.node_type == NodeType.USER_PREFERENCE

    def test_build_stores_preference_key_and_value(self) -> None:
        uid = uuid4()
        node = UserPreferenceNode.build(
            workspace_id=uuid4(),
            label="pref",
            content="user likes dark mode",
            user_id=uid,
            preference_key="ui.theme",
            preference_value="dark",
        )
        assert node.properties["preference_key"] == "ui.theme"
        assert node.properties["preference_value"] == "dark"
        assert node.user_id == uid

    def test_build_returns_user_preference_node_instance(self) -> None:
        node = UserPreferenceNode.build(
            workspace_id=uuid4(),
            label="p",
            content="d",
            user_id=uuid4(),
            preference_key="k",
            preference_value="v",
        )
        assert isinstance(node, UserPreferenceNode)


# ---------------------------------------------------------------------------
# SkillOutcomeNode
# ---------------------------------------------------------------------------


class TestSkillOutcomeNode:
    """Tests for SkillOutcomeNode.build() typed factory."""

    def test_build_sets_node_type(self) -> None:
        node = SkillOutcomeNode.build(
            workspace_id=uuid4(),
            label="improve-writing outcome",
            content="Rewrote 3 paragraphs for clarity",
            skill_name="improve-writing",
            outcome_summary="Rewrote 3 paragraphs",
        )
        assert node.node_type == NodeType.SKILL_OUTCOME

    def test_build_stores_skill_name_and_summary(self) -> None:
        node = SkillOutcomeNode.build(
            workspace_id=uuid4(),
            label="outcome",
            content="detail",
            skill_name="summarize",
            outcome_summary="Summarized 10 issues",
        )
        assert node.properties["skill_name"] == "summarize"
        assert node.properties["outcome_summary"] == "Summarized 10 issues"

    def test_build_returns_skill_outcome_node_instance(self) -> None:
        node = SkillOutcomeNode.build(
            workspace_id=uuid4(),
            label="o",
            content="d",
            skill_name="s",
            outcome_summary="sum",
        )
        assert isinstance(node, SkillOutcomeNode)


# ---------------------------------------------------------------------------
# ConversationSummaryNode
# ---------------------------------------------------------------------------


class TestConversationSummaryNode:
    """Tests for ConversationSummaryNode.build() typed factory."""

    def test_build_sets_node_type(self) -> None:
        node = ConversationSummaryNode.build(
            workspace_id=uuid4(),
            label="Session summary",
            content="We discussed sprint planning and priorities",
            session_id="sess_abc123",
            message_count=42,
        )
        assert node.node_type == NodeType.CONVERSATION_SUMMARY

    def test_build_stores_session_id_and_message_count(self) -> None:
        node = ConversationSummaryNode.build(
            workspace_id=uuid4(),
            label="summary",
            content="content",
            session_id="sess_xyz",
            message_count=10,
        )
        assert node.properties["session_id"] == "sess_xyz"
        assert node.properties["message_count"] == 10

    def test_build_returns_conversation_summary_node_instance(self) -> None:
        node = ConversationSummaryNode.build(
            workspace_id=uuid4(),
            label="s",
            content="d",
            session_id="id",
            message_count=1,
        )
        assert isinstance(node, ConversationSummaryNode)

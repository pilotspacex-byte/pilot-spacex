"""Unit tests for GraphNode base entity.

Tests cover:
- GraphNode construction and defaults
- NodeType enum values
- summary property
- GraphNode.create() factory
"""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

import pytest

from pilot_space.domain.graph_node import GraphNode, NodeType

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_node(**kwargs: Any) -> GraphNode:
    """Factory for GraphNode with sensible defaults."""
    defaults: dict[str, Any] = {
        "workspace_id": uuid4(),
        "node_type": NodeType.NOTE,
        "label": "Test Node",
        "content": "Some searchable content",
    }
    defaults.update(kwargs)
    return GraphNode(**defaults)


# ---------------------------------------------------------------------------
# NodeType enum
# ---------------------------------------------------------------------------


class TestNodeTypeEnum:
    """Tests for NodeType StrEnum values and behaviour."""

    def test_all_expected_values_defined(self) -> None:
        expected = {
            "issue",
            "note",
            "note_chunk",
            "project",
            "cycle",
            "user",
            "pull_request",
            "branch",
            "commit",
            "code_reference",
            "decision",
            "skill_outcome",
            "conversation_summary",
            "learned_pattern",
            "constitution_rule",
            "work_intent",
            "user_preference",
            "document",
            "document_chunk",
            "agent_turn",
            "user_correction",
            "pr_review_finding",
        }
        actual = {member.value for member in NodeType}
        assert actual == expected

    def test_node_type_is_str(self) -> None:
        assert isinstance(NodeType.ISSUE, str)

    def test_node_type_equality_with_string(self) -> None:
        assert NodeType.ISSUE == "issue"
        assert NodeType.LEARNED_PATTERN == "learned_pattern"


# ---------------------------------------------------------------------------
# GraphNode construction
# ---------------------------------------------------------------------------


class TestGraphNodeConstruction:
    """Tests for GraphNode initialization and field defaults."""

    def test_required_fields_stored_correctly(self) -> None:
        ws_id = uuid4()
        node = GraphNode(
            workspace_id=ws_id,
            node_type=NodeType.NOTE,
            label="My Note",
            content="Note content here",
        )
        assert node.workspace_id == ws_id
        assert node.node_type == NodeType.NOTE
        assert node.label == "My Note"
        assert node.content == "Note content here"

    def test_id_is_uuid_by_default(self) -> None:
        node = make_node()
        assert isinstance(node.id, UUID)

    def test_id_can_be_set_explicitly(self) -> None:
        fixed_id = uuid4()
        node = make_node(id=fixed_id)
        assert node.id == fixed_id

    def test_properties_defaults_to_empty_dict(self) -> None:
        node = make_node()
        assert node.properties == {}

    def test_embedding_defaults_to_none(self) -> None:
        node = make_node()
        assert node.embedding is None

    def test_user_id_defaults_to_none(self) -> None:
        node = make_node()
        assert node.user_id is None

    def test_external_id_defaults_to_none(self) -> None:
        node = make_node()
        assert node.external_id is None

    def test_created_at_is_utc_aware(self) -> None:
        node = make_node()
        assert node.created_at.tzinfo is not None

    def test_updated_at_is_utc_aware(self) -> None:
        node = make_node()
        assert node.updated_at.tzinfo is not None

    def test_two_nodes_have_distinct_ids(self) -> None:
        node_a = make_node()
        node_b = make_node()
        assert node_a.id != node_b.id

    def test_properties_stored_as_provided(self) -> None:
        props: dict[str, object] = {"state": "In Progress", "priority": "HIGH"}
        node = make_node(properties=props)
        assert node.properties["state"] == "In Progress"
        assert node.properties["priority"] == "HIGH"

    def test_embedding_stored_when_provided(self) -> None:
        vec = [0.1] * 1536
        node = make_node(embedding=vec)
        assert node.embedding == vec
        assert len(node.embedding) == 1536  # type: ignore[arg-type]

    def test_user_id_stored_when_provided(self) -> None:
        uid = uuid4()
        node = make_node(user_id=uid)
        assert node.user_id == uid

    def test_external_id_stored_when_provided(self) -> None:
        ext = uuid4()
        node = make_node(external_id=ext)
        assert node.external_id == ext


# ---------------------------------------------------------------------------
# summary property
# ---------------------------------------------------------------------------


class TestGraphNodeSummary:
    """Tests for the summary property."""

    def test_summary_returns_first_120_chars(self) -> None:
        node = make_node(content="x" * 200)
        assert node.summary == "x" * 120

    def test_summary_returns_full_content_when_short(self) -> None:
        node = make_node(content="short text")
        assert node.summary == "short text"

    def test_summary_exactly_120_chars_unchanged(self) -> None:
        content = "a" * 120
        node = make_node(content=content)
        assert node.summary == content

    def test_summary_empty_content(self) -> None:
        node = make_node(content="")
        assert node.summary == ""


# ---------------------------------------------------------------------------
# GraphNode.create() factory
# ---------------------------------------------------------------------------


class TestGraphNodeCreateFactory:
    """Tests for GraphNode.create() classmethod."""

    def test_create_returns_graph_node_instance(self) -> None:
        node = GraphNode.create(
            workspace_id=uuid4(),
            node_type=NodeType.DECISION,
            label="Decision label",
            content="We decided to use PostgreSQL",
        )
        assert isinstance(node, GraphNode)

    def test_create_applies_defaults(self) -> None:
        node = GraphNode.create(
            workspace_id=uuid4(),
            node_type=NodeType.NOTE,
            label="My note",
            content="Content",
        )
        assert node.properties == {}
        assert node.embedding is None
        assert node.user_id is None
        assert node.external_id is None

    def test_create_passes_optional_fields(self) -> None:
        uid = uuid4()
        ext = uuid4()
        props: dict[str, object] = {"key": "value"}
        node = GraphNode.create(
            workspace_id=uuid4(),
            node_type=NodeType.USER_PREFERENCE,
            label="Pref",
            content="User prefers dark mode",
            properties=props,
            user_id=uid,
            external_id=ext,
        )
        assert node.user_id == uid
        assert node.external_id == ext
        assert node.properties == props

    def test_create_gives_unique_ids(self) -> None:
        ws = uuid4()
        a = GraphNode.create(workspace_id=ws, node_type=NodeType.NOTE, label="A", content="A")
        b = GraphNode.create(workspace_id=ws, node_type=NodeType.NOTE, label="B", content="B")
        assert a.id != b.id

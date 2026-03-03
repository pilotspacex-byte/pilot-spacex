"""Unit tests for GraphEdge domain entity.

Tests cover:
- GraphEdge construction and defaults
- EdgeType enum values
- Weight validation (0.0-1.0)
- Self-loop prevention (source_id != target_id)
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest

from pilot_space.domain.graph_edge import EdgeType, GraphEdge

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_edge(**kwargs: Any) -> GraphEdge:
    """Factory for GraphEdge with sensible defaults."""
    defaults: dict[str, Any] = {
        "source_id": uuid4(),
        "target_id": uuid4(),
        "edge_type": EdgeType.RELATES_TO,
    }
    defaults.update(kwargs)
    return GraphEdge(**defaults)


# ---------------------------------------------------------------------------
# EdgeType enum
# ---------------------------------------------------------------------------


class TestEdgeTypeEnum:
    """Tests for EdgeType StrEnum values and behaviour."""

    def test_all_expected_values_defined(self) -> None:
        expected = {
            "relates_to",
            "caused_by",
            "led_to",
            "decided_in",
            "authored_by",
            "assigned_to",
            "belongs_to",
            "references",
            "learned_from",
            "summarizes",
            "blocks",
            "duplicates",
            "parent_of",
        }
        actual = {member.value for member in EdgeType}
        assert actual == expected

    def test_edge_type_is_str(self) -> None:
        assert isinstance(EdgeType.RELATES_TO, str)

    def test_edge_type_equality_with_string(self) -> None:
        assert EdgeType.BLOCKS == "blocks"
        assert EdgeType.PARENT_OF == "parent_of"


# ---------------------------------------------------------------------------
# GraphEdge construction
# ---------------------------------------------------------------------------


class TestGraphEdgeConstruction:
    """Tests for GraphEdge initialization and field defaults."""

    def test_required_fields_stored_correctly(self) -> None:
        src = uuid4()
        tgt = uuid4()
        edge = GraphEdge(
            source_id=src,
            target_id=tgt,
            edge_type=EdgeType.AUTHORED_BY,
        )
        assert edge.source_id == src
        assert edge.target_id == tgt
        assert edge.edge_type == EdgeType.AUTHORED_BY

    def test_id_is_uuid_by_default(self) -> None:
        edge = make_edge()
        from uuid import UUID

        assert isinstance(edge.id, UUID)

    def test_id_can_be_set_explicitly(self) -> None:
        fixed = uuid4()
        edge = make_edge(id=fixed)
        assert edge.id == fixed

    def test_weight_defaults_to_0_5(self) -> None:
        edge = make_edge()
        assert edge.weight == 0.5

    def test_properties_defaults_to_empty_dict(self) -> None:
        edge = make_edge()
        assert edge.properties == {}

    def test_created_at_is_utc_aware(self) -> None:
        edge = make_edge()
        assert edge.created_at.tzinfo is not None

    def test_properties_stored_when_provided(self) -> None:
        props: dict[str, object] = {"confidence": 0.9}
        edge = make_edge(properties=props)
        assert edge.properties["confidence"] == 0.9

    def test_weight_at_min_boundary(self) -> None:
        edge = make_edge(weight=0.0)
        assert edge.weight == 0.0

    def test_weight_at_max_boundary(self) -> None:
        edge = make_edge(weight=1.0)
        assert edge.weight == 1.0

    def test_weight_at_midpoint(self) -> None:
        edge = make_edge(weight=0.5)
        assert edge.weight == 0.5

    def test_two_edges_have_distinct_ids(self) -> None:
        a = make_edge()
        b = make_edge()
        assert a.id != b.id


# ---------------------------------------------------------------------------
# Weight validation
# ---------------------------------------------------------------------------


class TestGraphEdgeWeightValidation:
    """Tests for weight boundary enforcement."""

    def test_weight_below_0_raises(self) -> None:
        with pytest.raises(ValueError, match="weight"):
            make_edge(weight=-0.001)

    def test_weight_above_1_raises(self) -> None:
        with pytest.raises(ValueError, match="weight"):
            make_edge(weight=1.001)

    def test_weight_negative_large_raises(self) -> None:
        with pytest.raises(ValueError, match="weight"):
            make_edge(weight=-10.0)

    def test_weight_positive_large_raises(self) -> None:
        with pytest.raises(ValueError, match="weight"):
            make_edge(weight=2.0)

    def test_valid_weight_does_not_raise(self) -> None:
        edge = make_edge(weight=0.75)
        assert edge.weight == 0.75


# ---------------------------------------------------------------------------
# Self-loop prevention
# ---------------------------------------------------------------------------


class TestGraphEdgeSelfLoop:
    """Tests for self-loop invariant enforcement."""

    def test_self_loop_raises_value_error(self) -> None:
        same_id = uuid4()
        with pytest.raises(ValueError, match="Self-loop"):
            GraphEdge(
                source_id=same_id,
                target_id=same_id,
                edge_type=EdgeType.RELATES_TO,
            )

    def test_different_endpoints_does_not_raise(self) -> None:
        edge = make_edge(source_id=uuid4(), target_id=uuid4())
        assert edge.source_id != edge.target_id

    def test_self_loop_error_includes_id_in_message(self) -> None:
        same_id = uuid4()
        with pytest.raises(ValueError, match=str(same_id)):
            GraphEdge(
                source_id=same_id,
                target_id=same_id,
                edge_type=EdgeType.BLOCKS,
            )


# ---------------------------------------------------------------------------
# All EdgeType values can form valid edges
# ---------------------------------------------------------------------------


class TestAllEdgeTypesConstructible:
    """Verify each EdgeType can be used to construct a valid GraphEdge."""

    @pytest.mark.parametrize("edge_type", list(EdgeType))
    def test_edge_type_constructible(self, edge_type: EdgeType) -> None:
        edge = make_edge(edge_type=edge_type)
        assert edge.edge_type == edge_type

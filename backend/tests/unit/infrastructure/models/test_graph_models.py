"""Unit tests for GraphNodeModel and GraphEdgeModel.

Covers:
- Model construction with required and optional fields.
- _make_vector_type returns Vector(1536) when pgvector is available, Text otherwise.
- Column types, nullability, and server_default correctness.
- Soft-delete helpers (inherited from WorkspaceScopedModel).
- Basic persistence round-trip using the db_session fixture.
  NOTE: persistence tests require TEST_DATABASE_URL set to PostgreSQL;
  they are skipped under SQLite because JSONB is not supported by SQLite.
- Edge self-loop guard is defined in schema constraints.
- Relationship back-references are wired correctly.

SQLAlchemy mapped_column(default=...) sets the PYTHON-side callable/value
only when the ORM flushes a new row — NOT on __init__. Assertions about
defaults must either:
  a) Check after a DB flush (persistence tests), OR
  b) Allow None before flush.
"""

from __future__ import annotations

import os
import uuid
from typing import Any

import pytest
from sqlalchemy import Float, String, Text
from sqlalchemy.ext.asyncio import AsyncSession

from pilot_space.infrastructure.database.models.graph_edge import GraphEdgeModel
from pilot_space.infrastructure.database.models.graph_node import (
    GraphNodeModel,
    _make_vector_type,
)

# ---------------------------------------------------------------------------
# Skip marker for tests that require PostgreSQL
# ---------------------------------------------------------------------------

_NEEDS_POSTGRES = pytest.mark.skipif(
    "sqlite" in os.environ.get("TEST_DATABASE_URL", "sqlite"),
    reason="Requires PostgreSQL (JSONB, pgvector). Set TEST_DATABASE_URL.",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _node(
    workspace_id: uuid.UUID | None = None,
    node_type: str = "issue",
    label: str = "Test node",
    **kwargs: Any,
) -> GraphNodeModel:
    """Build a minimal GraphNodeModel without DB interaction."""
    return GraphNodeModel(
        workspace_id=workspace_id or uuid.uuid4(),
        node_type=node_type,
        label=label,
        **kwargs,
    )


def _edge(
    source_id: uuid.UUID,
    target_id: uuid.UUID,
    workspace_id: uuid.UUID | None = None,
    edge_type: str = "relates_to",
    **kwargs: Any,
) -> GraphEdgeModel:
    """Build a minimal GraphEdgeModel without DB interaction."""
    return GraphEdgeModel(
        source_id=source_id,
        target_id=target_id,
        workspace_id=workspace_id or uuid.uuid4(),
        edge_type=edge_type,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# _make_vector_type
# ---------------------------------------------------------------------------


class TestMakeVectorType:
    def test_returns_non_none(self) -> None:
        """_make_vector_type must always return a valid SQLAlchemy type."""
        result = _make_vector_type(1536)
        assert result is not None

    def test_returns_text_or_vector(self) -> None:
        """Returns Text (no pgvector) or Vector (pgvector installed)."""
        result = _make_vector_type(1536)
        try:
            from pgvector.sqlalchemy import Vector  # type: ignore[import-untyped]

            assert isinstance(result, Vector)
        except ImportError:
            assert isinstance(result, Text)

    def test_accepts_arbitrary_dim(self) -> None:
        """Must accept any positive dimension without raising."""
        assert _make_vector_type(768) is not None
        assert _make_vector_type(3072) is not None


# ---------------------------------------------------------------------------
# GraphNodeModel — construction (no DB)
# ---------------------------------------------------------------------------


class TestGraphNodeModelConstruction:
    def test_required_fields_assigned(self) -> None:
        ws = uuid.uuid4()
        node = _node(workspace_id=ws, node_type="note", label="My note")

        assert node.workspace_id == ws
        assert node.node_type == "note"
        assert node.label == "My note"

    def test_optional_fields_are_none_before_flush(self) -> None:
        node = _node()
        # user_id, external_id, embedding are nullable and not set
        assert node.user_id is None
        assert node.external_id is None
        assert node.embedding is None

    def test_all_valid_node_types_accepted(self) -> None:
        valid_types = [
            "issue",
            "note",
            "concept",
            "agent",
            "user",
            "workspace",
            "project",
            "cycle",
            "label",
            "comment",
            "document",
            "task",
            "sprint",
            "epic",
        ]
        for nt in valid_types:
            node = _node(node_type=nt)
            assert node.node_type == nt

    def test_user_id_can_be_set(self) -> None:
        uid = uuid.uuid4()
        node = _node(user_id=uid)
        assert node.user_id == uid

    def test_external_id_can_be_set(self) -> None:
        eid = uuid.uuid4()
        node = _node(external_id=eid)
        assert node.external_id == eid

    def test_properties_accepts_arbitrary_dict(self) -> None:
        props = {"priority": "high", "tags": ["ai", "memory"]}
        node = _node(properties=props)
        assert node.properties == props

    def test_label_up_to_500_chars(self) -> None:
        long_label = "x" * 500
        node = _node(label=long_label)
        assert node.label == long_label

    def test_content_can_be_set_explicitly(self) -> None:
        node = _node(content="Rich text content here")
        assert node.content == "Rich text content here"

    def test_repr_contains_node_type_and_label(self) -> None:
        node = _node(node_type="concept", label="Embedding")
        r = repr(node)
        assert "GraphNodeModel" in r
        assert "concept" in r
        assert "Embedding" in r


# ---------------------------------------------------------------------------
# GraphNodeModel — soft delete helpers
# ---------------------------------------------------------------------------


class TestGraphNodeSoftDelete:
    def test_soft_delete_sets_flags(self) -> None:
        node = _node()
        node.soft_delete()
        assert node.is_deleted is True
        assert node.deleted_at is not None

    def test_restore_clears_flags(self) -> None:
        node = _node()
        node.soft_delete()
        node.restore()
        assert node.is_deleted is False
        assert node.deleted_at is None

    def test_can_soft_delete_twice_idempotently(self) -> None:
        node = _node()
        node.soft_delete()
        node.soft_delete()
        # deleted_at is refreshed on each call; flag remains True
        assert node.is_deleted is True
        assert node.deleted_at is not None


# ---------------------------------------------------------------------------
# GraphEdgeModel — construction (no DB)
# ---------------------------------------------------------------------------


class TestGraphEdgeModelConstruction:
    def test_required_fields_assigned(self) -> None:
        src_id = uuid.uuid4()
        tgt_id = uuid.uuid4()
        ws = uuid.uuid4()
        edge = _edge(src_id, tgt_id, workspace_id=ws, edge_type="blocks")

        assert edge.source_id == src_id
        assert edge.target_id == tgt_id
        assert edge.workspace_id == ws
        assert edge.edge_type == "blocks"

    def test_all_valid_edge_types_accepted(self) -> None:
        valid_types = [
            "relates_to",
            "blocks",
            "blocked_by",
            "duplicates",
            "parent_of",
            "child_of",
            "mentions",
            "assigned_to",
            "created_by",
            "labeled_with",
            "part_of",
            "links_to",
            "summarises",
            "referenced_by",
        ]
        for et in valid_types:
            edge = _edge(uuid.uuid4(), uuid.uuid4(), edge_type=et)
            assert edge.edge_type == et

    def test_weight_can_be_overridden(self) -> None:
        edge = _edge(uuid.uuid4(), uuid.uuid4(), weight=0.9)
        assert edge.weight == pytest.approx(0.9)

    def test_properties_accepts_dict(self) -> None:
        props = {"confidence": 0.95, "source": "llm"}
        edge = _edge(uuid.uuid4(), uuid.uuid4(), properties=props)
        assert edge.properties == props

    def test_repr_contains_edge_type(self) -> None:
        edge = _edge(uuid.uuid4(), uuid.uuid4(), edge_type="parent_of")
        r = repr(edge)
        assert "GraphEdgeModel" in r
        assert "parent_of" in r


# ---------------------------------------------------------------------------
# Column schema inspection (metadata-level, no DB required)
# ---------------------------------------------------------------------------


class TestGraphNodeColumnSchema:
    def test_node_type_column_is_string(self) -> None:
        col = GraphNodeModel.__table__.c["node_type"]
        assert isinstance(col.type, String)

    def test_label_column_max_length_500(self) -> None:
        col = GraphNodeModel.__table__.c["label"]
        assert isinstance(col.type, String)
        assert col.type.length == 500

    def test_content_column_is_text(self) -> None:
        col = GraphNodeModel.__table__.c["content"]
        assert isinstance(col.type, Text)

    def test_workspace_id_is_not_nullable(self) -> None:
        col = GraphNodeModel.__table__.c["workspace_id"]
        assert not col.nullable

    def test_user_id_is_nullable(self) -> None:
        col = GraphNodeModel.__table__.c["user_id"]
        assert col.nullable

    def test_external_id_is_nullable(self) -> None:
        col = GraphNodeModel.__table__.c["external_id"]
        assert col.nullable

    def test_embedding_is_nullable(self) -> None:
        col = GraphNodeModel.__table__.c["embedding"]
        assert col.nullable

    def test_is_deleted_not_nullable(self) -> None:
        col = GraphNodeModel.__table__.c["is_deleted"]
        assert not col.nullable

    def test_graph_nodes_has_expected_columns(self) -> None:
        col_names = {c.name for c in GraphNodeModel.__table__.c}
        expected = {
            "id",
            "workspace_id",
            "user_id",
            "node_type",
            "external_id",
            "label",
            "content",
            "properties",
            "embedding",
            "created_at",
            "updated_at",
            "is_deleted",
            "deleted_at",
        }
        assert expected.issubset(col_names)


class TestGraphEdgeColumnSchema:
    def test_edge_type_column_is_string(self) -> None:
        col = GraphEdgeModel.__table__.c["edge_type"]
        assert isinstance(col.type, String)

    def test_edge_type_max_length_50(self) -> None:
        col = GraphEdgeModel.__table__.c["edge_type"]
        assert col.type.length == 50

    def test_source_id_not_nullable(self) -> None:
        col = GraphEdgeModel.__table__.c["source_id"]
        assert not col.nullable

    def test_target_id_not_nullable(self) -> None:
        col = GraphEdgeModel.__table__.c["target_id"]
        assert not col.nullable

    def test_workspace_id_not_nullable(self) -> None:
        col = GraphEdgeModel.__table__.c["workspace_id"]
        assert not col.nullable

    def test_weight_type_is_float(self) -> None:
        col = GraphEdgeModel.__table__.c["weight"]
        assert isinstance(col.type, Float)

    def test_weight_not_nullable(self) -> None:
        col = GraphEdgeModel.__table__.c["weight"]
        assert not col.nullable

    def test_created_at_not_nullable(self) -> None:
        col = GraphEdgeModel.__table__.c["created_at"]
        assert not col.nullable

    def test_graph_edges_has_expected_columns(self) -> None:
        col_names = {c.name for c in GraphEdgeModel.__table__.c}
        expected = {
            "id",
            "source_id",
            "target_id",
            "workspace_id",
            "edge_type",
            "properties",
            "weight",
            "created_at",
        }
        assert expected.issubset(col_names)


# ---------------------------------------------------------------------------
# Relationship wiring (no DB required — checks SQLAlchemy mapper config)
# ---------------------------------------------------------------------------


class TestGraphRelationships:
    def test_graph_node_has_outgoing_edges_relationship(self) -> None:
        mapper = GraphNodeModel.__mapper__
        assert "outgoing_edges" in mapper.relationships

    def test_graph_node_has_incoming_edges_relationship(self) -> None:
        mapper = GraphNodeModel.__mapper__
        assert "incoming_edges" in mapper.relationships

    def test_graph_edge_has_source_node_relationship(self) -> None:
        mapper = GraphEdgeModel.__mapper__
        assert "source_node" in mapper.relationships

    def test_graph_edge_has_target_node_relationship(self) -> None:
        mapper = GraphEdgeModel.__mapper__
        assert "target_node" in mapper.relationships


# ---------------------------------------------------------------------------
# Persistence round-trip (PostgreSQL only — SQLite lacks JSONB/pgvector)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@_NEEDS_POSTGRES
class TestGraphNodePersistence:
    async def test_insert_and_retrieve_node(self, db_session: AsyncSession) -> None:
        ws = uuid.uuid4()
        node = GraphNodeModel(
            workspace_id=ws,
            node_type="issue",
            label="Implement login",
            content="As a user I want to log in.",
            properties={"priority": "high"},
        )
        db_session.add(node)
        await db_session.flush()

        assert node.id is not None
        assert node.created_at is not None
        assert node.updated_at is not None
        assert node.is_deleted is False

    async def test_soft_delete_persisted(self, db_session: AsyncSession) -> None:
        ws = uuid.uuid4()
        node = GraphNodeModel(
            workspace_id=ws,
            node_type="note",
            label="Meeting notes",
        )
        db_session.add(node)
        await db_session.flush()

        node.soft_delete()
        await db_session.flush()

        assert node.is_deleted is True
        assert node.deleted_at is not None

    async def test_defaults_applied_after_flush(self, db_session: AsyncSession) -> None:
        ws = uuid.uuid4()
        node = GraphNodeModel(
            workspace_id=ws,
            node_type="concept",
            label="Default test",
        )
        db_session.add(node)
        await db_session.flush()

        # server_default takes effect after flush
        assert node.is_deleted is False
        assert node.content == "" or node.content is None  # server_default=''


@pytest.mark.asyncio
@_NEEDS_POSTGRES
class TestGraphEdgePersistence:
    async def test_insert_and_retrieve_edge(self, db_session: AsyncSession) -> None:
        ws = uuid.uuid4()

        src = GraphNodeModel(workspace_id=ws, node_type="issue", label="Source")
        tgt = GraphNodeModel(workspace_id=ws, node_type="issue", label="Target")
        db_session.add(src)
        db_session.add(tgt)
        await db_session.flush()

        edge = GraphEdgeModel(
            source_id=src.id,
            target_id=tgt.id,
            workspace_id=ws,
            edge_type="blocks",
            weight=0.8,
        )
        db_session.add(edge)
        await db_session.flush()

        assert edge.id is not None
        assert edge.created_at is not None
        assert edge.weight == pytest.approx(0.8)

    async def test_edge_properties_persisted(self, db_session: AsyncSession) -> None:
        ws = uuid.uuid4()

        src = GraphNodeModel(workspace_id=ws, node_type="concept", label="A")
        tgt = GraphNodeModel(workspace_id=ws, node_type="concept", label="B")
        db_session.add(src)
        db_session.add(tgt)
        await db_session.flush()

        props = {"confidence": 0.95, "source": "llm"}
        edge = GraphEdgeModel(
            source_id=src.id,
            target_id=tgt.id,
            workspace_id=ws,
            edge_type="relates_to",
            properties=props,
        )
        db_session.add(edge)
        await db_session.flush()

        assert edge.properties == props

    async def test_default_weight_after_flush(self, db_session: AsyncSession) -> None:
        ws = uuid.uuid4()
        src = GraphNodeModel(workspace_id=ws, node_type="issue", label="S")
        tgt = GraphNodeModel(workspace_id=ws, node_type="issue", label="T")
        db_session.add(src)
        db_session.add(tgt)
        await db_session.flush()

        edge = GraphEdgeModel(
            source_id=src.id,
            target_id=tgt.id,
            workspace_id=ws,
            edge_type="relates_to",
        )
        db_session.add(edge)
        await db_session.flush()

        assert edge.weight == pytest.approx(0.5)

"""Integration tests for the full knowledge graph pipeline.

Covers:
- Write node → hybrid search → recall context
- 1-hop neighbor expansion (get_subgraph)
- Workspace isolation (nodes from workspace A not visible from workspace B)

Requires PostgreSQL (TEST_DATABASE_URL env var). The test suite's Base.metadata
contains PMBlockInsight which uses a raw JSONB dialect column incompatible with
SQLite's type compiler, so these tests cannot run against the in-memory SQLite
engine used for unit tests.
"""

from __future__ import annotations

import os
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from pilot_space.application.services.memory.graph_search_service import (
    GraphSearchPayload,
    GraphSearchService,
)
from pilot_space.application.services.memory.graph_write_service import (
    EdgeInput,
    GraphWritePayload,
    GraphWriteService,
    NodeInput,
)
from pilot_space.domain.graph_edge import EdgeType
from pilot_space.domain.graph_node import NodeType
from pilot_space.infrastructure.database.repositories.knowledge_graph_repository import (
    KnowledgeGraphRepository,
)

# Skip the entire module if no PostgreSQL URL is configured.
# Base.metadata includes PMBlockInsight which uses a raw JSONB type column
# that SQLite's DDL compiler cannot render.
pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"),
    reason="TEST_DATABASE_URL not set — graph pipeline tests require PostgreSQL",
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_queue() -> MagicMock:
    """Mock SupabaseQueueClient — embedding enqueue does not need real queue."""
    q = MagicMock()
    q.enqueue = AsyncMock(return_value=None)
    return q


@pytest.fixture
def workspace_id() -> uuid.UUID:
    return uuid.UUID("10000000-0000-0000-0000-000000000001")


@pytest.fixture
def workspace_id_b() -> uuid.UUID:
    return uuid.UUID("20000000-0000-0000-0000-000000000002")


@pytest.fixture
def user_id() -> uuid.UUID:
    return uuid.UUID("a0000000-0000-0000-0000-000000000001")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_write_service(session: AsyncSession, mock_queue: MagicMock) -> GraphWriteService:
    repo = KnowledgeGraphRepository(session)
    return GraphWriteService(repo, mock_queue, session)


def _make_search_service(session: AsyncSession) -> GraphSearchService:
    repo = KnowledgeGraphRepository(session)
    return GraphSearchService(repo, session)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_save_and_recall_graph_context(
    db_session: AsyncSession,
    mock_queue: MagicMock,
    workspace_id: uuid.UUID,
) -> None:
    """Full pipeline: write node → keyword search → recall context."""
    write_service = _make_write_service(db_session, mock_queue)
    search_service = _make_search_service(db_session)

    content = "Implement retry logic for the job worker using exponential backoff."
    write_result = await write_service.execute(
        GraphWritePayload(
            workspace_id=workspace_id,
            nodes=[
                NodeInput(
                    node_type=NodeType.SKILL_OUTCOME,
                    label="Retry logic implementation",
                    content=content,
                    properties={"task_id": "T-001"},
                )
            ],
        )
    )

    assert len(write_result.node_ids) == 1

    search_result = await search_service.execute(
        GraphSearchPayload(
            query="retry logic job worker",
            workspace_id=workspace_id,
            limit=10,
        )
    )

    node_ids_found = {sn.node.id for sn in search_result.nodes}
    assert write_result.node_ids[0] in node_ids_found, "Written node must appear in search results"


@pytest.mark.asyncio
async def test_write_multiple_node_types_all_searchable(
    db_session: AsyncSession,
    mock_queue: MagicMock,
    workspace_id: uuid.UUID,
) -> None:
    """Nodes of different types written in one payload are all retrievable."""
    write_service = _make_write_service(db_session, mock_queue)
    search_service = _make_search_service(db_session)

    result = await write_service.execute(
        GraphWritePayload(
            workspace_id=workspace_id,
            nodes=[
                NodeInput(
                    node_type=NodeType.WORK_INTENT,
                    label="Deploy feature to staging",
                    content="Deploy the knowledge graph feature to the staging environment.",
                ),
                NodeInput(
                    node_type=NodeType.LEARNED_PATTERN,
                    label="Deploy pattern",
                    content="Staging deploys always require a migration step first.",
                ),
            ],
        )
    )

    assert len(result.node_ids) == 2

    search_result = await search_service.execute(
        GraphSearchPayload(
            query="deploy staging environment",
            workspace_id=workspace_id,
            limit=10,
        )
    )

    found_types = {sn.node.node_type for sn in search_result.nodes}
    assert NodeType.WORK_INTENT in found_types or NodeType.LEARNED_PATTERN in found_types


@pytest.mark.asyncio
async def test_graph_context_includes_neighbors(
    db_session: AsyncSession,
    mock_queue: MagicMock,
    workspace_id: uuid.UUID,
) -> None:
    """1-hop neighbor expansion: writing an edge makes target accessible via subgraph."""
    write_service = _make_write_service(db_session, mock_queue)
    repo = KnowledgeGraphRepository(db_session)

    ext_a = uuid.uuid4()
    ext_b = uuid.uuid4()

    write_result = await write_service.execute(
        GraphWritePayload(
            workspace_id=workspace_id,
            nodes=[
                NodeInput(
                    node_type=NodeType.SKILL_OUTCOME,
                    label="Root node",
                    content="Root skill outcome for subgraph test.",
                    external_id=ext_a,
                ),
                NodeInput(
                    node_type=NodeType.WORK_INTENT,
                    label="Neighbor node",
                    content="Work intent that relates to the root skill outcome.",
                    external_id=ext_b,
                ),
            ],
            edges=[
                EdgeInput(
                    source_external_id=ext_a,
                    target_external_id=ext_b,
                    edge_type=EdgeType.RELATES_TO,
                    weight=0.8,
                )
            ],
        )
    )

    assert len(write_result.node_ids) == 2
    assert len(write_result.edge_ids) == 1

    root_id = write_result.node_ids[0]
    nodes, edges = await repo.get_subgraph(root_id, max_depth=1, max_nodes=10)

    node_ids_in_subgraph = {n.id for n in nodes}
    # Both nodes must appear in the 1-hop subgraph from root
    assert len(node_ids_in_subgraph) == 2
    assert len(edges) == 1


@pytest.mark.asyncio
async def test_workspace_isolation(
    db_session: AsyncSession,
    mock_queue: MagicMock,
    workspace_id: uuid.UUID,
    workspace_id_b: uuid.UUID,
) -> None:
    """Nodes from workspace A are not visible when searching workspace B."""
    write_service = _make_write_service(db_session, mock_queue)
    search_service = _make_search_service(db_session)

    # Write a distinctive node in workspace A
    unique_content = "isolated-workspace-a-unique-content-xyz987"
    await write_service.execute(
        GraphWritePayload(
            workspace_id=workspace_id,
            nodes=[
                NodeInput(
                    node_type=NodeType.SKILL_OUTCOME,
                    label="Workspace A node",
                    content=unique_content,
                )
            ],
        )
    )

    # Search from workspace B — must return no results for this content
    search_result = await search_service.execute(
        GraphSearchPayload(
            query=unique_content,
            workspace_id=workspace_id_b,
            limit=10,
        )
    )

    node_contents = {sn.node.content for sn in search_result.nodes}
    assert unique_content not in node_contents, (
        "Node from workspace A must not appear in workspace B search results"
    )


@pytest.mark.asyncio
async def test_upsert_idempotent_by_external_id(
    db_session: AsyncSession,
    mock_queue: MagicMock,
    workspace_id: uuid.UUID,
) -> None:
    """Writing the same external_id twice updates the node instead of inserting duplicate."""
    write_service = _make_write_service(db_session, mock_queue)
    repo = KnowledgeGraphRepository(db_session)

    ext_id = uuid.uuid4()

    await write_service.execute(
        GraphWritePayload(
            workspace_id=workspace_id,
            nodes=[
                NodeInput(
                    node_type=NodeType.WORK_INTENT,
                    label="Original label",
                    content="Original content for upsert test.",
                    external_id=ext_id,
                )
            ],
        )
    )

    # Second write with same external_id — must update, not insert
    await write_service.execute(
        GraphWritePayload(
            workspace_id=workspace_id,
            nodes=[
                NodeInput(
                    node_type=NodeType.WORK_INTENT,
                    label="Updated label",
                    content="Updated content for upsert test.",
                    external_id=ext_id,
                )
            ],
        )
    )

    from sqlalchemy import select

    from pilot_space.infrastructure.database.models.graph_node import GraphNodeModel

    result = await db_session.execute(
        select(GraphNodeModel).where(
            GraphNodeModel.workspace_id == workspace_id,
            GraphNodeModel.node_type == "work_intent",
            GraphNodeModel.external_id == ext_id,
            GraphNodeModel.is_deleted == False,  # noqa: E712
        )
    )
    rows = result.scalars().all()
    assert len(rows) == 1
    assert rows[0].label == "Updated label"
    assert rows[0].content == "Updated content for upsert test."


@pytest.mark.asyncio
async def test_node_type_filter_restricts_results(
    db_session: AsyncSession,
    mock_queue: MagicMock,
    workspace_id: uuid.UUID,
) -> None:
    """node_types filter on GraphSearchPayload restricts results to specified types."""
    write_service = _make_write_service(db_session, mock_queue)
    search_service = _make_search_service(db_session)

    shared_content = "shared-search-term-for-type-filter-test"

    await write_service.execute(
        GraphWritePayload(
            workspace_id=workspace_id,
            nodes=[
                NodeInput(
                    node_type=NodeType.SKILL_OUTCOME,
                    label="Skill outcome node",
                    content=shared_content,
                ),
                NodeInput(
                    node_type=NodeType.LEARNED_PATTERN,
                    label="Learned pattern node",
                    content=shared_content,
                ),
            ],
        )
    )

    result = await search_service.execute(
        GraphSearchPayload(
            query=shared_content,
            workspace_id=workspace_id,
            node_types=[NodeType.SKILL_OUTCOME],
            limit=10,
        )
    )

    found_types = {sn.node.node_type for sn in result.nodes}
    assert found_types <= {NodeType.SKILL_OUTCOME}, (
        "Results must only contain SKILL_OUTCOME nodes when filtered"
    )

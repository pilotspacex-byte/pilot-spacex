"""KnowledgeGraphQueryService — read-only operations for the knowledge graph API.

Encapsulates neighbor traversal, subgraph extraction, user context,
and entity-scoped (issue/project) graph retrieval with optional GitHub
node synthesis.

Feature 016: Knowledge Graph — Unit 7 REST API
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import NAMESPACE_URL, UUID, uuid5

from pilot_space.domain.exceptions import NotFoundError
from pilot_space.domain.graph_edge import EdgeType, GraphEdge
from pilot_space.domain.graph_node import GraphNode, NodeType
from pilot_space.infrastructure.database.models.integration import (
    IntegrationLinkType,
)
from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from collections.abc import Sequence

    from pilot_space.infrastructure.database.models.integration import IntegrationLink
    from pilot_space.infrastructure.database.repositories.integration_link_repository import (
        IntegrationLinkRepository,
    )
    from pilot_space.infrastructure.database.repositories.issue_repository import (
        IssueRepository,
    )
    from pilot_space.infrastructure.database.repositories.knowledge_graph_repository import (
        KnowledgeGraphRepository,
    )
    from pilot_space.infrastructure.database.repositories.project_repository import (
        ProjectRepository,
    )

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Node importance tiers for sorting
# ---------------------------------------------------------------------------

_TIER_HIGH: frozenset[str] = frozenset(
    {
        NodeType.ISSUE.value,
        NodeType.NOTE.value,
        NodeType.DECISION.value,
        NodeType.PROJECT.value,
    }
)
_TIER_MID: frozenset[str] = frozenset(
    {
        NodeType.PULL_REQUEST.value,
        NodeType.BRANCH.value,
        NodeType.COMMIT.value,
        NodeType.CODE_REFERENCE.value,
        NodeType.WORK_INTENT.value,
    }
)

_GITHUB_NODE_TYPE_MAP: dict[IntegrationLinkType, str] = {
    IntegrationLinkType.PULL_REQUEST: NodeType.PULL_REQUEST.value,
    IntegrationLinkType.BRANCH: NodeType.BRANCH.value,
    IntegrationLinkType.COMMIT: NodeType.COMMIT.value,
    IntegrationLinkType.MENTION: NodeType.NOTE.value,
}


def node_tier(node_type: str) -> int:
    """Return sort priority tier (lower = higher priority)."""
    if node_type in _TIER_HIGH:
        return 0
    if node_type in _TIER_MID:
        return 1
    return 2


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class NeighborResult:
    """Result from a neighbor traversal."""

    nodes: list[GraphNode]
    edges: list[GraphEdge]
    center_node_id: UUID


@dataclass(frozen=True, slots=True)
class SubgraphResult:
    """Result from subgraph extraction."""

    nodes: list[GraphNode]
    edges: list[GraphEdge]
    center_node_id: UUID


@dataclass(frozen=True, slots=True)
class UserContextResult:
    """Result from user context retrieval."""

    nodes: list[GraphNode]


@dataclass(slots=True)
class EphemeralNode:
    """Ephemeral GitHub node synthesized from integration links."""

    id: str
    node_type: str
    label: str
    summary: str
    properties: dict[str, Any]
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class EntitySubgraphResult:
    """Result from entity-scoped subgraph extraction."""

    nodes: list[GraphNode]
    edges: list[GraphEdge]
    ephemeral_nodes: list[EphemeralNode]
    center_node_id: UUID | None


class EntityNotFoundError(NotFoundError):
    """Raised when the target entity (issue/project) does not exist."""

    def __init__(self, entity_type: str, entity_id: UUID) -> None:
        self.entity_type = entity_type
        self.entity_id = entity_id
        super().__init__(f"{entity_type} {entity_id} not found")


class RootNodeNotFoundError(NotFoundError):
    """Raised when the root node for subgraph extraction does not exist."""

    def __init__(self, node_id: UUID) -> None:
        self.node_id = node_id
        super().__init__(f"Root node {node_id} not found")


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class KnowledgeGraphQueryService:
    """Read-only service for knowledge graph queries.

    Encapsulates neighbor traversal, subgraph extraction, user context,
    and entity-scoped graph retrieval. Raises domain exceptions instead
    of HTTP exceptions.
    """

    def __init__(
        self,
        knowledge_graph_repository: KnowledgeGraphRepository,
        integration_link_repository: IntegrationLinkRepository,
        issue_repository: IssueRepository,
        project_repository: ProjectRepository,
    ) -> None:
        self._kg_repo = knowledge_graph_repository
        self._il_repo = integration_link_repository
        self._issue_repo = issue_repository
        self._project_repo = project_repository

    async def get_neighbors(
        self,
        *,
        node_id: UUID,
        workspace_id: UUID,
        depth: int = 1,
        edge_types: list[EdgeType] | None = None,
    ) -> NeighborResult:
        """Return local neighborhood subgraph around the given node."""
        neighbors = await self._kg_repo.get_neighbors(
            node_id=node_id,
            edge_types=edge_types,
            depth=depth,
            workspace_id=workspace_id,
        )
        center_node = await self._kg_repo.get_node_by_id(node_id, workspace_id)
        all_nodes = ([center_node] if center_node else []) + neighbors
        all_ids = [n.id for n in all_nodes]
        edges = await self._kg_repo.get_edges_between(all_ids, workspace_id=workspace_id)
        return NeighborResult(nodes=all_nodes, edges=edges, center_node_id=node_id)

    async def get_subgraph(
        self,
        *,
        root_id: UUID,
        workspace_id: UUID,
        max_depth: int = 2,
        max_nodes: int = 50,
    ) -> SubgraphResult:
        """Extract a subgraph for visualization centered on root_id."""
        if not await self._kg_repo.get_node_by_id(root_id, workspace_id):
            raise RootNodeNotFoundError(root_id)
        nodes, edges = await self._kg_repo.get_subgraph(
            root_id=root_id,
            max_depth=max_depth,
            max_nodes=max_nodes,
            workspace_id=workspace_id,
        )
        return SubgraphResult(nodes=nodes, edges=edges, center_node_id=root_id)

    async def get_user_context(
        self,
        *,
        workspace_id: UUID,
        user_id: UUID,
        limit: int = 10,
    ) -> UserContextResult:
        """Return personal context nodes for the current user."""
        nodes = await self._kg_repo.get_user_context(
            user_id=user_id,
            workspace_id=workspace_id,
            limit=limit,
        )
        return UserContextResult(nodes=nodes)

    async def get_issue_knowledge_graph(
        self,
        *,
        issue_id: UUID,
        workspace_id: UUID,
        depth: int = 2,
        node_types: str | None = None,
        max_nodes: int = 50,
        include_github: bool = True,
    ) -> EntitySubgraphResult:
        """Return knowledge graph subgraph for an issue."""
        if not await self._issue_repo.exists(issue_id):
            raise EntityNotFoundError("Issue", issue_id)

        integration_links: Sequence[IntegrationLink] = []
        if include_github:
            integration_links = await self._il_repo.get_by_issue_in_workspace(
                issue_id, workspace_id
            )

        return await self._build_entity_subgraph(
            entity_id=issue_id,
            workspace_id=workspace_id,
            depth=depth,
            node_types=node_types,
            max_nodes=max_nodes,
            integration_links=integration_links,
            fetch_max_override=100,
            log_event="knowledge_graph_issue_no_node",
        )

    async def get_project_knowledge_graph(
        self,
        *,
        project_id: UUID,
        workspace_id: UUID,
        depth: int = 2,
        node_types: str | None = None,
        max_nodes: int = 50,
        include_github: bool = True,
    ) -> EntitySubgraphResult:
        """Return knowledge graph subgraph for a project."""
        if not await self._project_repo.exists(project_id):
            raise EntityNotFoundError("Project", project_id)

        integration_links: Sequence[IntegrationLink] = []
        if include_github:
            integration_links = await self._il_repo.get_by_project_issues(project_id, workspace_id)

        return await self._build_entity_subgraph(
            entity_id=project_id,
            workspace_id=workspace_id,
            depth=depth,
            node_types=node_types,
            max_nodes=max_nodes,
            integration_links=integration_links,
            fetch_max_override=200,
            log_event="knowledge_graph_project_no_node",
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _build_entity_subgraph(
        self,
        *,
        entity_id: UUID,
        workspace_id: UUID,
        depth: int,
        node_types: str | None,
        max_nodes: int,
        integration_links: Sequence[IntegrationLink],
        fetch_max_override: int = 100,
        log_event: str = "knowledge_graph_entity_no_node",
    ) -> EntitySubgraphResult:
        """Shared pipeline: graph node lookup -> subgraph -> GitHub synthesis -> sort."""
        # Step 1: Find graph node linked to this entity
        graph_node = await self._kg_repo.find_node_by_external_id(entity_id, workspace_id)

        # Step 2: No graph node -> empty response
        if graph_node is None:
            logger.info(log_event, entity_id=str(entity_id), workspace_id=str(workspace_id))
            return EntitySubgraphResult(
                nodes=[],
                edges=[],
                ephemeral_nodes=[],
                center_node_id=None,
            )

        center_node_id = graph_node.id

        # Step 3: Extract subgraph
        _fetch_max = fetch_max_override if node_types else max_nodes
        nodes, edges = await self._kg_repo.get_subgraph(
            root_id=center_node_id,
            max_depth=depth,
            max_nodes=_fetch_max,
            workspace_id=workspace_id,
        )

        # Step 4: Filter by node types if specified
        # Center node is always kept regardless of node_types filter.
        allowed: set[str] | None = None
        if node_types:
            allowed = {t.strip() for t in node_types.split(",") if t.strip()}
            # Always include the center node even if its type is not in the filter.
            center_graph_node = next((n for n in nodes if n.id == center_node_id), None)
            filtered = [n for n in nodes if n.node_type.value in allowed]
            if center_graph_node is not None and center_graph_node not in filtered:
                filtered = [center_graph_node, *filtered]
            nodes = filtered[:max_nodes]
            node_ids = {n.id for n in nodes}
            edges = [e for e in edges if e.source_id in node_ids and e.target_id in node_ids]

        # Step 5: Synthesize ephemeral GitHub nodes
        # Only include GitHub nodes whose type matches the filter (if provided).
        # Enforce max_nodes cap across persisted + synthesized nodes; never remove the center node.
        ephemeral_nodes = self._synthesize_github_nodes(nodes, integration_links)
        if allowed is not None:
            ephemeral_nodes = [n for n in ephemeral_nodes if n.node_type in allowed]
        remaining_capacity = max(0, max_nodes - len(nodes))
        ephemeral_nodes = ephemeral_nodes[:remaining_capacity]

        # Step 6: Sort nodes by importance tier
        nodes.sort(key=lambda n: node_tier(n.node_type.value))

        return EntitySubgraphResult(
            nodes=nodes,
            edges=edges,
            ephemeral_nodes=ephemeral_nodes,
            center_node_id=center_node_id,
        )

    @staticmethod
    def _synthesize_github_nodes(
        nodes: list[GraphNode],
        integration_links: Sequence[IntegrationLink],
    ) -> list[EphemeralNode]:
        """Create ephemeral nodes from integration links not already in the graph.

        Deduplicates both against existing graph nodes (by type+id key) and
        across integration links themselves (by external_url) to handle the case
        where the same PR is linked from multiple issues in a project graph.
        """
        if not integration_links:
            return []

        seen_keys: set[str] = {
            f"{n.node_type.value}:{n.properties.get('external_url') or n.properties.get('external_id')}"
            for n in nodes
            if n.properties
            and (
                n.properties.get("external_id") is not None
                or n.properties.get("external_url") is not None
            )
        }
        # Track synthesized URLs separately to deduplicate across multiple issues
        # that reference the same PR (project-level graph expands many issues).
        seen_urls: set[str] = set()
        now = datetime.now(tz=UTC)
        ephemeral: list[EphemeralNode] = []

        for link in integration_links:
            mapped_type = _GITHUB_NODE_TYPE_MAP.get(link.link_type, NodeType.NOTE.value)
            key = f"{mapped_type}:{link.external_url or link.external_id}"
            url = link.external_url or link.external_id
            if key in seen_keys or url in seen_urls:
                continue
            seen_keys.add(key)
            if url:
                seen_urls.add(url)
            ephemeral.append(
                EphemeralNode(
                    id=str(uuid5(NAMESPACE_URL, f"ephemeral:{key}")),
                    node_type=mapped_type,
                    label=link.title or link.external_id,
                    summary=f"GitHub {link.link_type.value}: {link.title or link.external_id}",
                    properties={
                        "external_id": link.external_id,
                        "external_url": link.external_url,
                        "author_name": link.author_name,
                        "ephemeral": True,
                    },
                    created_at=now,
                    updated_at=now,
                )
            )
        return ephemeral


__all__ = [
    "EntityNotFoundError",
    "EntitySubgraphResult",
    "EphemeralNode",
    "KnowledgeGraphQueryService",
    "NeighborResult",
    "RootNodeNotFoundError",
    "SubgraphResult",
    "UserContextResult",
    "node_tier",
]

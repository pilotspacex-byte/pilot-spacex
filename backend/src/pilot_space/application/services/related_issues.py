"""Related issues suggestion service -- semantic KG search + enrichment.

Phase 15: RELISS-01..04.

Extracts KG search with filtering, batch fetching + enrichment, and reason
inference from edge types from the related_issues router.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from pilot_space.domain.graph_edge import EdgeType
from pilot_space.domain.graph_node import NodeType
from pilot_space.infrastructure.database.repositories.issue_repository import (
    IssueRepository,
)
from pilot_space.infrastructure.database.repositories.issue_suggestion_dismissal_repository import (
    IssueSuggestionDismissalRepository,
)
from pilot_space.infrastructure.database.repositories.knowledge_graph_repository import (
    KnowledgeGraphRepository,
)
from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)


# -- Result dataclass ----------------------------------------------------------


@dataclass(frozen=True)
class RelatedIssueSuggestion:
    """A single related issue suggestion with enrichment."""

    id: UUID
    title: str
    identifier: str
    similarity_score: float
    reason: str


# -- Service -------------------------------------------------------------------


class RelatedIssuesSuggestionService:
    """Business logic for related issue suggestions.

    Owns KG search with filtering, batch issue fetching + enrichment,
    and reason inference from edge types (same project, shared note,
    semantic match).
    """

    def __init__(
        self,
        session: AsyncSession,
        issue_repository: IssueRepository,
        knowledge_graph_repository: KnowledgeGraphRepository,
        issue_suggestion_dismissal_repository: IssueSuggestionDismissalRepository,
    ) -> None:
        self._session = session
        self._issue_repo = issue_repository
        self._kg_repo = knowledge_graph_repository
        self._dismissal_repo = issue_suggestion_dismissal_repository

    async def suggest_related(
        self,
        workspace_id: UUID,
        issue_id: UUID,
        user_id: UUID,
        *,
        limit: int = 8,
    ) -> list[RelatedIssueSuggestion]:
        """Return semantically related issue suggestions for a given issue.

        Returns empty list when the issue has no KG node yet.
        Dismissed suggestions are excluded. Never returns the source issue itself.
        """
        kg_repo = self._kg_repo
        dismissal_repo = self._dismissal_repo

        # Find the issue's KG node
        node = await kg_repo._find_node_by_external(  # pyright: ignore[reportPrivateUsage]  # noqa: SLF001
            workspace_id, NodeType.ISSUE, issue_id
        )
        if node is None:
            return []

        # Hybrid search for related issues (overfetch for filtering)
        scored_nodes = await kg_repo.hybrid_search(
            query_embedding=node.embedding,
            query_text=node.content or "",
            workspace_id=workspace_id,
            node_types=[NodeType.ISSUE],
            limit=limit + 5,
        )

        # Get dismissed target IDs for this user/issue pair
        dismissed_ids = await dismissal_repo.get_dismissed_target_ids(user_id, issue_id)

        # Filter: exclude self and dismissed
        candidates = [
            sn
            for sn in scored_nodes
            if sn.node.external_id != issue_id and sn.node.external_id not in dismissed_ids
        ][:limit]

        if not candidates:
            return []

        # Batch-fetch issue records for enrichment
        candidate_issue_ids = [sn.node.external_id for sn in candidates if sn.node.external_id]
        issues_by_id = await self._issue_repo.get_active_by_ids(candidate_issue_ids)

        # Enrich reasons via KG edges
        candidate_node_ids = [sn.node.id for sn in candidates if sn.node.id]
        edges = await kg_repo.get_edges_between(
            candidate_node_ids + ([node.id] if node.id else []),
            workspace_id,
        )

        # Map node_id -> set of connected node_ids for RELATES_TO edge lookup
        shared_note_node_ids: set[UUID] = set()
        for edge in edges:
            if edge.edge_type == EdgeType.RELATES_TO:
                shared_note_node_ids.add(edge.source_id)
                shared_note_node_ids.add(edge.target_id)

        suggestions: list[RelatedIssueSuggestion] = []
        for scored_node in candidates:
            ext_id = scored_node.node.external_id
            if ext_id is None:
                continue
            issue_rec = issues_by_id.get(ext_id)
            if issue_rec is None:
                continue

            # Determine reason
            node_id = scored_node.node.id
            if node_id in shared_note_node_ids:
                reason = "shared note"
            else:
                reason = f"Semantic match ({round(scored_node.score * 100)}%)"

            suggestions.append(
                RelatedIssueSuggestion(
                    id=issue_rec.id,
                    title=issue_rec.name,
                    identifier=issue_rec.identifier,
                    similarity_score=scored_node.score,
                    reason=reason,
                )
            )

        return suggestions

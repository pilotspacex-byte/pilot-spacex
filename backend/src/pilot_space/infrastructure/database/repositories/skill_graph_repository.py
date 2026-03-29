"""Repository for SkillGraph entities.

Provides workspace-scoped CRUD operations for compiled skill graphs.
Primary query patterns:
- get_by_template: latest graph for a skill template

Source: Phase 50, P50-03
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import and_, select

from pilot_space.infrastructure.database.models.skill_graph import SkillGraph
from pilot_space.infrastructure.database.repositories.base import BaseRepository

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession


class SkillGraphRepository(BaseRepository[SkillGraph]):
    """Repository for SkillGraph entities.

    All write operations use flush() (no commit) -- callers own transaction
    boundaries via the session context.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, SkillGraph)

    async def create(  # type: ignore[override]
        self,
        *,
        workspace_id: UUID,
        skill_template_id: UUID,
        graph_json: dict[str, Any],
        node_count: int = 0,
        edge_count: int = 0,
    ) -> SkillGraph:
        """Create a new skill graph.

        Args:
            workspace_id: Owning workspace UUID.
            skill_template_id: Parent skill template UUID.
            graph_json: Full graph structure (nodes, edges, metadata).
            node_count: Number of nodes in the graph.
            edge_count: Number of edges in the graph.

        Returns:
            Newly created SkillGraph.
        """
        graph = SkillGraph(
            workspace_id=workspace_id,
            skill_template_id=skill_template_id,
            graph_json=graph_json,
            node_count=node_count,
            edge_count=edge_count,
        )
        self.session.add(graph)
        await self.session.flush()
        await self.session.refresh(graph)
        return graph

    async def get_by_template(
        self,
        skill_template_id: UUID,
    ) -> SkillGraph | None:
        """Get the latest graph for a skill template.

        Args:
            skill_template_id: The parent skill template UUID.

        Returns:
            The most recent SkillGraph, or None if no graph exists.
        """
        query = (
            select(SkillGraph)
            .where(
                and_(
                    SkillGraph.skill_template_id == skill_template_id,
                    SkillGraph.is_deleted == False,  # noqa: E712
                )
            )
            .order_by(SkillGraph.updated_at.desc())
            .limit(1)
        )
        result = await self.session.execute(query)
        return result.scalars().first()

    async def update(  # type: ignore[override]
        self,
        graph: SkillGraph,
    ) -> SkillGraph:
        """Update a skill graph.

        Args:
            graph: The graph to update (already modified in-memory).

        Returns:
            Updated SkillGraph.
        """
        await self.session.flush()
        await self.session.refresh(graph)
        return graph


__all__ = ["SkillGraphRepository"]

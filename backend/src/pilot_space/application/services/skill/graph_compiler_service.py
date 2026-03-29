"""GraphCompilerService: compile graph JSON to deterministic SKILL.md content.

Traverses graph nodes in topological order (Kahn's algorithm) and generates
a structured SKILL.md document. Optionally uses LLMGateway for AI-polished
output. Persists compiled content to skill_templates and updates
last_compiled_at on skill_graphs.

Phase 053: Graph-to-Skill Compiler
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import select, update

from pilot_space.ai.prompts.graph_compiler import (
    format_graph_for_llm,
    get_graph_compile_system_prompt,
)
from pilot_space.ai.providers.provider_selector import TaskType
from pilot_space.domain.exceptions import AppError, NotFoundError, ValidationError
from pilot_space.infrastructure.database.models.skill_graph import SkillGraph
from pilot_space.infrastructure.database.models.skill_template import SkillTemplate
from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from pilot_space.ai.proxy.llm_gateway import LLMGateway

logger = get_logger(__name__)


class GraphCompilerError(AppError):
    """Raised when graph compilation fails."""

    http_status = 422
    error_code = "graph_compile_error"

    def __init__(self, message: str = "Graph compilation failed") -> None:
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class GraphCompilePayload:
    """Input for graph compilation."""

    graph_id: UUID
    workspace_id: UUID
    user_id: UUID


@dataclass(frozen=True, slots=True)
class GraphCompileResult:
    """Output of graph compilation."""

    skill_content: str
    node_order: list[str]
    compiled_at: datetime
    skill_template_id: UUID = field(default_factory=lambda: UUID(int=0))


class GraphCompilerService:
    """Compiles graph JSON to deterministic SKILL.md content.

    Uses Kahn's algorithm for topological traversal, producing a structured
    markdown document with sections for each graph node. When an LLMGateway
    is available, the mechanical output is polished by AI into coherent,
    human-readable text.

    Args:
        session: Request-scoped async database session.
        llm_gateway: Optional LLM gateway for AI-polished compilation.
    """

    def __init__(
        self,
        session: AsyncSession,
        llm_gateway: LLMGateway | None = None,
    ) -> None:
        self._session = session
        self._llm_gateway = llm_gateway

    async def compile(self, payload: GraphCompilePayload) -> GraphCompileResult:
        """Compile a skill graph to SKILL.md content.

        When an LLMGateway is available, uses AI synthesis for polished output.
        Falls back to mechanical compilation when LLM is unavailable or fails.

        Loads the graph, performs topological sort, generates SKILL.md,
        and persists the result to skill_templates.skill_content.

        Args:
            payload: Compilation input with graph_id, workspace_id, user_id.

        Returns:
            GraphCompileResult with compiled content and metadata.

        Raises:
            NotFoundError: If graph or template not found.
            ValidationError: If graph has cycles or no nodes.
            GraphCompilerError: If compilation fails unexpectedly.
        """
        # Load graph
        stmt = select(SkillGraph).where(SkillGraph.id == payload.graph_id)
        result = await self._session.execute(stmt)
        graph = result.scalar_one_or_none()
        if graph is None:
            raise NotFoundError("Skill graph not found")

        graph_json = graph.graph_json
        nodes = graph_json.get("nodes", [])
        edges = graph_json.get("edges", [])

        # Topological sort
        sorted_nodes = self._topological_sort(nodes, edges)
        node_order = [n["id"] for n in sorted_nodes]

        # Generate SKILL.md — AI-polished when gateway available, mechanical otherwise
        mechanical_content = self._generate_skill_content(sorted_nodes, edges, graph_json)

        if self._llm_gateway is not None:
            skill_content = await self._synthesize_with_ai(
                sorted_nodes=sorted_nodes,
                edges=edges,
                mechanical_fallback=mechanical_content,
                template_name=getattr(graph, "skill_template_id", "Untitled"),
                workspace_id=payload.workspace_id,
                user_id=payload.user_id,
            )
        else:
            skill_content = mechanical_content

        # Persist compiled content to skill_template
        now = datetime.now(UTC)
        await self._session.execute(
            update(SkillTemplate)
            .where(SkillTemplate.id == graph.skill_template_id)
            .values(skill_content=skill_content)
        )

        # Update last_compiled_at on graph
        await self._session.execute(
            update(SkillGraph)
            .where(SkillGraph.id == payload.graph_id)
            .values(last_compiled_at=now)
        )
        await self._session.flush()

        logger.info(
            "[GraphCompiler] Compiled graph=%s nodes=%d ai=%s",
            payload.graph_id,
            len(sorted_nodes),
            self._llm_gateway is not None,
        )

        return GraphCompileResult(
            skill_content=skill_content,
            node_order=node_order,
            compiled_at=now,
            skill_template_id=graph.skill_template_id,
        )

    async def _synthesize_with_ai(
        self,
        *,
        sorted_nodes: list[dict[str, Any]],
        edges: list[dict[str, Any]],
        mechanical_fallback: str,
        template_name: str,
        workspace_id: UUID,
        user_id: UUID,
    ) -> str:
        """Use LLM to synthesize polished SKILL.md from graph data.

        Falls back to mechanical output if the LLM call fails.

        Args:
            sorted_nodes: Nodes in topological order.
            edges: Graph edges.
            mechanical_fallback: Pre-generated mechanical SKILL.md content.
            template_name: Skill template name for context.
            workspace_id: Workspace UUID for LLM routing.
            user_id: User UUID for cost tracking.

        Returns:
            AI-polished or mechanical SKILL.md content.
        """
        assert self._llm_gateway is not None  # noqa: S101

        system_prompt = get_graph_compile_system_prompt()
        user_message = format_graph_for_llm(sorted_nodes, edges, str(template_name))

        try:
            response = await self._llm_gateway.complete(
                workspace_id=workspace_id,
                user_id=user_id,
                task_type=TaskType.ROLE_SKILL_GENERATION,
                messages=[{"role": "user", "content": user_message}],
                system=system_prompt,
                max_tokens=2048,
                temperature=0.7,
                agent_name="graph_compiler",
            )
            ai_content = response.text.strip()
            if ai_content:
                logger.info(
                    "[GraphCompiler] AI synthesis succeeded, len=%d",
                    len(ai_content),
                )
                return ai_content
        except Exception:
            logger.warning(
                "[GraphCompiler] AI synthesis failed, using mechanical fallback",
                exc_info=True,
            )

        return mechanical_fallback

    @staticmethod
    def _topological_sort(
        nodes: list[dict[str, Any]],
        edges: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Sort nodes in topological order using Kahn's algorithm.

        Deterministic: at each step, selects the node with the smallest ID
        among candidates with in-degree 0.

        Args:
            nodes: List of graph node dicts.
            edges: List of graph edge dicts.

        Returns:
            Nodes in topological order.

        Raises:
            ValidationError: If graph has no nodes or contains cycles.
        """
        if not nodes:
            raise ValidationError("Graph contains no nodes")

        # Build node lookup
        node_map: dict[str, dict[str, Any]] = {n["id"]: n for n in nodes}
        node_ids = set(node_map.keys())

        # Build adjacency list and in-degree, excluding loop edges
        adj: dict[str, list[str]] = defaultdict(list)
        in_degree: dict[str, int] = dict.fromkeys(node_ids, 0)

        for edge in edges:
            edge_type = edge.get("type", "sequential")
            if edge_type == "loop":
                continue
            src = edge["source"]
            tgt = edge["target"]
            if src in node_ids and tgt in node_ids:
                adj[src].append(tgt)
                in_degree[tgt] += 1

        # Kahn's BFS — sorted by ID for determinism
        queue: deque[str] = deque(
            sorted(nid for nid, deg in in_degree.items() if deg == 0)
        )
        result: list[dict[str, Any]] = []

        while queue:
            # Pop smallest ID for deterministic order
            current = queue.popleft()
            result.append(node_map[current])

            # Sort neighbors for deterministic insertion
            for neighbor in sorted(adj[current]):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    # Insert in sorted position
                    _insert_sorted(queue, neighbor)

        if len(result) != len(nodes):
            raise ValidationError("Graph contains cycles — not a valid DAG")

        return result

    @staticmethod
    def _generate_skill_content(
        sorted_nodes: list[dict[str, Any]],
        _edges: list[dict[str, Any]],
        _graph_json: dict[str, Any],
    ) -> str:
        """Generate SKILL.md content from topologically sorted nodes.

        Produces a structured markdown document with frontmatter and
        a section for each node based on its type.

        Args:
            sorted_nodes: Nodes in topological order.
            edges: Graph edges (for context in condition branches).
            graph_json: Full graph JSON (for metadata).

        Returns:
            Complete SKILL.md string.
        """
        lines: list[str] = []

        # Frontmatter
        lines.append("---")
        lines.append("description: Compiled from graph workflow")
        lines.append(f"node_count: {len(sorted_nodes)}")
        lines.append("---")
        lines.append("")

        step_num = 0
        for node in sorted_nodes:
            data = node.get("data", {})
            node_type = data.get("nodeType", node.get("type", ""))
            label = data.get("label", "Untitled")
            config = data.get("config", {})

            if node_type == "input":
                lines.append(f"## Input: {label}")
                lines.append("")
                lines.append("Parameters:")
                if config:
                    for key, value in sorted(config.items()):
                        lines.append(f"- {key}: {value}")
                else:
                    lines.append("- (none)")
                lines.append("")

            elif node_type == "output":
                output_format = config.get("outputFormat", "text")
                lines.append(f"## Output: {label}")
                lines.append("")
                lines.append(f"Format: {output_format}")
                lines.append("")

            elif node_type == "prompt":
                step_num += 1
                prompt_text = config.get("promptText", "")
                lines.append(f"## Step {step_num}: {label}")
                lines.append("")
                if prompt_text:
                    lines.append(prompt_text)
                    lines.append("")

            elif node_type == "skill":
                step_num += 1
                skill_name = config.get("skillName", "unknown")
                lines.append(f"## Step {step_num}: Execute Skill — {label}")
                lines.append("")
                lines.append(f"Invoke skill: {skill_name}")
                lines.append("With input from previous step.")
                lines.append("")

            elif node_type == "condition":
                step_num += 1
                expression = config.get("conditionExpression", "")
                lines.append(f"## Step {step_num}: Condition — {label}")
                lines.append("")
                lines.append(f"If {expression}:")
                lines.append("  → Follow true branch")
                lines.append("Else:")
                lines.append("  → Follow false branch")
                lines.append("")

            elif node_type == "transform":
                step_num += 1
                template = config.get("transformTemplate", "")
                lines.append(f"## Step {step_num}: Transform — {label}")
                lines.append("")
                lines.append("Apply transformation:")
                lines.append(template)
                lines.append("")

            else:
                step_num += 1
                lines.append(f"## Step {step_num}: {label}")
                lines.append("")

        return "\n".join(lines)


def _insert_sorted(queue: deque[str], item: str) -> None:
    """Insert item into a sorted deque maintaining order."""
    # Convert to list, insert, convert back
    items = list(queue)
    items.append(item)
    items.sort()
    queue.clear()
    queue.extend(items)


__all__ = [
    "GraphCompilePayload",
    "GraphCompileResult",
    "GraphCompilerError",
    "GraphCompilerService",
]

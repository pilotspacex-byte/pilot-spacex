"""Structured output schemas for Claude Agent SDK.

Pydantic models defining JSON schemas for structured AI responses.
Used with SDK's `output_format` parameter to enforce response structure.

Reference: docs/architect/scalable-agent-architecture.md
Skills: extract-issues, decompose-tasks, find-duplicates
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ExtractedIssue(BaseModel):
    """Single extracted issue from note content."""

    title: str = Field(description="Issue title (concise, actionable)")
    description: str = Field(default="", description="Issue description")
    issue_type: str = Field(
        default="task",
        description="Issue type: bug, improvement, feature, task",
    )
    priority: str = Field(
        default="medium",
        description="Priority: urgent, high, medium, low, none",
    )
    source_block_id: str | None = Field(
        default=None,
        description="Block ID where issue was extracted from",
    )
    category: str = Field(
        default="explicit",
        description="Extraction category: explicit, implicit, related",
    )
    confidence: float | None = Field(
        default=None,
        description="Confidence score (0.0-1.0) for this extraction",
    )
    labels: list[str] = Field(
        default_factory=list,
        description="Suggested labels for the issue",
    )


class ExtractionResult(BaseModel):
    """Result of extract-issues skill invocation."""

    model_config = ConfigDict(populate_by_name=True)

    schema_type: str = Field(default="extraction_result", alias="schemaType")
    issues: list[ExtractedIssue] = Field(default_factory=list)
    summary: str = Field(default="", description="Brief extraction summary")
    total_count: int = Field(default=0, alias="totalCount")


class Subtask(BaseModel):
    """Single subtask from task decomposition."""

    model_config = ConfigDict(populate_by_name=True)

    title: str = Field(description="Subtask title")
    description: str = Field(default="", description="Subtask description")
    story_points: int = Field(
        default=1,
        description="Fibonacci story points estimate",
        alias="storyPoints",
    )
    depends_on: list[int] = Field(
        default_factory=list,
        description="Indices of subtasks this depends on (0-based)",
        alias="dependsOn",
    )
    estimated_days: float | None = Field(
        default=None,
        description="Estimated days to complete",
        alias="estimatedDays",
    )
    labels: list[str] = Field(
        default_factory=list,
        description="Labels for categorization (e.g., backend, frontend, testing)",
    )
    acceptance_criteria: list[str] = Field(
        default_factory=list,
        description="Acceptance criteria for the subtask",
        alias="acceptanceCriteria",
    )
    confidence: str = Field(
        default="DEFAULT",
        description="Confidence tag: RECOMMENDED, DEFAULT, ALTERNATIVE",
    )
    can_parallel_with: list[int] = Field(
        default_factory=list,
        description="Indices of subtasks that can run in parallel with this one",
        alias="canParallelWith",
    )


class DecompositionResult(BaseModel):
    """Result of decompose-tasks skill invocation."""

    model_config = ConfigDict(populate_by_name=True)

    schema_type: str = Field(default="decomposition_result", alias="schemaType")
    subtasks: list[Subtask] = Field(default_factory=list)
    total_points: int = Field(default=0, alias="totalPoints")
    summary: str = Field(default="", description="Brief decomposition summary")
    critical_path: list[int] = Field(
        default_factory=list,
        description="Ordered list of subtask indices on the critical path",
        alias="criticalPath",
    )
    parallel_opportunities: list[str] = Field(
        default_factory=list,
        description="Human-readable descriptions of parallelizable work",
        alias="parallelOpportunities",
    )

    @model_validator(mode="after")
    def validate_dag_no_cycles(self) -> DecompositionResult:
        """Validate that depends_on references form a valid DAG (no cycles).

        Uses Kahn's algorithm for topological sort. If not all nodes
        are visited, the graph contains a cycle.
        """
        if not self.subtasks:
            return self

        n = len(self.subtasks)

        # Build adjacency list and in-degree count
        in_degree = [0] * n
        adjacency: dict[int, list[int]] = {i: [] for i in range(n)}

        for idx, subtask in enumerate(self.subtasks):
            for dep in subtask.depends_on:
                if dep < 0 or dep >= n:
                    msg = (
                        f"Subtask '{subtask.title}' (index {idx}) "
                        f"depends on invalid index {dep} "
                        f"(valid range: 0-{n - 1})"
                    )
                    raise ValueError(msg)
                if dep == idx:
                    msg = f"Subtask '{subtask.title}' (index {idx}) depends on itself"
                    raise ValueError(msg)
                adjacency[dep].append(idx)
                in_degree[idx] += 1

        # Kahn's algorithm: BFS from nodes with in_degree == 0
        queue = [i for i in range(n) if in_degree[i] == 0]
        visited_count = 0

        while queue:
            node = queue.pop(0)
            visited_count += 1
            for neighbor in adjacency[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if visited_count != n:
            # Find nodes involved in cycle for error message
            cycle_nodes = [
                f"'{self.subtasks[i].title}' (index {i})" for i in range(n) if in_degree[i] > 0
            ]
            msg = f"Circular dependency detected among subtasks: {', '.join(cycle_nodes)}"
            raise ValueError(msg)

        return self


class DuplicateCandidate(BaseModel):
    """Candidate duplicate issue."""

    model_config = ConfigDict(populate_by_name=True)

    issue_id: str = Field(description="Issue identifier", alias="issueId")
    issue_key: str = Field(description="Issue key (e.g., PS-42)", alias="issueKey")
    title: str = Field(description="Issue title")
    similarity_score: float = Field(
        description="Similarity score (0.0-1.0)",
        alias="similarityScore",
    )
    reason: str = Field(default="", description="Why this is considered a duplicate")


class DuplicateSearchResult(BaseModel):
    """Result of find-duplicates skill invocation."""

    model_config = ConfigDict(populate_by_name=True)

    schema_type: str = Field(default="duplicate_search_result", alias="schemaType")
    candidates: list[DuplicateCandidate] = Field(default_factory=list)
    threshold: float = Field(default=0.7, description="Similarity threshold used")
    query_title: str = Field(default="", alias="queryTitle")


# Registry mapping schema_type to Pydantic model for validation
STRUCTURED_OUTPUT_SCHEMAS: dict[str, type[BaseModel]] = {
    "extraction_result": ExtractionResult,
    "decomposition_result": DecompositionResult,
    "duplicate_search_result": DuplicateSearchResult,
}

# Skill name → JSON schema for SDK output_format enforcement
SKILL_OUTPUT_FORMATS: dict[str, dict[str, Any]] = {
    "extract-issues": ExtractionResult.model_json_schema(),
    "decompose-tasks": DecompositionResult.model_json_schema(),
    "find-duplicates": DuplicateSearchResult.model_json_schema(),
}


def get_skill_output_format(skill_name: str) -> dict[str, Any] | None:
    """Get SDK output_format schema for a skill name.

    Args:
        skill_name: Skill identifier (e.g., 'extract-issues')

    Returns:
        JSON schema dict for SDK output_format, or None for free-text skills.
    """
    return SKILL_OUTPUT_FORMATS.get(skill_name)


def get_output_schema(schema_type: str) -> type[BaseModel] | None:
    """Get Pydantic model class for a schema type.

    Args:
        schema_type: Schema type identifier

    Returns:
        Pydantic model class or None if not found
    """
    return STRUCTURED_OUTPUT_SCHEMAS.get(schema_type)


def validate_structured_output(
    schema_type: str,
    data: dict[str, Any],
) -> BaseModel | None:
    """Validate structured output data against its schema.

    Args:
        schema_type: Schema type identifier
        data: Raw output data

    Returns:
        Validated Pydantic model or None if schema not found
    """
    schema_cls = get_output_schema(schema_type)
    if schema_cls is None:
        return None
    return schema_cls.model_validate(data)

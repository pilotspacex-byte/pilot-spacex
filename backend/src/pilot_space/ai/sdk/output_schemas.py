"""Structured output schemas for Claude Agent SDK.

Pydantic models defining JSON schemas for structured AI responses.
Used with SDK's `output_format` parameter to enforce response structure.

Reference: docs/architect/scalable-agent-architecture.md
Skills: extract-issues, decompose-tasks, find-duplicates
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


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


class ExtractionResult(BaseModel):
    """Result of extract-issues skill invocation."""

    schema_type: str = Field(default="extraction_result", alias="schemaType")
    issues: list[ExtractedIssue] = Field(default_factory=list)
    summary: str = Field(default="", description="Brief extraction summary")
    total_count: int = Field(default=0, alias="totalCount")


class Subtask(BaseModel):
    """Single subtask from task decomposition."""

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


class DecompositionResult(BaseModel):
    """Result of decompose-tasks skill invocation."""

    schema_type: str = Field(default="decomposition_result", alias="schemaType")
    subtasks: list[Subtask] = Field(default_factory=list)
    total_points: int = Field(default=0, alias="totalPoints")
    summary: str = Field(default="", description="Brief decomposition summary")


class DuplicateCandidate(BaseModel):
    """Candidate duplicate issue."""

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

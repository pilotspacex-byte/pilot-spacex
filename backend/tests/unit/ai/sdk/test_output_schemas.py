"""Unit tests for structured output schemas.

Tests Subtask/DecompositionResult models including:
- Optional field defaults and backward compatibility
- camelCase alias serialization
- DAG cycle detection via model_validator
- Out-of-range and self-reference dependency validation
"""

import pytest
from pydantic import ValidationError

from pilot_space.ai.sdk.output_schemas import (
    DecompositionResult,
    Subtask,
    get_skill_output_format,
    validate_structured_output,
)


class TestSubtaskDefaults:
    """Verify optional fields have correct defaults for backward compat."""

    def test_minimal_subtask(self) -> None:
        """Subtask with only required field (title) should validate."""
        subtask = Subtask(title="Do something")
        assert subtask.title == "Do something"
        assert subtask.description == ""
        assert subtask.story_points == 1
        assert subtask.depends_on == []
        assert subtask.estimated_days is None
        assert subtask.labels == []
        assert subtask.acceptance_criteria == []
        assert subtask.confidence == "DEFAULT"
        assert subtask.can_parallel_with == []

    def test_all_fields_populated(self) -> None:
        """Subtask with every field populated should validate."""
        subtask = Subtask(
            title="Implement auth",
            description="JWT-based authentication",
            story_points=3,
            depends_on=[0],
            estimated_days=2.5,
            labels=["backend", "security"],
            acceptance_criteria=["Tokens expire in 15min", "Refresh flow works"],
            confidence="RECOMMENDED",
            can_parallel_with=[2],
        )
        assert subtask.title == "Implement auth"
        assert subtask.story_points == 3
        assert subtask.estimated_days == 2.5
        assert subtask.labels == ["backend", "security"]
        assert subtask.acceptance_criteria == ["Tokens expire in 15min", "Refresh flow works"]
        assert subtask.confidence == "RECOMMENDED"
        assert subtask.can_parallel_with == [2]


class TestSubtaskAliasSerialization:
    """Verify camelCase aliases work for JSON input/output."""

    def test_dump_by_alias(self) -> None:
        """model_dump(by_alias=True) should use camelCase keys."""
        subtask = Subtask(
            title="Test",
            story_points=2,
            depends_on=[0],
            estimated_days=1.0,
            acceptance_criteria=["Works"],
            can_parallel_with=[1],
        )
        dumped = subtask.model_dump(by_alias=True)
        assert "storyPoints" in dumped
        assert "dependsOn" in dumped
        assert "estimatedDays" in dumped
        assert "acceptanceCriteria" in dumped
        assert "canParallelWith" in dumped
        # Python attribute names should NOT be in alias dump
        assert "story_points" not in dumped
        assert "depends_on" not in dumped

    def test_parse_from_camel_case(self) -> None:
        """model_validate should accept camelCase keys."""
        data = {
            "title": "Test",
            "storyPoints": 5,
            "dependsOn": [0, 1],
            "estimatedDays": 3.0,
            "acceptanceCriteria": ["Done"],
            "canParallelWith": [2],
        }
        subtask = Subtask.model_validate(data)
        assert subtask.story_points == 5
        assert subtask.depends_on == [0, 1]
        assert subtask.estimated_days == 3.0
        assert subtask.can_parallel_with == [2]


class TestDecompositionResultDAGValidation:
    """Verify DAG cycle detection in DecompositionResult."""

    def test_empty_subtasks(self) -> None:
        """Empty subtask list should validate without error."""
        result = DecompositionResult(subtasks=[], summary="Nothing to do")
        assert result.subtasks == []

    def test_valid_linear_chain(self) -> None:
        """Linear dependency chain A->B->C should validate."""
        result = DecompositionResult(
            subtasks=[
                Subtask(title="A"),
                Subtask(title="B", depends_on=[0]),
                Subtask(title="C", depends_on=[1]),
            ],
            summary="Linear chain",
        )
        assert len(result.subtasks) == 3

    def test_valid_diamond_dag(self) -> None:
        """Diamond DAG (A->B, A->C, B->D, C->D) should validate."""
        result = DecompositionResult(
            subtasks=[
                Subtask(title="A"),
                Subtask(title="B", depends_on=[0]),
                Subtask(title="C", depends_on=[0]),
                Subtask(title="D", depends_on=[1, 2]),
            ],
            summary="Diamond",
        )
        assert len(result.subtasks) == 4

    def test_valid_parallel_tasks(self) -> None:
        """Independent tasks with no dependencies should validate."""
        result = DecompositionResult(
            subtasks=[
                Subtask(title="A"),
                Subtask(title="B"),
                Subtask(title="C"),
            ],
            summary="All parallel",
        )
        assert len(result.subtasks) == 3

    def test_cycle_two_nodes(self) -> None:
        """Mutual dependency A<->B should raise ValueError."""
        with pytest.raises(ValidationError, match="Circular dependency"):
            DecompositionResult(
                subtasks=[
                    Subtask(title="A", depends_on=[1]),
                    Subtask(title="B", depends_on=[0]),
                ],
            )

    def test_cycle_three_nodes(self) -> None:
        """Cycle A->B->C->A should raise ValueError."""
        with pytest.raises(ValidationError, match="Circular dependency"):
            DecompositionResult(
                subtasks=[
                    Subtask(title="A", depends_on=[2]),
                    Subtask(title="B", depends_on=[0]),
                    Subtask(title="C", depends_on=[1]),
                ],
            )

    def test_self_reference(self) -> None:
        """Task depending on itself should raise ValueError."""
        with pytest.raises(ValidationError, match="depends on itself"):
            DecompositionResult(
                subtasks=[
                    Subtask(title="A", depends_on=[0]),
                ],
            )

    def test_out_of_range_dependency(self) -> None:
        """depends_on index >= len(subtasks) should raise ValueError."""
        with pytest.raises(ValidationError, match="invalid index"):
            DecompositionResult(
                subtasks=[
                    Subtask(title="A", depends_on=[5]),
                ],
            )

    def test_negative_dependency_index(self) -> None:
        """Negative depends_on index should raise ValueError."""
        with pytest.raises(ValidationError, match="invalid index"):
            DecompositionResult(
                subtasks=[
                    Subtask(title="A", depends_on=[-1]),
                ],
            )


class TestDecompositionResultFields:
    """Verify DecompositionResult-level fields."""

    def test_critical_path_default(self) -> None:
        """critical_path defaults to empty list."""
        result = DecompositionResult(subtasks=[])
        assert result.critical_path == []

    def test_parallel_opportunities_default(self) -> None:
        """parallel_opportunities defaults to empty list."""
        result = DecompositionResult(subtasks=[])
        assert result.parallel_opportunities == []

    def test_full_result_with_metadata(self) -> None:
        """DecompositionResult with all fields populated."""
        result = DecompositionResult(
            subtasks=[
                Subtask(title="A"),
                Subtask(title="B", depends_on=[0]),
            ],
            total_points=5,
            summary="Two tasks",
            critical_path=[0, 1],
            parallel_opportunities=["No parallel opportunities"],
        )
        assert result.total_points == 5
        assert result.critical_path == [0, 1]
        assert result.parallel_opportunities == ["No parallel opportunities"]

    def test_alias_serialization(self) -> None:
        """DecompositionResult aliases serialize correctly."""
        result = DecompositionResult(
            subtasks=[Subtask(title="A")],
            total_points=3,
            critical_path=[0],
            parallel_opportunities=["None"],
        )
        dumped = result.model_dump(by_alias=True)
        assert "schemaType" in dumped
        assert "totalPoints" in dumped
        assert "criticalPath" in dumped
        assert "parallelOpportunities" in dumped


class TestSkillOutputFormat:
    """Verify JSON schema generation includes new fields."""

    def test_decompose_tasks_schema_has_new_fields(self) -> None:
        """decompose-tasks JSON schema should include all Subtask fields."""
        schema = get_skill_output_format("decompose-tasks")
        assert schema is not None

        # Navigate to Subtask properties in JSON schema
        subtask_ref = schema.get("$defs", {}).get("Subtask", {})
        props = subtask_ref.get("properties", {})

        assert "estimatedDays" in props
        assert "labels" in props
        assert "acceptanceCriteria" in props
        assert "confidence" in props
        assert "canParallelWith" in props

        # DecompositionResult-level fields
        top_props = schema.get("properties", {})
        assert "criticalPath" in top_props
        assert "parallelOpportunities" in top_props

    def test_validate_structured_output_decomposition(self) -> None:
        """validate_structured_output should accept valid decomposition data."""
        data = {
            "schemaType": "decomposition_result",
            "subtasks": [
                {"title": "Task A"},
                {"title": "Task B", "dependsOn": [0], "estimatedDays": 1.5},
            ],
            "totalPoints": 4,
            "summary": "Test decomposition",
        }
        result = validate_structured_output("decomposition_result", data)
        assert result is not None
        assert isinstance(result, DecompositionResult)
        assert len(result.subtasks) == 2
        assert result.subtasks[1].estimated_days == 1.5

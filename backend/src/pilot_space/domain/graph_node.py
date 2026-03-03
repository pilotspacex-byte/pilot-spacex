"""GraphNode domain entity for the knowledge graph system.

Represents a vertex in the workspace knowledge graph. Nodes model
workspace entities (issues, notes, users, decisions, etc.) with
vector embeddings for semantic search and typed metadata via properties.

Feature 016: Knowledge Graph — Memory Engine replacement
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4


class NodeType(StrEnum):
    """Type discriminator for graph nodes."""

    ISSUE = "issue"
    NOTE = "note"
    PROJECT = "project"
    CYCLE = "cycle"
    USER = "user"
    PULL_REQUEST = "pull_request"
    CODE_REFERENCE = "code_reference"
    DECISION = "decision"
    SKILL_OUTCOME = "skill_outcome"
    CONVERSATION_SUMMARY = "conversation_summary"
    LEARNED_PATTERN = "learned_pattern"
    CONSTITUTION_RULE = "constitution_rule"
    WORK_INTENT = "work_intent"
    USER_PREFERENCE = "user_preference"


_SUMMARY_LENGTH = 120


@dataclass
class GraphNode:
    """Base domain entity for a knowledge graph vertex.

    Each node represents one addressable entity in the workspace
    knowledge graph. Embeddings are filled asynchronously by a background
    worker after the node is persisted.

    Attributes:
        id: Unique identifier for this node.
        workspace_id: Owning workspace (multi-tenant isolation).
        node_type: Discriminator value (see NodeType).
        label: Human-readable display name (e.g. "PS-42", note title).
        content: Searchable text content; used for FTS and embedding.
        properties: Type-specific JSONB metadata (state, priority, etc.).
        embedding: 1536-dim OpenAI embedding vector (async filled).
        user_id: For user-scoped nodes (UserPreference, LearnedPattern).
        external_id: FK reference to the originating entity.
        created_at: UTC creation timestamp.
        updated_at: UTC last-modified timestamp.
    """

    workspace_id: UUID
    node_type: NodeType
    label: str
    content: str
    id: UUID = field(default_factory=uuid4)
    properties: dict[str, object] = field(default_factory=dict)
    embedding: list[float] | None = None
    user_id: UUID | None = None
    external_id: UUID | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))

    @property
    def summary(self) -> str:
        """Return the first 120 characters of content as a summary."""
        return self.content[:_SUMMARY_LENGTH]

    @classmethod
    def create(
        cls,
        *,
        workspace_id: UUID,
        node_type: NodeType,
        label: str,
        content: str,
        properties: dict[str, object] | None = None,
        user_id: UUID | None = None,
        external_id: UUID | None = None,
    ) -> GraphNode:
        """Factory method for constructing a new unsaved GraphNode.

        Args:
            workspace_id: Owning workspace UUID.
            node_type: Node discriminator type.
            label: Display name for the node.
            content: Searchable text content.
            properties: Optional type-specific metadata dict.
            user_id: Optional user scope for personal nodes.
            external_id: Optional FK to originating entity.

        Returns:
            A new GraphNode instance with defaults applied.
        """
        return cls(
            workspace_id=workspace_id,
            node_type=node_type,
            label=label,
            content=content,
            properties=properties or {},
            user_id=user_id,
            external_id=external_id,
        )


# ---------------------------------------------------------------------------
# Typed node subtypes
#
# Each subtype adds a specialized `build()` classmethod that enforces the
# correct properties shape for that NodeType. Named `build()` (not `create()`)
# to avoid an incompatible LSP override of GraphNode.create().
# ---------------------------------------------------------------------------


@dataclass
class IssueNode(GraphNode):
    """Graph node representing a workspace issue (e.g. PS-42).

    properties keys:
        state: Issue state name (str).
        priority: Issue priority label (str).
        identifier: Human-readable identifier (e.g. "PS-42").
        project_id: UUID of the owning project as str.
    """

    @classmethod
    def build(
        cls,
        *,
        workspace_id: UUID,
        label: str,
        content: str,
        state: str,
        priority: str,
        identifier: str,
        project_id: UUID,
        external_id: UUID | None = None,
        user_id: UUID | None = None,
    ) -> IssueNode:
        """Construct a typed IssueNode with required issue properties."""
        return cls(
            workspace_id=workspace_id,
            node_type=NodeType.ISSUE,
            label=label,
            content=content,
            properties={
                "state": state,
                "priority": priority,
                "identifier": identifier,
                "project_id": str(project_id),
            },
            external_id=external_id,
            user_id=user_id,
        )


@dataclass
class NoteNode(GraphNode):
    """Graph node representing a workspace note.

    properties keys:
        title: Note title (str).
    """

    @classmethod
    def build(
        cls,
        *,
        workspace_id: UUID,
        label: str,
        content: str,
        title: str,
        external_id: UUID | None = None,
        user_id: UUID | None = None,
    ) -> NoteNode:
        """Construct a typed NoteNode with required note properties."""
        return cls(
            workspace_id=workspace_id,
            node_type=NodeType.NOTE,
            label=label,
            content=content,
            properties={"title": title},
            external_id=external_id,
            user_id=user_id,
        )


@dataclass
class DecisionNode(GraphNode):
    """Graph node representing an architectural or product decision.

    properties keys:
        rationale: Decision rationale text (str).
        decided_at: ISO-8601 timestamp of the decision (str).
    """

    @classmethod
    def build(
        cls,
        *,
        workspace_id: UUID,
        label: str,
        content: str,
        rationale: str,
        decided_at: datetime,
        external_id: UUID | None = None,
        user_id: UUID | None = None,
    ) -> DecisionNode:
        """Construct a typed DecisionNode with required decision properties."""
        return cls(
            workspace_id=workspace_id,
            node_type=NodeType.DECISION,
            label=label,
            content=content,
            properties={
                "rationale": rationale,
                "decided_at": decided_at.isoformat(),
            },
            external_id=external_id,
            user_id=user_id,
        )


@dataclass
class LearnedPatternNode(GraphNode):
    """Graph node representing a pattern the AI has observed.

    properties keys:
        occurrence_count: Number of times this pattern was observed (int).
        confidence: Confidence score 0.0-1.0 (float).
    """

    @classmethod
    def build(
        cls,
        *,
        workspace_id: UUID,
        label: str,
        content: str,
        occurrence_count: int,
        confidence: float,
        user_id: UUID | None = None,
        external_id: UUID | None = None,
    ) -> LearnedPatternNode:
        """Construct a typed LearnedPatternNode with required pattern properties."""
        return cls(
            workspace_id=workspace_id,
            node_type=NodeType.LEARNED_PATTERN,
            label=label,
            content=content,
            properties={
                "occurrence_count": occurrence_count,
                "confidence": confidence,
            },
            user_id=user_id,
            external_id=external_id,
        )


@dataclass
class UserPreferenceNode(GraphNode):
    """Graph node representing a user-scoped preference.

    properties keys:
        preference_key: Dotted preference key (str).
        preference_value: Serialized preference value (str or object).
    """

    @classmethod
    def build(
        cls,
        *,
        workspace_id: UUID,
        label: str,
        content: str,
        user_id: UUID,
        preference_key: str,
        preference_value: object,
        external_id: UUID | None = None,
    ) -> UserPreferenceNode:
        """Construct a typed UserPreferenceNode with required preference properties."""
        return cls(
            workspace_id=workspace_id,
            node_type=NodeType.USER_PREFERENCE,
            label=label,
            content=content,
            properties={
                "preference_key": preference_key,
                "preference_value": preference_value,
            },
            user_id=user_id,
            external_id=external_id,
        )


@dataclass
class SkillOutcomeNode(GraphNode):
    """Graph node recording the outcome of an AI skill execution.

    properties keys:
        skill_name: Name of the skill that produced the outcome (str).
        outcome_summary: Short summary of what was accomplished (str).
    """

    @classmethod
    def build(
        cls,
        *,
        workspace_id: UUID,
        label: str,
        content: str,
        skill_name: str,
        outcome_summary: str,
        user_id: UUID | None = None,
        external_id: UUID | None = None,
    ) -> SkillOutcomeNode:
        """Construct a typed SkillOutcomeNode with required skill properties."""
        return cls(
            workspace_id=workspace_id,
            node_type=NodeType.SKILL_OUTCOME,
            label=label,
            content=content,
            properties={
                "skill_name": skill_name,
                "outcome_summary": outcome_summary,
            },
            user_id=user_id,
            external_id=external_id,
        )


@dataclass
class ConversationSummaryNode(GraphNode):
    """Graph node storing a condensed summary of a conversation session.

    properties keys:
        session_id: Conversation session identifier (str).
        message_count: Number of messages in the summarized session (int).
    """

    @classmethod
    def build(
        cls,
        *,
        workspace_id: UUID,
        label: str,
        content: str,
        session_id: str,
        message_count: int,
        user_id: UUID | None = None,
        external_id: UUID | None = None,
    ) -> ConversationSummaryNode:
        """Construct a typed ConversationSummaryNode with required session properties."""
        return cls(
            workspace_id=workspace_id,
            node_type=NodeType.CONVERSATION_SUMMARY,
            label=label,
            content=content,
            properties={
                "session_id": session_id,
                "message_count": message_count,
            },
            user_id=user_id,
            external_id=external_id,
        )


__all__ = [
    "ConversationSummaryNode",
    "DecisionNode",
    "GraphNode",
    "IssueNode",
    "LearnedPatternNode",
    "NodeType",
    "NoteNode",
    "SkillOutcomeNode",
    "UserPreferenceNode",
]

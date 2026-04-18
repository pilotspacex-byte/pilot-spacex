"""GraphNode domain entity for the knowledge graph system.

Represents a vertex in the workspace knowledge graph. Nodes model
workspace entities (issues, notes, users, decisions, etc.) with
vector embeddings for semantic search and typed metadata via properties.

Feature 016: Knowledge Graph — Memory Engine replacement
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4


class NodeType(StrEnum):
    """Type discriminator for graph nodes."""

    ISSUE = "issue"
    NOTE = "note"
    NOTE_CHUNK = "note_chunk"
    PROJECT = "project"
    CYCLE = "cycle"
    USER = "user"
    PULL_REQUEST = "pull_request"
    BRANCH = "branch"
    COMMIT = "commit"
    CODE_REFERENCE = "code_reference"
    DECISION = "decision"
    SKILL_OUTCOME = "skill_outcome"
    CONVERSATION_SUMMARY = "conversation_summary"
    LEARNED_PATTERN = "learned_pattern"
    CONSTITUTION_RULE = "constitution_rule"
    WORK_INTENT = "work_intent"
    USER_PREFERENCE = "user_preference"
    DOCUMENT = "document"
    DOCUMENT_CHUNK = "document_chunk"
    # Phase 69 — memory substrate (Decision Point 1)
    AGENT_TURN = "agent_turn"
    USER_CORRECTION = "user_correction"
    PR_REVIEW_FINDING = "pr_review_finding"


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
        embedding: 768-dim embedding vector (async filled by background worker).
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
    content_hash: str | None = None
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
        content_hash: str | None = None,
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
            content_hash: Optional SHA-256 digest for unkeyed node dedup.

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
            content_hash=content_hash,
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
        external_id: UUID | None = None,
        user_id: UUID | None = None,
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
            external_id=external_id,
            user_id=user_id,
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
        external_id: UUID | None = None,
        user_id: UUID | None = None,
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
            external_id=external_id,
            user_id=user_id,
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
        external_id: UUID | None = None,
        user_id: UUID | None = None,
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
            external_id=external_id,
            user_id=user_id,
        )


@dataclass
class DocumentNode(GraphNode):
    """Graph node representing an uploaded document in the workspace.

    properties keys:
        filename: Original filename (str).
        mime_type: MIME type, e.g. ``application/pdf`` (str).
        size_bytes: File size in bytes (int).
        extraction_source: How text was extracted: "ocr" | "office" | "raw" (str).
        page_count: Number of pages; None if unknown (int | None).
        language: Detected language code e.g. "en"; None if unknown (str | None).
        project_id: UUID of the owning project as str.
    """

    @classmethod
    def build(
        cls,
        *,
        workspace_id: UUID,
        label: str,
        content: str,
        filename: str,
        mime_type: str,
        size_bytes: int,
        extraction_source: str,
        project_id: UUID,
        page_count: int | None = None,
        language: str | None = None,
        external_id: UUID | None = None,
        user_id: UUID | None = None,
    ) -> DocumentNode:
        """Construct a typed DocumentNode with required document properties."""
        return cls(
            workspace_id=workspace_id,
            node_type=NodeType.DOCUMENT,
            label=label,
            content=content,
            properties={
                "filename": filename,
                "mime_type": mime_type,
                "size_bytes": size_bytes,
                "extraction_source": extraction_source,
                "project_id": str(project_id),
                **({"page_count": page_count} if page_count is not None else {}),
                **({"language": language} if language is not None else {}),
            },
            external_id=external_id,
            user_id=user_id,
        )


@dataclass
class DocumentChunkNode(GraphNode):
    """Graph node representing a heading-delimited chunk of a document.

    properties keys:
        chunk_index: 0-based position of this chunk in the document (int).
        heading: Heading text for this chunk section (str).
        heading_level: Markdown heading level 1-6; 0 if no heading (int).
        parent_document_id: attachment_id of the parent DOCUMENT node as str.
        project_id: UUID of the owning project as str.
    """

    @classmethod
    def build(
        cls,
        *,
        workspace_id: UUID,
        label: str,
        content: str,
        chunk_index: int,
        heading: str,
        parent_document_id: UUID,
        project_id: UUID,
        heading_level: int = 0,
    ) -> DocumentChunkNode:
        """Construct a typed DocumentChunkNode with required chunk properties."""
        return cls(
            workspace_id=workspace_id,
            node_type=NodeType.DOCUMENT_CHUNK,
            label=label,
            content=content,
            properties={
                "chunk_index": chunk_index,
                "heading": heading,
                "heading_level": heading_level,
                "parent_document_id": str(parent_document_id),
                "project_id": str(project_id),
            },
        )


def compute_content_hash(
    workspace_id: UUID,
    node_type: str,
    content: str,
    user_id: UUID | None = None,
) -> str:
    """SHA-256 of normalized (workspace_id:node_type[:user_id]:stripped_lowered_content).

    Used for deduplication of unkeyed nodes (no external_id) such as
    DECISION, LEARNED_PATTERN, USER_PREFERENCE — which have no stable FK.

    user_id is included in the hash for user-scoped node types (USER_PREFERENCE,
    LEARNED_PATTERN) so two users writing the same content produce distinct nodes
    rather than silently merging.

    Args:
        workspace_id: Owning workspace UUID.
        node_type: NodeType string (e.g. "decision").
        content: Node content text.
        user_id: Optional user UUID; included in hash when set.

    Returns:
        64-char hex SHA-256 digest.
    """
    normalized = re.sub(r"\s+", " ", content.strip().lower())
    user_segment = f":{user_id}" if user_id is not None else ""
    raw = f"{workspace_id}:{node_type}{user_segment}:{normalized}"
    return hashlib.sha256(raw.encode()).hexdigest()


__all__ = [
    "ConversationSummaryNode",
    "DecisionNode",
    "DocumentChunkNode",
    "DocumentNode",
    "GraphNode",
    "IssueNode",
    "LearnedPatternNode",
    "NodeType",
    "NoteNode",
    "SkillOutcomeNode",
    "UserPreferenceNode",
    "compute_content_hash",
]

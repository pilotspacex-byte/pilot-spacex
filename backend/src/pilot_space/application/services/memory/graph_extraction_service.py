"""GraphExtractionService — extract structured graph data from AI conversations.

Analyzes conversation messages using a lightweight Claude Haiku LLM call to
identify decisions, patterns, user preferences, and entity references.
Returns NodeInput + EdgeInput objects ready for GraphWriteService.

BYOK: if no api_key is provided, returns empty ExtractionResult without
making any API call.

Feature 016: Knowledge Graph — Memory Engine replacement
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from pilot_space.application.services.memory.graph_write_service import EdgeInput, NodeInput
from pilot_space.domain.graph_node import NodeType
from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)

_EXTRACTION_MODEL = "claude-haiku-4-5-20251001"
_MAX_TOKENS = 1024

EXTRACTION_PROMPT_TEMPLATE = """\
Analyze this AI conversation and extract structured knowledge.

Conversation:
{conversation_text}

Return a JSON object with exactly this structure:
{{
  "decisions": [{{"text": "...", "context": "..."}}],
  "patterns": [{{"text": "...", "confidence": 0.8}}],
  "user_preferences": [{{"key": "...", "value": "..."}}],
  "entity_references": [{{"entity_type": "issue|note|code_ref", "identifier": "..."}}]
}}

Focus on explicit decisions and clear patterns. Skip generic statements."""


# ---------------------------------------------------------------------------
# Input / output data structures
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ConversationExtractionPayload:
    """Input for a graph extraction from AI conversation messages.

    Attributes:
        messages: List of conversation messages [{role, content}].
        workspace_id: Owning workspace for all extracted nodes.
        user_id: Optional user whose conversation produced the messages.
        issue_id: Optional issue context UUID for this conversation.
        api_key: Anthropic API key. None → skip extraction (BYOK pattern).
    """

    messages: list[dict[str, str]]
    workspace_id: UUID
    user_id: UUID | None = None
    issue_id: UUID | None = None
    api_key: str | None = None


@dataclass
class ExtractionResult:
    """Result from a graph extraction operation.

    Attributes:
        nodes: NodeInput objects ready to pass to GraphWriteService.
        edges: EdgeInput objects ready to pass to GraphWriteService.
        decisions: Human-readable decision strings.
        patterns: Human-readable pattern strings.
        raw_response: Raw LLM response text (for debugging/logging).
    """

    nodes: list[NodeInput]
    edges: list[EdgeInput]
    decisions: list[str]
    patterns: list[str]
    raw_response: str | None


def _empty_result() -> ExtractionResult:
    """Return an empty ExtractionResult."""
    return ExtractionResult(
        nodes=[],
        edges=[],
        decisions=[],
        patterns=[],
        raw_response=None,
    )


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------


def _build_conversation_text(messages: list[dict[str, str]]) -> str:
    """Serialize messages to a readable conversation text block.

    Args:
        messages: List of {role, content} dicts.

    Returns:
        Multi-line string with Role: Content format.
    """
    lines: list[str] = []
    for msg in messages:
        role = msg.get("role", "unknown").capitalize()
        content = msg.get("content", "").strip()
        if content:
            lines.append(f"{role}: {content}")
    return "\n".join(lines)


def _build_prompt(messages: list[dict[str, str]]) -> str:
    """Build the extraction prompt from conversation messages.

    Args:
        messages: Conversation message list.

    Returns:
        Full prompt string for the LLM.
    """
    conversation_text = _build_conversation_text(messages)
    return EXTRACTION_PROMPT_TEMPLATE.format(conversation_text=conversation_text)


# ---------------------------------------------------------------------------
# LLM response parsing
# ---------------------------------------------------------------------------


def _parse_llm_response(raw: str) -> dict[str, Any]:
    """Parse raw LLM response into a structured dict.

    Strips markdown code fences if present, then JSON-parses the result.
    Returns an empty dict on any parse failure.

    Args:
        raw: Raw LLM response text.

    Returns:
        Parsed dict or {} on failure.
    """
    text = raw.strip()
    # Strip ```json ... ``` or ``` ... ``` fences
    if text.startswith("```"):
        lines = text.splitlines()
        # Remove first and last fence lines
        inner = lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
        text = "\n".join(inner)
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
        logger.warning("GraphExtractionService: LLM returned non-dict JSON — ignoring")
        return {}
    except json.JSONDecodeError:
        logger.warning(
            "GraphExtractionService: failed to parse LLM response as JSON",
            exc_info=True,
        )
        return {}


# ---------------------------------------------------------------------------
# Node construction helpers
# ---------------------------------------------------------------------------


def _build_decision_nodes(
    decisions: list[dict[str, Any]],
) -> list[NodeInput]:
    """Convert raw decision dicts to DecisionNode NodeInputs.

    Args:
        decisions: List of {"text": str, "context": str} dicts from LLM.

    Returns:
        List of NodeInput with NodeType.DECISION.
    """
    nodes: list[NodeInput] = []
    now_iso = datetime.now(tz=UTC).isoformat()
    for item in decisions:
        text = str(item.get("text", "")).strip()
        context = str(item.get("context", "")).strip()
        if not text:
            continue
        nodes.append(
            NodeInput(
                node_type=NodeType.DECISION,
                label=text[:120],
                content=text,
                properties={
                    "rationale": context,
                    "decided_at": now_iso,
                },
            )
        )
    return nodes


def _build_pattern_nodes(
    patterns: list[dict[str, Any]],
) -> list[NodeInput]:
    """Convert raw pattern dicts to LearnedPatternNode NodeInputs.

    Args:
        patterns: List of {"text": str, "confidence": float} dicts from LLM.

    Returns:
        List of NodeInput with NodeType.LEARNED_PATTERN.
    """
    nodes: list[NodeInput] = []
    for item in patterns:
        text = str(item.get("text", "")).strip()
        confidence = float(item.get("confidence", 0.5))
        # Clamp to valid range
        confidence = max(0.0, min(1.0, confidence))
        if not text:
            continue
        nodes.append(
            NodeInput(
                node_type=NodeType.LEARNED_PATTERN,
                label=text[:120],
                content=text,
                properties={
                    "occurrence_count": 1,
                    "confidence": confidence,
                },
            )
        )
    return nodes


def _build_preference_nodes(
    preferences: list[dict[str, Any]],
    user_id: UUID | None,
) -> list[NodeInput]:
    """Convert raw preference dicts to UserPreferenceNode NodeInputs.

    Skips any preference if user_id is None (user scope required).

    Args:
        preferences: List of {"key": str, "value": str} dicts from LLM.
        user_id: Optional user UUID; nodes are skipped if None.

    Returns:
        List of NodeInput with NodeType.USER_PREFERENCE.
    """
    if user_id is None:
        return []
    nodes: list[NodeInput] = []
    for item in preferences:
        key = str(item.get("key", "")).strip()
        value = item.get("value", "")
        if not key:
            continue
        label = f"{key}: {value}"
        nodes.append(
            NodeInput(
                node_type=NodeType.USER_PREFERENCE,
                label=label[:120],
                content=label,
                properties={
                    "preference_key": key,
                    "preference_value": value,
                },
                user_id=user_id,
            )
        )
    return nodes


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class GraphExtractionService:
    """Extract structured knowledge graph data from AI conversation messages.

    Makes a single lightweight LLM call to identify decisions, patterns,
    user preferences, and entity references in the conversation. Returns
    NodeInput objects suitable for passing to GraphWriteService.

    Returns an empty ExtractionResult when api_key is None (BYOK pattern)
    or when the LLM response cannot be parsed — never raises.

    Example:
        service = GraphExtractionService()
        result = await service.execute(ConversationExtractionPayload(
            messages=[{"role": "user", "content": "We decided to use Redis..."}],
            workspace_id=workspace_id,
            api_key=api_key,
        ))
    """

    def __init__(self) -> None:
        """Initialize service."""

    async def execute(self, payload: ConversationExtractionPayload) -> ExtractionResult:
        """Extract graph nodes from conversation messages.

        Args:
            payload: Conversation messages plus context and API key.

        Returns:
            ExtractionResult with NodeInput/EdgeInput lists.
            Returns empty result when api_key is None or on any error.
        """
        if not payload.api_key:
            logger.debug("GraphExtractionService: no api_key provided — returning empty result")
            return _empty_result()

        if not payload.messages:
            logger.debug("GraphExtractionService: empty messages list — returning empty result")
            return _empty_result()

        raw_response = await self._call_llm(payload.api_key, payload.messages)
        if raw_response is None:
            return _empty_result()

        parsed = _parse_llm_response(raw_response)
        if not parsed:
            return _empty_result()

        return self._build_result(parsed, payload, raw_response)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _call_llm(self, api_key: str, messages: list[dict[str, str]]) -> str | None:
        """Call Anthropic Claude Haiku for extraction.

        Args:
            api_key: Anthropic API key.
            messages: Conversation messages.

        Returns:
            Raw LLM response text, or None on failure.
        """
        try:
            import anthropic  # type: ignore[import-untyped]

            prompt = _build_prompt(messages)
            client = anthropic.AsyncAnthropic(api_key=api_key)
            message = await client.messages.create(
                model=_EXTRACTION_MODEL,
                max_tokens=_MAX_TOKENS,
                messages=[{"role": "user", "content": prompt}],
            )
            # Extract text from the first content block (safe for all block union types)
            if message.content:
                first_block = message.content[0]
                text_val = getattr(first_block, "text", None)
                if text_val is not None:
                    return str(text_val)
            return None
        except Exception:
            logger.warning(
                "GraphExtractionService: LLM call failed",
                exc_info=True,
            )
            return None

    def _build_result(
        self,
        parsed: dict[str, Any],
        payload: ConversationExtractionPayload,
        raw_response: str,
    ) -> ExtractionResult:
        """Convert parsed LLM dict into ExtractionResult.

        Args:
            parsed: JSON dict from the LLM response.
            payload: Original extraction payload for context.
            raw_response: Raw response text for inclusion in result.

        Returns:
            Populated ExtractionResult.
        """
        raw_decisions: list[dict[str, Any]] = parsed.get("decisions", []) or []
        raw_patterns: list[dict[str, Any]] = parsed.get("patterns", []) or []
        raw_preferences: list[dict[str, Any]] = parsed.get("user_preferences", []) or []

        decision_nodes = _build_decision_nodes(raw_decisions)
        pattern_nodes = _build_pattern_nodes(raw_patterns)
        preference_nodes = _build_preference_nodes(raw_preferences, payload.user_id)

        all_nodes = decision_nodes + pattern_nodes + preference_nodes

        # Edges linking extracted nodes to the issue context are deferred to
        # GraphWriteService after nodes are persisted and their UUIDs are known.
        # Building edges here with target_external_id=None is unresolvable.
        edges: list[EdgeInput] = []

        # Derive human-readable text lists directly from the already-filtered nodes
        decisions_text = [n.content for n in decision_nodes]
        patterns_text = [n.content for n in pattern_nodes]

        logger.info(
            "GraphExtractionService: workspace=%s decisions=%d patterns=%d preferences=%d",
            payload.workspace_id,
            len(decision_nodes),
            len(pattern_nodes),
            len(preference_nodes),
        )

        return ExtractionResult(
            nodes=all_nodes,
            edges=edges,
            decisions=decisions_text,
            patterns=patterns_text,
            raw_response=raw_response,
        )


__all__ = [
    "ConversationExtractionPayload",
    "EdgeInput",
    "ExtractionResult",
    "GraphExtractionService",
    "NodeInput",
]

"""Multi-turn skill generation prompts.

Provides system prompts for each conversation phase of skill generation:
gathering (turn 1), refining (turn 2), and preview (turn 3+).

Phase 051: Conversational Skill Generator
"""

from __future__ import annotations

from typing import Any

_OUTPUT_FORMAT = """\
Return a JSON object with these exact keys:
{
  "name": "Skill Name",
  "description": "One-sentence description",
  "category": "engineering|design|product|general",
  "icon": "LucideIconName",
  "skill_content": "Full SKILL.md markdown content",
  "example_prompts": ["Example prompt 1", "Example prompt 2"],
  "context_requirements": ["Required context 1"],
  "tool_declarations": ["tool_name_1"],
  "graph_data": {
    "nodes": [{"id": "1", "type": "prompt", "position": {"x": 0, "y": 0}, "data": {"label": "Step 1", "content": "..."}}],
    "edges": [{"id": "e1-2", "source": "1", "target": "2", "type": "default"}],
    "viewport": {"x": 0, "y": 0, "zoom": 1}
  },
  "is_complete": false,
  "refinement_suggestion": "Suggestion for next refinement step or null if complete"
}

IMPORTANT: Return ONLY valid JSON. No markdown fences, no explanation text."""


def get_skill_generation_system_prompt(
    turn_number: int,
    current_draft: dict[str, Any] | None = None,
) -> str:
    """Return the system prompt for a skill generation turn.

    Args:
        turn_number: Current conversation turn (1-based).
        current_draft: Existing draft data from previous turns, or None for first turn.

    Returns:
        System prompt string instructing the LLM how to generate/refine the skill.
    """
    if turn_number == 1:
        return _gathering_prompt()
    if current_draft:
        return _refining_prompt(current_draft, turn_number)
    return _gathering_prompt()


def _gathering_prompt() -> str:
    """Turn 1: Extract skill intent and generate initial draft."""
    return f"""\
You are a skill creation assistant for Pilot Space, an AI-augmented software development platform.

The user wants to create a new AI skill. Your job is to:
1. Extract the skill intent from their message
2. Infer a good name, category, and icon
3. Generate initial SKILL.md content with sections:
   - Description
   - Instructions (detailed behavior)
   - Example Prompts (2-3 examples)
   - Context Requirements (what data the skill needs)
   - Tool Declarations (what tools the skill should use)
4. Generate a simple graph representation of the skill workflow
5. Suggest a refinement for the next iteration

Set is_complete to false on the first turn. Always provide a refinement_suggestion.

{_OUTPUT_FORMAT}"""


def _refining_prompt(current_draft: dict[str, Any], turn_number: int) -> str:
    """Turn 2+: Refine existing draft based on user feedback."""
    import json

    draft_json = json.dumps(current_draft, indent=2)
    is_preview = turn_number >= 3

    return f"""\
You are a skill creation assistant for Pilot Space. The user is refining their skill.

Current draft:
```json
{draft_json}
```

Apply the user's refinement request to the current draft. Return the complete updated skill.

{"Set is_complete to true — this is the preview/final turn. Set refinement_suggestion to null." if is_preview else "Set is_complete to false. Suggest the next refinement step in refinement_suggestion."}

{_OUTPUT_FORMAT}"""


def get_skill_refinement_prompt(
    current_draft: dict[str, Any],
    user_message: str,
) -> str:
    """Format the current draft + user refinement request into a user message.

    Args:
        current_draft: Current skill draft data.
        user_message: User's refinement request.

    Returns:
        Formatted user message for the LLM.
    """
    draft_summary = current_draft.get("name", "Untitled Skill")
    return f"""\
I'm refining the "{draft_summary}" skill.

Current skill content:
{current_draft.get("skill_content", "(no content yet)")}

My refinement request: {user_message}"""


def get_metadata_extraction_prompt(
    skill_content: str,
    conversation_history: list[str],
) -> str:
    """Extract metadata from skill content and conversation context.

    Args:
        skill_content: The generated SKILL.md content.
        conversation_history: List of user messages from the conversation.

    Returns:
        Prompt for metadata extraction.
    """
    history_text = "\n".join(f"- {msg}" for msg in conversation_history[-5:])
    return f"""\
Extract metadata from this skill definition and conversation context.

Skill content:
{skill_content}

Conversation context:
{history_text}

Return JSON with:
- example_prompts: list of 2-5 example prompts users might use with this skill
- context_requirements: list of data/context the skill needs to function
- tool_declarations: list of tool names the skill should have access to

Return ONLY valid JSON."""


__all__ = [
    "get_metadata_extraction_prompt",
    "get_skill_generation_system_prompt",
    "get_skill_refinement_prompt",
]

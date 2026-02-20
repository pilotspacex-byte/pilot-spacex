"""Keyword/regex-based intent classification for user messages.

Maps user messages to ``UserIntent`` values using pattern matching
(no LLM call). Also provides intent-to-rule-file mapping so the
prompt assembler knows which operational rules to inject.
"""

from __future__ import annotations

import re

from pilot_space.ai.prompt.models import IntentClassification, UserIntent

# ---------------------------------------------------------------------------
# Intent detection patterns (compiled regexes, case-insensitive)
# ---------------------------------------------------------------------------

_INTENT_PATTERNS: dict[UserIntent, list[re.Pattern[str]]] = {
    UserIntent.NOTE_WRITING: [
        re.compile(p, re.IGNORECASE)
        for p in [
            r"\bwrite\b",
            r"\bdraft\b",
            r"\bdocument\b",
            r"\badd\s+content\b",
            r"\bcreate\s+(?:a\s+)?note\b",
            r"\bimprove\s+writing\b",
            r"\bsummarize\b",
        ]
    ],
    UserIntent.NOTE_READING: [
        re.compile(p, re.IGNORECASE)
        for p in [
            r"\bread\s+note\b",
            r"\bshow\s+note\b",
            r"\bsearch\s+note\b",
            r"\bfind\s+in\s+note\b",
            r"\bnote\s+content\b",
        ]
    ],
    UserIntent.ISSUE_MGMT: [
        re.compile(p, re.IGNORECASE)
        for p in [
            r"\b(?:create|update|close|reopen|extract|enhance|find|search|list)\s+(?:an?\s+)?issues?\b",
            r"\bissues?\s+(?:list|board|status|state|tracker)\b",
            r"\b(?:PS|PILOT)-\d+",
            r"\bbug\b",
            r"\bfeature\s+request\b",
            r"\bticket\b",
            r"\bfind\s+duplicates\b",
            r"\bassign\s+(?:this|it|to|issue|task|ticket)\b",
            r"\breassign\b",
            r"\btransition\s+(?:the\s+)?state\b",
            r"\bissue\s+state\b",
            r"\bstate\s+(?:to|from)\b",
        ]
    ],
    UserIntent.PM_BLOCKS: [
        re.compile(p, re.IGNORECASE)
        for p in [
            r"\bdecision\s+record\b",
            r"\b(?:create|add|insert)\s+(?:a\s+)?form\b",
            r"\braci\s*(?:matrix)?\b",
            r"\brisk\s+(?:register|matrix|assessment)\b",
            r"\btimeline\b",
            r"\b(?:kpi|pm)\s+dashboard\b",
            r"\bchecklist\b",
            r"\bdiagram\b",
            r"\bmermaid\b",
            r"\bsprint\s+planning\b",
            r"\bpm\s+block\b",
        ]
    ],
    UserIntent.PROJECT_MGMT: [
        re.compile(p, re.IGNORECASE)
        for p in [
            r"\bproject\s+(?:status|settings|config|progress)\b",
            r"\b(?:create|update|delete)\s+(?:a\s+)?project\b",
            r"\bcycle\b",
            r"\bvelocity\b",
            r"\bcurrent\s+sprint\b",
        ]
    ],
    UserIntent.COMMENT: [
        re.compile(p, re.IGNORECASE)
        for p in [
            r"\b(?:add|post|create|leave)\s+(?:a\s+)?comment\b",
            r"\breply\s+to\s+(?:the\s+)?(?:comment|thread|feedback)\b",
            r"\bstart\s+(?:a\s+)?thread\b",
            r"\bmention\s+(?:the\s+|@)?\w+",
            r"\b(?:open|view)\s+(?:the\s+)?discussion\b",
        ]
    ],
}

# ---------------------------------------------------------------------------
# Intent → rule file mapping
# ---------------------------------------------------------------------------

INTENT_RULE_MAP: dict[UserIntent, tuple[str, ...]] = {
    UserIntent.NOTE_WRITING: ("notes.md",),
    UserIntent.NOTE_READING: ("notes.md",),
    UserIntent.ISSUE_MGMT: ("issues.md",),
    UserIntent.PM_BLOCKS: ("pm_blocks.md", "notes.md"),
    UserIntent.PROJECT_MGMT: (),
    UserIntent.COMMENT: (),
    UserIntent.GENERAL: (),
}

# ---------------------------------------------------------------------------
# Rule file summaries (injected when rule is NOT loaded, for awareness)
# ---------------------------------------------------------------------------

RULE_SUMMARIES: dict[str, str] = {
    "issues.md": "Issue creation/update rules: states, labels, confidence tagging, validation.",
    "notes.md": "Note handling: ghost text, annotations, block structure, batch writing, PM blocks.",
    "pm_blocks.md": "PM block types: decision, form, raci, risk, timeline, dashboard, diagrams, checklists.",
}

# ---------------------------------------------------------------------------
# Tie-breaking priority (higher = preferred when match counts are equal)
# ---------------------------------------------------------------------------

_INTENT_PRIORITY: dict[UserIntent, int] = {
    UserIntent.ISSUE_MGMT: 7,
    UserIntent.NOTE_WRITING: 6,
    UserIntent.PM_BLOCKS: 5,
    UserIntent.NOTE_READING: 4,
    UserIntent.PROJECT_MGMT: 3,
    UserIntent.COMMENT: 2,
    UserIntent.GENERAL: 1,
}


def classify_intent(
    message: str,
    *,
    has_note_context: bool = False,
) -> IntentClassification:
    """Classify a user message into a primary (and optional secondary) intent.

    Uses keyword/regex pattern matching. No LLM call.

    Args:
        message: The user's message text.
        has_note_context: Whether note context is present in the conversation.
            If True and no strong match, biases toward NOTE_WRITING.

    Returns:
        An ``IntentClassification`` with primary, optional secondary, and confidence.
    """
    # Normalize whitespace (collapse newlines, extra spaces) for reliable matching
    message = " ".join(message.split())

    match_counts: dict[UserIntent, int] = {}

    for intent, patterns in _INTENT_PATTERNS.items():
        count = sum(1 for p in patterns if p.search(message))
        if count > 0:
            match_counts[intent] = count

    if not match_counts:
        # No pattern matched — apply note context bias or fall back to GENERAL
        if has_note_context:
            return IntentClassification(
                primary=UserIntent.NOTE_WRITING,
                confidence=0.4,
            )
        return IntentClassification(
            primary=UserIntent.GENERAL,
            confidence=0.5,
        )

    # Sort by match count descending, then by priority for deterministic tie-breaking
    sorted_intents = sorted(
        match_counts.items(),
        key=lambda x: (x[1], _INTENT_PRIORITY.get(x[0], 0)),
        reverse=True,
    )

    primary_intent, primary_count = sorted_intents[0]
    total_matches = sum(c for _, c in sorted_intents)

    # Confidence based on how dominant the primary intent is
    confidence = min(primary_count / max(total_matches, 1), 1.0)

    secondary_intent: UserIntent | None = None
    if len(sorted_intents) > 1:
        secondary_intent = sorted_intents[1][0]

    return IntentClassification(
        primary=primary_intent,
        secondary=secondary_intent,
        confidence=round(confidence, 2),
    )


def get_rules_for_intent(
    classification: IntentClassification,
) -> tuple[list[str], list[str]]:
    """Determine which rule files to load and which to summarize.

    Combines rule files from both primary and secondary intents
    (deduplicated). Rules NOT loaded get their 1-line summaries
    included so the agent has awareness of all available rules.

    Args:
        classification: The classified intent result.

    Returns:
        Tuple of (rule_files_to_load, summaries_for_unloaded_rules).
    """
    files_to_load: list[str] = []
    seen: set[str] = set()

    for intent in (classification.primary, classification.secondary):
        if intent is None:
            continue
        for rule_file in INTENT_RULE_MAP.get(intent, ()):
            if rule_file not in seen:
                files_to_load.append(rule_file)
                seen.add(rule_file)

    # Summaries for rules NOT being loaded
    summaries: list[str] = []
    for rule_file, summary in RULE_SUMMARIES.items():
        if rule_file not in seen:
            summaries.append(f"- {rule_file}: {summary}")

    return files_to_load, summaries

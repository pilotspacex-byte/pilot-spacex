"""Mock margin annotation generator.

Provides deterministic margin annotations based on
content pattern analysis in note blocks.
"""

from pilot_space.ai.agents.margin_annotation_agent import (
    AnnotationSuggestion,
    MarginAnnotationInput,
    MarginAnnotationOutput,
)
from pilot_space.ai.prompts.margin_annotation import AnnotationType
from pilot_space.ai.providers.mock import MockResponseRegistry

# Annotation trigger patterns
ANNOTATION_TRIGGERS: list[dict[str, str | list[str] | AnnotationType | float]] = [
    {
        "keywords": ["todo", "fixme", "hack", "xxx", "note:"],
        "type": AnnotationType.ACTION_ITEM,
        "template": "Consider creating an issue to track this {keyword}.",
        "confidence": 0.85,
    },
    {
        "keywords": ["might", "maybe", "perhaps", "could", "possibly"],
        "type": AnnotationType.CLARIFICATION,
        "template": "This section could benefit from more specific requirements.",
        "confidence": 0.7,
    },
    {
        "keywords": ["important", "critical", "must", "required", "mandatory"],
        "type": AnnotationType.ISSUE_CANDIDATE,
        "template": "Key requirement identified - consider creating an issue.",
        "confidence": 0.8,
    },
    {
        "keywords": ["api", "endpoint", "request", "response", "schema"],
        "type": AnnotationType.TECHNICAL_REVIEW,
        "template": "API design consideration - document the contract.",
        "confidence": 0.75,
    },
    {
        "keywords": ["user", "customer", "stakeholder", "client"],
        "type": AnnotationType.EXPANSION,
        "template": "User-facing change - consider UX implications.",
        "confidence": 0.65,
    },
    {
        "keywords": ["?", "how", "what", "why", "when", "where"],
        "type": AnnotationType.QUESTION,
        "template": "Open question - needs clarification before implementation.",
        "confidence": 0.6,
    },
    {
        "keywords": ["see also", "related", "reference", "link", "cf."],
        "type": AnnotationType.REFERENCE,
        "template": "Cross-reference detected - verify link validity.",
        "confidence": 0.7,
    },
    {
        "keywords": ["complex", "complicated", "difficult", "tricky"],
        "type": AnnotationType.SIMPLIFICATION,
        "template": "Consider breaking this down into simpler components.",
        "confidence": 0.65,
    },
]


@MockResponseRegistry.register("MarginAnnotationAgent")
def generate_margin_annotation(
    input_data: MarginAnnotationInput,
) -> MarginAnnotationOutput:
    """Generate mock margin annotations.

    Analyzes note blocks to identify:
    1. Actionable items (TODOs, FIXMEs)
    2. Clarification needs (ambiguous language)
    3. Issue candidates (requirements)
    4. Technical notes (API, code)
    5. Questions (open items)

    Args:
        input_data: Margin annotation input with blocks.

    Returns:
        MarginAnnotationOutput with annotations.
    """
    annotations: list[AnnotationSuggestion] = []
    blocks_processed = 0

    for block in input_data.blocks:
        block_id = block.get("id", "")
        content = block.get("content", "")

        if not content or len(content) < 10:
            continue

        blocks_processed += 1
        content_lower = content.lower()

        # Track annotations per block to limit
        block_annotation_count = 0

        # Check each trigger pattern
        for trigger in ANNOTATION_TRIGGERS:
            if block_annotation_count >= 2:
                break

            keywords = trigger["keywords"]
            if not isinstance(keywords, list):
                continue

            for keyword in keywords:
                if keyword in content_lower:
                    annotation_type = trigger["type"]
                    template = trigger["template"]
                    confidence = trigger["confidence"]

                    if not isinstance(annotation_type, AnnotationType):
                        continue
                    if not isinstance(template, str):
                        continue
                    if not isinstance(confidence, float):
                        confidence = 0.7

                    annotations.append(
                        AnnotationSuggestion(
                            type=annotation_type,
                            block_id=block_id,
                            content=template.format(keyword=keyword),
                            confidence=confidence,
                        )
                    )
                    block_annotation_count += 1
                    break  # One annotation per trigger type per block

    # Limit total annotations
    annotations = annotations[:10]

    return MarginAnnotationOutput(
        annotations=annotations,
        block_count=blocks_processed,
    )


__all__ = ["generate_margin_annotation"]

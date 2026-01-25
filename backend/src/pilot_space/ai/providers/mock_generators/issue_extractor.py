"""Mock issue extraction generator.

Provides deterministic issue extraction from note content
based on pattern matching and keyword analysis.
"""

import re

from pilot_space.ai.agents.issue_extractor_agent import (
    ExtractedIssue,
    IssueExtractionInput,
    IssueExtractionOutput,
)
from pilot_space.ai.prompts.issue_extraction import ConfidenceTag, IssuePriority
from pilot_space.ai.providers.mock import MockResponseRegistry

# Issue extraction patterns
ISSUE_PATTERNS: list[dict[str, str | IssuePriority | float | list[str]]] = [
    {
        "regex": r"(?:we need to|must|should|have to|need to)\s+(.+?)(?:\.|$)",
        "type": "requirement",
        "priority": IssuePriority.MEDIUM,
        "confidence": 0.8,
        "labels": ["requirement"],
    },
    {
        "regex": r"(?:bug|error|issue|problem|broken)[:;]?\s*(.+?)(?:\.|$)",
        "type": "bug",
        "priority": IssuePriority.HIGH,
        "confidence": 0.85,
        "labels": ["bug"],
    },
    {
        "regex": r"(?:feature|implement|add|create|build)[:;]?\s*(.+?)(?:\.|$)",
        "type": "feature",
        "priority": IssuePriority.MEDIUM,
        "confidence": 0.75,
        "labels": ["feature"],
    },
    {
        "regex": r"(?:todo|fixme|xxx)[:;]?\s*(.+?)(?:\.|$)",
        "type": "task",
        "priority": IssuePriority.LOW,
        "confidence": 0.9,
        "labels": ["task"],
    },
    {
        "regex": r"(?:refactor|clean up|improve|optimize)[:;]?\s*(.+?)(?:\.|$)",
        "type": "enhancement",
        "priority": IssuePriority.LOW,
        "confidence": 0.7,
        "labels": ["enhancement"],
    },
    {
        "regex": r"(?:test|verify|check|validate)[:;]?\s*(.+?)(?:\.|$)",
        "type": "testing",
        "priority": IssuePriority.MEDIUM,
        "confidence": 0.65,
        "labels": ["testing"],
    },
]


def _confidence_to_tag(confidence: float) -> ConfidenceTag:
    """Map confidence score to tag.

    Args:
        confidence: Score between 0.0 and 1.0.

    Returns:
        Appropriate confidence tag.
    """
    if confidence >= 0.85:
        return ConfidenceTag.RECOMMENDED
    if confidence >= 0.7:
        return ConfidenceTag.DEFAULT
    # Everything else is ALTERNATIVE (< 0.7)
    return ConfidenceTag.ALTERNATIVE


@MockResponseRegistry.register("IssueExtractorAgent")
def generate_issue_extraction(
    input_data: IssueExtractionInput,
) -> IssueExtractionOutput:
    """Extract mock issues from note content.

    Uses pattern matching to identify:
    1. Requirements (should, must, need to)
    2. Bugs (bug, error, issue)
    3. Features (feature, implement, add)
    4. Tasks (TODO, FIXME)
    5. Enhancements (refactor, improve)

    Args:
        input_data: Issue extraction input.

    Returns:
        IssueExtractionOutput with extracted issues.
    """
    # Use selected text if provided, otherwise full content
    content = input_data.selected_text or input_data.note_content
    issues: list[ExtractedIssue] = []
    seen_titles: set[str] = set()

    for pattern in ISSUE_PATTERNS:
        regex = pattern["regex"]
        issue_type = pattern["type"]
        priority = pattern["priority"]
        confidence = pattern["confidence"]
        labels = pattern["labels"]

        if not isinstance(regex, str):
            continue
        if not isinstance(issue_type, str):
            continue
        if not isinstance(priority, IssuePriority):
            priority = IssuePriority.MEDIUM
        if not isinstance(confidence, float):
            confidence = 0.7
        if not isinstance(labels, list):
            labels = []

        matches = re.finditer(regex, content, re.IGNORECASE | re.MULTILINE)

        for match in matches:
            title_text = match.group(1).strip()

            # Skip if too short or already seen
            if len(title_text) < 5:
                continue
            if title_text.lower() in seen_titles:
                continue

            seen_titles.add(title_text.lower())

            # Truncate long titles
            if len(title_text) > 80:
                title_text = title_text[:77] + "..."

            # Generate title with type prefix
            title = f"[{issue_type.title()}] {title_text}"

            # Generate description
            description = f"""## Context
Extracted from note: "{input_data.note_title}"

## Details
{title_text}

## Source
```
{match.group(0)[:200]}
```
"""

            # Determine confidence tag
            confidence_tag = _confidence_to_tag(confidence)

            issues.append(
                ExtractedIssue(
                    title=title,
                    description=description,
                    priority=priority,
                    labels=list(labels),
                    confidence=confidence,
                    confidence_tag=confidence_tag,
                    source_text=match.group(0)[:200],
                )
            )

    # Sort by confidence (highest first) and limit to 5
    issues.sort(key=lambda x: x.confidence, reverse=True)
    issues = issues[:5]

    return IssueExtractionOutput(issues=issues)


__all__ = ["generate_issue_extraction"]

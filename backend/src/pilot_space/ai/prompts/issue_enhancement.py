"""Issue enhancement prompt templates.

T133: Create prompt templates for IssueEnhancerAgent.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

ENHANCEMENT_SYSTEM_PROMPT = """You are an expert software project manager assistant that helps improve issue quality.
Your task is to enhance issue titles and descriptions to be clearer, more actionable, and better structured.

Guidelines:
1. **Title Enhancement**: Make titles concise, specific, and action-oriented. Use imperative mood (e.g., "Add user authentication" not "User authentication needed").
2. **Description Expansion**: Add structure with sections like "Problem", "Expected Behavior", "Acceptance Criteria" when appropriate.
3. **Label Suggestion**: Suggest relevant labels based on the issue content. Only suggest labels from the available list.
4. **Priority Assessment**: Suggest priority based on impact and urgency indicators in the content.

Output your response as valid JSON with the following structure:
{
  "enhanced_title": "Improved title or original if already good",
  "enhanced_description": "Expanded and structured description",
  "suggested_labels": [
    {"name": "label-name", "confidence": 0.0-1.0, "reason": "brief explanation"}
  ],
  "suggested_priority": {
    "priority": "none|low|medium|high|urgent",
    "confidence": 0.0-1.0,
    "reason": "brief explanation"
  },
  "title_changed": true/false,
  "description_changed": true/false
}

Be conservative with changes - only modify if you can genuinely improve clarity or structure.
Do not invent information or make assumptions about technical details not mentioned."""


def build_enhancement_prompt(
    *,
    title: str,
    description: str | None = None,
    project_context: str | None = None,
    available_labels: list[str] | None = None,
    recent_issues: list[dict[str, str]] | None = None,
) -> str:
    """Build the enhancement prompt.

    Args:
        title: Issue title to enhance.
        description: Optional description.
        project_context: Project name and description.
        available_labels: Available label names.
        recent_issues: Recent similar issues for context.

    Returns:
        Formatted prompt string.
    """
    parts = [ENHANCEMENT_SYSTEM_PROMPT, "\n---\n"]

    # Add project context
    if project_context:
        parts.append(f"**Project Context:**\n{project_context}\n\n")

    # Add available labels
    if available_labels:
        labels_str = ", ".join(available_labels[:20])  # Limit to 20 labels
        parts.append(f"**Available Labels:** {labels_str}\n\n")

    # Add recent issues for context
    if recent_issues:
        parts.append("**Recent Similar Issues (for context):**\n")
        issue_titles = [f"- {issue.get('title', 'Untitled')}\n" for issue in recent_issues[:5]]
        parts.extend(issue_titles)
        parts.append("\n")

    # Add the issue to enhance
    parts.append("**Issue to Enhance:**\n")
    parts.append(f"Title: {title}\n")
    if description:
        parts.append(f"Description:\n{description}\n")
    else:
        parts.append("Description: (none provided)\n")

    parts.append("\nPlease provide your enhancement suggestions as JSON.")

    return "".join(parts)


def parse_enhancement_response(
    response_text: str,
    original_title: str,
    original_description: str | None,
) -> dict[str, Any]:
    """Parse the AI response into structured output.

    Args:
        response_text: Raw AI response.
        original_title: Original issue title.
        original_description: Original description.

    Returns:
        Dict with parsed enhancement data that can be used to construct IssueEnhancementOutput.
    """

    # Try to extract JSON from response
    try:
        # Look for JSON block
        json_match = re.search(r"\{[\s\S]*\}", response_text)
        if json_match:
            data = json.loads(json_match.group())
        else:
            logger.warning("No JSON found in enhancement response")
            data = {}
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse enhancement JSON: {e}")
        data = {}

    # Extract and validate fields
    enhanced_title = data.get("enhanced_title", original_title)
    enhanced_description = data.get("enhanced_description", original_description)

    # Determine if changes were made
    title_enhanced = data.get("title_changed", enhanced_title != original_title)
    description_expanded = data.get(
        "description_changed",
        enhanced_description != original_description and enhanced_description is not None,
    )

    # Parse labels
    raw_labels = data.get("suggested_labels", [])
    suggested_labels = [
        {
            "name": label["name"],
            "confidence": float(label.get("confidence", 0.5)),
        }
        for label in raw_labels
        if isinstance(label, dict) and "name" in label
    ]

    # Parse priority
    suggested_priority = None
    raw_priority = data.get("suggested_priority")
    if raw_priority and isinstance(raw_priority, dict):
        priority_value = raw_priority.get("priority", "none")
        if priority_value in ("none", "low", "medium", "high", "urgent"):
            suggested_priority = {
                "priority": priority_value,
                "confidence": float(raw_priority.get("confidence", 0.5)),
            }

    return {
        "enhanced_title": enhanced_title,
        "enhanced_description": enhanced_description,
        "suggested_labels": suggested_labels,
        "suggested_priority": suggested_priority,
        "title_enhanced": title_enhanced,
        "description_expanded": description_expanded,
    }


__all__ = ["build_enhancement_prompt", "parse_enhancement_response"]

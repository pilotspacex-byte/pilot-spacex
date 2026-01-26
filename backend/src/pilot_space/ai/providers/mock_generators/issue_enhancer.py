"""Mock issue enhancement generator.

Provides deterministic issue enhancements based on
keyword analysis in title and description.
"""

from pilot_space.ai.agents import (
    IssueEnhancementInput,
    IssueEnhancementOutput,
)
from pilot_space.ai.providers.mock import MockResponseRegistry

# Label inference rules based on keywords
LABEL_KEYWORDS: dict[str, list[str]] = {
    "bug": ["bug", "fix", "error", "crash", "broken", "issue", "fail", "wrong"],
    "feature": ["feature", "add", "new", "implement", "create", "build", "introduce"],
    "enhancement": ["improve", "enhance", "update", "optimize", "refactor", "better"],
    "documentation": ["doc", "readme", "guide", "tutorial", "comment", "explain"],
    "security": ["security", "auth", "permission", "vulnerability", "cve", "exploit"],
    "performance": ["performance", "slow", "fast", "optimize", "speed", "memory"],
    "ui": ["ui", "ux", "design", "style", "layout", "visual", "frontend"],
    "api": ["api", "endpoint", "rest", "graphql", "request", "response"],
    "testing": ["test", "coverage", "spec", "e2e", "unit", "integration"],
}

# Priority inference based on keywords
PRIORITY_KEYWORDS: dict[str, list[str]] = {
    "urgent": ["urgent", "critical", "asap", "blocker", "production", "outage"],
    "high": ["important", "high", "priority", "security", "crash", "data loss"],
    "medium": ["should", "need", "improve", "enhance", "expected"],
    "low": ["nice", "minor", "cosmetic", "later", "backlog", "maybe"],
}


@MockResponseRegistry.register("IssueEnhancerAgent")
def generate_issue_enhancement(
    input_data: IssueEnhancementInput,
) -> IssueEnhancementOutput:
    """Generate mock issue enhancement.

    Analyzes title and description to:
    1. Add prefix to title if missing
    2. Expand description with acceptance criteria
    3. Suggest labels based on keywords
    4. Estimate priority

    Args:
        input_data: Issue enhancement input.

    Returns:
        IssueEnhancementOutput with enhancements.
    """
    title = input_data.title
    description = input_data.description or ""
    combined_text = f"{title} {description}".lower()

    # Enhance title
    title_enhanced = False
    enhanced_title = title

    # Check if already prefixed
    prefixes = ["[", "feat:", "fix:", "chore:", "docs:", "refactor:", "test:"]
    if not any(title.startswith(p) for p in prefixes):
        # Determine prefix based on keywords
        for label, keywords in LABEL_KEYWORDS.items():
            if any(kw in combined_text for kw in keywords):
                if label == "bug":
                    enhanced_title = f"[Bug] {title}"
                elif label == "feature":
                    enhanced_title = f"[Feature] {title}"
                elif label == "enhancement":
                    enhanced_title = f"[Enhancement] {title}"
                elif label == "documentation":
                    enhanced_title = f"[Docs] {title}"
                else:
                    enhanced_title = f"[{label.title()}] {title}"
                title_enhanced = True
                break

        # Default prefix if no match
        if not title_enhanced:
            enhanced_title = f"[Task] {title}"
            title_enhanced = True

    # Expand description
    enhanced_description = f"""{description}

## Acceptance Criteria
- [ ] Implementation matches the specification
- [ ] Unit tests cover the main functionality
- [ ] Documentation is updated if needed
- [ ] No regression in existing functionality

## Technical Notes
Consider the existing patterns in the codebase when implementing this change.
"""

    # Infer labels from keywords
    suggested_labels: list[dict[str, str | float]] = []
    available_labels = set(input_data.available_labels or [])

    for label, keywords in LABEL_KEYWORDS.items():
        if any(kw in combined_text for kw in keywords):
            # Check if label exists in available labels
            if not available_labels or label in available_labels:
                # Higher confidence if keyword in title
                confidence = 0.85 if any(kw in title.lower() for kw in keywords) else 0.65
                suggested_labels.append({"name": label, "confidence": confidence})

    # Default label if none found
    if not suggested_labels:
        suggested_labels.append({"name": "needs-triage", "confidence": 0.5})

    # Limit to top 3 labels
    suggested_labels = sorted(suggested_labels, key=lambda x: float(x["confidence"]), reverse=True)[
        :3
    ]

    # Estimate priority
    suggested_priority: dict[str, str | float] = {"priority": "medium", "confidence": 0.7}
    for priority, keywords in PRIORITY_KEYWORDS.items():
        if any(kw in combined_text for kw in keywords):
            confidence = 0.8 if any(kw in title.lower() for kw in keywords) else 0.6
            suggested_priority = {"priority": priority, "confidence": confidence}
            break

    return IssueEnhancementOutput(
        enhanced_title=enhanced_title,
        enhanced_description=enhanced_description,
        suggested_labels=suggested_labels,
        suggested_priority=suggested_priority,
        title_enhanced=title_enhanced,
        description_expanded=True,
    )


__all__ = ["generate_issue_enhancement"]

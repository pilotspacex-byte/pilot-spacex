"""Mock duplicate detector generator.

Provides deterministic duplicate detection based on
keyword similarity and title matching.
"""

from uuid import uuid4

from pilot_space.ai.agents import (
    DuplicateCandidate,
    DuplicateDetectionInput,
    DuplicateDetectionOutput,
)
from pilot_space.ai.providers.mock import MockResponseRegistry

# Mock issue database for duplicate matching
MOCK_ISSUES: list[dict[str, str | float | list[str]]] = [
    {
        "identifier": "PILOT-101",
        "title": "Fix authentication bug in login flow",
        "keywords": ["authentication", "login", "bug", "fix"],
    },
    {
        "identifier": "PILOT-102",
        "title": "Implement user registration feature",
        "keywords": ["user", "registration", "feature", "implement"],
    },
    {
        "identifier": "PILOT-103",
        "title": "Update API documentation",
        "keywords": ["api", "documentation", "update"],
    },
    {
        "identifier": "PILOT-104",
        "title": "Fix login validation error",
        "keywords": ["login", "validation", "error", "fix"],
    },
    {
        "identifier": "PILOT-105",
        "title": "Optimize database queries performance",
        "keywords": ["database", "queries", "performance", "optimize"],
    },
]


def _calculate_similarity(text1: str, text2: str, keywords: list[str]) -> float:
    """Calculate similarity score between two texts.

    Args:
        text1: First text to compare.
        text2: Second text to compare.
        keywords: Keywords from the second text.

    Returns:
        Similarity score (0-1).
    """
    text1_lower = text1.lower()
    text2_lower = text2.lower()

    # Exact match
    if text1_lower == text2_lower:
        return 1.0

    # Keyword matching
    matching_keywords = sum(1 for kw in keywords if kw in text1_lower)
    keyword_score = matching_keywords / len(keywords) if len(keywords) > 0 else 0.0

    # Word overlap
    words1 = set(text1_lower.split())
    words2 = set(text2_lower.split())
    overlap = len(words1 & words2)
    word_score = overlap / len(words1) if len(words1) > 0 else 0.0

    # Weighted combination
    similarity = (keyword_score * 0.6) + (word_score * 0.4)

    return min(similarity, 1.0)


def _generate_explanation(similarity: float) -> str:
    """Generate explanation for similarity score.

    Args:
        similarity: Similarity score.

    Returns:
        Human-readable explanation.
    """
    if similarity >= 0.95:
        return "Very high similarity - likely exact duplicate"
    if similarity >= 0.9:
        return "High similarity - likely duplicate or closely related"
    if similarity >= 0.85:
        return "Significant similarity - may be duplicate or related"
    if similarity >= 0.8:
        return "Moderate similarity - possibly related issue"
    return "Some similarity - review for potential relationship"


@MockResponseRegistry.register("DuplicateDetectorAgent")
def generate_duplicate_detection(
    input_data: DuplicateDetectionInput,
) -> DuplicateDetectionOutput:
    """Generate mock duplicate detection results.

    Analyzes title and description to find similar issues:
    1. Keyword matching
    2. Word overlap analysis
    3. Similarity scoring

    Args:
        input_data: Duplicate detection input.

    Returns:
        DuplicateDetectionOutput with candidates.
    """
    # Combine title and description
    text_to_compare = input_data.title
    if input_data.description:
        text_to_compare = f"{input_data.title} {input_data.description}"

    candidates: list[DuplicateCandidate] = []

    # Compare against mock issues
    for issue in MOCK_ISSUES:
        # Skip excluded issue
        if input_data.exclude_issue_id and str(issue.get("identifier")) == str(
            input_data.exclude_issue_id
        ):
            continue

        identifier = str(issue.get("identifier", ""))
        title = str(issue.get("title", ""))
        keywords_raw = issue.get("keywords", [])
        keywords = keywords_raw if isinstance(keywords_raw, list) else []

        # Calculate similarity
        similarity = _calculate_similarity(text_to_compare, title, keywords)

        # Filter by threshold
        if similarity >= input_data.threshold:
            candidates.append(
                DuplicateCandidate(
                    issue_id=uuid4(),  # Mock UUID
                    identifier=identifier,
                    title=title,
                    similarity=similarity,
                    explanation=_generate_explanation(similarity),
                )
            )

    # Sort by similarity (highest first)
    candidates.sort(key=lambda x: x.similarity, reverse=True)

    # Limit results
    candidates = candidates[: input_data.max_results]

    # Determine if likely duplicate exists
    has_likely_duplicate = any(c.similarity >= 0.85 for c in candidates)
    highest_similarity = max((c.similarity for c in candidates), default=0.0)

    return DuplicateDetectionOutput(
        candidates=candidates,
        has_likely_duplicate=has_likely_duplicate,
        highest_similarity=highest_similarity,
    )


__all__ = ["generate_duplicate_detection"]

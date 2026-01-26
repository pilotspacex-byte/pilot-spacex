"""Mock assignee recommender generator.

Provides deterministic assignee recommendations based on
workload patterns and label matching.
"""

from uuid import uuid4

from pilot_space.ai.agents import (
    AssigneeRecommendation,
    AssigneeRecommendationInput,
    AssigneeRecommendationOutput,
)
from pilot_space.ai.providers.mock import MockResponseRegistry


@MockResponseRegistry.register("AssigneeRecommenderAgent")
def generate_assignee_recommendation(
    input_data: AssigneeRecommendationInput,
) -> AssigneeRecommendationOutput:
    """Generate mock assignee recommendations.

    Simulates workload-based and expertise-based assignment:
    1. Balanced workload distribution
    2. Label expertise matching
    3. Recent activity consideration

    Args:
        input_data: Assignee recommendation input.

    Returns:
        AssigneeRecommendationOutput with recommendations.
    """
    # Use provided team members or generate mock members
    team_members = input_data.team_members
    if not team_members:
        # Generate 3 mock team members
        from pilot_space.ai.agents import TeamMember

        team_members = [
            TeamMember(
                user_id=uuid4(),
                name="Alice Developer",
                email="alice@example.com",
                current_workload=2,
                expertise_labels=["backend", "api", "database"],
                recent_issue_count=5,
            ),
            TeamMember(
                user_id=uuid4(),
                name="Bob Engineer",
                email="bob@example.com",
                current_workload=0,
                expertise_labels=["frontend", "ui", "testing"],
                recent_issue_count=3,
            ),
            TeamMember(
                user_id=uuid4(),
                name="Carol Architect",
                email="carol@example.com",
                current_workload=7,
                expertise_labels=["security", "performance", "architecture"],
                recent_issue_count=8,
            ),
        ]

    issue_labels = input_data.issue_labels or []
    recommendations: list[AssigneeRecommendation] = []

    # Score each team member
    for member in team_members:
        score = 0.5  # Base score
        reasons: list[str] = []

        # Label expertise matching
        if issue_labels and member.expertise_labels:
            matching_labels = set(issue_labels) & set(member.expertise_labels)
            if matching_labels:
                label_score = len(matching_labels) / len(issue_labels) * 0.3
                score += label_score
                reasons.append(f"Expert in: {', '.join(matching_labels)}")

        # Workload balancing (lower is better)
        if member.current_workload == 0:
            score += 0.2
            reasons.append("Available (no active issues)")
        elif member.current_workload <= 3:
            score += 0.1
            reasons.append(f"Light workload ({member.current_workload} issues)")
        elif member.current_workload >= 7:
            score -= 0.15
            reasons.append(f"Heavy workload ({member.current_workload} issues)")

        # Recent activity bonus
        if member.recent_issue_count > 0:
            activity_score = min(member.recent_issue_count / 10, 0.1)
            score += activity_score
            reasons.append(f"Active contributor ({member.recent_issue_count} recent)")

        reason = " | ".join(reasons) if reasons else "Available team member"

        recommendations.append(
            AssigneeRecommendation(
                user_id=member.user_id,
                name=member.name,
                confidence=min(score, 1.0),
                reason=reason,
            )
        )

    # Sort by confidence (highest first) and limit to 5
    recommendations.sort(key=lambda x: x.confidence, reverse=True)
    recommendations = recommendations[:5]

    has_strong_match = any(r.confidence >= 0.7 for r in recommendations)

    return AssigneeRecommendationOutput(
        recommendations=recommendations,
        has_strong_match=has_strong_match,
    )


__all__ = ["generate_assignee_recommendation"]

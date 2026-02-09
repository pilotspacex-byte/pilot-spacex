"""Homepage Hub application services (CQRS-lite).

Query services:
- GetActivityService: Recent notes + issues grouped by day
- GetDigestService: Latest AI digest with dismissed filtering

Command services:
- DismissSuggestionService: Persist user dismissal
"""

from pilot_space.application.services.homepage.dismiss_suggestion_service import (
    DismissSuggestionPayload,
    DismissSuggestionService,
)
from pilot_space.application.services.homepage.get_activity_service import (
    ActivityItem,
    GetActivityPayload,
    GetActivityResult,
    GetActivityService,
    GroupedActivity,
)
from pilot_space.application.services.homepage.get_digest_service import (
    DigestSuggestionItem,
    GetDigestPayload,
    GetDigestResult,
    GetDigestService,
)

__all__ = [
    "ActivityItem",
    "DigestSuggestionItem",
    "DismissSuggestionPayload",
    "DismissSuggestionService",
    "GetActivityPayload",
    "GetActivityResult",
    "GetActivityService",
    "GetDigestPayload",
    "GetDigestResult",
    "GetDigestService",
    "GroupedActivity",
]

"""Discussion application services (CQRS-lite).

Command services:
- CreateDiscussionService: Create discussions with initial comment
"""

from pilot_space.application.services.discussion.create_discussion_service import (
    CreateDiscussionPayload,
    CreateDiscussionResult,
    CreateDiscussionService,
)

__all__ = [
    "CreateDiscussionPayload",
    "CreateDiscussionResult",
    "CreateDiscussionService",
]

"""AI Infrastructure Services.

This package provides foundational services for the AI layer:

- SecureKeyStorage: BYOK API key encryption (DD-002)
- ApprovalService: Human-in-the-loop approval flow (DD-003)
- CostTracker: Usage and cost tracking per workspace
- CircuitBreaker: Provider resilience and failover
- ResilientExecutor: Retry logic with exponential backoff (T016)
- AIResponseCache: Response caching for cost optimization (T319)

All services are registered in the DI container (container.py).

References:
- T004: Create ai/infrastructure/__init__.py module initialization
- T016: ResilientExecutor with retry and circuit breaker
- T319: Response caching implementation
- specs/004-mvp-agents-build/tasks/P1-T001-T005.md
- specs/004-mvp-agents-build/tasks/P29-T313-T331.md
- docs/DESIGN_DECISIONS.md#DD-002 (BYOK model)
- docs/DESIGN_DECISIONS.md#DD-003 (Approval flow)
"""

from pilot_space.ai.infrastructure.approval import (
    ActionType,
    ApprovalLevel,
    ApprovalRequest,
    ApprovalService,
    ApprovalStatus,
    ProjectSettings,
)
from pilot_space.ai.infrastructure.cache import (
    DEFAULT_CACHE_TTL_SECONDS,
    AIResponseCache,
)
from pilot_space.ai.infrastructure.resilience import (
    ResilientExecutor,
    RetryConfig,
    with_resilience,
)

__all__ = [
    "DEFAULT_CACHE_TTL_SECONDS",
    "AIResponseCache",
    "ActionType",
    "ApprovalLevel",
    "ApprovalRequest",
    "ApprovalService",
    "ApprovalStatus",
    "ProjectSettings",
    "ResilientExecutor",
    "RetryConfig",
    "with_resilience",
]

"""AI layer for Pilot Space.

This package contains AI-related components:
- agents/: AI agents (GhostText, PRReview, AIContext, etc.)
- prompts/: Prompt templates for each agent
- rag/: RAG pipeline (embeddings, retriever, indexer)
- providers/: LLM provider adapters (Anthropic, OpenAI, Google)
- utils/: AI utilities (retry, circuit breaker, telemetry)

Provider Routing (DD-011):
- Claude → Code analysis, PR review, complex reasoning
- Gemini Flash → Low-latency tasks (ghost text)
- OpenAI → Embeddings (text-embedding-3-large)
"""

from pilot_space.ai.circuit_breaker import CircuitBreaker, CircuitBreakerConfig
from pilot_space.ai.degradation import (
    DegradationLevel,
    DegradedResponse,
    GhostTextFallback,
    IssueExtractionFallback,
    MarginAnnotationFallback,
)
from pilot_space.ai.exceptions import (
    AgentExecutionError,
    AIConfigurationError,
    AIError,
    AITimeoutError,
    InvalidResponseError,
    ProviderUnavailableError,
    RateLimitError,
    TokenLimitExceededError,
)
from pilot_space.ai.telemetry import AIMetrics, AIOperation, AIProvider

__all__ = [
    # Exceptions
    "AIConfigurationError",
    "AIError",
    # Telemetry
    "AIMetrics",
    "AIOperation",
    "AIProvider",
    "AITimeoutError",
    "AgentExecutionError",
    # Circuit Breaker
    "CircuitBreaker",
    "CircuitBreakerConfig",
    # Degradation
    "DegradationLevel",
    "DegradedResponse",
    "GhostTextFallback",
    "InvalidResponseError",
    "IssueExtractionFallback",
    "MarginAnnotationFallback",
    "ProviderUnavailableError",
    "RateLimitError",
    "TokenLimitExceededError",
]

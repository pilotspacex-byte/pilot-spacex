"""Queue infrastructure for Pilot Space.

Backend: Supabase Queues (pgmq + pg_cron)

Queues:
- ai_high: PR review, AI context generation (5 min timeout)
- ai_normal: Embedding generation, duplicate detection
- ai_low: Knowledge graph recalculation

Features:
- Priority levels (high, normal, low)
- Dead letter queue for failed jobs
- Exponential backoff retry
"""

from pilot_space.infrastructure.queue.error_handlers import (
    CircuitBreaker,
    CircuitOpenError,
    CircuitState,
    DeadLetterRecord,
    EdgeFunctionTimeoutError,
    RetryConfig,
    RetryState,
    RetryStrategy,
    calculate_delay,
    is_retryable,
    should_dead_letter,
    with_circuit_breaker,
    with_edge_function_timeout,
    with_retry,
)
from pilot_space.infrastructure.queue.supabase_queue import (
    MessageStatus,
    QueueConnectionError,
    QueueMessage,
    QueueName,
    QueueOperationError,
    SupabaseQueueClient,
    SupabaseQueueError,
)

__all__ = [
    "CircuitBreaker",
    "CircuitOpenError",
    "CircuitState",
    "DeadLetterRecord",
    "EdgeFunctionTimeoutError",
    "MessageStatus",
    "QueueConnectionError",
    "QueueMessage",
    "QueueName",
    "QueueOperationError",
    "RetryConfig",
    "RetryState",
    "RetryStrategy",
    "SupabaseQueueClient",
    "SupabaseQueueError",
    "calculate_delay",
    "is_retryable",
    "should_dead_letter",
    "with_circuit_breaker",
    "with_edge_function_timeout",
    "with_retry",
]

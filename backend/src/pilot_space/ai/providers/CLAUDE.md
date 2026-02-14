# Provider Routing, Resilience & Cost Tracking - Pilot Space AI Layer

**For AI layer overview, see parent [ai/CLAUDE.md](../CLAUDE.md)**

---

## Overview

The providers module handles task-based provider routing (DD-011), circuit breaker resilience, cost tracking, and error propagation for all AI operations. It ensures the right model handles each task type, with per-task fallback chains and budget controls.

---

## Provider Routing (DD-011)

### ProviderSelector

**File**: `provider_selector.py`

Routes each AI task to the optimal provider based on task complexity, latency requirements, and cost.

- **Provider enum** (3 providers): `ANTHROPIC`, `OPENAI`, `GOOGLE`. See `provider_selector.py:Provider`.
- **TaskType enum** (20 task types): Organized into Opus tier (complex reasoning), Sonnet tier (standard), Haiku/Flash tier (latency-sensitive), and Embeddings. See `provider_selector.py:TaskType`.
- **ProviderConfig**: Defines primary provider, fallback chain, max_tokens, timeout. See `provider_selector.py:ProviderConfig`.
- **Model ID constants**: Defined on `ProviderSelector` class (e.g., `ANTHROPIC_OPUS`, `ANTHROPIC_SONNET`, `GOOGLE_FLASH`).

### Task-to-Provider Mapping

| Task | Provider | Model | SLA |
|------|----------|-------|-----|
| PR review | Claude Opus | `claude-opus-4-5` | <5min |
| AI context | Claude Opus | `claude-opus-4-5` | <30s |
| Code generation | Claude Sonnet | `claude-sonnet-4` | <30s |
| Template filling | Claude Sonnet | `claude-sonnet-4` | <30s |
| Ghost text | Gemini Flash | `gemini-2.0-flash` | <2.5s |
| Embeddings | OpenAI | `text-embedding-3-large` | <500ms |

Full routing table defined in `provider_selector.py:ProviderSelector._ROUTING_TABLE`.

### Per-Task Fallback Chains

```
PR_REVIEW:        Opus -> Sonnet
AI_CONTEXT:       Opus -> Sonnet
GHOST_TEXT:        Gemini Flash -> Sonnet
TEMPLATE_FILLING:  Sonnet -> Haiku
SEMANTIC_SEARCH:   OpenAI (no fallback)
```

### Selection API

- `select(task_type) -> ProviderConfig`: Get provider config for task
- `get_fallback()`: Get next provider on `ProviderUnavailableError`
- `is_provider_healthy(provider)`: Check circuit breaker state before routing

---

## Resilience Patterns

### ResilientExecutor

**File**: `ai/infrastructure/resilience.py`

Wraps all provider calls with retry logic and circuit breaker integration. See `resilience.py:ResilientExecutor` and `resilience.py:RetryConfig`.

**Execution flow**: Circuit breaker check (fail-fast if OPEN) -> Execute with timeout -> On failure: exponential backoff with jitter -> Retry up to max_retries -> On success: record on circuit breaker.

### Circuit Breaker

**File**: `ai/circuit_breaker.py`

Per-provider state machine preventing cascading failures. See `circuit_breaker.py:CircuitBreaker`.

```
CLOSED (normal) --[3 failures]--> OPEN (fail-fast) --[30s]--> HALF_OPEN (probe)
  ^                                                               |
  +--- success ---------------------------------------------------+
```

- `CircuitBreaker.get_or_create(name)`: Singleton per provider (not per-request)
- `get_metrics()`: Returns name, state, failure_count, success_count, last_failure_time

### Key Constants

| Constant | Value | Context |
|----------|-------|---------|
| CIRCUIT_BREAKER_TIMEOUT | 30 seconds | OPEN -> HALF_OPEN transition |
| FAILURE_THRESHOLD | 3 | Consecutive failures to open circuit |
| MAX_RETRIES | 3 | Exponential backoff attempts |
| BASE_DELAY | 1.0 second | Retry initial delay |
| MAX_DELAY | 60.0 seconds | Retry cap |
| JITTER | 0.3 | Randomization on retry delays |

---

## Cost Tracking

### CostTracker

**File**: `ai/infrastructure/cost_tracker.py`

Tracks per-request token usage, calculates USD cost, persists `AICostRecord` to PostgreSQL, triggers budget alerts at 90% of workspace limit. See `cost_tracker.py:CostTracker`.

**Interface**: `track_request(workspace_id, model_id, prompt_tokens, completion_tokens, cached_tokens)`.

### Pricing Table (per 1M tokens)

| Provider | Model ID | Input | Output |
|----------|----------|-------|--------|
| Claude Opus | `claude-opus-4-5-20251101` | $15.00 | $75.00 |
| Claude Sonnet | `claude-sonnet-4-20250514` | $3.00 | $15.00 |
| Claude Haiku | `claude-3-5-haiku-20241022` | $1.00 | $5.00 |
| Gemini Pro | `gemini-2.0-pro` | $1.25 | $5.00 |
| Gemini Flash | `gemini-2.0-flash` | $0.075 | $0.30 |
| GPT-4o | `gpt-4o` | $5.00 | $15.00 |
| GPT-4o Mini | `gpt-4o-mini` | $0.15 | $0.60 |
| Embeddings | `text-embedding-3-large` | $0.13 | $0.00 |

Cached tokens receive 90% discount on input.

---

## Error Handling

**File**: `ai/exceptions.py`

| Exception | Purpose | Recoverable |
|-----------|---------|-------------|
| `AIError` | Base exception for all AI errors | Varies |
| `ProviderUnavailableError` | Circuit breaker OPEN, provider down | Yes (fallback) |
| `AITimeoutError` | Operation exceeded timeout | Yes (retry) |
| `RateLimitError` | Provider rate limit hit (includes `retry_after`) | Yes (backoff) |

Errors propagate to frontend as SSE events with `recoverable` flag and `retry_after_seconds`.

---

## Adding a New Provider

1. Add to `Provider` enum in `provider_selector.py`
2. Add task mapping to `_ROUTING_TABLE` in `provider_selector.py`
3. Add pricing to `cost_tracker.py`
4. Create circuit breaker: `CircuitBreaker.get_or_create("new_provider")`
5. Test fallback chain: `pytest tests/ai/test_provider_selector.py`

---

## Key Files

| Component | File | Purpose |
|-----------|------|---------|
| Provider Selector | `ai/providers/provider_selector.py` | Task -> Provider routing (DD-011) |
| Key Validator | `ai/providers/key_validator.py` | BYOK key verification |
| Resilience | `ai/infrastructure/resilience.py` | ResilientExecutor (retry + CB) |
| Circuit Breaker | `ai/circuit_breaker.py` | Per-provider state machine |
| Cost Tracker | `ai/infrastructure/cost_tracker.py` | Token usage + pricing |
| Exceptions | `ai/exceptions.py` | AI-specific exception hierarchy |

---

## Related Documentation

- **AI Layer Parent**: [ai/CLAUDE.md](../CLAUDE.md)
- **Agents**: [agents/CLAUDE.md](../agents/CLAUDE.md)
- **MCP Tools**: [mcp/CLAUDE.md](../mcp/CLAUDE.md)
- **Design Decisions**: DD-011 (provider routing), DD-003 (approval)

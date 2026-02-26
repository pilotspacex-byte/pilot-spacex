# Pilot Space Agent: Infrastructure & Resilience

> **Location**: `backend/src/pilot_space/ai/infrastructure/`, `providers/`, `session/`, `services/`, `workers/`
> **Design Decisions**: DD-002 (BYOK), DD-011 (Provider Routing), DD-060 (Supabase Platform)

## Overview

The infrastructure layer is the **operational backbone** of the AI system — provider routing, circuit breakers, retry logic, BYOK key encryption, cost tracking, rate limiting, AI caching, ghost text generation, session persistence, background workers, and observability. It is designed for failure-tolerant operation: the AI system degrades gracefully when providers are unavailable, never taking down the rest of the application.

---

## Provider Routing (DD-011)

### `providers/provider_selector.py`

**Purpose**: Map every AI task type to the optimal provider+model pair based on complexity, latency budget, and cost.

**Task → Model routing table**:

| Tier | Tasks | Primary | Fallback | Rationale |
|------|-------|---------|---------|-----------|
| **Opus** (complex) | PR Review, AI Context, Task Decomposition | Claude Opus 4.5 | Sonnet | Deep reasoning, code analysis |
| **Sonnet** (standard) | Code Gen, Doc Gen, Issue Enhancement, Extraction, Conversation | Claude Sonnet | Haiku | Balanced quality/cost |
| **Haiku** (speed) | Ghost Text, Notification Priority, Assignee Recommendation | Claude Haiku | Sonnet | <2.5s latency SLA |
| **Embeddings** | Semantic Search, Duplicate Detection | OpenAI text-embedding-3-large | — | 3072-dim, HNSW-indexed |

**Key methods**:
```python
selector.select(task_type: TaskType) → (provider, model)
selector.select_with_config(task_type) → ProviderConfig  # includes fallback
selector.is_provider_healthy(provider) → bool            # circuit breaker check
selector.get_fallback(task_type) → (provider, model) | None
```

**Per-provider circuit breakers**: `ProviderSelector` maintains one `CircuitBreaker` per provider. If a provider's CB is OPEN, `select()` automatically returns the fallback model.

**BYOK resolution**: `select_with_config()` returns the config needed to retrieve the right BYOK key for the selected provider. The caller resolves the key via `SecureKeyStorage`.

---

## Circuit Breaker (`circuit_breaker.py`)

**States**:
```
CLOSED (normal) ──[3 failures]──→ OPEN (fail-fast)
                                     │
                              [30s wait]
                                     ↓
                                HALF_OPEN (probe)
                                     │
                     ┌───────────────┴──────────────┐
               [success]                        [failure]
                  CLOSED                          OPEN
```

**Configuration**:
```python
CircuitBreakerConfig(
    failure_threshold=3,      # consecutive failures to OPEN
    timeout_seconds=30.0,     # OPEN → HALF_OPEN wait
    success_threshold=1,      # successes in HALF_OPEN to CLOSE
    half_open_max_calls=1,    # max concurrent probes
)
```

**Usage**: `CircuitBreaker.get_or_create("anthropic")` returns a singleton per provider. All callers share the same CB state, so 3 failures from any user opens the circuit for all users.

**Why singleton per provider**: One workspace's failures should protect all workspaces. Cascading failures from a degraded provider would affect all users; a single shared CB trips after 3 collective failures.

---

## Retry & Backoff (`infrastructure/resilience.py`)

**Exponential backoff with jitter**:
```
delay = base * 2^(attempt-1)        # 1s, 2s, 4s, 8s...
delay = min(delay, 60s)             # cap at 60s
delay += random(-delay*0.3, +delay*0.3)  # ±30% jitter
```

**Default config**: 3 retries, 1s base, 60s cap, ±30% jitter.

**Retryable errors**: `AITimeoutError`, `RateLimitError`, `ConnectionError`, `asyncio.TimeoutError`

**Non-retryable**: `ProviderUnavailableError` (CB open — fail-fast), auth errors, `ValueError`

**Streaming support**: Retries apply to initial connection only. Once streaming starts, errors propagate immediately — prevents partial stream delivery.

---

## Graceful Degradation (`degradation.py`)

Features degrade silently when the AI provider is unavailable:

| Feature | Degraded behavior | User impact |
|---------|------------------|-------------|
| Ghost Text | Returns empty suggestion | No completion, typing unaffected |
| Margin Annotations | Returns empty list | No new annotations, existing preserved |
| Issue Enhancement | Returns original unmodified | Issues visible, AI fields missing |
| Issue Extraction | Returns empty extraction | Manual creation required |
| Duplicate Detection | Returns no duplicates | No false positives |

**Implementation**: `@graceful_degradation(fallback_fn)` decorator. On `AIError`, calls `fallback_fn()` and returns `DegradedResponse(data=fallback, degraded=True)`.

**Non-breaking guarantee**: All degradation paths are synchronous and instant. The application never blocks waiting for a degraded AI feature.

---

## Anthropic Client Pool (`infrastructure/anthropic_client_pool.py`)

**Purpose**: Avoid allocating a new TCP connection pool on every request. Ghost text at 500ms polling frequency would create hundreds of short-lived clients per minute without pooling.

**Implementation**:
- Per-workspace `AsyncAnthropic` instances keyed by SHA-256 hash of the API key (first 16 chars)
- Hash prevents plaintext keys appearing in dict keys or logs
- `evict(api_key)` removes client on key rotation

**Why not one global client?**: Each BYOK workspace uses a different API key → different billing account → needs separate client.

---

## Cost Tracking (`infrastructure/cost_tracker.py`)

**Pricing table** (per 1M tokens, USD):

| Model | Input | Output |
|-------|-------|--------|
| Claude Opus 4.5 | $15.00 | $75.00 |
| Claude Sonnet 4 | $3.00 | $15.00 |
| Claude Haiku 3.5 | $1.00 | $5.00 |
| OpenAI text-embedding-3-large | $0.13 | $0.00 |
| Gemini Flash | $0.075 | $0.30 |

Cached input tokens receive **90% discount**.

**Per-request tracking**:
```python
await tracker.track(
    workspace_id, user_id, agent_name,
    provider, model, input_tokens, output_tokens
)
# → INSERT INTO ai_cost_records
```

**Aggregate queries**: `get_workspace_summary(workspace_id, days=30)` → by_provider, by_agent, by_model breakdown. `get_cost_trends()` → daily/weekly period-over-period trends.

---

## Encrypted Key Storage (`infrastructure/key_storage.py`)

**Security model** — BYOK keys at rest:
```
Master secret (env var)
    ↓ PBKDF2-HMAC-SHA256 (600K iterations, OWASP 2023)
256-bit key
    ↓ Fernet (AES-128-CBC + HMAC)
Encrypted ciphertext → WorkspaceAPIKey table
```

**Fixed salt** (`b"pilotspace_fernet_kdf_v1"`) tied to deployment. Key rotation requires re-encrypting all stored keys.

**API**:
```python
await storage.store_api_key(workspace_id, "anthropic", "sk-ant-...")
key = await storage.get_api_key(workspace_id, "anthropic")  # decrypts
await storage.validate_api_key("anthropic", key)  # test call, doesn't store
```

**Safety**: Keys never appear in logs (masked as `sk-ant-XXXX...XXXX`), never in exception messages.

---

## Rate Limiter (`infrastructure/rate_limiter.py`)

**Algorithm**: Redis sliding window sorted set.
- Key: `rate_limit:{scope}:{user_id}`
- On each request: remove entries older than window start, count current, add new entry if under limit
- Ghost text limit: 60 req/min per user (aggressive — prevents abuse)

**On limit hit**: Returns `False` → caller returns empty degraded response. No HTTP 429 for ghost text (would disrupt typing).

---

## AI Cache (`infrastructure/cache.py`)

**What's cached**: Skill outputs and AI responses that are deterministic on the same input.

**Cache policy**: 7-day TTL in Redis. Key = SHA-256 of (workspace_id + prompt hash + model).

**Cached token discount**: Anthropic charges 90% less for cached prompt tokens. Cache-aware cost tracking credits this discount.

**Why 7 days**: Skill outputs (issue extraction, enhancement) are stable across days. Note content rarely changes enough to invalidate cache within a week.

---

## Ghost Text Service (`services/ghost_text.py`)

**SLA**: <2.5s total (500ms typing pause + <2s execution)

**Latency budget**:
```
Cache lookup:        <10ms
Key retrieval:        <5ms
Client pool lookup:   <1ms
API call (Haiku):   500-800ms network + inference
Cache write:          <5ms
Cost tracking:      background (async, non-blocking)
```

**Block-type-aware prompts**: Different system prompts for `codeBlock`, `heading`, `bulletList`, and default paragraph. Code blocks get code-completion rules; headings get title-case and brevity rules.

**Confidence heuristic**:
- `stop_reason == "max_tokens"` → 0.6 (truncated mid-completion)
- Otherwise → `min(0.9, len(suggestion)/100 + 0.5)` (length-based)

**Why Haiku (not Gemini Flash)?**: Same Anthropic billing account → single API key, simpler fallback chains. Haiku latency ≈ Flash with better instruction-following for constrained completions.

---

## Session Management (`session/session_manager.py`)

**Dual-storage architecture**:

| Storage | TTL | Purpose |
|---------|-----|---------|
| Redis | 30-min sliding | Hot path: <1ms session lookup during active conversation |
| PostgreSQL | 24h (optional) | Durable recovery after Redis flush or deployment restart |

**Sliding TTL**: Every `update_session()` call resets `expires_at = now + 30min`. A user actively in conversation never expires mid-session.

**Session identity**: Keyed by `(user_id, agent_name, context_id)`. One session per user per agent per context entity (note/issue/project).

**Session resume**: `get_active_session(user_id, agent_name, context_id)` checks Redis index → returns existing session with message history → conversation continues in place.

---

## Background Workers

### Digest Worker (`workers/digest_worker.py`)

Generates AI-powered workspace digests (daily summaries of activity, issues created, PRs merged). Triggered by pg_cron (Supabase Queues / pgmq, DD-069).

**Output**: Structured digest with sections: "Issues Created", "PRs Merged", "Key Decisions", "Blockers". Stored in PostgreSQL, surfaced via workspace notification.

### Memory Worker (`workers/memory_worker.py`)

Generates embeddings for notes and issues and upserts into pgvector (768-dim HNSW index, DD-070).

**Flow**: `note_updated` event → chunked content → Gemini gemini-embedding-001 → 768-dim vectors → `upsert INTO note_embeddings WHERE note_id=...`

**Why background?** Embedding generation takes 200-500ms per chunk. Running it synchronously on save would add 500ms+ to every note save. Background worker decouples embedding from write path.

---

## Cost Alerts (`alerts/cost_alerts.py`)

**Threshold defaults**:
- Daily: $10.00 per workspace
- Weekly: $50.00 per workspace
- Monthly: $200.00 per workspace

**Trigger**: Background job calls `check_cost_alerts()` on workspace activity. Returns list of alert messages if thresholds exceeded. Alerts emitted to workspace notification channel and logged.

**At 90%**: Warning alert (not hard stop). Workspace owner sees "AI budget 90% consumed" in settings.

---

## Telemetry (`telemetry.py`)

**Per-request metrics captured** via `track_ai_operation()` context manager:
- Provider, model, agent name
- Input/output token counts
- Estimated cost (USD)
- Duration (ms)
- Success/failure + error type
- Cache hit/miss

**Optional Prometheus integration**: If `prometheus_client` installed, exposes:
- `ai_requests_total` (counter, by agent + status)
- `ai_tokens_total` (counter, by agent + direction)
- `ai_latency_seconds` (histogram, by agent)
- `ai_circuit_breaker_state` (gauge, by provider)
- `ai_active_sessions` (gauge, by agent)

---

## Implicit Features

| Feature | Mechanism | File |
|---------|-----------|------|
| Per-provider CB singletons | `CircuitBreaker.get_or_create()` | `circuit_breaker.py` |
| CB auto-selects fallback provider | `is_provider_healthy()` check in selector | `provider_selector.py` |
| 90% discount on cached tokens | Pricing table + cache flag | `cost_tracker.py` |
| Ghost text cache 1h | Redis TTL on prompt hash | `ghost_text.py` |
| Block-type-aware completions | System prompt switched by block type | `ghost_text.py` |
| Non-blocking cost tracking | `asyncio.create_task()` (fire-and-forget) | `ghost_text.py` |
| SHA-256 hashed pool keys | Security: plaintext never in dict keys | `anthropic_client_pool.py` |
| Sliding session TTL | `expires_at = now + 30min` on every update | `session_manager.py` |
| Embedding generation decoupled | Background worker, not in write path | `memory_worker.py` |
| Jitter on retry | ±30% random offset prevents thundering herd | `resilience.py` |

---

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| Task-based model routing (DD-011) | Match model capability to task complexity. Opus for PR review (deep analysis), Haiku for ghost text (speed), Sonnet for general tasks (cost). |
| Circuit breaker shared across users | One workspace's failures protect all workspaces from a degraded provider. |
| Dual-storage sessions (Redis + PG) | Redis for <1ms active session access; PostgreSQL for durable recovery without sticky sessions. |
| PBKDF2 600K iterations | OWASP 2023 recommendation for password-based key derivation. Slows brute force. |
| Ghost text cache 1h (not per-session) | Same note context + same prefix → same completion. Sharing cache across users and sessions is safe and saves cost. |
| Background embedding workers | Decouples write latency from embedding cost. Users don't wait for vector generation on save. |
| Graceful degradation (fail-open) | AI features are enhancements, not core CRUD. Degrading them keeps the app usable during AI outages. |

---

## Files Reference

| File | Lines | Purpose |
|------|-------|---------|
| `providers/provider_selector.py` | ~463 | Task → model routing, CB integration |
| `providers/key_validator.py` | ~157 | BYOK key format + auth validation |
| `circuit_breaker.py` | ~320 | 3-state CB per provider |
| `degradation.py` | ~386 | Feature-level graceful degradation |
| `infrastructure/resilience.py` | ~490 | Retry + exponential backoff + streaming |
| `utils/retry.py` | ~337 | Retry utilities + context manager |
| `infrastructure/anthropic_client_pool.py` | ~73 | Connection pooling (BYOK isolation) |
| `infrastructure/cost_tracker.py` | ~656 | Token cost calc + persistence + analytics |
| `infrastructure/key_storage.py` | ~386 | BYOK AES-256 encryption/decryption |
| `infrastructure/cache.py` | ~346 | Redis-based AI response cache (7d TTL) |
| `infrastructure/approval.py` | ~521 | Approval request persistence + resolution |
| `infrastructure/rate_limiter.py` | ~156 | Sliding window rate limiter |
| `services/ghost_text.py` | ~395 | Haiku-powered <2.5s ghost text |
| `session/session_manager.py` | ~452 | Redis + PG dual-storage session lifecycle |
| `session/session_models.py` | ~100 | `AISession`, `AIMessage` Pydantic models |
| `workers/digest_worker.py` | ~200 | Daily workspace digest generation |
| `workers/memory_worker.py` | ~150 | Note/issue embedding generation |
| `alerts/cost_alerts.py` | ~214 | Daily/weekly cost threshold alerts |
| `analytics/token_analysis.py` | ~261 | Per-agent token efficiency metrics |
| `telemetry.py` | ~561 | Prometheus + structured observability |
| `config/token_limits.py` | ~60 | Hard token limits per prompt layer |

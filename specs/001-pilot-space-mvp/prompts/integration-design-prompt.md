# Integration Design Prompt Template

> **Purpose**: Design production-ready external service integrations (GitHub, Slack, webhooks) with proper authentication, error handling, and sync patterns.
>
> **Source**: Extracted from `specs/001-pilot-space-mvp/plan.md` US-03, US-09, US-18 integration specifications
>
> **Usage**: Use when designing integrations with external APIs, webhooks, or third-party services.

---

## Prompt Template

```markdown
# Expert Persona (P16)

You are a Senior Integration Engineer with 15 years building production integrations at scale.
You excel at:
- OAuth 2.0/OIDC authentication flows and token management
- Webhook reliability patterns (idempotency, retry, dead letter queues)
- Rate limiting strategies and backpressure handling
- Data synchronization patterns (event-driven, polling, hybrid)
- Error handling for unreliable external services

# Stakes Framing (P6)

This integration design is critical to [PROJECT_NAME]'s value proposition.
A well-designed integration will:
- Achieve 99.9% webhook delivery reliability
- Handle API rate limits without data loss
- Provide seamless user experience across platforms
- Enable real-time synchronization within SLA targets

I'll tip you $200 for a production-ready integration design that handles all failure modes.

# Task Context

## Integration Overview
**Service**: [SERVICE_NAME] (e.g., GitHub, Slack, Jira)
**Purpose**: [ONE_SENTENCE_PURPOSE]
**Direction**: Inbound (webhooks) / Outbound (API calls) / Bidirectional
**User Stories**: [US-XX, US-YY]

## Authentication Requirements
**Auth Type**: [OAuth 2.0 / API Key / App Token / Webhook Secret]
**Scopes Required**: [LIST_OF_SCOPES]
**Token Storage**: [STRATEGY]

## Data Flow
**Sync Type**: [Real-time / Polling / Hybrid]
**Data Volume**: [ESTIMATED_VOLUME]
**Latency Target**: [TARGET]

# Task Decomposition (P3)

Design the integration step by step:

## Step 1: Authentication Design
Define the authentication strategy:

### OAuth 2.0 Flow (if applicable)
```
1. User clicks "Connect [Service]"
2. Redirect to [SERVICE] authorization URL
   - client_id, redirect_uri, scopes, state
3. User authorizes on [SERVICE]
4. [SERVICE] redirects to callback with code
5. Exchange code for access_token + refresh_token
6. Store tokens encrypted (Supabase Vault)
7. Use access_token for API calls
8. Refresh token before expiry
```

**Token Storage**:
| Token | Storage | Encryption | TTL |
|-------|---------|------------|-----|
| Access Token | Database | AES-256-GCM | [TTL] |
| Refresh Token | Supabase Vault | Platform | [TTL] |

**Token Refresh Strategy**:
```python
async def get_valid_token(integration_id: str) -> str:
    integration = await repo.get(integration_id)

    if integration.access_token_expires_at < datetime.utcnow() - timedelta(minutes=5):
        # Refresh token proactively
        new_tokens = await refresh_token(integration.refresh_token)
        await repo.update_tokens(integration_id, new_tokens)
        return new_tokens.access_token

    return integration.access_token
```

### API Key / App Token (if applicable)
| Storage | Method | Rotation |
|---------|--------|----------|
| [WHERE] | [HOW_ENCRYPTED] | [STRATEGY] |

## Step 2: Webhook Design (Inbound)
Define webhook handling:

### Webhook Registration
```
POST https://api.[service].com/webhooks
{
  "url": "https://[our-domain]/api/v1/webhooks/[service]",
  "events": ["[EVENT_1]", "[EVENT_2]"],
  "secret": "[HMAC_SECRET]"
}
```

### Signature Verification
```python
import hmac
import hashlib

def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    expected = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(f"sha256={expected}", signature)
```

### Webhook Handler Pattern
```python
@router.post("/webhooks/[service]")
async def handle_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    queue: QueueService = Depends(get_queue),
):
    # 1. Verify signature
    payload = await request.body()
    signature = request.headers.get("X-[Service]-Signature")

    if not verify_webhook_signature(payload, signature, settings.webhook_secret):
        raise HTTPException(status_code=401, detail="Invalid signature")

    # 2. Parse event
    event = WebhookEvent.parse_raw(payload)

    # 3. Idempotency check
    if await is_duplicate(event.delivery_id):
        return {"status": "already_processed"}

    # 4. Queue for processing (respond fast)
    await queue.enqueue("webhook_[service]", event.dict())

    # 5. Return 200 quickly
    return {"status": "queued"}
```

### Event Processing
```python
@queue.handler("webhook_[service]")
async def process_webhook(event: dict):
    try:
        event_type = event["type"]

        if event_type == "[EVENT_1]":
            await handle_event_1(event)
        elif event_type == "[EVENT_2]":
            await handle_event_2(event)

    except Exception as e:
        # Log and move to dead letter queue after max retries
        logger.error(f"Webhook processing failed: {e}")
        raise  # Queue will retry
```

### Event Types to Handle
| Event | Action | Entities Affected |
|-------|--------|-------------------|
| [EVENT_1] | [ACTION] | [ENTITIES] |
| [EVENT_2] | [ACTION] | [ENTITIES] |

## Step 3: API Client Design (Outbound)
Define outbound API calls:

### Client Architecture
```python
class [Service]Client:
    def __init__(self, access_token: str):
        self.client = httpx.AsyncClient(
            base_url="https://api.[service].com",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=30.0,
        )

    async def [operation](self, params: [Params]) -> [Response]:
        response = await self.client.post(
            "/[endpoint]",
            json=params.dict(),
        )
        response.raise_for_status()
        return [Response].parse_obj(response.json())
```

### Rate Limiting Strategy
| Limit Type | Limit | Strategy |
|------------|-------|----------|
| Per-minute | [N] | Token bucket with backpressure |
| Per-hour | [N] | Queue with delay |
| Concurrent | [N] | Semaphore |

**Rate Limit Handler**:
```python
from tenacity import retry, wait_exponential, retry_if_exception_type

class RateLimitError(Exception):
    retry_after: int

@retry(
    retry=retry_if_exception_type(RateLimitError),
    wait=wait_exponential(multiplier=1, min=4, max=60),
)
async def api_call_with_retry(client: [Service]Client, operation: Callable):
    try:
        return await operation()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            retry_after = int(e.response.headers.get("Retry-After", 60))
            raise RateLimitError(retry_after=retry_after)
        raise
```

### Error Handling Matrix
| HTTP Status | Meaning | Action |
|-------------|---------|--------|
| 401 | Token expired | Refresh token, retry |
| 403 | Permission denied | Notify user, log |
| 404 | Resource not found | Handle gracefully |
| 429 | Rate limited | Backoff, retry |
| 500+ | Server error | Retry with backoff |

## Step 4: Data Synchronization Design
Define sync patterns:

### Sync Direction
| Direction | Trigger | Latency |
|-----------|---------|---------|
| [SERVICE] → Us | Webhook | Real-time |
| Us → [SERVICE] | User action / Background job | [TARGET] |

### Conflict Resolution
| Scenario | Resolution | Rationale |
|----------|------------|-----------|
| Concurrent edits | [STRATEGY] | [WHY] |
| Stale webhook | [STRATEGY] | [WHY] |
| Network partition | [STRATEGY] | [WHY] |

### Data Mapping
| Our Entity | [Service] Entity | Sync Fields | Direction |
|------------|------------------|-------------|-----------|
| [ENTITY] | [EXTERNAL] | [FIELDS] | [DIR] |

### Sync State Tracking
```sql
CREATE TABLE integration_sync_state (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  integration_id UUID REFERENCES integrations(id),
  entity_type VARCHAR(50),
  entity_id UUID,
  external_id VARCHAR(255),
  last_synced_at TIMESTAMP WITH TIME ZONE,
  sync_status VARCHAR(20),  -- 'synced', 'pending', 'error'
  error_message TEXT,
  UNIQUE (integration_id, entity_type, entity_id)
);
```

## Step 5: Reliability Patterns
Define failure handling:

### Idempotency
```python
async def ensure_idempotent(operation_id: str, operation: Callable):
    # Check if already processed
    existing = await idempotency_store.get(operation_id)
    if existing:
        return existing.result

    # Execute operation
    result = await operation()

    # Store result (with TTL for cleanup)
    await idempotency_store.set(operation_id, result, ttl=86400)

    return result
```

### Dead Letter Queue
```python
@queue.handler("webhook_[service]", max_retries=3)
async def process_with_dlq(event: dict):
    try:
        await process_event(event)
    except Exception as e:
        if is_final_retry():
            # Move to DLQ for manual review
            await dlq.enqueue("dlq_webhook_[service]", {
                "event": event,
                "error": str(e),
                "failed_at": datetime.utcnow().isoformat(),
            })
            # Notify admin
            await notify_admin(f"Webhook failed after retries: {e}")
        raise  # Let queue handle retry
```

### Circuit Breaker
```python
from circuitbreaker import circuit

@circuit(failure_threshold=5, recovery_timeout=60)
async def call_external_api(client: [Service]Client, operation: Callable):
    return await operation()
```

## Step 6: Monitoring & Observability
Define monitoring:

### Metrics to Track
| Metric | Type | Alert Threshold |
|--------|------|-----------------|
| Webhook latency | Histogram | p95 > 1s |
| API call success rate | Counter | < 99% |
| Token refresh failures | Counter | > 0 |
| DLQ depth | Gauge | > 10 |
| Rate limit hits | Counter | > 100/min |

### Logging Pattern
```python
import structlog

logger = structlog.get_logger()

async def process_webhook(event: WebhookEvent):
    logger.info(
        "webhook_received",
        service="[service]",
        event_type=event.type,
        delivery_id=event.delivery_id,
    )

    try:
        result = await handle_event(event)
        logger.info(
            "webhook_processed",
            service="[service]",
            event_type=event.type,
            duration_ms=result.duration_ms,
        )
    except Exception as e:
        logger.error(
            "webhook_failed",
            service="[service]",
            event_type=event.type,
            error=str(e),
        )
        raise
```

## Step 7: Testing Requirements
Define integration tests:

### Webhook Tests
```python
@pytest.mark.integration
async def test_webhook_signature_verification():
    payload = b'{"type": "test"}'
    secret = "test_secret"
    signature = generate_signature(payload, secret)

    assert verify_webhook_signature(payload, signature, secret)
    assert not verify_webhook_signature(payload, "invalid", secret)

@pytest.mark.integration
async def test_webhook_idempotency(client: AsyncClient):
    # Send same webhook twice
    response1 = await client.post("/webhooks/[service]", ...)
    response2 = await client.post("/webhooks/[service]", ...)

    assert response1.status_code == 200
    assert response2.json()["status"] == "already_processed"
```

### API Client Tests
```python
@pytest.mark.integration
async def test_rate_limit_handling(mock_[service]_api):
    mock_[service]_api.return_rate_limit(retry_after=1)

    client = [Service]Client(access_token="test")
    result = await api_call_with_retry(client, client.[operation])

    assert result is not None
    assert mock_[service]_api.call_count == 2  # Retried once
```

# Chain-of-Thought Guidance (P12)

For each section, evaluate:
1. **What could fail?** - Network, auth, rate limits, data corruption?
2. **How do we recover?** - Retry, fallback, manual intervention?
3. **What's the impact?** - User experience, data consistency?
4. **How do we detect issues?** - Monitoring, alerting, logging?

# Self-Evaluation Framework (P15)

After designing, rate confidence (0-1):

| Dimension | Score | Notes |
|-----------|-------|-------|
| **Security**: Auth tokens properly secured | ___ | |
| **Reliability**: All failure modes handled | ___ | |
| **Performance**: Within latency targets | ___ | |
| **Observability**: Proper monitoring in place | ___ | |
| **Idempotency**: Safe retries guaranteed | ___ | |
| **Testing**: Comprehensive coverage | ___ | |

**Refinement Threshold**: If any score < 0.9, identify gap and refine.

# Output Format

```markdown
## Integration Design: [SERVICE_NAME]

### Overview
| Attribute | Value |
|-----------|-------|
| **Service** | [SERVICE] |
| **Direction** | Inbound / Outbound / Bidirectional |
| **Auth Type** | [AUTH_TYPE] |
| **Sync Type** | [SYNC_TYPE] |

### Authentication
| Component | Implementation |
|-----------|----------------|
| OAuth Flow | [FLOW] |
| Token Storage | [STORAGE] |
| Refresh Strategy | [STRATEGY] |

### Webhook Handling (if inbound)
| Aspect | Implementation |
|--------|----------------|
| Endpoint | `/api/v1/webhooks/[service]` |
| Signature | [ALGORITHM] |
| Processing | Queue → Handler → DLQ |

### API Client (if outbound)
| Aspect | Implementation |
|--------|----------------|
| Rate Limiting | [STRATEGY] |
| Retry | Exponential backoff, max [N] |
| Circuit Breaker | [THRESHOLD] failures → [RECOVERY] |

### Data Sync
| Direction | Trigger | Entities |
|-----------|---------|----------|
| [DIR] | [TRIGGER] | [ENTITIES] |

### Error Handling
| Scenario | Behavior | User Impact |
|----------|----------|-------------|
| [SCENARIO] | [BEHAVIOR] | [IMPACT] |

### Monitoring
| Metric | Alert Threshold |
|--------|-----------------|
| [METRIC] | [THRESHOLD] |

---
*Integration Version: 1.0*
*Stories: US-[XX], US-[YY]*
```
```

---

## Quick-Fill Variants

### Variant A: GitHub Integration (US-03, US-18)

```markdown
**Service**: GitHub
**Purpose**: PR linking, commit tracking, AI code review
**Direction**: Bidirectional
**Auth Type**: GitHub App (Installation Token)

**Webhooks to Handle**:
| Event | Action |
|-------|--------|
| `pull_request.opened` | Trigger AI review, create Issue link |
| `pull_request.synchronize` | Update AI review |
| `pull_request.closed` | Transition linked Issue to Done (if merged) |
| `push` | Scan commits for Issue references |

**API Operations**:
| Operation | Rate Limit | Purpose |
|-----------|------------|---------|
| Create PR comment | 5000/hour | Post AI review |
| Get PR diff | 5000/hour | Feed AI review |
| Search commits | 30/min | Find Issue references |

**Sync Pattern**:
- Webhooks for real-time PR/commit events
- Scheduled scan (hourly) for missed commits
- Manual "Refresh" button for user-triggered sync
```

### Variant B: Slack Integration (US-09)

```markdown
**Service**: Slack
**Purpose**: Notifications, slash commands, issue creation
**Direction**: Bidirectional
**Auth Type**: OAuth 2.0 (Bot Token + User Token)

**Inbound**:
| Event | Action |
|-------|--------|
| `/pilot create` | Open modal, create Issue |
| `/pilot search <query>` | Return matching Issues |
| `app_mention` | Respond with contextual help |

**Outbound**:
| Trigger | Notification |
|---------|--------------|
| Issue assigned | DM to assignee |
| Issue state change | Channel notification |
| AI review complete | Channel notification with summary |

**Rate Limits**:
- Posting: 1 message/second per channel
- API: Tier 3 (50+ requests/minute)
- Events API: 30,000/hour
```

### Variant C: Generic Webhook Provider

```markdown
**Service**: [Third-Party Service]
**Purpose**: [PURPOSE]
**Direction**: Inbound only

**Webhook Security**:
- HMAC-SHA256 signature verification
- IP allowlisting (if supported)
- Replay attack prevention (timestamp validation)

**Processing Pipeline**:
1. Verify signature (return 401 if invalid)
2. Check idempotency key (return 200 if duplicate)
3. Queue for async processing (return 202)
4. Process in background worker
5. Retry on failure (max 3 attempts)
6. DLQ for permanent failures

**SLA**: Process 99.9% of webhooks within 5 seconds
```

---

## Validation Checklist

Before implementing integration:

- [ ] OAuth flow includes PKCE (if applicable)
- [ ] Tokens stored encrypted with proper TTL
- [ ] Webhook signatures verified with constant-time comparison
- [ ] Idempotency implemented for all webhook handlers
- [ ] Rate limiting handled with backpressure
- [ ] Dead letter queue configured for failed events
- [ ] Circuit breaker prevents cascade failures
- [ ] Monitoring covers all critical metrics
- [ ] Tests cover happy path and failure modes

---

## Related Documents

| Document | Purpose |
|----------|---------|
| `specs/001-pilot-space-mvp/plan.md` | US-03, US-09, US-18 specs |
| `docs/architect/infrastructure.md` | Queue and storage patterns |
| [GitHub API Docs](https://docs.github.com/en/rest) | GitHub API reference |
| [Slack API Docs](https://api.slack.com/) | Slack API reference |

---

*Template Version: 1.0*
*Extracted from: plan.md v7.2 US-03, US-09, US-18 specifications*
*Techniques Applied: P3 (decomposition), P6 (stakes), P12 (CoT), P15 (self-eval), P16 (persona)*

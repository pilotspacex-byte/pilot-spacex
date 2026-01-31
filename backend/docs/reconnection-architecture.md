# Conversation Reconnection Architecture

## Problem Statement

Users may navigate away from conversations while AI is processing, then return expecting to see:
- Completed responses
- Partial responses (if still processing)
- Pending approvals
- Conversation history

## Solution: Multi-Layer Reconnection Strategy

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    User Navigation Scenarios                            │
├─────────────────────────────────────────────────────────────────────────┤
│  1. User sends message → navigates to homepage → returns to conversation│
│  2. Browser refresh while AI is responding                              │
│  3. User closes tab → returns hours later                               │
│  4. Network disconnect → reconnects                                     │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Detailed Flow

### Scenario 1: Navigate Away While Processing

```
Timeline:

T+0s    User: "Explain this code"
        ↓
        Frontend: POST /messages → {job_id: "abc123"}
        ↓
        Frontend: Connect SSE stream
        ↓
        Worker: Starts processing, stores events in Redis

T+5s    User navigates to homepage (SSE connection closes)

T+8s    Worker still processing (unaware of disconnect)
        Worker stores events to Redis:
        - stream:events:abc123 → [event1, event2, event3...]
        - partial:response:abc123 → "The code uses async/await..."
        - stream:active:abc123 → "1"

T+15s   User returns to /conversations/{id}

        Frontend: GET /conversations/{id}/status
        ↓
        Backend: {
          active_job: {
            status: "PROCESSING",
            can_reconnect: true,
            stream_url: "/stream/abc123",
            partial_response: "The code uses async/await..."
          }
        }
        ↓
        Frontend: Shows partial response immediately
        ↓
        Frontend: GET /stream/abc123/events?after_event=0
        ↓
        Backend: Returns [event1, event2, event3] (missed during disconnect)
        ↓
        Frontend: Replays missed events
        ↓
        Frontend: Reconnects to SSE stream
        ↓
        Worker: Continues streaming events
        ↓
        Frontend: Receives new events in real-time

T+20s   Worker completes, sends message_stop
        ↓
        Frontend: Shows complete response
```

### Scenario 2: Job Completes During Absence

```
T+0s    User: "Generate docs"
        ↓
        Frontend: POST /messages → {job_id: "xyz789"}
        ↓
        User navigates away

T+5s    Worker completes job
        ↓
        Worker saves to conversation_turns table:
        - turn_id: "xyz789"
        - content: "# Documentation\n..."
        - completed_at: 2026-01-30T10:05:00Z

T+60s   User returns

        Frontend: GET /conversations/{id}/status
        ↓
        Backend: {
          active_job: {
            status: "COMPLETED",
            can_reconnect: false,
            response: "# Documentation\n..."
          }
        }
        ↓
        Frontend: Shows completed response immediately
        (No SSE reconnection needed)
```

### Scenario 3: Waiting for Approval

```
T+0s    User: "Update config.py with new API key"
        ↓
        Worker processes, encounters write_file tool
        ↓
        SDK hook triggers: on_tool_approval_required
        ↓
        Worker creates ApprovalRequest in DB (status=pending)
        ↓
        Worker publishes approval_required event
        ↓
        User sees approval UI

T+10s   User navigates away (approval still pending)

T+60s   User returns

        Frontend: GET /conversations/{id}/status
        ↓
        Backend: {
          active_job: {
            status: "WAITING_APPROVAL",
            pending_approval: {
              approval_id: "123",
              tool_name: "write_file",
              params: {...},
              risk_level: "high"
            }
          }
        }
        ↓
        Frontend: Shows approval UI immediately
        ↓
        User clicks "Approve"
        ↓
        Frontend: POST /approvals/123/decide {action: "approve"}
        ↓
        Worker receives approval via Redis pub/sub
        ↓
        Worker resumes SDK with approval decision
        ↓
        Conversation continues via SSE
```

---

## Data Storage for Reconnection

### Redis (Temporary, 5-10 minutes TTL)

| Key | Type | Purpose | TTL |
|-----|------|---------|-----|
| `stream:active:{job_id}` | STRING | Indicates job is still processing | 10m |
| `stream:events:{job_id}` | LIST | Ordered list of all events | 5m |
| `partial:response:{job_id}` | STRING | Accumulated text response | 10m |
| `stream:active:{job_id}` | STRING | Worker heartbeat | 10m |

### PostgreSQL (Persistent)

| Table | Purpose |
|-------|---------|
| `agent_sessions` | Session lifecycle (ACTIVE, COMPLETED, etc.) |
| `conversation_turns` | Persistent message history |
| `approval_requests` | Pending approvals |

---

## Frontend State Management

### Local Storage

```typescript
// Store last received event index
localStorage.setItem(`last_event_${jobId}`, String(eventIndex));

// On reconnect, fetch missed events
const lastEventIndex = localStorage.getItem(`last_event_${jobId}`) || '0';
const missedEvents = await fetch(`/stream/${jobId}/events?after_event=${lastEventIndex}`);
```

### Component Lifecycle

```typescript
useEffect(() => {
  // Mount: Fetch conversation status
  fetchConversationStatus();

  // Unmount: Close SSE, cleanup
  return () => {
    eventSource?.close();
  };
}, [conversationId]);

// Page visibility: Reconnect when tab becomes visible
useEffect(() => {
  const handleVisibilityChange = () => {
    if (document.visibilityState === 'visible') {
      fetchConversationStatus(); // Check for updates
    }
  };

  document.addEventListener('visibilitychange', handleVisibilityChange);
  return () => document.removeEventListener('visibilitychange', handleVisibilityChange);
}, []);
```

---

## SSE Reconnection Strategy

### Automatic Retry with Exponential Backoff

```typescript
let reconnectAttempts = 0;
const maxAttempts = 5;

const scheduleReconnect = (streamUrl: string) => {
  reconnectAttempts += 1;

  if (reconnectAttempts > maxAttempts) {
    showError('Unable to reconnect. Please refresh the page.');
    return;
  }

  // Exponential backoff: 1s, 2s, 4s, 8s, 16s
  const delay = Math.min(1000 * 2 ** (reconnectAttempts - 1), 16000);

  setTimeout(() => {
    connectSSE(streamUrl);
  }, delay);
};

eventSource.onerror = (err) => {
  console.error('SSE error:', err);
  eventSource.close();
  scheduleReconnect(streamUrl);
};

// Reset attempts on successful event
eventSource.onmessage = () => {
  reconnectAttempts = 0; // Success! Reset counter
};
```

---

## Edge Cases Handled

| Edge Case | Solution |
|-----------|----------|
| **User navigates while event is mid-stream** | Worker continues processing; partial response stored in Redis |
| **SSE connection drops during approval** | Approval state persisted in DB; frontend refetches on reconnect |
| **Worker crashes mid-processing** | pgmq visibility timeout ensures message reprocessed; partial response recoverable |
| **User opens conversation in multiple tabs** | Each tab has own SSE connection; worker broadcasts to all via Redis pub/sub |
| **Browser refresh during streaming** | Frontend fetches missed events from Redis, reconnects to SSE |
| **User returns after job expired (> 10min)** | Events purged from Redis, but response persisted in DB; show completed result |
| **Network flaps (multiple disconnects)** | Exponential backoff prevents thundering herd; max 5 retries |

---

## Performance Considerations

### Redis Memory Usage

```
Average event size: 200 bytes
Avg events per conversation: 50
Avg concurrent conversations: 100

Redis usage = 200 bytes × 50 events × 100 jobs = ~1 MB

With TTL cleanup, sustained load easily under 10 MB.
```

### Database Load

- Status check on reconnect: 1 query (indexed by conversation_id)
- Fetch missed events: Redis read (very fast)
- No DB writes during reconnection

### Network Bandwidth

- Missed events catchup: 1 HTTP request (~10 KB typical)
- SSE reconnection: Standard EventSource handshake
- Total: < 20 KB per reconnection

---

## Testing Strategy

### Unit Tests

```python
# test_reconnection.py

async def test_partial_response_stored():
    """Verify partial responses stored in Redis."""
    worker = ConversationWorker(...)
    job_id = uuid4()

    await worker.start_stream_session(job_id)
    await worker._append_partial_response(job_id, "Hello ")
    await worker._append_partial_response(job_id, "world")

    partial = await redis.get(f"partial:response:{job_id}")
    assert partial.decode() == "Hello world"

async def test_events_stored_in_order():
    """Verify events stored sequentially."""
    worker = ConversationWorker(...)
    job_id = uuid4()

    await worker.start_stream_session(job_id)

    for i, event in enumerate([event1, event2, event3]):
        await worker.store_stream_event(job_id, event, i)

    events = await redis.lrange(f"stream:events:{job_id}", 0, -1)
    assert len(events) == 3
    assert json.loads(events[0])["index"] == 0
```

### Integration Tests

```typescript
// test_reconnection.spec.ts

test('should fetch missed events after disconnect', async () => {
  // Start conversation
  const { jobId } = await sendMessage('Hello');

  // Simulate disconnect (close SSE)
  closeSSE();

  // Wait for some events to be generated
  await sleep(2000);

  // Reconnect
  const missedEvents = await fetchMissedEvents(jobId, 0);

  expect(missedEvents.length).toBeGreaterThan(0);
  expect(missedEvents[0].type).toBe('message_start');
});

test('should show partial response on reconnect', async () => {
  const { conversationId } = await createConversation();
  await sendMessage('Explain async/await');

  // Navigate away
  navigateTo('/');

  // Return to conversation
  navigateTo(`/conversations/${conversationId}`);

  // Should see partial response immediately
  const partialText = await screen.findByText(/async\/await/i);
  expect(partialText).toBeInTheDocument();
});
```

### Load Tests

```python
# Simulate 100 users navigating away and returning
async def test_concurrent_reconnections():
    users = [simulate_user(i) for i in range(100)]

    async def simulate_user(user_id):
        # Send message
        job_id = await send_message(f"user-{user_id}", "Hello")

        # Disconnect after 2s
        await asyncio.sleep(2)
        close_connection(job_id)

        # Wait random time (simulate navigation)
        await asyncio.sleep(random.uniform(1, 10))

        # Reconnect
        status = await get_conversation_status(job_id)
        assert status["active_job"] is not None

        # Fetch missed events
        events = await get_missed_events(job_id, 0)

        # Reconnect SSE
        await connect_sse(job_id)

    await asyncio.gather(*users)

    # Verify no events lost, all users reconnected successfully
```

---

## Monitoring & Alerts

### Key Metrics

```python
# Prometheus metrics

reconnection_attempts = Counter(
    'ai_reconnection_attempts_total',
    'Total SSE reconnection attempts',
    ['status']  # 'success', 'failed'
)

missed_events_fetched = Histogram(
    'ai_missed_events_count',
    'Number of events fetched on reconnect'
)

partial_response_size = Histogram(
    'ai_partial_response_bytes',
    'Size of partial response on reconnect'
)

reconnection_latency = Histogram(
    'ai_reconnection_duration_seconds',
    'Time from status check to SSE reconnection'
)
```

### Alerts

```yaml
- alert: HighReconnectionFailureRate
  expr: rate(ai_reconnection_attempts_total{status="failed"}[5m]) > 0.1
  for: 3m
  labels:
    severity: warning
  annotations:
    summary: "High rate of failed SSE reconnections"

- alert: LargePartialResponses
  expr: ai_partial_response_bytes > 100000  # 100 KB
  for: 5m
  labels:
    severity: info
  annotations:
    summary: "Large partial responses being stored in Redis"
```

---

## Summary

This reconnection architecture provides:

✅ **Seamless UX** - Users can navigate freely without losing context
✅ **No Data Loss** - All events stored in Redis for 5-10 minutes
✅ **Automatic Recovery** - SSE reconnects with exponential backoff
✅ **Instant Feedback** - Partial responses shown immediately on return
✅ **Approval Continuity** - Pending approvals survive navigation
✅ **Multi-Tab Support** - Each tab has independent SSE connection
✅ **Network Resilience** - Handles flaky connections gracefully

**Performance:**
- < 100ms status check latency
- < 1 MB Redis memory per 100 active jobs
- < 20 KB bandwidth per reconnection
- Auto-cleanup via TTL (no manual intervention)

**Next Steps:**
1. Implement backend reconnection endpoints ✅
2. Implement worker reconnection mixin ✅
3. Implement frontend reconnection hook ✅
4. Add monitoring dashboards
5. Write integration tests
6. Load test with 100 concurrent reconnections

# Worker Event Processing Pipeline - Sequence Diagrams Summary

**Location:** `backend/docs/plan-conversational-agent-v2.md` - Section **2.3.7**

This document summarizes the 6 comprehensive sequence diagrams added to visualize the worker event processing pipeline.

---

## Diagrams Overview

| # | Diagram | Participants | Key Events | Use Case |
|---|---------|-------------|------------|----------|
| 1 | Normal Message Processing | 9 systems | 12 steps | Happy path from user message to database persistence |
| 2 | Approval Workflow | 7 systems | Hook trigger → User decision → Resume | Human-in-the-loop for critical actions |
| 3 | Error Handling & Retry | 7 systems | 3 retries → Circuit breaker → DLQ | Fault tolerance and recovery |
| 4 | Conversation Cancellation | 6 systems | Cancel request → SDK graceful shutdown | User-initiated interruption |
| 5 | Reconnection Flow | 7 systems | Navigate away → Return → Catchup → Resume | Seamless reconnection after disconnect |
| 6 | Multi-Worker Concurrency | 8 systems | 2 workers, 3 messages, lock conflict | Concurrent processing with distributed locks |

---

## Diagram 1: Normal Message Processing Flow

**Purpose:** Illustrates the complete happy path from user message submission to database persistence.

**Key Steps:**
1. User submits message → FastAPI creates DB record and enqueues
2. User connects to SSE stream (EventSource)
3. Worker picks up message from pgmq (vt=300s)
4. Worker acquires Redis distributed lock
5. SessionManager gets/creates ClaudeSDKClient (resume if exists)
6. Worker initializes reconnection session (Redis storage)
7. Worker publishes `message_start` event to SSE
8. **Main streaming loop:**
   - For each SDK event:
     - Transform SDK format → SSE format
     - Store event in Redis (for reconnection)
     - Append to partial response (for instant display)
     - Publish to Redis pub/sub → FastAPI → User
     - Check cancellation flag
     - Extend pgmq visibility timeout every 2 minutes
9. SDK sends `stop` event → Worker exits loop
10. Worker persists ConversationTurn to PostgreSQL (with token usage, processing time)
11. Worker publishes `message_stop` event
12. Worker cleans up: deletes pgmq message, releases lock, expires Redis keys, updates metrics

**Participants:**
- User, FastAPI, Supabase pgmq, ConversationWorker
- Redis Lock, SessionManager, ClaudeSDKClient
- Redis Pub/Sub, PostgreSQL

**Visual Highlights:**
- Shows Redis operations for reconnection support
- Demonstrates visibility timeout extension for long operations
- Illustrates SSE pub/sub architecture

---

## Diagram 2: Approval Workflow

**Purpose:** Shows how the worker pauses for user approval of critical tool use.

**Key Steps:**
1. Normal streaming in progress
2. SDK encounters tool requiring approval (e.g., `write_file`)
3. SDK triggers hook: `on_tool_approval_required(tool_name, params)`
4. Hook creates `ApprovalRequest` in database (status=pending, risk_level=high)
5. Hook publishes `approval_required` event to SSE → User sees approval UI
6. Worker enters approval wait loop:
   - Extends pgmq visibility every 30s
   - Checks for timeout (5 minutes default)
   - If timeout → auto-reject and continue
7. User makes decision: POST `/approvals/{id}/decide`
8. FastAPI updates database, publishes decision to Redis
9. Hook receives decision, returns `ApprovalDecision` to SDK
10. SDK resumes execution with approved/rejected action
11. Hook publishes `approval_received` event to SSE
12. Streaming continues normally

**Participants:**
- User, FastAPI, Worker, ClaudeSDKClient
- ApprovalHook, Redis, PostgreSQL

**Visual Highlights:**
- Shows non-blocking async wait for user decision
- Demonstrates timeout handling (auto-reject after 5 min)
- Illustrates hook integration with SDK

---

## Diagram 3: Error Handling & Retry Flow

**Purpose:** Demonstrates resilience through retry logic, circuit breaker, and dead letter queue.

**Key Steps:**
1. Worker starts streaming, SDK calls Claude API
2. **Attempt 1:** Network timeout → Retry with 1s backoff
3. **Attempt 2:** Rate limit (429) → Retry with 2s backoff
4. **Attempt 3:** Service unavailable (503) → Retry with 4s backoff
5. **Attempt 4:** Still unavailable (503) → Max retries reached
6. Circuit breaker checks failure count:
   - If 5 consecutive failures → Open circuit (stop calling API for 60s)
   - Alert on-call engineer
7. Worker moves message to Dead Letter Queue (DLQ)
8. Worker sends alert: "Message in DLQ after 3 retries"
9. Worker updates conversation_turn status to 'failed'
10. **Recovery:** After 60s, circuit enters half-open state
11. Next message arrives → Circuit allows one test request
12. API responds successfully → Circuit closes, normal operation resumes

**Participants:**
- Worker, ClaudeSDKClient, Claude API
- Supabase pgmq, CircuitBreaker, Dead Letter Queue, Alerting System

**Visual Highlights:**
- Shows exponential backoff progression (1s → 2s → 4s)
- Demonstrates circuit breaker states (closed → open → half-open → closed)
- Illustrates DLQ pattern for unrecoverable errors

---

## Diagram 4: Conversation Cancellation Flow

**Purpose:** Shows graceful cancellation when user clicks "Stop".

**Key Steps:**
1. Streaming in progress (worker publishing events to SSE)
2. User clicks "Stop" button in UI
3. Frontend sends: DELETE `/conversations/{id}/cancel`
4. FastAPI sets cancellation flag: `SETEX cancel:{job_id} 300 "true"`
5. FastAPI responds to user: `{status: "cancelling"}`
6. Worker checks cancel flag on every event in streaming loop
7. Worker detects cancellation: `GET cancel:{job_id}` → "true"
8. Worker breaks out of streaming loop
9. Worker calls `SDK.cancel()` → Graceful shutdown
10. Worker publishes `cancelled` event with partial response
11. User's SSE stream closes
12. Worker saves partial results to database (status=cancelled)
13. Worker archives pgmq message (makes visible for potential retry)
14. Worker cleans up: releases lock, deletes cancel flag, expires Redis keys
15. Worker updates metrics: `cancellation_count.inc()`

**Participants:**
- User, FastAPI, Redis, Worker, ClaudeSDKClient, Supabase pgmq

**Visual Highlights:**
- Shows cancellation flag check in streaming loop
- Demonstrates graceful SDK shutdown (preserves partial state)
- Illustrates `archive()` vs `delete()` for pgmq messages

---

## Diagram 5: Reconnection Flow

**Purpose:** Demonstrates seamless reconnection after user navigates away and returns.

**Key Steps:**
1. User sends message, streaming starts
2. Browser connects to SSE stream
3. Worker processes message, stores events in Redis for recovery
4. **User navigates away** → EventSource closes (worker unaware)
5. Worker continues processing, storing events in Redis (no subscribers)
6. **User returns** → Frontend requests: GET `/conversations/{id}/status`
7. FastAPI queries database and Redis:
   - `agent_sessions` → status=ACTIVE
   - `conversation_turns` → active turn with job_id
   - `stream:active:{job_id}` → exists (job still running)
   - `partial:response:{job_id}` → "The authentication flow..."
8. FastAPI responds with active_job status + partial_response
9. **Browser immediately displays partial response** to user (instant feedback)
10. Browser fetches missed events: GET `/stream/{job_id}/events?after_event={lastEventIndex}`
11. FastAPI returns events from Redis: `LRANGE stream:events:{job_id}`
12. **Browser replays missed events** in order, updating UI
13. Browser stores last event index in localStorage
14. **Browser reconnects to live SSE stream**
15. Worker still streaming → new events published → browser receives them
16. Stream completes, worker cleans up (with TTL on Redis keys)
17. **User sees complete conversation with no gaps!**

**Participants:**
- User, Browser, FastAPI, Redis, Worker
- ClaudeSDKClient, PostgreSQL

**Visual Highlights:**
- Shows Redis event storage for catchup (5-10 min TTL)
- Demonstrates partial response for instant display
- Illustrates localStorage for tracking last received event
- Shows seamless transition from catchup → live stream

---

## Diagram 6: Multi-Worker Concurrent Processing

**Purpose:** Illustrates how multiple workers process different conversations concurrently while preventing concurrent processing of the same conversation.

**Key Steps:**
1. User 1 sends message for conversation A
2. User 2 sends message for conversation B (different conversation)
3. Both messages enqueued to pgmq
4. **Worker 1** picks up msg1 (conv_id_A):
   - Acquires lock: `SET lock:conv_id_A worker1 NX` → OK
   - Starts streaming
5. **Worker 2** picks up msg2 (conv_id_B):
   - Acquires lock: `SET lock:conv_id_B worker2 NX` → OK
   - Starts streaming
6. **Both workers process concurrently** (different conversations)
7. Worker 1 completes first:
   - Deletes pgmq message
   - Releases lock: `DEL lock:conv_id_A`
8. Worker 2 still processing conv_id_B
9. User 2 sends follow-up message (same conv_id_B)
10. Worker 1 picks up msg3 (conv_id_B)
11. Worker 1 tries to acquire lock: `SET lock:conv_id_B worker1 NX` → **nil (lock exists!)**
12. **Lock acquisition failed!** (Worker 2 already processing this conversation)
13. Worker 1 archives message → Will be retried later
14. Worker 2 completes, releases lock
15. Worker 2 picks up msg3 (retry)
16. Worker 2 acquires lock successfully, resumes SDK session

**Participants:**
- User 1, User 2, FastAPI, Supabase pgmq
- Worker 1, Worker 2, Redis Lock
- SDK Session 1, SDK Session 2

**Visual Highlights:**
- Shows parallel processing of different conversations
- Demonstrates lock conflict resolution (archive + retry)
- Illustrates serialized processing per conversation_id
- Shows how locks prevent race conditions

---

## Key Insights from Diagrams

### 1. **Event Processing Pipeline**
```
pgmq → Lock → Session → Stream → Transform → Store → Publish → Persist → Cleanup
```

### 2. **Redis Usage Patterns**
- **Distributed Locks:** `SET lock:{conv_id} worker_pid EX 30 NX`
- **Pub/Sub:** `PUBLISH stream:{job_id} {event_json}`
- **Event Storage:** `RPUSH stream:events:{job_id} {event_json}` (TTL 5min)
- **Partial Response:** `APPEND partial:response:{job_id} {text}` (TTL 10min)
- **Cancellation Flag:** `SETEX cancel:{job_id} 300 "true"`

### 3. **Fault Tolerance Mechanisms**
- **Retry:** Exponential backoff (1s → 2s → 4s)
- **Circuit Breaker:** 5 failures → open circuit for 60s
- **Dead Letter Queue:** Move unrecoverable messages
- **Visibility Timeout:** Ensures message reprocessing on worker crash

### 4. **Human-in-the-Loop Pattern**
- **Non-blocking:** Worker can process other messages while waiting for approval
- **Timeout:** Auto-reject after 5 minutes if no user response
- **Risk-based:** Tool risk level determines approval requirement

### 5. **Reconnection Strategy**
- **Instant Feedback:** Show partial response immediately on return
- **Event Replay:** Fetch missed events from Redis
- **Seamless Transition:** Catchup → live stream with no gaps

### 6. **Concurrency Control**
- **Distributed Locks:** Prevent concurrent processing of same conversation
- **Lock TTL:** Auto-expires after 30s (prevents deadlock on crash)
- **Archive + Retry:** Failed lock acquisition → retry later

---

## Usage in Documentation

These diagrams serve multiple purposes:

1. **Onboarding:** Help new developers understand the system quickly
2. **Design Review:** Visual verification of architecture decisions
3. **Debugging:** Identify where issues might occur in the pipeline
4. **Communication:** Explain system behavior to stakeholders
5. **Testing:** Guide test scenario development

---

## Rendering the Diagrams

The diagrams use **Mermaid** syntax and can be rendered in:

- **GitHub/GitLab:** Automatically renders in markdown
- **VS Code:** Install "Markdown Preview Mermaid Support" extension
- **Documentation Sites:** Docusaurus, MkDocs, VitePress support Mermaid
- **Online:** https://mermaid.live/

---

## Next Steps

1. **Add Implementation Tests** based on these flows
2. **Create Monitoring Dashboards** with metrics from each step
3. **Build Debugging Tools** that visualize current state in pipeline
4. **Document Edge Cases** discovered during implementation
5. **Generate API Documentation** aligned with these flows

---

**Related Documents:**
- Main Plan: `backend/docs/plan-conversational-agent-v2.md`
- Reconnection Architecture: `backend/docs/reconnection-architecture.md`
- Worker Implementation: `backend/src/pilot_space/ai/workers/conversation_worker.py`

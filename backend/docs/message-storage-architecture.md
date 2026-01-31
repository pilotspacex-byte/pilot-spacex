# Conversation Message Storage Architecture

## Overview

Messages in the PilotSpace conversational AI system are stored using a **two-tier architecture**:
- **Redis** (temporary, 5-10 min): For real-time streaming and reconnection
- **PostgreSQL** (permanent): For conversation history and analytics

---

## 1. PostgreSQL Schema (Permanent Storage)

### conversation_turns Table

This is the **primary permanent storage** for all conversation messages.

```sql
CREATE TABLE conversation_turns (
    -- Primary Key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Relationships
    conversation_id UUID NOT NULL REFERENCES agent_sessions(conversation_id) ON DELETE CASCADE,
    job_id UUID NOT NULL UNIQUE,  -- Links to queue message and SSE stream

    -- Message Content
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,  -- Full message text

    -- Tool Usage (JSONB)
    tool_calls JSONB DEFAULT '[]',
    -- Example:
    -- [
    --   {
    --     "tool_name": "read_file",
    --     "params": {"path": "auth.py"},
    --     "result": "...file contents...",
    --     "status": "completed",
    --     "duration_ms": 450
    --   }
    -- ]

    -- Performance Metrics
    token_usage JSONB,
    -- Example:
    -- {
    --   "input_tokens": 450,
    --   "output_tokens": 320,
    --   "cache_read_tokens": 1200,
    --   "cache_creation_tokens": 0
    -- }
    processing_time_ms INTEGER,  -- Total time to generate response

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,  -- NULL while processing, set when done

    -- Vector Embedding (for semantic search & context pruning)
    message_embedding vector(1536),  -- OpenAI ada-002 dimension

    -- Indexes
    CONSTRAINT fk_conversation FOREIGN KEY (conversation_id)
        REFERENCES agent_sessions(conversation_id) ON DELETE CASCADE
);

-- Indexes for fast queries
CREATE INDEX idx_conversation_turns_conversation
    ON conversation_turns(conversation_id, created_at DESC);

CREATE INDEX idx_conversation_turns_job
    ON conversation_turns(job_id);

CREATE INDEX idx_conversation_turns_active
    ON conversation_turns(conversation_id, completed_at)
    WHERE completed_at IS NULL;  -- Partial index for active turns

-- Vector similarity search (for context pruning)
CREATE INDEX idx_conversation_turns_embedding
    ON conversation_turns
    USING ivfflat (message_embedding vector_cosine_ops)
    WITH (lists = 100);
```

### Example Records

**User Message:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "conversation_id": "660e8400-e29b-41d4-a716-446655440001",
  "job_id": "770e8400-e29b-41d4-a716-446655440002",
  "role": "user",
  "content": "Explain the authentication flow in auth.py",
  "tool_calls": [],
  "token_usage": null,
  "processing_time_ms": null,
  "created_at": "2026-01-30T10:00:00.123Z",
  "completed_at": "2026-01-30T10:00:00.123Z",
  "message_embedding": [0.123, -0.456, ...]
}
```

**Assistant Message:**
```json
{
  "id": "880e8400-e29b-41d4-a716-446655440003",
  "conversation_id": "660e8400-e29b-41d4-a716-446655440001",
  "job_id": "990e8400-e29b-41d4-a716-446655440004",
  "role": "assistant",
  "content": "The authentication flow in auth.py uses FastAPI's dependency injection system for managing JWT tokens and user sessions...",
  "tool_calls": [
    {
      "tool_name": "read_file",
      "params": {"path": "auth.py"},
      "result": "...file contents...",
      "status": "completed",
      "duration_ms": 450
    }
  ],
  "token_usage": {
    "input_tokens": 450,
    "output_tokens": 320,
    "cache_read_tokens": 1200,
    "cache_creation_tokens": 0
  },
  "processing_time_ms": 5420,
  "created_at": "2026-01-30T10:00:00.200Z",
  "completed_at": "2026-01-30T10:00:05.620Z",
  "message_embedding": [0.789, -0.234, ...]
}
```

---

## 2. Redis Storage (Temporary - For Streaming & Reconnection)

Redis stores **transient data** during message processing to support:
- Real-time SSE streaming
- Reconnection after disconnect
- Cancellation handling

### Redis Data Structures

| Key Pattern | Type | Purpose | TTL | Example Value |
|-------------|------|---------|-----|---------------|
| `stream:events:{job_id}` | LIST | Ordered list of all events for replay | 5 min | `[event0, event1, event2, ...]` |
| `partial:response:{job_id}` | STRING | Accumulated text response | 10 min | `"The authentication flow uses..."` |
| `stream:active:{job_id}` | STRING | Flag indicating job is processing | 10 min | `"1"` |
| `cancel:{job_id}` | STRING | Cancellation flag | 5 min | `"true"` |

### stream:events:{job_id} - Event List

**Purpose:** Store all SSE events in order for replay after disconnect.

**Structure:**
```python
# Each event stored as JSON string
events = [
    {
        "index": 0,
        "type": "message_start",
        "data": {"conversation_id": "...", "turn_id": "..."},
        "timestamp": "2026-01-30T10:00:00.123Z"
    },
    {
        "index": 1,
        "type": "text_delta",
        "data": {"content": "The authentication "},
        "timestamp": "2026-01-30T10:00:01.234Z"
    },
    {
        "index": 2,
        "type": "text_delta",
        "data": {"content": "flow uses "},
        "timestamp": "2026-01-30T10:00:01.456Z"
    },
    {
        "index": 3,
        "type": "tool_use",
        "data": {
            "tool_call_id": "call_abc123",
            "tool_name": "read_file",
            "params": {"path": "auth.py"}
        },
        "timestamp": "2026-01-30T10:00:02.000Z"
    },
    {
        "index": 4,
        "type": "tool_result",
        "data": {"tool_call_id": "call_abc123", "status": "completed"},
        "timestamp": "2026-01-30T10:00:02.450Z"
    },
    {
        "index": 5,
        "type": "message_stop",
        "data": {
            "token_usage": {"input_tokens": 450, "output_tokens": 320},
            "processing_time_ms": 5420
        },
        "timestamp": "2026-01-30T10:00:05.620Z"
    }
]

# Redis commands
RPUSH stream:events:{job_id} '{"index": 0, "type": "message_start", ...}'
RPUSH stream:events:{job_id} '{"index": 1, "type": "text_delta", ...}'
EXPIRE stream:events:{job_id} 300  # 5 minutes
```

### partial:response:{job_id} - Accumulated Text

**Purpose:** Store accumulated response text for instant display on reconnect.

**Structure:**
```python
# Simple string that grows as text_delta events arrive
partial_response = "The authentication flow uses FastAPI's dependency injection system..."

# Redis commands
SET partial:response:{job_id} ""
APPEND partial:response:{job_id} "The authentication "
APPEND partial:response:{job_id} "flow uses "
APPEND partial:response:{job_id} "FastAPI's dependency injection system..."
EXPIRE partial:response:{job_id} 600  # 10 minutes
```

---

## 3. Message Lifecycle

### Phase 1: Message Submission (Instant)

```
User submits: "Explain auth.py"
         ↓
FastAPI creates ConversationTurn in PostgreSQL:
{
  id: "new-uuid",
  conversation_id: "...",
  job_id: "new-job-id",
  role: "user",
  content: "Explain auth.py",
  tool_calls: [],
  created_at: NOW(),
  completed_at: NOW()  // User messages complete immediately
}
         ↓
FastAPI enqueues to pgmq
         ↓
Returns to user: {job_id, stream_url}
```

### Phase 2: Processing Starts (Worker)

```
Worker picks up message from pgmq
         ↓
Worker initializes Redis session:
  SETEX stream:active:{job_id} 600 "1"
  SETEX partial:response:{job_id} 600 ""
  DEL stream:events:{job_id}
         ↓
Worker creates ConversationTurn in PostgreSQL:
{
  id: "new-uuid",
  job_id: job_id,
  role: "assistant",
  content: "",  // Empty initially
  completed_at: NULL  // Not finished yet
}
```

### Phase 3: Streaming (Real-time Updates)

```
For each SDK event:
    ↓
Worker transforms to SSE format
    ↓
Worker stores in Redis:
  RPUSH stream:events:{job_id} '{"index": N, "type": "...", ...}'
  APPEND partial:response:{job_id} "text content"
    ↓
Worker publishes to Redis pub/sub:
  PUBLISH stream:{job_id} '{"type": "text_delta", ...}'
    ↓
FastAPI forwards to user via SSE
```

### Phase 4: Completion (Persistence)

```
SDK sends stop event
         ↓
Worker updates PostgreSQL:
UPDATE conversation_turns
SET
  content = "The authentication flow uses...",  // Full response
  tool_calls = [{...}],
  token_usage = {...},
  processing_time_ms = 5420,
  completed_at = NOW()
WHERE job_id = ?
         ↓
Worker cleans up Redis (with TTL):
  DEL stream:active:{job_id}
  EXPIRE stream:events:{job_id} 300      // Keep 5 more min
  EXPIRE partial:response:{job_id} 300
         ↓
Worker deletes message from pgmq
```

---

## 4. Data Retrieval Patterns

### Pattern 1: Get Conversation History

**Use Case:** User opens conversation page or reconnects.

```sql
-- Get last 20 turns for a conversation
SELECT
  id,
  role,
  content,
  tool_calls,
  token_usage,
  processing_time_ms,
  created_at,
  completed_at
FROM conversation_turns
WHERE conversation_id = ?
ORDER BY created_at DESC
LIMIT 20;
```

**FastAPI Endpoint:**
```python
@router.get("/api/v1/ai/chat/conversations/{conversation_id}/history")
async def get_conversation_history(
    conversation_id: UUID,
    limit: int = 20,
    offset: int = 0
):
    turns = await db.query(ConversationTurn).filter(
        ConversationTurn.conversation_id == conversation_id
    ).order_by(
        ConversationTurn.created_at.desc()
    ).limit(limit).offset(offset).all()

    return {
        "conversation_id": conversation_id,
        "total_turns": await db.count(ConversationTurn, conversation_id),
        "turns": [
            {
                "id": str(turn.id),
                "role": turn.role,
                "content": turn.content,
                "timestamp": turn.created_at.isoformat(),
                "completed": turn.completed_at is not None
            }
            for turn in turns
        ]
    }
```

### Pattern 2: Get Active Turn (Still Processing)

**Use Case:** Check if job is still running.

```sql
-- Get active turn (not completed yet)
SELECT
  id,
  job_id,
  role,
  content,
  created_at
FROM conversation_turns
WHERE
  conversation_id = ?
  AND completed_at IS NULL
ORDER BY created_at DESC
LIMIT 1;
```

### Pattern 3: Get Missed Events (Reconnection)

**Use Case:** User reconnects after disconnect.

```python
@router.get("/api/v1/ai/chat/stream/{job_id}/events")
async def get_missed_events(
    job_id: UUID,
    after_event: int = 0  # Last event index user received
):
    # Get events from Redis
    redis = get_redis()
    events_key = f"stream:events:{job_id}"

    # Get all events
    all_events = await redis.lrange(events_key, 0, -1)

    # Filter events after the specified index
    missed_events = []
    for event_json in all_events:
        event = json.loads(event_json)
        if event["index"] > after_event:
            missed_events.append(event)

    return {
        "job_id": str(job_id),
        "total_events": len(all_events),
        "missed_events": len(missed_events),
        "events": missed_events
    }
```

### Pattern 4: Context Pruning (Semantic Search)

**Use Case:** Keep only relevant turns for long conversations.

```sql
-- Find most semantically similar turns to current message
SELECT
  id,
  content,
  1 - (message_embedding <=> :current_embedding) AS similarity
FROM conversation_turns
WHERE conversation_id = ?
ORDER BY message_embedding <=> :current_embedding
LIMIT 10;
```

**Python Code:**
```python
from pgvector.sqlalchemy import Vector

async def prune_conversation_history(
    conversation_id: UUID,
    current_message: str,
    max_turns: int = 20
) -> list[ConversationTurn]:
    """Keep only last N most relevant turns using semantic similarity."""

    # Get embedding for current message
    current_embedding = await get_embedding(current_message)

    # Always keep last 5 turns
    recent_turns = await db.query(ConversationTurn).filter(
        ConversationTurn.conversation_id == conversation_id
    ).order_by(
        ConversationTurn.created_at.desc()
    ).limit(5).all()

    # Find most similar older turns
    older_turns = await db.query(ConversationTurn).filter(
        ConversationTurn.conversation_id == conversation_id,
        ConversationTurn.id.notin_([t.id for t in recent_turns])
    ).order_by(
        ConversationTurn.message_embedding.cosine_distance(current_embedding)
    ).limit(max_turns - 5).all()

    return recent_turns + older_turns
```

---

## 5. Storage Optimization Strategies

### 5.1 Compression

For long assistant responses, store compressed content:

```python
import zlib
import base64

def compress_content(content: str) -> str:
    """Compress long content for storage."""
    if len(content) < 1000:  # Only compress if > 1KB
        return content

    compressed = zlib.compress(content.encode('utf-8'))
    return base64.b64encode(compressed).decode('ascii')

def decompress_content(content: str) -> str:
    """Decompress content on retrieval."""
    try:
        compressed = base64.b64decode(content.encode('ascii'))
        return zlib.decompress(compressed).decode('utf-8')
    except:
        return content  # Not compressed, return as-is
```

### 5.2 Archival (Cold Storage)

Move old conversations to cheaper storage:

```python
# Archive conversations older than 90 days
async def archive_old_conversations():
    """Move conversations > 90 days old to S3/cold storage."""

    cutoff_date = datetime.utcnow() - timedelta(days=90)

    old_turns = await db.query(ConversationTurn).filter(
        ConversationTurn.created_at < cutoff_date
    ).all()

    # Export to JSON
    export_data = [
        {
            "id": str(turn.id),
            "conversation_id": str(turn.conversation_id),
            "role": turn.role,
            "content": turn.content,
            "created_at": turn.created_at.isoformat()
        }
        for turn in old_turns
    ]

    # Upload to S3
    s3_key = f"archives/{cutoff_date.year}/{cutoff_date.month}/turns.json.gz"
    await upload_to_s3(s3_key, gzip.compress(json.dumps(export_data).encode()))

    # Delete from PostgreSQL
    await db.delete(old_turns)
    await db.commit()
```

### 5.3 Embedding Generation

Generate embeddings asynchronously after message completion:

```python
# Background job (Celery/Supabase Queue)
async def generate_embeddings_job():
    """Generate embeddings for turns without embeddings."""

    turns_without_embeddings = await db.query(ConversationTurn).filter(
        ConversationTurn.message_embedding.is_(None)
    ).limit(100).all()

    for turn in turns_without_embeddings:
        # Generate embedding using OpenAI
        embedding = await openai_client.embeddings.create(
            model="text-embedding-ada-002",
            input=turn.content
        )

        turn.message_embedding = embedding.data[0].embedding
        await db.commit()
```

---

## 6. Data Retention Policies

| Data Type | Storage | Retention | Cleanup Strategy |
|-----------|---------|-----------|------------------|
| **User Messages** | PostgreSQL | Permanent | User-initiated deletion only |
| **Assistant Messages** | PostgreSQL | 90 days (hot) → Archive (cold) | Automated archival job |
| **Tool Calls** | PostgreSQL (JSONB) | Same as assistant messages | Included in archival |
| **Token Usage** | PostgreSQL (JSONB) | Same as assistant messages | Aggregated to metrics |
| **SSE Events** | Redis | 5 minutes | TTL auto-expiration |
| **Partial Responses** | Redis | 10 minutes | TTL auto-expiration |
| **Embeddings** | PostgreSQL (vector) | Same as messages | Included in archival |

---

## 7. Storage Metrics

**PostgreSQL Table Size:**
```sql
-- Check table size
SELECT
  pg_size_pretty(pg_total_relation_size('conversation_turns')) AS total_size,
  pg_size_pretty(pg_relation_size('conversation_turns')) AS table_size,
  pg_size_pretty(pg_indexes_size('conversation_turns')) AS indexes_size;
```

**Expected Growth:**
```
Average message size: 500 bytes (text) + 6KB (embedding) = 6.5 KB
100 conversations/day × 10 turns/conversation = 1000 turns/day
1000 turns × 6.5 KB = 6.5 MB/day
6.5 MB × 365 days = 2.37 GB/year
```

**Redis Memory Usage:**
```
Average events per job: 50 events × 200 bytes = 10 KB
Partial response: ~2 KB
Total per job: ~12 KB
100 concurrent jobs × 12 KB = 1.2 MB
```

---

## 8. Query Performance Optimization

### Indexes

```sql
-- Conversation history query (most common)
CREATE INDEX idx_conversation_turns_conversation
  ON conversation_turns(conversation_id, created_at DESC);

-- Active job lookup
CREATE INDEX idx_conversation_turns_job
  ON conversation_turns(job_id);

-- Partial index for active turns (WHERE completed_at IS NULL)
CREATE INDEX idx_conversation_turns_active
  ON conversation_turns(conversation_id, completed_at)
  WHERE completed_at IS NULL;

-- Vector similarity search
CREATE INDEX idx_conversation_turns_embedding
  ON conversation_turns
  USING ivfflat (message_embedding vector_cosine_ops)
  WITH (lists = 100);
```

### Query Plan Analysis

```sql
EXPLAIN ANALYZE
SELECT *
FROM conversation_turns
WHERE conversation_id = '660e8400-e29b-41d4-a716-446655440001'
ORDER BY created_at DESC
LIMIT 20;

-- Expected: Index Scan using idx_conversation_turns_conversation
-- Cost: ~0.5ms for 20 rows
```

---

## 9. Backup & Recovery

### PostgreSQL Backup

```bash
# Daily backup of conversation_turns table
pg_dump -h localhost -U postgres \
  --table=conversation_turns \
  --format=custom \
  --file=backups/turns_$(date +%Y%m%d).dump \
  pilot_space

# Restore
pg_restore -h localhost -U postgres \
  --table=conversation_turns \
  backups/turns_20260130.dump
```

### Point-in-Time Recovery

```sql
-- Restore conversation to specific point in time
SELECT *
FROM conversation_turns
WHERE
  conversation_id = ?
  AND created_at <= '2026-01-30T10:00:00Z'
ORDER BY created_at DESC;
```

---

## Summary

**Storage Architecture:**
- **Redis** (temporary): Real-time streaming, 5-10 min TTL
- **PostgreSQL** (permanent): Conversation history, forever (with archival)

**Key Tables:**
- `conversation_turns` - All messages with embeddings
- `agent_sessions` - Session metadata

**Data Flow:**
1. User message → PostgreSQL (instant)
2. Worker creates assistant turn → PostgreSQL (in-progress)
3. Streaming events → Redis (5 min TTL)
4. Completion → PostgreSQL (final update)
5. Archival → S3/cold storage (after 90 days)

**Performance:**
- Query latency: < 10ms for 20 turns
- Storage growth: ~2.4 GB/year (100 conversations/day)
- Redis memory: ~1.2 MB (100 concurrent jobs)

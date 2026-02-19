# Black Box Architecture: AI Workforce Core (Feature 015)

**Version**: 1.1
**Principles**: Eskil Steenberg — replaceable modules, primitive-first, one person per module

---

## 1. Primitives

Three data types flow through the entire system. Everything else is derived.

```
WorkIntent      — what the human wants done
SkillResult     — what the AI produced
MemoryEntry     — what the system learned
```

That's it. Every module accepts or produces one of these three.

---

## 2. Module Map

```
┌─────────────────────────────────────────────────────────┐
│                    AGENT LOOP (M1)                        │
│                                                           │
│   message ──→ MemoryStore.recall()                        │
│           ──→ IntentStore.detect()                         │
│           ──→ (human confirms)                             │
│           ──→ SkillRunner.execute()                        │
│           ──→ MemoryStore.save()                           │
│           ──→ SSE stream to client                         │
│                                                           │
│   This is a PIPELINE, not a god class.                    │
│   It calls 3 stores. It owns no business logic.           │
└────────┬──────────────┬───────────────┬──────────────────┘
         │              │               │
    ┌────▼────┐   ┌─────▼─────┐   ┌────▼─────┐
    │ Intent  │   │   Skill   │   │  Memory  │
    │  Store  │   │  Runner   │   │  Store   │
    │  (M2)   │   │   (M3)    │   │  (M4)    │
    └─────────┘   └───────────┘   └──────────┘
```

**4 modules total.** M7 (Chat Engine) is frontend-only — it consumes SSE events from M1. It is not a backend module.

### Why 4, not 5+

The spec lists 5 modules (M1-M4, M7). But M7 has zero backend services — it renders SSE events the agent loop already emits. Adding a "ChatEngineService" on the backend would be an empty wrapper. Frontend handles M7 entirely.

On the backend, 4 black boxes with 4 interfaces is the minimum.

---

## 3. Black Box Interfaces

### 3.1 IntentStore (M2)

**What it does**: Detects, stores, and manages WorkIntents.
**What it hides**: LLM prompt engineering, dedup algorithm, confidence scoring, chat-priority window.

```python
class IntentStore(Protocol):
    """Detect and manage work intents. One person can own this module."""

    async def detect(self, text: str, source: Source, ctx: WorkspaceContext) -> list[WorkIntent]:
        """Extract intents from human text. Returns 0+ intents, never throws."""
        ...

    async def confirm(self, intent_id: UUID) -> WorkIntent:
        """Mark intent as confirmed. Raises IntentNotFound or InvalidTransition."""
        ...

    async def reject(self, intent_id: UUID, feedback: str | None = None) -> None:
        """Dismiss intent. Optional feedback stored for learning."""
        ...

    async def edit(self, intent_id: UUID, changes: IntentPatch) -> WorkIntent:
        """Edit and re-score. Returns updated intent."""
        ...

    async def confirm_all(self, ctx: WorkspaceContext, min_confidence: float = 0.7) -> ConfirmAllResult:
        """Batch confirm top-10 by confidence. Returns confirmed + remaining count."""
        ...

    async def get_pending(self, ctx: WorkspaceContext) -> list[WorkIntent]:
        """List all pending intents for workspace."""
        ...
```

**Primitives in/out**:
- In: `str` (human text), `Source` (chat | note)
- Out: `WorkIntent`

**Replaceable?** Yes. Swap the LLM, change the prompt, use rules instead of AI — interface stays the same.

---

### 3.2 SkillRunner (M3)

**What it does**: Executes a skill against a confirmed WorkIntent, produces a SkillResult.
**What it hides**: SDK subagent lifecycle, tool whitelisting, concurrency semaphore, TipTap validation, approval hold.

```python
class SkillRunner(Protocol):
    """Execute skills as SDK subagents. One person can own this module."""

    async def execute(self, intent: WorkIntent, skill_name: str, ctx: WorkspaceContext) -> AsyncIterator[SkillEvent]:
        """
        Run skill. Yields progress events. Final event contains SkillResult.
        Destructive skills yield ApprovalRequired event and pause.
        """
        ...

    async def approve(self, execution_id: UUID) -> SkillResult:
        """Release held destructive output. Persists to note. Returns final result."""
        ...

    async def reject_execution(self, execution_id: UUID) -> None:
        """Discard held output. Intent → rejected."""
        ...

    async def list_skills(self) -> list[SkillDefinition]:
        """All available skills (core + workspace custom)."""
        ...
```

**Primitives in/out**:
- In: `WorkIntent`, `str` (skill name)
- Out: `SkillResult` (via `SkillEvent` stream)

**Replaceable?** Yes. Swap Claude SDK for OpenAI Assistants, use local LLM, run skills as microservices — interface stays the same.

---

### 3.3 MemoryStore (M4)

**What it does**: Stores and retrieves workspace knowledge.
**What it hides**: pgvector, FTS fusion weights, embedding provider, DLQ, constitution versioning.

```python
class MemoryStore(Protocol):
    """Persistent workspace knowledge. One person can own this module."""

    async def recall(self, query: str, ctx: WorkspaceContext, limit: int = 5) -> list[MemoryEntry]:
        """Search workspace memory. Hybrid vector+keyword. <200ms."""
        ...

    async def save(self, entry: MemoryEntry) -> MemoryEntry:
        """Persist a learning. Embeds async. Retries on failure. Never throws."""
        ...

    async def delete(self, entry_id: UUID) -> None:
        """Remove a memory entry."""
        ...

    async def ingest_constitution(self, rules: list[str], ctx: WorkspaceContext) -> int:
        """Parse and index constitution rules. Returns new version number."""
        ...

    async def get_constitution_version(self, ctx: WorkspaceContext) -> int:
        """Current indexed constitution version for the workspace."""
        ...
```

**Primitives in/out**:
- In: `str` (query), `MemoryEntry`
- Out: `list[MemoryEntry]`, `int` (version)

**Replaceable?** Yes. Swap pgvector for Pinecone, replace Gemini embeddings with OpenAI, use a flat file — interface stays the same.

---

### 3.4 AgentLoop (M1)

**What it does**: Orchestrates the pipeline. Calls IntentStore, SkillRunner, MemoryStore in order.
**What it hides**: Nothing complex. It's a thin pipeline. If it gets complex, you're doing it wrong.

```python
class AgentLoop:
    """
    Pipeline orchestrator. Owns NO business logic.
    Calls stores in order, emits SSE events.
    This is the ONLY module that knows about all three stores.
    """

    def __init__(
        self,
        intent_store: IntentStore,
        skill_runner: SkillRunner,
        memory_store: MemoryStore,
    ) -> None: ...

    async def process(self, message: str, ctx: WorkspaceContext) -> AsyncIterator[SSEEvent]:
        """
        Full pipeline:
        1. memory_store.recall(message)     → context
        2. intent_store.detect(message)     → intents
        3. Yield intent_detected events     → human confirms
        4. (on confirmation signal)
        5. skill_runner.execute(intent)     → yield progress events
        6. memory_store.save(learning)      → persist
        7. Yield completion event
        """
        ...

    async def on_intent_confirmed(self, intent_id: UUID, ctx: WorkspaceContext) -> AsyncIterator[SSEEvent]:
        """Resume pipeline after human confirms intent."""
        ...

    async def on_approval(self, execution_id: UUID, ctx: WorkspaceContext) -> AsyncIterator[SSEEvent]:
        """Resume pipeline after human approves destructive output."""
        ...
```

**Replaceable?** The pipeline order is the product decision. But each step is replaceable independently because AgentLoop only calls Protocol interfaces.

---

## 4. Primitives: Full Definitions

```python
@dataclass(frozen=True)
class WorkspaceContext:
    """Flows through every call. Immutable."""
    workspace_id: UUID
    user_id: UUID
    session_id: UUID | None = None


class Source(StrEnum):
    CHAT = "chat"
    NOTE = "note"


class IntentStatus(StrEnum):
    DETECTED = "detected"
    CONFIRMED = "confirmed"
    EXECUTING = "executing"
    REVIEW = "review"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


@dataclass
class WorkIntent:
    """The atomic unit of work."""
    id: UUID
    what: str
    why: str
    constraints: list[str]
    acceptance: list[str]
    status: IntentStatus
    confidence: float               # 0.0 - 1.0
    source: Source
    owner: str | None = None        # skill name or None (human)
    parent_intent_id: UUID | None = None
    source_block_id: UUID | None = None
    workspace_id: UUID = field(default_factory=UUID)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class SkillResult:
    """What a skill produced."""
    execution_id: UUID
    intent_id: UUID
    skill_name: str
    status: Literal["completed", "failed", "pending_approval"]
    output_blocks: list[dict]       # TipTap JSON blocks (validated)
    target_note_id: UUID | None     # where output was/will be written
    error: str | None = None


class SkillEventType(StrEnum):
    STARTED = "started"
    PROGRESS = "progress"
    APPROVAL_REQUIRED = "approval_required"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class SkillEvent:
    """Streaming event from skill execution."""
    type: SkillEventType
    execution_id: UUID
    intent_id: UUID
    skill_name: str
    data: dict                      # type-specific payload
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class MemoryEntry:
    """What the system learned."""
    id: UUID
    content: str
    source_type: Literal["intent", "skill_outcome", "user_feedback", "constitution"]
    workspace_id: UUID
    source_id: UUID | None = None   # intent_id or execution_id
    pinned: bool = False
    # embedding + keywords are internal to MemoryStore — NOT in this dataclass


@dataclass
class ConfirmAllResult:
    confirmed: list[WorkIntent]
    remaining_count: int


@dataclass
class IntentPatch:
    what: str | None = None
    why: str | None = None
    constraints: list[str] | None = None
    acceptance: list[str] | None = None


@dataclass
class SkillDefinition:
    name: str
    description: str
    domain: str
    model_tier: str
    approval: Literal["auto", "suggest", "require"]
    tools: list[str]
```

---

## 5. SSE Event Contract (M1 → M7)

The agent loop emits these events. The frontend renders them. That's the entire M7 contract.

```typescript
// Frontend receives these via EventSource. Each is a JSON line.
type SSEEvent =
  | { type: "intent_detected";      data: { intent: WorkIntent } }
  | { type: "intent_confirmed";     data: { intent_id: string } }
  | { type: "skill_started";        data: { execution_id: string; intent_id: string; skill_name: string } }
  | { type: "skill_progress";       data: { execution_id: string; message: string; percent?: number } }
  | { type: "approval_required";    data: { execution_id: string; preview_blocks: TipTapBlock[]; expires_at: string } }
  | { type: "skill_completed";      data: { execution_id: string; result: SkillResult } }
  | { type: "skill_failed";         data: { execution_id: string; error: string } }
  | { type: "memory_saved";         data: { entry_id: string } }
  | { type: "text_delta";           data: { content: string } }
  | { type: "error";                data: { message: string; code: string } }
```

**No other contract is needed between backend and frontend for Feature 015.**

---

## 6. Background Jobs

### Design Principle

The request-response cycle handles fast operations (<2s). Anything requiring an external API call (embedding) or time-based cleanup (expiry) runs as a background job. This keeps the agent loop snappy and the UX responsive.

### What Runs Inline vs Background

| Operation | Path | Why |
|-----------|------|-----|
| Intent detection (LLM) | Inline | Must return <2s for chat UX |
| Intent confirm/reject | Inline | DB status update, <50ms |
| Skill execution | Inline (streaming) | User watches progress via SSE |
| Memory keyword save | Inline | Fast PG insert, no API call |
| Memory recall (search) | Inline | Critical path, <200ms SLA |
| Approval approve/reject | Inline | DB update + persist, <500ms |
| **Intent dedup (embedding)** | **Background** | Gemini API call ~200ms, not on critical path |
| **Memory vector embedding** | **Background** | Gemini API call, keyword search works immediately |
| **Constitution vector indexing** | **Background** | Same as above, version gate handles consistency |
| **Stale intent expiry** | **Background** | Time-based, no request trigger |
| **Memory DLQ reconciliation** | **Background** | Hourly cleanup, no request trigger |
| **Approval expiry** | **Background** | Time-based (24h), no request trigger |

### Job Inventory

| ID | Job | Module | Trigger | Queue / Scheduler | Frequency |
|----|-----|--------|---------|-------------------|-----------|
| J-1 | Intent dedup | M2 | `IntentStore.detect()` enqueues after returning | `ai_normal` (pgmq) | Per detection |
| J-2 | Stale intent expiry | M2 | pg_cron | SQL function, no Python | Every 15 min |
| J-3 | Memory embedding | M4 | `MemoryStore.save()` enqueues after keyword persist | `ai_normal` (pgmq) | Per save |
| J-4 | Constitution vector indexing | M4 | `MemoryStore.ingest_constitution()` enqueues after keyword index | `ai_normal` (pgmq) | Per constitution edit |
| J-5 | Memory DLQ reconciliation | M4 | pg_cron enqueues to `ai_normal` | `ai_normal` (pgmq) | Every 1 hour |
| J-6 | Approval expiry | M3 | pg_cron | SQL function, no Python | Every 1 hour |

### Architecture

```
         AgentLoop (M1) — request path (inline)
        /      |       \
IntentStore  SkillRunner  MemoryStore
   (M2)        (M3)         (M4)
     │                        │
     │ enqueue(J-1)           ├── enqueue(J-3: embedding)
     │                        └── enqueue(J-4: constitution)
     │
     └────────────┬───────────┘
                  │
     ┌────────────▼────────────────┐
     │    ai_normal queue (pgmq)   │
     │  ┌──────┐ ┌──────┐ ┌─────┐ │
     │  │ J-1  │ │ J-3  │ │ J-4 │ │
     │  │dedup │ │embed │ │const│ │
     │  └──────┘ └──────┘ └─────┘ │
     └────────────┬────────────────┘
                  │
           MemoryWorker (polls)
                  │
     ┌────────────▼────────────────┐
     │  pg_cron (SQL-only jobs)    │
     │  J-2: stale intents (15min) │
     │  J-5: DLQ recon (hourly)    │
     │  J-6: approval expiry (1hr) │
     └────────────────────────────┘
```

### Worker Design

**One new worker** — `MemoryWorker`. Follows existing `DigestWorker` pattern: polls `ai_normal`, routes by `task_type`.

```python
class MemoryWorker:
    """Single worker for all Feature 015 background jobs.
    Polls ai_normal queue. Routes to handler by task_type."""

    HANDLERS: dict[str, type[JobHandler]] = {
        "intent_dedup": IntentDedupJobHandler,
        "memory_embedding": MemoryEmbeddingJobHandler,
        "memory_dlq_reconciliation": MemoryDLQJobHandler,
    }

    def __init__(self, queue: SupabaseQueueClient, session_factory: async_sessionmaker):
        # Same pattern as DigestWorker

    async def start(self) -> None:
        """Poll loop: dequeue → route → ack/nack. Sleeps 2s on empty."""

    async def stop(self) -> None:
        """Graceful shutdown."""

    async def _process(self, message: QueueMessage) -> None:
        handler_cls = self.HANDLERS[message.payload["task_type"]]
        async with self._session_factory() as session:
            handler = handler_cls(session)
            await handler.handle(message.payload)
```

### Job Handlers

```python
class IntentDedupJobHandler:
    """J-1: Embed intent 'what' field, find >90% similar pending intents, merge."""
    async def handle(self, payload: dict) -> dict:
        # 1. Get intent by ID
        # 2. Embed 'what' via Gemini
        # 3. Vector search pending intents in same workspace
        # 4. If cosine >0.9 → merge (keep higher confidence, emit SSE intent_merged)
        # 5. Return {"merged": bool, "merged_with": UUID | None}

class MemoryEmbeddingJobHandler:
    """J-3 + J-4: Embed content via Gemini, update memory_entries/constitution_rules row."""
    async def handle(self, payload: dict) -> dict:
        # 1. Get entry by ID (memory_entry or constitution_rule)
        # 2. Embed content via Gemini gemini-embedding-001 (768-dim)
        # 3. UPDATE row SET embedding = vector
        # 4. For constitution: update indexed_version
        # 5. Return {"embedded": True, "entry_id": UUID}

class MemoryDLQJobHandler:
    """J-5: Retry failed memory saves, detect orphaned executions."""
    async def handle(self, payload: dict) -> dict:
        # 1. SELECT FROM memory_dlq WHERE attempts < 6 AND next_retry_at <= now()
        # 2. For each: retry save (embed + persist)
        # 3. On success: DELETE from DLQ
        # 4. On failure: INCREMENT attempts, SET next_retry_at (exponential)
        # 5. Detect orphans: skill_executions with no memory_entry AND age > 1h
        # 6. Return {"retried": N, "recovered": M, "orphans_detected": K}
```

### pg_cron SQL Functions (in Migration 039)

```sql
-- J-2: Stale intent expiry (every 15 min)
CREATE OR REPLACE FUNCTION fn_expire_stale_intents()
RETURNS void LANGUAGE plpgsql SECURITY INVOKER AS $$
BEGIN
  UPDATE work_intents
  SET status = 'rejected', updated_at = now()
  WHERE status = 'detected'
    AND created_at < now() - interval '1 hour';
END;
$$;
SELECT cron.schedule('expire-stale-intents', '*/15 * * * *',
  'SELECT fn_expire_stale_intents()');

-- J-5: DLQ reconciliation trigger (hourly → enqueues to ai_normal)
CREATE OR REPLACE FUNCTION fn_enqueue_memory_dlq_reconciliation()
RETURNS void LANGUAGE plpgsql SECURITY INVOKER AS $$
BEGIN
  PERFORM pgmq.send('ai_normal', jsonb_build_object(
    'task_type', 'memory_dlq_reconciliation',
    'triggered_at', now()::text
  ));
END;
$$;
SELECT cron.schedule('memory-dlq-reconciliation', '0 * * * *',
  'SELECT fn_enqueue_memory_dlq_reconciliation()');

-- J-6: Approval expiry (hourly)
CREATE OR REPLACE FUNCTION fn_expire_pending_approvals()
RETURNS void LANGUAGE plpgsql SECURITY INVOKER AS $$
BEGIN
  UPDATE skill_executions
  SET approval_status = 'expired', updated_at = now()
  WHERE approval_status = 'pending_approval'
    AND created_at < now() - interval '24 hours';
END;
$$;
SELECT cron.schedule('expire-pending-approvals', '0 * * * *',
  'SELECT fn_expire_pending_approvals()');
```

### Enqueue Points

| Job | Enqueued from | Code |
|-----|---------------|------|
| J-1 | `IntentStore.detect()` after returning intents | `queue.enqueue_ai_task("intent_dedup", workspace_id, {"intent_id": id}, "normal")` |
| J-2 | pg_cron (no Python) | Migration 039 SQL |
| J-3 | `MemoryStore.save()` after keyword persist | `queue.enqueue_ai_task("memory_embedding", workspace_id, {"entry_id": id, "table": "memory_entries"}, "normal")` |
| J-4 | `MemoryStore.ingest_constitution()` after keyword index | `queue.enqueue_ai_task("memory_embedding", workspace_id, {"entry_id": id, "table": "constitution_rules"}, "normal")` |
| J-5 | pg_cron → `ai_normal` queue | Migration 039 SQL |
| J-6 | pg_cron (no Python) | Migration 039 SQL |

### Startup Wiring (main.py lifespan)

```python
# Added alongside existing DigestWorker
memory_worker = MemoryWorker(queue_client, session_factory)
memory_worker_task = asyncio.create_task(memory_worker.start())

# Shutdown
await memory_worker.stop()
memory_worker_task.cancel()
```

### Black Box Boundary

Background jobs are **internal to their owning module**. The enqueue call is inside the store implementation. Callers of `IntentStore.detect()` and `MemoryStore.save()` never know that background work was triggered.

```
IntentStore.detect()     → returns intents immediately
                         → internally enqueues J-1 (invisible to caller)

MemoryStore.save()       → persists content + keywords synchronously
                         → internally enqueues J-3 (invisible to caller)
                         → caller gets MemoryEntry back, embedding arrives later
```

This preserves the black box contract: the interface doesn't change whether embedding is sync or async.

---

## 7. File Layout

Follows existing codebase conventions exactly. No new patterns introduced.

```
backend/src/pilot_space/
├── ai/
│   ├── agents/
│   │   └── agent_loop.py                    # AgentLoop (M1) — thin pipeline
│   ├── intent/                              # NEW directory
│   │   ├── __init__.py
│   │   ├── types.py                         # WorkIntent, IntentStatus, Source, IntentPatch
│   │   ├── store.py                         # IntentStore implementation
│   │   ├── detector.py                      # LLM-based detection (hidden behind store)
│   │   └── dedup.py                         # Semantic dedup (hidden behind store)
│   ├── skill/                               # NEW directory
│   │   ├── __init__.py
│   │   ├── types.py                         # SkillResult, SkillEvent, SkillDefinition
│   │   ├── runner.py                        # SkillRunner implementation
│   │   ├── validator.py                     # TipTap output validation (hidden)
│   │   └── concurrency.py                   # Semaphore manager (hidden)
│   ├── memory/                              # NEW directory
│   │   ├── __init__.py
│   │   ├── types.py                         # MemoryEntry (domain-facing)
│   │   ├── store.py                         # MemoryStore implementation
│   │   ├── embedder.py                      # Gemini embedding (hidden)
│   │   ├── constitution.py                  # Constitution versioning (hidden)
│   │   └── dlq.py                           # Dead-letter queue (hidden)
│   ├── jobs/
│   │   ├── digest_job.py                    # existing
│   │   ├── digest_context.py                # existing
│   │   ├── intent_dedup_job.py              # J-1: IntentDedupJobHandler
│   │   ├── memory_embedding_job.py          # J-3 + J-4: MemoryEmbeddingJobHandler
│   │   └── memory_dlq_job.py               # J-5: MemoryDLQJobHandler
│   ├── workers/
│   │   ├── digest_worker.py                 # existing
│   │   └── memory_worker.py                 # NEW: polls ai_normal, routes by task_type
│   └── templates/skills/
│       ├── generate-code/SKILL.md           # 6 net-new skills
│       ├── write-tests/SKILL.md
│       ├── generate-migration/SKILL.md
│       ├── review-code/SKILL.md
│       ├── review-architecture/SKILL.md
│       └── scan-security/SKILL.md
│
├── application/services/
│   └── ai/
│       ├── intent_service.py                # Thin wrapper: IntentStore → API payloads
│       ├── skill_service.py                 # Thin wrapper: SkillRunner → API payloads
│       ├── memory_service.py                # Thin wrapper: MemoryStore → API payloads
│       └── approval_service.py              # Thin wrapper: SkillRunner.approve/reject → API
│
├── infrastructure/database/
│   ├── models/
│   │   ├── work_intent.py                   # SQLAlchemy model (WorkspaceScopedModel)
│   │   ├── intent_artifact.py
│   │   ├── memory_entry.py
│   │   ├── constitution_rule.py
│   │   └── memory_dlq.py
│   ├── repositories/
│   │   ├── work_intent_repository.py        # BaseRepository[WorkIntentModel]
│   │   ├── memory_entry_repository.py       # + hybrid search query
│   │   ├── constitution_rule_repository.py
│   │   └── memory_dlq_repository.py
│   └── migrations/versions/
│       ├── 038_work_intents.py
│       └── 039_memory_engine.py
│
├── api/v1/
│   ├── routers/
│   │   ├── ai_intents.py                    # Intent CRUD + detect + confirm-all
│   │   ├── ai_approvals.py                  # Approve/reject destructive output
│   │   └── ai_memory.py                     # Memory search + constitution version
│   └── schemas/
│       ├── ai_intent.py                     # Request/response Pydantic schemas
│       ├── ai_approval.py
│       └── ai_memory.py
│
frontend/src/
├── features/ai/ChatView/
│   ├── cards/                               # NEW directory
│   │   ├── IntentCard.tsx
│   │   ├── SkillProgressCard.tsx
│   │   ├── ApprovalCard.tsx
│   │   └── ConversationBlock.tsx
│   ├── MessageRenderer.tsx                  # Polymorphic: event type → card component
│   ├── ConfirmAllButton.tsx
│   └── QueueIndicator.tsx
├── stores/
│   └── IntentStore.ts                       # MobX store for intent lifecycle
└── services/api/
    ├── intentApi.ts                         # API client for intent endpoints
    ├── approvalApi.ts                       # API client for approval endpoints
    └── memoryApi.ts                         # API client for memory endpoints
```

### File count: ~50 new files

| Layer | Files | Largest file estimate |
|-------|-------|----------------------|
| AI modules (intent, skill, memory, agent_loop) | 14 | ~400 lines (store.py) |
| Background jobs + worker | 4 | ~200 lines (memory_embedding_job.py) |
| Application services | 4 | ~150 lines |
| DB models | 5 | ~100 lines |
| Repositories | 4 | ~200 lines (memory hybrid search) |
| Migrations | 2 | ~200 lines (039 includes pg_cron functions) |
| API routers + schemas | 6 | ~200 lines |
| Frontend components | 7 | ~250 lines |
| Frontend stores + API clients | 4 | ~200 lines |
| **Total** | **~50** | **All under 400 lines** |

No file exceeds 700-line limit. Most are under 300.

---

## 7. Module Dependency Rules

```
         AgentLoop (M1)
        /      |       \
IntentStore  SkillRunner  MemoryStore
   (M2)        (M3)         (M4)

Rules:
1. AgentLoop depends on all 3 stores (it's the pipeline)
2. IntentStore, SkillRunner, MemoryStore depend on NOTHING from each other
3. SkillRunner MAY call MemoryStore.recall() for skill context — but through AgentLoop, not directly
4. Each store depends only on its own repository + external APIs
5. Frontend depends only on SSE events + 3 API clients
```

**Why no cross-store dependencies?**

The spec says skills use memory context (M3 needs M4). But the AgentLoop handles this — it calls `MemoryStore.recall()` first, passes context to `SkillRunner.execute()` as part of the intent's constraints. SkillRunner never calls MemoryStore directly.

This keeps each store independently testable and replaceable.

---

## 8. Integration with Existing Architecture

### What changes in PilotSpaceAgent

PilotSpaceAgent **stays as the SDK orchestrator**. AgentLoop is a new internal pipeline that PilotSpaceAgent calls instead of directly running `agent.query()`.

```python
# Before (current):
class PilotSpaceAgent:
    async def stream(self, input_data, context):
        # ... directly calls SDK, processes response

# After (Feature 015):
class PilotSpaceAgent:
    def __init__(self, ..., agent_loop: AgentLoop):
        self._agent_loop = agent_loop

    async def stream(self, input_data, context):
        workspace_ctx = WorkspaceContext(workspace_id=..., user_id=...)
        async for event in self._agent_loop.process(input_data.message, workspace_ctx):
            yield self._transform_to_sse(event)
```

PilotSpaceAgent remains the DI entry point, SDK client creator, and SSE transformer. AgentLoop is the new pipeline it delegates to.

### What stays unchanged

- All 17 existing skills — frozen, no modifications
- All 36 existing MCP tools — no changes
- All existing subagents (PR review, doc generator, AI context) — still spawned by PilotSpaceAgent
- GhostTextService — independent fast path, untouched
- Session management — unchanged
- Provider routing — add new TaskTypes for intent detection and memory embedding

### New DI registrations

```python
# In container.py — 4 new singletons + 4 new factories
intent_store = providers.Singleton(IntentStore, ...)
skill_runner = providers.Singleton(SkillRunner, ...)
memory_store = providers.Singleton(MemoryStore, ...)
agent_loop = providers.Singleton(AgentLoop, intent_store=..., skill_runner=..., memory_store=...)

# Application services (per-request)
intent_service = providers.Factory(IntentService, session=..., intent_store=...)
skill_service = providers.Factory(SkillService, session=..., skill_runner=...)
memory_service = providers.Factory(MemoryService, session=..., memory_store=...)
approval_service = providers.Factory(ApprovalService, session=..., skill_runner=...)
```

---

## 9. What I Intentionally Left Out

| Omitted | Why |
|---------|-----|
| MemoryEntry.embedding field in domain primitive | Embedding is an implementation detail of MemoryStore. Callers never see or produce embeddings. |
| Skill execution DB model in domain layer | SkillRunner owns execution state internally. The approval API uses execution_id as an opaque handle. |
| Constitution version in WorkIntent | Skills check constitution version at execution time, not at intent creation. This is SkillRunner's concern. |
| Chat session management | Already exists. Feature 015 adds event types to the existing SSE stream, not a new session model. |
| Retry/circuit breaker config | Each store wraps ResilientExecutor internally. Callers don't configure resilience. |
| Frontend state management details | MobX store structure follows existing patterns. The SSE event contract is the interface. |

---

## 10. Validation Checklist

| Principle | Check |
|-----------|-------|
| **Primitives identified?** | 3: WorkIntent, SkillResult, MemoryEntry |
| **Black box boundaries clear?** | 4 modules, each with Protocol interface |
| **Each module replaceable?** | Yes — swap implementation behind Protocol |
| **One person per module?** | IntentStore (~800 LOC), SkillRunner (~600 LOC), MemoryStore (~700 LOC), AgentLoop (~300 LOC) |
| **No cross-store dependencies?** | AgentLoop is the only module that knows about all stores |
| **Existing patterns followed?** | Same DI, same repository, same router, same SSE patterns |
| **No over-engineering?** | 4 modules, 3 primitives, 10 API endpoints, 1 worker. Minimum viable. |
| **Background jobs hidden?** | Yes — enqueue is internal to stores, callers never know |
| **All files under 700 lines?** | Yes. Largest: ~400 lines |

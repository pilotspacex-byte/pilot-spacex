# Pilot Space Agent: PilotSpaceAgent Orchestrator

> **Location**: `backend/src/pilot_space/ai/agents/pilotspace_agent.py` (+ helpers)
> **Design Decisions**: DD-086 (Centralized Agent Architecture), DD-003 (Approval), DD-066 (SSE Streaming)

## Overview

`PilotSpaceAgent` is the **single entry point for all user-facing AI interactions** in Pilot Space. It is the centralized orchestrator (DD-086): every AI conversation, skill invocation, subagent dispatch, approval workflow, and SSE stream flows through it. It accepts a user message + context, assembles a layered system prompt, configures the Claude Agent SDK with workspace-scoped tools and keys, runs the SDK execution loop, transforms SDK events into SSE events, and manages the conversation session.

**9 core responsibilities**:
1. Workspace context setup (RLS + API keys)
2. Intent detection pipeline
3. System prompt assembly (6-layer)
4. MCP tool configuration (7 servers)
5. Message transformation (SDK → SSE)
6. Session persistence
7. Approval workflow (DD-003)
8. Error handling + cleanup
9. Telemetry + cost tracking

---

## Architecture

```
POST /api/v1/ai/chat  (SSE stream opens)
       ↓
PilotSpaceAgent.run(request: AIRequest) → AsyncGenerator[SSEEvent]
       ├── 1. Setup context (RLS, BYOK key resolution)
       ├── 2. Intent classification (IntentClassifier, ~1ms, no LLM)
       ├── 3. Prompt assembly (PromptAssembler, 6-layer)
       ├── 4. SDK config (SdkConfig, sandbox, MCP servers, hooks)
       ├── 5. Session load (SessionHandler.load_messages)
       ├── 6. SDK execution loop (query or run)
       │      ├── PreToolHook → permission_handler.classify()
       │      ├── MCP tool call → result
       │      ├── PostToolHook → audit + cost delta
       │      └── Stream events → sse_transformer.transform()
       ├── 7. SSE event emission (14 event types)
       ├── 8. Session update (SessionHandler.append_message)
       └── 9. Telemetry + cost track (fire-and-forget)
```

---

## `pilotspace_agent.py`

**~488 lines** — the core execution loop.

### Constructor

```python
class PilotSpaceAgent:
    def __init__(
        self,
        workspace_service: WorkspaceService,
        session_handler: SessionHandler,
        key_storage: SecureKeyStorage,
        cost_tracker: CostTracker,
        telemetry: AITelemetry,
        provider_selector: ProviderSelector,
        prompt_assembler: PromptAssembler,
        intent_classifier: IntentClassifier,
        permission_handler: PermissionHandler,
        approval_waiter: ApprovalWaiter,
        question_adapter: QuestionAdapter,
        # MCP servers injected as DI dependencies
        note_server: NoteServer,
        note_content_server: NoteContentServer,
        issue_server: IssueServer,
        issue_relation_server: IssueRelationServer,
        project_server: ProjectServer,
        comment_server: CommentServer,
        interaction_server: InteractionServer,
        ownership_server: OwnershipServer,
    )
```

All dependencies injected via `dependency-injector` (DD-064). No global state — each orchestrator instance is workspace-scoped.

### `run()` — Main Execution Entry Point

```python
async def run(
    self,
    request: AIRequest,
    context: AIRequestContext,
) -> AsyncGenerator[SSEEvent, None]:
```

**`AIRequest`** fields:
- `message: str` — user's message text
- `session_id: UUID | None` — resume existing session
- `agent_name: str` — `"pilotspace"` or subagent name (`"pr-review"`)
- `skill_name: str | None` — slash command invocation (`"extract-issues"`)
- `initial_prompt: bool` — whether this is an auto-sent initial prompt

**Execution phases**:

#### Phase 1: Context Setup
```python
# Set RLS context for all DB queries in this request
await set_rls_context(context.workspace_id, context.user_id, context.user_role)

# Resolve BYOK keys
api_key = await self.key_storage.get_api_key(context.workspace_id, "anthropic")
if not api_key:
    api_key = settings.anthropic_api_key  # deployment fallback
if not api_key:
    raise HTTPException(402, "No Anthropic API key configured")
```

#### Phase 2: Intent Detection
```python
intent = self.intent_classifier.classify(
    message=request.message,
    context=context,  # note_id/issue_id bias routing
)
# Returns IntentType: skill_invocation | agent_mention | free_conversation | ...
```

**~1ms, no LLM call** — regex-based classifier. Only dispatches to LLM if intent is `free_conversation` or requires multi-step reasoning.

#### Phase 3: System Prompt Assembly
```python
prompt = await self.prompt_assembler.assemble(
    intent=intent,
    context=context,
    conversation_history=session.messages if session else [],
)
# 6-layer: base + workspace + role + document + history + message
```

#### Phase 4: SDK Configuration
```python
sdk_config = SdkConfig(
    model=self.provider_selector.select(task_type)[1],
    api_key=api_key,
    sandbox_path=f"/sandbox/{context.user_id}/{context.workspace_id}",
    max_tokens=context.token_budget,
    tools=[
        self.note_server,
        self.note_content_server,
        self.issue_server,
        # ... all 7 MCP servers
    ],
    hooks=[
        PermissionHook(self.permission_handler),
        LifecycleHook(self.approval_waiter, self.question_adapter),
        AuditHook(self.cost_tracker),
    ],
)
```

#### Phase 5-6: SDK Execution + SSE Streaming
```python
async for sdk_event in sdk.run(prompt, config=sdk_config):
    sse_event = self.sse_transformer.transform(sdk_event)
    if sse_event:
        yield sse_event  # FastAPI StreamingResponse forwards to frontend
```

#### Phase 7-9: Cleanup
```python
# Session update (async, non-blocking)
asyncio.create_task(
    self.session_handler.append_message(session_id, user_msg, assistant_msg)
)

# Telemetry (fire-and-forget)
asyncio.create_task(
    self.telemetry.record(operation, context, tokens, duration_ms)
)

# Cost tracking (fire-and-forget)
asyncio.create_task(
    self.cost_tracker.track(context.workspace_id, context.user_id, ...)
)
```

**Why fire-and-forget for session/telemetry?** These operations must not block the SSE stream. The user should receive `message_stop` immediately after the last token, not after persistence finishes.

---

## `pilotspace_intent_pipeline.py`

**Purpose**: Higher-level intent routing — after `IntentClassifier` identifies the intent type, the pipeline dispatches to the correct handler.

**Routing table**:

| Intent type | Handler |
|-------------|---------|
| `skill_invocation` | `SkillExecutor.run(skill_name, args)` |
| `agent_mention` (`@pr-review`) | `PRReviewSubagent(...)` |
| `agent_mention` (`@doc-generator`) | `DocGeneratorSubagent(...)` |
| `agent_mention` (`@ai-context`) | `AIContextAgent(...)` |
| `issue_extraction_hint` | Suggest `\extract-issues` via `suggestion_event` |
| `note_editing` | Suggest `\improve-writing` via `suggestion_event` |
| `free_conversation` | `SDK.run(assembled_prompt)` |

**Suggestion events**: For `*_hint` intents, the pipeline emits a `suggestion` SSE event (rendered as a clickable chip in the frontend) rather than auto-invoking the skill. Respects human-in-the-loop principle — the user confirms the suggested action.

---

## `pilotspace_note_helpers.py`

**Purpose**: Note-specific context assembly utilities used by the orchestrator.

**`build_note_context(note_id, selected_block_ids, token_budget)`**:
1. Fetch full note content (`note.read_note`)
2. If `selected_block_ids` set: extract only those blocks
3. Build `BlockRefMap` (¶N notation)
4. If content exceeds `token_budget`: chunk and select most relevant chunks via pgvector similarity against user message
5. Return `NoteContext(content, block_ref_map, note_title)`

**Why chunking in helpers, not in prompt assembler?** Note chunking requires access to the note server (MCP tool) and the vector search service. The prompt assembler is a pure text manipulator that doesn't call external services.

---

## `pilotspace_agent_helpers.py`

**Purpose**: General-purpose orchestrator utilities.

**`build_workspace_context(workspace_id)`**: Assembles workspace-level context (project list, team size, active cycles) for Prompt Layer 2. Cached in Redis (30-min TTL) — workspace metadata rarely changes mid-session.

**`emit_intent_cards(intents)`**: When `IntentClassifier` returns multiple detected intents (e.g., extraction of 5 issues), emits `intent_detected` SSE events for each, enabling the frontend to show `IntentCard` components.

**`route_to_subagent(agent_name, context)`**: Constructs the correct subagent class, injects workspace context, and returns the initialized subagent. Centralized here to avoid import duplication across the intent pipeline.

---

## `pilotspace_stream_utils.py`

**Purpose**: SSE stream utilities — building, validating, and error-wrapping SSE events.

**`build_sse_event(event_type, payload)`**: Constructs a properly formatted `data: {json}\n\n` SSE event with `event_type`, `session_id`, and `timestamp` always included.

**`wrap_stream_errors(generator)`**: Async context manager that catches exceptions from the SDK execution loop and emits a `error` SSE event before re-raising, ensuring the frontend always receives an error notification rather than a silent stream close.

**`stream_with_timeout(generator, timeout_sec)`**: Wraps the SDK execution with a timeout. If the stream stalls (no events for `timeout_sec`), emits a `timeout` SSE event and cancels.

---

## `sse_delta_buffer.py`

**Purpose**: Buffer and batch rapid successive SSE token delta events to reduce frontend rendering overhead.

**Problem**: The SDK emits one `text_delta` event per token. At 50 tokens/second, the frontend would process 50 React re-renders/second — causing jank.

**Solution**: Accumulate deltas in a 50ms window, then flush as one batched event.

```python
class SSEDeltaBuffer:
    FLUSH_INTERVAL_MS = 50  # batch window

    async def push(delta: str) → SSEEvent | None:
        # Append delta to buffer
        # If buffer age > 50ms: flush and return batched event
        # Otherwise: return None (still accumulating)

    async def flush() → SSEEvent | None:
        # Force-flush any remaining buffer
        # Called on message_stop
```

**Result**: 10-100x reduction in SSE events — from ~50/sec (individual tokens) to 1-5/sec (50ms batches). Frontend renders feel smooth.

**Why 50ms?** At typical reading speeds, 50ms batches are imperceptible as discrete updates. Below 100ms feels "live"; above 200ms feels laggy.

---

## `stream_event_transformer.py`

**Purpose**: Transform raw SDK internal events into the 14 SSE event types the frontend's `PilotSpaceStreamHandler` consumes.

**Transformation table** (SDK event → SSE event):

| SDK Event | SSE Type | Notes |
|-----------|----------|-------|
| `ContentBlockStart(text)` | `text_delta` (initial) | Starts delta buffer |
| `ContentBlockDelta(text)` | `text_delta` | Through delta buffer |
| `ContentBlockStart(thinking)` | `thinking_delta` | Bypasses delta buffer (always immediate) |
| `ContentBlockDelta(thinking)` | `thinking_delta` | Bypasses delta buffer |
| `ToolUseStart` | `tool_use` | With tool name + use_id |
| `ToolUseInputDelta` | `tool_use` (input_json_delta) | Streams tool input JSON |
| `ToolResultEvent` | `tool_result` | With tool_use_id + result |
| `SubagentProgress` | `task_progress` | Step name + status |
| `ApprovalRequired` | `approval_request` | Action type + payload |
| `SkillApprovalRequired` | `skill_approval_request` | Skill artifacts |
| `IntentDetected` | `intent_detected` | Intent + confidence |
| `QuestionRequest` | `question_request` | Question options |
| `BudgetWarning` | `budget_warning` | Remaining tokens |
| `MessageStop` | `message_stop` | Flush delta buffer first |

**Thinking blocks bypass delta buffer**: Extended thinking tokens are emitted immediately for responsive rendering of the thinking animation.

---

## `agent_base.py`

**Purpose**: Base class that all agents (orchestrator + subagents) inherit.

**Provided capabilities**:
- `setup_rls_context(workspace_id, user_id, role)` → sets PostgreSQL session variables
- `get_byok_key(workspace_id, provider)` → decrypts BYOK from vault
- `execute_with_resilience(operation, timeout)` → retry + circuit breaker wrapper
- `track_cost(tokens, model)` → fire-and-forget cost recording
- `log_telemetry(operation, duration_ms, success)` → structured telemetry

**Why a base class instead of composition?** The same BYOK + RLS + retry + telemetry pattern appears in every agent. A base class enforces consistency — new agents cannot forget to set RLS context or track cost.

---

## `agents/types.py`

**Canonical type definitions** for the entire agent layer:

```python
@dataclass
class AgentTask:
    task_id: str
    name: str
    description: str | None
    status: Literal["pending", "running", "done", "failed"]
    progress: int | None        # 0-100
    eta: int | None             # seconds remaining
    agent_name: str | None      # which subagent
    model_id: str | None        # which model
    steps: list[TaskStep]
    started_at: datetime | None
    completed_at: datetime | None
    error: str | None

@dataclass
class AIRequest:
    message: str
    session_id: UUID | None
    agent_name: str
    skill_name: str | None
    initial_prompt: bool
    note_id: UUID | None
    issue_id: UUID | None
    project_id: UUID | None
    selected_block_ids: list[str] | None
```

---

## SSE Event Flow (Complete)

```
User message → run()
    ↓
yield SSEEvent(message_start)

    [SDK execution loop]

    On text token:
        SSEDeltaBuffer.push(token)
        → if buffer ready: yield SSEEvent(text_delta, batched_text)

    On thinking token:
        yield SSEEvent(thinking_delta, token)  # immediate, no buffer

    On tool call start:
        yield SSEEvent(tool_use, {tool_name, use_id})

    On tool input streaming:
        yield SSEEvent(tool_use, {input_json_delta})

    On tool result:
        yield SSEEvent(tool_result, {use_id, result})

    On task progress (subagent):
        yield SSEEvent(task_progress, {step, status})

    On approval required:
        yield SSEEvent(approval_request, {action_type, payload})
        [execution pauses — approval_waiter polls DB]
        → resume on approve, raise on reject

    On intent detected:
        yield SSEEvent(intent_detected, {intent, confidence})

    On question:
        yield SSEEvent(question_request, {question, options})
        [execution pauses — question_adapter awaits answer]

    [End of SDK loop]

    SSEDeltaBuffer.flush()  # emit any remaining buffered tokens
    yield SSEEvent(message_stop)
```

---

## Implicit Features

| Feature | Mechanism | File |
|---------|-----------|------|
| RLS set before every DB call | `setup_rls_context()` in `run()` | `agent_base.py` |
| Session/telemetry fire-and-forget | `asyncio.create_task()` | `pilotspace_agent.py` |
| Token delta batching (50ms) | `SSEDeltaBuffer` | `sse_delta_buffer.py` |
| Thinking tokens bypass buffer | Direct yield in transformer | `stream_event_transformer.py` |
| Stream timeout protection | `stream_with_timeout()` wrapper | `pilotspace_stream_utils.py` |
| Error → SSE (not silent close) | `wrap_stream_errors()` | `pilotspace_stream_utils.py` |
| Note context chunked by relevance | pgvector similarity in helpers | `pilotspace_note_helpers.py` |
| Workspace context cached 30min | Redis in `build_workspace_context()` | `pilotspace_agent_helpers.py` |
| Suggestion events (not auto-invoke) | `hint` intents → `suggestion` SSE | `pilotspace_intent_pipeline.py` |
| Subagent construction centralized | `route_to_subagent()` helper | `pilotspace_agent_helpers.py` |
| BYOK fallback to deployment key | `get_byok_key()` → env var fallback | `agent_base.py` |
| 402 Payment Required on no key | Explicit check before SDK config | `pilotspace_agent.py` |

---

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| Centralized orchestrator (DD-086) | Single entry point → consistent RLS, auth, session, telemetry. Routing logic not scattered across 8 agents. |
| Intent classification before LLM | Regex routes 90%+ of messages to correct handler in ~1ms. Saves 200ms+ LLM call for clear slash commands. |
| SSE delta buffer (50ms) | 50 tokens/sec → 50 re-renders/sec without buffering. Batching to 1-5/sec eliminates jank. |
| Fire-and-forget session + telemetry | These must not delay `message_stop` event. Async tasks run after the stream closes. |
| Suggestion events for hints | `*_hint` intents don't auto-invoke skills — human confirms. Respects DD-003 spirit even for non-destructive suggestions. |
| All subagents via orchestrator SSE | One SSE connection per frontend session. Subagents can't open their own connections. |
| `agent_base.py` enforces RLS/cost | New agents inherit the contract — cannot accidentally skip security-critical patterns. |

---

## Files Reference

| File | Lines | Purpose |
|------|-------|---------|
| `agents/pilotspace_agent.py` | ~488 | Main orchestrator, 9-phase execution loop |
| `agents/pilotspace_intent_pipeline.py` | ~200 | Intent → handler routing table |
| `agents/pilotspace_note_helpers.py` | ~180 | Note context assembly + chunking |
| `agents/pilotspace_agent_helpers.py` | ~160 | Workspace context, intent emission, subagent routing |
| `agents/pilotspace_stream_utils.py` | ~140 | SSE building, error wrapping, timeout |
| `agents/sse_delta_buffer.py` | ~100 | 50ms token batching |
| `agents/stream_event_transformer.py` | ~220 | SDK events → 14 SSE types |
| `agents/agent_base.py` | ~200 | RLS, BYOK, retry, telemetry base class |
| `agents/types.py` | ~150 | `AgentTask`, `AIRequest`, `NoteContext` types |
| `ai/README.md` | — | Complete AI layer architecture overview |
| `agents/README.md` | — | Agent-specific architecture + patterns |

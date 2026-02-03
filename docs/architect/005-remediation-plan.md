# 005: Remediation Plan — Claude Agent SDK Gap Closure

**Date**: 2026-02-03
**Branch**: `005-conversational-agent-arch`
**Prerequisite**: `docs/architect/005-sdk-feature-audit.md`
**Tasks**: #45–#53

---

## Phase 1: Security (P0) — Tasks #45, #46

### T1: Session Ownership Validation (#45)

**Problem**: `ai_chat.py:132-134` calls `session_handler.get_session(session_id_uuid)` without verifying the session belongs to the requesting `user_id` + `workspace_id`. A user who guesses a valid UUID can resume another user's session, accessing their conversation history and workspace context.

**Root Cause**: `SessionHandler.get_session()` at `session_handler.py:274-291` accepts only `session_id` and returns the session regardless of ownership.

**Data Flow (Current — INSECURE)**:
```
POST /chat {session_id: "abc-123", workspace_id: "ws-1"}
  → ai_chat.py: get_session("abc-123")        # No ownership check
  → session_handler.py: _session_manager.get_session("abc-123")
  → Returns session (may belong to ws-2/user-2)  # VIOLATION
```

**Fix — Option A (Preferred): Validate in SessionHandler**:

```python
# session_handler.py — modify get_session()
async def get_session(
    self,
    session_id: UUID,
    *,
    workspace_id: UUID | None = None,
    user_id: UUID | None = None,
) -> ConversationSession | None:
    try:
        ai_session = await self._session_manager.get_session(session_id)
    except SessionNotFoundError:
        return None

    session = self._to_conversation_session(ai_session)

    # Ownership validation
    if workspace_id is not None and session.workspace_id != workspace_id:
        logger.warning(
            "Session %s workspace mismatch: expected %s, got %s",
            session_id, workspace_id, session.workspace_id,
        )
        return None  # Treat as not found (don't leak existence)

    if user_id is not None and session.user_id != user_id:
        logger.warning(
            "Session %s user mismatch: expected %s, got %s",
            session_id, user_id, session.user_id,
        )
        return None

    return session
```

**Caller Update** (`ai_chat.py:132-134`):
```python
conv_session = await session_handler.get_session(
    session_id_uuid,
    workspace_id=chat_request.context.workspace_id,
    user_id=user_id,
)
```

**Integration Points**:
- `ai_chat.py:chat()` — primary caller
- `ai_chat.py:chat_abort()` — also needs ownership check
- `ai_chat.py:chat_answer()` — also needs ownership check

**Test Cases**:
1. Valid session_id + matching workspace/user → returns session
2. Valid session_id + wrong workspace → returns None (403-equivalent)
3. Valid session_id + wrong user → returns None
4. Invalid session_id → returns None (existing behavior)
5. No workspace_id/user_id passed → skips validation (backward compat)

---

### T2: Vault-Based API Key Retrieval (#46)

**Problem**: `pilotspace_agent.py:205-223` always returns `os.getenv("ANTHROPIC_API_KEY")` regardless of `workspace_id`. In BYOK model, each workspace should have its own API key stored in Supabase Vault (DD-060).

**Data Flow (Current)**:
```
_get_api_key(workspace_id="ws-1")
  → os.getenv("ANTHROPIC_API_KEY")   # Same key for ALL workspaces
```

**Data Flow (Target)**:
```
_get_api_key(workspace_id="ws-1")
  → SecureKeyStorage.get_key("ws-1", "anthropic_api_key")
    → Supabase Vault (AES-256-GCM)
    → Decrypted key for ws-1
  → Fallback: os.getenv("ANTHROPIC_API_KEY") if Vault unavailable
```

**Fix**:
```python
# pilotspace_agent.py — modify _get_api_key()
async def _get_api_key(self, workspace_id: UUID | None) -> str:
    if workspace_id and self._key_storage:
        try:
            key = await self._key_storage.get_key(
                workspace_id=workspace_id,
                key_name="anthropic_api_key",
            )
            if key:
                return key
        except Exception:
            logger.warning(
                "Vault lookup failed for workspace %s, falling back to env var",
                workspace_id,
            )

    # Fallback to environment variable
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        msg = "Anthropic API key not found"
        raise ValueError(msg)
    return api_key
```

**Dependency**: Requires `SecureKeyStorage` interface. If not yet implemented, create interface + env-var adapter:

```python
# ai/sdk/key_storage.py (new file if needed)
class SecureKeyStorage(Protocol):
    async def get_key(self, workspace_id: UUID, key_name: str) -> str | None: ...

class EnvVarKeyStorage:
    """Fallback: reads from environment variables."""
    async def get_key(self, workspace_id: UUID, key_name: str) -> str | None:
        return os.getenv("ANTHROPIC_API_KEY")
```

**Security Considerations**:
- Keys never logged (even at DEBUG level)
- Keys never stored in session/message metadata
- Vault access audited via Supabase audit log
- Circuit breaker on Vault calls (prevent cascade on Vault outage)

**Test Cases**:
1. Workspace has Vault key → returns Vault key
2. Workspace has no Vault key → falls back to env var
3. Vault service unavailable → falls back to env var (graceful degradation)
4. No env var and no Vault key → raises ValueError

---

## Phase 2: High-ROI SDK Features (P1) — Tasks #47–#51

### T3: Structured Output Schema for Skills (#47)

**Problem**: Skills (extract-issues, decompose-tasks, find-duplicates) return free text that gets parsed by the frontend. Schema mismatches cause silent data loss.

**Current Flow**:
```
Skill invocation → SDK generates free-text JSON
  → transform_sdk_message() tries to parse
  → structured_result SSE (if parseable)
  → Frontend StructuredResultCard renders
```

**Target Flow**:
```
Skill invocation → SDK enforces JSON schema via output_format
  → Guaranteed valid JSON matching Pydantic model
  → structured_result SSE
  → Frontend StructuredResultCard renders (no parse errors)
```

**Implementation**: Add skill-to-schema mapping in `pilotspace_agent.py`:

```python
# Skill → output_format mapping
SKILL_OUTPUT_SCHEMAS: ClassVar[dict[str, dict[str, Any]]] = {
    "extract-issues": {
        "type": "object",
        "properties": {
            "issues": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "description": {"type": "string"},
                        "issue_type": {"type": "string", "enum": ["bug", "feature", "task", "improvement"]},
                        "priority": {"type": "string", "enum": ["urgent", "high", "medium", "low", "none"]},
                        "source_block_id": {"type": ["string", "null"]},
                        "category": {"type": "string", "enum": ["explicit", "implicit", "related"]},
                    },
                    "required": ["title", "description", "issue_type", "priority", "category"],
                },
            },
            "summary": {"type": "string"},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        },
        "required": ["issues", "summary", "confidence"],
    },
    "decompose-tasks": {
        "type": "object",
        "properties": {
            "subtasks": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "description": {"type": "string"},
                        "story_points": {"type": "integer", "enum": [1, 2, 3, 5, 8, 13]},
                        "depends_on": {"type": "array", "items": {"type": "integer"}},
                    },
                    "required": ["title", "description", "story_points"],
                },
            },
            "total_points": {"type": "integer"},
        },
        "required": ["subtasks", "total_points"],
    },
    "find-duplicates": {
        "type": "object",
        "properties": {
            "candidates": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "issue_id": {"type": "string"},
                        "issue_key": {"type": "string"},
                        "title": {"type": "string"},
                        "similarity_score": {"type": "number", "minimum": 0, "maximum": 1},
                        "reason": {"type": "string"},
                    },
                    "required": ["issue_id", "title", "similarity_score", "reason"],
                },
            },
        },
        "required": ["candidates"],
    },
}
```

**Wire into SDK config** in `_stream_with_space()`:
```python
# Detect skill invocation from message metadata or slash command
skill_name = input_data.metadata.get("skill_invoked") if input_data.metadata else None
output_format = self.SKILL_OUTPUT_SCHEMAS.get(skill_name) if skill_name else None

sdk_config = configure_sdk_for_space(
    space_context,
    ...
    output_format=output_format,  # SDK enforces schema
)
```

**Test Cases**:
1. extract-issues skill → output_format set → SDK returns valid schema
2. Regular chat message → output_format is None → no constraint
3. Unknown skill → output_format is None → free text

---

### T4: File Checkpointing for Note Mutations (#48)

**Problem**: When the agent modifies a note via MCP tools and the user rejects the approval, there's no way to revert the filesystem changes in the sandbox.

**Fix**: Enable SDK-native file checkpointing in `configure_sdk_for_space()`:

```python
sdk_config = configure_sdk_for_space(
    space_context,
    ...
    enable_file_checkpointing=True,  # SDK creates checkpoints before file writes
)
```

The `enable_file_checkpointing` field already exists in `SDKConfiguration` (line 223) and is wired in `to_sdk_params()` (line 268-269). Just need to set it to `True` in the `configure_sdk_for_space()` call.

**Integration with Approval Flow**: On approval rejection, the SDK automatically reverts to the last checkpoint. No additional code needed — the SDK handles this natively.

**Test Cases**:
1. SDK config includes `enable_file_checkpointing: True`
2. Note tool writes file → checkpoint created (SDK behavior)
3. Approval rejected → file reverted to checkpoint (SDK behavior)

---

### T5: PostToolUse Audit via SDK Hook (#49)

**Problem**: `tool_audit` SSE events are emitted manually in `transform_sdk_message()` with estimated durations. SDK has a native `PostToolUse` hook that provides actual execution duration.

**Current**:
```
tool_result message → transform manually builds tool_audit SSE
```

**Target**:
```
SDK PostToolUse hook fires → callback emits tool_audit SSE to event_queue
```

**Implementation** in `hooks.py`:

```python
# Add to PermissionAwareHookExecutor.to_sdk_hooks()
def _create_post_tool_callback(self) -> Callable:
    event_queue = self._event_queue

    async def post_tool_callback(
        tool_use_id: str,
        tool_name: str,
        tool_input: dict[str, Any],
        tool_result: Any,
        duration_ms: float | None,
    ) -> dict[str, Any]:
        audit_data = {
            "tool_use_id": tool_use_id,
            "tool_name": tool_name,
            "input_summary": json.dumps(tool_input, default=str)[:200],
            "output_summary": str(tool_result)[:200],
            "duration_ms": duration_ms,
        }
        event = f"event: tool_audit\ndata: {json.dumps(audit_data)}\n\n"
        if event_queue:
            await event_queue.put(event)
        return {}  # No modification

    return post_tool_callback
```

Register in `to_sdk_hooks()`:
```python
hooks["PostToolUse"] = [{
    "matcher": ".*",
    "hooks": [self._create_post_tool_callback()],
}]
```

**Test Cases**:
1. Tool executes → PostToolUse fires → tool_audit SSE emitted with real duration
2. Tool fails → PostToolUse fires → tool_audit with error info

---

### T6: TodoWrite/TodoRead → TaskPanel Wiring (#50)

**Problem**: SDK's TodoWrite/TodoRead tools are in `base_tools` but their results aren't mapped to `task_progress` SSE events. Frontend TaskPanel already handles `task_progress`.

**Implementation** in `pilotspace_agent_helpers.py`:

Add detection in `transform_tool_result()`:
```python
def transform_tool_result(message: Message) -> str | None:
    result_data = getattr(message, "result", {})
    tool_use_id = getattr(message, "tool_use_id", "")
    tool_name = getattr(message, "tool_name", "")

    # Map TodoWrite results to task_progress events
    if tool_name in ("TodoWrite", "mcp__TodoWrite"):
        return _transform_todo_to_task_progress(result_data, tool_use_id)

    # ... existing logic ...
```

Helper function:
```python
def _transform_todo_to_task_progress(
    result_data: Any, tool_use_id: str
) -> str | None:
    if not isinstance(result_data, dict):
        return None

    todos = result_data.get("todos", [])
    events = []
    for todo in todos:
        task_data = {
            "taskId": todo.get("id", str(uuid4())),
            "subject": todo.get("content", "Task"),
            "status": _map_todo_status(todo.get("status", "pending")),
            "progress": 100 if todo.get("status") == "completed" else 0,
        }
        events.append(
            f"event: task_progress\ndata: {json.dumps(task_data)}\n\n"
        )
    return "".join(events) if events else None


def _map_todo_status(status: str) -> str:
    return {
        "pending": "pending",
        "in_progress": "in_progress",
        "completed": "completed",
        "done": "completed",
    }.get(status, "pending")
```

**Test Cases**:
1. TodoWrite result → task_progress SSE events emitted
2. TodoRead result → no SSE (read-only, no progress change)
3. Empty todos list → no SSE emitted

---

### T7: Dynamic Effort Parameter (#51)

**Problem**: All queries use the same effort level regardless of complexity. Simple greetings ("Hi", "What can you do?") could use `effort: "low"` for ~40% latency reduction.

**Implementation** in `pilotspace_agent.py`:

```python
# Query complexity classifier
SIMPLE_PATTERNS: ClassVar[list[str]] = [
    r"^(hi|hello|hey|thanks|thank you|ok|okay)\b",
    r"^what (can you|do you) do",
    r"^help\b",
    r"^(yes|no|sure|yep|nope)\b",
]

@staticmethod
def _classify_effort(message: str) -> str | None:
    """Classify query effort level. Returns None for default (no effort param)."""
    import re
    msg_lower = message.strip().lower()

    # Short simple messages → low effort
    if len(msg_lower) < 50:
        for pattern in PilotSpaceAgent.SIMPLE_PATTERNS:
            if re.match(pattern, msg_lower):
                return "low"

    # Messages with skill invocations or complex analysis → default
    return None
```

Wire into `_stream_with_space()`:
```python
effort = self._classify_effort(input_data.message)

sdk_config = configure_sdk_for_space(
    space_context,
    ...
    effort=effort,  # None = default, "low" = fast
)
```

**Test Cases**:
1. "Hi" → effort="low"
2. "Extract issues from this note" → effort=None (default)
3. Long complex prompt → effort=None

---

## Phase 3: UX Enhancements (P2) — Tasks #52, #53

### T8: Implement setProjectContext() (#52)

**Problem**: `PilotSpaceStore.ts:524-527` is a no-op stub. Project context not available to AI.

**Implementation**:

Add observable state:
```typescript
// PilotSpaceStore.ts — add to observable state
@observable projectContext: { projectId: string; name?: string; slug?: string } | null = null;
```

Implement the method:
```typescript
setProjectContext(context: { projectId: string; name?: string; slug?: string } | null): void {
  this.projectContext = context;
}
```

Update `conversationContext` computed:
```typescript
get conversationContext(): ConversationContext {
  return {
    workspaceId: this.workspaceId ?? '',
    noteId: this.noteContext?.noteId ?? null,
    issueId: this.issueContext?.issueId ?? null,
    projectId: this.projectContext?.projectId ?? null,  // Now populated
    selectedText: this.noteContext?.selectedText ?? null,
    selectedBlockIds: this.noteContext?.selectedBlockIds ?? [],
  };
}
```

Update `clearContext()`:
```typescript
clearContext(): void {
  this.noteContext = null;
  this.issueContext = null;
  this.projectContext = null;  // Add
}
```

**Test Cases**:
1. setProjectContext({projectId: "p1"}) → projectContext stored
2. conversationContext.projectId reflects stored value
3. clearContext() clears projectContext

---

### T9: Implement setActiveSkill() + addMentionedAgent() (#53)

**Problem**: Both methods are console.log stubs. Skill/agent context not tracked.

**Implementation**:

Add observable state:
```typescript
@observable activeSkill: { name: string; args?: string } | null = null;
@observable mentionedAgents: string[] = [];
```

Implement methods:
```typescript
setActiveSkill(skill: string, args?: string): void {
  this.activeSkill = { name: skill, args };
}

addMentionedAgent(agent: string): void {
  if (!this.mentionedAgents.includes(agent)) {
    this.mentionedAgents.push(agent);
  }
}
```

Wire into `sendMessage()` metadata in `PilotSpaceActions.ts`:
```typescript
const metadata: MessageMetadata = {};
if (this.store.activeSkill) {
  metadata.skillInvoked = this.store.activeSkill.name;
}
if (this.store.mentionedAgents.length > 0) {
  metadata.agentMentioned = this.store.mentionedAgents[0];
}
```

Clear on message send:
```typescript
// After sending, reset transient state
runInAction(() => {
  this.store.activeSkill = null;
  this.store.mentionedAgents = [];
});
```

**Test Cases**:
1. setActiveSkill("extract-issues") → activeSkill stored
2. addMentionedAgent("pr-review") → added to array (no duplicates)
3. sendMessage includes skill/agent in metadata
4. After send, activeSkill and mentionedAgents reset

---

## Execution Order & Dependencies

```
Week 1 (P0 — Security):
  #45 Session ownership ──────────► commit
  #46 Vault key retrieval ────────► commit

Week 2 (P1 — SDK Features):
  #47 Structured output ─► (blocked by #45 for test pattern)
  #48 File checkpointing ─► (independent)
  #49 PostToolUse hook ───► (independent)
  #50 Todo → TaskPanel ──► (independent)
  #51 Effort parameter ──► (independent)
  All 5 can be parallelized, commit together

Week 3 (P2 — UX):
  #52 Project context ───► (independent)
  #53 Skill/agent tracking ► (independent)
  Both can be parallelized, commit together
```

---

## Quality Gates Per Phase

**Each phase must pass before merging**:

```bash
# Backend
uv run pyright src/pilot_space/ai/  # 0 new errors
uv run ruff check src/pilot_space/ai/
uv run pytest tests/unit/ai/sdk/ -v --tb=short  # All pass

# Frontend
pnpm lint
pnpm type-check  # Scoped to modified files
pnpm vitest run src/stores/ai/  # All pass
```

**File size check**: No file exceeds 700 lines after modifications.

---

## Security Considerations Summary

| Task | Security Impact | Mitigation |
|------|----------------|------------|
| #45 | Session hijacking | Ownership validation + return None (no info leak) |
| #46 | Shared API key across workspaces | Per-workspace Vault keys + fallback |
| #47 | Schema injection via output_format | Schemas are hardcoded, not user-provided |
| #48 | File system state after rejection | SDK-native checkpoint revert |
| #49 | Audit log completeness | SDK-native timing replaces estimates |
| #50 | Task data exposure | Tasks scoped to session (already isolated) |
| #51 | Model behavior change | Effort only reduces reasoning depth, not safety |
| #52 | Context leakage | Project context scoped to workspace (RLS) |
| #53 | Metadata tracking | Transient state, cleared after send |

---

## Rollback Strategy

Each task modifies isolated code paths. If any task causes regression:

1. **Revert commit** — Each phase is a single commit
2. **Feature flags** — Tasks #48 (checkpointing), #51 (effort), #47 (structured output) can be disabled via SDKConfiguration defaults without code changes
3. **Backward compatibility** — #45 uses optional params with `None` defaults, existing callers unaffected

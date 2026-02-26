# Pilot Space Agent: Claude Agent SDK Integration

> **Location**: `backend/src/pilot_space/ai/sdk/`
> **Design Decisions**: DD-002 (BYOK + Claude Agent SDK), DD-003 (Human-in-the-Loop)

## Overview

The SDK layer is the **bridge between PilotSpaceAgent and the Claude Agent SDK**. It adapts Pilot Space's security model (BYOK, RLS, workspace roles, approval workflow) to the SDK's execution model (tool calls, hooks, sessions, commands). This layer is intentionally separate from the orchestrator to enable independent evolution and modular testing.

The SDK executes inside the same Python process (no external daemon) — MCP servers are in-process objects registered at SDK initialization, not network services.

---

## Architecture

```
PilotSpaceAgent (orchestrator)
       ↓ initializes with:
sdk/config.py          ← SDK configuration factory (model, BYOK key, sandbox)
sdk/session_handler.py ← multi-turn conversation state
sdk/session_store.py   ← Redis + PostgreSQL dual persistence
       ↓ SDK runs tools, fires hooks:
sdk/hooks.py           ← pre-tool permission check + subagent progress
sdk/hooks_lifecycle.py ← post-tool audit, input validation, budget enforcement
sdk/hook_executor.py   ← file-based hook system execution
sdk/hook_models.py     ← hook data models
sdk/file_hooks.py      ← YAML-configured hooks for tool events
sdk/permission_handler.py ← DD-003: approval classification for 100+ actions
sdk/approval_waiter.py ← async polling wait for user approval decision
sdk/command_registry.py ← slash command discovery from .claude/commands/*.md
sdk/question_adapter.py ← user question handling (QuestionBlock UI)
sdk/sandbox_config.py  ← agent filesystem isolation
sdk/output_schemas.py  ← structured output schemas with DAG validation
sdk/sse_transformer.py ← SDK internal events → 14 frontend SSE event types
```

---

## `config.py` — SDK Configuration Factory

**Responsibility**: Build the `ClaudeCodeConfig` (or equivalent SDK config object) for each agent invocation.

**Assembled from**:
- **Model**: Resolved via `ProviderSelector` (task-type routing, DD-011)
- **API key**: Decrypted BYOK from `SecureKeyStorage` (workspace vault)
- **Sandbox path**: `/sandbox/{user_id}/{workspace_id}/` (isolated per user+workspace)
- **Max tokens**: From `token_limits.py` (8K per session default)
- **Tool servers**: All MCP servers registered as in-process tools

**BYOK resolution**: If workspace has no stored key → falls back to deployment-level env var → if neither, raises `HTTP 402 Payment Required`.

---

## `session_handler.py` / `session_store.py` — Session Persistence

**Responsibility**: Make multi-turn conversations survive page refreshes and server restarts.

**Dual storage**:

| Storage | TTL | Purpose |
|---------|-----|---------|
| Redis | 30-min sliding | Hot path: <1ms lookup during active conversation |
| PostgreSQL | 24h (optional) | Durable recovery across deployments |

**Session loading for multi-turn**:
1. Request arrives with `session_id`
2. `session_handler.load_messages(session_id)` → Redis lookup → returns `list[AIMessage]`
3. Messages reconstructed as SDK `conversation_history` parameter
4. SDK continues conversation with full prior context

**TTL sliding**: Every new message extends Redis TTL by 30min from now. Active conversations never expire mid-session.

**`session_store.py`**: Raw Redis/PostgreSQL I/O — serialize/deserialize `AISession` dataclasses to JSON, handle TTL management, index by `(user_id, agent_name, context_id)` for session lookup.

---

## `hooks.py` / `hooks_lifecycle.py` — SDK Hook System

**Responsibility**: Intercept SDK tool call lifecycle for permission checking, audit logging, and token budget enforcement.

### Hook Types

| Hook | When | Action |
|------|------|--------|
| `PreToolHook` | Before tool executes | DD-003 permission check — block if needs approval |
| `PostToolHook` | After tool completes | Audit log, cost delta update, SSE result event |
| `StopHook` | On streaming stop | Flush delta buffer, record session cost |
| `CompactHook` | On history compaction | Summarize old turns to fit token budget |

### `hooks_lifecycle.py` — Advanced Hook Logic

**Input validation hook**: Validates tool input against `ToolInputSchema` before execution. Prevents malformed inputs from reaching MCP handlers (e.g., invalid UUIDs, missing required fields).

**Budget enforcement hook**: Checks `context.token_budget_remaining` before each tool call. If < 500 tokens remaining, emits `budget_warning` SSE event. If < 100, cancels execution.

**Subagent progress hook**: When a subagent (`@pr-review`, `@doc-generator`) is dispatched, emits `task_progress` SSE events back through the orchestrator's stream.

---

## `hook_executor.py` / `hook_models.py` / `file_hooks.py` — File-Based Hooks

**Responsibility**: Execute hooks defined in `.claude/hooks.json` — a YAML-configured policy file in the agent sandbox that non-engineers can edit.

**Why file-based hooks?** Workspace admins can configure automation rules (e.g., "always run tests before committing code", "require approval for delete operations in production") without changing Python code.

**Hook definition example** (`.claude/hooks.json`):
```json
{
  "hooks": [
    {
      "event": "pre_tool_call",
      "tool_name": "issue.delete_issue",
      "action": "require_approval",
      "message": "Deleting issues requires admin approval"
    }
  ]
}
```

**`hook_executor.py`**: Reads parsed hook models, evaluates conditions, executes action (`require_approval`, `block`, `log`, `notify`).

---

## `permission_handler.py` — DD-003 Approval Classification

**Responsibility**: Classify every tool call into one of 3 approval tiers.

**3-tier classification**:

| Tier | Condition | SDK behavior |
|------|-----------|-------------|
| `AUTO_EXECUTE` | Read-only, suggestions, reversible | Proceed immediately |
| `DEFAULT` | Content creation, updates | Emit `approval_request` SSE, block |
| `CRITICAL` | Destructive (delete, merge, archive) | Emit `approval_request` + open blocking modal |

**100+ actions mapped**. Examples:

| Tool | Tier |
|------|------|
| `note.read_note` | AUTO_EXECUTE |
| `issue.create_issue` | DEFAULT |
| `issue.update_issue` | DEFAULT |
| `issue.delete_issue` | CRITICAL |
| `note.update_note` | DEFAULT |
| `issue_relation.merge_pr` | CRITICAL |
| `project.archive_workspace` | CRITICAL |
| `comment.post_comment` | DEFAULT |

**Why at SDK boundary?** The permission handler sits between the SDK's tool execution and the actual MCP handler. This ensures approval is enforced regardless of which code path triggers the tool — orchestrator, subagent, or slash command.

---

## `approval_waiter.py` — Blocking Approval Wait

**Responsibility**: Suspend SDK execution until the user approves or rejects a tool call.

**Mechanism** — async polling loop:
```
1. Emit approval_request SSE event (with approval_id, action, payload)
2. Poll PostgreSQL every 2s for approval resolution:
   SELECT status FROM ai_approvals WHERE id = {approval_id}
3. If status = 'approved' → resume SDK execution
4. If status = 'rejected' → raise ApprovalRejectedError (tool cancelled)
5. If 5 minutes elapse → auto-reject (timeout = safe default)
```

**Why polling, not WebSocket push?** The SDK runs in a background async task. A push notification would require cross-task signaling (asyncio.Event across tasks). Polling with a 2s interval is simpler, reliable, and the 2s delay is unnoticeable compared to the human decision time.

**Fresh DB session per poll**: Each poll uses a new database session to avoid holding a connection across the 5-minute wait window.

---

## `command_registry.py` — Slash Command Discovery

**Responsibility**: Discover available slash commands from the agent sandbox's `.claude/commands/` directory and map them to skill executors.

**Discovery**: On agent initialization, scans `/sandbox/{user_id}/{workspace_id}/.claude/commands/*.md`. Each Markdown file is a command definition (name = filename, description = file content frontmatter).

**Dispatch**: When user sends `\extract-issues from my notes`, `CommandRegistry.dispatch("extract-issues", args)` → `SkillExecutor.run("extract-issues", parsed_args)`.

**Why Markdown command files?** Claude Agent SDK natively reads `.claude/commands/*.md` for slash command definitions. Using this convention keeps the SDK's native discovery mechanism working without a separate registry API.

---

## `question_adapter.py` — AI Question Handling

**Responsibility**: When the SDK needs clarification from the user, route the question through the frontend's `QuestionBlock` UI and wait for the answer.

**Flow**:
```
SDK asks question (e.g., "Which issues should I prioritize?")
    ↓
QuestionAdapter.ask(question_text, options, required)
    ↓
Emits `question_request` SSE event → QuestionBlock renders in MessageList
    ↓
User selects answer → POST /api/v1/ai/questions/{id}/answer
    ↓
QuestionAdapter.await_answer(question_id) returns answer
    ↓
SDK continues with answer injected into conversation
```

**In-memory registry**: `{question_id: asyncio.Future}` — the Future is resolved when the answer arrives. A cleanup task removes stale futures after 30 minutes (prevents memory leak on abandoned questions).

**Two-turn model**: Question + answer are a complete round-trip. The answer is injected back as a user message in the SDK conversation history, maintaining conversational coherence.

---

## `sandbox_config.py` — Agent Filesystem Isolation

**Responsibility**: Define the filesystem sandbox for each agent invocation.

**Sandbox structure**:
```
/sandbox/{user_id}/{workspace_id}/
├── .claude/
│   ├── skills/         ← materialized skill YAML files
│   ├── commands/       ← slash command Markdown files
│   ├── hooks.json      ← file-based hook policies
│   └── CLAUDE.md       ← agent instructions + context
└── notes/              ← note file mirrors (for file-based operations)
```

**Allowed paths**: Only the user's sandbox directory tree. The SDK cannot read `/etc/`, `/home/other_user/`, or other workspaces' sandboxes.

**Dangerous pattern detection**: `sandbox_config.py` defines regex patterns for shell injection, path traversal (`../`), and other dangerous inputs. The SDK validates tool inputs against these before execution.

**Model tier config**: Per-sandbox model constraints — guest sandboxes cannot use Opus (cost control), admin sandboxes have full access.

---

## `output_schemas.py` — Structured Output Types

**Responsibility**: Define Pydantic schemas for all structured AI outputs, with DAG validation for outputs that have dependency relationships (e.g., task decomposition with prerequisite tasks).

**Output types**:
- `IssueExtractionOutput` — list of `IssueCandidate` with confidence scores
- `TaskDecompositionOutput` — `AgentTask[]` with dependency edges
- `PRReviewOutput` — `ReviewComment[]` with severity and file/line references
- `DiagramOutput` — Mermaid/PlantUML source string
- `DocumentationOutput` — Markdown sections
- `StandupOutput` — formatted standup text

**DAG validation**: `TaskDecompositionOutput.validate_dag()` checks that task dependency graph has no cycles. Prevents the agent from generating impossible task orderings (e.g., "implement auth → design auth schema → implement auth").

---

## `sse_transformer.py` — SDK Events → Frontend SSE

**Responsibility**: Transform SDK's internal event stream into the 14 SSE event types the frontend's `PilotSpaceStreamHandler` consumes.

**14 SSE event types emitted**:

| SSE Event | Trigger |
|-----------|---------|
| `message_start` | SDK conversation begins |
| `text_delta` | Text token arrives |
| `thinking_delta` | Extended thinking token arrives |
| `tool_use` | SDK calls MCP tool |
| `tool_result` | MCP tool returns result |
| `task_progress` | Subagent step completes |
| `approval_request` | Tool needs human approval |
| `skill_approval_request` | Skill execution needs approval |
| `intent_detected` | Intent classifier identifies intent |
| `intent_confirmed` | User confirms intent |
| `question_request` | SDK needs clarification |
| `citations` | Sources referenced |
| `budget_warning` | Token budget < 500 |
| `message_stop` | Streaming complete |

**SSE format**: `data: {json}\n\n` (Server-Sent Events spec). Each event includes `event_type`, `session_id`, `timestamp`, and event-specific payload.

---

## Implicit Features

| Feature | Mechanism | File |
|---------|-----------|------|
| Approval auto-reject after 5min | Timeout in polling loop | `approval_waiter.py` |
| Permission check at SDK boundary | `PreToolHook` fires before every tool call | `hooks.py` |
| Token budget warning SSE | `hooks_lifecycle.py` checks remaining budget | `hooks_lifecycle.py` |
| Question Future cleanup (30min) | Background asyncio task | `question_adapter.py` |
| DAG cycle detection in task output | `validate_dag()` on structured output | `output_schemas.py` |
| File hook policies (non-code) | `.claude/hooks.json` YAML config | `file_hooks.py` |
| Sandbox path traversal prevention | Regex check on all tool inputs | `sandbox_config.py` |
| Session sliding TTL on message | `session_store.update()` resets TTL | `session_store.py` |
| Command discovery from filesystem | `CommandRegistry` scans `.claude/commands/` | `command_registry.py` |
| In-process MCP (no network) | MCP servers registered as Python objects | `config.py` |

---

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| SDK layer separate from orchestrator | Independent evolution — SDK API changes don't require orchestrator rewrites. Modular testing. |
| In-process MCP servers | No network roundtrip for tool calls. Eliminates 10-50ms latency per tool, enables RLS context sharing via Python objects. |
| Polling for approval (not push) | SDK runs in async background task. Cross-task push requires asyncio.Event coordination. 2s poll is simpler and unnoticeable vs. human decision time. |
| Permission check at SDK boundary | Approval enforcement regardless of call path (orchestrator / subagent / slash command). |
| File-based hooks | Workspace admins can configure automation policy without Python code changes. |
| Question as 2-turn conversation | Injects answer as user message → maintains SDK conversation coherence. No SDK special-casing needed. |
| Auto-reject timeout 5min (not auto-approve) | Timeout failure must be safe. Auto-approve on timeout could execute destructive actions unattended. |

---

## Files Reference

| File | Lines | Purpose |
|------|-------|---------|
| `sdk/config.py` | ~150 | SDK config factory (BYOK, model, sandbox, tools) |
| `sdk/session_handler.py` | ~200 | Multi-turn session loading + updating |
| `sdk/session_store.py` | ~250 | Redis + PG dual storage |
| `sdk/hooks.py` | ~180 | Pre/post tool hooks + subagent progress |
| `sdk/hooks_lifecycle.py` | ~220 | Input validation, budget enforcement, audit |
| `sdk/hook_executor.py` | ~150 | File-based hook policy execution |
| `sdk/hook_models.py` | ~100 | Hook event data models |
| `sdk/file_hooks.py` | ~120 | `.claude/hooks.json` parser |
| `sdk/permission_handler.py` | ~300 | 100+ action → approval tier mapping |
| `sdk/approval_waiter.py` | ~150 | Async 2s-poll approval wait (5min timeout) |
| `sdk/command_registry.py` | ~130 | Slash command discovery + dispatch |
| `sdk/question_adapter.py` | ~160 | Question SSE + Future-based await |
| `sdk/sandbox_config.py` | ~180 | Filesystem isolation + dangerous patterns |
| `sdk/output_schemas.py` | ~200 | Pydantic output types + DAG validation |
| `sdk/sse_transformer.py` | ~120 | SDK events → 14 SSE types |

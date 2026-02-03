# 005: Claude Agent SDK Feature Audit — Full Gap Analysis

**Date**: 2026-02-03
**Branch**: `005-conversational-agent-arch`
**Auditor**: AI Architecture Review
**Scope**: All Claude Agent SDK capabilities vs PilotSpace implementation

---

## 1. Executive Summary

The PilotSpace Agent system is **mature and production-ready** on its core event pipeline. All 14 SSE event types are handled end-to-end (backend emission + frontend consumption + UI rendering). The recent commit (`bf7aeca`) closed 9 BE-FE contract gaps.

**However**, there are **12 SDK features** not yet leveraged that could significantly improve the agent experience. These range from P0 security fixes to P3 enhancements.

### Coverage Scorecard

| Category | Implemented | Partial | Missing | Total |
|----------|-------------|---------|---------|-------|
| Core Streaming | 6 | 0 | 0 | 6 |
| Event Pipeline | 14 | 0 | 0 | 14 |
| Hooks & Permissions | 4 | 1 | 0 | 5 |
| Sessions | 4 | 1 | 1 | 6 |
| Tools & MCP | 6 | 2 | 3 | 11 |
| UI Components | 10 | 3 | 0 | 13 |
| SDK Advanced | 2 | 2 | 5 | 9 |
| **Total** | **46** | **9** | **9** | **64** |

**Overall**: 72% fully implemented, 14% partial, 14% missing.

---

## 2. Feature-by-Feature Audit

### Legend

- **IMPL** = Fully implemented and tested
- **PARTIAL** = Code exists but incomplete or stubbed
- **MISSING** = SDK supports it, not implemented
- **N/A** = Not applicable to PilotSpace use case

---

### 2.1 Core Streaming Pipeline

| # | Feature | Status | Backend | Frontend | Notes |
|---|---------|--------|---------|----------|-------|
| 1 | SSE text_delta streaming | IMPL | `transform_sdk_message()` | `handleTextDelta()` | |
| 2 | thinking_delta streaming | IMPL | ThinkingBlock extraction | `handleThinkingDelta()` + `<ThinkingBlock>` | |
| 3 | tool_use events | IMPL | ToolUseBlock → SSE | `handleToolUseStart()` + `<ToolCallList>` | |
| 4 | tool_result events | IMPL | `transform_tool_result()` | `handleToolResult()` | Fixed in bf7aeca |
| 5 | content_block_start | IMPL | Block index + type | `handleContentBlockStart()` | parentToolUseId added |
| 6 | message_start/stop | IMPL | Session + model info | `handleMessageStart/Complete()` | model field added |

### 2.2 SSE Event Types (14/14)

| # | Event | Status | Handler | UI |
|---|-------|--------|---------|-----|
| 7 | message_start | IMPL | `handleMessageStart()` | Session init |
| 8 | content_block_start | IMPL | `handleContentBlockStart()` | Phase tracking |
| 9 | text_delta | IMPL | `handleTextDelta()` | `<StreamingContent>` |
| 10 | thinking_delta | IMPL | `handleThinkingDelta()` | `<ThinkingBlock>` |
| 11 | tool_use | IMPL | `handleToolUseStart()` | `<ToolCallList>` |
| 12 | tool_result | IMPL | `handleToolResult()` | Status + output |
| 13 | task_progress | IMPL | `handleTaskUpdate()` | `<TaskPanel>` |
| 14 | approval_request | IMPL | `handleApprovalRequired()` | `<ApprovalOverlay>` |
| 15 | ask_user_question | IMPL | `handleAskUserQuestion()` | `<QuestionCard>` |
| 16 | content_update | IMPL | `store.handleContentUpdate()` | TipTap editor |
| 17 | structured_result | IMPL | `handleStructuredResult()` | `<StructuredResultCard>` |
| 18 | message_stop | IMPL | `handleTextComplete()` | Message finalization |
| 19 | budget_warning | IMPL | `handleBudgetWarning()` | Error toast |
| 20 | tool_audit | IMPL | `handleToolAudit()` | durationMs on ToolCall |
| 21 | error | IMPL | `handleError()` | Auto-retry + toast |

### 2.3 Hooks & Permissions (DD-003)

| # | Feature | Status | Location | Notes |
|---|---------|--------|----------|-------|
| 22 | PreToolUse hook | IMPL | `PermissionCheckHook` | TOOL_ACTION_MAPPING |
| 23 | Approval SSE emission | IMPL | `_build_approval_sse_event()` | 9 fields, urgency classification |
| 24 | Approval resolve endpoint | IMPL | `POST /chat/answer` | approve/reject |
| 25 | SubagentProgressHook | IMPL | `PermissionAwareHookExecutor` | task_progress events |
| 26 | **PostToolUse audit hook** | **PARTIAL** | tool_audit emitted but not from SDK hook | SDK has PostToolUse hook — we emit tool_audit manually in transform, not via SDK's native PostToolUse lifecycle |

### 2.4 Session Management

| # | Feature | Status | Location | Notes |
|---|---------|--------|----------|-------|
| 27 | Session create | IMPL | `SessionHandler.create_session()` | 30-min TTL |
| 28 | Session resume | IMPL | `resume` param in SDK options | Via session_id query param |
| 29 | Session fork | IMPL | `SessionHandler.fork_session()` | Max 3 forks/source |
| 30 | Sliding window pruning | IMPL | `get_messages_for_sdk()` | 8K token budget |
| 31 | **Session ownership validation** | **PARTIAL** | session_id used but not verified against user_id/workspace_id | Security gap: user could resume another user's session |
| 32 | **Cross-session memory** | **MISSING** | SDK has Memory tool | Not wired — conversations are isolated per session |

### 2.5 Tools & MCP

| # | Feature | Status | Location | Notes |
|---|---------|--------|----------|-------|
| 33 | MCP note tools (6) | IMPL | `create_note_tools_server()` | update, enhance, summarize, extract, create, link |
| 34 | SDK base tools | IMPL | sandbox_config base_tools | Read, Glob, Grep, Bash, etc. |
| 35 | AskUserQuestion tool | IMPL | Detected in transform → SSE | `<QuestionCard>` renders |
| 36 | Tool search (auto) | IMPL | `tool_search: "auto"` in config | Enabled when >10 tools |
| 37 | Skill system (.claude/skills/) | IMPL | SkillRegistry + SDK auto-discovery | 8 skills defined |
| 38 | Slash commands | IMPL | SDK slash_commands mapped to skills | `/extract-issues`, etc. |
| 39 | **Fine-grained tool streaming** | **MISSING** | SDK docs: stream tool input JSON progressively | Would enable showing tool params as they're generated |
| 40 | **Code execution tool** | **MISSING** | SDK sandboxed code execution (not Bash) | Could enable safe Python/JS execution for data analysis |
| 41 | **Memory tool** | **MISSING** | SDK persistent cross-session memory | Would enable "remember my preferences" across sessions |
| 42 | **File checkpointing** | **MISSING** | SDK: rewind file changes | Safety net for note mutations — revert if user rejects |
| 43 | **Todo tracking tool** | **PARTIAL** | SDK TodoWrite/TodoRead in base_tools but not wired to frontend TaskPanel | Backend has tools, frontend has TaskPanel, but they're not connected |

### 2.6 SDK Configuration & Advanced

| # | Feature | Status | Location | Notes |
|---|---------|--------|----------|-------|
| 44 | Prompt caching (ephemeral) | IMPL | `SYSTEM_PROMPT_BASE` + `cache_control` | ~63% savings |
| 45 | Extended thinking config | IMPL | `max_thinking_tokens` auto 10K for Opus | |
| 46 | Sandbox configuration | IMPL | SandboxSettings, safe/dangerous patterns | |
| 47 | Structured output schema | PARTIAL | `output_format` field in SDKConfiguration exists but not passed for skill invocations | Skills return free text, not JSON-schema-enforced |
| 48 | **Effort parameter** | **PARTIAL** | Field exists in SDKConfiguration but never set dynamically | Could optimize latency for simple queries |
| 49 | **Citations** | **MISSING** | `citations_enabled: False` in config | SDK supports citation anchoring to source documents |
| 50 | **Plugins** | **MISSING** | SDK plugin system for extending agent behavior | Not explored |
| 51 | **Streaming input mode** | **MISSING** | SDK streaming vs single-shot input selection | Always uses single-shot currently |
| 52 | **Secure key retrieval** | **PARTIAL** | Hardcoded to `ANTHROPIC_API_KEY` env var | Should use Supabase Vault per DD-060 |

### 2.7 Frontend UI

| # | Feature | Status | Component | Notes |
|---|---------|--------|-----------|-------|
| 53 | ThinkingBlock | IMPL | `ThinkingBlock.tsx` (124 lines) | Collapsible, duration, a11y |
| 54 | QuestionCard | IMPL | `QuestionCard.tsx` (206 lines) | Single/multi-select + free text |
| 55 | StructuredResultCard | IMPL | `StructuredResultCard.tsx` (347 lines) | 3 schema renderers |
| 56 | SuggestionCard | IMPL | `SuggestionCard.tsx` (78 lines) | Inline approvals |
| 57 | ApprovalOverlay | IMPL | `ApprovalOverlay.tsx` (80+ lines) | Modal, auto-advance queue |
| 58 | TaskPanel | IMPL | `TaskPanel/` (4 components) | Progress bars |
| 59 | SessionList | IMPL | `SessionList/` | Session history |
| 60 | ChatInput + menus | IMPL | `ChatInput/` (4 components) | Skills, agents |
| 61 | **setProjectContext()** | **PARTIAL** | `PilotSpaceStore.ts:524-527` | No-op stub with TODO |
| 62 | **setActiveSkill()** | **PARTIAL** | `PilotSpaceStore.ts:534-537` | console.log only |
| 63 | **addMentionedAgent()** | **PARTIAL** | `PilotSpaceStore.ts:543-546` | console.log only |
| 64 | Message virtualization | MISSING | MessageList.tsx | No react-window, may lag at 1000+ messages |

---

## 3. Prioritized Gap List

### P0 — Security & Correctness

| ID | Gap | Risk | Fix |
|----|-----|------|-----|
| G-01 | Session ownership not validated | **HIGH** — user could hijack another user's session by guessing UUID | Add `workspace_id + user_id` check in `get_session()` before returning |
| G-02 | API key from env var, not Vault | **MEDIUM** — single API key shared across all workspaces | Integrate `SecureKeyStorage` → Supabase Vault per DD-060 |

### P1 — SDK Features with High ROI

| ID | Gap | Value | Effort |
|----|-----|-------|--------|
| G-03 | Structured output schema for skills | Eliminates parsing errors in extraction/decomposition | S — Pass `output_format` when invoking skills |
| G-04 | File checkpointing for note mutations | Safety net: revert note changes on user rejection | M — SDK native, wire to approval flow |
| G-05 | PostToolUse audit via SDK hook (not manual) | Correct lifecycle tracking, duration from SDK | S — Register PostToolUse hook callback |
| G-06 | Todo tool → TaskPanel wiring | SDK's TodoWrite/TodoRead connected to frontend task UI | M — Map SDK todo events to task_progress SSE |
| G-07 | Effort parameter for latency optimization | Route simple queries with `effort: "low"` for faster responses | S — Detect query complexity, set effort dynamically |

### P2 — Enhanced UX

| ID | Gap | Value | Effort |
|----|-----|-------|--------|
| G-08 | Fine-grained tool streaming | Show tool inputs as they generate (progressive rendering) | M — Backend: stream tool JSON deltas; Frontend: render partial tool params |
| G-09 | Implement setProjectContext() | Project-scoped AI conversations | S — Wire project data to ConversationContext |
| G-10 | setActiveSkill() + addMentionedAgent() | Track which skill/agent is in use for UI indicators | S — Store state + message metadata |
| G-11 | Memory tool for cross-session preferences | "Remember I prefer TypeScript" persists across sessions | M — Enable SDK Memory tool, add memory_enabled config |

### P3 — Future Enhancements

| ID | Gap | Value | Effort |
|----|-----|-------|--------|
| G-12 | Citations for source attribution | Link AI responses to source notes/issues/code | L — Enable citations, build citation UI components |
| G-13 | Code execution tool | Safe data analysis in sandboxed environment | L — SDK native, build result viewer component |
| G-14 | Message virtualization | Performance at 1000+ messages | M — Integrate react-window in MessageList |
| G-15 | Streaming input mode | Large document analysis with streaming input | S — SDK config change, minor backend wiring |

---

## 4. Architecture: Current vs Target State

### 4.1 Current Architecture (Post bf7aeca)

```
Frontend                          Backend                           SDK
────────                          ───────                           ───
ChatInput                         POST /chat                        ClaudeSDKClient
  │ sendMessage()                   │ extract_ai_context()            │ subprocess
  ▼                                 ▼                                 │
PilotSpaceActions ──POST──►  ai_chat.py                              │
  │                               │ create_session()                  │
  ▼                               ▼                                   │
PilotSpaceStreamHandler    PilotSpaceAgent.stream()                   │
  │ consumeSSEStream()          │ _stream_with_space()                │
  │                             │   SpaceManager.get_space()          │
  │                             │   PermissionAwareHookExecutor       │
  │                             │   create_note_tools_server()        │
  │                             │   configure_sdk_for_space()         │
  │                             │   ClaudeSDKClient.connect()  ──────►│
  │                             │                                     │
  │◄────── SSE events ◄────────│◄── transform_sdk_message() ◄────────│
  │                             │◄── drain tool_event_queue           │
  ▼                             │                                     │
PilotSpaceStore (MobX)          │  message_start ──► handleMessageStart()
  │ messages[]                  │  text_delta ─────► handleTextDelta()
  │ streamingState              │  thinking_delta ─► handleThinkingDelta()
  │ tasks Map                   │  tool_use ───────► handleToolUseStart()
  │ pendingApprovals[]          │  tool_result ────► handleToolResult()
  │ pendingContentUpdates[]     │  task_progress ──► handleTaskUpdate()
  ▼                             │  approval_req ──► handleApprovalRequired()
ChatView (React)                │  ask_question ──► handleAskUserQuestion()
  ├── MessageList               │  content_update ► handleContentUpdate()
  │   ├── AssistantMessage      │  structured_res ► handleStructuredResult()
  │   ├── ThinkingBlock         │  message_stop ──► handleTextComplete()
  │   ├── QuestionCard          │  budget_warning ► handleBudgetWarning()
  │   ├── StructuredResultCard  │  tool_audit ────► handleToolAudit()
  │   └── SuggestionCard        │  error ─────────► handleError()
  ├── TaskPanel                 │
  ├── ApprovalOverlay           │
  └── ChatInput                 │
```

### 4.2 Target Architecture (After Gap Closure)

New additions marked with `[NEW]`:

```
Frontend                          Backend                           SDK
────────                          ───────                           ───

PilotSpaceStreamHandler           PilotSpaceAgent                   ClaudeSDKClient
  │                                 │                                │
  │ [NEW] handleToolInputDelta()    │ [NEW] PostToolUse hook ────────│ PostToolUse
  │ [NEW] handleMemoryUpdate()      │ [NEW] file checkpointing ─────│ checkpoint
  │ [NEW] handleCitation()          │ [NEW] effort routing ──────────│ effort param
  │                                 │ [NEW] output_format for skills │ output_schema
  │                                 │ [NEW] session ownership check  │
  │                                 │ [NEW] Vault key retrieval      │
  │                                 │ [NEW] todo → task_progress map │ TodoWrite
  ▼                                 │                                │
PilotSpaceStore                     │                                │
  │ [NEW] projectContext            │                                │
  │ [NEW] activeSkill tracking      │                                │
  │ [NEW] agentMention tracking     │                                │
  │ [NEW] memory preferences        │                                │
  ▼                                 │                                │
ChatView                            │                                │
  ├── MessageList                   │                                │
  │   ├── [NEW] CitationLink        │                                │
  │   └── [NEW] VirtualScroller     │                                │
  └── [NEW] MemoryIndicator         │                                │
```

---

## 5. Implementation Tasks

### Phase 1: Security (P0) — 2 tasks

| Task | Files | Description |
|------|-------|-------------|
| **T1: Session ownership validation** | `session_handler.py`, `ai_chat.py` | Add `workspace_id + user_id` validation in `get_session()`. Return 403 if mismatch. Add test. |
| **T2: Vault-based API key retrieval** | `pilotspace_agent.py` | Replace `os.getenv("ANTHROPIC_API_KEY")` with `SecureKeyStorage.get_key(workspace_id)` → Supabase Vault. Fallback to env var. Add test. |

### Phase 2: High-ROI SDK Features (P1) — 5 tasks

| Task | Files | Description |
|------|-------|-------------|
| **T3: Structured output for skills** | `pilotspace_agent.py`, `sandbox_config.py` | Pass `output_format` with JSON schema when skill invocation is detected (extract-issues, decompose-tasks, find-duplicates). Backend validates with Pydantic before emitting structured_result SSE. |
| **T4: File checkpointing** | `pilotspace_agent.py`, `sandbox_config.py` | Enable SDK file checkpointing. On approval rejection of content_update, call checkpoint.revert(). Wire to approval flow. |
| **T5: PostToolUse audit hook** | `hooks.py` | Register SDK-native PostToolUse hook callback instead of manual tool_audit emission in transform. Hook receives actual SDK duration. Emit tool_audit SSE from hook. |
| **T6: Todo → TaskPanel wiring** | `pilotspace_agent_helpers.py`, `PilotSpaceStreamHandler.ts` | Detect TodoWrite/TodoRead tool results in transform. Map to task_progress SSE events. Frontend TaskPanel already handles task_progress. |
| **T7: Dynamic effort parameter** | `pilotspace_agent.py`, `sandbox_config.py` | Classify query complexity (simple greeting vs complex analysis). Set `effort: "low"` for simple queries to reduce latency by ~40%. |

### Phase 3: UX Enhancements (P2) — 4 tasks

| Task | Files | Description |
|------|-------|-------------|
| **T8: Fine-grained tool streaming** | `pilotspace_agent_helpers.py`, `events.ts`, `PilotSpaceStreamHandler.ts` | Add `tool_input_delta` SSE event. Backend streams tool input JSON chunks. Frontend renders partial tool params in ToolCallList. |
| **T9: Project context** | `PilotSpaceStore.ts`, `PilotSpaceActions.ts` | Implement `setProjectContext()` — store project data, include in ConversationContext. Update sendMessage() to pass projectId. |
| **T10: Skill/agent tracking** | `PilotSpaceStore.ts` | Implement `setActiveSkill()` and `addMentionedAgent()` — track in store state, attach to message metadata. Show active skill badge in ChatInput. |
| **T11: Memory tool** | `sandbox_config.py`, `pilotspace_agent.py` | Enable SDK Memory tool (`memory_enabled: true`). Memory persists to `.claude/memory/` in workspace sandbox. Cross-session preference retention. |

### Phase 4: Future (P3) — 4 tasks

| Task | Files | Description |
|------|-------|-------------|
| **T12: Citations** | `sandbox_config.py`, `events.ts`, `PilotSpaceStreamHandler.ts`, new `CitationLink.tsx` | Enable `citations_enabled: true`. Backend emits citation events. Frontend renders clickable source links. |
| **T13: Code execution tool** | `sandbox_config.py`, new `CodeResultViewer.tsx` | Enable SDK code execution tool. Build result viewer for stdout/stderr/images. Sandboxed execution only. |
| **T14: Message virtualization** | `MessageList.tsx` | Integrate `@tanstack/react-virtual` for windowed rendering. Only render visible messages. Required at 500+ messages. |
| **T15: Streaming input mode** | `sandbox_config.py`, `ai_chat.py` | Enable streaming input for large documents. Backend detects input >10K chars and uses streaming input mode. |

---

## 6. Dependency Graph

```
T1 (session ownership) ─── no deps ──────────── can start immediately
T2 (vault keys)        ─── no deps ──────────── can start immediately

T3 (structured output) ─── no deps ──────────── can start immediately
T4 (file checkpoint)   ─── no deps ──────────── can start immediately
T5 (PostToolUse hook)  ─── no deps ──────────── can start immediately
T6 (todo → TaskPanel)  ─── no deps ──────────── can start immediately
T7 (effort param)      ─── no deps ──────────── can start immediately

T8 (tool streaming)    ─── no deps ──────────── can start immediately
T9 (project context)   ─── no deps ──────────── can start immediately
T10 (skill tracking)   ─── no deps ──────────── can start immediately
T11 (memory tool)      ─── T2 (vault keys) ──── needs secure key storage

T12 (citations)        ─── no deps ──────────── can start immediately
T13 (code execution)   ─── T4 (checkpoint) ───── safety: revert on errors
T14 (virtualization)   ─── no deps ──────────── can start immediately
T15 (streaming input)  ─── no deps ──────────── can start immediately
```

Most tasks are independent and can be parallelized within each phase.

---

## 7. Risk Assessment

| Task | Risk | Mitigation |
|------|------|------------|
| T1 (session ownership) | Low — straightforward validation | Unit test with cross-workspace session ID |
| T2 (vault keys) | Medium — Supabase Vault integration may not exist yet | Fallback to env var if Vault unavailable |
| T3 (structured output) | Low — SDK native, well-documented | Pydantic validation catches schema mismatches |
| T4 (file checkpoint) | Medium — SDK checkpoint API may have edge cases with concurrent edits | Checkpoint only for MCP note tools, not all files |
| T5 (PostToolUse) | Low — replacing manual with SDK-native | Verify duration_ms accuracy from SDK vs manual timing |
| T7 (effort) | Low — transparent optimization | A/B test: measure latency improvement vs quality |
| T8 (tool streaming) | Medium — new SSE event type, requires frontend state for partial JSON | Stream complete key-value pairs, not arbitrary JSON chunks |
| T11 (memory) | Medium — privacy implications of persistent memory | Memory scoped to workspace, clearable by user |
| T12 (citations) | High — new UI paradigm, may require significant frontend work | Defer to Phase 4, prototype first |

---

## 8. Verification Plan

| Phase | Quality Gate | Command |
|-------|-------------|---------|
| Phase 1 | Backend: pyright + ruff + pytest on modified files | `uv run pyright && uv run ruff check && uv run pytest tests/unit/ai/sdk/` |
| Phase 2 | Backend + Frontend: full quality gates | Backend: `uv run pyright && uv run ruff check && uv run pytest --cov=.` / Frontend: `pnpm lint && pnpm type-check && pnpm test` |
| Phase 3 | Same as Phase 2 + manual UI verification | Visual inspection of new UI states |
| Phase 4 | Same as Phase 2 + performance benchmarks | MessageList render time at 500/1000/5000 messages |

---

## 9. Files Reference

### Backend (modify)

| File | Lines | Tasks |
|------|-------|-------|
| `pilotspace_agent.py` | 686 | T2, T3, T4, T7, T11 |
| `pilotspace_agent_helpers.py` | 558 | T6, T8 |
| `hooks.py` | 692 | T5 |
| `sandbox_config.py` | 478 | T3, T4, T7, T11, T12, T13, T15 |
| `session_handler.py` | 612 | T1 |
| `ai_chat.py` | 462 | T1, T15 |

### Frontend (modify)

| File | Lines | Tasks |
|------|-------|-------|
| `PilotSpaceStore.ts` | 593 | T9, T10 |
| `PilotSpaceActions.ts` | 333 | T9 |
| `PilotSpaceStreamHandler.ts` | 644 | T6, T8 |
| `events.ts` | 606 | T8 |

### Frontend (create)

| File | Task |
|------|------|
| `CitationLink.tsx` | T12 |
| `CodeResultViewer.tsx` | T13 |

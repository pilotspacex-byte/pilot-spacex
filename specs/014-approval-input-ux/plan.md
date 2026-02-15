# Implementation Plan: Approval & User Input UX

**Feature**: 014 — Approval & User Input UX
**Branch**: `014-approval-input-ux`
**Created**: 2026-02-13
**Spec**: `specs/014-approval-input-ux/spec.md`
**Author**: Tin Dang

---

## Summary

Replaces the current modal-heavy approval flow and flat question cards with an inline, two-tier approval/question system in the ChatView sidebar. Backend wraps the SDK's AskUserQuestion with a thin adapter that publishes richer SSE events. Frontend gets new QuestionBlock (with stepped flow), InlineApprovalCard, DestructiveApprovalModal, and WaitingIndicator components.

---

## Technical Context

| Attribute | Value |
|-----------|-------|
| **Language/Version** | Python 3.12+, TypeScript 5.3+ |
| **Primary Dependencies** | FastAPI 0.110+, Next.js 14+, Claude Agent SDK, MobX 6+ |
| **Testing** | pytest + pytest-asyncio (backend), Vitest (frontend) |
| **Target Platform** | Browser (35% sidebar panel) |
| **Performance Goals** | <100ms UI render (P95), <200ms answer submission |
| **Constraints** | 700-line file limit, WCAG 2.2 AA |

---

## Research Decisions

| Question | Options Evaluated | Decision | Rationale |
|----------|-------------------|----------|-----------|
| Question mechanism | Custom MCP tool + DB table, SDK built-in only, SDK + thin adapter | **SDK + thin adapter** | SDK handles waiting/persistence. Adapter publishes richer SSE event for custom UI. No new DB table, no custom waiter. FR-013. |
| Approval tiers | 3 tiers (safe/caution/critical), 2 tiers (inline/modal) | **2 tiers** | Inline for all non-destructive, modal for destructive. Simpler. Add severity badges in v2. FR-006. |
| Undo on approve | 8s backend hold + cancel endpoint, Frontend-only optimistic, No undo | **No undo in v1** | Approve = execute immediately. Safety gate is the approval card itself. Simplifies backend. |
| Edit & Approve | Editable payload fields, Reject + re-ask | **Reject + re-ask** | User rejects with reason, AI adjusts. Natural conversation flow, no editable payload complexity. |
| Destructive confirmation | Typed phrase (GitHub-style), Standard confirm dialog, Double-click | **Standard confirm dialog** | "Are you sure? This cannot be undone." with Confirm/Cancel. Simpler, still prevents accidents. FR-007. |
| WaitingIndicator complexity | Full (escalate + scroll), Simple static banner | **Simple static banner** | "Waiting for your response" with pulse dot. No 60s escalation, no click-to-scroll. FR-009. |
| WaitingIndicator placement | Replace StreamingBanner, Stack above, Merge | **Replace StreamingBanner** | QUESTION_PENDING and STREAMING are mutually exclusive. Clean swap. |
| Component sharing (ChatView vs queue page) | Shared base + variants, Completely independent | **Completely independent** | Different layouts, data shapes, contexts. No shared base. |

---

## Story-to-Component Matrix

| User Story | Backend Changes | Frontend Components |
|------------|----------------|---------------------|
| US-1: Questions | Thin adapter wrapping SDK AskUserQuestion → publishes `question_request` SSE event | `QuestionBlock.tsx`, `WaitingIndicator.tsx` (shared), PilotSpaceStore question state |
| US-2: Inline Approval | None (existing approval flow unchanged) | `InlineApprovalCard.tsx` |
| US-3: Destructive Modal | None (existing approval flow unchanged) | `DestructiveApprovalModal.tsx` |
| US-4: Waiting Indicator | None | `WaitingIndicator.tsx`, `StreamingBanner.tsx` (modified) |

---

## Architectural Approach: SDK Thin Adapter

**Decision**: Wrap the Claude Agent SDK's built-in `AskUserQuestion` tool with a thin adapter instead of building a custom MCP tool with its own DB table and waiter.

**How It Works**:

1. SDK's AskUserQuestion fires during agent processing → SDK blocks the agent internally
2. Thin adapter intercepts the SDK event, generates a `questionId`, publishes a richer `question_request` SSE event
3. Frontend receives event, renders QuestionBlock inline in chat
4. WaitingIndicator appears above chat input
5. User selects options / types free text, clicks Submit
6. Frontend sends the answer as a **regular chat message** through `POST /chat` with a `[ANSWER:{questionId}]` prefix (e.g., `"[ANSWER:q-abc123] Detailed Report"`)
7. Backend chat handler parses the `[ANSWER:...]` prefix, extracts questionId, and routes to `adapter.resolve_answer()` instead of the agent
8. Adapter resolves the SDK's pending tool result callback with the parsed answer
9. If no `[ANSWER:...]` prefix and no pending question, the message passes through to the agent normally
9. SDK unblocks the agent, which continues processing with the user's input

**No New Endpoint**: The answer flows through the existing `POST /chat` endpoint with an `[ANSWER:questionId]` prefix. The chat handler parses the prefix and routes to the adapter. The existing `POST /answer` endpoint is **deprecated and removed** as part of this feature.

**Single-Worker Assumption (v1)**: The adapter holds pending callbacks in-memory (`dict[questionId → callback]`). This assumes a single uvicorn worker. If the process restarts mid-question, the question is lost (user re-asks). Multi-worker support is deferred to v2.

**What We Don't Build** (SDK handles these):
- No `ai_user_questions` DB table (SDK manages blocking/timeout in memory)
- No asyncio.Event waiter (SDK's built-in blocking)
- No custom timeout logic (SDK's 5-min timeout)
- No dedicated answer endpoint (answers flow through `POST /chat` with `[ANSWER:...]` prefix; existing `POST /answer` removed)

**What We Build**:
- Thin adapter that intercepts SDK question events and publishes richer SSE
- Chat handler logic to detect pending question and route answer to adapter
- Frontend QuestionBlock component with stepped flow, option selection, collapse animation
- Event type + handler for `question_request`

**Browser Refresh Recovery**: Pending *approvals* recover from DB (existing). Pending *questions* rely on the agent process still running — if agent is alive, the chat handler still routes to adapter. If agent process died, question is lost (acceptable for v1).

---

## SSE Event: question_request

**Source**: FR-016

```typescript
{
  type: 'question_request',
  data: {
    messageId: string;      // Parent AI message
    questionId: string;     // SDK question ID
    toolCallId: string;     // SDK tool call ID
    questions: Array<{
      text: string;
      options: Array<{ label: string; description?: string }>;
      multiSelect: boolean;
      header?: string;      // max 12 chars badge
    }>;
  }
}
```

---

## Migration Strategy

**Components Replaced**:
- `QuestionCard` → `QuestionBlock` (US-1)
- `SuggestionCard` → `InlineApprovalCard` (US-2)
- `ApprovalOverlay` floating button → removed (approvals are now inline)
- `ChatView/ApprovalOverlay/ApprovalDialog` → `DestructiveApprovalModal` (US-3)
- `components/ai/ApprovalDialog` → deleted (approval queue page gets its own component in v2)

**Components Retained**:
- `features/approvals/ApprovalCard` (approval queue page — separate from ChatView)
- `features/approvals/ApprovalDetailModal` (approval queue page — separate from ChatView)

**Approach**: Delete old components, replace with new. No feature flags, no coexistence period.

---

## Project Structure

```text
backend/src/pilot_space/
├── ai/sdk/
│   └── question_adapter.py            # NEW: thin adapter wrapping SDK AskUserQuestion → SSE
├── api/v1/routers/
│   └── ai_chat.py                     # MODIFIED: rename SSE event, parse [ANSWER:] prefix, remove POST /answer endpoint

frontend/src/
├── features/ai/ChatView/
│   ├── MessageList/
│   │   ├── QuestionBlock.tsx          # NEW: replaces QuestionCard.tsx
│   │   ├── QuestionCard.tsx           # DELETED
│   │   ├── InlineApprovalCard.tsx     # NEW: replaces SuggestionCard.tsx
│   │   └── SuggestionCard.tsx         # DELETED
│   ├── ApprovalOverlay/
│   │   ├── DestructiveApprovalModal.tsx # NEW: replaces ApprovalDialog.tsx
│   │   ├── ApprovalDialog.tsx         # DELETED
│   │   └── ApprovalOverlay.tsx        # DELETED
│   ├── WaitingIndicator.tsx           # NEW
│   └── StreamingBanner.tsx            # MODIFIED: yields to WaitingIndicator
├── stores/ai/
│   ├── PilotSpaceStore.ts             # MODIFIED: question state, event handlers
│   └── types/
│       ├── events.ts                  # MODIFIED: add question_request event type
│       └── event-guards.ts            # MODIFIED: add type guard

tests/
├── backend/
│   └── unit/
│       └── test_question_adapter.py   # NEW
└── frontend/
    ├── QuestionBlock.test.tsx         # NEW
    ├── InlineApprovalCard.test.tsx    # NEW
    ├── DestructiveApprovalModal.test.tsx # NEW
    └── WaitingIndicator.test.tsx      # NEW
```

All new files target <400 lines. Follows existing ChatView component structure.

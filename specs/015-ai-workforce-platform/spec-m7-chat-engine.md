# M7 — Chat Engine

**Feature**: 015 AI Workforce Core
**Module**: M7 — Chat Engine (Frontend)
**Status**: Pending (Sprint 3)
**Depends on**: M1 SSE events, M2 API (confirm/reject), M3 Approval API
**Consumed by**: End users

---

## Purpose

Upgrade the existing `ChatView` right panel to render intent cards, skill progress, approval actions, and conversation blocks. This is **frontend-only** — no new backend services. M7 consumes SSE events that M1 already emits.

NoteCanvas 65/35 split is unchanged. Only message rendering and interaction model are upgraded.

---

## Codebase Anchors

- `frontend/src/features/ai/ChatView/` — upgrade target
- `frontend/src/stores/PilotSpaceStore.ts` — MobX orchestrator
- `frontend/src/stores/ApprovalStore.ts` — approval state
- `frontend/src/stores/ChatHistoryStore.ts` — message history

---

## New Components

### IntentCard

Renders a detected WorkIntent in the chat timeline.

| Element | Detail |
|---------|--------|
| Content | what, why, confidence bar |
| Confidence bar colors | green >80%, yellow 70–80%, red <70% |
| Actions | [Confirm] [Edit] [Dismiss] |
| SSE trigger | `intent_detected` event |
| Accessibility | ARIA labels, keyboard nav, focus management |

### SkillProgressCard

Renders active/completed skill execution.

| Element | Detail |
|---------|--------|
| Content | intent summary, skill name, animated status |
| Status states | executing → completed / failed |
| Links | artifact links to modified notes/issues |
| SSE triggers | `intent_executing` + `intent_completed` |

### ApprovalCard

For destructive/suggest skills requiring explicit approval.

| Element | Detail |
|---------|--------|
| Content | TipTap block preview (read-only render) |
| Actions | [Approve] [Reject] |
| Countdown | 24h expiry timer |
| API calls | POST `/{workspace_id}/skill-approvals/{id}/approve` or `/reject` |
| Error handling | Toast on failure, retry option |
| Role guard | [Approve] disabled if user role < required_approval_role |

### ConversationBlock

Threaded Q&A for AI clarification questions (FR-066–068).

| Element | Detail |
|---------|--------|
| Content | AI question + human reply input |
| SLA indicator | 5s processing timer (FR-068) |

### Polymorphic Message Renderer

Routes message type → correct component:

| Type | Component |
|------|-----------|
| `text` | TextMessage (existing) |
| `intent_card` | IntentCard |
| `skill_progress` | SkillProgressCard |
| `approval` | ApprovalCard |
| `conversation` | ConversationBlock |
| default | TextMessage |

---

## Chat Interaction Model

### SSE Event Handlers

| Event | Store Update |
|-------|-------------|
| `intent_detected` | ChatHistoryStore: add IntentCard message |
| `intent_confirmed` | ChatHistoryStore: update IntentCard to "confirmed" state |
| `intent_executing` | ChatHistoryStore: replace IntentCard with SkillProgressCard |
| `intent_completed` | ChatHistoryStore: update SkillProgressCard to "completed" |

Optimistic UI: confirm/reject actions update local state immediately, revert on API error.

### ConfirmAll UI

- Button in chat header when pending intents > 0
- Badge showing pending count
- Calls `POST /api/v1/ai/intents/confirm-all` (max 10)
- Shows result: "N confirmed, M remaining" (M2 cap behavior)
- Hidden when 0 pending intents

### Queue Depth Indicator

- Shown when > 5 skills running simultaneously
- Live text: "N running, M queued" via SSE
- Disappears when all slots free

### Skill Output Preview

For `suggest` approval skills:
- Render TipTap blocks read-only in chat before writing to note
- [Approve] → POST approve API → blocks written to note
- [Revise] → new intent cycle with feedback

---

## Ghost Text (No Changes)

GhostTextAgent operates independently of M4 Memory Engine for <2s latency SLA. Memory-aware ghost text is deferred to Feature 016 (Note Collaboration). This module only documents that ghost text cache expires after 5 minutes (FR-045–047).

---

## Functional Requirements

| ID | Requirement |
|----|-------------|
| FR-105 | Chat = primary command interface |
| FR-106 | Skill output written to notes (blocks for small, new note for large) |
| FR-107 | Intent detection from chat (primary) and note changes (secondary) |
| FR-108 | Approval interactions (approve/revise/reject) in chat |
| FR-066 | AI creates shared Conversation blocks for clarification |
| FR-067 | Threaded Q&A in conversation blocks |
| FR-068 | AI processes responses within 5s |
| FR-045 | Ghost text cache expires after 5 minutes |
| FR-046 | Fresh suggestion on expiry |
| FR-047 | Cache invalidated on content change |

---

## Tasks

| ID | Task | Status |
|----|------|--------|
| T-052 | IntentCard component | Pending |
| T-053 | SkillProgressCard component | Pending |
| T-054 | ApprovalCard component | Pending |
| T-055 | ConversationBlock component | Pending |
| T-056 | Polymorphic message renderer | Pending |
| T-057 | SSE event handlers for intent lifecycle | Pending |
| T-058 | Wire ApprovalCard → ApprovalStore → API | Pending |
| T-059 | ConfirmAll UI | Pending |
| T-060 | Queue depth indicator | Pending |
| T-061 | Skill output preview in chat | Pending |
| T-062 | Chat session rehydration | Pending |
| T-063 | Ghost text documentation | Pending |
| T-064 | Unit tests for chat components | Pending |
| T-065 | E2E test: full user flow | Pending |
| T-066 | Accessibility audit | Pending |

---

## Sprint 3 Gate

- [ ] IntentCard renders with correct actions (Storybook + unit test)
- [ ] ApprovalCard calls approval API and handles success/error (integration test)
- [ ] SSE intent lifecycle events render correctly in chat (E2E test)
- [ ] ConfirmAll UI respects cap and shows queue depth (unit test)
- [ ] Full user flow: type command → intent card → confirm → skill progress → approve → note updated (E2E test)
- [ ] Chat state rehydrates on page refresh (integration test)
- [ ] Test coverage >80% for new frontend code
- [ ] Lighthouse accessibility >95 for new components

---

## Edge Cases

| Scenario | Behavior |
|----------|----------|
| Chat closed while skill running | Skill continues, output queued. Reconnect: rehydrate from API. |
| Page refresh mid-skill | Rehydrate: fetch active intents + pending approvals → render correct card states |
| Approval role insufficient | [Approve] button disabled, tooltip shows required role |
| ApprovalCard expiry countdown reaches 0 | Card transitions to "expired" state, no-op on action attempts |

---

## Success Criteria

| Criteria | Target |
|----------|--------|
| Progress visibility after skill start | <5 seconds |
| Ghost text cache expiry accuracy | 5 ± 0.5 minutes |
| Accessibility score | Lighthouse >95 |
| Chat state rehydration | No flash of empty state on refresh |

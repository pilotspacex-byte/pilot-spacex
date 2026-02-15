# Feature Specification: Approval & User Input UX

**Feature Number**: 014
**Branch**: `014-approval-input-ux`
**Created**: 2026-02-13
**Status**: Draft
**Author**: Tin Dang

---

## Problem Statement

**Who**: All team members (PMs, Developers, Tech Leads) interacting with the AI sidebar in the Note Canvas workspace.

**Problem**: The current AI approval and question-answering experience in the 35% ChatView sidebar breaks conversation flow. Modal dialogs interrupt thinking. All approval requests look identical regardless of risk level. When AI asks questions, the presentation is flat and unstyled, with no multi-step guidance for complex queries. After responding, there is no feedback that AI received the answer or is processing. Users cannot tell if the AI is waiting for them or working.

**Impact**: Users develop "approval fatigue" — dismissing or ignoring approval requests because the cost of interruption exceeds the perceived risk. Questions go unanswered because the UI doesn't convey urgency or waiting state. Trust erodes: users don't understand what the AI wants to do, why, or what the consequences are. This directly undermines the human-in-the-loop principle (DD-003).

**Success**: AI approvals and questions feel like natural conversation turns in the sidebar. Users respond within 2 seconds. Destructive actions are unmistakably different from safe ones. The AI's waiting state is always visible.

---

## Stakeholders

| Stakeholder | Role | Interest |
|-------------|------|----------|
| Tin Dang | Product Owner / Architect | UX quality, trust model, DD-003 compliance |
| Frontend Dev | Implementer | Component API design, animation perf, accessibility |
| End Users | All personas | Fast, non-disruptive AI interactions |

---

## User Scenarios & Testing

### User Story 1 — AI Asks a Clarifying Question (P1)

The AI needs input before proceeding. The question appears inline in the chat as a natural conversation turn with tappable option cards. For 3+ questions, a stepped flow with progress indicator is used. After answering, the question collapses to a compact summary.

**Acceptance Scenarios**:

1. **Given** the AI sends a single-select question with 3 options, **When** the user taps an option, **Then** the option highlights, Submit becomes enabled, and submitting sends the answer within 200ms.
2. **Given** the AI sends 3 questions in sequence, **When** the user answers the first, **Then** a step indicator shows "1/3" and the next question slides in.
3. **Given** the AI sends a multi-select question, **When** the user selects 2 of 4 options, **Then** both show checkmarks and Submit shows "(2 selected)".
4. **Given** none of the options fit, **When** the user selects "Other", **Then** a text input appears for free-text entry (200-char limit).
5. **Given** the user has answered all questions, **Then** the question block collapses to a single line "You chose: [answer]" with a chevron to expand.
6. **Given** a question has been pending for 5 minutes, **Then** the block shows "Timed out", the AI stops the current task and informs the user.

---

### User Story 2 — Non-Destructive Approval (Inline) (P1)

The AI wants to perform a safe or low-risk action. An inline approval card appears in the chat flow with the action name, a brief description, and Approve/Reject buttons. The user approves with a single tap and the AI proceeds immediately. Approve = execute immediately (no undo window in v1).

**Acceptance Scenarios**:

1. **Given** the AI requests approval for a non-destructive action, **When** the card appears, **Then** it shows: action name, one-line description, Approve (primary) and Reject (ghost) buttons.
2. **Given** the user taps Approve, **Then** the card collapses to "[action] approved" and the AI proceeds immediately.
3. **Given** the user taps Reject, **Then** an optional inline text field appears for a rejection reason (user can type or skip). Card collapses to "[action] rejected — [reason]". AI receives rejection with reason.
4. **Given** two approvals arrive simultaneously, **Then** they stack vertically with independent controls.

---

### User Story 3 — Destructive Action Approval (Modal) (P1)

The AI wants to perform a high-risk action (deleting issues, removing members). A blocking modal appears with clear risk communication: warning header, description of consequences, list of affected items, and a standard confirmation dialog ("Are you sure? This cannot be undone."). No typed confirmation — just Confirm/Cancel buttons.

**Acceptance Scenarios**:

1. **Given** the AI requests a destructive action (e.g., "Delete 5 issues"), **When** the modal appears, **Then** it shows: red warning header, action description, list of affected items, and Confirm/Cancel buttons.
2. **Given** the modal is open, **When** the user clicks Confirm, **Then** the modal closes, the AI executes, and the chat shows "[action] executed" with a warning indicator.
3. **Given** the modal is open, **When** the user clicks Cancel or presses Escape, **Then** the modal closes and the AI receives a rejection.
4. **Given** the modal has been open 5 minutes with no action, **Then** the modal auto-cancels with "Timed out — no action taken".
5. **Given** a destructive action is approved, **Then** NO undo is available (destructive = final).

---

### User Story 4 — AI Waiting Indicator (P1)

When the AI is waiting for the user's response (question or approval), a static indicator appears above the chat input showing "Waiting for your response" with a gentle pulsing animation.

**Acceptance Scenarios**:

1. **Given** the AI sends a question or approval request, **Then** a waiting indicator appears above the chat input within 100ms showing "Waiting for your response" with a pulse animation.
2. **Given** the waiting indicator is visible, **When** the user responds, **Then** the indicator disappears within 200ms.

---

### Edge Cases

- Sidebar closed while approval pending → Approval persists in MobX state; reopening shows it. AI remains paused.
- AI session times out (24h) while approval pending → Auto-rejects with "Session expired".
- Two approvals arrive simultaneously → Stack vertically, each independent.
- User navigates to a different note → Pending approval stays in chat; waiting indicator remains.
- Browser force-refresh during pending approval → Session recovery from backend restores pending approval state (approvals have DB table). Pending questions rely on SDK agent still running — if agent is alive, answer relay endpoint still works; if agent died, question is lost (user re-asks).
- Question with 0 valid options (malformed) → Falls back to free-text input.
- Question times out at 5 minutes → QuestionBlock shows "Timed out". AI stops and informs user.
- Rejection without reason → Sent with empty reason. AI adjusts.

---

## Requirements

### Functional Requirements

- **FR-001**: System MUST display AI questions inline in the chat flow as conversation turns.
- **FR-002**: System MUST support 1-4 questions per request, using a stepped flow with progress indicator for 3+ questions.
- **FR-003**: System MUST support single-select, multi-select, and free-text ("Other") input modes.
- **FR-004**: System MUST collapse answered questions to a compact summary within 300ms.
- **FR-005**: System MUST display non-destructive approvals as inline cards, not modals.
- **FR-006**: System MUST differentiate two approval tiers: inline (non-destructive) and modal (destructive). Tier is auto-determined from ACTION_CLASSIFICATIONS (CRITICAL_REQUIRE → modal, all others → inline). No severity badges in v1 — single visual style for inline cards.
- **FR-007**: System MUST show a standard confirmation dialog for destructive actions (Confirm/Cancel with warning text).
- **FR-008**: System MUST auto-cancel destructive modals after 5 minutes of inactivity (matches SDK question timeout).
- **FR-009**: System MUST show a static waiting indicator when the AI is in QUESTION_PENDING or APPROVAL_PENDING state.
- **FR-010**: System MUST deliver approval/question UI within 100ms of receiving the SSE event.
- **FR-011**: System MUST persist pending approvals across sidebar close/reopen (MobX) and browser refresh (backend recovery).
- **FR-012**: System MUST auto-reject pending approvals when the AI session expires (24h TTL).
- **FR-013**: System MUST wrap the SDK's AskUserQuestion with a thin adapter that publishes a richer `question_request` SSE event for custom frontend rendering. The user's answer is sent as a regular chat message through the existing `POST /chat` endpoint with a `[ANSWER:questionId]` prefix — the chat handler parses the prefix and routes to the adapter, which resolves the SDK's pending callback. The existing `POST /answer` endpoint is deprecated and removed.
- **FR-014**: System MUST verify that the SDK blocks the AI agent while waiting for a question response, resuming after answer or 5-minute timeout. (SDK-managed — adapter must not break this contract.)
- **FR-015**: System MUST verify that the SDK auto-timeouts unanswered questions after 5 minutes. AI MUST NOT auto-pick a default. (SDK-managed — adapter must not break this contract.)
- **FR-016**: System MUST publish questions as `question_request` SSE events, separate from `approval_request`.
- **FR-017**: System MUST support optional rejection reasons for non-destructive approvals via inline text field.
- **FR-018**: System MUST limit question types to options + free text for v1.
- **FR-019**: System SHOULD support keyboard navigation: Enter to submit, Escape to cancel, Tab/arrows to navigate.
- **FR-020**: System SHOULD announce state changes to screen readers via live regions.

### Key Entities

- **ApprovalRequest** (existing): id, action_name, description, payload, status (pending/approved/rejected/expired), created_at, resolved_at. Belongs to ChatSession.
- **UserQuestion** (frontend state + SDK memory): id, questions array, status (pending/answered/timed_out), answers. SDK manages blocking and timeout in-memory. No new DB table. Note: browser refresh recovery for pending *questions* depends on SDK state surviving the agent process — if the agent is still running, the adapter's answer relay endpoint can still accept answers. If the agent process died, the question is lost (acceptable for v1).
- **WaitingState** (UI-only): type (question/approval), derived from ChatSession state machine.

---

## Success Criteria

- **SC-001**: Users respond to approvals within 2 seconds (median).
- **SC-002**: Modal interruptions reduced by 80% (only destructive actions use modals).
- **SC-003**: Zero accidental destructive approvals — all critical actions require explicit confirmation.
- **SC-004**: UI renders within 100ms of SSE event (P95).
- **SC-005**: Pending state survives sidebar close/reopen and browser refresh.

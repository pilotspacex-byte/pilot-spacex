# Tasks: Approval & User Input UX

**Feature**: 014 — Approval & User Input UX
**Branch**: `014-approval-input-ux`
**Created**: 2026-02-13
**Source**: `specs/014-approval-input-ux/`
**Author**: Tin Dang

---

## v1 Scope Decisions

| Decision | Rationale |
|----------|-----------|
| SDK + thin adapter (no custom MCP tool, no DB table) | SDK handles waiting/persistence. Adapter publishes richer SSE. |
| 2 approval tiers (inline vs modal) | No severity badges in v1. Add safe/caution/critical in v2. |
| No undo window | Approve = execute immediately. Safety gate is the card itself. |
| Reject + re-ask (no Edit & Approve) | User rejects with reason, AI adjusts. Natural conversation. |
| Standard confirm dialog (no typed phrase) | Simpler, still blocks accidental destructive approvals. |
| Simple static WaitingIndicator | No 60s escalation, no click-to-scroll. Just pulse dot + text. |
| Stepped flow for 3+ questions | 1-2 stack vertically; 3-4 use step indicator with Back/Next. |
| Sidebar + browser refresh recovery | MobX for sidebar; backend query on reconnect for refresh. |
| Deferred to v2 | BatchApprovalCard, ApprovalHistorySummary, TokenCost, Edit & Approve, SeverityBadge, UndoToast |

---

## Phase 1: Backend + Frontend Foundation

### Backend

- [ ] T01 Create question adapter wrapping SDK AskUserQuestion in `backend/src/pilot_space/ai/sdk/question_adapter.py`
  - Intercepts SDK's AskUserQuestion events, generates questionId
  - Publishes richer `question_request` SSE event with question data formatted for frontend
  - Maintains in-memory registry: `dict[questionId → SDK callback]` for pending questions (single-worker assumption for v1)
  - Exposes `resolve_answer(questionId, answers)` method that resolves the SDK's pending tool result callback
  - No new DB table — SDK manages blocking/timeout in memory
  - Per plan.md Architectural Approach

- [ ] T02 Modify chat handler to route question answers and remove `/answer` endpoint in `backend/src/pilot_space/api/v1/routers/ai_chat.py`
  - Rename SSE event `ask_user_question` → `question_request` (FR-016)
  - Parse `[ANSWER:{questionId}]` prefix on incoming chat messages → route to `adapter.resolve_answer()` with parsed answer text
  - If no `[ANSWER:...]` prefix, pass message to agent normally
  - Remove existing `POST /answer` endpoint (deprecated — answers now flow through `POST /chat`)
  - Touchpoints for SSE rename: event type string in stream generator, any backend event builder helpers

- [ ] T02b Add session recovery: on reconnect, return pending approvals so frontend can restore state (FR-011)
  - Query existing approval DB table for pending approvals in the session
  - For questions: if agent process is alive and question is in adapter's in-memory registry, include it
  - Per FR-011

### Frontend Foundation

- [ ] T03 Rename SSE event type frontend-side and add design tokens
  - Rename `ask_user_question` → `question_request` in `frontend/src/stores/ai/types/events.ts` (type name + event string)
  - Rename `isAskUserQuestionEvent()` → `isQuestionRequestEvent()` in `frontend/src/stores/ai/types/event-guards.ts`
  - Update all imports/usages of the old name in: PilotSpaceStore event handler switch, any stream handler files
  - Add CSS custom properties: `--color-question-bg` (#F5F0EB), `--color-question-bg-dark` (#252220)

- [ ] T04 Add question state management to PilotSpaceStore in `frontend/src/stores/ai/PilotSpaceStore.ts`
  - Observable: pendingQuestion (QuestionRequestEvent | null)
  - Action: handleQuestionRequest(event) — sets pendingQuestion, transitions to QUESTION_PENDING
  - Action: submitQuestionAnswer(questionId, answers) — sends chat message with `[ANSWER:{questionId}]` prefix through existing `POST /chat`, clears pendingQuestion
  - Wire `question_request` SSE event handler in the event processing switch

**Checkpoint**: Backend adapter publishes `question_request` events, chat handler parses `[ANSWER:]` prefix and routes to adapter, `POST /answer` removed, session recovery returns pending state. Frontend has renamed event types, store state, design tokens. Run `uv run pyright && uv run ruff check` and `pnpm lint && pnpm type-check`.

---

## Phase 2: Questions + Waiting Indicator (US-1, US-4)

### Tests

- [ ] T05 [P] Write unit tests for question adapter in `backend/tests/unit/test_question_adapter.py`
  - Test: adapter publishes question_request SSE event with correct shape and questionId
  - Test: resolve_answer(questionId, answers) resolves the SDK callback with correct data
  - Test: resolve_answer for unknown questionId is a no-op (message passes through to agent)
  - Test: resolve_answer for already-answered question is a no-op
  - Test: handles malformed question data gracefully (0 options → free-text fallback)
  - Test: chat handler parses `[ANSWER:questionId]` prefix and routes to adapter
  - Test: chat message without `[ANSWER:]` prefix passes through to agent normally
  - Test: `POST /answer` endpoint is removed (404)

- [ ] T06 [P] Write component tests for QuestionBlock in `frontend/tests/QuestionBlock.test.tsx`
  - Test: renders single question with radio options (single-select)
  - Test: renders multi-select question with checkboxes
  - Test: Submit enabled only when selection made
  - Test: "Other" free-text input appears on selecting last option
  - Test: step indicator shows for 3+ questions (1/3, 2/3, 3/3)
  - Test: 1-2 questions stack vertically without stepping
  - Test: collapsed state shows "You chose: [selection]" after submit
  - Test: keyboard (Tab, Enter, ArrowUp/Down)
  - Test: ARIA roles (radiogroup for single-select, group+checkbox for multi-select)

- [ ] T07 [P] Write component tests for WaitingIndicator in `frontend/tests/WaitingIndicator.test.tsx`
  - Test: renders "Waiting for your response" with pulse animation
  - Test: disappears within 200ms on state change
  - Test: ARIA role="status" with aria-live="polite"

### Implementation

- [ ] T08 Create QuestionBlock component in `frontend/src/features/ai/ChatView/MessageList/QuestionBlock.tsx`
  - Single-question: radio options (single-select) or checkbox options (multi-select)
  - Multi-question stepped view (3+ questions): step indicator, Back/Next/Submit navigation
  - "Other" option: inline text input with 200-char limit (FR-003)
  - Collapsed state: single-line "You chose: [selection]" with expand chevron
  - Submitting state: spinner on Submit, inputs disabled
  - Animations: slide-in entrance (200ms), collapse after submit (250ms), option selection (150ms)
  - Keyboard: Tab=cycle, Space/Enter=select, ArrowUp/Down=move (FR-019)
  - ARIA: role="region", radiogroup/group, aria-checked, aria-live="polite" (FR-020)
  - Minimum touch target: 44px height per option
  - Respects prefers-reduced-motion
  - Reference UX spec section 7.1 for Tailwind classes

- [ ] T09 Create WaitingIndicator component in `frontend/src/features/ai/ChatView/WaitingIndicator.tsx`
  - Static message: "Waiting for your response" with pulse dot
  - Fade-out: 200ms on state change
  - ARIA: role="status", aria-live="polite"
  - Tailwind: "flex items-center gap-2 px-4 py-3 border-t bg-muted/30 text-sm text-muted-foreground"

- [ ] T10 Modify StreamingBanner to yield to WaitingIndicator in `frontend/src/features/ai/ChatView/StreamingBanner.tsx`
  - When state is QUESTION_PENDING or APPROVAL_PENDING, hide StreamingBanner, show WaitingIndicator
  - States are mutually exclusive (streaming vs waiting)

- [ ] T11 Integrate QuestionBlock + WaitingIndicator into ChatView in `frontend/src/features/ai/ChatView/ChatView.tsx`
  - Render QuestionBlock when pendingQuestion is set
  - Render WaitingIndicator when state is QUESTION_PENDING or APPROVAL_PENDING
  - Wire onSubmit → PilotSpaceStore.submitQuestionAnswer()

- [ ] T12 Delete old QuestionCard in `frontend/src/features/ai/ChatView/MessageList/QuestionCard.tsx`
  - Remove file, update all imports to use QuestionBlock

**Checkpoint**: AI asks questions inline with stepped flow, option selection, collapse animation, and waiting indicator.

---

## Phase 3: Approvals (US-2, US-3)

### Tests

- [ ] T13 [P] Write component tests for InlineApprovalCard in `frontend/tests/InlineApprovalCard.test.tsx`
  - Test: renders with action name, description, Approve/Reject buttons
  - Test: Approve collapses to "[action] approved"
  - Test: Reject shows inline text field for optional reason
  - Test: "View details" toggles payload preview
  - Test: keyboard Enter=approve, Escape=reject (FR-019)
  - Test: ARIA role="region" with action label

- [ ] T14 [P] Write component tests for DestructiveApprovalModal in `frontend/tests/DestructiveApprovalModal.test.tsx`
  - Test: renders with red warning header, affected items list, Confirm/Cancel
  - Test: Confirm executes and closes modal
  - Test: Cancel/Escape closes modal, AI receives rejection
  - Test: auto-cancels after 5 minutes (FR-008)
  - Test: no undo after destructive action
  - Test: focus trapped inside modal, returns to trigger on close
  - Test: ARIA role="alertdialog", aria-modal="true"

### Implementation

- [ ] T15 Create InlineApprovalCard component in `frontend/src/features/ai/ChatView/MessageList/InlineApprovalCard.tsx`
  - States: Default, Expanded (payload preview), Approving (spinner), Approved (collapsed), Rejected (collapsed + reason)
  - Single visual style — no severity prop or badges in v1 (FR-006)
  - "View details" toggle: expands card to show payload preview
  - Approve: card collapses to "[action] approved". Execute immediately, no undo.
  - Reject: collapsed inline text field for optional reason (FR-017). Card collapses to "[action] rejected — [reason]"
  - Animations: slide-in entrance (200ms), approval collapse (250ms), dismissal slide-out (200ms)
  - Keyboard: Enter=approve, Escape=reject (FR-019)
  - ARIA: role="region", aria-label="Approval: {action}" (FR-020)
  - Respects prefers-reduced-motion
  - Reference UX spec section 7.2 for Tailwind classes (ignore severity border colors — single style for v1)

- [ ] T16 Create DestructiveApprovalModal in `frontend/src/features/ai/ChatView/ApprovalOverlay/DestructiveApprovalModal.tsx`
  - Standard confirm dialog: red warning header, action description, consequence text, affected items list, Confirm/Cancel buttons
  - No typed confirmation — Confirm is immediately enabled
  - 5-minute auto-cancel timer (FR-008, matches SDK timeout): calls onReject with "Timed out"
  - No undo after confirmation (destructive = final)
  - Chat shows "[action] executed" with warning indicator
  - Focus trap: Tab cycles through elements. Escape = Cancel
  - ARIA: role="alertdialog", aria-modal="true", aria-labelledby, aria-describedby
  - Reference UX spec section 7.3 for layout

- [ ] T17 Integrate InlineApprovalCard + DestructiveApprovalModal into ChatView in `frontend/src/features/ai/ChatView/ChatView.tsx`
  - Non-destructive (CRITICAL_REQUIRE=false) → InlineApprovalCard
  - Destructive (CRITICAL_REQUIRE=true) → DestructiveApprovalModal
  - Multiple non-destructive approvals stack vertically (US-2 scenario 4)
  - Wire onApprove, onReject to existing store actions

- [ ] T18 Delete old approval components
  - Delete `ChatView/MessageList/SuggestionCard.tsx`, update imports → InlineApprovalCard
  - Delete `ChatView/ApprovalOverlay/ApprovalDialog.tsx`, update imports → DestructiveApprovalModal
  - Delete `ChatView/ApprovalOverlay/ApprovalOverlay.tsx` (floating button removed)
  - Delete `components/ai/ApprovalDialog.tsx` (approval queue page gets its own component in v2)
  - Retain: IssuePreview.tsx, ContentDiff.tsx, GenericJSON.tsx (reused)

**Checkpoint**: Non-destructive approvals inline, destructive actions get confirm modal. Old components deleted.

---

## Phase 4: Polish + Quality Gates

- [ ] T19 Add session recovery for pending state on browser refresh in `frontend/src/stores/ai/PilotSpaceStore.ts`
  - On session recovery from backend: restore pendingQuestion and pending approvals
  - Re-render components with preserved state (FR-011)

- [ ] T20 Verify all acceptance scenarios manually
  - US-1: AI asks question → user answers → AI continues
  - US-2: Non-destructive approval → approve → AI proceeds immediately
  - US-3: Destructive action → modal → confirm → executed
  - US-4: Waiting indicator visible during pending states
  - Edge: sidebar close/reopen preserves state
  - Edge: browser refresh restores pending state

- [ ] T21 Run full quality gates and verify coverage >80%
  - Backend: `uv run pyright && uv run ruff check && uv run pytest --cov=.`
  - Frontend: `pnpm lint && pnpm type-check && pnpm test`
  - Verify no remaining references to deleted QuestionCard, SuggestionCard, ApprovalDialog, ApprovalOverlay
  - Verify all new files under 700 lines

**Checkpoint**: Feature complete. All quality gates pass. All scenarios verified.

---

## Dependencies

```
Phase 1 (Foundation) → Phase 2 (Questions + Waiting) → Phase 3 (Approvals) → Phase 4 (Polish + QA)
```

- Phase 2 + Phase 3 are independent of each other (both depend on Phase 1 only) and could run in parallel.
- Within each phase: Tests first → Implementation → Integration → Cleanup.

---

## Task Summary

| Phase | Tasks | Description |
|-------|-------|-------------|
| Phase 1: Foundation | T01–T04 (5) | Backend adapter, SSE rename + chat routing, session recovery, frontend types + store |
| Phase 2: Questions + Waiting | T05–T12 (8) | QuestionBlock, WaitingIndicator, tests, integration |
| Phase 3: Approvals | T13–T18 (6) | InlineApprovalCard, DestructiveModal, tests, cleanup |
| Phase 4: Polish + QA | T19–T21 (3) | Session recovery frontend, manual verification, quality gates |
| Phase V: Validation | V01–V06 (6) | Cross-artifact audit, FR coverage, UX spec alignment |
| **Total** | **28 tasks** | |

---

## Phase V: Validation (run after each phase, mandatory before merge)

- [ ] V01 Cross-artifact consistency check
  - Verify every FR in spec.md has a corresponding task in tasks.md
  - Verify every task references the correct FR
  - Verify plan.md component names match task file paths
  - Verify spec edge cases are covered by tasks or explicitly accepted as out-of-scope

- [ ] V02 Answer path end-to-end verification
  - Verify the full question flow: SDK AskUserQuestion → adapter → SSE `question_request` → frontend QuestionBlock → user submits → `POST /chat` with `[ANSWER:questionId]` prefix → chat handler parses prefix → adapter resolves SDK callback → agent continues
  - Verify a normal chat message (no `[ANSWER:]` prefix) passes through to agent normally
  - Verify `POST /answer` returns 404 (removed)
  - This is the most critical integration path — test manually before Phase 2 checkpoint

- [ ] V03 Verify FR-012: session expiry auto-rejects pending approvals
  - Check if existing session expiry code already cascades to `AIApprovalRequest` table
  - If not, add backend logic to update pending approvals to `expired` on session cleanup
  - Questions: SDK timeout (5 min) handles this — no additional work needed

- [ ] V04 UX spec alignment check
  - Add deprecation note at top of `approval-input-ux-spec.md` listing v1 deferrals:
    - Section 4.2 (Edit & Approve) → deferred
    - Section 4.4 (BatchApprovalCard) → deferred
    - Sections 5.4 + 7.8 (UndoToast) → deferred (v1: approve = execute immediately, inline Cancel link per FR-011 is also deferred)
    - Section 5.3 + 7.6 (ApprovalHistorySummary) → deferred
    - Section 5.5 (Token cost indicator) → deferred
  - Ensures implementers referencing UX spec don't build deferred features

- [ ] V05 Verify SDK adapter doesn't break SDK contracts
  - Confirm SDK still blocks agent during pending question (FR-014)
  - Confirm SDK still auto-timeouts after 5 minutes (FR-015)
  - Confirm adapter's in-memory registry is cleaned up after answer/timeout (no memory leak)
  - Run with 2+ concurrent questions in different sessions to verify isolation

- [ ] V06 Verify no orphaned references after migration
  - Search codebase for imports of: QuestionCard, SuggestionCard, ApprovalDialog (both locations), ApprovalOverlay
  - Search for SSE event name `ask_user_question` (should be fully renamed to `question_request`)
  - Search for references to `POST /answer` endpoint (should be fully removed)
  - Verify retained components (features/approvals/ApprovalCard, ApprovalDetailModal) still work without `components/ai/ApprovalDialog`

---

## Deferred to v2

| Feature | Why Deferred |
|---------|-------------|
| SeverityBadge (safe/caution/critical) | 2 tiers sufficient for v1. Add visual severity in v2. |
| Edit & Approve | Reject + re-ask is simpler. Add editable payloads in v2. |
| 8-second undo window | Requires backend hold + cancel endpoint. Add in v2. |
| BatchApprovalCard | Multiple approvals stack vertically for now. Add grouped batch in v2. |
| ApprovalHistorySummary | Session history counter. Nice-to-have for v2. |
| Token cost indicator | Not in core FRs. Add in v2. |
| Typed confirmation (destructive) | Standard confirm dialog sufficient. Add GitHub-style typed phrase in v2. |
| WaitingIndicator escalation + scroll | Static banner sufficient. Add 60s escalation + click-to-scroll in v2. |

# Tasks: Daily Routine — Contextual AI Chat Experience

**Feature**: Daily Routine — Contextual AI Chat Experience
**Branch**: `019-daily-routine`
**Created**: 2026-02-20
**Source**: `specs/019-daily-routine/`
**Author**: Tin Dang

---

## Phase 1: Setup & Bug Fixes

- [ ] T001 Fix `noteId: ''` bug in `frontend/src/features/notes/editor/extensions/MarginAnnotationAutoTriggerExtension.ts` — pass noteId from NoteCanvasEditor through extension config (FR-020)
- [ ] T002 [P] Add `daily-standup` to skill menu in `frontend/src/features/ai/ChatView/constants.ts` — add entry with description "Generate daily standup summary" (FR-006)
- [ ] T003 [P] Send `blockType` field from `frontend/src/features/notes/editor/extensions/GhostTextExtension.ts` — extract current block type from ProseMirror node and include in API payload (FR-015)

**Checkpoint**: Annotation bug fixed (noteId flows correctly). Ghost text sends blockType. Standup skill appears in command menu. Quality gates pass.

---

## Phase 2: Foundation — Backend Enhancements

- [ ] T004 Create `daily-standup/SKILL.md` in `backend/src/pilot_space/ai/templates/skills/daily-standup/` — skill prompt instructs agent to query issues by state transitions (yesterday completed, today in-progress, blocked), format as standup with 3 sections, handle Monday/weekend lookback (FR-007, FR-009)
- [ ] T005 [P] Enhance `_build_prompt()` in `backend/src/pilot_space/ai/services/ghost_text.py` — add block-type routing: if `block_type == "codeBlock"` use existing `build_code_ghost_text_prompt`, if `heading` use outline prompt, if `bulletList` use list-continuation prompt. Accept `note_title` and `linked_issues` for context injection (FR-015, FR-016)
- [ ] T006 [P] Enhance ghost text prompt templates in `backend/src/pilot_space/ai/prompts/ghost_text.py` — add `build_heading_ghost_text_prompt` and `build_list_ghost_text_prompt` functions alongside existing `build_code_ghost_text_prompt` (FR-015)
- [ ] T007 [P] Accept `block_type`, `note_title`, `linked_issues` params in `backend/src/pilot_space/api/v1/routers/ghost_text.py` — add optional fields to request schema, pass through to GhostTextService (FR-015, FR-016)
- [ ] T008 Write unit tests for block-type routing in `backend/tests/unit/ai/services/test_ghost_text.py` — test paragraph/heading/code/bulletList routing, test note context injection into prompt (FR-015, FR-016)
- [ ] T009 [P] Write unit tests for daily-standup skill loading in `backend/tests/unit/ai/templates/test_daily_standup_skill.py` — verify SKILL.md parses correctly, contains required sections (FR-006)

**Checkpoint**: Ghost text routes by block type. Daily standup skill defined. Backend quality gates pass: `uv run pyright && uv run ruff check && uv run pytest`

---

## Phase 3: User Story 1 — AI-Powered Daily Briefing (P1) — MVP

**Goal**: Wire existing backend digest to frontend homepage. Users see categorized AI insights with contextual prompts.
**Verify**: Open homepage with active workspace data → see digest cards, click prompt → ChatView responds with context.

### Tests

- [ ] T010 [P] [US1] Write unit tests for `useWorkspaceDigest` hook in `frontend/src/features/homepage/hooks/__tests__/useWorkspaceDigest.test.ts` — test fetch, stale time, background refresh, error states (FR-001, FR-003)
- [ ] T011 [P] [US1] Write unit tests for `DigestInsights` component in `frontend/src/features/homepage/components/__tests__/DigestInsights.test.ts` — test category rendering, empty category hiding, dismiss action, freshness indicator (FR-001, FR-003, FR-004, FR-005)
- [ ] T012 [P] [US1] Write unit tests for contextual prompt generation in `frontend/src/features/homepage/components/__tests__/HomepageHub.test.ts` — test prompt derivation from digest data, fallback to static prompts when no digest (FR-002)

### Implementation

- [ ] T013 [US1] Create `useWorkspaceDigest` hook in `frontend/src/features/homepage/hooks/useWorkspaceDigest.ts` — TanStack Query wrapper calling `GET /workspaces/{id}/homepage/digest`, staleTime 60s, refetchInterval 300s, expose `dismiss` mutation calling `POST /homepage/dismiss` with optimistic update (FR-001, FR-003, FR-005)
- [ ] T014 [US1] Create `DigestInsights` component in `frontend/src/features/homepage/components/DigestInsights.tsx` — render categorized insight cards (stale_issues, unlinked_notes, cycle_risk, blocked_deps, overdue_items), each with icon + count + item list + dismiss button. Hide empty categories. Show freshness timestamp in header. (FR-001, FR-003, FR-004, FR-005)
- [ ] T015 [US1] Replace static AI Insights section in `frontend/src/features/homepage/components/DailyBrief.tsx` — replace hardcoded placeholder with `DigestInsights` component, pass workspace data from `useWorkspaceDigest` hook (FR-001)
- [ ] T016 [US1] Replace static `HOMEPAGE_PROMPTS` in `frontend/src/features/homepage/components/HomepageHub.tsx` — derive `suggestedPrompts` from digest data: map insight categories to actionable prompts (e.g., stale issues → "Review N stale issues"), fall back to static prompts only when no digest data available (FR-002)

**Checkpoint**: US1 complete — homepage shows live AI digest cards with contextual prompts. Dismiss works. Freshness indicator visible. Verify with quickstart Scenario 1.

---

## Phase 4: User Story 2 — Daily Standup Generator (P2)

**Goal**: One-click standup generation on homepage with copy-to-clipboard.
**Verify**: Click "Generate Standup" → AI produces formatted yesterday/today/blockers → copy works.

### Tests

- [ ] T017 [P] [US2] Write unit tests for StandupButton in `frontend/src/features/homepage/components/__tests__/DailyBrief.test.ts` — test button renders, click sends standup command to ChatView, loading state during generation (FR-006)

### Implementation

- [ ] T018 [US2] Add "Generate Standup" button in `frontend/src/features/homepage/components/DailyBrief.tsx` — button in DailyBrief header area, onClick sends `\daily-standup` command to `aiStore.pilotSpace.sendMessage()` and opens ChatView panel (FR-006, FR-008)
- [ ] T019 [US2] Add copy-to-clipboard for standup structured result in `frontend/src/features/ai/ChatView/ChatView.tsx` — detect `structured_result` of type `standup` in message list, render with copy button that calls `navigator.clipboard.writeText()` + shows toast (FR-008)

**Checkpoint**: US2 complete — "Generate Standup" button produces formatted standup. Copy works. Verify with quickstart Scenario 2.

---

## Phase 5: User Story 3 — Note Health Indicator & Proactive Suggestions (P2)

**Goal**: Note editor shows health badges and contextual ChatView prompts. Ghost text adapts to block type.
**Verify**: Open note with mixed content → see health badges → ChatView shows note-specific prompts → ghost text adapts per block.

### Tests

- [ ] T020 [P] [US3] Write unit tests for `useNoteHealth` hook in `frontend/src/hooks/__tests__/useNoteHealth.test.ts` — test extractable count calculation, clarity issue detection, linked issue fetching, debounced refresh (FR-010, FR-012)
- [ ] T021 [P] [US3] Write unit tests for `NoteHealthBadges` component in `frontend/src/components/editor/__tests__/NoteHealthBadges.test.ts` — test badge rendering with counts, click handlers send correct messages, empty state hidden (FR-010, FR-011)
- [ ] T022 [P] [US3] Write unit tests for enhanced `GhostTextStore` in `frontend/src/stores/ai/__tests__/GhostTextStore.test.ts` — test blockType and note context included in API payload (FR-015, FR-016)

### Implementation

- [ ] T023 [US3] Create `useNoteHealth` hook in `frontend/src/hooks/useNoteHealth.ts` — compute: extractable issue count by scanning note blocks for actionable verb patterns (implement/fix/add/create/update/remove), clarity issues from annotation store data, linked issues from note-issue-links API. Debounced 5s refresh on content change. Cache per noteId. (FR-010, FR-012)
- [ ] T024 [US3] Create `NoteHealthBadges` component in `frontend/src/components/editor/NoteHealthBadges.tsx` — render badges: extractable count (orange), clarity issues (yellow), linked issues (teal). Each badge clickable → sends pre-filled prompt to ChatView via `aiStore.pilotSpace.sendMessage()` and opens panel. Hidden when all counts are 0. (FR-010, FR-011)
- [ ] T025 [US3] Integrate health badges into `frontend/src/components/editor/NoteCanvasEditor.tsx` — add `useNoteHealth(noteId, editor)` hook, render `NoteHealthBadges` in editor toolbar area. Pass health-derived prompts as `suggestedPrompts` to ChatView. (FR-010, FR-013)
- [ ] T026 [US3] Enhance `frontend/src/stores/ai/GhostTextStore.ts` — include `blockType`, `noteTitle`, and `linkedIssues` in API request payload sent to ghost text endpoint (FR-015, FR-016)
- [ ] T027 [US3] Pass note-specific suggested prompts to ChatView in `frontend/src/components/editor/NoteCanvasEditor.tsx` — derive prompts from health analysis (e.g., "Extract N issues", "Improve clarity in N sections") and pass as `suggestedPrompts` prop to ChatView, replacing generic prompts (FR-013, FR-014)

**Checkpoint**: US3 complete — note health badges visible, contextual prompts in ChatView, ghost text adapts to block type. Verify with quickstart Scenarios 3 and 5.

---

## Phase 6: User Story 4 — Annotation-to-Action Pipeline (P3)

**Goal**: Annotation cards have action buttons that directly trigger AI operations.
**Verify**: Edit note → annotations appear → click action button → relevant AI flow starts.

### Tests

- [ ] T028 [P] [US4] Write unit tests for annotation action buttons in `frontend/src/features/notes/components/__tests__/annotation-card.test.ts` — test "Extract Issue" button on issue_candidate, "Ask AI" on clarification, "Create Task" on action_item, loading state (FR-017, FR-018, FR-019)

### Implementation

- [ ] T029 [US4] Add action buttons to `frontend/src/features/notes/components/annotation-card.tsx` — per annotation type: `issue_candidate` → "Extract Issue" (sends `/extract-issues` with block context to ChatView), `clarification` → "Ask AI" (sends clarification prompt to ChatView), `action_item` → "Create Task" (sends `/create-issue` with action item text). Each button opens ChatView panel. (FR-017, FR-018, FR-019)
- [ ] T030 [US4] Pass `noteId` to `MarginAnnotationAutoTriggerExtension` in `frontend/src/components/editor/NoteCanvasEditor.tsx` — update extension config to include noteId from note context, ensuring annotations have correct note identity for persistence (FR-020, complements T001)

**Checkpoint**: US4 complete — annotation cards have action buttons, clicking triggers correct AI flow. Verify with quickstart Scenario 4.

---

## Phase 7: User Story 5 — Homepage Context Injection (P3)

**Goal**: ChatView on homepage has digest data pre-loaded so AI responds instantly.
**Verify**: Ask "What should I focus on today?" on homepage → AI responds with specific workspace data, no visible tool calls.

### Tests

- [ ] T031 [P] [US5] Write unit tests for context injection in `frontend/src/stores/ai/__tests__/PilotSpaceStore.test.ts` — test `setHomepageContext()` injects digest data, `clearHomepageContext()` removes it, context transitions between homepage and note (FR-021)

### Implementation

- [ ] T032 [US5] Add `setHomepageContext()` and `clearHomepageContext()` to `frontend/src/stores/ai/PilotSpaceStore.ts` — store digest summary (insight categories, active issue counts, recent notes) as `homepageContext` in conversation context. Include in `sendMessage` payload as metadata. (FR-014, FR-021)
- [ ] T033 [US5] Inject homepage context in `frontend/src/features/homepage/components/HomepageHub.tsx` — on mount, call `aiStore.pilotSpace.setHomepageContext(digestData)` with digest + activity data. On unmount, call `clearHomepageContext()`. (FR-021)
- [ ] T034 [US5] Handle context transition in `frontend/src/stores/ai/PilotSpaceActions.ts` — when `setNoteContext()` is called, auto-clear homepage context. When `setHomepageContext()` is called, auto-clear note context. Ensure clean context switching. (FR-021)

**Checkpoint**: US5 complete — homepage ChatView has pre-loaded context. AI responds to "What should I focus on today?" with specific insights. Verify with quickstart Scenario 1, step 7-8.

---

## Phase Final: Polish

- [ ] T035 [P] Run full quickstart validation — all 5 scenarios from plan.md
- [ ] T036 [P] Verify test coverage >80% for all new files — `pnpm test --coverage` and `uv run pytest --cov`
- [ ] T037 Code cleanup — verify all new/modified files under 700 lines, remove dead code
- [ ] T038 Run full quality gates: `uv run pyright && uv run ruff check && uv run pytest --cov=.` (backend) and `pnpm lint && pnpm type-check && pnpm test` (frontend)

**Checkpoint**: Feature complete. All quality gates pass. All quickstart scenarios verified.

---

## Dependencies

### Phase Order

```
Phase 1 (Setup/Fixes) → Phase 2 (Backend) → Phase 3-7 (Stories) → Phase Final (Polish)
```

### Story Independence

- [x] US1 (Daily Briefing) and US2 (Standup) can run in parallel after Phase 2 (different components)
- [x] US3 (Note Health) and US4 (Annotations) can run in parallel (different components, both in note editor)
- [x] US5 (Context Injection) depends on US1 (needs digest data to inject)
- [x] US4 depends on T001 (annotation noteId fix from Phase 1)

### Within Each Story

```
Tests (write, verify fail) → Implementation → Checkpoint verification
```

### Parallel Opportunities

| Phase | Parallel Group | Tasks |
|-------|---------------|-------|
| Phase 1 | Bug fixes | T001, T002, T003 |
| Phase 2 | Backend enhancements | T004, T005+T006, T007, T008+T009 |
| Phase 3 | US1 tests | T010, T011, T012 |
| Phase 4+5 | US2 + US3 (parallel stories) | T017-T019 ∥ T020-T027 |
| Phase 5+6 | US3 + US4 (parallel stories) | T023-T027 ∥ T028-T030 |
| Phase Final | Polish | T035, T036 |

---

## Execution Strategy

**Selected Strategy**: B: Incremental — stable requirements from deep-context analysis. Deploy after each story for continuous feedback.

```
Phase 1 (Fixes) → Phase 2 (Backend) → US1 (MVP Briefing) → US2+US3 (parallel) → US4+US5 (parallel) → Polish
```

---

## Validation Checklists

### Coverage Completeness

- [x] Every user story from spec.md has a task phase (US1→Phase 3, US2→Phase 4, US3→Phase 5, US4→Phase 6, US5→Phase 7)
- [x] Every entity from data-model has a creation/wiring task (WorkspaceDigest→T013, NoteHealthAnalysis→T023)
- [x] Every endpoint interaction has an implementation task (digest→T013, ghost text→T005+T007+T026, dismiss→T013)
- [x] Every quickstart scenario has a validation task (T035)
- [x] Setup and Polish phases included

### Task Quality

- [x] Task IDs sequential (T001-T038) with no gaps
- [x] Each task has exact file path
- [x] Each task starts with imperative verb
- [x] One responsibility per task
- [x] `[P]` markers only where tasks are truly independent
- [x] `[USn]` markers on all Phase 3+ tasks

### Dependency Integrity

- [x] No circular dependencies
- [x] Phase order enforced: Setup → Foundation → Stories → Polish
- [x] Within-story order: Tests → Implementation → Checkpoint
- [x] Cross-story shared entities placed in Foundation phase (ghost text backend in Phase 2)
- [x] Each phase has a checkpoint statement

### Execution Readiness

- [x] Any developer can pick up any task and execute without questions
- [x] File paths match plan.md project structure exactly
- [x] Quality gate commands specified in Polish phase
- [x] Execution strategy selected with rationale

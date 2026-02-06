# Tasks: Onboarding Launch Page

**Feature**: Onboarding Launch Page
**Branch**: `010-onboarding-launch`
**Created**: 2026-02-05
**Source**: `specs/010-onboarding-launch/`
**Author**: Tin Dang

---

## Phase 1: Setup

- [ ] T001 Create feature branch `010-onboarding-launch` from main
- [ ] T002 Create `features/onboarding/` directory structure in `frontend/src/features/onboarding/` with `components/`, `hooks/`, `__tests__/`, and `index.ts` barrel export
- [ ] T003 [P] Create onboarding Pydantic schemas in `backend/src/pilot_space/api/v1/schemas/onboarding.py` — request/response types for GET/PATCH onboarding state, POST validate, POST guided-note
- [ ] T004 [P] Create OnboardingStore (MobX UI state) in `frontend/src/stores/onboarding-store.ts` — track collapsed state, active step, celebration trigger
- [ ] T005 [P] Register OnboardingStore in RootStore in `frontend/src/stores/root-store.ts` — add to store hierarchy with proper initialization
- [ ] T006 [P] Create onboarding API client in `frontend/src/services/api/onboarding.ts` — typed functions for getOnboardingState(), updateOnboardingStep(), dismissOnboarding(), validateProviderKey(), createGuidedNote()

**Checkpoint**: Directory structure exists. Schema types compile. MobX store initializes and is accessible via `useStore()`. API client functions are typed. `pnpm type-check` and `uv run pyright` pass.

---

## Phase 2: Foundation — Backend Data Layer

- [ ] T007 Create WorkspaceOnboarding domain entity in `backend/src/pilot_space/domain/onboarding.py` with 3-step tracking (ai_providers, invite_members, first_note), completion logic, and dismiss behavior per spec FR-001/FR-002/FR-003
- [ ] T008 Create WorkspaceOnboarding SQLAlchemy model in `backend/src/pilot_space/infrastructure/database/models/onboarding.py` with JSONB steps column (3 steps: ai_providers, invite_members, first_note), workspace_id FK (UNIQUE), guided_note_id FK, dismissed_at, completed_at per plan data model
- [ ] T009 Add `is_guided_template` boolean column to Note model in `backend/src/pilot_space/infrastructure/database/models/note.py` — default False, used to identify onboarding guided notes
- [ ] T010 Create Alembic migration for `workspace_onboarding` table AND `is_guided_template` column on `notes` table, with RLS policy: `workspace_id IN (SELECT workspace_id FROM workspace_members WHERE user_id = auth.uid() AND role IN ('owner', 'admin'))` per DD-061
- [ ] T011 Create OnboardingRepository in `backend/src/pilot_space/infrastructure/database/repositories/onboarding_repository.py` extending BaseRepository with get_by_workspace_id(), upsert_step(), set_dismissed(), set_completed() methods
- [ ] T012 Create OnboardingService in `backend/src/pilot_space/application/services/onboarding.py` implementing CQRS-lite pattern with get_onboarding_state(), complete_step(), dismiss_onboarding(), create_guided_note() per DD-064

**Checkpoint**: Domain entity, model, repository, and service compile. Migration applies successfully (both tables). `uv run pyright` passes.

---

## Phase 3: User Story 1 — Guided Workspace Setup (P1) — MVP

**Goal**: Workspace owners/admins see an onboarding checklist with 3 steps and progress tracking that persists across sessions. Regular members see a welcome banner instead.
**Verify**: Create workspace as owner → see checklist (3 steps) → complete a step → refresh → step still complete. Log in as member → see welcome banner, no checklist.

### Tests

- [ ] T013 [P] [US1] Write unit tests for OnboardingService in `backend/tests/unit/services/test_onboarding_service.py` covering get_state, complete_step, dismiss, completion detection (3 steps)
- [ ] T014 [P] [US1] Write integration tests for onboarding API endpoints in `backend/tests/integration/api/test_onboarding_router.py` covering GET/PATCH with auth, RLS enforcement, and owner/admin-only access
- [ ] T015 [P] [US1] Write unit tests for OnboardingChecklist component in `frontend/src/features/onboarding/__tests__/onboarding-checklist.test.tsx` covering render states (0/3 to 3/3), click handlers, dismiss behavior, owner/admin visibility gate

### Implementation — Backend

- [ ] T016 [US1] Create onboarding router in `backend/src/pilot_space/api/v1/routers/onboarding.py` with GET `/workspaces/{id}/onboarding` and PATCH `/workspaces/{id}/onboarding` endpoints per plan API contracts
- [ ] T017 [US1] Register onboarding router in `backend/src/pilot_space/api/v1/routers/__init__.py` and add DI wiring for OnboardingService and OnboardingRepository in `backend/src/pilot_space/infrastructure/di/container.py`
- [ ] T018 [US1] Add auto-creation of WorkspaceOnboarding record in WorkspaceService.create_workspace() in `backend/src/pilot_space/application/services/workspace.py` — create onboarding record with default steps when workspace is created

### Implementation — Frontend

- [ ] T019 [US1] Create useOnboardingState hook in `frontend/src/features/onboarding/hooks/useOnboardingState.ts` using TanStack Query to fetch via onboardingApi.getOnboardingState()
- [ ] T020 [US1] Create useOnboardingActions hook in `frontend/src/features/onboarding/hooks/useOnboardingActions.ts` with useMutation for step completion and dismiss via onboardingApi
- [ ] T021 [US1] Create OnboardingStepItem component in `frontend/src/features/onboarding/components/onboarding-step-item.tsx` rendering step title, description, icon, completion checkmark, and click-to-navigate behavior
- [ ] T022 [US1] Create OnboardingChecklist component in `frontend/src/features/onboarding/components/onboarding-checklist.tsx` rendering 3 steps with progress bar (N/3), dismiss button, and subtle celebration trigger (animated checkmark + "All set!" auto-collapse 3s) per FR-001/FR-013. Must respect prefers-reduced-motion
- [ ] T023 [US1] Create WelcomeBanner component in `frontend/src/features/onboarding/components/welcome-banner.tsx` — simplified banner for non-admin members with links to Notes, Issues, and Settings
- [ ] T024 [US1] Integrate OnboardingChecklist into workspace home page in `frontend/src/app/(workspace)/[workspaceSlug]/page.tsx` — render checklist above existing template cards when onboarding is incomplete AND user is owner/admin. For regular members, render WelcomeBanner instead (FR-016). Replace hardcoded recent notes with real data query

**Checkpoint**: US1 complete — Workspace owner sees 3-step onboarding checklist, steps persist across refresh, dismiss collapses to sidebar reminder. Regular member sees welcome banner. Verify with quickstart Scenario 1 (steps 1-3), Scenario 2, and Scenario 4.

---

## Phase 4: User Story 2 — Anthropic API Key Validation (P1)

**Goal**: Users validate their Anthropic API key during onboarding via a separate validation endpoint with clear status and feature unlock indicators.
**Verify**: Enter Anthropic key → validate via backend → see green checkmark → see which features are unlocked.

### Tests

- [ ] T025 [P] [US2] Write unit tests for AIProviderKeyValidator in `backend/tests/unit/services/test_key_validator.py` covering successful Anthropic validation, invalid key format, invalid auth, provider unreachable (timeout >10s)
- [ ] T026 [P] [US2] Write integration tests for validate endpoint in `backend/tests/integration/api/test_ai_provider_validation.py` covering POST with valid/invalid Anthropic key, 502 on provider down, 403 for non-admin
- [ ] T027 [P] [US2] Write unit tests for FeatureUnlockSummary in `frontend/src/features/onboarding/__tests__/feature-unlock-summary.test.tsx` covering Anthropic configured vs not configured states

### Implementation — Backend

- [ ] T028 [US2] Create AIProviderKeyValidator in `backend/src/pilot_space/ai/providers/key_validator.py` with validate_anthropic_key(api_key) method that calls Anthropic GET /v1/models with 10s timeout. Return valid/invalid with error message and available models list. Extensible for future providers
- [ ] T029 [US2] Add POST `/workspaces/{id}/ai-providers/validate` endpoint to onboarding router in `backend/src/pilot_space/api/v1/routers/onboarding.py` per plan API contract — separate from existing save endpoint, validates without persisting

### Implementation — Frontend

- [ ] T030 [US2] Enhance existing ProviderStatusCard in `frontend/src/features/settings/components/provider-status-card.tsx` — add "Validate" button that calls onboardingApi.validateProviderKey(), show validating spinner, display specific error messages from backend response
- [ ] T031 [US2] Create FeatureUnlockSummary component in `frontend/src/features/onboarding/components/feature-unlock-summary.tsx` mapping Anthropic key → available features (ghost text, code review, annotations, issue extraction, doc generation). Show as checklist with green checkmarks
- [ ] T032 [US2] Enhance AI Providers settings page in `frontend/src/features/settings/pages/ai-settings-page.tsx` to detect `?onboarding=true` query param for contextual guidance banner ("Anthropic key is required for AI features"), and trigger onboarding step completion on successful validation via useOnboardingActions
- [ ] T033 [US2] Create AIKeyRequiredBanner component in `frontend/src/features/onboarding/components/ai-key-required-banner.tsx` — soft warning banner for display in note editor when Anthropic key not configured, with direct link to AI Providers settings per FR-015

**Checkpoint**: US2 complete — Anthropic key validates via separate endpoint, status indicator shows valid/invalid with specific errors, feature unlock summary visible. Verify with quickstart Scenario 1 (steps 4-6) and Scenario 3.

---

## Phase 5: User Story 3 — Team Member Invitation (P2)

**Goal**: Users invite team members from the onboarding checklist with role selection.
**Verify**: Click invite from checklist → dialog opens → send invite → invitee appears in pending list → step marked complete.

### Tests

- [ ] T034 [P] [US3] Write unit tests for onboarding invitation trigger in `frontend/src/features/onboarding/__tests__/invite-from-onboarding.test.tsx` covering dialog open from checklist, step completion on successful invite

### Implementation

- [ ] T035 [US3] Add onboarding trigger to InviteMemberDialog in `frontend/src/features/settings/components/invite-member-dialog.tsx` — accept optional `onSuccess` callback prop that completes the invite_members onboarding step via useOnboardingActions
- [ ] T036 [US3] Wire "Invite Members" checklist step to open InviteMemberDialog in `frontend/src/features/onboarding/components/onboarding-checklist.tsx` — pass onSuccess callback that marks step complete

**Checkpoint**: US3 complete — Invite dialog opens from checklist, successful invite marks step complete. Reuses existing invitation backend with no changes needed. Verify with quickstart Scenario 1 (steps 7-9).

---

## Phase 6: User Story 4 — Guided First Note with AI (P1)

**Goal**: Users create a guided note ("Planning authentication for our app") with AI features demonstrated via contextual tooltips. Soft enforcement: if AI keys not configured, show warning banner but allow writing.
**Verify**: Click "Write First Note" → note created with template → ghost text appears with tooltip (if key configured) → annotations explained. Without key: warning banner shown, no AI tooltips.

### Tests

- [ ] T037 [P] [US4] Write unit tests for guided note creation in `backend/tests/unit/services/test_onboarding_guided_note.py` covering template creation, duplicate prevention (409), note content structure, is_guided_template flag
- [ ] T038 [P] [US4] Write integration tests for guided note endpoint in `backend/tests/integration/api/test_onboarding_guided_note.py` covering POST with auth, 409 on duplicate, note returned with is_guided_template=true
- [ ] T039 [P] [US4] Write unit tests for GuidedNoteTooltips in `frontend/src/features/onboarding/__tests__/guided-note-tooltips.test.tsx` covering tooltip sequence, dismiss behavior, conditional render based on AI key status

### Implementation — Backend

- [ ] T040 [US4] Add guided note template content as TipTap JSON constant in `backend/src/pilot_space/application/services/onboarding.py` — 4 paragraphs about "Planning authentication for our app" with headings, bullet points, and action verbs that trigger issue detection
- [ ] T041 [US4] Implement create_guided_note() in OnboardingService in `backend/src/pilot_space/application/services/onboarding.py` — create Note via existing NoteService with is_guided_template=True, set guided_note_id on onboarding record, return note ID and redirect URL. Return 409 if guided note already exists
- [ ] T042 [US4] Add POST `/workspaces/{id}/onboarding/guided-note` endpoint to onboarding router in `backend/src/pilot_space/api/v1/routers/onboarding.py` per plan API contract

### Implementation — Frontend

- [ ] T043 [US4] Create GuidedNoteTooltips component in `frontend/src/features/onboarding/components/guided-note-tooltips.tsx` — overlay tooltips that explain ghost text (on first appearance), margin annotations (on first annotation), and issue extraction. Only render when Anthropic key is configured. Use Popover from shadcn/ui positioned relative to editor features. Dismiss on click or after 10s auto-fade
- [ ] T044 [US4] Create WhatsNextSection component in `frontend/src/features/onboarding/components/whats-next-section.tsx` — rendered at bottom of guided note with 3 links: "Create a project", "Explore the issues board", "Connect GitHub" with icons and descriptions
- [ ] T045 [US4] Create OnboardingCelebration component in `frontend/src/features/onboarding/components/onboarding-celebration.tsx` — subtle animated checkmark with "All set!" message when all 3 steps complete, auto-collapse after 3s, respects `prefers-reduced-motion` (no confetti)
- [ ] T046 [US4] Integrate GuidedNoteTooltips and AIKeyRequiredBanner into NoteEditor in `frontend/src/app/(workspace)/[workspaceSlug]/notes/[noteId]/page.tsx` — render tooltips when note has `is_guided_template` metadata AND Anthropic key configured. Show AIKeyRequiredBanner when `is_guided_template` AND key NOT configured (soft enforce)
- [ ] T047 [US4] Wire "Write Your First Note" checklist step in `frontend/src/features/onboarding/components/onboarding-checklist.tsx` — call onboardingApi.createGuidedNote(), navigate to note editor on success, mark first_note step complete on return to home page

**Checkpoint**: US4 complete — Guided note ("Planning authentication for our app") created with template and is_guided_template=true, tooltips explain AI features when key configured, warning banner when not. Subtle celebration on 3/3 completion. Verify with quickstart Scenario 1 (steps 10-14) and Scenario 3.

---

## Phase Final: Polish

- [ ] T048 [P] Run full quickstart.md validation — all 4 scenarios (happy path, dismiss/resume, guided note without keys, regular member experience)
- [ ] T049 [P] Add missing unit tests to reach >80% coverage for `features/onboarding/` and `application/services/onboarding.py`
- [ ] T050 Code cleanup — verify all files under 700 lines, remove dead code, ensure barrel exports in `frontend/src/features/onboarding/index.ts`
- [ ] T051 [P] Write E2E test for full onboarding flow in `frontend/tests/e2e/onboarding-flow.spec.ts` — new workspace → checklist → configure keys → invite → guided note → celebration
- [ ] T052 Run full quality gates: `uv run pyright && uv run ruff check && uv run pytest --cov=.` (backend) and `pnpm lint && pnpm type-check && pnpm test` (frontend)

**Checkpoint**: Feature complete. All quality gates pass. All quickstart scenarios verified. Coverage >80%.

---

## Dependencies

### Phase Order

```
Phase 1 (Setup) -> Phase 2 (Foundation) -> Phase 3 (US1) -> Phase 4 (US2) -> Phase 5 (US3) -> Phase 6 (US4) -> Phase Final
```

### Story Independence

- [ ] US1 (checklist) must complete first — US2/US3/US4 all depend on checklist infrastructure
- [ ] US2 (AI keys) and US3 (invite) can run in parallel after US1 (different files, no shared deps)
- [ ] US4 (guided note) depends on US1 (checklist step wiring) but not US2/US3

### Within Each Story

```
Tests (write first, verify fail) -> Backend models/services/endpoints -> Frontend components/hooks -> Integration
```

### Parallel Opportunities

| Phase | Parallel Group | Tasks |
|-------|---------------|-------|
| Phase 1 | Config tasks | T003, T004, T005, T006 |
| Phase 3 | US1 tests | T013, T014, T015 |
| Phase 4 | US2 tests | T025, T026, T027 |
| Phase 4+5 | US2 + US3 (after US1) | T025-T033, T034-T036 |
| Phase 6 | US4 tests | T037, T038, T039 |
| Phase Final | Validation tasks | T048, T049, T051 |

---

## Task Quality Rules

| Rule | Good Example | Bad Example |
|------|-------------|-------------|
| Imperative verb | "Create OnboardingService" | "OnboardingService" |
| Exact file path | "in backend/src/pilot_space/application/services/onboarding.py" | "in the services folder" |
| One responsibility | "Create OnboardingChecklist component" | "Create OnboardingChecklist and wire to home page" |
| Observable outcome | "GET /onboarding returns 200 with steps object" | "Endpoint works" |
| References source | "per plan API contracts" | "per the spec" |

---

## Execution Strategy

**Selected Strategy**: B (Incremental) — Deploy after each user story for continuous validation. US1 is the foundation; US2+US3 can be developed in parallel; US4 caps the experience.

---

## Validation Checklists

### Coverage Completeness

- [x] Every user story from spec.md has a task phase (US1→Phase 3, US2→Phase 4, US3→Phase 5, US4→Phase 6)
- [x] Every entity from data-model.md has a creation task (WorkspaceOnboarding→T007/T008, Note.is_guided_template→T009)
- [x] Every endpoint from contracts has an implementation task (GET→T016, PATCH→T016, POST validate→T029, POST guided-note→T042)
- [x] Every quickstart scenario has a validation task (T044)
- [x] Setup and Polish phases included

### Task Quality

- [x] Task IDs sequential (T001-T052) with no gaps
- [x] Each task has exact file path
- [x] Each task starts with imperative verb
- [x] One responsibility per task
- [x] `[P]` markers only where tasks are truly independent
- [x] `[USn]` markers on all Phase 3+ tasks

### Dependency Integrity

- [x] No circular dependencies
- [x] Phase order enforced: Setup → Foundation → Stories → Polish
- [x] Within-story order: Tests → Backend → Frontend
- [x] Cross-story shared entities placed in Foundation phase (T007-T012)
- [x] Each phase has a checkpoint statement

### Execution Readiness

- [x] Any developer can pick up any task and execute without questions
- [x] File paths match plan.md project structure exactly
- [x] Quality gate commands specified in Polish phase
- [x] Execution strategy selected with rationale

---

## Next Phase

After this task list passes all checklists:

1. **Run consistency analysis** — Verify spec + plan + tasks alignment
2. **Assign and execute** — Each task is a self-contained work unit
3. **Track progress** — Check off tasks, verify checkpoints at phase boundaries
4. **Prepare for implementation** — Follow `references/template-implement.md` for coding steps

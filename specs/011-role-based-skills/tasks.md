# Tasks: Role-Based Skills for PilotSpace Agent

**Feature**: Role-Based Skills for PilotSpace Agent
**Branch**: `feat/skill-role-sdlc`
**Created**: 2026-02-06
**Source**: `specs/011-role-based-skills/`
**Author**: Tin Dang

---

## Phase 1: Setup

- [x] T001 ~~Create feature branch~~ — Branch `feat/skill-role-sdlc` already exists with spec artifacts committed
- [ ] T002 Create role template markdown files (8 SKILL.md templates) in `backend/src/pilot_space/ai/templates/role_templates/`

**Checkpoint**: Branch created. 8 role template files exist with SKILL.md-format content for developer, tester, business_analyst, product_owner, architect, tech_lead, project_manager, devops.

---

## Phase 2: Foundation — Database & Models

- [ ] T003 Create `UserRoleSkill` and `RoleTemplate` SQLAlchemy models in `backend/src/pilot_space/infrastructure/database/models/user_role_skill.py` per data-model.md
- [ ] T004 Create Alembic migration `025_add_role_based_skills.py` in `backend/alembic/versions/025_add_role_based_skills.py` (revises `024_enhanced_mcp_models`) — create `role_templates` table, `user_role_skills` table, add `default_sdlc_role` to `users`, add `suggested_sdlc_role` to `workspace_invitations`, seed 8 role templates, create RLS policies, update existing onboarding steps JSONB to include `role_setup`
- [ ] T005 Register new models in `backend/src/pilot_space/infrastructure/database/models/__init__.py`
- [ ] T006 Create `RoleSkillRepository` in `backend/src/pilot_space/infrastructure/database/repositories/role_skill_repository.py` — CRUD operations for `user_role_skills` and read operations for `role_templates`. Methods: `get_by_user_workspace`, `get_templates`, `create`, `update`, `delete`, `count_by_user_workspace`
- [ ] T007 Write unit tests for `RoleSkillRepository` in `backend/tests/unit/test_role_skill_repository.py` — test CRUD operations, max 3 roles constraint, unique constraint, RLS isolation

**Checkpoint**: Foundation complete. Migration runs. Models created. Repository with tests passes. `uv run pytest backend/tests/unit/test_role_skill_repository.py` green.

---

## Phase 3: User Story 1+2 — Role Selection & AI Skill Generation (P1)

**Goal**: Users select SDLC roles during onboarding and generate personalized skills via AI or templates.
**Verify**: Create workspace → onboarding shows role step → select role → generate skill → skill saved in DB.

### Backend

- [ ] T008 [US1/US2] Create Pydantic request/response schemas in `backend/src/pilot_space/api/v1/schemas/role_skill.py` — `RoleTemplateResponse`, `RoleSkillResponse`, `CreateRoleSkillRequest`, `UpdateRoleSkillRequest`, `GenerateSkillRequest`, `GenerateSkillResponse`, `RegenerateSkillRequest`
- [ ] T009 [US1/US2] Create `RoleSkillService` in `backend/src/pilot_space/application/services/role_skill_service.py` — CQRS-lite service with methods: `get_templates`, `get_user_skills`, `create_skill`, `update_skill`, `delete_skill`, `check_max_roles`, `set_primary`. Include guest restriction check (FR-020) and max 3 roles validation (FR-018)
- [ ] T010 [US2] Create `GenerateRoleSkillService` in `backend/src/pilot_space/application/services/generate_role_skill_service.py` — Uses one-shot Claude Sonnet `query()` to generate SKILL.md content from role_type + experience_description. Includes fallback to default template on provider failure. Rate limit: 5 generations/hour per user.
- [ ] T011 [US1/US2/US6] Create role skills router in `backend/src/pilot_space/api/v1/routers/role_skills.py` — Endpoints: GET `/role-templates`, GET `/workspaces/{id}/role-skills`, POST `/workspaces/{id}/role-skills`, PUT `/workspaces/{id}/role-skills/{skill_id}`, DELETE `/workspaces/{id}/role-skills/{skill_id}`, POST `/workspaces/{id}/role-skills/generate`, POST `/workspaces/{id}/role-skills/{skill_id}/regenerate` per contracts/rest-api.md
- [ ] T012 [US1] Register role skills router in `backend/src/pilot_space/main.py`
- [ ] T013 [US1] Extend existing onboarding service to include `role_setup` step — service already exists at `backend/src/pilot_space/application/services/onboarding/` with `get_onboarding_service.py`, `types.py`, `create_guided_note_service.py`. Add `role_setup: bool` field to `OnboardingStepsResult` in `types.py`, update `GetOnboardingService.execute()` to auto-sync role_setup (check if user has any role skills), update completion percentage calculation from /3 to /4 in model `completion_percentage` property at `backend/src/pilot_space/infrastructure/database/models/onboarding.py:119-132`. Step ordering: ai_providers → invite_members → role_setup → first_note (role before first note so AI is personalized for first interaction).
- [ ] T014 [US1/US2] Write unit tests for `RoleSkillService` in `backend/tests/unit/test_role_skill_service.py` — test create, update, delete, max roles, guest restriction, primary role demotion
- [ ] T015 [US2] Write unit tests for `GenerateRoleSkillService` in `backend/tests/unit/test_generate_role_skill_service.py` — test AI generation, template fallback, rate limiting
- [ ] T016 [US1/US2] Write integration tests for role skills API in `backend/tests/integration/test_role_skills_api.py` — test all 7 endpoints per contracts/rest-api.md, RLS isolation, error codes

### Frontend

- [ ] T017 [P] [US1] Create API client in `frontend/src/services/api/role-skills.ts` — typed functions for all 9 endpoints per contracts/rest-api.md
- [ ] T018 [P] [US1] Create `RoleSkillStore` (MobX) in `frontend/src/stores/role-skill-store.ts` — observable state for role selection, skill generation loading, skill editing. Register in RootStore.
- [ ] T019 [US1] Create `RoleCard` component in `frontend/src/components/role-skill/role-card.tsx` — displays role template card with icon, name, description, selected state. Used in both onboarding grid and settings.
- [ ] T020 [US1] Create `RoleSelectorStep` component in `frontend/src/features/onboarding/components/role-selector-step.tsx` — onboarding feature directory already exists with `OnboardingChecklist.tsx`, `OnboardingStepItem.tsx`, `OnboardingCelebration.tsx`. Grid of 8 role cards + custom role option, multi-select (max 3), primary designation, pre-selection from default role and workspace hint
- [ ] T021 [US2] Create `SkillGenerationWizard` component in `frontend/src/components/role-skill/skill-generation-wizard.tsx` — three paths: "Use Default", "Describe Expertise" (textarea + generate button), "Show Examples". Shows generated skill preview with accept/customize/retry actions.
- [ ] T022 [US1] Integrate `RoleSelectorStep` into onboarding flow in `frontend/src/features/onboarding/components/onboarding-checklist.tsx` — add as step 3 (before first_note per RD-004) so AI is personalized before first interaction. Step order: ai_providers → invite_members → role_setup → first_note. Wire to onboarding state.
- [ ] T023 [US1/US2] Write component tests for `RoleSelectorStep` and `SkillGenerationWizard` in `frontend/src/components/role-skill/__tests__/role-selector.test.tsx` — test role selection, multi-select limit, default pre-selection, generation flow, fallback

**Checkpoint**: US1+US2 complete. Onboarding shows role selection. User can select role, generate skill, save. Backend stores skill in DB. Verify with quickstart.md Scenario 1.

---

## Phase 4: User Story 3 — Agent Skill Injection (P1)

**Goal**: PilotSpace Agent automatically loads user's role skills and adapts behavior per workspace.
**Verify**: Configure role → chat with agent → agent response reflects role focus areas.

### Backend

- [ ] T024 [US3] Implement `_materialize_role_skills()` method in `backend/src/pilot_space/ai/agents/pilotspace_agent.py` — before `_stream_with_space` creates SDK client, query DB for user's role skills in current workspace, write each as `role-{role_type}/SKILL.md` to `space_context.path / .claude/skills/`, clean stale role skill directories. Primary role's SKILL.md includes `priority: primary` in YAML frontmatter.
- [ ] T025 [US3] Wire `_materialize_role_skills()` into `_stream_with_space()` in `backend/src/pilot_space/ai/agents/pilotspace_agent.py` — call after `space.session()` context entry and before `configure_sdk_for_space()`. Pass workspace_id and user_id from AgentContext. Requires async DB session access.
- [ ] T026 [US3] Add DB session dependency for role skill materialization in `backend/src/pilot_space/dependencies/ai.py` — extend `get_pilotspace_agent` or create a new dependency that provides role skill repository access to PilotSpaceAgent
- [ ] T027 Write unit tests for `_materialize_role_skills()` in `backend/tests/unit/test_role_skill_materialization.py` — test file writing, primary flag in frontmatter, stale cleanup, no-skills fallback, multi-role materialization

**Checkpoint**: US3 complete. Agent loads role skills from DB into sandbox space. Verify with quickstart.md Scenario 2 (Tester vs Developer behavior difference).

---

## Phase 5: User Story 4+5 — Default Role & Owner Hints (P2)

**Goal**: Users set default SDLC role in profile. Workspace owners suggest roles during invitation.
**Verify**: Set default → join new workspace → default pre-selected. Invite with hint → invitee sees suggestion.

### Backend

- [ ] T028 [P] [US4] Extend existing auth router at `backend/src/pilot_space/api/v1/routers/auth.py` — add `default_sdlc_role` field to `UpdateProfileRequest` schema and `UserProfileResponse` in `backend/src/pilot_space/api/v1/schemas/auth.py`. The existing `PATCH /auth/me` endpoint (auth.py:97) already handles profile updates — extend it to accept and persist the new field.
- [ ] T029 [P] [US5] Extend invitation create endpoint to support `suggested_sdlc_role` in `backend/src/pilot_space/api/v1/routers/workspace_members.py` — POST invitations accepts `suggested_sdlc_role` field per contracts/rest-api.md
- [ ] T030 [P] [US4] Write tests for default role profile update in `backend/tests/unit/test_user_profile_default_role.py`
- [ ] T031 [P] [US5] Write tests for invitation role hint in `backend/tests/integration/test_invitation_role_hint.py`

### Frontend

- [ ] T032 [P] [US4] Extend profile settings page to show default role selector in `frontend/src/app/(workspace)/[workspaceSlug]/settings/profile/page.tsx` — add "Default SDLC Role" section with role grid, save via `PATCH /auth/me` (existing auth endpoint)
- [ ] T033 [P] [US5] Extend invite dialog to show optional role hint dropdown in `frontend/src/features/settings/components/invite-member-dialog.tsx` — add "Suggest SDLC Role" dropdown populated from role templates
- [ ] T034 [US4/US5] Update `RoleSelectorStep` to display default role and workspace hint labels in `frontend/src/features/onboarding/components/role-selector-step.tsx` — show "Your default" and "Suggested by workspace owner" badges per spec US1 scenarios 2-3

**Checkpoint**: US4+US5 complete. Default role pre-selects in onboarding. Owner hints shown to invitee. Verify with quickstart.md Scenario 5.

---

## Phase 6: User Story 6 — Skills Settings Tab (P1)

**Goal**: Users manage role skills from a dedicated Settings tab — view, edit, regenerate, add, remove, reset.
**Verify**: Navigate to Settings → Skills → full CRUD operations work and agent reflects changes.

### Frontend

- [ ] T035 [US6] Add "Skills" nav item to settings layout in `frontend/src/app/(workspace)/[workspaceSlug]/settings/layout.tsx` — add to "Account" section with Wand2 icon, href `/{slug}/settings/skills`
- [ ] T036 [US6] Create skills settings route in `frontend/src/app/(workspace)/[workspaceSlug]/settings/skills/page.tsx`
- [ ] T037 [US6] Create `SkillEditor` component in `frontend/src/components/role-skill/skill-editor.tsx` — markdown editor with word count, live preview, save/cancel actions. Warn at 1800+ words, block at 2000.
- [ ] T038 [US6] Create `SkillsSettingsPage` in `frontend/src/features/settings/pages/skills-settings-page.tsx` — displays role cards with skill content, Edit/Regenerate/Remove/Reset buttons, "Add Role" button (disabled at 3 roles), guest read-only view. Uses TanStack Query for data fetching.
- [ ] T039 [US6] Wire regeneration flow in `SkillsSettingsPage` — "Regenerate with AI" button → modal with experience textarea → call `/regenerate` → show diff preview (current vs new) → confirm to save
- [ ] T040 [US6] Write component tests for `SkillsSettingsPage` in `frontend/src/features/settings/__tests__/skills-settings-page.test.tsx` — test CRUD operations, max roles warning, guest restriction, regeneration flow, word count validation

**Checkpoint**: US6 complete. Full skills management UI in Settings. Verify with quickstart.md Scenario 3.

---

## Phase 7: Polish

- [ ] T041 [P] Run all quickstart.md scenarios (1-8) end-to-end and fix failures
- [ ] T042 [P] Run backend quality gates: `uv run pyright && uv run ruff check && uv run pytest --cov=.` — ensure >80% coverage on new files, fix all type errors and lint issues
- [ ] T043 [P] Run frontend quality gates: `pnpm lint && pnpm type-check && pnpm test` — fix all issues
- [ ] T044 Verify file size limits — all new files under 700 lines, split if needed
- [ ] T045 [P] Verify RLS isolation — run cross-workspace role skill access tests per quickstart.md Scenario 4

**Checkpoint**: Feature complete. All quality gates pass. All quickstart scenarios verified. Ready for PR.

---

## Dependencies

### Phase Order

```
Phase 1 (Setup) → Phase 2 (Foundation) → Phase 3 (US1+2) → Phase 4 (US3) → Phase 5 (US4+5) + Phase 6 (US6) → Phase 7 (Polish)
```

### Story Independence

- US1 (Role Selection) and US2 (Skill Generation) are tightly coupled — implemented together in Phase 3
- US3 (Agent Injection) depends on Phase 3 (needs role skills in DB to materialize)
- US4 (Default Role) and US5 (Owner Hints) are independent of each other — parallelizable in Phase 5
- US6 (Settings Tab) depends on Phase 3 (CRUD endpoints) but can parallelize with Phase 4+5

### Within Each Phase

```
Schemas → Models → Repository → Service → Router → Frontend Components → Tests
```

### Parallel Opportunities

| Phase | Parallel Group | Tasks |
|-------|---------------|-------|
| Phase 3 | Frontend scaffolding | T017, T018 (API client + store) |
| Phase 5 | Backend extensions | T028, T029 (profile + invitation) |
| Phase 5 | Frontend extensions | T032, T033 (profile page + invite dialog) |
| Phase 5 | Tests | T030, T031 |
| Phase 7 | Quality gates | T041, T042, T043, T045 |

---

## Execution Strategy

**Selected Strategy**: B (Incremental) — Requirements are stable (spec finalized with user input). Deploy after each phase for continuous validation. Phase 3 is the critical path delivering core value (role selection + skill generation).

---

## Validation Checklists

### Coverage Completeness

- [x] Every user story from spec.md has a task phase (US1-US6 across Phases 3-6)
- [x] Every entity from data-model.md has a creation task (T003: UserRoleSkill + RoleTemplate, T004: migration)
- [x] Every endpoint from contracts/rest-api.md has an implementation task (T011: 7 new endpoints, T028-T029: 2 extended)
- [x] Every quickstart scenario has a validation task (T041: all 8 scenarios)
- [x] Setup and Polish phases included (Phase 1, Phase 7)

### Task Quality

- [x] Task IDs sequential (T001-T045) with no gaps
- [x] Each task has exact file path
- [x] Each task starts with imperative verb
- [x] One responsibility per task
- [x] `[P]` markers only where tasks are truly independent
- [x] `[USn]` markers on all Phase 3+ tasks

### Dependency Integrity

- [x] No circular dependencies
- [x] Phase order enforced: Setup → Foundation → Stories → Polish
- [x] Within-story order: Schemas → Models → Services → Endpoints → Components
- [x] Cross-story shared entities placed in Foundation phase (T003-T007)
- [x] Each phase has a checkpoint statement

### Execution Readiness

- [x] Any developer can pick up any task and execute without questions
- [x] File paths match plan.md project structure exactly
- [x] Quality gate commands specified in Polish phase (T042, T043)
- [x] Execution strategy selected with rationale (Incremental — stable requirements)

---

## Next Phase

After this task list passes all checklists:

1. **Run consistency analysis** — Verify spec + plan + tasks alignment
2. **Assign and execute** — Each task is a self-contained work unit
3. **Track progress** — Check off tasks, verify checkpoints at phase boundaries
4. **Prepare for implementation** — Follow `references/template-implement.md` for coding steps

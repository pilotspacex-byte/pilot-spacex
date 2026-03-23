# Tasks: Workspace Feature Toggles

**Feature Branch**: `024-workspace-feature-toggles`
**Created**: 2026-03-18
**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

**Total Tasks**: 33
**User Stories**: 6 (3x P1, 3x P2)
**MVP Scope**: Phase 1–3 (US1 + US2 — admin toggles + member visibility)

---

## Phase 1: Setup

No project initialization needed — feature uses existing workspace infrastructure (JSONB column, MobX stores, sidebar component). No migrations required.

---

## Phase 2: Foundational — Backend Schema + API

These tasks are blocking prerequisites for all user stories. They create the backend API that every frontend and AI feature depends on.

- [x] T001 Add `WorkspaceFeatureToggles` and `WorkspaceFeatureTogglesUpdate` Pydantic schemas to `backend/src/pilot_space/api/v1/schemas/workspace.py`. Follow `AIFeatureToggles` pattern. 8 boolean fields with defaults: notes=True, issues=False, projects=False, members=True, docs=False, skills=True, costs=False, approvals=False. `WorkspaceFeatureTogglesUpdate` has all fields as `bool | None = None`.

- [x] T002 Create `backend/src/pilot_space/api/v1/routers/workspace_feature_toggles.py` with GET and PATCH endpoints. Reference: `workspace_ai_settings.py`. GET `/workspaces/{workspace_id}/feature-toggles` — accessible to any workspace member, reads `workspace.settings["feature_toggles"]` and returns `WorkspaceFeatureToggles` (defaults when key absent). PATCH — admin/owner only, merges partial update into `workspace.settings["feature_toggles"]` using `flag_modified(workspace, "settings")`, returns full updated state. Include `_get_feature_toggles(workspace)` helper and reuse `_get_admin_workspace()` pattern for admin check.

- [x] T003 Register the feature toggles router in `backend/src/pilot_space/api/v1/routers/__init__.py` — add import and export. Then register in `backend/src/pilot_space/main.py` — add `app.include_router()` under `/api/v1` prefix, grouped with other workspace routers.

- [x] T004 Add `WorkspaceFeatureToggles` TypeScript interface and `DEFAULT_FEATURE_TOGGLES` constant to `frontend/src/types/workspace.ts`. 8 boolean fields matching backend schema defaults.

- [x] T005 [P] Add `getFeatureToggles(workspaceId)` and `updateFeatureToggles(workspaceId, data)` API functions to `frontend/src/services/api/workspaces.ts`. GET returns `WorkspaceFeatureToggles`, PATCH accepts `Partial<WorkspaceFeatureToggles>` and returns `WorkspaceFeatureToggles`.

---

## Phase 3: US1 — Admin Configures Feature Visibility (P1)

**Goal**: Admin navigates to Settings > Features, toggles features on/off, changes persist and affect sidebar.
**Independent test**: Toggle off "Docs" as admin → sidebar hides "Docs" for all members.

- [x] T006 [US1] Extend `WorkspaceStore` in `frontend/src/stores/WorkspaceStore.ts` with feature toggle state. Add `featureToggles: WorkspaceFeatureToggles | null` observable, `loadFeatureToggles(workspaceId)` action that calls `getFeatureToggles()`, `saveFeatureToggles(data)` action that calls `updateFeatureToggles()` and refreshes local state, and `isFeatureEnabled(key: string): boolean` method that returns `this.featureToggles?.[key] ?? DEFAULT_FEATURE_TOGGLES[key]`. Trigger `loadFeatureToggles` when workspace is set (in existing workspace load flow).

- [x] T007 [US1] Add "Features" nav item to settings sidebar in `frontend/src/app/(workspace)/[workspaceSlug]/settings/layout.tsx`. Insert as first item in the Workspace section (before "General" or "AI Providers"). Use `Sliders` icon from lucide-react. Path: `/{slug}/settings/features`. Only visible to admin/owner roles (check `workspaceStore.isAdmin`).

- [x] T008 [US1] Create `frontend/src/app/(workspace)/[workspaceSlug]/settings/features/page.tsx` — the Features settings page. Reference UI: `frontend/src/features/settings/components/ai-feature-toggles.tsx`. Display 8 toggleable features in two groups: "Main" (Notes, Issues, Projects, Members, Docs) and "AI" (Skills, Costs, Approvals). Each item: icon + name + description + Switch component. On toggle change, call `workspaceStore.saveFeatureToggles({ [key]: newValue })`. Show loading spinner while saving, success toast on save. Redirect non-admin users to settings home.

- [x] T009 [US1] Add `featureKey` property to `NavItem` interface in `frontend/src/components/layout/sidebar.tsx`. Map each nav item: Notes→`notes`, Issues→`issues`, Projects→`projects`, Members→`members`, Docs→`docs`, Skills→`skills`, Costs→`costs`, Approvals→`approvals`. Home and Chat have no `featureKey` (always visible). In the render loop, skip items where `featureKey` is defined and `workspaceStore.isFeatureEnabled(item.featureKey)` returns false. Hide section labels ("Main", "AI") when all items in that section are filtered out.

- [x] T010 [US1] Add feature toggle route protection in `frontend/src/app/(workspace)/[workspaceSlug]/layout.tsx`. Create a pathname-to-featureKey mapping: `notes→notes`, `issues→issues`, `projects→projects`, `members→members`, `docs→docs`, `skills→skills`, `costs→costs`, `approvals→approvals`. In a `useEffect`, check if the current pathname segment maps to a disabled feature. If so, redirect to workspace home (`/${workspaceSlug}`). Skip redirect while `featureToggles` is still loading (null).

---

## Phase 4: US2 — Member Sees Only Enabled Features (P1)

**Goal**: Non-admin members see only enabled features in sidebar and cannot access disabled routes.
**Independent test**: As member, verify disabled features are hidden and direct URLs redirect.

- [x] T011 [US2] Verify that `loadFeatureToggles` in `WorkspaceStore` is called for all users (not just admins) when the workspace loads. The GET endpoint allows any member to read — ensure the store load is triggered on workspace resolution regardless of role. No new code if T006 already loads for all users; otherwise adjust the load trigger.

- [x] T012 [US2] Verify sidebar filtering from T009 works for all roles (member, guest). The `isFeatureEnabled` check should not depend on role — it reads workspace-level toggles. Ensure `adminOnly` filtering (existing) and `featureKey` filtering (new) both apply independently. An `adminOnly` item that is also feature-disabled should be hidden for everyone.

---

## Phase 5: US3 — Non-Admin Cannot Modify Feature Toggles (P2)

**Goal**: Members and guests cannot see or access the Features settings page, and the PATCH endpoint rejects non-admins.
**Independent test**: Log in as member → "Features" not in settings nav → direct URL returns 403 or redirects.

- [x] T013 [US3] Verify the PATCH endpoint in `workspace_feature_toggles.py` (T002) rejects requests from non-admin members with HTTP 403. The `_get_admin_workspace()` helper already handles this — confirm it's wired correctly.

- [x] T014 [US3] Verify the "Features" nav item in settings layout (T007) is hidden for non-admin roles. The visibility check should use `workspaceStore.isAdmin`. Also verify the Features settings page (T008) redirects non-admins (member, guest) to settings home if they navigate directly to `/settings/features`.

---

## Phase 6: US4 — New Workspace Has Default Feature Set (P2)

**Goal**: New workspaces and existing workspaces without toggle config show defaults (Notes, Members, Skill on; others off).
**Independent test**: Create new workspace → sidebar shows only Notes, Members, Skill.

- [x] T015 [US4] Verify that when `workspace.settings` has no `feature_toggles` key, the GET endpoint returns `WorkspaceFeatureToggles()` defaults (notes=True, members=True, skills=True; others=False). This is handled by schema defaults in T001 — no additional code needed if the helper in T002 instantiates `WorkspaceFeatureToggles()` when the key is absent.

- [x] T016 [US4] Verify the frontend `isFeatureEnabled` fallback in `WorkspaceStore` (T006) uses `DEFAULT_FEATURE_TOGGLES` when `featureToggles` is null or a key is missing. This ensures the sidebar shows correct defaults before the API responds.

---

## Phase 7: US5 — Feature Toggle Persists Across Sessions (P2)

**Goal**: Toggled features remain in their state after logout/login.
**Independent test**: Toggle off Issues → logout → login → Issues still hidden.

- [x] T017 [US5] No additional implementation needed — persistence is guaranteed by storing toggles in `workspace.settings` JSONB (server-side). The GET endpoint always reads from the database. Verify by confirming the PATCH endpoint commits to the database (`await session.commit()` in T002) and the GET endpoint reads from the database (not from any in-memory cache).

---

## Phase 8: US6 — AI Skills and Tools Respect Feature Toggles (P1)

**Goal**: When a feature is toggled off, related AI skills and MCP tools are unavailable to the agent.
**Independent test**: Disable "Issues" → AI chat → request issue extraction → agent refuses.

- [x] T018 [US6] Add `feature_module` field to YAML frontmatter of each applicable SKILL.md file. Use the mapping from data-model.md:
  - `summarize/SKILL.md` → `feature_module: notes`
  - `create-note-from-chat/SKILL.md` → `feature_module: notes`
  - `generate-digest/SKILL.md` → `feature_module: notes`
  - `improve-writing/SKILL.md` → `feature_module: notes`
  - `extract-issues/SKILL.md` → `feature_module: issues`
  - `enhance-issue/SKILL.md` → `feature_module: issues`
  - `find-duplicates/SKILL.md` → `feature_module: issues`
  - `recommend-assignee/SKILL.md` → `feature_module: [issues, members]`
  - `decompose-tasks/SKILL.md` → `feature_module: projects`
  - `generate-pm-blocks/SKILL.md` → `feature_module: projects`
  - `speckit-pm-guide/SKILL.md` → `feature_module: projects`
  - `sprint-planning/SKILL.md` → `feature_module: projects`
  - `generate-diagram/SKILL.md` → `feature_module: docs`
  - `adr-lite/SKILL.md` → `feature_module: docs`
  - `generate-code/SKILL.md` → `feature_module: docs`
  Skills without a `feature_module` (e.g., review-code, scan-security, ai-context) are always available.

- [x] T019 [US6] Update `backend/src/pilot_space/ai/skills/skill_discovery.py` to parse the `feature_module` field from YAML frontmatter. Add `feature_module: list[str] | None` to `SkillInfo` dataclass (normalize single string to list). Add `filter_skills_by_features(skills: list[SkillInfo], active_features: set[str]) -> list[SkillInfo]`: for each skill, if `feature_module is None` → keep; if ANY module in `feature_module` is in `active_features` → keep; otherwise remove.

- [x] T020 [US6] Add `active_features`-aware MCP server grouping to `build_mcp_servers()` in `backend/src/pilot_space/ai/agents/pilotspace_stream_utils.py`. Signature: `active_features: set[str] | None = None`. Unconditional block: always add `comment_server` and `interaction_server`. Feature-conditional blocks: `if active_features is None or "notes" in active_features` → add note_server, note_query_server, note_content_server; same for `"issues"` → issue_server, issue_relation_server; `"projects"` → project_server. No `_all_servers` list.

- [x] T021 [US6] (Superseded by T020 — `registry.py list_tools()` filtering was not implemented; MCP filtering is handled entirely in `build_mcp_servers()` in `pilotspace_stream_utils.py`.)

- [x] T022 [US6] Update `_build_stream_config()` in `backend/src/pilot_space/ai/agents/pilotspace_agent.py`: load workspace feature toggles via `WorkspaceRepository.get_by_id()`. Compute `_active_features: set[str] = {k for k, v in (workspace.settings or {}).get("feature_toggles", {}).items() if v}`. Pass `active_features=_active_features` to `build_mcp_servers()`. Pass `active_features=list(_active_features)` to `PromptLayerConfig`.

- [x] T023 [US6] (Superseded by T020 — `build_mcp_servers()` was moved/implemented in `pilotspace_stream_utils.py`, not `pilotspace_agent_helpers.py`.)

- [x] T024 [US6] Add `active_features: list[str]` field to `PromptLayerConfig` in `backend/src/pilot_space/ai/prompt/models.py`. Add `_build_feature_context_section(config)` to `backend/src/pilot_space/ai/prompt/prompt_assembler.py` (layer 4.6): computes `disabled = ALL_FEATURES − set(config.active_features)`, returns a "Disabled Workspace Features" section when non-empty, instructs agent to decline and direct user to Settings > Features. Returns `None` when all features active.

---

## Phase 9: Polish & Cross-Cutting

- [x] T025 Verify backward compatibility: test that an existing workspace with NO `feature_toggles` key in `workspace.settings` returns correct defaults from GET endpoint and renders correct sidebar (Notes, Members, Skill visible). No data migration should be needed.

- [x] T026 Verify that disabling a feature does NOT delete any underlying data. Toggle off "Issues" → confirm issues still exist in the database → toggle on "Issues" → confirm all issues are accessible again.

- [x] T027 Verify section label hiding in sidebar: when all "Main" items (Notes, Issues, Projects, Members, Docs) are disabled, the "Main" section label should be hidden. Same for "AI" section when Skills, Costs, and Approvals are all disabled. Edge case: Chat is always visible in AI section, so the "AI" label should remain if Chat is present even when Skills/Costs/Approvals are all off.

- [x] T028 Run quality gates to verify no regressions: `make quality-gates-backend` (pyright + ruff + pytest) and `make quality-gates-frontend` (eslint + tsc + vitest).

---

## Phase 10: Refactor — active_features API + grouped MCP structure

**Goal**: Clarify the feature-toggle contract by using `active_features` (what's ON) instead of `disabled_features` / `feature_toggles` (what's OFF), and restructure `build_mcp_servers()` so always-on servers are declared unconditionally while feature-gated servers are appended in explicit groups. No behavior change — only naming, structure, and readability.

- [ ] T029 Refactor `PromptLayerConfig` in `backend/src/pilot_space/ai/prompt/models.py`: rename `disabled_features: list[str]` → `active_features: list[str]`. Update the docstring to describe it as the list of enabled feature module names (e.g. `["notes", "members", "skills"]`). All features are drawn from the 8-key set: `notes`, `issues`, `projects`, `members`, `docs`, `skills`, `costs`, `approvals`.

- [ ] T030 [P] Refactor `_build_disabled_features_section()` in `backend/src/pilot_space/ai/prompt/prompt_assembler.py`: rename to `_build_feature_context_section(config: PromptLayerConfig) -> str | None`. Change the logic: compute `disabled = ALL_FEATURES - set(config.active_features)` where `ALL_FEATURES = frozenset({"notes","issues","projects","members","docs","skills","costs","approvals"})`. Return `None` when `disabled` is empty (all features active). When non-empty, format as before. Update the caller in `assemble_system_prompt()`: rename `disabled_section` variable and `layers_loaded` key from `"disabled_features"` → `"feature_context"`.

- [ ] T031 [P] Refactor `build_mcp_servers()` in `backend/src/pilot_space/ai/agents/pilotspace_stream_utils.py`: change signature from `feature_toggles: dict[str, bool] | None = None` → `active_features: set[str] | None = None`. Restructure the body so `servers: dict[str, McpServerConfig]` is populated in two stages: (1) unconditional block — always add `COMMENT_SERVER_NAME` and `INTERACTION_SERVER_NAME` directly; (2) feature-conditional blocks — one `if` block per feature, e.g. `if active_features is None or "notes" in active_features: servers[NOTE_SERVER_NAME] = ...; servers[NOTE_QUERY_SERVER_NAME] = ...; servers[NOTE_CONTENT_SERVER_NAME] = ...`. Same pattern for `"issues"` (ISSUE_SERVER, ISSUE_REL_SERVER) and `"projects"` (PROJECT_SERVER). Remove the `_all_servers` list entirely. When `active_features is None`, all servers are included (backward-compatible default).

- [ ] T032 Update `_build_stream_config()` in `backend/src/pilot_space/ai/agents/pilotspace_agent.py`: replace `_feature_toggles: dict[str, bool]` and `_disabled_features: list[str]` with `_active_features: set[str]`. Compute it as `set(k for k, v in (_workspace_obj.settings or {}).get("feature_toggles", {}).items() if v)` — keys whose value is `True`. Pass `active_features=_active_features` to `build_mcp_servers()`. Pass `active_features=list(_active_features)` to `PromptLayerConfig`.

- [ ] T033 Run `uv run pyright` and `uv run ruff check` in `backend/` to verify no type errors or lint issues after the rename. Fix any issues found.

---

## Dependencies

```
T001 ──→ T002 ──→ T003 (backend API chain)
T004 ──→ T005 (frontend types → API calls)
T003 + T005 ──→ T006 (store needs API)
T006 ──→ T007, T008, T009, T010 (settings UI + sidebar + route guard)
T006 ──→ T011, T012 (member visibility verification)
T007 + T008 ──→ T013, T014 (access control verification)
T006 ──→ T015, T016 (default verification)
T002 ──→ T017 (persistence verification)
T001 ──→ T018 → T019 (skill metadata + filtering)
T001 ──→ T020 → T021 (MCP metadata + filtering)
T019 + T021 ──→ T022 → T023, T024 (agent integration)
All ──→ T025, T026, T027, T028 (polish)
T028 ──→ T029 → T030, T031 ∥ T032 → T033 (active_features refactor)
```

## Parallel Execution Opportunities

| Parallel Group | Tasks | Reason |
|---------------|-------|--------|
| Backend + Frontend types | T001–T003 ∥ T004–T005 | Different codebases, no deps |
| Settings UI + Sidebar | T007 + T008 ∥ T009 + T010 | Different files, both depend on T006 |
| Skill metadata + MCP metadata | T018–T019 ∥ T020–T021 | Independent subsystems |
| All US verifications | T011–T012 ∥ T013–T014 ∥ T015–T016 | Read-only verification tasks |
| Phase 10 rename | T030 ∥ T031 | Different files (prompt_assembler vs stream_utils) |

## Implementation Strategy

**MVP (Phase 1–3)**: T001–T010 delivers US1 (admin configures) + US2 (member sees). This gives the core toggle functionality with backend API, settings UI, sidebar filtering, and route protection. ~16 files touched.

**Full feature (Phase 1–9)**: All 28 tasks. Adds access control verification (US3), default verification (US4), persistence verification (US5), AI integration (US6), and polish.

**Refactor (Phase 10)**: T029–T033 renames to `active_features` API and restructures `build_mcp_servers()` for clarity. Pure rename/restructure — no behavior change.

**Recommended order**: Start with T001 (backend schema) and T004 (frontend types) in parallel, then chain through the dependency graph.

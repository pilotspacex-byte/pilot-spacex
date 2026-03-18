# Tasks: Workspace Feature Toggles

**Feature Branch**: `024-workspace-feature-toggles`
**Created**: 2026-03-18
**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

**Total Tasks**: 28
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

- [ ] T018 [US6] Add `feature_module` field to YAML frontmatter of each applicable SKILL.md file. Use the mapping from data-model.md:
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

- [ ] T019 [US6] Update `backend/src/pilot_space/ai/skills/skill_discovery.py` to parse the `feature_module` field from YAML frontmatter. Add `feature_module: str | list[str] | None` to `SkillInfo` dataclass. In `_parse_skill_file()`, read `frontmatter.get("feature_module")` and store as a list (normalize single string to `[string]`). Add a `filter_skills_by_features(skills: list[SkillInfo], feature_toggles: dict[str, bool]) -> list[SkillInfo]` function: for each skill, if `feature_module` is None → keep; if all modules in `feature_module` are disabled → remove; otherwise keep.

- [ ] T020 [US6] Add `feature_module` metadata to MCP server registrations. In `backend/src/pilot_space/ai/mcp/registry.py`, add a `feature_module: str | None` field to the tool/server registration metadata. Update each MCP server registration (in `backend/src/pilot_space/ai/agents/pilotspace_agent_helpers.py` or wherever `build_mcp_servers()` constructs servers) to tag: `note_server→notes`, `note_content_server→notes`, `note_query_server→notes`, `ownership_server→notes`, `issue_server→issues`, `issue_relation_server→issues`, `project_server→projects`. Servers without a `feature_module` (comment_server, github_server, interaction_server) are always included.

- [ ] T021 [US6] Update `list_tools()` in `backend/src/pilot_space/ai/mcp/registry.py` to accept an optional `feature_toggles: dict[str, bool] | None` parameter. When provided, filter out tools whose server's `feature_module` is disabled in the toggles dict. When `feature_toggles` is None, return all tools (backward compatible).

- [ ] T022 [US6] Update `backend/src/pilot_space/ai/agents/pilotspace_agent.py` to load workspace feature toggles at agent session start. In the method that builds the agent context (near `build_mcp_servers()`), read `workspace.settings.get("feature_toggles", {})` from the database. Pass the toggles to: (1) `filter_skills_by_features()` to filter the skill list before building the system prompt, and (2) `list_tools()` / `build_mcp_servers()` to filter MCP tools.

- [ ] T023 [US6] Update `backend/src/pilot_space/ai/agents/pilotspace_agent_helpers.py` — modify `build_mcp_servers()` to accept `feature_toggles: dict[str, bool] | None` parameter. When building the server list, skip servers whose `feature_module` is in the toggles dict and mapped to `False`.

- [ ] T024 [US6] Add a system prompt instruction in the agent's system message (in `pilotspace_agent.py` or the prompt template) that informs the agent about disabled features. Something like: "The following workspace features are currently disabled: {disabled_list}. If a user requests functionality related to a disabled feature, politely inform them that the feature is not enabled for this workspace and suggest they ask a workspace admin to enable it in Settings > Features."

---

## Phase 9: Polish & Cross-Cutting

- [ ] T025 Verify backward compatibility: test that an existing workspace with NO `feature_toggles` key in `workspace.settings` returns correct defaults from GET endpoint and renders correct sidebar (Notes, Members, Skill visible). No data migration should be needed.

- [ ] T026 Verify that disabling a feature does NOT delete any underlying data. Toggle off "Issues" → confirm issues still exist in the database → toggle on "Issues" → confirm all issues are accessible again.

- [ ] T027 Verify section label hiding in sidebar: when all "Main" items (Notes, Issues, Projects, Members, Docs) are disabled, the "Main" section label should be hidden. Same for "AI" section when Skills, Costs, and Approvals are all disabled. Edge case: Chat is always visible in AI section, so the "AI" label should remain if Chat is present even when Skills/Costs/Approvals are all off.

- [ ] T028 Run quality gates to verify no regressions: `make quality-gates-backend` (pyright + ruff + pytest) and `make quality-gates-frontend` (eslint + tsc + vitest).

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
```

## Parallel Execution Opportunities

| Parallel Group | Tasks | Reason |
|---------------|-------|--------|
| Backend + Frontend types | T001–T003 ∥ T004–T005 | Different codebases, no deps |
| Settings UI + Sidebar | T007 + T008 ∥ T009 + T010 | Different files, both depend on T006 |
| Skill metadata + MCP metadata | T018–T019 ∥ T020–T021 | Independent subsystems |
| All US verifications | T011–T012 ∥ T013–T014 ∥ T015–T016 | Read-only verification tasks |

## Implementation Strategy

**MVP (Phase 1–3)**: T001–T010 delivers US1 (admin configures) + US2 (member sees). This gives the core toggle functionality with backend API, settings UI, sidebar filtering, and route protection. ~16 files touched.

**Full feature (Phase 1–9)**: All 28 tasks. Adds access control verification (US3), default verification (US4), persistence verification (US5), AI integration (US6), and polish.

**Recommended order**: Start with T001 (backend schema) and T004 (frontend types) in parallel, then chain through the dependency graph.

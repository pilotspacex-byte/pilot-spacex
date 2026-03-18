# Implementation Plan: Workspace Feature Toggles

**Feature Branch**: `024-workspace-feature-toggles`
**Created**: 2026-03-18
**Spec**: [spec.md](./spec.md)
**Research**: [research.md](./research.md)
**Data Model**: [data-model.md](./data-model.md)
**API Contracts**: [contracts/feature-toggles-api.md](./contracts/feature-toggles-api.md)

---

## Technical Context

| Aspect | Detail |
|--------|--------|
| **Storage** | `workspace.settings` JSONB → `feature_toggles` key (no migration) |
| **Backend pattern** | Mirrors `workspace_ai_settings.py` router + `AIFeatureToggles` schema |
| **Frontend state** | Extends `WorkspaceStore` with `featureToggles` observable |
| **Sidebar** | Adds `featureKey` to `NavItem`, filters in render loop |
| **Route guard** | Client-side redirect in workspace layout |
| **AI integration** | `feature_module` metadata on skills + MCP servers, filtered at session init |

---

## Implementation Phases

### Phase 1: Backend — Schema + API (no dependencies)

**Files to create/modify:**

1. **`backend/src/pilot_space/api/v1/schemas/workspace.py`** — Add schemas
   - Add `WorkspaceFeatureToggles(BaseSchema)` with 8 bool fields (defaults per spec)
   - Add `WorkspaceFeatureTogglesUpdate(BaseSchema)` for partial updates

2. **`backend/src/pilot_space/api/v1/routers/workspace_feature_toggles.py`** — New router
   - `GET /workspaces/{workspace_id}/feature-toggles` — any member can read
   - `PATCH /workspaces/{workspace_id}/feature-toggles` — admin/owner only
   - Reuse `_get_admin_workspace()` pattern from `workspace_ai_settings.py`
   - Helper: `_get_feature_toggles(workspace) -> WorkspaceFeatureToggles`
   - PATCH: merge into `workspace.settings["feature_toggles"]`, `flag_modified`, commit

3. **`backend/src/pilot_space/api/v1/routers/__init__.py`** — Register router
   - Add `feature_toggles_router` to workspace routes

4. **Tests**: `backend/tests/api/v1/test_workspace_feature_toggles.py`
   - Test GET returns defaults when no config exists
   - Test PATCH updates individual toggles
   - Test PATCH rejects non-admin
   - Test partial update doesn't overwrite other toggles

---

### Phase 2: Frontend — Store + Settings UI (depends on Phase 1)

**Files to create/modify:**

5. **`frontend/src/lib/api/workspace.ts`** (or equivalent API module) — Add API calls
   - `getFeatureToggles(workspaceId): Promise<WorkspaceFeatureToggles>`
   - `updateFeatureToggles(workspaceId, data): Promise<WorkspaceFeatureToggles>`

6. **`frontend/src/stores/WorkspaceStore.ts`** — Extend with feature toggles
   - Add `featureToggles: WorkspaceFeatureToggles | null` observable
   - Add `loadFeatureToggles(workspaceId)` action
   - Add `updateFeatureToggles(data)` action
   - Add `isFeatureEnabled(key: string): boolean` computed helper
   - Load feature toggles when workspace is set (alongside member loading)

7. **`frontend/src/types/workspace.ts`** (or equivalent) — Add TypeScript types
   - `WorkspaceFeatureToggles` interface
   - `DEFAULT_FEATURE_TOGGLES` constant

8. **`frontend/src/app/(workspace)/[workspaceSlug]/settings/features/page.tsx`** — New settings page
   - List of feature toggles with switches (grouped: Main, AI)
   - Each toggle: icon + name + description + Switch component
   - Admin-only access (redirect non-admins)
   - Loading and saving states
   - Success toast on save

9. **`frontend/src/app/(workspace)/[workspaceSlug]/settings/layout.tsx`** — Add nav item
   - Add "Features" to `settingsNavSections` Workspace section (first position)
   - Icon: `ToggleLeft` or `Sliders` from lucide-react
   - Visible to admin/owner only

---

### Phase 3: Frontend — Sidebar + Route Protection (depends on Phase 2)

**Files to modify:**

10. **`frontend/src/components/layout/sidebar.tsx`** — Conditional rendering
    - Add `featureKey?: string` to `NavItem` interface
    - Map each nav item to its feature key (Home and Chat have no featureKey → always shown)
    - In render loop: skip items where `featureKey` is set and `workspaceStore.isFeatureEnabled(featureKey)` returns false
    - Hide section labels when all items in section are filtered out

11. **`frontend/src/app/(workspace)/[workspaceSlug]/layout.tsx`** — Route protection
    - Add a `useFeatureGuard()` hook or inline effect
    - Map pathname segments to feature keys
    - If current route's feature is disabled, redirect to workspace home
    - Graceful redirect (no flash, no error)

---

### Phase 4: AI Integration — Skill/Tool Filtering (depends on Phase 1)

**Files to modify:**

12. **Skill YAML frontmatter** — Add `feature_module` to each skill's `SKILL.md`
    - `backend/src/pilot_space/ai/templates/skills/*/SKILL.md`
    - Add `feature_module: notes` (or `issues`, `projects`, `docs`)
    - Multi-module: `feature_module: [issues, members]`

13. **`backend/src/pilot_space/ai/skills/skill_discovery.py`** — Filter by feature toggles
    - Add `feature_module` parsing from frontmatter
    - Add `filter_skills_by_features(skills, feature_toggles)` function
    - Multi-module: skill is available if ANY listed module is enabled

14. **`backend/src/pilot_space/ai/mcp/registry.py`** — Filter tools by feature toggles
    - Add `feature_module` metadata to MCP server registration
    - Update `list_tools()` to accept `feature_toggles` parameter
    - Filter out tools whose server's `feature_module` is disabled

15. **`backend/src/pilot_space/ai/agents/pilotspace_agent.py`** — Load toggles at session start
    - In `_run_agent_turn()` or session init, load workspace feature toggles
    - Pass to `build_mcp_servers()` and skill filtering
    - Add system prompt instruction: when user requests a disabled feature, explain it's not enabled

16. **`backend/src/pilot_space/ai/agents/pilotspace_agent_helpers.py`** — Update helpers
    - `build_mcp_servers()` accepts feature toggles, excludes disabled servers

---

### Phase 5: Testing + Polish

17. **Backend tests**: Feature toggle API (Phase 1 tests + integration tests)
    - Skill filtering with various toggle combinations
    - MCP tool filtering
    - Multi-module skill edge cases

18. **Frontend tests**: Settings page, sidebar filtering, route protection
    - Vitest: `WorkspaceStore.isFeatureEnabled` logic
    - Vitest: Sidebar renders only enabled items
    - E2E: Toggle off feature → sidebar updates → route redirects

---

## File Change Summary

| # | File | Action | Phase |
|---|------|--------|-------|
| 1 | `backend/.../schemas/workspace.py` | Modify | 1 |
| 2 | `backend/.../routers/workspace_feature_toggles.py` | Create | 1 |
| 3 | `backend/.../routers/__init__.py` | Modify | 1 |
| 4 | `backend/tests/.../test_workspace_feature_toggles.py` | Create | 1 |
| 5 | `frontend/src/lib/api/workspace.ts` | Modify | 2 |
| 6 | `frontend/src/stores/WorkspaceStore.ts` | Modify | 2 |
| 7 | `frontend/src/types/workspace.ts` | Modify | 2 |
| 8 | `frontend/.../settings/features/page.tsx` | Create | 2 |
| 9 | `frontend/.../settings/layout.tsx` | Modify | 2 |
| 10 | `frontend/src/components/layout/sidebar.tsx` | Modify | 3 |
| 11 | `frontend/.../[workspaceSlug]/layout.tsx` | Modify | 3 |
| 12 | `backend/.../skills/*/SKILL.md` (15+ files) | Modify | 4 |
| 13 | `backend/.../skills/skill_discovery.py` | Modify | 4 |
| 14 | `backend/.../mcp/registry.py` | Modify | 4 |
| 15 | `backend/.../agents/pilotspace_agent.py` | Modify | 4 |
| 16 | `backend/.../agents/pilotspace_agent_helpers.py` | Modify | 4 |
| 17 | `backend/tests/...` (multiple test files) | Create | 5 |
| 18 | `frontend/src/...` (test files) | Create | 5 |

---

## Risk Assessment

| Risk | Mitigation |
|------|-----------|
| Existing workspaces break (features hidden unexpectedly) | Defaults match current spec (Notes, Members, Skill on). Explicit admin action required to change. |
| JSONB merge race condition | Use `flag_modified` + single-field PATCH pattern (same as AI settings). |
| Sidebar flickers on load | Load feature toggles alongside workspace data; show skeleton until loaded. |
| AI agent ignores toggles | System prompt reinforcement + tool/skill filtering at registry level (defense in depth). |
| Route guard bypass via deep links | Client-side guard in workspace layout catches all nested routes. |

---

## Estimated Scope

- **Backend**: ~200 lines new code (router + schema), ~50 lines modifications
- **Frontend**: ~300 lines new code (settings page + types), ~100 lines modifications (sidebar + store + layout)
- **AI integration**: ~100 lines modifications across 5+ files, ~15 SKILL.md metadata updates
- **Tests**: ~300 lines

# Quickstart: Workspace Feature Toggles

**Feature Branch**: `024-workspace-feature-toggles`

---

## What This Feature Does

Allows workspace admins to enable/disable sidebar modules (Notes, Issues, Projects, Members, Docs, Skills, Costs, Approvals) for all workspace members. Disabled features are hidden from the sidebar, blocked at route level, and their related AI skills/MCP tools are suppressed.

## Key Files to Start With

### Backend (start here)
1. `backend/src/pilot_space/api/v1/schemas/workspace.py` — Add `WorkspaceFeatureToggles` schema
2. `backend/src/pilot_space/api/v1/routers/workspace_feature_toggles.py` — New GET/PATCH endpoints
3. Reference: `backend/src/pilot_space/api/v1/routers/workspace_ai_settings.py` — Follow this exact pattern

### Frontend
4. `frontend/src/stores/WorkspaceStore.ts` — Add `featureToggles` observable + actions
5. `frontend/src/app/(workspace)/[workspaceSlug]/settings/features/page.tsx` — New settings page
6. `frontend/src/components/layout/sidebar.tsx` — Add `featureKey` filtering
7. Reference: `frontend/src/features/settings/components/ai-feature-toggles.tsx` — Follow this UI pattern

### AI Integration
8. `backend/src/pilot_space/ai/skills/skill_discovery.py` — Add `feature_module` filtering
9. `backend/src/pilot_space/ai/mcp/registry.py` — Filter tools by workspace feature toggles
10. `backend/src/pilot_space/ai/agents/pilotspace_agent.py` — Load toggles at session start

## Implementation Order

```
Phase 1: Backend API (schema + router)
    ↓
Phase 2: Frontend store + settings page
    ↓
Phase 3: Sidebar filtering + route protection
    ↓
Phase 4: AI skill/tool filtering
    ↓
Phase 5: Tests
```

## Critical Patterns to Follow

1. **JSONB merge**: Always use `flag_modified(workspace, "settings")` after updating `workspace.settings`
2. **Admin check**: Reuse `_get_admin_workspace()` helper from `workspace_ai_settings.py`
3. **Defaults in schema**: `WorkspaceFeatureToggles()` with no args returns all defaults — no migration needed
4. **Partial update**: PATCH merges provided fields; omitted fields keep current values
5. **Multi-module skills**: `recommend-assignee` maps to `[issues, members]` — disabled only when ALL are off

## Quick Verification

```bash
# Backend: Run tests
cd backend && uv run pytest tests/api/v1/test_workspace_feature_toggles.py -v

# Frontend: Type check
cd frontend && pnpm type-check

# Frontend: Tests
cd frontend && pnpm test
```

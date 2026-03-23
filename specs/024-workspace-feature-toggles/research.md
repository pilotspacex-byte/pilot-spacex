# Research: Workspace Feature Toggles

**Feature Branch**: `024-workspace-feature-toggles`
**Created**: 2026-03-18

---

## Decision 1: Storage Strategy

**Decision**: Use existing `workspace.settings` JSONB column with a `feature_toggles` key.

**Rationale**: The codebase already uses `workspace.settings` JSONB for AI feature toggles (`ai_features` key). Reusing this pattern:
- Requires no database migration
- Follows established JSONB merge pattern (`flag_modified` for SQLAlchemy tracking)
- Consistent with how `AIFeatureToggles` are stored and retrieved
- Supports atomic partial updates

**Alternatives considered**:
- Separate `workspace_feature_toggles` table: Rejected — adds migration complexity, RLS policies, and a new model/repository for a flat key-value structure that JSONB handles well.
- Per-feature columns on workspace table: Rejected — schema migration for each new toggle, inflexible.

---

## Decision 2: Default Values Strategy

**Decision**: Defaults defined in the Pydantic schema (`WorkspaceFeatureToggles`), not in the database.

**Rationale**: When `workspace.settings["feature_toggles"]` is absent or partial, the schema fills defaults. This means:
- Existing workspaces get defaults without migration
- New toggles added in future automatically default without data backfill
- Single source of truth for defaults in `WorkspaceFeatureToggles` schema

**Defaults**: Notes=True, Members=True, Skills=True; all others=False.

---

## Decision 3: API Endpoint Design

**Decision**: Dedicated router `workspace_feature_toggles.py` with GET and PATCH endpoints, separate from AI settings.

**Rationale**: Feature toggles affect the entire workspace UX (sidebar, routes, AI), not just AI settings. Keeping them separate:
- Avoids overloading the AI settings endpoint
- Allows different permission models (all members can read; only admin/owner can write)
- Cleaner API surface for frontend consumption

**Alternatives considered**:
- Extend existing AI settings endpoint: Rejected — conceptually different; feature toggles are workspace-level UX configuration, not AI-specific.
- Include in workspace CRUD endpoint: Rejected — workspace CRUD is heavy; toggles need a lightweight, focused endpoint.

---

## Decision 4: Frontend State Management

**Decision**: Add `featureToggles` to the existing `WorkspaceStore` (not a new store).

**Rationale**: Feature toggles are core workspace state consumed by the sidebar, route guards, and settings page. The `WorkspaceStore` already:
- Tracks workspace membership and roles
- Is available globally via `useWorkspaceStore()`
- Is the natural location for workspace-level configuration
- Avoids circular dependency issues (sidebar already uses `WorkspaceStore`)

**Alternatives considered**:
- New `FeatureTogglesStore`: Rejected — adds an extra store for a simple flat object; `WorkspaceStore` is already the source of truth for workspace context.
- Extend `AISettingsStore`: Rejected — feature toggles are not AI-specific; would create confusing ownership.

---

## Decision 5: Sidebar Filtering Strategy

**Decision**: Filter `navigationSections` in the sidebar component by reading feature toggles from `WorkspaceStore`.

**Rationale**: The sidebar already uses `useMemo` to derive navigation items. Adding a toggle filter here:
- Keeps the change localized to `sidebar.tsx`
- Uses existing MobX reactivity — toggles change, sidebar re-renders
- Matches existing `adminOnly` filtering pattern

**Implementation**: Add a `featureKey` property to `NavItem` interface. In the render loop, skip items where `featureKey` maps to a disabled toggle.

---

## Decision 6: Route Protection Strategy

**Decision**: Client-side redirect in a shared layout component that checks feature toggles on navigation.

**Rationale**: The app already uses client-side route guards (e.g., guest redirect in settings layout). A feature toggle guard in the workspace layout:
- Catches direct URL navigation
- Redirects to workspace home gracefully
- No backend route-level enforcement needed (data APIs remain accessible for admin/integration use)

**Alternatives considered**:
- Backend middleware blocking API calls: Rejected — data should remain accessible via API for integrations; only the UI should hide features.
- Next.js middleware: Possible but requires server-side toggle fetching; client-side is simpler and consistent with existing patterns.

---

## Decision 7: AI Skill/Tool Filtering Strategy

**Decision**: Filter skills and MCP tools at agent session initialization time, using workspace feature toggles.

**Rationale**:
- `build_mcp_servers()` in `pilotspace_agent.py` already builds tool context per-session with `workspace_id`
- `discover_skills()` returns a filterable list
- The MCP registry's `list_tools()` already has a `workspace_id` parameter reserved for future filtering — this is that future use case
- Add a `feature_key` metadata field to each skill's YAML frontmatter and each MCP server registration

**Implementation**:
1. Add `feature_module` field to skill YAML frontmatter (e.g., `feature_module: issues`)
2. Add `feature_module` to MCP server registration metadata
3. At agent session start, load workspace feature toggles, filter out skills/tools whose `feature_module` is disabled
4. For multi-module skills (e.g., `recommend-assignee` → issues+members), skill is available if ANY related module is enabled

---

## Decision 8: Settings UI Placement

**Decision**: Add "Features" as the first item in the Workspace section of settings navigation, accessible only to admin/owner.

**Rationale**: Feature toggles are a high-level workspace configuration that admins should find easily. Placing it first in the Workspace section (before AI Providers) makes it discoverable.

**UI Design**: Follows the existing `AIFeatureToggles` component pattern — a list of labeled switches with icons, descriptions, and grouped by section (Main features, AI features).

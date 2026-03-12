---
phase: 14-remote-mcp-server-management
plan: 04
subsystem: frontend
tags: [mcp, settings, mobx, react, nextjs, api-client]
dependency_graph:
  requires: [14-03]
  provides: [frontend-mcp-ui, mcp-servers-api-client, MCPServersStore]
  affects: [ai-settings, workspace-settings-nav]
tech_stack:
  added:
    - MCPServersStore (MobX observable store, AIStore.mcpServers)
    - mcpServersApi (typed API client, axios)
    - MCPServerCard (shadcn Card + AlertDialog + Badge)
    - MCPServerForm (collapsible form, bearer/OAuth2 conditional fields)
    - MCPServersSettingsPage (observer component)
  patterns:
    - Mirror AISettingsStore pattern for MobX store
    - Plain component (no observer) for cards and forms, observer only at page level
    - Store mounted in AIStore singleton, accessed via useStore()
key_files:
  created:
    - frontend/src/services/api/mcp-servers.ts
    - frontend/src/stores/ai/MCPServersStore.ts
    - frontend/src/features/settings/components/mcp-server-card.tsx
    - frontend/src/features/settings/components/mcp-server-form.tsx
    - frontend/src/features/settings/pages/mcp-servers-settings-page.tsx
    - frontend/src/app/(workspace)/[workspaceSlug]/settings/mcp-servers/page.tsx
    - frontend/src/stores/ai/__tests__/MCPServersStore.test.ts
  modified:
    - frontend/src/stores/ai/AIStore.ts (added mcpServers field)
    - frontend/src/stores/ai/index.ts (exported MCPServersStore and types)
    - frontend/src/app/(workspace)/[workspaceSlug]/settings/layout.tsx (added MCP Servers nav item)
decisions:
  - MCPServersStore added to AIStore as mcpServers field — consistent with settings, cost, approval store pattern; avoids useState local instance antipattern
  - MCPServerForm uses collapsible pattern (expand/collapse) — avoids permanently visible large form in settings page, matches CustomProviderForm UX intent
  - onRegister callback pattern in MCPServerForm — store interaction stays in page observer, form remains pure/testable
  - StatusBadge uses connected=green/failed=red/unknown=gray — matches ProviderStatusCard color semantics
metrics:
  duration_minutes: 40
  completed_date: "2026-03-10"
  tasks_completed: 3
  files_created: 7
  files_modified: 4
---

# Phase 14 Plan 04: MCP Server Frontend UI Summary

Complete frontend surface for remote MCP server management: typed API client, MobX store, settings page with collapsible registration form (bearer/OAuth2), server cards with status badges and delete confirmation, and settings nav entry.

## What Was Built

### Task 1: API Client + MCPServersStore + Tests (TDD)

**RED**: Wrote 6 failing tests in `MCPServersStore.test.ts` covering all store methods with `vi.mock('@/services/api/mcp-servers')`.

**GREEN**: Implemented both files to pass all tests.

- `frontend/src/services/api/mcp-servers.ts`: 5-method typed API client using `apiClient` from `@/services/api/client`. Methods: `list`, `register`, `checkStatus`, `remove`, `getOAuthUrl`.
- `frontend/src/stores/ai/MCPServersStore.ts`: MobX store with `makeAutoObservable`, `runInAction` for all async state transitions. Exports: `MCPServer`, `MCPServerStatus`, `MCPServerListResponse`, `MCPServerRegisterRequest` interfaces.

Store added to `AIStore.ts` as `mcpServers: MCPServersStore` (singleton pattern matching all other AI stores).

### Task 2: Settings Page Components + Route

- `mcp-server-card.tsx`: Plain component (not observer). Shows server name, URL, auth type badge (Bearer/OAuth2), status badge (connected=green/failed=red/unknown=gray), refresh status icon button, delete with `AlertDialog` confirmation.
- `mcp-server-form.tsx`: Collapsible plain component. Displays bearer token field OR OAuth2 config section (client_id, auth_url, token_url, scopes) based on radio selection. Submit calls `onRegister` callback then `onSuccess` to reload list.
- `mcp-servers-settings-page.tsx`: Observer component using `useStore()` → `ai.mcpServers`. Loads servers on mount using `useParams()` + `workspaceStore.getWorkspaceBySlug()` (same pattern as `ai-settings-page.tsx`). Shows empty state when no servers registered.
- Route page: thin wrapper at `/[workspaceSlug]/settings/mcp-servers/page.tsx`.
- Nav entry: "MCP Servers" with `ServerCog` icon added after "AI Providers" in settings layout `Workspace` section.

## Deviations from Plan

None — plan executed exactly as written.

## Test Results

```
MCPServersStore (6 tests)
  ✓ loadServers() fetches from GET /workspaces/{id}/mcp-servers and populates servers observable
  ✓ loadServers() sets isLoading=true during fetch and isLoading=false after completion
  ✓ loadServers() sets error string on API failure; servers remains empty array
  ✓ registerServer() calls POST /workspaces/{id}/mcp-servers with payload, then appends to servers list
  ✓ removeServer() calls DELETE /workspaces/{id}/mcp-servers/{serverId}, removes entry from servers observable
  ✓ refreshStatus() calls GET .../status and updates matching server status field in servers observable
```

## Deviations from Plan (Post-Verification Fixes)

### Auto-fixed Issues (Rule 1 - Bug)

**1. [Rule 1 - Bug] Migration 071: duplicate CREATE TYPE and duplicate index**
- **Found during:** Task 3 (human verification - browser testing)
- **Issue:** Migration 071 contained a duplicate `CREATE TYPE mcp_auth_type` and duplicate index definition, causing migration to fail on a clean database.
- **Fix:** Removed the duplicate statements in migration 071.
- **Commit:** 477603b1

**2. [Rule 1 - Bug] SQLAlchemy StrEnum values_callable missing for MCP auth type**
- **Found during:** Task 3 (human verification - browser testing)
- **Issue:** SQLAlchemy `StrEnum` needed `values_callable=lambda x: [e.value for e in x]` to store enum values (not names) in the database. Without it, the column stored `"bearer"` as `"BEARER"`, breaking the backend schema validation.
- **Fix:** Added `values_callable` to the `auth_type` column definition in the `WorkspaceMcpServer` model.
- **Commit:** 477603b1

## Self-Check: PASSED

All 7 files confirmed to exist on disk. Task commits verified:
- `e9c3a12b`: feat(14-04): add MCPServersStore, mcp-servers API client, and store tests
- `5be53fd1`: feat(14-04): add MCP server settings UI components, page, and route
- `477603b1`: fix(14-04): resolve migration enum and SQLAlchemy StrEnum mismatch

`pnpm type-check` exits 0. `pnpm lint` on new files: 0 errors. `pnpm test src/stores/ai/__tests__/MCPServersStore.test.ts`: 6/6 pass.

## Checkpoint 3: Human Verification - APPROVED

All 9 verification steps passed:
1. Navigated to `/workspace/settings/mcp-servers` — page renders
2. "MCP Servers" link visible in settings sidebar
3. Empty state with "Register New MCP Server" collapsible form
4. Registered "Test MCP" with URL `https://example.com/sse` and bearer token
5. Server card appeared with name, URL, Bearer badge, Unknown status
6. Refresh status — badge updated to "Failed" (correct for unreachable example.com)
7. Delete — confirmation dialog — server removed, empty state restored
8. OAuth 2.0 radio — shows Client ID, Auth URL, Token URL fields
9. Backend logs showed clean `mcp_server_registered`/`probed`/`deleted` events, no errors

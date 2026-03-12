# Phase 22: Integration Safety -- Session & OAuth2 UI - Research

**Researched:** 2026-03-12
**Domain:** SQLAlchemy async session safety, OAuth2 Authorization Code flow, MobX/React UI wiring
**Confidence:** HIGH

## Summary

Phase 22 closes two specific integration gaps identified in the v1.0-alpha audit: (1) a race condition where `SeedPluginsService` shares the request-scoped `session` via `asyncio.create_task` fire-and-forget, and (2) the missing OAuth2 "Authorize" button in the MCP server management UI that completes the OAuth2 flow already implemented on the backend.

The backend already has a complete OAuth2 flow: `GET /{workspace_id}/mcp-servers/{server_id}/oauth-url` generates the authorization URL with Redis-backed state, and `GET /api/v1/oauth2/mcp-callback` handles the code-for-token exchange. The frontend store already has `getOAuthUrl()` wired. The gap is purely UI: no button exists to trigger authorization, and no callback status handling exists on the settings page.

**Primary recommendation:** Fix the session bug by giving `SeedPluginsService` an independent session from `get_db_session()`, then add an "Authorize" button to `MCPServerCard` for OAuth2 servers and handle the `?status=` query param on the MCP settings page after callback redirect.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SKRG-05 | Session safety -- SeedPluginsService must not share the request-scoped session across task boundaries | Session isolation pattern via `get_db_session()` context manager; existing pattern already used in `mcp_oauth_callback` (line 573 of workspace_mcp_servers.py) |
| MCP-03 | OAuth2 flow completion -- admin can authorize OAuth2 MCP servers end-to-end | Backend fully implemented (oauth-url endpoint + callback); store method `getOAuthUrl()` exists; gap is UI button + redirect status handling |
</phase_requirements>

## Standard Stack

### Core (already in project -- no new dependencies)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy (async) | 2.x | Database sessions | Already used; `get_db_session()` provides independent session lifecycle |
| MobX + mobx-react-lite | 6.x / 4.x | Frontend state | Already used; MCPServersStore has `getOAuthUrl()` |
| Next.js App Router | 15.x | Routing + query params | Already used; `useSearchParams()` for callback status |
| shadcn/ui | latest | UI components | Already used; Button, Badge, toast from sonner |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| sonner (toast) | already installed | Success/error notifications | After OAuth callback redirect lands on settings page |

### Alternatives Considered

None -- all work uses existing stack. No new dependencies required.

## Architecture Patterns

### Pattern 1: Independent Session for Background Tasks

**What:** When spawning `asyncio.create_task` from a request handler, the background task MUST use its own session, not the request-scoped one.
**When to use:** Any fire-and-forget pattern where the background task outlives the request.
**Why:** The request session is committed/closed when the response returns. The background task may still be running, causing `session is closed` or silent data loss.

**Current bug (workspaces.py:152):**
```python
# BAD: shares request-scoped `session` with background task
asyncio.create_task(
    SeedPluginsService(db_session=session).seed_workspace(
        workspace_id=workspace.id,
    )
)
```

**Fix pattern (from mcp_oauth_callback, line 573):**
```python
# GOOD: background task creates its own session
async def _seed_workspace_background(workspace_id: UUID) -> None:
    """Seed plugins in an independent session."""
    from pilot_space.infrastructure.database import get_db_session
    async with get_db_session() as independent_session:
        svc = SeedPluginsService(db_session=independent_session)
        await svc.seed_workspace(workspace_id=workspace_id)

asyncio.create_task(_seed_workspace_background(workspace.id))
```

The `get_db_session()` context manager (engine.py:112-129) creates a fresh session, auto-commits on success, and auto-rollbacks on exception. This is the exact pattern already used in the OAuth callback handler.

### Pattern 2: OAuth2 Authorization Code Flow (UI completion)

**What:** The backend OAuth2 flow is fully implemented. The UI needs to: (1) call `getOAuthUrl()` to get the authorization URL, (2) open it in a new window/redirect, (3) handle the callback redirect back to the settings page.

**Backend flow (already complete):**
```
1. Frontend calls GET /workspaces/{id}/mcp-servers/{serverId}/oauth-url
2. Backend generates state nonce, stores in Redis (10min TTL)
3. Backend returns { auth_url, state }
4. Frontend opens auth_url (browser navigates to OAuth provider)
5. User authorizes, provider redirects to /api/v1/oauth2/mcp-callback?code=X&state=Y
6. Backend exchanges code for token, encrypts, stores in DB
7. Backend redirects browser to /settings/mcp-servers?status=connected (or ?status=error&reason=X)
```

**Frontend gap:**
- `MCPServerCard` shows an "OAuth2" badge but has no "Authorize" button
- `MCPServersSettingsPage` does not read `?status=` query params
- `MCPServersStore.getOAuthUrl()` exists but is never called from UI

**UI fix:**
```typescript
// In MCPServerCard: Add onAuthorize callback for oauth2 servers
interface MCPServerCardProps {
  server: MCPServer;
  onDelete: (serverId: string) => void;
  onRefreshStatus: (serverId: string) => void;
  onAuthorize?: (serverId: string) => void;  // NEW
  isDeleting: boolean;
}

// Show "Authorize" button when auth_type === 'oauth2'
{server.auth_type === 'oauth2' && (
  <Button variant="outline" size="sm" onClick={() => onAuthorize?.(server.id)}>
    Authorize
  </Button>
)}
```

```typescript
// In MCPServersSettingsPage: Handle callback status via useSearchParams
const searchParams = useSearchParams();
const oauthStatus = searchParams.get('status');
const oauthReason = searchParams.get('reason');

React.useEffect(() => {
  if (oauthStatus === 'connected') {
    toast.success('OAuth authorization successful');
    mcpStore.loadServers(workspaceId); // Refresh to show updated status
  } else if (oauthStatus === 'error') {
    toast.error(`OAuth authorization failed: ${oauthReason || 'unknown error'}`);
  }
}, [oauthStatus, oauthReason]);

// Handler for authorize button
const handleAuthorize = async (serverId: string) => {
  const url = await mcpStore.getOAuthUrl(workspaceId, serverId);
  window.location.href = url; // Redirect to OAuth provider
};
```

### Pattern 3: Callback Redirect URL Considerations

**What:** The OAuth callback redirects to `/settings/mcp-servers?status=connected`. This is a relative path without the workspace slug prefix.
**Issue:** The Next.js app uses workspace-scoped routes: `/{workspaceSlug}/settings/mcp-servers`. The backend callback redirect (line 534, 614) uses `redirect_base = "/settings/mcp-servers"` which will NOT resolve correctly in the workspace-scoped Next.js app router.
**Fix:** The callback redirect must include the workspace slug. Store it in Redis state data alongside `server_id` and `workspace_id`, then use it in the redirect URL.

### Anti-Patterns to Avoid

- **Sharing request session with background tasks:** The exact bug being fixed. SQLAlchemy async sessions are NOT thread/task-safe when the parent request closes.
- **Opening OAuth in popup window:** Use `window.location.href` for the OAuth redirect, not `window.open()`. The callback redirect from the backend returns to `/settings/mcp-servers`, which expects a full page context.
- **Forgetting to refresh after OAuth callback:** The page must call `loadServers()` after detecting `?status=connected` to show the updated server state.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Independent DB session | Manual engine/session creation | `get_db_session()` from `infrastructure.database` | Already handles commit/rollback lifecycle |
| OAuth state management | Custom state storage | Existing Redis-backed state in `workspace_mcp_servers.py` | Already implemented with 10min TTL and one-time-use invalidation |
| URL query param reading | Manual `window.location` parsing | `useSearchParams()` from `next/navigation` | Next.js standard; handles SSR hydration correctly |

## Common Pitfalls

### Pitfall 1: Session Closed After Request Returns
**What goes wrong:** `asyncio.create_task` with request session. The task runs after the request handler returns and session is committed/closed.
**Why it happens:** FastAPI middleware commits the session when the response is sent. The background task still holds a reference to the closed session.
**How to avoid:** Always use `get_db_session()` for independent session lifecycle in background tasks.
**Warning signs:** `sqlalchemy.exc.InvalidRequestError: Session is closed` in logs, or silent data not persisting.

### Pitfall 2: OAuth Callback Redirect Without Workspace Slug
**What goes wrong:** Backend callback redirects to `/settings/mcp-servers?status=connected` but the Next.js app expects `/{slug}/settings/mcp-servers`.
**Why it happens:** The backend `redirect_base` is hardcoded without workspace context.
**How to avoid:** Store `workspace_slug` in Redis state data during `get_mcp_oauth_url`, include it in the redirect URL in `mcp_oauth_callback`.
**Warning signs:** 404 page after OAuth authorization, or redirect to wrong route.

### Pitfall 3: SeedPluginsService Non-Fatal Error Handling
**What goes wrong:** If the independent session fix introduces a new exception path (e.g., `get_db_session()` fails to connect), it could propagate up and crash the workspace creation.
**Why it happens:** The try/except is inside `SeedPluginsService.seed_workspace()`, but session creation happens outside it.
**How to avoid:** Wrap the entire background task (including session creation) in try/except with logging. Keep the non-fatal contract.
**Warning signs:** Workspace creation 500 errors when DB pool is exhausted.

### Pitfall 4: useSearchParams Suspense Boundary
**What goes wrong:** `useSearchParams()` in Next.js App Router requires a `<Suspense>` boundary in the parent, or it throws during static rendering.
**Why it happens:** Next.js 14+ treats `useSearchParams` as a dynamic API that triggers client-side bailout.
**How to avoid:** The MCP settings page is already `'use client'` and rendered inside the workspace layout (dynamic route `[workspaceSlug]`), so this should be fine. But verify no SSR error appears.
**Warning signs:** `useSearchParams() should be wrapped in a suspense boundary` warning in dev console.

## Code Examples

### Fix 1: Independent Session for SeedPluginsService (workspaces.py)

```python
# Source: Pattern from workspace_mcp_servers.py:566-573 (mcp_oauth_callback)
# File: backend/src/pilot_space/api/v1/routers/workspaces.py

# Replace lines 145-156 with:
import asyncio
from pilot_space.application.services.workspace_plugin.seed_plugins_service import (
    SeedPluginsService,
)
from pilot_space.infrastructure.logging import get_logger

_logger = get_logger(__name__)

async def _seed_workspace_background(workspace_id: UUID) -> None:
    """Seed default plugins using an independent DB session.

    Non-fatal: all exceptions are caught and logged.
    """
    try:
        from pilot_space.infrastructure.database import get_db_session
        async with get_db_session() as bg_session:
            await SeedPluginsService(db_session=bg_session).seed_workspace(
                workspace_id=workspace_id,
            )
    except Exception:
        _logger.exception(
            "Background plugin seeding failed for workspace %s",
            workspace_id,
        )

asyncio.create_task(_seed_workspace_background(workspace.id))  # noqa: RUF006
```

### Fix 2: OAuth Callback Redirect with Workspace Slug

```python
# Source: workspace_mcp_servers.py — modify get_mcp_oauth_url and mcp_oauth_callback
# In get_mcp_oauth_url: add workspace_slug to Redis state
from pilot_space.infrastructure.database.repositories.workspace_repository import (
    WorkspaceRepository,
)

# After resolving workspace, get slug:
state_data = {
    "server_id": str(server_id),
    "workspace_id": str(workspace_id),
    "workspace_slug": workspace.slug,  # NEW
    "nonce": nonce,
}

# In mcp_oauth_callback: use workspace_slug in redirect
workspace_slug = state_data.get("workspace_slug", "")
redirect_base = f"/{workspace_slug}/settings/mcp-servers" if workspace_slug else "/settings/mcp-servers"
```

### Fix 3: Authorize Button in MCPServerCard

```typescript
// Source: frontend/src/features/settings/components/mcp-server-card.tsx
// Add onAuthorize to props, render button for OAuth2 servers

// In the actions div, before the delete button:
{server.auth_type === 'oauth2' && onAuthorize && (
  <Button
    variant="outline"
    size="sm"
    className="h-8"
    onClick={() => onAuthorize(server.id)}
    title="Authorize OAuth2 connection"
  >
    Authorize
  </Button>
)}
```

### Fix 4: OAuth Status Handling in MCPServersSettingsPage

```typescript
// Source: frontend/src/features/settings/pages/mcp-servers-settings-page.tsx
import { useSearchParams } from 'next/navigation';

// Inside the observer component:
const searchParams = useSearchParams();

React.useEffect(() => {
  const status = searchParams.get('status');
  const reason = searchParams.get('reason');
  if (status === 'connected') {
    toast.success('MCP server authorized successfully');
  } else if (status === 'error') {
    toast.error(`OAuth authorization failed: ${reason || 'Unknown error'}`);
  }
}, [searchParams]);

const handleAuthorize = async (serverId: string) => {
  try {
    const authUrl = await mcpStore.getOAuthUrl(workspaceId, serverId);
    window.location.href = authUrl;
  } catch {
    toast.error('Failed to start OAuth authorization');
  }
};
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Shared session in fire-and-forget | Independent session via `get_db_session()` | This phase | Prevents race condition / silent data loss |
| OAuth2 config saved but no UI trigger | "Authorize" button + callback handling | This phase | Completes MCP-03 end-to-end |

## Open Questions

1. **Should SeedTemplatesService also be fixed?**
   - What we know: Only `SeedPluginsService` is called in `workspaces.py:152` via `create_task`. `SeedTemplatesService` has the same docstring pattern ("Called via asyncio.create_task") but is not visible in the current workspaces.py router.
   - What's unclear: Whether SeedTemplatesService is called elsewhere with the same session-sharing pattern.
   - Recommendation: Grep for other `create_task` + session patterns in the router layer; fix any found.

2. **OAuth callback redirect_base missing workspace slug**
   - What we know: Backend hardcodes `redirect_base = "/settings/mcp-servers"` without workspace slug prefix.
   - What's unclear: Whether the Next.js proxy or middleware rewrites this path. The app router uses `/(workspace)/[workspaceSlug]/settings/mcp-servers`.
   - Recommendation: Store workspace slug in Redis state and use it in the redirect. This is a bug fix bundled into MCP-03.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio (backend), vitest (frontend) |
| Config file | `backend/pyproject.toml`, `frontend/vitest.config.ts` |
| Quick run command | `cd backend && uv run pytest tests/unit/services/test_seed_plugins_service.py -x` |
| Full suite command | `make quality-gates-backend && make quality-gates-frontend` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SKRG-05 | SeedPluginsService uses independent session | unit | `cd backend && uv run pytest tests/unit/services/test_seed_plugins_service.py -x` | Exists (needs new test case) |
| SKRG-05 | Background task non-fatal when session creation fails | unit | `cd backend && uv run pytest tests/unit/services/test_seed_plugins_service.py -x` | Needs new test |
| MCP-03 | Authorize button renders for OAuth2 servers | unit | `cd frontend && pnpm test -- --run mcp-server-card` | Needs new test |
| MCP-03 | OAuth status toast on page load with ?status= | unit | `cd frontend && pnpm test -- --run mcp-servers-settings` | Needs new test |
| MCP-03 | getOAuthUrl called and redirects browser | unit | `cd frontend && pnpm test -- --run mcp-servers-settings` | Needs new test |
| MCP-03 | Callback redirect includes workspace slug | unit | `cd backend && uv run pytest tests/api/test_workspace_mcp_servers.py -x -k oauth` | Exists (xfail stub, needs update) |

### Sampling Rate
- **Per task commit:** `cd backend && uv run pytest tests/unit/services/test_seed_plugins_service.py tests/api/test_workspace_mcp_servers.py -x`
- **Per wave merge:** `make quality-gates-backend && make quality-gates-frontend`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `frontend/src/features/settings/components/__tests__/mcp-server-card.test.tsx` -- covers MCP-03 Authorize button rendering
- [ ] `frontend/src/features/settings/pages/__tests__/mcp-servers-settings-page.test.tsx` -- covers MCP-03 OAuth status handling
- [ ] New test case in `test_seed_plugins_service.py` -- covers SKRG-05 independent session usage verification
- [ ] Update `test_workspace_mcp_servers.py` xfail tests -- MCP-03 OAuth callback with workspace slug

## Sources

### Primary (HIGH confidence)
- Direct codebase analysis of:
  - `backend/src/pilot_space/api/v1/routers/workspaces.py` (lines 145-156) -- the session sharing bug
  - `backend/src/pilot_space/application/services/workspace_plugin/seed_plugins_service.py` -- service taking session param
  - `backend/src/pilot_space/infrastructure/database/engine.py` (lines 112-129) -- `get_db_session()` context manager
  - `backend/src/pilot_space/api/v1/routers/workspace_mcp_servers.py` -- full OAuth2 backend implementation
  - `frontend/src/stores/ai/MCPServersStore.ts` -- `getOAuthUrl()` method already exists
  - `frontend/src/features/settings/components/mcp-server-card.tsx` -- no authorize button
  - `frontend/src/features/settings/pages/mcp-servers-settings-page.tsx` -- no callback status handling
  - `frontend/src/services/api/mcp-servers.ts` -- `getOAuthUrl` API method exists

### Secondary (MEDIUM confidence)
- SQLAlchemy async session safety: session objects are not safe to share across concurrent tasks when the parent task closes the session

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies, all patterns already in codebase
- Architecture: HIGH -- both bugs are well-understood with clear fix patterns already present in codebase
- Pitfalls: HIGH -- all pitfalls identified from direct code reading

**Research date:** 2026-03-12
**Valid until:** 2026-04-12 (stable codebase, no external dependency changes)

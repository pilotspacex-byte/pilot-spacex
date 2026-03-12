# Phase 14: Remote MCP Server Management - Research

**Researched:** 2026-03-10
**Domain:** Remote MCP server registry — persistence, encrypted auth tokens, connection health checks, hot-loading into PilotSpaceAgent per workspace request
**Confidence:** HIGH

---

## Summary

Phase 14 extends the existing AI infrastructure with a workspace-scoped remote MCP server registry. The project already has all the primitives needed: Fernet encryption (`infrastructure/encryption.py`, `SecureKeyStorage`), pattern-matched database models (`AIConfiguration` is a direct analogue), workspace-scoped repositories, and the SDK's `McpServerConfig` union type (`McpSSEServerConfig | McpHttpServerConfig`) already supports Bearer token headers for remote server auth.

The work splits into four surfaces:

1. **Backend DB + Domain**: New `workspace_mcp_servers` table (migration 071), `WorkspaceMcpServer` SQLAlchemy model, `WorkspaceMcpServerRepository`. Encrypted token column using the same `encrypt_api_key` / `decrypt_api_key` utilities already used by `AIConfiguration`.

2. **Backend API**: New router `workspace_mcp_servers.py` mounted under `/workspaces/{workspace_id}/mcp-servers` providing CRUD + connection status check. Admin-only (OWNER or ADMIN role, same gate as `workspace_ai_settings.py`).

3. **Backend Agent wiring**: `build_mcp_servers()` in `pilotspace_stream_utils.py` is the single injection point — augment it to query registered `WorkspaceMcpServer` rows for the incoming `workspace_id`, decrypt their tokens, and append `McpSSEServerConfig | McpHttpServerConfig` entries to the `servers` dict. This achieves MCP-04 hot-load per workspace request without agent restart.

4. **Frontend**: New `MCPServersStore` (MobX) + `MCPServersSettingsPage` + `MCPServerCard` component in `frontend/src/features/settings/`. New Next.js route `settings/mcp-servers/page.tsx`. OAuth 2.0 flow requires a backend `/oauth/callback` route that exchanges the code for a token, encrypts it, and stores it — analogous to `DriveOAuthService`.

OAuth 2.0 for MCP-03 is the most complex part. The existing `DriveOAuthService` pattern (PKCE state registry in Redis, callback handler stores encrypted token) is the correct template. The key difference is the registered server's OAuth metadata (auth URL, token URL, client ID, scopes) must be stored per server row, not per provider.

**Primary recommendation:** Create `workspace_mcp_servers` table (migration 071) with encrypted `auth_token` column and nullable `oauth_*` columns; use `encrypt_api_key`/`decrypt_api_key` from `infrastructure/encryption.py`; inject registered servers into `build_mcp_servers()` using `McpSSEServerConfig` with `Authorization: Bearer {token}` header; model `MCPServersStore` after `AISettingsStore`; model OAuth flow after `DriveOAuthService`.

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| MCP-01 | Workspace owner/admin can register a remote MCP server by URL + display name | New `POST /workspaces/{id}/mcp-servers` endpoint; `WorkspaceMcpServer` model with `url` + `display_name`; admin-gate from `_get_admin_workspace()` pattern in `workspace_ai_settings.py` |
| MCP-02 | Bearer token auth — token stored securely per workspace | `encrypt_api_key(token, master_secret)` from `infrastructure/encryption.py`; stored in `auth_token_encrypted` column; mirrored pattern from `ai_configurations.api_key_encrypted` |
| MCP-03 | OAuth 2.0 redirect auth — token stored after callback | `DriveOAuthService` PKCE pattern; Redis pending-state TTL=600s; new `/oauth2/mcp-callback` endpoint stores decrypted token back via encrypted column |
| MCP-04 | Registered servers dynamically available to PilotSpaceAgent (hot-load) | Augment `build_mcp_servers()` in `pilotspace_stream_utils.py`; query `WorkspaceMcpServerRepository.get_active_by_workspace(workspace_id)`; construct `McpSSEServerConfig` with auth header |
| MCP-05 | Connection status badge (connected / failed / unknown) per server | `GET /workspaces/{id}/mcp-servers/{server_id}/status` — httpx HEAD/GET to server URL with 5s timeout; returns enum `connected | failed | unknown` |
| MCP-06 | Owner/admin can remove a registered server | `DELETE /workspaces/{id}/mcp-servers/{server_id}` — soft-delete via `is_deleted=True`; agent hot-reload picks up removal on next request (no registry cache) |
</phase_requirements>

---

## Standard Stack

### Core (Already in Project — No New Dependencies)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy async | in uv.lock | `WorkspaceMcpServer` model + repository | Project ORM standard |
| alembic | in uv.lock | Migration 071 — new table + RLS | Project migration standard |
| cryptography (Fernet) | in uv.lock | Encrypt/decrypt Bearer tokens at rest | Same as `AIConfiguration.api_key_encrypted` |
| httpx | in uv.lock | Connection status health check (HEAD to server URL) | Already used in `key_validator.py` |
| MobX | in package.json | `MCPServersStore` observable state | Project frontend state standard |
| shadcn/ui | in package.json | `MCPServerCard`, `StatusBadge` | Project UI component library |
| Redis (fakeredis in tests) | in uv.lock | OAuth PKCE pending-state registry (MCP-03) | Already used in `DriveOAuthService` |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `claude_agent_sdk.McpSSEServerConfig` | installed | Remote SSE MCP server config with headers | Used for Bearer token auth; maps `{"type": "sse", "url": ..., "headers": {"Authorization": "Bearer ..."}}` |
| `claude_agent_sdk.McpHttpServerConfig` | installed | Remote HTTP MCP server config | Alternative transport if server supports streamable HTTP |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Soft delete (`is_deleted`) for MCP-06 | Hard delete | Soft delete matches existing project pattern; audit trail preserved |
| Per-request DB query for active servers | Cache (Redis TTL) | Per-request query is simpler, correct, eliminates cache invalidation on delete; latency is one indexed query |
| `McpSSEServerConfig` | `McpStdioServerConfig` | stdio requires local process — remote servers use SSE or HTTP |

**Installation:** No new packages required.

---

## Architecture Patterns

### Recommended Project Structure

New files:

```
backend/
├── alembic/versions/
│   └── 071_add_workspace_mcp_servers.py              # Migration: table + RLS
├── src/pilot_space/
│   ├── infrastructure/database/models/
│   │   └── workspace_mcp_server.py                   # WorkspaceMcpServer SQLAlchemy model
│   ├── infrastructure/database/repositories/
│   │   └── workspace_mcp_server_repository.py        # WorkspaceMcpServerRepository
│   ├── api/v1/
│   │   ├── routers/
│   │   │   └── workspace_mcp_servers.py              # CRUD + status + OAuth endpoints
│   │   └── schemas/
│   │       └── mcp_server.py                         # Pydantic schemas
│   └── ai/agents/
│       └── (modify pilotspace_stream_utils.py)       # Augment build_mcp_servers()

frontend/
├── src/
│   ├── features/settings/
│   │   ├── pages/
│   │   │   └── mcp-servers-settings-page.tsx         # MCPServersSettingsPage (observer)
│   │   └── components/
│   │       ├── mcp-server-card.tsx                   # Card with status badge + actions
│   │       └── mcp-server-form.tsx                   # Register form (URL, display name, auth type)
│   ├── stores/ai/
│   │   └── MCPServersStore.ts                        # MobX store
│   ├── services/api/
│   │   └── mcp-servers.ts                            # API client functions
│   └── app/(workspace)/[workspaceSlug]/settings/
│       └── mcp-servers/
│           └── page.tsx                              # Next.js route
```

### Pattern 1: WorkspaceMcpServer Model (mirrors AIConfiguration)

**What:** SQLAlchemy model extending `WorkspaceScopedModel` (gets `workspace_id`, `is_deleted`, timestamps for free).
**When to use:** All workspace-scoped entities in this project follow this base.

```python
# Source: backend/src/pilot_space/infrastructure/database/models/ai_configuration.py (pattern)
class WorkspaceMcpServer(WorkspaceScopedModel):
    __tablename__ = "workspace_mcp_servers"

    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    url: Mapped[str] = mapped_column(String(512), nullable=False)
    auth_type: Mapped[McpAuthType] = mapped_column(
        Enum(McpAuthType, name="mcp_auth_type", create_type=False),
        nullable=False,
        default=McpAuthType.BEARER,
    )
    # Encrypted Bearer token or OAuth access token
    auth_token_encrypted: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    # OAuth metadata (required when auth_type=OAUTH2)
    oauth_client_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    oauth_auth_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    oauth_token_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    oauth_scopes: Mapped[str | None] = mapped_column(String(512), nullable=True)
    # Status (cached from last check; updated by status endpoint)
    last_status: Mapped[str | None] = mapped_column(String(16), nullable=True)  # connected|failed|unknown
    last_status_checked_at: Mapped[datetime | None] = mapped_column(nullable=True)
```

### Pattern 2: Hot-Loading Remote MCP Servers in build_mcp_servers()

**What:** Query active registered servers for the workspace, construct `McpSSEServerConfig` entries, merge into existing `servers` dict.
**When to use:** Every chat request routed to `PilotSpaceAgent.stream()` already calls `build_mcp_servers()`.

```python
# Source: backend/src/pilot_space/ai/agents/pilotspace_stream_utils.py (existing pattern)
# Add at end of build_mcp_servers() before return:

async def _load_remote_mcp_servers(
    workspace_id: UUID | None,
    db_session: AsyncSession | None,
) -> dict[str, McpServerConfig]:
    """Load registered remote MCP servers for workspace (MCP-04)."""
    if workspace_id is None or db_session is None:
        return {}

    from pilot_space.infrastructure.database.repositories.workspace_mcp_server_repository import (
        WorkspaceMcpServerRepository,
    )
    from pilot_space.infrastructure.encryption import decrypt_api_key
    from pilot_space.config import get_settings

    repo = WorkspaceMcpServerRepository(session=db_session)
    registered = await repo.get_active_by_workspace(workspace_id)
    remote: dict[str, McpServerConfig] = {}
    settings = get_settings()

    for server in registered:
        token: str | None = None
        if server.auth_token_encrypted:
            try:
                token = decrypt_api_key(server.auth_token_encrypted, settings.secret_key)
            except Exception:
                logger.warning("mcp_token_decrypt_failed", server_id=str(server.id))
                continue

        config: McpSSEServerConfig = {
            "type": "sse",
            "url": server.url,
        }
        if token:
            config["headers"] = {"Authorization": f"Bearer {token}"}

        remote[f"remote_{server.id}"] = config

    return remote
```

Note: `build_mcp_servers()` is currently synchronous. Adding a DB query makes it async — callers must be updated or the DB call extracted into a pre-step called before `build_mcp_servers()`. The cleanest approach is to pass `remote_servers: dict` as a parameter built by the async caller in `pilotspace_agent.py`.

### Pattern 3: Connection Status Health Check

**What:** HEAD request to the registered URL with 5s timeout. Returns `connected | failed | unknown`.
**When to use:** Called by `GET /workspaces/{id}/mcp-servers/{server_id}/status`.

```python
# Source: backend/src/pilot_space/ai/providers/key_validator.py (httpx pattern)
async def check_mcp_server_status(url: str, token: str | None) -> str:
    """Check if remote MCP server is reachable. Returns 'connected'|'failed'|'unknown'."""
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url, headers=headers)
            if response.status_code < 500:
                return "connected"
            return "failed"
    except (httpx.TimeoutException, httpx.ConnectError):
        return "failed"
    except Exception:
        return "unknown"
```

### Pattern 4: OAuth 2.0 Flow (MCP-03)

**What:** Redirect-based OAuth. Admin clicks "Connect via OAuth" — backend generates state + code_verifier, stores in Redis (TTL=600s), returns authorization URL. User is redirected to provider. Provider redirects to `/api/v1/oauth2/mcp-callback?code=...&state=...`. Backend exchanges code for token, encrypts, stores in `auth_token_encrypted`.
**When to use:** Only when admin selects `auth_type = oauth2` on server registration.

```python
# Source: DriveOAuthService pattern (drive_oauth_service.py)
# Key differences from Drive OAuth:
# - state maps to server_id (not workspace_id alone)
# - token_url comes from server.oauth_token_url (not hardcoded Google endpoint)
# - No refresh token handling required for MVP
```

### Anti-Patterns to Avoid

- **Caching remote servers in memory**: Don't cache at singleton level — removes are instant per-request without a cache. Registry is small (admin-level, not high-cardinality).
- **Making build_mcp_servers() async directly**: The function is called synchronously inside `PilotSpaceAgent.stream()`. Pass pre-fetched remote servers as a parameter from the async `stream()` method instead.
- **Storing unencrypted tokens**: Bearer tokens go through `encrypt_api_key()` before insert, same path as AI provider keys. Never store plaintext.
- **Status polling on every chat request**: Status checks are on-demand (admin clicks "check status") or scheduled — never inline in the chat hot path.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Token encryption at rest | Custom AES | `encrypt_api_key` / `decrypt_api_key` from `infrastructure/encryption.py` | Already audited, Fernet, consistent key derivation |
| Remote MCP server SDK config | Custom HTTP MCP client | `McpSSEServerConfig` + `McpHttpServerConfig` from `claude_agent_sdk.types` | SDK handles connection lifecycle, tool listing, tool calling |
| OAuth PKCE state management | In-memory dict | Redis TTL key (or `DriveOAuthService._pending_states`) | Multi-worker safe; TTL expires stale states automatically |
| Admin permission check | New role check logic | `_get_admin_workspace()` pattern from `workspace_ai_settings.py` | Already validates workspace membership + OWNER/ADMIN role |
| Workspace-scoped DB model | Raw SQLAlchemy | `WorkspaceScopedModel` base class | Gets `workspace_id`, `is_deleted`, timestamps, RLS policy hooks |

**Key insight:** The SDK's `McpServerConfig` union type (`McpSSEServerConfig | McpHttpServerConfig`) is the entire integration contract — just supply `{"type": "sse", "url": ..., "headers": {"Authorization": "Bearer ..."}}` and the SDK handles the MCP protocol.

---

## Common Pitfalls

### Pitfall 1: build_mcp_servers() Is Synchronous

**What goes wrong:** `build_mcp_servers()` in `pilotspace_stream_utils.py` is currently a regular (sync) function. Calling `await repo.get_active_by_workspace()` inside it will fail.
**Why it happens:** The function was originally pure data transformation, not a DB accessor.
**How to avoid:** Fetch remote servers in `PilotSpaceAgent.stream()` (which is `async`) before calling `build_mcp_servers()`, pass them as a `remote_servers` parameter. Keep `build_mcp_servers()` sync — do not make it async (it would ripple through the call chain).
**Warning signs:** `SyntaxError: 'await' expression not valid in synchronous function` at startup or `RuntimeError: coroutine was never awaited`.

### Pitfall 2: RLS Missing on workspace_mcp_servers

**What goes wrong:** Without RLS, workspace members can read other workspaces' MCP server configs including encrypted tokens via direct SQL.
**Why it happens:** New tables require explicit RLS setup.
**How to avoid:** Migration 071 must include `ENABLE ROW LEVEL SECURITY`, `FORCE ROW LEVEL SECURITY`, workspace isolation policy using `current_setting('app.current_user_id', true)::uuid`, and service_role bypass — see `rls-check.md` rule.

### Pitfall 3: OAuth Callback State Collision

**What goes wrong:** If two admins simultaneously initiate OAuth for different servers, state keys could collide or be confused.
**Why it happens:** State must encode both `workspace_id` and `server_id`, not just a random nonce.
**How to avoid:** State key format: `mcp_oauth_{server_id}_{nonce}`. Store state → `{server_id, workspace_id, code_verifier}` in Redis.

### Pitfall 4: McpServerConfig Key Collision

**What goes wrong:** If a remote server name collides with a built-in server name in the `servers` dict, the built-in server gets silently overwritten.
**Why it happens:** `build_mcp_servers()` uses string keys from `SERVER_NAME` constants.
**How to avoid:** Prefix remote server keys with `remote_{server.id}` (UUID-based, guaranteed unique).

### Pitfall 5: Connection Status in Chat Hot Path

**What goes wrong:** Checking server reachability during `build_mcp_servers()` adds 5s timeout latency to every chat request.
**Why it happens:** Status check feels natural alongside server loading.
**How to avoid:** Status checks are explicit admin-triggered endpoint only (`GET .../status`). The agent loads all active servers unconditionally — the SDK handles connection failures gracefully.

### Pitfall 6: Token Decryption Failure Crashes Chat

**What goes wrong:** If `auth_token_encrypted` is corrupted, `decrypt_api_key()` raises `cryptography.fernet.InvalidToken`. This must not crash the entire chat session.
**Why it happens:** Fernet raises on corrupt ciphertext.
**How to avoid:** Wrap token decryption in `try/except`, log warning, skip the server (continue loop). Agent proceeds without that server's tools.

---

## Code Examples

### McpSSEServerConfig with Bearer Auth

```python
# Source: backend/.venv/lib/python3.12/site-packages/claude_agent_sdk/types.py
from claude_agent_sdk import McpServerConfig

server_config: McpServerConfig = {
    "type": "sse",
    "url": "https://mcp.example.com/sse",
    "headers": {"Authorization": "Bearer sk-..."},
}
```

### encrypt_api_key / decrypt_api_key (existing pattern)

```python
# Source: backend/src/pilot_space/infrastructure/encryption.py
from pilot_space.infrastructure.encryption import encrypt_api_key, decrypt_api_key

encrypted = encrypt_api_key(plain_token, master_secret)   # Store this
plain = decrypt_api_key(encrypted, master_secret)          # Read this
```

### Admin Permission Gate (existing pattern)

```python
# Source: backend/src/pilot_space/api/v1/routers/workspace_ai_settings.py
async def _get_admin_workspace(
    workspace_id: UUID,
    current_user: CurrentUser,
    session: DbSession,
) -> Workspace:
    workspace_repo = WorkspaceRepository(session=session)
    workspace = await workspace_repo.get_with_members(workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    member = next((m for m in workspace.members if m.user_id == current_user.id), None)
    if not member or member.role not in ("OWNER", "ADMIN"):
        raise HTTPException(status_code=403, detail="Admin access required")
    return workspace
```

### MobX Store Pattern (mirrors AISettingsStore)

```typescript
// Source: frontend/src/stores/ai/AISettingsStore.ts (pattern)
import { makeAutoObservable, runInAction } from 'mobx';

export class MCPServersStore {
  servers: MCPServer[] = [];
  isLoading = false;
  error: string | null = null;

  constructor() {
    makeAutoObservable(this);
  }

  async loadServers(workspaceId: string) {
    runInAction(() => { this.isLoading = true; this.error = null; });
    try {
      const data = await mcpServersApi.list(workspaceId);
      runInAction(() => { this.servers = data.items; });
    } catch (e) {
      runInAction(() => { this.error = String(e); });
    } finally {
      runInAction(() => { this.isLoading = false; });
    }
  }
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Stdio MCP servers (local process) | SSE/HTTP remote MCP servers | MCP spec 2024 | Remote servers require URL + auth headers, not subprocess commands |
| Global fixed MCP tool list | Per-workspace dynamic tool list | Phase 14 | Each workspace gets its own tool surface from registered servers |

**Deprecated/outdated:**
- `McpStdioServerConfig`: Requires local process — inappropriate for remote external services. All registered remote MCP servers use `McpSSEServerConfig` or `McpHttpServerConfig`.

---

## Open Questions

1. **OAuth 2.0 token refresh**
   - What we know: `DriveOAuthService` does not implement refresh token rotation for MVP.
   - What's unclear: MCP servers may issue short-lived tokens (1h). Do we need refresh?
   - Recommendation: Store `refresh_token_encrypted` column but implement refresh only if a server returns 401 during status check (v2 scope). For MVP, display "token expired" status and prompt re-auth.

2. **MCP-07 tool discovery (v2 out of scope)**
   - What we know: REQUIREMENTS.md marks MCP-07 as v2 (`MCP-07: MCP server tool discovery — list available tools`).
   - What's unclear: The SDK's `McpSSEServerConfig` handles tool listing transparently. The agent receives all tools from connected servers without explicit discovery step.
   - Recommendation: Do not implement explicit tool discovery UI in Phase 14 (out of scope per v2 designation). The agent auto-discovers tools via the SDK protocol.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio (backend); Vitest (frontend) |
| Config file | `backend/pyproject.toml` (pytest), `frontend/vitest.config.ts` |
| Quick run command | `cd backend && uv run pytest tests/ai/ tests/infrastructure/ -q` |
| Full suite command | `make quality-gates-backend && make quality-gates-frontend` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MCP-01 | POST /workspaces/{id}/mcp-servers creates server row | unit | `uv run pytest tests/api/test_workspace_mcp_servers.py::test_register_server -x` | ❌ Wave 0 |
| MCP-02 | Bearer token stored encrypted (not plaintext) in DB | unit | `uv run pytest tests/api/test_workspace_mcp_servers.py::test_token_encrypted_at_rest -x` | ❌ Wave 0 |
| MCP-03 | OAuth callback stores token after code exchange | unit | `uv run pytest tests/api/test_workspace_mcp_servers.py::test_oauth_callback_stores_token -x` | ❌ Wave 0 |
| MCP-04 | build_mcp_servers includes registered remote servers | unit | `uv run pytest tests/ai/agents/test_remote_mcp_loading.py -x` | ❌ Wave 0 |
| MCP-05 | Status endpoint returns connected/failed/unknown | unit | `uv run pytest tests/api/test_workspace_mcp_servers.py::test_status_endpoint -x` | ❌ Wave 0 |
| MCP-06 | DELETE soft-deletes server, next request excludes it | unit | `uv run pytest tests/api/test_workspace_mcp_servers.py::test_delete_removes_from_agent -x` | ❌ Wave 0 |
| MCPStore | MCPServersStore.loadServers populates observable | unit | `cd frontend && pnpm test src/stores/ai/__tests__/MCPServersStore.test.ts` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `cd backend && uv run pytest tests/api/test_workspace_mcp_servers.py -q`
- **Per wave merge:** `make quality-gates-backend && make quality-gates-frontend`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `backend/tests/api/test_workspace_mcp_servers.py` — covers MCP-01 through MCP-06
- [ ] `backend/tests/ai/agents/test_remote_mcp_loading.py` — covers MCP-04 agent injection
- [ ] `frontend/src/stores/ai/__tests__/MCPServersStore.test.ts` — covers frontend store

*(Existing test infrastructure sufficient for fixtures; new test files required for Phase 14 logic.)*

---

## Sources

### Primary (HIGH confidence)

- `claude_agent_sdk/types.py` (installed) — `McpSSEServerConfig`, `McpHttpServerConfig`, `McpServerConfig` union definition; verified `headers` field supports `Authorization: Bearer`
- `backend/src/pilot_space/infrastructure/encryption.py` — `encrypt_api_key`, `decrypt_api_key` function signatures
- `backend/src/pilot_space/ai/agents/pilotspace_stream_utils.py` — `build_mcp_servers()` injection point, server dict structure
- `backend/src/pilot_space/infrastructure/database/models/ai_configuration.py` — `WorkspaceScopedModel` pattern, encrypted column pattern
- `backend/src/pilot_space/application/services/ai/drive_oauth_service.py` — OAuth PKCE pattern for MCP-03
- `backend/src/pilot_space/api/v1/routers/workspace_ai_settings.py` — `_get_admin_workspace()` admin gate pattern
- `backend/src/pilot_space/ai/providers/key_validator.py` — httpx health-check pattern for MCP-05

### Secondary (MEDIUM confidence)

- MCP SSE transport spec (verified: SSE and streamable HTTP are the two remote transports; stdio is local-only) — consistent with `McpSSEServerConfig` and `McpHttpServerConfig` TypedDicts in SDK

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in use; `McpSSEServerConfig` inspected directly from installed SDK
- Architecture: HIGH — all four surfaces follow existing patterns (`AIConfiguration`, `DriveOAuthService`, `build_mcp_servers`, `AISettingsStore`)
- Pitfalls: HIGH — `build_mcp_servers` sync/async boundary verified by reading actual function signatures; encryption failure path verified by reading Fernet behavior

**Research date:** 2026-03-10
**Valid until:** 2026-04-10 (SDK types are stable; patterns are internal and project-controlled)

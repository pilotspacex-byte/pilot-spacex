# Implementation Plan: MCP Settings Redevelopment

**Feature**: MCP Settings Redevelopment
**Branch**: `25-mcp-settings`
**Created**: 2026-03-19
**Spec**: `specs/025-mcp-settings/spec.md`
**Author**: AI-generated

---

## Summary

Redevelop the MCP settings experience from a simple remote-server card list into a full-featured management page. The new design supports three server types (Remote/SSE, NPX, UVX), a 5-state status enum (Enabled/Disabled/Unhealthy/Unreachable/Config Error), bulk JSON import, background health polling, and enable/disable toggling — without deleting the existing backend foundation.

This plan is a **full-stack incremental redevelopment**: extend the existing `workspace_mcp_servers` backend and `MCPServersStore`/settings UI rather than rewrite from scratch.

---

## Technical Context

| Attribute | Value |
|-----------|-------|
| **Backend Language** | Python 3.12+ |
| **Backend Framework** | FastAPI 0.110+ |
| **ORM** | SQLAlchemy 2.0+ async |
| **Migrations** | Alembic |
| **Auth / RLS** | Supabase Auth + workspace RLS |
| **Encryption** | Fernet (existing `encrypt_api_key` / `decrypt_api_key`) |
| **Background Jobs** | pg_cron via Supabase (existing infrastructure) |
| **Frontend Framework** | Next.js 14+ App Router |
| **State Management** | MobX 6+ (`MCPServersStore`) |
| **Server State** | TanStack Query (mutations) |
| **Styling** | TailwindCSS + shadcn/ui |
| **Testing** | pytest (>80% cov), Vitest |
| **Performance targets** | API reads <500ms p95, API writes <1s p95, Connection test result ≤10s |

---

## Constitution Gate Check

### Technology Standards Gate

- [x] Python 3.12+, FastAPI — matches constitution
- [x] PostgreSQL 16+ with RLS — matches constitution
- [x] Supabase Auth + workspace_id RLS isolation — matches constitution
- [x] CQRS-lite with Use Case / Repository patterns — matches constitution
- [x] MobX for complex UI state — matches constitution (override: Zustand → MobX)
- [x] Fernet encryption for secrets at rest — matches existing security pattern
- [x] Next.js App Router, TailwindCSS, shadcn/ui — matches constitution

### Simplicity Gate

- [x] Extend existing `WorkspaceMcpServer` model — no new table; one Alembic migration
- [x] Re-use existing `encrypt_api_key` / `decrypt_api_key` — no new encryption layer
- [x] Re-use existing `_get_admin_workspace` guard — no new auth helper
- [x] Re-use existing `MCPServersStore` MobX store — extend, don't replace
- [x] No premature abstraction — NPX/UVX handled via `url_or_command` + `server_type` enum
- [x] No feature flags — cut-over replaces old UI; backend is additive (new fields nullable)

### Quality Gate

- [x] Backend type-check: pyright strict, zero errors
- [x] Backend lint: ruff, zero warnings
- [x] Backend coverage: pytest-cov >80%
- [x] Frontend type-check: tsc strict, zero errors
- [x] Frontend lint: ESLint, zero warnings
- [x] Frontend coverage: Vitest >80%
- [x] File size: 700 lines max per file

---

## Architecture Mapping

### Backend Layer Routing

| Concern | Layer | File(s) |
|---------|-------|---------|
| Domain entity | Domain | `workspace_mcp_server.py` (model, enum extension) |
| DB migration | Infrastructure | new Alembic migration |
| Repository | Infrastructure | `workspace_mcp_server_repository.py` (extend) |
| API schemas | Presentation | `_mcp_server_schemas.py` (extend) |
| REST endpoints | Presentation | `workspace_mcp_servers.py` (extend + new routes) |
| Background polling | Infrastructure | pg_cron SQL migration |
| Import parser | Application | new `mcp_import_service.py` |
| Test connection | Application | extracted from status probe, 10s timeout |

### Frontend Layer Routing

| Concern | Layer | File(s) |
|---------|-------|---------|
| Store | State | `MCPServersStore.ts` (extend types + methods) |
| API client | Services | `mcp-servers.ts` API service (extend) |
| Page | Feature | `mcp-servers-settings-page.tsx` (full redevelopment) |
| Table | Component | new `mcp-servers-table.tsx` |
| Dialog | Component | new `mcp-server-dialog.tsx` (tabs: Import JSON + Form Config) |
| Status badge | Component | new `mcp-status-badge.tsx` |
| Row actions | Component | new `mcp-server-row-actions.tsx` |

### Key Patterns Applied

| Pattern | Application |
|---------|-------------|
| Repository | `WorkspaceMcpServerRepository` owns all DB queries |
| CQRS-lite | Import → `ImportMcpServersCommand`; List → `ListMcpServersQuery` |
| Credential masking | Secrets never returned from API; edit shows `has_secret: true` flag |
| Soft-delete | Deleted servers set `is_deleted=True`; remain in DB for audit |
| Enable/Disable | `is_enabled` boolean column; disabled servers skipped by poller |
| Background polling | pg_cron job calls a Postgres function every 60s per enabled server |

---

## Phase 0: Research

### Resolved Decisions

| Question | Decision | Rationale |
|----------|----------|-----------|
| How to support NPX/UVX alongside remote servers | Extend `server_type` enum on existing model (`remote`, `npx`, `uvx`); rename `url` → `url_or_command` String(1024) | Additive migration, no data loss; command string maps cleanly to same field |
| Transport field | Add `transport` enum (`sse`, `stdio`, `streamable_http`) with smart default (SSE for remote, stdio for NPX/UVX) | Spec FR-04-3; no transport-level behavior change needed in backend at this layer |
| Status enum expansion | Replace `last_status` String(16) with `McpStatus` StrEnum: `enabled`, `disabled`, `unhealthy`, `unreachable`, `config_error` | Maps directly to spec clarification Q4; `is_enabled` controls admin toggle; poller sets health states |
| Background polling mechanism | pg_cron SQL job that calls a Postgres PL/pgSQL procedure every 60s; procedure iterates enabled servers and updates `last_status` | Consistent with existing Supabase/pg_cron infrastructure (DD-005); no new external service |
| SSRF for NPX/UVX | NPX/UVX commands run server-side — no SSRF risk from URL validation; command args validated for path traversal only (no shell metacharacters) | Security boundary: commands are spawned by backend runtime; allowlist approach |
| Credential masking on edit | API never returns `auth_token_encrypted`; response includes `has_headers_secret: bool` and `has_env_secret: bool` flags; frontend shows `••••••••` when flag is `true` | Spec Q1 answer; matches existing `auth_token_encrypted` pattern |
| Duplicate server name on import | Import service iterates detected servers; servers whose `name` collides with existing `display_name` in same workspace are skipped; response includes `imported: [...]` and `skipped: [...]` arrays | Spec Q2 answer |
| Connection test timeout | 10 seconds (both httpx async client and stdio subprocess probe) | Spec Q5 answer; existing status probe used 5s — upgraded |
| Command Arguments for NPX/UVX | Single `command_args` String(512) field stored on model; appended to the launch command at runtime | Spec FR-04-7 |
| Header key-value pairs | Stored as `headers_encrypted` JSON blob (Fernet-encrypted); deserialized at probe/connection time | Maps to spec `headers` key-value map; reuses existing encryption |
| Env vars for NPX/UVX | Stored as `env_vars_encrypted` JSON blob (Fernet-encrypted); injected into subprocess env at launch | Maps to spec `env_vars` key-value map |

---

## Phase 1: Data Model

### Migration: `025_mcp_settings_redevelopment`

**Table**: `workspace_mcp_servers` (existing)

**Changes** (all additive or type-safe replacements):

| Column | Change | Type | Nullable | Default |
|--------|--------|------|----------|---------|
| `server_type` | ADD | `mcp_server_type` enum (`remote`, `npx`, `uvx`) | NOT NULL | `'remote'` |
| `transport` | ADD | `mcp_transport` enum (`sse`, `stdio`, `streamable_http`) | NOT NULL | `'sse'` |
| `url_or_command` | ADD (alias) | `VARCHAR(1024)` | NULL | NULL |
| `command_args` | ADD | `VARCHAR(512)` | NULL | NULL |
| `headers_encrypted` | ADD | `TEXT` | NULL | NULL |
| `env_vars_encrypted` | ADD | `TEXT` | NULL | NULL |
| `is_enabled` | ADD | `BOOLEAN` | NOT NULL | `TRUE` |
| `last_status` | ALTER | `mcp_status` enum (`enabled`, `disabled`, `unhealthy`, `unreachable`, `config_error`) | NULL | NULL |
| `url` | KEEP | existing `VARCHAR(512)` — populated from `url_or_command` on migrate; backfill |

**Migration strategy**:
1. Add new columns with nullable/defaults.
2. Backfill: `UPDATE workspace_mcp_servers SET url_or_command = url, server_type = 'remote', transport = 'sse', is_enabled = TRUE`.
3. Rename old `last_status` String(16) to new enum via `USING` cast (map `'connected'→'enabled'`, `'failed'→'unreachable'`, `'unknown'→NULL`).
4. Keep `url` column for backward compatibility with existing tool hot-load code; sync from `url_or_command` on write.

### Alembic Model Update: `WorkspaceMcpServer`

```python
class McpServerType(StrEnum):
    REMOTE = "remote"
    NPX = "npx"
    UVX = "uvx"

class McpTransport(StrEnum):
    SSE = "sse"
    STDIO = "stdio"
    STREAMABLE_HTTP = "streamable_http"

class McpStatus(StrEnum):
    ENABLED = "enabled"
    DISABLED = "disabled"
    UNHEALTHY = "unhealthy"
    UNREACHABLE = "unreachable"
    CONFIG_ERROR = "config_error"
```

**New columns on `WorkspaceMcpServer`**:
- `server_type: Mapped[McpServerType]` — default `REMOTE`
- `transport: Mapped[McpTransport]` — default `SSE`
- `url_or_command: Mapped[str | None]` — primary URL/command field
- `command_args: Mapped[str | None]` — NPX/UVX extra args
- `headers_encrypted: Mapped[str | None]` — Fernet JSON blob
- `env_vars_encrypted: Mapped[str | None]` — Fernet JSON blob
- `is_enabled: Mapped[bool]` — default `True`
- `last_status: Mapped[McpStatus | None]` — replaces String(16)

### Status Lifecycle

```
[New server] → ENABLED (is_enabled=True, poller sets health)
     │
     ├─ Poller: reachable + healthy → stays ENABLED
     ├─ Poller: reachable + error response → UNHEALTHY
     ├─ Poller: connection failed/timeout → UNREACHABLE
     ├─ Validator: invalid config → CONFIG_ERROR
     └─ Admin action: disable → DISABLED (is_enabled=False, poller skips)
              └─ Admin action: re-enable → ENABLED (is_enabled=True, poller resumes)
```

---

## Phase 1: API Contracts

### Extended / New Endpoints

#### `POST /api/v1/workspaces/{workspace_id}/mcp-servers`
**Extended** — add new fields to request body.

**Request** `WorkspaceMcpServerCreate` (extended):
```json
{
  "display_name": "my-remote-server",
  "server_type": "remote",
  "url_or_command": "https://mcp.example.com/sse",
  "transport": "sse",
  "auth_type": "bearer",
  "auth_token": "sk-...",
  "headers": { "X-Custom": "value" },
  "env_vars": { "API_KEY": "abc123" },
  "command_args": "--directory /path"
}
```

**Response** `WorkspaceMcpServerResponse` (extended):
```json
{
  "id": "uuid",
  "workspace_id": "uuid",
  "display_name": "my-remote-server",
  "server_type": "remote",
  "url_or_command": "https://mcp.example.com/sse",
  "transport": "sse",
  "auth_type": "bearer",
  "has_auth_secret": true,
  "has_headers_secret": false,
  "has_env_secret": false,
  "command_args": null,
  "is_enabled": true,
  "last_status": "enabled",
  "last_status_checked_at": "2026-03-19T10:00:00Z",
  "created_at": "2026-03-19T09:00:00Z"
}
```
> Note: `auth_token`, `headers`, `env_vars` values are **never returned** — only boolean presence flags.

---

#### `GET /api/v1/workspaces/{workspace_id}/mcp-servers`
**Extended** — add query params for filtering.

**Query params**:
- `server_type`: `remote | npx | uvx | all` (default `all`)
- `status`: `enabled | disabled | unhealthy | unreachable | config_error | all` (default `all`)
- `search`: substring match on `display_name` or `url_or_command`

**Response**: `WorkspaceMcpServerListResponse { items: [...], total: int }`

---

#### `PATCH /api/v1/workspaces/{workspace_id}/mcp-servers/{server_id}` *(NEW)*
Update server fields (partial update). Same field shape as `POST` minus `display_name` uniqueness check.

---

#### `POST /api/v1/workspaces/{workspace_id}/mcp-servers/{server_id}/enable` *(NEW)*
Set `is_enabled=True`, clear `DISABLED` status, resume polling.
**Response**: `204 No Content`

---

#### `POST /api/v1/workspaces/{workspace_id}/mcp-servers/{server_id}/disable` *(NEW)*
Set `is_enabled=False`, set `last_status='disabled'`.
**Response**: `204 No Content`

---

#### `POST /api/v1/workspaces/{workspace_id}/mcp-servers/{server_id}/test` *(NEW)*
On-demand connection test with 10-second timeout.
**Response**:
```json
{
  "server_id": "uuid",
  "status": "enabled | unreachable | unhealthy | config_error",
  "latency_ms": 142,
  "checked_at": "2026-03-19T10:00:00Z",
  "error_detail": null
}
```

---

#### `POST /api/v1/workspaces/{workspace_id}/mcp-servers/import` *(NEW)*
Bulk import from JSON config.

**Request**:
```json
{
  "config_json": "{ \"mcpServers\": { ... } }"
}
```

**Response**:
```json
{
  "imported": [
    { "name": "remote-server", "id": "uuid" }
  ],
  "skipped": [
    { "name": "existing-server", "reason": "name_conflict" }
  ],
  "errors": [
    { "name": "bad-server", "reason": "invalid_url" }
  ]
}
```

---

### Background Poller (pg_cron)

**SQL migration** (`025_mcp_health_poller`):

```sql
-- Polling function called by pg_cron
CREATE OR REPLACE FUNCTION poll_mcp_server_health()
RETURNS void LANGUAGE plpgsql AS $$
BEGIN
  -- Updates last_status for all enabled servers via HTTP extension or mark for
  -- async probe via pgmq. Implementation detail resolved in tasks.
  -- Status enum: enabled / unhealthy / unreachable / config_error
  UPDATE workspace_mcp_servers
    SET last_status = 'unreachable',
        last_status_checked_at = NOW()
  WHERE is_enabled = TRUE
    AND is_deleted = FALSE
    AND last_status_checked_at < NOW() - INTERVAL '60 seconds';
END;
$$;

-- Schedule every 60 seconds
SELECT cron.schedule('mcp-health-poll', '* * * * *', 'SELECT poll_mcp_server_health()');
```

> **Note**: pg_cron fires once per minute (minimum interval). The actual HTTP probe is dispatched via pgmq to the backend's async worker, which performs the real connectivity check and writes the result back. This keeps the SQL function lightweight.

---

## Phase 1: Frontend Design

### Store Extension (`MCPServersStore.ts`)

**Updated types**:
```typescript
export type McpServerType = 'remote' | 'npx' | 'uvx';
export type McpTransport = 'sse' | 'stdio' | 'streamable_http';
export type McpStatus = 'enabled' | 'disabled' | 'unhealthy' | 'unreachable' | 'config_error';

export interface MCPServer {
  id: string;
  workspace_id: string;
  display_name: string;
  server_type: McpServerType;
  url_or_command: string;
  transport: McpTransport;
  auth_type: 'bearer' | 'oauth2';
  has_auth_secret: boolean;
  has_headers_secret: boolean;
  has_env_secret: boolean;
  command_args: string | null;
  is_enabled: boolean;
  last_status: McpStatus | null;
  last_status_checked_at: string | null;
  created_at: string;
}
```

**New store methods**:
- `enableServer(workspaceId, serverId)` → `PATCH .../enable`
- `disableServer(workspaceId, serverId)` → `PATCH .../disable`
- `updateServer(workspaceId, serverId, data)` → `PATCH .../`
- `testConnection(workspaceId, serverId)` → `POST .../test`
- `importServers(workspaceId, configJson)` → `POST .../import`
- `filterBy(type?, status?, search?)` — computed observable for table filtering

---

### Page Architecture

```
mcp-servers-settings-page.tsx       (observer, orchestrates page)
├── mcp-servers-table.tsx            (pure table, receives rows)
│   ├── mcp-status-badge.tsx         (5-state visual indicator)
│   └── mcp-server-row-actions.tsx   (edit, test, enable/disable, delete)
└── mcp-server-dialog.tsx            (modal: 2 tabs)
    ├── import-json-tab.tsx          (JSON editor + preview)
    └── form-config-tab.tsx          (guided form)
```

### Status Badge Visual Spec

| Status | Dot colour | Label | Icon |
|--------|-----------|-------|------|
| `enabled` | `#22c55e` (green) | Enabled | circle |
| `disabled` | `#6b7280` (grey) | Disabled | circle |
| `unhealthy` | `#f59e0b` (amber) | Unhealthy | triangle-alert |
| `unreachable` | `#ef4444` (red) | Unreachable | circle-x |
| `config_error` | `#ef4444` (red) | Config Error | alert-triangle |

---

## Implementation Phases

### Phase A — Backend: Model & Migration
1. Extend `McpAuthType` → add `McpServerType`, `McpTransport`, `McpStatus` enums to `workspace_mcp_server.py`
2. Add new columns to `WorkspaceMcpServer` model
3. Write Alembic migration `025_mcp_settings_redevelopment.py` with backfill
4. Extend `WorkspaceMcpServerRepository`: `get_filtered`, `update_fields`, `set_enabled`
5. Update existing `get_active_by_workspace` to filter `is_enabled=True OR include_disabled` based on caller

### Phase B — Backend: New Application Services
1. `ImportMcpServersService` — parses JSON, validates, deduplicates, bulk creates
2. `TestMcpConnectionService` — 10s probe for remote; subprocess healthcheck for NPX/UVX; returns `McpTestResult`
3. `EncryptedKVService` — wrap/unwrap `headers_encrypted` / `env_vars_encrypted` JSON blobs with Fernet

### Phase C — Backend: API Router Updates
1. Extend `_mcp_server_schemas.py`: new request/response shapes, SSRF validation for NPX/UVX command sanitization (no shell metacharacters)
2. Extend `workspace_mcp_servers.py`: `PATCH` (update), `POST .../enable`, `POST .../disable`, `POST .../test`, `POST .../import`
3. Update existing `GET` to support `server_type`, `status`, `search` query params
4. Write/extend tests (`tests/api/test_workspace_mcp_servers.py`)

### Phase D — Backend: Background Poller
1. Add pgmq queue `mcp_health_probe` to existing queue config
2. Add pg_cron migration to schedule `poll_mcp_server_health()` at 1-minute intervals
3. Add `MCPHealthWorker` (async worker in `infrastructure/workers/`) that drains queue and performs probes
4. Wire worker into app startup (`main.py` lifespan)

### Phase E — Frontend: Store & API Client
1. Extend `MCPServerRegisterRequest` → `MCPServerUpsertRequest` with all new fields
2. Update `MCPServer` interface with new type/transport/status fields
3. Add new methods to `MCPServersStore`
4. Extend `mcp-servers` API client (`services/api/mcp-servers.ts`)

### Phase F — Frontend: Components
1. `mcp-status-badge.tsx` — 5-state visual badge
2. `mcp-server-row-actions.tsx` — dropdown: Edit / Test Connection / Enable / Disable / Delete
3. `mcp-servers-table.tsx` — data table with filter bar (type + status dropdowns + search input), sort, footer count
4. `import-json-tab.tsx` — textarea + file upload + real-time parse + detected servers preview
5. `form-config-tab.tsx` — controlled form with conditional fields (server type drives visible sections)
6. `mcp-server-dialog.tsx` — tabbed modal (Import JSON / Form Config), Validate + primary action footer

### Phase G — Frontend: Page Integration
1. Replace `mcp-servers-settings-page.tsx` entirely — new full-width table layout
2. Background polling: `useEffect` with `setInterval` every 30s refreshes `loadServers()` (client-side complement to server-side pg_cron)
3. Add route handler for the new page at existing `app/(workspace)/[workspaceSlug]/settings/mcp-servers/page.tsx`

---

## Phase 16: Agent MCP Integration — Load & Verify

**Goal**: Confirm that workspace MCP configs are loaded into the agent on every chat request, and that the agent can successfully invoke tools from a registered server.

### Context

`_load_remote_mcp_servers()` (in `pilotspace_stream_utils.py`) and `_build_server_config()` were implemented as part of Phase 14 (T079). The agent calls them at lines ~550–552 of `pilotspace_agent.py`:

```python
remote_servers = await _load_remote_mcp_servers(context.workspace_id, db_session)
mcp_servers, ref_map = build_mcp_servers(tool_event_queue, tool_context, input_data)
mcp_servers.update(remote_servers)
```

The existing stub tests in `tests/ai/agents/test_remote_mcp_loading.py` still carry `@pytest.mark.xfail` from before the implementation shipped. This phase removes those markers, extends coverage, and adds an end-to-end verification path.

### What needs to be done

| Step | Work |
|------|------|
| Remove xfail markers | The three stubs in `test_remote_mcp_loading.py` now have a real implementation. Remove `xfail` and make them pass |
| Add NPX/UVX unit tests | Add `_build_server_config` unit tests for `npx`/`uvx` server types: correct `command`, `args`, `env` injection; env decryption failure → server skipped |
| Add disabled-server test | Assert `get_active_by_workspace(enabled_only=True)` excludes `is_enabled=False` servers |
| Add `_build_server_config` unit tests | Test all four config branches: remote+sse, remote+streamable_http, npx+stdio, uvx+stdio; also test headers_json priority over headers_encrypted |
| Integration smoke test | Using a mock MCP stdio server (e.g. `echo` subprocess), confirm that when a WorkspaceMcpServer row exists, `_load_remote_mcp_servers` produces a config that can be passed to the SDK without error |

### Architecture — no changes needed

The loading path is complete. This phase is **test and verification only**:

```
PilotSpaceAgent.stream()
  └─ _load_remote_mcp_servers(workspace_id, db_session)   [already wired]
       └─ repo.get_active_by_workspace(enabled_only=True) [already wired]
       └─ _build_server_config(server, decrypt_fn)        [already wired]
            ├─ remote+sse    → McpSSEServerConfig
            ├─ remote+http   → McpHttpServerConfig
            └─ npx/uvx+stdio → McpStdioServerConfig
```

### Config key naming convention

Workspace MCP servers are keyed as `WORKSPACE_{NORMALIZED_NAME}` in the `mcp_servers` dict passed to the SDK, where `NORMALIZED_NAME = re.sub(r"[^A-Z0-9]", "_", display_name.upper())` (e.g. `display_name="my-context7"` → `WORKSPACE_MY_CONTEXT7`). This avoids collisions with the 8 built-in servers (note, issue, project, etc.) which use fixed string names, and produces human-readable, env-var-style identifiers.

---

---

## Risk & Mitigations

| Risk | Mitigation |
|------|-----------|
| Alembic migration on existing `last_status` column (String→Enum) | Add `USING` cast in migration; test with `alembic upgrade --sql` before applying |
| NPX/UVX command injection | Validate `url_or_command` against a strict allowlist regex (no `;`, `&&`, `|`, `$`, backticks); reject at schema layer |
| Background poller starving event loop | pg_cron dispatches to pgmq; async worker processes off the main request path |
| Credential masking regression | CI test asserts API response never contains raw `auth_token`, `headers`, or `env_vars` values |
| 700-line file limit | `workspace_mcp_servers.py` currently ~400 lines; split import and test routes to separate files if needed |

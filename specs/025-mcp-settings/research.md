# Research: MCP Settings Redevelopment

**Feature**: MCP Settings Redevelopment
**Branch**: `25-mcp-settings`
**Date**: 2026-03-19

---

## Existing Codebase Baseline

| Area | Current State | Gap |
|------|--------------|-----|
| `WorkspaceMcpServer` model | Supports `remote` servers only; `url` VARCHAR(512); `last_status` String('connected'\|'failed'\|'unknown') | Missing `server_type`, `transport`, `is_enabled`, NPX/UVX fields, status enum |
| `workspace_mcp_servers.py` router | POST (register), GET (list), GET (status probe), DELETE (soft-delete), GET (oauth-url), GET (oauth-callback) | Missing PATCH (update), enable/disable, bulk import, on-demand test with 10s timeout |
| `MCPServersStore.ts` | Supports `bearer`/`oauth2` remote servers only | Missing new types, filtering, enable/disable, import methods |
| UI (`mcp-servers-settings-page.tsx`) | Simple vertical card list, collapsible form | No table, no filter bar, no dialog tabs, no status enum |
| Background polling | On-demand only (`GET .../status` probe, 5s timeout) | No scheduled poller; 5s → 10s timeout upgrade needed |

---

## Decision Log

### D-01: NPX/UVX Command Storage

**Decision**: Store NPX/UVX launch commands in the existing `url` column (renamed `url_or_command`) as a single string (e.g., `npx @modelcontextprotocol/server-filesystem`). Keep `url` as an alias for backward compatibility with the AI agent hot-loader.

**Rationale**: The field semantics are identical for the settings layer — both remote URLs and local commands are a single string identifying the server source. Avoids a schema split that would require updating the agent hot-loader code.

**Alternatives considered**:
- Separate `command` column alongside `url` → rejected (agent hot-loader would need dual-column logic)
- JSONB `connection_config` blob → rejected (overkill; each type only has 1-2 unique fields)

---

### D-02: SSRF / Command Injection Boundaries

**Decision**: Apply distinct validation per `server_type`:
- `remote`: Existing SSRF validation (HTTPS required, private IP blocklist)
- `npx` / `uvx`: Validate `url_or_command` starts with `npx ` or `uvx ` respectively; reject shell metacharacters (`; & | $ \` ( ) { } < >`)

**Rationale**: NPX/UVX run server-side, so SSRF IP blocklist is irrelevant. The real risk is command injection. Allowlist prefix + metacharacter denylist provides defense-in-depth.

**Alternatives considered**:
- Full shell command sanitization library → rejected (adds dependency; our validation surface is narrow)
- Run NPX/UVX in a sandbox → deferred (platform-level concern; out of scope for this spec)

---

### D-03: Status Enum Upgrade Strategy

**Decision**: Replace `last_status` `VARCHAR(16)` with a PostgreSQL native `mcp_status` enum type. Map existing values in migration: `'connected' → 'enabled'`, `'failed' → 'unreachable'`, `'unknown' → NULL`.

**Rationale**: Native enums provide DB-level constraint enforcement and make invalid states impossible to store. The migration `USING` cast is safe and reversible.

**Alternatives considered**:
- Keep as VARCHAR, validate in Python only → rejected (no DB constraint; incorrect values could slip through)
- New column alongside old → rejected (more complex migration; two sources of truth)

---

### D-04: Background Polling Architecture

**Decision**: pg_cron fires every 60 seconds → enqueues a probe message per enabled server to pgmq queue `mcp_health_probe` → async Python worker (`MCPHealthWorker`) drains queue, performs real HTTP/subprocess probe (10s timeout), writes result back to DB.

**Rationale**: Keeps SQL function lightweight (no HTTP in PL/pgSQL). Aligns with existing pgmq usage pattern in the codebase. Async worker processes probes concurrently without blocking the API event loop.

**Alternatives considered**:
- HTTP extension in PL/pgSQL → rejected (not available in Supabase managed; operational complexity)
- FastAPI background task triggered by client refresh → rejected (no server-side polling; stale data between refreshes)
- APScheduler in FastAPI → rejected (doesn't survive restart without state; pgmq + pg_cron is more robust)

---

### D-05: Credential Masking Pattern

**Decision**: API responses include boolean flags (`has_auth_secret`, `has_headers_secret`, `has_env_secret`) instead of any credential value. On edit, the frontend renders `••••••••` for fields where the flag is `true`. To change a secret, the admin retypes the value and the API replaces it. Clearing is done by submitting an empty string.

**Rationale**: Spec Q1 clarification; matches industry standard (Stripe, Vercel). Prevents plaintext transmission of secrets over the wire. Aligns with existing pattern (current code never returns `auth_token_encrypted`).

**Alternatives considered**:
- Return encrypted blob to client, decrypt client-side → rejected (key management complexity; worse security posture)
- "Reveal" button that fetches plaintext via separate endpoint → rejected (spec explicitly excluded this)

---

### D-06: Bulk Import Parser

**Decision**: Backend `ImportMcpServersService` handles JSON parsing, format detection (Claude/Cursor/VS Code), deduplication by `display_name` within the workspace, and bulk create. Returns three lists: `imported`, `skipped` (name conflict), `errors` (invalid config).

**Rationale**: Server-side parsing is more secure (avoids trusting client-parsed data) and enables accurate duplicate checking against the real DB state.

**Alternatives considered**:
- Client-side parse → submit only valid entries → rejected (client can't know server-side name conflicts without a separate lookup round-trip)
- Validate-then-confirm two-step flow → rejected (adds latency; spec FR-03-8 implies single-step import)

---

---

### D-08: Agent MCP Config Loading — Integration Point

**Decision**: `_load_remote_mcp_servers()` in `pilotspace_stream_utils.py` is the definitive integration point. It is called on every chat request in `pilotspace_agent.py` (lines ~550–552), fetches all `is_enabled=True` + `is_deleted=False` servers via `WorkspaceMcpServerRepository.get_active_by_workspace(enabled_only=True)`, and merges resulting configs into the SDK's `mcp_servers` dict under `WORKSPACE_{NORMALIZED_NAME}` keys, where `NORMALIZED_NAME = re.sub(r"[^A-Z0-9]", "_", display_name.upper())`.

Config type mapping:
- `remote + sse` → `{"type": "sse", "url": ..., "headers": {...}}`
- `remote + streamable_http` → `{"type": "http", "url": ..., "headers": {...}}`
- `npx/uvx + stdio` → `{"type": "stdio", "command": ..., "args": [...], "env": {...}}`

**Rationale**: Single async call before `build_mcp_servers()` keeps the loading path clean. Errors are swallowed per-server so one broken server never blocks the entire session.

**Status**: Implementation complete (T079). Tests need `xfail` removal (Phase 16, T089–T094).


**Decision**: `mcp-servers-settings-page.tsx` uses `setInterval(30_000)` to call `mcpStore.loadServers()` while the page is mounted. Combined with server-side pg_cron (60s), status is fresh within 60s as required by spec.

**Rationale**: Client-side polling complements pg_cron: even if the backend poller hasn't fired, the frontend refresh picks up any status changes written by other means (manual test, enable/disable).

**Alternatives considered**:
- Supabase Realtime subscription → deferred (real-time push is more elegant but adds subscription management complexity; polling is sufficient for spec's 60s accuracy requirement)

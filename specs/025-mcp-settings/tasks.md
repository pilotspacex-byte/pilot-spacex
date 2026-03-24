# Tasks: MCP Settings Redevelopment

**Feature**: MCP Settings Redevelopment
**Branch**: `25-mcp-settings`
**Plan**: `specs/025-mcp-settings/plan.md`
**Spec**: `specs/025-mcp-settings/spec.md`
**Created**: 2026-03-19

---

## Summary

| Phase | Stories Covered | Task Count |
|-------|----------------|------------|
| 1: Setup & Migration | — | 5 |
| 2: Foundational Backend | — | 8 |
| 3: US1 — Server List View | Scenario 1 | 7 |
| 4: US2 — Add via Form Config | Scenarios 3, 4 | 9 |
| 5: US3 — Bulk JSON Import | Scenarios 2, 7 | 7 |
| 6: US4 — Connection Test | Scenario 5 | 5 |
| 7: US5 — Enable / Disable | FR-07 | 5 |
| 8: US6 — Delete Server | Scenario 6 | 3 |
| 9: Background Poller | FR-01-3 (auto refresh) | 5 |
| 10: Polish & Cross-cutting | — | 5 |
| 11: US7 — None Auth Option | — | 5 |
| 12: Bug Fixes | — | 4 |
| 13: Bug Fixes — NPX Create | — | 3 |
| 14: Form UX Redesign + SDK Test | — | 10 |
| 15: Header/Env Visibility Fixes | — | 7 |
| 16: Agent MCP Integration — Load & Verify | Scenario 8, FR-08 | 6 |
| 17: Type Annotation Cleanup | — | 4 |
| 18: MCP Server Key Naming Convention | FR-08-7 | 3 |
| **Total** | | **101** |

---

## Phase 1: Setup & Migration

> Alembic schema migration and Python model extension. Must complete before any backend work.

- [X] T001 Add `McpServerType`, `McpTransport`, `McpStatus` StrEnum classes to `backend/src/pilot_space/infrastructure/database/models/workspace_mcp_server.py` alongside existing `McpAuthType`
- [X] T002 Add new mapped columns to `WorkspaceMcpServer` model in `backend/src/pilot_space/infrastructure/database/models/workspace_mcp_server.py`: `server_type`, `transport`, `url_or_command`, `command_args`, `headers_encrypted`, `env_vars_encrypted`, `is_enabled`, replace `last_status` String → `McpStatus` enum
- [X] T003 Write Alembic migration `backend/alembic/versions/025_mcp_settings_redevelopment.py`: add new columns with `server_type='remote'`, `transport='sse'`, `is_enabled=TRUE` defaults; backfill `url_or_command = url`; cast `last_status` VARCHAR → `mcp_status` enum with `'connected'→'enabled'`, `'failed'→'unreachable'`, `'unknown'→NULL`
- [ ] T004 Verify migration: run `cd backend && alembic heads` (single head), `alembic upgrade head`, `alembic check` with `TEST_DATABASE_URL` pointing to PostgreSQL; confirm no data loss on existing rows
- [X] T005 [P] Update `__all__` exports in `backend/src/pilot_space/infrastructure/database/models/workspace_mcp_server.py` to include all new enum classes; update `backend/src/pilot_space/infrastructure/database/models/__init__.py` if needed

---

## Phase 2: Foundational Backend

> Core repository extensions and application services that all user story phases depend on.

- [X] T006 Extend `WorkspaceMcpServerRepository` in `backend/src/pilot_space/infrastructure/database/repositories/workspace_mcp_server_repository.py`: add `get_filtered(workspace_id, server_type, status, search)` query with optional filters; add `update_fields(server, **kwargs)` partial update; add `set_enabled(server, enabled: bool)`
- [X] T007 [P] Create `EncryptedKVService` in `backend/src/pilot_space/infrastructure/encryption_kv.py`: `encrypt_kv(data: dict[str,str]) -> str` (Fernet JSON blob) and `decrypt_kv(blob: str) -> dict[str,str]`; use existing `encrypt_api_key`/`decrypt_api_key` Fernet key
- [X] T008 [P] Extend `_mcp_server_schemas.py` in `backend/src/pilot_space/api/v1/routers/_mcp_server_schemas.py`: add `WorkspaceMcpServerCreate` new fields (`server_type`, `transport`, `url_or_command`, `headers`, `env_vars`, `command_args`); add `WorkspaceMcpServerUpdate` (partial, all fields optional); update `WorkspaceMcpServerResponse` to include new fields + boolean presence flags (`has_auth_secret`, `has_headers_secret`, `has_env_secret`) instead of raw secrets; add SSRF validator for NPX/UVX commands (allowlist prefix `npx `/`uvx `, shell metacharacter denylist)
- [X] T009 [P] Update `WorkspaceMcpServerResponse.model_validate` in `_mcp_server_schemas.py` to set `has_auth_secret = bool(server.auth_token_encrypted)`, `has_headers_secret = bool(server.headers_encrypted)`, `has_env_secret = bool(server.env_vars_encrypted)`; ensure raw encrypted fields are excluded from the response model
- [X] T010 Update existing `register_mcp_server` endpoint in `backend/src/pilot_space/api/v1/routers/workspace_mcp_servers.py`: accept new request fields; encrypt `headers` via `EncryptedKVService`; encrypt `env_vars`; sync `url` field from `url_or_command` for backward compat with AI agent hot-loader
- [X] T011 Update existing `list_mcp_servers` endpoint in `backend/src/pilot_space/api/v1/routers/workspace_mcp_servers.py`: accept `server_type`, `status`, `search` query params and pass to `get_filtered()`
- [X] T012 [P] Write backend unit tests for `EncryptedKVService` in `backend/tests/unit/test_encryption_kv.py`: round-trip encrypt→decrypt; empty dict; unicode values; large dict
- [X] T013 [P] Extend `backend/tests/api/test_workspace_mcp_servers.py`: update existing `POST` and `GET` tests to include new fields; add assertions that `auth_token`, `headers`, `env_vars` are never present in API responses

---

## Phase 3: US1 — Server List View

> **Goal**: Admin can open the MCP Settings page and see a filterable, sortable table of all servers with real-time status.
> **Independent test**: Navigate to `/{workspace}/settings/mcp-servers` → table renders with server rows, filter dropdowns, search, footer count.

- [X] T014 Update `MCPServer` TypeScript interface in `frontend/src/stores/ai/MCPServersStore.ts`: add `server_type: McpServerType`, `transport: McpTransport`, `last_status: McpStatus | null`, `is_enabled: boolean`, `has_auth_secret`, `has_headers_secret`, `has_env_secret`, `url_or_command`, `command_args`; export `McpServerType`, `McpTransport`, `McpStatus` type unions
- [X] T015 [P] [US1] Add `filterBy(type?, status?, search?)` computed observable to `MCPServersStore` in `frontend/src/stores/ai/MCPServersStore.ts`; update `mcp-servers` API service in `frontend/src/services/api/mcp-servers.ts` to pass `server_type`, `status`, `search` query params to `GET` endpoint
- [X] T016 [P] [US1] Create `frontend/src/features/settings/components/mcp-status-badge.tsx`: renders 5-state badge with dot colour and label per `McpStatus`; green `Enabled`, grey `Disabled`, amber `Unhealthy`, red `Unreachable`, red warning icon `Config Error`; pure component, no store dependency
- [X] T017 [US1] Create `frontend/src/features/settings/components/mcp-servers-table.tsx`: data table using shadcn `<Table>` with columns Server Name (icon + monospace name), Type badge, URL/Command, Transport, Status (`<McpStatusBadge>`), Actions; filter bar row with Type dropdown, Status dropdown, search input, Sort button; footer showing "Showing N of M servers"
- [X] T018 [US1] Redevelop `frontend/src/features/settings/pages/mcp-servers-settings-page.tsx` as MobX `observer`: load servers on mount with `mcpStore.loadServers(workspaceId)`; set up `useEffect` with `setInterval(30_000)` for background refresh while mounted; render page header (title + Refresh + New MCP buttons) + `<MCPServersTable>`; handle loading/error states
- [X] T019 [P] [US1] Write Vitest test `frontend/src/features/settings/components/__tests__/mcp-servers-table.test.tsx`: renders table with mocked servers; filter by type shows correct rows; status badge renders correct colour per status; footer count updates with filter
- [X] T020 [P] [US1] Write Vitest test `frontend/src/features/settings/pages/__tests__/mcp-servers-settings-page.test.tsx`: calls `loadServers` on mount; renders skeleton while loading; renders table when data available; sets up polling interval; clears interval on unmount

---

## Phase 4: US2 — Add / Edit Server via Form Config

> **Goal**: Admin can open "New MCP Server" dialog, fill out Form Configuration tab, and save a new or edited server.
> **Independent test**: Open dialog → Form Config tab → fill required fields → Save → server appears in table.

- [X] T021 [US2] Create `frontend/src/features/settings/components/form-config-tab.tsx`: controlled form with Server Name + Server Type (two-column row); Server URL/Command + Transport (two-column row with Transport defaulting to SSE/stdio by type); Headers section (dynamic key-value rows with Add Header + per-row trash icon, masked `••••••••` when `has_headers_secret=true` on edit); Env Vars section (same pattern, masked when `has_env_secret=true`); Command Arguments field (visible only for NPX/UVX type); all validation inline
- [X] T022 [US2] Create `frontend/src/features/settings/components/mcp-server-dialog.tsx`: modal 720px wide with title "Add New MCP Server" / "Edit MCP Server"; two tabs using shadcn `<Tabs>`: Import JSON (default on add) + Form Configuration; footer with Cancel + primary action; Test Connection ghost button in footer; pass `initialData` prop (optional — populates form for edit mode with masked secret fields)
- [X] T023 [US2] Add `updateServer(workspaceId, serverId, data)` method to `MCPServersStore` in `frontend/src/stores/ai/MCPServersStore.ts`; add corresponding `update(workspaceId, serverId, data)` method to `frontend/src/services/api/mcp-servers.ts` calling `PATCH /api/v1/workspaces/{workspace_id}/mcp-servers/{server_id}`
- [X] T024 [US2] Add `PATCH /{workspace_id}/mcp-servers/{server_id}` endpoint to `backend/src/pilot_space/api/v1/routers/workspace_mcp_servers.py`: accept `WorkspaceMcpServerUpdate` (all fields optional); for each secret field, skip update if omitted/empty (preserves existing encrypted value); re-encrypt if new value provided; sync `url` from `url_or_command`
- [X] T025 [US2] Wire edit action in `frontend/src/features/settings/components/mcp-server-row-actions.tsx` (new file): dropdown menu with Edit, Test Connection, Enable/Disable toggle (label changes based on `is_enabled`), Delete (with confirmation); on Edit click open `<MCPServerDialog>` with `initialData` populated from the server row
- [X] T026 [P] [US2] Write backend test in `backend/tests/api/test_workspace_mcp_servers.py`: `PATCH` updates only provided fields; existing secrets preserved when not included in patch; `url` synced from `url_or_command`; non-admin returns 404
- [X] T027 [P] [US2] Write Vitest test `frontend/src/features/settings/components/__tests__/form-config-tab.test.tsx`: required field validation; Transport auto-sets on type change; Command Arguments hidden for Remote, shown for NPX/UVX; secret fields show `••••••••` when `hasSecret=true`; submit fires `onSave` with correct payload
- [X] T028 [P] [US2] Write Vitest test `frontend/src/features/settings/components/__tests__/mcp-server-dialog.test.tsx`: opens to Import JSON tab by default (add mode); opens to Form Config tab in edit mode; Cancel closes dialog; Test Connection button calls `testConnection`
- [X] T029 [US2] Register `<MCPServerDialog>` in `mcp-servers-settings-page.tsx`: "New MCP" button opens dialog in add mode; row edit action opens in edit mode; on successful save reload servers and show toast

---

## Phase 5: US3 — Bulk JSON Import

> **Goal**: Admin can paste or upload a JSON config and import all detected servers in one action, with conflict skipping and error reporting.
> **Independent test**: Paste valid JSON with 3 servers → preview shows 3 cards → Import → 3 servers in table (or N imported + skipped summary).

- [X] T030 [US3] Create `ImportMcpServersService` in `backend/src/pilot_space/application/mcp/import_mcp_servers_service.py`: `parse_config_json(raw: str) -> list[ParsedMcpServer]` supporting Claude Desktop, Cursor, VS Code MCP `{ "mcpServers": {...} }` format; validate each entry (SSRF/command checks); `import_servers(workspace_id, parsed, session) -> ImportResult` checking existing `display_name` duplicates in workspace and bulk-creating non-conflicting entries; return `imported`, `skipped`, `errors` lists
- [X] T031 [US3] Add `POST /{workspace_id}/mcp-servers/import` endpoint to `backend/src/pilot_space/api/v1/routers/workspace_mcp_servers.py`: accept `{ "config_json": "..." }`; call `ImportMcpServersService`; return `ImportMcpServersResponse { imported: [...], skipped: [...], errors: [...] }`
- [X] T032 [US3] Create `frontend/src/features/settings/components/import-json-tab.tsx`: monospace `<textarea>` with skeleton JSON placeholder `{ "mcpServers": { ... } }`; Upload File ghost button (`<input type="file" accept=".json">`); info line "Supports Claude, Cursor, and VS Code MCP config formats"; real-time client-side JSON parse on change: on valid parse show Detected Servers preview (card per server with icon, name, URL/command, transport badge); show "Valid JSON — N server entries detected" with green check icon; on invalid JSON show inline error; "Import & Add Servers" button disabled until valid + ≥1 server detected
- [X] T033 [US3] Add `importServers(workspaceId, configJson)` method to `MCPServersStore` in `frontend/src/stores/ai/MCPServersStore.ts`; add `import(workspaceId, configJson)` to `frontend/src/services/api/mcp-servers.ts`; on success show toast with "N imported" and if skipped > 0 show inline summary of skipped names in dialog
- [X] T034 [US3] Wire Import JSON tab into `<MCPServerDialog>`: on "Import & Add Servers" call `mcpStore.importServers()`; on success reload server list and close dialog; show post-import summary if any servers were skipped
- [X] T035 [P] [US3] Write backend tests in `backend/tests/unit/application/test_import_mcp_servers_service.py`: parse Claude format; parse VS Code format; skip duplicate names; reject SSRF URL; reject shell metacharacter in command; return correct `imported`/`skipped`/`errors` split
- [X] T036 [P] [US3] Write Vitest test `frontend/src/features/settings/components/__tests__/import-json-tab.test.tsx`: valid JSON shows detected servers preview; invalid JSON shows error; Import button disabled on invalid JSON; Upload File populates textarea; valid JSON with 0 servers keeps Import button disabled

---

## Phase 6: US4 — Connection Test

> **Goal**: Admin can test a server's connectivity before saving, or from the table row actions, and receive success/failure feedback within 10 seconds.
> **Independent test**: Fill form with valid URL → click Test Connection → result appears within 10s.

- [X] T037 Create `TestMcpConnectionService` in `backend/src/pilot_space/application/mcp/test_mcp_connection_service.py`: for `remote` type — HTTP GET with 10s timeout using `httpx.AsyncClient`; inject decrypted auth headers; return `McpTestResult { status, latency_ms, error_detail }`; for `npx`/`uvx` — subprocess health check (`asyncio.create_subprocess_exec` with 10s timeout, check process starts without immediate error); map results to `McpStatus` enum
- [X] T038 Add `POST /{workspace_id}/mcp-servers/{server_id}/test` endpoint to `backend/src/pilot_space/api/v1/routers/workspace_mcp_servers.py`: load server; decrypt credentials via `EncryptedKVService`; call `TestMcpConnectionService`; persist `last_status` + `last_status_checked_at`; return `McpServerTestResponse { server_id, status, latency_ms, checked_at, error_detail }`
- [X] T039 Add `testConnection(workspaceId, serverId)` method to `MCPServersStore` and `frontend/src/services/api/mcp-servers.ts`; update server's `last_status` in store on response
- [X] T040 [P] Wire Test Connection button in `<FormConfigTab>` and `<MCPServerRowActions>`: show loading spinner during test; on success show inline `<McpStatusBadge>` + latency; on failure show inline error message with guidance text; timeout renders as "Unreachable — connection timed out after 10s"
- [X] T041 [P] Write backend tests in `backend/tests/api/test_workspace_mcp_servers.py`: test endpoint returns `enabled` status for reachable mock server; returns `unreachable` on timeout; returns `unhealthy` on 5xx response; latency_ms populated on success

---

## Phase 7: US5 — Enable / Disable Server

> **Goal**: Admin can disable a server without deleting it, and re-enable it later. Disabled servers are excluded from polling and MCP routing.
> **Independent test**: Disable server → status badge shows "Disabled" → server excluded from AI agent hot-load → re-enable → polling resumes.

- [X] T042 Add `POST /{workspace_id}/mcp-servers/{server_id}/enable` and `POST /{workspace_id}/mcp-servers/{server_id}/disable` endpoints to `backend/src/pilot_space/api/v1/routers/workspace_mcp_servers.py`: `enable` sets `is_enabled=True`, clears `disabled` status (sets `last_status=None`); `disable` sets `is_enabled=False`, sets `last_status='disabled'`; both return `204 No Content`
- [X] T043 Add `enableServer(workspaceId, serverId)` and `disableServer(workspaceId, serverId)` methods to `MCPServersStore` and corresponding API calls in `frontend/src/services/api/mcp-servers.ts`; update `is_enabled` + `last_status` on the matching server in store after response
- [X] T044 [P] Update AI agent hot-loader in `backend/src/pilot_space/ai/tools/mcp_server.py` (or `dependencies/ai.py`): filter out servers where `is_enabled=False` when loading MCP servers for a chat session
- [X] T045 [P] Wire enable/disable toggle in `<MCPServerRowActions>`: label is "Disable" when `is_enabled=true`, "Enable" when `is_enabled=false`; optimistic UI update in store; on error revert and show toast
- [X] T046 [P] Write backend tests: `disable` sets `last_status='disabled'` and `is_enabled=False`; `enable` clears status and sets `is_enabled=True`; disabled server not returned by AI hot-loader `get_active_by_workspace`

---

## Phase 8: US6 — Delete Server

> **Goal**: Admin can delete a server with a confirmation prompt; deleted servers are removed from the list immediately.
> **Independent test**: Click delete on a row → confirmation dialog appears → confirm → server removed from table.

- [X] T047 [US6] Update `<MCPServerRowActions>` in `frontend/src/features/settings/components/mcp-server-row-actions.tsx`: Delete action opens shadcn `<AlertDialog>` confirmation with server name in message body; on confirm call `mcpStore.removeServer()`; show loading state on confirm button; on success close dialog and show toast "Server removed"
- [X] T048 [P] [US6] Verify existing `DELETE` endpoint handles soft-delete correctly with new schema (no changes expected); add regression test asserting soft-deleted server not returned by `list_mcp_servers` filtered query
- [X] T049 [P] [US6] Write Vitest test for `<MCPServerRowActions>`: delete opens AlertDialog; cancel keeps server in list; confirm calls `onDelete` callback with correct server id

---

## Phase 9: Background Poller

> **Goal**: Server statuses update automatically within 60 seconds of a connectivity change without admin action.
> **Independent test**: Server goes unreachable → within 60s list shows "Unreachable" without manual refresh.

- [ ] T050 Create Alembic migration `backend/alembic/versions/025b_mcp_health_poller.py`: create `poll_mcp_server_health()` PL/pgSQL function that enqueues one pgmq message per enabled server to queue `mcp_health_probe`; schedule with `SELECT cron.schedule('mcp-health-poll', '* * * * *', 'SELECT poll_mcp_server_health()')`
- [ ] T051 Create `MCPHealthWorker` in `backend/src/pilot_space/infrastructure/workers/mcp_health_worker.py`: drain `mcp_health_probe` pgmq queue in a loop; for each message call `TestMcpConnectionService`; write result back to `workspace_mcp_servers` via repository; set `McpStatus.CONFIG_ERROR` if server has no `url_or_command`
- [ ] T052 Wire `MCPHealthWorker` into FastAPI app lifespan in `backend/src/pilot_space/main.py`: start worker as `asyncio.Task` on startup; cancel gracefully on shutdown
- [ ] T053 [P] Add `mcp_health_probe` queue to pgmq queue registration in existing infrastructure queue config (same location as other queues)
- [ ] T054 [P] Write unit tests for `MCPHealthWorker` in `backend/tests/unit/workers/test_mcp_health_worker.py`: mock pgmq drain; assert `TestMcpConnectionService` called per message; assert status written back; config_error set for missing url_or_command

---

## Phase 10: Polish & Cross-cutting

- [X] T055 [P] Keyboard accessibility: ensure `<MCPServerDialog>` traps focus on open, closes on Escape, and all interactive elements are keyboard-reachable; confirm against WCAG 2.2 AA tab order
- [X] T056 [P] Empty state: `mcp-servers-settings-page.tsx` shows a centred empty state with `ServerCog` icon and "No MCP servers configured yet. Click New MCP to add one." when `servers.length === 0` and not loading
- [ ] T057 [P] Run `make quality-gates-backend` (`pyright + ruff + pytest --cov`): fix any type errors introduced by new enums or nullable columns; confirm >80% coverage on all new files
- [X] T058 [P] Run `make quality-gates-frontend` (`eslint + tsc --noEmit + vitest`): fix any TypeScript errors in new components; confirm >80% coverage on new components
- [ ] T059 Update `specs/025-mcp-settings/checklists/requirements.md` to mark all items resolved; update feature `Status` in `spec.md` from `Draft` to `In Progress`

---

## Phase 11: US7 — None Auth Option

> **Goal**: Admin can select "None" as the authentication type when adding a new MCP server, for servers that require no authentication (e.g., local or trusted-network MCP endpoints).
> **Independent test**: Open "New MCP Server" dialog → Form Config tab → select "None" for Authentication → Bearer Token field is hidden → Save → server created with `auth_type=none`.

- [X] T060 [US7] Add `NONE = "none"` to `McpAuthType` StrEnum in `backend/src/pilot_space/infrastructure/database/models/workspace_mcp_server.py`; update `__all__` exports if needed
- [X] T061 [US7] Create Alembic migration `backend/alembic/versions/091_add_none_auth_type.py` (revises `090_mcp_settings_redevelopment`): `ALTER TYPE mcp_auth_type ADD VALUE 'none'`; downgrade is no-op (PostgreSQL enum values cannot be removed)
- [X] T062 [P] [US7] Update frontend types and form: widen `auth_type` union to `'none' | 'bearer' | 'oauth2'` in `MCPServer`, `MCPServerRegisterRequest`, `MCPServerUpdateRequest` interfaces in `frontend/src/stores/ai/MCPServersStore.ts`; in `FormConfigData` in `frontend/src/features/settings/components/form-config-tab.tsx` widen `authType` to `'none' | 'bearer' | 'oauth2'`; add "None" radio option to the Authentication section (rendered for `remote` type); hide Bearer Token input and OAuth2 fields when `authType === 'none'`; set default `authType` to `'none'` for new servers
- [X] T063 [P] [US7] Update tests: add Vitest case in `frontend/src/features/settings/components/__tests__/form-config-tab.test.tsx` verifying "None" radio renders, selecting "None" hides Bearer Token field, and submit payload has `auth_type: 'none'`; add backend test in `backend/tests/api/test_workspace_mcp_servers.py` verifying `POST` with `auth_type=none` succeeds and no auth token is stored
- [X] T064 [P] [US7] Update `AuthTypeBadge` in `frontend/src/features/settings/components/mcp-server-card.tsx` to handle `auth_type === 'none'` rendering label "None" instead of falling through to "OAuth2"

---

## Phase 12: Bug Fixes

> **Goal**: Fix two bugs — (1) tab state loss when switching between Import JSON and Form Configuration tabs in the "New MCP Server" dialog, and (2) backend 500 error on bulk import endpoint.
> **Independent test**: (1) Open "Add New MCP Server" → paste JSON in Import tab → switch to Form Config → switch back → JSON text is still there. (2) Paste valid MCP config JSON → click "Import & Add Servers" → servers are imported without 500 error.

- [X] T065 Fix tab state preservation in `frontend/src/features/settings/components/mcp-server-dialog.tsx`: add `forceMount` to both `<TabsContent>` elements and use CSS `hidden` class on inactive tab to prevent Radix Tabs from unmounting `ImportJsonTab` state when switching tabs
- [X] T066 [P] Add/update Vitest test in `frontend/src/features/settings/components/__tests__/mcp-server-dialog.test.tsx` verifying that tab switching preserves ImportJsonTab content (render dialog → type JSON → switch to form tab → switch back → JSON text persists)
- [X] T067 Fix backend import 500 error in `backend/src/pilot_space/api/v1/routers/workspace_mcp_servers.py`: remove `session=session` keyword argument from `ImportMcpServersService.import_servers()` call (line ~584-589) — the service method does not accept a `session` parameter
- [X] T068 [P] Fix missing `auth_type` field in `backend/src/pilot_space/application/services/mcp/import_mcp_servers_service.py`: add `auth_type=McpAuthType.NONE` to `WorkspaceMcpServer()` constructor (line ~284-296) and add `McpAuthType` to imports

---

## Phase 13: Bug Fixes — NPX Create

> **Goal**: Fix two bugs — (1) Frontend form sends raw package name for NPX/UVX servers without the required `npx `/`uvx ` prefix, causing backend validation error; (2) Error handler crashes when Pydantic validation errors contain non-serializable `ValueError` objects in `ctx` field.
> **Independent test**: (1) Select NPX type → enter `@upstash/context7-mcp` as Command → Save → server created successfully with `url_or_command='npx @upstash/context7-mcp'`. (2) Trigger a validation error → receive clean 422 JSON response instead of 500 crash.

- [X] T069 Fix frontend NPX/UVX prefix: in `frontend/src/features/settings/components/form-config-tab.tsx` `handleSubmit()`, prepend `'npx '` or `'uvx '` to `url_or_command` if the value doesn't already start with the server type prefix, for both create and update payloads
- [X] T070 [P] Fix error handler crash: in `backend/src/pilot_space/api/middleware/error_handler.py` `validation_exception_handler()`, sanitize Pydantic error dicts to ensure all values are JSON-serializable (convert `ValueError` objects in `ctx` to their string representation)
- [X] T071 [P] Update placeholder text in `frontend/src/features/settings/components/form-config-tab.tsx` for NPX/UVX Command field — change from `'npx @modelcontextprotocol/server'` to `'@modelcontextprotocol/server'` since the prefix is now auto-prepended

---

## Phase 14: Form UX Redesign + SDK-based Test Connection

> **Goal**: Simplify the form to 2 server types ("Remote Server" and "Command"), remove `ensureCommandPrefix()`, update Command field to accept the full executable (e.g. `npx`, `uvx`, `node`), hide Headers for Command type, update args placeholder, add env var binding tooltip, and implement backend test connection using `claude_agent_sdk` config types (`McpStdioServerConfig | McpSSEServerConfig | McpHttpServerConfig`).
> **Independent test**: (1) Select "Command" → enter `npx` as Command → enter `-y @modelcontextprotocol/server --api-key $API_KEY` as args → add env var `API_KEY=xxx` → Save → server created. (2) Click "Test Connection" on any server → backend builds correct SDK config → returns status.

### Frontend: Form UX

- [X] T072 Remove `ensureCommandPrefix()` helper from `frontend/src/features/settings/components/form-config-tab.tsx`; revert `handleSubmit()` to send `url_or_command` as-is for both create and update paths (user enters the full command like `npx`, `uvx`, etc.)
- [X] T073 Simplify Server Type select in `form-config-tab.tsx`: change from 3 options (`Remote MCP (SSE)`, `NPX`, `UVX`) to 2 options: `Remote Server` (value `remote`) and `Command` (value `npx`). When user selects "Command", set `transport` to `stdio`. Remove the separate `UVX` option — user types `uvx` directly in the Command field
- [X] T074 [P] Update Command field placeholder to `npx, uvx ...` and args placeholder to `-y @modelcontextprotocol/server --api-key $API_KEY` in `form-config-tab.tsx`
- [X] T075 [P] Hide Headers KV editor when `serverType !== 'remote'` in `form-config-tab.tsx` (Command-type servers don't use HTTP headers; they use env vars instead)
- [X] T076 [P] Add info tooltip (?) next to "Environment Variables" label in `form-config-tab.tsx` using `@/components/ui/tooltip` with `lucide-react` `HelpCircle` icon. Tooltip text: `"Define environment variables passed to the command process. Use $VAR_NAME in command arguments to reference them (e.g. --api-key $API_KEY)."`

### Backend: Validator + Test Connection

- [X] T077 Update backend validator `_validate_npx_uvx_command()` in `backend/src/pilot_space/api/v1/routers/_mcp_server_schemas.py`: relax the prefix check — for `server_type=npx` accept any non-empty command (the user enters the full executable e.g. `npx`, `uvx`, `node`); still enforce shell metacharacter denylist on `url_or_command`
- [X] T078 Create `backend/src/pilot_space/application/services/mcp/test_mcp_connection_service.py` with `TestMcpConnectionService.test(server: WorkspaceMcpServer)` that builds the correct `claude_agent_sdk` config type based on `server.server_type` and `server.transport`: `McpSSEServerConfig` for `remote+sse`, `McpHttpServerConfig` for `remote+streamable_http`, `McpStdioServerConfig` for `npx/uvx+stdio`. Decrypts `auth_token_encrypted`, `headers_encrypted`, `env_vars_encrypted` as needed. Returns `TestResult(status, latency_ms, checked_at, error_detail)`
- [X] T079 [P] Update `_load_remote_mcp_servers()` in `backend/src/pilot_space/ai/agents/pilotspace_stream_utils.py` to handle all server types, not just remote SSE: build `McpStdioServerConfig` for NPX/UVX (with `command`, `args`, `env`) and `McpHttpServerConfig` for `streamable_http` transport. Rename function to `_load_workspace_mcp_servers()`
- [X] T081 [P] Update frontend tests in `frontend/src/features/settings/components/__tests__/form-config-tab.test.tsx`: update tests for 2-type select ("Remote Server"/"Command"), verify Headers hidden for Command type, verify args placeholder text

---

## Phase 15: Header/Env Visibility Fixes

> **Goal**: (1) Add tooltip to Headers section. (2) Store headers as plaintext JSON instead of encrypted — return full key-value pairs in API response so they are visible when editing. (3) Return env var keys (but not values) in API response so edit form shows `API_KEY = ●●●●●●●●` instead of generic mask.
> **Independent test**: (1) Edit a Remote server with existing headers → headers show key+value pre-filled. (2) Edit a server with existing env vars → env var keys show with masked values. (3) Headers section has tooltip icon.

### Backend: API Response Changes

- [X] T082 Add `headers_json` (plaintext `Text` column) to `WorkspaceMcpServer` model in `backend/src/pilot_space/infrastructure/database/models/workspace_mcp_server.py`. Store headers as plain JSON instead of encrypted. Keep `headers_encrypted` for backward compat but stop writing to it for new saves.
- [X] T083 Update `WorkspaceMcpServerResponse` in `backend/src/pilot_space/api/v1/routers/_mcp_server_schemas.py`: add `headers: dict[str, str] | None = None` (full key-value pairs) and `env_var_keys: list[str] | None = None` (keys only, no values). Update `from_orm_model()` to populate `headers` from `headers_json` (or decrypt `headers_encrypted` as fallback) and `env_var_keys` from decrypted `env_vars_encrypted`.
- [X] T084 Update `register_mcp_server()` and `update_mcp_server()` in `backend/src/pilot_space/api/v1/routers/workspace_mcp_servers.py`: store headers as plaintext JSON in `headers_json` column (stop encrypting headers). Keep env vars encrypted.

### Frontend: Form Visibility

- [X] T085 Update `MCPServer` interface in `frontend/src/stores/ai/MCPServersStore.ts`: add `headers?: Record<string, string> | null` and `env_var_keys?: string[] | null` fields.
- [X] T086 Update `buildInitialState()` in `frontend/src/features/settings/components/form-config-tab.tsx`: when editing, populate `headers` from `initialData.headers` (full key-value pairs) and `envVars` from `initialData.env_var_keys` (keys with empty string values as masked placeholders). Update KVEditor for env vars to show `type="text"` for keys and `type="password"` for values.
- [X] T087 [P] Add tooltip (?) next to "Headers" label in `form-config-tab.tsx` using same pattern as env vars tooltip. Tooltip text: `"Custom HTTP headers sent with every request to the remote MCP server. Use for API keys, auth tokens, or custom routing headers."`
- [X] T088 [P] Update `handleSubmit()` in `form-config-tab.tsx`: for env vars, only send entries where value is non-empty (skip entries where user didn't change the masked placeholder). This prevents overwriting existing encrypted values with empty strings.

---

## Phase 16: Agent MCP Integration — Load & Verify

> **Goal**: Confirm the workspace MCP config loading path (`_load_remote_mcp_servers` + `_build_server_config`) is fully tested and verified end-to-end. All T079 implementation is already shipped; this phase removes `xfail` stubs, extends coverage, and adds an integration smoke-test.
> **Independent test**: Register an enabled WorkspaceMcpServer row → agent loads it → `mcp_servers` dict contains that server's config → agent can call tools on it.

- [X] T089 Remove `@pytest.mark.xfail` from all three stubs in `backend/tests/ai/agents/test_remote_mcp_loading.py` and make them pass: update fixture usage to match current `WorkspaceMcpServer` model fields (`url_or_command`, `server_type`, `is_enabled`); use `db_session_committed` where cross-session visibility is required
- [X] T090 [P] Add `_build_server_config` unit tests in `backend/tests/ai/agents/test_remote_mcp_loading.py` for all four config branches: (a) `remote+sse` → `{"type":"sse","url":...,"headers":{...}}`; (b) `remote+streamable_http` → `{"type":"http","url":...}`; (c) `npx+stdio` → `{"type":"stdio","command":"npx","args":[...],"env":{...}}`; (d) `uvx+stdio` → same pattern with `uvx`; confirm `headers_json` takes priority over `headers_encrypted` for remote servers
- [X] T091 [P] Add unit test: `_build_server_config` returns `None` for a remote server whose `auth_token_encrypted` fails decryption (corrupt ciphertext) — the `_load_remote_mcp_servers` wrapper silently skips it; add second test: NPX server with corrupt `env_vars_encrypted` is also skipped
- [X] T092 [P] Add repository unit test in `backend/tests/ai/agents/test_remote_mcp_loading.py`: `get_active_by_workspace(enabled_only=True)` excludes servers where `is_enabled=False`; a subsequently re-enabled server appears in the next call
- [X] T093 [P] Add integration smoke-test in `backend/tests/ai/agents/test_remote_mcp_loading.py`: create a WorkspaceMcpServer row for an NPX server (e.g. `command="echo"`, `args=["-n","ok"]`); call `_load_remote_mcp_servers(workspace.id, db_session)`; assert result contains key `npx_{server.id}` with `type=="stdio"`; assert the config dict can be JSON-serialised (no non-serialisable types) — validates that the config is SDK-ready
- [X] T094 [P] Update `backend/tests/ai/agents/test_remote_mcp_loading.py` docstring header: remove "implementation pending" note; document that `_load_remote_mcp_servers` is active in production (`pilotspace_agent.py` lines ~550–552) and these tests are the definitive contract tests for FR-08

---

## Phase 17: Type Annotation Cleanup

> **Goal**: Remove all `# type: ignore` and `# pyright: ignore` suppressors from the agent MCP loading path without introducing any new errors. Three root causes: (1) `_load_remote_mcp_servers` is a private name crossing module boundaries causing `reportPrivateUsage`; (2) pyright sees it as unused due to the suppressor hiding the cross-module usage causing `reportUnusedFunction`; (3) `_build_server_config` builds SDK TypedDicts via dict-literal syntax which pyright cannot verify as `McpServerConfig` without the concrete subtype constructors.
> **Independent test**: `uv run pyright src/pilot_space/ai/agents/pilotspace_stream_utils.py src/pilot_space/ai/agents/pilotspace_agent.py` reports 0 errors with zero `# type: ignore` / `# pyright: ignore` suppressors in these two files for the targeted lines.

- [X] T095 Rename `_load_remote_mcp_servers` → `load_workspace_mcp_servers` in `backend/src/pilot_space/ai/agents/pilotspace_stream_utils.py` (remove leading underscore to make it a public module export); update the function definition line to remove `# pyright: ignore[reportUnusedFunction]`; update the import in `backend/src/pilot_space/ai/agents/pilotspace_agent.py` from `_load_remote_mcp_servers,  # type: ignore[reportPrivateUsage]` to plain `load_workspace_mcp_servers,`; update the call site at line ~550 accordingly; update all references in `backend/tests/ai/agents/test_remote_mcp_loading.py` to use the new public name
- [X] T096 [P] Retype `_build_server_config` in `backend/src/pilot_space/ai/agents/pilotspace_stream_utils.py`: change parameter `decrypt_fn: object` to `decrypt_fn: Callable[[str], str]` (import `Callable` from `collections.abc`); change parameter `server: object` to `server: WorkspaceMcpServer` with the import moved from the function body to the top of the file (use `TYPE_CHECKING` guard if needed to avoid circular import); remove the `assert isinstance(server, WorkspaceMcpServer)` runtime check and the `_decrypt = decrypt_fn  # type: ignore[assignment]` cast line; call `decrypt_fn(...)` directly
- [X] T097 [P] Replace dict-literal TypedDict construction in `_build_server_config` with typed constructors: change `config: McpServerConfig = {  # type: ignore[typeddict-item]` and subsequent `config["headers"] = headers  # type: ignore[typeddict-unknown-key]` to `McpSSEServerConfig(type="sse", url=url, headers=headers)` / `McpHttpServerConfig(type="http", url=url, headers=headers)`; change `stdio_config: McpServerConfig = {  # type: ignore[typeddict-item]` and `stdio_config["args"] = ...  # type: ignore[typeddict-unknown-key]` / `stdio_config["env"] = ...  # type: ignore[typeddict-unknown-key]` to `McpStdioServerConfig(type="stdio", command=command, args=args, env=env)` built once with all optional fields; import `McpSSEServerConfig`, `McpHttpServerConfig`, `McpStdioServerConfig` from `claude_agent_sdk` at top of file alongside existing `McpServerConfig` import
- [X] T098 [P] After T095–T097: run `cd backend && uv run pyright src/pilot_space/ai/agents/pilotspace_stream_utils.py src/pilot_space/ai/agents/pilotspace_agent.py` and confirm 0 errors; run `uv run ruff check src/pilot_space/ai/agents/` to confirm 0 lint warnings; run `uv run pytest tests/ai/agents/ -q` to confirm all agent tests pass

---

## Phase 18: MCP Server Key Naming Convention

> **Goal**: Change the key used when registering workspace MCP servers in the agent's `mcp_servers` dict from `{server_type}_{server.id}` to `WORKSPACE_{normalized_name}` where `normalized_name = re.sub(r"[^A-Z0-9]", "_", server.display_name.upper())`. Non-alphanumeric characters (hyphens, spaces, dots) become `_`, making keys safe env-var-style identifiers collision-free with built-in server names.
> **Independent test**: `load_workspace_mcp_servers()` returns a dict whose keys match `WORKSPACE_{re.sub(r"[^A-Z0-9]", "_", display_name.upper())}` (e.g. `display_name="my-context7 server"` → key `WORKSPACE_MY_CONTEXT7_SERVER`); tests confirm the old `{server_type}_{id}` pattern no longer appears.

- [X] T099 Update `load_workspace_mcp_servers()` in `backend/src/pilot_space/ai/agents/pilotspace_stream_utils.py`: add `import re` at the top of the file if not already present; change the key assignment from `servers[f"{server.server_type.value}_{server.id}"] = config` to `servers["WORKSPACE_" + re.sub(r"[^A-Z0-9]", "_", server.display_name.upper())] = config`; update the module-level docstring at line ~651 from `Dict keyed by "{server_type}_{server.id}"` to `Dict keyed by "WORKSPACE_{NORMALIZED_NAME}" where NORMALIZED_NAME = re.sub(r"[^A-Z0-9]", "_", display_name.upper()) — non-alphanumeric chars replaced with underscores`; update the inline comment on that line accordingly
- [X] T100 [P] Update all key-pattern assertions in `backend/tests/ai/agents/test_remote_mcp_loading.py`: add `import re` at top; replace every occurrence of `f"remote_{server.id}"` → `"WORKSPACE_" + re.sub(r"[^A-Z0-9]", "_", server.display_name.upper())`, same substitution for `f"npx_{server.id}"` and `f"uvx_{server.id}"`; update the contract-guarantee docstring block at lines 9–13 to reflect the new `WORKSPACE_{NORMALIZED_NAME}` pattern; verify that test `display_name` values like `"Test Remote MCP"` → `WORKSPACE_TEST_REMOTE_MCP`, `"NPX Smoke Test"` → `WORKSPACE_NPX_SMOKE_TEST`; run `uv run pytest tests/ai/agents/test_remote_mcp_loading.py -q` to confirm all tests pass
- [X] T101 [P] Update `plan.md` at `specs/025-mcp-settings/plan.md` line ~502: change the "Config key naming convention" note from `{server_type.value}_{server.id}` to `WORKSPACE_{NORMALIZED_NAME}` with a note that `NORMALIZED_NAME = re.sub(r"[^A-Z0-9]", "_", display_name.upper())`; update `research.md` D-08 decision note in `specs/025-mcp-settings/research.md` line ~102 from `{server_type}_{server_id}` to `WORKSPACE_{NORMALIZED_NAME}` to keep design documents in sync

---

```
T001─T002─T003─T004 (migration complete)
            │
     T005───┴──────────────────────────────────────────────────────────┐
            │                                                           │
      T006─T007─T008─T009─T010─T011 (foundational backend complete)   │
            │                                                           │
  ┌─────────┴──────────┐          ┌───────────────────┐               │
  │   US1 (T014–T020)  │          │   US2 (T021–T029) │               │
  └────────────────────┘          └───────────────────┘               │
           │                                │                           │
  ┌────────┴────────────────────────────────┴──────────────────────┐   │
  │                    US3 (T030–T036)                              │   │
  └─────────────────────────────────────────────────────────────────┘   │
           │                                                             │
  ┌────────┴──────┐  ┌─────────────────┐  ┌────────────────────────┐   │
  │ US4 (T037–T041)│  │ US5 (T042–T046)│  │  US6 (T047–T049)       │   │
  └───────────────┘  └────────────────┘  └────────────────────────┘   │
           │                │                         │                  │
           └────────────────┴─────────────────────────┴──────────────────┤
                                                                         │
                        Poller (T050–T054) ─ parallel to US phases ─────┘
                                │
                      Polish (T055–T059)
                                │
                  US7 None Auth (T060–T064)
                                │
              Agent Integration (T089–T094) ─ independent, runs after T079
                                │
              Type Cleanup (T095–T098) ─ depends on T079; T096/T097 parallel; T098 last
                                │
              Key Rename (T099–T101) ─ depends on T095 (public name); T100/T101 parallel
```

### Parallel Execution Opportunities

- **T007, T008, T009, T012** — can run in parallel after T006 starts (different files)
- **T014, T015, T016** — can run in parallel (frontend store + components are independent files)
- **T026, T027, T028** — backend and frontend tests can run in parallel
- **T035, T036** — backend service tests and frontend component tests are independent
- **T050–T054** — poller work is independent of US4/US5/US6 phases; can run in parallel with them
- **T055–T059** — all polish tasks are independent
- **T062, T063, T064** — frontend type changes, tests, and badge update are independent files; can run in parallel after T060+T061
- **T089–T094** — all test-only; fully independent of all other phases; can run in parallel with Phase 9 (poller)
- **T096, T097** — independent file edits within `pilotspace_stream_utils.py`; can run in parallel after T095
- **T100, T101** — test updates and doc updates are independent files; can run in parallel after T099

---

## MVP Scope

**Minimum viable increment** = Phases 1–4 (T001–T029):
- Migration applied ✓
- Core CRUD (list + create + edit) working ✓
- Table view with filter ✓
- Form Config dialog with masked secrets ✓
- Satisfies Scenarios 1, 3, 4 from spec

Add Phase 5 (T030–T036) for bulk onboarding (Scenario 2/7).
Add Phases 6–8 (T037–T049) for full operational controls.
Add Phase 9 (T050–T054) for autonomous health monitoring.
Add Phase 16 (T089–T094) to verify agent MCP tool invocation end-to-end.
Add Phase 17 (T095–T098) to clean up type annotation suppressors.
Add Phase 18 (T099–T101) to rename server key pattern to `WORKSPACE_{DISPLAY_NAME}`.

---

## Implementation Strategy

1. **Start with T001–T004** (migration) — unblocks all backend work
2. **T006–T013 in parallel batches** — 2 engineers can split backend infra (T006–T011) vs tests (T012–T013)
3. **US1 frontend (T014–T020)** — unblocks visual review of the table before form dialog is ready
4. **US2 + US3 in tandem** — dialog (T021–T029) and import service (T030–T036) are largely independent
5. **US4/US5/US6 + Poller** — can be parallelised after dialog is working
6. **Polish last** — T055–T059 run once all feature phases are green

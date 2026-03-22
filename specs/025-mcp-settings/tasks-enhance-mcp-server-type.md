# Tasks: McpServerType Simplification — Remove Legacy npx/uvx, Promote to Command Sub-enum

**Feature**: MCP Server Type Refactor
**Plan**: `specs/025-mcp-settings/plan-enhance-mcp-server-type.md`
**Spec**: `specs/025-mcp-settings/spec.md`
**Branch**: `25-mcp-settings`
**Generated**: 2026-03-22

---

## Summary

Simplify `McpServerType` from 4 values (`remote`, `command`, `npx`, `uvx`) to 2 values (`remote`, `command`).
Introduce `McpCommandRunner` enum (`npx` | `uvx`) as a separate required field when `server_type=command`.
No backward compatibility required — no production rows exist.

**Total tasks**: 47
**Parallel opportunities**: 15 tasks marked `[P]`

---

## Phase 1: Backend Foundation

> All subsequent phases depend on these completing first.

### 1A — ORM Model & Enum Refactor

- [ ] T001 Rename class `REM` → `McpServerType` and remove `NPX = "npx"` / `UVX = "uvx"` values from `McpServerType` in `backend/src/pilot_space/infrastructure/database/models/workspace_mcp_server.py`
- [ ] T002 Add `McpCommandRunner(StrEnum)` with `NPX = "npx"` and `UVX = "uvx"` in `backend/src/pilot_space/infrastructure/database/models/workspace_mcp_server.py`
- [ ] T003 Add `command_runner: Mapped[McpCommandRunner | None]` mapped column (nullable, `Enum(McpCommandRunner, name="mcp_command_runner", create_type=False, values_callable=...)`) to `WorkspaceMcpServer` class in `backend/src/pilot_space/infrastructure/database/models/workspace_mcp_server.py`
- [ ] T004 Update `__all__` in `backend/src/pilot_space/infrastructure/database/models/workspace_mcp_server.py`: export `McpCommandRunner`; update docstring on `WorkspaceMcpServer` to remove NPX/UVX references

### 1B — Alembic Migration

- [ ] T005 Write `backend/alembic/versions/092_simplify_mcp_server_type.py` with `down_revision = "091_widen_mcp_url_column"`. The `upgrade()` must execute in order: (1) `ALTER COLUMN server_type TYPE TEXT`, (2) `DROP TYPE mcp_server_type`, (3) `CREATE TYPE mcp_server_type AS ENUM ('remote', 'command')`, (4) `UPDATE ... SET server_type='command' WHERE server_type IN ('npx','uvx')`, (5) `ALTER COLUMN server_type TYPE mcp_server_type USING server_type::mcp_server_type`, (6) `CREATE TYPE mcp_command_runner AS ENUM ('npx', 'uvx')`, (7) `ADD COLUMN command_runner mcp_command_runner NULL`, (8) backfill `command_runner` via CASE on `url_or_command` prefix for command rows, (9) strip runner prefix from `url_or_command` for command rows. The `downgrade()` must reverse all steps.

### 1C — Security Layer

- [ ] T006 [P] Rename `validate_npx_uvx_command` → `validate_command_package` in `backend/src/pilot_space/security/mcp_validation.py`; update function signature to `def validate_command_package(package_args: str, runner: McpCommandRunner) -> str`; add `McpCommandRunner` to the import from `workspace_mcp_server` models; update `__all__`

---

## Phase 2: Backend API Layer

> Depends on Phase 1 (T001–T006).

### 2A — API Schemas

- [ ] T007 Update imports in `backend/src/pilot_space/api/v1/routers/_mcp_server_schemas.py`: add `McpCommandRunner` to the import from `workspace_mcp_server`; update `validate_npx_uvx_command` import → `validate_command_package`
- [ ] T008 Add `command_runner: McpCommandRunner | None = Field(default=None, description="Command runner: npx or uvx. Required when server_type=command.")` field to `WorkspaceMcpServerCreate` in `backend/src/pilot_space/api/v1/routers/_mcp_server_schemas.py`
- [ ] T009 Update `validate_server_type_transport` model validator in `WorkspaceMcpServerCreate` in `backend/src/pilot_space/api/v1/routers/_mcp_server_schemas.py`: remove all `McpServerType.NPX` and `McpServerType.UVX` branches — only `REMOTE` (SSE/StreamableHTTP) and `COMMAND` (STDIO) remain
- [ ] T010 Add `validate_command_runner_required` model validator to `WorkspaceMcpServerCreate` in `backend/src/pilot_space/api/v1/routers/_mcp_server_schemas.py`: raises `ValueError("command_runner ('npx' or 'uvx') is required for command-type servers")` if `server_type==COMMAND and command_runner is None`; raises `ValueError("command_runner must not be set for remote servers")` if `server_type==REMOTE and command_runner is not None`
- [ ] T011 Update `validate_url_or_command` model validator in `WorkspaceMcpServerCreate` in `backend/src/pilot_space/api/v1/routers/_mcp_server_schemas.py`: replace `elif self.server_type in (McpServerType.COMMAND, McpServerType.NPX, McpServerType.UVX):` with `elif self.server_type == McpServerType.COMMAND:`; call `validate_command_package(effective, self.command_runner)` instead of `validate_npx_uvx_command`
- [ ] T012 [P] Apply same changes to `WorkspaceMcpServerUpdate` in `backend/src/pilot_space/api/v1/routers/_mcp_server_schemas.py`: add `command_runner: McpCommandRunner | None = Field(default=None)` field; update `validate_server_type_transport` (remove NPX/UVX branches); add `validate_command_runner_required`; update `validate_url_or_command` to call `validate_command_package`
- [ ] T013 [P] Add `command_runner: McpCommandRunner | None = None` field to `WorkspaceMcpServerResponse` in `backend/src/pilot_space/api/v1/routers/_mcp_server_schemas.py`; update `from_orm_model` classmethod to pass `command_runner=server.command_runner` in the `cls(...)` constructor call

### 2B — Router

- [ ] T014 [P] Update `backend/src/pilot_space/api/v1/routers/workspace_mcp_servers.py`: add `McpCommandRunner` to the import from `workspace_mcp_server` models; remove all references to `McpServerType.NPX` and `McpServerType.UVX` in PATCH cross-validation logic (the effective_type check); update comments that mention "NPX/UVX" → "COMMAND"

---

## Phase 3: Backend Application Services

> Depends on Phase 1 (T001–T006). Can run in parallel with Phase 2.

### 3A — Import Service

- [ ] T015 Add `command_runner: McpCommandRunner | None = None` field to the `ParsedMcpServer` dataclass in `backend/src/pilot_space/application/services/mcp/import_mcp_servers_service.py`; add `McpCommandRunner` to the import block from models
- [ ] T016 Refactor `_parse_server_entry` in `backend/src/pilot_space/application/services/mcp/import_mcp_servers_service.py` command branch: split `command` string on whitespace; if `parts[0].lower()` is `"npx"` set `command_runner = McpCommandRunner.NPX`, if `"uvx"` set `McpCommandRunner.UVX`, otherwise return `None` (the entry will be excluded from parsed list — the caller should record it as an error via the validate step); set `url_or_command = " ".join(parts[1:]).strip()`; append `args` list to `url_or_command`; set `server_type=McpServerType.COMMAND` and `command_runner=<runner>` on the returned `ParsedMcpServer`
- [ ] T017 Update `_validate_entry` in `backend/src/pilot_space/application/services/mcp/import_mcp_servers_service.py`: remove `McpServerType.NPX` and `McpServerType.UVX` from the `elif` condition; keep only `McpServerType.COMMAND`; update shell metachar validation call to use renamed import if needed
- [ ] T018 Update `import_servers` method in `backend/src/pilot_space/application/services/mcp/import_mcp_servers_service.py`: pass `command_runner=entry.command_runner` when constructing `WorkspaceMcpServer(...)`

### 3B — Agent Utils

- [ ] T019 Update `_build_server_config` in `backend/src/pilot_space/ai/agents/pilotspace_stream_utils.py` non-REMOTE branch: add guard `if not server.command_runner: logger.warning("mcp_command_runner_missing", server_id=str(server.id)); return None`; replace `command_str = server.url_or_command` with `runner = server.command_runner.value; package_args = server.url_or_command or ""; command_str = f"{runner} {package_args}".strip()`; remove comment `"# Command (COMMAND / legacy NPX / UVX)"` → update to `"# COMMAND — build McpStdioServerConfig"`

---

## Phase 4: Backend Tests

> Depends on Phases 1–3 (T001–T019).

- [ ] T020 Update all test fixtures in `backend/tests/api/test_workspace_mcp_servers.py`: replace `server_type='npx'` → `server_type='command', command_runner='npx'`; replace `server_type='uvx'` → `server_type='command', command_runner='uvx'`; update request payload dicts that reference npx/uvx server_type; update any assertions on response `server_type` field
- [ ] T021 Add test `test_create_command_server_requires_command_runner` in `backend/tests/api/test_workspace_mcp_servers.py`: POST `{"server_type": "command", "url_or_command": "@foo/bar", "display_name": "test", "auth_type": "none", "transport": "stdio"}` (no `command_runner`) → assert `response.status_code == 422`
- [ ] T022 Add test `test_create_command_server_with_npx_runner` in `backend/tests/api/test_workspace_mcp_servers.py`: POST `{"server_type": "command", "command_runner": "npx", "url_or_command": "@modelcontextprotocol/server", "display_name": "npx-srv", "auth_type": "none", "transport": "stdio"}` → assert `201` and `response.json()["command_runner"] == "npx"`
- [ ] T023 Add test `test_remote_server_rejects_command_runner` in `backend/tests/api/test_workspace_mcp_servers.py`: POST `{"server_type": "remote", "command_runner": "npx", "url_or_command": "https://mcp.example.com/sse", "display_name": "r", "auth_type": "none", "transport": "sse"}` → assert `422`
- [ ] T024 [P] Add test `test_import_rejects_non_npx_uvx_command` in `backend/tests/api/test_workspace_mcp_servers.py` (or `backend/tests/services/test_import_mcp_servers_service.py`): call `ImportMcpServersService.parse_config_json(...)` with `{"mcpServers": {"bad": {"command": "docker run foo"}}}` → result entry has runner `None` and is excluded from valid parsed list; when imported, it appears in `errors` with a non-empty reason
- [ ] T025 [P] Update `backend/tests/ai/agents/test_remote_mcp_loading.py`: replace `server_type=McpServerType.NPX` → `server_type=McpServerType.COMMAND, command_runner=McpCommandRunner.NPX`; replace `server_type=McpServerType.UVX` → `server_type=McpServerType.COMMAND, command_runner=McpCommandRunner.UVX`; add test asserting that `_build_server_config` returns `None` when `command_runner=None` on a COMMAND server; remove xfail markers on tests whose implementation is now complete

---

## Phase 5: Frontend Types & Store

> Can start in parallel with backend phases — types are known from the plan.

- [ ] T026 Update `McpServerType` union in `frontend/src/stores/ai/MCPServersStore.ts`: change to `'remote' | 'command'`; add `export type McpCommandRunner = 'npx' | 'uvx'`
- [ ] T027 Add `command_runner: McpCommandRunner | null` to the `MCPServer` interface in `frontend/src/stores/ai/MCPServersStore.ts`
- [ ] T028 [P] Add `command_runner?: McpCommandRunner` to `MCPServerRegisterRequest` in `frontend/src/stores/ai/MCPServersStore.ts`; add `command_runner?: McpCommandRunner | null` to `MCPServerUpdateRequest`

---

## Phase 6: Frontend Components

> Depends on Phase 5 (T026–T028).

### 6A — Table Component

- [ ] T029 Remove `npx` and `uvx` entries from `SERVER_TYPE_ICON` and `SERVER_TYPE_LABEL` record maps in `frontend/src/features/settings/components/mcp-servers-table.tsx`; keep only `remote` and `command`
- [ ] T030 Update `ServerTypeBadge` component in `frontend/src/features/settings/components/mcp-servers-table.tsx`: add `runner?: McpCommandRunner | null` prop; when `type === 'command'`, display badge label as `runner === 'uvx' ? 'uvx' : 'npx'`; update all call sites in the table row to pass `runner={server.command_runner}`; import `McpCommandRunner` from store
- [ ] T031 [P] Remove `<SelectItem value="npx">` and `<SelectItem value="uvx">` from the Type filter `<SelectContent>` in `frontend/src/features/settings/components/mcp-servers-table.tsx`

### 6B — Form Component

- [ ] T032 Add `commandRunner: McpCommandRunner` (default `'npx'`) to the `FormConfigData` interface and `buildInitialState` function in `frontend/src/features/settings/components/form-config-tab.tsx`; populate from `server.command_runner ?? 'npx'` when editing; reset `commandRunner: 'npx'` inside `handleServerTypeChange` when switching to `'command'`; import `McpCommandRunner` from store
- [ ] T033 Add Command Runner `<Select>` field block inside the form JSX in `frontend/src/features/settings/components/form-config-tab.tsx` (shown only when `form.serverType === 'command'`): `<Label htmlFor="fc-runner">Command Runner</Label>` with `<SelectItem value="npx">npx (Node.js)</SelectItem>` and `<SelectItem value="uvx">uvx (Python)</SelectItem>`; place it between Server Type and URL/Command rows
- [ ] T034 Update URL/Command field in `frontend/src/features/settings/components/form-config-tab.tsx`: label changes to `Package / Arguments` when `form.serverType === 'command'`; add helper `<p>` below input showing `Full command: {form.commandRunner} {form.urlOrCommand || '<package>'}` for command type; in `handleSubmit`, include `command_runner: form.commandRunner` in the request payload when `form.serverType === 'command'`

### 6C — Import JSON Tab

- [ ] T035 [P] Update detected server preview cards in `frontend/src/features/settings/components/import-json-tab.tsx`: when a parsed server has `server_type === 'command'`, display `command_runner` badge (`npx`/`uvx`) instead of just "Command"; import `McpCommandRunner` type from store

---

## Phase 7: Frontend Tests

> Depends on Phases 5–6 (T026–T035).

- [ ] T036 Update `makeServer` factory helper in `frontend/src/features/settings/components/__tests__/form-config-tab.test.tsx`: add `command_runner: null` to the default shape (to satisfy the updated `MCPServer` interface)
- [ ] T037 [P] Add test `shows command runner selector when server type is command` in `frontend/src/features/settings/components/__tests__/form-config-tab.test.tsx`: render `<FormConfigTab onSave={vi.fn()} isSaving={false} />`; change Server Type select to `command`; assert `screen.getByLabelText('Command Runner')` is visible with `npx` selected
- [ ] T038 [P] Add test `submit payload includes command_runner for command type` in `frontend/src/features/settings/components/__tests__/form-config-tab.test.tsx`: fill display name as `"my-server"`, change type to `command`, change runner to `uvx`, fill url as `my-tool`; submit form; assert `onSave` called with object containing `{ server_type: 'command', command_runner: 'uvx', url_or_command: 'my-tool' }`
- [ ] T039 [P] Update `makeServer` in `frontend/src/features/settings/components/__tests__/mcp-servers-table.test.tsx`, `mcp-server-dialog.test.tsx`, `mcp-server-row-actions.test.tsx`, and `frontend/src/stores/ai/__tests__/MCPServersStore.test.ts`: add `command_runner: null` to default shape; replace any occurrence of `server_type: 'npx'` with `server_type: 'command', command_runner: 'npx'`; replace any `server_type: 'uvx'` with `server_type: 'command', command_runner: 'uvx'`

---

## Phase 8: Quality Gates

> Run after all implementation phases are complete.

- [ ] T040 Run `cd backend && alembic check` — verify single head and model/migration alignment; fix any mismatch
- [ ] T041 [P] Run `cd backend && uv run pyright` — zero errors; fix all type errors from refactor
- [ ] T042 [P] Run `cd backend && uv run ruff check` — zero warnings; apply `--fix` as needed
- [ ] T043 [P] Run `cd backend && uv run pytest tests/api/test_workspace_mcp_servers.py -v` — all pass
- [ ] T044 [P] Run `cd frontend && pnpm type-check` — zero errors
- [ ] T045 [P] Run `cd frontend && pnpm lint` — zero warnings
- [ ] T046 [P] Run `cd frontend && pnpm test` — all pass

---

## Dependency Graph

```
T001–T004 (model)
    │
    ├─► T005 (migration)
    │
    ├─► T006 (security rename)
    │        │
    │        ▼
    │   T007–T013 (schemas)  ←── can run in parallel with T014–T018
    │   T014 (router)
    │   T015–T018 (import service)
    │   T019 (agent utils)
    │        │
    │        ▼
    │   T020–T025 (backend tests)
    │
    └─► T026–T028 (frontend types — independent)
             │
             ▼
        T029–T035 (frontend components)
             │
             ▼
        T036–T039 (frontend tests)
             │
             ▼
        T040–T046 (quality gates)
```

## Parallel Execution Opportunities

```
T006 || T001–T005          — security rename while writing model + migration
T012 || T008–T011          — WorkspaceMcpServerUpdate schema while doing Create
T013 || T007–T012          — Response schema while validators being updated
T014 || T007–T013          — Router update while schemas being written
T015–T018 || T007–T014     — Import service while API layer being updated
T024 || T020–T023          — Import test in different file
T025 || T020–T023          — Agent tests in different file
T028 || T026–T027          — Request interfaces while base types being updated
T031 || T029–T030          — Filter dropdown while badges updated
T035 || T032–T034          — Import tab while form being updated
T037–T038 || T036          — New form tests while fixture updated
T039 || T036–T038          — Other test fixture updates
T041–T046 || after T040    — All quality checks after alembic check
```

---

## Implementation Notes

- **No backward compat**: Migration can safely drop and recreate `mcp_server_type` — no production rows.
- **`url_or_command` for COMMAND servers**: After migration stores only the package/args (e.g. `@foo/bar --debug`), NOT the full command with runner prefix.
- **Agent command assembly**: `f"{server.command_runner.value} {server.url_or_command}"` — guarded by `if not server.command_runner: return None`.
- **Import parser for arbitrary commands**: `"docker run foo"` → `_parse_server_entry` returns `None` (unsupported runner); this causes the entry to be excluded from the parsed list silently. To surface it as an error, the import flow should track entries that returned `None` from `_parse_server_entry` and add them to the `errors` list with reason `"unsupported_command_runner"`.
- **File size guard**: `_mcp_server_schemas.py` is ~524 lines; adding ~25 lines stays within the 700-line limit.
- **Frontend filter state**: `McpFilterState.serverType` was `McpServerType | 'all'` — now only valid values are `'all' | 'remote' | 'command'`. No code change needed if old `'npx'`/`'uvx'` filter values are never written; guard on mount with `if (!['all','remote','command'].includes(filter.serverType)) setFilter({ serverType: 'all' })` if persisted to URL/localStorage.

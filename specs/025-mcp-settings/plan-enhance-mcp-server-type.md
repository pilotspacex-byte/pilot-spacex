# Enhancement Plan: McpServerType Simplification — Remove Legacy npx/uvx, Promote to Command Sub-enum

**Feature**: MCP Server Type Refactor
**Branch**: `25-mcp-settings` (current)
**Created**: 2026-03-22
**Spec**: `specs/025-mcp-settings/spec.md`
**Author**: AI-generated

---

## Summary

The current `McpServerType` enum has four values: `remote`, `command`, `npx`, `uvx`.
The user request changes this to **two server types**:

- `REMOTE` — remote HTTP endpoint (SSE / StreamableHTTP)
- `COMMAND` — locally-launched process **restricted** to `npx` or `uvx` commands only

`npx` and `uvx` are promoted from top-level `McpServerType` values to an enum for the **command runner** field (`McpCommandRunner`).
There is **no backward compatibility requirement** — the DB currently has no production rows that need migration.

---

## Scope

| Layer | Change |
|-------|--------|
| Backend: DB model | Rename class `REM` → `McpServerType`; remove `NPX`/`UVX` values; remove `COMMAND` legacy guard |
| Backend: DB migration | Recreate `mcp_server_type` enum with only `('remote', 'command')`; add `command_runner` column `('npx', 'uvx')` |
| Backend: API schemas | `WorkspaceMcpServerCreate/Update`: remove legacy NPX/UVX server_type branches; add `command_runner` field (required when `server_type=command`) |
| Backend: Security validation | `validate_npx_uvx_command` → `validate_command_runner_command`; update signature |
| Backend: Import service | Refactor `_parse_server_entry` to produce `command_runner='npx'|'uvx'` instead of inferred server_type |
| Backend: Agent utils | Update `_build_server_config` type checks (remove NPX/UVX enum branches) |
| Backend: Tests | Update all test fixtures that use `server_type='npx'` or `server_type='uvx'` |
| Frontend: Types | `McpServerType = 'remote' \| 'command'` (drop `'npx' \| 'uvx'`) |
| Frontend: New type | Add `McpCommandRunner = 'npx' \| 'uvx'` |
| Frontend: Store | Add `command_runner` to `MCPServer`, `MCPServerRegisterRequest`, `MCPServerUpdateRequest` |
| Frontend: Table | `SERVER_TYPE_ICON/LABEL` maps simplify to 2 entries; filter dropdown simplified |
| Frontend: Form | Command sub-type selector (npx/uvx) appears when `serverType === 'command'`; `urlOrCommand` placeholder updates accordingly |
| Frontend: Tests | Update test fixtures |

---

## Technical Context

### Current State

```python
# workspace_mcp_server.py
class REM(StrEnum):          # BUG: misnamed class
    REMOTE = "remote"
    COMMAND = "command"
    NPX = "npx"              # legacy
    UVX = "uvx"              # legacy

# DB enum: mcp_server_type ('remote', 'npx', 'uvx', 'command')
# url_or_command stores the full command string, e.g. "npx @modelcontextprotocol/server"
```

### Target State

```python
class McpServerType(StrEnum):
    REMOTE = "remote"
    COMMAND = "command"

class McpCommandRunner(StrEnum):
    NPX = "npx"
    UVX = "uvx"

# DB enum: mcp_server_type ('remote', 'command') — simplified
# DB column: command_runner mcp_command_runner ('npx', 'uvx') NULL — required when server_type='command'
# url_or_command stores the package/tool args, e.g. "@modelcontextprotocol/server --port 3000"
# At runtime: "{command_runner} {url_or_command} {command_args}" is assembled
```

> **Key design change**: `url_or_command` for COMMAND servers stores the **package/tool name + args** (not the full command including the runner). The runner prefix (`npx` / `uvx`) is stored separately in `command_runner` and prepended at runtime. This makes the distinction explicit and UI-friendly.
>
> **Alternative considered**: Keep `url_or_command` as a free-text full command (current behavior) and only add `command_runner` as a validator/selector hint. **Rejected** — this creates ambiguity when the user types `npx foo` (runner duplicated in both fields).

---

## Phase 0: Research — All Clarifications Resolved

| Question | Decision |
|----------|----------|
| Should `url_or_command` still contain the full `npx foo` command, or just `foo`? | **Just the package/args** — `command_runner` stores `npx\|uvx`; runtime prepends it. This aligns with how the form presents the field: "Command" = `npx {url_or_command} {command_args}`. |
| How does the import service handle `"command": "npx @foo/bar --debug"` from Claude Desktop JSON? | Parse command token[0] as `command_runner` (`npx`/`uvx`); remaining tokens become `url_or_command`; `args` list becomes `command_args`. |
| What happens to arbitrary commands (not npx/uvx) in imported JSON? | **Reject with `errors` entry**: only `npx` and `uvx` are supported runners. The import error message is `"command_runner: only 'npx' and 'uvx' are supported"`. |
| Does `_build_server_config` in `pilotspace_stream_utils.py` need changes? | Yes: assemble `f"{server.command_runner} {server.url_or_command}"` and pass `command_args` separately via `shlex.split`. The existing `shlex.split(command_str)` logic becomes `shlex.split(f"{runner} {url_or_command}")`. |
| Are there existing DB rows that need migration? | No production rows. The migration may **drop and recreate** the `mcp_server_type` enum safely. |
| Does the `validate_npx_uvx_command` function need updating? | Yes: rename to `validate_command_package` (or similar); it now validates `url_or_command` (package + args, no runner prefix). Shell metachar rules remain identical. |
| SSRF scope for COMMAND type | Unchanged — COMMAND servers validate for shell injection, not SSRF. |

---

## Phase 1: Data Model

### Migration: `092_simplify_mcp_server_type`

**Chains from**: `091_widen_mcp_url_column`

**Strategy** (no production rows — destructive migration is safe):

```sql
-- Step 1: Drop the old enum type (requires dropping dependent column first)
ALTER TABLE workspace_mcp_servers ALTER COLUMN server_type TYPE TEXT;
DROP TYPE mcp_server_type;

-- Step 2: Recreate enum with only 2 values
CREATE TYPE mcp_server_type AS ENUM ('remote', 'command');

-- Step 3: Migrate old values: 'npx' → 'command', 'uvx' → 'command'
UPDATE workspace_mcp_servers SET server_type = 'command'
  WHERE server_type IN ('npx', 'uvx');

-- Step 4: Re-apply enum type
ALTER TABLE workspace_mcp_servers
  ALTER COLUMN server_type TYPE mcp_server_type
  USING server_type::mcp_server_type;

-- Step 5: Add command_runner column
CREATE TYPE mcp_command_runner AS ENUM ('npx', 'uvx');
ALTER TABLE workspace_mcp_servers
  ADD COLUMN command_runner mcp_command_runner NULL;

-- Step 6: Backfill command_runner from url_or_command prefix for old rows
UPDATE workspace_mcp_servers
  SET command_runner = CASE
    WHEN url_or_command LIKE 'npx %' THEN 'npx'::mcp_command_runner
    WHEN url_or_command LIKE 'uvx %' THEN 'uvx'::mcp_command_runner
    WHEN url_or_command = 'npx' THEN 'npx'::mcp_command_runner
    WHEN url_or_command = 'uvx' THEN 'uvx'::mcp_command_runner
    ELSE NULL
  END
WHERE server_type = 'command';

-- Step 7: Strip the runner prefix from url_or_command for command rows
-- e.g. "npx @foo/bar" → "@foo/bar"
UPDATE workspace_mcp_servers
  SET url_or_command = TRIM(SUBSTRING(url_or_command FROM 5))  -- strip 'npx '
WHERE server_type = 'command' AND url_or_command LIKE 'npx %';

UPDATE workspace_mcp_servers
  SET url_or_command = TRIM(SUBSTRING(url_or_command FROM 5))  -- strip 'uvx '
WHERE server_type = 'command' AND url_or_command LIKE 'uvx %';
```

**ORM changes** (`workspace_mcp_server.py`):

```python
class McpServerType(StrEnum):   # Fix: rename from REM
    REMOTE = "remote"
    COMMAND = "command"

class McpCommandRunner(StrEnum):  # NEW
    NPX = "npx"
    UVX = "uvx"

# New column on WorkspaceMcpServer:
command_runner: Mapped[McpCommandRunner | None] = mapped_column(
    Enum(
        McpCommandRunner,
        name="mcp_command_runner",
        create_type=False,
        values_callable=lambda x: [e.value for e in x],
    ),
    nullable=True,
    doc="Command runner for COMMAND-type servers: npx or uvx",
)
```

**`__all__` update**: export `McpCommandRunner`, remove `McpServerType` alias for `REM`.

---

## Phase 1: API Contract Changes

### `WorkspaceMcpServerCreate` changes

```python
server_type: McpServerType = Field(
    default=McpServerType.REMOTE,
    description="Server type: remote or command",
)
command_runner: McpCommandRunner | None = Field(
    default=None,
    description="Command runner: npx or uvx. Required when server_type=command.",
)
```

**New validator** (replace `validate_server_type_transport`):

```python
@model_validator(mode="after")
def validate_command_runner_required(self) -> WorkspaceMcpServerCreate:
    """command_runner is required when server_type=command."""
    if self.server_type == McpServerType.COMMAND and self.command_runner is None:
        raise ValueError("command_runner ('npx' or 'uvx') is required for command-type servers")
    if self.server_type == McpServerType.REMOTE and self.command_runner is not None:
        raise ValueError("command_runner must not be set for remote servers")
    return self
```

**Updated `validate_url_or_command`**:
- Remove NPX/UVX enum branches — only `REMOTE` and `COMMAND` exist
- `COMMAND`: validate via `validate_command_package(effective, self.command_runner)`

**Updated `validate_server_type_transport`**:
- Remove `McpServerType.NPX` / `McpServerType.UVX` references
- Keep: REMOTE → SSE/STREAMABLE_HTTP; COMMAND → STDIO

### `WorkspaceMcpServerUpdate` changes

Same additions: `command_runner: McpCommandRunner | None` field. Same validators updated to remove NPX/UVX branches.

### `WorkspaceMcpServerResponse` changes

Add field:
```python
command_runner: McpCommandRunner | None = None
```

Update `from_orm_model` to include `command_runner=server.command_runner`.

### Security: `mcp_validation.py`

- Rename `validate_npx_uvx_command` → `validate_command_package`
- Signature: `def validate_command_package(package_args: str, runner: McpCommandRunner) -> str`
- Same shell metachar validation logic — `package_args` no longer contains the runner prefix

Update `__all__` and all callers.

---

## Phase 1: Import Service Changes

**`import_mcp_servers_service.py`** — `_parse_server_entry`:

```python
if command and isinstance(command, str):
    parts = command.split()
    runner_str = parts[0].lower() if parts else ""

    if runner_str == "npx":
        command_runner = McpCommandRunner.NPX
    elif runner_str == "uvx":
        command_runner = McpCommandRunner.UVX
    else:
        # Reject: only npx and uvx are supported
        return None, f"command_runner: only 'npx' and 'uvx' are supported (got '{runner_str}')"

    # Strip runner from url_or_command
    package_args = " ".join(parts[1:]).strip() if len(parts) > 1 else ""

    # Append JSON args list
    args_list = config.get("args")
    if isinstance(args_list, list):
        str_args = " ".join(str(a) for a in args_list if a)
        if str_args:
            package_args = f"{package_args} {str_args}".strip()

    return ParsedMcpServer(
        name=name,
        server_type=McpServerType.COMMAND,
        command_runner=command_runner,
        transport=McpTransport.STDIO,
        url_or_command=package_args,
        env_vars=_extract_env_vars(config),
    ), None
```

Update `ParsedMcpServer` dataclass to add `command_runner: McpCommandRunner | None = None`.

Update `_validate_entry` to remove NPX/UVX server_type checks; validation is now `COMMAND` only.

---

## Phase 1: Agent Utils Changes

**`pilotspace_stream_utils.py`** — `_build_server_config`:

```python
# Current (line ~777):
# Command (COMMAND / legacy NPX / UVX) — build McpStdioServerConfig
# ...
# command_str = server.url_or_command  ← was full "npx @foo/bar"

# New:
# COMMAND — build McpStdioServerConfig
if server.server_type != McpServerType.REMOTE:
    if server.transport != McpTransport.STDIO:
        logger.warning(...)
        return None
    if not server.command_runner:
        logger.warning("mcp_command_runner_missing", server_id=str(server.id))
        return None

    runner = server.command_runner.value   # "npx" or "uvx"
    package_args = server.url_or_command or ""
    full_cmd = f"{runner} {package_args}".strip()

    try:
        import shlex
        parts = shlex.split(full_cmd, posix=True)
    except ValueError:
        ...
```

No other changes in `pilotspace_stream_utils.py`.

---

## Phase 1: Frontend Changes

### Type Updates (`MCPServersStore.ts`)

```typescript
// Before
export type McpServerType = 'remote' | 'command' | 'npx' | 'uvx';

// After
export type McpServerType = 'remote' | 'command';
export type McpCommandRunner = 'npx' | 'uvx';
```

**`MCPServer` interface** — add:
```typescript
command_runner: McpCommandRunner | null;
```

**`MCPServerRegisterRequest`** — add:
```typescript
command_runner?: McpCommandRunner;
```

**`MCPServerUpdateRequest`** — add:
```typescript
command_runner?: McpCommandRunner | null;
```

**`McpFilterState`** — `serverType` remains `McpServerType | 'all'` (now only 2 real values).

### `mcp-servers-table.tsx`

- `SERVER_TYPE_ICON` and `SERVER_TYPE_LABEL` maps: remove `npx` and `uvx` entries
- Filter `<SelectContent>`: remove `<SelectItem value="npx">` and `<SelectItem value="uvx">`
- Type badge renders `command_runner` sub-label when type is `command`:

```tsx
function ServerTypeBadge({ type, runner }: { type: McpServerType; runner?: McpCommandRunner | null }) {
  if (type === 'command') {
    return (
      <Badge variant="secondary" className="gap-1 text-xs">
        <Terminal className="h-4 w-4" />
        {runner === 'uvx' ? 'uvx' : 'npx'}
      </Badge>
    );
  }
  return (
    <Badge variant="default" className="gap-1 text-xs">
      <Globe className="h-4 w-4" />
      Remote
    </Badge>
  );
}
```

### `form-config-tab.tsx`

**`FormConfigData`** — add:
```typescript
commandRunner: McpCommandRunner;   // 'npx' | 'uvx', default 'npx'
```

**`buildInitialState`** — populate from `server.command_runner || 'npx'`.

**`handleServerTypeChange`** — reset `commandRunner: 'npx'` when switching to command.

**New field block** (shown when `form.serverType === 'command'`):
```tsx
<div className="space-y-2">
  <Label htmlFor="fc-runner">Command Runner</Label>
  <Select
    value={form.commandRunner}
    onValueChange={(v) => setField('commandRunner', v as McpCommandRunner)}
    disabled={isSaving}
  >
    <SelectTrigger id="fc-runner">
      <SelectValue />
    </SelectTrigger>
    <SelectContent>
      <SelectItem value="npx">npx (Node.js)</SelectItem>
      <SelectItem value="uvx">uvx (Python)</SelectItem>
    </SelectContent>
  </Select>
</div>
```

**URL/Command placeholder** updates to:
```tsx
placeholder={
  form.serverType === 'remote'
    ? 'https://mcp.example.com/sse'
    : `${form.commandRunner} package-name --arg`   // e.g. "npx @foo/bar --port 3000"
}
```

But the label should clarify the full assembled command:
```tsx
<Label htmlFor="fc-url">
  {form.serverType === 'remote'
    ? 'Server URL'
    : `Package / Arguments`}
</Label>
{form.serverType !== 'remote' && (
  <p className="text-xs text-muted-foreground">
    Full command: <code>{form.commandRunner} {form.urlOrCommand || '<package>'}</code>
  </p>
)}
```

**`handleSubmit`** — include `command_runner: form.commandRunner` in the request when `serverType === 'command'`.

### `import-json-tab.tsx`

Detected servers preview cards: update to show `command_runner` badge (`npx`/`uvx`) instead of server_type when type is `command`.

### `MCPServersStore.ts` — `filteredServers` computed

No logic change needed — filter now only has `'all' | 'remote' | 'command'` for `serverType`.

---

## Implementation Order

### Step 1: Backend model + migration (no tests yet)
1. Rename class `REM` → `McpServerType` in `workspace_mcp_server.py`
2. Remove `NPX = "npx"` and `UVX = "uvx"` from `McpServerType`
3. Add `McpCommandRunner(StrEnum)` with `NPX = "npx"` and `UVX = "uvx"`
4. Add `command_runner` column to `WorkspaceMcpServer` model
5. Update `__all__`
6. Write migration `092_simplify_mcp_server_type.py`

### Step 2: Security layer
1. Rename `validate_npx_uvx_command` → `validate_command_package` in `mcp_validation.py`
2. Update signature and `__all__`

### Step 3: API schemas
1. Update imports to use renamed `McpCommandRunner`
2. Add `command_runner` field to `WorkspaceMcpServerCreate`, `WorkspaceMcpServerUpdate`, `WorkspaceMcpServerResponse`
3. Update validators: remove NPX/UVX server_type branches; add `command_runner` required validator
4. Update `from_orm_model` to include `command_runner`

### Step 4: Import service
1. Update `ParsedMcpServer` to add `command_runner` field
2. Refactor `_parse_server_entry` to parse runner from command prefix
3. Update `_validate_entry` to remove NPX/UVX enum checks
4. Update `import_servers` to persist `command_runner` on the created ORM object

### Step 5: Agent utils
1. Update `_build_server_config` in `pilotspace_stream_utils.py` to assemble `"{runner} {url_or_command}"` from separate fields
2. Remove NPX/UVX enum branches from `_build_server_config`

### Step 6: Router
1. Update `workspace_mcp_servers.py` to import `McpCommandRunner`
2. Update any PATCH cross-validation logic that references NPX/UVX server_type values

### Step 7: Backend tests
1. Update all test fixtures using `server_type='npx'`/`'uvx'` → `server_type='command', command_runner='npx'`/`'uvx'`
2. Add new test: `command_runner` required when `server_type='command'`
3. Add new test: import rejects arbitrary commands (non-npx/uvx)
4. Update existing agent-loading tests

### Step 8: Frontend types + store
1. Update `McpServerType` union type in `MCPServersStore.ts`
2. Add `McpCommandRunner` type
3. Update `MCPServer`, `MCPServerRegisterRequest`, `MCPServerUpdateRequest` interfaces
4. Export `McpCommandRunner` from store

### Step 9: Frontend components
1. Update `mcp-servers-table.tsx`: icons/labels, filter dropdown, `ServerTypeBadge`
2. Update `form-config-tab.tsx`: add command runner selector, update placeholder/label, update `handleSubmit`
3. Update `import-json-tab.tsx`: preview cards show `command_runner`
4. Update `mcp-server-dialog.tsx` if it references server type labels

### Step 10: Frontend tests
1. Update all mocked `MCPServer` objects: replace `server_type: 'npx'`/`'uvx'` with `server_type: 'command', command_runner: 'npx'`/`'uvx'`
2. Add test: form shows command runner selector when type is `command`
3. Add test: form submits `command_runner` in request payload

---

## Affected Files

### Backend

| File | Change Type |
|------|-------------|
| `backend/src/pilot_space/infrastructure/database/models/workspace_mcp_server.py` | Rename enum class, remove legacy values, add `McpCommandRunner`, add `command_runner` column |
| `backend/alembic/versions/092_simplify_mcp_server_type.py` | **NEW** — migration |
| `backend/src/pilot_space/security/mcp_validation.py` | Rename function, update signature |
| `backend/src/pilot_space/api/v1/routers/_mcp_server_schemas.py` | Add `command_runner` field, update validators, update response |
| `backend/src/pilot_space/application/services/mcp/import_mcp_servers_service.py` | Add `command_runner` to `ParsedMcpServer`, update parser logic |
| `backend/src/pilot_space/ai/agents/pilotspace_stream_utils.py` | Update `_build_server_config` to assemble command from runner + url_or_command |
| `backend/src/pilot_space/api/v1/routers/workspace_mcp_servers.py` | Import `McpCommandRunner`, update cross-validation in PATCH route |
| `backend/tests/api/test_workspace_mcp_servers.py` | Update fixtures, add new tests |

### Frontend

| File | Change Type |
|------|-------------|
| `frontend/src/stores/ai/MCPServersStore.ts` | Update `McpServerType` union, add `McpCommandRunner`, update interfaces |
| `frontend/src/features/settings/components/mcp-servers-table.tsx` | Update icons/labels/filter |
| `frontend/src/features/settings/components/form-config-tab.tsx` | Add command runner selector, update placeholder/submit |
| `frontend/src/features/settings/components/import-json-tab.tsx` | Update preview card labels |
| `frontend/src/features/settings/components/mcp-server-dialog.tsx` | Minor: update any hardcoded type labels |
| `frontend/src/stores/ai/__tests__/MCPServersStore.test.ts` | Update fixtures |
| `frontend/src/features/settings/components/__tests__/form-config-tab.test.tsx` | Update fixtures + add runner tests |
| `frontend/src/features/settings/components/__tests__/mcp-servers-table.test.tsx` | Update fixtures |
| `frontend/src/features/settings/components/__tests__/mcp-server-dialog.test.tsx` | Update fixtures |
| `frontend/src/features/settings/components/__tests__/mcp-server-row-actions.test.tsx` | Update fixtures |

---

## Risk & Mitigations

| Risk | Mitigation |
|------|------------|
| Alembic migration drops `mcp_server_type` enum while it is in use by column | Use `ALTER COLUMN ... TYPE TEXT` before `DROP TYPE`; re-apply enum after recreate |
| `pilotspace_stream_utils.py` gets `None` for `command_runner` on old rows | Guard with `if not server.command_runner: logger.warning(...); return None` |
| Frontend type filter `'npx'` / `'uvx'` persisted in URL/local state | Both map to `'command'` — treat as `'command'` on load; clear invalid filter values on mount |
| 700-line file limit on `_mcp_server_schemas.py` | Currently ~524 lines; adding ~20 lines stays within limit |

---

## Quality Gate Checklist

- [ ] `cd backend && uv run pyright` — zero errors
- [ ] `cd backend && uv run ruff check` — zero warnings
- [ ] `cd backend && uv run pytest tests/api/test_workspace_mcp_servers.py -v` — all pass
- [ ] `cd backend && alembic check` — head matches models
- [ ] `cd frontend && pnpm type-check` — zero errors
- [ ] `cd frontend && pnpm lint` — zero warnings
- [ ] `cd frontend && pnpm test` — all pass

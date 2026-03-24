# Plan: Remove Package/Command Input — Use Args Field for Command Servers

**Feature**: MCP Settings — Form UX Simplification
**Branch**: `25-mcp-settings`
**Created**: 2026-03-22
**Spec**: `specs/025-mcp-settings/spec.md`
**Parent plan**: `plan-enhance-mcp-server-type.md`

---

## Summary

The current `FormConfigTab` shows **two separate input fields** for command-type servers:

1. **Package / Command** (`urlOrCommand`) — the package/tool name, e.g. `@modelcontextprotocol/server-github`
2. **Command Arguments** (`commandArgs`) — extra CLI args, e.g. `-y --api-key $API_KEY`

This is confusing because users mentally think of the whole thing as a single "args" string.

**Change**:
- **Remove** the `urlOrCommand` input from the UI for command-type servers.
- **Repurpose** the `commandArgs` field as the sole args input (full package + args string).
- On form submit, send the `commandArgs` value as `url_or_command` (mapped in `handleSubmit`).
- **Move** the helper note ("Package name or command. The runner will be prepended automatically.") to appear **after** the args input.
- For remote servers, `urlOrCommand` remains the Server URL field — no change.

The JSON import service already parses `url_or_command` correctly (strips runner prefix). No import-side changes are needed.

---

## Current UI Layout (command type)

```
Row 1:   [Server Name]        [Server Type = Command]
Row 1b:  [Command Runner]     (empty col)
Row 2:   [Package / Command]  [Transport]
...
         [Env Vars]
         [Command Arguments]
         <note: "Package name... runner will be prepended">
```

## Target UI Layout (command type)

```
Row 1:   [Server Name]        [Server Type = Command]
Row 1b:  [Command Runner]     (empty col)
Row 2:   [Transport]          (full row — URL/Command input gone for command type)
...
         [Env Vars]
         [Command Arguments]
         <note: "Full command: {runner} {commandArgs}">
```

For **remote type**, Row 2 remains unchanged: `[Server URL] [Transport]`

---

## Research: No Clarifications Needed

| Question | Decision |
|----------|----------|
| What value gets sent as `url_or_command` on submit for command servers? | `commandArgs.trim()` — the args field now owns the package + args string |
| Does backend `url_or_command` semantics change? | No — it still stores the package/args without the runner prefix |
| Does `canSubmit` validation break? | Yes — need to guard `canSubmit` for command servers: require `commandArgs` instead of `urlOrCommand` |
| Does the edit mode pre-population change? | Yes — `buildInitialState` must populate `commandArgs` from `server.url_or_command` for command servers (not `urlOrCommand`) |
| Tests affected? | `form-config-tab.test.tsx` — tests that reference `url_or_command` and `Server URL` label for command type |
| Import JSON tab change? | No — the import parser writes to `url_or_command` directly; the form is separate |

---

## Data Model Changes

No database or API schema changes. The mapping is purely in the form component:

| Form field | Remote server → API field | Command server → API field |
|------------|--------------------------|---------------------------|
| `urlOrCommand` | `url_or_command` | *(not shown; not sent)* |
| `commandArgs` | `command_args` | **`url_or_command`** |

> For command servers, `commandArgs` is repurposed to store the full package + args string, which maps to `url_or_command` in the request payload. The `command_args` field in the API request is no longer sent by the form for command servers (the concept is collapsed into a single field).

---

## Phase 1: Component Changes

### `form-config-tab.tsx`

#### 1. `buildInitialState` — populate `commandArgs` for command servers

```typescript
// Before
return {
  ...
  urlOrCommand: server.url_or_command || server.url || '',
  commandArgs: server.command_args || '',
};

// After
const isCommand = server.server_type !== 'remote';
return {
  ...
  urlOrCommand: isCommand ? '' : (server.url_or_command || server.url || ''),
  commandArgs: isCommand
    ? (server.url_or_command || '')   // ← url_or_command populates commandArgs for command servers
    : (server.command_args || ''),
};
```

#### 2. `canSubmit` — use `commandArgs` for command servers

```typescript
// Before
const canSubmit =
  form.displayName.trim().length > 0 &&
  form.displayName.trim().length <= 128 &&
  form.urlOrCommand.trim().length > 0;

// After
const hasRequiredValue =
  form.serverType === 'remote'
    ? form.urlOrCommand.trim().length > 0
    : form.commandArgs.trim().length > 0;

const canSubmit =
  form.displayName.trim().length > 0 &&
  form.displayName.trim().length <= 128 &&
  hasRequiredValue;
```

#### 3. `handleSubmit` — map `commandArgs` → `url_or_command` for command servers

```typescript
// In both edit and create branches, for command servers:
url_or_command: form.serverType === 'remote'
  ? form.urlOrCommand.trim()
  : form.commandArgs.trim(),
command_args: form.serverType === 'remote'
  ? (form.commandArgs.trim() || null/undefined)
  : null/undefined,   // command_args not sent for command servers (collapsed into url_or_command)
```

#### 4. Row 2 — hide `urlOrCommand` input for command servers

```tsx
{/* Row 2: URL/Command + Transport */}
<div className="grid grid-cols-2 gap-4">
  {form.serverType === 'remote' && (
    <div className="space-y-2">
      <Label htmlFor="fc-url">Server URL</Label>
      <Input id="fc-url" ... />
    </div>
  )}
  <div className="space-y-2">
    <Label htmlFor="fc-transport">Transport</Label>
    <Select ... />
  </div>
</div>
```

When `serverType === 'command'`, the grid becomes a single-column (Transport only).

#### 5. Command Arguments section — move note to after args input

```tsx
{/* Command Args (Command type only) */}
{form.serverType !== 'remote' && (
  <div className="space-y-2">
    <Label htmlFor="fc-args">Command Arguments</Label>
    <Input
      id="fc-args"
      value={form.commandArgs}
      onChange={(e) => setField('commandArgs', e.target.value)}
      placeholder="@modelcontextprotocol/server-github --api-key $API_KEY"
      disabled={isSaving}
      required
    />
    {/* Note moved here from the old Package/Command field */}
    <p className="text-xs text-muted-foreground">
      Full command:{' '}
      <code className="font-mono">
        {form.commandRunner} {form.commandArgs || '<package or args>'}
      </code>
    </p>
  </div>
)}
```

---

## Phase 1: Test Changes

### `form-config-tab.test.tsx`

#### Tests to update

| Test | Change |
|------|--------|
| `'renders URL label as "Server URL" for remote type'` | No change — still valid |
| `'calls onSave with correct payload when form is submitted'` | No change — remote server only |
| `'populates form fields from initialData in edit mode'` | For remote server — no change; for command server tests, `url_or_command` now pre-populates `commandArgs` input |
| `'includes command_runner in submit payload for command type servers'` | Update: type into `Command Arguments` field (not `Package / Command`) |
| `'shows Command Runner selector when server type is command'` | No change |
| `'does NOT show Command Arguments for remote type'` | No change |

#### Tests to add

```typescript
it('does NOT show Package/Command input for command type servers', () => {
  render(
    <FormConfigTab
      initialData={makeServer({ server_type: 'command', command_runner: 'npx', transport: 'stdio', auth_type: 'none' })}
      onSave={vi.fn()}
      isSaving={false}
    />
  );
  expect(screen.queryByLabelText('Package / Command')).not.toBeInTheDocument();
});

it('pre-populates Command Arguments from url_or_command for command servers in edit mode', () => {
  render(
    <FormConfigTab
      initialData={makeServer({
        server_type: 'command',
        command_runner: 'uvx',
        transport: 'stdio',
        url_or_command: 'mcp-server-git',
        auth_type: 'none',
      })}
      onSave={vi.fn()}
      isSaving={false}
    />
  );
  expect(screen.getByDisplayValue('mcp-server-git')).toBeInTheDocument();
});

it('sends url_or_command from commandArgs field for command servers', async () => {
  const onSave = vi.fn();
  render(
    <FormConfigTab
      initialData={makeServer({
        server_type: 'command',
        command_runner: 'npx',
        transport: 'stdio',
        url_or_command: '@foo/bar',
        auth_type: 'none',
      })}
      onSave={onSave}
      isSaving={false}
    />
  );

  const form = screen.getByLabelText('Server Name').closest('form')!;
  form.dispatchEvent(new Event('submit', { bubbles: true }));

  expect(onSave).toHaveBeenCalledTimes(1);
  const payload = onSave.mock.calls[0]?.[0] as Record<string, unknown>;
  expect(payload.url_or_command).toBe('@foo/bar');
  expect(payload.command_runner).toBe('npx');
  expect(payload.command_args).toBeUndefined();  // or null
});

it('shows full command preview note after args input for command servers', () => {
  render(
    <FormConfigTab
      initialData={makeServer({
        server_type: 'command',
        command_runner: 'npx',
        transport: 'stdio',
        url_or_command: '@foo/bar',
        auth_type: 'none',
      })}
      onSave={vi.fn()}
      isSaving={false}
    />
  );
  // The note appears after Command Arguments
  expect(screen.getByText(/Full command:/)).toBeInTheDocument();
});
```

---

## Affected Files

| File | Change |
|------|--------|
| `frontend/src/features/settings/components/form-config-tab.tsx` | Remove urlOrCommand input for command servers; repurpose commandArgs; move note; update canSubmit + handleSubmit + buildInitialState |
| `frontend/src/features/settings/components/__tests__/form-config-tab.test.tsx` | Update submit payload test for command type; add 4 new tests |

No other files change — the backend API contract, store types, and import logic are unaffected.

---

## Quality Gate Checklist

- [ ] `cd frontend && pnpm type-check` — zero errors
- [ ] `cd frontend && pnpm lint` — zero warnings
- [ ] `cd frontend && pnpm test` — all pass (including new tests)
- [ ] Manual: add command server via form → `url_or_command` stored correctly in DB
- [ ] Manual: edit command server → args field pre-populated from `url_or_command`
- [ ] Manual: remote server form unchanged

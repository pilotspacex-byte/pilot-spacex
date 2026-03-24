# Tasks: Remove Package/Command Input — Use Args Field for Command Servers

**Feature**: MCP Settings — Form UX Simplification
**Branch**: `25-mcp-settings`
**Plan**: `specs/025-mcp-settings/plan-remove-package-input.md`
**Total tasks**: 7
**Affected files**: 2

---

## Phase 1: Implementation

### User Story: Simplify command server form (FR-04)

Goal: Command-type servers use a single `Command Arguments` field (no separate Package/Command input). The helper note appears after the args field. Edit mode pre-populates args from `url_or_command`. Submit maps args → `url_or_command`.

---

- [x] T001 Update `buildInitialState` in `frontend/src/features/settings/components/form-config-tab.tsx` — for command servers (`server_type !== 'remote'`), populate `commandArgs` from `server.url_or_command` and set `urlOrCommand: ''`; for remote servers keep existing logic (`urlOrCommand` from `url_or_command`, `commandArgs` from `command_args`)

- [x] T002 Update `canSubmit` in `frontend/src/features/settings/components/form-config-tab.tsx` — replace `form.urlOrCommand.trim().length > 0` with a type-conditional check: remote → require `urlOrCommand`; command → require `commandArgs`

- [x] T003 Update `handleSubmit` in `frontend/src/features/settings/components/form-config-tab.tsx` — for command servers, send `url_or_command: form.commandArgs.trim()` and omit `command_args` (set to `null`/`undefined`); for remote servers keep existing mapping (`url_or_command: form.urlOrCommand.trim()`, `command_args: form.commandArgs.trim() || undefined`)

- [x] T004 Update Row 2 JSX in `frontend/src/features/settings/components/form-config-tab.tsx` — wrap the `urlOrCommand` Input block in `{form.serverType === 'remote' && (...)}` so it is hidden for command servers; keep Transport Select always visible; remove the inline note `<p>` from inside the `urlOrCommand` block (it moves to T005)

- [x] T005 Update Command Arguments section JSX in `frontend/src/features/settings/components/form-config-tab.tsx` — add `required` to the Input; change `placeholder` to `'@modelcontextprotocol/server-github --api-key $API_KEY'`; add helper `<p>` after the Input reading: `Full command: <code>{form.commandRunner} {form.commandArgs || '<package or args>'}</code>`

---

## Phase 2: Tests

- [x] T006 [P] Update existing test `'includes command_runner in submit payload for command type servers'` in `frontend/src/features/settings/components/__tests__/form-config-tab.test.tsx` — the test currently relies on `url_or_command: 'mcp-server-git'` pre-populating `urlOrCommand`; after T001 it pre-populates `commandArgs` instead, so no userEvent interaction change is needed, but verify the `Command Arguments` input is the one found via `getByDisplayValue('mcp-server-git')`

- [x] T007 [P] Add 4 new tests to `frontend/src/features/settings/components/__tests__/form-config-tab.test.tsx`:
  1. `'does NOT show Package/Command input for command type servers'` — render with `server_type: 'command'`; assert `queryByLabelText('Package / Command')` is null
  2. `'pre-populates Command Arguments from url_or_command for command servers in edit mode'` — render with `url_or_command: 'mcp-server-git'`; assert `getByDisplayValue('mcp-server-git')` is present
  3. `'sends url_or_command from commandArgs field for command servers'` — render command server with `url_or_command: '@foo/bar'`; submit; assert `payload.url_or_command === '@foo/bar'` and `payload.command_args` is undefined
  4. `'shows full command preview note after args input for command servers'` — render command server; assert `getByText(/Full command:/)` is present

---

## Dependencies

```
T001 → T002, T003   (canSubmit and handleSubmit depend on form state shape)
T001 → T006         (test relies on updated buildInitialState)
T004 → T007.1       (test verifies Package/Command input is absent)
T005 → T007.4       (test verifies note is present)
T001, T003 → T007.3 (test verifies submit payload mapping)
```

## Parallel Execution

T006 and T007 can run in parallel after T001–T005 are complete.
T004 and T005 can run in parallel (different JSX blocks in same file — coordinate to avoid conflicts).

## Quality Gate

After all tasks complete:
```bash
cd frontend && pnpm type-check   # zero errors
cd frontend && pnpm lint         # zero warnings
cd frontend && pnpm test         # all pass
```

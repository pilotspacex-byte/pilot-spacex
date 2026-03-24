# Tasks: Command Args Inline with Transport + Move Above Env Vars

**Feature**: MCP Settings — Form Layout Refinement
**Branch**: `25-mcp-settings`
**Total tasks**: 3
**Affected files**: 2

---

## Phase 1: Implementation

### Layout: Command Arguments inline with Transport; above Env Vars

Goal: For command-type servers, the Command Arguments input appears in the same two-column row
as Transport (col 1 = args, col 2 = transport) — mirroring the remote layout of
`[Server URL] [Transport]`. The standalone Command Args section below Env Vars is removed.

---

- [ ] T001 Merge Command Arguments into Row 2 in `frontend/src/features/settings/components/form-config-tab.tsx`:
  - Replace the current Row 2 block (`{/* Row 2: URL (Remote only) + Transport */}`) with a unified grid that conditionally renders either the Server URL input (remote) or the Command Arguments input (command) in col 1, and always renders Transport in col 2.
  - For the command col-1 block: include the `<Label>`, `<Input id="fc-args">`, and the `<p>Full command:…</p>` helper note.
  - Remove the standalone `{/* Command Args (Command type only) */}` section that currently appears after Env Vars.

- [ ] T002 Verify section order in `frontend/src/features/settings/components/form-config-tab.tsx`:
  - After T001, the JSX order for command servers must be:
    1. Row 1: Name + Type
    2. Row 1b: Command Runner
    3. Row 2: [Command Arguments] [Transport]
    4. Env Vars
  - For remote servers the order must be:
    1. Row 1: Name + Type
    2. Row 2: [Server URL] [Transport]
    3. Auth Type / Bearer / OAuth2 / Headers
    4. Env Vars

---

## Phase 2: Tests

- [ ] T003 [P] Update `frontend/src/features/settings/components/__tests__/form-config-tab.test.tsx`:
  - Existing test `'does NOT show Command Arguments for remote type'` — no change needed (still valid).
  - Existing test `'shows full command preview note after args input for command servers'` — still valid.
  - Add test: `'Command Arguments input is rendered in the same grid row as Transport for command servers'` — render with `server_type: 'command'`; assert both `screen.getByLabelText('Command Arguments')` and `screen.getByLabelText('Transport')` are present, and that the Command Arguments input appears before the Transport select in the DOM (use `compareDocumentPosition` or check ordering).

---

## Dependencies

```
T001 → T002 (order verification depends on merge being done)
T001 → T003 (tests depend on updated JSX)
T002 ∥ T003  (verification and tests can run after T001)
```

## Quality Gate

```bash
cd frontend && pnpm type-check   # zero errors
cd frontend && pnpm lint         # zero warnings
cd frontend && pnpm test         # all pass
```

---
phase: 33-remote-mcp-approval
plan: 03
subsystem: frontend-settings
tags: [mcp, approval-mode, settings-ui, mobx, switch-toggle, tdd]
dependency_graph:
  requires: [33-01]
  provides: [approval-mode-toggle-ui, mcp-server-approval-mode-api-client]
  affects: [frontend/src/stores/ai/MCPServersStore.ts, frontend/src/features/settings]
tech_stack:
  added: []
  patterns: [shadcn-switch, mobx-runInAction, tdd-red-green, plain-component-not-observer]
key_files:
  created: []
  modified:
    - frontend/src/stores/ai/MCPServersStore.ts
    - frontend/src/services/api/mcp-servers.ts
    - frontend/src/features/settings/components/mcp-server-card.tsx
    - frontend/src/features/settings/pages/mcp-servers-settings-page.tsx
    - frontend/src/stores/ai/__tests__/MCPServersStore.test.ts
    - frontend/src/features/settings/components/__tests__/mcp-server-card.test.tsx
    - frontend/src/features/settings/pages/__tests__/mcp-servers-settings-page.test.tsx
decisions:
  - "approval_mode field is optional (?) on MCPServer for backwards compat — older API responses that pre-date the column omit it"
  - "Switch placed under the badge row in server info column (not actions column) to keep destructive actions isolated on right"
  - "MCPA-03 requires no new component — InlineApprovalCard handles unknown actionType via GenericJSON fallback; remote_mcp_tool absent from DESTRUCTIVE_ACTIONS"
metrics:
  duration: "~15 minutes"
  completed: "2026-03-19T21:12:51Z"
  tasks_completed: 2
  files_modified: 7
---

# Phase 33 Plan 03: Approval Mode Toggle (Frontend Settings UI) Summary

**One-liner:** shadcn Switch toggle per MCP server card for require_approval/auto_approve with MobX store action and PATCH API client method.

## What Was Built

Full frontend approval mode toggle flow for admin-facing MCP server settings:

1. **MCPServer interface** (`MCPServersStore.ts`): Added optional `approval_mode?: 'auto_approve' | 'require_approval'` field. Optional for backwards compat — servers registered before the column was added won't have the field.

2. **mcpServersApi.updateApprovalMode** (`mcp-servers.ts`): New `PATCH /workspaces/{id}/mcp-servers/{id}/approval-mode` method with typed body `{ approval_mode: mode }`.

3. **MCPServersStore.updateApprovalMode** (`MCPServersStore.ts`): Async action calls API then `runInAction` to update the matching server's `approval_mode` in the observable array. Throws on error (caller handles).

4. **MCPServerCard Switch toggle** (`mcp-server-card.tsx`): shadcn `Switch` component (size="sm") below the badge row. Checked when `approval_mode === 'require_approval'`. Label "Require approval for tool calls". Fires `onUpdateApprovalMode(serverId, mode)` via `onCheckedChange`. Component stays plain (NOT observer per RESEARCH.md pitfall 5).

5. **MCPServersSettingsPage wiring** (`mcp-servers-settings-page.tsx`): `handleUpdateApprovalMode` handler added, calls `mcpStore.updateApprovalMode(workspaceId, serverId, mode)`. Passed as `onUpdateApprovalMode` prop to `MCPServerCard`.

6. **MCPA-03 verification**: `remote_mcp_tool` is absent from `DESTRUCTIVE_ACTIONS` in `ChatView/utils.ts` — `InlineApprovalCard` handles it via GenericJSON fallback. No new chat component needed.

## Tests

All tests follow TDD (RED → GREEN):

| File | Tests | Status |
|------|-------|--------|
| `MCPServersStore.test.ts` | 7 (1 new) | All pass |
| `mcp-server-card.test.tsx` | 8 (3 new in `describe('approval mode toggle')`) | All pass |
| `mcp-servers-settings-page.test.tsx` | 9 (2 new in `describe('onUpdateApprovalMode wiring')`) | All pass |

**Total: 24 tests pass**

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check

- MCPServer interface includes `approval_mode` field: YES (optional field in MCPServersStore.ts)
- MCPServersStore.updateApprovalMode action: YES (calls API + runInAction)
- MCPServerCard Switch toggle rendered: YES (shadcn Switch with aria-label)
- mcp-servers-settings-page onUpdateApprovalMode wired: YES (handleUpdateApprovalMode → mcpStore.updateApprovalMode)
- All 24 new/modified tests pass: YES
- tsc --noEmit: CLEAN (0 errors)
- ESLint: CLEAN (0 errors, pre-existing warnings only in unrelated files)
- MCPA-03 no new component: CONFIRMED (remote_mcp_tool absent from DESTRUCTIVE_ACTIONS)

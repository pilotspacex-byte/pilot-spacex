---
phase: 01-identity-and-access
plan: 08
subsystem: frontend/settings
tags: [settings, sessions, scim, security, tanstack-query]
dependency_graph:
  requires: [01-04, 01-06]
  provides: [security-settings-ui, session-management-ui, scim-token-ui]
  affects: [frontend/settings/pages, frontend/settings/hooks]
tech_stack:
  added: []
  patterns:
    - TanStack Query hooks with 30s polling for live session data
    - AlertDialog for destructive confirm flows (terminate, token rotation)
    - One-time token reveal Dialog (shown once, then dismissed)
    - Plain React component (no observer()) — no MobX observables needed
key_files:
  created:
    - frontend/src/features/settings/hooks/use-sessions.ts
    - frontend/src/features/settings/hooks/use-scim.ts
    - frontend/src/features/settings/pages/security-settings-page.tsx
    - frontend/src/app/(workspace)/[workspaceSlug]/settings/security/page.tsx
    - frontend/src/features/settings/pages/__tests__/security-settings-page.test.tsx
  modified:
    - frontend/src/features/settings/hooks/index.ts
    - frontend/src/features/settings/pages/index.ts
decisions:
  - SecuritySettingsPage is plain React (no observer()) — no MobX observables; TanStack Query handles all data
  - Token reveal uses separate Dialog (not AlertDialog) — allows more content for copy UX
  - Terminate-all shown as inline "All" button in each non-current row — avoids extra expand/collapse complexity (YAGNI)
metrics:
  duration_minutes: 12
  completed_date: "2026-03-07"
  tasks_completed: 1
  files_created: 5
  files_modified: 2
---

# Phase 1 Plan 8: Security Settings Page Summary

SecuritySettingsPage with active sessions table (30s polling, terminate/terminate-all, (you) badge) and SCIM directory sync section (base URL display, one-time token generation with copy UX).

## What Was Built

### use-sessions.ts
Three TanStack Query hooks:
- `useSessions(workspaceSlug)` — lists workspace sessions with 30s `staleTime` + `refetchInterval`
- `useTerminateSession(workspaceSlug)` — DELETE `/workspaces/{slug}/sessions/{id}`, invalidates list
- `useTerminateAllUserSessions(workspaceSlug)` — DELETE `/workspaces/{slug}/sessions/users/{userId}`, invalidates list

### use-scim.ts
- `useGenerateScimToken(workspaceSlug)` — POST `/workspaces/{slug}/settings/scim-token`, returns `{ token, message }`

### security-settings-page.tsx
Two-section layout:

**Active Sessions** — Table with columns: Member (avatar + name), Location (IP), Device (browser + OS + icon), Last Active (relative time), Actions. Current session shows `(you)` Badge, no Terminate button. Non-current sessions show "Terminate session" + "All" buttons that each open AlertDialog before executing. Loading state: 3 skeleton rows. Empty state: text message.

**Directory Sync (SCIM)** — Read-only SCIM Base URL input with copy button. Warning alert: data never deleted on deprovision. "Generate New SCIM Token" button opens confirmation AlertDialog (warns previous token is invalidated), then on confirm shows the raw token once in a Dialog with copy button.

### App Router page
`settings/security/page.tsx` — thin wrapper importing SecuritySettingsPage from barrel.

## Tests (TDD)

8 tests in `security-settings-page.test.tsx`:
1. renders sessions table with mocked data
2. current session shows "(you)" badge
3. current session has no Terminate button
4. non-current session shows Terminate button
5. terminate click shows AlertDialog
6. SCIM URL contains workspace slug
7. "Generate New SCIM Token" button visible
8. token modal shows with copy button after successful mutation

All 8 pass. TypeScript clean. ESLint clean.

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check

### Files Exist
- [x] `frontend/src/features/settings/hooks/use-sessions.ts`
- [x] `frontend/src/features/settings/hooks/use-scim.ts`
- [x] `frontend/src/features/settings/pages/security-settings-page.tsx`
- [x] `frontend/src/app/(workspace)/[workspaceSlug]/settings/security/page.tsx`
- [x] `frontend/src/features/settings/pages/__tests__/security-settings-page.test.tsx`

### Commits Exist
- d253ab5b — test(01-08): TDD RED tests
- 73748b34 — feat(01-08): implementation (GREEN phase)

## Self-Check: PASSED

---
phase: 32-oauth-refresh-flow
plan: 03
subsystem: ui
tags: [mcp, oauth2, badge, mobx, react, lucide-react, typescript]

# Dependency graph
requires:
  - phase: 32-01
    provides: token_expires_at column on WorkspaceMcpServer model and WorkspaceMcpServerResponse schema field
provides:
  - MCPServer TypeScript interface with token_expires_at: string | null
  - ExpiryBadge component in mcp-server-card.tsx showing "Token expired" or "expires in Xh"
  - ExpiryBadge rendered only for oauth2 servers with non-null token_expires_at
affects:
  - mcp-server-settings
  - workspace-admin-ui

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Inline pure-function badge component (ExpiryBadge) co-located in card file, no state required
    - Guard oauth2-only UI with auth_type === 'oauth2' conditional before rendering expiry badge

key-files:
  created: []
  modified:
    - frontend/src/stores/ai/MCPServersStore.ts
    - frontend/src/features/settings/components/mcp-server-card.tsx
    - frontend/src/features/settings/components/__tests__/mcp-server-card.test.tsx
    - frontend/src/stores/ai/__tests__/MCPServersStore.test.ts

key-decisions:
  - "Backend token_expires_at field was already present from Plan 32-01 — Task 1 became verification-only"
  - "ExpiryBadge is a plain function component co-located in mcp-server-card.tsx, not a separate file, following existing AuthTypeBadge/StatusBadge pattern in the same file"
  - "ExpiryBadge shows < 1h granularity with 'expires in <1h' label for sub-hour remaining time"

patterns-established:
  - "Inline badge components: pure functions in same file as parent card, no separate file needed"
  - "oauth2-specific UI: guard with server.auth_type === 'oauth2' in JSX conditional"

requirements-completed:
  - MCPO-03

# Metrics
duration: 8min
completed: 2026-03-20
---

# Phase 32 Plan 03: Token Expiry Badge Summary

**ExpiryBadge component added to MCPServerCard showing OAuth2 token health — expired (destructive) or expires-in-Xh (muted) — wired to token_expires_at from WorkspaceMcpServerResponse**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-20T02:20:00Z
- **Completed:** 2026-03-19T19:23:02Z
- **Tasks:** 2 (Task 1: verification-only; Task 2: frontend changes)
- **Files modified:** 4

## Accomplishments

- Added `token_expires_at: string | null` to MCPServer TypeScript interface (MCPServersStore.ts)
- Added `ExpiryBadge` component to mcp-server-card.tsx with expired/expires-in-Xh display logic
- Rendered ExpiryBadge in badge row, guarded by `server.auth_type === 'oauth2'`
- Updated test fixtures in both test files to include `token_expires_at: null`
- All quality gates pass: `pnpm type-check`, `pnpm lint`, `ruff check`

## Task Commits

1. **Task 1: Backend schema (verification only)** — already complete from Plan 32-01
2. **Task 2: TS type + ExpiryBadge** — `cdfd2fc1` (feat)

## Files Created/Modified

- `frontend/src/stores/ai/MCPServersStore.ts` — Added `token_expires_at: string | null` field to MCPServer interface
- `frontend/src/features/settings/components/mcp-server-card.tsx` — Added AlertCircle/Clock imports, ExpiryBadge component, conditional render in badge row
- `frontend/src/features/settings/components/__tests__/mcp-server-card.test.tsx` — Added `token_expires_at: null` to makeServer fixture
- `frontend/src/stores/ai/__tests__/MCPServersStore.test.ts` — Added `token_expires_at: null` to makeMockServer fixture

## Decisions Made

- Backend `token_expires_at` field was already present in `WorkspaceMcpServerResponse` (added in Plan 32-01). Task 1 became a verification step only.
- `ExpiryBadge` co-located in `mcp-server-card.tsx` following the existing `AuthTypeBadge`/`StatusBadge` pattern in that file — no separate file needed.
- Sub-hour remaining time displays as `expires in <1h` rather than minutes, keeping badge compact.

## Deviations from Plan

None - plan executed exactly as written. The only deviation was that the backend schema change (Task 1) was pre-completed by Plan 32-01, making Task 1 verification-only rather than implementation.

## Issues Encountered

Prettier reformatted `mcp-server-card.tsx` on first commit attempt (pre-commit hook). Re-staged the prettier-formatted file and committed successfully on second attempt.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- ExpiryBadge renders correctly for oauth2 servers; bearer servers show no expiry badge
- MCPO-03 requirement fully satisfied: token_expires_at flows from DB model through Pydantic schema to TypeScript interface to UI badge
- Ready for any remaining Phase 32 OAuth refresh flow plans

---
*Phase: 32-oauth-refresh-flow*
*Completed: 2026-03-20*

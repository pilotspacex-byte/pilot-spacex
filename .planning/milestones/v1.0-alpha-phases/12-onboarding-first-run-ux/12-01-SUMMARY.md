---
phase: 12-onboarding-first-run-ux
plan: "01"
subsystem: ui
tags: [react, nextjs, mobx, supabase, onboarding, workspace, auth]

# Dependency graph
requires: []
provides:
  - "WorkspaceHomePage reads workspaceId from WorkspaceContext (UUID), never from MobX store or slug string"
  - "First-time users auto-redirected to newly created workspace (email-derived name + 4-char random suffix)"
  - "Slug collision on auto-create retries once with a new suffix, then falls back to manual form"
affects:
  - "12-02-PLAN.md (OnboardingChecklist now always receives UUID workspaceId)"
  - "12-03-PLAN.md (auto-create workspace prerequisites satisfied)"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "WorkspaceContext-first: use useWorkspace().workspace.id as UUID source, never store fallback"
    - "Auto-create-with-retry: slug = toSlug(name) + 4-char random suffix, retry once on 409"

key-files:
  created:
    - "frontend/src/app/__tests__/page.test.tsx"
    - "frontend/src/app/(workspace)/[workspaceSlug]/__tests__/page.test.tsx"
  modified:
    - "frontend/src/app/(workspace)/[workspaceSlug]/page.tsx"
    - "frontend/src/app/page.tsx"

key-decisions:
  - "WorkspaceContext is the authoritative workspaceId source — WorkspaceGuard resolves workspace from API before rendering children, guaranteeing UUID availability"
  - "Auto-create uses email prefix as workspace name; slug gets 4-char alphanumeric suffix to reduce collision probability on new accounts"
  - "supabase.auth.getUser() used directly in app/page.tsx (not via AuthProvider) because AuthProvider interface lacks getUser() — avoids interface expansion"
  - "Manual creation wizard retained as fallback path — only shown on double-409 or non-conflict error"

patterns-established:
  - "TDD RED-GREEN: test scaffolds written first (RED), then implementation turns them GREEN"
  - "ApiError mock in vi.mock factory uses full ApiProblemDetails constructor shape to match real class type signature"
  - "act(async () => { render(); await tick(); }) pattern for React 19 Suspense-based params via React.use()"

requirements-completed:
  - BUG-01
  - BUG-02
  - ONBD-01
  - ONBD-02

# Metrics
duration: 25min
completed: 2026-03-09
---

# Phase 12 Plan 01: Fix workspaceId Race Condition and Auto-Create Workspace Summary

**WorkspaceHomePage now reads workspaceId from WorkspaceContext UUID (not MobX store/slug fallback), and first-time users are auto-redirected to an email-derived workspace without seeing a blank creation form**

## Performance

- **Duration:** 25 min
- **Started:** 2026-03-09T15:14:53Z
- **Completed:** 2026-03-09T15:39:00Z
- **Tasks:** 3
- **Files modified:** 4 (2 source + 2 test)

## Accomplishments

- Fixed BUG-01: `useWorkspace().workspace.id` replaces `workspaceStore.currentWorkspace?.id ?? workspaceSlug` — OnboardingChecklist always receives a UUID
- Implemented ONBD-01/BUG-02: `autoCreateWorkspace()` inner function in `resolveWorkspace()` — derives name from email prefix, generates collision-resistant slug with 4-char suffix, retries once on 409
- 5 unit tests written (RED → GREEN via TDD): 3 for ONBD-01 auto-create flow, 2 for BUG-01 context source

## Task Commits

Each task was committed atomically:

1. **Task 1: Create Wave 0 test scaffolds** - `67ff3597` (test)
2. **Task 2: Fix BUG-01 — use WorkspaceContext** - `5d0b7844` (feat)
3. **Task 3: Fix ONBD-01/BUG-02 — auto-create workspace** - `b3cc7ed8` (feat)

## Files Created/Modified

- `frontend/src/app/(workspace)/[workspaceSlug]/page.tsx` - Replaced MobX store workspaceId lookup with `useWorkspace().workspace.id`
- `frontend/src/app/page.tsx` - Added `autoCreateWorkspace()` with retry logic; supabase import for user metadata
- `frontend/src/app/__tests__/page.test.tsx` - 3 tests for ONBD-01 (auto-create, retry on 409, fallback form)
- `frontend/src/app/(workspace)/[workspaceSlug]/__tests__/page.test.tsx` - 2 tests for BUG-01 (UUID from context, not slug)

## Decisions Made

- `useWorkspace()` from WorkspaceGuard is the source of truth for workspaceId — the guard resolves via API before rendering children, making the UUID always available synchronously via context
- `supabase.auth.getUser()` imported directly rather than expanding `AuthProvider` interface — keeps the interface minimal and avoids breaking other providers
- Slug format: `toSlug(displayName)-XXXX` where XXXX is `Math.random().toString(36).slice(2,6)` — 4 alphanumeric chars from base-36 gives 36^4 = 1.68M possibilities, sufficient for first-account collisions
- Manual wizard form retained in JSX as fallback — only rendered when both auto-create attempts fail (double-409 or other error)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] ApiError mock constructor shape mismatch**
- **Found during:** Task 3 (ONBD-01 implementation)
- **Issue:** Real `ApiError` takes `ApiProblemDetails` object, test initially used `(message, status)` signature — TypeScript pre-commit hook rejected with TS2554
- **Fix:** Updated vi.mock factory class to match real constructor: `constructor(problem: { title, status, type? })` — test body updated to `new ApiError({ title: 'Slug taken', status: 409 })`
- **Files modified:** `frontend/src/app/__tests__/page.test.tsx`
- **Verification:** `pnpm type-check` passes; tests GREEN
- **Committed in:** b3cc7ed8 (Task 3 commit)

**2. [Rule 1 - Bug] React Suspense / act() wrapper for React.use(params)**
- **Found during:** Task 2 (BUG-01 test implementation)
- **Issue:** `use(params)` creates a Suspense boundary; tests needed `await act(async () => { render(); await tick(); })` to resolve it
- **Fix:** Wrapped render calls in `act(async () => {...})` in the workspace page test
- **Files modified:** `frontend/src/app/(workspace)/[workspaceSlug]/__tests__/page.test.tsx`
- **Verification:** Tests GREEN; no unhandled suspension warnings
- **Committed in:** 5d0b7844 (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (2 bugs in test setup)
**Impact on plan:** Both auto-fixes were test infrastructure issues, not production code changes. No scope creep.

## Issues Encountered

- `vi.restoreAllMocks()` in `afterEach` was clearing supabase mock implementation between tests — resolved by removing `restoreAllMocks()` (which is for `vi.spyOn` scenarios) and re-asserting mocks in `beforeEach`

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 12-01 prerequisites satisfied: workspaceId is always a UUID, first-time users never see a blank page
- Plan 12-02 (OnboardingChecklist enrichment) can proceed: `workspaceId` prop is now reliably UUID
- Plan 12-03 (auto-create flow polish/testing) can proceed: baseline auto-create logic is implemented

## Self-Check: PASSED

- FOUND: `frontend/src/app/(workspace)/[workspaceSlug]/page.tsx`
- FOUND: `frontend/src/app/page.tsx`
- FOUND: `frontend/src/app/__tests__/page.test.tsx`
- FOUND: `frontend/src/app/(workspace)/[workspaceSlug]/__tests__/page.test.tsx`
- FOUND: `.planning/phases/12-onboarding-first-run-ux/12-01-SUMMARY.md`
- FOUND: commit `67ff3597` (test scaffolds)
- FOUND: commit `5d0b7844` (BUG-01 fix)
- FOUND: commit `b3cc7ed8` (ONBD-01/BUG-02 fix)

---
*Phase: 12-onboarding-first-run-ux*
*Completed: 2026-03-09*

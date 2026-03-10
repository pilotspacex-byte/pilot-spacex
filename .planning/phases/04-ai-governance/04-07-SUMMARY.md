---
phase: 04-ai-governance
plan: "07"
subsystem: ui
tags: [react, tanstack-query, mobx, shadcn-ui, byok, ai-governance, radix-popover]

# Dependency graph
requires:
  - phase: 04-ai-governance
    provides: "AI status endpoint GET /workspaces/{slug}/settings/ai-status, audit log actor_type filter"

provides:
  - "AI rationale popover in ExtractionReviewPanel (Info icon, audit log fetch)"
  - "ReviewCommentCard ai_rationale collapsible section"
  - "AiNotConfiguredBanner component (owner-only, sessionStorage dismiss)"
  - "useAIStatus hook (shared BYOK status query)"
  - "[workspaceSlug]/layout.tsx with banner mounted at workspace level"
  - "PRReviewPanel disabled state when byok_configured=false"

affects: [pr-review, notes, workspace-layout, ai-governance]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "useAIRationale: lazy TanStack Query fetch triggered on Popover open (enabled flag)"
    - "AiNotConfiguredBanner: owner-only guard + sessionStorage dismiss + conditional ai-status fetch"
    - "BYOK disabled state: byokConfigured prop with title tooltip on affected buttons"

key-files:
  created:
    - frontend/src/hooks/use-ai-status.ts
    - frontend/src/components/workspace/ai-not-configured-banner.tsx
    - frontend/src/app/(workspace)/[workspaceSlug]/layout.tsx
  modified:
    - frontend/src/features/notes/components/ExtractionReviewPanel.tsx
    - frontend/src/features/notes/components/__tests__/ExtractionReviewPanel.test.tsx
    - frontend/src/components/integrations/ReviewCommentCard.tsx
    - frontend/src/components/editor/NoteCanvasLayout.tsx
    - frontend/src/features/github/components/pr-review-panel.tsx

key-decisions:
  - "ExtractionReviewPanel rationale popover uses noteId as resource_id (not issue.id — issues not yet persisted at review stage)"
  - "useAIRationale hook uses enabled flag pattern: fetch triggered only when popover opens, not on card render"
  - "AiNotConfiguredBanner queries ai-status only when isOwner=true — avoids unnecessary endpoint calls for non-owners"
  - "workspaceSlug prop added to ExtractionReviewPanel (was only workspaceId UUID before) for audit API routing"
  - "PRReviewPanel byokConfigured prop defaults to true for backward compatibility — existing callers unaffected"
  - "[workspaceSlug]/layout.tsx uses observer() wrapping WorkspaceGuard useWorkspace() context — necessary for MobX isOwner reactivity"

patterns-established:
  - "Lazy popover fetch: useQuery with enabled=popoverOpen && !!resourceId pattern"
  - "BYOK guard: disabled + title tooltip on AI action buttons"
  - "Owner-only UI: check workspaceStore.isOwner before rendering owner-specific controls"

requirements-completed: [AIGOV-05, AIGOV-07]

# Metrics
duration: 21min
completed: 2026-03-08
---

# Phase 4 Plan 07: AI Transparency + BYOK Enforcement UX Summary

**AI rationale popover in ExtractionReviewPanel (audit log fetch via noteId), AI reasoning collapsible in ReviewCommentCard, and AiNotConfiguredBanner mounted at workspace layout level with owner-only visibility and sessionStorage dismiss**

## Performance

- **Duration:** 21 min
- **Started:** 2026-03-08T10:33:00Z
- **Completed:** 2026-03-08T10:54:59Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments

- ExtractionReviewPanel: added Info icon popover on each review card; lazy-fetches AI rationale from audit log (resource_id=noteId — not issue.id which isn't persisted yet); `useAIRationale` hook with 5min staleTime; `workspaceSlug` prop added
- ReviewCommentCard: added optional `ai_rationale` field to `ReviewComment` interface; collapsible "AI reasoning" section below comment body (conditionally rendered)
- BYOK enforcement: `useAIStatus` shared hook, `AiNotConfiguredBanner` (owner-only, sessionStorage dismiss), `[workspaceSlug]/layout.tsx` mounting banner at workspace scope, `PRReviewPanel` disabled state with tooltip

## Task Commits

1. **Task 1: AI rationale display** - `5bb60834` (feat)
2. **Task 2: BYOK enforcement UX** - `c48e9d8b` (feat)

## Files Created/Modified

- `frontend/src/hooks/use-ai-status.ts` - Shared useAIStatus TanStack Query hook, queries GET /workspaces/{slug}/settings/ai-status
- `frontend/src/components/workspace/ai-not-configured-banner.tsx` - AiNotConfiguredBanner component (owner-only, dismissable)
- `frontend/src/app/(workspace)/[workspaceSlug]/layout.tsx` - Workspace-slug-level layout that mounts the banner
- `frontend/src/features/notes/components/ExtractionReviewPanel.tsx` - Added Info icon + Popover, useAIRationale hook, workspaceSlug prop
- `frontend/src/features/notes/components/__tests__/ExtractionReviewPanel.test.tsx` - Added workspaceSlug to defaultProps, mocked apiClient and useQuery, added AIGOV-07 test
- `frontend/src/components/integrations/ReviewCommentCard.tsx` - Added ai_rationale to ReviewComment interface, added AI reasoning Collapsible
- `frontend/src/components/editor/NoteCanvasLayout.tsx` - Wired workspaceSlug prop to ExtractionReviewPanel
- `frontend/src/features/github/components/pr-review-panel.tsx` - Added byokConfigured prop, disabled buttons with tooltip

## Decisions Made

- ExtractionReviewPanel rationale uses `noteId` as `resource_id` (not `issue.id`) because extracted issues are not yet persisted to the DB at the review stage — using issue.id would return empty audit results
- `useAIRationale` fetch is gated by `enabled: rationalePopoverOpen && !!resourceId` — query fires only when popover is opened, minimizing API calls
- `AiNotConfiguredBanner` passes empty string to `useAIStatus` when `!isOwner` (disabled query) to avoid fetching AI status for non-owners
- `[workspaceSlug]/layout.tsx` created as new file (did not exist) rather than modifying `(workspace)/layout.tsx` — keeps workspace-slug-specific concerns scoped to the correct route segment
- `PRReviewPanel.byokConfigured` defaults to `true` for backward compatibility — all existing callers work without modification

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Test mocks for new useQuery + apiClient dependencies**
- **Found during:** Task 1 (ExtractionReviewPanel changes)
- **Issue:** Adding `useQuery` and `apiClient` imports to ExtractionReviewPanel would cause test failures — tests render the component but have no mock for the network calls
- **Fix:** Added `vi.mock('@/services/api/client', ...)` and `vi.mock('@tanstack/react-query', ...)` partial mock in the test file; `useQuery` returns `{ data: null, isLoading: false }` to simulate loaded state
- **Files modified:** `ExtractionReviewPanel.test.tsx`
- **Verification:** 16/16 ExtractionReviewPanel tests pass
- **Committed in:** `5bb60834` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 missing critical — test mocks)
**Impact on plan:** Essential for test correctness. No scope creep.

## Issues Encountered

- `[workspaceSlug]/layout.tsx` did not exist (plan referenced it as a file to modify). Created as new file mounting the banner. The workspace guard context (`useWorkspace()`) is available because this route segment is nested under the `(workspace)` layout that renders `WorkspaceGuard`.

## Next Phase Readiness

- AIGOV-05 and AIGOV-07 complete — all 7 Phase 4 plans done
- Phase 4 (AI Governance) fully implemented: approval policies, cost tracking, audit integration, BYOK enforcement, rationale transparency
- Ready for Phase 5 (final phase)

---
*Phase: 04-ai-governance*
*Completed: 2026-03-08*

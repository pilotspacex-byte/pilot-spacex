---
phase: 04-ai-governance
plan: "05"
subsystem: ui
tags: [next.js, react, tanstack-query, shadcn-ui, approvals, ai-governance, mobx]

requires:
  - phase: 04-04
    provides: ai_governance.py router (GET/PUT policy, AI status, rollback endpoints)
  - phase: 04-01
    provides: ai_approvals.py endpoints (list, resolve) + approvalsApi service

provides:
  - Approvals queue page at /[workspaceSlug]/approvals with Pending/Expired tabs
  - ApprovalRow expandable component with Approve/Reject workflow
  - useApprovals / usePendingApprovalCount / useResolveApproval TanStack Query hooks
  - AI Governance settings page at /[workspaceSlug]/settings/ai-governance
  - Policy matrix (4 roles × N actions) with optimistic cell toggles
  - Sidebar Approvals nav item (adminOnly, pending badge, CheckCircle2 icon)

affects:
  - sidebar navigation
  - settings layout nav
  - ai-governance phase completion

tech-stack:
  added: []
  patterns:
    - useResolveApproval mutation proxies to approvalsApi.approve/reject (not raw apiClient)
    - Optimistic updates with rollback via onMutate/onError in useSetAIPolicy
    - adminOnly nav items filtered via isAdminOrOwner computed from workspaceStore.currentUserRole
    - badgeKey indirection pattern for dynamic sidebar badge counts (avoids coupling sidebar to specific hooks)

key-files:
  created:
    - frontend/src/features/approvals/hooks/use-approvals.ts
    - frontend/src/features/approvals/components/approval-row.tsx
    - frontend/src/features/approvals/pages/approvals-page.tsx
    - frontend/src/app/(workspace)/[workspaceSlug]/approvals/page.tsx
    - frontend/src/features/settings/pages/ai-governance-settings-page.tsx
    - frontend/src/app/(workspace)/[workspaceSlug]/settings/ai-governance/page.tsx
  modified:
    - frontend/src/components/layout/sidebar.tsx
    - frontend/src/app/(workspace)/[workspaceSlug]/settings/layout.tsx
    - frontend/src/features/settings/pages/index.ts
    - frontend/src/components/layout/__tests__/sidebar-navigation.test.tsx

key-decisions:
  - "useResolveApproval delegates to approvalsApi.approve/reject (not raw apiClient.post) — reuses existing workspace-slug-agnostic API service that maps backend flat format to PendingApproval"
  - "Sidebar Approvals item uses badgeKey indirection (not direct hook call in static array) — keeps navigationSections as a static constant while allowing dynamic badge injection at render time"
  - "adminOnly nav items filtered via workspaceStore.currentUserRole in Sidebar observer — same store already used for canCreateContent check; no new auth layer needed"
  - "AI policy matrix uses optimistic onMutate with rollback on error — immediate UI feedback for toggle switches, no loading state flicker"
  - "AIGovernanceSettingsPage uses inline useAIPolicy/useSetAIPolicy hooks (not a separate hooks file) — page fits under 300 lines with hooks inline"
  - "ApprovalsPage uses workspaceStore.getWorkspaceBySlug for workspaceId — consistent with sidebar pattern; approvalsApi ignores workspaceId param (backend uses JWT context)"

patterns-established:
  - "Approvals feature pattern: hooks/use-approvals.ts + components/approval-row.tsx + pages/approvals-page.tsx"
  - "Settings page pattern: plain React (no observer), useParams for slug, TanStack Query for data"
  - "Policy matrix cell pattern: locked Badge for ALWAYS_REQUIRE, greyed Badge for OWNER, Switch with label for configurable cells"

requirements-completed:
  - AIGOV-01
  - AIGOV-02

duration: 25min
completed: 2026-03-08
---

# Phase 4 Plan 05: AI Governance Frontend Summary

**Approvals queue page with expandable Approve/Reject rows and AI Governance settings page with 4-role policy matrix and optimistic switch toggles**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-03-08T17:20:00Z
- **Completed:** 2026-03-08T17:45:00Z
- **Tasks:** 2
- **Files modified:** 10

## Accomplishments

- Approvals queue page (`/[workspaceSlug]/approvals`) with Pending/Expired tabs, expandable rows showing JSON payload, Approve button and Reject dialog with optional reason
- AI Governance settings page (`/[workspaceSlug]/settings/ai-governance`) with policy matrix table: ALWAYS_REQUIRE rows locked with destructive badge, Owner column read-only, other cells are Switch toggles with optimistic updates
- Sidebar extended with Approvals nav item (adminOnly, pending count badge, hidden when 0, hidden from non-Owner/Admin roles)

## Task Commits

1. **Task 1: Approvals page + sidebar nav item** - `746905c7` (feat)
2. **Task 2: AI Governance settings page** - `3df3c9e4` (feat)

## Files Created/Modified

- `frontend/src/features/approvals/hooks/use-approvals.ts` — useApprovals, usePendingApprovalCount, useResolveApproval TanStack Query hooks
- `frontend/src/features/approvals/components/approval-row.tsx` — Expandable table row with Approve/Reject (Reject has Dialog + optional reason Textarea)
- `frontend/src/features/approvals/pages/approvals-page.tsx` — ApprovalsPage with Pending/Expired Tabs, ApprovalTable sub-component, skeleton loading
- `frontend/src/app/(workspace)/[workspaceSlug]/approvals/page.tsx` — App Router route wrapper
- `frontend/src/features/settings/pages/ai-governance-settings-page.tsx` — AIGovernanceSettingsPage with policy matrix, useAIPolicy + useSetAIPolicy hooks with optimistic updates
- `frontend/src/app/(workspace)/[workspaceSlug]/settings/ai-governance/page.tsx` — App Router settings route wrapper
- `frontend/src/components/layout/sidebar.tsx` — Added NavItem.badgeKey/adminOnly fields, Approvals item, usePendingApprovalCount integration, badge rendering in expanded/collapsed states
- `frontend/src/app/(workspace)/[workspaceSlug]/settings/layout.tsx` — Added AI Governance nav entry (ShieldCheck icon)
- `frontend/src/features/settings/pages/index.ts` — Added AIGovernanceSettingsPage export
- `frontend/src/components/layout/__tests__/sidebar-navigation.test.tsx` — Added mocks for usePendingApprovalCount and currentUserRole/currentWorkspaceId fields

## Decisions Made

- useResolveApproval delegates to existing `approvalsApi.approve/reject` rather than raw `apiClient.post` — the existing service handles backend format differences (uses `approved: bool` not `action: string`)
- Sidebar uses `badgeKey` indirection in the static nav definition — the Sidebar observer resolves badge values at render time via a `badgeValues` map, keeping the nav structure as a pure constant
- AI policy matrix optimistic updates: `onMutate` flips the cell immediately and `onError` rolls back — avoids loading spinner on each Switch toggle
- ApprovalsPage is plain React (not observer()) — consistent with all settings pages; workspaceStore accessed via `useWorkspaceStore()` hook which is fine in non-observer components for reading non-reactive values at render time

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Fixed sidebar test mocks for new hook dependency**
- **Found during:** Task 1 (after sidebar changes)
- **Issue:** sidebar-navigation.test.tsx didn't mock `@/features/approvals/hooks/use-approvals` or provide `currentUserRole` in the workspaceStore mock — all 16 tests failed
- **Fix:** Added `vi.mock('@/features/approvals/hooks/use-approvals', ...)` returning `usePendingApprovalCount: () => 0`, and added `currentUserRole: 'owner'`, `currentWorkspaceId`, `isOwner`, `isAdmin` to the store mock
- **Files modified:** `src/components/layout/__tests__/sidebar-navigation.test.tsx`
- **Verification:** All 16 sidebar tests pass; overall failing tests count decreased by 1 file (44 → 43, all remaining failures are pre-existing)
- **Committed in:** `746905c7`

---

**Total deviations:** 1 auto-fixed (Rule 2 - missing test mock for new dependency)
**Impact on plan:** Necessary to maintain passing tests. No scope creep.

## Issues Encountered

- Pre-existing: 43 test files had pre-existing failures unrelated to this plan (pre-existing before this session). No new failures introduced.

## Next Phase Readiness

- AIGOV-01 and AIGOV-02 requirements satisfied
- Approvals route and AI Governance settings route are live
- Sidebar badge will show live pending count for Owner/Admin roles
- Ready for Phase 4 wave 5 plans (04-06: BYOK enforcement, 04-07: frontend wiring)

## Self-Check: PASSED

All 6 created files found on disk. Both task commits (746905c7, 3df3c9e4) verified in git log.

---
*Phase: 04-ai-governance*
*Completed: 2026-03-08*

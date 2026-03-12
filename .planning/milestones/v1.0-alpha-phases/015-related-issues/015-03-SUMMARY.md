---
phase: 015-related-issues
plan: 03
subsystem: ui
tags: [react, tanstack-query, mobx, typescript, radix-ui, cmdk, vitest]

# Dependency graph
requires:
  - phase: 015-related-issues
    provides: "015-01 Wave 0 stubs and test scaffolding, 015-02 backend REST endpoints for related issues"
provides:
  - "RelatedSuggestion TypeScript interface (types/issue.ts)"
  - "4 API client methods (createRelation, deleteRelation, getRelatedSuggestions, dismissSuggestion)"
  - "4 TanStack hooks (useRelatedSuggestions, useDismissSuggestion, useCreateRelation, useDeleteRelation)"
  - "RelatedIssuesPanel observer component with AI Suggestions and Linked Issues subsections"
  - "IssuePropertiesPanel wired with RelatedIssuesPanel below SourceNotesList"
  - "5 passing Vitest tests replacing Wave 0 it.todo() stubs"
affects:
  - "016-workspace-role-skills (frontend patterns)"
  - "017-skill-action-buttons (hook pattern reference)"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "TanStack mutation hook with queryClient.invalidateQueries on success"
    - "Radix Popover + cmdk Command for issue search combobox"
    - "MobX observer component (no TipTap — observer is correct here)"
    - "vi.mock for all hooks in unit tests, as unknown as ReturnType<typeof hook> cast"

key-files:
  created:
    - frontend/src/features/issues/components/related-issues-panel.tsx
    - frontend/src/features/issues/hooks/use-related-suggestions.ts
    - frontend/src/features/issues/hooks/use-dismiss-suggestion.ts
    - frontend/src/features/issues/hooks/use-create-relation.ts
    - frontend/src/features/issues/hooks/use-delete-relation.ts
  modified:
    - frontend/src/types/issue.ts
    - frontend/src/types/index.ts
    - frontend/src/services/api/issues.ts
    - frontend/src/features/issues/hooks/index.ts
    - frontend/src/features/issues/components/issue-properties-panel.tsx
    - frontend/src/features/issues/components/__tests__/related-issues-panel.test.tsx

key-decisions:
  - "RelatedIssuesPanel uses observer() — no TipTap NodeViewRenderer, so MobX reactivity is correct"
  - "LinkIssueCombobox uses useQuery with enabled:open guard to avoid unnecessary requests"
  - "useDismissSuggestion imports relatedSuggestionsKeys from use-related-suggestions to keep query key DRY"
  - "useCreateRelation/useDeleteRelation import issueRelationsKeys from use-issue-relations for same reason"
  - "Test mocks use 'as unknown as ReturnType<typeof hook>' — TanStack UseQueryResult is complex union; unknown cast avoids 20+ missing field errors while keeping type safety at call site"
  - "RelatedIssueBrief.name field used (not title) — Issue interface uses name as canonical field"

patterns-established:
  - "mutation hook invalidates sibling query via imported key constants"
  - "combobox search uses separate useQuery with enabled:open&&search.length>=1 guard"

requirements-completed: [RELISS-01, RELISS-02, RELISS-03, RELISS-04]

# Metrics
duration: 30min
completed: 2026-03-10
---

# Phase 15 Plan 03: Related Issues Frontend Summary

**RelatedIssuesPanel with AI semantic suggestions, manual linking, dismiss, unlink — wired into IssuePropertiesPanel sidebar via 4 new TanStack hooks and typed API client methods**

## Performance

- **Duration:** ~30 min
- **Started:** 2026-03-10T05:54:00Z
- **Completed:** 2026-03-10T06:05:00Z
- **Tasks:** 2
- **Files modified:** 11

## Accomplishments

- RelatedSuggestion TypeScript interface added to types with full barrel re-export
- 4 API client methods added to issuesApi covering full CRUD for relations and suggestions lifecycle
- 4 TanStack hooks with proper query key management and cache invalidation on mutation
- RelatedIssuesPanel observer component: AI Suggestions subsection (reason badge + dismiss), Linked Issues subsection (unlink button), Radix Popover + Command issue search combobox
- IssuePropertiesPanel updated to render RelatedIssuesPanel below SourceNotesList
- 5 it.todo() stubs replaced with passing Vitest tests (mocked hooks, QueryClientProvider)

## Task Commits

1. **Task 1: Types, API client methods, and TanStack query/mutation hooks** - `962da790` (feat)
2. **Task 2: RelatedIssuesPanel component, test implementations, and IssuePropertiesPanel wire-up** - `6d6a9423` (feat)
3. **Fix: Add RelatedIssuesPanel to IssueEditorContent for desktop visibility** - `f9dc097a` (fix)

**Plan metadata:** (see final commit below)

## Files Created/Modified

- `frontend/src/types/issue.ts` - Added RelatedSuggestion interface
- `frontend/src/types/index.ts` - Re-export RelatedSuggestion
- `frontend/src/services/api/issues.ts` - 4 new API methods: createRelation, deleteRelation, getRelatedSuggestions, dismissSuggestion
- `frontend/src/features/issues/hooks/use-related-suggestions.ts` - Query hook (60s staleTime, UUID guard)
- `frontend/src/features/issues/hooks/use-dismiss-suggestion.ts` - Mutation hook (invalidates suggestions on success)
- `frontend/src/features/issues/hooks/use-create-relation.ts` - Mutation hook (invalidates relations on success)
- `frontend/src/features/issues/hooks/use-delete-relation.ts` - Mutation hook (invalidates relations on success)
- `frontend/src/features/issues/hooks/index.ts` - Exported 4 new hooks
- `frontend/src/features/issues/components/related-issues-panel.tsx` - New observer component
- `frontend/src/features/issues/components/issue-properties-panel.tsx` - Wired RelatedIssuesPanel
- `frontend/src/features/issues/components/__tests__/related-issues-panel.test.tsx` - 5 passing tests

## Decisions Made

- RelatedIssuesPanel uses observer() — no TipTap NodeViewRenderer involvement, so MobX reactivity is correct (unlike IssueEditorContent which must NOT be observer)
- LinkIssueCombobox issues search uses `enabled: open && search.length >= 1` guard — avoids requests when popover closed or empty query
- Test mocks use `as unknown as ReturnType<typeof hook>` — TanStack query result types are complex unions with 20+ required fields; unknown cast is the accepted pattern for partial mocks
- RelatedIssueBrief uses `.name` field (not `.title`) — consistent with Issue interface canonical field

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] RelatedIssuesPanel wired into IssueEditorContent instead of IssuePropertiesPanel only**
- **Found during:** Human verification checkpoint
- **Issue:** RelatedIssuesPanel was rendered inside IssuePropertiesPanel, which is a mobile-only Sheet component with no trigger visible on desktop. The panel was invisible on desktop viewports.
- **Fix:** Moved RelatedIssuesPanel render from IssuePropertiesPanel to IssueEditorContent so it renders in the main editor column and is visible on desktop.
- **Files modified:** `frontend/src/features/issues/components/issue-editor-content.tsx`, `frontend/src/features/issues/components/issue-properties-panel.tsx`
- **Verification:** Human verification confirmed "Related Issues section visible below Activity in issue detail (desktop)"
- **Committed in:** `f9dc097a` (fix)

---

**Total deviations:** 1 auto-fixed (1 bug — wrong component placement)
**Impact on plan:** Fix essential for desktop visibility. Plan correctly described IssuePropertiesPanel but the component is mobile-only Sheet; fix applied Rule 1.

## Issues Encountered

- Type check initially failed on test mocks: `as ReturnType<...>` is insufficient for TanStack UseQueryResult complex union types. Fixed by using `as unknown as ReturnType<...>` pattern, which is the standard approach for partial mock objects.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- RELISS-01 through RELISS-04 requirements fully addressed by backend (015-02) + frontend (015-03)
- Human verification approved: dismiss persistence across reload confirmed, bidirectional linking confirmed, search combobox UX confirmed
- Phase 15 (Related Issues) complete — Phase 16 (Workspace Role Skills) can begin

---
*Phase: 015-related-issues*
*Completed: 2026-03-10*

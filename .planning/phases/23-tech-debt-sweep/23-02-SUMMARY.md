---
phase: 23-tech-debt-sweep
plan: 02
subsystem: ui
tags: [react, vitest, tailwind, ai-settings, plugin-card]

requires:
  - phase: 13-ai-provider-config
    provides: AISettingsStore with validateKey, plugin card components
provides:
  - Amber-colored Update Available badge in plugin-card and plugin-detail-sheet
  - validateKey supporting all 6 provider types (anthropic, openai, google, kimi, glm, custom)
affects: [ai-settings, plugin-management]

tech-stack:
  added: []
  patterns: [length-only validation for providers without known key prefixes]

key-files:
  created: []
  modified:
    - frontend/src/features/settings/components/plugin-card.tsx
    - frontend/src/features/settings/components/plugin-detail-sheet.tsx
    - frontend/src/features/settings/components/__tests__/plugin-card.test.tsx
    - frontend/src/stores/ai/AISettingsStore.ts
    - frontend/src/features/settings/components/api-key-form.tsx
    - frontend/src/stores/ai/__tests__/AISettingsStore.test.ts

key-decisions:
  - "Unknown/future providers pass validateKey with length check only (permissive default)"
  - "Google key prefix check uses AIza (4 chars) matching GCP API key format"

patterns-established: []

requirements-completed: [AIPR-05]

duration: 4min
completed: 2026-03-12
---

# Phase 23 Plan 02: Frontend Tech Debt - Badge Color and ValidateKey Summary

**Amber Update Available badges and validateKey extended to all 6 provider types (anthropic, openai, google, kimi, glm, custom)**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-12T04:47:18Z
- **Completed:** 2026-03-12T04:51:29Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Fixed Update Available badge from blue-500 to amber-500 in plugin-card and plugin-detail-sheet
- Extended AISettingsStore.validateKey from 2 providers to all 6 LLMProvider types plus unknown
- Added 12 new unit tests (4 plugin-card + 8 validateKey)

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix Update Available badge color blue -> amber** - `985362a2` (fix)
2. **Task 2: Extend AISettingsStore.validateKey for all provider types** - `63184985` (feat)

## Files Created/Modified
- `frontend/src/features/settings/components/plugin-card.tsx` - Changed Update badge from blue-500 to amber-500
- `frontend/src/features/settings/components/plugin-detail-sheet.tsx` - Changed Update button from blue-500 to amber-500
- `frontend/src/features/settings/components/__tests__/plugin-card.test.tsx` - Added 4 tests: amber class assertion, no-update hidden, inactive opacity
- `frontend/src/stores/ai/AISettingsStore.ts` - Widened validateKey to accept string, added google/kimi/glm/custom cases
- `frontend/src/features/settings/components/api-key-form.tsx` - Updated validateKey type from union to string
- `frontend/src/stores/ai/__tests__/AISettingsStore.test.ts` - Added 8 tests for all provider validation paths

## Decisions Made
- Unknown/future providers pass validateKey with length check only (permissive default avoids blocking new providers)
- Google key prefix check uses `AIza` (4 chars) matching standard GCP API key format

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All frontend tech debt items in plan 02 resolved
- Plugin card and AI settings store ready for additional provider integrations

---
*Phase: 23-tech-debt-sweep*
*Completed: 2026-03-12*

## Self-Check: PASSED

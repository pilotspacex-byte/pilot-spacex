---
phase: 34-file-preview-modal
plan: 01
subsystem: ui
tags: [papaparse, tanstack-query, mime-routing, vitest, typescript]

# Dependency graph
requires:
  - phase: 32-inline-editor-features
    provides: artifactKeys query key pattern and ArtifactStore for context
  - phase: 31-storage-backend
    provides: Supabase Storage signed URL generation (60-min expiry)
provides:
  - resolveRenderer(mimeType, filename) → RendererType pure function
  - getLanguageForFile(filename) → lowlight language string
  - useFileContent(signedUrl, rendererType, open) hook with isExpired flag
  - artifactKeys query key factory
  - PREV-01 through PREV-05 test scaffolds (17 todo tests)
affects:
  - 34-file-preview-modal/34-02 (Plan 02 builds renderer components against these contracts)
  - 35-artifacts-page (uses FilePreviewModal)

# Tech tracking
tech-stack:
  added:
    - papaparse 5.5.3 (CSV parsing, used in Plan 02 CsvRenderer)
    - "@types/papaparse 5.5.2"
  patterns:
    - TanStack Query key factory pattern (artifactKeys mirrors notesKeys from useNotes.ts)
    - fetch() directly for signed URLs (never apiClient — avoids Authorization header conflict)
    - RendererType discriminated union routing all renderer decisions through one pure function
    - HTML → code renderer routing (XSS prevention: escaped source, never live render)

key-files:
  created:
    - frontend/src/features/artifacts/utils/mime-type-router.ts
    - frontend/src/features/artifacts/hooks/useFileContent.ts
    - frontend/src/features/artifacts/utils/__tests__/mime-type-router.test.ts
    - frontend/src/features/artifacts/components/__tests__/FilePreviewModal.test.tsx
    - frontend/src/features/artifacts/components/__tests__/CsvRenderer.test.tsx
  modified:
    - frontend/package.json (papaparse + @types/papaparse added)
    - frontend/pnpm-lock.yaml

key-decisions:
  - "HTML always routes to 'code' renderer — never live render HTML from storage (XSS prevention)"
  - "fetch() directly for signed URL content, NOT apiClient — apiClient injects Authorization header that Supabase Storage rejects with 403"
  - "staleTime: 55 minutes (signed URLs expire at 60 min); retry: false (403 = expired, not transient)"
  - "isExpired flag derived from error.message === 'URL_EXPIRED' — enables specific UI feedback"
  - "CsvRenderer scaffold omits parseCSV import (forward ref to Plan 02) — keeps pnpm type-check passing"
  - "Extension-first routing: filename extension wins over generic text/plain MIME for csv/md/json/html"

patterns-established:
  - "Artifact query keys: artifactKeys.fileContent(signedUrl) scoped to URL for per-file cache isolation"
  - "shouldFetch guard: open && !!signedUrl && rendererType not in ['image', 'download']"
  - "RendererType routing priority: image > csv > markdown > json > html(code) > text/* > download"

requirements-completed:
  - PREV-01
  - PREV-02
  - PREV-03
  - PREV-04
  - PREV-05

# Metrics
duration: 10min
completed: 2026-03-19
---

# Phase 34 Plan 01: File Preview Modal — Utility & Hook Layer Summary

**papaparse installed + mime-type-router pure function + useFileContent TanStack Query hook with fetch() and isExpired, all renderer PREV test scaffolds committed**

## Performance

- **Duration:** 10 min
- **Started:** 2026-03-19T14:52:11Z
- **Completed:** 2026-03-19T15:02:11Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments

- Created `features/artifacts/` directory structure with utils/, hooks/, components/__tests__/
- Implemented `resolveRenderer()` with 7 routing cases including HTML→code (XSS prevention) and 56 passing tests
- Implemented `useFileContent()` hook using fetch() directly (not apiClient) with 55-min staleTime, retry:false, isExpired flag
- Scaffolded PREV-01 through PREV-05 test requirements (17 todo tests) ready for Plan 02 implementation

## Task Commits

1. **Task 1: Install papaparse and create mime-type-router utility** - `0a483a14` (feat)
2. **Task 2: Create useFileContent hook and test scaffolds** - `b4f9e003` (feat)

**Plan metadata:** (see final docs commit)

_Note: Task 1 used TDD — tests written (RED) before implementation (GREEN). One auto-fix applied (TypeScript strict mode `noUncheckedIndexedAccess` for `parts[n]`)._

## Files Created/Modified

- `frontend/src/features/artifacts/utils/mime-type-router.ts` - Pure MIME-type to RendererType routing, getLanguageForFile extension mapping
- `frontend/src/features/artifacts/hooks/useFileContent.ts` - TanStack Query hook for signed URL content fetch
- `frontend/src/features/artifacts/utils/__tests__/mime-type-router.test.ts` - 56 passing tests for all routing cases
- `frontend/src/features/artifacts/components/__tests__/FilePreviewModal.test.tsx` - Scaffold: PREV-01, PREV-02, PREV-03, PREV-05 (11 todo)
- `frontend/src/features/artifacts/components/__tests__/CsvRenderer.test.tsx` - Scaffold: PREV-04 (6 todo)
- `frontend/package.json` - papaparse 5.5.3, @types/papaparse 5.5.2 added
- `frontend/pnpm-lock.yaml` - lockfile updated

## Decisions Made

- **fetch() not apiClient**: Supabase Storage signed URLs embed auth token in URL query string; apiClient injects `Authorization: Bearer` header which Storage rejects with 403.
- **staleTime 55 minutes**: Signed URLs expire at 60 minutes; 55-min staleTime ensures cache is invalidated before URL expires.
- **retry: false**: A 403 from a signed URL means it expired — retrying the same URL won't help. Show "Link expired" UI immediately.
- **HTML → code routing**: text/html and .html/.htm extensions always route to the code renderer (escaped source view). Never render live HTML from storage — prevents XSS.
- **Extension-first priority for ambiguous MIME**: text/plain with .csv → csv; text/plain with .md → markdown; text/plain with .json → json. Filename extension overrides generic MIME type.
- **CsvRenderer scaffold without parseCSV import**: The plan note explicitly says parseCSV belongs in Plan 02 alongside CsvRenderer. Removed the forward-reference import to keep `pnpm type-check` passing (consistent with established scaffold pattern).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed TypeScript strict mode error in getExtension()**
- **Found during:** Task 1 (after implementing mime-type-router.ts, running pnpm type-check)
- **Issue:** `parts[parts.length - 1]` typed as `string | undefined` under `noUncheckedIndexedAccess` — TS2532
- **Fix:** Added intermediate variable with explicit undefined guard: `const last = parts[parts.length - 1]; return last !== undefined ? last.toLowerCase() : '';`
- **Files modified:** `frontend/src/features/artifacts/utils/mime-type-router.ts`
- **Verification:** `pnpm type-check` exits 0
- **Committed in:** `0a483a14` (Task 1 commit)

**2. [Rule 1 - Bug] Removed forward-reference parseCSV import from CsvRenderer scaffold**
- **Found during:** Task 2 (after creating CsvRenderer.test.tsx, running pnpm type-check)
- **Issue:** Plan template included `import { parseCSV } from '../../utils/mime-type-router'` but parseCSV doesn't exist yet (Plan 02 adds it). This caused TS2305 + TS6133 errors.
- **Fix:** Removed the import line from scaffold; added comment documenting Plan 02 will add it.
- **Files modified:** `frontend/src/features/artifacts/components/__tests__/CsvRenderer.test.tsx`
- **Verification:** `pnpm type-check` exits 0; 17 todo tests appear as pending in vitest
- **Committed in:** `b4f9e003` (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (2 Rule 1 - TypeScript correctness)
**Impact on plan:** Both fixes essential for TypeScript compliance. No scope creep. The parseCSV import removal is consistent with plan note explicitly calling out this forward reference.

## Issues Encountered

- Prettier pre-commit hook reformatted `useFileContent.ts` (removed extra comment alignment spaces). Staged re-formatted files and committed successfully on second attempt.

## Next Phase Readiness

- `resolveRenderer()` and `getLanguageForFile()` are complete and tested — Plan 02 can import them immediately
- `useFileContent()` hook is ready — Plan 02 FilePreviewModal uses it as the data layer
- 17 todo test scaffolds are in place — Plan 02 replaces todos with full test implementations
- `papaparse` is installed — Plan 02 CsvRenderer can `import Papa from 'papaparse'` immediately
- No blockers for Plan 02

## Self-Check: PASSED

All files confirmed present:
- FOUND: `frontend/src/features/artifacts/utils/mime-type-router.ts`
- FOUND: `frontend/src/features/artifacts/hooks/useFileContent.ts`
- FOUND: `frontend/src/features/artifacts/utils/__tests__/mime-type-router.test.ts`
- FOUND: `frontend/src/features/artifacts/components/__tests__/FilePreviewModal.test.tsx`
- FOUND: `frontend/src/features/artifacts/components/__tests__/CsvRenderer.test.tsx`

All commits confirmed:
- FOUND: `0a483a14` (Task 1 — mime-type-router + papaparse)
- FOUND: `b4f9e003` (Task 2 — useFileContent + test scaffolds)

Note: `apiClient` references in useFileContent.ts are comments-only (explaining why NOT to use it). No actual import or usage of apiClient.

---
*Phase: 34-file-preview-modal*
*Completed: 2026-03-19*

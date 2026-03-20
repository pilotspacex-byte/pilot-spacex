---
phase: 32-inline-editor-features
plan: 01
subsystem: ui
tags: [mobx, tiptap, typescript, artifacts, file-upload, xhr]

requires:
  - phase: 31-storage-backend
    provides: "POST /v1/workspaces/{ws_id}/projects/{project_id}/artifacts endpoint + signed URL endpoint"

provides:
  - "ArtifactStore MobX store with upload progress tracking per in-flight upload key"
  - "artifactsApi service with XHR multipart upload (progress events) + signed URL fetch"
  - "RootStore.artifacts field + useArtifactStore() hook"
  - "4 Wave 0 RED test scaffold files for Plans 02, 03, 04"

affects:
  - 32-02-file-card-extension
  - 32-03-figure-extension
  - 32-04-slash-commands-media

tech-stack:
  added: []
  patterns:
    - "ArtifactStore uses Map<string, UploadState> with AbortController per upload key — keys are caller-assigned (e.g., TipTap node ID)"
    - "artifactsApi.upload() uses XMLHttpRequest (not axios) so xhr.upload.onprogress fires for real progress"
    - "Auth token retrieved via getAuthProviderSync().getToken() — matches apiClient.ts interceptor pattern"
    - "@ts-expect-error on test scaffold imports that reference not-yet-created modules — keeps pnpm type-check passing while preserving RED vitest state"

key-files:
  created:
    - frontend/src/stores/features/artifacts/ArtifactStore.ts
    - frontend/src/services/api/artifacts.ts
    - frontend/src/features/notes/editor/extensions/__tests__/FileCardExtension.test.ts
    - frontend/src/features/notes/editor/extensions/__tests__/FigureExtension.test.ts
    - frontend/src/features/notes/editor/__tests__/drop-handler.test.ts
    - frontend/src/features/notes/editor/extensions/__tests__/slash-command-media.test.ts
  modified:
    - frontend/src/stores/RootStore.ts
    - frontend/src/stores/index.ts
    - frontend/src/services/api/index.ts

key-decisions:
  - "ArtifactStore.reset() aborts all in-flight uploads before clearing the Map — prevents dangling XHRs on sign-out"
  - "Use getAuthProviderSync().getToken() in artifactsApi (not supabase.auth.getSession()) — consistent with apiClient.ts pattern, supports both Supabase and AuthCore providers"
  - "@ts-expect-error on Wave 0 test scaffold imports — allows pnpm type-check to pass while vitest fails at runtime with import error (correct RED state)"
  - "drop-handler.test.ts tests pure routing logic only (no TipTap dependency) — GREEN immediately; documents expected image/* vs non-image routing for Plans 02/03"

patterns-established:
  - "Wave 0 test scaffolds: use @ts-expect-error on imports of not-yet-created modules to keep type-check passing"
  - "Upload progress tracking: caller creates uploadKey (e.g., TipTap node ID), calls startUpload(), passes AbortController.signal to XHR, calls setProgress() via onProgress callback, calls completeUpload() on success"

requirements-completed: [ARTF-01, ARTF-02, ARTF-03, EDIT-04, EDIT-05]

duration: 15min
completed: 2026-03-19
---

# Phase 32 Plan 01: Artifact Infrastructure Layer Summary

**MobX ArtifactStore with per-key upload progress + XHR artifactsApi service + 4 Wave 0 RED test scaffolds for FileCard, Figure, drop handler, and slash-command media group**

## Performance

- **Duration:** 15 min
- **Started:** 2026-03-19T20:20:00Z
- **Completed:** 2026-03-19T20:38:00Z
- **Tasks:** 3
- **Files modified:** 9

## Accomplishments

- ArtifactStore with `startUpload`, `setProgress`, `completeUpload`, `cancelUpload`, `getProgress`, `activeUploadCount`, and `reset` — registered on RootStore with `useArtifactStore()` hook
- `artifactsApi.upload()` using XMLHttpRequest for real upload progress events; `artifactsApi.getSignedUrl()` using fetch; both exported from services/api/index.ts
- 4 Wave 0 test scaffold files in correct RED state — FileCardExtension and FigureExtension fail with import errors, slash-command-media fails on "media" group assertion, drop-handler passes as pure logic verification

## Task Commits

Each task was committed atomically:

1. **Task 1: ArtifactStore + RootStore wiring** - `2146b890` (feat)
2. **Task 2: artifactsApi service** - `5af270c1` (feat)
3. **Task 3: Wave 0 test scaffolds** - `22951bcf` (test)

**Deviation fix:** `e6813d91` (fix: @ts-expect-error on RED test scaffold imports)

## Files Created/Modified

- `frontend/src/stores/features/artifacts/ArtifactStore.ts` — Ephemeral upload progress store; Map<string, UploadState> with AbortController per key
- `frontend/src/stores/RootStore.ts` — Added artifacts field, constructor, reset(), useArtifactStore() hook
- `frontend/src/stores/index.ts` — Added ArtifactStore and useArtifactStore exports
- `frontend/src/services/api/artifacts.ts` — XHR upload with progress + fetch-based signed URL retrieval
- `frontend/src/services/api/index.ts` — Added artifactsApi, ArtifactUploadResponse, ArtifactUrlResponse exports
- `frontend/src/features/notes/editor/extensions/__tests__/FileCardExtension.test.ts` — RED scaffold (import error until Plan 02)
- `frontend/src/features/notes/editor/extensions/__tests__/FigureExtension.test.ts` — RED scaffold (import error until Plan 03)
- `frontend/src/features/notes/editor/__tests__/drop-handler.test.ts` — GREEN (pure routing logic)
- `frontend/src/features/notes/editor/extensions/__tests__/slash-command-media.test.ts` — RED (fails on "media" group until Plan 04)

## Decisions Made

- Used `getAuthProviderSync().getToken()` instead of `supabase.auth.getSession()` in artifactsApi — consistent with apiClient.ts pattern, supports both Supabase and AuthCore auth providers
- `ArtifactStore.reset()` aborts all in-flight uploads before clearing the Map — prevents dangling XHR connections on sign-out
- Added `@ts-expect-error` to Wave 0 test scaffold imports referencing non-existent modules — keeps `pnpm type-check` passing while vitest still fails at runtime (correct RED state)
- `drop-handler.test.ts` tests pure routing logic only (GREEN immediately) — documents the expected `image/*` vs non-image routing decision for Plans 02/03

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Added @ts-expect-error to Wave 0 test scaffold imports**
- **Found during:** Task 3 verification (Wave 0 test scaffolds)
- **Issue:** `pnpm type-check` failed with TS2307 on FileCardExtension.test.ts and FigureExtension.test.ts because those modules don't exist yet — but the plan's done criteria requires type-check to pass
- **Fix:** Added `// @ts-expect-error — module not yet created (Wave 0 scaffold)` above each import of non-existent module
- **Files modified:** FileCardExtension.test.ts, FigureExtension.test.ts
- **Verification:** `pnpm type-check` passes; `vitest --run FileCardExtension.test.ts` still fails with import error (RED state preserved)
- **Committed in:** `e6813d91` (separate fix commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — type-check vs vitest RED state conflict)
**Impact on plan:** Necessary fix to reconcile TypeScript strict mode with Wave 0 RED test strategy. No scope creep.

## Issues Encountered

None beyond the @ts-expect-error fix above.

## Next Phase Readiness

- Plans 02 (FileCardExtension) and 03 (FigureExtension) can import `ArtifactStore` and `artifactsApi` immediately
- Wave 0 RED tests provide the TDD target — when Plans 02/03/04 create their extensions, tests will turn GREEN
- `useArtifactStore()` hook ready for use in NodeView components (plans 02, 03)

---
*Phase: 32-inline-editor-features*
*Completed: 2026-03-19*

## Self-Check: PASSED

All created files verified present. All 4 commits verified in git log.
- ArtifactStore.ts: FOUND
- artifacts.ts: FOUND
- FileCardExtension.test.ts: FOUND
- FigureExtension.test.ts: FOUND
- drop-handler.test.ts: FOUND
- slash-command-media.test.ts: FOUND
- 32-01-SUMMARY.md: FOUND
- Commits 2146b890, 5af270c1, 22951bcf, e6813d91: ALL FOUND

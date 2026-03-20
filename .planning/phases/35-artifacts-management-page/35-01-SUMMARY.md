---
phase: 35-artifacts-management-page
plan: "01"
subsystem: frontend/data-layer
tags: [tanstack-query, typescript, api-client, optimistic-updates, tdd]
dependency_graph:
  requires:
    - Phase 34 (FilePreviewModal) — ArtifactSignedUrlResponse type compatible with modal
    - frontend/src/services/api/client.ts (apiClient)
  provides:
    - Artifact + ArtifactSignedUrlResponse types
    - artifactsApi.list / .delete / .getSignedUrl
    - useProjectArtifacts hook (Plan 35-02 page consumes this)
    - useDeleteArtifact hook (Plan 35-02 delete button consumes this)
    - useArtifactSignedUrl hook (Plan 35-02 file preview consumes this)
    - artifactsKeys factory (shared cache invalidation key)
  affects:
    - frontend/src/services/api/artifacts.ts (extended, not replaced)
    - frontend/src/features/notes/editor/config.ts (getSignedUrl now uses apiClient)
tech_stack:
  added: []
  patterns:
    - TanStack Query v5 optimistic mutation with onMutate/onError/onSettled
    - Query key factory with all/lists/list/signedUrl segments
    - TDD Red-Green with @ts-expect-error on RED imports
    - noUncheckedIndexedAccess: use .at() instead of [0] for TypeScript strictness
key_files:
  created:
    - frontend/src/types/artifact.ts
    - frontend/src/features/artifacts/hooks/use-project-artifacts.ts
    - frontend/src/features/artifacts/hooks/use-delete-artifact.ts
    - frontend/src/features/artifacts/hooks/use-artifact-signed-url.ts
    - frontend/src/features/artifacts/hooks/index.ts
    - frontend/src/features/artifacts/hooks/__tests__/use-project-artifacts.test.ts
    - frontend/src/features/artifacts/hooks/__tests__/use-delete-artifact.test.ts
    - frontend/src/features/artifacts/hooks/__tests__/use-artifact-signed-url.test.ts
  modified:
    - frontend/src/services/api/artifacts.ts
decisions:
  - "Replaced raw-fetch getSignedUrl with apiClient.get — Phase 34 decision was for useFileContent (external Supabase storage URLs); artifactsApi.getSignedUrl goes through /api/v1 proxy so apiClient is correct"
  - "noUncheckedIndexedAccess requires .at(0)?.id instead of [0].id — used in test assertions to satisfy strict TypeScript config"
  - "ArtifactUrlResponse kept as deprecated export — config.ts in notes/editor calls getSignedUrl and uses .url; both types have same shape so backward compatible"
  - "staleTime 55min on useArtifactSignedUrl — Supabase signed URLs expire at 60min; 5-min buffer prevents serving stale URLs that expire before render"
metrics:
  duration: "12 minutes"
  completed_date: "2026-03-19"
  tasks_completed: 2
  files_created: 8
  files_modified: 1
  tests_added: 12
---

# Phase 35 Plan 01: Artifact Data Layer Summary

Typed API client, domain models, and three TanStack Query hooks for the artifacts management page — complete data layer built TDD with 12 passing tests.

## What Was Built

**Artifact type contracts** (`frontend/src/types/artifact.ts`): `Artifact` (id, filename, mimeType, sizeBytes, storageKey, status, uploader, projectId, workspaceId, timestamps) and `ArtifactSignedUrlResponse` (url, expiresAt).

**Extended artifactsApi** (`frontend/src/services/api/artifacts.ts`): Added `list(ws, proj)` and `delete(ws, proj, id)` using `apiClient`. Replaced raw-fetch `getSignedUrl` with `apiClient.get` returning the new `ArtifactSignedUrlResponse` type. Retained legacy `ArtifactUrlResponse` export for backward compatibility.

**Three TanStack Query hooks**:
- `useProjectArtifacts(ws, proj)` — list query, 5min staleTime, disabled on empty IDs
- `useDeleteArtifact(ws, proj)` — optimistic delete mutation; onMutate filters cache, onError restores + `toast.error('Delete failed. Please try again.')`, onSettled invalidates
- `useArtifactSignedUrl(ws, proj, artifactId | null)` — on-demand, enabled only when artifactId non-null, 55min staleTime (sub-60min Supabase expiry constraint), 1hr gcTime

**artifactsKeys factory**: Hierarchical key structure `['artifacts'] → ['artifacts', 'list'] → ['artifacts', 'list', ws, proj]` and `['artifacts', 'signed-url', artifactId]` enabling precise query invalidation without over-fetching.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] getSignedUrl type/fetch mismatch**
- **Found during:** Task 1
- **Issue:** Existing `getSignedUrl` used raw `fetch()` with auth header injection (pattern correct for external Supabase Storage URLs per Phase 34 decision), but the route `/api/v1/workspaces/.../artifacts/{id}/url` goes through the backend proxy — not directly to Supabase Storage. The raw-fetch pattern was correct for `useFileContent` (which fetches content from signed URLs), not for getting the signed URL from the backend.
- **Fix:** Changed `getSignedUrl` to use `apiClient.get<ArtifactSignedUrlResponse>`. This is consistent with how all other backend API calls work. The `useFileContent` hook (Phase 34) still uses raw `fetch()` correctly for the actual signed URL content fetch.
- **Files modified:** `frontend/src/services/api/artifacts.ts`
- **Commit:** `1a03f8ac`

**2. [Rule 2 - TypeScript] noUncheckedIndexedAccess in tests**
- **Found during:** Task 2 type-check
- **Issue:** `tsconfig.json` has `noUncheckedIndexedAccess: true` making array[0] return `T | undefined`
- **Fix:** Replaced `cached[0].id` with `cached.at(0)?.id` in test assertions
- **Files modified:** `frontend/src/features/artifacts/hooks/__tests__/use-delete-artifact.test.ts`
- **Commit:** `95736236`

**3. [Rule 2 - TypeScript] queryClient.isStale doesn't exist in TanStack Query v5**
- **Found during:** Task 2 test run (1 RED failure)
- **Issue:** The staleTime test used `queryClient.isStale()` which doesn't exist in TQ v5
- **Fix:** Used `queryClient.getQueryCache().find({ queryKey }).isStale()` — the correct v5 API
- **Files modified:** Both staleTime tests (use-project-artifacts and use-artifact-signed-url)
- **Commit:** `95736236`

## Self-Check: PASSED

All created files verified present on disk.
All commits (1a03f8ac, 97c09000, 95736236) verified in git history.
pnpm type-check: 0 errors.
pnpm vitest run artifacts hooks: 12/12 tests pass.

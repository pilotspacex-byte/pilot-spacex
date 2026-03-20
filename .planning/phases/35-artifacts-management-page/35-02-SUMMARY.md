---
phase: 35-artifacts-management-page
plan: "02"
subsystem: frontend
tags: [artifacts, management-page, table, search, sort, preview, delete]
dependency_graph:
  requires:
    - 35-01  # useProjectArtifacts, useDeleteArtifact, useArtifactSignedUrl hooks
    - 34-01  # FilePreviewModal component
  provides:
    - ArtifactsPage at /{workspace}/projects/{id}/artifacts
    - Artifacts nav link in ProjectSidebar (between Knowledge and Chat)
  affects:
    - ProjectSidebar (nav item added)
    - Project navigation UX (new top-level section)
tech_stack:
  added: []
  patterns:
    - observer() page with useParams + useStore (CyclesPage template)
    - Sort state in URL search params via router.replace (not push)
    - Optimistic delete via useDeleteArtifact (no local rollback logic in page)
    - FilePreviewModal gated by selectedArtifact + signedUrlData
    - shadcn AlertDialog for delete confirmation (not window.confirm)
key_files:
  created:
    - frontend/src/app/(workspace)/[workspaceSlug]/projects/[projectId]/artifacts/page.tsx
  modified:
    - frontend/src/components/projects/ProjectSidebar.tsx
decisions:
  - "FilePreviewModal rendered only when both selectedArtifact and signedUrlData are truthy — avoids flash of empty modal while signed URL is fetching"
  - "handleDownload uses artifactsApi.getSignedUrl directly (not TanStack hook) — one-shot action, no caching needed, simpler than setting a separate download-artifact state"
  - "AlertDialog open state tracked by deleteTargetId (artifact id string | null) — supports multiple rows each having their own AlertDialog without an outer Map"
metrics:
  duration: "~6 minutes"
  completed_date: "2026-03-19"
  tasks_completed: 2
  tasks_total: 2
  files_created: 1
  files_modified: 1
---

# Phase 35 Plan 02: Artifacts Management Page Summary

**One-liner:** Full-page artifact management table with per-keystroke search, URL-persisted sort, FilePreviewModal on row click, optimistic delete with AlertDialog, and Artifacts nav link in ProjectSidebar.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Artifacts page component | 939f6314 | `artifacts/page.tsx` (created) |
| 2 | Sidebar navigation — add Artifacts link | 609ae4d9 | `ProjectSidebar.tsx` (modified) |

## What Was Built

### Task 1: ArtifactsPage (`artifacts/page.tsx`)

Full management page composed from Plan 01 hooks and Phase 34 FilePreviewModal:

- **MGMT-01 (List):** Table with file type icon, filename, human-readable size, uploader avatar+name, relative date. Responsive — size/uploader/date columns hide on small screens.
- **MGMT-02 (Preview):** Row click sets `selectedArtifact`; `useArtifactSignedUrl` fetches signed URL on-demand; `FilePreviewModal` renders when both `selectedArtifact` and `signedUrlData` are truthy.
- **MGMT-03 (Download):** Download button calls `artifactsApi.getSignedUrl` directly (one-shot, no cache) and opens URL in new tab via `window.open`.
- **MGMT-04 (Delete):** `AlertDialog` gated by `deleteTargetId` state; `useDeleteArtifact` provides optimistic removal + error rollback + "Delete failed" toast — no extra logic needed in page.
- **MGMT-05 (Search):** `Input` with `searchQuery` state; `useMemo` filters `artifacts` by `filename.toLowerCase().includes(q)` per-keystroke.
- **MGMT-06 (Sort):** `Select` dropdown; `handleSortChange` writes `?sort=date|name|size|type` via `router.replace({ scroll: false })` — no browser history pollution.

Helper functions (`getFileTypeIcon`, `formatBytes`, `formatRelativeDate`, `sortArtifacts`) are pure module-level functions to keep the observer component lean.

Empty state shows `Paperclip` icon + contextual message ("No artifacts yet — upload files in your notes" or "No files match your search").

### Task 2: ProjectSidebar Artifacts link

Added `Paperclip` icon import and inserted `{ label: 'Artifacts', icon: Paperclip, segment: 'artifacts' }` between Knowledge and Chat in `NAV_ITEMS`. The `as const` typed array and JSX map handle the new item automatically on both desktop sidebar and mobile tab bar.

## Verification

- `pnpm type-check` — passes (zero errors)
- `pnpm test --run` — all artifact hook tests (12) and FilePreviewModal tests (15) pass; 55 pre-existing failing tests unrelated to this plan
- Prettier auto-formatted `page.tsx` on first commit; re-staged cleanly on second attempt

## Deviations from Plan

None — plan executed exactly as written.

The only adaptation was adapting `FilePreviewModal` props from the plan's guessed interface (`artifact`, `signedUrl`) to the actual Phase 34 interface (`artifactId`, `filename`, `mimeType`, `signedUrl`) by reading the actual component file before coding.

## Self-Check: PASSED

- FOUND: `frontend/src/app/(workspace)/[workspaceSlug]/projects/[projectId]/artifacts/page.tsx`
- FOUND: `frontend/src/components/projects/ProjectSidebar.tsx` (modified)
- FOUND: commit 939f6314 (ArtifactsPage component)
- FOUND: commit 609ae4d9 (Artifacts nav link)

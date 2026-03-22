---
phase: 05-pptx-annotations
plan: 02
subsystem: frontend
tags: [tanstack-query, optimistic-updates, annotation-panel, pptx, react]
dependency_graph:
  requires: ["05-01"]
  provides: ["PptxAnnotationPanel", "useSlideAnnotations", "annotationApi"]
  affects: ["FilePreviewModal", "artifacts/hooks", "services/api"]
tech_stack:
  added: []
  patterns:
    - "TanStack Query optimistic updates (cancel/snapshot/mutate/rollback)"
    - "MobX observer wrapper for FilePreviewModal to read workspaceStore/authStore"
    - "next/dynamic with ssr:false for PptxAnnotationPanel lazy-load"
    - "Query key factory: annotationKeys.slide(artifactId, slideIndex)"
key_files:
  created:
    - frontend/src/services/api/artifact-annotations.ts
    - frontend/src/features/artifacts/hooks/use-slide-annotations.ts
    - frontend/src/features/artifacts/components/PptxAnnotationPanel.tsx
  modified:
    - frontend/src/features/artifacts/components/FilePreviewModal.tsx
decisions:
  - "Use useParams() inside FilePreviewModal to get projectId (Option A) — fewest prop changes to FilePreviewModalProps"
  - "workspaceId and currentUserId from MobX stores (workspaceStore/authStore) via useStore() — consistent with ArtifactsPage pattern"
  - "Annotation panel toggle state is internal to PptxAnnotationPanel — collapses to narrow icon strip with badge"
  - "Panel hidden during fullscreen — annotation panel would overlap slide presentation"
metrics:
  duration: 4 min
  completed: "2026-03-22"
  tasks: 3
  files: 4
---

# Phase 05 Plan 02: Frontend Annotation Panel Summary

**One-liner:** TanStack Query annotation CRUD panel with optimistic updates wired into FilePreviewModal as a collapsible 320px right sidebar for PPTX slides.

## What Was Built

### 1. API Client (`artifact-annotations.ts`)
Four typed operations (`list`, `create`, `update`, `delete`) wrapping `apiClient` for the annotations endpoints. `list` unwraps `AnnotationListResponse` to return `ArtifactAnnotation[]` directly.

### 2. TanStack Query Hooks (`use-slide-annotations.ts`)
- `useSlideAnnotations` — `useQuery` with key `['artifact-annotations', artifactId, slideIndex]`, staleTime 30s, enabled when all params truthy
- `useCreateAnnotation` — optimistic append with temp UUID
- `useUpdateAnnotation` — optimistic content replace; `toast.error('Update failed. Please try again.')`
- `useDeleteAnnotation` — optimistic filter-out; `toast.error('Delete failed. Please try again.')`

All three mutations follow the exact `useDeleteArtifact` pattern: `cancelQueries → snapshot → setQueryData → return context`, `onError` rollback, `onSettled` invalidate.

### 3. PptxAnnotationPanel (`PptxAnnotationPanel.tsx`)
Collapsible right panel (320px expanded, narrow icon strip when collapsed). Features:
- `useSlideAnnotations` for per-slide data refresh when `currentSlide` changes
- Annotation cards with relative time, edit mode (inline Textarea + Save/Cancel), delete (owner-only)
- New annotation form at bottom with Cmd+Enter shortcut
- Empty state: "No annotations on this slide. Add one below."
- Annotation count badge on toggle button
- Panel hidden during fullscreen (passed-through via `isFullscreen` context)

### 4. FilePreviewModal Integration (`FilePreviewModal.tsx`)
- Wrapped with `observer()` to read MobX stores
- `useParams()` provides `projectId` from URL; `workspaceStore.currentWorkspace?.id` provides `workspaceId`; `authStore.user?.id` provides `currentUserId`
- `PptxAnnotationPanel` lazy-loaded via `next/dynamic({ ssr: false })`
- Rendered as right sibling to slide area in the `pptx` switch case; hidden when `isFullscreen || !workspaceId || !projectId`

## Deviations from Plan

None — plan executed exactly as written.

## Checkpoint Auto-Approved

Task 3 (human-verify): Auto-approved (auto mode active). End-to-end verification will occur during integration testing.

## Self-Check: PASSED

All 4 key files confirmed on disk. Both task commits (1122be9c, 80609584) confirmed in git log.

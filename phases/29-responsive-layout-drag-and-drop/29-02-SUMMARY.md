---
phase: 29-responsive-layout-drag-and-drop
plan: 02
subsystem: frontend/sidebar
tags: [dnd-kit, drag-and-drop, page-tree, tanstack-query, mutation]
dependency_graph:
  requires: [25-tree-api-page-service, 26-sidebar-tree-navigation]
  provides: [drag-and-drop page reorder and re-parent in sidebar tree]
  affects: [frontend/src/components/layout/ProjectPageTree.tsx, frontend/src/services/api/notes.ts]
tech_stack:
  added: []
  patterns: [dnd-kit useSortable + DndContext, TanStack mutation with cache invalidation on success]
key_files:
  created:
    - frontend/src/features/notes/hooks/useMovePage.ts
    - frontend/src/features/notes/hooks/useReorderPage.ts
    - frontend/src/components/layout/DraggableTreeNode.tsx
    - frontend/src/features/notes/hooks/__tests__/useMovePage.test.tsx
    - frontend/src/features/notes/hooks/__tests__/useReorderPage.test.tsx
  modified:
    - frontend/src/services/api/notes.ts
    - frontend/src/features/notes/hooks/index.ts
    - frontend/src/lib/tree-utils.ts
    - frontend/src/components/layout/ProjectPageTree.tsx
    - frontend/src/components/layout/__tests__/ProjectPageTree.test.tsx
decisions:
  - DragOverlay flattens treeNodes recursively via inline flatMap to find active node title — avoids maintaining a separate Map for overlay lookup
  - nodeMap built from flattenTreeWithDepth result provides O(1) parentId lookup in handleDragEnd without traversing tree
  - handleDragEnd uses active.data.current (from useSortable data payload) is NOT used — nodeMap is the source of truth to avoid stale closure issues
  - DraggableTreeNode is a plain function component (not observer) — no MobX reads in the node renderer itself, avoiding unnecessary re-renders during drag
metrics:
  duration: 7m 30s
  completed: "2026-03-13"
  tasks_completed: 2
  files_changed: 9
---

# Phase 29 Plan 02: DnD Sidebar Page Tree Summary

Drag-and-drop reordering and re-parenting for the sidebar page tree using @dnd-kit, with API client methods and TanStack mutation hooks.

## What Was Built

**notesApi.movePage / notesApi.reorderPage** — Two new API client methods in `notes.ts` calling the Phase 25 backend endpoints:
- `POST /workspaces/{wid}/notes/{nid}/move` with `{ new_parent_id }`
- `POST /workspaces/{wid}/notes/{nid}/reorder` with `{ insert_after_id }`

**useMovePage / useReorderPage hooks** — TanStack `useMutation` hooks with:
- Cache invalidation via `projectTreeKeys.tree(workspaceId, projectId)` on success
- `toast.error` via sonner on failure
- Exported from `features/notes/hooks/index.ts` barrel

**flattenTreeWithDepth** — New utility in `tree-utils.ts` that flattens only visible (expanded) tree nodes for `SortableContext items` array. This ensures the SortableContext matches rendered DOM nodes, preventing @dnd-kit id mismatch errors.

**DraggableTreeNode** — New component wrapping the existing tree node UI with `useSortable`:
- Data payload: `{ parentId, depth, type: 'tree-node' }` for drag metadata
- `GripVertical` drag handle with `aria-label="drag to reorder"`, hidden until `group-hover:flex`
- `opacity: 0.4` when `isDragging`
- Recursive rendering of children (self-referential)

**ProjectPageTree (updated)** — DnD wiring:
- `DndContext` wraps the entire tree with sensors matching BoardView pattern (distance: 8, delay: 150)
- `SortableContext` with `verticalListSortingStrategy` over `flatIds`
- `handleDragEnd`: same parentId → `reorderPage.mutate`; different parentId → `movePage.mutate`
- `DragOverlay` shows simplified node preview during drag
- No optimistic updates — server state via cache invalidation only

## Tests

17 tests across 3 test files, all passing:
- `useMovePage.test.tsx` (3 tests): API call params, cache invalidation, error toast
- `useReorderPage.test.tsx` (3 tests): API call params, cache invalidation, error toast
- `ProjectPageTree.test.tsx` (11 tests): pre-existing 10 tests all still pass + new Test 11 for drag handle presence

## Deviations from Plan

None — plan executed exactly as written.

The only minor deviation: `handleDragEnd` uses `nodeMap` (built from `flattenTreeWithDepth`) for parentId lookup rather than `active.data.current` (useSortable data payload). Both approaches are equivalent but `nodeMap` avoids potential stale closure issues with the sortable data registration timing.

## Self-Check: PASSED

- FOUND: frontend/src/services/api/notes.ts (movePage, reorderPage methods)
- FOUND: frontend/src/features/notes/hooks/useMovePage.ts
- FOUND: frontend/src/features/notes/hooks/useReorderPage.ts
- FOUND: frontend/src/components/layout/DraggableTreeNode.tsx
- FOUND: frontend/src/components/layout/ProjectPageTree.tsx (DndContext)
- FOUND: frontend/src/lib/tree-utils.ts (flattenTreeWithDepth)
- FOUND: Commits e5310e5e and a06bc935
- All 17 tests pass, type-check clean

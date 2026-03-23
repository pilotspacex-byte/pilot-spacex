---
phase: 29-responsive-layout-drag-and-drop
plan: 03
subsystem: frontend/sidebar
tags: [dnd-kit, drag-and-drop, page-tree, depth-limit, visual-feedback]
dependency_graph:
  requires: [29-02]
  provides: [depth limit visual rejection during drag-and-drop]
  affects:
    - frontend/src/lib/tree-utils.ts
    - frontend/src/components/layout/ProjectPageTree.tsx
    - frontend/src/components/layout/DraggableTreeNode.tsx
    - frontend/src/components/layout/__tests__/ProjectPageTree.test.tsx
    - frontend/src/lib/__tests__/tree-utils.test.ts
tech_stack:
  added: []
  patterns:
    - onDragOver + invalidDropTargetId state for real-time depth validation
    - fullNodeMap recursive walk for collapsed-node subtree access
    - getSubtreeHeight recursive utility for subtree depth measurement
key_files:
  created: []
  modified:
    - frontend/src/lib/tree-utils.ts
    - frontend/src/components/layout/ProjectPageTree.tsx
    - frontend/src/components/layout/DraggableTreeNode.tsx
    - frontend/src/components/layout/__tests__/ProjectPageTree.test.tsx
    - frontend/src/lib/__tests__/tree-utils.test.ts
decisions:
  - fullNodeMap built via recursive walk of treeNodes (not just flatItems) — collapsed children are still needed for subtree height computation; flattenTreeWithDepth only includes visible nodes
  - newDeepestDepth = overMeta.depth + getSubtreeHeight(activeFullNode) — active becomes sibling of over (lands at overMeta.depth), deepest descendant is that depth + subtree height
  - Same-parent reorder skips depth check — same-level reorder never changes depth, short-circuits to null immediately
  - invalidDropTargetId cleared in handleDragEnd unconditionally — ensures state is always clean after a drag cycle regardless of drop validity
metrics:
  duration: 6m 37s
  completed: "2026-03-13"
  tasks_completed: 1
  files_changed: 5
---

# Phase 29 Plan 03: Depth Limit Visual Enforcement Summary

Depth limit visual rejection during drag-and-drop — red ring + reduced opacity on invalid drop target, API call blocked on invalid drop.

## What Was Built

**getSubtreeHeight(node: PageTreeNode): number** — New utility in `tree-utils.ts` that returns the max descendant depth relative to a node (0 for leaf, 1 for single-child level, 2 for grandchildren, etc.). Recursive: `node.children.length === 0 ? 0 : 1 + Math.max(...node.children.map(getSubtreeHeight))`.

**fullNodeMap** — Built via recursive walk of all `treeNodes` in `ProjectPageTree` (including collapsed children), mapping id -> `PageTreeNode`. Required because `flattenTreeWithDepth` (the source of `nodeMap`) excludes collapsed children, but subtree height computation needs the full subtree.

**handleDragOver** — New DragOverEvent handler in `ProjectPageTree` that:
1. Short-circuits on same-parent drags (sibling reorder — depth unchanged, always valid)
2. For cross-parent drags: computes `newDeepestDepth = overMeta.depth + getSubtreeHeight(activeFullNode)`
3. Sets `invalidDropTargetId = over.id` when `newDeepestDepth > 2`, clears to `null` otherwise

**handleDragEnd early return** — Blocks `movePage.mutate` / `reorderPage.mutate` when `over.id === invalidDropTargetId`. Depth-exceeding drops are no-ops.

**DraggableTreeNode visual rejection** — Added `invalidDropTargetId?: string | null` prop, `isInvalidTarget = invalidDropTargetId === node.id` computation, and conditional class `ring-1 ring-destructive/50 rounded-md opacity-60 cursor-not-allowed` on the outer `<div ref={setNodeRef}>`. Prop propagated to recursive children renders.

## Tests

20 tests in `tree-utils.test.ts` (4 new getSubtreeHeight tests + 16 pre-existing):
- `getSubtreeHeight > returns 0 for a leaf node`
- `getSubtreeHeight > returns 1 for a node with only direct children`
- `getSubtreeHeight > returns 2 for a node with grandchildren`
- `getSubtreeHeight > returns the max height when children have unequal depths`

12 tests in `ProjectPageTree.test.tsx` (1 new Test 12 + 11 pre-existing):
- `Test 12: depth limit — component renders without error when tree has max-depth nodes`
  - Verifies all 5 nodes render correctly (depth2Node + secondRoot subtrees)
  - Confirms 5+ drag handles are present (DnD fully wired)

All 32 tests pass. Type-check clean. Lint 0 errors.

## Deviations from Plan

None — plan executed exactly as written.

The one minor implementation note: `fullNodeMap` uses an IIFE (`(function walkAll(nodes) {...})(treeNodes)`) to avoid defining a named function at module/component level. This is idiomatic for one-off recursive walks that don't need to be reused.

## Self-Check: PASSED

- FOUND: `frontend/src/lib/tree-utils.ts` (getSubtreeHeight exported at line 156)
- FOUND: `frontend/src/components/layout/ProjectPageTree.tsx` (onDragOver at line 209, invalidDropTargetId at line 73)
- FOUND: `frontend/src/components/layout/DraggableTreeNode.tsx` (invalidDropTargetId prop at line 35)
- FOUND: `frontend/src/lib/__tests__/tree-utils.test.ts` (4 getSubtreeHeight tests)
- FOUND: `frontend/src/components/layout/__tests__/ProjectPageTree.test.tsx` (Test 12 at line 282+)
- FOUND: Commit 0715dc90
- All 32 tests pass, type-check clean, lint 0 errors

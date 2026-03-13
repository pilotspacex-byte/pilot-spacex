---
phase: 28-visual-design-refresh
plan: 02
subsystem: frontend/page-layouts
tags: [css, tailwind, spacing, 8px-grid, page-layout]
dependency_graph:
  requires: [28-01]
  provides: [8px-grid-page-spacing]
  affects:
    - frontend/src/app/(workspace)/[workspaceSlug]/issues/page.tsx
    - frontend/src/app/(workspace)/[workspaceSlug]/notes/page.tsx
    - frontend/src/app/(workspace)/[workspaceSlug]/projects/page.tsx
    - frontend/src/app/(workspace)/[workspaceSlug]/settings/layout.tsx
    - frontend/src/app/(workspace)/[workspaceSlug]/projects/[projectId]/layout.tsx
    - frontend/src/app/(workspace)/[workspaceSlug]/projects/[projectId]/chat/page.tsx
tech_stack:
  added: []
  patterns: [8px-grid-spacing, tailwind-utility-classes]
key_files:
  created: []
  modified:
    - frontend/src/app/(workspace)/[workspaceSlug]/issues/page.tsx
    - frontend/src/app/(workspace)/[workspaceSlug]/notes/page.tsx
    - frontend/src/app/(workspace)/[workspaceSlug]/projects/page.tsx
    - frontend/src/app/(workspace)/[workspaceSlug]/settings/layout.tsx
    - frontend/src/app/(workspace)/[workspaceSlug]/projects/[projectId]/layout.tsx
    - frontend/src/app/(workspace)/[workspaceSlug]/projects/[projectId]/chat/page.tsx
decisions:
  - "py-3 (12px) in page headers replaced with py-4 (16px) — more breathing room, consistent header height across all pages"
  - "py-3 (12px) in compact toolbars replaced with py-2 (8px) — toolbars are tight contexts, py-2 preserves density"
  - "Dynamic issue.state.color API values in notes/page.tsx left unchanged — runtime API values, not design token hardcodes"
  - "3 files already 8px-grid-aligned: notes/[noteId]/page.tsx, cycles/page.tsx, cycles/[cycleId]/page.tsx — no changes needed"
  - "settings/layout.tsx nav item px-3/py-2 left unchanged — internal nav link padding, out of plan scope (components/ boundary)"
metrics:
  duration_minutes: 8
  completed_date: "2026-03-12"
  tasks_completed: 2
  files_modified: 6
---

# Phase 28 Plan 02: Page-Level Spacing Alignment to 8px Grid

Audited 9 page-level layout files, replaced all non-8px-grid structural padding with grid-aligned values; 6 files required changes, 3 were already compliant.

## Tasks Completed

| # | Task | Commit | Key Changes |
|---|------|--------|-------------|
| 1 | Audit and fix page-level structural spacing | adde8bda | 6 files — py-3 headers → py-4, py-3 toolbars → py-2, gap-3 → gap-4 |
| 2 | Visual verification (auto-approved) | — | Autonomous mode: checkpoint auto-approved |

## Changes Made

### Per-File Audit Results

| File | Changes | Rationale |
|------|---------|-----------|
| `issues/page.tsx` | `py-3` → `py-4`, removed redundant `sm:py-4` | Header context: needs breathing room |
| `notes/page.tsx` | Header `py-3` → `py-4`; toolbar `py-3` → `py-2` | Header + compact toolbar distinction |
| `projects/page.tsx` | Header `py-3` → `py-4`; filter bar `py-3` → `py-2`, `sm:gap-3` → `sm:gap-4` | Same pattern as notes |
| `settings/layout.tsx` | Desktop header `gap-3` → `gap-4`; mobile header `py-3` → `py-4`, `gap-3` → `gap-4` | Header context on both breakpoints |
| `projects/[projectId]/layout.tsx` | Skeleton sidebar `py-3` → `py-4` | Skeleton mirrors real layout proportions |
| `projects/[projectId]/chat/page.tsx` | Chat header `py-3` → `py-4` | Header context |
| `notes/[noteId]/page.tsx` | No changes | All structural spacing already 8px-aligned |
| `projects/[projectId]/cycles/page.tsx` | No changes | Header uses `py-4` already |
| `projects/[projectId]/cycles/[cycleId]/page.tsx` | No changes | Header uses `py-4`, tabs bar uses `py-2` already |

### Hardcoded Color Audit

No hardcoded `bg-[#...]`, `text-[#...]`, or `border-[#...]` overrides found in page-level layout containers.

Two occurrences of `style={{ backgroundColor: issue.state.color }}` in `notes/page.tsx` are **runtime API values** (issue state colors from server), not design token hardcodes. Left unchanged — they are appropriate dynamic values.

## Verification

```
pnpm type-check    → PASS: 0 TypeScript errors
pnpm lint          → PASS: 0 errors, 21 pre-existing warnings (unchanged from Plan 01 baseline)
pnpm test --run    → 38 pre-existing failures (same count before and after changes — confirmed by git stash test)
```

Pre-existing test failures are in editor, store, and hook tests unrelated to page layout files. Not caused by this plan's changes.

## Deviations from Plan

None — plan executed exactly as written. 3 files were already 8px-grid-aligned (no changes needed). The `settings/layout.tsx` nav item `px-3`/`py-2` values were correctly excluded per plan scope boundary (internal nav component spacing).

## Self-Check: PASSED

- [x] `frontend/src/app/(workspace)/[workspaceSlug]/issues/page.tsx` — updated
- [x] `frontend/src/app/(workspace)/[workspaceSlug]/notes/page.tsx` — updated
- [x] `frontend/src/app/(workspace)/[workspaceSlug]/projects/page.tsx` — updated
- [x] `frontend/src/app/(workspace)/[workspaceSlug]/settings/layout.tsx` — updated
- [x] `frontend/src/app/(workspace)/[workspaceSlug]/projects/[projectId]/layout.tsx` — updated
- [x] `frontend/src/app/(workspace)/[workspaceSlug]/projects/[projectId]/chat/page.tsx` — updated
- [x] Commit adde8bda exists

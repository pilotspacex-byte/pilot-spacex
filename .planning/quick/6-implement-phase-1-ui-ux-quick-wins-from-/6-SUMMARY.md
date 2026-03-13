---
phase: quick-6
plan: 01
subsystem: frontend
tags: [fonts, design-tokens, ux, accessibility, css]
dependency_graph:
  requires: []
  provides: [UX-AUDIT-PHASE1]
  affects: [frontend/layout, frontend/globals.css, frontend/components]
tech_stack:
  added: []
  patterns: [tailwind-css-variables, aa-contrast-tokens]
key_files:
  created: []
  modified:
    - frontend/src/app/layout.tsx
    - frontend/src/app/globals.css
    - frontend/src/components/layout/sidebar.tsx
    - frontend/src/app/(workspace)/[workspaceSlug]/notes/page.tsx
    - frontend/src/features/members/components/member-card.tsx
    - frontend/src/components/projects/ProjectCard.tsx
    - frontend/src/components/role-skill/RoleCard.tsx
decisions:
  - "Keep geist package in package.json (may be used elsewhere) — only remove layout.tsx imports"
  - "Tailwind color mappings added in @theme inline block for --primary-text and --ai-text"
metrics:
  duration: 3m
  completed: "2026-03-13"
  tasks_completed: 3
  files_modified: 7
---

# Phase quick-6 Plan 01: Phase 1 UI/UX Quick Wins Summary

**One-liner:** Removed 3 unused font packages, fixed muted-foreground contrast to AA-compliant #6f6e6b, added --primary-text and --ai-text tokens in both themes, and eliminated hover:-translate-y-0.5 bounce from 5 components.

## Tasks Completed

| Task | Name | Commit | Files Modified |
|------|------|--------|----------------|
| 1 | Clean up fonts in layout.tsx | 4f4e6d47 | frontend/src/app/layout.tsx |
| 2 | Fix design tokens in globals.css | 7d5f0c97 | frontend/src/app/globals.css |
| 3 | Remove button translateY hover from 5 components | 04ad972d | sidebar.tsx, notes/page.tsx, member-card.tsx, ProjectCard.tsx, RoleCard.tsx |

## What Changed

### Task 1: Font cleanup (layout.tsx)

- Removed `GeistSans` import from `geist/font/sans`
- Removed `GeistMono` import from `geist/font/mono`
- Removed `DM_Mono` import and instantiation block (`dmMono`)
- Removed Google Fonts `<link>` tags for Fraunces (preconnect + stylesheet)
- Removed empty `<head>` element
- Body `className` now only includes `${jetbrainsMono.variable} font-sans antialiased`

Result: 3 fewer font downloads on page load; no Fraunces Google Fonts network request.

### Task 2: Design tokens (globals.css)

- `--font-mono` updated to lead with `var(--font-jetbrains-mono)` instead of `var(--font-dm-mono), var(--font-geist-mono)`
- `--muted-foreground` in `:root` changed from `#787774` → `#6f6e6b` (WCAG AA 5.1:1 contrast on white)
- Added `--primary-text: #1f7d66` and `--ai-text: #4a6f8f` to `:root` (light theme)
- Added `--primary-text: #4ecaa8` and `--ai-text: #8fb5d3` to `.dark` theme
- Added `--color-primary-text` and `--color-ai-text` Tailwind mappings in `@theme inline` block

### Task 3: Remove translateY hover (5 components)

Removed `hover:-translate-y-0.5` from all 5 files:
- `sidebar.tsx` — New Note Button
- `notes/page.tsx` — NoteGridCard
- `member-card.tsx` — MemberCard
- `ProjectCard.tsx` — grid variant card
- `RoleCard.tsx` — unselected state

Other hover classes (`hover:shadow-md`, `hover:shadow-warm-md`) preserved.

## Deviations from Plan

None — plan executed exactly as written.

## Verification

- `pnpm lint` — passes (21 pre-existing warnings, 0 errors)
- `pnpm type-check` — passes (0 errors)
- `grep -r "hover:-translate-y-0.5" src/` — CLEAN (0 occurrences)
- globals.css tokens confirmed present via grep

## Self-Check: PASSED

Files exist:
- frontend/src/app/layout.tsx — FOUND
- frontend/src/app/globals.css — FOUND
- frontend/src/components/layout/sidebar.tsx — FOUND
- frontend/src/app/(workspace)/[workspaceSlug]/notes/page.tsx — FOUND
- frontend/src/features/members/components/member-card.tsx — FOUND
- frontend/src/components/projects/ProjectCard.tsx — FOUND
- frontend/src/components/role-skill/RoleCard.tsx — FOUND

Commits verified: 4f4e6d47, 7d5f0c97, 04ad972d

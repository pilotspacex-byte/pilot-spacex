# Tasks: Compact Layout Redesign

**Feature**: Compact Layout Redesign
**Branch**: `009-compact-layout-redesign`
**Created**: 2026-02-04
**Source**: `specs/009-compact-layout-redesign/`
**Author**: Tin Dang

---

## Phase 1: Foundation

- [ ] T001 Update `--header-height` CSS variable from 56px to 40px in `frontend/src/app/globals.css`

**Checkpoint**: CSS variable updated. No visual change yet (variable consumed by components).

---

## Phase 2: User Story 2 — Minimal Header Bar (P1)

**Goal**: Strip header to breadcrumb-only bar at 40px height, remove search/AI/+New/notifications/avatar.
**Verify**: Navigate to any page. Header shows only breadcrumb at 40px. No action buttons visible. Cmd+K still opens search.

### Implementation

- [ ] T002 [US2] Remove search bar, AI button, +New dropdown, notifications, and user avatar from header in `frontend/src/components/layout/header.tsx`
- [ ] T003 [US2] Reduce header height from h-14 to h-10 and clean up unused imports in `frontend/src/components/layout/header.tsx`

**Checkpoint**: Header is breadcrumb-only at 40px. Keyboard shortcuts (Cmd+K, Cmd+N) still work via global handlers.

---

## Phase 3: User Story 1 — Consolidated Sidebar Controls (P1)

**Goal**: Add notification bell + user avatar menu to sidebar bottom section. Works in both expanded and collapsed modes.
**Verify**: Click notification bell in sidebar — dropdown opens right. Click avatar — menu opens right with Profile/Settings/Sign out.

### Implementation

- [ ] T004 [US1] Add notification and user avatar imports and store usage to `frontend/src/components/layout/sidebar.tsx`
- [ ] T005 [US1] Add notification bell + user avatar section between New Note button and collapse toggle in `frontend/src/components/layout/sidebar.tsx`
- [ ] T006 [US1] Handle collapsed sidebar mode for notification + user controls with tooltips in `frontend/src/components/layout/sidebar.tsx`

**Checkpoint**: Notification + user controls visible in sidebar bottom. Dropdowns open to the right. Collapsed mode shows icons with tooltips.

---

## Phase 4: User Story 3 — Font & Spacing Compaction (P1)

**Goal**: Reduce font sizes by ~2px and tighten spacing across layout components.
**Verify**: Navigation text ~12px, note items ~12px, section labels ~9px. 15%+ more content visible per viewport.

### Implementation

- [ ] T007 [P] [US3] Compact sidebar navigation: reduce font sizes, padding, and gaps in `frontend/src/components/layout/sidebar.tsx`
- [ ] T008 [P] [US3] Compact sidebar logo header height from h-14 to h-10 in `frontend/src/components/layout/sidebar.tsx`
- [ ] T009 [US3] Compact sidebar notes sections and bottom controls spacing in `frontend/src/components/layout/sidebar.tsx`

**Checkpoint**: All layout text is visibly smaller. Sidebar feels compact but readable. No overflow or clipping.

---

## Phase Final: Polish

- [ ] T010 Run quality gates: `pnpm lint && pnpm type-check && pnpm test` in `frontend/`
- [ ] T011 Verify all quickstart.md scenarios pass (manual visual check)
- [ ] T012 Verify file size limits: header.tsx < 700 lines, sidebar.tsx < 700 lines

**Checkpoint**: Feature complete. All quality gates pass. All quickstart scenarios verified.

---

## Dependencies

### Phase Order

```
Phase 1 (Foundation: CSS var) → Phase 2 (Header strip) → Phase 3 (Sidebar controls) → Phase 4 (Compaction) → Final (Polish)
```

Phase 2 before Phase 3: Header controls must be removed before adding them to sidebar (avoid duplication during dev).

### Parallel Opportunities

| Phase | Parallel Group | Tasks |
|-------|---------------|-------|
| Phase 4 | Compaction | T007, T008 (different sections of sidebar.tsx, no overlap) |

---

## Execution Strategy

**Selected Strategy**: A (MVP-First) — Single developer, stable requirements, all P1 stories. Execute sequentially Phase 1→2→3→4→Final.

---

## Validation Checklists

### Coverage Completeness

- [x] Every user story from spec.md has a task phase
- [x] Every entity from data-model.md has a creation task (N/A — no entities)
- [x] Every endpoint from contracts/ has an implementation task (N/A — no endpoints)
- [x] Every quickstart scenario has a validation task (T011)
- [x] Setup and Polish phases included

### Task Quality

- [x] Task IDs sequential (T001–T012) with no gaps
- [x] Each task has exact file path
- [x] Each task starts with imperative verb
- [x] One responsibility per task
- [x] `[P]` markers only where tasks are truly independent
- [x] `[USn]` markers on all Phase 2+ tasks

### Dependency Integrity

- [x] No circular dependencies
- [x] Phase order enforced
- [x] Cross-story shared entities placed in Foundation phase (CSS var)
- [x] Each phase has a checkpoint statement

### Execution Readiness

- [x] Any developer can pick up any task and execute without questions
- [x] File paths match plan.md project structure exactly
- [x] Quality gate commands specified in Polish phase
- [x] Execution strategy selected with rationale

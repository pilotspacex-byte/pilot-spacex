# Tasks: Project Notes Panel (022)

**Source**: `/specs/022-project-notes-panel/`
**Branch**: `022-project-notes-panel`
**Required**: plan.md ✅, spec.md ✅
**Optional**: research.md ✅, data-model.md ✅, contracts/ ✅, quickstart.md ✅

---

## Task Format

```
- [ ] [ID] [P?] [Story?] Description with exact file path
```

| Marker | Meaning |
|--------|---------|
| `[P]` | Parallelizable (different files, no dependencies) |
| `[USn]` | User story label (Phase 3+ only) |

---

## Phase 1: Setup

Verify reference patterns and confirm the working environment before writing any code.
No new infrastructure needed — this is a frontend-only change to an existing Next.js app.

- [ ] T001 Read `frontend/src/components/layout/sidebar.tsx` lines 372–544 to capture the exact CSS class names and structure used for PINNED/RECENT note sections (visual reference for FR-008)
- [ ] T002 Read `frontend/src/components/projects/ProjectSidebar.tsx` in full to understand mount point and line count before modification
- [ ] T003 [P] Read `frontend/src/features/notes/hooks/useNotes.ts` to confirm `useNotes` signature accepts `projectId`, `isPinned`, and `pageSize` parameters
- [ ] T004 [P] Read `frontend/src/features/notes/hooks/useCreateNote.ts` to confirm `useCreateNote` mutation accepts `projectId` in the data payload

**Checkpoint**: Reference patterns confirmed; proceed to implementation.

---

## Phase 2: Foundational

No new shared infrastructure is required. All hooks, types, and API services already exist. This phase is intentionally empty — implementation begins directly in Phase 3.

**Skipped**: No database migrations, no new API routes, no new stores. `useNotes`, `useCreateNote`, `useWorkspaceStore`, `Note` type, and `Project` type are all available.

---

## Phase 3: User Story 1 — Browse Project Notes from Sidebar (P1) 🎯 MVP

**Goal**: Display Pinned and Recent project-scoped notes in the project sidebar desktop panel, each as a clickable link to the note editor. Show skeleton on load, error text on failure, empty state when no notes exist.

**Verify**: Navigate to any project with notes → project sidebar shows "Pinned" and/or "Recent" note sections with correct titles and working links.

### Implementation

- [ ] T005 [US1] Create `frontend/src/components/projects/ProjectNotesPanel.tsx` with the full component skeleton: props interface `{ project: Project, workspaceSlug: string, workspaceId: string }`, two `useNotes` calls (pinned + recent), and placeholder render that returns `null`
- [ ] T006 [US1] Implement loading state in `ProjectNotesPanel.tsx`: when either query `isLoading`, render 3 `<Skeleton>` rows (class `h-4 w-full rounded`) inside a `<div className="px-2 py-1.5 space-y-1">` container
- [ ] T007 [US1] Implement error state in `ProjectNotesPanel.tsx`: when either query `isError`, render `<p className="px-3 py-2 text-xs text-muted-foreground">Failed to load notes</p>` (non-crashing inline message per research Decision 5)
- [ ] T008 [US1] Implement the "Pinned" sub-section in `ProjectNotesPanel.tsx`: render section header `<div className="mb-1 flex items-center gap-1.5 px-1.5">` with `<Pin className="h-2.5 w-2.5 text-muted-foreground" />` and label `text-[10px] font-semibold uppercase tracking-wider text-muted-foreground`; render up to 5 note rows as `<Link href="/{workspaceSlug}/notes/{note.id}">` with `<FileText className="h-3 w-3 text-muted-foreground" />` and truncated title (class `truncate text-xs`) — only rendered when `pinnedNotes.length > 0`
- [ ] T009 [US1] Implement the "Recent" sub-section in `ProjectNotesPanel.tsx`: same structure as Pinned section using `<Clock className="h-2.5 w-2.5 text-muted-foreground" />` header icon; note rows exclude any note already in `pinnedNotes` — only rendered when `recentNotes.length > 0`
- [ ] T010 [US1] Implement the empty state in `ProjectNotesPanel.tsx`: when both `pinnedNotes.length === 0` and `recentNotes.length === 0` (and neither query is loading/erroring), render `<p className="px-3 py-2 text-xs text-muted-foreground">No notes yet</p>` (FR-005)
- [ ] T011 [US1] Mount `ProjectNotesPanel` in `frontend/src/components/projects/ProjectSidebar.tsx`: import `ProjectNotesPanel`; inside the `<aside>` block (desktop only), add after the closing `</nav>` tag (line 88): `<Separator className="mx-2 my-2" />` then `<ProjectNotesPanel project={project} workspaceSlug={workspaceSlug} workspaceId={project.workspaceId} />`; do NOT add to the mobile `<nav>` tab bar (FR-009)

**Checkpoint**: US1 functional and testable independently — project sidebar shows note lists with skeleton, error, and empty states.

---

## Phase 4: User Story 2 — Create Project-Linked Note from Panel (P2)

**Goal**: "New Note" button in the panel creates a note with `projectId` pre-set and navigates the user to the note editor. Button hidden for guest-role users.

**Verify**: Click "New Note" in the project sidebar → new note created → navigated to note editor → note has `projectId` matching the current project.

### Implementation

- [ ] T012 [US2] Add `useCreateNote`, `useWorkspaceStore`, and `useRouter` imports to `frontend/src/components/projects/ProjectNotesPanel.tsx`; add `useCreateNote({ workspaceId, onSuccess: (note) => router.push('/{workspaceSlug}/notes/{note.id}') })` mutation; add `canCreateContent = workspaceStore.currentUserRole !== 'guest'` permission check
- [ ] T013 [US2] Add "New Note" button to `ProjectNotesPanel.tsx`: render at the bottom of the panel (above the closing `</div>`) as `<Button variant="ghost" size="sm" className="w-full justify-start gap-1.5 px-2 text-xs text-muted-foreground hover:text-sidebar-foreground" onClick={handleCreateNote} disabled={createNote.isPending}>`; include `<Plus className="h-3 w-3" />` icon and label "New Note"; hide completely (`return null` branch) when `!canCreateContent` (FR-006)
- [ ] T014 [US2] Implement `handleCreateNote` callback in `ProjectNotesPanel.tsx`: calls `createNote.mutate({ title: 'Untitled', workspaceId, projectId: project.id })`; the `onSuccess` handler navigates to `/{workspaceSlug}/notes/{note.id}` via `router.push`

**Checkpoint**: US2 functional — "New Note" creates a project-linked note and navigates to editor; button absent for guest users.

---

## Phase 5: User Story 3 — "View all" Link and Visual Polish (P3)

**Goal**: Add "View all →" links when total > 5, and verify exact visual parity with the workspace sidebar PINNED/RECENT sections.

**Verify**: Side-by-side comparison of workspace sidebar and project sidebar notes sections shows identical visual style; "View all" link appears when more than 5 notes exist.

### Implementation

- [ ] T015 [P] [US3] Add "View all" link to the Pinned sub-section in `ProjectNotesPanel.tsx`: after the pinned rows, if `pinnedData?.total ?? 0 > 5` render `<Link href="/{workspaceSlug}/notes" className="flex items-center gap-1 px-1.5 py-1 text-[10px] text-muted-foreground hover:text-sidebar-foreground">View all <ChevronRight className="h-3 w-3" /></Link>` (FR-007)
- [ ] T016 [P] [US3] Add "View all" link to the Recent sub-section in `ProjectNotesPanel.tsx`: same pattern as T015 but conditioned on `recentData?.total ?? 0 > 5`
- [ ] T017 [US3] Audit `ProjectNotesPanel.tsx` for visual parity with `sidebar.tsx` lines 488–544: verify section header classes (`text-[10px] font-semibold uppercase tracking-wider text-muted-foreground`), row hover class (`hover:bg-sidebar-accent/50`), row padding (`rounded-md px-1.5 py-1`), icon sizes (`h-3 w-3`), and title class (`text-xs truncate`) all match exactly

---

## Phase 6: Polish & Validation

Cross-cutting concerns after all user stories are complete.

- [ ] T018 [P] Run `cd frontend && pnpm type-check` and fix any TypeScript errors in `ProjectNotesPanel.tsx` and `ProjectSidebar.tsx`
- [ ] T019 [P] Run `cd frontend && pnpm lint` and fix any ESLint errors in `ProjectNotesPanel.tsx` and `ProjectSidebar.tsx`
- [ ] T020 Write unit tests in `frontend/src/components/projects/__tests__/ProjectNotesPanel.test.tsx`: mock `useNotes`, `useCreateNote`, `useWorkspaceStore`; cover — (a) skeleton when loading, (b) error message when query fails, (c) pinned notes list renders with correct titles, (d) recent notes excludes pinned notes, (e) empty state when no notes, (f) "New Note" hidden for guest role, (g) "View all" shown when `total > 5`, (h) create mutation called with correct `projectId`
- [ ] T021 Validate all 5 quickstart scenarios from `specs/022-project-notes-panel/quickstart.md` manually: (1) panel with pinned+recent, (2) empty project, (3) create note, (4) guest user, (5) "View all" link

---

## Dependencies

### Phase Order

```
Phase 1 (Setup — read references)
  → Phase 3 (US1 — browse notes panel core)
    → Phase 4 (US2 — create note, depends on US1 panel structure)
      → Phase 5 (US3 — "View all" + polish, depends on US1 panel data)
        → Phase 6 (Polish — runs after all stories)
```

### Phase 2

Skipped — no foundational infrastructure needed (all hooks, types, API services pre-exist).

### User Story Independence

- **US1** (T005–T011): Independently testable once T001–T004 (setup reads) done
- **US2** (T012–T014): Depends on US1 panel existing; adds to same file
- **US3** (T015–T017): T015/T016 are parallel (different conditionals in same file); T017 is a verification pass

### Parallel Opportunities

Tasks marked `[P]` within the same phase can run concurrently:

```
Phase 1:   T003 || T004  (reading different files)
Phase 5:   T015 || T016  (adding "View all" to pinned vs recent sub-sections)
Phase 6:   T018 || T019  (type-check vs lint — independent tools)
```

---

## Implementation Strategy

### MVP (US1 only)

```
T001 → T002 → T003 || T004 → T005 → T006 → T007 → T008 → T009 → T010 → T011
```

Delivers: Project sidebar shows project-scoped pinned and recent notes with correct states (loading, error, empty, populated). Links navigate to note editor.

### Incremental

1. Phase 1 (setup reads) → Phase 3 (US1: browse) → validate
2. Phase 4 (US2: create note) → validate
3. Phase 5 (US3: view all + polish) → validate
4. Phase 6 (type-check, lint, tests, quickstart validation)

---

## Notes

- No backend changes required — all endpoints pre-exist and accept the required filter params
- `useNotes` (non-infinite) is correct for this panel — max 5 items per sub-section, no pagination needed
- The `<Separator />` import for `ProjectSidebar.tsx` modification: already available at `@/components/ui/separator`
- Mobile tab bar must NOT be modified (FR-009); only the `<aside>` desktop block receives the panel
- "View all" links point to `/{workspaceSlug}/notes` (notes page); project pre-filtering via URL param is a follow-on (research Decision 4)

# Tasks: Project Notes Panel (022)

**Source**: `/specs/022-project-notes-panel/`
**Branch**: `022-project-notes-panel`
**Updated**: 2026-03-10 — v3: Bug fixes T045–T064 + Enhancements T065–T082 added
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
| `[BUGn]` | Bug fix label |
| `[ENHn]` | Enhancement label |

---

## Phases 1–12 (v1 + v2 — COMPLETE)

All T001–T044 are complete. See above in original task list.

---

## Phase 13: BUG-1 — Remove Recent Section from Workspace Sidebar

**Goal**: The workspace taskbar (sidebar.tsx) no longer shows a "Recent" notes section (FR-017).
**Verify**: Open workspace sidebar → only "Pinned" section visible; no "Recent" header or list.

- [X] T045 [BUG1] In `frontend/src/components/layout/sidebar.tsx`, remove the `recentNotes` useMemo block (~lines 394–403): delete `const recentNotes = useMemo(...)`. Remove all imports and variables only used by `recentNotes` if no longer needed.
- [X] T046 [BUG1] In `frontend/src/components/layout/sidebar.tsx`, remove the entire `{/* Recent Notes */}` render block (~lines 580–607): the `<div data-testid="note-list">` section containing `recentNotes.map(...)`. Also remove `Clock` from lucide imports if no longer used.

**Checkpoint**: Workspace sidebar shows only "Pinned" section. No "Recent" notes section.

---

## Phase 14: BUG-2 — Remove Pinned Section from Project Notes Panel

**Goal**: `ProjectNotesPanel` shows only the "Recent" section — no "Pinned" section (FR-018).
**Verify**: Navigate to any project sidebar → only "Recent" notes visible; no pin icon or "Pinned" header.

- [X] T047 [BUG2] In `frontend/src/components/projects/ProjectNotesPanel.tsx`, remove the `useNotes` call for pinned notes (`isPinned: true`): delete the `pinnedData` query and associated `pinnedNotes` / `isPinnedLoading` / `isPinnedError` variables.
- [X] T048 [BUG2] In `frontend/src/components/projects/ProjectNotesPanel.tsx`, remove the "Pinned" sub-section render block: the section header with `<Pin>` icon, the pinned note rows, and the "View all" link for pinned notes. Remove `Pin` from lucide imports if no longer used.

**Checkpoint**: `ProjectNotesPanel` renders only the Recent section. The pinned API call is no longer made.

---

## Phase 15: BUG-3 — Fix Backend Project + isPinned Combined Filter

**Goal**: `GET /notes?project_id=X&is_pinned=true/false` correctly filters by both params simultaneously (FR-019).
**Verify**: Backend test: project with 1 pinned + 2 unpinned notes → `?project_id=X&is_pinned=true` returns 1 note; `?project_id=X&is_pinned=false` returns 2 notes.

- [X] T049 [BUG3] In `backend/src/pilot_space/infrastructure/database/repositories/note_repository.py`, update `get_by_project` signature to accept `is_pinned: bool | None = None`. Add a WHERE clause: `if is_pinned is not None: query = query.where(Note.is_pinned == is_pinned)`. Also change the ORDER BY from `created_at.desc()` to `updated_at.desc()` to match recent-first semantics.
- [X] T050 [BUG3] In `backend/src/pilot_space/application/services/note/list_notes_service.py`, in the `elif payload.project_id:` branch (line ~97), update the `get_by_project` call to pass `is_pinned=payload.is_pinned`.

**Checkpoint**: `ListNotesService` correctly filters by both `project_id` AND `is_pinned` when both are provided.

---

## Phase 16: BUG-4 — Fix Create Note Returning Empty Content

**Goal**: `POST /workspaces/{id}/notes` returns the full note including `content`, so `useCreateNote.onSuccess` can seed the TanStack Query detail cache with template content (FR-020).
**Verify**: Create note with template → navigate to editor → template content visible immediately, no blank screen.

- [X] T051 [BUG4] In `backend/src/pilot_space/api/v1/routers/workspace_notes.py`, change the `create_workspace_note` endpoint: update `response_model=NoteDetailResponse` (was `NoteResponse`) and change the return statement to `return _note_to_detail_response(result.note)` (was `_note_to_response`).

**Checkpoint**: `POST /notes` response now includes `content` field. No frontend changes needed (TanStack Query cache is correctly populated).

---

## Phase 17: BUG-5 — Add Move Note Endpoint + Frontend Fix

**Goal**: Moving a note to a different project OR to root workspace (clearing `project_id`) works correctly via a new dedicated endpoint. Toast notification shown on success (FR-021).
**Verify**: Open note in "Frontend" project → "Move..." → "No project (root)" → note.projectId is null; breadcrumb reverts to "Notes > Title"; toast visible.

### Backend

- [X] T052 [BUG5] In `backend/src/pilot_space/api/v1/schemas/note.py`, add the `NoteMove` schema class: `class NoteMove(BaseSchema): project_id: UUID | None = Field(..., description="New project ID, or null to remove project association")`. Add `"NoteMove"` to `__all__`.
- [X] T053 [BUG5] In `backend/src/pilot_space/application/services/note/update_note_service.py`, add `clear_project_id: bool = False` field to `UpdateNotePayload`. In `execute()`, add handling before the existing `if payload.project_id is not None` block: `if payload.clear_project_id: note.project_id = None; fields_updated.append("project_id")`. Keep the existing `elif payload.project_id is not None` branch unchanged.
- [X] T054 [BUG5] In `backend/src/pilot_space/api/v1/routers/workspace_notes.py`, add the move endpoint:

  ```python
  @router.post(
      "/{workspace_id}/notes/{note_id}/move",
      response_model=NoteResponse,
      tags=["workspace-notes"],
      summary="Move a note to a different project or root workspace",
  )
  async def move_workspace_note(
      workspace_id: WorkspaceIdOrSlug,
      note_id: NoteIdPath,
      move_data: NoteMove,
      current_user_id: CurrentUserId,
      session: SessionDep,
      update_service: UpdateNoteServiceDep,
      workspace_repo: WorkspaceRepositoryDep,
  ) -> NoteResponse:
  ```

  Import `NoteMove` from schemas. Build `UpdateNotePayload` with `clear_project_id=True` when `move_data.project_id is None`, else `project_id=move_data.project_id`.

### Frontend

- [X] T055 [BUG5] In `frontend/src/services/api/notes.ts`, add `moveNote(workspaceId: string, noteId: string, projectId: string | null): Promise<Note>` method calling `apiClient.post<Note>(\`/workspaces/${workspaceId}/notes/${noteId}/move\`, { project_id: projectId })`.
- [X] T056 [BUG5] In `frontend/src/app/(workspace)/[workspaceSlug]/notes/[noteId]/page.tsx`:
  - Add `notesApi` import if not already imported.
  - Add `queryClient` from `useQueryClient()` at the top of the component.
  - Update `handleMove` to be an `async` callback that calls `notesApi.moveNote(workspaceId, noteId, newProjectId)` directly, then invalidates `notesKeys.detail(workspaceId, noteId)`, then calls `toast.success(newProjectId ? 'Note moved to project' : 'Note moved to workspace root')`.
  - Add `toast` import from `sonner` if not present.

**Checkpoint**: `POST /move` endpoint exists and works. Moving to "No project" clears `project_id`. Toast shown on success. Breadcrumb updates via cache invalidation.

---

## Phase 18: ENH-7 — TemplatePicker Integrated Project Selector

**Goal**: Replace the separate `MoveNoteDialog` second step in `useNewNoteFlow` with an inline searchable project combobox at the bottom of `TemplatePicker`. `onConfirm` now passes `(template, projectId)` (FR-022).
**Verify**: Click "New Note" → single `TemplatePicker` modal with project combobox at bottom → select template + project → note created; no second popup appears.

- [X] T057 [ENH7] In `frontend/src/features/notes/components/TemplatePicker.tsx`:
  - Update `TemplatePickerProps.onConfirm` signature from `(template: NoteTemplate | null) => void` to `(template: NoteTemplate | null, projectId: string | null) => void`.
  - Add `useProjects({ workspaceId })` call inside the component to fetch projects.
  - Add `selectedProjectId` state (`string | null`, default `null`) and `projectSearch` state (`string`, default `''`).
  - Add a project selector section below the template grid and above the confirm button: show a `<Select>` or Popover+Command combobox with a search input, "No project (root)" as first option, then filtered projects.
  - Update `handleConfirm` to call `onConfirm(selectedTemplate, selectedProjectId)`.
- [X] T058 [ENH7] In `frontend/src/components/layout/useNewNoteFlow.ts`:
  - Remove `showProjectPicker`, `pendingTemplate`, `handleProjectSelect`, `handleProjectClose` state/handlers.
  - Update `handleTemplateConfirm` signature to `(template: NoteTemplate | null, projectId: string | null)`.
  - In `handleTemplateConfirm`, directly call `onCreateNote({ title, content, ...(projectId ? { projectId } : {}) })` without an intermediate step.
  - Remove `showProjectPicker` and `handleProjectClose` from the returned object.
- [X] T059 [ENH7] In `frontend/src/components/layout/sidebar.tsx`:
  - Remove the `{newNoteFlow.showProjectPicker && <MoveNoteDialog ... />}` render block.
  - Remove `MoveNoteDialog` import from sidebar (it's still used in `InlineNoteHeader`; check that removing from sidebar doesn't break anything).
  - Verify the `<TemplatePicker onConfirm={newNoteFlow.handleTemplateConfirm} />` prop type still matches.

**Checkpoint**: New Note flow is single modal. `TemplatePicker` includes project combobox. No second popup.

---

## Phase 19: ENH-8 — MoveNoteDialog Search Input

**Goal**: `MoveNoteDialog` has a search input that filters the project list in real time (FR-023).
**Verify**: Open "Move..." → search "back" → only projects matching "back" in name shown; "No project (root)" always visible.

- [X] T060 [ENH8] In `frontend/src/components/editor/MoveNoteDialog.tsx`:
  - Add `search` state (`string`, default `''`).
  - Add a `filteredProjects` useMemo that filters `projects` by `project.name.toLowerCase().includes(search.toLowerCase())`.
  - Render a `<Input>` field (from `@/components/ui/input`) at the top of the project list section (below the header, above "No project (root)"), with `value={search}` and `onChange={(e) => setSearch(e.target.value)}`, `placeholder="Search projects..."`, `autoFocus`.
  - Replace `projects.map(...)` with `filteredProjects.map(...)`.
  - Add `Input` to imports.
  - Add `Search` icon from lucide to the input prefix for visual consistency (optional but preferred).

**Checkpoint**: MoveNoteDialog has a functional search input that filters projects.

---

## Phase 20: ENH-9 — Notes Page Project Filter with Chips

**Goal**: The notes list page has a multi-select project filter. Selected projects appear as dismissible chips below the search bar (FR-024).
**Verify**: Select 2 projects → notes reload filtered → 2 chips appear → remove one chip → notes reload with 1 project filter.

- [X] T061 [ENH9] In `frontend/src/features/notes/hooks/useInfiniteNotes.ts`, add `projectIds?: string[]` to the options interface and query params. When provided, pass as `projectId` repeated query params (or comma-separated if backend supports it; check `notesApi.list` first). If backend only accepts single `project_id`, implement client-side multi-project filtering as a fallback.
- [X] T062 [ENH9] In `frontend/src/app/(workspace)/[workspaceSlug]/notes/page.tsx`:
  - Add `selectedProjectIds` state: `const [selectedProjectIds, setSelectedProjectIds] = useState<string[]>([])`.
  - Add `pendingProjectIds` state for the dropdown before "Done" is pressed: `const [pendingProjectIds, setPendingProjectIds] = useState<string[]>([])`.
  - Add a "Projects" `<Button variant="outline" size="sm">` in the filter toolbar (next to the existing "Filter" button).
  - The button opens a `<DropdownMenu>` containing a `<Command>` with multi-select `<CommandItem>` for each project (checkboxes via `Check` icon). Include a search input at the top of the command list.
  - Add a "Done" `<DropdownMenuItem>` or `<Button>` inside the dropdown that calls `setSelectedProjectIds(pendingProjectIds)` and closes the dropdown.
  - Import `FolderKanban`, `X`, `Check` from lucide (if not already imported).
- [X] T063 [ENH9] In `frontend/src/app/(workspace)/[workspaceSlug]/notes/page.tsx`:
  - Pass `selectedProjectIds` to `useInfiniteNotes` as `projectIds`.
  - Render project filter chips between the toolbar and the content area.
    ```tsx
    {selectedProjectIds.length > 0 && (
      <div className="flex flex-wrap gap-2 px-4 py-2 sm:px-6 border-b border-border">
        {selectedProjectIds.map((pid) => {
          const project = projectMap.get(pid);
          return (
            <Badge key={pid} variant="secondary" className="gap-1 pr-1.5">
              <FolderKanban className="h-3 w-3" />
              <span className="text-xs">{project?.name ?? 'Project'}</span>
              <button
                type="button"
                onClick={() => {
                  const next = selectedProjectIds.filter((id) => id !== pid);
                  setSelectedProjectIds(next);
                  setPendingProjectIds(next);
                }}
                className="ml-0.5 rounded hover:bg-muted"
              >
                <X className="h-3 w-3" />
              </button>
            </Badge>
          );
        })}
        <button
          type="button"
          onClick={() => { setSelectedProjectIds([]); setPendingProjectIds([]); }}
          className="text-xs text-muted-foreground hover:text-foreground"
        >
          Clear all
        </button>
      </div>
    )}
    ```

**Checkpoint**: Notes page has project multi-select filter. Chips appear and are dismissible. Notes reload when filter changes.

---

## Phase 21: Polish & Validation (v3)

- [X] T064 [P] Run `cd frontend && pnpm type-check` and fix all TypeScript errors across v3 modified files: `sidebar.tsx`, `useNewNoteFlow.ts`, `ProjectNotesPanel.tsx`, `TemplatePicker.tsx`, `MoveNoteDialog.tsx`, `notes/[noteId]/page.tsx`, `notes/page.tsx`, `services/api/notes.ts`, `features/notes/hooks/useInfiniteNotes.ts`
- [X] T065 [P] Run `cd frontend && pnpm lint` and fix all ESLint errors across the v3 file set
- [X] T066 [P] Run `cd backend && uv run ruff check` and fix all lint errors in `workspace_notes.py`, `note.py`, `update_note_service.py`, `list_notes_service.py`, `note_repository.py`
- [X] T067 [P] Run `cd backend && uv run pyright` and fix all type errors in the same backend files

---

## Dependencies (v3)

### Phase Order

```
Phase 13 (BUG-1: remove Recent from workspace sidebar)     — independent
Phase 14 (BUG-2: remove Pinned from project panel)         — independent
Phase 15 (BUG-3: backend project+isPinned fix)             — independent (backend only)
Phase 16 (BUG-4: backend create returns NoteDetailResponse) — independent (backend only)
Phase 17 (BUG-5: move endpoint)
  └── T052 → T053 → T054 (backend, sequential)
  └── T055 → T056 (frontend, sequential)

Phase 18 (ENH-7: TemplatePicker project selector)
  └── T057 → T058 → T059 (sequential — TemplatePicker → useNewNoteFlow → sidebar)

Phase 19 (ENH-8: MoveNoteDialog search)                    — independent

Phase 20 (ENH-9: notes page project filter)
  └── T061 → T062 → T063 (sequential)

Phase 21 (Polish) — depends on all phases above
```

### Cross-task Dependencies

| Task | Depends On | Reason |
|---|---|---|
| T050 | T049 | Service uses updated `get_by_project` signature |
| T054 | T052, T053 | Router imports `NoteMove` schema and uses `clear_project_id` |
| T056 | T055 | `handleMove` uses `notesApi.moveNote` from T055 |
| T058 | T057 | `useNewNoteFlow` handles new `onConfirm(template, projectId)` sig |
| T059 | T058 | Sidebar removes project picker and passes updated props |
| T063 | T061, T062 | Chips render uses `selectedProjectIds` state and `projectMap` from T062 |
| T064–T067 | T045–T063 | Final quality gate |

### Parallel Opportunities

```
Phase 13+14+15+16 — all independent, run in parallel
BUG-5 backend (T052→T053→T054) || BUG-5 frontend (T055→T056) — parallel
ENH-7 (T057→T058→T059) || ENH-8 (T060) — parallel
ENH-9 (T061→T062→T063) — independent
Phase 21 (T064-T067) — all 4 tasks parallel
```

---

## Notes (v3)

- **T049** changes `get_by_project` sort from `created_at.desc()` to `updated_at.desc()` — this is the correct "recent" semantics for the panel.
- **T057** extends `TemplatePicker.onConfirm` — verify no other callers of `TemplatePicker` in the codebase before updating the signature.
- **T061** — check if `useInfiniteNotes` + backend supports multiple `project_id` params. If not, implement single `project_id` with client-side union filtering as a pragmatic fallback.
- **T056** — `handleMove` currently uses `useUpdateNote`. After this change, it calls `notesApi.moveNote` directly. Remove the `onMove` wiring from `useUpdateNote` if it's no longer needed.


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

## Phase 1: Setup (Base Feature — COMPLETE)

Verify reference patterns and confirm the working environment before writing any code.
No new infrastructure needed — this is a frontend-only change to an existing Next.js app.

- [x] T001 Read `frontend/src/components/layout/sidebar.tsx` lines 372–544 to capture the exact CSS class names and structure used for PINNED/RECENT note sections (visual reference for FR-008)
- [x] T002 Read `frontend/src/components/projects/ProjectSidebar.tsx` in full to understand mount point and line count before modification
- [x] T003 [P] Read `frontend/src/features/notes/hooks/useNotes.ts` to confirm `useNotes` signature accepts `projectId`, `isPinned`, and `pageSize` parameters
- [x] T004 [P] Read `frontend/src/features/notes/hooks/useCreateNote.ts` to confirm `useCreateNote` mutation accepts `projectId` in the data payload

**Checkpoint**: Reference patterns confirmed ✅

---

## Phase 2: Foundational (Skipped)

No new shared infrastructure required. All hooks, types, and API services already exist.

**Skipped**: `useNotes`, `useCreateNote`, `useWorkspaceStore`, `Note` type, `Project` type, and all API services are pre-existing.

---

## Phase 3: User Story 1 — Browse Project Notes from Sidebar (P1) 🎯 MVP — COMPLETE

**Goal**: Display Pinned and Recent project-scoped notes in the project sidebar desktop panel.
**Verify**: Navigate to any project with notes → sidebar shows Pinned/Recent sections with working links.

- [x] T005 [US1] Create `frontend/src/components/projects/ProjectNotesPanel.tsx` with full component skeleton, two `useNotes` calls (pinned + recent), props interface `{ project, workspaceSlug, workspaceId }`
- [x] T006 [US1] Implement loading state in `ProjectNotesPanel.tsx`: 3 `<Skeleton>` rows when either query `isLoading`
- [x] T007 [US1] Implement error state in `ProjectNotesPanel.tsx`: inline "Failed to load notes" text (non-crashing)
- [x] T008 [US1] Implement "Pinned" sub-section in `ProjectNotesPanel.tsx`: section header with `<Pin>` icon; up to 5 note rows as `<Link>` with `<FileText>` icon and truncated title
- [x] T009 [US1] Implement "Recent" sub-section in `ProjectNotesPanel.tsx`: same structure with `<Clock>` header icon; note rows exclude pinned notes
- [x] T010 [US1] Implement empty state in `ProjectNotesPanel.tsx`: "No notes yet" message when both lists empty
- [x] T011 [US1] Mount `ProjectNotesPanel` in `frontend/src/components/projects/ProjectSidebar.tsx` after `</nav>` tag inside `<aside>` desktop block with `<Separator />`

**Checkpoint**: US1 complete ✅

---

## Phase 4: User Story 2 — Create Project-Linked Note from Panel (P2) — COMPLETE

**Goal**: "New Note" button in the panel creates a project-linked note and navigates to the editor. Hidden for guests.
**Verify**: Click "New Note" → new note created → navigated to editor → note has correct `projectId`.

- [x] T012 [US2] Add `useCreateNote`, `useWorkspaceStore`, `useRouter` to `ProjectNotesPanel.tsx`; add mutation and `canCreateContent` check
- [x] T013 [US2] Add "New Note" `<Button>` to `ProjectNotesPanel.tsx`; hide for guest role
- [x] T014 [US2] Implement `handleCreateNote` in `ProjectNotesPanel.tsx`: mutates with `{ title: 'Untitled', projectId: project.id }`; navigates on success

**Checkpoint**: US2 complete ✅

---

## Phase 5: User Story 3 — Visual Polish and "View all" (P3) — COMPLETE

**Goal**: "View all →" links when total > 5; exact visual parity with workspace sidebar.
**Verify**: Side-by-side comparison shows identical styles; "View all" link appears when more than 5 notes.

- [x] T015 [P] [US3] Add "View all" link to Pinned sub-section in `ProjectNotesPanel.tsx` (when `pinnedData?.total > 5`)
- [x] T016 [P] [US3] Add "View all" link to Recent sub-section in `ProjectNotesPanel.tsx` (when `recentData?.total > 5`)
- [x] T017 [US3] Audit `ProjectNotesPanel.tsx` for visual parity with `sidebar.tsx` lines 488–544

**Checkpoint**: US3 complete ✅

---

## Phase 6: Enhancement 1 — Workspace Sidebar Pinned Notes: Project Label (P1)

**Goal**: Each pinned note in the workspace sidebar `<aside>` PINNED section shows a muted project name label after the note title when `note.projectId` is set (FR-011).

**Verify**: Open workspace sidebar → PINNED section → note linked to a project shows `"[Note title]    [Project name]"` with project name muted/truncated on the right.

### Implementation

- [x] T022 [ENH1] In `frontend/src/components/layout/sidebar.tsx`, add `useProjects` import from `@/features/projects/hooks`; add `useProjects({ workspaceId, enabled: !!workspaceId })` call in the `Sidebar` component body; derive `projectMap: Record<string, string>` via `useMemo` mapping `project.id → project.name` from `projectsData?.items ?? []`
- [x] T023 [ENH1] In `frontend/src/components/layout/sidebar.tsx`, extend the `pinnedNotes` useMemo (around line 372) to also map `projectId: note.projectId` alongside `id`, `title`, `href` — change the mapped type from `{ id, title, href }` to `{ id, title, projectId: string | undefined, href }`
- [x] T024 [ENH1] In `frontend/src/components/layout/sidebar.tsx`, update the pinned notes render block (around line 546–554) to show a project label: inside the `<Link>` row, after `<span className="truncate">{note.title}</span>`, add `{note.projectId && projectMap[note.projectId] && (<span className="ml-auto shrink-0 text-[10px] text-muted-foreground/60 truncate max-w-[60px]">{projectMap[note.projectId]}</span>)}`

**Checkpoint**: Workspace sidebar pinned notes show muted project name badge when note has `projectId`. Notes without `projectId` show no label.

---

## Phase 7: Enhancement 2 — Project Panel: Remove "New Note" Button (P1)

**Goal**: The project sidebar `ProjectNotesPanel` shows only Pinned and Recent lists — no "New Note" button (FR-012). The workspace sidebar "New Note" (enhanced in E3/E4) is the creation entry point.

**Verify**: Open project sidebar notes panel → no "New Note" button visible for any user role.

### Implementation

- [x] T025 [ENH2] In `frontend/src/components/projects/ProjectNotesPanel.tsx`, remove the `useCreateNote` import and its call (the `createNote` mutation); remove the `useWorkspaceStore` import (no longer needed); remove the `canCreateContent` const; remove the `handleCreateNote` useCallback; remove the `Plus` and `Loader2` lucide icon imports
- [x] T026 [ENH2] In `frontend/src/components/projects/ProjectNotesPanel.tsx`, remove the "New Note" button `<Button>` render block (the `{canCreateContent && (<Button ...>)}` block at the bottom of the return); ensure the component still closes cleanly

**Checkpoint**: `ProjectNotesPanel` renders only note lists — no creation button, no guest check needed.

---

## Phase 8: Enhancement 3 — Wire TemplatePicker into Workspace Sidebar "New Note" (P2)

**Goal**: Clicking "New Note" in the workspace sidebar opens the `TemplatePicker` modal (4 SDLC templates + blank) before creating a note, reusing the T-018 component from feature 018 (FR-013).

**Verify**: Click workspace sidebar "New Note" → `TemplatePicker` modal opens → selecting a template and confirming creates a note with that template's content → navigates to note editor.

### Implementation

- [x] T027 [ENH3] In `frontend/src/components/layout/sidebar.tsx`, add imports: `import { TemplatePicker } from '@/features/notes/components/TemplatePicker'` and `import type { NoteTemplate } from '@/services/api/templates'`
- [x] T028 [ENH3] In `frontend/src/components/layout/sidebar.tsx`, in the `Sidebar` component body, add state: `const [showTemplatePicker, setShowTemplatePicker] = useState(false)`; replace the existing `handleNewNote` callback body from `createNote.mutate(createNoteDefaults())` to `setShowTemplatePicker(true)`
- [x] T029 [ENH3] In `frontend/src/components/layout/sidebar.tsx`, add `handleTemplateConfirm` callback: `(template: NoteTemplate | null) => { setShowTemplatePicker(false); setPendingTemplate(template); setShowProjectPicker(true); }` — note: `setPendingTemplate` and `setShowProjectPicker` are added in T031 (E4); wire the close handler: `onClose={() => setShowTemplatePicker(false)}`
- [x] T030 [ENH3] In `frontend/src/components/layout/sidebar.tsx`, render `TemplatePicker` conditionally inside the component return (outside the `<div className="flex h-full flex-col">`, just before the closing JSX fragment): `{showTemplatePicker && (<TemplatePicker workspaceId={workspaceId} isAdmin={workspaceStore.currentUserRole === 'owner' || workspaceStore.currentUserRole === 'admin'} onConfirm={handleTemplateConfirm} onClose={() => setShowTemplatePicker(false)} />)}`

**Checkpoint**: Workspace sidebar "New Note" opens TemplatePicker modal. Closing without confirming cancels without creating a note.

---

## Phase 9: Enhancement 4 — New Note Project Selector Step (P2)

**Goal**: After template selection, show a project picker (`MoveNoteDialog`) so users can assign the new note to a project or root workspace (FR-014).

**Verify**: Click "New Note" → TemplatePicker → confirm template → project picker appears → selecting "No project" or a project → note created with correct `projectId`.

### Implementation

- [x] T031 [P] [ENH4] Create `frontend/src/components/editor/MoveNoteDialog.tsx` (~80 lines): props `{ workspaceId: string, currentProjectId?: string | null, confirmLabel?: string, onSelect: (projectId: string | null) => void, onClose: () => void }`; fetch projects via `useProjects({ workspaceId })`; render as a modal overlay (same pattern as `TemplatePicker` — fixed inset-0, backdrop-blur-sm); list projects as selectable rows; include "No project (root)" option as first item; confirm button calls `onSelect(selectedId)`; cancel calls `onClose()`; pre-select `currentProjectId` if provided
- [x] T032 [ENH4] In `frontend/src/components/layout/sidebar.tsx`, add `MoveNoteDialog` import from `@/components/editor/MoveNoteDialog`; add state: `const [pendingTemplate, setPendingTemplate] = useState<NoteTemplate | null | undefined>(undefined)` and `const [showProjectPicker, setShowProjectPicker] = useState(false)`
- [x] T033 [ENH4] In `frontend/src/components/layout/sidebar.tsx`, add `handleProjectSelect` callback: `(projectId: string | null) => { setShowProjectPicker(false); const template = pendingTemplate; setPendingTemplate(undefined); createNote.mutate({ title: template ? \`New ${template.name} Note\` : 'Untitled', content: template?.content ?? createNoteDefaults().content, ...(projectId ? { projectId } : {}) }); }`
- [x] T034 [ENH4] In `frontend/src/components/layout/sidebar.tsx`, render `MoveNoteDialog` conditionally: `{showProjectPicker && (<MoveNoteDialog workspaceId={workspaceId} onSelect={handleProjectSelect} onClose={() => { setShowProjectPicker(false); setPendingTemplate(undefined); }} />)}`

**Checkpoint**: Full New Note flow: click button → TemplatePicker → project selector → note created with both template content and `projectId` (or null for root).

---

## Phase 10: Enhancement 5 — Note View Breadcrumb Shows Project Path (P2)

**Goal**: The note header breadcrumb displays `Notes > [Project name] > [Note title]` when the note has a `projectId`; project name links to the project overview page (FR-015).

**Verify**: Open a note linked to a project → breadcrumb shows three segments with project name as clickable link → note without `projectId` shows two-segment breadcrumb `Notes > [title]`.

### Implementation

- [x] T035 [ENH5] In `frontend/src/components/editor/InlineNoteHeader.tsx`, add `projectId?: string` and `workspaceId?: string` to the `InlineNoteHeaderProps` interface; add `useProject` import from `@/features/projects/hooks`; inside the component, add: `const { data: project } = useProject({ projectId: projectId ?? '', enabled: !!projectId })`
- [x] T036 [ENH5] In `frontend/src/components/editor/InlineNoteHeader.tsx`, update the breadcrumb render section (after the `<Link href="/{workspaceSlug}/notes">` notes link, before the note title `<span>`): insert the project segment conditionally: `{project && (<><ChevronRight className="h-3 w-3 flex-shrink-0" /><Link href={\`/${workspaceSlug}/projects/${projectId}/overview\`} className="hover:text-foreground transition-colors hidden sm:inline truncate max-w-[80px]">{project.name}</Link></>)}`; keep the existing `<ChevronRight>` before the title
- [x] T037 [ENH5] In `frontend/src/components/editor/NoteCanvasLayout.tsx`, update the `<InlineNoteHeader>` render call (around line 195) to pass `projectId={projectId}` and `workspaceId={workspaceId}` — both are already in scope in `NoteCanvasLayout` props

**Checkpoint**: Note breadcrumb shows `Notes > [Project] > [Title]` for project-linked notes; project name is a link to project overview; breadcrumb hides project on mobile.

---

## Phase 11: Enhancement 6 — Note Options: "Move..." Action (P2)

**Goal**: The note `...` options dropdown gains a "Move..." item that opens `MoveNoteDialog` to reassign the note to a different project or root workspace (FR-016).

**Verify**: Open note → click `...` → click "Move..." → `MoveNoteDialog` opens with current project pre-selected → selecting new project patches the note → breadcrumb updates.

### Implementation

- [x] T038 [ENH6] In `frontend/src/components/editor/InlineNoteHeader.tsx`, add `onMove?: (projectId: string | null) => void` to `InlineNoteHeaderProps`; add `FolderInput` to lucide imports; add state `const [showMoveDialog, setShowMoveDialog] = useState(false)`; add `MoveNoteDialog` import from `./MoveNoteDialog`
- [x] T039 [ENH6] In `frontend/src/components/editor/InlineNoteHeader.tsx`, in the `<DropdownMenuContent>` block (around line 356), add before the `<DropdownMenuSeparator />` before Delete: `{onMove && (<DropdownMenuItem onClick={() => setShowMoveDialog(true)}><FolderInput className="mr-2 h-4 w-4" />Move...</DropdownMenuItem>)}`
- [x] T040 [ENH6] In `frontend/src/components/editor/InlineNoteHeader.tsx`, render `MoveNoteDialog` conditionally at the end of the component return (after the delete confirm `<Dialog>`): `{showMoveDialog && workspaceId && (<MoveNoteDialog workspaceId={workspaceId} currentProjectId={projectId ?? null} confirmLabel="Move Note" onSelect={(newProjectId) => { setShowMoveDialog(false); onMove?.(newProjectId); }} onClose={() => setShowMoveDialog(false)} />)}`
- [x] T041 [ENH6] In `frontend/src/components/editor/NoteCanvasLayout.tsx`, add `onMove?: (projectId: string | null) => void` to `NoteCanvasProps` (in `NoteCanvasEditor.tsx`); destructure `onMove` in `NoteCanvasLayout`; pass `onMove={onMove}` to `<InlineNoteHeader>`
- [x] T042 [ENH6] In `frontend/src/app/(workspace)/[workspaceSlug]/notes/[noteId]/page.tsx`, add `handleMove` callback: `const handleMove = useCallback((newProjectId: string | null) => { updateNote.mutate({ projectId: newProjectId ?? undefined }); }, [updateNote])`; pass `onMove={handleMove}` to the `<NoteCanvas>` component call

**Checkpoint**: "Move..." action in note options opens project picker; selecting a project (or "No project") patches the note and the breadcrumb reflects the new project.

---

## Phase 12: Polish & Validation

Cross-cutting concerns after all enhancements complete.

- [x] T043 [P] Run `cd frontend && pnpm type-check` and fix all TypeScript errors across modified files: `sidebar.tsx`, `ProjectNotesPanel.tsx`, `InlineNoteHeader.tsx`, `NoteCanvasLayout.tsx`, `NoteCanvasEditor.tsx`, `notes/[noteId]/page.tsx`, and new `MoveNoteDialog.tsx`
- [x] T044 [P] Run `cd frontend && pnpm lint` and fix all ESLint errors across the same file set

---

## Dependencies

### Phase Order

```
Phase 1–5 (Base Feature) — COMPLETE
  │
  ├── Phase 6 (ENH1: workspace sidebar project label) — independent, starts immediately
  ├── Phase 7 (ENH2: remove project panel New Note) — independent, starts immediately
  │
  ├── Phase 8 (ENH3: TemplatePicker wiring)
  │     └── Phase 9 (ENH4: project selector step) — depends on ENH3 state/handlers
  │
  ├── Phase 10 (ENH5: breadcrumb) — independent; T037 modifies NoteCanvasLayout
  │
  └── Phase 11 (ENH6: Move... option)
        ├── T031 (MoveNoteDialog) — created in ENH4 Phase 9; must exist before T038–T042
        ├── T038–T040 depend on MoveNoteDialog (T031)
        ├── T041 depends on T035–T037 (NoteCanvasProps already updated)
        └── T042 depends on T041
          └── Phase 12 (Polish) — runs after all enhancements
```

### Cross-task Dependencies

| Task | Depends On | Reason |
|---|---|---|
| T023 | T022 | Uses `projectMap` from T022 |
| T024 | T022, T023 | Renders from `projectMap` and extended `pinnedNotes` |
| T029 | T031 (scheduled) | References `setPendingTemplate`/`setShowProjectPicker` added in T032 |
| T032 | T027 | Imports TemplatePicker types |
| T033 | T032 | Uses `pendingTemplate` state |
| T034 | T031, T033 | Renders `MoveNoteDialog` with `handleProjectSelect` |
| T036 | T035 | Uses `project` data fetched in T035 |
| T037 | T035, T036 | Passes props to updated InlineNoteHeader |
| T038 | T031 | Imports `MoveNoteDialog` |
| T039 | T038 | Adds to DropdownMenuContent after state added |
| T040 | T038, T031 | Renders MoveNoteDialog with state from T038 |
| T041 | T035 | `NoteCanvasProps` already updated; adds `onMove` to same interface |
| T042 | T041 | Passes `onMove` to NoteCanvas which now accepts it |
| T043, T044 | All T022–T042 | Final quality gate |

### Parallel Opportunities

Tasks marked `[P]` within the same phase can run concurrently:

```
Phase 6:   T022 → T023 → T024  (sequential — build on each other)
Phase 7:   T025 → T026         (sequential — T026 removes code added in T025 setup)

Phase 8+9: T027 → T028 → T029 → T030 (sequential in sidebar.tsx)
           T031 [P] — new file, no deps — can run in parallel with T027–T030

Phase 10:  T035 → T036 → T037 (sequential in InlineNoteHeader → NoteCanvasLayout)

Phase 11:  T038 → T039 → T040 (sequential in InlineNoteHeader)
           T041 → T042         (sequential in NoteCanvasLayout → NoteDetailPage)
           T038–T040 || T041–T042 (parallel — different files)

Phase 12:  T043 || T044        (independent tools)
```

---

## Implementation Strategy

### MVP Enhancement Order

Start with the two independent, highest-value enhancements:

```
ENH2 (T025–T026) — Remove project panel New Note button (quick cleanup)
ENH1 (T022–T024) — Project label on workspace sidebar pinned notes
ENH3+4 (T027–T034) — New Note with TemplatePicker + project selector (T031 first)
ENH5 (T035–T037) — Note breadcrumb
ENH6 (T038–T042) — Move... option (depends on T031 from ENH4)
Polish (T043–T044)
```

### Suggested Execution

```
Day 1:
  ENH2: T025 → T026  (fast — remove code from ProjectNotesPanel.tsx)
  ENH1: T022 → T023 → T024  (workspace sidebar project label)

Day 2:
  ENH4 prep: T031 (create MoveNoteDialog.tsx — shared by ENH4 and ENH6)
  ENH3: T027 → T028 → T029 → T030  (TemplatePicker wiring)
  ENH4: T032 → T033 → T034  (project selector step)

Day 3:
  ENH5: T035 → T036 → T037  (breadcrumb)
  ENH6: T038 → T039 → T040 || T041 → T042  (Move... option)
  Polish: T043 || T044
```

---

## Notes

- **Base feature (T001–T021)** is complete — `ProjectNotesPanel.tsx` and `ProjectSidebar.tsx` integration are already implemented
- **T031 (`MoveNoteDialog.tsx`)** is the critical shared component — create it before ENH6 (T038) and it doubles as the project selector for ENH4 (T034)
- **ENH2 reverses ENH from the base spec** — the project panel originally had a "New Note" button (T012–T014); these are now removed per the enhancement spec (FR-012)
- **`useProject` for breadcrumb** uses TanStack Query — data is typically pre-cached from the project context page; no extra API cost
- **`NoteTemplate.content`** — verify `NoteTemplate` type has `content?: JSONContent` before T033; check `frontend/src/services/api/templates.ts`
- **`updateNote` with `projectId: undefined`** — verify backend `PATCH /notes/{id}` treats omitted/undefined `projectId` as "remove project link"; if not, use `null` explicitly

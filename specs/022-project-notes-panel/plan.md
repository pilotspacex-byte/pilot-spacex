# Implementation Plan: Project Notes Panel

**Branch**: `022-project-notes-panel` | **Date**: 2026-03-10 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/022-project-notes-panel/spec.md`
**Updated**: 2026-03-10 — v3: 5 bug fixes + 3 enhancements added

## Summary

The v2 enhancement round (T022–T044) is complete. This plan documents **5 bug fixes** and **3 enhancements** to be added on top of the v2 implementation. Changes span both frontend and backend.

### Bug Fixes

1. **BUG-1 — Remove Recent section from workspace sidebar** — Remove `{/* Recent Notes */}` block from `sidebar.tsx`.
2. **BUG-2 — Remove Pinned section from project panel** — Remove "Pinned" sub-section from `ProjectNotesPanel.tsx`; keep only Recent.
3. **BUG-3 — Recent panel not project-scoped** — Fix backend `ListNotesService` and `NoteRepository.get_by_project()` to support combined `project_id` + `is_pinned` filter.
4. **BUG-4 — Template content empty on creation** — Change `POST /workspaces/{id}/notes` to return `NoteDetailResponse` (with `content` field).
5. **BUG-5 — Move note cannot clear project_id** — Add `POST /workspaces/{id}/notes/{noteId}/move` endpoint; update frontend `handleMove` + add toast.

### Enhancements

1. **ENH-7 — TemplatePicker integrated project selector** — Replace the separate `MoveNoteDialog` second step in `useNewNoteFlow` with an inline searchable project selector at the bottom of `TemplatePicker`.
2. **ENH-8 — MoveNoteDialog search** — Add a search input to `MoveNoteDialog` to filter projects by name.
3. **ENH-9 — Notes page project filter** — Add multi-select project filter to notes page with chips below the search bar.

---

## Technical Context

**Language/Version**: TypeScript 5.x (strict mode) + Python 3.12
**Primary Dependencies**: React 18, TanStack Query v5, MobX 6, Next.js 15 App Router, shadcn/ui, TailwindCSS, FastAPI, SQLAlchemy 2.0 async
**Storage**: N/A for frontend; PostgreSQL for backend note model
**Testing**: Vitest + React Testing Library (frontend); pytest (backend)
**Target Platform**: Web (desktop sidebar, `md:` breakpoint and above)
**Constraints**: 700-line file limit per constitution; minimal new backend surface area
**Scale/Scope**: 5 bugs + 3 enhancements; backend changes touch 3 files; frontend changes touch 5 files + 1 new file

---

## Constitution Check (v3)

| Gate | Status | Notes |
|---|---|---|
| Frontend: React 18 + TypeScript strict | ✅ PASS | All changes use existing patterns |
| Frontend: TailwindCSS for styling | ✅ PASS | Reuses sidebar/panel CSS classes |
| Frontend: Feature-based MobX + TanStack Query | ✅ PASS | useProjects (TQ), useWorkspaceStore (MobX) |
| Backend: FastAPI + SQLAlchemy 2.0 async | ✅ PASS | New move endpoint follows existing router pattern |
| Backend: Pydantic v2 for validation | ✅ PASS | New `NoteMove` schema uses Pydantic v2 |
| Code: Type check passes | ✅ PASS | Nullable UUID handled via `UUID \| None` |
| Code: Lint passes | ✅ PASS | Will verify with `pnpm lint` + `uv run ruff check` |
| Code: No TODOs / mocks in production paths | ✅ PASS | Real API calls; real error states |
| Code: File size ≤ 700 lines | ✅ PASS | All files estimated to stay under limit |
| Security: Auth required for all API calls | ✅ PASS | Move endpoint uses `CurrentUserId` dep |
| Architecture: Layer boundaries respected | ✅ PASS | Router → Service → Repository pattern |
| AI: Human-in-the-loop principle | ✅ N/A | No AI features in these changes |

---

## Project Structure

### Source Code

```text
frontend/src/
├── components/
│   ├── layout/
│   │   ├── sidebar.tsx                        # MODIFY: remove Recent section (BUG-1)
│   │   └── useNewNoteFlow.ts                  # MODIFY: remove showProjectPicker step (ENH-7)
│   ├── editor/
│   │   └── MoveNoteDialog.tsx                 # MODIFY: add search input (ENH-8)
│   └── projects/
│       └── ProjectNotesPanel.tsx              # MODIFY: remove Pinned section (BUG-2)
├── features/
│   └── notes/
│       ├── components/
│       │   └── TemplatePicker.tsx             # MODIFY: add inline project selector (ENH-7)
│       └── hooks/
│           └── useCreateNote.ts               # MODIFY: invalidate note detail cache properly (BUG-4)
└── app/(workspace)/[workspaceSlug]/notes/
    └── page.tsx                               # MODIFY: add project filter chips (ENH-9)

backend/src/pilot_space/
├── api/v1/
│   ├── routers/
│   │   └── workspace_notes.py                # MODIFY: move endpoint + change create response type (BUG-4, BUG-5)
│   └── schemas/
│       └── note.py                           # MODIFY: add NoteMove schema (BUG-5)
├── application/services/note/
│   ├── list_notes_service.py                 # MODIFY: support project_id + is_pinned combined filter (BUG-3)
│   └── update_note_service.py                # MODIFY: support clearing project_id (BUG-5)
└── infrastructure/database/repositories/
    └── note_repository.py                    # MODIFY: get_by_project accepts is_pinned param (BUG-3)
```

---

## Implementation Approach

### Enhancement 1: Workspace sidebar — project label on pinned notes

**File**: `frontend/src/components/layout/sidebar.tsx`
**Scope**: `pinnedNotes` useMemo + render

Add `projectId` to the mapped note objects from `noteStore.pinnedNotes`:

```ts
// sidebar.tsx pinnedNotes useMemo (~line 372)
const pinnedNotes = useMemo(() => {
  return noteStore.pinnedNotes.slice(0, 5).map((note) => ({
    id: note.id,
    title: note.title,
    projectId: note.projectId,           // NEW
    href: `/${workspaceSlug}/notes/${note.id}`,
  }));
}, [noteStore.pinnedNotes, workspaceSlug]);
```

Fetch project names via `useProjects` (already cached from workspace load):

```ts
const { data: projectsData } = useProjects({ workspaceId, enabled: !!workspaceId });
const projectMap = useMemo(() => {
  const map: Record<string, string> = {};
  (projectsData?.items ?? []).forEach((p) => { map[p.id] = p.name; });
  return map;
}, [projectsData]);
```

Render the project label after each pinned note title (only when `note.projectId` is set):

```tsx
<Link href={note.href} ...>
  <FileText className="h-3 w-3 text-muted-foreground" />
  <span className="truncate flex-1">{note.title}</span>
  {note.projectId && projectMap[note.projectId] && (
    <span className="ml-auto shrink-0 text-[10px] text-muted-foreground/60 truncate max-w-[60px]">
      {projectMap[note.projectId]}
    </span>
  )}
</Link>
```

**Key references**:
- `sidebar.tsx` lines 372–378 (pinnedNotes useMemo)
- `sidebar.tsx` lines 539–554 (pinned notes render)
- `useProjects` hook: `frontend/src/features/projects/hooks/useProjects.ts`
- `Note.projectId?: string` in `frontend/src/types/note.ts` line 28

---

### Enhancement 2: Project notes panel — remove "New Note" button

**File**: `frontend/src/components/projects/ProjectNotesPanel.tsx`

The project sidebar's `ProjectNotesPanel` currently shows a "New Note" button (lines 167–183). Per the enhancement spec, the project panel should only display the Recent note section without a "New Note" button (the button belongs to the workspace-level sidebar flow enhanced in Enhancement 3).

Remove:
- The `useCreateNote` hook import and usage (lines 49–53)
- The `handleCreateNote` callback (lines 56–58)
- The "New Note" button render block (lines 167–183)
- The `canCreateContent` check (line 23) — no longer needed here
- The `useWorkspaceStore` import if no longer used (line 11)
- The `Plus` and `Loader2` icon imports (line 6)

**Result**: Panel is read-only list of pinned + recent notes only.

---

### Enhancement 3: Wire TemplatePicker into workspace sidebar "New Note"

**File**: `frontend/src/components/layout/sidebar.tsx`
**Reference**: T-018 from `specs/018-mvp-note-first-complete/tasks.md`

The existing `handleNewNote` handler (line 391) calls `createNote.mutate(createNoteDefaults())` directly, bypassing the already-built `TemplatePicker` component.

**Implementation**:

1. Add state:
```ts
const [showTemplatePicker, setShowTemplatePicker] = useState(false);
```

2. Replace `handleNewNote`:
```ts
const handleNewNote = useCallback(() => {
  setShowTemplatePicker(true);
}, []);
```

3. Handle template confirm:
```ts
const handleTemplateConfirm = useCallback((template: NoteTemplate | null) => {
  setShowTemplatePicker(false);
  createNote.mutate({
    title: template ? `New ${template.name} Note` : 'Untitled',
    content: template?.content ?? { type: 'doc', content: [{ type: 'paragraph' }] },
  });
}, [createNote]);
```

4. Render `TemplatePicker` conditionally (renders as a modal overlay over the entire page):
```tsx
{showTemplatePicker && (
  <TemplatePicker
    workspaceId={workspaceId}
    isAdmin={workspaceStore.currentUserRole === 'owner' || workspaceStore.currentUserRole === 'admin'}
    onConfirm={handleTemplateConfirm}
    onClose={() => setShowTemplatePicker(false)}
  />
)}
```

**Imports to add**:
```ts
import { TemplatePicker } from '@/features/notes/components/TemplatePicker';
import type { NoteTemplate } from '@/services/api/templates';
```

**Key references**:
- `TemplatePicker` props: `frontend/src/features/notes/components/TemplatePicker.tsx` lines 35–41
- `sidebar.tsx` lines 391–393 (`handleNewNote`)
- `sidebar.tsx` lines 597–606 (New Note button)

---

### Enhancement 4: New Note dialog includes project selector

**File**: `frontend/src/components/layout/sidebar.tsx`

After the user confirms a template in `TemplatePicker`, show a second step that lets them assign the new note to a project or leave it at root workspace level.

**Implementation**:

Add a second modal state and a `pendingTemplate` state:

```ts
const [pendingTemplate, setPendingTemplate] = useState<NoteTemplate | null | undefined>(undefined);
const [showProjectPicker, setShowProjectPicker] = useState(false);
```

Update `handleTemplateConfirm` to stage the template then open project picker:
```ts
const handleTemplateConfirm = useCallback((template: NoteTemplate | null) => {
  setShowTemplatePicker(false);
  setPendingTemplate(template);
  setShowProjectPicker(true);
}, []);
```

Handle project selection:
```ts
const handleProjectSelect = useCallback((projectId: string | null) => {
  setShowProjectPicker(false);
  const template = pendingTemplate;
  setPendingTemplate(undefined);
  createNote.mutate({
    title: template ? `New ${template.name} Note` : 'Untitled',
    content: template?.content ?? { type: 'doc', content: [{ type: 'paragraph' }] },
    ...(projectId ? { projectId } : {}),
  });
}, [pendingTemplate, createNote]);
```

The project picker is a simple inline dialog using existing shadcn/ui primitives:

```tsx
{showProjectPicker && (
  <ProjectPickerDialog
    workspaceId={workspaceId}
    onSelect={handleProjectSelect}
    onClose={() => { setShowProjectPicker(false); setPendingTemplate(undefined); }}
  />
)}
```

`ProjectPickerDialog` is a new small component (~60 lines) — see separate section below.

---

### Enhancement 4b: Create `MoveNoteDialog.tsx` (shared by Enhancement 4 and 6)

**File**: `frontend/src/components/editor/MoveNoteDialog.tsx` (new, ~80 lines)

A reusable project picker dialog used by both the "New Note" project selection step and the "Move..." note option.

```tsx
interface MoveNoteDialogProps {
  workspaceId: string;
  /** Current projectId (for Move... — pre-selects current project). null = root. */
  currentProjectId?: string | null;
  /** Label for the confirm button */
  confirmLabel?: string;
  onSelect: (projectId: string | null) => void;
  onClose: () => void;
}
```

Internal structure:
- Fetches projects via `useProjects({ workspaceId })`
- Lists projects as selectable rows
- "No project (root)" option always first
- Confirm button calls `onSelect(selectedProjectId)`
- Cancel calls `onClose()`

Render as a modal overlay (same pattern as `TemplatePicker`).

**Key references**:
- `useProjects` hook: `frontend/src/features/projects/hooks/useProjects.ts`
- `TemplatePicker` modal pattern: `frontend/src/features/notes/components/TemplatePicker.tsx` lines 285–300

---

### Enhancement 5: Note breadcrumb shows project path

**File**: `frontend/src/components/editor/InlineNoteHeader.tsx`

**Current breadcrumb** (lines 233–243):
```
Notes (link) > [Title]
```

**Target breadcrumb**:
```
Notes (link) > [Project name] (link) > [Title]
```

**Changes**:

1. Add `projectId?: string` and `workspaceId?: string` to `InlineNoteHeaderProps`:
```ts
/** Project ID — when set, renders project name in breadcrumb */
projectId?: string;
/** Workspace ID — needed to build project link href */
workspaceId?: string;
```

2. Inside the component, fetch project data conditionally:
```ts
const { data: project } = useProject({
  projectId: projectId ?? '',
  enabled: !!projectId,
});
```

3. Update breadcrumb render:
```tsx
{/* Breadcrumb */}
<Link href={`/${workspaceSlug}/notes`} ...>
  <FileText ... />
  <span className="hidden sm:inline">Notes</span>
</Link>
<ChevronRight className="h-3 w-3 flex-shrink-0" />
{project && (
  <>
    <Link
      href={`/${workspaceSlug}/projects/${projectId}/overview`}
      className="hover:text-foreground transition-colors hidden sm:inline truncate max-w-[80px]"
    >
      {project.name}
    </Link>
    <ChevronRight className="h-3 w-3 flex-shrink-0 hidden sm:block" />
  </>
)}
<span className="text-foreground truncate max-w-[80px] sm:max-w-[120px] md:max-w-[180px] lg:max-w-[240px] font-medium">
  {title || 'Untitled'}
</span>
```

4. Pass through `projectId` and `workspaceId` from `NoteCanvasLayout.tsx` (already receives `projectId` as prop; needs to also pass `workspaceId`):
```tsx
<InlineNoteHeader
  ...
  projectId={projectId}
  workspaceId={workspaceId}
/>
```

**Key references**:
- `InlineNoteHeader` props: `InlineNoteHeader.tsx` lines 94–127
- `InlineNoteHeader` render: `InlineNoteHeader.tsx` lines 232–243
- `NoteCanvasLayout.tsx` lines 184–200 (where InlineNoteHeader is rendered, `projectId` already in scope)
- `useProject` hook: `frontend/src/features/projects/hooks/useProject.ts`

---

### Enhancement 6: Note options — "Move..." action

**File**: `frontend/src/components/editor/InlineNoteHeader.tsx`

Add a "Move..." option to the DropdownMenuContent that opens `MoveNoteDialog`.

**Changes**:

1. Add `onMove?: (projectId: string | null) => void` to `InlineNoteHeaderProps`.

2. Add state for the dialog:
```ts
const [showMoveDialog, setShowMoveDialog] = useState(false);
```

3. Add `MoveNoteDialog` import:
```ts
import { MoveNoteDialog } from './MoveNoteDialog';
```

4. Add menu item before the separator before Delete:
```tsx
{onMove && (
  <DropdownMenuItem onClick={() => setShowMoveDialog(true)}>
    <FolderInput className="mr-2 h-4 w-4" />
    Move...
  </DropdownMenuItem>
)}
```

5. Add `FolderInput` to lucide imports.

6. Render dialog:
```tsx
{showMoveDialog && workspaceId && (
  <MoveNoteDialog
    workspaceId={workspaceId}
    currentProjectId={projectId ?? null}
    confirmLabel="Move Note"
    onSelect={(newProjectId) => {
      setShowMoveDialog(false);
      onMove?.(newProjectId);
    }}
    onClose={() => setShowMoveDialog(false)}
  />
)}
```

7. In `NoteDetailPage` (`notes/[noteId]/page.tsx`), wire `handleMove`:
```ts
const handleMove = useCallback((newProjectId: string | null) => {
  updateNote.mutate({ projectId: newProjectId ?? undefined });
}, [updateNote]);
```

Pass to `NoteCanvas`:
```tsx
onMove={handleMove}
```

8. In `NoteCanvasLayout.tsx`, forward `onMove` through to `InlineNoteHeader`:
- Add `onMove?: (projectId: string | null) => void` to `NoteCanvasProps`
- Pass it down to `InlineNoteHeader`

**Key references**:
- `InlineNoteHeader` dropdown: `InlineNoteHeader.tsx` lines 344–406
- `NoteDetailPage` handlers: `notes/[noteId]/page.tsx` lines 276–309
- `useUpdateNote` supports `projectId`: `UpdateNoteData.projectId?: string` in `types/note.ts` line 116
- `NoteCanvasLayout` props: `NoteCanvasLayout.tsx` lines 84–106

---

---

## v3 Implementation Approach (Bug Fixes + Enhancements)

### BUG-1: Remove Recent section from workspace sidebar

**File**: `frontend/src/components/layout/sidebar.tsx`

Remove the entire `{/* Recent Notes */}` block (the `<div data-testid="note-list">` block containing `recentNotes.map(...)`) and the `recentNotes` useMemo (lines ~394-403).

The sidebar will only show the "Pinned" section going forward.

**Key references**:
- `sidebar.tsx` lines ~394-403 (`recentNotes` useMemo)
- `sidebar.tsx` lines ~580-607 (`{/* Recent Notes */}` block)

---

### BUG-2: Remove Pinned section from project notes panel

**File**: `frontend/src/components/projects/ProjectNotesPanel.tsx`

Remove:
- The `useNotes` call for pinned notes (`isPinned: true`)
- The "Pinned" sub-section render block (section header + pinned note rows + "View all" link)
- The `Pin` lucide icon import (if no longer used)
- The `pinnedData` variable and related loading/error state

Keep only the Recent sub-section.

---

### BUG-3: Fix backend project + isPinned filter

**Files**:
- `backend/src/pilot_space/infrastructure/database/repositories/note_repository.py`
- `backend/src/pilot_space/application/services/note/list_notes_service.py`

**Repository change** — Update `get_by_project` to accept optional `is_pinned`:

```python
async def get_by_project(
    self,
    project_id: UUID,
    *,
    is_pinned: bool | None = None,
    include_deleted: bool = False,
    limit: int | None = None,
) -> Sequence[Note]:
    query = select(Note).where(Note.project_id == project_id)
    if not include_deleted:
        query = query.where(Note.is_deleted == False)  # noqa: E712
    if is_pinned is not None:
        query = query.where(Note.is_pinned == is_pinned)
    query = query.order_by(Note.updated_at.desc())
    if limit:
        query = query.limit(limit)
    result = await self.session.execute(query)
    return result.scalars().all()
```

**Service change** — Update `ListNotesService.execute()` to pass `is_pinned` when calling `get_by_project`:

```python
elif payload.project_id:
    notes = await self._note_repo.get_by_project(
        payload.project_id,
        is_pinned=payload.is_pinned,  # NEW: pass through
        limit=payload.limit,
    )
```

---

### BUG-4: Fix note creation returning empty content

**File**: `backend/src/pilot_space/api/v1/routers/workspace_notes.py`

Change `create_workspace_note` to return `NoteDetailResponse` instead of `NoteResponse`:

```python
@router.post(
    "/{workspace_id}/notes",
    response_model=NoteDetailResponse,   # CHANGED from NoteResponse
    ...
)
async def create_workspace_note(...) -> NoteDetailResponse:
    ...
    return _note_to_detail_response(result.note)   # CHANGED from _note_to_response
```

This ensures the created note's `content` is included in the response so `useCreateNote.onSuccess` can cache it correctly in TanStack Query.

---

### BUG-5: Add move note endpoint + frontend fix

**Backend — Schema** (`backend/src/pilot_space/api/v1/schemas/note.py`):

```python
class NoteMove(BaseSchema):
    """Schema for moving a note to a different project."""
    project_id: UUID | None = Field(
        default=...,  # required — caller must pass null explicitly
        description="New project ID, or null to remove project association",
    )
```

**Backend — UpdateNoteService** (`update_note_service.py`):

Add a `move_project_id` sentinel field or update the logic to allow clearing `project_id`:

The cleanest approach: change the service condition from
```python
if payload.project_id is not None:
```
to a new `move_project_id: UUID | None = UNSET` sentinel pattern. However, since this requires a new endpoint, it's simpler to handle in a new `move_note` router function that directly sets `note.project_id = payload.project_id` (allowing None).

**Backend — Router** (`workspace_notes.py`):

```python
@router.post(
    "/{workspace_id}/notes/{note_id}/move",
    response_model=NoteResponse,
    tags=["workspace-notes"],
    summary="Move a note to a different project",
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
    """Move a note to a different project or root workspace.
    Pass project_id=null to remove project association.
    """
    ...
```

Since `UpdateNotePayload.project_id` can never be `None` (service checks `is not None`), the move endpoint must directly update via the repository or a modified payload. Simplest approach: add a `clear_project_id: bool = False` field to `UpdateNotePayload`:

```python
@dataclass(slots=True)
class UpdateNotePayload:
    ...
    clear_project_id: bool = False  # NEW: when True, sets project_id = None
```

And in the service:
```python
if payload.clear_project_id:
    note.project_id = None
    fields_updated.append("project_id")
elif payload.project_id is not None:
    note.project_id = payload.project_id
    fields_updated.append("project_id")
```

**Frontend — `notesApi`** (`frontend/src/services/api/notes.ts`):

```ts
moveNote(workspaceId: string, noteId: string, projectId: string | null): Promise<Note> {
  return apiClient.post<Note>(`/workspaces/${workspaceId}/notes/${noteId}/move`, {
    project_id: projectId,
  });
},
```

**Frontend — `useUpdateNote`** (`frontend/src/features/notes/hooks/useUpdateNote.ts`):

Add `isPinned?: boolean` to `UpdateNoteData` and keep `projectId?: string`. For the move operation, a separate hook or the page's `handleMove` should call `notesApi.moveNote` directly with a toast.

**Frontend — `notes/[noteId]/page.tsx`**:

Update `handleMove`:
```ts
const handleMove = useCallback(
  async (newProjectId: string | null) => {
    try {
      await notesApi.moveNote(workspaceId, noteId, newProjectId);
      queryClient.invalidateQueries({ queryKey: notesKeys.detail(workspaceId, noteId) });
      toast.success(newProjectId ? 'Note moved to project' : 'Note moved to workspace root');
    } catch (err) {
      toast.error('Failed to move note');
    }
  },
  [workspaceId, noteId, queryClient]
);
```

---

### ENH-7: TemplatePicker integrated project selector

**File**: `frontend/src/features/notes/components/TemplatePicker.tsx`

Add a project selector (combobox with search) at the bottom of the `TemplatePicker` confirm section. The `onConfirm` signature is extended to pass the selected `projectId`:

```ts
// New prop signature
onConfirm: (template: NoteTemplate | null, projectId: string | null) => void;
```

Inside `TemplatePicker`:
1. Add `useProjects({ workspaceId })` call
2. Add `selectedProjectId` local state
3. Render a searchable combobox (`<Command>` / shadcn Popover+Command pattern) below the template list/confirm button
4. Pass `selectedProjectId` to `onConfirm`

**File**: `frontend/src/components/layout/useNewNoteFlow.ts`

Update `handleTemplateConfirm` signature to accept `(template, projectId)`:
```ts
const handleTemplateConfirm = useCallback((template: NoteTemplate | null, projectId: string | null) => {
  setShowTemplatePicker(false);
  onCreateNote({
    title: template ? `New ${template.name} Note` : 'Untitled',
    content: (template?.content ?? { type: 'doc', content: [{ type: 'paragraph' }] }) as JSONContent,
    ...(projectId ? { projectId } : {}),
  });
}, [onCreateNote]);
```

Remove `setPendingTemplate`, `showProjectPicker`, `handleProjectSelect`, `handleProjectClose` from the hook — the two-step modal flow is no longer needed.

**File**: `frontend/src/components/layout/sidebar.tsx`

Remove `MoveNoteDialog` render block for `{newNoteFlow.showProjectPicker && ...}` and the `handleProjectSelect`/`handleProjectClose` props.

---

### ENH-8: MoveNoteDialog search input

**File**: `frontend/src/components/editor/MoveNoteDialog.tsx`

Add a search `<Input>` at the top of the project list. Filter `projects` via `useMemo`:

```tsx
const [search, setSearch] = useState('');
const filteredProjects = useMemo(
  () => projects.filter((p) => p.name.toLowerCase().includes(search.toLowerCase())),
  [projects, search]
);
```

Render the input:
```tsx
<div className="px-3 pt-2 pb-1">
  <Input
    value={search}
    onChange={(e) => setSearch(e.target.value)}
    placeholder="Search projects..."
    className="h-8 text-sm"
    autoFocus
  />
</div>
```

Replace `projects.map(...)` with `filteredProjects.map(...)`.

---

### ENH-9: Notes page project filter chips

**File**: `frontend/src/app/(workspace)/[workspaceSlug]/notes/page.tsx`

1. Add `selectedProjectIds` state: `const [selectedProjectIds, setSelectedProjectIds] = useState<string[]>([])`

2. Add a "Projects" button to the filter toolbar (next to "Filter" button):
   - Opens a `<DropdownMenu>` containing a `<Command>` with multi-select checkboxes for each project
   - Has a "Done" button that closes the dropdown and applies the filter

3. Pass `selectedProjectIds` to `useInfiniteNotes`:
   ```ts
   const { data, ... } = useInfiniteNotes({
     workspaceId,
     projectIds: selectedProjectIds.length > 0 ? selectedProjectIds : undefined,
     isPinned: filterPinned,
     pageSize: 20,
     enabled: !!workspaceId,
   });
   ```
   Note: `useInfiniteNotes` currently doesn't support `projectIds` — this needs to be added (or handled client-side if the note list is small enough, but for correctness add server-side filtering).

4. Render project filter chips below the toolbar:
   ```tsx
   {selectedProjectIds.length > 0 && (
     <div className="flex flex-wrap gap-2 px-4 py-2 sm:px-6 border-b border-border">
       {selectedProjectIds.map((pid) => {
         const project = projectMap.get(pid);
         return (
           <Badge key={pid} variant="secondary" className="gap-1.5 pr-1">
             <FolderKanban className="h-3 w-3" />
             {project?.name ?? pid}
             <button onClick={() => setSelectedProjectIds((ids) => ids.filter((id) => id !== pid))}>
               <X className="h-3 w-3" />
             </button>
           </Badge>
         );
       })}
     </div>
   )}
   ```

5. Update `useInfiniteNotes` hook to accept `projectIds?: string[]` parameter and pass it to the API.

---

## Updated Data Model (v3)

### Backend additions

| Change | File | Details |
|---|---|---|
| `NoteMove` schema | `schemas/note.py` | `project_id: UUID \| None` (required, nullable) |
| `UpdateNotePayload.clear_project_id` | `update_note_service.py` | `bool = False` sentinel to clear project_id |
| `NoteRepository.get_by_project(is_pinned)` | `note_repository.py` | Added optional `is_pinned: bool \| None` param |
| `ListNotesService` | `list_notes_service.py` | Passes `is_pinned` to `get_by_project` |

### Frontend additions

| Change | File | Details |
|---|---|---|
| `notesApi.moveNote` | `services/api/notes.ts` | New method calling `POST /move` |
| `TemplatePicker.onConfirm` signature | `TemplatePicker.tsx` | `(template, projectId)` instead of `(template)` |
| `useNewNoteFlow` simplified | `useNewNoteFlow.ts` | Remove two-step flow; single confirm with projectId |
| `selectedProjectIds` | `notes/page.tsx` | New state for project filter |
| `useInfiniteNotes({ projectIds })` | `useInfiniteNotes.ts` | New optional param |

---

## API Calls (v3 additions)

| Action | Endpoint |
|---|---|
| Move note to project/root | `POST /api/v1/workspaces/{id}/notes/{noteId}/move` |
| Create note (now returns content) | `POST /api/v1/workspaces/{id}/notes` → NoteDetailResponse |
| List notes filtered by projectId+isPinned | `GET /api/v1/workspaces/{id}/notes?project_id=X&is_pinned=true/false` (fixed) |

---

## Constitution Check (Post-Design v3)

| Gate | Status | Notes |
|---|---|---|
| File size ≤ 700 lines | ✅ PASS | All files estimated under limit |
| No duplicate API calls | ✅ PASS | `useProjects` cached; `useInfiniteNotes` single call |
| Type safety | ✅ PASS | Nullable UUID handled cleanly in both FE and BE |
| Backend: async SQLAlchemy | ✅ PASS | All new repo methods use async patterns |
| Security: Auth on new endpoint | ✅ PASS | `CurrentUserId` dep on move endpoint |
| No N+1 queries | ✅ PASS | Project list fetched once; note list filtered server-side |

---

## Key Reference Patterns (v3)

| Pattern | Source |
|---|---|
| Existing router pattern | `workspace_notes.py` `update_workspace_note` |
| NoteDetailResponse schema | `schemas/note.py` + `_note_to_detail_response()` |
| Repository pattern | `note_repository.py` `get_by_project` |
| shadcn Command/combobox | Used in many places in `frontend/src/components/` |
| Badge + X chip | Used in `notes/page.tsx` filter area |
| useInfiniteNotes | `frontend/src/features/notes/hooks/useInfiniteNotes.ts` |

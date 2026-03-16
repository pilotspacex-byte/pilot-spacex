# Data Model: Project Notes Panel (022)

**Date**: 2026-03-10
**Updated**: 2026-03-10 — v3: Bug fix data flows + new backend schema additions

This feature is **primarily frontend** but v3 adds **backend changes** for bug fixes.

---

## Entities Used

### Note (existing)

Relevant fields consumed by the panel and enhancements:

| Field | Type | Notes |
|---|---|---|
| `id` | `string` (UUID) | Navigation link key |
| `title` | `string` | Displayed in panel row (truncated to 1 line) |
| `isPinned` | `boolean` | Determines Pinned vs Recent sub-section |
| `projectId` | `string?` | Filter: only notes where `projectId === project.id`; also used for breadcrumb and Move dialog |
| `updatedAt` | `string` (ISO) | Sort order for Recent sub-section |

Source: `frontend/src/types/note.ts`

### Project (existing)

Relevant fields consumed by the panel and enhancements:

| Field | Type | Notes |
|---|---|---|
| `id` | `string` (UUID) | Used as `projectId` filter in API call; used as option value in project picker |
| `name` | `string` | Displayed as label in workspace sidebar pinned notes; used in breadcrumb; listed in project picker |
| `workspaceId` | `string` (UUID) | Used to build `workspaceSlug`-based note links |

Source: `frontend/src/types/workspace.ts`

---

## Data Flow

### Base Feature: Project panel

```
ProjectSidebar
  └── ProjectNotesPanel (props: project, workspaceSlug, workspaceId)
        ├── useNotes({ workspaceId, projectId: project.id, isPinned: true, pageSize: 5 })
        │     → TanStack Query → GET /workspaces/{id}/notes?project_id=X&is_pinned=true&pageSize=5
        │     → pinnedNotes: Note[]
        └── useNotes({ workspaceId, projectId: project.id, isPinned: false, pageSize: 5 })
              → TanStack Query → GET /workspaces/{id}/notes?project_id=X&is_pinned=false&pageSize=5
              → recentNotes: Note[]
```

### Enhancement 1: Workspace sidebar project label

```
sidebar.tsx
  ├── noteStore.pinnedNotes → Note[] (includes projectId?: string)
  └── useProjects({ workspaceId })
        → TanStack Query → GET /workspaces/{id}/projects
        → projectMap: Record<string, string>  (id → name)
  → Render: pinnedNotes[i].title + projectMap[pinnedNotes[i].projectId]
```

### Enhancement 3+4: New Note with TemplatePicker + project selector

```
sidebar.tsx (showTemplatePicker state)
  └── TemplatePicker
        → onConfirm(template: NoteTemplate | null)
        → sets pendingTemplate, opens showProjectPicker
  └── MoveNoteDialog (project selector step)
        ├── useProjects({ workspaceId })
        └── onSelect(projectId: string | null)
              → createNote.mutate({ title, content, projectId })
              → POST /workspaces/{id}/notes
```

### Enhancement 5: Note breadcrumb

```
NoteDetailPage
  └── NoteCanvasLayout (props: projectId, workspaceId)
        └── InlineNoteHeader (props: projectId, workspaceId)
              └── useProject({ projectId, enabled: !!projectId })
                    → TanStack Query → GET /projects/{id}
                    → project: Project
              → Render: Notes > [project.name link] > [note.title]
```

### Enhancement 6: Move note

```
NoteDetailPage
  └── NoteCanvasLayout (props: onMove)
        └── InlineNoteHeader (props: onMove, projectId, workspaceId)
              └── MoveNoteDialog (when "Move..." clicked)
                    ├── useProjects({ workspaceId })
                    └── onSelect(newProjectId: string | null)
                          → updateNote.mutate({ projectId: newProjectId ?? undefined })
                          → PATCH /workspaces/{id}/notes/{noteId}
```

---

## API Calls (existing endpoints, no changes)

### List pinned project notes
```
GET /api/v1/workspaces/{workspaceId}/notes
  ?project_id={projectId}
  &is_pinned=true
  &pageSize=5
```

### List recent project notes (not pinned)
```
GET /api/v1/workspaces/{workspaceId}/notes
  ?project_id={projectId}
  &is_pinned=false
  &pageSize=5
```

### Create project-linked note
```
POST /api/v1/workspaces/{workspaceId}/notes
Body: {
  "title": "...",
  "workspaceId": "{workspaceId}",
  "projectId": "{projectId}",        // optional
  "content": { ... }                  // optional template content
}
```

### Move note (update projectId)
```
PATCH /api/v1/workspaces/{workspaceId}/notes/{noteId}
Body: {
  "projectId": "{newProjectId}"      // or omit to remove project link
}
```

### List projects (for picker and label)
```
GET /api/v1/workspaces/{workspaceId}/projects
```

### Get single project (for breadcrumb)
```
GET /api/v1/projects/{projectId}
```

All endpoints are authenticated (Supabase Auth header) and RLS-enforced.

---

## State (UI only, no persistent state)

### Base Feature

| State | Location | Type |
|---|---|---|
| Loading (pinned) | TanStack Query | `boolean` |
| Loading (recent) | TanStack Query | `boolean` |
| Error (pinned) | TanStack Query | `Error \| null` |
| Error (recent) | TanStack Query | `Error \| null` |
| Create pending | TanStack Query mutation | `boolean` |

### Enhancement Features

| State | Location | Type | Purpose |
|---|---|---|---|
| `showTemplatePicker` | `sidebar.tsx` local | `boolean` | Controls TemplatePicker modal |
| `pendingTemplate` | `sidebar.tsx` local | `NoteTemplate \| null \| undefined` | Staged template awaiting project selection |
| `showProjectPicker` | `sidebar.tsx` local | `boolean` | Controls project selector modal after template |
| `showMoveDialog` | `InlineNoteHeader` local | `boolean` | Controls Move... dialog |

> **v3 UPDATE**: `pendingTemplate` and `showProjectPicker` will be removed when ENH-7 integrates the project selector into `TemplatePicker`.

---

## v3 Backend Schema Additions

### NoteMove (new)

```python
class NoteMove(BaseSchema):
    project_id: UUID | None  # required field; null = remove project association
```

Source: `backend/src/pilot_space/api/v1/schemas/note.py`

### UpdateNotePayload additions

```python
@dataclass(slots=True)
class UpdateNotePayload:
    ...
    clear_project_id: bool = False  # NEW: when True, sets note.project_id = None
```

Source: `backend/src/pilot_space/application/services/note/update_note_service.py`

---

## v3 Data Flows

### BUG-3: ProjectNotesPanel pinned/recent split (fixed)

```
ProjectNotesPanel
  ├── useNotes({ workspaceId, projectId: project.id, isPinned: true, pageSize: 5 })
  │     → GET /workspaces/{id}/notes?project_id=X&is_pinned=true&pageSize=5
  │     → ListNotesService.execute() → get_by_project(project_id, is_pinned=True) ✅
  └── useNotes({ workspaceId, projectId: project.id, isPinned: false, pageSize: 5 })
        → GET /workspaces/{id}/notes?project_id=X&is_pinned=false&pageSize=5
        → ListNotesService.execute() → get_by_project(project_id, is_pinned=False) ✅
```

### BUG-4: Create note with template (fixed)

```
useNewNoteFlow.handleTemplateConfirm(template, projectId)
  → useCreateNote.mutate({ title, content: template.content, projectId })
  → POST /workspaces/{id}/notes
  → backend returns NoteDetailResponse (WITH content) ✅
  → useCreateNote.onSuccess: setQueryData(detail key, note with content) ✅
  → NoteDetailPage: note.content from cache is non-null ✅
```

### BUG-5: Move note to project/root (fixed)

```
InlineNoteHeader "Move..." → MoveNoteDialog → onSelect(newProjectId)
  → NoteDetailPage.handleMove(newProjectId: string | null)
  → notesApi.moveNote(workspaceId, noteId, newProjectId)
  → POST /workspaces/{id}/notes/{noteId}/move
    Body: { project_id: newProjectId }  // null = remove project
  → UpdateNotePayload(note_id, clear_project_id=True)  // when newProjectId is null
  → note.project_id = None ✅
  → toast.success("Note moved...") ✅
```

### ENH-7: TemplatePicker project selector (integrated)

```
sidebar.tsx New Note button
  → useNewNoteFlow.open()
  → TemplatePicker opens
        ├── user selects template
        ├── user selects project (inline combobox in TemplatePicker)
        └── onConfirm(template, projectId) called
              → createNote.mutate({ title, content, projectId? })
```

### ENH-9: Notes page project filter

```
notes/page.tsx
  ├── [selectedProjectIds] state
  ├── useInfiniteNotes({ workspaceId, projectIds: selectedProjectIds, isPinned, pageSize })
  │     → GET /workspaces/{id}/notes?project_id=X&project_id=Y&...
  └── render chips: selectedProjectIds.map(id → Badge)
```

---

## v3 State Additions

| State | Location | Type | Purpose |
|---|---|---|---|
| `selectedProjectId` | `TemplatePicker` local | `string \| null` | Project selected in integrated picker |
| `search` (project filter) | `TemplatePicker` local | `string` | Combobox search term |
| `search` (move dialog) | `MoveNoteDialog` local | `string` | Project list search filter |
| `selectedProjectIds` | `notes/page.tsx` local | `string[]` | Multi-select project filter chips |



### Note (existing)

Relevant fields consumed by the panel:

| Field | Type | Notes |
|---|---|---|
| `id` | `string` (UUID) | Navigation link key |
| `title` | `string` | Displayed in panel row (truncated to 1 line) |
| `isPinned` | `boolean` | Determines Pinned vs Recent sub-section |
| `projectId` | `string?` | Filter: only notes where `projectId === project.id` |
| `updatedAt` | `string` (ISO) | Sort order for Recent sub-section |

Source: `frontend/src/types/note.ts`

### Project (existing)

Relevant fields consumed by the panel:

| Field | Type | Notes |
|---|---|---|
| `id` | `string` (UUID) | Used as `projectId` filter in API call |
| `workspaceId` | `string` (UUID) | Used to build `workspaceSlug`-based note links |

Source: `frontend/src/types/workspace.ts`

---

## Data Flow

```
ProjectSidebar
  └── ProjectNotesPanel (props: project, workspaceSlug, workspaceId)
        ├── useNotes({ workspaceId, projectId: project.id, isPinned: true, pageSize: 5 })
        │     → TanStack Query → GET /workspaces/{id}/notes?project_id=X&is_pinned=true&pageSize=5
        │     → pinnedNotes: Note[]
        └── useNotes({ workspaceId, projectId: project.id, isPinned: false, pageSize: 5 })
              → TanStack Query → GET /workspaces/{id}/notes?project_id=X&is_pinned=false&pageSize=5
              → recentNotes: Note[]
```

---

## API Calls (existing endpoints, no changes)

### List pinned project notes
```
GET /api/v1/workspaces/{workspaceId}/notes
  ?project_id={projectId}
  &is_pinned=true
  &pageSize=5
```

### List recent project notes (not pinned)
```
GET /api/v1/workspaces/{workspaceId}/notes
  ?project_id={projectId}
  &is_pinned=false
  &pageSize=5
```

### Create project-linked note
```
POST /api/v1/workspaces/{workspaceId}/notes
Body: {
  "title": "Untitled",
  "workspaceId": "{workspaceId}",
  "projectId": "{projectId}"
}
```

All endpoints are authenticated (Supabase Auth header) and RLS-enforced.

---

## State (UI only, no persistent state)

| State | Location | Type |
|---|---|---|
| Loading (pinned) | TanStack Query | `boolean` |
| Loading (recent) | TanStack Query | `boolean` |
| Error (pinned) | TanStack Query | `Error \| null` |
| Error (recent) | TanStack Query | `Error \| null` |
| Create pending | TanStack Query mutation | `boolean` |

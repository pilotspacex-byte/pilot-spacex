# Quickstart: Project Notes Panel (022)

**Date**: 2026-03-10
**Updated**: 2026-03-10 — v2: Enhancement feature scenarios added

## Integration Scenarios (Base Feature)

### Scenario 1: Panel renders with pinned + recent notes

```
Setup:
  - Workspace has a project with ID "proj-123"
  - 3 notes linked to "proj-123", 1 pinned, 2 recent

Steps:
  1. Navigate to /{workspaceSlug}/projects/proj-123/overview
  2. Project layout renders ProjectSidebar
  3. ProjectSidebar renders ProjectNotesPanel below nav items
  4. Panel shows:
     - "Pinned" section: 1 note title (clickable)
     - "Recent" section: 2 note titles (clickable)

Verify:
  - API call: GET /workspaces/{wsId}/notes?project_id=proj-123&is_pinned=true&pageSize=5
  - API call: GET /workspaces/{wsId}/notes?project_id=proj-123&is_pinned=false&pageSize=5
  - Clicking a title navigates to /{workspaceSlug}/notes/{noteId}
  - No "New Note" button visible (Enhancement 2)
```

### Scenario 2: Empty project (no notes)

```
Setup:
  - Project has no linked notes

Steps:
  1. Navigate to project
  2. ProjectNotesPanel renders

Verify:
  - Both queries return { items: [], total: 0 }
  - Empty state message shown
  - No "New Note" button (Enhancement 2: button removed from project panel)
```

### Scenario 3: Guest user sees panel without "New Note"

```
Setup:
  - Current user has role "guest"

Steps:
  1. Navigate to project sidebar

Verify:
  - Notes panel renders notes list normally
  - No "New Note" button (removed from project panel by Enhancement 2)
```

### Scenario 4: "View all" link with >5 notes

```
Setup:
  - Project has 8 pinned notes

Steps:
  1. Navigate to project sidebar

Verify:
  - Only 5 pinned note rows shown
  - "View all →" link present below pinned section
  - Link points to /{workspaceSlug}/notes (notes page)
```

---

## Integration Scenarios (Enhancement Features)

### Scenario 5: Workspace sidebar pinned notes show project label

```
Setup:
  - Workspace has note "Sprint Retro" (pinned) with projectId = "proj-123"
  - Project "proj-123" has name "Backend"
  - useProjects returns project list including Backend

Steps:
  1. Open workspace sidebar
  2. PINNED section renders

Verify:
  - Row shows: [FileText icon] "Sprint Retro" · "Backend" (muted label)
  - Notes without projectId show no label
  - Project name resolved from TQ cache (no extra API call)
```

### Scenario 6: New Note via TemplatePicker + project selection

```
Steps:
  1. Click "New Note" in workspace sidebar
  2. TemplatePicker modal opens (4 SDLC templates + blank)
  3. Select "Design Review" template
  4. Click "Create Design Review Note →"
  5. MoveNoteDialog opens: "Add to project?"
  6. Select project "Frontend" from list
  7. Note created: title "New Design Review Note", template content, projectId = Frontend.id
  8. Router navigates to /{workspaceSlug}/notes/{newNoteId}

Verify:
  - note.projectId === Frontend.id
  - note.content matches Design Review template content
  - TanStack Query notes list cache invalidated
```

### Scenario 7: New Note to root workspace (no project)

```
Steps:
  1. Click "New Note" in workspace sidebar
  2. TemplatePicker opens → select "Blank"
  3. MoveNoteDialog opens
  4. Select "No project (root)"
  5. Confirm

Verify:
  - note.projectId is undefined/null
  - Note created without project association
```

### Scenario 8: Note breadcrumb shows project path

```
Setup:
  - Note "Auth Design" with projectId = "proj-backend"
  - Project "proj-backend" has name "Backend"

Steps:
  1. Navigate to /{workspaceSlug}/notes/{noteId}
  2. NoteCanvasLayout renders InlineNoteHeader with projectId

Verify:
  - Breadcrumb renders: [FileText] Notes > Backend > Auth Design
  - "Backend" is a link to /{workspaceSlug}/projects/proj-backend/overview
  - On mobile (<sm), project segment hidden (hidden sm:inline)
  - useProject fetches project data (cached from earlier page loads)
```

### Scenario 9: Note without project shows simple breadcrumb

```
Setup:
  - Note has no projectId

Verify:
  - Breadcrumb renders: [FileText] Notes > [Title]
  - No project segment rendered
```

### Scenario 10: Move note to different project

```
Setup:
  - Note currently linked to project "Frontend"

Steps:
  1. Open note
  2. Click "..." options dropdown in header
  3. Click "Move..."
  4. MoveNoteDialog opens with "Frontend" pre-selected
  5. Select "Backend"
  6. Click "Move Note"

Verify:
  - PATCH /workspaces/{wsId}/notes/{noteId} called with body { projectId: "backend-id" }
  - Breadcrumb updates to "Notes > Backend > [title]"
  - TanStack Query note detail cache invalidated/updated
```

### Scenario 11: Move note to root workspace

```
Steps:
  1. Open note in project "Frontend"
  2. Click "..." → "Move..."
  3. Select "No project (root)"
  4. Confirm

Verify:
  - PATCH called with { projectId: null } or projectId omitted
  - Breadcrumb reverts to "Notes > [title]"
```

---

## Integration Scenarios (v3 — Bug Fixes)

### Scenario 12: Workspace sidebar shows only Pinned (no Recent)

```
Steps:
  1. Open workspace sidebar

Verify:
  - Only "PINNED" section is visible (no "Recent" / "RECENT" section)
  - Notes without projectId show no project label
```

### Scenario 13: Project notes panel shows only Recent (no Pinned)

```
Steps:
  1. Navigate to any project with both pinned and unpinned notes

Verify:
  - Only "Recent" section is visible in the project sidebar notes panel
  - No "Pinned" section header or pin icon visible
```

### Scenario 14: Project notes panel Recent is filtered by isPinned=false

```
Setup:
  - Project has 1 pinned note and 2 recent (unpinned) notes

Steps:
  1. Navigate to project sidebar

Verify:
  - Recent section shows exactly 2 notes (pinned note excluded)
  - API call: GET /notes?project_id=X&is_pinned=false ✅ (backend now filters correctly)
```

### Scenario 15: Create note from template — editor shows template content immediately

```
Steps:
  1. Click "New Note" in workspace sidebar
  2. TemplatePicker opens
  3. Select "Design Review" template
  4. Pick project (or no project) in integrated combobox
  5. Click "Create..."
  6. Navigate to new note editor

Verify:
  - Editor shows template content immediately (no blank screen)
  - No F5 refresh needed
  - note.content is non-null in TanStack Query cache
```

### Scenario 16: Move note to different project

```
Setup:
  - Note currently linked to project "Frontend"

Steps:
  1. Open note
  2. Click "..." → "Move..."
  3. MoveNoteDialog opens (search bar visible)
  4. Type "Back" — list filters to "Backend"
  5. Select "Backend" and confirm

Verify:
  - POST /workspaces/{id}/notes/{noteId}/move called with { project_id: "backend-id" }
  - Toast: "Note moved to project"
  - Breadcrumb updates to "Notes > Backend > [title]"
```

### Scenario 17: Move note to root workspace (remove project)

```
Setup:
  - Note currently linked to project "Frontend"

Steps:
  1. Click "..." → "Move..."
  2. Select "No project (root)"
  3. Confirm

Verify:
  - POST /move called with { project_id: null }
  - Toast: "Note moved to workspace root"
  - Breadcrumb reverts to "Notes > [title]"
  - note.projectId is null in cache
```

---

## Integration Scenarios (v3 — Enhancements)

### Scenario 18: New Note with template and project (integrated picker)

```
Steps:
  1. Click "New Note" in workspace sidebar
  2. TemplatePicker modal opens (4 SDLC templates + blank)
  3. Select "Sprint Review" template
  4. At bottom of TemplatePicker: searchable project combobox visible
  5. Type "Front" — filters to "Frontend"
  6. Select "Frontend"
  7. Click "Create Sprint Review Note"

Verify:
  - Single modal (no second popup)
  - Note created with template content + projectId = Frontend.id
  - Editor shows template content immediately
```

### Scenario 19: MoveNoteDialog search filters projects

```
Steps:
  1. Open note
  2. Click "..." → "Move..."
  3. Type "back" in search input

Verify:
  - Only projects matching "back" shown in list
  - "No project (root)" option always visible regardless of search
```

### Scenario 20: Notes page project filter multi-select

```
Setup:
  - Workspace has projects: Frontend, Backend, Mobile

Steps:
  1. Navigate to /notes
  2. Click "Projects" button in filter toolbar
  3. Multi-select dropdown opens
  4. Check "Frontend" and "Backend"
  5. Click "Done"

Verify:
  - Notes list reloads filtered to Frontend and Backend notes
  - Two chips appear below search bar: "Frontend × " and "Backend × "
  - Clicking "Frontend ×" removes that chip and reloads without Frontend filter
```



---

## File Locations (v3)

| File | Purpose |
|---|---|
| `frontend/src/components/layout/sidebar.tsx` | Remove Recent section (BUG-1) |
| `frontend/src/components/projects/ProjectNotesPanel.tsx` | Remove Pinned section (BUG-2) |
| `frontend/src/features/notes/components/TemplatePicker.tsx` | Add integrated project combobox (ENH-7) |
| `frontend/src/components/layout/useNewNoteFlow.ts` | Remove two-step flow (ENH-7) |
| `frontend/src/components/editor/MoveNoteDialog.tsx` | Add search input (ENH-8) |
| `frontend/src/app/(workspace)/[workspaceSlug]/notes/[noteId]/page.tsx` | Update handleMove to use moveNote API (BUG-5) |
| `frontend/src/app/(workspace)/[workspaceSlug]/notes/page.tsx` | Add project filter chips (ENH-9) |
| `frontend/src/services/api/notes.ts` | Add moveNote method (BUG-5) |
| `frontend/src/features/notes/hooks/useInfiniteNotes.ts` | Add projectIds param (ENH-9) |
| `backend/src/pilot_space/api/v1/routers/workspace_notes.py` | Add move endpoint + change create response (BUG-4, BUG-5) |
| `backend/src/pilot_space/api/v1/schemas/note.py` | Add NoteMove schema (BUG-5) |
| `backend/src/pilot_space/application/services/note/update_note_service.py` | Add clear_project_id flag (BUG-5) |
| `backend/src/pilot_space/application/services/note/list_notes_service.py` | Pass is_pinned to get_by_project (BUG-3) |
| `backend/src/pilot_space/infrastructure/database/repositories/note_repository.py` | Add is_pinned to get_by_project (BUG-3) |

---

## Dev Commands

```bash
# Frontend
cd frontend && pnpm dev          # Start dev server (port 3000)
cd frontend && pnpm type-check   # TypeScript check
cd frontend && pnpm lint         # ESLint check
cd frontend && pnpm test         # Vitest unit tests

# Backend
cd backend && uv run uvicorn pilot_space.main:app --reload --port 8000
cd backend && uv run ruff check  # Lint
cd backend && uv run pyright     # Type check
cd backend && uv run pytest      # All tests
```



### Scenario 1: Panel renders with pinned + recent notes

```
Setup:
  - Workspace has a project with ID "proj-123"
  - 3 notes linked to "proj-123", 1 pinned, 2 recent

Steps:
  1. Navigate to /{workspaceSlug}/projects/proj-123/overview
  2. Project layout renders ProjectSidebar
  3. ProjectSidebar renders ProjectNotesPanel below nav items
  4. Panel shows:
     - "Pinned" section: 1 note title (clickable)
     - "Recent" section: 2 note titles (clickable)
     - "New Note" button visible (non-guest user)

Verify:
  - API call: GET /workspaces/{wsId}/notes?project_id=proj-123&is_pinned=true&pageSize=5
  - API call: GET /workspaces/{wsId}/notes?project_id=proj-123&is_pinned=false&pageSize=5
  - Clicking a title navigates to /{workspaceSlug}/notes/{noteId}
```

### Scenario 2: Empty project (no notes)

```
Setup:
  - Project has no linked notes

Steps:
  1. Navigate to project
  2. ProjectNotesPanel renders

Verify:
  - Both queries return { items: [], total: 0 }
  - Empty state message shown
  - "New Note" button visible (non-guest)
```

### Scenario 3: Create note from panel

```
Steps:
  1. Click "New Note" in the panel
  2. Mutation: POST /workspaces/{wsId}/notes { title: "Untitled", projectId: "proj-123" }
  3. On success: navigate to /{workspaceSlug}/notes/{newNoteId}
  4. Note canvas opens with project context header

Verify:
  - New note has projectId === "proj-123"
  - TanStack Query cache invalidated for project notes list
```

### Scenario 4: Guest user sees panel without "New Note"

```
Setup:
  - Current user has role "guest"

Steps:
  1. Navigate to project sidebar

Verify:
  - Notes panel renders notes list normally
  - "New Note" button is NOT rendered
  - workspaceStore.currentUserRole === 'guest' check passes
```

### Scenario 5: "View all" link with >5 notes

```
Setup:
  - Project has 8 pinned notes

Steps:
  1. Navigate to project sidebar

Verify:
  - Only 5 pinned note rows shown
  - "View all →" link present below pinned section
  - Link points to /{workspaceSlug}/notes (notes page)
```

---

## File Locations

| File | Purpose |
|---|---|
| `frontend/src/components/projects/ProjectNotesPanel.tsx` | New panel component (create) |
| `frontend/src/components/projects/ProjectSidebar.tsx` | Mount point (modify: add panel after nav) |
| `frontend/src/features/notes/hooks/useNotes.ts` | Data hook (already supports projectId + isPinned) |
| `frontend/src/features/notes/hooks/useCreateNote.ts` | Create mutation (already supports projectId) |

---

## Dev Commands

```bash
cd frontend && pnpm dev          # Start dev server (port 3000)
cd frontend && pnpm type-check   # TypeScript check
cd frontend && pnpm lint         # ESLint check
cd frontend && pnpm test         # Vitest unit tests
```

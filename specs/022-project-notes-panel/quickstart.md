# Quickstart: Project Notes Panel (022)

**Date**: 2026-03-10

## Integration Scenarios

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

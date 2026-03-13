# Feature Specification: Project Notes Panel

**Feature Branch**: `022-project-notes-panel`
**Created**: 2026-03-10
**Updated**: 2026-03-10 — v3: 5 bugs + 3 enhancements added on top of v2
**Status**: In Progress
**Input**: User description: "A new panel has been added to the project's taskbar to display Recent Notes/Pinned Notes, which looks similar to the workspace's UI panel."

---

## Enhancement Features (v2 additions — complete)

These 6 enhancements build on the base implementation:

1. **Workspace sidebar pinned notes** — display a project label after the note name.
2. **Project notes panel** — remove the "New Note" button; show only the Recent notes section.
3. **New Note button (workspace sidebar)** — wire TemplatePicker modal before note creation (reusing T-018 from feature 018).
4. **New Note with project selector** — after template selection, user can choose which project (or root workspace) to store the note in.
5. **Note view breadcrumb** — display `Notes > [Project name] > [Note name]` when the note belongs to a project.
6. **Note options: Move** — add a "Move..." option in the note's `...` dropdown to reassign the note to a different project or root workspace.

## Bug Fixes (v3 additions)

**Bug 1**: The workspace taskbar (sidebar.tsx) still displays a "Recent" section listing all workspace-scope recent notes — this should be removed.

**Bug 2**: The project taskbar (`ProjectNotesPanel`) still displays a "Pinned" section — this should be removed; only the "Recent" section should remain.

**Bug 3**: Notes displayed in the workspace sidebar "Recent" section are not filtered by project. Backend `list_notes_service.py` uses `elif project_id:` logic that ignores `is_pinned` when a `project_id` is provided. The `get_by_project` repository method also ignores `is_pinned`. Both need to be fixed so that `project_id` and `is_pinned` filters can be combined.

**Bug 4**: After creating a note using a template (`useNewNoteFlow` → `useCreateNote`), the opened file will be empty — the template content will only appear after refreshing (F5). Root cause: `POST /workspaces/{id}/notes` returns `NoteResponse` (no `content` field), but `useCreateNote.onSuccess` stores that response in the TanStack Query detail cache. When `NoteDetailPage` renders, `note.content` from cache is `undefined`, so the editor shows blank. Fix: change the `POST /workspaces/{id}/notes` endpoint to return `NoteDetailResponse` (which includes `content`).

**Bug 5**: The "Move..." note feature cannot change the `project_id` to clear a project link (move to root workspace). Root causes:
- Backend `UpdateNoteService.execute()`: `if payload.project_id is not None: ...` guard prevents clearing project_id.
- Backend `NoteUpdate` schema: `project_id` field is missing.
- Frontend `handleMove`: passes `newProjectId ?? undefined` which is omitted from the PATCH body when null.
Fix: add a dedicated `POST /workspaces/{id}/notes/{noteId}/move` endpoint that accepts `project_id: UUID | null` (nullable, explicitly settable to null) + a toast notification on success.

## Enhancements (v3 additions)

**Enhancement 1**: When creating a new note, the project selector (`MoveNoteDialog`) currently opens as a separate popup after `TemplatePicker`. Replace this second-step popup with a **dropdown list integrated at the end** of the `TemplatePicker` modal itself — a searchable combobox (or `Select` with search) showing projects, allowing the user to pick a project or "No project (root)" before confirming.

**Enhancement 2**: The "Move..." option dialog (`MoveNoteDialog`) should display a **search input** at the top of the project list, allowing users to filter projects by name.

**Enhancement 3**: On the notes list page (`/notes`), the "Filter" dropdown should include a **project filter** option — a button that opens a dropdown list of projects with multi-select capability. After pressing "Done", the notes list reloads filtered to those projects, and **project filter chips** appear below the search bar. Multi-select is supported.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Browse Project Notes from Project Sidebar (Priority: P1)

A project member navigates to a project and sees a collapsible "Notes" section in the project sidebar (similar to the PINNED/RECENT sections in the workspace sidebar). The section lists up to 5 pinned notes and up to 5 recent notes scoped to that project, each showing the note title and a link to navigate directly to the note canvas.

**Why this priority**: This is the core feature — making project-scoped notes discoverable from the project context without leaving to the global Notes page. Every other story depends on notes being visible here.

**Independent Test**: Can be fully tested by navigating to any project with notes and verifying the Notes section appears in the project sidebar with correct pinned/recent listings.

**Acceptance Scenarios**:

1. **Given** a project has at least one pinned note, **When** a user opens that project's sidebar, **Then** a "Pinned" notes section is visible showing up to 5 pinned notes for that project, each with a clickable title.
2. **Given** a project has recent notes (not pinned), **When** a user opens that project's sidebar, **Then** a "Recent" notes section is visible showing up to 5 of the most recently modified notes for that project (excluding pinned ones).
3. **Given** a project has no notes at all, **When** a user opens the project sidebar, **Then** the Notes section shows an empty state with a "New Note" shortcut.
4. **Given** a user clicks a note title in the panel, **When** the click is registered, **Then** the user is navigated to the note's editing canvas.

---

### User Story 2 — Create a Note Scoped to the Project from the Panel (Priority: P2)

A project member wants to quickly create a new note associated with the current project. They see a "New Note" button or inline shortcut within the project notes panel that creates a note pre-linked to the project and navigates them to the note canvas.

**Why this priority**: Reduces friction for creating project-linked notes; secondary to browsing which is P1.

**Independent Test**: Can be fully tested by clicking the "New Note" action in the project notes panel and verifying a new note is created, linked to the project, and the user is navigated to the note editor.

**Acceptance Scenarios**:

1. **Given** a user is in the project sidebar notes section, **When** they click "New Note", **Then** a new note is created pre-linked to the current project and the user is navigated to the note editor.
2. **Given** a guest-role user is viewing the project sidebar, **When** the notes panel is displayed, **Then** the "New Note" button is hidden (guests cannot create content).

---

### User Story 3 — Notes Panel Matches Workspace Sidebar Visual Style (Priority: P3)

The project notes panel (both the Pinned and Recent sub-sections) uses the same visual language as the workspace sidebar's PINNED/RECENT notes sections: same icon sizes, typography, hover states, and section headers.

**Why this priority**: Visual consistency; purely a polish concern once the functional panel exists.

**Independent Test**: Can be validated by side-by-side screenshot comparison of the workspace sidebar notes sections and the new project sidebar notes sections.

**Acceptance Scenarios**:

1. **Given** the project sidebar notes panel is rendered, **When** compared side-by-side to the workspace sidebar notes sections, **Then** icon sizes, text size, hover styles, and section header labels are visually identical.
2. **Given** the notes list is longer than 5 items, **When** the panel is displayed, **Then** only 5 items are shown with a "View all" link pointing to the project-scoped notes list.

---

### Edge Cases

- What happens when a note appears in both pinned and recent lists? The note is shown only in Pinned; the Recent sub-section excludes pinned notes (same behaviour as workspace sidebar).
- What happens when the project notes API call fails or is slow? The panel shows skeleton loaders during fetch and a non-blocking inline error message on failure; the project layout does not crash.
- What happens on mobile where the project sidebar collapses to a tab bar? The Notes panel is not shown in the mobile tab bar (tab bar shows fixed nav items only); notes remain accessible via the global Notes page.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The project sidebar MUST include a "Notes" section below the navigation links, containing two sub-sections: "Pinned" and "Recent".
- **FR-002**: The Pinned sub-section MUST display up to 5 notes with `isPinned = true` linked to the current project, ordered by most-recently-modified.
- **FR-003**: The Recent sub-section MUST display up to 5 notes linked to the current project (excluding pinned notes), ordered by `updatedAt` descending.
- **FR-004**: Each note entry MUST display the note title (truncated to one line) as a clickable link navigating to the note's editor page.
- **FR-005**: When a project has no notes, the Notes section MUST show a minimal empty state with a "New Note" action.
- **FR-006**: The Notes section MUST include a "New Note" action that creates a note pre-linked to the current project and navigates to the note editor. This action MUST be hidden for guest-role users.
- **FR-007**: When more than 5 notes exist in either sub-section, a "View all" link MUST be shown, pointing to the Notes page filtered by the current project.
- **FR-008**: The Notes panel visual style (section headers, item rows, icons, hover states) MUST match the workspace sidebar PINNED/RECENT notes sections.
- **FR-009**: The Notes section MUST be rendered only in the desktop sidebar (medium breakpoint and above); it MUST NOT appear in the mobile tab bar.
- **FR-010**: Note data for the panel MUST be fetched scoped to the current project, requesting no more than 10 notes per call.

### Functional Requirements (v2 — Enhancement Features)

- **FR-011**: The workspace sidebar PINNED notes section MUST display a muted project name label after each note title when the note's `projectId` is set.
- **FR-012**: The project sidebar notes panel MUST NOT include a "New Note" button; it MUST display only the Pinned and Recent lists.
- **FR-013**: The workspace sidebar "New Note" button MUST open a TemplatePicker modal before creating a note (4 SDLC templates + blank option), reusing the `TemplatePicker` component built in feature 018.
- **FR-014**: After template selection, the system MUST present a project selector step allowing the user to assign the new note to a project or the root workspace.
- **FR-015**: The note view header MUST display a breadcrumb path of `Notes > [Project name] > [Note name]` when the note has a `projectId`; the project name segment MUST link to the project overview page.
- **FR-016**: The note view options menu MUST include a "Move..." action that opens a project picker allowing the user to reassign the note to a different project or root workspace (no project).

### Functional Requirements (v3 — Bug Fixes)

- **FR-017**: The workspace sidebar (sidebar.tsx) MUST NOT display a "Recent" notes section. Only the "Pinned" section remains.
- **FR-018**: The project sidebar notes panel (`ProjectNotesPanel`) MUST NOT display a "Pinned" section. Only the "Recent" notes section remains.
- **FR-019**: The backend `ListNotesService` MUST support combining `project_id` and `is_pinned` filters simultaneously. The `NoteRepository.get_by_project()` MUST accept an optional `is_pinned` parameter and filter accordingly.
- **FR-020**: `POST /workspaces/{id}/notes` MUST return `NoteDetailResponse` (including `content`) so that `useCreateNote.onSuccess` can populate the TanStack Query detail cache with the full note including template content.
- **FR-021**: A new `POST /workspaces/{id}/notes/{noteId}/move` endpoint MUST be added that accepts `{ project_id: UUID | null }` (explicitly nullable) to reassign a note to a project or remove its project association. On success, the frontend MUST show a toast notification.

### Functional Requirements (v3 — Enhancements)

- **FR-022**: The `TemplatePicker` modal MUST include an integrated project selector (searchable dropdown/combobox) at the bottom of the confirm section, replacing the separate `MoveNoteDialog` second step in `useNewNoteFlow`.
- **FR-023**: The `MoveNoteDialog` MUST include a search input that filters the project list by name in real time.
- **FR-024**: The notes list page (`/notes`) filter toolbar MUST include a "Projects" button that opens a multi-select dropdown listing all workspace projects. After the user selects projects and presses "Done", the notes list MUST reload filtered to notes belonging to those projects, and a project filter chip per selected project MUST appear below the search bar. Removing a chip deselects that project and reloads.

### Key Entities

- **Note**: A workspace note. Relevant attributes: `id`, `title`, `isPinned`, `projectId`, `updatedAt`. Notes are linked to a project via `projectId`.
- **Project**: The project context. Relevant attributes: `id`, `name`, `workspaceId`. Used as the filter scope for the notes panel and as label/picker options.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can reach a project-linked note from the project sidebar in 2 clicks or fewer (open project → click note title).
- **SC-002**: The Notes panel data appears within the same page load as the rest of the project sidebar with no additional perceptible delay.
- **SC-003**: 100% of notes created via workspace sidebar "New Note" that have a project selected are correctly linked to that project.
- **SC-004**: The Notes panel is visually consistent with the workspace sidebar notes sections when reviewed side-by-side.
- **SC-005**: The note view breadcrumb correctly resolves and displays the project name segment for all notes with a `projectId`.
- **SC-006**: After using "Move...", the note's `projectId` is updated and the breadcrumb reflects the change without a full page reload.

## Assumptions

- Notes are already linkable to projects via `projectId` in the data model (`Note.projectId?: string`).
- The existing notes list API supports filtering by `projectId` (`project_id` query param on `GET /workspaces/{id}/notes`).
- The project panel will use a direct data query with `projectId` filter rather than the workspace-scoped MobX `NoteStore`, since `NoteStore` is not project-aware.
- The `canCreateContent` permission check (role is not guest) applies identically to the project sidebar as it does to the workspace sidebar.
- `PATCH /workspaces/{id}/notes/{noteId}` already accepts `projectId` in the request body (mapped from `UpdateNoteData.projectId?: string`).
- The `TemplatePicker` component and `NoteTemplate` type from feature 018 are fully built and available at `features/notes/components/TemplatePicker.tsx`.
- **v3 revised**: `PATCH /workspaces/{id}/notes/{noteId}` cannot clear `project_id` (set to null) — the new `POST /move` endpoint is required for move-to-root operations.
- **v3 revised**: `POST /workspaces/{id}/notes` returns `NoteResponse` (no content) — needs to return `NoteDetailResponse` to fix Bug 4.

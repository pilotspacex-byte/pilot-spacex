# Feature Specification: Project Notes Panel

**Feature Branch**: `022-project-notes-panel`
**Created**: 2026-03-10
**Status**: Draft
**Input**: User description: "A new panel has been added to the project's taskbar to display Recent Notes/Pinned Notes, which looks similar to the workspace's UI panel."

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

### Key Entities

- **Note**: A workspace note. Relevant attributes: `id`, `title`, `isPinned`, `projectId`, `updatedAt`. Notes are linked to a project via `projectId`.
- **Project**: The project context. Relevant attributes: `id`, `workspaceId`. Used as the filter scope for the notes panel.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can reach a project-linked note from the project sidebar in 2 clicks or fewer (open project → click note title).
- **SC-002**: The Notes panel data appears within the same page load as the rest of the project sidebar with no additional perceptible delay.
- **SC-003**: 100% of notes created via the "New Note" shortcut in the project panel are correctly linked to the current project.
- **SC-004**: The Notes panel is visually consistent with the workspace sidebar notes sections when reviewed side-by-side.

## Assumptions

- Notes are already linkable to projects via `projectId` in the data model (`Note.projectId?: string`).
- The existing notes list API supports filtering by `projectId` (`project_id` query param on `GET /workspaces/{id}/notes`).
- The project panel will use a direct data query with `projectId` filter rather than the workspace-scoped MobX `NoteStore`, since `NoteStore` is not project-aware.
- The `canCreateContent` permission check (role is not guest) applies identically to the project sidebar as it does to the workspace sidebar.

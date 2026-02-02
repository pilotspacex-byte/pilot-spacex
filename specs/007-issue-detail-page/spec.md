# Feature Specification: Issue Detail Page - Full Implementation

**Feature Branch**: `007-issue-detail-page`
**Created**: 2026-02-02
**Status**: Draft
**Input**: Build the complete Issue Detail page with all missing components: inline editing, TipTap description editor, full interactive properties panel, activity timeline, linked PRs, source notes, sub-issues, and responsive layout.

---

## Summary

The Issue Detail page is the primary workspace for viewing and editing a single issue. It follows a 70/30 split layout with main content on the left and a properties sidebar on the right. The page currently has a partial implementation (header, read-only display, AI context sidebar) but is missing interactive editing, activity timeline, linked items, and responsive behavior.

This feature completes the Issue Detail page to provide a fully interactive, auto-saving, accessible experience that matches the design system's "Warm, Capable, Collaborative" philosophy.

---

## Clarifications

### Session 2026-02-02

- Q: What form should the auto-save confirmation take when edits are persisted? → A: Inline status text near the edited field showing "Saving..." → "Saved" → fades out after 2 seconds (Notion/Linear pattern)
- Q: Can users edit or delete their own comments after posting? → A: Yes, users can edit and delete their own comments only. Edited comments show "(edited)" label with last-edited timestamp. Deleted comments are removed from the timeline.
- Q: Who can edit issue fields — all members or role-restricted? → A: All workspace members can edit all fields on any issue within their workspace. No role-based field restrictions. Matches Linear's model and existing RLS workspace-scoped access.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Inline Issue Editing (Priority: P1)

A developer opens an issue to update its title and description. They click on the title to edit it inline, type the new title, and it auto-saves. They then edit the description using a rich text editor with markdown support.

**Why this priority**: Editing is the most fundamental interaction on the detail page. Without it, users must use a separate modal or navigate elsewhere to make changes.

**Independent Test**: Open any issue, click the title, type a new value, click away, and verify the title persists on page reload.

**Acceptance Scenarios**:

1. **Given** a user is viewing an issue detail page, **When** they click on the issue title, **Then** the title becomes an editable text input with the current title pre-filled and cursor at the end.

2. **Given** a user is editing the issue title, **When** they type a new title and click away (blur), **Then** the title auto-saves after 2 seconds and an inline status text near the field shows "Saving..." then "Saved" before fading out after 2 seconds.

3. **Given** a user is editing the issue title, **When** they press Enter, **Then** the title is confirmed and focus moves to the description editor.

4. **Given** a user is editing the issue title, **When** they press Escape, **Then** the edit is cancelled and the original title is restored.

5. **Given** a user clears the title field completely, **When** they attempt to save, **Then** validation prevents saving and shows "Title is required (1-255 characters)".

6. **Given** a user is viewing the issue description, **When** they click on the description area, **Then** a rich text editor activates with formatting toolbar, supporting markdown, code blocks, images, and mentions.

7. **Given** a user is editing the description, **When** they stop typing for 2 seconds, **Then** the description auto-saves without requiring a manual save action.

8. **Given** the description is empty, **When** the user views the issue, **Then** they see a placeholder "Add a description..." that activates the editor on click.

---

### User Story 2 - Properties Panel Interaction (Priority: P1)

A project manager opens an issue to update its assignee, labels, cycle, and estimate. They use dropdown selectors and date pickers in the right sidebar to update each property, with changes saving immediately.

**Why this priority**: Property management is essential for issue tracking workflows. Users need to assign work, set priorities, and manage sprint planning from the detail page.

**Independent Test**: Open an issue, change the assignee from the sidebar dropdown, and verify the change persists on reload.

**Acceptance Scenarios**:

1. **Given** a user is viewing the properties sidebar, **When** they click the assignee field, **Then** a dropdown shows workspace members with avatars and names, searchable by name.

2. **Given** a user selects a new assignee, **When** the selection is made, **Then** the change saves immediately with optimistic UI update (instant visual feedback, rollback on error).

3. **Given** a user is viewing the labels field, **When** they click it, **Then** a multi-select dropdown shows available labels with color indicators, and allows adding/removing labels.

4. **Given** a user is viewing the cycle field, **When** they click it, **Then** a dropdown shows available workspace cycles (past, current, future) with date ranges.

5. **Given** a user is viewing the estimate field, **When** they click it, **Then** they can select from Fibonacci story point values (1, 2, 3, 5, 8, 13) or enter a custom integer.

6. **Given** a user is viewing date fields, **When** they click the start date or due date, **Then** a date picker calendar appears for selecting the date.

7. **Given** a user is viewing the type field, **When** they click it, **Then** a dropdown shows issue types: Bug, Feature, Task, Improvement.

8. **Given** a property update fails (network error), **When** the error occurs, **Then** the UI rolls back to the previous value and shows a toast notification with the error.

---

### User Story 3 - Activity Timeline (Priority: P2)

A team lead reviews an issue's history to understand what changes were made, by whom, and when. They scroll through a chronological timeline showing state changes, comments, assignments, and AI actions.

**Why this priority**: Activity history provides accountability and context. It's essential for team collaboration but not blocking for basic issue management.

**Independent Test**: Open an issue that has had state changes and assignments, and verify the timeline shows each change with actor, action, and timestamp.

**Acceptance Scenarios**:

1. **Given** a user is viewing the issue detail page, **When** they scroll below the description, **Then** they see a chronological activity timeline showing all issue changes.

2. **Given** the activity timeline is loaded, **When** the user views an entry, **Then** each entry shows: actor avatar, actor name, action description (e.g., "changed state from Todo to In Progress"), and relative timestamp.

3. **Given** an AI agent made a change to the issue, **When** the user views that activity entry, **Then** it is marked with a distinct AI indicator (dusty blue sparkles icon) and shows which agent performed the action.

4. **Given** the activity timeline has more than 50 entries, **When** the user scrolls to the bottom, **Then** additional entries load automatically (infinite scroll pagination).

5. **Given** a user wants to add a comment, **When** they type in the comment input at the bottom of the timeline, **Then** they can write rich text and submit with Enter (Shift+Enter for newline).

6. **Given** a comment is submitted, **When** the submission completes, **Then** the new comment appears immediately at the bottom of the timeline with optimistic rendering.

7. ~~**Given** a user views their own comment, **When** they hover over it, **Then** edit and delete action buttons appear.~~ **DESCOPED**: No backend edit/delete comment endpoints.

8. ~~**Given** a user clicks edit on their comment~~ **DESCOPED**: Requires backend PATCH `/comments/:id` endpoint.

9. ~~**Given** a user clicks delete on their comment~~ **DESCOPED**: Requires backend DELETE `/comments/:id` endpoint.

---

### User Story 4 - Linked Items (Priority: P2)

A developer checks an issue to see which GitHub PRs are linked and which notes originally extracted the issue. They click a linked PR to open it in GitHub, and click a source note to navigate to the note editor.

**Why this priority**: Linked items provide traceability between issues, code changes, and original requirements. Important for the Note-First workflow but not blocking for basic editing.

**Independent Test**: Open an issue that was extracted from a note, verify the source note appears in the sidebar, and click it to navigate to the note editor.

**Acceptance Scenarios**:

1. **Given** an issue has linked GitHub PRs, **When** the user views the sidebar, **Then** a "Linked Pull Requests" section shows each PR with number, title, and status badge (Open/Merged/Closed).

2. **Given** the user clicks a linked PR, **When** the click occurs, **Then** the GitHub PR opens in a new browser tab.

3. **Given** an issue was extracted from a note, **When** the user views the sidebar, **Then** a "Source Notes" section shows each linked note with title and link type badge (EXTRACTED/CREATED/REFERENCED).

4. **Given** the user clicks a source note, **When** the click occurs, **Then** they navigate to the note editor page for that note.

5. **Given** an issue has no linked PRs, **When** the user views the sidebar, **Then** the "Linked Pull Requests" section shows "No linked pull requests" in muted text.

6. **Given** an issue has no linked notes, **When** the user views the sidebar, **Then** the "Source Notes" section shows "No linked notes" in muted text.

---

### User Story 5 - Sub-issues Management (Priority: P2)

A tech lead breaks down a feature issue into smaller sub-tasks. They view existing sub-issues, track completion progress, and add new sub-issues directly from the parent issue.

**Why this priority**: Task decomposition is a core workflow for development teams. Sub-issues help break large features into manageable work items.

**Independent Test**: Open a parent issue, verify sub-issues are listed with progress, and add a new sub-issue that appears in the list.

**Acceptance Scenarios**:

1. **Given** an issue has child issues (sub-issues), **When** the user views the main content area, **Then** a "Sub-issues" section shows each child issue with identifier, title, state badge, and assignee avatar.

2. **Given** the sub-issues section is visible, **When** the user views the header, **Then** a progress indicator shows completed count vs total count (e.g., "3 of 5 completed") with a visual progress bar.

3. **Given** the user clicks "Add sub-issue", **When** the action triggers, **Then** an inline form appears to create a new child issue with title and optional type/priority.

4. **Given** the user clicks a sub-issue in the list, **When** the click occurs, **Then** they navigate to the sub-issue's detail page.

---

### User Story 6 - Responsive Layout (Priority: P3)

A developer reviews an issue on their tablet during a standup meeting. The page adapts to the narrower screen by stacking the properties panel above the main content, with collapsible sections on mobile.

**Why this priority**: Responsive design ensures the page is usable across devices. Important for accessibility and mobile use cases but not blocking for desktop-first development.

**Independent Test**: Resize the browser to 768px width and verify the layout switches to single-column with properties above content.

**Acceptance Scenarios**:

1. **Given** the viewport is wider than 1280px (xl+), **When** the page renders, **Then** the layout shows 70% main content and 30% sidebar side by side.

2. **Given** the viewport is 1024-1279px (lg), **When** the page renders, **Then** the layout shows 65% main content and 35% sidebar.

3. **Given** the viewport is 768-1023px (md), **When** the page renders, **Then** the layout switches to single column with properties displayed above the main content.

4. **Given** the viewport is less than 768px (sm), **When** the page renders, **Then** the layout is single column with properties in a collapsible accordion section.

---

### User Story 7 - Keyboard Navigation & Shortcuts (Priority: P3)

A power user navigates the issue detail page entirely with keyboard shortcuts. They use Tab to move between fields, Escape to close panels, and Cmd+S to force-save.

**Why this priority**: Keyboard navigation is required for accessibility compliance (WCAG 2.2 AA) and improves power user productivity.

**Independent Test**: Navigate to an issue, press Tab repeatedly, and verify focus moves logically through all interactive elements.

**Acceptance Scenarios**:

1. **Given** the user presses Tab, **When** focus moves, **Then** it follows a logical order: title → description → sub-issues → activity → sidebar properties (top to bottom).

2. **Given** the AI Context sidebar is open, **When** the user presses Escape, **Then** the sidebar closes and focus returns to the main content.

3. **Given** the user is editing any field, **When** they press Cmd+S (Ctrl+S on Windows), **Then** all pending changes are force-saved immediately regardless of the debounce timer.

4. **Given** a dropdown is open, **When** the user presses Arrow keys, **Then** the selection moves through the options. Enter selects, Escape closes.

5. **Given** any interactive element has focus, **When** the user views it, **Then** a visible focus ring (3px primary color at 30% opacity) indicates the focused element.

---

## Functional Requirements *(mandatory)*

### FR-1: Inline Title Editing

- Title renders as `text-2xl` (24px/32px line height) heading
- Click activates edit mode with text input
- Auto-save triggers 2 seconds after last keystroke (debounce)
- Validation: minimum 1 character, maximum 255 characters
- Enter key confirms edit, Escape key cancels edit
- Optimistic update: UI reflects change immediately, rolls back on server error
- Save feedback: Inline status text near the field shows "Saving..." → "Saved" → fades after 2 seconds; applies to title, description, and all property fields

### FR-2: TipTap Description Editor

- Rich text editor replaces static paragraph display
- Supports: bold, italic, headings, bullet/numbered lists, code blocks, images, mentions, links
- Auto-save triggers 2 seconds after last content change (debounce)
- Empty state shows "Add a description..." placeholder
- Reuses existing TipTap extensions: BlockId, CodeBlock, Mention, SlashCommand, FloatingToolbar
- Content stored as both markdown and HTML (description + description_html fields)

### FR-3: Interactive Properties Panel

- **Assignee selector**: Searchable dropdown of workspace members with avatars
- **Label selector**: Multi-select with color-coded labels, add/remove support
- **Cycle selector**: Dropdown showing workspace cycles with date ranges
- **Estimate field**: Fibonacci story points (1, 2, 3, 5, 8, 13) or custom integer
- **Type selector**: Bug, Feature, Task, Improvement
- **Start date picker**: Calendar widget for setting start date
- **Due date picker**: Calendar widget for setting target date
- All fields: optimistic updates with instant visual feedback and rollback on error

### FR-4: Activity Timeline

- Chronological list of all issue changes, newest at bottom
- Event types: based on `activity_type` string from backend (e.g., 'commented', 'state_changed', 'assigned')
- Each entry: actor display_name (from UserBrief), action description, relative timestamp. Note: actor can be null for system events.
- AI-generated entries: check `metadata` field for AI indicators (no dedicated `isAiGenerated` flag in backend)
- Comment input at bottom submitting `{ content }` (plain text, 1-10000 chars)
- Initial load: 50 entries via offset-based pagination (`limit=50&offset=0`); additional entries via infinite scroll incrementing offset
- New comments appear immediately via optimistic rendering
- ~~Users can edit and delete their own comments only~~ **DESCOPED**: No backend edit/delete comment endpoints exist. Deferred to future backend work.
- ~~Edited comments display "(edited)" label~~ **DESCOPED**: No `edited_at` field in backend response.
- ~~Deleted comments are removed from the timeline~~ **DESCOPED**: No `deleted_at` field or delete endpoint in backend.

### FR-5: Linked Pull Requests

- Displays GitHub PRs linked to the issue via integration links
- Each PR shows: number (#234), title, status badge (Open in blue, Merged in purple, Closed in grey)
- Click opens PR in new browser tab
- Empty state: "No linked pull requests" in muted text

### FR-6: Source Notes

- Displays notes linked to the issue via NoteIssueLink
- Each note shows: title, link type badge (EXTRACTED/CREATED/REFERENCED)
- Click navigates to the note editor page
- Empty state: "No linked notes" in muted text

### FR-7: Sub-issues Section

- Lists child issues with identifier, title, state color badge, assignee avatar
- Progress indicator: "X of Y completed" with visual progress bar
- "Add sub-issue" button opens inline creation form
- Click on sub-issue navigates to its detail page

### FR-8: Responsive Layout

- xl+ (>1280px): 70/30 split (main content / sidebar)
- lg (1024-1279px): 65/35 split
- md (768-1023px): Single column, properties above content
- sm (<768px): Single column, properties in collapsible accordion

### FR-9: Keyboard Navigation

- Logical tab order through all interactive elements
- Escape closes sidebars and cancels edits
- Cmd/Ctrl+S force-saves all pending changes
- Arrow keys navigate dropdown options
- Visible focus indicators on all interactive elements (WCAG 2.2 AA)

---

## Success Criteria *(mandatory)*

1. **Editing efficiency**: Users can edit any issue field (title, description, properties) directly on the detail page without navigating to a separate form or modal.

2. **Auto-save reliability**: All changes auto-save within 3 seconds of the last edit, with zero data loss during normal operation.

3. **Activity completeness**: 100% of issue state changes, assignments, comments, and AI actions appear in the activity timeline with correct attribution and timestamps.

4. **Navigation traceability**: Users can navigate from an issue to any linked PR, source note, or sub-issue with a single click.

5. **Responsive usability**: The page is fully functional on screens from 375px to 2560px width, with all interactive elements accessible at every breakpoint.

6. **Keyboard accessibility**: Every interactive element on the page is reachable and operable via keyboard alone, with visible focus indicators meeting 3:1 contrast ratio.

7. **Performance**: The issue detail page loads and becomes interactive within 2 seconds on a standard connection, including all sidebar data.

8. **Optimistic feedback**: Property changes reflect in the UI within 100ms of user action, before server confirmation.

---

## Key Entities *(mandatory when data is involved)*

### Issue (existing — aligned with backend `IssueResponse`)
- **Core fields**: id, workspace_id, sequence_id, identifier, name (NOT title), description, description_html
- **Workflow**: state (object: { id, name, color, group }), priority, estimate_points, start_date, target_date, sort_order
- **Assignment**: assignee (UserBrief | null), reporter (UserBrief)
- **Project**: project (ProjectBrief: { id, name, identifier })
- **AI**: ai_metadata, has_ai_enhancements
- **Counts**: sub_issue_count (count only, no children list)
- **Relationships in response**: labels (LabelBrief[])
- **NOT in response**: cycle, module, parent_id, children, integration_links, note_links, type

### Activity (displayed in timeline — aligned with backend `ActivityResponse`)
- **Core**: id, activity_type (string), actor (UserBrief | null)
- **Change tracking**: field, old_value, new_value
- **Comments**: comment (plain text only, not HTML)
- **Metadata**: metadata (may contain AI-related info)
- **Timestamp**: created_at
- **NOT in backend**: comment_html, is_ai_generated, edited_at, deleted_at

### NoteIssueLink (existing, displayed in Source Notes)
- **Core**: id, note_id, issue_id
- **Type**: link_type (CREATED, EXTRACTED, REFERENCED)

### IntegrationLink (existing, displayed in Linked PRs)
- **Core**: id, issue_id, integration_type, external_id, external_url
- **GitHub**: pr_number, pr_title, pr_status (open, merged, closed)

---

## Scope & Boundaries

### In Scope
- All 9 functional requirements listed above
- Frontend implementation only (page, components, stores, hooks)
- Reuse of existing shared components (selectors, AI panels)
- Unit tests for new components (>80% coverage)

### Out of Scope
- **Backend API changes** — the following require new backend endpoints and are descoped from this feature:
  - Comment edit (PATCH `/comments/:id`) and delete (DELETE `/comments/:id`)
  - Workspace-scoped labels list endpoint
  - Integration links list endpoint (linked PRs)
  - Note-issue links list endpoint (source notes)
  - Dedicated sub-issues list endpoint (workaround: filter by `parent_id`)
- Real-time collaborative editing (Phase 2, DD-005)
- Issue creation flow (separate feature, already has IssueModal)
- Bulk issue operations
- Issue templates
- Custom fields beyond the defined set

---

## Assumptions

1. ~~Backend API endpoints for issue CRUD, activities, and related data are already implemented and return data matching the entity schemas above.~~ **REVISED**: Backend has issue CRUD, activity list (offset-based), and comment add. Missing: comment edit/delete, labels list, integration-links list, note-links list, dedicated sub-issues list. See data-model.md "Missing Endpoints" table.
2. Existing shared components (IssueStateSelect, IssuePrioritySelect, AssigneeSelector, LabelSelector) are production-ready and require no modifications.
3. TipTap editor setup and extensions from the notes feature can be reused with minimal configuration changes.
4. The issue detail page will not support real-time collaborative editing in this phase (last-write-wins per DD-005).
5. ~~Activity timeline pagination uses cursor-based pagination via the existing API pattern.~~ **REVISED**: Activity timeline uses **offset-based pagination** (`limit`/`offset` query params). Backend returns `{ activities: Activity[], total: number }`.
6. ~~Workspace cycles data is available via an existing API endpoint.~~ **REVISED**: Cycles endpoint exists but requires `project_id` parameter — it is **project-scoped**, not workspace-scoped. Frontend must pass `issue.project.id`.
7. All workspace members have full edit access to all issue fields (no role-based field restrictions). Access is controlled at the workspace level via RLS.
8. Backend `IssueResponse` uses `name` field (not `title`), `state` as an object `{ id, name, color, group }` (not string enum), `estimate_points` (not `estimatedHours`), `target_date` (not `dueDate`). Frontend types must be aligned before component work starts.
9. Backend `CommentCreateRequest` accepts a single `content` string field (1-10000 chars), not `{ comment, commentHtml }`. Backend `ActivityResponse` returns plain `comment` string, not HTML.
10. Backend does NOT include `integrationLinks`, `noteLinks`, `children`, `cycleId`, `moduleId`, `parentId`, or `type` in `IssueResponse`. Components for linked PRs and source notes will render empty state until backend adds these fields.

---

## Dependencies

- **Existing components**: IssueStateSelect, IssuePrioritySelect, AssigneeSelector, LabelSelector, AIContextSidebar, DeleteConfirmDialog
- **Existing stores**: IssueStore (MobX), AIContextStore, ConversationStore
- **Existing services**: issues.ts API client
- **TipTap**: Reuses extensions from notes feature (BlockId, CodeBlock, Mention, SlashCommand, FloatingToolbar)
- **Design system**: shadcn/ui components (Button, Badge, Separator, Avatar, Skeleton, Card, Select, Popover, Calendar — **note**: Calendar not yet installed, requires `npx shadcn-ui@latest add calendar` + `date-fns`)

---

## Risks

1. **TipTap bundle size**: Adding TipTap to the issue detail page may increase the page's JavaScript bundle. **Mitigation**: Use dynamic import (`next/dynamic`) to code-split the editor.
2. **Auto-save race conditions**: Rapid edits across multiple fields could cause concurrent save requests. **Mitigation**: Queue mutations and deduplicate pending saves.
3. **Optimistic update conflicts**: Two users editing the same issue could overwrite each other's changes. **Mitigation**: Last-write-wins is acceptable per DD-005; show "Updated by [name]" notification when server data changes.
4. **Missing backend endpoints**: 6 endpoints assumed by the original spec do not exist (comment edit/delete, labels list, integration-links, note-links, sub-issues list). **Mitigation**: Descoped from MVP. Components render empty state or use workarounds (filter by parent_id for sub-issues). Backend work tracked separately.
5. **Frontend-backend type mismatch**: Backend uses `name` (not `title`), `state` as object (not string), `estimate_points` (not `estimatedHours`). **Mitigation**: Phase 1 includes T001a-T001c to align frontend types before any component work begins.

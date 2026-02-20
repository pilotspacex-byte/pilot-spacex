# Feature Specification: Note Editor Enhancements — Links, TOC, & Issue Gutter

**Feature Number**: 018
**Branch**: `018-note-editor-enhancements`
**Created**: 2026-02-20
**Status**: Draft
**Author**: Tin Dang

---

## Problem Statement

**Who**: All Pilot Space users (Architects, Tech Leads, PMs, Developers) working in the note editor

**Problem**: The note editor lacks critical navigation and cross-referencing capabilities. Notes cannot link to other notes, creating information silos. Users have no visual overview of document structure or linked issues while editing. The project assignment is read-only and cannot be changed without leaving the editor. These gaps force users to context-switch between views, losing their writing flow.

**Impact**: Users spend extra time navigating between notes, manually tracking cross-references, and losing context when searching for related content. The "Note-First" paradigm (DD-013) promises that thinking flows naturally into structure, but without note-to-note linking and at-a-glance structure/issue visibility, the paradigm is incomplete.

**Success**: Users can link notes bidirectionally, see document structure and linked issues at a glance in a left gutter, and manage project assignment — all without leaving the editor canvas.

---

## Stakeholders

| Stakeholder | Role | Interest | Input Needed | Review Point |
|-------------|------|----------|-------------|-------------|
| TinDang | Architect / PO | Cross-note knowledge graph, clean UX | Architecture approval | Spec + plan review |
| End Users | Writers / PMs | Fast note linking, minimal friction | Usability feedback | Acceptance test |
| Frontend Dev | Implementer | TipTap extension patterns, performance | Extension feasibility | Pre-plan review |
| Backend Dev | Implementer | Data model, RLS, API design | Schema design | Pre-plan review |

---

## User Scenarios & Testing

### User Story 1 — Wiki-Style Note Linking (Priority: P1)

A user is writing a note about "API Design" and wants to reference their earlier "Authentication Refactor" note. They type `[[` which opens an autocomplete dropdown. They type "auth" to filter, select "Authentication Refactor", and an inline chip appears in their text. The chip shows the current title of the linked note. Clicking the chip navigates to that note. In the linked note, a backlinks panel shows that "API Design" references it.

**Why this priority**: Cross-note linking is the core missing capability. Without it, notes are isolated documents rather than a connected knowledge base. This directly supports the Note-First paradigm (DD-013).

**Independent Test**: Create two notes. In note A, type `[[` and link to note B. Verify the chip renders with note B's title. Navigate to note B and verify note A appears in backlinks. Rename note B and verify note A's chip updates to the new title.

**Acceptance Scenarios**:

1. **Given** a user is editing a note, **When** they type `[[`, **Then** an autocomplete dropdown appears showing workspace notes filtered by typed text
2. **Given** the autocomplete is open, **When** the user selects a note, **Then** an inline chip renders showing the target note's current title with a note icon
3. **Given** a note contains `[[link]]` chips, **When** the linked note's title changes, **Then** the chip displays the updated title on next load (title resolved at render time, not stored in document)
4. **Given** a note contains `[[link]]` chips, **When** the user clicks a chip, **Then** they navigate to the linked note
5. **Given** a note is linked from other notes, **When** the user opens the backlinks sidebar tab, **Then** they see a list of all notes that reference this note
6. **Given** a linked note is deleted, **When** the chip renders, **Then** it shows a "Note not found" state with a visual indicator (dashed border, red icon)
7. **Given** a user types `[[`, **When** the autocomplete shows results, **Then** the current note is excluded from results (no self-links)

---

### User Story 2 — Left Gutter TOC with Magnet Effect (Priority: P1)

A user opens a long note with many headings. On desktop (>= 1024px), a vertical column of small dots appears in the left gutter, each dot representing a heading. As the user scrolls, the dot corresponding to the visible heading becomes larger and highlighted in the primary teal color. Neighboring dots subtly pull toward the active dot (magnet effect). Hovering any dot shows the heading text. Clicking a dot scrolls to that heading.

**Why this priority**: Document navigation is essential for long notes. The existing AutoTOC component is built but not mounted. This story activates and enhances it.

**Independent Test**: Create a note with 5+ headings (H1, H2, H3). On desktop, verify TOC dots appear in left gutter. Scroll and verify active dot changes. Hover dots and verify heading labels. Click a dot and verify smooth scroll. Resize to mobile and verify gutter hides gracefully.

**Acceptance Scenarios**:

1. **Given** a note has headings (H1-H3), **When** displayed on desktop (>= 1024px), **Then** the left gutter shows dots aligned to heading positions with connecting lines
2. **Given** the user scrolls the note, **When** a heading enters the viewport, **Then** its dot animates to active state (larger, primary color) and neighboring dots pull toward it (magnet effect)
3. **Given** a TOC dot is visible, **When** the user hovers or focuses it, **Then** a tooltip shows the heading text (slide-in from left, max 180px truncated)
4. **Given** a TOC dot is visible, **When** the user clicks or presses Enter, **Then** the editor smooth-scrolls to that heading
5. **Given** the viewport is below 1024px, **When** viewing the editor, **Then** the left gutter is hidden (fallback to existing horizontal TOC or none)
6. **Given** a note has no headings, **When** displayed on desktop, **Then** the TOC track is empty (no dots, no connecting lines)
7. **Given** `prefers-reduced-motion` is enabled, **When** scrolling, **Then** all spring animations and magnet effects are replaced with instant state changes

---

### User Story 3 — Left Margin Issue Indicators (Priority: P2)

A user opens a note that has several blocks with linked issues. In the left gutter (inner column, next to the TOC dots), small colored dots appear aligned to the blocks that contain issue references. The dot color reflects the issue state (e.g., amber for In Progress, teal for Done). Hovering a dot shows a popover with issue details. Clicking navigates to the issue.

**Why this priority**: Builds on P1 gutter infrastructure. Provides at-a-glance issue context without breaking writing flow. Currently, issue links in the editor are non-interactive (click handlers are no-ops).

**Independent Test**: Create a note with inline issue references in several blocks. Verify colored dots appear in the left gutter aligned to those blocks. Hover a dot and verify issue details popover. Click through to the issue detail page.

**Acceptance Scenarios**:

1. **Given** a note has blocks with linked issues (via NoteIssueLink or InlineIssue nodes), **When** displayed on desktop, **Then** colored dots appear in the issue indicator column aligned to those blocks
2. **Given** a block has one linked issue, **When** the dot is hovered or focused, **Then** a popover shows issue key, title, state badge, priority, and assignee
3. **Given** a block has 4+ linked issues, **When** rendered, **Then** the first 3 issues show as stacked dots and an overflow badge shows the remaining count
4. **Given** an issue indicator dot is visible, **When** the user clicks or presses Enter on the popover's "Open Issue" link, **Then** they navigate to the issue detail page
5. **Given** inline issue text (e.g., "PS-42") in the editor, **When** the user clicks the detected issue text, **Then** they navigate to that issue (wiring the currently no-op IssueLinkExtension onClick)

---

### User Story 4 — Slash Command Note Embed (Priority: P2)

A user types `/link-note` in the slash command menu to insert a block-level preview of another note. The autocomplete opens, they select a note, and a preview card appears showing the note title, first 3 lines of content, and metadata. This is richer than the inline `[[chip]]` and serves as a "see also" reference block.

**Why this priority**: Complements the inline wiki-style link. Some references deserve more visual weight than an inline chip.

**Independent Test**: Type `/link-note`, select a note. Verify the embed card renders with title, preview text, and metadata. Verify clicking navigates to the note.

**Acceptance Scenarios**:

1. **Given** a user types `/link-note`, **When** the slash command triggers, **Then** the same note search autocomplete opens
2. **Given** a note is selected from the autocomplete, **When** inserted, **Then** a block-level embed card renders with title, 3-line preview, and metadata footer
3. **Given** the linked note is deleted, **When** the embed card renders, **Then** it shows a "Note unavailable" error state

---

### User Story 5 — Project Picker in Note Metadata (Priority: P2)

A user creates a note and later wants to assign it to a project. In the metadata bar, they click the project area, which opens a searchable dropdown of workspace projects. They select a project, and the note is immediately reassigned. The progress bar updates to reflect the selected project's issue completion.

**Why this priority**: Currently, project assignment is read-only in the editor. Users must leave the editor to change it. This is a quick UX improvement.

**Independent Test**: Open a note with no project. Click the project area, search and select a project. Verify the project name and progress bar update. Change to a different project. Remove the project assignment.

**Acceptance Scenarios**:

1. **Given** a note is open in the editor, **When** the user clicks the project area in the metadata bar, **Then** a searchable dropdown appears with workspace projects
2. **Given** the project dropdown is open, **When** the user selects a project, **Then** the note's project updates optimistically with rollback on error
3. **Given** a note has a project assigned, **When** the user selects "Remove project", **Then** the project assignment is cleared
4. **Given** a note is in read-only mode, **When** viewing the metadata bar, **Then** the project shows as a non-interactive link (existing behavior preserved)

---

### Edge Cases

- What happens when a user types `[[` but there are no notes matching the query? Display "No notes found" in the autocomplete, allow creating a new note (future enhancement, not P1)
- What happens when a note linked via `[[chip]]` is deleted? Show "Note not found" state with dashed red border and italic text
- What happens when two users simultaneously edit notes that link to each other? NoteNoteLink creation is idempotent — duplicate links are ignored (existing pattern from NoteIssueLink)
- What happens when a block with linked issues is deleted? Issue indicators disappear; NoteIssueLink records persist (soft-delete pattern, cleaned up on save reconciliation)
- What happens when 50+ headings exist in a single note? TOC dot positions use `offsetTop` (no per-frame layout reflow). Position cache rebuilds only when heading structure changes, not on every keystroke
- What happens on mobile/tablet (< 1024px)? Left gutter is hidden. Inline chips and issue nodes still work. TOC falls back to existing horizontal variant or none
- What happens when a user uses keyboard-only navigation? All dots are `<button>` elements with 24px+ hit areas. Popovers and tooltips open on focus, not just hover

---

## Requirements

### Functional Requirements

- **FR-001**: System MUST allow users to create inline links between notes via a `[[` autocomplete trigger
- **FR-002**: System MUST resolve linked note titles at render time (not from stored document content) so titles stay current when target notes are renamed
- **FR-003**: System MUST display backlinks (incoming note references) in a sidebar panel
- **FR-004**: System MUST display a vertical TOC in the left gutter on desktop viewports (>= 1024px) with dots aligned to heading positions
- **FR-005**: System MUST animate TOC dots with a magnet snap effect where neighboring dots pull toward the active heading dot
- **FR-006**: System MUST show heading text on hover/focus of TOC dots
- **FR-007**: System MUST display issue indicator dots in the left gutter aligned to blocks with linked issues
- **FR-008**: System MUST show issue details (key, title, state, priority) on hover/focus of issue indicator dots
- **FR-009**: System MUST allow users to change a note's project assignment via a searchable dropdown in the metadata bar
- **FR-010**: System MUST handle deleted linked notes gracefully with a visual "not found" state
- **FR-011**: System MUST hide the left gutter on viewports below 1024px
- **FR-012**: System MUST provide keyboard navigation for all gutter interactions (tab, arrow keys, enter, escape)
- **FR-013**: System MUST respect `prefers-reduced-motion` for all animations
- **FR-014**: System MUST provide minimum 24px x 24px touch/click targets for all gutter dots (WCAG 2.2 SC 2.5.8)
- **FR-015**: System MUST support a `/link-note` slash command that inserts a block-level note embed card
- **FR-016**: System MUST make inline issue text (detected by pattern) and inline issue nodes clickable, navigating to the issue detail page
- **FR-017**: System MUST make note link creation idempotent — multiple `[[links]]` to the same note from different blocks are supported without conflict
- **FR-018**: System SHOULD exclude the current note from `[[` autocomplete results (prevent self-links)
- **FR-019**: System SHOULD throttle gutter position recalculation to avoid layout thrash on large notes (rebuild only when heading structure changes)

### Key Entities

- **NoteNoteLink**: A directional relationship between two notes. Key attributes: source note, target note, link type (inline/embed), source block ID. Relationships: belongs to workspace, references two Notes
- **Note (extended)**: Existing entity gains bidirectional note links (outgoing links + incoming backlinks) and enhanced project picker interaction
- **GutterState**: UI-only model tracking heading positions, active heading, issue-to-block mapping, and magnet effect offsets. Not persisted — computed from editor state

---

## Success Criteria

- **SC-001**: Users can create and navigate note-to-note links within 3 seconds (type `[[`, search, select, chip appears)
- **SC-002**: TOC magnet effect renders at 60fps during scrolling on notes with up to 50 headings
- **SC-003**: Linked note titles update within 1 page load after the target note is renamed (render-time resolution)
- **SC-004**: All gutter interactions (dots, popovers, navigation) are operable via keyboard alone
- **SC-005**: Gutter is hidden without layout shift on viewports below 1024px
- **SC-006**: Test coverage > 80% for all new components and extensions

---

## Constitution Compliance

| Principle | Applies? | How Addressed |
|-----------|----------|--------------|
| I. AI-Human Collaboration | No | No AI approval flows in this feature |
| II. Note-First | Yes | Core enhancement to the note editor — notes become interconnected knowledge base |
| III. Documentation-Third | Yes | Backlinks auto-generated from note content, no manual maintenance |
| IV. Task-Centric | Yes | Each user story is independently testable and demo-able |
| V. Collaboration | Yes | Backlinks create shared knowledge graph across workspace members |
| VI. Agile Integration | Yes | Stories fit sprint planning with P1/P2 prioritization |
| VII. Notation Standards | No | No diagram notation needed |

---

## Validation Checklists

### Requirement Completeness

- [x] No `[NEEDS CLARIFICATION]` markers remain
- [x] Every user story has acceptance scenarios with Given/When/Then
- [x] Every story is independently testable and demo-able
- [x] Edge cases documented for each story
- [x] All entities have defined relationships

### Specification Quality

- [x] Focus is WHAT/WHY, not HOW
- [x] No technology names anywhere in requirements
- [x] Requirements use RFC 2119 keywords (MUST/SHOULD/MAY)
- [x] Success criteria are measurable with numbers/thresholds
- [x] Written for business stakeholders, not developers
- [x] One capability per FR line (no compound requirements)

### Structural Integrity

- [x] Stories prioritized P1 through P2
- [x] Functional requirements numbered sequentially (FR-001 through FR-019)
- [x] Key entities identified with attributes and relationships
- [x] No duplicate or contradicting requirements
- [x] Problem statement clearly defines WHO/PROBLEM/IMPACT/SUCCESS

### Constitution Gate

- [x] All applicable principles checked and addressed
- [x] No violations

---

## Risk Register (from Devil's Advocate Review)

| ID | Risk | Probability | Impact | Score | Response | Trigger |
|----|------|-------------|--------|-------|----------|---------|
| R-1 | Magnet animation technology mismatch | 2 | 3 | 6 | Mitigate: Use existing motion library (already in deps) | Implementation starts |
| R-2 | Gutter positioning fails in nested scroll containers | 3 | 5 | 15 | Avoid: Use absolute positioning (dots scroll with document) | Gutter integration |
| R-3 | Heading + issue dot visual collision | 2 | 2 | 4 | Accept: Separate columns prevent overlap; count badge for multi-issue headings | Notes with many linked issues on headings |
| R-4 | Stale note titles in wiki link chips | 4 | 4 | 16 | Avoid: Store only note ID, resolve title at render time | Note rename after linking |
| R-7 | Duplicate link creation on multi-link notes | 3 | 3 | 9 | Mitigate: Idempotent link creation, reconcile on save | Multiple [[links]] to same target |
| R-8 | Inaccessible hover-only interactions | 3 | 4 | 12 | Avoid: 24px+ hit areas, focus triggers for all popovers | Touch/keyboard usage |

---

## Next Phase

After this spec passes all checklists:

1. **Proceed to planning** — Use `template-plan.md` to create the implementation plan (architecture plan draft exists at `tmp/note-editor-plan.md`, UI design at `tmp/note-editor-ui-design.md`, review at `tmp/note-editor-review.md`)
2. **Resolve R-2 positioning** — Plan must be updated with absolute positioning decision
3. **Resolve R-4 title resolution** — Plan must be updated with render-time title resolution
4. **Share for review** — This spec is the alignment artifact for all stakeholders

# Feature Specification: MVP Note-First Complete

**Feature Number**: 018
**Branch**: `018-mvp-note-first-complete`
**Created**: 2026-02-20
**Status**: Draft
**Author**: Tin Dang

---

## Problem Statement

**Who**: Software development teams (architects, tech leads, PMs, developers) using PilotSpace for AI-augmented project management.

**Problem**: The current PilotSpace app has critical functional bugs (Issues Kanban broken, AI Chat 404, Approvals/Costs errors) and incomplete core workflows. The "Note-First" paradigm — where ideas flow naturally from notes to structured issues — is not yet realized end-to-end. Notes cannot effectively feed into issues, and issues lack the rich AI context needed for coding agents to implement them autonomously.

**Impact**: Without a working note-to-issue pipeline, users must manually create and populate issues, losing 60-80% of context captured during brainstorming. AI coding agents (Claude Code) cannot get sufficient context to implement features without extensive manual prompting, adding 2-4 hours per issue.

**Success**: Users write freely in notes, AI detects actionable items and extracts them as fully-contextualized issues. Each issue carries enough context (related notes, dependency graph, acceptance criteria, technical requirements) that an AI coding agent can read it and begin implementation with minimal human guidance.

---

## Stakeholders

| Stakeholder | Role | Interest | Input Needed | Review Point |
|-------------|------|----------|-------------|-------------|
| Tin Dang | Product Owner / Architect | MVP completeness, AI coding agent integration | Architecture decisions, priority calls | Spec + Plan review |
| Dev Team | Implementation | Clear tasks, working foundation | Bug impact assessment | Pre-plan review |
| End Users | Workspace users | Reliable features, smooth workflow | Usage patterns, pain points | Acceptance test |
| AI Coding Agents | Consumers of issue context | Rich, structured context per issue | Context schema requirements | Integration test |

---

## User Scenarios & Testing

### User Story 1 — Fix Critical Bugs & Stabilize Platform (Priority: P1)

The platform has 7 critical bugs that prevent basic usage. Users cannot view issues in correct workflow states, cannot access AI Chat, Approvals shows errors, Costs page fails, and the homepage displays incorrect data. These must be fixed before any new features can be built or tested.

**Why this priority**: The platform is unusable for demo or development without these fixes. Every other story depends on a stable foundation.

**Independent Test**: After fixes, a user can log in, view the homepage with correct note word counts, navigate to Issues and see issues distributed across Backlog/Todo/In Progress/In Review/Done columns, access AI Chat without 404, view Approvals without errors, and see the Costs page load.

**Acceptance Scenarios**:

1. **Given** seeded demo data with issues in various states, **When** user navigates to Issues page, **Then** issues appear in correct Kanban columns matching their state (not all in Backlog)
2. **Given** a logged-in user, **When** user clicks "AI Chat" in sidebar, **Then** the AI Chat page loads without 404 error
3. **Given** a logged-in user, **When** user navigates to Approvals, **Then** the page loads showing approval tabs without "Bad Request" error
4. **Given** a logged-in user, **When** user navigates to Costs, **Then** the cost dashboard loads without "Not Found" error
5. **Given** notes with content, **When** user views the homepage, **Then** note cards show correct word count (not "0 words")
6. **Given** an issue with seeded priority and estimate, **When** user opens issue detail, **Then** priority shows actual value (not "No priority") and estimate shows "No estimate" instead of "null pts"
7. **Given** pinned and recently accessed notes, **When** user views the sidebar, **Then** PINNED and RECENT sections are populated

---

### User Story 2 — Homepage as Intelligent Workspace Dashboard (Priority: P1)

When a user logs in, they should see a dashboard that orients them immediately: what happened since they last visited, what needs their attention, and quick actions to start working. The homepage should surface AI-generated insights about workspace health and activity.

**Why this priority**: The homepage is the first thing users see. A blank or broken homepage undermines confidence in the entire platform. This is the entry point for the Note-First workflow.

**Independent Test**: User logs in and sees: activity feed grouped by date with note previews, AI insights panel with workspace health, quick actions for creating notes/issues, and sidebar pinned/recent notes populated.

**Acceptance Scenarios**:

1. **Given** a workspace with recent activity, **When** user visits homepage, **Then** activity feed shows note cards grouped by Today/Yesterday/This Week with content previews (first 2 lines)
2. **Given** a workspace with notes and issues, **When** user views AI Insights panel, **Then** panel shows workspace summary (total notes, issues by state, project health indicators)
3. **Given** a logged-in user, **When** user clicks "What's on your mind?" quick input, **Then** a new note is created and the editor opens immediately
4. **Given** user has pinned notes, **When** homepage loads, **Then** PINNED section in sidebar shows up to 5 pinned notes with titles
5. **Given** user has accessed notes recently, **When** homepage loads, **Then** RECENT section shows last 10 accessed notes

---

### User Story 3 — Note Editor for Brainstorming & PM (Priority: P1)

The note editor is the primary workspace for brainstorming and project management. Users write freely with rich text, and the editor provides structural blocks for PM workflows: task lists, decision logs, meeting notes, and requirements capture. The editor must support slash commands for quick block insertion and a floating toolbar for text formatting.

**Why this priority**: This is the core of the "Note-First" paradigm. Without a capable editor, users cannot capture ideas in a way that feeds the intent-to-issues pipeline.

**Independent Test**: User creates a note, types with slash commands to insert headings/lists/code blocks/task lists, selects text to see floating toolbar, and the auto-save indicator confirms saves within 2 seconds.

**Acceptance Scenarios**:

1. **Given** user is in note editor, **When** user types "/" at the start of a line, **Then** a command palette appears with block types: Heading (1-3), Bullet List, Numbered List, Task List, Code Block, Quote, Table, Divider
2. **Given** user selects text in the editor, **When** text is highlighted, **Then** a floating toolbar appears with: Bold, Italic, Strikethrough, Code, Link, Highlight options
3. **Given** user is typing in the editor, **When** 2 seconds pass without changes, **Then** content auto-saves and a save indicator shows in the header
4. **Given** user has written content, **When** user clicks version history icon, **Then** a panel shows previous versions with timestamps and option to restore
5. **Given** a note with content, **When** user views note header, **Then** word count, last-modified date, and project association are displayed correctly

---

### User Story 4 — Intent-to-Issues Pipeline (Priority: P1)

Users write notes containing actionable items (bugs, features, tasks, decisions). The AI agent detects these intents and helps extract them as structured issues. Extracted issues maintain bidirectional links to their source note, carrying full context including surrounding paragraphs, related notes, and technical requirements.

**Why this priority**: This is the key differentiator — "issues emerge from refined thinking." Without this pipeline, PilotSpace is just another note-taking app + issue tracker.

**Independent Test**: User writes a note with several actionable items, clicks "Extract issues from this note", AI identifies 3-5 potential issues, user reviews and approves them, issues are created with links back to the source note, and clicking the issue shows the originating note context.

**Acceptance Scenarios**:

1. **Given** a note with actionable text like "We need to migrate from sessions to JWT", **When** user clicks "Extract issues from this note", **Then** AI identifies actionable items categorized as Explicit (directly stated), Implicit (inferred), or Related (contextual)
2. **Given** AI has identified potential issues, **When** extraction results display, **Then** each potential issue shows: suggested title, description, priority, source text highlighted in the note with rainbow border
3. **Given** user reviews extracted issues, **When** user approves an issue, **Then** the issue is created in the selected project with: title, description, priority, link to source note, and the source paragraph reference
4. **Given** an issue was extracted from a note, **When** user views the note, **Then** inline badges like [AUTH-45] appear at the extraction point, clickable to navigate to the issue
5. **Given** an issue was extracted from a note, **When** user views the issue detail, **Then** a "Source Notes" section shows the originating note with the relevant paragraph highlighted

---

### User Story 5 — AI Coding Agent Context per Issue (Priority: P2)

Each issue should carry a rich context object that AI coding agents can consume to implement the feature/fix. The context includes: issue description, acceptance criteria, technical requirements, related notes (full content), dependency graph (blocking/blocked-by issues), project architecture context, and suggested implementation approach.

**Why this priority**: This transforms PilotSpace from a PM tool into an AI-augmented development platform. The context object is what makes Claude Code effective at implementing issues autonomously.

**Independent Test**: User opens an issue, clicks "AI Context" tab, sees a structured context document that includes all related information. User can copy or export this context for use with Claude Code.

**Acceptance Scenarios**:

1. **Given** an issue with description, acceptance criteria, and technical requirements, **When** user clicks "Generate AI Context", **Then** AI produces a structured context document combining all issue fields
2. **Given** an issue linked to source notes, **When** AI context is generated, **Then** context includes relevant paragraphs from linked notes with surrounding context
3. **Given** an issue with blocking/blocked-by relationships, **When** AI context is generated, **Then** context includes dependency graph showing related issues and their states
4. **Given** AI context has been generated, **When** user clicks "Copy for Claude Code", **Then** the context is formatted as a markdown prompt optimized for AI coding agents, copied to clipboard
5. **Given** an issue in a project with existing codebase context, **When** AI context is generated, **Then** context includes relevant file paths, architecture patterns, and coding conventions from the project

---

### User Story 6 — Issues Kanban & Detail Polish (Priority: P2)

The Issues page should provide a fully functional Kanban board with drag-and-drop state transitions, proper issue cards showing title/priority/assignee, and a detailed issue view with all fields working correctly. List and table views should also function.

**Why this priority**: Issues are the output of the Note-First pipeline. Users need to manage, prioritize, and track issues effectively.

**Independent Test**: User views Issues page with issues distributed across Kanban columns, drags an issue from "Todo" to "In Progress", opens an issue to see all properties correctly displayed, and switches between Kanban/List/Table views.

**Acceptance Scenarios**:

1. **Given** issues exist in various states, **When** user views Kanban board, **Then** issue cards show: identifier, title, priority indicator (color-coded arrow), assignee avatar, and creation date
2. **Given** an issue in "Todo" column, **When** user drags it to "In Progress", **Then** issue state updates and card moves to the new column with animation
3. **Given** issues exist, **When** user switches to List view, **Then** issues display in a table with sortable columns: identifier, title, state, priority, assignee, labels, updated date
4. **Given** user opens issue detail, **When** viewing Properties panel, **Then** all fields are functional: State dropdown, Priority selector, Type selector, Assignee picker, Labels multi-select, Cycle picker, Estimate points, Hours input, Start/Due dates
5. **Given** user is on issue detail, **When** user adds acceptance criteria, **Then** criteria are saved and display as a checklist

---

### User Story 7 — Settings & Configuration Complete (Priority: P3)

All settings pages should be functional: workspace general, members with invite flow, AI providers with validation, integrations (GitHub/Slack), billing placeholder, profile with save, and skills configuration.

**Why this priority**: Settings are needed for workspace setup but don't block the core Note-First workflow.

**Independent Test**: User navigates through all settings pages without errors, can update workspace name, invite a member, configure AI API keys, and connect GitHub.

**Acceptance Scenarios**:

1. **Given** user is on General settings, **When** user changes workspace name and clicks save, **Then** the name updates throughout the app
2. **Given** user is on Members settings, **When** user clicks "Invite Member" and enters an email, **Then** an invitation is sent and appears in pending invitations list
3. **Given** user is on AI Providers, **When** user enters an Anthropic API key and saves, **Then** key is validated, stored securely, and provider status shows "Connected"
4. **Given** user is on Integrations, **When** user clicks "Connect GitHub", **Then** OAuth flow initiates and returns to show connected repositories

---

### Edge Cases

- What happens when user extracts issues from an empty note? System shows message "No actionable items detected."
- What happens when AI context generation fails (no API key)? System shows clear error directing user to Settings > AI Providers.
- What happens when two users edit the same note? Last-write-wins with conflict notification toast.
- What happens when user drags issue to a state that requires a cycle? System prompts to assign a cycle first.
- What happens when the note content exceeds token limits for AI extraction? System processes in chunks and merges results.
- What happens when network drops during auto-save? System retries with exponential backoff and shows "Unsaved changes" indicator.

---

## Requirements

### Functional Requirements

- **FR-001**: System MUST display issues in the correct workflow state columns on the Kanban board so that users can see project progress at a glance
- **FR-002**: System MUST render the AI Chat page at the correct route so that users can access conversational AI features
- **FR-003**: System MUST load the Approvals page without errors so that users can review AI-suggested actions
- **FR-004**: System MUST load the Costs page with usage data so that users can track AI spending
- **FR-005**: System MUST display accurate word counts on homepage note cards so that users can gauge note length
- **FR-006**: System MUST show correct property values (priority, estimate) in issue detail so that users can manage issues effectively
- **FR-007**: System MUST populate sidebar PINNED and RECENT sections so that users can quickly navigate to frequently used notes
- **FR-008**: System MUST group homepage activity by date (Today/Yesterday/This Week) so that users can understand recent activity chronologically
- **FR-009**: System MUST display AI-generated workspace insights on the homepage so that users get immediate value upon login
- **FR-010**: System MUST provide a "/" slash command menu in the note editor with block types (headings, lists, code, tables, tasks) so that users can structure content quickly
- **FR-011**: System MUST show a floating toolbar on text selection with formatting options so that users can format text without keyboard shortcuts
- **FR-012**: System MUST auto-save note content within 2 seconds of last change with a visible save indicator
- **FR-013**: System MUST detect actionable items in notes (explicit tasks, implicit requirements, related work) when user triggers extraction
- **FR-014**: System MUST create issues from extracted items with bidirectional links to source notes
- **FR-015**: System MUST display inline issue badges in notes at extraction points, navigable to the linked issue
- **FR-016**: System MUST generate structured AI context per issue containing: description, acceptance criteria, technical requirements, source notes, dependency graph
- **FR-017**: System MUST provide a "Copy for Claude Code" action that formats issue context as an AI-optimized markdown prompt
- **FR-018**: System MUST support drag-and-drop issue state transitions on the Kanban board
- **FR-019**: System MUST render issue cards with identifier, title, priority indicator, and assignee avatar
- **FR-020**: System MUST provide functional List and Table view alternatives to Kanban
- **FR-021**: System SHOULD display note content previews (first 2 lines) on homepage activity cards
- **FR-022**: System SHOULD support version history with restore capability in the note editor
- **FR-023**: System SHOULD allow workspace invitation via email with role assignment
- **FR-024**: System SHOULD validate and securely store AI provider API keys
- **FR-025**: System MAY provide keyboard shortcut Command+K for global search/command palette

### Key Entities

- **Note**: A rich-text document for brainstorming and PM. Key attributes: title, content (TipTap JSON), word_count, project association, pin status, owner. Relationships: belongs to Workspace, optionally belongs to Project, has many NoteVersions, has many NoteIssueLinks.
- **Issue**: A trackable work item with state machine. Key attributes: name, description, state, priority, type, assignee, labels, estimate, hours, dates. Relationships: belongs to Project, belongs to State, has many NoteIssueLinks, has many IssueRelations (dependency graph).
- **NoteIssueLink**: Bidirectional link between notes and issues. Key attributes: note_id, issue_id, link_type (CREATED/EXTRACTED/REFERENCED), source_paragraph_ref. Relationships: belongs to Note, belongs to Issue.
- **AIContext**: Generated rich context for an issue. Key attributes: issue_id, context_json (structured markdown), source_notes, dependency_graph, generated_at. Relationships: belongs to Issue.
- **Intent**: A detected actionable item in a note. Key attributes: note_id, intent_type (explicit/implicit/related), source_text, suggested_title, suggested_priority, status (detected/approved/dismissed). Relationships: belongs to Note, may create Issue.

---

## Success Criteria

- **SC-001**: All 7 critical bugs resolved — zero error pages when navigating core features (Homepage, Notes, Issues, AI Chat, Approvals, Costs)
- **SC-002**: Users can complete the full Note-to-Issue flow (write note → extract issues → view linked issues) in under 3 minutes
- **SC-003**: AI context generation produces a structured document with at least 5 context sections (description, criteria, requirements, notes, dependencies) within 10 seconds
- **SC-004**: Issues display correctly across all 6 workflow states in the Kanban board with accurate counts
- **SC-005**: Note editor supports at least 8 block types via slash commands with under 200ms command palette response
- **SC-006**: Homepage loads with correct data (word counts, activity grouping, sidebar population) within 2 seconds
- **SC-007**: "Copy for Claude Code" produces a prompt that an AI coding agent can use to begin implementation without additional context gathering

---

## Constitution Compliance

| Principle | Applies? | How Addressed |
|-----------|----------|--------------|
| I. AI-Human Collaboration | Yes | Extract Issues requires human review/approval before creating issues. AI Context is generated on demand, not autonomously. |
| II. Note-First | Yes | Core focus — notes are the entry point for all work. Issues emerge from notes, not forms. |
| III. Documentation-Third | Yes | AI Context auto-generates documentation from issue + note content. No manual doc maintenance. |
| IV. Task-Centric | Yes | Each user story is independently testable and deliverable. Tasks are self-contained work units. |
| V. Collaboration | Yes | Notes support team viewing. Issues link to shared notes for knowledge sharing. |
| VI. Agile Integration | Yes | Stories fit sprint planning. P1 stories form Sprint 1, P2 form Sprint 2, P3 form Sprint 3. |
| VII. Notation Standards | No | No diagram/notation needs for this feature set. |

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
- [x] No technology names in requirements (tech names only in constraints section)
- [x] Requirements use RFC 2119 keywords (MUST/SHOULD/MAY)
- [x] Success criteria are measurable with numbers/thresholds
- [x] Written for business stakeholders, not developers
- [x] One capability per FR line (no compound requirements)

### Structural Integrity

- [x] Stories prioritized P1 through P3
- [x] Functional requirements numbered sequentially (FR-001 through FR-025)
- [x] Key entities identified with attributes and relationships
- [x] No duplicate or contradicting requirements
- [x] Problem statement clearly defines WHO/PROBLEM/IMPACT/SUCCESS

### Constitution Gate

- [x] All applicable principles checked and addressed
- [x] No violations

---

## Next Phase

After this spec passes all checklists:

1. **Resolve remaining ambiguities** — None remaining
2. **Proceed to planning** — Use `template-plan.md` to create the implementation plan
3. **Share for review** — This spec is the alignment artifact for all stakeholders

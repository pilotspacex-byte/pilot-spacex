# Feature Specification: Pilot Space Phase 2

**Feature Branch**: `002-pilot-space-phase2`
**Created**: 2026-01-23
**Status**: Draft
**Dependency**: Requires completion of `001-pilot-space-mvp`
**Scope**: P2 Features - Enhanced Productivity

## Summary

Phase 2 extends the Pilot Space MVP with enhanced productivity features including modules/epics organization, documentation pages, AI task decomposition, architecture diagram generation, Slack integration, command palette navigation, knowledge graph visualization, templates, and notifications.

**Prerequisite**: All P0 + P1 features from MVP must be complete and stable.

## User Stories (9 Total)

| Priority | User Story | Description |
|----------|------------|-------------|
| P2 | US-05 | Modules/Epics |
| P2 | US-06 | Documentation Pages |
| P2 | US-07 | Task Decomposition |
| P2 | US-08 | Architecture Diagrams |
| P2 | US-09 | Slack Integration |
| P2 | US-13 | Command Palette & Search |
| P2 | US-14 | Knowledge Graph |
| P2 | US-15 | Templates |
| P2 | US-17 | Notifications |

---

## Clarifications (from MVP Sessions)

### US-05 - Modules/Epics
- Q: Should modules have target dates? → A: Optional target date with overdue warning badge.
- Q: How to calculate module progress? → A: Hybrid. Story points if available, issue count as fallback.

### US-06 - Documentation Pages
- Q: Autosave timing? → A: 1-2 seconds inactivity (1.5s debounce).
- Q: Code block features? → A: Syntax highlighting, language selector, line numbers, copy button.
- Q: Image insert methods? → A: Paste from clipboard, drag & drop, upload via button, URL embed.

### US-07 - Task Decomposition
- Q: What estimation unit? → A: Story points (Fibonacci: 1, 2, 3, 5, 8, 13).

### US-08 - Architecture Diagrams
- Q: How to edit Mermaid diagrams? → A: Code editor + live preview side-by-side.

### US-09 - Slack Integration
- Q: How should `/pilot create` work? → A: Open Slack modal with title, description, priority fields.

### US-13 - Command Palette
- Q: Should AI suggestions learn from behavior? → A: Context-only ranking (no frequency learning for Phase 2).

### US-14 - Knowledge Graph
- Q: Should graph preserve user positions? → A: Always auto-layout with ForceAtlas2 (no position persistence).
- Q: What relationship types? → A: Explicit (user-created) + semantic (AI-detected) + mentions.
- Q: How to detect semantic relationships? → A: Attach metadata (project, epic, reference issue) + embedding similarity (cosine > 0.7).
- Q: Where to store graph? → A: PostgreSQL adjacency table (`relationships`: from_id, to_id, type, weight).
- Q: When to update relationships? → A: Explicit links on save; semantic relationships recalculated weekly via batch job.

### US-15 - Templates
- Q: Where to store AI-generated templates? → A: Workspace-level library for team reuse.
- Q: What placeholder syntax for templates? → A: Smart detection. AI infers fill-in areas from context. No special syntax.

### US-17 - Notifications
- Q: How to determine notification priority? → A: AI considers urgency (deadline), user assignment, and mention type.

---

## User Scenarios & Testing

### User Story 5 - Organize Work with Modules/Epics (Priority: P2)

A product manager groups related issues into modules (epics) to track feature-level progress and organize the product roadmap.

**Why this priority**: Modules provide essential organizational structure but are not required for basic issue tracking to function.

**Independent Test**: Can be tested by creating modules, associating issues, and verifying progress aggregation displays correctly.

**Acceptance Scenarios**:

1. **Given** a user is creating a module, **When** they provide name and description, **Then** the module is created with 0% progress
2. **Given** a module exists, **When** issues are linked to it, **Then** the module progress reflects the percentage of completed issues
3. **Given** multiple modules exist, **When** viewing the modules list, **Then** users see each module with issue count, progress, and target date
4. **Given** a user views a module, **When** they check details, **Then** they see all linked issues with their current states

---

### User Story 6 - Create and Maintain Documentation Pages (Priority: P2)

A team member creates rich documentation pages within the project workspace, with AI assistance for generating content from code or discussions.

**Why this priority**: Documentation is important for knowledge management but teams can function initially with external docs. AI doc generation adds significant value.

**Independent Test**: Can be tested by creating pages with the rich text editor, requesting AI-generated documentation, and verifying autosave works correctly.

**Acceptance Scenarios**:

1. **Given** a user opens the page editor, **When** they write content, **Then** rich text formatting (headers, lists, code blocks, tables) is supported
2. **Given** a user is editing a page, **When** they pause typing, **Then** content is automatically saved within 5 seconds
3. **Given** a user requests AI documentation, **When** they specify a code file or feature, **Then** AI generates relevant documentation draft
4. **Given** generated content is displayed, **When** the user reviews it, **Then** they can edit, approve, or regenerate sections
5. **Given** a page exists, **When** another user views it, **Then** they see the latest saved version (no real-time co-editing)
6. **Given** a user adds a code block, **When** editing code, **Then** syntax highlighting, language selector, line numbers, and copy button are available
7. **Given** a user wants to add an image, **When** choosing insert method, **Then** they can paste from clipboard, drag & drop, upload via button, or embed via URL

---

### User Story 7 - Decompose Features into Tasks with AI (Priority: P2)

A tech lead or product manager describes a feature and AI automatically breaks it down into actionable development tasks with estimates and dependencies.

**Why this priority**: Task decomposition accelerates sprint planning and ensures comprehensive task coverage. Provides high value but requires other features to be useful.

**Independent Test**: Can be tested by describing a feature and verifying AI generates sensible task breakdown with estimates.

**Acceptance Scenarios**:

1. **Given** a user creates a feature/epic, **When** they request AI decomposition, **Then** AI generates a list of subtasks within 30 seconds
2. **Given** AI generates tasks, **When** displaying results, **Then** each task includes title, description, type (frontend/backend/QA), and story point estimate
3. **Given** tasks are generated, **When** dependencies exist, **Then** AI identifies and marks task dependencies
4. **Given** decomposition results are shown, **When** the user reviews them, **Then** they can accept all, modify individual tasks, or reject and regenerate
5. **Given** tasks are accepted, **When** confirmed, **Then** sub-issues are created and linked to the parent feature

---

### User Story 8 - Generate Architecture Diagrams (Priority: P2)

A developer or architect describes a system or requests analysis of code, and AI generates appropriate diagrams in standard notation formats.

**Why this priority**: Visual documentation aids understanding and communication but is not blocking for core workflow.

**Independent Test**: Can be tested by requesting a diagram via natural language and verifying valid Mermaid output is generated.

**Acceptance Scenarios**:

1. **Given** a user describes a system flow, **When** they request a diagram, **Then** AI generates a Mermaid diagram within 15 seconds
2. **Given** a diagram is generated, **When** displayed, **Then** it renders visually in the page editor
3. **Given** diagram output, **When** the user wants to modify, **Then** they can edit the diagram code directly
4. **Given** multiple diagram types are supported, **When** requesting, **Then** user can specify sequence, class, flowchart, ERD, or C4 component types
5. **Given** a generated diagram, **When** the user approves it, **Then** they can insert it directly into a documentation page

---

### User Story 9 - Receive Notifications via Slack (Priority: P2)

A team member receives relevant notifications about issues, PRs, and sprint events in their Slack workspace without leaving their communication tool.

**Why this priority**: Slack integration keeps teams informed but is not required for core functionality.

**Independent Test**: Can be tested by linking a Slack workspace, triggering events, and verifying notifications appear in the configured channel.

**Acceptance Scenarios**:

1. **Given** Slack integration is configured, **When** an issue is created, **Then** a notification is posted to the linked channel within 30 seconds
2. **Given** a notification is posted, **When** viewing it, **Then** it shows issue title, assignee, priority, and link back to Pilot Space
3. **Given** Slack commands are enabled, **When** a user types `/pilot create`, **Then** they can create an issue directly from Slack
4. **Given** a Pilot Space URL is shared in Slack, **When** the message is viewed, **Then** the link unfurls with a rich preview
5. **Given** notification preferences exist, **When** a user configures them, **Then** they control which events trigger Slack messages

---

### User Story 13 - Navigate with Command Palette and Search (Priority: P2)

A power user quickly accesses features, searches content, and executes AI actions using keyboard-driven command palette and search interfaces.

**Why this priority**: Efficient navigation reduces friction for daily use. Command palette and search are expected features in modern productivity tools.

**Reference**: DD-018 (Command Palette), DD-019 (Full-Page Search), DD-021 (Keyboard Shortcuts)

**Acceptance Scenarios**:

1. **Given** a user presses Cmd+P, **When** the palette opens, **Then** AI suggestions appear based on current context (selection, active block, document)
2. **Given** command palette is open, **When** typing, **Then** fuzzy search matches commands with keyboard shortcut hints
3. **Given** a user presses Cmd+K, **When** search modal opens, **Then** it shows recent items before any query is entered
4. **Given** search query is entered, **When** results display, **Then** content type filters are available (All, Notes, Issues, Projects)
5. **Given** search results exist, **When** pressing Tab on a result, **Then** a preview appears without navigation
6. **Given** slash commands are available, **When** typing "/" in editor, **Then** command menu shows AI actions, formatting, and block insertion options
7. **Given** a user presses "?" key, **When** not in text input, **Then** a keyboard shortcut guide overlay appears
8. **Given** a user clicks the FAB (bottom-right), **When** the button activates, **Then** an AI-enabled search bar opens with keyword + semantic search
9. **Given** the AI panel is collapsed, **When** viewing the bottom bar, **Then** a thin bar with pulse dot indicates AI availability; click expands full panel
10. **Given** the AI panel is expanded, **When** viewing the panel, **Then** a free-form input and static/dynamic action chips (Summarize, Generate diagram, Extract tasks) appear
11. **Given** a user selects blocks, **When** pressing Cmd+Shift+Up/Down, **Then** the selected blocks move up/down in the document
12. **Given** a user hovers over a UI element, **When** hover exceeds 1 second, **Then** a progressive tooltip shows detailed help and keyboard shortcut

---

### User Story 14 - Explore Knowledge Graph (Priority: P2)

A user visualizes connections between notes, issues, and projects in an interactive graph view to discover patterns and navigate relationships.

**Why this priority**: Graph visualization helps users understand complex project relationships and discover hidden connections between work items.

**Reference**: DD-037 (Force-Directed Graph View)

**Acceptance Scenarios**:

1. **Given** a user opens graph view, **When** it loads, **Then** the current note appears at center, highlighted, with connected nodes around it
2. **Given** the graph displays, **When** viewing clusters, **Then** nodes are grouped by project with cluster labels
3. **Given** graph navigation, **When** panning/zooming, **Then** a mini-map shows current viewport position
4. **Given** a node is clicked once, **When** preview appears, **Then** it shows note summary with AI analysis of connections
5. **Given** a node is clicked twice, **When** opening, **Then** the user navigates to that note/issue
6. **Given** AI pattern detection, **When** patterns found, **Then** AI suggests potential connections between orphaned or related notes
7. **Given** graph metrics, **When** viewing, **Then** connection count, cluster count, and orphaned note count are displayed

---

### User Story 15 - Use Templates for New Notes (Priority: P2)

A user creates notes from templates (system, user-created, or AI-generated) with conversational AI assistance to fill template placeholders.

**Why this priority**: Templates accelerate note creation and ensure consistency. AI-assisted filling reduces the friction of blank-page anxiety.

**Reference**: DD-016 (New Note AI Prompt Flow), DD-033 (Template System)

**Acceptance Scenarios**:

1. **Given** a user clicks "New Note", **When** modal opens, **Then** AI greeting appears with prompt input and recommended templates based on recent work
2. **Given** template options display, **When** viewing, **Then** system templates (Sprint Plan, Feature Spec, Bug Analysis), user templates, and AI-generate option are available
3. **Given** a template is selected, **When** filling begins, **Then** a split view shows conversation on left and live preview on right
4. **Given** conversational filling, **When** user types natural language description, **Then** AI fills template hints from the description
5. **Given** template hints, **When** reviewing, **Then** user can skip optional hints with Skip button
6. **Given** an existing note, **When** user selects "Use as template", **Then** a copy is created as a new template
7. **Given** a new note is created, **When** similar notes exist in the workspace, **Then** AI shows similar notes with guidance on differences
8. **Given** similar notes are displayed, **When** viewing suggestions, **Then** user can view, link, or merge with the similar note

---

### User Story 17 - Receive AI-Prioritized Notifications (Priority: P2)

A team member receives notifications about workspace activity through an AI-prioritized inbox that intelligently categorizes and surfaces the most important updates.

**Why this priority**: Notifications keep users informed about team activity and reduce the need to manually check for updates. AI prioritization helps manage notification fatigue.

**Reference**: DD-038 (AI-Prioritized Notification Center)

**Acceptance Scenarios**:

1. **Given** a user views the notification center, **When** new notifications exist, **Then** they see a smart preview with count badge (e.g., "3 new")
2. **Given** notifications are displayed, **When** viewing priorities, **Then** AI-assigned labels appear (Urgent, Important, FYI)
3. **Given** a notification is viewed, **When** the user reads it briefly (2-3 seconds), **Then** it is automatically marked as read after the delay
4. **Given** notification settings exist, **When** configuring, **Then** the user can enable/disable triggers per event type
5. **Given** unread notifications exist, **When** viewing the list, **Then** unread items have a subtle background tint distinguishing them from read items

---

## Functional Requirements

### Navigation & Search (FR-040 to FR-044)

- **FR-040**: System MUST provide command palette (Cmd+P) with context-aware AI suggestions
- **FR-041**: System MUST provide full-page search modal (Cmd+K) with content type filters
- **FR-042**: System MUST support fuzzy search with keyboard navigation and preview on Tab
- **FR-043**: System MUST support slash commands (/) in editor for AI actions and formatting
- **FR-044**: System MUST provide keyboard shortcut guide on "?" key press

### Graph View & Templates (FR-045 to FR-049)

- **FR-045**: System MUST provide force-directed graph view showing note/issue connections
- **FR-046**: System MUST support graph navigation with pan/zoom and mini-map
- **FR-047**: System MUST detect and suggest connections between orphaned notes via AI
- **FR-048**: System MUST provide template gallery with system, user, and AI-generated templates
- **FR-049**: System MUST support conversational template filling with split view preview

### Slack Integration (FR-053 to FR-056)

- **FR-053**: System MUST support Slack integration for notifications and slash commands
- **FR-054**: System MUST post rich notifications to Slack channels for configured events
- **FR-055**: System MUST support creating issues from Slack via slash commands
- **FR-056**: System MUST support outbound webhooks for custom integrations

### Note Canvas Performance & UX (FR-066 to FR-074)

- **FR-066**: System MUST use virtualized rendering for notes with 1000+ blocks to maintain performance
- **FR-067**: System MUST auto-generate table of contents from headings with click-to-scroll and current section highlighting
- **FR-068**: System MUST display rich note header with created date, last edited, author, word count, and AI-estimated reading time with topic summary
- **FR-069**: System MUST save note content automatically after 1-2 seconds of inactivity with subtle "Saved" indicator
- **FR-070**: System MUST support extended undo stack including text changes, AI-generated content, block moves, and formatting
- **FR-071**: System MUST allow users to pin frequently accessed notes to sidebar top
- **FR-072**: System MUST allow users to resize the margin annotation panel (150px min, 350px max)
- **FR-073**: System MUST highlight linked content block when margin annotation is clicked with smooth scroll animation
- **FR-074**: System MUST show recent section combining both edited and viewed notes in one list

### AI Experience Enhancements (FR-075 to FR-082)

- **FR-075**: System MUST display AI confidence using contextual tags (Recommended, Default, Current, Alternative) with percentage on hover
- **FR-076**: System MUST auto-select the best LLM model per task type with automatic failover and user-accessible override option
- **FR-077**: System MUST display AI errors as non-blocking margin annotations with retry and dismiss options
- **FR-078**: System MUST show detailed AI status text during operations (e.g., "Searching codebase...", "Generating diagram...")
- **FR-079**: System MUST display AI artifacts with collapsed preview (first 2-3 lines) and fade-out gradient, expandable on click
- **FR-080**: System MUST include AI action section in right-click context menus with contextual suggestions
- **FR-081**: System MUST suggest tags based on content analysis (hybrid: predefined + user-created + AI-suggested)
- **FR-082**: System MUST support AI-powered bulk actions on selected items (summarize, extract issues from selection)

### Navigation & Onboarding Enhancements (FR-083 to FR-086)

- **FR-083**: System MUST provide a floating action button (FAB) at bottom-right that opens AI-enabled search bar
- **FR-084**: System MUST provide a collapsible AI panel at bottom with thin bar + pulse dot when collapsed, expanding to full input with action chips
- **FR-085**: System MUST support keyboard-only block reordering using Cmd+Shift+Up/Down
- **FR-086**: System MUST display progressive tooltips (instant brief label, detailed help + shortcut after 1 second hover)

### Editor Features (FR-088 to FR-089)

- **FR-088**: System MUST support full-featured code blocks with syntax highlighting, language selector, line numbers, and copy button
- **FR-089**: System MUST support all image insert methods: paste from clipboard, drag & drop, upload button, and URL embed

### Knowledge Discovery & Notifications (FR-090 to FR-092)

- **FR-090**: System MUST show similar existing notes after note creation with AI guidance explaining differences and suggested actions (view, link, merge)
- **FR-091**: System MUST provide a notification center in sidebar with AI-prioritized smart inbox and label tags (Urgent, Important, FYI)
- **FR-092**: System MUST support configurable notification triggers with delayed mark-as-read (brief viewing delay before auto-marking)

---

## AI Agents (Phase 2)

| Agent | SDK Mode | Provider | Description |
|-------|----------|----------|-------------|
| **TaskDecomposerAgent** | Claude SDK (agentic) | Anthropic Claude | Decomposes features into tasks |
| **DiagramGeneratorAgent** | Claude SDK `query()` | Anthropic Claude | Generates Mermaid diagrams |
| **DocumentGeneratorAgent** | Claude SDK `query()` | Anthropic Claude | Generates documentation |
| **PatternMatcherAgent** | Claude SDK (agentic) | Anthropic Claude | Discovers knowledge graph patterns |

---

## Edge Cases

- What happens when Slack integration fails mid-sync? Operations should be idempotent with retry capability and sync state preserved.
- What happens when a note has 5000+ blocks and user scrolls rapidly? Virtual scroll only renders visible blocks plus buffer; scroll position preserved on content changes.
- What happens when template placeholder detection fails? Fallback to displaying placeholder markers; user can manually edit.
- What happens when knowledge graph has 50,000+ nodes? Performance maintained via Sigma.js WebGL rendering; cluster filtering available.

---

## Related Documentation

- [MVP Specification](../001-pilot-space-mvp/spec.md) - Foundation features (P0 + P1)
- [Phase 3 Specification](../003-pilot-space-phase3/spec.md) - Discovery & Onboarding features (P3)
- [Implementation Plan](./plan.md) - Phase 2 implementation breakdown
- [Design Decisions](../../docs/DESIGN_DECISIONS.md) - Architectural decision records

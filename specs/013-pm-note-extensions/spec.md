# Feature Specification: PM Note Extensions — Enterprise SDLC Block Types

**Feature Number**: 013
**Branch**: `013-pm-note-extensions`
**Created**: 2026-02-11
**Revised**: 2026-02-11 (v2.0 — addressed 38 review findings)
**Status**: Draft v2
**Author**: Tin Dang

---

## Problem Statement

**Who**: Tech Leads, PMs, Architects, and DevOps Engineers using Pilot Space for Enterprise SDLC workflows.

**Problem**: The Note Editor currently supports only basic text blocks (paragraphs, headings, lists, code, tables, task checkboxes). Enterprise SDLC teams need structured PM artifacts — diagrams, risk registers, responsibility matrices, decision records, forms, and dashboards — but must create these in external tools (Lucidchart, Google Forms, Jira, Miro), breaking the "Note-First" workflow and losing AI context.

**Impact**: Teams spend 30-40% of planning time context-switching between tools. The AI agent cannot generate or reason about structured PM artifacts. Sprint planning, architecture decisions, and release readiness reviews happen outside Pilot Space, making the platform incomplete for Enterprise SDLC adoption.

**Success**: A PM or Tech Lead can conduct an entire sprint planning session, architecture decision review, or release readiness assessment within a single note — with the AI Agent proactively generating diagrams, checklists, decision blocks, and dashboards based on conversational context. All artifacts are live, interactive, and queryable across notes.

---

## Stakeholders

| Stakeholder | Role | Interest | Input Needed | Review Point |
|-------------|------|----------|-------------|-------------|
| Tin Dang | Architect / PO | Full SDLC coverage, AI integration quality | Architecture decisions, approval flow design | Spec + Plan review |
| Tech Lead (User) | Primary User | Sprint planning efficiency, decision tracking | Workflow validation, usability feedback | Acceptance test |
| PM (User) | Primary User | Risk tracking, status reporting, cross-note aggregation | Template validation, reporting needs | Scenario review |
| DevOps Lead | Secondary User | Release readiness, deployment checklists | Deployment workflow validation | Pre-release review |

---

## Phasing Strategy

Each phase targets a single-sprint scope (~3,000-4,000 LOC including tests). Phases are independently shippable — each delivers user value without requiring subsequent phases.

### Phase 1 — Declarative Diagram Block (P1)
Text-based diagram rendering with live preview. Agent auto-generates from conversation context.

### Phase 2 — Smart Checklist + Decision Record (P2)
Structured checklist with per-item metadata. Single-user decision tracking with rationale.

### Phase 3 — Structured Data Collection (P3)
Form/Survey blocks, RACI Matrix, Risk Register. Requires Phase 2 block infrastructure.

### Phase 4 — Interactive Visualization & Analytics (P4)
Custom data visualizations, timeline tracking, KPI dashboards, cross-note aggregation. Requires Phase 3 form metadata extraction.

### Prerequisites (Before Phase 1)

- **PRE-001**: Refactor editor canvas component to support block-type plugin registry without exceeding 700-line file size limit. Current canvas is at 702 lines.
- **PRE-002**: Document extension loading order constraints for new block-type extensions.
- **PRE-003**: Extend content update handler to support new operation types beyond current 5 (replace_block, append_blocks, insert_blocks, remove_block, insert_inline_issue).

---

## User Scenarios & Testing

### US-001 — Declarative Diagram Block (Priority: P1)

A user is discussing system architecture with the AI Agent in a note. The Agent analyzes the conversation and proactively inserts a diagram (flowchart, sequence diagram, Gantt chart, class diagram, ER diagram, state diagram, or C4 diagram) directly into the note. The diagram renders as a live, interactive vector graphic. The user can click "Edit Source" to modify the diagram definition directly. The user can also insert diagrams manually via `/diagram` slash command.

**Why P1**: Diagrams are the most requested PM artifact. Text-based diagram definitions are AI-native (easy to generate), and support all diagram types needed for SDLC documentation.

**Independent Test**: Insert `/diagram` in an empty note, type a flowchart definition, verify it renders correctly. Ask AI "draw a sequence diagram for the login flow" and verify auto-insertion.

**Acceptance Scenarios**:

1. **Given** a note with ongoing architecture discussion, **When** the Agent detects architecture-related content, **Then** it auto-inserts a relevant diagram with undo available.
2. **Given** a user types `/diagram` in the editor, **Then** a diagram editing area appears with syntax highlighting, live preview panel, and diagram type selector dropdown.
3. **Given** a diagram block with invalid syntax, **When** the user edits the source, **Then** an inline error message appears below the block with the specific parse error, and the last valid render is preserved.
4. **Given** a rendered diagram, **When** the user clicks a node/entity, **Then** a tooltip shows the node label and offers "Link to Issue" action.
5. **Given** a rendered diagram, **When** the user clicks "Export Image", **Then** the diagram is exported as a static image file.
6. **Given** a diagram block on a mobile device, **Then** the diagram renders in a read-only view with pinch-to-zoom. Source editing is disabled with "Edit on Desktop" message.
7. **Given** a diagram block, **When** the user copies and pastes it into another note, **Then** the source definition is preserved but the block gets a new unique ID.

**Supported Diagram Types** (10):
- Flowchart (directed graph, top-down or left-right)
- Sequence Diagram
- Gantt Chart
- Class Diagram
- ER Diagram (Entity Relationship)
- State Diagram
- C4 Diagram (Context, Container, Component)
- Pie Chart
- Mindmap
- Git Graph

**Size Limits**: Maximum 500 lines of source definition or 200 nodes/entities. Exceeding this displays "Diagram too complex — showing source only" fallback.

---

### US-002 — Smart Checklist Block (Priority: P2)

A PM is planning a sprint in a note. The Agent generates a smart checklist with items that have assignees, due dates, priority levels, and optional/required flags. Items can be nested (subtasks). Progress is tracked visually (progress bar). The checklist supports conditional items (shown only if a parent item is checked). The Agent auto-populates checklists from sprint planning context, definition of done, or release readiness criteria.

**Why P2**: Checklists are the backbone of PM workflows. The existing task list (basic checkboxes) lacks assignees, dates, priorities, and progress tracking — all essential for Enterprise SDLC.

**Independent Test**: Insert `/checklist` in a note, add items with assignees and dates, verify progress bar updates. Ask AI "create a definition of done checklist" and verify structured output.

**Acceptance Scenarios**:

1. **Given** a sprint planning discussion, **When** the Agent detects task decomposition, **Then** it auto-inserts a Smart Checklist with items, assignees (if mentioned), estimated effort, and priority flags.
2. **Given** a Smart Checklist block, **When** the user checks/unchecks items, **Then** the progress bar updates in real-time and auto-save triggers within 2 seconds.
3. **Given** a checklist item marked as "optional", **Then** it displays with a dashed border and does not count toward the progress percentage.
4. **Given** a checklist item with a conditional dependency (e.g., "only if deploy to staging passes"), **When** the parent item is unchecked, **Then** the conditional child is greyed out and non-interactive.
5. **Given** a Smart Checklist, **When** the user clicks an item's assignee avatar, **Then** a member picker dropdown appears (workspace members).
6. **Given** a checklist with due dates, **When** an item is overdue, **Then** the date badge turns red and the item shows an overdue indicator.
7. **Given** a Smart Checklist on a mobile device, **Then** items are fully interactive (check/uncheck, swipe for actions). Assignee and date pickers use native mobile controls.
8. **Given** a Smart Checklist, **When** the user presses keyboard arrows to navigate items and Space to toggle, **Then** full keyboard navigation works without a mouse.
9. **Given** a Smart Checklist, **When** the user copies and pastes it to another note, **Then** item text and structure are preserved but assignee references are cleared (may not exist in target context).
10. **Given** a Smart Checklist in a read-only note, **Then** items display with current state but check/uncheck, assignee, and date pickers are disabled.

**Checklist Item Attributes**:
- Text content (rich text inline — bold, code, links)
- Checked/unchecked state
- Assignee (workspace member ID, optional)
- Due date (optional)
- Priority: none | low | medium | high | urgent
- Required/Optional flag
- Estimated effort (story points or hours, optional)
- Nested children (max 5 levels deep, max 200 total items per checklist)
- Conditional parent ID (optional — item only active when parent is checked)

---

### US-003 — Decision Record Block (Priority: P2)

An Architect is documenting an architecture decision in a note. The Agent proactively inserts a Decision Record when it detects decision-related language ("should we use X or Y?", "decision: ", "ADR:"). The block captures the decision title, options (binary Yes/No or multi-option), rationale per option, and the owner's final decision with reasoning. This is a **single-user decision tracking** tool — the note owner records their decision and rationale. Multi-stakeholder voting is a future collaboration feature.

**Why P2**: Architecture Decision Records (ADRs) and go/no-go gates are core Enterprise SDLC artifacts. Current workflow forces these into external docs, breaking Note-First.

**Independent Test**: Insert `/decision` in a note, fill in title and options, record decision, verify status transitions. Ask AI "should we use Redis or Memcached for caching?" and verify Decision Record auto-insertion.

**Acceptance Scenarios**:

1. **Given** a note with decision-related content, **When** the Agent detects decision language, **Then** it auto-inserts a Decision Record pre-populated with options extracted from context.
2. **Given** a Decision Record in "Open" status, **When** the owner fills in rationale and clicks "Decide", **Then** the status changes to "Decided" with timestamp and selected option highlighted.
3. **Given** a Decision Record in "Decided" status, **Then** the block shows a summary banner with the decision outcome. The block is still editable (for amendments).
4. **Given** a decided Decision Record, **When** the user clicks "Create Issue", **Then** a linked issue is created with the decision context as description.
5. **Given** a multi-option Decision Record (e.g., 3 alternatives), **Then** each option shows a pros/cons section, effort estimate field, and risk indicator.
6. **Given** a Decision Record, **When** the user clicks "Supersede", **Then** the status changes to "Superseded" with a link field for the new decision.
7. **Given** a Decision Record on a mobile device, **Then** options display in a stacked vertical layout instead of side-by-side columns.
8. **Given** a Decision Record in a read-only note, **Then** the decision and rationale are visible but no editing or status changes are allowed.
9. **Given** a Decision Record, **When** exported to a document, **Then** it renders as a structured text section: title, status, options with pros/cons, and selected decision.

**Decision Record States**: Open → Decided → Superseded

**Decision Record Attributes**:
- Title
- Description/context
- Type: binary (Yes/No) | multi-option (max 6 options)
- Options (each with: label, description, pros, cons, effort estimate, risk level)
- Status: open | decided | superseded
- Final decision (selected option)
- Decision rationale (free text)
- Decision date
- Linked issue IDs
- Amendment notes (post-decision changes)
- Superseded-by reference (optional — links to new Decision Record)

---

### US-004 — Form/Survey Block (Priority: P3)

A Scrum Master is running a sprint retrospective. The Agent generates a Form Block with structured fields: "What went well?" (text area), "What needs improvement?" (text area), "Action item owner" (member dropdown), "Satisfaction score" (1-5 rating), "Priority for next sprint" (dropdown). The note owner fills out the form. Responses are stored within the document format for rendering, with lightweight metadata extracted for future cross-note aggregation.

**Why P3**: Forms enable structured data collection within notes. Critical for retros, risk assessments, status reports, and stakeholder surveys.

**Independent Test**: Insert `/form` in a note, add fields of various types, fill in responses, verify data persists across page reloads.

**Acceptance Scenarios**:

1. **Given** a retrospective discussion, **When** the Agent detects retro-related content, **Then** it auto-inserts a Form Block with relevant fields (went-well, improve, action-items).
2. **Given** a Form Block with a dropdown field, **When** the user clicks the field, **Then** a dropdown with pre-defined options appears.
3. **Given** a Form Block with a rating field (1-5), **Then** it renders as clickable stars or number pills.
4. **Given** a Form Block with a required field left empty, **When** the user navigates away from the field, **Then** the field is highlighted with validation message.
5. **Given** a Form Block on a mobile device, **Then** form fields use native mobile input controls (date picker, dropdown, keyboard types).
6. **Given** a Form Block in a read-only note, **Then** filled responses are visible but fields are non-editable.
7. **Given** a Form Block, **When** exported to a document, **Then** it renders as a structured list of field labels and values.

**Supported Field Types** (10):
- Short text (single line)
- Long text (multi-line, rich text)
- Dropdown (single select, max 20 options)
- Multi-select (tags, max 10 selections)
- Date picker
- Rating (1-5 stars)
- Number input (with optional min/max)
- Member picker (workspace member)
- Yes/No toggle
- File attachment reference

**Size Limits**: Maximum 30 fields per form. Maximum 20 options per dropdown.

---

### US-005 — RACI Matrix Block (Priority: P3)

A Tech Lead is assigning responsibilities for a feature rollout. The Agent auto-generates a RACI matrix from the task breakdown in the note. The matrix shows deliverables (rows) vs. stakeholders (columns) with clickable R/A/C/I cells. Each row must have exactly one "A" (Accountable). The Agent validates RACI constraints in real-time.

**Why P3**: RACI is a standard PM artifact for stakeholder alignment. Manual creation is tedious and error-prone. AI-generated RACI from existing task context is a significant productivity gain.

**Independent Test**: Insert `/raci` in a note, add deliverables and stakeholders, assign roles, verify constraint validation (exactly one A per row).

**Acceptance Scenarios**:

1. **Given** a note with task decomposition, **When** the user asks "generate a RACI matrix", **Then** the Agent creates a RACI Block with deliverables from the checklist and stakeholders from mentioned team members.
2. **Given** a RACI Block, **When** the user clicks a cell, **Then** a dropdown shows R/A/C/I/empty options.
3. **Given** a RACI row with zero "A" assignments, **Then** a warning indicator appears on that row.
4. **Given** a RACI row with more than one "A", **Then** an error indicator appears with message "Exactly one Accountable required per deliverable."
5. **Given** a completed RACI Block, **When** the user clicks "Export", **Then** the matrix is exportable as a table or comma-separated format.
6. **Given** a RACI Block on a mobile device, **Then** the matrix scrolls horizontally with sticky first column (deliverable names).
7. **Given** a RACI Block, **When** a referenced workspace member is removed from the workspace, **Then** their column header shows "(removed)" with a greyed-out indicator.

**Size Limits**: Maximum 30 deliverables (rows) × 15 stakeholders (columns) = 450 cells.

---

### US-006 — Risk Register Block (Priority: P3)

A PM is conducting a risk assessment for a release. The Agent generates a Risk Register from context analysis — identifying technical risks, schedule risks, and dependency risks from the note content. Each risk has probability (1-5), impact (1-5), composite score, response strategy (Avoid/Mitigate/Transfer/Accept), owner, and trigger condition.

**Why P3**: Risk registers are mandatory in Enterprise SDLC. AI-generated risk identification from project context is a differentiator.

**Independent Test**: Insert `/risk-register` in a note, add risks manually, verify score calculation. Ask AI "identify risks for this release" and verify auto-populated register.

**Acceptance Scenarios**:

1. **Given** a release planning note, **When** the Agent is asked to identify risks, **Then** it generates a Risk Register Block with categorized risks (technical, schedule, resource, dependency) and pre-filled probability/impact scores.
2. **Given** a Risk Register Block, **When** the user changes probability or impact, **Then** the composite score updates automatically and the row color changes (green: score < 6, yellow: 6-14, red: ≥ 15).
3. **Given** a risk with score ≥ 15, **Then** the Agent proactively suggests a mitigation strategy via margin annotation.
4. **Given** a Risk Register on a mobile device, **Then** rows stack vertically (card layout) instead of horizontal table.

**Size Limits**: Maximum 50 risks per register.

---

### US-007 — Custom Data Visualization Block (Priority: P4)

An Architect needs a force-directed dependency graph of the project's modules. The Agent generates visualization code that renders in an isolated execution environment within the note. Supports: bar/line/area/pie charts, force-directed graphs, treemaps, hierarchies, and custom vector rendering.

**Why P4**: Custom visualizations provide maximum flexibility beyond declarative diagram syntax. Essential for PM dashboards, dependency graphs, and codebase visualizations.

**Independent Test**: Insert `/chart` in a note, select chart type, provide data, verify render. Ask AI "show me a burndown chart for this sprint" and verify visualization.

**Acceptance Scenarios**:

1. **Given** a sprint in progress, **When** the Agent is asked for a burndown chart, **Then** it generates a line chart block with sprint data from the active cycle.
2. **Given** a visualization block with code, **Then** the visualization renders in an isolated container (no access to parent page, no network calls, no local storage).
3. **Given** a visualization block, **When** the user clicks "Edit Data", **Then** a data editor panel appears for modifying the data source.
4. **Given** a force-directed graph, **When** the user drags a node, **Then** the graph rebalances with physics simulation. Keyboard alternative: focus node + arrow keys to reposition.
5. **Given** a treemap visualization, **When** the user clicks a segment, **Then** it zooms into that segment's children.
6. **Given** a visualization block on a mobile device, **Then** interactive features (drag, zoom) use touch gestures. Non-interactive fallback renders a static image.
7. **Given** a visualization block, **When** exported to a document, **Then** it renders as a static image captured at export time.

**Supported Visualization Types** (8):
- Bar chart (vertical/horizontal, grouped, stacked)
- Line chart (single/multi-series, with trend lines)
- Area chart (stacked, streamgraph)
- Pie/Donut chart
- Force-directed graph (nodes + edges, drag interaction)
- Treemap (hierarchical area, zoomable)
- Hierarchy tree (collapsible tree layout)
- Custom vector rendering (full rendering pipeline, isolated execution)

**Security**: Visualization code MUST execute in an isolated environment with no parent page access, no network calls, no storage access. Data is passed via message protocol. Agent-generated code is validated for common injection patterns before execution. Execution timeout: 5 seconds.

**Size Limits**: Maximum 5,000 data points per visualization. Maximum 200 nodes for force-directed graphs.

---

### US-008 — Timeline/Milestone Block (Priority: P4)

A PM is tracking a release across multiple sprints. The Agent generates a Timeline Block showing milestones with dates, status indicators (on-track/at-risk/blocked), and dependency arrows. The timeline is interactive — milestones can be repositioned to reschedule.

**Why P4**: Visual timeline is the bridge between textual planning and visual PM. Especially valuable for multi-sprint release tracking.

**Independent Test**: Insert `/timeline` in a note, add milestones with dates and statuses, verify visual rendering and reschedule interaction.

**Acceptance Scenarios**:

1. **Given** a release planning note, **When** the Agent detects milestone references, **Then** it auto-inserts a Timeline Block with milestones and dates.
2. **Given** a Timeline Block, **When** the user repositions a milestone to a new date, **Then** the date updates and dependent milestones shift accordingly. Keyboard alternative: focus milestone + Ctrl+Arrow to shift by 1 day.
3. **Given** a milestone with status "blocked", **Then** it renders with a red border and block indicator.
4. **Given** a Timeline Block, **When** two milestones have a dependency, **Then** an arrow connects them visually.
5. **Given** a Timeline Block on a mobile device, **Then** the timeline scrolls horizontally with swipe. Repositioning disabled with "Edit on Desktop" note.

**Size Limits**: Maximum 30 milestones per timeline.

---

### US-009 — Metrics/KPI Dashboard Block (Priority: P4)

A Tech Lead wants to embed a live sprint metrics dashboard in a planning note. The Agent generates a KPI Dashboard Block with mini-charts pulling from the workspace's cycle data (burndown, velocity, SPI, CPI gauges). The dashboard updates automatically when cycle data changes.

**Why P4**: Contextual metrics within planning notes eliminate the need to switch to a separate dashboard. AI can reference these metrics during conversation.

**Independent Test**: Insert `/dashboard` in a note, select metrics to display, verify data loads from active cycle.

**Acceptance Scenarios**:

1. **Given** a sprint planning note, **When** the Agent is asked "show sprint metrics", **Then** it inserts a KPI Dashboard Block with burndown, velocity, and SPI/CPI gauges.
2. **Given** a KPI Dashboard Block, **When** the active cycle's data changes (issue completed), **Then** the dashboard reflects the update within 30 seconds.
3. **Given** a KPI Dashboard with SPI < 0.9, **Then** the gauge renders in red with a warning label.
4. **Given** a KPI Dashboard in a read-only note, **Then** metrics display with current values but configuration is locked.
5. **Given** a KPI Dashboard on a mobile device, **Then** widgets stack vertically in a single column.

---

### US-010 — Cross-Note Form Aggregation (Priority: P4)

A PM has conducted 4 sprint retrospectives, each in a separate note with Form Blocks. The PM asks the Agent "summarize retro trends across the last 4 sprints". The Agent reads form data from each note's stored content, aggregates responses, and generates a summary report with trend analysis.

**Why P4**: Cross-note aggregation transforms Pilot Space from a note-taking tool into a lightweight PM intelligence platform.

**Independent Test**: Create 3 notes with identical form templates, fill in different responses, ask Agent to aggregate, verify summary accuracy.

**Acceptance Scenarios**:

1. **Given** 4 notes with retro Form Blocks, **When** the user asks "aggregate retro trends", **Then** the Agent produces a summary with: common themes, satisfaction score trends, recurring action items.
2. **Given** form responses across notes, **When** aggregated, **Then** the Agent generates a visualization block showing metric changes over time (requires Phase 4 visualization blocks).
3. **Given** a form field of type "rating", **When** aggregated across notes, **Then** the Agent computes mean, median, and trend direction (improving/declining/stable).

**Data Access Strategy**: The Agent reads note content (which contains form data in the stored format) via existing MCP note content tools. No separate database table required for MVP aggregation. For scale beyond 50 notes, a lightweight metadata index SHOULD be introduced (future optimization, not blocking Phase 4).

---

### Edge Cases

**Rendering & Display**:
- What happens when a diagram exceeds 500 lines or 200 nodes? → Render limit with "Diagram too complex" message and "Show Source Only" fallback.
- What happens when visualization code enters an infinite loop? → Isolated execution environment with 5-second timeout, terminated with error message.
- What happens when a PM block is viewed on a mobile device? → Diagram: read-only with pinch-zoom. Checklist: fully interactive with native controls. Decision: stacked vertical layout. RACI/Risk: card layout or horizontal scroll. Visualization: static image fallback.
- What happens when a PM block is rendered in light vs dark theme? → All blocks MUST respect theme variables. Diagrams adapt colors to current theme.

**Data Integrity**:
- What happens when two users edit the same checklist item simultaneously? → Last-write-wins with auto-save conflict detection (existing pattern). If conflict detected on reload, yellow border with "Updated by another user — reload to sync."
- What happens when a checklist assignee is removed from the workspace? → Assignee shown as "(removed)" with greyed-out avatar.
- What happens when a risk register's trigger condition references a deleted issue? → Show "(deleted issue)" placeholder with warning icon.
- What happens when a user copies a PM block to another note? → Diagram: source preserved, new block ID. Checklist: items and text preserved, assignee references cleared. Decision: content preserved, linked issue IDs cleared. Form: field schema preserved, responses cleared.

**Export & Read-Only**:
- What happens when a note with PM blocks is exported to a document? → Diagrams: static image. Checklists: formatted list with status indicators. Decisions: structured text section. Forms: label-value pairs. Visualizations: static image captured at export time. RACI: formatted table. Risk Register: formatted table with color indicators as text labels.
- What happens when a guest user (read-only access) views a PM block? → All blocks display current state but interactive elements (checkboxes, dropdowns, date pickers, status buttons) are disabled.

**Agent Behavior**:
- What happens when the Agent inserts the wrong PM block type? → User can undo (Ctrl+Z). No cross-block type conversion supported. Agent learns from undo patterns to improve trigger accuracy.
- What happens when a PM template inserts 5 blocks at once? → All blocks in a template insertion are grouped as a single undo operation. One Ctrl+Z removes the entire template.
- What happens when the Agent tries to modify a PM block after the user has edited it? → Agent MUST NOT modify PM blocks that the user has manually edited (edit guard). Agent generates new blocks for revisions instead.
- What happens when a Decision Record has been "Open" for more than 7 days? → Agent proactively reminds via margin annotation "Decision pending for 7+ days — consider deciding or archiving."

**Offline & Connectivity**:
- What happens when the user edits a Smart Checklist while offline? → Check/uncheck and text editing work offline. Assignee picker shows cached member list (may be stale). Changes sync on reconnect with conflict detection.

**Size Limits Summary**:

| Block Type | Limit |
|-----------|-------|
| Diagram | 500 lines or 200 nodes |
| Smart Checklist | 200 items, 5 nesting levels |
| Decision Record | 6 options |
| Form | 30 fields, 20 options per dropdown |
| RACI Matrix | 30 rows × 15 columns |
| Risk Register | 50 risks |
| Visualization | 5,000 data points, 200 graph nodes |
| Timeline | 30 milestones |

---

## Requirements

### Functional Requirements

**Phase 1 — Declarative Diagram Block**

- **FR-001**: System MUST render text-based diagram definitions as interactive vector graphics within the note editor.
- **FR-002**: System MUST support 10 diagram types: flowchart, sequence, Gantt, class, ER, state, C4, pie, mindmap, and git graph.
- **FR-003**: Rendered diagrams MUST be interactive — users can click nodes to see tooltips and link nodes to issues.
- **FR-004**: System MUST provide a live preview panel alongside the diagram source editor.
- **FR-005**: System MUST validate diagram syntax in real-time and display inline error messages (not toast notifications).
- **FR-006**: System MUST preserve the last valid render when syntax errors are introduced.
- **FR-007**: The AI Agent MUST proactively insert diagram blocks when architecture-related content is detected, without requiring explicit user commands.
- **FR-008**: All PM blocks MUST support undo (Ctrl+Z) immediately after Agent auto-insertion.
- **FR-009**: All PM blocks MUST persist as custom node types in the document's structured format, compatible with the existing auto-save pipeline (2-second debounce).
- **FR-010**: System MUST provide a `/diagram` slash command for manual block insertion with a diagram type selector.
- **FR-011**: Diagram blocks MUST render in read-only mode on mobile devices with pinch-to-zoom support.
- **FR-012**: Diagram blocks MUST be exportable as static images for document export.

**Phase 2 — Smart Checklist + Decision Record**

- **FR-013**: System MUST support Smart Checklist blocks with structured items.
- **FR-014**: Checklist items MUST support assignee assignment from workspace members.
- **FR-015**: Checklist items MUST support due dates with overdue indicators.
- **FR-016**: Checklist items MUST support priority levels (none, low, medium, high, urgent).
- **FR-017**: Checklist items MUST support a required/optional flag where optional items are excluded from progress calculations.
- **FR-018**: Checklist items MUST support conditional visibility based on parent item checked state.
- **FR-019**: Smart Checklist MUST display a progress bar reflecting checked-item percentage (excluding optional items from denominator).
- **FR-020**: System MUST support Decision Record blocks with a state machine (Open → Decided → Superseded).
- **FR-021**: Decision Record MUST support binary (Yes/No) and multi-option modes (max 6 options).
- **FR-022**: Decision options MUST support structured comparison fields: pros, cons, effort estimate, and risk level.
- **FR-023**: Decision Record MUST record the owner's decision with rationale and timestamp.
- **FR-024**: Decided Decision Records MUST support "Create Issue" action that links the new issue to the decision context.
- **FR-025**: Agent MUST proactively insert checklist blocks on task decomposition and decision blocks on decision-related language.
- **FR-026**: System MUST provide `/checklist` and `/decision` slash commands for manual insertion.

**Phase 3 — Structured Data Collection**

- **FR-027**: System MUST support Form/Survey blocks with typed input fields.
- **FR-028**: System MUST support 10 field types: short text, long text, dropdown, multi-select, date, rating, number, member picker, toggle, and file reference.
- **FR-029**: Form Block MUST validate required fields and display inline validation messages.
- **FR-030**: System MUST support RACI Matrix blocks with deliverable rows and stakeholder columns.
- **FR-031**: RACI Matrix MUST validate that each row has exactly one "Accountable" assignment.
- **FR-032**: System MUST support Risk Register blocks with probability (1-5), impact (1-5), auto-calculated composite score, response strategy, owner, and trigger condition.
- **FR-033**: Risk Register rows MUST be color-coded by severity (green: score < 6, yellow: 6-14, red: ≥ 15).
- **FR-034**: Agent MUST proactively insert form, RACI, and risk register blocks based on conversational context.
- **FR-035**: System MUST provide `/form`, `/raci`, and `/risk-register` slash commands.

**Phase 4 — Interactive Visualization & Analytics**

- **FR-036**: System MUST support custom data visualization blocks with 8 types: bar, line, area, pie, force-directed graph, treemap, hierarchy tree, and custom vector rendering.
- **FR-037**: Visualization code MUST execute in an isolated environment with no parent page access, no network, no storage, and a 5-second execution timeout.
- **FR-038**: Interactive visualizations (drag, zoom) MUST have keyboard alternatives (focus + arrow keys).
- **FR-039**: System MUST support Timeline/Milestone blocks with visual dependency arrows and reposition-to-reschedule interaction.
- **FR-040**: Timeline repositioning MUST have a keyboard alternative (Ctrl+Arrow to shift by 1 day).
- **FR-041**: System MUST support KPI Dashboard blocks with live data from workspace cycles, auto-refreshing within 30 seconds.
- **FR-042**: System MUST support cross-note form aggregation where the Agent reads form data from multiple notes and generates summary reports with trend analysis.
- **FR-043**: Agent MUST provide `/chart`, `/timeline`, and `/dashboard` slash commands.

**Cross-Cutting**

- **FR-044**: All PM blocks MUST preserve block IDs through editing operations, compatible with the existing block identification system.
- **FR-045**: New PM block extensions MUST load before the block identification extension in the extension pipeline.
- **FR-046**: All PM blocks MUST be serializable to and from a text format for the Agent's content pipeline.
- **FR-047**: Agent auto-inserted blocks MUST follow DD-003 approval policy: auto-insert with undo (non-destructive additive operations).
- **FR-048**: The Agent MUST NOT modify PM blocks that the user has manually edited. Agent generates new blocks for revisions instead.
- **FR-049**: All PM blocks MUST be keyboard navigable (WCAG 2.2 AA).
- **FR-050**: All PM blocks MUST be compatible with screen readers, including announcing block type and current state (WCAG 2.2 AA).
- **FR-051**: All PM blocks MUST render correctly in high contrast mode (WCAG 2.2 AA).
- **FR-052**: All PM blocks MUST render correctly in both light and dark themes.
- **FR-053**: All PM blocks MUST have defined behavior in read-only mode (display state, disable interactions).
- **FR-054**: All PM blocks MUST define copy/paste behavior (what transfers, what resets).
- **FR-055**: All PM blocks MUST define export behavior (how they render in document export).
- **FR-056**: System SHOULD support block-to-block references (e.g., Decision Record linking to Risk Register entries). When a referenced block is deleted, the reference MUST show "(deleted)" placeholder.
- **FR-057**: Template insertions (multiple PM blocks at once) MUST be grouped as a single undo operation.

### Key Entities

- **DiagramBlock**: A block containing text-based diagram source code and rendered vector output. Key attributes: diagramType, sourceCode, renderStatus, lastValidRender. Relationships: parent Note via blockId.
- **SmartChecklistBlock**: A block containing structured checklist items. Key attributes: items (nested tree), progressPercentage, templateId. Relationships: items reference workspace Members (assignee), parent Note.
- **ChecklistItem**: An individual item within a SmartChecklist. Key attributes: text, checked, assignee, dueDate, priority, isOptional, estimatedEffort, conditionalParentId. Relationships: parent SmartChecklistBlock, optional assignee Member.
- **DecisionRecordBlock**: A structured decision record (single-user). Key attributes: title, description, type (binary/multi-option), options, status, finalDecision, decisionRationale, decisionDate. Relationships: parent Note, linked Issues.
- **FormBlock**: A structured form with typed fields and responses. Key attributes: fields (schema), responses (data), templateId. Relationships: parent Note.
- **RACIMatrixBlock**: A responsibility assignment matrix. Key attributes: deliverables (rows), stakeholders (columns), assignments (R/A/C/I cells). Relationships: parent Note, referenced workspace Members.
- **RiskRegisterBlock**: A risk tracking table. Key attributes: risks (rows with probability, impact, score, strategy, owner, trigger). Relationships: parent Note, owner Members, linked Issues.
- **VisualizationBlock**: A custom data visualization container. Key attributes: chartType, dataSource (inline data or reference), code (rendering script), renderStatus. Relationships: parent Note.
- **TimelineBlock**: A visual milestone tracker. Key attributes: milestones (date, title, status, dependencies). Relationships: parent Note, linked Cycles.
- **KPIDashboardBlock**: A metrics dashboard. Key attributes: widgets (metric type, data source reference, display config). Relationships: parent Note, referenced Cycle.

---

## Enterprise SDLC Templates

Templates compose PM blocks from available phases. Each template is labeled with its earliest available phase.

### Phase 1 Templates

**T-001: Simple Architecture Diagram**
- Diagram block (C4 or flowchart of system architecture)
- Available immediately with Phase 1.

### Phase 2 Templates

**T-002: Sprint Planning**
- Diagram block — Gantt chart (sprint timeline)
- Smart Checklist — sprint backlog with assignees, estimates
- Smart Checklist — Definition of Done
- Decision Record — sprint goal confirmation

**T-003: Architecture Decision Record (ADR) — Lite**
- Decision Record — multi-option with alternatives comparison
- Diagram block — architecture before/after

### Phase 3 Templates

**T-004: Architecture Decision Record (ADR) — Full**
- Decision Record — multi-option with alternatives comparison
- Diagram block — architecture before/after
- Risk Register — technical risks of each option
- Form Block — stakeholder impact assessment

**T-005: Release Readiness Review**
- Smart Checklist — deployment checklist (migrations, feature flags, monitoring)
- Decision Record — Go/No-Go
- Risk Register — release risks
- Diagram block — deployment pipeline
- Form Block — rollback plan details

**T-006: Sprint Retrospective**
- Form Block — what went well, what needs improvement, satisfaction rating
- Smart Checklist — action items with owners and due dates
- Decision Record — process change proposals

**T-007: Project Kickoff**
- RACI Matrix — team responsibilities
- Diagram block — Gantt project timeline
- Risk Register — initial risk assessment
- Smart Checklist — kickoff action items

### Phase 4 Templates

**T-008: Work Breakdown Structure (WBS)**
- Visualization block — treemap (hierarchical task decomposition)
- Smart Checklist — work packages (max 40h each)
- Timeline Block — milestone schedule

**T-009: Sprint Retrospective — Enhanced**
- Form Block — what went well, what needs improvement, satisfaction rating
- Smart Checklist — action items with owners and due dates
- Decision Record — process change proposals
- Visualization block — velocity trend chart (from cycle data)
- Cross-note aggregation — trends across past retros

---

## Success Criteria

- **SC-001**: Users complete a full sprint planning session (goal, backlog, estimates, DoD) within a single note in under 15 minutes, without leaving Pilot Space.
- **SC-002**: Agent auto-insertion undo rate MUST be below 30% (indicates user acceptance of auto-inserted blocks).
- **SC-003**: Diagrams render within 500ms for diagrams with fewer than 100 nodes or 50 entities.
- **SC-004**: Custom visualizations render within 3 seconds for datasets under 1,000 data points (execution timeout: 5 seconds).
- **SC-005**: Smart Checklist operations (check/uncheck, assign, date change) persist via auto-save within 3 seconds.
- **SC-006**: Cross-note form aggregation produces results within 10 seconds for up to 50 notes (Agent reads note content sequentially).
- **SC-007**: All PM blocks pass WCAG 2.2 AA audit (Lighthouse accessibility score ≥ 95).
- **SC-008**: Visualization sandbox prevents any cross-origin access attempts (0 security violations in pen test).
- **SC-009**: PM block adoption reaches ≥20% of active workspace notes within 30 days of Phase 1 launch (baseline: task checkboxes in ~15% of notes).
- **SC-010**: All PM blocks render correctly on viewports ≥ 768px. Mobile (< 768px) renders in degraded mode with documented fallbacks per block type.

---

## Constitution Compliance

| Principle | Applies? | How Addressed |
|-----------|----------|--------------|
| I. AI-Human Collaboration | Yes | Agent-first insertion with undo. DD-003: auto-insert (non-destructive), undo available. Agent MUST NOT modify user-edited PM blocks (FR-048). |
| II. Note-First | Yes | All PM artifacts created and managed within notes. No external tool dependency. |
| III. Documentation-Third | Yes | PM blocks are self-documenting. Agent generates structured artifacts from conversation, not manual forms. |
| IV. Task-Centric | Yes | Each user story is independently testable. 4-phase delivery, each phase single-sprint scoped. |
| V. Collaboration | Yes | RACI Matrix and Form responses enable structured information capture. Multi-stakeholder voting deferred to future collaboration feature. |
| VI. Agile Integration | Yes | Sprint Planning, Retrospective, and Release Readiness templates align with Scrum/Kanban ceremonies. |
| VII. Notation Standards | Yes | Declarative diagrams (industry standard text-to-diagram), RACI (PMI standard), risk register (ISO 31000 aligned). |

---

## Validation Checklists

### Requirement Completeness

- [x] No `[NEEDS CLARIFICATION]` markers remain
- [x] Every user story has acceptance scenarios with Given/When/Then
- [x] Every story is independently testable and demo-able
- [x] Edge cases documented for each story (rendering, data integrity, export, agent behavior, offline, size limits)
- [x] All entities have defined relationships

### Specification Quality

- [x] Focus is WHAT/WHY, not HOW
- [x] No technology names in requirements (Mermaid, D3.js, ProseMirror, SVG, iframe, JSON, TipTap, postMessage — all removed)
- [x] Requirements use RFC 2119 keywords (MUST/SHOULD/MAY)
- [x] Success criteria are measurable with numbers/thresholds
- [x] Written for business stakeholders, not developers
- [x] One capability per FR line (no compound requirements — split from 28 to 57 FRs)

### Structural Integrity

- [x] Stories prioritized P1 through P4
- [x] Functional requirements numbered sequentially (FR-001 through FR-057)
- [x] Key entities identified with attributes and relationships
- [x] No duplicate or contradicting requirements
- [x] Problem statement clearly defines WHO/PROBLEM/IMPACT/SUCCESS
- [x] Prerequisites documented (PRE-001 through PRE-003)
- [x] Templates labeled with earliest available phase
- [x] Size limits defined for all block types
- [x] Mobile/tablet behavior specified per block type
- [x] Read-only mode specified per block type
- [x] Copy/paste behavior specified per block type
- [x] Export behavior specified per block type

### Constitution Gate

- [x] All applicable principles checked and addressed
- [x] No violations
- [x] Multi-stakeholder voting explicitly deferred (not a hidden prerequisite)

---

## Review Findings Addressed (v2.0)

| # | Finding | Severity | Resolution |
|---|---------|----------|------------|
| 1-3 | Technology names (Mermaid 43x, D3 17x, ProseMirror 7x) | CRITICAL | Replaced with descriptive terms throughout |
| 4 | NoteCanvas.tsx at 702 lines | CRITICAL | Added PRE-001 prerequisite |
| 5 | Phase 1 scope 9-13K LOC | CRITICAL | Slimmed to P1=Diagrams only (~3-4K LOC) |
| 6-7 | Template cross-phase deps + MUST violation | CRITICAL | Templates labeled by phase, split MUST/SHOULD |
| 8 | Decision Block voting needs multi-user | CRITICAL | Changed to single-user decision tracking |
| 9 | Form aggregation vs persistence contradiction | CRITICAL | Agent reads note content directly, no separate table for MVP |
| 10-13 | Missing edge cases (mobile, copy/paste, export, read-only) | CRITICAL | Added comprehensive edge case section |
| 14-16 | Tech leaks (SVG, iframe, JSON) | HIGH | Removed |
| 17-19 | Compound FRs (FR-001, FR-003, FR-005) | HIGH | Split from 28 FRs to 57 FRs |
| 20 | SC-002 unmeasurable "correct" | HIGH | Changed to undo rate metric |
| 21 | SC-004 vs FR-018 contradiction | HIGH | Aligned to 3s success / 5s timeout |
| 22-24 | Architecture constraints (extension order, optimistic updates, handlers) | HIGH | Added PRE-002, PRE-003, FR-045, FR-048 |
| 25 | Template T-002 needs Risk Register (P2) | HIGH | Split into ADR Lite (P2) and ADR Full (P3) |
| 26 | No keyboard alternatives for drag | HIGH | Added FR-038, FR-040 with keyboard alternatives |
| 27-31 | Minor tech leaks, compound FRs | MEDIUM | Fixed throughout |
| 32 | SC-003 200 lines unrealistic | MEDIUM | Changed to 100 nodes / 50 entities |
| 33 | SC-009 no baseline | MEDIUM | Added baseline (15% task checkbox adoption) |
| 34 | AI edit guard interaction | MEDIUM | Added FR-048 (Agent MUST NOT modify user-edited blocks) |
| 35-37 | Offline, block limits, undo depth | MEDIUM | Added edge cases, size limit table, FR-057 |
| 38 | Block reference integrity | LOW | Added to FR-056 |

---

## Next Phase

After this spec passes review:

1. **Resolve prerequisites** — PRE-001 (canvas refactor), PRE-002 (extension ordering), PRE-003 (content handler extension)
2. **Proceed to planning** — Use `template-plan.md` to create implementation plan for Phase 1 (Declarative Diagram Block)
3. **Research** — Evaluate text-to-diagram rendering libraries, custom node type patterns, diagram rendering performance
4. **Data model** — Design structured document schema for each block type
5. **Contracts** — Define MCP tool extensions for Agent block generation

# Requirements Validation Checklist — 013-pm-note-extensions

**Generated**: 2026-02-11
**Spec Version**: Draft v2.0 (4-phase, 57 FRs)
**Validator**: Tin Dang

---

## Prerequisites

### PRE-001: Canvas Refactoring
- [ ] Editor canvas component refactored below 700-line limit
- [ ] Block-type plugin registry extracted for extensibility

### PRE-002: Extension Loading Order
- [ ] Extension loading order constraints documented
- [ ] New PM block extensions confirmed to load before block identification extension

### PRE-003: Content Handler Extension
- [ ] Content update handler supports new operation types beyond current 5
- [ ] New PM block insert/update/remove operations registered

---

## Phase 1 — Declarative Diagram Block (P1)

### FR-001: Diagram Rendering
- [ ] Flowchart (directed graph TD/LR) renders correctly
- [ ] Sequence diagram renders correctly
- [ ] Gantt chart renders correctly
- [ ] Class diagram renders correctly
- [ ] ER diagram renders correctly
- [ ] State diagram renders correctly
- [ ] C4 diagram renders correctly
- [ ] Pie chart renders correctly
- [ ] Mindmap renders correctly
- [ ] Git graph renders correctly

### FR-002: 10 Diagram Types Supported
- [ ] All 10 diagram types listed in spec are available in type selector

### FR-003: Interactive Diagrams
- [ ] Node click shows tooltip with label
- [ ] "Link to Issue" action available on node click

### FR-004: Live Preview Panel
- [ ] Source editor with syntax highlighting
- [ ] Live preview panel alongside source editor
- [ ] Preview updates on keystroke

### FR-005: Inline Syntax Validation
- [ ] Syntax errors shown inline (not toast)
- [ ] Error message includes specific parse error

### FR-006: Last Valid Render Preservation
- [ ] Last valid render preserved when syntax errors are introduced

### FR-007: Agent Auto-Insertion (Diagrams)
- [ ] Agent detects architecture-related content
- [ ] Agent proactively inserts relevant diagram block
- [ ] Insertion is non-destructive (additive only)

### FR-008: Undo Support
- [ ] Ctrl+Z immediately after auto-insertion removes the block
- [ ] Undo works within editor history stack
- [ ] Multi-step undo preserves document integrity

### FR-009: Auto-Save Compatibility
- [ ] PM blocks serialize as custom node types in document format
- [ ] Auto-save triggers within 2s of block changes
- [ ] Block IDs preserved through save/reload cycle

### FR-010: Slash Command /diagram
- [ ] `/diagram` inserts diagram block
- [ ] Diagram type selector dropdown available
- [ ] Command appears in slash command menu with icon
- [ ] Command filterable by typing

### FR-011: Mobile Diagram Rendering
- [ ] Diagrams render in read-only mode on mobile
- [ ] Pinch-to-zoom supported
- [ ] Source editing disabled with "Edit on Desktop" message

### FR-012: Diagram Export
- [ ] Diagrams exportable as static images
- [ ] Export triggered via "Export Image" action

### Diagram Size Limits
- [ ] Maximum 500 lines of source definition enforced
- [ ] Maximum 200 nodes/entities enforced
- [ ] "Diagram too complex — showing source only" fallback displayed on limit exceed

### Diagram Rendering Performance
- [ ] Render time < 500ms for diagrams with < 100 nodes or 50 entities (SC-003)

---

## Phase 2 — Smart Checklist + Decision Record (P2)

### FR-013: Smart Checklist Block
- [ ] Checklist block renders with structured items
- [ ] Items support rich text inline (bold, code, links)
- [ ] Checked/unchecked state toggleable

### FR-014: Assignee Assignment
- [ ] Member picker dropdown appears on assignee click
- [ ] Workspace members listed in picker
- [ ] Assignee avatar displayed on item

### FR-015: Due Dates
- [ ] Date picker available on checklist items
- [ ] Overdue items show red date badge
- [ ] Overdue indicator visible

### FR-016: Priority Levels
- [ ] none/low/medium/high/urgent priority options available
- [ ] Priority visually distinguished per item

### FR-017: Required/Optional Flag
- [ ] Items can be flagged as required or optional
- [ ] Optional items display with dashed border
- [ ] Optional items excluded from progress percentage

### FR-018: Conditional Visibility
- [ ] Items support conditional parent dependency
- [ ] Conditional child greyed out when parent unchecked
- [ ] Conditional child non-interactive when parent unchecked

### FR-019: Progress Bar
- [ ] Progress bar displays checked-item percentage
- [ ] Optional items excluded from denominator
- [ ] Progress bar updates in real-time on check/uncheck
- [ ] 0% = empty, 100% = full, partial = proportional

### FR-020: Decision Record Block
- [ ] Decision Record renders with state machine
- [ ] States: Open -> Decided -> Superseded
- [ ] Status transitions work correctly

### FR-021: Binary and Multi-Option Modes
- [ ] Binary mode (Yes/No) works
- [ ] Multi-option mode (2-6 alternatives) works
- [ ] Maximum 6 options enforced

### FR-022: Option Comparison Fields
- [ ] Each option has pros section
- [ ] Each option has cons section
- [ ] Each option has effort estimate field
- [ ] Each option has risk level indicator

### FR-023: Decision Recording
- [ ] Owner can select final decision
- [ ] Rationale free text field available
- [ ] Timestamp recorded on decision
- [ ] Summary banner shows decision outcome in "Decided" status

### FR-024: Create Issue from Decision
- [ ] "Create Issue" action available on decided records
- [ ] Linked issue created with decision context as description
- [ ] Issue linked back to decision record

### FR-025: Agent Auto-Insertion (Checklists + Decisions)
- [ ] Agent detects task decomposition -> inserts Smart Checklist
- [ ] Agent detects decision language -> inserts Decision Record
- [ ] Agent pre-populates items/options from conversation context

### FR-026: Slash Commands /checklist and /decision
- [ ] `/checklist` inserts Smart Checklist block
- [ ] `/decision` inserts Decision Record block
- [ ] Commands appear in slash command menu with icons
- [ ] Commands filterable by typing

### Checklist Size Limits
- [ ] Maximum 200 items per checklist enforced
- [ ] Maximum 5 nesting levels enforced

### Checklist Mobile Behavior
- [ ] Items fully interactive on mobile (check/uncheck)
- [ ] Assignee and date pickers use native mobile controls

### Checklist Keyboard Navigation
- [ ] Arrow keys navigate items
- [ ] Space toggles check/uncheck
- [ ] Full keyboard navigation without mouse

### Checklist Copy/Paste
- [ ] Item text and structure preserved on paste
- [ ] Assignee references cleared on paste to another note

### Checklist Read-Only Mode
- [ ] Items display current state in read-only notes
- [ ] Check/uncheck, assignee, date pickers disabled

### Decision Record Mobile
- [ ] Options display in stacked vertical layout on mobile

### Decision Record Read-Only
- [ ] Decision and rationale visible in read-only notes
- [ ] Editing and status changes disabled

### Decision Record Export
- [ ] Exports as structured text: title, status, options, pros/cons, selected decision

### Decision Record Supersede
- [ ] "Supersede" action changes status to "Superseded"
- [ ] Link field for replacement decision

---

## Phase 3 — Structured Data Collection (P3)

### FR-027: Form/Survey Block
- [ ] Form block renders with typed input fields
- [ ] Responses stored within document format

### FR-028: 10 Field Types
- [ ] Short text (single line)
- [ ] Long text (multi-line, rich text)
- [ ] Dropdown (single select, max 20 options)
- [ ] Multi-select (tags, max 10 selections)
- [ ] Date picker
- [ ] Rating (1-5 stars or number pills)
- [ ] Number input (with optional min/max)
- [ ] Member picker (workspace member)
- [ ] Yes/No toggle
- [ ] File attachment reference

### FR-029: Form Validation
- [ ] Required fields validated
- [ ] Inline validation messages on field blur

### FR-030: RACI Matrix Block
- [ ] Matrix renders with deliverable rows and stakeholder columns
- [ ] Cell click shows R/A/C/I/empty dropdown

### FR-031: RACI Constraint Validation
- [ ] Warning indicator on rows with zero "A" assignments
- [ ] Error indicator on rows with more than one "A"
- [ ] Message "Exactly one Accountable required per deliverable" displayed

### FR-032: Risk Register Block
- [ ] Risk rows with probability (1-5) and impact (1-5)
- [ ] Composite score auto-calculated (probability x impact)
- [ ] Response strategy field (Avoid/Mitigate/Transfer/Accept)
- [ ] Owner field
- [ ] Trigger condition field

### FR-033: Risk Register Color Coding
- [ ] Green: score < 6
- [ ] Yellow: score 6-14
- [ ] Red: score >= 15
- [ ] Colors update dynamically on probability/impact change

### FR-034: Agent Auto-Insertion (Forms, RACI, Risk)
- [ ] Agent detects retro content -> inserts Form Block
- [ ] Agent detects responsibility assignment -> inserts RACI Block
- [ ] Agent detects risk discussion -> inserts Risk Register Block

### FR-035: Slash Commands /form, /raci, /risk-register
- [ ] `/form` inserts Form Block
- [ ] `/raci` inserts RACI Matrix Block
- [ ] `/risk-register` inserts Risk Register Block
- [ ] Commands appear in slash command menu with icons

### Form Size Limits
- [ ] Maximum 30 fields per form enforced
- [ ] Maximum 20 options per dropdown enforced

### Form Mobile Behavior
- [ ] Form fields use native mobile input controls

### Form Read-Only Mode
- [ ] Filled responses visible in read-only notes
- [ ] Fields non-editable

### Form Export
- [ ] Exports as structured list of field labels and values

### RACI Size Limits
- [ ] Maximum 30 deliverables x 15 stakeholders enforced

### RACI Mobile Behavior
- [ ] Matrix scrolls horizontally with sticky first column

### RACI Member Removal
- [ ] Removed member column shows "(removed)" with greyed-out indicator

### Risk Register Size Limits
- [ ] Maximum 50 risks per register enforced

### Risk Register Mobile Behavior
- [ ] Rows stack vertically (card layout) on mobile

### Risk Register Agent Suggestion
- [ ] Agent suggests mitigation for risks with score >= 15 via margin annotation

---

## Phase 4 — Interactive Visualization & Analytics (P4)

### FR-036: Custom Visualization Block (8 Types)
- [ ] Bar chart (vertical/horizontal, grouped, stacked)
- [ ] Line chart (single/multi-series, trend lines)
- [ ] Area chart (stacked, streamgraph)
- [ ] Pie/Donut chart
- [ ] Force-directed graph (nodes + edges, drag)
- [ ] Treemap (hierarchical area, zoomable)
- [ ] Hierarchy tree (collapsible tree layout)
- [ ] Custom vector rendering (full pipeline, isolated)

### FR-037: Visualization Sandboxing
- [ ] No parent page access
- [ ] No network calls
- [ ] No local storage access
- [ ] 5-second execution timeout enforced
- [ ] Agent-generated code validated for injection patterns

### FR-038: Keyboard Alternatives for Visualizations
- [ ] Force-directed graph: focus node + arrow keys to reposition
- [ ] Treemap: keyboard navigation to zoom segments

### FR-039: Timeline/Milestone Block
- [ ] Visual rendering with milestones
- [ ] Dependency arrows between milestones
- [ ] Reposition-to-reschedule interaction (drag milestone to new date)
- [ ] Dependent milestones shift accordingly

### FR-040: Timeline Keyboard Alternative
- [ ] Ctrl+Arrow shifts focused milestone by 1 day

### FR-041: KPI Dashboard Block
- [ ] Live data from workspace cycles
- [ ] Auto-refreshes within 30 seconds
- [ ] Burndown, velocity, SPI/CPI gauges supported
- [ ] SPI < 0.9 renders in red with warning label

### FR-042: Cross-Note Form Aggregation
- [ ] Agent reads form data from multiple notes via MCP tools
- [ ] Summary report generated with trend analysis
- [ ] Rating fields compute mean, median, trend direction
- [ ] Common themes identified across responses

### FR-043: Slash Commands /chart, /timeline, /dashboard
- [ ] `/chart` inserts visualization block with type selector
- [ ] `/timeline` inserts Timeline Block
- [ ] `/dashboard` inserts KPI Dashboard Block
- [ ] Commands appear in slash command menu with icons

### Visualization Size Limits
- [ ] Maximum 5,000 data points enforced
- [ ] Maximum 200 nodes for force-directed graphs enforced

### Visualization Mobile Behavior
- [ ] Touch gestures for interactive features (drag, zoom)
- [ ] Non-interactive fallback renders static image on mobile

### Visualization Export
- [ ] Exports as static image captured at export time

### Timeline Size Limits
- [ ] Maximum 30 milestones per timeline enforced

### Timeline Mobile Behavior
- [ ] Horizontal scroll with swipe
- [ ] Repositioning disabled with "Edit on Desktop" note

### KPI Dashboard Read-Only
- [ ] Metrics display with current values
- [ ] Configuration locked in read-only mode

### KPI Dashboard Mobile
- [ ] Widgets stack vertically in single column

### Cross-Note Aggregation Performance
- [ ] Results produced within 10 seconds for up to 50 notes (SC-006)

---

## Cross-Cutting Requirements

### FR-044: Block ID Preservation
- [ ] All PM blocks have stable blockIds
- [ ] IDs survive copy/paste, undo/redo, AI content updates

### FR-045: Extension Loading Order
- [ ] New PM block extensions load before block identification extension
- [ ] Extension pipeline order validated in tests

### FR-046: Text Serialization
- [ ] All PM blocks serializable to text format for Agent content pipeline
- [ ] Agent can generate blocks via text in content_update pipeline

### FR-047: DD-003 Compliance
- [ ] Auto-insert (non-destructive) — no approval modal
- [ ] Undo available immediately after agent insertion

### FR-048: Agent Edit Guard
- [ ] Agent MUST NOT modify PM blocks that user has manually edited
- [ ] Agent generates new blocks for revisions instead

### FR-049: Keyboard Navigation (WCAG 2.2 AA)
- [ ] All blocks keyboard navigable (Tab, Enter, Escape, Arrow keys)
- [ ] Focus management on block insertion

### FR-050: Screen Reader Support (WCAG 2.2 AA)
- [ ] Screen reader announces block type
- [ ] Screen reader announces current block state

### FR-051: High Contrast Mode (WCAG 2.2 AA)
- [ ] 4.5:1 contrast ratios maintained in all blocks

### FR-052: Theme Support
- [ ] Light theme renders correctly
- [ ] Dark theme renders correctly
- [ ] Diagrams adapt colors to current theme

### FR-053: Read-Only Mode
- [ ] All blocks display current state in read-only mode
- [ ] All interactive elements disabled in read-only mode

### FR-054: Copy/Paste Behavior
- [ ] Diagram: source preserved, new block ID
- [ ] Checklist: items/text preserved, assignee references cleared
- [ ] Decision: content preserved, linked issue IDs cleared
- [ ] Form: field schema preserved, responses cleared

### FR-055: Export Behavior
- [ ] Diagrams: static image
- [ ] Checklists: formatted list with status indicators
- [ ] Decisions: structured text section
- [ ] Forms: label-value pairs
- [ ] Visualizations: static image
- [ ] RACI: formatted table
- [ ] Risk Register: formatted table with text color labels

### FR-056: Block-to-Block References
- [ ] Decision Record can reference Risk Register entries
- [ ] Checklist items can link to Decision outcomes
- [ ] Deleted block reference shows "(deleted)" placeholder

### FR-057: Template Undo Grouping
- [ ] Template insertions (multiple blocks) grouped as single undo operation
- [ ] One Ctrl+Z removes entire template

### Reduced Motion
- [ ] `prefers-reduced-motion` respected across all animated blocks

---

## Enterprise SDLC Templates

### T-001: Simple Architecture Diagram (P1)
- [ ] Agent generates diagram on architecture context
- [ ] C4 or flowchart included

### T-002: Sprint Planning (P2)
- [ ] Agent generates template on sprint planning context
- [ ] Gantt diagram + Checklist + DoD Checklist + Decision included

### T-003: ADR Lite (P2)
- [ ] Agent generates template on ADR context
- [ ] Decision Record + Diagram included

### T-004: ADR Full (P3)
- [ ] Extends T-003 with Risk Register + Form Block

### T-005: Release Readiness Review (P3)
- [ ] Checklist + Decision + Risk Register + Diagram + Form included

### T-006: Sprint Retrospective (P3)
- [ ] Form + Checklist + Decision included

### T-007: Project Kickoff (P3)
- [ ] RACI + Diagram + Risk Register + Checklist included

### T-008: Work Breakdown Structure (P4)
- [ ] Treemap visualization + Checklist + Timeline included

### T-009: Sprint Retrospective Enhanced (P4)
- [ ] Extends T-006 with velocity chart + cross-note aggregation

---

## Success Criteria Validation

- [ ] SC-001: Sprint planning in < 15 min (timed user test)
- [ ] SC-002: Agent auto-insertion undo rate < 30% (analytics tracking)
- [ ] SC-003: Diagram render < 500ms for < 100 nodes / 50 entities (performance test)
- [ ] SC-004: Visualization render < 3s for < 1,000 data points (performance test, 5s timeout)
- [ ] SC-005: Checklist auto-save < 3s (E2E test)
- [ ] SC-006: Cross-note aggregation < 10s for 50 notes (load test)
- [ ] SC-007: WCAG 2.2 AA score >= 95 (Lighthouse audit)
- [ ] SC-008: Visualization sandbox 0 violations (security pen test)
- [ ] SC-009: PM block adoption >= 20% of active notes in 30 days (baseline: 15% task checkbox adoption)
- [ ] SC-010: All PM blocks render correctly on viewports >= 768px; mobile degrades per documented fallbacks

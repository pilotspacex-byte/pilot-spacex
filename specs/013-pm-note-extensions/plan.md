# Implementation Plan: PM Note Extensions — Enterprise SDLC Block Types (Simplified)

**Feature**: PM Note Extensions (013)
**Branch**: `013-pm-note-extensions`
**Created**: 2026-02-11
**Revised**: 2026-02-11 (v2 — Simplified: enhance existing extensions)
**Spec**: `specs/013-pm-note-extensions/spec.md`
**Author**: Tin Dang

---

## Summary

Add PM block capabilities to the Note Editor by **enhancing 2 existing TipTap extensions** (CodeBlock, TaskList) and adding **1 generic PMBlock extension** with a renderer factory. This replaces the original 10-extension design with a 3-extension approach at ~40% of the effort.

**Key simplification**: Instead of 10 separate TipTap Node extensions, we categorize all PM blocks into 3 strategies:

| Strategy | Block Types | How |
|----------|-----------|-----|
| **Enhanced CodeBlock** | Diagrams (10 types), Visualizations (8 types) | Add Mermaid/ECharts preview decoration to existing `codeBlock` node when `language` matches `mermaid` or `echarts-*` |
| **Enhanced TaskList** | Smart Checklist | Extend existing `TaskItem` node with extra attrs (assignee, dueDate, priority, isOptional, conditionalParentId, estimatedEffort) |
| **Generic PMBlock** | Decision Record, Form, RACI Matrix, Risk Register, Timeline, KPI Dashboard | 1 new TipTap Node with `{blockType, data}` attrs + ReactNodeViewRenderer dispatching to type-specific renderers |

---

## Technical Context

| Attribute | Value |
|-----------|-------|
| **Language/Version** | TypeScript 5.3+, Python 3.12+ |
| **Primary Dependencies** | Next.js 14+, TipTap 3.16+, Mermaid.js 11+, Apache ECharts 5+ (P4 only) |
| **Storage** | PostgreSQL 16+ (TipTap JSON in `notes.content` JSONB column — no new tables) |
| **Testing** | Vitest + React Testing Library (frontend), pytest (backend) |
| **Performance Goals** | Diagram render < 500ms, viz render < 3s, auto-save < 3s |
| **Constraints** | 700-line file limit, RLS inherited from note, DD-003 approval, WCAG 2.2 AA |

---

## Constitution Gate Check

### Technology Standards Gate

- [x] Enhances existing TipTap extensions — no new framework dependencies
- [x] No new database tables — PM data stored in existing `notes.content` JSONB
- [x] Auth/RLS inherited — PM blocks are part of the note document
- [x] Pattern match: TipTap extension enhancement is established codebase pattern

### Simplicity Gate

- [x] 3 extensions (2 enhanced + 1 new) instead of 10 new
- [x] Zero new API endpoints — uses existing note CRUD + MCP tools
- [x] Zero new database tables or migrations
- [x] Agent uses existing `insert_block` MCP tool with markdown patterns

### Quality Gate

- [x] > 80% test coverage per renderer component
- [x] TypeScript strict, 700-line limit per file
- [x] Each renderer is a separate file (stays small)

---

## Research Decisions

| Question | Options | Decision | Rationale |
|----------|---------|----------|-----------|
| **RD-001**: Diagram engine | Mermaid.js 11, D2, PlantUML | **Mermaid.js 11** | All 10 diagram types (FR-002). AI-native text syntax. `securityLevel: 'strict'`. |
| **RD-002**: Diagram integration | (a) New DiagramBlock node, (b) Enhance CodeBlock with preview | **(b) Enhance CodeBlock** | Zero new node types. Detect `language: 'mermaid'` on codeBlock → render SVG preview above code. Toggle source/preview. Matches GitHub/GitLab Mermaid rendering pattern. |
| **RD-003**: Checklist integration | (a) New SmartChecklist node, (b) Extend TaskItem attrs | **(b) Extend TaskItem** | TipTap's TaskItem already has `checked` + text content. Use `TaskItem.extend()` to add assignee, dueDate, priority, isOptional, conditionalParentId attrs. Progress bar as wrapper decoration. |
| **RD-004**: Structured PM blocks | (a) Separate node per type, (b) Single PMBlock with renderer factory | **(b) Single PMBlock** | 1 extension handles Decision, Form, RACI, Risk, Timeline, Dashboard. `data` attr holds JSON specific to each `blockType`. ReactNodeViewRenderer dispatches to type-specific renderer. |
| **RD-005**: Phase 4 viz engine | Apache ECharts 5, D3.js, Chart.js, Nivo | **Apache ECharts 5** | All 8 viz types built-in (bar, line, area, pie, force graph, treemap, tree, custom). Interactive drag/zoom/click. Sandbox-friendly in iframe. |
| **RD-006**: Viz sandboxing | iframe srcdoc, Web Worker, Shadow DOM | **iframe srcdoc** | Full isolation. `sandbox="allow-scripts"`. No parent access. postMessage for data. 5s timeout. |
| **RD-007**: Agent block generation | (a) New MCP tools, (b) Existing insert_block with markdown patterns | **(b) Existing insert_block** | Agent generates markdown code blocks (` ```mermaid `, ` ```checklist `) or structured JSON blocks. Frontend content handler recognizes and converts. Zero backend changes. |

---

## Architecture: 3-Extension Strategy

### Extension 1: Enhanced CodeBlock (Diagrams + Visualizations)

**Approach**: Extend existing `CodeBlockExtension` to detect special language identifiers and render interactive previews.

**Language → Renderer mapping**:

| Code Block Language | Renderer | Phase |
|--------------------|----------|-------|
| `mermaid` | Mermaid.js → SVG preview | P1 |
| `echarts-bar`, `echarts-line`, `echarts-area`, `echarts-pie` | ECharts iframe sandbox | P4 |
| `echarts-graph`, `echarts-treemap`, `echarts-tree` | ECharts iframe sandbox | P4 |
| `echarts-custom` | ECharts iframe sandbox (custom render) | P4 |

**How it works**:
1. User types ` ```mermaid ` or AI inserts via `insert_block` MCP tool
2. CodeBlock node has `language: 'mermaid'` (standard attr)
3. Enhanced CodeBlock's NodeView detects the language
4. Renders preview panel (SVG for Mermaid, iframe for ECharts) above the source code
5. Toggle button switches between source-only and preview+source
6. All data is the text content of the code block — zero new attrs needed

**Stored in TipTap JSON as** (identical to current code blocks):
```json
{
  "type": "codeBlock",
  "attrs": { "language": "mermaid", "blockId": "uuid-1" },
  "content": [{ "type": "text", "text": "flowchart TD\n  A-->B" }]
}
```

### Extension 2: Enhanced TaskList (Smart Checklist)

**Approach**: Use `TaskItem.extend()` to add structured attributes.

**New attrs on TaskItem**:

| Attr | Type | Default | Notes |
|------|------|---------|-------|
| assignee | string | null | Workspace member UUID |
| dueDate | string | null | ISO date |
| priority | string | 'none' | none/low/medium/high/urgent |
| isOptional | boolean | false | Excluded from progress % |
| estimatedEffort | string | null | Story points or hours |
| conditionalParentId | string | null | Parent item ID for conditional visibility |

**Progress bar**: ProseMirror decoration plugin on TaskList that calculates `checkedRequired / totalRequired * 100` and renders a progress bar above the list.

**Stored in TipTap JSON as** (extended existing TaskItem):
```json
{
  "type": "taskList",
  "attrs": { "blockId": "uuid-2" },
  "content": [
    {
      "type": "taskItem",
      "attrs": {
        "checked": false,
        "assignee": "member-uuid",
        "dueDate": "2026-02-15",
        "priority": "high",
        "isOptional": false
      },
      "content": [{ "type": "paragraph", "content": [{ "type": "text", "text": "Review PR" }] }]
    }
  ]
}
```

### Extension 3: Generic PMBlock (Decision, Form, RACI, Risk, Timeline, Dashboard)

**Approach**: Single TipTap Node with `blockType` discriminator and `data` JSON attr.

**Node definition**:

| Attr | Type | Notes |
|------|------|-------|
| blockId | string (UUID) | Stable identifier |
| blockType | enum | `decision` / `form` / `raci` / `risk-register` / `timeline` / `dashboard` |
| data | JSON string | Type-specific data (parsed by renderer) |
| userEdited | boolean | Agent edit guard (FR-048) |

**Renderer factory** (`PMBlockNodeView.tsx`):
```
blockType → Renderer Component
decision  → DecisionRenderer.tsx
form      → FormRenderer.tsx
raci      → RACIRenderer.tsx
risk      → RiskRenderer.tsx
timeline  → TimelineRenderer.tsx
dashboard → DashboardRenderer.tsx
```

**Stored in TipTap JSON as**:
```json
{
  "type": "pmBlock",
  "attrs": {
    "blockId": "uuid-3",
    "blockType": "decision",
    "data": "{\"title\":\"Redis vs Memcached\",\"type\":\"multi-option\",\"options\":[...],\"status\":\"open\"}",
    "userEdited": false
  }
}
```

---

## Story-to-Extension Matrix

| User Story | Extension Used | New Files |
|------------|---------------|-----------|
| US-001: Diagram (P1) | Enhanced CodeBlock | MermaidPreview.tsx |
| US-002: Smart Checklist (P2) | Enhanced TaskItem | TaskItemEnhanced.ts, ProgressBarDecoration.ts, ChecklistItemUI.tsx |
| US-003: Decision Record (P2) | PMBlock (type: decision) | DecisionRenderer.tsx, OptionCard.tsx |
| US-004: Form (P3) | PMBlock (type: form) | FormRenderer.tsx, FormField.tsx |
| US-005: RACI Matrix (P3) | PMBlock (type: raci) | RACIRenderer.tsx |
| US-006: Risk Register (P3) | PMBlock (type: risk) | RiskRenderer.tsx |
| US-007: Custom Viz (P4) | Enhanced CodeBlock | EChartsPreview.tsx, VizSandbox.tsx |
| US-008: Timeline (P4) | PMBlock (type: timeline) | TimelineRenderer.tsx |
| US-009: KPI Dashboard (P4) | PMBlock (type: dashboard) | DashboardRenderer.tsx |
| US-010: Aggregation (P4) | Agent skill only | aggregate-forms skill |

---

## Requirements-to-Architecture Mapping

### Phase 1 — Diagrams (Enhanced CodeBlock + Mermaid)

| FR | Requirement | Approach |
|----|------------|----------|
| FR-001 | Render diagrams as vector graphics | Mermaid.js `render()` → SVG in preview panel above codeBlock |
| FR-002 | 10 diagram types | Mermaid native: flowchart, sequence, gantt, class, erDiagram, stateDiagram, C4, pie, mindmap, gitGraph |
| FR-003 | Click nodes for tooltips + issue link | SVG event delegation on rendered output |
| FR-004 | Live preview panel | Split view: code editor (existing) + SVG preview (new decoration) |
| FR-005 | Inline syntax validation | `mermaid.parse()` → error shown below preview |
| FR-006 | Last valid render preservation | Cache last valid SVG in component state |
| FR-007 | Agent auto-insertion | Agent uses `insert_block` with ` ```mermaid\n...\n``` ` markdown |
| FR-008 | Undo support | Native TipTap undo — codeBlock is standard node |
| FR-009 | Auto-save compatible | codeBlock already auto-saves — zero changes needed |
| FR-010 | `/diagram` slash command | Inserts codeBlock with `language: 'mermaid'` + template |
| FR-011 | Mobile read-only | CSS responsive: hide source, show SVG only, pinch-zoom |
| FR-012 | Export as image | SVG → Canvas → PNG |

### Phase 2 — Smart Checklist (Enhanced TaskItem)

| FR | Requirement | Approach |
|----|------------|----------|
| FR-013 | Structured checklist items | `TaskItem.extend()` with new attrs |
| FR-014 | Assignee assignment | MemberPicker component on assignee attr click |
| FR-015 | Due dates with overdue | DatePicker + overdue logic: `dueDate < now && !checked` |
| FR-016 | Priority levels | Priority badge rendered from `priority` attr |
| FR-017 | Required/Optional | `isOptional` attr → dashed border, excluded from progress |
| FR-018 | Conditional visibility | `conditionalParentId` → grey out when parent unchecked |
| FR-019 | Progress bar | Decoration plugin calculates and renders above TaskList |
| FR-025 | Agent auto-insertion | Agent inserts markdown task list with extended syntax |
| FR-026 | `/checklist` command | Inserts TaskList with sample items |

### Phase 2 — Decision Record (PMBlock type: decision)

| FR | Requirement | Approach |
|----|------------|----------|
| FR-020 | State machine (Open → Decided → Superseded) | `data.status` field in PMBlock |
| FR-021 | Binary / multi-option | `data.type` field: 'binary' or 'multi-option' |
| FR-022 | Pros/cons/effort/risk per option | `data.options[]` with structured fields |
| FR-023 | Decision recording | `data.finalDecision`, `data.rationale`, `data.decisionDate` |
| FR-024 | Create Issue | Button calls `issuesApi.create()`, links ID to `data.linkedIssueIds` |
| FR-025 | Agent auto-insertion | Agent inserts PMBlock with `blockType: 'decision'` |
| FR-026 | `/decision` command | Inserts PMBlock with decision template |

### Phase 3 — Form, RACI, Risk Register (PMBlock variants)

| FR | Requirement | Approach |
|----|------------|----------|
| FR-027-029 | Form with 10 field types + validation | PMBlock `blockType: 'form'`, `data.fields[]` + `data.responses{}` |
| FR-030-031 | RACI with constraint validation | PMBlock `blockType: 'raci'`, `data.deliverables[]` + `data.stakeholders[]` + `data.assignments{}` |
| FR-032-033 | Risk Register with scoring + colors | PMBlock `blockType: 'risk'`, `data.risks[]` with P×I score |
| FR-034-035 | Agent triggers + slash commands | Same pattern as P2 |

### Phase 4 — Viz, Timeline, Dashboard

| FR | Requirement | Approach |
|----|------------|----------|
| FR-036-038 | 8 viz types in sandbox | CodeBlock `language: 'echarts-*'` + iframe preview |
| FR-039-040 | Timeline with drag + keyboard | PMBlock `blockType: 'timeline'` |
| FR-041 | KPI Dashboard with live data | PMBlock `blockType: 'dashboard'` |
| FR-042-043 | Aggregation + slash commands | Agent skill + same patterns |

### Cross-Cutting (FR-044 through FR-057)

| FR | Approach |
|----|----------|
| FR-044 Block IDs | CodeBlock + TaskList already have blockId. PMBlock adds it. |
| FR-045 Loading order | PMBlock registered before BlockIdExtension |
| FR-046 Text serialization | CodeBlock content IS text. PMBlock `data` is JSON string. TaskItem attrs serialized. |
| FR-047 DD-003 | Agent insertions are additive. Undo removes block. |
| FR-048 Agent edit guard | PMBlock has `userEdited` attr. CodeBlock/TaskList: track via `editor.storage`. |
| FR-049-051 Accessibility | Per-renderer: role, aria-label, keyboard handlers, contrast |
| FR-052 Theme | Mermaid theme config. ECharts theme. CSS variables for PMBlock. |
| FR-053 Read-only | Pass `readOnly` prop to renderers. Disable interactive elements. |
| FR-054 Copy/paste | CodeBlock: native. TaskItem: clear assignee on paste. PMBlock: type-specific clear rules. |
| FR-055 Export | CodeBlock: SVG→image. TaskItem: markdown list. PMBlock: structured text per type. |
| FR-056 Block references | PMBlock `data` can reference other blockIds. "(deleted)" on missing. |
| FR-057 Template undo | Wrap template insertions in `editor.chain()` |

---

## Project Structure (Simplified)

```text
frontend/src/features/notes/editor/extensions/
├── CodeBlockExtension.ts              # MODIFIED — add preview renderer registry
├── pm-blocks/                         # NEW directory
│   ├── MermaidPreview.tsx             # P1: Mermaid SVG preview component
│   ├── EChartsPreview.tsx             # P4: ECharts iframe sandbox component
│   ├── VizSandbox.tsx                 # P4: iframe srcdoc builder + postMessage
│   ├── TaskItemEnhanced.ts           # P2: TaskItem.extend() with new attrs
│   ├── ProgressBarDecoration.ts      # P2: ProseMirror decoration for progress bar
│   ├── ChecklistItemUI.tsx           # P2: Enhanced task item UI (assignee, date, priority)
│   ├── PMBlockExtension.ts           # NEW: Single generic PM block node
│   ├── PMBlockNodeView.tsx           # NEW: Renderer factory (dispatches by blockType)
│   ├── renderers/                    # Type-specific renderers
│   │   ├── DecisionRenderer.tsx      # P2
│   │   ├── OptionCard.tsx            # P2
│   │   ├── FormRenderer.tsx          # P3
│   │   ├── FormField.tsx             # P3 (10 field types)
│   │   ├── RACIRenderer.tsx          # P3
│   │   ├── RiskRenderer.tsx          # P3
│   │   ├── TimelineRenderer.tsx      # P4
│   │   └── DashboardRenderer.tsx     # P4
│   ├── shared/
│   │   ├── MemberPicker.tsx          # Shared: workspace member dropdown
│   │   ├── DatePicker.tsx            # Shared: date picker component
│   │   └── useBlockEditGuard.ts      # Shared: FR-048 edit guard hook
│   └── __tests__/
│       ├── MermaidPreview.test.tsx
│       ├── TaskItemEnhanced.test.ts
│       ├── PMBlockExtension.test.ts
│       └── renderers/
│           ├── DecisionRenderer.test.tsx
│           ├── FormRenderer.test.tsx
│           └── ...
├── slash-command-items.ts             # MODIFIED — add PM commands
└── createEditorExtensions.ts          # MODIFIED — register enhanced extensions

backend/src/pilot_space/ai/templates/skills/
├── generate-diagram/                  # MODIFIED — output ```mermaid format
└── aggregate-forms/                   # P4: NEW skill for cross-note aggregation
```

**File count comparison**:
- Original plan: ~45 new files (10 extensions + 10 NodeViews + 10 test dirs + shared)
- Simplified plan: ~22 new files (3 extensions + 8 renderers + shared + tests)

---

## Quickstart Validation

*(Same 8 scenarios as quickstart.md — no changes needed)*

---

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected |
|-----------|------------|------------------------------|
| PRE-001: NoteCanvas refactor | 701 lines, must split | Cannot add rendering logic without this |
| Mermaid.js (~250KB) | 10 diagram types | No built-in alternative |
| ECharts (~300KB, P4) | 8 interactive viz types | D3 requires 3x more code |
| PMBlock generic node | 6 block types need custom rendering | Individual extensions would be 6x files |

---

## Validation Checklists

### Architecture Completeness

- [x] Every FR mapped to extension strategy (57/57)
- [x] Every user story mapped to extension + renderer
- [x] Data model uses existing JSONB storage (zero migrations)
- [x] Agent integration uses existing MCP tools (zero backend changes)

### Simplicity Validation

- [x] 2 enhanced extensions + 1 new (vs 10 new)
- [x] ~22 new files (vs ~45)
- [x] Zero new API endpoints
- [x] Zero new database tables
- [x] Zero new MCP tools
- [x] Agent markdown patterns work with existing `insert_block`

### Constitution Compliance

- [x] Technology standards: TipTap extension enhancement
- [x] Simplicity: minimal new abstractions
- [x] Quality: >80% coverage, TypeScript strict, 700-line limit

---

## Agent Integration Architecture

**Research**: See `research.md` for full deep context analysis (42 files traced).

### Content Transport Strategy (RD-008)

**Hybrid approach** — leverage existing markdown parsing for standard nodes, use JSON content for custom PMBlock nodes:

| Block Type | Transport | SSE Field | Rationale |
|-----------|-----------|-----------|-----------|
| Diagram (mermaid) | Markdown: ` ```mermaid\n...\n``` ` | `markdown` | Standard code block, parsed natively by TipTap |
| Smart Checklist | Markdown: `- [ ] Item text` | `markdown` | Standard task list, extended attrs set by user |
| Decision Record | TipTap JSON | `content` | No standard markdown representation exists |
| Form Block | TipTap JSON | `content` | Complex field schema, no markdown equivalent |
| RACI Matrix | TipTap JSON | `content` | Matrix data, no markdown equivalent |
| Risk Register | TipTap JSON | `content` | Structured risk data, no markdown equivalent |
| Timeline | TipTap JSON | `content` | Milestone + dependency data |
| Dashboard | TipTap JSON | `content` | Widget config + data source refs |

**SSE contract unchanged** — `ContentUpdateData` already has both `markdown` and `content` fields (`events.ts:302-351`). No schema changes needed.

### System Prompt Changes

**`SYSTEM_PROMPT_BASE`** (`pilotspace_agent.py:110-136`):
Add after tool categories section:
```
## PM blocks
When users discuss architecture, decisions, sprints, risks, or planning:
- Diagrams: insert ```mermaid code block via insert_block
- Checklists: insert markdown task list via write_to_note
- Decision/Form/RACI/Risk/Timeline/Dashboard: insert PMBlock via insert_block with JSON content
PM blocks are additive (auto-execute, no approval). User can Ctrl+Z to undo.
Do NOT modify PM blocks the user has manually edited (FR-048 edit guard).
```

**Estimated token impact**: +120 tokens to system prompt (~3% of 8K budget).

### Operational Rules Changes

**`templates/rules/notes.md`** — append new section:

```markdown
## PM Block Types:

1. **Diagram blocks** (Phase 1):
   - Code blocks with `language: 'mermaid'` render as interactive diagrams
   - Auto-insert when architecture discussion detected (components, flows, entities, states)
   - Trigger keywords: "architecture", "flow", "diagram", "sequence", "class", "relationship"
   - Insert via: `insert_block` with ```mermaid\n{syntax}\n```
   - Size limit: 500 lines or 200 nodes

2. **Smart Checklist** (Phase 2):
   - Enhanced task lists with assignee, due date, priority metadata
   - Auto-insert on task decomposition detection
   - Trigger keywords: "tasks", "checklist", "action items", "definition of done", "sprint backlog"
   - Insert via: `write_to_note` or `insert_block` with markdown task list

3. **Decision Record** (Phase 2):
   - Structured decision tracking (Open → Decided → Superseded)
   - Auto-insert on decision language detection
   - Trigger keywords: "should we", "decision:", "ADR:", "option A vs B", "go/no-go"
   - Insert via: `insert_block` with PMBlock JSON content

4. **Form / RACI / Risk Register** (Phase 3):
   - Structured data collection blocks
   - Auto-insert on retrospective, responsibility, risk language
   - Insert via: `insert_block` with PMBlock JSON content

5. **Visualization / Timeline / Dashboard** (Phase 4):
   - Interactive charts and KPI widgets
   - Insert via enhanced code blocks (echarts-*) or PMBlock JSON

## PM Block Agent Rules:

- NEVER modify a PM block the user has manually edited (edit guard FR-048)
- Auto-insertions are non-destructive: user can always Ctrl+Z
- Use conservative trigger detection — prefer false negative over false positive
- Include confidence tag in chat response when auto-inserting
```

### Skill Updates

**`generate-diagram/SKILL.md`** — update output format:

| Aspect | Current | Updated |
|--------|---------|---------|
| Output | JSON `{diagram_type, mermaid_code, confidence}` | Call `insert_block` with ` ```mermaid\n{syntax}\n``` ` markdown |
| Delivery | Skill returns JSON → not rendered | Skill instructs Agent to use `insert_block` MCP tool → renders in note |
| Confidence | In JSON output | In chat response text |

**New skills** (by phase):

| Skill | Phase | Purpose | Files |
|-------|-------|---------|-------|
| sprint-planning | P2 | Template: Gantt + checklist + decision | `templates/skills/sprint-planning/SKILL.md` |
| adr-lite | P2 | Template: decision + architecture diagram | `templates/skills/adr-lite/SKILL.md` |
| adr-full | P3 | Template: decision + diagram + risk register + form | `templates/skills/adr-full/SKILL.md` |
| release-readiness | P3 | Template: checklist + decision + risk + diagram + form | `templates/skills/release-readiness/SKILL.md` |
| sprint-retro | P3 | Template: form + checklist + decision | `templates/skills/sprint-retro/SKILL.md` |
| project-kickoff | P3 | Template: RACI + diagram + risk + checklist | `templates/skills/project-kickoff/SKILL.md` |
| aggregate-forms | P4 | Cross-note form data aggregation | `templates/skills/aggregate-forms/SKILL.md` |

### Role Template Updates

| Template | Phase | Changes |
|----------|-------|---------|
| `project_manager.md` | P2 | Add: "Use /checklist for sprint backlogs, /decision for go/no-go, /risk-register for risk assessment, /raci for responsibilities. Generate Gantt diagrams for sprint timelines." |
| `architect.md` | P2 | Add: "Use /diagram for C4, sequence, class, ER diagrams. Use /decision for ADRs with structured alternatives comparison." |
| `tech_lead.md` | P2 | Add: "Use /checklist for sprint backlogs and DoD. Use /diagram for architecture visualization. Use /decision for technical decisions." |
| `devops.md` | P3 | Add: "Use /checklist for deployment checklists. Use /risk-register for release risks." |

### Backend File Changes (Complete)

```text
backend/src/pilot_space/ai/
├── agents/pilotspace_agent.py               # MODIFIED: SYSTEM_PROMPT_BASE +120 tokens
├── templates/
│   ├── rules/notes.md                       # MODIFIED: +PM block types section
│   ├── role_templates/
│   │   ├── project_manager.md               # MODIFIED: PM block awareness (P2)
│   │   ├── architect.md                     # MODIFIED: diagram + ADR awareness (P2)
│   │   ├── tech_lead.md                     # MODIFIED: sprint planning awareness (P2)
│   │   └── devops.md                        # MODIFIED: release checklist awareness (P3)
│   └── skills/
│       ├── generate-diagram/SKILL.md        # MODIFIED: JSON → mermaid markdown (P1)
│       ├── sprint-planning/SKILL.md         # NEW (P2)
│       ├── adr-lite/SKILL.md                # NEW (P2)
│       ├── adr-full/SKILL.md                # NEW (P3)
│       ├── release-readiness/SKILL.md       # NEW (P3)
│       ├── sprint-retro/SKILL.md            # NEW (P3)
│       ├── project-kickoff/SKILL.md         # NEW (P3)
│       └── aggregate-forms/SKILL.md         # NEW (P4)
```

---

## Next Phase

1. Create simplified `tasks.md` (~65 tasks vs 132)
2. Start Phase 1: PRE-001 canvas refactor → Mermaid preview → slash command → Agent integration
3. Install: `pnpm add mermaid@11` (P1), `pnpm add echarts echarts-for-react` (P4)

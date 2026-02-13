# Tasks: PM Note Extensions (Simplified)

**Feature**: PM Note Extensions (013)
**Branch**: `013-pm-note-extensions`
**Created**: 2026-02-11
**Revised**: 2026-02-11 (v2 — 65 tasks vs 132)
**Source**: `specs/013-pm-note-extensions/`
**Author**: Tin Dang

---

## Phase 1: Prerequisites

- [ ] T001 Split NoteCanvas.tsx into NoteCanvasEditor.tsx + NoteCanvasLayout.tsx in `frontend/src/components/editor/` (PRE-001: reduce from 701 to <500 lines)
- [ ] T002 Write tests for extracted canvas components in `frontend/src/components/editor/__tests__/NoteCanvasEditor.test.tsx`
- [ ] T003 Document extension loading order in `frontend/src/features/notes/editor/extensions/createEditorExtensions.ts` (PRE-002)
- [ ] T004 Create shared PM utilities: MemberPicker, DatePicker, useBlockEditGuard in `frontend/src/features/notes/editor/extensions/pm-blocks/shared/`

**Checkpoint**: NoteCanvas < 500 lines. Shared components ready. Quality gates pass.

---

## Phase 2: Diagrams — Enhanced CodeBlock + Mermaid (P1)

**Goal**: ` ```mermaid ` code blocks render as interactive SVG diagrams.
**Verify**: Type ` ```mermaid ` → flowchart renders. Agent auto-inserts. Undo works.

- [ ] T005 Install Mermaid.js: `pnpm add mermaid@11` in `frontend/`
- [ ] T006 [P] Write tests for MermaidPreview in `frontend/src/features/notes/editor/extensions/pm-blocks/__tests__/MermaidPreview.test.tsx` (10 diagram types, error handling, last valid SVG, theme sync)
- [ ] T007 [P] Write tests for enhanced CodeBlock preview in `frontend/src/features/notes/editor/extensions/pm-blocks/__tests__/CodeBlockPreview.test.ts` (language detection, toggle source/preview)
- [ ] T008 Create MermaidPreview component in `frontend/src/features/notes/editor/extensions/pm-blocks/MermaidPreview.tsx` (mermaid.render() → SVG, 300ms debounce, error display, last valid SVG cache, theme sync; FR-001 through FR-006)
- [ ] T009 Enhance CodeBlockExtension in `frontend/src/features/notes/editor/extensions/CodeBlockExtension.ts` (detect `language: 'mermaid'` → render MermaidPreview above source, toggle source/preview button; FR-004)
- [ ] T010 Add SVG click handler in MermaidPreview for node tooltips + "Link to Issue" action (FR-003)
- [ ] T011 Add diagram export-as-image in MermaidPreview (SVG → Canvas → PNG; FR-012)
- [ ] T012 Add `/diagram` slash command to `frontend/src/features/notes/editor/extensions/slash-command-items.ts` (inserts codeBlock with `language: 'mermaid'` + type template; FR-010)
- [ ] T013 Update `generate-diagram` skill in `backend/src/pilot_space/ai/templates/skills/generate-diagram/SKILL.md`: change output format from JSON `{diagram_type, mermaid_code, confidence}` to instruction for Agent to call `insert_block` MCP tool with ` ```mermaid\n{syntax}\n``` ` as `content_markdown`. Move confidence tag to chat response text. (FR-007; see research.md §4 R-001 DANGER)
- [ ] T014 Add diagram size limit enforcement (max 500 lines, 200 nodes → "Diagram too complex" fallback)

**Checkpoint**: 10 diagram types render. `/diagram` works. Agent inserts mermaid blocks. Undo removes. Auto-save persists (zero changes needed). Quickstart Scenarios 1, 2, 4.

---

## Phase 3: Smart Checklist — Enhanced TaskItem (P2)

**Goal**: TaskList items gain assignee, due date, priority, optional flag, progress bar.
**Verify**: `/checklist` → add items with metadata → progress bar updates.

- [ ] T015 [P] Write tests for TaskItemEnhanced in `frontend/src/features/notes/editor/extensions/pm-blocks/__tests__/TaskItemEnhanced.test.ts` (new attrs serialization, parse/render)
- [ ] T016 [P] Write tests for ChecklistItemUI in `frontend/src/features/notes/editor/extensions/pm-blocks/__tests__/ChecklistItemUI.test.tsx` (assignee picker, date picker, priority badge, optional style, conditional grey-out)
- [ ] T017 [P] Write tests for ProgressBarDecoration in `frontend/src/features/notes/editor/extensions/pm-blocks/__tests__/ProgressBarDecoration.test.ts`
- [ ] T018 Create TaskItemEnhanced in `frontend/src/features/notes/editor/extensions/pm-blocks/TaskItemEnhanced.ts` (TaskItem.extend() with assignee, dueDate, priority, isOptional, estimatedEffort, conditionalParentId attrs; FR-013 through FR-018)
- [ ] T019 Create ChecklistItemUI in `frontend/src/features/notes/editor/extensions/pm-blocks/ChecklistItemUI.tsx` (render assignee avatar + MemberPicker, date badge + DatePicker, priority badge, optional dashed border, conditional parent grey-out; FR-014 through FR-018)
- [ ] T020 Create ProgressBarDecoration in `frontend/src/features/notes/editor/extensions/pm-blocks/ProgressBarDecoration.ts` (ProseMirror decoration on TaskList: computes checkedRequired/totalRequired, renders progress bar above list; FR-019)
- [ ] T021 Register TaskItemEnhanced + ProgressBarDecoration in `frontend/src/features/notes/editor/extensions/createEditorExtensions.ts` (replace default TaskItem)
- [ ] T022 Add `/checklist` slash command to `slash-command-items.ts` (inserts TaskList with 3 sample items; FR-026)
- [ ] T023 Add keyboard navigation: arrow keys between items, Space toggle, Tab indent (FR-049)

**Checkpoint**: Checklist items show assignee/date/priority. Progress bar works. Optional excluded from %. Conditional items grey out. Quickstart Scenario 3.

---

## Phase 4: Decision Record — PMBlock (P2)

**Goal**: PMBlock with `blockType: 'decision'` renders a decision record with state machine.
**Verify**: `/decision` → fill options → decide → status transitions.

- [ ] T024 [P] Write tests for PMBlockExtension in `frontend/src/features/notes/editor/extensions/pm-blocks/__tests__/PMBlockExtension.test.ts` (generic node: blockType, data, userEdited attrs)
- [ ] T025 [P] Write tests for DecisionRenderer in `frontend/src/features/notes/editor/extensions/pm-blocks/__tests__/renderers/DecisionRenderer.test.tsx`
- [ ] T026 Create PMBlockExtension in `frontend/src/features/notes/editor/extensions/pm-blocks/PMBlockExtension.ts` (TipTap Node: blockType enum, data JSON string, userEdited boolean; group: 'block', atom: true)
- [ ] T027 Create PMBlockNodeView in `frontend/src/features/notes/editor/extensions/pm-blocks/PMBlockNodeView.tsx` (ReactNodeViewRenderer: reads blockType → dispatches to renderer component from registry)
- [ ] T028 Create DecisionRenderer in `frontend/src/features/notes/editor/extensions/pm-blocks/renderers/DecisionRenderer.tsx` (state machine UI: Open/Decided/Superseded, option cards, "Decide" button, rationale field, summary banner; FR-020 through FR-023)
- [ ] T029 Create OptionCard in `frontend/src/features/notes/editor/extensions/pm-blocks/renderers/OptionCard.tsx` (label, description, pros/cons, effort, risk; FR-022)
- [ ] T030 Implement "Create Issue" in DecisionRenderer (calls issuesApi.create() with context, links ID back; FR-024)
- [ ] T031 Register PMBlockExtension in `createEditorExtensions.ts` (before BlockIdExtension; FR-045)
- [ ] T032 Add pmBlock to BlockIdExtension's block type list in `BlockIdExtension.ts` (FR-044)
- [ ] T033 Add `/decision` slash command to `slash-command-items.ts` (inserts PMBlock with blockType: 'decision' + empty template; FR-026)

**Checkpoint**: Decision Record renders. State transitions work. Options comparison. Issue creation. Quickstart Scenario 5.

---

## Phase 5: Agent Integration P1+P2

**Goal**: Agent proactively inserts diagrams, checklists, and decisions from conversation context.

- [ ] T034 [P] Update `SYSTEM_PROMPT_BASE` in `backend/src/pilot_space/ai/agents/pilotspace_agent.py:110-136`: add PM block section after tool categories — diagram (mermaid code blocks via `insert_block`), checklist (markdown task lists via `write_to_note`), PMBlock (decision/form/raci/risk via `insert_block` with JSON `content`). Add edit guard rule (FR-048). Estimated +120 tokens. (FR-007, FR-025; see research.md §3 for content transport strategy)
- [ ] T035 [P] Update `backend/src/pilot_space/ai/templates/rules/notes.md`: append PM Block Types section with auto-detection trigger keywords — diagrams: "architecture/flow/diagram/sequence/class/relationship", checklists: "tasks/checklist/action items/DoD/sprint backlog", decisions: "should we/decision:/ADR:/option A vs B". Add PM Block Agent Rules (edit guard, conservative detection, confidence tags). (FR-007, FR-025; see research.md §3 for full text)
- [ ] T036 [P] Update role templates: (a) `project_manager.md` — add PM block awareness for /checklist, /decision, /risk-register, /raci, Gantt diagrams; (b) `architect.md` — add /diagram (C4, sequence, class, ER) + /decision for ADRs; (c) `tech_lead.md` — add /checklist for sprint backlogs + /diagram for architecture. (FR-025; see research.md §5)
- [ ] T037 Write integration test for Agent PM block generation in `backend/tests/integration/ai/test_pm_block_generation.py`: verify Agent calls `insert_block` with mermaid markdown for diagram triggers, markdown task list for checklist triggers, PMBlock JSON for decision triggers. Test edit guard (Agent skips user-edited blocks). Test undo grouping for template insertions.
- [ ] T038 [P] Create template skill `backend/src/pilot_space/ai/templates/skills/sprint-planning/SKILL.md` (T-002): instructs Agent to insert Gantt diagram (mermaid gantt), sprint backlog checklist (markdown task list), DoD checklist, sprint goal decision record (PMBlock JSON). All blocks inserted as single undo group via `editor.chain()`.
- [ ] T039 [P] Create template skill `backend/src/pilot_space/ai/templates/skills/adr-lite/SKILL.md` (T-003): instructs Agent to insert Decision Record (PMBlock JSON with multi-option template) + architecture diagram (mermaid code block with before/after). Skill auto-discovered by `skill_discovery.py`.

**Checkpoint**: Agent auto-inserts PM blocks from conversation. Templates work as single undo group.

---

## Phase 6: Form + RACI + Risk Register — PMBlock Renderers (P3)

**Goal**: 3 new PMBlock renderers for structured data collection.
**Verify**: `/form`, `/raci`, `/risk-register` each insert working blocks.

### Form Block

- [ ] T040 [P] Write tests for FormRenderer in `frontend/src/features/notes/editor/extensions/pm-blocks/__tests__/renderers/FormRenderer.test.tsx`
- [ ] T041 Create FormRenderer in `frontend/src/features/notes/editor/extensions/pm-blocks/renderers/FormRenderer.tsx` (renders fields from `data.fields[]`, stores responses in `data.responses{}`; FR-027 through FR-029)
- [ ] T042 Create FormField in `frontend/src/features/notes/editor/extensions/pm-blocks/renderers/FormField.tsx` (factory for 10 types: short-text, long-text, dropdown, multi-select, date, rating, number, member, toggle, file-ref; FR-028)
- [ ] T043 Add `/form` slash command to `slash-command-items.ts` (FR-035)

### RACI Matrix

- [ ] T044 [P] Write tests for RACIRenderer in `frontend/src/features/notes/editor/extensions/pm-blocks/__tests__/renderers/RACIRenderer.test.tsx`
- [ ] T045 Create RACIRenderer in `frontend/src/features/notes/editor/extensions/pm-blocks/renderers/RACIRenderer.tsx` (matrix grid, cell click → R/A/C/I dropdown, exactly-one-A validation per row; FR-030, FR-031)
- [ ] T046 Add `/raci` slash command to `slash-command-items.ts` (FR-035)

### Risk Register

- [ ] T047 [P] Write tests for RiskRenderer in `frontend/src/features/notes/editor/extensions/pm-blocks/__tests__/renderers/RiskRenderer.test.tsx`
- [ ] T048 Create RiskRenderer in `frontend/src/features/notes/editor/extensions/pm-blocks/renderers/RiskRenderer.tsx` (risk rows, P×I auto-score, color coding: green < 6, yellow 6-14, red >= 15, strategy/owner/trigger fields; FR-032, FR-033)
- [ ] T049 Add `/risk-register` slash command to `slash-command-items.ts` (FR-035)

### Agent Integration P3

- [ ] T050 [P] Update `backend/src/pilot_space/ai/templates/rules/notes.md`: add Form/RACI/Risk Register auto-detection triggers — form: "retrospective/survey/feedback/assessment", RACI: "responsibility/who does what/accountability", risk: "risk/mitigation/probability/impact". Update `devops.md` role template with deployment checklist + release risk awareness. (FR-034; see research.md §5)
- [ ] T051 [P] Create 4 template skills in `backend/src/pilot_space/ai/templates/skills/`: (a) `adr-full/SKILL.md` (T-004: decision + diagram + risk register + form as PMBlock JSON); (b) `release-readiness/SKILL.md` (T-005: checklist + decision + risk + diagram + form); (c) `sprint-retro/SKILL.md` (T-006: form + checklist + decision); (d) `project-kickoff/SKILL.md` (T-007: RACI + diagram + risk + checklist). All use `insert_block` with PMBlock JSON content. Auto-discovered by `skill_discovery.py`.
- [ ] T052 Write integration tests for P3 Agent triggers in `backend/tests/integration/ai/test_pm_block_p3_triggers.py`: verify Agent calls `insert_block` with PMBlock JSON content for form/RACI/risk triggers. Verify template skills insert correct block types. Verify role template adaptation (PM gets risk/RACI suggestions, DevOps gets deployment checklists).

**Checkpoint**: Form renders 10 field types. RACI validates A-constraint. Risk auto-scores with colors. Quickstart Scenarios 6, 7.

---

## Phase 7: Viz + Timeline + Dashboard (P4)

**Goal**: ECharts visualizations in sandboxed iframe, timeline, and KPI dashboard.
**Verify**: `/chart` renders in sandbox. `/timeline` + `/dashboard` work.

### Visualizations (Enhanced CodeBlock + ECharts)

- [ ] T053 Install ECharts: `pnpm add echarts echarts-for-react` in `frontend/`
- [ ] T054 [P] Write tests for EChartsPreview + VizSandbox in `frontend/src/features/notes/editor/extensions/pm-blocks/__tests__/EChartsPreview.test.tsx`
- [ ] T055 Create VizSandbox in `frontend/src/features/notes/editor/extensions/pm-blocks/VizSandbox.tsx` (iframe srcdoc, sandbox="allow-scripts", CSP, postMessage data, 5s timeout; FR-037)
- [ ] T056 Create EChartsPreview in `frontend/src/features/notes/editor/extensions/pm-blocks/EChartsPreview.tsx` (builds ECharts config from code block content, renders in VizSandbox; FR-036)
- [ ] T057 Enhance CodeBlockExtension for `echarts-*` languages (same pattern as mermaid; FR-036)
- [ ] T058 Add `/chart` slash command to `slash-command-items.ts` (FR-043)

### Timeline (PMBlock renderer)

- [ ] T059 [P] Write tests for TimelineRenderer in `frontend/src/features/notes/editor/extensions/pm-blocks/__tests__/renderers/TimelineRenderer.test.tsx`
- [ ] T060 Create TimelineRenderer in `frontend/src/features/notes/editor/extensions/pm-blocks/renderers/TimelineRenderer.tsx` (SVG timeline, milestones, dependency arrows, drag-to-reschedule, Ctrl+Arrow keyboard; FR-039, FR-040)
- [ ] T061 Add `/timeline` slash command to `slash-command-items.ts` (FR-043)

### KPI Dashboard (PMBlock renderer)

- [ ] T062 [P] Write tests for DashboardRenderer in `frontend/src/features/notes/editor/extensions/pm-blocks/__tests__/renderers/DashboardRenderer.test.tsx`
- [ ] T063 Create DashboardRenderer in `frontend/src/features/notes/editor/extensions/pm-blocks/renderers/DashboardRenderer.tsx` (KPI widgets, cycle data fetch, 30s polling, SPI/CPI gauges; FR-041)
- [ ] T064 Add `/dashboard` slash command to `slash-command-items.ts` (FR-043)

### Cross-Note Aggregation + Agent P4

- [ ] T065 Create `aggregate-forms` skill in `backend/src/pilot_space/ai/templates/skills/aggregate-forms/SKILL.md`: instructs Agent to read form data from multiple notes via `search_notes` + `search_note_content` MCP tools (existing), aggregate rating fields (mean/median/trend), text fields (common themes via LLM), and generate summary report with trend visualization. Performance target: <10s for 50 notes (SC-006). (FR-042; see research.md §9 R-009 UNKNOWN)
- [ ] T066 [P] Update `backend/src/pilot_space/ai/templates/rules/notes.md`: add viz/timeline/dashboard auto-detection triggers — viz: "chart/graph/burndown/velocity/trend", timeline: "milestone/schedule/release plan", dashboard: "metrics/KPI/sprint status". Add echarts-* code block language patterns. (FR-043)
- [ ] T067 [P] Create 2 template skills: (a) `backend/src/pilot_space/ai/templates/skills/wbs/SKILL.md` (T-008: treemap viz + checklist + timeline); (b) `backend/src/pilot_space/ai/templates/skills/sprint-retro-enhanced/SKILL.md` (T-009: form + checklist + decision + velocity chart + cross-note aggregation). Auto-discovered by `skill_discovery.py`.
- [ ] T068 Write integration tests for P4 Agent triggers + aggregation in `backend/tests/integration/ai/test_pm_block_p4_triggers.py`: verify viz triggers produce echarts-* code blocks, timeline/dashboard triggers produce PMBlock JSON, aggregate-forms skill reads multiple notes and produces summary.

**Checkpoint**: 8 viz types render in sandbox. Timeline drag works. Dashboard auto-refreshes. Aggregation produces trends. Quickstart Scenario 8.

---

## Phase Final: Polish

- [ ] T069 [P] Add WCAG: `role="region"` + `aria-label` to all PM blocks (FR-049, FR-050)
- [ ] T070 [P] Add `prefers-reduced-motion` support (FR-049)
- [ ] T071 [P] Verify 4.5:1 contrast ratios in all PM blocks (FR-051)
- [ ] T072 Add copy/paste handlers: clear assignees (checklist), clear issue IDs (decision), clear responses (form) on paste (FR-054)
- [ ] T073 Add export handlers per block type (diagrams/viz → image, checklists → markdown, PMBlocks → structured text; FR-055)
- [ ] T074 Add template undo grouping via `editor.chain()` (FR-057)
- [ ] T075 Run full quickstart.md validation (all 8 scenarios)
- [ ] T076 [P] Ensure all PM block files < 700 lines
- [ ] T077 Run quality gates: `pnpm lint && pnpm type-check && pnpm test`
- [ ] T078 Run backend quality gates: `uv run pyright && uv run ruff check && uv run pytest --cov=.`

**Checkpoint**: Feature complete. All quality gates pass. WCAG AA. All quickstart scenarios verified.

---

## Dependencies

### Phase Order

```
Phase 1 (Prerequisites) → Phase 2 (Diagrams P1) → Phase 3 (Checklist P2) + Phase 4 (Decision P2)
→ Phase 5 (Agent P1+P2) → Phase 6 (Form+RACI+Risk P3) → Phase 7 (Viz+Timeline+Dashboard P4)
→ Phase Final (Polish)
```

### Parallel Opportunities

| Phase | Parallel Tasks |
|-------|---------------|
| Phase 2 | T006, T007 (tests) |
| Phase 3 | T015, T016, T017 (tests) |
| Phase 3+4 | Can run in parallel after Phase 2 |
| Phase 5 | T034, T035, T036 (Agent triggers), T038, T039 (templates) |
| Phase 6 | T040, T044, T047 (tests for Form, RACI, Risk — all independent) |
| Phase 7 | T054, T059, T062 (tests for Viz, Timeline, Dashboard — all independent) |
| Final | T069, T070, T071, T076 (a11y + cleanup) |

### Within Each Story

```
Tests → Extension/Enhancement → UI Component → Registration → Slash Command
```

---

## Execution Strategy

**Selected**: B (Incremental) — Deploy after each spec phase.

```
Phase 1-2 → Deploy P1 (Diagrams)
Phase 3-5 → Deploy P2 (Checklist + Decision + Agent)
Phase 6   → Deploy P3 (Form + RACI + Risk)
Phase 7   → Deploy P4 (Viz + Timeline + Dashboard + Aggregation)
Phase Final → Production-ready
```

---

## Comparison: Original vs Simplified

| Metric | Original | Simplified | Reduction |
|--------|----------|-----------|-----------|
| Total tasks | 132 | 78 | **-41%** |
| New TipTap extensions | 10 | 1 (+ 2 enhanced) | **-70%** |
| New files | ~45 | ~22 | **-51%** |
| New DB tables | 0 | 0 | Same |
| New API endpoints | 0 | 0 | Same |
| New MCP tools | 0 | 0 | Same |
| Diagram data format | Custom node attrs | Standard codeBlock text | **Simpler** |
| Checklist data format | Custom node attrs | Extended TaskItem attrs | **Reuses existing** |
| PM block format | 6 separate nodes | 1 generic PMBlock | **6→1** |

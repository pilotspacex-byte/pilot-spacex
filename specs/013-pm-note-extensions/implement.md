# Implementation Guide: PM Note Extensions (013)

**Feature**: PM Note Extensions — Enterprise SDLC Block Types
**Branch**: `013-pm-note-extensions`
**Created**: 2026-02-11
**Source**: `specs/013-pm-note-extensions/`
**Author**: Tin Dang

---

## Persona

You are a Senior Software Engineer with 15 years implementing production systems from
structured specifications. You excel at translating spec.md requirements and plan.md
architecture into working, tested code — following exact file paths, dependency ordering,
and quality gates without deviation. You treat tasks.md as a contract, not a suggestion.

Correct implementation from spec/plan artifacts prevents $50,000+ in rework from
misaligned code. Every line must trace to a requirement (FR-NNN) or constitution article.

---

## Context Loading Protocol

Before writing any code, load and internalize these artifacts in order:

### Step 1: Load Spec

**Read `specs/013-pm-note-extensions/spec.md`**

- Extract all FR-001 through FR-057 requirements and their acceptance scenarios (Given/When/Then)
- Note priority levels: P1 (Diagrams), P2 (Checklist + Decision), P3 (Form + RACI + Risk), P4 (Viz + Timeline + Dashboard)
- Note success criteria SC-001 through SC-010
- Identify 10 key entities: DiagramBlock, SmartChecklistBlock, ChecklistItem, DecisionRecordBlock, FormBlock, RACIMatrixBlock, RiskRegisterBlock, VisualizationBlock, TimelineBlock, KPIDashboardBlock
- Note size limits per block type (spec.md Size Limits Summary table)
- Note mobile/read-only/copy-paste/export behavior per block type

### Step 2: Load Plan

**Read `specs/013-pm-note-extensions/plan.md`**

- Load 3-Extension Strategy: Enhanced CodeBlock (diagrams + viz), Enhanced TaskItem (checklists), Generic PMBlock (decision, form, RACI, risk, timeline, dashboard)
- Load Story-to-Extension Matrix (10 user stories → 3 extensions)
- Load Requirements-to-Architecture Mapping (FR → approach per phase)
- Load Content Transport Strategy (RD-008): markdown for diagrams/checklists, TipTap JSON for PMBlocks
- Load Agent Integration Architecture: system prompt changes, rule updates, skill updates, role template updates
- Load Project Structure (file paths for all new/modified files)
- Note: Zero new DB tables, Zero new API endpoints, Zero new MCP tools

### Step 3: Load Research

**Read `specs/013-pm-note-extensions/research.md`**

- Load content pipeline trace: Agent → MCP tool → SSE → Frontend → TipTap mutation
- Note DANGER risks: R-001 (generate-diagram skill format), R-002 (NoteCanvas 702 lines)
- Note WATCH risks: R-003 through R-008
- Load key decisions: RD-008 (hybrid transport), RD-009 (plain task list for MVP)

### Step 4: Load Tasks

**Read `specs/013-pm-note-extensions/tasks.md`**

- Identify current phase being implemented
- Load the specific task T{NNN} and its dependencies
- Check [P] markers for parallelization opportunities
- Read the phase Checkpoint — this is the acceptance test

### Step 5: Load Quickstart

**Read `specs/013-pm-note-extensions/quickstart.md`**

- 8 smoke test scenarios mapped to phases
- Each phase checkpoint references specific quickstart scenarios

---

## Task Execution Protocol

For each task T{NNN}, execute these steps:

### Step A: Pre-Implementation Verification

- Confirm all blocking tasks (earlier T{NNN}s without [P]) are complete
- Confirm the target file path from tasks.md matches plan.md project structure
- Confirm the component being built is defined in plan.md Requirements-to-Architecture mapping
- If ANY mismatch exists between spec, plan, and tasks — STOP and flag it

### Step B: Write Tests First (if task starts with "Write tests")

- Derive test cases directly from spec.md acceptance scenarios (Given/When/Then)
- Map each test to the FR-NNN it validates
- Include edge cases from spec.md Edge Cases section
- Include size limit enforcement tests from spec.md Size Limits Summary
- Verify tests FAIL before implementation exists (TDD red phase)

### Step C: Implement the Component

- Follow the exact file path specified in T{NNN}
- Match the data model from plan.md (node attrs, JSON structure, enum values)
- Apply patterns from plan.md Research Decisions (RD-001 through RD-009)
- Respect constraints: 700-line file limit, TypeScript strict, WCAG 2.2 AA

### Step D: Validate Against Spec

For the implemented component, verify:

- [ ] Every FR-NNN mapped to this component (from plan.md mapping table) is satisfied
- [ ] Every acceptance scenario (Given/When/Then) from spec.md passes
- [ ] Size limits enforced (spec.md Size Limits Summary)
- [ ] Mobile behavior matches spec (read-only, pinch-zoom, stacked layout per block type)
- [ ] Read-only mode disables interactive elements per spec
- [ ] Copy/paste clears appropriate data per spec (assignees, issue IDs, responses)
- [ ] Export behavior per spec (diagrams → image, checklists → markdown, PMBlocks → structured text)
- [ ] Performance targets met (SC-003: diagram < 500ms, SC-004: viz < 3s, SC-005: checklist < 3s)

### Step E: Run Quality Gates

- [ ] Lint passes: `pnpm lint`
- [ ] Type check passes: `pnpm type-check`
- [ ] Tests pass: `pnpm test`
- [ ] File stays under 700 lines
- [ ] No TODOs, placeholders, or deferred work

For backend tasks:

- [ ] Lint passes: `uv run ruff check`
- [ ] Type check passes: `uv run pyright`
- [ ] Tests pass: `uv run pytest --cov=.`

### Step F: Checkpoint Validation

- If this task completes a phase, verify the phase Checkpoint statement from tasks.md
- Run the referenced quickstart.md scenarios
- Mark T{NNN} as complete only after all gates pass

---

## Phase-Specific Implementation Notes

### Phase 1: Prerequisites (T001-T004)

**Critical blocker**: NoteCanvas.tsx at 702 lines (PRE-001). Must split before any PM work.

| Task | Target File | Validation |
|------|-------------|------------|
| T001 | `frontend/src/components/editor/NoteCanvasEditor.tsx` + `NoteCanvasLayout.tsx` | < 500 lines each, existing tests pass |
| T002 | `frontend/src/components/editor/__tests__/NoteCanvasEditor.test.tsx` | Coverage > 80% |
| T003 | `frontend/src/features/notes/editor/extensions/createEditorExtensions.ts` | Loading order documented, BlockIdExtension remains last |
| T004 | `frontend/src/features/notes/editor/extensions/pm-blocks/shared/` | MemberPicker, DatePicker, useBlockEditGuard exported |

**Checkpoint**: NoteCanvas < 500 lines. Shared components ready. Quality gates pass.

### Phase 2: Diagrams (T005-T014)

**Strategy**: Enhanced CodeBlock — detect `language: 'mermaid'` → render MermaidPreview.

| Key Constraint | Value | Source |
|---------------|-------|--------|
| Render target | < 500ms for < 100 nodes | SC-003 |
| Size limit | 500 lines or 200 nodes | spec.md |
| Debounce | 300ms on source edit | plan.md |
| Error handling | Inline error + preserve last valid SVG | FR-005, FR-006 |
| Mobile | Read-only, pinch-to-zoom | FR-011 |
| Agent delivery | Markdown via `insert_block`: ` ```mermaid\n{syntax}\n``` ` | RD-008 |

**DANGER (R-001)**: T013 must update `generate-diagram` skill from JSON output to mermaid markdown + `insert_block` instruction. Without this, Agent-generated diagrams will not render.

**Checkpoint**: 10 diagram types render. `/diagram` works. Agent inserts mermaid blocks. Undo removes. Quickstart Scenarios 1, 2, 4.

### Phase 3: Smart Checklist (T015-T023)

**Strategy**: Enhanced TaskItem — `TaskItem.extend()` with new attrs.

| New Attr | Type | Default | FR |
|----------|------|---------|-----|
| assignee | string | null | FR-014 |
| dueDate | string | null | FR-015 |
| priority | string | 'none' | FR-016 |
| isOptional | boolean | false | FR-017 |
| estimatedEffort | string | null | spec.md |
| conditionalParentId | string | null | FR-018 |

**Progress bar formula**: `checkedRequired / totalRequired * 100` (exclude isOptional items from both numerator and denominator).

**Agent delivery**: Plain markdown task list `- [ ] Item text` via `write_to_note` or `insert_block`. Extended attrs set by user manually (RD-009).

**Checkpoint**: Checklist items show assignee/date/priority. Progress bar works. Optional excluded from %. Conditional items grey out. Quickstart Scenario 3.

### Phase 4: Decision Record (T024-T033)

**Strategy**: Generic PMBlock with `blockType: 'decision'`.

**State machine**: Open → Decided → Superseded (FR-020)

**Node attrs**: `{ blockId: UUID, blockType: 'decision', data: JSON string, userEdited: boolean }`

**Agent delivery**: TipTap JSON in SSE `content` field (not markdown — no standard markdown for decision records). Uses `insert_block` MCP tool.

**Checkpoint**: Decision Record renders. State transitions work. Options comparison. Issue creation. Quickstart Scenario 5.

### Phase 5: Agent Integration P1+P2 (T034-T039)

**3 categories of backend changes**:

1. **System prompt** (T034): +120 tokens to `SYSTEM_PROMPT_BASE` — PM block awareness
2. **Operational rules** (T035): Append to `templates/rules/notes.md` — trigger keywords + agent rules
3. **Role templates** (T036): Update project_manager.md, architect.md, tech_lead.md

**Key constraint**: System prompt total ~2.3K tokens of 8K budget after PM additions (research.md §1).

**Skills** (T038-T039): sprint-planning, adr-lite — auto-discovered by `skill_discovery.py` from `templates/skills/{name}/SKILL.md`.

**Checkpoint**: Agent auto-inserts PM blocks from conversation. Templates work as single undo group.

### Phase 6: Form + RACI + Risk (T040-T052)

**All use PMBlock** with different `blockType` values:

| Block | blockType | Key Validation | Quickstart |
|-------|-----------|---------------|------------|
| Form | `form` | 10 field types, required field validation | Scenario 6 |
| RACI | `raci` | Exactly-one-A per row constraint | — |
| Risk | `risk-register` | P*I auto-score, color coding (green < 6, yellow 6-14, red >= 15) | Scenario 7 |

**Skills** (T051): adr-full, release-readiness, sprint-retro, project-kickoff.

**Checkpoint**: Form renders 10 field types. RACI validates A-constraint. Risk auto-scores with colors. Quickstart Scenarios 6, 7.

### Phase 7: Viz + Timeline + Dashboard (T053-T068)

**Visualization security** (FR-037): iframe srcdoc with `sandbox="allow-scripts"`. No parent access, no network, no storage. 5-second execution timeout. Data via postMessage.

**Cross-note aggregation** (T065): Agent reads note content via existing `search_notes` + `search_note_content` MCP tools. Performance target: < 10s for 50 notes (SC-006).

**Checkpoint**: 8 viz types render in sandbox. Timeline drag works. Dashboard auto-refreshes. Aggregation produces trends. Quickstart Scenario 8.

### Phase Final: Polish (T069-T078)

**Accessibility** (FR-049 through FR-051): `role="region"`, `aria-label`, `prefers-reduced-motion`, 4.5:1 contrast.

**Full validation**: Run all 8 quickstart scenarios + both quality gate suites.

---

## Traceability Requirements

Every implementation decision must be traceable:

| Code Element | Must Reference |
|-------------|---------------|
| Node attrs / JSON structure | `plan.md` Extension Strategy section |
| Renderer component | `plan.md` Story-to-Extension Matrix |
| FR satisfaction | `spec.md` Functional Requirements |
| Test case | `spec.md` acceptance scenario (Given/When/Then) |
| Agent behavior | `plan.md` Agent Integration Architecture |
| Content transport | `research.md` Content Pipeline trace |
| Size limits | `spec.md` Size Limits Summary table |
| Performance targets | `spec.md` Success Criteria SC-001 through SC-010 |

If you cannot trace a piece of code to an artifact, it should not exist.
If an artifact requires something not yet implemented, flag it as a gap.

---

## Error Recovery Protocol

1. **Spec-Plan mismatch** — Plan says X, spec says Y
    -> Flag the conflict. Do NOT guess. Reference both artifact locations.

2. **Missing detail** — Task references component not in plan
    -> Check if it's in a different task's scope. If truly missing, flag as gap.

3. **Test failure after implementation** — Tests derived from spec don't pass
    -> Fix implementation to match spec, never modify tests to match broken code.

4. **Quality gate failure** — Lint/type/test failure
    -> Fix the issue in the current task. Do NOT defer to a later task.

5. **File size approaching 700 lines** — Near constitution limit
    -> Extract to a new module following plan.md project structure patterns.

6. **Agent content transport uncertainty** — Unsure if markdown or JSON
    -> Consult research.md RD-008 (hybrid strategy) and plan.md Content Transport table.

7. **DANGER risk triggered** — R-001 (skill format) or R-002 (canvas size)
    -> These are hard blockers. Stop and resolve before continuing.

---

## Output Format Per Task

For each T{NNN} completed, produce:

```
T{NNN}: {task description}

Files Modified/Created:
- {exact/path/file.ext} — {what was done}

Requirements Satisfied:
- FR-{NNN}: {brief description} ✓

Tests:
- {test_name}: {what it validates} — {PASS/FAIL}

Quality Gates:
- Lint: {PASS/FAIL}
- Type check: {PASS/FAIL}
- Tests: {PASS/FAIL} ({N}/{N} passing)
- File size: {N} lines (limit: 700)

Next Task:
- T{NNN+1}: {description} — {ready/blocked by T{NNN}}
```

---

## Self-Evaluation Framework

After completing each task, rate confidence (0-1):

1. **Spec Fidelity**: Does implementation match spec.md FR requirements exactly?
2. **Plan Compliance**: Does code follow plan.md 3-extension strategy and patterns?
3. **Content Transport**: Does Agent delivery match research.md RD-008 hybrid strategy?
4. **Test Coverage**: Are all acceptance scenarios (Given/When/Then) covered?
5. **Quality Gates**: Do all gates pass clean?
6. **Traceability**: Can every code element trace to an artifact?
7. **Edge Cases**: Are edge/error cases from spec handled (rendering, data integrity, export, agent, offline, size limits)?
8. **Performance**: SC-003 (diagram < 500ms), SC-004 (viz < 3s), SC-005 (checklist < 3s)?
9. **Accessibility**: WCAG 2.2 AA — keyboard nav, screen reader, contrast, reduced motion?
10. **Constitution**: 700-line limit, no TODOs, no placeholders, > 80% coverage?

If any score < 0.9, refine before marking the task complete.

---

## Task Validation Matrix

Cross-reference every task against spec requirements, plan architecture, and quickstart scenarios.

### Phase 1: Prerequisites

| Task | Spec Ref | Plan Ref | Quickstart | Validates |
|------|----------|----------|------------|-----------|
| T001 | PRE-001 | plan.md Complexity Tracking | — | NoteCanvas < 500 lines, existing functionality preserved |
| T002 | PRE-001 | — | — | Extracted components have > 80% test coverage |
| T003 | PRE-002, FR-045 | plan.md Extension Loading | — | BlockIdExtension remains last, new extensions load before it |
| T004 | FR-014, FR-015, FR-048 | plan.md shared/ directory | — | MemberPicker renders workspace members, DatePicker handles dates, useBlockEditGuard tracks user edits |

### Phase 2: Diagrams (P1)

| Task | Spec Ref | Plan Ref | Quickstart | Validates |
|------|----------|----------|------------|-----------|
| T005 | — | plan.md RD-001 | — | `mermaid@11` installed, no version conflicts |
| T006 | FR-001, FR-002, FR-005, FR-006, FR-052 | plan.md Extension 1 | — | 10 diagram types render, errors shown inline, last valid SVG cached, theme sync |
| T007 | FR-004 | plan.md Extension 1 | — | `language: 'mermaid'` detected, source/preview toggle works |
| T008 | FR-001 through FR-006 | plan.md Extension 1 | Scenario 1 | Mermaid.render() -> SVG, 300ms debounce, error display, last valid cache |
| T009 | FR-004 | plan.md Extension 1 | Scenario 1 | CodeBlock detects mermaid, renders preview above source |
| T010 | FR-003 | plan.md Extension 1 | — | SVG node click -> tooltip + "Link to Issue" action |
| T011 | FR-012 | plan.md Extension 1 | — | SVG -> Canvas -> PNG export |
| T012 | FR-010 | plan.md slash commands | Scenario 1 | `/diagram` inserts codeBlock with `language: 'mermaid'` |
| T013 | FR-007 | plan.md Skill Updates, research.md R-001 | Scenario 2 | Skill outputs `insert_block` call with mermaid markdown (not JSON) |
| T014 | spec.md Size Limits | plan.md Extension 1 | Scenario 4 | 500 lines / 200 nodes -> "Diagram too complex" fallback |

### Phase 3: Smart Checklist (P2)

| Task | Spec Ref | Plan Ref | Quickstart | Validates |
|------|----------|----------|------------|-----------|
| T015 | FR-013 through FR-018 | plan.md Extension 2 | — | Extended attrs serialize/parse correctly |
| T016 | FR-014 through FR-018 | plan.md Extension 2 | — | Assignee picker, date picker, priority badge, optional style, conditional grey-out |
| T017 | FR-019 | plan.md Extension 2 | — | Progress = checkedRequired / totalRequired * 100 |
| T018 | FR-013 through FR-018 | plan.md Extension 2 | Scenario 3 | TaskItem.extend() with 6 new attrs |
| T019 | FR-014 through FR-018 | plan.md Extension 2 | Scenario 3 | Assignee avatar, date badge (red if overdue), priority badge, dashed border (optional) |
| T020 | FR-019 | plan.md Extension 2 | Scenario 3 | Progress bar above TaskList, optional items excluded |
| T021 | FR-045 | plan.md createEditorExtensions.ts | — | TaskItemEnhanced replaces default TaskItem, before BlockIdExtension |
| T022 | FR-026 | plan.md slash commands | Scenario 3 | `/checklist` inserts TaskList with 3 sample items |
| T023 | FR-049 | spec.md WCAG 2.2 AA | — | Arrow keys navigate, Space toggles, Tab indents |

### Phase 4: Decision Record (P2)

| Task | Spec Ref | Plan Ref | Quickstart | Validates |
|------|----------|----------|------------|-----------|
| T024 | FR-044, FR-048 | plan.md Extension 3 | — | PMBlock node: blockType enum, data JSON string, userEdited boolean |
| T025 | FR-020 through FR-024 | plan.md Extension 3 | — | State machine transitions, option cards, rationale, issue creation |
| T026 | FR-044 | plan.md Extension 3 | Scenario 5 | PMBlock node registered: group: 'block', atom: true |
| T027 | FR-044 | plan.md Extension 3 | — | ReactNodeViewRenderer dispatches by blockType |
| T028 | FR-020 through FR-023 | plan.md DecisionRenderer | Scenario 5 | Open/Decided/Superseded UI, "Decide" button, rationale field, summary banner |
| T029 | FR-022 | plan.md OptionCard | Scenario 5 | Label, description, pros/cons, effort, risk per option |
| T030 | FR-024 | plan.md DecisionRenderer | Scenario 5 | issuesApi.create() with context, ID linked back to decision |
| T031 | FR-045 | plan.md createEditorExtensions.ts | — | PMBlockExtension before BlockIdExtension |
| T032 | FR-044 | plan.md BlockIdExtension | — | pmBlock added to block type list |
| T033 | FR-026 | plan.md slash commands | Scenario 5 | `/decision` inserts PMBlock with blockType: 'decision' |

### Phase 5: Agent Integration P1+P2

| Task | Spec Ref | Plan Ref | Quickstart | Validates |
|------|----------|----------|------------|-----------|
| T034 | FR-007, FR-025, FR-048 | plan.md System Prompt Changes, research.md §1 | Scenario 2 | SYSTEM_PROMPT_BASE +120 tokens, PM block section, edit guard rule |
| T035 | FR-007, FR-025 | plan.md Operational Rules, research.md §3 | Scenario 2 | PM Block Types section, trigger keywords, agent rules |
| T036 | FR-025 | plan.md Role Template Updates, research.md §5 | — | project_manager.md, architect.md, tech_lead.md updated |
| T037 | FR-007, FR-025, FR-048 | plan.md Agent Integration | Scenario 2 | Agent calls insert_block for diagrams/checklists/decisions, edit guard works |
| T038 | spec.md T-002 | plan.md Skills | — | Sprint planning template: Gantt + checklist + DoD + decision |
| T039 | spec.md T-003 | plan.md Skills | — | ADR lite template: decision + architecture diagram |

### Phase 6: Form + RACI + Risk (P3)

| Task | Spec Ref | Plan Ref | Quickstart | Validates |
|------|----------|----------|------------|-----------|
| T040 | FR-027 through FR-029 | plan.md Extension 3 | — | Form field rendering, response storage, validation |
| T041 | FR-027 through FR-029 | plan.md FormRenderer | Scenario 6 | Fields from data.fields[], responses in data.responses{} |
| T042 | FR-028 | plan.md FormField | Scenario 6 | 10 field types: short-text, long-text, dropdown, multi-select, date, rating, number, member, toggle, file-ref |
| T043 | FR-035 | plan.md slash commands | Scenario 6 | `/form` inserts PMBlock with blockType: 'form' |
| T044 | FR-030, FR-031 | plan.md Extension 3 | — | Matrix grid, cell click, exactly-one-A validation |
| T045 | FR-030, FR-031 | plan.md RACIRenderer | — | Deliverable rows, stakeholder columns, R/A/C/I dropdown, A-constraint error |
| T046 | FR-035 | plan.md slash commands | — | `/raci` inserts PMBlock with blockType: 'raci' |
| T047 | FR-032, FR-033 | plan.md Extension 3 | — | Risk rows, P*I score, color coding |
| T048 | FR-032, FR-033 | plan.md RiskRenderer | Scenario 7 | Probability/impact inputs, auto-score, green/yellow/red, strategy/owner/trigger |
| T049 | FR-035 | plan.md slash commands | Scenario 7 | `/risk-register` inserts PMBlock with blockType: 'risk-register' |
| T050 | FR-034 | plan.md Operational Rules | — | Form/RACI/Risk triggers, devops.md update |
| T051 | spec.md T-004 through T-007 | plan.md Skills | — | 4 template skills: adr-full, release-readiness, sprint-retro, project-kickoff |
| T052 | FR-034 | plan.md Agent Integration | — | Agent triggers for form/RACI/risk verified |

### Phase 7: Viz + Timeline + Dashboard (P4)

| Task | Spec Ref | Plan Ref | Quickstart | Validates |
|------|----------|----------|------------|-----------|
| T053 | — | plan.md RD-005 | — | `echarts` + `echarts-for-react` installed |
| T054 | FR-036, FR-037 | plan.md Extension 1 | — | ECharts renders in iframe, sandbox isolation |
| T055 | FR-037 | plan.md VizSandbox, research.md R-010 | Scenario 8 | iframe srcdoc, sandbox="allow-scripts", CSP, postMessage, 5s timeout |
| T056 | FR-036 | plan.md EChartsPreview | Scenario 8 | ECharts config from code block, rendered in sandbox |
| T057 | FR-036 | plan.md Extension 1 | — | echarts-* language detection in CodeBlockExtension |
| T058 | FR-043 | plan.md slash commands | Scenario 8 | `/chart` inserts codeBlock with echarts-* language |
| T059 | FR-039, FR-040 | plan.md Extension 3 | — | Timeline rendering, dependency arrows, keyboard |
| T060 | FR-039, FR-040 | plan.md TimelineRenderer | — | SVG timeline, drag-to-reschedule, Ctrl+Arrow |
| T061 | FR-043 | plan.md slash commands | — | `/timeline` inserts PMBlock with blockType: 'timeline' |
| T062 | FR-041 | plan.md Extension 3 | — | KPI widgets, cycle data, 30s polling |
| T063 | FR-041 | plan.md DashboardRenderer | — | Widgets, cycle data fetch, SPI/CPI gauges |
| T064 | FR-043 | plan.md slash commands | — | `/dashboard` inserts PMBlock with blockType: 'dashboard' |
| T065 | FR-042 | plan.md Skills, research.md R-009 | — | Aggregate forms across notes, < 10s for 50 notes |
| T066 | FR-043 | plan.md Operational Rules | — | Viz/timeline/dashboard triggers |
| T067 | spec.md T-008, T-009 | plan.md Skills | — | WBS + sprint-retro-enhanced templates |
| T068 | FR-036 through FR-043 | plan.md Agent Integration | Scenario 8 | Viz/timeline/dashboard Agent triggers + aggregation |

### Phase Final: Polish

| Task | Spec Ref | Plan Ref | Quickstart | Validates |
|------|----------|----------|------------|-----------|
| T069 | FR-049, FR-050 | spec.md WCAG 2.2 AA | — | role="region", aria-label on all PM blocks |
| T070 | FR-049 | spec.md WCAG 2.2 AA | — | prefers-reduced-motion respected |
| T071 | FR-051 | spec.md WCAG 2.2 AA | — | 4.5:1 contrast in all PM blocks |
| T072 | FR-054 | spec.md Copy/Paste behavior | — | Assignees cleared (checklist), issue IDs cleared (decision), responses cleared (form) |
| T073 | FR-055 | spec.md Export behavior | — | Diagrams/viz -> image, checklists -> markdown, PMBlocks -> structured text |
| T074 | FR-057 | plan.md Cross-Cutting | — | Template insertions grouped as single undo via editor.chain() |
| T075 | SC-001 through SC-010 | quickstart.md | All 8 | All quickstart scenarios pass |
| T076 | Constitution | — | — | All PM block files < 700 lines |
| T077 | Quality Gates | — | — | `pnpm lint && pnpm type-check && pnpm test` all pass |
| T078 | Quality Gates | — | — | `uv run pyright && uv run ruff check && uv run pytest --cov=.` all pass |

---

## Risk Validation Checklist

Before marking any phase complete, verify these risks are mitigated:

### DANGER Risks (Must resolve before proceeding)

- [ ] **R-001**: `generate-diagram` skill updated from JSON output to mermaid markdown + `insert_block` instruction (T013)
- [ ] **R-002**: NoteCanvas.tsx split to < 500 lines (T001) — blocks all Phase 2+ work

### WATCH Risks (Monitor during implementation)

- [ ] **R-003**: PMBlock content uses `content` JSON field (not markdown) for Decision/Form/RACI/Risk/Timeline/Dashboard
- [ ] **R-004**: Enhanced TaskItem uses plain markdown for Agent delivery (assignee/date set manually by user)
- [ ] **R-005**: System prompt total < 2.5K tokens after PM additions (monitor in T034)
- [ ] **R-006**: Agent auto-insertion undo rate tracked (target < 30%, SC-002)
- [ ] **R-007**: All 4 role templates updated with PM block awareness (T036, T050)
- [ ] **R-008**: Slash command items grouped under "PM Blocks" category to avoid dropdown clutter

### UNKNOWN Risks (Verify during later phases)

- [ ] **R-009**: Cross-note form aggregation < 10s for 50 notes (T065, P4)
- [ ] **R-010**: ECharts iframe sandbox prevents cross-origin access (T055, P4)
- [ ] **R-011**: Conditional TaskItem visibility performant with 200 items (T018, P2)

---

## Cross-Artifact Consistency Checks

Run after completing each phase:

1. **spec.md <-> plan.md**: Every FR-NNN has an approach in plan.md Requirements-to-Architecture mapping
2. **plan.md <-> tasks.md**: Every approach has implementing tasks in tasks.md
3. **tasks.md <-> quickstart.md**: Every phase checkpoint references correct quickstart scenarios
4. **plan.md <-> research.md**: Content transport strategy (RD-008) consistent across both
5. **spec.md <-> quickstart.md**: Quickstart scenarios cover all user stories (US-001 through US-010)

---

## Important: Update tasks.md as needed

You can update tasks.md to reflect changes in task order, parallelization, or newly discovered work. Then implement per this guide. Mark completed tasks with `[x]`.

# Research: PM Note Extensions — Agent Integration Deep Context

**Feature**: PM Note Extensions (013)
**Branch**: `013-pm-note-extensions`
**Created**: 2026-02-11
**Author**: Tin Dang

---

## Summary

This document captures the deep context analysis of integrating spec 013 PM Note Extensions with the Pilot Space Agent system. It traces the full path from Agent prompt → MCP tool → SSE event → Frontend TipTap mutation, identifying hidden couplings, contract boundaries, and risk areas.

**Scope**: 42 files analyzed across backend Agent layer and frontend content pipeline.

**Risk Summary**: 2 DANGER, 6 WATCH, 3 UNKNOWN.

---

## 1. System Prompt Architecture

### Current State

**Static base** (`pilotspace_agent.py:110-136`):
- `SYSTEM_PROMPT_BASE` is a class-level string constant on `PilotSpaceAgent`
- Defines tool categories (33 tools), approval tiers, entity resolution, subagent list
- **No PM block awareness** — no mention of diagrams, checklists, decisions, forms, RACI, risk registers

**Dynamic assembly** (`pilotspace_stream_utils.py:424-468`):
- `build_dynamic_system_prompt(base, role_type, workspace_name, project_names)` composes:
  1. Static `SYSTEM_PROMPT_BASE`
  2. Role template from `templates/role_templates/{role_type}.md` (8 roles)
  3. Workspace context (name + project names)
  4. Operational rules from `templates/rules/` (notes.md, issues.md, ai-confidence.md)

**Key Insight**: Rules are loaded via `_load_rules()` which reads all `.md` files in `templates/rules/`. Adding PM block rules to `notes.md` or as a separate `pm-blocks.md` file will be auto-discovered.

### Block Types in Rules

**Current** (`templates/rules/notes.md:70-76`):
```
Block types: paragraph, heading, list, code, quote
```

**Needed**: Add `mermaid` (code block variant), `taskList` (enhanced), `pmBlock` (generic: decision, form, raci, risk-register, timeline, dashboard)

### Token Budget Impact [WATCH]

- System prompt base: ~350 tokens
- Role template: ~300-500 tokens
- Workspace context: ~50 tokens
- Operational rules (current): ~800 tokens
- **PM block rules addition**: Estimated +400-600 tokens
- **Total after PM rules**: ~2,000-2,300 tokens of system prompt

Session budget is 8K tokens (per `pilotspace_agent.py` constant). System prompt consuming ~2.3K leaves ~5.7K for conversation — sufficient but warrants monitoring.

---

## 2. Content Pipeline: Agent → Frontend

### Full Trace

```
Agent decides to insert PM block
  ↓
Agent calls MCP tool (note_server.py or note_content_server.py)
  • write_to_note(note_id, markdown) → append_blocks payload
  • insert_block(note_id, content_markdown, after_block_id) → insert_blocks payload
  ↓
Tool returns JSON operation payload:
  {"status": "pending_apply", "operation": "insert_blocks",
   "note_id": "...", "content_markdown": "...", "after_block_id": "..."}
  ↓
transform_user_message_tool_results() in pilotspace_note_helpers.py
  → emit_insert_blocks_event() or emit_append_blocks_event()
  ↓
SSE event emitted:
  event: content_update
  data: {"noteId": "...", "operation": "insert_blocks",
         "markdown": "```mermaid\nflowchart TD\n...\n```",
         "blockId": null, "afterBlockId": "¶3", ...}
  ↓
Frontend PilotSpaceStreamHandler processes SSE event
  → buffers in PilotSpaceStore.pendingContentUpdates[]
  ↓
useContentUpdates hook consumes from buffer (by noteId)
  → dispatches to contentUpdateHandlers.ts
  ↓
handleInsertBlocks(editor, update) or handleAppendBlocks(editor, update)
  → editor.commands.insertContentAt(pos, markdown, {parseOptions})
  ↓
TipTap parses markdown → creates node(s) in ProseMirror doc
  → BlockIdExtension assigns UUID to new nodes
  → Auto-save triggers (2s debounce)
```

### SSE Contract: ContentUpdateData [SAFE]

**File**: `frontend/src/stores/ai/types/events.ts:302-351`

```typescript
interface ContentUpdateData {
  noteId: string;
  operation: 'replace_block' | 'append_blocks' | 'insert_blocks'
           | 'remove_block' | 'insert_inline_issue'
           | 'remove_content' | 'replace_content';
  blockId: string | null;
  markdown: string | null;       // Preferred — Agent sends markdown
  content: Record<string, unknown> | null;  // Fallback — TipTap JSON
  issueData: {...} | null;
  afterBlockId: string | null;
  beforeBlockId?: string | null;
  pattern?: string | null;
  oldPattern?: string | null;
  newContent?: string | null;
  blockIds?: string[];
}
```

**Finding**: The `markdown` field is the primary content carrier. Agent-generated mermaid code blocks (` ```mermaid\n...\n``` `) will be sent as markdown strings. Frontend parses markdown → TipTap nodes. **No SSE schema changes needed.**

### Content Handler Functions [SAFE for P1, WATCH for P2+]

**File**: `frontend/src/features/notes/editor/hooks/contentUpdateHandlers.ts`

Functions: `handleReplaceBlock`, `handleAppendBlocks`, `handleInsertBlocks`, `handleInsertInlineIssue`, `handleRemoveBlock`

**P1 (Diagrams)**: Mermaid code blocks are standard markdown (` ```mermaid `) → parsed by existing CodeBlockExtension → no handler changes needed. [SAFE]

**P2 (Smart Checklist)**: Enhanced TaskItem with extra attrs (assignee, dueDate, priority). The Agent generates markdown task lists: `- [ ] Item @assignee 📅2026-03-01`. The frontend must parse these extended attrs from markdown. **The existing handler passes markdown to `editor.commands.insertContentAt()` which uses TipTap's markdown parser** — needs custom parsing for the extended task syntax. [WATCH]

**P2 (Decision Record) / P3 (Form, RACI, Risk)**: PMBlock nodes are NOT standard markdown. Agent must send either:
  - (a) TipTap JSON in the `content` field (bypasses markdown parsing), or
  - (b) A custom markdown pattern (e.g., `:::decision\n{JSON data}\n:::`) that a custom input rule parses

**Decision needed**: Plan says "Agent generates markdown patterns" (RD-007). The frontend content handler already supports both `markdown` and `content` (JSON) fields. For PMBlock, using the `content` JSON field is simpler and more reliable than inventing a markdown pattern. [WATCH — needs decision confirmation]

---

## 3. MCP Tool Analysis

### insert_block Tool [SAFE]

**File**: `backend/src/pilot_space/ai/mcp/note_content_server.py:259-330`

```python
@tool()
async def insert_block(note_id: str, content_markdown: str,
                       after_block_id: str | None, before_block_id: str | None):
    return {"status": "pending_apply", "operation": "insert_blocks",
            "note_id": note_id, "content_markdown": content_markdown, ...}
```

**Finding**: `insert_block` accepts any markdown string. Agent can pass:
- ` ```mermaid\nflowchart TD\nA-->B\n``` ` for diagrams
- Markdown task lists for checklists
- Any content — the tool is content-agnostic

**No MCP tool changes needed.** [SAFE]

### write_to_note Tool [SAFE]

**File**: `backend/src/pilot_space/ai/mcp/note_server.py:222-262`

Appends markdown to end of note. Same content-agnostic behavior.

### Content Update Transform [SAFE]

**File**: `backend/src/pilot_space/ai/agents/pilotspace_note_helpers.py`

Functions: `emit_append_blocks_event()`, `emit_insert_blocks_event()`, `emit_replace_block_event()`

These functions convert operation payloads to SSE `content_update` events. They pass the markdown string through without interpretation. **No backend transform changes needed.**

---

## 4. Skill System

### generate-diagram Skill [DANGER]

**File**: `backend/src/pilot_space/ai/templates/skills/generate-diagram/SKILL.md`

**Current output format**:
```json
{
  "diagram_type": "sequence",
  "mermaid_code": "sequenceDiagram\n    actor User\n    ...",
  "confidence": "RECOMMENDED",
  "preview_url": "/api/diagrams/preview?code=..."
}
```

**Problem**: The plan (RD-007) says the Agent should output mermaid markdown via `insert_block`. But the current skill outputs structured JSON that is NOT compatible with the `insert_block` tool. The skill teaches the Agent to produce JSON, but the tool expects markdown.

**Resolution**: Update the skill to instruct the Agent to:
1. Generate the mermaid syntax
2. Call `insert_block` with ` ```mermaid\n{syntax}\n``` ` as `content_markdown`
3. Include confidence tag in the chat response (not in the block content)

**Risk**: If the skill is not updated, the Agent will generate JSON diagrams that don't render. [DANGER]

### Skill Discovery Mechanism [SAFE]

**File**: `backend/src/pilot_space/ai/skills/skill_discovery.py`

Auto-discovers `SKILL.md` files from `.claude/skills/` directory. New skills (sprint-planning, adr-lite, aggregate-forms) will be auto-discovered if placed in the correct directory structure. [SAFE]

---

## 5. Role Templates

### project_manager.md [WATCH]

**File**: `backend/src/pilot_space/ai/templates/role_templates/project_manager.md`

Current PM role template focuses on:
- Delivery tracking, risk management, dependency management
- Sprint planning guidance, status reporting
- PM vocabulary (milestone, critical path, burndown)

**Missing**: No awareness of PM blocks. PM users are the primary persona for spec 013. Template should reference:
- `/checklist` for sprint backlogs and DoD
- `/decision` for go/no-go gates
- `/risk-register` for risk assessments
- `/raci` for responsibility matrices
- Diagrams for Gantt charts and architecture

### architect.md [WATCH]

Should reference:
- `/diagram` for architecture diagrams (C4, sequence, class, ER)
- `/decision` for ADR blocks

### tech_lead.md [WATCH]

Should reference:
- Sprint planning templates (T-002)
- `/checklist` for sprint backlogs

### Other templates [SAFE]

`developer.md`, `devops.md`, `tester.md`, `product_owner.md`, `business_analyst.md` — lower priority, minimal changes.

---

## 6. Frontend Extension Loading [WATCH]

### createEditorExtensions.ts

**Current extension order** (13 extensions):
```
1. BlockIdExtension       (MUST be last — assigns IDs after all other processing)
2. GhostTextExtension
3. AnnotationMark
4. MarginAnnotationExtension
5. MarginAnnotationAutoTriggerExtension
6. IssueLinkExtension
7. InlineIssueExtension
8. CodeBlockExtension     ← Enhanced for mermaid (P1)
9. MentionExtension
10. SlashCommandExtension  ← New PM slash commands added here
11. ParagraphSplitExtension
12. AIBlockProcessingExtension
13. LineGutterExtension
```

**FR-045 Requirement**: PM blocks MUST load BEFORE BlockIdExtension.

**Finding**: BlockIdExtension is already last (position 1 in the list, but registered last in the array). New extensions (PMBlockExtension, TaskItemEnhanced) should be added BEFORE BlockIdExtension. [SAFE — architecture already supports this]

### NoteCanvas.tsx Size [DANGER]

**PRE-001**: NoteCanvas.tsx is at 702 lines (exceeds 700-line limit). Must be split before adding PM block rendering logic.

**Risk**: If PRE-001 is not completed first, adding PM blocks will push NoteCanvas further over the limit, triggering pre-commit hook failures and blocking all commits. [DANGER — blocks Phase 1]

---

## 7. Auto-Save Compatibility [SAFE]

PM blocks store data in TipTap's JSON document format:
- Mermaid diagrams: `codeBlock` node with `language: 'mermaid'` — already auto-saved
- Smart Checklists: `taskItem` nodes with extended attrs — new attrs auto-serialized by TipTap
- PMBlocks: `pmBlock` node with `blockType` + `data` attrs — TipTap auto-serializes attrs

The auto-save hook (`useAutoSave`, 2s debounce) calls `editor.getJSON()` which serializes ALL node types and their attrs. **No auto-save changes needed.** [SAFE]

---

## 8. Approval Workflow (DD-003) [SAFE]

PM block insertions are **additive** (non-destructive):
- Agent inserts new blocks → auto-execute (no approval needed)
- Undo available via Ctrl+Z → user can revert

Per DD-003 classification:
- `insert_block`: non-destructive → auto-execute
- `write_to_note`: non-destructive → auto-execute

**FR-047 compliance**: Agent insertions of PM blocks don't require human approval. [SAFE]

---

## 9. Implementation Risks

| # | Risk | Severity | Impact | Mitigation |
|---|------|----------|--------|------------|
| R-001 | `generate-diagram` skill output format incompatible with `insert_block` | DANGER | Agent produces JSON instead of markdown → diagrams don't render | Update skill output format to mermaid markdown (T013) |
| R-002 | NoteCanvas.tsx at 702 lines blocks all PM work | DANGER | Pre-commit hook rejects changes to NoteCanvas | Complete PRE-001 canvas refactor before Phase 1 |
| R-003 | PMBlock content format (markdown vs JSON) undefined | WATCH | Agent may generate unrecognized markdown patterns | Decision: use `content` JSON field for PMBlocks, `markdown` for diagrams/checklists |
| R-004 | Enhanced TaskItem markdown parsing | WATCH | Extended attrs (assignee, date) not parsed from markdown | Define markdown syntax for enhanced task items or use JSON content field |
| R-005 | System prompt token growth | WATCH | PM rules add ~500 tokens to system prompt | Keep rules concise; monitor token budget |
| R-006 | Agent over-triggers PM block insertion (SC-002: undo rate > 30%) | WATCH | Users annoyed by unwanted blocks | Conservative trigger keywords; tune after feedback |
| R-007 | Role templates not updated for PM blocks | WATCH | PM/Architect users don't get PM block suggestions | Update role templates in Phase 2 (T035-T036) |
| R-008 | Slash command items list grows large | WATCH | SlashCommandExtension dropdown gets unwieldy | Group PM commands under a "PM Blocks" category |
| R-009 | Cross-note form aggregation performance (SC-006) | UNKNOWN | Agent reads 50+ notes sequentially → may exceed 10s | Unknown until P4; may need metadata index |
| R-010 | ECharts sandbox security (FR-037) | UNKNOWN | iframe srcdoc isolation effectiveness | Needs security review in P4 |
| R-011 | Conditional TaskItem visibility performance | UNKNOWN | 200 items with conditional parents → rendering overhead | Needs benchmarking in P2 |

---

## 10. Key Decisions Required

### RD-008: PMBlock Content Transport

**Options**:
- (a) **Markdown pattern**: Agent sends `:::decision\n{JSON}\n:::` as markdown → frontend custom input rule parses
- (b) **JSON content field**: Agent sends TipTap JSONContent in `content` field → frontend directly inserts node
- (c) **Hybrid**: Diagrams use markdown (` ```mermaid `), checklists use markdown (task lists), PMBlocks use JSON content

**Recommendation**: **(c) Hybrid** — leverage existing markdown parsing for standard nodes (code blocks, task lists), use JSON content for custom PMBlock nodes (no markdown representation exists for decision records, forms, RACI matrices).

**Rationale**: Inventing a markdown syntax for complex PMBlocks is fragile and requires custom parsing. TipTap's `insertContentAt()` already accepts JSONContent. The SSE contract already has a `content` field for this purpose.

### RD-009: Enhanced TaskItem Markdown Syntax

**Options**:
- (a) **Plain task list**: Agent sends `- [ ] Review PR` → frontend parses as standard TaskItem, user adds assignee/date manually
- (b) **Extended syntax**: Agent sends `- [ ] Review PR @alice 📅2026-03-01 🔴high` → frontend custom parser extracts attrs
- (c) **JSON content**: Agent sends TaskItem as JSONContent with attrs → bypasses markdown

**Recommendation**: **(a) Plain task list for MVP**, then **(b) Extended syntax** if Agent-populated metadata proves valuable. Start simple, iterate.

**Rationale**: Markdown task lists work out of the box. Extended syntax requires a custom TipTap input rule or post-parse transform. Defer complexity until user demand is validated.

---

## 11. Files-to-Change Matrix

### Phase 1 (Diagrams)

| File | Change | Risk |
|------|--------|------|
| `backend/.../templates/skills/generate-diagram/SKILL.md` | Update output format: JSON → mermaid markdown + `insert_block` call instruction | DANGER (R-001) |
| `backend/.../templates/rules/notes.md` | Add diagram block type + auto-detection trigger rules | WATCH (R-005) |
| `backend/.../agents/pilotspace_agent.py` | Update `SYSTEM_PROMPT_BASE`: add mermaid code block awareness | SAFE |
| `frontend/.../extensions/CodeBlockExtension.ts` | Enhance: detect `language: 'mermaid'` → render MermaidPreview | Phase 1 core |
| `frontend/.../extensions/slash-command-items.ts` | Add `/diagram` command | SAFE |
| `frontend/.../editor/hooks/contentUpdateHandlers.ts` | No changes needed (markdown passthrough) | SAFE |

### Phase 2 (Checklist + Decision)

| File | Change | Risk |
|------|--------|------|
| `backend/.../templates/rules/notes.md` | Add checklist/decision detection rules | WATCH (R-005) |
| `backend/.../templates/role_templates/project_manager.md` | Add PM block awareness | WATCH (R-007) |
| `backend/.../templates/role_templates/architect.md` | Add ADR + diagram awareness | WATCH (R-007) |
| `backend/.../templates/role_templates/tech_lead.md` | Add sprint planning awareness | WATCH (R-007) |
| `frontend/.../extensions/pm-blocks/TaskItemEnhanced.ts` | TaskItem.extend() with new attrs | Phase 2 core |
| `frontend/.../extensions/pm-blocks/PMBlockExtension.ts` | New generic PM node | Phase 2 core |
| `frontend/.../extensions/slash-command-items.ts` | Add `/checklist`, `/decision` | SAFE |
| `frontend/.../extensions/createEditorExtensions.ts` | Register new extensions before BlockIdExtension | SAFE |

### Phase 3 (Form + RACI + Risk)

| File | Change | Risk |
|------|--------|------|
| `backend/.../templates/rules/notes.md` | Add form/RACI/risk detection rules | WATCH (R-005) |
| `frontend/.../extensions/pm-blocks/renderers/*.tsx` | FormRenderer, RACIRenderer, RiskRenderer | Phase 3 core |
| `frontend/.../extensions/slash-command-items.ts` | Add `/form`, `/raci`, `/risk-register` | SAFE |

### Phase 4 (Viz + Timeline + Dashboard)

| File | Change | Risk |
|------|--------|------|
| `backend/.../templates/skills/aggregate-forms/SKILL.md` | New skill for cross-note aggregation | Phase 4 core |
| `backend/.../templates/rules/notes.md` | Add viz/timeline/dashboard triggers | WATCH (R-005) |
| `frontend/.../extensions/pm-blocks/EChartsPreview.tsx` | ECharts iframe sandbox | UNKNOWN (R-010) |
| `frontend/.../extensions/pm-blocks/renderers/*.tsx` | TimelineRenderer, DashboardRenderer | Phase 4 core |
| `frontend/.../extensions/slash-command-items.ts` | Add `/chart`, `/timeline`, `/dashboard` | SAFE |

---

## 12. Validation Checklist

- [x] System prompt composition traced (base + role + workspace + rules)
- [x] MCP tool contract verified (insert_block accepts any markdown)
- [x] SSE event schema verified (ContentUpdateData supports markdown + JSON content)
- [x] Frontend content handlers traced (5 handlers, markdown passthrough)
- [x] Auto-save compatibility confirmed (TipTap JSON serialization handles all node types)
- [x] Approval workflow compliance verified (DD-003: PM insertions are non-destructive)
- [x] Extension loading order analyzed (BlockIdExtension last — correct for FR-045)
- [x] Skill discovery mechanism verified (auto-discovery from .claude/skills/)
- [x] Token budget estimated (system prompt ~2.3K of 8K budget)
- [x] NoteCanvas file size risk identified (702 lines — PRE-001 blocker)
- [x] generate-diagram skill incompatibility identified (DANGER)
- [x] PMBlock transport mechanism analyzed (hybrid: markdown for standard nodes, JSON for custom)

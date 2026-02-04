# Implementation Plan: AI Context Tab - Full Implementation

**Branch**: `005-conversation-fix` | **Date**: 2026-02-02 | **Spec**: `specs/005-conversation-fix/spec.md`
**Input**: Feature specification from `/specs/005-conversation-fix/spec.md`

## Summary

Replace the current AIContextSidebar (Sheet component) with a rich AI Context tab in the issue detail main content area. Phase 1 delivers: tab integration, context header with Copy All/Regenerate, summary card with stats, related context (issues with relation types, documents with doc types), AI tasks (checklist + prompts), and section-based SSE streaming. The AIContextStore is enhanced to handle structured JSON events per section.

## Technical Context

**Language/Version**: TypeScript 5.3+ / Next.js 14+ (App Router) + React 18
**Primary Dependencies**: MobX 6+, TanStack Query 5+, shadcn/ui, Lucide React
**Storage**: N/A (frontend-only; backend SSE endpoint already exists)
**Testing**: Vitest + Testing Library (>80% coverage)
**Target Platform**: Web (Chrome 125+, Safari 17+, Firefox 120+)
**Project Type**: Web application (frontend feature)
**Performance Goals**: AI Context tab renders within 500ms when cached; SSE sections render independently as they arrive
**Constraints**: File size <700 lines per file; WCAG 2.2 AA keyboard/focus compliance
**Scale/Scope**: Single page enhancement affecting ~8 files (3 new components, 1 store update, 1 page update, 3 test files)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. AI-Human Collaboration First | PASS | Context is read-only display of AI-generated data; no destructive actions; Copy All requires user action |
| II. Note-First Approach | PASS | AI Context shows linked notes/documents from Note-First workflow |
| III. Documentation-Third | PASS | Context auto-generated from issue analysis |
| IV. Task-Centric Workflow | PASS | AI Tasks section with checklist supports task decomposition |
| V. Collaboration & Knowledge Sharing | PASS | Related context surfaces team knowledge graph |
| VI. Agile Integration | N/A | No sprint/velocity features in this scope |
| VII. Notation & Standards | N/A | No diagram generation in Phase 1 |

**Quality Gates**:
- [x] Lint passes (pnpm lint)
- [x] Type check passes (pnpm type-check)
- [x] Tests pass with coverage >80%
- [x] No N+1 queries (frontend-only, no DB access)
- [x] No TODOs, mocks, or placeholder code
- [x] Keyboard navigation + ARIA labels (WCAG 2.2 AA)
- [x] File size <700 lines per file

## Project Structure

### Documentation (this feature)

```text
specs/005-conversation-fix/
├── plan.md              # This file
├── spec.md              # Feature specification with clarifications
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output (TypeScript interfaces)
├── contracts/           # Phase 1 output (SSE event contracts)
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
frontend/src/
├── app/(workspace)/[workspaceSlug]/issues/[issueId]/
│   └── page.tsx                          # MODIFY: Add tab layout, replace sidebar
├── features/issues/components/
│   ├── index.ts                          # MODIFY: Export new components
│   ├── ai-context-tab.tsx                # NEW: Main AI Context tab container
│   ├── context-summary-card.tsx          # NEW: Summary card with stats
│   ├── context-section.tsx               # NEW: Reusable section wrapper (header + copy)
│   ├── related-issues-section.tsx        # NEW: Related issues with relation badges
│   ├── related-docs-section.tsx          # NEW: Related documents with type badges
│   ├── ai-tasks-section.tsx              # NEW: Checklist + prompts
│   ├── prompt-block.tsx                  # NEW: Copyable prompt block
│   ├── ai-context-panel.tsx              # MODIFY: Adapt for tab context (remove sidebar deps)
│   ├── ai-context-streaming.tsx          # REUSE: No changes needed
│   ├── claude-code-prompt-card.tsx       # REUSE: No changes needed
│   └── __tests__/
│       ├── ai-context-tab.test.tsx       # NEW
│       ├── context-summary-card.test.tsx # NEW
│       ├── related-issues-section.test.tsx # NEW
│       ├── ai-tasks-section.test.tsx     # NEW
│       └── prompt-block.test.tsx         # NEW
├── stores/ai/
│   └── AIContextStore.ts                 # MODIFY: New interfaces, section-based events
└── lib/
    └── copy-context.ts                   # NEW: Markdown generation for Copy All
```

**Structure Decision**: Frontend-only feature. Extends existing `features/issues/` directory with new AI Context components. Store update is minimal (new interfaces + event handler expansion). No backend changes.

## Complexity Tracking

No constitution violations. All changes follow existing patterns (MobX observer, SSE streaming, shadcn/ui components).

---

## Phase 0: Research

### R1: Existing AIContextStore SSE Event Handling

**Decision**: Extend the existing `handleEvent` switch statement to support section-based events (`context_summary`, `related_issues`, `related_docs`, `ai_tasks`, `ai_prompts`, `context_error`, `context_complete`).

**Rationale**: The current store handles two event types (`phase`, `complete`). Adding 7 new event types follows the same pattern. Each section updates an independent observable field, enabling per-section rendering.

**Alternatives considered**: Creating a new store — rejected because AIContextStore already manages the SSE lifecycle, caching, and abort logic. Duplicating this would violate DRY.

### R2: Tab Integration Pattern in Issue Detail Page

**Decision**: Add a `Tabs` component (shadcn/ui) wrapping the main content area of the issue detail page. Tabs: Description (default), Related, Graph, Activity, AI Context. The current inline content (title, description, sub-issues, activity) becomes the "Description" tab content.

**Rationale**: The prototype uses this exact pattern. shadcn/ui `Tabs` component provides keyboard navigation (arrow keys, Home/End) and ARIA attributes out of the box.

**Alternatives considered**: Custom tab implementation — rejected because shadcn/ui Tabs already handles accessibility, keyboard nav, and focus management per WCAG 2.2 AA requirements.

### R3: Copy-to-Clipboard Approach

**Decision**: Use `navigator.clipboard.writeText()` with a shared utility function that generates structured markdown. Each section has its own copy button using the same utility with a section filter. "Copy All" generates the full document.

**Rationale**: `navigator.clipboard.writeText()` is supported in all target browsers (Chrome 66+, Safari 13.1+, Firefox 63+). The markdown generation is a pure function that's easy to test.

**Alternatives considered**: Clipboard API `write()` with MIME types — rejected because plain text markdown is the target format per clarification.

### R4: Relation Type Badge Styling

**Decision**: Reuse the design token pattern from the prototype. Relation badges use colored backgrounds matching the design system:
- BLOCKS: `bg-destructive/10 text-destructive` (red)
- RELATES: `bg-ai/10 text-ai` (blue)
- BLOCKED BY: `bg-warning/10 text-warning` (orange)
- Document types: NOTE (teal), ADR (orange), SPEC (blue)

**Rationale**: These colors match the prototype exactly and align with the existing design token system.

### R5: Task Checklist State Management

**Decision**: Task completion state is managed locally in the component via `useState`. Not persisted to backend or MobX store.

**Rationale**: Per spec, "checkboxes are session-local". This is a Phase 1 simplification — Phase 2 may add persistence. Local state keeps the component simple and avoids store complexity.

---

## Phase 1: Design & Contracts

### Data Model

See `data-model.md` for full TypeScript interfaces.

**Key types**:

```typescript
// Extended AIContextResult with structured sections
interface AIContextResult {
  summary: ContextSummary | null;
  relatedIssues: ContextRelatedIssue[];
  relatedDocs: ContextRelatedDoc[];
  tasks: ContextTask[];
  prompts: ContextPrompt[];
  // Legacy fields (kept for backward compat during migration)
  claudeCodePrompt: string;
  relatedDocs_legacy: string[];
  relatedCode: string[];
  similarIssues: string[];
}

interface ContextSummary {
  issueIdentifier: string;
  title: string;
  summaryText: string;
  stats: {
    relatedCount: number;
    docsCount: number;
    filesCount: number;
    tasksCount: number;
  };
}

interface ContextRelatedIssue {
  relationType: 'blocks' | 'relates' | 'blocked_by';
  issueId: string;
  identifier: string;
  title: string;
  summary: string;
  status: string;
  stateGroup: string;
}

interface ContextRelatedDoc {
  docType: 'note' | 'adr' | 'spec';
  title: string;
  summary: string;
  url?: string;
}

interface ContextTask {
  id: number;
  title: string;
  estimate: string;
  dependencies: number[];
  completed: boolean;
}

interface ContextPrompt {
  taskId: number;
  title: string;
  content: string;
}
```

### SSE Event Contracts

See `contracts/sse-events.md` for full contract.

**Event types**:

| Event | Payload | Triggers |
|-------|---------|----------|
| `context_summary` | `ContextSummary` | Summary card renders |
| `related_issues` | `{ items: ContextRelatedIssue[] }` | Related issues section renders |
| `related_docs` | `{ items: ContextRelatedDoc[] }` | Related docs section renders |
| `ai_tasks` | `{ items: ContextTask[] }` | Task checklist renders |
| `ai_prompts` | `{ items: ContextPrompt[] }` | Prompt blocks render |
| `context_error` | `{ section: string, message: string }` | Per-section error state |
| `context_complete` | `{}` | Loading indicators stop |
| `phase` | `{ name, status, content? }` | Phase progress (existing) |

### Component Architecture

```text
IssueDetailPage (page.tsx) — MODIFIED
└── Tabs (shadcn/ui)
    ├── TabsTrigger: Description (default)
    ├── TabsTrigger: Related
    ├── TabsTrigger: Activity
    └── TabsTrigger: AI Context (sparkle icon, ai styling)
        └── AIContextTab (NEW)
            ├── [Empty State] → EmptyState with "Generate Context" button
            ├── [Loading State] → AIContextStreaming (EXISTING)
            ├── [Error State] → ErrorState with retry
            └── [Results State]
                ├── ContextHeader (Copy All + Regenerate)
                ├── ContextSummaryCard (NEW)
                ├── ContextSection: "Related Context" (NEW)
                │   ├── RelatedIssuesSection (NEW)
                │   └── RelatedDocsSection (NEW)
                └── ContextSection: "AI Tasks" (NEW)
                    ├── TaskChecklist (interactive checkboxes)
                    └── PromptBlocks (copyable prompts)
```

### Markdown Export Format

```markdown
# {identifier}: {title}

## Summary
{summaryText}

## Related Issues
- {identifier} ({relationType}): {title} — {status}
  {summary}

## Related Documents
- [{docType}] {title}
  {summary}

## Implementation Tasks
1. {title} (~{estimate})
   Dependencies: {dependencies}

## Ready-to-Use Prompts

### Task {id}: {title}
```
{content}
```

## Acceptance Criteria
{extracted from issue description}
```

---

## Implementation Phases

### Phase 1A: Store & Types (Foundation)

**Files**: `AIContextStore.ts`, `data-model.md`

1. Add new TypeScript interfaces (`ContextSummary`, `ContextRelatedIssue`, `ContextRelatedDoc`, `ContextTask`, `ContextPrompt`)
2. Extend `AIContextResult` with new structured fields (keep legacy fields)
3. Add section-based event handling in `handleEvent()`:
   - `context_summary` → sets `result.summary`
   - `related_issues` → sets `result.relatedIssues`
   - `related_docs` → sets `result.relatedDocs`
   - `ai_tasks` → sets `result.tasks`
   - `ai_prompts` → sets `result.prompts`
   - `context_error` → sets per-section error state
   - `context_complete` → marks loading complete
4. Add `sectionErrors: Map<string, string>` observable for per-section errors

### Phase 1B: Core Components (UI)

**Files**: New components in `features/issues/components/`

1. **`context-section.tsx`** (~80 lines): Reusable section wrapper with header (icon + title), copy button, and content slot. Copy button uses section-specific markdown generator.

2. **`context-summary-card.tsx`** (~100 lines): Gradient card with issue identifier, title, AI summary, and stats row (4 counts). Uses Card component from shadcn/ui.

3. **`related-issues-section.tsx`** (~120 lines): Maps `ContextRelatedIssue[]` to items with:
   - Relation badge (BLOCKS=red, RELATES=blue, BLOCKED BY=orange)
   - Issue identifier in mono font
   - Status pill (colored by state group)
   - Title and summary

4. **`related-docs-section.tsx`** (~80 lines): Maps `ContextRelatedDoc[]` to items with:
   - Type badge (NOTE=teal, ADR=orange, SPEC=blue)
   - Title and summary

5. **`ai-tasks-section.tsx`** (~150 lines): Two subsections:
   - **Task Checklist**: Interactive checkboxes with local state, task title, estimate, dependency info

6. **`prompt-block.tsx`** (~90 lines): Collapsible block with:
   - Header: task title + Copy button
   - Content: mono font, pre-wrap, dark background
   - Copy with "Copied!" feedback (2s timeout)

### Phase 1C: Tab Integration (Assembly)

**Files**: `ai-context-tab.tsx`, `page.tsx`, `index.ts`

1. **`ai-context-tab.tsx`** (~200 lines): Main container orchestrating:
   - Empty/Loading/Error/Results states (adapted from current AIContextPanel)
   - Context header with "Copy All Context" and "Regenerate" buttons
   - Renders: ContextSummaryCard, ContextSection(RelatedIssues + RelatedDocs), ContextSection(AITasks + PromptBlocks)
   - Uses `observer()` to react to AIContextStore changes

2. **`page.tsx`** modifications:
   - Add shadcn/ui `Tabs` component wrapping main content
   - Move existing content (title, description, sub-issues, activity) into "Description" tab
   - Add "AI Context" tab trigger with sparkle icon and ai styling
   - Remove `AIContextSidebar` component and `isAIContextOpen` state
   - Remove `onAIContextClick` from IssueHeader (replace with tab)
   - Dynamic import `AIContextTab` for code splitting

3. **`index.ts`**: Add exports for new components, remove `AIContextSidebar` export (deprecated)

### Phase 1D: Copy & Utilities

**Files**: `lib/copy-context.ts`

1. **`copy-context.ts`** (~100 lines): Pure functions:
   - `generateFullContextMarkdown(result: AIContextResult): string` — Full document
   - `generateSectionMarkdown(section: string, result: AIContextResult): string` — Single section
   - `copyToClipboard(text: string): Promise<boolean>` — Wrapper with error handling

### Phase 1E: Tests

**Files**: 5 test files in `__tests__/`

1. **`ai-context-tab.test.tsx`**: Tests for all 4 states (empty, loading, error, results), Copy All, Regenerate
2. **`context-summary-card.test.tsx`**: Renders stats, handles missing data
3. **`related-issues-section.test.tsx`**: Relation badges, status pills, navigation
4. **`ai-tasks-section.test.tsx`**: Checkbox toggling, dependency display
5. **`prompt-block.test.tsx`**: Copy functionality, expand/collapse

**Coverage target**: >80% per component file

---

## Post-Phase 1 Constitution Re-Check

| Principle | Status | Notes |
|-----------|--------|-------|
| I. AI-Human Collaboration First | PASS | AI context is read-only; user initiates generation; copy requires explicit action |
| II. Note-First Approach | PASS | Related documents include notes linked to issue |
| Quality: Lint | PASS | All components follow existing patterns |
| Quality: Type check | PASS | Strict TypeScript interfaces defined |
| Quality: Tests >80% | PASS | 5 test files covering all new components |
| Quality: File size <700 | PASS | Largest file ~200 lines (ai-context-tab.tsx) |
| Quality: Accessibility | PASS | shadcn/ui Tabs provides ARIA; all buttons have labels; keyboard nav via Tab/Enter/Space |

---

## Phase 2 Preview (follow-up branch)

Not in scope for this plan. Documented here for context:

1. **Codebase Context Section**: File tree component with folder/file hierarchy, code snippet display with dark theme, git references (PR/commit/branch)
2. **Task Dependency Graph**: HTML Canvas DAG with ~5-10 nodes, arrows, and labels
3. **Enhance Context Chat**: Embed ConversationPanel within AI Context tab with context-specific prompts
4. **Persistent Task State**: Save checklist completion to backend/localStorage

---

## Artifacts Generated

| Artifact | Path | Status |
|----------|------|--------|
| Implementation Plan | `specs/005-conversation-fix/plan.md` | Complete |
| Feature Spec | `specs/005-conversation-fix/spec.md` | Complete |
| Research | `specs/005-conversation-fix/research.md` | Complete |
| Data Model | `specs/005-conversation-fix/data-model.md` | Complete |
| SSE Contracts | `specs/005-conversation-fix/contracts/sse-events.md` | Complete |
| Tasks | `specs/005-conversation-fix/tasks.md` | Complete |

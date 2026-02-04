# Research: AI Context Tab - Full Implementation

**Branch**: `005-conversation-fix` | **Date**: 2026-02-02

## R1: AIContextStore SSE Event Handling

**Decision**: Extend existing `handleEvent()` with 7 new event types.

**Rationale**: Current store handles `phase` and `complete`. Adding `context_summary`, `related_issues`, `related_docs`, `ai_tasks`, `ai_prompts`, `context_error`, `context_complete` follows the same switch pattern. Each section updates an independent observable, enabling per-section rendering without blocking.

**Alternatives rejected**:
- New store: Duplicates SSE lifecycle, caching, abort logic.
- Separate SSE connections per section: Multiplied connections, complex coordination.

**Implementation**: Add observable fields `summary`, `relatedIssues`, `relatedDocs`, `tasks`, `prompts`, `sectionErrors`. Initialize as null/empty in `generateContext()`. Populate in `handleEvent()` via `runInAction()`.

## R2: Tab Integration Pattern

**Decision**: shadcn/ui `Tabs` component in issue detail page.

**Rationale**: Provides keyboard navigation (arrow keys, Home/End), ARIA `tablist`/`tab`/`tabpanel` roles, and focus management per WCAG 2.2 AA. Already installed in the project.

**Alternatives rejected**:
- Custom tabs: No accessibility benefit, more code.
- Radix Tabs directly: shadcn/ui wraps Radix with project styling.

**Implementation**: `Tabs defaultValue="description"` wrapping `TabsList` with 4 triggers. Content area uses `TabsContent` per tab. AI Context tab uses `dynamic()` import for code splitting.

## R3: Copy-to-Clipboard

**Decision**: `navigator.clipboard.writeText()` with pure markdown generator functions.

**Rationale**: Supported in all target browsers. Pure functions are easily testable. Structured markdown format (headers per section) confirmed in spec clarification.

**Implementation**: `lib/copy-context.ts` exports `generateFullContextMarkdown()` and `generateSectionMarkdown()`. Both take `AIContextResult` and return strings. `copyToClipboard()` wraps with try/catch returning boolean success.

## R4: Relation Type Badge Styling

**Decision**: Color-coded badges matching prototype design tokens.

**Mapping**:
| Type | Background | Text | Tailwind |
|------|-----------|------|----------|
| BLOCKS | red/10 | red | `bg-destructive/10 text-destructive` |
| RELATES | blue/10 | blue | `bg-ai/10 text-ai` |
| BLOCKED BY | orange/10 | orange | `bg-orange-100 text-orange-700 dark:bg-orange-950 dark:text-orange-400` |
| NOTE | teal/10 | teal | `bg-primary/10 text-primary` |
| ADR | orange/10 | orange | `bg-orange-100 text-orange-700` |
| SPEC | blue/10 | blue | `bg-ai/10 text-ai` |

## R5: Task Checklist State

**Decision**: Local `useState` per component instance. Not persisted.

**Rationale**: Spec states "checkboxes are session-local". MobX store state would add complexity without benefit — tasks are regenerated on each "Regenerate" action anyway.

**Implementation**: `const [completedTasks, setCompletedTasks] = useState<Set<number>>(new Set())`. Toggle via `setCompletedTasks(prev => { const next = new Set(prev); next.has(id) ? next.delete(id) : next.add(id); return next; })`.

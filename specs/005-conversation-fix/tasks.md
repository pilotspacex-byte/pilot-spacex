# Tasks: AI Context Tab - Full Implementation

**Source**: `/specs/005-conversation-fix/`
**Required**: plan.md, spec.md
**Optional**: research.md, data-model.md, contracts/

---

## Task Format

```
- [ ] [ID] [P?] [Story?] Description with exact file path
```

| Marker | Meaning |
|--------|---------|
| `[P]` | Parallelizable (different files, no dependencies) |
| `[USn]` | User story label (Phase 3+ only) |

---

## Phase 1: Setup

Project initialization — no new project scaffolding needed. This is a frontend-only feature extending an existing Next.js codebase.

- [ ] T001 Add TypeScript interfaces (ContextSummary, ContextRelatedIssue, ContextRelatedDoc, ContextTask, ContextPrompt, ContextSection, ContextStats) to `frontend/src/stores/ai/AIContextStore.ts`
- [ ] T002 Extend AIContextResult interface with new structured fields (summary, relatedIssues, relatedDocs, tasks, prompts) while keeping legacy fields (claudeCodePrompt, relatedDocs_legacy, relatedCode, similarIssues) in `frontend/src/stores/ai/AIContextStore.ts`
- [ ] T003 Add sectionErrors observable (Map<ContextSection, string>) and initialize new fields as null/empty in generateContext() in `frontend/src/stores/ai/AIContextStore.ts`

**Checkpoint**: AIContextStore has all new types and observable fields. No UI changes yet.

---

## Phase 2: Foundational

Core infrastructure required before user story work — store event handling and copy utilities.

- [ ] T004 Extend handleEvent() switch statement in AIContextStore to handle 7 new SSE event types: context_summary (sets result.summary), related_issues (sets result.relatedIssues), related_docs (sets result.relatedDocs), ai_tasks (sets result.tasks), ai_prompts (sets result.prompts), context_error (sets sectionErrors per section), context_complete (marks loading complete) in `frontend/src/stores/ai/AIContextStore.ts`
- [ ] T005 Add backward compatibility check in handleEvent(): when legacy `complete` event arrives, populate legacy fields; when new section events arrive, populate structured fields. Use `result.summary !== null` to determine rendering path. In `frontend/src/stores/ai/AIContextStore.ts`
- [ ] T006 Create copy-context.ts with pure functions: generateFullContextMarkdown(result: AIContextResult): string, generateSectionMarkdown(section: ContextSection, result: AIContextResult): string, copyToClipboard(text: string): Promise<boolean> in `frontend/src/lib/copy-context.ts`
- [ ] T007 Create reusable ContextSection component (~80 lines) with header (Lucide icon + title), copy button using generateSectionMarkdown(), children slot, and error state display from sectionErrors in `frontend/src/features/issues/components/context-section.tsx`

**Checkpoint**: Store handles all SSE events, copy utilities work, reusable section wrapper ready. UI components can build on this.

---

## Phase 3: User Story 1 - View AI Context Summary (P1)

**Goal**: Developer sees a summary card with stats when viewing AI Context tab. Tab replaces sidebar.
**Verify**: Open any issue, click AI Context tab, see summary card with title/description/stats or empty state with Generate button.

### Tests

- [ ] T008 [P] [US1] Write tests for ContextSummaryCard: renders issue identifier, title, summaryText, 4 stat counts; handles null summary gracefully in `frontend/src/features/issues/components/__tests__/context-summary-card.test.tsx`
- [ ] T009 [P] [US1] Write tests for AIContextTab: tests 4 states (empty with Generate button, loading with AIContextStreaming, error with retry, results with sections); tests Copy All button calls generateFullContextMarkdown and copyToClipboard; tests Regenerate button calls store.generateContext() in `frontend/src/features/issues/components/__tests__/ai-context-tab.test.tsx`

### Implementation

- [ ] T010 [P] [US1] Create ContextSummaryCard component (~100 lines) with gradient card (bg-ai/5 to bg-ai/10), FileText icon, issue identifier + title heading, summaryText paragraph, stats row (4 counts: Related Issues, Documents, Files, Tasks using Lucide icons) in `frontend/src/features/issues/components/context-summary-card.tsx`
- [ ] T011 [US1] Create AIContextTab component (~200 lines) as observer() wrapping: empty state (Sparkles icon + "Generate Context" button), loading state (reuse AIContextStreaming), error state (AlertCircle + retry button), results state (ContextHeader with Copy All/Regenerate buttons, ContextSummaryCard, placeholder slots for Related Context and AI Tasks sections). Use AIContextStore from RootStore. Dynamic import for code splitting. In `frontend/src/features/issues/components/ai-context-tab.tsx`
- [ ] T012 [US1] Modify page.tsx: add shadcn/ui Tabs wrapping main content area, move existing content (IssueHeader, description, sub-issues, activity) into TabsContent value="description", add TabsTrigger for "AI Context" with Sparkles icon and ai styling (bg-ai/10 text-ai), dynamically import AIContextTab, remove AIContextSidebar and isAIContextOpen state in `frontend/src/app/(workspace)/[workspaceSlug]/issues/[issueId]/page.tsx`
- [ ] T013 [US1] Update barrel exports: add AIContextTab, ContextSummaryCard, ContextSection exports; remove AIContextSidebar export (deprecated) in `frontend/src/features/issues/components/index.ts`

**Checkpoint**: US1 functional — AI Context tab visible, summary card renders, empty/loading/error states work, Copy All and Regenerate buttons functional.

---

## Phase 4: User Story 2 - Browse Related Context (P1)

**Goal**: Developer browses related issues with relation badges and documents with type badges.
**Verify**: Open issue with related context, see issues with BLOCKS/RELATES/BLOCKED BY badges and documents with NOTE/ADR/SPEC badges.

### Tests

- [ ] T014 [P] [US2] Write tests for RelatedIssuesSection: renders relation badges with correct colors (BLOCKS=destructive, RELATES=ai, BLOCKED BY=orange), issue identifier in mono font, status pill colored by stateGroup, title and summary text; handles empty array in `frontend/src/features/issues/components/__tests__/related-issues-section.test.tsx`

### Implementation

- [ ] T015 [P] [US2] Create RelatedIssuesSection component (~120 lines) mapping ContextRelatedIssue[] to items: relation badge (BLOCKS=bg-destructive/10 text-destructive, RELATES=bg-ai/10 text-ai, BLOCKED BY=bg-orange-100 text-orange-700 dark:bg-orange-950 dark:text-orange-400), identifier in font-mono, status pill colored by stateGroup (backlog/unstarted=muted, started=primary, completed=green, cancelled=destructive), title, summary in `frontend/src/features/issues/components/related-issues-section.tsx`
- [ ] T016 [P] [US2] Create RelatedDocsSection component (~80 lines) mapping ContextRelatedDoc[] to items: type badge (NOTE=bg-primary/10 text-primary, ADR=bg-orange-100 text-orange-700, SPEC=bg-ai/10 text-ai), title, summary, optional URL link in `frontend/src/features/issues/components/related-docs-section.tsx`
- [ ] T017 [US2] Integrate RelatedIssuesSection and RelatedDocsSection into AIContextTab results state: wrap in ContextSection with Link icon, title "Related Context", and section copy using generateSectionMarkdown('related_issues') and generateSectionMarkdown('related_docs'). Show per-section error from sectionErrors if present. In `frontend/src/features/issues/components/ai-context-tab.tsx`

**Checkpoint**: US2 functional — related issues show relation badges, documents show type badges, section copy works.

---

## Phase 5: User Story 4 - Use AI Tasks & Prompts (P1)

**Goal**: Developer uses AI-generated task checklist with local completion state and copies prompts.
**Verify**: See task checklist with checkboxes, click to toggle, expand prompt blocks, copy prompts.

### Tests

- [ ] T018 [P] [US4] Write tests for AITasksSection: checkbox toggling via local useState, task title/estimate/dependency display, handles empty array in `frontend/src/features/issues/components/__tests__/ai-tasks-section.test.tsx`
- [ ] T019 [P] [US4] Write tests for PromptBlock: renders title and content, copy button calls copyToClipboard with content, expand/collapse toggle, "Copied!" feedback with 2s timeout in `frontend/src/features/issues/components/__tests__/prompt-block.test.tsx`

### Implementation

- [ ] T020 [P] [US4] Create PromptBlock component (~90 lines) with collapsible block: header shows task title + Copy button (clipboard icon), content area uses font-mono pre-wrap dark background (bg-muted), copy triggers copyToClipboard() with "Copied!" feedback (2s setTimeout), Chevron toggle for expand/collapse in `frontend/src/features/issues/components/prompt-block.tsx`
- [ ] T021 [US4] Create AITasksSection component (~150 lines) with two subsections: (1) Task Checklist using local useState<Set<number>> for completedTasks, each item has checkbox, title, estimate badge, dependency list (e.g. "Depends on: Task 1, Task 3"), toggle via Set add/delete; (2) Prompt Blocks mapping ContextPrompt[] to PromptBlock components matched by taskId. In `frontend/src/features/issues/components/ai-tasks-section.tsx`
- [ ] T022 [US4] Integrate AITasksSection into AIContextTab results state: wrap in ContextSection with CheckSquare icon, title "AI Tasks", and section copy using generateSectionMarkdown('tasks'). Pass tasks and prompts from AIContextStore result. In `frontend/src/features/issues/components/ai-context-tab.tsx`

**Checkpoint**: US4 functional — task checkboxes toggle, prompts copyable, section renders independently from SSE.

---

## Phase 6: Polish

Cross-cutting concerns after all Phase 1 stories complete.

- [ ] T023 Run full quality gates: `cd frontend && pnpm lint && pnpm type-check && pnpm test` — fix any failures
- [ ] T024 Verify all new component files are under 700 lines
- [ ] T025 Verify WCAG 2.2 AA compliance: all interactive elements (buttons, checkboxes, tabs, copy actions) have ARIA labels, keyboard navigation works via Tab/Enter/Space/Arrow keys, focus indicators visible
- [ ] T026 Verify AIContextTab renders within 500ms when cached context exists (no unnecessary re-renders, dynamic import loads correctly)
- [ ] T027 Run test coverage check: `cd frontend && pnpm test -- --coverage` — verify >80% coverage on all new component files

**Checkpoint**: All quality gates pass, accessibility verified, performance target met.

---

## Dependencies

### Phase Order

```
Setup (T001-T003) → Foundational (T004-T007) → US1 (T008-T013) → US2 (T014-T017) → US4 (T018-T022) → Polish (T023-T027)
```

### User Story Independence

- US1 (Summary + Tab) must complete first — it creates the tab container and page integration
- US2 (Related Context) and US4 (AI Tasks) can run in parallel after US1, as they plug into independent slots in AIContextTab
- US3 (Codebase Context) and US5 (Chat) are Phase 2 — not in this task list

### Within Each Story

1. Tests (if included) — write first, verify failure
2. Leaf components before container components
3. Container integration last (plugs sections into AIContextTab)

### Parallel Opportunities

Tasks marked `[P]` in the same phase can run concurrently:

```bash
# Phase 3 (US1): Tests and leaf component in parallel
T008: ContextSummaryCard tests
T009: AIContextTab tests
T010: ContextSummaryCard component

# Phase 4 (US2): Both section components in parallel
T014: RelatedIssuesSection tests
T015: RelatedIssuesSection component
T016: RelatedDocsSection component

# Phase 5 (US4): Tests and PromptBlock in parallel
T018: AITasksSection tests
T019: PromptBlock tests
T020: PromptBlock component
```

---

## Implementation Strategy

### MVP First

1. Setup (T001-T003) → Foundational (T004-T007) → US1 (T008-T013) only
2. Validate: AI Context tab shows summary card, empty/loading/error states work
3. Deploy/demo — basic tab functional

### Incremental

1. Complete Foundation (T001-T007)
2. Add US1 (T008-T013) → test → verify tab works
3. Add US2 (T014-T017) → test → related context displays
4. Add US4 (T018-T022) → test → tasks and prompts functional
5. Polish (T023-T027) → quality gates pass

---

## Notes

- Tests included per spec.md requirement: "Unit tests for new components (>80% coverage)"
- Paths follow plan.md structure under `frontend/src/`
- US3 (Codebase Context, P2) and US5 (Enhance Chat, P3) are Phase 2 scope — excluded from this task list
- US4 is labeled as Phase 5 (not Phase 4) because its spec priority is P1 but it logically follows US2 for complete Related Context display before Tasks
- All components use observer() + MobX pattern per project conventions
- shadcn/ui components (Tabs, Card, Badge, Button) are already installed in the project

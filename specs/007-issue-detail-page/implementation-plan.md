# Implementation Plan: Issue Detail Page

## Task Dependency Graph

```
Phase 1 (Setup - Type Alignment)
═══════════════════════════════════
T001c ─────┐  (new types: StateBrief, UserBrief, Activity, etc.)
T001a ─────┤  (update Issue interface - depends on T001c types)
T001b ─────┤  (update UpdateIssueData - depends on T001c types)
T001d ─────┤  (install Calendar - independent)
T001  ─────┤  (SaveStatus component - independent)
T002  ─────┘  (SaveStatus tests - depends on T001)

Execution: T001c first, then T001a+T001b+T001d+T001 parallel, then T002

Phase 2 (Foundational - API + Hooks + Store)
═══════════════════════════════════════════════
T003 ──┐  (listActivities API)
T004 ──┤  (addComment API)
       │
T007 ──┤  (useIssueDetail hook)
T008 ──┤  (useUpdateIssue hook)
T009 ──┤  (useActivities hook - depends on T003)
T010 ──┤  (useAddComment hook - depends on T004)
T013 ──┤  (useProjectCycles hook - uses existing cyclesApi)
T013a ─┤  (useCreateSubIssue hook)
T013b ─┤  (useWorkspaceMembers hook)
T013c ─┤  (useWorkspaceLabels hook)
       │
T014 ──┤  (IssueStore saveStatus observable)
T014a ─┤  (useSaveStatus hook - depends on T014)
       │
T015 ──┤  (hook tests - depends on all hooks)
T015a ─┘  (useSaveStatus tests - depends on T014a)

Execution:
  Wave 1: T003, T004 (API methods) + T007, T008, T013, T013a, T013b, T013c (hooks without API deps) + T014 (store)
  Wave 2: T009, T010 (hooks needing APIs) + T014a (useSaveStatus)
  Wave 3: T015, T015a (all tests)

Phase 3 (US2 - Properties Panel) ← depends on Phase 2
════════════════════════════════════════════════════════
T016 ──┐  (IssueTypeSelect)
T017 ──┤  (CycleSelector)
T018 ──┤  (EstimateSelector)
T019 ──┤  (LinkedPRsList)
T020 ──┤  (SourceNotesList)
       │
T021 ──┤  (IssuePropertiesPanel - depends on T016-T020, T014a)
       │
T022 ──┤  (IssueTypeSelect tests)
T023 ──┤  (CycleSelector tests)
T024 ──┤  (EstimateSelector tests)
T025 ──┤  (LinkedPRsList tests)
T026 ──┤  (SourceNotesList tests)
T027 ──┘  (IssuePropertiesPanel tests - depends on T021)

Execution:
  Wave 1: T016, T017, T018, T019, T020 (all parallel)
  Wave 2: T021 (composition) + T022-T026 (tests for wave 1, parallel)
  Wave 3: T027 (panel tests)

Phase 4 (US1 - Inline Editing) ← depends on Phase 2 (parallel with Phase 3)
═══════════════════════════════════════════════════════════════════════════════
T028 ──┐  (IssueTitle)
T029 ──┤  (createIssueEditorExtensions)
T030 ──┤  (IssueDescriptionEditor - depends on T029)
T031 ──┤  (IssueTitle tests)
T032 ──┘  (IssueDescriptionEditor tests)

Execution:
  Wave 1: T028, T029 (parallel)
  Wave 2: T030 (depends on T029) + T031 (tests for T028)
  Wave 3: T032

Phase 5 (US5 - Sub-issues) ← depends on Phase 2 (parallel with Phase 3/4)
══════════════════════════════════════════════════════════════════════════════
T033 ──┐  (SubIssuesList)
T034 ──┘  (SubIssuesList tests)

Execution: T033 then T034

Phase 6 (US3 - Activity Timeline) ← depends on Phase 2 (parallel with Phase 5)
═════════════════════════════════════════════════════════════════════════════════
T035 ──┐  (ActivityEntry)
T036 ──┤  (CommentInput)
T037 ──┤  (ActivityTimeline - depends on T035, T036)
T038 ──┤  (ActivityEntry tests)
T039 ──┤  (CommentInput tests)
T040 ──┘  (ActivityTimeline tests)

Execution:
  Wave 1: T035, T036 (parallel)
  Wave 2: T037 + T038, T039 (parallel)
  Wave 3: T040

Phase 7 (US4 - Linked Items Tests) ← depends on Phase 3 (T019, T020)
════════════════════════════════════════════════════════════════════════
T041 ──┐  (LinkedPRsList nav tests)
T042 ──┘  (SourceNotesList nav tests)

Execution: T041, T042 parallel

Phase 8 (Composition) ← depends on ALL phases 3-7
═════════════════════════════════════════════════════
T043 ──┐  (page refactor)
T044 ──┤  (responsive layout - depends on T043)
T045 ──┤  (keyboard nav - depends on T043)
T046 ──┤  (ARIA/focus - depends on T043)
T047 ──┤  (page composition tests)
T047a ─┤  (data flow integration tests)
T048 ──┤  (responsive tests)
T049 ──┘  (keyboard tests)

Execution:
  Wave 1: T043
  Wave 2: T044, T045, T046 (parallel) + T047, T047a (parallel)
  Wave 3: T048, T049 (parallel)

Phase Final (Polish) ← depends on Phase 8
═══════════════════════════════════════════
T050 ──┐  (quality gates)
T051 ──┤  (file size check)
T052 ──┤  (accessibility audit)
T053 ──┤  (bundle size)
T054 ──┤  (barrel export)
T055 ──┘  (quickstart validation)

Execution: T050 first, then T051-T055 parallel
```

## Critical Path

```
T001c → T001a → T003+T004+T007+T008+T014 → T014a → T021 → T043 → T050
        (types)   (API + hooks + store)      (save)  (panel) (page) (quality)
```

## Execution Plan (Optimized for Parallelism)

### Batch 1: Phase 1 (Setup)
- Agent 1: T001c (new types) → T001a (Issue interface) → T001b (UpdateIssueData)
- Agent 2: T001 (SaveStatus) → T002 (SaveStatus tests)
- Agent 3: T001d (install Calendar)

### Batch 2: Phase 2 (Foundation)
- Agent 1: T003 + T004 (API methods) → T009 + T010 (hooks needing APIs)
- Agent 2: T007 + T008 + T013 + T013a + T013b + T013c (independent hooks)
- Agent 3: T014 (store) → T014a (useSaveStatus)
- After above: T015 + T015a (all hook tests)

### Batch 3: Phase 3 + 4 (Properties Panel + Inline Editing) PARALLEL
- Agent 1: T016 + T017 + T018 + T019 + T020 (shared components) → T021 (panel)
- Agent 2: T028 + T029 (title + editor factory) → T030 (description editor)
- After above: T022-T027 (US2 tests) + T031-T032 (US1 tests)

### Batch 4: Phase 5 + 6 (Sub-issues + Activity) PARALLEL
- Agent 1: T033 → T034 (sub-issues)
- Agent 2: T035 + T036 → T037 (activity timeline) → T038-T040 (tests)

### Batch 5: Phase 7 + 8 (Linked Items Tests + Composition)
- T041 + T042 (nav tests) → T043 (page refactor) → T044-T049 (responsive/keyboard/tests)

### Batch 6: Phase Final
- T050 → T051-T055 (quality checks)

## Codebase Key Facts

- **No labels API service** exists — T013c needs a thin wrapper or use store
- **No workspace members API service** — T013b needs a thin wrapper or use WorkspaceStore
- **Calendar component** not installed — T001d required before date pickers
- **Backend field `name`** not `title` — all Issue references must use `name`
- **Backend state is object** `{ id, name, color, group }` — not string enum
- **Activity pagination is offset-based** — not cursor
- **Comment body is `{ content }` only** — single string field
- **6 endpoints descoped** — edit/delete comments, labels list, integration-links, note-links, sub-issues list

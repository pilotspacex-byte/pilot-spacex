# Implementation Plan: Issue Detail Page

**Branch**: `007-issue-detail-page` | **Date**: 2026-02-02 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/007-issue-detail-page/spec.md`

## Summary

Complete the Issue Detail page at route `/[workspaceSlug]/issues/[issueId]` by adding inline title editing, TipTap description editor, interactive properties panel, activity timeline with comments, linked PRs/notes, sub-issues, responsive layout, and keyboard navigation. The page currently has a partial implementation (399 lines) with header, read-only display, and AI context sidebar. This plan covers frontend-only changes using existing backend APIs.

## Technical Context

**Language/Version**: TypeScript 5.3+ / Next.js 14+ (App Router)
**Primary Dependencies**: React 18, MobX 6+, TanStack Query 5+, TipTap 3.16+, TailwindCSS 3.4+, shadcn/ui
**Storage**: N/A (frontend-only; backend APIs already exist)
**Testing**: Vitest (unit), Playwright (E2E)
**Target Platform**: Web (desktop-first, responsive to 375px)
**Project Type**: Web application (frontend module within existing monorepo)
**Performance Goals**: FCP <1.5s, LCP <2.5s, page interactive <2s, property update feedback <100ms
**Constraints**: Files <700 lines, test coverage >80%, WCAG 2.2 AA, no API data in MobX
**Scale/Scope**: ~21 new files (12 components, 7 hooks, 1 utility, 1 page refactor), ~2500 lines of new code

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-Phase 0 Check

| Principle | Status | Evidence |
|-----------|--------|----------|
| I. AI-Human Collaboration | PASS | AI Context sidebar already follows DD-003 approval flow; no new AI features added |
| II. Note-First Approach | PASS | Source Notes section maintains bidirectional note-issue links per principle |
| III. Documentation-Third | N/A | No documentation generation in this feature |
| IV. Task-Centric Workflow | PASS | Sub-issues section supports task decomposition with progress tracking |
| V. Collaboration | PASS | Activity timeline enables team knowledge sharing |
| VI. Agile Integration | PASS | Cycle selector and estimate field support sprint planning |
| VII. Notation & Standards | N/A | No diagram generation in this feature |

### Technology Standards

| Standard | Status | Implementation |
|----------|--------|---------------|
| Frontend: React 18 + TypeScript + MobX | PASS | All new components use TypeScript strict + observer() |
| Frontend: TailwindCSS styling | PASS | All styling via Tailwind utility classes |
| State: MobX (UI) + TanStack Query (server) | PASS | See data-model.md state mapping table |
| Error format: RFC 7807 | PASS | Existing API client handles RFC 7807 responses |
| File size: 700 lines max | PASS | Component tree designed for small, focused files |
| Type checking: TypeScript strict | PASS | All new files use strict mode |
| Test coverage: >80% | PASS | Test files for all new components |
| AI features: human-in-the-loop | N/A | No new AI features; existing AI Context sidebar unchanged |
| RLS: workspace-scoped | PASS | All API calls scoped by workspaceId (existing pattern) |

### Quality Gates

| Gate | Status | Enforcement |
|------|--------|-------------|
| Lint passes | Required | `pnpm lint` |
| Type check passes | Required | `pnpm type-check` |
| Tests pass >80% | Required | `pnpm test --coverage` |
| No N+1 queries | N/A | Frontend-only |
| No TODOs/placeholders | Required | Pre-commit hook |
| WCAG 2.2 AA | Required | Manual + Playwright tests |

**Result**: All gates PASS. No violations requiring justification.

### Post-Phase 1 Re-check

| Principle | Status | Notes |
|-----------|--------|-------|
| I. AI-Human Collaboration | PASS | No changes to AI interaction |
| II. Note-First Approach | PASS | SourceNotesList maintains bidirectional links |
| IV. Task-Centric Workflow | PASS | SubIssuesList with progress indicator |
| Technology Standards | PASS | All components follow established patterns |
| Quality Gates | PASS | File sizes projected <300 lines each |

## Project Structure

### Documentation (this feature)

```text
specs/007-issue-detail-page/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0: research decisions
├── data-model.md        # Phase 1: TypeScript interfaces & API mapping
├── quickstart.md        # Phase 1: development guide
├── contracts/
│   └── frontend-components.yaml  # Phase 1: component tree & props
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2: implementation tasks (TBD)
```

### Source Code (repository root)

```text
frontend/src/
├── app/(workspace)/[workspaceSlug]/issues/[issueId]/
│   └── page.tsx                          # REFACTOR: compose new components
│
├── features/issues/
│   ├── components/
│   │   ├── issue-title.tsx               # NEW: inline editable title
│   │   ├── issue-description-editor.tsx  # NEW: TipTap description editor
│   │   ├── issue-properties-panel.tsx    # NEW: right sidebar properties
│   │   ├── activity-timeline.tsx         # NEW: activity feed container
│   │   ├── activity-entry.tsx            # NEW: single activity entry
│   │   ├── comment-input.tsx             # NEW: comment rich text input
│   │   ├── sub-issues-list.tsx           # NEW: child issues with progress
│   │   ├── linked-prs-list.tsx           # NEW: GitHub PR links
│   │   ├── source-notes-list.tsx         # NEW: note links
│   │   ├── issue-header.tsx              # EXISTING (no changes)
│   │   ├── ai-context-sidebar.tsx        # EXISTING (no changes)
│   │   └── __tests__/
│   │       ├── issue-title.test.tsx      # NEW
│   │       ├── issue-description-editor.test.tsx # NEW
│   │       ├── issue-properties-panel.test.tsx   # NEW
│   │       ├── activity-timeline.test.tsx        # NEW
│   │       ├── activity-entry.test.tsx           # NEW
│   │       ├── comment-input.test.tsx            # NEW
│   │       ├── sub-issues-list.test.tsx          # NEW
│   │       ├── linked-prs-list.test.tsx          # NEW
│   │       └── source-notes-list.test.tsx        # NEW
│   └── hooks/
│       ├── use-issue-detail.ts           # NEW: TanStack Query
│       ├── use-update-issue.ts           # NEW: mutation + optimistic
│       ├── use-activities.ts             # NEW: infinite query
│       ├── use-add-comment.ts            # NEW: mutation
│       ├── use-edit-comment.ts           # NEW: mutation
│       ├── use-delete-comment.ts         # NEW: mutation
│       └── use-workspace-cycles.ts       # NEW: query
│
├── components/
│   ├── issues/
│   │   ├── IssueTypeSelect.tsx           # NEW: type dropdown
│   │   ├── CycleSelector.tsx             # NEW: cycle dropdown
│   │   ├── EstimateSelector.tsx          # NEW: story points
│   │   ├── AssigneeSelector.tsx          # EXISTING (no changes)
│   │   ├── LabelSelector.tsx             # EXISTING (no changes)
│   │   └── IssueStateSelect.tsx          # EXISTING (no changes)
│   └── ui/
│       └── save-status.tsx               # NEW: save indicator
│
├── stores/features/issues/
│   └── IssueStore.ts                     # MINOR UPDATE: add save status observables
│
└── services/api/
    └── issues.ts                         # MINOR UPDATE: add comment & activity endpoints
```

**Structure Decision**: Frontend-only feature within existing Next.js App Router monorepo. All new components follow the established feature-folder pattern under `frontend/src/features/issues/`. Shared components (selectors, save status) go under `frontend/src/components/`. TanStack Query hooks are colocated with the feature.

## Implementation Phases

### Phase 1: Foundation (Hooks + Shared Components)

**Goal**: Establish the data fetching layer and reusable UI primitives.

**Components**:
1. `SaveStatus` — Shared save indicator component with idle/saving/saved/error states
2. TanStack Query hooks — `useIssueDetail`, `useUpdateIssue`, `useActivities`, `useAddComment`, `useEditComment`, `useDeleteComment`, `useWorkspaceCycles`
3. API client updates — Add `listActivities`, `addComment`, `editComment`, `deleteComment` to `issues.ts`
4. IssueStore updates — Add `saveStatus` observable map for per-field tracking

**Dependencies**: None (foundation layer)

### Phase 2: Properties Panel (Sidebar)

**Goal**: Replace the read-only sidebar with fully interactive property fields.

**Components**:
1. `IssueTypeSelect` — Issue type dropdown (Bug/Feature/Task/Improvement)
2. `CycleSelector` — Cycle assignment dropdown with date ranges
3. `EstimateSelector` — Fibonacci story point selector (1,2,3,5,8,13)
4. `IssuePropertiesPanel` — Composes all selectors + dates + metadata
5. `LinkedPRsList` — GitHub PR links in sidebar
6. `SourceNotesList` — Note links in sidebar

**Dependencies**: Phase 1 (hooks, SaveStatus)

### Phase 3: Main Content (Editing)

**Goal**: Replace read-only title and description with editable components.

**Components**:
1. `IssueTitle` — Inline editable title with auto-save, validation, keyboard shortcuts
2. `IssueDescriptionEditor` — TipTap rich text editor (dynamic import for code splitting)
3. `SubIssuesList` — Child issues with progress bar and inline creation

**Dependencies**: Phase 1 (hooks, SaveStatus), TipTap extensions (existing)

### Phase 4: Activity Timeline

**Goal**: Add the chronological activity feed with comments.

**Components**:
1. `ActivityEntry` — Single activity entry (state changes, comments, assignments, AI actions)
2. `CommentInput` — Rich text comment input with TipTap mini editor
3. `ActivityTimeline` — Container with infinite scroll pagination

**Dependencies**: Phase 1 (hooks), Phase 3 (TipTap setup for comment editor)

### Phase 5: Page Composition + Responsive + Keyboard

**Goal**: Refactor the page to compose all new components with responsive layout and keyboard navigation.

**Changes**:
1. Refactor `page.tsx` — Replace inline JSX with composed components, add responsive breakpoints
2. Responsive layout — Tailwind `xl:`, `lg:`, `md:`, `sm:` classes for split/stacked layout
3. Keyboard navigation — Tab order, Escape handlers, Cmd+S, arrow key navigation
4. Accessibility audit — Focus rings, ARIA labels, screen reader testing

**Dependencies**: Phases 1-4 (all components)

## Architecture Decisions

### AD-1: TipTap Extension Subset for Issue Description

Create `createIssueEditorExtensions()` that imports a subset of the note editor's extensions:
- **Included**: StarterKit, Markdown, Placeholder, CodeBlock, Mention, CharacterCount
- **Excluded**: GhostText, MarginAnnotation, SlashCommand, IssueLink, InlineIssue, ParagraphSplit

**Rationale**: Issue descriptions don't need AI ghost text or annotation features. Smaller bundle, simpler UX.

### AD-2: Optimistic Updates with TanStack Query

All property mutations use `useMutation` with `onMutate` snapshot pattern:
```
User action → onMutate (snapshot + optimistic update) → API call → onError (rollback) → onSettled (invalidate)
```

Title/description use local state (useState) for editing + MobX reaction for debounced save.

### AD-3: Dynamic Import for TipTap

`IssueDescriptionEditor` uses `next/dynamic` with `ssr: false` to:
- Code-split the TipTap bundle (~100KB gzipped)
- Avoid SSR hydration mismatch (TipTap is client-only)
- Show Skeleton placeholder during load

### AD-4: Activity Timeline Pagination

`useInfiniteQuery` with cursor-based pagination:
- Initial load: 50 entries
- `IntersectionObserver` on sentinel element triggers `fetchNextPage()`
- Newest entries at bottom (chronological order)
- New comments optimistically prepended to last page

## Complexity Tracking

> No Constitution Check violations. All components follow established patterns.

| Decision | Justification | Simpler Alternative |
|----------|--------------|---------------------|
| TipTap for description | Spec requires rich text (bold, code, images, mentions) | Plain textarea — rejected because spec requires formatting |
| Separate editor factory | Avoid loading ghost text/annotation code | Reuse full createEditorExtensions — rejected because 40%+ unused code |
| useInfiniteQuery | Activity timeline is unbounded + paginated | Single useQuery — rejected because doesn't support pagination |

## Risk Mitigations

| Risk | Mitigation | Monitoring |
|------|-----------|------------|
| TipTap bundle size | Dynamic import + code splitting | Bundle analyzer check in CI |
| Auto-save race conditions | Debounce + mutation queue dedup | Unit test for rapid edit sequences |
| Optimistic rollback UX | Toast notification on rollback | E2E test for network error scenario |
| File size >700 lines | Component tree splits page into 12 focused files | Pre-commit hook enforcement |

## Generated Artifacts

| Artifact | Path | Status |
|----------|------|--------|
| Specification | `specs/007-issue-detail-page/spec.md` | Complete |
| Research | `specs/007-issue-detail-page/research.md` | Complete |
| Data Model | `specs/007-issue-detail-page/data-model.md` | Complete |
| Component Contracts | `specs/007-issue-detail-page/contracts/frontend-components.yaml` | Complete |
| Quickstart Guide | `specs/007-issue-detail-page/quickstart.md` | Complete |
| Requirements Checklist | `specs/007-issue-detail-page/checklists/requirements.md` | Complete |
| Tasks | `specs/007-issue-detail-page/tasks.md` | Pending (`/speckit.tasks`) |

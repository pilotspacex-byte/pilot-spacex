# Tasks: Issue Detail Page - Full Implementation

**Source**: `/specs/007-issue-detail-page/`
**Required**: plan.md, spec.md
**Optional**: research.md, data-model.md, contracts/, quickstart.md

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

Project initialization, shared infrastructure, and frontend type alignment.

- [ ] T001 Create `SaveStatus` component with idle/saving/saved/error states and aria-live polite in `frontend/src/components/ui/save-status.tsx`
- [ ] T001a Update `Issue` interface in `frontend/src/types/index.ts` to align with backend `IssueResponse` schema: rename `title` → keep as frontend alias but add `name` field for API mapping, add `descriptionHtml`, `estimatePoints` (replace `estimatedHours`), `startDate`, `targetDate` (replace `dueDate`), `cycleId`, `parentId`, `subIssueCount`, `workspaceId`, `sequenceId`. Change `state` from `IssueState` string enum to `StateBrief` object `{ id, name, color, group }`. Add `project: ProjectBrief`. Update `assignee`/`reporter` to use `UserBrief` (matching backend `UserBriefSchema`: `id, email, display_name`). Keep `type` and `aiGenerated` as frontend-only fields (not in backend response).
- [ ] T001b [P] Update `UpdateIssueData` interface in `frontend/src/types/index.ts` to match backend `IssueUpdateRequest`: rename `title` → `name`, add `descriptionHtml`, `estimatePoints`, `startDate`, `targetDate`, `cycleId`, `moduleId`, `parentId`, `stateId` (UUID, not string enum), `labelIds` (UUID array), add `clear_*` fields (`clearAssignee`, `clearCycle`, `clearModule`, `clearParent`, `clearEstimate`, `clearStartDate`, `clearTargetDate`). Remove `estimatedHours`, `dueDate`, `labels`.
- [ ] T001c [P] Add missing frontend types to `frontend/src/types/index.ts`: `StateBrief` (`{ id, name, color, group }`), `UserBrief` (`{ id, email, displayName }`), `Activity` (matching backend: `id, activityType, field, oldValue, newValue, comment, metadata, createdAt, actor: UserBrief | null` — note: NO `commentHtml`, `editedAt`, `deletedAt`, `isAiGenerated` fields as backend doesn't have them), `IntegrationLink` (frontend-only type for future use: `id, issueId, integrationType, externalId, externalUrl, prNumber?, prTitle?, prStatus?`), `NoteIssueLink` (frontend-only type for future use: `id, noteId, issueId, linkType, noteTitle`), `ActivityTimelineResponse` (`{ activities: Activity[], total: number }`).
- [ ] T001d [P] Install shadcn/ui Calendar component: `npx shadcn-ui@latest add calendar` + verify `date-fns` peer dependency installed. Required for date pickers in T021 (IssuePropertiesPanel).
- [ ] T002 Write tests for `SaveStatus` component in `frontend/src/components/ui/__tests__/save-status.test.tsx`

---

## Phase 2: Foundational

Core hooks and API client updates required before user story work.

### API Client Updates

- [ ] T003 Add `listActivities(workspaceId, issueId, { limit?, offset? })` method to `frontend/src/services/api/issues.ts` returning `ActivityTimelineResponse` (`{ activities: Activity[], total: number }`). Backend uses **offset-based pagination** (`limit`/`offset` query params), NOT cursor-based. Default limit=50, offset=0.
- [ ] T004 [P] Add `addComment(workspaceId, issueId, { content })` method to `frontend/src/services/api/issues.ts`. Backend `CommentCreateRequest` has a single `content: string` field (1-10000 chars), NOT `{ comment, commentHtml }`.
- [ ] ~~T005~~ DESCOPED: No `editComment` endpoint exists in backend. Backend only has `POST /{issue_id}/comments`. Edit comment requires backend work first — tracked as future backend task.
- [ ] ~~T006~~ DESCOPED: No `deleteComment` endpoint exists in backend. Requires backend work first — tracked as future backend task.
- [ ] T006a [P] `cyclesApi.list()` already exists in `frontend/src/services/api/cycles.ts` with `(workspaceId, { projectId, ...filters })` signature. No new API method needed. Note: backend requires `project_id` query param (not workspace-scoped). The hook (T013) must pass `projectId` from the issue's `project.id`.

### TanStack Query Hooks

- [ ] T007 Create `useIssueDetail` hook with `useQuery` for fetching single issue data in `frontend/src/features/issues/hooks/use-issue-detail.ts` (queryKey: `['issues', issueId]`, staleTime: 30s)
- [ ] T008 [P] Create `useUpdateIssue` hook with `useMutation` and optimistic update (onMutate snapshot + rollback) in `frontend/src/features/issues/hooks/use-update-issue.ts`. `onSettled` must invalidate `['issues', issueId]` to sync `useIssueDetail` cache.
- [ ] T009 [P] Create `useActivities` hook with `useInfiniteQuery` for **offset-based** paginated activity loading (50 per page) in `frontend/src/features/issues/hooks/use-activities.ts`. `getNextPageParam` computes next offset from `(pageIndex + 1) * 50`; stops when `offset >= total`. Backend returns `{ activities: Activity[], total: number }`.
- [ ] T010 [P] Create `useAddComment` mutation hook with optimistic rendering in `frontend/src/features/issues/hooks/use-add-comment.ts`. Calls `issuesApi.addComment(workspaceId, issueId, { content })`. `onSettled` must invalidate `['issues', issueId, 'activities']` to sync `useActivities` cache.
- [ ] ~~T011~~ DESCOPED: `useEditComment` hook not implementable — no backend `PATCH /comments/:id` endpoint. Tracked as future work.
- [ ] ~~T012~~ DESCOPED: `useDeleteComment` hook not implementable — no backend `DELETE /comments/:id` endpoint. Tracked as future work.
- [ ] T013 [P] Create `useProjectCycles` hook (renamed from `useWorkspaceCycles`) with `useQuery` for fetching cycles in `frontend/src/features/issues/hooks/use-project-cycles.ts` (queryKey: `['cycles', projectId]`, staleTime: 60s). Uses existing `cyclesApi.list(workspaceId, { projectId })`. Requires `projectId` from issue's `project.id`, NOT workspace-scoped.
- [ ] T013a [P] Create `useCreateSubIssue` mutation hook in `frontend/src/features/issues/hooks/use-create-sub-issue.ts` calling `issuesApi.create()` with `parentId`, invalidating `['issues', parentId]` on success
- [ ] T013b [P] Create `useWorkspaceMembers` hook with `useQuery` for fetching workspace members in `frontend/src/features/issues/hooks/use-workspace-members.ts` (queryKey: `['workspaces', workspaceId, 'members']`, staleTime: 60s). Uses existing `workspacesApi.listMembers()`. Required by `AssigneeSelector` in `IssuePropertiesPanel`.
- [ ] T013c [P] Create `useWorkspaceLabels` hook with `useQuery` for fetching workspace labels in `frontend/src/features/issues/hooks/use-workspace-labels.ts` (queryKey: `['workspaces', workspaceId, 'labels']`, staleTime: 60s). Uses existing `labelsApi.list()`. Required by `LabelSelector` in `IssuePropertiesPanel`.

### MobX Store Updates

- [ ] T014 Add `saveStatus: Map<string, 'idle' | 'saving' | 'saved' | 'error'>` observable and `setSaveStatus(field, status)` action to `frontend/src/stores/features/issues/IssueStore.ts`. Include `clearSaveStatus(field)` action that resets to `'idle'` after 2s timeout (auto-fade pattern).
- [ ] T014a Create `useSaveStatus` helper hook in `frontend/src/features/issues/hooks/use-save-status.ts` that encapsulates the SaveStatus wiring pattern: accepts a `fieldName` string, returns `{ status, wrapMutation }` where `wrapMutation(mutationFn)` calls `setSaveStatus(field, 'saving')` before mutation, `setSaveStatus(field, 'saved')` on success (with 2s auto-clear), and `setSaveStatus(field, 'error')` on failure. Used by `IssueTitle` (T028), `IssueDescriptionEditor` (T030), and `IssuePropertiesPanel` (T021) to avoid duplicating SaveStatus wiring logic.

### Tests

- [ ] T015 Write unit tests for all TanStack Query hooks (useIssueDetail, useUpdateIssue, useActivities, useAddComment, useProjectCycles, useCreateSubIssue, useWorkspaceMembers, useWorkspaceLabels) in `frontend/src/features/issues/hooks/__tests__/`
- [ ] T015a Write unit tests for `useSaveStatus` hook verifying: idle → saving → saved → idle (2s auto-clear) lifecycle, error state on mutation failure, concurrent field tracking in `frontend/src/features/issues/hooks/__tests__/use-save-status.test.ts`

**Checkpoint**: Foundation complete — all data fetching hooks and API methods ready for use in components.

---

## Phase 3: User Story 2 — Properties Panel Interaction (P1)

**Goal**: Replace the read-only sidebar with fully interactive property fields using existing selectors and new components.
**Verify**: Open an issue, change assignee from sidebar dropdown, verify change persists on reload.

### New Shared Components

- [ ] T016 [P] [US2] Create `IssueTypeSelect` dropdown component (Bug/Feature/Task/Improvement) with colored icons in `frontend/src/components/issues/IssueTypeSelect.tsx`
- [ ] T017 [P] [US2] Create `CycleSelector` dropdown showing workspace cycles with name + date range, supporting null (no cycle) in `frontend/src/components/issues/CycleSelector.tsx`
- [ ] T018 [P] [US2] Create `EstimateSelector` with Fibonacci preset buttons (1,2,3,5,8,13) and custom input in `frontend/src/components/issues/EstimateSelector.tsx`

### Sidebar Sections

- [ ] T019 [P] [US2] Create `LinkedPRsList` component displaying GitHub PRs with number, title, status badge (Open=blue, Merged=purple, Closed=grey), external link, empty state in `frontend/src/features/issues/components/linked-prs-list.tsx`
- [ ] T020 [P] [US2] Create `SourceNotesList` component displaying linked notes with title, link type badge (EXTRACTED/CREATED/REFERENCED), navigation to note editor, empty state in `frontend/src/features/issues/components/source-notes-list.tsx`

### Properties Panel Composition

- [ ] T021 [US2] Create `IssuePropertiesPanel` component composing IssueStateSelect, IssuePrioritySelect, IssueTypeSelect, AssigneeSelector, LabelSelector, CycleSelector, EstimateSelector, date pickers (using shadcn Calendar from T001d), Reporter (read-only display with avatar + display_name), LinkedPRsList, SourceNotesList, and metadata timestamps in `frontend/src/features/issues/components/issue-properties-panel.tsx`. Receives `members` (from `useWorkspaceMembers` T013b), `labels` (from `useWorkspaceLabels` T013c), `cycles` (from `useProjectCycles` T013) as props from page. Note: State and Priority selectors are already interactive in the current page — wire them through `useUpdateIssue` instead of direct IssueStore calls. `onUpdate` must send backend field names (`name` not `title`, `stateId` not `state`, `estimatePoints` not `estimatedHours`, `targetDate` not `dueDate`). Each property update calls `onUpdate` prop (bound to `useUpdateIssue` mutate fn) with `useSaveStatus` (T014a) for per-field save feedback. **Note**: LinkedPRsList and SourceNotesList will render from data included in the issue response; no separate list endpoints exist in backend — these components render from `issue.integrationLinks` and `issue.noteLinks` arrays if/when the backend adds them to `IssueResponse`. For MVP, render empty state if these fields are undefined.

### Tests

- [ ] T022 [P] [US2] Write tests for `IssueTypeSelect` in `frontend/src/components/issues/__tests__/IssueTypeSelect.test.tsx`
- [ ] T023 [P] [US2] Write tests for `CycleSelector` in `frontend/src/components/issues/__tests__/CycleSelector.test.tsx`
- [ ] T024 [P] [US2] Write tests for `EstimateSelector` in `frontend/src/components/issues/__tests__/EstimateSelector.test.tsx`
- [ ] T025 [P] [US2] Write tests for `LinkedPRsList` in `frontend/src/features/issues/components/__tests__/linked-prs-list.test.tsx`
- [ ] T026 [P] [US2] Write tests for `SourceNotesList` in `frontend/src/features/issues/components/__tests__/source-notes-list.test.tsx`
- [ ] T027 [US2] Write tests for `IssuePropertiesPanel` (property change, optimistic update, rollback on error) in `frontend/src/features/issues/components/__tests__/issue-properties-panel.test.tsx`

**Checkpoint**: US2 functional — all sidebar properties are editable with optimistic updates, linked items display correctly with navigation.

---

## Phase 4: User Story 1 — Inline Issue Editing (P1) 🎯 MVP

**Goal**: Replace read-only title and description with inline editable components using auto-save.
**Verify**: Open any issue, click title, type new value, click away, verify title persists on reload.

### Implementation

- [ ] T028 [P] [US1] Create `IssueTitle` component with click-to-edit, 2s debounce auto-save, Enter confirm, Escape cancel, 1-255 char validation, `SaveStatus` integration via `useSaveStatus` (T014a) in `frontend/src/features/issues/components/issue-title.tsx`. Uses local `useState` for edit buffer; on save calls `useUpdateIssue` with `{ name: newTitle }` (backend field is `name`, not `title`). Optimistically patches the `['issues', issueId]` query cache so other consumers stay in sync.
- [ ] T029 [P] [US1] Create `createIssueEditorExtensions()` factory importing subset (StarterKit, Markdown, Placeholder, CodeBlock, Mention, CharacterCount) from existing note editor extensions in `frontend/src/features/issues/editor/create-issue-editor-extensions.ts`
- [ ] T030 [US1] Create `IssueDescriptionEditor` component with TipTap rich text editor (dynamic import via `next/dynamic` with `ssr: false`), 2s debounce auto-save, "Add a description..." placeholder, `SaveStatus` integration via `useSaveStatus` (T014a) in `frontend/src/features/issues/components/issue-description-editor.tsx`. TipTap editor content is the source of truth during editing; on save calls `useUpdateIssue` with `{ description, description_html }` (backend field uses snake_case `description_html`). Optimistically patches the `['issues', issueId]` query cache.

### Tests

- [ ] T031 [P] [US1] Write tests for `IssueTitle` (edit mode, auto-save, validation, keyboard shortcuts) in `frontend/src/features/issues/components/__tests__/issue-title.test.tsx`
- [ ] T032 [P] [US1] Write tests for `IssueDescriptionEditor` (render, auto-save, placeholder, read-only mode) in `frontend/src/features/issues/components/__tests__/issue-description-editor.test.tsx`

**Checkpoint**: US1 functional — title and description are editable inline with auto-save, validation, and keyboard shortcuts.

---

## Phase 5: User Story 5 — Sub-issues Management (P2)

**Goal**: Display child issues with progress tracking and inline creation.
**Verify**: Open a parent issue, verify sub-issues listed with progress, add new sub-issue.

### Implementation

- [ ] T033 [US5] Create `SubIssuesList` component displaying child issues (identifier, title, state badge, assignee avatar), progress bar (X of Y completed), "Add sub-issue" inline form (title + optional type/priority) using `useCreateSubIssue` hook from T013a, click navigation to sub-issue detail in `frontend/src/features/issues/components/sub-issues-list.tsx`

### Tests

- [ ] T034 [US5] Write tests for `SubIssuesList` (display, progress, creation, navigation) in `frontend/src/features/issues/components/__tests__/sub-issues-list.test.tsx`

**Checkpoint**: US5 functional — sub-issues display with progress, new sub-issues creatable inline.

---

## Phase 6: User Story 3 — Activity Timeline (P2)

**Goal**: Add chronological activity feed with comments and infinite scroll. Comment edit/delete deferred until backend endpoints exist.
**Verify**: Open an issue with state changes, verify timeline shows changes with actor/action/timestamp.

### Implementation

- [ ] T035 [P] [US3] Create `ActivityEntry` component rendering state changes ("changed state from {old} to {new}"), assignments, label changes, comments (plain text — backend `comment` field is string, not HTML), relative timestamps. Backend `ActivityResponse` has `activity_type` (string), `field`, `old_value`, `new_value`, `comment`, `metadata`, `actor: UserBrief | null`. No `isAiGenerated` field in backend — check `metadata` for AI indicator if available, otherwise omit AI sparkles icon. No edit/delete buttons (endpoints don't exist yet). File: `frontend/src/features/issues/components/activity-entry.tsx`
- [ ] T036 [P] [US3] Create `CommentInput` component with TipTap mini editor (StarterKit + Mention + CodeBlock), Enter to submit, Shift+Enter for newline, clear after submit. Submit sends `{ content: plainTextContent }` (backend accepts single `content` string field, 1-10000 chars). File: `frontend/src/features/issues/components/comment-input.tsx`
- [ ] T037 [US3] Create `ActivityTimeline` component with `useActivities` infinite query (offset-based: loads 50 at a time, `IntersectionObserver` sentinel triggers next page by incrementing offset), `CommentInput` at bottom. No edit/delete handlers in MVP (descoped T011/T012). File: `frontend/src/features/issues/components/activity-timeline.tsx`

### Tests

- [ ] T038 [P] [US3] Write tests for `ActivityEntry` (state change rendering, comment rendering, relative timestamps, empty actor handling) in `frontend/src/features/issues/components/__tests__/activity-entry.test.tsx`
- [ ] T039 [P] [US3] Write tests for `CommentInput` (submit with content, newline, clear, empty submit prevention) in `frontend/src/features/issues/components/__tests__/comment-input.test.tsx`
- [ ] T040 [US3] Write tests for `ActivityTimeline` (offset pagination, comment add, infinite scroll sentinel) in `frontend/src/features/issues/components/__tests__/activity-timeline.test.tsx`

**Checkpoint**: US3 functional — activity timeline shows all changes, comments addable, offset-based pagination works. Edit/delete comments deferred to future backend work.

---

## Phase 7: User Story 4 — Linked Items (P2)

**Goal**: Enable navigation from issue to linked PRs and source notes.
**Verify**: Open an issue extracted from a note, verify source note appears in sidebar, click navigates to note editor.

> Note: `LinkedPRsList` and `SourceNotesList` components were created in Phase 3 (US2) as part of the properties panel. This phase adds navigation verification tests.

- [ ] T041 [US4] Write navigation tests for `LinkedPRsList` verifying: PR links render with `target="_blank"` and `rel="noopener noreferrer"`, click triggers external navigation, status badges have correct colors (Open=blue, Merged=purple, Closed=grey) in `frontend/src/features/issues/components/__tests__/linked-prs-list.test.tsx` (extend T025)
- [ ] T042 [US4] Write navigation tests for `SourceNotesList` verifying: click navigates to `/${workspaceSlug}/notes/${noteId}` via Next.js router, link type badges render correctly (EXTRACTED/CREATED/REFERENCED) in `frontend/src/features/issues/components/__tests__/source-notes-list.test.tsx` (extend T026)

**Checkpoint**: US4 functional — linked PRs open externally, source notes navigate internally.

---

## Phase 8: Page Composition + User Story 6 (Responsive) + User Story 7 (Keyboard)

**Goal**: Refactor page.tsx to compose all new components, add responsive breakpoints and keyboard navigation.
**Verify**: Page renders correctly at all breakpoints, all elements keyboard-accessible.

### Page Refactor

- [ ] T043 Refactor `frontend/src/app/(workspace)/[workspaceSlug]/issues/[issueId]/page.tsx` to replace inline JSX with composed components. **Data flow**: Page calls `useIssueDetail(workspaceId, issueId)` as single source of truth. Backend returns `IssueResponse` with `name` (not `title`), `state: { id, name, color, group }` (object, not string), `estimate_points`, `start_date`, `target_date`, `project: { id, name, identifier }`. Page passes props down:
  - `IssueHeader`: `identifier`, `hasAiEnhancements`, callbacks
  - `IssueTitle`: `title={issue.name}`, `onSave` (sends `{ name: newTitle }` via `useUpdateIssue`)
  - `IssueDescriptionEditor`: `content={issue.descriptionHtml}`, `onSave` (sends `{ description, description_html }` via `useUpdateIssue`)
  - `SubIssuesList`: `parentId={issue.id}`, `subIssueCount={issue.subIssueCount}`, `workspaceSlug` (note: backend only returns count, not children list — sub-issues list requires filtering issues by `parent_id`)
  - `ActivityTimeline`: `issueId`, `workspaceId`, `currentUserId` (calls own `useActivities` internally)
  - `IssuePropertiesPanel`: `issue`, `workspaceId`, `workspaceSlug`, `members` (from `useWorkspaceMembers`), `labels` (from `useWorkspaceLabels`), `cycles` (from `useProjectCycles` using `issue.project.id`), `onUpdate` (receives `useUpdateIssue` mutate fn)
  - `AIContextSidebar`: `issueId`, `issueIdentifier`, `open`, `onOpenChange`
  Page also calls `useWorkspaceMembers`, `useWorkspaceLabels`, `useProjectCycles(issue.project.id)` at page level to pass as props. Remove now-unused MobX handlers (`handleStateChange`, `handlePriorityChange`). Remove inline utility functions (`getInitials`, `formatDate`, `formatRelativeTime`) — extract to `frontend/src/lib/format-utils.ts` or use within child components. Keep file under 300 lines.

### Responsive Layout

- [ ] T044 [US6] Add responsive Tailwind classes to page layout: `xl:flex-row xl:w-[70%]` / `xl:w-[30%]`, `lg:w-[65%]` / `lg:w-[35%]`, `md:flex-col` with properties above content, `sm:flex-col` with properties in shadcn/ui `Collapsible` accordion

### Keyboard Navigation

- [ ] T045 [US7] Add keyboard event handlers to page: Escape closes AI Context sidebar, Cmd/Ctrl+S force-saves all pending changes (flush debounce timers), Tab order follows title → description → sub-issues → activity → sidebar properties
- [ ] T046 [US7] Add visible focus rings (3px primary at 30% opacity) to all interactive elements and ARIA labels to all property selectors (`aria-label="State"`, `aria-label="Priority"`, etc.)

### Tests

- [ ] T047 Write integration test for page composition verifying all sections render with mock data in `frontend/src/app/(workspace)/[workspaceSlug]/issues/[issueId]/__tests__/page.test.tsx`
- [ ] T047a Write data flow integration test in `frontend/src/features/issues/hooks/__tests__/integration-data-flow.test.ts` verifying end-to-end wiring: (1) user changes assignee → `useUpdateIssue` fires with `{ assignee_id: newId }` → optimistic update patches `['issues', issueId]` cache → `onSettled` invalidates → `useIssueDetail` refetches; (2) user adds comment → `useAddComment` fires with `{ content }` → optimistic entry appended to `useActivities` cache → `onSettled` invalidates `['issues', issueId, 'activities']`; (3) `useSaveStatus` lifecycle: idle → saving → saved → idle (2s auto-clear); (4) verify field name mapping: frontend `title` → API `name`, frontend `estimatePoints` → API `estimate_points`. Use `@tanstack/react-query` test utilities with `QueryClient` and `renderHook`.
- [ ] T048 [P] [US6] Write responsive layout test verifying breakpoint behavior (mock viewport widths) in `frontend/src/features/issues/components/__tests__/responsive-layout.test.tsx`
- [ ] T049 [P] [US7] Write keyboard navigation test verifying Tab order, Escape, Cmd+S in `frontend/src/features/issues/components/__tests__/keyboard-nav.test.tsx`

**Checkpoint**: Page fully composed, responsive across all breakpoints, keyboard accessible.

---

## Phase Final: Polish

Cross-cutting concerns after all stories complete.

- [ ] T050 Run `pnpm lint && pnpm type-check && pnpm test --coverage` and fix all errors. Verify >80% coverage for new files.
- [ ] T051 [P] Verify all new files are under 700 lines. Split any that exceed the limit.
- [ ] T052 [P] Run accessibility audit: verify WCAG 2.2 AA compliance (4.5:1 contrast, keyboard nav complete, ARIA labels present, focus rings visible, screen reader announcements for save status)
- [ ] T053 [P] Verify bundle size impact: run `pnpm build` and check that TipTap dynamic import code-splits correctly (issue description editor not in main bundle)
- [ ] T054 Update `frontend/src/features/issues/components/index.ts` barrel export to include all new components
- [ ] T055 Run quickstart.md validation: verify development workflow end-to-end (create issue, edit title, change properties, add comment, view activity)

---

## Dependencies

### Phase Order

```
Phase 1 (Setup) → Phase 2 (Foundational) → Phases 3-7 (User Stories) → Phase 8 (Composition) → Phase Final (Polish)
```

### User Story Independence

After Phase 2 completes:
- **US2 (Properties Panel)** can start immediately
- **US1 (Inline Editing)** can start immediately (parallel with US2)
- **US5 (Sub-issues)** can start immediately (parallel with US1/US2 — no TipTap dependency; only needs `useCreateSubIssue` from Phase 2)
- **US3 (Activity Timeline)** can start after Phase 2 (depends on `useAddComment` hook). Comment edit/delete deferred — no backend endpoints.
- **US4 (Linked Items)** depends on US2 (components created there). LinkedPRsList and SourceNotesList render empty state for MVP — no dedicated backend endpoints.
- **US6 + US7 (Responsive + Keyboard)** depend on all components being created (Phase 8)

### Within Each Story

1. Shared components before composition components
2. Implementation before tests
3. Core rendering before interaction handlers

### Parallel Opportunities

Tasks marked `[P]` in the same phase can run concurrently:

```text
# Phase 1: Type alignment tasks in parallel
T001a, T001b, T001c, T001d — type updates + Calendar install (independent)

# Phase 2: All API methods can be added in parallel
T003, T004 — activity + comment API methods (T005/T006 descoped)

# Phase 2: All hooks can be created in parallel
T007-T010, T013, T013a, T013b, T013c — 8 TanStack Query hooks (T011/T012 descoped)
T014, T014a — MobX saveStatus + useSaveStatus helper (T014a depends on T014)

# Phase 3: All shared selectors in parallel
T016, T017, T018 — IssueTypeSelect, CycleSelector, EstimateSelector

# Phase 3: Sidebar sections in parallel
T019, T020 — LinkedPRsList, SourceNotesList

# Phase 4: Title and editor factory in parallel
T028, T029 — IssueTitle, createIssueEditorExtensions

# Phase 5+6: Sub-issues and Activity can run in parallel (no dependency)
Phase 5 (T033-T034) || Phase 6 (T035-T040)

# Phase 6: Activity entry and comment input in parallel
T035, T036 — ActivityEntry, CommentInput
```

---

## Implementation Strategy

### MVP First

1. Phase 1 (Setup) → Phase 2 (Foundational) → Phase 4 (US1: Inline Editing)
2. Validate: title and description editable with auto-save
3. Deploy/demo with read-only sidebar (existing)

### Incremental

1. Complete Phases 1-2 (Foundation)
2. Phase 3 (US2: Properties) + Phase 4 (US1: Editing) → test → deploy
3. Phase 5 (US5: Sub-issues) + Phase 6 (US3: Activity) → test → deploy
4. Phase 7 (US4: Linked Items) → test → deploy
5. Phase 8 (Composition + Responsive + Keyboard) → test → deploy
6. Phase Final (Polish) → final deploy

---

## Notes

- All file paths are relative to repository root
- Tests follow Vitest + Testing Library pattern per project standards
- Components use `observer()` wrapper for MobX reactivity where needed
- TanStack Query hooks follow the project's optimistic update pattern (onMutate snapshot + rollback)
- Commit after each completed phase or logical group of tasks
- **Existing page state**: `page.tsx` (399 lines) already has working IssueStateSelect and IssuePrioritySelect dropdowns, read-only Assignee/Labels/Reporter/DueDate display, and AI Context sidebar. T043 refactor replaces all inline JSX.
- **No prototype exists** at `docs/design-system/prototype/issue-detail-full.html` — implementation follows spec.md and design system tokens from `ui-design-spec.md`
- **Backend field naming**: Backend uses `name` (not `title`), `estimate_points` (not `estimatedHours`), `target_date` (not `dueDate`), `state` as object `{ id, name, color, group }` (not string enum). Frontend types must be aligned before component work starts (T001a-T001c).
- **Descoped features** (no backend endpoints): Comment edit/delete (T005/T006/T011/T012), dedicated sub-issues list endpoint, integration-links list endpoint, note-links list endpoint, workspace-scoped labels list. These require backend work in a separate branch.
- **Cycles scoping**: Backend `list_cycles` requires `project_id` param, not workspace-scoped. Hook renamed from `useWorkspaceCycles` → `useProjectCycles`.

## Validation Log

**2026-02-02 (v1)**: Validated against codebase, spec.md, and business decisions. Fixes applied:
- Added T006a: missing `listCycles` API method (blocked CycleSelector)
- Added T013a: missing `useCreateSubIssue` hook (blocked SubIssuesList creation)
- Fixed T021: added Reporter read-only display, noted State/Priority already interactive
- Fixed T043: explicit cleanup of unused IssueStore handlers and utility functions
- Fixed US5 dependency: SubIssuesList has no TipTap dependency, can run parallel with US1/US2
- Fixed T041/T042: converted from verification-only to proper navigation test tasks
- Updated parallel opportunities to reflect new tasks and Phase 5||6 parallelism

**2026-02-02 (v2)**: Integration gap analysis — 6 cross-layer wiring gaps fixed:
- Gap 1: Added T013b (`useWorkspaceMembers`) and T013c (`useWorkspaceLabels`) — required by `IssuePropertiesPanel` for `AssigneeSelector` and `LabelSelector` props. Without these, the panel has no member/label data.
- Gap 2: Added T014a (`useSaveStatus` helper hook) — encapsulates SaveStatus wiring pattern (saving → saved → auto-clear 2s). Eliminates duplicate wiring in T028, T030, T021. Updated T014 with `clearSaveStatus` auto-fade.
- Gap 3: Added explicit `onSettled` invalidation requirements to T008, T010, T011, T012 — ensures `useUpdateIssue` syncs `useIssueDetail` cache and comment mutations sync `useActivities` cache.
- Gap 4: Updated T028 and T030 — documented local state → query cache sync: local `useState`/TipTap is source of truth during editing, `useUpdateIssue` optimistically patches `['issues', issueId]` cache on save.
- Gap 5: Updated T043 — explicit prop-passing contract: page calls `useIssueDetail` + `useWorkspaceMembers` + `useWorkspaceLabels` + `useWorkspaceCycles` at page level, passes data as props to each child component with exact prop names.
- Gap 6: Added T047a (data flow integration test) — verifies end-to-end: property change → optimistic update → cache invalidation → refetch; comment add → activity cache update; SaveStatus lifecycle.

**2026-02-02 (v3)**: Spec-vs-backend gap analysis — 7 gaps fixed:
- Gap 1 (CRITICAL): Frontend `Issue` type out of sync with backend `IssueResponse`. Added T001a (update Issue interface: `name` not `title`, `StateBrief` object not string, `estimatePoints`, `startDate`, `targetDate`, `cycleId`, `parentId`, `subIssueCount`, `workspaceId`, `sequenceId`), T001b (update `UpdateIssueData` with backend field names + `clear_*` fields), T001c (add missing types: `StateBrief`, `UserBrief`, `Activity`, `IntegrationLink`, `NoteIssueLink`, `ActivityTimelineResponse`).
- Gap 2 (CRITICAL): 6 missing backend endpoints. Descoped T005/T006 (edit/delete comment APIs) and T011/T012 (edit/delete comment hooks). LinkedPRsList/SourceNotesList render empty state — no dedicated endpoints. Sub-issues list requires filtering by `parent_id`, not a dedicated endpoint.
- Gap 3: Activity pagination is offset-based (`limit`/`offset`), not cursor-based. Updated T003 (API method), T009 (useActivities hook), T037 (ActivityTimeline component), T040 (tests).
- Gap 4: Comment schema mismatch. Backend `CommentCreateRequest` has single `content` field (not `{ comment, commentHtml }`). Updated T004, T010, T036 (CommentInput), T035 (ActivityEntry — comments are plain text, no `commentHtml`).
- Gap 5: Missing frontend types. Added T001c with all missing types aligned to actual backend schemas. Notably: `Activity` has NO `editedAt`, `deletedAt`, `isAiGenerated`, `commentHtml` fields (backend doesn't return them). `UserBrief` uses `email` + `display_name` (not `name` + `avatarUrl`).
- Gap 6: Missing UI dependency. Added T001d — install shadcn Calendar component for date pickers.
- Gap 7: Cycles endpoint requires `project_id`, not workspace-scoped. Renamed `useWorkspaceCycles` → `useProjectCycles` (T013). Updated T021 and T043 to pass `issue.project.id`.

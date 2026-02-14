# Issues Module

_For project overview, see main `CLAUDE.md` and `frontend/CLAUDE.md`_

## Purpose

Issue CRUD with inline editing, property management, state transitions, activity tracking (comments + history), sub-issues, AI context generation, and keyboard shortcuts (Cmd/Ctrl+S force save, Escape close sidebar).

**Design Decisions**: DD-065 (state split), DD-086 (AI agent), DD-003 (approval)

---

## Critical Constants

| Constant | Value | Purpose |
|----------|-------|---------|
| Debounce MS | 2000 | Auto-save delay for title/description |
| AI Context Cache | 5 minutes | Stale time for generated context |
| Activity Page Size | 50 | Offset pagination per request |
| Issue Stale Time | 30 seconds | Detail query cache time |

---

## Issue State Machine

```
Backlog --> Todo --> In Progress --> In Review --> Done
                                                   |
    <------------ Can Reopen (to Todo) ------------+

Any state --> Cancelled (final, no reopen)
```

**State-Cycle Constraints**: Backlog (no cycle), Todo (optional), In Progress/In Review (active cycle required), Done (archived), Cancelled (removed from cycle).

---

## Directory Structure

```
features/issues/
├── components/                      # 24 UI components
│   ├── issue-header.tsx
│   ├── issue-title.tsx             # Click-to-edit, 2s debounce
│   ├── issue-description-editor.tsx # TipTap, 2s debounce
│   ├── issue-properties-panel.tsx
│   ├── sub-issues-list.tsx
│   ├── activity-timeline.tsx        # Infinite scroll
│   ├── ai-context-tab.tsx          # Dynamic import, SSR=false
│   ├── ai-context-panel.tsx
│   ├── ai-context-streaming.tsx
│   ├── context-summary-card.tsx
│   ├── related-*-section.tsx       # Related issues, docs, items
│   ├── ai-tasks-section.tsx
│   ├── prompt-block.tsx
│   ├── linked-prs-list.tsx
│   ├── source-notes-list.tsx
│   ├── conversation-*.tsx          # 3 chat components
│   ├── index.ts
│   └── __tests__/
├── hooks/                          # 15 custom hooks
│   ├── use-issue-detail.ts         # Query (30s stale)
│   ├── use-update-issue.ts         # Mutation + optimistic
│   ├── use-activities.ts           # InfiniteQuery (50/page)
│   ├── use-add-comment.ts          # Mutation + invalidations
│   ├── use-save-status.ts          # MobX UI feedback
│   ├── useAIContext.ts             # Generate + regenerate
│   ├── useAIContextChat.ts         # SSE streaming
│   ├── useExportContext.ts
│   ├── use-workspace-members.ts
│   ├── use-project-cycles.ts
│   ├── use-workspace-labels.ts
│   ├── use-create-sub-issue.ts
│   ├── use-issue-keyboard-shortcuts.ts
│   ├── use-copy-feedback.ts
│   └── index.ts
├── editor/
│   └── create-issue-editor-extensions.ts
└── CLAUDE.md
```

---

## Component Tree (70/30 Layout)

```
IssueDetailPage
├── IssueHeader
├── Main Content (70%)
│   ├── IssueTitle (click-to-edit)
│   ├── IssueDescriptionEditor (TipTap)
│   ├── SubIssuesList
│   ├── ActivityTimeline (infinite scroll)
│   │   ├── CommentInput
│   │   └── ActivityEntry[] (50/page)
│   └── Tabs: "AI Context" | "Details" | "Linked"
└── Sidebar (30%)
    ├── "Details" tab --> IssuePropertiesPanel
    ├── "AI Context" tab --> AIContextTab (dynamic)
    │   ├── ContextSummaryCard
    │   ├── RelatedIssuesSection
    │   ├── RelatedDocsSection
    │   ├── AITasksSection
    │   ├── PromptBlock
    │   └── AIContextStreaming
    └── "Linked" tab --> RelatedItemsList
```

---

## Data Flows

**Issue Detail**: `useIssueDetail(workspaceId, issueId)` -> TanStack Query (30s stale) -> `issuesApi.get()` -> cache update -> UI render.

**Optimistic Update**: User edits -> 2s debounce -> `useUpdateIssue().mutateAsync()` -> onMutate (snapshot + optimistic patch) -> onSuccess (server data) / onError (rollback) -> onSettled (invalidate). See `hooks/use-update-issue.ts`.

**Comment -> Activity**: `useAddComment.mutate(content)` -> POST -> onSettled invalidates activities + issue detail -> `useActivities()` refetches page 1.

**AI Context Generation**: AIContextTab mount -> `useAIContext()` (5min cache) -> POST generate -> backend aggregates (related issues, notes, code, tasks, prompt) -> sections render. See `hooks/useAIContext.ts`.

---

## Hooks Reference

### TanStack Query (Server State)

| Hook | Pattern | Stale Time | Key Feature |
|------|---------|-----------|---|
| `useIssueDetail` | Query | 30s | Enabled gating |
| `useUpdateIssue` | Mutation | -- | Optimistic + rollback |
| `useActivities` | InfiniteQuery | -- | 50/page, sentinel |
| `useAddComment` | Mutation | -- | Invalidates activities |
| `useCreateSubIssue` | Mutation | -- | Invalidates parent |
| `useWorkspaceMembers` | Query | 60s | Enabled gating |
| `useWorkspaceLabels` | Query | 60s | Enabled gating |
| `useProjectCycles` | Query | 60s | Enabled gating |
| `useAIContext` | Query | 5m | Generate/regenerate |
| `useAIContextChat` | -- | -- | SSE message state |

### MobX (UI State)

| Hook/Store | Purpose |
|------------|---------|
| `useSaveStatus(fieldName)` | Per-field save indicator (idle/saving/saved/error) |
| `IssueStore.aggregateSaveStatus` | Priority: saving > error > saved > idle |
| `AIContextStore` | Context generation state (isLoading, phases, error) |

Query key factories: See `hooks/use-issue-detail.ts`, `hooks/use-activities.ts`, `hooks/useAIContext.ts`.

Store implementation: See `stores/features/IssueStore.ts`, `stores/ai/AIContextStore.ts`.

---

## Troubleshooting

| Problem | Cause | Solution |
|---------|-------|----------|
| Save status not showing | useSaveStatus not called consistently | Verify fieldName matches |
| Optimistic update no rollback | onMutate doesn't return snapshot | Check snapshot capture + onError |
| AI Context takes >30s | Search timeouts | Check phases array |
| Infinite scroll not triggering | Sentinel not visible | Verify IntersectionObserver |
| State transition fails | Backend rejects (RLS?) | Check state machine + constraints |

---

## Related Documentation

- **DD-065**: State split (MobX UI, TanStack server)
- **DD-086**: Centralized AI agent architecture
- **DD-003**: Human-in-the-loop approval
- `docs/dev-pattern/45-pilot-space-patterns.md`

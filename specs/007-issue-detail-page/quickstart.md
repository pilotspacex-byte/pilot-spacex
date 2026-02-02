# Quickstart: Issue Detail Page

**Feature**: 007-issue-detail-page
**Branch**: `007-issue-detail-page`

---

## Prerequisites

```bash
cd frontend && pnpm install
pnpm dev  # runs on http://localhost:3000
```

Ensure backend is running on port 8000 with at least one workspace, project, and a few issues with varying states/assignees.

---

## Key Files to Understand

### Existing (read before modifying)

| File | Purpose |
|------|---------|
| `frontend/src/app/(workspace)/[workspaceSlug]/issues/[issueId]/page.tsx` | Current page (399 lines, refactor target) |
| `frontend/src/stores/features/issues/IssueStore.ts` | MobX store (554 lines) |
| `frontend/src/services/api/issues.ts` | API client (14 methods) |
| `frontend/src/features/issues/components/issue-header.tsx` | Header component (reuse) |
| `frontend/src/features/issues/components/ai-context-sidebar.tsx` | AI sidebar (reuse) |
| `frontend/src/components/issues/AssigneeSelector.tsx` | Assignee dropdown (reuse) |
| `frontend/src/components/issues/LabelSelector.tsx` | Label multi-select (reuse) |
| `frontend/src/features/notes/editor/extensions/createEditorExtensions.ts` | TipTap extension factory (reference for description editor) |

### New Files to Create

| File | Purpose |
|------|---------|
| `frontend/src/features/issues/components/issue-title.tsx` | Inline editable title |
| `frontend/src/features/issues/components/issue-description-editor.tsx` | TipTap description editor |
| `frontend/src/features/issues/components/issue-properties-panel.tsx` | Right sidebar properties |
| `frontend/src/features/issues/components/activity-timeline.tsx` | Activity feed |
| `frontend/src/features/issues/components/activity-entry.tsx` | Single activity entry |
| `frontend/src/features/issues/components/comment-input.tsx` | Comment text input |
| `frontend/src/features/issues/components/sub-issues-list.tsx` | Sub-issues with progress |
| `frontend/src/features/issues/components/linked-prs-list.tsx` | GitHub PR links |
| `frontend/src/features/issues/components/source-notes-list.tsx` | Note links |
| `frontend/src/components/issues/IssueTypeSelect.tsx` | Issue type dropdown |
| `frontend/src/components/issues/CycleSelector.tsx` | Cycle assignment dropdown |
| `frontend/src/components/issues/EstimateSelector.tsx` | Story points selector |
| `frontend/src/components/ui/save-status.tsx` | Save indicator component |
| `frontend/src/features/issues/hooks/use-issue-detail.ts` | TanStack Query hook |
| `frontend/src/features/issues/hooks/use-update-issue.ts` | Update mutation hook |
| `frontend/src/features/issues/hooks/use-activities.ts` | Activities infinite query |
| `frontend/src/features/issues/hooks/use-add-comment.ts` | Comment mutation |
| `frontend/src/features/issues/hooks/use-edit-comment.ts` | Edit comment mutation |
| `frontend/src/features/issues/hooks/use-delete-comment.ts` | Delete comment mutation |
| `frontend/src/features/issues/hooks/use-workspace-cycles.ts` | Cycles query |

---

## Development Order

1. **Shared utilities first**: SaveStatus component, TanStack Query hooks
2. **Properties panel**: IssueTypeSelect, CycleSelector, EstimateSelector, then IssuePropertiesPanel
3. **Inline editing**: IssueTitle, IssueDescriptionEditor
4. **Activity timeline**: ActivityEntry, CommentInput, then ActivityTimeline
5. **Linked items**: LinkedPRsList, SourceNotesList, SubIssuesList
6. **Page refactor**: Update IssueDetailPage to compose all new components
7. **Responsive**: Add Tailwind breakpoint classes
8. **Keyboard**: Add keyboard event handlers and focus management

---

## Quality Gates

```bash
pnpm lint && pnpm type-check && pnpm test
```

- All files under 700 lines
- Test coverage >80% for new components
- WCAG 2.2 AA: keyboard nav, ARIA labels, focus rings
- No API data stored in MobX (TanStack Query only)

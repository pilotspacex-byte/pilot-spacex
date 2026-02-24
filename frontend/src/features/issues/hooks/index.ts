/**
 * Issues feature hooks index.
 */

export { useSaveStatus } from './use-save-status';

// T007: Issue detail query
export { useIssueDetail, issueDetailKeys } from './use-issue-detail';

// T008: Issue update mutation with optimistic updates
export { useUpdateIssue, useUpdateIssueState } from './use-update-issue';

// T013: Project cycles query
export { useProjectCycles, projectCyclesKeys } from './use-project-cycles';

// T013a: Sub-issue creation mutation
export { useCreateSubIssue } from './use-create-sub-issue';

// T013b: Workspace members query
export {
  useWorkspaceMembers,
  workspaceMembersKeys,
  type WorkspaceMember,
} from './use-workspace-members';

// T013c: Workspace labels query
export { useWorkspaceLabels, workspaceLabelsKeys } from './use-workspace-labels';

// T009: Activity timeline infinite query
export { useActivities, activitiesKeys } from './use-activities';

// T010: Add comment mutation
export { useAddComment } from './use-add-comment';

// T045: Keyboard navigation for Issue Detail page
export { useIssueKeyboardShortcuts } from './use-issue-keyboard-shortcuts';

// Copy-to-clipboard feedback with auto-reset
export { useCopyFeedback } from './use-copy-feedback';

// Issue list for views (TanStack Query)
export { useIssuesList, issuesListKeys } from './use-issues-list';

// Bulk update for multi-select actions
export { useBulkUpdateIssues } from './use-bulk-update-issues';

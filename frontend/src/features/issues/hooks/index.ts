/**
 * Issues feature hooks index.
 *
 * Phase 8 (US-12 AI Context) hooks + Phase 2 issue detail hooks.
 */

export {
  useAIContext,
  aiContextKeys,
  type UseAIContextOptions,
  type UseAIContextReturn,
} from './useAIContext';

export {
  useAIContextChat,
  type UseAIContextChatOptions,
  type UseAIContextChatReturn,
} from './useAIContextChat';

export {
  useExportContext,
  type UseExportContextOptions,
  type UseExportContextReturn,
} from './useExportContext';

export { useSaveStatus } from './use-save-status';

// T007: Issue detail query
export { useIssueDetail, issueDetailKeys } from './use-issue-detail';

// T008: Issue update mutation with optimistic updates
export { useUpdateIssue } from './use-update-issue';

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

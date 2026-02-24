/**
 * useUpdateIssue - TanStack Query mutation with optimistic updates.
 *
 * T008: Patches issue cache optimistically and rolls back on error.
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { issuesApi } from '@/services/api';
import type { Issue, IssueState, UpdateIssueData } from '@/types';
import { issueDetailKeys } from './use-issue-detail';

/**
 * Build an optimistic patch from mutation data.
 *
 * Only applies fields that map directly between UpdateIssueData and Issue.
 * Relational fields (assignee, labels, state) require server-side resolution
 * and are handled via onSuccess with the full API response.
 */
function buildOptimisticPatch(data: UpdateIssueData): Partial<Issue> {
  const patch: Partial<Issue> = {};

  if (data.name !== undefined) patch.name = data.name;
  if (data.description !== undefined) patch.description = data.description;
  if (data.descriptionHtml !== undefined) patch.descriptionHtml = data.descriptionHtml;
  if (data.priority !== undefined) patch.priority = data.priority;
  if (data.estimatePoints !== undefined) patch.estimatePoints = data.estimatePoints;
  if (data.estimateHours !== undefined) patch.estimateHours = data.estimateHours;
  if (data.startDate !== undefined) patch.startDate = data.startDate;
  if (data.targetDate !== undefined) patch.targetDate = data.targetDate;
  if (data.sortOrder !== undefined) patch.sortOrder = data.sortOrder;
  if (data.assigneeId !== undefined) patch.assigneeId = data.assigneeId;
  if (data.cycleId !== undefined) patch.cycleId = data.cycleId;
  if (data.acceptanceCriteria !== undefined) patch.acceptanceCriteria = data.acceptanceCriteria;
  if (data.technicalRequirements !== undefined)
    patch.technicalRequirements = data.technicalRequirements;

  // Handle clear operations
  if (data.clearAssignee) {
    patch.assigneeId = undefined;
    patch.assignee = null;
  }
  if (data.clearCycle) patch.cycleId = undefined;
  if (data.clearEstimate) {
    patch.estimatePoints = undefined;
    patch.estimateHours = undefined;
  }
  if (data.clearStartDate) patch.startDate = undefined;
  if (data.clearTargetDate) patch.targetDate = undefined;

  return patch;
}

export function useUpdateIssue(workspaceId: string, issueId: string) {
  const queryClient = useQueryClient();
  const queryKey = issueDetailKeys.detail(issueId);

  return useMutation({
    mutationFn: (data: UpdateIssueData) => issuesApi.update(workspaceId, issueId, data),

    onMutate: async (newData) => {
      await queryClient.cancelQueries({ queryKey });
      const previousIssue = queryClient.getQueryData<Issue>(queryKey);

      if (previousIssue) {
        const patch = buildOptimisticPatch(newData);
        queryClient.setQueryData<Issue>(queryKey, {
          ...previousIssue,
          ...patch,
          updatedAt: new Date().toISOString(),
        });
      }

      return { previousIssue };
    },

    onError: (_err, _newData, context) => {
      if (context?.previousIssue) {
        queryClient.setQueryData<Issue>(queryKey, context.previousIssue);
      }
    },

    onSuccess: (updatedIssue) => {
      // Merge server response but preserve the current cached state.
      // useUpdateIssue never mutates state — useUpdateIssueState owns that field.
      // Without this, a concurrent description auto-save can overwrite an optimistic
      // state update with the server's stale state value, causing a visible blink.
      queryClient.setQueryData<Issue>(queryKey, (current) => ({
        ...updatedIssue,
        state: current?.state ?? updatedIssue.state,
      }));
    },

    onSettled: () => {
      queryClient.invalidateQueries({ queryKey });
    },
  });
}

/**
 * useUpdateIssueState - Optimistic state transition with cache sync.
 *
 * Separate from useUpdateIssue because state updates use a dedicated endpoint
 * and optimistically patch only the state field while awaiting full server response.
 */
// Maps IssueState keys to the display names stored in DB (avoids blink on optimistic update).
const STATE_DISPLAY_NAMES: Record<IssueState, string> = {
  backlog: 'Backlog',
  todo: 'Todo',
  in_progress: 'In Progress',
  in_review: 'In Review',
  done: 'Done',
  cancelled: 'Cancelled',
};

export function useUpdateIssueState(workspaceId: string, issueId: string) {
  const queryClient = useQueryClient();
  const queryKey = issueDetailKeys.detail(issueId);

  return useMutation({
    mutationFn: (state: IssueState) => issuesApi.updateState(workspaceId, issueId, state),

    onMutate: async (newState) => {
      await queryClient.cancelQueries({ queryKey });
      const previousIssue = queryClient.getQueryData<Issue>(queryKey);

      if (previousIssue) {
        queryClient.setQueryData<Issue>(queryKey, {
          ...previousIssue,
          state: { ...previousIssue.state, name: STATE_DISPLAY_NAMES[newState] ?? newState },
          updatedAt: new Date().toISOString(),
        });
      }

      return { previousIssue };
    },

    onError: (_err, _state, context) => {
      if (context?.previousIssue) {
        queryClient.setQueryData<Issue>(queryKey, context.previousIssue);
      }
    },

    onSuccess: (updatedIssue) => {
      // Merge server response but preserve any in-flight description changes.
      // useUpdateIssueState never mutates description/descriptionHtml.
      queryClient.setQueryData<Issue>(queryKey, (current) => ({
        ...updatedIssue,
        description: current?.description ?? updatedIssue.description,
        descriptionHtml: current?.descriptionHtml ?? updatedIssue.descriptionHtml,
      }));
    },

    onSettled: () => {
      queryClient.invalidateQueries({ queryKey });
    },
  });
}

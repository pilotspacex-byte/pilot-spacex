/**
 * useUpdateIssue - TanStack Query mutation with optimistic updates.
 *
 * T008: Patches issue cache optimistically and rolls back on error.
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { issuesApi } from '@/services/api';
import type { Issue, UpdateIssueData } from '@/types';
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
  if (data.clearEstimate) patch.estimatePoints = undefined;
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
      // Replace cache with full server response (includes resolved assignee, labels, state)
      queryClient.setQueryData<Issue>(queryKey, updatedIssue);
    },

    onSettled: () => {
      queryClient.invalidateQueries({ queryKey });
    },
  });
}

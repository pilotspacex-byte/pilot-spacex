/**
 * useUpdateIssue - TanStack Query mutation with optimistic updates.
 *
 * T008: Patches issue cache optimistically and rolls back on error.
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { issuesApi } from '@/services/api';
import type { Issue, UpdateIssueData } from '@/types';
import { issueDetailKeys } from './use-issue-detail';

export function useUpdateIssue(workspaceId: string, issueId: string) {
  const queryClient = useQueryClient();
  const queryKey = issueDetailKeys.detail(issueId);

  return useMutation({
    mutationFn: (data: UpdateIssueData) => issuesApi.update(workspaceId, issueId, data),

    onMutate: async (newData) => {
      await queryClient.cancelQueries({ queryKey });
      const previousIssue = queryClient.getQueryData<Issue>(queryKey);

      if (previousIssue) {
        queryClient.setQueryData<Issue>(queryKey, {
          ...previousIssue,
          ...newData,
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

    onSettled: () => {
      queryClient.invalidateQueries({ queryKey });
    },
  });
}

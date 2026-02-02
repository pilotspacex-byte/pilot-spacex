/**
 * useAddComment - TanStack mutation hook for adding comments to an issue.
 *
 * T010: Invalidates activity timeline and issue detail on settlement.
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { issuesApi } from '@/services/api';
import { activitiesKeys } from './use-activities';
import { issueDetailKeys } from './use-issue-detail';

export function useAddComment(workspaceId: string, issueId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (content: string) => issuesApi.addComment(workspaceId, issueId, { content }),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: activitiesKeys.all(issueId) });
      queryClient.invalidateQueries({
        queryKey: issueDetailKeys.detail(issueId),
      });
    },
  });
}

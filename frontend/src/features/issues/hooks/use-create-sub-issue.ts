/**
 * useCreateSubIssue - TanStack Query mutation for creating sub-issues.
 *
 * T013a: Creates a child issue linked to a parent, then invalidates caches.
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { issuesApi } from '@/services/api';
import type { CreateIssueData } from '@/types';
import { issueDetailKeys } from './use-issue-detail';

export function useCreateSubIssue(workspaceId: string, parentId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: Omit<CreateIssueData, 'parentId'>) =>
      issuesApi.create(workspaceId, { ...data, parentId }),

    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: issueDetailKeys.detail(parentId),
      });
      queryClient.invalidateQueries({
        queryKey: issueDetailKeys.all,
      });
    },
  });
}

/**
 * useActivities - TanStack infinite query hook for offset-based activity loading.
 *
 * T009: Loads 50 activities per page with offset pagination.
 */

import { useInfiniteQuery } from '@tanstack/react-query';
import { issuesApi } from '@/services/api';

const PAGE_SIZE = 50;

export const activitiesKeys = {
  all: (issueId: string) => ['issues', issueId, 'activities'] as const,
};

export function useActivities(workspaceId: string, issueId: string) {
  return useInfiniteQuery({
    queryKey: activitiesKeys.all(issueId),
    queryFn: ({ pageParam }) =>
      issuesApi.listActivities(workspaceId, issueId, {
        limit: PAGE_SIZE,
        offset: pageParam,
      }),
    initialPageParam: 0,
    getNextPageParam: (lastPage, allPages) => {
      const nextOffset = allPages.length * PAGE_SIZE;
      return nextOffset < lastPage.total ? nextOffset : undefined;
    },
    enabled: !!workspaceId && !!issueId,
  });
}

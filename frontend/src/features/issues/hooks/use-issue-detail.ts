/**
 * useIssueDetail - TanStack Query hook for fetching a single issue.
 *
 * T007: Provides issue detail data with 30s stale time.
 */

import { useQuery } from '@tanstack/react-query';
import { issuesApi } from '@/services/api';
import type { Issue } from '@/types';

export const issueDetailKeys = {
  all: ['issues'] as const,
  detail: (issueId: string) => ['issues', issueId] as const,
};

export function useIssueDetail(workspaceId: string, issueId: string) {
  return useQuery<Issue>({
    queryKey: issueDetailKeys.detail(issueId),
    queryFn: () => issuesApi.get(workspaceId, issueId),
    enabled: !!workspaceId && !!issueId,
    staleTime: 30_000,
  });
}

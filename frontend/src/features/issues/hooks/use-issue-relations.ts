/**
 * useIssueRelations - TanStack Query hook for fetching issue-to-issue relations.
 *
 * Calls GET /workspaces/{id}/issues/{id}/relations and returns all
 * blocks / blocked_by / duplicates / related links for the given issue.
 */

import { useQuery } from '@tanstack/react-query';
import { issuesApi } from '@/services/api';
import type { IssueRelation } from '@/types';

export const issueRelationsKeys = {
  detail: (workspaceId: string, issueId: string) =>
    ['issues', issueId, 'relations', workspaceId] as const,
};

export function useIssueRelations(workspaceId: string, issueId: string) {
  return useQuery<IssueRelation[]>({
    queryKey: issueRelationsKeys.detail(workspaceId, issueId),
    queryFn: () => issuesApi.getRelations(workspaceId, issueId),
    enabled: !!workspaceId && !!issueId,
    staleTime: 30_000,
  });
}

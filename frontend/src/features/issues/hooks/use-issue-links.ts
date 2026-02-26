/**
 * useIssueLinks - TanStack Query hook for fetching integration links for an issue.
 *
 * Calls GET /integrations/issues/{issueId}/links and returns links split by
 * link_type for direct consumption by UI components.
 */

import { useQuery } from '@tanstack/react-query';
import { integrationsApi } from '@/services/api/integrations';
import type { IntegrationLink } from '@/types';

export const issueLinksKeys = {
  all: ['issue-links'] as const,
  detail: (issueId: string) => ['issue-links', issueId] as const,
  byWorkspace: (workspaceId: string, issueId: string) =>
    ['issue-links', workspaceId, issueId] as const,
};

export interface UseIssueLinksResult {
  commits: IntegrationLink[];
  pullRequests: IntegrationLink[];
  branches: IntegrationLink[];
  allLinks: IntegrationLink[];
  isLoading: boolean;
  error: Error | null;
}

export function useIssueLinks(workspaceId: string, issueId: string): UseIssueLinksResult {
  const { data, isLoading, error } = useQuery<IntegrationLink[], Error>({
    queryKey: issueLinksKeys.byWorkspace(workspaceId, issueId),
    queryFn: () => integrationsApi.getIssueLinks(workspaceId, issueId),
    enabled: !!workspaceId && !!issueId,
    staleTime: 60_000,
  });

  const allLinks = data ?? [];

  return {
    commits: allLinks.filter((link) => link.link_type === 'commit'),
    pullRequests: allLinks.filter((link) => link.link_type === 'pull_request'),
    branches: allLinks.filter((link) => link.link_type === 'branch'),
    allLinks,
    isLoading,
    error,
  };
}

import { useQuery } from '@tanstack/react-query';
import { issuesApi } from '@/services/api';
import type { ImplementContextResponse } from '@/services/api/issues';

export const implementationPlanKeys = {
  all: ['implementation-plan'] as const,
  detail: (issueId: string) => ['implementation-plan', issueId] as const,
};

export function useImplementationPlan(workspaceId: string, issueId: string) {
  return useQuery<ImplementContextResponse>({
    queryKey: implementationPlanKeys.detail(issueId),
    queryFn: () => issuesApi.getImplementContext(workspaceId, issueId),
    staleTime: 5 * 60_000,
    retry: 2,
    enabled: !!issueId && !!workspaceId,
  });
}

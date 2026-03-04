import { useQuery } from '@tanstack/react-query';
import { knowledgeGraphApi } from '@/services/api/knowledge-graph';
import type { GraphNodeType, GraphResponse } from '@/types/knowledge-graph';

export const issueKnowledgeGraphKeys = {
  all: ['knowledge-graph'] as const,
  issue: (issueId: string) => ['knowledge-graph', 'issue', issueId] as const,
  issueWithOptions: (issueId: string, depth?: number, nodeTypes?: GraphNodeType[]) =>
    ['knowledge-graph', 'issue', issueId, depth, nodeTypes] as const,
};

export function useIssueKnowledgeGraph(
  workspaceId: string,
  issueId: string,
  options?: {
    depth?: number;
    nodeTypes?: GraphNodeType[];
    enabled?: boolean;
  }
) {
  return useQuery<GraphResponse>({
    queryKey: issueKnowledgeGraphKeys.issueWithOptions(issueId, options?.depth, options?.nodeTypes),
    queryFn: () =>
      knowledgeGraphApi.getIssueGraph(workspaceId, issueId, {
        depth: options?.depth ?? 2,
        nodeTypes: options?.nodeTypes,
        maxNodes: 50,
      }),
    staleTime: 30_000,
    enabled: options?.enabled !== false && !!issueId && !!workspaceId,
  });
}

import { useQuery } from '@tanstack/react-query';
import { knowledgeGraphApi } from '@/services/api/knowledge-graph';
import type { GraphNodeType, GraphResponse } from '@/types/knowledge-graph';

export const workspaceKnowledgeGraphKeys = {
  all: ['knowledge-graph', 'workspace'] as const,
  overview: (workspaceId: string, nodeTypes?: GraphNodeType[], maxNodes?: number) =>
    ['knowledge-graph', 'workspace', workspaceId, nodeTypes, maxNodes] as const,
};

export function useWorkspaceKnowledgeGraph(
  workspaceId: string,
  options?: {
    nodeTypes?: GraphNodeType[];
    maxNodes?: number;
    enabled?: boolean;
  }
) {
  const nodeTypes = options?.nodeTypes;
  const maxNodes = options?.maxNodes ?? 200;

  return useQuery<GraphResponse>({
    queryKey: workspaceKnowledgeGraphKeys.overview(workspaceId, nodeTypes, maxNodes),
    queryFn: () =>
      knowledgeGraphApi.getWorkspaceOverview(workspaceId, {
        nodeTypes,
        maxNodes,
      }),
    staleTime: 30_000,
    enabled: options?.enabled !== false && !!workspaceId,
  });
}

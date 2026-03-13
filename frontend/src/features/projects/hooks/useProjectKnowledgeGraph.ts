import { useQuery } from '@tanstack/react-query';
import { knowledgeGraphApi } from '@/services/api/knowledge-graph';
import type { GraphNodeType, GraphResponse } from '@/types/knowledge-graph';

export const projectKnowledgeGraphKeys = {
  all: ['knowledge-graph', 'project'] as const,
  project: (projectId: string) => ['knowledge-graph', 'project', projectId] as const,
  projectWithOptions: (projectId: string, depth: number, nodeTypes?: GraphNodeType[]) =>
    ['knowledge-graph', 'project', projectId, depth, nodeTypes] as const,
};

export function useProjectKnowledgeGraph(
  workspaceId: string,
  projectId: string,
  options?: {
    depth?: number;
    nodeTypes?: GraphNodeType[];
    enabled?: boolean;
  }
) {
  const depth = options?.depth ?? 2;
  const nodeTypes = options?.nodeTypes;

  return useQuery<GraphResponse>({
    queryKey: projectKnowledgeGraphKeys.projectWithOptions(projectId, depth, nodeTypes),
    queryFn: () =>
      knowledgeGraphApi.getProjectGraph(workspaceId, projectId, {
        depth,
        nodeTypes,
        maxNodes: 100,
      }),
    staleTime: 30_000,
    enabled: options?.enabled !== false && !!projectId && !!workspaceId,
  });
}

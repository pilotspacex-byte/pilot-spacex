import { apiClient } from './client';
import type {
  GraphEdgeType,
  GraphNodeType,
  GraphResponse,
  GraphQueryParams,
} from '@/types/knowledge-graph';

function _buildGraphQueryParams(
  params?: GraphQueryParams
): Record<string, string | number | boolean> {
  const q: Record<string, string | number | boolean> = {};
  if (params?.depth !== undefined) q.depth = params.depth;
  if (params?.maxNodes !== undefined) q.max_nodes = params.maxNodes;
  if (params?.includeGithub !== undefined) q.include_github = params.includeGithub;
  // Backend expects comma-separated string, not array
  if (params?.nodeTypes?.length) q.node_types = params.nodeTypes.join(',');
  return q;
}

export const knowledgeGraphApi = {
  getIssueGraph(
    workspaceId: string,
    issueId: string,
    params?: GraphQueryParams
  ): Promise<GraphResponse> {
    return apiClient.get<GraphResponse>(
      `/workspaces/${workspaceId}/issues/${issueId}/knowledge-graph`,
      { params: _buildGraphQueryParams(params) }
    );
  },

  getNodeNeighbors(
    workspaceId: string,
    nodeId: string,
    depth?: number,
    edgeTypes?: GraphEdgeType[]
  ): Promise<GraphResponse> {
    const queryParams: Record<string, string | number> = {};
    if (depth !== undefined) queryParams.depth = depth;
    // Backend expects comma-separated string for edge_types
    if (edgeTypes?.length) queryParams.edge_types = edgeTypes.join(',');

    return apiClient.get<GraphResponse>(
      `/workspaces/${workspaceId}/knowledge-graph/nodes/${nodeId}/neighbors`,
      { params: queryParams }
    );
  },

  searchGraph(
    workspaceId: string,
    query: string,
    nodeTypes?: GraphNodeType[],
    limit?: number
  ): Promise<GraphResponse> {
    const queryParams: Record<string, string | number> = { q: query };
    // Backend expects comma-separated string, not array
    if (nodeTypes?.length) queryParams.node_types = nodeTypes.join(',');
    if (limit !== undefined) queryParams.limit = limit;

    return apiClient.get<GraphResponse>(`/workspaces/${workspaceId}/knowledge-graph/search`, {
      params: queryParams,
    });
  },

  getSubgraph(
    workspaceId: string,
    rootId: string,
    params?: { maxDepth?: number; maxNodes?: number }
  ): Promise<GraphResponse> {
    const queryParams: Record<string, string | number> = { root_id: rootId };
    if (params?.maxDepth !== undefined) queryParams.max_depth = params.maxDepth;
    if (params?.maxNodes !== undefined) queryParams.max_nodes = params.maxNodes;

    return apiClient.get<GraphResponse>(`/workspaces/${workspaceId}/knowledge-graph/subgraph`, {
      params: queryParams,
    });
  },

  getProjectGraph(
    workspaceId: string,
    projectId: string,
    params?: GraphQueryParams
  ): Promise<GraphResponse> {
    return apiClient.get<GraphResponse>(
      `/workspaces/${workspaceId}/projects/${projectId}/knowledge-graph`,
      { params: _buildGraphQueryParams(params) }
    );
  },

  getUserContext(workspaceId: string, limit?: number): Promise<GraphResponse> {
    const queryParams: Record<string, number> = {};
    if (limit !== undefined) queryParams.limit = limit;

    return apiClient.get<GraphResponse>(`/workspaces/${workspaceId}/knowledge-graph/user-context`, {
      params: queryParams,
    });
  },
};

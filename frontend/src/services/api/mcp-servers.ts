/**
 * MCP Servers API client.
 *
 * Phase 25: Extended for multi-type servers, bulk import, connection testing,
 * enable/disable, and partial updates (PATCH).
 */
import { apiClient } from '@/services/api/client';
import type {
  MCPServer,
  MCPServerStatus,
  MCPServerListResponse,
  MCPServerRegisterRequest,
  MCPServerUpdateRequest,
  MCPServerTestResult,
  ImportMcpServersResponse,
} from '@/stores/ai/MCPServersStore';

const base = (workspaceId: string) => `/workspaces/${workspaceId}/mcp-servers`;

export const mcpServersApi = {
  /** List all registered MCP servers. GET /workspaces/{id}/mcp-servers */
  list: (workspaceId: string): Promise<MCPServerListResponse> =>
    apiClient.get<MCPServerListResponse>(base(workspaceId)),

  /** Register a new MCP server. POST /workspaces/{id}/mcp-servers */
  register: (workspaceId: string, data: MCPServerRegisterRequest): Promise<MCPServer> =>
    apiClient.post<MCPServer>(base(workspaceId), data),

  /** Partial update. PATCH /workspaces/{id}/mcp-servers/{serverId} */
  update: (
    workspaceId: string,
    serverId: string,
    data: MCPServerUpdateRequest
  ): Promise<MCPServer> =>
    apiClient.patch<MCPServer>(`${base(workspaceId)}/${serverId}`, data),

  /** Legacy status probe. GET /workspaces/{id}/mcp-servers/{serverId}/status */
  checkStatus: (workspaceId: string, serverId: string): Promise<MCPServerStatus> =>
    apiClient.get<MCPServerStatus>(`${base(workspaceId)}/${serverId}/status`),

  /** On-demand connection test. POST /workspaces/{id}/mcp-servers/{serverId}/test */
  testConnection: (workspaceId: string, serverId: string): Promise<MCPServerTestResult> =>
    apiClient.post<MCPServerTestResult>(`${base(workspaceId)}/${serverId}/test`),

  /** Enable server. POST /workspaces/{id}/mcp-servers/{serverId}/enable */
  enable: (workspaceId: string, serverId: string): Promise<void> =>
    apiClient.post<void>(`${base(workspaceId)}/${serverId}/enable`),

  /** Disable server. POST /workspaces/{id}/mcp-servers/{serverId}/disable */
  disable: (workspaceId: string, serverId: string): Promise<void> =>
    apiClient.post<void>(`${base(workspaceId)}/${serverId}/disable`),

  /** Bulk import from JSON config. POST /workspaces/{id}/mcp-servers/import */
  importServers: (workspaceId: string, configJson: string): Promise<ImportMcpServersResponse> =>
    apiClient.post<ImportMcpServersResponse>(`${base(workspaceId)}/import`, {
      config_json: configJson,
    }),

  /** Remove (soft-delete). DELETE /workspaces/{id}/mcp-servers/{serverId} */
  remove: (workspaceId: string, serverId: string): Promise<void> =>
    apiClient.delete<void>(`${base(workspaceId)}/${serverId}`),

  /** Get OAuth URL. GET /workspaces/{id}/mcp-servers/{serverId}/oauth-url */
  getOAuthUrl: (workspaceId: string, serverId: string): Promise<{ auth_url: string }> =>
    apiClient.get<{ auth_url: string }>(`${base(workspaceId)}/${serverId}/oauth-url`),
};

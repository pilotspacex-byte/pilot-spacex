/**
 * MCP Servers API client.
 *
 * Phase 14 Plan 04: Typed API client for workspace remote MCP server CRUD + status + OAuth.
 * Uses apiClient from services/api/client (same pattern as AISettingsStore).
 */
import { apiClient } from '@/services/api/client';
import type {
  MCPServer,
  MCPServerStatus,
  MCPServerListResponse,
  MCPServerRegisterRequest,
} from '@/stores/ai/MCPServersStore';

const base = (workspaceId: string) => `/workspaces/${workspaceId}/mcp-servers`;

export const mcpServersApi = {
  /**
   * List all registered MCP servers for a workspace.
   * GET /workspaces/{workspaceId}/mcp-servers
   */
  list: (workspaceId: string): Promise<MCPServerListResponse> =>
    apiClient.get<MCPServerListResponse>(base(workspaceId)),

  /**
   * Register a new remote MCP server.
   * POST /workspaces/{workspaceId}/mcp-servers
   */
  register: (workspaceId: string, data: MCPServerRegisterRequest): Promise<MCPServer> =>
    apiClient.post<MCPServer>(base(workspaceId), data),

  /**
   * Check connection status of a registered MCP server.
   * GET /workspaces/{workspaceId}/mcp-servers/{serverId}/status
   */
  checkStatus: (workspaceId: string, serverId: string): Promise<MCPServerStatus> =>
    apiClient.get<MCPServerStatus>(`${base(workspaceId)}/${serverId}/status`),

  /**
   * Remove a registered MCP server.
   * DELETE /workspaces/{workspaceId}/mcp-servers/{serverId}
   */
  remove: (workspaceId: string, serverId: string): Promise<void> =>
    apiClient.delete<void>(`${base(workspaceId)}/${serverId}`),

  /**
   * Get the OAuth authorization URL for an OAuth2 MCP server.
   * GET /workspaces/{workspaceId}/mcp-servers/{serverId}/oauth-url
   */
  getOAuthUrl: (workspaceId: string, serverId: string): Promise<{ auth_url: string }> =>
    apiClient.get<{ auth_url: string }>(`${base(workspaceId)}/${serverId}/oauth-url`),
};

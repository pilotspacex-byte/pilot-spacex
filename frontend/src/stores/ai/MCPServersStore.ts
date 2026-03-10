/**
 * MCPServersStore - MobX observable store for workspace MCP server management.
 *
 * Phase 14 Plan 04: Manages registered remote MCP servers including
 * CRUD operations and connection status checking.
 *
 * Pattern: mirrors AISettingsStore pattern exactly.
 */
import { makeAutoObservable, runInAction } from 'mobx';
import { mcpServersApi } from '@/services/api/mcp-servers';

// ============================================================
// Domain types (exported — imported by mcp-servers API client)
// ============================================================

export interface MCPServer {
  id: string;
  workspace_id: string;
  display_name: string;
  url: string;
  auth_type: 'bearer' | 'oauth2';
  last_status: 'connected' | 'failed' | 'unknown' | null;
  last_status_checked_at: string | null;
  created_at: string;
}

export interface MCPServerStatus {
  server_id: string;
  status: 'connected' | 'failed' | 'unknown';
  checked_at: string;
}

export interface MCPServerListResponse {
  items: MCPServer[];
  total: number;
}

export interface MCPServerRegisterRequest {
  display_name: string;
  url: string;
  auth_type: 'bearer' | 'oauth2';
  auth_token?: string;
  oauth_client_id?: string;
  oauth_auth_url?: string;
  oauth_token_url?: string;
  oauth_scopes?: string;
}

// ============================================================
// Store
// ============================================================

export class MCPServersStore {
  servers: MCPServer[] = [];
  isLoading = false;
  isSaving = false;
  error: string | null = null;

  constructor() {
    makeAutoObservable(this);
  }

  async loadServers(workspaceId: string): Promise<void> {
    runInAction(() => {
      this.isLoading = true;
      this.error = null;
    });

    try {
      const data = await mcpServersApi.list(workspaceId);
      runInAction(() => {
        this.servers = data.items;
      });
    } catch (err) {
      runInAction(() => {
        this.error = err instanceof Error ? err.message : 'Failed to load MCP servers';
      });
    } finally {
      runInAction(() => {
        this.isLoading = false;
      });
    }
  }

  async registerServer(workspaceId: string, data: MCPServerRegisterRequest): Promise<void> {
    runInAction(() => {
      this.isSaving = true;
      this.error = null;
    });

    try {
      const server = await mcpServersApi.register(workspaceId, data);
      runInAction(() => {
        this.servers = [...this.servers, server];
        this.isSaving = false;
      });
    } catch (err) {
      runInAction(() => {
        this.error = err instanceof Error ? err.message : 'Failed to register MCP server';
        this.isSaving = false;
      });
      throw err;
    }
  }

  async removeServer(workspaceId: string, serverId: string): Promise<void> {
    try {
      await mcpServersApi.remove(workspaceId, serverId);
      runInAction(() => {
        this.servers = this.servers.filter((s) => s.id !== serverId);
      });
    } catch (err) {
      runInAction(() => {
        this.error = err instanceof Error ? err.message : 'Failed to remove MCP server';
      });
      throw err;
    }
  }

  async refreshStatus(workspaceId: string, serverId: string): Promise<void> {
    try {
      const statusResult = await mcpServersApi.checkStatus(workspaceId, serverId);
      runInAction(() => {
        this.servers = this.servers.map((s) =>
          s.id === serverId
            ? {
                ...s,
                last_status: statusResult.status,
                last_status_checked_at: statusResult.checked_at,
              }
            : s
        );
      });
    } catch (err) {
      runInAction(() => {
        this.error = err instanceof Error ? err.message : 'Failed to refresh server status';
      });
    }
  }

  async getOAuthUrl(workspaceId: string, serverId: string): Promise<string> {
    const result = await mcpServersApi.getOAuthUrl(workspaceId, serverId);
    return result.auth_url;
  }

  reset(): void {
    this.servers = [];
    this.isLoading = false;
    this.isSaving = false;
    this.error = null;
  }
}

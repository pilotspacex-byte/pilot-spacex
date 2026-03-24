/**
 * MCPServersStore - MobX observable store for workspace MCP server management.
 *
 * Phase 25: Extended for multi-type servers (Remote/Command), 5-state status,
 * bulk import, connection testing, and enable/disable toggling.
 */
import { makeAutoObservable, runInAction, computed } from 'mobx';
import { mcpServersApi } from '@/services/api/mcp-servers';

// ============================================================
// Domain types
// ============================================================

export type McpServerType = 'remote' | 'command';
export type McpCommandRunner = 'npx' | 'uvx';
export type McpTransport = 'sse' | 'stdio' | 'streamable_http';
export type McpStatus = 'enabled' | 'disabled' | 'unhealthy' | 'unreachable' | 'config_error';

export interface MCPServer {
  id: string;
  workspace_id: string;
  display_name: string;
  url: string;
  server_type: McpServerType;
  command_runner: McpCommandRunner | null;
  transport: McpTransport;
  url_or_command: string;
  command_args: string | null;
  auth_type: 'none' | 'bearer' | 'oauth2';
  has_auth_secret: boolean;
  has_headers: boolean;
  has_headers_encrypted: boolean;
  has_env_secret: boolean;
  /** Full header key-value pairs (headers are not secret) */
  headers?: Record<string, string> | null;
  /** Env var keys only (values are secret and never returned) */
  env_var_keys?: string[] | null;
  is_enabled: boolean;
  last_status: McpStatus | null;
  last_status_checked_at: string | null;
  created_at: string;
}

export interface MCPServerStatus {
  server_id: string;
  status: McpStatus;
  checked_at: string;
}

export interface MCPServerTestResult {
  server_id: string;
  status: McpStatus;
  latency_ms: number | null;
  checked_at: string;
  error_detail: string | null;
}

export interface MCPServerListResponse {
  items: MCPServer[];
  total: number;
}

export interface MCPServerRegisterRequest {
  display_name: string;
  url?: string;
  server_type?: McpServerType;
  command_runner?: McpCommandRunner;
  transport?: McpTransport;
  url_or_command?: string;
  command_args?: string;
  auth_type: 'none' | 'bearer' | 'oauth2';
  auth_token?: string;
  headers?: Record<string, string>;
  env_vars?: Record<string, string>;
  oauth_client_id?: string;
  oauth_auth_url?: string;
  oauth_token_url?: string;
  oauth_scopes?: string;
}

export interface MCPServerUpdateRequest {
  display_name?: string;
  server_type?: McpServerType;
  command_runner?: McpCommandRunner | null;
  transport?: McpTransport;
  url_or_command?: string;
  command_args?: string | null;
  auth_type?: 'none' | 'bearer' | 'oauth2';
  auth_token?: string;
  headers?: Record<string, string>;
  env_vars?: Record<string, string>;
  oauth_client_id?: string;
  oauth_auth_url?: string;
  oauth_token_url?: string;
  oauth_scopes?: string;
}

export interface ImportMcpServersResponse {
  imported: Array<{ name: string; id: string }>;
  skipped: Array<{ name: string; reason: string }>;
  errors: Array<{ name: string; reason: string }>;
}

// ============================================================
// Filter state
// ============================================================

export interface McpFilterState {
  serverType: McpServerType | 'all';
  status: McpStatus | 'all';
  search: string;
}

// ============================================================
// Store
// ============================================================

export class MCPServersStore {
  servers: MCPServer[] = [];
  isLoading = false;
  isSaving = false;
  error: string | null = null;
  filter: McpFilterState = { serverType: 'all', status: 'all', search: '' };

  constructor() {
    makeAutoObservable(this, {
      filteredServers: computed,
    });
  }

  // ── Computed ──────────────────────────────────────────────

  get filteredServers(): MCPServer[] {
    return this.servers.filter((s) => {
      if (this.filter.serverType !== 'all' && s.server_type !== this.filter.serverType) return false;
      if (this.filter.status !== 'all' && s.last_status !== this.filter.status) return false;
      if (this.filter.search) {
        const q = this.filter.search.toLowerCase();
        const matchesName = s.display_name.toLowerCase().includes(q);
        const matchesUrl = s.url_or_command?.toLowerCase().includes(q);
        if (!matchesName && !matchesUrl) return false;
      }
      return true;
    });
  }

  setFilter(partial: Partial<McpFilterState>): void {
    this.filter = { ...this.filter, ...partial };
  }

  // ── List / Load ──────────────────────────────────────────

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

  // ── Register (create) ────────────────────────────────────

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

  // ── Update (PATCH) ───────────────────────────────────────

  async updateServer(
    workspaceId: string,
    serverId: string,
    data: MCPServerUpdateRequest
  ): Promise<void> {
    runInAction(() => {
      this.isSaving = true;
      this.error = null;
    });

    try {
      const updated = await mcpServersApi.update(workspaceId, serverId, data);
      runInAction(() => {
        this.servers = this.servers.map((s) => (s.id === serverId ? updated : s));
        this.isSaving = false;
      });
    } catch (err) {
      runInAction(() => {
        this.error = err instanceof Error ? err.message : 'Failed to update MCP server';
        this.isSaving = false;
      });
      throw err;
    }
  }

  // ── Remove (DELETE) ──────────────────────────────────────

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

  // ── Test Connection ──────────────────────────────────────

  async testConnection(workspaceId: string, serverId: string): Promise<MCPServerTestResult> {
    try {
      const result = await mcpServersApi.testConnection(workspaceId, serverId);
      runInAction(() => {
        this.servers = this.servers.map((s) =>
          s.id === serverId
            ? { ...s, last_status: result.status, last_status_checked_at: result.checked_at }
            : s
        );
      });
      return result;
    } catch (err) {
      runInAction(() => {
        this.error = err instanceof Error ? err.message : 'Connection test failed';
      });
      throw err;
    }
  }

  // ── Enable / Disable ─────────────────────────────────────

  async enableServer(workspaceId: string, serverId: string): Promise<void> {
    // Optimistic update
    const prev = this.servers.find((s) => s.id === serverId);
    runInAction(() => {
      this.servers = this.servers.map((s) =>
        s.id === serverId ? { ...s, is_enabled: true, last_status: 'enabled' as McpStatus } : s
      );
    });

    try {
      await mcpServersApi.enable(workspaceId, serverId);
    } catch (err) {
      // Revert on failure
      runInAction(() => {
        if (prev) {
          this.servers = this.servers.map((s) => (s.id === serverId ? prev : s));
        }
        this.error = err instanceof Error ? err.message : 'Failed to enable server';
      });
      throw err;
    }
  }

  async disableServer(workspaceId: string, serverId: string): Promise<void> {
    const prev = this.servers.find((s) => s.id === serverId);
    runInAction(() => {
      this.servers = this.servers.map((s) =>
        s.id === serverId ? { ...s, is_enabled: false, last_status: 'disabled' as McpStatus } : s
      );
    });

    try {
      await mcpServersApi.disable(workspaceId, serverId);
    } catch (err) {
      runInAction(() => {
        if (prev) {
          this.servers = this.servers.map((s) => (s.id === serverId ? prev : s));
        }
        this.error = err instanceof Error ? err.message : 'Failed to disable server';
      });
      throw err;
    }
  }

  // ── Bulk Import ───────────────────────────────────────────

  async importServers(
    workspaceId: string,
    configJson: string
  ): Promise<ImportMcpServersResponse> {
    runInAction(() => {
      this.isSaving = true;
      this.error = null;
    });

    try {
      const result = await mcpServersApi.importServers(workspaceId, configJson);
      // Reload the full list after import to get properly typed items
      await this.loadServers(workspaceId);
      runInAction(() => {
        this.isSaving = false;
      });
      return result;
    } catch (err) {
      runInAction(() => {
        this.error = err instanceof Error ? err.message : 'Failed to import servers';
        this.isSaving = false;
      });
      throw err;
    }
  }

  // ── Legacy status refresh ─────────────────────────────────

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

  // ── OAuth ─────────────────────────────────────────────────

  async getOAuthUrl(workspaceId: string, serverId: string): Promise<string> {
    const result = await mcpServersApi.getOAuthUrl(workspaceId, serverId);
    return result.auth_url;
  }

  // ── Reset ─────────────────────────────────────────────────

  reset(): void {
    this.servers = [];
    this.isLoading = false;
    this.isSaving = false;
    this.error = null;
    this.filter = { serverType: 'all', status: 'all', search: '' };
  }
}

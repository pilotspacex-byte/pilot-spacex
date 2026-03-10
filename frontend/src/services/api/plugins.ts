/**
 * Plugins API client.
 *
 * Phase 19 Plan 04: Typed API client for workspace plugin CRUD + GitHub credential management.
 * Uses apiClient from services/api/client (same pattern as mcp-servers.ts).
 */
import { apiClient } from '@/services/api/client';
import type { InstalledPlugin, AvailablePlugin } from '@/stores/ai/PluginsStore';

const base = (workspaceId: string) => `/workspaces/${workspaceId}/plugins`;

export const pluginsApi = {
  /**
   * List all installed plugins for a workspace.
   * GET /workspaces/{workspaceId}/plugins
   */
  getInstalled: (workspaceId: string): Promise<InstalledPlugin[]> =>
    apiClient.get<InstalledPlugin[]>(base(workspaceId)),

  /**
   * Browse available plugins from a GitHub repo.
   * GET /workspaces/{workspaceId}/plugins/browse?repo_url=...
   */
  browse: (workspaceId: string, repoUrl: string): Promise<AvailablePlugin[]> =>
    apiClient.get<AvailablePlugin[]>(`${base(workspaceId)}/browse`, {
      params: { repo_url: repoUrl },
    }),

  /**
   * Install a plugin from a GitHub repo.
   * POST /workspaces/{workspaceId}/plugins
   */
  install: (
    workspaceId: string,
    payload: { repo_url: string; skill_name: string }
  ): Promise<InstalledPlugin> => apiClient.post<InstalledPlugin>(base(workspaceId), payload),

  /**
   * Uninstall a plugin.
   * DELETE /workspaces/{workspaceId}/plugins/{pluginId}
   */
  uninstall: (workspaceId: string, pluginId: string): Promise<void> =>
    apiClient.delete<void>(`${base(workspaceId)}/${pluginId}`),

  /**
   * Check for available updates on installed plugins.
   * GET /workspaces/{workspaceId}/plugins/check-updates
   */
  checkUpdates: (workspaceId: string): Promise<{ plugins: InstalledPlugin[] }> =>
    apiClient.get<{ plugins: InstalledPlugin[] }>(`${base(workspaceId)}/check-updates`),

  /**
   * Save a GitHub PAT for accessing private repos.
   * POST /workspaces/{workspaceId}/plugins/github-credential
   */
  saveGitHubPat: (workspaceId: string, pat: string): Promise<void> =>
    apiClient.post<void>(`${base(workspaceId)}/github-credential`, { pat }),

  /**
   * Get GitHub credential status (has_pat).
   * GET /workspaces/{workspaceId}/plugins/github-credential
   */
  getGitHubCredential: (workspaceId: string): Promise<{ has_pat: boolean }> =>
    apiClient.get<{ has_pat: boolean }>(`${base(workspaceId)}/github-credential`),
};

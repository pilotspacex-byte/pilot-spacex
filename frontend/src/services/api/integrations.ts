/**
 * Integrations API client.
 *
 * T188-T192: API client for GitHub integration feature (US-18).
 */

import { apiClient } from './client';

// ============================================================================
// Types
// ============================================================================

export interface GitHubInstallation {
  id: string;
  installationId: number;
  accountLogin: string;
  accountType: 'User' | 'Organization';
  avatarUrl: string;
  permissions: Record<string, string>;
  repositorySelection: 'all' | 'selected';
  connectedAt: string;
}

export interface GitHubRepository {
  id: string;
  fullName: string;
  name: string;
  owner: string;
  private: boolean;
  defaultBranch: string;
  syncEnabled: boolean;
  webhookActive: boolean;
  lastSyncedAt?: string;
}

export interface GitHubCommit {
  sha: string;
  shortSha: string;
  message: string;
  messageHeadline: string;
  authorName: string;
  authorEmail: string;
  authorAvatarUrl?: string;
  committedAt: string;
  url: string;
}

export interface GitHubPullRequest {
  id: string;
  number: number;
  title: string;
  state: 'open' | 'closed' | 'merged';
  url: string;
  authorLogin: string;
  authorAvatarUrl?: string;
  baseBranch: string;
  headBranch: string;
  createdAt: string;
  updatedAt: string;
  mergedAt?: string;
  closedAt?: string;
  additions: number;
  deletions: number;
  changedFiles: number;
}

export interface GitHubWebhook {
  id: string;
  active: boolean;
  events: string[];
  createdAt: string;
}

export interface BranchNameSuggestion {
  branchName: string;
  gitCommand: string;
  format: string;
}

export interface IntegrationSettings {
  autoTransitionEnabled: boolean;
  branchNamingFormat: string;
  prMergeTransition: string;
  commitMessageFormat?: string;
}

// ============================================================================
// API Client
// ============================================================================

export const integrationsApi = {
  // ============================================================================
  // GitHub Connection
  // ============================================================================

  /**
   * Get GitHub OAuth authorization URL.
   */
  getGitHubAuthUrl(workspaceId: string): Promise<{ url: string; state: string }> {
    return apiClient
      .get<{
        authorize_url: string;
        state: string;
      }>(`/integrations/github/authorize?workspace_id=${workspaceId}`)
      .then((response) => ({
        url: response.authorize_url,
        state: response.state,
      }));
  },

  /**
   * Complete GitHub OAuth callback.
   */
  completeGitHubAuth(
    _workspaceId: string,
    code: string,
    state: string
  ): Promise<GitHubInstallation> {
    // workspace_id is embedded in state, backend extracts it
    return apiClient.post<GitHubInstallation>(`/integrations/github/callback`, { code, state });
  },

  /**
   * Get current GitHub installation.
   * Note: Backend returns IntegrationResponse with different shape.
   */
  getGitHubInstallation(workspaceId: string): Promise<GitHubInstallation | null> {
    return apiClient
      .get<{
        items: Array<{
          id: string;
          provider: string;
          external_account_name: string | null;
          avatar_url: string | null;
          is_active: boolean;
        }>;
      }>(`/integrations?workspace_id=${workspaceId}`)
      .then((response) => {
        // Find active GitHub integration and map to frontend model
        const githubIntegration = response.items?.find(
          (i) => i.provider === 'github' && i.is_active
        );
        if (!githubIntegration) return null;

        // Map backend response to frontend GitHubInstallation
        return {
          id: githubIntegration.id,
          installationId: 0, // Not available from backend
          accountLogin: githubIntegration.external_account_name ?? 'GitHub',
          accountType: 'User' as const,
          avatarUrl: githubIntegration.avatar_url ?? '',
          permissions: {},
          repositorySelection: 'selected' as const,
          connectedAt: new Date().toISOString(),
        };
      })
      .catch(() => null); // Return null on error (not connected)
  },

  /**
   * Disconnect GitHub integration.
   */
  disconnectGitHub(workspaceId: string): Promise<void> {
    return apiClient.delete<void>(`/workspaces/${workspaceId}/integrations/github`);
  },

  // ============================================================================
  // Repositories
  // ============================================================================

  /**
   * List available repositories from GitHub installation.
   */
  listRepositories(workspaceId: string): Promise<GitHubRepository[]> {
    return apiClient.get<GitHubRepository[]>(
      `/workspaces/${workspaceId}/integrations/github/repositories`
    );
  },

  /**
   * Enable/disable sync for a repository.
   */
  toggleRepository(
    workspaceId: string,
    repositoryId: string,
    enabled: boolean
  ): Promise<GitHubRepository> {
    return apiClient.patch<GitHubRepository>(
      `/workspaces/${workspaceId}/integrations/github/repositories/${repositoryId}`,
      { sync_enabled: enabled }
    );
  },

  /**
   * Sync repository data (trigger manual refresh).
   */
  syncRepository(workspaceId: string, repositoryId: string): Promise<void> {
    return apiClient.post<void>(
      `/workspaces/${workspaceId}/integrations/github/repositories/${repositoryId}/sync`
    );
  },

  // ============================================================================
  // Issue Links
  // ============================================================================

  /**
   * Get branch name suggestion for an issue.
   */
  getBranchName(workspaceId: string, issueId: string): Promise<BranchNameSuggestion> {
    return apiClient.get<BranchNameSuggestion>(
      `/workspaces/${workspaceId}/issues/${issueId}/branch-name`
    );
  },

  /**
   * Get commits linked to an issue.
   */
  getIssueCommits(workspaceId: string, issueId: string): Promise<GitHubCommit[]> {
    return apiClient.get<GitHubCommit[]>(`/workspaces/${workspaceId}/issues/${issueId}/commits`);
  },

  /**
   * Get pull requests linked to an issue.
   */
  getIssuePullRequests(workspaceId: string, issueId: string): Promise<GitHubPullRequest[]> {
    return apiClient.get<GitHubPullRequest[]>(
      `/workspaces/${workspaceId}/issues/${issueId}/pull-requests`
    );
  },

  // ============================================================================
  // Webhooks
  // ============================================================================

  /**
   * Get webhook status for a repository.
   */
  getWebhookStatus(workspaceId: string, repositoryId: string): Promise<GitHubWebhook | null> {
    return apiClient.get<GitHubWebhook | null>(
      `/workspaces/${workspaceId}/integrations/github/repositories/${repositoryId}/webhook`
    );
  },

  /**
   * Repair/recreate webhook.
   */
  repairWebhook(workspaceId: string, repositoryId: string): Promise<GitHubWebhook> {
    return apiClient.post<GitHubWebhook>(
      `/workspaces/${workspaceId}/integrations/github/repositories/${repositoryId}/webhook/repair`
    );
  },

  // ============================================================================
  // Settings
  // ============================================================================

  /**
   * Get integration settings.
   */
  getSettings(workspaceId: string): Promise<IntegrationSettings> {
    return apiClient.get<IntegrationSettings>(`/workspaces/${workspaceId}/integrations/settings`);
  },

  /**
   * Update integration settings.
   */
  updateSettings(
    workspaceId: string,
    settings: Partial<IntegrationSettings>
  ): Promise<IntegrationSettings> {
    return apiClient.patch<IntegrationSettings>(
      `/workspaces/${workspaceId}/integrations/settings`,
      settings
    );
  },
};

/**
 * Integrations API client.
 *
 * T188-T192: API client for GitHub integration feature (US-18).
 */

import type { IntegrationLink } from '@/types';
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

/** Wire shape of `link_metadata` for pull_request links (backend `metadata` JSONB column). */
interface PRLinkMetadata {
  /** PR number (integer). */
  number?: number;
  /** PR state from GitHub. */
  state?: 'open' | 'closed' | 'merged';
  head_branch?: string;
  base_branch?: string;
  repository?: string;
  is_draft?: boolean;
  merged_at?: string | null;
  commits_count?: number;
  changed_files?: number;
  additions?: number;
  deletions?: number;
}

/** Wire shape of `link_metadata` for commit links. */
interface CommitLinkMetadata {
  sha?: string;
  message?: string;
  branch?: string;
  repository?: string;
  timestamp?: string;
  files_changed?: number;
  additions?: number;
  deletions?: number;
}

/** Wire shape of `link_metadata` for branch links. */
interface BranchLinkMetadata {
  name?: string;
  repository?: string;
  is_protected?: boolean;
  ahead_by?: number;
  behind_by?: number;
}

/** Wire shape returned by GET /integrations/issues/{issueId}/links */
interface IntegrationLinkRaw {
  id: string;
  issue_id: string;
  integration_id: string;
  link_type: 'commit' | 'pull_request' | 'branch' | 'mention';
  external_id: string;
  external_url: string | null;
  title: string | null;
  author_name: string | null;
  author_avatar_url: string | null;
  /** Serialized as `metadata` by the backend Pydantic schema (DB column alias). */
  metadata?: PRLinkMetadata | CommitLinkMetadata | BranchLinkMetadata | null;
}

interface IntegrationLinksResponse {
  items: IntegrationLinkRaw[];
  total: number;
}

/** Maps a backend PR state string to the frontend union. Returns undefined for unknown values. */
function mapPRStatus(state: string | undefined | null): 'open' | 'closed' | 'merged' | undefined {
  if (state === 'open' || state === 'closed' || state === 'merged') return state;
  return undefined;
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
   * Backend returns ConnectGitHubResponse; we map it to GitHubInstallation.
   */
  completeGitHubAuth(
    _workspaceId: string,
    code: string,
    state: string
  ): Promise<GitHubInstallation> {
    return apiClient
      .post<{
        integration: { id: string; provider: string; is_active: boolean };
        github_login: string;
        github_name: string | null;
        github_avatar_url: string;
      }>(`/integrations/github/callback`, { code, state })
      .then((response) => ({
        id: response.integration.id,
        installationId: 0, // not available from OAuth response
        accountLogin: response.github_login,
        accountType: 'User' as const,
        avatarUrl: response.github_avatar_url,
        permissions: {},
        repositorySelection: 'selected' as const,
        connectedAt: new Date().toISOString(),
      }));
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
   * Disconnect GitHub integration for a workspace.
   */
  disconnectGitHub(workspaceId: string): Promise<void> {
    return apiClient.delete<void>(`/integrations/workspaces/${workspaceId}/github`);
  },

  // ============================================================================
  // Repositories
  // ============================================================================

  /**
   * List available repositories from the active GitHub integration for a workspace.
   */
  listRepositories(workspaceId: string): Promise<GitHubRepository[]> {
    return apiClient
      .get<{
        items: Array<{
          id: string | number;
          name: string;
          full_name: string;
          private: boolean;
          default_branch: string;
          description: string | null;
          html_url: string;
        }>;
      }>(`/integrations/workspaces/${workspaceId}/github/repositories`)
      .then((response) =>
        (response.items ?? []).map((r) => ({
          id: String(r.id),
          fullName: r.full_name,
          name: r.name,
          owner: r.full_name.split('/')[0] ?? '',
          private: r.private,
          defaultBranch: r.default_branch,
          syncEnabled: false,
          webhookActive: false,
        }))
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
   * Get all integration links for an issue.
   * Backend enforces workspace membership via RLS; workspaceId is used only
   * to satisfy the enabled guard in the hook.
   */
  getIssueLinks(_workspaceId: string, issueId: string): Promise<IntegrationLink[]> {
    return apiClient
      .get<IntegrationLinksResponse>(`/integrations/issues/${issueId}/links`)
      .then((response) =>
        response.items.map((raw): IntegrationLink => {
          const isPR = raw.link_type === 'pull_request';
          const prMeta = isPR ? (raw.metadata as PRLinkMetadata | undefined | null) : null;

          const isCommit = raw.link_type === 'commit';
          const commitMeta = isCommit
            ? (raw.metadata as CommitLinkMetadata | undefined | null)
            : null;

          return {
            id: raw.id,
            issueId: raw.issue_id,
            // pull_request → 'github_pr'; all other types fall back to 'github_issue'
            integrationType: isPR
              ? 'github_pr'
              : raw.link_type === 'commit'
                ? 'github_commit'
                : 'github_issue',
            externalId: raw.external_id,
            externalUrl: raw.external_url ?? '',
            link_type: raw.link_type,
            title: raw.title ?? undefined,
            authorName: raw.author_name ?? undefined,
            authorAvatarUrl: raw.author_avatar_url,
            // PR-specific fields: number and state from link_metadata, title from the
            // dedicated title column (backend populates it from GitHub's PR.title).
            prNumber:
              prMeta?.number ??
              (raw.external_id ? parseInt(raw.external_id, 10) || undefined : undefined),
            prTitle: isPR ? (raw.title ?? undefined) : undefined,
            prStatus: mapPRStatus(prMeta?.state),
            // Commit timestamp from metadata (used by stale issue detection).
            commitTimestamp: commitMeta?.timestamp ?? undefined,
          };
        })
      );
  },

  /**
   * Get branch name suggestion for an issue.
   */
  getBranchName(workspaceId: string, issueId: string): Promise<BranchNameSuggestion> {
    return apiClient.get<BranchNameSuggestion>(
      `/workspaces/${workspaceId}/issues/${issueId}/branch-name`
    );
  },

  /**
   * Create a GitHub branch from an issue.
   * POST /integrations/issues/{issueId}/links/branch?integration_id={integrationId}
   */
  createBranch(
    _workspaceId: string,
    issueId: string,
    integrationId: string,
    data: { repository: string; branch_name: string; base_branch?: string }
  ): Promise<IntegrationLink> {
    return apiClient
      .post<IntegrationLinkRaw>(
        `/integrations/issues/${issueId}/links/branch?integration_id=${integrationId}`,
        data
      )
      .then(
        (raw): IntegrationLink => ({
          id: raw.id,
          issueId: raw.issue_id,
          integrationType: 'github_issue',
          externalId: raw.external_id,
          externalUrl: raw.external_url ?? '',
          link_type: raw.link_type,
          title: raw.title ?? undefined,
          authorName: raw.author_name ?? undefined,
          authorAvatarUrl: raw.author_avatar_url,
        })
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

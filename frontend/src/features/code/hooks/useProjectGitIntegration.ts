import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/services/api/client';

// ─── Backend response shape ───────────────────────────────────────────────────

interface IntegrationItem {
  id: string;
  provider: string;
  is_active: boolean;
  config?: {
    repo_owner?: string;
    repo_name?: string;
    repo_full_name?: string;
    /** Some integrations store the linked project ID. */
    project_id?: string;
  } | null;
}

interface IntegrationsListResponse {
  items: IntegrationItem[];
}

// ─── Return type ─────────────────────────────────────────────────────────────

export interface ProjectGitIntegration {
  /** GitHub repository owner (org or user login). */
  owner: string | null;
  /** GitHub repository name (without owner prefix). */
  repo: string | null;
  /** Integration record ID (for API calls that need it). */
  integrationId: string | null;
  /** Whether the workspace has a connected GitHub integration. */
  isConnected: boolean;
  isLoading: boolean;
}

// ─── Helper ──────────────────────────────────────────────────────────────────

function parseOwnerRepo(item: IntegrationItem): { owner: string | null; repo: string | null } {
  const cfg = item.config;
  if (!cfg) return { owner: null, repo: null };

  // Prefer explicit fields
  if (cfg.repo_owner && cfg.repo_name) {
    return { owner: cfg.repo_owner, repo: cfg.repo_name };
  }

  // Fall back to parsing repo_full_name ("owner/repo")
  if (cfg.repo_full_name) {
    const parts = cfg.repo_full_name.split('/');
    if (parts.length === 2 && parts[0] && parts[1]) {
      return { owner: parts[0], repo: parts[1] };
    }
  }

  return { owner: null, repo: null };
}

// ─── Hook ─────────────────────────────────────────────────────────────────────

/**
 * useProjectGitIntegration — TanStack Query hook that fetches workspace integrations
 * and extracts the GitHub owner/repo for the given project.
 *
 * Query key: ['project-git-integration', workspaceId, projectId]
 * staleTime: 5 minutes (integration config rarely changes)
 *
 * @param projectId  - The project UUID (used for project-level integration filtering)
 * @param workspaceId - The workspace UUID
 * @returns owner, repo, integrationId, isConnected, isLoading
 */
export function useProjectGitIntegration(
  projectId: string | null | undefined,
  workspaceId: string | null | undefined
): ProjectGitIntegration {
  const query = useQuery<ProjectGitIntegration>({
    queryKey: ['project-git-integration', workspaceId, projectId],
    queryFn: async (): Promise<ProjectGitIntegration> => {
      const response = await apiClient.get<IntegrationsListResponse>(
        `/workspaces/${workspaceId!}/integrations`
      );

      const items = response.items ?? [];

      // Priority 1: GitHub integration linked to this specific project
      let githubItem = items.find(
        (i) =>
          i.provider === 'github' &&
          i.is_active &&
          i.config?.project_id === projectId
      );

      // Priority 2: First active GitHub integration (workspace-level)
      if (!githubItem) {
        githubItem = items.find((i) => i.provider === 'github' && i.is_active);
      }

      if (!githubItem) {
        return { owner: null, repo: null, integrationId: null, isConnected: false, isLoading: false };
      }

      const { owner, repo } = parseOwnerRepo(githubItem);
      const isConnected = owner !== null && repo !== null;

      return {
        owner,
        repo,
        integrationId: githubItem.id,
        isConnected,
        isLoading: false,
      };
    },
    enabled: Boolean(workspaceId) && Boolean(projectId),
    staleTime: 5 * 60 * 1000, // 5 minutes — integration config rarely changes
    select: (data) => data,
  });

  if (query.isLoading) {
    return { owner: null, repo: null, integrationId: null, isConnected: false, isLoading: true };
  }

  return query.data ?? { owner: null, repo: null, integrationId: null, isConnected: false, isLoading: false };
}

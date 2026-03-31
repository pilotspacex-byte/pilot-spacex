import { useQuery } from '@tanstack/react-query';
import { listBranches } from '@/services/api/git-proxy';
import type { BranchInfo } from '../git-types';

/**
 * useBranches — TanStack Query hook for listing repository branches.
 *
 * Supports optional search filtering for the BranchSelector dropdown.
 *
 * @param workspaceId - workspace UUID
 * @param owner - GitHub repository owner
 * @param repo - GitHub repository name
 * @param search - Optional search string to filter branches
 */
export function useBranches(
  workspaceId: string | null | undefined,
  owner: string | null | undefined,
  repo: string | null | undefined,
  search?: string
) {
  const enabled = Boolean(workspaceId) && Boolean(owner) && Boolean(repo);

  const query = useQuery<BranchInfo[]>({
    queryKey: ['git-branches', workspaceId, owner, repo, search],
    queryFn: async () => {
      const response = await listBranches(workspaceId!, owner!, repo!, search || undefined);
      return response.branches;
    },
    enabled,
  });

  return {
    ...query,
    branches: query.data ?? [],
    isLoading: query.isLoading,
  };
}

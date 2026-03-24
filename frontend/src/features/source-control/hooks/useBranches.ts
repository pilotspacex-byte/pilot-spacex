import { useQuery } from '@tanstack/react-query';
import { listBranches } from '@/services/api/git-proxy';
import type { BranchInfo, GitRepo } from '@/features/source-control/types';

/**
 * TanStack Query hook for listing repository branches.
 *
 * Supports optional search filtering for the branch selector.
 */
export function useBranches(repo: GitRepo | null, search?: string) {
  const query = useQuery<BranchInfo[]>({
    queryKey: ['git-branches', repo?.owner, repo?.repo, search],
    queryFn: async () => {
      const response = await listBranches(
        repo!.owner,
        repo!.repo,
        repo!.integrationId,
        search || undefined
      );
      return response.branches;
    },
    enabled: !!repo,
  });

  return {
    ...query,
    branches: query.data ?? [],
    isLoading: query.isLoading,
  };
}

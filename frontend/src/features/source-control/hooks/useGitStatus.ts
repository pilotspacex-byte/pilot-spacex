import { useQuery, useQueryClient } from '@tanstack/react-query';
import { getRepoStatus } from '@/services/api/git-proxy';
import { useGitWebStore } from '@/stores/RootStore';
import type { GitRepo, GitStatusResponse } from '@/features/source-control/types';

/**
 * TanStack Query hook for fetching git repository status.
 *
 * Polls every 30s for live updates and syncs changed files
 * into the GitWebStore on success.
 */
export function useGitStatus(repo: GitRepo | null, branch: string) {
  const gitWebStore = useGitWebStore();
  const queryClient = useQueryClient();

  const query = useQuery<GitStatusResponse>({
    queryKey: ['git-status', repo?.owner, repo?.repo, branch],
    queryFn: () =>
      getRepoStatus(repo!.owner, repo!.repo, repo!.integrationId, branch, repo!.defaultBranch),
    enabled: !!repo && branch.length > 0,
    refetchInterval: 30_000,
    select: (data) => {
      // Sync to MobX store on each successful fetch
      gitWebStore.setChangedFiles(data.files);
      return data;
    },
  });

  const refresh = () => {
    void queryClient.invalidateQueries({
      queryKey: ['git-status', repo?.owner, repo?.repo, branch],
    });
  };

  return { ...query, refresh };
}

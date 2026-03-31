import { useQuery, useQueryClient } from '@tanstack/react-query';
import { getRepoStatus } from '@/services/api/git-proxy';
import { useGitStore } from '@/stores/RootStore';
import type { GitStatusResponse } from '../git-types';

/**
 * useGitStatus — TanStack Query hook for fetching git repository status.
 *
 * Polls every 30s for live file change updates. On success, syncs the
 * changed files into GitStore so the SourceControlPanel stays reactive.
 *
 * @param workspaceId - workspace UUID
 * @param owner - GitHub repository owner
 * @param repo - GitHub repository name
 * @param branch - Current branch (defaults to empty string to disable)
 */
export function useGitStatus(
  workspaceId: string | null | undefined,
  owner: string | null | undefined,
  repo: string | null | undefined,
  branch: string | null | undefined
) {
  const gitStore = useGitStore();
  const queryClient = useQueryClient();

  const enabled = Boolean(workspaceId) && Boolean(owner) && Boolean(repo) && Boolean(branch);

  const query = useQuery<GitStatusResponse>({
    queryKey: ['git-status', workspaceId, owner, repo, branch],
    queryFn: async () => {
      const data = await getRepoStatus(workspaceId!, owner!, repo!, branch!);
      // Sync changed files into MobX store, adding client-side staged=false
      gitStore.setChangedFiles(data.files.map((f) => ({ ...f, staged: false })));
      // Sync branch name if the server reports it
      if (data.branch) {
        gitStore.setBranch(data.branch);
      }
      return data;
    },
    enabled,
    refetchInterval: 30_000,
  });

  const refresh = () => {
    void queryClient.invalidateQueries({
      queryKey: ['git-status', workspaceId, owner, repo, branch],
    });
  };

  return { ...query, refresh };
}

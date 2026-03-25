import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { createCommit, getFileContent } from '@/services/api/git-proxy';
import { useGitWebStore } from '@/stores/RootStore';
import type { CommitResult, FileChange, GitRepo } from '@/features/source-control/types';

/**
 * TanStack Query mutation hook for creating a commit.
 *
 * Fetches current content for each staged file, then creates a commit
 * via the git proxy. On success, invalidates the status query and
 * clears the commit state in the store.
 */
export function useCommit(repo: GitRepo | null) {
  const gitWebStore = useGitWebStore();
  const queryClient = useQueryClient();

  const mutation = useMutation<CommitResult, Error, { branch: string; message: string }>({
    mutationFn: async ({ branch, message }) => {
      if (!repo) throw new Error('No repository configured');

      const stagedFiles = gitWebStore.stagedFiles;
      if (stagedFiles.length === 0) throw new Error('No staged files');

      // Fetch current content for each staged file
      const files: FileChange[] = await Promise.all(
        stagedFiles.map(async (f: { path: string; status: string }) => {
          if (f.status === 'deleted') {
            return { path: f.path, content: '', action: 'delete' as const };
          }
          const fileContent = await getFileContent(
            repo.owner,
            repo.repo,
            repo.integrationId,
            f.path,
            branch
          );
          return {
            path: f.path,
            content: fileContent.content,
            encoding: fileContent.encoding,
            action: f.status === 'added' ? ('create' as const) : ('update' as const),
          };
        })
      );

      return createCommit(repo.owner, repo.repo, repo.integrationId, branch, message, files);
    },
    onSuccess: (data) => {
      gitWebStore.clearAfterCommit();
      void queryClient.invalidateQueries({ queryKey: ['git-status'] });
      toast.success(`Committed: ${data.message.slice(0, 50)}`);
    },
    onError: (error) => {
      toast.error(`Commit failed: ${error.message}`);
    },
  });

  return {
    commit: mutation.mutate,
    isCommitting: mutation.isPending,
  };
}

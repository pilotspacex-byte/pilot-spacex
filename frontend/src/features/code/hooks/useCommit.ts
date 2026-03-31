import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { createCommit, getFileContent } from '@/services/api/git-proxy';
import { useGitStore } from '@/stores/RootStore';
import type { ChangedFile, CommitResult, FileChange } from '../git-types';

/**
 * useCommit — TanStack mutation hook for creating a commit.
 *
 * For each staged file, fetches current content from the git proxy
 * (except deleted files which use empty content), then creates a commit.
 *
 * On success:
 * - Clears staged state from GitStore
 * - Invalidates git-status query to trigger a refresh
 * - Shows a success toast
 *
 * @param workspaceId - workspace UUID
 * @param owner - GitHub repository owner
 * @param repo - GitHub repository name
 */
export function useCommit(
  workspaceId: string | null | undefined,
  owner: string | null | undefined,
  repo: string | null | undefined
) {
  const gitStore = useGitStore();
  const queryClient = useQueryClient();

  const mutation = useMutation<
    CommitResult,
    Error,
    { branch: string; message: string }
  >({
    mutationFn: async ({ branch, message }) => {
      if (!workspaceId || !owner || !repo) throw new Error('No repository configured');

      const stagedFiles = gitStore.changedFiles.filter((f: ChangedFile) => f.staged);
      if (stagedFiles.length === 0) throw new Error('No staged files');

      // Fetch content for each staged file
      const files: FileChange[] = await Promise.all(
        stagedFiles.map(async (f: ChangedFile) => {
          if (f.status === 'deleted') {
            return { path: f.path, content: '', action: 'delete' as const };
          }
          const fileContent = await getFileContent(workspaceId, owner, repo, f.path, branch);
          return {
            path: f.path,
            content: fileContent.content,
            encoding: fileContent.encoding,
            action: f.status === 'added' ? ('create' as const) : ('update' as const),
          };
        })
      );

      return createCommit(workspaceId, owner, repo, branch, message, files);
    },
    onSuccess: (data) => {
      // Unstage all files after successful commit
      gitStore.setChangedFiles(
        gitStore.changedFiles.map((f) => ({ ...f, staged: false }))
      );
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

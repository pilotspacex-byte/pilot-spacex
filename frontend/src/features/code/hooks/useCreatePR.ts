import { useMutation } from '@tanstack/react-query';
import { toast } from 'sonner';
import { createPR } from '@/services/api/git-proxy';
import type { PullRequestResult } from '../git-types';

interface CreatePRParams {
  title: string;
  body: string;
  head: string;
  base: string;
  draft: boolean;
}

/**
 * useCreatePR — TanStack mutation hook for creating a pull request.
 *
 * On success:
 * - Shows a toast with the PR number and an "Open" action
 * - Opens the PR URL in a new tab
 *
 * On error: shows an error toast.
 *
 * @param workspaceId - workspace UUID
 * @param owner - GitHub repository owner
 * @param repo - GitHub repository name
 */
export function useCreatePR(
  workspaceId: string | null | undefined,
  owner: string | null | undefined,
  repo: string | null | undefined
) {
  const mutation = useMutation<PullRequestResult, Error, CreatePRParams>({
    mutationFn: async (params) => {
      if (!workspaceId || !owner || !repo) throw new Error('No repository configured');
      return createPR(
        workspaceId,
        owner,
        repo,
        params.title,
        params.body,
        params.head,
        params.base,
        params.draft
      );
    },
    onSuccess: (data) => {
      toast.success(`PR #${data.number} created`, {
        description: data.title,
        action: {
          label: 'Open',
          onClick: () => window.open(data.htmlUrl, '_blank'),
        },
      });
    },
    onError: (error) => {
      toast.error('Failed to create pull request', {
        description: error.message,
      });
    },
  });

  return {
    createPR: mutation.mutate,
    isCreating: mutation.isPending,
  };
}

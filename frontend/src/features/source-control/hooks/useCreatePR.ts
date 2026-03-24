import { useMutation } from '@tanstack/react-query';
import { createPR } from '@/services/api/git-proxy';
import { toast } from 'sonner';
import type { GitRepo, PullRequestResult } from '@/features/source-control/types';

interface CreatePRParams {
  title: string;
  body: string;
  head: string;
  base: string;
  draft: boolean;
}

/**
 * Mutation hook for creating a pull request.
 *
 * On success: shows toast with PR number and opens PR URL in new tab.
 * On error: shows error toast.
 */
export function useCreatePR(repo: GitRepo | null) {
  const mutation = useMutation<PullRequestResult, Error, CreatePRParams>({
    mutationFn: async (params) => {
      if (!repo) throw new Error('No repository configured');
      return createPR(
        repo.owner,
        repo.repo,
        repo.integrationId,
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
      window.open(data.htmlUrl, '_blank');
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

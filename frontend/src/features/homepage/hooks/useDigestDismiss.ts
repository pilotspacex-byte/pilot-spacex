'use client';

/**
 * useDigestDismiss (H042) — TanStack Query mutation for dismissing digest suggestions.
 * Performs optimistic removal from the suggestion list with rollback on error.
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { queryKeys } from '@/lib/queryClient';
import { homepageApi } from '../api/homepage-api';
import type { DigestResponse, DismissSuggestionPayload } from '../types';

export interface UseDigestDismissOptions {
  workspaceId: string;
}

export function useDigestDismiss({ workspaceId }: UseDigestDismissOptions) {
  const queryClient = useQueryClient();
  const digestKey = queryKeys.homepage.digest(workspaceId);

  return useMutation({
    mutationFn: (payload: DismissSuggestionPayload) =>
      homepageApi.dismissSuggestion(workspaceId, payload),

    // Optimistic removal
    onMutate: async (payload) => {
      await queryClient.cancelQueries({ queryKey: digestKey });

      const previousDigest = queryClient.getQueryData<DigestResponse>(digestKey);

      if (previousDigest) {
        queryClient.setQueryData<DigestResponse>(digestKey, {
          ...previousDigest,
          data: {
            ...previousDigest.data,
            suggestions: previousDigest.data.suggestions.filter(
              (s) => s.id !== payload.suggestion_id
            ),
            suggestion_count: previousDigest.data.suggestion_count - 1,
          },
        });
      }

      return { previousDigest };
    },

    // Rollback on error
    onError: (_err, _payload, context) => {
      if (context?.previousDigest) {
        queryClient.setQueryData<DigestResponse>(digestKey, context.previousDigest);
      }
    },

    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: digestKey });
    },
  });
}

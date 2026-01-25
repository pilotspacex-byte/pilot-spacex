/**
 * usePRReview - Hook for triggering AI-powered PR review.
 *
 * T200: Provides mutation to trigger review and polling status.
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { apiClient } from '@/services/api';

// ============================================================================
// Types
// ============================================================================

interface TriggerReviewResponse {
  reviewId: string;
  status: 'processing' | 'queued';
  estimatedTime?: number;
}

// ============================================================================
// Query Keys
// ============================================================================

export const prReviewKeys = {
  all: ['pr-review'] as const,
  status: (integrationId: string, prNumber: number) =>
    [...prReviewKeys.all, 'status', integrationId, prNumber] as const,
};

// ============================================================================
// API Functions
// ============================================================================

async function triggerPRReview(
  integrationId: string,
  prNumber: number
): Promise<TriggerReviewResponse> {
  return apiClient.post<TriggerReviewResponse>(`/integrations/${integrationId}/pr-review`, {
    prNumber,
  });
}

// ============================================================================
// Hook
// ============================================================================

export interface UsePRReviewOptions {
  /** Called when review starts successfully */
  onSuccess?: (data: TriggerReviewResponse) => void;
  /** Called when review trigger fails */
  onError?: (error: Error) => void;
}

export interface UsePRReviewReturn {
  /** Trigger a new PR review */
  trigger: () => void;
  /** Whether review is being triggered */
  isTriggering: boolean;
  /** Error from last trigger attempt */
  error: Error | null;
}

export function usePRReview(
  integrationId: string,
  prNumber: number,
  options?: UsePRReviewOptions
): UsePRReviewReturn {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: () => triggerPRReview(integrationId, prNumber),
    onSuccess: (data) => {
      // Invalidate status query to start polling
      queryClient.invalidateQueries({
        queryKey: prReviewKeys.status(integrationId, prNumber),
      });
      toast.success('PR review started', {
        description: `Estimated time: ${data.estimatedTime ? `${data.estimatedTime}s` : 'a few minutes'}`,
      });
      options?.onSuccess?.(data);
    },
    onError: (error: Error) => {
      toast.error('Failed to start PR review', {
        description: error.message,
      });
      options?.onError?.(error);
    },
  });

  return {
    trigger: () => mutation.mutate(),
    isTriggering: mutation.isPending,
    error: mutation.error,
  };
}

export default usePRReview;

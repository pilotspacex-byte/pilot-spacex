/**
 * usePRReviewStatus - Hook for fetching PR review status and results.
 *
 * T200: Polls for status updates during processing, returns final results.
 */

import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/services/api';
import type { ReviewResult } from '@/components/integrations/PRReviewStatus';
import { prReviewKeys } from './usePRReview';

// ============================================================================
// API Functions
// ============================================================================

async function getPRReviewStatus(
  integrationId: string,
  prNumber: number
): Promise<ReviewResult | null> {
  try {
    return await apiClient.get<ReviewResult>(
      `/integrations/${integrationId}/pr-review/${prNumber}/status`
    );
  } catch (error) {
    // Return null if no review exists (404)
    if (error instanceof Error && error.message.includes('404')) {
      return null;
    }
    throw error;
  }
}

// ============================================================================
// Hook
// ============================================================================

export interface UsePRReviewStatusOptions {
  /** Whether to enable polling */
  enablePolling?: boolean;
  /** Polling interval in ms (default: 3000) */
  pollInterval?: number;
  /** Whether the query is enabled */
  enabled?: boolean;
}

export interface UsePRReviewStatusReturn {
  /** Review result data */
  data: ReviewResult | null | undefined;
  /** Whether data is loading */
  isLoading: boolean;
  /** Whether data is being refetched */
  isRefetching: boolean;
  /** Error from fetch */
  error: Error | null;
  /** Refetch function */
  refetch: () => void;
}

export function usePRReviewStatus(
  integrationId: string,
  prNumber: number,
  options?: UsePRReviewStatusOptions
): UsePRReviewStatusReturn {
  const { enablePolling = true, pollInterval = 3000, enabled = true } = options ?? {};

  const query = useQuery({
    queryKey: prReviewKeys.status(integrationId, prNumber),
    queryFn: () => getPRReviewStatus(integrationId, prNumber),
    enabled: enabled && !!integrationId && !!prNumber,
    // Poll while processing
    refetchInterval: (query) => {
      if (!enablePolling) return false;
      const data = query.state.data;
      // Keep polling if processing
      if (data?.status === 'processing' || data?.status === 'pending') {
        return pollInterval;
      }
      return false;
    },
    // Don't refetch on window focus during processing
    refetchOnWindowFocus: (query) => {
      const data = query.state.data;
      return data?.status !== 'processing';
    },
    staleTime: 5000,
  });

  return {
    data: query.data,
    isLoading: query.isLoading,
    isRefetching: query.isRefetching,
    error: query.error,
    refetch: () => query.refetch(),
  };
}

export default usePRReviewStatus;

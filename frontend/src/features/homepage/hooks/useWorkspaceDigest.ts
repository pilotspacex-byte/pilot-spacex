'use client';

/**
 * useWorkspaceDigest (H041) — TanStack Query hook for AI digest suggestions.
 * Fetches digest with 5-min stale time.
 *
 * NOTE: Supabase Realtime subscription for digest_updated was removed because
 * no backend code currently broadcasts this event. Re-add when server-side
 * broadcast is implemented in the digest worker.
 */

import { useQuery } from '@tanstack/react-query';
import { queryKeys } from '@/lib/queryClient';
import { homepageApi } from '../api/homepage-api';
import { DIGEST_STALE_TIME } from '../constants';

export interface UseWorkspaceDigestOptions {
  workspaceId: string;
  enabled?: boolean;
}

export function useWorkspaceDigest({ workspaceId, enabled = true }: UseWorkspaceDigestOptions) {
  return useQuery({
    queryKey: queryKeys.homepage.digest(workspaceId),
    queryFn: () => homepageApi.getDigest(workspaceId),
    enabled: enabled && !!workspaceId,
    staleTime: DIGEST_STALE_TIME,
    gcTime: 10 * 60 * 1000, // 10 minutes
    refetchOnWindowFocus: false,
  });
}

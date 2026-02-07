'use client';

/**
 * useWorkspaceDigest (H041) — TanStack Query hook for AI digest suggestions.
 * Fetches digest with 5-min stale time. Subscribes to Supabase Realtime for
 * server-triggered refresh events.
 */

import { useEffect } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { supabase } from '@/lib/supabase';
import { queryKeys } from '@/lib/queryClient';
import { homepageApi } from '../api/homepage-api';
import { DIGEST_STALE_TIME } from '../constants';

export interface UseWorkspaceDigestOptions {
  workspaceId: string;
  enabled?: boolean;
}

export function useWorkspaceDigest({ workspaceId, enabled = true }: UseWorkspaceDigestOptions) {
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: queryKeys.homepage.digest(workspaceId),
    queryFn: () => homepageApi.getDigest(workspaceId),
    enabled: enabled && !!workspaceId,
    staleTime: DIGEST_STALE_TIME,
    gcTime: 10 * 60 * 1000, // 10 minutes
    refetchOnWindowFocus: false,
  });

  // Subscribe to Supabase Realtime for digest regeneration events
  useEffect(() => {
    if (!workspaceId) return;

    const channel = supabase
      .channel(`homepage-digest:${workspaceId}`)
      .on('broadcast', { event: 'digest_updated' }, () => {
        queryClient.invalidateQueries({
          queryKey: queryKeys.homepage.digest(workspaceId),
        });
      })
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, [workspaceId, queryClient]);

  return query;
}

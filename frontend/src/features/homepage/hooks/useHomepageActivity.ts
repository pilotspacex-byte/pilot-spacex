'use client';

/**
 * useHomepageActivity (H034) — TanStack Query infinite query for activity feed.
 * Subscribes to Supabase Realtime for live updates.
 */

import { useEffect } from 'react';
import { useInfiniteQuery, useQueryClient } from '@tanstack/react-query';
import { supabase } from '@/lib/supabase';
import { queryKeys } from '@/lib/queryClient';
import { homepageApi } from '../api/homepage-api';
import { ACTIVITY_STALE_TIME } from '../constants';
import type { HomepageActivityResponse } from '../types';

export interface UseHomepageActivityOptions {
  workspaceId: string;
  enabled?: boolean;
}

export function useHomepageActivity({ workspaceId, enabled = true }: UseHomepageActivityOptions) {
  const queryClient = useQueryClient();

  const query = useInfiniteQuery({
    queryKey: [...queryKeys.homepage.activity(workspaceId), 'infinite'],
    queryFn: ({ pageParam }: { pageParam: string | undefined }) =>
      homepageApi.getActivity(workspaceId, pageParam),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (lastPage: HomepageActivityResponse) => {
      if (lastPage.meta.has_more && lastPage.meta.cursor) {
        return lastPage.meta.cursor;
      }
      return undefined;
    },
    enabled: enabled && !!workspaceId,
    staleTime: ACTIVITY_STALE_TIME,
    gcTime: 5 * 60 * 1000, // 5 minutes
    refetchOnWindowFocus: true,
  });

  // Subscribe to Supabase Realtime for live updates
  useEffect(() => {
    if (!workspaceId) return;

    const channel = supabase
      .channel(`homepage-activity:${workspaceId}`)
      .on('broadcast', { event: 'note_updated' }, () => {
        queryClient.invalidateQueries({
          queryKey: queryKeys.homepage.activity(workspaceId),
        });
      })
      .on('broadcast', { event: 'issue_updated' }, () => {
        queryClient.invalidateQueries({
          queryKey: queryKeys.homepage.activity(workspaceId),
        });
      })
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, [workspaceId, queryClient]);

  return query;
}

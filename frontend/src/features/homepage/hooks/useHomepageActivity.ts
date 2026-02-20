'use client';

/**
 * useHomepageActivity (H034) — TanStack Query infinite query for activity feed.
 * Uses staleTime + refetchOnWindowFocus for freshness.
 *
 * NOTE: Supabase Realtime broadcast subscriptions were removed because no
 * backend code currently sends note_updated/issue_updated broadcast events.
 * Re-add when server-side broadcast is implemented.
 */

import { useInfiniteQuery } from '@tanstack/react-query';
import { queryKeys } from '@/lib/queryClient';
import { homepageApi } from '../api/homepage-api';
import { ACTIVITY_STALE_TIME } from '../constants';
import type { HomepageActivityResponse } from '../types';

export interface UseHomepageActivityOptions {
  workspaceId: string;
  enabled?: boolean;
}

export function useHomepageActivity({ workspaceId, enabled = true }: UseHomepageActivityOptions) {
  return useInfiniteQuery({
    queryKey: [...queryKeys.homepage.activity(workspaceId), 'infinite'],
    queryFn: ({ pageParam }: { pageParam: string | undefined }) =>
      homepageApi.getActivity(workspaceId, pageParam),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (lastPage: HomepageActivityResponse) => {
      if (lastPage.meta.hasMore && lastPage.meta.cursor) {
        return lastPage.meta.cursor;
      }
      return undefined;
    },
    enabled: enabled && !!workspaceId,
    staleTime: ACTIVITY_STALE_TIME,
    gcTime: 5 * 60 * 1000, // 5 minutes
    refetchOnWindowFocus: true,
  });
}

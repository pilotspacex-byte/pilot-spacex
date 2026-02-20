'use client';

/**
 * useWorkspaceDigest — TanStack Query hook for workspace AI digest.
 *
 * Fetches categorized suggestions from GET /homepage/digest.
 * Exposes dismiss (optimistic) and refresh mutations.
 *
 * References:
 * - US-1: Wire digest API to homepage (T010-T016)
 * - specs/012-homepage-note/spec.md Digest Endpoints
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { queryKeys } from '@/lib/queryClient';
import { homepageApi } from '../api/homepage-api';
import { DIGEST_REFETCH_INTERVAL, DIGEST_STALE_TIME } from '../constants';
import type { DigestCategory, DigestResponse, DigestSuggestion } from '../types';

export interface UseWorkspaceDigestOptions {
  workspaceId: string;
  enabled?: boolean;
}

/** Suggestions grouped by category for rendering */
export interface DigestCategoryGroup {
  category: DigestCategory;
  items: DigestSuggestion[];
}

/**
 * Group suggestions by category, preserving relevance order within each group.
 * Empty categories are excluded from the result (FR-004).
 */
export function groupByCategory(suggestions: DigestSuggestion[]): DigestCategoryGroup[] {
  const map = new Map<DigestCategory, DigestSuggestion[]>();

  for (const s of suggestions) {
    const existing = map.get(s.category);
    if (existing) {
      existing.push(s);
    } else {
      map.set(s.category, [s]);
    }
  }

  const groups: DigestCategoryGroup[] = [];
  for (const [category, items] of map) {
    groups.push({ category, items });
  }
  return groups;
}

export function useWorkspaceDigest({ workspaceId, enabled = true }: UseWorkspaceDigestOptions) {
  const queryClient = useQueryClient();
  const queryKey = queryKeys.homepage.digest(workspaceId);

  const query = useQuery({
    queryKey,
    queryFn: () => homepageApi.getDigest(workspaceId),
    enabled: enabled && !!workspaceId,
    staleTime: DIGEST_STALE_TIME,
    gcTime: 10 * 60 * 1000, // 10 minutes
    refetchInterval: DIGEST_REFETCH_INTERVAL,
    refetchOnWindowFocus: true,
  });

  const dismissMutation = useMutation({
    mutationFn: (suggestion: DigestSuggestion) =>
      homepageApi.dismissSuggestion(workspaceId, {
        suggestionId: suggestion.id,
        entityId: suggestion.entityId,
        entityType: suggestion.entityType,
        category: suggestion.category,
      }),

    // Optimistic update: remove suggestion from cache immediately
    onMutate: async (suggestion: DigestSuggestion) => {
      await queryClient.cancelQueries({ queryKey });

      const previous = queryClient.getQueryData<DigestResponse>(queryKey);

      queryClient.setQueryData<DigestResponse>(queryKey, (old) => {
        if (!old) return old;
        const filtered = old.data.suggestions.filter((s) => s.id !== suggestion.id);
        return {
          ...old,
          data: {
            ...old.data,
            suggestions: filtered,
            suggestionCount: filtered.length,
          },
        };
      });

      return { previous };
    },

    // Rollback on error
    onError: (_error, _suggestion, context) => {
      if (context?.previous) {
        queryClient.setQueryData(queryKey, context.previous);
      }
    },

    onSettled: () => {
      queryClient.invalidateQueries({ queryKey });
    },
  });

  const refreshMutation = useMutation({
    mutationFn: () => homepageApi.refreshDigest(workspaceId),
    onSuccess: () => {
      // Invalidate after a short delay to allow backend generation
      setTimeout(() => {
        queryClient.invalidateQueries({ queryKey });
      }, 5_000);
    },
  });

  return {
    /** Raw digest response */
    data: query.data,
    /** Suggestions grouped by category (empty categories excluded) */
    groups: query.data ? groupByCategory(query.data.data.suggestions) : [],
    /** All suggestions flat */
    suggestions: query.data?.data.suggestions ?? [],
    /** When digest was last generated */
    generatedAt: query.data?.data.generatedAt ?? null,
    /** Total suggestion count */
    suggestionCount: query.data?.data.suggestionCount ?? 0,

    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error,
    refetch: query.refetch,

    /** Dismiss a single suggestion (optimistic) */
    dismiss: dismissMutation.mutate,
    isDismissing: dismissMutation.isPending,

    /** Trigger manual digest regeneration */
    refresh: refreshMutation.mutate,
    isRefreshing: refreshMutation.isPending,
    refreshError: refreshMutation.error,
  };
}

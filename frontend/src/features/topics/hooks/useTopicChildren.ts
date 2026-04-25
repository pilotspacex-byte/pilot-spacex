'use client';

/**
 * useTopicChildren — paginated children of a parent topic, or top-level topics
 * when `parentId === null` (Phase 93 Plan 03 Task 2).
 *
 * Decision K (locked): for v1, root listing fetches the workspace-wide notes
 * via `notesApi.list` (existing endpoint, pageSize=200) and filters client-side
 * to `parentTopicId === null`. If profiling later shows this is wasteful, a
 * `?parent_topic_id=null` filter on the existing list endpoint is the planned
 * follow-up. Documented in 93-03-SUMMARY.md.
 */

import { useQuery } from '@tanstack/react-query';
import { notesApi } from '@/services/api';
import type { Note } from '@/types';
import type { PaginatedResponse } from '@/services/api/client';
import { topicTreeKeys } from '../lib/topic-tree-keys';

const ROOT_LISTING_PAGE_SIZE = 200;

interface UseTopicChildrenOptions {
  enabled?: boolean;
}

export function useTopicChildren(
  workspaceId: string,
  parentId: string | null,
  page: number = 1,
  pageSize: number = 20,
  options?: UseTopicChildrenOptions,
) {
  return useQuery<PaginatedResponse<Note>>({
    queryKey: topicTreeKeys.children(workspaceId, parentId, page),
    queryFn: async () => {
      if (parentId === null) {
        // Root listing — fetch workspace-wide and filter client-side (Decision K v1).
        const all = await notesApi.list(workspaceId, undefined, 1, ROOT_LISTING_PAGE_SIZE);
        const rootItems = all.items.filter((n) => (n.parentTopicId ?? null) === null);
        return {
          ...all,
          items: rootItems,
          total: rootItems.length,
        };
      }
      return notesApi.listChildren(workspaceId, parentId, page, pageSize);
    },
    enabled: (options?.enabled ?? true) && Boolean(workspaceId),
    staleTime: 1000 * 30, // 30s — tree is mutated by user actions; keep fresh-ish.
    gcTime: 1000 * 60 * 5,
  });
}

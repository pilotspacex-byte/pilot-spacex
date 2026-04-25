'use client';

/**
 * useTopicAncestors — root → leaf chain for a given note (includes self).
 * Backend contract: 93-02 SUMMARY — empty list when note missing/soft-deleted.
 */

import { useQuery } from '@tanstack/react-query';
import { notesApi } from '@/services/api';
import type { Note } from '@/types';
import { topicTreeKeys } from '../lib/topic-tree-keys';

interface UseTopicAncestorsOptions {
  enabled?: boolean;
}

export function useTopicAncestors(
  workspaceId: string,
  noteId: string,
  options?: UseTopicAncestorsOptions,
) {
  return useQuery<Note[]>({
    queryKey: topicTreeKeys.ancestors(workspaceId, noteId),
    queryFn: () => notesApi.listAncestors(workspaceId, noteId),
    enabled: (options?.enabled ?? true) && Boolean(workspaceId) && Boolean(noteId),
    staleTime: 1000 * 60, // 1 min — ancestors change less often than children.
    gcTime: 1000 * 60 * 10,
  });
}

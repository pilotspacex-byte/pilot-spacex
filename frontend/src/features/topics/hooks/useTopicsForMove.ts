'use client';

/**
 * useTopicsForMove — flat list of move candidates for the move-to picker
 * (Plan 93-03 Decision K).
 *
 * Filters out the source topic and ALL of its descendants client-side, so the
 * picker UI cannot offer a destination that would create a cycle. The backend
 * is authoritative (TopicCycleError on POST /move) — this filter is UX defense
 * only (T-93-16 in the threat register).
 *
 * v1 implementation reuses the existing `notesApi.list` endpoint (pageSize=200)
 * and computes the descendant set via a single BFS pass over the parentTopicId
 * pointers. T-93-15 accepts the 200-topic ceiling; revisit if a workspace
 * crosses that bar.
 */

import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { notesApi } from '@/services/api';
import type { Note } from '@/types';
import { topicTreeKeys } from '../lib/topic-tree-keys';

const PICKER_PAGE_SIZE = 200;

interface UseTopicsForMoveOptions {
  enabled?: boolean;
}

/**
 * Walk the parentTopicId graph downward from `sourceId`, returning the set of
 * its descendant ids (excluding `sourceId` itself).
 */
function collectDescendantIds(notes: Note[], sourceId: string): Set<string> {
  const childrenByParent = new Map<string, string[]>();
  for (const note of notes) {
    const parent = note.parentTopicId ?? null;
    if (parent === null) continue;
    const list = childrenByParent.get(parent) ?? [];
    list.push(note.id);
    childrenByParent.set(parent, list);
  }

  const descendants = new Set<string>();
  const queue: string[] = [sourceId];
  while (queue.length > 0) {
    const current = queue.shift() as string;
    const directChildren = childrenByParent.get(current) ?? [];
    for (const childId of directChildren) {
      if (descendants.has(childId)) continue; // cycle defense
      descendants.add(childId);
      queue.push(childId);
    }
  }
  return descendants;
}

export function useTopicsForMove(
  workspaceId: string,
  sourceId: string,
  options?: UseTopicsForMoveOptions,
) {
  // Reuse the children('__root__') key prefix's first three segments to avoid a
  // duplicate cache slot — sharing the workspace-wide list lookup with other
  // consumers if they ever cache it under the same key. For v1 we keep a
  // dedicated key so the picker controls its own gcTime/staleTime.
  const query = useQuery<Note[]>({
    queryKey: [...topicTreeKeys.all(workspaceId), 'picker'] as const,
    queryFn: async () => {
      const page = await notesApi.list(workspaceId, undefined, 1, PICKER_PAGE_SIZE);
      return page.items;
    },
    enabled: (options?.enabled ?? true) && Boolean(workspaceId) && Boolean(sourceId),
    staleTime: 1000 * 30,
    gcTime: 1000 * 60 * 5,
  });

  const filtered = useMemo<Note[]>(() => {
    const notes = query.data ?? [];
    if (notes.length === 0) return [];
    const exclude = collectDescendantIds(notes, sourceId);
    exclude.add(sourceId);
    return notes.filter((n) => !exclude.has(n.id));
  }, [query.data, sourceId]);

  return {
    data: filtered,
    isLoading: query.isLoading,
    isSuccess: query.isSuccess,
    isError: query.isError,
    error: query.error,
  };
}

'use client';

/**
 * useNotes - TanStack Query hook for fetching notes list with pagination
 */
import { useMemo } from 'react';
import { useQuery, useInfiniteQuery } from '@tanstack/react-query';
import { notesApi } from '@/services/api';
import type { Note } from '@/types';
import type { PaginatedResponse } from '@/services/api/client';

export const NOTES_QUERY_KEY = 'notes';

export interface UseNotesOptions {
  /** Workspace ID (required) */
  workspaceId: string;
  /** Filter by project ID */
  projectId?: string;
  /** Filter by multiple project IDs (client-side filter, fetches all notes then filters) */
  projectIds?: string[];
  /** Filter by pinned status */
  isPinned?: boolean;
  /** Filter by author ID */
  authorId?: string;
  /** Page size */
  pageSize?: number;
  /** Enable query */
  enabled?: boolean;
}

/**
 * Query key factory for notes
 */
export const notesKeys = {
  all: [NOTES_QUERY_KEY] as const,
  lists: () => [...notesKeys.all, 'list'] as const,
  list: (workspaceId: string, filters?: { projectId?: string; isPinned?: boolean }) =>
    [...notesKeys.lists(), workspaceId, filters] as const,
  details: () => [...notesKeys.all, 'detail'] as const,
  detail: (workspaceId: string, noteId: string) =>
    [...notesKeys.details(), workspaceId, noteId] as const,
  annotations: (workspaceId: string, noteId: string) =>
    [...notesKeys.detail(workspaceId, noteId), 'annotations'] as const,
  versions: (workspaceId: string, noteId: string) =>
    [...notesKeys.detail(workspaceId, noteId), 'versions'] as const,
};

/**
 * Hook for fetching paginated notes list
 */
export function useNotes({
  workspaceId,
  projectId,
  isPinned,
  authorId,
  pageSize = 50,
  enabled = true,
}: UseNotesOptions) {
  return useQuery({
    queryKey: notesKeys.list(workspaceId, { projectId, isPinned }),
    queryFn: () => notesApi.list(workspaceId, { projectId, isPinned, authorId }, 1, pageSize),
    enabled: enabled && !!workspaceId,
    staleTime: 1000 * 60 * 5, // 5 minutes
    gcTime: 1000 * 60 * 30, // 30 minutes
  });
}

/**
 * Hook for infinite scroll notes list
 */
export function useInfiniteNotes({
  workspaceId,
  projectId,
  projectIds,
  isPinned,
  authorId,
  pageSize = 20,
  enabled = true,
}: UseNotesOptions) {
  // Stabilize the projectIds key: sort and join so array identity doesn't cause spurious refetches
  const projectIdsKey = projectIds && projectIds.length > 0
    ? [...projectIds].sort().join(',')
    : undefined;

  const query = useInfiniteQuery({
    queryKey: [...notesKeys.list(workspaceId, { projectId, isPinned }), 'infinite', projectIdsKey],
    queryFn: ({ pageParam }) =>
      notesApi.list(workspaceId, { projectId, isPinned, authorId }, pageParam, pageSize),
    initialPageParam: 1,
    getNextPageParam: (lastPage, _pages, lastPageParam) =>
      lastPage.hasNext ? lastPageParam + 1 : undefined,
    enabled: enabled && !!workspaceId,
    staleTime: 1000 * 60 * 5,
    gcTime: 1000 * 60 * 30,
  });

  // Client-side multi-project filter when projectIds is provided.
  // Memoized so the Set and filtered pages are only recomputed when query data or projectIds change.
  const filteredData = useMemo(() => {
    if (!projectIdsKey || !query.data) return query.data;
    const projectIdSet = new Set(projectIds);
    return {
      ...query.data,
      pages: query.data.pages.map((page) => ({
        ...page,
        items: page.items.filter((note) => note.projectId && projectIdSet.has(note.projectId)),
      })),
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [query.data, projectIdsKey]);

  if (projectIdsKey) {
    return { ...query, data: filteredData };
  }

  return query;
}

/**
 * Select all notes from query data
 */
export function selectAllNotes(data: PaginatedResponse<Note> | undefined): Note[] {
  return data?.items ?? [];
}

/**
 * Select total count from query data
 */
export function selectTotalCount(data: PaginatedResponse<Note> | undefined): number {
  return data?.total ?? 0;
}

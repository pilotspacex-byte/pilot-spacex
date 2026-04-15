'use client';

/**
 * useNotes - TanStack Query hook for fetching notes list with pagination
 */
import { useQuery, useInfiniteQuery } from '@tanstack/react-query';
import { notesApi } from '@/services/api';
import type { Note } from '@/types';
import type { PaginatedResponse } from '@/services/api/client';

export const NOTES_QUERY_KEY = 'notes';

export interface UseNotesOptions {
  /** Workspace ID (required) */
  workspaceId: string;
  /** Filter by one or more project IDs — sent to the server as repeated project_id params */
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
  list: (workspaceId: string, filters?: { projectIds?: string[]; isPinned?: boolean }) =>
    [...notesKeys.lists(), workspaceId, filters] as const,
  details: () => [...notesKeys.all, 'detail'] as const,
  detail: (workspaceId: string, noteId: string) =>
    [...notesKeys.details(), workspaceId, noteId] as const,
  annotations: (workspaceId: string, noteId: string) =>
    [...notesKeys.detail(workspaceId, noteId), 'annotations'] as const,
  linkedIssues: (workspaceId: string, noteId: string) =>
    [...notesKeys.detail(workspaceId, noteId), 'linked-issues'] as const,
  specAnnotations: (workspaceId: string, noteId: string) =>
    [...notesKeys.detail(workspaceId, noteId), 'spec-annotations'] as const,
  versions: (workspaceId: string, noteId: string) =>
    [...notesKeys.detail(workspaceId, noteId), 'versions'] as const,
};

/**
 * Hook for fetching paginated notes list
 */
export function useNotes({
  workspaceId,
  projectIds,
  isPinned,
  authorId,
  pageSize = 50,
  enabled = true,
}: UseNotesOptions) {
  // Stable key: sort so array order doesn't cause spurious refetches
  const projectIdsKey =
    projectIds && projectIds.length > 0 ? [...projectIds].sort() : undefined;

  return useQuery({
    queryKey: notesKeys.list(workspaceId, { projectIds: projectIdsKey, isPinned }),
    queryFn: () => notesApi.list(workspaceId, { projectIds, isPinned, authorId }, 1, pageSize),
    enabled: enabled && !!workspaceId,
    staleTime: 1000 * 60 * 5, // 5 minutes
    gcTime: 1000 * 60 * 30, // 30 minutes
  });
}

/**
 * Hook for infinite scroll notes list.
 *
 * When `projectIds` is provided, the IDs are sent to the server as repeated
 * `project_id` query params so the server filters pages before returning them.
 * The sorted, joined key is included in the TanStack Query key so pagination
 * resets automatically whenever the project selection changes.
 */
export function useInfiniteNotes({
  workspaceId,
  projectIds,
  isPinned,
  authorId,
  pageSize = 20,
  enabled = true,
}: UseNotesOptions) {
  // Stable string key: sort so array order doesn't cause spurious refetches.
  const projectIdsKey =
    projectIds && projectIds.length > 0 ? [...projectIds].sort().join(',') : undefined;

  return useInfiniteQuery({
    queryKey: [...notesKeys.list(workspaceId, { isPinned }), 'infinite', projectIdsKey],
    queryFn: ({ pageParam }) =>
      notesApi.list(workspaceId, { projectIds, isPinned, authorId }, pageParam, pageSize),
    initialPageParam: 1,
    getNextPageParam: (lastPage, _pages, lastPageParam) =>
      lastPage.hasNext ? lastPageParam + 1 : undefined,
    enabled: enabled && !!workspaceId,
    staleTime: 1000 * 60 * 5,
    gcTime: 1000 * 60 * 30,
  });
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

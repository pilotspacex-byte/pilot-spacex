import { useQuery } from '@tanstack/react-query';
import { notesApi } from '@/services/api';
import type { Note } from '@/types';

export const personalPagesKeys = {
  all: ['notes', 'personal-pages'] as const,
  list: (workspaceId: string) => [...personalPagesKeys.all, workspaceId] as const,
};

/**
 * TanStack Query hook for personal pages (notes without a project).
 *
 * Personal pages are owned by the current user and not associated with any
 * project. They are filtered client-side from the full notes list since the
 * backend does not expose a dedicated project_id=null filter endpoint.
 *
 * Scale note: Appropriate for 5-100 member workspaces (<100 personal pages).
 *
 * @param workspaceId Workspace slug or ID
 * @param enabled Whether to enable the query (default true)
 */
export function usePersonalPages(workspaceId: string, enabled = true) {
  return useQuery({
    queryKey: personalPagesKeys.list(workspaceId),
    queryFn: () => notesApi.list(workspaceId, {}, 1, 100),
    enabled: enabled && !!workspaceId,
    staleTime: 1000 * 60 * 2, // 2 minutes
    select: (data) => data.items.filter((n: Note) => !n.projectId),
  });
}

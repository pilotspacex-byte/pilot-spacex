import { useQuery } from '@tanstack/react-query';
import { notesApi } from '@/services/api';
import { buildTree } from '@/lib/tree-utils';
import type { Note } from '@/types';

export const projectTreeKeys = {
  all: ['notes', 'project-tree'] as const,
  tree: (workspaceId: string, projectId: string) =>
    [...projectTreeKeys.all, workspaceId, projectId] as const,
};

/**
 * TanStack Query hook for project page tree.
 *
 * Fetches ALL notes for a project (via pagination loop) and transforms them
 * into a nested tree structure using buildTree. Projects with more than 100
 * pages are fully loaded rather than capped at the first page.
 *
 * @param workspaceId Workspace slug or ID
 * @param projectId Project ID
 * @param enabled Whether to enable the query (default true)
 */
export function useProjectPageTree(workspaceId: string, projectId: string, enabled = true) {
  return useQuery({
    queryKey: projectTreeKeys.tree(workspaceId, projectId),
    queryFn: async () => {
      const PAGE_SIZE = 100;
      let page = 1;
      let allItems: Note[] = [];
      let hasNext = true;

      while (hasNext) {
        const result = await notesApi.list(workspaceId, { projectId }, page, PAGE_SIZE);
        allItems = [...allItems, ...result.items];
        hasNext = result.hasNext;
        page++;
      }

      return {
        items: allItems,
        total: allItems.length,
        hasNext: false,
        hasPrev: false,
        pageSize: allItems.length,
        nextCursor: null,
        prevCursor: null,
      };
    },
    enabled: enabled && !!workspaceId && !!projectId,
    staleTime: 1000 * 60 * 2, // 2 minutes
    select: (data) => buildTree(data.items),
  });
}

'use client';

/**
 * useReorderPage - Mutation hook for reordering a page among its siblings.
 *
 * Calls POST /workspaces/{wid}/notes/{nid}/reorder and invalidates the
 * project tree cache on success so the sidebar reflects the new order.
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { notesApi } from '@/services/api';
import { projectTreeKeys } from './useProjectPageTree';

interface ReorderPageVariables {
  noteId: string;
  insertAfterId: string | null;
}

/**
 * @param workspaceId - The workspace ID (slug or UUID)
 * @param projectId   - The project ID for cache invalidation
 */
export function useReorderPage(workspaceId: string, projectId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ noteId, insertAfterId }: ReorderPageVariables) =>
      notesApi.reorderPage(workspaceId, noteId, insertAfterId),

    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: projectTreeKeys.tree(workspaceId, projectId),
      });
    },

    onError: () => {
      toast.error('Failed to reorder page');
    },
  });
}

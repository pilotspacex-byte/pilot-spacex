'use client';

/**
 * useMovePage - Mutation hook for moving a page to a new parent.
 *
 * Calls POST /workspaces/{wid}/notes/{nid}/move and invalidates the
 * project tree cache on success so the sidebar reflects the new hierarchy.
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { notesApi } from '@/services/api';
import { projectTreeKeys } from './useProjectPageTree';

interface MovePageVariables {
  noteId: string;
  newParentId: string | null;
}

/**
 * @param workspaceId - The workspace ID (slug or UUID)
 * @param projectId   - The project ID for cache invalidation
 */
export function useMovePage(workspaceId: string, projectId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ noteId, newParentId }: MovePageVariables) =>
      notesApi.movePage(workspaceId, noteId, newParentId),

    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: projectTreeKeys.tree(workspaceId, projectId),
      });
    },

    onError: () => {
      toast.error('Failed to move page');
    },
  });
}

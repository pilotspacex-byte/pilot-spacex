'use client';

/**
 * useDeleteNote - Mutation hook for deleting notes
 */
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { notesApi } from '@/services/api';
import type { Note } from '@/types';
import { notesKeys } from './useNotes';
import type { PaginatedResponse } from '@/services/api/client';

export interface UseDeleteNoteOptions {
  /** Workspace ID (required) */
  workspaceId: string;
  /** Callback on success */
  onSuccess?: () => void;
  /** Callback on error */
  onError?: (error: Error) => void;
}

/**
 * Hook for deleting a note
 */
export function useDeleteNote({ workspaceId, onSuccess, onError }: UseDeleteNoteOptions) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (noteId: string) => notesApi.delete(workspaceId, noteId),

    onMutate: async (noteId) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({
        queryKey: notesKeys.lists(),
      });

      // Get previous list data for rollback
      const previousLists = queryClient.getQueriesData<PaginatedResponse<Note>>({
        queryKey: notesKeys.lists(),
      });

      // Get the note being deleted for toast
      const noteToDelete = queryClient.getQueryData<Note>(notesKeys.detail(workspaceId, noteId));

      // Optimistically remove from lists
      queryClient.setQueriesData<PaginatedResponse<Note>>(
        { queryKey: notesKeys.lists() },
        (old) => {
          if (!old) return old;
          return {
            ...old,
            items: old.items.filter((note) => note.id !== noteId),
            total: old.total - 1,
          };
        }
      );

      // Remove detail from cache
      queryClient.removeQueries({
        queryKey: notesKeys.detail(workspaceId, noteId),
      });

      return { previousLists, noteToDelete };
    },

    onSuccess: (_data, _noteId, context) => {
      const title = context?.noteToDelete?.title ?? 'Topic';
      toast.success('Topic deleted', {
        description: `"${title}" has been deleted.`,
      });
      onSuccess?.();
    },

    onError: (error: Error, _noteId, context) => {
      // Rollback on error
      if (context?.previousLists) {
        context.previousLists.forEach(([queryKey, data]) => {
          queryClient.setQueryData(queryKey, data);
        });
      }

      toast.error('Failed to delete topic', {
        description: error.message,
      });

      onError?.(error);
    },

    onSettled: () => {
      // Refetch lists after mutation
      queryClient.invalidateQueries({
        queryKey: notesKeys.lists(),
      });
    },
  });
}

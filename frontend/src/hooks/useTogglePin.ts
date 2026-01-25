'use client';

/**
 * useTogglePin - Mutation hook for toggling note pin status
 */
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { notesApi } from '@/services/api';
import type { Note } from '@/types';
import { notesKeys } from '@/features/notes/hooks/useNotes';
import type { PaginatedResponse } from '@/services/api/client';

export interface UseTogglePinOptions {
  /** Workspace ID (required) */
  workspaceId: string;
  /** Callback on success */
  onSuccess?: (note: Note, isPinned: boolean) => void;
  /** Callback on error */
  onError?: (error: Error) => void;
}

/**
 * Hook for toggling note pin status
 */
export function useTogglePin({ workspaceId, onSuccess, onError }: UseTogglePinOptions) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ noteId, isPinned }: { noteId: string; isPinned: boolean }) => {
      if (isPinned) {
        return notesApi.unpin(workspaceId, noteId);
      } else {
        return notesApi.pin(workspaceId, noteId);
      }
    },

    onMutate: async ({ noteId, isPinned }) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({
        queryKey: notesKeys.detail(workspaceId, noteId),
      });
      await queryClient.cancelQueries({
        queryKey: notesKeys.lists(),
      });

      // Get previous values
      const previousNote = queryClient.getQueryData<Note>(notesKeys.detail(workspaceId, noteId));
      const previousLists = queryClient.getQueriesData<PaginatedResponse<Note>>({
        queryKey: notesKeys.lists(),
      });

      // Optimistically update the note
      if (previousNote) {
        queryClient.setQueryData<Note>(notesKeys.detail(workspaceId, noteId), {
          ...previousNote,
          isPinned: !isPinned,
        });
      }

      // Optimistically update lists
      queryClient.setQueriesData<PaginatedResponse<Note>>(
        { queryKey: notesKeys.lists() },
        (old) => {
          if (!old) return old;
          return {
            ...old,
            items: old.items.map((note) =>
              note.id === noteId ? { ...note, isPinned: !isPinned } : note
            ),
          };
        }
      );

      return { previousNote, previousLists, isPinned };
    },

    onSuccess: (note, { isPinned }) => {
      // Update cache with server response
      queryClient.setQueryData(notesKeys.detail(workspaceId, note.id), note);

      toast.success(isPinned ? 'Note unpinned' : 'Note pinned', {
        description: `"${note.title || 'Untitled'}" has been ${isPinned ? 'unpinned' : 'pinned'}.`,
      });

      onSuccess?.(note, !isPinned);
    },

    onError: (error: Error, { noteId, isPinned }, context) => {
      // Rollback on error
      if (context?.previousNote) {
        queryClient.setQueryData(notesKeys.detail(workspaceId, noteId), context.previousNote);
      }
      if (context?.previousLists) {
        context.previousLists.forEach(([queryKey, data]) => {
          queryClient.setQueryData(queryKey, data);
        });
      }

      toast.error(`Failed to ${isPinned ? 'unpin' : 'pin'} note`, {
        description: error.message,
      });

      onError?.(error);
    },

    onSettled: () => {
      // Invalidate to ensure consistency
      queryClient.invalidateQueries({
        queryKey: notesKeys.lists(),
      });
    },
  });
}

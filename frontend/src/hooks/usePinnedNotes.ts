'use client';

/**
 * usePinnedNotes - Query hook for fetching pinned notes
 */
import { useQuery, useQueryClient, useMutation } from '@tanstack/react-query';
import { notesApi } from '@/services/api';
import type { Note } from '@/types';
import { notesKeys } from '@/features/notes/hooks/useNotes';

export interface UsePinnedNotesOptions {
  /** Workspace ID (required) */
  workspaceId: string;
  /** Enable query */
  enabled?: boolean;
}

/**
 * Hook for fetching pinned notes
 */
export function usePinnedNotes({ workspaceId, enabled = true }: UsePinnedNotesOptions) {
  return useQuery({
    queryKey: notesKeys.list(workspaceId, { isPinned: true }),
    queryFn: async () => {
      const response = await notesApi.list(workspaceId, { isPinned: true }, 1, 50);
      return response.items;
    },
    enabled: enabled && !!workspaceId,
    staleTime: 1000 * 60 * 5,
    gcTime: 1000 * 60 * 30,
  });
}

/**
 * Hook for reordering pinned notes
 * Note: Requires backend support for pin_order field
 */
export function useReorderPinnedNotes({ workspaceId }: { workspaceId: string }) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (noteIds: string[]) => {
      // This would call a backend endpoint to update pin order
      // For now, we just update the local cache
      // await notesApi.updatePinOrder(workspaceId, noteIds);
      return noteIds;
    },

    onMutate: async (noteIds) => {
      await queryClient.cancelQueries({
        queryKey: notesKeys.list(workspaceId, { isPinned: true }),
      });

      const previousNotes = queryClient.getQueryData<Note[]>(
        notesKeys.list(workspaceId, { isPinned: true })
      );

      // Reorder notes based on new order
      if (previousNotes) {
        const reorderedNotes = noteIds
          .map((id) => previousNotes.find((n) => n.id === id))
          .filter((n): n is Note => n !== undefined);

        queryClient.setQueryData(notesKeys.list(workspaceId, { isPinned: true }), reorderedNotes);
      }

      return { previousNotes };
    },

    onError: (_error, _variables, context) => {
      if (context?.previousNotes) {
        queryClient.setQueryData(
          notesKeys.list(workspaceId, { isPinned: true }),
          context.previousNotes
        );
      }
    },

    onSettled: () => {
      queryClient.invalidateQueries({
        queryKey: notesKeys.list(workspaceId, { isPinned: true }),
      });
    },
  });
}

/**
 * Select pinned note IDs in order
 */
export function selectPinnedNoteIds(notes: Note[] | undefined): string[] {
  return notes?.map((note) => note.id) ?? [];
}

'use client';

/**
 * useUpdateNote - Mutation hook with optimistic updates for notes
 */
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { notesApi } from '@/services/api';
import type { Note, JSONContent } from '@/types';
import { notesKeys } from './useNotes';

export interface UseUpdateNoteOptions {
  /** Workspace ID (required) */
  workspaceId: string;
  /** Note ID (required) */
  noteId: string;
  /** Show toast on success */
  showToast?: boolean;
  /** Callback on success */
  onSuccess?: (note: Note) => void;
  /** Callback on error */
  onError?: (error: Error, previousNote: Note | undefined) => void;
}

export interface UpdateNoteData {
  title?: string;
  content?: JSONContent;
  projectId?: string;
  iconEmoji?: string | null;
}

/**
 * Hook for updating a note with optimistic updates
 */
export function useUpdateNote({
  workspaceId,
  noteId,
  showToast = false,
  onSuccess,
  onError,
}: UseUpdateNoteOptions) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: UpdateNoteData) => notesApi.update(workspaceId, noteId, data),

    // Optimistic update
    onMutate: async (newData) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({
        queryKey: notesKeys.detail(workspaceId, noteId),
      });

      // Get previous value
      const previousNote = queryClient.getQueryData<Note>(notesKeys.detail(workspaceId, noteId));

      // Optimistically update cache
      if (previousNote) {
        queryClient.setQueryData<Note>(notesKeys.detail(workspaceId, noteId), {
          ...previousNote,
          ...newData,
          updatedAt: new Date().toISOString(),
        });
      }

      return { previousNote };
    },

    onSuccess: (note) => {
      // Update cache with server response
      queryClient.setQueryData(notesKeys.detail(workspaceId, noteId), note);

      // Invalidate list to ensure consistency
      queryClient.invalidateQueries({
        queryKey: notesKeys.lists(),
        refetchType: 'none', // Don't refetch immediately
      });

      if (showToast) {
        toast.success('Topic saved');
      }

      onSuccess?.(note);
    },

    onError: (error: Error, _variables, context) => {
      // Rollback on error
      if (context?.previousNote) {
        queryClient.setQueryData(notesKeys.detail(workspaceId, noteId), context.previousNote);
      }

      toast.error('Failed to save note', {
        description: error.message,
      });

      onError?.(error, context?.previousNote);
    },
  });
}

/**
 * Hook for updating note content only
 */
export function useUpdateNoteContent({
  workspaceId,
  noteId,
  onSuccess,
  onError,
}: Omit<UseUpdateNoteOptions, 'showToast'>) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (content: JSONContent) => notesApi.updateContent(workspaceId, noteId, content),

    onMutate: async (newContent) => {
      await queryClient.cancelQueries({
        queryKey: notesKeys.detail(workspaceId, noteId),
      });

      const previousNote = queryClient.getQueryData<Note>(notesKeys.detail(workspaceId, noteId));

      if (previousNote) {
        queryClient.setQueryData<Note>(notesKeys.detail(workspaceId, noteId), {
          ...previousNote,
          content: newContent,
          updatedAt: new Date().toISOString(),
        });
      }

      return { previousNote };
    },

    onSuccess: (note) => {
      queryClient.setQueryData(notesKeys.detail(workspaceId, noteId), note);
      onSuccess?.(note);
    },

    onError: (error: Error, _variables, context) => {
      if (context?.previousNote) {
        queryClient.setQueryData(notesKeys.detail(workspaceId, noteId), context.previousNote);
      }
      onError?.(error, context?.previousNote);
    },
  });
}

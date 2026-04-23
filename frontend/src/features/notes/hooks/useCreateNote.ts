'use client';

/**
 * useCreateNote - Mutation hook for creating notes
 */
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { notesApi } from '@/services/api';
import type { CreateNoteData, Note } from '@/types';
import { notesKeys } from './useNotes';

export interface UseCreateNoteOptions {
  /** Workspace ID (required) */
  workspaceId: string;
  /** Callback on success */
  onSuccess?: (note: Note) => void;
  /** Callback on error */
  onError?: (error: Error) => void;
}

/**
 * Hook for creating a new note
 */
export function useCreateNote({ workspaceId, onSuccess, onError }: UseCreateNoteOptions) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: Omit<CreateNoteData, 'workspaceId'>) =>
      notesApi.create(workspaceId, { ...data, workspaceId }),

    onSuccess: (note) => {
      // Invalidate notes list
      queryClient.invalidateQueries({
        queryKey: notesKeys.lists(),
      });

      // Add note to cache
      queryClient.setQueryData(notesKeys.detail(workspaceId, note.id), note);

      toast.success('Topic created', {
        description: `"${note.title || 'Untitled'}" has been created.`,
      });

      onSuccess?.(note);
    },

    onError: (error: Error) => {
      toast.error('Failed to create topic', {
        description: error.message,
      });
      onError?.(error);
    },
  });
}

/**
 * Helper to create note with defaults
 */
export function createNoteDefaults(title?: string): Omit<CreateNoteData, 'workspaceId'> {
  return {
    title: title ?? 'Untitled',
    content: {
      type: 'doc',
      content: [{ type: 'paragraph' }],
    },
  };
}

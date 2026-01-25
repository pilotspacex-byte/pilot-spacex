'use client';

/**
 * useNote - TanStack Query hook for fetching a single note
 */
import { useQuery } from '@tanstack/react-query';
import { notesApi } from '@/services/api';
import type { Note, NoteAnnotation } from '@/types';
import { notesKeys } from './useNotes';

export interface UseNoteOptions {
  /** Workspace ID (required) */
  workspaceId: string;
  /** Note ID (required) */
  noteId: string;
  /** Enable query */
  enabled?: boolean;
}

/**
 * Hook for fetching a single note by ID
 */
export function useNote({ workspaceId, noteId, enabled = true }: UseNoteOptions) {
  return useQuery({
    queryKey: notesKeys.detail(workspaceId, noteId),
    queryFn: () => notesApi.get(workspaceId, noteId),
    enabled: enabled && !!workspaceId && !!noteId,
    staleTime: 1000 * 60 * 5, // 5 minutes
    gcTime: 1000 * 60 * 30, // 30 minutes
    retry: (failureCount, error) => {
      // Don't retry on 404
      if ((error as { status?: number })?.status === 404) {
        return false;
      }
      return failureCount < 3;
    },
  });
}

/**
 * Hook for fetching note annotations
 */
export function useNoteAnnotations({ workspaceId, noteId, enabled = true }: UseNoteOptions) {
  return useQuery({
    queryKey: notesKeys.annotations(workspaceId, noteId),
    queryFn: () => notesApi.getAnnotations(workspaceId, noteId),
    enabled: enabled && !!workspaceId && !!noteId,
    staleTime: 1000 * 60 * 2, // 2 minutes (annotations change more frequently)
    gcTime: 1000 * 60 * 15,
  });
}

/**
 * Select note title from query data
 */
export function selectNoteTitle(data: Note | undefined): string {
  return data?.title ?? 'Untitled';
}

/**
 * Select word count from query data
 */
export function selectWordCount(data: Note | undefined): number {
  return data?.wordCount ?? 0;
}

/**
 * Select unresolved annotations count
 */
export function selectUnresolvedAnnotationsCount(
  annotations: NoteAnnotation[] | undefined
): number {
  return annotations?.filter((a) => a.status === 'pending').length ?? 0;
}

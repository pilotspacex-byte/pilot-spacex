'use client';

/**
 * useNoteAnnotations (spec annotations) - TanStack Query hook with 30s polling
 * Phase 78: Living Specs sidebar — deviation + decision annotation feed
 */
import { useQuery } from '@tanstack/react-query';
import { notesApi } from '@/services/api';
import type { SpecAnnotationResponse } from '@/services/api/notes';
import { notesKeys } from './useNotes';

export type { SpecAnnotationResponse };

export interface UseNoteAnnotationsOptions {
  workspaceId: string;
  noteId: string;
  enabled?: boolean;
}

/**
 * Fetches spec annotations (deviations + decisions) for a note.
 * Polls every 30 seconds per UI-SPEC — new annotations arrive silently via background jobs.
 *
 * NOTE: This hook is separate from the existing useNoteAnnotations in useNote.ts which
 * fetches margin annotations. This hook fetches spec-level annotations (Phase 78).
 */
export function useSpecAnnotations({
  workspaceId,
  noteId,
  enabled = true,
}: UseNoteAnnotationsOptions) {
  return useQuery<SpecAnnotationResponse[]>({
    queryKey: notesKeys.specAnnotations(workspaceId, noteId),
    queryFn: () => notesApi.getSpecAnnotations(workspaceId, noteId),
    enabled: enabled && !!workspaceId && !!noteId,
    refetchInterval: 30_000,
    staleTime: 1000 * 20,
    gcTime: 1000 * 60 * 10,
  });
}

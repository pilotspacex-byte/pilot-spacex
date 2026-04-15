'use client';

/**
 * useLivingSpec - TanStack Query hook for linked issues with 30s polling
 * Phase 78: Living Specs sidebar
 */
import { useQuery } from '@tanstack/react-query';
import { notesApi } from '@/services/api';
import type { LinkedIssueResponse } from '@/services/api/notes';
import { notesKeys } from './useNotes';

export type { LinkedIssueResponse };

export interface UseLivingSpecOptions {
  workspaceId: string;
  noteId: string;
  enabled?: boolean;
}

/**
 * Fetches issues linked to a note via source_note_id.
 * Polls every 30 seconds per UI-SPEC to reflect live batch run statuses.
 */
export function useLivingSpec({ workspaceId, noteId, enabled = true }: UseLivingSpecOptions) {
  return useQuery<LinkedIssueResponse[]>({
    queryKey: notesKeys.linkedIssues(workspaceId, noteId),
    queryFn: () => notesApi.getLinkedIssues(workspaceId, noteId),
    enabled: enabled && !!workspaceId && !!noteId,
    refetchInterval: 30_000,
    staleTime: 1000 * 20, // 20s — always refetch after 30s polling window
    gcTime: 1000 * 60 * 10,
  });
}

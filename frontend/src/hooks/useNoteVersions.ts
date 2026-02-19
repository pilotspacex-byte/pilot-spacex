'use client';

/**
 * useNoteVersions - Query hook for fetching note version history
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { apiClient } from '@/services/api/client';
import { notesKeys } from '@/features/notes/hooks/useNotes';
import type { Note, NoteContent } from '@/types';

export interface NoteVersion {
  id: string;
  noteId: string;
  versionNumber: number;
  content: NoteContent;
  wordCount: number;
  createdAt: string;
  createdBy: string | null;
  changeDescription?: string;
}

export interface UseNoteVersionsOptions {
  /** Workspace ID (required) */
  workspaceId: string;
  /** Note ID (required) */
  noteId: string;
  /** Enable query */
  enabled?: boolean;
}

/**
 * Fetch note versions from API
 */
interface NoteVersionListResponse {
  versions: NoteVersion[];
  total: number;
  noteId: string;
}

async function fetchNoteVersions(workspaceId: string, noteId: string): Promise<NoteVersion[]> {
  const response = await apiClient.get<NoteVersionListResponse>(
    `/workspaces/${workspaceId}/notes/${noteId}/versions`
  );
  return response.versions;
}

/**
 * Restore a note to a specific version
 */
async function restoreNoteVersion(
  workspaceId: string,
  noteId: string,
  versionId: string
): Promise<Note> {
  return apiClient.post<Note>(
    `/workspaces/${workspaceId}/notes/${noteId}/versions/${versionId}/restore`
  );
}

/**
 * Hook for fetching note version history
 */
export function useNoteVersions({ workspaceId, noteId, enabled = true }: UseNoteVersionsOptions) {
  return useQuery({
    queryKey: notesKeys.versions(workspaceId, noteId),
    queryFn: () => fetchNoteVersions(workspaceId, noteId),
    enabled: enabled && !!workspaceId && !!noteId,
    staleTime: 1000 * 60 * 5,
    gcTime: 1000 * 60 * 30,
  });
}

/**
 * Hook for restoring a note version
 */
export function useRestoreNoteVersion({
  workspaceId,
  noteId,
  onSuccess,
  onError,
}: UseNoteVersionsOptions & {
  onSuccess?: (note: Note) => void;
  onError?: (error: Error) => void;
}) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (versionId: string) => restoreNoteVersion(workspaceId, noteId, versionId),

    onSuccess: (note) => {
      // Update note cache
      queryClient.setQueryData(notesKeys.detail(workspaceId, noteId), note);

      // Invalidate versions to include the new version
      queryClient.invalidateQueries({
        queryKey: notesKeys.versions(workspaceId, noteId),
      });

      // Invalidate lists
      queryClient.invalidateQueries({
        queryKey: notesKeys.lists(),
      });

      toast.success('Version restored', {
        description: 'The note has been restored to the selected version.',
      });

      onSuccess?.(note);
    },

    onError: (error: Error) => {
      toast.error('Failed to restore version', {
        description: error.message,
      });
      onError?.(error);
    },
  });
}

/**
 * Select version by ID
 */
export function selectVersionById(
  versions: NoteVersion[] | undefined,
  versionId: string
): NoteVersion | undefined {
  return versions?.find((v) => v.id === versionId);
}

/**
 * Select current (latest) version
 */
export function selectCurrentVersion(versions: NoteVersion[] | undefined): NoteVersion | undefined {
  if (!versions || versions.length === 0) return undefined;
  return versions.reduce((latest, version) =>
    version.versionNumber > latest.versionNumber ? version : latest
  );
}

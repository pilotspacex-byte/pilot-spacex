'use client';

/**
 * useDeleteArtifact — Optimistic delete mutation hook for project artifacts.
 *
 * onMutate: Removes artifact from cache immediately
 * onError: Restores previous cache and shows error toast
 * onSettled: Invalidates list query to sync with server
 *
 * Toast message: 'Delete failed. Please try again.' (exact — do not change)
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { artifactsApi } from '@/services/api/artifacts';
import type { Artifact } from '@/types/artifact';
import { artifactsKeys } from './use-project-artifacts';

export function useDeleteArtifact(workspaceId: string, projectId: string) {
  const queryClient = useQueryClient();
  const listKey = artifactsKeys.list(workspaceId, projectId);

  return useMutation({
    mutationFn: (artifactId: string) => artifactsApi.delete(workspaceId, projectId, artifactId),

    onMutate: async (artifactId: string) => {
      // Cancel in-flight refetches to prevent overwriting optimistic update
      await queryClient.cancelQueries({ queryKey: listKey });

      // Snapshot previous value for rollback
      const previousArtifacts = queryClient.getQueryData<Artifact[]>(listKey);

      // Optimistically remove the artifact
      queryClient.setQueryData<Artifact[]>(listKey, (old) =>
        old ? old.filter((a) => a.id !== artifactId) : []
      );

      return { previousArtifacts };
    },

    onError: (_err, _artifactId, context) => {
      // Restore previous cache on failure
      if (context?.previousArtifacts !== undefined) {
        queryClient.setQueryData<Artifact[]>(listKey, context.previousArtifacts);
      }
      toast.error('Delete failed. Please try again.');
    },

    onSettled: () => {
      // Always refetch after mutation to stay in sync with server
      void queryClient.invalidateQueries({ queryKey: listKey });
    },
  });
}

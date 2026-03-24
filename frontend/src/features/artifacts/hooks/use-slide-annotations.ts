'use client';

/**
 * use-slide-annotations — TanStack Query hooks for PPTX slide annotation CRUD.
 *
 * All mutations use optimistic updates following the useDeleteArtifact pattern:
 *   onMutate: cancelQueries → snapshot → optimistic setQueryData → return context
 *   onError: restore snapshot, show toast
 *   onSettled: invalidateQueries
 *
 * Query key: ['artifact-annotations', artifactId, slideIndex]
 * staleTime: 30 seconds (annotations update more often than artifact lists)
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { annotationApi, type ArtifactAnnotation } from '@/services/api/artifact-annotations';

// ---------------------------------------------------------------------------
// Query key factory
// ---------------------------------------------------------------------------

export const ANNOTATION_QUERY_KEY = 'artifact-annotations';

export const annotationKeys = {
  all: [ANNOTATION_QUERY_KEY] as const,
  workspace: (workspaceId: string, projectId: string) =>
    [...annotationKeys.all, workspaceId, projectId] as const,
  artifact: (workspaceId: string, projectId: string, artifactId: string) =>
    [...annotationKeys.workspace(workspaceId, projectId), artifactId] as const,
  slide: (workspaceId: string, projectId: string, artifactId: string, slideIndex: number) =>
    [...annotationKeys.artifact(workspaceId, projectId, artifactId), slideIndex] as const,
};

// ---------------------------------------------------------------------------
// useSlideAnnotations — read
// ---------------------------------------------------------------------------

/**
 * Fetch all annotations for a specific slide within a PPTX artifact.
 * Enabled only when all four params are truthy.
 */
export function useSlideAnnotations(
  workspaceId: string,
  projectId: string,
  artifactId: string,
  slideIndex: number
) {
  return useQuery<ArtifactAnnotation[]>({
    queryKey: annotationKeys.slide(workspaceId, projectId, artifactId, slideIndex),
    queryFn: () => annotationApi.list(workspaceId, projectId, artifactId, slideIndex),
    enabled: !!workspaceId && !!projectId && !!artifactId,
    staleTime: 30 * 1000, // 30 seconds
  });
}

// ---------------------------------------------------------------------------
// useCreateAnnotation — optimistic add
// ---------------------------------------------------------------------------

interface CreateAnnotationInput {
  slideIndex: number;
  content: string;
}

/**
 * Create a new annotation on a slide.
 * Optimistically appends a temporary annotation to the cache.
 */
export function useCreateAnnotation(workspaceId: string, projectId: string, artifactId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: CreateAnnotationInput) =>
      annotationApi.create(workspaceId, projectId, artifactId, input),

    onMutate: async (input: CreateAnnotationInput) => {
      const slideKey = annotationKeys.slide(workspaceId, projectId, artifactId, input.slideIndex);

      // Cancel in-flight refetches to prevent overwriting optimistic update
      await queryClient.cancelQueries({ queryKey: slideKey });

      // Snapshot previous value for rollback
      const previousAnnotations = queryClient.getQueryData<ArtifactAnnotation[]>(slideKey);

      // Optimistically append the new annotation with a temp ID
      const tempAnnotation: ArtifactAnnotation = {
        id: `temp-${Date.now()}`,
        artifactId,
        slideIndex: input.slideIndex,
        content: input.content,
        userId: '', // filled in on server — not used for display during optimistic window
        workspaceId,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      };

      queryClient.setQueryData<ArtifactAnnotation[]>(slideKey, (old) =>
        old ? [...old, tempAnnotation] : [tempAnnotation]
      );

      return { previousAnnotations, slideKey };
    },

    onError: (_err, _input, context) => {
      if (context?.previousAnnotations !== undefined) {
        queryClient.setQueryData<ArtifactAnnotation[]>(
          context.slideKey,
          context.previousAnnotations
        );
      }
      toast.error('Failed to add annotation. Please try again.');
    },

    onSettled: (_data, _err, input) => {
      void queryClient.invalidateQueries({
        queryKey: annotationKeys.slide(workspaceId, projectId, artifactId, input.slideIndex),
      });
    },
  });
}

// ---------------------------------------------------------------------------
// useUpdateAnnotation — optimistic content update
// ---------------------------------------------------------------------------

interface UpdateAnnotationInput {
  annotationId: string;
  content: string;
  slideIndex: number;
}

/**
 * Update the content of an existing annotation (author only).
 * Optimistically updates the content in the cache.
 */
export function useUpdateAnnotation(workspaceId: string, projectId: string, artifactId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: UpdateAnnotationInput) =>
      annotationApi.update(workspaceId, projectId, artifactId, input.annotationId, {
        content: input.content,
      }),

    onMutate: async (input: UpdateAnnotationInput) => {
      const slideKey = annotationKeys.slide(workspaceId, projectId, artifactId, input.slideIndex);

      // Cancel in-flight refetches to prevent overwriting optimistic update
      await queryClient.cancelQueries({ queryKey: slideKey });

      // Snapshot previous value for rollback
      const previousAnnotations = queryClient.getQueryData<ArtifactAnnotation[]>(slideKey);

      // Optimistically update content in cache
      queryClient.setQueryData<ArtifactAnnotation[]>(slideKey, (old) =>
        old
          ? old.map((a) =>
              a.id === input.annotationId
                ? { ...a, content: input.content, updatedAt: new Date().toISOString() }
                : a
            )
          : []
      );

      return { previousAnnotations, slideKey };
    },

    onError: (_err, _input, context) => {
      if (context?.previousAnnotations !== undefined) {
        queryClient.setQueryData<ArtifactAnnotation[]>(
          context.slideKey,
          context.previousAnnotations
        );
      }
      toast.error('Update failed. Please try again.');
    },

    onSettled: (_data, _err, input) => {
      void queryClient.invalidateQueries({
        queryKey: annotationKeys.slide(workspaceId, projectId, artifactId, input.slideIndex),
      });
    },
  });
}

// ---------------------------------------------------------------------------
// useDeleteAnnotation — optimistic remove
// ---------------------------------------------------------------------------

interface DeleteAnnotationInput {
  annotationId: string;
  slideIndex: number;
}

/**
 * Delete an annotation (author only, hard delete).
 * Optimistically removes it from the cache.
 */
export function useDeleteAnnotation(workspaceId: string, projectId: string, artifactId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: DeleteAnnotationInput) =>
      annotationApi.delete(workspaceId, projectId, artifactId, input.annotationId),

    onMutate: async (input: DeleteAnnotationInput) => {
      const slideKey = annotationKeys.slide(workspaceId, projectId, artifactId, input.slideIndex);

      // Cancel in-flight refetches to prevent overwriting optimistic update
      await queryClient.cancelQueries({ queryKey: slideKey });

      // Snapshot previous value for rollback
      const previousAnnotations = queryClient.getQueryData<ArtifactAnnotation[]>(slideKey);

      // Optimistically remove the annotation
      queryClient.setQueryData<ArtifactAnnotation[]>(slideKey, (old) =>
        old ? old.filter((a) => a.id !== input.annotationId) : []
      );

      return { previousAnnotations, slideKey };
    },

    onError: (_err, _input, context) => {
      if (context?.previousAnnotations !== undefined) {
        queryClient.setQueryData<ArtifactAnnotation[]>(
          context.slideKey,
          context.previousAnnotations
        );
      }
      toast.error('Delete failed. Please try again.');
    },

    onSettled: (_data, _err, input) => {
      void queryClient.invalidateQueries({
        queryKey: annotationKeys.slide(workspaceId, projectId, artifactId, input.slideIndex),
      });
    },
  });
}

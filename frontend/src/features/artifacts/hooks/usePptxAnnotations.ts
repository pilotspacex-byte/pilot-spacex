'use client';

/**
 * usePptxAnnotations -- TanStack Query hook for per-slide annotation CRUD.
 *
 * Provides optimistic create/edit/delete mutations following Pattern 5
 * (onMutate snapshot + onError rollback + onSettled invalidation).
 *
 * IMPORTANT: This is a plain React hook (NOT observer) to avoid
 * flushSync issues with React 19 / TipTap portals.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  annotationsApi,
  type AnnotationListResponse,
  type AnnotationResponse,
} from '@/services/api/artifact-annotations';

export interface UsePptxAnnotationsParams {
  workspaceId: string;
  projectId: string;
  artifactId: string;
  slideIndex: number;
}

const annotationKeys = {
  all: ['artifact-annotations'] as const,
  list: (artifactId: string, slideIndex: number) =>
    [...annotationKeys.all, artifactId, slideIndex] as const,
};

export function usePptxAnnotations({
  workspaceId,
  projectId,
  artifactId,
  slideIndex,
}: UsePptxAnnotationsParams) {
  const queryClient = useQueryClient();
  const queryKey = annotationKeys.list(artifactId, slideIndex);

  // ---- Query ----
  const { data, isLoading } = useQuery({
    queryKey,
    queryFn: () => annotationsApi.list(workspaceId, projectId, artifactId, slideIndex),
    enabled: !!workspaceId && !!projectId && !!artifactId,
    staleTime: 30_000, // 30s -- annotations change infrequently
  });

  const annotations = data?.annotations ?? [];
  const total = data?.total ?? 0;

  // ---- Create mutation (optimistic) ----
  const createAnnotation = useMutation({
    mutationFn: (variables: { content: string }) =>
      annotationsApi.create(workspaceId, projectId, artifactId, {
        slide_index: slideIndex,
        content: variables.content,
      }),
    onMutate: async (variables) => {
      await queryClient.cancelQueries({ queryKey });
      const previous = queryClient.getQueryData<AnnotationListResponse>(queryKey);

      const tempAnnotation: AnnotationResponse = {
        id: `temp-${Date.now()}`,
        artifact_id: artifactId,
        slide_index: slideIndex,
        content: variables.content,
        user_id: '',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };

      queryClient.setQueryData<AnnotationListResponse>(queryKey, (old) => ({
        annotations: [...(old?.annotations ?? []), tempAnnotation],
        total: (old?.total ?? 0) + 1,
      }));

      return { previous };
    },
    onError: (_err, _variables, context) => {
      if (context?.previous) {
        queryClient.setQueryData(queryKey, context.previous);
      }
    },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey });
    },
  });

  // ---- Update mutation (optimistic) ----
  const updateAnnotation = useMutation({
    mutationFn: (variables: { annotationId: string; content: string }) =>
      annotationsApi.update(workspaceId, projectId, artifactId, variables.annotationId, {
        content: variables.content,
      }),
    onMutate: async (variables) => {
      await queryClient.cancelQueries({ queryKey });
      const previous = queryClient.getQueryData<AnnotationListResponse>(queryKey);

      queryClient.setQueryData<AnnotationListResponse>(queryKey, (old) => {
        if (!old) return old;
        return {
          ...old,
          annotations: old.annotations.map((a) =>
            a.id === variables.annotationId
              ? { ...a, content: variables.content, updated_at: new Date().toISOString() }
              : a
          ),
        };
      });

      return { previous };
    },
    onError: (_err, _variables, context) => {
      if (context?.previous) {
        queryClient.setQueryData(queryKey, context.previous);
      }
    },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey });
    },
  });

  // ---- Delete mutation (optimistic) ----
  const deleteAnnotation = useMutation({
    mutationFn: (variables: { annotationId: string }) =>
      annotationsApi.delete(workspaceId, projectId, artifactId, variables.annotationId),
    onMutate: async (variables) => {
      await queryClient.cancelQueries({ queryKey });
      const previous = queryClient.getQueryData<AnnotationListResponse>(queryKey);

      queryClient.setQueryData<AnnotationListResponse>(queryKey, (old) => {
        if (!old) return old;
        return {
          ...old,
          annotations: old.annotations.filter((a) => a.id !== variables.annotationId),
          total: Math.max(0, old.total - 1),
        };
      });

      return { previous };
    },
    onError: (_err, _variables, context) => {
      if (context?.previous) {
        queryClient.setQueryData(queryKey, context.previous);
      }
    },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey });
    },
  });

  return {
    annotations,
    total,
    isLoading,
    createAnnotation,
    updateAnnotation,
    deleteAnnotation,
  };
}

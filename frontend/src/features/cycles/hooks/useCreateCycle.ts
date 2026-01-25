'use client';

/**
 * useCreateCycle - Mutation hook for creating cycles.
 *
 * T169: Creates new cycles with optimistic updates.
 */
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { cyclesApi } from '@/services/api';
import type { Cycle, CreateCycleData, UpdateCycleData } from '@/types';
import { cyclesKeys } from './useCycles';

export interface UseCreateCycleOptions {
  /** Workspace ID (required) */
  workspaceId: string;
  /** Project ID for cache invalidation */
  projectId: string;
  /** Callback on success */
  onSuccess?: (cycle: Cycle) => void;
  /** Callback on error */
  onError?: (error: Error) => void;
}

export interface UseUpdateCycleOptions {
  /** Workspace ID (required) */
  workspaceId: string;
  /** Project ID for cache invalidation */
  projectId: string;
  /** Callback on success */
  onSuccess?: (cycle: Cycle) => void;
  /** Callback on error */
  onError?: (error: Error) => void;
}

export interface UseDeleteCycleOptions {
  /** Workspace ID (required) */
  workspaceId: string;
  /** Project ID for cache invalidation */
  projectId: string;
  /** Callback on success */
  onSuccess?: () => void;
  /** Callback on error */
  onError?: (error: Error) => void;
}

/**
 * Hook for creating a new cycle
 */
export function useCreateCycle({
  workspaceId,
  projectId,
  onSuccess,
  onError,
}: UseCreateCycleOptions) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreateCycleData) => cyclesApi.create(workspaceId, data),

    onSuccess: (cycle) => {
      // Invalidate cycles list
      queryClient.invalidateQueries({
        queryKey: cyclesKeys.list(workspaceId, projectId, {}),
      });

      // Add cycle to cache
      queryClient.setQueryData(cyclesKeys.detail(workspaceId, cycle.id), cycle);

      toast.success('Cycle created', {
        description: `"${cycle.name}" has been created.`,
      });

      onSuccess?.(cycle);
    },

    onError: (error: Error) => {
      toast.error('Failed to create cycle', {
        description: error.message,
      });
      onError?.(error);
    },
  });
}

/**
 * Hook for updating a cycle
 */
export function useUpdateCycle({
  workspaceId,
  projectId,
  onSuccess,
  onError,
}: UseUpdateCycleOptions) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ cycleId, data }: { cycleId: string; data: UpdateCycleData }) =>
      cyclesApi.update(workspaceId, cycleId, data),

    onMutate: async ({ cycleId, data }) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({
        queryKey: cyclesKeys.detail(workspaceId, cycleId),
      });

      // Snapshot previous value
      const previousCycle = queryClient.getQueryData<Cycle>(
        cyclesKeys.detail(workspaceId, cycleId)
      );

      // Optimistically update cache
      if (previousCycle) {
        queryClient.setQueryData(cyclesKeys.detail(workspaceId, cycleId), {
          ...previousCycle,
          ...data,
        });
      }

      return { previousCycle };
    },

    onSuccess: (cycle) => {
      // Update cache with server response
      queryClient.setQueryData(cyclesKeys.detail(workspaceId, cycle.id), cycle);

      // Invalidate list to reflect changes
      queryClient.invalidateQueries({
        queryKey: cyclesKeys.list(workspaceId, projectId, {}),
      });

      // Invalidate active cycle if status changed
      queryClient.invalidateQueries({
        queryKey: cyclesKeys.active(workspaceId, projectId),
      });

      toast.success('Cycle updated', {
        description: `"${cycle.name}" has been updated.`,
      });

      onSuccess?.(cycle);
    },

    onError: (error: Error, { cycleId }, context) => {
      // Rollback on error
      if (context?.previousCycle) {
        queryClient.setQueryData(cyclesKeys.detail(workspaceId, cycleId), context.previousCycle);
      }

      toast.error('Failed to update cycle', {
        description: error.message,
      });
      onError?.(error);
    },
  });
}

/**
 * Hook for deleting a cycle
 */
export function useDeleteCycle({
  workspaceId,
  projectId,
  onSuccess,
  onError,
}: UseDeleteCycleOptions) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (cycleId: string) => cyclesApi.delete(workspaceId, cycleId),

    onMutate: async (cycleId) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({
        queryKey: cyclesKeys.detail(workspaceId, cycleId),
      });

      // Snapshot previous value
      const previousCycle = queryClient.getQueryData<Cycle>(
        cyclesKeys.detail(workspaceId, cycleId)
      );

      // Optimistically remove from cache
      queryClient.removeQueries({
        queryKey: cyclesKeys.detail(workspaceId, cycleId),
      });

      return { previousCycle };
    },

    onSuccess: () => {
      // Invalidate list
      queryClient.invalidateQueries({
        queryKey: cyclesKeys.list(workspaceId, projectId, {}),
      });

      toast.success('Cycle deleted');
      onSuccess?.();
    },

    onError: (error: Error, cycleId, context) => {
      // Restore on error
      if (context?.previousCycle) {
        queryClient.setQueryData(cyclesKeys.detail(workspaceId, cycleId), context.previousCycle);
      }

      toast.error('Failed to delete cycle', {
        description: error.message,
      });
      onError?.(error);
    },
  });
}

/**
 * Hook for activating a cycle
 */
export function useActivateCycle({
  workspaceId,
  projectId,
  onSuccess,
  onError,
}: UseUpdateCycleOptions) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (cycleId: string) => cyclesApi.update(workspaceId, cycleId, { status: 'active' }),

    onSuccess: (cycle) => {
      // Update cache
      queryClient.setQueryData(cyclesKeys.detail(workspaceId, cycle.id), cycle);

      // Invalidate list and active cycle
      queryClient.invalidateQueries({
        queryKey: cyclesKeys.list(workspaceId, projectId, {}),
      });
      queryClient.invalidateQueries({
        queryKey: cyclesKeys.active(workspaceId, projectId),
      });

      toast.success('Cycle activated', {
        description: `"${cycle.name}" is now active.`,
      });

      onSuccess?.(cycle);
    },

    onError: (error: Error) => {
      toast.error('Failed to activate cycle', {
        description: error.message,
      });
      onError?.(error);
    },
  });
}

/**
 * Hook for completing a cycle
 */
export function useCompleteCycle({
  workspaceId,
  projectId,
  onSuccess,
  onError,
}: UseUpdateCycleOptions) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (cycleId: string) =>
      cyclesApi.update(workspaceId, cycleId, { status: 'completed' }),

    onSuccess: (cycle) => {
      queryClient.setQueryData(cyclesKeys.detail(workspaceId, cycle.id), cycle);

      queryClient.invalidateQueries({
        queryKey: cyclesKeys.list(workspaceId, projectId, {}),
      });
      queryClient.invalidateQueries({
        queryKey: cyclesKeys.active(workspaceId, projectId),
      });
      queryClient.invalidateQueries({
        queryKey: cyclesKeys.velocity(workspaceId, projectId),
      });

      toast.success('Cycle completed', {
        description: `"${cycle.name}" has been marked as complete.`,
      });

      onSuccess?.(cycle);
    },

    onError: (error: Error) => {
      toast.error('Failed to complete cycle', {
        description: error.message,
      });
      onError?.(error);
    },
  });
}

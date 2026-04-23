'use client';

/**
 * useRolloverCycle - Mutation hook for rolling over issues between cycles.
 *
 * T169: Handles rollover of incomplete issues to target cycle.
 */
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { cyclesApi } from '@/services/api';
import type { RolloverCycleData, RolloverCycleResult } from '@/types';
import { cyclesKeys } from './useCycles';

export interface UseRolloverCycleOptions {
  /** Workspace ID (required) */
  workspaceId: string;
  /** Project ID for cache invalidation */
  projectId: string;
  /** Source cycle ID */
  sourceCycleId: string;
  /** Callback on success */
  onSuccess?: (result: RolloverCycleResult) => void;
  /** Callback on error */
  onError?: (error: Error) => void;
}

export interface UseAddIssueToCycleOptions {
  /** Workspace ID (required) */
  workspaceId: string;
  /** Cycle ID */
  cycleId: string;
  /** Callback on success */
  onSuccess?: () => void;
  /** Callback on error */
  onError?: (error: Error) => void;
}

export interface UseRemoveIssueFromCycleOptions {
  /** Workspace ID (required) */
  workspaceId: string;
  /** Cycle ID */
  cycleId: string;
  /** Callback on success */
  onSuccess?: () => void;
  /** Callback on error */
  onError?: (error: Error) => void;
}

/**
 * Hook for rolling over incomplete issues to another cycle
 */
export function useRolloverCycle({
  workspaceId,
  projectId,
  sourceCycleId,
  onSuccess,
  onError,
}: UseRolloverCycleOptions) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: RolloverCycleData) => cyclesApi.rollover(workspaceId, sourceCycleId, data),

    onSuccess: (result) => {
      // Update source cycle in cache
      queryClient.setQueryData(
        cyclesKeys.detail(workspaceId, result.sourceCycle.id),
        result.sourceCycle
      );

      // Update target cycle in cache
      queryClient.setQueryData(
        cyclesKeys.detail(workspaceId, result.targetCycle.id),
        result.targetCycle
      );

      // Invalidate cycles list
      queryClient.invalidateQueries({
        queryKey: cyclesKeys.list(workspaceId, projectId, {}),
      });

      // Invalidate active cycle
      queryClient.invalidateQueries({
        queryKey: cyclesKeys.active(workspaceId, projectId),
      });

      // Invalidate issues for both cycles
      queryClient.invalidateQueries({
        queryKey: cyclesKeys.issues(workspaceId, sourceCycleId),
      });
      queryClient.invalidateQueries({
        queryKey: cyclesKeys.issues(workspaceId, result.targetCycle.id),
      });

      // Invalidate burndown data
      queryClient.invalidateQueries({
        queryKey: cyclesKeys.burndown(workspaceId, sourceCycleId),
      });
      queryClient.invalidateQueries({
        queryKey: cyclesKeys.burndown(workspaceId, result.targetCycle.id),
      });

      // Invalidate velocity data
      queryClient.invalidateQueries({
        queryKey: cyclesKeys.velocity(workspaceId, projectId),
      });

      toast.success('Tasks rolled over', {
        description: `${result.totalRolledOver} task${result.totalRolledOver === 1 ? '' : 's'} moved to "${result.targetCycle.name}".`,
      });

      onSuccess?.(result);
    },

    onError: (error: Error) => {
      toast.error('Failed to rollover tasks', {
        description: error.message,
      });
      onError?.(error);
    },
  });
}

/**
 * Hook for adding an issue to a cycle
 */
export function useAddIssueToCycle({
  workspaceId,
  cycleId,
  onSuccess,
  onError,
}: UseAddIssueToCycleOptions) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (issueId: string) => cyclesApi.addIssue(workspaceId, cycleId, issueId),

    onSuccess: () => {
      // Invalidate cycle issues
      queryClient.invalidateQueries({
        queryKey: cyclesKeys.issues(workspaceId, cycleId),
      });

      // Invalidate cycle detail for metrics update
      queryClient.invalidateQueries({
        queryKey: cyclesKeys.detail(workspaceId, cycleId),
      });

      // Invalidate burndown
      queryClient.invalidateQueries({
        queryKey: cyclesKeys.burndown(workspaceId, cycleId),
      });

      toast.success('Task added to cycle');
      onSuccess?.();
    },

    onError: (error: Error) => {
      toast.error('Failed to add task to cycle', {
        description: error.message,
      });
      onError?.(error);
    },
  });
}

/**
 * Hook for bulk adding issues to a cycle
 */
export function useBulkAddIssuesToCycle({
  workspaceId,
  cycleId,
  onSuccess,
  onError,
}: UseAddIssueToCycleOptions) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (issueIds: string[]) => cyclesApi.bulkAddIssues(workspaceId, cycleId, issueIds),

    onSuccess: (result) => {
      // Invalidate cycle issues
      queryClient.invalidateQueries({
        queryKey: cyclesKeys.issues(workspaceId, cycleId),
      });

      // Invalidate cycle detail for metrics update
      queryClient.invalidateQueries({
        queryKey: cyclesKeys.detail(workspaceId, cycleId),
      });

      // Invalidate burndown
      queryClient.invalidateQueries({
        queryKey: cyclesKeys.burndown(workspaceId, cycleId),
      });

      toast.success('Tasks added to cycle', {
        description: `${result.addedCount} task${result.addedCount === 1 ? '' : 's'} added.`,
      });
      onSuccess?.();
    },

    onError: (error: Error) => {
      toast.error('Failed to add tasks to cycle', {
        description: error.message,
      });
      onError?.(error);
    },
  });
}

/**
 * Hook for removing an issue from a cycle
 */
export function useRemoveIssueFromCycle({
  workspaceId,
  cycleId,
  onSuccess,
  onError,
}: UseRemoveIssueFromCycleOptions) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (issueId: string) => cyclesApi.removeIssue(workspaceId, cycleId, issueId),

    onMutate: async (_issueId) => {
      void _issueId; // Used in mutation
      // Cancel outgoing refetches
      await queryClient.cancelQueries({
        queryKey: cyclesKeys.issues(workspaceId, cycleId),
      });

      // Snapshot previous value
      const previousIssues = queryClient.getQueryData(cyclesKeys.issues(workspaceId, cycleId));

      return { previousIssues };
    },

    onSuccess: () => {
      // Invalidate cycle issues
      queryClient.invalidateQueries({
        queryKey: cyclesKeys.issues(workspaceId, cycleId),
      });

      // Invalidate cycle detail for metrics update
      queryClient.invalidateQueries({
        queryKey: cyclesKeys.detail(workspaceId, cycleId),
      });

      // Invalidate burndown
      queryClient.invalidateQueries({
        queryKey: cyclesKeys.burndown(workspaceId, cycleId),
      });

      toast.success('Task removed from cycle');
      onSuccess?.();
    },

    onError: (error: Error, _issueId, context) => {
      // Rollback on error
      if (context?.previousIssues) {
        queryClient.setQueryData(cyclesKeys.issues(workspaceId, cycleId), context.previousIssues);
      }

      toast.error('Failed to remove issue from cycle', {
        description: error.message,
      });
      onError?.(error);
    },
  });
}

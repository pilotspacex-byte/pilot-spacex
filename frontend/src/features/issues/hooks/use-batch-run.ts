/**
 * useBatchRun - TanStack Query hooks for batch implementation runs.
 *
 * Phase 76: Sprint Batch Implementation
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/services/api';
import type { ImplementationStatus } from '../components/implementation-status-badge';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface BatchRunIssue {
  id: string;
  issueId: string;
  issueIdentifier?: string;
  issueTitle?: string;
  status: ImplementationStatus;
  executionOrder: number;
  currentStage: string | null;
  prUrl: string | null;
  errorMessage: string | null;
}

export interface BatchRun {
  id: string;
  cycleId: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  totalIssues: number;
  completedIssues: number;
  failedIssues: number;
  items: BatchRunIssue[];
  createdAt: string;
  updatedAt: string;
}

export interface BatchRunPreview {
  issues: Array<{
    id: string;
    identifier: string;
    title: string;
    executionOrder: number;
    dependsOn: string[];
  }>;
  parallelTracks: number;
  hasCycle: boolean;
  cycleIssues?: string[];
}

export interface CreateBatchRunData {
  cycleId: string;
}

// ---------------------------------------------------------------------------
// Query Keys
// ---------------------------------------------------------------------------

export const batchRunKeys = {
  all: ['batch-run'] as const,
  detail: (batchRunId: string) => ['batch-run', batchRunId] as const,
  issues: (batchRunId: string) => ['batch-run-issues', batchRunId] as const,
  preview: (cycleId: string) => ['batch-run-preview', cycleId] as const,
};

// ---------------------------------------------------------------------------
// Hooks
// ---------------------------------------------------------------------------

/**
 * Fetch a single batch run by ID.
 */
export function useBatchRun(workspaceSlug: string, batchRunId: string | null) {
  return useQuery({
    queryKey: batchRunId ? batchRunKeys.detail(batchRunId) : ['batch-run', null],
    queryFn: () => apiClient.get<BatchRun>(`/batch-runs/${batchRunId}`),
    enabled: !!workspaceSlug && !!batchRunId,
    refetchInterval: (query) => {
      const data = query.state.data;
      // Poll every 5s while the run is active
      if (data && (data.status === 'running' || data.status === 'pending')) {
        return 5000;
      }
      return false;
    },
  });
}

/**
 * Fetch DAG preview for a cycle before starting a batch run.
 */
export function useBatchRunPreview(workspaceSlug: string, cycleId: string | null) {
  return useQuery({
    queryKey: cycleId ? batchRunKeys.preview(cycleId) : ['batch-run-preview', null],
    queryFn: () => apiClient.get<BatchRunPreview>(`/batch-runs/preview/${cycleId}`),
    enabled: !!workspaceSlug && !!cycleId,
    staleTime: 30_000, // Preview is fresh for 30s
  });
}

/**
 * Create a new batch run for a cycle.
 */
export function useCreateBatchRun(workspaceSlug: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreateBatchRunData) =>
      apiClient.post<BatchRun>('/batch-runs', data),
    onSuccess: (data) => {
      queryClient.setQueryData(batchRunKeys.detail(data.id), data);
    },
    meta: { workspaceSlug },
  });
}

/**
 * Cancel an entire batch run.
 */
export function useCancelBatchRun(workspaceSlug: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (batchRunId: string) =>
      apiClient.post<BatchRun>(`/batch-runs/${batchRunId}/cancel`),
    onMutate: async (batchRunId) => {
      await queryClient.cancelQueries({ queryKey: batchRunKeys.detail(batchRunId) });
      const previous = queryClient.getQueryData<BatchRun>(batchRunKeys.detail(batchRunId));

      // Optimistic update
      queryClient.setQueryData<BatchRun>(batchRunKeys.detail(batchRunId), (old) =>
        old ? { ...old, status: 'cancelled' } : old
      );

      return { previous, batchRunId };
    },
    onError: (_err, batchRunId, context) => {
      // Revert on error
      if (context?.previous) {
        queryClient.setQueryData(batchRunKeys.detail(batchRunId), context.previous);
      }
    },
    onSettled: (_data, _err, batchRunId) => {
      queryClient.invalidateQueries({ queryKey: batchRunKeys.detail(batchRunId) });
    },
    meta: { workspaceSlug },
  });
}

/**
 * Cancel a single issue within a batch run.
 */
export function useCancelBatchRunIssue(workspaceSlug: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ batchRunId, issueId }: { batchRunId: string; issueId: string }) =>
      apiClient.post<void>(`/batch-runs/${batchRunId}/issues/${issueId}/cancel`),
    onMutate: async ({ batchRunId, issueId }) => {
      await queryClient.cancelQueries({ queryKey: batchRunKeys.detail(batchRunId) });
      const previous = queryClient.getQueryData<BatchRun>(batchRunKeys.detail(batchRunId));

      // Optimistic update — mark that specific issue as cancelled
      queryClient.setQueryData<BatchRun>(batchRunKeys.detail(batchRunId), (old) => {
        if (!old) return old;
        return {
          ...old,
          items: old.items.map((item) =>
            item.issueId === issueId ? { ...item, status: 'cancelled' as ImplementationStatus } : item
          ),
        };
      });

      return { previous, batchRunId };
    },
    onError: (_err, { batchRunId }, context) => {
      if (context?.previous) {
        queryClient.setQueryData(batchRunKeys.detail(batchRunId), context.previous);
      }
    },
    onSettled: (_data, _err, { batchRunId }) => {
      queryClient.invalidateQueries({ queryKey: batchRunKeys.detail(batchRunId) });
    },
    meta: { workspaceSlug },
  });
}

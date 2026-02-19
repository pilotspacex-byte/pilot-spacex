'use client';

import * as React from 'react';
import { useQuery, useMutation, useQueryClient, type UseQueryOptions } from '@tanstack/react-query';
import { toast } from 'sonner';
import { supabase } from '@/lib/supabase';
// import { queryKeys } from '@/lib/queryClient';
import { approvalsApi } from '@/services/api';
import type { PendingApproval, CreateApprovalRequest, ApprovalResolution } from '@/types';

/**
 * Query key factory for approvals.
 */
const approvalKeys = {
  all: ['approvals'] as const,
  pending: (workspaceId: string) => [...approvalKeys.all, 'pending', workspaceId] as const,
  detail: (workspaceId: string, approvalId: string) =>
    [...approvalKeys.all, 'detail', workspaceId, approvalId] as const,
  count: (workspaceId: string) => [...approvalKeys.all, 'count', workspaceId] as const,
};

export interface UseApprovalFlowOptions {
  /** Workspace ID to fetch approvals for */
  workspaceId: string;
  /** Whether to enable realtime subscriptions */
  enableRealtime?: boolean;
  /** Whether to show toast notifications for new approvals */
  showNotifications?: boolean;
  /** Callback when a new approval is received */
  onNewApproval?: (approval: PendingApproval) => void;
  /** Callback to show/navigate to a specific approval. Called from toast action button. */
  onShowApproval?: (approvalId: string) => void;
}

export interface UseApprovalFlowReturn {
  /** List of pending approvals */
  pendingApprovals: PendingApproval[];
  /** Whether approvals are loading */
  isLoading: boolean;
  /** Whether there was an error loading approvals */
  isError: boolean;
  /** Error message if any */
  error: Error | null;
  /** Count of pending approvals */
  pendingCount: number;
  /** Approve a pending approval */
  approve: (approvalId: string, note?: string) => Promise<ApprovalResolution>;
  /** Reject a pending approval */
  reject: (approvalId: string, reason?: string) => Promise<ApprovalResolution>;
  /** Create a new approval request */
  createApproval: (data: CreateApprovalRequest) => Promise<PendingApproval>;
  /** Whether an approval operation is in progress */
  isApproving: boolean;
  /** Whether a rejection operation is in progress */
  isRejecting: boolean;
  /** Whether a creation operation is in progress */
  isCreating: boolean;
  /** Refetch pending approvals */
  refetch: () => void;
}

/**
 * Hook for managing the human-in-the-loop approval flow.
 *
 * Features per DD-003:
 * - Polls for pending approvals
 * - Handles approve/reject mutations
 * - Realtime subscription via Supabase Realtime
 * - Toast notifications on new approvals
 *
 * @example
 * ```tsx
 * const {
 *   pendingApprovals,
 *   approve,
 *   reject,
 *   pendingCount,
 *   isApproving,
 * } = useApprovalFlow({ workspaceId: 'ws-123' });
 *
 * // Show approval dialog
 * const handleApprove = async () => {
 *   await approve(approval.id);
 *   toast.success('Action approved');
 * };
 * ```
 */
export function useApprovalFlow({
  workspaceId,
  enableRealtime = true,
  showNotifications = true,
  onNewApproval,
  onShowApproval,
}: UseApprovalFlowOptions): UseApprovalFlowReturn {
  const queryClient = useQueryClient();

  // Fetch pending approvals
  const {
    data: approvalsData,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: approvalKeys.pending(workspaceId),
    queryFn: () => approvalsApi.listPending(workspaceId),
    enabled: !!workspaceId,
    staleTime: 30 * 1000, // 30 seconds
    refetchInterval: 60 * 1000, // Poll every minute as fallback
  });

  // Fetch pending count for badges
  const { data: countData } = useQuery({
    queryKey: approvalKeys.count(workspaceId),
    queryFn: () => approvalsApi.getPendingCount(workspaceId),
    enabled: !!workspaceId,
    staleTime: 30 * 1000,
  });

  // Approve mutation
  const approveMutation = useMutation({
    mutationFn: ({ approvalId, note }: { approvalId: string; note?: string }) =>
      approvalsApi.approve(workspaceId, approvalId, note),
    onSuccess: (result) => {
      // Invalidate queries
      queryClient.invalidateQueries({ queryKey: approvalKeys.pending(workspaceId) });
      queryClient.invalidateQueries({ queryKey: approvalKeys.count(workspaceId) });

      // Show success toast
      toast.success('Action approved', {
        description: result.actionExecuted
          ? 'The action has been executed successfully.'
          : 'The action has been approved.',
      });
    },
    onError: (error: Error) => {
      toast.error('Failed to approve', {
        description: error.message,
      });
    },
  });

  // Reject mutation
  const rejectMutation = useMutation({
    mutationFn: ({ approvalId, reason }: { approvalId: string; reason?: string }) =>
      approvalsApi.reject(workspaceId, approvalId, reason),
    onSuccess: () => {
      // Invalidate queries
      queryClient.invalidateQueries({ queryKey: approvalKeys.pending(workspaceId) });
      queryClient.invalidateQueries({ queryKey: approvalKeys.count(workspaceId) });

      toast.success('Action rejected', {
        description: 'The AI action has been rejected.',
      });
    },
    onError: (error: Error) => {
      toast.error('Failed to reject', {
        description: error.message,
      });
    },
  });

  // Create approval mutation
  const createMutation = useMutation({
    mutationFn: (data: CreateApprovalRequest) => approvalsApi.create(workspaceId, data),
    onSuccess: (approval) => {
      // Invalidate queries
      queryClient.invalidateQueries({ queryKey: approvalKeys.pending(workspaceId) });
      queryClient.invalidateQueries({ queryKey: approvalKeys.count(workspaceId) });

      // Notify about new approval
      if (showNotifications) {
        toast.info('New approval required', {
          description: approval.actionDescription,
        });
      }
    },
    onError: (error: Error) => {
      toast.error('Failed to create approval', {
        description: error.message,
      });
    },
  });

  // Realtime subscription
  React.useEffect(() => {
    if (!enableRealtime || !workspaceId) return;

    const channel = supabase
      .channel(`approvals:${workspaceId}`)
      .on(
        'postgres_changes',
        {
          event: 'INSERT',
          schema: 'public',
          table: 'pending_approvals',
          filter: `workspace_id=eq.${workspaceId}`,
        },
        (payload) => {
          // Invalidate queries to refresh the list
          queryClient.invalidateQueries({ queryKey: approvalKeys.pending(workspaceId) });
          queryClient.invalidateQueries({ queryKey: approvalKeys.count(workspaceId) });

          const newApproval = payload.new as PendingApproval;

          // Call callback if provided
          onNewApproval?.(newApproval);

          // Show notification
          if (showNotifications) {
            toast.info('New action requires your approval', {
              description: newApproval.actionDescription,
              action: {
                label: 'View',
                onClick: () => {
                  onShowApproval?.(newApproval.id);
                },
              },
            });
          }
        }
      )
      .on(
        'postgres_changes',
        {
          event: 'UPDATE',
          schema: 'public',
          table: 'pending_approvals',
          filter: `workspace_id=eq.${workspaceId}`,
        },
        () => {
          // Refresh on any updates (resolved, expired, etc.)
          queryClient.invalidateQueries({ queryKey: approvalKeys.pending(workspaceId) });
          queryClient.invalidateQueries({ queryKey: approvalKeys.count(workspaceId) });
        }
      )
      .on(
        'postgres_changes',
        {
          event: 'DELETE',
          schema: 'public',
          table: 'pending_approvals',
          filter: `workspace_id=eq.${workspaceId}`,
        },
        () => {
          // Refresh on deletions
          queryClient.invalidateQueries({ queryKey: approvalKeys.pending(workspaceId) });
          queryClient.invalidateQueries({ queryKey: approvalKeys.count(workspaceId) });
        }
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, [workspaceId, enableRealtime, showNotifications, queryClient, onNewApproval, onShowApproval]);

  // Wrapper functions for mutations
  const approve = React.useCallback(
    async (approvalId: string, note?: string): Promise<ApprovalResolution> => {
      return approveMutation.mutateAsync({ approvalId, note });
    },
    [approveMutation]
  );

  const reject = React.useCallback(
    async (approvalId: string, reason?: string): Promise<ApprovalResolution> => {
      return rejectMutation.mutateAsync({ approvalId, reason });
    },
    [rejectMutation]
  );

  const createApproval = React.useCallback(
    async (data: CreateApprovalRequest): Promise<PendingApproval> => {
      return createMutation.mutateAsync(data);
    },
    [createMutation]
  );

  return {
    pendingApprovals: approvalsData?.items ?? [],
    isLoading,
    isError,
    error: error as Error | null,
    pendingCount: countData?.count ?? 0,
    approve,
    reject,
    createApproval,
    isApproving: approveMutation.isPending,
    isRejecting: rejectMutation.isPending,
    isCreating: createMutation.isPending,
    refetch,
  };
}

/**
 * Hook to fetch a single approval by ID.
 */
export function useApproval(
  workspaceId: string,
  approvalId: string,
  options?: Omit<UseQueryOptions<PendingApproval>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: approvalKeys.detail(workspaceId, approvalId),
    queryFn: () => approvalsApi.get(workspaceId, approvalId),
    enabled: !!workspaceId && !!approvalId,
    ...options,
  });
}

/**
 * Hook for approval count badge.
 */
export function useApprovalCount(workspaceId: string) {
  const { data, isLoading } = useQuery({
    queryKey: approvalKeys.count(workspaceId),
    queryFn: () => approvalsApi.getPendingCount(workspaceId),
    enabled: !!workspaceId,
    staleTime: 30 * 1000,
    refetchInterval: 60 * 1000,
  });

  return {
    count: data?.count ?? 0,
    isLoading,
  };
}

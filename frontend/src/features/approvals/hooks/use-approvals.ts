/**
 * useApprovals — TanStack Query hooks for AI approval requests.
 *
 * AIGOV-01: Approvals queue (list, resolve) per DD-003 human-in-the-loop.
 *
 * Uses the existing approvalsApi service which calls /ai/approvals endpoints.
 * NOT observer() — plain TanStack Query hooks.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { approvalsApi } from '@/services/api';
import type { ApprovalStatus, PendingApproval } from '@/types';

// ---- Types ----

export type { PendingApproval };

export interface ApprovalListResult {
  items: PendingApproval[];
  total: number;
  pending_count: number;
}

// ---- Hooks ----

/**
 * Fetch approvals filtered by status.
 * workspaceId is passed through but the backend uses the JWT for workspace context.
 */
export function useApprovals(workspaceId: string, status?: ApprovalStatus) {
  return useQuery<ApprovalListResult>({
    queryKey: ['approvals', workspaceId, status ?? 'all'],
    queryFn: () => approvalsApi.list(workspaceId, { status }),
    enabled: Boolean(workspaceId),
  });
}

/**
 * Fetch count of pending approvals for badge display.
 * Returns 0 when not loaded.
 */
export function usePendingApprovalCount(workspaceId: string): number {
  const { data } = useApprovals(workspaceId, 'pending');
  return data?.pending_count ?? data?.items.length ?? 0;
}

/**
 * Resolve an approval (approve or reject).
 */
export function useResolveApproval(workspaceId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      action,
      reason,
    }: {
      id: string;
      action: 'approve' | 'reject';
      reason?: string;
    }) => {
      if (action === 'approve') {
        return approvalsApi.approve(workspaceId, id);
      }
      return approvalsApi.reject(workspaceId, id, reason);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['approvals', workspaceId] });
    },
  });
}

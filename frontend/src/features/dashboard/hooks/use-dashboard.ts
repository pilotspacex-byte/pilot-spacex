/**
 * useDashboard — TanStack Query hook for the Implementation Dashboard.
 *
 * Fetches aggregated dashboard data from:
 * GET /workspaces/{workspace_id}/batch-runs/{batch_run_id}/dashboard
 *
 * Polls every 30 seconds while the sprint is active (running or pending),
 * then stops when the batch run reaches a terminal state.
 *
 * Phase 77 Plan 01 — dashboard data layer.
 */

import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/services/api';
import type { DashboardData } from '../types';

export const dashboardKeys = {
  all: ['dashboard'] as const,
  detail: (batchRunId: string) => ['dashboard', batchRunId] as const,
};

export function useDashboard(workspaceSlug: string, batchRunId: string | null) {
  return useQuery({
    queryKey: batchRunId ? dashboardKeys.detail(batchRunId) : ['dashboard', null],
    queryFn: () => apiClient.get<DashboardData>(`/batch-runs/${batchRunId}/dashboard`),
    enabled: !!workspaceSlug && !!batchRunId,
    refetchInterval: (query) => {
      const data = query.state.data;
      // 30-second refetch while sprint is active (per CONTEXT.md decision)
      if (data && (data.status === 'running' || data.status === 'pending')) {
        return 30_000;
      }
      return false;
    },
    staleTime: 10_000,
  });
}

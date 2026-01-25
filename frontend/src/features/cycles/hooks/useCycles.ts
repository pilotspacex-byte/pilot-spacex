'use client';

/**
 * useCycles - TanStack Query hook for fetching cycles list with cursor pagination.
 *
 * T169: Lists cycles for a project with filtering and sorting.
 */
import { useQuery, useInfiniteQuery, useQueryClient } from '@tanstack/react-query';
import { cyclesApi, type CycleListResponse } from '@/services/api';
import type { Cycle, CycleStatus } from '@/types';

export const CYCLES_QUERY_KEY = 'cycles';

export interface UseCyclesOptions {
  /** Workspace ID (required) */
  workspaceId: string;
  /** Project ID (required) */
  projectId: string;
  /** Filter by status */
  status?: CycleStatus;
  /** Search query */
  search?: string;
  /** Include metrics in response */
  includeMetrics?: boolean;
  /** Page size */
  pageSize?: number;
  /** Sort by field */
  sortBy?: 'sequence' | 'created_at' | 'start_date';
  /** Sort order */
  sortOrder?: 'asc' | 'desc';
  /** Enable query */
  enabled?: boolean;
}

/**
 * Query key factory for cycles
 */
export const cyclesKeys = {
  all: [CYCLES_QUERY_KEY] as const,
  lists: () => [...cyclesKeys.all, 'list'] as const,
  list: (
    workspaceId: string,
    projectId: string,
    filters?: { status?: CycleStatus; search?: string }
  ) => [...cyclesKeys.lists(), workspaceId, projectId, filters] as const,
  details: () => [...cyclesKeys.all, 'detail'] as const,
  detail: (workspaceId: string, cycleId: string) =>
    [...cyclesKeys.details(), workspaceId, cycleId] as const,
  active: (workspaceId: string, projectId: string) =>
    [...cyclesKeys.all, 'active', workspaceId, projectId] as const,
  issues: (workspaceId: string, cycleId: string) =>
    [...cyclesKeys.detail(workspaceId, cycleId), 'issues'] as const,
  burndown: (workspaceId: string, cycleId: string) =>
    [...cyclesKeys.detail(workspaceId, cycleId), 'burndown'] as const,
  velocity: (workspaceId: string, projectId: string) =>
    [...cyclesKeys.all, 'velocity', workspaceId, projectId] as const,
};

/**
 * Hook for fetching paginated cycles list
 */
export function useCycles({
  workspaceId,
  projectId,
  status,
  search,
  includeMetrics = true,
  pageSize = 20,
  sortBy = 'sequence',
  sortOrder = 'desc',
  enabled = true,
}: UseCyclesOptions) {
  return useQuery({
    queryKey: cyclesKeys.list(workspaceId, projectId, { status, search }),
    queryFn: () =>
      cyclesApi.list(
        workspaceId,
        { projectId, status, search, includeMetrics },
        { pageSize, sortBy, sortOrder }
      ),
    enabled: enabled && !!workspaceId && !!projectId,
    staleTime: 1000 * 60 * 2, // 2 minutes
    gcTime: 1000 * 60 * 15, // 15 minutes
  });
}

/**
 * Hook for infinite scroll cycles list
 */
export function useInfiniteCycles({
  workspaceId,
  projectId,
  status,
  search,
  includeMetrics = true,
  pageSize = 20,
  sortBy = 'sequence',
  sortOrder = 'desc',
  enabled = true,
}: UseCyclesOptions) {
  return useInfiniteQuery({
    queryKey: [...cyclesKeys.list(workspaceId, projectId, { status, search }), 'infinite'],
    queryFn: ({ pageParam }) =>
      cyclesApi.list(
        workspaceId,
        { projectId, status, search, includeMetrics },
        { cursor: pageParam, pageSize, sortBy, sortOrder }
      ),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (lastPage: CycleListResponse) => {
      if (lastPage.hasNext && lastPage.nextCursor) {
        return lastPage.nextCursor;
      }
      return undefined;
    },
    enabled: enabled && !!workspaceId && !!projectId,
    staleTime: 1000 * 60 * 2,
    gcTime: 1000 * 60 * 15,
  });
}

/**
 * Select all cycles from query data
 */
export function selectAllCycles(data: CycleListResponse | undefined): Cycle[] {
  return data?.items ?? [];
}

/**
 * Select cycles by status from query data
 */
export function selectCyclesByStatus(
  data: CycleListResponse | undefined,
  status: CycleStatus | CycleStatus[]
): Cycle[] {
  const statusArray = Array.isArray(status) ? status : [status];
  return (data?.items ?? []).filter((c) => statusArray.includes(c.status));
}

/**
 * Select active cycle from query data
 */
export function selectActiveCycle(data: CycleListResponse | undefined): Cycle | null {
  return (data?.items ?? []).find((c) => c.status === 'active') ?? null;
}

/**
 * Hook to prefetch cycles for a project
 */
export function usePrefetchCycles() {
  const queryClient = useQueryClient();

  return (workspaceId: string, projectId: string) => {
    queryClient.prefetchQuery({
      queryKey: cyclesKeys.list(workspaceId, projectId, {}),
      queryFn: () =>
        cyclesApi.list(
          workspaceId,
          { projectId, includeMetrics: true },
          { pageSize: 20, sortBy: 'sequence', sortOrder: 'desc' }
        ),
      staleTime: 1000 * 60 * 2,
    });
  };
}

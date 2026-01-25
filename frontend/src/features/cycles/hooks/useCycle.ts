'use client';

/**
 * useCycle - TanStack Query hook for fetching a single cycle with details.
 *
 * T169: Fetches single cycle with metrics, issues, and chart data.
 */
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { cyclesApi } from '@/services/api';
import type { Cycle } from '@/types';
import { cyclesKeys } from './useCycles';

export interface UseCycleOptions {
  /** Workspace ID (required) */
  workspaceId: string;
  /** Cycle ID (required) */
  cycleId: string;
  /** Include metrics in response */
  includeMetrics?: boolean;
  /** Enable query */
  enabled?: boolean;
}

export interface UseCycleIssuesOptions {
  /** Workspace ID (required) */
  workspaceId: string;
  /** Cycle ID (required) */
  cycleId: string;
  /** Include completed issues */
  includeCompleted?: boolean;
  /** Enable query */
  enabled?: boolean;
}

export interface UseCycleBurndownOptions {
  /** Workspace ID (required) */
  workspaceId: string;
  /** Cycle ID (required) */
  cycleId: string;
  /** Enable query */
  enabled?: boolean;
}

export interface UseVelocityOptions {
  /** Workspace ID (required) */
  workspaceId: string;
  /** Project ID (required) */
  projectId: string;
  /** Number of cycles to include */
  limit?: number;
  /** Enable query */
  enabled?: boolean;
}

export interface UseActiveCycleOptions {
  /** Workspace ID (required) */
  workspaceId: string;
  /** Project ID (required) */
  projectId: string;
  /** Include metrics in response */
  includeMetrics?: boolean;
  /** Enable query */
  enabled?: boolean;
}

/**
 * Hook for fetching a single cycle by ID
 */
export function useCycle({
  workspaceId,
  cycleId,
  includeMetrics = true,
  enabled = true,
}: UseCycleOptions) {
  return useQuery({
    queryKey: cyclesKeys.detail(workspaceId, cycleId),
    queryFn: () => cyclesApi.get(workspaceId, cycleId, includeMetrics),
    enabled: enabled && !!workspaceId && !!cycleId,
    staleTime: 1000 * 60 * 2, // 2 minutes
    gcTime: 1000 * 60 * 15, // 15 minutes
  });
}

/**
 * Hook for fetching the active cycle for a project
 */
export function useActiveCycle({
  workspaceId,
  projectId,
  includeMetrics = true,
  enabled = true,
}: UseActiveCycleOptions) {
  return useQuery({
    queryKey: cyclesKeys.active(workspaceId, projectId),
    queryFn: () => cyclesApi.getActive(workspaceId, projectId, includeMetrics),
    enabled: enabled && !!workspaceId && !!projectId,
    staleTime: 1000 * 60 * 2,
    gcTime: 1000 * 60 * 15,
  });
}

/**
 * Hook for fetching issues in a cycle
 */
export function useCycleIssues({
  workspaceId,
  cycleId,
  includeCompleted = true,
  enabled = true,
}: UseCycleIssuesOptions) {
  return useQuery({
    queryKey: cyclesKeys.issues(workspaceId, cycleId),
    queryFn: () => cyclesApi.getIssues(workspaceId, cycleId, includeCompleted),
    enabled: enabled && !!workspaceId && !!cycleId,
    staleTime: 1000 * 30, // 30 seconds - issues change frequently
    gcTime: 1000 * 60 * 10,
  });
}

/**
 * Hook for fetching burndown chart data
 */
export function useCycleBurndown({
  workspaceId,
  cycleId,
  enabled = true,
}: UseCycleBurndownOptions) {
  return useQuery({
    queryKey: cyclesKeys.burndown(workspaceId, cycleId),
    queryFn: () => cyclesApi.getBurndownData(workspaceId, cycleId),
    enabled: enabled && !!workspaceId && !!cycleId,
    staleTime: 1000 * 60 * 5, // 5 minutes
    gcTime: 1000 * 60 * 30,
  });
}

/**
 * Hook for fetching velocity chart data
 */
export function useVelocity({
  workspaceId,
  projectId,
  limit = 10,
  enabled = true,
}: UseVelocityOptions) {
  return useQuery({
    queryKey: cyclesKeys.velocity(workspaceId, projectId),
    queryFn: () => cyclesApi.getVelocityData(workspaceId, projectId, limit),
    enabled: enabled && !!workspaceId && !!projectId,
    staleTime: 1000 * 60 * 5, // 5 minutes
    gcTime: 1000 * 60 * 30,
  });
}

/**
 * Hook to prefetch cycle details
 */
export function usePrefetchCycle() {
  const queryClient = useQueryClient();

  return (workspaceId: string, cycleId: string) => {
    queryClient.prefetchQuery({
      queryKey: cyclesKeys.detail(workspaceId, cycleId),
      queryFn: () => cyclesApi.get(workspaceId, cycleId, true),
      staleTime: 1000 * 60 * 2,
    });
  };
}

/**
 * Hook to get cached cycle data
 */
export function useCycleCache() {
  const queryClient = useQueryClient();

  return {
    getCycle: (workspaceId: string, cycleId: string) =>
      queryClient.getQueryData<Cycle>(cyclesKeys.detail(workspaceId, cycleId)),

    setCycle: (workspaceId: string, cycleId: string, cycle: Cycle) =>
      queryClient.setQueryData(cyclesKeys.detail(workspaceId, cycleId), cycle),

    invalidateCycle: (workspaceId: string, cycleId: string) =>
      queryClient.invalidateQueries({
        queryKey: cyclesKeys.detail(workspaceId, cycleId),
      }),

    invalidateCycleIssues: (workspaceId: string, cycleId: string) =>
      queryClient.invalidateQueries({
        queryKey: cyclesKeys.issues(workspaceId, cycleId),
      }),

    invalidateProjectCycles: (workspaceId: string, projectId: string) =>
      queryClient.invalidateQueries({
        queryKey: cyclesKeys.list(workspaceId, projectId, {}),
      }),

    invalidateAll: () => queryClient.invalidateQueries({ queryKey: cyclesKeys.all }),
  };
}

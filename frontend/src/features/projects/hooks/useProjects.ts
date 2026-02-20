'use client';

/**
 * useProjects - TanStack Query hook for fetching projects list.
 *
 * T005: Lists projects for a workspace with caching.
 */
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { projectsApi } from '@/services/api';
import type { Project } from '@/types';
import type { PaginatedResponse } from '@/services/api/client';

export const PROJECTS_QUERY_KEY = 'projects';

/**
 * Query key factory for projects
 */
export const projectsKeys = {
  all: [PROJECTS_QUERY_KEY] as const,
  lists: () => [...projectsKeys.all, 'list'] as const,
  list: (workspaceId: string) => [...projectsKeys.lists(), workspaceId] as const,
  details: () => [...projectsKeys.all, 'detail'] as const,
  detail: (projectId: string) => [...projectsKeys.details(), projectId] as const,
};

export interface UseProjectsOptions {
  /** Workspace ID (required) */
  workspaceId: string;
  /** Enable query */
  enabled?: boolean;
}

/**
 * Hook for fetching projects list
 */
export function useProjects({ workspaceId, enabled = true }: UseProjectsOptions) {
  return useQuery({
    queryKey: projectsKeys.list(workspaceId),
    queryFn: () => projectsApi.list(workspaceId),
    enabled: enabled && !!workspaceId,
    staleTime: 1000 * 60 * 2, // 2 minutes
    gcTime: 1000 * 60 * 15, // 15 minutes
  });
}

/**
 * Select all projects from query data
 */
export function selectAllProjects(data: PaginatedResponse<Project> | undefined): Project[] {
  return data?.items ?? [];
}

/**
 * Hook to prefetch projects for a workspace
 */
export function usePrefetchProjects() {
  const queryClient = useQueryClient();

  return (workspaceId: string) => {
    queryClient.prefetchQuery({
      queryKey: projectsKeys.list(workspaceId),
      queryFn: () => projectsApi.list(workspaceId),
      staleTime: 1000 * 60 * 2,
    });
  };
}

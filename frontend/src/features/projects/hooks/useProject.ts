'use client';

/**
 * useProject - TanStack Query hook for fetching a single project.
 *
 * T006: Fetches project detail by ID with caching.
 */
import { useQuery } from '@tanstack/react-query';
import { projectsApi } from '@/services/api';
import { projectsKeys } from './useProjects';

export interface UseProjectOptions {
  /** Project ID (required) */
  projectId: string;
  /** Enable query */
  enabled?: boolean;
}

/**
 * Hook for fetching a single project
 */
export function useProject({ projectId, enabled = true }: UseProjectOptions) {
  return useQuery({
    queryKey: projectsKeys.detail(projectId),
    queryFn: () => projectsApi.get(projectId),
    enabled: enabled && !!projectId,
    staleTime: 1000 * 60 * 2, // 2 minutes
    gcTime: 1000 * 60 * 15, // 15 minutes
  });
}

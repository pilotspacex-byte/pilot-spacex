'use client';

/**
 * useProjectArtifacts — TanStack Query hook for fetching project artifacts.
 *
 * Query key factory: artifactsKeys
 * staleTime: 5 minutes (artifact lists change infrequently)
 * disabled: when workspaceId or projectId is empty
 */

import { useQuery } from '@tanstack/react-query';
import { artifactsApi } from '@/services/api/artifacts';
import type { Artifact } from '@/types/artifact';

export const ARTIFACTS_QUERY_KEY = 'artifacts';

export const artifactsKeys = {
  all: [ARTIFACTS_QUERY_KEY] as const,
  lists: () => [...artifactsKeys.all, 'list'] as const,
  list: (workspaceId: string, projectId: string) =>
    [...artifactsKeys.lists(), workspaceId, projectId] as const,
  signedUrl: (artifactId: string) => [...artifactsKeys.all, 'signed-url', artifactId] as const,
};

export function useProjectArtifacts(
  workspaceId: string,
  projectId: string
): ReturnType<typeof useQuery<Artifact[]>> {
  return useQuery({
    queryKey: artifactsKeys.list(workspaceId, projectId),
    queryFn: () => artifactsApi.list(workspaceId, projectId),
    enabled: !!workspaceId && !!projectId,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

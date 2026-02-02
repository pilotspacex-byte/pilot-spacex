/**
 * useProjectCycles - TanStack Query hook for fetching cycles by project.
 *
 * T013: Lists all cycles for a project with 60s stale time.
 */

import { useQuery } from '@tanstack/react-query';
import { cyclesApi, type CycleListResponse } from '@/services/api';

export const projectCyclesKeys = {
  all: ['cycles'] as const,
  byProject: (projectId: string) => ['cycles', projectId] as const,
};

export function useProjectCycles(workspaceId: string, projectId: string) {
  return useQuery<CycleListResponse>({
    queryKey: projectCyclesKeys.byProject(projectId),
    queryFn: () => cyclesApi.list(workspaceId, { projectId }),
    enabled: !!workspaceId && !!projectId,
    staleTime: 60_000,
  });
}

/**
 * useWorkspaceSettings - TanStack Query hook for workspace settings.
 *
 * T031: Query for workspace data, mutation for update and delete.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/services/api';
import type { Workspace } from '@/types';

export const workspaceSettingsKeys = {
  detail: (workspaceId: string) => ['workspaces', workspaceId] as const,
};

export interface UpdateWorkspaceSettingsData {
  name?: string;
  slug?: string;
  description?: string;
}

export function useWorkspaceSettings(workspaceId: string) {
  return useQuery<Workspace>({
    queryKey: workspaceSettingsKeys.detail(workspaceId),
    queryFn: () => apiClient.get<Workspace>(`/workspaces/${workspaceId}`),
    enabled: !!workspaceId,
    staleTime: 60_000,
  });
}

export function useUpdateWorkspaceSettings(workspaceId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: UpdateWorkspaceSettingsData) =>
      apiClient.patch<Workspace>(`/workspaces/${workspaceId}`, data),
    onSuccess: (updatedWorkspace) => {
      queryClient.setQueryData(workspaceSettingsKeys.detail(workspaceId), updatedWorkspace);
    },
  });
}

export function useDeleteWorkspace(workspaceId: string) {
  return useMutation({
    mutationFn: () => apiClient.delete(`/workspaces/${workspaceId}`),
  });
}

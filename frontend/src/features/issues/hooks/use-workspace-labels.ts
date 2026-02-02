/**
 * useWorkspaceLabels - TanStack Query hook for workspace labels.
 *
 * T013c: Fetches labels via apiClient directly (no dedicated API service).
 */

import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/services/api';
import type { Label } from '@/types';

export const workspaceLabelsKeys = {
  all: (workspaceId: string) => ['workspaces', workspaceId, 'labels'] as const,
};

export function useWorkspaceLabels(workspaceId: string) {
  return useQuery<Label[]>({
    queryKey: workspaceLabelsKeys.all(workspaceId),
    queryFn: () => apiClient.get<Label[]>(`/workspaces/${workspaceId}/labels`),
    enabled: !!workspaceId,
    staleTime: 60_000,
  });
}

/**
 * useWorkspaceMembers - TanStack Query hook for workspace members.
 *
 * T013b: Fetches members via apiClient directly (no dedicated API service).
 */

import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/services/api';

export interface WorkspaceMember {
  userId: string;
  email: string;
  fullName: string | null;
  avatarUrl: string | null;
  role: 'owner' | 'admin' | 'member' | 'guest';
  joinedAt: string;
}

export const workspaceMembersKeys = {
  all: (workspaceId: string) => ['workspaces', workspaceId, 'members'] as const,
};

export function useWorkspaceMembers(workspaceId: string) {
  return useQuery<WorkspaceMember[]>({
    queryKey: workspaceMembersKeys.all(workspaceId),
    queryFn: () => apiClient.get<WorkspaceMember[]>(`/workspaces/${workspaceId}/members`),
    enabled: !!workspaceId,
    staleTime: 60_000,
  });
}

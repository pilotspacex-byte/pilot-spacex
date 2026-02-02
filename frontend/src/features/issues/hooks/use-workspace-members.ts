/**
 * useWorkspaceMembers - TanStack Query hook for workspace members.
 *
 * T013b: Fetches members via apiClient directly (no dedicated API service).
 */

import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/services/api';

export interface WorkspaceMember {
  user_id: string;
  email: string;
  full_name: string | null;
  avatar_url: string | null;
  role: 'owner' | 'admin' | 'member' | 'guest';
  joined_at: string;
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

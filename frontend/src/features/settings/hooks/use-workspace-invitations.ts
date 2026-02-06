/**
 * useWorkspaceInvitations - TanStack Query hook for workspace invitations.
 *
 * T025: Fetches pending invitations and provides cancel mutation.
 * Follows use-workspace-members.ts pattern.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/services/api';

export interface WorkspaceInvitation {
  id: string;
  email: string;
  role: 'admin' | 'member' | 'guest';
  status: 'pending' | 'accepted' | 'expired' | 'cancelled';
  invitedById: string;
  invitedByName: string | null;
  createdAt: string;
  expiresAt: string;
}

export const workspaceInvitationsKeys = {
  all: (workspaceId: string) => ['workspaces', workspaceId, 'invitations'] as const,
};

export function useWorkspaceInvitations(workspaceId: string) {
  return useQuery<WorkspaceInvitation[]>({
    queryKey: workspaceInvitationsKeys.all(workspaceId),
    queryFn: () => apiClient.get<WorkspaceInvitation[]>(`/workspaces/${workspaceId}/invitations`),
    enabled: !!workspaceId,
    staleTime: 60_000,
  });
}

export function useCancelInvitation(workspaceId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (invitationId: string) =>
      apiClient.delete(`/workspaces/${workspaceId}/invitations/${invitationId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: workspaceInvitationsKeys.all(workspaceId),
      });
    },
  });
}

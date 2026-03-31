/**
 * useWorkspaceInvitations - TanStack Query hook for workspace invitations.
 *
 * T025: Fetches pending invitations and provides cancel mutation.
 * A4-E05: Returns PaginatedResponse<WorkspaceInvitation> from server-side pagination.
 * Follows use-workspace-members.ts pattern.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/services/api';

export interface WorkspaceInvitation {
  id: string;
  email: string;
  role: 'admin' | 'member' | 'guest';
  status: 'pending' | 'accepted' | 'expired' | 'cancelled' | 'revoked';
  invitedById: string;
  invitedByName: string | null;
  createdAt: string;
  expiresAt: string;
}

export interface PaginatedInvitations {
  items: WorkspaceInvitation[];
  total: number;
  hasNext: boolean;
  hasPrev: boolean;
  pageSize: number;
}

export interface InvitationPreviewResponse {
  invitation_id: string;
  status: 'pending' | 'accepted' | 'expired' | 'cancelled' | 'revoked';
  workspace_name: string;
  workspace_slug: string;
  invited_email_masked: string;
  expires_at: string;
}

export interface RequestMagicLinkResponse {
  message: string;
  expires_in_minutes: number;
}

export const workspaceInvitationsKeys = {
  all: (workspaceId: string) => ['workspaces', workspaceId, 'invitations'] as const,
};

interface UseWorkspaceInvitationsOptions {
  page?: number;
  pageSize?: number;
}

export function useWorkspaceInvitations(
  workspaceId: string,
  enabled = true,
  options?: UseWorkspaceInvitationsOptions
) {
  const page = options?.page ?? 1;
  const pageSize = options?.pageSize ?? 20;

  return useQuery<PaginatedInvitations>({
    queryKey: [...workspaceInvitationsKeys.all(workspaceId), { page, pageSize }],
    queryFn: async () => {
      const params = new URLSearchParams();
      params.set('page', String(page));
      params.set('page_size', String(pageSize));
      const response = await apiClient.get<{
        items: WorkspaceInvitation[];
        total: number;
        has_next: boolean;
        has_prev: boolean;
        page_size: number;
      }>(`/workspaces/${workspaceId}/invitations?${params.toString()}`);
      return {
        items: response.items,
        total: response.total,
        hasNext: response.has_next,
        hasPrev: response.has_prev,
        pageSize: response.page_size,
      };
    },
    enabled: !!workspaceId && enabled,
    staleTime: 60_000,
    placeholderData: (previousData) => previousData,
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

/**
 * Preview an invitation without authentication.
 * Used by the /invite page to show workspace name and detect status.
 */
export async function previewInvitation(
  invitationId: string,
): Promise<InvitationPreviewResponse> {
  return apiClient.get<InvitationPreviewResponse>(
    `/invitations/${invitationId}/preview`,
  );
}

/**
 * Request a Supabase magic link for an invitation.
 * Rate limited to 3 requests per hour per email (server-side).
 */
export async function requestMagicLink(
  invitationId: string,
  email: string,
): Promise<RequestMagicLinkResponse> {
  return apiClient.post<RequestMagicLinkResponse>(
    `/invitations/${invitationId}/request-magic-link`,
    { email },
  );
}


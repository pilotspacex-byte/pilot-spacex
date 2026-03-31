/**
 * useWorkspaceMembers - TanStack Query hook for workspace members.
 *
 * T013b: Fetches members via apiClient directly (no dedicated API service).
 * A4-E05: Returns PaginatedResponse<WorkspaceMember> from server-side pagination endpoint.
 */

import { apiClient } from '@/services/api';
import { useQuery } from '@tanstack/react-query';

export interface WorkspaceMember {
  userId: string;
  email: string;
  fullName: string | null;
  avatarUrl: string | null;
  role: 'owner' | 'admin' | 'member' | 'guest';
  joinedAt: string;
  /** Hours available per week for capacity planning (0-168, T-246) */
  weeklyAvailableHours: number;
  /** Custom role assigned by RBAC (01-03). When set, overrides built-in role display. */
  custom_role?: { id: string; name: string } | null;
  /** Whether the member is active. Deprovisioned (SCIM) members have is_active=false. */
  is_active?: boolean;
  /** Project chips — projects this member is assigned to (FR-02). */
  projects?: Array<{ id: string; name: string; identifier: string }>;
}

export interface PaginatedWorkspaceMembers {
  items: WorkspaceMember[];
  total: number;
  hasNext: boolean;
  hasPrev: boolean;
  pageSize: number;
}

export const workspaceMembersKeys = {
  all: (workspaceId: string) => ['workspaces', workspaceId, 'members'] as const,
  filtered: (workspaceId: string, projectId: string | null) =>
    ['workspaces', workspaceId, 'members', { projectId }] as const,
};

interface UseWorkspaceMembersOptions {
  projectId?: string | null;
  search?: string;
  role?: string;
  page?: number;
  pageSize?: number;
}

export function useWorkspaceMembers(workspaceId: string, options?: UseWorkspaceMembersOptions) {
  const projectId = options?.projectId ?? null;
  const search = options?.search ?? '';
  const role = options?.role ?? '';
  const page = options?.page ?? 1;
  const pageSize = options?.pageSize ?? 20;

  return useQuery<PaginatedWorkspaceMembers>({
    queryKey: [...workspaceMembersKeys.all(workspaceId), { projectId, search, role, page, pageSize }],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (projectId) params.set('project_id', projectId);
      if (search) params.set('search', search);
      if (role && role !== 'all') params.set('role', role);
      params.set('page', String(page));
      params.set('page_size', String(pageSize));
      const qs = `?${params.toString()}`;
      const response = await apiClient.get<{
        items: WorkspaceMember[];
        total: number;
        has_next: boolean;
        has_prev: boolean;
        page_size: number;
      }>(`/workspaces/${workspaceId}/members${qs}`);
      return {
        items: response.items.map((m) => ({
          ...m,
          role: m.role.toLowerCase() as WorkspaceMember['role'],
        })),
        total: response.total,
        hasNext: response.has_next,
        hasPrev: response.has_prev,
        pageSize: response.page_size,
      };
    },
    enabled: !!workspaceId,
    staleTime: 60_000,
    placeholderData: (previousData) => previousData,
  });
}

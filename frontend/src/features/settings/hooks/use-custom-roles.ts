/**
 * useCustomRoles - TanStack Query hooks for custom RBAC role management.
 *
 * AUTH-04, AUTH-05: Custom roles list, create, update, delete, assign operations.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient, ApiError } from '@/services/api';

// ---- Types ----

export interface CustomRole {
  id: string;
  workspace_id: string;
  name: string;
  description: string | null;
  permissions: string[];
  created_at: string;
  updated_at: string;
}

export interface CreateRoleInput {
  name: string;
  description?: string;
  permissions: string[];
}

export interface UpdateRoleInput {
  name?: string;
  description?: string;
  permissions?: string[];
}

export interface AssignRoleInput {
  member_id: string;
  role_id: string | null;
}

// ---- Query Keys ----

export const customRolesKeys = {
  list: (workspaceSlug: string) => ['custom-roles', workspaceSlug] as const,
  detail: (workspaceSlug: string, roleId: string) =>
    ['custom-roles', workspaceSlug, roleId] as const,
};

// ---- Hooks ----

export function useCustomRoles(workspaceSlug: string) {
  return useQuery<CustomRole[]>({
    queryKey: customRolesKeys.list(workspaceSlug),
    queryFn: () => apiClient.get<CustomRole[]>(`/workspaces/${workspaceSlug}/roles`),
    enabled: !!workspaceSlug,
    staleTime: 30_000,
  });
}

export function useCustomRole(workspaceSlug: string, roleId: string) {
  return useQuery<CustomRole>({
    queryKey: customRolesKeys.detail(workspaceSlug, roleId),
    queryFn: () => apiClient.get<CustomRole>(`/workspaces/${workspaceSlug}/roles/${roleId}`),
    enabled: !!workspaceSlug && !!roleId,
    staleTime: 30_000,
  });
}

export function useCreateRole(workspaceSlug: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreateRoleInput) =>
      apiClient.post<CustomRole>(`/workspaces/${workspaceSlug}/roles`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: customRolesKeys.list(workspaceSlug) });
    },
    // 409 Conflict is handled by callers via error.status check
    onError: (error: unknown) => {
      if (error instanceof ApiError && error.status === 409) {
        // Bubble up — caller displays inline error
        return;
      }
    },
  });
}

export function useUpdateRole(workspaceSlug: string, roleId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: UpdateRoleInput) =>
      apiClient.patch<CustomRole>(`/workspaces/${workspaceSlug}/roles/${roleId}`, data),
    onSuccess: (updated) => {
      queryClient.setQueryData(customRolesKeys.detail(workspaceSlug, roleId), updated);
      queryClient.invalidateQueries({ queryKey: customRolesKeys.list(workspaceSlug) });
    },
    onError: (error: unknown) => {
      if (error instanceof ApiError && error.status === 409) {
        return;
      }
    },
  });
}

export function useDeleteRole(workspaceSlug: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (roleId: string) =>
      apiClient.delete(`/workspaces/${workspaceSlug}/roles/${roleId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: customRolesKeys.list(workspaceSlug) });
    },
  });
}

export function useAssignRole(workspaceSlug: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ member_id, role_id }: AssignRoleInput) =>
      apiClient.patch(`/workspaces/${workspaceSlug}/members/${member_id}`, {
        custom_role_id: role_id,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['members', workspaceSlug] });
    },
  });
}

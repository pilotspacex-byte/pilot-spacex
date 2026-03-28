/**
 * Project Members API client — RBAC project membership management.
 * Source: specs/026-project-rbac, FR-01..FR-07
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from './client';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type ProjectAssignmentAction = 'add' | 'remove';

export interface ProjectMember {
  id: string;
  projectId: string;
  userId: string;
  email: string;
  fullName: string | null;
  avatarUrl: string | null;
  isActive: boolean;
  assignedAt: string;
  assignedBy: string | null;
}

export interface ProjectMemberListResponse {
  items: ProjectMember[];
  total: number;
  nextCursor: string | null;
  hasNext: boolean;
}

export interface AddMemberRequest {
  userId: string;
}

export interface BulkAssignmentActionItem {
  projectId: string;
  action: ProjectAssignmentAction;
}

export interface BulkAssignmentRequest {
  workspaceRole?: string;
  projectAssignments: BulkAssignmentActionItem[];
}

export interface BulkAssignmentWarning {
  code: string;
  message: string;
}

export interface BulkAssignmentResponse {
  userId: string;
  workspaceRole: string | null;
  projectAssignmentsUpdated: number;
  warnings: BulkAssignmentWarning[];
}

export interface ProjectSummaryChip {
  id: string;
  name: string;
  identifier: string;
  isArchived: boolean;
}

export interface MyProjectCard {
  projectId: string;
  name: string;
  identifier: string;
  description: string | null;
  icon: string | null;
  isArchived: boolean;
  issueCount: number;
  memberCount: number;
  assignedAt: string;
}

export interface MyProjectsResponse {
  items: MyProjectCard[];
  total: number;
}

export interface ArchiveProjectRequest {
  isArchived: boolean;
}

// ---------------------------------------------------------------------------
// API client object
// ---------------------------------------------------------------------------

export const projectMembersApi = {
  /**
   * GET /workspaces/{wid}/projects/{pid}/members
   * List members of a project with optional search and pagination.
   */
  listProjectMembers(
    workspaceId: string,
    projectId: string,
    params?: { search?: string; cursor?: string; pageSize?: number }
  ): Promise<ProjectMemberListResponse> {
    return apiClient.get<ProjectMemberListResponse>(
      `/workspaces/${workspaceId}/projects/${projectId}/members`,
      { params }
    );
  },

  /**
   * POST /workspaces/{wid}/projects/{pid}/members
   * Add a workspace member to a project.
   */
  addProjectMember(
    workspaceId: string,
    projectId: string,
    payload: AddMemberRequest
  ): Promise<ProjectMember> {
    return apiClient.post<ProjectMember>(
      `/workspaces/${workspaceId}/projects/${projectId}/members`,
      payload
    );
  },

  /**
   * DELETE /workspaces/{wid}/projects/{pid}/members/{uid}
   * Remove a member from a project.
   */
  removeProjectMember(workspaceId: string, projectId: string, userId: string): Promise<void> {
    return apiClient.delete(`/workspaces/${workspaceId}/projects/${projectId}/members/${userId}`);
  },

  /**
   * PATCH /workspaces/{wid}/members/{uid}/assignments
   * Bulk update workspace role and/or project assignments for a member.
   */
  bulkUpdateAssignments(
    workspaceId: string,
    userId: string,
    payload: BulkAssignmentRequest
  ): Promise<BulkAssignmentResponse> {
    return apiClient.patch<BulkAssignmentResponse>(
      `/workspaces/${workspaceId}/members/${userId}/assignments`,
      {
        workspace_role: payload.workspaceRole,
        project_assignments: payload.projectAssignments.map((a) => ({
          project_id: a.projectId,
          action: a.action,
        })),
      }
    );
  },

  /**
   * GET /workspaces/{wid}/my-projects
   * Get projects visible to the current user (assigned or admin-all).
   */
  listMyProjects(workspaceId: string): Promise<MyProjectsResponse> {
    return apiClient.get<MyProjectsResponse>(`/workspaces/${workspaceId}/my-projects`);
  },

  /**
   * PATCH /workspaces/{wid}/members/me/last-active-project
   * Update the current user's last active project.
   */
  updateLastActiveProject(workspaceId: string, projectId: string): Promise<void> {
    return apiClient.patch(`/workspaces/${workspaceId}/members/me/last-active-project`, {
      project_id: projectId,
    });
  },

  /**
   * PATCH /workspaces/{wid}/projects/{pid}/archive
   * Archive or unarchive a project (admin/owner only).
   */
  archiveProject(
    workspaceId: string,
    projectId: string,
    payload: ArchiveProjectRequest
  ): Promise<void> {
    return apiClient.patch(`/workspaces/${workspaceId}/projects/${projectId}/archive`, {
      is_archived: payload.isArchived,
    });
  },

  /**
   * DELETE /workspaces/{wid}/members/invitations/{invId}
   * Rescind a pending invitation (admin/owner only).
   */
  rescindInvitation(workspaceId: string, invitationId: string): Promise<void> {
    return apiClient.delete(`/workspaces/${workspaceId}/members/invitations/${invitationId}`);
  },
};

// ---------------------------------------------------------------------------
// TanStack Query Keys
// ---------------------------------------------------------------------------

export const projectMemberKeys = {
  all: ['project-members'] as const,
  list: (workspaceId: string, projectId: string) =>
    [...projectMemberKeys.all, workspaceId, projectId] as const,
  myProjects: (workspaceId: string) => ['my-projects', workspaceId] as const,
};

// ---------------------------------------------------------------------------
// TanStack Query Hooks
// ---------------------------------------------------------------------------

export function useProjectMembers(
  workspaceId: string,
  projectId: string,
  params?: { search?: string; cursor?: string; pageSize?: number }
) {
  return useQuery({
    queryKey: [...projectMemberKeys.list(workspaceId, projectId), params],
    queryFn: () => projectMembersApi.listProjectMembers(workspaceId, projectId, params),
    enabled: !!workspaceId && !!projectId,
  });
}

export function useMyProjects(workspaceId: string) {
  return useQuery({
    queryKey: projectMemberKeys.myProjects(workspaceId),
    queryFn: () => projectMembersApi.listMyProjects(workspaceId),
    enabled: !!workspaceId,
  });
}

export function useAddProjectMember(workspaceId: string, projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: AddMemberRequest) =>
      projectMembersApi.addProjectMember(workspaceId, projectId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: projectMemberKeys.list(workspaceId, projectId),
      });
    },
  });
}

export function useRemoveProjectMember(workspaceId: string, projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (userId: string) =>
      projectMembersApi.removeProjectMember(workspaceId, projectId, userId),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: projectMemberKeys.list(workspaceId, projectId),
        }),
        queryClient.invalidateQueries({
          queryKey: ['workspaces', workspaceId, 'members'],
        }),
      ]);
    },
  });
}

export function useBulkUpdateAssignments(workspaceId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ userId, payload }: { userId: string; payload: BulkAssignmentRequest }) =>
      projectMembersApi.bulkUpdateAssignments(workspaceId, userId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: projectMemberKeys.all });
      queryClient.invalidateQueries({ queryKey: projectMemberKeys.myProjects(workspaceId) });
      queryClient.invalidateQueries({ queryKey: ['workspace-members', workspaceId] });
    },
  });
}

export function useRescindInvitation(workspaceId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (invitationId: string) =>
      projectMembersApi.rescindInvitation(workspaceId, invitationId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workspace-invitations', workspaceId] });
    },
  });
}

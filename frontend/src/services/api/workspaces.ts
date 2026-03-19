import { apiClient } from './client';
import type {
  Workspace,
  WorkspaceRole,
  WorkspaceMember,
  CreateWorkspaceData,
  UpdateWorkspaceData,
  InviteMemberData,
} from '@/types';

export type {
  WorkspaceRole,
  WorkspaceMember,
  CreateWorkspaceData,
  UpdateWorkspaceData,
  InviteMemberData,
};

interface WorkspaceResponse {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  ownerId: string;
  memberCount: number;
  projectCount: number;
  createdAt: string;
  updatedAt: string;
}

/** Flat response from GET /workspaces/{id}/members — camelCase because backend uses BaseSchema. */
interface WorkspaceMemberResponse {
  userId: string;
  email: string;
  fullName: string | null;
  avatarUrl: string | null;
  role: WorkspaceRole;
  joinedAt: string;
  weeklyAvailableHours?: number;
}

interface PaginatedWorkspaceResponse {
  items: WorkspaceResponse[];
  total: number;
  hasNext: boolean;
  hasPrev: boolean;
  nextCursor: string | null;
  prevCursor: string | null;
  pageSize: number;
}

/**
 * Transform API response to frontend Workspace type.
 */
function transformWorkspace(response: WorkspaceResponse): Workspace {
  return {
    id: response.id,
    name: response.name,
    slug: response.slug,
    description: response.description ?? undefined,
    ownerId: response.ownerId,
    memberCount: response.memberCount,
    memberIds: [],
    createdAt: response.createdAt,
    updatedAt: response.updatedAt,
  };
}

/**
 * Transform API response to frontend WorkspaceMember type.
 */
function transformWorkspaceMember(response: WorkspaceMemberResponse): WorkspaceMember {
  return {
    id: response.userId,
    userId: response.userId,
    workspaceId: '',
    role: response.role.toLowerCase() as WorkspaceRole,
    joinedAt: response.joinedAt,
    weeklyAvailableHours: response.weeklyAvailableHours ?? 40,
    user: {
      id: response.userId,
      email: response.email,
      name: response.fullName ?? 'Unknown',
      avatarUrl: response.avatarUrl ?? undefined,
    },
  };
}

export const workspacesApi = {
  /**
   * List workspaces the current user is a member of.
   */
  async list(): Promise<{ items: Workspace[] }> {
    const response = await apiClient.get<PaginatedWorkspaceResponse>('/workspaces');
    return {
      items: response.items.map(transformWorkspace),
    };
  },

  /**
   * Get a workspace by ID or slug.
   */
  async get(workspaceIdOrSlug: string): Promise<Workspace> {
    const response = await apiClient.get<WorkspaceResponse>(`/workspaces/${workspaceIdOrSlug}`);
    return transformWorkspace(response);
  },

  /**
   * Create a new workspace.
   */
  async create(data: CreateWorkspaceData): Promise<Workspace> {
    const response = await apiClient.post<WorkspaceResponse>('/workspaces', data);
    return transformWorkspace(response);
  },

  /**
   * Update a workspace.
   */
  async update(workspaceIdOrSlug: string, data: UpdateWorkspaceData): Promise<Workspace> {
    const response = await apiClient.patch<WorkspaceResponse>(
      `/workspaces/${workspaceIdOrSlug}`,
      data
    );
    return transformWorkspace(response);
  },

  /**
   * Delete a workspace.
   */
  async delete(workspaceIdOrSlug: string): Promise<void> {
    await apiClient.delete<void>(`/workspaces/${workspaceIdOrSlug}`);
  },

  /**
   * Get workspace members.
   */
  async getMembers(workspaceId: string): Promise<WorkspaceMember[]> {
    const response = await apiClient.get<WorkspaceMemberResponse[]>(
      `/workspaces/${workspaceId}/members`
    );
    return response.map(transformWorkspaceMember);
  },

  /**
   * Invite a new member to the workspace.
   */
  async inviteMember(workspaceId: string, data: InviteMemberData): Promise<WorkspaceMember> {
    const response = await apiClient.post<WorkspaceMemberResponse>(
      `/workspaces/${workspaceId}/members`,
      { ...data, role: data.role.toUpperCase() }
    );
    return transformWorkspaceMember(response);
  },

  /**
   * Remove a member from the workspace.
   */
  async removeMember(workspaceId: string, memberId: string): Promise<void> {
    await apiClient.delete<void>(`/workspaces/${workspaceId}/members/${memberId}`);
  },

  /**
   * Update a member's role.
   */
  async updateMemberRole(
    workspaceId: string,
    memberId: string,
    role: WorkspaceRole
  ): Promise<WorkspaceMember> {
    const response = await apiClient.patch<WorkspaceMemberResponse>(
      `/workspaces/${workspaceId}/members/${memberId}`,
      { role: role.toUpperCase() }
    );
    return transformWorkspaceMember(response);
  },

  /**
   * Update a member's weekly available hours (T-246).
   * Any member can update their own; admins can update any.
   */
  async updateMemberAvailability(
    workspaceId: string,
    userId: string,
    weeklyAvailableHours: number
  ): Promise<void> {
    await apiClient.patch<WorkspaceMemberResponse>(
      `/workspaces/${workspaceId}/members/${userId}/availability`,
      { weeklyAvailableHours }
    );
  },
};

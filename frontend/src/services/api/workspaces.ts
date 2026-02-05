import { apiClient } from './client';
import type { Workspace, User } from '@/types';

export type WorkspaceRole = 'owner' | 'admin' | 'member' | 'guest';

export interface CreateWorkspaceData {
  name: string;
  slug?: string;
  description?: string;
}

export interface UpdateWorkspaceData {
  name?: string;
  slug?: string;
  description?: string;
}

export interface InviteMemberData {
  email: string;
  role: WorkspaceRole;
}

export interface WorkspaceMember {
  id: string;
  userId: string;
  user: User;
  workspaceId: string;
  role: WorkspaceRole;
  joinedAt: string;
}

interface WorkspaceResponse {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  owner_id: string;
  member_count: number;
  project_count: number;
  created_at: string;
  updated_at: string;
}

interface WorkspaceMemberResponse {
  user_id: string;
  workspace_id: string;
  role: WorkspaceRole;
  created_at: string;
  user?: {
    id: string;
    email: string;
    name: string | null;
    avatar_url: string | null;
  };
}

interface PaginatedWorkspaceResponse {
  items: WorkspaceResponse[];
  total: number;
  has_next: boolean;
  has_prev: boolean;
  next_cursor: string | null;
  prev_cursor: string | null;
  page_size: number;
}

/**
 * Transform API response to frontend Workspace type.
 */
function transformWorkspace(response: WorkspaceResponse): Workspace {
  return {
    id: response.id,
    name: response.name,
    slug: response.slug,
    ownerId: response.owner_id,
    memberIds: [],
    createdAt: response.created_at,
    updatedAt: response.updated_at,
  };
}

/**
 * Transform API response to frontend WorkspaceMember type.
 */
function transformWorkspaceMember(response: WorkspaceMemberResponse): WorkspaceMember {
  return {
    id: `${response.workspace_id}-${response.user_id}`,
    userId: response.user_id,
    workspaceId: response.workspace_id,
    role: response.role,
    joinedAt: response.created_at,
    user: {
      id: response.user?.id ?? response.user_id,
      email: response.user?.email ?? '',
      name: response.user?.name ?? 'Unknown',
      createdAt: response.created_at,
      updatedAt: response.created_at,
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
      data
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
      { role }
    );
    return transformWorkspaceMember(response);
  },
};

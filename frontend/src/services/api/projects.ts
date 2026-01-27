import { apiClient, type PaginatedResponse } from './client';
import type { Project } from '@/types';

interface CreateProjectData {
  name: string;
  description?: string;
  leadId?: string;
}

interface UpdateProjectData {
  name?: string;
  description?: string;
  leadId?: string;
}

export const projectsApi = {
  list(workspaceId: string, _page = 1, pageSize = 50): Promise<PaginatedResponse<Project>> {
    // Backend uses cursor-based pagination with workspace_id as query param
    return apiClient.get<PaginatedResponse<Project>>('/projects', {
      params: {
        workspace_id: workspaceId,
        page_size: String(pageSize),
      },
    });
  },

  get(projectId: string): Promise<Project> {
    return apiClient.get<Project>(`/projects/${projectId}`);
  },

  create(workspaceId: string, data: CreateProjectData): Promise<Project> {
    return apiClient.post<Project>('/projects', {
      ...data,
      workspace_id: workspaceId,
    });
  },

  update(projectId: string, data: UpdateProjectData): Promise<Project> {
    return apiClient.patch<Project>(`/projects/${projectId}`, data);
  },

  delete(projectId: string): Promise<void> {
    return apiClient.delete<void>(`/projects/${projectId}`);
  },

  // Note: addMember, removeMember, and label endpoints are not yet implemented in backend
};

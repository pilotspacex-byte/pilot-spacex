import { apiClient, type PaginatedResponse } from './client';
import type { Project, Label } from '@/types';

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
  list(workspaceId: string, page = 1, pageSize = 50): Promise<PaginatedResponse<Project>> {
    return apiClient.get<PaginatedResponse<Project>>(`/workspaces/${workspaceId}/projects`, {
      params: { page: String(page), pageSize: String(pageSize) },
    });
  },

  get(workspaceId: string, projectId: string): Promise<Project> {
    return apiClient.get<Project>(`/workspaces/${workspaceId}/projects/${projectId}`);
  },

  getBySlug(workspaceId: string, slug: string): Promise<Project> {
    return apiClient.get<Project>(`/workspaces/${workspaceId}/projects/by-slug/${slug}`);
  },

  create(workspaceId: string, data: CreateProjectData): Promise<Project> {
    return apiClient.post<Project>(`/workspaces/${workspaceId}/projects`, data);
  },

  update(workspaceId: string, projectId: string, data: UpdateProjectData): Promise<Project> {
    return apiClient.patch<Project>(`/workspaces/${workspaceId}/projects/${projectId}`, data);
  },

  delete(workspaceId: string, projectId: string): Promise<void> {
    return apiClient.delete<void>(`/workspaces/${workspaceId}/projects/${projectId}`);
  },

  addMember(workspaceId: string, projectId: string, userId: string): Promise<Project> {
    return apiClient.post<Project>(`/workspaces/${workspaceId}/projects/${projectId}/members`, {
      userId,
    });
  },

  removeMember(workspaceId: string, projectId: string, userId: string): Promise<Project> {
    return apiClient.delete<Project>(
      `/workspaces/${workspaceId}/projects/${projectId}/members/${userId}`
    );
  },

  // Labels
  getLabels(workspaceId: string, projectId: string): Promise<Label[]> {
    return apiClient.get<Label[]>(`/workspaces/${workspaceId}/projects/${projectId}/labels`);
  },

  createLabel(
    workspaceId: string,
    projectId: string,
    data: { name: string; color: string }
  ): Promise<Label> {
    return apiClient.post<Label>(`/workspaces/${workspaceId}/projects/${projectId}/labels`, data);
  },

  updateLabel(
    workspaceId: string,
    projectId: string,
    labelId: string,
    data: { name?: string; color?: string }
  ): Promise<Label> {
    return apiClient.patch<Label>(
      `/workspaces/${workspaceId}/projects/${projectId}/labels/${labelId}`,
      data
    );
  },

  deleteLabel(workspaceId: string, projectId: string, labelId: string): Promise<void> {
    return apiClient.delete<void>(
      `/workspaces/${workspaceId}/projects/${projectId}/labels/${labelId}`
    );
  },
};

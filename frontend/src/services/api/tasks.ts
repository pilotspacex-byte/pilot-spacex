import { apiClient } from './client';
import type {
  Task,
  TaskCreate,
  TaskUpdate,
  TaskListResponse,
  DecomposeResponse,
  ContextExportResponse,
  TaskStatus,
} from '@/types';

export const tasksApi = {
  list(workspaceId: string, issueId: string): Promise<TaskListResponse> {
    return apiClient.get<TaskListResponse>(`/workspaces/${workspaceId}/issues/${issueId}/tasks`);
  },

  create(workspaceId: string, issueId: string, data: TaskCreate): Promise<Task> {
    return apiClient.post<Task>(`/workspaces/${workspaceId}/issues/${issueId}/tasks`, data);
  },

  update(workspaceId: string, taskId: string, data: TaskUpdate): Promise<Task> {
    return apiClient.patch<Task>(`/workspaces/${workspaceId}/tasks/${taskId}`, data);
  },

  delete(workspaceId: string, taskId: string): Promise<void> {
    return apiClient.delete(`/workspaces/${workspaceId}/tasks/${taskId}`);
  },

  updateStatus(workspaceId: string, taskId: string, status: TaskStatus): Promise<Task> {
    return apiClient.patch<Task>(`/workspaces/${workspaceId}/tasks/${taskId}/status`, {
      status,
    });
  },

  reorder(workspaceId: string, issueId: string, taskIds: string[]): Promise<TaskListResponse> {
    return apiClient.put<TaskListResponse>(
      `/workspaces/${workspaceId}/issues/${issueId}/tasks/reorder`,
      { taskIds }
    );
  },

  exportContext(
    workspaceId: string,
    issueId: string,
    format: 'markdown' | 'claude_code' | 'task_list' = 'markdown'
  ): Promise<ContextExportResponse> {
    return apiClient.get<ContextExportResponse>(
      `/workspaces/${workspaceId}/issues/${issueId}/context/export`,
      { params: { format } }
    );
  },

  decompose(workspaceId: string, issueId: string): Promise<DecomposeResponse> {
    return apiClient.post<DecomposeResponse>(
      `/workspaces/${workspaceId}/issues/${issueId}/tasks/decompose`
    );
  },
};

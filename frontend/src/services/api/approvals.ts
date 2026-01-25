import { apiClient, type PaginatedResponse } from './client';
import type {
  PendingApproval,
  CreateApprovalRequest,
  ApprovalResolution,
  ApprovalStatus,
} from '@/types';

/**
 * Approvals API service for human-in-the-loop actions per DD-003.
 */
export const approvalsApi = {
  /**
   * List pending approvals for a workspace.
   */
  listPending: (
    workspaceId: string,
    options?: { limit?: number; offset?: number }
  ): Promise<PaginatedResponse<PendingApproval>> =>
    apiClient.get<PaginatedResponse<PendingApproval>>(
      `/workspaces/${workspaceId}/approvals/pending`,
      { params: options }
    ),

  /**
   * List all approvals (including resolved) for a workspace.
   */
  list: (
    workspaceId: string,
    options?: {
      status?: ApprovalStatus;
      limit?: number;
      offset?: number;
    }
  ): Promise<PaginatedResponse<PendingApproval>> =>
    apiClient.get<PaginatedResponse<PendingApproval>>(`/workspaces/${workspaceId}/approvals`, {
      params: options,
    }),

  /**
   * Get a specific approval by ID.
   */
  get: (workspaceId: string, approvalId: string): Promise<PendingApproval> =>
    apiClient.get<PendingApproval>(`/workspaces/${workspaceId}/approvals/${approvalId}`),

  /**
   * Create a new approval request.
   */
  create: (workspaceId: string, data: CreateApprovalRequest): Promise<PendingApproval> =>
    apiClient.post<PendingApproval>(`/workspaces/${workspaceId}/approvals`, data),

  /**
   * Approve a pending approval and execute the action.
   */
  approve: (workspaceId: string, approvalId: string, note?: string): Promise<ApprovalResolution> =>
    apiClient.post<ApprovalResolution>(
      `/workspaces/${workspaceId}/approvals/${approvalId}/approve`,
      { note }
    ),

  /**
   * Reject a pending approval.
   */
  reject: (workspaceId: string, approvalId: string, reason?: string): Promise<ApprovalResolution> =>
    apiClient.post<ApprovalResolution>(
      `/workspaces/${workspaceId}/approvals/${approvalId}/reject`,
      { reason }
    ),

  /**
   * Get count of pending approvals for badge display.
   */
  getPendingCount: (workspaceId: string): Promise<{ count: number }> =>
    apiClient.get<{ count: number }>(`/workspaces/${workspaceId}/approvals/pending/count`),
};

import { apiClient } from './client';
import type {
  PendingApproval,
  CreateApprovalRequest,
  ApprovalResolution,
  ApprovalStatus,
} from '@/types';

/** Raw backend ApprovalRequest list response. */
interface BackendApprovalListResult {
  requests: Array<{
    id: string;
    agent_name: string;
    action_type: string;
    status: 'pending' | 'approved' | 'rejected' | 'expired';
    created_at: string;
    expires_at: string;
    requested_by: string;
    context_preview: string;
    payload?: Record<string, unknown>;
  }>;
  pending_count: number;
  total: number;
}

/** Synthesise a PendingApproval-compatible object from the backend flat format. */
function toApproval(r: BackendApprovalListResult['requests'][number]): PendingApproval {
  return {
    id: r.id,
    workspaceId: '',
    requestedById: r.requested_by,
    actionType: r.action_type as PendingApproval['actionType'],
    actionDescription: r.context_preview,
    consequences: '',
    urgency: 'medium' as PendingApproval['urgency'],
    status: r.status as PendingApproval['status'],
    metadata: r.payload,
    affectedEntityIds: [],
    affectedEntityType: 'issue' as PendingApproval['affectedEntityType'],
    expiresAt: r.expires_at,
    createdAt: r.created_at,
  };
}

/** List response wrapper matching frontend pagination conventions. */
export interface ApprovalListResult {
  items: PendingApproval[];
  total: number;
  pending_count: number;
}

/**
 * Approvals API service for human-in-the-loop actions per DD-003.
 * Calls /ai/approvals endpoints (correct backend routes).
 */
export const approvalsApi = {
  /** List pending approvals. */
  listPending: (
    _workspaceId: string,
    options?: { limit?: number; offset?: number }
  ): Promise<ApprovalListResult> =>
    apiClient
      .get<BackendApprovalListResult>('/ai/approvals', {
        params: { status: 'pending', ...options },
      })
      .then((r) => ({
        items: r.requests.map(toApproval),
        total: r.total,
        pending_count: r.pending_count,
      })),

  /** List all approvals with optional status filter. */
  list: (
    _workspaceId: string,
    options?: { status?: ApprovalStatus; limit?: number; offset?: number }
  ): Promise<ApprovalListResult> =>
    apiClient.get<BackendApprovalListResult>('/ai/approvals', { params: options }).then((r) => ({
      items: r.requests.map(toApproval),
      total: r.total,
      pending_count: r.pending_count,
    })),

  /** Get a specific approval by ID. */
  get: (_workspaceId: string, approvalId: string): Promise<PendingApproval> =>
    apiClient
      .get<BackendApprovalListResult['requests'][number]>(`/ai/approvals/${approvalId}`)
      .then(toApproval),

  /** Create approval — not supported by backend; reserved for future use. */
  create: (_workspaceId: string, _data: CreateApprovalRequest): Promise<PendingApproval> =>
    Promise.reject(new Error('create approval is not supported by the backend API')),

  /** Approve a pending approval. */
  approve: (_workspaceId: string, approvalId: string, note?: string): Promise<ApprovalResolution> =>
    apiClient
      .post<{
        approved: boolean;
        action_result: Record<string, unknown> | null;
        action_error: string | null;
      }>(`/ai/approvals/${approvalId}/resolve`, { approved: true, note })
      .then(
        (r) =>
          ({
            approval: { id: approvalId, status: 'approved' } as unknown as PendingApproval,
            actionExecuted: r.approved && r.action_error === null,
          }) as ApprovalResolution
      ),

  /** Reject a pending approval. */
  reject: (
    _workspaceId: string,
    approvalId: string,
    reason?: string
  ): Promise<ApprovalResolution> =>
    apiClient
      .post<{
        approved: boolean;
        action_result: Record<string, unknown> | null;
        action_error: string | null;
      }>(`/ai/approvals/${approvalId}/resolve`, { approved: false, note: reason })
      .then(
        () =>
          ({
            approval: { id: approvalId, status: 'rejected' } as unknown as PendingApproval,
            actionExecuted: false,
          }) as ApprovalResolution
      ),

  /** Get count of pending approvals for badge display. */
  getPendingCount: (_workspaceId: string): Promise<{ count: number }> =>
    apiClient
      .get<BackendApprovalListResult>('/ai/approvals', { params: { status: 'pending' } })
      .then((r) => ({ count: r.pending_count })),
};

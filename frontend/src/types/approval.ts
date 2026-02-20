import type { User } from './workspace';

// ============================================================================
// Approval Types (Human-in-the-Loop per DD-003)
// ============================================================================

/**
 * Status of a pending approval.
 */
export type ApprovalStatus = 'pending' | 'approved' | 'rejected' | 'expired';

/**
 * Action types that require human approval per DD-003.
 */
export type ApprovalActionType =
  | 'issue_delete_bulk'
  | 'issue_merge_duplicate'
  | 'ai_bulk_update'
  | 'ai_create_sub_issues'
  | 'ai_archive_issues'
  | 'cycle_delete'
  | 'module_delete';

/**
 * Urgency level for approval requests.
 */
export type ApprovalUrgency = 'low' | 'medium' | 'high' | 'critical';

/**
 * Pending approval request requiring human confirmation.
 */
export interface PendingApproval {
  id: string;
  workspaceId: string;
  requestedById: string;
  requestedBy?: User;
  actionType: ApprovalActionType;
  actionDescription: string;
  consequences: string;
  urgency: ApprovalUrgency;
  status: ApprovalStatus;
  metadata?: Record<string, unknown>;
  affectedEntityIds: string[];
  affectedEntityType: 'issue' | 'cycle' | 'module' | 'note';
  expiresAt: string;
  createdAt: string;
  resolvedAt?: string;
  resolvedById?: string;
  resolvedBy?: User;
  resolutionNote?: string;
}

/**
 * Request payload for creating an approval.
 */
export interface CreateApprovalRequest {
  actionType: ApprovalActionType;
  actionDescription: string;
  consequences: string;
  urgency?: ApprovalUrgency;
  metadata?: Record<string, unknown>;
  affectedEntityIds: string[];
  affectedEntityType: 'issue' | 'cycle' | 'module' | 'note';
}

/**
 * Response after resolving an approval.
 */
export interface ApprovalResolution {
  approval: PendingApproval;
  actionExecuted: boolean;
  executionResult?: unknown;
  error?: string;
}

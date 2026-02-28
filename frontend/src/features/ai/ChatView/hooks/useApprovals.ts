/**
 * useApprovals - Derives inline and modal approval lists from store state.
 *
 * Must be called from an observer() component so MobX auto-tracks the
 * store.pendingApprovals ObservableArray. Do NOT wrap in useMemo — the
 * array reference never changes on push, which would cache a stale result.
 */
import type { PilotSpaceStore } from '@/stores/ai/PilotSpaceStore';
import type { ApprovalStore } from '@/stores/ai/ApprovalStore';
import { isDestructiveAction } from '../utils';
import type { ApprovalRequest } from '../types';

export function useApprovals(
  store: PilotSpaceStore,
  approvalStore?: ApprovalStore
): { inlineApprovals: ApprovalRequest[]; modalApprovals: ApprovalRequest[] } {
  // SSE-triggered approvals (current session, in-memory).
  const sseApprovals: ApprovalRequest[] = store.pendingApprovals.map((req) => ({
    id: req.requestId,
    agentName: 'PilotSpace Agent',
    actionType: req.actionType,
    status: 'pending' as const,
    contextPreview: req.description,
    payload: req.proposedContent as Record<string, unknown> | undefined,
    createdAt: req.createdAt,
    expiresAt: req.expiresAt,
    reasoning: req.consequences,
  }));

  // Backend-polled approvals (all sessions); de-dup against SSE list by id.
  const polledApprovals = (approvalStore?.pendingRequests ?? []).filter(
    (r) => !sseApprovals.some((s) => s.id === r.id)
  );

  const chatViewApprovals = [...sseApprovals, ...polledApprovals];

  const inlineApprovals: ApprovalRequest[] = [];
  const modalApprovals: ApprovalRequest[] = [];
  for (const req of chatViewApprovals) {
    if (isDestructiveAction(req.actionType)) {
      modalApprovals.push(req);
    } else {
      inlineApprovals.push(req);
    }
  }

  return { inlineApprovals, modalApprovals };
}

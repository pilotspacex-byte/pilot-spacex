/**
 * Adapters — normalize the two raw approval shapes into the `NormalizedProposal`
 * model consumed by `EditProposalCard`.
 *
 * Keeping adapters in a dedicated module (not inside the card) preserves
 * purity of the render component and allows other surfaces (future analytics,
 * keyboard-shortcut dispatchers) to reuse the same normalisation.
 */

import type { ApprovalRequest } from '@/features/ai/ChatView/types';
import type { PendingApproval } from '@/types';
import type { NormalizedProposal } from './EditProposalCard';

/**
 * Convert a chat-side `ApprovalRequest` → `NormalizedProposal`.
 */
export function proposalFromApprovalRequest(req: ApprovalRequest): NormalizedProposal {
  const payload = req.payload;
  const before =
    payload && typeof payload.before === 'string' ? (payload.before as string) : undefined;
  const after =
    payload && typeof payload.after === 'string' ? (payload.after as string) : undefined;

  return {
    id: req.id,
    actionType: req.actionType,
    status: req.status,
    headline: req.contextPreview,
    reasoning: req.reasoning,
    before,
    after,
    payload,
    expiresAt: req.expiresAt.toISOString(),
    agentName: req.agentName,
  };
}

/**
 * Convert an approvals-page `PendingApproval` → `NormalizedProposal`.
 */
export function proposalFromPendingApproval(approval: PendingApproval): NormalizedProposal {
  const payload = approval.metadata;
  const before =
    payload && typeof payload.before === 'string' ? (payload.before as string) : undefined;
  const after =
    payload && typeof payload.after === 'string' ? (payload.after as string) : undefined;

  return {
    id: approval.id,
    actionType: approval.actionType,
    status: approval.status,
    headline: approval.actionDescription,
    reasoning: approval.actionDescription,
    consequences: approval.consequences,
    before,
    after,
    payload,
    expiresAt: approval.expiresAt,
    agentName: approval.requestedBy?.name,
  };
}

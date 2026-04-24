/**
 * Axios wrappers for `/api/v1/proposals/*` endpoints (Phase 89 Plan 02).
 *
 * All mutation endpoints return a `ProposalEnvelope` of the updated
 * proposal so the UI can swap card → receipt without a follow-up fetch.
 */

import { apiClient } from '@/services/api/client';
import type {
  ProposalEnvelope,
  ProposalListResponse,
  RejectProposalRequestBody,
  RetryProposalRequestBody,
} from './types';

const BASE = '/proposals';

export function acceptProposal(id: string): Promise<ProposalEnvelope> {
  return apiClient.post<ProposalEnvelope>(`${BASE}/${id}/accept`, {});
}

export function rejectProposal(id: string, reason?: string): Promise<ProposalEnvelope> {
  const body: RejectProposalRequestBody = reason ? { reason } : {};
  return apiClient.post<ProposalEnvelope>(`${BASE}/${id}/reject`, body);
}

export function retryProposal(id: string, hint?: string): Promise<ProposalEnvelope> {
  const body: RetryProposalRequestBody = hint ? { hint } : {};
  return apiClient.post<ProposalEnvelope>(`${BASE}/${id}/retry`, body);
}

export function listProposals(sessionId: string): Promise<ProposalListResponse> {
  return apiClient.get<ProposalListResponse>(BASE, {
    params: { session_id: sessionId },
  });
}

export const proposalApi = {
  acceptProposal,
  rejectProposal,
  retryProposal,
  listProposals,
};

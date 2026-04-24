/**
 * Phase 89 Plan 06 — PilotSpaceStreamHandler dispatches proposal_reverted
 * to ProposalsStore.applyRevertedEvent.
 *
 * Deliberately isolates the SSE → store path so the fan-out wiring is
 * verified even before any UI component is mounted.
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { PilotSpaceStore } from '../PilotSpaceStore';
import { ProposalsStore } from '@/stores/proposals/proposalsStore';
import { mockAppliedProposal } from '@/features/ai/proposals/fixtures/proposals';
import type { SSEEvent } from '@/lib/sse-client';

describe('PilotSpaceStreamHandler — proposal_reverted dispatch', () => {
  let pilotStore: PilotSpaceStore;
  let proposalsStore: ProposalsStore;

  beforeEach(() => {
    pilotStore = new PilotSpaceStore();
    proposalsStore = new ProposalsStore();
    pilotStore.streamHandler.setProposalsStore(proposalsStore);
  });

  it('routes a `proposal_reverted` SSE frame to applyRevertedEvent', () => {
    const applied = mockAppliedProposal({ id: 'p-sse', appliedVersion: 4 });
    proposalsStore.upsertProposal(applied);
    proposalsStore.applyAppliedEvent({
      proposalId: 'p-sse',
      appliedVersion: 4,
      linesChanged: 2,
      timestamp: '2026-04-24T12:00:00.000Z',
    });

    const frame = {
      type: 'proposal_reverted',
      data: {
        proposalId: 'p-sse',
        newVersionNumber: 3,
        revertedFromVersion: 4,
        timestamp: '2026-04-24T12:05:00.000Z',
      },
    } as unknown as SSEEvent;

    pilotStore.streamHandler.handleSSEEvent(frame);

    // Observable state confirms the dispatch reached applyRevertedEvent.
    expect(proposalsStore.getById('p-sse')?.status).toBe('reverted');
    expect(proposalsStore.getById('p-sse')?.appliedVersion).toBe(3);
    expect(proposalsStore.lastAppliedProposalId).toBeNull();
  });

  it('is silent when proposalsStore is not wired', () => {
    const handler = new PilotSpaceStore().streamHandler;
    const frame = {
      type: 'proposal_reverted',
      data: {
        proposalId: 'p-none',
        newVersionNumber: 1,
        revertedFromVersion: 2,
        timestamp: '2026-04-24T12:00:00.000Z',
      },
    } as unknown as SSEEvent;
    expect(() => handler.handleSSEEvent(frame)).not.toThrow();
  });
});

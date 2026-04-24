import { describe, it, expect, beforeEach } from 'vitest';
import { autorun } from 'mobx';
import { ProposalsStore } from '../proposalsStore';
import {
  mockTextProposal,
  mockAppliedProposal,
} from '@/features/ai/proposals/fixtures/proposals';
import type {
  ProposalAppliedEventData,
  ProposalRejectedEventData,
  ProposalRetriedEventData,
} from '@/features/ai/proposals/types';

describe('ProposalsStore', () => {
  let store: ProposalsStore;

  beforeEach(() => {
    store = new ProposalsStore();
  });

  describe('upsertProposal + getByMessageId', () => {
    it('stores a proposal keyed by id and indexes by messageId', () => {
      const p = mockTextProposal({ id: 'p1', messageId: 'm1' });
      store.upsertProposal(p);
      expect(store.getById('p1')).toEqual(p);
      expect(store.getByMessageId('m1')).toEqual([p]);
    });

    it('returns multiple proposals for the same message in chronological order', () => {
      const a = mockTextProposal({
        id: 'a',
        messageId: 'm1',
        createdAt: '2026-04-24T10:00:00.000Z',
      });
      const b = mockTextProposal({
        id: 'b',
        messageId: 'm1',
        createdAt: '2026-04-24T10:00:05.000Z',
      });
      store.upsertProposal(b);
      store.upsertProposal(a);
      expect(store.getByMessageId('m1').map((p) => p.id)).toEqual(['a', 'b']);
    });

    it('pendingByMessageId filters non-pending entries', () => {
      const pending = mockTextProposal({ id: 'p1', messageId: 'm1' });
      const applied = mockAppliedProposal({ id: 'p2', messageId: 'm1' });
      store.upsertProposal(pending);
      store.upsertProposal(applied);
      expect(store.pendingByMessageId('m1').map((p) => p.id)).toEqual(['p1']);
    });
  });

  describe('applyAppliedEvent', () => {
    it('transitions proposal to applied + records appliedVersion + linesChanged', () => {
      const p = mockTextProposal({ id: 'p1' });
      store.upsertProposal(p);

      const event: ProposalAppliedEventData = {
        proposalId: 'p1',
        appliedVersion: 5,
        linesChanged: 12,
        timestamp: '2026-04-24T12:00:05.000Z',
      };
      store.applyAppliedEvent(event);

      const updated = store.getById('p1')!;
      expect(updated.status).toBe('applied');
      expect(updated.appliedVersion).toBe(5);
      expect(updated.decidedAt).toBe(event.timestamp);
      expect(store.getLinesChanged('p1')).toBe(12);
      expect(store.lastAppliedProposalId).toBe('p1');
    });

    it('ignores applied events for unknown proposal ids', () => {
      store.applyAppliedEvent({
        proposalId: 'unknown',
        appliedVersion: 1,
        linesChanged: 0,
        timestamp: '2026-04-24T12:00:00.000Z',
      });
      expect(store.getById('unknown')).toBeUndefined();
      expect(store.lastAppliedProposalId).toBeNull();
    });
  });

  describe('applyRejectedEvent', () => {
    it('transitions proposal to rejected', () => {
      const p = mockTextProposal({ id: 'p1' });
      store.upsertProposal(p);

      const event: ProposalRejectedEventData = {
        proposalId: 'p1',
        reason: 'not needed',
        timestamp: '2026-04-24T12:00:05.000Z',
      };
      store.applyRejectedEvent(event);

      expect(store.getById('p1')!.status).toBe('rejected');
      expect(store.getById('p1')!.decidedAt).toBe(event.timestamp);
    });
  });

  describe('applyRetriedEvent', () => {
    it('transitions proposal to retried', () => {
      const p = mockTextProposal({ id: 'p1' });
      store.upsertProposal(p);

      const event: ProposalRetriedEventData = {
        proposalId: 'p1',
        hint: 'try a smaller change',
        timestamp: '2026-04-24T12:00:05.000Z',
      };
      store.applyRetriedEvent(event);

      expect(store.getById('p1')!.status).toBe('retried');
    });
  });

  describe('reactivity', () => {
    it('is makeAutoObservable — mutations trigger autorun callbacks', () => {
      const seen: string[] = [];
      const dispose = autorun(() => {
        const p = store.getById('p1');
        seen.push(p?.status ?? 'missing');
      });

      store.upsertProposal(mockTextProposal({ id: 'p1' }));
      store.applyAppliedEvent({
        proposalId: 'p1',
        appliedVersion: 1,
        linesChanged: 3,
        timestamp: '2026-04-24T12:00:00.000Z',
      });

      dispose();
      expect(seen).toEqual(['missing', 'pending', 'applied']);
    });
  });

  describe('setStatus (optimistic)', () => {
    it('applies a transient status without waiting for an SSE event', () => {
      store.upsertProposal(mockTextProposal({ id: 'p1' }));
      store.setStatus('p1', 'applied', '2026-04-24T12:00:00.000Z');
      expect(store.getById('p1')!.status).toBe('applied');
    });
  });

  describe('removeOlderThan', () => {
    it('evicts non-pending proposals older than cutoff', () => {
      store.upsertProposal(
        mockAppliedProposal({
          id: 'old',
          decidedAt: '2026-04-20T00:00:00.000Z',
        })
      );
      store.upsertProposal(
        mockAppliedProposal({
          id: 'fresh',
          decidedAt: '2026-04-24T12:00:00.000Z',
        })
      );
      store.upsertProposal(mockTextProposal({ id: 'pending' }));

      store.removeOlderThan(new Date('2026-04-22T00:00:00.000Z'));

      expect(store.getById('old')).toBeUndefined();
      expect(store.getById('fresh')).toBeDefined();
      expect(store.getById('pending')).toBeDefined();
    });
  });

  describe('reset', () => {
    it('clears all proposals', () => {
      store.upsertProposal(mockTextProposal({ id: 'p1' }));
      store.upsertProposal(mockTextProposal({ id: 'p2' }));
      store.reset();
      expect(store.getById('p1')).toBeUndefined();
      expect(store.lastAppliedProposalId).toBeNull();
    });
  });
});

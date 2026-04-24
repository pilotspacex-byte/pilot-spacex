import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { StoreContext, RootStore } from '@/stores/RootStore';
import {
  useAcceptProposal,
  useRejectProposal,
  useRetryProposal,
} from '../useProposalActions';
import { mockTextProposal } from '../fixtures/proposals';
import * as proposalApiModule from '../proposalApi';

function makeWrapper(rootStore: RootStore) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return ({ children }: { children: ReactNode }) => (
    <StoreContext.Provider value={rootStore}>
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    </StoreContext.Provider>
  );
}

describe('useProposalActions', () => {
  let rootStore: RootStore;

  beforeEach(() => {
    rootStore = new RootStore();
    vi.restoreAllMocks();
  });

  describe('useAcceptProposal', () => {
    it('optimistically flips status to applied then persists server envelope', async () => {
      const p = mockTextProposal({ id: 'p1' });
      rootStore.proposals.upsertProposal(p);

      const serverEnvelope = { ...p, status: 'applied' as const, appliedVersion: 7 };
      vi.spyOn(proposalApiModule.proposalApi, 'acceptProposal').mockResolvedValue(serverEnvelope);

      const { result } = renderHook(() => useAcceptProposal(), {
        wrapper: makeWrapper(rootStore),
      });

      act(() => {
        result.current.mutate('p1');
      });

      // Optimistic: status flips immediately.
      await waitFor(() => {
        expect(rootStore.proposals.getById('p1')?.status).toBe('applied');
      });

      // Server reply arrives with appliedVersion.
      await waitFor(() => {
        expect(rootStore.proposals.getById('p1')?.appliedVersion).toBe(7);
      });
    });

    it('rolls back to prior envelope on API error', async () => {
      const p = mockTextProposal({ id: 'p1' });
      rootStore.proposals.upsertProposal(p);

      vi.spyOn(proposalApiModule.proposalApi, 'acceptProposal').mockRejectedValue(
        new Error('boom')
      );

      const { result } = renderHook(() => useAcceptProposal(), {
        wrapper: makeWrapper(rootStore),
      });

      act(() => {
        result.current.mutate('p1');
      });

      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });
      expect(rootStore.proposals.getById('p1')?.status).toBe('pending');
    });
  });

  describe('useRejectProposal', () => {
    it('optimistically transitions to rejected', async () => {
      const p = mockTextProposal({ id: 'p1' });
      rootStore.proposals.upsertProposal(p);
      const server = { ...p, status: 'rejected' as const };
      vi.spyOn(proposalApiModule.proposalApi, 'rejectProposal').mockResolvedValue(server);

      const { result } = renderHook(() => useRejectProposal(), {
        wrapper: makeWrapper(rootStore),
      });
      act(() => {
        result.current.mutate({ id: 'p1', reason: 'nope' });
      });

      await waitFor(() => {
        expect(rootStore.proposals.getById('p1')?.status).toBe('rejected');
      });
    });
  });

  describe('useRetryProposal', () => {
    it('optimistically transitions to retried', async () => {
      const p = mockTextProposal({ id: 'p1' });
      rootStore.proposals.upsertProposal(p);
      const server = { ...p, status: 'retried' as const };
      vi.spyOn(proposalApiModule.proposalApi, 'retryProposal').mockResolvedValue(server);

      const { result } = renderHook(() => useRetryProposal(), {
        wrapper: makeWrapper(rootStore),
      });
      act(() => {
        result.current.mutate({ id: 'p1' });
      });

      await waitFor(() => {
        expect(rootStore.proposals.getById('p1')?.status).toBe('retried');
      });
    });
  });
});

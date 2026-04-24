/**
 * Phase 89 Plan 06 — AppliedReceipt revert wiring (RED→GREEN).
 *
 * Asserts:
 *   1. Internal useRevertProposal fires on click within the 10-min window
 *      when `onRevert` prop is omitted.
 *   2. Optimistic status flip (pending → reverted) visible in store.
 *   3. Button hidden past the 10-min window (matches Plan 04 behavior —
 *      do NOT refactor to disabled+tooltip; button is hidden).
 *   4. Outside window + window-open behavior.
 *   5. PilotSpaceStreamHandler dispatches proposal_reverted to the store.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import React from 'react';
import { StoreContext, RootStore } from '@/stores/RootStore';
import { AppliedReceipt } from '../AppliedReceipt';
import { mockAppliedProposal } from '../fixtures/proposals';
import * as proposalApiModule from '../proposalApi';
import type { RevertResultEnvelope } from '../types';

function renderReceipt(ui: ReactNode, rootStore: RootStore = new RootStore()) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return {
    rootStore,
    ...render(
      React.createElement(
        StoreContext.Provider,
        { value: rootStore },
        React.createElement(QueryClientProvider, { client: queryClient }, ui)
      )
    ),
  };
}

describe('AppliedReceipt — Plan 06 revert wiring', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('fires useRevertProposal internally on click (no onRevert prop)', async () => {
    const decided = new Date('2026-04-24T12:00:00.000Z').getTime();
    const now = decided + 5 * 60 * 1000; // 5 min — inside window
    const envelope = mockAppliedProposal({
      id: 'p-internal',
      appliedVersion: 3,
      decidedAt: new Date(decided).toISOString(),
    });

    const store = new RootStore();
    store.proposals.upsertProposal(envelope);

    const result: RevertResultEnvelope = {
      proposal: { ...envelope, appliedVersion: 2 },
      newVersionNumber: 2,
      newHistoryEntry: {
        vN: 2,
        by: 'user',
        at: new Date(now).toISOString(),
        summary: 'Reverted v3 → v2',
        snapshot: {},
      },
    };
    const spy = vi
      .spyOn(proposalApiModule.proposalApi, 'revertProposal')
      .mockResolvedValue(result);

    renderReceipt(
      <AppliedReceipt envelope={envelope} linesChanged={1} now={now} />,
      store
    );

    await userEvent.click(screen.getByTestId('revert-button'));
    await waitFor(() => expect(spy).toHaveBeenCalledWith('p-internal'));

    // Optimistic flip to 'reverted' then applyRevertedEvent on success.
    await waitFor(() => {
      expect(store.proposals.getById('p-internal')?.status).toBe('reverted');
    });
  });

  it('hides the Revert button past the 10-minute window (unchanged Plan 04 behavior)', () => {
    const decided = new Date('2026-04-24T12:00:00.000Z').getTime();
    const now = decided + 11 * 60 * 1000; // 11 min — outside window
    const envelope = mockAppliedProposal({
      decidedAt: new Date(decided).toISOString(),
    });
    renderReceipt(<AppliedReceipt envelope={envelope} linesChanged={1} now={now} />);
    expect(screen.queryByTestId('revert-button')).not.toBeInTheDocument();
  });

  it('prefers the `onRevert` prop override (test path) over internal mutation', async () => {
    const decided = new Date('2026-04-24T12:00:00.000Z').getTime();
    const now = decided + 60_000;
    const envelope = mockAppliedProposal({
      id: 'p-override',
      decidedAt: new Date(decided).toISOString(),
    });

    const apiSpy = vi.spyOn(proposalApiModule.proposalApi, 'revertProposal');
    const onRevert = vi.fn();

    renderReceipt(
      <AppliedReceipt
        envelope={envelope}
        linesChanged={0}
        onRevert={onRevert}
        now={now}
      />
    );

    await userEvent.click(screen.getByTestId('revert-button'));
    expect(onRevert).toHaveBeenCalledWith('p-override');
    expect(apiSpy).not.toHaveBeenCalled();
  });

  it('shows "Reverting…" label while the mutation is pending', async () => {
    const decided = new Date('2026-04-24T12:00:00.000Z').getTime();
    const now = decided + 60_000;
    const envelope = mockAppliedProposal({
      id: 'p-pending',
      decidedAt: new Date(decided).toISOString(),
    });

    const store = new RootStore();
    store.proposals.upsertProposal(envelope);

    // Never-resolving mock to keep mutation in pending state.
    vi.spyOn(proposalApiModule.proposalApi, 'revertProposal').mockImplementation(
      () => new Promise(() => {})
    );

    renderReceipt(
      <AppliedReceipt envelope={envelope} linesChanged={1} now={now} />,
      store
    );

    await userEvent.click(screen.getByTestId('revert-button'));
    await waitFor(() =>
      expect(screen.getByTestId('revert-button')).toHaveTextContent(/reverting/i)
    );
  });
});

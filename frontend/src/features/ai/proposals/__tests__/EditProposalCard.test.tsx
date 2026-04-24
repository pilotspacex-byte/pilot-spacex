import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { StoreContext, RootStore } from '@/stores/RootStore';
import { EditProposalCard } from '../EditProposalCard';
import {
  mockTextProposal,
  mockFieldsProposal,
  mockPlanModeProposal,
  mockDraftModeProposal,
} from '../fixtures/proposals';
import * as proposalApiModule from '../proposalApi';

vi.mock('sonner', () => ({
  toast: {
    message: vi.fn(),
    error: vi.fn(),
    success: vi.fn(),
  },
}));

import { toast } from 'sonner';

function renderCard(ui: ReactNode, rootStore: RootStore = new RootStore()) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return {
    rootStore,
    ...render(
      <StoreContext.Provider value={rootStore}>
        <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>
      </StoreContext.Provider>
    ),
  };
}

describe('EditProposalCard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the orange pending stroke + 16px radius anatomy', () => {
    const envelope = mockTextProposal();
    renderCard(<EditProposalCard envelope={envelope} />);
    const card = screen.getByTestId('edit-proposal-card');
    expect(card).toHaveClass('border-[#f97316]', 'border-[1.5px]', 'rounded-2xl');
  });

  it('renders EDIT PROPOSAL badge, target chip, and version label', () => {
    const envelope = mockTextProposal({ targetArtifactType: 'ISSUE' });
    renderCard(<EditProposalCard envelope={envelope} />);
    expect(screen.getByTestId('edit-proposal-badge')).toHaveTextContent(/edit proposal/i);
    const target = screen.getByTestId('target-chip');
    expect(target).toHaveTextContent(/ISSUE/);
    expect(screen.getByTestId('version-label')).toHaveTextContent('current → +1');
  });

  it('renders TextDiffBlock when diffKind=text and FieldDiffRow list when fields', () => {
    const textEnv = mockTextProposal();
    const { unmount } = renderCard(<EditProposalCard envelope={textEnv} />);
    expect(screen.getByTestId('text-diff-block')).toBeInTheDocument();
    unmount();

    const fieldsEnv = mockFieldsProposal();
    renderCard(<EditProposalCard envelope={fieldsEnv} />);
    expect(screen.getByTestId('field-diff-list')).toBeInTheDocument();
    expect(screen.getAllByTestId('field-diff-row').length).toBeGreaterThan(0);
  });

  it('renders reasoning callout when reasoning is present', () => {
    renderCard(<EditProposalCard envelope={mockTextProposal()} />);
    expect(screen.getByTestId('reasoning-callout')).toBeInTheDocument();
  });

  it('hides reasoning callout when reasoning is null', () => {
    renderCard(<EditProposalCard envelope={mockTextProposal({ reasoning: null })} />);
    expect(screen.queryByTestId('reasoning-callout')).not.toBeInTheDocument();
  });

  it('renders DD-003 rail', () => {
    renderCard(<EditProposalCard envelope={mockTextProposal()} />);
    expect(screen.getByTestId('dd003-rail')).toHaveTextContent('Nothing saved until you accept.');
  });

  it('calls accept mutation on Accept click', async () => {
    const envelope = mockTextProposal({ id: 'p-acc' });
    const store = new RootStore();
    store.proposals.upsertProposal(envelope);
    const spy = vi
      .spyOn(proposalApiModule.proposalApi, 'acceptProposal')
      .mockResolvedValue({ ...envelope, status: 'applied', appliedVersion: 2 });

    renderCard(<EditProposalCard envelope={envelope} />, store);
    await userEvent.click(screen.getByTestId('accept-button'));
    await waitFor(() => expect(spy).toHaveBeenCalledWith('p-acc'));
  });

  it('plan mode renders the "Plan mode preview only" badge and disables Accept', async () => {
    const envelope = mockPlanModeProposal({ id: 'p-plan' });
    const store = new RootStore();
    store.proposals.upsertProposal(envelope);
    const spy = vi.spyOn(proposalApiModule.proposalApi, 'acceptProposal');
    renderCard(<EditProposalCard envelope={envelope} />, store);

    expect(screen.getByTestId('plan-mode-badge')).toBeInTheDocument();
    const btn = screen.getByTestId('accept-button');
    expect(btn).toBeDisabled();
    expect(btn.getAttribute('title')).toContain('Switch to Act');

    await userEvent.click(btn);
    expect(spy).not.toHaveBeenCalled();
  });

  it('draft mode renders the Draft badge; Accept shows toast + does not call API', async () => {
    const envelope = mockDraftModeProposal({ id: 'p-draft' });
    const store = new RootStore();
    store.proposals.upsertProposal(envelope);
    const spy = vi.spyOn(proposalApiModule.proposalApi, 'acceptProposal');
    renderCard(<EditProposalCard envelope={envelope} />, store);

    expect(screen.getByTestId('draft-mode-badge')).toBeInTheDocument();
    await userEvent.click(screen.getByTestId('accept-button'));
    expect(spy).not.toHaveBeenCalled();
    expect(toast.message).toHaveBeenCalledWith(
      'Draft mode does not persist',
      expect.any(Object)
    );
  });

  it('⌘↵ keybinding triggers accept when focus is inside the card', async () => {
    const envelope = mockTextProposal({ id: 'p-kbd' });
    const store = new RootStore();
    store.proposals.upsertProposal(envelope);
    const spy = vi
      .spyOn(proposalApiModule.proposalApi, 'acceptProposal')
      .mockResolvedValue({ ...envelope, status: 'applied' });
    renderCard(<EditProposalCard envelope={envelope} />, store);

    const accept = screen.getByTestId('accept-button');
    accept.focus();
    await act(async () => {
      accept.dispatchEvent(
        new KeyboardEvent('keydown', {
          key: 'Enter',
          metaKey: true,
          bubbles: true,
          cancelable: true,
        })
      );
    });
    await waitFor(() => expect(spy).toHaveBeenCalled());
  });

  it('respects prefers-reduced-motion — no transition class applied', () => {
    const originalMM = window.matchMedia;
    window.matchMedia = vi.fn().mockImplementation((q: string) => ({
      matches: q.includes('reduce'),
      media: q,
      onchange: null,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }));
    try {
      renderCard(<EditProposalCard envelope={mockTextProposal()} />);
      const card = screen.getByTestId('edit-proposal-card');
      expect(card.className).not.toMatch(/transition-all/);
    } finally {
      window.matchMedia = originalMM;
    }
  });

  it('calls reject mutation on Reject click', async () => {
    const envelope = mockTextProposal({ id: 'p-rej' });
    const store = new RootStore();
    store.proposals.upsertProposal(envelope);
    const spy = vi
      .spyOn(proposalApiModule.proposalApi, 'rejectProposal')
      .mockResolvedValue({ ...envelope, status: 'rejected' });
    renderCard(<EditProposalCard envelope={envelope} />, store);
    await userEvent.click(screen.getByTestId('reject-button'));
    await waitFor(() => expect(spy).toHaveBeenCalledWith('p-rej', undefined));
  });

  it('calls retry mutation on Retry click', async () => {
    const envelope = mockTextProposal({ id: 'p-ret' });
    const store = new RootStore();
    store.proposals.upsertProposal(envelope);
    const spy = vi
      .spyOn(proposalApiModule.proposalApi, 'retryProposal')
      .mockResolvedValue({ ...envelope, status: 'retried' });
    renderCard(<EditProposalCard envelope={envelope} />, store);
    await userEvent.click(screen.getByTestId('retry-button'));
    await waitFor(() => expect(spy).toHaveBeenCalledWith('p-ret', undefined));
  });

  it('has a descriptive aria-label on the region root', () => {
    const envelope = mockTextProposal({ targetArtifactType: 'NOTE', targetArtifactId: 'abcdefgh12345' });
    renderCard(<EditProposalCard envelope={envelope} />);
    const card = screen.getByTestId('edit-proposal-card');
    expect(card.getAttribute('role')).toBe('region');
    expect(card.getAttribute('aria-label')).toContain('note abcdefgh');
  });
});

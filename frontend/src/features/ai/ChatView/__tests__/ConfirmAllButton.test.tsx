/**
 * Unit tests for ConfirmAllButton component.
 * T-064
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { makeAutoObservable } from 'mobx';

// Mock aiApi
vi.mock('@/services/api/ai', () => ({
  aiApi: {
    confirmAllIntents: vi.fn().mockResolvedValue({
      confirmed: [],
      confirmed_count: 5,
      remaining_count: 2,
      deduplicating_count: 0,
    }),
  },
}));

vi.mock('@/hooks/use-toast', () => ({
  useToast: () => ({ toast: vi.fn() }),
}));

import { ConfirmAllButton } from '../ConfirmAllButton';
import { aiApi } from '@/services/api/ai';
import type { WorkIntentState } from '@/stores/ai/PilotSpaceStore';

/** Minimal store stub for ConfirmAllButton */
class MockStore {
  intents = new Map<string, WorkIntentState>();
  workspaceId: string | null = 'ws-1';
  skillQueue = { runningCount: 0, queuedCount: 0, maxConcurrent: 5 };

  get eligibleIntentCount() {
    return Array.from(this.intents.values()).filter(
      (i) => i.status === 'detected' && i.confidence >= 0.7
    ).length;
  }

  get runningSkillCount() {
    return this.skillQueue.runningCount;
  }
  get queuedSkillCount() {
    return this.skillQueue.queuedCount;
  }

  updateIntentStatus(id: string, status: WorkIntentState['status']) {
    const existing = this.intents.get(id);
    if (existing) this.intents.set(id, { ...existing, status });
  }

  constructor() {
    makeAutoObservable(this);
  }
}

function addIntent(store: MockStore, id: string, confidence: number) {
  store.intents.set(id, {
    intentId: id,
    what: `Intent ${id}`,
    confidence,
    status: 'detected',
  });
}

describe('ConfirmAllButton', () => {
  let store: MockStore;

  beforeEach(() => {
    store = new MockStore();
    vi.clearAllMocks();
  });

  it('renders nothing when < 2 eligible intents', () => {
    addIntent(store, 'i-1', 0.85);
    const { container } = render(<ConfirmAllButton store={store as never} />);
    expect(container.firstChild).toBeNull();
  });

  it('renders button when >= 2 eligible intents', () => {
    addIntent(store, 'i-1', 0.85);
    addIntent(store, 'i-2', 0.75);
    render(<ConfirmAllButton store={store as never} />);
    expect(screen.getByRole('button', { name: /confirm all/i })).toBeInTheDocument();
  });

  it('hides intents with confidence < 70% from eligible count', () => {
    addIntent(store, 'i-1', 0.85);
    addIntent(store, 'i-2', 0.65); // below threshold
    const { container } = render(<ConfirmAllButton store={store as never} />);
    expect(container.firstChild).toBeNull();
  });

  it('shows count badge in button', () => {
    addIntent(store, 'i-1', 0.85);
    addIntent(store, 'i-2', 0.75);
    addIntent(store, 'i-3', 0.9);
    render(<ConfirmAllButton store={store as never} />);
    expect(screen.getByText(/\(3\)/)).toBeInTheDocument();
  });

  it('calls confirmAllIntents on click', async () => {
    addIntent(store, 'i-1', 0.85);
    addIntent(store, 'i-2', 0.75);
    const user = userEvent.setup();
    render(<ConfirmAllButton store={store as never} />);

    await user.click(screen.getByRole('button', { name: /confirm all/i }));
    await waitFor(() => {
      expect(aiApi.confirmAllIntents).toHaveBeenCalledWith('ws-1', 0.7, 10);
    });
  });

  it('shows result after successful confirmation', async () => {
    addIntent(store, 'i-1', 0.85);
    addIntent(store, 'i-2', 0.75);
    const user = userEvent.setup();
    render(<ConfirmAllButton store={store as never} />);

    await user.click(screen.getByRole('button', { name: /confirm all/i }));
    await waitFor(() => {
      expect(screen.getByText(/5 confirmed/i)).toBeInTheDocument();
      expect(screen.getByText(/2 remaining/i)).toBeInTheDocument();
    });
  });
});

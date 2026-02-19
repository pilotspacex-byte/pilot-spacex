/**
 * Unit tests for QueueDepthIndicator component.
 * T-064
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { makeAutoObservable } from 'mobx';
import { QueueDepthIndicator } from '../QueueDepthIndicator';
import type { WorkIntentState } from '@/stores/ai/PilotSpaceStore';

class MockStore {
  intents = new Map<string, WorkIntentState>();
  workspaceId = 'ws-1';
  skillQueue = { runningCount: 0, queuedCount: 0, maxConcurrent: 5 };

  get eligibleIntentCount() {
    return 0;
  }
  get runningSkillCount() {
    return this.skillQueue.runningCount;
  }
  get queuedSkillCount() {
    return this.skillQueue.queuedCount;
  }

  constructor() {
    makeAutoObservable(this);
  }
}

describe('QueueDepthIndicator', () => {
  it('renders nothing when idle', () => {
    const store = new MockStore();
    const { container } = render(<QueueDepthIndicator store={store as never} />);
    expect(container.firstChild).toBeNull();
  });

  it('renders when skills are running', () => {
    const store = new MockStore();
    store.skillQueue = { runningCount: 2, queuedCount: 1, maxConcurrent: 5 };
    render(<QueueDepthIndicator store={store as never} />);

    expect(screen.getByRole('status')).toBeInTheDocument();
    expect(screen.getByText(/2 running/i)).toBeInTheDocument();
    expect(screen.getByText(/1 queued/i)).toBeInTheDocument();
  });

  it('has correct aria-live attribute', () => {
    const store = new MockStore();
    store.skillQueue = { runningCount: 1, queuedCount: 0, maxConcurrent: 5 };
    render(<QueueDepthIndicator store={store as never} />);

    const status = screen.getByRole('status');
    expect(status).toHaveAttribute('aria-live', 'polite');
  });

  it('shows queue full warning when maxConcurrent reached', () => {
    const store = new MockStore();
    store.skillQueue = { runningCount: 5, queuedCount: 3, maxConcurrent: 5 };
    render(<QueueDepthIndicator store={store as never} />);

    expect(screen.getByText(/Queue full/i)).toBeInTheDocument();
  });

  it('renders max label', () => {
    const store = new MockStore();
    store.skillQueue = { runningCount: 1, queuedCount: 0, maxConcurrent: 5 };
    render(<QueueDepthIndicator store={store as never} />);

    expect(screen.getByText('max 5')).toBeInTheDocument();
  });

  it('has correct aria-label', () => {
    const store = new MockStore();
    store.skillQueue = { runningCount: 2, queuedCount: 3, maxConcurrent: 5 };
    render(<QueueDepthIndicator store={store as never} />);

    const status = screen.getByRole('status');
    expect(status).toHaveAttribute('aria-label', 'Skill execution queue: 2 running, 3 queued');
  });
});

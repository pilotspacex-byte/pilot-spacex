import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock MobX observer as passthrough
vi.mock('mobx-react-lite', () => ({
  observer: (component: React.FC) => component,
}));

// Mock stores
vi.mock('@/stores/RootStore', () => ({
  useAuthStore: () => ({
    userDisplayName: 'Tin Dang',
  }),
  useWorkspaceStore: () => ({
    currentWorkspace: { id: 'ws-1', slug: 'test-ws' },
  }),
}));

// Mock AIStore
const mockPilotSpaceStore = {
  workspaceId: '',
  setWorkspaceId: vi.fn(),
};

vi.mock('@/stores/ai/AIStore', () => ({
  getAIStore: () => ({
    pilotSpace: mockPilotSpaceStore,
  }),
}));

// Mock child components
vi.mock('../components/DailyBrief', () => ({
  DailyBrief: ({ workspaceSlug }: { workspaceSlug: string }) => (
    <div data-testid="daily-brief" data-workspace-slug={workspaceSlug} />
  ),
}));

vi.mock('@/features/ai/ChatView', () => ({
  ChatView: ({
    className,
    autoFocus,
    userName,
  }: {
    store: unknown;
    userName: string;
    className?: string;
    autoFocus?: boolean;
  }) => (
    <div
      data-testid="chat-view"
      data-class={className}
      data-auto-focus={String(autoFocus)}
      data-user-name={userName}
    />
  ),
}));

import { HomepageHub } from '../components/HomepageHub';

describe('HomepageHub', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockPilotSpaceStore.workspaceId = '';
  });

  it('renders DailyBrief and ChatView', () => {
    render(<HomepageHub workspaceSlug="test-ws" />);

    expect(screen.getByTestId('daily-brief')).toBeInTheDocument();
    expect(screen.getByTestId('chat-view')).toBeInTheDocument();
  });

  it('passes workspaceSlug to DailyBrief', () => {
    render(<HomepageHub workspaceSlug="my-workspace" />);

    expect(screen.getByTestId('daily-brief')).toHaveAttribute(
      'data-workspace-slug',
      'my-workspace'
    );
  });

  it('renders ChatView with autoFocus disabled', () => {
    render(<HomepageHub workspaceSlug="test-ws" />);

    expect(screen.getByTestId('chat-view')).toHaveAttribute('data-auto-focus', 'false');
  });

  it('renders AI command center aside with ARIA label', () => {
    render(<HomepageHub workspaceSlug="test-ws" />);

    const aside = screen.getByLabelText('AI command center');
    expect(aside).toBeInTheDocument();
    expect(aside.tagName).toBe('ASIDE');
  });

  it('sets workspace ID on AI store', () => {
    render(<HomepageHub workspaceSlug="test-ws" />);

    expect(mockPilotSpaceStore.setWorkspaceId).toHaveBeenCalledWith('ws-1');
  });

  it('does not set workspace ID when it matches', () => {
    mockPilotSpaceStore.workspaceId = 'ws-1';
    render(<HomepageHub workspaceSlug="test-ws" />);

    expect(mockPilotSpaceStore.setWorkspaceId).not.toHaveBeenCalled();
  });

  it('passes real userName to ChatView from auth store', () => {
    render(<HomepageHub workspaceSlug="test-ws" />);

    expect(screen.getByTestId('chat-view')).toHaveAttribute('data-user-name', 'Tin Dang');
  });
});

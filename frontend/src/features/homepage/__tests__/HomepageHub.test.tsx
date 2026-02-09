import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock MobX observer as passthrough
vi.mock('mobx-react-lite', () => ({
  observer: (component: React.FC) => component,
}));

// Mock HomepageUIStore
const mockSetActiveZone = vi.fn();
const mockHomepageStore = {
  chatExpanded: false,
  activeZone: 'activity' as 'chat' | 'activity' | 'digest',
  setActiveZone: mockSetActiveZone,
  expandChat: vi.fn(),
  collapseChat: vi.fn(),
};

vi.mock('@/stores/RootStore', () => ({
  useHomepageStore: () => mockHomepageStore,
  useWorkspaceStore: () => ({
    currentWorkspace: { id: 'ws-1', slug: 'test-ws' },
  }),
}));

// Mock child components
vi.mock('../components/CompactChatView', () => ({
  CompactChatView: ({ inputRef }: { inputRef?: React.RefObject<HTMLInputElement | null> }) => (
    <div data-testid="compact-chat-view">
      <input ref={inputRef} data-testid="chat-input" />
    </div>
  ),
}));

vi.mock('../components/ActivityFeed', () => ({
  ActivityFeed: ({ workspaceSlug }: { workspaceSlug: string }) => (
    <div data-testid="activity-feed" data-workspace-slug={workspaceSlug} />
  ),
}));

vi.mock('../components/DigestPanel', () => ({
  DigestPanel: ({ aiConfigured }: { aiConfigured?: boolean }) => (
    <div data-testid="digest-panel" data-ai-configured={String(aiConfigured)} />
  ),
}));

import { HomepageHub } from '../components/HomepageHub';

describe('HomepageHub', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockHomepageStore.activeZone = 'activity';
  });

  it('renders all 3 zones', () => {
    render(<HomepageHub workspaceSlug="test-ws" />);

    expect(screen.getByTestId('compact-chat-view')).toBeInTheDocument();
    expect(screen.getByTestId('activity-feed')).toBeInTheDocument();
    expect(screen.getByTestId('digest-panel')).toBeInTheDocument();
  });

  it('passes workspaceSlug to ActivityFeed', () => {
    render(<HomepageHub workspaceSlug="my-workspace" />);

    expect(screen.getByTestId('activity-feed')).toHaveAttribute(
      'data-workspace-slug',
      'my-workspace'
    );
  });

  it('passes aiConfigured prop to DigestPanel', () => {
    render(<HomepageHub workspaceSlug="test-ws" aiConfigured={false} />);

    expect(screen.getByTestId('digest-panel')).toHaveAttribute('data-ai-configured', 'false');
  });

  it('renders ARIA landmarks on all zones', () => {
    render(<HomepageHub workspaceSlug="test-ws" />);

    expect(screen.getByRole('region', { name: 'Quick AI chat' })).toBeInTheDocument();
    expect(screen.getByRole('region', { name: 'Recent activity' })).toBeInTheDocument();
    expect(screen.getByRole('region', { name: 'AI workspace insights' })).toBeInTheDocument();
  });

  it('focuses chat input on "/" keypress', () => {
    render(<HomepageHub workspaceSlug="test-ws" />);

    const chatInput = screen.getByTestId('chat-input');
    fireEvent.keyDown(document, { key: '/' });

    expect(document.activeElement).toBe(chatInput);
  });

  it('does not focus chat on "/" when typing in an input', () => {
    render(
      <div>
        <input data-testid="other-input" />
        <HomepageHub workspaceSlug="test-ws" />
      </div>
    );

    const otherInput = screen.getByTestId('other-input');
    otherInput.focus();

    fireEvent.keyDown(otherInput, { key: '/' });

    // Chat input should not have been focused
    expect(document.activeElement).toBe(otherInput);
  });

  it('cycles zones on F6 keypress', () => {
    mockHomepageStore.activeZone = 'chat';
    render(<HomepageHub workspaceSlug="test-ws" />);

    fireEvent.keyDown(document, { key: 'F6' });

    expect(mockSetActiveZone).toHaveBeenCalledWith('activity');
  });

  it('cycles zones backward on Shift+F6', () => {
    mockHomepageStore.activeZone = 'activity';
    render(<HomepageHub workspaceSlug="test-ws" />);

    fireEvent.keyDown(document, { key: 'F6', shiftKey: true });

    expect(mockSetActiveZone).toHaveBeenCalledWith('chat');
  });

  it('wraps around when cycling past last zone', () => {
    mockHomepageStore.activeZone = 'digest';
    render(<HomepageHub workspaceSlug="test-ws" />);

    fireEvent.keyDown(document, { key: 'F6' });

    expect(mockSetActiveZone).toHaveBeenCalledWith('chat');
  });

  it('defaults aiConfigured to true', () => {
    render(<HomepageHub workspaceSlug="test-ws" />);

    expect(screen.getByTestId('digest-panel')).toHaveAttribute('data-ai-configured', 'true');
  });
});

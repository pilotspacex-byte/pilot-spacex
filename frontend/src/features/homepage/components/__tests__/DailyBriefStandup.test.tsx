/**
 * DailyBrief standup button tests (T017).
 *
 * Tests the "Generate Standup" button renders and sends
 * the \daily-standup command to the AI store on click.
 */

import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

// ── Mocks ────────────────────────────────────────────────────────────────

// Mock next/navigation
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

// Mock date-fns
vi.mock('date-fns', () => ({
  format: vi.fn(() => 'Thursday, February 20, 2026'),
}));

// Mock RootStore hooks
vi.mock('@/stores/RootStore', () => ({
  useAuthStore: () => ({ userDisplayName: 'Tin Dang' }),
  useWorkspaceStore: () => ({
    currentWorkspace: { id: 'ws-1', slug: 'test-ws' },
  }),
  useOnboardingStore: () => ({ openModal: vi.fn() }),
}));

// Mock homepage hooks
vi.mock('../../hooks/useHomepageActivity', () => ({
  useHomepageActivity: () => ({ data: null, isLoading: false }),
}));

vi.mock('../../hooks/useWorkspaceDigest', () => ({
  useWorkspaceDigest: () => ({
    groups: [],
    suggestionCount: 0,
    generatedAt: null,
    isLoading: false,
    isError: false,
    isRefreshing: false,
    dismiss: vi.fn(),
    refresh: vi.fn(),
    refetch: vi.fn(),
  }),
}));

vi.mock('../DigestInsights', () => ({
  DigestInsights: () => React.createElement('div', { 'data-testid': 'digest-insights' }),
}));

// Mock TanStack Query
vi.mock('@tanstack/react-query', () => ({
  useQuery: () => ({ data: null, isLoading: false }),
}));

// Mock services
vi.mock('@/services/api/issues', () => ({
  issuesApi: { list: vi.fn() },
}));
vi.mock('@/services/api/projects', () => ({
  projectsApi: { list: vi.fn() },
}));

// Mock onboarding hooks
vi.mock('@/features/onboarding/hooks/useOnboardingState', () => ({
  useOnboardingState: () => ({ data: null }),
  selectCompletionPercentage: () => 0,
}));

// Mock Tooltip to render children directly (avoids Radix portal issues)
vi.mock('@/components/ui/tooltip', () => ({
  Tooltip: ({ children }: { children: React.ReactNode }) =>
    React.createElement('div', null, children),
  TooltipTrigger: ({ children }: { children: React.ReactNode }) =>
    React.createElement('div', null, children),
  TooltipContent: ({ children }: { children: React.ReactNode }) =>
    React.createElement('div', { role: 'tooltip' }, children),
}));

// AI store mock
const mockSendMessage = vi.fn();
vi.mock('@/stores/ai/AIStore', () => ({
  getAIStore: () => ({
    pilotSpace: { sendMessage: mockSendMessage },
  }),
}));

// ── Import after mocks ──────────────────────────────────────────────────

import { DailyBrief } from '../DailyBrief';

// ── Tests ────────────────────────────────────────────────────────────────

describe('DailyBrief standup button', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the standup button with correct aria-label', () => {
    render(<DailyBrief workspaceSlug="test-ws" />);

    const button = screen.getByRole('button', { name: 'Generate a daily standup summary' });
    expect(button).toBeInTheDocument();
  });

  it('renders the standup button text on wider screens', () => {
    render(<DailyBrief workspaceSlug="test-ws" />);

    // The text is hidden on mobile but present in DOM
    expect(screen.getByText('Standup')).toBeInTheDocument();
  });

  it('shows tooltip text', () => {
    render(<DailyBrief workspaceSlug="test-ws" />);

    // Our mock renders TooltipContent directly
    expect(screen.getByText('Generate a daily standup summary')).toBeInTheDocument();
  });

  it('sends \\daily-standup command to AI store on click', async () => {
    const user = userEvent.setup();
    render(<DailyBrief workspaceSlug="test-ws" />);

    const button = screen.getByRole('button', { name: 'Generate a daily standup summary' });
    await user.click(button);

    expect(mockSendMessage).toHaveBeenCalledOnce();
    expect(mockSendMessage).toHaveBeenCalledWith('\\daily-standup');
  });
});

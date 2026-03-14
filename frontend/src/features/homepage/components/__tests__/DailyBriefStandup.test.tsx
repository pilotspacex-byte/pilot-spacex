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

// Mock RootStore hooks — overridable per test
const mockAuthStore = {
  userDisplayName: 'Tin Dang',
  user: { email: 'tin@example.com' },
};

vi.mock('@/stores/RootStore', () => ({
  useAuthStore: () => mockAuthStore,
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

// Mock new SDLC Context Bridge hooks
vi.mock('../../hooks/useIssueDevObjects', () => ({
  useIssueDevObjects: () => ({ devObjects: new Map(), isLoading: false }),
}));

vi.mock('../../hooks/useActiveCycleMetrics', () => ({
  useActiveCycleMetrics: () => ({
    activeCycle: null,
    velocityData: [],
    averageVelocity: 0,
    isLoading: false,
  }),
}));

vi.mock('../../hooks/useStaleIssueDetection', () => ({
  useStaleIssueDetection: () => [],
}));

// Mock new SDLC Context Bridge components
vi.mock('../NoteContextBadge', () => ({
  NoteContextBadge: () => null,
}));

vi.mock('../DevObjectIndicators', () => ({
  DevObjectIndicators: () => null,
}));

vi.mock('../IssueDetailSheet', () => ({
  IssueDetailSheet: () => null,
}));

vi.mock('../SprintSparkline', () => ({
  SprintSparkline: () => null,
}));

vi.mock('../StaleLogicAlert', () => ({
  StaleLogicAlert: () => null,
}));

vi.mock('../SDLCSuggestionCards', () => ({
  SDLCSuggestionCards: () => null,
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
    // Reset to default display name with real name
    mockAuthStore.userDisplayName = 'Tin Dang';
    mockAuthStore.user = { email: 'tin@example.com' };
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

describe('DailyBrief greeting display name', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows first name when display name is a real name (not email-derived)', () => {
    mockAuthStore.userDisplayName = 'Tin Dang';
    mockAuthStore.user = { email: 'tin@example.com' };

    render(<DailyBrief workspaceSlug="test-ws" />);

    expect(screen.getByText(/Good (morning|afternoon|evening), Tin/)).toBeInTheDocument();
  });

  it('omits name from greeting when display name equals email prefix', () => {
    // e2e-test@pilotspace.dev → userDisplayName = 'e2e-test' (from Supabase fallback)
    mockAuthStore.userDisplayName = 'e2e-test';
    mockAuthStore.user = { email: 'e2e-test@pilotspace.dev' };

    render(<DailyBrief workspaceSlug="test-ws" />);

    // Greeting should NOT include 'e2e-test'
    expect(screen.queryByText(/e2e-test/)).not.toBeInTheDocument();
    // Should show bare greeting
    expect(screen.getByText(/^Good (morning|afternoon|evening)$/)).toBeInTheDocument();
  });

  it('shows first name when display name differs from email prefix', () => {
    mockAuthStore.userDisplayName = 'Alice Smith';
    mockAuthStore.user = { email: 'alice.smith@company.com' };

    render(<DailyBrief workspaceSlug="test-ws" />);

    // 'Alice Smith' !== 'alice.smith' so first name should be shown
    expect(screen.getByText(/Good (morning|afternoon|evening), Alice/)).toBeInTheDocument();
  });

  it('shows bare greeting when display name is empty', () => {
    mockAuthStore.userDisplayName = '';
    mockAuthStore.user = { email: 'user@example.com' };

    render(<DailyBrief workspaceSlug="test-ws" />);

    expect(screen.getByText(/^Good (morning|afternoon|evening)$/)).toBeInTheDocument();
  });
});

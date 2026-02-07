import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { DigestSuggestion, DigestResponse } from '../types';

// Mock MobX observer as passthrough
vi.mock('mobx-react-lite', () => ({
  observer: (component: React.FC) => component,
}));

// Mock stores
vi.mock('@/stores/RootStore', () => ({
  useWorkspaceStore: () => ({
    currentWorkspace: { id: 'ws-1', slug: 'test-ws' },
  }),
}));

// Mock Supabase
vi.mock('@/lib/supabase', () => ({
  supabase: {
    channel: () => ({
      on: vi.fn().mockReturnThis(),
      subscribe: vi.fn().mockReturnThis(),
    }),
    removeChannel: vi.fn(),
  },
}));

// Mock useWorkspaceDigest hook
const mockUseWorkspaceDigest = vi.fn();
vi.mock('../hooks/useWorkspaceDigest', () => ({
  useWorkspaceDigest: (opts: unknown) => mockUseWorkspaceDigest(opts),
}));

// Mock useDigestDismiss hook
const mockDismissMutate = vi.fn();
vi.mock('../hooks/useDigestDismiss', () => ({
  useDigestDismiss: () => ({
    mutate: mockDismissMutate,
  }),
}));

// Mock TanStack Query
vi.mock('@tanstack/react-query', async () => {
  const actual = await vi.importActual('@tanstack/react-query');
  return {
    ...actual,
    useQueryClient: () => ({
      invalidateQueries: vi.fn(),
    }),
  };
});

// Mock query keys
vi.mock('@/lib/queryClient', () => ({
  queryKeys: {
    homepage: {
      digest: (wsId: string) => ['homepage', 'digest', wsId],
    },
  },
}));

// Mock homepage API
vi.mock('../api/homepage-api', () => ({
  homepageApi: {
    refreshDigest: vi.fn().mockResolvedValue({ data: { status: 'generating' } }),
  },
}));

import { DigestPanel } from '../components/DigestPanel/DigestPanel';
import { DigestSuggestionCard } from '../components/DigestPanel/DigestSuggestionCard';
import { DigestEmptyState } from '../components/DigestPanel/DigestEmptyState';
import { DigestSkeleton } from '../components/DigestPanel/DigestSkeleton';

// --- Test data ---

const mockSuggestion: DigestSuggestion = {
  id: 'sug-1',
  category: 'stale_issues',
  title: '3 issues stale for 7+ days',
  description: 'These issues have not been updated recently and may need attention.',
  entity_id: 'issue-1',
  entity_type: 'issue',
  entity_identifier: 'PS-42',
  project_id: 'proj-1',
  project_name: 'Pilot Space',
  action_type: 'navigate',
  action_label: 'View issues',
  action_url: '/test-ws/issues?filter=stale',
  relevance_score: 0.92,
};

const mockDigestResponse: DigestResponse = {
  data: {
    generated_at: new Date(Date.now() - 5 * 60 * 1000).toISOString(), // 5 min ago
    generated_by: 'scheduled',
    suggestions: [mockSuggestion],
    suggestion_count: 1,
  },
};

// --- Component Tests ---

describe('DigestEmptyState', () => {
  it('renders no-provider state', () => {
    render(<DigestEmptyState variant="no-provider" />);

    expect(screen.getByText('AI not configured')).toBeInTheDocument();
    expect(screen.getByText('Settings')).toBeInTheDocument();
  });

  it('renders no-suggestions state', () => {
    render(<DigestEmptyState variant="no-suggestions" />);

    expect(screen.getByText('No suggestions yet')).toBeInTheDocument();
  });
});

describe('DigestSkeleton', () => {
  it('renders skeleton cards', () => {
    const { container } = render(<DigestSkeleton />);
    const skeletons = container.querySelectorAll('[class*="animate-pulse"]');
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it('has loading role', () => {
    render(<DigestSkeleton />);
    expect(screen.getByRole('status')).toBeInTheDocument();
  });
});

describe('DigestSuggestionCard', () => {
  it('renders suggestion title', () => {
    render(<DigestSuggestionCard suggestion={mockSuggestion} onDismiss={vi.fn()} />);
    expect(screen.getByText('3 issues stale for 7+ days')).toBeInTheDocument();
  });

  it('renders suggestion description', () => {
    render(<DigestSuggestionCard suggestion={mockSuggestion} onDismiss={vi.fn()} />);
    expect(screen.getByText(/have not been updated recently/)).toBeInTheDocument();
  });

  it('renders entity identifier', () => {
    render(<DigestSuggestionCard suggestion={mockSuggestion} onDismiss={vi.fn()} />);
    expect(screen.getByText('PS-42')).toBeInTheDocument();
  });

  it('renders project name', () => {
    render(<DigestSuggestionCard suggestion={mockSuggestion} onDismiss={vi.fn()} />);
    expect(screen.getByText(/Pilot Space/)).toBeInTheDocument();
  });

  it('renders action button', () => {
    render(<DigestSuggestionCard suggestion={mockSuggestion} onDismiss={vi.fn()} />);
    expect(screen.getByText('View issues')).toBeInTheDocument();
  });

  it('calls onDismiss when dismiss button is clicked', () => {
    const handleDismiss = vi.fn();
    render(<DigestSuggestionCard suggestion={mockSuggestion} onDismiss={handleDismiss} />);

    fireEvent.click(screen.getByLabelText('Dismiss suggestion'));
    expect(handleDismiss).toHaveBeenCalledWith(mockSuggestion);
  });

  it('has correct aria-label with human-readable category', () => {
    render(<DigestSuggestionCard suggestion={mockSuggestion} onDismiss={vi.fn()} />);
    const article = screen.getByRole('article');
    expect(article).toHaveAttribute('aria-label', expect.stringContaining('Stale Issues'));
  });
});

describe('DigestPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows no-provider state when aiConfigured is false', () => {
    mockUseWorkspaceDigest.mockReturnValue({
      data: undefined,
      isLoading: false,
      isRefetching: false,
    });

    render(<DigestPanel aiConfigured={false} />);

    expect(screen.getByText('AI not configured')).toBeInTheDocument();
  });

  it('shows skeleton when loading', () => {
    mockUseWorkspaceDigest.mockReturnValue({
      data: undefined,
      isLoading: true,
      isRefetching: false,
    });

    render(<DigestPanel />);

    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('shows empty state when no suggestions', () => {
    mockUseWorkspaceDigest.mockReturnValue({
      data: {
        data: {
          generated_at: new Date().toISOString(),
          generated_by: 'scheduled',
          suggestions: [],
          suggestion_count: 0,
        },
      },
      isLoading: false,
      isRefetching: false,
    });

    render(<DigestPanel />);

    expect(screen.getByText('No suggestions yet')).toBeInTheDocument();
  });

  it('renders suggestions when data is available', () => {
    mockUseWorkspaceDigest.mockReturnValue({
      data: mockDigestResponse,
      isLoading: false,
      isRefetching: false,
    });

    render(<DigestPanel />);

    expect(screen.getByText('3 issues stale for 7+ days')).toBeInTheDocument();
  });

  it('renders AI Insights header', () => {
    mockUseWorkspaceDigest.mockReturnValue({
      data: mockDigestResponse,
      isLoading: false,
      isRefetching: false,
    });

    render(<DigestPanel />);

    expect(screen.getByText('AI Insights')).toBeInTheDocument();
  });

  it('renders last updated timestamp', () => {
    mockUseWorkspaceDigest.mockReturnValue({
      data: mockDigestResponse,
      isLoading: false,
      isRefetching: false,
    });

    render(<DigestPanel />);

    expect(screen.getByText(/Last updated/)).toBeInTheDocument();
  });

  it('renders refresh button', () => {
    mockUseWorkspaceDigest.mockReturnValue({
      data: mockDigestResponse,
      isLoading: false,
      isRefetching: false,
    });

    render(<DigestPanel />);

    expect(screen.getByLabelText('Refresh AI digest')).toBeInTheDocument();
  });

  it('calls dismiss mutation when suggestion is dismissed', () => {
    mockUseWorkspaceDigest.mockReturnValue({
      data: mockDigestResponse,
      isLoading: false,
      isRefetching: false,
    });

    render(<DigestPanel />);

    fireEvent.click(screen.getByLabelText('Dismiss suggestion'));

    expect(mockDismissMutate).toHaveBeenCalledWith(
      expect.objectContaining({
        suggestion_id: 'sug-1',
        category: 'stale_issues',
      })
    );
  });
});

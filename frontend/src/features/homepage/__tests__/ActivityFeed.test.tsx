import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { ActivityCardNote, ActivityCardIssue, HomepageActivityResponse } from '../types';

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

// Mock Supabase for Realtime subscription
vi.mock('@/lib/supabase', () => ({
  supabase: {
    channel: () => ({
      on: vi.fn().mockReturnThis(),
      subscribe: vi.fn().mockReturnThis(),
    }),
    removeChannel: vi.fn(),
  },
}));

// Mock useHomepageActivity hook
const mockUseHomepageActivity = vi.fn();
vi.mock('../hooks/useHomepageActivity', () => ({
  useHomepageActivity: (opts: unknown) => mockUseHomepageActivity(opts),
}));

import { ActivityFeed } from '../components/ActivityFeed/ActivityFeed';
import { NoteActivityCard } from '../components/ActivityFeed/NoteActivityCard';
import { IssueActivityCard } from '../components/ActivityFeed/IssueActivityCard';
import { DayGroupHeader } from '../components/ActivityFeed/DayGroupHeader';
import { ActivityFeedSkeleton } from '../components/ActivityFeed/ActivityFeedSkeleton';

// --- Test data ---

const mockNote: ActivityCardNote = {
  type: 'note',
  id: 'note-1',
  title: 'Sprint Planning Notes',
  project: { id: 'proj-1', name: 'Pilot Space', identifier: 'PS' },
  topics: ['architecture', 'frontend', 'testing'],
  word_count: 420,
  latest_annotation: {
    type: 'suggestion',
    content: 'Consider adding error handling for the edge case when user is not authenticated',
    confidence: 0.85,
  },
  updated_at: new Date().toISOString(),
  is_pinned: false,
};

const mockIssue: ActivityCardIssue = {
  type: 'issue',
  id: 'issue-1',
  identifier: 'PS-42',
  title: 'Fix authentication flow',
  project: { id: 'proj-1', name: 'Pilot Space', identifier: 'PS' },
  state: { name: 'In Progress', color: '#D9853F', group: 'started' },
  priority: 'high',
  assignee: { id: 'user-1', name: 'John Doe', avatar_url: null },
  last_activity: 'Moved to In Progress',
  updated_at: new Date().toISOString(),
};

const mockActivityResponse: HomepageActivityResponse = {
  data: {
    today: [mockNote, mockIssue],
    yesterday: [],
    this_week: [],
  },
  meta: { total: 2, cursor: null, has_more: false },
};

// --- Component Tests ---

describe('DayGroupHeader', () => {
  it('renders label text', () => {
    render(<DayGroupHeader label="Today" />);
    expect(screen.getByText('Today')).toBeInTheDocument();
  });
});

describe('ActivityFeedSkeleton', () => {
  it('renders skeleton cards', () => {
    const { container } = render(<ActivityFeedSkeleton />);
    // Should have multiple skeleton elements
    const skeletons = container.querySelectorAll('[class*="animate-pulse"]');
    expect(skeletons.length).toBeGreaterThan(0);
  });
});

describe('NoteActivityCard', () => {
  it('renders note title', () => {
    render(<NoteActivityCard card={mockNote} workspaceSlug="test-ws" />);
    expect(screen.getByText('Sprint Planning Notes')).toBeInTheDocument();
  });

  it('renders project badge', () => {
    render(<NoteActivityCard card={mockNote} workspaceSlug="test-ws" />);
    expect(screen.getByText('PS')).toBeInTheDocument();
  });

  it('renders topic tags (max 3)', () => {
    render(<NoteActivityCard card={mockNote} workspaceSlug="test-ws" />);
    expect(screen.getByText('architecture')).toBeInTheDocument();
    expect(screen.getByText('frontend')).toBeInTheDocument();
    expect(screen.getByText('testing')).toBeInTheDocument();
  });

  it('renders word count', () => {
    render(<NoteActivityCard card={mockNote} workspaceSlug="test-ws" />);
    expect(screen.getByText(/420/)).toBeInTheDocument();
  });

  it('has correct role and aria-label', () => {
    render(<NoteActivityCard card={mockNote} workspaceSlug="test-ws" />);
    const article = screen.getByRole('article');
    expect(article).toHaveAttribute('aria-label', expect.stringContaining('Sprint Planning Notes'));
  });
});

describe('IssueActivityCard', () => {
  it('renders issue identifier', () => {
    render(<IssueActivityCard card={mockIssue} workspaceSlug="test-ws" />);
    expect(screen.getByText('PS-42')).toBeInTheDocument();
  });

  it('renders issue title', () => {
    render(<IssueActivityCard card={mockIssue} workspaceSlug="test-ws" />);
    expect(screen.getByText('Fix authentication flow')).toBeInTheDocument();
  });

  it('renders state name', () => {
    render(<IssueActivityCard card={mockIssue} workspaceSlug="test-ws" />);
    expect(screen.getByText('In Progress')).toBeInTheDocument();
  });

  it('renders assignee name', () => {
    render(<IssueActivityCard card={mockIssue} workspaceSlug="test-ws" />);
    expect(screen.getByText(/John Doe|JD/)).toBeInTheDocument();
  });

  it('has correct role and aria-label', () => {
    render(<IssueActivityCard card={mockIssue} workspaceSlug="test-ws" />);
    const article = screen.getByRole('article');
    expect(article).toHaveAttribute('aria-label', expect.stringContaining('PS-42'));
  });
});

describe('ActivityFeed', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows skeleton when loading', () => {
    mockUseHomepageActivity.mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
      fetchNextPage: vi.fn(),
      hasNextPage: false,
      isFetchingNextPage: false,
      refetch: vi.fn(),
    });

    const { container } = render(<ActivityFeed workspaceSlug="test-ws" />);
    const skeletons = container.querySelectorAll('[class*="animate-pulse"]');
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it('shows error state with retry button', () => {
    const mockRefetch = vi.fn();
    mockUseHomepageActivity.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
      fetchNextPage: vi.fn(),
      hasNextPage: false,
      isFetchingNextPage: false,
      refetch: mockRefetch,
    });

    render(<ActivityFeed workspaceSlug="test-ws" />);

    expect(screen.getByText('Failed to load activity')).toBeInTheDocument();
    fireEvent.click(screen.getByText('Retry'));
    expect(mockRefetch).toHaveBeenCalledTimes(1);
  });

  it('shows empty state when no data', () => {
    mockUseHomepageActivity.mockReturnValue({
      data: {
        pages: [{ data: {}, meta: { total: 0, cursor: null, has_more: false } }],
      },
      isLoading: false,
      isError: false,
      fetchNextPage: vi.fn(),
      hasNextPage: false,
      isFetchingNextPage: false,
      refetch: vi.fn(),
    });

    render(<ActivityFeed workspaceSlug="test-ws" />);

    expect(screen.getByText(/Your workspace is quiet/)).toBeInTheDocument();
  });

  it('renders day groups with cards', () => {
    mockUseHomepageActivity.mockReturnValue({
      data: {
        pages: [mockActivityResponse],
      },
      isLoading: false,
      isError: false,
      fetchNextPage: vi.fn(),
      hasNextPage: false,
      isFetchingNextPage: false,
      refetch: vi.fn(),
    });

    render(<ActivityFeed workspaceSlug="test-ws" />);

    expect(screen.getByText('Today')).toBeInTheDocument();
    expect(screen.getByText('Sprint Planning Notes')).toBeInTheDocument();
    expect(screen.getByText('PS-42')).toBeInTheDocument();
  });

  it('renders loading indicator when fetching next page', () => {
    mockUseHomepageActivity.mockReturnValue({
      data: {
        pages: [mockActivityResponse],
      },
      isLoading: false,
      isError: false,
      fetchNextPage: vi.fn(),
      hasNextPage: true,
      isFetchingNextPage: true,
      refetch: vi.fn(),
    });

    render(<ActivityFeed workspaceSlug="test-ws" />);

    expect(screen.getByText('Loading more activity')).toBeInTheDocument();
  });
});

/**
 * ActivityTimeline component tests (T040).
 *
 * Verifies loading state, error state with retry, empty state,
 * activity rendering, comment submission, infinite scroll via
 * IntersectionObserver, pagination spinner, and disabled prop.
 */

import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ActivityTimeline } from '../activity-timeline';
import type { Activity } from '@/types';

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

const mockUseActivities = vi.fn();
const mockUseAddComment = vi.fn();

vi.mock('../../hooks/use-activities', () => ({
  useActivities: (...args: unknown[]) => mockUseActivities(...args),
}));

vi.mock('../../hooks/use-add-comment', () => ({
  useAddComment: (...args: unknown[]) => mockUseAddComment(...args),
}));

vi.mock('../activity-entry', () => ({
  ActivityEntry: ({ activity }: { activity: Activity }) => (
    <div data-testid={`activity-${activity.id}`}>{activity.activityType}</div>
  ),
}));

vi.mock('../comment-input', () => ({
  CommentInput: ({
    onSubmit,
    disabled,
  }: {
    onSubmit: (content: string) => void;
    disabled: boolean;
    isSubmitting: boolean;
  }) => (
    <div data-testid="comment-input">
      <button
        data-testid="mock-submit"
        onClick={() => onSubmit('test comment')}
        disabled={disabled}
      >
        Submit
      </button>
    </div>
  ),
}));

// ---------------------------------------------------------------------------
// IntersectionObserver mock
// ---------------------------------------------------------------------------

const mockObserve = vi.fn();
const mockDisconnect = vi.fn();
let intersectionCallback: IntersectionObserverCallback;

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

function createActivity(overrides?: Partial<Activity>): Activity {
  return {
    id: 'act-1',
    activityType: 'comment',
    field: null,
    oldValue: null,
    newValue: null,
    comment: 'Test comment',
    metadata: null,
    createdAt: new Date().toISOString(),
    actor: { id: 'user-1', email: 'john@test.com', displayName: 'John Doe' },
    ...overrides,
  };
}

function createActivitiesPage(activities: Activity[], total = 100) {
  return { activities, total };
}

const defaultActivitiesReturn = {
  data: {
    pages: [createActivitiesPage([createActivity({ id: 'a1' }), createActivity({ id: 'a2' })])],
  },
  fetchNextPage: vi.fn(),
  hasNextPage: false,
  isFetchingNextPage: false,
  isLoading: false,
  isError: false,
  refetch: vi.fn(),
};

const defaultAddCommentReturn = {
  mutate: vi.fn(),
  isPending: false,
};

// ---------------------------------------------------------------------------
// Setup
// ---------------------------------------------------------------------------

beforeEach(() => {
  vi.clearAllMocks();
  mockUseActivities.mockReturnValue({ ...defaultActivitiesReturn });
  mockUseAddComment.mockReturnValue({ ...defaultAddCommentReturn });

  global.IntersectionObserver = vi.fn((callback) => {
    intersectionCallback = callback;
    return {
      observe: mockObserve,
      disconnect: mockDisconnect,
      unobserve: vi.fn(),
      root: null,
      rootMargin: '',
      thresholds: [],
      takeRecords: () => [],
    } as IntersectionObserver;
  }) as unknown as typeof IntersectionObserver;
});

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('ActivityTimeline', () => {
  const defaultProps = { issueId: 'issue-1', workspaceId: 'ws-1' };

  describe('Loading state', () => {
    it('shows loading spinner during initial load', () => {
      mockUseActivities.mockReturnValue({
        ...defaultActivitiesReturn,
        isLoading: true,
        data: undefined,
      });

      render(<ActivityTimeline {...defaultProps} />);

      expect(screen.getByText('Loading activities')).toBeInTheDocument();
      expect(screen.getByText('Activity')).toBeInTheDocument();
    });
  });

  describe('Error state', () => {
    it('shows error state with retry button', () => {
      mockUseActivities.mockReturnValue({
        ...defaultActivitiesReturn,
        isError: true,
        data: undefined,
      });

      render(<ActivityTimeline {...defaultProps} />);

      expect(screen.getByText('Failed to load activities')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Retry' })).toBeInTheDocument();
    });

    it('calls refetch when retry button is clicked', async () => {
      const mockRefetch = vi.fn();
      mockUseActivities.mockReturnValue({
        ...defaultActivitiesReturn,
        isError: true,
        data: undefined,
        refetch: mockRefetch,
      });

      const user = userEvent.setup();
      render(<ActivityTimeline {...defaultProps} />);

      await user.click(screen.getByRole('button', { name: 'Retry' }));
      expect(mockRefetch).toHaveBeenCalledTimes(1);
    });
  });

  describe('Empty state', () => {
    it('shows empty message when no activities', () => {
      mockUseActivities.mockReturnValue({
        ...defaultActivitiesReturn,
        data: { pages: [createActivitiesPage([], 0)] },
      });

      render(<ActivityTimeline {...defaultProps} />);

      expect(screen.getByText('No activity yet')).toBeInTheDocument();
    });
  });

  describe('Activity rendering', () => {
    it('renders activity entries when data is loaded', () => {
      render(<ActivityTimeline {...defaultProps} />);

      expect(screen.getByTestId('activity-a1')).toBeInTheDocument();
      expect(screen.getByTestId('activity-a2')).toBeInTheDocument();
    });

    it('renders activity entries inside a list', () => {
      render(<ActivityTimeline {...defaultProps} />);

      const list = screen.getByRole('list', { name: 'Activity entries' });
      const items = within(list).getAllByRole('listitem');
      expect(items).toHaveLength(2);
    });

    it('flattens multiple pages of activities', () => {
      mockUseActivities.mockReturnValue({
        ...defaultActivitiesReturn,
        data: {
          pages: [
            createActivitiesPage([
              createActivity({ id: 'p1-a1' }),
              createActivity({ id: 'p1-a2' }),
            ]),
            createActivitiesPage([createActivity({ id: 'p2-a1' })]),
          ],
        },
      });

      render(<ActivityTimeline {...defaultProps} />);

      expect(screen.getByTestId('activity-p1-a1')).toBeInTheDocument();
      expect(screen.getByTestId('activity-p1-a2')).toBeInTheDocument();
      expect(screen.getByTestId('activity-p2-a1')).toBeInTheDocument();

      const list = screen.getByRole('list', { name: 'Activity entries' });
      const items = within(list).getAllByRole('listitem');
      expect(items).toHaveLength(3);
    });
  });

  describe('Comment input', () => {
    it('renders CommentInput at the bottom', () => {
      render(<ActivityTimeline {...defaultProps} />);

      expect(screen.getByTestId('comment-input')).toBeInTheDocument();
    });

    it('calls addComment.mutate on comment submission', async () => {
      const mockMutate = vi.fn();
      mockUseAddComment.mockReturnValue({ mutate: mockMutate, isPending: false });

      const user = userEvent.setup();
      render(<ActivityTimeline {...defaultProps} />);

      await user.click(screen.getByTestId('mock-submit'));
      expect(mockMutate).toHaveBeenCalledWith('test comment');
    });

    it('passes disabled prop to CommentInput', () => {
      render(<ActivityTimeline {...defaultProps} disabled />);

      expect(screen.getByTestId('mock-submit')).toBeDisabled();
    });
  });

  describe('Infinite scroll', () => {
    it('creates IntersectionObserver and observes sentinel', () => {
      render(<ActivityTimeline {...defaultProps} />);

      expect(global.IntersectionObserver).toHaveBeenCalledTimes(1);
      expect(mockObserve).toHaveBeenCalledTimes(1);
    });

    it('calls fetchNextPage when sentinel intersects and hasNextPage is true', () => {
      const mockFetchNextPage = vi.fn();
      mockUseActivities.mockReturnValue({
        ...defaultActivitiesReturn,
        hasNextPage: true,
        fetchNextPage: mockFetchNextPage,
      });

      render(<ActivityTimeline {...defaultProps} />);

      intersectionCallback(
        [{ isIntersecting: true } as IntersectionObserverEntry],
        {} as IntersectionObserver
      );

      expect(mockFetchNextPage).toHaveBeenCalledTimes(1);
    });

    it('does NOT call fetchNextPage when hasNextPage is false', () => {
      const mockFetchNextPage = vi.fn();
      mockUseActivities.mockReturnValue({
        ...defaultActivitiesReturn,
        hasNextPage: false,
        fetchNextPage: mockFetchNextPage,
      });

      render(<ActivityTimeline {...defaultProps} />);

      intersectionCallback(
        [{ isIntersecting: true } as IntersectionObserverEntry],
        {} as IntersectionObserver
      );

      expect(mockFetchNextPage).not.toHaveBeenCalled();
    });

    it('shows "Loading more..." spinner during pagination', () => {
      mockUseActivities.mockReturnValue({
        ...defaultActivitiesReturn,
        isFetchingNextPage: true,
      });

      render(<ActivityTimeline {...defaultProps} />);

      expect(screen.getByText('Loading more...')).toBeInTheDocument();
    });

    it('disconnects observer on unmount', () => {
      const { unmount } = render(<ActivityTimeline {...defaultProps} />);

      unmount();

      expect(mockDisconnect).toHaveBeenCalledTimes(1);
    });
  });
});

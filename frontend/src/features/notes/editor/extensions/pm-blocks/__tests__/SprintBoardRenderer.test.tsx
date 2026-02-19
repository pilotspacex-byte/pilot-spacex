/**
 * Tests for SprintBoardRenderer component.
 *
 * SprintBoardRenderer renders a sprint board PM block with:
 * - 6 state-based lanes (FR-049)
 * - AI-proposed state transitions (FR-050)
 * - Read-only fallback (FR-060)
 * - AI insight badge (FR-056–059)
 *
 * @module pm-blocks/__tests__/SprintBoardRenderer.test
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import { SprintBoardRenderer } from '../renderers/SprintBoardRenderer';
import type { SprintBoardData } from '@/services/api/pm-blocks';

// ── Mocks ─────────────────────────────────────────────────────────────────────

vi.mock('@/services/api/pm-blocks', () => ({
  pmBlocksApi: {
    getSprintBoard: vi.fn(),
    listInsights: vi.fn(),
    dismissInsight: vi.fn(),
  },
}));

import { pmBlocksApi } from '@/services/api/pm-blocks';
const mockGetSprintBoard = vi.mocked(pmBlocksApi.getSprintBoard);
const mockListInsights = vi.mocked(pmBlocksApi.listInsights);

// ── Test helpers ──────────────────────────────────────────────────────────────

function makeQueryClient() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
}

function wrapper({ children }: { children: React.ReactNode }) {
  return <QueryClientProvider client={makeQueryClient()}>{children}</QueryClientProvider>;
}

const WORKSPACE_ID = 'ws-123';
const CYCLE_ID = 'cycle-456';

const defaultProps = {
  data: { workspaceId: WORKSPACE_ID, cycleId: CYCLE_ID } as Record<string, unknown>,
  readOnly: false,
  onDataChange: vi.fn(),
  blockType: 'sprint-board' as const,
};

function makeBoardData(overrides: Partial<SprintBoardData> = {}): SprintBoardData {
  return {
    cycleId: CYCLE_ID,
    cycleName: 'Sprint 1',
    totalIssues: 3,
    isReadOnly: false,
    lanes: [
      {
        stateId: 'state-1',
        stateName: 'Todo',
        stateGroup: 'todo',
        count: 2,
        issues: [
          {
            id: 'issue-1',
            identifier: 'PS-1',
            name: 'Feature A',
            priority: 'high',
            stateName: 'Todo',
            stateId: 'state-1',
            labels: [],
          },
          {
            id: 'issue-2',
            identifier: 'PS-2',
            name: 'Feature B',
            priority: 'medium',
            stateName: 'Todo',
            stateId: 'state-1',
            labels: ['frontend'],
          },
        ],
      },
      {
        stateId: 'state-2',
        stateName: 'Done',
        stateGroup: 'done',
        count: 1,
        issues: [
          {
            id: 'issue-3',
            identifier: 'PS-3',
            name: 'Feature C',
            priority: 'low',
            stateName: 'Done',
            stateId: 'state-2',
            labels: [],
          },
        ],
      },
    ],
    ...overrides,
  };
}

beforeEach(() => {
  vi.clearAllMocks();
  mockListInsights.mockResolvedValue([]);
});

// ── Config missing ────────────────────────────────────────────────────────────

describe('SprintBoardRenderer config missing', () => {
  it('shows config prompt when workspaceId is missing', () => {
    render(
      <QueryClientProvider client={makeQueryClient()}>
        <SprintBoardRenderer
          {...defaultProps}
          data={{ cycleId: CYCLE_ID } as Record<string, unknown>}
        />
      </QueryClientProvider>
    );
    expect(screen.getByText(/Configure workspace and cycle/i)).toBeInTheDocument();
  });

  it('shows config prompt when cycleId is missing', () => {
    render(
      <QueryClientProvider client={makeQueryClient()}>
        <SprintBoardRenderer
          {...defaultProps}
          data={{ workspaceId: WORKSPACE_ID } as Record<string, unknown>}
        />
      </QueryClientProvider>
    );
    expect(screen.getByText(/Configure workspace and cycle/i)).toBeInTheDocument();
  });
});

// ── Loading state ─────────────────────────────────────────────────────────────

describe('SprintBoardRenderer loading', () => {
  it('shows loading spinner while data is fetching', async () => {
    mockGetSprintBoard.mockReturnValue(new Promise(() => {})); // never resolves
    render(
      <QueryClientProvider client={makeQueryClient()}>
        <SprintBoardRenderer {...defaultProps} />
      </QueryClientProvider>
    );
    await waitFor(() => {
      expect(screen.getByText(/Loading sprint board/i)).toBeInTheDocument();
    });
  });
});

// ── Board lanes (FR-049) ──────────────────────────────────────────────────────

describe('SprintBoardRenderer lane rendering (FR-049)', () => {
  it('renders the sprint board with cycle name in header', async () => {
    mockGetSprintBoard.mockResolvedValue(makeBoardData());
    render(<SprintBoardRenderer {...defaultProps} />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText('Sprint 1')).toBeInTheDocument();
    });
  });

  it('renders lane columns for each state', async () => {
    mockGetSprintBoard.mockResolvedValue(makeBoardData());
    render(<SprintBoardRenderer {...defaultProps} />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText('Todo')).toBeInTheDocument();
      expect(screen.getByText('Done')).toBeInTheDocument();
    });
  });

  it('renders issue cards with identifiers', async () => {
    mockGetSprintBoard.mockResolvedValue(makeBoardData());
    render(<SprintBoardRenderer {...defaultProps} />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText('PS-1')).toBeInTheDocument();
      expect(screen.getByText('PS-2')).toBeInTheDocument();
      expect(screen.getByText('PS-3')).toBeInTheDocument();
    });
  });

  it('renders issue names', async () => {
    mockGetSprintBoard.mockResolvedValue(makeBoardData());
    render(<SprintBoardRenderer {...defaultProps} />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText('Feature A')).toBeInTheDocument();
    });
  });

  it('renders total issue count', async () => {
    mockGetSprintBoard.mockResolvedValue(makeBoardData({ totalIssues: 3 }));
    render(<SprintBoardRenderer {...defaultProps} />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText(/3 issues/)).toBeInTheDocument();
    });
  });

  it('shows "Empty" placeholder for lanes with no issues', async () => {
    const board = makeBoardData();
    board.lanes.push({
      stateId: 'state-3',
      stateName: 'In Progress',
      stateGroup: 'in_progress',
      count: 0,
      issues: [],
    });
    mockGetSprintBoard.mockResolvedValue(board);
    render(<SprintBoardRenderer {...defaultProps} />, { wrapper });

    await waitFor(() => {
      expect(screen.getAllByText('Empty').length).toBeGreaterThan(0);
    });
  });
});

// ── Read-only fallback (FR-060) ───────────────────────────────────────────────

describe('SprintBoardRenderer read-only fallback (FR-060)', () => {
  it('shows read-only badge when board isReadOnly', async () => {
    mockGetSprintBoard.mockResolvedValue(makeBoardData({ isReadOnly: true }));
    render(<SprintBoardRenderer {...defaultProps} />, { wrapper });

    await waitFor(() => {
      expect(screen.getByLabelText('Read-only mode')).toBeInTheDocument();
    });
  });

  it('hides Move button on issue cards when readOnly prop true', async () => {
    mockGetSprintBoard.mockResolvedValue(makeBoardData());
    render(
      <QueryClientProvider client={makeQueryClient()}>
        <SprintBoardRenderer {...defaultProps} readOnly />
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(screen.queryByText('Move →')).not.toBeInTheDocument();
    });
  });
});

// ── Refresh ───────────────────────────────────────────────────────────────────

describe('SprintBoardRenderer refresh', () => {
  it('renders refresh button', async () => {
    mockGetSprintBoard.mockResolvedValue(makeBoardData());
    render(<SprintBoardRenderer {...defaultProps} />, { wrapper });

    await waitFor(() => {
      expect(screen.getByLabelText('Refresh sprint board')).toBeInTheDocument();
    });
  });
});

// ── Error state ───────────────────────────────────────────────────────────────

describe('SprintBoardRenderer error state', () => {
  it('shows error message when API fails', async () => {
    mockGetSprintBoard.mockRejectedValue(new Error('Network error'));
    render(<SprintBoardRenderer {...defaultProps} />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText(/Failed to load sprint board/)).toBeInTheDocument();
    });
  });

  it('shows retry link on error', async () => {
    mockGetSprintBoard.mockRejectedValue(new Error('Network error'));
    render(<SprintBoardRenderer {...defaultProps} />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText('Retry')).toBeInTheDocument();
    });
  });
});

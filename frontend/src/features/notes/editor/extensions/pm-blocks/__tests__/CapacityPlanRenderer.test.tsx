/**
 * Tests for CapacityPlanRenderer component.
 *
 * CapacityPlanRenderer renders a capacity plan PM block with:
 * - Available vs committed hours per member (FR-053)
 * - Utilization bars with color coding
 * - Over-allocation detection and badge
 * - Team summary row
 * - AI insight badge (FR-056–059)
 *
 * @module pm-blocks/__tests__/CapacityPlanRenderer.test
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import { CapacityPlanRenderer } from '../renderers/CapacityPlanRenderer';
import type { CapacityPlanData } from '@/services/api/pm-blocks';

// ── Mocks ─────────────────────────────────────────────────────────────────────

vi.mock('@/services/api/pm-blocks', () => ({
  pmBlocksApi: {
    getCapacityPlan: vi.fn(),
    listInsights: vi.fn(),
    dismissInsight: vi.fn(),
  },
}));

import { pmBlocksApi } from '@/services/api/pm-blocks';
const mockGetCapacityPlan = vi.mocked(pmBlocksApi.getCapacityPlan);
const mockListInsights = vi.mocked(pmBlocksApi.listInsights);

// ── Helpers ───────────────────────────────────────────────────────────────────

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
  blockType: 'capacity-plan' as const,
};

function makePlanData(overrides: Partial<CapacityPlanData> = {}): CapacityPlanData {
  return {
    cycleId: CYCLE_ID,
    cycleName: 'Sprint 1',
    teamAvailable: 80,
    teamCommitted: 65,
    teamUtilizationPct: 81.25,
    hasData: true,
    members: [
      {
        userId: 'user-1',
        displayName: 'Alice',
        avatarUrl: undefined,
        availableHours: 40,
        committedHours: 35,
        utilizationPct: 87.5,
        isOverAllocated: false,
      },
      {
        userId: 'user-2',
        displayName: 'Bob',
        avatarUrl: undefined,
        availableHours: 40,
        committedHours: 30,
        utilizationPct: 75,
        isOverAllocated: false,
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

describe('CapacityPlanRenderer config missing', () => {
  it('shows config prompt when workspaceId missing', () => {
    render(
      <QueryClientProvider client={makeQueryClient()}>
        <CapacityPlanRenderer
          {...defaultProps}
          data={{ cycleId: CYCLE_ID } as Record<string, unknown>}
        />
      </QueryClientProvider>
    );
    expect(screen.getByText(/Configure workspace and cycle/i)).toBeInTheDocument();
  });
});

// ── Loading ───────────────────────────────────────────────────────────────────

describe('CapacityPlanRenderer loading', () => {
  it('shows loading spinner while fetching', async () => {
    mockGetCapacityPlan.mockReturnValue(new Promise(() => {}));
    render(
      <QueryClientProvider client={makeQueryClient()}>
        <CapacityPlanRenderer {...defaultProps} />
      </QueryClientProvider>
    );
    await waitFor(() => {
      expect(screen.getByText(/Loading capacity plan/i)).toBeInTheDocument();
    });
  });
});

// ── Member rows (FR-053) ──────────────────────────────────────────────────────

describe('CapacityPlanRenderer member rows (FR-053)', () => {
  it('renders testid for each member', async () => {
    mockGetCapacityPlan.mockResolvedValue(makePlanData());
    render(<CapacityPlanRenderer {...defaultProps} />, { wrapper });

    await waitFor(() => {
      expect(screen.getByTestId('member-row-user-1')).toBeInTheDocument();
      expect(screen.getByTestId('member-row-user-2')).toBeInTheDocument();
    });
  });

  it('renders member display names', async () => {
    mockGetCapacityPlan.mockResolvedValue(makePlanData());
    render(<CapacityPlanRenderer {...defaultProps} />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText('Alice')).toBeInTheDocument();
      expect(screen.getByText('Bob')).toBeInTheDocument();
    });
  });

  it('renders committed/available hours for each member', async () => {
    mockGetCapacityPlan.mockResolvedValue(makePlanData());
    render(<CapacityPlanRenderer {...defaultProps} />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText('35h / 40h')).toBeInTheDocument();
      expect(screen.getByText('30h / 40h')).toBeInTheDocument();
    });
  });

  it('renders utilization percentage', async () => {
    mockGetCapacityPlan.mockResolvedValue(makePlanData());
    render(<CapacityPlanRenderer {...defaultProps} />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText('88%')).toBeInTheDocument(); // 87.5 rounded
    });
  });

  it('sorts members by utilization descending', async () => {
    const plan = makePlanData();
    // Alice=87.5%, Bob=75% → Alice should appear first
    mockGetCapacityPlan.mockResolvedValue(plan);
    render(<CapacityPlanRenderer {...defaultProps} />, { wrapper });

    await waitFor(() => {
      const rows = screen.getAllByText(/\d+h \/ \d+h/);
      expect(rows[0]).toHaveTextContent('35h / 40h'); // Alice
    });
  });
});

// ── Over-allocation ───────────────────────────────────────────────────────────

describe('CapacityPlanRenderer over-allocation', () => {
  it('shows over-allocated badge in header when member is over-allocated', async () => {
    const plan = makePlanData({
      members: [
        {
          userId: 'user-1',
          displayName: 'Alice',
          availableHours: 40,
          committedHours: 50,
          utilizationPct: 125,
          isOverAllocated: true,
        },
      ],
    });
    mockGetCapacityPlan.mockResolvedValue(plan);
    render(<CapacityPlanRenderer {...defaultProps} />, { wrapper });

    await waitFor(() => {
      expect(screen.getByLabelText('1 over-allocated')).toBeInTheDocument();
    });
  });

  it('does not show over-allocated badge when no members over-allocated', async () => {
    mockGetCapacityPlan.mockResolvedValue(makePlanData());
    render(<CapacityPlanRenderer {...defaultProps} />, { wrapper });

    await waitFor(() => {
      expect(screen.queryByText(/over-allocated/)).not.toBeInTheDocument();
    });
  });
});

// ── No data ───────────────────────────────────────────────────────────────────

describe('CapacityPlanRenderer no data', () => {
  it('shows no data message when hasData is false', async () => {
    mockGetCapacityPlan.mockResolvedValue(makePlanData({ hasData: false }));
    render(<CapacityPlanRenderer {...defaultProps} />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText(/No capacity data available/i)).toBeInTheDocument();
    });
  });
});

// ── Error state ───────────────────────────────────────────────────────────────

describe('CapacityPlanRenderer error', () => {
  it('shows error message when API fails', async () => {
    mockGetCapacityPlan.mockRejectedValue(new Error('500'));
    render(<CapacityPlanRenderer {...defaultProps} />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText(/Failed to load capacity plan/)).toBeInTheDocument();
    });
  });
});

// ── Team summary ──────────────────────────────────────────────────────────────

describe('CapacityPlanRenderer team summary', () => {
  it('renders team total available and committed hours', async () => {
    mockGetCapacityPlan.mockResolvedValue(makePlanData({ teamAvailable: 80, teamCommitted: 65 }));
    render(<CapacityPlanRenderer {...defaultProps} />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText('65h')).toBeInTheDocument();
      expect(screen.getByText('/ 80h')).toBeInTheDocument();
    });
  });
});

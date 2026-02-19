/**
 * Tests for DependencyMapRenderer component.
 *
 * DependencyMapRenderer renders dependency map PM block with:
 * - DAG with critical path highlighting (FR-051)
 * - Zoom/pan controls (FR-052)
 * - Circular dependency warning (FR-051)
 * - AI insight badge (FR-056–059)
 *
 * @module pm-blocks/__tests__/DependencyMapRenderer.test
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import userEvent from '@testing-library/user-event';

import { DependencyMapRenderer } from '../renderers/DependencyMapRenderer';
import type { DependencyMapData } from '@/services/api/pm-blocks';

// ── Mocks ─────────────────────────────────────────────────────────────────────

vi.mock('@/services/api/pm-blocks', () => ({
  pmBlocksApi: {
    getDependencyMap: vi.fn(),
    listInsights: vi.fn(),
    dismissInsight: vi.fn(),
  },
}));

import { pmBlocksApi } from '@/services/api/pm-blocks';
const mockGetDependencyMap = vi.mocked(pmBlocksApi.getDependencyMap);
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
  blockType: 'dependency-map' as const,
};

function makeMapData(overrides: Partial<DependencyMapData> = {}): DependencyMapData {
  return {
    nodes: [
      {
        id: 'node-1',
        identifier: 'PS-1',
        name: 'Feature A',
        state: 'todo',
        stateGroup: 'unstarted',
      },
      {
        id: 'node-2',
        identifier: 'PS-2',
        name: 'Feature B',
        state: 'todo',
        stateGroup: 'unstarted',
      },
      {
        id: 'node-3',
        identifier: 'PS-3',
        name: 'Feature C',
        state: 'done',
        stateGroup: 'completed',
      },
    ],
    edges: [
      { sourceId: 'node-1', targetId: 'node-2', isCritical: false },
      { sourceId: 'node-2', targetId: 'node-3', isCritical: true },
    ],
    criticalPath: ['node-2', 'node-3'],
    circularDeps: [],
    hasCircular: false,
    ...overrides,
  };
}

beforeEach(() => {
  vi.clearAllMocks();
  mockListInsights.mockResolvedValue([]);
});

// ── Config missing ────────────────────────────────────────────────────────────

describe('DependencyMapRenderer config missing', () => {
  it('shows config prompt when workspaceId missing', () => {
    render(
      <QueryClientProvider client={makeQueryClient()}>
        <DependencyMapRenderer
          {...defaultProps}
          data={{ cycleId: CYCLE_ID } as Record<string, unknown>}
        />
      </QueryClientProvider>
    );
    expect(screen.getByText(/Configure workspace and cycle/i)).toBeInTheDocument();
  });
});

// ── Loading ───────────────────────────────────────────────────────────────────

describe('DependencyMapRenderer loading', () => {
  it('shows loading while fetching', async () => {
    mockGetDependencyMap.mockReturnValue(new Promise(() => {}));
    render(
      <QueryClientProvider client={makeQueryClient()}>
        <DependencyMapRenderer {...defaultProps} />
      </QueryClientProvider>
    );
    await waitFor(() => {
      expect(screen.getByText(/Loading dependency map/i)).toBeInTheDocument();
    });
  });
});

// ── DAG rendering (FR-051) ────────────────────────────────────────────────────

describe('DependencyMapRenderer DAG rendering (FR-051)', () => {
  it('renders the dependency map testid', async () => {
    mockGetDependencyMap.mockResolvedValue(makeMapData());
    render(<DependencyMapRenderer {...defaultProps} />, { wrapper });

    await waitFor(() => {
      expect(screen.getByTestId('dependency-map-renderer')).toBeInTheDocument();
    });
  });

  it('renders node and edge counts', async () => {
    mockGetDependencyMap.mockResolvedValue(makeMapData());
    render(<DependencyMapRenderer {...defaultProps} />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText(/3 issues/)).toBeInTheDocument();
      expect(screen.getByText(/2 dependencies/)).toBeInTheDocument();
    });
  });

  it('shows critical path issue count', async () => {
    mockGetDependencyMap.mockResolvedValue(makeMapData());
    render(<DependencyMapRenderer {...defaultProps} />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText(/Critical path: 2 issues/)).toBeInTheDocument();
    });
  });

  it('renders SVG DAG canvas', async () => {
    mockGetDependencyMap.mockResolvedValue(makeMapData());
    const { container } = render(<DependencyMapRenderer {...defaultProps} />, { wrapper });

    await waitFor(() => {
      expect(container.querySelector('svg')).toBeInTheDocument();
    });
  });

  it('renders node identifiers in SVG', async () => {
    mockGetDependencyMap.mockResolvedValue(makeMapData());
    render(<DependencyMapRenderer {...defaultProps} />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText('PS-1')).toBeInTheDocument();
      expect(screen.getByText('PS-2')).toBeInTheDocument();
      expect(screen.getByText('PS-3')).toBeInTheDocument();
    });
  });
});

// ── Circular dependency warning ───────────────────────────────────────────────

describe('DependencyMapRenderer circular dependency warning', () => {
  it('shows circular dependency warning when hasCircular=true', async () => {
    mockGetDependencyMap.mockResolvedValue(
      makeMapData({
        hasCircular: true,
        circularDeps: [['PS-1', 'PS-2', 'PS-1']],
      })
    );
    render(<DependencyMapRenderer {...defaultProps} />, { wrapper });

    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument();
      expect(screen.getByText(/Circular dependency detected/)).toBeInTheDocument();
    });
  });

  it('does not show warning when hasCircular=false', async () => {
    mockGetDependencyMap.mockResolvedValue(makeMapData({ hasCircular: false }));
    render(<DependencyMapRenderer {...defaultProps} />, { wrapper });

    await waitFor(() => {
      expect(screen.queryByText(/Circular dependency detected/)).not.toBeInTheDocument();
    });
  });
});

// ── Zoom controls (FR-052) ────────────────────────────────────────────────────

describe('DependencyMapRenderer zoom controls (FR-052)', () => {
  it('renders zoom in button', async () => {
    mockGetDependencyMap.mockResolvedValue(makeMapData());
    render(<DependencyMapRenderer {...defaultProps} />, { wrapper });

    await waitFor(() => {
      expect(screen.getByLabelText('Zoom in')).toBeInTheDocument();
    });
  });

  it('renders zoom out button', async () => {
    mockGetDependencyMap.mockResolvedValue(makeMapData());
    render(<DependencyMapRenderer {...defaultProps} />, { wrapper });

    await waitFor(() => {
      expect(screen.getByLabelText('Zoom out')).toBeInTheDocument();
    });
  });

  it('renders reset view button', async () => {
    mockGetDependencyMap.mockResolvedValue(makeMapData());
    render(<DependencyMapRenderer {...defaultProps} />, { wrapper });

    await waitFor(() => {
      expect(screen.getByLabelText('Reset view')).toBeInTheDocument();
    });
  });

  it('shows default zoom level 100%', async () => {
    mockGetDependencyMap.mockResolvedValue(makeMapData());
    render(<DependencyMapRenderer {...defaultProps} />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText('100%')).toBeInTheDocument();
    });
  });

  it('increments zoom on zoom in click', async () => {
    const user = userEvent.setup();
    mockGetDependencyMap.mockResolvedValue(makeMapData());
    render(<DependencyMapRenderer {...defaultProps} />, { wrapper });

    await waitFor(() => {
      expect(screen.getByLabelText('Zoom in')).toBeInTheDocument();
    });

    await user.click(screen.getByLabelText('Zoom in'));
    expect(screen.getByText('115%')).toBeInTheDocument();
  });

  it('decrements zoom on zoom out click', async () => {
    const user = userEvent.setup();
    mockGetDependencyMap.mockResolvedValue(makeMapData());
    render(<DependencyMapRenderer {...defaultProps} />, { wrapper });

    await waitFor(() => {
      expect(screen.getByLabelText('Zoom out')).toBeInTheDocument();
    });

    await user.click(screen.getByLabelText('Zoom out'));
    expect(screen.getByText('85%')).toBeInTheDocument();
  });

  it('resets zoom to 100% on reset view click', async () => {
    const user = userEvent.setup();
    mockGetDependencyMap.mockResolvedValue(makeMapData());
    render(<DependencyMapRenderer {...defaultProps} />, { wrapper });

    await waitFor(() => {
      expect(screen.getByLabelText('Zoom in')).toBeInTheDocument();
    });

    await user.click(screen.getByLabelText('Zoom in'));
    expect(screen.getByText('115%')).toBeInTheDocument();
    await user.click(screen.getByLabelText('Reset view'));
    expect(screen.getByText('100%')).toBeInTheDocument();
  });
});

// ── Legend ────────────────────────────────────────────────────────────────────

describe('DependencyMapRenderer legend', () => {
  it('shows legend with status categories', async () => {
    mockGetDependencyMap.mockResolvedValue(makeMapData());
    render(<DependencyMapRenderer {...defaultProps} />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText('Critical path')).toBeInTheDocument();
      expect(screen.getByText('Completed')).toBeInTheDocument();
      expect(screen.getByText('In progress')).toBeInTheDocument();
      expect(screen.getByText('Unstarted')).toBeInTheDocument();
    });
  });
});

// ── Error state ───────────────────────────────────────────────────────────────

describe('DependencyMapRenderer error', () => {
  it('shows error when API fails', async () => {
    mockGetDependencyMap.mockRejectedValue(new Error('500'));
    render(<DependencyMapRenderer {...defaultProps} />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText(/Failed to load dependency map/)).toBeInTheDocument();
    });
  });
});

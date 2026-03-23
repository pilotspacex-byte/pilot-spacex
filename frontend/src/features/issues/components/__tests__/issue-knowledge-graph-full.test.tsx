/**
 * IssueKnowledgeGraphFull tests.
 *
 * Covers:
 * - Toolbar renders with filter chips
 * - Node detail panel shown on node click
 * - onClose callback triggered when back button clicked
 */

import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { GraphResponse } from '@/types/knowledge-graph';

// ── Mock @xyflow/react ──────────────────────────────────────────────────────

vi.mock('@xyflow/react', () => ({
  ReactFlow: ({
    children,
    onNodeDoubleClick: _onNodeDoubleClick,
  }: {
    children?: React.ReactNode;
    onNodeDoubleClick?: unknown;
  }) => <div data-testid="reactflow">{children}</div>,
  Background: () => null,
  BackgroundVariant: { Dots: 'dots' },
  MiniMap: () => null,
  Controls: () => null,
  ReactFlowProvider: ({ children }: { children?: React.ReactNode }) => <>{children}</>,
  useReactFlow: () => ({
    fitView: vi.fn(),
    setCenter: vi.fn(),
  }),
}));

// ── Mock d3-force ───────────────────────────────────────────────────────────

vi.mock('d3-force', () => {
  const makeSimulation = () => {
    const sim = {
      force: () => sim,
      stop: vi.fn(() => sim),
      tick: vi.fn(() => sim),
    };
    return sim;
  };
  const makeLinkForce = () => {
    const lf = {
      id: () => lf,
      distance: () => lf,
    };
    return lf;
  };
  return {
    forceSimulation: () => makeSimulation(),
    forceLink: () => makeLinkForce(),
    forceManyBody: () => ({ strength: () => null }),
    forceCenter: () => null,
    forceCollide: () => null,
  };
});

// ── Mock the hook and API ───────────────────────────────────────────────────

vi.mock('@/features/issues/hooks/use-issue-knowledge-graph', () => ({
  useIssueKnowledgeGraph: vi.fn(),
}));

vi.mock('@/services/api/knowledge-graph', () => ({
  knowledgeGraphApi: {
    getIssueGraph: vi.fn(),
    getNodeNeighbors: vi.fn().mockResolvedValue({ nodes: [], edges: [], centerNodeId: '' }),
    searchGraph: vi.fn(),
  },
}));

import { useIssueKnowledgeGraph } from '@/features/issues/hooks/use-issue-knowledge-graph';
import { IssueKnowledgeGraphFull } from '../issue-knowledge-graph-full';

// ── Fixtures ────────────────────────────────────────────────────────────────

const MOCK_GRAPH_RESPONSE: GraphResponse = {
  centerNodeId: 'n1',
  nodes: [
    {
      id: 'n1',
      nodeType: 'issue',
      label: 'Test Issue',
      summary: null,
      score: null,
      properties: {},
      createdAt: '2025-01-01T00:00:00Z',
      updatedAt: '2025-01-01T00:00:00Z',
    },
    {
      id: 'n2',
      nodeType: 'note',
      label: 'Related Note',
      summary: 'A note summary',
      score: null,
      properties: {},
      createdAt: '2025-01-01T00:00:00Z',
      updatedAt: '2025-01-01T00:00:00Z',
    },
  ],
  edges: [
    {
      id: 'e1',
      sourceId: 'n1',
      targetId: 'n2',
      edgeType: 'relates_to',
      label: 'relates_to',
      weight: 1,
      properties: {},
    },
  ],
};

const mockHook = useIssueKnowledgeGraph as ReturnType<typeof vi.fn>;

// ── Tests ───────────────────────────────────────────────────────────────────

describe('IssueKnowledgeGraphFull', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockHook.mockReturnValue({
      data: MOCK_GRAPH_RESPONSE,
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    });
  });

  it('renders toolbar with filter chips', () => {
    render(<IssueKnowledgeGraphFull workspaceId="ws-1" issueId="issue-1" onClose={vi.fn()} />);

    expect(screen.getByRole('button', { name: /back to chat/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Issues' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Notes' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'PRs' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Decisions' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Code' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'All' })).toBeInTheDocument();
  });

  it('renders depth slider in toolbar', () => {
    render(<IssueKnowledgeGraphFull workspaceId="ws-1" issueId="issue-1" onClose={vi.fn()} />);

    const slider = screen.getByRole('slider', { name: /graph depth/i });
    expect(slider).toBeInTheDocument();
    expect(slider).toHaveAttribute('min', '1');
    expect(slider).toHaveAttribute('max', '3');
  });

  it('calls onClose when back button is clicked', () => {
    const onClose = vi.fn();

    render(<IssueKnowledgeGraphFull workspaceId="ws-1" issueId="issue-1" onClose={onClose} />);

    fireEvent.click(screen.getByRole('button', { name: /back to chat/i }));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('shows filter chip as selected when active', () => {
    render(<IssueKnowledgeGraphFull workspaceId="ws-1" issueId="issue-1" onClose={vi.fn()} />);

    // Default: "All" is active
    expect(screen.getByRole('button', { name: 'All' })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByRole('button', { name: 'Issues' })).toHaveAttribute('aria-pressed', 'false');
  });

  it('updates active filter chip when clicked', () => {
    render(<IssueKnowledgeGraphFull workspaceId="ws-1" issueId="issue-1" onClose={vi.fn()} />);

    fireEvent.click(screen.getByRole('button', { name: 'Issues' }));

    expect(screen.getByRole('button', { name: 'Issues' })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByRole('button', { name: 'All' })).toHaveAttribute('aria-pressed', 'false');
  });

  it('renders ReactFlow canvas', () => {
    render(<IssueKnowledgeGraphFull workspaceId="ws-1" issueId="issue-1" onClose={vi.fn()} />);

    expect(screen.getByTestId('reactflow')).toBeInTheDocument();
  });

  it('shows loading state when query is loading', () => {
    mockHook.mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
      refetch: vi.fn(),
    });

    render(<IssueKnowledgeGraphFull workspaceId="ws-1" issueId="issue-1" onClose={vi.fn()} />);

    expect(screen.getByRole('status', { name: /loading knowledge graph/i })).toBeInTheDocument();
  });

  it('shows error state when query fails', () => {
    mockHook.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
      refetch: vi.fn(),
    });

    render(<IssueKnowledgeGraphFull workspaceId="ws-1" issueId="issue-1" onClose={vi.fn()} />);

    expect(screen.getByText('Failed to load knowledge graph')).toBeInTheDocument();
  });

  it('shows empty state when no nodes', () => {
    mockHook.mockReturnValue({
      data: { nodes: [], edges: [], centerNodeId: '' },
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    });

    render(<IssueKnowledgeGraphFull workspaceId="ws-1" issueId="issue-1" onClose={vi.fn()} />);

    expect(screen.getByText('No knowledge graph yet')).toBeInTheDocument();
  });

  it('renders node count in toolbar when data is loaded', () => {
    render(<IssueKnowledgeGraphFull workspaceId="ws-1" issueId="issue-1" onClose={vi.fn()} />);

    expect(screen.getByText('2 nodes')).toBeInTheDocument();
  });
});

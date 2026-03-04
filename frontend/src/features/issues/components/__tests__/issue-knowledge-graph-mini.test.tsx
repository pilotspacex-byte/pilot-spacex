/**
 * IssueKnowledgeGraphMini tests.
 *
 * Covers:
 * - Loading skeleton shown when query is loading
 * - Empty state shown when data has no nodes
 * - Node count rendered in section header
 * - onExpandFullView callback triggered when button clicked
 */

import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { GraphResponse } from '@/types/knowledge-graph';

// ── Mock @xyflow/react ──────────────────────────────────────────────────────

vi.mock('@xyflow/react', () => ({
  ReactFlow: ({ children }: { children?: React.ReactNode }) => (
    <div data-testid="reactflow">{children}</div>
  ),
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

// ── Mock the hook ───────────────────────────────────────────────────────────

vi.mock('@/features/issues/hooks/use-issue-knowledge-graph', () => ({
  useIssueKnowledgeGraph: vi.fn(),
}));

import { useIssueKnowledgeGraph } from '@/features/issues/hooks/use-issue-knowledge-graph';
import { IssueKnowledgeGraphMini } from '../issue-knowledge-graph-mini';

// ── Fixtures ────────────────────────────────────────────────────────────────

const MOCK_GRAPH_RESPONSE: GraphResponse = {
  centerNodeId: 'n1',
  nodes: [
    {
      id: 'n1',
      nodeType: 'issue',
      label: 'Test Issue',
      properties: {},
      createdAt: '2025-01-01T00:00:00Z',
    },
    {
      id: 'n2',
      nodeType: 'note',
      label: 'Related Note',
      properties: {},
      createdAt: '2025-01-01T00:00:00Z',
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
    },
  ],
};

const mockHook = useIssueKnowledgeGraph as ReturnType<typeof vi.fn>;

// ── Tests ───────────────────────────────────────────────────────────────────

describe('IssueKnowledgeGraphMini', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders loading skeleton when query is loading', () => {
    mockHook.mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
      refetch: vi.fn(),
    });

    render(
      <IssueKnowledgeGraphMini workspaceId="ws-1" issueId="issue-1" onExpandFullView={vi.fn()} />
    );

    expect(screen.getByRole('status', { name: /loading knowledge graph/i })).toBeInTheDocument();
  });

  it('renders empty state when data has no nodes', () => {
    mockHook.mockReturnValue({
      data: { nodes: [], edges: [], centerNodeId: '' },
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    });

    render(
      <IssueKnowledgeGraphMini workspaceId="ws-1" issueId="issue-1" onExpandFullView={vi.fn()} />
    );

    expect(screen.getByText('No knowledge graph yet')).toBeInTheDocument();
  });

  it('renders node count in section header', () => {
    mockHook.mockReturnValue({
      data: MOCK_GRAPH_RESPONSE,
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    });

    render(
      <IssueKnowledgeGraphMini workspaceId="ws-1" issueId="issue-1" onExpandFullView={vi.fn()} />
    );

    // CollapsibleSection renders count badge with node count (2)
    expect(screen.getByText('2')).toBeInTheDocument();
  });

  it('calls onExpandFullView when expand button is clicked', () => {
    mockHook.mockReturnValue({
      data: MOCK_GRAPH_RESPONSE,
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    });

    const onExpandFullView = vi.fn();

    render(
      <IssueKnowledgeGraphMini
        workspaceId="ws-1"
        issueId="issue-1"
        onExpandFullView={onExpandFullView}
      />
    );

    const expandBtn = screen.getByRole('button', { name: /expand full.*view/i });
    fireEvent.click(expandBtn);

    expect(onExpandFullView).toHaveBeenCalledTimes(1);
  });

  it('renders error state when query fails', () => {
    mockHook.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
      refetch: vi.fn(),
    });

    render(
      <IssueKnowledgeGraphMini workspaceId="ws-1" issueId="issue-1" onExpandFullView={vi.fn()} />
    );

    expect(screen.getByText('Failed to load knowledge graph')).toBeInTheDocument();
  });

  it('renders ReactFlow canvas when data is present', () => {
    mockHook.mockReturnValue({
      data: MOCK_GRAPH_RESPONSE,
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    });

    render(
      <IssueKnowledgeGraphMini workspaceId="ws-1" issueId="issue-1" onExpandFullView={vi.fn()} />
    );

    expect(screen.getByTestId('reactflow')).toBeInTheDocument();
  });
});

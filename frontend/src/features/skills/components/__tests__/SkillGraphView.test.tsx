/**
 * Tests for SkillGraphView (Phase 92 Plan 02 Task 3).
 *
 * Branches under test:
 *  1. Pending → skeleton (no ReactFlow mount).
 *  2. Error → GraphErrorState; Reload calls catalog.refetch.
 *  3. Empty graph → GraphEmptyState.
 *  4. Data → ReactFlow mounted with nodeTypes registered.
 *  5. Sibling-div role="application" + tabIndex=0 (NOT on RF root) per
 *     UI-SPEC Design-Debt #5.
 *  6. Aria-label verbatim (singular/plural).
 *  7. nodesDraggable={false} + proOptions.hideAttribution=true.
 *  8. miniMapNodeColor returns violet for skill, neutral for file.
 *  9. ReactFlow root does NOT have role="application".
 */

import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { UseQueryResult } from '@tanstack/react-query';
import type { Skill } from '@/types/skill';
import type { ApiError } from '@/services/api/client';
import type {
  UseSkillGraphDataResult,
  UseSkillGraphLayoutResult,
} from '../../hooks';

// ── Mocks ───────────────────────────────────────────────────────────────────

// Capture every prop ReactFlow is rendered with so we can assert later.
const reactFlowSpy = vi.fn();
const miniMapSpy = vi.fn();

vi.mock('@xyflow/react', () => ({
  ReactFlow: (props: Record<string, unknown>) => {
    reactFlowSpy(props);
    return (
      <div data-testid="react-flow">
        {props.children as React.ReactNode}
      </div>
    );
  },
  Background: () => <div data-testid="rf-background" />,
  Controls: () => <div data-testid="rf-controls" />,
  MiniMap: (props: Record<string, unknown>) => {
    miniMapSpy(props);
    return <div data-testid="rf-minimap" />;
  },
  Panel: ({ children }: { children?: React.ReactNode }) => (
    <div data-testid="rf-panel">{children}</div>
  ),
  ReactFlowProvider: ({ children }: { children?: React.ReactNode }) => (
    <>{children}</>
  ),
  Handle: () => null,
  Position: { Top: 'top', Right: 'right', Bottom: 'bottom', Left: 'left' },
  MarkerType: { ArrowClosed: 'arrowclosed' },
  BackgroundVariant: { Dots: 'dots' },
}));

const mockUseSkillGraphData = vi.fn();
const mockUseSkillGraphLayout = vi.fn();

vi.mock('../../hooks/useSkillGraphData', () => ({
  useSkillGraphData: () => mockUseSkillGraphData(),
}));
vi.mock('../../hooks/useSkillGraphLayout', () => ({
  useSkillGraphLayout: (graph: unknown) => mockUseSkillGraphLayout(graph),
}));

// Imports must come AFTER mocks.
import { SkillGraphView } from '../SkillGraphView';
import { miniMapNodeColor } from '../SkillGraphView';

// ── Helpers ─────────────────────────────────────────────────────────────────

const mockRefetch = vi.fn();

function makeCatalog(
  overrides: Partial<UseQueryResult<Skill[], ApiError>>,
): UseQueryResult<Skill[], ApiError> {
  return {
    data: undefined,
    error: null,
    isError: false,
    isPending: false,
    isLoading: false,
    isSuccess: false,
    isFetching: false,
    fetchStatus: 'idle',
    status: 'pending',
    refetch: mockRefetch,
    ...overrides,
  } as unknown as UseQueryResult<Skill[], ApiError>;
}

function setData(
  catalog: Partial<UseQueryResult<Skill[], ApiError>>,
  data: UseSkillGraphDataResult['graph'],
  layout: UseSkillGraphLayoutResult,
) {
  mockUseSkillGraphData.mockReturnValue({
    catalog: makeCatalog(catalog),
    graph: data,
  });
  mockUseSkillGraphLayout.mockReturnValue(layout);
}

// ── Tests ───────────────────────────────────────────────────────────────────

describe('SkillGraphView', () => {
  beforeEach(() => {
    reactFlowSpy.mockClear();
    miniMapSpy.mockClear();
    mockUseSkillGraphData.mockReset();
    mockUseSkillGraphLayout.mockReset();
    mockRefetch.mockClear();
  });

  it('renders skeleton (no ReactFlow) while catalog is pending', () => {
    setData(
      { isPending: true, status: 'pending' },
      null,
      { flowNodes: [], flowEdges: [], isReady: false },
    );

    render(<SkillGraphView />);

    expect(screen.queryByTestId('react-flow')).not.toBeInTheDocument();
    expect(screen.getByTestId('skill-graph-skeleton')).toBeInTheDocument();
  });

  it('renders GraphErrorState on catalog error and Reload calls refetch', () => {
    setData(
      {
        isError: true,
        error: new Error('boom') as ApiError,
        status: 'error',
      },
      null,
      { flowNodes: [], flowEdges: [], isReady: false },
    );

    render(<SkillGraphView />);

    expect(screen.queryByTestId('react-flow')).not.toBeInTheDocument();
    expect(screen.getByText(/Couldn't lay out the graph\./i)).toBeInTheDocument();

    const reloadBtn = screen.getByRole('button', { name: /Reload graph/i });
    fireEvent.click(reloadBtn);
    expect(mockRefetch).toHaveBeenCalledTimes(1);
  });

  it('renders GraphEmptyState when graph is empty', () => {
    setData(
      { isSuccess: true, status: 'success', data: [] },
      { nodes: [], edges: [], cycles: [] },
      { flowNodes: [], flowEdges: [], isReady: true },
    );

    render(<SkillGraphView />);

    expect(screen.queryByTestId('react-flow')).not.toBeInTheDocument();
    expect(
      screen.getByText(/No skills to graph yet\./i),
    ).toBeInTheDocument();
  });

  it('mounts ReactFlow with skill + file nodeTypes when data is ready', () => {
    setData(
      { isSuccess: true, status: 'success' },
      { nodes: [], edges: [], cycles: [] },
      {
        flowNodes: [
          {
            id: 'skill:alpha',
            type: 'skill',
            position: { x: 0, y: 0 },
            data: { label: 'Alpha', kind: 'skill', refCount: 1 },
          },
          {
            id: 'file:docs/a.md',
            type: 'file',
            position: { x: 280, y: 0 },
            data: { label: 'a.md', kind: 'file', path: 'docs/a.md' },
          },
        ],
        flowEdges: [
          { id: 'edge:skill:alpha->file:docs/a.md', source: 'skill:alpha', target: 'file:docs/a.md' },
        ],
        isReady: true,
      },
    );

    render(<SkillGraphView />);

    expect(screen.getByTestId('react-flow')).toBeInTheDocument();
    expect(reactFlowSpy).toHaveBeenCalledTimes(1);
    const props = reactFlowSpy.mock.calls[0][0] as Record<string, unknown>;
    const nodeTypes = props.nodeTypes as Record<string, unknown>;
    expect(nodeTypes).toHaveProperty('skill');
    expect(nodeTypes).toHaveProperty('file');
  });

  it('canvas wrapper has role="application" + tabIndex=0', () => {
    setData(
      { isSuccess: true, status: 'success' },
      { nodes: [], edges: [], cycles: [] },
      {
        flowNodes: [
          {
            id: 'skill:alpha',
            type: 'skill',
            position: { x: 0, y: 0 },
            data: { label: 'Alpha', kind: 'skill', refCount: 0 },
          },
        ],
        flowEdges: [],
        isReady: true,
      },
    );

    render(<SkillGraphView />);

    const region = screen.getByRole('application');
    expect(region).toBeInTheDocument();
    expect(region.getAttribute('tabIndex')).toBe('0');
    // The role is on the wrapper, NOT on the ReactFlow stub.
    expect(region.getAttribute('data-testid')).not.toBe('react-flow');
  });

  it('aria-label uses singular/plural per UI-SPEC verbatim', () => {
    setData(
      { isSuccess: true, status: 'success' },
      { nodes: [], edges: [], cycles: [] },
      {
        flowNodes: [
          {
            id: 'skill:alpha',
            type: 'skill',
            position: { x: 0, y: 0 },
            data: { label: 'Alpha', kind: 'skill', refCount: 1 },
          },
          {
            id: 'file:docs/a.md',
            type: 'file',
            position: { x: 280, y: 0 },
            data: { label: 'a.md', kind: 'file', path: 'docs/a.md' },
          },
        ],
        flowEdges: [],
        isReady: true,
      },
    );

    render(<SkillGraphView />);

    expect(
      screen.getByLabelText(
        /Skill dependency graph\. 1 skill, 1 reference file\. Use arrow keys to navigate, Enter to open, Escape to deselect\./i,
      ),
    ).toBeInTheDocument();
  });

  it('passes nodesDraggable={false} and proOptions.hideAttribution=true', () => {
    setData(
      { isSuccess: true, status: 'success' },
      { nodes: [], edges: [], cycles: [] },
      {
        flowNodes: [
          {
            id: 'skill:alpha',
            type: 'skill',
            position: { x: 0, y: 0 },
            data: { label: 'Alpha', kind: 'skill', refCount: 0 },
          },
        ],
        flowEdges: [],
        isReady: true,
      },
    );

    render(<SkillGraphView />);

    const props = reactFlowSpy.mock.calls[0][0] as Record<string, unknown>;
    expect(props.nodesDraggable).toBe(false);
    const proOptions = props.proOptions as Record<string, unknown>;
    expect(proOptions.hideAttribution).toBe(true);
  });

  it('miniMapNodeColor returns violet for skill, neutral for file', () => {
    expect(miniMapNodeColor({ type: 'skill' } as never)).toBe('#7c5cff');
    expect(miniMapNodeColor({ type: 'file' } as never)).toBe('#f1f1ef');
  });

  it('ReactFlow root does NOT carry role="application" (Design-Debt #5)', () => {
    setData(
      { isSuccess: true, status: 'success' },
      { nodes: [], edges: [], cycles: [] },
      {
        flowNodes: [
          {
            id: 'skill:alpha',
            type: 'skill',
            position: { x: 0, y: 0 },
            data: { label: 'Alpha', kind: 'skill', refCount: 0 },
          },
        ],
        flowEdges: [],
        isReady: true,
      },
    );

    render(<SkillGraphView />);

    const rfRoot = screen.getByTestId('react-flow');
    expect(rfRoot.getAttribute('role')).not.toBe('application');
  });

  it('mounts MiniMap with skill/file color function', () => {
    setData(
      { isSuccess: true, status: 'success' },
      { nodes: [], edges: [], cycles: [] },
      {
        flowNodes: [
          {
            id: 'skill:alpha',
            type: 'skill',
            position: { x: 0, y: 0 },
            data: { label: 'Alpha', kind: 'skill', refCount: 0 },
          },
        ],
        flowEdges: [],
        isReady: true,
      },
    );

    render(<SkillGraphView />);

    expect(miniMapSpy).toHaveBeenCalledTimes(1);
    const miniProps = miniMapSpy.mock.calls[0][0] as Record<string, unknown>;
    expect(miniProps.position).toBe('bottom-right');
    expect(typeof miniProps.nodeColor).toBe('function');
    const colorFn = miniProps.nodeColor as (n: { type?: string }) => string;
    expect(colorFn({ type: 'skill' })).toBe('#7c5cff');
    expect(colorFn({ type: 'file' })).toBe('#f1f1ef');
  });
});

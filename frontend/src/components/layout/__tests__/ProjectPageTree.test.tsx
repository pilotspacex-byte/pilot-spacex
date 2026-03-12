/**
 * Tests for ProjectPageTree component
 *
 * Tests expand/collapse, inline create, active highlight, depth limit.
 */

import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { PageTreeNode } from '@/lib/tree-utils';

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

const mockToggleNodeExpanded = vi.fn();
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const mockIsNodeExpanded = vi.fn((_id: any) => false);

vi.mock('@/stores', () => ({
  useUIStore: () => ({
    toggleNodeExpanded: mockToggleNodeExpanded,
    isNodeExpanded: mockIsNodeExpanded,
  }),
}));

const mockCreateNoteMutate = vi.fn();
vi.mock('@/features/notes/hooks', () => ({
  useCreateNote: () => ({
    mutate: mockCreateNoteMutate,
    isPending: false,
  }),
  createNoteDefaults: (title?: string) => ({ title: title ?? 'Untitled' }),
}));

const mockRouterPush = vi.fn();
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockRouterPush }),
}));

vi.mock('next/link', () => ({
  default: ({
    href,
    children,
    className,
  }: {
    href: string;
    children: React.ReactNode;
    className?: string;
  }) => (
    <a href={href} className={className}>
      {children}
    </a>
  ),
}));

// ---------------------------------------------------------------------------
// Test fixtures
// ---------------------------------------------------------------------------

const leafNode: PageTreeNode = {
  id: 'node-1',
  title: 'Getting Started',
  parentId: null,
  depth: 0,
  position: 1000,
  children: [],
};

const parentNode: PageTreeNode = {
  id: 'node-2',
  title: 'Architecture',
  parentId: null,
  depth: 0,
  position: 2000,
  children: [
    {
      id: 'node-2-1',
      title: 'Overview',
      parentId: 'node-2',
      depth: 1,
      position: 1000,
      children: [],
    },
  ],
};

const depth2Node: PageTreeNode = {
  id: 'node-3',
  title: 'Deep Section',
  parentId: null,
  depth: 0,
  position: 3000,
  children: [
    {
      id: 'node-3-1',
      title: 'Level 1',
      parentId: 'node-3',
      depth: 1,
      position: 1000,
      children: [
        {
          id: 'node-3-1-1',
          title: 'Level 2',
          parentId: 'node-3-1',
          depth: 2,
          position: 1000,
          children: [],
        },
      ],
    },
  ],
};

// ---------------------------------------------------------------------------
// Setup: import component after mocks are defined
// ---------------------------------------------------------------------------

let ProjectPageTree: React.ComponentType<{
  workspaceId: string;
  workspaceSlug: string;
  projectId: string;
  projectName: string;
  currentNoteId?: string;
}>;

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const mockUseProjectPageTree = vi.fn((_ws: any, _proj: any) => ({
  data: [leafNode, parentNode] as PageTreeNode[],
  isLoading: false,
}));

vi.mock('@/features/notes/hooks/useProjectPageTree', () => ({
  useProjectPageTree: (workspaceId: string, projectId: string) =>
    mockUseProjectPageTree(workspaceId, projectId),
}));

beforeEach(async () => {
  vi.clearAllMocks();
  mockIsNodeExpanded.mockReturnValue(false);
  mockUseProjectPageTree.mockReturnValue({ data: [leafNode, parentNode], isLoading: false });
  const mod = await import('../ProjectPageTree');
  ProjectPageTree = mod.ProjectPageTree;
});

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('ProjectPageTree', () => {
  const defaultProps = {
    workspaceId: 'ws-1',
    workspaceSlug: 'workspace',
    projectId: 'proj-1',
    projectName: 'Test Project',
  };

  it('Test 1: renders root nodes from tree data with correct titles', () => {
    render(<ProjectPageTree {...defaultProps} />);
    expect(screen.getByText('Getting Started')).toBeInTheDocument();
    expect(screen.getByText('Architecture')).toBeInTheDocument();
  });

  it('Test 2: clicking a node chevron calls UIStore.toggleNodeExpanded', async () => {
    render(<ProjectPageTree {...defaultProps} />);
    const [chevronBtn] = screen.getAllByRole('button', { name: /expand|collapse/i });
    await userEvent.click(chevronBtn!);
    expect(mockToggleNodeExpanded).toHaveBeenCalledWith(expect.any(String));
  });

  it('Test 3: when node is expanded (UIStore.isNodeExpanded=true), children are visible', () => {
    mockIsNodeExpanded.mockImplementation((id: string) => id === 'node-2');
    mockUseProjectPageTree.mockReturnValue({ data: [parentNode], isLoading: false });
    render(<ProjectPageTree {...defaultProps} />);
    expect(screen.getByText('Overview')).toBeInTheDocument();
  });

  it('Test 4: when node is collapsed, children are hidden', () => {
    mockIsNodeExpanded.mockReturnValue(false);
    mockUseProjectPageTree.mockReturnValue({ data: [parentNode], isLoading: false });
    render(<ProjectPageTree {...defaultProps} />);
    expect(screen.queryByText('Overview')).not.toBeInTheDocument();
  });

  it('Test 5: clicking "+" button on a node triggers inline create mode (shows input field)', async () => {
    render(<ProjectPageTree {...defaultProps} />);
    const [addBtn] = screen.getAllByRole('button', { name: /add child|new child/i });
    await userEvent.click(addBtn!);
    expect(screen.getByRole('textbox')).toBeInTheDocument();
  });

  it('Test 6: submitting inline create input calls useCreateNote with correct parentId and projectId', async () => {
    render(<ProjectPageTree {...defaultProps} />);
    const [addBtn] = screen.getAllByRole('button', { name: /add child|new child/i });
    await userEvent.click(addBtn!);

    const input = screen.getByRole('textbox');
    await userEvent.type(input, 'New Child Page');
    fireEvent.keyDown(input, { key: 'Enter' });

    expect(mockCreateNoteMutate).toHaveBeenCalledWith(
      expect.objectContaining({
        title: 'New Child Page',
        parentId: leafNode.id,
        projectId: 'proj-1',
      })
    );
  });

  it('Test 7: active page (matching currentNoteId) has highlighted styling', () => {
    render(<ProjectPageTree {...defaultProps} currentNoteId="node-1" />);
    const activeLink = screen.getByText('Getting Started').closest('a');
    expect(activeLink?.className).toContain('bg-sidebar-accent');
  });

  it('Test 8: nodes at depth 2 do NOT show "+" button (max depth reached)', () => {
    mockIsNodeExpanded.mockImplementation((id: string) => id === 'node-3' || id === 'node-3-1');
    mockUseProjectPageTree.mockReturnValue({ data: [depth2Node], isLoading: false });
    render(<ProjectPageTree {...defaultProps} />);

    // depth-2 node "Level 2" should not have a "+" button
    const level2Item = screen.getByText('Level 2').closest('[data-testid="tree-node"]');
    const addBtn = level2Item?.querySelector('[aria-label*="child"]');
    expect(addBtn).toBeNull();
  });
});

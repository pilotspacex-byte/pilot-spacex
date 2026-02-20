/**
 * Unit tests for GutterIssueIndicators and buildBlockIssueMap.
 *
 * @module components/editor/gutter/__tests__/GutterIssueIndicators.test
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { GutterIssueIndicators, buildBlockIssueMap } from '../GutterIssueIndicators';
import type { LinkedIssueBrief, StateBrief, StateGroup } from '@/types';

// Mock HoverCard to simplify tests — render trigger and content inline
vi.mock('@/components/ui/hover-card', () => ({
  HoverCard: ({ children }: React.PropsWithChildren) => <div>{children}</div>,
  HoverCardTrigger: ({
    children,
    asChild: _asChild,
  }: React.PropsWithChildren<{ asChild?: boolean }>) => <div>{children}</div>,
  HoverCardContent: ({ children }: React.PropsWithChildren) => (
    <div data-testid="hover-card-content">{children}</div>
  ),
}));

function makeState(group: StateGroup, name: string): StateBrief {
  return { id: `state-${group}`, name, color: '#000', group };
}

function makeIssue(overrides: Partial<LinkedIssueBrief> = {}): LinkedIssueBrief {
  return {
    id: 'issue-1',
    identifier: 'PS-42',
    name: 'Fix login timeout',
    priority: 'medium' as const,
    state: makeState('started', 'In Progress'),
    assignee: { id: 'user-1', email: 'dev@test.com', displayName: 'Dev User' },
    ...overrides,
  };
}

function createMockEditor(
  inlineIssueNodes: Array<{ issueId: string; sourceBlockId: string }> = []
) {
  return {
    view: {
      dom: {
        querySelector: vi.fn((selector: string) => {
          const id = selector.match(/data-block-id="(.+?)"/)?.[1];
          if (!id) return null;
          return {
            offsetTop: id === 'block-a' ? 100 : id === 'block-b' ? 300 : 500,
          } as unknown as HTMLElement;
        }),
      },
    },
    state: {
      doc: {
        descendants: vi.fn((cb: (node: Record<string, unknown>) => boolean) => {
          for (const node of inlineIssueNodes) {
            cb({
              type: { name: 'inlineIssue' },
              attrs: { issueId: node.issueId, sourceBlockId: node.sourceBlockId },
            });
          }
        }),
      },
    },
    on: vi.fn(),
    off: vi.fn(),
    isDestroyed: false,
  };
}

describe('buildBlockIssueMap', () => {
  it('maps issues by blockId from linkedIssues', () => {
    const issues = [
      makeIssue({ id: 'i1', blockId: 'block-a' }),
      makeIssue({ id: 'i2', blockId: 'block-a' }),
      makeIssue({ id: 'i3', blockId: 'block-b' }),
    ];

    const editor = createMockEditor();
    const map = buildBlockIssueMap(issues, editor as unknown as import('@tiptap/react').Editor);

    expect(map.get('block-a')?.length).toBe(2);
    expect(map.get('block-b')?.length).toBe(1);
  });

  it('includes InlineIssue nodes from editor doc', () => {
    const issues = [makeIssue({ id: 'i1' })];
    const editor = createMockEditor([{ issueId: 'i1', sourceBlockId: 'block-c' }]);

    const map = buildBlockIssueMap(issues, editor as unknown as import('@tiptap/react').Editor);

    expect(map.get('block-c')?.length).toBe(1);
    expect(map.get('block-c')![0]!.id).toBe('i1');
  });

  it('deduplicates issues that appear in both linkedIssues and editor nodes', () => {
    const issues = [makeIssue({ id: 'i1', blockId: 'block-a' })];
    const editor = createMockEditor([{ issueId: 'i1', sourceBlockId: 'block-a' }]);

    const map = buildBlockIssueMap(issues, editor as unknown as import('@tiptap/react').Editor);

    expect(map.get('block-a')?.length).toBe(1);
  });

  it('ignores issues without blockId and no matching editor nodes', () => {
    const issues = [makeIssue({ id: 'i1' })];
    const editor = createMockEditor();

    const map = buildBlockIssueMap(issues, editor as unknown as import('@tiptap/react').Editor);

    expect(map.size).toBe(0);
  });

  it('returns empty map when no issues', () => {
    const editor = createMockEditor();
    const map = buildBlockIssueMap([], editor as unknown as import('@tiptap/react').Editor);
    expect(map.size).toBe(0);
  });
});

describe('GutterIssueIndicators', () => {
  it('renders nothing when no linked issues with blockId', () => {
    const editor = createMockEditor();
    const issues = [makeIssue({ id: 'i1' })]; // no blockId

    const { container } = render(
      <GutterIssueIndicators
        editor={editor as unknown as import('@tiptap/react').Editor}
        linkedIssues={issues}
      />
    );

    // No dots rendered
    expect(container.querySelector('button')).toBeNull();
  });

  it('renders issue dot with correct aria-label', () => {
    const editor = createMockEditor();
    const issues = [makeIssue({ blockId: 'block-a' })];

    render(
      <GutterIssueIndicators
        editor={editor as unknown as import('@tiptap/react').Editor}
        linkedIssues={issues}
      />
    );

    expect(
      screen.getByRole('button', { name: 'PS-42: Fix login timeout (In Progress)' })
    ).toBeInTheDocument();
  });

  it('calls onIssueClick when dot is clicked', () => {
    const editor = createMockEditor();
    const issues = [makeIssue({ blockId: 'block-a' })];
    const onClick = vi.fn();

    render(
      <GutterIssueIndicators
        editor={editor as unknown as import('@tiptap/react').Editor}
        linkedIssues={issues}
        onIssueClick={onClick}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: /PS-42/ }));
    expect(onClick).toHaveBeenCalledWith('issue-1');
  });

  it('shows 1 dot and overflow badge when multiple issues on a block', () => {
    const editor = createMockEditor();
    const issues = [
      makeIssue({ id: 'i1', identifier: 'PS-1', blockId: 'block-a' }),
      makeIssue({ id: 'i2', identifier: 'PS-2', blockId: 'block-a' }),
      makeIssue({ id: 'i3', identifier: 'PS-3', blockId: 'block-a' }),
      makeIssue({ id: 'i4', identifier: 'PS-4', blockId: 'block-a' }),
    ];

    render(
      <GutterIssueIndicators
        editor={editor as unknown as import('@tiptap/react').Editor}
        linkedIssues={issues}
      />
    );

    // 1 visible dot + overflow badge showing remaining count
    const buttons = screen.getAllByRole('button');
    expect(buttons.length).toBe(1);
    expect(screen.getByText('3+')).toBeInTheDocument();
  });

  it('renders popover content with issue details', () => {
    const editor = createMockEditor();
    const issues = [
      makeIssue({
        blockId: 'block-a',
        assignee: { id: 'u1', email: 'dev@test.com', displayName: 'Jane' },
      }),
    ];

    render(
      <GutterIssueIndicators
        editor={editor as unknown as import('@tiptap/react').Editor}
        linkedIssues={issues}
      />
    );

    // HoverCard content is always rendered in our mock
    expect(screen.getByText('PS-42')).toBeInTheDocument();
    expect(screen.getByText('Fix login timeout')).toBeInTheDocument();
    expect(screen.getByText('In Progress')).toBeInTheDocument();
    expect(screen.getByText('medium')).toBeInTheDocument();
    expect(screen.getByText('Jane')).toBeInTheDocument();
  });

  it('registers editor update listener for position tracking', () => {
    const editor = createMockEditor();
    const issues = [makeIssue({ blockId: 'block-a' })];

    render(
      <GutterIssueIndicators
        editor={editor as unknown as import('@tiptap/react').Editor}
        linkedIssues={issues}
      />
    );

    expect(editor.on).toHaveBeenCalledWith('update', expect.any(Function));
  });
});

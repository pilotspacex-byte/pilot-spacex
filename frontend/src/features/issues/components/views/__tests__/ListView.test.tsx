/**
 * ListView component tests.
 *
 * Covers: loading skeleton, empty state, grouping by state, rendering groups.
 */

import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { ListView } from '../list/ListView';
import type { Issue } from '@/types';

vi.mock('mobx-react-lite', () => ({
  observer: (component: unknown) => component,
}));

const mockViewStore = {
  collapsedGroups: new Set<string>(),
  toggleGroupCollapsed: vi.fn(),
  selectedIssueIds: new Set<string>(),
  toggleSelectedIssue: vi.fn(),
  clearSelection: vi.fn(),
};

vi.mock('@/stores/RootStore', () => ({
  useIssueViewStore: () => mockViewStore,
}));

vi.mock('../list/ListGroup', () => ({
  ListGroup: ({ groupLabel, issues }: { groupLabel: string; issues: Issue[] }) => (
    <div data-testid={`group-${groupLabel}`}>
      {groupLabel} ({issues.length})
    </div>
  ),
}));

vi.mock('../list/BulkActionsBar', () => ({
  BulkActionsBar: ({ selectedCount }: { selectedCount: number }) =>
    selectedCount > 0 ? <div data-testid="bulk-bar">{selectedCount} selected</div> : null,
}));

function makeIssue(id: string, stateName: string): Issue {
  return {
    id,
    identifier: `PS-${id}`,
    name: `Issue ${id}`,
    description: '',
    type: 'task',
    priority: 'medium',
    state: { id: `s-${stateName}`, name: stateName, color: '#ccc', group: 'started' },
    assignee: null,
    assigneeId: undefined,
    labels: [],
    projectId: 'p1',
    workspaceId: 'w1',
    sequenceId: 1,
    reporterId: 'u1',
    reporter: { id: 'u1', displayName: 'Test', email: 'test@test.com' },
    project: { id: 'p1', name: 'Project', identifier: 'PS' },
    hasAiEnhancements: false,
    createdAt: '2024-01-01',
    updatedAt: '2024-01-01',
    sortOrder: 0,
    subIssueCount: 0,
  } as Issue;
}

describe('ListView', () => {
  it('shows loading skeleton when isLoading=true', () => {
    const { container } = render(<ListView issues={[]} isLoading={true} />);
    const pulseElements = container.querySelectorAll('.animate-pulse');
    expect(pulseElements.length).toBeGreaterThan(0);
  });

  it('shows empty state when no issues', () => {
    render(<ListView issues={[]} isLoading={false} />);
    expect(screen.getByText('No issues yet')).toBeInTheDocument();
  });

  it('groups issues by state name', () => {
    const issues = [
      makeIssue('1', 'Backlog'),
      makeIssue('2', 'In Progress'),
      makeIssue('3', 'Backlog'),
      makeIssue('4', 'Done'),
    ];
    render(<ListView issues={issues} isLoading={false} />);
    expect(screen.getByTestId('group-Backlog')).toHaveTextContent('Backlog (2)');
    expect(screen.getByTestId('group-In Progress')).toHaveTextContent('In Progress (1)');
    expect(screen.getByTestId('group-Done')).toHaveTextContent('Done (1)');
  });

  it('does not render groups with zero issues', () => {
    const issues = [makeIssue('1', 'Todo')];
    render(<ListView issues={issues} isLoading={false} />);
    expect(screen.getByTestId('group-Todo')).toBeInTheDocument();
    expect(screen.queryByTestId('group-Backlog')).not.toBeInTheDocument();
    expect(screen.queryByTestId('group-Done')).not.toBeInTheDocument();
  });

  it('renders BulkActionsBar', () => {
    mockViewStore.selectedIssueIds = new Set(['1', '2']);
    render(
      <ListView issues={[makeIssue('1', 'Todo'), makeIssue('2', 'Todo')]} isLoading={false} />
    );
    expect(screen.getByTestId('bulk-bar')).toHaveTextContent('2 selected');
    mockViewStore.selectedIssueIds = new Set();
  });
});

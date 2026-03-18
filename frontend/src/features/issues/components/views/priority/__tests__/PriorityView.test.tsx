import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { PriorityView } from '../PriorityView';
import type { Issue } from '@/types';

// Mock the store singleton
vi.mock('@/stores/RootStore', () => ({
  useIssueViewStore: () => ({
    collapsedGroups: new Set<string>(),
    toggleGroupCollapsed: vi.fn(),
    toggleSelectedIssue: vi.fn(),
    selectedIssueIds: new Set<string>(),
    clearSelection: vi.fn(),
  }),
}));

// Mock ListGroup to simplify tests
vi.mock('../../list/ListGroup', () => ({
  ListGroup: ({
    groupLabel,
    issues,
    isCollapsed,
    onToggleCollapse,
  }: {
    groupLabel: string;
    issues: { id: string }[];
    isCollapsed: boolean;
    onToggleCollapse: () => void;
  }) => (
    <div data-testid={`group-${groupLabel.toLowerCase().replace(/\s+/g, '-')}`}>
      <button onClick={onToggleCollapse}>{groupLabel}</button>
      <span data-testid="count">{issues.length}</span>
      {!isCollapsed && issues.map((i) => <div key={i.id} data-testid={`issue-${i.id}`} />)}
    </div>
  ),
}));

function makeIssue(id: string, priority: string | null): Issue {
  return {
    id,
    name: `Issue ${id}`,
    identifier: `PS-${id}`,
    priority: priority as Issue['priority'],
    state: null,
    labels: [],
    subIssueCount: 0,
    projectId: 'proj-1',
    assigneeId: null,
    type: 'task',
    description: null,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  } as unknown as Issue;
}

describe('PriorityView', () => {
  const onIssueClick = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows empty state when no issues', () => {
    render(<PriorityView issues={[]} isLoading={false} onIssueClick={onIssueClick} />);

    expect(screen.getByText('No issues yet')).toBeInTheDocument();
  });

  it('distributes issues into correct priority groups', () => {
    const issues = [
      makeIssue('1', 'urgent'),
      makeIssue('2', 'urgent'),
      makeIssue('3', 'high'),
      makeIssue('4', 'medium'),
      makeIssue('5', 'low'),
      makeIssue('6', null),
    ];

    render(<PriorityView issues={issues} isLoading={false} onIssueClick={onIssueClick} />);

    const urgentGroup = screen.getByTestId('group-urgent');
    expect(urgentGroup.querySelector('[data-testid="count"]')?.textContent).toBe('2');

    const highGroup = screen.getByTestId('group-high');
    expect(highGroup.querySelector('[data-testid="count"]')?.textContent).toBe('1');

    const noPriorityGroup = screen.getByTestId('group-no-priority');
    expect(noPriorityGroup.querySelector('[data-testid="count"]')?.textContent).toBe('1');
  });

  it('issues with no priority default to none group', () => {
    const issues = [makeIssue('1', null), makeIssue('2', undefined as unknown as string)];

    render(<PriorityView issues={issues} isLoading={false} onIssueClick={onIssueClick} />);

    const noPriorityGroup = screen.getByTestId('group-no-priority');
    expect(noPriorityGroup.querySelector('[data-testid="count"]')?.textContent).toBe('2');
  });

  it('renders empty groups (with 0 count)', () => {
    render(
      <PriorityView
        issues={[makeIssue('1', 'urgent')]}
        isLoading={false}
        onIssueClick={onIssueClick}
      />
    );

    // All 5 groups should be present even when empty
    expect(screen.getByTestId('group-urgent')).toBeTruthy();
    expect(screen.getByTestId('group-high')).toBeTruthy();
    expect(screen.getByTestId('group-medium')).toBeTruthy();
    expect(screen.getByTestId('group-low')).toBeTruthy();
    expect(screen.getByTestId('group-no-priority')).toBeTruthy();

    // High group should have count 0
    const highGroup = screen.getByTestId('group-high');
    expect(highGroup.querySelector('[data-testid="count"]')?.textContent).toBe('0');
  });

  it('shows loading skeleton when isLoading is true', () => {
    const { container } = render(
      <PriorityView issues={[]} isLoading={true} onIssueClick={onIssueClick} />
    );

    // Should show skeletons, not priority groups
    expect(screen.queryByTestId('group-urgent')).toBeNull();
    expect(container.querySelector('[data-testid*="group-"]')).toBeNull();
  });
});

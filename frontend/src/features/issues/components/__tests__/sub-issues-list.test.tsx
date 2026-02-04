/**
 * SubIssuesList component tests (T034).
 *
 * Verifies sub-issue rows, progress bar, inline create form,
 * empty state, state badges, and navigation links.
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { SubIssuesList } from '../sub-issues-list';
import type { Issue, StateBrief } from '@/types';

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

vi.mock('next/link', () => ({
  default: ({ children, href, ...props }: { children: React.ReactNode; href: string }) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}));

const mockMutate = vi.fn();

vi.mock('../../hooks/use-create-sub-issue', () => ({
  useCreateSubIssue: () => ({
    mutate: mockMutate,
    isPending: false,
  }),
}));

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const doneState: StateBrief = { id: 's1', name: 'Done', color: '#29A386', group: 'completed' };
const todoState: StateBrief = { id: 's2', name: 'Todo', color: '#5B8FC9', group: 'unstarted' };
const inProgressState: StateBrief = {
  id: 's3',
  name: 'In Progress',
  color: '#D9853F',
  group: 'started',
};

function createSubIssue(overrides?: Partial<Issue>): Issue {
  return {
    id: 'sub-1',
    identifier: 'PS-10',
    name: 'Sub-issue one',
    title: 'Sub-issue one',
    state: todoState,
    priority: 'medium',
    type: 'task',
    projectId: 'proj-1',
    workspaceId: 'ws-1',
    sequenceId: 10,
    sortOrder: 1,
    reporterId: 'user-1',
    reporter: { id: 'user-1', email: 'john@test.com', displayName: 'John' },
    labels: [],
    subIssueCount: 0,
    project: { id: 'proj-1', name: 'Project', identifier: 'PS' },
    aiGenerated: false,
    hasAiEnhancements: false,
    createdAt: '2025-01-01',
    updatedAt: '2025-01-01',
    ...overrides,
  };
}

const defaultProps = {
  parentId: 'issue-parent',
  workspaceId: 'ws-1',
  workspaceSlug: 'my-team',
  projectId: 'proj-1',
  subIssues: [] as Issue[],
};

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('SubIssuesList', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders sub-issue rows with identifiers and names', () => {
    const subIssues = [
      createSubIssue({ id: 'sub-1', identifier: 'PS-10', name: 'First sub-issue' }),
      createSubIssue({ id: 'sub-2', identifier: 'PS-11', name: 'Second sub-issue' }),
    ];

    render(<SubIssuesList {...defaultProps} subIssues={subIssues} />);

    expect(screen.getByText('PS-10')).toBeInTheDocument();
    expect(screen.getByText('First sub-issue')).toBeInTheDocument();
    expect(screen.getByText('PS-11')).toBeInTheDocument();
    expect(screen.getByText('Second sub-issue')).toBeInTheDocument();
  });

  it('shows progress bar with correct completion count', () => {
    const subIssues = [
      createSubIssue({ id: 'sub-1', state: doneState }),
      createSubIssue({ id: 'sub-2', state: todoState }),
      createSubIssue({ id: 'sub-3', state: doneState }),
    ];

    render(<SubIssuesList {...defaultProps} subIssues={subIssues} />);

    expect(screen.getByText('2 of 3 completed')).toBeInTheDocument();
  });

  it('"Add sub-issue" button shows inline form', () => {
    render(<SubIssuesList {...defaultProps} subIssues={[]} />);

    const addButton = screen.getByRole('button', { name: /Add sub-issue/i });
    fireEvent.click(addButton);

    expect(screen.getByRole('textbox', { name: 'Sub-issue title' })).toBeInTheDocument();
  });

  it('submitting the form calls createSubIssue mutation', async () => {
    mockMutate.mockImplementation((_data: unknown, opts: { onSuccess: () => void }) => {
      opts.onSuccess();
    });

    render(<SubIssuesList {...defaultProps} subIssues={[]} />);

    // Open the form
    fireEvent.click(screen.getByRole('button', { name: /Add sub-issue/i }));

    const input = screen.getByRole('textbox', { name: 'Sub-issue title' });
    fireEvent.change(input, { target: { value: 'New sub-issue' } });

    const submitButton = screen.getByRole('button', { name: 'Add' });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(mockMutate).toHaveBeenCalledWith(
        { name: 'New sub-issue', projectId: 'proj-1' },
        expect.objectContaining({ onSuccess: expect.any(Function) })
      );
    });
  });

  it('empty state when no sub-issues', () => {
    render(<SubIssuesList {...defaultProps} subIssues={[]} />);

    expect(screen.getByText('No sub-issues')).toBeInTheDocument();
  });

  it('state badges show correct colors from state.color', () => {
    const subIssues = [
      createSubIssue({ id: 'sub-1', state: doneState }),
      createSubIssue({ id: 'sub-2', state: inProgressState }),
    ];

    render(<SubIssuesList {...defaultProps} subIssues={subIssues} />);

    // Find state dots by their color style
    const stateDots = screen.getAllByText('', { selector: 'span[aria-hidden="true"]' });
    const doneColor = stateDots.find(
      (el) =>
        (el as HTMLElement).style.backgroundColor === 'rgb(41, 163, 134)' ||
        (el as HTMLElement).style.backgroundColor === doneState.color
    );
    expect(doneColor).toBeTruthy();
  });

  it('state name labels render correctly', () => {
    const subIssues = [
      createSubIssue({ id: 'sub-1', state: doneState }),
      createSubIssue({ id: 'sub-2', state: inProgressState }),
    ];

    render(<SubIssuesList {...defaultProps} subIssues={subIssues} />);

    expect(screen.getByText('Done')).toBeInTheDocument();
    expect(screen.getByText('In Progress')).toBeInTheDocument();
  });

  it('links navigate to correct issue URL', () => {
    const subIssues = [createSubIssue({ id: 'sub-42' })];

    render(<SubIssuesList {...defaultProps} subIssues={subIssues} />);

    const link = screen.getByRole('link');
    expect(link).toHaveAttribute('href', '/my-team/issues/sub-42');
  });

  it('does not show "Add sub-issue" button when disabled', () => {
    render(<SubIssuesList {...defaultProps} subIssues={[]} disabled />);

    expect(screen.queryByRole('button', { name: /Add sub-issue/i })).not.toBeInTheDocument();
  });

  it('does not show progress bar when no sub-issues', () => {
    render(<SubIssuesList {...defaultProps} subIssues={[]} />);

    expect(screen.queryByText(/of.*completed/)).not.toBeInTheDocument();
  });

  it('cancel button closes the inline form', () => {
    render(<SubIssuesList {...defaultProps} subIssues={[]} />);

    fireEvent.click(screen.getByRole('button', { name: /Add sub-issue/i }));
    expect(screen.getByRole('textbox', { name: 'Sub-issue title' })).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }));
    expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
  });
});

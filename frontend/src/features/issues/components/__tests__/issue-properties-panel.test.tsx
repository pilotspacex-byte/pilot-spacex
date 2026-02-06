/**
 * IssuePropertiesPanel component tests.
 *
 * T021: Verifies the composition panel renders all property sections,
 * calls onUpdate with correct payloads, and shows save status indicators.
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { IssuePropertiesPanel } from '../issue-properties-panel';
import type { Issue, Label, Cycle, StateBrief, IntegrationLink, NoteIssueLink } from '@/types';
import type { WorkspaceMember } from '@/features/issues/hooks';

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

const mockGetSaveStatus = vi.fn().mockReturnValue('idle');
const mockSetSaveStatus = vi.fn();

vi.mock('@/lib/supabase', () => ({
  supabase: {
    auth: { getSession: vi.fn(), onAuthStateChange: vi.fn() },
  },
}));

vi.mock('@/stores', () => ({
  useIssueStore: () => ({
    getSaveStatus: mockGetSaveStatus,
    setSaveStatus: mockSetSaveStatus,
  }),
}));

// Mock child selector components to avoid their internal complexity
vi.mock('@/components/issues', () => ({
  IssueStateSelect: ({ value, onChange, disabled }: Record<string, unknown>) => (
    <button
      data-testid="state-select"
      data-value={value}
      disabled={disabled as boolean}
      onClick={() => (onChange as (v: string) => void)('in_progress')}
    >
      State: {value as string}
    </button>
  ),
  IssuePrioritySelect: ({ value, onChange, disabled }: Record<string, unknown>) => (
    <button
      data-testid="priority-select"
      data-value={value}
      disabled={disabled as boolean}
      onClick={() => (onChange as (v: string) => void)('high')}
    >
      Priority: {value as string}
    </button>
  ),
  IssueTypeSelect: ({ value, onChange, disabled }: Record<string, unknown>) => (
    <button
      data-testid="type-select"
      data-value={value}
      disabled={disabled as boolean}
      onClick={() => (onChange as (v: string) => void)('bug')}
    >
      Type: {value as string}
    </button>
  ),
  CycleSelector: ({ value, onChange, disabled }: Record<string, unknown>) => (
    <button
      data-testid="cycle-select"
      data-value={value as string}
      disabled={disabled as boolean}
      onClick={() => (onChange as (v: string | null) => void)('cycle-2')}
    >
      Cycle: {(value as string) ?? 'None'}
    </button>
  ),
  EstimateSelector: ({ value, onChange, disabled }: Record<string, unknown>) => (
    <button
      data-testid="estimate-select"
      data-value={value as number}
      disabled={disabled as boolean}
      onClick={() => (onChange as (v: number) => void)(5)}
    >
      Estimate: {(value as number) ?? 'None'}
    </button>
  ),
  AssigneeSelector: ({ value, onChange, disabled }: Record<string, unknown>) => {
    const user = value as { id: string; name: string } | null;
    return (
      <button
        data-testid="assignee-select"
        disabled={disabled as boolean}
        onClick={() =>
          (onChange as (v: { id: string; name: string; email: string } | null) => void)({
            id: 'user-2',
            name: 'Jane',
            email: 'jane@test.com',
          })
        }
      >
        Assignee: {user?.name ?? 'Unassigned'}
      </button>
    );
  },
  LabelSelector: ({ selectedLabels, onChange, disabled }: Record<string, unknown>) => {
    const labels = selectedLabels as { id: string; name: string }[];
    return (
      <button
        data-testid="label-select"
        disabled={disabled as boolean}
        onClick={() =>
          (
            onChange as (
              v: { id: string; name: string; color: string; projectId: string }[]
            ) => void
          )([{ id: 'label-1', name: 'Bug', color: '#ff0000', projectId: 'proj-1' }])
        }
      >
        Labels: {labels.map((l) => l.name).join(', ') || 'None'}
      </button>
    );
  },
}));

vi.mock('@/features/issues/components/linked-prs-list', () => ({
  LinkedPRsList: ({ links }: { links: IntegrationLink[] }) => (
    <div data-testid="linked-prs">PRs: {links.length}</div>
  ),
}));

vi.mock('@/features/issues/components/source-notes-list', () => ({
  SourceNotesList: ({
    links,
    workspaceSlug,
  }: {
    links: NoteIssueLink[];
    workspaceSlug: string;
  }) => (
    <div data-testid="source-notes" data-slug={workspaceSlug}>
      Notes: {links.length}
    </div>
  ),
}));

vi.mock('@/components/ui/calendar', () => ({
  Calendar: ({ onSelect }: { onSelect: (d: Date | undefined) => void }) => (
    <button data-testid="calendar" onClick={() => onSelect(new Date('2025-03-15'))}>
      Pick date
    </button>
  ),
}));

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

function createIssue(overrides?: Partial<Issue>): Issue {
  return {
    id: 'issue-1',
    identifier: 'PS-42',
    name: 'Test Issue',
    title: 'Test Issue',
    state: { id: 'state-1', name: 'Todo', color: '#5B8FC9', group: 'unstarted' },
    priority: 'medium',
    type: 'task',
    projectId: 'proj-1',
    workspaceId: 'ws-1',
    sequenceId: 42,
    sortOrder: 1,
    assignee: { id: 'user-1', email: 'john@test.com', displayName: 'John Doe' },
    reporterId: 'user-1',
    reporter: { id: 'user-1', email: 'john@test.com', displayName: 'John Doe' },
    labels: [{ id: 'label-1', name: 'Bug', color: '#ff0000' }],
    estimatePoints: 3,
    startDate: '2025-01-15',
    targetDate: '2025-02-28',
    cycleId: 'cycle-1',
    subIssueCount: 0,
    project: { id: 'proj-1', name: 'Project', identifier: 'PS' },
    aiGenerated: false,
    hasAiEnhancements: false,
    createdAt: '2025-01-01T00:00:00Z',
    updatedAt: '2025-01-10T12:00:00Z',
    ...overrides,
  };
}

const mockMembers: WorkspaceMember[] = [
  {
    userId: 'user-1',
    email: 'john@test.com',
    fullName: 'John Doe',
    avatarUrl: null,
    role: 'admin',
    joinedAt: '2025-01-01',
  },
  {
    userId: 'user-2',
    email: 'jane@test.com',
    fullName: 'Jane Smith',
    avatarUrl: null,
    role: 'member',
    joinedAt: '2025-01-02',
  },
];

const mockLabels: Label[] = [
  { id: 'label-1', name: 'Bug', color: '#ff0000', projectId: 'proj-1' },
  { id: 'label-2', name: 'Feature', color: '#00ff00', projectId: 'proj-1' },
];

const mockCycles: Cycle[] = [
  {
    id: 'cycle-1',
    workspaceId: 'ws-1',
    name: 'Sprint 1',
    status: 'active',
    sequence: 1,
    createdAt: '2025-01-01',
    updatedAt: '2025-01-01',
    project: { id: 'proj-1', name: 'Project', identifier: 'PS' },
    issueCount: 5,
  },
];

const mockStates: StateBrief[] = [
  { id: 'state-1', name: 'Todo', color: '#5B8FC9', group: 'unstarted' },
  { id: 'state-2', name: 'In Progress', color: '#D9853F', group: 'started' },
  { id: 'state-3', name: 'Done', color: '#29A386', group: 'completed' },
];

const defaultProps = {
  issue: createIssue(),
  workspaceId: 'ws-1',
  workspaceSlug: 'my-team',
  members: mockMembers,
  labels: mockLabels,
  cycles: mockCycles,
  states: mockStates,
  onUpdate: vi.fn().mockResolvedValue(undefined),
};

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('IssuePropertiesPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGetSaveStatus.mockReturnValue('idle');
  });

  // --- Rendering ---

  it('renders all four sections', () => {
    render(<IssuePropertiesPanel {...defaultProps} />);

    expect(screen.getByText('Properties')).toBeInTheDocument();
    expect(screen.getByText('Dates')).toBeInTheDocument();
    expect(screen.getByText('Details')).toBeInTheDocument();
    expect(screen.getByText('Linked Items')).toBeInTheDocument();
  });

  it('renders the aside with aria-label', () => {
    render(<IssuePropertiesPanel {...defaultProps} />);

    expect(screen.getByRole('complementary', { name: 'Issue properties' })).toBeInTheDocument();
  });

  it('renders all property selectors', () => {
    render(<IssuePropertiesPanel {...defaultProps} />);

    expect(screen.getByTestId('state-select')).toBeInTheDocument();
    expect(screen.getByTestId('priority-select')).toBeInTheDocument();
    expect(screen.getByTestId('type-select')).toBeInTheDocument();
    expect(screen.getByTestId('assignee-select')).toBeInTheDocument();
    expect(screen.getByTestId('label-select')).toBeInTheDocument();
    expect(screen.getByTestId('cycle-select')).toBeInTheDocument();
    expect(screen.getByTestId('estimate-select')).toBeInTheDocument();
  });

  it('renders reporter with initials', () => {
    render(<IssuePropertiesPanel {...defaultProps} />);

    expect(screen.getByText('JD')).toBeInTheDocument();
    expect(screen.getByText('John Doe')).toBeInTheDocument();
  });

  it('renders created and updated dates', () => {
    render(<IssuePropertiesPanel {...defaultProps} />);

    expect(screen.getByText('Jan 1, 2025')).toBeInTheDocument();
    expect(screen.getByText('Jan 10, 2025')).toBeInTheDocument();
  });

  it('renders linked PRs and source notes', () => {
    const links: IntegrationLink[] = [
      {
        id: 'link-1',
        issueId: 'issue-1',
        integrationType: 'github_pr',
        externalId: '123',
        externalUrl: 'https://github.com/test/pr/1',
        prNumber: 1,
        prTitle: 'Fix bug',
        prStatus: 'open',
      },
    ];
    const noteLinks: NoteIssueLink[] = [
      {
        id: 'nl-1',
        noteId: 'note-1',
        issueId: 'issue-1',
        linkType: 'EXTRACTED',
        noteTitle: 'Meeting notes',
      },
    ];

    render(
      <IssuePropertiesPanel {...defaultProps} integrationLinks={links} noteLinks={noteLinks} />
    );

    expect(screen.getByTestId('linked-prs')).toHaveTextContent('PRs: 1');
    expect(screen.getByTestId('source-notes')).toHaveTextContent('Notes: 1');
    expect(screen.getByTestId('source-notes')).toHaveAttribute('data-slug', 'my-team');
  });

  // --- State mapping ---

  it('maps state group to IssueState for the state select', () => {
    render(<IssuePropertiesPanel {...defaultProps} />);

    expect(screen.getByTestId('state-select')).toHaveAttribute('data-value', 'todo');
  });

  it('maps backlog state group correctly', () => {
    const issue = createIssue({
      state: { id: 'state-b', name: 'Backlog', color: '#9C9590', group: 'backlog' },
    });

    render(<IssuePropertiesPanel {...defaultProps} issue={issue} />);

    expect(screen.getByTestId('state-select')).toHaveAttribute('data-value', 'backlog');
  });

  // --- onUpdate calls ---

  it('calls onUpdate with priority on priority change', async () => {
    const onUpdate = vi.fn().mockResolvedValue(undefined);
    render(<IssuePropertiesPanel {...defaultProps} onUpdate={onUpdate} />);

    fireEvent.click(screen.getByTestId('priority-select'));

    await waitFor(() => {
      expect(onUpdate).toHaveBeenCalledWith({ priority: 'high' });
    });
  });

  it('calls onUpdate with assigneeId on assignee change', async () => {
    const onUpdate = vi.fn().mockResolvedValue(undefined);
    render(<IssuePropertiesPanel {...defaultProps} onUpdate={onUpdate} />);

    fireEvent.click(screen.getByTestId('assignee-select'));

    await waitFor(() => {
      expect(onUpdate).toHaveBeenCalledWith({ assigneeId: 'user-2' });
    });
  });

  it('calls onUpdate with labelIds on label change', async () => {
    const onUpdate = vi.fn().mockResolvedValue(undefined);
    render(<IssuePropertiesPanel {...defaultProps} onUpdate={onUpdate} />);

    fireEvent.click(screen.getByTestId('label-select'));

    await waitFor(() => {
      expect(onUpdate).toHaveBeenCalledWith({ labelIds: ['label-1'] });
    });
  });

  it('calls onUpdate with cycleId on cycle change', async () => {
    const onUpdate = vi.fn().mockResolvedValue(undefined);
    render(<IssuePropertiesPanel {...defaultProps} onUpdate={onUpdate} />);

    fireEvent.click(screen.getByTestId('cycle-select'));

    await waitFor(() => {
      expect(onUpdate).toHaveBeenCalledWith({ cycleId: 'cycle-2' });
    });
  });

  it('calls onUpdate with estimatePoints on estimate change', async () => {
    const onUpdate = vi.fn().mockResolvedValue(undefined);
    render(<IssuePropertiesPanel {...defaultProps} onUpdate={onUpdate} />);

    fireEvent.click(screen.getByTestId('estimate-select'));

    await waitFor(() => {
      expect(onUpdate).toHaveBeenCalledWith({ estimatePoints: 5 });
    });
  });

  it('calls onUpdate with stateId when state changes and states prop provided', async () => {
    const onUpdate = vi.fn().mockResolvedValue(undefined);
    render(<IssuePropertiesPanel {...defaultProps} onUpdate={onUpdate} />);

    fireEvent.click(screen.getByTestId('state-select'));

    await waitFor(() => {
      expect(onUpdate).toHaveBeenCalledWith({ stateId: 'state-2' });
    });
  });

  // --- Disabled state ---

  it('disables all selectors when disabled prop is true', () => {
    render(<IssuePropertiesPanel {...defaultProps} disabled />);

    expect(screen.getByTestId('priority-select')).toBeDisabled();
    expect(screen.getByTestId('type-select')).toBeDisabled();
    expect(screen.getByTestId('assignee-select')).toBeDisabled();
    expect(screen.getByTestId('label-select')).toBeDisabled();
    expect(screen.getByTestId('cycle-select')).toBeDisabled();
    expect(screen.getByTestId('estimate-select')).toBeDisabled();
  });

  it('disables state select when no states provided', () => {
    render(<IssuePropertiesPanel {...defaultProps} states={[]} />);

    expect(screen.getByTestId('state-select')).toBeDisabled();
  });

  // --- Edge cases ---

  it('shows email when reporter displayName is null', () => {
    const issue = createIssue({
      reporter: { id: 'user-3', email: 'anon@test.com', displayName: null },
    });

    render(<IssuePropertiesPanel {...defaultProps} issue={issue} />);

    expect(screen.getByText('anon@test.com')).toBeInTheDocument();
  });

  it('handles issue with no assignee', () => {
    const issue = createIssue({ assignee: null });

    render(<IssuePropertiesPanel {...defaultProps} issue={issue} />);

    expect(screen.getByTestId('assignee-select')).toHaveTextContent('Unassigned');
  });

  it('handles issue with no cycle', () => {
    const issue = createIssue({ cycleId: undefined });

    render(<IssuePropertiesPanel {...defaultProps} issue={issue} />);

    expect(screen.getByTestId('cycle-select')).toHaveTextContent('None');
  });

  it('renders with empty integration and note links by default', () => {
    render(<IssuePropertiesPanel {...defaultProps} />);

    expect(screen.getByTestId('linked-prs')).toHaveTextContent('PRs: 0');
    expect(screen.getByTestId('source-notes')).toHaveTextContent('Notes: 0');
  });

  // --- Save status ---

  it('calls setSaveStatus during mutation lifecycle', async () => {
    const onUpdate = vi.fn().mockResolvedValue(undefined);
    render(<IssuePropertiesPanel {...defaultProps} onUpdate={onUpdate} />);

    fireEvent.click(screen.getByTestId('priority-select'));

    await waitFor(() => {
      expect(mockSetSaveStatus).toHaveBeenCalledWith('priority', 'saving');
    });

    await waitFor(() => {
      expect(mockSetSaveStatus).toHaveBeenCalledWith('priority', 'saved');
    });
  });

  it('sets error status when onUpdate rejects', async () => {
    // Suppress the expected unhandled rejection
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
    const onUpdate = vi.fn().mockRejectedValue(new Error('Network error'));
    render(<IssuePropertiesPanel {...defaultProps} onUpdate={onUpdate} />);

    fireEvent.click(screen.getByTestId('priority-select'));

    await waitFor(() => {
      expect(mockSetSaveStatus).toHaveBeenCalledWith('priority', 'error');
    });

    consoleError.mockRestore();
  });
});

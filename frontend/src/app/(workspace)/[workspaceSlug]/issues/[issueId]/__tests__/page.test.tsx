/**
 * IssueDetailPage composition tests.
 *
 * T047: Verifies the refactored page composes all child components correctly
 * with proper props and conditional rendering logic.
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import type { Issue } from '@/types';

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

vi.mock('next/navigation', () => ({
  useParams: () => ({ workspaceSlug: 'test-ws', issueId: 'issue-1' }),
  useRouter: () => ({ push: vi.fn() }),
}));

const mockUseIssueDetail = vi.fn((_issueId: string) => ({
  data: undefined as Issue | undefined,
  isLoading: false,
  isError: false,
}));
const mockUseUpdateIssue = vi.fn((_workspaceId: string, _issueId: string) => ({
  mutateAsync: vi.fn(),
}));
const mockUseWorkspaceMembers = vi.fn((_workspaceId: string) => ({ data: [] }));
const mockUseWorkspaceLabels = vi.fn((_workspaceId: string) => ({ data: [] }));
const mockUseProjectCycles = vi.fn((_workspaceId: string, _projectId: string) => ({
  data: undefined,
}));
const mockUseIssueKeyboardShortcuts = vi.fn((_onDelete: () => void) => {});

vi.mock('@/features/issues/hooks', async () => {
  return {
    useIssueDetail: (issueId: string) => mockUseIssueDetail(issueId),
    useUpdateIssue: (workspaceId: string, issueId: string) =>
      mockUseUpdateIssue(workspaceId, issueId),
    useWorkspaceMembers: (workspaceId: string) => mockUseWorkspaceMembers(workspaceId),
    useWorkspaceLabels: (workspaceId: string) => mockUseWorkspaceLabels(workspaceId),
    useProjectCycles: (workspaceId: string, projectId: string) =>
      mockUseProjectCycles(workspaceId, projectId),
    useIssueKeyboardShortcuts: (onDelete: () => void) => mockUseIssueKeyboardShortcuts(onDelete),
  };
});

vi.mock('@/stores', () => ({
  useStore: () => ({
    workspaceStore: { currentWorkspace: { id: 'ws-1', slug: 'test-ws' } },
    aiStore: { settings: { aiContextEnabled: true } },
    issueStore: { deleteIssue: vi.fn() },
  }),
}));

vi.mock('@/features/issues/components', () => ({
  IssueHeader: (props: Record<string, unknown>) => (
    <div data-testid="issue-header" data-identifier={props.identifier} />
  ),
  AIContextSidebar: (props: Record<string, unknown>) => (
    <div data-testid="ai-context-sidebar" data-open={String(props.open)} />
  ),
  IssueTitle: (props: Record<string, unknown>) => (
    <div data-testid="issue-title">{String(props.title)}</div>
  ),
  IssueDescriptionEditor: (props: Record<string, unknown>) => (
    <div data-testid="issue-description-editor" data-content={(props.content as string) ?? ''} />
  ),
  SubIssuesList: () => <div data-testid="sub-issues-list" />,
  ActivityTimeline: (props: Record<string, unknown>) => (
    <div data-testid="activity-timeline" data-workspace-id={props.workspaceId} />
  ),
  IssuePropertiesPanel: (props: Record<string, unknown>) => (
    <div data-testid="issue-properties-panel" data-workspace-id={props.workspaceId} />
  ),
}));

vi.mock('@/components/ui/button', () => ({
  Button: (props: Record<string, unknown>) => (
    <button data-testid="button" onClick={props.onClick as () => void}>
      {props.children as React.ReactNode}
    </button>
  ),
}));

vi.mock('@/components/ui/skeleton', () => ({
  Skeleton: (props: Record<string, unknown>) => (
    <div data-testid="skeleton" className={props.className as string} />
  ),
}));

vi.mock('@/components/ui/separator', () => ({
  Separator: () => <hr data-testid="separator" />,
}));

vi.mock('mobx-react-lite', () => ({
  observer: (component: React.FC) => component,
}));

// ---------------------------------------------------------------------------
// Test data
// ---------------------------------------------------------------------------

const mockIssue = {
  id: 'issue-1',
  identifier: 'PS-42',
  name: 'Test Issue',
  description: 'Test description',
  descriptionHtml: '<p>Test description</p>',
  state: {
    id: 'state-1',
    name: 'Todo',
    color: '#5B8FC9',
    group: 'unstarted' as const,
  },
  priority: 'medium' as const,
  type: 'feature' as const,
  projectId: 'proj-1',
  workspaceId: 'ws-1',
  sequenceId: 42,
  sortOrder: 0,
  reporter: { id: 'user-1', email: 'test@test.com', displayName: 'Test User' },
  reporterId: 'user-1',
  labels: [],
  subIssueCount: 0,
  project: { id: 'proj-1', name: 'Test Project', identifier: 'PS' },
  aiGenerated: false,
  hasAiEnhancements: false,
  createdAt: '2024-01-01T00:00:00Z',
  updatedAt: '2024-01-01T00:00:00Z',
};

// ---------------------------------------------------------------------------
// Import page component (after mocks)
// ---------------------------------------------------------------------------

import IssueDetailPage from '../page';

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('IssueDetailPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseIssueDetail.mockReturnValue({
      data: mockIssue,
      isLoading: false,
      isError: false,
    });
  });

  it('shows loading skeleton when isLoading', () => {
    mockUseIssueDetail.mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
    });

    render(<IssueDetailPage />);

    const skeletons = screen.getAllByTestId('skeleton');
    expect(skeletons.length).toBeGreaterThan(0);
    expect(screen.queryByTestId('issue-header')).not.toBeInTheDocument();
  });

  it('shows "Issue not found" when no issue data', () => {
    mockUseIssueDetail.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: false,
    });

    render(<IssueDetailPage />);

    expect(screen.getByText('Issue not found')).toBeInTheDocument();
    expect(screen.getByText('Back to issues')).toBeInTheDocument();
  });

  it('renders IssueHeader with correct identifier', () => {
    render(<IssueDetailPage />);

    const header = screen.getByTestId('issue-header');
    expect(header).toBeInTheDocument();
    expect(header).toHaveAttribute('data-identifier', 'PS-42');
  });

  it('renders IssueTitle with issue.name', () => {
    render(<IssueDetailPage />);

    const title = screen.getByTestId('issue-title');
    expect(title).toBeInTheDocument();
    expect(title).toHaveTextContent('Test Issue');
  });

  it('renders IssueDescriptionEditor with descriptionHtml', () => {
    render(<IssueDetailPage />);

    const editor = screen.getByTestId('issue-description-editor');
    expect(editor).toBeInTheDocument();
    expect(editor).toHaveAttribute('data-content', '<p>Test description</p>');
  });

  it('falls back to plain description when descriptionHtml is null', () => {
    mockUseIssueDetail.mockReturnValue({
      data: { ...mockIssue, descriptionHtml: undefined, description: 'Plain text description' },
      isLoading: false,
      isError: false,
    });

    render(<IssueDetailPage />);

    const editor = screen.getByTestId('issue-description-editor');
    expect(editor).toHaveAttribute('data-content', 'Plain text description');
  });

  it('renders ActivityTimeline', () => {
    render(<IssueDetailPage />);

    expect(screen.getByTestId('activity-timeline')).toBeInTheDocument();
  });

  it('renders IssuePropertiesPanel', () => {
    render(<IssueDetailPage />);

    expect(screen.getByTestId('issue-properties-panel')).toBeInTheDocument();
  });

  it('renders SubIssuesList', () => {
    render(<IssueDetailPage />);

    expect(screen.getByTestId('sub-issues-list')).toBeInTheDocument();
  });

  it('AI Context tab initially inactive', () => {
    render(<IssueDetailPage />);

    // AI Context is rendered as a tab; the "ai-context" tab content should be inactive by default
    const tabPanels = screen.getAllByRole('tabpanel', { hidden: true });
    const aiPanel = tabPanels.find((panel) => panel.id.includes('ai-context'));
    expect(aiPanel).toBeDefined();
    expect(aiPanel).toHaveAttribute('data-state', 'inactive');
  });

  it('passes correct workspaceId to child components', () => {
    render(<IssueDetailPage />);

    const propsPanel = screen.getByTestId('issue-properties-panel');
    expect(propsPanel).toHaveAttribute('data-workspace-id', 'ws-1');

    const timeline = screen.getByTestId('activity-timeline');
    expect(timeline).toHaveAttribute('data-workspace-id', 'ws-1');
  });
});

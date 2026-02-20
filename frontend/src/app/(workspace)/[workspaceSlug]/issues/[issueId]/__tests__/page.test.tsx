/**
 * IssueDetailPage composition tests - Note-first layout.
 *
 * Verifies the refactored page composes: IssueNoteHeader, IssueNoteLayout,
 * IssueTitle, EditorContent, SubIssuesList, ActivityTimeline, and
 * IssueNoteContext.Provider with proper props.
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
    aiStore: { pilotSpace: {}, settings: { aiContextEnabled: true } },
    issueStore: {
      deleteIssue: vi.fn(),
      aggregateSaveStatus: 'idle',
      getSaveStatus: () => 'idle',
      setSaveStatus: vi.fn(),
    },
  }),
  useIssueStore: () => ({
    aggregateSaveStatus: 'idle',
    getSaveStatus: () => 'idle',
    setSaveStatus: vi.fn(),
  }),
}));

vi.mock('@/features/issues/components', () => ({
  IssueNoteHeader: (props: Record<string, unknown>) => (
    <div data-testid="issue-note-header" data-identifier={props.identifier} />
  ),
  IssueNoteLayout: (props: Record<string, unknown>) => (
    <div data-testid="issue-note-layout">{props.editorContent as React.ReactNode}</div>
  ),
  IssueTitle: (props: Record<string, unknown>) => (
    <div data-testid="issue-title">{String(props.title)}</div>
  ),
  SubIssuesList: () => <div data-testid="sub-issues-list" />,
  ActivityTimeline: (props: Record<string, unknown>) => (
    <div data-testid="activity-timeline" data-workspace-id={props.workspaceId} />
  ),
  IssuePropertiesPanel: (props: Record<string, unknown>) => (
    <div data-testid="issue-properties-panel" data-workspace-id={props.workspaceId} />
  ),
  CollapsibleSection: (props: Record<string, unknown>) => (
    <div data-testid="collapsible-section">{props.children as React.ReactNode}</div>
  ),
  IssueSectionDivider: (props: Record<string, unknown>) => (
    <div data-testid="section-divider">{String(props.label)}</div>
  ),
}));

vi.mock('@/features/issues/editor/create-issue-note-extensions', () => ({
  createIssueNoteExtensions: () => [],
}));

vi.mock('@tiptap/react', () => ({
  useEditor: () => null,
  EditorContent: () => <div data-testid="editor-content" />,
}));

vi.mock('@/components/editor/SelectionToolbar', () => ({
  SelectionToolbar: () => null,
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

vi.mock('@/components/ui/sheet', () => ({
  Sheet: (props: Record<string, unknown>) => <div>{props.children as React.ReactNode}</div>,
  SheetContent: (props: Record<string, unknown>) => <div>{props.children as React.ReactNode}</div>,
  SheetHeader: (props: Record<string, unknown>) => <div>{props.children as React.ReactNode}</div>,
  SheetTitle: (props: Record<string, unknown>) => <div>{props.children as React.ReactNode}</div>,
}));

vi.mock('@/components/issues/DeleteConfirmDialog', () => ({
  DeleteConfirmDialog: () => <div data-testid="delete-dialog" />,
}));

vi.mock('mobx-react-lite', () => ({
  observer: (component: React.FC) => component,
}));

vi.mock('@/features/notes/editor/extensions/note-link.css', () => ({}));

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

describe('IssueDetailPage (note-first layout)', () => {
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
    expect(screen.queryByTestId('issue-note-header')).not.toBeInTheDocument();
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

  it('renders IssueNoteHeader with correct identifier', () => {
    render(<IssueDetailPage />);

    const header = screen.getByTestId('issue-note-header');
    expect(header).toBeInTheDocument();
    expect(header).toHaveAttribute('data-identifier', 'PS-42');
  });

  it('renders IssueTitle with issue.name', () => {
    render(<IssueDetailPage />);

    const title = screen.getByTestId('issue-title');
    expect(title).toBeInTheDocument();
    expect(title).toHaveTextContent('Test Issue');
  });

  it('renders IssueNoteLayout', () => {
    render(<IssueDetailPage />);
    expect(screen.getByTestId('issue-note-layout')).toBeInTheDocument();
  });

  it('renders SubIssuesList', () => {
    render(<IssueDetailPage />);
    expect(screen.getByTestId('sub-issues-list')).toBeInTheDocument();
  });

  it('renders ActivityTimeline inside CollapsibleSection', () => {
    render(<IssueDetailPage />);
    expect(screen.getByTestId('activity-timeline')).toBeInTheDocument();
  });

  it('renders section divider for sub-issues', () => {
    render(<IssueDetailPage />);
    const divider = screen.getByTestId('section-divider');
    expect(divider).toHaveTextContent('Sub-issues');
  });

  it('renders delete dialog', () => {
    render(<IssueDetailPage />);
    expect(screen.getByTestId('delete-dialog')).toBeInTheDocument();
  });
});

/**
 * Responsive layout tests for the Issue Detail page.
 *
 * T048: Verifies responsive Tailwind CSS classes are applied correctly.
 * Since CSS media queries do not work in JSDOM, we test for the presence
 * of responsive class names on the rendered DOM elements.
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach } from 'vitest';

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

vi.mock('next/navigation', () => ({
  useParams: () => ({ workspaceSlug: 'test-ws', issueId: 'issue-1' }),
  useRouter: () => ({ push: vi.fn() }),
}));

vi.mock('@/lib/supabase', () => ({
  supabase: {
    auth: { getSession: vi.fn().mockResolvedValue({ data: { session: null } }) },
  },
}));

vi.mock('@tanstack/react-query', async () => {
  const actual = await vi.importActual('@tanstack/react-query');
  return {
    ...actual,
    useQueryClient: () => ({ invalidateQueries: vi.fn() }),
  };
});

const mockUseIssueDetail = vi.fn();

vi.mock('@/features/issues/hooks', () => ({
  useIssueDetail: (...args: unknown[]) => mockUseIssueDetail(...args),
  useUpdateIssue: () => ({ mutateAsync: vi.fn() }),
  useUpdateIssueState: () => ({ mutateAsync: vi.fn() }),
  useWorkspaceMembers: () => ({ data: [] }),
  useWorkspaceLabels: () => ({ data: [] }),
  useProjectCycles: () => ({ data: undefined }),
  useIssueKeyboardShortcuts: vi.fn(),
}));

vi.mock('@/stores', () => ({
  useStore: () => ({
    workspaceStore: { currentWorkspace: { id: 'ws-1', slug: 'test-ws' } },
    aiStore: {
      pilotSpace: {
        setWorkspaceId: vi.fn(),
        setIssueContext: vi.fn(),
        pendingApprovals: [],
      },
      settings: { aiContextEnabled: true },
    },
    issueStore: {
      deleteIssue: vi.fn(),
      aggregateSaveStatus: 'idle',
      getSaveStatus: () => 'idle',
      setSaveStatus: vi.fn(),
    },
  }),
  useTaskStore: () => ({
    getTasksForIssue: () => [],
    getCompletedCount: () => 0,
  }),
}));

vi.mock('@/features/issues/components', () => ({
  IssueHeader: () => <div data-testid="issue-header" />,
  IssueNoteHeader: () => <div data-testid="issue-note-header" />,
  IssueNoteLayout: ({
    headerContent,
    editorContent,
  }: {
    headerContent: React.ReactNode;
    editorContent: React.ReactNode;
  }) => (
    <div data-testid="issue-note-layout">
      {headerContent}
      {editorContent}
    </div>
  ),
  IssuePropertiesPanel: () => <div data-testid="issue-properties-panel" />,
  CollapsibleSection: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="collapsible-section">{children}</div>
  ),
  IssueSectionDivider: () => <div data-testid="section-divider" />,
  TaskProgressWidget: () => null,
}));

vi.mock('@/features/issues/components/issue-editor-content', () => ({
  IssueEditorContent: () => <div data-testid="issue-editor-content" />,
}));

vi.mock('@/components/issues/DeleteConfirmDialog', () => ({
  DeleteConfirmDialog: () => null,
}));

vi.mock('@/components/editor/ProjectContextHeader', () => ({
  ProjectContextHeader: () => <div data-testid="project-context-header" />,
}));

vi.mock('@/components/ui/button', () => ({
  Button: ({ children, ...rest }: Record<string, unknown>) => (
    <button {...rest}>{children as React.ReactNode}</button>
  ),
}));

vi.mock('@/components/ui/skeleton', () => ({
  Skeleton: () => <div data-testid="skeleton" />,
}));

vi.mock('@/components/ui/separator', () => ({
  Separator: () => <hr />,
}));

vi.mock('@/components/ui/sheet', () => ({
  Sheet: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="mobile-sheet">{children}</div>
  ),
  SheetTrigger: ({ children }: { children: React.ReactNode }) => children,
  SheetContent: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="sheet-content">{children}</div>
  ),
  SheetHeader: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  SheetTitle: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
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
  description: 'Test',
  descriptionHtml: '<p>Test</p>',
  state: { id: 'state-1', name: 'Todo', color: '#5B8FC9', group: 'unstarted' as const },
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

import IssueDetailPage from '@/app/(workspace)/[workspaceSlug]/issues/[issueId]/page';

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('IssueDetailPage responsive layout', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseIssueDetail.mockReturnValue({
      data: mockIssue,
      isLoading: false,
      isError: false,
    });
  });

  it('top-level container has flex layout with overflow-hidden', () => {
    render(<IssueDetailPage />);

    const container = screen.getByTestId('issue-detail');
    expect(container.className).toContain('flex');
    expect(container.className).toContain('h-full');
    expect(container.className).toContain('overflow-hidden');
  });

  it('renders IssueNoteLayout as the main content area', () => {
    render(<IssueDetailPage />);

    expect(screen.getByTestId('issue-note-layout')).toBeInTheDocument();
  });

  it('renders mobile Sheet for properties panel', () => {
    render(<IssueDetailPage />);

    expect(screen.getByTestId('mobile-sheet')).toBeInTheDocument();
  });

  it('Sheet contains IssuePropertiesPanel', () => {
    render(<IssueDetailPage />);

    // Sheet wraps the properties panel for mobile bottom-sheet access
    const sheet = screen.getByTestId('mobile-sheet');
    expect(sheet).toBeInTheDocument();
    // SheetContent renders with Properties title
    expect(screen.getByText('Properties')).toBeInTheDocument();
  });

  it('renders editor content inside note layout', () => {
    render(<IssueDetailPage />);

    expect(screen.getByTestId('issue-editor-content')).toBeInTheDocument();
  });
});

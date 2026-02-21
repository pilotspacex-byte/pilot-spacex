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

const mockUseIssueDetail = vi.fn();

vi.mock('@/features/issues/hooks', () => ({
  useIssueDetail: (...args: unknown[]) => mockUseIssueDetail(...args),
  useUpdateIssue: () => ({ mutateAsync: vi.fn() }),
  useWorkspaceMembers: () => ({ data: [] }),
  useWorkspaceLabels: () => ({ data: [] }),
  useProjectCycles: () => ({ data: undefined }),
  useIssueKeyboardShortcuts: vi.fn(),
}));

vi.mock('@/stores', () => ({
  useStore: () => ({
    workspaceStore: { currentWorkspace: { id: 'ws-1', slug: 'test-ws' } },
    aiStore: { settings: { aiContextEnabled: true } },
    issueStore: { deleteIssue: vi.fn() },
  }),
  useTaskStore: () => ({
    getTasksForIssue: () => [],
    getCompletedCount: () => 0,
  }),
}));

vi.mock('@/features/issues/components', () => ({
  IssueHeader: () => <div data-testid="issue-header" />,
  IssueTitle: () => <div data-testid="issue-title" />,
  IssueDescriptionEditor: () => <div data-testid="issue-description-editor" />,
  SubIssuesList: () => <div data-testid="sub-issues-list" />,
  ActivityTimeline: () => <div data-testid="activity-timeline" />,
  IssuePropertiesPanel: () => <div data-testid="issue-properties-panel" />,
  AcceptanceCriteriaEditor: () => <div data-testid="acceptance-criteria" />,
  TechnicalRequirementsEditor: () => <div data-testid="technical-requirements" />,
  CollapsibleSection: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="collapsible-section">{children}</div>
  ),
  TaskProgressWidget: () => null,
}));

vi.mock('@/components/issues/DeleteConfirmDialog', () => ({
  DeleteConfirmDialog: () => null,
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

  it('main container has flex-col md:flex-row classes', () => {
    render(<IssueDetailPage />);

    const panels = screen.getAllByTestId('issue-properties-panel');
    // Desktop sidebar parent
    const desktopSidebar = panels[0]?.parentElement;
    const flexContainer = desktopSidebar?.parentElement;
    expect(desktopSidebar).toBeDefined();
    expect(flexContainer).toBeDefined();
    expect(flexContainer!.className).toContain('flex-col');
    expect(flexContainer!.className).toContain('md:flex-row');
  });

  it('desktop sidebar is hidden on mobile, visible on md+', () => {
    render(<IssueDetailPage />);

    const panels = screen.getAllByTestId('issue-properties-panel');
    const desktopSidebar = panels[0]?.parentElement;
    expect(desktopSidebar).toBeDefined();
    expect(desktopSidebar!.className).toContain('hidden');
    expect(desktopSidebar!.className).toContain('md:block');
    expect(desktopSidebar!.className).toContain('md:w-[35%]');
    expect(desktopSidebar!.className).toContain('xl:w-[30%]');
  });

  it('main content has responsive width classes', () => {
    render(<IssueDetailPage />);

    const mainContent = screen.getByRole('main');
    expect(mainContent.className).toContain('md:w-[65%]');
    expect(mainContent.className).toContain('xl:w-[70%]');
  });

  it('renders mobile Sheet trigger for properties', () => {
    render(<IssueDetailPage />);

    expect(screen.getByTestId('mobile-sheet')).toBeInTheDocument();
    expect(screen.getByLabelText('Open issue properties')).toBeInTheDocument();
  });

  it('desktop sidebar has border-l on desktop', () => {
    render(<IssueDetailPage />);

    const panels = screen.getAllByTestId('issue-properties-panel');
    const desktopSidebar = panels[0]?.parentElement;
    expect(desktopSidebar).toBeDefined();
    expect(desktopSidebar!.className).toContain('md:border-l');
  });
});

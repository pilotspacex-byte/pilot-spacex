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
}));

vi.mock('@/features/issues/components', () => ({
  IssueHeader: () => <div data-testid="issue-header" />,
  AIContextSidebar: () => <div data-testid="ai-context-sidebar" />,
  IssueTitle: () => <div data-testid="issue-title" />,
  IssueDescriptionEditor: () => <div data-testid="issue-description-editor" />,
  SubIssuesList: () => <div data-testid="sub-issues-list" />,
  ActivityTimeline: () => <div data-testid="activity-timeline" />,
  IssuePropertiesPanel: () => <div data-testid="issue-properties-panel" />,
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

    // The flex container wrapping sidebar + main content
    const flexContainer =
      screen.getByTestId('issue-properties-panel').parentElement!.parentElement!;
    expect(flexContainer.className).toContain('flex-col');
    expect(flexContainer.className).toContain('md:flex-row');
  });

  it('properties sidebar has responsive width classes', () => {
    render(<IssueDetailPage />);

    const sidebar = screen.getByTestId('issue-properties-panel').parentElement!;
    expect(sidebar.className).toContain('md:w-[35%]');
    expect(sidebar.className).toContain('xl:w-[30%]');
  });

  it('main content has responsive width classes', () => {
    render(<IssueDetailPage />);

    const mainContent = screen.getByRole('main');
    expect(mainContent.className).toContain('md:w-[65%]');
    expect(mainContent.className).toContain('xl:w-[70%]');
  });

  it('properties sidebar has order-first md:order-last for mobile-first layout', () => {
    render(<IssueDetailPage />);

    const sidebar = screen.getByTestId('issue-properties-panel').parentElement!;
    expect(sidebar.className).toContain('order-first');
    expect(sidebar.className).toContain('md:order-last');
  });

  it('sidebar has border-b on mobile, border-l on desktop', () => {
    render(<IssueDetailPage />);

    const sidebar = screen.getByTestId('issue-properties-panel').parentElement!;
    expect(sidebar.className).toContain('border-b');
    expect(sidebar.className).toContain('md:border-b-0');
    expect(sidebar.className).toContain('md:border-l');
  });
});

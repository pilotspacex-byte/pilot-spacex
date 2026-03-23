/**
 * IssueEditorContent — knowledge graph integration tests.
 *
 * Verifies:
 * - IssueKnowledgeGraphMini section renders inside the editor
 * - onExpandGraphFullView prop is wired to the mini graph component
 * - GitHubImplementationSection renders in place of GitHubSection
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { Issue } from '@/types';

// ---------------------------------------------------------------------------
// Mocks — declared before importing the component under test
// ---------------------------------------------------------------------------

vi.mock('next/dynamic', () => ({
  default: (loader: () => Promise<{ default: React.ComponentType }>) => {
    // Eagerly resolve the dynamic import for tests
    let Component: React.ComponentType | null = null;
    void loader().then((m) => {
      Component = m.default;
    });
    return function DynamicWrapper(props: Record<string, unknown>) {
      if (!Component) return null;
      return <Component {...props} />;
    };
  },
}));

vi.mock('@tiptap/react', () => ({
  useEditor: () => null,
  EditorContent: () => <div data-testid="editor-content" />,
}));

vi.mock('@/features/issues/editor/create-issue-note-extensions', () => ({
  createIssueNoteExtensions: () => [],
}));

vi.mock('@/components/editor/SelectionToolbar', () => ({
  SelectionToolbar: () => null,
}));

vi.mock('@/features/issues/components', () => ({
  IssueTitle: () => <div data-testid="issue-title" />,
  SubIssuesList: () => <div data-testid="sub-issues-list" />,
  ActivityTimeline: () => <div data-testid="activity-timeline" />,
  CollapsibleSection: ({
    title,
    children,
  }: {
    title: string;
    children: React.ReactNode;
    icon?: React.ReactNode;
    defaultOpen?: boolean;
    count?: number;
  }) => (
    <div data-testid={`collapsible-${title.toLowerCase().replace(/\s+/g, '-')}`}>
      <span>{title}</span>
      {children}
    </div>
  ),
  IssueSectionDivider: () => <div data-testid="section-divider" />,
}));

vi.mock('../issue-description-empty-state', () => ({
  IssueDescriptionEmptyState: () => null,
}));

const mockOnExpandFullView = vi.fn();
const mockOnNodeClickHighlight = vi.fn();

vi.mock('../github-implementation-section', () => ({
  GitHubImplementationSection: ({
    onAffectedNodeClick,
  }: {
    onAffectedNodeClick?: (id: string) => void;
  }) => (
    <div data-testid="github-implementation-section">
      <button onClick={() => onAffectedNodeClick?.('node-42')}>Click node</button>
    </div>
  ),
}));

vi.mock('../issue-knowledge-graph-mini', () => ({
  IssueKnowledgeGraphMini: ({
    onExpandFullView,
  }: {
    workspaceId: string;
    issueId: string;
    onExpandFullView?: () => void;
  }) => (
    <div data-testid="issue-knowledge-graph-mini">
      <button data-testid="expand-full-view" onClick={onExpandFullView}>
        Expand full view
      </button>
    </div>
  ),
}));

vi.mock('@/features/issues/hooks', () => ({
  useIssueLinks: () => ({
    pullRequests: [],
    commits: [],
    branches: [],
    isLoading: false,
  }),
}));

vi.mock('@/services/api/integrations', () => ({
  integrationsApi: {
    getGitHubInstallation: vi.fn().mockResolvedValue({ id: 'gh-install-1' }),
  },
}));

vi.mock('@tanstack/react-query', () => ({
  useQuery: ({ queryFn }: { queryFn: () => Promise<unknown> }) => {
    void queryFn;
    return { data: { id: 'gh-install-1' }, isLoading: false };
  },
}));

// ---------------------------------------------------------------------------
// Import component under test (after mocks)
// ---------------------------------------------------------------------------

import { IssueEditorContent } from '../issue-editor-content';

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const MOCK_ISSUE: Issue = {
  id: 'issue-1',
  identifier: 'PS-1',
  name: 'Test issue',
  description: null,
  descriptionHtml: null,
  type: 'bug',
  priority: 'medium',
  status: 'open',
  aiGenerated: false,
  subIssueCount: 0,
  noteLinks: [],
  project: null,
  projectId: null,
  createdAt: new Date().toISOString(),
  updatedAt: new Date().toISOString(),
} as unknown as Issue;

function renderComponent(overrides: Partial<React.ComponentProps<typeof IssueEditorContent>> = {}) {
  return render(
    <IssueEditorContent
      issue={MOCK_ISSUE}
      issueId="issue-1"
      workspaceId="ws-1"
      workspaceSlug="test-ws"
      onUpdate={vi.fn()}
      onChatOpen={vi.fn()}
      onExpandGraphFullView={mockOnExpandFullView}
      onNodeClickHighlight={mockOnNodeClickHighlight}
      {...overrides}
    />
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('IssueEditorContent — knowledge graph integration', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders IssueKnowledgeGraphMini section', () => {
    renderComponent();
    expect(screen.getByTestId('issue-knowledge-graph-mini')).toBeTruthy();
  });

  it('wires onExpandGraphFullView to the mini graph expand button', async () => {
    renderComponent();
    const expandBtn = screen.getByTestId('expand-full-view');
    fireEvent.click(expandBtn);
    await waitFor(() => {
      expect(mockOnExpandFullView).toHaveBeenCalledOnce();
    });
  });

  it('renders GitHubImplementationSection instead of GitHubSection', () => {
    renderComponent();
    expect(screen.getByTestId('github-implementation-section')).toBeTruthy();
  });

  it('wires onNodeClickHighlight to GitHubImplementationSection', async () => {
    renderComponent();
    const clickNodeBtn = screen.getByText('Click node');
    fireEvent.click(clickNodeBtn);
    await waitFor(() => {
      expect(mockOnNodeClickHighlight).toHaveBeenCalledWith('node-42');
    });
  });

  it('renders Activity section', () => {
    renderComponent();
    expect(screen.getByTestId('collapsible-activity')).toBeTruthy();
  });
});

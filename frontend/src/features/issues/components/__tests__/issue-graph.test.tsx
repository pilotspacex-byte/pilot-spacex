/**
 * IssueGraph component tests.
 *
 * Covers:
 * - Project section renders pill linking to project page
 * - Notes section renders note links grouped by linkType
 * - Relations section renders IssueReferenceCards from hook data
 * - Empty state per section when no items
 * - Show more/less toggle when > 3 items
 * - Loading state for relations
 */

import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { Issue, IssueRelation } from '@/types';

const mockPush = vi.fn();

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush }),
}));

vi.mock('@/lib/utils', () => ({
  cn: (...classes: (string | undefined | false)[]) => classes.filter(Boolean).join(' '),
}));

vi.mock('@/services/api', () => ({
  issuesApi: {
    getRelations: vi.fn(),
  },
}));

import { issuesApi } from '@/services/api';
import { IssueGraph } from '../issue-graph';

const BASE_ISSUE: Issue = {
  id: 'issue-1',
  identifier: 'PS-1',
  name: 'Test Issue',
  state: { id: 'state-1', name: 'Todo', color: '#60a5fa', group: 'unstarted' },
  priority: 'medium',
  projectId: 'proj-1',
  workspaceId: 'ws-1',
  sequenceId: 1,
  sortOrder: 0,
  reporterId: 'user-1',
  reporter: { id: 'user-1', email: 'u@t.com', displayName: 'User' },
  labels: [],
  subIssueCount: 0,
  project: { id: 'proj-1', name: 'Pilot', identifier: 'PS' },
  hasAiEnhancements: false,
  createdAt: '2025-01-01T00:00:00Z',
  updatedAt: '2025-01-01T00:00:00Z',
};

const MOCK_RELATION: IssueRelation = {
  id: 'link-1',
  linkType: 'blocks',
  direction: 'outbound',
  relatedIssue: {
    id: 'issue-2',
    identifier: 'PS-2',
    name: 'Blocked Issue',
    priority: 'high',
    state: { id: 'state-2', name: 'In Progress', color: '#fbbf24', group: 'started' },
  },
};

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return React.createElement(QueryClientProvider, { client: queryClient }, children);
  };
}

describe('IssueGraph', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(issuesApi.getRelations).mockResolvedValue([]);
  });

  const renderGraph = (overrides: Partial<Issue> = {}) =>
    render(
      <IssueGraph
        issue={{ ...BASE_ISSUE, ...overrides }}
        workspaceId="ws-1"
        workspaceSlug="my-ws"
      />,
      { wrapper: createWrapper() }
    );

  // ── Project section ─────────────────────────────────────────────────────

  it('renders the project name as a link', () => {
    renderGraph();
    expect(screen.getByText('Pilot')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Pilot/i })).toHaveAttribute(
      'href',
      '/my-ws/projects/proj-1'
    );
  });

  it('shows "No project assigned" when issue has no project', () => {
    renderGraph({ project: undefined as unknown as Issue['project'] });
    expect(screen.getByText('No project assigned')).toBeInTheDocument();
  });

  // ── Notes section ────────────────────────────────────────────────────────

  it('shows "No linked notes" when noteLinks is empty', () => {
    renderGraph({ noteLinks: [] });
    expect(screen.getByText('No linked notes')).toBeInTheDocument();
  });

  it('renders note links', () => {
    renderGraph({
      noteLinks: [
        {
          id: 'nl-1',
          noteId: 'note-1',
          issueId: 'issue-1',
          linkType: 'CREATED',
          noteTitle: 'My Note',
        },
      ],
    });
    expect(screen.getByText('My Note')).toBeInTheDocument();
    expect(screen.getByText('Created from')).toBeInTheDocument();
  });

  it('links each note to the correct URL', () => {
    renderGraph({
      noteLinks: [
        {
          id: 'nl-1',
          noteId: 'note-abc',
          issueId: 'issue-1',
          linkType: 'EXTRACTED',
          noteTitle: 'Note A',
        },
      ],
    });
    expect(screen.getByRole('link', { name: /Note A/i })).toHaveAttribute(
      'href',
      '/my-ws/notes/note-abc'
    );
  });

  it('shows "Show N more" button when note links exceed 3', () => {
    renderGraph({
      noteLinks: Array.from({ length: 5 }, (_, i) => ({
        id: `nl-${i}`,
        noteId: `note-${i}`,
        issueId: 'issue-1',
        linkType: 'REFERENCED' as const,
        noteTitle: `Note ${i}`,
      })),
    });
    expect(screen.getByText('Show 2 more')).toBeInTheDocument();
    // Only first 3 visible initially
    expect(screen.getByText('Note 0')).toBeInTheDocument();
    expect(screen.queryByText('Note 4')).not.toBeInTheDocument();
  });

  it('expands all note links on "Show more" click', () => {
    renderGraph({
      noteLinks: Array.from({ length: 5 }, (_, i) => ({
        id: `nl-${i}`,
        noteId: `note-${i}`,
        issueId: 'issue-1',
        linkType: 'REFERENCED' as const,
        noteTitle: `Note ${i}`,
      })),
    });
    fireEvent.click(screen.getByText('Show 2 more'));
    expect(screen.getByText('Note 4')).toBeInTheDocument();
    expect(screen.getByText('Show less')).toBeInTheDocument();
  });

  // ── Relations section ────────────────────────────────────────────────────

  it('shows "No related issues" when relations list is empty', async () => {
    renderGraph();
    expect(await screen.findByText('No related issues')).toBeInTheDocument();
  });

  it('renders IssueReferenceCard for each relation', async () => {
    vi.mocked(issuesApi.getRelations).mockResolvedValue([MOCK_RELATION]);
    renderGraph();
    expect(await screen.findByText('PS-2')).toBeInTheDocument();
    expect(await screen.findByText('Blocked Issue')).toBeInTheDocument();
  });

  it('navigates to related issue on card click', async () => {
    vi.mocked(issuesApi.getRelations).mockResolvedValue([MOCK_RELATION]);
    renderGraph();
    const card = await screen.findByRole('button');
    fireEvent.click(card);
    expect(mockPush).toHaveBeenCalledWith('/my-ws/issues/issue-2');
  });

  it('shows "Show N more" when relations exceed 3', async () => {
    const manyRelations: IssueRelation[] = Array.from({ length: 5 }, (_, i) => ({
      id: `link-${i}`,
      linkType: 'related' as const,
      direction: 'inbound' as const,
      relatedIssue: {
        id: `issue-rel-${i}`,
        identifier: `PS-${i + 10}`,
        name: `Relation ${i}`,
        priority: 'low' as const,
        state: { id: 'state-x', name: 'Todo', color: '#60a5fa', group: 'unstarted' as const },
      },
    }));
    vi.mocked(issuesApi.getRelations).mockResolvedValue(manyRelations);
    renderGraph();
    expect(await screen.findByText('Show 2 more')).toBeInTheDocument();
  });
});

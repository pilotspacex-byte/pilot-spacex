/**
 * ProjectNotesPanel component tests.
 *
 * Covers: loading skeleton, error state, empty state, recent notes list,
 * note link URLs, and "View all" link when total > 5.
 */

import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ProjectNotesPanel } from '../ProjectNotesPanel';
import type { Project } from '@/types';

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

vi.mock('next/link', () => ({
  default: ({ href, children, ...props }: { href: string; children: React.ReactNode; [k: string]: unknown }) => (
    <a href={href} {...props}>{children}</a>
  ),
}));

const mockUseNotes = vi.fn();
vi.mock('@/features/notes/hooks/useNotes', () => ({
  useNotes: (opts: unknown) => mockUseNotes(opts),
}));

// ---------------------------------------------------------------------------
// Test data
// ---------------------------------------------------------------------------

const mockProject: Project = {
  id: 'proj-1',
  name: 'Test Project',
  identifier: 'TP',
  workspaceId: 'ws-1',
  issueCount: 0,
  openIssueCount: 0,
  createdAt: '2026-01-01T00:00:00Z',
  updatedAt: '2026-01-01T00:00:00Z',
};

const recentNote = {
  id: 'note-2',
  title: 'Recent Note',
  isPinned: false,
  projectId: 'proj-1',
  updatedAt: '2026-01-01T00:00:00Z',
  wordCount: 50,
  topics: [],
};

const loadingState = { data: undefined, isLoading: true, isError: false };
const errorState   = { data: undefined, isLoading: false, isError: true };
const emptyState   = {
  data: { items: [], total: 0, hasNext: false, hasPrev: false, pageSize: 5 },
  isLoading: false,
  isError: false,
};

function makeDataState(items: unknown[], total?: number) {
  return {
    data: { items, total: total ?? items.length, hasNext: false, hasPrev: false, pageSize: 5 },
    isLoading: false,
    isError: false,
  };
}

function renderPanel() {
  return render(
    <ProjectNotesPanel
      project={mockProject}
      workspaceSlug="my-workspace"
      workspaceId="ws-1"
    />
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('ProjectNotesPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ── Single hook call contract ────────────────────────────────────────────

  it('calls useNotes once with projectIds array and isPinned: false', () => {
    mockUseNotes.mockReturnValue(emptyState);
    renderPanel();
    expect(mockUseNotes).toHaveBeenCalledTimes(1);
    expect(mockUseNotes).toHaveBeenCalledWith(
      expect.objectContaining({ projectIds: ['proj-1'], isPinned: false })
    );
  });

  // ── Loading state ────────────────────────────────────────────────────────

  it('renders skeleton rows when loading', () => {
    mockUseNotes.mockReturnValue(loadingState);
    renderPanel();
    const skeletons = document.querySelectorAll('.rounded');
    expect(skeletons.length).toBeGreaterThanOrEqual(3);
  });

  // ── Error state ──────────────────────────────────────────────────────────

  it('renders error message when query fails', () => {
    mockUseNotes.mockReturnValue(errorState);
    renderPanel();
    expect(screen.getByText('Failed to load notes')).toBeTruthy();
  });

  // ── Empty state ──────────────────────────────────────────────────────────

  it('renders empty state when no notes exist', () => {
    mockUseNotes.mockReturnValue(emptyState);
    renderPanel();
    expect(screen.getByText('No notes yet')).toBeTruthy();
  });

  // ── Recent notes list ────────────────────────────────────────────────────

  it('renders recent note titles', () => {
    mockUseNotes.mockReturnValue(makeDataState([recentNote]));
    renderPanel();
    expect(screen.getByText('Recent Note')).toBeTruthy();
    expect(screen.queryByText('No notes yet')).toBeNull();
  });

  it('renders one list item per note', () => {
    const notes = [
      { ...recentNote, id: 'note-a', title: 'Alpha' },
      { ...recentNote, id: 'note-b', title: 'Beta' },
    ];
    mockUseNotes.mockReturnValue(makeDataState(notes));
    renderPanel();
    expect(screen.getAllByTestId('project-note-item')).toHaveLength(2);
  });

  // ── Note link URLs ───────────────────────────────────────────────────────

  it('note links point to the correct URL', () => {
    mockUseNotes.mockReturnValue(makeDataState([recentNote]));
    renderPanel();
    const link = screen.getByText('Recent Note').closest('a');
    expect(link?.getAttribute('href')).toBe('/my-workspace/notes/note-2');
  });

  // ── "View all" behaviour ─────────────────────────────────────────────────

  it('shows "View all" link when total > 5', () => {
    mockUseNotes.mockReturnValue(makeDataState([recentNote], 7));
    renderPanel();
    expect(screen.getByTestId('project-notes-view-all-recent')).toBeTruthy();
  });

  it('does not show "View all" link when total <= 5', () => {
    mockUseNotes.mockReturnValue(makeDataState([recentNote], 3));
    renderPanel();
    expect(screen.queryByTestId('project-notes-view-all-recent')).toBeNull();
  });

  it('does not show "View all" link when total is exactly 5', () => {
    mockUseNotes.mockReturnValue(makeDataState([recentNote], 5));
    renderPanel();
    expect(screen.queryByTestId('project-notes-view-all-recent')).toBeNull();
  });
});

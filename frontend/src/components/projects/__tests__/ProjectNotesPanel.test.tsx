/**
 * ProjectNotesPanel component tests.
 *
 * Covers: loading skeleton, error state, pinned notes list, recent notes list,
 * empty state, guest permission (no "New Note" button), "View all" when total > 5,
 * and create mutation called with correct projectId.
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ProjectNotesPanel } from '../ProjectNotesPanel';
import type { Project } from '@/types';

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

const mockPush = vi.fn();

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush }),
}));

vi.mock('next/link', () => ({
  default: ({ href, children, ...props }: { href: string; children: React.ReactNode; [k: string]: unknown }) => (
    <a href={href} {...props}>{children}</a>
  ),
}));

vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

const mockUseNotes = vi.fn();
vi.mock('@/features/notes/hooks/useNotes', () => ({
  useNotes: (opts: unknown) => mockUseNotes(opts),
}));

const mockMutate = vi.fn();
const mockUseCreateNote = vi.fn();
vi.mock('@/features/notes/hooks/useCreateNote', () => ({
  useCreateNote: (opts: unknown) => mockUseCreateNote(opts),
}));

const mockUseWorkspaceStore = vi.fn();
vi.mock('@/stores/RootStore', () => ({
  useWorkspaceStore: () => mockUseWorkspaceStore(),
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

const pinnedNote = { id: 'note-1', title: 'Pinned Note', isPinned: true, projectId: 'proj-1', updatedAt: '2026-01-01T00:00:00Z', wordCount: 100, topics: [] };
const recentNote = { id: 'note-2', title: 'Recent Note', isPinned: false, projectId: 'proj-1', updatedAt: '2026-01-01T00:00:00Z', wordCount: 50, topics: [] };

const loadingState = { data: undefined, isLoading: true, isError: false };
const emptyState = { data: { items: [], total: 0, hasNext: false, hasPrev: false, pageSize: 5 }, isLoading: false, isError: false };
const errorState = { data: undefined, isLoading: false, isError: true };

function makeDataState(items: unknown[], total?: number) {
  return {
    data: { items, total: total ?? items.length, hasNext: false, hasPrev: false, pageSize: 5 },
    isLoading: false,
    isError: false,
  };
}

const defaultCreateNote = { mutate: mockMutate, isPending: false };

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
    mockUseWorkspaceStore.mockReturnValue({ currentUserRole: 'member' });
    mockUseCreateNote.mockReturnValue(defaultCreateNote);
  });

  it('renders skeleton rows when loading', () => {
    mockUseNotes.mockReturnValue(loadingState);
    renderPanel();
    const skeletons = document.querySelectorAll('.rounded');
    expect(skeletons.length).toBeGreaterThanOrEqual(3);
  });

  it('renders error message when query fails', () => {
    mockUseNotes.mockReturnValue(errorState);
    renderPanel();
    expect(screen.getByText('Failed to load notes')).toBeTruthy();
  });

  it('renders empty state when no notes exist', () => {
    mockUseNotes.mockReturnValue(emptyState);
    renderPanel();
    expect(screen.getByText('No notes yet')).toBeTruthy();
  });

  it('renders pinned notes list with correct titles', () => {
    mockUseNotes
      .mockReturnValueOnce(makeDataState([pinnedNote])) // pinned call
      .mockReturnValueOnce(emptyState);                  // recent call
    renderPanel();
    expect(screen.getByText('Pinned Note')).toBeTruthy();
    expect(screen.queryByText('No notes yet')).toBeNull();
  });

  it('renders recent notes list', () => {
    mockUseNotes
      .mockReturnValueOnce(emptyState)                     // pinned call
      .mockReturnValueOnce(makeDataState([recentNote]));   // recent call
    renderPanel();
    expect(screen.getByText('Recent Note')).toBeTruthy();
  });

  it('note links point to the correct URL', () => {
    mockUseNotes
      .mockReturnValueOnce(makeDataState([pinnedNote]))
      .mockReturnValueOnce(emptyState);
    renderPanel();
    const link = screen.getByText('Pinned Note').closest('a');
    expect(link?.getAttribute('href')).toBe('/my-workspace/notes/note-1');
  });

  it('hides "New Note" button for guest role', () => {
    mockUseWorkspaceStore.mockReturnValue({ currentUserRole: 'guest' });
    mockUseNotes.mockReturnValue(emptyState);
    renderPanel();
    expect(screen.queryByTestId('project-new-note-button')).toBeNull();
  });

  it('shows "New Note" button for non-guest role', () => {
    mockUseNotes.mockReturnValue(emptyState);
    renderPanel();
    expect(screen.getByTestId('project-new-note-button')).toBeTruthy();
  });

  it('calls create mutation with correct projectId on "New Note" click', async () => {
    mockUseNotes.mockReturnValue(emptyState);
    renderPanel();
    fireEvent.click(screen.getByTestId('project-new-note-button'));
    await waitFor(() => {
      expect(mockMutate).toHaveBeenCalledWith({ title: 'Untitled', projectId: 'proj-1' });
    });
  });

  it('shows "View all" link for pinned section when total > 5', () => {
    mockUseNotes
      .mockReturnValueOnce(makeDataState([pinnedNote], 8)) // total 8 > 5
      .mockReturnValueOnce(emptyState);
    renderPanel();
    expect(screen.getByTestId('project-notes-view-all-pinned')).toBeTruthy();
  });

  it('shows "View all" link for recent section when total > 5', () => {
    mockUseNotes
      .mockReturnValueOnce(emptyState)
      .mockReturnValueOnce(makeDataState([recentNote], 7)); // total 7 > 5
    renderPanel();
    expect(screen.getByTestId('project-notes-view-all-recent')).toBeTruthy();
  });

  it('does not show "View all" link when total <= 5', () => {
    mockUseNotes
      .mockReturnValueOnce(makeDataState([pinnedNote], 3))
      .mockReturnValueOnce(makeDataState([recentNote], 2));
    renderPanel();
    expect(screen.queryByTestId('project-notes-view-all-pinned')).toBeNull();
    expect(screen.queryByTestId('project-notes-view-all-recent')).toBeNull();
  });
});

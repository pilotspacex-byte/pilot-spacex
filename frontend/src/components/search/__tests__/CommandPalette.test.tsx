/**
 * CommandPalette Tests — T-019
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { CommandPalette } from '../CommandPalette';

// Mock next/navigation
const mockPush = vi.fn();
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush }),
  useParams: () => ({ workspaceSlug: 'my-workspace' }),
}));

// Mock stores
vi.mock('@/stores', () => ({
  useUIStore: () => ({
    commandPaletteOpen: true,
    closeCommandPalette: vi.fn(),
    toggleCommandPalette: vi.fn(),
  }),
  useWorkspaceStore: () => ({
    currentWorkspace: { id: 'ws-uuid-1', slug: 'my-workspace' },
    currentWorkspaceId: 'ws-uuid-1',
    getWorkspaceBySlug: vi.fn(() => ({ id: 'ws-uuid-1' })),
    workspaceList: [{ id: 'ws-uuid-1' }],
  }),
}));

// Mock notes API
vi.mock('@/services/api/notes', () => ({
  notesApi: {
    list: vi.fn().mockResolvedValue({
      items: [
        {
          id: 'note-1',
          title: 'Sprint planning notes',
          workspaceId: 'ws-uuid-1',
          linkedIssues: [],
          isPinned: false,
          wordCount: 0,
          createdAt: '',
          updatedAt: '',
        },
        {
          id: 'note-2',
          title: 'API design document',
          workspaceId: 'ws-uuid-1',
          linkedIssues: [],
          isPinned: false,
          wordCount: 0,
          createdAt: '',
          updatedAt: '',
        },
      ],
      total: 2,
      page: 1,
      pageSize: 5,
    }),
  },
}));

// Mock issues API
vi.mock('@/services/api/issues', () => ({
  issuesApi: {
    list: vi.fn().mockResolvedValue({
      items: [
        {
          id: 'issue-1',
          identifier: 'PS-42',
          name: 'Fix login bug',
          state: { id: 's1', name: 'In Progress', color: '#f59e0b', group: 'started' },
          priority: 'high',
          workspaceId: 'ws-uuid-1',
          projectId: 'proj-1',
          sequenceId: 42,
          sortOrder: 0,
          reporterId: 'u1',
          labels: [],
          subIssueCount: 0,
          hasAiEnhancements: false,
          createdAt: '',
          updatedAt: '',
        },
      ],
      total: 1,
      page: 1,
      pageSize: 5,
    }),
  },
}));

describe('CommandPalette', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the dialog when open', () => {
    render(<CommandPalette />);
    // The command dialog is mounted
    expect(screen.getByRole('dialog')).toBeDefined();
  });

  it('shows placeholder when query is empty', () => {
    render(<CommandPalette />);
    expect(screen.getByText('Start typing to search notes and issues')).toBeDefined();
  });

  it('shows note and issue results when query matches', async () => {
    render(<CommandPalette />);
    const input = screen.getByPlaceholderText('Search notes and issues...');

    await userEvent.type(input, 'sprint');

    await waitFor(() => {
      expect(screen.getByText('Sprint planning notes')).toBeDefined();
    });
  });

  it('shows issues group heading when issues match', async () => {
    render(<CommandPalette />);
    const input = screen.getByPlaceholderText('Search notes and issues...');

    await userEvent.type(input, 'fix');

    await waitFor(() => {
      expect(screen.getByText('Fix login bug')).toBeDefined();
    });
  });

  it('navigates to note URL on selection', async () => {
    render(<CommandPalette />);
    const input = screen.getByPlaceholderText('Search notes and issues...');

    await userEvent.type(input, 'sprint');

    await waitFor(() => {
      expect(screen.getByText('Sprint planning notes')).toBeDefined();
    });

    fireEvent.click(screen.getByText('Sprint planning notes'));

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith('/my-workspace/notes/note-1');
    });
  });

  it('navigates to issue URL on selection', async () => {
    render(<CommandPalette />);
    const input = screen.getByPlaceholderText('Search notes and issues...');

    await userEvent.type(input, 'fix login');

    await waitFor(() => {
      expect(screen.getByText('Fix login bug')).toBeDefined();
    });

    fireEvent.click(screen.getByText('Fix login bug'));

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith('/my-workspace/issues/issue-1');
    });
  });
});

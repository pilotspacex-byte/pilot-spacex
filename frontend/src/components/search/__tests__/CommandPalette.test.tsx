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

  // ─── Mode prefix tests ───────────────────────────────────────────────────

  it('shows hint bar with > Commands # Symbols : Go to Line', () => {
    render(<CommandPalette />);
    // The hint bar should always be visible
    expect(screen.getByText('Commands')).toBeDefined();
    expect(screen.getByText('Symbols')).toBeDefined();
    expect(screen.getByText('Go to Line')).toBeDefined();
  });

  it('switches to commands mode when typing > prefix', async () => {
    render(<CommandPalette />);
    const input = screen.getByPlaceholderText('Search notes and issues...');

    // Type > to enter commands mode
    await userEvent.type(input, '>');

    // Should show commands mode items
    await waitFor(() => {
      expect(screen.getByText('Toggle Source Control Panel')).toBeDefined();
    });
  });

  it('filters commands by effectiveQuery after > prefix', async () => {
    render(<CommandPalette />);
    const input = screen.getByPlaceholderText(/search/i);

    await userEvent.type(input, '>source');

    await waitFor(() => {
      expect(screen.getByText('Toggle Source Control Panel')).toBeDefined();
    });

    // "Toggle File Tree" should not appear since query is "source"
    expect(screen.queryByText('Toggle File Tree')).toBeNull();
  });

  it('switches to symbols mode when typing # prefix', async () => {
    render(<CommandPalette />);
    const input = screen.getByPlaceholderText('Search notes and issues...');

    await userEvent.type(input, '#');

    // Should show symbol search placeholder
    await waitFor(() => {
      expect(screen.getByText('Symbol search available in a future update')).toBeDefined();
    });
  });

  it('switches to goto-line mode when typing : prefix', async () => {
    render(<CommandPalette />);
    const input = screen.getByPlaceholderText('Search notes and issues...');

    await userEvent.type(input, ':');

    // Should show go-to-line prompt
    await waitFor(() => {
      expect(screen.getByText('Type a line number to navigate')).toBeDefined();
    });
  });

  it('shows go-to-line prompt text after : prefix mode is active', async () => {
    render(<CommandPalette />);
    // Verify the goto-line mode renders the "Type a line number to navigate" prompt
    // by checking that the : prefix mode switch shows its content
    const input = screen.getByRole('combobox');

    // Type ':' to enter goto-line mode (the existing test confirms mode switch)
    await userEvent.type(input, ':');

    await waitFor(() => {
      expect(screen.getByText('Type a line number to navigate')).toBeDefined();
    });
  });

  it('keeps search mode when no prefix is typed', async () => {
    render(<CommandPalette />);
    const input = screen.getByPlaceholderText('Search notes and issues...');

    // Type plain text — no prefix
    await userEvent.type(input, 'sprint');

    // Should show notes/issues results (search mode)
    await waitFor(() => {
      expect(screen.getByText('Sprint planning notes')).toBeDefined();
    });

    // Commands mode items should NOT appear
    expect(screen.queryByText('Toggle Source Control Panel')).toBeNull();
    // Symbols placeholder should NOT appear
    expect(screen.queryByText('Symbol search available in a future update')).toBeNull();
  });
});

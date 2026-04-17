/**
 * CommandPalette Tests — v3 (issues/people/pages/commands)
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

// Mock stores — v3 adds members data (currentMembers + fetchMembers)
const mockFetchMembers = vi.fn().mockResolvedValue(undefined);
const mockMembers = [
  {
    id: 'u-tin',
    userId: 'u-tin',
    workspaceId: 'ws-uuid-1',
    role: 'owner',
    joinedAt: '',
    weeklyAvailableHours: 40,
    user: { id: 'u-tin', name: 'Tin Dang', email: 'tin@example.com' },
  },
  {
    id: 'u-alex',
    userId: 'u-alex',
    workspaceId: 'ws-uuid-1',
    role: 'member',
    joinedAt: '',
    weeklyAvailableHours: 40,
    user: { id: 'u-alex', name: 'Alex Rivera', email: 'alex@example.com' },
  },
];

vi.mock('@/stores', () => ({
  useUIStore: () => ({
    commandPaletteOpen: true,
    closeCommandPalette: vi.fn(),
    openCommandPalette: vi.fn(),
    toggleCommandPalette: vi.fn(),
  }),
  useWorkspaceStore: () => ({
    currentWorkspace: { id: 'ws-uuid-1', slug: 'my-workspace' },
    currentWorkspaceId: 'ws-uuid-1',
    getWorkspaceBySlug: vi.fn(() => ({ id: 'ws-uuid-1' })),
    workspaceList: [{ id: 'ws-uuid-1' }],
    currentMembers: mockMembers,
    fetchMembers: mockFetchMembers,
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
    expect(screen.getByRole('dialog')).toBeDefined();
  });

  it('shows placeholder when query is empty', () => {
    render(<CommandPalette />);
    expect(
      screen.getByText((t) => t.startsWith('Start typing'))
    ).toBeDefined();
  });

  it('shows note and issue results when query matches (unified search)', async () => {
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

  // ─── v3 prefix legend ────────────────────────────────────────────────────

  it('shows prefix legend chips: issues, people, pages, commands', () => {
    render(<CommandPalette />);
    expect(screen.getByLabelText('Switch to issues mode')).toBeDefined();
    expect(screen.getByLabelText('Switch to people mode')).toBeDefined();
    expect(screen.getByLabelText('Switch to pages mode')).toBeDefined();
    expect(screen.getByLabelText('Switch to commands mode')).toBeDefined();
  });

  it('clicking a prefix chip prepends that prefix to the input', async () => {
    render(<CommandPalette />);
    const input = screen.getByRole('combobox') as HTMLInputElement;

    await userEvent.type(input, 'tin');
    fireEvent.click(screen.getByLabelText('Switch to people mode'));

    await waitFor(() => {
      expect(input.value).toBe('@tin');
    });
  });

  // ─── Mode prefix tests ───────────────────────────────────────────────────

  it('switches to commands mode when typing > prefix', async () => {
    render(<CommandPalette />);
    const input = screen.getByPlaceholderText('Search notes and issues...');

    await userEvent.type(input, '>');

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

    expect(screen.queryByText('Toggle File Tree')).toBeNull();
  });

  it('switches to issues mode when typing # prefix', async () => {
    render(<CommandPalette />);
    const input = screen.getByPlaceholderText('Search notes and issues...');

    await userEvent.type(input, '#');

    await waitFor(() => {
      expect(
        (screen.getByPlaceholderText('Search issues...') as HTMLInputElement).value
      ).toBe('#');
    });

    await waitFor(() => {
      expect(screen.getByText('Fix login bug')).toBeDefined();
    });
  });

  it('switches to pages mode when typing / prefix', async () => {
    render(<CommandPalette />);
    const input = screen.getByPlaceholderText('Search notes and issues...');

    await userEvent.type(input, '/');

    await waitFor(() => {
      expect(screen.getByPlaceholderText('Search pages...')).toBeDefined();
    });

    await waitFor(() => {
      expect(screen.getByText('Sprint planning notes')).toBeDefined();
    });
  });

  it('switches to people mode when typing @ prefix and filters by name', async () => {
    render(<CommandPalette />);
    const input = screen.getByPlaceholderText('Search notes and issues...');

    await userEvent.type(input, '@tin');

    await waitFor(() => {
      expect(screen.getByText('Tin Dang')).toBeDefined();
    });
    expect(screen.queryByText('Alex Rivera')).toBeNull();
  });

  it('navigates to member URL on selection in people mode', async () => {
    render(<CommandPalette />);
    const input = screen.getByPlaceholderText('Search notes and issues...');

    await userEvent.type(input, '@tin');

    await waitFor(() => {
      expect(screen.getByText('Tin Dang')).toBeDefined();
    });

    fireEvent.click(screen.getByText('Tin Dang'));

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith('/my-workspace/members/u-tin');
    });
  });

  it('switches to goto-line mode when typing : prefix', async () => {
    render(<CommandPalette />);
    const input = screen.getByPlaceholderText('Search notes and issues...');

    await userEvent.type(input, ':');

    await waitFor(() => {
      expect(screen.getByText('Type a line number to navigate')).toBeDefined();
    });
  });

  it('keeps search mode when no prefix is typed', async () => {
    render(<CommandPalette />);
    const input = screen.getByPlaceholderText('Search notes and issues...');

    await userEvent.type(input, 'sprint');

    await waitFor(() => {
      expect(screen.getByText('Sprint planning notes')).toBeDefined();
    });

    expect(screen.queryByText('Toggle Source Control Panel')).toBeNull();
  });
});

/**
 * CommandPalette v3 integration tests (Plan 90-03 Task 3).
 *
 * Verifies scope tabs, prefix consumption + mode chip, ghost-completion
 * scaffolding, AI fallback row, ?palette=1&q= URL hydration, footer
 * legend copy, and Esc / ⌘K keybindings.
 *
 * Mocking strategy:
 *   - Real `UIStore` instance per test → component (observer) re-renders
 *     reactively when paletteScope / palettePrefixMode change.
 *   - `next/navigation` is a hand-rolled module mock; per-test we swap
 *     `currentSearchParams` to drive `?palette=1&q=…` hydration.
 *   - notesApi.list / issuesApi.list mocks default to empty `items: []`;
 *     individual tests override `mockResolvedValueOnce` for fixtures.
 *   - We control debounce timing with `vi.useFakeTimers()` + `act()`.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { act, render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { UIStore } from '@/stores/UIStore';
import { CommandPalette } from '../CommandPalette';

// ─── Mocks ─────────────────────────────────────────────────────────────────

const pushMock = vi.fn();
const replaceMock = vi.fn();
let currentSearchParams = new URLSearchParams();

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: pushMock, replace: replaceMock }),
  useParams: () => ({ workspaceSlug: 'alpha' }),
  usePathname: () => '/alpha',
  useSearchParams: () => currentSearchParams,
}));

// Real UIStore instance per test (observer reactivity).
let testUIStore: UIStore;

vi.mock('@/stores', () => ({
  useUIStore: () => testUIStore,
  useWorkspaceStore: () => ({
    currentWorkspace: { id: 'ws1', slug: 'alpha' },
    currentWorkspaceId: 'ws1',
    getWorkspaceBySlug: (slug: string) => (slug === 'alpha' ? { id: 'ws1' } : undefined),
  }),
}));

const notesListMock = vi.fn();
const issuesListMock = vi.fn();

vi.mock('@/services/api/notes', () => ({
  notesApi: { list: (...args: unknown[]) => notesListMock(...args) },
}));

vi.mock('@/services/api/issues', () => ({
  issuesApi: { list: (...args: unknown[]) => issuesListMock(...args) },
}));

// ─── Helpers ───────────────────────────────────────────────────────────────

function makeStoreOpen(): UIStore {
  const store = new UIStore();
  store.openCommandPalette();
  return store;
}

function setSearchParams(qs: string): void {
  currentSearchParams = new URLSearchParams(qs);
}

async function flushDebounce(): Promise<void> {
  // Push past the 250ms debounce + microtasks for the awaited Promise.all.
  await act(async () => {
    await vi.advanceTimersByTimeAsync(300);
  });
}

// ─── Setup ─────────────────────────────────────────────────────────────────

beforeEach(() => {
  vi.useFakeTimers({ shouldAdvanceTime: true });
  pushMock.mockReset();
  replaceMock.mockReset();
  notesListMock.mockReset();
  issuesListMock.mockReset();
  notesListMock.mockResolvedValue({ items: [], total: 0, page: 1, pageSize: 5 });
  issuesListMock.mockResolvedValue({ items: [], total: 0, page: 1, pageSize: 5 });
  setSearchParams('');
  testUIStore = makeStoreOpen();
});

afterEach(() => {
  vi.useRealTimers();
});

// ─── Tests ─────────────────────────────────────────────────────────────────

describe('CommandPalette v3', () => {
  it('opens when uiStore.commandPaletteOpen is true', () => {
    render(<CommandPalette />);
    expect(screen.getByRole('dialog')).toBeDefined();
  });

  it('⌘K-style keybinding is owned by useCommandPaletteShortcut (palette opens via store)', () => {
    // The component itself doesn't bind ⌘K — that's the parent shortcut hook.
    // Verify the store-driven open contract: closing then reopening via the
    // store flips the dialog visibility in a single render.
    const { rerender } = render(<CommandPalette />);
    expect(screen.getByRole('dialog')).toBeDefined();

    act(() => testUIStore.closeCommandPalette());
    rerender(<CommandPalette />);
    expect(screen.queryByRole('dialog')).toBeNull();

    act(() => testUIStore.openCommandPalette());
    rerender(<CommandPalette />);
    expect(screen.getByRole('dialog')).toBeDefined();
  });

  it('clicking the Tasks scope tab updates uiStore.paletteScope and aria-selected', () => {
    render(<CommandPalette />);
    const tasksTab = screen.getByRole('tab', { name: 'Tasks' });
    fireEvent.click(tasksTab);
    expect(testUIStore.paletteScope).toBe('tasks');
    expect(tasksTab.getAttribute('aria-selected')).toBe('true');
  });

  it("typing '#stale' activates tasks mode (chip + scope)", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<CommandPalette />);
    const input = screen.getByRole('combobox');
    await user.type(input, '#stale');
    expect(testUIStore.palettePrefixMode).toBe('tasks');
    expect(testUIStore.paletteScope).toBe('tasks');
    const chip = screen.getByTestId('palette-mode-chip');
    expect(chip.textContent).toBe('#');
  });

  it('backspace on empty clears the prefix mode', async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<CommandPalette />);
    const input = screen.getByRole('combobox') as HTMLInputElement;
    await user.type(input, '#');
    expect(testUIStore.palettePrefixMode).toBe('tasks');
    // Backspace deletes the '#'; the keydown handler fires on the now-empty
    // input value via the next render — assert eventual clearing.
    await user.type(input, '{Backspace}');
    await waitFor(() => {
      expect(testUIStore.palettePrefixMode).toBe(null);
    });
  });

  it('placeholder swaps per prefix mode', async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<CommandPalette />);
    const input = screen.getByRole('combobox') as HTMLInputElement;
    await user.type(input, '@');
    expect(input.placeholder).toBe('Find people…');
    await user.clear(input);
    await user.type(input, '/');
    expect(input.placeholder).toBe('Go to page…');
  });

  it('zero matches renders the AI fallback row with sparkles + exact copy', async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<CommandPalette />);
    const input = screen.getByRole('combobox');
    await user.type(input, 'nonexistent');
    await flushDebounce();

    await waitFor(() => {
      // The fallback row text comes from /Ask AI: "{query}"/.
      expect(screen.getByText(/Ask AI:/)).toBeDefined();
      expect(screen.getByText('nonexistent')).toBeDefined();
    });
    // Sparkles icon (lucide renders as svg with lucide-sparkles class).
    const dialog = screen.getByRole('dialog');
    expect(dialog.querySelector('.lucide-sparkles')).not.toBeNull();
  });

  it('clicking AI fallback pushes /chat?prompt=<encoded> with raw query', async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<CommandPalette />);
    const input = screen.getByRole('combobox');
    await user.type(input, 'nonexistent');
    await flushDebounce();

    const fallback = await screen.findByText(/Ask AI:/);
    fireEvent.click(fallback);
    expect(pushMock).toHaveBeenCalledWith('/chat?prompt=nonexistent');
  });

  it('AI fallback strips the prefix before encoding (#stale → prompt=stale)', async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<CommandPalette />);
    const input = screen.getByRole('combobox');
    await user.type(input, '#stale');
    await flushDebounce();

    const fallback = await screen.findByText(/Ask AI:/);
    fireEvent.click(fallback);
    expect(pushMock).toHaveBeenCalledWith('/chat?prompt=stale');
  });

  it('?palette=1 on mount keeps palette open', () => {
    setSearchParams('palette=1');
    // Mount with a fresh store NOT pre-opened — let the qs sync hook do it.
    testUIStore = new UIStore();
    render(<CommandPalette />);
    // The hook's effect runs synchronously after mount; React Testing Library
    // flushes effects by default. The store should now be open.
    expect(testUIStore.commandPaletteOpen).toBe(true);
  });

  it('?palette=1&q=%23stale pre-populates input and activates tasks mode', async () => {
    setSearchParams('palette=1&q=%23stale');
    render(<CommandPalette />);
    const input = screen.getByRole('combobox') as HTMLInputElement;
    expect(input.value).toBe('#stale');
    await waitFor(() => {
      expect(testUIStore.palettePrefixMode).toBe('tasks');
    });
  });

  it('footer legend renders all four key hints', () => {
    render(<CommandPalette />);
    expect(screen.getByText('↑↓ navigate')).toBeDefined();
    expect(screen.getByText('↵ open')).toBeDefined();
    expect(screen.getByText('⌘↵ open in split')).toBeDefined();
    expect(screen.getByText('esc close')).toBeDefined();
  });

  it('Esc closes the palette via Radix Dialog onOpenChange', () => {
    render(<CommandPalette />);
    fireEvent.keyDown(document, { key: 'Escape' });
    // Radix dispatches onOpenChange(false) on Escape; assert store sync.
    expect(testUIStore.commandPaletteOpen).toBe(false);
  });

  it("scope='all' renders Topics + Tasks groups when both have results", async () => {
    notesListMock.mockResolvedValueOnce({
      items: [
        {
          id: 'n1',
          title: 'Stale Topic',
          workspaceId: 'ws1',
          linkedIssues: [],
          isPinned: false,
          wordCount: 0,
          createdAt: '',
          updatedAt: '',
        },
      ],
      total: 1,
      page: 1,
      pageSize: 5,
    });
    issuesListMock.mockResolvedValueOnce({
      items: [
        {
          id: 'i1',
          identifier: 'ISS-1',
          name: 'Stale Task',
          state: { id: 's1', name: 'Open', color: '#000', group: 'unstarted' },
          priority: 'medium',
          workspaceId: 'ws1',
          projectId: 'p1',
          sequenceId: 1,
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
    });

    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<CommandPalette />);
    const input = screen.getByRole('combobox');
    await user.type(input, 'stale');
    await flushDebounce();

    await waitFor(() => {
      expect(screen.getByText('Stale Topic')).toBeDefined();
      expect(screen.getByText('Stale Task')).toBeDefined();
    });
    // Both group headings are present.
    expect(screen.getByText('TOPICS')).toBeDefined();
    expect(screen.getByText('TASKS')).toBeDefined();
  });

  it("scope='tasks' filtering hides the Topics group", async () => {
    notesListMock.mockResolvedValueOnce({
      items: [
        {
          id: 'n1',
          title: 'Stale Topic',
          workspaceId: 'ws1',
          linkedIssues: [],
          isPinned: false,
          wordCount: 0,
          createdAt: '',
          updatedAt: '',
        },
      ],
      total: 1,
      page: 1,
      pageSize: 5,
    });
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<CommandPalette />);
    // User actively switches to Tasks scope.
    fireEvent.click(screen.getByRole('tab', { name: 'Tasks' }));
    await user.type(screen.getByRole('combobox'), 'stale');
    await flushDebounce();

    expect(screen.queryByText('TOPICS')).toBeNull();
    expect(screen.queryByText('Stale Topic')).toBeNull();
  });

  it('shows the empty state with prefix hints when no query is typed', () => {
    render(<CommandPalette />);
    expect(screen.getByText('Search everything')).toBeDefined();
    expect(screen.getByText('#tasks')).toBeDefined();
    expect(screen.getByText('@people')).toBeDefined();
    expect(screen.getByText('/pages')).toBeDefined();
  });

  // ─── Phase 91 Plan 05 — Skills scope tab ────────────────────────────────
  it('renders Skills tab between Specs and People (Plan 91-05)', () => {
    render(<CommandPalette />);
    const tabs = screen
      .getAllByRole('tab')
      .map((t) => (t as HTMLElement).textContent?.trim());
    expect(tabs).toEqual(['All', 'Chats', 'Topics', 'Tasks', 'Specs', 'Skills', 'People']);
  });

  it('clicking Skills tab updates uiStore.paletteScope and aria-selected (Plan 91-05)', () => {
    render(<CommandPalette />);
    const skillsTab = screen.getByRole('tab', { name: 'Skills' });
    fireEvent.click(skillsTab);
    expect(testUIStore.paletteScope).toBe('skills');
    expect(skillsTab.getAttribute('aria-selected')).toBe('true');
  });

  it('?palette=1&scope=skills opens palette with Skills tab active (Plan 91-05)', async () => {
    setSearchParams('palette=1&scope=skills');
    testUIStore = new UIStore();
    render(<CommandPalette />);
    await waitFor(() => {
      expect(testUIStore.paletteScope).toBe('skills');
    });
    const skillsTab = screen.getByRole('tab', { name: 'Skills' });
    expect(skillsTab.getAttribute('aria-selected')).toBe('true');
  });
});

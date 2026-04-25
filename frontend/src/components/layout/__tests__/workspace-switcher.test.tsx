/**
 * Unit tests for the v3 WorkspaceSwitcher (Surface 2 — Popover + cmdk).
 *
 * Verifies:
 *  - Pill click opens the popover (UIStore-backed open state)
 *  - Escape closes the popover
 *  - cmdk filter narrows the WORKSPACES list
 *  - Workspace row click calls addRecentWorkspace with the slug STRING
 *    (not the workspace object) and router.push with the resolved path
 *  - JUMP TO rows navigate to Phase 84 routes (/tasks, /topics) and never to
 *    the legacy /issues or /notes paths
 *  - Settings row opens the modal via openSettings, NOT router.push
 *  - + New workspace footer opens CreateWorkspaceDialog
 *  - ⌘2 / ⌘3 kbd hints render on row indices 1 / 2
 *  - The current workspace row renders the Check icon
 *  - ?switcher=1 mount opens the popover automatically
 *
 * @module components/layout/__tests__/workspace-switcher.test
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, within, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { makeAutoObservable } from 'mobx';
import { TooltipProvider } from '@/components/ui/tooltip';

// jsdom doesn't implement Element.scrollIntoView; cmdk calls it on mount.
if (!Element.prototype.scrollIntoView) {
  Element.prototype.scrollIntoView = vi.fn();
}

// ---------------------------------------------------------------------------
// Hoisted mock state (vi.mock factories run before module-level statements)
// ---------------------------------------------------------------------------

const hoisted = vi.hoisted(() => ({
  push: vi.fn(),
  replace: vi.fn(),
  searchParams: new URLSearchParams(),
  addRecentWorkspace: vi.fn(),
  openSettings: vi.fn(),
}));

// ---------------------------------------------------------------------------
// next/navigation
// ---------------------------------------------------------------------------

vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: hoisted.push,
    replace: hoisted.replace,
    prefetch: vi.fn(),
    back: vi.fn(),
    forward: vi.fn(),
  }),
  usePathname: () => '/alpha',
  useSearchParams: () => hoisted.searchParams,
}));

// ---------------------------------------------------------------------------
// useSwitcherQueryStringSync — emulate the mount-time URL hydration only.
// (The real hook is exercised in its own test file.)
// ---------------------------------------------------------------------------

vi.mock('@/hooks/useSwitcherQueryStringSync', () => ({
  useSwitcherQueryStringSync: () => {
    const stores = stubStores;
    if (hoisted.searchParams.get('switcher') === '1') {
      stores?.uiStore.openWorkspaceSwitcher();
    }
  },
}));

// ---------------------------------------------------------------------------
// workspace-selector — slug-string contract
// ---------------------------------------------------------------------------

vi.mock('@/components/workspace-selector', () => ({
  addRecentWorkspace: (slug: string) => hoisted.addRecentWorkspace(slug),
  getRecentWorkspaces: () => [
    { slug: 'alpha', lastVisited: 3 },
    { slug: 'beta', lastVisited: 2 },
    { slug: 'gamma', lastVisited: 1 },
  ],
}));

// ---------------------------------------------------------------------------
// workspace-nav — deterministic recents order matching the WorkspaceStore stub
// ---------------------------------------------------------------------------

vi.mock('@/lib/workspace-nav', () => ({
  getLastWorkspacePath: (slug: string) => `/${slug}`,
  getOrderedRecentWorkspaces: (store: {
    workspaces: Map<string, { id: string; slug: string; name: string }>;
  }) => {
    const slugOrder = ['alpha', 'beta', 'gamma'];
    const ordered: Array<{ id: string; slug: string; name: string }> = [];
    for (const slug of slugOrder) {
      for (const ws of store.workspaces.values()) {
        if (ws.slug === slug) {
          ordered.push(ws);
          break;
        }
      }
    }
    return ordered;
  },
}));

// ---------------------------------------------------------------------------
// settings modal
// ---------------------------------------------------------------------------

vi.mock('@/features/settings/settings-modal-context', () => ({
  useSettingsModal: () => ({
    open: false,
    activeSection: 'general',
    openSettings: hoisted.openSettings,
    closeSettings: vi.fn(),
    setActiveSection: vi.fn(),
  }),
}));

// ---------------------------------------------------------------------------
// workspaces API (used by CreateWorkspaceDialog slug-availability check)
// ---------------------------------------------------------------------------

vi.mock('@/services/api/workspaces', () => ({
  workspacesApi: {
    get: vi.fn(),
    list: vi.fn().mockResolvedValue({ items: [] }),
    create: vi.fn(),
  },
}));

// ---------------------------------------------------------------------------
// MobX-backed test stores — real `observer()` + real reactivity.
// ---------------------------------------------------------------------------

type Workspace = { id: string; slug: string; name: string; memberCount: number };

class TestUIStore {
  workspaceSwitcherOpen = false;

  constructor() {
    makeAutoObservable(this);
  }

  openWorkspaceSwitcher(): void {
    this.workspaceSwitcherOpen = true;
  }

  closeWorkspaceSwitcher(): void {
    this.workspaceSwitcherOpen = false;
  }

  toggleWorkspaceSwitcher(): void {
    this.workspaceSwitcherOpen = !this.workspaceSwitcherOpen;
  }
}

class TestWorkspaceStore {
  workspaces = new Map<string, Workspace>([
    ['id-alpha', { id: 'id-alpha', slug: 'alpha', name: 'Alpha', memberCount: 1 }],
    ['id-beta', { id: 'id-beta', slug: 'beta', name: 'Beta', memberCount: 1 }],
    ['id-gamma', { id: 'id-gamma', slug: 'gamma', name: 'Gamma', memberCount: 1 }],
  ]);
  currentWorkspaceId: string | null = 'id-alpha';
  error: string | null = null;

  constructor() {
    makeAutoObservable(this);
  }

  get workspaceList(): Workspace[] {
    return Array.from(this.workspaces.values()).sort((a, b) => a.name.localeCompare(b.name));
  }

  get currentWorkspace(): Workspace | null {
    return this.currentWorkspaceId
      ? (this.workspaces.get(this.currentWorkspaceId) ?? null)
      : null;
  }

  getWorkspaceBySlug(slug: string): Workspace | undefined {
    return this.workspaceList.find((w) => w.slug === slug);
  }

  selectWorkspace(): void {}
  fetchWorkspaces(): void {}
  async createWorkspace(): Promise<Workspace | null> {
    return null;
  }
}

let stubStores: { uiStore: TestUIStore; workspaceStore: TestWorkspaceStore } | null = null;

vi.mock('@/stores', () => ({
  useUIStore: () => stubStores!.uiStore,
  useWorkspaceStore: () => stubStores!.workspaceStore,
}));

// ---------------------------------------------------------------------------
// Component under test (imported AFTER mocks)
// ---------------------------------------------------------------------------
import { WorkspaceSwitcher } from '../workspace-switcher';

function renderSwitcher() {
  return render(
    <TooltipProvider>
      <WorkspaceSwitcher currentSlug="alpha" />
    </TooltipProvider>
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('WorkspaceSwitcher (Surface 2 — Popover + cmdk)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    hoisted.searchParams = new URLSearchParams();
    stubStores = {
      uiStore: new TestUIStore(),
      workspaceStore: new TestWorkspaceStore(),
    };
  });

  it('renders WorkspacePill with current workspace name', () => {
    renderSwitcher();
    const pill = screen.getByTestId('workspace-pill');
    expect(pill).toBeInTheDocument();
    expect(pill).toHaveTextContent('Alpha');
  });

  it('clicking the pill opens the popover (WORKSPACES heading visible)', async () => {
    const user = userEvent.setup();
    renderSwitcher();

    await user.click(screen.getByTestId('workspace-pill'));

    expect(await screen.findByText('WORKSPACES')).toBeInTheDocument();
    expect(stubStores!.uiStore.workspaceSwitcherOpen).toBe(true);
  });

  it('Escape key closes the popover', async () => {
    const user = userEvent.setup();
    renderSwitcher();

    await user.click(screen.getByTestId('workspace-pill'));
    expect(await screen.findByText('WORKSPACES')).toBeInTheDocument();

    await user.keyboard('{Escape}');

    await vi.waitFor(() => {
      expect(screen.queryByText('WORKSPACES')).not.toBeInTheDocument();
    });
  });

  it('typing "be" filters WORKSPACES to only Beta', async () => {
    const user = userEvent.setup();
    renderSwitcher();

    await user.click(screen.getByTestId('workspace-pill'));
    const input = await screen.findByPlaceholderText('Jump to…');
    await user.type(input, 'be');

    expect(screen.queryByTestId('switcher-ws-beta')).toBeInTheDocument();
    expect(screen.queryByTestId('switcher-ws-alpha')).not.toBeInTheDocument();
    expect(screen.queryByTestId('switcher-ws-gamma')).not.toBeInTheDocument();
  });

  it("clicking beta row calls addRecentWorkspace('beta') (slug STRING, not object), router.push('/beta'), and closes popover", async () => {
    const user = userEvent.setup();
    renderSwitcher();

    await user.click(screen.getByTestId('workspace-pill'));
    const betaRow = await screen.findByTestId('switcher-ws-beta');
    await user.click(betaRow);

    expect(hoisted.addRecentWorkspace).toHaveBeenCalledWith('beta');
    // Hard contract: must be called with the STRING, never the workspace object
    expect(hoisted.addRecentWorkspace).not.toHaveBeenCalledWith(
      expect.objectContaining({ id: expect.any(String) })
    );

    expect(hoisted.push).toHaveBeenCalledWith('/beta');
    expect(stubStores!.uiStore.workspaceSwitcherOpen).toBe(false);
  });

  it('row at index 1 (beta) renders the ⌘2 kbd label', async () => {
    const user = userEvent.setup();
    renderSwitcher();

    await user.click(screen.getByTestId('workspace-pill'));
    const betaRow = await screen.findByTestId('switcher-ws-beta');
    expect(within(betaRow).getByText('⌘2')).toBeInTheDocument();
  });

  it('row at index 2 (gamma) renders the ⌘3 kbd label', async () => {
    const user = userEvent.setup();
    renderSwitcher();

    await user.click(screen.getByTestId('workspace-pill'));
    const gammaRow = await screen.findByTestId('switcher-ws-gamma');
    expect(within(gammaRow).getByText('⌘3')).toBeInTheDocument();
  });

  it('current workspace (alpha) row renders the Check icon', async () => {
    const user = userEvent.setup();
    renderSwitcher();

    await user.click(screen.getByTestId('workspace-pill'));
    expect(await screen.findByTestId('switcher-active-check-alpha')).toBeInTheDocument();
    expect(screen.queryByTestId('switcher-active-check-beta')).not.toBeInTheDocument();
    expect(screen.queryByTestId('switcher-active-check-gamma')).not.toBeInTheDocument();
  });

  it('clicking JUMP TO Projects routes to /alpha/projects', async () => {
    const user = userEvent.setup();
    renderSwitcher();

    await user.click(screen.getByTestId('workspace-pill'));
    await user.click(await screen.findByTestId('switcher-jump-projects'));

    expect(hoisted.push).toHaveBeenCalledWith('/alpha/projects');
  });

  it('clicking JUMP TO Tasks routes to /alpha/tasks (Phase 84 route — NOT /alpha/issues)', async () => {
    const user = userEvent.setup();
    renderSwitcher();

    await user.click(screen.getByTestId('workspace-pill'));
    await user.click(await screen.findByTestId('switcher-jump-tasks'));

    expect(hoisted.push).toHaveBeenCalledWith('/alpha/tasks');
    expect(hoisted.push).not.toHaveBeenCalledWith('/alpha/issues');
  });

  it('clicking JUMP TO Topics routes to /alpha/topics (Phase 84 route — NOT /alpha/notes)', async () => {
    const user = userEvent.setup();
    renderSwitcher();

    await user.click(screen.getByTestId('workspace-pill'));
    await user.click(await screen.findByTestId('switcher-jump-topics'));

    expect(hoisted.push).toHaveBeenCalledWith('/alpha/topics');
    expect(hoisted.push).not.toHaveBeenCalledWith('/alpha/notes');
  });

  it('clicking JUMP TO Settings opens the settings modal (NOT router.push)', async () => {
    const user = userEvent.setup();
    renderSwitcher();

    await user.click(screen.getByTestId('workspace-pill'));
    await user.click(await screen.findByTestId('switcher-jump-settings'));

    expect(hoisted.openSettings).toHaveBeenCalledTimes(1);
    expect(hoisted.push).not.toHaveBeenCalledWith(expect.stringContaining('/settings'));
  });

  it('clicking + New workspace opens CreateWorkspaceDialog', async () => {
    const user = userEvent.setup();
    renderSwitcher();

    await user.click(screen.getByTestId('workspace-pill'));
    await user.click(await screen.findByTestId('switcher-new-workspace'));

    // Two elements share the text 'Create workspace' (dialog title h2 + submit
    // button) — assert via the dialog role + accessible name
    const dialog = await screen.findByRole('dialog');
    expect(within(dialog).getByRole('heading', { name: 'Create workspace' })).toBeInTheDocument();
  });

  it('mount with ?switcher=1 opens the popover automatically', async () => {
    hoisted.searchParams = new URLSearchParams('switcher=1');

    await act(async () => {
      renderSwitcher();
    });

    expect(await screen.findByText('WORKSPACES')).toBeInTheDocument();
    expect(stubStores!.uiStore.workspaceSwitcherOpen).toBe(true);
  });
});

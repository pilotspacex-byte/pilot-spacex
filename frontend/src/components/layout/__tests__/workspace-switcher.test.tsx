/**
 * Unit tests for the WorkspaceSwitcher (Surface 2 — Popover + cmdk).
 *
 * Verifies:
 *  - Pill click opens the popover
 *  - Escape closes the popover
 *  - cmdk filter narrows the workspace lists
 *  - Workspace row click calls addRecentWorkspace with the slug STRING
 *    (not the workspace object) and router.push with the resolved path
 *  - CURRENT band renders workspace name, role chip, member count
 *  - CURRENT band action rows open the settings modal at the right tab
 *  - Leave workspace row is hidden for owners and visible for non-owners
 *  - SWITCH TO renders RECENT and ALL subgroup headers
 *  - Per-row role badge derived from authStore workspaceMemberships
 *  - + New workspace footer opens CreateWorkspaceDialog
 *  - ⌘2 / ⌘3 kbd hints render on RECENT row indices 0 / 1 (current excluded)
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
// Hoisted mock state
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
// useSwitcherQueryStringSync — emulate mount-time URL hydration only
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
// workspace-nav — deterministic recents order
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
// workspaces API (used by CreateWorkspaceDialog + Leave flow)
// ---------------------------------------------------------------------------

vi.mock('@/services/api/workspaces', () => ({
  workspacesApi: {
    get: vi.fn(),
    list: vi.fn().mockResolvedValue({ items: [] }),
    create: vi.fn(),
    removeMember: vi.fn().mockResolvedValue(undefined),
  },
}));

// ---------------------------------------------------------------------------
// MobX-backed test stores
// ---------------------------------------------------------------------------

type Workspace = { id: string; slug: string; name: string; memberCount: number };
type Member = { id: string; userId: string; role: string };

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
    ['id-alpha', { id: 'id-alpha', slug: 'alpha', name: 'Alpha', memberCount: 12 }],
    ['id-beta', { id: 'id-beta', slug: 'beta', name: 'Beta', memberCount: 4 }],
    ['id-gamma', { id: 'id-gamma', slug: 'gamma', name: 'Gamma', memberCount: 7 }],
  ]);
  // Per-workspace member arrays. Used by Leave flow to look up the current
  // user's memberId for removeMember(workspaceId, memberId).
  members = new Map<string, Member[]>([
    ['id-alpha', [{ id: 'mem-alpha-self', userId: 'user-1', role: 'MEMBER' }]],
    ['id-beta', [{ id: 'mem-beta-self', userId: 'user-1', role: 'ADMIN' }]],
    ['id-gamma', [{ id: 'mem-gamma-self', userId: 'user-1', role: 'GUEST' }]],
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

class TestAuthStore {
  user: {
    id: string;
    email: string;
    workspaceMemberships?: Array<{ workspaceId: string; role: string }>;
  } | null = {
    id: 'user-1',
    email: 'user@example.com',
    workspaceMemberships: [
      { workspaceId: 'id-alpha', role: 'MEMBER' },
      { workspaceId: 'id-beta', role: 'ADMIN' },
      { workspaceId: 'id-gamma', role: 'GUEST' },
    ],
  };

  constructor() {
    makeAutoObservable(this);
  }

  setRole(workspaceId: string, role: string): void {
    if (!this.user?.workspaceMemberships) return;
    const m = this.user.workspaceMemberships.find((x) => x.workspaceId === workspaceId);
    if (m) m.role = role;
  }
}

let stubStores: {
  uiStore: TestUIStore;
  workspaceStore: TestWorkspaceStore;
  authStore: TestAuthStore;
} | null = null;

vi.mock('@/stores', () => ({
  useUIStore: () => stubStores!.uiStore,
  useWorkspaceStore: () => stubStores!.workspaceStore,
  useAuthStore: () => stubStores!.authStore,
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

describe('WorkspaceSwitcher', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    hoisted.searchParams = new URLSearchParams();
    stubStores = {
      uiStore: new TestUIStore(),
      workspaceStore: new TestWorkspaceStore(),
      authStore: new TestAuthStore(),
    };
  });

  it('renders WorkspacePill with current workspace name', () => {
    renderSwitcher();
    const pill = screen.getByTestId('workspace-pill');
    expect(pill).toBeInTheDocument();
    expect(pill).toHaveTextContent('Alpha');
  });

  it('clicking the pill opens the popover (CURRENT heading visible)', async () => {
    const user = userEvent.setup();
    renderSwitcher();

    await user.click(screen.getByTestId('workspace-pill'));

    expect(await screen.findByText('CURRENT')).toBeInTheDocument();
    expect(stubStores!.uiStore.workspaceSwitcherOpen).toBe(true);
  });

  it('Escape key closes the popover', async () => {
    const user = userEvent.setup();
    renderSwitcher();

    await user.click(screen.getByTestId('workspace-pill'));
    expect(await screen.findByText('CURRENT')).toBeInTheDocument();

    await user.keyboard('{Escape}');

    await vi.waitFor(() => {
      expect(screen.queryByText('CURRENT')).not.toBeInTheDocument();
    });
  });

  it('CURRENT band renders the workspace name, role chip, and member count', async () => {
    const user = userEvent.setup();
    renderSwitcher();

    await user.click(screen.getByTestId('workspace-pill'));
    const header = await screen.findByTestId('switcher-current-header');
    expect(header).toHaveTextContent('Alpha');
    expect(within(header).getByTestId('switcher-current-role')).toHaveTextContent('Member');
    expect(header).toHaveTextContent('· 12');
  });

  it('SWITCH TO band shows RECENT subgroup with non-current workspaces only', async () => {
    const user = userEvent.setup();
    renderSwitcher();

    await user.click(screen.getByTestId('workspace-pill'));

    expect(await screen.findByText('RECENT')).toBeInTheDocument();
    expect(screen.getByTestId('switcher-ws-beta')).toBeInTheDocument();
    expect(screen.getByTestId('switcher-ws-gamma')).toBeInTheDocument();
    // Current workspace must not appear in either SWITCH TO subgroup
    expect(screen.queryByTestId('switcher-ws-alpha')).not.toBeInTheDocument();
  });

  it('typing "be" filters the lists down to Beta', async () => {
    const user = userEvent.setup();
    renderSwitcher();

    await user.click(screen.getByTestId('workspace-pill'));
    const input = await screen.findByPlaceholderText('Search workspaces…');
    await user.type(input, 'be');

    expect(screen.queryByTestId('switcher-ws-beta')).toBeInTheDocument();
    expect(screen.queryByTestId('switcher-ws-gamma')).not.toBeInTheDocument();
  });

  it("clicking beta row calls addRecentWorkspace('beta'), router.push('/beta'), and closes popover", async () => {
    const user = userEvent.setup();
    renderSwitcher();

    await user.click(screen.getByTestId('workspace-pill'));
    const betaRow = await screen.findByTestId('switcher-ws-beta');
    await user.click(betaRow);

    expect(hoisted.addRecentWorkspace).toHaveBeenCalledWith('beta');
    expect(hoisted.addRecentWorkspace).not.toHaveBeenCalledWith(
      expect.objectContaining({ id: expect.any(String) })
    );

    expect(hoisted.push).toHaveBeenCalledWith('/beta');
    expect(stubStores!.uiStore.workspaceSwitcherOpen).toBe(false);
  });

  it('first RECENT row (beta) renders the ⌘2 kbd label', async () => {
    const user = userEvent.setup();
    renderSwitcher();

    await user.click(screen.getByTestId('workspace-pill'));
    const betaRow = await screen.findByTestId('switcher-ws-beta');
    expect(within(betaRow).getByText('⌘2')).toBeInTheDocument();
  });

  it('second RECENT row (gamma) renders the ⌘3 kbd label', async () => {
    const user = userEvent.setup();
    renderSwitcher();

    await user.click(screen.getByTestId('workspace-pill'));
    const gammaRow = await screen.findByTestId('switcher-ws-gamma');
    expect(within(gammaRow).getByText('⌘3')).toBeInTheDocument();
  });

  it('per-row role badge is rendered (beta = Admin, gamma = Guest)', async () => {
    const user = userEvent.setup();
    renderSwitcher();

    await user.click(screen.getByTestId('workspace-pill'));
    const betaRow = await screen.findByTestId('switcher-ws-beta');
    const gammaRow = await screen.findByTestId('switcher-ws-gamma');
    expect(within(betaRow).getByText('Admin')).toBeInTheDocument();
    expect(within(gammaRow).getByText('Guest')).toBeInTheDocument();
  });

  it('clicking AI providers row opens settings modal at ai-providers tab', async () => {
    const user = userEvent.setup();
    renderSwitcher();

    await user.click(screen.getByTestId('workspace-pill'));
    await user.click(await screen.findByTestId('switcher-current-ai-providers'));

    expect(hoisted.openSettings).toHaveBeenCalledWith('ai-providers');
    expect(hoisted.push).not.toHaveBeenCalledWith(expect.stringContaining('/settings'));
  });

  it('clicking Members & invites row routes to /alpha/settings/members', async () => {
    const user = userEvent.setup();
    renderSwitcher();

    await user.click(screen.getByTestId('workspace-pill'));
    await user.click(await screen.findByTestId('switcher-current-members'));

    expect(hoisted.push).toHaveBeenCalledWith('/alpha/settings/members');
  });

  it('clicking Workspace settings row opens settings modal at general tab', async () => {
    const user = userEvent.setup();
    renderSwitcher();

    await user.click(screen.getByTestId('workspace-pill'));
    await user.click(await screen.findByTestId('switcher-current-settings'));

    expect(hoisted.openSettings).toHaveBeenCalledWith('general');
  });

  it('Leave workspace row is visible for non-owner roles', async () => {
    const user = userEvent.setup();
    renderSwitcher();

    await user.click(screen.getByTestId('workspace-pill'));
    expect(await screen.findByTestId('switcher-current-leave')).toBeInTheDocument();
  });

  it('Leave workspace row is hidden for owners', async () => {
    stubStores!.authStore.setRole('id-alpha', 'OWNER');

    const user = userEvent.setup();
    renderSwitcher();

    await user.click(screen.getByTestId('workspace-pill'));
    await screen.findByTestId('switcher-current-header');
    expect(screen.queryByTestId('switcher-current-leave')).not.toBeInTheDocument();
  });

  it('clicking + New workspace opens CreateWorkspaceDialog', async () => {
    const user = userEvent.setup();
    renderSwitcher();

    await user.click(screen.getByTestId('workspace-pill'));
    await user.click(await screen.findByTestId('switcher-new-workspace'));

    const dialog = await screen.findByRole('dialog');
    expect(within(dialog).getByRole('heading', { name: 'Create workspace' })).toBeInTheDocument();
  });

  it('mount with ?switcher=1 opens the popover automatically', async () => {
    hoisted.searchParams = new URLSearchParams('switcher=1');

    await act(async () => {
      renderSwitcher();
    });

    expect(await screen.findByText('CURRENT')).toBeInTheDocument();
    expect(stubStores!.uiStore.workspaceSwitcherOpen).toBe(true);
  });
});

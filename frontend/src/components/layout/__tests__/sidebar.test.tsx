/**
 * Sidebar v3 — Surface 1 unit tests (Plan 90-04).
 *
 * Verifies the v3 stack order, the +New chat /chat route contract
 * (blocker-4 — flat /${slug}/chat, no /chat/new, no chatsApi), the
 * ⌘K Search button → openCommandPalette wiring, the RECENT CHATS
 * empty-state copy, the WORKSPACE accordion canonical entry order
 * with Phase 84 routes (/tasks, /topics — NOT /issues, /notes), and
 * the NAV-04 sweep (no inline <input placeholder="Search…">).
 *
 * @module components/layout/__tests__/sidebar.test
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { makeAutoObservable } from 'mobx';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { TooltipProvider } from '@/components/ui/tooltip';

// jsdom: cmdk + Radix Popover call scrollIntoView on mount.
if (!Element.prototype.scrollIntoView) {
  Element.prototype.scrollIntoView = vi.fn();
}

// jsdom: Radix uses ResizeObserver; provide a no-op stub.
if (typeof globalThis.ResizeObserver === 'undefined') {
  globalThis.ResizeObserver = class {
    observe(): void {}
    unobserve(): void {}
    disconnect(): void {}
  } as unknown as typeof ResizeObserver;
}

// ---------------------------------------------------------------------------
// Hoisted mock state
// ---------------------------------------------------------------------------

const hoisted = vi.hoisted(() => ({
  push: vi.fn(),
  replace: vi.fn(),
  searchParams: new URLSearchParams(),
  pathname: '/alpha',
  params: { workspaceSlug: 'alpha' } as { workspaceSlug: string },
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
  usePathname: () => hoisted.pathname,
  useSearchParams: () => hoisted.searchParams,
  useParams: () => hoisted.params,
}));

// ---------------------------------------------------------------------------
// Internal helpers WorkspaceSwitcher uses (kept inert for sidebar tests)
// ---------------------------------------------------------------------------

vi.mock('@/hooks/useSwitcherQueryStringSync', () => ({
  useSwitcherQueryStringSync: () => undefined,
}));

vi.mock('@/components/workspace-selector', () => ({
  addRecentWorkspace: (slug: string) => hoisted.addRecentWorkspace(slug),
  getRecentWorkspaces: () => [{ slug: 'alpha', lastVisited: 1 }],
}));

vi.mock('@/lib/workspace-nav', () => ({
  getLastWorkspacePath: (slug: string) => `/${slug}`,
  getOrderedRecentWorkspaces: () => [],
}));

vi.mock('@/features/settings/settings-modal-context', () => ({
  useSettingsModal: () => ({
    open: false,
    activeSection: 'general',
    openSettings: hoisted.openSettings,
    closeSettings: vi.fn(),
    setActiveSection: vi.fn(),
  }),
}));

vi.mock('@/services/api/workspaces', () => ({
  workspacesApi: {
    get: vi.fn(),
    list: vi.fn().mockResolvedValue({ items: [] }),
    create: vi.fn(),
  },
}));

// ---------------------------------------------------------------------------
// MobX-backed stores
// ---------------------------------------------------------------------------

type Workspace = { id: string; slug: string; name: string };

class TestUIStore {
  sidebarCollapsed = false;
  workspaceSwitcherOpen = false;
  commandPaletteOpen = false;
  theme: 'light' | 'dark' | 'system' = 'system';
  isFocusMode = false;
  sidebarWidth = 240;

  constructor() {
    makeAutoObservable(this);
  }

  toggleSidebar(): void {
    this.sidebarCollapsed = !this.sidebarCollapsed;
  }
  setSidebarCollapsed(v: boolean): void {
    this.sidebarCollapsed = v;
  }
  setTheme(v: 'light' | 'dark' | 'system'): void {
    this.theme = v;
  }
  openCommandPalette(): void {
    this.commandPaletteOpen = true;
  }
  closeCommandPalette(): void {
    this.commandPaletteOpen = false;
  }
  toggleCommandPalette(): void {
    this.commandPaletteOpen = !this.commandPaletteOpen;
  }
  openWorkspaceSwitcher(): void {
    this.workspaceSwitcherOpen = true;
  }
  closeWorkspaceSwitcher(): void {
    this.workspaceSwitcherOpen = false;
  }
}

const featureToggles = {
  notes: true,
  issues: true,
  projects: true,
  members: true,
  knowledge: true,
  docs: true,
  skills: true,
  costs: true,
  approvals: true,
};

class TestWorkspaceStore {
  workspaces = new Map<string, Workspace>([
    ['id-alpha', { id: 'id-alpha', slug: 'alpha', name: 'Alpha' }],
    ['id-beta', { id: 'id-beta', slug: 'beta', name: 'Beta' }],
  ]);
  currentWorkspaceId: string | null = 'id-alpha';
  currentUserRole: 'owner' | 'admin' | 'member' | 'guest' = 'owner';
  error: string | null = null;
  featureToggles = featureToggles;
  isLoading = false;

  constructor() {
    makeAutoObservable(this);
  }

  get workspaceList(): Workspace[] {
    return Array.from(this.workspaces.values()).sort((a, b) =>
      a.name.localeCompare(b.name)
    );
  }

  get currentWorkspace(): Workspace | null {
    return this.currentWorkspaceId
      ? (this.workspaces.get(this.currentWorkspaceId) ?? null)
      : null;
  }

  getWorkspaceBySlug(slug: string): Workspace | undefined {
    return this.workspaceList.find((w) => w.slug === slug);
  }

  isFeatureEnabled(key: keyof typeof featureToggles): boolean {
    return !!this.featureToggles[key];
  }

  selectWorkspace(): void {}
  fetchWorkspaces(): void {}
  async createWorkspace(): Promise<Workspace | null> {
    return null;
  }
}

class TestNotificationStore {
  unreadCount = 0;
  sortedNotifications: unknown[] = [];
  notifications: unknown[] = [];
  totalPages = 0;
  currentPage = 1;
  isLoading = false;
  error: null = null;

  constructor() {
    makeAutoObservable(this);
  }
  startPolling(): void {}
  stopPolling(): void {}
  fetchNotifications(): void {}
  fetchUnreadCount(): void {}
  markAllAsRead(): void {}
  markAsRead(): void {}
  markRead(): void {}
  markAllRead(): void {}
  removeNotification(): void {}
  clearAll(): void {}
}

class TestAuthStore {
  user = {
    id: 'u1',
    name: 'Test User',
    email: 'test@test.com',
    avatarUrl: null,
  };
  userDisplayName = 'Test User';
  userInitials = 'TU';
  isAuthenticated = true;
  constructor() {
    makeAutoObservable(this);
  }
  logout(): void {}
}

let stubStores: {
  uiStore: TestUIStore;
  workspaceStore: TestWorkspaceStore;
  notificationStore: TestNotificationStore;
  authStore: TestAuthStore;
} | null = null;

vi.mock('@/stores', () => ({
  useUIStore: () => stubStores!.uiStore,
  useWorkspaceStore: () => stubStores!.workspaceStore,
  useNotificationStore: () => stubStores!.notificationStore,
  useAuthStore: () => stubStores!.authStore,
}));

// ---------------------------------------------------------------------------
// Hooks consumed by the v3 sidebar
// ---------------------------------------------------------------------------

vi.mock('@/features/notes/hooks', () => ({
  useCreateNote: () => ({ mutate: vi.fn(), isPending: false }),
  createNoteDefaults: () => ({}),
}));

vi.mock('@/features/projects/hooks/useProjects', () => ({
  useProjects: () => ({ data: { items: [] }, isLoading: false }),
  selectAllProjects: () => [],
}));

vi.mock('@/features/approvals/hooks/use-approvals', () => ({
  usePendingApprovalCount: () => 0,
}));

vi.mock('@/hooks/usePinnedNotes', () => ({
  usePinnedNotes: () => ({ data: [] }),
}));

vi.mock('@/hooks/useMediaQuery', () => ({
  useResponsive: () => ({ isSmallScreen: false }),
}));

vi.mock('@/components/layout/notification-panel', () => ({
  NotificationPanel: () => <div data-testid="notification-panel-stub" />,
}));

vi.mock('@/features/notes/components/TemplatePicker', () => ({
  TemplatePicker: () => null,
}));

vi.mock('./useNewNoteFlow', () => ({
  useNewNoteFlow: () => ({
    showTemplatePicker: false,
    open: vi.fn(),
    handleTemplateConfirm: vi.fn(),
    handleTemplateClose: vi.fn(),
  }),
}));

// Sidebar reads the AI sessions list via @tanstack/react-query. Mock the
// network module so the test does not need a real fetch, and wrap the render
// in a fresh QueryClient (per test, no retries) below.
vi.mock('@/services/api/ai', () => ({
  aiApi: {
    listSessions: vi.fn().mockResolvedValue({ sessions: [] }),
  },
}));

// TopicTreeContainer is heavy and depends on its own data fetching pipeline.
// Stub it for sidebar shell tests — we only care about nav row presence.
vi.mock('@/features/topics/components', () => ({
  TopicTreeContainer: () => <div data-testid="topic-tree-stub" />,
}));

// ---------------------------------------------------------------------------
// Component under test
// ---------------------------------------------------------------------------
import { Sidebar } from '../sidebar';

function renderSidebar() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <Sidebar />
      </TooltipProvider>
    </QueryClientProvider>
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('Sidebar v3 (Surface 1 — Plan 90-04)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    hoisted.searchParams = new URLSearchParams();
    hoisted.pathname = '/alpha';
    hoisted.params = { workspaceSlug: 'alpha' };
    stubStores = {
      uiStore: new TestUIStore(),
      workspaceStore: new TestWorkspaceStore(),
      notificationStore: new TestNotificationStore(),
      authStore: new TestAuthStore(),
    };
  });

  it('renders the rail at 240px width on the snow surface', () => {
    renderSidebar();
    const rail = screen.getByTestId('sidebar');
    expect(rail.className).toContain('w-[240px]');
    expect(rail.className).toContain('bg-[var(--surface-snow)]');
    expect(rail.className).toContain('border-r');
  });

  it('top stack is rendered in DOM order: workspace-pill → new-chat-button → sidebar-search-button', () => {
    renderSidebar();
    const pill = screen.getByTestId('workspace-pill');
    const newChat = screen.getByTestId('new-chat-button');
    const search = screen.getByTestId('sidebar-search-button');

    // compareDocumentPosition: 4 == FOLLOWING → first arg precedes second arg
    expect(pill.compareDocumentPosition(newChat) & Node.DOCUMENT_POSITION_FOLLOWING).toBe(
      Node.DOCUMENT_POSITION_FOLLOWING
    );
    expect(newChat.compareDocumentPosition(search) & Node.DOCUMENT_POSITION_FOLLOWING).toBe(
      Node.DOCUMENT_POSITION_FOLLOWING
    );
  });

  it('+ New chat click navigates to EXACTLY /alpha/chat (no /new, no /${chatId})', async () => {
    const user = userEvent.setup();
    renderSidebar();

    await user.click(screen.getByTestId('new-chat-button'));

    expect(hoisted.push).toHaveBeenCalledWith('/alpha/chat');
    // Hard contract: must NEVER be called with the legacy /new suffix or any
    // dynamic chat-id path.
    expect(hoisted.push).not.toHaveBeenCalledWith('/alpha/chat/new');
    expect(hoisted.push).not.toHaveBeenCalledWith(expect.stringMatching(/^\/alpha\/chat\/.+/));
  });

  it('+ New chat handler is synchronous (no chatsApi reference)', async () => {
    const user = userEvent.setup();
    renderSidebar();
    // No throws / no unhandled promise rejections — handler is a plain
    // router.push wrapper. If we ever reintroduce a chatsApi.create call this
    // assertion would not catch the type, but the route assertion above does.
    await user.click(screen.getByTestId('new-chat-button'));
    expect(hoisted.push).toHaveBeenCalledTimes(1);
  });

  it('⌘K Search button click opens the command palette', async () => {
    const user = userEvent.setup();
    renderSidebar();

    expect(stubStores!.uiStore.commandPaletteOpen).toBe(false);
    await user.click(screen.getByTestId('sidebar-search-button'));
    expect(stubStores!.uiStore.commandPaletteOpen).toBe(true);
  });

  it('RECENT CHATS empty state renders the calm copy', () => {
    renderSidebar();
    expect(screen.getByTestId('recent-chats-header')).toHaveTextContent('RECENT CHATS');
    expect(screen.getByTestId('recent-chats-empty')).toBeInTheDocument();
    expect(screen.getByText('No recent chats')).toBeInTheDocument();
    expect(screen.getByText(/Start a new chat to see it here/)).toBeInTheDocument();
  });

  it('WORKSPACE accordion is expanded by default and shows only entries with shipped routes', () => {
    // Knowledge graph and Integrations are hidden via `hiddenPendingRoute`
    // until their routes ship — see sidebar.tsx WORKSPACE_ENTRIES.
    renderSidebar();

    const list = screen.getByTestId('workspace-accordion-list');
    const links = within(list).getAllByRole('link');
    const labels = links.map((l) => (l.textContent ?? '').replace(/\s*\d+\s*$/, '').trim());

    expect(labels).toEqual(['Projects', 'Tasks', 'Topics', 'Skills', 'Members']);
  });

  it('hides Integrations and Knowledge graph entries while their routes 404', () => {
    renderSidebar();
    expect(screen.queryByTestId('nav-integrations')).not.toBeInTheDocument();
    expect(screen.queryByTestId('nav-kg')).not.toBeInTheDocument();
  });

  it('Tasks link href is /alpha/tasks (Phase 84 — NOT /alpha/issues)', () => {
    renderSidebar();
    const tasksLink = screen.getByTestId('nav-tasks');
    expect(tasksLink).toHaveAttribute('href', '/alpha/tasks');
    expect(tasksLink).not.toHaveAttribute('href', '/alpha/issues');
  });

  it('Topics link href is /alpha/topics (Phase 84 — NOT /alpha/notes)', () => {
    renderSidebar();
    const topicsLink = screen.getByTestId('nav-topics');
    expect(topicsLink).toHaveAttribute('href', '/alpha/topics');
    expect(topicsLink).not.toHaveAttribute('href', '/alpha/notes');
  });

  it('Projects, Skills, Members links target the correct Phase 84 routes', () => {
    renderSidebar();
    expect(screen.getByTestId('nav-projects')).toHaveAttribute('href', '/alpha/projects');
    expect(screen.getByTestId('nav-skills')).toHaveAttribute('href', '/alpha/skills');
    expect(screen.getByTestId('nav-members')).toHaveAttribute('href', '/alpha/members');
  });

  it('+ New chat button uses the canonical primary CTA tokens (≥4.5:1 contrast)', () => {
    // Bug fix: the previous classes used `bg-[var(--brand-primary)]` /
    // `hover:bg-[var(--brand-dark)]`, but neither token is defined in
    // globals.css, so the button rendered transparent and looked disabled.
    // The fix maps the button to the design-system primary tokens used by
    // every other CTA (Invite member, form submits).
    renderSidebar();
    const newChat = screen.getByTestId('new-chat-button');

    expect(newChat).toHaveClass('bg-primary');
    expect(newChat).toHaveClass('text-primary-foreground');
    expect(newChat).toHaveClass('hover:bg-primary/90');
    // Hard contract: must NEVER reintroduce the undefined `--brand-primary`
    // / `--brand-dark` token references.
    expect(newChat.className).not.toContain('--brand-primary');
    expect(newChat.className).not.toContain('--brand-dark');
  });

  it('clicking the WORKSPACE trigger collapses the accordion and hides Projects', async () => {
    const user = userEvent.setup();
    renderSidebar();

    expect(screen.getByTestId('nav-projects')).toBeInTheDocument();
    // Accordion trigger has aria-controls / data-state; pick by exact name.
    const triggers = screen.getAllByRole('button', { name: /^WORKSPACE$/i });
    const accordionTrigger = triggers.find(
      (b) => b.getAttribute('data-state') === 'open'
    );
    expect(accordionTrigger).toBeDefined();
    await user.click(accordionTrigger!);

    await vi.waitFor(() => {
      expect(screen.queryByTestId('nav-projects')).not.toBeInTheDocument();
    });
  });

  it('does not render any inline <input placeholder="Search…"> (NAV-04 sweep)', () => {
    renderSidebar();
    const sidebar = screen.getByTestId('sidebar');
    const searchInputs = sidebar.querySelectorAll('input[placeholder*="earch" i]');
    expect(searchInputs.length).toBe(0);
    // The ⌘K Search affordance is a <button>, never an input.
    expect(screen.getByTestId('sidebar-search-button').tagName).toBe('BUTTON');
  });

  it('disabled feature toggles hide the corresponding entry (issues=false hides Tasks)', () => {
    stubStores!.workspaceStore.featureToggles = {
      ...featureToggles,
      issues: false,
    };
    renderSidebar();
    expect(screen.queryByTestId('nav-tasks')).not.toBeInTheDocument();
    // Topics still visible
    expect(screen.getByTestId('nav-topics')).toBeInTheDocument();
  });
});

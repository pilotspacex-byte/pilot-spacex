/**
 * Unit tests for Sidebar navigation (v3).
 *
 * The v3 sidebar replaces the flat section list with:
 *   - primary nav (Home, Pilot AI)
 *   - a WORKSPACE accordion grouping Projects/Issues/Notes/Skills/Knowledge/Members/Integrations
 *   - an AI section gated to Owner/Admin
 *   - a search-as-button that opens the Command Palette
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Sidebar } from '../sidebar';
import { TooltipProvider } from '@/components/ui/tooltip';

// Mock mobx-react-lite
vi.mock('mobx-react-lite', () => ({
  observer: <T,>(component: T) => component,
}));

// Mock next/navigation
const mockPathname = vi.fn(() => '/test-ws');
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), prefetch: vi.fn(), back: vi.fn() }),
  usePathname: () => mockPathname(),
  useSearchParams: () => new URLSearchParams(),
  useParams: () => ({ workspaceSlug: 'test-ws' }),
}));

// Mock stores
const mockSidebarCollapsed = vi.fn(() => false);
const mockOpenCommandPalette = vi.fn();
const mockWorkspace = { slug: 'test-ws', id: 'test-ws', name: 'Test Workspace' };
const defaultFeatureToggles = {
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
const mockFeatureToggles = { ...defaultFeatureToggles };

vi.mock('@/stores', () => ({
  useUIStore: () => ({
    sidebarCollapsed: mockSidebarCollapsed(),
    toggleSidebar: vi.fn(),
    setSidebarCollapsed: vi.fn(),
    theme: 'system' as const,
    setTheme: vi.fn(),
    openCommandPalette: mockOpenCommandPalette,
  }),
  useWorkspaceStore: () => ({
    currentWorkspace: mockWorkspace,
    workspaceList: [mockWorkspace],
    getWorkspaceBySlug: () => mockWorkspace,
    fetchWorkspaces: vi.fn(),
    isLoading: false,
    currentUserRole: 'owner' as const,
    currentWorkspaceId: 'test-ws',
    isOwner: true,
    isAdmin: false,
    featureToggles: mockFeatureToggles,
    isFeatureEnabled: (key: keyof typeof mockFeatureToggles) => !!mockFeatureToggles[key],
  }),
  useNotificationStore: () => ({
    unreadCount: 0,
    sortedNotifications: [],
    notifications: [],
    totalPages: 0,
    currentPage: 1,
    isLoading: false,
    error: null,
    markAllAsRead: vi.fn(),
    markAsRead: vi.fn(),
    markRead: vi.fn(),
    markAllRead: vi.fn(),
    removeNotification: vi.fn(),
    clearAll: vi.fn(),
    fetchNotifications: vi.fn(),
    fetchUnreadCount: vi.fn(),
    startPolling: vi.fn(),
    stopPolling: vi.fn(),
  }),
  useAuthStore: () => ({
    user: { id: 'u1', name: 'Test', email: 'test@test.com', avatarUrl: null },
    userDisplayName: 'Test',
    userInitials: 'T',
    isAuthenticated: true,
    logout: vi.fn(),
  }),
}));

// Mock features/notes/hooks
vi.mock('@/features/notes/hooks', () => ({
  useCreateNote: () => ({ mutate: vi.fn(), isPending: false }),
  createNoteDefaults: () => ({}),
}));

// Sidebar no longer depends on projects, but guard remaining imports that may load.
vi.mock('@/features/projects/hooks/useProjects', () => ({
  useProjects: () => ({ data: undefined, isLoading: false }),
  selectAllProjects: () => [],
}));

// Mock ProjectPageTree / PersonalPagesList — still imported by layout barrel in tests.
vi.mock('@/components/layout/ProjectPageTree', () => ({
  ProjectPageTree: () => null,
}));
vi.mock('@/components/layout/PersonalPagesList', () => ({
  PersonalPagesList: () => null,
}));

// Mock workspace API
vi.mock('@/services/api/workspaces', () => ({
  workspacesApi: {
    get: vi.fn(),
    list: vi.fn().mockResolvedValue({ items: [] }),
    create: vi.fn(),
  },
}));

// Mock supabase
vi.mock('@/lib/supabase', () => ({
  supabase: {
    auth: { getSession: vi.fn().mockResolvedValue({ data: { session: null } }) },
  },
}));

// Mock useResponsive
vi.mock('@/hooks/useMediaQuery', () => ({
  useResponsive: () => ({ isSmallScreen: false }),
}));

// Mock approvals hook — sidebar calls usePendingApprovalCount for badge
vi.mock('@/features/approvals/hooks/use-approvals', () => ({
  usePendingApprovalCount: () => 0,
}));

// Mock AI store + SessionListStore so the recents effect resolves with no sessions.
vi.mock('@/stores/ai/AIStore', () => ({
  getAIStore: () => ({ pilotSpace: null }),
}));
vi.mock('@/stores/ai/SessionListStore', () => ({
  SessionListStore: class {
    sessions: unknown[] = [];
    async fetchSessions(): Promise<void> {
      /* noop */
    }
  },
}));

// Mock useSettingsModal — used by SidebarUserControls inside Sidebar
vi.mock('@/features/settings/settings-modal-context', () => ({
  useSettingsModal: () => ({ openSettings: vi.fn(), open: false, closeSettings: vi.fn() }),
}));

function renderSidebar() {
  return render(
    <TooltipProvider>
      <Sidebar />
    </TooltipProvider>
  );
}

describe('Sidebar v3', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockPathname.mockReturnValue('/test-ws');
    mockSidebarCollapsed.mockReturnValue(false);
    Object.assign(mockFeatureToggles, defaultFeatureToggles);
  });

  describe('primary nav', () => {
    it('renders Home and Pilot AI in the main navigation landmark', () => {
      renderSidebar();

      const mainNav = screen.getByRole('navigation', { name: 'Main navigation' });
      expect(mainNav).toBeInTheDocument();
      expect(screen.getByTestId('nav-home')).toBeInTheDocument();
      expect(screen.getByTestId('nav-pilot-ai')).toBeInTheDocument();
    });

    it('highlights Home on exact workspace path', () => {
      mockPathname.mockReturnValue('/test-ws');
      renderSidebar();

      const homeLink = screen.getByTestId('nav-home');
      expect(homeLink.className).toContain('bg-sidebar-accent');
      expect(homeLink).toHaveAttribute('aria-current', 'page');
    });
  });

  describe('search button', () => {
    it('renders an accessible button (not an input) with ⌘K hint', () => {
      renderSidebar();

      const searchBtn = screen.getByTestId('nav-search');
      expect(searchBtn).toBeInstanceOf(HTMLButtonElement);
      expect(searchBtn).toHaveAttribute('aria-label', 'Search');
      expect(searchBtn.textContent).toContain('⌘K');
    });

    it('opens the command palette when clicked', async () => {
      const user = userEvent.setup();
      renderSidebar();

      await user.click(screen.getByTestId('nav-search'));
      expect(mockOpenCommandPalette).toHaveBeenCalledOnce();
    });
  });

  describe('WORKSPACE accordion', () => {
    it('renders the accordion trigger with aria-expanded=true by default', () => {
      renderSidebar();

      const trigger = screen.getByTestId('workspace-accordion-trigger');
      expect(trigger).toBeInTheDocument();
      expect(trigger).toHaveAttribute('aria-expanded', 'true');
    });

    it('collapses and re-expands on click', async () => {
      const user = userEvent.setup();
      renderSidebar();

      const trigger = screen.getByTestId('workspace-accordion-trigger');
      await user.click(trigger);
      expect(trigger).toHaveAttribute('aria-expanded', 'false');

      await user.click(trigger);
      expect(trigger).toHaveAttribute('aria-expanded', 'true');
    });

    it('renders all workspace children when expanded', () => {
      renderSidebar();

      expect(screen.getByTestId('nav-projects')).toBeInTheDocument();
      expect(screen.getByTestId('nav-issues')).toBeInTheDocument();
      expect(screen.getByTestId('nav-notes')).toBeInTheDocument();
      expect(screen.getByTestId('nav-skills')).toBeInTheDocument();
      expect(screen.getByTestId('nav-knowledge')).toBeInTheDocument();
      expect(screen.getByTestId('nav-members')).toBeInTheDocument();
      expect(screen.getByTestId('nav-integrations')).toBeInTheDocument();
    });

    it('hides children whose feature is disabled', () => {
      mockFeatureToggles.knowledge = false;
      mockFeatureToggles.skills = false;
      renderSidebar();

      expect(screen.queryByTestId('nav-knowledge')).not.toBeInTheDocument();
      expect(screen.queryByTestId('nav-skills')).not.toBeInTheDocument();
      // Non-feature-gated items still render.
      expect(screen.getByTestId('nav-integrations')).toBeInTheDocument();
    });

    it('routes Integrations to the workspace settings sub-page', () => {
      renderSidebar();

      expect(screen.getByTestId('nav-integrations')).toHaveAttribute(
        'href',
        '/test-ws/settings/integrations'
      );
    });
  });

  describe('AI section', () => {
    it('renders AI navigation landmark with Costs (owner/admin only)', () => {
      renderSidebar();

      expect(screen.getByRole('navigation', { name: 'AI navigation' })).toBeInTheDocument();
      expect(screen.getByTestId('nav-costs')).toBeInTheDocument();
    });
  });

  describe('active state', () => {
    it('highlights Notes on nested note path', () => {
      mockPathname.mockReturnValue('/test-ws/notes/some-note-id');
      renderSidebar();

      const notesLink = screen.getByTestId('nav-notes');
      expect(notesLink.className).toContain('bg-sidebar-accent');
      expect(notesLink).toHaveAttribute('aria-current', 'page');
    });

    it('does not false-match prefix overlaps (e.g. /issues vs /issues-archive)', () => {
      mockPathname.mockReturnValue('/test-ws/issues-archive');
      renderSidebar();

      const issuesLink = screen.getByTestId('nav-issues');
      expect(issuesLink).not.toHaveAttribute('aria-current');
      expect(issuesLink.className).not.toMatch(/\bbg-sidebar-accent\b(?!\/)/);
    });
  });

  describe('collapsed rail', () => {
    it('hides accordion chrome and flattens workspace items', () => {
      mockSidebarCollapsed.mockReturnValue(true);
      renderSidebar();

      // No accordion trigger in collapsed mode — rail flattens the list.
      expect(screen.queryByTestId('workspace-accordion-trigger')).not.toBeInTheDocument();
      // Child links still rendered so keyboard/tooltip nav works.
      expect(screen.getByTestId('nav-projects')).toBeInTheDocument();
      expect(screen.getByTestId('nav-integrations')).toBeInTheDocument();
    });

    it('hides section header text when collapsed', () => {
      mockSidebarCollapsed.mockReturnValue(true);
      renderSidebar();

      expect(screen.queryByText('Workspace')).not.toBeInTheDocument();
      expect(screen.queryByText('AI')).not.toBeInTheDocument();
    });
  });

  describe('feature gating — top-level', () => {
    it('hides the New Note button when notes feature is disabled', () => {
      mockFeatureToggles.notes = false;
      renderSidebar();

      expect(screen.queryByTestId('new-note-button')).not.toBeInTheDocument();
    });

    it('shows the New Note button when notes feature is enabled', () => {
      mockFeatureToggles.notes = true;
      renderSidebar();

      expect(screen.getByTestId('new-note-button')).toBeInTheDocument();
    });
  });
});

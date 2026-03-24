/**
 * Unit tests for Sidebar navigation sections.
 *
 * Tests the restructured Main + AI section layout, section headers,
 * collapsed mode behavior, and Roles nav item.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
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
const mockWorkspace = { slug: 'test-ws', id: 'test-ws', name: 'Test Workspace' };
vi.mock('@/stores', () => ({
  useUIStore: () => ({
    sidebarCollapsed: mockSidebarCollapsed(),
    toggleSidebar: vi.fn(),
    setSidebarCollapsed: vi.fn(),
    theme: 'system' as const,
    setTheme: vi.fn(),
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
    featureToggles: {
      notes: true,
      issues: true,
      projects: true,
      members: true,
      knowledge: true,
      skills: true,
      costs: true,
      approvals: true,
    },
    isFeatureEnabled: (_key: string) => true,
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

// Mock useProjects — sidebar uses this to fetch workspace projects
vi.mock('@/features/projects/hooks/useProjects', () => ({
  useProjects: () => ({ data: undefined, isLoading: false }),
  selectAllProjects: () => [],
}));

// Mock ProjectPageTree and PersonalPagesList to avoid their hook dependencies in sidebar tests
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

// Mock usePinnedNotes — sidebar calls this via useQuery, which needs QueryClientProvider
vi.mock('@/hooks/usePinnedNotes', () => ({
  usePinnedNotes: () => ({ data: [] }),
}));

// Mock useSettingsModal — used by SidebarUserControls inside Sidebar
vi.mock('@/features/settings/settings-modal-context', () => ({
  useSettingsModal: () => ({ open: vi.fn(), isOpen: false }),
}));

function renderSidebar() {
  return render(
    <TooltipProvider>
      <Sidebar />
    </TooltipProvider>
  );
}

describe('Sidebar Navigation', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockPathname.mockReturnValue('/test-ws');
    mockSidebarCollapsed.mockReturnValue(false);
  });

  describe('section structure', () => {
    it('renders Main section items (Home, Notes, Issues, Projects, Members, Knowledge)', () => {
      renderSidebar();

      expect(screen.getByTestId('nav-home')).toBeInTheDocument();
      expect(screen.getByTestId('nav-notes')).toBeInTheDocument();
      expect(screen.getByTestId('nav-issues')).toBeInTheDocument();
      expect(screen.getByTestId('nav-projects')).toBeInTheDocument();
      expect(screen.getByTestId('nav-members')).toBeInTheDocument();
      expect(screen.getByTestId('nav-knowledge')).toBeInTheDocument();
    });

    it('renders AI section items (Chat, Skill, Costs)', () => {
      renderSidebar();

      expect(screen.getByTestId('nav-chat')).toBeInTheDocument();
      expect(screen.getByTestId('nav-roles')).toBeInTheDocument();
      expect(screen.getByTestId('nav-costs')).toBeInTheDocument();
    });

    it('renders section headers when sidebar is expanded', () => {
      renderSidebar();

      expect(screen.getByText('Main')).toBeInTheDocument();
      expect(screen.getByText('AI')).toBeInTheDocument();
    });

    it('hides section headers when sidebar is collapsed', () => {
      mockSidebarCollapsed.mockReturnValue(true);
      renderSidebar();

      expect(screen.queryByText('Main')).not.toBeInTheDocument();
      expect(screen.queryByText('AI')).not.toBeInTheDocument();
    });

    it('renders dot separator between sections when collapsed', () => {
      mockSidebarCollapsed.mockReturnValue(true);
      renderSidebar();

      const aiNav = screen.getByRole('navigation', { name: 'AI navigation' });
      const separator = aiNav.querySelector('.bg-sidebar-border');
      expect(separator).toBeInTheDocument();
      expect(separator).toHaveAttribute('aria-hidden', 'true');
    });

    it('renders two nav landmarks with aria-labels', () => {
      renderSidebar();

      expect(screen.getByRole('navigation', { name: 'Main navigation' })).toBeInTheDocument();
      expect(screen.getByRole('navigation', { name: 'AI navigation' })).toBeInTheDocument();
    });
  });

  describe('Skill nav item', () => {
    it('links to /test-ws/roles', () => {
      renderSidebar();

      const rolesLink = screen.getByTestId('nav-roles');
      expect(rolesLink).toHaveAttribute('href', '/test-ws/skills');
    });

    it('displays "Skill" label text', () => {
      renderSidebar();

      expect(screen.getByText('Skill')).toBeInTheDocument();
    });

    it('highlights Skill when pathname matches /test-ws/skills', () => {
      mockPathname.mockReturnValue('/test-ws/skills');
      renderSidebar();

      const rolesLink = screen.getByTestId('nav-roles');
      expect(rolesLink.className).toContain('bg-sidebar-accent');
    });
  });

  describe('Members nav item', () => {
    it('links to /test-ws/members', () => {
      renderSidebar();

      const membersLink = screen.getByTestId('nav-members');
      expect(membersLink).toHaveAttribute('href', '/test-ws/members');
    });

    it('displays "Members" label text', () => {
      renderSidebar();

      expect(screen.getByText('Members')).toBeInTheDocument();
    });

    it('highlights Members when pathname matches /test-ws/members', () => {
      mockPathname.mockReturnValue('/test-ws/members');
      renderSidebar();

      const membersLink = screen.getByTestId('nav-members');
      expect(membersLink.className).toContain('bg-sidebar-accent');
      expect(membersLink).toHaveAttribute('aria-current', 'page');
    });
  });

  describe('Chat rename', () => {
    it('displays "Chat" instead of "AI Chat"', () => {
      renderSidebar();

      expect(screen.getByText('Chat')).toBeInTheDocument();
      expect(screen.queryByText('AI Chat')).not.toBeInTheDocument();
    });
  });

  describe('active state', () => {
    it('highlights Home on exact workspace path', () => {
      mockPathname.mockReturnValue('/test-ws');
      renderSidebar();

      const homeLink = screen.getByTestId('nav-home');
      expect(homeLink.className).toContain('bg-sidebar-accent');
      expect(homeLink).toHaveAttribute('aria-current', 'page');
    });

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
});

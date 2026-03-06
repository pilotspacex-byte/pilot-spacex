/**
 * Unit tests for SidebarUserControls component.
 *
 * Tests the Claude iOS-inspired unified user card: notification dot,
 * dropdown items (notifications, profile, settings, sign out),
 * expanded/collapsed rendering, and ARIA labels.
 *
 * @module components/layout/__tests__/SidebarUserControls.test
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { SidebarUserControls } from '../sidebar';
import { TooltipProvider } from '@/components/ui/tooltip';
import type { AuthStore } from '@/stores/AuthStore';
import type { NotificationStore } from '@/stores/NotificationStore';
import type { UIStore } from '@/stores/UIStore';

vi.mock('mobx-react-lite', () => ({
  observer: <T,>(component: T) => component,
}));

const mockPush = vi.fn();
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush, replace: vi.fn(), prefetch: vi.fn(), back: vi.fn() }),
  usePathname: () => '/pilot-space-demo',
  useSearchParams: () => new URLSearchParams(),
  useParams: () => ({}),
}));

// Mock stores to prevent supabase import chain
vi.mock('@/stores', () => ({
  useUIStore: () => ({ sidebarCollapsed: false, toggleSidebar: vi.fn() }),
  useWorkspaceStore: () => ({ currentWorkspace: { slug: 'test-ws', id: 'test-ws' } }),
  useNoteStore: () => ({ pinnedNotes: [], recentNotes: [] }),
  useNotificationStore: () => ({ unreadCount: 0, markAllAsRead: vi.fn() }),
  useAuthStore: () => ({
    user: null,
    userDisplayName: '',
    userInitials: '',
    logout: vi.fn(),
  }),
}));

// Mock features/notes/hooks to prevent supabase import chain
vi.mock('@/features/notes/hooks', () => ({
  useCreateNote: () => ({ mutate: vi.fn(), isPending: false }),
  createNoteDefaults: () => ({}),
}));

// Mock workspace API to prevent supabase import chain via workspace-switcher
vi.mock('@/services/api/workspaces', () => ({
  workspacesApi: {
    get: vi.fn(),
    list: vi.fn().mockResolvedValue({ items: [] }),
    create: vi.fn(),
  },
}));

// Mock supabase to prevent NEXT_PUBLIC_SUPABASE_URL missing error
vi.mock('@/lib/supabase', () => ({
  supabase: {
    auth: { getSession: vi.fn().mockResolvedValue({ data: { session: null } }) },
  },
}));

function createMockAuthStore(overrides: Partial<AuthStore> = {}): AuthStore {
  return {
    user: {
      id: 'user-1',
      name: 'John Doe',
      email: 'john@example.com',
      avatarUrl: null,
    },
    userDisplayName: 'John Doe',
    userInitials: 'JD',
    logout: vi.fn(),
    ...overrides,
  } as unknown as AuthStore;
}

function createMockNotificationStore(
  overrides: Partial<NotificationStore> = {}
): NotificationStore {
  return {
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
    ...overrides,
  } as unknown as NotificationStore;
}

function createMockUIStore(overrides: Partial<UIStore> = {}): UIStore {
  return {
    theme: 'system' as const,
    setTheme: vi.fn(),
    resolvedTheme: 'light' as const,
    sidebarCollapsed: false,
    ...overrides,
  } as unknown as UIStore;
}

function renderControls({
  collapsed = false,
  workspaceSlug = 'test-ws',
  workspaceId = 'test-ws',
  authStore,
  notificationStore,
  uiStore,
}: {
  collapsed?: boolean;
  workspaceSlug?: string;
  workspaceId?: string;
  authStore?: AuthStore;
  notificationStore?: NotificationStore;
  uiStore?: UIStore;
} = {}) {
  const auth = authStore ?? createMockAuthStore();
  const notifications = notificationStore ?? createMockNotificationStore();
  const ui = uiStore ?? createMockUIStore();

  return render(
    <TooltipProvider>
      <SidebarUserControls
        collapsed={collapsed}
        workspaceSlug={workspaceSlug}
        workspaceId={workspaceId}
        authStore={auth}
        notificationStore={notifications}
        uiStore={ui}
      />
    </TooltipProvider>
  );
}

describe('SidebarUserControls', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('expanded mode', () => {
    it('renders user display name in trigger', () => {
      renderControls();
      expect(screen.getByText('John Doe')).toBeInTheDocument();
    });

    it('renders user initials in avatar fallback', () => {
      renderControls();
      expect(screen.getByText('JD')).toBeInTheDocument();
    });

    it('renders account button with aria-label', () => {
      renderControls();
      expect(screen.getByRole('button', { name: 'Account' })).toBeInTheDocument();
    });

    it('opens unified dropdown with menu items', async () => {
      const user = userEvent.setup();
      renderControls();

      await user.click(screen.getByRole('button', { name: 'Account' }));

      expect(screen.getByText('Theme')).toBeInTheDocument();
      expect(screen.getByText('Profile')).toBeInTheDocument();
      expect(screen.getByText('Settings')).toBeInTheDocument();
      expect(screen.getByText('Sign out')).toBeInTheDocument();
    });

    it('shows user name and email in dropdown header', async () => {
      const user = userEvent.setup();
      renderControls();

      await user.click(screen.getByRole('button', { name: 'Account' }));

      // Name appears in trigger and dropdown header
      const nameElements = screen.getAllByText('John Doe');
      expect(nameElements.length).toBeGreaterThanOrEqual(2);
      expect(screen.getByText('john@example.com')).toBeInTheDocument();
    });

    it('navigates to profile settings on Profile click', async () => {
      const user = userEvent.setup();
      renderControls({ workspaceSlug: 'my-ws' });

      await user.click(screen.getByRole('button', { name: 'Account' }));
      await user.click(screen.getByText('Profile'));

      expect(mockPush).toHaveBeenCalledWith('/my-ws/settings/profile');
    });

    it('navigates to settings on Settings click', async () => {
      const user = userEvent.setup();
      renderControls({ workspaceSlug: 'my-ws' });

      await user.click(screen.getByRole('button', { name: 'Account' }));
      await user.click(screen.getByText('Settings'));

      expect(mockPush).toHaveBeenCalledWith('/my-ws/settings');
    });

    it('calls authStore.logout on Sign out click', async () => {
      const user = userEvent.setup();
      const authStore = createMockAuthStore();
      renderControls({ authStore });

      await user.click(screen.getByRole('button', { name: 'Account' }));
      await user.click(screen.getByText('Sign out'));

      expect(authStore.logout).toHaveBeenCalledTimes(1);
    });

    it('shows theme submenu trigger in dropdown', async () => {
      const user = userEvent.setup();
      const uiStore = createMockUIStore();
      renderControls({ uiStore });

      await user.click(screen.getByRole('button', { name: 'Account' }));

      expect(screen.getByText('Theme')).toBeInTheDocument();
    });

    it('falls back to "User" when userDisplayName is empty', () => {
      const authStore = createMockAuthStore({
        userDisplayName: '',
        userInitials: '',
      } as unknown as Partial<AuthStore>);
      renderControls({ authStore });

      expect(screen.getByText('User')).toBeInTheDocument();
      expect(screen.getByText('U')).toBeInTheDocument();
    });
  });

  describe('collapsed mode', () => {
    it('renders account button with aria-label', () => {
      renderControls({ collapsed: true });
      expect(screen.getByRole('button', { name: 'Account' })).toBeInTheDocument();
    });

    it('does not render user display name text', () => {
      renderControls({ collapsed: true });
      expect(screen.queryByText('John Doe')).not.toBeInTheDocument();
    });

    it('opens unified dropdown in collapsed mode', async () => {
      const user = userEvent.setup();
      renderControls({ collapsed: true });

      await user.click(screen.getByRole('button', { name: 'Account' }));

      expect(screen.getByText('Theme')).toBeInTheDocument();
      expect(screen.getByText('Profile')).toBeInTheDocument();
      expect(screen.getByText('Settings')).toBeInTheDocument();
      expect(screen.getByText('Sign out')).toBeInTheDocument();
    });

    it('shows settings item with test id in dropdown', async () => {
      const user = userEvent.setup();
      renderControls({ collapsed: true, workspaceSlug: 'my-ws' });

      await user.click(screen.getByRole('button', { name: 'Account' }));

      expect(screen.getByTestId('nav-settings')).toBeInTheDocument();
    });
  });
});

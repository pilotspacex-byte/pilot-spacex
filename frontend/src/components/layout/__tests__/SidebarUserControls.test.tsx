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
    markAllAsRead: vi.fn(),
    ...overrides,
  } as unknown as NotificationStore;
}

function renderControls({
  collapsed = false,
  workspaceSlug = 'test-ws',
  authStore,
  notificationStore,
}: {
  collapsed?: boolean;
  workspaceSlug?: string;
  authStore?: AuthStore;
  notificationStore?: NotificationStore;
} = {}) {
  const auth = authStore ?? createMockAuthStore();
  const notifications = notificationStore ?? createMockNotificationStore();

  return render(
    <TooltipProvider>
      <SidebarUserControls
        collapsed={collapsed}
        workspaceSlug={workspaceSlug}
        authStore={auth}
        notificationStore={notifications}
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

    it('does not show notification dot when unreadCount is 0', () => {
      renderControls();
      expect(screen.queryByTestId('notification-dot')).not.toBeInTheDocument();
    });

    it('shows notification dot when unreadCount > 0', () => {
      const notificationStore = createMockNotificationStore({ unreadCount: 5 });
      renderControls({ notificationStore });
      expect(screen.getByTestId('notification-dot')).toBeInTheDocument();
    });

    it('opens unified dropdown with all menu items', async () => {
      const user = userEvent.setup();
      renderControls();

      await user.click(screen.getByRole('button', { name: 'Account' }));

      expect(screen.getByText('Notifications')).toBeInTheDocument();
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

    it('shows notification badge count in dropdown when unreadCount > 0', async () => {
      const user = userEvent.setup();
      const notificationStore = createMockNotificationStore({ unreadCount: 3 });
      renderControls({ notificationStore });

      await user.click(screen.getByRole('button', { name: 'Account' }));

      expect(screen.getByText('3')).toBeInTheDocument();
    });

    it('caps notification badge at 99+', async () => {
      const user = userEvent.setup();
      const notificationStore = createMockNotificationStore({ unreadCount: 150 });
      renderControls({ notificationStore });

      await user.click(screen.getByRole('button', { name: 'Account' }));

      expect(screen.getByText('99+')).toBeInTheDocument();
    });

    it('calls markAllAsRead when Notifications clicked', async () => {
      const user = userEvent.setup();
      const notificationStore = createMockNotificationStore({ unreadCount: 3 });
      renderControls({ notificationStore });

      await user.click(screen.getByRole('button', { name: 'Account' }));
      await user.click(screen.getByText('Notifications'));

      expect(notificationStore.markAllAsRead).toHaveBeenCalledTimes(1);
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

    it('shows notification dot in collapsed mode when unread > 0', () => {
      const notificationStore = createMockNotificationStore({ unreadCount: 7 });
      renderControls({ collapsed: true, notificationStore });
      expect(screen.getByTestId('notification-dot')).toBeInTheDocument();
    });

    it('does not show notification dot when unreadCount is 0', () => {
      renderControls({ collapsed: true });
      expect(screen.queryByTestId('notification-dot')).not.toBeInTheDocument();
    });

    it('opens unified dropdown in collapsed mode', async () => {
      const user = userEvent.setup();
      renderControls({ collapsed: true });

      await user.click(screen.getByRole('button', { name: 'Account' }));

      expect(screen.getByText('Notifications')).toBeInTheDocument();
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

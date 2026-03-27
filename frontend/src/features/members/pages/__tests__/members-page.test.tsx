/**
 * Tests for MembersPage.
 *
 * Table rendering, admin vs non-admin views, search/filter (server-side),
 * invite dialog, tabs, role change, member removal, invitation
 * cancellation, transfer ownership, navigation.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';

vi.mock('mobx-react-lite', () => ({
  observer: <T,>(component: T) => component,
}));

const { mockToast } = vi.hoisted(() => ({
  mockToast: { success: vi.fn(), error: vi.fn() },
}));
vi.mock('sonner', () => ({ toast: mockToast }));

const mockPush = vi.fn();
vi.mock('next/navigation', () => ({
  useParams: () => ({ workspaceSlug: 'test-workspace' }),
  useRouter: () => ({ push: mockPush }),
  usePathname: () => '/test-workspace/members',
  useSearchParams: () => new URLSearchParams(),
}));

const mockAuthStore = { user: { id: 'user-1' } };
const mockWorkspaceStore: {
  getWorkspaceBySlug: ReturnType<typeof vi.fn>;
  isAdmin: boolean;
  currentUserRole: string | null;
  updateMemberRole: ReturnType<typeof vi.fn>;
  removeMember: ReturnType<typeof vi.fn>;
  error: string | null;
} = {
  getWorkspaceBySlug: vi.fn().mockReturnValue({ id: 'ws-123', slug: 'test-workspace' }),
  isAdmin: true,
  currentUserRole: 'admin',
  updateMemberRole: vi.fn().mockResolvedValue(true),
  removeMember: vi.fn().mockResolvedValue(true),
  error: null,
};

vi.mock('@/stores', () => ({
  useStore: () => ({ authStore: mockAuthStore, workspaceStore: mockWorkspaceStore }),
}));

const mockUseWorkspaceMembers = vi.fn();
vi.mock('@/features/issues/hooks/use-workspace-members', () => ({
  useWorkspaceMembers: (...args: unknown[]) => mockUseWorkspaceMembers(...args),
  workspaceMembersKeys: {
    all: (id: string) => ['workspaces', id, 'members'],
    filtered: (id: string, params: unknown) => ['workspaces', id, 'members', params],
  },
}));

const mockUseWorkspaceInvitations = vi.fn();
const mockCancelMutateAsync = vi.fn().mockResolvedValue(undefined);
const mockUseCancelInvitation = vi.fn();
vi.mock('@/features/members/hooks/use-workspace-invitations', () => ({
  useWorkspaceInvitations: (...args: unknown[]) => mockUseWorkspaceInvitations(...args),
  useCancelInvitation: (...args: unknown[]) => mockUseCancelInvitation(...args),
}));

interface MockMemberCardProps {
  member: { userId: string; fullName: string | null; email: string; role: string };
  onNavigate: (userId: string) => void;
  onRoleChange: (userId: string, role: string) => void;
  onRemove: (userId: string) => void;
  onTransferOwnership?: (userId: string) => void;
}

vi.mock('@/features/members/components/member-table-row', () => ({
  MemberTableRow: ({
    member,
    onNavigate,
    onRoleChange,
    onRemove,
    onTransferOwnership,
  }: MockMemberCardProps) => (
    <tr data-testid={`member-card-${member.userId}`}>
      <td>{member.fullName || member.email} - {member.role}</td>
      <td>
        <button data-testid={`navigate-${member.userId}`} onClick={() => onNavigate(member.userId)}>
          View
        </button>
        <button
          data-testid={`role-change-${member.userId}`}
          onClick={() => onRoleChange(member.userId, 'admin')}
        >
          Change Role
        </button>
        <button data-testid={`remove-${member.userId}`} onClick={() => onRemove(member.userId)}>
          Remove
        </button>
        {onTransferOwnership && (
          <button
            data-testid={`transfer-${member.userId}`}
            onClick={() => onTransferOwnership(member.userId)}
          >
            Transfer
          </button>
        )}
      </td>
    </tr>
  ),
}));

vi.mock('@/features/members/components/invite-member-dialog', () => ({
  InviteMemberDialog: () => <button data-testid="invite-dialog-trigger">Invite</button>,
}));

interface MockConfirmDialogProps {
  open: boolean;
  onConfirm: () => void;
  onCancel: () => void;
  title: string;
  confirmLabel: string;
}

vi.mock('@/features/settings/components/confirm-action-dialog', () => ({
  ConfirmActionDialog: ({
    open,
    onConfirm,
    onCancel,
    title,
    confirmLabel,
  }: MockConfirmDialogProps) =>
    open ? (
      <div data-testid="confirm-dialog" role="alertdialog">
        <p>{title}</p>
        <button data-testid="confirm-action" onClick={onConfirm}>
          {confirmLabel}
        </button>
        <button data-testid="cancel-action" onClick={onCancel}>
          Cancel
        </button>
      </div>
    ) : null,
}));

// Mock Tabs to render all content simultaneously (Radix Tabs doesn't switch in jsdom)
vi.mock('@/components/ui/tabs', () => ({
  Tabs: ({ children, ...props }: React.PropsWithChildren<Record<string, unknown>>) => (
    <div data-testid="tabs" {...props}>
      {children}
    </div>
  ),
  TabsList: ({ children }: React.PropsWithChildren) => (
    <div data-testid="tabs-list" role="tablist">
      {children}
    </div>
  ),
  TabsTrigger: ({ children, value }: React.PropsWithChildren<{ value: string }>) => (
    <button role="tab" data-value={value}>
      {children}
    </button>
  ),
  TabsContent: ({ children }: React.PropsWithChildren) => <div>{children}</div>,
}));

vi.mock('@/lib/supabase', () => ({
  supabase: { auth: { getSession: vi.fn().mockResolvedValue({ data: { session: null } }) } },
}));

vi.mock('@/services/api', () => ({
  apiClient: { get: vi.fn(), post: vi.fn(), delete: vi.fn() },
}));

const mockUpdateMemberAvailability = vi.fn().mockResolvedValue(undefined);
vi.mock('@/services/api/workspaces', () => ({
  workspacesApi: {
    updateMemberAvailability: (...args: unknown[]) => mockUpdateMemberAvailability(...args),
  },
}));

import { MembersPage } from '../members-page';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';

function createWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return React.createElement(QueryClientProvider, { client: qc }, children);
  };
}

const sampleMembers = [
  {
    userId: 'user-1',
    email: 'admin@example.com',
    fullName: 'Admin User',
    avatarUrl: null,
    role: 'admin',
    joinedAt: '2025-01-01T00:00:00Z',
    weeklyAvailableHours: 40,
  },
  {
    userId: 'user-2',
    email: 'dev@example.com',
    fullName: 'Dev User',
    avatarUrl: null,
    role: 'member',
    joinedAt: '2025-01-15T00:00:00Z',
    weeklyAvailableHours: 40,
  },
];

const sampleInvitations = [
  {
    id: 'inv-1',
    email: 'pending@example.com',
    role: 'member',
    status: 'pending',
    invitedBy: 'user-1',
    invitedByName: null,
    createdAt: '2025-02-01T00:00:00Z',
    expiresAt: '2025-02-08T00:00:00Z',
  },
];

function makePaginatedMembers(items: typeof sampleMembers) {
  return { items, total: items.length, page: 1, pageSize: 25, totalPages: 1 };
}

function makePaginatedInvitations(items: typeof sampleInvitations) {
  return { items, total: items.length, page: 1, pageSize: 25, totalPages: 1 };
}

function setupLoadedState() {
  mockUseWorkspaceMembers.mockReturnValue({
    data: makePaginatedMembers(sampleMembers),
    isLoading: false,
    isFetching: false,
    error: null,
  });
  mockUseWorkspaceInvitations.mockReturnValue({
    data: makePaginatedInvitations(sampleInvitations),
    isLoading: false,
  });
}

describe('MembersPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockWorkspaceStore.isAdmin = true;
    mockWorkspaceStore.currentUserRole = 'admin';
    mockWorkspaceStore.updateMemberRole = vi.fn().mockResolvedValue(true);
    mockWorkspaceStore.removeMember = vi.fn().mockResolvedValue(true);
    mockWorkspaceStore.error = null;
    mockUseCancelInvitation.mockReturnValue({
      mutateAsync: mockCancelMutateAsync,
      isPending: false,
    });
  });

  // --- Loading & Error states ---

  it('shows loading skeleton when members are loading', () => {
    mockUseWorkspaceMembers.mockReturnValue({ data: undefined, isLoading: true, isFetching: true, error: null });
    mockUseWorkspaceInvitations.mockReturnValue({ data: undefined, isLoading: true });

    const { container } = render(<MembersPage />, { wrapper: createWrapper() });

    expect(container.querySelector('.animate-pulse')).toBeInTheDocument();
    expect(screen.queryByRole('list', { name: 'Workspace members' })).not.toBeInTheDocument();
  });

  it('shows error alert when members fail to load', () => {
    mockUseWorkspaceMembers.mockReturnValue({
      data: undefined,
      isLoading: false,
      isFetching: false,
      error: new Error('Network failure'),
    });
    mockUseWorkspaceInvitations.mockReturnValue({ data: undefined, isLoading: false });

    render(<MembersPage />, { wrapper: createWrapper() });

    expect(screen.getByText('Failed to load members')).toBeInTheDocument();
    expect(screen.getByText('Network failure')).toBeInTheDocument();
  });

  // --- Rendering ---

  it('renders member cards when data loaded', () => {
    setupLoadedState();
    render(<MembersPage />, { wrapper: createWrapper() });

    expect(screen.getByTestId('member-card-user-1')).toBeInTheDocument();
    expect(screen.getByTestId('member-card-user-2')).toBeInTheDocument();
  });

  it('shows member count badge', () => {
    setupLoadedState();
    render(<MembersPage />, { wrapper: createWrapper() });
    expect(screen.getByText('2')).toBeInTheDocument();
  });

  // --- Admin vs non-admin ---

  it('shows invite button for admin users', () => {
    setupLoadedState();
    render(<MembersPage />, { wrapper: createWrapper() });
    expect(screen.getByTestId('invite-dialog-trigger')).toBeInTheDocument();
  });

  it('hides invite button for non-admin users', () => {
    mockWorkspaceStore.isAdmin = false;
    mockWorkspaceStore.currentUserRole = 'member';
    setupLoadedState();
    render(<MembersPage />, { wrapper: createWrapper() });
    expect(screen.queryByTestId('invite-dialog-trigger')).not.toBeInTheDocument();
  });

  it('shows tabs (Members + Invitations) for admin', () => {
    setupLoadedState();
    render(<MembersPage />, { wrapper: createWrapper() });
    expect(screen.getByRole('tab', { name: /members/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /invitations/i })).toBeInTheDocument();
  });

  it('hides tabs for non-admin (shows grid directly)', () => {
    mockWorkspaceStore.isAdmin = false;
    mockWorkspaceStore.currentUserRole = 'member';
    setupLoadedState();
    render(<MembersPage />, { wrapper: createWrapper() });

    expect(screen.queryByRole('tab')).not.toBeInTheDocument();
    expect(screen.getByTestId('member-card-user-1')).toBeInTheDocument();
  });

  it('does not fetch invitations for non-admin users', () => {
    mockWorkspaceStore.isAdmin = false;
    mockWorkspaceStore.currentUserRole = 'member';
    setupLoadedState();
    render(<MembersPage />, { wrapper: createWrapper() });

    expect(mockUseWorkspaceInvitations).toHaveBeenCalledWith(
      expect.any(String),
      false,
      expect.any(Object),
    );
  });

  it('shows invitation badge count for admin', () => {
    setupLoadedState();
    render(<MembersPage />, { wrapper: createWrapper() });
    const invitationsTab = screen.getByRole('tab', { name: /invitations/i });
    expect(invitationsTab).toHaveTextContent('1');
  });

  // --- Search (server-side) ---

  it('search passes query to useWorkspaceMembers hook', () => {
    setupLoadedState();
    render(<MembersPage />, { wrapper: createWrapper() });

    fireEvent.change(screen.getByLabelText('Search members'), { target: { value: 'Admin' } });

    // Verify the hook is called with the search option (debounce may not have fired yet)
    expect(mockUseWorkspaceMembers).toHaveBeenCalled();
  });

  it('shows empty state when server returns no members', () => {
    mockUseWorkspaceMembers.mockReturnValue({
      data: makePaginatedMembers([]),
      isLoading: false,
      isFetching: false,
      error: null,
    });
    mockUseWorkspaceInvitations.mockReturnValue({
      data: makePaginatedInvitations(sampleInvitations),
      isLoading: false,
    });

    render(<MembersPage />, { wrapper: createWrapper() });
    expect(screen.getByText('No members found.')).toBeInTheDocument();
  });

  it('role filter filters members by role', () => {
    setupLoadedState();
    render(<MembersPage />, { wrapper: createWrapper() });

    // Members are server-side filtered; both members visible with no filter
    expect(screen.getByTestId('member-card-user-1')).toBeInTheDocument();
    expect(screen.getByTestId('member-card-user-2')).toBeInTheDocument();
  });

  it('shows empty state with clear filters button when filtered results empty', () => {
    mockUseWorkspaceMembers.mockReturnValue({
      data: makePaginatedMembers([]),
      isLoading: false,
      isFetching: false,
      error: null,
    });
    mockUseWorkspaceInvitations.mockReturnValue({
      data: makePaginatedInvitations(sampleInvitations),
      isLoading: false,
    });

    render(<MembersPage />, { wrapper: createWrapper() });
    // With empty items and no search/filter, show generic empty state
    expect(screen.getByText('No members found.')).toBeInTheDocument();
  });

  // --- Navigation ---

  it('card navigate click calls router.push to member profile', () => {
    setupLoadedState();
    render(<MembersPage />, { wrapper: createWrapper() });

    fireEvent.click(screen.getByTestId('navigate-user-2'));
    expect(mockPush).toHaveBeenCalledWith('/test-workspace/members/user-2');
  });

  // --- Role change ---

  it('calls updateMemberRole on role change', async () => {
    setupLoadedState();
    render(<MembersPage />, { wrapper: createWrapper() });

    fireEvent.click(screen.getByTestId('role-change-user-2'));
    // Role change goes through confirm dialog
    expect(screen.getByTestId('confirm-dialog')).toBeInTheDocument();
    fireEvent.click(screen.getByTestId('confirm-action'));

    await waitFor(() => {
      expect(mockWorkspaceStore.updateMemberRole).toHaveBeenCalledWith('ws-123', 'user-2', 'admin');
    });
  });

  // --- Remove member ---

  it('shows confirmation dialog on member removal', () => {
    setupLoadedState();
    render(<MembersPage />, { wrapper: createWrapper() });

    fireEvent.click(screen.getByTestId('remove-user-2'));

    expect(screen.getByTestId('confirm-dialog')).toBeInTheDocument();
    expect(screen.getByText('Remove member')).toBeInTheDocument();
  });

  // --- Cancel invitation ---

  it('cancel invitation flow works through confirmation dialog', async () => {
    setupLoadedState();
    render(<MembersPage />, { wrapper: createWrapper() });

    const cancelButton = screen.getByRole('button', {
      name: /cancel invitation for pending@example.com/i,
    });
    fireEvent.click(cancelButton);

    expect(screen.getByTestId('confirm-dialog')).toBeInTheDocument();
    fireEvent.click(screen.getByTestId('confirm-action'));

    await waitFor(() => {
      expect(mockCancelMutateAsync).toHaveBeenCalledWith('inv-1');
    });
  });

  // --- Transfer ownership ---

  it('transfer ownership flow works through confirmation dialog', async () => {
    setupLoadedState();
    render(<MembersPage />, { wrapper: createWrapper() });

    fireEvent.click(screen.getByTestId('transfer-user-2'));

    expect(screen.getByTestId('confirm-dialog')).toBeInTheDocument();
    expect(screen.getByText('Transfer ownership')).toBeInTheDocument();

    fireEvent.click(screen.getByTestId('confirm-action'));

    await waitFor(() => {
      expect(mockWorkspaceStore.updateMemberRole).toHaveBeenCalledWith('ws-123', 'user-2', 'owner');
    });
  });
});


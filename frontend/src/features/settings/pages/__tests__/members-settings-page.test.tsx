/**
 * Tests for MembersSettingsPage.
 *
 * T028: Member list rendering, admin vs non-admin views,
 * invite dialog presence, pending invitations section,
 * role change, member removal confirmation, invitation cancellation.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';

vi.mock('mobx-react-lite', () => ({
  observer: <T,>(component: T) => component,
}));

const { mockToast } = vi.hoisted(() => ({
  mockToast: { success: vi.fn(), error: vi.fn() },
}));
vi.mock('sonner', () => ({
  toast: mockToast,
}));

vi.mock('next/navigation', () => ({
  useParams: () => ({ workspaceSlug: 'test-workspace' }),
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => '/test-workspace/settings/members',
  useSearchParams: () => new URLSearchParams(),
}));

const mockAuthStore = {
  user: { id: 'user-1' },
};

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
  useStore: () => ({
    authStore: mockAuthStore,
    workspaceStore: mockWorkspaceStore,
  }),
}));

const mockUseWorkspaceMembers = vi.fn();
vi.mock('@/features/issues/hooks/use-workspace-members', () => ({
  useWorkspaceMembers: (...args: unknown[]) => mockUseWorkspaceMembers(...args),
}));

const mockUseWorkspaceInvitations = vi.fn();
const mockCancelMutateAsync = vi.fn().mockResolvedValue(undefined);
const mockUseCancelInvitation = vi.fn();
vi.mock('@/features/settings/hooks/use-workspace-invitations', () => ({
  useWorkspaceInvitations: (...args: unknown[]) => mockUseWorkspaceInvitations(...args),
  useCancelInvitation: (...args: unknown[]) => mockUseCancelInvitation(...args),
}));

interface MockMemberRowProps {
  member: { userId: string; fullName: string | null; email: string; role: string };
  onRoleChange: (userId: string, role: string) => void;
  onRemove: (userId: string) => void;
  onTransferOwnership?: (userId: string) => void;
}

vi.mock('@/features/settings/components/member-row', () => ({
  MemberRow: ({ member, onRoleChange, onRemove, onTransferOwnership }: MockMemberRowProps) => (
    <div data-testid={`member-${member.userId}`} role="listitem">
      {member.fullName || member.email} - {member.role}
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
    </div>
  ),
  ROLE_HIERARCHY: { owner: 0, admin: 1, member: 2, guest: 3 },
}));

vi.mock('@/features/settings/components/invite-member-dialog', () => ({
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

vi.mock('@/lib/supabase', () => ({
  supabase: {
    auth: { getSession: vi.fn().mockResolvedValue({ data: { session: null } }) },
  },
}));

vi.mock('@/services/api', () => ({
  apiClient: { get: vi.fn(), post: vi.fn(), delete: vi.fn() },
}));

import { MembersSettingsPage } from '../members-settings-page';

const sampleMembers = [
  {
    userId: 'user-1',
    email: 'admin@example.com',
    fullName: 'Admin User',
    avatarUrl: null,
    role: 'admin',
    joinedAt: '2025-01-01T00:00:00Z',
  },
  {
    userId: 'user-2',
    email: 'dev@example.com',
    fullName: 'Dev User',
    avatarUrl: null,
    role: 'member',
    joinedAt: '2025-01-15T00:00:00Z',
  },
];

const sampleInvitations = [
  {
    id: 'inv-1',
    email: 'pending@example.com',
    role: 'member',
    status: 'pending',
    invited_by: 'user-1',
    createdAt: '2025-02-01T00:00:00Z',
    expires_at: '2025-02-08T00:00:00Z',
  },
];

function setupLoadedState() {
  mockUseWorkspaceMembers.mockReturnValue({
    data: sampleMembers,
    isLoading: false,
    error: null,
  });
  mockUseWorkspaceInvitations.mockReturnValue({
    data: sampleInvitations,
    isLoading: false,
  });
}

describe('MembersSettingsPage', () => {
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

  it('shows loading skeleton when members are loading', () => {
    mockUseWorkspaceMembers.mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    });
    mockUseWorkspaceInvitations.mockReturnValue({
      data: undefined,
      isLoading: true,
    });

    const { container } = render(<MembersSettingsPage />);

    expect(container.querySelector('.animate-pulse')).toBeInTheDocument();
    expect(screen.queryByText('Members')).not.toBeInTheDocument();
  });

  it('shows error alert when members fail to load', () => {
    mockUseWorkspaceMembers.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error('Network failure'),
    });
    mockUseWorkspaceInvitations.mockReturnValue({
      data: undefined,
      isLoading: false,
    });

    render(<MembersSettingsPage />);

    expect(screen.getByText('Failed to load members')).toBeInTheDocument();
    expect(screen.getByText('Network failure')).toBeInTheDocument();
  });

  it('renders member list when data loaded', () => {
    setupLoadedState();
    render(<MembersSettingsPage />);

    expect(screen.getByText('Members')).toBeInTheDocument();
    expect(screen.getByTestId('member-user-1')).toBeInTheDocument();
    expect(screen.getByTestId('member-user-2')).toBeInTheDocument();
  });

  it('shows member count badge', () => {
    setupLoadedState();
    render(<MembersSettingsPage />);

    expect(screen.getByText('2')).toBeInTheDocument();
  });

  it('shows invite button for admin users', () => {
    setupLoadedState();
    render(<MembersSettingsPage />);

    expect(screen.getByTestId('invite-dialog-trigger')).toBeInTheDocument();
  });

  it('hides invite button for non-admin users', () => {
    mockWorkspaceStore.isAdmin = false;
    mockWorkspaceStore.currentUserRole = 'member';
    setupLoadedState();

    render(<MembersSettingsPage />);

    expect(screen.queryByTestId('invite-dialog-trigger')).not.toBeInTheDocument();
  });

  it('shows pending invitations section for admin', () => {
    setupLoadedState();
    render(<MembersSettingsPage />);

    expect(screen.getByText('Pending Invitations')).toBeInTheDocument();
    expect(screen.getByText('pending@example.com')).toBeInTheDocument();
  });

  it('hides pending invitations section for non-admin', () => {
    mockWorkspaceStore.isAdmin = false;
    mockWorkspaceStore.currentUserRole = 'member';
    setupLoadedState();

    render(<MembersSettingsPage />);

    expect(screen.queryByText('Pending Invitations')).not.toBeInTheDocument();
  });

  it('shows empty state when no members', () => {
    mockUseWorkspaceMembers.mockReturnValue({
      data: [],
      isLoading: false,
      error: null,
    });
    mockUseWorkspaceInvitations.mockReturnValue({
      data: [],
      isLoading: false,
    });

    render(<MembersSettingsPage />);

    expect(screen.getByText('No members found.')).toBeInTheDocument();
  });

  it('shows no pending invitations message', () => {
    mockUseWorkspaceMembers.mockReturnValue({
      data: sampleMembers,
      isLoading: false,
      error: null,
    });
    mockUseWorkspaceInvitations.mockReturnValue({
      data: [],
      isLoading: false,
    });

    render(<MembersSettingsPage />);

    expect(screen.getByText('No pending invitations.')).toBeInTheDocument();
  });

  it('shows manage description for admin users', () => {
    setupLoadedState();
    render(<MembersSettingsPage />);

    expect(screen.getByText('Manage roles and access for workspace members.')).toBeInTheDocument();
  });

  it('shows view-only description for non-admin users', () => {
    mockWorkspaceStore.isAdmin = false;
    mockWorkspaceStore.currentUserRole = 'member';
    setupLoadedState();

    render(<MembersSettingsPage />);

    expect(screen.getByText('View workspace members and their roles.')).toBeInTheDocument();
  });

  // --- Interaction tests ---

  it('calls updateMemberRole on role change', async () => {
    setupLoadedState();
    render(<MembersSettingsPage />);

    fireEvent.click(screen.getByTestId('role-change-user-2'));

    await waitFor(() => {
      expect(mockWorkspaceStore.updateMemberRole).toHaveBeenCalledWith('ws-123', 'user-2', 'admin');
    });
  });

  it('shows confirmation dialog on member removal', () => {
    setupLoadedState();
    render(<MembersSettingsPage />);

    fireEvent.click(screen.getByTestId('remove-user-2'));

    expect(screen.getByTestId('confirm-dialog')).toBeInTheDocument();
    expect(screen.getByText('Remove member')).toBeInTheDocument();
  });

  it('calls removeMember after confirming removal', async () => {
    setupLoadedState();
    render(<MembersSettingsPage />);

    fireEvent.click(screen.getByTestId('remove-user-2'));
    fireEvent.click(screen.getByTestId('confirm-action'));

    await waitFor(() => {
      expect(mockWorkspaceStore.removeMember).toHaveBeenCalledWith('ws-123', 'user-2');
    });
  });

  it('closes confirmation dialog on cancel', () => {
    setupLoadedState();
    render(<MembersSettingsPage />);

    fireEvent.click(screen.getByTestId('remove-user-2'));
    expect(screen.getByTestId('confirm-dialog')).toBeInTheDocument();

    fireEvent.click(screen.getByTestId('cancel-action'));
    expect(screen.queryByTestId('confirm-dialog')).not.toBeInTheDocument();
  });

  it('shows confirmation dialog on invitation cancellation', () => {
    setupLoadedState();
    render(<MembersSettingsPage />);

    const cancelButton = screen.getByRole('button', {
      name: /cancel invitation for pending@example.com/i,
    });
    fireEvent.click(cancelButton);

    expect(screen.getByTestId('confirm-dialog')).toBeInTheDocument();
    // Title and confirm button both say 'Cancel invitation' - verify dialog opened
    expect(screen.getAllByText('Cancel invitation').length).toBeGreaterThanOrEqual(1);
  });

  it('calls cancelInvitation after confirming cancellation', async () => {
    setupLoadedState();
    render(<MembersSettingsPage />);

    const cancelButton = screen.getByRole('button', {
      name: /cancel invitation for pending@example.com/i,
    });
    fireEvent.click(cancelButton);
    fireEvent.click(screen.getByTestId('confirm-action'));

    await waitFor(() => {
      expect(mockCancelMutateAsync).toHaveBeenCalledWith('inv-1');
    });
  });

  it('shows transfer ownership button and confirmation dialog', () => {
    setupLoadedState();
    render(<MembersSettingsPage />);

    const transferButton = screen.getByTestId('transfer-user-2');
    fireEvent.click(transferButton);

    expect(screen.getByTestId('confirm-dialog')).toBeInTheDocument();
    expect(screen.getByText('Transfer ownership')).toBeInTheDocument();
  });

  it('calls updateMemberRole with owner on transfer ownership confirm', async () => {
    setupLoadedState();
    render(<MembersSettingsPage />);

    fireEvent.click(screen.getByTestId('transfer-user-2'));
    fireEvent.click(screen.getByTestId('confirm-action'));

    await waitFor(() => {
      expect(mockWorkspaceStore.updateMemberRole).toHaveBeenCalledWith('ws-123', 'user-2', 'owner');
    });
  });
});

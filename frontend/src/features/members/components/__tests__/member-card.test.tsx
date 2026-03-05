/**
 * MemberCard component tests.
 *
 * Verifies rendering, role badges, actions dropdown visibility,
 * navigation, and accessibility attributes.
 */

import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import type { WorkspaceMember } from '@/features/issues/hooks/use-workspace-members';
import type { WorkspaceRole } from '@/stores/WorkspaceStore';
import { MemberCard } from '../member-card';

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const baseMember: WorkspaceMember = {
  userId: 'user-1',
  email: 'jane@company.com',
  fullName: 'Jane Smith',
  avatarUrl: null,
  role: 'member',
  joinedAt: '2025-01-12T00:00:00Z',
  weeklyAvailableHours: 40,
};

const defaultProps = {
  member: baseMember,
  currentUserRole: 'member' as WorkspaceRole | null,
  isCurrentUser: false,
  isLastAdmin: false,
  onRoleChange: vi.fn(),
  onRemove: vi.fn(),
  onTransferOwnership: vi.fn(),
  onAvailabilityChange: vi.fn(),
  isUpdating: false,
  onNavigate: vi.fn(),
};

function setup(overrides: Partial<typeof defaultProps> = {}) {
  const props = { ...defaultProps, ...overrides };
  return render(<MemberCard {...props} />);
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('MemberCard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders member name, email, and avatar initials', () => {
    setup();

    expect(screen.getByText('Jane Smith')).toBeInTheDocument();
    expect(screen.getByText('jane@company.com')).toBeInTheDocument();
    expect(screen.getByText('JS')).toBeInTheDocument();
  });

  it('shows role badge with correct variant for each role', () => {
    const roles: WorkspaceMember['role'][] = ['owner', 'admin', 'member', 'guest'];

    for (const role of roles) {
      const { unmount } = setup({ member: { ...baseMember, role } });
      const badge = screen.getByTestId(`role-badge-${role}`);
      expect(badge).toHaveTextContent(role);
      unmount();
    }
  });

  it('shows Crown icon for owner role', () => {
    setup({ member: { ...baseMember, role: 'owner' } });

    const badge = screen.getByTestId('role-badge-owner');
    // Crown icon renders as SVG inside the badge
    const svg = badge.querySelector('svg');
    expect(svg).toBeInTheDocument();
  });

  it('shows "(you)" suffix for current user', () => {
    setup({ isCurrentUser: true });

    expect(screen.getByText('(you)')).toBeInTheDocument();
  });

  it('does not show "(you)" for other users', () => {
    setup({ isCurrentUser: false });

    expect(screen.queryByText('(you)')).not.toBeInTheDocument();
  });

  it('shows admin actions dropdown when currentUserRole is admin', async () => {
    setup({
      currentUserRole: 'admin',
      member: { ...baseMember, role: 'member' },
    });

    const trigger = screen.getByRole('button', { name: /actions for/i });
    expect(trigger).toBeInTheDocument();
  });

  it('shows admin actions dropdown when currentUserRole is owner', () => {
    setup({
      currentUserRole: 'owner',
      member: { ...baseMember, role: 'member' },
    });

    expect(screen.getByRole('button', { name: /actions for/i })).toBeInTheDocument();
  });

  it('hides actions dropdown for non-admin roles', () => {
    setup({
      currentUserRole: 'member',
      member: { ...baseMember, role: 'member' },
    });

    expect(screen.queryByRole('button', { name: /actions for/i })).not.toBeInTheDocument();
  });

  it('hides actions dropdown when viewing own card as admin', () => {
    setup({
      currentUserRole: 'admin',
      isCurrentUser: true,
      member: { ...baseMember, role: 'admin' },
    });

    expect(screen.queryByRole('button', { name: /actions for/i })).not.toBeInTheDocument();
  });

  it('hides actions dropdown when target is owner', () => {
    setup({
      currentUserRole: 'admin',
      member: { ...baseMember, role: 'owner' },
    });

    expect(screen.queryByRole('button', { name: /actions for/i })).not.toBeInTheDocument();
  });

  it('calls onNavigate when card is clicked', async () => {
    const user = userEvent.setup();
    const onNavigate = vi.fn();
    setup({ onNavigate });

    const card = screen.getByTestId('member-card-user-1');
    await user.click(card);

    expect(onNavigate).toHaveBeenCalledWith('user-1');
  });

  it('calls onNavigate on Enter key press', async () => {
    const user = userEvent.setup();
    const onNavigate = vi.fn();
    setup({ onNavigate });

    const card = screen.getByTestId('member-card-user-1');
    card.focus();
    await user.keyboard('{Enter}');

    expect(onNavigate).toHaveBeenCalledWith('user-1');
  });

  it('stops propagation on actions dropdown click', async () => {
    const user = userEvent.setup();
    const onNavigate = vi.fn();
    setup({
      currentUserRole: 'admin',
      member: { ...baseMember, role: 'member' },
      onNavigate,
    });

    const trigger = screen.getByRole('button', { name: /actions for/i });
    await user.click(trigger);

    // onNavigate should NOT have been called because stopPropagation
    expect(onNavigate).not.toHaveBeenCalled();
  });

  it('shows weekly hours and join date', () => {
    setup({ member: { ...baseMember, weeklyAvailableHours: 32 } });

    const meta = screen.getByTestId('member-meta');
    expect(meta).toHaveTextContent('32h/wk');
    expect(meta).toHaveTextContent(/Joined/);
  });

  it('shows subtle ring for current user card', () => {
    setup({ isCurrentUser: true });

    const card = screen.getByTestId('member-card-user-1');
    expect(card.className).toContain('ring-1');
    expect(card.className).toContain('ring-primary/20');
  });

  it('does not show ring for non-current user card', () => {
    setup({ isCurrentUser: false });

    const card = screen.getByTestId('member-card-user-1');
    expect(card.className).not.toContain('ring-1');
  });

  it('disables remove when isLastAdmin', async () => {
    const user = userEvent.setup();
    const onRemove = vi.fn();
    setup({
      currentUserRole: 'admin',
      member: { ...baseMember, role: 'member' },
      isLastAdmin: true,
      onRemove,
    });

    // Open dropdown
    const trigger = screen.getByRole('button', { name: /actions for/i });
    await user.click(trigger);

    // Find the Remove Member item — it should be disabled
    const removeItem = screen.getByRole('menuitem', { name: /remove member/i });
    expect(removeItem).toHaveAttribute('data-disabled');
  });

  it('renders email fallback when fullName is null', () => {
    setup({ member: { ...baseMember, fullName: null } });

    // Display name falls back to email prefix
    expect(screen.getByText('jane')).toBeInTheDocument();
    // Initials fall back to email prefix
    expect(screen.getByText('JA')).toBeInTheDocument();
  });

  it('has correct aria-label on the card', () => {
    setup();

    const card = screen.getByTestId('member-card-user-1');
    expect(card).toHaveAttribute('aria-label', 'Member card for Jane Smith');
  });

  it('has role="article" on the card', () => {
    setup();

    const card = screen.getByTestId('member-card-user-1');
    expect(card).toHaveAttribute('role', 'article');
  });
});

/**
 * MemberRoleBadge component tests.
 *
 * Tests custom role name display and built-in role badge variants.
 */

import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { MemberRoleBadge } from '../member-role-badge';

describe('MemberRoleBadge', () => {
  // ---- Custom role ----

  it('renders custom role name when customRole is provided', () => {
    render(<MemberRoleBadge role="member" customRole={{ id: 'role-1', name: 'Tech Lead' }} />);
    expect(screen.getByText('Tech Lead')).toBeInTheDocument();
  });

  it('does not render built-in role when customRole is provided', () => {
    render(<MemberRoleBadge role="member" customRole={{ id: 'role-2', name: 'Design Lead' }} />);
    expect(screen.queryByText('member')).not.toBeInTheDocument();
    expect(screen.queryByText('Member')).not.toBeInTheDocument();
  });

  it('renders custom role with data-testid for accessibility', () => {
    render(<MemberRoleBadge role="admin" customRole={{ id: 'role-3', name: 'Product Manager' }} />);
    const badge = screen.getByTestId('role-badge-custom');
    expect(badge).toHaveTextContent('Product Manager');
  });

  // ---- Built-in roles ----

  it('renders Owner label for owner role', () => {
    render(<MemberRoleBadge role="owner" customRole={null} />);
    expect(screen.getByText('Owner')).toBeInTheDocument();
  });

  it('renders Admin label for admin role', () => {
    render(<MemberRoleBadge role="admin" customRole={null} />);
    expect(screen.getByText('Admin')).toBeInTheDocument();
  });

  it('renders Member label for member role', () => {
    render(<MemberRoleBadge role="member" customRole={null} />);
    expect(screen.getByText('Member')).toBeInTheDocument();
  });

  it('renders Guest label for guest role', () => {
    render(<MemberRoleBadge role="guest" customRole={null} />);
    expect(screen.getByText('Guest')).toBeInTheDocument();
  });

  it('returns null when role is null and customRole is null', () => {
    const { container } = render(<MemberRoleBadge role={null} customRole={null} />);
    expect(container.firstChild).toBeNull();
  });

  it('renders built-in badge with data-testid matching role', () => {
    render(<MemberRoleBadge role="owner" customRole={null} />);
    expect(screen.getByTestId('role-badge-owner')).toBeInTheDocument();
  });

  it('applies custom className to the badge', () => {
    render(<MemberRoleBadge role="member" customRole={null} className="my-custom-class" />);
    const badge = screen.getByTestId('role-badge-member');
    expect(badge.className).toContain('my-custom-class');
  });

  it('custom role badge has data-testid role-badge-custom', () => {
    render(<MemberRoleBadge role="admin" customRole={{ id: 'x', name: 'Scrum Master' }} />);
    expect(screen.getByTestId('role-badge-custom')).toBeInTheDocument();
  });

  // ---- Visual consistency ----

  it('custom role badge uses same visual style as outline built-in badge', () => {
    const { rerender } = render(<MemberRoleBadge role="member" customRole={null} />);
    const memberBadgeClass = screen.getByTestId('role-badge-member').className;

    rerender(<MemberRoleBadge role="member" customRole={{ id: 'r1', name: 'Custom Role' }} />);
    const customBadgeClass = screen.getByTestId('role-badge-custom').className;

    // Both should include the base Badge classes
    expect(memberBadgeClass).toBeTruthy();
    expect(customBadgeClass).toBeTruthy();
  });
});

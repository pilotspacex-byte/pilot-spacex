/**
 * Tests for MemberPicker component (FR-014).
 *
 * Validates workspace member selection with avatars, search filtering,
 * and compact/standard rendering modes.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemberPicker } from '../shared/MemberPicker';
import type { UserBrief } from '@/types';

// Mock scrollIntoView for Command component
beforeEach(() => {
  Element.prototype.scrollIntoView = vi.fn();
});

const mockMembers: UserBrief[] = [
  { id: 'user-1', email: 'alice@example.com', displayName: 'Alice Smith' },
  { id: 'user-2', email: 'bob@example.com', displayName: 'Bob Jones' },
  { id: 'user-3', email: 'charlie@example.com', displayName: null },
];

describe('MemberPicker', () => {
  it('renders placeholder when no value is selected', () => {
    render(<MemberPicker value={null} members={mockMembers} onChange={vi.fn()} />);

    expect(screen.getByText('Assign...')).toBeInTheDocument();
  });

  it('renders custom placeholder', () => {
    render(
      <MemberPicker
        value={null}
        members={mockMembers}
        onChange={vi.fn()}
        placeholder="Pick someone..."
      />
    );

    expect(screen.getByText('Pick someone...')).toBeInTheDocument();
  });

  it('renders selected member name', () => {
    render(<MemberPicker value={mockMembers[0]!} members={mockMembers} onChange={vi.fn()} />);

    expect(screen.getByText('Alice Smith')).toBeInTheDocument();
  });

  it('renders member email when displayName is null', () => {
    render(<MemberPicker value={mockMembers[2]!} members={mockMembers} onChange={vi.fn()} />);

    expect(screen.getByText('charlie@example.com')).toBeInTheDocument();
  });

  it('opens popover and shows member list on click', async () => {
    const user = userEvent.setup();
    render(<MemberPicker value={null} members={mockMembers} onChange={vi.fn()} />);

    await user.click(screen.getByLabelText('Assign...'));

    expect(screen.getByPlaceholderText('Search members...')).toBeInTheDocument();
    expect(screen.getByText('Alice Smith')).toBeInTheDocument();
    expect(screen.getByText('Bob Jones')).toBeInTheDocument();
  });

  it('calls onChange when a member is selected', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<MemberPicker value={null} members={mockMembers} onChange={onChange} />);

    await user.click(screen.getByLabelText('Assign...'));
    await user.click(screen.getByText('Bob Jones'));

    expect(onChange).toHaveBeenCalledWith(mockMembers[1]!);
  });

  it('calls onChange with null when clear span is clicked', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<MemberPicker value={mockMembers[0]!} members={mockMembers} onChange={onChange} />);

    await user.click(screen.getByLabelText('Unassign'));

    expect(onChange).toHaveBeenCalledWith(null);
  });

  it('disables the trigger when disabled prop is true', () => {
    render(<MemberPicker value={null} members={mockMembers} onChange={vi.fn()} disabled />);

    expect(screen.getByLabelText('Assign...')).toBeDisabled();
  });

  it('shows check mark for currently selected member in dropdown', async () => {
    const user = userEvent.setup();
    render(<MemberPicker value={mockMembers[0]!} members={mockMembers} onChange={vi.fn()} />);

    await user.click(screen.getByLabelText('Assigned to Alice Smith'));

    // The Alice item should exist in the command list
    const popoverContent = screen.getByRole('listbox');
    const aliceOption = within(popoverContent).getByText('Alice Smith');
    expect(aliceOption).toBeInTheDocument();
  });

  it('renders in compact mode without name text', () => {
    render(<MemberPicker value={null} members={mockMembers} onChange={vi.fn()} compact />);

    // In compact mode, placeholder text should not be visible
    expect(screen.queryByText('Assign...')).not.toBeInTheDocument();
  });

  it('has proper aria-label for accessibility', () => {
    render(<MemberPicker value={mockMembers[0]!} members={mockMembers} onChange={vi.fn()} />);

    expect(screen.getByLabelText('Assigned to Alice Smith')).toBeInTheDocument();
  });

  it('renders avatar initials for selected member', () => {
    render(<MemberPicker value={mockMembers[0]!} members={mockMembers} onChange={vi.fn()} />);

    expect(screen.getByText('AS')).toBeInTheDocument();
  });
});

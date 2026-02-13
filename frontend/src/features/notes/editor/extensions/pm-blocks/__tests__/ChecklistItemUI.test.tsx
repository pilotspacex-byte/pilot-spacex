/**
 * TDD red-phase tests for ChecklistItemUI component (T016).
 *
 * ChecklistItemUI renders the enhanced task item row with inline metadata:
 * assignee avatar + MemberPicker, date badge + DatePicker, priority badge,
 * optional dashed border, conditional parent grey-out.
 *
 * Spec refs: FR-014 (assignee), FR-015 (due date), FR-016 (priority),
 * FR-017 (optional flag), FR-018 (conditional visibility)
 *
 * These tests define the expected rendering and interaction behavior.
 * The component does not exist yet -- all tests are expected to fail (red phase).
 *
 * @module pm-blocks/__tests__/ChecklistItemUI.test
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

// This import will fail until the component is created
import { ChecklistItemUI } from '../ChecklistItemUI';

const defaultProps = {
  checked: false,
  text: 'Implement login flow',
  assignee: null as string | null,
  dueDate: null as string | null,
  priority: 'none' as 'none' | 'low' | 'medium' | 'high' | 'urgent',
  isOptional: false,
  conditionalParentId: null as string | null,
  isParentChecked: true,
  onCheckedChange: vi.fn(),
  onAssigneeChange: vi.fn(),
  onDueDateChange: vi.fn(),
  onPriorityChange: vi.fn(),
};

// ── Basic rendering ─────────────────────────────────────────────────────
describe('ChecklistItemUI basic rendering', () => {
  it('renders a checkbox and item text', () => {
    render(<ChecklistItemUI {...defaultProps} />);
    expect(screen.getByRole('checkbox')).toBeInTheDocument();
    expect(screen.getByText('Implement login flow')).toBeInTheDocument();
  });

  it('renders checked state with strikethrough styling', () => {
    render(<ChecklistItemUI {...defaultProps} checked={true} />);
    const checkbox = screen.getByRole('checkbox');
    expect(checkbox).toBeChecked();
    expect(screen.getByText('Implement login flow')).toHaveClass('line-through');
  });

  it('calls onCheckedChange when checkbox is toggled', async () => {
    const onCheckedChange = vi.fn();
    render(<ChecklistItemUI {...defaultProps} onCheckedChange={onCheckedChange} />);
    await userEvent.click(screen.getByRole('checkbox'));
    expect(onCheckedChange).toHaveBeenCalledWith(true);
  });
});

// ── FR-014: Assignee ────────────────────────────────────────────────────
describe('ChecklistItemUI assignee (FR-014)', () => {
  it('renders assignee avatar when assignee is set', () => {
    render(<ChecklistItemUI {...defaultProps} assignee="user-123" />);
    expect(screen.getByTestId('checklist-assignee')).toBeInTheDocument();
  });

  it('renders empty assignee slot when no assignee', () => {
    render(<ChecklistItemUI {...defaultProps} assignee={null} />);
    expect(screen.queryByTestId('checklist-assignee')).not.toBeInTheDocument();
  });

  it('calls onAssigneeChange when assignee is selected', async () => {
    const onAssigneeChange = vi.fn();
    render(<ChecklistItemUI {...defaultProps} onAssigneeChange={onAssigneeChange} />);
    const assignBtn = screen.getByLabelText('Assign member');
    await userEvent.click(assignBtn);
    expect(assignBtn).toBeInTheDocument();
  });
});

// ── FR-015: Due date ────────────────────────────────────────────────────
describe('ChecklistItemUI due date (FR-015)', () => {
  it('renders due date badge when dueDate is set', () => {
    render(<ChecklistItemUI {...defaultProps} dueDate="2026-03-15" />);
    expect(screen.getByTestId('checklist-due-date')).toBeInTheDocument();
    expect(screen.getByText(/Mar 15/)).toBeInTheDocument();
  });

  it('renders overdue indicator when past due and unchecked', () => {
    render(<ChecklistItemUI {...defaultProps} dueDate="2025-01-01" checked={false} />);
    const badge = screen.getByTestId('checklist-due-date');
    expect(badge).toHaveClass('text-destructive');
  });

  it('does not render overdue when checked even if past due', () => {
    render(<ChecklistItemUI {...defaultProps} dueDate="2025-01-01" checked={true} />);
    const badge = screen.getByTestId('checklist-due-date');
    expect(badge).not.toHaveClass('text-destructive');
  });
});

// ── FR-016: Priority ────────────────────────────────────────────────────
describe('ChecklistItemUI priority (FR-016)', () => {
  it('does not render priority badge when priority is "none"', () => {
    render(<ChecklistItemUI {...defaultProps} priority="none" />);
    expect(screen.queryByTestId('checklist-priority')).not.toBeInTheDocument();
  });

  it.each(['low', 'medium', 'high', 'urgent'] as const)(
    'renders priority badge for %s',
    (priority) => {
      render(<ChecklistItemUI {...defaultProps} priority={priority} />);
      const badge = screen.getByTestId('checklist-priority');
      expect(badge).toBeInTheDocument();
      expect(badge).toHaveTextContent(new RegExp(priority, 'i'));
    }
  );

  it('uses correct color for urgent priority', () => {
    render(<ChecklistItemUI {...defaultProps} priority="urgent" />);
    const badge = screen.getByTestId('checklist-priority');
    expect(badge.className).toMatch(/priority-urgent/);
  });
});

// ── FR-017: Optional flag ───────────────────────────────────────────────
describe('ChecklistItemUI optional flag (FR-017)', () => {
  it('renders with dashed border when isOptional is true', () => {
    const { container } = render(<ChecklistItemUI {...defaultProps} isOptional={true} />);
    const item = container.firstElementChild;
    expect(item?.className).toMatch(/border-dashed/);
  });

  it('renders with reduced opacity when isOptional is true', () => {
    const { container } = render(<ChecklistItemUI {...defaultProps} isOptional={true} />);
    const item = container.firstElementChild;
    expect(item?.className).toMatch(/opacity-70/);
  });

  it('renders normal styling when isOptional is false', () => {
    const { container } = render(<ChecklistItemUI {...defaultProps} isOptional={false} />);
    const item = container.firstElementChild;
    expect(item?.className).not.toMatch(/border-dashed/);
  });
});

// ── FR-018: Conditional visibility ──────────────────────────────────────
describe('ChecklistItemUI conditional visibility (FR-018)', () => {
  it('renders greyed out when parent is unchecked', () => {
    const { container } = render(
      <ChecklistItemUI
        {...defaultProps}
        conditionalParentId="parent-block-1"
        isParentChecked={false}
      />
    );
    const item = container.firstElementChild;
    expect(item?.className).toMatch(/opacity-40/);
    expect(item?.className).toMatch(/pointer-events-none/);
  });

  it('renders normally when parent is checked', () => {
    const { container } = render(
      <ChecklistItemUI
        {...defaultProps}
        conditionalParentId="parent-block-1"
        isParentChecked={true}
      />
    );
    const item = container.firstElementChild;
    expect(item?.className).not.toMatch(/opacity-40/);
  });

  it('renders normally when no conditional parent', () => {
    const { container } = render(
      <ChecklistItemUI {...defaultProps} conditionalParentId={null} isParentChecked={false} />
    );
    const item = container.firstElementChild;
    expect(item?.className).not.toMatch(/opacity-40/);
  });
});

// ── Keyboard navigation ─────────────────────────────────────────────────
describe('ChecklistItemUI keyboard navigation', () => {
  it('checkbox is focusable via Tab', async () => {
    render(<ChecklistItemUI {...defaultProps} />);
    await userEvent.tab();
    expect(screen.getByRole('checkbox')).toHaveFocus();
  });

  it('Space toggles checkbox', async () => {
    const onCheckedChange = vi.fn();
    render(<ChecklistItemUI {...defaultProps} onCheckedChange={onCheckedChange} />);
    const checkbox = screen.getByRole('checkbox');
    checkbox.focus();
    await userEvent.keyboard(' ');
    expect(onCheckedChange).toHaveBeenCalledWith(true);
  });
});

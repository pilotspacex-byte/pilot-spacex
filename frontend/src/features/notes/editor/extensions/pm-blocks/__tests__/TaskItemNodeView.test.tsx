/* eslint-disable @typescript-eslint/no-explicit-any */
/**
 * Tests for TaskItemNodeView — TipTap React NodeView for enhanced TaskItem.
 *
 * TaskItemNodeView renders task items with inline metadata badges:
 * - FR-014: Assignee avatar
 * - FR-015: Due date badge with overdue detection
 * - FR-016: Priority badge with color variants
 * - FR-017: Optional flag (dashed border + reduced opacity)
 * - FR-018: Conditional visibility (greyed out when parent unchecked)
 *
 * Since TaskItemNodeView requires TipTap NodeViewProps (node, updateAttributes,
 * editor), we mock @tiptap/react and create minimal editor state stubs.
 *
 * @module pm-blocks/__tests__/TaskItemNodeView.test
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { ReactNode } from 'react';

// Mock TipTap's react package
vi.mock('@tiptap/react', () => ({
  NodeViewWrapper: ({
    children,
    className,
    ...props
  }: {
    children: ReactNode;
    className?: string;
  } & Record<string, unknown>) => (
    <li data-testid="task-item-wrapper" className={className} {...props}>
      {children}
    </li>
  ),
  NodeViewContent: ({ className, ...props }: { className?: string } & Record<string, unknown>) => (
    <div data-testid="task-item-content" className={className} {...props} />
  ),
}));

import { TaskItemNodeView } from '../TaskItemNodeView';

/* ── Mock NodeViewProps factory ─────────────────────────────────────── */

interface TaskItemAttrs {
  checked?: boolean;
  assignee?: string | null;
  dueDate?: string | null;
  priority?: string;
  isOptional?: boolean;
  conditionalParentId?: string | null;
  id?: string;
}

/**
 * Create a doc descendants mock that simulates finding parent task items
 * in the ProseMirror doc tree for conditional visibility (FR-018).
 */
function createDocDescendantsMock(parentItems: Array<{ id: string; checked: boolean }>) {
  return (callback: (node: Record<string, unknown>) => boolean | undefined) => {
    for (const item of parentItems) {
      const result = callback({
        type: { name: 'taskItem' },
        attrs: { id: item.id, checked: item.checked },
      });
      if (result === false) break;
    }
  };
}

function createMockProps(
  attrs: TaskItemAttrs = {},
  options: { isEditable?: boolean; parentItems?: Array<{ id: string; checked: boolean }> } = {}
) {
  const defaultAttrs: Required<TaskItemAttrs> = {
    checked: false,
    assignee: null,
    dueDate: null,
    priority: 'none',
    isOptional: false,
    conditionalParentId: null,
    id: 'task-1',
  };

  const mergedAttrs = { ...defaultAttrs, ...attrs };
  const isEditable = options.isEditable ?? true;
  const parentItems = options.parentItems ?? [];

  return {
    node: {
      attrs: mergedAttrs,
      type: { name: 'taskItem' },
    },
    updateAttributes: vi.fn(),
    editor: {
      isEditable,
      state: {
        doc: {
          descendants: createDocDescendantsMock(parentItems),
        },
      },
    },
    getPos: vi.fn(() => 0),
    decorations: [],
    selected: false,
    extension: {} as never,
    HTMLAttributes: {},
    deleteNode: vi.fn(),
  } as unknown as Parameters<typeof TaskItemNodeView>[0];
}

/* ── Basic rendering ────────────────────────────────────────────────── */

describe('TaskItemNodeView basic rendering', () => {
  it('renders checkbox and content area', () => {
    const props = createMockProps();
    render(<TaskItemNodeView {...(props as any)} />);

    expect(screen.getByRole('checkbox')).toBeInTheDocument();
    expect(screen.getByTestId('task-item-content')).toBeInTheDocument();
  });

  it('renders unchecked state by default', () => {
    const props = createMockProps({ checked: false });
    render(<TaskItemNodeView {...(props as any)} />);
    expect(screen.getByRole('checkbox')).not.toBeChecked();
  });

  it('renders checked state', () => {
    const props = createMockProps({ checked: true });
    render(<TaskItemNodeView {...(props as any)} />);
    expect(screen.getByRole('checkbox')).toBeChecked();
  });

  it('calls updateAttributes when checkbox is toggled', async () => {
    const user = userEvent.setup();
    const props = createMockProps({ checked: false });
    render(<TaskItemNodeView {...(props as any)} />);

    await user.click(screen.getByRole('checkbox'));
    expect(props.updateAttributes).toHaveBeenCalledWith({ checked: true });
  });

  it('does not toggle checkbox when editor is read-only', async () => {
    const props = createMockProps({ checked: false }, { isEditable: false });
    render(<TaskItemNodeView {...(props as any)} />);

    const checkbox = screen.getByRole('checkbox');
    expect(checkbox).toBeDisabled();
  });
});

/* ── FR-014: Assignee ───────────────────────────────────────────────── */

describe('TaskItemNodeView assignee (FR-014)', () => {
  it('renders assignee indicator when assignee is set', () => {
    const props = createMockProps({ assignee: 'user-123' });
    render(<TaskItemNodeView {...(props as any)} />);
    expect(screen.getByTestId('checklist-assignee')).toBeInTheDocument();
  });

  it('does not render assignee indicator when assignee is null', () => {
    const props = createMockProps({ assignee: null });
    render(<TaskItemNodeView {...(props as any)} />);
    expect(screen.queryByTestId('checklist-assignee')).not.toBeInTheDocument();
  });

  it('renders assign button when no assignee and editor is editable', () => {
    const props = createMockProps({ assignee: null }, { isEditable: true });
    render(<TaskItemNodeView {...(props as any)} />);
    expect(screen.getByLabelText('Assign member')).toBeInTheDocument();
  });

  it('does not render assign button when read-only', () => {
    const props = createMockProps({ assignee: null }, { isEditable: false });
    render(<TaskItemNodeView {...(props as any)} />);
    expect(screen.queryByLabelText('Assign member')).not.toBeInTheDocument();
  });
});

/* ── FR-015: Due date ───────────────────────────────────────────────── */

describe('TaskItemNodeView due date (FR-015)', () => {
  it('renders due date badge when dueDate is set', () => {
    const props = createMockProps({ dueDate: '2026-03-15' });
    render(<TaskItemNodeView {...(props as any)} />);
    expect(screen.getByTestId('checklist-due-date')).toBeInTheDocument();
    expect(screen.getByText(/Mar 15/)).toBeInTheDocument();
  });

  it('does not render due date badge when dueDate is null', () => {
    const props = createMockProps({ dueDate: null });
    render(<TaskItemNodeView {...(props as any)} />);
    expect(screen.queryByTestId('checklist-due-date')).not.toBeInTheDocument();
  });

  it('shows overdue indicator when past due and unchecked', () => {
    const props = createMockProps({ dueDate: '2020-01-01', checked: false });
    render(<TaskItemNodeView {...(props as any)} />);
    const badge = screen.getByTestId('checklist-due-date');
    expect(badge.className).toContain('text-destructive');
  });

  it('does not show overdue when checked even if past due', () => {
    const props = createMockProps({ dueDate: '2020-01-01', checked: true });
    render(<TaskItemNodeView {...(props as any)} />);
    const badge = screen.getByTestId('checklist-due-date');
    expect(badge.className).not.toContain('text-destructive');
  });
});

/* ── FR-016: Priority badge ─────────────────────────────────────────── */

describe('TaskItemNodeView priority (FR-016)', () => {
  it('does not render priority badge when priority is "none"', () => {
    const props = createMockProps({ priority: 'none' });
    render(<TaskItemNodeView {...(props as any)} />);
    expect(screen.queryByTestId('checklist-priority')).not.toBeInTheDocument();
  });

  it.each(['low', 'medium', 'high', 'urgent'] as const)(
    'renders priority badge for %s',
    (priority) => {
      const props = createMockProps({ priority });
      render(<TaskItemNodeView {...(props as any)} />);
      const badge = screen.getByTestId('checklist-priority');
      expect(badge).toBeInTheDocument();
    }
  );

  it('renders correct label text for urgent priority', () => {
    const props = createMockProps({ priority: 'urgent' });
    render(<TaskItemNodeView {...(props as any)} />);
    expect(screen.getByTestId('checklist-priority')).toHaveTextContent('Urgent');
  });

  it('renders correct label text for high priority', () => {
    const props = createMockProps({ priority: 'high' });
    render(<TaskItemNodeView {...(props as any)} />);
    expect(screen.getByTestId('checklist-priority')).toHaveTextContent('High');
  });

  it('applies priority-specific CSS class', () => {
    const props = createMockProps({ priority: 'urgent' });
    render(<TaskItemNodeView {...(props as any)} />);
    const badge = screen.getByTestId('checklist-priority');
    expect(badge.className).toContain('priority-urgent');
  });
});

/* ── FR-017: Optional flag ──────────────────────────────────────────── */

describe('TaskItemNodeView optional flag (FR-017)', () => {
  it('applies optional styling when isOptional is true', () => {
    const props = createMockProps({ isOptional: true });
    render(<TaskItemNodeView {...(props as any)} />);
    const wrapper = screen.getByTestId('task-item-wrapper');
    expect(wrapper.className).toContain('border-dashed');
    expect(wrapper.className).toContain('opacity-70');
  });

  it('does not apply optional styling when isOptional is false', () => {
    const props = createMockProps({ isOptional: false });
    render(<TaskItemNodeView {...(props as any)} />);
    const wrapper = screen.getByTestId('task-item-wrapper');
    expect(wrapper.className).not.toContain('border-dashed');
  });

  it('renders "Optional" label when isOptional is true', () => {
    const props = createMockProps({ isOptional: true });
    render(<TaskItemNodeView {...(props as any)} />);
    expect(screen.getByText('Optional')).toBeInTheDocument();
  });

  it('does not render "Optional" label when isOptional is false', () => {
    const props = createMockProps({ isOptional: false });
    render(<TaskItemNodeView {...(props as any)} />);
    expect(screen.queryByText('Optional')).not.toBeInTheDocument();
  });
});

/* ── FR-018: Conditional visibility ─────────────────────────────────── */

describe('TaskItemNodeView conditional visibility (FR-018)', () => {
  it('disables checkbox when conditional parent is unchecked', () => {
    const props = createMockProps(
      { conditionalParentId: 'parent-1' },
      { parentItems: [{ id: 'parent-1', checked: false }] }
    );
    render(<TaskItemNodeView {...(props as any)} />);
    expect(screen.getByRole('checkbox')).toBeDisabled();
  });

  it('enables checkbox when conditional parent is checked', () => {
    const props = createMockProps(
      { conditionalParentId: 'parent-1' },
      {
        isEditable: true,
        parentItems: [{ id: 'parent-1', checked: true }],
      }
    );
    render(<TaskItemNodeView {...(props as any)} />);
    expect(screen.getByRole('checkbox')).not.toBeDisabled();
  });

  it('applies disabled styling when parent is unchecked', () => {
    const props = createMockProps(
      { conditionalParentId: 'parent-1' },
      { parentItems: [{ id: 'parent-1', checked: false }] }
    );
    render(<TaskItemNodeView {...(props as any)} />);
    const wrapper = screen.getByTestId('task-item-wrapper');
    expect(wrapper.className).toContain('opacity-40');
    expect(wrapper.className).toContain('pointer-events-none');
  });

  it('does not apply disabled styling when no conditional parent', () => {
    const props = createMockProps({ conditionalParentId: null });
    render(<TaskItemNodeView {...(props as any)} />);
    const wrapper = screen.getByTestId('task-item-wrapper');
    expect(wrapper.className).not.toContain('opacity-40');
    expect(wrapper.className).not.toContain('pointer-events-none');
  });

  it('does not apply disabled styling when parent is checked', () => {
    const props = createMockProps(
      { conditionalParentId: 'parent-1' },
      { parentItems: [{ id: 'parent-1', checked: true }] }
    );
    render(<TaskItemNodeView {...(props as any)} />);
    const wrapper = screen.getByTestId('task-item-wrapper');
    expect(wrapper.className).not.toContain('opacity-40');
  });

  it('handles missing parent gracefully (parent not in doc)', () => {
    const props = createMockProps(
      { conditionalParentId: 'nonexistent-parent' },
      { parentItems: [] }
    );
    render(<TaskItemNodeView {...(props as any)} />);
    // When parent not found, parentChecked stays false -> disabled
    expect(screen.getByRole('checkbox')).toBeDisabled();
  });
});

/* ── Data attribute rendering ───────────────────────────────────────── */

describe('TaskItemNodeView data attributes', () => {
  it('sets data-checked="true" when checked', () => {
    const props = createMockProps({ checked: true });
    render(<TaskItemNodeView {...(props as any)} />);
    expect(screen.getByTestId('task-item-wrapper')).toHaveAttribute('data-checked', 'true');
  });

  it('sets data-checked="false" when unchecked', () => {
    const props = createMockProps({ checked: false });
    render(<TaskItemNodeView {...(props as any)} />);
    expect(screen.getByTestId('task-item-wrapper')).toHaveAttribute('data-checked', 'false');
  });

  it('sets data-type="taskItem"', () => {
    const props = createMockProps();
    render(<TaskItemNodeView {...(props as any)} />);
    expect(screen.getByTestId('task-item-wrapper')).toHaveAttribute('data-type', 'taskItem');
  });
});

/* ── Keyboard accessibility ─────────────────────────────────────────── */

describe('TaskItemNodeView keyboard accessibility', () => {
  it('checkbox has aria-checked attribute', () => {
    const props = createMockProps({ checked: true });
    render(<TaskItemNodeView {...(props as any)} />);
    expect(screen.getByRole('checkbox')).toHaveAttribute('aria-checked', 'true');
  });

  it('checkbox is focusable via Tab', async () => {
    const user = userEvent.setup();
    const props = createMockProps();
    render(<TaskItemNodeView {...(props as any)} />);
    await user.tab();
    expect(screen.getByRole('checkbox')).toHaveFocus();
  });
});

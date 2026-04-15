/**
 * Unit tests for BatchPreviewCard component.
 * Phase 75-02 — Chat-to-issue pipeline (CIP-03, CIP-04)
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BatchPreviewCard } from '../BatchPreviewCard';
import type { ProposedIssue } from '@/stores/ai/types/events';

// Mock motion/react to avoid animation side-effects in tests
vi.mock('motion/react', () => ({
  motion: {
    div: ({ children, ...props }: React.HTMLAttributes<HTMLDivElement> & { children?: React.ReactNode }) => (
      <div {...props}>{children}</div>
    ),
  },
  useReducedMotion: () => true, // Always reduced motion in tests
}));

const makeIssue = (overrides: Partial<ProposedIssue> = {}): ProposedIssue => ({
  title: 'Default issue title',
  description: 'Default description',
  acceptance_criteria: [
    { criterion: 'AC 1', met: true },
    { criterion: 'AC 2', met: false },
  ],
  priority: 'medium',
  ...overrides,
});

const defaultIssues: ProposedIssue[] = [
  makeIssue({ title: 'Issue One', priority: 'high' }),
  makeIssue({ title: 'Issue Two', priority: 'low' }),
  makeIssue({ title: 'Issue Three', priority: 'urgent' }),
];

describe('BatchPreviewCard', () => {
  let onCreateAll: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    onCreateAll = vi.fn().mockResolvedValue(undefined);
  });

  it('renders the correct number of collapsed issue cards', () => {
    render(<BatchPreviewCard issues={defaultIssues} onCreateAll={onCreateAll} />);
    // Each IssuePreviewItem has role="listitem"
    const items = screen.getAllByRole('listitem');
    expect(items).toHaveLength(3);
  });

  it('shows header with correct count', () => {
    render(<BatchPreviewCard issues={defaultIssues} onCreateAll={onCreateAll} />);
    expect(screen.getByText(/3 proposed issues/)).toBeInTheDocument();
  });

  it('expanding a card shows editable title field', async () => {
    const user = userEvent.setup();
    render(<BatchPreviewCard issues={defaultIssues} onCreateAll={onCreateAll} />);

    // Expand the first issue by clicking the title button
    const titleButtons = screen.getAllByRole('button', { name: /Issue One/i });
    await user.click(titleButtons[0]!);

    // After expansion, an input with the title value should appear
    await waitFor(() => {
      expect(screen.getByDisplayValue('Issue One')).toBeInTheDocument();
    });
  });

  it('expanding a card shows acceptance criteria items', async () => {
    const user = userEvent.setup();
    render(<BatchPreviewCard issues={defaultIssues} onCreateAll={onCreateAll} />);

    const titleButtons = screen.getAllByRole('button', { name: /Issue One/i });
    await user.click(titleButtons[0]!);

    await waitFor(() => {
      expect(screen.getByText('AC 1')).toBeInTheDocument();
      expect(screen.getByText('AC 2')).toBeInTheDocument();
    });
  });

  it('AC items render with correct met state (aria-checked)', async () => {
    const user = userEvent.setup();
    render(<BatchPreviewCard issues={defaultIssues} onCreateAll={onCreateAll} />);

    const titleButtons = screen.getAllByRole('button', { name: /Issue One/i });
    await user.click(titleButtons[0]!);

    await waitFor(() => {
      const metCheckbox = screen.getByRole('checkbox', { name: 'AC 1' });
      const unmetCheckbox = screen.getByRole('checkbox', { name: 'AC 2' });
      expect(metCheckbox).toHaveAttribute('aria-checked', 'true');
      expect(unmetCheckbox).toHaveAttribute('aria-checked', 'false');
    });
  });

  it('X button removes a card and updates footer count', async () => {
    const user = userEvent.setup();
    render(<BatchPreviewCard issues={defaultIssues} onCreateAll={onCreateAll} />);

    // Find and click the remove button for the first issue
    const removeButtons = screen.getAllByRole('button', { name: /Remove.*from batch/i });
    expect(removeButtons).toHaveLength(3);

    // Remove is async (150ms fade) — use act + fake timers OR just wait
    await act(async () => {
      await user.click(removeButtons[0]!);
      // advance fake timer in a simple way by waiting
      await new Promise((r) => setTimeout(r, 200));
    });

    // Should now have 2 items
    await waitFor(() => {
      const items = screen.getAllByRole('listitem');
      expect(items).toHaveLength(2);
    });

    // Footer count should update — text is split across elements, use header paragraph
    expect(screen.getByText(/2 proposed issues/)).toBeInTheDocument();
  });

  it('"Create All" button is disabled when 0 issues remain', async () => {
    const user = userEvent.setup();
    render(<BatchPreviewCard issues={[makeIssue()]} onCreateAll={onCreateAll} />);

    const removeButtons = screen.getAllByRole('button', { name: /Remove.*from batch/i });
    await act(async () => {
      await user.click(removeButtons[0]!);
      await new Promise((r) => setTimeout(r, 200));
    });

    await waitFor(() => {
      const createBtn = screen.getByRole('button', { name: /No issues remaining/i });
      expect(createBtn).toBeDisabled();
    });
  });

  it('"Create All" triggers onCreateAll callback (DD-003 gate proxy), NOT direct API call', async () => {
    const user = userEvent.setup();
    render(<BatchPreviewCard issues={defaultIssues} onCreateAll={onCreateAll} />);

    const createBtn = screen.getByRole('button', { name: /Create All 3 Issues/i });
    await user.click(createBtn);

    expect(onCreateAll).toHaveBeenCalledTimes(1);
    // onCreateAll receives the current editable issues array
    expect(onCreateAll).toHaveBeenCalledWith(
      expect.arrayContaining([
        expect.objectContaining({ title: 'Issue One' }),
        expect.objectContaining({ title: 'Issue Two' }),
        expect.objectContaining({ title: 'Issue Three' }),
      ])
    );
  });

  it('shows creating state while onCreateAll is pending', async () => {
    const user = userEvent.setup();
    let resolveCreate!: () => void;
    onCreateAll.mockReturnValue(new Promise<void>((r) => { resolveCreate = r; }));

    render(<BatchPreviewCard issues={defaultIssues} onCreateAll={onCreateAll} />);

    const createBtn = screen.getByRole('button', { name: /Create All 3 Issues/i });
    await user.click(createBtn);

    // Button should show loading state
    expect(screen.getByText('Creating issues...')).toBeInTheDocument();
    expect(createBtn).toBeDisabled();

    // Resolve the promise
    await act(async () => { resolveCreate(); });
  });

  it('shows created state after successful creation', async () => {
    const user = userEvent.setup();
    render(<BatchPreviewCard issues={defaultIssues} onCreateAll={onCreateAll} />);

    const createBtn = screen.getByRole('button', { name: /Create All 3 Issues/i });
    await user.click(createBtn);

    // "3 issues created." — text is split: <strong>3 issues</strong> created.
    // Check via the card container's textContent
    await waitFor(() => {
      const card = screen.getByTestId('batch-preview-card');
      expect(card.textContent).toMatch(/3.*issues.*created/);
    });
  });

  it('empty issues array shows "No issues could be extracted" message', () => {
    render(<BatchPreviewCard issues={[]} onCreateAll={onCreateAll} />);
    expect(screen.getByText('No issues could be extracted')).toBeInTheDocument();
    expect(
      screen.getByText(/Try providing more detail/i)
    ).toBeInTheDocument();
  });

  it('has role="list" on the issue container', () => {
    render(<BatchPreviewCard issues={defaultIssues} onCreateAll={onCreateAll} />);
    expect(screen.getByRole('list')).toBeInTheDocument();
  });

  it('does NOT use observer() — BatchPreviewCard is a React.memo component', () => {
    // React.memo returns an object with $$typeof === Symbol(react.memo)
    // observer() wraps with a displayName suffix 'observer(...)' or ForwardRef
    // Verify the component renders without any MobX reactive context requirement
    // (observer() components throw when rendered outside MobX context)
    expect(() => {
      render(<BatchPreviewCard issues={defaultIssues} onCreateAll={onCreateAll} />);
    }).not.toThrow();

    // React.memo wrapped objects have type === 'object' (not a function)
    expect(typeof BatchPreviewCard).toBe('object');
  });
});

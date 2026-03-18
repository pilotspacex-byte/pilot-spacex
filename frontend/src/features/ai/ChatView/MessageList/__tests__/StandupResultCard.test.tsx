/**
 * StandupResultCard tests (T017).
 *
 * Tests rendering of three standup sections, empty state display,
 * clipboard copy behavior, and "Copied!" state transition.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, act, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { StructuredResultCard } from '../StructuredResultCard';
import { formatStandupForClipboard } from '../StructuredResultCard';

// ── Fixtures ─────────────────────────────────────────────────────────────

const fullStandupData = {
  yesterday: [
    { identifier: 'PS-42', title: 'Fix login timeout' },
    { identifier: 'PS-43', title: 'Update API docs' },
  ],
  today: [{ identifier: 'PS-44', title: 'Implement search filter' }],
  blockers: [
    {
      identifier: 'PS-45',
      title: 'Database migration blocked',
      reason: 'Waiting for DBA approval',
    },
  ],
  period: 'Feb 19-20, 2026',
};

const emptyStandupData = {
  yesterday: [],
  today: [],
  blockers: [],
  period: 'Feb 19-20, 2026',
};

const partialStandupData = {
  yesterday: [{ identifier: 'PS-10', title: 'Completed task' }],
  today: [],
  blockers: [],
  period: 'Feb 20, 2026',
};

function renderStandupCard(data: Record<string, unknown> = fullStandupData) {
  return render(<StructuredResultCard schemaType="standup_result" data={data} />);
}

// ── Tests ────────────────────────────────────────────────────────────────

describe('StandupResultCard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers({ shouldAdvanceTime: true });

    // Ensure clipboard exists for tests that use it
    if (!navigator.clipboard) {
      Object.defineProperty(navigator, 'clipboard', {
        value: { writeText: async () => {} },
        writable: true,
        configurable: true,
      });
    }
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('renders the card with region role and label', () => {
    renderStandupCard();

    const region = screen.getByRole('region', { name: 'Structured result: standup_result' });
    expect(region).toBeInTheDocument();
  });

  it('renders "Daily Standup" header with period', () => {
    renderStandupCard();

    expect(screen.getByText('Daily Standup')).toBeInTheDocument();
    expect(screen.getByText('Feb 19-20, 2026')).toBeInTheDocument();
  });

  it('renders all three section headings', () => {
    renderStandupCard();

    expect(screen.getByText('Yesterday (Completed)')).toBeInTheDocument();
    expect(screen.getByText('Today (In Progress)')).toBeInTheDocument();
    expect(screen.getByText('Blockers')).toBeInTheDocument();
  });

  it('renders issue identifiers in each section', () => {
    renderStandupCard();

    expect(screen.getByText('PS-42')).toBeInTheDocument();
    expect(screen.getByText('PS-43')).toBeInTheDocument();
    expect(screen.getByText('PS-44')).toBeInTheDocument();
    expect(screen.getByText('PS-45')).toBeInTheDocument();
  });

  it('renders issue titles in each section', () => {
    renderStandupCard();

    expect(screen.getByText('Fix login timeout')).toBeInTheDocument();
    expect(screen.getByText('Update API docs')).toBeInTheDocument();
    expect(screen.getByText('Implement search filter')).toBeInTheDocument();
    expect(screen.getByText('Database migration blocked')).toBeInTheDocument();
  });

  it('renders blocker reason text', () => {
    renderStandupCard();

    expect(screen.getByText(/Waiting for DBA approval/)).toBeInTheDocument();
  });

  it('shows "(No items)" for empty sections', () => {
    renderStandupCard(emptyStandupData);

    const noItems = screen.getAllByText('(No items)');
    expect(noItems).toHaveLength(3);
  });

  it('shows "(No items)" only for empty sections when partially filled', () => {
    renderStandupCard(partialStandupData);

    // Yesterday has content
    expect(screen.getByText('PS-10')).toBeInTheDocument();
    // Today and Blockers are empty
    const noItems = screen.getAllByText('(No items)');
    expect(noItems).toHaveLength(2);
  });

  it('renders Copy button with correct aria-label', () => {
    renderStandupCard();

    const copyBtn = screen.getByRole('button', { name: 'Copy standup to clipboard' });
    expect(copyBtn).toBeInTheDocument();
    expect(screen.getByText('Copy')).toBeInTheDocument();
  });

  it('invokes clipboard.writeText and transitions to Copied state on click', async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    renderStandupCard();

    const copyBtn = screen.getByRole('button', { name: 'Copy standup to clipboard' });
    await user.click(copyBtn);

    // The component calls navigator.clipboard.writeText then sets "Copied!" state
    await waitFor(() => {
      expect(screen.getByText('Copied!')).toBeInTheDocument();
    });

    // Verify the "Copied" aria label is set
    expect(screen.getByRole('button', { name: 'Copied to clipboard' })).toBeInTheDocument();
  });

  it('shows "Copied!" state after clicking copy, then resets', async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    renderStandupCard();

    const copyBtn = screen.getByRole('button', { name: 'Copy standup to clipboard' });
    await user.click(copyBtn);

    // Should show "Copied!" and updated aria-label
    await waitFor(() => {
      expect(screen.getByText('Copied!')).toBeInTheDocument();
    });
    expect(screen.getByRole('button', { name: 'Copied to clipboard' })).toBeInTheDocument();

    // After 2 seconds, should reset back to "Copy"
    act(() => {
      vi.advanceTimersByTime(2100);
    });

    await waitFor(() => {
      expect(screen.getByText('Copy')).toBeInTheDocument();
    });
    expect(screen.getByRole('button', { name: 'Copy standup to clipboard' })).toBeInTheDocument();
  });

  it('handles malformed data gracefully without crashing', () => {
    // yesterday is a string instead of array, today is missing, blockers is number
    const malformedData = {
      yesterday: 'not an array',
      blockers: 42,
      period: 123, // number instead of string
    };

    renderStandupCard(malformedData);

    // Should render all three sections with "(No items)" since arrays are invalid
    const noItems = screen.getAllByText('(No items)');
    expect(noItems).toHaveLength(3);

    // Period should not render since it's not a string
    expect(screen.queryByText('123')).not.toBeInTheDocument();
  });
});

// ── formatStandupForClipboard ────────────────────────────────────────────────

describe('formatStandupForClipboard', () => {
  it('formats full standup data as markdown', () => {
    const result = formatStandupForClipboard({
      yesterday: [{ identifier: 'PS-1', title: 'Did thing' }],
      today: [{ identifier: 'PS-2', title: 'Do thing' }],
      blockers: [{ identifier: 'PS-3', title: 'Stuck', reason: 'Need help' }],
      period: 'Feb 20, 2026',
    });

    expect(result).toContain('**Daily Standup** — Feb 20, 2026');
    expect(result).toContain('**Yesterday (Completed)**');
    expect(result).toContain('- PS-1: Did thing');
    expect(result).toContain('**Today (In Progress)**');
    expect(result).toContain('- PS-2: Do thing');
    expect(result).toContain('**Blockers**');
    expect(result).toContain('- PS-3: Stuck — Need help');
  });

  it('shows "(No items)" for empty sections', () => {
    const result = formatStandupForClipboard({
      yesterday: [],
      today: [],
      blockers: [],
      period: 'Feb 20, 2026',
    });

    const noItemsCount = (result.match(/\(No items\)/g) ?? []).length;
    expect(noItemsCount).toBe(3);
  });

  it('omits reason suffix when blocker has no reason', () => {
    const result = formatStandupForClipboard({
      yesterday: [],
      today: [],
      blockers: [{ identifier: 'PS-5', title: 'Blocked thing' }],
      period: 'Feb 20, 2026',
    });

    expect(result).toContain('- PS-5: Blocked thing');
    // The blocker line should NOT have a reason suffix (em-dash exists in header only)
    expect(result).not.toContain('PS-5: Blocked thing —');
  });
});

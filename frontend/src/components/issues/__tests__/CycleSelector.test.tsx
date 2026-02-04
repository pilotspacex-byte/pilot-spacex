/**
 * CycleSelector component tests (T023).
 *
 * Verifies null/selected cycle rendering, dropdown options,
 * onChange callbacks, disabled state, and date range display.
 */

import { render, screen, fireEvent, within } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { CycleSelector } from '../CycleSelector';
import type { Cycle } from '@/types';

// ---------------------------------------------------------------------------
// Mocks - Radix DropdownMenu
// ---------------------------------------------------------------------------

vi.mock('@/components/ui/dropdown-menu', async () => {
  return {
    DropdownMenuTrigger: ({ children }: { children: React.ReactNode }) => (
      <div data-testid="dropdown-trigger">{children}</div>
    ),
    DropdownMenuContent: ({ children }: { children: React.ReactNode }) => (
      <div data-testid="dropdown-content">{children}</div>
    ),
    DropdownMenuItem: ({
      children,
      onClick,
      className,
    }: {
      children: React.ReactNode;
      onClick?: () => void;
      className?: string;
    }) => (
      <button data-testid="dropdown-item" onClick={onClick} className={className}>
        {children}
      </button>
    ),
    DropdownMenuSeparator: () => <hr data-testid="dropdown-separator" />,
  };
});

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

function createCycle(overrides?: Partial<Cycle>): Cycle {
  return {
    id: 'cycle-1',
    workspaceId: 'ws-1',
    name: 'Sprint 1',
    status: 'active',
    sequence: 1,
    createdAt: '2025-01-01',
    updatedAt: '2025-01-01',
    project: { id: 'proj-1', name: 'Project', identifier: 'PS' },
    issueCount: 5,
    ...overrides,
  };
}

const mockCycles: Cycle[] = [
  createCycle({
    id: 'cycle-1',
    name: 'Sprint 1',
    status: 'active',
    startDate: '2025-01-15',
    endDate: '2025-01-29',
  }),
  createCycle({
    id: 'cycle-2',
    name: 'Sprint 2',
    status: 'planned',
    startDate: '2025-02-01',
    endDate: '2025-02-14',
  }),
  createCycle({ id: 'cycle-3', name: 'Sprint 3', status: 'draft' }),
];

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('CycleSelector', () => {
  const defaultOnChange = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders "No cycle" when value is null', () => {
    render(<CycleSelector value={null} onChange={defaultOnChange} cycles={mockCycles} />);

    const trigger = screen.getByTestId('dropdown-trigger');
    expect(within(trigger).getByText('No cycle')).toBeInTheDocument();
  });

  it('renders cycle name when value matches a cycle', () => {
    render(<CycleSelector value="cycle-1" onChange={defaultOnChange} cycles={mockCycles} />);

    const trigger = screen.getByTestId('dropdown-trigger');
    expect(within(trigger).getByText('Sprint 1')).toBeInTheDocument();
  });

  it('shows all cycles in dropdown plus "No cycle" option', () => {
    render(<CycleSelector value={null} onChange={defaultOnChange} cycles={mockCycles} />);

    const content = screen.getByTestId('dropdown-content');
    const items = within(content).getAllByTestId('dropdown-item');

    // 1 "No cycle" + 3 cycles = 4
    expect(items).toHaveLength(4);
    expect(within(content).getByText('Sprint 1')).toBeInTheDocument();
    expect(within(content).getByText('Sprint 2')).toBeInTheDocument();
    expect(within(content).getByText('Sprint 3')).toBeInTheDocument();
  });

  it('calls onChange with cycle id', () => {
    render(<CycleSelector value={null} onChange={defaultOnChange} cycles={mockCycles} />);

    const content = screen.getByTestId('dropdown-content');
    const items = within(content).getAllByTestId('dropdown-item');

    // Click Sprint 1 (index 1 after "No cycle")
    fireEvent.click(items.at(1)!);
    expect(defaultOnChange).toHaveBeenCalledWith('cycle-1');
  });

  it('calls onChange with null for "No cycle" option', () => {
    render(<CycleSelector value="cycle-1" onChange={defaultOnChange} cycles={mockCycles} />);

    const content = screen.getByTestId('dropdown-content');
    const items = within(content).getAllByTestId('dropdown-item');

    // First item is "No cycle"
    fireEvent.click(items.at(0)!);
    expect(defaultOnChange).toHaveBeenCalledWith(null);
  });

  it('disabled state prevents interaction', () => {
    render(<CycleSelector value={null} onChange={defaultOnChange} cycles={mockCycles} disabled />);

    const trigger = screen.getByTestId('dropdown-trigger');
    const button = within(trigger).getByRole('button');
    expect(button).toBeDisabled();
  });

  it('shows date range for cycles with dates', () => {
    render(<CycleSelector value={null} onChange={defaultOnChange} cycles={mockCycles} />);

    const content = screen.getByTestId('dropdown-content');
    // Sprint 1 has startDate: 2025-01-15, endDate: 2025-01-29
    expect(within(content).getByText(/Jan 15/)).toBeInTheDocument();
    expect(within(content).getByText(/Jan 29/)).toBeInTheDocument();
  });

  it('shows date range on trigger when cycle with dates is selected', () => {
    render(<CycleSelector value="cycle-1" onChange={defaultOnChange} cycles={mockCycles} />);

    const trigger = screen.getByTestId('dropdown-trigger');
    expect(within(trigger).getByText(/Jan 15/)).toBeInTheDocument();
  });

  it('shows "Active" badge for active cycles', () => {
    render(<CycleSelector value={null} onChange={defaultOnChange} cycles={mockCycles} />);

    const content = screen.getByTestId('dropdown-content');
    expect(within(content).getByText('Active')).toBeInTheDocument();
  });

  it('renders separator between "No cycle" and cycle list', () => {
    render(<CycleSelector value={null} onChange={defaultOnChange} cycles={mockCycles} />);

    expect(screen.getByTestId('dropdown-separator')).toBeInTheDocument();
  });

  it('does not render separator when cycles list is empty', () => {
    render(<CycleSelector value={null} onChange={defaultOnChange} cycles={[]} />);

    expect(screen.queryByTestId('dropdown-separator')).not.toBeInTheDocument();
  });
});

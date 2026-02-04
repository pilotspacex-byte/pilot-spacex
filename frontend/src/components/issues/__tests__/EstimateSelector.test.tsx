/**
 * EstimateSelector component tests (T024).
 *
 * Verifies undefined/set value rendering, Fibonacci presets,
 * onChange callbacks, clear button, disabled state, aria-pressed.
 */

import { render, screen, fireEvent, within } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { EstimateSelector } from '../EstimateSelector';

// ---------------------------------------------------------------------------
// Mocks - Radix Popover
// ---------------------------------------------------------------------------

vi.mock('@/components/ui/popover', () => {
  return {
    Popover: ({
      children,
    }: {
      children: React.ReactNode;
      open?: boolean;
      onOpenChange?: (open: boolean) => void;
    }) => {
      // Always render children for testing
      return <div data-testid="popover-root">{children}</div>;
    },
    PopoverTrigger: ({ children }: { children: React.ReactNode }) => (
      <div data-testid="popover-trigger">{children}</div>
    ),
    PopoverContent: ({ children }: { children: React.ReactNode }) => (
      <div data-testid="popover-content">{children}</div>
    ),
  };
});

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('EstimateSelector', () => {
  const defaultOnChange = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders "Estimate" when value is undefined', () => {
    render(<EstimateSelector value={undefined} onChange={defaultOnChange} />);

    const trigger = screen.getByTestId('popover-trigger');
    expect(within(trigger).getByText('Estimate')).toBeInTheDocument();
  });

  it('renders point value when set (singular)', () => {
    render(<EstimateSelector value={1} onChange={defaultOnChange} />);

    const trigger = screen.getByTestId('popover-trigger');
    expect(within(trigger).getByText('1 pt')).toBeInTheDocument();
  });

  it('renders point value when set (plural)', () => {
    render(<EstimateSelector value={5} onChange={defaultOnChange} />);

    const trigger = screen.getByTestId('popover-trigger');
    expect(within(trigger).getByText('5 pts')).toBeInTheDocument();
  });

  it('shows Fibonacci presets (1, 2, 3, 5, 8, 13)', () => {
    render(<EstimateSelector value={undefined} onChange={defaultOnChange} />);

    const content = screen.getByTestId('popover-content');
    [1, 2, 3, 5, 8, 13].forEach((num) => {
      expect(within(content).getByText(String(num))).toBeInTheDocument();
    });
  });

  it('calls onChange with selected value', () => {
    render(<EstimateSelector value={undefined} onChange={defaultOnChange} />);

    const content = screen.getByTestId('popover-content');
    fireEvent.click(within(content).getByText('5'));
    expect(defaultOnChange).toHaveBeenCalledWith(5);
  });

  it('calls onChange with each Fibonacci value correctly', () => {
    render(<EstimateSelector value={undefined} onChange={defaultOnChange} />);

    const content = screen.getByTestId('popover-content');
    const expected = [1, 2, 3, 5, 8, 13];

    expected.forEach((num) => {
      fireEvent.click(within(content).getByText(String(num)));
    });

    expected.forEach((num, idx) => {
      expect(defaultOnChange).toHaveBeenNthCalledWith(idx + 1, num);
    });
  });

  it('shows clear button when value is set and calls onChange with undefined', () => {
    render(<EstimateSelector value={3} onChange={defaultOnChange} />);

    const clearButton = screen.getByRole('button', { name: 'Clear estimate' });
    expect(clearButton).toBeInTheDocument();

    fireEvent.click(clearButton);
    expect(defaultOnChange).toHaveBeenCalledWith(undefined);
  });

  it('does not show clear button when value is undefined', () => {
    render(<EstimateSelector value={undefined} onChange={defaultOnChange} />);

    expect(screen.queryByRole('button', { name: 'Clear estimate' })).not.toBeInTheDocument();
  });

  it('disabled state prevents interaction', () => {
    render(<EstimateSelector value={undefined} onChange={defaultOnChange} disabled />);

    const trigger = screen.getByTestId('popover-trigger');
    const button = within(trigger).getByRole('button');
    expect(button).toBeDisabled();
  });

  it('aria-pressed on selected preset', () => {
    render(<EstimateSelector value={5} onChange={defaultOnChange} />);

    const content = screen.getByTestId('popover-content');
    const fiveButton = within(content).getByRole('button', { name: '5 points' });
    expect(fiveButton).toHaveAttribute('aria-pressed', 'true');

    const threeButton = within(content).getByRole('button', { name: '3 points' });
    expect(threeButton).toHaveAttribute('aria-pressed', 'false');
  });

  it('trigger has correct aria-label when value is set', () => {
    render(<EstimateSelector value={3} onChange={defaultOnChange} />);

    const trigger = screen.getByTestId('popover-trigger');
    const button = within(trigger).getByRole('button');
    expect(button).toHaveAttribute('aria-label', 'Estimate: 3 points');
  });

  it('trigger has correct aria-label when value is undefined', () => {
    render(<EstimateSelector value={undefined} onChange={defaultOnChange} />);

    const trigger = screen.getByTestId('popover-trigger');
    const button = within(trigger).getByRole('button');
    expect(button).toHaveAttribute('aria-label', 'Set estimate');
  });

  it('shows "Story Points" heading in content', () => {
    render(<EstimateSelector value={undefined} onChange={defaultOnChange} />);

    expect(screen.getByText('Story Points')).toBeInTheDocument();
  });
});

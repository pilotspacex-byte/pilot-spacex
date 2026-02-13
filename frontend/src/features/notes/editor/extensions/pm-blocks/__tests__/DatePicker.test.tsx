/**
 * Tests for DatePicker component (FR-015).
 *
 * Validates date selection, overdue indicators, compact mode,
 * and clear functionality.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { DatePicker } from '../shared/DatePicker';

beforeEach(() => {
  Element.prototype.scrollIntoView = vi.fn();
});

describe('DatePicker', () => {
  describe('rendering', () => {
    it('renders placeholder when no date is selected', () => {
      render(<DatePicker value={null} onChange={vi.fn()} />);
      expect(screen.getByText('Set date...')).toBeInTheDocument();
    });

    it('renders custom placeholder', () => {
      render(<DatePicker value={null} onChange={vi.fn()} placeholder="Due date..." />);
      expect(screen.getByText('Due date...')).toBeInTheDocument();
    });

    it('renders formatted date when value is provided', () => {
      vi.useFakeTimers();
      vi.setSystemTime(new Date('2026-02-11T12:00:00'));
      const date = new Date('2026-03-15');
      render(<DatePicker value={date} onChange={vi.fn()} />);
      expect(screen.getByText('Mar 15')).toBeInTheDocument();
      vi.useRealTimers();
    });

    it('shows year for dates in a different year', () => {
      vi.useFakeTimers();
      vi.setSystemTime(new Date('2026-02-11T12:00:00'));
      const date = new Date('2027-06-01');
      render(<DatePicker value={date} onChange={vi.fn()} />);
      expect(screen.getByText('Jun 1, 2027')).toBeInTheDocument();
      vi.useRealTimers();
    });

    it('disables the trigger when disabled prop is true', () => {
      render(<DatePicker value={null} onChange={vi.fn()} disabled />);
      expect(screen.getByRole('button')).toBeDisabled();
    });

    it('renders in compact mode without placeholder text', () => {
      render(<DatePicker value={null} onChange={vi.fn()} compact />);
      expect(screen.queryByText('Set date...')).not.toBeInTheDocument();
    });
  });

  describe('overdue logic', () => {
    beforeEach(() => {
      vi.useFakeTimers();
      vi.setSystemTime(new Date('2026-02-11T12:00:00'));
    });

    afterEach(() => {
      vi.useRealTimers();
    });

    it('shows overdue badge when date is in the past and not completed', () => {
      const pastDate = new Date('2026-02-01');
      render(<DatePicker value={pastDate} onChange={vi.fn()} isCompleted={false} />);
      expect(screen.getByText('Overdue')).toBeInTheDocument();
    });

    it('does not show overdue badge when date is in the past but item is completed', () => {
      const pastDate = new Date('2026-02-01');
      render(<DatePicker value={pastDate} onChange={vi.fn()} isCompleted={true} />);
      expect(screen.queryByText('Overdue')).not.toBeInTheDocument();
    });

    it('does not show overdue badge for future dates', () => {
      const futureDate = new Date('2026-12-25');
      render(<DatePicker value={futureDate} onChange={vi.fn()} />);
      expect(screen.queryByText('Overdue')).not.toBeInTheDocument();
    });

    it('does not show overdue badge for today', () => {
      const today = new Date('2026-02-11');
      render(<DatePicker value={today} onChange={vi.fn()} />);
      expect(screen.queryByText('Overdue')).not.toBeInTheDocument();
    });
  });

  describe('interactions', () => {
    it('opens calendar popup on click', async () => {
      const user = userEvent.setup();
      render(<DatePicker value={null} onChange={vi.fn()} />);

      await user.click(screen.getByRole('button'));

      expect(screen.getByRole('grid')).toBeInTheDocument();
    });

    it('calls onChange with null when clear is clicked', async () => {
      const onChange = vi.fn();
      const user = userEvent.setup();
      const date = new Date('2026-03-15');
      render(<DatePicker value={date} onChange={onChange} />);

      await user.click(screen.getByLabelText('Clear date'));

      expect(onChange).toHaveBeenCalledWith(null);
    });
  });

  describe('accessibility', () => {
    it('has proper aria-label with date', () => {
      vi.useFakeTimers();
      vi.setSystemTime(new Date('2026-02-11T12:00:00'));
      const date = new Date('2026-03-15');
      render(<DatePicker value={date} onChange={vi.fn()} />);
      expect(screen.getByLabelText('Due date: Mar 15')).toBeInTheDocument();
      vi.useRealTimers();
    });

    it('has proper aria-label with placeholder when no date', () => {
      render(<DatePicker value={null} onChange={vi.fn()} />);
      expect(screen.getByLabelText('Set date...')).toBeInTheDocument();
    });
  });
});

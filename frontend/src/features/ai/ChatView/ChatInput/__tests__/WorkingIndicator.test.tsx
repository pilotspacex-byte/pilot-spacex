/**
 * Unit tests for WorkingIndicator component.
 *
 * Covers rendering states, accessibility attributes,
 * idiom rotation via setInterval, and reset on visibility toggle.
 *
 * @module features/ai/ChatView/ChatInput/__tests__/WorkingIndicator.test
 */

import { render, screen, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { WorkingIndicator } from '../WorkingIndicator';

/** Idiom list mirrored from component source for assertion accuracy. */
const IDIOMS = [
  'Thinking deeply\u2026',
  'Analyzing context\u2026',
  'Crafting a response\u2026',
  'Reading your notes\u2026',
  'Connecting the dots\u2026',
  'Processing request\u2026',
  'Working on it\u2026',
  'Almost there\u2026',
] as const;

const ROTATION_INTERVAL_MS = 3000;

describe('WorkingIndicator', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  // ── Visibility ──────────────────────────────────────────────────

  it('renders null when isVisible is false', () => {
    const { container } = render(<WorkingIndicator isVisible={false} />);
    expect(container.innerHTML).toBe('');
  });

  it('renders spinner and idiom text when isVisible is true', () => {
    render(<WorkingIndicator isVisible={true} />);

    const status = screen.getByRole('status');
    expect(status).toBeInTheDocument();
    expect(status).toHaveTextContent(IDIOMS[0]!);
  });

  // ── Accessibility ───────────────────────────────────────────────

  it('has role="status" for screen reader announcements', () => {
    render(<WorkingIndicator isVisible={true} />);
    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('has aria-live="polite" to announce idiom changes non-intrusively', () => {
    render(<WorkingIndicator isVisible={true} />);
    expect(screen.getByRole('status')).toHaveAttribute('aria-live', 'polite');
  });

  it('hides the spinner icon from assistive technology via aria-hidden', () => {
    render(<WorkingIndicator isVisible={true} />);

    const svg = screen.getByRole('status').querySelector('svg');
    expect(svg).not.toBeNull();
    expect(svg!.getAttribute('aria-hidden')).toBe('true');
  });

  // ── Idiom rotation ─────────────────────────────────────────────

  it('rotates to the next idiom after one interval', () => {
    render(<WorkingIndicator isVisible={true} />);

    expect(screen.getByRole('status')).toHaveTextContent(IDIOMS[0]!);

    act(() => {
      vi.advanceTimersByTime(ROTATION_INTERVAL_MS);
    });

    expect(screen.getByRole('status')).toHaveTextContent(IDIOMS[1]!);
  });

  it('cycles through multiple idioms sequentially', () => {
    render(<WorkingIndicator isVisible={true} />);

    for (let i = 1; i < IDIOMS.length; i++) {
      act(() => {
        vi.advanceTimersByTime(ROTATION_INTERVAL_MS);
      });
      expect(screen.getByRole('status')).toHaveTextContent(IDIOMS[i]!);
    }
  });

  it('wraps back to the first idiom after exhausting the list', () => {
    render(<WorkingIndicator isVisible={true} />);

    // Advance through all idioms
    act(() => {
      vi.advanceTimersByTime(ROTATION_INTERVAL_MS * IDIOMS.length);
    });

    expect(screen.getByRole('status')).toHaveTextContent(IDIOMS[0]!);
  });

  it('does not rotate when isVisible is false', () => {
    const { container } = render(<WorkingIndicator isVisible={false} />);

    act(() => {
      vi.advanceTimersByTime(ROTATION_INTERVAL_MS * 5);
    });

    // Still renders nothing -- no interval side effects
    expect(container.innerHTML).toBe('');
  });

  // ── Visibility toggle ──────────────────────────────────────────

  it('restarts interval when visibility toggles off then on', () => {
    const { rerender } = render(<WorkingIndicator isVisible={true} />);

    // Advance past first idiom
    act(() => {
      vi.advanceTimersByTime(ROTATION_INTERVAL_MS * 3);
    });
    expect(screen.getByRole('status')).toHaveTextContent(IDIOMS[3]!);

    // Toggle off — renders nothing
    rerender(<WorkingIndicator isVisible={false} />);

    // Toggle back on — interval restarts, continues from current index
    rerender(<WorkingIndicator isVisible={true} />);

    // Advance one interval — should move to next idiom
    act(() => {
      vi.advanceTimersByTime(ROTATION_INTERVAL_MS);
    });
    expect(screen.getByRole('status')).toHaveTextContent(IDIOMS[4]!);
  });

  it('clears old interval on toggle off so no stale updates occur', () => {
    const { rerender } = render(<WorkingIndicator isVisible={true} />);

    // Advance to second idiom
    act(() => {
      vi.advanceTimersByTime(ROTATION_INTERVAL_MS);
    });
    expect(screen.getByRole('status')).toHaveTextContent(IDIOMS[1]!);

    // Toggle off — interval should be cleared
    rerender(<WorkingIndicator isVisible={false} />);

    // Advance time while hidden — should NOT cause any state update
    act(() => {
      vi.advanceTimersByTime(ROTATION_INTERVAL_MS * 5);
    });

    // Toggle back on — still at last known idiom (1), interval restarts
    rerender(<WorkingIndicator isVisible={true} />);
    expect(screen.getByRole('status')).toHaveTextContent(IDIOMS[1]!);
  });
});

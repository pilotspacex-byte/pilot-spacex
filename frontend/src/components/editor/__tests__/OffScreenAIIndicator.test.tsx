/**
 * Unit tests for OffScreenAIIndicator component.
 *
 * Covers visibility toggling, callback wiring, and ARIA accessibility.
 *
 * @module components/editor/__tests__/OffScreenAIIndicator.test
 */

import React from 'react';
import { describe, it, expect, vi, beforeAll } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { OffScreenAIIndicator } from '../OffScreenAIIndicator';

// ---------------------------------------------------------------------------
// Environment
// ---------------------------------------------------------------------------
beforeAll(() => {
  process.env.NEXT_PUBLIC_SUPABASE_URL = 'http://test.supabase.co';
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY = 'test-key';
});

// ---------------------------------------------------------------------------
// Mock motion/react to avoid animation side-effects in tests
// ---------------------------------------------------------------------------
vi.mock('motion/react', () => ({
  AnimatePresence: ({ children }: { children: React.ReactNode }) => children,
  motion: {
    div: ({ children, ...props }: React.PropsWithChildren<Record<string, unknown>>) => {
      const { initial, animate, exit, transition, ...domProps } = props;
      return <div {...domProps}>{children}</div>;
    },
  },
}));

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------
describe('OffScreenAIIndicator', () => {
  it('renders nothing when isVisible is false', () => {
    const { container } = render(
      <OffScreenAIIndicator isVisible={false} onScrollToBlock={vi.fn()} onDismiss={vi.fn()} />
    );

    expect(container.querySelector('[role="status"]')).toBeNull();
    expect(screen.queryByText('AI is editing below')).toBeNull();
  });

  it('renders pill with "AI is editing below" text when isVisible is true', () => {
    render(
      <OffScreenAIIndicator isVisible={true} onScrollToBlock={vi.fn()} onDismiss={vi.fn()} />
    );

    expect(screen.getByText('AI is editing below')).toBeInTheDocument();
  });

  it('calls onScrollToBlock when the text button is clicked', () => {
    const onScrollToBlock = vi.fn();
    render(
      <OffScreenAIIndicator
        isVisible={true}
        onScrollToBlock={onScrollToBlock}
        onDismiss={vi.fn()}
      />
    );

    fireEvent.click(screen.getByText('AI is editing below'));
    expect(onScrollToBlock).toHaveBeenCalledTimes(1);
  });

  it('calls onDismiss when the X button is clicked', () => {
    const onDismiss = vi.fn();
    render(
      <OffScreenAIIndicator isVisible={true} onScrollToBlock={vi.fn()} onDismiss={onDismiss} />
    );

    fireEvent.click(screen.getByText('Dismiss'));
    expect(onDismiss).toHaveBeenCalledTimes(1);
  });

  it('has role="status" and aria-live="polite" for accessibility', () => {
    render(
      <OffScreenAIIndicator isVisible={true} onScrollToBlock={vi.fn()} onDismiss={vi.fn()} />
    );

    const statusRegion = screen.getByRole('status');
    expect(statusRegion).toBeInTheDocument();
    expect(statusRegion.getAttribute('aria-live')).toBe('polite');
  });

  it('renders "AI is editing above" and has top-4 positioning when direction="above"', () => {
    const { container } = render(
      <OffScreenAIIndicator
        isVisible={true}
        direction="above"
        onScrollToBlock={vi.fn()}
        onDismiss={vi.fn()}
      />
    );

    expect(screen.getByText('AI is editing above')).toBeInTheDocument();
    expect(screen.queryByText('AI is editing below')).toBeNull();

    const statusRegion = container.querySelector('[role="status"]');
    expect(statusRegion?.className).toContain('top-4');
    expect(statusRegion?.className).not.toContain('bottom-4');
  });

  it('uses orange warning colors and ai-offscreen-indicator class', () => {
    const { container } = render(
      <OffScreenAIIndicator isVisible={true} onScrollToBlock={vi.fn()} onDismiss={vi.fn()} />
    );

    const pill = container.querySelector('.ai-offscreen-indicator');
    expect(pill).not.toBeNull();

    // The pill should have warning/orange color classes, not ai-blue
    expect(pill?.className).toContain('bg-warning/10');
    expect(pill?.className).toContain('border-warning/30');
  });

  it('renders "AI is editing below" and has bottom-4 positioning when direction="below"', () => {
    const { container } = render(
      <OffScreenAIIndicator
        isVisible={true}
        direction="below"
        onScrollToBlock={vi.fn()}
        onDismiss={vi.fn()}
      />
    );

    expect(screen.getByText('AI is editing below')).toBeInTheDocument();
    expect(screen.queryByText('AI is editing above')).toBeNull();

    const statusRegion = container.querySelector('[role="status"]');
    expect(statusRegion?.className).toContain('bottom-4');
    expect(statusRegion?.className).not.toContain('top-4');
  });

  it('defaults to "AI is editing below" when no direction prop is provided', () => {
    const { container } = render(
      <OffScreenAIIndicator
        isVisible={true}
        onScrollToBlock={vi.fn()}
        onDismiss={vi.fn()}
      />
    );

    expect(screen.getByText('AI is editing below')).toBeInTheDocument();

    const statusRegion = container.querySelector('[role="status"]');
    expect(statusRegion?.className).toContain('bottom-4');
  });
});

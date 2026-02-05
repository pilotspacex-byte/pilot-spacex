/**
 * Unit tests for ThinkingBlock component (Claude.ai minimal style).
 *
 * Tests minimal inline toggle styling, streaming/completed states,
 * auto-collapse behavior, expand/collapse toggle, streaming cursor,
 * scrollable overflow, empty content, and interrupted state.
 *
 * @module features/ai/ChatView/MessageList/__tests__/ThinkingBlock
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, act } from '@testing-library/react';

// Mock useElapsedTime to control timer output
vi.mock('@/hooks/useElapsedTime', () => ({
  useElapsedTime: vi.fn(() => '3.2s'),
}));

// Mock lucide-react icons
vi.mock('lucide-react', () => ({
  Check: (props: Record<string, unknown>) => <span data-testid="check-icon" {...props} />,
  ChevronDown: (props: Record<string, unknown>) => (
    <span data-testid="chevron-down-icon" {...props} />
  ),
  ChevronUp: (props: Record<string, unknown>) => <span data-testid="chevron-up-icon" {...props} />,
  Loader2: (props: Record<string, unknown>) => <span data-testid="loader2-icon" {...props} />,
  ShieldAlert: (props: Record<string, unknown>) => (
    <span data-testid="shield-alert-icon" {...props} />
  ),
}));

import { useElapsedTime } from '@/hooks/useElapsedTime';
import { ThinkingBlock } from '../ThinkingBlock';

const mockUseElapsedTime = vi.mocked(useElapsedTime);

describe('ThinkingBlock', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
    mockUseElapsedTime.mockReturnValue('3.2s');
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  // ========================================
  // Minimal inline styling
  // ========================================

  it('renders minimal inline style without frosted glass', () => {
    render(
      <ThinkingBlock
        content="Analyzing the problem..."
        isStreaming
        thinkingStartedAt={Date.now()}
      />
    );

    // Should have aria-label on button, not a region role anymore
    const button = screen.getByRole('button', { name: 'Agent reasoning' });
    expect(button).toBeInTheDocument();

    // Should NOT have frosted glass styling
    expect(button.className).not.toContain('glass-subtle');
    expect(button.className).not.toContain('bg-ai-muted');
    expect(button.className).not.toContain('border-l-ai');

    // Should have minimal styling
    expect(button.className).toContain('text-muted-foreground');
  });

  // ========================================
  // Streaming state header
  // ========================================

  it('shows Loader2 icon and "Thinking..." label when streaming', () => {
    render(<ThinkingBlock content="Working on it..." isStreaming thinkingStartedAt={Date.now()} />);

    expect(screen.getByTestId('loader2-icon')).toBeInTheDocument();
    expect(screen.getByText('Thinking...')).toBeInTheDocument();
  });

  // ========================================
  // Elapsed time counter
  // ========================================

  it('displays elapsed time counter from useElapsedTime during streaming', () => {
    mockUseElapsedTime.mockReturnValue('4.5s');

    render(<ThinkingBlock content="Thinking..." isStreaming thinkingStartedAt={Date.now()} />);

    expect(screen.getByText('4.5s')).toBeInTheDocument();
    expect(mockUseElapsedTime).toHaveBeenCalledWith(expect.any(Number), true);
  });

  // ========================================
  // Auto-collapse on streaming transition
  // ========================================

  it('auto-collapses when isStreaming transitions from true to false', () => {
    const { rerender } = render(
      <ThinkingBlock content="Done thinking now." isStreaming thinkingStartedAt={Date.now()} />
    );

    // While streaming, content should be visible (expanded)
    expect(screen.getByText('Done thinking now.')).toBeInTheDocument();

    // Transition to not streaming
    rerender(
      <ThinkingBlock
        content="Done thinking now."
        isStreaming={false}
        durationMs={4200}
        thinkingStartedAt={Date.now() - 4200}
      />
    );

    // After 300ms delay, should auto-collapse (content hidden)
    act(() => {
      vi.advanceTimersByTime(300);
    });

    // Content is inside a conditional render, so when collapsed it won't show
    const preElement = document.querySelector('pre');
    expect(preElement).toBeNull();
  });

  // ========================================
  // Completed state header
  // ========================================

  it('shows "Thought for X.Xs" and Check icon when completed', () => {
    render(
      <ThinkingBlock
        content="This is the completed thinking content with enough text."
        isStreaming={false}
        durationMs={4200}
      />
    );

    // Should show formatted duration
    expect(screen.getByText(/Thought for 4\.2s/)).toBeInTheDocument();

    // Should show Check icon (not Brain icon)
    expect(screen.getByTestId('check-icon')).toBeInTheDocument();

    // Should NOT show token badge (removed in minimal design)
    expect(screen.queryByText(/tokens/)).not.toBeInTheDocument();
  });

  // ========================================
  // Expand/collapse toggle
  // ========================================

  it('toggles expand/collapse via click on button', () => {
    render(
      <ThinkingBlock content="Some thinking content here." isStreaming={false} durationMs={2000} />
    );

    const button = screen.getByRole('button', { name: 'Agent reasoning' });

    // Initially collapsed (after auto-collapse)
    act(() => {
      vi.advanceTimersByTime(350);
    });
    expect(button).toHaveAttribute('aria-expanded', 'false');

    // Click to expand
    fireEvent.click(button);
    expect(button).toHaveAttribute('aria-expanded', 'true');
    expect(screen.getByText('Some thinking content here.')).toBeInTheDocument();
  });

  it('stays open after manual expand on completed block (no re-collapse)', () => {
    render(<ThinkingBlock content="Completed thinking." isStreaming={false} durationMs={3000} />);

    // Initially collapsed (auto-collapse already fired)
    act(() => {
      vi.advanceTimersByTime(350); // 300ms auto-collapse + buffer
    });
    const button = screen.getByRole('button', { name: 'Agent reasoning' });
    expect(button).toHaveAttribute('aria-expanded', 'false');

    // User manually expands
    fireEvent.click(button);
    expect(button).toHaveAttribute('aria-expanded', 'true');

    // Advance timers well past auto-collapse delay — should stay open
    act(() => {
      vi.advanceTimersByTime(1000);
    });
    expect(button).toHaveAttribute('aria-expanded', 'true');
  });

  // ========================================
  // Streaming cursor
  // ========================================

  it('shows streaming cursor when expanded and streaming', () => {
    render(
      <ThinkingBlock content="Still thinking..." isStreaming thinkingStartedAt={Date.now()} />
    );

    // Streaming cursor: animate-pulse bg-ai span
    const cursor = Array.from(document.querySelectorAll('span')).find(
      (el) => el.className.includes('animate-pulse') && el.className.includes('bg-ai')
    );
    expect(cursor).toBeTruthy();
  });

  // ========================================
  // Scrollable content area
  // ========================================

  it('content area has scrollable overflow class', () => {
    render(<ThinkingBlock content="Long content..." isStreaming thinkingStartedAt={Date.now()} />);

    const scrollableDiv = document.querySelector('.max-h-\\[400px\\]');
    expect(scrollableDiv).toBeInTheDocument();
  });

  // ========================================
  // Empty content returns null
  // ========================================

  it('returns null when content is empty', () => {
    const { container } = render(<ThinkingBlock content="" isStreaming={false} />);

    expect(container.firstElementChild).toBeNull();
  });

  // ========================================
  // Interrupted label
  // ========================================

  it('renders "Thinking interrupted" label when interrupted=true', () => {
    render(
      <ThinkingBlock
        content="Was thinking but got interrupted..."
        isStreaming={false}
        interrupted
      />
    );

    expect(screen.getByText('Thinking interrupted')).toBeInTheDocument();
  });

  // ========================================
  // Redacted reasoning
  // ========================================

  it('renders "Reasoning redacted" with ShieldAlert icon for redacted content', () => {
    render(
      <ThinkingBlock
        content="[Thinking redacted by safety system]"
        isStreaming={false}
        durationMs={1000}
      />
    );

    expect(screen.getByText('Reasoning redacted')).toBeInTheDocument();
    expect(screen.getByTestId('shield-alert-icon')).toBeInTheDocument();
  });

  // ========================================
  // Named export
  // ========================================

  it('exports ThinkingBlock with displayName', () => {
    expect(ThinkingBlock.displayName).toBe('ThinkingBlock');
  });
});

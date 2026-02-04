/**
 * Unit tests for enhanced ThinkingBlock component.
 *
 * Tests frosted glass styling, streaming/completed states,
 * auto-collapse behavior, expand/collapse toggle, streaming
 * cursor, scrollable overflow, empty content, and interrupted state.
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
  Brain: (props: Record<string, unknown>) => <span data-testid="brain-icon" {...props} />,
  ChevronDown: (props: Record<string, unknown>) => (
    <span data-testid="chevron-down-icon" {...props} />
  ),
  ChevronRight: (props: Record<string, unknown>) => (
    <span data-testid="chevron-right-icon" {...props} />
  ),
  ShieldAlert: (props: Record<string, unknown>) => (
    <span data-testid="shield-alert-icon" {...props} />
  ),
}));

// Mock Collapsible components to render children directly with data-testids
vi.mock('@/components/ui/collapsible', () => ({
  Collapsible: ({
    children,
    open,
    ...rest
  }: {
    children: React.ReactNode;
    open?: boolean;
    onOpenChange?: (open: boolean) => void;
  }) => (
    <div data-testid="collapsible" data-open={open} {...rest}>
      {children}
    </div>
  ),
  CollapsibleTrigger: ({ children, ...rest }: { children: React.ReactNode; asChild?: boolean }) => (
    <div data-testid="collapsible-trigger" {...rest}>
      {children}
    </div>
  ),
  CollapsibleContent: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="collapsible-content">{children}</div>
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
  // Frosted glass styling
  // ========================================

  it('renders frosted glass styling when streaming', () => {
    render(
      <ThinkingBlock
        content="Analyzing the problem..."
        isStreaming
        thinkingStartedAt={Date.now()}
      />
    );

    const region = screen.getByRole('region', { name: 'Agent reasoning' });
    expect(region.className).toContain('glass-subtle');
    expect(region.className).toContain('bg-ai-muted');
    expect(region.className).toContain('border-l-ai');
  });

  // ========================================
  // Streaming state header
  // ========================================

  it('shows brain icon and "Thinking..." label with pulsing indicator when streaming', () => {
    render(<ThinkingBlock content="Working on it..." isStreaming thinkingStartedAt={Date.now()} />);

    expect(screen.getByTestId('brain-icon')).toBeInTheDocument();
    expect(screen.getByText('Thinking...')).toBeInTheDocument();

    // Pulsing dot indicator (1.5x1.5 rounded-full with motion-safe prefix)
    const pulsingDot = Array.from(document.querySelectorAll('span')).find(
      (el) =>
        el.className.includes('h-1.5') &&
        el.className.includes('w-1.5') &&
        el.className.includes('animate-pulse') &&
        el.className.includes('rounded-full') &&
        el.className.includes('bg-ai')
    );
    expect(pulsingDot).toBeTruthy();
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

    // While streaming, should be open
    const collapsible = screen.getByTestId('collapsible');
    expect(collapsible).toHaveAttribute('data-open', 'true');

    // Transition to not streaming
    rerender(
      <ThinkingBlock
        content="Done thinking now."
        isStreaming={false}
        durationMs={4200}
        thinkingStartedAt={Date.now() - 4200}
      />
    );

    // After 300ms delay, should auto-collapse
    act(() => {
      vi.advanceTimersByTime(300);
    });

    const collapsibleAfter = screen.getByTestId('collapsible');
    expect(collapsibleAfter).toHaveAttribute('data-open', 'false');
  });

  // ========================================
  // Completed state header
  // ========================================

  it('shows "Thought for X.Xs" and token badge when collapsed and completed', () => {
    render(
      <ThinkingBlock
        content="This is the completed thinking content with enough text."
        isStreaming={false}
        durationMs={4200}
      />
    );

    // Should show formatted duration
    expect(screen.getByText(/Thought for 4\.2s/)).toBeInTheDocument();

    // Should show token estimate badge
    const tokenText = screen.getByText(/tokens/);
    expect(tokenText).toBeInTheDocument();
  });

  // ========================================
  // Expand/collapse toggle
  // ========================================

  it('toggles expand/collapse via click on trigger', () => {
    render(
      <ThinkingBlock content="Some thinking content here." isStreaming={false} durationMs={2000} />
    );

    const trigger = screen.getByTestId('collapsible-trigger');
    const button = trigger.querySelector('button');
    expect(button).toBeInTheDocument();

    // Click to expand
    fireEvent.click(button!);

    // Collapsible should update
    const collapsible = screen.getByTestId('collapsible');
    expect(collapsible).toHaveAttribute('data-open', 'true');
  });

  it('stays open after manual expand on completed block (no re-collapse)', () => {
    render(<ThinkingBlock content="Completed thinking." isStreaming={false} durationMs={3000} />);

    // Initially collapsed (auto-collapse already fired)
    act(() => {
      vi.advanceTimersByTime(350); // 300ms auto-collapse + buffer
    });
    expect(screen.getByTestId('collapsible')).toHaveAttribute('data-open', 'false');

    // User manually expands
    const button = screen.getByTestId('collapsible-trigger').querySelector('button');
    fireEvent.click(button!);
    expect(screen.getByTestId('collapsible')).toHaveAttribute('data-open', 'true');

    // Advance timers well past auto-collapse delay — should stay open
    act(() => {
      vi.advanceTimersByTime(1000);
    });
    expect(screen.getByTestId('collapsible')).toHaveAttribute('data-open', 'true');
  });

  // ========================================
  // Streaming cursor
  // ========================================

  it('shows streaming cursor when expanded and streaming', () => {
    render(
      <ThinkingBlock content="Still thinking..." isStreaming thinkingStartedAt={Date.now()} />
    );

    // Streaming cursor: motion-safe:animate-pulse bg-ai span
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

    const contentArea = screen.getByTestId('collapsible-content');
    const scrollableDiv = contentArea.querySelector('.max-h-\\[400px\\]');
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

  it('renders "Interrupted" label when interrupted=true', () => {
    render(
      <ThinkingBlock
        content="Was thinking but got interrupted..."
        isStreaming={false}
        interrupted
      />
    );

    expect(screen.getByText('Interrupted')).toBeInTheDocument();
  });

  // ========================================
  // Named export
  // ========================================

  it('exports ThinkingBlock with displayName', () => {
    expect(ThinkingBlock.displayName).toBe('ThinkingBlock');
  });
});

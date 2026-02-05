/**
 * Unit tests for StreamingBanner component (T018).
 *
 * Validates:
 * - Renders nothing when not streaming and not interrupted
 * - Phase-specific icon + label rendering
 * - Right-side elapsed time vs word count display
 * - Interrupted state with auto-hide
 * - Glass-subtle background and border styling
 * - ARIA accessibility attributes
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import { StreamingBanner } from '../StreamingBanner';

// Mock motion/react — render children immediately without animation
vi.mock('motion/react', () => ({
  AnimatePresence: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  motion: {
    div: ({
      children,
      ...props
    }: React.HTMLAttributes<HTMLDivElement> & Record<string, unknown>) => {
      // Filter out motion-specific props
      const {
        initial: _initial,
        animate: _animate,
        exit: _exit,
        transition: _transition,
        ...htmlProps
      } = props;
      return <div {...htmlProps}>{children}</div>;
    },
  },
}));

// Mock useElapsedTime hook
vi.mock('@/hooks/useElapsedTime', () => ({
  useElapsedTime: vi.fn(() => '3.2s'),
}));

// Import after mock setup
import { useElapsedTime } from '@/hooks/useElapsedTime';
const mockUseElapsedTime = vi.mocked(useElapsedTime);

describe('StreamingBanner', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    mockUseElapsedTime.mockReturnValue('3.2s');
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it('renders nothing when isStreaming=false and interrupted=false', () => {
    const { container } = render(<StreamingBanner isStreaming={false} interrupted={false} />);
    expect(container.firstChild).toBeNull();
  });

  it('renders nothing when isStreaming=false and interrupted is undefined', () => {
    const { container } = render(<StreamingBanner isStreaming={false} />);
    expect(container.firstChild).toBeNull();
  });

  it('shows brain icon and "Thinking..." when phase is thinking', () => {
    render(<StreamingBanner isStreaming={true} phase="thinking" thinkingStartedAt={Date.now()} />);

    expect(screen.getByText('Thinking...')).toBeInTheDocument();
    expect(screen.getByTestId('streaming-banner')).toBeInTheDocument();
  });

  it('shows wrench icon and mapped tool name when phase is tool_use', () => {
    render(<StreamingBanner isStreaming={true} phase="tool_use" activeToolName="extract_issues" />);

    expect(screen.getByText('Using Extracting Issues...')).toBeInTheDocument();
  });

  it('shows fallback tool name when activeToolName is unknown', () => {
    render(<StreamingBanner isStreaming={true} phase="tool_use" activeToolName="custom_tool" />);

    expect(screen.getByText('Using Custom Tool...')).toBeInTheDocument();
  });

  it('shows "Using tool..." when tool_use phase but no activeToolName', () => {
    render(<StreamingBanner isStreaming={true} phase="tool_use" activeToolName={null} />);

    expect(screen.getByText('Using tool...')).toBeInTheDocument();
  });

  it('shows pencil icon and "Writing response..." with word count when phase is content', () => {
    render(<StreamingBanner isStreaming={true} phase="content" wordCount={42} />);

    expect(screen.getByText('Writing response...')).toBeInTheDocument();
    expect(screen.getByText('42w')).toBeInTheDocument();
  });

  it('shows word count of 0 when content phase with no words', () => {
    render(<StreamingBanner isStreaming={true} phase="content" wordCount={0} />);

    expect(screen.getByText('0w')).toBeInTheDocument();
  });

  it('shows "Connecting..." when phase is connecting', () => {
    render(<StreamingBanner isStreaming={true} phase="connecting" />);

    expect(screen.getByText('Connecting...')).toBeInTheDocument();
  });

  it('shows "Finishing..." when phase is completing', () => {
    render(<StreamingBanner isStreaming={true} phase="completing" />);

    expect(screen.getByText('Finishing...')).toBeInTheDocument();
  });

  it('shows "Starting..." when phase is message_start', () => {
    render(<StreamingBanner isStreaming={true} phase="message_start" />);

    expect(screen.getByText('Starting...')).toBeInTheDocument();
  });

  it('displays elapsed time for thinking phase', () => {
    mockUseElapsedTime.mockReturnValue('5.1s');

    render(
      <StreamingBanner isStreaming={true} phase="thinking" thinkingStartedAt={Date.now() - 5100} />
    );

    expect(screen.getByText('5.1s')).toBeInTheDocument();
  });

  it('displays elapsed time for tool_use phase', () => {
    mockUseElapsedTime.mockReturnValue('2.0s');

    render(
      <StreamingBanner
        isStreaming={true}
        phase="tool_use"
        activeToolName="enhance_text"
        thinkingStartedAt={Date.now() - 2000}
      />
    );

    expect(screen.getByText('2.0s')).toBeInTheDocument();
  });

  it('shows "Stopped" when interrupted=true', async () => {
    await act(async () => {
      render(<StreamingBanner isStreaming={false} interrupted={true} />);
    });

    // Flush microtask queue for queueMicrotask-based state update
    await act(async () => {
      await Promise.resolve();
    });

    expect(screen.getByText('Stopped')).toBeInTheDocument();
  });

  it('auto-hides after 1.5s when interrupted', async () => {
    let container: HTMLElement;
    await act(async () => {
      const result = render(<StreamingBanner isStreaming={false} interrupted={true} />);
      container = result.container;
    });

    // Flush microtask queue
    await act(async () => {
      await Promise.resolve();
    });

    expect(screen.getByText('Stopped')).toBeInTheDocument();

    await act(async () => {
      vi.advanceTimersByTime(1500);
    });

    // After 1.5s, banner should hide
    expect(container!.querySelector('[data-testid="streaming-banner"]')).toBeNull();
  });

  it('uses glass-subtle class for frosted glass background', () => {
    render(<StreamingBanner isStreaming={true} phase="thinking" />);

    const banner = screen.getByTestId('streaming-banner');
    expect(banner.className).toContain('glass-subtle');
  });

  it('has border-t border-t-border-subtle for top border', () => {
    render(<StreamingBanner isStreaming={true} phase="thinking" />);

    const banner = screen.getByTestId('streaming-banner');
    expect(banner.className).toContain('border-t');
    expect(banner.className).toContain('border-t-border-subtle');
  });

  it('has role="status" and aria-live="polite" for accessibility', () => {
    render(<StreamingBanner isStreaming={true} phase="content" wordCount={10} />);

    const banner = screen.getByRole('status');
    expect(banner).toBeInTheDocument();
    expect(banner).toHaveAttribute('aria-live', 'polite');
  });

  it('applies custom className', () => {
    render(<StreamingBanner isStreaming={true} phase="thinking" className="custom-class" />);

    const banner = screen.getByTestId('streaming-banner');
    expect(banner.className).toContain('custom-class');
  });
});

/**
 * Unit tests for ToolCallCard component.
 *
 * Tests display name mapping, status icons with correct colors,
 * error message display, elapsed time, completed duration,
 * collapsible detail section, and partial input streaming indicator.
 *
 * @module features/ai/ChatView/MessageList/__tests__/ToolCallCard
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, act } from '@testing-library/react';

// Mock useElapsedTime to control timer output
vi.mock('@/hooks/useElapsedTime', () => ({
  useElapsedTime: vi.fn(() => '1.5s'),
}));

// Mock lucide-react icons
vi.mock('lucide-react', () => ({
  Loader2: (props: Record<string, unknown>) => <span data-testid="loader2-icon" {...props} />,
  CheckCircle2: (props: Record<string, unknown>) => (
    <span data-testid="check-circle-icon" {...props} />
  ),
  XCircle: (props: Record<string, unknown>) => <span data-testid="x-circle-icon" {...props} />,
  ChevronDown: (props: Record<string, unknown>) => (
    <span data-testid="chevron-down-icon" {...props} />
  ),
}));

// Mock Collapsible components
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

import { makeAutoObservable, runInAction } from 'mobx';
import { useElapsedTime } from '@/hooks/useElapsedTime';
import { ToolCallCard } from '../ToolCallCard';
import type { ToolCall } from '@/stores/ai/types/conversation';

const mockUseElapsedTime = vi.mocked(useElapsedTime);

function makeToolCall(overrides: Partial<ToolCall> = {}): ToolCall {
  return {
    id: 'tc-1',
    name: 'extract_issues',
    input: { text: 'some content' },
    status: 'pending',
    ...overrides,
  };
}

describe('ToolCallCard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseElapsedTime.mockReturnValue('1.5s');
  });

  // ========================================
  // Display name mapping
  // ========================================

  it('renders mapped display name for known tools', () => {
    render(<ToolCallCard toolCall={makeToolCall({ name: 'extract_issues' })} />);

    expect(screen.getByText('Extracting Issues')).toBeInTheDocument();
  });

  it('falls back to title-cased raw name for unknown tools', () => {
    render(<ToolCallCard toolCall={makeToolCall({ name: 'some_tool' })} />);

    expect(screen.getByText('Some Tool')).toBeInTheDocument();
  });

  // ========================================
  // Status icons
  // ========================================

  it('shows Loader2 spinning icon with AI blue color when status is pending', () => {
    render(<ToolCallCard toolCall={makeToolCall({ status: 'pending' })} />);

    const icon = screen.getByTestId('loader2-icon');
    expect(icon).toBeInTheDocument();
    expect(icon.className).toContain('text-ai');
    expect(icon.className).toContain('animate-spin');
  });

  it('shows CheckCircle2 green icon when status is completed', () => {
    render(<ToolCallCard toolCall={makeToolCall({ status: 'completed', durationMs: 800 })} />);

    const icon = screen.getByTestId('check-circle-icon');
    expect(icon).toBeInTheDocument();
    expect(icon.className).toContain('text-primary');
  });

  it('shows XCircle red icon when status is failed', () => {
    render(
      <ToolCallCard
        toolCall={makeToolCall({ status: 'failed', errorMessage: 'Something went wrong' })}
      />
    );

    const icon = screen.getByTestId('x-circle-icon');
    expect(icon).toBeInTheDocument();
    expect(icon.className).toContain('text-destructive');
  });

  // ========================================
  // Error message
  // ========================================

  it('displays error message when errorMessage is set', () => {
    render(
      <ToolCallCard
        toolCall={makeToolCall({ status: 'failed', errorMessage: 'Rate limit exceeded' })}
      />
    );

    expect(screen.getByText('Rate limit exceeded')).toBeInTheDocument();
  });

  // ========================================
  // Elapsed time (pending)
  // ========================================

  it('shows elapsed time via useElapsedTime when status is pending', () => {
    mockUseElapsedTime.mockReturnValue('2.3s');

    render(<ToolCallCard toolCall={makeToolCall({ status: 'pending' })} />);

    expect(screen.getByText('2.3s')).toBeInTheDocument();
    expect(mockUseElapsedTime).toHaveBeenCalledWith(expect.any(Number), true);
  });

  // ========================================
  // Completed duration
  // ========================================

  it('shows formatted duration when completed with durationMs', () => {
    render(<ToolCallCard toolCall={makeToolCall({ status: 'completed', durationMs: 800 })} />);

    expect(screen.getByText('0.8s')).toBeInTheDocument();
  });

  it('shows formatted duration in seconds for longer durations', () => {
    render(<ToolCallCard toolCall={makeToolCall({ status: 'completed', durationMs: 2100 })} />);

    expect(screen.getByText('2.1s')).toBeInTheDocument();
  });

  // ========================================
  // Collapsible detail section
  // ========================================

  it('collapsible detail expands to show input JSON', () => {
    const input = { text: 'hello world', count: 3 };
    render(
      <ToolCallCard toolCall={makeToolCall({ input, status: 'completed', durationMs: 500 })} />
    );

    // Collapsible content should contain the input JSON
    const content = screen.getByTestId('collapsible-content');
    expect(content.textContent).toContain('"text": "hello world"');
    expect(content.textContent).toContain('"count": 3');
  });

  it('shows output when available', () => {
    render(
      <ToolCallCard
        toolCall={makeToolCall({
          status: 'completed',
          durationMs: 500,
          output: { result: 'success', items: [1, 2] },
        })}
      />
    );

    const content = screen.getByTestId('collapsible-content');
    expect(content.textContent).toContain('"result": "success"');
  });

  it('shows string output directly', () => {
    render(
      <ToolCallCard
        toolCall={makeToolCall({
          status: 'completed',
          durationMs: 500,
          output: 'Plain text result',
        })}
      />
    );

    const content = screen.getByTestId('collapsible-content');
    expect(content.textContent).toContain('Plain text result');
  });

  // ========================================
  // Partial input (G-09)
  // ========================================

  it('shows partial input with pulsing indicator when partialInput is set and pending', () => {
    render(
      <ToolCallCard
        toolCall={makeToolCall({
          status: 'pending',
          partialInput: '{"text": "partial...',
          input: {},
        })}
      />
    );

    const content = screen.getByTestId('collapsible-content');
    expect(content.textContent).toContain('{"text": "partial...');

    // Pulsing dot indicator
    const pulsingDot = content.querySelector('.animate-pulse.rounded-full');
    expect(pulsingDot).toBeInTheDocument();
  });

  // ========================================
  // ARIA attributes
  // ========================================

  it('has correct ARIA role and label', () => {
    render(<ToolCallCard toolCall={makeToolCall({ status: 'pending' })} />);

    const article = screen.getByRole('article');
    expect(article).toHaveAttribute('aria-label', 'Extracting Issues — Pending');
  });

  it('has correct ARIA label for completed status', () => {
    render(<ToolCallCard toolCall={makeToolCall({ status: 'completed', durationMs: 1000 })} />);

    const article = screen.getByRole('article');
    expect(article).toHaveAttribute('aria-label', 'Extracting Issues — Completed');
  });

  // ========================================
  // className forwarding
  // ========================================

  it('forwards className prop', () => {
    render(<ToolCallCard toolCall={makeToolCall()} className="custom-class" />);

    const article = screen.getByRole('article');
    expect(article.className).toContain('custom-class');
  });

  // ========================================
  // MobX observer reactivity (memo→observer fix)
  // ========================================

  it('re-renders when MobX observable ToolCall properties are mutated', () => {
    // Create a MobX observable tool call to simulate store behavior
    const toolCall = makeToolCall({ status: 'pending' });
    makeAutoObservable(toolCall);

    const { rerender } = render(<ToolCallCard toolCall={toolCall} />);

    // Initially pending
    expect(screen.getByTestId('loader2-icon')).toBeInTheDocument();
    expect(screen.getByRole('article')).toHaveAttribute(
      'aria-label',
      'Extracting Issues — Pending'
    );

    // Mutate the observable (simulating tool_result handler in store)
    act(() => {
      runInAction(() => {
        toolCall.status = 'completed';
        toolCall.durationMs = 1200;
        toolCall.output = { result: 'done' };
      });
    });

    // Re-render (observer detects MobX mutation)
    rerender(<ToolCallCard toolCall={toolCall} />);

    expect(screen.getByTestId('check-circle-icon')).toBeInTheDocument();
    expect(screen.getByRole('article')).toHaveAttribute(
      'aria-label',
      'Extracting Issues — Completed'
    );
  });
});

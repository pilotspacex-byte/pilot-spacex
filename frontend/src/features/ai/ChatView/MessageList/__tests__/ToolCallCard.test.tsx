/**
 * Unit tests for ToolCallCard component (Claude.ai minimal style).
 *
 * Tests display name mapping, status icons with correct colors,
 * error message display, elapsed time, completed duration,
 * collapsible detail section, and partial input streaming indicator.
 *
 * @module features/ai/ChatView/MessageList/__tests__/ToolCallCard
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, act } from '@testing-library/react';

// Mock useElapsedTime to control timer output
vi.mock('@/hooks/useElapsedTime', () => ({
  useElapsedTime: vi.fn(() => '1.5s'),
}));

// Mock lucide-react icons
vi.mock('lucide-react', () => ({
  Loader2: (props: Record<string, unknown>) => <span data-testid="loader2-icon" {...props} />,
  Settings: (props: Record<string, unknown>) => <span data-testid="settings-icon" {...props} />,
  XCircle: (props: Record<string, unknown>) => <span data-testid="x-circle-icon" {...props} />,
  ChevronDown: (props: Record<string, unknown>) => (
    <span data-testid="chevron-down-icon" {...props} />
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
  // Display name mapping with "Calling/Used" prefix
  // ========================================

  it('renders "Calling X..." when status is pending', () => {
    render(<ToolCallCard toolCall={makeToolCall({ name: 'extract_issues', status: 'pending' })} />);

    expect(screen.getByText('Calling Extracting Issues...')).toBeInTheDocument();
  });

  it('renders "Used X" when status is completed', () => {
    render(
      <ToolCallCard
        toolCall={makeToolCall({ name: 'extract_issues', status: 'completed', durationMs: 800 })}
      />
    );

    expect(screen.getByText('Used Extracting Issues')).toBeInTheDocument();
  });

  it('falls back to title-cased raw name for unknown tools', () => {
    render(<ToolCallCard toolCall={makeToolCall({ name: 'some_tool', status: 'completed' })} />);

    expect(screen.getByText('Used Some Tool')).toBeInTheDocument();
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

  it('shows Settings (gear) icon with muted color when status is completed', () => {
    render(<ToolCallCard toolCall={makeToolCall({ status: 'completed', durationMs: 800 })} />);

    const icon = screen.getByTestId('settings-icon');
    expect(icon).toBeInTheDocument();
    expect(icon.className).toContain('text-muted-foreground');
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

  it('expands to show input JSON when clicked', () => {
    const input = { text: 'hello world', count: 3 };
    render(
      <ToolCallCard toolCall={makeToolCall({ input, status: 'completed', durationMs: 500 })} />
    );

    // Click to expand
    const button = screen.getByRole('button');
    fireEvent.click(button);

    // Should show input JSON
    expect(screen.getByText(/Input:/)).toBeInTheDocument();
    expect(screen.getByText(/"text": "hello world"/)).toBeInTheDocument();
  });

  it('shows output when available and expanded', () => {
    render(
      <ToolCallCard
        toolCall={makeToolCall({
          status: 'completed',
          durationMs: 500,
          output: { result: 'success', items: [1, 2] },
        })}
      />
    );

    // Click to expand
    const button = screen.getByRole('button');
    fireEvent.click(button);

    expect(screen.getByText(/Output:/)).toBeInTheDocument();
    expect(screen.getByText(/"result": "success"/)).toBeInTheDocument();
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

    // Click to expand
    const button = screen.getByRole('button');
    fireEvent.click(button);

    expect(screen.getByText('Plain text result')).toBeInTheDocument();
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

    // Click to expand
    const button = screen.getByRole('button');
    fireEvent.click(button);

    expect(screen.getByText('{"text": "partial...')).toBeInTheDocument();

    // Pulsing dot indicator
    const pulsingDot = document.querySelector('.animate-pulse.rounded-full');
    expect(pulsingDot).toBeInTheDocument();
  });

  // ========================================
  // ARIA attributes
  // ========================================

  it('has correct aria-label on button', () => {
    render(<ToolCallCard toolCall={makeToolCall({ status: 'pending' })} />);

    const button = screen.getByRole('button', { name: 'Extracting Issues tool call' });
    expect(button).toBeInTheDocument();
  });

  it('has aria-expanded attribute when detail is available', () => {
    render(<ToolCallCard toolCall={makeToolCall({ status: 'completed', durationMs: 500 })} />);

    const button = screen.getByRole('button');
    expect(button).toHaveAttribute('aria-expanded', 'false');

    // Click to expand
    fireEvent.click(button);
    expect(button).toHaveAttribute('aria-expanded', 'true');
  });

  // ========================================
  // className forwarding
  // ========================================

  it('forwards className prop', () => {
    const { container } = render(
      <ToolCallCard toolCall={makeToolCall()} className="custom-class" />
    );

    expect(container.firstElementChild?.className).toContain('custom-class');
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
    expect(screen.getByText('Calling Extracting Issues...')).toBeInTheDocument();

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

    expect(screen.getByTestId('settings-icon')).toBeInTheDocument();
    expect(screen.getByText('Used Extracting Issues')).toBeInTheDocument();
  });
});

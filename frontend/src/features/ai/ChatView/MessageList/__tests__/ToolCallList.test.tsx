/**
 * Unit tests for ToolCallList component (Claude.ai minimal style).
 *
 * Tests ToolCallCard rendering for each tool call, empty state,
 * and className forwarding. Parallel header removed per minimal design.
 *
 * @module features/ai/ChatView/MessageList/__tests__/ToolCallList
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';

// Mock useElapsedTime (used by ToolCallCard)
vi.mock('@/hooks/useElapsedTime', () => ({
  useElapsedTime: vi.fn(() => '1.0s'),
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

import { ToolCallList } from '../ToolCallList';
import type { ToolCall } from '@/stores/ai/types/conversation';

function makeToolCall(overrides: Partial<ToolCall> = {}): ToolCall {
  return {
    id: 'tc-1',
    name: 'extract_issues',
    input: {},
    status: 'pending',
    ...overrides,
  };
}

describe('ToolCallList', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ========================================
  // Empty state
  // ========================================

  it('returns null when toolCalls is empty', () => {
    const { container } = render(<ToolCallList toolCalls={[]} />);

    expect(container.firstElementChild).toBeNull();
  });

  // ========================================
  // Single tool call
  // ========================================

  it('renders ToolCallCard for a single tool call', () => {
    render(<ToolCallList toolCalls={[makeToolCall()]} />);

    // Should render the tool card with "Calling" prefix
    expect(screen.getByText('Calling Extracting Issues...')).toBeInTheDocument();
  });

  it('does not show parallel header for single tool call (removed in minimal design)', () => {
    render(<ToolCallList toolCalls={[makeToolCall()]} />);

    expect(screen.queryByText(/Parallel/)).not.toBeInTheDocument();
  });

  // ========================================
  // Multiple tool calls
  // ========================================

  it('renders ToolCallCard for each tool call', () => {
    const toolCalls = [
      makeToolCall({ id: 'tc-1', name: 'extract_issues' }),
      makeToolCall({ id: 'tc-2', name: 'enhance_text' }),
      makeToolCall({ id: 'tc-3', name: 'summarize_note' }),
    ];

    render(<ToolCallList toolCalls={toolCalls} />);

    expect(screen.getByText('Calling Extracting Issues...')).toBeInTheDocument();
    expect(screen.getByText('Calling Enhancing Text...')).toBeInTheDocument();
    expect(screen.getByText('Calling Summarizing Note...')).toBeInTheDocument();
  });

  it('does NOT show "Parallel (N tools)" header (removed in minimal design)', () => {
    const toolCalls = [
      makeToolCall({ id: 'tc-1', name: 'extract_issues' }),
      makeToolCall({ id: 'tc-2', name: 'enhance_text' }),
    ];

    render(<ToolCallList toolCalls={toolCalls} />);

    // Parallel header removed in Claude.ai minimal style
    expect(screen.queryByText(/Parallel/)).not.toBeInTheDocument();
    expect(screen.queryByText(/tools\)/)).not.toBeInTheDocument();
  });

  it('does NOT have left border container styling (removed in minimal design)', () => {
    const toolCalls = [makeToolCall({ id: 'tc-1' }), makeToolCall({ id: 'tc-2' })];

    render(<ToolCallList toolCalls={toolCalls} />);

    // Border styling removed in Claude.ai minimal style
    const borderContainer = document.querySelector('.border-l-2');
    expect(borderContainer).toBeNull();
  });

  // ========================================
  // Spacing
  // ========================================

  it('uses space-y-1 for compact spacing between cards', () => {
    const toolCalls = [makeToolCall({ id: 'tc-1' }), makeToolCall({ id: 'tc-2' })];

    const { container } = render(<ToolCallList toolCalls={toolCalls} />);

    expect(container.firstElementChild?.className).toContain('space-y-1');
  });

  // ========================================
  // className forwarding
  // ========================================

  it('forwards className to root element', () => {
    const { container } = render(
      <ToolCallList toolCalls={[makeToolCall()]} className="extra-class" />
    );

    expect(container.firstElementChild?.className).toContain('extra-class');
  });
});

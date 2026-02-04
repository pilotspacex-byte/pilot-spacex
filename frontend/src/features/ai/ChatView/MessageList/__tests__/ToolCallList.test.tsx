/**
 * Unit tests for updated ToolCallList component.
 *
 * Tests ToolCallCard rendering for each tool call, parallel header
 * with GitBranch icon, left border styling, and empty state.
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
  CheckCircle2: (props: Record<string, unknown>) => (
    <span data-testid="check-circle-icon" {...props} />
  ),
  XCircle: (props: Record<string, unknown>) => <span data-testid="x-circle-icon" {...props} />,
  ChevronDown: (props: Record<string, unknown>) => (
    <span data-testid="chevron-down-icon" {...props} />
  ),
  GitBranch: (props: Record<string, unknown>) => <span data-testid="git-branch-icon" {...props} />,
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

    // Should render the tool card with display name
    expect(screen.getByText('Extracting Issues')).toBeInTheDocument();
  });

  it('does not show parallel header for single tool call', () => {
    render(<ToolCallList toolCalls={[makeToolCall()]} />);

    expect(screen.queryByTestId('git-branch-icon')).not.toBeInTheDocument();
    expect(screen.queryByText(/Parallel/)).not.toBeInTheDocument();
  });

  // ========================================
  // Parallel tool calls
  // ========================================

  it('renders ToolCallCard for each tool call', () => {
    const toolCalls = [
      makeToolCall({ id: 'tc-1', name: 'extract_issues' }),
      makeToolCall({ id: 'tc-2', name: 'enhance_text' }),
      makeToolCall({ id: 'tc-3', name: 'summarize_note' }),
    ];

    render(<ToolCallList toolCalls={toolCalls} />);

    expect(screen.getByText('Extracting Issues')).toBeInTheDocument();
    expect(screen.getByText('Enhancing Text')).toBeInTheDocument();
    expect(screen.getByText('Summarizing Note')).toBeInTheDocument();
  });

  it('shows "Parallel (N tools)" header with GitBranch icon when toolCalls.length > 1', () => {
    const toolCalls = [
      makeToolCall({ id: 'tc-1', name: 'extract_issues' }),
      makeToolCall({ id: 'tc-2', name: 'enhance_text' }),
    ];

    render(<ToolCallList toolCalls={toolCalls} />);

    expect(screen.getByTestId('git-branch-icon')).toBeInTheDocument();
    expect(screen.getByText('Parallel (2 tools)')).toBeInTheDocument();
  });

  it('wraps parallel calls in container with left border', () => {
    const toolCalls = [makeToolCall({ id: 'tc-1' }), makeToolCall({ id: 'tc-2' })];

    render(<ToolCallList toolCalls={toolCalls} />);

    // Find the container with border-l styling
    const container = document.querySelector('.border-l-2.border-l-ai\\/20');
    expect(container).toBeInTheDocument();
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

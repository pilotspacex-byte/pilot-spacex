/**
 * Unit tests for StreamingContent component.
 *
 * Tests ordered block rendering via blockOrder/textSegments,
 * fallback grouped rendering, and empty/partial states.
 *
 * @module features/ai/ChatView/MessageList/__tests__/StreamingContent
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';

// Mock useElapsedTime (used by ThinkingBlock)
vi.mock('@/hooks/useElapsedTime', () => ({
  useElapsedTime: vi.fn(() => '1.0s'),
}));

// Mock lucide-react icons
vi.mock('lucide-react', () => ({
  Loader2: (props: Record<string, unknown>) => <span data-testid="loader2-icon" {...props} />,
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
  CheckCircle2: (props: Record<string, unknown>) => (
    <span data-testid="check-circle-icon" {...props} />
  ),
  XCircle: (props: Record<string, unknown>) => <span data-testid="x-circle-icon" {...props} />,
  GitBranch: (props: Record<string, unknown>) => <span data-testid="git-branch-icon" {...props} />,
}));

// Mock Collapsible components (used by ThinkingBlock and ToolCallCard)
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

// Mock MarkdownContent to expose rendered text
vi.mock('../MarkdownContent', () => ({
  MarkdownContent: ({ content, isStreaming }: { content: string; isStreaming?: boolean }) => (
    <div data-testid="markdown-content" data-streaming={isStreaming}>
      {content}
    </div>
  ),
}));

import { StreamingContent } from '../StreamingContent';
import type { ToolCall, ThinkingBlockEntry } from '@/stores/ai/types/conversation';

function makeToolCall(overrides: Partial<ToolCall> = {}): ToolCall {
  return {
    id: 'tc-1',
    name: 'extract_issues',
    input: {},
    status: 'pending',
    ...overrides,
  };
}

function makeThinkingBlock(overrides: Partial<ThinkingBlockEntry> = {}): ThinkingBlockEntry {
  return {
    blockIndex: 0,
    content: 'Thinking about the problem...',
    ...overrides,
  };
}

describe('StreamingContent', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ========================================
  // Streaming indicator
  // ========================================

  it('shows "Streaming..." indicator when not thinking', () => {
    render(<StreamingContent content="Hello" />);

    expect(screen.getByText('Streaming...')).toBeInTheDocument();
  });

  it('shows "Thinking..." indicator when isThinking is true', () => {
    render(<StreamingContent content="" isThinking thinkingContent="reasoning..." />);

    // Both the streaming indicator and ThinkingBlock header show "Thinking..."
    const thinkingElements = screen.getAllByText('Thinking...');
    expect(thinkingElements.length).toBeGreaterThanOrEqual(1);
  });

  // ========================================
  // Ordered block rendering (blockOrder)
  // ========================================

  describe('OrderedStreamingBlocks', () => {
    it('renders thinking → text → tool_use in SSE arrival order', () => {
      const { container } = render(
        <StreamingContent
          content=""
          thinkingBlocks={[makeThinkingBlock({ blockIndex: 0, content: 'Reasoning step' })]}
          textSegments={['Response text here']}
          pendingToolCalls={[makeToolCall({ id: 'tc-1', name: 'extract_issues' })]}
          blockOrder={['thinking', 'text', 'tool_use']}
          isThinking={false}
        />
      );

      // All three block types should render
      expect(container.textContent).toContain('Reasoning step');
      expect(screen.getByTestId('markdown-content')).toHaveTextContent('Response text here');
      expect(screen.getByText('Extracting Issues')).toBeInTheDocument();
    });

    it('renders text → thinking → text interleaved order', () => {
      render(
        <StreamingContent
          content=""
          thinkingBlocks={[makeThinkingBlock({ blockIndex: 0, content: 'Mid-stream thinking' })]}
          textSegments={['First part', 'Second part']}
          blockOrder={['text', 'thinking', 'text']}
          isThinking={false}
        />
      );

      const markdownElements = screen.getAllByTestId('markdown-content');
      expect(markdownElements).toHaveLength(2);
      expect(markdownElements[0]).toHaveTextContent('First part');
      expect(markdownElements[1]).toHaveTextContent('Second part');
    });

    it('renders tool_use → text → tool_use interleaved order', () => {
      render(
        <StreamingContent
          content=""
          textSegments={['Intermediate text']}
          pendingToolCalls={[
            makeToolCall({ id: 'tc-1', name: 'extract_issues' }),
            makeToolCall({ id: 'tc-2', name: 'enhance_text' }),
          ]}
          blockOrder={['tool_use', 'text', 'tool_use']}
          isThinking={false}
        />
      );

      expect(screen.getByText('Extracting Issues')).toBeInTheDocument();
      expect(screen.getByText('Enhancing Text')).toBeInTheDocument();
      expect(screen.getByTestId('markdown-content')).toHaveTextContent('Intermediate text');
    });

    it('skips empty text segments in ordered rendering', () => {
      render(
        <StreamingContent
          content=""
          textSegments={['', 'Real content']}
          blockOrder={['text', 'text']}
          isThinking={false}
        />
      );

      const markdownElements = screen.getAllByTestId('markdown-content');
      expect(markdownElements).toHaveLength(1);
      expect(markdownElements[0]).toHaveTextContent('Real content');
    });

    it('marks only the last block as streaming', () => {
      render(
        <StreamingContent
          content=""
          textSegments={['First', 'Second (streaming)']}
          blockOrder={['text', 'text']}
          isThinking={false}
        />
      );

      const markdownElements = screen.getAllByTestId('markdown-content');
      expect(markdownElements[0]).toHaveAttribute('data-streaming', 'false');
      expect(markdownElements[1]).toHaveAttribute('data-streaming', 'true');
    });

    it('handles missing data gracefully (more blockOrder entries than data)', () => {
      render(
        <StreamingContent
          content=""
          thinkingBlocks={[]}
          textSegments={[]}
          pendingToolCalls={[]}
          blockOrder={['thinking', 'text', 'tool_use']}
          isThinking={false}
        />
      );

      // Should not crash, no content rendered
      expect(screen.queryByTestId('markdown-content')).not.toBeInTheDocument();
    });
  });

  // ========================================
  // Fallback grouped rendering (no blockOrder)
  // ========================================

  describe('fallback grouped rendering', () => {
    it('renders thinking blocks when no blockOrder is provided', () => {
      const { container } = render(
        <StreamingContent
          content="Response"
          thinkingBlocks={[makeThinkingBlock({ content: 'Grouped thinking' })]}
          isThinking={false}
        />
      );

      expect(container.textContent).toContain('Grouped thinking');
      expect(screen.getByTestId('markdown-content')).toHaveTextContent('Response');
    });

    it('renders thinkingContent (legacy) when no thinkingBlocks exist', () => {
      const { container } = render(
        <StreamingContent content="Hello" thinkingContent="Legacy thinking" isThinking />
      );

      expect(container.textContent).toContain('Legacy thinking');
    });

    it('renders tool calls in fallback mode', () => {
      render(
        <StreamingContent
          content="After tools"
          pendingToolCalls={[makeToolCall({ name: 'summarize_note' })]}
        />
      );

      expect(screen.getByText('Summarizing Note')).toBeInTheDocument();
      expect(screen.getByTestId('markdown-content')).toHaveTextContent('After tools');
    });

    it('does not render markdown when content is empty', () => {
      render(<StreamingContent content="" pendingToolCalls={[makeToolCall()]} />);

      expect(screen.queryByTestId('markdown-content')).not.toBeInTheDocument();
    });
  });

  // ========================================
  // className forwarding
  // ========================================

  it('forwards className prop to root element', () => {
    const { container } = render(<StreamingContent content="test" className="custom-streaming" />);

    expect(container.firstElementChild?.className).toContain('custom-streaming');
  });
});

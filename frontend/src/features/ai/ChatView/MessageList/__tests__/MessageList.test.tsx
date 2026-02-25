/**
 * Unit tests for MessageList component (T60 virtualization).
 *
 * Tests:
 * - Empty state rendering when no messages
 * - Virtuoso-based message group rendering
 * - Streaming footer visibility
 * - Scroll-to-bottom button visibility (default hidden at bottom)
 * - Named export verification
 * - groupMessagesByRole utility logic
 */

import type React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import type { ChatMessage } from '@/stores/ai/types/conversation';

// Mock react-virtuoso: render all items synchronously for unit testing
vi.mock('react-virtuoso', () => ({
  Virtuoso: vi.fn(
    ({
      totalCount,
      itemContent,
    }: {
      totalCount: number;
      itemContent: (index: number) => React.ReactNode;
    }) => (
      <div data-testid="virtuoso">
        {Array.from({ length: totalCount }, (_, i) => (
          <div key={i}>{itemContent(i)}</div>
        ))}
      </div>
    )
  ),
}));

// Mock child components to isolate MessageList behavior
vi.mock('../MessageGroup', () => ({
  MessageGroup: ({ messages }: { messages: ChatMessage[] }) => (
    <div data-testid="message-group" data-count={messages.length}>
      {messages.map((m) => (
        <span key={m.id} data-testid={`msg-${m.id}`}>
          {m.content}
        </span>
      ))}
    </div>
  ),
}));

vi.mock('../StreamingContent', () => ({
  StreamingContent: ({ content }: { content: string }) => (
    <div data-testid="streaming-content">{content}</div>
  ),
}));

// Mock mobx-react-lite observer to pass through the component
vi.mock('mobx-react-lite', () => ({
  observer: <T,>(component: T): T => component,
}));

// Mock lucide-react icons
vi.mock('lucide-react', () => ({
  ArrowDown: () => <span data-testid="arrow-down-icon" />,
  Sparkles: () => <span data-testid="sparkles-icon" />,
}));

import { MessageList } from '../MessageList';

function createMessage(
  overrides: Partial<ChatMessage> & { id: string; role: ChatMessage['role'] }
): ChatMessage {
  return {
    content: '',
    timestamp: new Date('2026-01-15T10:00:00Z'),
    ...overrides,
  };
}

describe('MessageList (T60 virtualization)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ========================================
  // Empty state
  // ========================================

  it('renders empty state when no messages', () => {
    render(<MessageList messages={[]} />);

    expect(screen.getByText('Start a conversation')).toBeInTheDocument();
    expect(screen.queryByTestId('virtuoso')).not.toBeInTheDocument();
  });

  // ========================================
  // Virtuoso rendering with message groups
  // ========================================

  it('renders message groups with Virtuoso', () => {
    const messages: ChatMessage[] = [
      createMessage({ id: 'msg-1', role: 'user', content: 'Hello' }),
      createMessage({ id: 'msg-2', role: 'assistant', content: 'Hi there' }),
      createMessage({ id: 'msg-3', role: 'user', content: 'How are you?' }),
    ];

    render(<MessageList messages={messages} />);

    // Virtuoso container should render
    expect(screen.getByTestId('virtuoso')).toBeInTheDocument();

    // 3 messages with alternating roles = 3 groups
    const groups = screen.getAllByTestId('message-group');
    expect(groups).toHaveLength(3);

    // Each group has exactly 1 message (no consecutive same-role)
    groups.forEach((group) => {
      expect(group).toHaveAttribute('data-count', '1');
    });

    // Verify message content renders
    expect(screen.getByText('Hello')).toBeInTheDocument();
    expect(screen.getByText('Hi there')).toBeInTheDocument();
    expect(screen.getByText('How are you?')).toBeInTheDocument();
  });

  // ========================================
  // Streaming footer
  // ========================================

  it('shows streaming footer when streaming', () => {
    const messages: ChatMessage[] = [
      createMessage({ id: 'msg-1', role: 'user', content: 'Question' }),
    ];

    render(<MessageList messages={messages} isStreaming={true} streamContent="Hello" />);

    expect(screen.getByTestId('streaming-content')).toBeInTheDocument();
    expect(screen.getByText('Hello')).toBeInTheDocument();
  });

  // ========================================
  // Scroll button default state
  // ========================================

  it('hides scroll button when at bottom (default state)', () => {
    const messages: ChatMessage[] = [createMessage({ id: 'msg-1', role: 'user', content: 'Test' })];

    render(<MessageList messages={messages} />);

    // Default state: atBottom=true, showScrollButton=false
    expect(screen.queryByRole('button', { name: /scroll to bottom/i })).not.toBeInTheDocument();
  });

  // ========================================
  // Named export verification
  // ========================================

  it('exports MessageList as named export', () => {
    expect(typeof MessageList).toBe('function');
    expect(MessageList.displayName).toBe('MessageList');
  });

  // ========================================
  // emptyStateSlot
  // ========================================

  it('renders emptyStateSlot when provided and no messages', () => {
    render(
      <MessageList messages={[]} emptyStateSlot={<div data-testid="custom-empty">Custom</div>} />
    );
    expect(screen.getByTestId('custom-empty')).toBeInTheDocument();
    expect(screen.queryByText('Start a conversation')).not.toBeInTheDocument();
  });

  it('falls back to default empty state when emptyStateSlot is not provided', () => {
    render(<MessageList messages={[]} />);
    expect(screen.getByText('Start a conversation')).toBeInTheDocument();
  });

  // ========================================
  // groupMessagesByRole utility
  // ========================================

  it('groupMessagesByRole groups consecutive same-role messages', () => {
    // groupMessagesByRole is not exported, so we test it indirectly
    // by passing consecutive same-role messages and verifying group counts
    const messages: ChatMessage[] = [
      createMessage({ id: 'msg-1', role: 'user', content: 'First' }),
      createMessage({ id: 'msg-2', role: 'user', content: 'Second' }),
      createMessage({ id: 'msg-3', role: 'assistant', content: 'Response' }),
      createMessage({ id: 'msg-4', role: 'assistant', content: 'More' }),
      createMessage({ id: 'msg-5', role: 'assistant', content: 'Even more' }),
      createMessage({ id: 'msg-6', role: 'user', content: 'Follow-up' }),
    ];

    render(<MessageList messages={messages} />);

    // Expected groups: [user x2], [assistant x3], [user x1] = 3 groups
    const groups = screen.getAllByTestId('message-group');
    expect(groups).toHaveLength(3);

    // First group: 2 consecutive user messages
    expect(groups[0]).toHaveAttribute('data-count', '2');
    // Second group: 3 consecutive assistant messages
    expect(groups[1]).toHaveAttribute('data-count', '3');
    // Third group: 1 user message
    expect(groups[2]).toHaveAttribute('data-count', '1');
  });
});

/**
 * ConversationMessage component tests.
 *
 * Tests for:
 * - User vs AI message styling
 * - Copy functionality
 * - Timestamp display
 * - Markdown rendering
 * - Streaming indicator
 *
 * @see specs/004-mvp-agents-build/tasks/P22-P25-T178-T222.md#T221
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ConversationMessage } from '../conversation-message';
import type { ConversationMessage as ConversationMessageType } from '@/stores/ai/ConversationStore';

// Mock clipboard API
Object.assign(navigator, {
  clipboard: {
    writeText: vi.fn().mockResolvedValue(undefined),
  },
});

describe('ConversationMessage', () => {
  const mockUserMessage: ConversationMessageType = {
    id: 'msg-1',
    role: 'user',
    content: 'Hello, how are you?',
    created_at: '2026-01-26T10:00:00Z',
  };

  const mockAIMessage: ConversationMessageType = {
    id: 'msg-2',
    role: 'assistant',
    content: 'I am doing well, thank you!',
    created_at: '2026-01-26T10:01:00Z',
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should render user message with correct styling', () => {
    render(<ConversationMessage message={mockUserMessage} />);

    expect(screen.getByText('Hello, how are you?')).toBeInTheDocument();
    expect(screen.getByLabelText('User message')).toBeInTheDocument();
  });

  it('should render AI message with correct styling', () => {
    render(<ConversationMessage message={mockAIMessage} />);

    expect(screen.getByText('I am doing well, thank you!')).toBeInTheDocument();
    expect(screen.getByLabelText('AI message')).toBeInTheDocument();
  });

  it('should display timestamp', () => {
    render(<ConversationMessage message={mockUserMessage} />);

    const timestamp = screen.getByText('10:00');
    expect(timestamp).toBeInTheDocument();
  });

  it('should show copy button for AI messages', async () => {
    const user = userEvent.setup();
    const { container } = render(<ConversationMessage message={mockAIMessage} />);

    // Copy button should be in the DOM but hidden initially
    const copyButton = screen.getByLabelText('Copy message');
    expect(copyButton).toBeInTheDocument();

    // Simulate hover to show button
    const messageContainer = container.querySelector('.group');
    if (messageContainer) {
      await user.hover(messageContainer);
    }

    await user.click(copyButton);

    expect(navigator.clipboard.writeText).toHaveBeenCalledWith('I am doing well, thank you!');
  });

  it('should not show copy button for user messages', () => {
    render(<ConversationMessage message={mockUserMessage} />);

    expect(screen.queryByLabelText('Copy message')).not.toBeInTheDocument();
  });

  it('should render streaming indicator when isStreaming=true', () => {
    render(<ConversationMessage message={mockAIMessage} isStreaming />);

    expect(screen.getByText('Typing')).toBeInTheDocument();
  });

  it('should render inline code', () => {
    const messageWithCode: ConversationMessageType = {
      id: 'msg-3',
      role: 'assistant',
      content: 'Use the `console.log()` function',
      created_at: '2026-01-26T10:02:00Z',
    };

    render(<ConversationMessage message={messageWithCode} />);

    const code = screen.getByText('console.log()');
    expect(code).toBeInTheDocument();
    expect(code.tagName).toBe('CODE');
  });

  it('should render code blocks', () => {
    const messageWithCodeBlock: ConversationMessageType = {
      id: 'msg-4',
      role: 'assistant',
      content: '```typescript\nconst x = 1;\n```',
      created_at: '2026-01-26T10:03:00Z',
    };

    render(<ConversationMessage message={messageWithCodeBlock} />);

    const code = screen.getByText('const x = 1;');
    expect(code).toBeInTheDocument();
    expect(code.tagName).toBe('CODE');
  });

  it('should preserve whitespace in content', () => {
    const messageWithWhitespace: ConversationMessageType = {
      id: 'msg-5',
      role: 'assistant',
      content: 'Line 1\nLine 2\nLine 3',
      created_at: '2026-01-26T10:04:00Z',
    };

    const { container } = render(<ConversationMessage message={messageWithWhitespace} />);

    // Check that content is rendered with whitespace-pre-wrap
    const contentElement = container.querySelector('.whitespace-pre-wrap');
    expect(contentElement).toBeInTheDocument();
  });
});

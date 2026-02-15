/**
 * Unit tests for UserMessage component.
 *
 * Tests rendering, answer message hiding, and display content.
 *
 * @module features/ai/ChatView/MessageList/__tests__/UserMessage
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import type { ChatMessage } from '@/stores/ai/types/conversation';
import { UserMessage } from '../UserMessage';

function makeMessage(overrides: Partial<ChatMessage> = {}): ChatMessage {
  return {
    id: 'msg-1',
    role: 'user',
    content: 'Hello, AI!',
    timestamp: new Date('2025-01-26T10:00:00Z'),
    ...overrides,
  };
}

describe('UserMessage', () => {
  it('renders user message content', () => {
    render(<UserMessage message={makeMessage()} />);
    expect(screen.getByText('Hello, AI!')).toBeDefined();
  });

  it('renders user name', () => {
    render(<UserMessage message={makeMessage()} userName="Alice" />);
    expect(screen.getByText('Alice')).toBeDefined();
  });

  it('returns null when metadata.isAnswerMessage is true', () => {
    const msg = makeMessage({
      content: '[User answered AI question abc-123]\n\nQ: Pick a color\nA: Red',
      metadata: { isAnswerMessage: true },
    });
    const { container } = render(<UserMessage message={msg} />);
    expect(container.firstElementChild).toBeNull();
  });

  it('renders normally when isAnswerMessage is not set', () => {
    const msg = makeMessage({ metadata: {} });
    render(<UserMessage message={msg} />);
    expect(screen.getByText('Hello, AI!')).toBeDefined();
  });

  it('renders normally when metadata is undefined', () => {
    const msg = makeMessage({ metadata: undefined });
    render(<UserMessage message={msg} />);
    expect(screen.getByTestId('message-user')).toBeDefined();
  });
});

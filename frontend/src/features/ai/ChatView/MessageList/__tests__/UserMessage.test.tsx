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

describe('UserMessage — mention pill rendering', () => {
  it('renders @[Note:uuid] as a MentionChip pill', () => {
    const msg = makeMessage({
      content: 'Check @[Note:550e8400-e29b-41d4-a716-446655440000] for details',
    });
    render(<UserMessage message={msg} />);
    // MentionChip renders with aria-label including entity type
    expect(
      screen.getByLabelText('Note: Note:550e8400. Press Backspace to remove.')
    ).toBeDefined();
    // Raw token should NOT be visible as text
    expect(screen.queryByText('@[Note:550e8400-e29b-41d4-a716-446655440000]')).toBeNull();
    // Surrounding text should still render
    expect(screen.getByText(/Check/)).toBeDefined();
    expect(screen.getByText(/for details/)).toBeDefined();
  });

  it('renders @[Issue:uuid] as a MentionChip pill', () => {
    const msg = makeMessage({
      content: 'Fix @[Issue:6ba7b810-9dad-11d1-80b4-00c04fd430c8] ASAP',
    });
    render(<UserMessage message={msg} />);
    expect(
      screen.getByLabelText('Issue: Issue:6ba7b810. Press Backspace to remove.')
    ).toBeDefined();
  });

  it('renders @[Project:uuid] as a MentionChip pill', () => {
    const msg = makeMessage({
      content: 'See @[Project:f47ac10b-58cc-4372-a567-0e02b2c3d479] overview',
    });
    render(<UserMessage message={msg} />);
    expect(
      screen.getByLabelText('Project: Project:f47ac10b. Press Backspace to remove.')
    ).toBeDefined();
  });

  it('renders multiple mention tokens as separate pills', () => {
    const msg = makeMessage({
      content:
        '@[Note:aaa-bbb] and @[Issue:ccc-ddd] are related',
    });
    render(<UserMessage message={msg} />);
    expect(
      screen.getByLabelText('Note: Note:aaa-bbb. Press Backspace to remove.')
    ).toBeDefined();
    expect(
      screen.getByLabelText('Issue: Issue:ccc-ddd. Press Backspace to remove.')
    ).toBeDefined();
  });

  it('renders plain text without tokens unchanged', () => {
    const msg = makeMessage({ content: 'Just a plain message' });
    render(<UserMessage message={msg} />);
    expect(screen.getByText('Just a plain message')).toBeDefined();
  });

  it('renders /resume command token as plain text (not a pill)', () => {
    const msg = makeMessage({ content: '/resume session' });
    render(<UserMessage message={msg} />);
    expect(screen.getByText('/resume session')).toBeDefined();
  });

  it('renders MentionChip pills without remove button (read-only)', () => {
    const msg = makeMessage({
      content: 'See @[Note:abc-123] here',
    });
    render(<UserMessage message={msg} />);
    // The remove button has aria-label "Remove {title}" -- should not exist
    expect(screen.queryByLabelText(/^Remove /)).toBeNull();
  });
});

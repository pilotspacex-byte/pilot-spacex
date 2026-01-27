/**
 * Conversation integration tests.
 *
 * End-to-end tests for multi-turn conversation flow:
 * - Start session
 * - Send multiple messages
 * - Receive streaming responses
 * - Handle errors
 *
 * @see specs/004-mvp-agents-build/tasks/P22-P25-T178-T222.md#T222
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { runInAction } from 'mobx';
import { ConversationPanel } from '../conversation-panel';
import type { ConversationStore } from '@/stores/ai/ConversationStore';
import type { ConversationMessage } from '@/stores/ai/ConversationStore';

// Create a real observable store for integration testing
const createMockStore = () => ({
  currentIssueId: null,
  isSessionActive: false,
  messages: [] as ConversationMessage[],
  isStreaming: false,
  currentStreamContent: '',
  error: null,
  get messageCount() {
    return this.messages.length;
  },
  startSession: vi.fn(async (issueId: string) => {
    runInAction(() => {
      Object.assign(mockStore, {
        currentIssueId: issueId,
        isSessionActive: true,
        messages: [],
      });
    });
  }),
  sendMessage: vi.fn(async (content: string) => {
    // Add user message
    runInAction(() => {
      (mockStore.messages as ConversationMessage[]).push({
        id: `msg-user-${Date.now()}`,
        role: 'user',
        content,
        created_at: new Date().toISOString(),
      });
      mockStore.isStreaming = true;
    });

    // Simulate streaming response
    await new Promise((resolve) => setTimeout(resolve, 100));

    runInAction(() => {
      mockStore.currentStreamContent = 'AI response to: ' + content;
    });

    await new Promise((resolve) => setTimeout(resolve, 100));

    // Complete streaming
    runInAction(() => {
      (mockStore.messages as ConversationMessage[]).push({
        id: `msg-ai-${Date.now()}`,
        role: 'assistant',
        content: mockStore.currentStreamContent!,
        created_at: new Date().toISOString(),
      });
      mockStore.isStreaming = false;
      mockStore.currentStreamContent = '';
    });
  }),
  abort: vi.fn(() => {
    runInAction(() => {
      mockStore.isStreaming = false;
      mockStore.currentStreamContent = '';
    });
  }),
  clearSession: vi.fn(() => {
    runInAction(() => {
      Object.assign(mockStore, {
        messages: [],
        sessionId: null,
        currentIssueId: null,
        error: null,
      });
    });
  }),
});

let mockStore: Partial<ConversationStore>;

vi.mock('@/stores', () => ({
  useStore: () => ({
    aiStore: {
      conversation: mockStore,
    },
  }),
}));

describe('Conversation Integration', () => {
  const issueId = 'test-issue-id';

  beforeEach(() => {
    mockStore = createMockStore();
  });

  it('should complete multi-turn conversation flow', async () => {
    const user = userEvent.setup();

    render(<ConversationPanel issueId={issueId} />);

    // Wait for session to start
    await waitFor(() => {
      expect(mockStore.startSession).toHaveBeenCalledWith(issueId);
      expect(mockStore.isSessionActive).toBe(true);
    });

    // Send first message
    const input = screen.getByPlaceholderText(/ask about implementation/i);
    await user.type(input, 'How do I implement this?');
    await user.click(screen.getByRole('button', { name: /send message/i }));

    // Wait for AI response
    await waitFor(
      () => {
        expect(screen.getByText('How do I implement this?')).toBeInTheDocument();
        expect(screen.getByText('AI response to: How do I implement this?')).toBeInTheDocument();
      },
      { timeout: 3000 }
    );

    expect(mockStore.messageCount).toBe(2);

    // Send second message
    await user.type(input, 'What about tests?');
    await user.click(screen.getByRole('button', { name: /send message/i }));

    // Wait for second AI response
    await waitFor(
      () => {
        expect(screen.getByText('What about tests?')).toBeInTheDocument();
        expect(screen.getByText('AI response to: What about tests?')).toBeInTheDocument();
      },
      { timeout: 3000 }
    );

    expect(mockStore.messageCount).toBe(4);
  });

  it('should handle suggested prompt click', async () => {
    const user = userEvent.setup();

    render(<ConversationPanel issueId={issueId} />);

    await waitFor(() => {
      expect(mockStore.isSessionActive).toBe(true);
    });

    // Click suggested prompt
    const promptButton = screen.getByText(/how can i implement this/i);
    await user.click(promptButton);

    await waitFor(
      () => {
        expect(mockStore.sendMessage).toHaveBeenCalled();
        expect(mockStore.messageCount).toBeGreaterThan(0);
      },
      { timeout: 3000 }
    );
  });

  it('should show streaming indicator during response', async () => {
    const user = userEvent.setup();

    render(<ConversationPanel issueId={issueId} />);

    await waitFor(() => {
      expect(mockStore.isSessionActive).toBe(true);
    });

    const input = screen.getByPlaceholderText(/ask about implementation/i);
    await user.type(input, 'Test message');
    await user.click(screen.getByRole('button', { name: /send message/i }));

    // During streaming
    await waitFor(() => {
      expect(mockStore.isStreaming).toBe(true);
    });

    // After streaming completes
    await waitFor(
      () => {
        expect(mockStore.isStreaming).toBe(false);
      },
      { timeout: 3000 }
    );
  });

  it('should handle session restart on different issue', async () => {
    const { rerender } = render(<ConversationPanel issueId={issueId} />);

    await waitFor(() => {
      expect(mockStore.currentIssueId).toBe(issueId);
    });

    // Change to different issue
    const newIssueId = 'different-issue-id';
    rerender(<ConversationPanel issueId={newIssueId} />);

    await waitFor(() => {
      expect(mockStore.startSession).toHaveBeenCalledWith(newIssueId);
    });
  });

  it('should clear input after sending message', async () => {
    const user = userEvent.setup();

    render(<ConversationPanel issueId={issueId} />);

    await waitFor(() => {
      expect(mockStore.isSessionActive).toBe(true);
    });

    const input = screen.getByPlaceholderText(/ask about implementation/i) as HTMLTextAreaElement;

    await user.type(input, 'Test message');
    expect(input.value).toBe('Test message');

    await user.click(screen.getByRole('button', { name: /send message/i }));

    await waitFor(() => {
      expect(input.value).toBe('');
    });
  });
});

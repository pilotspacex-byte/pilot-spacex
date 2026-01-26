/**
 * ConversationPanel component tests.
 *
 * Tests for:
 * - Session initialization
 * - Message display
 * - Input interaction
 * - Error handling
 * - Suggested prompts
 *
 * @see specs/004-mvp-agents-build/tasks/P22-P25-T178-T222.md#T221
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ConversationPanel } from '../conversation-panel';

// Types
interface MockMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
}

// Mock stores
const mockConversationStore = {
  currentIssueId: null as string | null,
  isSessionActive: false,
  messages: [] as MockMessage[],
  isStreaming: false,
  currentStreamContent: '',
  error: null as string | null,
  get messageCount() {
    return this.messages.length;
  },
  startSession: vi.fn(),
  sendMessage: vi.fn(),
};

vi.mock('@/stores', () => ({
  useStore: () => ({
    aiStore: {
      conversation: mockConversationStore,
    },
  }),
}));

describe('ConversationPanel', () => {
  const issueId = 'test-issue-id';

  beforeEach(() => {
    vi.clearAllMocks();
    mockConversationStore.messages = [];
    mockConversationStore.error = null;
    mockConversationStore.isStreaming = false;
  });

  it('should start session on mount', async () => {
    render(<ConversationPanel issueId={issueId} />);

    await waitFor(() => {
      expect(mockConversationStore.startSession).toHaveBeenCalledWith(issueId);
    });
  });

  it('should display suggested prompts when no messages', () => {
    render(<ConversationPanel issueId={issueId} />);

    expect(screen.getByText(/suggested prompts/i)).toBeInTheDocument();
    expect(screen.getByText(/how can i implement this/i)).toBeInTheDocument();
  });

  it('should hide suggested prompts when messages exist', () => {
    mockConversationStore.messages = [
      {
        id: 'msg-1',
        role: 'user',
        content: 'Hello',
        created_at: new Date().toISOString(),
      },
    ];

    render(<ConversationPanel issueId={issueId} />);

    expect(screen.queryByText(/suggested prompts/i)).not.toBeInTheDocument();
  });

  it('should send message on input submit', async () => {
    mockConversationStore.isSessionActive = true;
    const user = userEvent.setup();

    render(<ConversationPanel issueId={issueId} />);

    const input = screen.getByPlaceholderText(/ask about implementation/i);
    await user.type(input, 'Test message');
    await user.click(screen.getByRole('button', { name: /send message/i }));

    expect(mockConversationStore.sendMessage).toHaveBeenCalledWith('Test message');
  });

  it('should send message on prompt click', async () => {
    const user = userEvent.setup();

    render(<ConversationPanel issueId={issueId} />);

    const prompt = screen.getByText(/how can i implement this/i);
    await user.click(prompt);

    expect(mockConversationStore.sendMessage).toHaveBeenCalledWith(
      expect.stringContaining('How can I implement this issue')
    );
  });

  it('should display error alert', () => {
    mockConversationStore.error = 'Test error message';

    render(<ConversationPanel issueId={issueId} />);

    expect(screen.getByText('Test error message')).toBeInTheDocument();
  });

  it('should disable input during streaming', () => {
    mockConversationStore.isStreaming = true;
    mockConversationStore.isSessionActive = true;

    render(<ConversationPanel issueId={issueId} />);

    const sendButton = screen.getByRole('button', { name: /send message/i });
    expect(sendButton).toBeDisabled();
  });

  it('should disable input when session inactive', () => {
    mockConversationStore.isSessionActive = false;

    render(<ConversationPanel issueId={issueId} />);

    const input = screen.getByPlaceholderText(/starting session/i);
    expect(input).toBeDisabled();
  });
});

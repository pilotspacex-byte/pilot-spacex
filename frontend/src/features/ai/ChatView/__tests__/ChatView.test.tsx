/**
 * Unit tests for ChatView component.
 *
 * Validates:
 * - Input clears after successful message send
 * - Input restores on send failure
 * - Conversation clears and refetches on noteId change
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { PilotSpaceStore } from '@/stores/ai/PilotSpaceStore';

// Mock mobx-react-lite observer to pass through
vi.mock('mobx-react-lite', () => ({
  observer: <T,>(component: T) => component,
}));

// Mock motion/react
vi.mock('motion/react', () => ({
  AnimatePresence: ({ children }: { children: React.ReactNode }) => children,
  motion: {
    div: ({ children, ...props }: Record<string, unknown>) => {
      const { initial, animate, exit, transition, ...rest } = props;
      return <div {...rest}>{children as React.ReactNode}</div>;
    },
  },
  useReducedMotion: () => false,
}));

// Mock child components to isolate ChatView logic
vi.mock('../ChatHeader', () => ({
  ChatHeader: () => <div data-testid="chat-header" />,
}));

vi.mock('../MessageList/MessageList', () => ({
  MessageList: () => <div data-testid="message-list" />,
}));

vi.mock('../TaskPanel/TaskPanel', () => ({
  TaskPanel: () => <div data-testid="task-panel" />,
}));

vi.mock('../ApprovalOverlay/ApprovalOverlay', () => ({
  ApprovalOverlay: () => null,
}));

vi.mock('../ChatInput/ChatInput', () => ({
  ChatInput: ({
    value,
    onChange,
    onSubmit,
  }: {
    value: string;
    onChange: (v: string) => void;
    onSubmit: () => void;
  }) => (
    <div data-testid="chat-input">
      <input data-testid="chat-textarea" value={value} onChange={(e) => onChange(e.target.value)} />
      <button data-testid="send-button" onClick={onSubmit}>
        Send
      </button>
    </div>
  ),
}));

vi.mock('../MessageList/SuggestionCard', () => ({
  SuggestionCard: () => null,
}));

vi.mock('../MessageList/QuestionCard', () => ({
  QuestionCard: () => null,
}));

vi.mock('../ChatViewErrorBoundary', () => ({
  ChatViewErrorBoundary: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

vi.mock('@/stores/ai/SessionListStore', () => ({
  SessionListStore: vi.fn().mockImplementation(() => ({
    fetchSessions: vi.fn().mockResolvedValue(undefined),
    resumeSessionForContext: vi.fn().mockResolvedValue(false),
    resumeSession: vi.fn().mockResolvedValue(undefined),
    recentSessions: [],
    activeSessions: [],
    sessions: [],
    selectedSessionId: null,
  })),
}));

// Import after mocks
import { ChatView } from '../index';

function createMockStore(overrides: Partial<PilotSpaceStore> = {}): PilotSpaceStore {
  return {
    messages: [],
    isStreaming: false,
    error: null,
    tasks: new Map(),
    pendingApprovals: [],
    pendingContentUpdates: [],
    noteContext: null,
    issueContext: null,
    projectContext: null,
    activeQuestion: null,
    pendingQuestion: null,
    activeTasks: [],
    sessionId: null,
    streamContent: '',
    hasUnresolvedApprovals: false,
    streamingState: {
      isStreaming: false,
      streamContent: '',
      currentMessageId: null,
      thinkingContent: '',
      isThinking: false,
      thinkingStartedAt: null,
    },
    sendMessage: vi.fn().mockResolvedValue(undefined),
    clearConversation: vi.fn(),
    abort: vi.fn(),
    clear: vi.fn(),
    setNoteContext: vi.fn(),
    setIssueContext: vi.fn(),
    setProjectContext: vi.fn(),
    approveAction: vi.fn(),
    rejectAction: vi.fn(),
    submitQuestionAnswer: vi.fn(),
    ...overrides,
  } as unknown as PilotSpaceStore;
}

describe('ChatView', () => {
  let store: PilotSpaceStore;

  beforeEach(() => {
    vi.clearAllMocks();
    store = createMockStore();
  });

  describe('input clearing on send', () => {
    it('should clear input text after successful message send', async () => {
      const user = userEvent.setup();
      render(<ChatView store={store} />);

      const textarea = screen.getByTestId('chat-textarea');
      const sendButton = screen.getByTestId('send-button');

      // Type a message
      await user.type(textarea, 'Hello AI');
      expect(textarea).toHaveValue('Hello AI');

      // Send the message
      await user.click(sendButton);

      // Input should be cleared
      expect(textarea).toHaveValue('');
      expect(store.sendMessage).toHaveBeenCalledWith('Hello AI');
    });

    it('should restore input text if message send fails', async () => {
      const user = userEvent.setup();
      store = createMockStore({
        sendMessage: vi.fn().mockRejectedValue(new Error('Network error')),
      });
      render(<ChatView store={store} />);

      const textarea = screen.getByTestId('chat-textarea');
      const sendButton = screen.getByTestId('send-button');

      await user.type(textarea, 'Hello AI');
      await user.click(sendButton);

      // Input should be restored on failure
      expect(textarea).toHaveValue('Hello AI');
      expect(store.error).toBe('Network error');
    });
  });

  describe('conversation reset on note navigation', () => {
    it('should clear conversation and reload when noteId changes', async () => {
      const { SessionListStore: MockSessionListStore } =
        await import('@/stores/ai/SessionListStore');
      const mockResumeForContext = vi.fn().mockResolvedValue(true);
      const mockFetchSessions = vi.fn().mockResolvedValue(undefined);
      (MockSessionListStore as unknown as ReturnType<typeof vi.fn>).mockImplementation(() => ({
        fetchSessions: mockFetchSessions,
        resumeSessionForContext: mockResumeForContext,
        resumeSession: vi.fn().mockResolvedValue(undefined),
        recentSessions: [],
        activeSessions: [],
        sessions: [],
        selectedSessionId: null,
      }));

      store = createMockStore({
        noteContext: { noteId: 'note-1', noteTitle: 'Note 1' },
      });

      const { rerender } = render(<ChatView store={store} />);

      // Should have loaded context for note-1
      expect(store.clearConversation).toHaveBeenCalled();
      expect(mockResumeForContext).toHaveBeenCalledWith('note-1', 'note');

      // Navigate to a different note
      vi.clearAllMocks();
      store = createMockStore({
        noteContext: { noteId: 'note-2', noteTitle: 'Note 2' },
        clearConversation: store.clearConversation,
      });

      rerender(<ChatView store={store} />);

      // Should clear old conversation and load new one
      expect(store.clearConversation).toHaveBeenCalled();
      expect(mockResumeForContext).toHaveBeenCalledWith('note-2', 'note');
    });

    it('should not reload if noteId is the same', async () => {
      const { SessionListStore: MockSessionListStore } =
        await import('@/stores/ai/SessionListStore');
      const mockResumeForContext = vi.fn().mockResolvedValue(false);
      (MockSessionListStore as unknown as ReturnType<typeof vi.fn>).mockImplementation(() => ({
        fetchSessions: vi.fn().mockResolvedValue(undefined),
        resumeSessionForContext: mockResumeForContext,
        resumeSession: vi.fn().mockResolvedValue(undefined),
        recentSessions: [],
        activeSessions: [],
        sessions: [],
        selectedSessionId: null,
      }));

      store = createMockStore({
        noteContext: { noteId: 'note-1', noteTitle: 'Note 1' },
      });

      const { rerender } = render(<ChatView store={store} />);

      const firstCallCount = mockResumeForContext.mock.calls.length;

      // Re-render with same noteId
      rerender(<ChatView store={store} />);

      // Should not call resume again
      expect(mockResumeForContext.mock.calls.length).toBe(firstCallCount);
    });

    it('should fetch sessions without context on standalone chat page', async () => {
      const { SessionListStore: MockSessionListStore } =
        await import('@/stores/ai/SessionListStore');
      const mockFetchSessions = vi.fn().mockResolvedValue(undefined);
      const mockResumeForContext = vi.fn().mockResolvedValue(false);
      (MockSessionListStore as unknown as ReturnType<typeof vi.fn>).mockImplementation(() => ({
        fetchSessions: mockFetchSessions,
        resumeSessionForContext: mockResumeForContext,
        resumeSession: vi.fn().mockResolvedValue(undefined),
        recentSessions: [],
        activeSessions: [],
        sessions: [],
        selectedSessionId: null,
      }));

      store = createMockStore({
        noteContext: null,
      });

      render(<ChatView store={store} />);

      // Without noteContext, should just fetch sessions (standalone chat)
      expect(mockFetchSessions).toHaveBeenCalled();
      expect(mockResumeForContext).not.toHaveBeenCalled();
    });
  });
});

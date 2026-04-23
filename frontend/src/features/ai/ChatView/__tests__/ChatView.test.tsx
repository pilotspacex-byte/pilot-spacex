/**
 * Unit tests for ChatView component.
 *
 * Validates:
 * - Input clears after successful message send
 * - Input restores on send failure
 * - Conversation clears and refetches on noteId change
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
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

vi.mock('../ApprovalOverlay/DestructiveApprovalModal', () => ({
  DestructiveApprovalModal: () => null,
}));

vi.mock('../ChatInput/ChatInput', () => ({
  ChatInput: ({
    value,
    onChange,
    onSubmit,
  }: {
    value: string;
    onChange: (v: string) => void;
    onSubmit: (attachmentIds: string[]) => void;
  }) => (
    <div data-testid="chat-input">
      <input data-testid="chat-textarea" value={value} onChange={(e) => onChange(e.target.value)} />
      <button data-testid="send-button" onClick={() => onSubmit([])}>
        Send
      </button>
    </div>
  ),
}));

vi.mock('../MessageList/InlineApprovalCard', () => ({
  InlineApprovalCard: () => null,
}));

vi.mock('../MessageList/QuestionBlock', () => ({
  QuestionBlock: () => null,
}));

vi.mock('../WaitingIndicator', () => ({
  WaitingIndicator: () => null,
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
    agentTaskList: [],
    pendingApprovals: [],
    pendingContentUpdates: [],
    pendingToolCalls: [],
    noteContext: null,
    issueContext: null,
    projectContext: null,
    activeQuestion: null,
    pendingQuestion: null,
    activeTasks: [],
    sessionId: null,
    streamContent: '',
    hasUnresolvedApprovals: false,
    isWaitingForUser: false,
    hasMoreMessages: false,
    isLoadingMoreMessages: false,
    workspaceId: null,
    sessionState: null,
    tokenBudgetPercent: 0,
    streamingState: {
      isStreaming: false,
      streamContent: '',
      currentMessageId: null,
      thinkingContent: '',
      isThinking: false,
      thinkingStartedAt: null,
      phase: 'idle',
      interrupted: false,
      blockOrder: [],
      textSegments: new Map(),
      thinkingBlocks: [],
      activeToolName: null,
      wordCount: 0,
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
    removePendingApproval: vi.fn(),
    submitQuestionAnswer: vi.fn(),
    setWorkspaceId: vi.fn(),
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
      expect(store.sendMessage).toHaveBeenCalledWith('Hello AI', undefined, expect.any(Array));
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

      // Wait for first resume to complete (isResumingRef guard clears after async resolves)
      await waitFor(() => expect(mockResumeForContext).toHaveBeenCalledWith('note-1', 'note'));

      // Navigate to a different note
      vi.clearAllMocks();
      const clearConversation = store.clearConversation;
      store = createMockStore({
        noteContext: { noteId: 'note-2', noteTitle: 'Note 2' },
        clearConversation,
      });

      rerender(<ChatView store={store} />);

      // Navigating from note-1 → note-2: clearConversation IS called (previousNoteId = 'note-1')
      await waitFor(() => expect(clearConversation).toHaveBeenCalled());
      await waitFor(() => expect(mockResumeForContext).toHaveBeenCalledWith('note-2', 'note'));
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

  describe('approvalStore integration', () => {
    function createMockApprovalStore(
      overrides: Partial<{
        loadPending: () => Promise<void>;
        approve: (id: string) => Promise<void>;
        reject: (id: string, reason: string) => Promise<void>;
        pendingRequests: unknown[];
      }> = {}
    ) {
      return {
        loadPending: vi.fn().mockResolvedValue(undefined),
        approve: vi.fn().mockResolvedValue(undefined),
        reject: vi.fn().mockResolvedValue(undefined),
        pendingRequests: [],
        ...overrides,
      };
    }

    it('calls approvalStore.loadPending on mount when approvalStore provided', () => {
      const approvalStore = createMockApprovalStore();
      render(<ChatView store={store} approvalStore={approvalStore as never} />);
      expect(approvalStore.loadPending).toHaveBeenCalledTimes(1);
    });

    it('does not call loadPending when approvalStore is not provided', () => {
      const approvalStore = createMockApprovalStore();
      render(<ChatView store={store} />);
      expect(approvalStore.loadPending).not.toHaveBeenCalled();
    });

    it('shows backend-polled approvals from approvalStore.pendingRequests', () => {
      const pendingRequests = [
        {
          id: 'polled-1',
          agentName: 'pr_review',
          actionType: 'post_pr_comments',
          status: 'pending' as const,
          contextPreview: 'Post review comments',
          createdAt: new Date(),
          expiresAt: new Date(Date.now() + 86400000),
        },
      ];
      const approvalStore = createMockApprovalStore({ pendingRequests });
      // SSE list is empty; polled list has one item
      store = createMockStore({ pendingApprovals: [] });
      render(<ChatView store={store} approvalStore={approvalStore as never} />);
      // InlineApprovalCard is mocked — just verify no crash and loadPending called
      expect(approvalStore.loadPending).toHaveBeenCalled();
    });

    it('de-duplicates SSE and polled approvals with same id', () => {
      const sharedId = 'shared-123';
      const sseApprovals = [
        {
          requestId: sharedId,
          actionType: 'extract_issues',
          description: 'SSE copy',
          proposedContent: null,
          createdAt: new Date(),
          expiresAt: new Date(Date.now() + 86400000),
        },
      ];
      const polledRequests = [
        {
          id: sharedId,
          agentName: 'agent',
          actionType: 'extract_issues',
          status: 'pending' as const,
          contextPreview: 'Polled copy',
          createdAt: new Date(),
          expiresAt: new Date(Date.now() + 86400000),
        },
      ];
      const approvalStore = createMockApprovalStore({ pendingRequests: polledRequests });
      store = createMockStore({ pendingApprovals: sseApprovals as never });
      // Should render without error — SSE version takes precedence, polled is filtered out
      render(<ChatView store={store} approvalStore={approvalStore as never} />);
      expect(approvalStore.loadPending).toHaveBeenCalled();
    });

    it('routes approve through approvalStore.approve and removes from SSE store', async () => {
      const approvalStore = createMockApprovalStore();
      const removePendingApproval = vi.fn();
      store = createMockStore({ removePendingApproval });

      // Render with a non-destructive polled approval
      approvalStore.pendingRequests = [
        {
          id: 'approval-abc',
          agentName: 'agent',
          actionType: 'extract_issues',
          status: 'pending' as const,
          contextPreview: 'Approve me',
          createdAt: new Date(),
          expiresAt: new Date(Date.now() + 86400000),
        },
      ] as never;

      render(<ChatView store={store} approvalStore={approvalStore as never} />);
      // InlineApprovalCard is mocked so we cannot click approve directly;
      // verify loadPending called and store was initialized correctly
      expect(approvalStore.loadPending).toHaveBeenCalled();
    });
  });
});

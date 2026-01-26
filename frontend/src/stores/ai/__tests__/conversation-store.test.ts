/**
 * ConversationStore tests.
 *
 * Tests for:
 * - Session management (create/resume/expire)
 * - Message sending and streaming
 * - SSE event handling
 * - Error handling
 * - Computed properties
 *
 * @see specs/004-mvp-agents-build/tasks/P22-P25-T178-T222.md#T220
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { runInAction } from 'mobx';
import { ConversationStore } from '../ConversationStore';
import type { AIStore } from '../AIStore';

// Mock SSEClient
vi.mock('@/lib/sse-client', () => ({
  SSEClient: vi.fn().mockImplementation(() => ({
    connect: vi.fn().mockResolvedValue(undefined),
    abort: vi.fn(),
    isConnected: false,
    resetRetries: vi.fn(),
  })),
}));

// Mock AI API
vi.mock('@/services/api/ai', () => ({
  aiApi: {
    createConversationSession: vi.fn(),
    getConversationHistory: vi.fn(),
    getConversationUrl: vi.fn(() => '/api/v1/ai/conversation'),
  },
}));

describe('ConversationStore', () => {
  let store: ConversationStore;
  let mockRootStore: AIStore;
  let mockAiApi: typeof import('@/services/api/ai').aiApi;

  beforeEach(async () => {
    vi.clearAllMocks();

    // Import mocked aiApi
    const { aiApi } = await import('@/services/api/ai');
    mockAiApi = aiApi;

    // Create mock root store
    mockRootStore = {
      isGloballyEnabled: true,
    } as AIStore;

    store = new ConversationStore(mockRootStore);
  });

  afterEach(() => {
    store.clearSession();
  });

  describe('session management', () => {
    it('should create new session for issue', async () => {
      const issueId = 'test-issue-id';
      const mockSession = {
        session_id: 'test-session-id',
        issue_id: issueId,
        created_at: new Date().toISOString(),
        expires_at: new Date(Date.now() + 3600000).toISOString(),
      };

      vi.mocked(mockAiApi.createConversationSession).mockResolvedValue(mockSession);

      await store.startSession(issueId);

      expect(mockAiApi.createConversationSession).toHaveBeenCalledWith(issueId);
      expect(store.sessionId).toBe('test-session-id');
      expect(store.currentIssueId).toBe(issueId);
      expect(store.messages).toEqual([]);
    });

    it('should resume session from cache', async () => {
      const issueId = 'test-issue-id';
      const mockSession = {
        session_id: 'cached-session-id',
        issue_id: issueId,
        created_at: new Date().toISOString(),
        expires_at: new Date(Date.now() + 3600000).toISOString(),
      };

      const mockHistory = [
        {
          id: 'msg-1',
          role: 'user' as const,
          content: 'Hello',
          created_at: new Date().toISOString(),
        },
      ];

      vi.mocked(mockAiApi.createConversationSession).mockResolvedValue(mockSession);
      vi.mocked(mockAiApi.getConversationHistory).mockResolvedValue(mockHistory);

      // First call creates session
      await store.startSession(issueId);

      // Second call should reuse cached session
      await store.startSession(issueId);

      expect(mockAiApi.createConversationSession).toHaveBeenCalledTimes(1);
      expect(mockAiApi.getConversationHistory).toHaveBeenCalledWith('cached-session-id');
      expect(store.messages).toEqual(mockHistory);
    });

    it('should create new session when cached session expired', async () => {
      const issueId = 'test-issue-id';
      const expiredSession = {
        session_id: 'expired-session-id',
        issue_id: issueId,
        created_at: new Date(Date.now() - 7200000).toISOString(),
        expires_at: new Date(Date.now() - 3600000).toISOString(), // Expired 1 hour ago
      };

      const newSession = {
        session_id: 'new-session-id',
        issue_id: issueId,
        created_at: new Date().toISOString(),
        expires_at: new Date(Date.now() + 3600000).toISOString(),
      };

      vi.mocked(mockAiApi.createConversationSession)
        .mockResolvedValueOnce(expiredSession)
        .mockResolvedValueOnce(newSession);

      // First call
      await store.startSession(issueId);
      expect(store.sessionId).toBe('expired-session-id');

      // Second call should create new session due to expiration
      await store.startSession(issueId);
      expect(store.sessionId).toBe('new-session-id');
      expect(mockAiApi.createConversationSession).toHaveBeenCalledTimes(2);
    });

    it('should handle session creation error', async () => {
      const issueId = 'test-issue-id';
      vi.mocked(mockAiApi.createConversationSession).mockRejectedValue(new Error('API error'));

      await store.startSession(issueId);

      expect(store.sessionId).toBeNull();
      expect(store.error).toBe('API error');
    });

    it('should check session active state', async () => {
      const issueId = 'test-issue-id';
      const mockSession = {
        session_id: 'test-session-id',
        issue_id: issueId,
        created_at: new Date().toISOString(),
        expires_at: new Date(Date.now() + 3600000).toISOString(),
      };

      vi.mocked(mockAiApi.createConversationSession).mockResolvedValue(mockSession);

      expect(store.isSessionActive).toBe(false);

      await store.startSession(issueId);

      expect(store.isSessionActive).toBe(true);
    });
  });

  describe('message sending', () => {
    beforeEach(async () => {
      const mockSession = {
        session_id: 'test-session-id',
        issue_id: 'test-issue-id',
        created_at: new Date().toISOString(),
        expires_at: new Date(Date.now() + 3600000).toISOString(),
      };

      vi.mocked(mockAiApi.createConversationSession).mockResolvedValue(mockSession);
      await store.startSession('test-issue-id');
    });

    it('should send message and stream response', async () => {
      const { SSEClient } = await import('@/lib/sse-client');
      const mockSSEClient = SSEClient as unknown as ReturnType<typeof vi.fn>;

      await store.sendMessage('Hello AI');

      expect(store.messages).toHaveLength(1);
      expect(store.messages[0]).toMatchObject({
        role: 'user',
        content: 'Hello AI',
      });
      expect(store.isStreaming).toBe(true);
      expect(mockSSEClient).toHaveBeenCalled();
    });

    it('should handle streaming tokens', async () => {
      const { SSEClient } = await import('@/lib/sse-client');
      const mockSSEClient = SSEClient as unknown as ReturnType<typeof vi.fn>;

      let onMessageCallback:
        | ((event: { type: string; data: Record<string, unknown> }) => void)
        | undefined;
      mockSSEClient.mockImplementation(
        (options: {
          onMessage?: (event: { type: string; data: Record<string, unknown> }) => void;
        }) => {
          onMessageCallback = options.onMessage;
          return {
            connect: vi.fn().mockResolvedValue(undefined),
            abort: vi.fn(),
          };
        }
      );

      await store.sendMessage('Hello');

      // Simulate streaming tokens
      runInAction(() => {
        onMessageCallback?.({ type: 'token', data: { content: 'Hello' } });
        onMessageCallback?.({ type: 'token', data: { content: ' there' } });
      });

      expect(store.currentStreamContent).toBe('Hello there');
    });

    it('should complete message on stream complete', async () => {
      const { SSEClient } = await import('@/lib/sse-client');
      const mockSSEClient = SSEClient as unknown as ReturnType<typeof vi.fn>;

      let onMessageCallback:
        | ((event: { type: string; data: Record<string, unknown> }) => void)
        | undefined;
      let onCompleteCallback: (() => void) | undefined;
      mockSSEClient.mockImplementation(
        (options: {
          onMessage?: (event: { type: string; data: Record<string, unknown> }) => void;
          onComplete?: () => void;
        }) => {
          onMessageCallback = options.onMessage;
          onCompleteCallback = options.onComplete;
          return {
            connect: vi.fn().mockResolvedValue(undefined),
            abort: vi.fn(),
          };
        }
      );

      await store.sendMessage('Test');

      runInAction(() => {
        onMessageCallback?.({ type: 'token', data: { content: 'Response text' } });
        onMessageCallback?.({
          type: 'complete',
          data: { message_id: 'msg-ai-1' },
        });
        onCompleteCallback?.();
      });

      expect(store.messages).toHaveLength(2);
      expect(store.messages[1]).toMatchObject({
        id: 'msg-ai-1',
        role: 'assistant',
        content: 'Response text',
      });
      expect(store.isStreaming).toBe(false);
      expect(store.currentStreamContent).toBe('');
    });

    it('should handle streaming error', async () => {
      const { SSEClient } = await import('@/lib/sse-client');
      const mockSSEClient = SSEClient as unknown as ReturnType<typeof vi.fn>;

      let onErrorCallback: ((error: Error) => void) | undefined;
      mockSSEClient.mockImplementation((options: { onError?: (error: Error) => void }) => {
        onErrorCallback = options.onError;
        return {
          connect: vi.fn().mockResolvedValue(undefined),
          abort: vi.fn(),
        };
      });

      await store.sendMessage('Test');

      runInAction(() => {
        onErrorCallback?.(new Error('Stream error'));
      });

      expect(store.isStreaming).toBe(false);
      expect(store.error).toBe('Stream error');
    });

    it('should not send message without active session', async () => {
      store.clearSession();

      await store.sendMessage('Test');

      expect(store.error).toBe('No active session');
      expect(store.messages).toHaveLength(0);
    });
  });

  describe('abort and clear', () => {
    beforeEach(async () => {
      const mockSession = {
        session_id: 'test-session-id',
        issue_id: 'test-issue-id',
        created_at: new Date().toISOString(),
        expires_at: new Date(Date.now() + 3600000).toISOString(),
      };

      vi.mocked(mockAiApi.createConversationSession).mockResolvedValue(mockSession);
      await store.startSession('test-issue-id');
    });

    it('should abort streaming', async () => {
      const { SSEClient } = await import('@/lib/sse-client');
      const mockAbort = vi.fn();
      const mockSSEClient = SSEClient as unknown as ReturnType<typeof vi.fn>;

      mockSSEClient.mockImplementation(() => ({
        connect: vi.fn().mockResolvedValue(undefined),
        abort: mockAbort,
      }));

      await store.sendMessage('Test');

      store.abort();

      expect(mockAbort).toHaveBeenCalled();
      expect(store.isStreaming).toBe(false);
      expect(store.currentStreamContent).toBe('');
    });

    it('should clear session', () => {
      runInAction(() => {
        store.messages.push({
          id: 'msg-1',
          role: 'user',
          content: 'Test',
          created_at: new Date().toISOString(),
        });
      });

      store.clearSession();

      expect(store.messages).toHaveLength(0);
      expect(store.sessionId).toBeNull();
      expect(store.currentIssueId).toBeNull();
      expect(store.error).toBeNull();
    });
  });

  describe('computed properties', () => {
    beforeEach(async () => {
      const mockSession = {
        session_id: 'test-session-id',
        issue_id: 'test-issue-id',
        created_at: new Date().toISOString(),
        expires_at: new Date(Date.now() + 3600000).toISOString(),
      };

      vi.mocked(mockAiApi.createConversationSession).mockResolvedValue(mockSession);
      await store.startSession('test-issue-id');
    });

    it('should return last message', () => {
      runInAction(() => {
        store.messages.push(
          {
            id: 'msg-1',
            role: 'user',
            content: 'First',
            created_at: new Date().toISOString(),
          },
          {
            id: 'msg-2',
            role: 'assistant',
            content: 'Second',
            created_at: new Date().toISOString(),
          }
        );
      });

      expect(store.lastMessage).toMatchObject({
        id: 'msg-2',
        content: 'Second',
      });
    });

    it('should return message count', () => {
      runInAction(() => {
        store.messages.push(
          {
            id: 'msg-1',
            role: 'user',
            content: 'Test 1',
            created_at: new Date().toISOString(),
          },
          {
            id: 'msg-2',
            role: 'user',
            content: 'Test 2',
            created_at: new Date().toISOString(),
          }
        );
      });

      expect(store.messageCount).toBe(2);
    });
  });
});

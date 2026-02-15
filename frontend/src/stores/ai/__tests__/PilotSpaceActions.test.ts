/**
 * Unit tests for PilotSpaceActions.
 *
 * Tests user-facing async actions: sendMessage, approvals,
 * question answers, and lifecycle (abort, clear, reset).
 *
 * @module stores/ai/__tests__/PilotSpaceActions.test
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';

// Mock supabase before any store imports
vi.mock('@/lib/supabase', () => ({
  supabase: {
    auth: {
      getSession: vi.fn().mockResolvedValue({
        data: { session: { access_token: 'test-token' } },
      }),
    },
  },
}));

vi.mock('@/lib/sse-client', () => ({
  SSEClient: vi.fn().mockImplementation(() => ({
    connect: vi.fn().mockResolvedValue(undefined),
    abort: vi.fn(),
  })),
}));

import { PilotSpaceStore } from '../PilotSpaceStore';
import { PilotSpaceActions } from '../PilotSpaceActions';
import { PilotSpaceStreamHandler } from '../PilotSpaceStreamHandler';
import type { AIStore } from '../AIStore';

describe('PilotSpaceActions', () => {
  let store: PilotSpaceStore;
  let actions: PilotSpaceActions;
  let streamHandler: PilotSpaceStreamHandler;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  let fetchSpy: any;

  beforeEach(() => {
    const mockAIStore = {} as AIStore;
    store = new PilotSpaceStore(mockAIStore);
    store.setWorkspaceId('ws-1');
    streamHandler = new PilotSpaceStreamHandler(store);
    actions = new PilotSpaceActions(store, streamHandler);
    fetchSpy = vi.spyOn(global, 'fetch');
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('sendMessage', () => {
    it('should set error when stream completes without assistant response', async () => {
      // Simulate backend returning SSE stream that immediately closes (empty response)
      const mockReadableStream = new ReadableStream({
        start(controller) {
          controller.close(); // Immediately close = empty stream
        },
      });

      fetchSpy.mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ 'Content-Type': 'text/event-stream' }),
        body: mockReadableStream,
      } as unknown as Response);

      await actions.sendMessage('Hello AI');

      // User message should be added
      expect(store.messages).toHaveLength(1);
      expect(store.messages[0]!.role).toBe('user');

      // Silent failure detection: no assistant message, so error should be set
      expect(store.error).toBe(
        'No response received from AI. Check your API key configuration or try again.'
      );
      expect(store.streamingState.isStreaming).toBe(false);
    });

    it('should not set error when stream produces assistant message', async () => {
      // Simulate a stream that produces a message_start and message_stop
      const sseData = [
        'event: message_start\ndata: {"messageId":"msg-1","sessionId":"sess-1"}\n\n',
        'event: text_delta\ndata: {"delta":"Hello!"}\n\n',
        'event: message_stop\ndata: {"messageId":"msg-1","usage":{"totalTokens":10}}\n\n',
      ].join('');

      const encoder = new TextEncoder();
      const mockReadableStream = new ReadableStream({
        start(controller) {
          controller.enqueue(encoder.encode(sseData));
          controller.close();
        },
      });

      fetchSpy.mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ 'Content-Type': 'text/event-stream' }),
        body: mockReadableStream,
      } as unknown as Response);

      await actions.sendMessage('Hello AI');

      // Should have user + assistant messages
      expect(store.messages).toHaveLength(2);
      expect(store.messages[1]!.role).toBe('assistant');
      expect(store.error).toBeNull();
    });

    it('should set error on HTTP failure', async () => {
      fetchSpy.mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
      } as Response);

      await actions.sendMessage('Hello AI');

      expect(store.error).toBe('Chat request failed: 500 Internal Server Error');
      expect(store.streamingState.isStreaming).toBe(false);
    });

    it('should set error on network failure', async () => {
      fetchSpy.mockRejectedValueOnce(new Error('Failed to fetch'));

      await actions.sendMessage('Hello AI');

      expect(store.error).toBe('Failed to fetch');
      expect(store.streamingState.isStreaming).toBe(false);
    });
  });

  describe('approveRequest', () => {
    it('should send approval to backend and remove from queue', async () => {
      store.addApproval({
        requestId: 'req-1',
        actionType: 'create_issue',
        description: 'Create issue',
        affectedEntities: [],
        urgency: 'medium',
        expiresAt: new Date(),
        createdAt: new Date(),
      });

      fetchSpy.mockResolvedValueOnce({
        ok: true,
        json: async () => ({}),
      } as Response);

      await actions.approveRequest('req-1');

      expect(fetchSpy).toHaveBeenCalledWith(
        expect.stringContaining('/approvals/req-1/resolve'),
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ approved: true }),
        })
      );
      expect(store.pendingApprovals).toHaveLength(0);
    });

    it('should not throw when request not found', async () => {
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      await actions.approveRequest('nonexistent');
      expect(consoleSpy).toHaveBeenCalledWith(expect.stringContaining('nonexistent'));
    });

    it('should set error on fetch failure', async () => {
      store.addApproval({
        requestId: 'req-1',
        actionType: 'create_issue',
        description: 'Test',
        affectedEntities: [],
        urgency: 'low',
        expiresAt: new Date(),
        createdAt: new Date(),
      });

      fetchSpy.mockRejectedValueOnce(new Error('Network error'));

      await actions.approveRequest('req-1');

      expect(store.error).toBe('Network error');
    });
  });

  describe('rejectRequest', () => {
    it('should send rejection with reason to backend', async () => {
      store.addApproval({
        requestId: 'req-1',
        actionType: 'delete_issue',
        description: 'Delete',
        affectedEntities: [],
        urgency: 'high',
        expiresAt: new Date(),
        createdAt: new Date(),
      });

      fetchSpy.mockResolvedValueOnce({ ok: true } as Response);

      await actions.rejectRequest('req-1', 'Not needed');

      expect(fetchSpy).toHaveBeenCalledWith(
        expect.stringContaining('/approvals/req-1/resolve'),
        expect.objectContaining({
          body: JSON.stringify({ approved: false, note: 'Not needed' }),
        })
      );
      expect(store.pendingApprovals).toHaveLength(0);
    });
  });

  describe('submitQuestionAnswer', () => {
    it('should resolve question inline and send as new chat turn via sendMessage', async () => {
      store.setSessionId('sess-1');
      store.pendingQuestion = {
        questionId: 'q-1',
        questions: [{ question: 'Priority?', options: [], multiSelect: false }],
      };
      // Add an assistant message with questionData so resolveQuestion can find it
      store.messages.push({
        id: 'msg-prev',
        role: 'assistant',
        content: 'I need some info.',
        timestamp: new Date(),
        questionData: {
          questionId: 'q-1',
          questions: [{ question: 'Priority?', options: [], multiSelect: false }],
        },
      });

      // Mock two fetches: one for the [ANSWER:] sendMessage, one for the silent failure check
      const mockReadableStream = new ReadableStream({
        start(controller) {
          controller.close();
        },
      });
      fetchSpy.mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ 'Content-Type': 'text/event-stream' }),
        body: mockReadableStream,
      } as unknown as Response);

      await actions.submitQuestionAnswer('q-1', 'High', { q0: 'High' });

      // Should POST to /ai/chat with [ANSWER:questionId] prefix (via sendMessage)
      expect(fetchSpy).toHaveBeenCalledWith(
        expect.stringContaining('/ai/chat'),
        expect.objectContaining({
          method: 'POST',
          body: expect.stringContaining('[ANSWER:q-1] High'),
        })
      );
      // No separate user message — answer is embedded in assistant message
      const userMsg = store.messages.find((m) => m.role === 'user' && m.metadata?.isAnswerMessage);
      expect(userMsg).toBeUndefined();
      // Pending question should be cleared
      expect(store.pendingQuestion).toBeNull();
      // Q&A should be embedded in the assistant message via questionData.answers
      const assistantMsg = store.messages.find((m) => m.id === 'msg-prev');
      expect(assistantMsg?.questionData?.answers).toEqual({ q0: 'High' });
      // isSubmittingAnswer should be reset
      expect(store.isSubmittingAnswer).toBe(false);
    });

    it('should handle SSE stream response after answer submission', async () => {
      store.setSessionId('sess-1');
      store.pendingQuestion = {
        questionId: 'q-2',
        questions: [{ question: 'Which?', options: [], multiSelect: false }],
      };

      const sseData = [
        'event: message_start\ndata: {"messageId":"msg-a","sessionId":"sess-1"}\n\n',
        'event: text_delta\ndata: {"delta":"Got it."}\n\n',
        'event: message_stop\ndata: {"messageId":"msg-a","usage":{"totalTokens":5}}\n\n',
      ].join('');

      const encoder = new TextEncoder();
      const mockStream = new ReadableStream({
        start(controller) {
          controller.enqueue(encoder.encode(sseData));
          controller.close();
        },
      });

      fetchSpy.mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ 'Content-Type': 'text/event-stream' }),
        body: mockStream,
      } as unknown as Response);

      await actions.submitQuestionAnswer('q-2', 'Option A');

      // Pending question cleared
      expect(store.pendingQuestion).toBeNull();
      // Assistant response processed (user message from sendMessage + assistant from stream)
      expect(store.messages.some((m) => m.role === 'assistant')).toBe(true);
    });

    it('should rollback optimistic update and set error on HTTP failure', async () => {
      store.setSessionId('sess-1');
      store.pendingQuestion = {
        questionId: 'q-3',
        questions: [{ question: 'Test?', options: [], multiSelect: false }],
      };
      // Add assistant message with questionData for rollback verification
      store.messages.push({
        id: 'msg-fail',
        role: 'assistant',
        content: 'Question for you.',
        timestamp: new Date(),
        questionData: {
          questionId: 'q-3',
          questions: [{ question: 'Test?', options: [], multiSelect: false }],
        },
      });

      fetchSpy.mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
      } as Response);

      await actions.submitQuestionAnswer('q-3', 'answer', { q0: 'answer' });

      expect(store.error).toContain('500 Internal Server Error');
      expect(store.streamingState.isStreaming).toBe(false);
      // Rollback: pendingQuestion restored
      expect(store.pendingQuestion).toEqual({
        questionId: 'q-3',
        questions: [{ question: 'Test?', options: [], multiSelect: false }],
      });
      // Rollback: answers cleared from assistant message
      const msg = store.messages.find((m) => m.id === 'msg-fail');
      expect(msg?.questionData?.answers).toBeUndefined();
    });

    it('should do nothing when sessionId is null', async () => {
      store.setSessionId(null);
      await actions.submitQuestionAnswer('q-1', 'answer');
      expect(fetchSpy).not.toHaveBeenCalled();
    });
  });

  describe('abort', () => {
    it('should send abort signal when session active', async () => {
      store.setSessionId('sess-1');
      fetchSpy.mockResolvedValueOnce({ ok: true } as Response);

      actions.abort();

      // Flush microtask queue: abort() now resolves auth headers asynchronously
      await vi.waitFor(() => {
        expect(fetchSpy).toHaveBeenCalledWith(
          expect.stringContaining('/ai/chat/abort'),
          expect.objectContaining({ method: 'POST' })
        );
      });
      expect(store.streamingState.isStreaming).toBe(false);
    });

    it('should reset streaming state even without session', () => {
      store.streamingState.isStreaming = true;
      store.streamingState.streamContent = 'partial';

      actions.abort();

      expect(store.streamingState.isStreaming).toBe(false);
      expect(store.streamingState.streamContent).toBe('');
    });
  });

  describe('clear', () => {
    it('should reset all conversation state including pendingQuestion', () => {
      store.addMessage({ id: '1', role: 'user', content: 'Hi', timestamp: new Date() });
      store.setSessionId('sess-1');
      store.setForkSessionId('fork-1');
      store.addTask('task-1', { subject: 'Test', status: 'pending', progress: 0 });
      store.addApproval({
        requestId: 'req-1',
        actionType: 'test',
        description: 'test',
        affectedEntities: [],
        urgency: 'low',
        expiresAt: new Date(),
        createdAt: new Date(),
      });
      store.pendingQuestion = {
        questionId: 'q-1',
        questions: [{ question: 'Test?', options: [], multiSelect: false }],
      };
      store.error = 'some error';

      actions.clear();

      expect(store.messages).toHaveLength(0);
      expect(store.sessionId).toBeNull();
      expect(store.forkSessionId).toBeNull();
      expect(store.tasks.size).toBe(0);
      expect(store.pendingApprovals).toHaveLength(0);
      expect(store.pendingQuestion).toBeNull();
      expect(store.error).toBeNull();
    });
  });

  describe('reset', () => {
    it('should clear conversation and context', () => {
      store.setWorkspaceId('ws-1');
      store.setNoteContext({ noteId: 'n-1' });
      store.setIssueContext({ issueId: 'i-1' });
      store.skills = [{ name: 'test', description: 'test', category: 'analysis' as never }];

      actions.reset();

      expect(store.workspaceId).toBeNull();
      expect(store.noteContext).toBeNull();
      expect(store.issueContext).toBeNull();
      expect(store.skills).toHaveLength(0);
    });
  });

  describe('approveAction / rejectAction aliases', () => {
    it('should delegate approveAction to approveRequest', async () => {
      const spy = vi.spyOn(actions, 'approveRequest').mockResolvedValue();
      await actions.approveAction('req-1');
      expect(spy).toHaveBeenCalledWith('req-1', undefined);
    });

    it('should delegate approveAction with modifications to approveRequest', async () => {
      const spy = vi.spyOn(actions, 'approveRequest').mockResolvedValue();
      const mods = { title: 'Updated title' };
      await actions.approveAction('req-1', mods);
      expect(spy).toHaveBeenCalledWith('req-1', mods);
    });

    it('should delegate rejectAction to rejectRequest', async () => {
      const spy = vi.spyOn(actions, 'rejectRequest').mockResolvedValue();
      await actions.rejectAction('req-1', 'No reason');
      expect(spy).toHaveBeenCalledWith('req-1', 'No reason');
    });
  });
});

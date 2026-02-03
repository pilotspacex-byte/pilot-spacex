/**
 * Unit tests for PilotSpaceStreamHandler.
 *
 * Tests SSE event dispatch, stream parsing, and auth header resolution.
 *
 * @module stores/ai/__tests__/PilotSpaceStreamHandler.test
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';

// Mock supabase before any store imports
vi.mock('@/lib/supabase', () => ({
  supabase: {
    auth: {
      getSession: vi.fn().mockResolvedValue({
        data: { session: { access_token: 'test-token-123' } },
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
import { PilotSpaceStreamHandler } from '../PilotSpaceStreamHandler';
import type { AIStore } from '../AIStore';
import type { SSEEvent } from '../types/events';

describe('PilotSpaceStreamHandler', () => {
  let store: PilotSpaceStore;
  let handler: PilotSpaceStreamHandler;

  beforeEach(() => {
    const mockAIStore = {} as AIStore;
    store = new PilotSpaceStore(mockAIStore);
    handler = new PilotSpaceStreamHandler(store);
  });

  describe('parseSSEBuffer', () => {
    it('should parse a single event from buffer', () => {
      const buffer = 'event: text_delta\ndata: {"delta":"Hello"}\n\n';
      const events = handler.parseSSEBuffer(buffer);

      expect(events).toHaveLength(1);
      expect(events[0]!.type).toBe('text_delta');
      expect(events[0]!.data).toEqual({ delta: 'Hello' });
    });

    it('should parse multiple events from buffer', () => {
      const buffer =
        'event: message_start\ndata: {"messageId":"m1","sessionId":"s1"}\n\n' +
        'event: text_delta\ndata: {"delta":"Hi"}\n\n';
      const events = handler.parseSSEBuffer(buffer);

      expect(events).toHaveLength(2);
      expect(events[0]!.type).toBe('message_start');
      expect(events[1]!.type).toBe('text_delta');
    });

    it('should skip events with invalid JSON', () => {
      const buffer =
        'event: text_delta\ndata: {invalid json}\n\n' +
        'event: text_delta\ndata: {"delta":"Valid"}\n\n';
      const events = handler.parseSSEBuffer(buffer);

      expect(events).toHaveLength(1);
      expect(events[0]!.data).toEqual({ delta: 'Valid' });
    });

    it('should skip blocks without event type', () => {
      const buffer = 'data: {"delta":"no-type"}\n\n';
      const events = handler.parseSSEBuffer(buffer);

      expect(events).toHaveLength(0);
    });

    it('should skip blocks without data', () => {
      const buffer = 'event: text_delta\n\n';
      const events = handler.parseSSEBuffer(buffer);

      expect(events).toHaveLength(0);
    });

    it('should return empty array for empty buffer', () => {
      expect(handler.parseSSEBuffer('')).toHaveLength(0);
      expect(handler.parseSSEBuffer('\n\n')).toHaveLength(0);
    });
  });

  describe('handleSSEEvent routing', () => {
    it('should route message_start and set session ID', () => {
      const event: SSEEvent = {
        type: 'message_start',
        data: { messageId: 'msg-1', sessionId: 'sess-1' },
      };

      handler.handleSSEEvent(event);

      expect(store.sessionId).toBe('sess-1');
      expect(store.streamingState.currentMessageId).toBe('msg-1');
      expect(store.streamingState.isStreaming).toBe(true);
    });

    it('should route text_delta and accumulate content', () => {
      handler.handleSSEEvent({
        type: 'text_delta',
        data: { delta: 'Hello ' },
      });
      handler.handleSSEEvent({
        type: 'text_delta',
        data: { delta: 'World' },
      });

      expect(store.streamingState.streamContent).toBe('Hello World');
    });

    it('should route thinking_delta and track thinking state', () => {
      handler.handleSSEEvent({
        type: 'thinking_delta',
        data: { delta: 'Analyzing...' },
      });

      expect(store.streamingState.isThinking).toBe(true);
      expect(store.streamingState.thinkingContent).toBe('Analyzing...');
      expect(store.streamingState.thinkingStartedAt).toBeTruthy();
    });

    it('should end thinking when text_delta arrives after thinking', () => {
      handler.handleSSEEvent({
        type: 'thinking_delta',
        data: { delta: 'Thinking...' },
      });
      expect(store.streamingState.isThinking).toBe(true);

      handler.handleSSEEvent({
        type: 'text_delta',
        data: { delta: 'Response' },
      });
      expect(store.streamingState.isThinking).toBe(false);
    });

    it('should route tool_use and attach to current message', () => {
      // First create a message that tool_use can attach to
      store.addMessage({
        id: 'msg-1',
        role: 'assistant',
        content: '',
        timestamp: new Date(),
      });
      store.streamingState.currentMessageId = 'msg-1';

      handler.handleSSEEvent({
        type: 'tool_use',
        data: {
          toolCallId: 'tc-1',
          toolName: 'extract_issues',
          toolInput: { noteId: 'n1' },
        },
      });

      const msg = store.messages.find((m) => m.id === 'msg-1');
      expect(msg?.toolCalls).toHaveLength(1);
      expect(msg?.toolCalls?.[0]?.name).toBe('extract_issues');
      expect(msg?.toolCalls?.[0]?.status).toBe('pending');
    });

    it('should route tool_result and update tool call status', () => {
      store.addMessage({
        id: 'msg-1',
        role: 'assistant',
        content: '',
        timestamp: new Date(),
        toolCalls: [{ id: 'tc-1', name: 'extract_issues', input: {}, status: 'pending' }],
      });

      handler.handleSSEEvent({
        type: 'tool_result',
        data: {
          toolCallId: 'tc-1',
          status: 'completed',
          output: { issues: [] },
        },
      });

      const msg = store.messages.find((m) => m.id === 'msg-1');
      expect(msg?.toolCalls?.[0]?.status).toBe('completed');
      expect(msg?.toolCalls?.[0]?.output).toEqual({ issues: [] });
    });

    it('should route tool_result with cancelled status to failed', () => {
      store.addMessage({
        id: 'msg-1',
        role: 'assistant',
        content: '',
        timestamp: new Date(),
        toolCalls: [{ id: 'tc-1', name: 'test_tool', input: {}, status: 'pending' }],
      });

      handler.handleSSEEvent({
        type: 'tool_result',
        data: { toolCallId: 'tc-1', status: 'cancelled' },
      });

      expect(store.messages[0]?.toolCalls?.[0]?.status).toBe('failed');
    });

    it('should route task_progress and update task state', () => {
      handler.handleSSEEvent({
        type: 'task_progress',
        data: {
          taskId: 'task-1',
          subject: 'PR Review',
          status: 'in_progress',
          progress: 50,
          agentName: 'PRReviewAgent',
          model: 'claude-opus',
        },
      });

      const task = store.tasks.get('task-1');
      expect(task).toBeDefined();
      expect(task?.subject).toBe('PR Review');
      expect(task?.progress).toBe(50);
      expect(task?.agentName).toBe('PRReviewAgent');
    });

    it('should route approval_request and add to pending', () => {
      handler.handleSSEEvent({
        type: 'approval_request',
        data: {
          requestId: 'req-1',
          actionType: 'create_issue',
          description: 'Create issue from note',
          affectedEntities: [{ type: 'issue', id: 'i-1', name: 'Bug fix' }],
          urgency: 'medium',
          expiresAt: '2026-02-04T00:00:00Z',
        },
      });

      expect(store.pendingApprovals).toHaveLength(1);
      expect(store.pendingApprovals[0]?.requestId).toBe('req-1');
      expect(store.pendingApprovals[0]?.actionType).toBe('create_issue');
    });

    it('should route ask_user_question and set pendingQuestion', () => {
      handler.handleSSEEvent({
        type: 'ask_user_question',
        data: {
          messageId: 'msg-1',
          questionId: 'q-1',
          questions: [
            { question: 'Which priority?', options: [{ label: 'High' }], multiSelect: false },
          ],
        },
      });

      expect(store.pendingQuestion?.questionId).toBe('q-1');
      expect(store.pendingQuestion?.questions).toHaveLength(1);
    });

    it('should route structured_result and set pending result', () => {
      handler.handleSSEEvent({
        type: 'structured_result',
        data: {
          messageId: 'msg-1',
          schemaType: 'extraction_result',
          data: { issues: [{ title: 'Bug' }] },
        },
      });

      const result = store.consumePendingStructuredResult();
      expect(result?.schemaType).toBe('extraction_result');
    });

    it('should route content_update to store.handleContentUpdate', () => {
      const spy = vi.spyOn(store, 'handleContentUpdate');

      handler.handleSSEEvent({
        type: 'content_update',
        data: {
          noteId: 'note-1',
          operation: 'replace_block',
          blockId: 'b-1',
          markdown: null,
          content: { type: 'paragraph' },
          issueData: null,
          afterBlockId: null,
        },
      });

      expect(spy).toHaveBeenCalledTimes(1);
    });

    it('should route message_stop and finalize assistant message', () => {
      // Set up streaming state as if message_start + text_delta happened
      store.streamingState = {
        isStreaming: true,
        streamContent: 'Final answer',
        currentMessageId: 'msg-1',
        thinkingContent: 'I thought about it',
        isThinking: false,
        thinkingStartedAt: Date.now() - 1000,
      };

      handler.handleSSEEvent({
        type: 'message_stop',
        data: {
          messageId: 'msg-1',
          stopReason: 'end_turn',
          usage: { inputTokens: 100, outputTokens: 50, totalTokens: 150 },
          costUsd: 0.003,
        },
      });

      // Should create assistant message
      const msg = store.messages.find((m) => m.id === 'msg-1');
      expect(msg).toBeDefined();
      expect(msg?.role).toBe('assistant');
      expect(msg?.content).toBe('Final answer');
      expect(msg?.thinkingContent).toBe('I thought about it');
      expect(msg?.thinkingDurationMs).toBeGreaterThan(0);
      expect(msg?.metadata?.tokenCount).toBe(150);
      expect(msg?.metadata?.costUsd).toBe(0.003);

      // Should reset streaming state
      expect(store.streamingState.isStreaming).toBe(false);
      expect(store.streamingState.streamContent).toBe('');
    });

    it('should route error and set error state', () => {
      handler.handleSSEEvent({
        type: 'error',
        data: {
          errorCode: 'rate_limited',
          message: 'Too many requests',
          retryable: true,
          retryAfter: 10,
        },
      });

      expect(store.error).toBe('[rate_limited] Too many requests');
      expect(store.streamingState.isStreaming).toBe(false);
    });
  });

  describe('getAuthHeaders', () => {
    it('should return authorization header when session exists', async () => {
      const headers = await handler.getAuthHeaders();
      expect(headers).toEqual({ Authorization: 'Bearer test-token-123' });
    });
  });

  describe('content_block_start handling (G13)', () => {
    it('should track currentBlockType from content_block_start', () => {
      handler.handleSSEEvent({
        type: 'content_block_start',
        data: { index: 0, contentType: 'text' },
      });

      expect(store.streamingState.currentBlockType).toBe('text');
      expect(store.streamingState.currentBlockIndex).toBe(0);
    });

    it('should track tool_use block type', () => {
      handler.handleSSEEvent({
        type: 'content_block_start',
        data: { index: 1, contentType: 'tool_use' },
      });

      expect(store.streamingState.currentBlockType).toBe('tool_use');
      expect(store.streamingState.currentBlockIndex).toBe(1);
    });

    it('should transition phase to content on first text block', () => {
      // Start with message_start phase
      store.streamingState.phase = 'message_start';

      handler.handleSSEEvent({
        type: 'content_block_start',
        data: { index: 0, contentType: 'text' },
      });

      expect(store.streamingState.phase).toBe('content');
    });

    it('should store parentToolUseId when present', () => {
      handler.handleSSEEvent({
        type: 'content_block_start',
        data: { index: 0, contentType: 'tool_use', parentToolUseId: 'parent-tc-1' },
      });

      // Verify it's stored by creating a tool call afterward
      store.addMessage({
        id: 'msg-1',
        role: 'assistant',
        content: '',
        timestamp: new Date(),
      });
      store.streamingState.currentMessageId = 'msg-1';

      handler.handleSSEEvent({
        type: 'tool_use',
        data: {
          toolCallId: 'child-tc-1',
          toolName: 'Read',
          toolInput: { file: 'test.py' },
        },
      });

      const msg = store.messages.find((m) => m.id === 'msg-1');
      expect(msg?.toolCalls?.[0]?.parentToolUseId).toBe('parent-tc-1');
    });
  });

  describe('parentToolUseId correlation (G12)', () => {
    it('should reset parentToolUseId on message_start', () => {
      // Set parent from a content_block_start
      handler.handleSSEEvent({
        type: 'content_block_start',
        data: { index: 0, contentType: 'tool_use', parentToolUseId: 'old-parent' },
      });

      // message_start should reset it
      handler.handleSSEEvent({
        type: 'message_start',
        data: { messageId: 'msg-2', sessionId: 'sess-1' },
      });

      // Tool call after reset should not have parentToolUseId
      store.streamingState.currentMessageId = 'msg-2';
      store.addMessage({
        id: 'msg-2',
        role: 'assistant',
        content: '',
        timestamp: new Date(),
      });

      handler.handleSSEEvent({
        type: 'tool_use',
        data: {
          toolCallId: 'tc-2',
          toolName: 'Write',
          toolInput: { content: 'test' },
        },
      });

      const msg = store.messages.find((m) => m.id === 'msg-2');
      expect(msg?.toolCalls?.[0]?.parentToolUseId).toBeUndefined();
    });

    it('should attach parentToolUseId to tool calls from subagent blocks', () => {
      // First, a content_block_start with parent
      handler.handleSSEEvent({
        type: 'content_block_start',
        data: { index: 0, contentType: 'tool_use', parentToolUseId: 'subagent-parent' },
      });

      // Set up message for tool attachment
      store.addMessage({
        id: 'msg-3',
        role: 'assistant',
        content: '',
        timestamp: new Date(),
      });
      store.streamingState.currentMessageId = 'msg-3';

      // Tool call should get parent ID
      handler.handleSSEEvent({
        type: 'tool_use',
        data: {
          toolCallId: 'tc-3',
          toolName: 'extract_issues',
          toolInput: { noteId: 'n1' },
        },
      });

      const msg = store.messages.find((m) => m.id === 'msg-3');
      expect(msg?.toolCalls?.[0]?.parentToolUseId).toBe('subagent-parent');
    });
  });

  describe('abortClient', () => {
    it('should not throw when no client exists', () => {
      expect(() => handler.abortClient()).not.toThrow();
    });
  });
});
